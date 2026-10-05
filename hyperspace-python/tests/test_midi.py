"""MIDI adapter: routing, pickup, feedback, learn — no hardware, fake ports."""

from types import SimpleNamespace

import mido
import pytest

from hyperspace import apc40, hands, lfo, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.midi import PICKUP_TOL, Binding, MidiIO
from hyperspace.overlay import Output
from hyperspace.params import Kind, build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Bindings, Router, is_session_row
from hyperspace.view import ViewState


class FakeIn:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)


class FakeOut:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


def cc(control, value, channel=0):
    return mido.Message("control_change", channel=channel, control=control, value=value)


def note(n, vel=127, channel=0):
    t = "note_on" if vel else "note_off"
    return mido.Message(t, channel=channel, note=n, velocity=vel)


@pytest.fixture()
def rig(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(tmp_path)
    presets = lib.project
    reg = build_registry(view, control, audio, presets)
    lib.attach(reg)
    reg.toggle("ui.panel", "Panel", lambda: True, lambda v: None)
    reg.toggle("ui.cheatsheet", "Sheet", lambda: True, lambda v: None)
    reg.trigger("audio.restart", "Restart", lambda: None)
    reg.trigger("audio.stop", "Stop", lambda: None)
    reg.toggle("audio.play", "Play", lambda: False, lambda v: None)
    Output(None, None).register(reg)
    clock = tempo.Clock(now=lambda: 0.0)       # the transport corner: tap, nudge, trigger
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    hands.register(reg, hands.HandSettings.from_config({}))   # the global track knobs
    inp, out = FakeIn(), FakeOut()
    m = MidiIO(reg, path=tmp_path / "midi_map.json", inp=inp, out=out)
    Presets(lib, reg, Router(reg, m.table))     # the bank the clip row and QUANT load
    return SimpleNamespace(reg=reg, view=view, control=control, audio=audio,
                           presets=presets, midi=m, inp=inp, out=out, clock=clock)


def push(r, *msgs):
    r.inp.queue.extend(msgs)
    r.midi.poll()


def shift(r):
    """Latch SHIFT (plan 13 D4): the global layer comes up."""
    push(r, note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))


# ---------------------------------------------------------------- default map

def test_default_map_binds_only_real_params(rig):
    ids = set(rig.reg.ids())
    for b in rig.midi.bindings:
        assert b.target in ids, b
        if b.op == "set" and rig.reg[b.target].kind is Kind.ENUM:
            assert 0 <= int(b.value) < len(rig.reg[b.target].names), b


def test_default_map_has_no_two_controls_on_one_key(rig):
    keys = [(b.key, b.layer) for b in rig.midi.bindings]      # one row per layer
    assert len(keys) == len(set(keys))


def test_power_up_sends_mode_sysex(rig):
    first = rig.out.sent[0]
    assert first.type == "sysex" and list(first.data)[:6] == [0x47, 0x7F, 0x73, 0x60, 0, 4]
    assert list(first.data)[6] == apc40.MODE_LIVE_ALT


# ---------------------------------------------------------------- knobs

def test_device_knob_drives_selected_band_under_shift(rig):
    """The band strip is the global layer's (plan 13 §3.2): dead until
    SHIFT is up. A device knob is an endless encoder the ring re-bases
    (D7), so it continues from the ring it was just sent — no pickup —
    and a band switch re-draws the ring, which re-bases it again."""
    reg, control = rig.reg, rig.control
    atk = reg["band.sel.atk"]
    before = atk.norm
    push(rig, cc(0x15, 0))            # the preset layer: nothing there
    assert atk.norm == pytest.approx(before)
    shift(rig)
    push(rig, cc(0x15, 127))          # re-based at the ring: applied at once
    assert atk.norm == pytest.approx(1.0)
    push(rig, cc(0x15, 64))
    assert atk.position() == round(64 / 127 * atk.steps)
    # switching band moves the alias under the knob: the ring is redrawn,
    # and the knob continues from there
    control.selb = 3
    rig.midi.poll()
    b = next(x for x in rig.midi.bindings if x.target == "band.sel.atk")
    assert b.caught and b.last_hw == pytest.approx(round(reg["band.3.atk"].norm * 127) / 127)
    push(rig, cc(0x15, 10))
    assert reg["band.3.atk"].norm == pytest.approx(10 / 127, abs=PICKUP_TOL)


def test_pickup_catches_when_knob_reaches_value(rig):
    b = rig.reg["view.bright"]
    b.set_norm(0.5)
    target = round(0.5 * 127)
    push(rig, cc(0x30, target))       # exactly on it
    assert b.norm == pytest.approx(target / 127, abs=PICKUP_TOL)
    push(rig, cc(0x30, target + 20))
    assert b.norm == pytest.approx((target + 20) / 127, abs=PICKUP_TOL)


def test_a_fader_moved_while_its_row_is_disabled_has_to_pick_up_again(rig):
    """Audit R13: a disabled row's messages are passed over, and the fader
    travels without its param. Re-enabled, its next message must not write
    the whole distance: the row picks up again from where the fader is."""
    b = rig.reg["view.bright"]
    row = next(x for x in rig.midi.bindings if x.target == "view.bright" and x.kind == "cc")
    b.set_norm(0.5)
    mid = round(0.5 * 127)
    push(rig, cc(0x30, mid))
    assert row.caught
    row.enabled = False
    push(rig, cc(0x30, 120))                  # moved while the row is off
    assert b.norm == pytest.approx(mid / 127, abs=PICKUP_TOL)
    assert not row.caught and row.last_hw == pytest.approx(120 / 127)
    row.enabled = True
    push(rig, cc(0x30, 118))                  # was: a jump from 0.5 to 0.93
    assert b.norm == pytest.approx(mid / 127, abs=PICKUP_TOL)
    push(rig, cc(0x30, 90), cc(0x30, mid))    # brought back through the value: caught
    assert row.caught
    push(rig, cc(0x30, mid - 10))
    assert b.norm == pytest.approx((mid - 10) / 127, abs=PICKUP_TOL)


def test_fader_without_pickup_jumps(rig):
    for x in rig.midi.bindings:
        if x.target == "master.gain":
            x.pickup = False
    g = rig.reg["master.gain"]
    push(rig, cc(apc40.CC_MASTER, 0))
    assert g.value == 0.0
    push(rig, cc(apc40.CC_MASTER, 127))
    assert g.norm == 1.0


def test_relative_encoder_steps_shape(rig):
    rig.view.shape = 5
    push(rig, cc(apc40.CC_CUE, 1))    # +1
    assert rig.view.shape == 6
    push(rig, cc(apc40.CC_CUE, 126))  # −2 in two's complement
    assert rig.view.shape == 4


def test_faders_on_channels_pick_their_band(rig):
    for x in rig.midi.bindings:
        x.pickup = False
    push(rig, cc(apc40.CC_FADER, 0, channel=2))
    assert rig.audio.chain.params[2].post == 0.0
    assert rig.audio.chain.params[1].post == 1.0
    push(rig, cc(apc40.CC_FADER, 0, channel=7))
    assert rig.audio.chain.params[7 - 7].post == 1.0  # channel 8 is master trim
    assert rig.reg["master.trim"].position() == 0


# ---------------------------------------------------------------- buttons

def test_select_buttons_and_led_state(rig):
    push(rig, note(apc40.N_SELECT, channel=4))
    assert rig.control.selb == 4
    leds = {(m.channel, m.note): m.velocity for m in rig.out.sent if m.type == "note_on"}
    assert leds[(4, apc40.N_SELECT)] == 1
    assert leds[(0, apc40.N_SELECT)] == 0
    shift(rig)                                    # the band scenes are global (§3.2)
    push(rig, note(apc40.N_CLIP[1], channel=3))   # scene 3
    assert rig.control.scene == 3
    leds = {(m.channel, m.note): m.velocity for m in rig.out.sent if m.type == "note_on"}
    assert leds[(3, apc40.N_CLIP[1])] == apc40.YELLOW
    push(rig, note(apc40.N_CLIP[2], channel=1))   # scene 9
    assert rig.control.scene == 9


def test_toggle_button_flips_and_lights(rig):
    assert not rig.view.faces
    push(rig, note(apc40.N_SCENE[2]), note(apc40.N_SCENE[2], 0))
    assert rig.view.faces
    last = [m for m in rig.out.sent if m.type == "note_on" and m.note == apc40.N_SCENE[2]][-1]
    assert last.velocity == 1
    push(rig, note(apc40.N_SCENE[2]), note(apc40.N_SCENE[2], 0))
    assert not rig.view.faces
    last = [m for m in rig.out.sent if m.type == "note_on" and m.note == apc40.N_SCENE[2]][-1]
    assert last.velocity == 0


