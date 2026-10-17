"""Plan 27 B2 — the existing inputs on the device registry.

Driven through `devices.DeviceRegistry` over `[[devices]]` entries, with
MIDI ports the tests plug in by name (mido's port lookup replaced by a
fake bus, so a desk can be missing at launch and plugged in later):

- **several MIDI ports, each with its own profile**: the APC40 (`apc40`)
  and a second controller (`generic`: plain CC / note / pitch, no
  feedback) both open; an unqualified row is the first MIDI role's, the
  second desk's rows carry its role (``cc@launch:0:7``); a generic desk
  maps on the desk's Learn with no code;
- **the latch per role**: SHIFT is the first role's (`desk.shift`); the
  second desk keeps its own layer, so a learn on it is not refused while
  the APC40 shows the global layer, and its rows act either way;
- **a missing desk** is `lost`, its rows wait, and plugging it in brings it
  up with its feedback;
- **the pad and the hands** run on the registry: the pad publishes its
  axes, delivers its rows and runs the sticks' camera job itself; the
  hands feed `hand` and `hands` through `hands/device.py`;
- **schemes from the registry**: the router's continuous schemes and their
  order, the learn's wants, the referee's row schemes;
- **nothing old moves**: a pre-run `bindings.json` and every factory preset
  load with no note and no dirt with two desks listed.
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from test_midi import cc, note

import hyperspace.gamepad as gp
from hyperspace import apc40, devices, hands, lfo, midi, routing, tempo, ui, ui_routing
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.learn import Learn, blocked
from hyperspace.library import Library
from hyperspace.overlay import Output
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import SHIFT_PARAM, Binding, Bindings, Router, bindings_path
from hyperspace.view import ViewState

APC, LAUNCH = "Akai APC40", "Launch Control XL"


class Port:
    """One fake MIDI port, both directions: what a test pushes, what the
    app sent."""

    def __init__(self):
        self.queue: list = []
        self.sent: list = []
        self.closed = False

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)

    def send(self, msg):
        self.sent.append(msg)

    def close(self):
        self.closed = True


class Bus:
    """The system's MIDI ports, by name: `plug` one and mido finds it."""

    def __init__(self, monkeypatch):
        self.ports: dict[str, Port] = {}
        m = midi.mido
        monkeypatch.setattr(m, "get_input_names", lambda: list(self.ports))
        monkeypatch.setattr(m, "get_output_names", lambda: list(self.ports))
        monkeypatch.setattr(m, "open_input", lambda name: self.ports[name])
        monkeypatch.setattr(m, "open_output", lambda name: self.ports[name])

    def plug(self, name: str) -> Port:
        self.ports[name] = Port()
        return self.ports[name]


class ScriptedPad(gp.Pad):
    """A real Pad whose frames are scripted; `poll` reads nothing (no GLFW)."""

    def __init__(self, usb: bool = False):
        super().__init__(usb=False)
        self.source = "usb"

    def poll(self) -> None:
        pass

    def frame(self, held=(), hat=0, axes=None) -> None:
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons = [1 if i in held else 0 for i in range(gp.N_BUTTONS)]
        self.hat = hat
        self.axes = list(axes) if axes is not None else [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]


class HandSource:
    """A tracker giving one right hand, palm at `y` mm."""

    status, on = "fake", True

    def __init__(self):
        self.y = 200.0
        self.n = 0

    def latest(self):
        palm = NS(x=0.0, y=self.y, z=0.0)
        h = NS(type=NS(name="Right"), confidence=1.0, grab_strength=0.0, pinch_strength=0.0,
               grab_angle=0.0, pinch_distance=80.0,
               palm=NS(position=palm, normal=NS(x=0.0, y=-1.0, z=0.0),
                       direction=NS(x=0.0, y=0.0, z=-1.0), width=90.0))
        self.n += 1
        return self.n, 0.0, {"right": (hands.features(h), 1.0)}


def entries(*extra: dict, apc: bool = True, launch: bool = True) -> list[dict]:
    """The rig as checked `[[devices]]` entries: the APC40 first, a generic
    second desk, the pad and the hands off unless `extra` says."""
    out = []
    if apc:
        out.append({"role": "apc40", "kind": "midi", "enabled": True, "port": "APC40",
                    "profile": "apc40"})
    if launch:
        out.append({"role": "launch", "kind": "midi", "enabled": True, "port": "Launch",
                    "profile": "generic"})
    return out + list(extra)


