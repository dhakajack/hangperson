from hangperson import HangpersonGame, is_letter_for_language, resolve_language_choice


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


def test_is_letter_for_language_respects_selected_script() -> None:
    assert is_letter_for_language("e", "e") is True
    assert is_letter_for_language("é", "f") is True
    assert is_letter_for_language("д", "r") is True

    assert is_letter_for_language("д", "e") is False
    assert is_letter_for_language("e", "r") is False
    assert is_letter_for_language("7", "e") is False
