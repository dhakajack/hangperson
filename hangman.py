#!/usr/bin/env python3
"""Simple CLI Hangman game."""

from __future__ import annotations

import random
from pathlib import Path

MAX_ERRORS = 10
WORDS_FILE = Path("data/words.txt")


def load_words(path: Path) -> list[str]:
    """Load lowercase English words with at least 6 letters."""
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
            print("Please enter a single letter (A-Z).")
            continue
        return guess


def run_round(words: list[str]) -> bool:
    word = choose_word(words)
    progress = ["-" for _ in word]
    guessed_letters: set[str] = set()
    errors = 0

    print("\nNew game started!")

    while True:
        print(f"\nWord: {format_progress(progress)}")
        print(f"Errors: {errors}/{MAX_ERRORS}")

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

        if errors >= MAX_ERRORS:
            print(f"\nGame over. You used {MAX_ERRORS} incorrect guesses.")
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
    try:
        words = load_words(WORDS_FILE)
    except Exception as exc:
        print(f"Could not start game: {exc}")
        return

    print("Hangman (CLI)")
    print("Guess letters to reveal the hidden word.")

    while True:
        run_round(words)
        if not play_again():
            print("Thanks for playing.")
            break


if __name__ == "__main__":
    main()
