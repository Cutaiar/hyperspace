"""The kit's text against Chromium's: widths, shaping, and the baseline.

RETRO row 61 found the kit's text measured differently from the browser's
in two ways: advances were whole pixels (and 12px text was set at 16/15.6
of its size), and 12px text sat ~0.93px low. Both came from how the faces
were loaded, not from any one component - see "faces and metrics" in
`draw.py` and `build_fonts.py` - so they are pinned here, once, against
numbers Chromium produced:

* WIDTHS are canvas `measureText` with `"Geist Variable"` on `?probe`,
  which is the same text shaping the DOM uses (kerning and ligatures on);
* BASELINES are the bottom row of an "H"'s ink in a flex `items-center`
  box, one cell per (font size, box height, line-height), at dpr 1.

    xvfb-run -a uv run python -m pytest hyperspace/dkit/dev/test_text.py -q -n0
"""

from __future__ import annotations

import pytest

from hyperspace.dkit import draw as D

VARIANT = {400: "regular", 500: "medium", 600: "semibold"}

# (weight, px, text, Chromium's width). Chosen to cover each mechanism:
# kerning ("Ctrl", "AVATAR"), the width-changing ligatures ("Settings",
# "Effects", "office" - tt and ff), every weight, 12-16px, and long strings
# where per-glyph rounding would add up.
BROWSER_W = [
    (500, 12, "Ctrl", 21.192),
    (400, 12, "Save Changes", 78.541),
    (500, 12, "Save Changes", 80.197),
    (500, 12, "K", 7.872),
    (500, 12, "W", 11.616),
    (500, 12, "B", 8.256),
    (400, 12, "Settings", 45.42),
    (500, 14, "Settings", 54.67),
    (600, 16, "Settings", 64.4),
    (400, 14, "Effects", 44.45),
    (500, 12, "office", 31.414),
    (500, 14, "AVATAR", 50.078),
    (400, 14, "1234567890", 80.416),
    (400, 16, "Toggle sidebar", 107.04),
    (600, 14, "Type a command or search...", 188.355),
    (600, 16, "Type a command or search...", 215.264),
    (400, 13, "Select a fruit", 76.193),
]

# (px, box height, line-height or 0 for normal, Chromium's baseline row).
# A sample of the 252 measured; it keeps both roundings - an odd leading
# BETWEEN the line box and the box goes down (12 in 21), an odd leading
# INSIDE the line box goes up (13 at 16px line-height in 16).
BROWSER_BASELINE = [
    (11, 15, 0, 12),
    (12, 20, 0, 14),
    (12, 21, 0, 15),
    (13, 15, 20, 12),
    (13, 16, 0, 13),
    (13, 16, 16, 12),
    (14, 32, 0, 21),
    (14, 33, 20, 22),
    (15, 17, 16, 14),
    (15, 18, 0, 15),
    (16, 24, 0, 18),
    (16, 33, 20, 22),
    (20, 23, 0, 19),
]


# --------------------------------------------------------------------------
# pure
# --------------------------------------------------------------------------

@pytest.mark.parametrize("px_, box, lh, want", BROWSER_BASELINE)
def test_the_baseline_is_where_chromium_puts_it(px_, box, lh, want):
    assert D.baseline_y(0.0, px_, box, lh) == want


def test_ascent_and_descent_round_separately_as_blink_does():
    """12px Geist is 12.06 above and 3.54 below: 12 and 4, so a 16px glyph
    box - where rounding the SUM (15.6) would give 16 as well, but put the
    baseline at 13 under a ceil'd ascent, which is what the kit had."""
    assert D.ascent_descent(12.0) == (12.0, 4.0)
    assert D.ascent_descent(14.0) == (14.0, 4.0)


def test_kerning_and_ligatures_are_applied_before_measuring():
    glyphs, pen = D.shape("Settings", "regular")
    assert len(glyphs) == 7, "tt is one glyph, as Chromium shapes it"
    _, pen_c = D.shape("Ctrl", "medium")
    _, pen_c_alone = D.shape("C", "medium")
    assert pen_c[0] < pen_c_alone[0], "C before t is kerned in"
    # a character Geist does not carry is left to the fallback face
    assert D.shape("⌘", "medium")[1] == (None,)


def test_the_tabular_face_has_its_own_figures():
    _, prop = D.shape("1", "regular")
    _, tab = D.shape("1", "regular", tabular=True)
    assert tab[0] > prop[0]


# --------------------------------------------------------------------------
# rendered
# --------------------------------------------------------------------------

def _gl():
    from hyperspace.dkit.dev.test_interaction import _gl_or_skip
    _gl_or_skip()


def _run(paint):
    from hyperspace.dkit.dev.test_interaction import one_widget
    one_widget("light", paint, 1)


def test_the_text_widths_are_chromiums():
    """Within 0.03px, every one. Before: whole-pixel advances, unkerned, at
    16/15.6 of the size at 12px - "Ctrl" 22, "Save Changes" 82."""
    _gl()
    got = {}

    def paint(ui):
        for wt, px_, s, _ in BROWSER_W:
            got[(wt, px_, s)] = D.text_w(s, ui.faces, VARIANT[wt], float(px_))
    _run(paint)
    bad = [(wt, px_, s, round(got[(wt, px_, s)], 3), w)
           for wt, px_, s, w in BROWSER_W if abs(got[(wt, px_, s)] - w) > 0.03]
    assert not bad, f"(weight, px, text, kit, Chromium): {bad}"


