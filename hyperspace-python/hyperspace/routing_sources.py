"""The router's shared sources (plan 44 D2): what every source has said
this frame, one for the rig.

`Sources` is the half of the old `routing.Router` that the adapters write
and every deck's pass reads: each scheme's vector this frame (`feeds`),
the names, rests, gates and signal kinds an adapter publishes for its
lanes (`labels`, `rests`, `gates`, `lane_kinds`), the address map a scheme
with named lanes publishes (`names`) and what an address means over it
(`resolve`, `address`), the device registry it asks which schemes there
are (`use`, `follow_devices`, `schemes`), the scheme's own feel and its
rule (`source_feel`: the pad's feel for `axis`, none else), the key and
button constants a row names (`code`), and the one clock every router's banks
step on (plan 44 §2: one beat for every deck). The
evaluator — the patch, the banks, the macros, the modifiers' memory, the
rows' followers and the camera job's (`Router.felt`), the key and pad
rows — stays `routing.Router`, one per
deck, built over a `Sources` (`Router(reg, table, sources)`); one `Sources`
fed once a frame can feed two routers over two registries, which is what
decks need first (plan 44 §1).

The scheme grammar a source address is spelled in lives here too, since
the sources resolve it: `BUILTIN_LANES`, `MIDI_SCHEMES`, `ROW_SCHEMES`,
`QUALIFIER`, `base_scheme`, `qualified`, `is_continuous`. `routing.py`
imports them back, and re-exports `Sources`, so no importer changes.

What is a deck's stays off the sources (plan 44 D4, row 591 changed): the
lanes a deck makes for itself — its LFOs', envelopes', sequencer's and
modifiers' (`DECK_SCHEMES`) — live in that router's own `LaneLayer`, read
over these sources through `Layered`. A scheme the layer does not hold falls
through to the sources, so whatever feeds one with no bank still feeds it.

A leaf below `routing`: it imports `motion`, `pointer` and numpy, and `glfw` /
`gamepad` only lazily, to resolve key and pad names
(`tests/test_routing_boundary.py`). The meta controller facts the device registry
states — which schemes are rows, which MIDI role an unqualified row
means, which device is a scheme's primary — are written into every live
binding table that follows these sources (`follow`, held weakly). The
sources read no table: what an address means under a table's primaries
(`resolve`) and a scheme's feel under a table's pad feel (`source_feel`)
are asked with that table's facts, so each router resolves
against its own table and caches the answer itself.
"""

from __future__ import annotations

import weakref
from collections.abc import Iterator, MutableMapping
from typing import Any, NamedTuple

import numpy as np

from . import pointer
from .motion import OFF, Motion

# the schemes no device feeds — the analyzer, the LFOs, the envelopes and
# the sequencer's trigger lanes (plan 31) — in offer order; devices.py's
# BUILTIN_SCHEMES, restated (routing never imports devices), the two held
# equal by tests/test_plan31_wiring.py
BUILTIN_LANES = ("lane", "lfo", "env", "seq")
# the schemes a deck makes for itself and no device feeds: its banks' lanes
# and its modifiers' (plan 44 D4, row 591). Each router keeps its own
# (`LaneLayer`), so two decks' `lfo:0` are two lanes; held equal to the
# banks' and `modifiers.SCHEME` by tests/test_routing_sources.py
DECK_SCHEMES = frozenset(("lfo", "env", "seq", "mod"))

# the schemes no controller feeds: an analyzer's lanes and a deck's own. A route from one is
# no mapping for node mode, which holds its param off it instead (`Bindings.node_holds`)
MODULATOR_SCHEMES = frozenset(BUILTIN_LANES) | DECK_SCHEMES

MIDI_SCHEMES = ("cc", "note", "pitch")
# the row kinds the table dispatches itself (plan 27 B2): the keys
# (`Router.keys`), the pad's buttons and D-pad (`Router.pad`) and MIDI
# (midi.MidiIO). Every other scheme is a **continuous** source — a lane
# some device feeds (`lane`, `lfo`, `hand`, `axis`, a new device's role) —
# so a patch row naming a device this rig lacks is still a performer,
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


# Plan 56: two discrete controls of one pad as one bipolar lane. The address
# is its own declaration, ``pair:<+ pole>/<− pole>`` in the rows' own control
# names (``pair:UP/DOWN``, ``pair@p2:RB/LB``), so nothing lists a pair but the
# row that reads it. Continuous: a route reads it as it reads a stick; a `step`
# row on one is `Router.pad`'s
PAIR_SCHEME = "pair"
PAIR_SEP = "/"
PAIR_REST = 0.5


