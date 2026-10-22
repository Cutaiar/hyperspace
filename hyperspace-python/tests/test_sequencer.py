"""The step sequencer (sequencer.py, plan 31 §S): clock-locked stepping,
exact step times, stalls, nudges, the epoch, swing, length, mute, the
transport, pulses, the params and a hot-reload swap. Every test runs on a
deterministic clock (``Clock(now=lambda: 0.0)``) with explicit times, as
test_tempo.py does: at 120 BPM ``beat(t) = 2t``, so at the default span
of one bar (8ths, 2 steps a beat) a step is 0.25 s.
"""

import ast
import importlib.util
import random
import sys
from pathlib import Path

import pytest

from hyperspace import sequencer as seqmod
from hyperspace.params import Kind, Registry
from hyperspace.sequencer import LANES, SPANS, STEPS, Sequencer, register
from hyperspace.tempo import Clock

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
STEP_S = 0.25                               # one bar of 8ths at 120 BPM


class Log:
    """The fire callback: (lane, env, at, velocity) per call, in order."""

    def __init__(self):
        self.calls = []

    def __call__(self, lane, env, at, velocity):
        self.calls.append((lane, env, at, velocity))

    def lane(self, i=0):
        return [c for c in self.calls if c[0] == i]

    def times(self, i=0):
        return [c[2] for c in self.lane(i)]

    def indexes(self, i=0):
        """Which step fired, read off the velocity (step j has (j + 1) / 10)."""
        return [round(c[3] * 10) - 1 for c in self.lane(i)]


def rig(span="1 bar", bpm=120.0, run=True):
    clock = Clock(bpm=bpm, now=lambda: 0.0)
    seq = Sequencer()
    seq.span = SPANS.index(span)
    seq.run = run
    seq.lanes[0].steps = [(j + 1) / 10 for j in range(STEPS)]   # every step on, tagged
    return clock, seq, Log()


def frames(seq, clock, fire, times, release=None):
    for t in times:
        clock.tick(t)
        seq.step(t, clock, fire, release)


def at_60fps(t0, t1):
    n = round((t1 - t0) * 60)
    return [t0 + i / 60 for i in range(n)]


# ---------------------------------------------------------------- the grid

@pytest.mark.parametrize("span, spb", [("1/2 bar", 4.0), ("1 bar", 2.0),
                                        ("2 bars", 1.0), ("4 bars", 0.5)])
def test_steps_per_beat_for_every_span(span, spb):
    seq = Sequencer()
    seq.span = SPANS.index(span)
    assert seq.steps_per_beat == spb


def test_each_step_fires_exactly_once_at_its_exact_time_at_60fps():
    clock, seq, log = rig()
    frames(seq, clock, log, at_60fps(0.0, 4.0))
    assert len(log.calls) == 16                       # s reaches 15.9 by the last frame
    assert log.times() == pytest.approx([k * STEP_S for k in range(16)], abs=1e-12)
    assert log.indexes() == [k % 8 for k in range(16)]
    assert all(c[1] == 1 for c in log.calls)          # lane 1 fires envelope 1


def test_each_step_fires_exactly_once_at_irregular_dt():
    clock, seq, log = rig()
    rng, t, ts = random.Random(3), 0.0, []
    while t < 5.0:
        ts.append(t)
        t += rng.uniform(0.001, 0.1)
    frames(seq, clock, log, ts)
    n = seq.k_last + 1
    assert n == int(ts[-1] / STEP_S) + 1
    assert log.times() == pytest.approx([k * STEP_S for k in range(n)], abs=1e-12)
    # a step is never stamped later than the frame that fired it
    assert all(c[2] <= ts[-1] for c in log.calls)


def test_several_steps_in_one_big_frame_fire_in_order_with_their_times():
    clock, seq, log = rig()
    frames(seq, clock, log, [0.0, 1.1])
    assert log.indexes() == [0, 1, 2, 3, 4]
    assert log.times() == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])


