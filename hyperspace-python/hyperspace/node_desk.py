"""Node mode on a controller (plan 53 N1, N2): the rows `nodemode` says, per player and per `Deck`.

The owner, 2026-11-04: a controller points at one node, "its degrees of freedom filled
by that node's params", saved in the loadable patch, with no latch and no paging. So this
holds nothing of its own to save: each `Deck`'s table has a `NodeDesk`
(`Bindings.node_desk`), which reads what that deck's loadable patch points where
(`LoadedPatch.node_mode`) and derives the rows (`nodemode.fill`), the same objects until
what they say moves. A row's state (its catch, its last ring) is kept on it.

**Whose rows.** A saved entry names a player and a kind, so the rows are for that player's
first MIDI controller (`controller_of`), read on this deck's table: a desk reads the table
of the deck its pointer is on (`MidiIO.table`), so a desk on the other `Deck` is not reached,
and the rows it would have wait, drawn dormant (`on_here`). A load moves no pointer: the
patch says where a player points, and the meta controller says where the player is.

**Choosing the `Deck`.** `enter` is the panel's verb: it is run on the deck the panel looks
at, an edit of that patch, and it brings the controller there (one controller points at one
patch at a time, and mapping it elsewhere moves it, plan 55). Its player's duty stays;
moving the player brings it back. Undoing the edit does not move the controller: the
pointer is the meta controller's, the undo stack the patch's.

**The layers.** They are patch-layer rows on the deck's own registry, so:
- under SHIFT the global layer is as it was (`Bindings.dispatch`, `active`);
- a saved patch-layer row on a control they fill is shadowed while they stand, and comes
  back when they go; a control they do not fill keeps its row;
- a meta param is none of them (`nodemode.fillable`, `routing.meta_refusal`);
- they are in no `bindings`, so not in the file, the dirty dot or `routes()`; a learn takes
  their control freely (`is_invariant` does not read them), and a pair's consent (row 754)
  does not ask about them, since no one made them.

A mapping stays, whoever's: a row from any controller on one of the node's params keeps it
out of the fill.

**A modulator gives way, and comes back** (the owner, 2026-11-06, row 711): "we need to have
LFOs and audio routes be allowed to be overwritten for node mode, as long as they come back when
you disengage node mode." So a route from an LFO, an envelope, an analyzer lane, the sequencer or
a modifier does not keep its param from filling, and while a desk here holds that param
(`holding`) the route does not run: the knob is the param. `Router` leaves it out of its plan;
nothing edits the saved route, so a leave, an undo, a re-point or a load is the route back, and
the file holds what it held. A desk that does not act here holds nothing, so the modulators run:
one on the other `Deck`, or one that is not plugged in. SHIFT does not let go: a held key is no
reason for the look to jump. A branch to keep them is future work ("not important enough yet").

**A pad (N2)** is the same road: one fill, one set of rests, one cable kind. Its entry says
"gamepad", and its rows are for the player's first pad. What differs is what a row is, since a
stick has no ring to catch and a pad's rows are routes: each is a `push` about the base at
`PAD_DEPTH`, with the pad's own feel, so a stick at rest moves nothing and the look comes back on
release (NQ5). `Router` runs them while the pad is on this `Deck` (`routed`), and that is also how
the camera job stands down (`Router.claimed`) and a Joy-Con's stick stays heard
(`PadDevice.quiet_stick`). Its freedoms are its axes, then its natural pairs (plan 56); a lone
button has no lane for a route to read, so it fills nothing. A control an enabled row reads, or
gates on, or a modifier reads, or one the model's own layout holds (`routing.layout_of`), is no
freedom: node mode takes no button that does something (NQ6), and it needs no hold on any. Desks
fill first and pads in list order, each leaving what an earlier one filled, so a pad pointed second
never changes a desk's map. **Whose pad:** the player's first that is connected, else their first
listed (`is_first`), as the pad window picks. **A nap changes no map:** a pad asleep is filled as
the last model it read (`DeviceRegistry.pad_model`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import nodemode
from .routing import Binding, layout_of
from .routing_sources import PAIR_SCHEME, pair_address, pair_poles, qualified

KIND = "midi"                  # what a saved entry's `controller` says of a desk
PAD_KIND = "gamepad"           # ...and of a pad (`PadDevice.kind`)
# a pad row's depth: a stick's whole throw is half the param's range either way, a trigger's
# all of it. Not `learn.PUSH_DEPTH`, a route's start for a depth knob to take up: these have no
# knob, so the stick must reach the param (row 820)
PAD_DEPTH = 1.0
PAD_SCHEMES = ("axis", "pad", "hat", PAIR_SCHEME)   # what can hold a freedom of a pad's

NOT_FIRST = "{role} is player {player}'s second desk: a patch points at a player's first"
NOT_FIRST_PAD = ("{role} is not player {player}'s pad in hand: a patch points at a player's "
                 "first connected")
NO_SHAPE = "{role} has no known knobs or faders to fill"


def _address(source: str, qualifier: str) -> str:
    """A bare source, as this desk's rows spell it."""
    scheme, _, rest = source.partition(":")
    return f"{qualified(scheme, qualifier)}:{rest}"