@pytest.fixture()
def build(tmp_path, monkeypatch):
    """`build(entries, plug=(…))`: the host's pieces over a scratch
    library, the registry opened behind the entries, ports plugged first."""
    bus = Bus(monkeypatch)
    monkeypatch.setattr(gp, "Pad", ScriptedPad)
    real_io = hands.HandsIO
    tracker = HandSource()
    monkeypatch.setattr(hands, "HandsIO", lambda settings, cfg, cal_path=None: real_io(
        settings, {**cfg, "out": ""}, source=tracker, out=None))

    def make(ents, plug=(APC, LAUNCH), bindings: str | None = None):
        for name in plug:
            bus.plug(name)
        chain = Analyzer(Analyser())
        control = Control(chain)
        audio = NS(chain=chain, on=False)
        lib = Library(tmp_path)
        reg = build_registry(ViewState(), control, audio, lib.project)
        lib.attach(reg)
        reg.toggle("ui.panel", "Panel", lambda: True, lambda v: None)
        reg.toggle("ui.cheatsheet", "Sheet", lambda: True, lambda v: None)
        reg.trigger("audio.restart", "Restart", lambda: None)
        reg.trigger("audio.stop", "Stop", lambda: None)
        reg.toggle("audio.play", "Play", lambda: False, lambda v: None)
        Output(None, None).register(reg)
        clock = tempo.Clock(now=lambda: 0.0)
        tempo.register(reg, clock)
        lfo.register(reg, lfo.LFOs(), clock)
        settings = hands.HandSettings.from_config({})
        hands.register(reg, settings)
        path = bindings_path(tmp_path)
        if bindings is not None:
            path.write_text(bindings)
        table = Bindings.load(path, legacy_midi=None)
        router = Router(reg, table)
        learn = Learn(reg, table, lane=router.lane)
        notes: list[str] = []
        rig = devices.DeviceRegistry(ents, devices.Context(
            reg=reg, table=table, learn=learn, audio=audio, hand_settings=settings, notes=notes))
        router.use(rig)
        learn.devices = rig
        rig.open_all()
        presets = Presets(lib, reg, router)
        return NS(reg=reg, table=table, router=router, learn=learn, devices=rig, lib=lib,
                  presets=presets, bus=bus, notes=notes, path=path, tracker=tracker)
    return make


def frame(r, dt: float = 1 / 60, now: float = 1.0) -> None:
    """One frame's device slots: the scene-setters, then the feeds."""
    r.devices.poll(dt, now, router=r.router, learn=r.learn)
    r.devices.feed(r.router)


def push(r, port: str, *msgs) -> None:
    r.bus.ports[port].queue.extend(msgs)
    frame(r)


# ---------------------------------------------------------------- the qualifier

def test_a_qualified_source_is_its_roles_and_adds_no_colon():
    """`cc@<role>:<ch>:<n>` (register row 1xx): the scheme is still `cc`,
    the role is the qualifier, the address parts are unchanged — so every
    reader that splits at the first `:` keeps working — and two rows on
    the same numbers of two devices are two controls."""
    b = Binding("cc@launch:0:7", "view.bright", "abs")
    assert (b.scheme, b.kind, b.device, b.channel, b.number) == ("cc", "cc", "launch", 0, 7)
    assert b.is_midi and not b.is_performer and b.bare == "cc:0:7"
    assert b.describe() == "MIDI CC 7 ch1 on launch"
    assert Binding.midi_source("cc", 0, 7, "launch") == "cc@launch:0:7"
    assert Binding.midi_source("pitch", 3, role="launch") == "pitch@launch:3"
    assert Binding.midi_source("note", None, 60) == "note:*:60"         # unqualified as ever
    p = Binding("pitch@launch:3", "x", "abs")
    assert (p.scheme, p.device, p.channel) == ("pitch", "launch", 3)
    plain = Binding("cc:0:7", "view.speed", "abs")
    assert plain.device == "" and plain.bare == "cc:0:7"
    assert not b.overlaps(plain) and not plain.overlaps(b)
    assert b.overlaps(Binding("cc@launch:*:7", "view.speed", "abs"))
    assert b.matches("cc", 0, 7)                     # (the table picks the device: `serves`)
    # plan 27 B6: any scheme takes the qualifier (it was MIDI's only), and
    # the qualified head stays the Router key its lanes are read under
    h = Binding("hand@x:1", "x", "push")
    assert (h.scheme, h.device, h.head, h.bare) == ("hand", "x", "hand@x", "hand:1")
    assert routing.is_continuous("hand") and routing.is_continuous("osc")
    assert not routing.is_continuous("cc@launch") and not routing.is_continuous("pad")


