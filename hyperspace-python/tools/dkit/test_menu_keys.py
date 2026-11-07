"""A menu's keyboard, one test per measured rule.

The rules are not invented and they are not the Combobox's. They come from
driving the REAL components in Chromium on `?probe` blocks that are NOT
forced open, which is the whole point: a `defaultOpen` component reports
`data-state="open"` whatever you press, so "did this key open it" and "did
this key close it" both come back yes. That is how the Combobox's first
keyboard model came out wrong (RETRO row 17), and it is why these blocks
exist:

    menu.kb              a DropdownMenu with a real trigger - one label, one
                         separator, one DISABLED item, one destructive item,
                         six enabled rows with distinct initials
    menu.long            sixteen rows, for the page keys and the scroll
    contextmenu.target   a ContextMenu, opened with a real right-click
    select.kb            a Select holding `Gamma`
    select.kbnone        the same Select holding nothing

The measured table is in `menu.py`, above THE KEYBOARD, with the block each
row came from named beside it. In short:

    closed  focus alone           stays closed
    closed  click                 opens with NOTHING highlighted
                                  (a Select: on its CHECKED row)
    closed  Enter/Space/Down      opens on the FIRST row
                                  (a Select: on its CHECKED row)
    closed  ArrowUp               does NOT open a menu; opens a Select
    open    ArrowDown, no hl      the first row
    open    ArrowUp, no hl        the LAST row
    open    the arrows on row i   i +- 1, CLAMPING at both ends
    open    Home / End            the ends
    open    PageUp / PageDown     the ends on a MENU; nothing on a Select
    open    a letter              typeahead, by prefix, wrapping, 1s buffer
    open    Enter / Space         takes the highlight, closes
    open    Enter with no hl      nothing at all; stays open
    open    Escape                closes
    open    Tab                   SWALLOWED; stays open

**Two of those differ from the Combobox and porting its table would have got
them wrong.** The arrows CLAMP here where the Combobox falls off either end
into a none-state, and Tab is SWALLOWED here where the Combobox closes and
moves focus on. Both are deliberate in Radix - the menus do not pass `loop`
to their roving-focus group, and the menu content runs
`if (event.key === "Tab") event.preventDefault()`.

Driven on the dashboard, which carries all three users of `menu.popup`: a
kebab menu on every table row, the same menu on a right-click anywhere in a
row, and Selects on the "Plane" and "Mode" rows.
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

W, H = 1440, 1100
# The open fade is `duration-100` and the highlight eases over the same
# 150ms, which is nine frames at 60fps. Forty is well past it: a test that
# reads a fill one frame after the key is reading the ease, not the state.
DWELL = 40

MKEY = "rowmenu.1"            # the kebab menu on table row 1
CKEY = "##ctx.ctx.1"          # the same menu, right-clicked on row 1
PLANE = "##sel.ctl.plane"     # the Plane Select, which HOLDS a value


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


# --------------------------------------------------------------------------
# reading the highlight off the frame
# --------------------------------------------------------------------------

def _row_tops(DB, items, rect):
    """The y of each HIGHLIGHTABLE row, in the order the keyboard counts
    them, for a panel drawn at `rect`.

    Two numbering systems meet here and the test has to use the keyboard's:
    a separator and a label take space in the panel and can never hold the
    highlight, so row 3 of the dashboard's kebab menu is `remove`, the sixth
    ITEM in the list. Walking `menu.row_h` is the only way to get it right -
    the stride is not uniform.
    """
    import menu as M
    px, py, _pw, _ph = rect
    out, iy = [], py + M.PAD
    for it in items:
        if it.kind == "item" and it.enabled:
            out.append(iy)
        iy += M.row_h(it)
    return px, out


def _painted(DB, f, rect):
    """Is a panel actually DRAWN at `rect`? Its ground against `popover`.

    `menu.LAST_RECT` is a seam, not a pixel, and a seam can go stale: until
    this pass `interact.select` only called `menu.popup` while its popup was
    open, so the closed branch that pops the entry never ran and the rect
    outlived the panel for the rest of the process. A test that asked the
    dict whether the panel was up therefore could not fail - which is
    exactly what `test_a_key_on_a_closed_select_trigger_opens_it` did when
    it was run against the unfixed code. So the rect says WHERE and the
    pixels say WHETHER.
    """
    import tokens as T
    px, py, pw, _ph = rect
    want = [round(255 * c) for c in T.rgba("popover", theme=T.DARK)[:3]]
    got = f[int(py) + 2, int(px) + int(pw) // 2].astype(int)
    return max(abs(int(g) - wv) for g, wv in zip(got, want)) <= 2


def _highlight(DB, f, rect, items):
    """Which rows are filled differently from the panel's ground.

    Sampled SIX PIXELS IN - the row's own left padding, where the fill is
    and no glyph ever reaches. The first version of this read a column
    through the text and called every row highlighted, which is the same
    mistake `test_combobox_keys._highlight` records.

    The ground is read from the panel's own padding strip above the first
    row, which is `popover` and nothing else.
    """
    px, tops = _row_tops(DB, items, rect)
    import menu as M
    ground = f[int(rect[1]) + 2, int(px) + int(rect[2]) // 2].astype(int)
    out = []
    for i, ty in enumerate(tops):
        yy = int(ty + M.ITEM_H / 2)
        if abs(f[yy, int(px) + 6].astype(int) - ground).max() > 2:
            out.append(i)
    return out


# --------------------------------------------------------------------------
# driving the dashboard
# --------------------------------------------------------------------------

_SCROLL: dict = {}


def _scrolled(DB):
    """Wheel the page down to the table and return (prefix, rects).

    The table is below the fold at this window height, so a test that wants
    a row has to scroll to it - which is what a person does too.

    CACHED, and that is not a micro-optimisation. Working it out costs a
    whole 1440x1100 render, every helper in this file needs it, and the
    first version did it twice per driven case: `test_enter_and_space...`
    alone came to sixteen renders and killed its pytest-xdist worker. The
    scroll is deterministic, so one answer serves the module.
    """
    if not _SCROLL:
        px, py, pw, ph = (DB.SIDEBAR_W, DB.HEADER_H,
                          W - DB.SIDEBAR_W, H - DB.HEADER_H)
        mx, my = px + pw / 2, py + ph / 2
        prefix = ([(mx, my)] * 4 + [(mx, my, False, -3.0)] * 120
                  + [(mx, my)] * 4)
        DB.render("dark", W, H, script=prefix, keep="last")
        sy = DB.render.last_state["page_scroll"]
        _SCROLL["v"] = (prefix, DB.lay_out(W, H, body_dy=-sy))
    return _SCROLL["v"]


def _kebab(DB):
    prefix, r = _scrolled(DB)
    rx, ry, rw, rh = r.table_rows[1]
    return prefix, rx + rw - 30 + 13, ry + rh / 2, ry


def _open_kebab(DB):
    """Click the kebab open, then park the pointer WELL off the panel.

    Parking matters twice over: a pointer sitting on a row owns the
    highlight, and a pointer that MOVES takes it from the keyboard - so a
    test that left it on the panel would be asserting the mouse's answer
    and calling it the keyboard's. Returns (script, parked_point, key_frame).
    """
    prefix, kx, ky, ry = _kebab(DB)
    park = (kx - 420, ry - 300, False)
    script = (prefix + [(kx, ky)] * 4 + [(kx, ky, True)] * 3
              + [(kx, ky, False)] * 6 + [park] * DWELL)
    return script, park, len(script) - DWELL + 2


def _drive(DB, script, keys=None, key=MKEY):
    import menu as M
    f = np.asarray(DB.render("dark", W, H, script=script, keys=keys,
                             keep="last")[-1])[:, :, :3]
    return f, M.LAST_RECT.get(key)


def _menu_hl(DB, keys, extra=0, key=MKEY, items=None):
    """Open the kebab menu with the pointer, press `keys`, read the
    highlight. Returns (rect_or_None, [row positions])."""
    script, park, at = _open_kebab(DB)
    f, rect = _drive(DB, script + [park] * extra, keys=keys, key=key)
    if rect is None:
        return None, None
    return rect, _highlight(DB, f, rect, items or DB.ROW_MENU)


def _n_items(DB):
    import menu as M
    return len(M.item_rows(DB.ROW_MENU))


# --------------------------------------------------------------------------
# the rules, as pure functions - the columns driving cannot reach
# --------------------------------------------------------------------------

def test_item_rows_skips_separators_labels_and_disabled():
    """The highlight can only land on an enabled item. Measured: a label
    and a separator carry `tabIndex -1` and never hold `data-highlighted`,
    and ArrowDown on `menu.kb` stepped 0 -> 1 -> 3 straight over the
    disabled row at index 2.

    A pure test because the dashboard has no disabled menu item to drive -
    one probe block answers one column, and this is the column the app
    cannot reach.
    """
    import menu as M
    items = [M.Item("a", "Alpha"), M.heading("Group"), M.Item("b", "Beta"),
             M.sep(), M.Item("c", "Gamma", enabled=False),
             M.Item("d", "Delta")]
    assert M.item_rows(items) == [0, 2, 5]
    assert M.highlighted_item(items, 0) == 0
    assert M.highlighted_item(items, 1) == 2
    assert M.highlighted_item(items, 2) == 5
    assert M.highlighted_item(items, 3) is None
    assert M.highlighted_item(items, None) is None


def test_resolve_open_is_the_measured_table():
    """Which row an open highlights, both columns.

    Measured on `select.kb` (holds `Gamma`, index 2) and `select.kbnone`
    (holds nothing): with a value every gesture opens on it; with none they
    open on the FIRST row. And on `menu.kb`, which has no checked item at
    all, a click opens with NOTHING highlighted while Enter, Space and
    ArrowDown open on the first.

    Pure, because both of the dashboard's Selects hold a value - the
    no-value column is not reachable by driving the app at all, which is
    exactly the gap that cost the Combobox a round (RETRO row 26).
    """
    import menu as M
    held = [M.Item("a", "Alpha"), M.Item("b", "Beta", checked=True),
            M.Item("c", "Gamma")]
    none = [M.Item("a", "Alpha"), M.Item("b", "Beta"), M.Item("c", "Gamma")]

    # a listbox: the checked row beats every gesture
    for want in (M.SEL_NONE, M.SEL_FIRST, M.SEL_LAST):
        rows = M.item_rows(held)
        assert M.resolve_open(want, held, rows, on_checked=True) == 1
    # ... and with nothing checked it falls through to the gesture
    rows = M.item_rows(none)
    assert M.resolve_open(M.SEL_FIRST, none, rows, on_checked=True) == 0
    assert M.resolve_open(M.SEL_LAST, none, rows, on_checked=True) == 2
    assert M.resolve_open(M.SEL_NONE, none, rows, on_checked=True) is None

    # a menu does NOT prefer the checked row: that column was never asked,
    # because the probe's DropdownMenu has no checked item, and a
    # measurement that was not made is not a default
    assert M.resolve_open(M.SEL_NONE, held, M.item_rows(held)) is None
    assert M.resolve_open(M.SEL_FIRST, held, M.item_rows(held)) == 0

    # an explicit index passes straight through
    assert M.resolve_open(2, held, M.item_rows(held), on_checked=True) == 2
    # and an empty menu has no row to land on
    assert M.resolve_open(M.SEL_FIRST, [], [], on_checked=True) is None


def test_next_match_is_radix_getnextmatch():
    """Typeahead, which is the thing menus have and comboboxes do not.

    Measured on `menu.kb`: 'e' from Alpha lands on Epsilon; 'd' then lands
    on Delta; 'z' on Zeta; 'g' moves NOTHING because Gamma is disabled; 'q'
    moves nothing; 'a' twice stays on Alpha; and 'e' then 'p' inside the
    second lands on Epsilon rather than looking for a row called "ep".
    """
    import menu as M
    items = [M.Item("a", "Alpha"), M.Item("b", "Beta"),
             M.Item("g", "Gamma", enabled=False), M.Item("d", "Delta"),
             M.Item("e", "Epsilon"), M.Item("z", "Zeta")]
    rows = M.item_rows(items)              # Gamma is not a candidate
    assert M.next_match(items, rows, "e", 0) == 3        # -> Epsilon
    assert M.next_match(items, rows, "d", 3) == 2        # -> Delta
    assert M.next_match(items, rows, "z", 2) == 4        # -> Zeta
    assert M.next_match(items, rows, "g", 4) is None     # Gamma is disabled
    assert M.next_match(items, rows, "q", 4) is None     # no match
    # a one-character search drops the current row, so a single A-row stays
    assert M.next_match(items, rows, "a", 0) is None
    # it starts AFTER the highlight and wraps round
    assert M.next_match(items, rows, "b", 4) == 1
    # two characters accumulate into a prefix
    assert M.next_match(items, rows, "ep", 0) == 3
    assert M.next_match(items, rows, "et", 0) is None
    # a repeated character is that character, so holding it walks the rows
    assert M.next_match(items, rows, "aaa", 1) == 0
    assert M.next_match(items, rows, "", 0) is None
    assert M.next_match(items, [], "e", None) is None


# --------------------------------------------------------------------------
# the dropdown, driven
# --------------------------------------------------------------------------

def test_the_probe_reads_a_highlight_it_is_shown(DB):
    """The highlight reader's own sanity check, and it runs FIRST.

    Three probes in this project's history reported a defect that was not
    there (RETRO row 35), so this one is pointed at a case whose answer is
    not in doubt: the pointer sitting on a row. If this fails, the reader is
    wrong and nothing below it means anything.
    """
    script, _park, _at = _open_kebab(DB)
    f, rect = _drive(DB, script)
    assert rect, "the kebab did not open"
    px, tops = _row_tops(DB, DB.ROW_MENU, rect)
    import menu as M
    for i, ty in enumerate(tops):
        on = (px + rect[2] / 2, ty + M.ITEM_H / 2, False)
        f2, r2 = _drive(DB, script + [on] * DWELL)
        assert _highlight(DB, f2, r2, DB.ROW_MENU) == [i], \
            f"the reader cannot see the pointer's own highlight on row {i}"


def test_a_pointer_opened_menu_highlights_nothing(DB):
    """Measured on `menu.kb` and on `contextmenu.target`: a click - and a
    right-click - opens the panel with NO `data-highlighted` anywhere and
    focus on the content itself.

    Not the Select's rule, and not the Combobox's either.
    """
    rect, hl = _menu_hl(DB, None)
    assert rect, "the kebab did not open"
    assert hl == [], f"a click left something highlighted: {hl}"


def test_the_arrows_take_the_first_and_last_rows_from_nothing(DB):
    """Measured: from the no-highlight state a pointer-opened menu takes the
    FIRST row on ArrowDown and the LAST on ArrowUp - the content's own
    handler, where `FIRST_KEYS` and `LAST_KEYS` live.
    """
    _rect, down = _menu_hl(DB, [(_open_kebab(DB)[2], imgui.Key.down_arrow)])
    assert down == [0], f"ArrowDown did not take the first row: {down}"
    _rect, up = _menu_hl(DB, [(_open_kebab(DB)[2], imgui.Key.up_arrow)])
    assert up == [_n_items(DB) - 1], \
        f"ArrowUp did not take the last row: {up}"


def test_the_arrows_move_one_row_and_step_over_the_furniture(DB):
    """Two rules in one drive, because they are one measurement.

    The arrows move exactly one row, and the dashboard's kebab menu has a
    separator AND a label between its third item and its fourth - so
    arrowing four times has to land on `remove`, the sixth entry in the
    list. A stride that counted items would be two rows out here, and that
    is a real bug the browser cannot show you on a menu without furniture.
    """
    at = _open_kebab(DB)[2]
    n = _n_items(DB)
    for presses in range(1, n + 1):
        keys = [(at + 8 * i, imgui.Key.down_arrow) for i in range(presses)]
        _rect, hl = _menu_hl(DB, keys, extra=8 * presses + 10)
        assert hl == [presses - 1], \
            f"{presses} ArrowDowns landed on {hl}, not [{presses - 1}]"


def test_the_arrows_clamp_rather_than_wrapping(DB):
    """**The rule a port of the Combobox's table would have got wrong.**

    Measured on `menu.kb`: ArrowDown x24 off the bottom of a six-row menu
    sits on the last row and ArrowUp x20 off the top sits on the first.
    There is no wrap and no none-state between the ends. The Combobox does
    the opposite - it falls off either end into nothing - and the kit's
    menus used to wrap, because ImGui's own nav was driving them.
    """
    at = _open_kebab(DB)[2]
    n = _n_items(DB)
    over = n + 4
    keys = [(at + 6 * i, imgui.Key.down_arrow) for i in range(over)]
    rect, hl = _menu_hl(DB, keys, extra=6 * over + 20)
    assert rect, "the menu closed"
    assert hl == [n - 1], \
        f"going down off the last row gave {hl}, not a clamp on [{n - 1}]"
    keys += [(at + 6 * over + 6 * i, imgui.Key.up_arrow)
             for i in range(over)]
    rect, hl = _menu_hl(DB, keys, extra=12 * over + 20)
    assert rect, "the menu closed"
    assert hl == [0], f"going up off the first row gave {hl}, not [0]"


def test_home_end_pageup_and_pagedown_go_to_the_ends(DB):
    """All four, and PageUp / PageDown are the pair that make a menu a menu.

    Measured: Radix maps PageUp and Home onto `first` and PageDown and End
    onto `last` - NOT onto a page of rows. Sixteen rows behaved exactly as
    six did, which is what settles it. A Select ignores the page keys
    entirely; that is the next test but one.
    """
    at = _open_kebab(DB)[2]
    n = _n_items(DB)
    for name, k, want in (("Home", imgui.Key.home, [0]),
                          ("PageUp", imgui.Key.page_up, [0]),
                          ("End", imgui.Key.end, [n - 1]),
                          ("PageDown", imgui.Key.page_down, [n - 1])):
        _rect, hl = _menu_hl(DB, [(at, k)], extra=10)
        assert hl == want, f"{name} gave {hl}, not {want}"


def test_a_letter_jumps_to_a_matching_row(DB):
    """Typeahead, driven. The dashboard's kebab menu is Open / Copy
    Schlafli / Pin to scene / Remove from view, so the four initials are
    distinct and a letter has exactly one answer.

    A letter rather than a key event on purpose: `is_key_pressed` cannot
    tell you which CHARACTER a layout produced, and the real component
    keys off `event.key.length === 1`. The dashboard's harness feeds a str
    through `add_input_character`, which is the same path GLFW uses.
    """
    at = _open_kebab(DB)[2]
    for ch, want in (("o", 0), ("c", 1), ("p", 2), ("r", 3)):
        _rect, hl = _menu_hl(DB, [(at, ch)], extra=10)
        assert hl == [want], f"typing {ch!r} gave {hl}, not [{want}]"
    # no match leaves the highlight exactly where it was - here, nowhere
    _rect, hl = _menu_hl(DB, [(at, "q")], extra=10)
    assert hl == [], f"a letter matching nothing moved the highlight: {hl}"


def test_typeahead_accumulates_inside_the_second_and_then_clears(DB):
    """Measured: 'e' then 'p' inside the second lands on Epsilon; 'e', a
    1.3s wait, then 'p' lands on Pi. Radix clears the buffer on a 1000ms
    timer, which is `menu.TYPEAHEAD_HOLD`.

    Driven on `Pin to scene` and `Copy Schlafli`: 'p' then 'i' inside the
    second is the prefix "pi", which only Pin answers. Sixty frames apart -
    a second at 60fps - the 'i' is a search of its own and matches nothing,
    so the highlight stays on Pin either way. What distinguishes the two is
    the row 'c' then 'o' reaches: as "co" it is Copy, and as two searches
    the 'o' is Open.
    """
    at = _open_kebab(DB)[2]
    _rect, fast = _menu_hl(DB, [(at, "c"), (at + 4, "o")], extra=20)
    assert fast == [1], f"'co' inside the second gave {fast}, not Copy"
    _rect, slow = _menu_hl(DB, [(at, "c"), (at + 70, "o")], extra=90)
    assert slow == [0], \
        f"'c' then a pause then 'o' gave {slow}, not Open - the buffer " \
        f"did not clear"


def _take(DB, presses, k):
    """Arrow down `presses` times, press `k`, and return what the dashboard
    says was chosen."""
    import menu as M
    script, park, at = _open_kebab(DB)
    keys = [(at + 8 * i, imgui.Key.down_arrow) for i in range(presses)]
    keys.append((at + 8 * presses + 6, k))
    DB.render("dark", W, H, script=script + [park] * (8 * presses + 40),
              keys=keys, keep="last")
    return M.LAST_RECT.get(MKEY), DB.render.last_state.get("said") or ""


def test_enter_takes_the_highlighted_row(DB):
    """Measured: Enter closes the panel and fires the row.

    Driven on all four rows, because the fourth is past the separator AND
    the label - the row a stride that counted items rather than ROWS gets
    wrong, and no menu in the browser probe has furniture in it to show
    that.
    """
    ids = [it.id for it in DB.ROW_MENU if it.kind == "item" and it.enabled]
    for presses, want in enumerate(ids, start=1):
        rect, said = _take(DB, presses, imgui.Key.enter)
        assert rect is None, f"Enter on row {presses - 1} left it open"
        assert said.startswith(want + " "), \
            f"Enter on row {presses - 1} fired {said!r}, not {want!r}"


def test_space_takes_the_highlighted_row(DB):
    """Space is the menu's second selection key - `SELECTION_KEYS` is
    `["Enter", " "]` - and measured, it closes and fires exactly as Enter
    does. One row rather than four: the stride is Enter's test above, and
    what is new here is the key.
    """
    rect, said = _take(DB, 2, imgui.Key.space)
    assert rect is None, "Space did not close the menu"
    assert said.startswith("copy "), f"Space fired {said!r}, not `copy`"


def test_enter_with_nothing_highlighted_does_nothing_at_all(DB):
    """Measured on a pointer-opened `menu.kb`: Enter and Space with no
    `data-highlighted` leave the menu OPEN and choose nothing.

    Not the Combobox's rule, where an Enter with no highlight closes the
    list and reverts the query. A menu has nothing to revert.
    """
    import menu as M
    at = _open_kebab(DB)[2]
    for name, k in (("Enter", imgui.Key.enter), ("Space", imgui.Key.space)):
        script, park, _ = _open_kebab(DB)
        DB.render("dark", W, H, script=script + [park] * 30,
                  keys=[(at, k)], keep="last")
        assert M.LAST_RECT.get(MKEY), f"{name} closed a menu with no highlight"
        assert not DB.render.last_state.get("said"), \
            f"{name} chose a row with nothing highlighted"


def test_escape_closes_the_menu(DB):
    """ImGui's own, and it stays ImGui's: a menu holds no text field, so
    nothing eats the key the way an `InputText` eats the Combobox's first
    Escape. Asserted rather than implemented, so a future change that adds
    a field to a menu fails here instead of silently needing two presses.
    """
    import menu as M
    at = _open_kebab(DB)[2]
    script, park, _ = _open_kebab(DB)
    DB.render("dark", W, H, script=script + [park] * 24,
              keys=[(at, imgui.Key.escape)], keep="last")
    assert M.LAST_RECT.get(MKEY) is None, "Escape did not close the menu"


def test_tab_is_swallowed_and_the_menu_stays_open(DB):
    """**The opposite of the Combobox, and the rule most likely to be got
    wrong by analogy.**

    Measured on `menu.kb`: three Tabs and a Shift+Tab all leave the menu
    open on the same row. Radix's menu content runs
    `if (event.key === "Tab") event.preventDefault()` - it is a modal
    roving-focus layer and the only ways out are Escape, Enter, Space and a
    click.

    The kit satisfies this because ImGui will not tab out of a popup and
    every menu row is submitted `nav=False`, so there is nothing inside one
    for a Tab to reach. Both halves are load-bearing and neither is
    obvious, which is why this is driven rather than argued.
    """
    import menu as M
    at = _open_kebab(DB)[2]
    script, park, _ = _open_kebab(DB)
    keys = [(at + 6 * i, imgui.Key.tab) for i in range(4)]
    f = np.asarray(DB.render("dark", W, H, script=script + [park] * 40,
                             keys=keys, keep="last")[-1])[:, :, :3]
    rect = M.LAST_RECT.get(MKEY)
    assert rect, "Tab closed the menu; the real one swallows it"
    assert _highlight(DB, f, rect, DB.ROW_MENU) == [], \
        "a Tab moved the highlight"


def test_a_parked_pointer_does_not_override_the_arrows(DB):
    """The pointer takes the highlight when it MOVES and not otherwise.

    Radix hands it over on `onPointerMove`; taking it every frame would let
    a mouse resting on row 0 fight every arrow press, which is the whole
    reason cmdk carries `disablePointerSelection`. ImGui's hover is
    positional, so this one cannot be inherited - it has to be written, and
    it has to be driven to be believed.
    """
    import menu as M
    script, _park, at = _open_kebab(DB)
    f, rect = _drive(DB, script)
    assert rect, "the kebab did not open"
    px, tops = _row_tops(DB, DB.ROW_MENU, rect)
    on = (px + rect[2] / 2, tops[0] + M.ITEM_H / 2, False)
    # park ON row 0, then arrow twice: the keyboard must win
    base = len(script) + 6
    f2, r2 = _drive(DB, script + [on] * (DWELL + 30),
                    keys=[(base, imgui.Key.down_arrow),
                          (base + 10, imgui.Key.down_arrow)])
    # [2], not [0] and not [1]: the pointer ARRIVING on row 0 took the
    # highlight, which is right, and then the two arrows walked it to row 2
    # and it STAYED there for thirty more frames with the mouse still
    # sitting on row 0. A highlight taken every frame reads [0] here.
    assert _highlight(DB, f2, r2, DB.ROW_MENU) == [2], \
        "a parked pointer took the highlight back from the arrows"


def test_the_opening_key_is_not_also_processed_by_the_panel(DB):
    """The off-by-one that cost the Combobox a round, on the Select.

    The open happens in the parent window and the panel's own handler runs
    later in the SAME frame, so without `menu.arm` an opening ArrowDown
    lands one row past the row the open chose, and an opening Enter opens
    the panel and commits a row in one frame - which looks like a click
    that went nowhere.

    Driven on the Plane Select, which is the only trigger in the kit a key
    can open: the kebab is inside the page's scroll window, and ImGui's Tab
    never leaves the window it starts in, so the dropdown has no keyboard
    route to its own trigger yet.
    """
    import menu as M
    at = _committed(DB)
    for name, k in (("ArrowDown", imgui.Key.down_arrow),
                    ("ArrowUp", imgui.Key.up_arrow),
                    ("Enter", imgui.Key.enter),
                    ("Space", imgui.Key.space)):
        rect, hl = _select_hl(DB, k)
        assert rect, f"{name} did not reopen the Select"
        assert hl == [at], \
            f"{name} opened the Select on {hl}, not the committed row [{at}]"


# --------------------------------------------------------------------------
# the ContextMenu: the same panel, a different gesture
# --------------------------------------------------------------------------

def _open_context(DB):
    """Right-click row 1 open, then park the pointer off the panel."""
    prefix, _kx, _ky, ry = _kebab(DB)
    _p, r = _scrolled(DB)
    rx, rry, rw, rh = r.table_rows[1]
    x, y = rx + 200, rry + rh / 2
    park = (rx + 40, ry - 300, False, 0.0, False)
    script = (prefix + [(x, y)] * 6 + [(x, y, False, 0.0, True)] * 2
              + [(x, y, False, 0.0, False)] * 4 + [park] * DWELL)
    return script, park, len(script) - DWELL + 2


def test_a_right_clicked_menu_answers_the_same_keys(DB):
    """A ContextMenu is `menu.popup` placed at the pointer, and measured on
    `contextmenu.target` its keyboard is the DropdownMenu's to the key: no
    highlight on open, ArrowDown to the first, ArrowUp to the last, Home and
    End to the ends, a clamp at both ends, typeahead, Enter taking the row
    and Tab swallowed.

    So `comp_context_menu.py` needs no keyboard of its own - it inherits
    one, which is the point of putting the model in `menu.popup`. This test
    is what makes "it inherits" a claim rather than a hope.
    """
    import menu as M
    n = _n_items(DB)
    script, park, at = _open_context(DB)

    f, rect = _drive(DB, script, key=CKEY)
    assert rect, "the right-click did not open the context menu"
    assert _highlight(DB, f, rect, DB.ROW_MENU) == [], \
        "a right-click left something highlighted"

    cases = [("ArrowDown", [(at, imgui.Key.down_arrow)], 10, [0]),
             ("ArrowUp", [(at, imgui.Key.up_arrow)], 10, [n - 1]),
             ("End", [(at, imgui.Key.end)], 10, [n - 1]),
             ("Home", [(at, imgui.Key.home)], 10, [0]),
             ("typed 'p'", [(at, "p")], 10, [2]),
             ("ArrowDown x%d" % (n + 3),
              [(at + 6 * i, imgui.Key.down_arrow) for i in range(n + 3)],
              6 * (n + 3) + 20, [n - 1])]
    for name, keys, extra, want in cases:
        f, rect = _drive(DB, script + [park] * extra, keys=keys, key=CKEY)
        assert rect, f"{name} closed the context menu"
        got = _highlight(DB, f, rect, DB.ROW_MENU)
        assert got == want, f"context menu, {name}: {got} not {want}"

    # Tab is swallowed here too
    f, rect = _drive(DB, script + [park] * 20,
                     keys=[(at, imgui.Key.tab)], key=CKEY)
    assert rect, "Tab closed the context menu"

    # and Enter takes the highlight
    DB.render("dark", W, H, script=script + [park] * 40,
              keys=[(at, imgui.Key.down_arrow),
                    (at + 10, imgui.Key.enter)], keep="last")
    assert M.LAST_RECT.get(CKEY) is None, "Enter did not close it"
    assert (DB.render.last_state.get("ctx") or "").startswith("open "), \
        f"Enter fired {DB.render.last_state.get('ctx')!r}, not `open`"


# --------------------------------------------------------------------------
# the Select: the same panel with a listbox's two differences
# --------------------------------------------------------------------------

def _plane_trigger(DB):
    r = DB.lay_out(W, H)
    ex, ey, ew, eh = r.ctl_rows[2]
    return ex + DB.CTL_LABEL_W, ey, min(ew - DB.CTL_LABEL_W, 130.0), eh


def _committed(DB):
    """Which row of the Plane Select carries the check."""
    return list(DB.PLANES).index(DB.CTL_STATE["plane"])


def _plane_items(DB):
    import menu as M
    return [M.Item(id=p, label=p, checked=(p == DB.CTL_STATE["plane"]))
            for p in DB.PLANES]


def _open_plane(DB):
    """Click the Plane Select open, then park the pointer off the panel."""
    x, y, w, h = _plane_trigger(DB)
    on = (x + 20, y + h / 2)
    park = (x - 300, y - 300, False)
    script = ([(10, 10, False)] * 6 + [on] * 4 + [(*on, True)] * 3
              + [(*on, False)] * 6 + [park] * DWELL)
    return script, park, len(script) - DWELL + 2


def _select_frame(DB, opener):
    """Escape the open panel - which leaves nav focus on the trigger, the
    way a real Escape does - then press `opener`. Returns (frame, rect).

    This is the only route to the Select's trigger from the keyboard in a
    driven test: ImGui's Tab never leaves the window it starts in, and both
    Selects are inside the page's scroll window. `test_combobox_keys` uses
    the same trick for the same reason.
    """
    script, park, at = _open_plane(DB)
    return _drive(DB, script + [park] * 46,
                  keys=[(at, imgui.Key.escape), (at + 16, opener)],
                  key=PLANE)


def _select_hl(DB, opener):
    """`_select_frame`, and the highlight read off it."""
    f, rect = _select_frame(DB, opener)
    if rect is None or not _painted(DB, f, rect):
        return None, None
    return rect, _highlight(DB, f, rect, _plane_items(DB))


def test_a_select_opens_on_its_committed_row(DB):
    """**RETRO row 26, one component over.** Measured on `select.kb`, which
    holds `Gamma`: a click, Enter, Space, ArrowDown and ArrowUp all open the
    panel with Gamma highlighted AND ticked - never with the first row
    highlighted and never with none.

    The valueless column is `select.kbnone`, where all four open on the
    first row; it is covered as a pure test of `resolve_open`, because both
    of the dashboard's Selects hold a value.
    """
    at = _committed(DB)
    script, park, _ = _open_plane(DB)
    f, rect = _drive(DB, script, key=PLANE)
    assert rect, "the click did not open the Select"
    assert _highlight(DB, f, rect, _plane_items(DB)) == [at], \
        "a click did not open the Select on its committed row"


def test_a_key_on_a_closed_select_trigger_opens_it(DB):
    """Measured on `select.kb`: Enter, Space, ArrowDown AND ArrowUp all open
    a Select. ArrowUp is the one that distinguishes it from a DropdownMenu,
    whose trigger answers `["Enter", " ", "ArrowDown"]` and is inert under
    ArrowUp.

    Before this, no key opened the kit's Select at all - the trigger was a
    hit target and nothing read a key near it.
    """
    for name, k in (("Enter", imgui.Key.enter), ("Space", imgui.Key.space),
                    ("ArrowDown", imgui.Key.down_arrow),
                    ("ArrowUp", imgui.Key.up_arrow)):
        f, rect = _select_frame(DB, k)
        assert rect and _painted(DB, f, rect), \
            f"{name} did not open the Select"


def test_focus_alone_does_not_open_a_select(DB):
    """The companion to the test above, so "a key opens it" cannot be
    satisfied by opening on focus. Measured: a Tab onto the trigger rings it
    and leaves the panel shut.

    Driven as the trigger holding nav focus after an Escape, with no key
    pressed afterwards - the same state the openers are tested from.
    """
    import menu as M
    script, park, at = _open_plane(DB)
    f = np.asarray(DB.render("dark", W, H, script=script + [park] * 46,
                             keys=[(at, imgui.Key.escape)],
                             keep="last")[-1])[:, :, :3]
    rect = M.LAST_RECT.get(PLANE)
    assert rect is None or not _painted(DB, f, rect), \
        "the focused trigger reopened its own panel with no key pressed"


def test_the_page_keys_do_nothing_on_a_select(DB):
    """The one measured keyboard difference between a menu and a listbox,
    and it is a difference of ABSENCE, which is the kind that gets ported by
    accident.

    Measured on `select.kb`: Home takes the first row and End the last, and
    PageUp and PageDown do nothing whatever - Radix's `SelectContentImpl`
    handles the arrows plus Home and End and no more. On a DropdownMenu all
    four move the highlight to an end.
    """
    at = _committed(DB)
    n = len(DB.PLANES)
    script, park, base = _open_plane(DB)
    for name, k, want in (("Home", imgui.Key.home, [0]),
                          ("End", imgui.Key.end, [n - 1]),
                          ("PageUp", imgui.Key.page_up, [at]),
                          ("PageDown", imgui.Key.page_down, [at])):
        f, rect = _drive(DB, script + [park] * 14, keys=[(base, k)],
                         key=PLANE)
        assert rect, f"{name} closed the Select"
        got = _highlight(DB, f, rect, _plane_items(DB))
        assert got == want, f"Select, {name}: {got} not {want}"


def test_a_select_commits_the_highlighted_row(DB):
    """Enter closes the panel and sets the value, which is the half a
    highlight test cannot see. Measured: after Enter the trigger holds the
    new value and `document.activeElement` is the trigger again.
    """
    import menu as M
    was = DB.CTL_STATE["plane"]
    at = _committed(DB)
    script, park, base = _open_plane(DB)
    DB.render("dark", W, H, script=script + [park] * 60,
              keys=[(base, imgui.Key.down_arrow),
                    (base + 12, imgui.Key.enter)], keep="last")
    assert M.LAST_RECT.get(PLANE) is None, "Enter did not close the Select"
    assert DB.render.last_state["plane"] == DB.PLANES[at + 1], \
        f"Enter committed {DB.render.last_state['plane']!r}, not the row " \
        f"below {was!r}"


def test_a_select_answers_typeahead(DB):
    """Measured on `select.kb`: typing a letter with the panel open jumps to
    the next row whose label starts with it, wrapping from the row after the
    highlight. The planes are XY XZ XW YZ YW ZW with XW committed, so a 'y'
    from row 2 is YZ at row 3 and a 'z' is ZW at row 5.
    """
    script, park, base = _open_plane(DB)
    for ch, want in (("y", 3), ("z", 5)):
        f, rect = _drive(DB, script + [park] * 14, keys=[(base, ch)],
                         key=PLANE)
        assert rect, f"typing {ch!r} closed the Select"
        got = _highlight(DB, f, rect, _plane_items(DB))
        assert got == [want], f"Select, typed {ch!r}: {got} not [{want}]"
