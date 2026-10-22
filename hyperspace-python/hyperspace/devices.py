"""The device registry (plan 27): every input or output the rig has,
listed in ``config.toml`` as ``[[devices]]``, opened behind its own entry,
polled in order each frame, and closed in one list.

A *device* is anything that satisfies the `Device` protocol below:
`open()`, `poll(dt, now)`, `close()`, a `status` for the SYSTEM page, a
`role`, its `sources` (the ports it publishes), `feed(router)`,
`learn(learn)` and `wants` (what a Learn can arm it for). Today's inputs
are devices since B2: `MidiDevice` — one per MIDI entry, each with its own
`profile` (`apc40`, `generic`) and its own rows (`cc@<role>:…` for every
MIDI role but the first) —, `PadDevice` (the gamepad: its rows, its axis
lanes and the sticks' default camera job) and the hands'
`hands.device.HandsDevice` (a thin wrapper over the liftable `HandsIO`);
the bridge is one device with both halves (`BridgeDevice`: its `ext` lanes
a source, its out half a sink) and a `midi-out` entry is a sink alone
(`MidiOutDevice`: the hands' DAW out is one, role `hands-daw`). Each owns
its adapter object (`io`: `midi.MidiIO`, `gamepad.Pad`, `hands.HandsIO`,
`bridge.Bridge`). This module is the one importer of every adapter
module, each imported lazily inside its device's `open`, so importing
`app` imports none of them (tests/test_app_boundary.py).

**Roles, not serials** (decision 11): an entry has a `role` — `apc40`,
`pad`, `leap`, `wand1` — the name the SYSTEM page, the notes and a MIDI
row's qualifier (``cc@launch:0:7``) use. A role contains no ``:``. **For
today's devices the role is not the scheme:** a preset names a *scheme*
(`hand:right.roll`, `axis:LX`, `ext:3`, `cc:0:48`) and the device's
`schemes` tuple says which schemes its role publishes, so every existing
row is unchanged whatever the entry is called. A new device (B4's OSC)
publishes under its role. Two enabled devices may not **feed** one
scheme: the Router holds one vector per fed scheme (`feeds`), so a second
pad (`axis`) or a second hands device (`hand`) is refused with a note
naming both roles (`RefusedDevice`); two MIDI desks of different roles
feed nothing (their messages are rows) and are both accepted — an
unqualified MIDI row is the first MIDI role's (`midi_roles`), the second
desk's rows carry its role. One role, one entry (config drops a
duplicate role).

**Schemes from the registry** (B2): which schemes are continuous, and in
what order a page offers them, is `continuous_schemes` (the analyzer's
`lane` and the LFOs' `lfo` first, then each device's `feeds`); which a
device delivers as rows is `row_schemes`; what a Learn can be armed for is
`wants`. The Router and the Learn are handed this object as an argument
(`Router.use`, `Learn.devices`): routing and learn import nothing from
here.

**Two signal kinds** (decision 13): a port is a *value* (an axis, a
fader, a lane) or a *trigger* (a hit, a button, a pad — with a velocity
when the device sends one). Discrete controls stay scene-setters: a
device delivers them as rows through the table (`Router.pad`,
`MidiIO._handle`), never as a feed. A device may expose `layers`
(decision 14: the APC40 as two nodes in plan 28): the first MIDI role's
desk has two, the preset layer and SHIFT's global one.

**The frame.** `DeviceRegistry.poll` runs in the scene-setter slot
(after the key rows, before the macros and undo): each device is polled,
offered to an armed Learn, then delivers its rows. `feed` runs in the
feed slot (after the analyzer's lanes, before the LFOs and the pass):
each device publishes its vectors. `send` runs after `reg.apply`: the
sinks. One device's exception never stops the frame: it is recorded
on the device (`status = "error: …"`) and on the registry (`error`, the
hot-reload toast), and the next device runs.

**Coming and going — whose job reconnect is.** The registry retries a
device whose `open()` *raised*: `error: …`, said once (stderr and the
config notes), opened again on the `Ports` schedule (midi.py: every 2 s
five times, then every 10 s). A device whose `open()` returned but whose
hardware is not there reports `lost` and **reconnects itself** on its own
schedule — today's adapters do (`midi.Ports.retry`, the pad's GLFW poll
and USB rescan, the hands' Leap thread and DAW port), and a B2 / B4
device must too; the registry never closes or reopens a `lost` device
(a `Ports` of its own inside `poll` is the pattern). The registry watches `config.toml`'s
mtime every `WATCH_FRAMES` frames and re-reads only the device list,
closing what left and opening what arrived; a bad edit is a note and the
old list stands.

**Sinks** (plan 27 B3). A sink takes values *out* of the app: a device's
`sinks` are its sink ports (a `Port` whose `scheme` is the device's role and
whose `name` is the channel, so its `address` is ``<role>:<channel>`` —
``bridge:3``), and its `send(reg, analyzer)` runs in the slot after
`reg.apply`, reading **effective** values. What a sink sends is the
session's *sink rows* (routing.py, `SINK_OP`): a `Binding` from a param
(``param:<id>``) or a lane (``lane:<i>``, ``lane:*``) to a sink port, in
`bindings.json` (sinks are rig), made on the ROUTING page or by the param
menu's "Learn sink ▸ <role>:<channel>" (learn.Learn.learn_sink) — the same
table and Learn as a hand routed to a param, with no referee (a sink row is
not a performer). An entry's old `send` list (`[bridge] send`) becomes its
rows once, the first launch it is on with none (`DeviceRegistry`'s
`_seed_sinks`, one note). The SYSTEM line of a sink says how many rows it
sends (``n sinks``) before its last message.
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

# the open-retry schedule — midi.Ports' (RECONNECT_S, RECONNECT_FAST,
# RECONNECT_SLOW_S), restated here because midi is imported only behind
# a device's entry; tests/test_devices.py holds the two equal
RETRY_S = 2.0
RETRY_FAST = 5
RETRY_SLOW_S = 10.0
WATCH_FRAMES = 30        # config.toml's mtime is looked at this often (as the shaders are)
STATUSES = ("connected", "lost", "off")     # …and "error: <why>"
# fed by the analyzer, the LFOs, the envelopes and the sequencer (plan 31),
# not a device
BUILTIN_SCHEMES = ("lane", "lfo", "env", "seq")


def retry_after(misses: int) -> float:
    """Seconds until the next try to open a device, after `misses` tries
    in a row that failed — midi.retry_after's schedule."""
    return RETRY_S if misses <= RETRY_FAST else RETRY_SLOW_S


@dataclass(frozen=True)
class Port:
    """One source (or, from B3, one sink) a device publishes — what the
    node editor (plan 28) draws a device from, so there is no second
    description of it. `scheme` is the Router scheme the port lives under
    (`hand`, `axis`, `cc`), `name` the address after it (``right.roll``,
    ``LX``, ``0:48``), and `address` the row's source string,
    ``scheme:name`` — a cable can be built from a port. `kind` is
    ``value`` or ``trigger`` — or ``cloud`` (plan 27 B4: a `PointCloud`
    the device publishes on the registry, `DeviceRegistry.clouds`, never
    through the Router; its scheme is ``cloud``); `rest` where a value idles; `bipolar` a
    value centred on its rest; `velocity` a trigger that carries one;
    `group` folds a long list (the APC40's hundred controls); `layer` the
    device layer the port belongs to ("" = every layer). A *sink* port
    (plan 27 B3, `Device.sinks`) has the device's role as its `scheme`
    and a channel as its `name`, so its `address` is ``<role>:<channel>``
    — what a sink row targets."""

    name: str
    label: str
    kind: str = "value"
    rest: float = 0.0
    bipolar: bool = False
    velocity: bool = False
    group: str = ""
    layer: str = ""
    scheme: str = ""

    @property
    def address(self) -> str:
        """The source string a row names: ``scheme:name``."""
        return f"{self.scheme}:{self.name}" if self.scheme else self.name