def test_an_unqualified_row_is_the_first_midi_roles():
    """The rule that keeps every row written before plan 27: `cc:0:7`
    means the first MIDI role listed — whatever profile it has — and a
    row qualified with that role's name means it too; a second role reads
    only its own qualified rows."""
    t = Bindings([Binding("cc:0:7", "view.speed", "abs"),
                  Binding("cc@apc40:0:7", "view.bright", "abs"),
                  Binding("cc@gen:0:7", "view.inst_amp", "abs")])
    # a table told no roles (a bare one, the tests'): the unqualified rows
    # are its one desk's, a qualified row some other device's
    assert [b.target for b in t.dispatch("cc", 0, 7)] == ["view.speed"]
    t.midi_roles = ("gen", "apc40")                  # a rig listing the generic desk first
    assert [b.target for b in t.dispatch("cc", 0, 7, "gen")] == ["view.speed", "view.inst_amp"]
    assert [b.target for b in t.dispatch("cc", 0, 7, "apc40")] == ["view.bright"]
    assert [b.target for b in t.dispatch("cc", 0, 7)] == ["view.speed", "view.inst_amp"]
    t.midi_roles = ("apc40", "gen")
    assert [b.target for b in t.dispatch("cc", 0, 7, "apc40")] == ["view.speed", "view.bright"]
    assert [b.target for b in t.dispatch("cc", 0, 7, "gen")] == ["view.inst_amp"]
    assert t.role_of(t.bindings[0]) == "apc40" and t.role_of(t.bindings[2]) == "gen"


# ---------------------------------------------------------------- two desks

def test_two_desks_open_each_with_its_profile_and_its_own_rows(build):
    """The APC40 and a generic second desk both open on the registry; the
    table knows their order; the APC40 gets its power-up and its lights,
    the generic desk is sent nothing at all (no feedback)."""
    r = build(entries())
    apc, launch = r.devices.get("apc40"), r.devices.get("launch")
    assert r.table.midi_roles == ("apc40", "launch")
    assert apc.status == "connected" and launch.status == "connected"
    assert apc.io.profile is apc40 and launch.io.profile.__name__ == "hyperspace.generic"
    assert apc.io.qualifier == "" and launch.io.qualifier == "launch"
    assert apc.layers == ("preset", "global") and launch.layers == ("preset",)
    out_apc, out_launch = r.bus.ports[APC].sent, r.bus.ports[LAUNCH].sent
    assert out_apc[0].type == "sysex" and len(out_apc) > 50       # mode, then the whole desk
    assert out_launch == []                                        # a generic desk: nothing
    assert len(launch.io.bindings) == 0 < len(apc.io.bindings)     # no factory rows of its own
    assert len(apc.sources) == len(apc40.LAYOUT) and launch.sources == ()
    lines = ui.device_lines(r.devices)
    assert lines[0].startswith("apc40  ·  midi  ·  connected  ·  ")
    assert lines[1].startswith("launch  ·  midi  ·  connected  ·  0 sources  ·  Launch Control XL")
    # the APC40's crossfader still dims through its invariant row, the
    # generic desk's CC 15 does nothing (no row of its own)
    dim = r.reg["output.dim"]
    push(r, LAUNCH, cc(apc40.CC_XFADE, 0))
    assert dim.value == pytest.approx(1.0)
    r.devices.close()
    assert r.bus.ports[LAUNCH].sent == []                          # not even a leave
    assert r.bus.ports[APC].sent[-1].type == "sysex"               # the APC40's leave


