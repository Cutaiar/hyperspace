#!/usr/bin/env python3
"""Measure a library's route depths along the new effect tapers, once
(wave 0 T1: coarse and fine control through tapers).

    uv run python tools/retaper_routes.py [--library PATH] [--rows] [--write]

**The owner runs this on the library before the next show**, with both
Macs on this build (a dry run first, then `--write`). Until then every
old file is read as it was at each load (`params.retaper_depths` in
`Presets.load_doc`, `patches.read`, the desk templates' expansion and
`Bindings.from_json`), so nothing is lost; this rewrite makes it
permanent, with a backup, so the whole library moves together.

Why: each effect's `speed` (linear −8 … +8) and its amount-type params
(linear 0 … hi) are on tapers now — `fx.T_SPEED`, a signed exponential
with the stop in the middle, and `fx.amount_taper`, a zero-safe log — so
a knob reaches 0.05× or 5 % as easily as 0.5. A route's depth is in the
target's normalised units, and the tapers sit between those units and the
real ones, so the same depth number now means another real-unit change
(triage addendum, tension 8). Bases are stored in real units and are
safe; depths are not. The documents visited, each without the marker
``units["fx.depth"] == "taper"`` (a marked one is left as it is, so a
second run finds nothing to do):

- the presets, ``<library>/presets/*.json``;
- the patches, ``<library>/patches/*.json`` (a patch saved on this build
  carries the marker; `patches.read` converts an older one when it is
  spawned);
- the desk templates, ``<library>/desk/*.json`` (expanded into a preset's
  desk at load; a `set` row's value is a norm);
- the session table, ``<home>/bindings.json`` — the machine home's, not
  the library's — whose `set` rows (and any hand-edited performer row) are
  measured about the effect's default, there being no base of its own.
  A show holds no rows (its `session` is a snapshot of session params),
  so there is nothing to visit there.

In each (not ``trash/``, not a backup, not a dot-file):

- every ``push`` row onto a retapered param keeps the real value a full
  push reaches **from the row's base** (the document's own value of the
  param, or the effect's default where it names none): the new depth is
  the taper distance from that base to that value. Exact at rest and at
  full push about that base — the tool says "about <base>" on each — and
  not between, where the taper's curve stands in for the line; a push
  from a base of 0 keeps its reach but its first part now does little. A
  push that over- or undershoots the range from its base (a negative push
  from 0) keeps its sign and carries the overshoot over in norm as it was,
  so no row that had a depth is written 0 — said "overshoots";
- every ``position`` row (and a ``set`` row) keeps the real value the
  source lands at full throw: the new depth is that value's position on
  the taper. Exact at the top; below it the source is the param's new
  fader, which is what a position row means;
- a macro's base subscriber on such a param has its ``from`` / ``to``
  (norms) moved as a position's depth is: each end lands the real value
  it did. A macro's throw is linear in norm, so between the ends it now
  runs the taper's curve — a macro resting mid-throw lands the base
  somewhere else at load, and two macros that agreed on a shared base
  at their rests no longer do. The tool names every such sub; listen to
  those presets and re-set the ends by ear;
- a row whose ``value`` is missing is read as 1.0 (`Binding.value`'s
  default, which `to_json` omits); a row whose value is not a number is
  left as it is and named ("left");
- the document is then marked.

Rows onto other params, depth subscribers, ``scale`` and ``rest`` do not
move. A changed row is written as the app writes one (`Binding.to_json`:
a depth of exactly 1.0 omitted, the keys in its order), and each document
as the app saves its kind (a preset through `preset.dumps`, the rows one
a line; a patch and a desk template as the library writes them,
``json.dumps(indent=1)``; the session table through `routing.dumps_doc`),
so a diff shows only the rows that moved and the marker. Every unmarked
document is written, marker at least.

The default is a **dry run**: every file is read and every change worked
out and printed before anything is written, one line per file. ``--write``
then copies the whole library folder to ``~/Hyperspace/library-backup-
<stamp>/`` (the machine's home, never inside the library;
`migrate_library.backup`), keeps ``bindings.json`` beside itself as the
app does before it rewrites it (`routing.backup`, ``bindings.json.bak-v3``),
says where, and writes. The test corpus (``tests/corpus/presets``) was
rewritten with this tool in the PR that brought the tapers, so the goldens
draw the migrated depths; it is never touched again by a run on a library.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace import routing
from hyperspace.fx import FxState, retaper_of
from hyperspace.params import DEPTH_TAPER, DEPTH_UNIT, UNITS_KEY, retaper_depths
from hyperspace.preset import dumps as preset_text

PATCHES = "patches"
DESK = "desk"
KINDS = ("preset", "patch", "desk", "bindings")
_OPS = ("push", "position", "set")
_SECTIONS = ("routes", "desk", "bindings")


def _migrate_library():
    """tools/migrate_library.py as a module: its home, library, file list,
    backup and atomic write are this tool's too (as tools/calm_lanes.py)."""
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
    """What one document's rewrite did, or would do."""
    file: str
    kind: str = "preset"
    marked: bool = False      # already measured along the tapers: nothing to do
    skipped: str = ""         # not a document this tool reads
    rows: list[str] = field(default_factory=list)   # one line per row or sub that moved
    left: list[str] = field(default_factory=list)   # rows onto such params left as they are
    text: str = ""            # what a write puts there

    @property
    def changed(self) -> bool:
        """Whether a write would change the file: a row moved, or the marker is new."""
        return not self.marked and not self.skipped


def marked(doc: dict) -> bool:
    units = doc.get(UNITS_KEY)
    return isinstance(units, dict) and units.get(DEPTH_UNIT) == DEPTH_TAPER


