"""Plan 31 review findings — one regression test (or a few) per finding,
each written to fail before its fix. The rigs are test_plan31_wiring's."""

import pytest

from hyperspace import envelope
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
