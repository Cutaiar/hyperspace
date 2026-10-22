"""Plan 31 W1, the wiring: the envelopes as a second modulator bank, the
sequencer stepping inside `Router.modulate` and firing them, and the lot
carried by undo and the preset — end to end through a real Router and
Registry on a deterministic clock (`Clock(now=…)`, ticked by hand).

The frame here is the app's: the clock ticks, `router.modulate` runs the
pass (banks begin, the sequencer steps, the plan walks the nodes), then
`reg.apply` lands every param the pass did not."""

import math
from types import SimpleNamespace

import pytest

from hyperspace import devices, envelope, lfo, patch, routing, sequencer, undo
from hyperspace.envelope import Envelopes
from hyperspace.lfo import LFOs
from hyperspace.params import PERFORMANCE_GROUPS, Registry
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.sequencer import Sequencer
from hyperspace.tempo import Clock
from hyperspace.tempo import register as register_tempo

STEP = 0.25        # 120 BPM, span 1 bar: eight 8ths, 0.25 s each; a pattern is 2 s


def rig(routes=()):
    """A registry with the clock, four LFOs, the envelopes and the
    sequencer, a target param `t.x` (0–1) and a trigger `t.hit` that
    counts; a router stepping all of it, as app.main wires it."""
    reg = Registry()
    clock = Clock(now=lambda: 0.0)
    lfos, envs, seq = LFOs(seed=1), Envelopes(), Sequencer()
    register_tempo(reg, clock)
    lfo.register(reg, lfos, clock)
    envelope.register(reg, envs, clock)
    sequencer.register(reg, seq, clock)
    box = SimpleNamespace(x=0.0, hits=[])
    reg.continuous("t.x", "x", lambda: box.x, lambda v: setattr(box, "x", float(v)),
                   group="view")
    reg.trigger("t.hit", "hit", lambda: box.hits.append(clock.t), group="view")
    router = Router(reg, Bindings(list(routes)))
    router.use_lfos(lfos, clock)
    router.use_bank(envs, clock)
    router.use_sequencer(seq, envs)
    return SimpleNamespace(reg=reg, clock=clock, lfos=lfos, envs=envs, seq=seq,
                           router=router, box=box)


def frame(r, t: float, dt: float = 1 / 60) -> None:
    r.clock.tick(t)
    r.router.modulate(None, dt, t)
    r.reg.apply()


def one_shot(r, n: int, attack=0.1, decay=0.2, release=0.3) -> None:
    """Envelope n as a drum hit: linear, no hold, sustain 0."""
    reg = r.reg
    reg[f"env.{n}.mode"].set(envelope.ONE_SHOT)
    reg[f"env.{n}.attack"].set(attack)
    reg[f"env.{n}.decay"].set(decay)
    reg[f"env.{n}.sustain"].set(0.0)
    reg[f"env.{n}.release"].set(release)


# ---- the registration ----

def test_the_kinds_and_schemes_are_registered():
    assert routing.BANKS["env"] is Envelopes and routing.BANKS["lfo"] is LFOs
    assert "env" in patch.KINDS and Envelopes.KNOBS == patch.ENV_KNOBS
    assert set(patch.ENV_KNOBS) <= set(patch.PORTS)
    assert len(set(patch.PORTS)) == len(patch.PORTS)
    assert devices.BUILTIN_SCHEMES == routing.BUILTIN_LANES == ("lane", "lfo", "env", "seq")
    assert {"env", "seq"} <= set(PERFORMANCE_GROUPS)
    r = rig()
    assert r.router.schemes()[:4] == ("lane", "lfo", "env", "seq")
    frame(r, 0.5)
    assert r.router.lane_kinds["seq"] == ["trigger"] * sequencer.LANES
    assert r.router.rests["seq"] == [0.0] * 5 and r.router.rests["env"] == [0.0] * 5
    assert r.router.labels["env"] == [f"env {n}" for n in range(1, 6)]


def test_unrouted_envelopes_rest_and_the_sequencer_is_stopped():
    """The golden rule: nothing moves by default."""
    r = rig()
    assert not r.seq.run and r.envs.ids() == [1, 2, 3, 4, 5]
    for k in range(1, 200):
        frame(r, k / 60)
    assert list(r.router.feeds["env"]) == [0.0] * 5
    assert list(r.router.feeds["seq"]) == [0.0] * 5
    assert r.reg["seq.step"].value == 0


# ---- the sequencer fires the envelopes ----