def same_control(a: Binding | str, b: Binding) -> bool:
    """Are these one physical control of one desk? Their qualifiers have been settled by
    the caller (`Bindings.serves`): a first desk's row may spell its own role or none."""
    bare = a if isinstance(a, str) else a.bare
    return Binding(bare, "").overlaps(Binding(b.bare, ""))


def profile_of(devices, role: str):
    """The MIDI profile module of the desk `role`, None for a role with none. `midi.PROFILES`,
    asked for here because `midi` (and mido) is imported only once a desk opens."""
    from .midi import PROFILES
    return PROFILES.get(getattr(devices.get(role), "profile", ""))


def freedoms_of(profile) -> list[tuple[str, ...]]:
    """What a MIDI profile's desk has to fill: none for a desk of unknown shape."""
    fn = getattr(profile, "degrees_of_freedom", None)
    return fn() if fn is not None else []


def pad_freedoms(model) -> list[tuple[str, ...]]:
    """What a pad has to fill: `gamepad.degrees_of_freedom`, less a lone discrete control,
    which has no lane for a route to read. (`gamepad` is imported once a pad is asked of.)"""
    from . import gamepad
    return [f for f in gamepad.degrees_of_freedom(model)
            if len(f) == 2 or f[0].startswith("axis:")]


def _reads(bare: str) -> tuple[str, ...]:
    """The sources a row's unqualified `bare` holds of a pad, as `degrees_of_freedom` spells
    them: a pair's poles; a lane by number its axis; a dial's sector both its stick's axes,
    since a stick read as a dial is off every other job (`gamepad.claims`)."""
    scheme, _, rest = bare.partition(":")
    if scheme != "axis":
        return nodemode.own_sources(bare)
    from . import gamepad
    lane = int(rest) if rest.isdigit() else (
        gamepad.LANES.index(rest) if rest in gamepad.LANES else -1)
    return tuple(f"axis:{gamepad.AXES[a]}" for a in sorted(gamepad.claims({lane})))


def _pad_source(sources: tuple[str, ...], qualifier: str) -> str:
    """The source a pad's row reads for one freedom: an axis, or a pair's lane."""
    if len(sources) == 1:
        return _address(sources[0], qualifier)
    pos, neg = (s.partition(":")[2] for s in sources)
    return pair_address(pos, neg, qualifier)


def is_desk(d) -> bool:
    """A desk that is open or could be. By what it can do, not `isinstance`: an entry switched off
    has this kind too and none of this, and a kind's class is new after a reload."""
    return d.kind == KIND and hasattr(d, "profile")


def is_pad(d) -> bool:
    """A pad that is open or could be, as `is_desk`."""
    return d.kind == PAD_KIND and hasattr(d, "quiet_stick")


@dataclass
class Row(Binding):
    """A derived row: `words`, what the on-screen desk says of it. Never saved."""

    words: str = ""


