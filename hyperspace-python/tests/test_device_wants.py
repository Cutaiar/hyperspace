"""Plan 40 T4 — what the loaded preset wants and the rig lacks, and the
arrival (spec P4).

- **`devices.wants(table, registry)`**: one `Want(role, state, scheme,
  rows)` per device role the preset's performer routes, preset-layer desk
  rows and modifier inputs name — ``connected``, ``lost``, ``off`` or
  ``missing`` (not in this rig) — with its rows in words
  (`routing.row_words`); never a built-in scheme. Over a bare registry and
  a `[[devices]]` list, headless.
- **`wants_for` / `want_words`**: what a group node's status line says
  (T2 calls them).
- **Where it shows**: the chip's words, the SYSTEM page's lines.
- **The arrival**: `DeviceRegistry.poll` compares each status with the
  last frame's — the listeners once a frame, `said` once a change, with
  the count; nothing over 100 steady frames; a real `MidiDevice` coming
  back fires each once; a device added to config.toml says it through
  `apply`.
"""

from __future__ import annotations

from test_device_inputs import APC, entries, frame
from test_device_inputs import build as inputs_build  # noqa: F401 — the fake-bus host fixture
from test_ui_shell import frame as ui_frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import devices, graphview, modifiers, routing, ui, ui_graph
from hyperspace.devices import Want
from hyperspace.routing import Binding, Bindings

HAND_ROWS = (Binding("hand:right.y", "view.bright", "position"),
             Binding("hand:right.roll", "view.spin", "push", 0.5),
             Binding("hand:left.x", "view.zoom", "position"))


def table_of(*rows: Binding) -> Bindings:
    return Bindings(list(rows))


def rig_of(*ents: dict) -> devices.DeviceRegistry:
    """A registry over `[[devices]]` entries, nothing opened: a listed,
    enabled device reads `lost` (no adapter), an ``enabled = false`` one
    `off`."""
    return devices.DeviceRegistry(list(ents))


HANDS = {"role": "leap", "kind": "hands", "enabled": True}
DESK = {"role": "apc40", "kind": "midi", "enabled": True, "port": "APC40", "profile": "apc40"}


# ---------------------------------------------------------------- the words for a row

def test_row_words_say_a_control_as_a_person_does():
    w = routing.row_words
    assert w("hand:right.y") == "right hand y"
    assert w(Binding("hand:left.pinch.index", "x", "position")) == "left hand pinch index"
    assert w("hands:gap") == "hands gap"
    assert w("lane:0") == "band 1"
    assert w("pad:A") == "pad A" and w("pad@p2:A") == "pad A"
    assert w("hat:UP") == "d-pad up"
    assert w("axis@p2:LX") == "axis LX"
    assert w("cc:0:48") == "CC 48 ch1" and w("note:*:53") == "note 53 any ch"
    assert w("pitch:2") == "pitch bend ch3"
    assert w("lfo:0") == "LFO 1" and w("env:1") == "env 2" and w("seq:3") == "seq lane 4"
    assert w("mod:3") == "mod.3"
    assert w("osc1:/fader/1") == "/fader/1"
    assert w("thing:7") == "thing:7"
    # the caller's names first — the desk's glyph, a canvas port's name
    from hyperspace import apc40
    assert w("cc:0:48", apc40.glyph) == "K1"
    assert w("cc@launch:0:48", apc40.glyph) == "K1"         # the bare control is named
    assert w("hand:right.y", lambda s: None) == "right hand y"


def test_cable_words_still_read_the_port_name_first():
    """graphview.cable_words delegates the source's words to row_words, the
    canvas's port name first — and the table moved, keeping its name."""
    assert graphview.SCHEME_ROLE is devices.SCHEME_ROLE
    assert set(graphview.NO_DEVICE) | {"key"} == set(devices.NO_DEVICE_SCHEMES)
    assert modifiers.SCHEME in devices.NO_DEVICE_SCHEMES
    assert devices.BUILTIN_SCHEMES == routing.BUILTIN_LANES


# ---------------------------------------------------------------- wants

def test_hand_rows_on_a_rig_without_hands_want_leap_not_in_this_rig():
    ws = devices.wants(table_of(*HAND_ROWS), rig_of(DESK))
    assert ws == [Want("leap", "missing", "hand",
                       ("right hand y", "right hand roll", "left hand x"))]
    assert ws[0].count == "3 rows" and ws[0].lacking
    # no registry at all: the same answer (a rig with nothing listed)
    assert devices.wants(table_of(*HAND_ROWS), None) == ws


