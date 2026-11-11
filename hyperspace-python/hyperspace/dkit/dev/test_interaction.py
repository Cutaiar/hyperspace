"""End-to-end interaction tests, driven by synthetic input and read back
from pixels.

These exist because of a bug they would have caught and my earlier manual
check did not: the row kebab flickered and could never be clicked. The check
I ran hovered for six frames, which is *shorter than the 150ms transition*,
so the oscillation had not started yet and a screenshot looked fine.

So every test here **dwells well past the easing period** and asserts
stability over time, not just the state of one frame. A UI bug that needs
time to appear needs a test that spends time.

    uv run python -m pytest hyperspace/dkit/dev/test_interaction.py -q

Needs GL; skips cleanly without a display, the way the project's other
GL tests do (tests/gl_probe.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))

W, H = 1440, 1100
DWELL = 40          # frames; the transition is 9 at 60fps


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


def scrolled_to_bottom(DB):
    """A script prefix that wheels the page to the end, and the Rects as
    they then are.

    The table lives below the fold at this window size, so a test that
    wants a row has to scroll to it first - which is what a person does
    too. Returns (prefix, rects) where the rects are laid out at that
    scroll, so a caller reads screen positions straight off them.
    """
    px, py, pw, ph = page_view(DB)
    mx, my = px + pw / 2, py + ph / 2
    prefix = [(mx, my)] * 4 + [(mx, my, False, -3.0)] * 120 + [(mx, my)] * 4
    DB.render("dark", W, H, script=prefix)
    sy = DB.render.last_state["page_scroll"]
    return prefix, DB.lay_out(W, H, body_dy=-sy)


def kebab_xy(DB, row=1):
    """The kebab of a table row, and the script that scrolls it into view."""
    prefix, r = scrolled_to_bottom(DB)
    rx, ry, rw, rh = r.table_rows[row]
    return prefix, rx + rw - 30 + 13, ry + rh / 2


def menu_rect(key):
    """Where ImGui actually put the menu, from menu.LAST_RECT.

    Reading it from pixels was tried and is unreliable: a hovered table row
    composites to within a level of the popover fill, so the bounding box
    swallowed the row.
    """
    from hyperspace.dkit import menu as M
    return M.LAST_RECT.get(key)


def menu_item_xy(key, index):
    from hyperspace.dkit import menu as M
    r = menu_rect(key)
    assert r, f"menu {key!r} is not open"
    mx, my, mw, _ = r
    return mx + mw / 2, my + M.PAD + M.ITEM_H * index + M.ITEM_H / 2


def ink(frame, x, y, r=9):
    """How much is drawn around (x, y) — mean distance from the local ground."""
    box = frame[int(y) - r:int(y) + r, int(x) - r:int(x) + r].astype(float)
    return float(np.abs(box - np.median(box)).mean())


def test_kebab_stays_put_while_hovered(DB):
    """The regression. Hovering the kebab must not make it come and go.

    The old code gated the kebab's *submission* on the row's hover, so the
    kebab took the hover, the row lost it, the kebab was withdrawn, the row
    regained it — forever, at the easing's period.
    """
    pre, x, y = kebab_xy(DB)
    frames = DB.render("dark", W, H, script=pre + [(x, y)] * DWELL)
    # from after the scroll prefix, or this averages in frames where the
    # table had not been scrolled into view yet
    settled = [ink(f, x, y) for f in frames[len(pre) + 12:]]
    assert min(settled) > 1.0, "the kebab vanished while being hovered"
    spread = max(settled) - min(settled)
    assert spread < 1.0, f"the kebab flickered: ink varied by {spread:.2f}"


def test_kebab_opens_the_menu_after_a_long_hover(DB):
    """Press after dwelling — the case that was broken for a real person,
    who takes far longer than six frames to move and click."""
    pre, x, y = kebab_xy(DB)
    script = pre + [(x, y)] * DWELL + [(x, y, True)] * 2 + [(x, y, False)] * 14
    frames = DB.render("dark", W, H, script=script)
    # Where the menu went comes from menu.LAST_RECT, not from a guessed
    # offset below the kebab: place_popover FLIPS a panel above its trigger
    # when there is no room below, so a fixed probe point stops finding it
    # the moment the table's last rows move up the window.
    r = menu_rect("rowmenu.1")
    assert r, f"no menu opened after a {DWELL}-frame hover and a press"
    mx, my, mw, mh = r
    cx, cy = mx + mw / 2, my + mh / 2
    before = ink(frames[DWELL - 1], cx, cy)
    after = ink(frames[-1], cx, cy)
    assert after > before + 2.0, (
        f"the menu rect is empty after a {DWELL}-frame hover and a press "
        f"(ink {before:.2f} -> {after:.2f})")


def test_menu_item_can_be_chosen(DB):
    """Open the menu, move onto its first item, click, see the choice land."""
    pre, x, y = kebab_xy(DB)
    open_script = pre + [(x, y)] * 20 + [(x, y, True)] * 2 + [(x, y, False)] * 12
    DB.render("dark", W, H, script=open_script)
    ix, iy = menu_item_xy("rowmenu.1", 0)
    script = (open_script + [(ix, iy)] * 12
              + [(ix, iy, True)] * 2 + [(ix, iy, False)] * 4)
    DB.render("dark", W, H, script=script)
    said = DB.render.last_state.get("said")
    assert said and said.startswith("open"), f"menu choice did not land: {said!r}"


def test_destructive_item_is_reachable(DB):
    """The last row, past a separator and a heading — the offsets a guessed
    coordinate gets wrong."""
    pre, x, y = kebab_xy(DB)
    open_script = pre + [(x, y)] * 20 + [(x, y, True)] * 2 + [(x, y, False)] * 12
    from hyperspace.dkit import menu as M
    DB.render("dark", W, H, script=open_script)
    r = menu_rect("rowmenu.1")
    assert r, "menu did not open"
    mx, my, mw, mh = r
    ix, iy = mx + mw / 2, my + mh - M.PAD - M.ITEM_H / 2     # last row
    script = (open_script + [(ix, iy)] * 12
              + [(ix, iy, True)] * 2 + [(ix, iy, False)] * 4)
    DB.render("dark", W, H, script=script)
    said = DB.render.last_state.get("said")
    assert said and said.startswith("remove"), f"got {said!r}"


def test_escape_dismisses_the_menu(DB):
    """ImGui owns dismissal; this checks the kit has not broken it."""
    from imgui_bundle import imgui
    _pre, x, y = kebab_xy(DB)
    script = [(x, y)] * 20 + [(x, y, True)] * 2 + [(x, y, False)] * 12
    DB.render("dark", W, H, script=script,
              keys=[(len(script) - 6, imgui.Key.escape)])
    assert menu_rect("rowmenu.1") is None, "menu survived Escape"


def test_tabs_filter_the_table(DB):
    """Each tab hit-tests to its own index and changes what the table shows."""
    y = DB.lay_out(W, H).table_tabs[1] + 16
    for x, want in ((285, 0), (360, 1), (445, 2), (509, 3), (567, 4)):
        script = [(x, y)] * 12 + [(x, y, True)] * 2 + [(x, y, False)] * 4
        DB.render("dark", W, H, script=script)
        got = DB.render.last_state["tab"]
        assert got == want, f"click at x={x} chose tab {got}, wanted {want}"


def test_sidebar_selection_follows_clicks(DB):
    r = DB.lay_out(W, H)
    for i in (2, 4, 0):
        nx, ny, nw, nh = r.nav[i]
        p = (nx + nw / 2, ny + nh / 2)
        script = [p] * 12 + [(*p, True)] * 2 + [(*p, False)] * 4
        DB.render("dark", W, H, script=script)
        assert DB.render.last_state["nav"] == i


def test_every_widget_id_is_unique(DB):
    """Ui.hit refuses duplicates; a frame that draws is proof there are none."""
    DB.render("dark", W, H, script=[(700, 500)] * 4)


# --------------------------------------------------------------------------
# Tier 1 controls
# --------------------------------------------------------------------------
#
# Same rule as above: every one of these dwells well past the 150ms easing
# (DWELL = 40 frames against a 9-frame transition) and asserts stability over
# time rather than the state of one frame. The kebab bug survived a six-frame
# check because the oscillation had not started yet.


def ctl_rect(DB, i):
    return DB.lay_out(W, H).ctl_rows[i]


def slider_track(DB):
    """The Cutoff slider's track, as dashboard.paint lays it out.

    The label column comes from the module rather than being copied here:
    a number duplicated into a test goes stale the moment the layout moves,
    and this one did exactly that when the spacing was put on the scale.
    """
    rx, ry, rw, rh = ctl_rect(DB, 0)
    sx = rx + DB.CTL_LABEL_W
    return sx, ry, rw - DB.CTL_LABEL_W - 46.0, rh


def test_slider_drag_moves_the_value(DB):
    """Press at 20% of the track and drag to 80%: the value must follow.

    A slider jumps to where it is pressed, so this also covers the press.
    """
    sx, sy, sw, sh = slider_track(DB)
    y = sy + sh / 2
    a, b = sx + sw * 0.2, sx + sw * 0.8
    script = ([(a, y)] * 6 + [(a, y, True)] * 4
              + [(a + (b - a) * i / 10.0, y, True) for i in range(11)] * 2
              + [(b, y, False)] * DWELL)
    DB.render("dark", W, H, script=script)
    got = DB.render.last_state["cutoff"]
    lo, hi = 20.0, 20000.0
    want = lo + (hi - lo) * 0.8
    assert abs(got - want) < (hi - lo) * 0.08, (
        f"drag to 80% left the value at {got:.0f}, wanted about {want:.0f}")


def test_slider_is_stable_while_hovered(DB):
    """The kebab's failure mode, on a slider: the thumb's ring eases in on
    hover, and must then sit still rather than breathe."""
    sx, sy, sw, sh = slider_track(DB)
    x, y = sx + sw * 0.5, sy + sh / 2
    frames = DB.render("dark", W, H, script=[(x, y)] * DWELL)
    settled = [ink(f, x, y) for f in frames[14:]]       # past the fade-in
    spread = max(settled) - min(settled)
    assert spread < 1.0, f"the slider flickered while hovered: {spread:.2f}"


def test_slider_clamps_when_dragged_past_either_end(DB):
    """Drag hard past both ends and the value stops at the domain's edge.

    Checked on the VALUE rather than on pixels: the geometric half of this -
    that the thumb is inset by its own width and so never overhangs the
    track - is swept over every width and fraction in
    test_components.test_slider_thumb_never_overhangs_the_track, where it can
    be asserted exactly instead of inferred from ink.
    """
    sx, sy, sw, sh = slider_track(DB)
    y = sy + sh / 2
    lo, hi = 20.0, 20000.0
    for target, want, name in ((sx - 400, lo, "left"),
                               (sx + sw + 400, hi, "right")):
        script = ([(sx + sw / 2, y)] * 4 + [(sx + sw / 2, y, True)] * 2
                  + [(target, y, True)] * 10 + [(target, y, False)] * DWELL)
        DB.render("dark", W, H, script=script)
        got = DB.render.last_state["cutoff"]
        assert abs(got - want) < 1e-6, (
            f"dragging {name} left the value at {got} rather than {want}")


def test_switch_toggles_and_settles(DB):
    """Click it, then dwell: the thumb slides on the 150ms curve and must
    come to rest, not oscillate."""
    rx, ry, _, rh = ctl_rect(DB, 1)
    x, y = rx + DB.CTL_LABEL_W + 16.0, ry + rh / 2
    before = DB.render("dark", W, H, script=[(x, y)] * 4)
    script = ([(x, y)] * 6 + [(x, y, True)] * 2 + [(x, y, False)] * DWELL)
    frames = DB.render("dark", W, H, script=script)
    assert DB.render.last_state["bypass"] is True, "the switch did not toggle"
    settled = [ink(f, x, y) for f in frames[-12:]]      # long past the 9-frame slide
    spread = max(settled) - min(settled)
    assert spread < 0.8, f"the switch never settled: ink varied by {spread:.2f}"
    assert len(before) == 4


def test_switch_does_not_toggle_twice_on_one_click(DB):
    """A press held down for many frames is still one click."""
    rx, ry, _, rh = ctl_rect(DB, 1)
    x, y = rx + DB.CTL_LABEL_W + 16.0, ry + rh / 2
    script = [(x, y)] * 6 + [(x, y, True)] * DWELL + [(x, y, False)] * 6
    DB.render("dark", W, H, script=script)
    assert DB.render.last_state["bypass"] is True, (
        "holding the press toggled the switch more than once")


def test_select_opens_and_stays_open(DB):
    """The kebab bug's shape again: open the panel, then dwell on it. It has
    to still be there, and steady, forty frames later."""
    rx, ry, _, rh = ctl_rect(DB, 2)
    x, y = rx + DB.CTL_LABEL_W + 40.0, ry + rh / 2
    script = [(x, y)] * 10 + [(x, y, True)] * 2 + [(x, y, False)] * DWELL
    frames = DB.render("dark", W, H, script=script)
    from hyperspace.dkit import menu as M
    assert M.LAST_RECT.get("##sel.ctl.plane"), "the select panel did not open"
    below = [ink(f, x, y + rh + 24) for f in frames[-16:]]
    assert min(below) > 1.0, "the select panel vanished while open"
    assert max(below) - min(below) < 1.0, "the select panel flickered"


def test_select_choice_lands(DB):
    """Open it, move onto an item, click: the state must change."""
    rx, ry, _, rh = ctl_rect(DB, 2)
    x, y = rx + DB.CTL_LABEL_W + 40.0, ry + rh / 2
    open_script = [(x, y)] * 10 + [(x, y, True)] * 2 + [(x, y, False)] * 14
    DB.render("dark", W, H, script=open_script)
    from hyperspace.dkit import menu as M
    r = M.LAST_RECT.get("##sel.ctl.plane")
    assert r, "the select panel did not open"
    mx, my, mw, _ = r
    ix, iy = mx + mw / 2, my + M.PAD + M.ITEM_H / 2        # the first item, XY
    script = (open_script + [(ix, iy)] * 12 + [(ix, iy, True)] * 2
              + [(ix, iy, False)] * 6)
    DB.render("dark", W, H, script=script)
    assert DB.render.last_state["plane"] == "XY", (
        f"choice did not land: {DB.render.last_state['plane']!r}")


def test_tooltip_waits_for_the_delay_then_holds(DB):
    """A tooltip opens on a delay and must then STAY open, every frame.

    Counted, not sampled: a tooltip floats over whatever is above it - here
    the card's own description - so ink at a guessed point cannot tell the
    two apart. dashboard.paint tallies the frames it actually drew on, which
    also makes the flicker check exact rather than inferred. If it blinks at
    the easing's period the frames simply do not add up.

    Both halves matter. Appearing instantly is wrong, and a tooltip that
    took the hover from the control it describes would blink - the trap
    `row_action` exists to close, which a tooltip would walk straight back
    into if it had a hit target of its own.
    """
    sx, sy, sw, sh = slider_track(DB)
    x, y = sx + sw * 0.5, sy + sh / 2
    # TOOLTIP_DELAY is 0.4s and render steps a fixed 1/60, so ~24 frames
    N = 70
    DB.render("dark", W, H, script=[(x, y)] * N)
    shown = DB.render.last_state["tip_frames"]
    from hyperspace.dkit import interact as I
    delay_frames = round(I.TOOLTIP_DELAY * 60)
    expected = N - delay_frames
    assert shown > 0, "the tooltip never appeared"
    assert shown <= expected + 2, (
        f"the tooltip appeared before its delay: {shown} frames of a "
        f"possible {expected}")
    assert shown >= expected - 2, (
        f"the tooltip blinked: drawn on {shown} frames, not {expected}")


def test_tooltip_goes_away_when_the_pointer_leaves(DB):
    sx, sy, sw, sh = slider_track(DB)
    x, y = sx + sw * 0.5, sy + sh / 2
    away = (sx + sw * 0.5, sy - 220)
    DB.render("dark", W, H, script=[(x, y)] * 50)
    assert DB.render.last_state["tip_now"], "the tooltip never opened"
    DB.render("dark", W, H, script=[(x, y)] * 50 + [away] * 20)
    assert not DB.render.last_state["tip_now"], (
        "the tooltip outlived the hover")


def test_input_takes_typing(DB):
    """Click into the field and type: the sandwich must pass the keyboard
    through to the real input_text underneath."""
    rx, ry, _, rh = ctl_rect(DB, 3)
    x, y = rx + DB.CTL_LABEL_W + 40.0, ry + rh / 2
    script = [(x, y)] * 6 + [(x, y, True)] * 2 + [(x, y, False)] * 30
    # characters, not keys: input_text is fed by character events
    DB.render("dark", W, H, script=script, keys=[(12, "Z"), (16, "9")])
    got = DB.render.last_state["name"]
    assert got != "600-cell", f"typing did not reach the input ({got!r})"
    assert "Z" in got and "9" in got, f"typed characters missing from {got!r}"


def test_input_text_is_visible_in_both_themes(DB):
    """The stock widget draws the value with imgui's OWN Col_.text, which is
    white by default. On dark that happens to look right and on light the
    value is simply invisible - so the theme has to be pushed explicitly.

    Caught by looking at the demo, not by the diff: the gallery's Input cells
    carry no text, because the whole point of the spec is that chrome is
    measured without glyphs.
    """
    rx, ry, _, rh = ctl_rect(DB, 3)
    x, y = rx + DB.CTL_LABEL_W + 40.0, ry + rh / 2
    for theme in ("light", "dark"):
        frames = DB.render(theme, W, H, script=[(0.0, 0.0)] * 4)
        assert ink(frames[-1], x, y) > 2.0, (
            f"the input's value is invisible on the {theme} theme")


# --------------------------------------------------------------------------
# ScrollArea
# --------------------------------------------------------------------------

def page_view(DB):
    """The page's scroll viewport: everything below the header, right of
    the sidebar. The whole body scrolls now, not the table on its own - at
    the window heights people use, the content above left the table a
    viewport one row deep."""
    return (DB.SIDEBAR_W, DB.HEADER_H,
            W - DB.SIDEBAR_W, H - DB.HEADER_H)


def table_centre(DB):
    vx, vy, vw, vh = page_view(DB)
    return vx + vw / 2, vy + vh / 2


def test_the_wheel_scrolls_the_page(DB):
    x, y = table_centre(DB)
    DB.render("dark", W, H, script=[(x, y)] * 6)
    assert DB.render.last_state["page_scroll"] == 0.0
    DB.render("dark", W, H,
              script=[(x, y)] * 6 + [(x, y, False, -3.0)] * 10 + [(x, y)] * 20)
    assert DB.render.last_state["page_scroll"] > 100.0, "the wheel did nothing"


def test_the_scroll_range_is_the_content_less_the_viewport(DB):
    """101 rows of 34 in a 196px viewport is 3238 of travel, and that number
    must not drift as the thing is scrolled.

    It did: the content extent was stated with a SCREEN cursor position
    inside a scrolled child, so it started lower every frame and the range
    went 3238 -> 5638 -> 51238 while the row count never changed.
    """
    x, y = table_centre(DB)
    _bx, _by, _bw, bh = page_view(DB)
    want = DB.lay_out(W, H).body_h - bh
    seen = []
    for n in (0, 10, 200):
        DB.render("dark", W, H,
                  script=[(x, y)] * 4 + [(x, y, False, -3.0)] * n + [(x, y)] * 8)
        seen.append(DB.render.last_state["page_max"])
    assert all(abs(m - want) < 0.5 for m in seen), (
        f"the scroll range drifted: {seen}, wanted {want}")


def test_scrolling_clamps_at_both_ends(DB):
    x, y = table_centre(DB)
    DB.render("dark", W, H,
              script=[(x, y)] * 4 + [(x, y, False, -3.0)] * 200 + [(x, y)] * 8)
    st = DB.render.last_state
    assert st["page_scroll"] == pytest.approx(st["page_max"], abs=0.5)
    DB.render("dark", W, H,
              script=[(x, y)] * 4 + [(x, y, False, -3.0)] * 50
              + [(x, y, False, 3.0)] * 200 + [(x, y)] * 8)
    assert DB.render.last_state["page_scroll"] == 0.0


def test_scrolled_content_stays_inside_the_viewport(DB):
    """The bug this is here for: content drawn into the PARENT's draw list
    is clipped by nothing, so a scrolled body paints straight over the fixed
    header above it. It has to go into the child's list.
    """
    DBr = DB.lay_out(W, H)
    vx, vy, vw, vh = page_view(DB)
    x, y = vx + vw / 2, vy + vh / 2
    frames = DB.render("dark", W, H,
                       script=[(x, y)] * 4 + [(x, y, False, -3.0)] * 8
                       + [(x, y)] * 20)
    assert DB.render.last_state["page_scroll"] > 0, "it did not scroll"
    still = DB.render("dark", W, H, script=[(x, y)] * 4)[-1]
    # The header sits flush on top of the viewport, so there is no gap to
    # inspect - but it must be IDENTICAL scrolled and not. A row painted
    # into the parent's list instead of the child's lands right on it.
    hx, hy, hw, hh = DBr.header
    band = (slice(int(hy), int(hy + hh)), slice(int(hx), int(hx + hw)))
    assert np.array_equal(frames[-1][band], still[band]), (
        "scrolled body leaked over the fixed header")


def test_the_scrollbar_shows_on_hover_and_not_otherwise(DB):
    """shadcn's default is `type="hover"`: no scrollbar until the pointer is
    over the region. Dwells either side of the easing period."""
    DBr = DB.lay_out(W, H)
    vx, vy, vw, vh = page_view(DB)
    from hyperspace.dkit import tokens as T
    col = int(vx + vw - T.SCROLL["bar_w"] + T.SCROLL["thumb_inset"] + 3)
    inside = (vx + vw / 2, vy + vh / 2)
    away = (40, DBr.header[1] + 20)          # over the fixed sidebar

    off = DB.render("dark", W, H, script=[away] * DWELL)[-1]
    on = DB.render("dark", W, H,
                   script=[inside] * 6 + [(inside[0], inside[1], False, -3.0)] * 6
                   + [inside] * DWELL)[-1]
    band = slice(int(vy) + 4, int(vy + vh) - 4)
    assert on[band, col].max() > off[band, col].max() + 6, (
        "the scrollbar did not appear while the region was hovered")


def test_the_thumb_lands_where_the_geometry_says(DB):
    """Pixels against box.scroll_thumb, so the drawn thumb and the measured
    law cannot drift apart."""
    from hyperspace.dkit import box as B
    from hyperspace.dkit import tokens as T
    DB.lay_out(W, H)
    vx, vy, vw, vh = page_view(DB)
    x, y = vx + vw / 2, vy + vh / 2
    frames = DB.render("dark", W, H,
                       script=[(x, y)] * 6 + [(x, y, False, -3.0)] * 8
                       + [(x, y)] * DWELL)
    st = DB.render.last_state
    s = T.SCROLL
    t = B.scroll_thumb(vx + vw - s["bar_w"], vy, s["bar_w"], vh, vh,
                       vh + st["page_max"], st["page_scroll"],
                       inset=s["track_inset"], thumb_w=s["thumb_w"],
                       thumb_inset=s["thumb_inset"], thumb_min=s["thumb_min"])
    assert t is not None
    # Differenced against a column just LEFT of the thumb, inside the same
    # rows. Two earlier attempts measured the wrong thing: a raw column
    # crosses every 34px row separator (and read a thumb 42px tall), and
    # differencing against an unhovered frame removes the hovered ROW's tint
    # too, which starts exactly where the thumb does not.
    f = frames[-1]
    col = int(t.x + t.w / 2)
    ref = int(t.x) - 4
    a = f[:, col, 0].astype(int)
    b = f[:, ref, 0].astype(int)
    lit = [yy for yy in range(int(vy) + 2, int(vy + vh) - 2)
           if a[yy] - b[yy] > 4]
    assert lit, "no thumb was drawn"
    assert abs(min(lit) - t.y) <= 2.0, f"thumb top {min(lit)} vs {t.y:.1f}"
    assert abs(max(lit) + 1 - (t.y + t.h)) <= 2.0, (
        f"thumb bottom {max(lit) + 1} vs {t.y + t.h:.1f}")


# --------------------------------------------------------------------------
# The components the agents built, driven in the demo
# --------------------------------------------------------------------------
# They had unit tests and gallery chrome, but nothing exercised them with a
# pointer until they were composed into the dashboard. That gap is the whole
# reason the demo is the dashboard: three of the bugs in this file's history
# were invisible to the diff by construction.


def test_right_click_opens_the_context_menu(DB):
    """The gesture a node editor wants. A left click must NOT open it."""
    from hyperspace.dkit import menu as M
    pre, r = scrolled_to_bottom(DB)
    rx, ry, _rw, rh = r.table_rows[1]
    x, y = rx + 200, ry + rh / 2
    DB.render("dark", W, H,
              script=pre + [(x, y)] * 8 + [(x, y, True)] * 2
              + [(x, y, False)] * 14)
    assert not M.LAST_RECT.get("##ctx.ctx.1"), "a LEFT click opened it"
    DB.render("dark", W, H,
              script=pre + [(x, y)] * 8 + [(x, y, False, 0.0, True)] * 2
              + [(x, y, False, 0.0, False)] * DWELL)
    assert M.LAST_RECT.get("##ctx.ctx.1"), "right-click did not open the menu"


def test_a_context_menu_choice_lands(DB):
    from hyperspace.dkit import menu as M
    pre, r = scrolled_to_bottom(DB)
    rx, ry, _rw, rh = r.table_rows[1]
    x, y = rx + 200, ry + rh / 2
    openit = (pre + [(x, y)] * 8 + [(x, y, False, 0.0, True)] * 2
              + [(x, y, False, 0.0, False)] * 14)
    DB.render("dark", W, H, script=openit)
    r = M.LAST_RECT.get("##ctx.ctx.1")
    assert r, "the menu did not open"
    mx, my, mw, _mh = r
    ix, iy = mx + mw / 2, my + M.PAD + M.LABEL_H + M.ITEM_H / 2   # first item
    DB.render("dark", W, H,
              script=openit + [(ix, iy)] * 10 + [(ix, iy, True)] * 2
              + [(ix, iy, False)] * 6)
    assert DB.render.last_state["ctx"], "no choice landed"


def test_the_combobox_opens_and_filters(DB):
    """Typing must narrow the list, and the surviving row must be the right
    one - the thing a Select cannot do, and the reason this exists for a
    panel with 600-900 params.

    The panel shrinks as rows are filtered out, so its HEIGHT is the
    assertion: six planes to one is a real, measurable difference.
    """
    from hyperspace.dkit import comp_combobox as CC
    rx, ry, _rw, rh = DB.lay_out(W, H).ctl_rows[5]
    x, y = rx + DB.CTL_LABEL_W + 40, ry + rh / 2
    openit = [(x, y)] * 8 + [(x, y, True)] * 2 + [(x, y, False)] * 16
    DB.render("dark", W, H, script=openit)
    r = CC.LAST_RECT.get("##cb.ctl.find")
    assert r, "the combobox panel did not open"
    full_h = r[3]
    # the panel sits BELOW the field now - the trigger IS the input
    rr = DB.lay_out(W, H)
    fy = rr.ctl_rows[5][1]
    assert r[1] > fy, "the list did not open below the field"

    # "yw" is a subsequence of YW only - not of XY, XZ, XW, YZ or ZW
    typed = openit + [(x, y)] * 34
    DB.render("dark", W, H, script=typed,
              keys=[(len(openit) + 4, "y"), (len(openit) + 10, "w")])
    narrowed = CC.LAST_RECT.get("##cb.ctl.find")
    assert narrowed, "the panel closed while typing"
    assert narrowed[3] < full_h - 20.0, (
        f"the list did not narrow: {narrowed[3]} against {full_h}")


def test_the_button_group_picks_the_member_that_was_clicked(DB):
    """Three members abutting with one shared border column, so a click a
    third of the way along must land on the FIRST, not the second."""
    r = DB.lay_out(W, H)
    hx, hy, hw, hh = r.header
    # the demo's own right-aligned placement, read back from it rather than
    # recomputed here - a copied layout constant goes stale
    DB.render("dark", W, H, script=[(0.0, 0.0)] * 4)
    assert DB.render.last_state["range"] == "Week", "the default moved"
    gw = DB.render.last_group_w
    gx = hx + hw - DB.GUT - DB.render.last_github_w - 8.0 - gw
    by = hy + (hh - 32) / 2
    # the middle of the first member
    cx, cy = gx + gw / 6.0, by + 14
    DB.render("dark", W, H,
              script=[(cx, cy)] * 8 + [(cx, cy, True)] * 2
              + [(cx, cy, False)] * 8)
    assert DB.render.last_state["range"] == "Day", (
        f"clicking the first member gave {DB.render.last_state['range']!r}")


def test_the_destructive_button_is_clickable(DB):
    rx, ry, _rw, rh = DB.lay_out(W, H).ctl_rows[11]
    x, y = rx + DB.CTL_LABEL_W + 40, ry + rh / 2
    DB.render("dark", W, H,
              script=[(x, y)] * 10 + [(x, y, True)] * 2 + [(x, y, False)] * 8)
    said = DB.render.last_state.get("said")
    assert said and said.startswith("delete"), f"got {said!r}"


def test_a_mouse_click_leaves_no_focus_ring(DB):
    """`:focus-visible`, not `:focus`.

    ImGui has ONE notion of focus and a mouse click sets it, so a clicked
    button kept its 3px ring for ever and the ring walked from one button to
    the next as you clicked along a group. The browser rings a control
    reached by keyboard and never one reached by pointer.

    Rewritten, because the first version of this test could not fail: it
    compared the rows 1..6 px above the control ROW, and a Button sits
    centred inside its row, so the band it read was pixels no ring would ever
    reach whatever the code did. It now reads the three columns immediately
    outside the Button's own box - the strip `draw.ring` is calibrated to
    cover - and checks the keyboard case in the same breath, so "no ring"
    cannot pass by the ring being impossible.

    Dwells 40 frames after the release, well past the 150ms the ring takes
    to ease in.
    """
    from imgui_bundle import imgui

    from hyperspace.dkit import comp_button as CBtn

    _gl_or_skip()
    w, h = 110.0, 32.0

    def paint(ui):
        CBtn.ui_button(ui, "b", PROBE_X, PROBE_Y, w, h, "Button",
                       variant="outline")

    ground = ground_of("dark")
    on = (PROBE_X + w / 2, PROBE_Y + h / 2)
    click = [on] * 6 + [(*on, True)] * 2 + [(*on, False)] * DWELL
    clicked = one_widget("dark", paint, len(click), script=click)
    kb = one_widget("dark", paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])

    i_click = ring_ink(left_band(clicked[-1], PROBE_X, PROBE_Y, h), ground)
    i_kb = ring_ink(left_band(kb[-1], PROBE_X, PROBE_Y, h), ground)
    assert i_click < 1.0, f"a mouse click left a focus ring behind: {i_click:.1f}"
    assert i_kb > 10.0, (
        f"the keyboard did not ring the button either ({i_kb:.1f}), so the "
        f"click assertion above proves nothing")


def test_the_combobox_panel_keeps_its_side_while_you_type(DB):
    """It opens on one side and stays there. Measured on the real component:
    16 items pinned 90px from the bottom of a 900px viewport open on
    `side="top"`, and a filter that cuts them to one leaves it on top —
    the panel's near edge stays 6px off the field and only the far edge
    moves.

    The kit re-ran the placement every frame against the current content
    height, so the first keystroke shrank the panel, the shrunken panel
    suddenly fitted below, and it hopped across the field mid-word.

    Driven in a SHORT window, which is the configuration that made it hop:
    the control sits 48px off the bottom, so the full list cannot fit below
    it but a one-row list can.
    """
    from hyperspace.dkit import comp_combobox as CC
    SH = 820
    rr = DB.lay_out(W, SH)
    rx, ry, _rw, rh = rr.ctl_rows[5]
    x, y = rx + DB.CTL_LABEL_W + 40, ry + rh / 2
    assert SH - (ry + 32) < 120.0, "the control is not near the bottom"

    openit = [(x, y)] * 8 + [(x, y, True)] * 2 + [(x, y, False)] * 40
    DB.render("dark", W, SH, script=openit)
    first = CC.LAST_RECT.get("##cb.ctl.find")
    assert first, "the combobox panel did not open"
    above_at_rest = first[1] + first[3] <= ry + 1.0

    typed = openit + [(x, y)] * 50
    DB.render("dark", W, SH, script=typed,
              keys=[(len(openit) + 4, "y"), (len(openit) + 12, "w")])
    after = CC.LAST_RECT.get("##cb.ctl.find")
    assert after, "the panel closed while typing"
    assert after[3] < first[3] - 20.0, "the list did not narrow"
    above_when_short = after[1] + after[3] <= ry + 1.0
    assert above_at_rest == above_when_short, (
        f"the panel changed sides while filtering: was "
        f"{'above' if above_at_rest else 'below'} at y={first[1]}, "
        f"is {'above' if above_when_short else 'below'} at y={after[1]}")


def test_the_combobox_panel_hugs_the_field_on_whichever_side(DB):
    """`sideOffset: 6`, measured, and it holds after a filter: the gap
    between the panel's near edge and the field is the same number before
    and after."""
    from hyperspace.dkit import comp_combobox as CC
    from hyperspace.dkit import comp_combobox as _CC
    tbl = _CC.combobox_table("dark")
    SH = 820
    rr = DB.lay_out(W, SH)
    rx, ry, _rw, rh = rr.ctl_rows[5]
    x, y = rx + DB.CTL_LABEL_W + 40, ry + rh / 2
    openit = [(x, y)] * 8 + [(x, y, True)] * 2 + [(x, y, False)] * 40
    DB.render("dark", W, SH, script=openit)
    a = CC.LAST_RECT["##cb.ctl.find"]
    typed = openit + [(x, y)] * 50
    DB.render("dark", W, SH, script=typed,
              keys=[(len(openit) + 4, "y"), (len(openit) + 12, "w")])
    b = CC.LAST_RECT["##cb.ctl.find"]
    for r in (a, b):
        gap = (ry - (r[1] + r[3])) if r[1] < ry else (r[1] - (ry + 32.0))
        assert abs(gap - tbl["side_offset"]) <= 0.5, (
            f"panel at y={r[1]} h={r[3]} is {gap} off a field at {ry}, "
            f"not {tbl['side_offset']}")


def test_the_combobox_list_draws_no_scrollbar(DB):
    """`no-scrollbar` on the real list, measured as `offsetWidth -
    clientWidth == 0` in every state — including one scrolled 204px with
    456px of content in a 252px box. It scrolls and shows nothing.

    Asserted at the CALL, not on pixels. The pixel version of this test
    passed against the broken code: the dashboard's combobox holds six
    planes, 168px of rows in a 252px clamp, so nothing overflows and no
    thumb would have been drawn either way. A test that cannot fail is
    worse than no test, so this one watches the argument instead and is
    true whatever the demo happens to hold.
    """
    from hyperspace.dkit import comp_combobox as CC
    from hyperspace.dkit import interact as I

    seen = []
    real = I.scroll_area

    def spy(ui, key, x, y, w, h, content_h, **kw):
        seen.append((key, kw.get("bars", True)))
        return real(ui, key, x, y, w, h, content_h, **kw)

    rx, ry, _rw, rh = DB.lay_out(W, H).ctl_rows[5]
    x, y = rx + DB.CTL_LABEL_W + 40, ry + rh / 2
    openit = [(x, y)] * 8 + [(x, y, True)] * 2 + [(x, y, False)] * DWELL
    I.scroll_area = spy
    try:
        DB.render("dark", W, H, script=openit)
    finally:
        I.scroll_area = real
    assert CC.LAST_RECT.get("##cb.ctl.find"), "the combobox panel did not open"
    lists = [bars for key, bars in seen if key.endswith(".list")]
    assert lists, f"the combobox did not open a scroll area: {seen}"
    assert not any(lists), (
        f"the combobox list asked for scrollbars: {lists}")
    # and the page's own scroll area still has one, so this is a
    # per-region decision rather than the kit losing its scrollbars
    assert any(bars for key, bars in seen if not key.endswith(".list")), \
        f"nothing else drew a scrollbar: {seen}"


# --------------------------------------------------------------------------
# focus-visible: the ring, driven from the keyboard
# --------------------------------------------------------------------------
#
# These ask for one thing the dashboard tests cannot: a control that the
# KEYBOARD has reached. So they run one primitive in a window of its own and
# read the pixels immediately outside its box, where a `box-shadow: 0 0 0 3px`
# and nothing else can paint.
#
# Driving the keyboard is the whole point. `Ui.focus_visible` is only true
# while the last input was a key, so a scripted CLICK is what proves the gate:
# the same control, reached with the pointer, must come out with no ring at
# all. A test that only clicked would pass against code that ringed on every
# kind of focus, which is exactly the bug being fixed.
#
# Why its own harness rather than `dashboard.render`: ImGui's nav moves focus
# between the items of the focused window in submission order, so "the switch"
# in a window of 30 controls is however many arrow presses away the layout
# happens to put it today. One widget per window makes the focused item the
# only item. The window is torn down with its context at the end of each run -
# leaking one poisons every later render in the process.

PROBE_W, PROBE_H = 360, 140    # the probe window
PROBE_X, PROBE_Y = 80.0, 60.0  # where the one control goes
FAR = (5.0, 5.0)               # the pointer, parked clear of everything


def _probe_flags():
    from imgui_bundle import imgui
    return (imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_saved_settings
            # the kit paints its own ground; imgui's window_bg would sit
            # between the clear colour and the chrome and darken every read
            | imgui.WindowFlags_.no_background)


def one_widget(theme_name, paint, frames, *, script=None, keys=None):
    """Render ONE dkit primitive for `frames` frames; return the frames.

    `script` and `keys` are `dashboard.render`'s, so a test reads the same:
    `script` is (x, y[, down]) per frame - the last entry holds for the rest -
    and `keys` is [(frame, imgui.Key | str)], a str being a character.
    """
    import glfw
    from imgui_bundle import imgui
    from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
    from OpenGL import GL

    from hyperspace.dkit import draw as D
    from hyperspace.dkit import interact as I
    from hyperspace.dkit import tokens as T
    from hyperspace.dkit.ease import Anim

    theme = T.LIGHT if theme_name == "light" else T.DARK
    if not glfw.init():
        pytest.skip("GLFW failed to initialise")
    for hint, v in ((glfw.CONTEXT_VERSION_MAJOR, 3),
                    (glfw.CONTEXT_VERSION_MINOR, 3),
                    (glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE),
                    (glfw.OPENGL_FORWARD_COMPAT, True),
                    (glfw.VISIBLE, False), (glfw.SAMPLES, 0),
                    (glfw.COCOA_RETINA_FRAMEBUFFER, False)):
        glfw.window_hint(hint, v)
    win = glfw.create_window(PROBE_W, PROBE_H, "dkit ring probe", None, None)
    if not win:
        glfw.terminate()
        pytest.skip("could not create the hidden window")
    glfw.make_context_current(win)
    ctx = imgui.create_context()
    impl = GlfwRenderer(win)
    io = imgui.get_io()
    # ImGui's nav is off by default, and without it no key moves focus at all
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    faces = D.load_faces(io, HERE)
    anim = Anim()
    bgc = T.rgba("background", theme=theme)
    keymap = {}
    for at, k in (keys or []):
        keymap.setdefault(at + 2, []).append(k)
    sc = list(script or [])
    out = []
    try:
        for i in range(frames + 2):        # two warm-up frames, as render's
            glfw.poll_events()
            impl.process_inputs()
            if sc:
                m = sc[min(max(i - 2, 0), len(sc) - 1)]
                io.add_mouse_pos_event(float(m[0]), float(m[1]))
                if len(m) > 2:
                    io.add_mouse_button_event(0, bool(m[2]))
            for k in keymap.get(i, ()):
                if isinstance(k, str):
                    for ch in k:
                        io.add_input_character(ord(ch))
                else:
                    io.add_key_event(k, True)
                    io.add_key_event(k, False)
            imgui.new_frame()
            GL.glClearColor(bgc[0], bgc[1], bgc[2], 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            imgui.set_next_window_pos(imgui.ImVec2(0, 0))
            imgui.set_next_window_size(imgui.ImVec2(PROBE_W, PROBE_H))
            imgui.push_style_var(imgui.StyleVar_.window_padding,
                                 imgui.ImVec2(0, 0))
            imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
            imgui.begin("##ringprobe", None, _probe_flags())
            ui = I.Ui(imgui.get_window_draw_list(), faces, theme, anim, None,
                      theme_name=theme_name)
            with I.chrome(ui):
                paint(ui)
            imgui.end()
            imgui.pop_style_var(2)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()
            ui.frame_done(1.0 / 60.0)
            if i >= 2:
                fw, fh = glfw.get_framebuffer_size(win)
                raw = GL.glReadPixels(0, 0, fw, fh, GL.GL_RGB,
                                      GL.GL_UNSIGNED_BYTE)
                px = np.frombuffer(raw, np.uint8).reshape(fh, fw, 3)[::-1]
                out.append(px.copy())
    finally:
        impl.shutdown()
        imgui.destroy_context(ctx)      # or the next render inherits it
        glfw.terminate()
    return out


def left_band(frame, x, y, h, w=None):
    """The mean level of the `w` columns immediately LEFT of the box.

    That strip is where a CSS outer box-shadow paints and where nothing else
    does: `draw.ring` is calibrated to cover exactly [x - width, x).
    """
    from hyperspace.dkit import tokens as T
    w = int(T.RING_W if w is None else w)
    return float(frame[int(y):int(y) + int(h), int(x) - w:int(x), :].mean())


def top_band(frame, x, y, w, h=None):
    """The same strip, ABOVE the box - for a control with something of its
    own immediately to its left, like a slider thumb sitting on its track."""
    from hyperspace.dkit import tokens as T
    h = int(T.RING_W if h is None else h)
    return float(frame[int(y) - h:int(y), int(x):int(x) + int(w), :].mean())


def ring_ink(band, ground):
    """How far the band is from the page's own colour. 0 is no ring."""
    return abs(band - ground)


