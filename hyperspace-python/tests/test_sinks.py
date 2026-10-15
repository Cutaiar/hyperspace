"""Plan 27 B3: sinks — the bridge and the hands' DAW out as sinks; a param
routed to a sink through the table and Learn.

A sink is a device that reads effective values after `reg.apply` and sends
them out (`Device.sinks`, `send`). What it sends is the session's sink rows
(routing.py, `SINK_OP`: ``param:<id>`` / ``lane:<i>`` → ``<role>:<channel>``),
which the bridge's old `send` list becomes once; the hands' DAW out is a
`midi-out` sink entry (`hands-daw`) carrying `HandsIO`'s messages. Fake
ports throughout, as in test_bridge / test_hands.
"""

import json
from types import SimpleNamespace as NS

import mido
import pytest

from hyperspace import bridge, config, devices, routing, ui
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import CEIL, default_params
from hyperspace.bridge import Bridge, quantize
from hyperspace.control import Control
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.learn import Learn
from hyperspace.params import build_registry
from hyperspace.routing import SINK_OP, Binding, Bindings, Router
from hyperspace.view import ViewState


class FakeIn:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)


class FakeOut:
    name = "fake out"

    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _rig(tmp_path):
    chain = Analyzer(Analyser(48_000.0), default_params(), layout=legacy_layout())
    control = Control(chain)
    reg = build_registry(ViewState(), control, NS(chain=chain, on=True), None)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    router = Router(reg, table)
    return NS(reg=reg, chain=chain, table=table, router=router)


def _bridge_device(r, clock=None, **cfg):
    """A bridge device on fake ports over the rig's table, opened."""
    out = FakeOut()
    io = Bridge(r.reg, cfg, inp=FakeIn(), out=out, clock=clock or Clock())
    d = devices.BridgeDevice("bridge", {"role": "bridge", "kind": "bridge", **cfg},
                             devices.Context(reg=r.reg, table=r.table), io=io)
    return d, out


def pitches(out):
    return {m.channel: m.pitch + 8192 for m in out.sent}


# ---------------------------------------------------------------- the row

def test_a_sink_row_is_a_session_row_never_a_performer_and_round_trips(tmp_path):
    """The sink row's form: ``{"source": "param:<id>" | "lane:<i>" |
    "lane:*", "target": "<role>:<channel>", "op": "send"}``. bindings.json
    keeps it (sinks are rig, D1 / D9); it is no route, owns nothing, and a
    preset never sees it."""
    r = _rig(tmp_path)
    rows = [Binding("param:view.bright", "bridge:3", SINK_OP),
            Binding("lane:*", "bridge:0", SINK_OP),
            Binding("lane:2", "hands-daw:1", SINK_OP, enabled=False)]
    for b in rows:
        r.table.add(b)
    assert all(b.is_sink and not b.is_performer and routing.is_session_row(b) for b in rows)
    assert r.table.routes() == [] and r.table.owner("view.bright") is None
    assert [b.sink for b in rows] == [("bridge", 3), ("bridge", 0), ("hands-daw", 1)]
    # a lane reads as the ext / LFO rows do: scheme, index, then its name
    r.router.labels["lane"] = ["SUB", "LOW", "MID", "HIGH"]
    assert r.router.describe(Binding("lane:3", "bridge:3", SINK_OP)) == "lane 3 HIGH → bridge:3"
    assert r.router.describe(rows[0]) == "param view.bright → bridge:3"
    r.table.write()
    doc = json.loads((tmp_path / "bindings.json").read_text())
    assert {"source": "param:view.bright", "target": "bridge:3", "op": "send"} in doc["bindings"]
    assert {"source": "lane:2", "target": "hands-daw:1", "op": "send",
            "enabled": False} in doc["bindings"]
    again = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    assert [(b.source, b.target, b.op, b.enabled) for b in again.sinks(enabled=False)] == [
        (b.source, b.target, b.op, b.enabled) for b in rows]
    assert again.carried is None and not again.notes          # no note, no migration
    assert [b.target for b in again.sinks("bridge")] == ["bridge:3", "bridge:0"]
    # what a sink row cannot be: the referee's door says why
    for bad in (Binding("hand:right.roll", "bridge:0", SINK_OP),
                Binding("param:view.bright", "view.bright", SINK_OP),
                Binding("lane:x", "bridge:0", SINK_OP)):
        with pytest.raises(ValueError):
            r.table.add(bad)


