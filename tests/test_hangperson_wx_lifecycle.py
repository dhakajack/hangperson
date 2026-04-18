import pytest

pytest.importorskip("wx")

import hangperson_wx
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


class _FakeStartSessionFrame:
    def __init__(self) -> None:
        self.language_key = ""
        self.language_name = ""
        self.difficulty_key = ""
        self.difficulty_name = ""
        self.words: list[str] = []
        self.max_errors = 0
        self.ui: dict[str, object] = {}
        self.session_rounds_played = -1
        self.session_rounds_won = -1
        self.info_messages: list[str] = []
        self.started_round = 0

    def prompt_language_key(self) -> str | None:
        return "e"

    def prompt_difficulty_choice(self) -> str | None:
        return "2"

    def _apply_localized_labels(self) -> None:
        pass

    def _build_bad_guess_slots(self, _: int) -> None:
        pass

    def _update_status_widgets(self) -> None:
        pass

    def _dismiss_info(self) -> None:
        pass

    def start_new_round(self) -> None:
        self.started_round += 1

    def _show_info(
        self, message: str, icon_flag: int = 0, timeout_ms: int = 0  # noqa: ARG002
    ) -> None:
        self.info_messages.append(message)


def test_start_session_shows_fallback_warning_when_scored_source_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _FakeStartSessionFrame()

    monkeypatch.setattr(
        hangperson_wx,
        "load_locale",
        lambda _: {
            "difficulty_names": {"1": "Easy", "2": "Medium", "3": "Hard"},
            "no_words_error": "no words",
            "error_title": "error",
            "start_error": "{error}",
            "scored_words_fallback_warning": "fallback: {reason}",
        },
    )
    monkeypatch.setattr(
        hangperson_wx,
        "load_words_for_session",
        lambda **_: (["mountain"], "score source missing"),
    )

    started = HangpersonFrame.start_session(frame)  # type: ignore[arg-type]
    assert started is True
    assert frame.words == ["mountain"]
    assert frame.info_messages == ["fallback: score source missing"]
    assert frame.started_round == 1


def test_start_session_uses_scored_source_without_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _FakeStartSessionFrame()

    monkeypatch.setattr(
        hangperson_wx,
        "load_locale",
        lambda _: {
            "difficulty_names": {"1": "Easy", "2": "Medium", "3": "Hard"},
            "no_words_error": "no words",
            "error_title": "error",
            "start_error": "{error}",
            "scored_words_fallback_warning": "fallback: {reason}",
        },
    )
    monkeypatch.setattr(
        hangperson_wx,
        "load_words_for_session",
        lambda **_: (["mountain"], None),
    )

    started = HangpersonFrame.start_session(frame)  # type: ignore[arg-type]
    assert started is True
    assert frame.words == ["mountain"]
    assert frame.info_messages == []
    assert frame.started_round == 1
