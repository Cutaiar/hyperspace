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