@runtime_checkable
class Device(Protocol):
    """What the registry asks of a device. `role` names it on the SYSTEM
    page and in the notes; `kind` is its `[[devices]]` kind; `schemes`
    the Router keys it publishes under (a new device's is its role;
    today's keep the schemes their rows use) and `feeds` the subset it
    feeds continuous vectors under (the pad's `axis`, not its `pad` /
    `hat` rows; MIDI feeds nothing); `status` one of `connected`, `lost`,
    `off` or ``error: <why>``; `last` the last thing seen, for the status
    line. Reconnecting is the device's own job once `open` returned: a
    `lost` device looks for its hardware itself (as `midi.Ports` does);
    the registry retries only an `open` that raised. `poll` reads the
    hardware and, for a scene-setting device, applies its rows; `learn`
    offers a moved axis or a pressed button to an armed Learn and says
    whether a press was the learn's; `act` delivers the rest of this
    frame's discrete controls as rows; `feed` publishes the continuous
    vectors, labels, rests, gates and names; `sinks` are the device's sink
    ports (``<role>:<channel>``) and `send` the sink half, after
    `reg.apply` (plan 27 B3). `targets` are the live objects the hot reloader re-classes.
    `wants` are what a Learn can be armed for and this device completes
    (plan 27 B2: ``desk`` for MIDI, ``pad``, ``hand:left`` /
    ``hand:right``; a new device's role by default)."""

    role: str
    kind: str
    schemes: tuple[str, ...]
    feeds: tuple[str, ...]
    layers: tuple[str, ...]
    wants: tuple[str, ...]

    @property
    def status(self) -> str: ...

    @property
    def last(self) -> str: ...

    @property
    def sources(self) -> tuple[Port, ...]: ...

    @property
    def sinks(self) -> tuple[Port, ...]: ...

    def open(self) -> None: ...

    def poll(self, dt: float, now: float) -> None: ...

    def learn(self, learn) -> bool: ...

    def act(self, router) -> None: ...

    def feed(self, router) -> None: ...

    def send(self, reg, analyzer) -> None: ...

    def close(self) -> None: ...

    def targets(self) -> list[tuple]: ...


@dataclass
class Context:
    """What the device factories need from the host, handed in once:
    the registry and the binding table (MIDI), the shared Learn, the
    audio engine (the bridge sends the analyzer's lanes), the hands setup,
    the config's notes list (an open that fails is said there) and the
    home (relative paths)."""

    reg: object | None = None
    table: object | None = None
    learn: object | None = None
    audio: object | None = None
    hand_settings: object | None = None
    notes: list[str] = field(default_factory=list)
    home: Path | None = None
    # the registry itself (set by `DeviceRegistry`): a sink that carries
    # another device's output (the hands' DAW messages) finds it by role
    devices: object | None = None
    # what the pad devices share (plan 27 B6, gamepad.Claims): which GLFW
    # joystick each reads, the pinned indices, the one USB reader's owner.
    # Made by the first pad that opens
    pads: object | None = None


class Base:
    """The protocol's defaults: a device that does nothing until a
    subclass says otherwise. `entry` is its checked `[[devices]]` table,
    `ctx` the host's `Context`; a shim built in a test over an adapter of
    its own passes `io` and needs neither."""

    kind = ""
    schemes: tuple[str, ...] = ()
    feeds: tuple[str, ...] = ()
    layers: tuple[str, ...] = ()
    # plan 27 B6: may several entries of this kind be enabled at once? A
    # repeatable kind's first enabled entry (`primaries`) publishes its
    # schemes bare, as every row before B6 names them; each later one
    # publishes them under its role (``axis@p2``, `qualify`), so no two
    # feed one Router key. A kind that is not repeatable keeps B1's rule:
    # a second entry that would feed a scheme already fed is refused
    repeatable = False
    # the device's qualifier: "" for its kind's primary, else its role
    qualifier = ""

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None):
        self.role = role
        self.entry = dict(entry or {})
        self.ctx = ctx if ctx is not None else Context()
        self.io = io
        self.error = ""          # the last exception, as `status` says it

    @property
    def status(self) -> str:
        if self.error:
            return f"error: {self.error}"
        return "connected" if self.io is not None else "lost"

    @property
    def last(self) -> str:
        return ""

    @property
    def sources(self) -> tuple[Port, ...]:
        return ()

    @property
    def sinks(self) -> tuple[Port, ...]:
        return ()

    def open(self) -> None:
        pass

    def poll(self, dt: float, now: float) -> None:
        pass

    def learn(self, learn) -> bool:
        return False

    def act(self, router) -> None:
        pass

    def feed(self, router) -> None:
        pass

    def send(self, reg, analyzer) -> None:
        pass

    def close(self) -> None:
        io, self.io = self.io, None
        if io is not None and hasattr(io, "close"):
            io.close()

    def targets(self) -> list[tuple]:
        return []

    @property
    def wants(self) -> tuple[str, ...]:
        """A new device that feeds can be armed for by its role (plan 27
        B2); today's devices name theirs as a class tuple."""
        return (self.role,) if self.feeds else ()

    @property
    def rows(self) -> tuple[str, ...]:
        """The schemes this device delivers discrete rows under (the
        referee's `row_schemes`): its `schemes` less its `feeds` — the
        pad's `pad` / `hat`, MIDI's three. A device whose role is its
        scheme and which has both lanes and hits under it (B4's OSC) says
        so itself."""
        return tuple(s for s in self.schemes if s not in self.feeds)

    def qualify(self, q: str) -> None:
        """Publish under the qualifier `q` (plan 27 B6): a repeatable
        kind's entry that is not its kind's primary — its `schemes`,
        `feeds` and `rows` become ``<scheme>@<role>``. "" leaves them bare."""
        self.qualifier = q
        if not q:
            return
        from .routing import qualified
        self.schemes = tuple(qualified(s, q) for s in self.schemes)
        self.feeds = tuple(qualified(s, q) for s in self.feeds)
        if "_rows" in self.__dict__:
            self._rows = tuple(qualified(s, q) for s in self._rows)

    @classmethod
    def publishes(cls, role: str, entry: dict | None = None
                  ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """(schemes, feeds, rows) an entry of this kind under `role` would
        publish, before any device is made: what `make` checks a second
        feeder against and what an `off` entry still lists. Today's kinds
        keep their class tuples; a kind whose role is its scheme (plan 27
        B4: OSC) overrides this."""
        return cls.schemes, cls.feeds, tuple(s for s in cls.schemes if s not in cls.feeds)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.role} {self.status}>"


class OffDevice(Base):
    """A listed device whose entry says ``enabled = false``: on the SYSTEM
    page as `off`, never opened, its adapter module (midi, gamepad, bridge,
    the Leap SDK) never imported — only its device class is looked up
    (`kind_class`, which for the hands imports `hands.device`, a host
    wrapper that imports no adapter), for its schemes and wants."""

    def __init__(self, role: str, kind: str, entry: dict | None = None,
                 ctx: Context | None = None):
        super().__init__(role, entry, ctx)
        self.kind = kind
        cls = kind_class(kind)      # its kind's schemes, so a row naming it stays dormant, not unknown
        self._wants: tuple[str, ...] = ()
        self._rows: tuple[str, ...] = ()
        if cls is not None:
            self.schemes, self.feeds, self._rows = cls.publishes(role, self.entry)
            w = cls.__dict__.get("wants")
            self._wants = w if isinstance(w, tuple) else ((role,) if self.feeds else ())
            self._wants_for = getattr(cls, "wants_for", None)    # a kind whose wants
                                                                 # follow its qualifier (B6)

    @property
    def wants(self) -> tuple[str, ...]:
        """Its kind's: a rig that lists a device, off or not, can arm a
        learn for it (it completes once the device is on)."""
        f = self.__dict__.get("_wants_for")
        return f(self.role, self.qualifier) if f is not None else self._wants

    @property
    def rows(self) -> tuple[str, ...]:
        """Its kind's, so a hit row in a preset is not refused while the
        device is off."""
        return self._rows

    @property
    def status(self) -> str:
        return "off"


class UnknownDevice(Base):
    """An entry whose kind the registry does not know: an error line, so
    a typo in config.toml is seen, not silently ignored."""

    def __init__(self, role: str, kind: str, entry: dict | None = None,
                 ctx: Context | None = None):
        super().__init__(role, entry, ctx)
        self.kind = kind
        self.error = f"unknown kind {kind!r}"

    @property
    def wants(self) -> tuple[str, ...]:
        return ()


class RefusedDevice(Base):
    """An enabled entry that would feed a scheme an earlier enabled entry
    already feeds: never opened (two devices feeding one Router key would
    overwrite each other every frame), an error line naming the other
    role, as if ``enabled = false``."""

    def __init__(self, role: str, kind: str, scheme: str, other: str,
                 entry: dict | None = None, ctx: Context | None = None, *, why: str = ""):
        super().__init__(role, entry, ctx)
        self.kind = kind
        self.error = why or f"feeds {scheme!r}, which {other} already feeds — not opened"

    @property
    def wants(self) -> tuple[str, ...]:
        return ()


