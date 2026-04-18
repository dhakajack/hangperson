from pathlib import Path

from tools.extract_apertium_wordlists import (
    extract_lemmas_from_file,
    is_valid_lemma,
    output_path_for,
)


def test_is_valid_lemma_filters_spaces_digits_and_punctuation() -> None:
    assert is_valid_lemma("Maison")
    assert is_valid_lemma("дом")
    assert is_valid_lemma("Ελλάδα")
    assert not is_valid_lemma("New York")
    assert not is_valid_lemma("alpha2")
    assert not is_valid_lemma("co-operate")
    assert not is_valid_lemma("l'été")


def test_extract_lemmas_from_file_deduplicates_and_filters(tmp_path: Path) -> None:
    source = tmp_path / "apertium-test.eng.dix"
    source.write_text(
        "\n".join(
            [
                '<e lm="planet"/>',
                '<e lm="planet"/>',
                '<e lm="multi word"/>',
                '<e lm="alpha2"/>',
                '<e lm="bonjour"/>',
                '<e lm="co-operate"/>',
            ]
        ),
        encoding="utf-8",
    )

    lemmas = extract_lemmas_from_file(source)
    assert lemmas == {"planet", "bonjour"}


def test_output_path_appends_wl_suffix(tmp_path: Path) -> None:
    source = Path("apertium-eng.eng.dix")
    out = output_path_for(source, tmp_path)
    assert out == tmp_path / "apertium-eng.eng_wl.txt"
