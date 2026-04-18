#!/usr/bin/env python3
"""Extract clean lemma word lists from Apertium .dix/.metadix files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

LM_RE = re.compile(r'lm="([^"]+)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read Apertium dictionaries, extract lm=\"...\" lemmas, filter to "
            "single-word alphabetic entries, then write sorted deduplicated lists."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/dictionaries/apertium"),
        help="Directory containing Apertium dictionary files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for *_wl files (default: same as --input-dir).",
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=["*.dix", "*.metadix"],
        help="File patterns to scan under --input-dir.",
    )
    return parser.parse_args()


def is_valid_lemma(lemma: str) -> bool:
    """Keep only single-token alphabetic lemmas without case normalization."""
    if not lemma:
        return False
    if any(char.isspace() for char in lemma):
        return False
    return all(char.isalpha() for char in lemma)


def extract_lemmas_from_file(path: Path) -> set[str]:
    lemmas: set[str] = set()
    with path.open("r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            for match in LM_RE.finditer(line):
                lemma = match.group(1)
                if is_valid_lemma(lemma):
                    lemmas.add(lemma)
    return lemmas


def output_path_for(source_file: Path, output_dir: Path) -> Path:
    return output_dir / f"{source_file.stem}_wl.txt"


def main() -> None:
    args = parse_args()
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir or input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    sources: list[Path] = []
    seen: set[Path] = set()
    for pattern in args.patterns:
        for file_path in sorted(input_dir.glob(pattern)):
            if file_path in seen or not file_path.is_file():
                continue
            seen.add(file_path)
            sources.append(file_path)

    if not sources:
        raise SystemExit(f"No files matched in {input_dir} using patterns: {args.patterns}")

    for source in sources:
        lemmas = extract_lemmas_from_file(source)
        out_path = output_path_for(source, output_dir)
        with out_path.open("w", encoding="utf-8") as out_file:
            for lemma in sorted(lemmas):
                out_file.write(f"{lemma}\n")
        print(f"{source.name} -> {out_path.name}: {len(lemmas)} entries")


if __name__ == "__main__":
    main()
