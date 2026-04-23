#!/usr/bin/env python3
"""Compute language-aware Hangperson difficulty scores from corpus statistics."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hangperson import LANGUAGE_SETTINGS, is_letter_for_language


TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)
CLI_LANGUAGE_TO_INTERNAL: dict[str, str] = {
    "en": "e",
    "fr": "f",
    "ru": "r",
    "el": "el",
}


@dataclass(frozen=True)
class FeatureWeights:
    rarity: float = 0.35
    unique: float = 0.20
    repetition: float = -0.15
    unpredictability: float = 0.20
    shortness: float = 0.10


@dataclass
class CorpusStats:
    letter_counts: dict[str, int]
    bigram_counts: dict[str, int]
    bigram_starts: dict[str, int]
    total_letters: int

    @property
    def alphabet_size(self) -> int:
        return max(1, len(self.letter_counts))


@dataclass
class WordFeatures:
    word: str
    length: int
    rarity: float
    unique_ratio: float
    repetition_ratio: float
    unpredictability: float
    shortness: float
    score: float = 0.0
    band: str = ""


@dataclass(frozen=True)
class FrequencyData:
    counts: dict[str, int]
    total_tokens: int


def _letters_only_for_language(text: str, language_key: str) -> list[str]:
    letters: list[str] = []
    for char in text.casefold():
        if char.isalpha() and _is_letter_for_language_extended(char, language_key):
            letters.append(char)
    return letters


def _is_letter_for_language_extended(letter: str, language_key: str) -> bool:
    if language_key == "el":
        return "GREEK" in unicodedata.name(letter, "")
    return is_letter_for_language(letter, language_key)


def build_corpus_stats(corpus_text: str, language_key: str) -> CorpusStats:
    letters = _letters_only_for_language(corpus_text, language_key)
    if not letters:
        raise ValueError("No letters from selected language were found in corpus text.")

    letter_counts: dict[str, int] = {}
    for char in letters:
        letter_counts[char] = letter_counts.get(char, 0) + 1

    bigram_counts: dict[str, int] = {}
    bigram_starts: dict[str, int] = {}
    for prev, curr in zip(letters, letters[1:]):
        bigram = prev + curr
        bigram_counts[bigram] = bigram_counts.get(bigram, 0) + 1
        bigram_starts[prev] = bigram_starts.get(prev, 0) + 1

    return CorpusStats(
        letter_counts=letter_counts,
        bigram_counts=bigram_counts,
        bigram_starts=bigram_starts,
        total_letters=len(letters),
    )


def _tokenize_words(corpus_text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_RE.finditer(corpus_text)]


def _normalize_candidates(
    words: list[str], language_key: str, min_length: int, max_length: int | None
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in words:
        word = raw.strip().casefold()
        if not word or word in seen:
            continue
        if not word.isalpha():
            continue
        if any(not _is_letter_for_language_extended(char, language_key) for char in word):
            continue
        if len(word) < min_length:
            continue
        if max_length is not None and len(word) > max_length:
            continue
        normalized.append(word)
        seen.add(word)
    return normalized


def load_candidates(
    language_key: str,
    min_length: int,
    max_length: int | None,
    candidates_path: Path | None,
    corpus_text: str,
) -> list[str]:
    if candidates_path is not None:
        raw_words = candidates_path.read_text(encoding="utf-8").splitlines()
        return _normalize_candidates(raw_words, language_key, min_length, max_length)

    tokenized = _tokenize_words(corpus_text)
    return _normalize_candidates(tokenized, language_key, min_length, max_length)


def load_frequency_data(freq_tsv_path: Path) -> FrequencyData:
    counts: dict[str, int] = {}
    total_tokens = 0
    with freq_tsv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if not reader.fieldnames or "word" not in reader.fieldnames or "count" not in reader.fieldnames:
            raise ValueError(
                f"Frequency TSV must include 'word' and 'count' columns: {freq_tsv_path}"
            )
        for row in reader:
            # Keep frequency keys aligned with candidate normalization (casefold).
            word = str(row.get("word", "")).strip().casefold()
            if not word:
                continue
            count_text = str(row.get("count", "")).strip()
            try:
                count = int(count_text)
            except ValueError:
                continue
            if count <= 0:
                continue
            counts[word] = counts.get(word, 0) + count
            total_tokens += count
    if not counts:
        raise ValueError(f"No frequency rows were loaded from {freq_tsv_path}.")
    return FrequencyData(counts=counts, total_tokens=total_tokens)


def filter_candidates_by_frequency(
    candidates: list[str],
    freq_data: FrequencyData,
    min_frequency_count: int,
    min_frequency_per_million: float,
) -> list[str]:
    if min_frequency_count < 0:
        raise ValueError("min_frequency_count must be >= 0")
    if min_frequency_per_million < 0:
        raise ValueError("min_frequency_per_million must be >= 0")

    if min_frequency_count == 0 and min_frequency_per_million == 0:
        return candidates

    threshold_count = min_frequency_count
    if min_frequency_per_million > 0:
        ppm_count = math.ceil((min_frequency_per_million / 1_000_000) * freq_data.total_tokens)
        threshold_count = max(threshold_count, ppm_count)

    return [word for word in candidates if freq_data.counts.get(word, 0) >= threshold_count]


def _safe_log_prob(numerator: float, denominator: float) -> float:
    return -math.log(numerator / denominator)


def extract_features(
    words: list[str],
    stats: CorpusStats,
    progress_every: int = 0,
) -> list[WordFeatures]:
    features: list[WordFeatures] = []
    alphabet_size = stats.alphabet_size
    letter_den = stats.total_letters + alphabet_size
    total_words = len(words)
    started_at = time.perf_counter()

    for idx, word in enumerate(words, start=1):
        rarity_values: list[float] = []
        for char in word:
            char_count = stats.letter_counts.get(char, 0)
            rarity_values.append(_safe_log_prob(char_count + 1, letter_den))

        bigram_values: list[float] = []
        for prev, curr in zip(word, word[1:]):
            bigram = prev + curr
            start_total = stats.bigram_starts.get(prev, 0)
            bigram_count = stats.bigram_counts.get(bigram, 0)
            bigram_values.append(
                _safe_log_prob(bigram_count + 1, start_total + alphabet_size)
            )

        unique_ratio = len(set(word)) / len(word)
        repetition_ratio = 1.0 - unique_ratio
        unpredictability = sum(bigram_values) / len(bigram_values) if bigram_values else 0.0

        features.append(
            WordFeatures(
                word=word,
                length=len(word),
                rarity=sum(rarity_values) / len(rarity_values),
                unique_ratio=unique_ratio,
                repetition_ratio=repetition_ratio,
                unpredictability=unpredictability,
                shortness=1.0 / len(word),
            )
        )
        if progress_every > 0 and (idx % progress_every == 0 or idx == total_words):
            elapsed = time.perf_counter() - started_at
            rate = idx / elapsed if elapsed > 0 else 0.0
            remaining = (total_words - idx) / rate if rate > 0 else 0.0
            print(
                "[compute_difficulty] scoring progress: "
                f"{idx}/{total_words} ({(100.0 * idx / total_words):.1f}%), "
                f"elapsed={elapsed:.1f}s, eta={remaining:.1f}s",
                flush=True,
            )
    return features


def _zscores(values: list[float]) -> list[float]:
    if not values:
        return []
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return [0.0 for _ in values]
    return [(value - mean) / std for value in values]


def score_features(features: list[WordFeatures], weights: FeatureWeights) -> None:
    rarity_z = _zscores([item.rarity for item in features])
    unique_z = _zscores([item.unique_ratio for item in features])
    repetition_z = _zscores([item.repetition_ratio for item in features])
    unpredictability_z = _zscores([item.unpredictability for item in features])
    shortness_z = _zscores([item.shortness for item in features])

    for idx, item in enumerate(features):
        item.score = (
            (weights.rarity * rarity_z[idx])
            + (weights.unique * unique_z[idx])
            + (weights.repetition * repetition_z[idx])
            + (weights.unpredictability * unpredictability_z[idx])
            + (weights.shortness * shortness_z[idx])
        )


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return sorted_values[low]
    frac = pos - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * frac


def assign_bands(features: list[WordFeatures]) -> None:
    scores = sorted(item.score for item in features)
    low_cut = _quantile(scores, 1 / 3)
    high_cut = _quantile(scores, 2 / 3)
    for item in features:
        if item.score <= low_cut:
            item.band = "easy"
        elif item.score <= high_cut:
            item.band = "medium"
        else:
            item.band = "hard"


def write_tsv(rows: list[WordFeatures], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(
            [
                "word",
                "length",
                "score",
                "band",
                "rarity",
                "unique_ratio",
                "repetition_ratio",
                "unpredictability",
                "shortness",
            ]
        )
        for item in sorted(rows, key=lambda row: row.score, reverse=True):
            writer.writerow(
                [
                    item.word,
                    item.length,
                    f"{item.score:.6f}",
                    item.band,
                    f"{item.rarity:.6f}",
                    f"{item.unique_ratio:.6f}",
                    f"{item.repetition_ratio:.6f}",
                    f"{item.unpredictability:.6f}",
                    f"{item.shortness:.6f}",
                ]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute language-aware Hangperson difficulty scores from a corpus "
            "and a candidate word list."
        )
    )
    parser.add_argument(
        "--language",
        required=True,
        choices=sorted(CLI_LANGUAGE_TO_INTERNAL.keys()),
    )
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument(
        "--candidates",
        type=Path,
        default=None,
        help=(
            "Optional candidate list file (one word per line). "
            "If omitted, words are mined from corpus tokens."
        ),
    )
    parser.add_argument("--min-length", type=int, default=6)
    parser.add_argument("--max-length", type=int, default=0)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--freq-tsv",
        type=Path,
        default=None,
        help=(
            "Optional frequency TSV (word<TAB>count). "
            "When provided, candidates can be filtered by minimum frequency."
        ),
    )
    parser.add_argument(
        "--min-frequency-count",
        type=int,
        default=0,
        help="Minimum token count in --freq-tsv required to keep a candidate word.",
    )
    parser.add_argument(
        "--min-frequency-per-million",
        type=float,
        default=0.0,
        help=(
            "Minimum frequency per million tokens required to keep a candidate word. "
            "Applied against --freq-tsv totals."
        ),
    )
    parser.add_argument("--w-rarity", type=float, default=0.35)
    parser.add_argument("--w-unique", type=float, default=0.20)
    parser.add_argument("--w-repetition", type=float, default=-0.15)
    parser.add_argument("--w-unpredictability", type=float, default=0.20)
    parser.add_argument("--w-shortness", type=float, default=0.10)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=5000,
        help=(
            "Print scoring progress every N candidate words. "
            "Set to 0 to disable periodic progress output."
        ),
    )
    return parser.parse_args()


def default_candidates_path(language_key: str) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    if language_key == "el":
        raise ValueError(
            "No default Greek candidates file is configured. "
            "Please provide --candidates for language 'el'."
        )
    return repo_root / Path(str(LANGUAGE_SETTINGS[language_key]["words_file"]))


def main() -> None:
    args = parse_args()
    started_at = time.perf_counter()
    max_length = None if args.max_length <= 0 else args.max_length
    language_key = CLI_LANGUAGE_TO_INTERNAL[args.language]

    print(
        "[compute_difficulty] Starting run "
        f"(language={args.language}, corpus={args.corpus}, "
        f"candidates={args.candidates or 'default'}, output={args.output}).",
        flush=True,
    )
    print("[compute_difficulty] Reading corpus...", flush=True)
    corpus_text = args.corpus.read_text(encoding="utf-8")
    print("[compute_difficulty] Building corpus letter/bigram statistics...", flush=True)
    stats = build_corpus_stats(corpus_text, language_key)
    print(
        "[compute_difficulty] Corpus stats ready "
        f"(letters={stats.total_letters:,}, alphabet_size={stats.alphabet_size}).",
        flush=True,
    )

    candidates_path = args.candidates or default_candidates_path(language_key)
    print(f"[compute_difficulty] Loading candidates from {candidates_path}...", flush=True)
    candidates = load_candidates(
        language_key=language_key,
        min_length=args.min_length,
        max_length=max_length,
        candidates_path=candidates_path,
        corpus_text=corpus_text,
    )
    print(
        f"[compute_difficulty] Candidate pool after length/script filters: {len(candidates):,}.",
        flush=True,
    )
    frequency_filter_applied = False
    if args.freq_tsv is not None:
        print(f"[compute_difficulty] Loading frequencies from {args.freq_tsv}...", flush=True)
        freq_data = load_frequency_data(args.freq_tsv)
        print(
            "[compute_difficulty] Frequency rows loaded "
            f"(unique_words={len(freq_data.counts):,}, total_tokens={freq_data.total_tokens:,}).",
            flush=True,
        )
        before_count = len(candidates)
        candidates = filter_candidates_by_frequency(
            candidates,
            freq_data=freq_data,
            min_frequency_count=args.min_frequency_count,
            min_frequency_per_million=args.min_frequency_per_million,
        )
        after_count = len(candidates)
        frequency_filter_applied = (
            args.min_frequency_count > 0 or args.min_frequency_per_million > 0
        )
        if frequency_filter_applied:
            print(
                "[compute_difficulty] Frequency filter applied: "
                f"{before_count} -> {after_count} candidates "
                f"(min_count={args.min_frequency_count}, "
                f"min_ppm={args.min_frequency_per_million})."
                ,
                flush=True,
            )
    elif args.min_frequency_count > 0 or args.min_frequency_per_million > 0:
        raise SystemExit(
            "Frequency thresholds were provided without --freq-tsv. "
            "Provide --freq-tsv or set thresholds to zero."
        )

    if not candidates:
        raise SystemExit("No candidates remain after filtering. Check inputs and length bounds.")

    weights = FeatureWeights(
        rarity=args.w_rarity,
        unique=args.w_unique,
        repetition=args.w_repetition,
        unpredictability=args.w_unpredictability,
        shortness=args.w_shortness,
    )
    print(
        f"[compute_difficulty] Scoring {len(candidates):,} candidates "
        f"(progress_every={args.progress_every})...",
        flush=True,
    )
    features = extract_features(candidates, stats, progress_every=args.progress_every)
    print("[compute_difficulty] Assigning difficulty bands...", flush=True)
    score_features(features, weights)
    assign_bands(features)
    print(f"[compute_difficulty] Writing TSV to {args.output}...", flush=True)
    write_tsv(features, args.output)

    elapsed = time.perf_counter() - started_at
    print(
        f"[compute_difficulty] Done in {elapsed:.1f}s. "
        f"Wrote {len(features)} scored words to {args.output} "
        f"(language={args.language}, min_length={args.min_length}, max_length={max_length}, "
        f"frequency_filter={frequency_filter_applied})."
    )


if __name__ == "__main__":
    main()
