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


# --------------------------------------------------------------------------
# The layout tree, against the demo
# --------------------------------------------------------------------------

def _dashboard():
    import dashboard
    return dashboard


def test_a_card_grows_when_a_row_is_added_to_it():
    """The whole point of intrinsic sizing, stated as a test.

    Before this the card's height was a number somebody typed, so a seventh
    row did not make the card taller - it landed outside it, silently, and
    nothing failed.
    """
    rows = tuple(B.Node(h=24.0) for _ in range(6))
    card = B.Node(dir="column", pad=(16.0,) * 4, gap=12.0, kids=rows)
    before = B.wants(card)[1]
    card.kids = rows + (B.Node(h=24.0),)
    after = B.wants(card)[1]
    assert after - before == 24.0 + 12.0, "the card did not grow by a row"


def test_flex_basis_zero_gives_equal_halves():
    """`flex-grow: 1` on an auto basis does NOT split a row evenly: grow only
    hands out what is left after each item's own content. Two cards with
    different contents came out 556 and 580. Equal halves need basis 0,
    which is what CSS calls `flex-1`."""
    def card(n):
        return B.Node(grow=1.0, dir="column", pad=(16.0,) * 4,
                      kids=tuple(B.Node(h=20.0, w=float(40 * n))
                                 for _ in range(n)))
    auto = B.Node(dir="row", gap=16.0, key="r",
                  kids=(card(2), card(5)))
    for i, k in enumerate(auto.kids):
        k.key = i
    got = B.lay_auto(auto, 0, 0, 800)
    assert got[0].w != got[1].w, "the auto-basis case is supposed to differ"

    zero = B.Node(dir="row", gap=16.0, kids=(card(2), card(5)))
    for i, k in enumerate(zero.kids):
        k.key, k.basis = i, 0.0
    got = B.lay_auto(zero, 0, 0, 800)
    assert got[0].w == got[1].w == 392.0


def test_stat_card_parts_are_inside_the_card_and_do_not_overlap():
    """The regression this cost me.

    Paint used to place a stat card's last two lines at `ch - 52` and
    `ch - 32`, derived from the card's own height. The moment layout gave
    the card its real height those offsets put the figure on top of the
    footnote. Layout and paint have to read the SAME rects; this asserts
    they do.
    """
    r = _dashboard().lay_out(1440, 1100)
    for card, part in zip(r.stats, r.stat_parts):
        cx, cy, cw, ch = card
        lines = [part[k] for k in ("title", "value", "head", "detail")]
        for x, y, w, h in lines:
            assert cx <= x and x + w <= cx + cw + 0.01, "a line left the card"
            assert cy <= y and y + h <= cy + ch + 0.01, "a line left the card"
        for (ax, ay, aw, ah), (bx, by, bw, bh) in zip(lines, lines[1:]):
            assert ay + ah <= by + 0.01, (
                f"stat card lines overlap: {ay + ah} > {by}")


def test_the_page_fits_the_window():
    """Nothing hangs off the bottom, at several window sizes."""
    D = _dashboard()
    for w, h in ((1440, 1100), (1280, 900), (1680, 1200)):
        r = D.lay_out(w, h)
        # The page SCROLLS now, so the body is taller than the window by
        # design - that is what body_h is. What must hold is that it is
        # laid out at its natural height and nothing escapes sideways.
        bottom = r.table_rows[-1][1] + r.table_rows[-1][3]
        assert bottom <= D.HEADER_H + r.body_h + 0.01, (
            f"the body overflows its own natural height at {w}x{h}")
        assert r.controls_card[0] + r.controls_card[2] <= w + 0.01


# --------------------------------------------------------------------------
# ScrollArea geometry
# --------------------------------------------------------------------------
# Chromium, measured on ?probe: a 320x200 ScrollArea with a 1px border, so
# the viewport is 198 tall and the scrollbar is 10 wide at x=309, y=1. Its
# track is the scrollbar less 1px of padding at each end.

BAR = dict(bar_x=309.0, bar_y=1.0, bar_w=10.0, bar_h=198.0, viewport_h=198.0)


