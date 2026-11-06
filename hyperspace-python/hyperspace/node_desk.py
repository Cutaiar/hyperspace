"""Node mode on a desk (plan 53 N1a): the rows `nodemode` says, per player and per `Deck`.

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
out of the fill. A modulator's route (an LFO, an analyzer lane) is no mapping: the knob
sets the base under it, as any knob on a performed param does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import nodemode
from .devices import MidiDevice
from .routing import Binding
from .routing_sources import BUILTIN_LANES, DECK_SCHEMES, qualified

KIND = "midi"                  # what a saved entry's `controller` says of a desk
# the schemes that are no controller's: what a route from one modulates is still free
MODULATORS = frozenset(BUILTIN_LANES) | DECK_SCHEMES

NOT_FIRST = "{role} is player {player}'s second desk: a patch points at a player's first"
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
    """A desk a patch can point: its role, its player, the node it is on here (None:
    none), and whether the desk is on this `Deck` now."""

    role: str
    player: int
    node: str | None
    on_here: bool
    fit: nodemode.Fit
    rows: tuple[Binding, ...]


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

    def _desks(self) -> list[MidiDevice]:
        """The desks that are open or could be (an entry switched off is no `MidiDevice`),
        in the order that makes one first: `DeviceRegistry.midi_roles`, whose first is the
        desk the bindings were written for, so a generic box listed above the APC40 is
        not its player's first desk."""
        desks = {d.role: d for d in self.devices.devices if isinstance(d, MidiDevice)}
        return [desks[r] for r in self.devices.midi_roles() if r in desks]

    def player_of(self, role: str) -> int:
        return self.meta.players.player_of(role).number

    def is_first(self, role: str) -> bool:
        """Is `role` its player's first desk listed, the one a saved entry reaches?"""
        n = self.player_of(role)
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

    def away(self, b: Binding) -> bool | None:
        """Row `b` as the on-screen desk asks (the first desk's): None when node mode did
        not derive it, else whether the desk is on the other `Deck`, so it acts there."""
        role = self._role(None)
        if not role or not any(x is b for x in self.rows(role)):
            return None
        return not self.on_here(role)

    def _standing(self, role: str, wanted: set[str], freedoms) -> list[tuple[str, str]]:
        """The rows `fill` is told of: any controller's on the node's params, and this
        desk's invariant ones, which never give way. This desk's other rows are
        shadowed where the fill lands, so they are left out (`nodemode.fill`). A desk's
        own row is spelled as the freedom it overlaps (`cc:0:16` is on `cc:*:16`)."""
        t = self.deck.table
        q = "" if t.is_primary(role) else role
        out = []
        for b in t.bindings:
            if not b.enabled or b.is_sink or b.scheme in MODULATORS:
                continue
            mine = b.is_midi and t.serves(role, b)
            if b.target not in wanted and not (mine and b.layer is None):
                continue
            spelled = b.source
            if mine:
                spelled = next((_address(f[0], q) for f in freedoms if same_control(f[0], b)),
                               b.source)
            out.append((spelled, b.target))
        return out

    def _follow(self, role: str) -> _Now:
        """`role`'s rows, derived again only when what they are made of moved."""
        now = self._now.setdefault(role, _Now())
        deck, t = self.deck, self.deck.table
        player = self.player_of(role)
        node = deck.loaded_patch.node_mode.of(player, KIND) if self.is_first(role) else None
        key = (node, player, getattr(deck.reg, "serial", 0), id(t.bindings), len(t.bindings),
               t.rows_serial, t.desk_serial, getattr(t, "redraw_serial", 0),
               getattr(self.devices.get(role), "profile", ""), t.is_primary(role))
        if key == now.key:
            return now
        now.key, now.node, now.player = key, node, player
        fit, rows = nodemode.Fit(), []
        if node is not None:
            freedoms = freedoms_of(self._profile(role))
            params = nodemode.fillable(deck.reg, self.params_of(node))
            fit = nodemode.fill(params, freedoms, self._standing(role, set(params), freedoms),
                                "" if t.is_primary(role) else role)
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
                b = Binding(source, slot.param, "abs", layer="preset")
                b.feedback_from(profile)
                b.words = reg[slot.param].label or slot.param     # the on-screen desk's
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
            if probe.channel is None:
                return any(x.kind == probe.kind and x.number == probe.number
                           and x.channel is None for x in rows)
            return any(x.matches(probe.kind, probe.channel, probe.number) for x in rows)
        return all(taken(s) for s in names or [b.bare])

    def held(self) -> list[Held]:
        """Every desk this patch can point, in list order: a player's first of each."""
        out = []
        for d in self._desks():
            if self.is_first(d.role):
                now = self._follow(d.role)
                out.append(Held(d.role, now.player, now.node, self.on_here(d.role), now.fit,
                                tuple(now.rows)))
        return out

    # ---- the panel's verbs: edits of this deck's patch ----

    def refusal(self, role: str, node: str | None) -> str | None:
        """Why desk `role` may not enter node mode on `node`, or None."""
        if not self.is_first(role):
            return NOT_FIRST.format(role=role, player=self.player_of(role))
        if not freedoms_of(self._profile(role)):
            return NO_SHAPE.format(role=role)
        return nodemode.enter_refusal(self.deck.reg, node, self.params_of(node) if node else ())

    def enter(self, role: str, node: str | None) -> str | None:
        """Desk `role` on `node` of this deck's patch: one undo step of it, the dot lit,
        and the desk is brought here. Another node just switches. Why not, in words."""
        why = self.refusal(role, node)
        if why is None:
            why = self.deck.loaded_patch.point_node_mode(self.player_of(role), KIND, node)
        if why is None:
            self.meta.point(role, self.deck)
        return why

    def leave(self, role: str) -> None:
        """Desk `role` off its node here, an edit too. It stays on this `Deck`."""
        self.deck.loaded_patch.leave_node_mode(self.player_of(role), KIND)

    def control_word(self, role: str, b: Binding) -> str:
        """What a person calls row `b`'s control: "K3"."""
        glyph = getattr(self._profile(role), "glyph", None)
        return (glyph(b.bare) if glyph is not None else None) or b.describe()

    def key(self) -> tuple[Any, ...]:
        """What a drawing of these rows is made of, for `graphview.key`."""
        return tuple((h.role, h.player, h.node, h.on_here,
                      tuple((b.source, b.target) for b in h.rows)) for h in self.held())


def install(meta, devices) -> None:
    """A `NodeDesk` on each of the two `Deck`s' tables (`app.main`)."""
    for deck in meta.decks:
        deck.table.node_desk = NodeDesk(deck, devices, meta)
