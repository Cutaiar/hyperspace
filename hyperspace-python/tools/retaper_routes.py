#!/usr/bin/env python3
"""Measure a library's route depths along the new effect tapers, once
(wave 0 T1: coarse and fine control through tapers).

    uv run python tools/retaper_routes.py [--library PATH] [--rows] [--write]

**The owner runs this on the library before the next show**, with both
Macs on this build (`--write`; a dry run first). Until then an old preset
is read as it was at every load (`params.retaper_depths` in
`Presets.load_doc`), so nothing is lost; this rewrite makes it permanent,
with a backup, so the whole library moves together.

Why: each effect's `speed` (linear −8 … +8) and its amount-type params
(linear 0 … hi) are on tapers now — `fx.T_SPEED`, a signed exponential
with the stop in the middle, and `fx.amount_taper`, a zero-safe log — so
a knob reaches 0.05× or 5 % as easily as 0.5. A route's depth is in the
target's normalised units, and the tapers sit between those units and the
real ones, so the same depth number now means another real-unit change
(triage addendum, tension 8). Bases are stored in real units and are
safe; depths are not. For each preset in ``<library>/presets/*.json`` and
each patch in ``<library>/patches/*.json`` (not ``trash/``, not a backup,
not a dot-file) without the marker ``units["fx.depth"] == "taper"``:

- every ``push`` row onto a retapered param keeps the real value a full
  push reaches **from the row's base** (the preset's own value of the
  param, or the effect's default where it names none): the new depth is
  the taper distance from that base to that value. Exact at rest and at
  full push about that base — the tool says "about <base>" on each — and
  not between, where the taper's curve stands in for the line; a push
  from a base of 0 keeps its reach but its first part now does little;
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
  left as it is;
- the document is then marked, so a second run finds nothing to do.

Rows the preset carries onto other params, depth subscribers, ``scale``
and ``rest`` do not move. A changed row is written as the app writes one
(`Binding.to_json`: a depth of exactly 1.0 omitted, the keys in its
order), and the document as the app saves it (`preset.dumps`, the rows
one a line; a patch as GRAPH writes one), so a diff shows only the rows
that moved and the marker. Every unmarked
document is written, marker at least. Performer rows in the session table
(``bindings.json``) and the shows (``shows/*.json``) onto such params are
**reported, not rewritten**: a session row has no base of its own to
measure against; edit any by hand.

The default is a **dry run**: one line per file with what would change.
``--write`` first copies the whole library folder to
``~/Hyperspace/library-backup-<stamp>/`` (the machine's home, never
inside the library; `migrate_library.backup`) and says where, then
writes. The test corpus (``tests/corpus/presets``) was rewritten with
this tool in the PR that brought the tapers, so the goldens draw the
migrated depths; it is never touched again by a run on a library.
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

from hyperspace.fx import FxState, retaper_of
from hyperspace.params import DEPTH_TAPER, DEPTH_UNIT, UNITS_KEY, retaper_depths
from hyperspace.preset import dumps as preset_text
from hyperspace.routing import MOD_OPS, Binding

PATCHES = "patches"
SHOWS = "shows"
BINDINGS = "bindings.json"


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
    """What one document's rewrite did."""
    file: str
    kind: str = "preset"      # or "patch"
    marked: bool = False      # already measured along the tapers: nothing to do
    skipped: str = ""         # not a document this tool reads
    rows: list[str] = field(default_factory=list)   # one line per row or sub that moved

    @property
    def changed(self) -> bool:
        """Whether a write would change the file: a row moved, or the marker is new."""
        return not self.marked and not self.skipped


def marked(doc: dict) -> bool:
    units = doc.get(UNITS_KEY)
    return isinstance(units, dict) and units.get(DEPTH_UNIT) == DEPTH_TAPER


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
    for section in ("routes", "desk"):
        before, after = doc.get(section), out.get(section)
        if not (isinstance(before, list) and isinstance(after, list)):
            continue
        for i, (a, b) in enumerate(zip(before, after, strict=True)):
            if a != b and isinstance(b, dict):
                after[i] = Binding.from_json(b).to_json()
    return out, c


