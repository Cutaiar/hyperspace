"""Tests for the easing curve and the animation store.

Pure maths and pure bookkeeping, so no GL and no display: these run
anywhere, unlike everything else in tools/dkit.

    uv run python -m pytest tools/dkit/test_ease.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ease import DURATION, STANDARD, Anim, cubic_bezier, mix  # noqa: E402


def test_endpoints_are_exact():
    assert cubic_bezier(0.0) == 0.0
    assert cubic_bezier(1.0) == 1.0


def test_out_of_range_clamps():
    assert cubic_bezier(-0.5) == 0.0
    assert cubic_bezier(1.5) == 1.0


# Chromium's own Web Animations output for
# cubic-bezier(0.4, 0, 0.2, 1), sampled off a paused animation.
# This curve is NOT symmetric: it is already past three quarters at the
# halfway point, which is what makes shadcn's hovers feel quick to start
# and slow to land.
BROWSER = {0.10: 0.025863, 0.25: 0.236587, 0.50: 0.775561,
           0.75: 0.959368, 0.90: 0.994354}


@pytest.mark.parametrize("x,y", sorted(BROWSER.items()))
def test_matches_the_browser(x, y):
    assert cubic_bezier(x) == pytest.approx(y, abs=1e-5)


def test_monotonic_and_bounded():
    prev = -1.0
    for i in range(201):
        y = cubic_bezier(i / 200.0)
        assert 0.0 <= y <= 1.0
        assert y >= prev - 1e-9
        prev = y


def test_eases_in_and_out():
    """Slow at both ends, fast in the middle — that is the whole point."""
    assert cubic_bezier(0.1) < 0.1          # still accelerating
    assert cubic_bezier(0.9) > 0.9          # already decelerating


def test_inverse_is_consistent():
    """X(t) solved back through the curve lands where it started."""
    for x in (0.07, 0.23, 0.5, 0.77, 0.93):
        y = cubic_bezier(x)
        assert 0.0 <= y <= 1.0
        # a nudge in x must not move y backwards
        assert cubic_bezier(x + 0.01) >= y - 1e-9


def test_first_sight_does_not_animate():
    """A widget appearing already hovered should not fade in."""
    a = Anim()
    assert a.to("x", 1.0) == 1.0


def test_transition_takes_the_whole_duration():
    a = Anim()
    a.to("x", 0.0)
    a.step(0.0)
    a.to("x", 1.0)                      # retarget
    seen = []
    for _ in range(10):
        a.step(DURATION / 10.0)
        seen.append(a.to("x", 1.0))
    assert seen[0] < 0.5                # eased in, not linear
    assert seen[-1] == pytest.approx(1.0, abs=1e-6)
    assert all(b >= a_ - 1e-9 for a_, b in zip(seen, seen[1:]))


def test_retarget_midflight_starts_from_where_it_is():
    a = Anim()
    a.to("x", 0.0)
    a.step(0.0)
    a.to("x", 1.0)
    for _ in range(3):
        a.step(DURATION / 10.0)
    mid = a.to("x", 1.0)
    assert 0.0 < mid < 1.0
    a.to("x", 0.0)                      # reverse before it arrives
    a.step(DURATION / 10.0)
    back = a.to("x", 0.0)
    assert back < mid                   # heading home, from where it was


def test_store_drops_widgets_that_stopped_drawing():
    a = Anim()
    a.to("gone", 1.0)
    a.to("kept", 1.0)
    a.step(DURATION)                    # both settled
    for _ in range(130):
        a.to("kept", 1.0)
        a.step(1 / 60.0)
    assert len(a) == 1                  # O(live widgets), not unbounded


def test_settled_reports_quiescence():
    a = Anim()
    a.to("x", 0.0)
    a.step(0.0)
    a.to("x", 1.0)
    a.step(DURATION / 4.0)
    assert not a.settled()
    for _ in range(8):
        a.step(DURATION / 4.0)
    assert a.settled()


def test_mix_blends_opaque_rgba():
    assert mix((0, 0, 0, 1), (1, 1, 1, 1), 0.5) == pytest.approx((0.5,) * 3 + (1.0,))


def test_mix_from_transparent_does_not_go_through_black():
    """The bug this exists to prevent: a straight RGBA lerp from transparent
    black darkens a widget before it lightens. Premultiplied, the colour is
    constant and only alpha moves."""
    clear = (0.0, 0.0, 0.0, 0.0)
    accent = (0.15, 0.15, 0.15, 1.0)
    for f in (0.1, 0.25, 0.5, 0.75, 0.9):
        r, g, b, a = mix(clear, accent, f)
        assert (r, g, b) == pytest.approx((0.15, 0.15, 0.15))
        assert a == pytest.approx(f)


def test_mix_composited_over_a_ground_is_monotonic():
    """Composited over the sidebar, the fade must only ever lighten."""
    clear, accent, ground = (0, 0, 0, 0), (0.15, 0.15, 0.15, 1.0), 0.09
    prev = -1.0
    for i in range(21):
        r, _, _, a = mix(clear, accent, i / 20.0)
        over = r * a + ground * (1 - a)
        assert over >= prev - 1e-9
        prev = over


def test_curve_constant_is_tailwinds():
    assert STANDARD == (0.4, 0.0, 0.2, 1.0)
    assert DURATION == pytest.approx(0.15)
