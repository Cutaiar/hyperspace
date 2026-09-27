"""The tap-tempo clock (tempo.py): burst math, the downbeat, the trigger."""

import pytest

from hyperspace.params import Kind, Registry
from hyperspace.tempo import GAP, Clock, register


def taps(clock, bpm, n, start=0.0):
    """n taps at `bpm` from `start`; returns the time of the last one."""
    step = 60.0 / bpm
    for k in range(n):
        clock.tap(start + k * step)
    return start + (n - 1) * step


# ---------------------------------------------------------------- taps

def test_three_taps_at_140_read_140():
    c = Clock(now=lambda: 0.0)
    taps(c, 140, 3)
    assert c.bpm == pytest.approx(140.0)


def test_one_tap_sets_nothing_and_a_gap_restarts_the_burst():
    c = Clock(bpm=120, now=lambda: 0.0)
    c.tap(0.0)
    assert c.bpm == 120.0                       # one tap is no interval
    c.tap(0.0)                                  # two in one frame: not a tempo
    assert c.bpm == 120.0
    t = taps(c, 90, 4, start=GAP + 0.5)         # a new burst of four
    assert c.bpm == pytest.approx(90.0) and len(c.taps) == 4
    c.tap(t + GAP + 0.1)                        # too late: a new burst of one
    assert len(c.taps) == 1 and c.bpm == pytest.approx(90.0)
    taps(c, 128, 2, start=t + GAP + 0.1 + 60 / 128)   # two more: three at 128
    assert len(c.taps) == 3 and c.bpm == pytest.approx(128.0)


def test_bpm_follows_the_last_eight_taps():
    """A tempo change registers within a bar of tapping, not after the
    whole burst has been averaged against it."""
    c = Clock(now=lambda: 0.0)
    t = taps(c, 120, 60)                        # half a minute at 120
    assert c.bpm == pytest.approx(120.0)
    taps(c, 128, 8, start=t + 60 / 128)         # eight more, at 128, no gap
    assert len(c.taps) == 68
    assert c.bpm == pytest.approx(128.0)
    taps(c, 128, 3, start=t + 60 / 128 + 8 * 60 / 128)
    assert c.bpm == pytest.approx(128.0)


def test_a_fresh_clocks_first_tap_folds_the_nudge_like_the_trigger():
    c = Clock(now=lambda: 0.0)
    c.nudge = 0.25
    taps(c, 120, 4, start=10.0)
    assert c.beat(10.0) == pytest.approx(0.0, abs=1e-12)        # the tap is the "one"
    assert c.phase(10.0, 0.25) == pytest.approx(0.0, abs=1e-12)
    assert c.t0 == pytest.approx(10.0 + 0.25 * 0.5)
    c.nudge = 0.0                                                # turned later: it moves
    assert c.beat(10.0) == pytest.approx(-0.25)


def test_bpm_is_clamped():
    c = Clock(now=lambda: 0.0)
    c.tap(0.0)
    c.tap(0.05)                                 # 1200 BPM
    assert c.bpm == 300.0
    c = Clock(now=lambda: 0.0)
    c.tap(0.0)
    c.tap(1.9)                                  # ~31.6 BPM, still one burst
    assert c.bpm == pytest.approx(60 / 1.9)


# ---------------------------------------------------------------- the beat

def test_a_fresh_clock_lines_up_on_its_first_tap():
    """Never triggered: the burst's first tap is the downbeat, so a bar-long
    division reads phase 0 there and on every bar after."""
    c = Clock(now=lambda: 0.0)
    taps(c, 120, 4, start=10.0)
    assert c.t0 == 10.0 and not hasattr(c, "now")
    assert c.phase(10.0, 0.25) == pytest.approx(0.0)
    assert c.phase(12.0, 0.25) == pytest.approx(0.0)          # one bar later
    assert c.phase(11.0, 0.25) == pytest.approx(0.5)          # half a bar
    assert c.bar(10.5) == pytest.approx(1.0)
    assert c.beat(10.5) == pytest.approx(1.0)


