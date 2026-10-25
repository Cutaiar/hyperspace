"""The media transport: rate, pos latch, jog coast, loop modes (plan 32 T2)."""

import pytest

from hyperspace.media.transport import LOOPS, Transport

DT = 1 / 60


def run(t, n, rate=1.0, pos=0.0, jog=0.0, loop="loop", dt=DT):
    out = None
    for _ in range(n):
        out = t.step(dt, rate, pos, jog, loop)
    return out


def test_loops_names():
    assert LOOPS == ("loop", "pingpong", "once")


def test_native_rate_advances():
    t = Transport(10.0)
    assert run(t, 60) == pytest.approx(1.0, abs=1e-6)


def test_double_and_reverse():
    t = Transport(10.0)
    assert run(t, 60, rate=2.0) == pytest.approx(2.0, abs=1e-6)
    t = Transport(10.0)
    t.reset(0.5)
    assert run(t, 60, rate=-1.0, pos=0.5) == pytest.approx(4.0, abs=1e-6)


def test_rate_zero_holds():
    t = Transport(10.0)
    run(t, 30)
    h = t.playhead
    assert run(t, 60, rate=0.0) == pytest.approx(h)


def test_pos_latch_scrubs_then_plays_on():
    t = Transport(10.0)
    assert t.step(DT, 1.0, 0.5, 0.0, "loop") == pytest.approx(5.0)
    assert t.scrubbing
    h = t.step(DT, 1.0, 0.5, 0.0, "loop")
    assert not t.scrubbing
    assert h == pytest.approx(5.0 + DT)
    assert run(t, 59, pos=0.5) == pytest.approx(6.0, abs=1e-6)


def test_lfo_on_pos_drives_playhead():
    t = Transport(10.0)
    for i in range(1, 40):
        pos = (i * 0.013) % 1.0
        assert t.step(DT, 1.0, pos, 0.0, "loop") == pytest.approx(pos * 10.0)


def test_jog_spins_and_coasts():
    t = Transport(1000.0)
    run(t, 30, jog=1.0)
    assert t.speed > 4.0
    run(t, 180, jog=0.0)
    assert abs(t.speed - 1.0) < 0.05


def test_rate_change_is_immediate():
    t = Transport(10.0)
    t.step(DT, 1.0, 0.0, 0.0, "loop")
    t.step(DT, 3.0, 0.0, 0.0, "loop")
    assert t.speed == pytest.approx(3.0)


def test_loop_modes():
    t = Transport(10.0)
    t.reset(0.99)
    assert t.step(0.2, 1.0, 0.99, 0.0, "loop") == pytest.approx(0.1)

    t = Transport(10.0)
    t.reset(0.99)
    assert t.step(0.2, 1.0, 0.99, 0.0, "pingpong") == pytest.approx(9.9)
    assert t.step(0.2, 1.0, 0.99, 0.0, "pingpong") == pytest.approx(9.7)
    assert t.direction == -1.0

    t = Transport(10.0)
    t.reset(0.99)
    assert t.step(0.2, 1.0, 0.99, 0.0, "once") == pytest.approx(10.0)
    assert t.step(0.2, 1.0, 0.99, 0.0, "once") == pytest.approx(10.0)


def test_pingpong_reverse_off_the_start():
    t = Transport(10.0)
    assert t.step(0.5, -1.0, 0.0, 0.0, "pingpong") == pytest.approx(0.5)
    assert t.direction == -1.0
    assert t.step(0.5, -1.0, 0.0, 0.0, "pingpong") == pytest.approx(1.0)


def test_zero_duration_is_zero():
    t = Transport(0.0)
    assert t.step(DT, 1.0, 0.7, 1.0, "loop") == 0.0
    assert t.step(DT, 1.0, 0.7, 0.0, "pingpong") == 0.0


@pytest.mark.parametrize("loop", ["loop", "once"])
def test_leaving_pingpong_plays_forward(loop):
    t = Transport(10.0)
    t.reset(0.99)
    t.step(0.2, 1.0, 0.99, 0.0, "pingpong")
    t.step(0.2, 1.0, 0.99, 0.0, "pingpong")
    assert t.direction == -1.0
    before = t.playhead
    assert t.step(0.1, 1.0, 0.99, 0.0, loop) > before