def test_trigger_echoes_while_held(rig):
    rig.view.yaw = 1.0
    push(rig, note(apc40.N_SCENE[4]))
    assert rig.view.yaw == 0.0
    lit = [m for m in rig.out.sent if m.type == "note_on" and m.note == apc40.N_SCENE[4]]
    assert lit[-1].velocity == 1
    push(rig, note(apc40.N_SCENE[4], 0))
    lit = [m for m in rig.out.sent if m.type == "note_on" and m.note == apc40.N_SCENE[4]]
    assert lit[-1].velocity == 0


def test_step_buttons(rig):
    b = rig.reg["view.bright"]
    p0 = b.position()
    push(rig, note(apc40.N_UP))
    assert b.position() == p0 + 3
    push(rig, note(apc40.N_LEFT))
    assert rig.control.selb == 0  # clamps at the first band
    push(rig, note(apc40.N_RIGHT))
    assert rig.control.selb == 1


def test_transport_corner_is_the_clock(rig):
    """TAP TEMPO taps, NUDGE ± steps a hundredth, QUANT steps the preset bank."""
    c = rig.clock
    c.tick(1.0)
    push(rig, note(apc40.N_TAP), note(apc40.N_TAP, 0))
    c.tick(1.5)
    push(rig, note(apc40.N_TAP), note(apc40.N_TAP, 0))
    assert c.bpm == pytest.approx(120.0)
    push(rig, note(apc40.N_NUDGE_P), note(apc40.N_NUDGE_P, 0))
    assert c.nudge == pytest.approx(0.01)
    push(rig, note(apc40.N_NUDGE_M), note(apc40.N_NUDGE_M, 0))
    push(rig, note(apc40.N_NUDGE_M), note(apc40.N_NUDGE_M, 0))
    assert c.nudge == pytest.approx(-0.01)
    was = rig.presets.active
    push(rig, note(apc40.N_QUANT))
    assert rig.presets.active != was


def test_metronome_fires_the_trigger_and_blinks_on_the_beat(rig):
    """One row on the note: the press is the global LFO trigger, and its
    LED follows the beat through the light the trigger param carries."""
    c = rig.clock
    c.tick(3.3)
    push(rig, note(apc40.N_METRO), note(apc40.N_METRO, 0))
    assert c.t0 == 3.3

    def led():
        return [m.velocity for m in rig.out.sent
                if m.type == "note_on" and m.note == apc40.N_METRO][-1]

    assert led() == 1                            # on the downbeat: lit
    c.tick(3.3 + 0.25)                           # half a beat at 120: dark
    rig.midi.poll()
    assert led() == 0
    c.tick(3.3 + 0.5)                            # the next beat
    rig.midi.poll()
    assert led() == 1
    assert len(rig.midi.table.route("note", 0, apc40.N_METRO)) == 1


def test_preset_row_lights_the_active_preset(rig):
    push(rig, note(apc40.N_CLIP[0], channel=2))
    assert rig.presets.active == 2
    leds = {(m.channel, m.note): m.velocity for m in rig.out.sent if m.type == "note_on"}
    assert leds[(2, apc40.N_CLIP[0])] == apc40.GREEN
    # a slot that holds another preset is amber, not dark (plan 19 WP2)
    assert leds[(0, apc40.N_CLIP[0])] == apc40.YELLOW


# ---------------------------------------------------------------- feedback

def test_ring_feedback_is_change_gated(rig):
    b = rig.reg["view.bright"]
    rings = [m for m in rig.out.sent if m.type == "control_change" and m.control == 0x30]
    assert len(rings) == 1 and rings[0].value == round(b.norm * 127)  # sent on connect
    rig.out.sent.clear()
    rig.midi.poll()
    rig.midi.poll()
    assert not [m for m in rig.out.sent if m.type == "control_change" and m.control == 0x30]
    b.set_norm(0.25)  # moved by something else: the ring follows
    rig.midi.poll()
    rings = [m for m in rig.out.sent if m.type == "control_change" and m.control == 0x30]
    assert rings[-1].value == round(0.25 * 127)


def test_ring_shows_the_base_and_never_chases_a_performer(rig):
    """Plan 09 WP2: a knob on a performed param is a scene-setter. The
    ring tracks p.norm — the base — so a performer moving the effective
    value sends nothing, the base moving does, and the knob itself turns
    the base while the performer's offset stays exactly where it was."""
    reg, b = rig.reg, rig.reg["view.bright"]

    def rings():
        return [m.value for m in rig.out.sent
                if m.type == "control_change" and m.control == 0x30]

    def perform(u):                   # the router's frame: offset in, apply, feedback
        b.modulate(u)
        reg.apply()
        rig.midi.poll()

    b.set_norm(0.5)
    rig.midi.poll()
    rig.out.sent.clear()
    for u in (0.1, 0.2, 0.3):         # only the offset moves
        perform(u)
    assert b.modulated and b.eff_norm == pytest.approx(0.8, abs=1e-3) and rings() == []
    b.set_norm(0.25)                  # the base moves (a fader, a preset)
    perform(0.3)
    assert rings() == [round(0.25 * 127)]
    assert b.eff_norm == pytest.approx(0.55, abs=1e-3)
    # the knob: caught at the base's value, then turned — the base follows
    # it, the performer's 0.3 rides on top, the ring shows the knob
    rig.out.sent.clear()
    target = round(0.25 * 127)
    push(rig, cc(0x30, target))
    perform(0.3)
    push(rig, cc(0x30, target + 40))
    perform(0.3)
    assert b.norm == pytest.approx((target + 40) / 127, abs=PICKUP_TOL)
    assert b.eff_norm - b.norm == pytest.approx(0.3, abs=1e-3)
    assert rings()[-1] == round(b.norm * 127)
    reg.apply()                       # the performer leaves: the knob's value shows
    assert not b.modulated and b.norm == pytest.approx((target + 40) / 127, abs=PICKUP_TOL)


def test_ring_style_is_set_once(rig):
    styles = [m for m in rig.out.sent if m.type == "control_change" and m.control == 0x30 + 8]
    assert len(styles) == 1 and styles[0].value == apc40.RING_VOLUME
    rig.midi.poll()
    styles = [m for m in rig.out.sent if m.type == "control_change" and m.control == 0x30 + 8]
    assert len(styles) == 1


def test_selected_band_rings_follow_the_selection(rig):
    def ring(ccn):
        return [m.value for m in rig.out.sent
                if m.type == "control_change" and m.control == ccn][-1]

    rig.reg["band.0.thr"].set_norm(0.1)
    rig.reg["band.2.thr"].set_norm(0.9)
    rig.control.selb = 0
    shift(rig)                                    # the strip's rings are the global layer's
    rig.midi.poll()
    assert ring(0x17) == round(0.1 * 127)
    rig.control.selb = 2
    rig.midi.poll()
    assert ring(0x17) == round(0.9 * 127)


# ---------------------------------------------------------------- learn

def test_learn_binds_next_message_into_the_preset_layer(rig, tmp_path):
    """Plan 13 §3.3: the learned row is a preset-layer row in the live
    table — the file is not written (tests/test_learn.py has the rest)."""
    m = rig.midi
    path = tmp_path / "midi_map.json"
    before = path.read_text() if path.exists() else None
    m.learner.arm("view.inst_amp")
    assert m.learner.learning == "view.inst_amp"
    push(rig, cc(0x57, 40))                   # send-A knob-ish: an unused CC
    assert m.learner.learning is None
    b = m.binding_for("view.inst_amp")
    assert b is not None and b.kind == "cc" and b.number == 0x57 and b.op == "abs"
    assert b.layer == "preset" and "CC 87" in b.describe()
    # the learning message itself did not move the param
    assert rig.view.inst_amp == 0.25
    # the old track-knob binding for the same param is gone
    assert not any(x.target == "view.inst_amp" and x.number == 0x34 for x in m.bindings)
    # and nothing went to disk
    assert (path.read_text() if path.exists() else None) == before


def test_learn_a_button_on_a_toggle(rig):
    m = rig.midi
    free = apc40.N_CLIP[2]                    # clip row 3, track 4: free on both layers
    m.learner.arm("view.lines")
    push(rig, note(free, 0, channel=3))       # a release is not a binding
    assert m.learner.learning == "view.lines"
    push(rig, note(free, channel=3))
    b = next(x for x in m.bindings if x.target == "view.lines" and x.number == free)
    assert b.kind == "note" and b.channel == 3 and b.feedback == "led" and b.on == apc40.GREEN
    push(rig, note(free, 0, channel=3), note(free, channel=3))
    assert not rig.view.lines                  # was True by default, flipped once