@pytest.mark.parametrize("content,thumb_h", [
    (200, 194.04), (400, 97.02), (1200, 32.34),
    (3000, 18.0), (8000, 18.0), (30000, 18.0),      # the floor
])
def test_scroll_thumb_height_matches_the_browser(content, thumb_h):
    t = B.scroll_thumb(content_h=float(content), scroll_y=0.0, **BAR)
    assert t is not None
    assert t.h == pytest.approx(thumb_h, abs=0.02)
    assert (t.x, t.w) == (311.0, 7.0)               # 2 in, 7 wide


def test_the_thumbs_floor_is_real_and_not_rounding():
    """At a 198px viewport the ideal thumb goes 97, 32, 13, 5, 1 as the
    content grows; the rendered one stops at 18 and stays there."""
    ideal = [198.0 / c * 196.0 for c in (3000, 8000, 30000)]
    assert all(i < 18.0 for i in ideal)
    for c in (3000, 8000, 30000):
        assert B.scroll_thumb(content_h=float(c), scroll_y=0.0, **BAR).h == 18.0


@pytest.mark.parametrize("frac,y", [
    (0.0, 2.0), (0.25, 42.997), (0.5, 83.830), (0.75, 124.827), (1.0, 165.660),
])
def test_scroll_thumb_travel_matches_the_browser(frac, y):
    t = B.scroll_thumb(content_h=1200.0, scroll_y=frac * (1200.0 - 198.0), **BAR)
    assert t.y == pytest.approx(y, abs=0.1)


def test_no_thumb_when_there_is_nothing_to_scroll():
    """The browser draws no scrollbar without overflow, and neither should
    this - a full-height thumb on an unscrollable region is a lie."""
    assert B.scroll_thumb(content_h=198.0, scroll_y=0.0, **BAR) is None
    assert B.scroll_thumb(content_h=100.0, scroll_y=0.0, **BAR) is None


def test_thumb_stays_inside_its_track_at_every_scroll():
    """Swept, because an off-by-one here puts the thumb through the end of
    its own track at exactly the position people scroll to most."""
    for content in (250, 400, 1200, 9000):
        for i in range(101):
            sy = i / 100.0 * (content - 198.0)
            t = B.scroll_thumb(content_h=float(content), scroll_y=sy, **BAR)
            assert t.y >= 2.0 - 1e-6
            assert t.y + t.h <= 199.0 + 1e-6, f"{content} at {sy}"


def test_scroll_thumb_clamps_a_scroll_past_the_end():
    a = B.scroll_thumb(content_h=1200.0, scroll_y=1002.0, **BAR)
    b = B.scroll_thumb(content_h=1200.0, scroll_y=99999.0, **BAR)
    assert a.y == pytest.approx(b.y)


# --------------------------------------------------------------------------
# focus-visible: the ring every control gives the same answer about
# --------------------------------------------------------------------------
#
# Measured in Chromium under a REAL keyboard focus (a key pressed first, so
# the modality is keyboard, then `.focus()`), on every focusable component of
# the registry, in both themes. Every one of them answers the same two-part
# way:
#
#     box-shadow: <ring>/50 0 0 0 3px        a 3px band, no blur, no offset
#     border:     1px <ring>                 the border colour swaps
#
# with `destructive` the only variant that differs (band /20, border /40),
# `outline-style: none` everywhere in every state, and the element's rect
# unchanged - a shadow takes no layout space.
#
# The colours live in each component's token table, so the tests below read
# them out of `tokens` rather than restating them. What IS written out here
# is the browser's own bytes, which is the oracle's answer and the only
# number in the file that is not derived from another.

RING_BYTES = {
    # theme -> (the band composited over the page, the border)
    "light": ((208, 208, 208), (161, 161, 161)),
    "dark": ((63, 63, 63), (115, 115, 115)),
}


def composite(col, ground) -> tuple:
    """`col` over an opaque `ground`, as sRGB bytes, the way the page does.
    The same helper test_button.py uses, for the same reason: a token can be
    checked as a byte without a GL context."""
    r, g, b, a = col
    return tuple(round((c * a + gc / 255.0 * (1.0 - a)) * 255.0)
                 for c, gc in ((r, ground[0]), (g, ground[1]), (b, ground[2])))


GROUND = {"light": (255, 255, 255), "dark": (10, 10, 10)}
THEME = {"light": T.LIGHT, "dark": T.DARK}