def test_a_step_fires_its_envelope_at_the_steps_exact_time_and_it_comes_back():
    """Lane 1, step 1 on, run on, env 1 on `t.x`: the param rises from the
    step's own time (2.0 s, the pattern's second downbeat), not from the
    frame that saw it, and falls back to its base once the hit is over."""
    r = rig([Binding("env:0", "t.x", "push", 1.0)])
    one_shot(r, 1)
    r.reg["seq.1.1"].set(True)
    r.reg["seq.run"].set(True)
    frame(r, 1.99)
    assert r.box.x == 0.0                         # nothing yet: step 8 is at 2.0
    frame(r, 2.03)                                # the frame after the step
    assert r.box.x == pytest.approx(0.03 / 0.1)   # 30 ms into a 100 ms attack
    assert r.router.feeds["seq"][0] == 1.0
    frame(r, 2.1)
    assert r.box.x == pytest.approx(1.0)          # the peak, exactly at its time
    frame(r, 2.2)
    assert r.box.x == pytest.approx(0.5)          # half way down the decay
    for t in (2.3, 2.5, 2.7, 2.9):
        frame(r, t)
    assert r.box.x == 0.0 and r.envs.outputs[0] == 0.0
    assert r.reg["t.x"].base == 0.0


def test_seq_lane_fires_a_trigger_param_on_each_step():
    """``seq:0`` (lane 1, 0-based like ``lfo:0``) on a trigger: one fire per
    step that sounds, on the rising edge, re-armed by the frames between."""
    r = rig([Binding("seq:0", "t.hit", "push", 1.0)])
    for s in (1, 5):
        r.reg[f"seq.1.{s}"].set(True)
    r.reg["seq.run"].set(True)
    k = 1
    while k / 60 < 4.0:                           # two patterns from 1/60
        frame(r, k / 60)
        k += 1
    # steps 0 and 4 of the 2 s pattern: 1.0, 2.0, 3.0 (0.0 came before the start)
    assert r.box.hits == pytest.approx([1.0, 2.0, 3.0], abs=1 / 60)


def test_seq_lane_2_is_seq_1():
    r = rig([Binding("seq:1", "t.hit", "push", 1.0)])
    r.reg["seq.1.2"].set(True)                    # lane 1: not this route's
    r.reg["seq.run"].set(True)
    for k in range(1, 60):
        frame(r, k / 60)
    assert r.box.hits == []
    r.reg["seq.2.2"].set(True)
    for k in range(60, 180):
        frame(r, k / 60)
    assert len(r.box.hits) == 1


def test_the_global_trigger_fires_step_0_the_same_frame():
    """``lfo.trigger`` mid-step re-aligns the grid: step 0 fires on that
    frame, at the trigger's time — whether it came before the pass (a key)
    or after it (the panel, held to the next frame's begin)."""
    r = rig([Binding("env:0", "t.x", "push", 1.0)])
    one_shot(r, 1)
    r.reg["seq.1.1"].set(True)
    r.reg["seq.run"].set(True)
    frame(r, 0.6)
    frame(r, 0.62)
    assert r.seq.playhead == 2 and r.envs.outputs[0] == 0.0
    r.clock.tick(0.64)
    r.reg["lfo.trigger"].fire()                   # a key, before the pass
    r.router.modulate(None, 1 / 60, 0.64)
    r.reg.apply()
    assert r.seq.playhead == 0 and r.router.feeds["seq"][0] == 1.0
    assert r.clock.t0 == 0.64
    frame(r, 0.69)
    assert r.box.x == pytest.approx(0.05 / 0.1)   # fired at 0.64 exactly
    # the late road: fired after the pass, it lands at the next frame's begin
    frame(r, 1.0)
    r.reg["lfo.trigger"].fire()
    assert r.seq.playhead != 0
    frame(r, 1.02)
    assert r.seq.playhead == 0 and r.router.feeds["seq"][0] == 1.0
    assert r.clock.t0 == 1.02


# ---- the envelopes in the patch ----

def _square(r) -> None:
    """LFO 1 a square in Hz at the slowest rate: its wave is +1 for ages."""
    r.reg["lfo.1.shape"].set(lfo.SHAPES.index("square"))
    r.reg["lfo.1.sync"].set(0)
    r.reg["lfo.1.rate"].set(lfo.RATE_LO)


