from pathlib import Path

import pytest

from hangman import load_words


def test_load_words_filters_and_deduplicates(tmp_path: Path) -> None:
    words_file = tmp_path / "words.txt"
    words_file.write_text(
        "\n".join(
            [
                "planet",   # valid
                "planet",   # duplicate
                "London",   # proper noun (uppercase)
                "alpha",    # too short
                "number7",  # non-alphabetic
                "forest",   # valid
            ]
        ),
        encoding="utf-8",
    )

    result = load_words(words_file)

    assert result == ["planet", "forest"]


def test_load_words_raises_when_file_missing(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing_words.txt"

    with pytest.raises(FileNotFoundError):
        load_words(missing_file)