# ---- today's inputs as devices (plan 27 B2) ----

MIDI_PROFILES = ("apc40", "generic")    # midi.PROFILES' names (midi is imported lazily)


class MidiDevice(Base):
    """One MIDI controller (plan 27 B2): a `midi.MidiIO` with the entry's
    `port` and `profile` (`apc40`, or `generic`: plain CC / note / pitch,
    no feedback) under this entry's role. Several may be listed: the first
    MIDI role's rows are unqualified (every row written before plan 27),
    any other's carry its role (``cc@launch:0:7``) — `MidiIO.qualifier` —
    and each role has its own layer; the first role's desk has two, the
    preset layer and SHIFT's global one (`desk.shift`). Its rows are
    applied inside `poll` (a scene-setter), an armed desk Learn completed
    there too. A desk that is not plugged in is `lost` and reconnects
    itself (`midi.Ports.retry`), redrawing every light when it comes."""

    kind = "midi"
    schemes = ("cc", "note", "pitch")
    feeds = ()                  # MIDI is never a feed source: every message is a row
    wants = ("desk",)           # a knob or a button completes a desk learn

    @property
    def profile(self) -> str:
        return str(self.entry.get("profile") or "apc40")

    def open(self) -> None:
        if self.profile not in MIDI_PROFILES:
            raise ValueError(f"no MIDI profile {self.profile!r}; one of "
                             f"{', '.join(MIDI_PROFILES)}")
        from . import midi
        e, c = self.entry, self.ctx
        self.io = midi.MidiIO(c.reg, c.table, port=e.get("port"), profile=self.profile,
                              learner=c.learn, role=self.role)

    def _primary(self) -> bool:
        table = self.ctx.table
        return table is None or table.is_primary(self.role)

    @property
    def qualifier(self) -> str:
        """What this desk's rows carry: "" for the first MIDI role, else
        its role (`Binding.midi_source`)."""
        return "" if self._primary() else self.role

    @property
    def layers(self) -> tuple[str, ...]:
        """The desk's layers (decision 14, for plan 28's one node per
        mode): the first MIDI role's APC40 has the preset layer and SHIFT's
        global one; any other desk has the preset layer only — no latch of
        its own in this plan."""
        if self.profile == "apc40" and self._primary():
            return ("preset", "global")
        return ("preset",)

    @property
    def status(self) -> str:
        io = self.io
        if self.error or io is None:
            return super().status
        if io.error:
            return f"error: {io.error}"
        return "connected" if io.on else "lost"

    @property
    def last(self) -> str:
        """The port's name and this desk's binding count (what the old
        MIDI line showed), then the last message when one has come."""
        io = self.io
        if io is None or io.error or not io.on:
            return ""
        n = len(getattr(io, "bindings", ()) or ())
        head = f"{io.name}  ·  {n} binding{'' if n == 1 else 's'}"
        return f"{head}  ·  {io.last}" if io.last else head

    @property
    def sources(self) -> tuple[Port, ...]:
        """The profile's layout as ports (the APC40's controls; a generic
        desk knows none in advance), each addressed as this desk's rows
        name it — qualified for every MIDI role but the first."""
        io = self.io
        layout = getattr(getattr(io, "profile", None), "LAYOUT", None) if io is not None else None
        if not layout:
            return ()
        name = getattr(io.profile, "control_name", lambda s: None)
        q = self.qualifier
        out = []
        for c in layout:
            button = c.kind in ("button", "grid")
            scheme, _, rest = c.source.partition(":")
            out.append(Port(rest, name(c.source) or c.source,
                            kind="trigger" if button else "value",
                            velocity=button, group=c.kind,
                            scheme=f"{scheme}@{q}" if q else scheme))
        return tuple(out)

    def poll(self, dt: float, now: float) -> None:
        if self.io is not None:
            self.io.poll()

    def targets(self) -> list[tuple]:
        return [(self.io, "midi", "MidiIO")] if self.io is not None else []


class PadDevice(Base):
    """The gamepad as a device (plan 27 B2): a `gamepad.Pad` polled each
    frame (it finds a pad itself — GLFW, then USB — so absent it is `lost`,
    never an error), offered to an armed Learn pad (`gamepad.learn_from`),
    then in `act` its rows delivered (`Router.pad`: the axis lanes fed —
    their names, labels and rests published by the pad, `gamepad.publish`
    — and the button and D-pad rows) and **the sticks' default camera
    job** run (`gamepad.steer`, moved here from `app.frame`: each axis no
    route names, a relative move on the base, through the pad's feel).
    All in the scene-setter slot.

    Several at once (plan 27 B6): the kind is `repeatable`. The first
    enabled pad entry is the primary — its rows unqualified (``pad:A``,
    ``axis:LX``, every row before B6), the factory pad rows its, the
    sticks' camera job its alone; each later pad publishes under its
    role (``pad@p2:A``, ``axis@p2:LX``) and starts with no rows. Each
    reads its own controller (`gamepad.Pad.attach` on the registry's
    shared `Context.pads`): the next free GLFW joystick in list order, or
    the entry's ``joystick = n``; the one libusb reader is lent, not
    owned (`gamepad.Claims.lend`): to the pad holding it while it has no
    GLFW joystick, else to the first ``usb = true`` pad with none. A
    second pad also arms a Learn by its role (`wants_for`)."""

    kind = "gamepad"
    schemes = ("axis", "pad", "hat")
    feeds = ("axis",)

    @staticmethod
    def wants_for(role: str, qualifier: str) -> tuple[str, ...]:
        """``pad`` — Learn pad, completed by whichever pad moves — and, for
        a pad other than the primary, its role too (plan 27 B6): "Learn
        p2" on a param's menu completes only from that pad, so a second
        pad can be learned onto while the first is not plugged in."""
        return ("pad", role) if qualifier else ("pad",)

    @property
    def wants(self) -> tuple[str, ...]:
        return self.wants_for(self.role, self.qualifier)
    repeatable = True

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None):
        super().__init__(role, entry, ctx, io=io)
        self._taken = False      # this frame's press completed a learn
        self._dt = 0.0

    @property
    def joystick(self) -> int | None:
        """The entry's pinned GLFW index (``joystick = n``, 0-based; config
        checks it), or None: the next free one."""
        j = self.entry.get("joystick")
        return j if isinstance(j, int) and not isinstance(j, bool) and j >= 0 else None

    def open(self) -> None:
        from .gamepad import Claims, Pad
        self.io = Pad(usb=bool(self.entry.get("usb", True)))
        claims = getattr(self.ctx, "pads", None)
        if claims is None:
            claims = self.ctx.pads = Claims()
        if hasattr(self.io, "attach"):
            self.io.attach(claims, self.role, self.joystick)
        self.io.open()

    @property
    def status(self) -> str:
        io = self.io
        if self.error or io is None:
            return super().status
        return "connected" if io.on else "lost"

    @property
    def last(self) -> str:
        """Where the pad reads from — ``glfw 1`` (the GLFW joystick index,
        so two pads are told apart, plan 27 B6) or ``usb: <name>`` — and,
        while lost, why: a pinned index waited for, the USB reader's note,
        or that another pad owns the USB reader."""
        io = self.io
        if io is None:
            return ""
        own = getattr(io, "usb_note", "") or ""
        if io.on:
            usb = getattr(io, "usb_pad", None)
            name = getattr(usb, "name", "") if io.source == "usb" else ""
            jid = getattr(io, "jid", None) if io.source == "glfw" else None
            head = (f"{io.source}: {name}" if name else
                    f"{io.source} {jid}" if jid is not None else str(io.source))
            return f"{head}  ·  {own}" if own else head
        pin = getattr(io, "joystick", None)
        why = [f"waiting for joystick {pin}"] if pin is not None else []
        why += [n for n in (getattr(getattr(io, "usb_pad", None), "note", "") or "", own) if n]
        return "  ·  ".join(why)

    @property
    def sources(self) -> tuple[Port, ...]:
        """The pad's fixed layout as ports, each addressed as this pad's
        rows name it — qualified for every pad but the primary (plan 27
        B6: ``axis@p2:LX``), as `MidiDevice.sources` does for a desk."""
        from . import gamepad as g
        q = self.qualifier

        def sc(s: str) -> str:
            return f"{s}@{q}" if q else s
        axes = [Port(n, lb, rest=r, bipolar=n in g.STICKS,
                     group="sticks" if n in g.STICKS else "triggers", scheme=sc("axis"))
                for n, lb, r in zip(g.AXES, g.AXIS_LABELS, g.AXIS_RESTS, strict=True)]
        buttons = [Port(n, n, kind="trigger", group="buttons", scheme=sc("pad"))
                   for n in g.BUTTONS]
        hats = [Port(n, f"D-pad {n.lower()}", kind="trigger", group="d-pad", scheme=sc("hat"))
                for n in g.HATS]
        return tuple(axes + buttons + hats)

    def poll(self, dt: float, now: float) -> None:
        self._taken = False
        self._dt = dt
        if self.io is not None:
            self.io.poll()

    def learn(self, learn) -> bool:
        if self.io is None:
            return False
        from . import gamepad
        q = self.qualifier
        self._taken = bool(gamepad.learn_from(self.io, learn, role=q) if q else
                           gamepad.learn_from(self.io, learn))
        return self._taken

    def act(self, router) -> None:
        """The pad's rows, then the sticks' camera job — on the registry
        the context carries (`Context.reg`), else the router's. The camera
        job is the primary pad's only (plan 27 B6, decision 24: defaults
        author no look): a second pad's unrouted axes do nothing."""
        io = self.io
        if io is None:
            return
        q = self.qualifier
        if q:
            router.pad(io, buttons=not self._taken, role=q)
            return
        router.pad(io, buttons=not self._taken)
        if io.on:
            from . import gamepad
            reg = self.ctx.reg if self.ctx.reg is not None else getattr(router, "reg", None)
            if reg is not None:
                gamepad.steer(io, router, reg, self.__dict__.get("_dt", 0.0))

    def targets(self) -> list[tuple]:
        return [(self.io, "gamepad", "Pad")] if self.io is not None else []