def test_learn_takes_over_a_key_from_its_old_param(rig):
    m = rig.midi
    m.learner.arm("view.pattern_mix")
    push(rig, cc(0x30, 64))                   # the brightness knob
    assert not [x for x in m.bindings if x.target == "view.bright" and x.kind == "cc"]
    assert m.binding_for("view.bright").kind == "note"  # its step buttons survive
    assert m.binding_for("view.pattern_mix").number == 0x30
    m.unbind("view.pattern_mix")
    assert m.binding_for("view.pattern_mix") is None
    push(rig, cc(0x30, 10))                   # now nothing listens
    assert rig.view.pattern_mix == 1.0


def test_unbind_removes_only_preset_layer_rows_and_writes_no_file(rig):
    """Plan 13 WP5: right-click → Unbind is an edit of the loaded preset —
    its desk rows on the param go (the knob and the step buttons), no file
    is written, the preset's dot lights; a param only the session maps (an
    invariant fader, a global-layer knob) is refused with the reason in
    the learn line, as Learn refuses, and its row stays."""
    m, lib = rig.midi, rig.presets.lib
    lib.load("presets", "BIG BLUE WAVE")
    assert not lib.is_dirty("presets")
    path = m.table.path
    before = path.read_bytes() if path.exists() else None
    session = [b.to_json() for b in m.table.bindings if b.layer != "preset"]
    rows = [b for b in m.table.desk() if b.target == "view.bright"]
    assert {b.kind for b in rows} == {"cc", "note"}               # the knob and ▲ ▼
    m.unbind("view.bright")
    assert not [b for b in m.table.bindings if b.target == "view.bright" and b.is_midi]
    assert not m.learner.refused and "unbound view.bright" in m.learner.last
    assert (path.read_bytes() if path.exists() else None) == before
    assert lib.is_dirty("presets")
    assert [b.to_json() for b in m.table.bindings if b.layer != "preset"] == session
    push(rig, cc(0x30, 10))                                       # nothing listens now
    assert rig.view.bright == pytest.approx(lib.read("presets", "BIG BLUE WAVE")["values"]
                                            .get("view.bright", 1.0))
    # the session's rows: refused, kept
    for pid, why in (("band.0.post", "invariant"), ("band.sel.trim", "global layer")):
        m.unbind(pid)
        assert m.learner.refused and why in m.learner.last, pid
        assert m.table.for_param(pid) is not None, pid
    assert (path.read_bytes() if path.exists() else None) == before


def test_relative_cc_learn_keeps_encoder_mode(rig):
    rig.midi.learner.arm("view.instances")
    push(rig, cc(apc40.CC_CUE, 1))
    assert rig.midi.binding_for("view.instances").op == "rel"


def test_a_hand_learn_reaches_the_shared_learn_object(rig):
    """The adapter arms and completes through the shared learn.Learn
    (tests/test_learn.py has the rest); a hand completing it writes a
    `position` row the MIDI view never sees, and the knob row stays."""
    m = rig.midi
    m.learner.arm("view.inst_amp")
    assert m.learner.learning == "view.inst_amp"
    m.learner.learn_source("hand:3", when="hand:14")
    assert m.learner.learning is None and m.learner.pending is None
    b = m.table.owner("view.inst_amp")
    assert (b.source, b.op, b.value, b.when) == ("hand:3", "position", 1.0, "hand:14")
    assert "pickup" not in b.to_json()                         # not a performer's field
    assert m.binding_for("view.inst_amp").is_midi            # the knob row is still there
    assert "learned view.inst_amp" in m.learner.last


# ------------------------------------- plan 17 WP2: a learn listens to one source

def test_a_knob_bump_during_a_hand_learn_does_its_own_job(rig):
    """Armed for a hand ("Learn hand ▸ left"), the desk is not listening
    for the learn: K1 turns and Brightness moves, a pad toggles its param,
    the learn is still armed and no row was added or replaced (plan 17 §1
    row 2: it used to take the param, or kill the learn)."""
    m, lrn, bright = rig.midi, rig.midi.learner, rig.reg["view.bright"]
    for x in m.bindings:
        x.pickup = False
    rows = [(b.to_json(), b.layer) for b in m.table.bindings]
    lrn.arm("view.depth4", "hand:left")
    push(rig, cc(0x30, 20))
    low = bright.norm
    push(rig, cc(0x30, 110))
    assert bright.norm > low and bright.norm == pytest.approx(110 / 127, abs=0.02)
    lines = rig.view.lines
    pad = next(b for b in m.table.desk() if b.target == "view.lines" and b.kind == "note")
    push(rig, note(pad.number, channel=pad.channel or 0), note(pad.number, 0, channel=pad.channel or 0))
    assert rig.view.lines != lines
    assert lrn.learning == "view.depth4" and lrn.want == "hand:left" and not lrn.refused
    assert [(b.to_json(), b.layer) for b in m.table.bindings] == rows
    # the hand then completes it; the knob had no part in it
    lrn.learn_source("hand:left.roll")
    assert lrn.learning is None and m.table.owner("view.depth4").source == "hand:left.roll"
    # no knob learned: depth's one desk row is the fresh layer's D1 (apc40.SCENE, plan 19 WP3)
    assert [b.source for b in m.table.desk() if b.target == "view.depth4" and b.is_midi] \
        == ["cc:*:16"]


def test_an_invariant_control_works_through_a_desk_learn(rig):
    """Fork 6: armed for the desk, an invariant control is not a candidate
    — it does its one job. A fader moves its param, SHIFT latches (and
    latches back), TAP taps, and the learn is still armed, unrefused, the
    table untouched; a release is never a candidate; then a knob the
    preset may map lands it, and that message is not dispatched."""
    m, lrn, reg = rig.midi, rig.midi.learner, rig.reg
    for x in m.bindings:
        x.pickup = False
    rows = [(b.to_json(), b.layer) for b in m.table.bindings]
    lrn.arm("view.depth4", "desk")
    post = reg["band.2.post"]
    push(rig, cc(apc40.CC_FADER, 0, channel=2))              # S3: a fader's jitter
    low = post.norm
    push(rig, cc(apc40.CC_FADER, 127, channel=2))
    assert post.norm > low
    assert lrn.learning == "view.depth4" and not lrn.refused and lrn.last == ""
    shift(rig)                                               # SHIFT latches through it
    assert m.table.layer == "global" and lrn.learning == "view.depth4"
    shift(rig)
    assert m.table.layer == "preset" and lrn.learning == "view.depth4"
    taps = len(rig.clock.taps)
    tap = next(b for b in m.table.midi() if b.target == "tempo.tap" and b.layer is None)
    push(rig, note(tap.number, channel=tap.channel or 0), note(tap.number, 0, channel=tap.channel or 0))
    assert lrn.learning == "view.depth4" and len(rig.clock.taps) == taps + 1
    assert [(b.to_json(), b.layer) for b in m.table.bindings] == rows
    depth4, bright = reg["view.depth4"].norm, reg["view.bright"].norm
    push(rig, cc(0x30, 100))                                 # K1: the preset's to map
    assert lrn.learning is None and "learned view.depth4 ← K1 (track knob 1)" in lrn.last
    assert "B16" not in lrn.last                             # Brightness keeps its buttons
    assert reg["view.depth4"].norm == depth4 and reg["view.bright"].norm == bright
    assert [b.source for b in m.table.desk() if b.target == "view.depth4"] == ["cc:0:48"]


# ---------------------------------------------------------------- map file

def test_map_round_trips_json(tmp_path):
    path = tmp_path / "m.json"
    mm = Bindings.load(path)
    n = len([b for b in mm.midi() if is_session_row(b)])   # the file keeps the session's
    mm.bind(Binding("pitch:3", "view.zoom", "abs"))
    mm2 = Bindings.load(path)
    assert len(mm2.midi()) == n + 1
    b = mm2.for_param("view.zoom")
    assert b.kind == "pitch" and b.channel == 3 and not hasattr(b.to_json(), "caught")
    assert "caught" not in b.to_json()


def test_pitch_bend(rig):
    rig.midi.table.bind(Binding("pitch:0", "camera.pitch", "abs", pickup=False))
    rig.inp.queue.append(mido.Message("pitchwheel", channel=0, pitch=8191))
    rig.midi.poll()
    assert rig.reg["camera.pitch"].norm == pytest.approx(1.0, abs=1e-3)


