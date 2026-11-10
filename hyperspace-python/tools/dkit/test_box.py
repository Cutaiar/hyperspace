"""Tests for the box model and popover placement.

Pure geometry — no GL, no display, no imgui. Popover placement in particular
is the kind of logic that is wrong in ways you only notice when a menu opens
off the bottom of the screen on someone else's monitor, so it is pinned here
rather than eyeballed once.

    uv run python -m pytest tools/dkit/test_box.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from box import Flow, Rect, place_popover

VIEW = Rect(0, 0, 1000, 800)


# -- Rect -----------------------------------------------------------------

def test_pad_css_shorthand():
    r = Rect(0, 0, 100, 100)
    assert r.pad(10).as_tuple() == (10, 10, 80, 80)
    assert r.pad(10, 20).as_tuple() == (20, 10, 60, 80)        # v, h
    assert r.pad(5, 10, 15).as_tuple() == (10, 5, 80, 80)      # t, h, b
    assert r.pad(1, 2, 3, 4).as_tuple() == (4, 1, 94, 96)      # t, r, b, l


def test_pad_never_goes_negative():
    assert Rect(0, 0, 10, 10).pad(50).w == 0


def test_pad_rejects_too_many_values():
    with pytest.raises(ValueError):
        Rect().pad(1, 2, 3, 4, 5)


def test_cuts_partition_exactly():
    r = Rect(10, 20, 100, 50)
    a, b = r.cut_left(30)
    assert a.as_tuple() == (10, 20, 30, 50)
    assert b.as_tuple() == (40, 20, 70, 50)
    a, b = r.cut_right(30)
    assert a.as_tuple() == (80, 20, 30, 50)
    assert b.as_tuple() == (10, 20, 70, 50)


def test_align_centres():
    assert Rect(0, 0, 100, 20).align(10, 10).as_tuple() == (45, 5, 10, 10)
    assert Rect(0, 0, 100, 20).align(10, 10, "end", "end").as_tuple() == \
        (90, 10, 10, 10)


# -- Flow -----------------------------------------------------------------

def test_flow_width_counts_gaps_between_not_around():
    f = Flow(gap=4).icon("x", 14).text("hi", 20, 16)
    assert f.width() == 14 + 4 + 20
    assert Flow(gap=4).icon("x", 14).width() == 14      # no trailing gap
    assert Flow(gap=4).width() == 0


def test_flow_places_without_overlap():
    """The badge bug: a hand-typed offset put the label a pixel inside the
    icon. Measured placement cannot do that."""
    f = Flow(gap=4).icon("trending-up", 14).text("+43", 22, 15)
    placed = f.place(Rect(0, 0, 100, 20))
    (_, a), (_, b) = placed
    assert a.right + 4 == b.x
    assert b.x >= a.right


def test_flow_centres_each_cell_vertically():
    f = Flow(gap=4).icon("x", 14).text("hi", 20, 10)
    (_, a), (_, b) = f.place(Rect(0, 0, 100, 20))
    assert a.cy == b.cy == 10


def test_flow_alignment_inside_a_box():
    f = Flow(gap=2).text("a", 10, 10).text("b", 10, 10)
    assert f.place(Rect(0, 0, 100, 10), "start")[0][1].x == 0
    assert f.place(Rect(0, 0, 100, 10), "end")[0][1].x == 100 - 22
    assert f.place(Rect(0, 0, 100, 10), "center")[0][1].x == (100 - 22) / 2


# -- popover placement ----------------------------------------------------

def test_anchors_below_the_trigger_not_at_the_mouse():
    anchor = Rect(500, 400, 26, 26)
    r, side = place_popover(anchor, 160, 150, VIEW)
    assert side == "bottom"
    assert r.y == anchor.bottom + 4          # sideOffset
    assert r.right == anchor.right           # align end


def test_align_start_and_centre():
    anchor = Rect(500, 400, 26, 26)
    assert place_popover(anchor, 160, 150, VIEW, align="start")[0].x == 500
    assert place_popover(anchor, 160, 150, VIEW, align="center")[0].cx == \
        anchor.cx


def test_flips_up_when_it_would_fall_off_the_bottom():
    anchor = Rect(500, 760, 26, 26)          # near the floor of an 800 view
    r, side = place_popover(anchor, 160, 150, VIEW)
    assert side == "top"
    assert r.bottom == anchor.y - 4
    assert r.y >= VIEW.y


def test_does_not_flip_when_there_is_room():
    anchor = Rect(500, 100, 26, 26)
    assert place_popover(anchor, 160, 150, VIEW)[1] == "bottom"


def test_shifts_back_inside_on_the_cross_axis():
    anchor = Rect(970, 100, 26, 26)          # hard against the right edge
    r, _ = place_popover(anchor, 300, 150, VIEW)
    assert r.right <= VIEW.right - 8
    assert r.x >= VIEW.x


def test_a_panel_taller_than_the_view_pins_to_the_top():
    """It cannot fit either way; pinning low would hide the first item,
    which is the one most likely to be wanted."""
    anchor = Rect(500, 400, 26, 26)
    r, _ = place_popover(anchor, 160, 2000, VIEW)
    assert r.y == VIEW.y + 8


def test_side_right_flips_to_left():
    anchor = Rect(960, 300, 26, 26)
    r, side = place_popover(anchor, 200, 100, VIEW, side="right",
                            align="start")
    assert side == "left"
    assert r.right == anchor.x - 4


@pytest.mark.parametrize("ax", range(0, 1000, 97))
@pytest.mark.parametrize("ay", range(0, 800, 79))
def test_never_leaves_the_viewport(ax, ay):
    """Wherever the trigger is, the panel stays on screen."""
    r, _ = place_popover(Rect(ax, ay, 26, 26), 180, 160, VIEW)
    assert r.x >= VIEW.x and r.y >= VIEW.y
    assert r.right <= VIEW.right and r.bottom <= VIEW.bottom
