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

from .params import Param, Registry
from .routing import Binding, Bindings, Owned


class Learn:
    """The armed param and the question the referee left for the panel."""

    def __init__(self, reg: Registry, table: Bindings):
        self.reg = reg
        self.table = table
        self.learning: str | None = None
        self.pending: tuple[Binding, Binding] | None = None
        self._last = ""         # what the last learn did, for the status lines
        self.refused = False    # …and whether it was a refusal (drawn as a warning)

    @property
    def last(self) -> str:
        return self._last

    @last.setter
    def last(self, text: str) -> None:
        self._last, self.refused = text, False

    def refuse(self, why: str) -> None:
        """A learn that may not land: nothing changes, `last` says why."""
        self._last, self.refused = why, True

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
        (hands/core.py: ``hand:<i>``): a `position` route at depth 1 — the
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
        if cur is not None and cur.source == source and cur.op == "position":
            cur.when = when                          # the same axis again: no move
            self.last = f"learned {p.id} ← {cur.describe()} (into the preset)"
            return
        if cur is not None:
            self.pending = (b, cur)
            self.last = f"{Owned(cur, b)} — replace?"
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
            self.last = f"kept {old.describe()} on {old.target}"
            return None
        self._place(new)
        return new

    def _place(self, b: Binding) -> None:
        """The learned row into the table: the axis's other position rows
        go first (one axis, one param), then `replace_owner` — the one door
        onto a target, which reads the owner *now* (a free target takes the
        row; the prompt's Replace removes whoever holds it at this moment,
        not whoever did when the question was asked). A route of the
        loaded preset's: no file is written (plan 13 §3.3)."""
        table = self.table
        for x in [x for x in table.of(b.scheme) if x.source == b.source and x.op == "position"]:
            table.remove(x)
        table.replace_owner(b)
        self.last = f"learned {b.target} ← {b.describe()} (into the preset)"