def test_a_listed_hands_device_is_off_or_lost_or_connected():
    t = table_of(*HAND_ROWS)
    assert devices.wants(t, rig_of({**HANDS, "enabled": False}))[0].state == "off"
    assert devices.wants(t, rig_of(HANDS))[0].state == "lost"
    assert devices.wants(t, devices.DeviceRegistry(devices=[_Live("leap", ("hand", "hands"))])
                         )[0].state == "connected"
    # a hands device under another role is that role's: the registry names it
    other = rig_of({**HANDS, "role": "hands1", "enabled": False})
    assert [(w.role, w.state) for w in devices.wants(t, other)] == [("hands1", "off")]


class _Live(devices.Base):
    """A listed device whose adapter is there."""

    kind = "fake"

    def __init__(self, role: str, schemes: tuple[str, ...]):
        super().__init__(role, io=object())
        self.schemes = self.feeds = schemes


def test_a_qualified_midi_row_wants_its_role_not_the_primary():
    t = table_of(Binding("cc@launch:0:7", "view.bright", "abs", layer="preset"),
                 Binding("cc:0:48", "view.zoom", "abs", layer="preset"))
    ws = devices.wants(t, rig_of(DESK))
    by = {w.role: w for w in ws}
    assert by["launch"].state == "missing" and by["launch"].rows == ("CC 7 ch1",)
    assert by["apc40"].state == "lost" and by["apc40"].rows == ("K1",)    # the desk's glyph
    assert by["apc40"].count == "1 control"


def test_only_the_presets_rows_count_and_never_a_builtin_scheme():
    """Performer routes, preset-layer desk rows and modifier inputs: a
    session row (a SHIFT-layer or invariant desk row, a pad button, a key)
    is the rig's, a disabled row reads nothing, and `lane`, `lfo`, `env`,
    `seq`, `mod` are no device's."""
    t = table_of(Binding("cc:0:48", "view.bright", "abs", layer="preset"),
                 Binding("cc:0:49", "view.bright", "abs", layer="global"),
                 Binding("cc:0:50", "view.bright", "abs"),
                 Binding("pad:A", "view.faces", "toggle"),
                 Binding("key:B", "view.faces", "toggle"),
                 Binding("lane:0", "view.zoom", "push", 0.5),
                 Binding("lfo:0", "view.zoom", "push", 0.5),
                 Binding("env:0", "view.zoom", "push", 0.5),
                 Binding("seq:0", "view.zoom", "push", 0.5),
                 Binding("mod:1", "view.zoom", "push", 0.5),
                 Binding("axis:LX", "view.spin", "push", 0.5, enabled=False))
    t.modifiers = (modifiers.Modifier("mod.1", "smooth", ("hand:left.x",)),)
    ws = devices.wants(t, None)
    assert [(w.role, w.rows) for w in ws] == [("apc40", ("K1",)), ("leap", ("left hand x",))]
    # the same knob on two params is one control
    t2 = table_of(Binding("cc:0:48", "view.bright", "abs", layer="preset"),
                  Binding("cc:0:48", "view.zoom", "abs", layer="preset"))
    assert devices.wants(t2, None)[0].rows == ("K1",)


def test_wants_for_keeps_the_rows_that_land_on_the_ids_and_want_words_say_them():
    t = table_of(Binding("cc:0:48", "fx.acid.2.speed", "abs", layer="preset"),
                 Binding("cc:0:49", "fx.acid.2.mix", "abs", layer="preset"),
                 Binding("cc:0:50", "view.bright", "abs", layer="preset"),
                 Binding("hand:right.y", "fx.wobble.2.amount", "position"),
                 Binding("hand:left.x", "view.zoom", "position"))
    t.modifiers = (modifiers.Modifier("mod.3", "smooth", ("hand:right.roll",)),)
    rig = rig_of(DESK)
    ws = devices.wants_for(t, rig, ["fx.acid.2", "fx.wobble.2.amount", "mod.3"])
    assert ws == [Want("apc40", "lost", "cc", ("K1", "K2")),
                  Want("leap", "missing", "hand", ("right hand y", "right hand roll"))]
    assert devices.want_words(ws) == ("waits for apc40 (lost): K1, K2 · "
                                      "leap (not in this rig): right hand y, right hand roll")
    assert devices.wants_for(t, rig, ["mod.1"]) == []
    assert devices.want_words([Want("apc40", "connected", "cc", ("K1",))]) == ""
    # a long list is cut, the rest counted
    many = Want("apc40", "lost", "cc", tuple(f"K{k}" for k in range(1, 12)))
    assert devices.want_lines([many])[0].endswith("K8, + 3 more")


# ---------------------------------------------------------------- where it shows

