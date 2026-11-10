"""The submenu, pinned to what Chromium actually does.

Every number here came out of `probe_submenu.js` driving the real
ContextMenu on `?probe`'s `contextmenu.sub` and `contextmenu.subwide`
blocks, in both themes - not out of the Tailwind classes, which cannot
answer any of the four things that matter:

* a SubContent carries `border`, a real CSS border INSIDE the box, where
  the top panel's outline is a `ring-1` box-shadow outside it. That one
  pixel a side is why the measured panel is 103 tall for 101px of rows;
* it is `shadow-lg`, not the panel's `shadow-md`;
* it lands on the **trigger row**, not on the panel: x = trigger.right
  (which is 4px INSIDE the parent's right edge), y = trigger.y;
* the hover delay is 100 ms, and a delay is not in a class at all.

The pure half runs anywhere. The driven half needs GL and skips without a
display, the way the project's other GL tests do - it is there because a
submenu is a gesture before it is a panel, and three of the things that can
go wrong (ImGui stealing focus into the child, the parent going dead to the
mouse, a dwell pouring from one row into the next) are invisible to a
measurement of the chrome.

    uv run python -m pytest hyperspace/dkit/dev/test_submenu.py -q
"""

from __future__ import annotations

import sys
import typing
from pathlib import Path

import numpy as np
import pytest
from imgui_bundle import imgui

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))

from hyperspace.dkit import menu as M
from hyperspace.dkit import tokens as T
from hyperspace.dkit.box import Rect

W, H = 1440, 1100
DWELL = 40          # frames; past the 100ms open fade and the 150ms ease

CKEY = "##ctx.ctx.0"            # row 0's context menu: the submenu's ground
SUBKEY = f"{CKEY}>insert"       # its `insert` panel
DEEPKEY = f"{SUBKEY}>insert.deep"

# the measured panel: item, item, separator, item inside p-1 and a border
MEASURED_SUB = (128.0, 103.0)


# --------------------------------------------------------------------------
# the measured table
# --------------------------------------------------------------------------

def test_the_sub_panel_floor_is_min_w_32_not_the_context_menus_144():
    """A SubContent is `min-w-32`; the ContextMenu panel's own floor is
    `min-w-36`. Measured 128.000 against 144.000 in the same menu."""
    assert M.SUB_MIN_W == 128.0
    from hyperspace.dkit.comp_context_menu import CONTEXT_MENU
    assert CONTEXT_MENU["min_w"] == 144.0


def test_the_sub_panel_carries_a_border_inside_the_box():
    """`border`, not `ring-1`. Measured borderTopWidth 1px solid with the
    border colour in both themes (light oklch(0.922 0 0), dark
    oklch(1 0 0 / 0.1)) - which is the `border` token either way - and the
    first row at panel.y + 5 rather than + 4."""
    assert M.SUB_BORDER == 1.0


def test_the_sub_panel_is_shadow_lg():
    """Measured `rgba(0,0,0,.1) 0 10 15 -3` + `rgba(0,0,0,.1) 0 4 6 -4`,
    identical in both themes - the panel's own is shadow-md."""
    assert M.SUB_SHADOW == T.SHADOW_LG
    assert M.SUB_SHADOW != T.SHADOW_MD


def test_the_hover_delay_is_a_tenth_of_a_second():
    """Radix's 100 ms timer, driven: 114, 123 and 129 ms with a 10 ms
    poll."""
    assert M.SUB_OPEN_S == 0.10


def test_the_height_law_reproduces_the_measured_panel():
    """103 = 1 + 4 + 28 + 28 + 9 + 28 + 4 + 1, which is the panel to the
    pixel. The rows are the probe's: two items, a separator, one item."""
    rows = sum(M.row_h(it) for it in (
        M.Item(label="Gain"), M.Item(label="Curve"), M.sep(),
        M.Item(label="Remove", variant="destructive")))
    assert rows == 93.0
    assert rows + 2 * (M.PAD + M.SUB_BORDER) == MEASURED_SUB[1]


def test_is_sub_is_what_carries_items():
    assert not M.is_sub(M.Item(label="Open"))
    assert not M.is_sub(M.sep())
    assert M.is_sub(M.Item(label="Insert", items=(M.Item(label="Gain"),)))


def test_a_sub_trigger_can_hold_the_highlight():
    """It is an item: measured, ArrowDown lands on it and ArrowRight then
    opens it, so `item_rows` must count it."""
    items = [M.Item("a", "Open"), M.Item("b", "Insert", items=(M.Item("c", "Gain"),))]
    assert M.item_rows(items) == [0, 1]


