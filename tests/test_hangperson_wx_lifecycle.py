from pathlib import Path

import pytest

pytest.importorskip("wx")

import json

import hangperson_wx
from hangperson import HangpersonGame
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


class _FakeGuessSlotsFrame:
    EMPTY_BAD_GUESS_SLOT_LABEL = HangpersonFrame.EMPTY_BAD_GUESS_SLOT_LABEL

    def __init__(self, game: HangpersonGame, max_errors: int) -> None:
        self.game = game
        self.max_errors = max_errors


def test_bad_guess_slots_do_not_mark_greek_sigma_as_incorrect() -> None:
    game = HangpersonGame(word="κόσμος", max_errors=5)
    game.apply_guess("σ")
    frame = _FakeGuessSlotsFrame(game=game, max_errors=5)

    slots = HangpersonFrame._format_guessed_slots(frame)  # type: ignore[arg-type]

    assert slots == [HangpersonFrame.EMPTY_BAD_GUESS_SLOT_LABEL] * 5


def test_cycle_choice_wraps_around() -> None:
    assert HangpersonFrame._cycle_choice(["e", "f", "r", "el"], "el") == "e"
    assert HangpersonFrame._cycle_choice(["1", "2", "3"], "2") == "3"


class _FakeLanguageCycleFrame:
    LANGUAGE_CYCLE = HangpersonFrame.LANGUAGE_CYCLE

    def __init__(self) -> None:
        self.pending_language_key = "e"
        self.load_calls: list[str] = []
        self.saved = False
        self.applied = 0
        self.updated = 0
        self.refreshed = 0

        class _Draw:
            def __init__(self, outer: "_FakeLanguageCycleFrame") -> None:
                self.outer = outer

            def Refresh(self) -> None:
                self.outer.refreshed += 1

        self.draw_panel = _Draw(self)

    def _can_change_settings(self) -> bool:
        return True

    def _show_locked_settings_hint_once(self) -> None:
        raise AssertionError("Should not lock in setup mode.")

    def _load_ui_for_language(self, language_key: str) -> bool:
        self.load_calls.append(language_key)
        return True

    def _apply_localized_labels(self) -> None:
        self.applied += 1

    def _update_status_widgets(self) -> None:
        self.updated += 1

    def _save_preferences(self) -> None:
        self.saved = True


def test_language_badge_click_rotates_in_setup_mode() -> None:
    frame = _FakeLanguageCycleFrame()
    HangpersonFrame.on_language_badge_click(frame, None)  # type: ignore[arg-type]

    assert frame.pending_language_key == "f"
    assert frame.load_calls == ["f"]
    assert frame.applied == 1
    assert frame.updated == 1
    assert frame.refreshed == 1
    assert frame.saved is True


class _FakeRestartCancelFrame:
    UI_MODE_SETUP = HangpersonFrame.UI_MODE_SETUP
    UI_MODE_ACTIVE = HangpersonFrame.UI_MODE_ACTIVE

    def __init__(self) -> None:
        self.ui_mode = self.UI_MODE_ACTIVE
        self.game = HangpersonGame(word="planet", max_errors=6)
        self.game.apply_guess("x")
        self.ui = {"session_kept_current": "kept"}
        self.info_messages: list[str] = []
        self.pending_language_key = "e"
        self.pending_difficulty_key = "2"
        self.language_key = "e"
        self.difficulty_key = "2"
        self.enter_setup_calls = 0

    def _is_round_in_progress(self) -> bool:
        return True

    def _confirm_enter_setup_mode(self) -> bool:
        return False

    def _show_info(self, message: str, icon_flag: int = 0) -> None:  # noqa: ARG002
        self.info_messages.append(message)

    def _load_ui_for_language(self, language_key: str) -> bool:  # noqa: ARG002
        raise AssertionError("Should not load locale when restart is canceled.")

    def enter_setup_mode(self, *, reset_session: bool, show_hint: bool = True) -> None:  # noqa: ARG002
        self.enter_setup_calls += 1


def test_on_new_game_cancel_keeps_active_round() -> None:
    frame = _FakeRestartCancelFrame()
    HangpersonFrame.on_new_game(frame, None)  # type: ignore[arg-type]

    assert frame.info_messages == ["kept"]
    assert frame.enter_setup_calls == 0


class _FakePrefsFrame:
    def __init__(self, prefs_path, pending_language_key: str, pending_difficulty_key: str):
        self._path = prefs_path
        self.pending_language_key = pending_language_key
        self.pending_difficulty_key = pending_difficulty_key

    def _prefs_path(self):
        return self._path

    def _is_valid_language_key(self, key: str) -> bool:
        return HangpersonFrame._is_valid_language_key(key)

    def _is_valid_difficulty_key(self, key: str) -> bool:
        return HangpersonFrame._is_valid_difficulty_key(key)