def ground_of(theme_name):
    from hyperspace.dkit import tokens as T
    bg = T.rgba("background", theme=T.LIGHT if theme_name == "light" else T.DARK)
    return sum(bg[:3]) / 3.0 * 255.0


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_switch_rings_from_the_keyboard_and_not_from_a_click(DB, theme_name):
    """The Switch had no focus ring at all, in either theme.

    Measured on the real one: keyboard focus paints a 3px `ring/50` band
    outside the track AND swaps the track's border to `ring`; the pointer
    paints neither, because `:focus-visible` does not match a mouse press.
    Both halves of that are checked here - the band by these pixels, the
    border colour by test_components - and the click case is what keeps the
    gate honest.
    """
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I
    from hyperspace.dkit import tokens as T

    _gl_or_skip()
    tw, th, _thumb = T.SWITCH_SIZES["default"]
    state = {"on": False}

    def paint(ui):
        _c, state["on"] = I.switch(ui, "sw", PROBE_X, PROBE_Y, state["on"])

    ground = ground_of(theme_name)
    rest = one_widget(theme_name, paint, DWELL,
                      script=[FAR] * DWELL)
    state["on"] = False
    # Tab both turns `focus_visible` on and, on a window of one item, leaves
    # ImGui's nav on that item
    kb = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    state["on"] = False
    on_sw = (PROBE_X + tw / 2, PROBE_Y + th / 2)
    click = ([on_sw] * 6 + [(*on_sw, True)] * 2 + [(*on_sw, False)] * DWELL)
    clicked = one_widget(theme_name, paint, len(click), script=click)

    i_rest = ring_ink(left_band(rest[-1], PROBE_X, PROBE_Y, th), ground)
    i_kb = ring_ink(left_band(kb[-1], PROBE_X, PROBE_Y, th), ground)
    i_click = ring_ink(left_band(clicked[-1], PROBE_X, PROBE_Y, th), ground)
    assert i_rest < 1.0, f"an untouched switch painted outside its box: {i_rest:.1f}"
    assert i_kb > 10.0, (
        f"no focus ring on a keyboard-focused switch: band ink {i_kb:.1f} "
        f"against {i_rest:.1f} at rest")
    assert i_click < 1.0, (
        f"a CLICKED switch rang: band ink {i_click:.1f}. `:focus-visible` "
        f"does not match a pointer press")
    # and it is there for the whole dwell, not just the frame the key landed
    late = [ring_ink(left_band(f, PROBE_X, PROBE_Y, th), ground)
            for f in kb[12:]]
    assert min(late) > 10.0, f"the ring flickered: {min(late):.1f}..{max(late):.1f}"


