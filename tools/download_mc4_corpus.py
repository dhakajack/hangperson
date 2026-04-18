#!/usr/bin/env python3
"""Download ~100MB of language-specific text from Hugging Face mc4-sampling."""

from __future__ import annotations

import argparse
import json
import re
from itertools import chain
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

DEFAULT_TARGET_MB = 100
PRIMARY_DATASET_NAME = "bertin-project/mc4-sampling"
FALLBACK_DATASET_NAME = "allenai/c4"
DATASETS_SERVER_BASE = "https://datasets-server.huggingface.co"


def _prompt_language() -> str:
    while True:
        lang = input("Language code (for example: en, fr, ru): ").strip().lower()
        if lang:
            return lang
        print("Please enter a non-empty language code.")


def _truncate_utf8(data: bytes, max_bytes: int) -> bytes:
    """Trim bytes without leaving an invalid UTF-8 sequence at the end."""
    chunk = data[:max_bytes]
    while chunk:
        try:
            chunk.decode("utf-8")
            return chunk
        except UnicodeDecodeError:
            chunk = chunk[:-1]
    return b""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download approximately N MB of text from Hugging Face mc4-sampling "
            "for a chosen language."
        )
    )
    parser.add_argument("--language", default="", help="Language code (e.g. en, fr, ru)")
    parser.add_argument(
        "--target-mb",
        type=int,
        default=DEFAULT_TARGET_MB,
        help=f"Target size in MB (default: {DEFAULT_TARGET_MB})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/corpora"),
        help="Destination directory (default: data/corpora)",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List available mc4-sampling language configs and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Import here so the script can still show useful help when dependency is missing.
    try:
        from datasets import get_dataset_config_names, load_dataset
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: datasets. Install with:\n"
            "  python3 -m pip install datasets"
        ) from exc

    if args.list_languages:
        print("Fetching available language configs...")
        config_names = _get_dataset_config_names_compat(
            get_dataset_config_names, PRIMARY_DATASET_NAME
        )
        if not config_names:
            config_names = _list_languages_via_server(PRIMARY_DATASET_NAME)
        if not config_names:
            print(
                f"Could not list configs from '{PRIMARY_DATASET_NAME}'. "
                f"Falling back to '{FALLBACK_DATASET_NAME}'."
            )
            config_names = _get_dataset_config_names_compat(
                get_dataset_config_names, FALLBACK_DATASET_NAME
            )
        if not config_names:
            config_names = _list_languages_via_server(FALLBACK_DATASET_NAME)
        if not config_names:
            config_names = _list_languages_via_hf_api(PRIMARY_DATASET_NAME)
        if not config_names:
            config_names = _list_languages_via_hf_api(FALLBACK_DATASET_NAME)
        if not config_names:
            config_names = _list_languages_from_readme(PRIMARY_DATASET_NAME)
        if not config_names:
            config_names = _list_languages_from_readme(FALLBACK_DATASET_NAME)
        if not config_names:
            raise SystemExit(
                "Could not list language configs from either dataset source. "
                "Check internet access and dataset availability."
            )
        for name in config_names:
            print(name)
        return

    dataset_name = PRIMARY_DATASET_NAME
    language = args.language.strip().lower() or _prompt_language()
    target_bytes = args.target_mb * 1024 * 1024
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Loading dataset '{dataset_name}' for language '{language}' in streaming mode..."
    )
    try:
        stream = _ensure_stream_has_rows(
            _load_dataset_compat(load_dataset, dataset_name, language)
        )
    except Exception as exc:
        print(
            "Falling back to datasets-server API because local datasets loading failed:\n"
            f"  {exc}"
        )
        try:
            stream = _ensure_stream_has_rows(
                _iter_text_rows_via_server(dataset_name, language)
            )
        except Exception as api_exc:
            print(
                f"datasets-server fallback failed for '{dataset_name}':\n"
                f"  {api_exc}\n"
                f"Trying fallback dataset '{FALLBACK_DATASET_NAME}'."
            )
            dataset_name = FALLBACK_DATASET_NAME
            try:
                stream = _ensure_stream_has_rows(
                    _load_dataset_compat(load_dataset, dataset_name, language)
                )
            except Exception as fallback_exc:
                print(
                    "Falling back to datasets-server API for fallback dataset because "
                    "local datasets loading failed:\n"
                    f"  {fallback_exc}"
                )
                try:
                    stream = _ensure_stream_has_rows(
                        _iter_text_rows_via_server(dataset_name, language)
                    )
                except Exception as fallback_api_exc:
                    raise SystemExit(
                        "Could not stream corpus rows from either dataset source.\n"
                        f"Primary dataset: {PRIMARY_DATASET_NAME}\n"
                        f"Fallback dataset: {FALLBACK_DATASET_NAME}\n"
                        f"Last error: {fallback_api_exc}"
                    ) from fallback_api_exc

    dataset_slug = dataset_name.replace("/", "_").replace("-", "_")
    output_path = output_dir / f"{dataset_slug}_{language}_{args.target_mb}mb.txt"

    bytes_written = 0
    rows_used = 0
    with output_path.open("w", encoding="utf-8") as file:
        for row in stream:
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            payload = (text + "\n").encode("utf-8")
            remaining = target_bytes - bytes_written
            if remaining <= 0:
                break
            if len(payload) <= remaining:
                file.write(text + "\n")
                bytes_written += len(payload)
            else:
                tail = _truncate_utf8(payload, remaining)
                file.write(tail.decode("utf-8", errors="ignore"))
                bytes_written += len(tail)
                break
            rows_used += 1

    print(
        f"Done. Wrote {bytes_written:,} bytes from {rows_used:,} rows to:\n"
        f"  {output_path}"
    )


