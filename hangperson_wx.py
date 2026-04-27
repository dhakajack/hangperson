#!/usr/bin/env python3
"""wxPython GUI Hangperson skeleton with inline setup flow."""

from __future__ import annotations

import json
from pathlib import Path

import wx
import wx.adv

from app_paths import assets_images_path
from hangperson import (
    DIFFICULTY_SETTINGS,
    LANGUAGE_SETTINGS,
    HangpersonGame,
    choose_word,
    is_letter_for_language,
    load_locale,
    load_words_for_session,
    normalize_guess_for_language,
)


class HangpersonFrame(wx.Frame):
    """Main GUI frame for the Hangperson game."""

    UI_MODE_SETUP = "setup"
    UI_MODE_ACTIVE = "active_round"
    UI_MODE_ROUND_COMPLETE = "round_complete"

    GUESS_SLOT_SYMBOL = "▯"
    LANGUAGE_IMAGE_SIZE = (120, 60)
    DIFFICULTY_IMAGE_SIZE = (120, 92)
    ACTION_BUTTON_IMAGE_SIZE = (27, 27)
    COLOR_BG_BASE = (242, 245, 249)
    COLOR_BG_DRAW = (232, 237, 245)
    COLOR_BG_BOTTOM = (236, 244, 236)
    COLOR_BG_STATUS = (232, 237, 243)
    COLOR_BG_BAD_GUESS_RAIL = (224, 231, 241)
    COLOR_BG_BAD_GUESS_SLOTS = (232, 238, 246)
    COLOR_BG_DRAW_SURFACE_TOP = (245, 248, 252)
    COLOR_BG_DRAW_SURFACE_BOTTOM = (234, 239, 247)
    COLOR_BORDER_DRAW_SURFACE = (108, 122, 141)
    COLOR_BORDER_DRAW_SURFACE_INNER = (171, 181, 195)
    COLOR_TEXT_PRIMARY = (22, 38, 53)
    COLOR_WORD_SLOT_BORDER = (28, 62, 89)
    COLOR_WORD_SLOT_FILL = (246, 252, 246)
    WORD_SLOTS_PANEL_MIN_HEIGHT = 60

    LANGUAGE_CYCLE = ["e", "f", "r", "el"]
    DIFFICULTY_CYCLE = ["1", "2", "3"]
    LANGUAGE_KEY_TO_ASSET_CODE = {
        "e": "en",
        "f": "fr",
        "r": "ru",
        "el": "el",
    }
    CHARACTER_BASE_KEY = "silhouette"
    CHARACTER_DEAD_KEY = "dead"
    CHARACTER_PART_KEYS = (
        "head",
        "left_eye",
        "right_eye",
        "nose",
        "mouth",
        "shirt",
        "left_arm",
        "right_arm",
        "left_leg",
        "right_leg",
    )
    REVEAL_GROUPS_BY_DIFFICULTY: dict[str, tuple[tuple[str, ...], ...]] = {
        # 10 steps
        "1": (
            ("head",),
            ("left_eye",),
            ("right_eye",),
            ("nose",),
            ("mouth",),
            ("shirt",),
            ("left_arm",),
            ("right_arm",),
            ("left_leg",),
            ("right_leg",),
        ),
        # 8 steps (eyes together, nose+mouth together)
        "2": (
            ("head",),
            ("left_eye", "right_eye"),
            ("nose", "mouth"),
            ("shirt",),
            ("left_arm",),
            ("right_arm",),
            ("left_leg",),
            ("right_leg",),
        ),
        # 6 steps (medium merges + both arms together + both legs together)
        "3": (
            ("head",),
            ("left_eye", "right_eye"),
            ("nose", "mouth"),
            ("shirt",),
            ("left_arm", "right_arm"),
            ("left_leg", "right_leg"),
        ),
    }

    def __init__(self) -> None:
        super().__init__(None, title="Hangperson (wxPython)", size=(900, 560))
        self.SetMinSize((780, 500))

        self.ui: dict[str, object] = {}
        self.ui_mode = self.UI_MODE_SETUP

        self.language_key = ""
        self.language_name = ""
        self.difficulty_key = ""
        self.difficulty_name = ""

        self.pending_language_key = ""
        self.pending_difficulty_key = ""

        self.words: list[str] = []
        self.max_errors = 0
        self.game: HangpersonGame | None = None
        self.session_rounds_played = 0
        self.session_rounds_won = 0
        self.script_warning_shown = False
        self.settings_lock_hint_shown = False
        self.round_input_enabled = False
        self.info_hide_timer: wx.CallLater | None = None
        self.message_label: wx.StaticText | None = None
        self.word_slot_cells: list[wx.StaticText] = []
        self.bad_guess_cells: list[wx.StaticText] = []
        self.language_badge_bitmap: wx.StaticBitmap | None = None
        self.language_badge_fallback: wx.StaticText | None = None
        self.difficulty_badge_bitmap: wx.StaticBitmap | None = None
        self.difficulty_badge_fallback: wx.StaticText | None = None
        self._character_bitmap_cache: dict[tuple[str, str, tuple[int, int]], wx.Bitmap | None] = {}

        self._build_layout()
        self.Centre()
        self.Bind(wx.EVT_SHOW, self._on_frame_show)

        self._initialize_setup_state()

    @staticmethod
    def _cycle_choice(options: list[str], current: str) -> str:
        if not options:
            return current
        if current not in options:
            return options[0]
        idx = options.index(current)
        return options[(idx + 1) % len(options)]

    @staticmethod
    def _is_valid_language_key(language_key: str) -> bool:
        return language_key in LANGUAGE_SETTINGS

    @staticmethod
    def _is_valid_difficulty_key(difficulty_key: str) -> bool:
        return difficulty_key in DIFFICULTY_SETTINGS

    @classmethod
    def _reveal_groups_for_difficulty(cls, difficulty_key: str) -> tuple[tuple[str, ...], ...]:
        return cls.REVEAL_GROUPS_BY_DIFFICULTY.get(difficulty_key, cls.REVEAL_GROUPS_BY_DIFFICULTY["2"])

    @classmethod
    def _revealed_parts_for_errors(cls, errors: int, difficulty_key: str) -> list[str]:
        if errors <= 0:
            return []
        groups = cls._reveal_groups_for_difficulty(difficulty_key)
        visible_groups = groups[: min(errors, len(groups))]
        parts: list[str] = []
        for group in visible_groups:
            parts.extend(group)
        return parts

    def _prefs_path(self) -> Path:
        config_dir = Path(wx.StandardPaths.Get().GetUserConfigDir()) / "codex1"
        return config_dir / "hangperson_wx_prefs.json"

    def _load_preferences(self) -> tuple[str, str]:
        default_language = "e"
        default_difficulty = "2"
        path = self._prefs_path()
        if not path.exists():
            return default_language, default_difficulty

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default_language, default_difficulty

        language_key = str(raw.get("language", default_language))
        difficulty_key = str(raw.get("difficulty", default_difficulty))

        if not self._is_valid_language_key(language_key):
            language_key = default_language
        if not self._is_valid_difficulty_key(difficulty_key):
            difficulty_key = default_difficulty
        return language_key, difficulty_key

    def _save_preferences(self) -> None:
        path = self._prefs_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "language": self.pending_language_key,
                "difficulty": self.pending_difficulty_key,
            }
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            # Preference persistence is best-effort.
            return

    def _initialize_setup_state(self) -> None:
        language_key, difficulty_key = self._load_preferences()
        self.pending_language_key = language_key
        self.pending_difficulty_key = difficulty_key

        if not self._load_ui_for_language(self.pending_language_key):
            self.Destroy()
            return

        self._apply_pending_difficulty()
        self.enter_setup_mode(reset_session=True, show_hint=False)

    def _load_ui_for_language(self, language_key: str) -> bool:
        settings = LANGUAGE_SETTINGS.get(language_key)
        if settings is None:
            return False

        try:
            self.ui = load_locale(Path(settings["locale_file"]))
        except Exception as exc:  # pragma: no cover - GUI error path
            wx.MessageBox(f"Could not start game: {exc}", "Error", wx.OK | wx.ICON_ERROR)
            return False

        self._apply_localized_labels()
        return True

    def _apply_pending_difficulty(self) -> None:
        min_length, max_length, max_errors = DIFFICULTY_SETTINGS[self.pending_difficulty_key]
        _ = min_length
        _ = max_length
        self.max_errors = max_errors

    def _build_layout(self) -> None:
        root = wx.Panel(self)
        root.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BASE))
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)

        gameplay_panel = wx.Panel(root)
        gameplay_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BASE))
        gameplay_sizer = wx.BoxSizer(wx.VERTICAL)

        self.draw_panel = wx.Panel(gameplay_panel)
        self.draw_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_DRAW))
        self.draw_panel.Bind(wx.EVT_PAINT, self.on_paint_draw_panel)

        self.bottom_panel = wx.Panel(gameplay_panel)
        self.bottom_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BOTTOM))
        self._build_bottom_panel(self.bottom_panel)

        gameplay_sizer.Add(self.draw_panel, 5, wx.EXPAND | wx.ALL, 8)
        gameplay_sizer.Add(self.bottom_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        gameplay_panel.SetSizer(gameplay_sizer)

        self.status_panel = wx.Panel(root)
        self.status_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_STATUS))
        self._build_status_panel(self.status_panel)
        self.status_panel.SetMinSize((170, -1))

        bad_guess_panel = wx.Panel(root)
        bad_guess_panel.SetMinSize((64, -1))
        bad_guess_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BAD_GUESS_RAIL))
        bad_guess_sizer = wx.BoxSizer(wx.VERTICAL)

        self.bad_guess_slots_panel = wx.Panel(bad_guess_panel)
        self.bad_guess_slots_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BAD_GUESS_SLOTS))
        self.bad_guess_slots_panel.SetMinSize((48, -1))
        slots_sizer = wx.BoxSizer(wx.VERTICAL)
        self.bad_guess_slots_panel.SetSizer(slots_sizer)

        bad_guess_sizer.Add(self.bad_guess_slots_panel, 1, wx.EXPAND | wx.ALL, 8)
        bad_guess_panel.SetSizer(bad_guess_sizer)

        root_sizer.Add(gameplay_panel, 1, wx.EXPAND)
        root_sizer.Add(self.status_panel, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        root_sizer.Add(bad_guess_panel, 0, wx.EXPAND | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)

        root.SetSizer(root_sizer)

    def _on_frame_show(self, event: wx.ShowEvent) -> None:
        if event.IsShown():
            # On GTK, setting button bitmaps before the native widget is fully shown
            # can trigger an assertion. Refresh button visuals once visible.
            self._configure_action_button()
            self._update_badge_tooltips()
        event.Skip()

    def _build_status_panel(self, panel: wx.Panel) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        score_row = wx.BoxSizer(wx.HORIZONTAL)
        self.trophy_label = wx.StaticText(panel, label="🏆")
        self.trophy_label.SetFont(wx.Font(wx.FontInfo(34)))
        self.score_fraction_label = wx.StaticText(panel, label="0\n—\n0", style=wx.ALIGN_CENTER)
        self.score_fraction_label.SetFont(wx.Font(wx.FontInfo(15).Bold()))
        self.score_fraction_label.SetForegroundColour(wx.Colour(*self.COLOR_TEXT_PRIMARY))

        score_row.Add(self.trophy_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        score_row.Add(self.score_fraction_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.language_badge_panel = wx.Panel(panel)
        self.language_badge_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_STATUS))
        self.language_badge_panel.SetMinSize((0, 66))
        language_badge_sizer = wx.BoxSizer(wx.VERTICAL)
        self.language_badge_bitmap = wx.StaticBitmap(
            self.language_badge_panel, bitmap=wx.Bitmap(1, 1)
        )
        self.language_badge_fallback = wx.StaticText(
            self.language_badge_panel, label="", style=wx.ALIGN_CENTER_HORIZONTAL
        )
        self.language_badge_fallback.SetFont(wx.Font(wx.FontInfo(18).Bold()))
        self.language_badge_fallback.SetForegroundColour(wx.Colour(*self.COLOR_TEXT_PRIMARY))
        language_badge_sizer.AddStretchSpacer(1)
        language_badge_sizer.Add(self.language_badge_bitmap, 0, wx.ALIGN_CENTER_HORIZONTAL)
        language_badge_sizer.Add(self.language_badge_fallback, 0, wx.ALIGN_CENTER_HORIZONTAL)
        language_badge_sizer.AddStretchSpacer(1)
        self.language_badge_panel.SetSizer(language_badge_sizer)

        self.difficulty_badge_panel = wx.Panel(panel)
        self.difficulty_badge_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_STATUS))
        self.difficulty_badge_panel.SetMinSize((0, 98))
        difficulty_badge_sizer = wx.BoxSizer(wx.VERTICAL)
        self.difficulty_badge_bitmap = wx.StaticBitmap(
            self.difficulty_badge_panel, bitmap=wx.Bitmap(1, 1)
        )
        self.difficulty_badge_fallback = wx.StaticText(
            self.difficulty_badge_panel, label="", style=wx.ALIGN_CENTER_HORIZONTAL
        )
        self.difficulty_badge_fallback.SetFont(wx.Font(wx.FontInfo(18).Bold()))
        self.difficulty_badge_fallback.SetForegroundColour(wx.Colour(*self.COLOR_TEXT_PRIMARY))
        difficulty_badge_sizer.AddStretchSpacer(1)
        difficulty_badge_sizer.Add(self.difficulty_badge_bitmap, 0, wx.ALIGN_CENTER_HORIZONTAL)
        difficulty_badge_sizer.Add(self.difficulty_badge_fallback, 0, wx.ALIGN_CENTER_HORIZONTAL)
        difficulty_badge_sizer.AddStretchSpacer(1)
        self.difficulty_badge_panel.SetSizer(difficulty_badge_sizer)

        self.new_game_button = wx.Button(panel, label="")
        self.new_game_button.Bind(wx.EVT_BUTTON, self.on_new_game)

        self.guess_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER | wx.TE_CENTER)
        self.guess_input.SetMaxLength(5)
        self.guess_input.SetMinSize((90, -1))
        self.guess_input.Bind(wx.EVT_TEXT_ENTER, self.on_submit_guess)
        self.guess_prompt_label = wx.StaticText(panel, label="")
        self.guess_prompt_label.SetFont(wx.Font(wx.FontInfo(10).Bold()))
        self.guess_prompt_label.SetForegroundColour(wx.Colour(*self.COLOR_TEXT_PRIMARY))

        guess_area = wx.BoxSizer(wx.VERTICAL)
        guess_area.Add(self.guess_prompt_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        guess_area.Add(self.guess_input, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # Keep middle elements tighter together while reserving larger outer margins.
        sizer.AddStretchSpacer(2)
        sizer.Add(score_row, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(self.language_badge_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        sizer.AddStretchSpacer(1)
        sizer.Add(
            self.difficulty_badge_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12
        )
        sizer.AddStretchSpacer(1)
        sizer.Add(self.new_game_button, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer.AddStretchSpacer(1)
        sizer.Add(guess_area, 0, wx.EXPAND)
        sizer.AddStretchSpacer(2)

        panel.SetSizer(sizer)

        self._bind_badge_click_targets()

    def _bind_badge_click_targets(self) -> None:
        targets: list[tuple[wx.Window | None, wx.PyEventBinder, callable]] = [
            (self.language_badge_panel, wx.EVT_LEFT_UP, self.on_language_badge_click),
            (self.language_badge_bitmap, wx.EVT_LEFT_UP, self.on_language_badge_click),
            (self.language_badge_fallback, wx.EVT_LEFT_UP, self.on_language_badge_click),
            (self.difficulty_badge_panel, wx.EVT_LEFT_UP, self.on_difficulty_badge_click),
            (self.difficulty_badge_bitmap, wx.EVT_LEFT_UP, self.on_difficulty_badge_click),
            (self.difficulty_badge_fallback, wx.EVT_LEFT_UP, self.on_difficulty_badge_click),
        ]
        for widget, event, handler in targets:
            if widget is not None:
                widget.Bind(event, handler)

    def _build_bottom_panel(self, panel: wx.Panel) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.message_label = wx.StaticText(panel, label="", style=wx.ALIGN_LEFT)
        self.message_label.SetMinSize((-1, 26))
        self.message_label.SetBackgroundColour(wx.Colour(255, 245, 207))
        self.message_label.SetForegroundColour(wx.Colour(120, 80, 0))

        left_row = wx.BoxSizer(wx.HORIZONTAL)

        self.word_slots_panel = wx.Panel(panel)
        self.word_slots_panel.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BOTTOM))
        # Reserve vertical space so the drawing area does not jump when slots appear.
        self.word_slots_panel.SetMinSize((-1, self.WORD_SLOTS_PANEL_MIN_HEIGHT))
        self.word_slots_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.word_slots_panel.SetSizer(self.word_slots_sizer)

        left_row.AddStretchSpacer(1)
        left_row.Add(self.word_slots_panel, 0, wx.ALIGN_CENTER_VERTICAL)
        left_row.AddStretchSpacer(1)

        if self.message_label is not None:
            sizer.Add(self.message_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(left_row, 1, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(sizer)

    def on_paint_draw_panel(self, _: wx.PaintEvent) -> None:
        dc = wx.PaintDC(self.draw_panel)
        dc.Clear()

        w, h = self.draw_panel.GetClientSize()
        outer_rect = wx.Rect(12, 12, max(w - 24, 20), max(h - 24, 20))
        # Gentle vertical gradient keeps focus without looking flat/debug-like.
        dc.GradientFillLinear(
            outer_rect,
            wx.Colour(*self.COLOR_BG_DRAW_SURFACE_TOP),
            wx.Colour(*self.COLOR_BG_DRAW_SURFACE_BOTTOM),
            wx.SOUTH,
        )
        dc.SetPen(wx.Pen(wx.Colour(*self.COLOR_BORDER_DRAW_SURFACE), 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(outer_rect)
        # Subtle inner keyline for card-like depth.
        inner_rect = wx.Rect(
            outer_rect.x + 4,
            outer_rect.y + 4,
            max(outer_rect.width - 8, 8),
            max(outer_rect.height - 8, 8),
        )
        dc.SetPen(wx.Pen(wx.Colour(*self.COLOR_BORDER_DRAW_SURFACE_INNER), 1))
        dc.DrawRectangle(inner_rect)
        self._paint_character_stack(dc=dc, panel_width=w, panel_height=h)

    @staticmethod
    def _character_filename(language_key: str, asset_key: str) -> str:
        code = HangpersonFrame.LANGUAGE_KEY_TO_ASSET_CODE.get(language_key, language_key)
        return f"{asset_key}_{code}.png"

    def _people_assets_root(self, language_key: str) -> Path:
        code = HangpersonFrame.LANGUAGE_KEY_TO_ASSET_CODE.get(language_key, language_key)
        return self._assets_root() / "people" / code

    def _character_asset_path(self, language_key: str, asset_key: str) -> Path:
        base_dir = self._people_assets_root(language_key)
        canonical = base_dir / self._character_filename(language_key, asset_key)
        if canonical.exists():
            return canonical
        # Compatibility fallback: allow part-only filenames without language suffix.
        fallback = base_dir / f"{asset_key}.png"
        if fallback.exists():
            return fallback
        return canonical

    def _load_character_bitmap(
        self, language_key: str, asset_key: str, target_size: tuple[int, int]
    ) -> wx.Bitmap | None:
        cache_key = (language_key, asset_key, target_size)
        if cache_key in self._character_bitmap_cache:
            return self._character_bitmap_cache[cache_key]
        bitmap = self._load_scaled_bitmap(self._character_asset_path(language_key, asset_key), target_size)
        self._character_bitmap_cache[cache_key] = bitmap
        return bitmap

    def _current_character_layer_keys(self) -> list[str]:
        if self.ui_mode == self.UI_MODE_SETUP:
            # Show base silhouette as setup preview.
            return [self.CHARACTER_BASE_KEY]
        if self.game is None:
            return []
        layers = [self.CHARACTER_BASE_KEY]
        layers.extend(self._revealed_parts_for_errors(self.game.errors, self.difficulty_key))
        if self.game.is_lost():
            layers.append(self.CHARACTER_DEAD_KEY)
        return layers

    def _paint_character_stack(self, dc: wx.PaintDC, panel_width: int, panel_height: int) -> None:
        layer_keys = self._current_character_layer_keys()
        if not layer_keys:
            return

        target_w = max(panel_width - 80, 24)
        target_h = max(panel_height - 120, 24)
        target_size = (target_w, target_h)
        language_key = self.pending_language_key if self.ui_mode == self.UI_MODE_SETUP else self.language_key
        if not language_key:
            return

        stacked_bitmaps: list[wx.Bitmap] = []
        for asset_key in layer_keys:
            bitmap = self._load_character_bitmap(language_key, asset_key, target_size)
            if bitmap is not None:
                stacked_bitmaps.append(bitmap)
        if not stacked_bitmaps:
            return

        draw_w = stacked_bitmaps[0].GetWidth()
        draw_h = stacked_bitmaps[0].GetHeight()
        x = max((panel_width - draw_w) // 2, 16)
        # Keep character visually grounded by anchoring near bottom of drawing surface.
        y = max(panel_height - draw_h - 34, 74)

        for bitmap in stacked_bitmaps:
            dc.DrawBitmap(bitmap, x, y, useMask=True)

    def start_session(self) -> bool:
        language_key = getattr(self, "pending_language_key", "")
        difficulty_choice = getattr(self, "pending_difficulty_key", "")
        if not language_key and hasattr(self, "prompt_language_key"):
            language_key = self.prompt_language_key()
        if not difficulty_choice and hasattr(self, "prompt_difficulty_choice"):
            difficulty_choice = self.prompt_difficulty_choice()
        if not language_key or not difficulty_choice:
            return False

        settings = LANGUAGE_SETTINGS[language_key]
        self.language_name = str(settings["name"])

        if hasattr(self, "_load_ui_for_language"):
            if not self._load_ui_for_language(language_key):
                return False
        else:
            self.ui = load_locale(Path(settings["locale_file"]))
            self._apply_localized_labels()

        min_length, max_length, self.max_errors = DIFFICULTY_SETTINGS[difficulty_choice]
        self.difficulty_name = str(self.ui["difficulty_names"][difficulty_choice])

        try:
            self.words, fallback_warning = load_words_for_session(
                language_key=language_key,
                words_file=Path(settings["words_file"]),
                difficulty_key=difficulty_choice,
                min_length=min_length,
                max_length=max_length,
            )
        except Exception as exc:  # pragma: no cover - GUI error path
            wx.MessageBox(
                str(self.ui["start_error"]).format(error=exc),
                str(self.ui["error_title"]),
                wx.OK | wx.ICON_ERROR,
            )
            return False

        if fallback_warning:
            self._show_info(
                str(self.ui["scored_words_fallback_warning"]).format(reason=fallback_warning),
                wx.ICON_INFORMATION,
                timeout_ms=5000,
            )

        if not self.words:
            wx.MessageBox(
                str(self.ui["no_words_error"]),
                str(self.ui["error_title"]),
                wx.OK | wx.ICON_ERROR,
            )
            return False

        self.language_key = language_key
        self.difficulty_key = difficulty_choice
        self.session_rounds_played = 0
        self.session_rounds_won = 0
        self._build_bad_guess_slots(self.max_errors)
        self._update_status_widgets()
        self._dismiss_info()
        if hasattr(self, "_save_preferences"):
            self._save_preferences()

        self.start_new_round()
        return True

    def enter_setup_mode(self, *, reset_session: bool, show_hint: bool = True) -> None:
        self.ui_mode = self.UI_MODE_SETUP
        self.game = None
        self.words = []
        self.script_warning_shown = False
        self.settings_lock_hint_shown = False

        self._set_guess_controls_enabled(False)
        self.guess_input.Clear()

        self._apply_pending_difficulty()
        self._build_word_slots(0)
        self._build_bad_guess_slots(self.max_errors)

        if reset_session:
            self.session_rounds_played = 0
            self.session_rounds_won = 0

        self._apply_localized_labels()
        self._update_status_widgets()
        self.draw_panel.Refresh()

        if show_hint:
            self._show_info(str(self.ui.get("setup_hint", "")), wx.ICON_INFORMATION, timeout_ms=2600)

    def start_new_round(self) -> None:
        self.game = HangpersonGame(
            word=choose_word(self.words),
            max_errors=self.max_errors,
            guessed_none=str(self.ui["guessed_none"]),
        )

        self.ui_mode = self.UI_MODE_ACTIVE
        self._configure_action_button()
        self._update_badge_tooltips()
        self._refresh_game_views()
        self.script_warning_shown = False
        self.settings_lock_hint_shown = False
        self.round_input_enabled = True
        self.guess_input.Clear()
        self.guess_input.SetFocus()

    def _can_change_settings(self) -> bool:
        return self.ui_mode == self.UI_MODE_SETUP

    def _show_locked_settings_hint_once(self) -> None:
        if self.settings_lock_hint_shown:
            return
        self._show_info(str(self.ui["settings_locked_hint"]), wx.ICON_INFORMATION)
        self.settings_lock_hint_shown = True

    def on_language_badge_click(self, _: wx.MouseEvent) -> None:
        if not self._can_change_settings():
            self._show_locked_settings_hint_once()
            return

        self.pending_language_key = HangpersonFrame._cycle_choice(
            HangpersonFrame.LANGUAGE_CYCLE, self.pending_language_key
        )
        if self._load_ui_for_language(self.pending_language_key):
            self._apply_localized_labels()
            self._update_status_widgets()
            self.draw_panel.Refresh()
            self._save_preferences()

    def on_difficulty_badge_click(self, _: wx.MouseEvent) -> None:
        if not self._can_change_settings():
            self._show_locked_settings_hint_once()
            return

        self.pending_difficulty_key = HangpersonFrame._cycle_choice(
            HangpersonFrame.DIFFICULTY_CYCLE, self.pending_difficulty_key
        )
        self._apply_pending_difficulty()
        self._build_bad_guess_slots(self.max_errors)
        self._apply_localized_labels()
        self._update_status_widgets()
        self.draw_panel.Refresh()
        self._save_preferences()

    def _confirm_enter_setup_mode(self) -> bool:
        dialog = wx.Dialog(self, title=str(self.ui["restart_confirm_title"]))
        dialog.SetMinSize((460, 190))

        outer = wx.BoxSizer(wx.VERTICAL)
        body = wx.StaticText(
            dialog,
            label=str(self.ui["restart_confirm_body"]),
            style=wx.ALIGN_CENTER,
        )
        body.Wrap(420)
        outer.Add(body, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.LEFT | wx.RIGHT, 12)
        outer.AddStretchSpacer(1)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        cancel_button = wx.BitmapButton(
            dialog,
            wx.ID_CANCEL,
            wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK, wx.ART_BUTTON, (20, 20)),
        )
        ok_button = wx.BitmapButton(
            dialog,
            wx.ID_OK,
            wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK, wx.ART_BUTTON, (20, 20)),
        )
        cancel_button.SetToolTip(str(self.ui["restart_confirm_cancel_button"]))
        ok_button.SetToolTip(str(self.ui["restart_confirm_ok_button"]))
        buttons.Add(cancel_button, 0, wx.RIGHT, 8)
        buttons.Add(ok_button, 0)

        def on_ok(_: wx.CommandEvent) -> None:
            dialog.EndModal(wx.ID_OK)

        def on_cancel(_: wx.CommandEvent) -> None:
            dialog.EndModal(wx.ID_CANCEL)

        ok_button.Bind(wx.EVT_BUTTON, on_ok)
        cancel_button.Bind(wx.EVT_BUTTON, on_cancel)
        dialog.SetEscapeId(wx.ID_CANCEL)
        dialog.SetDefaultItem(ok_button)
        ok_button.SetFocus()

        outer.Add(buttons, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)
        dialog.SetSizerAndFit(outer)
        try:
            return dialog.ShowModal() == wx.ID_OK
        finally:
            dialog.Destroy()

    def _is_round_in_progress(self) -> bool:
        if self.ui_mode != self.UI_MODE_ACTIVE or self.game is None:
            return False
        return not self.game.is_won() and not self.game.is_lost()

    def on_new_game(self, _: wx.CommandEvent) -> None:
        if self.ui_mode == self.UI_MODE_SETUP:
            if self.start_session():
                return
            return

        if self._is_round_in_progress() and not self._confirm_enter_setup_mode():
            self._show_info(str(self.ui["session_kept_current"]), wx.ICON_INFORMATION)
            return

        self.pending_language_key = self.language_key or self.pending_language_key
        self.pending_difficulty_key = self.difficulty_key or self.pending_difficulty_key
        if self.pending_language_key and not self._load_ui_for_language(self.pending_language_key):
            return
        self.enter_setup_mode(reset_session=True)

    def on_submit_guess(self, _: wx.CommandEvent) -> None:
        if not self.round_input_enabled or self.game is None:
            return

        guess = self.guess_input.GetValue().strip().lower()
        if len(guess) != 1 or not guess.isalpha():
            self._show_info(str(self.ui["letter_invalid"]))
            self.guess_input.SetFocus()
            self.guess_input.SelectAll()
            return

        self.guess_input.Clear()
        guess = normalize_guess_for_language(guess, self.language_key)
        if not is_letter_for_language(guess, self.language_key):
            # Soft warning only: accept the guess to avoid false negatives on WSL key layouts.
            if not self.script_warning_shown:
                self._show_info(str(self.ui["letter_wrong_script"]), wx.ICON_INFORMATION)
                self.script_warning_shown = True
        self._process_guess(guess)
        if self.round_input_enabled:
            self.guess_input.SetFocus()

    def _process_guess(self, guess: str) -> None:
        if self.game is None:
            return

        outcome = self.game.apply_guess(guess)

        self._refresh_game_views()

        if outcome == "repeat":
            self._show_info(str(self.ui["repeat_guess"]).format(letter=guess.upper()))
            return

        if self.game.is_won():
            self.ui_mode = self.UI_MODE_ROUND_COMPLETE
            self._record_round_result(won=True)
            round_summary = str(self.ui["win_short"])
            self._set_guess_controls_enabled(False)
            self._prompt_replay_after_round(round_summary)
            return

        if self.game.is_lost():
            self.ui_mode = self.UI_MODE_ROUND_COMPLETE
            self._record_round_result(won=False)
            round_summary = "\n".join(
                [
                    str(self.ui["loss_summary"]).format(max_errors=self.max_errors),
                    str(self.ui["loss_word"]).format(word=self.game.word.upper()),
                ]
            )
            self._set_guess_controls_enabled(False)
            self._prompt_replay_after_round(round_summary)

    def _prompt_replay_after_round(self, round_summary: str | None = None) -> None:
        replay = self._show_centered_round_complete_dialog(
            round_summary or "",
            str(self.ui["replay_prompt_label"]),
        )
        if replay:
            self.start_new_round()
            return
        self.Destroy()

    def _set_guess_controls_enabled(self, enabled: bool) -> None:
        self.round_input_enabled = enabled
        self.guess_input.Enable(enabled)

    def _show_centered_round_complete_dialog(
        self, round_summary: str, replay_label: str
    ) -> bool:
        dialog = wx.Dialog(self, title=str(self.ui["round_complete_title"]))
        dialog.SetMinSize((420, 180))

        outer = wx.BoxSizer(wx.VERTICAL)

        if round_summary.strip():
            summary_text = wx.StaticText(dialog, label=round_summary, style=wx.ALIGN_CENTER)
            summary_text.Wrap(380)
            outer.Add(summary_text, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.LEFT | wx.RIGHT, 12)

        prompt_row = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(dialog, label=replay_label)
        text.SetFont(wx.Font(wx.FontInfo(12).Bold()))

        prompt_row.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)

        outer.Add(prompt_row, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 10)
        outer.AddStretchSpacer(1)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        no_button = wx.BitmapButton(
            dialog,
            wx.ID_NO,
            wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK, wx.ART_BUTTON, (20, 20)),
        )
        yes_button = wx.BitmapButton(
            dialog,
            wx.ID_YES,
            wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK, wx.ART_BUTTON, (20, 20)),
        )
        no_button.SetToolTip(str(self.ui["play_again_no_button"]))
        yes_button.SetToolTip(str(self.ui["play_again_yes_button"]))
        buttons.Add(no_button, 0, wx.RIGHT, 8)
        buttons.Add(yes_button, 0)

        def on_yes(_: wx.CommandEvent) -> None:
            dialog.EndModal(wx.ID_YES)

        def on_no(_: wx.CommandEvent) -> None:
            dialog.EndModal(wx.ID_NO)

        yes_button.Bind(wx.EVT_BUTTON, on_yes)
        no_button.Bind(wx.EVT_BUTTON, on_no)
        dialog.SetEscapeId(wx.ID_NO)
        dialog.SetDefaultItem(yes_button)
        yes_button.SetFocus()

        outer.Add(buttons, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        dialog.SetSizerAndFit(outer)
        try:
            return dialog.ShowModal() == wx.ID_YES
        finally:
            dialog.Destroy()

    def _record_round_result(self, won: bool) -> None:
        self.session_rounds_played += 1
        if won:
            self.session_rounds_won += 1
        self._update_status_widgets()

    def _format_session_stats(self) -> str:
        percentage = 0.0
        if self.session_rounds_played > 0:
            percentage = (self.session_rounds_won * 100) / self.session_rounds_played
        return str(self.ui["session_stats_format"]).format(
            won=self.session_rounds_won,
            played=self.session_rounds_played,
            pct=f"{percentage:.0f}",
        )

    def _refresh_game_views(self) -> None:
        if self.game is None:
            return

        self._update_word_slots()
        self._update_bad_guess_slots()

        self._set_guess_controls_enabled(True)
        self.draw_panel.Refresh()

    def _configure_action_button(self) -> None:
        if self.ui_mode == self.UI_MODE_SETUP:
            start_icon: wx.Bitmap | None = None
            if self.IsShownOnScreen():
                start_icon = self._load_scaled_bitmap(
                    self._assets_root() / "buttons" / "start_rocket.png",
                    self.ACTION_BUTTON_IMAGE_SIZE,
                )
            try:
                if start_icon is not None:
                    self._set_action_button_bitmap(start_icon)
                    self.new_game_button.SetLabel("")
                else:
                    # Fallback when bitmap assets are unavailable or too early to set.
                    self._clear_action_button_bitmaps()
                    self.new_game_button.SetLabel(str(self.ui["start_button"]))
            except wx.PyAssertionError:
                # GTK-safe fallback if image widget is not ready yet.
                self._clear_action_button_bitmaps()
                self.new_game_button.SetLabel(str(self.ui["start_button"]))
            self.new_game_button.SetForegroundColour(wx.Colour(0, 110, 50))
            self.new_game_button.SetToolTip(str(self.ui["start_button"]))
        else:
            restart_icon: wx.Bitmap | None = None
            if self.IsShownOnScreen():
                restart_icon = self._load_scaled_bitmap(
                    self._assets_root() / "buttons" / "restart_arrow.png",
                    self.ACTION_BUTTON_IMAGE_SIZE,
                )
            self._clear_action_button_bitmaps()
            if restart_icon is not None:
                self._set_action_button_bitmap(restart_icon)
                self.new_game_button.SetLabel("")
            else:
                self.new_game_button.SetLabel("↻")
            self.new_game_button.SetForegroundColour(wx.Colour(0, 95, 200))
            self.new_game_button.SetToolTip(str(self.ui["new_game_button"]))
        self.new_game_button.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        self.new_game_button.SetMinSize((56, 44))
        self.new_game_button.Refresh()

    def _set_action_button_bitmap(self, bitmap: wx.Bitmap) -> None:
        set_methods = [
            "SetBitmap",
            "SetBitmapLabel",
            "SetBitmapCurrent",
            "SetBitmapPressed",
            "SetBitmapFocus",
        ]
        for method_name in set_methods:
            method = getattr(self.new_game_button, method_name, None)
            if method is None:
                continue
            try:
                method(bitmap)
            except Exception:
                continue

    def _clear_action_button_bitmaps(self) -> None:
        transparent = wx.Bitmap(1, 1)
        clear_methods = [
            "SetBitmap",
            "SetBitmapLabel",
            "SetBitmapCurrent",
            "SetBitmapPressed",
            "SetBitmapDisabled",
            "SetBitmapFocus",
        ]
        for method_name in clear_methods:
            method = getattr(self.new_game_button, method_name, None)
            if method is None:
                continue
            try:
                method(transparent)
            except Exception:
                continue

    def _update_badge_tooltips(self) -> None:
        if self.ui_mode == self.UI_MODE_SETUP:
            lang_tip = str(self.ui["language_click_hint"])
            diff_tip = str(self.ui["difficulty_click_hint"])
        else:
            lang_tip = str(self.ui["settings_locked_hint"])
            diff_tip = str(self.ui["settings_locked_hint"])

        for widget in [self.language_badge_panel, self.language_badge_bitmap, self.language_badge_fallback]:
            if widget is not None:
                widget.SetToolTip(lang_tip)

        for widget in [
            self.difficulty_badge_panel,
            self.difficulty_badge_bitmap,
            self.difficulty_badge_fallback,
        ]:
            if widget is not None:
                widget.SetToolTip(diff_tip)

    def _apply_localized_labels(self) -> None:
        self.SetTitle(str(self.ui["window_title"]))
        self.guess_input.SetToolTip(str(self.ui["guess_input_label"]))
        self.guess_prompt_label.SetLabel(str(self.ui["guess_prompt_label"]))
        score_tip = str(self.ui.get("score_tooltip", "Score: won / rounds played"))
        self.trophy_label.SetToolTip(score_tip)
        self.score_fraction_label.SetToolTip(score_tip)
        self._apply_game_area_tooltips()

        self._configure_action_button()
        self._update_badge_tooltips()

    def _apply_game_area_tooltips(self) -> None:
        incorrect_tip = str(self.ui.get("incorrect_guesses_tooltip", "Incorrect letters"))
        target_tip = str(self.ui.get("target_word_tooltip", "Guess this word"))
        self.word_slots_panel.SetToolTip(target_tip)
        self.bad_guess_slots_panel.SetToolTip(incorrect_tip)
        for cell in self.word_slot_cells:
            cell.SetToolTip(target_tip)
        for cell in self.bad_guess_cells:
            cell.SetToolTip(incorrect_tip)

    def _show_info(
        self, message: str, icon_flag: int = wx.ICON_WARNING, timeout_ms: int = 2200
    ) -> None:
        if self.message_label is None:
            return
        bg = wx.Colour(255, 245, 207)
        fg = wx.Colour(120, 80, 0)
        if icon_flag == wx.ICON_INFORMATION:
            bg = wx.Colour(229, 243, 255)
            fg = wx.Colour(31, 78, 121)
        self.message_label.SetBackgroundColour(bg)
        self.message_label.SetForegroundColour(fg)
        self.message_label.SetLabel(message)
        self.message_label.GetParent().Layout()
        if self.info_hide_timer is not None and self.info_hide_timer.IsRunning():
            self.info_hide_timer.Stop()
        self.info_hide_timer = wx.CallLater(timeout_ms, self._dismiss_info)

    def _dismiss_info(self) -> None:
        if self.message_label is None:
            return
        self.message_label.SetLabel("")
        self.message_label.GetParent().Layout()

    def _format_guessed_slots(self) -> list[str]:
        if self.game is None:
            return []

        incorrect_letters = sorted(
            letter.upper()
            for letter in self.game.guessed_letters
            if not self.game.word_contains_guess(letter)
        )
        remaining_slots = max(self.max_errors - len(incorrect_letters), 0)
        return incorrect_letters + [self.GUESS_SLOT_SYMBOL] * remaining_slots

    def _build_word_slots(self, slot_count: int) -> None:
        self.word_slots_sizer.Clear(delete_windows=True)
        self.word_slot_cells = []
        target_tip = str(self.ui.get("target_word_tooltip", "Guess this word"))
        self.word_slots_panel.SetToolTip(target_tip)
        for _ in range(slot_count):
            border = wx.Panel(self.word_slots_panel)
            border.SetBackgroundColour(wx.Colour(*self.COLOR_WORD_SLOT_BORDER))
            content = wx.Panel(border)
            content.SetBackgroundColour(wx.Colour(*self.COLOR_WORD_SLOT_FILL))
            content.SetMinSize((34, 48))

            inner = wx.StaticText(
                content,
                label="",
                style=wx.ALIGN_CENTER,
            )
            inner.SetToolTip(target_tip)
            inner.SetFont(wx.Font(wx.FontInfo(20).Bold()))
            inner.SetForegroundColour(wx.Colour(*self.COLOR_TEXT_PRIMARY))
            inner.SetMinSize((24, 30))

            content_sizer = wx.BoxSizer(wx.VERTICAL)
            content_sizer.AddStretchSpacer(1)
            content_sizer.Add(inner, 0, wx.ALIGN_CENTER)
            content_sizer.AddStretchSpacer(1)
            content.SetSizer(content_sizer)

            border_sizer = wx.BoxSizer(wx.VERTICAL)
            border_sizer.Add(content, 1, wx.EXPAND | wx.ALL, 1)
            border.SetSizer(border_sizer)
            border.SetMinSize((36, 50))

            self.word_slots_sizer.Add(border, 0, wx.RIGHT, 8)
            self.word_slot_cells.append(inner)
        self.word_slots_panel.Layout()

    def _update_word_slots(self) -> None:
        if self.game is None:
            return
        if len(self.word_slot_cells) != len(self.game.progress):
            self._build_word_slots(len(self.game.progress))
        for idx, char in enumerate(self.game.progress):
            self.word_slot_cells[idx].SetLabel("" if char == "-" else char)
        self.word_slots_panel.Layout()

    def _build_bad_guess_slots(self, slot_count: int) -> None:
        sizer = self.bad_guess_slots_panel.GetSizer()
        if sizer is None:
            return
        sizer.Clear(delete_windows=True)
        self.bad_guess_cells = []
        incorrect_tip = str(self.ui.get("incorrect_guesses_tooltip", "Incorrect letters"))
        self.bad_guess_slots_panel.SetToolTip(incorrect_tip)
        sizer.AddStretchSpacer(1)
        for _ in range(slot_count):
            slot = wx.StaticText(
                self.bad_guess_slots_panel,
                label=self.GUESS_SLOT_SYMBOL,
                style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE | wx.BORDER_SIMPLE,
            )
            slot.SetToolTip(incorrect_tip)
            slot.SetBackgroundColour(wx.Colour(*self.COLOR_BG_BAD_GUESS_SLOTS))
            slot.SetForegroundColour(wx.Colour(*self.COLOR_TEXT_PRIMARY))
            slot.SetMinSize((28, 40))
            slot.SetFont(wx.Font(wx.FontInfo(18).Bold()))
            sizer.Add(slot, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, 4)
            self.bad_guess_cells.append(slot)
        sizer.AddStretchSpacer(1)
        self.bad_guess_slots_panel.Layout()

    def _update_bad_guess_slots(self) -> None:
        letters = self._format_guessed_slots()
        if len(self.bad_guess_cells) != len(letters):
            self._build_bad_guess_slots(len(letters))
        for idx, value in enumerate(letters):
            self.bad_guess_cells[idx].SetLabel(value)
        self.bad_guess_slots_panel.Layout()

    def _display_language_key(self) -> str:
        if self.ui_mode == self.UI_MODE_SETUP:
            return self.pending_language_key
        return self.language_key

    def _display_difficulty_key(self) -> str:
        if self.ui_mode == self.UI_MODE_SETUP:
            return self.pending_difficulty_key
        return self.difficulty_key

    def _update_status_widgets(self) -> None:
        self.score_fraction_label.SetLabel(
            f"{self.session_rounds_won}\n—\n{self.session_rounds_played}"
        )
        self._set_language_badge(self._display_language_key())
        self._set_difficulty_badge(self._display_difficulty_key())
        self.status_panel.Layout()

    def _language_flag(self, key: str) -> str:
        return {
            "e": "🇺🇸",
            "f": "🇫🇷",
            "r": "🇷🇺",
            "el": "🇬🇷",
        }.get(key, "🏳️")

    def _difficulty_icon(self, key: str) -> str:
        return {
            "1": "👶",
            "2": "🎓",
            "3": "🧙",
        }.get(key, "❓")

    def _language_badge_text(self, key: str) -> str:
        return {
            "e": "EN",
            "f": "FR",
            "r": "RU",
            "el": "EL",
        }.get(key, "--")

    def _difficulty_badge_text(self, key: str) -> str:
        return {
            "1": "E",
            "2": "M",
            "3": "H",
        }.get(key, "?")

    def _assets_root(self) -> Path:
        return assets_images_path()

    def _load_scaled_bitmap(self, path: Path, size: tuple[int, int]) -> wx.Bitmap | None:
        if not path.exists():
            return None
        image = wx.Image(str(path), wx.BITMAP_TYPE_ANY)
        if not image.IsOk():
            return None
        max_w, max_h = size
        w, h = image.GetWidth(), image.GetHeight()
        if w <= 0 or h <= 0:
            return None
        scale = min(max_w / w, max_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return image.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()

    def _set_language_badge(self, key: str) -> None:
        if self.language_badge_bitmap is None or self.language_badge_fallback is None:
            return
        filename = {
            "e": "lang_en.png",
            "f": "lang_fr.png",
            "r": "lang_ru.png",
            "el": "lang_el.png",
        }.get(key, "")
        bitmap = (
            self._load_scaled_bitmap(
                self._assets_root() / "language" / filename,
                self.LANGUAGE_IMAGE_SIZE,
            )
            if filename
            else None
        )
        if bitmap is not None:
            self.language_badge_bitmap.SetBitmap(bitmap)
            self.language_badge_bitmap.Show()
            self.language_badge_fallback.Hide()
            return
        self.language_badge_bitmap.Hide()
        self.language_badge_fallback.SetLabel(self._language_badge_text(key))
        self.language_badge_fallback.Show()

    def _set_difficulty_badge(self, key: str) -> None:
        if self.difficulty_badge_bitmap is None or self.difficulty_badge_fallback is None:
            return
        filename = {
            "1": "difficulty_easy.png",
            "2": "difficulty_medium.png",
            "3": "difficulty_hard.png",
        }.get(key, "")
        bitmap = (
            self._load_scaled_bitmap(
                self._assets_root() / "difficulty" / filename,
                self.DIFFICULTY_IMAGE_SIZE,
            )
            if filename
            else None
        )
        if bitmap is not None:
            self.difficulty_badge_bitmap.SetBitmap(bitmap)
            self.difficulty_badge_bitmap.Show()
            self.difficulty_badge_fallback.Hide()
            return
        self.difficulty_badge_bitmap.Hide()
        self.difficulty_badge_fallback.SetLabel(self._difficulty_badge_text(key))
        self.difficulty_badge_fallback.Show()


def main() -> None:
    app = wx.App(False)
    frame = HangpersonFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()


# Backward compatibility for existing imports/tests.
HangmanFrame = HangpersonFrame
