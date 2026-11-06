"""Node mode's saved form (plan 53 NM0, plan 57): a controller pointed at one
node of a loadable patch, its degrees of freedom filled by that node's params.

The owner, 2026-11-04: node mode cables are "a special type of cable", drawn and
labelled, and "should save as part of the loadable patch. In doing so, when you open that
loadable patch up again, if you choose a different thing for node mode, it should just
switch. Whether or not you're in node mode and which node you are pointing to
with node mode, it's just application state. It should just go in the loadable patch."

**What is saved** (`KEY`, written only when something points; a patch with none
saves as it did, byte for byte)::

    "node_mode": [{"player": 2, "controller": "gamepad", "node": "render:acid"}]

`player` is 1 to 4. `controller` is a device kind (`devices.Base.kind`: "midi",
"gamepad", "hands"), never a device: it reads as a row's address does, the
player's first controller of that kind (`devices.qualifiers_of`). It is there
because every controller nobody has registered is player 1's (`players`), so
"player 1, this node" alone would point the desk, the pad and the hands at once.
One entry per (player, controller): one controller points at one node, and
choosing another just switches (`NodeMode.pointing`).

**What is not saved: the rows.** They come from `fill`, given the node's params
(`fillable`), the controller's degrees of freedom and the rows the patch already
has. A row's source says a controller's shape, and a patch names no device: the
same file on a Joy-Con fills what a Joy-Con has. N1 and N2 turn a `Fit` into rows
and draw them as `graphview.NODE_MODE` cables.

**The rule of the fill** (the owner, 2026-11-04): a mapping already on the node's
params stays, the rest fill what is left, and there is no paging: a param with no
freedom left is `Fit.over`, listed, as a node with too many params. A pair of
discrete controls is one degree of freedom (`gamepad.degrees_of_freedom`). You
enter with a node selected and a node with no params cannot be entered
(`enter_refusal`). A meta param is no row of a loadable patch's, in node mode as anywhere
(`routing.meta_refusal`, row 743).

**Whose it is.** The loadable patch's: `loadable.LoadedPatch.node_mode`, one per `Deck`, in its
dirty dot and in a load's undo step (`library.Marks`). Who is on which `Deck` is the
meta controller's: a cable naming a player on another `Deck` is drawn dormant, and
the file does not change.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from .params import Kind
from .players import NUMBERS
from .routing import meta_refusal
from .routing_sources import PAIR_SCHEME, pair_poles

KEY = "node_mode"

BAD_ENTRY = "node mode: an entry that is not a player, a controller and a node, ignored"
TWICE = "node mode: player {player}'s {controller} points twice, kept {node}"
NODE_GONE = "node mode: {node} is not in the preset, left out"

NO_NODE = "select a node first"
NO_PARAMS = "{node} has no params to point at"
NO_FILLABLE = "{node} has no param a controller can fill"
ONLY_META = "{node}'s params are the meta controller's: no row of a preset moves them"
TOO_MANY = "{node} has too many params for this controller: {params}"


@dataclass(frozen=True)
class Pointing:
    """One saved entry: player `player`'s `controller` is on node `node`."""

    player: int
    controller: str
    node: str

    def to_json(self) -> dict:
        return {"player": self.player, "controller": self.controller, "node": self.node}


def _entry(raw: Any) -> Pointing | None:
    """A file's entry, or None for what is not one. A kind this build does not
    have is kept: it is dormant, as a row on a device this Mac lacks is."""
    if not isinstance(raw, dict):
        return None
    player, controller, node = raw.get("player"), raw.get("controller"), raw.get("node")
    if type(player) is not int or player not in NUMBERS:
        return None
    if not (isinstance(controller, str) and controller and isinstance(node, str) and node):
        return None
    return Pointing(player, controller, node)