def test_the_size_pushed_is_the_size_drawn():
    """ImGui rounds a font size to a whole pixel. The faces are built with a
    one-em line box so the kit pushes the CSS px itself, which is already
    whole - so nothing is lost to the rounding at any size it uses."""
    _gl()
    from imgui_bundle import imgui
    got = {}

    def paint(ui):
        for px_ in (11.0, 12.0, 13.0, 14.0, 16.0, 30.0):
            D.push_css_font(ui.faces, "regular", px_)
            got[px_] = imgui.get_font_size()
            imgui.pop_font()
    _run(paint)
    assert all(v == k for k, v in got.items()), got


def test_the_faces_are_not_hinted():
    """A hinted advance is a whole pixel. Medium "K" at 12px is 7.872 in
    Chromium and 8 with hinting on."""
    _gl()
    from imgui_bundle import imgui
    got = {}

    def paint(ui):
        D.push_css_font(ui.faces, "medium", 12.0)
        got["k"] = imgui.get_font().get_font_baked(12.0).get_char_advance(ord("K"))
        imgui.pop_font()
    _run(paint)
    assert abs(got["k"] - 7.872) < 0.02, got


@pytest.mark.parametrize("px_, box", [(11.0, 20.0), (16.0, 36.0), (14.0, 32.0)])
def test_a_stock_input_puts_its_glyphs_on_the_labels_baseline(px_, box):
    """InputText draws its own glyphs, on ImGui's line - its baked ascent
    below a truncated top - not on `baseline_y`. `stock_text_y` hands it
    the top that lands them on the same row as `draw.label`'s.

    At 14px in an even box ImGui's own centring already agrees (that is
    what the TTFs' 800 / -200 split was chosen for), so 14 alone cannot
    tell; 11px in 20 and 16px in 36 are where centring imgui's line box
    instead puts the glyphs a pixel off."""
    _gl()
    import numpy as np
    from imgui_bundle import imgui
    from hyperspace.dkit.dev.test_interaction import PROBE_X, PROBE_Y, one_widget

    def paint(ui):
        D.label(ui.dl, PROBE_X, PROBE_Y, "H", ui.faces, "regular", px_,
                (0, 0, 0, 1), baseline_box=box)
        D.push_css_font(ui.faces, "regular", px_)
        imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(0, 0))
        imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(0, 0, 0, 1))
        imgui.push_style_color(imgui.Col_.frame_bg, imgui.ImVec4(0, 0, 0, 0))
        imgui.set_cursor_screen_pos(imgui.ImVec2(
            PROBE_X + 60, D.stock_text_y(PROBE_Y, px_, box)))
        imgui.push_item_width(60)
        imgui.input_text("##stock", "H")
        imgui.pop_item_width()
        imgui.pop_style_color(2)
        imgui.pop_style_var()
        imgui.pop_font()

    f = one_widget("light", paint, 2)[-1].max(axis=2).astype(int)
    y0, y1 = int(PROBE_Y) - 4, int(PROBE_Y + box) + 4

    def ink_bottom(x0):
        col = (255 - f[y0:y1, int(x0):int(x0) + 30]).sum(axis=1)
        return y0 + int(np.nonzero(col > 200)[0][-1]) + 1

    want = D.baseline_y(PROBE_Y, px_, box)
    assert ink_bottom(PROBE_X) == want, "the label is off its own baseline"
    assert ink_bottom(PROBE_X + 60) == want, (
        f"the stock input's glyphs end at row {ink_bottom(PROBE_X + 60)}, "
        f"the label's at {want}")


def test_a_kerned_string_draws_as_wide_as_it_measures():
    """`label` draws a long string as `add_text` runs (`draw._runs`), which
    is ImGui's pen - unkerned - restarted at the kerned one whenever it has
    drifted DRIFT_PX. So the INK has to end where `text_w` says the string
    does. "AVATAR WAVE" at 14px medium is 56.04 unkerned and 50.08 kerned
    (Chromium); drawn as one run, its ink would overshoot by ~6px."""
    _gl()
    import numpy as np
    from test_interaction import PROBE_X, PROBE_Y, one_widget
    s, size = "AVATAR WAVE", 14.0
    got = {}

    def paint(ui):
        got["w"] = D.label(ui.dl, PROBE_X, PROBE_Y, s, ui.faces, "medium",
                           size, (0, 0, 0, 1), baseline_box=20)
    f = one_widget("light", paint, 2)[-1].max(axis=2).astype(int)
    band = 255 - f[int(PROBE_Y):int(PROBE_Y) + 20, int(PROBE_X) - 2:]
    cols = np.nonzero(band.sum(axis=0) > 40)[0]
    ink_right = int(PROBE_X) - 2 + int(cols[-1]) + 1
    # "E"'s right side bearing is under a pixel at 14px; a run start may
    # round by half a pixel, and a run's pen drift is DRIFT_PX at most
    assert abs(ink_right - (PROBE_X + got["w"])) < 1.5, (
        f"ink ends at {ink_right}, the string measures to "
        f"{PROBE_X + got['w']:.2f}")
