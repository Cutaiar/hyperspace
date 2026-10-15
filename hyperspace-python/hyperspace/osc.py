"""OSC devices (plan 27 B4): a phone app, a laptop patch or anything else
that sends Open Sound Control over UDP, added by a `[[devices]]` entry
alone — **no edit to `app.py`**. The only code that names this kind is this
module and the registry's kind table (`devices.kinds`).

    [[devices]]
    role = "phone"            # the scheme its sources live under: phone:x, phone:hit
    kind = "osc"
    port = 9000               # UDP; host = "0.0.0.0" (every interface) by default
    axes = ["/x", "/y"]       # continuous: phone:x, phone:y
    hits = ["/hit"]           # triggers: phone:hit, velocity = the first number
    rest = 0.5                # where the axes idle (or a table: rest = { "/y" = 0 })

**The role is the scheme** (plan 27 B1's rule for a new device): an axis
``/x`` is the source ``phone:x`` — the address without its leading ``/``
(``/1/fader3`` → ``phone:1/fader3``). The axes are one fed vector under
the role, published with their names, labels and rests (`Router.names`,
`labels`, `rests`), so a route names ``phone:x`` like ``hand:right.roll``.
A value is the message's first number, mapped from the entry's `range`
(default ``[0, 1]``, what most phone apps send) onto 0–1 and clamped. An
axis no message has reached reads NaN — its routes dormant, never at a
made-up value — so nothing on screen moves until the phone does.

**Hits** are triggers (decision 13: values and triggers stay two kinds):
each ``/hit`` that arrives is delivered as rows through the table, like a
pad button's press — a row on ``phone:hit`` with op `fire`, `toggle`,
`step` or `set` acts when the velocity is above 0 (`routing.act`), `abs`
lands the velocity itself on the param (a trigger fires), `momentary`
holds a toggle while the velocity is above 0 and lets go at 0. The
velocity is the message's first number clamped to 0–1, 1 when the message
carries none. Hit rows are the session's (`bindings.json`), as the pad's
are; a Learn armed for the role (`Learn <role>` in a param's menu) takes
the next hit as a button row or the next axis moved `LEARN_TRAVEL` from
its rest as a route.

**Status.** `connected` while a message arrived within `timeout` seconds
(default `TIMEOUT_S`), `lost` before the first one and after a silence —
an OSC sender has no connection to lose, so silence is all there is to
read. While lost the axes **hold** their last values (a phone app sends
only on change: a fader left alone must not snap back); ``hold = false``
lets their routes go instead. A port another program holds is ``error:
…`` and the registry tries it again on its schedule.

The socket is read without a thread, non-blocking, each frame in the
device's `poll` (at most `MAX_DATAGRAMS`); `pythonosc` parses each
datagram, a bundle's messages in order. `pythonosc` is imported only when
an entry opens a server, so importing `app` imports neither this module
nor the library (tests/test_app_boundary.py).
"""

from __future__ import annotations

import math
import socket

import numpy as np

from .devices import BUILTIN_SCHEMES, CLOUD_SCHEME, Base, Context, Port

DEFAULT_HOST = "0.0.0.0"     # every interface: a phone on the LAN reaches it
DEFAULT_PORT = 9000
TIMEOUT_S = 5.0              # silence after which the device reads `lost`
LEARN_TRAVEL = 0.25          # an axis this far from its rest completes a Learn
MAX_DATAGRAMS = 512          # read per frame at most, so a flood cannot stall the frame


def _number(args) -> float | None:
    """The first number among a message's arguments (a bool is not one), or None."""
    for a in args:
        if isinstance(a, bool):
            continue
        if isinstance(a, int | float) and math.isfinite(float(a)):
            return float(a)
    return None


def _clamp(u: float) -> float:
    return 0.0 if u < 0.0 else min(u, 1.0)