# Every control that rings, and the table it keeps its ring colours in. The
# Slider is the odd one: its thumb's rest border is ALREADY `border-ring`, so
# there is no swap to make and `thumb_border` is what the focused border is.
RING_TABLES = {
    "input": (T.input_table, "ring", "focus_border"),
    "select": (T.select_table, "ring", "focus_border"),
    "switch": (T.switch_table, "ring", "focus_border"),
    "slider": (T.slider_table, "ring", "thumb_border"),
}


@pytest.mark.parametrize("control", sorted(RING_TABLES))
@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_every_ringed_control_names_the_same_two_colours(control, theme_name):
    """`ring/50` outside, `ring` on the border - and not one of them themed.

    The Button's `outline` variant is the only control in the kit whose
    focused border is NOT `ring` (`dark:border-input` outranks
    `focus-visible:border-ring` in Tailwind's output); measured, nothing
    here repeats that, so a table that overrode either colour in dark would
    be wrong and this would catch it.
    """
    table, ring_key, border_key = RING_TABLES[control]
    tbl = table(theme_name)
    assert tbl[ring_key] == ("ring", 0.5), f"{control}: {tbl[ring_key]}"
    assert tbl[border_key] == ("ring", 1.0), f"{control}: {tbl[border_key]}"


@pytest.mark.parametrize("control", sorted(RING_TABLES))
@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_ring_composites_to_the_browsers_bytes(control, theme_name):
    """What those two entries actually paint, as the page sees them."""
    table, ring_key, border_key = RING_TABLES[control]
    tbl = table(theme_name)
    theme, ground = THEME[theme_name], GROUND[theme_name]
    want_band, want_border = RING_BYTES[theme_name]
    band = composite(T.rgba(*tbl[ring_key], theme=theme), ground)
    border = composite(T.rgba(*tbl[border_key], theme=theme), ground)
    assert band == pytest.approx(want_band, abs=1), f"{control} band {band}"
    assert border == pytest.approx(want_border, abs=1), \
        f"{control} border {border}"


def test_the_band_is_three_pixels_and_one_constant_says_so():
    """`ring-3`, and the kit has one number for it rather than a 3 per
    component - which is what let the Switch and the Select drift apart in
    the first place."""
    assert T.RING_W == 3.0
    for table, ring_key, _b in RING_TABLES.values():
        # no component carries a width of its own to disagree with it
        assert "ring_w" not in table("light")


# --------------------------------------------------------------------------
# what draw.py actually paints, recorded rather than rasterized
# --------------------------------------------------------------------------

class Painted:
    """A draw list that records instead of drawing.

    With `draw._u32` patched to pass the colour straight through, every call
    arrives as floats and no imgui context is needed - the same bargain
    test_button.py makes by checking colour arithmetic rather than pixels.
    """

    def __init__(self):
        self.strokes = []      # (x, y, w, h, col, rounding, thickness)
        self.fills = []        # (x, y, w, h, col, rounding)

    def add_rect(self, p_min, p_max, col, rounding=0.0, thickness=1.0,
                 flags=0):
        self.strokes.append((p_min.x, p_min.y, p_max.x - p_min.x,
                             p_max.y - p_min.y, col, rounding, thickness))

    def add_rect_filled(self, p_min, p_max, col, rounding=0.0, flags=0):
        self.fills.append((p_min.x, p_min.y, p_max.x - p_min.x,
                           p_max.y - p_min.y, col, rounding))


@pytest.fixture
def painted(monkeypatch):
    monkeypatch.setattr(D, "_u32", lambda col: col)
    return Painted()


def band_of(rec, width=None):
    """The one stroke in `rec` that is the ring: the thickness says so."""
    want = T.RING_W if width is None else width
    hits = [s for s in rec.strokes if s[6] == want]
    assert len(hits) <= 1, f"more than one {want}px stroke: {hits}"
    return hits[0] if hits else None


