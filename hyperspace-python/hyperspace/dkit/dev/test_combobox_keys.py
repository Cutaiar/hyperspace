"""The Combobox's keyboard, one test per measured rule.

The rules are not invented. They come from driving the REAL Base UI
component in Chromium on the `?probe` route's `combobox.kb` block - which is
the only combobox there WITHOUT `open`, and that matters: every other block
reports `aria-expanded: true` whatever you press, and measuring one of those
is how the first pass concluded that focus opens the list.

    closed  focus (a Tab into it)   stays CLOSED
    closed  click the input         opens on the COMMITTED row, else none
    closed  click the chevron       the same
    closed  ArrowDown               opens on the COMMITTED row, else first
    closed  ArrowUp                 opens on the COMMITTED row, else LAST
    closed  typing                  opens, filters, highlight NONE
    open    typing                  filters, highlight back to NONE
    open    ArrowDown               none -> first, i -> i+1, last -> NONE
    open    ArrowUp                 none -> last,  i -> i-1, first -> NONE
    open    Enter, highlight set    selects it, closes, focus STAYS
    open    Enter, no highlight     closes, value reverts, focus STAYS
    open    Escape                  closes, value reverts, focus STAYS
    open    Tab                     closes, focus MOVES ON

**The committed row is the part this file first got wrong.** The rules
above were measured on `combobox.kb`, which carries no `defaultValue` - so
every open there has no committed row and falls through to the none /
first / last case, and that is the only case the model recorded. Re-driven
on `combobox.many` (sixteen rows, `defaultValue="Gamma"` at index 2), all
four gestures open on Gamma. The dashboard's Find combobox DOES hold a
value, so these tests were asserting the valueless rules against a valued
control the whole time.

The no-value half of the table cannot be driven at all here, because the
dashboard has no valueless Combobox; it is covered as a pure test of
`comp_combobox.resolve_open` in `test_combobox.py`, which is the same code
path this widget runs.

Driven on the dashboard's "Find" combobox, which holds the six planes and
has `XW` - index 2 - committed.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest
from imgui_bundle import imgui

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))

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
    from hyperspace.dkit.dev import dashboard
    return dashboard


def _field(DB):
    r = DB.lay_out(W, H)
    kx, ky, _kw, _kh = r.ctl_rows[5]
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
    from hyperspace.dkit import comp_combobox as CC
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


def _committed(DB):
    """Which row of the Find combobox holds the committed value."""
    return list(DB.PLANES).index(DB.CTL_STATE["plane"])


def test_clicking_the_field_opens_it_on_the_committed_row(DB):
    """MEASURED on `combobox.many`, which holds `Gamma`: clicking the field
    opens the list with Gamma highlighted AND ticked - not with nothing
    highlighted. The kit opened on none, because the model behind it was
    measured on the one probe block that holds no value."""
    pre, _at = _open_by_click(DB)
    f, rect = _drive(DB, pre)
    assert rect, "the click did not open the list"
    assert _highlight(DB, f, rect) == [_committed(DB)], \
        "a click did not land on the committed row"


def test_clicking_the_chevron_opens_it_on_the_committed_row(DB):
    """The chevron has its own hit target in the kit and its own button in
    the browser; measured, both open on the committed row."""
    fx, fy, fw, fh = _field(DB)
    cx, cy = fx + fw - 12, fy + fh / 2
    pre = [(10, 10, False)] * 10 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * DWELL
    f, rect = _drive(DB, pre)
    assert rect, "the chevron did not open the list"
    assert _highlight(DB, f, rect) == [_committed(DB)]


def test_escape_closes_it_and_keeps_the_field_focused(DB):
    """The second half is what makes the next arrow work, and it is why the
    close hands the focus back explicitly: the field inside the popup is a
    different imgui id from the one outside it."""
    pre, at = _open_by_click(DB)
    esc = len(pre) + 2
    _f, rect = _drive(DB, pre + [at + (False,)] * 24,
                     keys=[(esc, imgui.Key.escape)])
    assert rect is None, "Escape did not close the list"
    # and the focus came back: an arrow reopens it
    _f, rect = _drive(DB, pre + [at + (False,)] * 46,
                     keys=[(esc, imgui.Key.escape),
                           (esc + 14, imgui.Key.down_arrow)])
    assert rect, "the field lost focus on Escape - the arrow did not reopen"


def test_tab_closes_the_list_rather_than_being_swallowed(DB):
    """Tab is not the list's key. The kit ate it inside the popup, so a
    keyboard user could get into the combobox and not out of it."""
    pre, at = _open_by_click(DB)
    _f, rect = _drive(DB, pre + [at + (False,)] * 30,
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


def test_either_arrow_from_closed_opens_on_the_committed_row(DB):
    """MEASURED on `combobox.many`: ArrowDown AND ArrowUp both open on the
    value's row. The end the arrow asks for is only the fallback, for a
    combobox that holds nothing - see `resolve_open` and its tests."""
    base = len(_open_by_click(DB)[0]) + 16
    at = _committed(DB)
    for key in (imgui.Key.down_arrow, imgui.Key.up_arrow):
        f, rect = _after_escape(DB, 40, [(base, key)])
        assert rect, f"{key} did not open the list"
        assert _highlight(DB, f, rect) == [at], f"{key} landed elsewhere"


def test_the_opening_arrow_is_not_also_processed_by_the_list(DB):
    """The off-by-one this guards: the closed-field branch sets the
    highlight and the popup's own handler, running later in the SAME frame,
    moved it on by one - so an opening ArrowDown overshot the row it had
    just chosen."""
    base = len(_open_by_click(DB)[0]) + 16
    f, rect = _after_escape(DB, 40, [(base, imgui.Key.down_arrow)])
    assert _highlight(DB, f, rect) == [_committed(DB)], \
        "the opening arrow moved twice"


def test_a_second_arrow_moves_one_row(DB):
    base = len(_open_by_click(DB)[0]) + 16
    at = _committed(DB)
    f, rect = _after_escape(DB, 48, [(base, imgui.Key.down_arrow),
                                     (base + 10, imgui.Key.down_arrow)])
    assert _highlight(DB, f, rect) == [at + 1]
    f, rect = _after_escape(DB, 48, [(base, imgui.Key.up_arrow),
                                     (base + 10, imgui.Key.up_arrow)])
    assert _highlight(DB, f, rect) == [at - 1]


def test_the_highlight_falls_off_the_end_rather_than_wrapping(DB):
    """Measured: arrowing past the last row leaves NOTHING highlighted, and
    the next press comes back round at the other end. There is a real
    none-state between the two ends; it does not wrap."""
    base = len(_open_by_click(DB)[0]) + 16
    at = _committed(DB)
    # down off the end: from `at`, (n - at) presses reach past the last row
    n = len(DB.PLANES)
    keys = [(base + 10 * i, imgui.Key.down_arrow) for i in range(n - at + 1)]
    f, rect = _after_escape(DB, 10 * (n - at + 1) + 30, keys)
    assert rect, "the list closed"
    assert _highlight(DB, f, rect) == [], \
        "going down off the last row wrapped instead of clearing"


# --------------------------------------------------------------------------
# the ring the popup used to cut
# --------------------------------------------------------------------------
def _band(f, fx, fy, fw, fh):
    """The focus ring's strength on each side of the field, at d = 1, 2, 3.

    Read against the page's own ground well above the control, and sampled
    on the field's vertical and horizontal middles, where no corner arc and
    no glyph can reach. The ring is a 3px band immediately outside the
    box - `box-shadow: ring/50 0 0 0 3px`, no blur, no offset - so a clean
    ring reads the same number on all four sides.
    """
    X, Y, Wd, Ht = int(fx), int(fy), int(fw), int(fh)
    g = f[Y - 12, X + 40].astype(int)
    mid_y, mid_x = Y + Ht // 2, X + Wd // 2
    at = lambda yy, xx: int(abs(f[yy, xx].astype(int) - g).max())
    return {
        "left": [at(mid_y, X - d) for d in (1, 2, 3)],
        "right": [at(mid_y, X + Wd - 1 + d) for d in (1, 2, 3)],
        "top": [at(Y - d, mid_x) for d in (1, 2, 3)],
        "bottom": [at(Y + Ht - 1 + d, mid_x) for d in (1, 2, 3)],
    }


def test_the_fields_focus_ring_is_not_clipped_by_the_popup(DB):
    """The ring the user sees on a CLICK must be the ring they see on a Tab.

    The two routes differ in exactly one thing - a click opens the list and
    a Tab does not - so a ring that is right on one and clipped on the
    other can only be the fault of something that exists while the list is
    up. That is the popup window: ImGui clips a window's draw list to the
    window, the popup starts at the field's top-left and is exactly `w`
    wide, and the field used to draw its own chrome inside it. Measured
    before the fix, dark, pointer parked off the control:

        list closed   left [46,46,46]  right [46,46,46]  top [46,46,46]  bottom [46,46,46]
        list open     left [ 0, 0, 0]  right [ 0, 0, 0]  top [ 0, 0, 0]  bottom [46,46,46]

    - three sides gone, and the bottom surviving only because the window
    carries on down toward the panel.

    The fix is not a bigger window (`RING_PAD`, which produced artifacts on
    a Retina Mac and is still 0): the chrome moved to the copy of the field
    drawn in the PARENT window, where nothing clips it, and the copy inside
    the popup draws only the widget. See THE SPLIT FIELD in
    `comp_combobox.combobox`.

    The pointer is parked WELL off the control for both frames, so the
    hover tint cannot be mistaken for the band.
    """
    from hyperspace.dkit import comp_combobox as CC
    assert CC.RING_PAD == 0.0, \
        "this asserts the ring with NO window inflation; RING_PAD is back"
    fx, fy, fw, fh = _field(DB)
    cx, cy = fx + 40, fy + fh / 2
    pre = [(10, 10, False)] * 10 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 6
    off = [(cx, fy - 250, False)] * DWELL

    # the list OPEN, which is the case that was broken
    f_open, rect = _drive(DB, pre + off)
    assert rect, "the list did not open"
    opened = _band(f_open, fx, fy, fw, fh)

    # the same field focused with the list CLOSED (Escape keeps the focus),
    # which is the ring a person gets by tabbing to it
    f_shut, shut_rect = _drive(DB, pre + off,
                               keys=[(len(pre) + 2, imgui.Key.escape)])
    assert shut_rect is None, "Escape did not close the list"
    closed = _band(f_shut, fx, fy, fw, fh)

    for side, vals in closed.items():
        assert min(vals) > 15, \
            f"no ring on the {side} with the list CLOSED: {closed}"
    for side, vals in opened.items():
        assert min(vals) > 15, \
            f"the popup clipped the ring on the {side}: open={opened} " \
            f"closed={closed}"
        assert abs(min(vals) - min(closed[side])) <= 6, \
            f"the {side} band differs open vs closed: {opened} / {closed}"


# --------------------------------------------------------------------------
# the field as a text box: its hit area, its caret and its placeholder
# --------------------------------------------------------------------------
def _query_after(DB, click_dx, ch, dwell=DWELL):
    """Click the field `click_dx` in, type one character, and return what
    the field holds.

    Where a typed glyph LANDS is the observable for where the caret is - a
    person types and sees it appear somewhere - and unlike the caret itself
    it does not blink, so it can be read at any frame. On a committed value
    of `XW`:

        QXW   the caret was at 0        XQW   at 1
        XWQ   at the end                Q     the whole value was selected

    The kit gave `Q` - ImGui's `set_keyboard_focus_here()` activates an
    InputText the way a Tab does and selects all of it - where Chromium
    measures `selectionStart == selectionEnd` on every click, never a
    selection.
    """
    fx, fy, _fw, fh = _field(DB)
    cx, cy = fx + click_dx, fy + fh / 2
    pre = [(10, 10, False)] * 10 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 14
    seen = {}
    from hyperspace.dkit import comp_combobox as CC
    orig = CC._state

    def spy(ui, key):
        st = orig(ui, key)
        seen[key] = dict(st)
        return st
    CC._state = spy
    try:
        DB.render("dark", W, H, script=pre + [(cx, fy - 250, False)] * dwell,
                  keys=[(len(pre) + 4, ch)], keep="last")
    finally:
        CC._state = orig
    return seen.get("ctl.find", {}).get("q")


def test_the_caret_lands_where_the_field_was_clicked(DB):
    """Measured in Chromium on `combobox.many`, value `Gamma`: a click at
    +18px gives selectionStart == selectionEnd == 1, at +3px gives 0, past
    the text gives 5. The value is never selected.

    The caret has to survive the handover to the copy of the field inside
    the popup, which is a different imgui id in a different window."""
    val = DB.CTL_STATE["plane"]
    assert len(val) == 2, f"this test is written for a 2-glyph value: {val}"
    # +10 is `input_pad_l`, so the text starts there. +16 is 6px into an
    # "X" 8.484 wide at 14px - past its middle, so the caret goes after it.
    # This was +14, 4px in: past the middle of a HINTED "X", which was 8
    # (a tie at 4 that went to 1), and before the middle of the real one -
    # where Chromium would put the caret at 0 too. RETRO row 67.
    assert _query_after(DB, 16, "Q") == val[0] + "Q" + val[1:], \
        "the caret did not land between the glyphs"
    assert _query_after(DB, 40, "Q") == val + "Q", \
        "a click past the text did not put the caret at the end"
    assert _query_after(DB, 40, "Q") != "Q", "the value was selected"


def test_the_whole_field_is_clickable_not_just_its_text_box(DB):
    """An InputText's hit area is its FRAME, and the frame used to be the
    text box alone - so the field's leading 10px of padding and everything
    right of the text did nothing at all. Measured: a press at x+2 or at
    x+120 on the 150px Find combobox neither focused the field nor opened
    the list, where the browser treats the whole padded box as the input.
    """
    val = DB.CTL_STATE["plane"]
    assert _query_after(DB, 2, "Q") == "Q" + val, \
        "the field's left padding is dead; the click did nothing"
    assert _query_after(DB, 120, "Q") == val + "Q", \
        "the field's right end is dead"


def test_a_committed_row_leaves_the_field_focused_with_a_caret(DB):
    """Measured: after Enter the input is still `document.activeElement`
    AND the caret is at the END of the new value - `selectionStart ==
    selectionEnd == 4` on a committed `Beta`. Nothing is selected.

    The first half was already true of the kit (ImGui keeps nav focus on
    the field the popup was opened from, so an arrow reopens the list); the
    caret was not, so the field came back focused with no cursor in it.
    Asserted by typing, which is the only part of a caret a person can see
    without waiting for the blink.
    """
    pre, at = _open_by_click(DB)
    base = len(pre) + 2
    # the list opens on the committed row, so Enter re-commits the same one
    val = DB.CTL_STATE["plane"]
    _f, rect = _drive(DB, pre + [at + (False,)] * 60,
                     keys=[(base, imgui.Key.enter)])
    assert rect is None, "Enter did not close the list"
    # the focus came back: an arrow reopens it
    _f, rect = _drive(DB, pre + [at + (False,)] * 60,
                     keys=[(base, imgui.Key.enter),
                           (base + 20, imgui.Key.down_arrow)])
    assert rect, "the field lost focus on Enter - the arrow did not reopen"
    # and so did the caret, at the end of the value
    seen = {}
    from hyperspace.dkit import comp_combobox as CC
    orig = CC._state

    def spy(ui, key):
        st = orig(ui, key)
        seen[key] = dict(st)
        return st
    CC._state = spy
    try:
        DB.render("dark", W, H,
                  script=pre + [at + (False,)] * 60,
                  keys=[(base, imgui.Key.enter), (base + 20, "Q")],
                  keep="last")
    finally:
        CC._state = orig
    assert seen.get("ctl.find", {}).get("q") == val + "Q", \
        "no caret in the field after a commit"


# --------------------------------------------------------------------------
# the list follows its keyboard highlight
# --------------------------------------------------------------------------
@contextmanager
def _booted(DB):
    """A context and the real faces, torn down before anything renders.

    `render()` ends in `glfw.terminate()` and that destroys the font atlas,
    so a `faces` held across one asserts inside `calc_text_size`. Boot,
    measure, tear down, then render - `test_gallery.py` carries the same
    helper and the same reason.
    """
    import glfw
    _win, impl, _io, fc, _grad = DB._boot("dark", 320, 240, visible=False,
                                         retina=False)
    try:
        yield fc
    finally:
        impl.shutdown()
        imgui.destroy_context()
        glfw.terminate()


def _gallery_combobox(DB, w, tall):
    """Where the Gallery's sixteen-item Combobox is, and the script prefix
    that gets the Gallery on screen."""
    from hyperspace.dkit import tokens as T
    from hyperspace.dkit.dev import comp_gallery as CG
    with _booted(DB) as fc:
        gw = (w - DB.SIDEBAR_W) - 2 * DB.GUT
        _total, secs = CG.plan(gw, fc, "dark")
    ox, oy = DB.SIDEBAR_W + DB.GUT, DB.HEADER_H + DB.GUT
    head = (T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
            + T.CARD_HEAD_GAP)
    y, found = oy, None
    for title, _blurb, card_h, placed in secs:
        by = y + CG.PAD + head
        for cap, sx, sy, sw, sh, _draw in placed:
            if title == "Combobox" and cap == "sixteen items":
                found = (ox + CG.PAD + sx,
                         by + sy + CG.CAP_H + CG.CAP_GAP, sw, sh)
        y += card_h + CG.GAP
    assert found, "the Gallery has no 'sixteen items' Combobox any more"
    r = DB.lay_out(w, tall)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    gx, gy = nx + nw / 2, ny + nh / 2
    nav = [(10, 10, False)] * 6 + [(gx, gy, False)] * 4 \
        + [(gx, gy, True)] * 3 + [(gx, gy, False)] * 12
    return nav, found


def _lit_band(f, rect):
    """The highlighted row's (top, bottom) inside the panel, or None.

    Scanned down the row's left PADDING - six pixels in from the panel,
    where the row fill is and no glyph ever reaches - rather than by row
    index, because a SCROLLED list does not put its rows on multiples of
    28 from the panel's top, which is the whole thing under test.
    """
    px, py, pw, ph = rect
    # Sampled in the row's RIGHT padding, not its left. `pr-8` reserves 32
    # px there and the check occupies only the last 24, so a column 28 in
    # from the row's right edge is clear of every glyph AND clear of the
    # `rounded-md` corner arc, which at the usual 6px-from-the-panel
    # sample eats two rows off each end of the band and made it read 24
    # tall instead of 28.
    from hyperspace.dkit import comp_combobox as CC
    t = CC.combobox_table("dark")
    x = int(px + pw - t["pad"] - 28)
    ground = f[int(py + ph) - 3, int(px) + int(pw) // 2].astype(int)
    lit = [yy for yy in range(int(py) + 4, int(py + ph) - 3)
           if abs(f[yy, x].astype(int) - ground).max() > 2]
    if not lit:
        return None
    return lit[0], lit[-1] + 1


def test_the_list_scrolls_to_follow_the_keyboard_highlight(DB):
    """MEASURED on `combobox.many`, sixteen rows in a 252px clamp: the
    arrows take the list's `scrollTop` 0 -> 92 (row 11) -> 204 (row 15),
    minimum movement, and back to 0 when the highlight wraps round to the
    first row. The kit did not scroll at all, so arrowing past the ninth
    row moved a highlight nobody could see.

    Asserted on what a person sees rather than on a scroll offset: after
    arrowing well past the clamp there must still be a highlighted row in
    the panel, and it must be the LAST visible one, which is where a
    minimum scroll puts a highlight that came down from above.
    """
    import numpy as np
    TALL = 2600
    nav, (gx, gy, _gw, gh) = _gallery_combobox(DB, W, TALL)
    cx, cy = gx + 40, gy + gh / 2
    pre = nav + [(cx, cy, False)] * 4 + [(cx, cy, True)] * 3 \
        + [(cx, cy, False)] * 10
    steps = 13
    keys = [(len(pre) + 3 + i * 3, imgui.Key.down_arrow)
            for i in range(steps)]
    from hyperspace.dkit import comp_combobox as CC
    f = np.asarray(DB.render("dark", W, TALL,
                             script=pre + [(cx, gy - 200, False)] * 60,
                             keys=keys, keep="last")[-1])[:, :, :3]
    rect = next((v for k, v in CC.LAST_RECT.items()), None)
    assert rect, "the Gallery's Combobox did not open"
    _px, _py, _pw, ph = rect
    visible = int((ph - 2 * 4.0) // 28)
    assert steps > visible, \
        f"{steps} rows is not past the clamp's {visible}"
    band = _lit_band(f, rect)
    assert band, (
        "nothing is highlighted in the panel - the list did not scroll to "
        "follow the arrows")
    top, bot = band
    t = CC.combobox_table("dark")
    assert abs((bot - top) - t["row_h"]) <= 1, \
        f"the lit band is {bot - top} tall, not one {t['row_h']} row"
    # a MINIMUM scroll puts a highlight that came down from above flush
    # with the bottom of the list's viewport, which is the panel's own
    # bottom rail in. Measured in Chromium: row 13's bottom lands exactly
    # `scroll-py-1` (4) above the list's bottom edge.
    assert abs(bot - (rect[1] + ph - t["pad"])) <= 2, (
        f"the highlight is at {top}..{bot} in a panel ending at "
        f"{rect[1] + ph}; a minimum scroll puts it against the last rail")


# --------------------------------------------------------------------------
# the placeholder, and the disabled state
# --------------------------------------------------------------------------
def _ink(f, x, y, w, h, ground):
    """How far the strongest pixel in a box departs from `ground`."""
    import numpy as np
    s = f[int(y):int(y + h), int(x):int(x + w)].astype(int)
    return int(np.abs(s - np.asarray(ground, dtype=int)).max())


def test_clearing_the_field_leaves_the_placeholder_in_it(DB):
    """`::placeholder` keys off the VALUE, not the focus. Measured in
    Chromium on `combobox.kb`: the placeholder's ink is there unfocused,
    under a keyboard focus, and with the list open - the darkest pixel in
    the field reads 115 in all three. The kit drew it only
    `if not out and not focused`, and that `focused` is now gone.

    WHAT THIS DOES NOT COVER, said plainly rather than left implied. The
    state the old rule actually broke is `focused AND closed AND empty`,
    and it is not reachable here: the dashboard's only Combobox always
    holds one of the six planes, Escape puts the value back, and no number
    of Tabs reaches the field (measured - see
    `test_tabbing_onto_the_field_does_not_open_the_list`, which presses
    eight). With the list OPEN the old rule happened to draw the
    placeholder anyway, because the parent's copy of the field is not the
    focused one, so this test passes against the broken code as well. It
    is kept as a guard that the placeholder is drawn at all once the value
    is gone, which is a real thing to lose, and it is NOT evidence that
    the focus half of the fix works. That half is measured, not tested.
    """
    import numpy as np
    fx, fy, _fw, fh = _field(DB)
    cx, cy = fx + 40, fy + fh / 2
    pre = [(10, 10, False)] * 10 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 10
    # delete the committed value, which is the only way to reach an empty
    # focused field here - the dashboard's Combobox always holds one
    n = len(DB.CTL_STATE["plane"])
    keys = [(len(pre) + 2 + i * 4, imgui.Key.backspace) for i in range(n)]
    f = np.asarray(DB.render("dark", W, H,
                             script=pre + [(cx, fy - 250, False)] * DWELL,
                             keys=keys, keep="last")[-1])[:, :, :3]
    # the field's own fill, read between the border and the text
    ground = f[int(fy) + 3, int(fx) + 3].astype(int)
    got = _ink(f, fx + 10, fy + 6, 100, 20, ground)
    assert got > 30, (
        f"the field is blank with the value deleted: strongest pixel is "
        f"{got} off the fill, so no placeholder was drawn")


def test_a_disabled_combobox_dims_its_chevron_as_well_as_its_box(DB):
    """`has-disabled:opacity-50` is on the input GROUP, so it dims
    everything in it. Measured on `combobox.dis`: the addon's button
    computes `opacity: 0.5` and the group `bg-input/50` in light,
    `bg-input/80` in dark, over an element opacity of 0.5.

    The kit dimmed the box - `draw.field` has carried `disabled_bg` and
    `disabled_opacity` since the Input - and left the chevron and the
    placeholder at full strength, so a disabled field had a crisp arrow on
    a faded box.

    Driven on the Gallery, which carries an enabled and a disabled
    Combobox side by side, so the two are read off ONE frame with the same
    ground.
    """
    import numpy as np

    from hyperspace.dkit import tokens as T
    from hyperspace.dkit.dev import comp_gallery as CG
    TALL = 2600
    with _booted(DB) as fc:
        gw = (W - DB.SIDEBAR_W) - 2 * DB.GUT
        _total, secs = CG.plan(gw, fc, "dark")
    ox, oy = DB.SIDEBAR_W + DB.GUT, DB.HEADER_H + DB.GUT
    head = (T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
            + T.CARD_HEAD_GAP)
    y, spots = oy, {}
    for title, _b, card_h, placed in secs:
        by = y + CG.PAD + head
        for cap, sx, sy, sw, sh, _d in placed:
            if title == "Combobox":
                spots[cap] = (ox + CG.PAD + sx,
                              by + sy + CG.CAP_H + CG.CAP_GAP, sw, sh)
        y += card_h + CG.GAP
    assert {"sixteen items", "disabled"} <= set(spots), spots
    r = DB.lay_out(W, TALL)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    gx, gy = nx + nw / 2, ny + nh / 2
    nav = [(10, 10, False)] * 6 + [(gx, gy, False)] * 4 \
        + [(gx, gy, True)] * 3 + [(gx, gy, False)] * DWELL
    f = np.asarray(DB.render("dark", W, TALL, script=nav,
                             keep="last")[-1])[:, :, :3]

    def chevron(cap):
        x, yy, w, h = spots[cap]
        from hyperspace.dkit import comp_combobox as CC
        t = CC.combobox_table("dark")
        g = t["field_icon"]
        bx = x + w - 1.0 - T.SPACE[1] - g
        ground = f[int(yy) + 3, int(x) + 3].astype(int)
        return _ink(f, bx, yy + (h - g) / 2.0, g, g, ground)

    on, off = chevron("sixteen items"), chevron("disabled")
    assert on > 20, f"the enabled chevron is invisible: {on}"
    assert off < on * 0.75, (
        f"the disabled chevron is {off} against the enabled {on} - it is "
        f"not dimmed; `has-disabled:opacity-50` is 0.5")


def test_a_second_escape_empties_the_field(DB):
    """Measured on the real component: one Escape reverts the query and
    closes the list, and a SECOND Escape - pressed while it is already
    closed - sets `input.value` to "".

    The kit could not express that, which is why it sat unimplemented. A
    choice is signalled by returning its id, and a cleared value is a falsy
    id, so every caller read it as "nothing happened". `CC.CLEARED` is the
    third answer: an empty `str` subclass, so `if got:` in an un-updated
    caller still does the safe thing and `if got is not None` separates the
    three cases.
    """
    pre, at = _open_by_click(DB)
    esc = len(pre) + 2
    # one Escape closes it; the second, 14 frames later, clears the value
    DB.render("dark", W, H, script=pre + [at + (False,)] * 46,
              keys=[(esc, imgui.Key.escape), (esc + 14, imgui.Key.escape)],
              keep="last")
    assert DB.render.last_state["plane"] == "", (
        f"a second Escape did not clear the field: "
        f"{DB.render.last_state['plane']!r}")


def test_one_escape_on_its_own_keeps_the_value(DB):
    """The guard that makes the test above mean something: a single Escape
    closes the list and leaves the committed value alone."""
    pre, at = _open_by_click(DB)
    before = DB.CTL_STATE["plane"]
    DB.render("dark", W, H, script=pre + [at + (False,)] * 40,
              keys=[(len(pre) + 2, imgui.Key.escape)], keep="last")
    assert DB.render.last_state["plane"] == before


def test_cleared_is_falsy_so_an_old_caller_is_still_safe(DB):
    """`CLEARED` is an empty `str` subclass on purpose. A caller written
    before it existed does `if got:` and sets nothing - which is the old
    behaviour, not a crash and not a sentinel object landing in somebody's
    state dict and blowing up at the next `D.label`."""
    from hyperspace.dkit import comp_combobox as CC
    assert not CC.CLEARED
    assert CC.CLEARED is not None
    assert CC.CLEARED == ""
    assert isinstance(CC.CLEARED, str)
