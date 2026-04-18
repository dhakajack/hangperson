from pathlib import Path

import pytest

from scored_words import ScoreWordSourceError, load_band_words_from_tsv


def test_load_band_words_from_tsv_validates_columns(tmp_path: Path) -> None:
    tsv = tmp_path / "difficulty.tsv"
    tsv.write_text("word\tscore\nplanet\t1.0\n", encoding="utf-8")

    with pytest.raises(ScoreWordSourceError):
        load_band_words_from_tsv(tsv, language_key="e", band="easy")


def test_load_band_words_from_tsv_filters_dedupes_and_returns_band_words(tmp_path: Path) -> None:
    tsv = tmp_path / "difficulty.tsv"
    tsv.write_text(
        "\n".join(
            [
                "word\tband\tscore",
                "planet\teasy\t0.1",
                "planet\teasy\t0.2",
                "forest\teasy\t0.3",
                "Forest\teasy\t0.4",
                "number7\teasy\t0.5",
                "mountain\tmedium\t0.6",
            ]
        ),
        encoding="utf-8",
    )

    words = load_band_words_from_tsv(tsv, language_key="e", band="easy")

    assert words == ["planet", "forest"]


def test_load_band_words_from_tsv_raises_for_empty_band(tmp_path: Path) -> None:
    tsv = tmp_path / "difficulty.tsv"
    tsv.write_text("word\tband\nplanet\teasy\n", encoding="utf-8")

    with pytest.raises(ScoreWordSourceError):
        load_band_words_from_tsv(tsv, language_key="e", band="hard")