def test_draw_ring_covers_exactly_the_columns_outside_the_box(painted):
    """A box-shadow spread paints OUTSIDE the border box and nowhere else.

    An add_rect stroke of thickness t straddles its path, so the expansion
    that lands the band's inner edge on the box's own edge is
    `0.5 + t / 2` - not t, and not t / 2. This derives the covered span back
    out of the recorded call rather than restating that formula.
    """
    x, y, w, h, r = 20.0, 40.0, 80.0, 32.0, 10.0
    D.ring(painted, x, y, w, h, (0.1, 0.2, 0.3, 1.0), r)
    bx, by, bw, bh, _col, rounding, t = band_of(painted)
    assert t == T.RING_W
    # a stroke of thickness t centred on the path covers [p - t/2, p + t/2),
    # and ImGui's own half-pixel offset is the other 0.5
    left_outer = bx - t / 2.0 + 0.5
    assert left_outer == pytest.approx(x - T.RING_W)
    assert bx + bw + t / 2.0 - 0.5 == pytest.approx(x + w + T.RING_W)
    assert by - t / 2.0 + 0.5 == pytest.approx(y - T.RING_W)
    # concentric: the band's outer edge is radius + width, its inner one radius
    assert rounding == pytest.approx(D.css_radius(r, w, h) + 0.5 + t / 2.0)
    # and it takes no layout space - the box it was asked about is untouched
    assert not painted.fills


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_switch_paints_both_halves_only_when_focused(painted, theme_name):
    """The Switch drew neither half. Both come out of its table now, so this
    checks the band's colour, the border's colour, and that `disabled`
    suppresses them - the three things `focus_f` is for."""
    theme = THEME[theme_name]
    tbl = T.switch_table(theme_name)
    kw = dict(theme=theme, tbl=tbl)

    rest = Painted()
    D.switch(rest, 10.0, 10.0, 0.0, focus_f=0.0, **kw)
    assert band_of(rest) is None, "an unfocused switch painted a band"
    # and no border either: `border-transparent` is a real 1px border in CSS
    # and nothing at all in a draw list, which draw.border short-circuits
    assert T.rgba(*tbl["border"], theme=theme)[3] == 0.0
    assert not rest.strokes, f"an unfocused switch stroked {rest.strokes}"

    D.switch(painted, 10.0, 10.0, 0.0, focus_f=1.0, **kw)
    band = band_of(painted)
    assert band, "a focused switch painted no band"
    assert band[4] == pytest.approx(T.rgba(*tbl["ring"], theme=theme))
    borders = [s for s in painted.strokes if s[6] == 1.0]
    assert borders[-1][4] == pytest.approx(
        T.rgba(*tbl["focus_border"], theme=theme))

    off = Painted()
    D.switch(off, 10.0, 10.0, 0.0, focus_f=1.0, disabled=True, **kw)
    assert band_of(off) is None, "a disabled switch rang"


