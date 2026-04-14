#!/usr/bin/env python3
"""Simple CLI Hangman game."""

from __future__ import annotations

import random
from pathlib import Path

LANGUAGE_WORD_FILES: dict[str, tuple[str, Path]] = {
    "e": ("English", Path("data/words_en.txt")),
    "f": ("French", Path("data/words_fr.txt")),
    "r": ("Russian", Path("data/words_ru.txt")),
}
DIFFICULTY_SETTINGS: dict[str, tuple[str, int, int | None, int]] = {
    "e": ("Easy", 6, 7, 10),
    "m": ("Medium", 8, 9, 8),
    "h": ("Hard", 10, None, 6),
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


def choose_word(words: list[str]) -> str:
    if not words:
        raise ValueError("No valid words were found. Add lowercase words of length >= 6.")
    return random.choice(words)


def format_progress(progress: list[str]) -> str:
    return " ".join(progress)


def prompt_letter() -> str:
    while True:
        guess = input("> ").strip().lower()
        if len(guess) != 1 or not guess.isalpha():
            print("Please enter a single letter.")
            continue
        return guess


def prompt_language() -> tuple[str, Path]:
    while True:
        choice = input("Choose language: English (E), French (F), Russian (R): ").strip().lower()
        if choice in LANGUAGE_WORD_FILES:
            return LANGUAGE_WORD_FILES[choice]
        print("Please enter E, F, or R.")


def prompt_difficulty() -> tuple[str, int, int | None, int]:
    while True:
        choice = input("Choose difficulty: Easy (E), Medium (M), Hard (H): ").strip().lower()
        if choice in DIFFICULTY_SETTINGS:
            return DIFFICULTY_SETTINGS[choice]
        print("Please enter E, M, or H.")


def filter_words_for_difficulty(
    words: list[str], min_length: int, max_length: int | None
) -> list[str]:
    if max_length is None:
        return [word for word in words if len(word) >= min_length]
    return [word for word in words if min_length <= len(word) <= max_length]


def run_round(words: list[str], max_errors: int) -> bool:
    word = choose_word(words)
    progress = ["-" for _ in word]
    guessed_letters: set[str] = set()
    errors = 0

    print("\nNew game started!")

    while True:
        print(f"\nWord: {format_progress(progress)}")
        print(f"Guesses remaining: {max_errors - errors}")
        guessed_display = ", ".join(sorted(letter.upper() for letter in guessed_letters))
        if guessed_display:
            print(f"Guessed: {guessed_display}")
        else:
            print("Guessed: (none)")

        guess = prompt_letter()

        if guess in guessed_letters:
            print(f"You already guessed '{guess.upper()}'. Try a new letter.")
            continue

        guessed_letters.add(guess)

        if guess in word:
            for idx, letter in enumerate(word):
                if letter == guess:
                    progress[idx] = guess.upper()
            print("Correct!")
        else:
            errors += 1
            print("Incorrect.")

        if "-" not in progress:
            print(f"\nYou win! The word was {word.upper()}.")
            return True

        if errors >= max_errors:
            print(f"\nGame over. You used {max_errors} incorrect guesses.")
            print(f"The word was {word.upper()}.")
            return False


def play_again() -> bool:
    while True:
        answer = input("Play again or quit? (P/Q): ").strip().lower()
        if answer in {"p", "play", "y", "yes"}:
            return True
        if answer in {"q", "quit", "n", "no"}:
            return False
        print("Please enter P to play again or Q to quit.")


def main() -> None:
    print("Hangman (CLI)")
    print("Guess letters to reveal the hidden word.")

    language_name, words_file = prompt_language()
    difficulty_name, min_length, max_length, max_errors = prompt_difficulty()

    try:
        words = load_words(words_file)
        words = filter_words_for_difficulty(words, min_length, max_length)
    except Exception as exc:
        print(f"Could not start game: {exc}")
        return

    if not words:
        print(
            "Could not start game: no words match your selected language and difficulty."
        )
        return

    print(f"Language selected: {language_name}.")
    print(f"Difficulty selected: {difficulty_name} ({max_errors} max errors).")

    while True:
        run_round(words, max_errors)
        if not play_again():
            print("Thanks for playing.")
            break


if __name__ == "__main__":
    main()
