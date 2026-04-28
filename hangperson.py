#!/usr/bin/env python3
"""Simple CLI Hangperson game."""

from __future__ import annotations

import json
import random
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from app_paths import data_path
from scored_words import ScoreWordSourceError, load_scored_words_for_difficulty

LANGUAGE_SETTINGS: dict[str, dict[str, str | Path]] = {
    "e": {
        "name": "English",
        "words_file": data_path("words_en.txt"),
        "locale_file": data_path("locales", "en.json"),
    },
    "f": {
        "name": "Français",
        "words_file": data_path("words_fr.txt"),
        "locale_file": data_path("locales", "fr.json"),
    },
    "r": {
        "name": "Русский",
        "words_file": data_path("words_ru.txt"),
        "locale_file": data_path("locales", "ru.json"),
    },
    "el": {
        "name": "Ελληνικά",
        "words_file": data_path("words_el.txt"),
        "locale_file": data_path("locales", "el.json"),
    },
}

LANGUAGE_ALIASES: dict[str, str] = {
    "e": "e",
    "english": "e",
    "en": "e",
    "f": "f",
    "fr": "f",
    "francais": "f",
    "français": "f",
    "french": "f",
    "r": "r",
    "р": "r",
    "p": "r",
    "ru": "r",
    "russian": "r",
    "русский": "r",
    "g": "el",
    "el": "el",
    "greek": "el",
    "ελληνικα": "el",
    "ελληνικά": "el",
}

DIFFICULTY_SETTINGS: dict[str, tuple[int, int | None, int]] = {
    "1": (6, 7, 10),
    "2": (8, 9, 8),
    "3": (10, None, 6),
}

DIFFICULTY_ALIASES: dict[str, str] = {
    "1": "1",
    "easy": "1",
    "e": "1",
    "2": "2",
    "medium": "2",
    "m": "2",
    "3": "3",
    "hard": "3",
    "h": "3",
}


def load_words(path: Path) -> list[str]:
    """Load lowercase alphabetic words with at least 6 letters."""
    if not path.exists():
        raise FileNotFoundError(f"Words file not found: {path}")

    words: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        word = raw_line.strip()
        if len(word) < 6:
            continue
        # Keep simple words only: lowercase letters, no proper nouns.
        if not word.isalpha() or word.lower() != word:
            continue
        words.append(word)

    # Deduplicate while preserving order.
    return list(dict.fromkeys(words))


