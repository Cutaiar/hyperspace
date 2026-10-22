"""The envelope voice (plan 31 §E): stage timing, curves, modes, beats,
retrigger, velocity, exact sub-frame fires, event order, the late-fire
hold, and its params on a real registry. Every time is handed in, so
nothing here depends on the wall clock."""

import pytest

from hyperspace import envelope as E
from hyperspace.envelope import Envelope
from hyperspace.params import Kind, Registry
from hyperspace.tempo import Clock

approx = pytest.approx


def env(**kw):
    """Linear, round numbers: attack 1, hold 0.5, decay 1, sustain 0.5, release 2."""
    base = {"attack": 1.0, "hold": 0.5, "decay": 1.0, "sustain": 0.5, "rel": 2.0, "curve": 0.0}
    base.update(kw)
    return Envelope(**base)


def run(e, ts, clock=None):
    return [e.step(t, clock) for t in ts]


# ---- stage timing ----

@pytest.mark.parametrize("t, level, stage", [
    (0.0, 0.0, E.ATTACK), (0.5, 0.5, E.ATTACK), (1.0, 1.0, E.HOLD), (1.25, 1.0, E.HOLD),
    (1.5, 1.0, E.DECAY), (2.0, 0.75, E.DECAY), (2.5, 0.5, E.SUSTAIN), (3.9, 0.5, E.SUSTAIN),
    (4.0, 0.5, E.RELEASE), (5.0, 0.25, E.RELEASE), (6.0, 0.0, E.IDLE), (9.0, 0.0, E.IDLE),
])
def test_the_stages_land_on_time(t, level, stage):
    e = env()
    e.fire(at=0.0)
    e.release(at=4.0)
    assert e.step(t) == approx(level)
    assert e.stage == stage


def test_stepping_frame_by_frame_agrees_with_one_jump():
    a, b = env(), env()
    for x in (a, b):
        x.fire(at=0.0)
        x.release(at=4.0)
    run(a, [k / 60 for k in range(300)])
    assert a.step(5.0) == approx(b.step(5.0))


def test_hold_zero_is_an_adsr():
    e = env(hold=0.0)
    assert Envelope().hold == 0.0                  # the default reads as ADSR
    e.fire(at=0.0)
    assert e.step(1.0) == approx(1.0) and e.stage == E.DECAY
    assert e.step(1.5) == approx(0.75)
    assert e.step(2.0) == approx(0.5) and e.stage == E.SUSTAIN


def test_the_hold_knobs_bottom_is_zero():
    """The log range stops at 1 ms; on hold that bottom is 0, not 1 ms."""
    e = env(hold=E.T_LO)
    e.fire(at=0.0)
    assert e.step(1.0005) < 1.0 and e.stage == E.DECAY


def test_a_rest_voice_reads_rest():
    e = Envelope()
    assert run(e, [0.0, 1.0, 2.0]) == [E.REST] * 3 == [0.0] * 3


# ---- curves ----

@pytest.mark.parametrize("curve, g", [(-1.0, 0.5 ** 0.25), (0.0, 0.5), (1.0, 0.5 ** 4)])
def test_one_curve_shapes_every_stage(curve, g):
    e = env(curve=curve)
    e.fire(at=0.0)
    e.release(at=4.0)
    assert e.step(0.5) == approx(g)                       # attack, halfway
    assert e.step(2.0) == approx(1.0 - 0.5 * g)           # decay 1 → 0.5, halfway
    assert e.step(5.0) == approx(0.5 * (1.0 - g))         # release 0.5 → 0, halfway
    assert E.shape(0.0, curve) == 0.0 and E.shape(1.0, curve) == 1.0


def test_negative_curve_is_fast_out_of_the_corner():
    assert E.shape(0.1, -1.0) > E.shape(0.1, 0.0) > E.shape(0.1, 1.0)


# ---- modes ----

def test_one_shot_releases_at_the_end_of_decay_and_gate_sustains():
    g, o = env(rel=1.0), env(rel=1.0, mode=E.ONE_SHOT)
    for x in (g, o):
        x.fire(at=0.0)
    assert g.step(3.0) == approx(0.5) and g.stage == E.SUSTAIN
    assert o.step(3.0) == approx(0.25) and o.stage == E.RELEASE   # released at 2.5
    assert o.step(3.5) == 0.0 and o.stage == E.IDLE


def test_one_shot_ignores_release_and_gate_length():
    o = env(mode=E.ONE_SHOT)
    o.fire(at=0.0, gate=0.1)
    o.release(at=0.2)
    assert o.step(1.25) == approx(1.0) and o.stage == E.HOLD


def test_gate_length_releases_on_its_own():
    e = env(rel=1.0)
    e.fire(at=0.0, gate=3.0)
    assert e.step(2.9) == approx(0.5)
    assert e.step(3.5) == approx(0.25) and e.stage == E.RELEASE


