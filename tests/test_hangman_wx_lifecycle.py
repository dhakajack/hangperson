import pytest

pytest.importorskip("wx")

from hangman_wx import HangmanFrame


class _FakeFrame:
    def __init__(self, replay: bool) -> None:
        self._replay = replay
        self.ui = {"replay_prompt_label": "Replay?"}
        self.new_round_calls = 0
        self.destroy_calls = 0
        self.last_message = ""

    def _show_centered_round_complete_dialog(self, message: str) -> bool:
        self.last_message = message
        return self._replay

    def start_new_round(self) -> None:
        self.new_round_calls += 1

    def Destroy(self) -> None:
        self.destroy_calls += 1


def test_round_complete_yes_starts_new_round() -> None:
    frame = _FakeFrame(replay=True)

    HangmanFrame._prompt_replay_after_round(frame)  # type: ignore[arg-type]

    assert frame.last_message == "Replay?"
    assert frame.new_round_calls == 1
    assert frame.destroy_calls == 0


def test_round_complete_no_destroys_frame() -> None:
    frame = _FakeFrame(replay=False)

    HangmanFrame._prompt_replay_after_round(frame)  # type: ignore[arg-type]

    assert frame.last_message == "Replay?"
    assert frame.new_round_calls == 0
    assert frame.destroy_calls == 1