def test_a_panel_is_capped_and_a_long_row_is_cut_to_it(monkeypatch):
    """`MAX_W` is the kit's own policy, not the browser's.

    A shadcn item carries no `truncate`, so in the browser a long row makes
    the panel as wide as its words. A menu row here is one line and the
    graph's insert menu carries whole sentences — "faces pattern: Faces
    pattern is in the graph already: drag it onto the cable" — which made a
    980px panel over the canvas. Capped, the row is ellipsised and the
    words that were cut are the row's tooltip (`ui_menu._tips_kit`).
    """
    from hyperspace.dkit import draw as D
    monkeypatch.setattr(D, "text_w", lambda text, *a, **k: 9.0 * len(text))

    class FakeUi:
        faces: typing.ClassVar[dict] = {}

    long = M.Item("a", "faces pattern: Faces pattern is in the graph already: "
                       "drag it onto the cable")
    w, _h = M.measure(FakeUi(), [long])
    assert w == M.MAX_W - 2 * M.PAD, "the panel was not capped"
    # uncapped it is as wide as the whole sentence, which is the bug: the
    # panel the owner saw over the canvas was ~980px
    uncapped = M.measure(FakeUi(), [long], max_w=0.0)[0]
    assert uncapped == 9.0 * len(long.label) + 2 * M.ITEM_PAD_X
    assert uncapped > 2 * M.MAX_W


def test_a_row_keeps_room_for_its_chevron_and_its_shortcut(monkeypatch):
    """`label_room` is `measure`'s reservation read the other way round, so
    an ellipsised label cannot run under the chevron or off the panel."""
    from hyperspace.dkit import draw as D
    monkeypatch.setattr(D, "text_w", lambda text, *a, **k: 9.0 * len(text))

    class FakeUi:
        faces: typing.ClassVar[dict] = {}

    ui = FakeUi()
    plain = M.Item("a", "Open")
    sub = M.Item("b", "Insert", items=(M.Item("c", "x"),))
    cut = M.Item("d", "Copy", shortcut="\u2318C")
    assert M.label_room(plain, 200.0, ui) == 200.0 - 2 * M.ITEM_PAD_X
    assert M.label_room(plain, 200.0, ui) - M.label_room(sub, 200.0, ui) == M.GAP + M.ICON
    assert M.label_room(cut, 200.0, ui) < M.label_room(plain, 200.0, ui)
    assert M.label_room(plain, 4.0, ui) == 0.0          # never negative


def test_the_width_law_reserves_the_chevron_with_one_gap(monkeypatch):
    """Measured at max-content: a 221.3594 row = 6 + 187.3594 + 6 + 16 + 6.
    ONE gap, exactly as a shortcut gets one - reserving two would make
    every menu holding a submenu 6px wide of the browser.

    `text_w` is stubbed because the law is the reservation EITHER SIDE of
    the label, not the label: a real width needs a font atlas and a GL
    context, and neither would make this test say more.
    """
    from hyperspace.dkit import draw as D
    monkeypatch.setattr(D, "text_w", lambda text, *a, **k: 100.0)

    class FakeUi:
        faces: typing.ClassVar[dict] = {}

    plain, _ = M.measure(FakeUi(), [M.Item("a", "Open")], 0.0)
    sub, _ = M.measure(FakeUi(), [M.Item("a", "Open", items=(M.Item("b", "x"),))], 0.0)
    assert plain == 100.0 + 2 * M.ITEM_PAD_X
    assert sub - plain == M.GAP + M.ICON


# --------------------------------------------------------------------------
# the placement law
# --------------------------------------------------------------------------

VIEW = Rect(0, 0, 1000, 800)
TRIG = Rect(100, 200, 136, M.ITEM_H)


def test_it_lands_on_the_trigger_not_on_the_panel():
    """Measured dx 0.000 from the trigger's RIGHT edge and dy 0.000 from
    its top - which is -4 from the panel's right edge, because the trigger
    is inset by the panel's own p-1."""
    r = M.place_sub(TRIG, *MEASURED_SUB, VIEW)
    assert (r.x, r.y) == (TRIG.right, TRIG.y)
    assert (r.w, r.h) == MEASURED_SUB


def test_a_tuple_trigger_is_accepted():
    r = M.place_sub((100, 200, 136, 28), *MEASURED_SUB, VIEW)
    assert (r.x, r.y) == (236, 200)


def test_it_flips_to_the_left_when_the_right_does_not_fit():
    """Radix does NOT: measured in a 250px viewport the panel stayed at
    trigger.right and hung 20px off the edge. This flips instead, because
    an ImGui popup that leaves the window is lost - the same divergence
    `place_at_pointer` records, for the same reason."""
    trig = Rect(820, 200, 136, M.ITEM_H)
    r = M.place_sub(trig, *MEASURED_SUB, VIEW)
    assert r.x == trig.x - MEASURED_SUB[0]


def test_it_keeps_the_side_that_overflows_less_when_neither_fits():
    narrow = Rect(0, 0, 200, 800)
    trig = Rect(60, 100, 100, M.ITEM_H)
    r = M.place_sub(trig, *MEASURED_SUB, narrow)
    # right overflows by 160 + 128 - 200 = 88, left by 128 - 60 = 68
    assert r.x == 0                       # the left side, then clamped in
    assert r.right <= narrow.right


def test_it_never_leaves_the_viewport():
    for ty in (-50, 0, 400, 790, 1200):
        for tx in (-30, 0, 500, 980):
            r = M.place_sub(Rect(tx, ty, 136, M.ITEM_H), *MEASURED_SUB, VIEW)
            assert r.x >= VIEW.x and r.right <= VIEW.right
            assert r.y >= VIEW.y and r.bottom <= VIEW.bottom