def test_unbound_message_is_ignored_and_reported(rig):
    push(rig, cc(0x7F, 3))
    assert rig.midi.last == "cc 127 ch1 = 3"


def test_close_returns_to_generic_mode(rig):
    rig.out.sent.clear()
    rig.midi.close()
    assert rig.out.sent[-1].type == "sysex"
    assert list(rig.out.sent[-1].data)[6] == apc40.MODE_GENERIC
    assert not rig.midi.on


# ------------------------------------------------------ plan 15 WP1: undo

def test_an_unbind_is_one_undo_step(tmp_path):
    """Right-click → Unbind is one undo step: every preset-layer row it
    took comes back, the desk is redrawn (the control lights again), and
    it is a restore, not a load. A refused unbind leaves no step."""
    from test_undo import boot, frames, labels, settle

    r = boot(tmp_path / "home")
    table, u, m = r.table, r.undo, r.midi
    knob = next(b for b in table.desk() if b.kind == "cc" and b.feedback == "ring")
    pid = knob.target
    was = [b.to_json() for b in table.desk()]
    gone = [b.to_json() for b in table.desk() if b.target == pid]
    serial = table.desk_serial
    m.unbind(pid)
    assert not any(b.target == pid for b in table.desk())
    settle(r)
    assert labels(r) == [f"unbind {pid}"]
    r.out.sent.clear()
    assert u.undo() and u.status == f"undid unbind {pid}"
    assert [b.to_json() for b in table.desk()] == was and table.desk_serial == serial
    assert [b.to_json() for b in table.desk() if b.target == pid] == gone
    frames(r)                                             # the adapter follows the table
    ring = [x for x in r.out.sent if x.type == "control_change" and x.control == knob.number
            and x.channel == (knob.channel or 0)]
    assert ring and ring[-1].value == round(r.reg[pid].norm * 127)
    assert u.redo() and not any(b.target == pid for b in table.desk())
    u.undo()
    frames(r, 3)
    # the session's rows: refused, nothing changes, no step
    m.unbind("band.0.post")
    assert m.learner.refused
    settle(r)
    assert u.stack == []


# ---------------------------------------------------------------- the master dim

def test_the_crossfader_dims_with_soft_pickup(rig):
    """Plan 15 WP3: the crossfader is the master dim on both layers, CC 0
    black. A launch is at full with the fader wherever it was left: parked
    at the left it does nothing — it cannot black the rig out by being
    touched — until it is brought up to the value; then it follows."""
    dim = rig.reg["output.dim"]
    b = next(x for x in rig.midi.bindings if x.source == f"cc:0:{apc40.CC_XFADE}")
    assert (b.target, b.op, b.layer, b.pickup, b.feedback) == ("output.dim", "abs", None,
                                                               True, None)
    # invariant (D6): a preset's row on the control would never act
    assert rig.midi.table.is_invariant(Binding(b.source, "view.bright", "abs", layer="preset"))
    assert dim.value == 1.0 and not b.caught
    for v in (0, 0, 3, 40, 90, 120):               # parked at black, then on the way up
        push(rig, cc(apc40.CC_XFADE, v))
        assert dim.value == 1.0 and not b.caught, v
    push(rig, cc(apc40.CC_XFADE, 127))             # reached it
    assert b.caught and dim.value == 1.0
    push(rig, cc(apc40.CC_XFADE, 64))
    assert dim.value == pytest.approx(64 / 127, abs=PICKUP_TOL)
    shift(rig)                                     # the same on the global layer
    assert b.caught
    push(rig, cc(apc40.CC_XFADE, 20))
    assert dim.value == pytest.approx(20 / 127, abs=PICKUP_TOL)
    push(rig, cc(apc40.CC_XFADE, 0))               # the left end
    assert dim.value == 0.0 and dim.text() == "black"
    push(rig, cc(apc40.CC_XFADE, 127))
    assert dim.value == 1.0
    # the panel's fader moved it: pickup again, no jump
    dim.set_norm(0.5)
    rig.midi.poll()
    assert not b.caught
    push(rig, cc(apc40.CC_XFADE, 126))
    assert dim.value == pytest.approx(0.5)
    push(rig, cc(apc40.CC_XFADE, 40))              # swept through it
    assert dim.value == pytest.approx(40 / 127, abs=PICKUP_TOL)


# ------------------------------------------- plan 15 WP4: the hold, the bar, the blink

STOP = apc40.N_CLIPSTOP


def bar_rig(rig):
    """The rig with a clock the test moves and a counter on the bar's
    target: `fires` grows by one each time `preset.save_new` fires (the
    save itself still runs)."""
    from hyperspace import midi

    t = [0.0]
    rig.midi.clock = lambda: t[0]
    p = rig.reg["preset.save_new"]
    fires: list[float] = []
    real = p.fire

    def fire():
        fires.append(t[0])
        return real()
    p.fire = fire
    assert (midi.HOLD_S, midi.BLINK_S) == (0.6, 1.5)

    def at(seconds, *msgs):
        t[0] = seconds
        push(rig, *msgs)
    return at, fires


def leds(rig, n, channel=0, since=0):
    return [m.velocity for m in rig.out.sent[since:]
            if m.type == "note_on" and m.note == n and m.channel == channel]


def test_a_hold_fires_once_at_the_hold_time_while_held(rig):
    """A `hold` row fires when its button has been down HOLD_S — while it
    is still down (fork 14) — and never again for that press."""
    at, fires = bar_rig(rig)
    lib, pr = rig.presets.lib, rig.presets
    rows = [b for b in rig.midi.bindings if b.op == "hold"]
    assert [(b.source, b.target, b.layer) for b in rows] \
        == [(f"note:{k}:{STOP}", "preset.save_new", None) for k in range(8)]
    pr.clear_slot(5)
    push(rig, note(apc40.N_CLIP[0], channel=4), note(apc40.N_CLIP[0], 0, channel=4))
    assert lib.current("presets") == "TRIP"
    at(0.0, note(STOP, channel=2))
    at(0.3)
    at(0.59)
    assert fires == [] and lib.current("presets") == "TRIP"
    at(0.6)                                                  # still held: it fires now
    assert fires == [0.6]
    assert lib.current("presets") == "TRIP 2" and pr.bank[5] == "TRIP 2"
    at(1.0)
    at(2.0)                                                  # still down: nothing more
    assert fires == [0.6]
    at(2.5, note(STOP, 0, channel=2))                        # the release does nothing
    at(5.0)
    assert fires == [0.6] and lib.current("presets") == "TRIP 2"
    # a key or pad row with the op does nothing (`routing.act` ignores it)
    from hyperspace import routing
    routing.act(rig.reg, Binding("key:F9", "preset.save_new", "hold"))
    assert fires == [0.6]
    # a press held across a reconnect is forgotten
    at(10.0, note(STOP, channel=0))
    rig.midi._enter()
    at(11.0)
    assert fires == [0.6] and not any(b.lit for b in rows)


def test_a_tap_fires_nothing(rig):
    at, fires = bar_rig(rig)
    lib = rig.presets.lib
    was, bank = lib.current("presets"), list(rig.presets.bank)
    at(0.0, note(STOP, channel=3))
    at(0.3, note(STOP, 0, channel=3))                        # released at 0.3 s
    at(0.6)
    at(2.0)
    assert fires == [] and lib.current("presets") == was and rig.presets.bank == bank
    # a tap in one poll, and taps one after the other, likewise
    at(3.0, note(STOP, channel=3), note(STOP, 0, channel=3))
    at(3.5, note(STOP, channel=3))
    at(4.0, note(STOP, 0, channel=3), note(STOP, channel=4))  # 0.5 s each, never 0.6 on one
    at(4.5, note(STOP, 0, channel=4))
    at(6.0)
    assert fires == []
    # a release while a Learn is armed still ends the press
    at(7.0, note(STOP, channel=1))
    rig.midi.learner.arm("view.bright")
    at(7.2, note(STOP, 0, channel=1))
    rig.midi.learner.arm(None)
    at(8.0)
    assert fires == []