def test_an_envelope_owning_an_lfos_depth_lands_the_same_frame():
    r = rig([Binding("env:0", "lfo.1.depth", "push", 1.0)])
    _square(r)
    r.reg["lfo.1.depth"].set(0.0)
    r.reg["env.1.attack"].set(0.1)
    frame(r, 1.0)
    assert r.lfos.outputs[0] == pytest.approx(lfo.REST)
    r.envs.fire(1, at=1.0)
    frame(r, 1.05)                                # the envelope at 0.5 …
    assert r.envs.outputs[0] == pytest.approx(0.5)
    assert r.lfos.outputs[0] == pytest.approx(0.5 + 0.5 * 0.5)   # … LFO 1's depth this frame


def test_an_lfo_owning_an_envelopes_amount_lands_the_same_frame():
    r = rig([Binding("lfo:0", "env.1.amount", "push", 1.0)])
    _square(r)
    r.reg["env.1.amount"].set(0.0)
    r.reg["env.1.attack"].set(0.1)
    frame(r, 1.0)
    r.envs.fire(1, at=1.0)
    frame(r, 1.05)                                # LFO 1 at 1.0 pushes the amount to 0.5
    assert r.reg["env.1.amount"].value == pytest.approx(0.5)
    assert r.envs.outputs[0] == pytest.approx(0.5 * 0.5)       # level 0.5 × amount 0.5
    order = [s for s in r.router.__dict__["_plan"] if s[0] == "bank"]
    assert order.index(("bank", "lfo", 0)) < order.index(("bank", "env", 0))


def test_a_route_onto_an_envelopes_fire_starts_it_this_frame():
    """`fire` feeds the envelope's node (Envelopes.KNOBS): ``seq:1`` →
    ``env.6.fire`` lands before envelope 6 steps, so the note starts at
    this frame's t rather than the next one's."""
    r = rig([Binding("seq:1", "env.6.fire", "push", 1.0)])
    assert r.envs.add() == 6
    one_shot(r, 6)
    r.reg["seq.2.1"].set(True)
    r.reg["seq.2.mute"].set(False)
    r.reg["seq.2.env"].set(7)                     # its own envelope is none: only the route fires
    r.reg["seq.run"].set(True)
    frame(r, 1.99)
    frame(r, 2.0)
    frame(r, 2.05)
    assert r.envs.outputs[5] == pytest.approx(0.05 / 0.1)    # started at the 2.0 frame


# ---- membership ----

def test_an_extra_envelope_routes_and_goes_dormant_when_removed():
    r = rig([Binding("env:5", "t.x", "push", 1.0)])
    frame(r, 0.5)
    assert "env:5" not in r.router.patch.nodes or r.router.patch.nodes["env:5"].kind == "env"
    assert ("bank", "env", 5) not in r.router.__dict__["_plan"]
    assert r.envs.add() == 6 and "env.6.attack" in r.reg
    r.reg["env.6.attack"].set(0.1)
    r.envs.fire(6, at=0.5)
    frame(r, 0.55)
    assert ("bank", "env", 5) in r.router.__dict__["_plan"]
    assert r.box.x == pytest.approx(0.5)
    assert r.envs.remove(6) and "env.6.attack" not in r.reg
    frame(r, 0.6)
    assert len(r.router.feeds["env"]) == 5        # no lane 5: the route is dormant
    assert r.box.x == 0.0 and not r.reg["t.x"].modulated
    assert r.envs.next_id() == 6


def test_the_lane_envelopes_cannot_be_removed():
    r = rig()
    for n in (1, 5):
        assert r.envs.remove(n) is False and f"env.{n}.attack" in r.reg
    r.envs.set([])
    assert r.envs.ids() == [1, 2, 3, 4, 5]
    assert Envelopes.parse([6])[0] == [1, 2, 3, 4, 5, 6]
    assert Envelopes.parse(None)[0] == [1, 2, 3, 4, 5]
    assert Envelopes([7]).ids() == [1, 2, 3, 4, 5, 7]
    assert r.envs.fire(9) is False and r.envs.release(9) is False   # no such envelope: nothing


def test_a_lane_on_a_missing_envelope_fires_nothing():
    r = rig()
    r.reg["seq.1.1"].set(True)
    r.reg["seq.1.env"].set(12)
    r.reg["seq.run"].set(True)
    for k in range(1, 150):
        frame(r, k / 60)                          # step 0 at 2.0 fires env 12: there is none
    assert r.router.feeds["seq"] is not None and list(r.router.feeds["env"]) == [0.0] * 5


# ---- the transport ----

