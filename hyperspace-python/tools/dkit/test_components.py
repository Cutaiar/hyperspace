"""The component geometry laws, pinned to what the browser actually does.

Every expected number here was read off tools/dkit/probe_react.js against the
real shadcn components in Chromium - not derived from the Tailwind classes.
That matters because three of them are not what the classes imply, and each
cost a measurement to find:

* a Slider's range and its thumb use DIFFERENT mappings;
* a Switch is 18.390625 px tall, not 18.4;
* the browser pixel-snaps what it paints while laying out on fractions.

No imgui context is needed: this is all pure geometry, the way
test_box.py and test_flex.py are.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import box as B          # noqa: E402
import draw as D         # noqa: E402
import tokens as T       # noqa: E402


# --------------------------------------------------------------------------
# Slider
# --------------------------------------------------------------------------
# Measured in Chromium at dpr 1. Each row is (width, fraction, range width,
# thumb left) straight out of getBoundingClientRect.
BROWSER_SLIDER = [
    (240, 0.00, 0.0, 0.0),
    (240, 0.25, 60.0, 57.0),
    (240, 0.50, 120.0, 114.0),
    (240, 0.75, 180.0, 171.0),
    (240, 1.00, 240.0, 228.0),
    (120, 0.50, 60.0, 54.0),
    (200, 0.50, 100.0, 94.0),
    (320, 0.50, 160.0, 154.0),
    (240, 0.375, 90.0, 85.5),      # a 0..8 domain at 3
]


@pytest.mark.parametrize("w,frac,rng_w,thumb_x", BROWSER_SLIDER)
def test_slider_matches_the_browser(w, frac, rng_w, thumb_x):
    track, rng, thumbs = B.slider_geom(0, 0, w, 16, [frac])
    assert track.w == w
    assert rng.x == 0.0
    assert rng.w == pytest.approx(rng_w)
    assert thumbs[0].x == pytest.approx(thumb_x)
    assert thumbs[0].w == 12.0


def test_slider_range_and_thumb_disagree_except_at_half():
    """The finding worth a test of its own.

    Reading the classes gives one mapping for both, and that is wrong
    everywhere but the middle: the range runs edge to edge while the thumb is
    inset by its own width. Chromium's numbers for a 240px track: at 25% the
    range ends at 60 and the thumb's centre is at 63; at 100% the range
    reaches 240 and the thumb's centre stops at 234.
    """
    _, rng, thumbs = B.slider_geom(0, 0, 240, 16, [0.25])
    assert rng.x + rng.w == pytest.approx(60.0)
    assert thumbs[0].x + thumbs[0].w / 2.0 == pytest.approx(63.0)

    _, rng, thumbs = B.slider_geom(0, 0, 240, 16, [1.0])
    assert rng.x + rng.w == pytest.approx(240.0)
    assert thumbs[0].x + thumbs[0].w / 2.0 == pytest.approx(234.0)

    # ... and they do agree at the midpoint, which is why a single mapping
    # looks right until it is checked anywhere else
    _, rng, thumbs = B.slider_geom(0, 0, 240, 16, [0.5])
    assert rng.x + rng.w == pytest.approx(120.0)
    assert thumbs[0].x + thumbs[0].w / 2.0 == pytest.approx(120.0)


def test_slider_two_thumbs():
    """Chromium, value [30, 70] on 240: range 96 wide at x 72, thumbs at
    68.391 and 159.594 (its 1/64 px layout grid rounding 68.4 and 159.6)."""
    _, rng, thumbs = B.slider_geom(0, 0, 240, 16, [0.3, 0.7])
    assert (rng.x, rng.w) == pytest.approx((72.0, 96.0))
    assert [t.x for t in thumbs] == pytest.approx([68.4, 159.6], abs=0.02)


def test_slider_thumb_never_overhangs_the_track():
    """What the inset is FOR, swept rather than spot-checked."""
    for w in (40, 120, 200, 240, 320):
        for i in range(101):
            f = i / 100.0
            track, _, thumbs = B.slider_geom(0, 0, w, 16, [f])
            t = thumbs[0]
            assert t.x >= track.x - 1e-9
            assert t.x + t.w <= track.x + track.w + 1e-9


def test_slider_track_is_centred_in_the_box():
    track, _, thumbs = B.slider_geom(0, 100, 200, 16, [0.5])
    assert track.y == 100 + (16 - 4) / 2.0
    assert thumbs[0].y == 100 + (16 - 12) / 2.0
    # both centres coincide, which is what `items-center` means
    assert track.y + track.h / 2.0 == thumbs[0].y + thumbs[0].h / 2.0


# --------------------------------------------------------------------------
# Switch
# --------------------------------------------------------------------------

def test_switch_default_size_is_fractional():
    """`h-[18.4px]` is laid out on Chromium's 1/64 px grid as 1177/64."""
    w, h, th = T.SWITCH_SIZES["default"]
    assert (w, th) == (32.0, 16.0)
    assert h == pytest.approx(18.390625)
    assert h == pytest.approx(1177 / 64)