def test_the_bar_is_one_control(rig):
    """The eight buttons are one bar: a hand across several fires once; a
    button still down afterwards fires nothing more; only a new press
    starts a new hold."""
    at, fires = bar_rig(rig)
    at(0.0, note(STOP, channel=1))
    at(0.2, note(STOP, channel=2), note(STOP, channel=6))    # a hand lying across the row
    at(0.6)
    assert fires == [0.6]                                    # the first press's time; one fire
    at(0.8)                                                  # the others pass 0.6 s: nothing
    at(1.5)
    assert fires == [0.6]
    at(1.6, note(STOP, 0, channel=1))                        # one lifted, two still down
    at(3.0)
    assert fires == [0.6]
    at(3.1, note(STOP, channel=1))                           # a new press: a new hold
    at(3.6)
    assert fires == [0.6]
    at(3.75)
    assert fires == [0.6, 3.75]
    at(3.8, note(STOP, 0, channel=1), note(STOP, 0, channel=2), note(STOP, 0, channel=6))
    at(9.0)
    assert fires == [0.6, 3.75]
    # the same press on either layer (invariant), and SHIFT's state at the
    # press is what counts (D12)
    shift(rig)
    at(10.0, note(STOP, channel=7))
    at(10.7)
    assert len(fires) == 3


def test_the_bar_lights_while_held_and_the_new_slots_pad_blinks(rig):
    """The velocities sent, and for how long: dark at rest (fork 15); the
    whole bar lit while any of it is held; on the save the bar and the new
    slot's pad blink for BLINK_S (2: the protocol's blink for a plain
    button and green blink on the grid); then the bar is dark and the pad
    green. A tap lights the bar for as long as it lasts."""
    from hyperspace import midi

    at, fires = bar_rig(rig)
    pr = rig.presets
    pad = apc40.N_CLIP[0]
    assert apc40.blink_of(STOP, 1) == 2 and apc40.blink_of(pad, apc40.GREEN) == apc40.GREEN_BLINK
    assert apc40.blink_of(apc40.N_CLIP[2], apc40.RED) == apc40.RED_BLINK
    assert apc40.blink_of(apc40.N_CLIP[4], apc40.YELLOW) == apc40.YELLOW_BLINK
    assert apc40.blink_of(apc40.N_OVERDUB, 1) == 2
    pr.clear_slot(5)
    push(rig, note(pad, channel=4), note(pad, 0, channel=4))        # TRIP: pad 5 green
    assert all(leds(rig, STOP, k)[-1] == 0 for k in range(8))       # dark at rest
    assert leds(rig, pad, 4)[-1] == apc40.GREEN and leds(rig, pad, 5)[-1] == 0
    # a tap: the whole bar for as long as it lasts
    mark = len(rig.out.sent)
    at(0.0, note(STOP, channel=3))
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1]] * 8
    at(0.2, note(STOP, 0, channel=3))
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 0]] * 8
    # two held, one let go: lit until the last is up
    mark = len(rig.out.sent)
    at(1.0, note(STOP, channel=0), note(STOP, channel=1))
    at(1.2, note(STOP, 0, channel=0))
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1]] * 8
    at(1.4, note(STOP, 0, channel=1))
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 0]] * 8
    # the hold: lit, then on the save the bar and pad 6 blink
    mark = len(rig.out.sent)
    at(2.0, note(STOP, channel=3))
    at(2.5)
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1]] * 8
    assert leds(rig, pad, 5, mark) == []
    at(2.65)
    assert fires == [2.65] and pr.bank[5] == "TRIP 2" and pr.active == 5
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2]] * 8
    assert leds(rig, pad, 5, mark) == [apc40.GREEN_BLINK]           # the new slot's pad
    assert leds(rig, pad, 4, mark) == [apc40.YELLOW]     # TRIP's pad: filled, not loaded
    assert [leds(rig, pad, k, mark) for k in (0, 1, 2, 3, 6, 7)] == [[]] * 6   # no other pad
    at(3.0, note(STOP, 0, channel=3))                               # letting go changes nothing
    at(2.65 + midi.BLINK_S - 0.01)
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2]] * 8
    assert leds(rig, pad, 5, mark) == [apc40.GREEN_BLINK]
    at(2.65 + midi.BLINK_S)                                         # the time is up
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2, 0]] * 8
    assert leds(rig, pad, 5, mark) == [apc40.GREEN_BLINK, apc40.GREEN]
    at(9.0)
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2, 0]] * 8
    # a button kept down through the blink: the bar still goes dark after it
    mark = len(rig.out.sent)
    pr.clear_slot(1)
    at(10.0, note(STOP, channel=7))
    at(10.65)
    at(10.65 + midi.BLINK_S)
    assert pr.bank[1] == "TRIP 3"
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2, 0]] * 8
    # (the cleared slot's pad went from amber to dark first: plan 19 WP2)
    assert leds(rig, pad, 1, mark) == [0, apc40.GREEN_BLINK, apc40.GREEN]
    at(12.5, note(STOP, 0, channel=7))
    # a full bank: only the bar blinks — no pad came on (plan 19 WP1: the
    # bank is twenty-four, so the far slots are filled first)
    for k in range(8, len(pr.bank)):
        if pr.bank[k] is None:
            pr.put_slot(k, "WAKE")
    mark = len(rig.out.sent)
    assert pr.next_empty() is None
    at(20.0, note(STOP, channel=0))
    at(20.65)
    assert pr.lib.warning == "saved TRIP 4 — the bank is full: it is in the preset list"
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2]] * 8
    assert [m.velocity for m in rig.out.sent[mark:]                 # TRIP 3's pad: amber
            if m.type == "note_on" and m.note == pad] == [apc40.YELLOW]
    # a fire that answers False did nothing (a save that failed): the bar
    # goes dark at the hold time and nothing blinks (review of PR #87)
    at(30.0)
    mark = len(rig.out.sent)
    count = len(fires)
    with pytest.MonkeyPatch.context() as mp:
        def full(*a, **k):
            raise OSError("disk full")
        mp.setattr(pr.lib, "save_as", full)
        at(31.0, note(STOP, channel=2))
        at(31.65)
        at(33.0, note(STOP, 0, channel=2))
    assert len(fires) == count + 1 and "disk full" in pr.bank_error
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 0]] * 8
    assert [m.velocity for m in rig.out.sent[mark:]
            if m.type == "note_on" and m.note == pad] == []
    at(40.0, note(STOP, channel=0))
    at(40.65)
    # a redraw mid-blink (a layer switch) re-sends the blink, not the state
    mark = len(rig.out.sent)
    shift(rig)
    assert [leds(rig, STOP, k, mark)[-1] for k in range(8)] == [2] * 8
    at(40.65 + midi.BLINK_S, note(STOP, 0, channel=0))
    assert [leds(rig, STOP, k, mark)[-1] for k in range(8)] == [0] * 8


# ------------------------------------------- plan 18 WP2: knob smoothing

TICK = 1 / 64               # a frame, exact in binary: so are the sums below
GLIDE = 0.125               # desk.slew for these tests: eight frames
K_MIX = 0x33                # track knob 4 on the preset layer: view.pattern_mix, 100 detents


def slew_rig(rig, seconds=GLIDE):
    """The rig with a clock the test moves and smoothing on: `at(t, …)`
    sets the clock and polls with the messages; one poll at t = 0 is made."""
    t = [0.0]
    rig.midi.clock = lambda: t[0]
    rig.reg["desk.slew"].set(seconds)

    def at(seconds, *msgs):
        t[0] = seconds
        push(rig, *msgs)
    at(0.0)
    return at


def rings(rig, ccn=K_MIX, channel=0):
    return [m.value for m in rig.out.sent
            if m.type == "control_change" and m.control == ccn and m.channel == channel]


def test_smoothing_is_off_by_default_and_every_write_is_immediate(rig):
    """A bare table has `slew` 0 (the app sets its own default,
    tests/test_app_boundary.py): a CC lands on its detent in the poll that
    reads it and no glide is ever made."""
    from hyperspace import routing

    slew, mix = rig.reg["desk.slew"], rig.reg["view.pattern_mix"]
    assert Bindings().slew == 0.0 and rig.midi.table.slew == 0.0
    assert slew.value == 0.0 and slew.text() == "off" and not slew.modulatable
    assert (slew.lo, slew.hi, slew.persist) == (0.0, routing.SLEW_MAX_S, True)
    slew.set(9.0)                                   # clamped to the maximum
    assert rig.midi.table.slew == routing.SLEW_MAX_S and slew.text() == "250 ms"
    slew.set(0.0)
    for v in (100, 3, 64):
        push(rig, cc(K_MIX, v))
        assert mix.position() == round(v / 127 * 100) and mix.norm == mix.position() / 100
        assert rig.midi._slews == {}
    rig.midi.poll()
    assert rig.midi._slews == {}


