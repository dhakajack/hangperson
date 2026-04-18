from tools.postprocess_wordlist import (
    MODE_ENGLISH_DROP_ACCENTED,
    MODE_FRENCH_DECOMPOSE_LIGATURES,
    MODE_GREEK_STRIP_DIACRITICS,
    MODE_RUSSIAN_REMOVE_PREREFORM,
    SCRIPT_CYRILLIC,
    SCRIPT_GREEK,
    SCRIPT_LATIN,
    contains_diacritic,
    decompose_french_ligatures,
    has_russian_prereform_letters,
    _is_english_ascii_word,
    _matches_script_whitelist,
    process_words,
    strip_diacritics,
)


def test_contains_diacritic() -> None:
    assert contains_diacritic("cafe\u0301")
    assert contains_diacritic("café")
    assert contains_diacritic("αγάπη")
    assert not contains_diacritic("cafe")
    assert not contains_diacritic("αγαπη")


def test_strip_diacritics() -> None:
    assert strip_diacritics("αγάπη") == "αγαπη"
    assert strip_diacritics("ΰψιλον") == "υψιλον"
    assert strip_diacritics("café") == "cafe"


def test_process_words_english_drop_accented() -> None:
    words = ["resume", "résumé", "naive", "naïve", "planet", "planet", ""]
    processed = process_words(words, MODE_ENGLISH_DROP_ACCENTED)
    assert processed == ["naive", "planet", "resume"]


def test_process_words_greek_strip_diacritics_and_dedupe() -> None:
    words = ["αγάπη", "αγαπη", "κόσμος", "κοσμος", ""]
    processed = process_words(words, MODE_GREEK_STRIP_DIACRITICS)
    assert processed == ["αγαπη", "κοσμος"]


def test_decompose_french_ligatures() -> None:
    assert decompose_french_ligatures("cœur") == "coeur"
    assert decompose_french_ligatures("Œuvre") == "OEuvre"
    assert decompose_french_ligatures("æon") == "aeon"


def test_process_words_french_decompose_ligatures_and_dedupe() -> None:
    words = ["cœur", "coeur", "Œuvre", "oeuvre", "æon", "aeon", ""]
    processed = process_words(words, MODE_FRENCH_DECOMPOSE_LIGATURES)
    assert processed == ["OEuvre", "aeon", "coeur", "oeuvre"]


def test_has_russian_prereform_letters() -> None:
    assert has_russian_prereform_letters("мір")
    assert has_russian_prereform_letters("Ѳома")
    assert has_russian_prereform_letters("сѵнод")
    assert not has_russian_prereform_letters("мир")
    assert not has_russian_prereform_letters("Фома")


def test_process_words_russian_remove_prereform() -> None:
    words = ["мир", "мір", "Фома", "Ѳома", "синод", "сѵнод", ""]
    processed = process_words(words, MODE_RUSSIAN_REMOVE_PREREFORM)
    assert processed == ["Фома", "мир", "синод"]


def test_script_whitelist_matching() -> None:
    assert _matches_script_whitelist("bonjour", SCRIPT_LATIN)
    assert _matches_script_whitelist("мир", SCRIPT_CYRILLIC)
    assert _matches_script_whitelist("αγαπη", SCRIPT_GREEK)
    assert not _matches_script_whitelist("агресcия", SCRIPT_CYRILLIC)
    assert not _matches_script_whitelist("oμoιoγεvως", SCRIPT_GREEK)


def test_english_ascii_word_check() -> None:
    assert _is_english_ascii_word("planet")
    assert _is_english_ascii_word("CamelCase")
    assert not _is_english_ascii_word("Aþena")
    assert not _is_english_ascii_word("naïve")


def test_process_words_with_script_ascii_and_caps_filters() -> None:
    words = ["NASA", "Hello", "HELLO", "Aþena", "bonjour", "агресcия", "мир"]
    processed = process_words(
        words,
        MODE_ENGLISH_DROP_ACCENTED,
        script_whitelist=SCRIPT_LATIN,
        english_strict_ascii=True,
        drop_all_caps=True,
    )
    assert processed == ["Hello", "bonjour"]