@pytest.mark.parametrize("size,track,off_x,on_x,thumb", [
    # Chromium: thumb at x=1 off and x=15 on for default, 1 and 11 for sm
    ("default", (32.0, 18.390625), 1.0, 15.0, 16.0),
    ("sm", (24.0, 14.0), 1.0, 11.0, 12.0),
])
def test_switch_matches_the_browser(size, track, off_x, on_x, thumb):
    tr, o, n = B.switch_geom(0, 0, size)
    assert (tr.w, tr.h) == pytest.approx(track)
    assert o.x == pytest.approx(off_x)
    assert n.x == pytest.approx(on_x)
    assert o.w == o.h == thumb


def test_switch_thumb_sits_inside_the_border_and_is_flush_at_both_ends():
    for size in ("default", "sm"):
        tr, o, n = B.switch_geom(0, 0, size)
        assert o.x == 1.0                                  # inside the 1px border
        assert n.x + n.w == pytest.approx(tr.w - 1.0)      # flush right
        # vertically centred in the content box
        assert o.y == pytest.approx(1.0 + ((tr.h - 2.0) - o.h) / 2.0)
        assert o.y == n.y


def test_switch_travel_is_the_content_width_less_the_thumb():
    for size in ("default", "sm"):
        tr, o, n = B.switch_geom(0, 0, size)
        assert n.x - o.x == pytest.approx((tr.w - 2.0) - o.w)


# --------------------------------------------------------------------------
# Pixel snapping
# --------------------------------------------------------------------------

def test_snap_rounds_each_edge():
    # the Switch's own case: 790 .. 808.390625 is painted as 790 .. 808
    x, y, w, h = D.snap(120.0, 790.0, 32.0, 18.390625)
    assert (x, y, w, h) == (120.0, 790.0, 32.0, 18.0)

    # a Slider thumb at 33.3%: 102.604 .. 114.604 is painted 103 .. 115,
    # which keeps the width at 12 rather than shaving it
    x, y, w, h = D.snap(102.604, 842.0, 12.0, 12.0)
    assert (x, w) == (103.0, 12.0)


def test_snap_preserves_integer_rects_exactly():
    """It has to cost nothing on the rects the rest of the kit uses."""
    assert D.snap(40.0, 40.0, 86.0, 20.0) == (40.0, 40.0, 86.0, 20.0)


def test_snap_rounds_rather_than_truncates():
    # .6 goes up, .4 goes down - matching edge POSITIONS, not extents
    assert D.snap(0.0, 0.0, 10.6, 10.4)[2:] == (11.0, 10.0)


def test_snap_keeps_an_integer_size_exactly_under_translation():
    """A thumb slides across a track all day; it must not breathe a pixel.

    For an integer size this is exact - round(x + 12) - round(x) is 12 for
    every x - so a snapped slider thumb is always 12 px wide wherever its
    value puts it, and only its position moves. That is the property that
    makes snapping safe to apply to a continuously-dragged control.
    """
    for i in range(400):
        x = i / 7.0
        _, _, w, h = D.snap(x, x, 12.0, 12.0)
        assert w == 12.0 and h == 12.0


# --------------------------------------------------------------------------
# Rounded clipping
# --------------------------------------------------------------------------

def test_corner_flags_picks_only_the_corners_a_child_reaches():
    from imgui_bundle import imgui
    F = imgui.ImDrawFlags_
    bx, by, bw, bh = 0.0, 0.0, 100.0, 20.0

    # a left-anchored bar: the two left corners, as a slider range has
    f = D.corner_flags(0.0, 0.0, 40.0, 20.0, bx, by, bw, bh)
    assert f == (F.round_corners_top_left | F.round_corners_bottom_left)

    # the full width: all four
    f = D.corner_flags(0.0, 0.0, 100.0, 20.0, bx, by, bw, bh)
    assert f == (F.round_corners_top_left | F.round_corners_top_right
                 | F.round_corners_bottom_left | F.round_corners_bottom_right)

    # wholly interior, as a two-thumb range is: none, so it stays square
    f = D.corner_flags(30.0, 0.0, 40.0, 20.0, bx, by, bw, bh)
    assert f == F.round_corners_none

    # right-anchored
    f = D.corner_flags(60.0, 0.0, 40.0, 20.0, bx, by, bw, bh)
    assert f == (F.round_corners_top_right | F.round_corners_bottom_right)


def test_corner_flags_tolerates_float_slop():
    """A range at 100% lands on 239.99999 as readily as on 240, so the
    touch test carries half a pixel of tolerance."""
    from imgui_bundle import imgui
    F = imgui.ImDrawFlags_
    f = D.corner_flags(0.0, 0.0, 239.9999, 4.0, 0.0, 0.0, 240.0, 4.0)
    assert f & F.round_corners_top_right


def test_zero_width_range_draws_nothing():
    """A slider at its minimum has an empty range; it must not become a
    1px sliver or an inverted rect."""
    _, rng, _ = B.slider_geom(0, 0, 200, 16, [0.0])
    assert rng.w == 0.0