class BridgeDevice(Base):
    """`bridge.Bridge` as one device with two halves (plan 27 B3): its
    ports looked for again in `poll`; the inbound lanes fed as ``ext``,
    with their labels and rests, in the feed slot (`receive`, `publish`);
    and the out half a **sink** — in the slot after `reg.apply`, the
    session's sink rows on this role (``param:view.bright → bridge:3``,
    routing.sink_values) read as effective values and sent through the
    bridge's gate (`send_values`). With no binding table in the context (a
    bare shim) the out half sends the entry's old `send` list, as a
    `Bridge` on its own does."""

    kind = "bridge"
    schemes = ("ext",)
    feeds = ("ext",)
    # it feeds `ext` but cannot complete a Learn (no `learn`), so it arms
    # none, as `MidiOutDevice`; an off bridge offers nothing either
    wants: tuple[str, ...] = ()

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None, audio=None):
        super().__init__(role, entry, ctx, io=io)
        self.audio = audio if audio is not None else self.ctx.audio
        self._n = 0          # the analyzer's lane count, last seen: `lane:*` falls to 0 once

    def open(self) -> None:
        from . import bridge
        self.io = bridge.Bridge(self.ctx.reg, self.entry)

    @property
    def status(self) -> str:
        io = self.io
        if self.error or io is None:
            return super().status
        if io.error:
            return f"error: {io.error}"
        return "connected" if io.on else "lost"

    @property
    def last(self) -> str:
        io = self.io
        if io is None or io.error or not io.on:
            return ""
        return f"{io.name}  ·  {io.encoding}, {io.room} lanes  ·  {io.sent} sent"

    @property
    def sources(self) -> tuple[Port, ...]:
        io = self.io
        n = int(io.decoder.n) if io is not None else int(self.entry.get("in_lanes", 0) or 0)
        return tuple(Port(str(i), f"ext {i}", group="ext", scheme="ext") for i in range(n))

    @property
    def sinks(self) -> tuple[Port, ...]:
        """The out half's lanes as sink ports, ``<role>:<k>`` for each lane
        the encoding has room for (pitch: from `channel` to 15; cc14: from
        `cc` to 31), labelled with the wire they go out on."""
        return _lane_sinks(self.role, self.io, self.entry)

    def poll(self, dt: float, now: float) -> None:
        if self.io is not None:
            self.io.reconnect()

    def feed(self, router) -> None:
        if self.io is None:
            return
        self.io.receive(router)
        self.io.publish(router)

    def send(self, reg, analyzer) -> None:
        io = self.io
        if io is None:
            return
        table = self.ctx.table
        if table is None or not hasattr(table, "sinks"):
            io.transmit(analyzer)                    # a bare shim: the old `send` list
            return
        from .routing import sink_values
        io.send_values(sink_values(table.sinks(self.role), reg, analyzer, self._n))
        if analyzer is not None:
            self._n = int(getattr(analyzer, "n", self._n))

    def targets(self) -> list[tuple]:
        return [(self.io, "bridge", "Bridge")] if self.io is not None else []


# ---- the sinks (plan 27 B3): a device that only sends ----

def _lane_sinks(role: str, sender, entry: dict) -> tuple[Port, ...]:
    """A bridge-encoded output's lanes as sink ports, from the open
    adapter's encoding (`sender`: anything with encoding / channel / cc)
    or, before it opens, the entry's (the `[bridge]` defaults otherwise)."""
    enc = str(getattr(sender, "encoding", None) or entry.get("encoding") or "pitch")
    ch = int(getattr(sender, "channel", entry.get("channel", 0)) or 0)
    cc = int(getattr(sender, "cc", entry.get("cc", 16)) or 0)
    if enc == "pitch":
        wire = [f"pitch ch{ch + k + 1}" for k in range(max(0, 16 - ch))]
    else:
        wire = [f"cc {cc + k}/{cc + k + 32} ch{ch + 1}" for k in range(max(0, 32 - cc))]
    return tuple(Port(str(k), w, group="sink", scheme=role)
                 for k, w in enumerate(wire))


class MidiOutDevice(Base):
    """A MIDI output as a sink (`kind = "midi-out"`, plan 27 B3): a port
    found by `port` (a substring of an existing one, else a virtual port
    of that name unless ``virtual = false``; `bridge.OutPort`, looked for
    again on midi.Ports' schedule when it goes), carrying

      * the DAW messages of the hands device whose role `carries` names —
        what `HandsIO._send` sent before plan 27 B3 (`HandsIO.carry`): the
        `hands-daw` entry the `[hands] out` setting becomes at load
        (config.py). When the port comes back after a gap the DAW is
        brought up to date (`HandsIO.resync`) before the hands' frame runs;
      * the session's sink rows on this role, encoded like the bridge's
        lanes (`encoding`, `channel`, `cc`, `rate`; `bridge.Sender`).

    A `lost` port is looked for again in `poll` (the device's own job,
    B1). Nothing here feeds; it publishes no sources."""

    kind = "midi-out"
    schemes: tuple[str, ...] = ()
    feeds: tuple[str, ...] = ()
    wants: tuple[str, ...] = ()

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None, sender=None):
        super().__init__(role, entry, ctx, io=io)
        self.sender = sender
        self._resync: list = []      # the carried DAW's notes, to go first after a reconnect
        self._n = 0
        self._last = ""

    @property
    def carries(self) -> str:
        return str(self.entry.get("carries") or "")

    def open(self) -> None:
        from . import bridge
        if self.sender is None:
            self.sender = bridge.Sender.of(self.entry, who=self.role)
        if self.io is None:
            port = str(self.entry.get("port") or "")
            if not port:
                raise ValueError("a midi-out entry needs a port (a name, or part of one)")
            self.io = bridge.OutPort(port, virtual=self.entry.get("virtual", True) is not False,
                                     who=self.role)
            self.io.open()

    @property
    def status(self) -> str:
        io = self.io
        if self.error or io is None:
            return super().status
        return "connected" if io.on else "lost"

    @property
    def last(self) -> str:
        io = self.io
        if io is None:
            return ""
        parts = [io.name] if io.on else ([io.error] if io.error else [])
        if self.carries:
            parts.append(f"{self.carries}'s DAW out")
        if self._last:
            parts.append(self._last)
        return "  ·  ".join(p for p in parts if p)

    @property
    def sinks(self) -> tuple[Port, ...]:
        return _lane_sinks(self.role, self.sender, self.entry)

    def _carried(self):
        """The `HandsIO` (anything with `carry` and `resync`) of the
        device `carries` names, while it is open; None otherwise."""
        reg = self.ctx.devices
        if not self.carries or reg is None:
            return None
        d = reg.get(self.carries) if hasattr(reg, "get") else None
        io = getattr(d, "io", None)
        return io if hasattr(io, "carry") else None

    def poll(self, dt: float, now: float) -> None:
        io = self.io
        if io is None or not io.retry():
            return
        if self.sender is not None:
            self.sender.reset()                 # the far end starts blank: every lane again
        h = self._carried()
        if h is not None:                       # before the hands' frame: its axes resend now
            self._resync = h.resync()

    def _send(self, m) -> bool:
        io = self.io
        if io is None or not io.send(m):
            return False
        self._last = _said(m)
        return True

    def send(self, reg, analyzer) -> None:
        io = self.io
        if io is None:
            return
        resync, self._resync = self._resync, []
        for m in resync:
            if not self._send(m):
                break
        h = self._carried()
        if h is not None:
            h.carry(self._send, io.name, "" if io.on else io.error)
        table = self.ctx.table
        if self.sender is not None and table is not None and hasattr(table, "sinks"):
            rows = table.sinks(self.role)
            if rows and io.on:
                from .routing import sink_values
                for m in self.sender.messages(sink_values(rows, reg, analyzer, self._n)):
                    if not self._send(m):
                        break
        if analyzer is not None:
            self._n = int(getattr(analyzer, "n", self._n))

    def targets(self) -> list[tuple]:
        return [(self.io, "bridge", "OutPort")] if self.io is not None else []


