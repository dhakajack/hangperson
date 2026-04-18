from tools.flag_en_uk_us_variants import flag_words, generate_variants


def test_generate_variants_detects_common_patterns() -> None:
    variants = dict(generate_variants("flavour"))
    assert variants.get("flavor") == "our_or"

    variants2 = dict(generate_variants("center"))
    assert variants2.get("centre") == "exact_pair_us_to_uk"


def test_flag_words_marks_presence_of_counterpart() -> None:
    words = ["flavour", "flavor", "analyze", "analyse", "planet"]
    rows = flag_words(words)

    by_pair = {(r["word"], r["variant"]): r for r in rows}
    assert by_pair[("flavour", "flavor")]["variant_in_input"] == "yes"
    assert by_pair[("flavor", "flavour")]["variant_in_input"] == "yes"
    assert by_pair[("analyze", "analyse")]["variant_in_input"] == "yes"


def test_flag_words_includes_missing_counterpart_case() -> None:
    words = ["favour", "planet"]
    rows = flag_words(words)
    row = next(r for r in rows if r["word"] == "favour" and r["variant"] == "favor")
    assert row["variant_in_input"] == "no"