def test_a_two_second_stall_fires_the_current_step_not_a_burst():
    clock, seq, log = rig(span="1/2 bar")             # 16ths: a step is 0.125 s
    frames(seq, clock, log, [0.0, 2.1])                # 16 steps crossed, > length
    assert log.indexes() == [0, 0]                     # step 0, then only step 16 (≡ 0)
    assert log.times()[1] == pytest.approx(2.0)
    frames(seq, clock, log, [2.13])                    # and on from there
    assert log.indexes()[-1] == 1 and log.times()[-1] == pytest.approx(2.125)


def test_set_bpm_mid_step_neither_skips_nor_doubles():
    clock, seq, log = rig()
    ts = at_60fps(0.0, 1.1)
    frames(seq, clock, log, ts)
    clock.set_bpm(150.0, 1.1)                          # between steps 4 and 5
    frames(seq, clock, log, [1.1 + i / 60 for i in range(1, 90)])
    idx = log.indexes()
    assert idx == [k % 8 for k in range(len(idx))]     # consecutive, none twice
    times = log.times()
    assert times[:5] == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])
    # step 5 is at beat 2.5: the 0.3 beat left at 1.1 s takes 0.12 s at 150
    assert times[5] == pytest.approx(1.22)
    assert [b - a for a, b in zip(times[5:], times[6:])] == pytest.approx(
        [0.2] * (len(times) - 6))


def test_a_backward_nudge_never_fires_a_step_twice():
    clock, seq, log = rig()
    frames(seq, clock, log, at_60fps(0.0, 1.05))       # steps 0–4
    clock.nudge = -0.3                                 # back 0.6 of a step
    frames(seq, clock, log, [1.05 + i / 60 for i in range(60)])
    idx = log.indexes()
    assert idx == [k % 8 for k in range(len(idx))]
    # step 4 not again; s is 7.5 by the last frame, so 5–7 after
    assert idx[5] == 5 and len(idx) == 8


def test_the_clock_trigger_fires_step_zero_that_call_at_the_trigger_time():
    clock, seq, log = rig()
    clock.nudge = 0.1                                  # the trigger folds it in
    frames(seq, clock, log, at_60fps(0.0, 1.3))
    assert log.indexes()[-1] == 5
    e = clock.epoch
    clock.trigger(1.3)
    assert clock.epoch == e + 1
    frames(seq, clock, log, [1.3])
    assert log.indexes()[-1] == 0 and log.times()[-1] == pytest.approx(1.3)
    frames(seq, clock, log, [1.3 + i / 60 for i in range(1, 20)])
    assert log.indexes()[-1] == 1 and log.times()[-1] == pytest.approx(1.55)


def test_the_epoch_starts_at_zero_and_counts_triggers():
    c = Clock(now=lambda: 0.0)
    assert c.epoch == 0
    c.trigger(1.0)
    c.trigger(2.0)
    assert c.epoch == 2 and c.beat(2.0) == 0.0


def test_swing_offsets_the_odd_steps():
    clock, seq, log = rig()
    seq.swing = 0.25
    frames(seq, clock, log, at_60fps(0.0, 2.05))
    late = 0.25 * STEP_S
    assert log.times() == pytest.approx(
        [k * STEP_S + (late if k % 2 else 0.0) for k in range(9)])


def test_a_length_under_eight_wraps():
    clock, seq, log = rig()
    seq.length = 3
    frames(seq, clock, log, at_60fps(0.0, 2.05))
    assert log.indexes() == [0, 1, 2] * 3
    assert seq.playhead == 8 % 3


def test_a_muted_lane_fires_nothing():
    clock, seq, log = rig()
    seq.lanes[1].steps = [1.0] * STEPS
    seq.lanes[1].env = 7
    frames(seq, clock, log, [0.0, 0.3])
    assert [c[:2] for c in log.calls] == [(0, 1), (1, 7), (0, 1), (1, 7)]
    seq.lanes[1].mute = True
    frames(seq, clock, log, [0.55])
    assert [c[0] for c in log.calls[4:]] == [0]
    assert seq.pulses[1] == 0.0