def test_stopping_releases_gate_mode_envelopes():
    """A stop closes a gate the pattern opened before its own gate ends:
    span 4 bars (a 1 s step at 120 BPM) and a full-step gate, so the note
    would hold until 3.0; the stop at 2.6 releases it there."""
    r = rig([Binding("env:0", "t.x", "push", 1.0)])
    r.reg["env.1.mode"].set(envelope.GATE)
    r.reg["env.1.sustain"].set(0.6)
    r.reg["env.1.release"].set(0.1)
    r.reg["seq.span"].set(sequencer.SPANS.index("4 bars"))
    r.reg["seq.gate"].set(1.0)
    r.reg["seq.1.3"].set(True)                    # step 3 of 8: 2.0 s
    r.reg["seq.run"].set(True)
    frame(r, 1.99)
    for t in (2.0, 2.3, 2.5):
        frame(r, t)
    assert r.box.x == pytest.approx(0.6)          # gate open: the sustain holds
    r.reg["seq.run"].set(False)
    frame(r, 2.6)                                 # the frame that sees the stop releases
    frame(r, 2.65)
    assert r.box.x == pytest.approx(0.3)          # half way through a 100 ms release
    frame(r, 2.8)
    assert r.box.x == 0.0 and r.reg["seq.step"].value == 0


def _gate_rig():
    """Env 1 in gate mode, linear, fast attack and decay to a 0.6 sustain
    and a 100 ms release, pushed onto `t.x`; lane 1 step 1 on at 1 bar."""
    r = rig([Binding("env:0", "t.x", "push", 1.0)])
    reg = r.reg
    reg["env.1.mode"].set(envelope.GATE)
    reg["env.1.attack"].set(0.01)
    reg["env.1.decay"].set(0.01)
    reg["env.1.sustain"].set(0.6)
    reg["env.1.release"].set(0.1)
    reg["seq.1.1"].set(True)
    reg["seq.run"].set(True)
    return r


def test_a_step_releases_a_gate_mode_envelope_after_half_a_step():
    """At 120 BPM and 1 bar a step is 0.25 s; the default gate, half a
    step, releases the note 0.125 s after the step's own time (2.0)."""
    r = _gate_rig()
    assert r.reg["seq.gate"].value == pytest.approx(sequencer.GATE) == 0.5
    assert r.seq.gate_seconds(r.clock) == pytest.approx(0.125)
    frame(r, 1.99)
    frame(r, 2.1)
    assert r.box.x == pytest.approx(0.6)          # sustaining: the gate is open
    frame(r, 2.125)
    assert r.box.x == pytest.approx(0.6)          # released exactly now
    frame(r, 2.175)
    assert r.box.x == pytest.approx(0.3)          # half way through the release
    frame(r, 2.23)
    assert r.box.x == 0.0                         # back before the next step


def test_the_gate_follows_the_bpm_and_the_gate_param():
    r = _gate_rig()
    r.clock.set_bpm(60.0, 0.0)                    # a step is now 0.5 s, the gate 0.25 s
    assert r.seq.gate_seconds(r.clock) == pytest.approx(0.25)
    frame(r, 3.99)                                # step 0 of the next bar: 4.0 s
    frame(r, 4.2)
    assert r.box.x == pytest.approx(0.6)          # 0.2 s in: still open at 60 BPM
    frame(r, 4.3)
    assert r.box.x == pytest.approx(0.3)          # released at 4.25
    r.reg["seq.gate"].set(0.2)
    assert r.seq.gate_seconds(r.clock) == pytest.approx(0.1)
    r.reg["seq.gate"].set(5.0)                    # clamped to a whole step
    assert r.reg["seq.gate"].value == 1.0


def test_a_one_shot_ignores_the_gate():
    """A one-shot runs its attack and decay whatever the gate: a 0.4 s
    decay outlasts the 0.125 s gate."""
    r = rig([Binding("env:0", "t.x", "push", 1.0)])
    one_shot(r, 1, attack=0.1, decay=0.4)
    r.reg["seq.1.1"].set(True)
    r.reg["seq.run"].set(True)
    frame(r, 1.99)
    frame(r, 2.1)
    assert r.box.x == pytest.approx(1.0)
    frame(r, 2.3)
    assert r.box.x == pytest.approx(0.5)          # mid-decay, long past the gate


# ---- undo ----

def test_undo_of_a_step_toggle():
    r = rig()
    u = undo.Undo(r.reg, r.router.table, banks=lambda: r.router._banks())
    undo.install(u)
    try:
        t = [0.0]

        def settle():
            for _ in range(3):
                t[0] += 1.0
                u.tick(t[0])

        settle()
        r.reg["seq.1.3"].set(True)
        settle()
        assert r.seq.lanes[0].steps[2] == 1.0
        assert u.undo() and r.seq.lanes[0].steps[2] == 0.0
        assert u.redo() and r.reg["seq.1.3"].value is True
        settle()
        r.reg["seq.run"].set(True)                # the transport is no step
        r.reg["env.2.gate"].set(True)             # …nor a held gate
        settle()
        assert u.undo() and r.reg["seq.1.3"].value is False and r.seq.run
        # an extra envelope is a step through the bank's membership
        settle()
        undo.push("add env")
        r.envs.add()
        settle()
        assert u.undo() and r.envs.ids() == [1, 2, 3, 4, 5]
    finally:
        undo.install(None)


