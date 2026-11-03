"""The router's shared sources (plan 44 D2): what every source has said
this frame, one for the rig.

`Sources` is the half of the old `routing.Router` that the adapters write
and every deck's pass reads: each scheme's vector this frame (`feeds`),
the names, rests, gates and signal kinds an adapter publishes for its
lanes (`labels`, `rests`, `gates`, `lane_kinds`), the address map a scheme
with named lanes publishes (`names`) and what an address means over it
(`resolve`, `address`), the device registry it asks which schemes there
are (`use`, `follow_devices`, `schemes`), the scheme's own feel and its
followers (`source_feel`, `felt`, `felt_lanes`), the key and button
constants a row names (`code`), and the one clock every router's banks
step on (plan 44 §2: one beat for every deck). The
evaluator — the patch, the banks, the macros, the modifiers' memory, the
rows' followers, the key and pad rows — stays `routing.Router`, one per
deck, built over a `Sources` (`Router(reg, table, sources)`); one `Sources`
fed once a frame can feed two routers over two registries, which is what
decks need first (plan 44 §1).

The scheme grammar a source address is spelled in lives here too, since
the sources resolve it: `BUILTIN_LANES`, `MIDI_SCHEMES`, `ROW_SCHEMES`,
`QUALIFIER`, `base_scheme`, `qualified`, `is_continuous`. `routing.py`
imports them back, and re-exports `Sources`, so no importer changes.

A leaf below `routing`: it imports `motion` and numpy, and `glfw` /
`gamepad` only lazily, to resolve key and pad names
(`tests/test_routing_boundary.py`). The rig facts the device registry
states — which schemes are rows, which MIDI role an unqualified row
means, which device is a scheme's primary — are written into every live
binding table that follows these sources (`follow`, held weakly). The
sources read no table: what an address means under a table's primaries
(`resolve`) and a scheme's feel under a table's pad feel (`source_feel`,
`felt`) are asked with that table's facts, so each router resolves
against its own table and caches the answer itself.
"""

from __future__ import annotations

import weakref

import numpy as np

from .motion import OFF, Follower, Motion

# the schemes no device feeds — the analyzer, the LFOs, the envelopes and
# the sequencer's trigger lanes (plan 31) — in offer order; devices.py's
# BUILTIN_SCHEMES, restated (routing never imports devices), the two held
# equal by tests/test_plan31_wiring.py
BUILTIN_LANES = ("lane", "lfo", "env", "seq")

MIDI_SCHEMES = ("cc", "note", "pitch")
# the row kinds the table dispatches itself (plan 27 B2): the keys
# (`Router.keys`), the pad's buttons and D-pad (`Router.pad`) and MIDI
# (midi.MidiIO). Every other scheme is a **continuous** source — a lane
# some device feeds (`lane`, `lfo`, `hand`, `axis`, a new device's role) —
# so a preset row naming a device this rig lacks is still a performer,
# dormant until its device feeds (decision 11). Which continuous schemes
# exist, and in what order a page offers them, is the device registry's
# (`Sources.schemes`, devices.DeviceRegistry.continuous_schemes): there is
# no fixed list of them here
ROW_SCHEMES = ("key", "pad", "hat", *MIDI_SCHEMES)
# a source's device qualifier (plan 27 B2 for MIDI, B6 for every scheme):
# ``cc@<role>:<ch>:<n>``, ``pitch@<role>:<ch>``, ``pad@<role>:A``,
# ``axis@<role>:LX`` — the row of a device other than the first one listed
# that publishes the scheme. An unqualified source is that first device's
# (MIDI: `Bindings.midi_roles`, the profile-matching rule B2 built; any
# other scheme: `Bindings.primaries`, the first enabled device of its kind
# in list order), so every row written before plan 27 means what it meant.
# The qualifier adds no ``:`` (a role has none). For a continuous scheme
# the qualified head (``axis@p2``) is its own Sources key — its own feed,
# labels, rests and names — so two pads never overwrite each other
QUALIFIER = "@"


