#!/usr/bin/env python3
"""wxPython GUI Hangman skeleton with the existing game engine."""

from __future__ import annotations

from pathlib import Path

import wx

from hangman import (
    DIFFICULTY_SETTINGS,
    LANGUAGE_SETTINGS,
    HangmanGame,
    choose_word,
    filter_words_for_difficulty,
    load_locale,
    load_words,
)


class HangmanFrame(wx.Frame):
    """Main GUI frame for the Hangman game."""

    def __init__(self) -> None:
        super().__init__(None, title="Hangman (wxPython)", size=(900, 560))
        self.SetMinSize((780, 500))

        self.ui: dict[str, object] = {}
        self.language_name = ""
        self.difficulty_name = ""
        self.words: list[str] = []
        self.max_errors = 0
        self.game: HangmanGame | None = None

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
        right_panel.SetBackgroundColour(wx.Colour(255, 245, 220))
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        guessed_title = wx.StaticText(right_panel, label="Guessed Letters")
        guessed_title.SetFont(wx.Font(wx.FontInfo(11).Bold()))

        self.guessed_list = wx.ListBox(right_panel, style=wx.LB_SINGLE)

        right_sizer.Add(guessed_title, 0, wx.ALL, 10)
        right_sizer.Add(self.guessed_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        right_panel.SetSizer(right_sizer)

        root_sizer.Add(left_panel, 7, wx.EXPAND)
        root_sizer.Add(right_panel, 3, wx.EXPAND | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)

        root.SetSizer(root_sizer)

    def _build_bottom_panel(self, panel: wx.Panel) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.status_label = wx.StaticText(panel, label="")
        self.word_label = wx.StaticText(panel, label="Word: -")
        self.word_label.SetFont(wx.Font(wx.FontInfo(14).Bold()))
        self.remaining_label = wx.StaticText(panel, label="Guesses remaining: 0")

        self.output_ctrl = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 120),
        )

        input_row = wx.BoxSizer(wx.HORIZONTAL)
        input_label = wx.StaticText(panel, label="Guess")
        self.guess_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.guess_input.SetMaxLength(1)
        self.guess_input.Bind(wx.EVT_TEXT_ENTER, self.on_submit_guess)

        self.submit_button = wx.Button(panel, label="Submit")
        self.submit_button.Bind(wx.EVT_BUTTON, self.on_submit_guess)

        self.new_game_button = wx.Button(panel, label="New Game")
        self.new_game_button.Bind(wx.EVT_BUTTON, self.on_new_game)

        input_row.Add(input_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        input_row.Add(self.guess_input, 1, wx.RIGHT, 8)
        input_row.Add(self.submit_button, 0, wx.RIGHT, 8)
        input_row.Add(self.new_game_button, 0)

        sizer.Add(self.status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.word_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.remaining_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.output_ctrl, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(input_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(sizer)

    def on_paint_draw_panel(self, _: wx.PaintEvent) -> None:
        dc = wx.PaintDC(self.draw_panel)
        dc.Clear()

        w, h = self.draw_panel.GetClientSize()
        dc.SetPen(wx.Pen(wx.Colour(90, 90, 90), 2))
        dc.SetBrush(wx.Brush(wx.Colour(240, 245, 255)))
        dc.DrawRectangle(12, 12, max(w - 24, 20), max(h - 24, 20))

        title = "Hangman Drawing Area"
        subtitle = "(placeholder for gallows + character)"
        if self.game is not None:
            subtitle = f"Errors: {self.game.errors} / {self.game.max_errors}"

        dc.SetTextForeground(wx.Colour(40, 60, 95))
        dc.DrawText(title, 28, 28)
        dc.DrawText(subtitle, 28, 54)

    def append_output(self, message: str) -> None:
        self.output_ctrl.AppendText(f"{message}\n")

    def start_session(self) -> bool:
        language_key = self.prompt_language_key()
        if language_key is None:
            return False

        settings = LANGUAGE_SETTINGS[language_key]
        self.language_name = str(settings["name"])

        try:
            self.ui = load_locale(Path(settings["locale_file"]))
            all_words = load_words(Path(settings["words_file"]))
        except Exception as exc:  # pragma: no cover - GUI error path
            wx.MessageBox(f"Could not start game: {exc}", "Error", wx.OK | wx.ICON_ERROR)
            return False

        difficulty_choice = self.prompt_difficulty_choice()
        if difficulty_choice is None:
            return False

        min_length, max_length, self.max_errors = DIFFICULTY_SETTINGS[difficulty_choice]
        self.words = filter_words_for_difficulty(all_words, min_length, max_length)
        self.difficulty_name = str(self.ui["difficulty_names"][difficulty_choice])

        if not self.words:
            wx.MessageBox(
                str(self.ui["no_words_error"]),
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return False

        self.status_label.SetLabel(
            f"Language: {self.language_name}    Difficulty: {self.difficulty_name}"
        )
        self.guessed_list.Clear()
        self.output_ctrl.Clear()

        self.start_new_round()
        return True

    def prompt_language_key(self) -> str | None:
        choices = [
            f"English (E)",
            f"Français (F)",
            f"Русский (Р)",
        ]
        language_keys = ["e", "f", "r"]

        dialog = wx.SingleChoiceDialog(
            self,
            "Choose language",
            "Language",
            choices,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            selection = dialog.GetSelection()
            return language_keys[selection]
        finally:
            dialog.Destroy()

    def prompt_difficulty_choice(self) -> str | None:
        choices = [
            f"1 - {self.ui['difficulty_names']['1']}",
            f"2 - {self.ui['difficulty_names']['2']}",
            f"3 - {self.ui['difficulty_names']['3']}",
        ]
        difficulty_keys = ["1", "2", "3"]

        dialog = wx.SingleChoiceDialog(
            self,
            str(self.ui["difficulty_prompt"]),
            "Difficulty",
            choices,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            selection = dialog.GetSelection()
            return difficulty_keys[selection]
        finally:
            dialog.Destroy()

    def start_new_round(self) -> None:
        self.game = HangmanGame(
            word=choose_word(self.words),
            max_errors=self.max_errors,
            guessed_none=str(self.ui["guessed_none"]),
        )

        self.append_output(str(self.ui["new_game"]))
        self._refresh_game_views()
        self.guess_input.SetFocus()

    def on_new_game(self, _: wx.CommandEvent) -> None:
        self.start_new_round()

    def on_submit_guess(self, _: wx.CommandEvent) -> None:
        if self.game is None:
            return

        guess = self.guess_input.GetValue().strip().lower()
        self.guess_input.Clear()

        if len(guess) != 1 or not guess.isalpha():
            self.append_output(str(self.ui["letter_invalid"]))
            return

        outcome = self.game.apply_guess(guess)

        if outcome == "repeat":
            self.append_output(str(self.ui["repeat_guess"]).format(letter=guess.upper()))
        elif outcome == "correct":
            self.append_output(str(self.ui["correct"]))
        else:
            self.append_output(str(self.ui["incorrect"]))

        self._refresh_game_views()

        if self.game.is_won():
            self.append_output(str(self.ui["win"]).format(word=self.game.word.upper()))
            self._set_guess_controls_enabled(False)
            self._prompt_replay_after_round()
            return

        if self.game.is_lost():
            self.append_output(str(self.ui["loss_summary"]).format(max_errors=self.max_errors))
            self.append_output(str(self.ui["loss_word"]).format(word=self.game.word.upper()))
            self._set_guess_controls_enabled(False)
            self._prompt_replay_after_round()

    def _prompt_replay_after_round(self) -> None:
        # Keep replay UX close to the CLI concept while using native dialog buttons.
        message = f"{self.ui['play_again_prompt']}\n\nUse Yes to play again, No to quit."
        replay = wx.MessageBox(
            message,
            "Round Complete",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if replay == wx.YES:
            self.start_new_round()
            return
        self.Close()

    def _set_guess_controls_enabled(self, enabled: bool) -> None:
        self.guess_input.Enable(enabled)
        self.submit_button.Enable(enabled)

    def _refresh_game_views(self) -> None:
        if self.game is None:
            return

        word_text = " ".join(self.game.progress)
        self.word_label.SetLabel(f"{self.ui['word_label']}: {word_text}")
        self.remaining_label.SetLabel(
            f"{self.ui['guesses_remaining_label']}: {self.game.guesses_remaining}"
        )

        sorted_letters = sorted(letter.upper() for letter in self.game.guessed_letters)
        self.guessed_list.Set(sorted_letters)

        self._set_guess_controls_enabled(True)
        self.draw_panel.Refresh()


def main() -> None:
    app = wx.App(False)
    frame = HangmanFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