class Pole(NamedTuple):
    """One end of a pair: the row source its control is (``hat:UP``,
    ``pad:LB``), the constant that reads it, and whether that is a hat bit."""

    source: str
    code: int
    hat: bool


_POLES: dict[str, tuple[Pole, Pole] | None] = {}


def pair_address(pos: str, neg: str, role: str = "") -> str:
    """A pair's source address, from its poles' control names."""
    return f"{qualified(PAIR_SCHEME, role)}:{pos}{PAIR_SEP}{neg}"


def pair_poles(addr: str) -> tuple[Pole, Pole] | None:
    """The (+, −) poles the address after ``pair:`` names; None unless it
    names two different controls a pad can have."""
    if addr in _POLES:
        return _POLES[addr]
    try:
        from . import gamepad
    except ImportError:          # no window system: dormant (decision 11), asked again later
        return None
    got = None
    pos, sep, neg = addr.partition(PAIR_SEP)
    if sep and pos != neg:
        poles = []
        for name in (pos, neg):
            if name in gamepad.HATS:
                poles.append(Pole(f"hat:{name}", gamepad.HATS[name], True))
            elif name in gamepad.ALL_BUTTONS:
                poles.append(Pole(f"pad:{name}", gamepad.ALL_BUTTONS[name], False))
        if len(poles) == 2:
            got = (poles[0], poles[1])
    _POLES[addr] = got
    return got


def pole_free(pad, pole: Pole, skip=frozenset()) -> bool:
    """`models.control_free` for one of `pad`'s poles: a pole held by anything
    else neither moves a lane nor fires a row."""
    from . import gamepad  # (a pole was read through it: it is there)
    models = gamepad.models
    m = getattr(pad, "model", None)
    return models.control_free(m if models.is_model(m) else None,
                               pole.source.partition(":")[2], skip)


def pair_lanes(pad, names: dict[str, int], skip=frozenset()) -> list[float]:
    """Each pair's lane this frame (`names`: address → lane): 1 on its + pole,
    0 on its − pole, its rest with neither or both. A pole that is not free
    (`pole_free`) reads as not pressed."""
    def held(pole: Pole) -> int:
        if not pole_free(pad, pole, skip):
            return 0
        return int(bool(pad.hat & pole.code) if pole.hat else pad.down(pole.code))
    out = [PAIR_REST] * len(names)
    for addr, i in names.items():
        poles = pair_poles(addr)
        if poles is not None:
            out[i] = PAIR_REST + PAIR_REST * (held(poles[0]) - held(poles[1]))
    return out


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


class Layered(MutableMapping):
    """One of a router's views of a per-scheme dict: its deck's own layer
    over the shared sources' (plan 44 D4). A read finds the layer's entry,
    else the sources'; a write of a deck's scheme (`DECK_SCHEMES`) lands in
    the layer, any other in the sources, so an adapter handed the router
    writes where it always did. `hide` (plan 55): shared schemes this view
    does not read, a controller's on another deck (`Sources.away_from`). A
    write and a delete still reach them."""

    __slots__ = ("hide", "own", "shared")

    def __init__(self, own: dict, shared: dict, hide=frozenset()):
        self.own, self.shared, self.hide = own, shared, hide

    def __getitem__(self, scheme: str) -> Any:
        own = self.own
        if scheme in own:
            return own[scheme]
        if scheme in self.hide:
            raise KeyError(scheme)
        return self.shared[scheme]

    def get(self, scheme: str, default: Any = None) -> Any:
        own = self.own
        if scheme in own:
            return own[scheme]
        return default if scheme in self.hide else self.shared.get(scheme, default)

    def __contains__(self, scheme: object) -> bool:
        return scheme in self.own or (scheme in self.shared and scheme not in self.hide)

    def __setitem__(self, scheme: str, value: Any) -> None:
        (self.own if scheme in DECK_SCHEMES else self.shared)[scheme] = value

    def __delitem__(self, scheme: str) -> None:
        del (self.own if scheme in self.own else self.shared)[scheme]

    def pop(self, scheme: str, *default) -> Any:
        """As `__delitem__` goes, hidden or not (the inherited one reads first)."""
        return (self.own if scheme in self.own else self.shared).pop(scheme, *default)

    def setdefault(self, scheme: str, default: Any = None) -> Any:
        """As a write goes, keeping what is there, hidden or not."""
        if scheme in self.own:
            return self.own[scheme]
        return (self.own if scheme in DECK_SCHEMES else self.shared).setdefault(scheme, default)

    def __iter__(self) -> Iterator[str]:
        for scheme in self.shared:
            if scheme not in self.hide or scheme in self.own:
                yield scheme
        for scheme in self.own:
            if scheme not in self.shared:
                yield scheme

    def __len__(self) -> int:
        return sum(1 for _ in self)


