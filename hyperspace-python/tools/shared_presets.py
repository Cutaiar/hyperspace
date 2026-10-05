#!/usr/bin/env python3
"""Share a home's presets through the repo, and take someone else's.

    uv run python tools/shared_presets.py list    shared/dan-2026-10-04
    uv run python tools/shared_presets.py install shared/dan-2026-10-04 [--dry-run] [--shadow]
    uv run python tools/shared_presets.py export  shared/<you>-<date>

`install` copies a shared folder's presets, shows and module presets into
your own home (``~/Hyperspace``, or ``HYPERSPACE_HOME``). It never writes
over a file: one you already have under the same name is left alone and
said so (identical files are simply skipped). A file that would shadow a
factory one of the same name (a show called ``party``) is skipped unless
``--shadow`` is given. The running app picks new presets up within a
couple of seconds (the library is watched); no restart.

`export` copies your home's presets, shows and module presets into a new
folder under the repo for you to commit. It leaves out what is the
machine's: config.toml, bindings.json, hands.json, logs, backups, the
trash and the dream weights. It reads your home and writes only the
folder you name.

A shared folder mirrors a home: ``presets/*.json``, ``projects/*.hyp.json``
and one folder per module group (``fx/``, ``dream/``, ``band/`` …).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FACTORY = HERE / "hyperspace" / "library"
# the home's own files and folders that are never shared
SKIP_DIRS = {"weights", "trash", ".git"}
SKIP_FILES = {"RENAMED.txt"}


def _home() -> Path:
    sys.path.insert(0, str(HERE))
    from hyperspace import library
    return Path(library.home())


def files(root: Path) -> list[Path]:
    """The library files under `root`, relative: every ``<folder>/*.json``
    one level down, backups and the machine's own left out."""
    out = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIRS):
        for f in sorted(folder.glob("*.json")):
            if ".bak-" in f.name or f.name in SKIP_FILES:
                continue
            out.append(f.relative_to(root))
    return out


def plan(shared: Path, home: Path, *, shadow: bool = False) -> list[tuple[Path, str]]:
    """What `install` would do with each file: "copy", "have" (identical
    already), "kept yours" (a different file of that name is in the home)
    or "factory" (it would shadow a factory file; skipped without
    `shadow`)."""
    out = []
    for rel in files(shared):
        dst = home / rel
        if dst.exists():
            same = dst.read_bytes() == (shared / rel).read_bytes()
            out.append((rel, "have" if same else "kept yours"))
        elif (FACTORY / rel).exists() and not shadow:
            out.append((rel, "factory"))
        else:
            out.append((rel, "copy"))
    return out


def install(shared: Path, home: Path, *, shadow: bool = False, dry_run: bool = False) -> list[tuple[Path, str]]:
    todo = plan(shared, home, shadow=shadow)
    if not dry_run:
        for rel, what in todo:
            if what != "copy":
                continue
            dst = home / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "xb") as f:               # never over a file, even one that just appeared
                f.write((shared / rel).read_bytes())
    return todo


def export(home: Path, shared: Path) -> list[Path]:
    if shared.exists() and any(shared.iterdir()):
        raise SystemExit(f"{shared} is not empty: export into a new folder")
    done = []
    for rel in files(home):
        dst = shared / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(home / rel, dst)
        done.append(rel)
    return done


WORDS = {"copy": "copied", "have": "already have it", "kept yours": "KEPT YOURS (a different file of that name is in your home)",
         "factory": "skipped: would shadow the factory one (--shadow to take it)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=("list", "install", "export"))
    ap.add_argument("folder", type=Path)
    ap.add_argument("--home", type=Path, default=None, help="default: ~/Hyperspace or HYPERSPACE_HOME")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--shadow", action="store_true", help="also take files that shadow factory ones")
    a = ap.parse_args(argv)
    folder = a.folder if a.folder.is_absolute() else Path.cwd() / a.folder
    if a.action == "list":
        for rel in files(folder):
            print(rel)
        return 0
    home = a.home or _home()
    if a.action == "export":
        for rel in export(home, folder):
            print(rel)
        print(f"exported to {folder}: commit it")
        return 0
    todo = install(folder, home, shadow=a.shadow, dry_run=a.dry_run)
    for rel, what in todo:
        print(f"{'would be ' if a.dry_run and what == 'copy' else ''}{WORDS[what]:<12}  {rel}")
    n = sum(what == "copy" for _, what in todo)
    print(f"{n} file(s) {'would be ' if a.dry_run else ''}copied into {home}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