def _said(m) -> str:
    """A MIDI message in the SYSTEM line's words: "cc 102 = 64 ch16"."""
    t = getattr(m, "type", "")
    ch = f"ch{getattr(m, 'channel', 0) + 1}"
    if t == "control_change":
        return f"cc {m.control} = {m.value} {ch}"
    if t in ("note_on", "note_off"):
        return f"{t.replace('_', ' ')} {m.note} {ch}"
    if t == "pitchwheel":
        return f"pitch {m.pitch} {ch}"
    return str(t)


# ---- point clouds (plan 27 B4): the source type, its file, a recorded-cloud device ----

CLOUD_SCHEME = "cloud"          # a cloud is published as ``cloud:<role>`` (`DeviceRegistry.clouds`)
CLOUD_FILE_VERSION = 1


def _frozen(a, what: str, n: int | None = None) -> np.ndarray:
    """`a` as a read-only, C-contiguous (N, 3) float32 array — the layout a
    GPU vertex buffer takes as it is (``ctx.buffer(cloud.points)``). The
    caller's own array is never frozen: a copy is, when it would be."""
    out = np.ascontiguousarray(a, dtype=np.float32)
    if out.ndim != 2 or out.shape[1] != 3:
        raise ValueError(f"{what} must be N×3, not {out.shape}")
    if n is not None and out.shape[0] != n:
        raise ValueError(f"{what} has {out.shape[0]} rows for {n} points")
    if out is a and out.flags.writeable:
        out = out.copy()
    out.flags.writeable = False
    return out


@dataclass(frozen=True, eq=False)
class PointCloud:
    """One frame of a point-cloud source (plan 27 B4) — not a scalar lane:
    a device publishes it on the registry under ``cloud:<role>``
    (`DeviceRegistry.clouds`), never through the Router, and the render
    graph's point-cloud geometry node (plan 26 A4b) draws it.

    `points` is N×3 float32, C-contiguous and read-only: a GPU-ready
    buffer (``ctx.buffer(cloud.points)`` uploads it as it is), in the
    publisher's own units — the recorded file's, or a sensor's metres.
    `t` is when the frame was published, on the frame's monotonic clock
    (the ``now`` the registry polls with); `frame` its id, counting up
    from 0 for as long as the device is open, so a reader uploads only
    when it moved (a skipped id: frames came faster than the app polled).
    `colors`, when the source has them, is N×3 float32 RGB in 0–1,
    read-only like `points`. `bounds` is the 2×3 float32 box
    ``[[xmin, ymin, zmin], [xmax, ymax, zmax]]`` — all zeros for an empty
    cloud — so a reader can frame the cloud without walking it."""

    points: np.ndarray
    t: float
    frame: int
    colors: np.ndarray | None = None
    bounds: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        pts = _frozen(self.points, "points")
        object.__setattr__(self, "points", pts)
        if self.colors is not None:
            object.__setattr__(self, "colors", _frozen(self.colors, "colors", len(pts)))
        b = (np.stack([pts.min(axis=0), pts.max(axis=0)]) if len(pts)
             else np.zeros((2, 3))).astype(np.float32)
        b.flags.writeable = False
        object.__setattr__(self, "bounds", b)
        object.__setattr__(self, "t", float(self.t))
        object.__setattr__(self, "frame", int(self.frame))

    @property
    def n(self) -> int:
        """How many points."""
        return int(self.points.shape[0])

    def __repr__(self) -> str:
        return (f"PointCloud(n={self.n}, frame={self.frame}, t={self.t:.3f}"
                f"{', colors' if self.colors is not None else ''})")


@dataclass(frozen=True)
class CloudFile:
    """A recorded point-cloud sequence as `read_clouds` gives it: `rate`
    frames per second, `offsets` (F + 1) into the concatenated `points`
    (and `colors`, or None), so frames may differ in size."""

    points: np.ndarray
    offsets: np.ndarray
    rate: float
    colors: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def frame(self, i: int) -> tuple[np.ndarray, np.ndarray | None]:
        """Frame `i`'s points (and colours, or None) — read-only views."""
        a, b = int(self.offsets[i]), int(self.offsets[i + 1])
        return self.points[a:b], (None if self.colors is None else self.colors[a:b])


def write_clouds(path: Path | str, frames, rate: float, colors=None) -> Path:
    """A point-cloud sequence to `path` (.npz, version 1): `frames` a list
    of N×3 arrays (N may differ per frame), `colors` None or one N×3 RGB
    0–1 array per frame. The file holds ``version`` (1), ``rate`` (frames
    per second), ``offsets`` (int64, F + 1: frame i is
    ``points[offsets[i]:offsets[i + 1]]``), ``points`` (float32, M×3,
    every frame concatenated) and, when given, ``colors`` (float32, M×3)
    — plain numpy, so a recorder in any tool can write one."""
    pts = [np.asarray(f, dtype=np.float32).reshape(-1, 3) for f in frames]
    if not pts:
        raise ValueError("a cloud file needs at least one frame")
    if isinstance(rate, bool) or not isinstance(rate, int | float) or not rate > 0:
        raise ValueError(f"rate = {rate!r} is not a positive number of frames per second")
    offsets = np.zeros(len(pts) + 1, np.int64)
    offsets[1:] = np.cumsum([len(f) for f in pts])
    data = {"version": np.int64(CLOUD_FILE_VERSION), "rate": np.float64(rate),
            "offsets": offsets, "points": np.concatenate(pts)}
    if colors is not None:
        cols = [np.asarray(c, dtype=np.float32).reshape(-1, 3) for c in colors]
        if [len(c) for c in cols] != [len(f) for f in pts]:
            raise ValueError("colors must be one N×3 array per frame, N as its points")
        data["colors"] = np.concatenate(cols)
    path = Path(path)
    np.savez_compressed(path, **data)
    return path


def read_clouds(path: Path | str) -> CloudFile:
    """A sequence `write_clouds` wrote, checked: a missing key, a wrong
    shape, offsets that do not walk the points, or a version this build
    does not read is a ValueError naming it (the device's line says it)."""
    name = Path(path).name
    with np.load(Path(path), allow_pickle=False) as z:
        keys = set(z.files)
        for k in ("version", "rate", "offsets", "points"):
            if k not in keys:
                raise ValueError(f"{name}: no {k!r} — not a cloud file")
        version = int(z["version"])
        if version != CLOUD_FILE_VERSION:
            raise ValueError(f"{name}: cloud file version {version}; "
                             f"this build reads {CLOUD_FILE_VERSION}")
        rate = float(z["rate"])
        offsets = np.array(z["offsets"], dtype=np.int64)
        points = _frozen(z["points"], "points")
        colors = _frozen(z["colors"], "colors", len(points)) if "colors" in keys else None
    if not (np.isfinite(rate) and rate > 0):
        raise ValueError(f"{name}: rate {rate} is not a positive number")
    if (offsets.ndim != 1 or len(offsets) < 2 or offsets[0] != 0
            or offsets[-1] != len(points) or np.any(np.diff(offsets) < 0)):
        raise ValueError(f"{name}: offsets do not walk the {len(points)} points")
    offsets.flags.writeable = False
    return CloudFile(points, offsets, rate, colors)


