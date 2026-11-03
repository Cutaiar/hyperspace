#!/usr/bin/env python3
"""Rewrite a library's presets as the newest schema, once (row 394).

    uv run python tools/migrate_library.py [--library PATH] [--show NAME] [--apply]
                                           [--force NAME …]
    uv run python tools/migrate_library.py --library PATH --to FOLDER [--force NAME …]

The owner's decision of 2026-10-25: both Macs always run the newest build,
so every preset in the library is moved to the newest schema and old
schemas stop circulating. Since plan 43 C2 (rows 572, 576) that is
``hyperspace.preset/9`` — plan 36 T3's graph that says everything (every
edge a wire, ``/7``), the GRAPH page's groups (``/8``), and the one orbit
camera: the eye (``eye.fov``, ``eye.distance``) in every preset's
``values``, where until now the open show held it. A load reads an older
file through the one-way migration (`graphmigrate.seven`, then
`graphmigrate.nine`). Each preset in ``<library>/presets/*.json`` (not
``trash/``, not a backup, not a dot-file) is loaded and saved untouched
by the app itself (`hyperspace.headless.resave`: the registry, library,
router and presets the tests save through) in a scratch library — the
library's desk templates and module presets beside it, and **the rig's
show open** (below) — and three checks are made:

- it loads (a file this build refuses is left as it is);
- the ``/9`` is a fixed point: loaded and saved untouched again it is the
  same bytes;
- its save round-trips the picture: the original file and its ``/9`` are
  each drawn on the golden-frame rig (tools/golden_frames.py `picture`:
  offscreen, the clock pinned, hands present, eight windows on the rig as
  it ships, `SHIPPED`: each shows its own wires, else All outputs' by its
  bus cables), the same show open, and every output's hash must match.
  Both are drawn by *this* build — the original through the same one-way
  migration a load runs — so "round-trip picture: same" proves the
  written ``/9`` draws what this build draws of the old file with the
  rig's show open (the eye included), never that it draws what an older
  build drew. That parity is the migration's tests and the eye: a preset
  with a look-back or a dream is eyeballed live on the old and new build
  (hand check 366, party-wake).

**The rig's show** (plan 43 C2): an old preset drew through the eye the
open show's ``session`` held, so its ``/9`` takes that show's eye — and
the camera node's GRAPH position the show's ``layout`` kept — exactly as
the app hands it to an old preset's load (`library.Project.old_eye`).
The show is ``--show NAME`` (a file stem under ``<library>/projects/``),
else this Mac's last show (``<home>/last_show``), else the library's one
show; none (or a show that holds no eye, nor a ``.bak-v2-eye`` copy of
itself that does) is the build's default eye, and the tool says which.
Every show in ``<library>/projects/`` that holds the eye or the camera's
position is then rewritten without them, ``<file>.bak-v2-eye`` kept
beside it first (the app's own backup, `library.EYE_BACKUP`).

**The retaper first** (wave 0 T1, tools/retaper_routes.py): one bump moves
everything, so ``--apply`` measures every document of the library still
without the taper marker (``units["fx.depth"] == "taper"``) along the
effect tapers before anything else — the patches, the desk templates and
this Mac's ``bindings.json`` (kept as ``bindings.json.bak-v3``) as
retaper_routes.py writes them. A preset is retapered by its own resave
(its load measures an unmarked file's depths, its save writes the marker),
so every ``/9`` is along the tapers. The dry run says what it would
retaper.

An old file (before ``/7``) whose load says its section was "not read"
(the build refused it: black) is **not written**, whatever ``--force``
says: its ``/9`` would carry the old words with the migration lost for
good. A file whose load or save raises (a frame that does not settle
included) is skipped alone; the run goes on. No pose is written: an old
file had none and keeps spinning (`headless.resave` takes it back out).

The default is a **dry run**: for each preset its file, its name, old schema
→ new, the notes its load made and the checks' results; the show and the
eye it hands on; the shows and the documents it would rewrite. Nothing is
written anywhere but a scratch folder.

``--apply`` first copies the whole library folder to a local backup,
``~/Hyperspace/library-backup-<YYYYMMDD-HHMMSS>/`` (the machine's home,
``$HYPERSPACE_HOME`` if set — never inside the library), and says where;
then retapers, then computes and rewrites each preset that passed (against
the retapered templates; a dry run computes against a retapered scratch
copy, so it says what --apply writes), in place and
atomically (a dot-named temp file renamed over it), under its own file
name, then the shows. A file whose bytes the save would not change
(already ``/9`` and a fixed point) is left untouched. A preset that failed
a check is **not written** and is listed at the end — unless ``--force
NAME`` (its file stem; repeatable) names it, which writes it despite a
picture or fixed-point difference (a file that does not load has nothing
to write). No name changes. **Run it between shows, with both Macs on this
build**: a Mac on an older build refuses a ``/9``.

``--to FOLDER`` (plan 36 T3) writes each preset that passed into FOLDER
under its own file name instead — the library is read, never written, so
no backup is made, nothing in the library is retapered and no show is
rewritten (the presets are computed against a retapered scratch copy). The test
corpus was made so: ``--library <a copy holding tests/corpus/presets>
--to tests/corpus/presets`` (with ``$HYPERSPACE_HOME`` pointed at a
scratch folder; no show, so the build's default eye — what the goldens
draw with).

The library is ``--library``, else the config's ``[library] path`` (the
machine home's config.toml), else the machine home. Exit status: 0 when
every preset is (or would be) migrated or already was, 1 when any was (or
would be) skipped, 2 when the library is not there or ``--show`` names no
show.
"""

