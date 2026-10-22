"""The device registry (devices.py, plan 27 B1): the protocol and its
four shims over today's adapters, the registry's three frame slots, one
device's failure never stopping the frame, the open retry on the Ports
schedule, the one close list, the config list watched, and the SYSTEM
page's lines. Every adapter here is a fake: no port, no pad, no tracker."""

from __future__ import annotations

import ast
import importlib
import os
from pathlib import Path
from types import SimpleNamespace

from hyperspace import config, devices, hotreload, ui


class Fake(devices.Base):
    """A device that logs every call under its role; `raise_in` names the
    call that raises; `open_fails` makes `open` raise until cleared."""

    kind = "fake"
    schemes = ("fake",)

    def __init__(self, role: str, log: list[str], *, raise_in: str | None = None,
                 open_fails: bool = False, opened: bool = True):
        super().__init__(role, io=object() if opened else None)
        self.log, self.raise_in, self.open_fails = log, raise_in, open_fails

    def _hit(self, name: str) -> None:
        self.log.append(f"{self.role}.{name}")
        if name == self.raise_in:
            raise RuntimeError("boom")

    def open(self) -> None:
        self._hit("open")
        if self.open_fails:
            raise RuntimeError("no port")
        self.io = object()

    def poll(self, dt: float, now: float) -> None:
        self._hit("poll")

    def learn(self, learn) -> bool:
        self._hit("learn")
        return False

    def act(self, router) -> None:
        self._hit("act")

    def feed(self, router) -> None:
        self._hit("feed")

    def send(self, reg, analyzer) -> None:
        self._hit("send")

    def close(self) -> None:
        self.io = None
        self._hit("close")


# ---------------------------------------------------------------- the protocol

def test_the_retry_schedule_is_the_ports_schedule():
    """A device that would not open is tried again as midi.Ports looks for
    a missing port: every 2 s five times, then every 10 s — restated in
    devices.py because midi is imported only behind an entry."""
    from hyperspace import midi

    assert (devices.RETRY_S, devices.RETRY_FAST, devices.RETRY_SLOW_S) == (
        midi.RECONNECT_S, midi.RECONNECT_FAST, midi.RECONNECT_SLOW_S)
    assert [devices.retry_after(n) for n in range(9)] == [midi.retry_after(n) for n in range(9)]


def test_the_kinds_table_maps_each_kind_and_make_sorts_an_entry():
    """`[[devices]] kind` → the device class, here and nowhere else; an
    entry that is not enabled is `off`, a kind the table lacks an error
    line — never a crash, never an import."""
    # plan 27 B3 adds the midi-out sink; B4 the recorded cloud and the OSC device: one line each
    assert set(devices.KINDS) == {"midi", "gamepad", "hands", "bridge", "midi-out", "osc", "cloud"}
    assert devices.MidiDevice.schemes == ("cc", "note", "pitch")
    assert devices.PadDevice.schemes == ("axis", "pad", "hat")
    assert devices.HandsDevice.schemes == ("hand", "hands")      # B2: C4's pair scheme too
    assert devices.BridgeDevice.schemes == ("ext",)
    for kind, cls in devices.KINDS.items():
        d = devices.make({"role": "r", "kind": kind, "enabled": True})
        assert isinstance(d, cls) and d.role == "r" and d.kind == kind
        assert isinstance(d, devices.Device)                 # the protocol, structurally
        assert d.status == "lost" and d.last == ""
    assert devices.make({"role": "r", "kind": "midi"}).sources == ()      # (no adapter yet)
    assert len(devices.make({"role": "r", "kind": "gamepad"}).sources) == 22   # (a fixed layout; + SHARE, #197)
    off = devices.make({"role": "r", "kind": "midi", "enabled": False})
    assert isinstance(off, devices.OffDevice) and off.status == "off" and off.kind == "midi"
    odd = devices.make({"role": "r", "kind": "wand", "enabled": True})
    assert isinstance(odd, devices.UnknownDevice) and odd.status == "error: unknown kind 'wand'"
    assert devices.Port("x", "X") == devices.Port("x", "X", "value", 0.0, False, False, "", "", "")
    # a port knows its scheme, so a row's source — a cable (plan 28) — is one property
    assert devices.Port("LX", "left stick X", scheme="axis").address == "axis:LX"
    assert devices.Port("0:48", "track knob 1", scheme="cc").address == "cc:0:48"
    assert devices.Port("x", "X").address == "x"                       # (no scheme: bare)
    assert off.schemes == ("cc", "note", "pitch") and off.feeds == ()   # off, still its kind's


