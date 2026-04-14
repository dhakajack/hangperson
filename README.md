# Hangman CLI (Codex Starter Project)

A simple command-line Hangman game in Python.

## What it does

- Prompts for language at startup: English (`E`), French (`F`), or Russian (`R`)
- Prompts for difficulty after language: Easy (`E`), Medium (`M`), Hard (`H`)
- Picks a random word from the selected language file
- Filters words by difficulty:
  - Easy: 6-7 letters (10 max errors)
  - Medium: 8-9 letters (8 max errors)
  - Hard: 10+ letters (6 max errors)
- Uses only lowercase alphabetic words with at least 6 letters (Unicode supported)
- Ignores proper nouns by filtering out non-lowercase entries
- Shows hidden letters as hyphens (for example: `- - - - - -`)
- Accepts single-letter guesses from prompt `>`
- Reveals correct guesses in UPPERCASE
- Ends game after the difficulty-specific incorrect guess limit
- Prompts to play again or quit

## Run

```bash
python3 hangman.py
```

## Test (pytest)

Install dev dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python3 -m pytest -q
```

Simple TDD loop:

1. Add or update a test in `tests/`.
2. Run `python3 -m pytest -q` and watch it fail (red).
3. Change code to make it pass (green).
4. Refactor and rerun tests (still green).

## Customize word list

Edit language files in `data/` (`words_en.txt`, `words_fr.txt`, `words_ru.txt`) and add one word per line.

Rules applied by the loader:

- minimum length: 6
- letters only (`isalpha`, so accented and Cyrillic letters are allowed)
- lowercase only

## Suggested Codex practice prompts in VS Code

1. "Add ASCII hangman art that changes with each error."
2. "Track and display guessed letters in alphabetical order."
3. "Add a hint command (`?`) that reveals one unrevealed letter and costs 2 errors."
4. "Refactor into modules and add unit tests for word loading and guess handling."
