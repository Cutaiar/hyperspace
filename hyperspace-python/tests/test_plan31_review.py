"""Plan 31 review findings — one regression test (or a few) per finding,
each written to fail before its fix. The rigs are test_plan31_wiring's."""

import pytest

from hyperspace import envelope, graphview, modbank, sequencer
from hyperspace.envelope import Envelope

from test_plan31_wiring import frame, rig


# ---- 1: a note keeps the mode it was fired with ----

def _voice(mode):
    e = Envelope(mode=mode, attack=0.1, decay=0.2, sustain=0.5, rel=0.3)
    e.step(0.0)
    return e


def test_a_gate_note_switched_to_one_shot_still_releases():
    e = _voice(envelope.GATE)
    e.fire(at=0.0)
    e.step(1.0)
    assert e.stage == envelope.SUSTAIN
    e.mode = envelope.ONE_SHOT                 # the knob moves mid-note
    e.release()
    e.step(1.1)
    assert e.stage == envelope.RELEASE
    e.step(2.0)
    assert e.stage == envelope.IDLE and e.out == 0.0


def test_a_gate_notes_auto_release_lands_after_a_switch_to_one_shot():
    e = _voice(envelope.GATE)
    e.fire(at=0.0, gate=1.0)
    e.step(0.5)
    assert e.stage == envelope.SUSTAIN
    e.mode = envelope.ONE_SHOT
    e.step(1.1)
    assert e.stage == envelope.RELEASE


def test_a_one_shot_switched_to_gate_mid_decay_still_closes_at_decays_end():
    e = _voice(envelope.ONE_SHOT)
    e.fire(at=0.0)
    e.step(0.2)                                # in decay
    assert e.stage == envelope.DECAY
    e.mode = envelope.GATE
    e.step(0.31)
    assert e.stage == envelope.RELEASE
    e.step(1.0)
    assert e.stage == envelope.IDLE


def test_the_mode_knob_affects_the_next_fire():
    e = _voice(envelope.ONE_SHOT)
    e.fire(at=0.0)
    e.step(0.05)
    e.mode = envelope.GATE
    e.fire(at=0.06)                            # a new note: gate now
    e.step(1.0)
    assert e.stage == envelope.SUSTAIN


# ---- 2: stop releases only the notes the pattern opened ----

def test_stop_leaves_a_held_gate_sounding_and_its_release_still_works():
    r = rig()
    reg = r.reg
    frame(r, 0.0)
    reg["env.1.gate"].set(True)                # a held pad
    frame(r, 0.01)
    frame(r, 0.5)
    e = r.envs.voice(1)
    assert e.stage == envelope.SUSTAIN and e.held
    reg["seq.run"].set(True)
    frame(r, 0.51)
    reg["seq.run"].set(False)
    frame(r, 0.52)
    frame(r, 1.5)
    assert e.stage == envelope.SUSTAIN and e.held
    reg["env.1.gate"].set(False)               # the pad lets go: it releases
    frame(r, 1.51)
    assert e.stage == envelope.RELEASE and not e.held


def test_stop_leaves_a_fired_note_alone():
    r = rig()
    frame(r, 0.0)
    r.reg["env.2.fire"].fire()
    frame(r, 0.01)
    r.reg["seq.run"].set(True)
    frame(r, 0.1)
    r.reg["seq.run"].set(False)
    frame(r, 0.11)
    frame(r, 1.0)
    assert r.envs.voice(2).stage == envelope.SUSTAIN


def test_stop_still_releases_a_note_the_pattern_opened():
    r = rig()
    reg = r.reg
    reg["seq.gate"].set(1.0)                   # a step's whole length
    reg["seq.1.1"].set(True)
    reg["env.1.attack"].set(0.01)
    reg["env.1.decay"].set(0.01)
    reg["seq.run"].set(True)
    frame(r, 0.0)                              # step 0 fires
    frame(r, 0.1)
    e = r.envs.voice(1)
    assert e.stage == envelope.SUSTAIN
    reg["seq.run"].set(False)
    frame(r, 0.12)
    frame(r, 0.13)
    assert e.stage == envelope.RELEASE


# ---- 3: a lane can fire any envelope id the bank can hold ----

def test_a_lane_takes_an_envelope_id_above_16():
    r = rig()
    reg = r.reg
    while r.envs.can_add():
        r.envs.add()
    r.envs.remove(6)
    n = r.envs.add()
    assert n == 17
    reg["seq.1.env"].set(n)
    assert reg["seq.1.env"].value == 17 and r.seq.lanes[0].env == 17
    assert sequencer.ENV_HI == modbank.MAX_ID
    # the GRAPH page's drag onto an envelope's fire sets it too
    view = graphview.build(r.router.table, reg, r.router)
    e = graphview.Edit(r.router.table, reg, r.router, view)
    assert e.bind_lane(1, n) == (1, n) and r.seq.lanes[1].env == n
    # and the lane fires it
    reg["seq.2.1"].set(True)
    reg["seq.run"].set(True)
    frame(r, 0.0)
    frame(r, 0.05)
    assert r.envs.voice(n).stage != envelope.IDLE


def test_a_lane_on_a_missing_id_fires_nothing():
    r = rig()
    r.reg["seq.1.env"].set(40)                 # no such envelope
    assert r.seq.lanes[0].env == 40
    r.reg["seq.1.1"].set(True)
    r.reg["seq.run"].set(True)
    frame(r, 0.0)
    frame(r, 0.05)
    assert all(v.stage == envelope.IDLE for v in r.envs.voices)
