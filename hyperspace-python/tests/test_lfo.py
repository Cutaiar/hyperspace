"""The four LFOs (lfo.py): shapes, sync, the global trigger, chaining."""

import math

import pytest

from hyperspace.lfo import DIVISIONS, RANDOM, REST, SHAPES, SYNCS, LFOs, register, wave
from hyperspace.params import Kind, Registry
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.tempo import Clock
from hyperspace.tempo import register as register_tempo

DT = 1 / 60


def clock_at(bpm=120.0):
    c = Clock(bpm=bpm, now=lambda: 0.0)
    c.trigger(0.0)
    return c


def run(lfos, clock, t0, t1, dt=DT):
    """Step from t0 to t1 in dt frames; returns the last outputs."""
    t, out = t0, lfos.outputs
    while t < t1 - 1e-9:
        t += dt
        out = lfos.step(dt, t, clock)
    return out


# ---------------------------------------------------------------- shapes

@pytest.mark.parametrize("shape", range(4))
def test_shapes_swing_the_whole_range(shape):
    xs = [k / 400 for k in range(400)]
    ys = [wave(shape, x) for x in xs]
    assert min(ys) == pytest.approx(-1.0, abs=0.02) and max(ys) == pytest.approx(1.0, abs=0.02)
    assert all(-1.0 <= y <= 1.0 for y in ys)


def test_output_rests_at_half_at_depth_zero_and_swings_with_depth():
    lfos, c = LFOs(), clock_at()
    lf = lfos[0]
    lf.depth = 0.0
    assert all(lfos.step(DT, k * DT, c)[0] == REST for k in range(1, 121))
    lf.depth = 1.0
    lf.rate = 1.0
    us = [lfos.step(DT, k * DT, c)[0] for k in range(1, 61)]
    assert min(us) == pytest.approx(0.0, abs=0.01) and max(us) == pytest.approx(1.0, abs=0.01)
    lf.depth = 0.5
    us = [lfos.step(DT, k * DT, c)[0] for k in range(61, 121)]
    assert min(us) == pytest.approx(0.25, abs=0.01) and max(us) == pytest.approx(0.75, abs=0.01)


def test_hz_mode_integrates_rate_dt():
    lfos, c = LFOs(), clock_at()
    lf = lfos[0]
    lf.shape, lf.rate = SHAPES.index("saw"), 2.0
    lfos.step(0.125, 0.125, c)                  # a quarter cycle in: saw at −0.5
    assert lf.x == pytest.approx(0.25) and lf.out == pytest.approx(REST - 0.25)
    c.set_bpm(300.0)                            # the clock means nothing to it
    lfos.step(0.125, 0.25, c)
    assert lf.x == pytest.approx(0.5)


def test_random_holds_within_a_cycle_and_changes_between():
    lfos, c = LFOs(seed=7), clock_at()
    lf = lfos[0]
    lf.shape, lf.rate = RANDOM, 1.0
    # in Hz the phase integrates rate · dt, so cycles are counted in steps
    first = [lfos.step(DT, k * DT, c)[0] for k in range(1, 58)]   # steps 1–57: cycle 0
    assert len(set(first)) == 1 and 0.0 <= first[0] <= 1.0
    for k in range(58, 62):                                     # across the boundary
        lfos.step(DT, k * DT, c)
    second = [lfos.step(DT, k * DT, c)[0] for k in range(62, 118)]  # steps 62–117: cycle 1
    assert len(set(second)) == 1 and second[0] != first[0]


# ---------------------------------------------------------------- sync

def test_divisions_land_phase_zero_on_the_downbeat():
    lfos, c = LFOs(), clock_at(120.0)
    for i, name in enumerate(("1 bar", "1/4", "1/16", "4 bars")):
        lfos[i].sync = SYNCS.index(name)
        lfos[i].shape = SHAPES.index("saw")
    lfos.step(DT, 0.0, c)
    assert all(lf.x == 0.0 for lf in lfos.lfos)
    lfos.step(DT, 1.0, c)                      # two beats at 120: half a bar
    assert lfos[0].x == pytest.approx(0.5)
    assert lfos[1].x == pytest.approx(0.0)      # a quarter: whole cycles
    assert lfos[2].x == pytest.approx(0.0)
    assert lfos[3].x == pytest.approx(2 / 16)   # 2 of 16 beats
    lfos.step(DT, 2.0, c)                      # a bar: the bar wave is back at 0
    assert lfos[0].x == pytest.approx(0.0)
    assert DIVISIONS["1 bar"] * 4 == 1.0        # four beats to the bar