def test_a_sink_row_on_an_owned_param_asks_nothing(tmp_path):
    """The referee rules unchanged: a hand performs view.bright, and the
    param still goes out on a sink — no `Owned`, the owner untouched."""
    r = _rig(tmp_path)
    hand = r.table.add(Binding("hand:right.y", "view.bright", "position"))
    r.table.add(Binding("param:view.bright", "bridge:0", SINK_OP))
    assert r.table.owner("view.bright") is hand
    with pytest.raises(routing.Owned):
        r.table.add(Binding("lfo:0", "view.bright", "push"))      # a second performer still asks


def test_the_send_list_translates_to_rows_lane_star_first():
    rows, bad = routing.sink_rows_from_send(
        "bridge", ["lane:*", "param:view.bright", "ext:3", "lane:2"], lanes=6)
    assert [(b.source, b.target) for b in rows] == [
        ("lane:*", "bridge:0"), ("param:view.bright", "bridge:6"), ("lane:2", "bridge:7")]
    assert len(bad) == 1 and "'ext:3'" in bad[0]


def test_sink_values_read_effective_values_and_an_explicit_row_wins_its_channel(tmp_path):
    r = _rig(tmp_path)
    r.chain.out[:] = 0.0
    r.chain.out[1] = CEIL / 2
    p = r.reg["view.bright"]
    p.set_norm(0.25)
    rows = [Binding("lane:*", "s:0", SINK_OP), Binding("param:view.bright", "s:2", SINK_OP),
            Binding("lane:1", "s:9", SINK_OP), Binding("param:nope", "s:10", SINK_OP),
            Binding("lane:3", "s:11", SINK_OP, enabled=False)]
    got = routing.sink_values(rows, r.reg, r.chain)
    assert got[1] == pytest.approx(0.5) and got[9] == pytest.approx(0.5)
    assert got[2] == pytest.approx(p.eff_norm)              # the row wins the star's channel
    assert got[10] == 0.0 and 11 not in got and len(got) == r.chain.n + 2
    # no analyzer running: the star's lanes (as many as last seen) fall to 0
    idle = routing.sink_values(rows, r.reg, None, lanes=r.chain.n)
    assert [idle[k] for k in range(r.chain.n) if k != 2] == [0.0] * (r.chain.n - 1)


# ---------------------------------------------------------------- the bridge

def test_the_bridges_send_list_becomes_sink_rows_once_with_one_note(tmp_path, capsys):
    """A config with the old `send` list, the bridge on: its rows land in
    the session (bindings.json written), one note; the next launch, rows
    there, nothing is added or said. The default list (the file names
    none) is `lane:*` on bridge:0. An off bridge seeds nothing."""
    home = tmp_path
    (home / "config.toml").write_text(
        '[bridge]\nenabled = true\nout = "nope"\nsend = ["lane:*", "param:view.bright"]\n')
    cfg = config.load(home / "config.toml")
    capsys.readouterr()
    r = _rig(home)
    notes: list[str] = []
    devices.DeviceRegistry(config.devices(cfg), devices.Context(table=r.table, notes=notes))
    assert [(b.source, b.target) for b in r.table.sinks("bridge")] == [
        ("lane:*", "bridge:0"), ("param:view.bright", "bridge:6")]
    said = [n for n in notes if "send is now sink rows" in n]
    assert len(said) == 1 and "param:view.bright → bridge:6" in said[0]
    doc = json.loads((home / "bindings.json").read_text())
    assert sum(b.get("op") == "send" for b in doc["bindings"]) == 2
    # the next launch: the file's rows say; nothing added, nothing said
    again = Bindings.load(home / "bindings.json", legacy_midi=None)
    notes2: list[str] = []
    devices.DeviceRegistry(config.devices(cfg), devices.Context(table=again, notes=notes2))
    assert len(again.sinks("bridge")) == 2 and notes2 == []
    # the default list; and a bridge that is off seeds nothing
    t3 = Bindings.load(tmp_path / "b3.json", legacy_midi=None)
    devices.DeviceRegistry([{"role": "bridge", "kind": "bridge", "enabled": True,
                             "send": ["lane:*"]}], devices.Context(table=t3, notes=[]))
    assert [(b.source, b.target) for b in t3.sinks()] == [("lane:*", "bridge:0")]
    t4 = Bindings.load(tmp_path / "b4.json", legacy_midi=None)
    devices.DeviceRegistry(config.devices(config.load(tmp_path / "none.toml")),
                           devices.Context(table=t4, notes=[]))
    assert t4.sinks(enabled=False) == [] and not (tmp_path / "b4.json").exists()