class Server:
    """A UDP socket on `host:port`, read non-blocking each frame. `port` 0
    takes any free port (the tests); `port` is then the one bound."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        from pythonosc import osc_packet  # noqa: F401 — the library is there, or say so now

        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_DGRAM)
        try:
            sock.bind((host, port))
            sock.setblocking(False)
        except OSError as e:
            sock.close()
            raise OSError(e.errno, f"UDP {host}:{port} — {e.strerror or e}") from e
        self.sock = sock
        self.host = host
        self.port = int(sock.getsockname()[1])
        self.bad = 0                    # datagrams that were not OSC

    def read(self, limit: int = MAX_DATAGRAMS) -> list[tuple[str, list]]:
        """Every message waiting, in arrival order: (address, arguments)."""
        from pythonosc.osc_packet import OscPacket

        out: list[tuple[str, list]] = []
        for _ in range(limit):
            try:
                data = self.sock.recv(65536)
            except (BlockingIOError, InterruptedError):
                break
            try:
                packet = OscPacket(data)
            except Exception:  # noqa: BLE001 — a stray datagram is counted, never a crash
                self.bad += 1
                continue
            out.extend((m.message.address, list(m.message.params)) for m in packet.messages)
        return out

    def close(self) -> None:
        self.sock.close()


class Layout:
    """An OSC entry's addresses, checked: the axes (address → lane), their
    names, labels and rests, the hits (address → name), the value range.
    A bad entry is a ValueError naming the key — the device's error line."""

    def __init__(self, entry: dict):
        self.axes = self._addresses(entry, "axes")
        self.hits = self._addresses(entry, "hits")
        both = set(self.axes) & set(self.hits)
        if both:
            raise ValueError(f"{min(both)} is both an axis and a hit")
        self.names = [a[1:] for a in self.axes]
        self.index = {a: i for i, a in enumerate(self.axes)}
        self.hit_names = {a: a[1:] for a in self.hits}
        self.rests = [self._rest(entry.get("rest", 0.0), a) for a in self.axes]
        lo_hi = entry.get("range", [0.0, 1.0])
        if (not isinstance(lo_hi, list | tuple) or len(lo_hi) != 2
                or any(isinstance(v, bool) or not isinstance(v, int | float) for v in lo_hi)
                or lo_hi[0] == lo_hi[1]):
            raise ValueError(f"range = {lo_hi!r} is not [low, high]")
        self.lo, self.hi = float(lo_hi[0]), float(lo_hi[1])

    @staticmethod
    def _addresses(entry: dict, key: str) -> list[str]:
        raw = entry.get(key, [])
        if not isinstance(raw, list):
            raise ValueError(f"{key} = {raw!r} is not a list of OSC addresses")  # noqa: TRY004
        out: list[str] = []
        for a in raw:
            if not isinstance(a, str) or not a.startswith("/") or len(a) < 2 or ":" in a:
                raise ValueError(f"{key}: {a!r} is not an OSC address (\"/x\", no ':')")
            if a in out:
                raise ValueError(f"{key}: {a} is listed twice")
            out.append(a)
        return out

    @staticmethod
    def _rest(rest, address: str) -> float:
        if isinstance(rest, dict):
            rest = rest.get(address, rest.get(address[1:], 0.0))
        if isinstance(rest, bool) or not isinstance(rest, int | float):
            raise ValueError(f"rest for {address} = {rest!r} is not a number")  # noqa: TRY004
        return float(rest)

    def norm(self, v: float) -> float:
        """A received value on 0–1, from the entry's range."""
        return _clamp((v - self.lo) / (self.hi - self.lo))


def _say(address: str, args: list) -> str:
    return (f"{address} {' '.join(f'{a:.3g}' if isinstance(a, float) else str(a) for a in args)}"
            .strip()[:60])