def test_a_tap_does_not_move_a_running_synced_lfo_but_the_trigger_does():
    lfos, c = LFOs(), clock_at(120.0)
    bar, hz = lfos[0], lfos[1]
    bar.sync = SYNCS.index("1 bar")
    bar.shape = hz.shape = SHAPES.index("saw")
    hz.rate = 0.7
    run(lfos, c, 0.0, 3.3)                      # mid-bar, mid-cycle
    x_bar, x_hz = bar.x, hz.x
    assert 0.0 < x_bar < 1.0
    # a burst of taps at a new tempo: the readout changes, the wave does not
    # jump — it runs on at the old rate until the second tap sets the new one
    t2 = 3.3 + 60 / 140
    for k in range(3):
        c.tap(3.3 + k * 60 / 140)
    t = 3.3 + 2 * 60 / 140
    assert c.bpm == pytest.approx(140.0)
    expected = (x_bar + (t2 - 3.3) * 120 / 60 / 4 + (t - t2) * 140 / 60 / 4) % 1.0
    lfos.step(DT, t, c)
    assert bar.x == pytest.approx(expected, abs=1e-9)
    assert bar.x != pytest.approx(0.0, abs=0.05)
    # the trigger: every synced LFO reads phase 0 that frame; the Hz one does not
    c.tick(t + 0.4)
    lfos.trigger(c)
    lfos.step(DT, t + 0.4, c)
    assert bar.x == 0.0 and bar.out == pytest.approx(0.0)  # saw at −1
    assert hz.x == pytest.approx((x_hz + 2 * DT * 0.7) % 1.0, abs=1e-6)   # two more steps
    assert hz.x != pytest.approx(0.0, abs=0.05)


def test_the_trigger_realigns_every_synced_lfo_together():
    lfos, c = LFOs(), clock_at(100.0)
    for i in range(4):
        lfos[i].sync = i + 1                    # 4 bars … 1/2
        lfos[i].shape = SHAPES.index("saw")
    run(lfos, c, 0.0, 5.37)
    assert len({round(lf.x, 6) for lf in lfos.lfos}) > 1
    lfos.reset(2, c, 5.37)                      # one of them restarted on its own
    lfos.step(DT, 5.37, c)
    assert lfos[2].x == pytest.approx(0.0, abs=1e-9)
    lfos.trigger(c, 6.0)
    lfos.step(DT, 6.0, c)
    assert all(lf.x == 0.0 for lf in lfos.lfos)
    assert c.t0 == 6.0


def test_the_trigger_lands_phase_zero_whatever_the_nudge_and_nudge_then_moves_it():
    lfos, c = LFOs(), clock_at(120.0)
    c.nudge = 0.25
    for i in range(3):
        lfos[i].sync = SYNCS.index(("4 bars", "1 bar", "1/16")[i])
        lfos[i].shape = SHAPES.index("saw")
    lfos[3].sync, lfos[3].phase = SYNCS.index("1 bar"), 0.3
    run(lfos, c, 0.0, 2.7)
    c.tick(2.7)
    lfos.trigger(c)
    lfos.step(DT, 2.7, c)
    assert all(lf.x == pytest.approx(0.0, abs=1e-12) for lf in lfos.lfos[:3])
    assert lfos[3].x == pytest.approx(0.3)                    # + its own phase
    assert c.nudge == 0.25
    c.nudge = 0.35                                            # turned afterwards: it moves
    lfos.step(DT, 2.7, c)
    assert lfos[1].x == pytest.approx(0.1 / 4)                # a tenth of a beat, in bars
    assert lfos[2].x == pytest.approx((0.1 * 4) % 1.0)


def test_a_trigger_after_this_frames_step_lands_phase_zero_on_the_next_step():
    """The panel's chip and a performer-fired trigger run after `lfos.step`
    (audit B6): the trigger is held and applied at the next step's own t,
    so the first frame the LFOs see it reads exactly 0 — not dt·bpm/60·ratio."""
    lfos, c = LFOs(), clock_at(120.0)
    bar, hz = lfos[0], lfos[1]
    bar.sync, bar.shape = SYNCS.index("1/16"), SHAPES.index("saw")   # the coarsest phase
    hz.rate = 0.7
    run(lfos, c, 0.0, 3.3)
    c.tick(3.3)
    lfos.step(DT, 3.3, c)                        # this frame's step has run…
    x_hz = hz.x
    lfos.trigger(c)                              # …then the chip fires (t defaults to clock.t)
    assert lfos.pending and c.t0 == 0.0          # held; the clock has not moved yet
    lfos.step(DT, 3.3 + DT, c)                   # next frame
    assert c.t0 == pytest.approx(3.3 + DT) and bar.x == 0.0 and not lfos.pending
    assert hz.x == pytest.approx((x_hz + DT * 0.7) % 1.0)          # Hz untouched
    # fired before the step (a key): applied at once, phase 0 that frame
    c.tick(4.0)
    lfos.trigger(c)
    assert not lfos.pending and c.t0 == 4.0
    lfos.step(DT, 4.0, c)
    assert bar.x == 0.0