def test_trigger_lands_beat_zero_whatever_the_nudge():
    """The nudge is folded into where the downbeat goes, not zeroed: the
    trigger is the "one" exactly, and a nudge turned afterwards still moves
    the grid."""
    c = Clock(now=lambda: 0.0)
    c.nudge = 0.2
    c.trigger(5.0)
    assert c.nudge == 0.2 and c.t0 == pytest.approx(5.0 + 0.2 * 0.5)
    assert c.beat(5.0) == pytest.approx(0.0, abs=1e-12)
    for ratio in (1 / 16, 0.25, 1.0, 4.0):
        assert c.phase(5.0, ratio) == pytest.approx(0.0, abs=1e-12)
    assert c.phase(5.5, 1.0) == pytest.approx(0.0)          # the next beat, on the grid
    c.nudge = 0.0                                             # turned later: the grid shifts
    assert c.beat(5.0) == pytest.approx(-0.2)
    c.nudge = 0.45
    assert c.beat(5.0) == pytest.approx(0.25)
    c.trigger(5.0)                                            # and re-triggering re-lands it
    assert c.beat(5.0) == pytest.approx(0.0, abs=1e-12)


def test_a_tap_after_the_trigger_keeps_the_beat_continuous():
    """Re-tapping mid-set changes the rate, never where the wave is now."""
    c = Clock(now=lambda: 0.0)
    taps(c, 120, 3)
    c.trigger(10.0)
    t1 = 20.0 + 60 / 140                        # the second tap: where 140 takes over
    before = c.beat(t1)
    taps(c, 140, 3, start=20.0)
    assert c.bpm == pytest.approx(140.0)
    # the beat at that instant is what the old tempo had brought it to;
    # from there it runs at the new one
    assert c.beat(t1) == pytest.approx(before, rel=1e-9)
    assert c.beat(t1 + 1.0) == pytest.approx(before + 140 / 60)
    assert c.t0 != 10.0                          # re-anchored, not the tap


@pytest.mark.parametrize("nudge", [0.0, 0.25, -0.4])
def test_a_retap_after_the_trigger_is_continuous_with_any_nudge(nudge):
    c = Clock(now=lambda: 0.0)
    c.nudge = nudge
    c.trigger(10.0)
    assert c.beat(10.0) == pytest.approx(0.0, abs=1e-12)
    t1 = 20.0 + 60 / 150
    before = c.beat(t1)
    taps(c, 150, 3, start=20.0)
    assert c.bpm == pytest.approx(150.0) and c.nudge == nudge
    assert c.beat(t1) == pytest.approx(before, rel=1e-9)
    assert c.beat(t1 + 2.0) == pytest.approx(before + 2 * 150 / 60)


def test_set_bpm_from_the_panel_is_continuous_too():
    c = Clock(now=lambda: 0.0)
    c.trigger(0.0)
    b = c.beat(7.3)
    c.set_bpm(90.0, 7.3)
    assert c.beat(7.3) == pytest.approx(b)
    c.set_bpm(90.0, 8.0)                        # the same tempo: nothing moves
    assert c.beat(8.0) == pytest.approx(b + 0.7 * 90 / 60)


def test_tick_is_the_default_time():
    c = Clock(now=lambda: 3.0)
    assert c.t == 3.0
    c.tick(4.0)
    c.trigger()
    assert c.t0 == 4.0
    c.tick(4.25)                                # 120 BPM: half a beat later
    assert c.beat() == pytest.approx(0.5) and not c.on_beat()
    c.tick(4.5)
    assert c.on_beat()


# ---------------------------------------------------------------- params

def test_register_declares_the_tempo_group():
    reg = Registry()
    c = Clock(now=lambda: 0.0)
    register(reg, c)
    register(reg, c)                            # idempotent, like hands.register
    bpm, tap, nudge = reg["tempo.bpm"], reg["tempo.tap"], reg["tempo.nudge"]
    assert bpm.kind is Kind.CONTINUOUS and bpm.persist and bpm.lo == 20 and bpm.hi == 300
    assert tap.kind is Kind.TRIGGER and tap.modulatable
    assert nudge.kind is Kind.CONTINUOUS and nudge.persist and (nudge.lo, nudge.hi) == (-0.5, 0.5)
    assert {p.group for p in reg.group("tempo")} == {"tempo"}
    bpm.set_value(100.0)
    assert c.bpm == 100.0 and bpm.text() == "100.0 BPM"
    nudge.step(1)                                # the APC's NUDGE +: a hundredth
    assert c.nudge == pytest.approx(0.01)
    c.tick(1.0)
    tap.fire()
    c.tick(1.5)
    tap.fire()
    assert c.bpm == pytest.approx(120.0)
    assert reg.snapshot("tempo") == {"tempo.bpm": 120.0, "tempo.nudge": pytest.approx(0.01)}
