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
    filter_words_for_difficulty,
    is_letter_for_language,
    load_locale,
    load_words,
)


class HangpersonFrame(wx.Frame):
    """Main GUI frame for the Hangperson game."""
    GUESS_SLOT_SYMBOL = "▯"

    def __init__(self) -> None:
        super().__init__(None, title="Hangperson (wxPython)", size=(900, 560))
        self.SetMinSize((780, 500))

        self.ui: dict[str, object] = {}
        self.language_key = ""
        self.language_name = ""
        self.difficulty_name = ""
        self.words: list[str] = []
        self.max_errors = 0
        self.game: HangpersonGame | None = None
        self.session_rounds_played = 0
        self.session_rounds_won = 0
        self.script_warning_shown = False
        self.round_input_enabled = True
        self.info_hide_timer: wx.CallLater | None = None
        self.info_bar: wx.Window | None = None
        self.info_fallback_label: wx.StaticText | None = None

        self._build_layout()
        self.Centre()

        started = self.start_session()
        if not started:
            self.Destroy()

    def _build_layout(self) -> None:
        root = wx.Panel(self)
        root_sizer = wx.BoxSizer(wx.HORIZONTAL)

        left_panel = wx.Panel(root)
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        self.draw_panel = wx.Panel(left_panel)
        self.draw_panel.SetBackgroundColour(wx.Colour(220, 235, 255))
        self.draw_panel.Bind(wx.EVT_PAINT, self.on_paint_draw_panel)

        self.bottom_panel = wx.Panel(left_panel)
        self.bottom_panel.SetBackgroundColour(wx.Colour(225, 245, 225))
        self._build_bottom_panel(self.bottom_panel)

        left_sizer.Add(self.draw_panel, 3, wx.EXPAND | wx.ALL, 8)
        left_sizer.Add(self.bottom_panel, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        left_panel.SetSizer(left_sizer)

        right_panel = wx.Panel(root)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        self.guessed_list = wx.ListBox(right_panel, style=wx.LB_SINGLE)
        self.guessed_list.SetMinSize((70, -1))
        self.guessed_list.SetFont(wx.Font(wx.FontInfo(13).Bold()))

        right_sizer.Add(self.guessed_list, 1, wx.EXPAND | wx.ALL, 10)
        right_panel.SetSizer(right_sizer)

        root_sizer.Add(left_panel, 8, wx.EXPAND)
        root_sizer.Add(right_panel, 2, wx.EXPAND | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)

        root.SetSizer(root_sizer)

    def _build_bottom_panel(self, panel: wx.Panel) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.info_bar = self._create_info_widget(panel)
        self.status_label = wx.StaticText(panel, label="")
        self.session_label = wx.StaticText(panel, label="")
        self.word_label = wx.StaticText(panel, label="")
        self.word_label.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        self.input_hint_label = wx.StaticText(panel, label="")

        input_row = wx.BoxSizer(wx.HORIZONTAL)
        self.guess_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER | wx.TE_CENTER)
        self.guess_input.SetMaxLength(5)
        self.guess_input.SetMinSize((70, -1))
        self.guess_input.Bind(wx.EVT_TEXT_ENTER, self.on_submit_guess)

        self.submit_button = wx.Button(panel, label="")
        self.submit_button.Bind(wx.EVT_BUTTON, self.on_submit_guess)

        self.new_game_button = wx.Button(panel, label="")
        self.new_game_button.Bind(wx.EVT_BUTTON, self.on_new_game)

        input_row.Add(self.guess_input, 0, wx.RIGHT, 8)
        input_row.Add(self.submit_button, 0, wx.RIGHT, 8)
        input_row.AddStretchSpacer(1)
        input_row.Add(self.new_game_button, 0)

        if self.info_bar is not None:
            sizer.Add(self.info_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.session_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.word_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.input_hint_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(input_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

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
            all_words = load_words(Path(settings["words_file"]))
        except Exception as exc:  # pragma: no cover - GUI error path
            wx.MessageBox(f"Could not start game: {exc}", "Error", wx.OK | wx.ICON_ERROR)
            return False

        self._apply_localized_labels()

        difficulty_choice = self.prompt_difficulty_choice()
        if difficulty_choice is None:
            return False

        min_length, max_length, self.max_errors = DIFFICULTY_SETTINGS[difficulty_choice]
        self.words = filter_words_for_difficulty(all_words, min_length, max_length)
        self.difficulty_name = str(self.ui["difficulty_names"][difficulty_choice])

        if not self.words:
            wx.MessageBox(
                str(self.ui["no_words_error"]),
                str(self.ui["error_title"]),
                wx.OK | wx.ICON_ERROR,
            )
            return False

        language_status = str(self.ui["language_selected"]).format(language=self.language_name)
        difficulty_status = str(self.ui["difficulty_selected"]).format(
            difficulty=self.difficulty_name, max_errors=self.max_errors
        )
        self.status_label.SetLabel(f"{language_status}    {difficulty_status}")
        self.session_rounds_played = 0
        self.session_rounds_won = 0
        self.session_label.SetLabel(self._format_session_stats())
        self.guessed_list.Clear()
        self._dismiss_info()

        self.start_new_round()
        return True

    def prompt_language_key(self) -> str | None:
        choices = [
            "English",
            "Français",
            "Русский",
        ]
        language_keys = ["e", "f", "r"]
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
            round_summary = " ".join(
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
        self.submit_button.Enable(enabled)

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
        replay_icon = wx.StaticText(dialog, label="↻")
        replay_icon.SetFont(wx.Font(wx.FontInfo(18).Bold()))
        replay_icon.SetForegroundColour(wx.Colour(0, 95, 200))
        text = wx.StaticText(dialog, label=replay_label)
        text.SetFont(wx.Font(wx.FontInfo(12).Bold()))

        prompt_row.Add(replay_icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
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
        self.session_label.SetLabel(self._format_session_stats())

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

        word_text = " ".join(self.game.progress)
        self.word_label.SetLabel(f"{self.ui['word_label']}: {word_text}")

        self.guessed_list.Set(self._format_guessed_slots())

        self._set_guess_controls_enabled(True)
        self.draw_panel.Refresh()

    def _apply_localized_labels(self) -> None:
        self.SetTitle(str(self.ui["window_title"]))
        self.input_hint_label.SetLabel(str(self.ui["keyboard_input_hint"]))
        self.guess_input.SetToolTip(str(self.ui["guess_input_label"]))

        self.submit_button.SetLabel("↵")
        self.submit_button.SetForegroundColour(wx.Colour(0, 0, 0))
        self.submit_button.SetToolTip(str(self.ui["submit_button"]))
        self.submit_button.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        self.submit_button.SetMinSize((44, 34))

        self.new_game_button.SetLabel("↻")
        self.new_game_button.SetForegroundColour(wx.Colour(0, 95, 200))
        self.new_game_button.SetToolTip(str(self.ui["new_game_button"]))
        self.new_game_button.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        self.new_game_button.SetMinSize((44, 34))

    def _show_info(
        self, message: str, icon_flag: int = wx.ICON_WARNING, timeout_ms: int = 2200
    ) -> None:
        if self.info_bar is None:
            return
        show_message = getattr(self.info_bar, "ShowMessage", None)
        if callable(show_message):
            show_message(message, icon_flag)
        elif self.info_fallback_label is not None:
            self.info_fallback_label.SetLabel(message)
            self.info_fallback_label.Show()
            self.info_fallback_label.GetParent().Layout()
        if self.info_hide_timer is not None and self.info_hide_timer.IsRunning():
            self.info_hide_timer.Stop()
        self.info_hide_timer = wx.CallLater(timeout_ms, self._dismiss_info)

    def _create_info_widget(self, parent: wx.Window) -> wx.Window:
        info_bar_cls = getattr(wx.adv, "InfoBar", None) or getattr(wx, "InfoBar", None)
        if info_bar_cls is not None:
            return info_bar_cls(parent)

        # Fallback for wx builds that do not expose InfoBar.
        self.info_fallback_label = wx.StaticText(parent, label="")
        self.info_fallback_label.SetBackgroundColour(wx.Colour(255, 245, 207))
        self.info_fallback_label.SetForegroundColour(wx.Colour(120, 80, 0))
        self.info_fallback_label.Hide()
        return self.info_fallback_label

    def _dismiss_info(self) -> None:
        if self.info_bar is None:
            return
        dismiss = getattr(self.info_bar, "Dismiss", None)
        if callable(dismiss):
            dismiss()
            return
        if self.info_fallback_label is not None:
            self.info_fallback_label.Hide()
            self.info_fallback_label.GetParent().Layout()

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


def main() -> None:
    app = wx.App(False)
    frame = HangpersonFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()


# Backward compatibility for existing imports/tests.
HangmanFrame = HangpersonFrame
