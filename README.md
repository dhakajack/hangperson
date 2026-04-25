# Hangperson (wxPython Desktop Game)

A multilingual Hangman variant in Python with a wxPython desktop UI, conservative native-style widgets, and bundled image/data assets for English, French, Russian, and Greek play.

The CLI version is still included for development and debugging, but the main end-user target is now the desktop app in `hangperson_wx.py`.

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
- Canonicalizes guesses with Unicode `casefold()` before comparison (for example, Greek `ς` and `σ` are treated as the same letter)
- Ends game after the difficulty-specific incorrect guess limit
- Prompts with numeric replay controls: `1` to play again, `0` to quit

## Run The Desktop App

Install the app dependency once:

```bash
python3 -m pip install wxPython
```

Launch the GUI:

```bash
python3 hangperson_wx.py
```

## Run The CLI

```bash
python3 hangperson.py
```

## Test (pytest)

Install dev dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run tests:

```bash
python3 -m pytest -q
```

## Release / Packaging

The recommended release path for this project is **PyInstaller**, building **native artifacts on each target OS**:

- macOS: build a `.app` bundle first, then optionally wrap it in a `.dmg`
- Windows: build a windowed `.exe` distribution folder first, then optionally add an installer
- Linux: build a distribution folder first, then optionally add AppImage later

### Why PyInstaller first

- Good fit for a wxPython desktop app
- Handles bundled `assets/` and `data/` directories well
- Simpler and more proven for a first "double-click and run" release than Nuitka
- Lets you stabilize a bundle/app build before experimenting with one-file packaging

### Build workflow

This is best thought of as **release-time post-processing**. You can absolutely run the commands from the VS Code integrated terminal, but the build itself should happen on the target operating system:

- build macOS artifacts on macOS
- build Windows artifacts on Windows
- build Linux artifacts on Linux

### Install release tooling

```bash
python3 -m pip install -e ".[release]"
```

### Build with PyInstaller

Use the included spec file:

```bash
pyinstaller hangperson_wx.spec
```

This produces a windowed desktop build and bundles the project's `assets/` and `data/` directories with it.

### Output expectations

- macOS: `dist/Hangperson.app`
- Windows/Linux: `dist/Hangperson/`

### First release recommendation

Start with the default bundled build rather than true one-file packaging:

- easier to debug
- more reliable for wxPython
- fewer surprises around temporary extraction and asset loading

Once the bundled build is stable on each platform, you can optionally evaluate one-file mode or Nuitka as a second-stage experiment.

### Release smoke checks

Before publishing a build, verify:

- the app launches on a machine without a Python checkout of the repo
- language and difficulty badge images render
- character/body-part image assets load during gameplay
- locale JSON and difficulty TSV files are found
- the preferences file can be written in the user config directory
- the GUI launches without an unwanted terminal window
- at least one round completes in each supported language

Simple TDD loop:

1. Add or update a test in `tests/`.
2. Run `python3 -m pytest -q` and watch it fail (red).
3. Change code to make it pass (green).
4. Refactor and rerun tests (still green).

## Customize word list

Edit language files in `data/` (`words_en.txt`, `words_fr.txt`, `words_ru.txt`) and add one word per line.

### Word Entry Criteria

Use dictionary/base forms so word lists stay consistent and predictable across languages:

- Nouns: dictionary citation form.
  - English/French: singular.
  - Russian: nominative singular.
- Adjectives: dictionary citation form.
  - French: masculine singular.
  - Russian: long-form, masculine, nominative, singular.
- Verbs: dictionary citation form.
  - English/French: infinitive headword form (for example: `run`, `marcher`).
  - Russian: infinitive form; both imperfective and perfective infinitives are allowed.
- Lowercase only.
- Alphabetic characters only (`isalpha`), so avoid punctuation/apostrophes/hyphens.
- Avoid proper nouns, acronyms, and abbreviations.
- Keep one lemma per line (no duplicates).

Coverage target per language:

- Include enough words for all difficulty bands:
  - Easy: 6-7 letters
  - Medium: 8-9 letters
  - Hard: 10+ letters

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

## Difficulty Helper CLI

Scaffolded helper for corpus-driven difficulty scoring:

```bash
python3 tools/compute_difficulty.py \
  --language en \
  --corpus data/corpus_en.txt \
  --candidates data/words_en.txt \
  --min-length 6 \
  --output data/difficulty/en_difficulty.tsv
```

Key behavior:

- Uses corpus statistics to compute language-aware features:
  - letter rarity
  - unique-letter ratio
  - repetition ratio
  - bigram unpredictability
  - shortness adjustment
- Standardizes features (z-scores) within the candidate set.
- Produces a numeric score and a derived band (`easy`, `medium`, `hard`) in TSV output.
- If `--candidates` is omitted, candidates are mined from corpus tokens.

Output columns:

- `word`
- `length`
- `score`
- `band`
- `rarity`
- `unique_ratio`
- `repetition_ratio`
- `unpredictability`
- `shortness`

## End-to-End Difficulty Pipeline (Reproducible)

This project now has a full modular pipeline to build language difficulty TSVs.

### 1. Acquire Apertium dictionaries

Place source dictionary files in:

- `data/dictionaries/apertium/`

Expected source extensions:

- `*.dix`
- `*.metadix`

### 2. Extract lemma word lists from Apertium

```bash
python3 tools/extract_apertium_wordlists.py
```

This creates `*_wl.txt` files in `data/dictionaries/apertium/`.

### 3. Post-process dictionary lists

Current canonical clean outputs are:

- `apertium-eng.eng_wl_clean.txt`
- `apertium-fra.fra_wl_clean.txt`
- `apertium-rus.rus_wl_clean.txt`
- `apertium-ell.ell_wl_clean.txt`

Commands used:

```bash
python3 tools/postprocess_wordlist.py \
  --input data/dictionaries/apertium/apertium-eng.eng_wl.txt \
  --output data/dictionaries/apertium/apertium-eng.eng_wl_clean.txt \
  --mode english-drop-accented \
  --script-whitelist latin \
  --english-strict-ascii \
  --drop-all-caps \
  --lowercase-only
```

```bash
python3 tools/postprocess_wordlist.py \
  --input data/dictionaries/apertium/apertium-fra.fra_wl.txt \
  --output data/dictionaries/apertium/apertium-fra.fra_wl_clean.txt \
  --mode french-decompose-ligatures \
  --script-whitelist latin \
  --drop-all-caps \
  --lowercase-only
```

```bash
python3 tools/postprocess_wordlist.py \
  --input data/dictionaries/apertium/apertium-rus.rus_wl.txt \
  --output data/dictionaries/apertium/apertium-rus.rus_wl_clean.txt \
  --mode russian-remove-prereform \
  --script-whitelist cyrillic \
  --drop-all-caps \
  --lowercase-only
```

```bash
python3 tools/postprocess_wordlist.py \
  --input data/dictionaries/apertium/apertium-ell.ell_wl.txt \
  --output data/dictionaries/apertium/apertium-ell.ell_wl_clean.txt \
  --mode greek-strip-diacritics \
  --script-whitelist greek \
  --drop-all-caps \
  --lowercase-only
```

### 4. Download corpus samples

List languages:

```bash
python3 tools/download_mc4_corpus.py --list-languages
```

Download (default is currently 100 MB):

```bash
python3 tools/download_mc4_corpus.py --language en
python3 tools/download_mc4_corpus.py --language fr
python3 tools/download_mc4_corpus.py --language ru
python3 tools/download_mc4_corpus.py --language el
```

Large sample example:

```bash
python3 tools/download_mc4_corpus.py --language en --target-mb 1000
```

### 5. Normalize corpora (match dictionary cleanup rules)

Use `tools/normalize_corpus.py` to build:

- normalized token stream: `*_normalized.txt`
- token frequency table: `*_freq.tsv`

Example (100 MB files):

```bash
python3 -m tools.normalize_corpus \
  --input data/corpora/allenai_c4_en_100mb.txt \
  --output data/corpora/allenai_c4_en_100mb_normalized.txt \
  --language en \
  --frequency-output data/corpora/allenai_c4_en_100mb_freq.tsv
```

Repeat for `fr`, `ru`, and `el`.

Notes:

- Lowercasing is enabled by default in normalization.
- Use `--no-lowercase` only if you intentionally want case-sensitive output.

### 6. Compute difficulty TSV from clean dictionary + normalized corpus

Recommended baseline thresholds:

- `--min-length 6`
- `--max-length 12`
- `--min-frequency-count 5`
- `--min-frequency-per-million 10`

Greek typically needs a lower ppm threshold to keep enough words:

- `--min-frequency-per-million 5`

English:

```bash
python3 tools/compute_difficulty.py \
  --language en \
  --corpus data/corpora/allenai_c4_en_100mb_normalized.txt \
  --candidates data/dictionaries/apertium/apertium-eng.eng_wl_clean.txt \
  --freq-tsv data/corpora/allenai_c4_en_100mb_freq.tsv \
  --min-length 6 \
  --max-length 12 \
  --min-frequency-per-million 10 \
  --min-frequency-count 5 \
  --progress-every 5000 \
  --output data/difficulty/en_difficulty.tsv
```

French:

```bash
python3 tools/compute_difficulty.py \
  --language fr \
  --corpus data/corpora/allenai_c4_fr_100mb_normalized.txt \
  --candidates data/dictionaries/apertium/apertium-fra.fra_wl_clean.txt \
  --freq-tsv data/corpora/allenai_c4_fr_100mb_freq.tsv \
  --min-length 6 \
  --max-length 12 \
  --min-frequency-per-million 10 \
  --min-frequency-count 5 \
  --progress-every 5000 \
  --output data/difficulty/fr_difficulty.tsv
```

Russian:

```bash
python3 tools/compute_difficulty.py \
  --language ru \
  --corpus data/corpora/allenai_c4_ru_100mb_normalized.txt \
  --candidates data/dictionaries/apertium/apertium-rus.rus_wl_clean.txt \
  --freq-tsv data/corpora/allenai_c4_ru_100mb_freq.tsv \
  --min-length 6 \
  --max-length 12 \
  --min-frequency-per-million 10 \
  --min-frequency-count 5 \
  --progress-every 5000 \
  --output data/difficulty/ru_difficulty.tsv
```

Greek:

```bash
python3 tools/compute_difficulty.py \
  --language el \
  --corpus data/corpora/allenai_c4_el_100mb_normalized.txt \
  --candidates data/dictionaries/apertium/apertium-ell.ell_wl_clean.txt \
  --freq-tsv data/corpora/allenai_c4_el_100mb_freq.tsv \
  --min-length 6 \
  --max-length 12 \
  --min-frequency-per-million 5 \
  --min-frequency-count 5 \
  --progress-every 5000 \
  --output data/difficulty/el_difficulty.tsv
```

### 7. Optional manual review passes

- English US/UK variant flagging for manual cleanup:

```bash
python3 tools/flag_en_uk_us_variants.py \
  --input data/difficulty/en_difficulty.tsv \
  --output data/difficulty/en_difficulty_uk_us_flags.tsv
```
