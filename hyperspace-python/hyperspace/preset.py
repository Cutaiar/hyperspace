"""The preset — one file that holds everything a performance moment is
(plan 13 D1, §2.1): ``hyperspace.preset/2``.

  {"schema": "hyperspace.preset/2", "name": "TRIP", "note": "…",
   "values": {id: base, …},            the performance part (params.PARTS)
   "routes": [row, …],                 the performer rows (routing.Binding)
   "desk":   [row, …],                 the APC40's preset layer (routing.Binding)
   "macros": {"macro.1": {…}, …},      the macros' labels and subscribers
   "modules": {"fx": "trip", …}}       module-preset labels (D3)

One file per preset, ``<root>/presets/<slug>.json``: the factory ones in
``hyperspace/library/presets/``, the user's in ``<home>/presets/``
shadowing by name. `Presets` registers the folder with the library as a
**document kind** (`Library.kind`), so listing, shadowing, load / save
as / delete, the dirty dot and the file watch are the library's, and
the one preset strip (ui_presets.strip over ``presets``) drives it. The
bank (F1–F8, the APC40's clip row 1) names these files; the project
holds the bank (library.Project, ``hyperspace.project/2``).

A load is a scene-setter (docs/ARCHITECTURE.md §3): it writes bases and
replaces rows, never an offset. In order (plan 13 §5):

1. note what the file names that a preset may not: a session param
   ("`tempo.bpm` is the session's, ignored"), an id nobody has, a
   ``routes`` row that is not a performer row, a second performer on one
   target (the referee's, below);
2. land the values: **every** persisted param of every performance group
   gets the file's value or its group default (`Library.resolved`: the
   group's default module preset over the build values), in registry
   order, in one go (D2). A session param is never touched, and the
   rotation phases (not persisted) are left spinning;
3. replace every performer row with ``routes`` (`Bindings.set_routes`;
   the referee is first-wins, the rest in ``table.dropped`` for the
   ROUTING page);
4. replace the desk's preset layer with ``desk`` (`Bindings.set_desk`: a
   row on an invariant control is dropped and its note joins step 1's;
   the desk drops to the preset layer, D4, and the MIDI adapter redraws
   every ring and LED with the faders' catch cleared). A file with **no**
   ``desk`` key gets the factory preset layer (`routing.factory_desk`'s
   preset rows — a fresh preset, plan 13 §3.2); ``"desk": []`` is an
   empty preset layer, every preset control dark (D8);
5. replace the macros' labels and subscribers with ``macros``
   (`Bindings.set_macros`) and land the base subscribers at once from the
   macros' bases just landed (`Router.follow_macros(force=True)`). The
   macro is the scene-setter of record: a param a base subscriber names
   ends at the subscriber's value even when ``values`` names it too;
6. record each performance group's ``modules`` label as its current
   module preset, clean against the values just landed — a label only,
   never a chain-load of the module preset (D3); a group the file does
   not name shows none;
7. the notes from step 1 are kept in ``notes`` and summed up in
   ``Library.warning`` for the panel.

A save (`document`) writes the performance snapshot, every performer row
(disabled ones too), the table's preset-layer rows (`Bindings.desk`, a
row's ``layer`` left out: every desk row is the preset's), the table's
macros (`Bindings.macros_doc`) and the performance groups' current
module labels. The dirty dot (`signature`) covers all of it, so a Learn
or a ROUTING-page edit — which change the table and write no file —
shows as the loaded preset edited; only a save (⇧F, the strip's save /
as…) writes it. `python -m hyperspace.preset` regenerates the five
party presets' routes from ``routing.PRESETS`` and every factory
preset's ``desk`` from `routing.factory_desk` (their values are data in
the files); tests/test_presets.py pins the files to the code.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

from . import routing
from .library import FACTORY, PERFORMANCE_SCHEMA, PRESETS, LibraryError
from .params import PERFORMANCE_GROUPS, part_of
from .routing import LANE_SCHEMES, MOD_OPS, Binding

SCHEMA = PERFORMANCE_SCHEMA
GROUP = PRESETS                   # the library folder, and the strip's group
FACTORY_DIR = FACTORY / GROUP
# the party presets whose routes are generated from routing.PRESETS:
# file slug → routing preset name
PARTY = {f"party-{n}": f"party-{n}" for n in ("tumble", "faces", "field", "wake", "trip")}


def desk_json(rows) -> list[dict]:
    """Preset-layer rows as a preset's ``desk``: each row's JSON without
    its ``layer`` — in a preset every desk row is the preset layer's
    (`Bindings.set_desk` forces it on the way back in)."""
    out = []
    for b in rows:
        d = b.to_json()
        d.pop("layer", None)
        out.append(d)
    return out


def fresh_desk(profile: str = "apc40") -> list[Binding]:
    """A fresh preset's desk: the factory map's preset layer (plan 13 §3.2)
    — what a file with no ``desk`` key gets, and every factory preset's."""
    return [b for b in routing.factory_desk(profile) if b.layer == "preset"]