def test_a_per_lfo_reset_after_the_step_lands_phase_zero_next_step_in_either_mode():
    lfos, c = LFOs(), clock_at(120.0)
    hz, bar = lfos[0], lfos[1]
    hz.rate, hz.shape = 3.0, SHAPES.index("saw")
    bar.sync, bar.shape = SYNCS.index("1/16"), SHAPES.index("saw")
    run(lfos, c, 0.0, 0.7)
    c.tick(0.7)
    lfos.step(DT, 0.7, c)
    lfos.reset(0, c)                             # after the step: held
    lfos.reset(1, c)
    assert hz.pending and bar.pending
    lfos.step(DT, 0.7 + DT, c)
    assert hz.x == 0.0 and bar.x == pytest.approx(0.0, abs=1e-9)
    assert not hz.pending and not bar.pending and c.t0 == 0.0     # the clock never moved
    # the global trigger supersedes a held reset on a synced LFO
    lfos.step(DT, 0.8, c)
    lfos.reset(1, c, 0.8)
    lfos.trigger(c, 0.8)
    assert lfos.pending
    lfos.step(DT, 0.8 + DT, c)
    assert c.t0 == pytest.approx(0.8 + DT) and bar.x == 0.0 and bar.shift == 0.0
    assert not lfos.pending and not bar.pending


def test_switching_sync_carries_the_phase_both_ways():
    """Audit B7: Hz → division and back continue from the wave's position."""
    lfos, c = LFOs(), clock_at(120.0)
    lf = lfos[0]
    lf.shape, lf.rate, lf.phase = SHAPES.index("saw"), 0.9, 0.2
    run(lfos, c, 0.0, 1.3)                       # Hz: mid-cycle somewhere
    x = lf.x
    assert 0.05 < x < 0.95
    lf.sync = SYNCS.index("1 bar")               # to a division: no jump
    lfos.step(DT, 1.3 + DT, c)
    assert lf.x == pytest.approx(x, abs=1e-9)
    lfos.step(DT, 1.3 + 2 * DT, c)               # …and it now runs at the bar's rate
    assert lf.x == pytest.approx((x + DT * 120 / 60 / 4) % 1.0, abs=1e-9)
    run(lfos, c, 1.3 + 2 * DT, 2.9)
    x = lf.x
    lf.sync = 0                                  # back to Hz: continuous, at the rate
    lfos.step(DT, 2.9 + DT, c)
    assert lf.x == pytest.approx((x + DT * 0.9) % 1.0, abs=1e-9)
    # a random LFO keeps its held value across the switch
    rnd = lfos[1]
    rnd.shape, rnd.rate = RANDOM, 0.2
    run(lfos, c, 2.9 + DT, 3.5)
    held = rnd.hold
    rnd.sync = SYNCS.index("4 bars")
    lfos.step(DT, 3.5 + DT, c)
    assert rnd.hold == held


def test_phase_offset_rides_on_top_in_both_modes():
    lfos, c = LFOs(), clock_at()
    lfos[0].sync, lfos[0].phase = SYNCS.index("1 bar"), 0.25
    lfos[1].phase = 0.25
    lfos.trigger(c, 0.0)
    lfos.step(DT, 0.0, c)
    assert lfos[0].x == pytest.approx(0.25)
    lfos.reset(1, c, 0.0)
    lfos.step(0.0, 0.0, c)
    assert lfos[1].x == pytest.approx(0.25)


def test_per_lfo_reset_in_either_mode():
    lfos, c = LFOs(seed=3), clock_at()
    hz, bar = lfos[0], lfos[1]
    hz.rate, hz.shape = 1.0, SHAPES.index("saw")
    bar.sync, bar.shape = SYNCS.index("1 bar"), SHAPES.index("saw")
    run(lfos, c, 0.0, 0.7)
    assert hz.x > 0.5 and bar.x > 0.3
    lfos.reset(0, c, 0.7)
    lfos.step(0.0, 0.7, c)
    assert hz.x == pytest.approx(0.0) and bar.x > 0.3   # the other stays
    lfos.reset(1, c, 0.7)
    lfos.step(0.0, 0.7, c)
    assert bar.x == pytest.approx(0.0, abs=1e-9)
    assert c.t0 == 0.0                          # the clock never moved
    # a random LFO's reset draws a fresh value
    lfos[2].shape = RANDOM
    lfos.step(DT, 0.71, c)
    held = lfos[2].hold
    draws = set()
    for _ in range(8):
        lfos.reset(2, c)
        lfos.step(DT, 0.72, c)
        draws.add(lfos[2].hold)
    assert draws - {held}


# ---------------------------------------------------------------- params

def rig():
    reg = Registry()
    c = Clock(now=lambda: 0.0)
    lfos = LFOs(seed=1)
    register_tempo(reg, c)
    register(reg, lfos, c)
    register(reg, lfos, c)                      # idempotent
    return reg, c, lfos


