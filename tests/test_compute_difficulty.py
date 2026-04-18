from pathlib import Path

from tools.compute_difficulty import (
    CorpusStats,
    FeatureWeights,
    assign_bands,
    build_corpus_stats,
    extract_features,
    load_candidates,
    score_features,
    write_tsv,
)


def test_build_corpus_stats_collects_language_letters() -> None:
    stats = build_corpus_stats("alpha beta gamma", "e")
    assert stats.total_letters > 0
    assert stats.letter_counts.get("a", 0) > 0


def test_load_candidates_filters_by_language_and_length(tmp_path: Path) -> None:
    candidates_file = tmp_path / "candidates.txt"
    candidates_file.write_text(
        "\n".join(
            [
                "planet",        # valid English
                "развитие",      # Cyrillic -> invalid for English
                "an",            # too short
                "dictionary",    # valid English hard
            ]
        ),
        encoding="utf-8",
    )
    loaded = load_candidates(
        language_key="e",
        min_length=6,
        max_length=None,
        candidates_path=candidates_file,
        corpus_text="",
    )
    assert loaded == ["planet", "dictionary"]


def test_scoring_pipeline_assigns_bands_and_writes_tsv(tmp_path: Path) -> None:
    corpus = "planet balance journey courage dictionary foundation challenge blueprint"
    stats: CorpusStats = build_corpus_stats(corpus, "e")
    words = ["planet", "balance", "journey", "dictionary", "foundation", "blueprint"]

    features = extract_features(words, stats)
    score_features(features, FeatureWeights())
    assign_bands(features)

    assert all(item.band in {"easy", "medium", "hard"} for item in features)

    output = tmp_path / "difficulty.tsv"
    write_tsv(features, output)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("word\tlength\tscore\tband")
    assert len(lines) == len(words) + 1