def rewrite(path: Path, files: dict, *, write: bool, ml, kind: str = "preset") -> Change:
    """One file: read, retaper, and (with `write`) write it back as the app
    writes it. A file that is not a document is skipped."""
    try:
        doc = json.loads(path.read_text())
    except ValueError as e:
        return Change(path.name, kind, skipped=f"not JSON: {e}")
    if not isinstance(doc, dict):
        return Change(path.name, kind, skipped="not a document")
    out, c = retaper(doc, files, file=path.name, kind=kind)
    if write and c.changed:
        ml.write(path, text(out, kind).encode())
    return c


def text(doc: dict, kind: str = "preset") -> str:
    """`doc` as the app writes one of its `kind`: a preset through
    `preset.dumps` (the rows one a line), a patch as GRAPH saves it
    (``json.dumps(indent=1)``)."""
    return preset_text(doc) if kind == "preset" else json.dumps(doc, indent=1) + "\n"


def session_rows(library: Path, files: dict) -> list[str]:
    """Performer rows onto retapered params in the session table and the
    shows — said, never rewritten (no base of their own to measure by)."""
    found: list[str] = []
    paths = [library / BINDINGS]
    shows = library / SHOWS
    if shows.is_dir():
        paths += sorted(p for p in shows.glob("*.json") if not p.name.startswith("."))
    for path in paths:
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text())
        except ValueError:
            continue
        rows = doc.get("bindings") if isinstance(doc, dict) else None
        if rows is None and isinstance(doc, dict):
            rows = (doc.get("session") or {}).get("bindings") if isinstance(
                doc.get("session"), dict) else None
        for row in rows if isinstance(rows, list) else ():
            if not isinstance(row, dict) or row.get("op") not in MOD_OPS:
                continue
            if retaper_of(str(row.get("target", "")), files) is not None:
                found.append(f"{path.name}: {row.get('source')} → {row['target']} "
                             f"{row['op']} {row.get('value', 1.0):g}")
    return found


def line(c: Change) -> str:
    if c.skipped:
        return f"{c.file:44s} skipped: {c.skipped}"
    if c.marked:
        return f"{c.file:44s} already along the tapers"
    if not c.rows:
        return f"{c.file:44s} no depth onto a retapered param: marker only"
    return f"{c.file:44s} {len(c.rows):3d} moved"


def patch_files(library: Path) -> list[Path]:
    folder = library / PATCHES
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
    patches = patch_files(library)
    if not presets and not patches:
        print(f"no presets under {library / ml.PRESETS}")
        return 1
    files = FxState().files
    if a.write:
        print(f"backup: {ml.backup(library, home)}")
    changes = [rewrite(p, files, write=a.write, ml=ml) for p in presets]
    changes += [rewrite(p, files, write=a.write, ml=ml, kind="patch") for p in patches]
    for c in changes:
        print(line(c))
        if a.rows:
            for r in c.rows:
                print(f"{'':46s}{r}")
    touched = [c for c in changes if c.changed]
    moved = sum(len(c.rows) for c in touched)
    print(f"\n{len(presets)} presets, {len(patches)} patches: {len(touched)} "
          f"{'written' if a.write else 'would be written'} ({moved} rows moved, "
          f"{sum(1 for c in touched if not c.rows)} marker only), "
          f"{sum(1 for c in changes if c.marked)} already along the tapers, "
          f"{sum(1 for c in changes if c.skipped)} skipped"
          + ("" if a.write else "  (dry run: nothing written; add --write)"))
    said = session_rows(library, files)
    if said:
        print(f"\n{len(said)} session rows onto retapered params, not rewritten (no base to "
              "measure by; edit by hand):")
        for s in said:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