def _get_dataset_config_names_compat(get_dataset_config_names_fn, dataset_name: str):
    """Support both old and new datasets APIs."""
    try:
        return get_dataset_config_names_fn(dataset_name)
    except TypeError:
        # Some older signatures may require explicit trust_remote_code.
        return get_dataset_config_names_fn(dataset_name, trust_remote_code=True)
    except RuntimeError as exc:
        if "Dataset scripts are no longer supported" in str(exc):
            return []
        if "trust_remote_code" in str(exc):
            return get_dataset_config_names_fn(dataset_name, trust_remote_code=True)
        raise


def _load_dataset_compat(load_dataset_fn, dataset_name: str, language: str):
    """Support both old and new datasets APIs."""
    try:
        return load_dataset_fn(
            dataset_name,
            language,
            split="train",
            streaming=True,
        )
    except TypeError:
        # Some older signatures may require explicit trust_remote_code.
        return load_dataset_fn(
            dataset_name,
            language,
            split="train",
            streaming=True,
            trust_remote_code=True,
        )
    except RuntimeError as exc:
        if "trust_remote_code" in str(exc):
            return load_dataset_fn(
                dataset_name,
                language,
                split="train",
                streaming=True,
                trust_remote_code=True,
            )
        raise


def _list_languages_via_server(dataset_name: str) -> list[str]:
    try:
        payload = _fetch_json(
            f"{DATASETS_SERVER_BASE}/splits?{urlencode({'dataset': dataset_name})}"
        )
    except (HTTPError, URLError, TimeoutError):
        return []
    configs = {
        str(item.get("config", "")).strip()
        for item in payload.get("splits", [])
        if str(item.get("config", "")).strip()
    }
    return sorted(configs)


def _iter_text_rows_via_server(dataset_name: str, language: str) -> Iterable[dict[str, str]]:
    offset = 0
    length = 100
    while True:
        query = urlencode(
            {
                "dataset": dataset_name,
                "config": language,
                "split": "train",
                "offset": offset,
                "length": length,
            }
        )
        payload = _fetch_json(f"{DATASETS_SERVER_BASE}/rows?{query}")
        rows = payload.get("rows", [])
        if not rows:
            break
        for item in rows:
            row = item.get("row", {})
            if isinstance(row, dict):
                yield {"text": str(row.get("text", ""))}
        offset += len(rows)


def _fetch_json(url: str) -> dict:
    with urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _list_languages_from_readme(dataset_name: str) -> list[str]:
    """Parse language codes from dataset card YAML metadata as a last-resort fallback."""
    try:
        dataset_id = quote(dataset_name, safe="/")
        payload = _fetch_bytes(
            "https://huggingface.co/datasets/"
            f"{dataset_id}/resolve/main/README.md"
        )
    except Exception:
        return []

    text = payload.decode("utf-8", errors="ignore")
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    yaml_meta = text[3:end]

    # Match list items in the metadata language section: "- en", "- fr", etc.
    candidates = re.findall(r"^\s*-\s*([a-z]{2,3}(?:-[A-Za-z0-9]+)?)\s*$", yaml_meta, re.M)
    return sorted(set(candidates))


def _list_languages_via_hf_api(dataset_name: str) -> list[str]:
    """Try Hugging Face REST API cardData language metadata."""
    try:
        dataset_id = quote(dataset_name, safe="/")
        payload = _fetch_json(
            f"https://huggingface.co/api/datasets/{dataset_id}"
        )
    except Exception:
        return []

    card_data = payload.get("cardData", {})
    langs = card_data.get("language", [])
    if isinstance(langs, str):
        langs = [langs]
    if not isinstance(langs, list):
        return []
    return sorted(
        {
            str(item).strip()
            for item in langs
            if re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)?", str(item).strip())
        }
    )


def _fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=60) as response:
        return response.read()


def _ensure_stream_has_rows(stream: Iterable[dict[str, str]]) -> Iterable[dict[str, str]]:
    """Force first read so lazy HTTP errors are handled in fallback try/except blocks."""
    iterator = iter(stream)
    try:
        first_row = next(iterator)
    except StopIteration as exc:
        raise RuntimeError("Stream returned no rows.") from exc
    return chain([first_row], iterator)


if __name__ == "__main__":
    main()
