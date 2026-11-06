"""End-to-end interaction tests, driven by synthetic input and read back
from pixels.

These exist because of a bug they would have caught and my earlier manual
check did not: the row kebab flickered and could never be clicked. The check
I ran hovered for six frames, which is *shorter than the 150ms transition*,
so the oscillation had not started yet and a screenshot looked fine.

So every test here **dwells well past the easing period** and asserts
stability over time, not just the state of one frame. A UI bug that needs
time to appear needs a test that spends time.

    uv run python -m pytest tools/dkit/test_interaction.py -q

Needs GL; skips cleanly without a display, the way the project's other
GL tests do (tests/gl_probe.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tests"))

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
    import dashboard
    return dashboard


def kebab_xy(DB, row=1):
    rx, ry, rw, rh = DB.lay_out(W, H).table_rows[row]
    return rx + rw - 30 + 13, ry + rh / 2


def menu_rect(key):
    """Where ImGui actually put the menu, from menu.LAST_RECT.

    Reading it from pixels was tried and is unreliable: a hovered table row
    composites to within a level of the popover fill, so the bounding box
    swallowed the row.
    """
    import menu as M
    return M.LAST_RECT.get(key)


def menu_item_xy(key, index):
    import menu as M
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
    x, y = kebab_xy(DB)
    frames = DB.render("dark", W, H, script=[(x, y)] * DWELL)
    settled = [ink(f, x, y) for f in frames[12:]]      # past the fade-in
    assert min(settled) > 1.0, "the kebab vanished while being hovered"
    spread = max(settled) - min(settled)
    assert spread < 1.0, f"the kebab flickered: ink varied by {spread:.2f}"


def test_kebab_opens_the_menu_after_a_long_hover(DB):
    """Press after dwelling — the case that was broken for a real person,
    who takes far longer than six frames to move and click."""
    x, y = kebab_xy(DB)
    script = [(x, y)] * DWELL + [(x, y, True)] * 2 + [(x, y, False)] * 14
    frames = DB.render("dark", W, H, script=script)
    before = ink(frames[DWELL - 1], x - 90, y + 70)
    after = ink(frames[-1], x - 90, y + 70)
    assert after > before + 2.0, (
        f"no menu appeared below the kebab after a {DWELL}-frame hover "
        f"(ink {before:.2f} -> {after:.2f})")


def test_menu_item_can_be_chosen(DB):
    """Open the menu, move onto its first item, click, see the choice land."""
    x, y = kebab_xy(DB)
    open_script = [(x, y)] * 20 + [(x, y, True)] * 2 + [(x, y, False)] * 12
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
    x, y = kebab_xy(DB)
    open_script = [(x, y)] * 20 + [(x, y, True)] * 2 + [(x, y, False)] * 12
    import menu as M
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
    x, y = kebab_xy(DB)
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
    """The Cutoff slider's track, as dashboard.paint lays it out."""
    rx, ry, rw, rh = ctl_rect(DB, 0)
    sx = rx + 92.0                      # the label column
    return sx, ry, rw - 92.0 - 54.0, rh


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
    x, y = rx + 92.0 + 16.0, ry + rh / 2
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
    x, y = rx + 92.0 + 16.0, ry + rh / 2
    script = [(x, y)] * 6 + [(x, y, True)] * DWELL + [(x, y, False)] * 6
    DB.render("dark", W, H, script=script)
    assert DB.render.last_state["bypass"] is True, (
        "holding the press toggled the switch more than once")


def test_select_opens_and_stays_open(DB):
    """The kebab bug's shape again: open the panel, then dwell on it. It has
    to still be there, and steady, forty frames later."""
    rx, ry, _, rh = ctl_rect(DB, 2)
    x, y = rx + 92.0 + 40.0, ry + rh / 2
    script = [(x, y)] * 10 + [(x, y, True)] * 2 + [(x, y, False)] * DWELL
    frames = DB.render("dark", W, H, script=script)
    import menu as M
    assert M.LAST_RECT.get("##sel.ctl.plane"), "the select panel did not open"
    below = [ink(f, x, y + rh + 24) for f in frames[-16:]]
    assert min(below) > 1.0, "the select panel vanished while open"
    assert max(below) - min(below) < 1.0, "the select panel flickered"


def test_select_choice_lands(DB):
    """Open it, move onto an item, click: the state must change."""
    rx, ry, _, rh = ctl_rect(DB, 2)
    x, y = rx + 92.0 + 40.0, ry + rh / 2
    open_script = [(x, y)] * 10 + [(x, y, True)] * 2 + [(x, y, False)] * 14
    DB.render("dark", W, H, script=open_script)
    import menu as M
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
    """A tooltip opens on a delay and must then STAY open.

    Both halves matter. Appearing instantly is wrong, and a tooltip that
    takes the hover from the control it describes would blink at the easing's
    period - the trap `row_action` exists to close, which a tooltip would
    walk straight back into if it had a hit target of its own.
    """
    sx, sy, sw, sh = slider_track(DB)
    x, y = sx + sw * 0.5, sy + sh / 2
    # TOOLTIP_DELAY is 0.4s; render steps a fixed 1/60 dt, so 24 frames
    frames = DB.render("dark", W, H, script=[(x, y)] * 70)
    above = [ink(f, x, y - 34) for f in frames]
    assert max(above[:12]) < 2.0, "the tooltip appeared before its delay"
    tail = above[-20:]
    assert min(tail) > 2.0, "the tooltip did not appear, or did not stay"
    assert max(tail) - min(tail) < 1.0, "the tooltip flickered once open"


def test_tooltip_goes_away_when_the_pointer_leaves(DB):
    sx, sy, sw, sh = slider_track(DB)
    x, y = sx + sw * 0.5, sy + sh / 2
    away = (sx + sw * 0.5, sy - 220)
    script = [(x, y)] * 50 + [away] * 20
    frames = DB.render("dark", W, H, script=script)
    assert ink(frames[49], x, y - 34) > 2.0, "the tooltip never opened"
    assert ink(frames[-1], x, y - 34) < 2.0, "the tooltip outlived the hover"


def test_input_takes_typing(DB):
    """Click into the field and type: the sandwich must pass the keyboard
    through to the real input_text underneath."""
    rx, ry, _, rh = ctl_rect(DB, 3)
    x, y = rx + 92.0 + 40.0, ry + rh / 2
    script = [(x, y)] * 6 + [(x, y, True)] * 2 + [(x, y, False)] * 30
    # characters, not keys: input_text is fed by character events
    DB.render("dark", W, H, script=script, keys=[(12, "Z"), (16, "9")])
    got = DB.render.last_state["name"]
    assert got != "600-cell", f"typing did not reach the input ({got!r})"
    assert "Z" in got and "9" in got, f"typed characters missing from {got!r}"
