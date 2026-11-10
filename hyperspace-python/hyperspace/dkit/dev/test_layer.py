"""layer.py against the browser's own Dialog and Sheet.

Measured on `?probe&open`, which carries both open. The numbers here are
Chromium's, not arithmetic over the tokens - RETRO row 27's rule - and three
of them are ones a reading of the Tailwind classes gets wrong: the scrim's
alpha, the fact that it also blurs, and the fact that a Dialog has NO drop
shadow where a Sheet has shadow-lg.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tests"))

from hyperspace.dkit import layer as L
from hyperspace.dkit import tokens as T

# the viewport the probe measured in
VP = (1200.0, 900.0)


# --------------------------------------------------------------------------
# the scrim
# --------------------------------------------------------------------------

def test_the_scrim_is_ten_percent_black_not_fifty():
    """`bg-black/10`, measured `oklab(0 0 0 / 0.1)`. The guess is 50 or 80,
    and at 10 the wash on its own dims almost nothing - which is why the
    blur below matters so much."""
    tok, a = L.SCRIM["bg"]
    assert a == 0.10
    assert T.rgba(tok, a)[:3] == (0.0, 0.0, 0.0)


def test_the_scrim_is_a_literal_black_and_does_not_swap_with_the_theme():
    """`foreground` is #0a0a0a light and #fafafa dark, so a scrim drawn in it
    would go WHITE in dark. Measured identical in both themes, which means it
    is a literal - the same shape as the slider thumb's `bg-white`."""
    tok, _a = L.SCRIM["bg"]
    assert tok == "#000000"
    light = T.rgba("foreground", theme=T.LIGHT)[:3]
    dark = T.rgba("foreground", theme=T.DARK)[:3]
    assert light != dark, "if these ever match, this test proves nothing"


def test_the_blur_is_recorded_as_a_number_rather_than_ignored():
    """`backdrop-blur-sm` is 4px and a draw list cannot do it - there is no
    read-back of what is behind. Recorded so the deviation is measurable
    rather than forgotten; see THE BLUR in layer.py."""
    assert L.SCRIM["blur"] == 4.0


# --------------------------------------------------------------------------
# geometry, against the browser's own rects
# --------------------------------------------------------------------------

def test_a_dialog_is_centred_where_chromium_centres_it():
    """Measured: a 384x141 Dialog in a 1200x900 viewport lands at
    (408, 379.5), and the browser snaps what it PAINTS to whole pixels - so
    380, by `draw.px`, which is floor(v + 0.5) and not Python's banker's
    round (RETRO row 36)."""
    r = L.dialog_rect(VP, h=141.0)
    assert (r.x, r.w, r.h) == (408.0, 384.0, 141.0)
    assert r.y == 380.0


def test_the_centring_snaps_with_draw_px_and_not_pythons_round():
    """h=141 does not discriminate: (900-141)/2 is 379.5 and both functions
    give 380. h=143 does - 378.5, where `draw.px` is 379 and Python's
    banker's `round` is 378. That is RETRO row 36, which cost a session of
    chasing a two-pixel wobble, so the distinction gets a case that can see
    it rather than one that happens to agree."""
    assert L.dialog_rect(VP, h=143.0).y == 379.0
    assert round(378.5) == 378, "if this changes, the test above is moot"


def test_a_dialogs_width_is_the_measured_max_not_the_viewport():
    """`sm:max-w-lg` = 384, measured. It does not grow with the viewport."""
    assert L.DIALOG["w"] == 384.0
    assert L.dialog_rect((1920.0, 1080.0), h=100.0).w == 384.0


def test_a_narrow_viewport_insets_the_dialog_rather_than_overflowing():
    """`max-w-[calc(100%-2rem)]`: it gives up width before it hangs off."""
    r = L.dialog_rect((300.0, 900.0), h=100.0)
    assert r.w == 300.0 - 2 * T.SPACE[4]
    assert r.x >= 0.0 and r.x + r.w <= 300.0


def test_a_sheet_is_flush_to_its_edge_at_the_measured_width():
    """Measured: side="right" in a 1200x900 viewport is (816, 0) 384x900 -
    flush, full height, and 816 = 1200 - 384."""
    r = L.sheet_rect(VP, "right")
    assert (r.x, r.y, r.w, r.h) == (816.0, 0.0, 384.0, 900.0)


@pytest.mark.parametrize("side,expect", [
    ("left",   (0.0, 0.0, 384.0, 900.0)),
    ("right",  (816.0, 0.0, 384.0, 900.0)),
    ("top",    (0.0, 0.0, 1200.0, 384.0)),
    ("bottom", (0.0, 516.0, 1200.0, 384.0)),
])
def test_every_sheet_side_is_flush_and_full_on_the_other_axis(side, expect):
    r = L.sheet_rect(VP, side)
    assert (r.x, r.y, r.w, r.h) == expect


def test_an_unknown_sheet_side_is_refused():
    """A typo should not silently become `right`."""
    with pytest.raises(ValueError):
        L.sheet_rect(VP, "centre")