def test_a_disabled_switch_never_rings(DB):
    """`disabled` is the other half of the gate, and it is cheap to lose:
    the eased value has to be driven to 0, not read off the widget."""
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I
    from hyperspace.dkit import tokens as T

    _gl_or_skip()
    _tw, th, _t = T.SWITCH_SIZES["default"]

    def paint(ui):
        I.switch(ui, "sw", PROBE_X, PROBE_Y, False, disabled=True)

    fs = one_widget("light", paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    ink = ring_ink(left_band(fs[-1], PROBE_X, PROBE_Y, th), ground_of("light"))
    assert ink < 1.0, f"a disabled switch rang under the keyboard: {ink:.1f}"


def test_the_slider_rings_when_the_keyboard_reaches_it(DB):
    """The thumb carries all three of `hover:ring-3 focus-visible:ring-3
    active:ring-3`, so this pins the first and the third.

    What it does NOT prove is the `focus-visible` term in `interact.slider`:
    ImGui ACTIVATES a stock `slider_float` that is tabbed into (it is an
    inputable item, so the keyboard takes it over), and `active` rings the
    thumb on its own. Reverting the focus-visible term leaves this test
    green, which is worth saying rather than hiding -
    `test_the_range_sliders_thumb_rings_from_the_keyboard` is the one that
    goes red, because a range's thumbs are `invisible_button`s that focus
    without ever becoming active.

    Read ABOVE the thumb, not beside it: the three columns to its left are
    the track, which is painted either way.
    """
    from hyperspace.dkit import box as B
    from hyperspace.dkit import interact as I

    _gl_or_skip()
    w, h = 200.0, 16.0
    val = {"v": 0.5}

    def paint(ui):
        _c, val["v"] = I.slider(ui, "sl", PROBE_X, PROBE_Y, w, h, val["v"])

    _track, _rng, thumbs = B.slider_geom(PROBE_X, PROBE_Y, w, h, [0.5])
    t = thumbs[0]
    ground = ground_of("light")
    # The pointer is parked far away AND MOVED a pixel every frame, which is
    # what makes this test able to fail. ImGui reports `is_item_hovered` true
    # for a nav-focused item until the mouse next moves, so a still pointer
    # would have rung the thumb through `hover` whatever the focus code did -
    # the ring would have been there for the wrong reason and a broken
    # version would still have passed.
    jiggle = [(FAR[0] + (i % 2), FAR[1]) for i in range(DWELL)]
    rest = one_widget("light", paint, DWELL, script=jiggle)
    val["v"] = 0.5
    from imgui_bundle import imgui
    kb = one_widget("light", paint, DWELL, script=jiggle,
                    keys=[(2, imgui.Key.tab)])
    val["v"] = 0.5
    # the pointer on the thumb: the hover ring, which must still work
    hov = [(t.x + t.w / 2, t.y + t.h / 2)] * DWELL
    hovered = one_widget("light", paint, DWELL, script=hov)

    i_rest = ring_ink(top_band(rest[-1], t.x, t.y, t.w), ground)
    i_kb = ring_ink(top_band(kb[-1], t.x, t.y, t.w), ground)
    i_hov = ring_ink(top_band(hovered[-1], t.x, t.y, t.w), ground)
    assert i_rest < 1.0, f"an untouched thumb rang: {i_rest:.1f}"
    assert i_kb > 10.0, f"no ring on a keyboard-focused thumb: {i_kb:.1f}"
    assert i_hov > 10.0, f"the hover ring went missing: {i_hov:.1f}"


def test_a_mouse_opened_select_trigger_has_no_ring(DB):
    """The measurement this reverses. `interact.select` drove its ring off
    `open_`, and the browser does the opposite of that twice over: a trigger
    opened with the POINTER never rings, and opening one with the KEYBOARD
    moves focus into the listbox so the ring goes with it.

    Read above the trigger rather than beside it, because the panel's own
    `shadow-md` reaches a few rows up its left side.
    """
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I
    from hyperspace.dkit import menu as M
    from hyperspace.dkit import tokens as T

    _gl_or_skip()
    w = 160.0
    hh, _rk = T.SELECT_SIZES["default"]
    items = [M.Item(id="a", label="Alpha"), M.Item(id="b", label="Beta")]

    def paint(ui):
        I.select(ui, "se", PROBE_X, PROBE_Y, w, "Alpha", items)

    ground = ground_of("light")
    rest = one_widget("light", paint, DWELL, script=[FAR] * DWELL)
    # A TAB and nothing else. The ArrowDown that used to stand here was
    # there only to set `Ui.focus_visible`, which a Tab does on its own -
    # and ArrowDown is now an OPENER, measured on `?probe`'s `select.kb`
    # (Enter, Space, ArrowDown and ArrowUp all open a Select). An open
    # trigger has no ring by design, which is the next assertion down, so
    # pressing it here asked this test for both answers at once.
    kb = one_widget("light", paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    on = (PROBE_X + 40.0, PROBE_Y + hh / 2)
    click = [on] * 6 + [(*on, True)] * 2 + [(*on, False)] * DWELL
    opened = one_widget("light", paint, len(click), script=click,
                        keys=[(2, imgui.Key.tab), (4, imgui.Key.down_arrow)])

    i_rest = ring_ink(top_band(rest[-1], PROBE_X, PROBE_Y, w), ground)
    i_kb = ring_ink(top_band(kb[-1], PROBE_X, PROBE_Y, w), ground)
    i_open = ring_ink(top_band(opened[-1], PROBE_X, PROBE_Y, w), ground)
    assert i_rest < 1.0, f"an untouched trigger rang: {i_rest:.1f}"
    assert i_kb > 10.0, f"no ring on a keyboard-focused trigger: {i_kb:.1f}"
    assert i_open < 1.0, (
        f"a mouse-opened trigger rang: {i_open:.1f}. Measured, it carries no "
        f"box-shadow at all")


def test_the_input_rings_from_a_pointer_click(DB):
    """The one measured exception to `:focus-visible`, and it has to survive
    the gate going in everywhere else.

    Chromium matches `:focus-visible` on anything that takes text however the
    focus arrived: clicked with the pointer, the real Input rings - same
    band, same border - where a clicked Button, Switch or SelectTrigger does
    not. So `interact.text_input` must NOT be gated on `focus_visible`.
    """
    from hyperspace.dkit import interact as I
    from hyperspace.dkit import tokens as T

    _gl_or_skip()
    w = 180.0
    hh = T.INPUT["h"]
    val = {"t": ""}

    def paint(ui):
        _c, val["t"] = I.text_input(ui, "in", PROBE_X, PROBE_Y, w, val["t"],
                                    placeholder="Name")

    ground = ground_of("light")
    rest = one_widget("light", paint, DWELL, script=[FAR] * DWELL)
    val["t"] = ""
    on = (PROBE_X + 40.0, PROBE_Y + hh / 2)
    click = [on] * 6 + [(*on, True)] * 2 + [(*on, False)] * DWELL
    clicked = one_widget("light", paint, len(click), script=click)

    i_rest = ring_ink(left_band(rest[-1], PROBE_X, PROBE_Y, hh), ground)
    i_click = ring_ink(left_band(clicked[-1], PROBE_X, PROBE_Y, hh), ground)
    assert i_rest < 1.0, f"an untouched input rang: {i_rest:.1f}"
    assert i_click > 10.0, (
        f"a clicked Input did not ring: {i_click:.1f}. A text field matches "
        f"`:focus-visible` from the pointer too - measured")


def test_the_range_sliders_thumb_rings_from_the_keyboard(DB):
    """The two-thumb Slider, which is the case that can only come from
    `focus-visible`.

    A range does its own drag over two `invisible_button`s rather than a
    stock `slider_float`, so a thumb the keyboard has reached is focused and
    NOT active - neither `hover` nor `active` is true - and the band can only
    be there because the focus term put it there.
    """
    from imgui_bundle import imgui

    from hyperspace.dkit import box as B
    from hyperspace.dkit import interact as I

    _gl_or_skip()
    w, h = 200.0, 16.0
    val = {"lo": 0.3, "hi": 0.7}

    def paint(ui):
        _c, val["lo"], val["hi"] = I.range_slider(
            ui, "rs", PROBE_X, PROBE_Y, w, h, val["lo"], val["hi"])

    _track, _rng, thumbs = B.slider_geom(PROBE_X, PROBE_Y, w, h, [0.3, 0.7])
    t = thumbs[0]
    ground = ground_of("light")
    # moved every frame, so ImGui's nav-hover is cleared and `hot` is 0 -
    # see the note in the single-thumb test
    jiggle = [(FAR[0] + (i % 2), FAR[1]) for i in range(DWELL)]
    rest = one_widget("light", paint, DWELL, script=jiggle)
    val["lo"], val["hi"] = 0.3, 0.7
    kb = one_widget("light", paint, DWELL, script=jiggle,
                    keys=[(2, imgui.Key.tab)])

    i_rest = ring_ink(top_band(rest[-1], t.x, t.y, t.w), ground)
    i_kb = ring_ink(top_band(kb[-1], t.x, t.y, t.w), ground)
    assert i_rest < 1.0, f"an untouched range thumb rang: {i_rest:.1f}"
    assert i_kb > 10.0, f"no ring on a keyboard-focused range thumb: {i_kb:.1f}"


def test_the_range_sliders_track_takes_a_click(DB):
    """Radix moves the NEAREST thumb to the pointer when you press the
    track, and hands it the drag — the same thing a single-thumb slider does,
    because a single-thumb slider is a stock `imgui.slider_float` and that is
    what ImGui does. Only the two thumbs carried targets here, so a press on
    the track did nothing at all.

    Driven at three places: past the low thumb, past the high one, and
    between them nearer the low. Dwells past the 150ms transition so the
    value read back is the settled one.
    """
    r = DB.lay_out(W, H)
    rx, ry, rw, rh = r.ctl_rows[6]            # "Window", the range slider
    sx = rx + DB.CTL_LABEL_W
    sw = rw - DB.CTL_LABEL_W - 46
    lo0, hi0 = DB.CTL_STATE["win_lo"], DB.CTL_STATE["win"]

    def press(frac):
        cx = sx + 6 + frac * (sw - 12)
        cy = ry + rh / 2
        script = [(10, 10, False)] * 8 + [(cx, cy, False)] * 4 \
            + [(cx, cy, True)] * 3 + [(cx, cy, False)] * DWELL
        DB.render("dark", W, H, script=script, keep="last")
        s = DB.render.last_state
        return s["win_lo"], s["win"]

    lo, hi = press(0.05)
    assert lo < lo0 - 0.1, f"the low thumb did not come to the pointer: {lo}"
    assert hi == pytest.approx(hi0, abs=1e-6), "the high thumb moved too"

    lo, hi = press(0.95)
    assert hi > hi0 + 0.1, f"the high thumb did not come to the pointer: {hi}"
    assert lo == pytest.approx(lo0, abs=1e-6), "the low thumb moved too"

    # between them, nearer the low one: the low one goes
    lo, hi = press(0.45)
    assert lo > lo0 + 0.1 and hi == pytest.approx(hi0, abs=1e-6)


def test_the_disabled_range_slider_ignores_a_track_click(DB):
    """`disabled:pointer-events-none`. The dashboard's Bypass switch turns
    the whole control column off, which is how a disabled one is reachable
    at all."""
    r = DB.lay_out(W, H)
    bx, by, _bw, bh = r.ctl_rows[1]           # "Bypass"
    sw_x, sw_y = bx + DB.CTL_LABEL_W + 8, by + bh / 2
    rx, ry, rw, rh = r.ctl_rows[6]
    sx = rx + DB.CTL_LABEL_W
    sw = rw - DB.CTL_LABEL_W - 46
    cx, cy = sx + 6 + 0.05 * (sw - 12), ry + rh / 2

    script = [(10, 10, False)] * 6
    script += [(sw_x, sw_y, False)] * 3 + [(sw_x, sw_y, True)] * 2 \
        + [(sw_x, sw_y, False)] * DWELL          # bypass on -> column off
    script += [(cx, cy, False)] * 3 + [(cx, cy, True)] * 3 \
        + [(cx, cy, False)] * DWELL
    DB.render("dark", W, H, script=script, keep="last")
    s = DB.render.last_state
    assert s["bypass"], "the bypass switch did not turn on"
    assert s["win_lo"] == pytest.approx(DB.CTL_STATE["win_lo"], abs=1e-6), \
        "a disabled range slider moved"


def test_the_inputs_value_sits_on_the_placeholders_line(DB):
    """The value and the placeholder are one line of one field, so their ink
    must land on the same rows. Nothing else about an input is worth
    asserting here: this is the thing a person looks at.

    The first version of this test measured the SELECTION BAND - imgui's own
    line box - and the band was centred while the glyphs were not, so it
    passed on text that visibly sat high. A proxy for the observable is not
    the observable.

    Two causes, both now fixed. ImGui draws an InputText's text at the
    cursor PLUS `FramePadding`, default (4, 3), which the kit's own frame
    does not want; and the stock widget renders in imgui's CURRENT font,
    which is not the kit's face at `font * FONT_SPAN_EM` that `draw.label`
    draws the placeholder with - so the two had different metrics. The
    second is why this looked far worse on a Retina Mac, where the atlas is
    rasterised at 2x, than the 1px it measures here.
    """
    import numpy as np

    from hyperspace.dkit import tokens as T
    from hyperspace.dkit.dev import comp_gallery as CG

    TALL = 2600
    spots = {}
    # boot, measure, tear down, THEN render - `render()` ends in
    # `glfw.terminate()` and that destroys the atlas a held `faces` points
    # at. test_gallery.py carries the same helper and the same note.
    import glfw as _glfw
    from imgui_bundle import imgui as _im
    _win, impl, _io, fc, _grad = DB._boot("dark", 320, 240, visible=False,
                                         retina=False)
    try:
        gw = (W - DB.SIDEBAR_W) - 2 * DB.GUT
        _total, secs = CG.plan(gw, fc, "dark")
    finally:
        impl.shutdown()
        _im.destroy_context()
        _glfw.terminate()
    ox, oy = DB.SIDEBAR_W + DB.GUT, DB.HEADER_H + DB.GUT
    head = (T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
            + T.CARD_HEAD_GAP)
    yy = oy
    for title, _b, card_h, placed in secs:
        by = yy + CG.PAD + head
        for cap, sx, sy, sw, sh, _d in placed:
            if title == "Input":
                spots[cap] = (ox + CG.PAD + sx,
                              by + sy + CG.CAP_H + CG.CAP_GAP, sw, sh)
        yy += card_h + CG.GAP
    assert {"placeholder", "value"} <= set(spots), spots

    r = DB.lay_out(W, TALL)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    gx, gy = nx + nw / 2, ny + nh / 2
    script = [(10, 10, False)] * 6 + [(gx, gy, False)] * 4 \
        + [(gx, gy, True)] * 3 + [(gx, gy, False)] * DWELL
    f = np.asarray(DB.render("dark", W, TALL, script=script,
                             keep="last")[-1])[:, :, :3].astype(int)

    def ink_top(cap):
        x, y, w, h = spots[cap]
        # clear of the field's own border and of the caret at the far right
        reg = f[int(y) + 1:int(y + h) - 1, int(x) + 4:int(x + w) - 24]
        bg = np.median(reg.reshape(-1, 3), axis=0)
        d = np.abs(reg - bg).max(axis=2)
        rows = np.nonzero((d > 40).any(axis=1))[0]
        assert len(rows), f"no ink in the {cap} field"
        return int(rows.min()), int(rows.max())

    ph_top, ph_bot = ink_top("placeholder")
    _v_top, v_bot = ink_top("value")
    # The BASELINE - the bottom of the ink, as neither "Placeholder" nor
    # "600-cell" has a descender. Not the top: the placeholder is the fainter
    # ink, so its antialiased top row can fall under the threshold where the
    # value's does not, and in Inter it did - a row apart on one baseline.
    assert v_bot == ph_bot, (
        f"the value's ink ends at row {v_bot} and the placeholder's at "
        f"{ph_bot} - they are one line of one field")
    # and that line is centred in the field, which is what makes BOTH right
    # rather than equally wrong
    h = spots["placeholder"][3]
    above, below = ph_top, (h - 2) - ph_bot
    assert abs(above - below) <= 1, (
        f"the line is {above} from the top and {below} from the bottom of a "
        f"{h:.0f}px field")


# --------------------------------------------------------------------------
# the four controls that had no focus ring at all
# --------------------------------------------------------------------------
#
# RETRO row 21: `invisible_button` could not take keyboard focus in ImGui
# 1.92.9, so the Button's ring - the "reference implementation" - had never
# painted once. Porting it would have shipped four more rings that cannot
# appear and four tests that cannot fail. So each of these is DRIVEN: a real
# Tab, a real dwell past the 9-frame transition, and pixels.


def _col_mean(frame, x, y, h):
    """One column of pixels, as a mean level."""
    return float(frame[int(y):int(y) + int(h), int(x), :].mean())


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_tabs_trigger_rings_from_the_keyboard(DB, theme_name):
    """Measured on the real TabsTrigger: `ring/50` at 3px, `border-ring`, AND
    a 1px solid outline at full `ring`. The band is what is checked here; the
    colours are held by test_components against tokens.TABS_FOCUS.

    Compared against the REST frame rather than the page ground, because a
    trigger's ring band falls inside the TabsList's own `muted` fill - there
    is no page showing there to compare with.
    """
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I

    _gl_or_skip()
    ITEMS = ["Overview", "Bands"]

    def paint(ui):
        I.tabs(ui, "tab", PROBE_X, PROBE_Y, 36.0, ITEMS, 0)

    rest = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL)
    kb = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    # the first trigger sits at pad=3 inside the list
    tx, ty, th = PROBE_X + 3.0, PROBE_Y + 3.0, 30.0
    b_rest = left_band(rest[-1], tx, ty, th)
    b_kb = left_band(kb[-1], tx, ty, th)
    assert abs(b_kb - b_rest) > 8.0, (
        f"no focus ring on a keyboard-focused tabs trigger: band {b_kb:.1f} "
        f"against {b_rest:.1f} at rest")
    # and for the whole dwell, not just the frame the key landed on
    late = [abs(left_band(f, tx, ty, th) - b_rest) for f in kb[12:]]
    assert min(late) > 8.0, f"the ring flickered: {min(late):.1f}..{max(late):.1f}"


def test_a_clicked_tabs_trigger_does_not_ring(DB):
    """`:focus-visible`, not `:focus` - the gate that made the Button's ring
    walk along behind the pointer before it was added."""
    from hyperspace.dkit import interact as I

    _gl_or_skip()
    ITEMS = ["Overview", "Bands"]

    def paint(ui):
        I.tabs(ui, "tab", PROBE_X, PROBE_Y, 36.0, ITEMS, 0)

    tx, ty, th = PROBE_X + 3.0, PROBE_Y + 3.0, 30.0
    rest = one_widget("light", paint, DWELL, script=[FAR] * DWELL)
    on = (tx + 30.0, ty + th / 2)
    script = [on] * 6 + [(*on, True)] * 2 + [(*on, False)] * DWELL
    clicked = one_widget("light", paint, len(script), script=script)
    b_rest = left_band(rest[-1], tx, ty, th)
    b_click = left_band(clicked[-1], tx, ty, th)
    assert abs(b_click - b_rest) < 3.0, (
        f"a CLICKED tabs trigger rang: band {b_click:.1f} against "
        f"{b_rest:.1f} at rest")


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_sidebar_items_ring_is_two_pixels_not_three(DB, theme_name):
    """The measured difference from Button, and the reason HANDOFF's "apply
    the settled model" was wrong: a SidebarMenuButton rings `ring-2` at FULL
    opacity where Button rings 3px at /50.

    So the assertion is column-wise: the two columns outside the box carry
    ink and the THIRD does not. Porting Button's 3px ring passes a "does it
    ring" test and fails this one.
    """
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I

    _gl_or_skip()
    W, H = 180.0, 32.0

    def paint(ui):
        I.sidebar_item(ui, "nav", PROBE_X, PROBE_Y, W, H, "Catalog")

    ground = ground_of(theme_name)
    kb = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    rest = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL)
    f = kb[-1]
    c1 = abs(_col_mean(f, PROBE_X - 1, PROBE_Y, H) - ground)
    c2 = abs(_col_mean(f, PROBE_X - 2, PROBE_Y, H) - ground)
    c3 = abs(_col_mean(f, PROBE_X - 3, PROBE_Y, H) - ground)
    r3 = abs(_col_mean(rest[-1], PROBE_X - 3, PROBE_Y, H) - ground)
    assert c1 > 10.0 and c2 > 10.0, (
        f"the sidebar item's 2px ring did not paint: columns "
        f"{c1:.1f}, {c2:.1f} against the page")
    assert c3 < max(3.0, r3 + 1.0), (
        f"a THIRD ring column painted ({c3:.1f}): this is `ring-2`, not "
        f"Button's `ring-[3px]`")