def test_a_second_enabled_device_claiming_a_scheme_is_refused_with_a_note(monkeypatch):
    """Roles are not schemes for today's devices (`pad` feeds `axis`,
    `leap` feeds `hand`), and the Router holds one vector per fed key. The
    registry claims (scheme, role), not scheme (plan 27 B6): a kind that
    can qualify (the gamepad) opens a second entry under its role
    (``axis@pad2``); a kind that cannot (the hands) is refused when a
    second enabled entry would feed what the first feeds — an error line
    naming both roles, never opened, as if `enabled = false` — and comes
    up when the first leaves the list. MIDI feeds nothing (its messages
    are rows), so a second desk of another role is accepted."""
    entries = [
        {"role": "pad", "kind": "gamepad", "enabled": True},
        {"role": "pad2", "kind": "gamepad", "enabled": True},
        {"role": "leap", "kind": "hands", "enabled": True},
        {"role": "leap2", "kind": "hands", "enabled": True},
        {"role": "leap3", "kind": "hands", "enabled": False},
        {"role": "apc40", "kind": "midi", "enabled": True},
        {"role": "launchpad", "kind": "midi", "enabled": True},
    ]
    notes: list[str] = []
    reg = devices.DeviceRegistry(entries, devices.Context(hand_settings=None), notes=notes)
    pad2, leap2, leap3, lp = (reg.get(r) for r in ("pad2", "leap2", "leap3", "launchpad"))
    assert isinstance(pad2, devices.PadDevice) and pad2.qualifier == "pad2"   # B6: a second pad
    assert isinstance(leap2, devices.RefusedDevice)
    assert leap2.status == "error: feeds 'hand', which leap already feeds — not opened"
    assert isinstance(lp, devices.MidiDevice) and lp.status == "lost"    # a second desk: fine
    assert isinstance(leap3, devices.OffDevice) and leap3.status == "off"   # off claims nothing
    for cls in (devices.PadDevice, devices.MidiDevice):
        monkeypatch.setattr(cls, "open", lambda self: None)      # no port, no pad asked for
    monkeypatch.setattr(devices.HandsDevice, "open", lambda self: None)
    reg.open_all()
    for _ in range(3):
        reg.poll(1 / 60, 0.0, router=object())
    assert leap2.io is None
    assert [n for n in notes if "leap2" in n] == [
        "config: [[devices]] leap2: feeds 'hand', which leap already feeds — not opened"]
    assert not any("launchpad" in n or "pad2" in n for n in notes)
    assert [r for r, _, st, _, _ in reg.lines() if r in ("apc40", "launchpad")] == [
        "apc40", "launchpad"]                               # both desks on the SYSTEM page
    assert reg.schemes() == ("axis", "pad", "hat", "axis@pad2", "pad@pad2", "hat@pad2",
                             "hand", "hands", "cc", "note", "pitch")
    # the first hands device leaves the list: leap2 is no longer refused and opens
    monkeypatch.undo()
    monkeypatch.setattr(devices.PadDevice, "open", lambda self: None)
    monkeypatch.setattr(devices.HandsDevice, "open", lambda self: None)
    reg.apply([e for e in entries if e["role"] != "leap"])
    leap2 = reg.get("leap2")
    assert isinstance(leap2, devices.HandsDevice)
    assert "devices: leap removed" in notes and "devices: leap2 changed — reopened" in notes
    reg.close()


def test_two_pads_open_each_under_its_role(monkeypatch):
    """Plan 27 B6: two enabled gamepad entries both open; the first is
    the primary (its ports bare, every row before B6 its), the second
    publishes under its role — its sources, schemes, feeds and rows
    qualified — and arms the same Learn pad. The SYSTEM page names both
    pads with the joystick each reads. The first leaving the list makes
    the second the primary: it reopens with its ports bare."""
    from hyperspace import gamepad as gp

    entries = [{"role": "pad", "kind": "gamepad", "enabled": True, "usb": False},
               {"role": "p2", "kind": "gamepad", "enabled": True, "usb": False}]
    notes: list[str] = []
    table = SimpleNamespace(midi_roles=(), primaries={})
    reg = devices.DeviceRegistry(entries, devices.Context(table=table), notes=notes)
    one, two = reg.get("pad"), reg.get("p2")
    assert isinstance(one, devices.PadDevice) and isinstance(two, devices.PadDevice)
    assert (one.qualifier, two.qualifier) == ("", "p2")
    assert one.schemes == ("axis", "pad", "hat") and two.schemes == ("axis@p2", "pad@p2", "hat@p2")
    assert two.feeds == ("axis@p2",) and two.rows == ("pad@p2", "hat@p2")
    assert [p.address for p in one.sources][:2] == ["axis:LX", "axis:LY"]
    assert [p.address for p in two.sources][:2] == ["axis@p2:LX", "axis@p2:LY"]
    assert "pad@p2:A" in [p.address for p in two.sources]
    assert "hat@p2:UP" in [p.address for p in two.sources]
    assert reg.schemes() == ("axis", "pad", "hat", "axis@p2", "pad@p2", "hat@p2")
    assert reg.continuous_schemes() == ("lane", "lfo", "env", "seq", "axis", "axis@p2")
    assert reg.row_schemes() == ("pad", "hat", "pad@p2", "hat@p2")
    # Learn pad (whichever pad moves) and "Learn p2" (that pad only)
    assert reg.wants() == ("pad", "p2")
    assert one.wants == ("pad",) and two.wants == ("pad", "p2")
    assert reg.primaries() == {"axis": "pad", "pad": "pad", "hat": "pad"}
    assert table.primaries == reg.primaries()               # the table is told
    # two joysticks: each pad reads its own, and its line says which
    present = {0, 1}
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: j in present)
    monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: ([0] * 16, 16))
    monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: ([0], 1))
    monkeypatch.setattr(gp.glfw, "get_joystick_axes",
                        lambda j: ([0.0, 0.0, 0.0, 0.0, -1.0, -1.0], 6))
    reg.open_all()
    reg.poll(1 / 60, 0.0)
    assert ui.device_lines(reg) == [
        "pad  ·  gamepad  ·  connected  ·  22 sources  ·  glfw 0",
        "p2  ·  gamepad  ·  connected  ·  22 sources  ·  glfw 1"]
    assert one.io.claims is two.io.claims                   # one shared set of taken joysticks
    present.discard(0)
    reg.poll(1 / 60, 0.0)
    assert [st for _, _, st, _, _ in reg.lines()] == ["lost", "connected"]
    # the first pad leaves: p2 is the primary now, its rows bare
    reg.apply(entries[1:])
    two = reg.get("p2")
    assert two.qualifier == "" and two.schemes == ("axis", "pad", "hat")
    assert "devices: p2 changed — reopened" in notes
    assert two.wants == ("pad",) and reg.wants() == ("pad",)
    reg.close()


