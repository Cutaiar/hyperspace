"""Undo — one step per gesture, whatever wrote it (plan 15 WP1, decision 26).

Nothing tells this module *which* parameter was written; a counter says that
something was (`reg.writes`, writes.py), and a frame it has not moved in costs
a comparison (`Undo._still`). Once a frame with a write
`Undo.tick` compares a cheap **fingerprint** of what the user sets — the
*base* of every watched param, the table's performer rows, the desk's
patch layer and the macros — with last frame's. A change opens a step
that holds the state as it was; the step stays open while changes keep
coming and closes after `SETTLE_S` of quiet. So one slider drag, one knob
turn on the desk, one typed value or one toggle is one step, whatever
wrote it (the panel, a key row, a MIDI row, the mouse).

A performer makes no step: a hand, a band or an LFO writes an *offset*
(`Router.modulate`), not the base, and the fingerprint reads bases. Two write
the base, each keeping its own one step open (`Undo.keep_open`): a `turn` row
(plan 51 O2), one step per clutch closure, and the base chase (plan 52). The
frame a performer takes a param, and the frame it lets go, the base can
move in its last bits (the norm round trip in `Param.modulate` /
`Param.apply`), so two fingerprints are *the same* when every float pair
is within `REL_TOL` / `ABS_TOL`.

A **replacing action** — a loadable patch or show load, a Learn landing, an
Unbind, a route or macro delete, Replace in the Replace / Keep prompt —
calls `push(label)` *before* it changes anything: the step is then named
by the caller and, with `load=True`, carries "what is loaded" (`marks`),
so undoing a load also puts the library's names and clean references
back. A site that forgets to push is still undone: the watcher makes its
step, with a plain label and without the marks.

In the control model (ARCHITECTURE §3) this is a **scene-setter**. A
restore writes bases through `reg.restore` (which ends in `Param.set`)
and replaces table parts through the table's own calls (`set_routes`,
`set_desk(load=False)`, `set_macros`), and it puts back only what
differs: undoing one slider sets one param. It never calls
`Param.modulate`, never writes an offset and never writes a file.

What is watched (`watched`): a param that is persisted, not an alias, not
a trigger, and not in `EXCLUDED_GROUPS` (the clock: a tap burst rewrites
`tempo.bpm` on every tap, slower than the settle time). The integrated
angles (`rot.phase.*`), selections, the panel's own state, transport and
the meta controller's output settings are all `persist=False`.

**Three stacks** (plan 44 D5b, the owner's design, 2026-11-04): one `Undo` per
`Deck`, scoped to its loadable patch (`only`: `deck.in_patch`), and one for the meta
controller over `MetaRegistry` and `MetaTable` (`install_meta`,
`deck.meta_stack`). The second watches the meta params, whose tuning is done before a performance and
not during one, the meta controller's rows of the table (keys, pad,
invariant and global-layer MIDI rows, sinks) and who holds what (`moves`:
`deck.MetaPlayers`, row 740). Those rows live in `bindings.json` and the players in
`players.json` the moment they change, so their restores (`MetaTable.set_rows`,
`MetaController.put_players`) write those files: the two writes a restore makes.

**⌘Z goes by where you are** (`here`): the panel's `Deck`, except with the mouse
in a meta section or on a meta param (`where`), which takes the meta stack. Never the newest of all stacks: a
⌘Z meant for a knob on one deck must not take back an analyzer tweak from an hour
ago, and never the panel's focus, which says nothing of where you are an hour on.
Pressing it never crosses over: a stack with nothing says so. On the meta stack the
player screen (`BOARD`) answers for a player's moves and every other place for the
rest (`_not_its_own`, row 800).

**The latch** (the owner, 2026-11-06, row 753): a stack you have just come to takes
nothing back until you change something on it. Whenever focus comes to a stack it
latches shut (`latched`); ⌘Z and ⇧⌘Z there refuse, in words, and touch no history; the
first push after that opens it, and ⌘Z then goes all the way down, older steps
included. Focus (`_focused`) is not where the mouse is: `here` follows the mouse, and
one passing over a section is no event. It moves on three acts only: the panel moving
the stack ⌘Z reaches (`install`), a ⌘Z pressed at a stack, and the person's own change
in the panel (`by_hand`, read from the panel's input and reported by a text field's own
writers, row 757), whose stack is the edited param's own, so a popup over another
section cannot mislead it. A controller's change opens the stack in focus and never
moves the focus, wherever the mouse is; a held step (`keep_open`) opens nothing. A
change out of focus opens nothing, and coming back latches it again. Two things shut the
stack ⌘Z reaches without moving focus, since what it would take back has changed under
you: the panel's deck going on or off air (`on_air`), and, with the panel on air, a load
landing on the other deck (`push_on`).

The band layout: a band added, removed or moved re-declares every
`band.*` param and is **not** a step. Each state is tagged with the shape
its `tagged` ids live on (`tag()`: the bands' names in strip order), and
a `band.*` value is put back only when the tag is the same as when the
state was taken — a strip's values never land on another band. A load
step carries the layout in its marks and puts it back first.

**A move written another way** (plan 81 follow-up, row 1018): a fractal's dive
writes camera.zoom's and camera.pan's bases every frame it runs
(`Param.follow`: a re-root, the dive rate, the settle) — the same picture, not
an edit. The watcher reads a base less what `follow` moved it (`_drift`), so
a running dive makes no step and keeps none open: two edits a second apart
are two steps. A restore puts back what the user set and keeps the follows
made since, so an undo never yanks the dive back to where it stood. A step
also holds what lives beside the camera (`beside`: the dive's framing,
`Dive.frame`), put back only when a restore writes the camera.

The modulator banks (plan 31 B: the LFOs) are not that: adding or
removing an LFO is a step, pushed by the panel's chip like a modifier's.
Each state holds every bank's ids beside the modifiers, and a restore
puts the membership back before the bases — a voice that returns is
declared afresh, then its knobs land.

Imports nothing from the package: the registry and the table arrive as
arguments and are used duck-typed (the rule lfo.py and tempo.py keep), so
any module may import this one. `install` holds the panel's `Deck`'s `Undo`,
`install_meta` the meta controller's; `push` and `push_meta` at module level
act on one each, `undo` / `redo` on the one `here` names, and all do nothing
when none is installed (every test that builds no `Undo`).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, fields, replace
from operator import attrgetter
from typing import Any
from weakref import WeakKeyDictionary, ref

SETTLE_S = 0.4        # quiet time that ends a step. Plan 18's knob slew must stay under it.
LIMIT = 100           # steps kept; the oldest goes first
ABSORB_FRAMES = 2     # frames after a restore whose changes are the restore's own
REL_TOL, ABS_TOL = 1e-9, 1e-12
EXCLUDED_GROUPS = ("tempo",)          # the clock (plan 15 fork 5)
# groups whose params are watched as part of the table, not as bases: the
# modifiers' (plan 28 N1) — adding one declares its params, and a step must
# hold the node and its params together (`table.modifiers_doc(reg)`)
TABLE_GROUPS = ("mod",)
PASSES = 3            # restore passes: a setter with side effects (scene.select) needs a second

# the row fields the fingerprint reads — every one a file would hold; the
# ROUTING page edits rows in place, so there is no serial to read instead
ROW_FIELDS = ("source", "target", "op", "value", "enabled", "scale", "when", "rest",
              "layer", "pickup", "feedback", "on", "off", "ring")
LEFT = "the analyzer's bands have changed: their strips were left"


def watched(p) -> bool:
    """Is this param's base part of the undo history: persisted, not an
    alias, not a trigger, and its group not in `EXCLUDED_GROUPS`."""
    return (p.persist and not p.alias and p.group not in EXCLUDED_GROUPS
            and p.group not in TABLE_GROUPS
            and getattr(p.kind, "value", p.kind) != "trigger")


def _same(a, b) -> bool:
    """Two base values: equal, or two floats within the tolerance (the
    round-off a performer taking or leaving a param makes)."""
    if a == b:
        return True
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):   # NaN both sides: nothing moved
            return True
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return False


def alike(a, b) -> bool:
    """Two snapshots, or two signatures holding them (dicts, tuples and
    lists, nested): the same shape and keys, every leaf `_same`. What a
    dirty dot compares with (library.py; plan 16 WP7): a base a performer
    took and gave back differs from the file's in its last bits only, and
    that is not an edit — one detent of any param is far outside it. A
    whole number in a file (`"camera.zoom": 1`) is a number like any
    other here: it compares with the float base the same way."""
    if a == b:                            # the usual case, at dict-compare cost
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(alike(v, b[k]) for k, v in a.items())
    if isinstance(a, list | tuple) and isinstance(b, list | tuple):
        return (type(a) is type(b) and len(a) == len(b)
                and all(alike(x, y) for x, y in zip(a, b, strict=True)))
    if _number(a) and _number(b):
        try:
            return _same(float(a), float(b))
        except OverflowError:             # an int no float holds: not that float
            return False
    return _same(a, b)


def _drift(p) -> float:
    """How far `Param.follow` has moved `p`'s base, normalized (0: never;
    `getattr`: a param from before a hot reload, or a stand-in)."""
    return getattr(p, "_drift", 0.0)


def _base_of(p):
    """A base as the fingerprint reads it: the base, with what `follow` moved
    it beside it when it has (`_same_own` compares the two forms)."""
    d = getattr(p, "_drift", 0.0)
    return (p.base, d) if d else p.base


def _same_own(p, a, da: float, b, db: float) -> bool:
    """Two bases of `p` with `da` and `db` of `follow` in them: the same once
    the follows are taken off (normalized, the units `follow` moves in)."""
    if da == db:
        return _same(a, b)
    if p is None:
        return False
    try:
        x, y = p._norm_of(a) - da, p._norm_of(b) - db
    except Exception:  # noqa: BLE001 — a base that will not read: not the same
        return False
    if getattr(p, "wrap", False):
        x, y = x % 1.0, y % 1.0
    return math.isclose(x, y, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def own(p, v, then: float):
    """`v`, a base of `p` taken with `then` of `follow` in it, with the follows
    made since put on: what a restore writes, so it keeps them."""
    d = _drift(p)
    if d == then:
        return v
    u = p._norm_of(v) + d - then
    u = u % 1.0 if getattr(p, "wrap", False) else min(max(u, 0.0), 1.0)
    return p._value_of_norm(u)


def _number(v) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool)


_row = attrgetter(*ROW_FIELDS)        # a row as the tuple of its fields

# the debug mode (tests/conftest.py): called with (stack, the fingerprint held, the one
# taken) whenever a tick would have skipped a fingerprint that had changed — a
# write somewhere that marks nothing. Every tick then takes its fingerprint
oracle = globals().get("oracle")


def _marking(cls) -> bool:
    """Does writing any of `ROW_FIELDS` on a row of this class mark?"""
    return getattr(cls, "_cells", frozenset()).issuperset(ROW_FIELDS)


def _rows(rows) -> tuple:
    return tuple(map(_row, rows))


def _macros(table) -> tuple:
    """The macros as the fingerprint reads them: id, label and each
    subscriber's (base, depth, from, to); a macro with neither label nor
    subscriber is left out, as `macros_doc` leaves it out."""
    out = []
    for mid, m in sorted(table.macros.items()):
        if m.label or m.subs:
            out.append((mid, m.label, tuple((s.base, s.depth, s.lo, s.hi) for s in m.subs)))
    return tuple(out)


@dataclass(frozen=True)
class State:
    """What a step puts back: the watched bases by id, copies of the
    performer rows and of the patch-layer rows, the macros' document, the
    tag as it read then, and — for a load step — the marks."""

    bases: dict[str, Any]
    routes: tuple
    desk: tuple
    macros: dict
    tag: Any = None
    marks: Any = None
    modifiers: Any = None     # the modifiers' document (plan 28 N1); None: not taken
    banks: Any = None         # each bank's ids by scheme (plan 31 B); None: not taken
    # how much of a route's offset each base held then, those that held any
    # (the base chase's ledger, plan 52), so a base goes back with its own
    trims: Any = None
    rows: tuple = ()          # the meta controller's rows (`deck.MetaRows`, plan 44 D5b)
    moves: Any = None         # who holds what and who is where (`Undo.moves`, row 740)
    # plan 81 follow-up (row 1018): how far `Param.follow` had moved each base
    # then, those it had moved; and what lives beside the camera (`beside`)
    drift: Any = None
    beside: Any = None


@dataclass
class Step:
    """One entry of a stack: its label ("" until a gesture closes), the
    state to put back, whether it carries the marks, and whether a caller
    pushed it (an action) or the watcher opened it (a gesture)."""

    label: str
    before: State
    load: bool = False
    action: bool = False
    # a step that is not a load: every group's landed name and reference
    # as of the last quiet frame before it (`marks.lands()`), for `mend`
    lands: Any = None
    then: Any = None          # `Undo.moves.then()` as the step began (row 800)


class Undo:
    """The undo and redo stacks over one registry and one table.

    `reg` iterates params (`id`, `base`, `persist`, `alias`, `group`,
    `kind`, `label`, `fmt`, `names`) and has `get(id)` and `restore({id:
    value})`. `table` has `bindings` (rows with the `ROW_FIELDS`),
    `routes()`, `desk()`, `macros`, `macros_doc()`, `set_routes(rows)`,
    `set_desk(rows, load=False)` and `set_macros(doc, reg)`. `marks` (optional) is "what is loaded", opaque here: `take()`,
    `before(mark)` (called first in a load step's restore: the layout) and
    `put(mark)` (called last: the names and references). Two more are
    optional: `lands()`, a cheap read of every group's landed name, taken
    each quiet frame, and `mend(pre, lands)`, called after the restore of
    a step that is not a load — a setter's side effect may have moved a
    name (`scene.select` adopts its scene), and `mend` puts those back. `tag` (optional)
    is a callable naming the shape the `tagged` id prefixes live on.
    `on_restore` is called after every restore's writes. `banks`
    (optional) is the modulator banks by scheme (plan 31 B: the LFOs), or
    a callable returning them: each has `doc()` (its ids) and `set(ids)`;
    a step holds their membership and a restore puts it back before the
    bases, so a voice's params exist before their values land. `only`
    (optional) narrows `watched` to the params this stack is for: a `Deck`'s
    takes those of its loadable patch (plan 44 D5b). A `table` with `rows` and
    `set_rows(rows)` (`deck.MetaRows`) has those watched too. `moves` (optional:
    `deck.MetaPlayers`, row 740) is one more part of what a step holds: `doc()` to
    compare and hold; `then()`, what a step must remember of the moment it began and
    `doc` does not hold, kept on the `Step`; `put(doc, then)` to restore it;
    `refuses(doc, then)`, the words why it may not go back now (else None, and the step
    stays where it is, as under the latch); `trouble()`, what went wrong in the last
    `put`, for the status; and `heard`, what ⌘Z last said over the board, for its line.
    `beside` (optional: `deck.DiveFrame`, row 1018) is state the camera's bases
    carry with them that no param holds: `ids`, the params it goes with; `take()`
    to hold; `continues(then, now)`, whether the follows made between two takes
    are to be kept on a restore (else bases go back as they were);
    `put(doc, kept)`, called when a restore writes any of `ids`.
    """

    only = None      # on the class: a live `Undo` from before a hot reload has it
    moves: Any = None     # …and this
    latched = False  # …and these: ⌘Z refuses here until a new push (row 753)
    called = "here"  # how the refusal names this stack ("on deck 2"; `MetaController`)
    _opens = False   # the open step began on focus: when it lands it opens the latch
    beside: Any = None    # …and these (row 1018)
    _seen: Any = None     # …and these: `reg.writes` as the last fingerprint began
    _seen_every: Any = None    # …and the registry's params, the very list it read
    _reading: Any = None
    _rowlist: Any = None  # the table's rows then, by identity; None: rows that do not mark
    _polled: Any = ()     # (index in `_watched`, param): the bases no write marks
    _quiet: Any = None    # `beside.take()` as of the last quiet frame

    def __init__(self, reg, table, *, marks=None, tag=None, tagged=("band.",),
                 on_restore=None, banks=None, only=None, called=None, moves=None,
                 beside=None):
        self.reg, self.table = reg, table
        self.moves = moves
        self.beside = beside
        if called is not None:
            self.called = called
        try:
            _watching[reg] = ref(self)
        except TypeError:                 # a stand-in registry: found only by `installed`
            pass
        self.marks, self.tag, self.tagged = marks, tag, tuple(tagged)
        self.only = only
        self.on_restore = on_restore
        self.banks = banks
        self.stack: list[Step] = []       # the undo stack, newest last
        self.redos: list[Step] = []       # the redo stack, newest last
        self.status = ""                  # what the last undo / redo did, for the footer
        self.said_at = 0.0                # the frame clock when `status` was set
        self._now = 0.0                   # the last tick's clock
        self._frame = 0                   # ticks so far
        self._open: Step | None = None    # the step still collecting changes
        self._changed_at = 0.0            # when the fingerprint last moved
        self._action_frame = -1           # the tick count when an action step was opened
        self._absorb = 0                  # frames left of a restore's own follow-ups
        self._restoring = False           # a restore is running: its own pushes are ignored
        self._every: list = []            # the registry's params as last read (`_params`)
        self._watched: list = []          # …the watched ones among them
        self._ids: tuple = ()             # …and their ids
        self._lands = self._read_lands()  # what is landed, as of the last quiet frame
        self._quiet = self._quiet_take()
        self._fp = self._fingerprint()
        self._saw()
        self._settled = self._take()

    # ---- what is watched ----

    def _tag(self):
        return self.tag() if self.tag is not None else None

    def _watches(self, p) -> bool:
        """Is `p`'s base on this stack: `watched`, and this stack's (`only`)."""
        return watched(p) and (self.only is None or self.only(p))

    def _params(self) -> list:
        """The watched params, in registry order. A band layout change and
        a shader reload re-declare params, so the registry is read every
        time — but the filter runs only when it holds other objects than
        last time (a list comparison by identity: a re-declared param is a
        new object even under an old id)."""
        every = list(self.reg)
        if every != self._every:
            self._every = every
            self._watched = [p for p in every if self._watches(p)]
            ids = tuple(p.id for p in self._watched)
            if ids != self._ids:          # (else the same tuple: `_still` asks by identity)
                self._ids = ids
            self._polled = self._unmarked(every)
        return self._watched

    def _unmarked(self, every: list) -> list:
        """The watched params whose base may move with no mark (writes.py), read
        every frame: a getter on no cell; a cell two params write (one's
        offset would be the other's base); an enum whose choices are worked
        out (a modulated base's index goes by how many there are)."""
        cells: dict = {}
        for p in every:
            c = getattr(getattr(p, "get", None), "cell", None)
            if c is not None:
                cells[c] = cells.get(c, 0) + 1
        return [(i, p) for i, p in enumerate(self._watched)
                if cells.get(getattr(getattr(p, "get", None), "cell", None), 0) != 1
                or callable(getattr(p, "choices", None))]

    def _mods(self) -> list:
        """The table's modifiers as a loadable patch holds them, their params at
        their bases (plan 28 N1); [] for a table with none or no such call."""
        doc = getattr(self.table, "modifiers_doc", None)
        return doc(self.reg) if doc is not None else []

    def _banks(self) -> dict:
        """The banks by scheme; none for an Undo built without (or from
        before plan 31 B, a hot reload re-classes and never re-inits)."""
        banks = getattr(self, "banks", None)
        banks = banks() if callable(banks) else banks
        return dict(banks or {})

    def _bank_ids(self) -> dict:
        """Each bank's membership as a loadable patch holds it: scheme → ids."""
        return {scheme: list(b.doc()) for scheme, b in self._banks().items()}

    def _table_rows(self) -> list:
        """The meta controller's rows, for a table that has them (`deck.MetaRows`);
        none for a deck's, whose `routes` and `desk` are its own."""
        return getattr(self.table, "rows", ())

    def _fingerprint(self) -> tuple:
        """(ids, bases, routes, desk, macros, tag, modifiers, banks, rows, moves) as of now — the cheap
        read `tick` makes every frame. The patch layer is read as the
        table's rows whose `layer` is "preset" (what `table.desk()`
        returns, without asking every row whether it is a MIDI row)."""
        writes = getattr(self.reg, "writes", None)
        self._reading = writes() if writes is not None else None    # before anything is read
        ps = self._params()
        table = self.table
        return (self._ids, tuple([_base_of(p) for p in ps]), _rows(table.routes()),
                _rows([b for b in table.bindings if b.layer == "preset"]),
                _macros(table), self._tag(), self._mods(), self._bank_ids(),
                _rows(self._table_rows()), self._moves_doc())

    def _saw(self) -> None:
        """The fingerprint just taken is this stack's now: what was marked by
        the time it began has been looked at."""
        self._seen, self._seen_every = self._reading, self._every
        rows = [*self.table.bindings, *self._table_rows()]
        self._rowlist = rows if all(_marking(type(b)) for b in rows) else None

    def _still(self) -> bool:
        """Is `_fp` what a fingerprint taken now would be? By what no write can
        move without saying so: no mark since it was taken, the same params
        and rows, the few bases and table parts that do not mark read and
        found equal. Never True on doubt (a registry that counts no writes, a
        row type that marks none)."""
        writes = getattr(self.reg, "writes", None)
        if writes is None or self._seen is None or self._rowlist is None or writes() != self._seen:
            return False
        fp = self._fp
        self._params()
        # other param objects, even under the same ids: a shader reload declares
        # a knob over a new value, and nothing was written
        if self._every is not self._seen_every or fp[0] is not self._ids or fp[5] != self._tag():
            return False
        bases = fp[1]
        for i, p in self._polled:
            v = _base_of(p)
            if v is not bases[i] and v != bases[i]:
                return False
        table, rows = self.table, self._table_rows()
        now = [*table.bindings, *rows]
        return (now == self._rowlist and _macros(table) == fp[4] and self._mods() == fp[6]
                and self._bank_ids() == fp[7] and self._moves_doc() == fp[9])

    def _follows_kept(self, then: State, now) -> bool:
        """Are the follows made since `then` to be kept on a restore to it
        (`beside.continues`; with no `beside`, always)? Not across a load or
        another dive: those bases go back exactly as they were."""
        beside = getattr(self, "beside", None)
        if beside is None:
            return True
        return bool(beside.continues(getattr(then, "beside", None), now))

    def _beside_take(self):
        beside = getattr(self, "beside", None)
        return beside.take() if beside is not None else None

    def _quiet_take(self):
        """`beside` and the bases it goes with (`beside.ids`: the camera's),
        each with its drift, as of this frame — what a step that begins on
        the next one holds of them. The settled state's are as old as the
        last step: a running dive has moved them since without a step, and a
        restore to them in another frame of the dive would jump."""
        beside = getattr(self, "beside", None)
        if beside is None:
            return None
        cam = {}
        for pid in beside.ids:
            p = self.reg.get(pid)
            if p is not None and self._watches(p):
                cam[pid] = (p.base, _drift(p))
        return beside.take(), cam

    def _moves_doc(self):
        return self.moves.doc() if self.moves is not None else None

    def _then(self):
        return self.moves.then() if self.moves is not None else None

    def _next_is_a_move(self, src: list[Step]) -> bool | None:
        """Is the step a press would take from `src` a player's move? None: there is no
        such step. As `_swap` chooses it, touching nothing, so a hold goes on."""
        now = self._take()
        for step in reversed(src):
            ids, parts, left = self._differs(step.before, now, tagged=True)
            if "players" in parts:
                return True
            if ids or parts or left or (step.load and self.marks is not None
                                        and not self._marks_equal(step.before.marks)):
                return False
        return None

    def _same_fp(self, a: tuple, b: tuple) -> bool:
        """Equal, or equal but for float pairs within the tolerance, and bases
        that differ only by what `Param.follow` moved them (`_base_of`)."""
        if a == b:
            return True
        if a[0] != b[0] or a[2:6] != b[2:6] or a[8:] != b[8:] or not alike(a[6:8], b[6:8]):
            return False
        ps = None
        for i, (x, y) in enumerate(zip(a[1], b[1], strict=True)):
            if x is y or _same(x, y):
                continue
            if not (isinstance(x, tuple) or isinstance(y, tuple)):
                return False
            if ps is None:
                ps = {p.id: p for p in self._watched}
            (vx, dx), (vy, dy) = (x if isinstance(x, tuple) else (x, 0.0),
                                  y if isinstance(y, tuple) else (y, 0.0))
            if not _same_own(ps.get(a[0][i]), vx, dx, vy, dy):
                return False
        return True

    def _take(self, marks: bool = False) -> State:
        """The state as it is now; `marks`: with what is loaded."""
        table = self.table
        bases = {}
        for p in self._params():
            v = p.base
            bases[p.id] = list(v) if isinstance(v, list) else v
        return State(bases, tuple(replace(b) for b in table.routes()),
                     tuple(replace(b) for b in table.desk()), table.macros_doc(),
                     self._tag(),
                     self.marks.take() if marks and self.marks is not None else None,
                     modifiers=self._mods(), banks=self._bank_ids(),
                     trims={p.id: t for p in self._params() if (t := p._trim)},
                     rows=tuple(replace(b) for b in self._table_rows()),
                     moves=self._moves_doc(),
                     drift={p.id: d for p in self._params() if (d := _drift(p))},
                     beside=self._beside_take())

    def _read_lands(self):
        lands = getattr(self.marks, "lands", None)
        return lands() if lands is not None else None

    # ---- a step a held control keeps open (plan 52, the base chase) ----

    # on a class: a live `Undo` from before a hot reload reads them
    _kept: Step | None = None     # the step no quiet closes
    _on_end = None                # what to tell the holder when it closes

    def keep_open(self, label: str, on_end=None) -> None:
        """A held control's step, its own: whatever was open closes first,
        and no quiet closes this one, so one hold is one step however still
        the hold goes. `let_close` ends it. Anything else that closes it (an
        undo, an action's push, a band reshape, `clear`) ends the hold too:
        `on_end` is called, so the held control lets go and one hold is
        never more than one step."""
        self._flush()
        self.push(label)
        self._opens = False               # a held control's writes open no latch
        self._action_frame = -1           # the next push is an action of its own
        self._kept, self._on_end = self._open, on_end

    def let_close(self) -> None:
        """The hold is over: its step closes now (taken off the stack if the
        hold moved nothing, as any empty step is). Nothing kept: nothing."""
        if self._kept is not None:
            self._flush()

    def _end_kept(self) -> None:
        on_end, self._kept, self._on_end = self._on_end, None, None
        if on_end is not None:
            on_end()

    # ---- the frame ----

    def tick(self, now: float) -> None:
        """Once a frame, after the scene-setters have written their bases."""
        self._now = now
        self._frame += 1
        fp = self._fp if self._still() else self._fingerprint()
        if fp is self._fp and oracle is not None:
            fp = self._fingerprint()
            if not self._same_fp(fp, self._fp):
                oracle(self, self._fp, fp)
        if self._observe(fp):
            return
        if self._open is None:
            self._lands = self._read_lands()
            self._quiet = self._quiet_take()
        # quiet this frame: an open step closes once the settle time has passed
        if (self._open is not None and self._open is not self._kept
                and now - self._changed_at >= SETTLE_S):
            self._close()

    def _observe(self, fp: tuple) -> bool:
        """Steps 1–3 of the tick: a reshaped registry, a restore's own
        follow-ups, a change. True when the frame is settled by it (no
        step may close on this frame's evidence)."""
        last = self._fp
        if fp is not last:
            self._saw()
        if fp[0] != last[0] or fp[5] != last[5]:
            # the watched ids or the tag changed (a band added, removed or
            # moved; a shader reloaded into another shape): not a step
            self._fp = fp
            self._close()
            return True
        if self._absorb > 0:
            self._absorb -= 1
            if not self._same_fp(fp, last):
                self._fp = fp
                self._settled = self._take()
            return True
        if fp != last:
            self._fp = fp                     # kept, so the fast path resumes
            if not self._same_fp(fp, last):
                self._changed_at = self._now
                if self._open is None:
                    self._begin(Step("", self._settled, lands=self._lands))
                    self.redos.clear()
                elif _hand and self._open is not self._kept:   # the person joins a step under way
                    self._opens = _begun_on(self) or self._opens
                return True
        return False

    def _begin(self, step: Step) -> None:
        """Open `step` on the undo stack. A gesture clears the redo stack
        at once (its caller); an action only when it closes with something
        to put back — a refused unbind or a load that fails changes
        nothing and must not cost the redo."""
        self._open = step
        step.then = self._then()
        quiet = getattr(self, "_quiet", None)
        if getattr(self, "beside", None) is not None and quiet is not None:
            # what lives beside the camera, and the camera itself, as of the
            # last quiet frame (`_quiet_take`): one frame of the dive, where a
            # restore can put them back as they were
            side, cam = quiet
            before = step.before
            bases, drift = dict(before.bases), dict(getattr(before, "drift", None) or {})
            for pid, (v, d) in cam.items():
                if pid in bases:
                    bases[pid] = list(v) if isinstance(v, list) else v
                    if d:
                        drift[pid] = d
                    else:
                        drift.pop(pid, None)
            step.before = replace(before, bases=bases, drift=drift, beside=side)
        self._opens = _begun_on(self)
        self.stack.append(step)
        del self.stack[:-LIMIT]

    def _close(self) -> None:
        """End the open step, if any: `settled` becomes the state now, a
        gesture is labelled from what differs, and a step with nothing to
        put back is taken off the stack."""
        step, self._open = self._open, None
        self._settled = now = self._take()
        if step is None:
            return
        if step is self._kept:
            self._end_kept()
        ids, parts, _left = self._differs(step.before, now, tagged=False)
        empty = self._empty(step, now, ids, parts)
        opens, self._opens = self._opens, False
        _load_closed(self, landed=not empty)
        if empty:
            self.stack[:] = [s for s in self.stack if s is not step]
            return
        if opens:
            self.latched = False
        if step.action:
            self.redos.clear()
        if not step.label:
            step.label = self._label(step.before, now, ids, parts)

    def _empty(self, step: Step, now: State, ids, parts) -> bool:
        """Has `step` nothing to put back, with `ids` and `parts` what differs?"""
        empty = not ids and not parts and step.before.tag == now.tag
        if empty and step.load and self.marks is not None:
            empty = self._marks_equal(step.before.marks)
        return empty

    def _will_land(self) -> bool:
        """Is there an open step not about to close empty (a load of the look already
        there, a load that failed, a knob brought back)?"""
        step = self._open
        if step is None:
            return False
        now = self._take()
        ids, parts, _left = self._differs(step.before, now, tagged=False)
        return not self._empty(step, now, ids, parts)

    def _will_open(self) -> bool:
        """Will the open step open the latch when it lands: begun on focus, and landing?"""
        return self._opens and self._will_land()

    def _marks_equal(self, mark) -> bool:
        try:
            equal = getattr(self.marks, "equal", None)    # marks that know what they restore
            return bool(equal(mark) if equal is not None else self.marks.take() == mark)
        except Exception:  # noqa: BLE001 — marks that will not compare are kept
            return False

    def _flush(self) -> None:
        """Bring the watcher up to date as of now — an edit this frame's
        tick has not seen opens its gesture step — and close any open
        step without waiting for the settle time."""
        self._observe(self._fingerprint())
        self._absorb = 0
        if self._open is not None:
            self._close()

    # ---- steps ----

    def push(self, label: str, *, load: bool = False) -> None:
        """A replacing action is about to change something: open its step.
        Called **before** the change. `load`: the step also carries what
        is loaded (the library's names and references; a band layout).
        A second push with no tick since is the same action from the inside
        (a show load that loads its startup loadable patch; Replace landing a held
        learn): the outer label stands. Not so a load pushed under an open
        action that is no load — nothing nests that way, so it is another
        action (a delete at the end of one frame, an F-key at the start of
        the next) and gets its own step."""
        if self._restoring:
            return
        inner = self._action_frame == self._frame and self._open is not None
        if inner and not (load and not self._open.load):
            return
        self._flush()
        # an action is pushed before it writes: the camera beside it is as it
        # is now (a quiet frame's may be from before an open step's writes)
        self._quiet = self._quiet_take()
        before = self._settled
        if load and self.marks is not None:
            before = replace(before, marks=self.marks.take())
        self._begin(Step(label, before, load=load, action=True, lands=self._read_lands()))
        self._changed_at = self._now
        self._action_frame = self._frame

    def undo(self) -> bool:
        """Take back the newest step that has something to put back.
        False: nothing to undo."""
        return self._swap(self.stack, self.redos, "undid", "nothing to undo")

    def redo(self) -> bool:
        """Put back what the last undo took. False: nothing to redo."""
        return self._swap(self.redos, self.stack, "redid", "nothing to redo")

    def _swap(self, src: list[Step], dst: list[Step], verb: str, none: str) -> bool:
        self._flush()                         # (a fresh gesture clears the redo stack)
        self._action_frame = -1
        while src:
            step = src.pop()
            now = self._take(marks=step.load)
            ids, parts, left = self._differs(step.before, now, tagged=True)
            relabel = (step.load and self.marks is not None
                       and not self._marks_equal(step.before.marks))
            if not (ids or parts or left or relabel):
                continue                      # nothing to put back: dropped
            then = getattr(step, "then", None)
            why = self.moves.refuses(step.before.moves, then) if "players" in parts else None
            if why:                           # as the latch's refusal: no history moves
                src.append(step)
                self._say(f"not {'undone' if verb == 'undid' else 'redone'}: {why}")
                return False
            dst.append(Step(step.label, now, load=step.load, action=step.action,
                            lands=self._read_lands(), then=self._then()))
            del dst[:-LIMIT]
            left = self._restore(step.before, load=step.load, lands=step.lands, then=then)
            trouble = self.moves.trouble() if "players" in parts else ""
            self._say(f"{verb} {step.label}" + (f" ({LEFT})" if left else "")
                      + (f". {trouble}" if trouble else ""))
            self._fp = self._fingerprint()
            self._saw()
            self._settled = self._take()
            self._lands = self._read_lands()
            self._quiet = self._quiet_take()
            self._absorb = ABSORB_FRAMES
            return True
        self._say(none)
        return False

    def clear(self) -> None:
        """Forget every step; the state now is the settled one."""
        _load_closed(self, landed=self._will_land())
        self.stack.clear()
        self.redos.clear()
        self._open, self._absorb, self._action_frame = None, 0, -1
        self._opens = False               # (the latch stays as it was: a clear is no push)
        if self._kept is not None:
            self._end_kept()
        self._fp = self._fingerprint()
        self._saw()
        self._settled = self._take()

    def _say(self, text: str) -> None:
        self.status, self.said_at = text, self._now

    # ---- comparing and restoring ----

    def _is_tagged(self, pid: str) -> bool:
        return pid.startswith(self.tagged) if self.tagged else False

    def _differs(self, then: State, now: State, *,
                 tagged: bool) -> tuple[list[str], list[str], bool]:
        """(ids, table parts, left): the ids both states have whose bases
        differ, the table parts that differ ("routes", "desk", "macros"),
        and — with `tagged` — whether ids under a tagged prefix were left
        out because the two states are on different tags."""
        apart = then.tag != now.tag
        ids, left = [], False
        dt, dn = getattr(then, "drift", None) or {}, getattr(now, "drift", None) or {}
        kept = self._follows_kept(then, getattr(now, "beside", None))
        for pid, v in then.bases.items():
            if pid not in now.bases:
                continue
            a, b = dt.get(pid, 0.0), dn.get(pid, 0.0)
            if (_same(v, now.bases[pid]) if a == b or not kept
                    else _same_own(self.reg.get(pid), v, a, now.bases[pid], b)):
                continue
            if apart and self._is_tagged(pid):
                left = left or tagged
                continue
            ids.append(pid)
        parts = [name for name, a, b in (("routes", _rows(then.routes), _rows(now.routes)),
                                         ("desk", _rows(then.desk), _rows(now.desk)),
                                         ("macros", then.macros, now.macros),
                                         ("rows", _rows(then.rows), _rows(now.rows))) if a != b]
        if not alike(then.modifiers or [], now.modifiers or []):
            parts.append("modifiers")
        # (`getattr`: a state from before a hot reload has no such field)
        if getattr(then, "moves", None) is not None and then.moves != now.moves:
            parts.append("players")
        if then.banks is not None and now.banks is not None:
            banks = self._banks()
            parts += [getattr(banks.get(scheme), "KEY", "") or scheme
                      for scheme, ids in then.banks.items() if now.banks.get(scheme) != ids]
        return ids, parts, left

    @staticmethod
    def _rows_for(want: tuple, have: list) -> list:
        """The rows to hand a table call: the live row where one with the
        same fields is still in the table (its runtime state — a fader's
        catch — stays), else a copy of the state's with its runtime fields
        (the row type's `_RUNTIME`: catch, last reading, last feedback) back
        at their defaults — a row that was gone must pick up afresh."""
        pool: dict[tuple, list] = {}
        for b in have:
            pool.setdefault(_row(b), []).append(b)
        out = []
        for b in want:
            live = pool.get(_row(b))
            if live:
                out.append(live.pop(0))
                continue
            runtime = getattr(type(b), "_RUNTIME", ())
            out.append(replace(b, **{f.name: f.default for f in fields(b)
                                     if f.name in runtime}))
        return out

    def _restore(self, state: State, *, load: bool, lands=None, then=None) -> bool:
        """Put `state` back, touching only what differs. Returns whether
        tagged ids were left because the bands have changed."""
        reg, table, marks = self.reg, self.table, self.marks
        mend = getattr(marks, "mend", None) if not load and lands is not None else None
        pre = self._read_lands() if mend is not None else None
        self._restoring = True
        try:
            # 1. a load: the layout first, so the params exist before their values
            if load and marks is not None and state.marks is not None:
                marks.before(state.marks)
            # 2. the routes, through the table's own call (the referee runs)
            if _rows(table.routes()) != _rows(state.routes):
                table.set_routes(self._rows_for(state.routes, table.routes()))
            # 3. the patch layer: a redraw, the layer and the faders' catch stay
            if _rows(table.desk()) != _rows(state.desk):
                table.set_desk(self._rows_for(state.desk, table.desk()), load=False)
            # 4. the macros
            if table.macros_doc() != state.macros:
                table.set_macros(state.macros, reg)
            # 4¼. the meta controller's rows (plan 44 D5b): through the table's
            #     own call, which writes `bindings.json`, where they live
            if _rows(self._table_rows()) != _rows(state.rows):
                table.set_rows(self._rows_for(state.rows, self._table_rows()))
            # 4⅓. who holds what and who is where (row 740), through the meta
            #     controller, which writes `players.json`, where they live
            if getattr(state, "moves", None) is not None and self._moves_doc() != state.moves:
                self.moves.put(state.moves, then)
            # 4½. the modifiers and their params (plan 28 N1)
            if state.modifiers is not None and not alike(self._mods(), state.modifiers):
                table.set_modifiers(state.modifiers, reg)
            # 4¾. the banks' membership (plan 31 B): a voice that comes back
            #     is declared fresh here, and step 5 lands its bases
            if state.banks is not None:
                banks = self._banks()
                for scheme, ids in state.banks.items():
                    bank = banks.get(scheme)
                    if bank is not None and list(bank.doc()) != ids:
                        bank.set(ids)
            # 5. the bases that differ, in registry order; again while a
            #    setter's side effect (a scene landing) moved others
            on_tag = state.tag == self._tag()
            left = False
            drift = getattr(state, "drift", None) or {}
            kept = self._follows_kept(state, self._beside_take())
            wrote: set[str] = set()
            for _ in range(PASSES):
                todo = {}
                for p in reg:
                    if p.id not in state.bases or not self._watches(p):
                        continue
                    v = state.bases[p.id]
                    then = drift.get(p.id, 0.0)
                    if (_same(p.base, v) if then == _drift(p) or not kept
                            else _same_own(p, v, then, p.base, _drift(p))):
                        continue
                    if not on_tag and self._is_tagged(p.id):
                        left = True
                        continue
                    # (with the follows made since: an undo keeps the dive's
                    # progress and takes back only what the user set)
                    if kept:
                        v = own(p, v, then)
                    todo[p.id] = list(v) if isinstance(v, list) else v
                if not todo:
                    break
                wrote.update(todo)
                reg.restore(todo, trims=state.trims)
            # 5½. what lives beside the camera (row 1018: the dive's framing),
            #     with it: only when this restore wrote the camera
            beside = getattr(self, "beside", None)
            if beside is not None and wrote.intersection(beside.ids):
                beside.put(getattr(state, "beside", None), kept)
            # 6. the macros' bases are acted on: nothing re-lands next frame
            if self.on_restore is not None:
                self.on_restore()
            # 7. a load: what is loaded, last (a scene landing in 5 moves a mark)
            if load and marks is not None and state.marks is not None:
                marks.put(state.marks)
            elif mend is not None:
                # not a load, but a setter's side effect may have moved a
                # landed name (a scene adopted): those go back to the step's
                mend(pre, lands)
        finally:
            self._restoring = False
        return left

    # ---- labels ----

    def _text(self, p, v) -> str:
        """A base value in the param's own words."""
        kind = getattr(p.kind, "value", p.kind)
        try:
            if kind == "continuous":
                return p.fmt(v)
            if kind == "enum":
                names = p.names
                return names[v] if 0 <= v < len(names) else str(v)
            if kind == "toggle":
                return "on" if v else "off"
        except Exception:  # noqa: BLE001 — a label must never fail a step
            return str(v)
        return str(v)

    def _label(self, then: State, now: State, ids: list[str], parts: list[str]) -> str:
        """A gesture's name, from what differs: one param → "<label> <old>
        → <new>"; several in one group → "<n> <group> settings"; table
        parts alone → their names; a mix → "<n> changes"."""
        if len(ids) == 1 and not parts:
            pid = ids[0]
            p = self.reg.get(pid)
            if p is None:
                return pid
            was, v = then.bases[pid], now.bases[pid]
            d0 = (getattr(then, "drift", None) or {}).get(pid, 0.0)
            d1 = (getattr(now, "drift", None) or {}).get(pid, 0.0)
            if d0 != d1:
                # (the user's change alone: the follows made since taken off)
                v = own(_Drift(p, d0), v, d1)
            return f"{p.label} {self._text(p, was)} → {self._text(p, v)}"
        if ids and not parts:
            groups = {getattr(self.reg.get(pid), "group", "") for pid in ids}
            if len(groups) == 1:
                return f"{len(ids)} {self.reg.group_word(groups.pop()) or 'param'} settings"
        if parts and not ids:
            return ", ".join(parts)
        n = len(ids) + len(parts)
        return f"{n} changes" if n else "the analyzer's layout"


class _Drift:
    """`p` read as if `follow` had moved it `drift` (for `own` in a label)."""

    def __init__(self, p, drift: float):
        self._p, self._drift = p, drift

    def __getattr__(self, name):
        return getattr(self._p, name)


# ---- the installed instance: what every push site and the two triggers reach ----

# kept across a hot reload of this module (importlib.reload re-executes it
# over the same globals): the panel's `Deck`'s stack, the meta controller's,
# and what says whether the panel is inside a meta section
_installed: Undo | None = globals().get("_installed")
_meta: Undo | None = globals().get("_meta")
_where = globals().get("_where")
_focused: Undo | None = globals().get("_focused", _installed)   # what the latch goes by
_hand: bool = globals().get("_hand", False)   # the person is working the panel (`by_hand`)
_room: Undo | None = globals().get("_room")   # the stack of the deck on air (`on_air`)
_loading: Undo | None = globals().get("_loading")   # a load's step still open (`_await_load`)


# each registry's own `Undo`, a deck's whether or not it is the installed one, so
# a performer writing that registry's bases finds its stack (`watching`). Weak on
# both sides: an `Undo` holds its registry
_watching = globals().get("_watching")
if _watching is None:
    _watching = WeakKeyDictionary()


def watching(reg) -> Undo | None:
    """The `Undo` over `reg`; else the installed one if it is over `reg` (an
    `Undo` from before a hot reload is not in the map); else None."""
    try:
        got = _watching.get(reg)
    except TypeError:
        got = None
    u = got() if got is not None else None
    if u is None and _installed is not None and _installed.reg is reg:
        return _installed
    return u


def install(u: Undo | None) -> None:
    """Make `u` the stack of the panel's `Deck` (app.main,
    `MetaController.point_panel`); None uninstalls. Focus goes with it if this changes
    the stack ⌘Z reaches. With the mouse in a meta section it does not, and meta stays
    as it was; focus on the deck left goes nowhere, so coming back is still coming back."""
    global _installed, _focused
    old, _installed = _installed, u
    if u is old:
        return
    if u is None or here() is u:
        _focus(u)
    elif _focused is old:
        _focused = None


def install_meta(u: Undo | None) -> None:
    """Make `u` the meta controller's stack (`MetaController`); None uninstalls,
    and with it `where`."""
    global _meta, _where, _focused
    if u is None and _focused is _meta:
        _focused = None
    _meta = u
    if u is None:
        _where = None


def where(inside_meta) -> None:
    """`inside_meta()`: is the panel inside a meta section now (`ui.Panel`)?"""
    global _where
    _where = inside_meta


NOTHING_HERE = "nothing to undo here: a playlist's edit is on no stack"
BOARD = "board"       # what `where` says over the player screen: the meta stack, for moves alone


def here() -> Undo | None:
    """The stack ⌘Z acts on: the meta controller's inside a meta section, else
    that of the panel's `Deck` (the owner, 2026-11-04). Never the newest of them.
    None where `where` says None: there, nothing is taken back (a playlist's section);
    and with no stack installed. `_on_no_stack` tells the two apart."""
    inside = _inside()
    if inside is None:
        return None
    return _meta if inside else _installed


def _inside() -> bool | None:
    """What `where` says now: a meta section, not one, or None for where no stack
    answers. False with no meta controller or nothing to ask."""
    if _meta is not None and _where is not None:
        try:
            got = _where()
            return None if got is None else bool(got)
        except Exception as e:  # noqa: BLE001 — a panel that raises is not inside one
            print(f"undo: where failed ({type(e).__name__}: {e})", file=sys.stderr)
    return False


def _on_no_stack() -> None:
    """⌘Z found no stack. Said only where `where` said so: no stack installed says
    nothing, as before, and has no list to name."""
    if _inside() is None:
        _meta._say(NOTHING_HERE)


def _over_board() -> bool:
    """Is the mouse over the player screen (`where` says `BOARD`)?"""
    if _where is None:
        return False
    try:
        return _where() == BOARD
    except Exception:  # noqa: BLE001 — `_inside` says it
        return False


def _not_its_own(at: Undo, verb: str) -> bool:
    """A section takes back only its own (row 800): on the meta stack the board answers for
    a player's moves and every other place for the rest. One stack and one order, so the step
    a press would reach may be the other's: said, and no history moves. So a setting is not
    taken back from an unrelated screen, nor a device reopened from the HANDS section."""
    if at is not _meta or at.moves is None:
        return False
    move = at._next_is_a_move(at.stack if verb == "undo" else at.redos)
    if move is None or move == _over_board():
        return False
    if move:
        at._say(f"not here: the meta controller's last change is a player's move. "
                f"To {verb} it, press over the player screen")
    else:
        at._say(f"nothing to {verb} on the player screen: the meta controller's last change "
                "is not a player's move. Press over that setting")
    return True


def _heard(at: Undo) -> None:
    """A press over the board: its answer for the board's line, marked if it did not do
    what was asked or the file did not follow."""
    moves = getattr(at, "moves", None)
    if at is _meta and moves is not None and _over_board():
        moves.heard = (at.status, not at.status.startswith(("undid ", "redid "))
                       or bool(moves.trouble()))


def _focus(u: Undo | None) -> None:
    """Focus comes to `u`, from elsewhere: it latches, whatever happened in between,
    and a step already open on it opens nothing. Already there: nothing."""
    global _focused
    if u is not _focused:
        _focused = u
        if u is not None:
            u.latched, u._opens = True, False


def _begun_on(u: Undo) -> bool:
    """A step begins on `u`: does it open the latch when it lands? The person's own
    change in the panel takes the focus there (only a stack ⌘Z can reach: a bank pad on
    the on-screen desk loads off air), by the step's own stack and not by the mouse. A
    controller's opens the stack in focus and moves nothing."""
    if _hand and (u is _installed or u is _meta):
        _focus(u)
    return u is _focused


def by_hand(on: bool) -> None:
    """Is the person working the panel, as of its latest draw (`ui_pane.left`), or has a
    text field just written (its writer, row 757)? It holds to the next draw's `left`, so
    a stack's tick, which comes first in the frame, reads it. No panel: never, and a
    change opens only the stack in focus."""
    global _hand
    _hand = bool(on)


def on_air(u: Undo) -> None:
    """`u`'s deck has gone on air (`MetaController`). The panel's deck has just gone on or
    off air, so what ⌘Z reaches there is another thing than it was: its stack latches.
    A meta stack in focus is as it was."""
    global _room
    if u is not _room:
        _room = u
        _shut(_installed)


def _shut(u: Undo | None) -> None:
    """Latch `u` where it stands: no focus moves, so the next change on it opens it."""
    if u is not None:
        u.latched, u._opens = True, False


def _await_load(u: Undo) -> None:
    """A load's step has opened on `u`, which is not the panel's deck. If it lands, and
    the panel's deck is on air, that deck latches: a mis-pressed pad and a ⌘Z must not
    take the room's last step. A load that changed nothing shuts nothing."""
    global _loading
    if u._open is not None and u._open.load:
        _loading = u


def _load_closed(u: Undo, *, landed: bool) -> None:
    """`u`'s open step is closing (or a clear is dropping it): the end of the wait."""
    global _loading
    if u is _loading:
        _loading = None
        if landed and _installed is _room:
            _shut(_installed)


def takes_back(u: Undo, *, here_now: bool = False) -> bool:
    """Would ⌘Z here take back the step just begun on `u`? For words which promise it:
    only a step that opens the latch and will not close empty. `here_now`: the caller
    knows ⌘Z reaches `u` from where the mouse is, and `here` cannot say yet (a drop's
    frame, with the item still live: nothing reads as hovered until it ends)."""
    return (here_now or here() is u) and u is _focused and u._will_open()


def _refused(at: Undo, verb: str) -> bool:
    """The press at `at`: an edit its tick has not seen lands first, then the press is a
    focus event of its own. A latched stack says so and touches nothing: no step is
    closed, so a hold or a gesture under way goes on."""
    at._observe(at._fingerprint())
    _focus(at)
    if at is _installed and _loading is not None:     # inside a load's settle time
        _load_closed(_loading, landed=_loading._will_land())
    if at.latched and not at._will_open():
        at._say(f"nothing to {verb} here yet: make a change {at.called} first")
        return True
    return _not_its_own(at, verb)


def installed() -> Undo | None:
    return _installed


def _guarded(what: str, fn, on: Undo | None = None) -> None:
    """The safety net must not be what breaks a load or a frame: a raise
    in here is said (stderr, the status line) and the caller goes on. `on`:
    a deck's own `Undo`; None, the installed one."""
    u = on if on is not None else _installed
    try:
        fn(u)
    except Exception as e:  # noqa: BLE001
        print(f"undo: {what} failed ({type(e).__name__}: {e})", file=sys.stderr)
        u._say(f"undo: {what} failed ({type(e).__name__}: {e})"[:120])


def push(label: str, *, load: bool = False) -> None:
    """`Undo.push` on the installed instance; nothing installed: a no-op.
    Call it before a replacing action changes anything."""
    if _installed is not None:
        _guarded("push", lambda u: u.push(label, load=load))


def push_on(reg, label: str, *, load: bool = False) -> None:
    """`Undo.push` on the stack over `reg` (`watching`), whichever is installed
    (plan 44 D5a: a load into a deck the panel is not on opens no step on
    the panel's); no such stack: the installed one, as `push`."""
    u = watching(reg)
    if u is None or u is _installed:
        push(label, load=load)
    else:
        _guarded("push", lambda v: v.push(label, load=load), on=u)
        if load:                              # a pad, a copy, with the panel on air (row 753)
            _await_load(u)


def push_meta(label: str, *, load: bool = False) -> None:
    """`Undo.push` on the meta controller's stack (a show, an analyzer loadable patch);
    none installed: a no-op."""
    if _meta is not None:
        _guarded("push", lambda u: u.push(label, load=load), on=_meta)


def keep_open(label: str, on: Undo, *, on_end=None) -> None:
    """`Undo.keep_open` on a deck's `Undo`, guarded as `push` is."""
    _guarded("keep open", lambda u: u.keep_open(label, on_end), on)


def let_close(on: Undo) -> None:
    """`Undo.let_close` on a deck's `Undo`, guarded as `push` is."""
    _guarded("let close", lambda u: u.let_close(), on)


def undo() -> None:
    """`Undo.undo` on the stack `here` names (the `edit.undo` trigger), unless it is
    latched. `Undo.undo` itself knows no latch."""
    at = here()
    if at is not None:
        _guarded("undo", lambda u: _refused(u, "undo") or u.undo(), on=at)
        _heard(at)
    else:
        _on_no_stack()


def redo() -> None:
    """`Undo.redo` on the stack `here` names (the `edit.redo` trigger), unless it is
    latched: the same stack and the same surprise. The push that opens one clears its
    redos, as any new change does, so a redo cannot cross a focus change."""
    at = here()
    if at is not None:
        _guarded("redo", lambda u: _refused(u, "redo") or u.redo(), on=at)
        _heard(at)
    else:
        _on_no_stack()