def test_a_panel_taller_than_the_view_pins_to_the_top():
    short = Rect(0, 0, 1000, 60)
    r = M.place_sub(TRIG, 128.0, 300.0, short)
    assert r.y == 0 and r.h == 60


# --------------------------------------------------------------------------
# driven: the gesture
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# the chain keeps one side, and the safe triangle
# --------------------------------------------------------------------------

def test_a_chain_picks_its_side_from_the_widest_panel_it_could_draw():
    """`chain_side` answers for the WHOLE chain, not for the panel in
    hand: a side with room for `MAX_W` has room for every level."""
    view = Rect(0, 0, 1000, 800)
    assert M.chain_side(Rect(100, 200, 136, M.ITEM_H), view) == "right"
    # 700 + 136 = 836, and 836 + 320 > 1000: a narrow panel would still fit
    # to the right, which is exactly the trap
    trig = Rect(700, 200, 136, M.ITEM_H)
    assert trig.right + M.SUB_MIN_W < view.right          # the narrow one fits
    assert M.chain_side(trig, view) == "left"             # the chain still goes left


def test_neither_side_roomy_takes_the_roomier_one():
    view = Rect(0, 0, 400, 800)
    assert M.chain_side(Rect(40, 0, 100, M.ITEM_H), view) == "right"
    assert M.chain_side(Rect(260, 0, 100, M.ITEM_H), view) == "left"


def test_a_given_side_is_obeyed_however_wide_the_panel():
    """The point of the chain's side: a level that would not have chosen it
    still uses it, so the menus cannot jump between levels."""
    view = Rect(0, 0, 1000, 800)
    trig = Rect(700, 200, 136, M.ITEM_H)
    assert M.place_sub(trig, 128.0, 90.0, view, "left").x == trig.x - 128
    assert M.place_sub(trig, 128.0, 90.0, view, "right").x == trig.right
    # and with no side given it still works it out for itself, as before
    assert M.place_sub(trig, 128.0, 90.0, view).x == trig.right


def test_the_safe_triangle_is_the_wedge_to_the_panels_near_edge():
    """Amazon's golden triangle: while the pointer is inside the wedge from
    where it was to the panel's near edge, it is on its way there — and the
    rows it crosses on the diagonal do nothing."""
    panel = (300.0, 100.0, 128.0, 200.0)        # to the RIGHT of the pointer
    was = (200.0, 110.0)
    assert M.aiming_at(was, (250.0, 150.0), panel)      # diagonal, inside
    assert M.aiming_at(was, (280.0, 240.0), panel)      # steep, still inside
    assert not M.aiming_at(was, (290.0, 290.0), panel)  # under the wedge's edge
    assert not M.aiming_at(was, (250.0, 400.0), panel)  # past the bottom corner
    assert not M.aiming_at(was, (210.0, 10.0), panel)   # away, above it
    assert not M.aiming_at(None, (250.0, 150.0), panel)
    assert not M.aiming_at(was, (250.0, 150.0), None)


def test_a_parked_pointer_is_aiming_at_nothing():
    """A zero-length move makes a degenerate triangle, which contains every
    point — so without this the wedge reads "true" for as long as the hand
    rests on the trigger, and its patience is spent before the move it
    exists for begins. Measured in the app: five seconds of it, and the
    diagonal then failed on its first step."""
    panel = (300.0, 100.0, 128.0, 200.0)
    assert not M.aiming_at((250.0, 150.0), (250.0, 150.0), panel)


def test_a_pointer_already_over_the_panel_is_not_aiming():
    """Inside it is not toward it: the panel keeps itself open from there,
    and a wedge over its own rows would swallow their hover."""
    panel = (300.0, 100.0, 128.0, 200.0)
    assert not M.aiming_at((200.0, 110.0), (350.0, 150.0), panel)


def test_the_wedge_works_leftward_too():
    """A chain on the left of its trigger needs the mirror of it."""
    panel = (100.0, 100.0, 128.0, 200.0)        # to the LEFT of the pointer
    was = (300.0, 110.0)
    assert M.aiming_at(was, (250.0, 150.0), panel)
    assert not M.aiming_at(was, (250.0, 400.0), panel)


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


@pytest.fixture(autouse=True)
def _fresh_rects():
    """`menu.LAST_RECT` is module state and these tests assert on its
    ABSENCE, so a panel another test left in it reads here as a panel that
    is open. Cleared each time rather than trusted: the entry for a panel
    ImGui closed with its parent is dropped by `_forget` on the next frame
    the parent is submitted, and a test that never submits it again would
    be asking a stale dict."""
    M.LAST_RECT.clear()
    yield
    M.LAST_RECT.clear()


def _page_view(DB, h=H):
    """The page's scroll viewport, as `test_interaction.page_view` has it:
    everything below the header and right of the sidebar."""
    return (DB.SIDEBAR_W, DB.HEADER_H, W - DB.SIDEBAR_W, h - DB.HEADER_H)


