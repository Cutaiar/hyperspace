#!/usr/bin/env python3
"""Set every loadable patch's ghost hands to the show look.

    uv run python tools/set_hands_look.py [FOLDER]            # dry run
    uv run python tools/set_hands_look.py [FOLDER] --apply    # backup, then write

FOLDER is the library (the folder holding ``loadable/``), or its ``loadable/``
(or old ``presets/``) folder itself; ``--library PATH`` says the same. With
neither, the library is config.toml's ``[library] path``, else the home.

Run it on the library with Hyperspace closed: a dry run first, then
``--apply``. The look is `ghost.SHOW_LOOK` (on, BONES, PLAIN, 50%), the one the
app starts a new patch's hands from; this puts it into the patches already saved.

The patches visited are the library's loadable patches, ``loadable/`` and
``presets/`` every folder down — the era folders included — as the library
lists them (`migrate_library.loadable_files`: hidden folders, dot-files,
``.bak-`` copies and ``trash/`` left out). In each that loads:

- ``ghost.on``, ``ghost.alpha``, ``ghost.style`` and ``ghost.material`` are
  set to the show look, and so are ``ghost.<n>.*`` for every extra hands node
  the graph holds (``{"kind": "hands", "instance": n}``). ``guide``,
  ``tethers`` and the room's ``mirror`` are not touched, nor any route or desk
  row onto them;
- a hands layer that reaches no output (`graph.reaches`) gets the standard
  wires, each only where it is missing: ``hands → hands.layer.hands``,
  ``hands.layer → output.all.hands`` and ``hands.layer → output.all.guide``.
  A layer that reaches an output another way (through an effect, say) is left
  as it is wired.

"Loads" is the app's own load and save, headless, in a scratch library
(`headless.resave`): a file that does not load is named and left as it is.
Each changed patch is loaded again from what would be written, and must give
the same load notes as before; one that doesn't is named and not written.
A file is written in the app's own layout (`loadable.dumps`), so a file the
app last saved diffs only in the hands' values and wires; a patch already at
the look with its layer wired is not touched, and a second run finds nothing.

The default is a **dry run**: every file is read and every change worked out
and printed, nothing written. ``--apply`` first copies the whole library to
``<home>/library-backup-<stamp>/`` (`migrate_library.backup`, never inside the
library; the run stops if the copy is short), says where, then writes each
file atomically.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import ghost
from hyperspace.graph import (
    GraphError,
    reaches,
    read_graph,
    wired_hands_name,
    wired_layer_name,
)

# the standard wires of the hands' layer (as every corpus patch has them)
LAYER = wired_layer_name(1)
STANDARD_WIRES = ((wired_hands_name(1), f"{LAYER}.hands"),
                  (LAYER, "output.all.hands"),
                  (LAYER, "output.all.guide"))
LOADABLE_SCHEMA = "hyperspace.loadable/"


def _migrate_library():
    """tools/migrate_library.py as a module: its home, library, file walk,
    backup and atomic write are this tool's too (as tools/retaper_routes.py)."""
    if "migrate_library" in sys.modules:
        return sys.modules["migrate_library"]
    spec = importlib.util.spec_from_file_location("migrate_library",
                                                  ROOT / "tools" / "migrate_library.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_library"] = mod
    spec.loader.exec_module(mod)
    return mod


@dataclass
class Change:
    """What one loadable patch's rewrite does, or would do."""

    file: str
    skipped: str = ""                                  # left as it is, and why
    values: list[str] = field(default_factory=list)   # one entry per value that moved
    wires: list[str] = field(default_factory=list)    # one entry per wire added
    text: str = ""                                     # what a write puts there

    @property
    def changed(self) -> bool:
        return not self.skipped and bool(self.values or self.wires)


def hands_prefixes(section) -> list[str]:
    """The param prefixes of the graph's hands nodes: ``ghost`` (hands 1 is
    always there), then ``ghost.<n>`` for each extra ``hands`` entry."""
    out = [ghost.prefix(1)]
    nodes = section.get("nodes", []) if isinstance(section, dict) else []
    for e in nodes if isinstance(nodes, list) else ():
        if isinstance(e, dict) and e.get("kind") == "hands":
            n = e.get("instance", 1)
            if isinstance(n, int) and not isinstance(n, bool) and n >= 2:
                p = ghost.prefix(n)
                if p not in out:
                    out.append(p)
    return out


