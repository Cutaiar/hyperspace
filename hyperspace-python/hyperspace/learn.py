"""Learn — the one armed param, shared by every adapter that can complete it.

Right-click → Learn arms a param id here; whichever adapter sees the
performer move first completes it: the MIDI adapter with the message it
received (midi.py, ``MidiIO._learned`` → an ``abs`` / ``rel`` / ``toggle``
MIDI row), the hands adapter with the axis that moved furthest
(hands/core.py, ``HandsIO._learn`` → ``learn_source`` → a ``position``
route). Until plan 11 this state lived in ``MidiIO``, so with ``[midi]
enabled = false`` — or the adapter failing to open — there was no hand
Learn at all (audit B3). Now ``app.main`` builds one ``Learn`` over the
live table whatever the MIDI gate says and hands it to both adapters and
to the panel.

A learn writes into the **loaded preset** (plan 13 §3.3, D5): the row
goes into the live table — a knob's as a preset-layer desk row, a hand's
as a route — and no file is written. The preset's dirty dot (preset.py,
`Presets.signature` over the table) shows it until a save (⇧F, the preset
strip's save / as…); loading the preset again throws it away. A knob learn
on an invariant control or with the global layer up is refused (midi.py's
`_learned` calls `refuse`): the reason is `last`, `refused` is set, and
nothing changes.

**Unbind** is here too (plan 17 WP1): `unbind` removes what is bound to a
param in the loaded preset — its preset-layer desk rows and its routes,
one kind or both — as one undo step, whether or not a MIDI adapter
exists. `bound` is the same question without the edit (the menu asks it
to know what to list and whether to offer the item at all). A session row
(invariant or global layer) is never removed (D5, D6).

Two things the object owns:

  * **`learning`** — the armed param id, or None. Arming forgets a held
    question: the new learn is what the performer means now. Adapters key
    off it and clear it *before* the referee answers, so a hand cannot
    complete the same learn twice while the prompt is up.
  * **`pending`** — a learn the referee refused, ``(new row, the target's
    current performer)``, held for the panel's Replace / Keep prompt
    (ui_routing.py) rather than taking the target or being lost. The
    table is untouched until ``resolve_pending`` answers.

``learn_source`` resolves a ``band.sel.*`` alias to the band it stands
for (audit B4): an alias is not modulatable, so a route on it would sit
in the table doing nothing. The MIDI path binds the alias on purpose —
a knob on "the selected band's threshold" should follow the selection —
so that resolution is this object's, not the table's. The rule itself is
the registry's (``Registry.real``, installed by ``build_registry``), the
same one the panel's widgets read through; a registry without it (a
bare test rig) learns the alias as armed.

Imports nothing from the adapters or the panel: the registry and the
table are all it needs.
"""

from __future__ import annotations

from . import undo
from .params import Param, Registry
from .routing import Binding, Bindings, Owned