def test_two_pads_with_usb_on_the_reader_is_lent_to_the_one_without_a_joystick(monkeypatch):
    """Ruling 3 as amended: both entries at the default `usb = true`; the
    Bluetooth pad reads GLFW joystick 0, so the one USB reader is lent to
    the second pad — its line names the wired pad, the first says to whom
    the reader is lent."""
    from hyperspace import gamepad as gp

    class Wired:
        name, note = "Afterglow", ""

        def latest(self):
            return gp.decode(bytes((0x00, 0x14)) + bytes(18))

        def close(self):
            pass

    monkeypatch.setattr(gp, "UsbPad", Wired)
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: j == 0)
    monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: ([0] * 16, 16))
    monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: ([0], 1))
    monkeypatch.setattr(gp.glfw, "get_joystick_axes",
                        lambda j: ([0.0, 0.0, 0.0, 0.0, -1.0, -1.0], 6))
    entries = [{"role": "pad", "kind": "gamepad", "enabled": True},
               {"role": "p2", "kind": "gamepad", "enabled": True}]
    reg = devices.DeviceRegistry(config_entries(entries), devices.Context())
    reg.open_all()
    reg.poll(1 / 60, 0.0)
    assert ui.device_lines(reg) == [
        "pad  ·  gamepad  ·  connected  ·  22 sources  ·  glfw 0  ·  usb: lent to p2",
        "p2  ·  gamepad  ·  connected  ·  22 sources  ·  usb: Afterglow"]
    reg.close()


def config_entries(entries: list[dict]) -> list[dict]:
    """Entries with the kind's defaults filled in, as config.devices gives them."""
    return [{**config._kind_defaults(e["kind"]), **e} for e in entries]


def test_a_role_listed_twice_is_refused_and_a_joystick_pins_a_pad():
    """make_all refuses a true collision — a second enabled entry of the
    same role (config drops one at load already; the registry holds the
    line too) — and an entry's ``joystick = n`` pins its pad."""
    made = devices.make_all([
        {"role": "pad", "kind": "gamepad", "enabled": True},
        {"role": "pad", "kind": "gamepad", "enabled": True},
        {"role": "p2", "kind": "gamepad", "enabled": True, "joystick": 1, "usb": False}])
    assert isinstance(made[0], devices.PadDevice)
    assert isinstance(made[1], devices.RefusedDevice)
    assert made[1].status == "error: role 'pad' is listed twice — not opened"
    p2 = made[2]
    assert p2.joystick == 1 and p2.qualifier == "p2"
    p2.open()
    try:
        assert p2.io.joystick == 1 and p2.io.claims.pinned == {1: p2.io}
        assert p2.last == "waiting for joystick 1"
    finally:
        p2.close()


