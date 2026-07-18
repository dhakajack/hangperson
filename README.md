# Hangperson

A multilingual Hangman variant in Python. This started as CLI-based proof-of-concept and ballooned into a GUI desktop version based on wxPython. Finally, it morphed again into a React/Vite application.

The game plays in English, French, Russian or Greek. As much as possible, it is icon-driven to keep the main interface independent of language, but all feedback to the player is rendered in the selected language. Game controls include a choice of difficulty (easy - medium - hard) and language. Type a guess; if it is correct, it will appear in the target word, if not, your number of remaining guesses goes down. On a graphic version, this is represented by body parts being drawn. When a full body is drawn, the game round is over. A score keeps track of how many rounds have been won with the currrent settings.

More about the development history on my blog: 
[text](https://blog.templaro.com/hangperson/)

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

## Web-based version

The `web/` directory contains a browser-based version of Hangperson built with React,
TypeScript, Vite, and Vitest. It reimplements the game/session logic for the browser
while reusing the shared project assets, localized UI strings, and score-based
difficulty TSV files from the top-level `assets/` and `data/` directories.

The web app supports the same four languages as the desktop/CLI versions:
English, French, Russian, and Greek. Language, difficulty, character artwork,
localized messages, score tracking, replay flow, and reset flow are handled in the
client.

To run the web app locally:

```bash
cd web
npm install
npm run dev
```

The dev and build scripts automatically run `npm run sync:assets`, which copies
the required static files into `web/public/`:

- `assets/images/`
- `data/locales/`
- `data/difficulty/`

Those copied files are generated local build inputs and are intentionally ignored
by git.

Useful web commands:

```bash
cd web
npm test -- --run
npm run lint
npm run build
```

By default, the Vite build assumes the app will be served from
`/games/hangperson/`. To build for another base path, set `VITE_BASE_PATH`:

```bash
cd web
VITE_BASE_PATH=/ npm run build
```

The repository also includes `deploy-web.sh`, which builds the web app and uses
`rsync` to publish `web/dist/` to the target configured in a local `.deploy.env`
file:

```bash
OPALSTACK_TARGET='user@server:/path/to/public_html/games/hangperson/'
```
