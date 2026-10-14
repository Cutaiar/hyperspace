#!/usr/bin/env python3
"""Copy an existing library into a shared folder, once (plan 25 D8).

    uv run python tools/move_library.py DEST [--from HOME] [--dry-run]

Copies the library — ``presets/``, ``projects/``, every module-preset group
folder (``fx/``, ``dream/``, ``band/`` …) and ``hidden.json`` — from HOME
(default: ``$HYPERSPACE_HOME``, else ``~/Hyperspace``) into DEST, which it
creates if missing. Then add the two lines it prints to HOME's config.toml
and start Hyperspace: the library is read and written in DEST from then on.

It never overwrites: a file DEST already has is left alone — identical is
``have``, different is ``KEPT THEIRS`` (yours stays in HOME, at the path it
prints). ``hidden.json`` is a set, so DEST gets the union of both lists.
The machine files (config.toml, bindings.json and its backups, hands.json,
windows.json, last_show, logs, weights/), the trash, the legacy bindings/
folder, backups, dot-files and ``.git`` stay behind. Nothing in HOME is
deleted or edited, and config.toml is never touched.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HIDDEN = "hidden.json"
HIDDEN_SCHEMA = "hyperspace.hidden/1"
# folders of the home that are not the library (D3), or not to be copied
SKIP_DIRS = {"weights", "trash", "bindings"}


def _home() -> Path:
    sys.path.insert(0, str(HERE))
    from hyperspace import library
    return Path(library.home())


def files(root: Path) -> list[Path]:
    """The library documents under `root`, relative: every ``<folder>/*.json``
    one level down — backups, dot-files and the machine's folders left out."""
    out: list[Path] = []
    if not root.is_dir():
        return out
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        if folder.name in SKIP_DIRS or folder.name.startswith("."):
            continue
        for f in sorted(folder.glob("*.json")):
            if f.name.startswith(".") or ".bak-" in f.name or not f.is_file():
                continue
            out.append(f.relative_to(root))
    return out


def _hidden(path: Path) -> list[str] | None:
    """`hidden.json`'s stems, or None when there is no readable list."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    stems = doc.get("presets") if isinstance(doc, dict) else None
    if not isinstance(doc, dict) or doc.get("schema") != HIDDEN_SCHEMA or not isinstance(stems,
                                                                                         list):
        return None
    return [s for s in stems if isinstance(s, str) and s]


def move(dest: Path, home: Path, *, dry_run: bool = False,
         out=print) -> list[tuple[str, Path]]:
    """Copy `home`'s library into `dest`; returns (what happened, relative
    path) per file — "copied", "have" or "KEPT THEIRS" — and per
    ``hidden.json`` "hidden +N" / "hidden" (nothing to add)."""
    if not home.is_dir():
        raise SystemExit(f"move_library: {home} is not a folder")
    if dest.resolve() == home.resolve():
        raise SystemExit("move_library: DEST is HOME — nothing to move")
    done: list[tuple[str, Path]] = []
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    for rel in files(home):
        src, dst = home / rel, dest / rel
        data = src.read_bytes()
        if dst.exists():
            if dst.read_bytes() == data:
                done.append(("have", rel))
                out(f"have        {rel}")
            else:
                done.append(("KEPT THEIRS", rel))
                out(f"KEPT THEIRS {rel} — yours stays at {src}")
            continue
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "xb") as f:               # never over a file
                f.write(data)
        done.append(("copied", rel))
        out(f"copied      {rel}")
    mine = _hidden(home / HIDDEN)
    if mine is not None:
        theirs_path = dest / HIDDEN
        theirs = _hidden(theirs_path) if theirs_path.exists() else []
        rel = Path(HIDDEN)
        if theirs is None:
            done.append(("KEPT THEIRS", rel))
            out(f"KEPT THEIRS {HIDDEN} — not a {HIDDEN_SCHEMA} list there; yours stays at "
                f"{home / HIDDEN}")
        else:
            added = sorted(set(mine) - set(theirs))
            if added:
                if not dry_run:
                    tmp = theirs_path.with_name(f".{HIDDEN}.move.tmp")
                    tmp.write_text(json.dumps({"schema": HIDDEN_SCHEMA,
                                               "presets": sorted(set(mine) | set(theirs))},
                                              indent=1) + "\n")
                    tmp.replace(theirs_path)
                done.append((f"hidden +{len(added)}", rel))
                out(f"hidden      {HIDDEN} + {', '.join(added)}")
            else:
                done.append(("hidden", rel))
                out(f"have        {HIDDEN}")
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dest", type=Path, help="the shared folder (created if missing)")
    ap.add_argument("--from", dest="home", type=Path, default=None,
                    help="the home to copy from (default: $HYPERSPACE_HOME, else ~/Hyperspace)")
    ap.add_argument("--dry-run", action="store_true", help="say what would happen, write nothing")
    a = ap.parse_args(argv)
    home = (a.home if a.home is not None else _home()).expanduser()
    dest = a.dest.expanduser().resolve()
    done = move(dest, home, dry_run=a.dry_run)
    counts: dict[str, int] = {}
    for what, _ in done:
        key = what.split(" ")[0] if what.startswith("hidden") else what
        counts[key] = counts.get(key, 0) + 1
    print(("dry run: " if a.dry_run else "") + ", ".join(f"{n} {k}" for k, n in counts.items())
          if counts else "nothing to copy")
    print(f"\n{'Then' if a.dry_run else 'Now'} add these lines to {home / 'config.toml'} "
          "and start Hyperspace:\n")
    print("[library]")
    print(f'path = "{dest}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