from __future__ import annotations

import argparse
import importlib.util
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
PROJECTS = "projects"
SHOW_SUFFIX = ".hyp.json"
BACKUP_PREFIX = "library-backup-"
NEWEST = "hyperspace.preset/9"
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
    fixed: bool = False             # the /9 re-saves as itself
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


def show_files(library: Path) -> list[Path]:
    """The library's shows: ``projects/*.hyp.json``, a dot-file and a backup
    left out (plan 43 C2)."""
    folder = library / PROJECTS
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob(f"*{SHOW_SUFFIX}")
                  if p.is_file() and not p.name.startswith(".") and ".bak-" not in p.name)


def _read(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def rig_show(library: Path, home: Path, name: str | None = None
             ) -> tuple[Path | None, dict | None, str]:
    """The show whose eye the presets take (plan 43 C2): `name` (a file
    stem), else this Mac's last show if the library holds it, else the
    library's only show — (its path or None, its `headless.show_seed` or
    None when it kept no eye and no camera position, a line saying which).
    A show that no longer holds the eye (saved on this build before the
    migration ran) gives the eye its ``.bak-v2-eye`` kept. Raises
    LookupError for a `name` the library has no show of."""
    from hyperspace import headless
    from hyperspace.library import EYE_BACKUP, LAST_SHOW

    shows = {p.name[: -len(SHOW_SUFFIX)]: p for p in show_files(library)}
    if name is not None:
        if name not in shows:
            raise LookupError(f"no show {name!r} under {library / PROJECTS}")
        path, how = shows[name], "--show"
    else:
        try:
            last = (home / LAST_SHOW).read_text().strip()
        except OSError:
            last = ""
        if last in shows:
            path, how = shows[last], "this Mac's last show"
        elif len(shows) == 1:
            path, how = next(iter(shows.values())), "the library's one show"
        else:
            why = "no show in the library" if not shows else (
                f"{len(shows)} shows and none is this Mac's last: name one with --show")
            return None, None, f"show: none ({why}) — every preset takes the build's default eye"
    seed = headless.show_seed(_read(path))
    if seed is None or not seed["session"]:
        for bak in sorted(path.parent.glob(f"{path.name}.bak-v{EYE_BACKUP}*")):
            kept = headless.show_seed(_read(bak))
            if kept is not None and kept["session"]:
                seed = {**kept, **(seed or {}), "session": kept["session"]}
                how += f", its eye from {bak.name}"
                break
    eye = seed["session"] if seed is not None else {}
    said = (", ".join(f"{k} {v:.4g}" for k, v in sorted(eye.items())) if eye
            else "no eye (the build's default)")
    return path, seed, f"show: {path.name[: -len(SHOW_SUFFIX)]} ({how}) — {said}"


def check(path: Path, library: Path, scratch: Path, *, picture=None,
          show: dict | None = None) -> Result:
    """Load, save, re-save and draw preset file `path` (`picture`: the
    golden rig's, `golden_frames.picture`; a test may hand its own), the
    rig's show `show` (a `headless.show_seed`) open. An old file whose
    section the load did not read is an error: never written (`NOT_READ`)."""
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
        data, notes, name = headless.resave(path, scratch / "once", library=library, show=show)
    except (LibraryError, ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        res.error = f"does not load: {e}"
        return res
    res.data, res.notes, res.name = data, notes, name
    version = graphmigrate.schema_version(json.loads(original))
    if (version is None or version < graphmigrate.SEVEN) and any(NOT_READ in n for n in notes):
        res.error = ("its graph section was not read by this build (black) — writing its /9 "
                     "would lose the migration for good")
        return res
    res.new = str(json.loads(data).get("schema"))
    res.unchanged = data == original
    nine = scratch / "nine" / path.name
    nine.parent.mkdir(parents=True, exist_ok=True)
    nine.write_bytes(data)
    try:
        again, _, _ = headless.resave(nine, scratch / "twice", library=library, show=show)
        res.fixed = again == data
    except (LibraryError, ValueError, KeyError, TypeError, OSError, RuntimeError) as e:
        res.fixed = False
        res.notes = [*res.notes, f"its /9 does not load: {e}"]
    if picture is None:
        picture = _golden_picture()
    try:
        before, _ = picture(path, library=library, show=show)
        after, _ = picture(nine, library=library, show=show)
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

    def draw(path: Path, *, library: Path | None = None, show: dict | None = None):
        # (prefixed: never a fixture's slug, which the rig draws its own way;
        # plan 36 T3: the windows as the rig ships — the switch states the
        # goldens emulate are retired, and a `/9` is drawn as it is wired)
        return golden_frames.picture(path, slug=f"lib-{_slug(path.stem)}", library=library,
                                     states=golden_frames.SHIPPED, show=show)
    return draw


def _slug(stem: str) -> str:
    from hyperspace.library import slug
    return slug(stem)


def _retaper_tool():
    """tools/retaper_routes.py as a module (it imports this one as
    `migrate_library` for the home, the file list, the backup and the write)."""
    if "retaper_routes" in sys.modules:
        return sys.modules["retaper_routes"]
    sys.modules.setdefault("migrate_library", sys.modules[__name__])
    spec = importlib.util.spec_from_file_location("retaper_routes",
                                                  ROOT / "tools" / "retaper_routes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["retaper_routes"] = mod
    spec.loader.exec_module(mod)
    return mod


def retaper_plan(library: Path, home: Path) -> list[tuple[Path, object]]:
    """What the retaper would write first (plan 43 C2: one bump moves
    everything): every patch, desk template and this Mac's bindings.json
    still without the taper marker, each with its `retaper_routes.Change`.
    The presets are retapered by their own resave."""
    from hyperspace import routing
    from hyperspace.fx import FxState

    rt = _retaper_tool()
    files = FxState().files
    out = [(p, rt.plan(p, files, kind="patch")) for p in rt.json_files(library / rt.PATCHES)]
    out += [(p, rt.plan(p, files, kind="desk")) for p in rt.json_files(library / rt.DESK)]
    table = home / routing.FILE
    if table.is_file():
        out.append((table, rt.plan(table, files, kind="bindings")))
    return [(p, c) for p, c in out if c.changed]


def retaper_write(todo) -> list[str]:
    """Write `retaper_plan`'s documents (after the library's backup): the
    bindings table kept beside itself first, as the retaper keeps it."""
    from hyperspace import routing
    said = []
    for path, c in todo:
        if c.kind == "bindings":
            schema = str(json.loads(path.read_text()).get("schema", "")).rpartition("/")[2] or "0"
            if routing.backup(path, schema) is None:
                said.append(f"{path.name}: not retapered — no backup could be made")
                continue
        write(path, c.text.encode())
    return said


def shared_retapers(library: Path, todo) -> bool:
    """Whether `retaper_plan` would rewrite a document a preset's load reads
    beside it (`headless.SHARED_FOLDERS`: a desk template) — else the
    library itself is what every preset is computed against."""
    from hyperspace.headless import SHARED_FOLDERS
    for path, _c in todo:
        try:
            rel = path.relative_to(library)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] in SHARED_FOLDERS:
            return True
    return False


def retapered_copy(library: Path, todo, dest: Path) -> Path:
    """The folders a preset's load reads beside it (`headless.SHARED_FOLDERS`:
    the desk templates, the module presets) copied to `dest`, each document
    of `retaper_plan`'s that lives there written as the retaper writes it —
    what a dry run or --to computes every preset's /9 against, so it is what
    --apply (which retapers the library itself first) writes."""
    from hyperspace.headless import SHARED_FOLDERS
    for folder in SHARED_FOLDERS:
        if (library / folder).is_dir():
            shutil.copytree(library / folder, dest / folder,
                            ignore=shutil.ignore_patterns(".*", "Icon*"))
    for path, c in todo:
        try:
            rel = path.relative_to(library)
        except ValueError:                    # (the machine's bindings.json)
            continue
        if rel.parts[0] in SHARED_FOLDERS:
            (dest / rel).write_text(c.text)
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def show_plan(library: Path) -> list[tuple[Path, bytes]]:
    """Every show in the library that holds the eye or the camera's GRAPH
    position, with its bytes without them (`library.show_without_eye`)."""
    from hyperspace.library import show_text, show_without_eye
    out = []
    for path in show_files(library):
        doc = _read(path)
        new = show_without_eye(doc) if doc is not None else None
        if new is not None:
            out.append((path, show_text(new).encode()))
    return out


def show_write(todo) -> list[str]:
    """Write `show_plan`'s shows, each kept as ``<file>.bak-v2-eye`` first
    (`routing.backup`, the app's own); no backup, no write."""
    from hyperspace import routing
    from hyperspace.library import EYE_BACKUP
    said = []
    for path, data in todo:
        if routing.backup(path, EYE_BACKUP) is None:
            said.append(f"{path.name}: not rewritten — no backup could be made")
            continue
        write(path, data)
    return said


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
    state = ("already /9, untouched" if r.unchanged and r.ok else
             "ok" if r.ok else "SKIP")
    why = [] if r.ok else [w for w in (
        "" if r.fixed else "its /9 is not a fixed point",
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
    ap.add_argument("--show", default=None, metavar="NAME",
                    help="the show whose eye the presets take (its file stem; default: "
                         "this Mac's last show, else the library's only show)")
    ap.add_argument("--apply", action="store_true",
                    help="back the library up, retaper, then rewrite every preset that "
                         "passed and every show that holds the eye")
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
    try:
        _show, seed, said = rig_show(library, home, a.show)
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 2
    files = preset_files(library)
    print(f"library: {library}  ({len(files)} presets)"
          + ("" if a.apply else f"  — written to {a.to}" if a.to is not None
             else "  — dry run, nothing is written"))
    print(said)
    print("(round-trip picture: the old file as this build loads it, the show open, vs its "
          "/9 — not parity with an older build; eyeball dream presets live, hand check 366)")
    # (review 5: every preset's /9 is computed against the templates as the
    # retaper leaves them — with --apply the library is backed up and
    # retapered first; a dry run and --to read a retapered scratch copy, so
    # they report what --apply writes. --to writes only presets.)
    retapers = retaper_plan(library, home)
    shows = show_plan(library) if a.to is None else []
    if retapers:
        print(f"retaper first: {len(retapers)} document(s) without the taper marker — "
              + ", ".join(f"{c.kind} {p.name}" for p, c in retapers))
    if shows:
        print(f"shows holding the eye: {len(shows)} — "
              + ", ".join(p.name for p, _ in shows) + " (each kept as .bak-v2-eye)")
    if a.apply:
        where = backup(library, home)
        print(f"backup: {where}")
        for problem in retaper_write(retapers):
            print(problem)
        if retapers:
            print(f"retapered {len(retapers)} document(s) along the effect tapers")
    forced = set(a.force)
    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="hyperspace-migrate-") as scratch:
        # (review 2.7: a copy only when a document the loads read is retapered)
        read_from = (retapered_copy(library, retapers, Path(scratch) / "retapered")
                     if not a.apply and shared_retapers(library, retapers) else library)
        for k, path in enumerate(files):
            r = check(path, read_from, Path(scratch) / str(k), picture=picture, show=seed)
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
        print(f"wrote {len(writes)} as /9 into {a.to}, skipped {len(skipped)}")
    elif a.apply:
        for r in writes:
            write(library / PRESETS / r.file, r.data)
        print(f"rewrote {len(writes)} as /9, left {len(untouched)} untouched (already /9), "
              f"skipped {len(skipped)}")
        for problem in show_write(shows):
            print(problem)
        if shows:
            print(f"rewrote {len(shows)} show(s) without the eye")
    else:
        print(f"would rewrite {len(writes)} as /9, leave {len(untouched)} untouched "
              f"(already /9), skip {len(skipped)}"
              + (f"; retaper {len(retapers)} first" if retapers else "")
              + (f"; drop the eye from {len(shows)} show(s)" if shows else ""))
    if skipped:
        print("\nnot written" + (" (rerun with --force NAME to write one anyway)"
                                 if any(not r.error for r in skipped) else "") + ":")
        for r in skipped:
            why = r.error or "; ".join(w for w in (
                "" if r.fixed else "its /9 is not a fixed point",
                "" if r.picture == "same" else f"round-trip picture {r.picture}") if w)
            print(f"  {r.file.removesuffix('.json')}: {why}")
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
