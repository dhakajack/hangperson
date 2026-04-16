# Hangperson CLI (Codex Starter Project)

A simple command-line Hangperson game in Python.

## What it does

- Shows startup language chooser in English: `English (E), Français (F), Русский (Р)`
- Accepts either Latin `P/p` or Cyrillic `Р/р` for Russian selection
- Switches all in-game prompts/state text to the selected language
- Prompts for difficulty after language using numeric choices: `1` (Easy), `2` (Medium), `3` (Hard) with localized labels
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
- Prompts with numeric replay controls: `1` to play again, `0` to quit

## Run

```bash
python3 hangperson.py
```

## Run (wxPython GUI Skeleton)

Install wxPython (once):

```bash
python3 -m pip install wxPython
```

Run the GUI:

```bash
python3 hangperson_wx.py
```

The GUI currently uses tinted layout regions for development:
- left-top: drawing placeholder area
- left-bottom: game prompts/output and guess input
- right: guessed letters list (one letter per line)

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

## Add or edit UI languages

Localization strings live in `data/locales/`:

- `en.json`
- `fr.json`
- `ru.json`

To add a language, add:

1. A words file in `data/`
2. A locale JSON file in `data/locales/`
3. A `LANGUAGE_SETTINGS` entry in `hangperson.py`
4. Selection aliases in `LANGUAGE_ALIASES` (if needed)

Rules applied by the loader:

- minimum length: 6
- letters only (`isalpha`, so accented and Cyrillic letters are allowed)
- lowercase only
