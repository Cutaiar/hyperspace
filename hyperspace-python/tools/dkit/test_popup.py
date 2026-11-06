"""What ImGui's popup WINDOW does, as opposed to what the kit paints in it.

A new file rather than more of `test_interaction.py`, because the thing under
test is not a component: it is the window every popup in the kit sits in, and
the defaults ImGui gives it. Those defaults are not neutral, and one of them
drew two vertical lines across the Combobox for as long as the Combobox has
existed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tests"))

W, H = 1440, 1400       # tall, so the Combobox's panel opens BELOW the field
DWELL = 40


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


def _open_the_combobox(DB):
    """Open the dashboard's Find combobox and return (frame, field, panel)."""
    import numpy as np
    import comp_combobox as CC
    r = DB.lay_out(W, H)
    kx, ky, _kw, kh = r.ctl_rows[5]
    cx, cy = kx + DB.CTL_LABEL_W + 40, ky + kh / 2
    script = [(10, 10, False)] * 10 + [(cx, cy, False)] * 6 \
        + [(cx, cy, True)] * 4 + [(cx, cy, False)] * DWELL
    f = np.asarray(DB.render("dark", W, H, script=script)[-1])[:, :, :3]
    rect = CC.LAST_RECT.get("##cb.ctl.find")
    assert rect, "the combobox panel did not open"
    return f.astype(int), (kx + DB.CTL_LABEL_W, ky, 150.0, 32.0), rect


def test_no_popup_border_bridges_the_gap_under_the_combobox(DB):
    """ImGui's `PopupBorderSize` is 1.0 and `WindowBorderSize` does not cover
    it. This popup's window is deliberately TALLER than its panel — it spans
    the trigger too, so the field's caret is inside the focused window — so
    that 1px ran down both sides of the 6px gap between the field and the
    list, as two vertical lines that have no counterpart in the browser.

    Measured before the fix: 75 against a 23 ground, every row of the gap, at
    exactly the field's left and right edges.

    Every other popup in the kit hid the same border by accident, because
    their window IS their panel and their own chrome covers it. That is luck,
    not a decision, so `menu.popup` turns it off too.
    """
    import comp_combobox as CC
    f, (fx, fy, fw, fh), (px, py, _pw, _ph) = _open_the_combobox(DB)
    assert py > fy + fh, "this test needs the panel BELOW the field"
    gap = range(int(fy + fh), int(py))
    assert len(gap) >= 4, f"the gap is only {len(gap)} px"

    # the page's own ground, read well clear of either box
    bg = f[int(fy) + 6, int(fx) - 20]
    for edge, xx in (("left", int(fx)), ("right", int(fx + fw) - 1)):
        col = [int(f[yy, xx].max()) for yy in gap]
        worst = max(abs(v - int(bg.max())) for v in col)
        assert worst <= 8, (
            f"the {edge} edge of the popup window paints across the gap: "
            f"{col} against a ground of {int(bg.max())}")


def test_the_field_still_rings_in_the_gap_which_the_browser_does_too(DB):
    """The companion to the test above, so the fix cannot be "paint nothing
    in the gap".

    The real component's focused input group carries
    `box-shadow: oklab(0.556 0 0 / 0.5) 0 0 0 3px`, and measured in Chromium
    that is a 3px band at 63 against a 10 ground, immediately under the
    field, full width. The kit draws the same band. What had to go was the
    window border beside it, not the ring.
    """
    f, (fx, fy, fw, fh), _panel = _open_the_combobox(DB)
    bg = int(f[int(fy) + 6, int(fx) - 20].max())
    mid = int(fx + fw / 2)
    band = [int(f[int(fy + fh) + d, mid].max()) for d in range(3)]
    assert min(band) > bg + 20, (
        f"no ring under the focused field: {band} against {bg}")
