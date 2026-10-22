"""Plan 31 review findings — one regression test (or a few) per finding,
each written to fail before its fix. The rigs are test_plan31_wiring's."""

import pytest

from hyperspace import envelope, graphview, modbank, preset, sequencer
from hyperspace.envelope import Envelope
from hyperspace.sequencer import SPANS, Sequencer
from hyperspace.tempo import Clock

from test_plan31_wiring import frame, make_app, rig


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


# ---- 4: a refused load leaves the extra voices exactly as they were ----

def test_a_refused_load_keeps_the_extra_voices_and_their_values(tmp_path):
    app = make_app(tmp_path)
    reg = app.reg
    doc = app.presets.document("x")            # four LFOs, five envelopes
    bad = {**doc, "values": {**doc["values"], "view.bright": "fast"}}
    n = app.lfos.add()
    reg[f"lfo.{n}.depth"].set(0.9)
    reg[f"lfo.{n}.rate"].set(7.0)
    m = app.envs.add()
    reg[f"env.{m}.decay"].set(3.0)
    before = reg.snapshot(part="performance")
    with pytest.raises(ValueError):
        app.presets.load_doc(bad)
    assert app.lfos.ids() == [1, 2, 3, 4, 5] and app.envs.ids() == [1, 2, 3, 4, 5, 6]
    assert reg[f"lfo.{n}.depth"].value == pytest.approx(0.9)
    assert reg[f"lfo.{n}.rate"].value == pytest.approx(7.0)
    assert reg[f"env.{m}.decay"].value == pytest.approx(3.0)
    assert reg.snapshot(part="performance") == before


# ---- 5 and 6: the sequencer alone (test_sequencer's rig) ----

def _seq(run=True, span="1 bar"):
    clock = Clock(bpm=120.0, now=lambda: 0.0)
    seq = Sequencer()
    seq.span = SPANS.index(span)
    seq.run = run
    seq.lanes[0].steps = [(j + 1) / 10 for j in range(sequencer.STEPS)]
    calls = []
    return clock, seq, calls, lambda lane, env, at, v: calls.append((at, round(v * 10) - 1))


def _frames(seq, clock, fire, times):
    for t in times:
        clock.tick(t)
        seq.step(t, clock, fire)


def test_restart_while_stopped_then_run_fires_the_downbeat_at_the_run_frame():
    clock, seq, calls, fire = _seq(run=False)
    _frames(seq, clock, fire, [0.3 + k / 60 for k in range(30)])
    seq.restart()                              # stopped: held for run
    _frames(seq, clock, fire, [0.9, 0.95])
    assert calls == [] and seq.pending
    seq.run = True
    t_run = 0.95 + 1 / 60
    _frames(seq, clock, fire, [t_run, t_run + 0.1, t_run + 0.26])
    assert calls[0] == (pytest.approx(t_run), 0)
    assert calls[1] == (pytest.approx(t_run + 0.25), 1)
    assert not seq.pending


def test_run_on_with_no_restart_still_waits_for_the_next_boundary():
    clock, seq, calls, fire = _seq(run=False)
    _frames(seq, clock, fire, [0.0, 0.1])
    seq.run = True
    _frames(seq, clock, fire, [0.12, 0.2, 0.3])
    assert calls == [(pytest.approx(0.25), 1)]


@pytest.mark.parametrize("length", [1, 2])
def test_a_short_pattern_keeps_every_step_of_one_slow_frame(length):
    clock, seq, calls, fire = _seq()
    seq.length = length
    _frames(seq, clock, fire, [0.0, 0.8])     # crosses 0.25, 0.5 and 0.75
    assert [c[0] for c in calls] == pytest.approx([0.0, 0.25, 0.5, 0.75])
    assert [c[1] for c in calls] == [j % length for j in range(4)]


def test_a_two_second_stall_at_length_1_still_fires_one_step():
    clock, seq, calls, fire = _seq(span="1/2 bar")   # 0.125 s a step
    seq.length = 1
    _frames(seq, clock, fire, [0.0, 2.1])
    assert [c[0] for c in calls] == pytest.approx([0.0, 2.0])


# ---- 7: desk rows and layout keys need no /3 — an older build keeps them ----

def test_desk_rows_and_layout_keys_on_plan_31_ids_survive_a_build_without_it(tmp_path):
    """A pre-plan-31 build (`make_app(plan31=False)`: no env/seq params)
    loads a desk row on ``env.2.fire`` and GRAPH positions for env/seq
    nodes and writes them back verbatim — `set_desk` checks no target
    against the registry and `read_layout` keeps any name — so neither
    makes a file /3 (`preset.schema_of`)."""
    old = make_app(tmp_path, plan31=False)
    doc = old.presets.document("x")
    row = {**doc["desk"][0], "target": "env.2.fire", "op": "momentary"}
    layout = {"env.6": [10, 20], "seq": [1, 2], "lfo.7": [3, 4]}
    doc = {**doc, "desk": [row, *doc["desk"][1:]], "layout": layout}
    assert preset.schema_of(doc) == preset.SCHEMA
    old.presets.load_doc(doc)
    out = old.presets.document("x")
    assert out["desk"][0] == row and out["layout"] == layout
    assert out["schema"] == preset.SCHEMA
