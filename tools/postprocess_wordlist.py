#!/usr/bin/env python3
"""Post-process dictionary word lists for language-specific normalization rules."""

from __future__ import annotations

import argparse
import string
import unicodedata
from pathlib import Path

MODE_ENGLISH_DROP_ACCENTED = "english-drop-accented"
MODE_GREEK_STRIP_DIACRITICS = "greek-strip-diacritics"
MODE_FRENCH_DECOMPOSE_LIGATURES = "french-decompose-ligatures"
MODE_RUSSIAN_REMOVE_PREREFORM = "russian-remove-prereform"
SCRIPT_LATIN = "latin"
SCRIPT_CYRILLIC = "cyrillic"
SCRIPT_GREEK = "greek"
SCRIPT_CHOICES = [SCRIPT_LATIN, SCRIPT_CYRILLIC, SCRIPT_GREEK]
RUSSIAN_PREREFORM_CHARS = frozenset("ѢѣѲѳІіѴѵ")
VALID_MODES = [
    MODE_ENGLISH_DROP_ACCENTED,
    MODE_GREEK_STRIP_DIACRITICS,
    MODE_FRENCH_DECOMPOSE_LIGATURES,
    MODE_RUSSIAN_REMOVE_PREREFORM,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply language-specific cleanup rules to word-list files and write "
            "sorted, deduplicated output."
        )
    )
    parser.add_argument("--input", type=Path, required=True, help="Input word-list file.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for the cleaned word list.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        required=True,
        help=(
            f"{MODE_ENGLISH_DROP_ACCENTED}: remove entries that contain diacritics; "
            f"{MODE_GREEK_STRIP_DIACRITICS}: remove diacritics from each entry; "
            f"{MODE_FRENCH_DECOMPOSE_LIGATURES}: decompose French ligatures (oe, ae); "
            f"{MODE_RUSSIAN_REMOVE_PREREFORM}: remove words containing prereform "
            "letters (Ѣ/Ѳ/І/Ѵ)."
        ),
    )
    parser.add_argument(
        "--script-whitelist",
        choices=SCRIPT_CHOICES,
        default=None,
        help="Only keep words whose letters all belong to the selected script.",
    )
    parser.add_argument(
        "--english-strict-ascii",
        action="store_true",
        help="Only keep words made of ASCII letters A-Z/a-z.",
    )
    parser.add_argument(
        "--drop-all-caps",
        action="store_true",
        help="Drop words that are entirely uppercase (typically acronyms).",
    )
    parser.add_argument(
        "--drop-titlecase",
        action="store_true",
        help="Drop words in title case (typically proper nouns).",
    )
    parser.add_argument(
        "--lowercase-only",
        action="store_true",
        help="Keep only fully lowercase words.",
    )
    return parser.parse_args()


def contains_diacritic(text: str) -> bool:
    decomposed = unicodedata.normalize("NFD", text)
    return any(unicodedata.category(char) == "Mn" for char in decomposed)


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    filtered = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return unicodedata.normalize("NFC", filtered)


def decompose_french_ligatures(text: str) -> str:
    return (
        text.replace("œ", "oe")
        .replace("Œ", "OE")
        .replace("æ", "ae")
        .replace("Æ", "AE")
    )


def has_russian_prereform_letters(text: str) -> bool:
    return any(char in RUSSIAN_PREREFORM_CHARS for char in text)


def _char_script_name(char: str) -> str | None:
    name = unicodedata.name(char, "")
    if "LATIN" in name:
        return SCRIPT_LATIN
    if "CYRILLIC" in name:
        return SCRIPT_CYRILLIC
    if "GREEK" in name:
        return SCRIPT_GREEK
    return None


def _matches_script_whitelist(word: str, script: str) -> bool:
    for char in word:
        if not char.isalpha():
            return False
        if _char_script_name(char) != script:
            return False
    return True


def _is_english_ascii_word(word: str) -> bool:
    return all(char in string.ascii_letters for char in word)


def process_words(
    words: list[str],
    mode: str,
    *,
    script_whitelist: str | None = None,
    english_strict_ascii: bool = False,
    drop_all_caps: bool = False,
    drop_titlecase: bool = False,
    lowercase_only: bool = False,
) -> list[str]:
    output: set[str] = set()
    for raw in words:
        word = raw.strip()
        if not word:
            continue
        if drop_all_caps and word.isupper():
            continue
        if drop_titlecase and word.istitle():
            continue
        if mode == MODE_ENGLISH_DROP_ACCENTED:
            if contains_diacritic(word):
                continue
            output.add(word)
        elif mode == MODE_GREEK_STRIP_DIACRITICS:
            normalized = strip_diacritics(word)
            if normalized:
                output.add(normalized)
        elif mode == MODE_FRENCH_DECOMPOSE_LIGATURES:
            normalized = decompose_french_ligatures(word)
            if normalized:
                output.add(normalized)
        elif mode == MODE_RUSSIAN_REMOVE_PREREFORM:
            if has_russian_prereform_letters(word):
                continue
            output.add(word)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
    filtered: set[str] = set(output)
    if script_whitelist is not None:
        filtered = {
            word for word in filtered if _matches_script_whitelist(word, script_whitelist)
        }
    if english_strict_ascii:
        filtered = {word for word in filtered if _is_english_ascii_word(word)}
    if lowercase_only:
        filtered = {word for word in filtered if word == word.lower()}
    return sorted(filtered)


def main() -> None:
    args = parse_args()
    words = args.input.read_text(encoding="utf-8").splitlines()
    processed = process_words(
        words,
        args.mode,
        script_whitelist=args.script_whitelist,
        english_strict_ascii=args.english_strict_ascii,
        drop_all_caps=args.drop_all_caps,
        drop_titlecase=args.drop_titlecase,
        lowercase_only=args.lowercase_only,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for word in processed:
            file.write(f"{word}\n")

    print(
        f"Wrote {len(processed)} words to {args.output} "
        f"(mode={args.mode}, input={args.input}, script={args.script_whitelist}, "
        f"english_ascii={args.english_strict_ascii}, drop_all_caps={args.drop_all_caps}, "
        f"drop_titlecase={args.drop_titlecase}, lowercase_only={args.lowercase_only})."
    )


if __name__ == "__main__":
    main()