def load_locale(path: Path) -> dict[str, object]:
    """Load localized interface strings from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Locale file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid locale data in {path}")
    return data


def choose_word(words: list[str]) -> str:
    if not words:
        raise ValueError("No valid words were found. Add lowercase words of length >= 6.")
    return random.choice(words)


def format_progress(progress: list[str]) -> str:
    return " ".join(progress)


def is_letter_for_language(letter: str, language_key: str) -> bool:
    """Return True if the letter belongs to the selected language script."""
    if len(letter) != 1 or not letter.isalpha():
        return False

    unicode_name = unicodedata.name(letter, "")
    if language_key in {"e", "f"}:
        return "LATIN" in unicode_name
    if language_key == "r":
        return "CYRILLIC" in unicode_name
    if language_key == "el":
        return "GREEK" in unicode_name
    return False


def normalize_guess_for_language(guess: str, language_key: str) -> str:
    """Normalize user guesses to a canonical Unicode form for comparisons."""
    _ = language_key
    return unicodedata.normalize("NFC", guess.casefold())


def format_letter_for_display(letter: str) -> str:
    """Format a guessed letter for display using Unicode-aware uppercase."""
    return unicodedata.normalize("NFC", letter.upper())


def prompt_letter(ui: dict[str, object], language_key: str) -> str:
    while True:
        guess = input("> ").strip().lower()
        if len(guess) != 1 or not guess.isalpha():
            print(str(ui["letter_invalid"]))
            continue
        if not is_letter_for_language(guess, language_key):
            print(str(ui["letter_wrong_script"]))
            continue
        return normalize_guess_for_language(guess, language_key)


def resolve_language_choice(choice: str) -> str | None:
    return LANGUAGE_ALIASES.get(choice.strip().casefold())


def prompt_language() -> tuple[str, dict[str, str | Path]]:
    while True:
        choice = input(
            "Choose language: English (E), Français (F), Русский (Р), Ελληνικά (G): "
        )
        language_key = resolve_language_choice(choice)
        if language_key:
            return language_key, LANGUAGE_SETTINGS[language_key]
        print("Please enter E, F, Р, or G.")


def prompt_difficulty(ui: dict[str, object]) -> tuple[str, str, int, int | None, int]:
    while True:
        raw_choice = input(str(ui["difficulty_prompt"])).strip().lower()
        choice = DIFFICULTY_ALIASES.get(raw_choice)
        if choice in DIFFICULTY_SETTINGS:
            min_length, max_length, max_errors = DIFFICULTY_SETTINGS[choice]
            difficulty_name = str(ui["difficulty_names"][choice])
            return choice, difficulty_name, min_length, max_length, max_errors
        print(str(ui["difficulty_invalid"]))


def filter_words_for_difficulty(
    words: list[str], min_length: int, max_length: int | None
) -> list[str]:
    if max_length is None:
        return [word for word in words if len(word) >= min_length]
    return [word for word in words if min_length <= len(word) <= max_length]


def load_words_for_session(
    language_key: str,
    words_file: Path,
    difficulty_key: str,
    min_length: int,
    max_length: int | None,
) -> tuple[list[str], str | None]:
    """Load words using score TSV first; fallback to legacy length filtering."""
    try:
        return load_scored_words_for_difficulty(language_key, difficulty_key), None
    except ScoreWordSourceError as exc:
        fallback_words = load_words(words_file)
        fallback_words = filter_words_for_difficulty(fallback_words, min_length, max_length)
        return fallback_words, str(exc)


@dataclass
class HangpersonGame:
    word: str
    max_errors: int
    guessed_none: str = "(none)"
    progress: list[str] = field(init=False)
    guessed_letters: set[str] = field(default_factory=set)
    errors: int = 0

    def __post_init__(self) -> None:
        self.progress = ["-" for _ in self.word]

    @property
    def guesses_remaining(self) -> int:
        return self.max_errors - self.errors

    @property
    def guessed_display(self) -> str:
        guessed = ", ".join(
            sorted(format_letter_for_display(letter) for letter in self.guessed_letters)
        )
        return guessed if guessed else self.guessed_none

    @staticmethod
    def _canonicalize_letter(letter: str) -> str:
        return letter.casefold()

    def word_contains_guess(self, guess: str) -> bool:
        canonical_guess = self._canonicalize_letter(guess)
        return any(
            self._canonicalize_letter(letter) == canonical_guess
            for letter in self.word
        )

    def apply_guess(self, guess: str) -> str:
        guess = self._canonicalize_letter(guess)
        if guess in self.guessed_letters:
            return "repeat"

        self.guessed_letters.add(guess)

        if self.word_contains_guess(guess):
            for idx, letter in enumerate(self.word):
                if self._canonicalize_letter(letter) == guess:
                    self.progress[idx] = format_letter_for_display(letter)
            return "correct"

        self.errors += 1
        return "incorrect"

    def is_won(self) -> bool:
        return "-" not in self.progress

    def is_lost(self) -> bool:
        return self.errors >= self.max_errors


def run_round(
    words: list[str], max_errors: int, ui: dict[str, object], language_key: str
) -> bool:
    game = HangpersonGame(
        word=choose_word(words),
        max_errors=max_errors,
        guessed_none=str(ui["guessed_none"]),
    )

    print(f"\n{ui['new_game']}")

    while True:
        print(f"\n{ui['word_label']}: {format_progress(game.progress)}")
        print(f"{ui['guesses_remaining_label']}: {game.guesses_remaining}")
        print(f"{ui['guessed_label']}: {game.guessed_display}")

        guess = prompt_letter(ui, language_key)
        outcome = game.apply_guess(guess)

        if outcome == "repeat":
            print(str(ui["repeat_guess"]).format(letter=guess.upper()))
            continue

        if outcome == "correct":
            print(str(ui["correct"]))
        else:
            print(str(ui["incorrect"]))

        if game.is_won():
            print(f"\n{str(ui['win']).format(word=game.word.upper())}")
            return True

        if game.is_lost():
            print(f"\n{str(ui['loss_summary']).format(max_errors=max_errors)}")
            print(str(ui["loss_word"]).format(word=game.word.upper()))
            return False


def play_again(ui: dict[str, object]) -> bool:
    while True:
        answer = input(str(ui["play_again_prompt"])).strip().lower()
        if answer in {"1", "p", "play", "y", "yes"}:
            return True
        if answer in {"0", "q", "quit", "n", "no"}:
            return False
        print(str(ui["play_again_invalid"]))


def main() -> None:
    print("Hangperson (CLI)")
    print("Guess letters to reveal the hidden word.")

    language_key, language = prompt_language()
    language_name = str(language["name"])
    words_file = Path(language["words_file"])
    locale_file = Path(language["locale_file"])

    try:
        ui = load_locale(locale_file)
    except Exception as exc:
        # Fall back to English for startup errors.
        print(f"Could not start game: {exc}")
        return

    difficulty_key, difficulty_name, min_length, max_length, max_errors = prompt_difficulty(ui)

    try:
        words, fallback_warning = load_words_for_session(
            language_key=language_key,
            words_file=words_file,
            difficulty_key=difficulty_key,
            min_length=min_length,
            max_length=max_length,
        )
    except Exception as exc:
        print(str(ui["start_error"]).format(error=exc))
        return

    if fallback_warning:
        print(
            str(ui["scored_words_fallback_warning"]).format(
                reason=fallback_warning
            )
        )

    if not words:
        print(str(ui["no_words_error"]))
        return

    print(str(ui["language_selected"]).format(language=language_name))
    print(
        str(ui["difficulty_selected"]).format(
            difficulty=difficulty_name,
            max_errors=max_errors,
        )
    )

    while True:
        run_round(words, max_errors, ui, language_key)
        if not play_again(ui):
            print(str(ui["thanks"]))
            break


if __name__ == "__main__":
    main()


# Backward compatibility for existing imports/tests.
HangmanGame = HangpersonGame