def test_run_off_fires_nothing_and_run_on_starts_at_the_next_boundary():
    clock, seq, log = rig(run=False)
    frames(seq, clock, log, at_60fps(0.0, 0.6))
    assert log.calls == [] and seq.playhead is None
    seq.run = True                                     # mid step 2
    frames(seq, clock, log, [0.6])
    assert log.calls == [] and seq.playhead == 2
    frames(seq, clock, log, [0.6 + i / 60 for i in range(1, 10)])
    assert log.indexes()[0] == 3 and log.times()[0] == pytest.approx(0.75)


def test_stopping_calls_release_once_per_lane_and_marks_the_edge():
    clock, seq, log = rig()
    released = []
    rel = lambda lane, env, at: released.append((lane, env, at))
    frames(seq, clock, log, [0.0, 0.1], rel)
    assert released == [] and not seq.stopped
    seq.run = False
    frames(seq, clock, log, [0.3], rel)
    assert seq.stopped and released == [(i, i + 1, 0.3) for i in range(LANES)]
    assert len(log.calls) == 1                         # step 1 at 0.25 did not fire
    frames(seq, clock, log, [0.4], rel)
    assert not seq.stopped and len(released) == LANES


def test_pulses_carry_the_velocity_on_the_firing_call_only():
    clock, seq, log = rig()
    frames(seq, clock, log, [0.0])
    assert seq.pulses == [0.1, 0.0, 0.0, 0.0, 0.0]
    frames(seq, clock, log, [0.1])
    assert seq.pulses == [0.0] * LANES

    class Router:
        def __init__(self):
            self.labels, self.rests = {}, {}

        def feed(self, scheme, values):
            self.fed = (scheme, list(values))

    frames(seq, clock, log, [0.26])
    r = Router()
    seq.publish(r)
    assert r.fed == ("seq", [0.2, 0.0, 0.0, 0.0, 0.0])
    assert r.labels["seq"] == [f"Seq {i}" for i in range(1, 6)]
    assert r.rests["seq"] == [0.0] * LANES


def test_a_span_change_starts_at_the_next_boundary():
    clock, seq, log = rig()
    frames(seq, clock, log, at_60fps(0.0, 1.1))
    n = len(log.calls)
    seq.span = SPANS.index("1/2 bar")                  # s doubles: no catch-up burst
    frames(seq, clock, log, [1.1])
    assert len(log.calls) == n
    frames(seq, clock, log, [1.1 + i / 60 for i in range(1, 10)])
    assert log.times()[n] == pytest.approx(1.125)


# ---------------------------------------------------------------- params

def registered():
    reg, clock, seq = Registry(), Clock(now=lambda: 0.0), Sequencer()
    register(reg, seq, clock)
    register(reg, seq, clock)                          # idempotent
    return reg, clock, seq


def test_register_declares_the_grid_and_the_globals():
    reg, _, _ = registered()
    ids = [p.id for p in reg.group("seq")]
    want = [f"seq.{l}.{s}" for l in range(1, 6) for s in range(1, 9)]
    want += [f"seq.{l}.{k}" for l in range(1, 6) for k in ("mute", "env")]
    want += ["seq.span", "seq.length", "seq.swing", "seq.run", "seq.step", "seq.trigger"]
    assert sorted(ids) == sorted(want) and len(ids) == 56
    assert all(reg[f"seq.{l}.{s}"].kind is Kind.TOGGLE for l in range(1, 6) for s in range(1, 9))
    assert reg["seq.span"].names == SPANS
    assert reg["seq.trigger"].kind is Kind.TRIGGER
    snap = reg.snapshot("seq")
    assert "seq.3.5" in snap and "seq.2.mute" in snap and "seq.1.env" in snap
    assert {"seq.span", "seq.length", "seq.swing"} <= set(snap)
    assert "seq.run" not in snap and "seq.step" not in snap   # the pattern is, the transport not
    assert not reg["seq.step"].modulatable and not reg["seq.1.env"].modulatable


