"""The hands as a device on this host's registry (plan 27 B2).

A thin wrapper that owns a `HandsIO` and satisfies the device protocol
(devices.py): it opens the instrument behind its `[[devices]]` entry,
makes the instrument's one call — ``HandsIO.poll(dt, learn, router)``,
which reads the tracker, makes the frame's DAW MIDI, feeds ``hand`` and
``hands`` and completes a hand Learn at once — from the registry's feed
slot (the DAW MIDI goes out through the `hands-daw` sink, a `midi-out`
device that carries it after ``reg.apply``: plan 27 B3), and
describes the instrument's lanes as ports for the SYSTEM page and the node
editor (plan 28).

Like panel.py, this file knows the host: it is the adapter to *this*
registry, and extracting the package means replacing it. core.py,
signal.py and tape.py import nothing from it, nor from the host
(tests/test_hands_boundary.py). The lane layout is `Layout`'s — this
wrapper reads every count from it and pins none (plan 24 C4 and C5 grew
it; the dance lanes are the port group ``dance``, the pinches and the
grabs the group ``switches``). The ghost renderer reads the same
`HandsIO` through ``renderer.ghost.source``: the registry's listener in
app.main hands it over whenever the device list changes.
"""

from __future__ import annotations

from pathlib import Path

from ..devices import Base, Context, Port


class HandsDevice(Base):
    """`hands.HandsIO` as a device. Its `wants` are the two hands (a Learn
    armed "hand:left" completes from the left hand's axes only); its
    `schemes` and `feeds` are ``hand`` (each hand: axes, presence, switches,
    the dance sources, the grab) and ``hands`` (the two together: gap,
    twist). Status: `connected` while the tracker (or a tape) gives
    frames, `lost` while it looks for one, ``error: …`` when the tracker
    says why it cannot."""

    kind = "hands"
    schemes = ("hand", "hands")
    feeds = ("hand", "hands")
    wants = ("hand:left", "hand:right")

    def __init__(self, role: str, entry: dict | None = None, ctx: Context | None = None, *,
                 io=None):
        super().__init__(role, entry, ctx, io=io)
        self._dt = 0.0
        self._learn = None

    def open(self) -> None:
        if self.ctx.hand_settings is None:
            raise RuntimeError("no hands setup ([hands] would not read)")
        from . import HandsIO
        e = self.entry
        cal = e.get("calibration")
        self.io = HandsIO(self.ctx.hand_settings, e, cal_path=Path(cal) if cal else None)

    @property
    def status(self) -> str:
        io = self.io
        if self.error or io is None:
            return super().status
        s = io.status or ""
        if getattr(io.source, "on", True) or s in ("tracking", "connected"):
            return "connected"
        if s in ("", "connecting") or s.startswith("tape"):
            return "lost"
        return f"error: {s}"

    @property
    def last(self) -> str:
        io = self.io
        return (io.last or io.status or "") if io is not None else ""

    @property
    def sources(self) -> tuple[Port, ...]:
        """The instrument's lanes as ports, in `Layout` order: the axes
        (group ``axes``, with their rests and whether they are centred),
        the switches (``switches``: the pinches and the grabs, the layout's
        `gates`), the presence lanes (``presence``), the dance sources
        (``dance``) — all under ``hand`` — then the pair's lanes under
        ``hands`` (gap, twist; group ``dance``). Counts are the layout's."""
        io = self.io
        if io is None:
            return ()
        lay, axes, rests = io.layout, io.axes, io.rests()
        gates = dict(lay.gates)
        out = []
        for i, (addr, label) in enumerate(zip(lay.addresses, lay.names, strict=True)):
            if i < lay.n_axes:
                out.append(Port(addr, label, rest=rests[i], bipolar=bool(axes[i].bipolar),
                                group="axes", scheme="hand"))
            elif i in gates:
                out.append(Port(addr, label, group="switches", scheme="hand"))   # pinches, grabs
            elif addr.endswith(".present"):
                out.append(Port(addr, label, group="presence", scheme="hand"))
            else:   # plan 24 C4's dance sources (curl, spread, energy, flick)
                out.append(Port(addr, label, rest=rests[i], group="dance", scheme="hand"))
        pair = getattr(lay, "pair_addresses", None) or []
        names = getattr(lay, "pair_names", None) or pair
        prests = io.pair_rests() if pair else []
        for k, addr in enumerate(pair):
            out.append(Port(addr, names[k] if k < len(names) else addr,
                            rest=float(prests[k]) if k < len(prests) else 0.0,
                            group="dance", scheme="hands"))
        return tuple(out)

    def poll(self, dt: float, now: float) -> None:
        self._dt = dt

    def learn(self, learn) -> bool:
        self._learn = learn
        return False

    def feed(self, router) -> None:
        if self.io is not None:
            self.io.poll(self._dt, self._learn, router)

    def targets(self) -> list[tuple]:
        return [(self.io, "hands.core", "HandsIO")] if self.io is not None else []