def _row0(DB, h=H):
    """A script prefix that wheels the table into view, and row 0's rect."""
    px, py, pw, ph = _page_view(DB, h)
    mx, my = px + pw / 2, py + ph / 2
    prefix = [(mx, my)] * 4 + [(mx, my, False, -3.0)] * 120 + [(mx, my)] * 4
    DB.render("dark", W, h, script=prefix, keep="last")
    sy = DB.render.last_state["page_scroll"]
    return prefix, DB.lay_out(W, h, body_dy=-sy).table_rows[0]


def _open(DB, h=H, at_x=200.0):
    """The script that right-clicks row 0 open, and where it clicked.

    `at_x` is how far into the row the click lands, which is how a test
    puts the menu near the window's right edge.
    """
    prefix, (rx, ry, _rw, rh) = _row0(DB, h)
    x, y = rx + at_x, ry + rh / 2
    script = (prefix + [(x, y)] * 8 + [(x, y, False, 0.0, True)] * 2
              + [(x, y, False, 0.0, False)] * 14)
    return script, (x, y)


def _trigger_xy(key=CKEY, index=1):
    """The centre of row `index` of the menu at `key` (items only - row 0 of
    ROW_MENU_SUB is an item, so the stride is uniform here)."""
    r = M.LAST_RECT.get(key)
    assert r, f"menu {key!r} is not open"
    mx, my, mw, _mh = r
    return mx + mw / 2, my + M.PAD + M.ITEM_H * index + M.ITEM_H / 2


def test_a_dwell_on_the_trigger_opens_the_submenu(DB):
    """Hover, wait, and the panel is there - at the measured place."""
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    assert M.LAST_RECT.get(CKEY), "the right-click did not open the menu"
    tx, ty = _trigger_xy()
    assert not M.LAST_RECT.get(SUBKEY), "the submenu was up before any hover"

    DB.render("dark", W, H, script=script + [(tx, ty)] * DWELL, keep="last")
    sub = M.LAST_RECT.get(SUBKEY)
    assert sub, "a dwell on the trigger did not open the submenu"

    # the measured law, read off the panel ImGui actually placed
    mx, my, mw, _mh = M.LAST_RECT[CKEY]
    row_y = my + M.PAD + M.ITEM_H          # the trigger row's top
    assert sub[0] == pytest.approx(mx + mw - M.PAD, abs=1.0), \
        "the submenu did not land on the trigger's right edge"
    assert sub[1] == pytest.approx(row_y, abs=1.0), \
        "the submenu did not line up with its trigger row"
    assert sub[2] == M.SUB_MIN_W


def test_one_frame_on_the_trigger_is_not_enough(DB):
    """The 100 ms is real: a pointer that crosses the row does not open it.

    Which is the whole reason the dwell is a timer and not a hover - a
    menu whose submenus fly open as the mouse passes over them is the
    behaviour this measurement exists to avoid.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()
    DB.render("dark", W, H, script=script + [(tx, ty)] * 2, keep="last")
    assert not M.LAST_RECT.get(SUBKEY), "two frames of hover opened it"


def test_only_one_row_is_ever_lit(DB):
    """Moving from one SubTrigger to the NEXT closes the first at once.

    Closing is immediate and only opening is on the 100 ms timer, and the
    two were conflated: a move from `Insert` to `Look-back frames` left
    `Insert`'s panel up for the whole dwell, so the menu had two rows lit —
    the old one on `data-open`, the new one on hover — which the real
    component never shows. The panel being up is what lights the row, so
    its rect is the thing to assert on.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()                          # `Insert`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    assert M.LAST_RECT.get(SUBKEY), "the first submenu did not open"
    nx, ny = _trigger_xy(index=3)                   # `Look-back frames`
    # ONE frame on the other row: well inside the 100 ms its own panel waits
    DB.render("dark", W, H, script=opened + [(nx, ny)], keep="last")
    assert not M.LAST_RECT.get(SUBKEY), \
        "the old submenu stayed up while another row was hovered"
    assert not M.LAST_RECT.get(f"{CKEY}>frames"), "the new one opened with no dwell"
    # and the new one does open, once its dwell is up
    DB.render("dark", W, H, script=opened + [(nx, ny)] * DWELL, keep="last")
    assert M.LAST_RECT.get(f"{CKEY}>frames"), "the new submenu never opened"
    assert not M.LAST_RECT.get(SUBKEY)


