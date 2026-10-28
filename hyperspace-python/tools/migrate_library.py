#!/usr/bin/env python3
"""Rewrite a library's presets as the newest schema, once (row 394).

    uv run python tools/migrate_library.py [--library PATH] [--apply] [--force NAME …]
    uv run python tools/migrate_library.py --library PATH --to FOLDER [--force NAME …]

The owner's decision of 2026-10-25: both Macs always run the newest build,
so every preset in the library is moved to the newest schema and old
schemas stop circulating. Plan 36 T3 (W3, D5): that is
``hyperspace.preset/7`` — the graph that says everything, every edge a
wire — and a load reads an older file only through the one-way migration
to it (`graphmigrate.seven`), so a ``/7`` is never migrated again. Each
preset in ``<library>/presets/*.json`` (not ``trash/``, not a backup, not
a dot-file) is loaded and saved untouched by the app itself
(`hyperspace.headless.resave`: the registry, library, router and presets
the tests save through) in a scratch library — the library's desk
templates and module presets beside it — and three checks are made:

- it loads (a file this build refuses is left as it is);
- the ``/7`` is a fixed point: loaded and saved untouched again it is the
  same bytes;
- its save round-trips the picture: the original file and its ``/7`` are
  each drawn on the golden-frame rig (tools/golden_frames.py `picture`:
  offscreen, the clock pinned, hands present, eight windows on the rig as
  it ships, `SHIPPED`: each shows its own wires, else All outputs' by its
  bus cables) and every output's hash must match. Both are drawn by
  *this* build — the original through the same one-way migration
  (`graphmigrate.seven`) a load runs — so "round-trip picture: same"
  proves the written ``/7`` draws what this build draws of the old file,
  never that it draws what the ``/6`` build drew. That parity is the
  migration's tests and the eye: a preset with a look-back or a dream is
  eyeballed live on the old and new build (hand check 366, party-wake).

An old file (before ``/7``) whose load says its section was "not read"
(the build refused it: black) is **not written**, whatever ``--force``
says: its ``/7`` would carry the old words with the migration lost for
good. A file whose load or save raises (a frame that does not settle
included) is skipped alone; the run goes on.

The default is a **dry run**: for each preset its file, its name, old schema
→ new, the notes its load made and the checks' results. Nothing is
written anywhere but a scratch folder.

``--apply`` first copies the whole library folder to a local backup,
``~/Hyperspace/library-backup-<YYYYMMDD-HHMMSS>/`` (the machine's home,
``$HYPERSPACE_HOME`` if set — never inside the library), and says where;
then rewrites each preset that passed, in place and atomically (a
dot-named temp file renamed over it), under its own file name. A file
whose bytes the save would not change (already ``/7`` and a fixed point)
is left untouched. A preset that failed a check is **not written** and is
listed at the end — unless ``--force NAME`` (its file stem; repeatable)
names it, which writes it despite a picture or fixed-point difference (a
file that does not load has nothing to write). No name changes.

``--to FOLDER`` (plan 36 T3) writes each preset that passed into FOLDER
under its own file name instead — the library is read, never written, so
no backup is made. The test corpus was made so, from the retired
generator's sources: ``--library tests/fixtures/factory-sources --to
tests/corpus/presets`` (with ``$HYPERSPACE_HOME`` pointed at a scratch
folder).

The library is ``--library``, else the config's ``[library] path`` (the
machine home's config.toml), else the machine home. Exit status: 0 when
every preset is (or would be) migrated or already was, 1 when any was (or
would be) skipped, 2 when the library is not there.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRESETS = "presets"
BACKUP_PREFIX = "library-backup-"
NEWEST = "hyperspace.preset/7"
# what a load note says of a graph section the build refused (preset.py:
# `GraphSection.read`, `UNWIRED_SAID`)
NOT_READ = "not read — black"


@dataclass
class Result:
    """What one preset's checks found."""

    file: str                       # the file's name, kept
    name: str = ""                  # the preset's own name
    old: str = "?"                  # its schema as found
    new: str = ""                   # the schema it saves as
    notes: list[str] = field(default_factory=list)
    error: str = ""                 # it does not load (nothing to write)
    fixed: bool = False             # the /7 re-saves as itself
    picture: str = ""               # the round trip: "same", "differs (k of n outputs)", or why not drawn
    unchanged: bool = False         # the save is the file's own bytes
    data: bytes = b""               # what a write puts there

    @property
    def ok(self) -> bool:
        return not self.error and self.fixed and self.picture == "same"