class LaneLayer:
    """One deck's own lanes (plan 44 D4, row 591): what its banks and its
    modifiers publish — the five per-scheme dicts the sources hold for the
    meta controller's — and nobody else's pass or panel reads."""

    __slots__ = ("feeds", "gates", "labels", "lane_kinds", "rests")

    def __init__(self) -> None:
        self.feeds: dict[str, np.ndarray | None] = {}
        self.labels: dict[str, list[str]] = {}
        self.rests: dict[str, list[float]] = {}
        self.gates: dict[str, list[tuple[int, str]]] = {}
        self.lane_kinds: dict[str, list[str]] = {}

    def drop(self, scheme: str) -> None:
        """`scheme` no longer offered by this deck."""
        for name in self.__slots__:
            getattr(self, name).pop(scheme, None)


_NO_LANES: dict = {}      # a router's lane cache before its first miss; never written
_NO_PRIMARIES: dict = {}  # a table that names no primaries; never written
_NOWHERE: frozenset = frozenset()   # `away_from`, with every controller on this deck


class Sources:
    """What every source said this frame, shared by every router over it.

    `devices` is the meta controller's device registry (devices.DeviceRegistry, plan 27
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
        registry's meta controller facts from now on (`follow_devices`). Held weakly:
        a table no router keeps is forgotten, never written again. Plan 44
        D3 (row 593's note): the meta controller facts are the meta controller's, so a deck's
        table is followed through its meta table (`table.meta_table`, a
        `routing.MetaTable`) — every deck over one meta controller is told at
        once, and the meta controller is written once."""
        table = getattr(table, "meta_table", None) or table
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
            if i < 0 and base == PAIR_SCHEME and pair_poles(addr) is not None:
                # a pair no pad publishes by default: its row declares it
                pos, _, neg = addr.partition(PAIR_SEP)
                m = self.add_pairs(scheme, [(addr, f"{pos} / {neg}")])
                i = m[addr]
        return scheme, m, i

    def add_pairs(self, scheme: str, pairs) -> dict[str, int]:
        """Publish lanes for `pairs` ((address after ``pair:``, label)) under
        `scheme`, those it lacks, at its end: the names map is replaced, so
        every address resolves again. One it has takes the label given (a
        row can have named a natural pair first, with no words for it).
        Called once a frame: nothing changed, nothing is written. Returns the map."""
        m = self.names.get(scheme) or {}
        labels = self.labels.get(scheme) or []
        for a, lb in pairs:
            if a in m and labels[m[a]] != lb:
                labels = self.labels[scheme] = list(labels)
                labels[m[a]] = lb
        new = [(a, lb) for a, lb in pairs if a not in m]
        if not new:
            return m
        m = dict(m)
        labels = list(labels)
        rests = list(self.rests.get(scheme) or ())
        for addr, label in new:
            m[addr] = len(m)
            labels.append(label)
            rests.append(PAIR_REST)
        self.labels[scheme], self.rests[scheme] = labels, rests
        self.names[scheme] = m
        return m

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

    def away_from(self, router) -> frozenset[str]:
        """The schemes `router`'s pass does not read this frame (plan 55): those
        of a controller whose pointer is on another deck, so a row acts only on
        the `Deck` its player is on. Asked of the device registry (`holders`:
        scheme → that controller's pointer), a pointer's move counting at once.
        The analyzer is nobody's, a deck's own lanes are its own, and a bare
        registry or none holds nothing, so nothing is hidden. Kept on the router
        until a pointer moves or the list changes: the panel asks per cable."""
        holders = getattr(self.__dict__.get("devices"), "holders", None)
        if holders is None:
            return _NOWHERE
        held = holders()
        hit = router.__dict__.get("_away")
        if hit is not None and hit[0] == pointer.moves and hit[1] is held:
            return hit[2]
        away = [s for s, p in held.items() if p.deck.router is not router]
        got = frozenset(away) if away else _NOWHERE
        router.__dict__["_away"] = (pointer.moves, held, got)
        return got

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
