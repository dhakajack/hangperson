import pytest

pytest.importorskip("wx")

from hangperson_wx import HangpersonFrame


class _FakeFrame:
    def __init__(self, replay: bool) -> None:
        self._replay = replay
        self.ui = {"replay_prompt_label": "Replay?"}
        self.new_round_calls = 0
        self.destroy_calls = 0
        self.last_summary = ""
        self.last_replay_label = ""

    def _show_centered_round_complete_dialog(
        self, round_summary: str, replay_label: str
    ) -> bool:
        self.last_summary = round_summary
        self.last_replay_label = replay_label
        return self._replay

    def start_new_round(self) -> None:
        self.new_round_calls += 1

    def Destroy(self) -> None:
        self.destroy_calls += 1


def test_round_complete_yes_starts_new_round() -> None:
    frame = _FakeFrame(replay=True)

    HangpersonFrame._prompt_replay_after_round(frame)  # type: ignore[arg-type]

    assert frame.last_summary == ""
    assert frame.last_replay_label == "Replay?"
    assert frame.new_round_calls == 1
    assert frame.destroy_calls == 0


def test_round_complete_no_destroys_frame() -> None:
    frame = _FakeFrame(replay=False)

    HangpersonFrame._prompt_replay_after_round(frame)  # type: ignore[arg-type]

    assert frame.last_summary == ""
    assert frame.last_replay_label == "Replay?"
    assert frame.new_round_calls == 0
    assert frame.destroy_calls == 1