# ---- the preset ----

@pytest.fixture()
def app(tmp_path):
    from hyperspace import preset, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.fx import FxState
    from hyperspace.library import Library
    from hyperspace.lookback import DreamState
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState

    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    lfos, envs, seq = LFOs(), Envelopes(), Sequencer()
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    envelope.register(reg, envs, clock)
    sequencer.register(reg, seq, clock)
    table = routing.Bindings.load(routing.bindings_path(tmp_path), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = routing.Router(reg, table)
    router.use_lfos(lfos, clock)
    router.use_bank(envs, clock)
    router.use_sequencer(seq, envs)
    presets = preset.Presets(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, router=router, presets=presets, lfos=lfos,
                           envs=envs, seq=seq)


def test_a_preset_carries_the_pattern_and_the_envelopes(app):
    reg = app.reg
    reg["seq.1.1"].set(True)
    reg["seq.3.5"].set(True)
    reg["seq.span"].set(0)
    reg["seq.length"].set(6)
    reg["seq.2.mute"].set(True)
    reg["env.2.attack"].set(0.5)
    reg["env.4.mode"].set(envelope.ONE_SHOT)
    reg["seq.run"].set(True)
    reg["env.1.gate"].set(True)
    doc = app.presets.document("pattern")
    vals = doc["values"]
    assert "envs" not in doc                      # the five lane envelopes: no key
    assert vals["seq.1.1"] is True and vals["seq.3.5"] is True and vals["seq.1.2"] is False
    assert vals["seq.span"] == 0 and vals["seq.length"] == 6 and vals["seq.2.mute"] is True
    assert vals["env.2.attack"] == pytest.approx(0.5) and vals["env.4.mode"] == envelope.ONE_SHOT
    for pid in ("seq.run", "seq.step", "seq.trigger", "env.1.gate", "env.1.fire"):
        assert pid not in vals
    app.envs.add()
    reg["env.6.decay"].set(1.5)
    doc = app.presets.document("pattern")
    assert doc["envs"] == [1, 2, 3, 4, 5, 6] and doc["values"]["env.6.decay"] == 1.5
    # somewhere else entirely, then back
    reg["seq.1.1"].set(False)
    reg["env.2.attack"].set(0.01)
    app.envs.remove(6)
    assert app.presets.load_doc(doc) == []
    assert reg["seq.1.1"].value is True and app.seq.lanes[0].steps[0] == 1.0
    assert reg["env.2.attack"].value == pytest.approx(0.5)
    assert app.envs.ids() == [1, 2, 3, 4, 5, 6] and app.envs.voice(6).decay == 1.5
    assert app.seq.run                            # the transport is the session's
    assert app.presets.document("pattern")["values"] == doc["values"]


def test_an_old_preset_loads_four_lfos_five_envelopes_and_an_empty_pattern(app):
    reg = app.reg
    doc = app.presets.document("old")
    old = {**doc, "values": {k: v for k, v in doc["values"].items()
                             if not k.startswith(("env.", "seq."))}}
    old.pop("envs", None)
    old.pop("lfos", None)
    app.lfos.add()
    app.envs.add()
    reg["seq.4.8"].set(True)
    reg["env.3.sustain"].set(0.1)
    reg["seq.swing"].set(0.3)
    assert app.presets.load_doc(old) == []
    assert app.lfos.ids() == [1, 2, 3, 4] and app.envs.ids() == [1, 2, 3, 4, 5]
    assert not any(v for ln in app.seq.lanes for v in ln.steps)
    assert reg["env.3.sustain"].value == pytest.approx(envelope.Envelope().sustain)
    assert reg["seq.swing"].value == 0.0
    again = app.presets.document("old")
    assert "envs" not in again and "lfos" not in again


def test_nan_never_reaches_a_param_from_an_idle_bank():
    r = rig([Binding("env:2", "t.x", "push", 1.0), Binding("seq:4", "t.x", "push", 1.0)])
    for k in range(1, 30):
        frame(r, k / 60)
    assert r.box.x == 0.0 and not math.isnan(r.reg["t.x"].value)