class Learn:
    """The armed param and the question the referee left for the panel."""

    def __init__(self, reg: Registry, table: Bindings, lane=None):
        self.reg = reg
        self.table = table
        # the router's `lane` (source → (scheme, index)), so one hand axis
        # named two ways — `hand:7` in an older preset, `hand:right.y` from
        # a learn — is one axis here too (decision register row 20); None:
        # sources compare as strings
        self.lane = lane
        self.learning: str | None = None
        self.pending: tuple[Binding, Binding] | None = None
        self.last = ""          # what the last learn did, for the status lines
        self.refused = False    # …and whether it was a refusal (drawn as a warning)

    def same_source(self, a: str, b: str) -> bool:
        """Do two source addresses read the same lane — the same string,
        or a number and a name the router resolves to one lane?"""
        if a == b:
            return True
        lane = getattr(self, "lane", None)       # a Learn from before a hot reload: None
        if lane is None:
            return False
        la = lane(a)
        return la[1] >= 0 and la == lane(b)

    def said(self, text: str) -> None:
        """What a learn that landed (or was kept) did, for the status lines."""
        self.last, self.refused = text, False

    def refuse(self, why: str) -> None:
        """A learn that may not land: nothing changes, `last` says why."""
        self.last, self.refused = why, True

    # ---- arming ----

    def arm(self, pid: str | None) -> None:
        """Arm (or cancel with None). A learn the prompt hasn't answered
        yet is forgotten: the new one is what the performer means now."""
        self.learning = pid
        self.pending = None

    def take(self) -> str | None:
        """The armed id, cleared — an adapter about to complete the learn
        calls this first so nothing else can complete it too."""
        pid, self.learning = self.learning, None
        return pid

    # ---- a source completes it ----

    def target_for(self, pid: str) -> Param | None:
        """The param a route for `pid` must name: the alias's band, else
        itself; None when the registry has no such id."""
        p = self.reg.get(pid)
        if p is None:
            return None
        real = getattr(self.reg, "real", None)
        return real(p) if real is not None else p

    def learn_source(self, source: str, when: str | None = None) -> None:
        """An adapter completes the learn with one of its own sources
        (hands/core.py: ``hand:right.pitch``, by name): a `position` route at depth 1 — the
        source is the whole fader, through the Router like every route,
        with no pickup and no device feedback. `when` gates the row on a
        second source (a pinch held while learning), so the row only acts
        while that reads on.

        A learned axis drives one param: learning it onto another *moves*
        it (its other position rows go), and learning it again onto the
        same param only refreshes the gate. If the param already has a
        different performer the learn is held in `pending` for the panel's
        prompt (`resolve_pending`) — the table untouched until it answers —
        rather than taking the target or being lost. `learning` is cleared
        first, so the hands adapter, which keys off it, cannot fire again.
        """
        pid = self.take()
        if pid is None:
            return
        p = self.target_for(pid)
        if p is None:
            return
        b = Binding(source, p.id, "position", 1.0, when=when)
        cur = self.table.owner(p.id)
        if cur is not None and self.same_source(cur.source, source) and cur.op == "position":
            undo.push(f"learn {p.id}")               # one undo step (undo.py, plan 15)
            cur.when = when                          # the same axis again: no move
            self.said(f"learned {p.id} ← {cur.describe()} (into the preset)")
            return
        if cur is not None:
            self.pending = (b, cur)
            self.said(f"{Owned(cur, b)} — replace?")
            return
        self._place(b)

    def resolve_pending(self, replace: bool) -> Binding | None:
        """The prompt's answer to a held learn: *Replace* swaps the target's
        performer for the learned row (into the loaded preset, no file
        written); *Keep* leaves the table as it was. Returns the row now in
        the table, or None."""
        if self.pending is None:
            return None
        new, old = self.pending
        self.pending = None
        if not replace:
            self.said(f"kept {old.describe()} on {old.target}")
            return None
        self._place(new)
        return new

    def _place(self, b: Binding) -> None:
        """The learned row into the table: the axis's other position rows
        go first (one axis, one param), then `replace_owner` — the one door
        onto a target, which reads the owner *now* (a free target takes the
        row; the prompt's Replace removes whoever holds it at this moment,
        not whoever did when the question was asked). A route of the
        loaded preset's: no file is written (plan 13 §3.3). One undo step
        (undo.py): the rows it took out come back with a Ctrl+Z."""
        undo.push(f"learn {b.target}")
        table = self.table
        for x in [x for x in table.of(b.scheme)
                  if self.same_source(x.source, b.source) and x.op == "position"]:
            table.remove(x)
        table.replace_owner(b)
        self.said(f"learned {b.target} ← {b.describe()} (into the preset)")

    # ---- unbind ----

    def bound(self, ids) -> tuple[list[Binding], list[Binding], list[Binding]]:
        """What is bound to a param: (the loaded preset's desk rows, its
        routes, the session's MIDI rows). `ids` as for `unbind`. The first
        two are what `unbind` may remove; the third it never does."""
        return bound(self.table, ids)

    def unbind(self, ids, *, desk: bool = True, routes: bool = True, name=None) -> list[Binding]:
        """Remove what is bound to a param, in the loaded preset: its
        preset-layer desk rows (`desk`) and its routes (`routes`). `ids` is
        the drawn param's id and the real one's (an alias and its band; one
        id when they are the same). Returns the rows removed.

        A desk row goes through `Bindings.unbind` (it bumps
        `redraw_serial`: an adapter redraws and the control goes dark, D8);
        a route — any scheme, enabled or not — through `Bindings.remove`,
        its depth subscribers with it. No file is written: the edit is the
        loaded preset's (plan 13 §3.3). One undo step, pushed once and only
        when something goes. `name(b)` gives each row's words for the
        message; without it, `Binding.describe()`. A session row is never
        removed: with nothing else to remove, that is a refusal."""
        ids = _ids(ids)
        if not ids:
            return []
        real = ids[-1]
        name = name if name is not None else Binding.describe
        mine, routed, session = self.bound(ids)
        gone = (mine if desk else []) + (routed if routes else [])
        if not gone:
            if desk and session:
                b = session[0]
                where = "on the global layer" if b.layer == "global" else "invariant"
                self.refuse(f"{name(b)} → {b.target} is {where} (the session's, "
                            "edited in bindings.json) — not unbound")
            return []
        undo.push(f"unbind {real}")                  # one undo step (undo.py, plan 15)
        gone = []
        if desk:
            for pid in ids:
                gone += self.table.unbind(pid)       # what the table took out
        if routes:
            for b in routed:
                self.table.remove(b)
            gone += routed
        # a question held against a row that just went has nothing to ask
        if self.pending is not None and any(self.pending[1] is g for g in gone):
            self.pending = None
        names = [name(b) for b in gone]
        told = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
        self.said(f"unbound {real} from {told}")
        return gone


def _ids(ids) -> tuple[str, ...]:
    """One id or several, as a tuple with no repeats, in order."""
    return (ids,) if isinstance(ids, str) else tuple(dict.fromkeys(ids))


def bound(table: Bindings, ids) -> tuple[list[Binding], list[Binding], list[Binding]]:
    """`Learn.bound` over any table (the panel's menu lists from it with
    or without a learn object, so its lines are what Unbind removes):
    (preset-layer desk rows, routes, the session's MIDI rows) on `ids`. A
    route is a performer row from a continuous source — never a MIDI row,
    whatever its op, so a session row can not come back as a "route"."""
    ids = _ids(ids)
    midi = [b for b in table.bindings if b.is_midi and b.target in ids]
    routes: list[Binding] = []
    for pid in ids:
        routes += [b for b in table.routes_to(pid)
                   if not b.is_midi and not any(b is x for x in routes)]
    return ([b for b in midi if b.layer == "preset"], routes,
            [b for b in midi if b.layer != "preset"])