def test_the_joystick_key_is_checked(tmp_path):
    """A gamepad entry's `joystick` (plan 27 B6) is a GLFW index, 0–15: a
    whole number in range pins the pad; anything else is a note and the
    pad takes the next free one."""
    path = tmp_path / "config.toml"
    path.write_text('[[devices]]\nrole = "pad"\nkind = "gamepad"\n'
                    '[[devices]]\nrole = "p2"\nkind = "gamepad"\njoystick = "x"\n'
                    '[[devices]]\nrole = "p3"\nkind = "gamepad"\njoystick = 2\n'
                    '[[devices]]\nrole = "p4"\nkind = "gamepad"\njoystick = 16\n')
    cfg = config.load(path)
    ents = {e["role"]: e for e in config.devices(cfg)}
    assert "joystick" not in ents["pad"] and "joystick" not in ents["p2"]
    assert ents["p3"]["joystick"] == 2 and "joystick" not in ents["p4"]
    said = [n for n in cfg["notes"] if "joystick" in n]
    assert len(said) == 2 and "'x'" in said[0] and "16" in said[1]
    from hyperspace import gamepad as gp
    assert len(gp.JOYSTICKS) == config.JOYSTICKS           # the two counts agree
    # one GLFW index, one pad: a second entry pinned to it is dropped, said
    path.write_text('[[devices]]\nrole = "pad"\nkind = "gamepad"\njoystick = 1\n'
                    '[[devices]]\nrole = "p2"\nkind = "gamepad"\njoystick = 1\n')
    cfg = config.load(path)
    assert [e["role"] for e in config.devices(cfg)] == ["pad"]
    assert any("joystick = 1 is pinned by an earlier pad" in n for n in cfg["problems"])


# ---------------------------------------------------------------- the frame slots

def test_devices_run_in_list_order_poll_learn_act_then_feed_then_send():
    """The scene-setter slot polls each open device, offers it the armed
    Learn, then takes its rows; the feed slot feeds; the sink slot sends
    — each in the list's order, a device at a time."""
    log: list[str] = []
    reg = devices.DeviceRegistry(devices=[Fake("a", log), Fake("b", log)])
    assert len(reg) == 2 and [d.role for d in reg] == ["a", "b"]
    reg.poll(1 / 60, 1.0, router=object(), learn=object())
    assert log == ["a.poll", "a.learn", "a.act", "b.poll", "b.learn", "b.act"]
    log.clear()
    reg.feed(object())
    reg.send(object(), None)
    assert log == ["a.feed", "b.feed", "a.send", "b.send"]
    log.clear()
    reg.poll(1 / 60, 1.0)                               # no router, no learn: polled only
    assert log == ["a.poll", "b.poll"]
    # a device that is not open is skipped in every slot
    log.clear()
    reg = devices.DeviceRegistry(devices=[Fake("a", log, opened=False), Fake("b", log)])
    reg.poll(1 / 60, 1.0, router=object())
    reg.feed(object())
    assert log == ["b.poll", "b.act", "b.feed"]


def test_one_devices_exception_never_stops_the_frame():
    """A raising step is the device's `error: …` and the registry's
    `error` (the first one this frame, for the toast); the next device
    runs, and a clean frame clears both."""
    log: list[str] = []
    a, b = Fake("a", log, raise_in="poll"), Fake("b", log, raise_in="feed")
    reg = devices.DeviceRegistry(devices=[a, b])
    reg.poll(1 / 60, 1.0, router=object())
    assert log == ["a.poll", "b.poll", "b.act"]
    assert a.status == "error: RuntimeError: boom" and b.status == "connected"
    assert reg.error == "fake: RuntimeError: boom"
    reg.feed(object())
    assert b.status == "error: RuntimeError: boom" and reg.error == "fake: RuntimeError: boom"
    a.raise_in = b.raise_in = None
    reg.poll(1 / 60, 2.0, router=object())
    assert reg.error == "" and a.status == "connected"
    reg.feed(object())
    assert b.status == "connected"


# ---------------------------------------------------------------- opening, retrying, closing

class Lost(Fake):
    """An open device whose hardware is not there: it looks for it itself."""

    @property
    def status(self) -> str:
        return "lost"


def test_the_registry_retries_a_failed_open_and_a_lost_device_reconnects_itself():
    """Whose job reconnect is: an `open` that raised is the registry's to
    try again, on the Ports schedule; a device whose `open` returned and
    reports `lost` reconnects itself (today's adapters do, inside their
    own `poll`) — the registry never closes or reopens it."""
    log: list[str] = []
    notes: list[str] = []
    clock = SimpleNamespace(t=100.0)
    d = Fake("a", log, open_fails=True, opened=False)
    lost = Lost("b", log)
    reg = devices.DeviceRegistry(devices=[d, lost], clock=lambda: clock.t, notes=notes)
    reg.entries = [{"role": "a", "kind": "fake", "enabled": True},
                   {"role": "b", "kind": "fake", "enabled": True}]
    seen: list[int] = []
    reg.listeners.append(lambda: seen.append(len(reg)))
    reg.open_all()
    assert d.status == "error: RuntimeError: no port" and notes == ["fake: no port"]
    assert log == ["a.open"] and seen == [2]
    assert lost.status == "lost" and "b.open" not in log            # open, looking itself
    # tried again on the Ports schedule: 2 s, five times, then every 10 s
    tries = [100.0]
    for _ in range(8):
        reg.poll(1 / 60, 0.0, router=object())              # not yet
        assert log.count("a.open") == len(tries)
        clock.t = tries[-1] + (devices.RETRY_S if len(tries) <= devices.RETRY_FAST
                               else devices.RETRY_SLOW_S)
        reg.poll(1 / 60, 0.0, router=object())
        tries.append(clock.t)
        assert log.count("a.open") == len(tries), tries
    assert notes == ["fake: no port"]                       # said once
    assert "a.poll" not in log                              # never polled while shut
    assert "b.open" not in log and "b.close" not in log     # the lost one is left to itself…
    assert log.count("b.poll") == 16                        # …and polled every frame
    d.open_fails = False
    clock.t += devices.RETRY_SLOW_S
    reg.poll(1 / 60, 0.0, router=object())
    assert d.status == "connected" and seen == [2, 2]       # the listener re-points
    assert log[-5:] == ["a.open", "a.poll", "a.act", "b.poll", "b.act"]   # …runs this very frame


