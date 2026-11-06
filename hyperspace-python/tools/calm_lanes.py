#!/usr/bin/env python3
"""Calm a library's analyzer routes, once: every band row a spring, pushing
no more than a new route would.

    uv run python tools/calm_lanes.py [--library PATH] [--cap DEPTH] [--apply]

The owner, 2026-11-02, after the show of 2026-10-30: "all existing presets
need to have sensible mappings for the audio analyzer cables … whatever
the default is now, just use that as an upper bound for what audio is
allowed to push on its controls, and then just update all the presets
accordingly. Make sure that they're all using spring controls as well."
PRs #301 and #305 set those defaults for *new* routes only (a saved row
keeps its own depth and feel), and presets here are made by copying and
editing older ones, so the old rows would have lived on for ever.

For each preset in ``<library>/presets/*.json`` (not ``trash/``, not a
backup, not a dot-file), every route whose source is an analyzer lane
(the ``lane`` scheme, ``lane:<k>``) is rewritten:

- **depth**: a ``push`` keeps its sign and is held to ``--cap``
  (`learn.LANE_DEPTH`, the depth a new band route lands at); a
  ``position`` row (the band as the param's fader, its base ignored)
  becomes a ``push`` about the base at the same held depth, so the base
  shows again between beats;
- **feel**: a row with no feel (``auto``, which reads OFF for a lane) or
  with the old bouncy spring default (`motion.Motion("spring")`'s
  knobs, which the feel chip used to land on) gets the smooth spring every
  new route gets (`motion.DEFAULT_ROUTE_FEEL`); a spring the owner tuned by
  hand, or a follow, is kept as it is.

Nothing else in the file moves: the document is read and written back
as the app writes it (``json.dumps(indent=1)``), so a diff shows only the
rows that changed. A preset with no lane route is not written. The run
is idempotent.

The default is a **dry run**: one line per preset with what would change.
``--apply`` first copies the whole library folder to
``~/Hyperspace/library-backup-<stamp>/`` (the machine's home, never
inside the library; `migrate_library.backup`) and says where, then
writes. The test corpus (``tests/corpus/presets``) is test data behind
the goldens and is never touched by this tool.
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

from hyperspace.learn import LANE_DEPTH
from hyperspace.motion import DEFAULT_ROUTE_FEEL, Motion

LANE_SCHEME = "lane"


def _migrate_library():
    """tools/migrate_library.py as a module: its home, library, file list,
    backup and atomic write are this tool's too."""
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
    """What one preset's rewrite did."""
    file: str
    lanes: int = 0            # lane rows seen
    capped: int = 0           # pushes held to the cap
    faders: int = 0           # position rows made pushes
    sprung: int = 0           # rows given the smooth spring
    kept_feel: int = 0        # rows whose own spring or follow was kept
    rows: list[str] = field(default_factory=list)   # "target: what" per row changed

    @property
    def changed(self) -> bool:
        return bool(self.capped or self.faders or self.sprung)


def _old_default_spring(m: dict | None) -> bool:
    """The feel chip's old landing: `Motion("spring")` with its default
    knobs, in either spelling (duration/bounce, or the older hz/damp)."""
    if not m or m.get("mode") != "spring":
        return False
    try:
        return Motion.from_json(m).to_json() == Motion("spring").to_json()
    except (TypeError, ValueError, KeyError):
        return False


def calm(doc: dict, *, cap: float = LANE_DEPTH, file: str = "") -> Change:
    """Rewrite `doc`'s lane routes in place (see the module doc) and say
    what moved. `doc` is the preset as loaded from its file."""
    c = Change(file)
    smooth = DEFAULT_ROUTE_FEEL.to_json()
    for row in doc.get("routes", []):
        source = str(row.get("source", ""))
        if source.partition(":")[0] != LANE_SCHEME:
            continue
        c.lanes += 1
        what: list[str] = []
        op = row.get("op")
        value = float(row.get("value", 1.0))
        if op == "position":
            row["op"] = "push"
            held = max(-cap, min(cap, value))
            row["value"] = held
            c.faders += 1
            what.append(f"fader {value:g} → push {held:g}")
        elif op == "push" and abs(value) > cap:
            held = cap if value > 0 else -cap
            row["value"] = held
            c.capped += 1
            what.append(f"push {value:g} → {held:g}")
        feel = row.get("motion")
        if feel is None or _old_default_spring(feel):
            row["motion"] = dict(smooth)
            c.sprung += 1
            what.append("spring" if feel is None else "bouncy → smooth")
        else:
            c.kept_feel += 1
        if what:
            c.rows.append(f"{row.get('target', '?')}: {', '.join(what)}")
    return c


def rewrite(path: Path, *, cap: float, apply: bool, ml) -> Change:
    """One preset file: read, calm, and (with `apply`) write it back as the
    app writes it. A file that is not a preset document is skipped."""
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict) or not isinstance(doc.get("routes", []), list):
        return Change(path.name)
    c = calm(doc, cap=cap, file=path.name)
    if apply and c.changed:
        ml.write(path, (json.dumps(doc, indent=1) + "\n").encode())
    return c


def line(c: Change) -> str:
    if not c.lanes:
        return f"{c.file:44s} no lane routes"
    if not c.changed:
        return f"{c.file:44s} {c.lanes:3d} lane rows, already calm"
    return (f"{c.file:44s} {c.lanes:3d} lane rows: {c.capped} capped, {c.faders} faders → push, "
            f"{c.sprung} sprung, {c.kept_feel} feels kept")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--library", type=Path, default=None,
                    help="the library folder (default: config.toml's [library] path, else the home)")
    ap.add_argument("--cap", type=float, default=LANE_DEPTH,
                    help=f"the most a band may push, in norm units (default {LANE_DEPTH})")
    ap.add_argument("--apply", action="store_true",
                    help="write the files (after a backup); the default is a dry run")
    ap.add_argument("--rows", action="store_true", help="say every row that changes")
    a = ap.parse_args(argv)
    ml = _migrate_library()
    home = ml.machine_home()
    library = a.library or ml.configured_library(home)
    files = ml.preset_files(library)
    if not files:
        print(f"no presets under {library / ml.LOADABLE}")
        return 1
    if a.apply:
        print(f"backup: {ml.backup(library, home)}")
    changes = [rewrite(p, cap=a.cap, apply=a.apply, ml=ml) for p in files]
    for c in changes:
        print(line(c))
        if a.rows:
            for r in c.rows:
                print(f"{'':46s}{r}")
    touched = [c for c in changes if c.changed]
    print(f"\n{len(files)} presets, {len(touched)} {'written' if a.apply else 'would change'}: "
          f"{sum(c.capped for c in touched)} capped, {sum(c.faders for c in touched)} faders → push, "
          f"{sum(c.sprung for c in touched)} sprung, {sum(c.kept_feel for c in changes)} feels kept"
          + ("" if a.apply else "  (dry run: nothing written; add --apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