def test_a_generic_desk_maps_on_the_desks_learn_with_no_code(build):
    """The acceptance: Learn desk, a knob on the second controller — the
    row is `cc@launch:…`, a preset-layer `abs` row with soft pickup and no
    feedback, into the loaded preset (dirty, no file written) — and from
    then on that knob drives the param while the same CC on the APC40 does
    not, and the reverse. A note learns as a toggle; the same Learn
    completes from the APC40 too."""
    r = build(entries())
    lib, t = r.lib, r.table
    lib.load("presets", lib.list("presets")[0])
    assert not lib.is_dirty("presets")
    before = r.path.read_bytes() if r.path.exists() else None
    knob = Binding(f"cc:0:{apc40.DEVICE_KNOBS[7]}", "view.inst_amp", "abs", layer="preset")
    t.bind(knob, write=False)                      # the param's knob on the APC40…
    r.learn.arm("view.inst_amp", "desk")
    push(r, LAUNCH, cc(21, 90))
    assert any(x is knob for x in t.bindings)      # …stays: one knob per param per desk
    (b,) = [b for b in t.bindings if b.target == "view.inst_amp" and b.device]
    assert (b.source, b.op, b.layer, b.feedback, b.pickup) == (
        "cc@launch:0:21", "abs", "preset", None, True)
    assert r.learn.learning is None and "learned view.inst_amp" in r.learn.last
    assert lib.is_dirty("presets")                                 # into the preset…
    assert (r.path.read_bytes() if r.path.exists() else None) == before   # …not the file
    amp = r.reg["view.inst_amp"]
    for v in (60, 40):                     # soft pickup: crossing the base catches it
        push(r, LAUNCH, cc(21, v))
    push(r, LAUNCH, cc(21, 30))
    assert amp.norm == pytest.approx(30 / 127, abs=0.01)
    push(r, APC, cc(21, 127))              # the APC40's CC 21 is not that row
    assert amp.norm == pytest.approx(30 / 127, abs=0.01)
    r.learn.arm("view.points", "desk")
    push(r, LAUNCH, note(40), note(40, 0))
    (n,) = [x for x in t.bindings if x.source == "note@launch:0:40"]
    assert (n.target, n.op, n.layer) == ("view.points", "toggle", "preset")
    pts = r.reg["view.points"].value
    push(r, LAUNCH, note(40), note(40, 0))
    assert r.reg["view.points"].value != pts
    assert r.bus.ports[LAUNCH].sent == []          # still nothing sent to it
    # the preset's desk carries the qualified rows through a save and a load
    rows = [x.to_json() for x in t.desk()]
    assert {"source": "cc@launch:0:21", "target": "view.inst_amp", "op": "abs",
            "layer": "preset"} in rows
    assert t.set_desk(rows) == [] and any(x.source == "cc@launch:0:21" for x in t.desk())