def machine_home() -> Path:
    """The machine's home (`$HYPERSPACE_HOME`, else ~/Hyperspace), read
    before anything that points HYPERSPACE_HOME at a scratch folder."""
    from hyperspace import library
    return Path(library.home())


def configured_library(home: Path) -> Path:
    """The config's ``[library] path`` (home/config.toml), else `home`."""
    from hyperspace import config
    cfg_path = home / config.FILE
    if cfg_path.is_file():
        lp = config.load(cfg_path).get("library", {}).get("path", "")
        if lp:
            return Path(lp)
    return home


def preset_files(library: Path) -> list[Path]:
    """The library's presets: ``presets/*.json`` one level down — a dot-file
    (a write's temp file), a backup (``.bak-``) and anything in ``trash/``
    left out."""
    folder = library / PRESETS
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.json")
                  if p.is_file() and not p.name.startswith(".") and ".bak-" not in p.name)


def check(path: Path, library: Path, scratch: Path, *, picture=None) -> Result:
    """Load, save, re-save and draw preset file `path` (`picture`: the
    golden rig's, `golden_frames.picture`; a test may hand its own). An
    old file whose section the load did not read is an error: never
    written (`NOT_READ`)."""
    from hyperspace import graphmigrate, headless
    from hyperspace.library import LibraryError

    res = Result(path.name)
    original = path.read_bytes()
    try:
        res.old = str(json.loads(original).get("schema") or "?")
    except ValueError as e:
        res.error = f"not JSON: {e}"
        return res
    try:
        data, notes, name = headless.resave(path, scratch / "once", library=library)
    except (LibraryError, ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        res.error = f"does not load: {e}"
        return res
    res.data, res.notes, res.name = data, notes, name
    version = graphmigrate.schema_version(json.loads(original))
    if (version is None or version < graphmigrate.SEVEN) and any(NOT_READ in n for n in notes):
        res.error = ("its graph section was not read by this build (black) — writing its /7 "
                     "would lose the migration for good")
        return res
    res.new = str(json.loads(data).get("schema"))
    res.unchanged = data == original
    seven = scratch / "seven" / path.name
    seven.parent.mkdir(parents=True, exist_ok=True)
    seven.write_bytes(data)
    try:
        again, _, _ = headless.resave(seven, scratch / "twice", library=library)
        res.fixed = again == data
    except (LibraryError, ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        res.fixed = False
        res.notes = [*res.notes, f"its /7 does not load: {e}"]
    if picture is None:
        picture = _golden_picture()
    try:
        before, _ = picture(path, library=library)
        after, _ = picture(seven, library=library)
    except Exception as e:  # noqa: BLE001 — a preset the rig cannot draw is a skip, said
        res.picture = f"not drawn: {type(e).__name__}: {e}"
        return res
    moved = sum(1 for a, b in zip(before, after) if a != b) + abs(len(before) - len(after))
    res.picture = "same" if moved == 0 else f"differs ({moved} of {len(before)} outputs)"
    return res


def _golden_picture():
    """tools/golden_frames.py's `picture` (imported late: the module points
    HYPERSPACE_HOME at a scratch folder unless one is set)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import golden_frames

    def draw(path: Path, *, library: Path | None = None):
        # (prefixed: never a fixture's slug, which the rig draws its own way;
        # plan 36 T3: the windows as the rig ships — the switch states the
        # goldens emulate are retired, and a `/7` is drawn as it is wired)
        return golden_frames.picture(path, slug=f"lib-{_slug(path.stem)}", library=library,
                                     states=golden_frames.SHIPPED)
    return draw


def _slug(stem: str) -> str:
    from hyperspace.library import slug
    return slug(stem)


def backup(library: Path, home: Path) -> Path:
    """Copy the whole library folder to ``<home>/library-backup-<stamp>/``
    (a backup already there, or one inside the library, is not copied into
    the new one) and return where."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = home / f"{BACKUP_PREFIX}{stamp}"
    k = 2
    while dest.exists():
        dest = home / f"{BACKUP_PREFIX}{stamp}-{k}"
        k += 1
    home.mkdir(parents=True, exist_ok=True)
    shutil.copytree(library, dest, ignore=shutil.ignore_patterns(f"{BACKUP_PREFIX}*"))
    return dest


def write(path: Path, data: bytes) -> None:
    """`data` over `path` atomically: a dot-named temp file beside it (no
    ``*.json``, so neither the library nor a cloud client takes it for a
    preset), then renamed over the file."""
    tmp = path.parent / f".{path.name}.migrate-{time.time_ns()}.tmp"
    try:
        with open(tmp, "xb") as f:
            f.write(data)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def line(r: Result) -> str:
    """One preset's report line."""
    head = f"{r.file:40s} {r.name!r:36s} {r.old.rpartition('/')[2] or '?':>2} → "
    if r.error:
        return f"{r.file:40s} {'':36s} {r.old.rpartition('/')[2]:>2} → --  SKIP: {r.error}"
    state = ("already /7, untouched" if r.unchanged and r.ok else
             "ok" if r.ok else "SKIP")
    why = [] if r.ok else [w for w in (
        "" if r.fixed else "its /7 is not a fixed point",
        "" if r.picture == "same" else f"round-trip picture {r.picture}") if w]
    out = f"{head}{r.new.rpartition('/')[2]}  round-trip picture: {r.picture}  fixed point: " \
          f"{'yes' if r.fixed else 'NO'}  {state}" + (f" ({'; '.join(why)})" if why else "")
    for n in r.notes:
        out += f"\n{'':44s}note: {n}"
    return out


def main(argv: list[str] | None = None, *, picture=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--library", type=Path, default=None,
                    help="the library folder (default: the config's [library] path, "
                         "else the machine home)")
    ap.add_argument("--apply", action="store_true",
                    help="back the library up, then rewrite every preset that passed")
    ap.add_argument("--force", action="append", default=[], metavar="NAME",
                    help="write this preset (its file stem) despite a picture or "
                         "fixed-point difference; repeatable")
    ap.add_argument("--to", type=Path, default=None, metavar="FOLDER",
                    help="write each preset that passed into FOLDER (the library is "
                         "only read; no backup)")
    a = ap.parse_args(argv)
    if a.to is not None and a.apply:
        ap.error("--to writes elsewhere; --apply rewrites the library: one of the two")
    home = machine_home()
    library = (a.library if a.library is not None else configured_library(home)).expanduser()
    library = library.resolve()
    if not (library / PRESETS).is_dir():
        print(f"no presets folder at {library / PRESETS}", file=sys.stderr)
        return 2
    files = preset_files(library)
    print(f"library: {library}  ({len(files)} presets)"
          + ("" if a.apply else f"  — written to {a.to}" if a.to is not None
             else "  — dry run, nothing is written"))
    print("(round-trip picture: the old file as this build loads it vs its /7 — not parity "
          "with the /6 build; eyeball dream presets live, hand check 366)")
    forced = set(a.force)
    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="hyperspace-migrate-") as scratch:
        for k, path in enumerate(files):
            r = check(path, library, Path(scratch) / str(k), picture=picture)
            results.append(r)
            print(line(r), flush=True)
    counts: dict[str, int] = {}
    for r in results:
        counts[r.old] = counts.get(r.old, 0) + 1
    print("\nby schema found: " + ", ".join(f"{s}: {n}" for s, n in sorted(counts.items())))
    writes = [r for r in results if not r.error and (not r.unchanged or a.to is not None)
              and (r.ok or r.file.removesuffix(".json") in forced)]
    skipped = [r for r in results if not r.ok
               and (r.error or r.file.removesuffix(".json") not in forced)]
    untouched = [r for r in results if r.ok and r.unchanged]
    if a.to is not None:
        a.to.mkdir(parents=True, exist_ok=True)
        for r in writes:
            write(a.to / r.file, r.data)
        print(f"wrote {len(writes)} as /7 into {a.to}, skipped {len(skipped)}")
    elif a.apply:
        where = backup(library, home)
        print(f"backup: {where}")
        for r in writes:
            write(library / PRESETS / r.file, r.data)
        print(f"rewrote {len(writes)} as /7, left {len(untouched)} untouched (already /7), "
              f"skipped {len(skipped)}")
    else:
        print(f"would rewrite {len(writes)} as /7, leave {len(untouched)} untouched "
              f"(already /7), skip {len(skipped)}")
    if skipped:
        print("\nnot written" + (" (rerun with --force NAME to write one anyway)"
                                 if any(not r.error for r in skipped) else "") + ":")
        for r in skipped:
            why = r.error or "; ".join(w for w in (
                "" if r.fixed else "its /7 is not a fixed point",
                "" if r.picture == "same" else f"round-trip picture {r.picture}") if w)
            print(f"  {r.file.removesuffix('.json')}: {why}")
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
