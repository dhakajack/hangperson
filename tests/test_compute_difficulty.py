from pathlib import Path

from tools.compute_difficulty import (
    CorpusStats,
    FeatureWeights,
    default_candidates_path,
    assign_bands,
    build_corpus_stats,
    extract_features,
    filter_candidates_by_frequency,
    load_candidates,
    load_frequency_data,
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


def test_load_frequency_data_reads_word_count_tsv(tmp_path: Path) -> None:
    freq = tmp_path / "freq.tsv"
    freq.write_text(
        "\n".join(
            [
                "word\tcount",
                "planet\t10",
                "dictionary\t2",
            ]
        ),
        encoding="utf-8",
    )
    data = load_frequency_data(freq)
    assert data.total_tokens == 12
    assert data.counts == {"planet": 10, "dictionary": 2}


def test_filter_candidates_by_frequency_supports_count_and_ppm(tmp_path: Path) -> None:
    freq = tmp_path / "freq.tsv"
    freq.write_text(
        "\n".join(
            [
                "word\tcount",
                "planet\t100",
                "dictionary\t10",
                "journey\t1",
            ]
        ),
        encoding="utf-8",
    )
    data = load_frequency_data(freq)
    candidates = ["planet", "dictionary", "journey", "missing"]

    by_count = filter_candidates_by_frequency(
        candidates,
        freq_data=data,
        min_frequency_count=10,
        min_frequency_per_million=0.0,
    )
    assert by_count == ["planet", "dictionary"]

    by_ppm = filter_candidates_by_frequency(
        candidates,
        freq_data=data,
        min_frequency_count=0,
        min_frequency_per_million=100000.0,  # 10% of 111 tokens => ceil(11.1) = 12
    )
    assert by_ppm == ["planet"]


def test_load_candidates_supports_greek_script_filtering(tmp_path: Path) -> None:
    candidates_file = tmp_path / "candidates_el.txt"
    candidates_file.write_text(
        "\n".join(
            [
                "αγάπη",
                "κόσμος",
                "planet",
            ]
        ),
        encoding="utf-8",
    )
    loaded = load_candidates(
        language_key="el",
        min_length=5,
        max_length=None,
        candidates_path=candidates_file,
        corpus_text="",
    )
    assert loaded == ["αγάπη", "κόσμοσ"]


def test_default_candidates_path_requires_explicit_greek_file() -> None:
    try:
        default_candidates_path("el")
    except ValueError as exc:
        assert "provide --candidates" in str(exc)
    else:
        raise AssertionError("Expected ValueError for Greek default candidates path.")


def test_load_frequency_data_casefolds_keys_for_greek_final_sigma(tmp_path: Path) -> None:
    freq = tmp_path / "freq_el.tsv"
    freq.write_text(
        "\n".join(
            [
                "word\tcount",
                "λογος\t7",
                "ΛΟΓΟΣ\t5",
            ]
        ),
        encoding="utf-8",
    )

    data = load_frequency_data(freq)
    assert data.total_tokens == 12
    # Both rows canonicalize to λογοσ via casefold.
    assert data.counts == {"λογοσ": 12}