def test_the_switchs_ring_eases_rather_than_snapping(painted):
    """`transition-[color,box-shadow]` runs for 150ms, so half way through
    the band is at half its alpha and the border is half swapped."""
    from ease import mix
    theme = T.LIGHT
    tbl = T.switch_table("light")
    D.switch(painted, 10.0, 10.0, 0.0, theme=theme, tbl=tbl, focus_f=0.5)
    band = band_of(painted)
    tok, al = tbl["ring"]
    assert band[4][3] == pytest.approx(T.rgba(tok, al * 0.5, theme=theme)[3])
    border = [s for s in painted.strokes if s[6] == 1.0][-1]
    assert border[4] == pytest.approx(
        mix(T.rgba(*tbl["border"], theme=theme),
            T.rgba(*tbl["focus_border"], theme=theme), 0.5))


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_select_triggers_border_swaps_to_the_ring(painted, monkeypatch,
                                                      theme_name):
    """The entry that was missing. `tokens.SELECT` carried the band and not
    the border, so `draw.field` fell back to leaving the border alone: the
    trigger rang with a border still `input`, where the browser measures
    `ring` in both themes."""
    monkeypatch.setattr(D, "icon", lambda *a, **k: True)
    theme = THEME[theme_name]
    tbl = T.select_table(theme_name)
    D.select_trigger(painted, 10.0, 10.0, 160.0, 32.0, theme, tbl, focus_f=1.0)
    border = [s for s in painted.strokes if s[6] == 1.0][0]
    assert border[4] == pytest.approx(T.rgba(*tbl["focus_border"], theme=theme))
    assert border[4] != pytest.approx(T.rgba(*tbl["border"], theme=theme))
    assert band_of(painted)[4] == pytest.approx(
        T.rgba(*tbl["ring"], theme=theme))


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_the_combobox_trigger_rings_on_keyboard_focus(painted, monkeypatch,
                                                      theme_name):
    """The old Popover+Command trigger, whose table entry used to say the
    ring was "NOT MEASURED, and deliberately NOT drawn".

    It is measured now - `ring/50 0 0 0 3px` under a real keyboard focus on
    the probe's PopoverTrigger - and the border half is the outline Button's
    dark anomaly all over again: `ring` in light, still `input` in dark.
    """
    import comp_combobox as C

    monkeypatch.setattr(D, "icon", lambda *a, **k: True)
    monkeypatch.setattr(D, "label", lambda *a, **k: None)
    theme = THEME[theme_name]
    tbl = C.combobox_table(theme_name)

    class FakeUi:
        dl = None
        faces = {}

        def col(self, name, a=1.0):
            return T.rgba(name, a, theme=theme)
    ui = FakeUi()
    ui.theme = theme

    rest = Painted()
    ui.dl = rest
    C._trigger(ui, tbl, 10.0, 10.0, 200.0, 32.0, 10.0, "Pick", "Pick",
               focus_f=0.0)
    assert band_of(rest) is None, "an unfocused trigger rang"

    ui.dl = painted
    C._trigger(ui, tbl, 10.0, 10.0, 200.0, 32.0, 10.0, "Pick", "Pick",
               focus_f=1.0)
    band = band_of(painted)
    assert band, "a keyboard-focused trigger painted no band"
    assert band[4] == pytest.approx(T.rgba(*tbl["trigger_ring"], theme=theme))
    border = [s for s in painted.strokes if s[6] == 1.0][0]
    assert border[4] == pytest.approx(
        T.rgba(*tbl["trigger_focus_border"], theme=theme))
    # light swaps the border, dark does not - the Button's measured anomaly
    swapped = tbl["trigger_focus_border"] != tbl["trigger_border"]
    assert swapped == (theme_name == "light")


# --------------------------------------------------------------------------
# the scrollbar sits inside the VIEWPORT, not against the root's edge
# --------------------------------------------------------------------------
# Measured on ?probe, `scroll.h200.content400`, a 320x200 root with
# `rounded-lg border`:
#
#     root       320 x 200     radius 10   overflow visible
#     viewport   318 x 198 @ 1,1           <- inset by the 1px border
#     scrollbar   10 x 198 @ 309,1         <- hangs off the VIEWPORT's edge
#     thumb        7 x  97 @ 311,2         <- +2 left (border-l + p-px), +1 top
#
# The kit hung the bar off the ROOT's edge, so the thumb sat on top of the
# border and one pixel further out than the browser's at every point - which
# is what "no gutter" looked like, and why it crossed the rounded corner more
# than the real one does.
BROWSER_SCROLL = {
    "root_w": 320.0, "root_h": 200.0, "border": 1.0,
    "bar_x": 309.0, "bar_y": 1.0, "bar_w": 10.0, "bar_h": 198.0,
    "thumb_x": 311.0, "thumb_y": 2.0, "thumb_w": 7.0, "thumb_h": 97.02,
    "viewport_h": 198.0, "content_h": 400.0,
}


def test_the_scroll_thumb_lands_where_the_browsers_does():
    b = BROWSER_SCROLL
    s = T.SCROLL
    assert s["border"] == b["border"]
    # the bar, derived the way draw.scroll_bar derives it
    bar_x = 0.0 + b["root_w"] - s["border"] - s["bar_w"]
    bar_y = 0.0 + s["border"]
    bar_h = b["root_h"] - 2 * s["border"]
    assert (bar_x, bar_y, bar_h) == (b["bar_x"], b["bar_y"], b["bar_h"])

    t = B.scroll_thumb(bar_x, bar_y, s["bar_w"], bar_h,
                       b["viewport_h"], b["content_h"], 0.0,
                       inset=s["track_inset"], thumb_w=s["thumb_w"],
                       thumb_inset=s["thumb_inset"], thumb_min=s["thumb_min"])
    assert (t.x, t.y, t.w) == (b["thumb_x"], b["thumb_y"], b["thumb_w"])
    assert abs(t.h - b["thumb_h"]) < 0.05


