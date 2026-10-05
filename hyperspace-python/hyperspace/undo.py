"""Undo — one step per gesture, with no write hook (plan 15 WP1, decision 26).

Nothing tells this module that a parameter was written. Once a frame
`Undo.tick` compares a cheap **fingerprint** of what the user sets — the
*base* of every watched param, the table's performer rows, the desk's
preset layer and the macros — with last frame's. A change opens a step
that holds the state as it was; the step stays open while changes keep
coming and closes after `SETTLE_S` of quiet. So one slider drag, one knob
turn on the desk, one typed value or one toggle is one step, whatever
wrote it (the panel, a key row, a MIDI row, the mouse).

A performer makes no step: a hand, a band or an LFO writes an *offset*
(`Router.modulate`), never the base, and the fingerprint reads bases. The
frame a performer takes a param, and the frame it lets go, the base can
move in its last bits (the norm round trip in `Param.modulate` /
`Param.apply`), so two fingerprints are *the same* when every float pair
is within `REL_TOL` / `ABS_TOL`.

A **replacing action** — a preset or show load, a Learn landing, an
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
the rig's output settings are all `persist=False`. The session's rows of
the table (keys, pad, invariant and global-layer MIDI rows) are not
watched: they are `bindings.json`'s.

The band layout: a band added, removed or moved re-declares every
`band.*` param and is **not** a step. Each state is tagged with the shape
its `tagged` ids live on (`tag()`: the bands' names in strip order), and
a `band.*` value is put back only when the tag is the same as when the
state was taken — a strip's values never land on another band. A load
step carries the layout in its marks and puts it back first.

Imports nothing from the package: the registry and the table arrive as
arguments and are used duck-typed (the rule lfo.py and tempo.py keep), so
any module may import this one. `install` holds the app's one `Undo`;
`push` / `undo` / `redo` at module level act on it and do nothing when
none is installed (every test that builds no `Undo`).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, replace
from operator import attrgetter
from typing import Any

SETTLE_S = 0.4        # quiet time that ends a step. Plan 18's knob slew must stay under it.
LIMIT = 100           # steps kept; the oldest goes first
ABSORB_FRAMES = 2     # frames after a restore whose changes are the restore's own
REL_TOL, ABS_TOL = 1e-9, 1e-12
EXCLUDED_GROUPS = ("tempo",)          # the clock (plan 15 fork 5)
PASSES = 3            # restore passes: a setter with side effects (scene.select) needs a second

# the row fields the fingerprint reads — every one a file would hold; the
# ROUTING page edits rows in place, so there is no serial to read instead
ROW_FIELDS = ("source", "target", "op", "value", "enabled", "scale", "when", "rest",
              "layer", "pickup", "feedback", "on", "off", "ring")
LEFT = "the bands have changed: their strips were left"


def watched(p) -> bool:
    """Is this param's base part of the undo history: persisted, not an
    alias, not a trigger, and its group not in `EXCLUDED_GROUPS`."""
    return (p.persist and not p.alias and p.group not in EXCLUDED_GROUPS
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


_row = attrgetter(*ROW_FIELDS)        # a row as the tuple of its fields


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
    performer rows and of the preset-layer rows, the macros' document, the
    tag as it read then, and — for a load step — the marks."""

    bases: dict[str, Any]
    routes: tuple
    desk: tuple
    macros: dict
    tag: Any = None
    marks: Any = None


@dataclass
class Step:
    """One entry of a stack: its label ("" until a gesture closes), the
    state to put back, whether it carries the marks, and whether a caller
    pushed it (an action) or the watcher opened it (a gesture)."""

    label: str
    before: State
    load: bool = False
    action: bool = False


