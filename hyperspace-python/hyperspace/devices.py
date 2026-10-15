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
`BridgeDevice` is still B1's shim (B3 makes its out half a sink). Each owns
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
sinks (B3). One device's exception never stops the frame: it is recorded
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
BUILTIN_SCHEMES = ("lane", "lfo")           # fed by the analyzer and the LFOs, not a device


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
    device layer the port belongs to ("" = every layer)."""

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
    vectors, labels, rests, gates and names; `send` is the sink half
    (B3). `targets` are the live objects the hot reloader re-classes.
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


class Base:
    """The protocol's defaults: a device that does nothing until a
    subclass says otherwise. `entry` is its checked `[[devices]]` table,
    `ctx` the host's `Context`; a shim built in a test over an adapter of
    its own passes `io` and needs neither."""

    kind = ""
    schemes: tuple[str, ...] = ()
    feeds: tuple[str, ...] = ()
    layers: tuple[str, ...] = ()

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

    @property
    def wants(self) -> tuple[str, ...]:
        """Its kind's: a rig that lists a device, off or not, can arm a
        learn for it (it completes once the device is on)."""
        return self._wants

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
                 entry: dict | None = None, ctx: Context | None = None):
        super().__init__(role, entry, ctx)
        self.kind = kind
        self.error = f"feeds {scheme!r}, which {other} already feeds — not opened"

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
    All in the scene-setter slot."""

    kind = "gamepad"
    schemes = ("axis", "pad", "hat")
    feeds = ("axis",)
    wants = ("pad",)

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None):
        super().__init__(role, entry, ctx, io=io)
        self._taken = False      # this frame's press completed a learn
        self._dt = 0.0

    def open(self) -> None:
        from .gamepad import Pad
        self.io = Pad(usb=bool(self.entry.get("usb", True)))
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
        if io.on:
            usb = getattr(io, "usb_pad", None)
            name = getattr(usb, "name", "") if io.source == "usb" else ""
            return f"{io.source}: {name}" if name else str(io.source)
        return getattr(getattr(io, "usb_pad", None), "note", "") or ""

    @property
    def sources(self) -> tuple[Port, ...]:
        from . import gamepad as g
        axes = [Port(n, lb, rest=r, bipolar=n in g.STICKS,
                     group="sticks" if n in g.STICKS else "triggers", scheme="axis")
                for n, lb, r in zip(g.AXES, g.AXIS_LABELS, g.AXIS_RESTS, strict=True)]
        buttons = [Port(n, n, kind="trigger", group="buttons", scheme="pad") for n in g.BUTTONS]
        hats = [Port(n, f"D-pad {n.lower()}", kind="trigger", group="d-pad", scheme="hat")
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
        self._taken = bool(gamepad.learn_from(self.io, learn))
        return self._taken

    def act(self, router) -> None:
        """The pad's rows, then the sticks' camera job — on the registry
        the context carries (`Context.reg`), else the router's."""
        io = self.io
        if io is None:
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
    """`bridge.Bridge` as a device: its one `step` — the inbound lanes fed
    as ``ext``, the analyzer's lanes sent out — from the feed slot with
    the live analyzer, as today. B3 makes the outbound half a sink."""

    kind = "bridge"
    schemes = ("ext",)
    feeds = ("ext",)

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None, audio=None):
        super().__init__(role, entry, ctx, io=io)
        self.audio = audio if audio is not None else self.ctx.audio

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

    def feed(self, router) -> None:
        if self.io is None:
            return
        audio = self.audio
        chain = audio.chain if audio is not None and getattr(audio, "on", False) else None
        self.io.step(chain, router)

    def targets(self) -> list[tuple]:
        return [(self.io, "bridge", "Bridge")] if self.io is not None else []


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


def make(entry: dict, ctx: Context | None = None, claimed: dict[str, str] | None = None) -> Base:
    """A device for one checked `[[devices]]` entry (config.devices):
    `OffDevice` when it is not enabled, `UnknownDevice` for a kind the
    table lacks, `RefusedDevice` when an earlier enabled entry already
    **feeds** one of its `feeds` (`claimed`: fed scheme → role, filled
    here for the next entry) — a kind that feeds nothing (MIDI: rows,
    not vectors) is never refused, so two desks of different roles both
    open. Nothing is opened here."""
    role, kind = str(entry.get("role", "")), str(entry.get("kind", ""))
    if not entry.get("enabled", True):
        return OffDevice(role, kind, entry, ctx)
    cls = kind_class(kind)
    if cls is None:
        return UnknownDevice(role, kind, entry, ctx)
    if claimed is not None:
        feeds = cls.publishes(role, entry)[1]       # an OSC role feeds its own name (B4)
        for scheme in feeds:
            if scheme in claimed and claimed[scheme] != role:
                return RefusedDevice(role, kind, scheme, claimed[scheme], entry, ctx)
        for scheme in feeds:
            claimed[scheme] = role
    return cls(role, entry, ctx)


def make_all(entries: list[dict], ctx: Context | None = None) -> list[Base]:
    """One device per entry, in order, each later entry refused the fed
    schemes an earlier enabled one claims (roles are unique already:
    config drops a duplicate role at load and on a re-read)."""
    claimed: dict[str, str] = {}
    return [make(e, ctx, claimed) for e in entries]


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
        self.devices: list = list(devices) if devices is not None else make_all(
            self.entries, self.ctx)
        self._tell_table()           # which MIDI role an unqualified row means, before any opens
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
        built-in `lane` (the analyzer) and `lfo` first, then each listed
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

    def _tell_table(self) -> None:
        """The shared binding table learns the MIDI roles in list order
        (plan 27 B2), so a desk opened next reads and writes its own rows."""
        table = getattr(self.ctx, "table", None)
        if table is not None:
            table.midi_roles = self.midi_roles()

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
        SYSTEM page's lines."""
        out = []
        for d in self.devices:
            try:
                out.append((d.role, d.kind, d.status, len(d.sources), d.last))
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
        """After `reg.apply`: the sinks (B3) read effective values out."""
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
            # unchanged, and refused or not exactly as before: the device stays
            if kept is not None and old.get(role) == e and (
                    isinstance(kept, RefusedDevice) == isinstance(fresh[role], RefusedDevice)):
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
        if changed:
            for d in devices:
                if d.role not in self._opened:
                    self._open(d)
            self._changed()
        return changed