def test_the_chip_and_the_system_lines():
    t = table_of(*HAND_ROWS, Binding("cc:0:48", "view.zoom", "abs", layer="preset"))
    ws = devices.wants(t, rig_of(DESK))
    assert devices.missing_chip(ws) == "2 devices missing"
    assert ui.wanted_lines(rig_of(DESK), t) == [
        "wanted by the preset: leap — not in this rig; 3 rows wait",
        "wanted by the preset: apc40 — lost; 1 control wait"]
    assert devices.missing_chip(devices.wants(table_of(HAND_ROWS[0]), rig_of(DESK))) == \
        "1 device missing"
    # nothing when all are there, nothing when the preset wants nothing
    live = devices.DeviceRegistry(devices=[_Live("leap", ("hand", "hands"))])
    assert devices.missing_chip(devices.wants(table_of(*HAND_ROWS), live)) is None
    assert ui.wanted_lines(live, table_of(*HAND_ROWS)) == []
    assert ui.wanted_lines(rig_of(DESK), table_of()) == []
    assert ui.wanted_lines(None, t) == [] and ui.wanted_lines(rig_of(DESK), None) == []


def test_the_chip_draws_on_the_graph_head_the_preset_strip_and_system(shell_rig, monkeypatch):  # noqa: F811
    """Headless: with a registry that lacks the hands and a preset with a
    hand row, the GRAPH page, the PRESETS page and the SYSTEM page draw
    with the chip and the line; without a registry the head is as it was."""
    p = shell_rig.panel
    seen: list[str] = []
    real = ui.chip

    def chip(label, *a, **k):
        seen.append(label)
        return real(label, *a, **k)
    monkeypatch.setattr(ui, "chip", chip)
    texts: list[str] = []
    real_colored = ui.imgui.text_colored
    monkeypatch.setattr(ui.imgui, "text_colored",
                        lambda col, text: texts.append(text) or real_colored(col, text))
    ui_frame(p, "graph")
    ui_frame(p, "graph")
    assert not any("missing" in s for s in seen)          # no registry: nothing
    # the factory desk's preset layer on an APC40 not plugged in, and a hand
    # row on a rig with no hands: two devices
    p.devices = rig_of(DESK)
    shell_rig.router.table.bindings.append(HAND_ROWS[0])
    ui_frame(p, "graph")
    assert "2 devices missing##wants" in seen
    seen.clear()
    ui_frame(p, "presets")
    assert "2 devices missing##wants" in seen
    ui_frame(p, "system")
    assert "wanted by the preset: leap — not in this rig; 1 row wait" in texts
    assert any(t.startswith("wanted by the preset: apc40 — lost; ") for t in texts)
    assert callable(ui_graph._wants_chip)


# ---------------------------------------------------------------- the arrival

class _Flip(devices.Base):
    """A device whose hardware comes and goes inside its adapter, as a
    `MidiDevice`'s does (`Ports.retry`): `on` is the adapter's."""

    kind = "midi"
    schemes = ("cc", "note", "pitch")

    def __init__(self, role: str):
        super().__init__(role, io=object())
        self.on = False
        self.polls = 0

    @property
    def status(self) -> str:
        return "connected" if self.on else "lost"

    def poll(self, dt, now):
        self.polls += 1


def test_the_hook_fires_once_per_change_with_the_count_and_never_when_steady():
    t = table_of(*(Binding(f"cc:0:{48 + k}", "view.bright", "abs", layer="preset")
                   for k in range(6)))
    d = _Flip("apc40")
    rig = devices.DeviceRegistry(devices=[d], ctx=devices.Context(table=t))
    said: list[tuple] = []
    told: list[int] = []
    rig.said = lambda role, was, now: said.append(
        (role, was, now, devices.arrival(t, rig, role, was, now)))
    rig.listeners.append(lambda: told.append(1))
    rig.open_all()
    assert told == [1] and said == []                     # the launch is no change
    for _ in range(100):
        rig.poll(1 / 60, 0.0)
    assert told == [1] and said == [] and d.polls == 100  # steady: nothing fires
    d.on = True
    rig.poll(1 / 60, 0.0)
    rig.poll(1 / 60, 0.0)
    assert told == [1, 1]
    assert said == [("apc40", "lost", "connected", "apc40 connected — 6 controls live")]
    d.on = False
    rig.poll(1 / 60, 0.0)
    assert said[-1][3] == "apc40 lost — 6 controls wait" and told == [1, 1, 1]
    # no rows wanted: the connection alone
    assert devices.said_words("apc40", "lost", "connected", []) == "apc40 connected"
    assert devices.said_words("leap", "off", "connected",
                              [Want("leap", "connected", "hand", ("a", "b", "c"))]) == \
        "leap on — 3 rows live"
    assert devices.said_words("leap", "connected", "off") == "leap off"
    assert devices.said_words("leap", "connected", "error: boom") == ""


