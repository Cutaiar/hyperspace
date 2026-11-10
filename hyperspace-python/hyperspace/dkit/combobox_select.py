"""The Combobox's selection model: which row an open highlights.

`resolve_open` is RETRO row 26: the COMMITTED value beats the gesture, and
the gesture (an arrow pressed while closed, recorded as `SEL_FIRST` /
`SEL_LAST`) is only the fallback. Pure, no imgui. Moved out of
`comp_combobox.py` by `HANDOFF.md` item 3c, which re-exports every name
callers use.
"""

from __future__ import annotations

from .combobox_items import _k

# An arrow pressed while the list is CLOSED decides where the highlight
# lands, but `rows` is not known until the popup is open - so the open
# records which end it wants and the next frame resolves it. Sentinels
# rather than 0 / -1, because 0 is a real index and -1 is a real Python one.
SEL_FIRST = object()
SEL_LAST = object()


class _Cleared(str):
    """The answer "the user emptied this", which is neither a choice nor
    silence.

    A `str` subclass, and empty, so a caller that has not been updated still
    does the safe thing: `if got:` is False and nothing is set, exactly as
    before. A caller that wants the behaviour writes `if got is not None`
    and gets an empty string to store. The alternative - a bare `object()` -
    would have gone into somebody's state dict and blown up at the next
    `D.label`.
    """
    __slots__ = ()

    def __repr__(self):
        return "<CLEARED>"


CLEARED = _Cleared()
# "opened, and nothing was asked for". It cannot be a plain None, because
# None is the real `nothing is highlighted` state the arrows fall into at
# either end, and the committed value overrides an OPEN but must not
# override a user who has arrowed off the end.
SEL_NONE = object()
SENTINELS = (SEL_FIRST, SEL_LAST, SEL_NONE)
# `s.pop(k, None)` cannot tell "no scroll was asked for" from "scroll to
# nothing", and the second is a real state: the highlight falls off the end
# into None and the list must stay where it is.
_MISSING = object()


def _committed_row(shown, rows, label) -> int | None:
    """Where the committed value sits in `rows`, or None.

    MEASURED, and the thing the kit got most wrong about opening the list:
    an open does NOT start with nothing highlighted - it starts on the row
    that holds the committed value. On `combobox.many`, value `Gamma`
    (index 2 of sixteen):

        click the field     highlight = Gamma
        click the chevron   highlight = Gamma
        ArrowDown           highlight = Gamma      (not the first row)
        ArrowUp             highlight = Gamma      (not the last row)

    and on `combobox.kb`, which holds no value, the same four give none,
    none, the first row and the last row. So the value wins over all of
    them and the sentinels are the fallback.

    Typing is the exception and stays at none - a filter clears the
    highlight whatever the value is.

    The row is found by exactly the rule the CHECK uses, so the highlighted
    row and the ticked row cannot disagree: the real component highlights
    and ticks the same row, measured (`data-highlighted` on item 2 with the
    indicator rendered on item 2).
    """
    for n, i in enumerate(rows):
        it = shown[i]
        chk = _k(it, "checked", None)
        if chk is None:
            chk = bool(label) and _k(it, "label", "") == label
        if chk:
            return n
    return None


def resolve_open(want, shown, rows, label):
    """Which row an open highlights: the measured table, in one place.

                            holds a value      holds none
        click the field     the value's row    nothing
        click the chevron   the value's row    nothing
        ArrowDown           the value's row    the FIRST row
        ArrowUp             the value's row    the LAST row
        typing              nothing            nothing

    `want` is `SEL_NONE`, `SEL_FIRST` or `SEL_LAST` - which end the open
    asked for - or None for a type-open, which stays at none whatever the
    value is.

    A function rather than four lines inside `combobox` so the rule can be
    asked without a GL context: the dashboard's only Combobox holds a
    value and matches a row, so the no-value half of this table is not
    reachable by driving the app at all, and a driven test can only ever
    cover the left-hand column.
    """
    if want not in SENTINELS:
        return want
    at = _committed_row(shown, rows, label)
    if at is not None:
        return at
    if want is SEL_FIRST:
        return 0 if rows else None
    if want is SEL_LAST:
        return len(rows) - 1 if rows else None
    return None