def test_register_declares_every_knob_ownable_and_persistent():
    reg, c, _ = rig()
    ids = [p.id for p in reg.group("lfo")]
    assert ids[0] == "lfo.trigger"
    for n in range(1, 5):
        for k in ("shape", "rate", "sync", "depth", "phase", "reset"):
            assert f"lfo.{n}.{k}" in reg
    knobs = [p for p in reg.group("lfo") if p.kind is not Kind.TRIGGER]
    assert len(knobs) == 20 and all(p.modulatable and p.persist for p in knobs)
    triggers = [p for p in reg.group("lfo") if p.kind is Kind.TRIGGER]
    assert len(triggers) == 5 and all(p.modulatable for p in triggers)
    rate = reg["lfo.1.rate"]
    assert rate.log and (rate.lo, rate.hi) == (0.01, 20.0)
    assert reg["lfo.1.shape"].names == SHAPES and reg["lfo.1.sync"].names == SYNCS
    assert "lfo.1.reset" not in reg.snapshot("lfo") and "lfo.1.depth" in reg.snapshot("lfo")
    # the trigger carries the beat light the METRONOME LED shows
    trig = reg["lfo.trigger"]
    c.tick(0.0)
    assert trig.get() is True
    c.tick(0.25)
    assert trig.get() is False


def test_the_trigger_param_moves_the_clock_and_the_synced_lfos():
    reg, c, lfos = rig()
    reg["lfo.1.sync"].set(SYNCS.index("1 bar"))
    reg["lfo.2.rate"].set_value(0.5)
    c.tick(4.0)
    run(lfos, c, 0.0, 3.3)
    lfos.step(DT, 3.3, c)
    assert lfos[0].x > 0.1 and lfos[1].x > 0.1
    c.tick(3.3)
    reg["lfo.trigger"].fire()
    lfos.step(DT, 3.3, c)
    assert c.t0 == 3.3 and lfos[0].x == 0.0 and lfos[1].x > 0.1
    reg["lfo.2.reset"].fire()
    lfos.step(0.0, 3.3, c)
    assert lfos[1].x == 0.0


def test_an_lfo_owning_another_lfos_depth_changes_its_output_next_frame():
    """The chain: LFO 1 pushes lfo.2.depth, centred on the LFO rest of 0.5
    the router reads from `rests` (the row names none). One frame of lag,
    no recursion: the depth lands in apply(), the next step reads it."""
    reg, c, lfos = rig()
    one, two = lfos[0], lfos[1]
    one.shape, one.rate = SHAPES.index("sine"), 1.0    # a quarter cycle per frame below
    two.depth = 0.0                                     # silent on its own
    two.shape, two.rate = SHAPES.index("square"), 1.0
    table = Bindings([Binding("lfo:0", "lfo.2.depth", "push", 1.0)])
    router = Router(reg, table)
    depth = reg["lfo.2.depth"]
    dt = 0.25

    def frame(t):
        lfos.step(dt, t, c)
        lfos.publish(router)
        router.modulate(None)
        reg.apply()

    assert table.owner("lfo.2.depth") is table.bindings[0]
    frame(0.25)
    assert lfos.outputs[0] == pytest.approx(1.0)          # sine at its crest
    assert lfos.outputs[1] == pytest.approx(REST)          # LFO 2 stepped at depth 0
    assert depth.modulated and depth.base == 0.0
    assert two.depth == pytest.approx(0.5)                 # 1.0 · (1.0 − rest 0.5)
    assert router.rests["lfo"] == [REST] * 4 and router.labels["lfo"][1] == "LFO 2"
    frame(0.5)                                             # the next frame: it swings
    assert lfos.outputs[1] == pytest.approx(REST - 0.25)   # square low at depth 0.5
    assert lfos.outputs[0] == pytest.approx(REST, abs=1e-9)   # LFO 1 at its rest…
    assert two.depth == pytest.approx(0.0, abs=1e-9)       # …pushes nothing: a no-op
    frame(0.75)
    assert lfos.outputs[1] == pytest.approx(REST)          # depth 0 read a frame late
    assert two.depth == 0.0                                # the trough clamps at 0
    # the source lets go: the base comes back, and the output with it
    table.bindings.clear()
    frame(1.0)
    assert not depth.modulated and two.depth == 0.0


def test_lfo_source_is_fed_as_floats_in_range():
    reg, c, lfos = rig()
    router = Router(reg, Bindings([]))
    for k in range(1, 30):
        lfos.step(DT, k * DT, c)
        lfos.publish(router)
        vec = router.feeds["lfo"]
        assert len(vec) == 4 and all(0.0 <= v <= 1.0 and not math.isnan(v) for v in vec)