def test_the_close_list_is_every_device_last_listed_first_and_survives_a_broken_one():
    log: list[str] = []
    reg = devices.DeviceRegistry(devices=[Fake("a", log), Fake("b", log, raise_in="close"),
                                          Fake("c", log)])
    notes = reg.notes
    reg.close()
    assert log == ["c.close", "b.close", "a.close"]
    assert notes == ["fake: RuntimeError: boom"]
    assert all(d.io is None for d in reg) and reg.adapter("fake") is None
    log.clear()
    reg.poll(1 / 60, 0.0, router=object())                 # closed: nothing runs
    assert log == []


def test_adapter_first_get_and_schemes():
    log: list[str] = []
    a, b = Fake("a", log), Fake("b", log, opened=False)
    b.kind = "other"
    reg = devices.DeviceRegistry(devices=[a, b])
    assert reg.get("a") is a and reg.get("zz") is None
    assert reg.first("fake") is a and reg.first("other") is b and reg.first("x") is None
    assert reg.adapter("fake") is a.io and reg.adapter("other") is None
    assert reg.schemes() == ("fake",)


def test_continuous_schemes_are_the_builtins_then_each_devices_feeds_in_list_order():
    """What B2 hands the Router in place of `LANE_SCHEMES` / `SOURCE_ORDER`:
    `lane` and `lfo` first, then the schemes the listed devices feed —
    the pad's `axis` (not its `pad` / `hat` rows), the hands' `hand`, the
    bridge's `ext`; MIDI feeds nothing; an `off` device's scheme is still
    listed, so a preset row naming it is dormant, not unknown."""
    io = SimpleNamespace(on=False, error="", last="", name="", profile=None, bindings=[])
    reg = devices.DeviceRegistry(devices=[
        devices.MidiDevice("apc40", io=io), devices.PadDevice("pad", io=io),
        devices.OffDevice("leap", "hands"), devices.BridgeDevice("bridge", io=io)])
    assert devices.BUILTIN_SCHEMES == ("lane", "lfo", "env", "seq")
    assert reg.continuous_schemes() == ("lane", "lfo", "env", "seq", "axis", "hand", "hands", "ext")
    assert reg.schemes() == ("cc", "note", "pitch", "axis", "pad", "hat", "hand", "hands", "ext")
    assert devices.DeviceRegistry([]).continuous_schemes() == ("lane", "lfo", "env", "seq")


def test_a_bridge_on_or_off_arms_no_learn():
    """The bridge feeds `ext` but has no `learn`: a rig that lists one, on
    or off, offers no Learn item for it (review pass, Important 1)."""
    io = SimpleNamespace(on=False, error="", last="", name="", profile=None, bindings=[])
    reg = devices.DeviceRegistry(devices=[
        devices.BridgeDevice("bridge", io=io), devices.OffDevice("b2", "bridge")])
    assert reg.wants() == ()


# ---------------------------------------------------------------- config.toml, watched

def _write(path: Path, text: str, bump: float) -> None:
    path.write_text(text)
    os.utime(path, (bump, bump))


