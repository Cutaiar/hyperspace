"""shadcn Kbd and KbdGroup.

The box is in the pixel diff (`kbd.*` cells, both themes, the tooltip
restyle included). The diff hides glyphs, so what it cannot see is here:

* the WIDTH law - `max(min-w-5, text + px-1 twice)` - fed with Chromium's
  own text widths, because the kit's run a few percent wide (see below);
* KbdGroup's spacing, including its separator, which is MONOSPACE because
  KbdGroup is a <kbd> and never resets the UA font;
* the tooltip panel a Kbd grows and trims;
* where the glyph ink lands in the box, against where Chromium puts it.

Every number marked "?probe" was measured on the real component - the
probe blocks `kbd.*` and `tooltip.kbd`, and the canvas `measureText` widths
of Geist Variable at 12px - not derived from the classes.

    xvfb-run -a uv run python -m pytest tools/dkit/test_kbd.py -q -n0
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import draw as D     # noqa: E402
import tokens as T   # noqa: E402

TBL = T.kbd_table("light")

# Chromium's widths, Geist Variable 500 at 12px (canvas measureText), and
# the ⌘ / ⇧ of the fallback font it used here (Inter - see test docstring)
BROWSER_TEXT = {"K": 7.872, "B": 7.9, "Ctrl": 21.192, "⌘": 12.012,
                "⇧": 12.369}
# the Kbd boxes ?probe measured
BROWSER_W = {"K": 20.0, "Ctrl": 29.203, "⌘": 20.016, "⇧": 20.375}


def browser_text_w(s, variant, size):
    return BROWSER_TEXT[s]


# --------------------------------------------------------------------------
# geometry - pure
# --------------------------------------------------------------------------

@pytest.mark.parametrize("s", sorted(BROWSER_W))
def test_the_width_law_reproduces_the_browser(s):
    """A single glyph is min-w-5 (20); a word is its text plus 4 each side.
    The ⌘ is the edge case: its glyph is 12.012, so min-w loses by 0.012.
    Within 0.02 - the gap between canvas measureText and the laid-out
    text node, not a disagreement about the law."""
    w, h = D.kbd_size(s, None, TBL, text_w=BROWSER_TEXT[s])
    assert h == 20.0
    assert abs(w - BROWSER_W[s]) < 0.02, f"{s!r}: {w} against {BROWSER_W[s]}"


def test_a_group_with_a_separator_is_spaced_like_the_browser():
    """?probe `Ctrl + B`: group 66.813 wide, second key at 46.813. The "+"
    is 9.609 - monospace 0.6em at the parent's 16px - because KbdGroup is
    a <kbd> and the UA gives <kbd> `font-family: monospace`."""
    w, h = D.kbd_group_size(["Ctrl", "B"], None, TBL, sep="+", sep_font=16.0,
                            text_w=browser_text_w)
    # 0.03: two known sub-pixel sources add here - canvas measureText vs the
    # laid-out "Ctrl" (0.011), and Liberation Mono's real advance, 0.6006em
    # rather than 0.6 (0.009). Neither is a disagreement about the law.
    assert abs(w - 66.813) < 0.03, w
    assert abs(D.kbd_sep_w("+", TBL, 16.0) - 9.609) < 0.01


def test_a_chord_is_its_keys_a_gap_apart():
    """?probe `⌘ ⇧ P`: 20.016 + 4 + 20.375 + 4 + 20 = 68.391."""
    text = dict(BROWSER_TEXT, P=7.5)
    w, _ = D.kbd_group_size(["⌘", "⇧", "P"], None, TBL,
                            text_w=lambda s, v, z: text[s])
    assert abs(w - 68.391) < 0.02, w


# --------------------------------------------------------------------------
# rendered
# --------------------------------------------------------------------------

def _gl():
    from test_interaction import _gl_or_skip
    _gl_or_skip()


def _ink_centroid(frame, x, y, w, h):
    """Glyph ink's centroid inside a Kbd box, ignoring the rounded corners.
    The same reading `?probe`'s numbers were taken with."""
    x0, y0 = int(x), int(y)
    v = frame[y0:y0 + int(h), x0:x0 + int(np.ceil(w))].max(axis=2).astype(float)
    bg = np.median(v[3:-3, 3:-3][[0, -1]].ravel())
    ink = np.abs(v - bg)
    ink[ink < 8] = 0
    m = np.zeros_like(ink)
    m[2:-2, 2:-2] = 1
    ink *= m
    t = ink.sum()
    assert t > 0, "no glyph ink at all"
    return ((ink * np.arange(v.shape[1])[None]).sum() / t + 0.5,
            (ink * np.arange(v.shape[0])[:, None]).sum() / t + 0.5)


