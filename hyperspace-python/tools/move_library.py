#!/usr/bin/env python3
"""Copy an existing library into a shared folder, once (plan 25 D8).

    uv run python tools/move_library.py DEST [--from HOME] [--dry-run]

Copies the library — ``presets/`` every folder down (plan 48: hidden
folders skipped), ``projects/`` and every module-preset group folder
(``fx/``, ``dream/``, ``band/`` …) — from HOME (default:
``$HYPERSPACE_HOME``, else ``~/Hyperspace``) into DEST, which it creates if
missing. Then add the two lines it prints to HOME's config.toml
and start Hyperspace: the library is read and written in DEST from then on.

It never overwrites: a file DEST already has is left alone — identical is
``have``, different is ``KEPT THEIRS`` (yours is kept, at the path it
prints). The machine files (config.toml, bindings.json and its backups, hands.json,
windows.json, last_show, logs, weights/, media/, media-cache/), the trash, the legacy
bindings/ folder, backups, dot-files and ``.git`` stay behind — and so does a
``hidden.json`` from before 2026-10-28 (the library has no hidden loadable patches
any more).

Then it clears HOME of the library (2026-11-23, the owner: the shared folder is the one
place patches live): every folder it copied from is moved, whole, into
``HOME/old-local-library-<date>-<time>/``, so nothing in HOME looks like a library and
the app stops saying it holds one. Nothing is deleted — a ``KEPT THEIRS`` file is in
there, at the path printed — and config.toml is never touched. ``--keep`` leaves HOME
as it was. Quit Hyperspace on every Mac first.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
# folders of the home that are not the library (D3), or not to be copied
SKIP_DIRS = {"weights", "trash", "bindings", "media", "media-cache"}
# the folders copied every folder down, as the app lists them
DEEP_DIRS = ("loadable", "presets", "patches")
# where `clear` puts what was copied: HOME/old-local-library-<YYYYMMDD-HHMMSS>/
ARCHIVE = "old-local-library-"
# folders of copies, never the library: `clear`'s archive, migrate_library.py's backup of
# the whole home (machine files among them, review of #480) and a hand-made presets backup
SKIP_PREFIXES = (ARCHIVE, "library-backup-", "presets-backup-")


def _library():
    """The app's `hyperspace.library`, imported late (the tool runs from
    anywhere): the repo put on ``sys.path`` once."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from hyperspace import library
    return library


def _home() -> Path:
    return Path(_library().home())


def _walk(folder: Path) -> list[Path]:
    """`library._walk`: every ``*.json`` under `folder`, every folder down,
    less hidden folders and never through a link to a folder (plan 48)."""
    return _library()._walk(folder)


def files(root: Path) -> list[Path]:
    """The library documents under `root`, relative: every ``<folder>/*.json``
    one level down, and ``presets/`` every folder down as the library lists
    it (plan 48 stage 2: hidden folders skipped) — backups, dot-files and
    the machine's folders left out."""
    out: list[Path] = []
    if not root.is_dir():
        return out
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        if folder.name in SKIP_DIRS or folder.name.startswith((".", *SKIP_PREFIXES)):
            continue
        # every folder down where the app reads every folder down: the loadable patches
        # (plan 48) and the patches, whose groups' are in ``patches/<group>/`` (plan 50)
        found = _walk(folder) if folder.name in DEEP_DIRS else sorted(folder.glob("*.json"))
        for f in found:
            if f.name.startswith(".") or ".bak-" in f.name or not f.is_file():
                continue
            out.append(f.relative_to(root))
    return out


def move(dest: Path, home: Path, *, dry_run: bool = False,
         out=print) -> list[tuple[str, Path]]:
    """Copy `home`'s library into `dest`; returns (what happened, relative
    path) per file — "copied", "have" or "KEPT THEIRS"."""
    if not home.is_dir():
        raise SystemExit(f"move_library: {home} is not a folder")
    if dest.resolve() == home.resolve():
        raise SystemExit("move_library: DEST is HOME — nothing to move")
    # loadable patches still in the old `presets/`: copied as they are, they would sit in a
    # folder a library with `loadable/` never reads (`library.loadable_dir`) — so the one
    # migration goes first (review of #480). Counted as `files` copies them (hidden folders,
    # backups and dot-files are not patches); `projects/` shows need no such step, being
    # read from either folder (`library.install_files`)
    old = [rel for rel in files(home) if rel.parts[0] == "presets"]
    if old:
        raise SystemExit(f"move_library: {home} still has loadable patches in presets/ (the "
                         "old layout): quit Hyperspace, run tools/migrate_library.py --library "
                         f'"{home}" --apply, then run this again. Nothing was copied')
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
    return done


def clear(home: Path, done: list[tuple[str, Path]], *, out=print) -> Path | None:
    """Move every top-level folder `done` drew from out of `home`, whole, into one
    ``ARCHIVE<stamp>/`` beside them; returns that folder (None: nothing to move).
    Moves, never deletes; the folders' other files go with them."""
    tops = sorted({rel.parts[0] for _, rel in done if len(rel.parts) > 1})
    if not tops:
        return None
    archive = home / (ARCHIVE + time.strftime("%Y%m%d-%H%M%S"))
    n = 1
    while archive.exists():
        n += 1
        archive = home / (ARCHIVE + time.strftime("%Y%m%d-%H%M%S") + f"-{n}")
    archive.mkdir()
    for top in tops:
        (home / top).rename(archive / top)
        out(f"moved       {top}/ → {archive / top}")
    for what, rel in done:
        if what == "KEPT THEIRS":
            out(f"KEPT THEIRS {rel} — yours is now at {archive / rel}")
    return archive


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dest", type=Path, help="the shared folder (created if missing)")
    ap.add_argument("--from", dest="home", type=Path, default=None,
                    help="the home to copy from (default: $HYPERSPACE_HOME, else ~/Hyperspace)")
    ap.add_argument("--dry-run", action="store_true", help="say what would happen, write nothing")
    ap.add_argument("--keep", action="store_true",
                    help="leave HOME's copy where it is (default: moved into "
                         f"HOME/{ARCHIVE}<date>-<time>/)")
    a = ap.parse_args(argv)
    home = (a.home if a.home is not None else _home()).expanduser()
    dest = a.dest.expanduser().resolve()
    done = move(dest, home, dry_run=a.dry_run)
    if not a.dry_run and not a.keep:
        clear(home, done)
    elif a.dry_run and not a.keep and done:
        print(f"(then each folder above would be moved into {home / ARCHIVE}<date>-<time>/)")
    counts: dict[str, int] = {}
    for what, _ in done:
        counts[what] = counts.get(what, 0) + 1
    print(("dry run: " if a.dry_run else "") + ", ".join(f"{n} {k}" for k, n in counts.items())
          if counts else "nothing to copy")
    print(f"\n{'Then' if a.dry_run else 'Now'} add these lines to {home / 'config.toml'} "
          "and start Hyperspace:\n")
    print("[library]")
    print(f'path = "{dest}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