def test_gate_length_inside_one_step():
    e = env(rel=1.0)
    e.fire(at=0.0, gate=0.5)                  # released mid-attack, at 0.5
    assert e.step(1.0) == approx(0.25)


def test_a_later_fire_outlives_the_earlier_notes_gate():
    e = env()
    e.fire(at=0.0, gate=0.5)
    e.fire(at=0.4)                            # open gate: the 0.5 release was note 1's
    assert e.step(3.5) == approx(0.5) and e.stage == E.SUSTAIN


# ---- beats ----

def test_beats_follow_a_bpm_change_mid_stage():
    clock = Clock(bpm=120.0, now=lambda: 0.0)
    e = env(sync=E.BEATS, attack=2.0)          # 2 beats: 1 s at 120
    e.fire(at=0.0)
    assert e.step(0.5, clock) == approx(0.5)
    clock.set_bpm(60.0, 0.5)                   # now 2 s a stage: the rate halves
    assert e.step(1.0, clock) == approx(0.75)  # from where it was, no jump
    assert e.step(1.5, clock) == approx(1.0) and e.stage == E.HOLD


def test_beats_ignore_the_downbeat():
    """A trigger or a nudge moves the downbeat, never an envelope mid-stage."""
    clock = Clock(bpm=120.0, now=lambda: 0.0)
    e = env(sync=E.BEATS, attack=2.0)
    e.fire(at=0.0)
    e.step(0.25, clock)
    clock.trigger(0.3)
    clock.nudge = 0.4
    assert e.step(0.5, clock) == approx(0.5)


# ---- retrigger ----

@pytest.mark.parametrize("retrig, level", [(E.LEGATO, 0.75), (E.RESET, 0.5)])
def test_legato_attacks_from_the_level_and_reset_from_zero(retrig, level):
    e = env(retrig=retrig, hold=0.0)
    e.fire(at=0.0)
    assert e.step(2.0) == approx(0.5)
    e.fire(at=2.0)
    assert e.step(2.5) == approx(level)


def test_legato_mid_release_is_continuous():
    e = env(hold=0.0)
    e.fire(at=0.0)
    e.release(at=2.0)
    before = e.step(3.0)                       # 0.25
    e.fire(at=3.0)
    assert e.step(3.0 + 1e-9) == approx(before, abs=1e-6)


# ---- velocity ----

@pytest.mark.parametrize("vs, peak", [(0.0, 0.8), (0.5, 0.6), (1.0, 0.4)])
def test_velocity_sensitivity_scales_the_peak(vs, peak):
    e = env(amount=0.8, velocity=vs)
    e.fire(at=0.0, velocity=0.5)
    assert e.step(1.25) == approx(peak)
    assert e.step(3.0) == approx(peak * 0.5)   # sustain is a fraction of the peak


def test_amount_scales_the_note_live():
    e = env()
    e.fire(at=0.0)
    e.step(3.0)
    e.amount = 0.5
    assert e.step(3.1) == approx(0.25)


# ---- exactness and order ----

def test_a_sub_frame_fire_is_the_closed_form():
    at = 0.0123                                # between frames 0 and 1
    e2 = env()
    e2.step(0.0)
    e2.fire(at=at)
    t = 3 / 60
    for k in range(1, 4):
        e2.step(k / 60)
    assert e2.out == approx((t - at) / 1.0)
    for k in range(4, 120):
        e2.step(k / 60)
    t = 119 / 60                               # in decay: 1 → 0.5 from at + 1.5
    assert e2.out == approx(1.0 - 0.5 * (t - (at + 1.5)))


def test_a_stamp_before_the_last_step_is_clamped_to_it():
    e = env()
    e.step(1.0)
    e.fire(at=0.5)
    assert e.step(1.5) == approx(0.5)          # began at 1.0, not 0.5


def test_several_fires_in_one_step_apply_in_time_order():
    e = env(retrig=E.RESET, velocity=1.0)
    e.step(0.0)
    e.fire(at=0.1, velocity=1.0)               # queued first, but the later of the two
    e.fire(at=0.05, velocity=0.5)
    assert e.step(0.2) == approx(0.1)          # the 0.1 fire won: p = 0.1, peak 1
    assert e.vel == 1.0 and e.note == 2


def test_fire_release_fire_in_one_step():
    e = env(rel=1.0)
    e.step(0.0)
    e.fire(at=0.01)
    e.release(at=0.02)
    e.fire(at=0.03)
    y = 0.01 * (1 - 0.01)                      # the release's 0.01 s from 0.01
    assert e.step(0.04) == approx(y + (1 - y) * 0.01)
    assert e.stage == E.ATTACK


