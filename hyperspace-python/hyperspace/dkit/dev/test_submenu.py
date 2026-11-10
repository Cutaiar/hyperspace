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


def _page_view(DB):
    """The page's scroll viewport, as `test_interaction.page_view` has it:
    everything below the header and right of the sidebar."""
    return (DB.SIDEBAR_W, DB.HEADER_H, W - DB.SIDEBAR_W, H - DB.HEADER_H)


def _row0(DB):
    """A script prefix that wheels the table into view, and row 0's rect."""
    px, py, pw, ph = _page_view(DB)
    mx, my = px + pw / 2, py + ph / 2
    prefix = [(mx, my)] * 4 + [(mx, my, False, -3.0)] * 120 + [(mx, my)] * 4
    DB.render("dark", W, H, script=prefix, keep="last")
    sy = DB.render.last_state["page_scroll"]
    return prefix, DB.lay_out(W, H, body_dy=-sy).table_rows[0]


def _open(DB):
    """The script that right-clicks row 0 open, and row 0's rect."""
    prefix, (rx, ry, _rw, rh) = _row0(DB)
    x, y = rx + 200, ry + rh / 2
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
