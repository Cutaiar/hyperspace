"""Vector marks (after PR #214): an SVG of pill-shaped bars read as its
stadia (`hyperspace.vector`), the source the Flow mark's two catalog
shapes are built from (`tests/test_catalog.py` checks the shapes)."""

from pathlib import Path

import pytest

from hyperspace import vector

REPO = Path(__file__).resolve().parents[2]


def test_the_flow_mark_reads_as_five_stadia_off_its_svg():
    # wisprflow.ai's own mark on its 28-unit artboard: five vertical bars,
    # left to right, their x centres and ends as #214 read them by hand
    bars, vb = vector.mark("flow-mark")
    assert vb == (0.0, 0.0, 28.0, 28.0)
    by_hand = ((8.8096, 7.9961, 20.0039), (11.4058, 13.4966, 18.7963),
               (14.0000, 9.9612, 17.9536), (16.5943, 13.4966, 18.7963),
               (19.1884, 7.9961, 19.9996))
    assert len(bars) == 5
    for s, (cx, top, bot) in zip(bars, by_hand):
        assert s.a[0] == pytest.approx(cx, abs=1e-3) == pytest.approx(s.b[0], abs=1e-3)
        assert s.a[1] - s.r == pytest.approx(top, abs=1e-3)
        assert s.b[1] + s.r == pytest.approx(bot, abs=1e-3)
        assert s.r == pytest.approx(0.8648, abs=0.003)


def test_the_apps_svg_is_the_prototypes_source():
    # one mark, two homes: the app's copy may not drift from the prototype's
    proto = REPO / "prototypes" / "subjects" / "sources" / "flow-mark.svg"
    if not proto.exists():
        pytest.skip("no prototypes/ beside hyperspace-python/")
    assert (vector.MARKS / "flow-mark.svg").read_bytes() == proto.read_bytes()


def test_relative_commands_draw_the_same_stadium():
    # a horizontal pill, once absolute and once relative: one stadium
    absolute = "M2 0H8C9.1 0 10 0.9 10 2C10 3.1 9.1 4 8 4H2C0.9 4 0 3.1 0 2C0 0.9 0.9 0 2 0Z"
    relative = "m2 0h6c1.1 0 2 .9 2 2s-.9 2-2 2h-6c-1.1 0-2-.9-2-2s.9-2 2-2z"
    a, b = vector.stadium_of(absolute), vector.stadium_of(relative)
    assert a.r == pytest.approx(2.0) and a.a == pytest.approx((2.0, 2.0))
    assert a.b == pytest.approx((8.0, 2.0))
    assert b.a == pytest.approx(a.a) and b.b == pytest.approx(a.b) and b.r == pytest.approx(a.r)


def test_an_outline_that_is_not_a_pill_is_refused_by_name():
    with pytest.raises(ValueError, match="not a stadium"):
        vector.stadium_of("M0 0L10 0L10 4L0 4Z")          # a rectangle's corners
    with pytest.raises(ValueError, match="arc"):
        vector.stadium_of("M0 0A2 2 0 0 1 4 0Z")
    with pytest.raises(ValueError, match="no width"):
        vector.stadium_of("M0 0L0 5Z")