def test_a_smoothed_knob_arrives_in_a_straight_line_and_rests_on_the_detent(rig):
    """One message, eight frames: the base moves on every poll, by the same
    amount each time, between detents on the way, and on the poll GLIDE
    after the message it is exactly what `set_norm(u)` gives — the detent."""
    mix = rig.reg["view.pattern_mix"]
    mix.set_norm(0.0)
    at = slew_rig(rig)
    at(TICK, cc(K_MIX, 90))                        # the message: lands at TICK + GLIDE
    seen = [mix.norm]
    for k in range(2, 9):
        at(k * TICK)
        seen.append(mix.norm)
    # a straight line from the previous poll (t = 0) to the landing
    span, target = TICK + GLIDE, round(90 / 127 * 100) / 100
    assert seen == pytest.approx([target * k * TICK / span for k in range(1, 9)], abs=1e-12)
    steps = [b - a for a, b in zip([0.0, *seen], seen, strict=False)]
    assert all(s == pytest.approx(steps[0], abs=1e-12) and s > 0 for s in steps)
    assert sum(abs(u * 100 - round(u * 100)) > 0.01 for u in seen) >= 6   # between detents
    assert "view.pattern_mix" in rig.midi._slews
    at(9 * TICK)                                    # GLIDE after the message: the landing
    landed = mix.value
    assert rig.midi._slews == {} and mix.position() == 71 and mix.norm == 0.71
    mix.set_norm(90 / 127)                          # the write smoothing-off makes
    assert mix.value == landed
    at(10 * TICK)
    assert mix.value == landed                      # and it rests


def test_a_glide_starts_on_the_frame_of_the_message(rig):
    """No dead frame: the poll that reads the message already moved the
    base — the line starts at the previous poll, and after a long gap
    between polls no further back than 50 ms."""
    from hyperspace import midi

    mix = rig.reg["view.pattern_mix"]
    mix.set_norm(0.0)
    at = slew_rig(rig)
    at(TICK, cc(K_MIX, 127))
    assert mix.norm == pytest.approx(TICK / (TICK + GLIDE)) and mix.norm > 0.1
    for k in range(2, 10):
        at(k * TICK)
    assert mix.norm == 1.0
    at(5.0, cc(K_MIX, 0))                          # the last poll was seconds ago
    assert midi.SLEW_BACK_S == 0.05
    assert 1.0 - mix.norm == pytest.approx(0.05 / (0.05 + GLIDE))


def test_a_new_message_re_aims_the_glide_from_where_it_is(rig):
    """A turn is many messages: each re-aims the one glide from where the
    base has got to — no jump back to an old target, no jump on to the new
    one — and it lands GLIDE after the last. A second control on the same
    param re-aims the same glide: one per param."""
    mix = rig.reg["view.pattern_mix"]
    mix.set_norm(0.0)
    rig.midi.table.add(Binding("cc:0:60", "view.pattern_mix", "abs", layer="preset",
                               pickup=False))
    at = slew_rig(rig)
    at(TICK, cc(K_MIX, 127))
    at(2 * TICK)
    at(3 * TICK)
    up = mix.norm
    assert 0.3 < up < 0.4
    at(4 * TICK, cc(K_MIX, 0))                     # turned back: from here, downward
    assert 0.0 < mix.norm < up and up - mix.norm < 0.1
    s = rig.midi._slews["view.pattern_mix"]
    assert s.target == 0.0 and s.t_end == 4 * TICK + GLIDE
    at(5 * TICK, cc(60, 127))                      # the other control takes the same glide
    assert list(rig.midi._slews) == ["view.pattern_mix"]
    assert rig.midi._slews["view.pattern_mix"] is s and s.target == 1.0
    assert s.t_end == 5 * TICK + GLIDE
    low = mix.norm
    for k in range(6, 13):
        at(k * TICK)
        assert mix.norm > low
        low = mix.norm
    at(13 * TICK)                                   # GLIDE after the last message
    assert mix.norm == 1.0 and rig.midi._slews == {}


def test_the_ring_shows_where_the_knob_is_going(rig):
    """During a glide the ring CC is the knob's own target — the message a
    desk without smoothing sends, on the same poll — never the base in
    flight, so `_rebase` leaves the encoder where the hand has it. The
    whole turn's ring messages are the ones smoothing-off sends."""
    mix = rig.reg["view.pattern_mix"]
    b = next(x for x in rig.midi.bindings if x.target == "view.pattern_mix")
    turn = [70, 71, 73, 76, 80, 90, 127, 126, 64, 63, 0]

    def play(seconds):
        mix.set_norm(0.0)
        at = slew_rig(rig, seconds)
        rig.out.sent.clear()
        hw = []
        for k, v in enumerate(turn, start=1):
            at(k * TICK, cc(K_MIX, v))
            hw.append((b.caught, b.last_hw))
        for k in range(len(turn) + 1, len(turn) + 12):
            at(k * TICK)
        return rings(rig), hw, mix.value

    off = play(0.0)
    rig.out.sent.clear()
    mix.set_norm(0.0)
    at = slew_rig(rig)
    rig.out.sent.clear()
    at(TICK, cc(K_MIX, 90))                        # one message, looked at closely
    target = round(round(90 / 127 * 100) / 100 * 127)
    assert rings(rig) == [target] and mix.norm < 0.2          # the ring is ahead of the base
    assert b.caught and b.last_hw == target / 127             # the knob's own position
    for k in range(2, 12):
        at(k * TICK)
    assert rings(rig) == [target]                             # nothing more: no lagging value
    on = play(GLIDE)
    assert on == off and len(on[0]) >= 8
    assert all(caught for caught, _hw in on[1])


def test_the_ring_a_glide_shows_is_the_ring_after_the_write(rig):
    """`_landing` is the norm `set_norm` leaves, bit for bit, on every
    continuous param at every 7-bit value — tapered, logarithmic, wrapped
    — so the ring sent ahead of a glide is the ring sent after the write."""
    n = 0
    for p in rig.reg:
        if p.kind is not Kind.CONTINUOUS or p.integer or p.alias:
            continue
        keep = p.base
        for v in range(128):
            want = MidiIO._landing(p, v / 127)
            p.set_norm(v / 127)
            assert p.norm == want, (p.id, v)
            n += 1
        p.set(keep)
    assert n > 128 * 100


def test_a_fader_keeps_its_catch_through_a_glide_and_an_uncaught_one_writes_nothing(rig):
    """Soft pickup is unchanged: the glide's own writes are the adapter's
    (`_note_written`), so `_uncatch_moved` never reads them as "moved
    without us" and a caught fader stays caught while its value arrives;
    a fader that has not reached its param's value starts no glide."""
    dim, gain = rig.reg["output.dim"], rig.reg["master.gain"]
    x = next(b for b in rig.midi.bindings if b.source == f"cc:0:{apc40.CC_XFADE}")
    m = next(b for b in rig.midi.bindings if b.target == "master.gain")
    push(rig, cc(apc40.CC_XFADE, 127))             # brought up to the value: caught
    assert x.caught and x.pickup and dim.value == 1.0
    at = slew_rig(rig)
    at(TICK, cc(apc40.CC_XFADE, 0))
    seen = []
    for k in range(2, 9):
        at(k * TICK)
        seen.append(dim.norm)
        assert x.caught, k
    assert seen == sorted(seen, reverse=True) and 0.0 < seen[-1] < seen[0] < 1.0
    at(9 * TICK)
    assert dim.value == 0.0 and x.caught and rig.midi._slews == {}
    at(10 * TICK, cc(apc40.CC_XFADE, 64))          # still caught: it follows, gliding
    assert x.caught and 0.0 < dim.norm < 0.2
    # master.gain's fader has not been brought to its value: nothing
    was = gain.value
    assert m.pickup and not m.caught
    far = 0 if gain.norm > 0.5 else 127
    at(11 * TICK, cc(apc40.CC_MASTER, far))
    assert not m.caught and gain.value == was and "master.gain" not in rig.midi._slews
    for k in range(12, 24):
        at(k * TICK)
    assert gain.value == was and dim.norm == round(64 / 127 * 100) / 100


def test_someone_elses_write_stops_a_glide(rig):
    """The panel, a key, an undo: a write the adapter did not make ends
    the glide the next poll, and that value stands."""
    mix = rig.reg["view.pattern_mix"]
    mix.set_norm(0.0)
    at = slew_rig(rig)
    at(TICK, cc(K_MIX, 127))
    at(2 * TICK)
    assert 0.0 < mix.norm < 1.0 and rig.midi._slews
    mix.set(mix._value_of_norm(0.6234))             # someone else, between detents
    theirs = mix.value
    for k in range(3, 14):
        at(k * TICK)
        assert mix.value == theirs and rig.midi._slews == {}
    # and the knob takes it again from there (the ring re-based it)
    at(14 * TICK, cc(K_MIX, 0))
    assert mix.norm < 0.6234 and rig.midi._slews