def test_rows_deleted_on_routing_never_come_back_the_translation_is_marked(tmp_path):
    """The translation is marked done in bindings.json (`sinks_seeded`),
    not by consuming the config key: × every bridge row, reload the table,
    re-run the registry (a launch) and re-apply the list (a config.toml
    save mid-session) — no row comes back. A file from before the mark
    that already holds rows on the role counts as seeded (the mark added)."""
    entries = [{"role": "bridge", "kind": "bridge", "enabled": True, "send": ["lane:*"]}]
    path = tmp_path / "bindings.json"
    t = Bindings.load(path, legacy_midi=None)
    rig = devices.DeviceRegistry(entries, devices.Context(table=t, notes=[]))
    assert len(t.sinks("bridge")) == 1 and t.sinks_seeded == ["bridge"]
    assert '"sinks_seeded": ["bridge"]' in path.read_text()
    for b in t.sinks(enabled=False):                 # ROUTING's ×, each writing the file
        t.remove(b)
        t.write()
    rig.apply([dict(entries[0], rate=50)])           # config.toml saved mid-session
    assert t.sinks(enabled=False) == []
    again = Bindings.load(path, legacy_midi=None)
    assert again.sinks_seeded == ["bridge"]
    notes: list[str] = []
    devices.DeviceRegistry(entries, devices.Context(table=again, notes=notes))
    assert again.sinks(enabled=False) == [] and notes == []
    # a home whose file holds rows on the role but no mark (written before it)
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"schema": routing.SCHEMA, "profile": "apc40", "bindings": [
        {"source": "lane:0", "target": "bridge:0", "op": "send"}]}))
    t2 = Bindings.load(old, legacy_midi=None)
    devices.DeviceRegistry(entries, devices.Context(table=t2, notes=(n2 := [])))
    assert [b.source for b in t2.sinks()] == ["lane:0"] and n2 == []
    assert t2.sinks_seeded == ["bridge"] and "sinks_seeded" in old.read_text()


def test_a_param_routed_to_the_bridge_sends_its_effective_value_after_apply(tmp_path):
    """The frame's order: a lane pushes view.bright (Router.modulate), the
    registry commits (`reg.apply`), then the sinks send — the bridge's
    fake port receives the effective norm, not the base."""
    r = _rig(tmp_path)
    r.table.add(Binding("param:view.bright", "bridge:1", SINK_OP))
    r.table.set_routes([Binding("lane:0", "view.bright", "push", 0.5, rest=0.0)])
    d, out = _bridge_device(r)
    rig = devices.DeviceRegistry(devices=[d], ctx=d.ctx)
    p = r.reg["view.bright"]
    p.set_norm(0.25)
    r.chain.out[:] = 0.0
    r.chain.out[0] = CEIL                       # u = 1: the push adds 0.5
    rig.poll(1 / 60, 0.0, router=r.router)
    rig.feed(r.router)
    r.router.modulate(r.chain, 1 / 60)
    r.reg.apply()
    rig.send(r.reg, r.chain)
    assert p.norm == pytest.approx(0.25) and p.eff_norm == pytest.approx(0.75)
    assert pitches(out) == {1: quantize(0.75)} and quantize(0.75) != quantize(0.25)
    # nothing changed: nothing more goes out; the base moves: the change does
    rig.send(r.reg, r.chain)
    assert len(out.sent) == 1
    d.io.clock.t += 1.0
    p.set_norm(0.0)
    r.router.modulate(r.chain, 1 / 60)
    r.reg.apply()
    rig.send(r.reg, r.chain)
    assert out.sent[-1].channel == 1 and out.sent[-1].pitch + 8192 == quantize(0.5)