def test_the_thumb_keeps_a_gutter_off_the_right_edge():
    """Two pixels: the 1px border it is inside, and the 1px `p-px` rail."""
    b, s = BROWSER_SCROLL, T.SCROLL
    right = b["thumb_x"] + b["thumb_w"]
    assert b["root_w"] - right == s["border"] + s["track_inset"]


def test_a_region_with_no_border_gets_no_border_inset():
    """The dashboard's page is not a bordered box, so its bar hangs off its
    own edge. `border=0` is a caller's statement about its own chrome, not a
    switch to turn the measurement off."""
    s = T.SCROLL
    t = B.scroll_thumb(0.0 + 300.0 - 0.0 - s["bar_w"], 0.0, s["bar_w"], 200.0,
                       100.0, 400.0, 0.0,
                       inset=s["track_inset"], thumb_w=s["thumb_w"],
                       thumb_inset=s["thumb_inset"], thumb_min=s["thumb_min"])
    assert t.x + t.w == 300.0 - s["track_inset"]


# --------------------------------------------------------------------------
# the wheel
# --------------------------------------------------------------------------
def test_the_wheel_has_no_discontinuity_under_a_gesture():
    """What a browser does, measured: on macOS a trackpad sends
    pixel-precise deltas and the browser applies them 1:1 with no smoothing
    - one 300px wheel lands at exactly 300 in a single step, checked in
    Chromium. So this is only a scale factor, and the one thing it must not
    have is a step in it.

    The first version decided per EVENT - a delta of 1.0 or more was "a
    notch" and got ten times the precise rate. A trackpad sends whole-unit
    deltas constantly once you move at any speed, so every swipe crossed
    that threshold mid-gesture and sped up tenfold. That is what "still too
    fast" was.

    The device is decided ONCE now, by whether a fractional delta has ever
    arrived. This checks the mapping is linear across the old threshold.
    """
    import interact as I

    class _IO:
        mouse_wheel = 0.0

    io, font = _IO(), 18.2
    step = 5.0 * font
    I._PRECISE["seen"] = False
    try:
        # one fractional delta marks the device precise, for good
        io.mouse_wheel = 0.3
        I.tame_wheel(io, font_size=font)
        assert I._PRECISE["seen"]

        def px(raw):
            io.mouse_wheel = raw
            I.tame_wheel(io, font_size=font)
            return io.mouse_wheel * step

        # linear through the old 1.0 cliff, in both directions
        for a, b in ((0.9, 1.0), (1.0, 1.1), (0.5, 1.5), (-0.9, -1.1)):
            ra, rb = px(a) / a, px(b) / b
            assert abs(ra - rb) < 1e-6, (
                f"the rate changes between {a} and {b}: {ra} vs {rb}")
        # and the rate is the precise one
        assert abs(px(1.0) - T.SCROLL["px_per_unit"]) < 1e-6
    finally:
        I._PRECISE["seen"] = False


def test_a_notched_wheel_keeps_the_notch_rate():
    """A device that has only ever sent whole units is a notched wheel, and
    a browser gives one of those about 120px a tick, not 10."""
    import interact as I

    class _IO:
        mouse_wheel = 0.0

    io, font = _IO(), 18.2
    I._PRECISE["seen"] = False
    try:
        io.mouse_wheel = -1.0
        I.tame_wheel(io, font_size=font)
        assert abs(io.mouse_wheel * 5.0 * font + T.SCROLL["notch_px"]) < 1e-6
    finally:
        I._PRECISE["seen"] = False


def test_the_scroll_rate_can_be_dialled_without_an_edit():
    """`DKIT_SCROLL_PX`, because this is the one constant in the kit that
    cannot be measured on the machine that builds it - the units a trackpad
    sends per point are a property of the GLFW build and the platform."""
    import os
    import interact as I
    old = os.environ.get("DKIT_SCROLL_PX")
    os.environ["DKIT_SCROLL_PX"] = "3.5"
    try:
        assert I.wheel_px_per_unit() == 3.5
    finally:
        if old is None:
            os.environ.pop("DKIT_SCROLL_PX", None)
        else:
            os.environ["DKIT_SCROLL_PX"] = old
