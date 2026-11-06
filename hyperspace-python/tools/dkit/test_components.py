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


# --------------------------------------------------------------------------
# Spacing
# --------------------------------------------------------------------------
# The numbers come from a real shadcn Card + Field on the ?probe route, not
# from the Tailwind docs. They are here because the dashboard was first
# written without a scale and read cramped - 24px controls on a 27px pitch.

def test_space_is_tailwinds_4px_scale():
    assert T.SPACE[1] == 4.0 and T.SPACE[2] == 8.0 and T.SPACE[4] == 16.0
    # the half steps matter: shadcn uses them for control padding
    assert T.SPACE[1.5] == 6.0 and T.SPACE[2.5] == 10.0
    for k, v in T.SPACE.items():
        assert v == k * 4.0, f"SPACE[{k}] is {v}, off the 4px scale"


def test_control_padding_is_on_the_scale():
    """Tokenized padding, which is the point: a control's padding is a point
    on the same scale as a gap, not a literal that happens to look right."""
    assert T.INPUT["pad_x"] == T.SPACE[2.5]       # px-2.5
    assert T.SELECT["pad_l"] == T.SPACE[2.5]
    assert T.SELECT["pad_r"] == T.SPACE[2]        # pr-2
    assert T.TOOLTIP["pad_x"] == T.SPACE[3]       # px-3
    assert T.TOOLTIP["pad_y"] == T.SPACE[1.5]     # py-1.5


def test_card_rhythm_matches_the_browser():
    """Measured: 16 pad, a 22px title, 4, a 20px description, 16 to content.

    The demo wrote `y + 14` and `y + 34` instead - a 20px title-to-
    description gap where the component uses 4, which is why the headers read
    loose while the rows under them read tight.
    """
    assert T.CARD_PAD == 16.0
    assert T.CARD_TITLE_GAP == 4.0
    assert T.CARD_HEAD_GAP == 16.0
    assert T.card_body_y(0.0) == 16 + 22 + 4 + 20 + 16 == 78.0
    # a card with no description loses exactly the description and its gap
    assert T.card_body_y(0.0, description=False) == 16 + 22 + 16


def test_card_body_is_inside_the_padding():
    c = B.Rect(100.0, 500.0, 400.0, 300.0)
    body = B.card_body(c)
    assert body.x == c.x + T.CARD_PAD
    assert body.w == c.w - 2 * T.CARD_PAD
    assert body.y == T.card_body_y(c.y)
    assert body.y + body.h == c.y + c.h - T.CARD_PAD


def test_stack_leaves_a_real_gutter():
    """The bug this exists to stop: flex shrinks by default, so a stack that
    does not fit silently compressed every row - 24px controls came back as
    16.5px ones rather than overflowing visibly."""
    rows = B.stack(B.Rect(0.0, 0.0, 200.0, 1000.0), 5, 24.0, gap=T.SPACE[3])
    assert [r.h for r in rows] == [24.0] * 5
    gaps = [b.y - (a.y + a.h) for a, b in zip(rows, rows[1:])]
    assert gaps == [12.0] * 4

    # and it overflows rather than compressing when the box is too small
    tight = B.stack(B.Rect(0.0, 0.0, 200.0, 40.0), 5, 24.0, gap=T.SPACE[3])
    assert [r.h for r in tight] == [24.0] * 5


# --------------------------------------------------------------------------
# cover_corners — the other half of rounded clipping
# --------------------------------------------------------------------------

def test_cover_corners_covers_the_notch_and_spares_the_middle():
    """`fill_clipped` handles a rect child; this handles everything else, and
    it is what ScrollArea will need.

    The geometry is `corner_notches`, which carries no imgui - pulled out of
    `cover_corners` so it could be tested at all. Point-in-polygon rather
    than by eye: inside the rounded rect must be untouched, and the corner
    outside it must be covered.
    """
    import math

    x, y, w, h, r = 0.0, 0.0, 40.0, 30.0, 8.0
    polys = D.corner_notches(x, y, w, h, r)
    assert len(polys) == 4, "one notch per corner"

    def inside_any(px, py):
        for poly in polys:
            n, j = 0, len(poly) - 1
            for i in range(len(poly)):
                xi, yi = poly[i]
                xj, yj = poly[j]
                if (yi > py) != (yj > py) and \
                        px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi:
                    n += 1
                j = i
            if n % 2:
                return True
        return False

    # the box's own middle, and the centre of each edge, are never covered
    for px, py in ((w / 2, h / 2), (w / 2, 0.5), (0.5, h / 2),
                   (w - 0.5, h / 2), (w / 2, h - 0.5)):
        assert not inside_any(px, py), f"({px}, {py}) was covered"

    # the extreme corner pixels, which lie outside the rounded rect, are
    for px, py in ((0.3, 0.3), (w - 0.3, 0.3), (0.3, h - 0.3),
                   (w - 0.3, h - 0.3)):
        assert inside_any(px, py), f"corner ({px}, {py}) was left showing"

    # a point just inside the arc is spared
    cx, cy = x + r, y + r
    px, py = cx - r * math.cos(math.pi / 4) + 0.6, cy - r * math.sin(math.pi / 4) + 0.6
    assert not inside_any(px, py), "the cover ate into the rounded rect"
