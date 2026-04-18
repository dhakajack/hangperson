"""Shared score-based word loading for runtime difficulty selection."""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path


DIFFICULTY_TO_BAND: dict[str, str] = {
    "1": "easy",
    "2": "medium",
    "3": "hard",
}

LANGUAGE_TO_TSV: dict[str, Path] = {
    "e": Path("data/difficulty/en_difficulty.tsv"),
    "f": Path("data/difficulty/fr_difficulty.tsv"),
    "r": Path("data/difficulty/ru_difficulty.tsv"),
}

VALID_BANDS = frozenset({"easy", "medium", "hard"})


class ScoreWordSourceError(ValueError):
    """Raised when score-based word loading fails and caller should fallback."""


def _is_letter_for_language(letter: str, language_key: str) -> bool:
    if len(letter) != 1 or not letter.isalpha():
        return False
    unicode_name = unicodedata.name(letter, "")
    if language_key in {"e", "f"}:
        return "LATIN" in unicode_name
    if language_key == "r":
        return "CYRILLIC" in unicode_name
    return False


def difficulty_tsv_path(language_key: str) -> Path:
    path = LANGUAGE_TO_TSV.get(language_key)
    if path is None:
        raise ScoreWordSourceError(
            f"No score TSV mapping configured for language key: {language_key}"
        )
    return path


def load_band_words_from_tsv(path: Path, language_key: str, band: str) -> list[str]:
    if not path.exists():
        raise ScoreWordSourceError(f"Score TSV not found: {path}")
    if band not in VALID_BANDS:
        raise ScoreWordSourceError(f"Unsupported difficulty band: {band}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if not reader.fieldnames:
            raise ScoreWordSourceError(f"Score TSV has no header: {path}")
        columns = set(reader.fieldnames)
        if "word" not in columns or "band" not in columns:
            raise ScoreWordSourceError(
                f"Score TSV must include 'word' and 'band' columns: {path}"
            )

        words: list[str] = []
        seen: set[str] = set()
        for row in reader:
            raw_band = str(row.get("band", "")).strip().lower()
            if raw_band != band:
                continue
            raw_word = str(row.get("word", "")).strip()
            word = raw_word.casefold()
            if len(word) < 6:
                continue
            if not word.isalpha():
                continue
            if word != word.lower():
                continue
            if any(not _is_letter_for_language(char, language_key) for char in word):
                continue
            if word in seen:
                continue
            seen.add(word)
            words.append(word)

    if not words:
        raise ScoreWordSourceError(
            f"No valid words found for score band '{band}' in {path}"
        )
    return words


def load_scored_words_for_difficulty(language_key: str, difficulty_key: str) -> list[str]:
    band = DIFFICULTY_TO_BAND.get(difficulty_key)
    if band is None:
        raise ScoreWordSourceError(
            f"Unsupported difficulty key for score loading: {difficulty_key}"
        )
    return load_band_words_from_tsv(
        path=difficulty_tsv_path(language_key),
        language_key=language_key,
        band=band,
    )