def test_buttons_relative_knobs_and_discrete_targets_are_not_smoothed(rig):
    """With smoothing on: the cue knob (`rel`) and a `rel64` encoder step
    detents at once, a note `set` lands at once, and an `abs` row on an
    enum, on a toggle and on an integer param (`view.instances`: its steps
    are the integers) writes the value in the poll that reads it."""
    reg, t = rig.reg, rig.midi.table
    for src, target, op in (("cc:0:60", "view.pattern_mix", "rel64"),
                            ("cc:0:61", "view.shape", "abs"),
                            ("cc:0:62", "view.faces", "abs"),
                            ("note:0:120", "view.pattern_mix", "set")):
        t.add(Binding(src, target, op, value=0.25, layer="preset", pickup=False))
    assert reg["view.shape"].kind is Kind.ENUM and reg["view.faces"].kind is Kind.TOGGLE
    assert reg["view.instances"].integer
    at = slew_rig(rig)
    mix = reg["view.pattern_mix"]
    mix.set_norm(0.5)
    at(TICK)
    rig.view.shape = 5
    at(2 * TICK, cc(apc40.CC_CUE, 1))              # rel: the cue knob
    assert rig.view.shape == 6
    at(3 * TICK, cc(60, 64 + 3))                   # rel64: three detents
    assert mix.norm == pytest.approx(0.53)
    at(4 * TICK, note(120))                         # a note `set`
    assert mix.value == pytest.approx(0.25)
    at(5 * TICK, cc(61, 127))                       # abs on an enum
    assert reg["view.shape"].norm == 1.0
    faces = reg["view.faces"].value
    at(6 * TICK, cc(62, 0 if faces else 127))       # abs on a toggle
    assert reg["view.faces"].value is (not faces)
    inst = reg["view.instances"]
    at(7 * TICK, cc(0x32, 127))                     # abs on an integer param
    assert inst.norm == 1.0 and inst.value == inst.hi
    assert rig.midi._slews == {}


def test_turning_smoothing_off_or_losing_the_port_lands_every_glide(rig):
    """Both roads out: `desk.slew` set to 0 mid-glide lands every glide on
    the next poll (`_glide`), and so does the port going away
    (`_land_all`) — each on the detent the knob was sending it to. A glide
    someone else has ended is not landed by either."""
    reg = rig.reg
    mix, amp, rate = reg["view.pattern_mix"], reg["view.inst_amp"], reg["view.inst_rate"]

    def start(at):
        for p in (mix, amp, rate):
            p.set_norm(0.0)
        at(TICK)
        at(2 * TICK, cc(K_MIX, 90), cc(0x34, 40), cc(0x35, 127))
        at(3 * TICK)
        assert set(rig.midi._slews) == {mix.id, amp.id, rate.id}
        assert 0 < mix.norm < 0.71 and 0 < amp.norm < 0.31
        rate.set_norm(0.02)                         # someone else's: stands
    at = slew_rig(rig)
    start(at)
    reg["desk.slew"].set(0.0)
    at(4 * TICK)
    assert (mix.norm, amp.norm, rate.norm) == (0.71, 0.31, 0.02) and rig.midi._slews == {}
    at = slew_rig(rig)
    start(at)
    rig.midi.ports.inp = rig.midi.ports.out = None  # the device is gone
    at(4 * TICK)
    assert not rig.midi.on
    assert (mix.norm, amp.norm, rate.norm) == (0.71, 0.31, 0.02) and rig.midi._slews == {}


def test_a_glide_on_a_hand_owned_param_moves_the_return_value(rig):
    """A knob on a param a performer holds is still a scene-setter: the
    glide writes the base (`Param.set`, then `set_norm`) under a live
    position-style offset, the effective value stays the performer's all
    the way, and when the performer leaves the param is where the knob
    put it. The adapter never calls `Param.modulate`
    (tests/test_routing_boundary.py pins that for the whole module)."""
    reg, mix = rig.reg, rig.reg["view.pattern_mix"]
    mix.set_norm(0.0)
    at = slew_rig(rig)
    hand = 0.9                                      # where the hand holds the param

    def perform(t, *msgs):                         # the frame: midi, the performer, apply
        at(t, *msgs)
        mix.modulate(hand - mix.norm)               # a position row lands the reading
        reg.apply()

    perform(TICK)
    assert mix.modulated and mix.eff_norm == pytest.approx(hand)
    bases = []
    perform(2 * TICK, cc(K_MIX, 50))
    for k in range(3, 10):
        bases.append(mix.norm)
        assert mix.modulated and mix.eff_norm == pytest.approx(hand)
        perform(k * TICK)
    assert bases == sorted(bases) and len(set(bases)) == len(bases)   # the base glides
    perform(10 * TICK)
    assert mix.norm == 0.39 and mix.eff_norm == pytest.approx(hand)
    assert rig.midi._slews == {}
    reg.apply()                                     # the hand leaves: the knob's value
    assert not mix.modulated and mix.value == pytest.approx(0.39)


def test_a_param_that_moves_on_its_own_is_written_at_once(rig):
    """Review of PR #98: `rot.phase.*` is the integrator's angle and moves
    every frame while its plane turns, so a glide on it would look
    foreign-written the next poll, be dropped, and never arrive. The first
    message finds that out (one partial step); from then on the knob
    writes the phase at once, as with smoothing off. A param that holds
    still is unaffected."""
    reg, view = rig.reg, rig.view
    phase, mix = reg["rot.phase.XY"], reg["view.pattern_mix"]
    rig.midi.table.add(Binding("cc:0:60", "rot.phase.XY", "abs", layer="preset", pickup=False))
    at = slew_rig(rig)

    def turning(t, *msgs):                         # the plane turns between polls
        view.ang[0] += 0.01
        at(t, *msgs)

    turning(TICK, cc(60, 127))
    assert "rot.phase.XY" in rig.midi._slews
    turning(2 * TICK)
    assert rig.midi._slews == {} and rig.midi._restless == {"rot.phase.XY"}
    turning(3 * TICK, cc(60, 32))                  # now: where set_norm puts it, this poll
    landed = phase.value
    phase.set_norm(32 / 127)
    assert phase.value == pytest.approx(landed) and rig.midi._slews == {}
    mix.set_norm(0.0)
    turning(4 * TICK)                              # (the ring re-bases the knob there)
    turning(5 * TICK, cc(K_MIX, 127))              # a still param glides as ever
    assert 0.0 < mix.norm < 1.0 and list(rig.midi._slews) == ["view.pattern_mix"]


def test_a_load_from_a_pad_ends_a_glide_before_it_steps(rig):
    """Review of PR #98: a knob message and a pad that loads a preset in
    one poll. The load's desk replacement is followed before the glides
    step, so the glide the knob just aimed is gone and the value the load
    left stands — even though it equals what the glide last saw."""
    reg, t = rig.reg, rig.midi.table
    mix = reg["view.pattern_mix"]
    mix.set_norm(0.3)
    reg.trigger("test.load", "Load", lambda: t.set_desk(t.desk()))   # a load that moves nothing
    t.add(Binding("note:0:121", "test.load", "toggle"))
    at = slew_rig(rig)
    at(TICK, cc(K_MIX, 127), note(121))
    assert mix.norm == 0.3 and rig.midi._slews == {}
    for k in range(2, 12):
        at(k * TICK)
    assert mix.norm == 0.3


def test_closing_the_adapter_lands_every_glide(rig):
    """Review of PR #98: nothing is left between detents when the app
    quits inside the glide's time."""
    dim = rig.reg["output.dim"]
    push(rig, cc(apc40.CC_XFADE, 127))
    at = slew_rig(rig)
    at(TICK, cc(apc40.CC_XFADE, 64))
    at(2 * TICK)
    assert 0.5 < dim.norm < 1.0
    rig.midi.close()
    assert dim.norm == 0.5 and rig.midi._slews == {}


# ------------------------------------------- plan 19 WP2: the bank's lights