def test_the_params_and_the_sequencer_stay_in_sync():
    reg, clock, seq = registered()
    reg["seq.2.3"].set(True)
    assert seq.lanes[1].steps[2] == 1.0 and reg["seq.2.3"].value is True
    seq.lanes[1].steps[4] = 0.6                        # a velocity a toggle press keeps
    reg["seq.2.5"].set(True)
    assert seq.lanes[1].steps[4] == 0.6
    reg["seq.2.3"].set(False)
    assert seq.lanes[1].steps[2] == 0.0
    reg["seq.4.mute"].set(True)
    assert seq.lanes[3].mute
    assert reg["seq.3.env"].value == 3
    missing = reg.restore({"seq.3.env": 9.0, "seq.length": 3.0, "seq.swing": 0.9,
                           "seq.span": 0, "seq.run": True})
    assert missing == []
    assert seq.lanes[2].env == 9 and seq.length == 3 and isinstance(seq.length, int)
    assert seq.swing == 0.5 and seq.span == 0 and seq.run is True
    assert reg["seq.step"].value == 0                  # nothing stepped yet: stopped
    seq.lanes[1].steps = [1.0] * STEPS
    log = Log()
    clock.tick(0.4)
    seq.step(0.4, clock, log)                          # 16ths at 120: s = 3.2, length 3
    assert reg["seq.step"].value == 3                  # swing 0.5: step 3 starts at 3.5
    reg["seq.trigger"].fire()                          # held: lands on the next step
    assert seq.pending
    clock.tick(0.45)
    seq.step(0.45, clock, log)
    assert seq.playhead == 0 and log.calls[-1][2] == pytest.approx(0.45)
    assert reg["seq.trigger"].get() is True            # lit on step 0
    assert clock.beat(0.45) == pytest.approx(0.9)      # the clock never moved


def test_seq_trigger_keeps_its_offset_until_the_clock_trigger_clears_it():
    clock, seq, log = rig()
    frames(seq, clock, log, [0.0, 0.1])
    seq.restart()
    frames(seq, clock, log, [0.1])
    assert log.indexes()[-1] == 0 and log.times()[-1] == pytest.approx(0.1)
    frames(seq, clock, log, [0.1 + i / 60 for i in range(1, 20)])
    assert log.times()[2] == pytest.approx(0.35)        # the grid rides 0.1 s late
    clock.trigger(0.5)
    frames(seq, clock, log, [0.5, 0.76])
    assert seq.shift == 0.0
    assert log.times()[-2:] == pytest.approx([0.5, 0.75])


# ---------------------------------------------------------------- boundary & reload

def test_the_sequencer_imports_nothing_from_the_host():
    for n in ast.walk(ast.parse((PKG / "sequencer.py").read_text())):
        if isinstance(n, ast.ImportFrom):
            assert not n.level and not (n.module or "").startswith("hyperspace")
        elif isinstance(n, ast.Import):
            assert not any(a.name.startswith("hyperspace") for a in n.names)


def test_a_hot_reload_swap_keeps_k_last_and_fires_nothing_twice(monkeypatch):
    clock, seq, log = rig()
    frames(seq, clock, log, at_60fps(0.0, 1.1))
    k = seq.k_last
    spec = importlib.util.spec_from_file_location("seq_reloaded", PKG / "sequencer.py")
    fresh = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "seq_reloaded", fresh)   # dataclasses look it up
    spec.loader.exec_module(fresh)
    seq.__class__ = fresh.Sequencer                    # what the reloader does
    assert seq.k_last == k
    frames(seq, clock, log, [1.1 + i / 60 for i in range(1, 30)])
    idx = log.indexes()
    assert idx == [j % 8 for j in range(len(idx))]


def test_an_instance_from_before_the_runtime_state_existed_still_steps():
    old = object.__new__(Sequencer)                    # only the settings, none of the state
    old.lanes = [seqmod.Lane(env=i + 1) for i in range(LANES)]
    old.lanes[0].steps = [1.0] * STEPS
    old.span, old.length, old.swing, old.run = 1, STEPS, 0.0, True
    clock, log = Clock(now=lambda: 0.0), Log()
    frames(old, clock, log, [0.1, 0.3])                # starts at the next boundary
    assert log.times() == pytest.approx([0.25])
