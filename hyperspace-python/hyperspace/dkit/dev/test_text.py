"""The kit's text against Chromium's: widths, shaping, and the baseline.

RETRO row 61 found the kit's text measured differently from the browser's
in two ways: advances were whole pixels (and 12px text was set at 16/15.6
of its size), and 12px text sat ~0.93px low. Fixed in Geist (rows 77-82),
then the kit moved to Inter, the panel's own family (row 90). Both came from how the faces
were loaded, not from any one component - see "faces and metrics" in
`draw.py` and `build_fonts.py` - so they are pinned here, once, against
numbers Chromium produced:

* WIDTHS are canvas `measureText` with `"Inter Variable"` on `?probe`,
  which is the same text shaping the DOM uses (kerning and `calt` on);
* BASELINES are the bottom row of an "H"'s ink in a flex `items-center`
  box, one cell per (font size, box height, line-height), at dpr 1.

    xvfb-run -a uv run python -m pytest hyperspace/dkit/dev/test_text.py -q -n0
"""

from __future__ import annotations

import pytest

from hyperspace.dkit import draw as D

VARIANT = {400: "regular", 500: "medium", 600: "semibold"}

# (weight, px, text, Chromium's width) in Inter Variable. Chosen to cover
# each mechanism: kerning ("AVATAR", "Toggle"), the contextual alternates
# (below), every weight, 12-16px, and long strings where per-glyph rounding
# would add up.
BROWSER_W = [
    (500, 12, "Ctrl", 20.736),
    (400, 12, "Save Changes", 81.521),
    (500, 12, "Save Changes", 82.297),
    (500, 12, "K", 8.25),
    (500, 12, "W", 12.035),
    (500, 12, "B", 7.881),
    (400, 12, "Settings", 46.236),
    (500, 14, "Effects", 46.616),
    (500, 14, "AVATAR", 53.486),
    (400, 14, "1234567890", 82.811),
    (400, 16, "Toggle sidebar", 112.406),
    (600, 14, "Type a command or search...", 196.596),
    (600, 16, "Type a command or search...", 224.681),
    (400, 13, "Select a fruit", 77.733),
    # Inter's `calt`: one arrow glyph; a narrower multiplication sign
    # between digits; a raised colon, hyphen and parens (shape only)
    (400, 14, "->", 13.357),
    (500, 12, "1x2", 20.385),
    (400, 14, "12:30", 35.745),
    (500, 12, "A-B", 21.533),
    (400, 16, "(XY)", 33.445),
]

# (px, box height, line-height or 0 for normal, Chromium's baseline row).
# A sample of the 252 measured; it keeps both roundings - an odd leading
# BETWEEN the line box and the box goes down (12 in 21), an odd leading
# INSIDE the line box goes up (13 at 16px line-height in 16).
BROWSER_BASELINE = [
    (11, 15, 0, 12),
    (12, 20, 0, 15),
    (12, 21, 0, 15),
    (13, 15, 20, 13),
    (13, 16, 0, 13),
    (13, 16, 16, 13),
    (14, 32, 0, 22),
    (14, 33, 20, 22),
    (15, 17, 16, 14),
    (15, 18, 0, 15),
    (16, 24, 0, 18),
    (16, 33, 20, 23),
    (20, 23, 0, 19),
]


# --------------------------------------------------------------------------
# pure
# --------------------------------------------------------------------------

@pytest.mark.parametrize("px_, box, lh, want", BROWSER_BASELINE)
def test_the_baseline_is_where_chromium_puts_it(px_, box, lh, want):
    assert D.baseline_y(0.0, px_, box, lh) == want


def test_ascent_and_descent_round_separately_as_blink_does():
    """12px Inter is 11.63 above and 2.89 below: 12 and 3, a 15px glyph box.
    (Geist was 12.06 and 3.54: 12 and 4 - and ImGui, ceiling the ascent of
    a box it had rounded up to 16, put the baseline at 13, a pixel low.)"""
    assert D.ascent_descent(12.0) == (12.0, 3.0)
    assert D.ascent_descent(14.0) == (14.0, 3.0)


def test_substitutions_and_kerning_are_applied_before_measuring():
    glyphs, _pen = D.shape("->", "regular")
    assert len(glyphs) == 1, "`calt` makes -> one arrow, as Chromium shapes it"
    _, pen_av = D.shape("AV", "medium")
    _, pen_a = D.shape("A", "medium")
    assert pen_av[0] < pen_a[0], "A before V is kerned in"
    # a character the font does not carry is left to the fallback face
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
    """A hinted advance is a whole pixel. Medium "W" at 12px is 12.035 in
    Chromium and 12 with hinting on. (Not "K": Inter's is 8.25 exactly.)"""
    _gl()
    from imgui_bundle import imgui
    got = {}

    def paint(ui):
        D.push_css_font(ui.faces, "medium", 12.0)
        got["w"] = imgui.get_font().get_font_baked(12.0).get_char_advance(ord("W"))
        imgui.pop_font()
    _run(paint)
    assert abs(got["w"] - 12.035) < 0.02, got


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

    want = D.baseline_y(PROBE_Y, px_, box, D.TEXT_LEADING.get(px_, 0.0))
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

    from hyperspace.dkit.dev.test_interaction import PROBE_X, PROBE_Y, one_widget
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


def test_the_text_caches_survive_a_hot_reload_unless_shaping_changed():
    """REVIEW.md: module-level caches survive their module being reloaded.
    Shaped strings, widths and run cuts live in `draw._TEXT_CACHE`, kept
    across a reload; every key carries `draw._FINGERPRINT` (the font tables
    and the shaping code's source), so a reload that changes how text is
    shaped misses instead of serving the old result."""
    import importlib
    s = "Survives a hot reload"
    first = D.shape(s, "regular")
    cache = D._TEXT_CACHE
    importlib.reload(D)
    assert D._TEXT_CACHE is cache, "the reload replaced the cache"
    assert D.shape(s, "regular") is first, "the reload emptied the cache"
    kept = D._FINGERPRINT
    try:
        D._FINGERPRINT = ("shaping code changed",)
        assert D.shape(s, "regular") is not first, \
            "a changed fingerprint served the old result"
    finally:
        D._FINGERPRINT = kept


def test_a_full_text_cache_drops_the_oldest_strings_not_every_label(monkeypatch):
    """A readout whose digits change every frame mints a new key a frame.
    When the cache is full it must drop the least recently used entries -
    never the labels drawn every frame alongside them, which a clear-all
    threw out and rebuilt in one frame (REVIEW.md: no per-frame rebuilds)."""
    monkeypatch.setattr(D, "_TEXT_CACHE_MAX", 8)
    D._TEXT_CACHE.clear()
    stable = D.shape("Save Changes", "medium")
    for i in range(50):
        D.shape(f"{i * 0.37:.2f}", "regular", True)       # the readout
        assert D.shape("Save Changes", "medium") is stable, f"evicted at {i}"
    assert len(D._TEXT_CACHE) <= 8