def test_two_devices_changing_in_one_frame_tell_the_listeners_once():
    a, b = _Flip("apc40"), _Flip("launch")
    rig = devices.DeviceRegistry(devices=[a, b])
    told: list[int] = []
    said: list[str] = []
    rig.said = lambda role, was, now: said.append(role)
    rig.listeners.append(lambda: told.append(1))
    rig.open_all()
    a.on = b.on = True
    rig.poll(1 / 60, 0.0)
    assert told == [1, 1] and said == ["apc40", "launch"]


def test_an_error_is_no_coming_or_going_but_a_failed_open_that_succeeds_is():
    """A poll that raises on an open device flaps nothing (its error line
    says it); a device that would not open waits as `lost`, and the open
    that finally succeeds is said as a connection, the listeners told once."""
    log: list[str] = []
    d = _Flip("apc40")
    d.on = True
    rig = devices.DeviceRegistry(devices=[d])
    said: list[tuple] = []
    told: list[int] = []
    rig.said = lambda role, was, now: said.append((role, was, now))
    rig.listeners.append(lambda: told.append(1))
    rig.open_all()

    def boom(dt, now):
        raise RuntimeError("flaky")
    for k in range(10):
        d.poll = boom if k % 2 == 0 else (lambda dt, now: None)
        rig.poll(1 / 60, 0.0)
    assert said == [] and told == [1]
    # a failed open, retried
    clock = [100.0]

    class Shut(_Flip):
        fails = True

        @property
        def status(self) -> str:
            return f"error: {self.error}" if self.error else super().status

        def open(self):
            log.append("open")
            if self.fails:
                raise RuntimeError("no port")
            self.on = True

    s = Shut("launch")
    s.io = None
    rig2 = devices.DeviceRegistry(devices=[s], clock=lambda: clock[0], notes=[])
    rig2.said = lambda role, was, now: said.append((role, was, now))
    rig2.listeners.append(lambda: told.append(2))
    rig2.open_all()
    assert s.status.startswith("error") and told == [1, 2]
    s.fails = False
    clock[0] += devices.RETRY_S
    rig2.poll(1 / 60, 0.0)
    assert s.status == "connected" and told == [1, 2, 2]
    assert said == [("launch", "lost", "connected")]
    assert devices.said_words("launch", "lost", "connected") == "launch connected"


def test_a_broken_hook_is_a_note_never_the_frames_end():
    d = _Flip("apc40")
    rig = devices.DeviceRegistry(devices=[d], notes=[])

    def boom(role, was, now):
        raise RuntimeError("no footer")
    rig.said = boom
    rig.open_all()
    d.on = True
    rig.poll(1 / 60, 0.0)
    assert any("no footer" in n for n in rig.notes)


def test_a_midi_device_coming_back_fires_the_listeners_once_and_the_hook_once(inputs_build):  # noqa: F811
    """The real thing over the fake bus: the APC40 not plugged in at launch
    reads `lost`; plugged in, its own retry (`midi.Ports`) finds it and
    relights the desk inside `poll` — the registry sees the status move
    and says it once, with the preset layer's control count."""
    r = inputs_build(entries(launch=False), plug=())
    rig = r.devices
    apc = rig.get("apc40")
    assert apc.status == "lost"
    told: list[int] = []
    said: list[str] = []
    rig.listeners.append(lambda: told.append(1))
    rig.said = lambda role, was, now: said.append(devices.arrival(r.table, rig, role, was, now))
    for _ in range(5):
        frame(r)
    assert told == [] and said == []
    n = len({b.source for b in r.table.desk() if b.enabled})
    assert n > 0
    io = apc.io
    r.bus.plug(APC)
    io.ports._next_try = 0.0                          # its retry is due
    frame(r)
    assert apc.status == "connected" and apc.io is io
    for _ in range(5):
        frame(r)
    assert told == [1]
    assert said == [f"apc40 connected — {n} controls live"]


def test_a_device_added_to_config_says_it_through_apply():
    t = table_of(*HAND_ROWS)
    rig = devices.DeviceRegistry([DESK], ctx=devices.Context(table=t))
    said: list[str] = []
    rig.said = lambda role, was, now: said.append(devices.arrival(t, rig, role, was, now))
    rig.apply([DESK, {**HANDS, "enabled": False}])
    assert said == ["leap off"]
    assert rig.apply([DESK]) and said == ["leap off"]          # a removal says nothing here
    assert "leap" not in rig._status                          # …and is forgotten
