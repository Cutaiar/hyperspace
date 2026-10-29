"""The spring feel's picture (ui_spring): the pluck is motion.spring's
own response, held then released, and the coil spans wall to mass."""

import math

import pytest

from hyperspace import motion, ui_spring
from hyperspace.ui_spring import HOLD, PERIOD_MAX, PERIOD_MIN, coil, period, pose, settle


def test_the_mass_is_held_out_then_released_along_the_spring():
    hz, damp = 2.0, 0.5
    assert pose(0.0, hz, damp) == 1.0
    assert pose(HOLD * 0.9, hz, damp) == 1.0
    s = 0.2
    x, _ = motion.spring(1.0, 0.0, 0.0, s, hz, damp)
    assert pose(HOLD + s, hz, damp) == pytest.approx(x)


def test_below_critical_it_rings_past_rest_and_at_critical_it_does_not():
    ts = [HOLD + i * 0.01 for i in range(1, 300)]
    assert min(pose(t, 1.5, 0.3) for t in ts) < -0.2
    assert min(pose(t, 1.5, 1.0) for t in ts) > -1e-6
    assert min(pose(t, 1.5, 2.5) for t in ts) > -1e-6


def test_the_pluck_repeats_within_its_bounds():
    for hz, damp in ((0.1, 0.0), (0.1, 3.0), (12.0, 1.0), (2.0, 0.6)):
        p = period(hz, damp)
        assert PERIOD_MIN <= p <= PERIOD_MAX
        assert pose(0.3, hz, damp) == pytest.approx(pose(0.3 + p, hz, damp))
    assert math.isinf(settle(2.0, 0.0))
    assert settle(4.0, 1.0) < settle(1.0, 1.0)        # tighter settles sooner
    assert settle(2.0, 3.0) > settle(2.0, 1.0)        # overdamped creeps


def test_the_coil_runs_from_the_wall_to_the_mass_within_its_amplitude():
    pts = coil(10.0, 90.0, 20.0, 5.0)
    assert pts[0] == (10.0, 20.0) and pts[-1] == (90.0, 20.0)
    assert all(15.0 - 1e-9 <= y <= 25.0 + 1e-9 for _, y in pts)
    assert len(pts) > ui_spring.TURNS * ui_spring.COIL_SAMPLES
