#!/usr/bin/env python
from __future__ import annotations
import typing
import urwid


def get_stats_widget(stats: dict = {}) -> urwid.Pile:
    """Stats to display: chars stats (all, correct, %), word stats (all, correct, %), wpm."""
    n_chars = stats['n_chars'] if 'n_chars' in stats else ''
    n_chars_correct = stats['n_correct_chars'] if 'n_correct_chars' in stats else ''
    n_chars_correct_pct = stats['correct_chars_pct'] if 'correct_chars_pct' in stats else ''
    n_words = stats['n_words'] if 'n_words' in stats else ''
    n_words_correct = stats['n_correct_words'] if 'n_correct_words' in stats else ''
    n_words_correct_pct = stats['correct_words_pct'] if 'correct_words_pct' in stats else ''
    wpm = stats['wpm'] if 'wpm' in stats else ''

    char_stats = urwid.Columns([
        (22, urwid.Text(f"chars: {n_chars_correct}/{n_chars} ({n_chars_correct_pct}%)")),
    ])
    word_stats = urwid.Columns([
        (22, urwid.Text(f"words: {n_words_correct}/{n_words} ({n_words_correct_pct}%)")),
    ])
    wpm = urwid.Columns([
        (10, urwid.Text(f"wpm: {wpm}")),
    ])
    return urwid.Pile([char_stats, word_stats, wpm])


class PopUpDialog(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button"""

    signals: typing.ClassVar[list[str]] = ["close"]

    def __init__(self, stats: typing.Optional[dict], stats_widget):
        def on_retry_clicked(_button: urwid.Button) -> typing.NoReturn:
            self._emit("close")
            stats_widget.contents = [(get_stats_widget(stats), stats_widget.options())]

        # FIXME: remove duplicated code
        def on_exit_clicked(_button: urwid.Button) -> typing.NoReturn:
            raise urwid.ExitMainLoop()

        # retry: go back to the game and play again
        retry_button = urwid.Button("retry")
        # urwid.connect_signal(retry_button, "click", lambda button: self._emit("close"))
        urwid.connect_signal(retry_button, "click", on_retry_clicked)

        # exit: close the application
        exit_button = urwid.Button("exit")
        urwid.connect_signal(exit_button, "click", on_exit_clicked)

        pile = urwid.Pile(
            [
                # urwid.Text(f"this is a popup, and this is info: {stats}\n"),
                get_stats_widget(stats),
                urwid.Columns([retry_button, exit_button]),
            ]
        )
        super().__init__(urwid.AttrMap(urwid.Filler(pile), "popbg"))


class WidgetWithGameOverPopup(urwid.PopUpLauncher):
    """TODO
    - find out how to attach a new signal type to a widget (here Pile, signal -- gameover)
    """
    def __init__(self, widget) -> None:
        super().__init__(widget)

        self.info = None
        self.stats_widget = None

        def _on_gameover_event(w, info, stats_widget):
            self.info = info
            self.stats_widget = stats_widget
            self.open_pop_up()

        urwid.connect_signal(self.original_widget, "gameover", _on_gameover_event)

    def create_pop_up(self) -> PopUpDialog:
        pop_up = PopUpDialog(self.info, self.stats_widget)
        urwid.connect_signal(pop_up, "close", lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {"left": 0, "top": 1, "overlay_width": 32, "overlay_height": 7}

    def keypress(self, size: tuple[int], key: str) -> str | None:
        parsed = super().keypress(size, key)
        if parsed in {"q", "Q"}:
            raise urwid.ExitMainLoop("Done")
        return parsed


# fill = urwid.Filler(urwid.Padding(ThingWithAPopUp(), urwid.CENTER, 15))
# loop = urwid.MainLoop(fill, [("popbg", "white", "dark blue")], pop_ups=True)
# loop.run()

# class ThingWithAPopUp(urwid.PopUpLauncher):
#     def __init__(self) -> None:
#         super().__init__(urwid.Button("click-me"))
#         urwid.connect_signal(self.original_widget, "click", lambda button: self.open_pop_up())

#     def create_pop_up(self) -> PopUpDialog:
#         pop_up = PopUpDialog()
#         urwid.connect_signal(pop_up, "close", lambda button: self.close_pop_up())
#         return pop_up

#     def get_pop_up_parameters(self):
#         return {"left": 0, "top": 1, "overlay_width": 32, "overlay_height": 7}

#     def keypress(self, size: tuple[int], key: str) -> str | None:
#         parsed = super().keypress(size, key)
#         if parsed in {"q", "Q"}:
#             raise urwid.ExitMainLoop("Done")
#         return parsed