def _number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def left_rows(doc: dict, files: dict) -> list[str]:
    """The rows onto retapered params whose value is not a number — left as
    they are by `retaper_depths`, named here (a hand-edited file)."""
    out: list[str] = []
    for section in _SECTIONS:
        part = doc.get(section)
        for row in (part if isinstance(part, list) else ()):
            if not isinstance(row, dict) or row.get("op") not in _OPS:
                continue
            value = row.get("value", 1.0)
            if not _number(value) and retaper_of(str(row.get("target", "")), files) is not None:
                out.append(f"{section} {row.get('source', '?')} → {row.get('target')}: "
                           f"value {value!r} is not a number — left")
    return out


def retaper(doc: dict, files: dict, *, file: str = "", kind: str = "preset"
            ) -> tuple[dict, Change]:
    """`doc` with its depths measured along the tapers (`retaper_depths`),
    each row that moved written as `Binding.to_json` writes it: (the
    document to write, what moved). A marked document comes back itself."""
    c = Change(file, kind)
    if marked(doc):
        c.marked = True
        return doc, c
    out, c.rows = retaper_depths(doc, files)
    c.left = left_rows(doc, files)
    for section in _SECTIONS:
        before, after = doc.get(section), out.get(section)
        if not (isinstance(before, list) and isinstance(after, list)):
            continue
        for i, (a, b) in enumerate(zip(before, after, strict=True)):
            if a != b and isinstance(b, dict):
                after[i] = routing.Binding.from_json(b).to_json()
    c.text = text(out, kind)
    return out, c


def text(doc: dict, kind: str = "preset") -> str:
    """`doc` as the app writes one of its `kind`: a preset through
    `preset.dumps` (the rows one a line); a patch or a desk template as the
    library writes them (``json.dumps(indent=1)``); the session table
    through `routing.dumps_doc` (a hand-edited file with no `profile` gets
    the default's, which the app would write too)."""
    if kind == "preset":
        return preset_text(doc)
    if kind == "bindings":
        return routing.dumps_doc({"profile": "apc40", **doc})
    return json.dumps(doc, indent=1) + "\n"


def plan(path: Path, files: dict, *, kind: str = "preset") -> Change:
    """One file, read only: what a write would do to it. A file that is
    not a document is skipped."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return Change(path.name, kind, skipped=f"not read: {e}")
    if not isinstance(doc, dict):
        return Change(path.name, kind, skipped="not a document")
    return retaper(doc, files, file=path.name, kind=kind)[1]


def line(c: Change) -> str:
    what = f"{c.kind + ' ' if c.kind != 'preset' else ''}{c.file}"
    if c.skipped:
        return f"{what:44s} skipped: {c.skipped}"
    if c.marked:
        return f"{what:44s} already along the tapers"
    if not c.rows and not c.left:
        return f"{what:44s} no depth onto a retapered param: marker only"
    return f"{what:44s} {len(c.rows):3d} moved" + (f", {len(c.left)} left" if c.left else "")


def json_files(folder: Path) -> list[Path]:
    """``folder/*.json``, a dot-file (a write's temp file) and a backup
    (``.bak-``) left out; none for no folder."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.json")
                  if p.is_file() and not p.name.startswith(".") and ".bak-" not in p.name)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--library", type=Path, default=None,
                    help="the library folder (default: config.toml's [library] path, else the home)")
    ap.add_argument("--write", action="store_true",
                    help="write the files (after a backup); the default is a dry run")
    ap.add_argument("--rows", action="store_true", help="say every row that moves")
    a = ap.parse_args(argv)
    ml = _migrate_library()
    home = ml.machine_home()
    library = (a.library or ml.configured_library(home)).expanduser()
    presets = ml.preset_files(library)
    patches = json_files(library / PATCHES)
    desks = json_files(library / DESK)
    table = home / routing.FILE
    if not presets and not patches and not desks:
        print(f"no presets under {library / ml.PRESETS}")
        return 1
    files = FxState().files
    # every change worked out before anything is written
    todo: list[tuple[Path, Change]] = [(p, plan(p, files)) for p in presets]
    todo += [(p, plan(p, files, kind="patch")) for p in patches]
    todo += [(p, plan(p, files, kind="desk")) for p in desks]
    if table.is_file():
        todo.append((table, plan(table, files, kind="bindings")))
    for _, c in todo:
        print(line(c))
        if a.rows:
            for r in c.rows:
                print(f"{'':46s}{r}")
        for r in c.left:
            print(f"{'':46s}{r}")
    touched = [c for _, c in todo if c.changed]
    moved = sum(len(c.rows) for c in touched)
    print(f"\n{len(presets)} presets, {len(patches)} patches, {len(desks)} desk templates"
          f"{', bindings.json' if table.is_file() else ''}: {len(touched)} "
          f"{'written' if a.write else 'would be written'} ({moved} rows moved, "
          f"{sum(1 for c in touched if not c.rows)} marker only, "
          f"{sum(len(c.left) for _, c in todo)} left), "
          f"{sum(1 for _, c in todo if c.marked)} already along the tapers, "
          f"{sum(1 for _, c in todo if c.skipped)} skipped"
          + ("" if a.write else "  (dry run: nothing written; add --write)"))
    if not a.write:
        return 0
    if any(c.changed and c.kind != "bindings" for _, c in todo):
        print(f"backup: {ml.backup(library, home)}")
    for path, c in todo:
        if not c.changed:
            continue
        if c.kind == "bindings":
            schema = str(json.loads(path.read_text()).get("schema", "")).rpartition("/")[2] or "0"
            if routing.backup(path, schema) is None:
                print(f"{path.name}: not rewritten — no backup could be made")
                continue
        ml.write(path, c.text.encode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