def test_the_latch_is_per_role(build):
    """SHIFT is the first role's latch (`desk.shift`): with the APC40 on
    its global layer, the second desk is still on its preset layer — its
    rows act and a learn on it lands (D5 refuses only the APC40's). Its
    layer is its own (`set_layer(…, role)`); a preset load drops every
    role to the preset layer (D4); a press and its release on the second
    desk belong to the layer that was up at the press (D12)."""
    r = build(entries())
    t, shift = r.table, r.reg[SHIFT_PARAM]
    push(r, APC, note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert shift.value is True and t.layer_of("apc40") == "global"
    assert t.layer_of("launch") == "preset"
    assert blocked(t, "cc:0:21") == "global" and blocked(t, "cc@launch:0:21") is None
    r.learn.arm("view.inst_amp", "desk")
    push(r, APC, cc(apc40.TRACK_KNOBS[0], 70))      # an APC40 knob: the global layer's
    assert r.learn.learning == "view.inst_amp"
    push(r, LAUNCH, cc(22, 70))                     # the second desk: learned
    assert any(x.source == "cc@launch:0:22" for x in t.desk())
    # the second desk's own layer, and D12 across a flip of it
    t.add(Binding("note@launch:0:50", "view.faces", "momentary", layer="preset"))
    t.add(Binding("note@launch:0:50", "view.lines", "momentary", layer="global"))
    faces, lines = r.reg["view.faces"], r.reg["view.lines"]
    l0 = lines.value
    push(r, LAUNCH, note(50))
    assert faces.value is True
    t.set_layer("global", "launch")
    assert t.layer_of("launch") == "global" and t.layer_of("apc40") == "global"
    push(r, LAUNCH, note(50, 0))                    # the release goes where the press went
    assert faces.value is False and lines.value == l0
    push(r, LAUNCH, note(50))
    assert lines.value is True and faces.value is False
    push(r, LAUNCH, note(50, 0))
    assert lines.value is False and faces.value is False    # each release let its own go
    t.drop_layer()                                   # a preset load: every desk back (D4)
    assert t.layer_of("launch") == "preset" and t.layer_of("apc40") == "preset"
    assert shift.value is False


def test_a_missing_desk_is_lost_its_rows_wait_and_it_comes_up_with_its_feedback(build):
    """Neither desk plugged in at launch: both lines read `lost`, the
    APC40's rows stay in the table (they wait), nothing raises. Plug the
    APC40 in: the desk finds it on its own schedule (`Ports.retry`) and
    comes up with its power-up and every light — the registry neither
    closes nor reopens a lost device."""
    r = build(entries(), plug=())
    apc, launch = r.devices.get("apc40"), r.devices.get("launch")
    assert (apc.status, launch.status) == ("lost", "lost")
    assert [ln.split("  ·  ")[2] for ln in ui.device_lines(r.devices)] == ["lost", "lost"]
    n = len(apc.io.bindings)
    assert n > 100                                    # the desk's rows wait in the table
    frame(r)
    io = apc.io
    port = r.bus.plug(APC)
    io.ports._next_try = 0.0                          # its retry is due
    frame(r)
    assert apc.status == "connected" and apc.io is io and len(io.bindings) == n
    assert port.sent[0].type == "sysex"               # the power-up, then the lights
    toggles = {m.note: m.velocity for m in port.sent if m.type == "note_on" and m.channel == 0}
    assert toggles[apc40.N_SCENE[2]] == (1 if r.reg["view.faces"].value else 0)
    assert len(port.sent) > 50
    push(r, APC, cc(apc40.CC_XFADE, 127), cc(apc40.CC_XFADE, 64))   # and its rows act
    assert r.reg["output.dim"].value < 1.0
    # a generic entry with no port is an error line, never the first port there
    r2 = build(entries(launch=False) + [{"role": "nano", "kind": "midi", "enabled": True,
                                        "profile": "generic"}], plug=(APC,))
    assert r2.devices.get("nano").status.startswith("error: ValueError: the generic profile")
    bad = build([{"role": "x", "kind": "midi", "enabled": True, "profile": "akai"}], plug=())
    assert bad.devices.get("x").status == "error: ValueError: no MIDI profile 'akai'; one of " \
        "apc40, generic"


# ---------------------------------------------------------------- the pad and the hands

def test_the_pad_runs_on_the_registry_rows_axes_and_its_camera_job(build):
    """The pad device: it publishes the axes' names, labels and rests
    (`gamepad.publish` — no longer the router's), feeds the axis lanes,
    delivers its rows and runs the sticks' camera job (`gamepad.steer`,
    moved from app.frame) — a stick no route names orbits, a routed one
    leaves its job. Learn pad completes through it and the learning press
    fires nothing else."""
    r = build(entries(launch=False) + [{"role": "pad", "kind": "gamepad", "enabled": True,
                                        "usb": False}], plug=())
    d = r.devices.get("pad")
    pad = d.io
    assert isinstance(pad, ScriptedPad) and d.status == "connected" and pad.status == "connected"
    yaw = r.reg["camera.yaw"]
    y0 = yaw.base
    pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
    frame(r)
    assert r.router.labels["axis"] == list(gp.AXIS_LABELS)
    assert r.router.rests["axis"] == list(gp.AXIS_RESTS)
    assert float(r.router.feeds["axis"][0]) == pytest.approx(1.0)
    assert yaw.base > y0                                     # the left stick orbits
    r.table.add(Binding("axis:LX", "view.inst_amp", "position", 1.0))
    y1 = yaw.base
    pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
    frame(r)
    assert yaw.base == y1                                    # routed: off its camera job
    faces = r.reg["view.faces"].value
    r.learn.arm("view.points", "pad")
    pad.frame()
    pad.frame(held={gp.A})                                   # pad:A is view.faces's
    frame(r)
    assert any(b.source == "pad:A" and b.target == "view.points" for b in r.table.bindings)
    assert r.reg["view.faces"].value == faces                # the learning press only learned
    pad.source = None
    frame(r)
    assert d.status == "lost" and r.router.feeds["axis"] is None


def test_the_hands_run_on_the_registry_through_hands_device(build):
    """`hands/device.py` wraps the liftable `HandsIO`: the registry opens
    it behind its entry, polls it in the feed slot, and the router gets
    `hand` and `hands` with their labels; its ports are the layout's, the
    pair's included, never a pinned count."""
    r = build(entries(launch=False) + [{"role": "leap", "kind": "hands", "enabled": True}],
              plug=())
    d = r.devices.get("leap")
    assert type(d).__module__ == "hyperspace.hands.device" and d.status == "connected"
    frame(r)
    lay = d.io.layout
    assert len(r.router.feeds["hand"]) == lay.n
    assert r.router.labels["hands"] == lay.pair_names
    assert len(d.sources) == lay.n + len(lay.pair_addresses)
    assert {p.scheme for p in d.sources} == {"hand", "hands"}
    assert devices.HandsDevice is type(d)


# ---------------------------------------------------------------- schemes from the registry

def test_schemes_wants_and_row_schemes_come_from_the_registry(build):
    """No fixed tuple: the router's continuous schemes are the registry's
    (`lane`, `lfo`, then each device's feeds in list order), the ROUTING
    page offers them in that order, the learn arms what the listed devices
    complete (`desk` for every MIDI role, the pad, the two hands, a new
    device's role), and the referee knows which schemes are rows."""
    ents = entries() + [{"role": "pad", "kind": "gamepad", "enabled": True, "usb": False},
                        {"role": "leap", "kind": "hands", "enabled": False}]
    r = build(ents, plug=())
    assert r.router.schemes() == ("lane", "lfo", "axis", "hand", "hands")
    assert ui_routing.source_schemes(r.router) == ["lfo", "axis", "hand", "hands"]
    assert r.learn.wants() == ("desk", "pad", "hand:left", "hand:right")
    r.learn.arm("view.bright", "hand:left")             # off, but listed: armable
    with pytest.raises(ValueError, match="no such want"):
        r.learn.arm("view.bright", "wand1")
    assert r.devices.row_schemes() == ("cc", "note", "pitch", "pad", "hat")
    assert set(r.table.row_schemes) >= {"key", "pad", "hat", "cc", "note", "pitch"}
    assert ui.learn_wants(r.learn) == []
    # a new device that feeds (B4's kind, here a stand-in) is armed by its role
    class Wand(devices.Base):
        kind, schemes, feeds = "wand", ("wand1",), ("wand1",)

    r.devices.devices.append(Wand("wand1"))
    assert r.learn.wants()[-1] == "wand1" and ui.learn_wants(r.learn) == ["wand1"]
    assert r.router.schemes()[-1] == "wand1"
    r.learn.arm("view.bright", "wand1")
    assert r.learn.accepts("wand1:tilt") and not r.learn.accepts("hand:left.x")
    # a preset row on a scheme no device of this rig publishes is a dormant
    # performer, not dropped (decision 11), and the page still offers it
    r.table.add(Binding("osc:3", "view.inst_amp", "push", 0.5))
    assert r.table.owner("view.inst_amp").source == "osc:3"
    assert "osc" in ui_routing.source_schemes(r.router)


# ---------------------------------------------------------------- nothing old moves

def test_a_pre_run_bindings_json_and_every_preset_load_quietly_with_two_desks(build):
    """The acceptance's other half: a `bindings.json` written before plan
    27 (today's factory file) loads with no note, no rewrite, nothing
    said; every factory preset then loads with no desk note and no dirt
    with two desks and the pad listed; the APC40's rows are exactly the
    file's, unqualified."""
    text = routing.FACTORY_FILE.read_text()
    r = build(entries() + [{"role": "pad", "kind": "gamepad", "enabled": True, "usb": False}],
              bindings=text)
    t = r.table
    assert t.notes == [] and t.said == "" and not t.changed and t.error == ""
    assert r.path.read_text() == text
    assert all(not b.device for b in t.midi())
    assert len(r.devices.get("apc40").io.bindings) == len(t.midi())
    lib = r.lib
    for name in lib.list("presets"):
        lib.presets.load(name)
        frame(r)
        assert lib.presets.desk_notes == [], name
        assert not lib.is_dirty("presets"), name
    assert r.path.read_text() == text                # never rewritten
    assert not r.notes                               # the registry said nothing either


def test_a_pre_run_bindings_json_means_the_first_pad_with_two_pads_listed(build):
    """Plan 27 B6: a `bindings.json` written before B6 (today's factory
    file, its pad rows unqualified) loads with two pads listed with no
    note, no rewrite and no dirt, and every pad row means the primary
    pad: a press on the second pad fires none of them."""
    text = routing.FACTORY_FILE.read_text()
    pads = [{"role": "pad", "kind": "gamepad", "enabled": True, "usb": False},
            {"role": "p2", "kind": "gamepad", "enabled": True, "usb": False}]
    r = build(entries() + pads, bindings=text)
    t = r.table
    assert t.notes == [] and t.said == "" and not t.changed and t.error == ""
    rows = t.of("pad", "hat")
    assert rows and all(not b.device and t.role_of(b) == "pad" for b in rows)
    lib = r.lib
    for name in lib.list("presets"):
        lib.presets.load(name)
        frame(r)
        assert not lib.is_dirty("presets"), name
    one, two = r.devices.get("pad").io, r.devices.get("p2").io
    faces = r.reg["view.faces"].value                    # pad:A's
    one.frame()
    two.frame()
    frame(r)
    two.frame(held={gp.A})
    frame(r)
    assert r.reg["view.faces"].value == faces            # the second pad's A: none of the file's
    one.frame(held={gp.A})
    frame(r)
    assert r.reg["view.faces"].value != faces            # the primary's A: the file's row
    # ROUTING's combo offers the second pad's axes under its role, after
    # the primary's (no page change: the registry's feeds, the pad's labels)
    assert ui_routing.source_schemes(r.router) == ["lfo", "axis", "axis@p2"]
    panel = NS(audio=NS(chain=NS(band_names=["LOW"])))
    offered = dict(ui_routing._sources(panel, r.router))
    assert offered["axis@p2:LX"] == "axis@p2 left stick X"
    assert offered["axis:LX"] == "axis left stick X"
    # a route on a pad this rig does not list still shows its source
    r.table.add(Binding("axis@p3:RT", "view.inst_amp", "position", 1.0))
    assert "axis@p3" in ui_routing.source_schemes(r.router)
    assert r.path.read_text() == text                    # never rewritten
    assert not r.notes


# ---------------------------------------------------------------- review of PR #181

def test_shift_on_the_apc40_leaves_the_second_desks_caught_rows_caught(build):
    """D7 per desk: a layer switch re-arms pickup on the faders of the desk
    whose latch flipped (C2's `redraw(switch=True)`), never another's —
    the layer serial is per role (`Bindings.layer_serial_of`)."""
    r = build(entries())
    t = r.table
    row = Binding("cc@launch:0:30", "view.inst_amp", "abs", layer="preset")
    t.add(row)
    amp = r.reg["view.inst_amp"]
    push(r, LAUNCH, cc(30, round(amp.norm * 127)))    # on the value: caught
    assert row.caught
    io = r.devices.get("launch").io
    switches: list[dict] = []
    real = io.redraw
    io.redraw = lambda **k: switches.append(k) or real(**k)
    serial = t.layer_serial_of("launch")
    push(r, APC, note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert r.reg[SHIFT_PARAM].value is True and t.layer_of("apc40") == "global"
    frame(r)
    assert t.layer_serial_of("launch") == serial and switches == [] and row.caught
    # the APC40's own layered fader is re-armed by its switch (C2), as before
    assert r.devices.get("apc40").io._seen[0] == t.layer_serial
    t.set_layer("global", "launch")                   # its own latch flips: it redraws
    frame(r)
    assert t.layer_serial_of("launch") == serial + 1
    assert switches == [{"load": False, "switch": True}]


def test_the_desk_whose_profile_wrote_the_table_owns_the_unqualified_rows(build):
    """Orchestrator's ruling on PR #181: the unqualified rows are the first
    MIDI role whose profile is the table's (`bindings.json`'s "profile",
    apc40), else the first listed — a generic box listed above the APC40
    does not inherit the APC40's factory rows or SHIFT; a rig whose only
    desk is generic still maps."""
    r = build(list(reversed(entries())))              # the generic box listed first
    assert r.table.midi_roles == ("apc40", "launch")
    apc, launch = r.devices.get("apc40"), r.devices.get("launch")
    assert apc.io.qualifier == "" and launch.io.qualifier == "launch"
    assert len(launch.io.bindings) == 0 < len(apc.io.bindings)
    push(r, LAUNCH, note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert r.reg[SHIFT_PARAM].value is False          # the box's note 98 is not SHIFT
    push(r, APC, note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert r.reg[SHIFT_PARAM].value is True
    only = devices.DeviceRegistry(
        [entries(apc=False)[0]], devices.Context(table=NS(profile="apc40", midi_roles=())))
    assert only.midi_roles() == ("launch",)           # its only desk: it owns them