def test_the_bridge_publishes_its_ext_labels_and_rests(tmp_path):
    """The ext lanes have names and rests like every source, so the ROUTING
    page needs no fixed count (`N_EXT` is gone)."""
    from hyperspace import ui_routing

    r = _rig(tmp_path)
    d, _ = _bridge_device(r, in_lanes=4)
    d.feed(r.router)
    assert r.router.labels["ext"] == ["ext 0", "ext 1", "ext 2", "ext 3"]
    assert r.router.rests["ext"] == [0.0] * 4
    assert not hasattr(ui_routing, "N_EXT")
    assert [p.address for p in d.sinks][:3] == ["bridge:0", "bridge:1", "bridge:2"]
    assert d.sinks[3].label == "pitch ch4"


def test_the_system_line_of_a_sink_says_what_it_sends(tmp_path):
    r = _rig(tmp_path)
    d, _ = _bridge_device(r)
    r.table.add(Binding("param:view.bright", "bridge:1", SINK_OP))
    r.table.add(Binding("lane:0", "bridge:0", SINK_OP))
    r.table.add(Binding("lane:1", "bridge:2", SINK_OP, enabled=False))
    rig = devices.DeviceRegistry(devices=[d], ctx=d.ctx)
    (line,) = ui.device_lines(rig)
    assert line.startswith("bridge  ·  bridge  ·  connected  ·  16 sources  ·  2 sinks  ·  ")


# ---------------------------------------------------------------- a midi-out sink

def test_a_midi_out_sink_sends_its_rows_and_carries_nothing_it_was_not_given(tmp_path):
    r = _rig(tmp_path)
    clock = Clock()
    out = FakeOut()
    ctx = devices.Context(reg=r.reg, table=r.table)
    d = devices.MidiOutDevice("lights", {"port": "x", "encoding": "cc14", "cc": 20}, ctx,
                              io=bridge.OutPort("x", out=out, clock=clock),
                              sender=bridge.Sender("cc14", 0, 20, 100, clock))
    rig = devices.DeviceRegistry(devices=[d], ctx=ctx)
    r.table.add(Binding("param:view.bright", "lights:2", SINK_OP))
    r.reg["view.bright"].set_norm(0.5)
    r.reg.apply()
    rig.send(r.reg, None)
    v = quantize(r.reg["view.bright"].eff_norm)
    assert [(m.control, m.value) for m in out.sent] == [(22, v >> 7), (54, v & 0x7F)]
    assert d.status == "connected" and d.last.endswith(f"cc 54 = {v & 0x7F} ch1")
    assert [p.address for p in d.sinks][:2] == ["lights:0", "lights:1"]


def test_a_midi_out_entry_with_no_port_is_an_error_line(tmp_path):
    rig = devices.DeviceRegistry([{"role": "o", "kind": "midi-out", "enabled": True,
                                   **config.MIDI_OUT}], devices.Context(notes=[]))
    rig.open_all()
    assert rig.get("o").status.startswith("error: ValueError: a midi-out entry needs a port")


# ---------------------------------------------------------------- the hands' DAW out