def dumps(doc: dict) -> str:
    """A preset as file text: one route or desk row per line, so a diff
    reads as a binding; the values one per line."""
    parts = []
    for key, v in doc.items():
        if key in ("routes", "desk") and isinstance(v, list):
            if v:
                rows = ",\n".join("  " + json.dumps(r) for r in v)
                text = f"[\n{rows}\n ]"
            else:
                text = "[]"
        elif isinstance(v, dict) and v:
            text = json.dumps(v, indent=1).replace("\n", "\n ")
        else:
            text = json.dumps(v)
        parts.append(f" {json.dumps(key)}: {text}")
    return "{\n" + ",\n".join(parts) + "\n}\n"


class Presets:
    """The loaded preset over one library, registry and router.

    Built as ``Presets(lib, reg, router)`` after ``lib.routing(router)``;
    it registers the ``presets`` document kind and makes itself
    ``lib.presets``, which the project's bank (F-keys, the preset row)
    loads and saves through. The kind's hooks look this object's methods
    up at call time, so a hot reload that re-classes it reaches them."""

    def __init__(self, lib, reg, router):
        self.lib, self.reg, self.router = lib, reg, router
        self.note = ""
        self.notes: list[str] = []       # step 1's notes from the last load
        self.desk_notes: list[str] = []  # the desk rows the last load dropped (set_desk)
        lib.kind(GROUP, SCHEMA.rpartition("/")[0],
                 load=lambda doc, path: self.load_doc(doc, path),
                 document=lambda name: self.document(name),
                 signature=lambda: self.signature(),
                 versions=(int(SCHEMA.rpartition("/")[2]),),
                 text=lambda doc: dumps(doc))
        lib.on_load(GROUP, lambda name: self._landed(name))
        lib.presets = self

    # ---- the API ----

    @property
    def current(self) -> str | None:
        return self.lib.current(GROUP)

    def load(self, name: str) -> list[str]:
        """Load a preset by name through the library (which records it as
        the strip's current and its clean reference); returns the ids the
        file names that nothing has."""
        missing = self.lib.load(GROUP, name)
        self._warn(name)
        return missing

    def save_as(self, name: str) -> Path:
        """The live state as a user preset (a factory one of that name is
        shadowed, never overwritten)."""
        return self.lib.save_as(GROUP, name)

    def load_doc(self, doc: dict, path: Path | None = None) -> list[str]:
        """Apply a preset document — the kind's loader (plan 13 §5).
        Returns the unknown ids; the notes land in `notes`."""
        lib, reg, table = self.lib, self.reg, self.router.table
        notes: list[str] = []
        # 1. what the file names that a preset may not carry — all parsed
        #    before anything lands, so a bad row leaves the state alone
        values: dict[str, Any] = {}
        unknown: list[str] = []
        for pid, v in dict(doc.get("values") or {}).items():
            p = reg.get(pid)
            if p is None:
                unknown.append(pid)
            elif part_of(p) == "session":
                notes.append(f"{pid} is the session's, ignored")
            elif part_of(p) is None or not p.persist:
                notes.append(f"{pid} is not part of a preset, ignored")
            else:
                values[pid] = v
        if unknown:
            shown = ", ".join(unknown[:4]) + ("…" if len(unknown) > 4 else "")
            notes.append(f"{len(unknown)} unknown id(s): {shown}")
        routes: list[Binding] = []
        for row in doc.get("routes") or []:
            b = Binding.from_json(row)
            if b.scheme not in LANE_SCHEMES or b.op not in MOD_OPS:
                notes.append(f"dropped {b.source} → {b.target} ({b.op}): not a performer row")
                continue
            routes.append(b)
        # no `desk` key: a fresh preset's, the factory preset layer; an
        # explicit [] is an empty one (every preset control dark, D8)
        if "desk" in doc:
            desk = [Binding.from_json(row) for row in doc.get("desk") or []]
        else:
            desk = fresh_desk(table.profile)
        macros = dict(doc.get("macros") or {})
        routing.macros_of(macros)                  # a bad subscriber raises before anything lands
        modules = dict(doc.get("modules") or {})
        for group in list(modules):
            if group not in PERFORMANCE_GROUPS or group == "macro":
                notes.append(f"module {group}: not a performance group, ignored")
                modules.pop(group)
        # 2. every performance param: the file's value, else its group default
        by_group: dict[str, dict[str, Any]] = {g: {} for g in PERFORMANCE_GROUPS}
        for pid, v in values.items():
            by_group[reg[pid].group][pid] = v
        landed: dict[str, Any] = {}
        for group in PERFORMANCE_GROUPS:
            landed.update(lib.resolved(group, by_group[group]))
        # a value that will not take (a hand-edited "fast" on a number) must
        # not leave half the look on this preset and half on the last: the
        # state as it was goes back and the load is refused whole
        before = reg.snapshot(part="performance")
        try:
            lib.restore(landed)
        except (ValueError, TypeError) as e:
            lib.restore(before)
            raise ValueError(f"a value would not land ({e}); nothing loaded") from e
        # 3. every performer row replaced; the referee keeps the first
        table.set_routes(routes)
        notes += [f"dropped {b.source} → {b.target}: {why}" for b, why in table.dropped]
        # 4. the desk's preset layer replaced; the layer drops to it (D4)
        #    and the MIDI adapter redraws, the faders' catch cleared
        self.desk_notes = table.set_desk(desk)
        notes += self.desk_notes
        # 5. the macros replaced, their base subscribers landed now from the
        #    macro bases step 2 put down — the macro is the scene-setter of
        #    record, so its subscriber's value stands over `values`
        table.set_macros(macros)
        self.router.follow_macros(force=True)
        self.note = str(doc.get("note") or "")
        # 6. the module labels: a label and a clean dot, never a load (D3)
        for group in PERFORMANCE_GROUPS:
            if group == "macro":
                continue
            label = modules.get(group)
            lib.label(group, str(label) if label else None)
        # 7. the notes, for the panel
        self.notes = notes
        self._warn(str(doc.get("name") or (path.stem if path else "preset")))
        return unknown

    def document(self, name: str) -> dict:
        """The live state as a preset document, named — what a save writes."""
        lib = self.lib
        modules = {g: lib.current(g) for g in PERFORMANCE_GROUPS
                   if g != "macro" and lib.current(g)}
        doc: dict[str, Any] = {"schema": SCHEMA, "name": name}
        if self.note:
            doc["note"] = self.note
        table = self.router.table
        doc.update(values=self.reg.snapshot(part="performance"),
                   routes=[b.to_json() for b in table.routes()],
                   desk=desk_json(table.desk()), macros=table.macros_doc(),
                   modules=modules)
        return doc

    def signature(self) -> tuple:
        """What the strip's dirty dot compares: the performance bases, the
        performer rows, the desk's preset layer and the macros, each as it
        would be written."""
        table = self.router.table
        return (self.reg.snapshot(part="performance"),
                json.dumps([b.to_json() for b in table.routes()]),
                json.dumps(desk_json(table.desk()), sort_keys=True),
                json.dumps(table.macros_doc(), sort_keys=True))

    # ---- internals ----

    def _warn(self, name: str) -> None:
        if self.notes:
            more = f" (+{len(self.notes) - 1} more)" if len(self.notes) > 1 else ""
            self.lib.warning = f"preset {name}: {self.notes[0]}{more}"

    def _landed(self, name: str | None) -> None:
        """The library's load hook: the bank lights the slot that names
        what just loaded, whichever road it came in by (the strip, an F-key,
        a file edited on disk); a preset the bank does not name lights none."""
        pr = self.lib.project
        pr.active = pr.bank.index(name) if name in pr.bank else -1


# --------------------------------------------------------------- factory files

def write_factory(directory: Path = FACTORY_DIR) -> list[Path]:
    """Regenerate what the factory presets take from code
    (`python -m hyperspace.preset`): every preset's ``desk`` is the
    factory preset layer (`fresh_desk`), and the party presets' routes
    are `routing.PRESETS`'. Every other key in a file — the values, the
    note, the modules, the macros — is data and stays as it is."""
    desk = desk_json(fresh_desk())
    out = []
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            raise LibraryError(f"{path.name}: {e}") from e
        routing_name = PARTY.get(path.stem)
        if routing_name is not None:
            doc["routes"] = [b.to_json() for b in routing.PRESETS[routing_name][0]]
        doc["desk"] = copy.deepcopy(desk)
        path.write_text(dumps(doc))
        out.append(path)
    return out


if __name__ == "__main__":
    for p in write_factory():
        print(p, file=sys.stdout)
