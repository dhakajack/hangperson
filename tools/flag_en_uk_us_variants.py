#!/usr/bin/env python3
"""Flag likely US/UK English spelling variants for manual review."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VariantRule:
    name: str
    src_suffix: str
    dst_suffix: str


RULES: tuple[VariantRule, ...] = (
    VariantRule("our_or", "our", "or"),
    VariantRule("or_our", "or", "our"),
    VariantRule("ise_ize", "ise", "ize"),
    VariantRule("ize_ise", "ize", "ise"),
    VariantRule("isation_ization", "isation", "ization"),
    VariantRule("ization_isation", "ization", "isation"),
    VariantRule("yse_yze", "yse", "yze"),
    VariantRule("yze_yse", "yze", "yse"),
    VariantRule("ogue_og", "ogue", "og"),
    VariantRule("og_ogue", "og", "ogue"),
)

EXACT_PAIRS: tuple[tuple[str, str], ...] = (
    ("centre", "center"),
    ("metre", "meter"),
    ("litre", "liter"),
    ("fibre", "fiber"),
    ("theatre", "theater"),
    ("calibre", "caliber"),
    ("sombre", "somber"),
    ("lustre", "luster"),
    ("defence", "defense"),
    ("licence", "license"),
    ("pretence", "pretense"),
    ("offence", "offense"),
    ("artefact", "artifact"),
    ("cheque", "check"),
    ("pyjamas", "pajamas"),
    ("traveller", "traveler"),
    ("counsellor", "counselor"),
)

OUR_OR_STEMS: tuple[str, ...] = (
    "behavi",
    "col",
    "fav",
    "flav",
    "hon",
    "lab",
    "neighb",
    "rum",
    "hum",
    "od",
    "vap",
    "tum",
    "vig",
    "ard",
    "clam",
    "sav",
    "endeav",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan an English word list (txt or TSV with 'word' column) and flag "
            "predictable US/UK spelling variants for manual review."
        )
    )
    parser.add_argument("--input", type=Path, required=True, help="Input txt/tsv file.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output TSV file with flagged variants.",
    )
    return parser.parse_args()


def load_words(path: Path) -> list[str]:
    if path.suffix.lower() == ".tsv":
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file, delimiter="\t")
            if reader.fieldnames and "word" in reader.fieldnames:
                return [str(row.get("word", "")).strip() for row in reader if str(row.get("word", "")).strip()]
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def generate_variants(word: str) -> list[tuple[str, str]]:
    variants: list[tuple[str, str]] = []

    for uk, us in EXACT_PAIRS:
        if word == uk:
            variants.append((us, "exact_pair_uk_to_us"))
        elif word == us:
            variants.append((uk, "exact_pair_us_to_uk"))

    for rule in RULES:
        if word.endswith(rule.src_suffix) and len(word) > len(rule.src_suffix):
            if rule.name in {"our_or", "or_our"}:
                stem = word[: -len(rule.src_suffix)]
                if not any(stem.endswith(candidate) for candidate in OUR_OR_STEMS):
                    continue
            variant = word[: -len(rule.src_suffix)] + rule.dst_suffix
            if variant != word:
                variants.append((variant, rule.name))
    return variants


def flag_words(words: list[str]) -> list[dict[str, str]]:
    word_set = set(words)
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for word in words:
        for variant, rule_name in generate_variants(word):
            key = (word, variant, rule_name)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "word": word,
                    "variant": variant,
                    "variant_in_input": "yes" if variant in word_set else "no",
                    "rule": rule_name,
                }
            )
    return sorted(rows, key=lambda r: (r["word"], r["variant"], r["rule"]))


def write_rows(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["word", "variant", "variant_in_input", "rule"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    words = load_words(args.input)
    rows = flag_words(words)
    write_rows(rows, args.output)
    print(f"Wrote {len(rows):,} flagged rows to {args.output}.")


if __name__ == "__main__":
    main()