@dataclass(frozen=True)
class NodeMode:
    """What a patch points where. Immutable, so an undo mark keeps one by
    reference (as `graph.BusCuts`), and in one order whatever made it, so the
    dirty dot and the file do not depend on the order things were pointed."""

    entries: tuple[Pointing, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.entries)

    def of(self, player: int, controller: str) -> str | None:
        """The node `controller` of `player` points at, None when it is on none."""
        return next((e.node for e in self.entries
                     if (e.player, e.controller) == (player, controller)), None)

    def pointing(self, player: int, controller: str, node: str) -> NodeMode:
        """The same with this controller on `node`: another choice just switches."""
        return self.leaving(player, controller)._with(Pointing(player, controller, node))

    def leaving(self, player: int, controller: str) -> NodeMode:
        return NodeMode(tuple(e for e in self.entries
                              if (e.player, e.controller) != (player, controller)))

    def kept_in(self, nodes: Iterable[str]) -> NodeMode:
        """Only the entries on `nodes`; `self` itself when that is all of them."""
        nodes = set(nodes)
        left = tuple(e for e in self.entries if e.node in nodes)
        return self if len(left) == len(self.entries) else NodeMode(left)

    def _with(self, entry: Pointing) -> NodeMode:
        return NodeMode(tuple(sorted((*self.entries, entry),
                                     key=lambda e: (e.player, e.controller))))

    def to_json(self) -> list[dict]:
        return [e.to_json() for e in self.entries]

    @classmethod
    def read(cls, raw: Any) -> tuple[NodeMode, list[str]]:
        """A file's value → (the entries, the notes). What cannot be read is said
        and left out (a hand-edited file never stops a patch from opening); a
        second entry for one controller loses to the first."""
        got = cls()
        notes: list[str] = []
        bad = raw is not None and not isinstance(raw, list)
        for item in raw if isinstance(raw, list) else ():
            entry = _entry(item)
            if entry is None:
                bad = True
            elif got.of(entry.player, entry.controller) is not None:
                notes.append(TWICE.format(player=entry.player, controller=entry.controller,
                                          node=got.of(entry.player, entry.controller)))
            else:
                got = got._with(entry)
        return got, ([BAD_ENTRY] if bad else []) + notes


@dataclass(frozen=True)
class Slot:
    """One derived row: the sources of one degree of freedom, and its param."""

    sources: tuple[str, ...]
    param: str


@dataclass(frozen=True)
class Fit:
    """A node on a controller: `slots` the rows to derive, `kept` the params a
    row already has, `over` the params no freedom is left for."""

    slots: tuple[Slot, ...] = ()
    kept: tuple[str, ...] = ()
    over: tuple[str, ...] = ()

    def too_many(self, node: str) -> str | None:
        """The words for a node that does not fit, None when it does."""
        if not self.over:
            return None
        return TOO_MANY.format(node=node.removeprefix("render:"), params=", ".join(self.over))


def own_sources(source: str, qualifier: str = "") -> tuple[str, ...]:
    """The unqualified sources a row's `source` reads on the controller that
    publishes under `qualifier`, as `degrees_of_freedom` spells them; none when
    the row is another controller's, or names a pair no pad can have. A pair
    (plan 56) is its two poles."""
    scheme, _, rest = source.partition(":")
    bare, _, who = scheme.partition("@")
    if who != qualifier:
        return ()
    if bare == PAIR_SCHEME:
        return tuple(pole.source for pole in pair_poles(rest) or ())
    return (f"{bare}:{rest}",)


def fill(params: Sequence[str], freedoms: Iterable[Sequence[str]],
         rows: Iterable[tuple[str, str]] = (), qualifier: str = "") -> Fit:
    """The row map, from what the patch says and nothing saved: `params` in
    order onto `freedoms` in order. `rows` is the rows that stand, as (source,
    target). One on a param of the node stays, whoever's it is. Any this
    controller reads (`qualifier`) takes its freedom, wherever it aims, so one
    stick never moves two things by accident. A caller whose rows are shadowed
    while it points (a desk's layers, N1) leaves those out, keeping the ones on
    the node. Pure, so one file on one controller is always one map."""
    rows = list(rows)
    wanted = set(params)
    kept = {target for _, target in rows if target in wanted}
    taken = {part for source, _ in rows for part in own_sources(source, qualifier)}
    free = [tuple(f) for f in freedoms if not taken.intersection(f)]
    todo = [p for p in params if p not in kept]
    slots = tuple(Slot(f, p) for f, p in zip(free, todo, strict=False))
    return Fit(slots, tuple(p for p in params if p in kept), tuple(todo[len(slots):]))


def fillable(reg: Any, ids: Iterable[str], *, routed: bool = False) -> list[str]:
    """Of a node's param ids (`ui_graph.node_params`), those a controller may
    fill, in order: continuous, no alias, no meta param. `routed`: only those a
    route can move (a pad's rows are routes, plan 53 §3), which a desk's are not."""
    out = []
    for pid in ids:
        p = reg.get(pid)
        if p is None or p.alias or p.kind is not Kind.CONTINUOUS or meta_refusal(pid) is not None:
            continue
        if routed and not p.modulatable:
            continue
        out.append(pid)
    return out


def enter_refusal(reg: Any, node: str | None, ids: Iterable[str],
                  *, routed: bool = False) -> str | None:
    """Why a controller may not enter node mode on `node` (the panel's selection,
    None for nothing), or None when it may. A node that does not fit may: what
    fits fills, and `Fit.too_many` lists the rest."""
    if not node:
        return NO_NODE
    ids = list(ids)
    if fillable(reg, ids, routed=routed):
        return None
    word = node.removeprefix("render:")
    if not ids:
        return NO_PARAMS.format(node=word)
    if all(meta_refusal(pid) is not None for pid in ids):
        return ONLY_META.format(node=word)
    return NO_FILLABLE.format(node=word)
