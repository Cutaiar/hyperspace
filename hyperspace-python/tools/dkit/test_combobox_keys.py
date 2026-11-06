"""The Combobox's keyboard, one test per measured rule.

The rules are not invented. They come from driving the REAL Base UI
component in Chromium on the `?probe` route's `combobox.kb` block - which is
the only combobox there WITHOUT `open`, and that matters: every other block
reports `aria-expanded: true` whatever you press, and measuring one of those
is how the first pass concluded that focus opens the list.

    closed  focus (a Tab into it)   stays CLOSED
    closed  click the input         opens, highlight NONE
    closed  ArrowDown               opens, highlight = first
    closed  ArrowUp                 opens, highlight = LAST
    closed  typing                  opens, filters, highlight NONE
    open    typing                  filters, highlight back to NONE
    open    ArrowDown               none -> first, i -> i+1, last -> NONE
    open    ArrowUp                 none -> last,  i -> i-1, first -> NONE
    open    Enter, highlight set    selects it, closes
    open    Enter, no highlight     closes, value reverts
    open    Escape                  closes, value reverts, focus STAYS
    open    Tab                     closes, focus MOVES ON

Driven on the dashboard's "Find" combobox, which holds the six planes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from imgui_bundle import imgui

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tests"))

W, H = 1440, 1400          # tall, so the panel opens BELOW the field
DWELL = 40
PID = "##cb.ctl.find"


def _gl_or_skip():
    try:
        import gl_probe
    except ImportError:
        pytest.skip("gl_probe not importable")
    gl_probe.require()


@pytest.fixture(scope="module")
def DB():
    _gl_or_skip()
    import dashboard
    return dashboard


def _field(DB):
    r = DB.lay_out(W, H)
    kx, ky, _kw, kh = r.ctl_rows[5]
    return kx + DB.CTL_LABEL_W, ky, 150.0, 32.0


def _open_by_click(DB):
    """The script prefix that opens the list with the pointer, and the
    pointer position to hold for the rest of it."""
    fx, fy, _fw, fh = _field(DB)
    cx, cy = fx + 40, fy + fh / 2
    pre = [(10, 10, False)] * 10 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 20
    return pre, (cx, cy)


def _drive(DB, script, keys=None):
    import comp_combobox as CC
    f = np.asarray(DB.render("dark", W, H, script=script, keys=keys,
                             keep="last")[-1])[:, :, :3]
    return f, CC.LAST_RECT.get(PID)


def _highlight(DB, f, rect):
    """Which row indices are filled differently from the panel's ground.

    Sampled in the row's own left PADDING - six pixels in, where the row
    fill is and the label is not. The first version of this read a column
    through the text and reported every row as highlighted.
    """
    px, py, pw, ph = rect
    ground = f[int(py + ph) - 3, int(px) + int(pw) // 2].astype(int)
    out = []
    for i in range(len(DB.PLANES)):
        yy = int(py) + 4 + i * 28 + 14
        if yy >= int(py + ph) - 2:
            break
        if abs(f[yy, int(px) + 6].astype(int) - ground).max() > 2:
            out.append(i)
    return out


# --------------------------------------------------------------------------
# opening and closing
# --------------------------------------------------------------------------
def test_tabbing_onto_the_field_does_not_open_the_list(DB):
    """Measured: focus alone leaves it closed. The kit opened on focus, so
    tabbing through the panel popped the list open - and then trapped you in
    it."""
    _f, rect = _drive(DB, [(10, 10, False)] * 56,
                      keys=[(4 + i, imgui.Key.tab) for i in range(8)])
    assert rect is None, f"a Tab opened the list: {rect}"


def test_clicking_the_field_opens_it_with_nothing_highlighted(DB):
    pre, _at = _open_by_click(DB)
    f, rect = _drive(DB, pre + [(10, 10, False)] * 0 or pre)
    assert rect, "the click did not open the list"
    assert _highlight(DB, f, rect) == [], \
        "a click left a row highlighted; measured, it leaves none"


def test_escape_closes_it_and_keeps_the_field_focused(DB):
    """The second half is what makes the next arrow work, and it is why the
    close hands the focus back explicitly: the field inside the popup is a
    different imgui id from the one outside it."""
    pre, at = _open_by_click(DB)
    esc = len(pre) + 2
    f, rect = _drive(DB, pre + [at + (False,)] * 24,
                     keys=[(esc, imgui.Key.escape)])
    assert rect is None, "Escape did not close the list"
    # and the focus came back: an arrow reopens it
    f, rect = _drive(DB, pre + [at + (False,)] * 46,
                     keys=[(esc, imgui.Key.escape),
                           (esc + 14, imgui.Key.down_arrow)])
    assert rect, "the field lost focus on Escape - the arrow did not reopen"


def test_tab_closes_the_list_rather_than_being_swallowed(DB):
    """Tab is not the list's key. The kit ate it inside the popup, so a
    keyboard user could get into the combobox and not out of it."""
    pre, at = _open_by_click(DB)
    f, rect = _drive(DB, pre + [at + (False,)] * 30,
                     keys=[(len(pre) + 2, imgui.Key.tab)])
    assert rect is None, "Tab was swallowed; the list is still open"


# --------------------------------------------------------------------------
# the arrows
# --------------------------------------------------------------------------
def _after_escape(DB, extra, keys):
    """Open, Escape (which leaves the field focused), then press `keys`."""
    pre, at = _open_by_click(DB)
    esc = len(pre) + 2
    script = pre + [at + (False,)] * 20 + [at + (False,)] * extra
    return _drive(DB, script, keys=[(esc, imgui.Key.escape)] + keys)


def test_arrowdown_from_closed_opens_on_the_first_row(DB):
    base = len(_open_by_click(DB)[0]) + 16
    f, rect = _after_escape(DB, 40, [(base, imgui.Key.down_arrow)])
    assert rect, "ArrowDown did not open the list"
    assert _highlight(DB, f, rect) == [0]


def test_arrowup_from_closed_opens_on_the_LAST_row(DB):
    base = len(_open_by_click(DB)[0]) + 16
    f, rect = _after_escape(DB, 40, [(base, imgui.Key.up_arrow)])
    assert rect, "ArrowUp did not open the list"
    assert _highlight(DB, f, rect) == [len(DB.PLANES) - 1]


def test_the_opening_arrow_is_not_also_processed_by_the_list(DB):
    """The off-by-one this guards: the closed-field branch sets the
    highlight to the first row and the popup's own handler, running later in
    the SAME frame, moved it on by one - so a first ArrowDown landed on the
    second row and a first ArrowUp on the second-to-last."""
    base = len(_open_by_click(DB)[0]) + 16
    f, rect = _after_escape(DB, 40, [(base, imgui.Key.down_arrow)])
    assert _highlight(DB, f, rect) == [0], "the opening arrow moved twice"


def test_a_second_arrow_moves_one_row(DB):
    base = len(_open_by_click(DB)[0]) + 16
    f, rect = _after_escape(DB, 48, [(base, imgui.Key.down_arrow),
                                     (base + 10, imgui.Key.down_arrow)])
    assert _highlight(DB, f, rect) == [1]


def test_the_highlight_falls_off_the_end_rather_than_wrapping(DB):
    """Measured on six items: six ArrowDowns from the first leave NOTHING
    highlighted, and the next ArrowUp comes back at the last. There is a
    real none-state between the two ends; it does not wrap."""
    base = len(_open_by_click(DB)[0]) + 16
    f, rect = _after_escape(DB, 48, [(base, imgui.Key.down_arrow),
                                     (base + 10, imgui.Key.up_arrow)])
    assert rect, "the list closed"
    assert _highlight(DB, f, rect) == [], \
        "going up off the first row wrapped instead of clearing"


# --------------------------------------------------------------------------
# the ring the popup used to cut
# --------------------------------------------------------------------------
def test_the_fields_focus_ring_is_not_clipped_by_the_popup(DB):
    """The popup window spans the trigger as well as the panel, so the
    field's caret is inside the focused window. It used to END at the
    field's edge, and ImGui clips a window's draw list to the window - so
    the 3px ring drawn OUTSIDE the field was cut off square, and the right
    ends of the rows with it. The window is inflated by `RING_PAD` now.

    Asserted on the ring's own pixels: the band must be present on BOTH
    sides at the field's vertical middle, and at the same strength.
    """
    import comp_combobox as CC
    pre, _at = _open_by_click(DB)
    f, rect = _drive(DB, pre)
    assert rect, "the list did not open"
    fx, fy, fw, fh = _field(DB)
    mid = int(fy + fh / 2)
    ground = f[int(fy) - 10, int(fx) + 40].astype(int)

    def band(xx0, xx1):
        cols = [int(abs(f[mid, xx].astype(int) - ground).max())
                for xx in range(xx0, xx1)]
        return max(cols)

    left = band(int(fx) - int(CC.RING_PAD), int(fx))
    right = band(int(fx + fw), int(fx + fw) + int(CC.RING_PAD))
    assert left > 15, f"no ring left of the field: {left}"
    assert right > 15, f"no ring right of the field: {right}"
    assert abs(left - right) <= 6, (
        f"the ring is {left} on the left and {right} on the right - one "
        f"side is being clipped")
