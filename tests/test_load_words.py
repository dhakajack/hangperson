from pathlib import Path

import pytest

from hangperson import LANGUAGE_SETTINGS, filter_words_for_difficulty, load_words


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


def test_load_words_keeps_lowercase_unicode_words(tmp_path: Path) -> None:
    words_file = tmp_path / "words.txt"
    words_file.write_text(
        "\n".join(
            [
                "rivière",  # valid lowercase French
                "машина",   # valid lowercase Russian
                "Bonjour",  # uppercase starts -> filtered
                "ПРИВЕТ",   # uppercase Russian -> filtered
            ]
        ),
        encoding="utf-8",
    )

    result = load_words(words_file)

    assert result == ["rivière", "машина"]


def test_filter_words_for_difficulty_by_length_band() -> None:
    words = ["planet", "mountain", "bluebird", "extraordinary"]

    assert filter_words_for_difficulty(words, 6, 7) == ["planet"]
    assert filter_words_for_difficulty(words, 8, 9) == ["mountain", "bluebird"]
    assert filter_words_for_difficulty(words, 10, None) == ["extraordinary"]


def test_word_lists_have_medium_and_hard_coverage() -> None:
    for settings in LANGUAGE_SETTINGS.values():
        words = load_words(Path(settings["words_file"]))
        medium_words = filter_words_for_difficulty(words, 8, 9)
        hard_words = filter_words_for_difficulty(words, 10, None)
        assert medium_words, f"Expected medium words in {settings['words_file']}"
        assert hard_words, f"Expected hard words in {settings['words_file']}"