def look(doc: dict) -> tuple[dict, list[str]]:
    """`doc` with every hands node's look set to `ghost.SHOW_LOOK`: (the
    document, one line per value that moved)."""
    out = copy.deepcopy(doc)
    raw = out.get("values")
    # (read as `LoadedPatch.load_doc` reads it: missing or null is none, pairs a map;
    # anything else raises, and `plan` names the file and leaves it)
    values = raw if isinstance(raw, dict) else dict(raw or {})
    moved = []
    for pre in hands_prefixes(out.get("graph")):
        for k, v in ghost.SHOW_LOOK.items():
            key = f"{pre}.{k}"
            if key not in values or values[key] != v or type(values[key]) is not type(v):
                moved.append(f"{key} {values.get(key, '(none)')!r} → {v!r}")
                values[key] = v
    # written back in the file's own shape: the load reads a pairs list and a map
    # differently in places (`params.pan_world` converts only a map's pan)
    out["values"] = ([[k, v] for k, v in values.items()] if isinstance(raw, list)
                     else values)
    return out, moved


def wire_layer(doc: dict, effects) -> tuple[dict, list[str]]:
    """`doc` (changed in place) with its hands layer given the standard
    wires when it reaches no output: (the document, one line per wire added).
    A graph this build cannot read raises `GraphError`."""
    section = doc.get("graph")
    spec = read_graph(section, effects=effects)
    if not spec.wired or LAYER in reaches(spec):
        return doc, []
    wires = section.setdefault("wires", [])
    have = {(w.get("from"), w.get("to")) for w in wires if isinstance(w, dict)}
    fed = any(dst == f"{LAYER}.hands" for _, dst in have)   # (another hands node may feed it)
    added = []
    for src, dst in STANDARD_WIRES:
        if dst == f"{LAYER}.hands" and fed:
            continue
        if (src, dst) not in have:
            wires.append({"from": src, "to": dst})
            added.append(f"{src} → {dst}")
    # (what was added must read, and reach: else it is no fix)
    after = read_graph(section, effects=effects)
    if after.notes and len(after.notes) > len(spec.notes):
        raise GraphError(f"the standard wires don't read here: {'; '.join(after.notes)}")
    if LAYER not in reaches(after):
        raise GraphError("the standard wires don't reach an output here")
    return doc, added


def loads(path: Path, scratch: Path, library: Path) -> tuple[list[str], dict]:
    """The app's load notes for loadable patch file `path`, and what it saves
    from it less the hands' look and the graph (`landed`) — (raises what the
    load raises for one that does not load)."""
    from hyperspace import headless
    data, notes, _name = headless.resave(path, scratch, library=library)
    return notes, landed(json.loads(data))


def landed(doc: dict) -> dict:
    """A saved document less what this tool sets: every hands node's look
    values and the graph section (whose wires it may add). What remains must
    be the same before and after a change, or the change moved something else."""
    out = {k: v for k, v in doc.items() if k != "graph"}
    values = out.get("values")
    if isinstance(values, dict):
        out["values"] = {k: v for k, v in values.items()
                         if not (k.startswith(ghost.GROUP + ".")
                                 and k.rpartition(".")[2] in ghost.SHOW_LOOK)}
    return out


