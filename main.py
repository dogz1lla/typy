"""Initial ideas:
- the word box is a pile of columns (words) of columns (letters of each word);
- each time i press a button, i need to advance/move back the cursor;
- each the cursor moves, i need to change the color of the letter at the current pos;
- all i do is actually only change the colors map (WRONG! i change the cursor position too);

i have columns of columns (words/letters); it is effectively a 2d matrix (or a nested list); i could
just replace the matrix element on each button press through Columns.contents;

TODO:
- [x] look at the currently pressed key and act accordingly;
- [x] implement the cursor move logic;
- [x] prevent the program from crashing upon reaching the last word;
- [x] remove the current word highlight from the words user already passed;
- [x] figure out the double space edge case;
- [x] flush the edit box without sending one more extra keystroke from the old word to cursor change;
- [x] figure out why the edit text changes only after pressing an extra key after space;
- [x] figure out how to flush the edit box content on pressing space;
- [x] extend the word mask functionality to >1 word;
- [x] if not all chars are input and the word is advanced then convert all not typed to false;
- [x] bug: when backspacing the cursor seem to not go all the way to the first letter;
- [x] print stats on game over;
- [x] write a line wrapping logic, tie it to the screen dimension;
- [x] center all the gui elements;
- [x] restart button;
- [x] add wpm to the stats;
- [x] print stats in an overlay widget;
- [ ] add argparse for at least number of words;
"""
import urwid
import typing
from functools import partial
from enum import Enum
from typing import Optional
import time

from popup import WidgetWithGameOverPopup


