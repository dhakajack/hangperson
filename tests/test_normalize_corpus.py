from pathlib import Path

from tools.normalize_corpus import normalize_corpus, normalize_token


def test_normalize_token_english_rules() -> None:
    assert normalize_token("planet", "en") == "planet"
    assert normalize_token("Planet", "en") == "planet"
    assert normalize_token("café", "en") is None
    assert normalize_token("Aþena", "en") is None


def test_normalize_token_french_rules() -> None:
    assert normalize_token("cœur", "fr") == "coeur"
    assert normalize_token("Œuvre", "fr") == "oeuvre"
    assert normalize_token("œuvre", "fr") == "oeuvre"
    assert normalize_token("hello", "fr") == "hello"


def test_normalize_token_russian_rules() -> None:
    assert normalize_token("мир", "ru") == "мир"
    assert normalize_token("Мир", "ru") == "мир"
    assert normalize_token("мір", "ru") is None
    assert normalize_token("агресcия", "ru") is None


def test_normalize_token_greek_rules() -> None:
    assert normalize_token("αγάπη", "el") == "αγαπη"
    assert normalize_token("Αγάπη", "el") == "αγαπη"
    assert normalize_token("κόσμος", "el") == "κοσμος"
    assert normalize_token("oμoιoγεvως", "el") is None


def test_normalize_corpus_and_frequency_output(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text(
        "Planet café planet\n"
        "Cœur oeuvre\n"
        "αγάπη κόσμος\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.txt"
    freq = tmp_path / "freq.tsv"

    total, kept = normalize_corpus(source, out, language="en", frequency_output=freq)
    assert total == 7
    assert kept == 3
    assert out.read_text(encoding="utf-8").splitlines() == ["planet", "planet", "oeuvre"]

    freq_lines = freq.read_text(encoding="utf-8").splitlines()
    assert freq_lines[0] == "word\tcount"
    assert freq_lines[1] == "planet\t2"
    assert freq_lines[2] == "oeuvre\t1"


def test_normalize_token_can_disable_lowercase() -> None:
    assert normalize_token("Planet", "en", lowercase=False) == "Planet"
    assert normalize_token("Œuvre", "fr", lowercase=False) == "OEuvre"