def base_scheme(scheme: str) -> str:
    """A scheme without its device qualifier: ``cc@launch`` → ``cc``,
    ``axis@p2`` → ``axis`` (plan 27 B6: any scheme takes one); a scheme
    with none is returned as it is."""
    head, at, _ = scheme.partition(QUALIFIER)
    return head if at else scheme


def qualified(scheme: str, role: str) -> str:
    """`scheme` under the device qualifier `role` (``axis`` + ``p2`` →
    ``axis@p2``); "" leaves it bare — the primary device's (plan 27 B6)."""
    return f"{scheme}{QUALIFIER}{role}" if role else scheme


def is_continuous(scheme: str) -> bool:
    """Is `scheme` a continuous source — read by the Router as a lane,
    driven through a performer row — rather than a row kind the table
    dispatches (`ROW_SCHEMES`)? Open-ended: a scheme no device of this rig
    publishes is continuous too, its rows dormant (decision 11)."""
    return base_scheme(scheme) not in ROW_SCHEMES


_NO_LANES: dict = {}      # a router's lane cache before its first miss; never written
_NO_PRIMARIES: dict = {}  # a table that names no primaries; never written


class Sources:
    """What every source said this frame, shared by every router over it.

    `devices` is the rig's device registry (devices.DeviceRegistry, plan 27
    B2), handed in as an argument — this module imports nothing above it —
    and asked which continuous schemes there are and in what order a page
    offers them (`schemes`); None (bare sources, the tests') offers what
    has been fed or labelled. `clock` is the tap-tempo clock every router's
    banks step on — one for the rig: the first `Router.use_bank` sets it
    when none was given, and a router handed another clock is refused."""

    def __init__(self, devices=None, *, clock=None):
        # the binding tables that follow these sources (`follow`), held
        # weakly: a router dropped (the panel's swap) lets its table go
        self._tables: list[weakref.ref] = []
        self.devices = None
        self.clock = clock
        self.feeds: dict[str, np.ndarray | None] = {}   # ext/lfo/hand vectors, per frame
        self.labels: dict[str, list[str]] = {}          # scheme → lane names, from the adapter
        # scheme → the lanes an adapter offers as gates, [(index, label)]:
        # switch-like lanes a row's `when` can wait on. The adapter says
        # which of its lanes those are; nothing here knows about hands.
        self.gates: dict[str, list[tuple[int, str]]] = {}
        # scheme → where each lane sits idle, published like `labels`: what
        # a push row with no rest of its own uses, every frame (a hand axis
        # its configured rest value, a presence lane 0, an LFO 0.5); the
        # analyzer's lanes, and any scheme that publishes nothing, rest at 0
        self.rests: dict[str, list[float]] = {}
        # `names` (scheme → {address name: lane}) is made on first use
        self._codes: dict[str, int | None] = {}
        if devices is not None:
            self.use(devices)

    # ---- the tables that follow these sources ----

    def follow(self, table) -> None:
        """`table` (a routing.Bindings a router runs over) is told the
        registry's rig facts from now on (`follow_devices`). Held weakly:
        a table no router keeps is forgotten, never written again."""
        if any(r() is table for r in self._tables):
            return
        self._tables.append(weakref.ref(table))
        if self.devices is not None:
            self._tell(table)

    @property
    def tables(self) -> list:
        """The live tables that follow these sources, in the order they came."""
        live = [t for r in self._tables if (t := r()) is not None]
        if len(live) != len(self._tables):
            self._tables = [weakref.ref(t) for t in live]
        return live

    # ---- the device registry (plan 27 B2) ----

    def use(self, devices) -> None:
        """Ask `devices` (anything with `continuous_schemes()`, and
        optionally `row_schemes()` and `midi_roles()`) from now on: which
        schemes are lanes and in what order (`schemes`), which a device
        delivers as rows (the referee's `row_schemes`), which MIDI role an
        unqualified row means (`Bindings.midi_roles`). Called again
        whenever the device list changes."""
        self.devices = devices
        self.follow_devices()

    def follow_devices(self) -> None:
        """Re-read the registry's row schemes and MIDI roles into every
        table that follows (the registry's listener calls it when the list
        changes)."""
        if self.__dict__.get("devices") is None:
            return
        for t in self.tables:
            self._tell(t)

    def _tell(self, table) -> None:
        devs = self.devices
        rows = getattr(devs, "row_schemes", None)
        if rows is not None:
            table.row_schemes = tuple(dict.fromkeys((*ROW_SCHEMES, *rows())))
        roles = getattr(devs, "midi_roles", None)
        if roles is not None:
            table.midi_roles = tuple(roles())
        prim = getattr(devs, "primaries", None)
        if prim is not None:
            # a new dict: a router's lane cache is kept against its identity,
            # so an ``axis@pad`` address resolves again (`resolve`)
            table.primaries = dict(prim())

    def schemes(self) -> tuple[str, ...]:
        """The continuous schemes a route can read, in the order a page
        offers them: the registry's (`continuous_schemes`: the analyzer's
        `lane` and the LFOs' `lfo` first, then each listed device's feeds
        in list order), then any other scheme that has been fed or
        labelled this run. With no registry, `BUILTIN_LANES` (the
        analyzer, the LFOs, the envelopes, the sequencer) and then whatever
        has been fed or labelled."""
        devs = self.__dict__.get("devices")
        out = list(devs.continuous_schemes()) if devs is not None else [*BUILTIN_LANES]
        for s in (*self.labels, *self.feeds):
            if s not in out and is_continuous(s):
                out.append(s)
        return tuple(out)

    # ---- the lanes' addresses ----

    @property
    def names(self) -> dict[str, dict[str, int]]:
        """scheme → {address name: lane index}, published like `labels`
        by an adapter whose lanes have names (the hands: ``"right.roll"``
        → its lane, decision register row 20), by plain assignment of a
        **new** dict whenever its layout changes — the resolved addresses
        are cached against that dict's identity. A row naming
        ``hand:right.roll`` reads the lane this map gives; a name the map
        lacks, or any name while no map is published, is dormant — never
        another lane. A numeric address (``hand:7``) is the lane at that
        index whatever the map says."""
        d = self.__dict__.get("_names")
        if d is None:
            d = self.__dict__["_names"] = {}
        return d

    @property
    def lane_kinds(self) -> dict[str, list[str]]:
        """scheme → each lane's signal kind, "value" or "trigger" (decision
        10), published like `labels` by a source that has triggers: the
        ``mod`` lanes, where a threshold's output is a trigger, the
        sequencer's, a pad's touch lanes. A trigger lane is still read as a
        value (1 while it fires, else 0)."""
        d = self.__dict__.get("_lane_kinds")
        if d is None:
            d = self.__dict__["_lane_kinds"] = {}
        return d

    def resolve(self, source: str, primaries: dict | None = None
                ) -> tuple[str, dict | None, int]:
        """(scheme, the map it was resolved against, lane index) that a
        source address names under a table's `primaries` (scheme → the
        primary device's role, `Bindings.primaries`): its number, or its
        name through `names`, with −1 for an address that names no lane (a
        name the adapter's map lacks, no map yet, garbage), which every
        reader treats as dormant. A source qualified with the primary's own
        role (``axis@pad:RT``) means the bare scheme's lanes (B6). Not
        cached here: each router caches against its own table's primaries
        and the map's identity (`Router.lane`)."""
        scheme, _, addr = source.partition(":")
        base, at, role = scheme.partition(QUALIFIER)
        if at and role and (primaries or _NO_PRIMARIES).get(base) == role:
            scheme = base        # qualified with the primary's own role: its lanes (B6)
        m = self.names.get(scheme)
        try:
            i = int(addr)
        except ValueError:
            i = -1 if m is None else m.get(addr, -1)
        return scheme, m, i

    def address(self, scheme: str, i: int) -> str:
        """Lane `i` of `scheme` as a row should name it: by its published
        name when the scheme has one (``hand:right.roll``), else by index."""
        m = self.names.get(scheme)
        if not m:
            return f"{scheme}:{i}"
        inv = self.__dict__.setdefault("_inverse", {})    # scheme → (map, {lane: name})
        hit = inv.get(scheme)
        if hit is None or hit[0] is not m:                 # the page asks per row per frame
            hit = inv[scheme] = (m, {k: n for n, k in m.items()})
        name = hit[1].get(i)
        return f"{scheme}:{name}" if name is not None else f"{scheme}:{i}"

    def code(self, b) -> int | None:
        """The key / button / hat constant a row's source names (`b` a
        routing.Binding); None if there is none. Cached per source."""
        src = b.source
        if src not in self._codes:
            self._codes[src] = _resolve(b.scheme, ":".join(b.parts))
        return self._codes[src]

    # ---- the feeds ----

    def feed(self, scheme: str, values) -> None:
        """An adapter hands in this frame's vector for `ext` / `lfo` sources
        (None: not live, its rows let go)."""
        self.feeds[scheme] = None if values is None else np.asarray(values, dtype=float)

    # ---- motion (motion.py): a source's own feel ----

    def source_feel(self, scheme: str, pad_feel: Motion = OFF) -> Motion:
        """A scheme's own feel: the pad's (`pad_feel`, the asking table's
        `Bindings.pad_feel`) for `axis`, none for every other source — the
        analyzer's lanes have theirs in the chain already, a hand has its
        own smoothing. One feel for every pad (plan 27 B6): ``axis@p2``
        travels with it too."""
        return pad_feel if base_scheme(scheme) == "axis" else OFF

    def felt(self, scheme: str, values, dt: float,
             pad_feel: Motion = OFF) -> list[float] | None:
        """`values` — an adapter's lanes for `scheme` — through the scheme's
        own feel, one follower per lane: what the pad's default camera job
        reads (app.py). None while that feel is off or `values` is None,
        and the followers are dropped, so the next one starts where the
        source is. `pad_feel` is the asking table's (`source_feel`)."""
        m = self.source_feel(scheme, pad_feel)
        felt = self.__dict__.setdefault("_felt", {})
        if values is None or not m.on:
            felt.pop(scheme, None)
            return None
        rests = self.rests.get(scheme) or []
        fs = felt.get(scheme)
        if fs is None or len(fs) != len(values):
            fs = felt[scheme] = [Follower(v) for v in values]
        return [f.step(v, dt, m, rests[i] if i < len(rests) else 0.0)
                for i, (f, v) in enumerate(zip(fs, values))]

    def felt_lanes(self, scheme: str) -> list[float] | None:
        """`scheme`'s lanes after its own feel, as the last `felt` left
        them (the pad's camera job; the SYSTEM page's plot); None while
        that feel is off or nothing has run it."""
        fs = self.__dict__.get("_felt", {}).get(scheme)
        return None if fs is None else [f.x for f in fs]


def _resolve(scheme: str, name: str) -> int | None:
    """key:NAME → glfw.KEY_NAME; pad:NAME → gamepad.NAME; hat:DIR → gamepad.HAT_DIR.
    Imported here so the table itself never needs a window system."""
    try:
        if scheme == "key":
            import glfw
            return getattr(glfw, f"KEY_{name.rsplit('+', 1)[-1]}")   # SHIFT+B → KEY_B
        from . import gamepad
        return getattr(gamepad, f"HAT_{name}" if scheme == "hat" else name)
    except (ImportError, AttributeError):
        return None