# Chromium's glyph ink centroids inside the 20px box, read off ?probe
# screenshots at dpr 1 - identical in both themes to 0.02
BROWSER_INK = {"K": (9.55, 9.69), "W": (10.07, 9.63)}


def _render(theme, s):
    from test_interaction import PROBE_X, PROBE_Y, one_widget

    def paint(ui):
        D.kbd(ui.dl, PROBE_X, PROBE_Y, s, ui.faces, ui.theme,
              T.kbd_table(theme), w=20.0)
    return one_widget(theme, paint, 2)[-1], PROBE_X, PROBE_Y


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("s", sorted(BROWSER_INK))
def test_the_glyph_is_centred_across_like_the_browser(theme, s):
    _gl()
    f, x, y = _render(theme, s)
    cx, _cy = _ink_centroid(f, x, y, 20.0, 20.0)
    assert abs(cx - BROWSER_INK[s][0]) < 0.25, (
        f"{s!r} ink at x {cx:.2f}, Chromium's at {BROWSER_INK[s][0]}")


@pytest.mark.xfail(strict=True, reason=(
    "Kit-wide, not Kbd's: 12px text sits ~0.93px LOWER than Chromium's in "
    "draw.label (14px agrees to ~0.1). The baked font's metrics are whole "
    "pixels - its advances are too, see HANDOFF. Strict, so the day the "
    "font metrics are fixed this goes red and has to be promoted."))
@pytest.mark.parametrize("s", sorted(BROWSER_INK))
def test_the_glyph_sits_at_the_browsers_height(s):
    _gl()
    f, x, y = _render("light", s)
    _cx, cy = _ink_centroid(f, x, y, 20.0, 20.0)
    assert abs(cy - BROWSER_INK[s][1]) < 0.4, (
        f"{s!r} ink at y {cy:.2f}, Chromium's at {BROWSER_INK[s][1]}")


def test_a_tooltip_with_a_kbd_grows_and_trims_like_the_browser(monkeypatch):
    """?probe `tooltip.kbd`: "Save Changes" + S is a 124.547 x 32 panel =
    12 + text + gap-2 + 20 + 6, where text alone would be 28 tall with 12
    either side. The panel is read at the call into draw; the TEXT width is
    the kit's own, so the assertion is the decomposition, not 124.547."""
    import interact as I
    from test_interaction import PROBE_X, PROBE_Y, one_widget
    _gl()
    got = {}
    real = D.tooltip_panel

    def spy(dl, x, y, w, h, *a, **k):
        got["wh"] = (w, h)
        return real(dl, x, y, w, h, *a, **k)

    monkeypatch.setattr(D, "tooltip_panel", spy)

    def paint(ui):
        got["tw"] = D.text_w("Save Changes", ui.faces, "regular", 12.0)
        I.tooltip(ui, "tip", (PROBE_X, PROBE_Y + 40, 40, 20), "Save Changes",
                  hovered=True, delay=0.0, kbd="S")
    one_widget("light", paint, 3)
    w, h = got["wh"]
    tip = T.TOOLTIP
    assert h == 20.0 + 2 * tip["pad_y"] == 32.0
    assert abs(w - (tip["pad_x"] + got["tw"] + TBL["tip_gap"] + 20.0
                    + tip["kbd_pad_r"])) < 1e-6
    assert tip["pad_x"] - tip["kbd_pad_r"] == 6.0, "the trim is pr-1.5"