def test_the_config_list_is_watched_every_30_frames_and_a_bad_edit_keeps_the_old_list(tmp_path):
    """The registry re-reads only the `[[devices]]` list when the file's
    mtime moved (every WATCH_FRAMES polls): what left is closed, what
    arrived is opened, a changed entry is reopened, the rest stay. A file
    that will not parse, or an entry that had to be dropped, is a note and
    the old list stands."""
    p = tmp_path / "config.toml"
    _write(p, '[[devices]]\nrole = "a"\nkind = "gamepad"\nenabled = false\n'
              '[[devices]]\nrole = "b"\nkind = "bridge"\nenabled = false\n', 1000.0)
    cfg = config.load(p)
    notes: list[str] = []
    reg = devices.DeviceRegistry(config.devices(cfg), path=p, notes=notes)
    reg.open_all()
    assert [(d.role, d.status) for d in reg] == [("a", "off"), ("b", "off")]
    a = reg.get("a")
    _write(p, '[[devices]]\nrole = "a"\nkind = "gamepad"\nenabled = false\nusb = false\n'
              '[[devices]]\nrole = "c"\nkind = "midi"\nenabled = false\n', 1001.0)
    for _ in range(devices.WATCH_FRAMES - 1):
        reg.poll(1 / 60, 0.0)
    assert [d.role for d in reg] == ["a", "b"]              # not looked at yet
    reg.poll(1 / 60, 0.0)                                   # the 30th frame
    assert [(d.role, d.status) for d in reg] == [("a", "off"), ("c", "off")]
    assert reg.get("a") is not a                            # changed: reopened
    assert notes == ["devices: a changed — reopened", "devices: c added", "devices: b removed"]
    # the same content, a newer mtime: nothing changes, nothing is said
    _write(p, p.read_text(), 1002.0)
    assert reg.watch() is False and len(notes) == 3
    # a bad entry: the old list stands, with a note naming it
    kept = list(reg)
    _write(p, '[[devices]]\nrole = "x:y"\nkind = "midi"\n', 1003.0)
    assert reg.watch() is False
    assert list(reg) == kept and notes[-1].startswith("config: [[devices]] not applied — ")
    assert "role = 'x:y'" in notes[-1] and notes[-1].endswith("— the old list stands")
    # a file that will not parse: the same
    _write(p, "[[devices\n", 1004.0)
    assert reg.watch() is False and list(reg) == kept
    assert notes[-1].startswith("config: [[devices]] not applied — config: ")
    # no `[[devices]]` at all: the old tables, translated, as at launch
    _write(p, "[midi]\nenabled = false\n[gamepad]\nenabled = false\n", 1005.0)
    assert reg.watch() is True
    assert [(d.role, d.status) for d in reg] == [("pad", "off"), ("apc40", "off"),
                                                 ("leap", "off"), ("bridge", "off")]
    # no path: nothing is watched
    assert devices.DeviceRegistry([]).watch() is False


# ---------------------------------------------------------------- the SYSTEM page and hot reload

def test_lines_and_the_system_pages_text():
    log: list[str] = []
    a = Fake("a", log)
    b = devices.OffDevice("b", "hands")
    reg = devices.DeviceRegistry(devices=[a, b])
    assert reg.lines() == [("a", "fake", "connected", 0, ""), ("b", "hands", "off", 0, "")]
    assert ui.device_lines(reg) == ["a  ·  fake  ·  connected  ·  0 sources",
                                    "b  ·  hands  ·  off  ·  0 sources"]
    pad = devices.PadDevice("pad", io=SimpleNamespace(on=True, source="usb",
                                                       usb_pad=SimpleNamespace(name="AX.1")))
    assert ui.device_lines(devices.DeviceRegistry(devices=[pad])) == [
        "pad  ·  gamepad  ·  connected  ·  22 sources  ·  usb: AX.1"]
    # a status that raises is a line, not a page that will not draw
    bad = Fake("c", log)
    type(bad).last = property(lambda self: 1 / 0)
    try:
        assert devices.DeviceRegistry(devices=[bad]).lines()[0][2].startswith("status: ZeroDiv")
    finally:
        del type(bad).last


def test_every_swap_target_the_registry_hands_the_reloader_is_watched_and_defined():
    """`DeviceRegistry.targets` — the adapters, the shims, the registry —
    name (module, class) pairs the hot reloader can swap: each module on
    `hotreload.MODULES`, each class defined there (audit H1, as
    tests/test_hotreload.py holds for app.py's own list)."""
    io = SimpleNamespace(on=False, error="", last="", name="", profile=None, close=lambda: None)
    reg = devices.DeviceRegistry(devices=[
        devices.MidiDevice("apc40", io=io), devices.PadDevice("pad", io=io),
        devices.HandsDevice("leap", io=io), devices.BridgeDevice("bridge", io=io),
        devices.OffDevice("x", "osc")])
    pairs = {(m, c) for _, m, c in reg.targets()}
    assert pairs == {("devices", "DeviceRegistry"), ("devices", "MidiDevice"), ("midi", "MidiIO"),
                     ("devices", "PadDevice"), ("gamepad", "Pad"), ("hands.device", "HandsDevice"),
                     ("hands.core", "HandsIO"), ("devices", "BridgeDevice"), ("bridge", "Bridge"),
                     ("devices", "OffDevice")}
    assert "devices" in hotreload.MODULES
    root = Path(devices.__file__).parent
    for mod, cls in sorted(pairs):
        assert mod in hotreload.MODULES, mod
        src = root / (mod.replace(".", "/") + ".py")
        defined = {n.name for n in ast.parse(src.read_text()).body if isinstance(n, ast.ClassDef)}
        assert cls in defined, f"{cls} is not defined in {mod}"
    assert all(getattr(importlib.import_module(f"hyperspace.{m}"), c) for m, c in pairs
               if m != "midi")   # (midi is imported by other tests anyway; keep this one gated)


# ---------------------------------------------------------------- the four shims

