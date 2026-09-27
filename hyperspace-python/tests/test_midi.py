"""MIDI adapter: routing, pickup, feedback, learn — no hardware, fake ports."""

from types import SimpleNamespace

import mido
import pytest

from hyperspace import apc40
from hyperspace.analysis import Analyser
from hyperspace.bands import Chain
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.midi import PICKUP_TOL, Binding, MidiIO, MidiMap
from hyperspace.overlay import Output
from hyperspace.params import Kind, build_registry
from hyperspace.render import ViewState


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
    chain = Chain(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(tmp_path)
    presets = lib.bank
    reg = build_registry(view, control, audio, presets)
    lib.attach(reg)
    reg.toggle("ui.panel", "Panel", lambda: True, lambda v: None)
    reg.toggle("ui.cheatsheet", "Sheet", lambda: True, lambda v: None)
    reg.toggle("audio.mic", "Mic", lambda: False, lambda v: None)
    reg.trigger("audio.restart", "Restart", lambda: None)
    reg.trigger("audio.stop", "Stop", lambda: None)
    reg.toggle("audio.play", "Play", lambda: False, lambda v: None)
    Output(None, None).register(reg)
    inp, out = FakeIn(), FakeOut()
    m = MidiIO(reg, MidiMap(tmp_path / "midi_map.json"), inp=inp, out=out)
    return SimpleNamespace(reg=reg, view=view, control=control, audio=audio,
                           presets=presets, midi=m, inp=inp, out=out)


def push(r, *msgs):
    r.inp.queue.extend(msgs)
    r.midi.poll()


# ---------------------------------------------------------------- default map

def test_default_map_binds_only_real_params(rig):
    ids = set(rig.reg.ids())
    for b in rig.midi.map.bindings:
        assert b.target in ids, b
        if b.op == "set" and rig.reg[b.target].kind is Kind.ENUM:
            assert 0 <= int(b.value) < len(rig.reg[b.target].names), b


def test_default_map_has_no_two_controls_on_one_key(rig):
    keys = [b.key for b in rig.midi.map.bindings]
    assert len(keys) == len(set(keys))


def test_power_up_sends_mode_sysex(rig):
    first = rig.out.sent[0]
    assert first.type == "sysex" and list(first.data)[:6] == [0x47, 0x7F, 0x73, 0x60, 0, 4]
    assert list(first.data)[6] == apc40.MODE_LIVE_ALT


# ---------------------------------------------------------------- knobs

def test_device_knob_drives_selected_band_with_pickup(rig):
    reg, control = rig.reg, rig.control
    atk = reg["band.sel.atk"]
    assert atk.norm != pytest.approx(0.0)
    push(rig, cc(0x15, 0))            # far from the value: not caught yet
    assert atk.norm != pytest.approx(0.0)
    cur = atk.norm
    push(rig, cc(0x15, 127))          # swept past it: caught, and applied
    assert atk.norm == pytest.approx(1.0)
    push(rig, cc(0x15, 64))
    assert atk.position() == round(64 / 127 * atk.steps)
    # switching band moves the alias under the knob: pickup re-arms
    control.selb = 3
    before = reg["band.3.atk"].norm
    push(rig, cc(0x15, 10))
    assert reg["band.3.atk"].norm == pytest.approx(before)
    assert cur != 0  # silence the unused warning


def test_pickup_catches_when_knob_reaches_value(rig):
    b = rig.reg["view.bright"]
    b.set_norm(0.5)
    target = round(0.5 * 127)
    push(rig, cc(0x30, target))       # exactly on it
    assert b.norm == pytest.approx(target / 127, abs=PICKUP_TOL)
    push(rig, cc(0x30, target + 20))
    assert b.norm == pytest.approx((target + 20) / 127, abs=PICKUP_TOL)


def test_fader_without_pickup_jumps(rig):
    for x in rig.midi.map.bindings:
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
    for x in rig.midi.map.bindings:
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


def test_theme_grid_lights_the_active_theme(rig):
    push(rig, note(apc40.N_CLIP[0], channel=2))
    assert rig.presets.active == 2
    leds = {(m.channel, m.note): m.velocity for m in rig.out.sent if m.type == "note_on"}
    assert leds[(2, apc40.N_CLIP[0])] == apc40.GREEN
    assert leds[(0, apc40.N_CLIP[0])] == 0


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
    rig.midi.poll()
    assert ring(0x17) == round(0.1 * 127)
    rig.control.selb = 2
    rig.midi.poll()
    assert ring(0x17) == round(0.9 * 127)


# ---------------------------------------------------------------- learn

def test_learn_binds_next_message_and_persists(rig, tmp_path):
    m = rig.midi
    m.learn("view.inst_amp")
    assert m.learning == "view.inst_amp"
    push(rig, cc(0x57, 40))                   # send-A knob-ish: an unused CC
    assert m.learning is None
    b = m.binding_for("view.inst_amp")
    assert b is not None and b.kind == "cc" and b.number == 0x57 and b.op == "abs"
    assert "CC 87" in b.describe()
    # the learning message itself did not move the param
    assert rig.view.inst_amp == 0.25
    # persisted, and read back by a fresh map
    m2 = MidiMap(tmp_path / "midi_map.json")
    assert any(x.target == "view.inst_amp" and x.number == 0x57 for x in m2.bindings)
    # the old track-knob binding for the same param is gone
    assert not any(x.target == "view.inst_amp" and x.number == 0x34 for x in m2.bindings)


def test_learn_a_button_on_a_toggle(rig):
    m = rig.midi
    m.learn("view.lines")
    push(rig, note(apc40.N_METRO, 0))         # a release is not a binding
    assert m.learning == "view.lines"
    push(rig, note(apc40.N_METRO))
    b = m.binding_for("view.lines")
    assert b.kind == "note" and b.number == apc40.N_METRO and b.feedback == "led"
    push(rig, note(apc40.N_METRO, 0), note(apc40.N_METRO))
    assert not rig.view.lines                  # was True by default, flipped once


def test_learn_takes_over_a_key_from_its_old_param(rig):
    m = rig.midi
    m.learn("view.pattern_mix")
    push(rig, cc(0x30, 64))                   # the brightness knob
    assert not [x for x in m.map.bindings if x.target == "view.bright" and x.kind == "cc"]
    assert m.binding_for("view.bright").kind == "note"  # its step buttons survive
    assert m.binding_for("view.pattern_mix").number == 0x30
    m.unbind("view.pattern_mix")
    assert m.binding_for("view.pattern_mix") is None
    push(rig, cc(0x30, 10))                   # now nothing listens
    assert rig.view.pattern_mix == 1.0


def test_relative_cc_learn_keeps_encoder_mode(rig):
    rig.midi.learn("view.instances")
    push(rig, cc(apc40.CC_CUE, 1))
    assert rig.midi.binding_for("view.instances").op == "rel"


def test_learn_source_writes_a_position_route(rig, tmp_path):
    """Another adapter's source (a hand) completing a learn: a `position`
    row at depth 1 through the table's referee, written to the file; the
    MIDI view never sees it. On an owned target it is held in `pending`."""
    from hyperspace.routing import Bindings

    m = rig.midi
    m.learn("view.inst_amp")
    m.learn_source("hand:3", when="hand:14")
    assert m.learning is None and m.pending is None
    b = m.map.table.owner("view.inst_amp")
    assert (b.source, b.op, b.value, b.when, b.pickup) == ("hand:3", "position", 1.0, "hand:14", True)
    assert m.binding_for("view.inst_amp").is_midi            # the knob row is still there
    assert "learned view.inst_amp" in m.last
    assert Bindings.load(tmp_path / "midi_map.json").owner("view.inst_amp") == b
    m.learn("view.inst_amp")
    m.learn_source("hand:7")
    assert m.pending is not None and m.pending[1] is b and "replace?" in m.last
    assert m.map.table.owner("view.inst_amp") is b
    m.learn("no.such.param")
    m.learn_source("hand:7")                                  # unknown target: nothing
    assert m.learning is None and m.map.table.owner("no.such.param") is None


# ---------------------------------------------------------------- map file

def test_map_round_trips_json(tmp_path):
    path = tmp_path / "m.json"
    mm = MidiMap(path)
    n = len(mm.bindings)
    mm.bind(Binding("pitch:3", "view.zoom", "abs"))
    mm2 = MidiMap(path)
    assert len(mm2.bindings) == n + 1
    b = mm2.for_param("view.zoom")
    assert b.kind == "pitch" and b.channel == 3 and not hasattr(b.to_json(), "caught")
    assert "caught" not in b.to_json()


def test_pitch_bend(rig):
    rig.midi.map.bind(Binding("pitch:0", "camera.pitch", "abs", pickup=False))
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