@dataclass
class _Now:
    """One desk's rows on one deck."""

    key: tuple | None = None
    node: str | None = None
    player: int = 0
    fit: nodemode.Fit = field(default_factory=nodemode.Fit)
    rows: list[Binding] = field(default_factory=list)
    serial: int = 0


@dataclass(frozen=True)
class Held:
    """A controller a patch can point: its role, its player, the node it is on here (None:
    none), and whether the desk is on this `Deck` now."""

    role: str
    player: int
    node: str | None
    on_here: bool
    fit: nodemode.Fit
    rows: tuple[Binding, ...]
    kind: str = KIND


class NodeDesk:
    """A `Deck`'s derived desk rows. It reads the deck's loadable patch, registry and
    table, and only asks the meta controller who holds what and where it is."""

    def __init__(self, deck, devices, meta):
        self.deck = deck
        self.devices = devices      # `DeviceRegistry`
        self.meta = meta            # `MetaController`: who holds what, and where it is
        self._now: dict[str, _Now] = {}
        self._asked: tuple[tuple, dict] = ((), {})    # `_cached`

    # ---- who ----

    def _desks(self) -> list:
        """The desks that are open or could be (an entry switched off is no `MidiDevice`),
        in the order that makes one first: `DeviceRegistry.midi_roles`, whose first is the
        desk the bindings were written for, so a generic box listed above the APC40 is
        not its player's first desk."""
        desks = {d.role: d for d in self.devices.devices if is_desk(d)}
        return [desks[r] for r in self.devices.midi_roles() if r in desks]

    def _pads(self) -> list:
        """The pads that are open or could be, in list order: what `first_pad_on` reads."""
        return [d for d in self.devices.devices if is_pad(d)]

    def _controllers(self) -> list:
        """Every controller a patch can reach, in the order they fill: desks, then pads."""
        return [*self._desks(), *self._pads()]

    def kind_of(self, role: str) -> str:
        """What a saved entry calls `role`'s controller."""
        d = self.devices.get(role)
        return PAD_KIND if d is not None and is_pad(d) else KIND

    def player_of(self, role: str) -> int:
        return self.meta.players.player_of(role).number

    def is_first(self, role: str) -> bool:
        """Is `role` the controller of its kind a saved entry reaches: its player's first
        desk listed, or its player's first pad connected, else first listed? The pad in hand
        wins, as `DeviceRegistry.live_adapter` draws it: an x360 listed first and unplugged
        must not hold the Joy-Con's node mode, dead, with the window drawing the Joy-Con."""
        n = self.player_of(role)
        if self.kind_of(role) == PAD_KIND:
            mine = [d for d in self._pads() if self.player_of(d.role) == n]
            first = next((d for d in mine if getattr(d.io, "on", False)), mine[0] if mine else None)
            return first is not None and first.role == role
        return next((d.role for d in self._desks() if self.player_of(d.role) == n), None) == role

    def on_here(self, role: str) -> bool:
        return self.meta.pointer(role).deck is self.deck

    def _profile(self, role: str):
        return profile_of(self.devices, role)

    # ---- the rows ----

    def _cached(self, what: str, make):
        """`make()` once until the registry's list or the section moves: both answers
        below scan (`graphview.param_ids`, `LoadedPatch._pointable`), and the panel
        asks them each frame a node is selected."""
        deck = self.deck
        key = (getattr(deck.reg, "serial", 0), id(getattr(deck.graph, "spec", None)),
               getattr(deck.table, "modifiers_serial", 0))
        if self._asked[0] != key:
            self._asked = (key, {})
        got = self._asked[1]
        if what not in got:
            got[what] = make()
        return got[what]

    def params_of(self, node: str) -> list[str]:
        """The registry ids under `node`, kept (`LoadedPatch.node_params`)."""
        return self._cached(f"params:{node}", lambda: self.deck.loaded_patch.node_params(node))

    def pointable(self, node: str) -> bool:
        """May this patch point at `node` (`LoadedPatch.pointable`)? Kept."""
        return self._cached(f"can:{node}", lambda: self.deck.loaded_patch.pointable(node))

    def away(self, b: Binding, role: str | None = None) -> bool | None:
        """Row `b` as a picture of a controller asks (`role`; None, the first desk): None
        when node mode did not derive it, else whether the controller is on the other
        `Deck`, so it acts there."""
        role = self._role(role)
        if not role or not any(x is b for x in self.rows(role)):
            return None
        return not self.on_here(role)

    def _free(self, role: str, wanted: set[str], freedoms) -> list[tuple[str, ...]]:
        """The freedoms a row here would really be reached on, by `dispatch`'s own rule:
        not a control held above the layers on any channel it can arrive on
        (`Bindings.above_layers`), and not one of this desk's patch-layer rows on the
        node's params, which stay, on every control they name (an any-channel row on the
        faders stays on all eight). The desk's other patch-layer rows give way."""
        t = self.deck.table
        kept = [b for b in t.bindings if b.enabled and b.is_midi and b.layer == "preset"
                and b.target in wanted and t.serves(role, b)]
        pool = [b for b in t.bindings if b.is_midi and b.layer is None]     # (asked ~150 times)
        out = []
        for f in freedoms:
            probe = Binding(f[0], "")
            channels = range(16) if probe.channel is None else (probe.channel,)
            if not any(same_control(f[0], b) for b in kept) and all(
                    t.above_layers(probe.kind, ch, probe.number, role, pool) is None
                    for ch in channels):
                out.append(f)
        return out

    def _kept(self, wanted: set[str]) -> list[tuple[str, str]]:
        """Any controller's enabled row on the node's params: `fill` keeps those params
        out. With no source, since `_free` has settled which freedoms are taken (a pad's
        row takes no knob, and a SHIFT layer row takes no patch-layer control)."""
        return [("", b.target) for b in self.deck.table.bindings
                if b.enabled and not b.is_sink and not b.is_modulator_route
                and b.target in wanted]

    def _pad_free(self, pad, model) -> list[tuple[str, ...]]:
        """The freedoms of `pad` nothing holds: not a control this pad's enabled row reads,
        wherever it aims (`fill`'s rule: one stick never moves two things by accident), nor one
        a row gates on or a modifier reads, which moving it would also drive, nor one the model's
        own layout holds. This table's rows, not the file's: the meta controller's buttons are
        in it too, so node mode never takes one."""
        t, q = self.deck.table, pad.qualifier
        held = set(layout_of(model).sources)
        addresses: list[str] = []
        for b in t.bindings:
            if b.enabled:
                addresses.append(b.source)
                if b.when:
                    addresses.append(b.when)
        for m in t.modifiers:
            addresses.extend(a for a in m.inputs if a)
        for a in addresses:
            probe = Binding(a, "")
            if probe.scheme in PAD_SCHEMES and t.pad_serves(q, probe):
                held.update(_reads(probe.bare))
        return [f for f in pad_freedoms(model) if not held.intersection(f)]

    def _filled_before(self, role: str) -> tuple[str, ...]:
        """The params the controllers that fill ahead of `role` hold, wherever they are: a
        `Deck` a player moves to must not change the map a file says."""
        out: list[str] = []
        for d in self._controllers():
            if d.role == role:
                break
            out.extend(b.target for b in self._follow(d.role).rows)
        return tuple(out)

    def _pad_rows(self, pad, fit: nodemode.Fit, had: list[Binding]) -> list[Binding]:
        """The rows of `fit` on a pad: pushes, each kept while it says the same."""
        reg = self.deck.reg
        keep = {(b.source, b.target): b for b in had}
        out: list[Binding] = []
        for slot in fit.slots:
            source = _pad_source(slot.sources, pad.qualifier)
            b = keep.get((source, slot.param))
            out.append(b if b is not None else Row(source, slot.param, "push", PAD_DEPTH,
                                                   words=reg[slot.param].label or slot.param))
        return out

    def _follow(self, role: str) -> _Now:
        """`role`'s rows, derived again only when what they are made of moved."""
        now = self._now.setdefault(role, _Now())
        deck, t = self.deck, self.deck.table
        player = self.player_of(role)
        kind = self.kind_of(role)
        node = deck.loaded_patch.node_mode.of(player, kind) if self.is_first(role) else None
        dev = self.devices.get(role)
        shape: tuple = ()
        before: tuple[str, ...] = ()
        pad = kind == PAD_KIND
        model = self.devices.pad_model(dev) if pad else None
        if pad and node is not None:
            before = self._filled_before(role)
            shape = (getattr(model, "id", ""), dev.qualifier,
                     getattr(t, "primaries", {}).get("pad", ""), before,
                     tuple(b.when for b in t.bindings if b.when),
                     tuple(a for m in t.modifiers for a in m.inputs))
        key = (node, player, getattr(deck.reg, "serial", 0), id(t.bindings), len(t.bindings),
               t.rows_serial, t.desk_serial, getattr(t, "redraw_serial", 0),
               getattr(dev, "profile", ""), t.is_primary(role), shape)
        if key == now.key:
            return now
        now.key, now.node, now.player = key, node, player
        fit, rows = nodemode.Fit(), []
        if node is not None and pad:
            params = nodemode.fillable(deck.reg, self.params_of(node), routed=True)
            wanted = set(params)
            fit = nodemode.fill(params, self._pad_free(dev, model),
                                [*self._kept(wanted), *(("", p) for p in before)])
            rows = self._pad_rows(dev, fit, now.rows)
        elif node is not None:
            freedoms = freedoms_of(self._profile(role))
            params = nodemode.fillable(deck.reg, self.params_of(node))
            wanted = set(params)
            fit = nodemode.fill(params, self._free(role, wanted, freedoms), self._kept(wanted))
            rows = self._rows_of(role, fit, now.rows)
        if [(b.source, b.target) for b in rows] != [(b.source, b.target) for b in now.rows]:
            now.serial += 1
        now.fit, now.rows = fit, rows
        return now

    def _rows_of(self, role: str, fit: nodemode.Fit, had: list[Binding]) -> list[Binding]:
        """The rows of `fit`, keeping each one that says the same (its catch, its ring)."""
        t, reg = self.deck.table, self.deck.reg
        q = "" if t.is_primary(role) else role
        keep = {(b.source, b.target): b for b in had}
        profile = self._profile(role)
        out = []
        for slot in fit.slots:
            source = _address(slot.sources[0], q)
            b = keep.get((source, slot.param))
            if b is None:
                b = Row(source, slot.param, "abs", layer="preset",
                        words=reg[slot.param].label or slot.param)
                b.feedback_from(profile)
            out.append(b)
        return out

    def _role(self, role: str | None) -> str:
        return role or self.deck.table.primary_role()

    def rows(self, role: str | None = None) -> list[Binding]:
        role = self._role(role)
        return self._follow(role).rows if role else []

    def serial(self, role: str | None = None) -> int:
        role = self._role(role)
        return self._follow(role).serial if role else 0

    def holding(self) -> frozenset[str]:
        """The params a controller acting on this `Deck` holds now: filled, its rows the ones
        it reaches. Read each frame by `Router._modgraph_key`."""
        if not self.deck.loaded_patch.node_mode:
            return frozenset()
        out: set[str] = set()
        for d in self._controllers():
            if self.is_first(d.role) and self.on_here(d.role) and getattr(d.io, "on", False):
                out.update(b.target for b in self._follow(d.role).rows)
        return frozenset(out)

    def routed(self) -> list[Binding]:
        """The rows `Router` runs, read each frame: those of each pad on this `Deck`. A pad on
        the other runs nothing here, though its lanes are the shared half's and this deck
        could read them: no patch reaches another. One asleep stays, its lanes off, as a
        saved route on it does."""
        if not self.deck.loaded_patch.node_mode:
            return []
        out: list[Binding] = []
        for d in self._pads():
            if self.is_first(d.role) and self.on_here(d.role):
                out.extend(self._follow(d.role).rows)
        return out

    def under(self, b: Binding) -> bool:
        """Is saved row `b` shadowed by a row of node mode now (a patch-layer row on a
        control they fill)? It does not act until they go."""
        if not b.is_midi or b.layer != "preset":
            return False
        role = self.deck.table.role_of(b) or None
        rows = self.rows(role)
        if not rows:
            return False
        # `Bindings.dispatch`'s rule, for each control the row names: an any-channel row
        # on the eight faders still fires from a fader node mode has not filled
        controls = getattr(self._profile(self._role(role)), "controls", None)
        names = [c.source for c in controls(b.bare)] if controls is not None else []

        def taken(source: str) -> bool:
            probe = Binding(source, "")
            if probe.kind is None:
                return False
            if probe.channel is None:
                return any(x.kind == probe.kind and x.number == probe.number
                           and x.channel is None for x in rows)
            return any(x.matches(probe.kind, probe.channel, probe.number) for x in rows)
        return all(taken(s) for s in names or [b.bare])

    def held(self) -> list[Held]:
        """Every controller this patch can point, desks and then pads, each in list order: a
        player's first of each kind."""
        out = []
        for d in self._controllers():
            if self.is_first(d.role):
                now = self._follow(d.role)
                out.append(Held(d.role, now.player, now.node, self.on_here(d.role), now.fit,
                                tuple(now.rows), self.kind_of(d.role)))
        return out

    # ---- the panel's verbs: edits of this deck's patch ----

    def refusal(self, role: str, node: str | None) -> str | None:
        """Why controller `role` may not enter node mode on `node`, or None."""
        pad = self.kind_of(role) == PAD_KIND
        if not self.is_first(role):
            return (NOT_FIRST_PAD if pad else NOT_FIRST).format(role=role, player=self.player_of(role))
        if not pad and not freedoms_of(self._profile(role)):
            return NO_SHAPE.format(role=role)
        return nodemode.enter_refusal(self.deck.reg, node, self.params_of(node) if node else (),
                                      routed=pad)

    def enter(self, role: str, node: str | None) -> str | None:
        """Controller `role` on `node` of this deck's patch: one undo step of it, the dot
        lit, and it is brought here. Another node just switches. Why not, in words."""
        why = self.refusal(role, node)
        if why is None:
            why = self.deck.loaded_patch.point_node_mode(self.player_of(role), self.kind_of(role), node)
        if why is None:
            self.meta.point(role, self.deck)
        return why

    def leave(self, role: str) -> None:
        """Controller `role` off its node here, an edit too. It stays on this `Deck`."""
        self.deck.loaded_patch.leave_node_mode(self.player_of(role), self.kind_of(role))

    def control_word(self, role: str, b: Binding) -> str:
        """What a person calls row `b`'s control: "K3", "L2", "↑/↓"."""
        dev = self.devices.get(role)
        if dev is not None and is_pad(dev):
            from . import gamepad
            scheme, _, rest = b.bare.partition(":")
            poles = pair_poles(rest) if scheme == PAIR_SCHEME else None
            sources = [p.source for p in poles] if poles else [b.bare]
            model = self.devices.pad_model(dev)
            return "/".join(gamepad.models.glyph(model, s.partition(":")[2],
                                                 gamepad.glyph(s) or s) for s in sources)
        glyph = getattr(self._profile(role), "glyph", None)
        return (glyph(b.bare) if glyph is not None else None) or b.describe()

    def key(self) -> tuple[Any, ...]:
        """What a drawing of these rows is made of, for `graphview.key`."""
        return (self.holding(), *((h.role, h.player, h.node, h.on_here,
                                   tuple((b.source, b.target) for b in h.rows))
                                  for h in self.held()))


def install(meta, devices) -> None:
    """A `NodeDesk` on each of the two `Deck`s' tables (`app.main`)."""
    for deck in meta.decks:
        deck.table.node_desk = NodeDesk(deck, devices, meta)