def test_the_pad_shim_polls_learns_and_delivers_rows_as_the_frame_did(monkeypatch):
    """`pad.poll()`, `gamepad.learn_from`, then `router.pad(pad, buttons=…)`
    with the buttons held back on the frame a press completed a learn."""
    from hyperspace import gamepad

    calls: list = []
    pad = SimpleNamespace(poll=lambda: calls.append("poll"), on=True, source="glfw", usb_pad=None)
    router = SimpleNamespace(pad=lambda p, buttons: calls.append(("rows", p is pad, buttons)))
    monkeypatch.setattr(gamepad, "learn_from", lambda p, learn: calls.append(("learn", learn)) or
                        learn == "taken")
    d = devices.PadDevice("pad", io=pad)
    d.poll(1 / 60, 0.0)
    assert d.learn("taken") is True
    d.act(router)
    assert calls == ["poll", ("learn", "taken"), ("rows", True, False)]
    calls.clear()
    d.poll(1 / 60, 0.0)
    assert d.learn("other") is False
    d.act(router)
    assert calls == ["poll", ("learn", "other"), ("rows", True, True)]
    assert d.status == "connected" and d.last == "glfw"
    assert [p.name for p in d.sources][:6] == list(gamepad.AXES)
    assert [p.address for p in d.sources][:6] == [f"axis:{n}" for n in gamepad.AXES]
    assert "pad:A" in [p.address for p in d.sources] and "hat:UP" in [p.address for p in d.sources]
    assert [p.kind for p in d.sources].count("trigger") == len(gamepad.BUTTONS) + len(gamepad.HATS)
    assert {p.name: p.rest for p in d.sources if p.group == "sticks"} == {
        "LX": 0.5, "LY": 0.5, "RX": 0.5, "RY": 0.5}
    assert all(p.bipolar for p in d.sources if p.group == "sticks")
    pad.on = False
    pad.usb_pad = SimpleNamespace(note="usb pad: pyusb is not installed")
    assert d.status == "lost" and d.last == "usb pad: pyusb is not installed"


def test_the_hands_shim_makes_the_instruments_one_call_from_the_feed_slot():
    """`HandsIO.poll(dt, learn, router)` reads the tracker, feeds `hand`
    and completes a learn at once, so the shim calls it in `feed`, with the
    frame's dt and the Learn it was offered in the scene-setter slot."""
    calls: list = []
    io = SimpleNamespace(poll=lambda dt, learn, router: calls.append((dt, learn, router)),
                         status="tracking", source=SimpleNamespace(on=True), last="", error="",
                         close=lambda: calls.append("close"))
    d = devices.HandsDevice("leap", io=io)
    d.poll(0.02, 1.0)
    assert d.learn("L") is False and calls == []
    d.feed("R")
    assert calls == [(0.02, "L", "R")]
    assert d.status == "connected" and d.last == "tracking"
    io.status, io.source.on = "connecting", False
    assert d.status == "lost"
    io.status = "OSError: no tracker"
    assert d.status == "error: OSError: no tracker"
    io.status = "tape"
    assert d.status == "lost"
    d.close()
    assert calls[-1] == "close" and d.io is None


def test_the_hands_shims_ports_are_the_layout():
    from hyperspace.hands import HandSettings, HandsIO

    class Source:
        status, on = "fake", True

        def latest(self):
            return 0, 0.0, {}

    io = HandsIO(HandSettings.from_config({}), {"out": ""}, source=Source(), out=None)
    d = devices.HandsDevice("leap", io=io)
    ports = d.sources
    # B2: the `hand` lanes, then the pair's `hands` lanes (C4's gap, twist)
    pair = io.layout.pair_addresses
    assert len(ports) == io.layout.n + len(pair) and io.layout.n >= 22   # the layout's counts
    assert [p.name for p in ports] == io.layout.addresses + pair
    assert [p.address for p in ports] == ([f"hand:{a}" for a in io.layout.addresses]
                                          + [f"hands:{a}" for a in pair])
    assert [p.rest for p in ports if p.scheme == "hands"] == io.pair_rests()
    assert [p.group for p in ports].count("axes") == io.layout.n_axes
    assert [p.group for p in ports].count("presence") == 2
    n_gates = len(io.layout.gates)        # the pinches, and plan 24 C5's grabs
    assert n_gates >= 8
    assert [p.group for p in ports].count("switches") == n_gates
    assert [p.group for p in ports].count("dance") == (
        io.layout.n - io.layout.n_axes - 2 - n_gates + len(pair))
    assert all(p.kind == "value" for p in ports)
    roll = next(p for p in ports if p.name == "right.roll")
    assert roll.bipolar is True and roll.rest == 0.5 and roll.label == "R roll"
    io.close()