class LetterStatus(Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    DEFAULT = "default"
    CURRENT_LETTER = "current_letter"
    CORRECT_CURRENT_WORD = "correct_current_word"
    WRONG_CURRENT_WORD = "wrong_current_word"
    DEFAULT_CURRENT_WORD = "default_current_word"


PALETTE: list[tuple[str, str, str]] = [
    (LetterStatus.CORRECT, "dark green", ""),
    (LetterStatus.WRONG, "dark red", ""),
    (LetterStatus.DEFAULT, "light gray", ""),
    (LetterStatus.CURRENT_LETTER, "black", "white"),
    (LetterStatus.CORRECT_CURRENT_WORD, "black", "dark green"),
    (LetterStatus.WRONG_CURRENT_WORD, "black", "dark red"),
    (LetterStatus.DEFAULT_CURRENT_WORD, "dark blue", "black"),
    # pop-up style
    ("popbg", "dark red", "black"),
]


VOCAB = [
    "few", "public", "little", "who", "under", "some", "first", "see", "just", "interest",
    "down", "after", "both", "take", "no", "use", "own", "however", "stand", "system", "you",
    "find", "small", "same", "and", "get", "own", "by", "run", "group", "where", "old", "fact", "he",
    "we", "over", "high", "fact", "over", "people", "use", "end", "while", "also", "help", "form", "do",
]


def get_word_repr(word: str, letter_colors: list[str]) -> urwid.Columns:
    return [(1, urwid.Text((c, l))) for c, l in zip(letter_colors, word)]


def get_word_widget(word: str, letter_colors: list[str]) -> urwid.Columns:
    assert len(word) == len(letter_colors)
    letters = get_word_repr(word, letter_colors)
    return urwid.Columns(letters, dividechars=0)


def get_line_repr(words: list[str], color_map: list[list[str]]):
    return [(len(w), get_word_widget(w, cs)) for w, cs in zip(words, color_map)]


def get_line_widget(words: list[str], color_map: list[list[str]]) -> urwid.Columns:
    assert len(words) == len(color_map)
    line = get_line_repr(words, color_map)
    return urwid.Columns(line, dividechars=1)


def wrap_lines(words, max_width: int):
    wrapped_lines = list()
    current_line_width = 0
    current_line = list()
    for word in words:
        if len(word) + current_line_width < max_width:
            current_line_width += 1 if current_line else 0  # space between words
            current_line_width += len(word)
            current_line.append(word)
        else:
            wrapped_lines.append(current_line)
            current_line_width = len(word)
            current_line = [word]
    wrapped_lines.append(current_line)
    return wrapped_lines


def get_word_matrix(words: list[str], color_map: list[list[str]], box_dim: tuple[int, int] = (50, 10)) -> list[urwid.Columns]:
    max_width, _ = box_dim
    l1 = wrap_lines(words, max_width)
    l2 = wrap_lines(color_map, max_width)
    return [get_line_widget(line, cm) for line, cm in zip(l1, l2)]


def get_gui(stats_table, word_box, input_field, button_inst) -> urwid.Widget:
    div = urwid.Divider()
    pile = urwid.Pile([stats_table, word_box, div, input_field, div, button_inst])
    top = urwid.Filler(pile)
    return top


class GameOverException(Exception):
    def __init__(self, word_mask, start_time: Optional[float] = None, msg: str = "Game over", *args):
        super().__init__(msg, *args)
        self.word_mask = word_mask
        self.start_time = start_time


def get_colors(word_mask: list[list[Optional[bool]]], cursor_pos: tuple[int, int]) -> list[list[LetterStatus]]:
    word_idx, char_idx = cursor_pos
    def _map_mask_value_to_color(mask_value: Optional[bool], current_word: bool) -> LetterStatus:
        if current_word:
            if mask_value is None:
                return LetterStatus.DEFAULT_CURRENT_WORD
            elif mask_value:
                return LetterStatus.CORRECT_CURRENT_WORD
            else:
                return LetterStatus.WRONG_CURRENT_WORD
        else:
            if mask_value is None:
                return LetterStatus.DEFAULT
            elif mask_value:
                return LetterStatus.CORRECT
            else:
                return LetterStatus.WRONG
    result = [[_map_mask_value_to_color(mv, False) for mv in wm] for wm in word_mask]
    current_word_colors = [_map_mask_value_to_color(mv, True) for mv in word_mask[word_idx]]
    if char_idx < len(word_mask[word_idx]) - 1:
        current_word_colors[char_idx+1] = LetterStatus.CURRENT_LETTER
    result[word_idx] = current_word_colors
    return result

def correct_char(word: str, char_idx: int, char: str) -> bool:
    assert len(word) > 0
    assert char_idx > -1
    assert char_idx < len(word)
    # assert len(char) == 1
    return word[char_idx] == char


def init_word_mask(words: list[str]) -> list[Optional[bool]]:
    return [[None]*len(w) for w in words]


def update_word_mask(
    words: list[str],
    word_mask: list[Optional[bool]],
    cursor_pos: tuple[int, int],
    char: str,
) -> list[list[Optional[bool]]]:
    assert len(words) == len(word_mask)

    word_idx, char_idx = cursor_pos
    assert char_idx > -2  # can be -1
    assert word_idx > -1

    if word_idx >= len(word_mask):
        # pressing space after the last word -> advance beyond the bounds -> game over
        # NOTE: need to make sure the Nones in the last word are taken care of
        prev_words_masks = word_mask[:word_idx]
        for i, prev_word_mask in enumerate(prev_words_masks):
            prev_words_masks[i] = [False if x is None else x for x in prev_word_mask]
        word_mask[:word_idx] = prev_words_masks
        raise GameOverException(word_mask)

    # current word
    current_word = words[word_idx]
    current_word_mask = word_mask[word_idx]

    if char_idx >= len(current_word):
        # the user kept typing beyond the length of the word -> keep everything up to the end as it is
        return word_mask
    
    # all before word idx: if there are any Nones there it means the user hit space before finishing
    # typing the word -> convert all of the untyped letters to False
    prev_words_masks = word_mask[:word_idx]
    for i, prev_word_mask in enumerate(prev_words_masks):
        prev_words_masks[i] = [False if x is None else x for x in prev_word_mask]
    word_mask[:word_idx] = prev_words_masks

    # all after word idx
    next_words_masks = word_mask[word_idx+1:]
    assert all([all([x is None for x in wm]) for wm in next_words_masks])

    if char_idx == -1:
        # user hit backspace so many times we are back at the beginning of the word
        current_word_mask = [None]*len(current_word_mask)
    else:
        prev_chars = current_word_mask[:char_idx]
        assert all([c is not None for c in prev_chars])

        # re-init all the values in the mask after the current char (eg if the user hit back space key)
        current_word_mask[char_idx+1:] = [None]*len(current_word_mask[char_idx+1:])

        # check the current char
        current_word_mask[char_idx] = correct_char(current_word, char_idx=char_idx, char=char)
    word_mask[word_idx] = current_word_mask
    return word_mask


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


def main() -> None:
    def get_word_list(n: int) -> list[str]:
        from random import choice
        return [choice(VOCAB) for _ in range(n)]
        # return ["hi", "bye", "wee"]
        # return ["aaaaaa", "bbbb"]

    def exit_on_q(key: str) -> None:
        if key in {"q", "Q"}:
            raise urwid.ExitMainLoop()

    def on_exit_clicked(_button: urwid.Button) -> typing.NoReturn:
        raise urwid.ExitMainLoop()

    def on_input_change_closure(words, screen_dim):
        def _clean_state(state: dict, word_list: Optional[list[str]] = None) -> dict:
            state["cursor_pos"] = (0, -1)
            state["words"] = word_list or words
            state["word_mask"] = init_word_mask(state["words"])
            state["typed_so_far"] = ""
            state["colors"] = None
            state["game_start_time"] = None

        app_state = dict()
        _clean_state(app_state)

        def on_input_change(_edit: urwid.Edit, new_edit_text: str, word_widget: urwid.Pile, stats_widget: urwid.Pile) -> None:
            """Redraw dynamically updated widgets on user input."""

            # if app_state["game_start_time"] is None and app_state["cursor_pos"][0] == 0:
            if app_state["game_start_time"] is None and app_state["cursor_pos"][0] == 0 and app_state["cursor_pos"][1] > -1:
                # we are at the beginning of the game -> start timer
                app_state["game_start_time"] = time.time()

            if len(new_edit_text) == 0:
                # this will happen when the _edit.edit_text is set to "" by the postchange event
                app_state["typed_so_far"] = new_edit_text
                x, _ = app_state["cursor_pos"]
                new_cursor_pos = (x, -1)
                app_state["cursor_pos"] = new_cursor_pos

                # NOTE: this call wont raise the game over exception because this if branch does not
                # advance the word_idx
                new_word_mask = update_word_mask(app_state["words"], app_state["word_mask"], new_cursor_pos, "")
                app_state["word_mask"] = new_word_mask

                new_colors = get_colors(new_word_mask, new_cursor_pos)
                app_state["colors"] = new_colors

                new_word_matrix = get_word_matrix(app_state["words"], new_colors, screen_dim)
                word_widget.contents = [(w, word_widget.options()) for w in new_word_matrix]
                return

            if all([c == " " for c in new_edit_text]):
                # if the user keeps spamming spaces before entering any non-space char then ignore
                # TODO: check if this ever happens
                _, y = app_state["cursor_pos"]
                assert y == -1
                return

            # NOTE: Always possible because alternative is handled in the if clause above
            last_char = new_edit_text[-1]

            x, y = app_state["cursor_pos"]
            if new_edit_text.endswith(" "):
                # space -> move to the next word
                new_cursor_pos = (x + 1, -1)
            else:
                if len(new_edit_text) < len(app_state["typed_so_far"]):
                    # user hit backspace
                    new_cursor_pos = (x, max(-1, y - 1))
                else:
                    new_cursor_pos = (x, y + 1)

            app_state["cursor_pos"] = new_cursor_pos
            app_state["typed_so_far"] = new_edit_text

            try:
                new_word_mask = update_word_mask(app_state["words"], app_state["word_mask"], new_cursor_pos, last_char)
            except GameOverException as e:
                elapsed_time = time.time() - app_state["game_start_time"]
                final_word_mask = e.word_mask
                stats = _get_stats_from_word_mask(final_word_mask)
                wpm = int(round(60.0 * NUM_WORDS / elapsed_time, 0))
                stats["wpm"] = wpm
                new_words = get_word_list(len(app_state["words"]))
                urwid.emit_signal(word_widget, "gameover", word_widget, stats, stats_widget)
                _clean_state(app_state, new_words)
                return

            app_state["word_mask"] = new_word_mask

            new_colors = get_colors(new_word_mask, new_cursor_pos)
            app_state["colors"] = new_colors

            new_word_matrix = get_word_matrix(app_state["words"], new_colors, box_dim=screen_dim)
            word_widget.contents = [(w, word_widget.options()) for w in new_word_matrix]
            return
        return on_input_change

    def clear_if_space(_edit: urwid.Edit, _: str) -> None:
        if _edit.edit_text.endswith(" "):
            # if the user presses space -> clear the edit field
            _edit.set_edit_text(u"")

    def _get_stats_from_word_mask(word_mask) -> dict:
        assert all([all([x is not None for x in wm]) for wm in word_mask])
        n_chars = sum([len(wm) for wm in word_mask])
        n_correct_chars = sum([len([x for x in wm if x]) for wm in word_mask])
        n_words = len(word_mask)
        n_correct_words = sum([all([x for x in wm]) for wm in word_mask])
        return dict(
            n_chars=n_chars,
            n_correct_chars=n_correct_chars,
            correct_chars_pct=int(round(100*n_correct_chars/n_chars, 0)),
            n_words=n_words,
            n_correct_words=n_correct_words,
            correct_words_pct=int(round(100*n_correct_words/n_words, 0)),
        )

    NUM_WORDS = 5
    WORDS = get_word_list(NUM_WORDS)

    # init application loop
    # NOTE: need to do it before everything else to have access to the screen dimensions
    loop = urwid.MainLoop(None, PALETTE, unhandled_input=exit_on_q, pop_ups=True)
    screen_dim = loop.screen.get_cols_rows()
    word_box_dim = (screen_dim[0] - 4, screen_dim[1])

    # widgets
    ## stats
    stats_widget = get_stats_widget()
    ## word box
    init_colors = get_colors(init_word_mask(WORDS), (0, -1))
    word_matrix = get_word_matrix(WORDS, init_colors, word_box_dim)
    word_widget = urwid.Pile(word_matrix)

    ### augment the word widget Pile with a game over popup
    urwid.register_signal(urwid.Pile, ["gameover"])
    word_widget_with_popup = WidgetWithGameOverPopup(word_widget)

    word_box = urwid.LineBox(word_widget_with_popup)
    ## input field
    input_field = urwid.Edit(("", ""), align='center')
    input_field_box = urwid.LineBox(input_field)
    ## exit button
    button_inst = urwid.Button("Exit")
    ## top level widget
    top = get_gui(urwid.Filler(urwid.Padding(stats_widget, urwid.CENTER, 25)), word_box, input_field_box, button_inst)
    app = urwid.LineBox(top)

    # events
    on_input_change = on_input_change_closure(WORDS, word_box_dim)
    urwid.connect_signal(input_field, "change", partial(on_input_change, word_widget=word_widget, stats_widget=stats_widget))
    urwid.connect_signal(input_field, "postchange", clear_if_space)
    urwid.connect_signal(button_inst, "click", on_exit_clicked)

    # set the main widget for the application
    loop.widget = app

    # run application loop
    loop.run()


if __name__ == "__main__":
    main()