class OscDevice(Base):
    """An OSC sender as a device (module docstring). Its role is its scheme:
    it feeds ``<role>`` (the axes) and, with hits, delivers rows under it
    too (`rows`)."""

    kind = "osc"

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None):
        super().__init__(role, entry, ctx, io=io)
        self.schemes, self.feeds, self._rows = self.publishes(role, self.entry)
        self.layout: Layout | None = None
        self.message = ""                   # the last message, for the status line
        self._reset()

    @classmethod
    def publishes(cls, role: str, entry: dict | None = None
                  ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """The role is the scheme: its axes are fed under it, its hits are
        rows under it (only when the entry lists hits)."""
        hits = (entry or {}).get("hits")
        return (role,), (role,), ((role,) if hits else ())

    @property
    def rows(self) -> tuple[str, ...]:
        return self._rows

    def _reset(self) -> None:
        n = len(self.layout.axes) if self.layout is not None else 0
        self.values = np.full(n, np.nan)    # NaN: no message yet for that axis
        self.heard: float | None = None     # the frame clock at the last message
        self.now = 0.0
        self.hits: list[tuple[str, float]] = []     # this frame's (name, velocity)
        self.moved: list[int] = []          # this frame's axes that a message set
        self._taken = False
        self._names: dict[str, int] = {}

    # ---- the entry ----

    @property
    def timeout(self) -> float:
        t = self.entry.get("timeout", TIMEOUT_S)
        return float(t) if isinstance(t, int | float) and not isinstance(t, bool) and t > 0 \
            else TIMEOUT_S

    @property
    def hold(self) -> bool:
        return self.entry.get("hold", True) is not False

    def _layout(self) -> Layout | None:
        try:
            return self.layout or Layout(self.entry)
        except ValueError:
            return None

    def open(self) -> None:
        from .routing import is_continuous

        role = self.role
        if not is_continuous(role) or role in BUILTIN_SCHEMES or role == CLOUD_SCHEME:
            raise ValueError(f"role {role!r} is a scheme the app already reads — "
                             "give the device another role")
        layout = Layout(self.entry)
        host = self.entry.get("host", DEFAULT_HOST)
        port = self.entry.get("port", DEFAULT_PORT)
        if not isinstance(host, str) or not host:
            raise ValueError(f"host = {host!r} is not an address")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError(f"port = {port!r} is not a UDP port")
        self.io = Server(host, port)
        self.layout = layout
        self.message = ""
        self._reset()
        self._names = {n: i for i, n in enumerate(layout.names)}   # a new map: republished

    def close(self) -> None:
        """The socket closed; the router it fed is told the lanes are gone,
        so a held value does not outlive the device (an entry removed or
        changed, a quit)."""
        router = self.__dict__.pop("_router", None)
        super().close()
        self._reset()
        if router is not None:
            router.feed(self.role, None)

    # ---- the status line ----

    @property
    def status(self) -> str:
        if self.error or self.io is None:
            return super().status
        heard = self.heard
        return "connected" if heard is not None and self.now - heard <= self.timeout else "lost"

    @property
    def last(self) -> str:
        io = self.io
        if io is None:
            return ""
        out = f"UDP {io.host}:{io.port}"
        if self.message:
            out += f"  ·  {self.message}"
        if io.bad:
            out += f"  ·  {io.bad} not OSC"
        return out

    @property
    def sources(self) -> tuple[Port, ...]:
        layout = self._layout()
        if layout is None:
            return ()
        axes = [Port(n, n, rest=r, group="axes", scheme=self.role)
                for n, r in zip(layout.names, layout.rests, strict=True)]
        hits = [Port(n, n, kind="trigger", velocity=True, group="hits", scheme=self.role)
                for n in layout.hit_names.values()]
        return tuple(axes + hits)

    # ---- the frame ----

    def poll(self, dt: float, now: float) -> None:
        """Every message waiting: an axis's value set, a hit kept for this
        frame's rows. Any message at all (an address not listed included)
        keeps the device `connected`."""
        self.now = now
        self.hits, self.moved, self._taken = [], [], False
        io, layout = self.io, self.layout
        if io is None or layout is None:
            return
        for address, args in io.read():
            self.heard = now
            self.message = _say(address, args)
            i = layout.index.get(address)
            if i is not None:
                v = _number(args)
                if v is not None:
                    self.values[i] = layout.norm(v)
                    self.moved.append(i)
                continue
            name = layout.hit_names.get(address)
            if name is not None:
                v = _number(args)
                self.hits.append((name, 1.0 if v is None else _clamp(v)))

    def learn(self, learn) -> bool:
        """An armed Learn this device may complete (`Learn.accepts`): a hit
        lands a button row (`learn_pad_button`, the session's, like a pad
        button's) and holds this frame's rows back; else an axis moved
        `LEARN_TRAVEL` from its rest lands a route (`learn_source`)."""
        if learn is None or getattr(learn, "learning", None) is None or self.layout is None:
            return False
        for name, vel in self.hits:
            source = f"{self.role}:{name}"
            if vel > 0 and learn.accepts(source):
                learn.learn_pad_button(source)
                self._taken = True
                return True
        target = learn.target_for(learn.learning)
        if target is None or not target.modulatable:
            return False
        for i in self.moved:
            rest = self.layout.rests[i]
            source = f"{self.role}:{self.layout.names[i]}"
            if abs(self.values[i] - rest) >= LEARN_TRAVEL and learn.accepts(source):
                learn.learn_source(source, centred=0.0 < rest < 1.0)
                return False
        return False

    def act(self, router) -> None:
        """This frame's hits delivered as rows (unless one completed a learn)."""
        if self._taken or not self.hits:
            return
        from .routing import MOD_OPS

        rows = [b for b in router.table.of(self.role) if b.enabled and b.op not in MOD_OPS]
        for name, vel in self.hits:
            for b in rows:
                if ":".join(b.parts) == name:
                    fire(router.reg, b, vel)

    def feed(self, router) -> None:
        """The axes under the role: their names, labels and rests published
        (once per open), then the vector — None before the first message,
        and after a silence when the entry says ``hold = false``."""
        layout, role = self.layout, self.role
        self._router = router                   # told on close that the lanes are gone
        if layout is None:
            return
        if router.names.get(role) is not self._names:
            router.labels[role] = list(layout.names)
            router.rests[role] = list(layout.rests)
            router.names[role] = self._names
        if self.heard is None:
            router.feed(role, None)
            return
        if not self.hold and self.status == "lost":
            self.values[:] = np.nan             # back on fresh messages only
            router.feed(role, None)
            return
        router.feed(role, self.values.copy())

    def targets(self) -> list[tuple]:
        return [(self.io, "osc", "Server")] if self.io is not None else []


def fire(reg, b, velocity: float) -> None:
    """One hit on one row (module docstring): `abs` lands the velocity,
    `momentary` holds a toggle while it is above 0, `hold` does nothing (no
    OSC hit has a duration), any other op acts when it is above 0."""
    from .params import Kind
    from .routing import act, land

    p = reg.get(b.target)
    if p is None or not b.enabled:
        return
    pressed = velocity > 0.0
    if b.op == "abs":
        if p.kind is Kind.TRIGGER:
            if pressed:
                p.fire()
        else:
            land(p, velocity)
    elif b.op == "momentary":
        if p.kind is Kind.TOGGLE:
            p.set(pressed)
        elif pressed:
            p.toggle()
    elif b.op == "hold":
        return
    elif pressed:
        act(reg, b)