class Undo:
    """The undo and redo stacks over one registry and one table.

    `reg` iterates params (`id`, `base`, `persist`, `alias`, `group`,
    `kind`, `label`, `fmt`, `names`) and has `get(id)` and `restore({id:
    value})`. `table` has `bindings` (rows with the `ROW_FIELDS`),
    `routes()`, `desk()`, `macros`, `macros_doc()`, `set_routes(rows)`,
    `set_desk(rows, load=False)` and `set_macros(doc, reg)`. `marks` (optional) is "what is loaded", opaque here: `take()`,
    `before(mark)` (called first in a load step's restore: the layout) and
    `put(mark)` (called last: the names and references). `tag` (optional)
    is a callable naming the shape the `tagged` id prefixes live on.
    `on_restore` is called after every restore's writes.
    """

    def __init__(self, reg, table, *, marks=None, tag=None, tagged=("band.",),
                 on_restore=None):
        self.reg, self.table = reg, table
        self.marks, self.tag, self.tagged = marks, tag, tuple(tagged)
        self.on_restore = on_restore
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
        self._fp = self._fingerprint()
        self._settled = self._take()

    # ---- what is watched ----

    def _tag(self):
        return self.tag() if self.tag is not None else None

    def _params(self) -> list:
        """The watched params, in registry order. A band layout change and
        a shader reload re-declare params, so the registry is read every
        time — but the filter runs only when it holds other objects than
        last time (a list comparison by identity: a re-declared param is a
        new object even under an old id)."""
        every = list(self.reg)
        if every != self._every:
            self._every = every
            self._watched = [p for p in every if watched(p)]
            self._ids = tuple(p.id for p in self._watched)
        return self._watched

    def _fingerprint(self) -> tuple:
        """(ids, bases, routes, desk, macros, tag) as of now — the cheap
        read `tick` makes every frame. The preset layer is read as the
        table's rows whose `layer` is "preset" (what `table.desk()`
        returns, without asking every row whether it is a MIDI row)."""
        ps = self._params()
        table = self.table
        return (self._ids, tuple([p.base for p in ps]), _rows(table.routes()),
                _rows([b for b in table.bindings if b.layer == "preset"]),
                _macros(table), self._tag())

    @staticmethod
    def _same_fp(a: tuple, b: tuple) -> bool:
        """Equal, or equal but for float pairs within the tolerance."""
        if a == b:
            return True
        if a[0] != b[0] or a[2:] != b[2:]:
            return False
        return all(x is y or _same(x, y) for x, y in zip(a[1], b[1], strict=True))

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
                     self.marks.take() if marks and self.marks is not None else None)

    # ---- the frame ----

    def tick(self, now: float) -> None:
        """Once a frame, after the scene-setters have written their bases."""
        self._now = now
        self._frame += 1
        fp = self._fingerprint()
        if self._observe(fp):
            return
        # quiet this frame: an open step closes once the settle time has passed
        if self._open is not None and now - self._changed_at >= SETTLE_S:
            self._close()

    def _observe(self, fp: tuple) -> bool:
        """Steps 1–3 of the tick: a reshaped registry, a restore's own
        follow-ups, a change. True when the frame is settled by it (no
        step may close on this frame's evidence)."""
        last = self._fp
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
                    self._begin(Step("", self._settled))
                return True
        return False

    def _begin(self, step: Step) -> None:
        self._open = step
        self.stack.append(step)
        del self.stack[:-LIMIT]
        self.redos.clear()

    def _close(self) -> None:
        """End the open step, if any: `settled` becomes the state now, a
        gesture is labelled from what differs, and a step with nothing to
        put back is taken off the stack."""
        step, self._open = self._open, None
        self._settled = now = self._take()
        if step is None:
            return
        ids, parts, _left = self._differs(step.before, now, tagged=False)
        empty = not ids and not parts and step.before.tag == now.tag
        if empty and step.load and self.marks is not None:
            empty = self._marks_equal(step.before.marks)
        if empty:
            self.stack[:] = [s for s in self.stack if s is not step]
        elif not step.label:
            step.label = self._label(step.before, now, ids, parts)

    def _marks_equal(self, mark) -> bool:
        try:
            return bool(self.marks.take() == mark)
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
        A second push in the same frame is the same action from the inside
        (a show load that loads its startup preset): the outer label stands."""
        if self._restoring or self._action_frame == self._frame:
            return
        self._flush()
        before = self._settled
        if load and self.marks is not None:
            before = replace(before, marks=self.marks.take())
        self._begin(Step(label, before, load=load, action=True))
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
            dst.append(Step(step.label, now, load=step.load, action=step.action))
            del dst[:-LIMIT]
            left = self._restore(step.before, load=step.load)
            self._say(f"{verb} {step.label}" + (f" ({LEFT})" if left else ""))
            self._fp = self._fingerprint()
            self._settled = self._take()
            self._absorb = ABSORB_FRAMES
            return True
        self._say(none)
        return False

    def clear(self) -> None:
        """Forget every step; the state now is the settled one."""
        self.stack.clear()
        self.redos.clear()
        self._open, self._absorb, self._action_frame = None, 0, -1
        self._fp = self._fingerprint()
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
        for pid, v in then.bases.items():
            if pid not in now.bases or _same(v, now.bases[pid]):
                continue
            if apart and self._is_tagged(pid):
                left = left or tagged
                continue
            ids.append(pid)
        parts = [name for name, a, b in (("routes", _rows(then.routes), _rows(now.routes)),
                                         ("desk", _rows(then.desk), _rows(now.desk)),
                                         ("macros", then.macros, now.macros)) if a != b]
        return ids, parts, left

    @staticmethod
    def _rows_for(want: tuple, have: list) -> list:
        """The rows to hand a table call: the live row where one with the
        same fields is still in the table (its runtime state — a fader's
        catch — stays), else a copy of the state's."""
        pool: dict[tuple, list] = {}
        for b in have:
            pool.setdefault(_row(b), []).append(b)
        out = []
        for b in want:
            live = pool.get(_row(b))
            out.append(live.pop(0) if live else replace(b))
        return out

    def _restore(self, state: State, *, load: bool) -> bool:
        """Put `state` back, touching only what differs. Returns whether
        tagged ids were left because the bands have changed."""
        reg, table, marks = self.reg, self.table, self.marks
        self._restoring = True
        try:
            # 1. a load: the layout first, so the params exist before their values
            if load and marks is not None and state.marks is not None:
                marks.before(state.marks)
            # 2. the routes, through the table's own call (the referee runs)
            if _rows(table.routes()) != _rows(state.routes):
                table.set_routes(self._rows_for(state.routes, table.routes()))
            # 3. the preset layer: a redraw, the layer and the faders' catch stay
            if _rows(table.desk()) != _rows(state.desk):
                table.set_desk(self._rows_for(state.desk, table.desk()), load=False)
            # 4. the macros
            if table.macros_doc() != state.macros:
                table.set_macros(state.macros, reg)
            # 5. the bases that differ, in registry order; again while a
            #    setter's side effect (a scene landing) moved others
            on_tag = state.tag == self._tag()
            left = False
            for _ in range(PASSES):
                todo = {}
                for p in reg:
                    if p.id not in state.bases or not watched(p):
                        continue
                    v = state.bases[p.id]
                    if _same(p.base, v):
                        continue
                    if not on_tag and self._is_tagged(p.id):
                        left = True
                        continue
                    todo[p.id] = list(v) if isinstance(v, list) else v
                if not todo:
                    break
                reg.restore(todo)
            # 6. the macros' bases are acted on: nothing re-lands next frame
            if self.on_restore is not None:
                self.on_restore()
            # 7. a load: what is loaded, last (a scene landing in 5 moves a mark)
            if load and marks is not None and state.marks is not None:
                marks.put(state.marks)
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
            return f"{p.label} {self._text(p, then.bases[pid])} → {self._text(p, now.bases[pid])}"
        if ids and not parts:
            groups = {getattr(self.reg.get(pid), "group", "") for pid in ids}
            if len(groups) == 1:
                return f"{len(ids)} {groups.pop() or 'param'} settings"
        if parts and not ids:
            return ", ".join(parts)
        n = len(ids) + len(parts)
        return f"{n} changes" if n else "the band layout"


# ---- the installed instance: what every push site and the two triggers reach ----

# kept across a hot reload of this module (importlib.reload re-executes it
# over the same globals)
_installed: Undo | None = globals().get("_installed")


def install(u: Undo | None) -> None:
    """Make `u` the app's undo (app.main); None uninstalls."""
    global _installed
    _installed = u


def installed() -> Undo | None:
    return _installed


def _guarded(what: str, fn) -> None:
    """The safety net must not be what breaks a load or a frame: a raise
    in here is said (stderr, the status line) and the caller goes on."""
    u = _installed
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


def undo() -> None:
    """`Undo.undo` on the installed instance (the `edit.undo` trigger)."""
    if _installed is not None:
        _guarded("undo", lambda u: u.undo())


def redo() -> None:
    """`Undo.redo` on the installed instance (the `edit.redo` trigger)."""
    if _installed is not None:
        _guarded("redo", lambda u: u.redo())