def test_hands_out_becomes_the_hands_daw_entry_with_a_note_when_written(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('[hands]\nenabled = true\nout = "IAC Bus 2"\n')
    cfg = config.load(p)
    got = {e["role"]: e for e in config.devices(cfg)}
    assert got["hands-daw"] == {"role": "hands-daw", "kind": "midi-out", "enabled": True,
                                **config.MIDI_OUT, "port": "IAC Bus 2", "carries": "leap"}
    assert [e["role"] for e in config.devices(cfg)] == ["pad", "apc40", "leap", "hands-daw",
                                                        "bridge"]
    assert sum("[hands] out is now a [[devices]] entry" in n for n in cfg["notes"]) == 1
    # out = "": no DAW out at all; the hands off: none either
    p.write_text('[hands]\nenabled = true\nout = ""\n')
    assert "hands-daw" not in {e["role"] for e in config.devices(config.load(p))}
    p.write_text('[hands]\nout = "IAC Bus 2"\n')
    assert "hands-daw" not in {e["role"] for e in config.devices(config.load(p))}
    # a list that carries the hands itself keeps its own entry
    p.write_text('[[devices]]\nrole = "leap"\nkind = "hands"\n'
                 '[[devices]]\nrole = "daw"\nkind = "midi-out"\nport = "Bus"\ncarries = "leap"\n')
    assert [e["role"] for e in config.devices(config.load(p))] == ["leap", "daw"]


def test_the_hands_daw_sink_on_the_registry_sends_what_handsio_sent(tmp_path):
    """Through the registry's slots — the hands fed, then the sink after
    `reg.apply` — the `hands-daw` sink's port receives exactly the
    messages `HandsIO.poll` made this frame, in order; `HandsIO` holds no
    port, and the HANDS page reads the sink's port name."""
    from test_hands import FakeSource, hand

    settings = HandSettings.from_config({})
    settings.catch_s, settings.rate, settings.pinch_hold = 0.0, 0, 0.0
    clock = Clock()
    src = FakeSource(clock)
    io = HandsIO(settings, {"out": "Hyperspace Hands"}, source=src, clock=clock)
    assert io.out is None
    out = FakeOut()
    ctx = devices.Context()
    sink = devices.MidiOutDevice("hands-daw", {"port": "x", "carries": "leap"}, ctx,
                                 io=bridge.OutPort("x", out=out, clock=clock),
                                 sender=bridge.Sender(clock=clock))
    rig = devices.DeviceRegistry(devices=[devices.HandsDevice("leap", io=io), sink], ctx=ctx)
    assert ctx.devices is rig
    made: list = []
    real = io.poll
    io.poll = lambda *a, **k: (made.extend(m := real(*a, **k)), m)[1]   # what HandsIO made
    for k in range(4):
        clock.t += 1 / 60
        src.put(hand(pos=(10.0 * k, 220.0, 0.0), tips=(10.0, 80.0, 80.0, 80.0), palm_w=100.0))
        rig.poll(1 / 60, clock.t)
        rig.feed(None)
        rig.send(None, None)
    assert made and out.sent == made and all(isinstance(m, mido.Message) for m in out.sent)
    assert io.out_name == "fake out" and io.last and io.outbox == []
    notes_on = [m.note for m in out.sent if m.type == "note_on"]
    assert 121 in notes_on and 104 in notes_on               # presence, R index pinch


# ---------------------------------------------------------------- Learn → sink

def test_learn_sink_on_a_param_lands_a_session_row_with_no_question(tmp_path):
    """Right-click → Learn sink ▸ bridge:2: the row lands at once in the
    session (bindings.json written), even on a param a hand performs — no
    Replace / Keep, no pending question, the performer untouched; a second
    param on the same port takes it; a trigger is refused."""
    r = _rig(tmp_path)
    d, _ = _bridge_device(r)
    rig = devices.DeviceRegistry(devices=[d], ctx=d.ctx)
    learn = Learn(r.reg, r.table, devices=rig)
    hand_row = r.table.add(Binding("hand:right.y", "view.bright", "position"))
    assert [a for a, _ in ui.sink_items(learn)][:2] == ["bridge:0", "bridge:1"]
    assert ui.sink_items(learn)[2][1] == "bridge:2  ·  pitch ch3"
    b = learn.learn_sink("view.bright", "bridge:2")
    assert (b.source, b.target, b.op) == ("param:view.bright", "bridge:2", "send")
    assert learn.pending is None and not learn.refused and learn.learning is None
    assert r.table.owner("view.bright") is hand_row
    doc = json.loads((tmp_path / "bindings.json").read_text())
    assert {"source": "param:view.bright", "target": "bridge:2", "op": "send"} in doc["bindings"]
    assert "sent view.bright → bridge:2" in learn.last
    learn.learn_sink("view.speed", "bridge:2")
    assert [(x.source, x.target) for x in r.table.sinks()] == [("param:view.speed", "bridge:2")]
    assert "param:view.bright let go" in learn.last
    trig = next(p for p in r.reg if p.kind.name == "TRIGGER")
    assert learn.learn_sink(trig.id, "bridge:3") is None and learn.refused
    assert learn.learn_sink("view.speed", "bridge") is None and learn.refused
    # the rows the menu lists for the param
    from hyperspace import learn as learn_mod
    assert [x.target for x in learn_mod.sinks_of(r.table, ("view.speed",))] == ["bridge:2"]


def test_a_learn_with_no_registry_offers_no_sink(tmp_path):
    r = _rig(tmp_path)
    assert ui.sink_items(Learn(r.reg, r.table)) == []