class CloudDevice(Base):
    """A recorded point cloud played back as a source (plan 27 B4), so the
    `PointCloud` type is exercised with no sensor — the Kinect and the
    live sensors are plan 29. Its entry: `file` (a `write_clouds` .npz; a
    relative path is the home's), `rate` (frames per second; default the
    file's own), `loop` (default true: at the end it starts again; false
    holds the last frame). It plays at its own rate against the frame's
    clock, whatever the app's frame rate: polled at `now`, it shows
    recorded frame ``floor((now − start) · rate)`` (mod the file's length
    when looping) and that count is the cloud's `frame` id. Its one port
    is ``cloud:<role>``; it feeds nothing to the Router and makes no rows:
    the cloud is on the registry (`DeviceRegistry.clouds`). `connected`
    while the file is loaded; a missing or bad file is ``error: …`` and
    the registry tries again on its schedule, so a file copied in later
    comes up with no relaunch."""

    kind = "cloud"

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None):
        super().__init__(role, entry, ctx, io=io)
        self.cloud: PointCloud | None = None     # the frame published last; None until polled
        self._start: float | None = None

    @property
    def file(self) -> Path:
        """The entry's recording; a relative path is the home's."""
        name = self.entry.get("file")
        if not isinstance(name, str) or not name:
            raise ValueError('a cloud entry needs file = "<recording>.npz"')
        p = Path(name).expanduser()
        home = self.ctx.home
        return p if p.is_absolute() or home is None else Path(home) / p

    @property
    def rate(self) -> float:
        """The entry's `rate`, else the file's (frames per second); a bad
        `rate` is refused on open (an error line)."""
        r = self.entry.get("rate")
        if r is not None:
            return float(r)
        return float(self.io.rate) if self.io is not None else 0.0

    @property
    def loop(self) -> bool:
        return self.entry.get("loop", True) is not False

    def open(self) -> None:
        r = self.entry.get("rate")
        if r is not None and (isinstance(r, bool) or not isinstance(r, int | float)
                              or not (math.isfinite(r) and r > 0)):
            raise ValueError(f"rate = {r!r} is not a positive number of frames per second")
        self.io = read_clouds(self.file)
        self.cloud, self._start = None, None

    @property
    def last(self) -> str:
        io, c = self.io, self.cloud
        if io is None or c is None:
            return ""
        i = c.frame % len(io) if self.loop else min(c.frame, len(io) - 1)
        return (f"{self.file.name}  ·  frame {i + 1}/{len(io)}  ·  {c.n} points  ·  "
                f"{self.rate:g} fps")

    @property
    def sources(self) -> tuple[Port, ...]:
        return (Port(self.role, "point cloud", kind="cloud", scheme=CLOUD_SCHEME),)

    def poll(self, dt: float, now: float) -> None:
        io = self.io
        if io is None:
            return
        if self._start is None:
            self._start = now
        k = max(0, math.floor((now - self._start) * self.rate + 1e-9))
        if not self.loop:
            k = min(k, len(io) - 1)
        if self.cloud is not None and self.cloud.frame == k:
            return
        pts, cols = io.frame(k % len(io))
        self.cloud = PointCloud(pts, now, k, cols)

    def close(self) -> None:
        self.cloud, self._start = None, None
        super().close()


def kinds() -> dict[str, type[Base]]:
    """The kinds the registry knows: `[[devices]] kind` → the device class.
    B3 adds "midi-out", B4 adds "osc" and "cloud" — here and nowhere else
    (a new kind is one line here and its own class: no edit to `app.py`).
    The hands' device lives in its own package (`hands/device.py`, plan 27
    B2), which imports this module, so it is looked up when asked for —
    `devices.KINDS` and `devices.HandsDevice` read through here too."""
    from .hands.device import HandsDevice
    from .osc import OscDevice  # (osc.py imports pythonosc only when a server opens)
    return {
        "midi": MidiDevice,
        "gamepad": PadDevice,
        "hands": HandsDevice,
        "bridge": BridgeDevice,
        "midi-out": MidiOutDevice,          # plan 27 B3: a sink alone
        "osc": OscDevice,
        "cloud": CloudDevice,
    }


def kind_class(kind: str) -> type[Base] | None:
    """The device class of `kind`, or None for a kind the registry lacks."""
    return kinds().get(kind)