def test_a_late_fire_is_held_and_starts_at_zero():
    e = env()
    e.step(1.0)
    e.fire()                                   # after the step: the panel, Registry.apply
    t = 1.0 + 1 / 60
    assert e.step(t) == 0.0 and e.stage == E.ATTACK
    assert e.step(t + 1 / 60) == approx(1 / 60)


def test_release_from_mid_attack():
    e = env(rel=1.0)
    e.fire(at=0.0)
    e.release(at=0.5)
    assert e.step(1.0) == approx(0.25)
    assert e.step(1.5) == 0.0 and e.stage == E.IDLE


def test_time_never_runs_back():
    e = env()
    e.fire(at=0.0)
    e.step(0.5)
    assert e.step(0.25) == approx(0.5)


# ---- params ----

KNOB_KINDS = {
    "mode": Kind.ENUM, "attack": Kind.CONTINUOUS, "hold": Kind.CONTINUOUS,
    "decay": Kind.CONTINUOUS, "sustain": Kind.CONTINUOUS, "release": Kind.CONTINUOUS,
    "curve": Kind.CONTINUOUS, "sync": Kind.ENUM, "retrig": Kind.ENUM,
    "amount": Kind.CONTINUOUS, "velocity": Kind.CONTINUOUS,
}


def test_declare_registers_every_knob():
    reg, e = Registry(), Envelope()
    E.declare(reg, 3, e)
    ids = {f"env.3.{k}" for k in (*E.KNOBS, "fire", "gate")}
    assert set(reg.ids()) == ids and len(ids) == 13
    for k, kind in KNOB_KINDS.items():
        p = reg[f"env.3.{k}"]
        assert (p.kind, p.group, p.persist, p.modulatable) == (kind, "env", True, True), k
        assert p.label == f"env 3 {k}"
    assert reg["env.3.fire"].kind is Kind.TRIGGER and reg["env.3.fire"].modulatable
    g = reg["env.3.gate"]
    assert g.kind is Kind.TOGGLE and g.modulatable and not g.persist
    for k in ("attack", "hold", "decay", "release"):
        p = reg[f"env.3.{k}"]
        assert (p.lo, p.hi, p.log) == (0.001, 8.0, True)
    assert reg["env.3.mode"].names == ["gate", "one-shot"]
    assert reg["env.3.sync"].names == ["s", "beats"]
    assert reg["env.3.retrig"].names == ["legato", "reset"]
    assert set(reg.snapshot()) == {f"env.3.{k}" for k in E.KNOBS}
    n = len(reg)
    E.declare(reg, 3, e)                       # a second call is a no-op
    assert len(reg) == n


def test_the_knob_params_write_the_voice():
    reg, e = Registry(), Envelope()
    E.declare(reg, 1, e)
    reg["env.1.attack"].set_value(2.0)
    reg["env.1.mode"].set(1)
    reg["env.1.curve"].set_value(-0.5)
    assert (e.attack, e.mode, e.curve) == (2.0, E.ONE_SHOT, -0.5)
    assert reg["env.1.hold"].text() == "0"
    assert reg["env.1.attack"].text() == "2.00 s"
    reg["env.1.sync"].set(1)
    assert reg["env.1.attack"].text() == "2 beat"
    reg.restore({"env.1.decay": 0.5})
    assert e.decay == 0.5


def test_the_fire_param_fires_on_the_next_step():
    reg, e = Registry(), env()
    E.declare(reg, 1, e)
    e.step(1.0)
    reg["env.1.fire"].fire()
    assert e.step(1.5) == 0.0 and e.stage == E.ATTACK
    assert e.step(2.0) == approx(0.5)


def test_a_modulated_fire_fires_on_the_rising_edge():
    reg, e = Registry(), env()
    E.declare(reg, 1, e)
    p = reg["env.1.fire"]
    for u in (1.0, 1.0, 0.0, 1.0):
        p.modulate(u)
        reg.apply()
    assert e.note == 0 and len(e.events) == 2  # two rising edges
    e.step(0.0)
    assert e.note == 2


def test_the_gate_param_opens_and_closes():
    reg, e = Registry(), env(rel=1.0)
    E.declare(reg, 1, e)
    g = reg["env.1.gate"]
    g.set(True)
    e.step(0.0)
    assert e.step(3.0) == approx(0.5) and e.stage == E.SUSTAIN
    g.set(False)
    e.step(3.0 + 1e-9)
    assert e.stage == E.RELEASE


def test_a_modulated_gate_acts_only_on_its_edges():
    reg, e = Registry(), env()
    E.declare(reg, 1, e)
    g = reg["env.1.gate"]
    for u in (1.0, 1.0, 1.0):                  # written every frame, fired once
        g.modulate(u)
        reg.apply()
    assert e.held and len(e.events) == 1
    g.modulate(0.0)
    reg.apply()
    assert not e.held and [ev[2] for ev in e.events] == [0, 1]   # fire, release