def test_a_bank_pad_is_green_loaded_amber_filled_and_dark_empty(rig, monkeypatch):
    """Fork 5: the velocities sent for a bank pad's three states — GREEN
    (1) for the loaded preset's slot, YELLOW (5) for a slot that holds
    another preset, 0 for an empty one — on rows 1, 4 and 5 alike, and
    the same under SHIFT. A load moves the green; a cleared slot goes
    dark; a filled one comes up amber. `filled_of` answering None (the
    way to turn the third state off) leaves a filled pad dark."""
    from hyperspace import routing

    pr = rig.presets

    def led(k):
        n, ch = apc40.BANK_PADS[k]
        return leds(rig, n, ch)[-1]
    assert (apc40.GREEN, apc40.YELLOW) == (1, 5)
    assert apc40.filled_of(apc40.N_CLIP[3], apc40.GREEN) == apc40.YELLOW
    assert apc40.filled_of(apc40.N_CLIP[1], apc40.YELLOW) is None      # no third state of its own
    assert apc40.filled_of(apc40.N_OVERDUB, 1) is None                 # nor off the clip grid
    rig.midi.poll()
    # the party show as a fresh home has it: nine filled, nothing loaded yet
    assert all(pr.bank[:9]) and pr.bank[9:] == [None] * 15 and pr.active == -1
    assert [led(k) for k in range(24)] == [apc40.YELLOW] * 9 + [0] * 15
    # the rule the lights read, as levels
    p = rig.reg["preset.select"]
    row = {int(b.value): b for b in rig.midi.bindings if b.target == "preset.select"}
    assert [routing.led_level(row[k], p) for k in (0, 8, 9)] == [1, 1, 0]
    # a press on row 4's first pad loads slot 9: green there, amber elsewhere
    n, ch = apc40.BANK_PADS[8]
    push(rig, note(n, channel=ch), note(n, 0, channel=ch))
    assert pr.active == 8 and pr.lib.current("presets") == "TRACER"
    assert [routing.led_level(row[k], p) for k in (0, 8, 9)] == [1, 2, 0]
    assert [led(k) for k in range(24)] == [apc40.YELLOW] * 8 + [apc40.GREEN] + [0] * 15
    # a load from row 1 moves the green; slot 9 falls back to amber
    push(rig, note(apc40.N_CLIP[0], channel=2), note(apc40.N_CLIP[0], 0, channel=2))
    assert [led(k) for k in (2, 8, 0, 9)] == [apc40.GREEN, apc40.YELLOW, apc40.YELLOW, 0]
    # a slot filled from the page comes up amber; a cleared one goes dark
    pr.put_slot(20, "WAKE")
    pr.clear_slot(8)
    rig.midi.poll()
    assert [led(k) for k in (20, 8, 2)] == [apc40.YELLOW, 0, apc40.GREEN]
    # the same under SHIFT: the bank rows are invariant, the redraw re-sends them
    mark = len(rig.out.sent)
    shift(rig)
    for k, want in ((2, apc40.GREEN), (20, apc40.YELLOW), (0, apc40.YELLOW)):
        n, ch = apc40.BANK_PADS[k]
        assert leds(rig, n, ch, mark)[-1] == want, k
    for k in (8, 9, 23):                    # an empty slot's pad: dark (0, or never lit)
        n, ch = apc40.BANK_PADS[k]
        assert set(leds(rig, n, ch, mark)) <= {0}, k
    shift(rig)
    # the scene pads (yellow when selected) and the motion pads have no third state
    assert not [m for m in rig.out.sent if m.type == "note_on" and m.velocity == apc40.YELLOW
                and m.note in (apc40.N_CLIP[1], apc40.N_CLIP[2])
                and rig.reg["scene.select"].value != m.channel + 8 * (m.note == apc40.N_CLIP[2])]
    # fork 5's way back: no "filled" velocity, and a filled pad is dark again
    monkeypatch.setattr(apc40, "filled_of", lambda number, on: None)
    rig.midi.redraw()
    assert [led(k) for k in (2, 20, 0)] == [apc40.GREEN, 0, 0]


def test_save_as_blinks_the_new_pad_on_row_four(rig):
    """Plan 15 row 42, now on rows 4–5 too: with F1–F8 and slot 9 full the
    hold on the clip-stop row lands in slot 10 — row 4, pad 2 — and that
    pad blinks green with the bar for BLINK_S (`blink_of`), then shows
    green; the pad of the preset that was up falls to amber. The same
    under SHIFT, into slot 11."""
    from hyperspace import midi

    at, fires = bar_rig(rig)
    pr = rig.presets
    assert pr.next_empty() == 9                                     # slot 10
    pad = apc40.N_CLIP[0]
    push(rig, note(pad, channel=4), note(pad, 0, channel=4))        # TRIP, on F5
    assert leds(rig, pad, 4)[-1] == apc40.GREEN
    n10, ch10 = apc40.BANK_PADS[9]
    assert (n10, ch10) == (apc40.N_CLIP[3], 1) and leds(rig, n10, ch10)[-1] == 0
    assert apc40.blink_of(n10, apc40.GREEN) == apc40.GREEN_BLINK
    mark = len(rig.out.sent)
    at(1.0, note(STOP, channel=6))
    at(1.5)
    assert leds(rig, n10, ch10, mark) == []
    at(1.65)                                                        # held HOLD_S: the save
    assert fires == [1.65] and pr.bank[9] == "TRIP 2" and pr.active == 9
    assert pr.lib.status == "saved TRIP 2 → slot 10"
    assert leds(rig, n10, ch10, mark) == [apc40.GREEN_BLINK]        # the new slot's pad
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2]] * 8     # and the bar
    assert leds(rig, pad, 4, mark) == [apc40.YELLOW]                # TRIP: filled, not loaded
    others = [k for k in range(24) if k not in (4, 9)]
    assert [leds(rig, *apc40.BANK_PADS[k], mark) for k in others] == [[]] * 22
    at(1.65 + midi.BLINK_S - 0.01, note(STOP, 0, channel=6))
    assert leds(rig, n10, ch10, mark) == [apc40.GREEN_BLINK]
    at(1.65 + midi.BLINK_S)
    assert leds(rig, n10, ch10, mark) == [apc40.GREEN_BLINK, apc40.GREEN]
    assert [leds(rig, STOP, k, mark) for k in range(8)] == [[1, 2, 0]] * 8
    # under SHIFT: the bar and the bank are invariant — slot 11, row 4 pad 3
    shift(rig)
    n11, ch11 = apc40.BANK_PADS[10]
    mark = len(rig.out.sent)
    at(10.0, note(STOP, channel=0))
    at(10.65)
    assert pr.bank[10] == "TRIP 3" and pr.active == 10
    assert leds(rig, n11, ch11, mark) == [apc40.GREEN_BLINK]
    assert leds(rig, n10, ch10, mark) == [apc40.YELLOW]
    at(10.65 + midi.BLINK_S, note(STOP, 0, channel=0))
    assert leds(rig, n11, ch11, mark) == [apc40.GREEN_BLINK, apc40.GREEN]


# --------------------------------- plan 19 WP3: the fresh layer's device knobs

def test_a_knob_on_the_pattern_steps_through_every_pattern(rig):
    """The gate for D4 (plan 19 WP3): `view.pattern` is an enum on an
    absolute knob. Turned from one end to the other and back, it lands on
    every pattern, one step at a time, in order — never a skip, never a
    jump back — each value where `set_norm` puts it, and the ring follows
    the pattern the knob landed on. The knob smoothing never glides an
    enum (it is a discrete target), so each turn lands at once."""
    from hyperspace.params import PATTERNS

    m = rig.midi
    m.table.slew = 0.12                               # smoothing on, as in the app
    (row,) = [b for b in m.table.desk() if b.source == "cc:*:19"]
    assert (row.target, row.op, row.feedback, row.layer) == ("view.pattern", "abs", "ring",
                                                             "preset")
    p = rig.reg["view.pattern"]
    n = len(PATTERNS)
    assert p.kind is Kind.ENUM and p.steps == n - 1 == 11
    for x in m.bindings:
        x.pickup = False
    seen: list[int] = []
    for v in [*range(128), *range(127, -1, -1)]:
        push(rig, cc(0x13, v))
        k = int(p.value)
        assert k == round(v / 127 * (n - 1)), v
        rings = [msg.value for msg in rig.out.sent
                 if msg.type == "control_change" and msg.control == 0x13]
        assert rings[-1] == round(k / (n - 1) * 127), v           # the ring: where it landed
        if not seen or seen[-1] != k:
            seen.append(k)
    up = seen[:n]
    assert up == list(range(n))                                   # every pattern, in order
    assert seen[n - 1:] == list(range(n - 1, -1, -1))             # and back down
    assert rig.view.pattern == 0