# --------------------------------------------------------------------------
# the two panels are NOT the same panel
# --------------------------------------------------------------------------

def test_a_dialog_has_a_ring_and_no_drop_shadow():
    """The surprise in the dump. A Dialog's only box-shadow is
    `ring-1 ring-foreground/10`; every other layer of it measured
    transparent. The obvious implementation gives it shadow-lg like a
    popover and is wrong."""
    assert L.DIALOG["shadow"] is None
    assert L.DIALOG["ring"] == ("foreground", 0.10)
    assert L.DIALOG["ring_w"] == 1.0


def test_a_sheet_has_a_drop_shadow_and_no_ring():
    """The other way round, and measured: `0 10px 15px -3px rgba(0,0,0,.1),
    0 4px 6px -4px rgba(0,0,0,.1)`, which is shadow-lg."""
    assert L.SHEET["ring"] is None
    assert L.SHEET["shadow"] == T.SHADOW_LG
    assert T.SHADOW_LG == ((0.0, 10.0, 15.0, -3.0, 0.10),
                           (0.0, 4.0, 6.0, -4.0, 0.10))


def test_a_dialog_is_rounded_xl_and_a_sheet_is_square():
    """14, not the menus' 10 - and a Sheet is flush to the edge, so 0."""
    assert T.RADII[L.DIALOG["radius"]] == 14.0
    assert L.SHEET["radius"] == 0.0


def test_the_dialogs_padding_and_gap_are_on_the_spacing_scale():
    """p-4 / gap-4, and a Sheet's PANEL pads nothing - its header does."""
    assert L.DIALOG["pad"] == T.SPACE[4] == 16.0
    assert L.DIALOG["gap"] == T.SPACE[4]
    assert L.SHEET["pad"] == 0.0
    assert L.SHEET["gap"] == T.SPACE[4]


def test_the_close_button_is_the_measured_box():
    """28x28 on both, measured - a `size-7` ghost icon button."""
    assert L.DIALOG["close"] == 28.0
    assert L.SHEET["close"] == 28.0


# --------------------------------------------------------------------------
# and that the chrome actually paints - RETRO row 21's standing warning
# --------------------------------------------------------------------------

def test_the_dialog_panel_paints_its_fill_and_its_ring():
    """A table of measured numbers is worth nothing if the function that
    reads it draws nothing. RETRO row 21: the Button's focus ring - the
    "reference implementation" - had never once painted, because
    `invisible_button` could not take focus. So this renders it.

    Checks the three things the table claims: the fill is `background`, there
    IS a 1px ring one pixel outside the box, and there is NO drop shadow
    further out than that.
    """
    from hyperspace.dkit.dev import test_interaction as TI

    TI._gl_or_skip()
    # sized to the ring probe's window with room OUTSIDE the panel on every
    # side, because what is being checked is partly what is not there
    X, Y, W, H = 40.0, 40.0, 70.0, 40.0

    def paint(ui):
        L.panel_chrome(ui, ui.dl, X, Y, W, H, L.DIALOG)

    f = TI.one_widget("light", paint, 4, script=[TI.FAR] * 4)[-1]
    ground = TI.ground_of("light")
    mid = float(f[int(Y + H / 2), int(X + W / 2), :].mean())
    bg = T.rgba("background", theme=T.LIGHT)[:3]
    assert abs(mid - sum(bg) / 3.0 * 255.0) < 2.0, (
        f"the panel's fill is {mid:.1f}, not `background`")
    # the ring sits wholly OUTSIDE the box: the column at X-1 carries it
    ring_col = float(f[int(Y + H / 2), int(X) - 1, :].mean())
    assert abs(ring_col - ground) > 4.0, (
        f"no ring one pixel outside the panel: {ring_col:.1f} against a "
        f"ground of {ground:.1f}")
    # and nothing further out - a Dialog has no drop shadow
    for dx in (3, 5, 8):
        out = float(f[int(Y + H / 2), int(X) - dx, :].mean())
        assert abs(out - ground) < 2.0, (
            f"something painted {dx}px outside the panel ({out:.1f}): a "
            "Dialog's only box-shadow is its 1px ring")


def test_the_sheet_panel_paints_a_drop_shadow_where_the_dialog_does_not():
    """The other half of the pair, and the one that would catch the two
    tables being swapped."""
    from hyperspace.dkit.dev import test_interaction as TI

    TI._gl_or_skip()
    X, Y, W, H = 40.0, 40.0, 70.0, 40.0

    def paint(ui):
        L.panel_chrome(ui, ui.dl, X, Y, W, H, L.SHEET)

    f = TI.one_widget("light", paint, 4, script=[TI.FAR] * 4)[-1]
    ground = TI.ground_of("light")
    # shadow-lg reaches well past the 1px a ring would
    below = float(f[int(Y + H + 6), int(X + W / 2), :].mean())
    assert abs(below - ground) > 2.0, (
        f"no drop shadow under the sheet panel: {below:.1f} against "
        f"{ground:.1f}")
