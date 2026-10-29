"""The spring feel's curve (ui_spring): motion.spring's own step response
across a time axis fitted to the spring, and a playhead that loops it."""

import math

import pytest

from hyperspace import motion
from hyperspace.ui_spring import (PAUSE, RING_CYCLES, WINDOW_MIN, curve, playhead,
                                  position, settle, window)


def test_the_curve_is_the_feels_own_step_response():
    hz, damp = 2.0, 0.5
    assert position(0.0, hz, damp) == 0.0
    x, _ = motion.spring(0.0, 0.0, 1.0, 0.2, hz, damp)
    assert position(0.2, hz, damp) == pytest.approx(x)
    pts = curve(hz, damp, 16)
    assert len(pts) == 17 and pts[0] == (0.0, 0.0)
    assert pts[-1][0] == pytest.approx(window(hz, damp))


def test_below_critical_it_overshoots_and_at_or_above_it_does_not():
    assert max(y for _, y in curve(1.5, 0.3)) > 1.2
    assert max(y for _, y in curve(1.5, 1.0)) <= 1.0 + 1e-9
    assert max(y for _, y in curve(1.5, 2.5)) <= 1.0 + 1e-9
    assert abs(curve(1.5, 1.0)[-1][1] - 1.0) < 0.03       # settled by the axis' end


def test_the_time_axis_fits_the_spring():
    assert window(4.0, 1.0) < window(1.0, 1.0)            # tighter settles sooner
    assert window(2.0, 3.0) > window(2.0, 1.0)            # overdamped creeps
    assert math.isinf(settle(2.0, 0.0))
    assert window(2.0, 0.0) == pytest.approx(RING_CYCLES / 2.0)   # rings: a few cycles
    assert window(motion.HZ_MAX, 1.0) >= WINDOW_MIN


def test_the_playhead_sweeps_then_rests_then_sweeps_again():
    hz, damp = 2.0, 1.0
    w = window(hz, damp)
    assert playhead(0.0, hz, damp) == 0.0
    assert playhead(w / 2, hz, damp) == pytest.approx(w / 2)
    assert playhead(w + PAUSE / 2, hz, damp) == pytest.approx(w)
    assert playhead(w + PAUSE + 0.01, hz, damp) == pytest.approx(0.01)
