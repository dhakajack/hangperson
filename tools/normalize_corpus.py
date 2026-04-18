#!/usr/bin/env python3
"""Normalize corpus text with language-specific rules for dictionary matching."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

from tools.postprocess_wordlist import (
    SCRIPT_CYRILLIC,
    SCRIPT_GREEK,
    SCRIPT_LATIN,
    _is_english_ascii_word,
    _matches_script_whitelist,
    contains_diacritic,
    decompose_french_ligatures,
    has_russian_prereform_letters,
    strip_diacritics,
)

TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)
LANGUAGE_CHOICES = ["en", "fr", "ru", "el"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a corpus file into one-token-per-line output using "
            "language-specific transformations aligned with dictionary cleanup."
        )
    )
    parser.add_argument("--input", type=Path, required=True, help="Input corpus text file.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output normalized token file (one token per line).",
    )
    parser.add_argument(
        "--language",
        choices=LANGUAGE_CHOICES,
        required=True,
        help="Language code for normalization profile.",
    )
    parser.add_argument(
        "--frequency-output",
        type=Path,
        default=None,
        help="Optional TSV output for token frequencies (word<TAB>count).",
    )
    parser.add_argument(
        "--no-lowercase",
        action="store_true",
        help="Disable lowercase conversion during normalization.",
    )
    return parser.parse_args()


def normalize_token(token: str, language: str, *, lowercase: bool = True) -> str | None:
    word = token.strip()
    if not word or not word.isalpha():
        return None

    if lowercase:
        word = word.lower()

    if language == "en":
        if contains_diacritic(word):
            return None
        if not _matches_script_whitelist(word, SCRIPT_LATIN):
            return None
        if not _is_english_ascii_word(word):
            return None
        return word

    if language == "fr":
        word = decompose_french_ligatures(word)
        if not _matches_script_whitelist(word, SCRIPT_LATIN):
            return None
        return word

    if language == "ru":
        if has_russian_prereform_letters(word):
            return None
        if not _matches_script_whitelist(word, SCRIPT_CYRILLIC):
            return None
        return word

    if language == "el":
        word = strip_diacritics(word)
        if not _matches_script_whitelist(word, SCRIPT_GREEK):
            return None
        return word

    raise ValueError(f"Unsupported language: {language}")


def normalize_corpus(
    input_path: Path,
    output_path: Path,
    language: str,
    frequency_output: Path | None = None,
    *,
    lowercase: bool = True,
) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    freq: Counter[str] | None = Counter() if frequency_output is not None else None

    total_tokens = 0
    kept_tokens = 0
    with input_path.open("r", encoding="utf-8", errors="ignore") as source:
        with output_path.open("w", encoding="utf-8") as sink:
            for line in source:
                for match in TOKEN_RE.finditer(line):
                    total_tokens += 1
                    normalized = normalize_token(
                        match.group(0), language, lowercase=lowercase
                    )
                    if normalized is None:
                        continue
                    sink.write(f"{normalized}\n")
                    kept_tokens += 1
                    if freq is not None:
                        freq[normalized] += 1

    if frequency_output is not None and freq is not None:
        write_frequency_tsv(freq, frequency_output)

    return total_tokens, kept_tokens


def write_frequency_tsv(freq: Counter[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(["word", "count"])
        for word, count in sorted(freq.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow([word, count])


def main() -> None:
    args = parse_args()
    total, kept = normalize_corpus(
        input_path=args.input,
        output_path=args.output,
        language=args.language,
        frequency_output=args.frequency_output,
        lowercase=not args.no_lowercase,
    )
    print(
        f"Normalized corpus written to {args.output} "
        f"(language={args.language}, lowercase={not args.no_lowercase}, "
        f"kept {kept:,} of {total:,} tokens)."
    )
    if args.frequency_output is not None:
        print(f"Frequency TSV written to {args.frequency_output}.")


if __name__ == "__main__":
    main()