def test_the_bridge_is_one_device_with_a_source_half_and_a_sink_half():
    """Plan 27 B3 (was B1's `step` shim): the ports are looked for again in
    `poll`, the ext lanes received and published in the feed slot, and the
    out half sent in the sink slot — from the analyzer the frame hands
    `send` (None while audio is off), the bare shim's old `send` list."""
    calls: list = []
    io = SimpleNamespace(reconnect=lambda: calls.append("reconnect"),
                         receive=lambda router: calls.append(("receive", router)),
                         publish=lambda router: calls.append(("publish", router)),
                         transmit=lambda chain: calls.append(("transmit", chain)),
                         on=True, error="", name="IAC", encoding="pitch", channel=0, cc=16,
                         room=16, sent=3, decoder=SimpleNamespace(n=4))
    d = devices.BridgeDevice("bridge", io=io)
    d.poll(0.0, 0.0)
    d.feed("R")
    d.send("REG", "CHAIN")
    d.send("REG", None)
    assert calls == ["reconnect", ("receive", "R"), ("publish", "R"), ("transmit", "CHAIN"),
                     ("transmit", None)]
    assert d.status == "connected" and d.last == "IAC  ·  pitch, 16 lanes  ·  3 sent"
    assert [p.address for p in d.sinks][:2] == ["bridge:0", "bridge:1"] and len(d.sinks) == 16
    assert [p.name for p in d.sources] == ["0", "1", "2", "3"]
    io.on = False
    assert d.status == "lost" and d.last == ""
    io.error = "read: gone"
    assert d.status == "error: read: gone"
    assert devices.BridgeDevice("b", {"in_lanes": 2}).sources == (
        devices.Port("0", "ext 0", group="ext", scheme="ext"),
        devices.Port("1", "ext 1", group="ext", scheme="ext"))


def test_the_midi_shim_polls_and_reads_its_status_off_the_ports():
    from hyperspace import apc40

    calls: list = []
    io = SimpleNamespace(poll=lambda: calls.append("poll"), on=True, error="", name="Akai APC40",
                         last="", profile=apc40, bindings=[1, 2])
    d = devices.MidiDevice("apc40", io=io)
    d.poll(1 / 60, 0.0)
    d.act(object())
    d.feed(object())
    assert calls == ["poll"]                                # rows and learn happen in poll
    # the line keeps the port's name and the binding count the old MIDI line
    # showed, then the last message once one has come
    assert d.status == "connected" and d.last == "Akai APC40  ·  2 bindings"
    io.last = "cc 0 48 = 64"
    assert d.last == "Akai APC40  ·  2 bindings  ·  cc 0 48 = 64"
    ports = d.sources
    assert len(ports) == len(apc40.LAYOUT)
    by = {p.address: p for p in ports}
    assert by["cc:0:48"].kind == "value" and by["cc:0:48"].label == apc40.control_name("cc:0:48")
    assert by["cc:0:48"].scheme == "cc" and by["cc:0:48"].name == "0:48"
    assert by["note:0:98"].kind == "trigger" and by["note:0:98"].velocity is True
    io.on = False
    assert d.status == "lost" and d.last == ""
    io.error = "open APC40: busy"
    assert d.status == "error: open APC40: busy"


def test_pad_close_stops_the_usb_reader_and_forgets_the_pad():
    """Plan 27 B1: `Pad.close()` is real — the USB reader thread is told
    to stop and joined, and the pad reads absent until a later poll finds
    one again (the pad is on the one close list, so ⌘R's new image finds
    the device free)."""
    import threading

    from hyperspace.gamepad import Pad

    stopped = threading.Event()
    t = threading.Thread(target=stopped.wait, daemon=True)
    t.start()
    usb = SimpleNamespace(close=stopped.set, _thread=t, latest=lambda: None)
    pad = Pad(usb=True)
    pad.usb_pad, pad.source, pad.buttons = usb, "usb", [1, 0]
    assert pad.on
    pad.close()
    assert stopped.is_set() and not t.is_alive()
    assert pad.usb_pad is None and pad.source is None and not pad.on and pad.buttons == []
    pad.close()                                             # twice is fine
    Pad(usb=False).close()                                  # never started: nothing to stop


# ---------------------------------------------------------------- the owner's rig, as a list

TODAYS_RIG = '''
[[devices]]
role = "pad"
kind = "gamepad"

[[devices]]
role = "apc40"
kind = "midi"
port = "APC40"

[[devices]]
role = "leap"
kind = "hands"
enabled = false

[[devices]]
role = "bridge"
kind = "bridge"
enabled = false
'''


def test_todays_rig_as_a_devices_list_equals_the_old_tables(tmp_path, capsys):
    """The exact `[[devices]]` block the owner pastes to get today's rig
    gives the same device entries as the old tables do, and nothing is
    said about it."""
    old = tmp_path / "old.toml"
    old.write_text('[midi]\nport = "APC40"\n')
    new = tmp_path / "new.toml"
    new.write_text(TODAYS_RIG)
    a, b = config.load(old), config.load(new)
    assert config.devices(a) == config.devices(b)
    assert [e["role"] for e in config.devices(b)] == ["pad", "apc40", "leap", "bridge"]
    assert a["notes"] == [("config: [midi] is now a [[devices]] entry (role = 'apc40', "
                           "kind = 'midi') — see config.py")]
    assert "notes" not in b
    for key in ("midi", "gamepad", "hands", "bridge"):
        assert a[key] == b[key], key
    assert b["midi"]["port"] == "APC40" and b["hands"]["enabled"] is False
    assert capsys.readouterr().err.count("[midi] is now") == 1