def __getattr__(name: str):
    """`KINDS` and `HandsDevice`, read lazily (`kinds`)."""
    if name == "KINDS":
        return kinds()
    if name == "HandsDevice":
        return kinds()["hands"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_ROLE = "\0role:"       # `claimed`'s key for a role (no scheme starts with a NUL)


def primaries_of(entries: list[dict]) -> dict[str, str]:
    """kind → the role of its primary entry, for each repeatable kind
    (plan 27 B6): the first *enabled* entry of the kind in list order,
    else (none enabled) the first listed — the one whose rows are
    unqualified."""
    out: dict[str, str] = {}
    for want_on in (True, False):
        for e in entries:
            kind = str(e.get("kind", ""))
            cls = kind_class(kind)
            if (cls is None or not cls.repeatable or kind in out
                    or (want_on and not e.get("enabled", True))):
                continue
            out[kind] = str(e.get("role", ""))
    return out


def make(entry: dict, ctx: Context | None = None, claimed: dict[str, str] | None = None,
         primaries: dict[str, str] | None = None) -> Base:
    """A device for one checked `[[devices]]` entry (config.devices):
    `OffDevice` when it is not enabled, `UnknownDevice` for a kind the
    table lacks, `RefusedDevice` on a true collision — an earlier enabled
    entry of the same role, or one that already **feeds** one of its
    `feeds` (`claimed`: fed scheme → role, filled here for the next
    entry). The registry claims (scheme, role), not scheme (plan 27 B6):
    a repeatable kind's entry other than its kind's primary (`primaries`,
    kind → role; `primaries_of`) publishes under its role (`qualify`:
    a second pad feeds ``axis@p2``), so two pads never collide; a kind
    that cannot qualify (the hands: forty lanes of another shape) is
    refused as in B1. A kind that feeds nothing (MIDI: rows, not vectors)
    is never refused for a scheme, so two desks of different roles both
    open. Nothing is opened here."""
    role, kind = str(entry.get("role", "")), str(entry.get("kind", ""))
    cls = kind_class(kind)
    q = ""
    if cls is not None and cls.repeatable and primaries is not None:
        q = "" if primaries.get(kind, role) == role else role
    if not entry.get("enabled", True):
        d = OffDevice(role, kind, entry, ctx)
        if q:
            d.qualify(q)
        return d
    if cls is None:
        return UnknownDevice(role, kind, entry, ctx)
    if claimed is not None:
        if _ROLE + role in claimed:
            return RefusedDevice(role, kind, "", "", entry, ctx,
                                 why=f"role {role!r} is listed twice — not opened")
        claimed[_ROLE + role] = role
        feeds = cls.publishes(role, entry)[1]       # an OSC role feeds its own name (B4)
        if q:
            from .routing import qualified
            feeds = tuple(qualified(s, q) for s in feeds)
        for scheme in feeds:
            if scheme in claimed and claimed[scheme] != role:
                return RefusedDevice(role, kind, scheme, claimed[scheme], entry, ctx)
        for scheme in feeds:
            claimed[scheme] = role
    d = cls(role, entry, ctx)
    if q:
        d.qualify(q)
    return d


def make_all(entries: list[dict], ctx: Context | None = None) -> list[Base]:
    """One device per entry, in order, each later entry refused a role or
    the fed schemes an earlier enabled one claims (roles are unique
    already: config drops a duplicate role at load and on a re-read); a
    repeatable kind's entries after its primary qualified (plan 27 B6)."""
    claimed: dict[str, str] = {}
    prim = primaries_of(entries)
    return [make(e, ctx, claimed, prim) for e in entries]


def _err(where: str, e: Exception) -> str:
    return f"{where}: {type(e).__name__}: {e}"[:160]


class DeviceRegistry:
    """The list of devices, in `[[devices]]` order: opened each behind its
    own entry (`open_all`), polled in order each frame, closed in one
    list (reverse order). `entries` are checked entries (config.devices);
    `devices` may be given ready-made (tests, the frame-order stubs).
    `path` is the config.toml to watch, `clock` the retry clock
    (monotonic, as midi.Ports'). `listeners` are called after any open
    or close, so the host can re-point what holds an adapter (the panel,
    the ghost renderer)."""

    def __init__(self, entries: list[dict] | None = None, ctx: Context | None = None, *,
                 devices: list | None = None, path: Path | None = None,
                 clock=time.monotonic, notes: list[str] | None = None):
        self.ctx = ctx if ctx is not None else Context()
        self.notes = notes if notes is not None else self.ctx.notes
        self.path = Path(path) if path is not None else None
        self.clock = clock
        self.entries: list[dict] = [dict(e) for e in (entries or [])]
        if getattr(self.ctx, "devices", None) is None:
            self.ctx.devices = self      # a sink finds the device it carries (`MidiOutDevice`)
        self.devices: list = list(devices) if devices is not None else make_all(
            self.entries, self.ctx)
        self._tell_table()           # which MIDI role an unqualified row means, before any opens
        self._seed_sinks(self.entries)   # an old `send` list → the session's sink rows, once
        self.listeners: list = []
        self.error = ""              # this frame's first device error (the toast)
        # a device handed in with its adapter (tests, the frame-order stubs) is open
        self._opened: set[str] = {d.role for d in self.devices if getattr(d, "io", None) is not None}
        self._retry: dict[str, tuple[int, float]] = {}   # role → (misses, next try)
        self._frames = 0
        self._mtime: float | None = self._stat()

    # ---- the list ----

    def __iter__(self):
        return iter(self.devices)

    def __len__(self) -> int:
        return len(self.devices)

    def get(self, role: str):
        """The device of `role`, or None."""
        return next((d for d in self.devices if d.role == role), None)

    def first(self, kind: str):
        """The first listed device of `kind` (off or not), or None."""
        return next((d for d in self.devices if d.kind == kind), None)

    def adapter(self, kind: str):
        """The first open adapter object of `kind` — the `MidiIO`, `Pad`,
        `HandsIO` or `Bridge` the panel and the ghost renderer hold — or
        None when none is open."""
        return next((d.io for d in self.devices
                     if d.kind == kind and getattr(d, "io", None) is not None), None)

    def schemes(self) -> tuple[str, ...]:
        """Every scheme the listed devices publish under, in list order."""
        out: list[str] = []
        for d in self.devices:
            for s in getattr(d, "schemes", ()):
                if s not in out:
                    out.append(s)
        return tuple(out)

    def continuous_schemes(self) -> tuple[str, ...]:
        """The schemes a route can read as a lane, in offer order: the
        built-in `lane` (the analyzer), `lfo`, `env` and `seq` first, then each listed
        device's `feeds` in list order (an `off` device's too, so a preset
        row naming it stays a dormant route, not an unknown one). What the
        Router offers (`Router.schemes`, plan 27 B2: no fixed tuple)."""
        out = list(BUILTIN_SCHEMES)
        for d in self.devices:
            for s in getattr(d, "feeds", ()):
                if s not in out:
                    out.append(s)
        return tuple(out)

    def row_schemes(self) -> tuple[str, ...]:
        """The schemes the listed devices deliver as rows (each device's
        `rows`: its `schemes` less its `feeds` — the pad's `pad` / `hat`,
        MIDI's `cc` / `note` / `pitch` — or, for an OSC device with hits,
        its role, which is fed as well), in list order — the referee's
        `Bindings.row_schemes` (`Router.use`)."""
        out: list[str] = []
        for d in self.devices:
            rows = getattr(d, "rows", None)
            if rows is None:
                fed = getattr(d, "feeds", ())
                rows = tuple(s for s in getattr(d, "schemes", ()) if s not in fed)
            for s in rows:          # an OSC role's hits are rows under its fed scheme (B4)
                if s not in out:
                    out.append(s)
        return tuple(out)

    def midi_roles(self) -> tuple[str, ...]:
        """Every MIDI entry's role, off or not, the one whose rows are
        unqualified first (`Bindings.midi_roles`): the first MIDI role whose
        profile is the binding table's (`bindings.json`'s "profile",
        `apc40` by default) — the desk the file's rows were written for —
        else the first listed; the rest in list order. So a generic box
        listed above the APC40 never inherits the APC40's rows or SHIFT,
        and a rig whose only desk is generic still maps (orchestrator's
        ruling on PR #181)."""
        midi = [d for d in self.devices if d.kind == "midi"]
        table = getattr(self.ctx, "table", None)
        want = str(getattr(table, "profile", "") or "apc40")
        owner = next((d for d in midi
                      if str(getattr(d, "entry", {}).get("profile") or "apc40") == want), None)
        if owner is not None:
            midi.remove(owner)
            midi.insert(0, owner)
        return tuple(d.role for d in midi)

    def primaries(self) -> dict[str, str]:
        """scheme → the role whose rows on it are unqualified, for every
        scheme but MIDI's (plan 27 B6; MIDI's rule is `midi_roles`): the
        first listed device that publishes the scheme bare and is not off,
        refused or unknown — a repeatable kind's primary (``pad``, ``axis``,
        ``hat`` → the first enabled pad), any other device its own
        schemes. `Bindings.primaries`, through `Router.use`."""
        out: dict[str, str] = {}
        for d in self.devices:
            if isinstance(d, OffDevice | UnknownDevice | RefusedDevice) or d.kind == "midi":
                continue
            if getattr(d, "qualifier", ""):
                continue
            for s in getattr(d, "schemes", ()):
                out.setdefault(s, d.role)
        return out

    def wants(self) -> tuple[str, ...]:
        """What a Learn can be armed for on this rig (`Learn.wants`), in
        list order, off devices' included (the learn completes once the
        device is on): each device's `wants` — ``desk`` for every MIDI
        role, ``pad``, ``hand:left`` / ``hand:right``, a new device's role."""
        out: list[str] = []
        for d in self.devices:
            for w in getattr(d, "wants", ()):
                if w not in out:
                    out.append(w)
        return tuple(out)

    def sink_ports(self) -> tuple[Port, ...]:
        """Every listed device's sink ports, in list order (an `off` device
        offers none): what the param menu's "Learn sink ▸" lists."""
        out: list[Port] = []
        for d in self.devices:
            out += list(getattr(d, "sinks", ()) or ())
        return tuple(out)

    def _seed_sinks(self, entries: list[dict]) -> None:
        """An enabled entry's old `send` list (`[bridge] send`, the bridge's
        default ``["lane:*"]`` included) becomes the session's sink rows on
        its role — **once per role**, marked done in `bindings.json` itself
        (`Bindings.sinks_seeded`, never by consuming the owner's config
        key): a role in that list is never seeded again, so deleting every
        row of it on ROUTING, or saving config.toml mid-session, brings
        nothing back. A file that already holds sink rows on a role counts
        as seeded for it (the mark is added). Written with one note; from
        then on the rows say and the key is not read."""
        table = getattr(self.ctx, "table", None)
        if table is None or not hasattr(table, "sinks"):
            return
        from . import routing
        if not isinstance(getattr(table, "sinks_seeded", None), list):
            table.sinks_seeded = []          # a table from before a hot reload
        seeded = table.sinks_seeded
        added = False
        for e in entries:
            send = e.get("send")
            role = e.get("role", "")
            if not e.get("enabled", True) or send is None or not role or role in seeded:
                continue
            seeded.append(role)
            added = True                     # the mark alone is worth the write
            if table.sinks(role, enabled=False):
                continue                     # rows from before the mark: seeded already
            rows, bad = routing.sink_rows_from_send(role, send)
            table.bindings += rows       # checked already; the load's notes stand
            said = ", ".join(f"{b.source} → {b.target}" for b in rows) or "nothing"
            self._note(f"bindings: [{e.get('kind', role)}] send is now sink rows in "
                       f"bindings.json ({said}) — the rows say from here on; edit them on "
                       "ROUTING (sinks)")
            for why in bad:
                self._note(f"bindings: [{e.get('kind', role)}] send {why} — not translated")
        # a file still holding a preset's part waits for the first-launch
        # migration to rewrite it (routing.Bindings.load): the rows are in
        # memory until then, and that rewrite keeps them
        if added and hasattr(table, "write") and getattr(table, "carried", None) is None:
            table.write()

    def _tell_table(self) -> None:
        """The shared binding table learns the MIDI roles in list order
        (plan 27 B2), so a desk opened next reads and writes its own rows."""
        table = getattr(self.ctx, "table", None)
        if table is not None:
            table.midi_roles = self.midi_roles()
            table.primaries = self.primaries()      # plan 27 B6: every other scheme's

    @property
    def clouds(self) -> dict[str, PointCloud]:
        """The point clouds the open devices publish (plan 27 B4), as
        ``cloud:<role>`` → that device's latest `PointCloud`, in list order
        — what the render graph's point-cloud node reads (plan 26 A4b).
        Not through the Router: a cloud is not a scalar lane. A device that
        is closed, removed or not yet polled has no entry."""
        out: dict[str, PointCloud] = {}
        for d in self.devices:
            c = getattr(d, "cloud", None)
            if c is not None and d.role in self._opened:
                out[f"{CLOUD_SCHEME}:{d.role}"] = c
        return out

    def lines(self) -> list[tuple[str, str, str, int, str]]:
        """One (role, kind, status, n sources, last) per device — the
        SYSTEM page's lines. A sink's `last` starts with what it sends:
        ``n sinks``, its enabled sink rows (plan 27 B3)."""
        out = []
        table = getattr(self.ctx, "table", None)
        for d in self.devices:
            try:
                last = d.last
                if getattr(d, "sinks", ()) and hasattr(table, "sinks"):
                    k = len(table.sinks(d.role))
                    head = f"{k} sink{'' if k == 1 else 's'}"
                    last = f"{head}  ·  {last}" if last else head
                out.append((d.role, d.kind, d.status, len(d.sources), last))
            except Exception as e:  # noqa: BLE001 — a status line never takes the page down
                out.append((d.role, d.kind, _err("status", e), 0, ""))
        return out

    def targets(self) -> list[tuple]:
        """The hot reloader's swap targets: each device's adapter object,
        the shims and the registry itself."""
        out: list[tuple] = [(self, "devices", "DeviceRegistry")]
        for d in self.devices:
            mod = type(d).__module__.removeprefix(f"{__package__}.")
            out.append((d, mod, type(d).__name__))
            out += d.targets()
        return out

    def _changed(self) -> None:
        for fn in list(self.listeners):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                self._note(_err("devices", e))

    def _note(self, note: str) -> None:
        note = note[:200]
        if note not in self.notes:
            self.notes.append(note)
        print(note, file=sys.stderr)

    # ---- opening and closing ----

    def _open(self, d) -> bool:
        """Open one device: True when it is open now. A failure is its
        `error`, said once, and the next try is scheduled (`retry_after`)."""
        if d.role in self._opened:
            return True
        if d.status == "off" or isinstance(d, UnknownDevice | RefusedDevice):
            if d.role not in self._retry and not isinstance(d, OffDevice):
                self._retry[d.role] = (0, float("inf"))
                self._note(f"config: [[devices]] {d.role}: {d.error}"
                           + ("" if isinstance(d, RefusedDevice) else " — not opened"))
            return False
        try:
            d.open()
        except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
            misses = self._retry.get(d.role, (0, 0.0))[0] + 1
            self._retry[d.role] = (misses, self.clock() + retry_after(misses))
            d.error = f"{type(e).__name__}: {e}"[:120]
            if misses == 1:
                self._note(f"{d.kind}: {e}")
            return False
        d.error = ""
        self._opened.add(d.role)
        self._retry.pop(d.role, None)
        return True

    def open_all(self) -> None:
        """Open every listed device, each behind its own entry; one that
        fails is a note and `error: …`, the rest open."""
        for d in self.devices:
            self._open(d)
        self._changed()

    def _close(self, d) -> None:
        self._opened.discard(d.role)
        self._retry.pop(d.role, None)
        try:
            d.close()
        except Exception as e:  # noqa: BLE001 — teardown is best-effort
            self._note(_err(d.kind, e))
            if hasattr(d, "io"):
                d.io = None             # a port that would not close is still let go of

    def close(self) -> None:
        """Every device closed, last listed first, best-effort — the one
        close list for a quit and a restart (the pad included)."""
        for d in reversed(self.devices):
            self._close(d)

    # ---- the frame ----

    def _guard(self, d, fn, *, clear: bool = False) -> bool:
        """Run one device's step; its exception is the device's `error`
        and the registry's (the first one this frame), never the frame's.
        True when the step ran clean. `clear`: a clean run clears the
        device's error — the frame's first step (`poll`) does, so an error
        stands until the next frame runs clean."""
        try:
            fn()
        except Exception as e:  # noqa: BLE001 — one device never stops the frame
            d.error = f"{type(e).__name__}: {e}"[:120]
            if not self.error:
                self.error = _err(d.kind, e)
            return False
        if clear and d.role in self._opened and d.error:
            d.error = ""
        return True

    def poll(self, dt: float, now: float, *, router=None, learn=None) -> None:
        """The scene-setter slot: each open device polled, offered to the
        armed Learn, then its rows delivered (`act`). A device that would
        not open is tried again when its schedule says; the config list is
        re-read when the file changed (`watch`)."""
        self.error = ""
        self._frames += 1
        if self._frames % WATCH_FRAMES == 0:
            self.watch()
        for d in list(self.devices):
            if d.role not in self._opened:
                misses, at = self._retry.get(d.role, (0, 0.0))
                if not (misses and self.clock() >= at and self._open(d)):
                    continue
                self._changed()         # back: polled from this very frame
            if not self._guard(d, lambda d=d: d.poll(dt, now), clear=True):
                continue                # a poll that raised delivers no rows this frame
            if learn is not None:
                self._guard(d, lambda d=d: d.learn(learn))
            if router is not None:
                self._guard(d, lambda d=d: d.act(router))

    def feed(self, router) -> None:
        """The feed slot: every open device publishes its vectors."""
        for d in list(self.devices):
            if d.role in self._opened:
                self._guard(d, lambda d=d: d.feed(router))

    def send(self, reg, analyzer=None) -> None:
        """After `reg.apply`: the sinks read effective values out, each
        device in list order (plan 27 B3)."""
        for d in list(self.devices):
            if d.role in self._opened:
                self._guard(d, lambda d=d: d.send(reg, analyzer))

    # ---- config.toml, watched ----

    def _stat(self) -> float | None:
        if self.path is None:
            return None
        try:
            return self.path.stat().st_mtime
        except OSError:
            return None

    def watch(self) -> bool:
        """Re-read the `[[devices]]` list when config.toml's mtime moved;
        True when the list changed. A file that will not parse, or a list
        with a bad entry, is a note and the old list stands."""
        if self.path is None:
            return False
        mtime = self._stat()
        if mtime == self._mtime:
            return False
        self._mtime = mtime
        from . import config
        entries, problems = config.read_devices(self.path)
        if problems:
            self._note(f"config: [[devices]] not applied — {problems[0]} — the old list stands")
            return False
        return self.apply(entries)

    def apply(self, entries: list[dict]) -> bool:
        """A new device list: what left is closed, what arrived is opened,
        an entry that changed is closed and opened again, the rest stay;
        the order becomes the list's. True when anything changed."""
        new = [dict(e) for e in entries]
        old = {e["role"]: e for e in self.entries}
        have = {d.role: d for d in self.devices}
        fresh = {d.role: d for d in make_all(new, self.ctx)}
        changed = False
        devices = []
        for e in new:
            role = e["role"]
            kept = have.get(role)
            # unchanged, refused or not exactly as before, and under the same
            # qualifier (plan 27 B6: the first pad leaving makes the second
            # the primary — it reopens with its rows bare): the device stays
            if kept is not None and old.get(role) == e and (
                    isinstance(kept, RefusedDevice) == isinstance(fresh[role], RefusedDevice)
                    and getattr(kept, "qualifier", "") == getattr(fresh[role], "qualifier", "")):
                devices.append(have.pop(role))
                continue
            if kept is not None:
                self._close(have.pop(role))
                self._note(f"devices: {role} changed — reopened")
            else:
                self._note(f"devices: {role} added")
            devices.append(fresh[role])
            changed = True
        for role, d in have.items():
            self._close(d)
            self._note(f"devices: {role} removed")
            changed = True
        changed = changed or [d.role for d in devices] != [d.role for d in self.devices]
        self.entries, self.devices = new, devices
        self._tell_table()
        self._seed_sinks(new)
        if changed:
            for d in devices:
                if d.role not in self._opened:
                    self._open(d)
            self._changed()
        return changed
