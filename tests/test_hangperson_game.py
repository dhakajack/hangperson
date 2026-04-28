from hangperson import (
    HangpersonGame,
    format_letter_for_display,
    is_letter_for_language,
    normalize_guess_for_language,
    resolve_language_choice,
)


def test_hangperson_game_tracks_correct_incorrect_and_repeat_guesses() -> None:
    game = HangpersonGame(word="planet", max_errors=3)

    assert game.guesses_remaining == 3
    assert game.guessed_display == "(none)"

    assert game.apply_guess("p") == "correct"
    assert game.progress == ["P", "-", "-", "-", "-", "-"]
    assert game.errors == 0

    assert game.apply_guess("x") == "incorrect"
    assert game.errors == 1
    assert game.guesses_remaining == 2

    assert game.apply_guess("x") == "repeat"
    assert game.errors == 1


def test_hangperson_game_win_and_loss_states() -> None:
    win_game = HangpersonGame(word="aba", max_errors=3)
    win_game.apply_guess("a")
    win_game.apply_guess("b")
    assert win_game.is_won() is True
    assert win_game.is_lost() is False

    loss_game = HangpersonGame(word="planet", max_errors=2)
    loss_game.apply_guess("x")
    loss_game.apply_guess("y")
    assert loss_game.is_lost() is True
    assert loss_game.is_won() is False


def test_resolve_language_choice_accepts_latin_and_cyrillic_for_russian() -> None:
    assert resolve_language_choice("r") == "r"
    assert resolve_language_choice("R") == "r"
    assert resolve_language_choice("р") == "r"
    assert resolve_language_choice("Р") == "r"
    assert resolve_language_choice("p") == "r"
    assert resolve_language_choice("P") == "r"
    assert resolve_language_choice("g") == "el"
    assert resolve_language_choice("el") == "el"
    assert resolve_language_choice("Ελληνικά") == "el"


def test_is_letter_for_language_respects_selected_script() -> None:
    assert is_letter_for_language("e", "e") is True
    assert is_letter_for_language("é", "f") is True
    assert is_letter_for_language("д", "r") is True
    assert is_letter_for_language("α", "el") is True

    assert is_letter_for_language("д", "e") is False
    assert is_letter_for_language("e", "r") is False
    assert is_letter_for_language("e", "el") is False
    assert is_letter_for_language("7", "e") is False


def test_greek_sigma_variants_are_treated_as_single_guess() -> None:
    game = HangpersonGame(word="κόσμος", max_errors=5)

    # Unicode casefold normalizes terminal sigma to standard sigma.
    guess1 = normalize_guess_for_language("ς", "el")
    assert guess1 == "σ"
    assert normalize_guess_for_language("Σ", "el") == "σ"
    assert game.apply_guess(guess1) == "correct"
    assert game.progress == ["-", "-", "Σ", "-", "-", "Σ"]

    # Entering either sigma variant again should count as repeat.
    guess2 = normalize_guess_for_language("σ", "el")
    assert guess2 == "σ"
    assert game.apply_guess(guess2) == "repeat"


def test_accented_latin_letters_display_with_accents() -> None:
    game = HangpersonGame(word="rivière", max_errors=5)

    assert game.apply_guess("e") == "correct"
    assert game.progress == ["-", "-", "-", "-", "-", "-", "E"]

    assert game.apply_guess("è") == "correct"
    assert game.progress == ["-", "-", "-", "-", "È", "-", "E"]

    assert game.apply_guess("é") == "incorrect"
    assert game.guessed_display == "E, È, É"


def test_format_letter_for_display_keeps_latin_diacritics_visible() -> None:
    assert format_letter_for_display("e") == "E"
    assert format_letter_for_display("é") == "É"
    assert format_letter_for_display("e\u0301") == "É"
    assert format_letter_for_display("ç") == "Ç"
    assert format_letter_for_display("σ") == "Σ"


def test_decomposed_accented_guess_matches_composed_word_letter() -> None:
    game = HangpersonGame(word="caféine", max_errors=5)
    guess = normalize_guess_for_language("e\u0301", "f")

    assert guess == "é"
    assert game.apply_guess(guess) == "correct"
    assert game.progress == ["-", "-", "-", "É", "-", "-", "-"]


def test_french_word_progress_uses_accented_word_letters() -> None:
    game = HangpersonGame(word="espérer", max_errors=10)
    for raw in ["e", "é", "s", "p", "r"]:
        game.apply_guess(normalize_guess_for_language(raw, "f"))

    assert game.progress == ["E", "S", "P", "É", "R", "E", "R"]