def plan(path: Path, library: Path, effects, scratch: Path, *, file: str = "") -> Change:
    """One file, read only: what a write would do to it."""
    from hyperspace.library import LibraryError
    from hyperspace.loadable import dumps

    c = Change(file or path.name)
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        c.skipped = f"not read: {e}"
        return c
    from hyperspace.patches import LOADABLE_SHAPE, shape_of
    if not isinstance(doc, dict) or shape_of(doc) != LOADABLE_SHAPE:
        c.skipped = "not a loadable patch"
        return c
    if not str(doc.get("schema", "")).startswith(LOADABLE_SCHEMA):
        # (an older whole patch: the app migrates its graph on load, so its raw
        # section is not what runs — migrate the library first, then run this)
        c.skipped = (f"an older schema ({doc.get('schema')}): run tools/migrate_library.py "
                     "first, then this")
        return c
    failed = (LibraryError, ValueError, KeyError, TypeError, OSError, RuntimeError)
    try:
        before = loads(path, scratch / "before", library)
    except failed as e:
        c.skipped = f"does not load: {e}"
        return c
    try:
        out, c.values = look(doc)
        out, c.wires = wire_layer(out, effects)
    except GraphError as e:
        c.skipped = f"graph: {e}"
        return c
    except Exception as e:  # noqa: BLE001 — one odd file is named and left, never the run's end
        c.skipped = f"not changed: {type(e).__name__}: {e}"
        return c
    if not c.changed:
        return c
    c.text = dumps(out)
    trial = scratch / "after" / path.name
    trial.parent.mkdir(parents=True, exist_ok=True)
    trial.write_text(c.text)
    try:
        after = loads(trial, scratch / "after-load", library)
    except failed as e:
        c.skipped = f"does not load once changed: {e}"
        return c
    if after[0] != before[0]:
        c.skipped = ("its load notes change: "
                     + "; ".join(sorted(set(after[0]) ^ set(before[0]))))
    elif after[1] != before[1]:
        moved = sorted(k for k in set(after[1]) | set(before[1])
                       if after[1].get(k) != before[1].get(k))
        c.skipped = f"the load lands something else differently ({', '.join(moved)})"
    return c


def line(c: Change) -> str:
    if c.skipped:
        return f"{c.file:52s} left: {c.skipped}"
    if not c.changed:
        return f"{c.file:52s} already the show look"
    said = f"{len(c.values)} value(s)"
    if c.wires:
        said += f", wired: {', '.join(c.wires)}"
    return f"{c.file:52s} {said}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path, nargs="?", default=None,
                    help="the library, or its loadable/ folder (as --library)")
    ap.add_argument("--library", type=Path, default=None,
                    help="the library folder (default: config.toml's [library] path, else the home)")
    ap.add_argument("--apply", action="store_true",
                    help="back the library up, then write; the default is a dry run")
    ap.add_argument("--values", action="store_true", help="say every value that moves")
    a = ap.parse_args(argv)
    ml = _migrate_library()
    home = ml.machine_home()
    if a.folder is not None and a.library is not None and a.folder != a.library:
        ap.error("give the library once: FOLDER or --library")
    library = (a.folder or a.library or ml.configured_library(home)).expanduser()
    if library.name in (ml.LOADABLE, ml.OLD_LOADABLE) and not (
            (library / ml.LOADABLE).is_dir() or (library / ml.OLD_LOADABLE).is_dir()):
        library = library.parent       # (its loadable/ folder named: the library is above it)
    files = ml.loadable_files(library)
    if not files:
        print(f"no loadable patches under {library / ml.LOADABLE} or {library / ml.OLD_LOADABLE}")
        return 1
    if a.apply:
        running, said = ml.app_running()
        if running:
            print(f"{said}: quit it first (a save would write the old look back)")
            return 1
    from hyperspace.fx import FxState
    effects = set(FxState().files)
    look_said = ", ".join(f"{k} {v!r}" for k, v in ghost.SHOW_LOOK.items())
    print(f"the show look: {look_said} ({ghost.STYLES[ghost.SHOW_LOOK['style']]}, "
          f"{ghost.MATERIALS[ghost.SHOW_LOOK['material']]})")
    todo: list[tuple[Path, Change]] = []
    with tempfile.TemporaryDirectory(prefix="hands-look-") as tmp:
        for i, p in enumerate(files):
            c = plan(p, library, effects, Path(tmp) / str(i), file=ml.under_folder(library, p))
            todo.append((p, c))
            print(line(c))
            if a.values and c.changed:
                for v in c.values:
                    print(f"{'':54s}{v}")
    touched = [(p, c) for p, c in todo if c.changed]
    left = [c for _, c in todo if c.skipped]
    print(f"\n{len(files)} files: {len(touched)} {'to write' if a.apply else 'would be written'} "
          f"({sum(1 for _, c in touched if c.wires)} wired), "
          f"{len(files) - len(touched) - len(left)} already the show look, {len(left)} left"
          + ("" if a.apply else "  (dry run: nothing written; add --apply)"))
    if not a.apply or not touched:
        return 0
    print(f"backup: {ml.backup(library, home)}")
    for p, c in touched:
        ml.write(p, c.text.encode())
    print(f"written: {len(touched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