def _lit(frame, rect, items, sub: bool):
    """Which rows of the panel at `rect` are filled differently from its
    ground — the rows a person sees as highlighted.

    Sampled SIX PIXELS IN, in the row's own left padding where the fill is
    and no glyph reaches, against the padding strip above the first row,
    which is `popover` and nothing else. `test_menu_keys._highlight` reads
    a menu the same way and for the same reasons.
    """
    x, y, _w, _h = rect
    inset = M.PAD + (M.SUB_BORDER if sub else 0.0)
    ground = frame[int(y) + 2, int(x) + int(_w) // 2].astype(int)
    out, iy = [], y + inset
    for i, it in enumerate(items):
        rh = M.row_h(it)
        if it.kind == "item":
            # three pixels into the ROW, inside its own px-1.5 padding and
            # before any glyph: six would land on the first letter
            px = frame[int(iy + M.ITEM_H / 2), int(x + inset) + 3].astype(int)
            if abs(px - ground).max() > 2:
                out.append(i)
        iy += rh
    return out


def test_a_hover_opened_submenu_highlights_nothing(DB):
    """Measured: a hover open highlights NOTHING — only ArrowRight, Enter
    and Space open it on its first row.

    It armed every open, so a panel the pointer had merely dwelled on came
    up with its first row lit while the pointer was still in the parent:
    two rows filled, in two panels, with the pointer on neither of them.
    Read off the pixels, because that is what the owner saw.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()                          # `Insert`
    f = np.asarray(DB.render("dark", W, H, script=script + [(tx, ty)] * DWELL,
                             keep="last")[-1])[:, :, :3]
    sub = M.LAST_RECT.get(SUBKEY)
    assert sub, "the submenu did not open"
    rows = list(DB.ROW_MENU_SUB[1].items)
    assert _lit(f, sub, rows, sub=True) == [], \
        "a hover-opened submenu lit a row with the pointer still in the parent"
    # the parent's own trigger IS lit, which is `data-open:bg-accent`
    assert 1 in _lit(f, M.LAST_RECT[CKEY], DB.ROW_MENU_SUB, sub=False)


def test_the_highlight_follows_the_pointer_past_an_open_submenu(DB):
    """Exactly one row of a panel is ever lit, and it is the one under the
    pointer (or the one whose submenu is open, which is the same row).

    Walking down a menu opens a submenu in passing. The highlight used to
    be FROZEN while one was open, so it stayed on the row that had opened
    it while the pointer ran the next one — two rows lit, in one panel,
    which is what the owner's screenshot showed. A parked mouse still
    cannot take the highlight: the hand-over only happens on movement.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()                          # `Insert`, a SubTrigger
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    assert M.LAST_RECT.get(SUBKEY), "the submenu did not open"
    px, py = _trigger_xy(index=2)                   # `Pin to scene`, no submenu
    f = np.asarray(DB.render("dark", W, H, script=opened + [(px, py)] * DWELL,
                             keep="last")[-1])[:, :, :3]
    lit = _lit(f, M.LAST_RECT[CKEY], DB.ROW_MENU_SUB, sub=False)
    assert lit == [2], f"rows {lit} are lit; only the one under the pointer may be"


def test_moving_to_another_row_closes_it(DB):
    """Measured: the panel is gone inside 100 ms of the pointer reaching
    another row of the parent."""
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    assert M.LAST_RECT.get(SUBKEY), "the submenu did not open"
    ox, oy = _trigger_xy(index=0)           # the row above it
    DB.render("dark", W, H, script=opened + [(ox, oy)] * DWELL, keep="last")
    assert not M.LAST_RECT.get(SUBKEY), "another row left the submenu up"


def test_the_parent_is_still_alive_while_a_submenu_is_open(DB):
    """The ImGui trap this flag exists for. A popup that takes focus takes
    HOVERING with it - `IsWindowContentHoverable` refuses it to every
    window outside the focused popup's begin-stack chain - so a focused
    submenu would make its own parent dead to the mouse. Driven: with the
    submenu up, a click on a row of the PARENT still lands.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    assert M.LAST_RECT.get(SUBKEY), "the submenu did not open"
    px, py = _trigger_xy(index=0)
    DB.render("dark", W, H,
              script=opened + [(px, py)] * 10 + [(px, py, True)] * 2
              + [(px, py, False)] * 8, keep="last")
    assert DB.render.last_state["ctx"].startswith("open"), \
        "a click on the parent's row did not land while a submenu was open"


def test_a_choice_in_the_submenu_lands_and_closes_the_lot(DB):
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    sx, sy, sw, _sh = M.LAST_RECT[SUBKEY]
    # the submenu's first row, inside its border and padding
    ix = sx + sw / 2
    iy = sy + M.SUB_BORDER + M.PAD + M.ITEM_H / 2
    DB.render("dark", W, H,
              script=opened + [(ix, iy)] * 10 + [(ix, iy, True)] * 2
              + [(ix, iy, False)] * 8, keep="last")
    assert DB.render.last_state["ctx"].startswith("insert.gain"), \
        f"the submenu's choice did not land: {DB.render.last_state['ctx']!r}"
    assert not M.LAST_RECT.get(SUBKEY), "the submenu stayed open"
    assert not M.LAST_RECT.get(CKEY), "the parent menu stayed open"


def test_a_second_level_opens_too(DB):
    """Nesting is what the graph's menus actually need - `insert ▸ effects ▸
    <file>` is two deep - so one level is not enough to have built."""
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    sx, sy, sw, _sh = M.LAST_RECT[SUBKEY]
    # `More`, the third row of the submenu
    dx = sx + sw / 2
    dy = sy + M.SUB_BORDER + M.PAD + M.ITEM_H * 2 + M.ITEM_H / 2
    DB.render("dark", W, H, script=opened + [(dx, dy)] * DWELL, keep="last")
    deep = M.LAST_RECT.get(DEEPKEY)
    assert deep, "the second level did not open"
    assert deep[0] == pytest.approx(sx + sw - M.PAD - M.SUB_BORDER, abs=1.5)


def test_a_submenu_too_tall_for_the_window_scrolls_to_its_last_row(DB):
    """The look-back frame menu's shape: 32 rows, 906px, in a window that
    cannot hold them.

    `place_sub` clamps the panel to the viewport, which on its own CUTS the
    rows off the bottom — the last of them could not be clicked in any
    window shorter than the menu. The rows scroll instead, as `popup`'s do,
    and the test is that the LAST row still lands.
    """
    # a window SHORTER than the menu, which is the whole case: 32 rows want
    # 906px and this leaves them 640 to live in
    h = 640
    script, _at = _open(DB, h)
    DB.render("dark", W, h, script=script, keep="last")
    tx, ty = _trigger_xy(index=3)                   # `Look-back frames`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, h, script=opened, keep="last")
    key = f"{CKEY}>frames"
    sub = M.LAST_RECT.get(key)
    assert sub, "the long submenu did not open"
    rows = 32 * M.ITEM_H + 2 * (M.PAD + M.SUB_BORDER)
    assert sub[3] < rows, "the panel was not capped at all"
    assert sub[3] + sub[1] <= h + 0.5, "the panel hangs off the window"

    # wheel over it until the end of the list, then click the last row
    sx, sy, sw, sh = sub
    wx, wy = sx + sw / 2, sy + sh / 2
    wheel = opened + [(wx, wy)] * 4 + [(wx, wy, False, -3.0)] * 60 + [(wx, wy)] * 6
    DB.render("dark", W, h, script=wheel, keep="last")
    last_y = sy + sh - M.PAD - M.SUB_BORDER - M.ITEM_H / 2
    DB.render("dark", W, h,
              script=wheel + [(wx, last_y)] * 8 + [(wx, last_y, True)] * 2
              + [(wx, last_y, False)] * 8, keep="last")
    got = DB.render.last_state["ctx"]
    assert got.startswith("frames.32"), \
        f"the last row of a scrolled submenu did not land: {got!r}"


def test_the_pointer_lands_on_the_row_it_is_over_in_a_scrolled_submenu(DB):
    """Wheel a tall submenu, move the pointer, press Enter: the row under
    the pointer is the row that is taken.

    The rows of a capped panel are drawn at `y + inset - off`, and the
    pointer used to be hit-tested against them UNSCROLLED — so the
    highlight landed on a row nobody was pointing at, Enter took it, and
    `_scroll` dragged the list back to show it. `scrolled` is last frame's
    offset, which is where the rows the pointer is over were painted.
    """
    h = 640
    script, _at = _open(DB, h)
    DB.render("dark", W, h, script=script, keep="last")
    tx, ty = _trigger_xy(index=3)                   # `Look-back frames`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, h, script=opened, keep="last")
    sx, sy, sw, sh = M.LAST_RECT[f"{CKEY}>frames"]

    wx, wy = sx + sw / 2, sy + sh / 2
    wheel = opened + [(wx, wy)] * 4 + [(wx, wy, False, -3.0)] * 60 + [(wx, wy)] * 6
    DB.render("dark", W, h, script=wheel, keep="last")
    # scrolled to the end, so the FIRST row in view is no longer echo.1:
    # the pointer just inside the top of the panel is over a late row
    top_y = sy + M.SUB_BORDER + M.PAD + M.ITEM_H / 2
    moved = wheel + [(wx, top_y)] * 8
    at = len(moved) + 2
    DB.render("dark", W, h, script=moved + [(wx, top_y)] * DWELL,
              keys=[(at, imgui.Key.enter)], keep="last")
    got = DB.render.last_state["ctx"]
    # which row that is depends on how far the wheel went; what matters is
    # that it is NOT the first row of the list, which is what the
    # unscrolled hit test would have taken
    assert got.startswith("frames."), f"Enter took nothing: {got!r}"
    assert not got.startswith("frames.1 "), \
        f"Enter took the list's first row, not the one under the pointer: {got!r}"


def test_a_dismissed_submenu_forgets_its_own_descendants(DB):
    """Close a submenu by moving to another row, and its GRANDCHILD has to
    go with it.

    `_dismiss` begins the child only to close it, so `sub_popup`'s closed
    branch — which is what normally forgets a chain — never runs for it. Its
    own `open` and `shown` still named the grandchild, and hovering the
    child again brought that grandchild straight back, without its trigger
    ever being hovered.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()                          # `Insert`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    sx, sy, sw, _sh = M.LAST_RECT[SUBKEY]
    dx = sx + sw / 2
    dy = sy + M.SUB_BORDER + M.PAD + M.ITEM_H * 2 + M.ITEM_H / 2    # `More`
    deep = opened + [(dx, dy)] * DWELL
    DB.render("dark", W, H, script=deep, keep="last")
    assert M.LAST_RECT.get(DEEPKEY), "the second level did not open"

    # away to another row of the ROOT, which closes `Insert` and its child
    ox, oy = _trigger_xy(index=0)
    away = deep + [(ox, oy)] * DWELL
    DB.render("dark", W, H, script=away, keep="last")
    assert not M.LAST_RECT.get(SUBKEY) and not M.LAST_RECT.get(DEEPKEY)

    # back onto `Insert`: it opens, and its grandchild does NOT
    back = away + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=back, keep="last")
    assert M.LAST_RECT.get(SUBKEY), "the submenu did not reopen"
    assert not M.LAST_RECT.get(DEEPKEY), \
        "the grandchild came back without its trigger being hovered"


def test_both_levels_of_a_chain_land_on_the_same_side(DB):
    """The owner's report: "the small menu opens to the right of the
    initial panel, and then a larger menu opens to the left. It feels
    scary."

    Opened near the window's right edge, level one (128 wide) still fits on
    the right and level two (wide) does not — so each deciding for itself
    put them on opposite sides, one over the top of the other. The chain
    decides once, for the widest panel the kit can draw, and both go the
    same way.
    """
    script, _at = _open(DB, at_x=760.0)             # near the right edge
    DB.render("dark", W, H, script=script, keep="last")
    root = M.LAST_RECT.get(CKEY)
    assert root, "the menu did not open"
    # THE TRAP, stated rather than hoped for: a narrow panel still fits to
    # the right of level one's trigger here, so a panel deciding for itself
    # goes right — and the wide level under it cannot, so it goes left.
    trig_right = root[0] + root[2] - M.PAD
    assert trig_right + M.SUB_MIN_W <= W
    assert trig_right + M.MAX_W > W
    tx, ty = _trigger_xy()                          # `Insert`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    one = M.LAST_RECT.get(SUBKEY)
    assert one, "level one did not open"

    sx, sy, sw, _sh = one
    dx = sx + sw / 2
    dy = sy + M.SUB_BORDER + M.PAD + M.ITEM_H * 2 + M.ITEM_H / 2    # `More`
    DB.render("dark", W, H, script=opened + [(dx, dy)] * DWELL, keep="last")
    two = M.LAST_RECT.get(DEEPKEY)
    assert two, "level two did not open"
    assert two[2] > M.SUB_MIN_W, "level two was meant to be the wide one"
    # same side: both to the left of their trigger, or both to the right
    one_left = one[0] < root[0]
    two_left = two[0] < sx
    assert one_left == two_left, \
        f"level one went {'left' if one_left else 'right'} and level two " \
        f"went {'left' if two_left else 'right'}"


def test_a_diagonal_into_an_open_submenu_does_not_close_it(DB):
    """Amazon's golden triangle, driven.

    The path from a trigger to the far corner of its own panel crosses the
    rows under it. Each of those took the pointer and closed the panel that
    was being aimed at, so the only way in was an L: straight across, then
    down. With the wedge, the diagonal works.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()                          # `Insert`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    sx, sy, sw, sh = M.LAST_RECT[SUBKEY]
    assert sx > tx, "this test wants the panel on the right"

    # a straight diagonal from the trigger to the panel's bottom row,
    # crossing the parent's own rows on the way
    end = (sx + sw / 2, sy + sh - M.ITEM_H)
    steps = 10
    path = [(tx + (end[0] - tx) * k / steps, ty + (end[1] - ty) * k / steps)
            for k in range(1, steps + 1)]
    crossed = [p for p in path if p[0] < sx]
    assert len(crossed) >= 3, "the diagonal must cross the parent's rows"
    f = np.asarray(DB.render("dark", W, H, script=opened + path + [end] * 6,
                             keep="last")[-1])[:, :, :3]
    assert M.LAST_RECT.get(SUBKEY), \
        "the rows under the diagonal closed the panel it was heading for"
    # and the row that OWNS the open panel keeps the highlight: the parent
    # reads the pointer as being on its own rows the whole way (the panels
    # overlap, and `is_mouse_hovering_rect` knows nothing about what is on
    # top), so without the hold it lit whichever row the pointer was over
    lit = _lit(f, M.LAST_RECT[CKEY], DB.ROW_MENU_SUB, sub=False)
    assert lit == [1], f"rows {lit} are lit; only `Insert`, whose panel is open, may be"


def test_a_pointer_that_parks_in_the_wedge_gives_up(DB):
    """The wedge cannot hold a menu open for ever: a pointer that stops
    inside it without arriving releases after `AIM_HOLD_S`, so a row it is
    resting on gets its turn."""
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    tx, ty = _trigger_xy()
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, H, script=opened, keep="last")
    sx, sy, _sw, sh = M.LAST_RECT[SUBKEY]
    # one step into the wedge, then parked there, on another parent row
    park = ((tx + sx) / 2, sy + sh * 0.7)
    DB.render("dark", W, H, script=opened + [park] * 4, keep="last")
    DB.render("dark", W, H,
              script=opened + [park] * (4 + int(M.AIM_HOLD_S * 60) + 40),
              keep="last")
    assert not M.LAST_RECT.get(SUBKEY), "a parked pointer held the menu open"


def test_arrow_right_opens_it_and_arrow_left_closes_it(DB):
    """Measured on the real component: ArrowRight on the trigger opens the
    panel and highlights its FIRST row; ArrowLeft closes it and leaves the
    highlight on the trigger."""
    script, _at = _open(DB)
    park = (10, 10, False)              # off the panel: the keys must decide
    base = script + [park] * 6
    at = len(base) + 2
    keys = [(at, imgui.Key.down_arrow), (at + 4, imgui.Key.down_arrow),
            (at + 8, imgui.Key.right_arrow)]
    DB.render("dark", W, H, script=base + [park] * DWELL, keys=keys, keep="last")
    assert M.LAST_RECT.get(SUBKEY), "ArrowRight did not open the submenu"

    DB.render("dark", W, H, script=base + [park] * DWELL,
              keys=keys + [(at + 14, imgui.Key.left_arrow)], keep="last")
    assert not M.LAST_RECT.get(SUBKEY), "ArrowLeft did not close the submenu"
    assert M.LAST_RECT.get(CKEY), "ArrowLeft closed the parent as well"


def test_scrolling_moves_the_pointers_row_under_it(DB):
    """A wheel moves the rows under a pointer that has not moved at all.

    The claim on a row is taken by MOTION, which is right for a mouse and
    blind to a scroll: wheel a capped panel and a different trigger is
    under the cursor with no `mouse_delta` at all, so the panel of the row
    that used to be there stayed open over the row that is.
    """
    h = 560                                         # short: `Deep list` caps
    script, _at = _open(DB, h)
    DB.render("dark", W, h, script=script, keep="last")
    tx, ty = _trigger_xy(index=4)                   # `Deep list`
    opened = script + [(tx, ty)] * DWELL
    DB.render("dark", W, h, script=opened, keep="last")
    key = f"{CKEY}>deep"
    sub = M.LAST_RECT.get(key)
    assert sub, "the long submenu did not open"
    sx, sy, sw, sh = sub
    assert sh < 28 * M.ITEM_H, "this test wants a capped panel"

    # park on `row 4`, the first trigger in it, and let its panel open
    row4 = sy + M.SUB_BORDER + M.PAD + M.ITEM_H * 3 + M.ITEM_H / 2
    at_row4 = opened + [(sx + sw / 2, row4)] * DWELL
    DB.render("dark", W, h, script=at_row4, keep="last")
    first = [k for k in M.LAST_RECT if k.startswith(key + ">")]
    assert first == [f"{key}>deep.4"], f"expected row 4's panel, got {first}"

    # wheel WITHOUT moving the pointer, exactly four rows, so the NEXT
    # trigger (`row 8`) takes row 4's place under the cursor
    wheeled = at_row4 + [(sx + sw / 2, row4, False, -2.0)] * 2 \
        + [(sx + sw / 2, row4)] * DWELL
    DB.render("dark", W, h, script=wheeled, keep="last")
    now = [k for k in M.LAST_RECT if k.startswith(key + ">")]
    # the positive, not merely "something changed": the row now under the
    # cursor is the one whose panel is open. Unfixed, the claim stays on a
    # row that has scrolled away and NOTHING opens.
    assert now == [f"{key}>deep.8"], \
        f"after the scroll the open panel is {now}, not row 8's"


def test_a_parked_mouse_cannot_take_back_a_keyboard_opened_submenu(DB):
    """ArrowRight with the mouse resting on ANOTHER row.

    `over` is pure geometry and answers the same every frame a mouse rests,
    so hanging the hover rules on it let a parked mouse act: the panel the
    keyboard had just opened was closed on the very next frame by a row
    nobody was touching. A row is the pointer's only by MOTION, exactly as
    the highlight is.
    """
    script, _at = _open(DB)
    DB.render("dark", W, H, script=script, keep="last")
    # park the mouse on `Pin to scene`, which has no submenu of its own —
    # so nothing is open, the keys still belong to this panel, and the
    # row the mouse rests on is not the one they will open
    px, py = _trigger_xy(index=2)
    parked = script + [(px, py)] * 4
    at = len(parked) + 2
    # one ArrowDown moves the highlight from it to `Look-back frames`, the
    # next row and a SubTrigger; ArrowRight opens that. The mouse never
    # moves again.
    keys = [(at, imgui.Key.down_arrow), (at + 6, imgui.Key.right_arrow)]
    DB.render("dark", W, H, script=parked + [(px, py)] * DWELL, keys=keys,
              keep="last")
    assert M.LAST_RECT.get(f"{CKEY}>frames"), \
        "the parked mouse closed the submenu the keyboard opened"


def test_escape_in_a_submenu_closes_the_whole_menu(DB):
    """Measured: Escape inside a SubContent took the parent panel with it.
    ImGui's own Escape closes only the topmost popup, so this is a rule the
    kit has to add rather than inherit."""
    script, _at = _open(DB)
    park = (10, 10, False)
    base = script + [park] * 6
    at = len(base) + 2
    keys = [(at, imgui.Key.down_arrow), (at + 4, imgui.Key.down_arrow),
            (at + 8, imgui.Key.right_arrow), (at + 14, imgui.Key.escape)]
    DB.render("dark", W, H, script=base + [park] * DWELL, keys=keys, keep="last")
    assert not M.LAST_RECT.get(SUBKEY), "Escape left the submenu open"
    assert not M.LAST_RECT.get(CKEY), "Escape left the parent menu open"
