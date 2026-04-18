#!/usr/bin/env python3
"""wxPython GUI Hangperson skeleton with the existing game engine."""

from __future__ import annotations

from pathlib import Path

import wx
import wx.adv

from hangperson import (
    DIFFICULTY_SETTINGS,
    LANGUAGE_SETTINGS,
    HangpersonGame,
    choose_word,
    is_letter_for_language,
    load_locale,
    load_words_for_session,
)


class HangpersonFrame(wx.Frame):
    """Main GUI frame for the Hangperson game."""
    GUESS_SLOT_SYMBOL = "▯"
    LANGUAGE_IMAGE_SIZE = (120, 60)
    DIFFICULTY_IMAGE_SIZE = (120, 92)

    def __init__(self) -> None:
        super().__init__(None, title="Hangperson (wxPython)", size=(900, 560))
        self.SetMinSize((780, 500))

        self.ui: dict[str, object] = {}
        self.language_key = ""
        self.language_name = ""
        self.difficulty_key = ""
        self.difficulty_name = ""
        self.words: list[str] = []
        self.max_errors = 0
        self.game: HangpersonGame | None = None
        self.session_rounds_played = 0
        self.session_rounds_won = 0
        self.script_warning_shown = False
        self.round_input_enabled = True
        self.info_hide_timer: wx.CallLater | None = None
        self.message_label: wx.StaticText | None = None
        self.word_slot_cells: list[wx.StaticText] = []
        self.bad_guess_cells: list[wx.StaticText] = []
        self.language_badge_bitmap: wx.StaticBitmap | None = None
        self.language_badge_fallback: wx.StaticText | None = None
        self.difficulty_badge_bitmap: wx.StaticBitmap | None = None
        self.difficulty_badge_fallback: wx.StaticText | None = None

        self._build_layout()
        self.Centre()

        started = self.start_session()
        if not started:
            self.Destroy()

    def _build_layout(self) -> None:
        root = wx.Panel(self)
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)

        gameplay_panel = wx.Panel(root)
        gameplay_sizer = wx.BoxSizer(wx.VERTICAL)

        self.draw_panel = wx.Panel(gameplay_panel)
        self.draw_panel.SetBackgroundColour(wx.Colour(220, 235, 255))
        self.draw_panel.Bind(wx.EVT_PAINT, self.on_paint_draw_panel)

        self.bottom_panel = wx.Panel(gameplay_panel)
        self.bottom_panel.SetBackgroundColour(wx.Colour(225, 245, 225))
        self._build_bottom_panel(self.bottom_panel)

        gameplay_sizer.Add(self.draw_panel, 5, wx.EXPAND | wx.ALL, 8)
        gameplay_sizer.Add(self.bottom_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        gameplay_panel.SetSizer(gameplay_sizer)

        self.status_panel = wx.Panel(root)
        self.status_panel.SetBackgroundColour(wx.Colour(241, 236, 198))
        self._build_status_panel(self.status_panel)
        self.status_panel.SetMinSize((170, -1))

        bad_guess_panel = wx.Panel(root)
        bad_guess_panel.SetMinSize((64, -1))
        bad_guess_panel.SetBackgroundColour(wx.Colour(245, 248, 250))
        bad_guess_sizer = wx.BoxSizer(wx.VERTICAL)

        self.bad_guess_slots_panel = wx.Panel(bad_guess_panel)
        self.bad_guess_slots_panel.SetBackgroundColour(wx.Colour(250, 250, 250))
        self.bad_guess_slots_panel.SetMinSize((48, -1))
        slots_sizer = wx.BoxSizer(wx.VERTICAL)
        self.bad_guess_slots_panel.SetSizer(slots_sizer)

        bad_guess_sizer.Add(self.bad_guess_slots_panel, 1, wx.EXPAND | wx.ALL, 8)
        bad_guess_panel.SetSizer(bad_guess_sizer)

        root_sizer.Add(gameplay_panel, 1, wx.EXPAND)
        root_sizer.Add(self.status_panel, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)
        root_sizer.Add(bad_guess_panel, 0, wx.EXPAND | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)

        root.SetSizer(root_sizer)

    def _build_status_panel(self, panel: wx.Panel) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        score_row = wx.BoxSizer(wx.HORIZONTAL)
        self.trophy_label = wx.StaticText(panel, label="🏆")
        self.trophy_label.SetFont(wx.Font(wx.FontInfo(34)))
        self.score_fraction_label = wx.StaticText(panel, label="0\n—\n0", style=wx.ALIGN_CENTER)
        self.score_fraction_label.SetFont(wx.Font(wx.FontInfo(15).Bold()))

        score_row.Add(self.trophy_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        score_row.Add(self.score_fraction_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.language_badge_panel = wx.Panel(panel)
        self.language_badge_panel.SetBackgroundColour(wx.Colour(241, 236, 198))
        self.language_badge_panel.SetMinSize((0, 66))
        language_badge_sizer = wx.BoxSizer(wx.VERTICAL)
        self.language_badge_bitmap = wx.StaticBitmap(
            self.language_badge_panel, bitmap=wx.Bitmap(1, 1)
        )
        self.language_badge_fallback = wx.StaticText(
            self.language_badge_panel, label="", style=wx.ALIGN_CENTER_HORIZONTAL
        )
        self.language_badge_fallback.SetFont(wx.Font(wx.FontInfo(18).Bold()))
        self.language_badge_fallback.SetForegroundColour(wx.Colour(22, 38, 53))
        language_badge_sizer.AddStretchSpacer(1)
        language_badge_sizer.Add(self.language_badge_bitmap, 0, wx.ALIGN_CENTER_HORIZONTAL)
        language_badge_sizer.Add(self.language_badge_fallback, 0, wx.ALIGN_CENTER_HORIZONTAL)
        language_badge_sizer.AddStretchSpacer(1)
        self.language_badge_panel.SetSizer(language_badge_sizer)

        self.difficulty_badge_panel = wx.Panel(panel)
        self.difficulty_badge_panel.SetBackgroundColour(wx.Colour(241, 236, 198))
        self.difficulty_badge_panel.SetMinSize((0, 98))
        difficulty_badge_sizer = wx.BoxSizer(wx.VERTICAL)
        self.difficulty_badge_bitmap = wx.StaticBitmap(
            self.difficulty_badge_panel, bitmap=wx.Bitmap(1, 1)
        )
        self.difficulty_badge_fallback = wx.StaticText(
            self.difficulty_badge_panel, label="", style=wx.ALIGN_CENTER_HORIZONTAL
        )
        self.difficulty_badge_fallback.SetFont(wx.Font(wx.FontInfo(18).Bold()))
        self.difficulty_badge_fallback.SetForegroundColour(wx.Colour(22, 38, 53))
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
        self.guess_prompt_label.SetForegroundColour(wx.Colour(22, 38, 53))

        sizer.Add(score_row, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 12)
        sizer.Add(self.language_badge_panel, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 12)
        sizer.Add(
            self.difficulty_badge_panel, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 12
        )
        sizer.Add(self.new_game_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 12)
        sizer.AddStretchSpacer(1)
        sizer.Add(self.guess_prompt_label, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.AddSpacer(4)
        sizer.Add(self.guess_input, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        sizer.AddSpacer(12)

        panel.SetSizer(sizer)

    def _build_bottom_panel(self, panel: wx.Panel) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.message_label = wx.StaticText(panel, label="", style=wx.ALIGN_LEFT)
        self.message_label.SetMinSize((-1, 26))
        self.message_label.SetBackgroundColour(wx.Colour(255, 245, 207))
        self.message_label.SetForegroundColour(wx.Colour(120, 80, 0))

        left_row = wx.BoxSizer(wx.HORIZONTAL)

        self.word_slots_panel = wx.Panel(panel)
        self.word_slots_panel.SetBackgroundColour(wx.Colour(225, 245, 225))
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
        dc.SetPen(wx.Pen(wx.Colour(90, 90, 90), 2))
        dc.SetBrush(wx.Brush(wx.Colour(240, 245, 255)))
        dc.DrawRectangle(12, 12, max(w - 24, 20), max(h - 24, 20))

        title = str(self.ui.get("drawing_area_title", "Hangperson Drawing Area"))
        subtitle = str(
            self.ui.get(
                "drawing_area_placeholder",
                "(placeholder for gallows + character)",
            )
        )
        if self.game is not None:
            subtitle = str(
                self.ui.get(
                    "drawing_area_errors_format",
                    "Errors: {errors} / {max_errors}",
                )
            ).format(errors=self.game.errors, max_errors=self.game.max_errors)

        dc.SetTextForeground(wx.Colour(40, 60, 95))
        dc.DrawText(title, 28, 28)
        dc.DrawText(subtitle, 28, 54)

    def start_session(self) -> bool:
        language_key = self.prompt_language_key()
        if language_key is None:
            return False

        self.language_key = language_key
        settings = LANGUAGE_SETTINGS[language_key]
        self.language_name = str(settings["name"])

        try:
            self.ui = load_locale(Path(settings["locale_file"]))
        except Exception as exc:  # pragma: no cover - GUI error path
            wx.MessageBox(f"Could not start game: {exc}", "Error", wx.OK | wx.ICON_ERROR)
            return False

        self._apply_localized_labels()

        difficulty_choice = self.prompt_difficulty_choice()
        if difficulty_choice is None:
            return False

        min_length, max_length, self.max_errors = DIFFICULTY_SETTINGS[difficulty_choice]
        self.difficulty_key = difficulty_choice
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
        self.difficulty_name = str(self.ui["difficulty_names"][difficulty_choice])
        if fallback_warning:
            self._show_info(
                str(self.ui["scored_words_fallback_warning"]).format(
                    reason=fallback_warning
                ),
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

        self.session_rounds_played = 0
        self.session_rounds_won = 0
        self._build_bad_guess_slots(self.max_errors)
        self._update_status_widgets()
        self._dismiss_info()

        self.start_new_round()
        return True

    def prompt_language_key(self) -> str | None:
        choices = [
            "English",
            "Français",
            "Русский",
            "Ελληνικά",
        ]
        language_keys = ["e", "f", "r", "el"]
        selection = self._show_choice_dialog("Language", choices, min_size=(320, 240))
        if selection is None:
            return None
        return language_keys[selection]

    def prompt_difficulty_choice(self) -> str | None:
        choices = [
            str(self.ui["difficulty_names"]["1"]),
            str(self.ui["difficulty_names"]["2"]),
            str(self.ui["difficulty_names"]["3"]),
        ]
        difficulty_keys = ["1", "2", "3"]
        selection = self._show_choice_dialog(
            str(self.ui["difficulty_dialog_title"]),
            choices,
            prompt=str(self.ui["difficulty_prompt_gui"]),
        )
        if selection is None:
            return None
        return difficulty_keys[selection]

    def start_new_round(self) -> None:
        self.game = HangpersonGame(
            word=choose_word(self.words),
            max_errors=self.max_errors,
            guessed_none=str(self.ui["guessed_none"]),
        )

        self._refresh_game_views()
        self.script_warning_shown = False
        self.round_input_enabled = True
        self.guess_input.Clear()
        self.guess_input.SetFocus()

    def on_new_game(self, _: wx.CommandEvent) -> None:
        restarted = self.start_session()
        if restarted:
            return
        self._show_info(str(self.ui["session_kept_current"]), wx.ICON_INFORMATION)

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
            self._record_round_result(won=True)
            round_summary = str(self.ui["win_short"])
            self._set_guess_controls_enabled(False)
            self._prompt_replay_after_round(round_summary)
            return

        if self.game.is_lost():
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

    def _show_choice_dialog(
        self,
        title: str,
        choices: list[str],
        prompt: str = "",
        min_size: tuple[int, int] = (360, 260),
    ) -> int | None:
        dialog = wx.Dialog(self, title=title)
        dialog.SetMinSize(min_size)

        outer = wx.BoxSizer(wx.VERTICAL)
        if prompt.strip():
            prompt_text = wx.StaticText(dialog, label=prompt)
            outer.Add(prompt_text, 0, wx.ALL, 10)

        list_box = wx.ListBox(dialog, choices=choices)
        if choices:
            list_box.SetSelection(0)
        outer.Add(list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        cancel_button = wx.BitmapButton(
            dialog,
            wx.ID_CANCEL,
            wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK, wx.ART_BUTTON, (20, 20)),
        )
        confirm_button = wx.BitmapButton(
            dialog,
            wx.ID_OK,
            wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK, wx.ART_BUTTON, (20, 20)),
        )
        cancel_button.SetToolTip("Cancel")
        confirm_button.SetToolTip("Confirm")
        buttons.Add(cancel_button, 0, wx.RIGHT, 10)
        buttons.Add(confirm_button, 0)
        outer.Add(buttons, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        def on_confirm(_: wx.CommandEvent) -> None:
            if list_box.GetSelection() == wx.NOT_FOUND:
                return
            dialog.EndModal(wx.ID_OK)

        def on_cancel(_: wx.CommandEvent) -> None:
            dialog.EndModal(wx.ID_CANCEL)

        def on_double_click(_: wx.CommandEvent) -> None:
            on_confirm(_)

        confirm_button.Bind(wx.EVT_BUTTON, on_confirm)
        cancel_button.Bind(wx.EVT_BUTTON, on_cancel)
        list_box.Bind(wx.EVT_LISTBOX_DCLICK, on_double_click)
        dialog.SetEscapeId(wx.ID_CANCEL)
        dialog.SetDefaultItem(confirm_button)
        list_box.SetFocus()

        dialog.SetSizerAndFit(outer)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return list_box.GetSelection()
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

    def _apply_localized_labels(self) -> None:
        self.SetTitle(str(self.ui["window_title"]))
        self.guess_input.SetToolTip(str(self.ui["guess_input_label"]))
        self.guess_prompt_label.SetLabel(str(self.ui["guess_prompt_label"]))

        self.new_game_button.SetLabel("↻")
        self.new_game_button.SetForegroundColour(wx.Colour(0, 95, 200))
        self.new_game_button.SetToolTip(str(self.ui["new_game_button"]))
        self.new_game_button.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        self.new_game_button.SetMinSize((44, 34))

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
            if letter not in self.game.word
        )
        remaining_slots = max(self.max_errors - len(incorrect_letters), 0)
        return incorrect_letters + [self.GUESS_SLOT_SYMBOL] * remaining_slots

    def _build_word_slots(self, slot_count: int) -> None:
        self.word_slots_sizer.Clear(delete_windows=True)
        self.word_slot_cells = []
        for _ in range(slot_count):
            border = wx.Panel(self.word_slots_panel)
            border.SetBackgroundColour(wx.Colour(28, 62, 89))
            content = wx.Panel(border)
            content.SetBackgroundColour(wx.Colour(246, 252, 246))
            content.SetMinSize((34, 48))

            inner = wx.StaticText(
                content,
                label="",
                style=wx.ALIGN_CENTER,
            )
            inner.SetFont(wx.Font(wx.FontInfo(20).Bold()))
            inner.SetForegroundColour(wx.Colour(22, 38, 53))
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
        sizer.AddStretchSpacer(1)
        for _ in range(slot_count):
            slot = wx.StaticText(
                self.bad_guess_slots_panel,
                label=self.GUESS_SLOT_SYMBOL,
                style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE | wx.BORDER_SIMPLE,
            )
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

    def _update_status_widgets(self) -> None:
        self.score_fraction_label.SetLabel(
            f"{self.session_rounds_won}\n—\n{self.session_rounds_played}"
        )
        self._set_language_badge(self.language_key)
        self._set_difficulty_badge(self.difficulty_key)
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
        return Path(__file__).resolve().parent / "assets" / "images"

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