def test_a_clicked_sidebar_item_does_not_ring(DB):
    from hyperspace.dkit import interact as I

    _gl_or_skip()
    W, H = 180.0, 32.0

    def paint(ui):
        I.sidebar_item(ui, "nav", PROBE_X, PROBE_Y, W, H, "Catalog")

    ground = ground_of("light")
    on = (PROBE_X + W / 2, PROBE_Y + H / 2)
    script = [on] * 6 + [(*on, True)] * 2 + [(*on, False)] * DWELL
    clicked = one_widget("light", paint, len(script), script=script)
    ink = abs(_col_mean(clicked[-1], PROBE_X - 1, PROBE_Y, H) - ground)
    assert ink < 3.0, f"a CLICKED sidebar item rang: {ink:.1f}"


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_kebab_rings_from_the_keyboard(DB, theme_name):
    """`row_action` is a ghost icon Button, so its ring is Button's - read
    from comp_button's table rather than restated. Driven because a ring
    nobody has seen paint is a ring that does not."""
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I

    _gl_or_skip()
    S = 28.0

    def paint(ui):
        I.row_action(ui, "kebab", PROBE_X, PROBE_Y, S,
                     "ellipsis-vertical", 1.0)

    ground = ground_of(theme_name)
    rest = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL)
    kb = one_widget(theme_name, paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    i_rest = ring_ink(left_band(rest[-1], PROBE_X, PROBE_Y, S), ground)
    i_kb = ring_ink(left_band(kb[-1], PROBE_X, PROBE_Y, S), ground)
    assert i_rest < 1.0, f"an untouched kebab painted outside its box: {i_rest:.1f}"
    assert i_kb > 8.0, (
        f"no focus ring on a keyboard-focused kebab: {i_kb:.1f} against "
        f"{i_rest:.1f} at rest")
    late = [ring_ink(left_band(f, PROBE_X, PROBE_Y, S), ground)
            for f in kb[12:]]
    assert min(late) > 8.0, f"the ring flickered: {min(late):.1f}..{max(late):.1f}"


def test_a_faded_kebab_does_not_ring_at_full_strength(DB):
    """`row_action`'s chrome alpha has to reach the ring too: a kebab that
    has faded out must not be ringed at full strength by a stray focus."""
    from imgui_bundle import imgui

    from hyperspace.dkit import interact as I

    _gl_or_skip()
    S = 28.0

    def paint(ui):
        I.row_action(ui, "kebab", PROBE_X, PROBE_Y, S,
                     "ellipsis-vertical", 0.0)

    ground = ground_of("light")
    kb = one_widget("light", paint, DWELL, script=[FAR] * DWELL,
                    keys=[(2, imgui.Key.tab)])
    ink = ring_ink(left_band(kb[-1], PROBE_X, PROBE_Y, S), ground)
    assert ink < 1.0, (
        f"an invisible kebab rang at {ink:.1f}: the chrome alpha has to gate "
        "the ring as well as the fill")
