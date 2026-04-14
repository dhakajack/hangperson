from hangman import HangmanGame


def test_hangman_game_tracks_correct_incorrect_and_repeat_guesses() -> None:
    game = HangmanGame(word="planet", max_errors=3)

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


def test_hangman_game_win_and_loss_states() -> None:
    win_game = HangmanGame(word="aba", max_errors=3)
    win_game.apply_guess("a")
    win_game.apply_guess("b")
    assert win_game.is_won() is True
    assert win_game.is_lost() is False

    loss_game = HangmanGame(word="planet", max_errors=2)
    loss_game.apply_guess("x")
    loss_game.apply_guess("y")
    assert loss_game.is_lost() is True
    assert loss_game.is_won() is False