def test_preferences_round_trip_and_invalid_fallback(tmp_path) -> None:
    path = tmp_path / "prefs.json"
    frame = _FakePrefsFrame(path, "el", "3")

    HangpersonFrame._save_preferences(frame)  # type: ignore[arg-type]
    assert json.loads(path.read_text(encoding="utf-8")) == {"language": "el", "difficulty": "3"}

    assert HangpersonFrame._load_preferences(frame) == ("el", "3")  # type: ignore[arg-type]

    path.write_text(json.dumps({"language": "zzz", "difficulty": "9"}), encoding="utf-8")
    assert HangpersonFrame._load_preferences(frame) == ("e", "2")  # type: ignore[arg-type]


def test_revealed_parts_for_errors_easy_medium_hard() -> None:
    assert HangpersonFrame._revealed_parts_for_errors(0, "1") == []
    assert HangpersonFrame._revealed_parts_for_errors(2, "1") == ["head", "left_eye"]
    assert HangpersonFrame._revealed_parts_for_errors(3, "2") == [
        "head",
        "left_eye",
        "right_eye",
        "nose",
        "mouth",
    ]
    assert HangpersonFrame._revealed_parts_for_errors(5, "3") == [
        "head",
        "left_eye",
        "right_eye",
        "nose",
        "mouth",
        "shirt",
        "left_arm",
        "right_arm",
    ]


class _FakeLayerStateFrame:
    UI_MODE_SETUP = HangpersonFrame.UI_MODE_SETUP
    UI_MODE_ACTIVE = HangpersonFrame.UI_MODE_ACTIVE
    CHARACTER_BASE_KEY = HangpersonFrame.CHARACTER_BASE_KEY
    CHARACTER_DEAD_KEY = HangpersonFrame.CHARACTER_DEAD_KEY

    def __init__(self, mode: str, errors: int, lost: bool, difficulty_key: str) -> None:
        self.ui_mode = mode
        self.difficulty_key = difficulty_key
        if mode == self.UI_MODE_SETUP:
            self.game = None
        else:
            game = HangpersonGame(word="planet", max_errors=10)
            game.errors = errors
            if lost:
                game.max_errors = errors
            self.game = game

    def _revealed_parts_for_errors(self, errors: int, difficulty_key: str) -> list[str]:
        return HangpersonFrame._revealed_parts_for_errors(errors, difficulty_key)


def test_current_character_layer_keys_setup_has_no_layers() -> None:
    frame = _FakeLayerStateFrame(mode=HangpersonFrame.UI_MODE_SETUP, errors=0, lost=False, difficulty_key="1")
    assert HangpersonFrame._current_character_layer_keys(frame) == ["silhouette"]  # type: ignore[arg-type]


def test_current_character_layer_keys_includes_dead_overlay_on_loss() -> None:
    frame = _FakeLayerStateFrame(mode=HangpersonFrame.UI_MODE_ACTIVE, errors=6, lost=True, difficulty_key="3")
    layers = HangpersonFrame._current_character_layer_keys(frame)  # type: ignore[arg-type]
    assert layers[0] == "silhouette"
    assert layers[-1] == "dead"


class _FakeAssetPathFrame:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _assets_root(self) -> Path:
        return self._root

    def _people_assets_root(self, language_key: str) -> Path:
        return HangpersonFrame._people_assets_root(self, language_key)  # type: ignore[misc]

    def _character_filename(self, language_key: str, asset_key: str) -> str:
        return HangpersonFrame._character_filename(language_key, asset_key)


def test_character_asset_path_resolution() -> None:
    frame = _FakeAssetPathFrame(Path("/tmp/assets/images"))
    assert (
        HangpersonFrame._character_asset_path(frame, "e", "head")  # type: ignore[arg-type]
        == Path("/tmp/assets/images/people/en/head_en.png")
    )


class _FakeBitmapLoadFrame:
    def __init__(self) -> None:
        self._character_bitmap_cache: dict[tuple[str, str, tuple[int, int]], object | None] = {}
        self.load_calls = 0

    def _character_asset_path(self, language_key: str, asset_key: str) -> Path:
        return Path(f"/does/not/exist/{language_key}/{asset_key}.png")

    def _load_scaled_bitmap(self, path: Path, size: tuple[int, int]):  # noqa: ARG002
        self.load_calls += 1
        return None


def test_load_character_bitmap_caches_missing_result() -> None:
    frame = _FakeBitmapLoadFrame()
    size = (320, 320)
    first = HangpersonFrame._load_character_bitmap(frame, "en", "head", size)  # type: ignore[arg-type]
    second = HangpersonFrame._load_character_bitmap(frame, "en", "head", size)  # type: ignore[arg-type]
    assert first is None
    assert second is None
    assert frame.load_calls == 1
