#!/usr/bin/env python3
"""The one migration (plan 57 §7, §7a): a library to `/11`, its shows to install files.

    uv run python tools/migrate_library.py [--library PATH] [--show NAME] [--apply]
                                           [--force NAME …]
    uv run python tools/migrate_library.py --library PATH --to FOLDER [--force NAME …]

**The default is a dry run: nothing is written anywhere but a scratch folder.** ``--apply``
refuses to run while Hyperspace is open on this Mac (it says if it can't tell, and it can
never see the other Mac: quit there first), then, in this order, because of what reads what:

1. **One backup** of the whole library, ``<home>/library-backup-<stamp>/``, never inside it.
2. **The trash is deleted, not converted** (the owner, 2026-11-06): ``<library>/trash`` and
   ``presets-backup-*``.
3. **The retaper,** a no-op after the first (`retaper_plan`), and module presets and
   ``patch/1`` files into the one format (`group_plan`).
4. **Every loadable patch to** ``hyperspace.loadable/11`` by `hyperspace.headless.resave`, in
   place, with three checks: it loads; it is a fixed point (loaded and saved untouched again,
   the same bytes); and the same picture: the old file and its ``/11`` are each drawn on the
   golden-frame rig, the rig's show open, and every output's hash must match. Both are drawn
   by this build, so that proves the written ``/11`` draws what this build draws of the old
   file, never what an older build drew. **Shows still exist here:** an old file takes the
   eye, looks and cuts of **the rig's show** (``--show NAME``, else this Mac's last show, else
   the library's one show). A file that fails a check is not written and stays readable; it
   is listed at the end, and ``--force NAME`` writes it despite a picture or fixed-point
   difference (never one that doesn't load, or an old file whose section "was not read").
5. **Each show to** ``installs/<stem>.json`` (`library.install_doc`), last of the file
   rewrites, and it opens in the new reader before its show goes. Each show becomes an
   install; merging by machine would guess. ``startup`` that names no file is cleared and
   said (``mine``'s ``MIGRATED``); bank slots that point at nothing are reported and left.
6. **Tidy:** ``fx/``, ``.bak-v2-*`` and folders with nothing in them (a Drive ``Icon`` and
   ``.DS_Store`` count as nothing) are deleted.
7. **The folder move, last of all:** ``presets/`` to ``loadable/``, a rename, so a failure
   before it leaves today's paths.

A second run does nothing, and makes no backup. A run after an old build saved into the old
folders takes those files as well. Each Mac's ``bindings.json`` moves at its own next launch,
by the road it already has; ``last_show`` is read into ``last_install`` the same way.

``--to FOLDER`` writes each loadable patch that passed into FOLDER under its own file name:
the library is read, never written, and no backup is made. The test corpus was made so, with
``$HYPERSPACE_HOME`` pointed at a scratch folder.

The library is ``--library``, else the config's ``[library] path``, else the machine home.
Exit status: 0 when every file is (or would be) migrated or already was, 1 when any was (or
would be) skipped or left, 2 when there is no library, ``--show`` names no show, or the app is
open on this Mac.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOADABLE = "loadable"
OLD_LOADABLE = "presets"
PROJECTS = "projects"
INSTALLS = "installs"
SHOW_SUFFIX = ".hyp.json"
BACKUP_PREFIX = "library-backup-"
NEWEST = "hyperspace.loadable/11"         # plan 57 (FQ4)
OLD_BACKUPS = "presets-backup-"           # a hand-made copy, deleted with the trash (§7a)
TRASH = "trash"
NOTHING_FILES = ("Icon\r", "Icon", ".DS_Store")   # what makes no folder worth keeping
KEPT_FOLDERS = {"media", "media-cache", "weights", "trash", LOADABLE, INSTALLS, "patches"}
# what a load note says of a graph section the build refused (loadable.py:
# `GraphSection.read`, `UNWIRED_SAID`)
NOT_READ = "not read — black"


@dataclass
class Result:
    """What one loadable patch's checks found."""

    file: str                       # the file's path under presets/ (party/trip.json), kept
    name: str = ""                  # the loadable patch's own name
    old: str = "?"                  # its schema as found
    new: str = ""                   # the schema it saves as
    notes: list[str] = field(default_factory=list)
    error: str = ""                 # it does not load (nothing to write)
    fixed: bool = False             # the /11 re-saves as itself
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


def loadable_files(library: Path) -> list[Path]:
    """The library's loadable patches: ``loadable/`` and ``presets/`` every folder down, as
    the library lists them (`library._walk`, plan 48 stage 2: hidden folders skipped, never
    through a link): a dot-file (a write's temp file), a backup (``.bak-``) and anything in
    ``trash/`` left out."""
    from hyperspace.library import _walk

    out: list[Path] = []
    for name in (LOADABLE, OLD_LOADABLE):
        folder = library / name
        if folder.is_dir():
            out += [p for p in _walk(folder)
                    if p.is_file() and not p.name.startswith(".") and ".bak-" not in p.name]
    return out


def under_folder(library: Path, path: Path) -> str:
    """`path` under whichever of the two folders holds it (``party/trip.json``)."""
    for name in (LOADABLE, OLD_LOADABLE):
        if path.is_relative_to(library / name):
            return path.relative_to(library / name).as_posix()
    return path.name


def app_running() -> tuple[bool | None, str]:
    """Is Hyperspace open on this Mac? (True, False, or None when it can't tell), in words.
    The other Mac is never seen: that one is a person's to quit."""
    try:
        out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True,
                             timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"can't tell whether Hyperspace is open on this Mac ({e}): make sure it isn't"
    for row in out.splitlines():
        if "bin/hyperspace" in row or "-m hyperspace" in row or "hyperspace.app" in row:
            return True, f"Hyperspace is open on this Mac: {row.strip()[:100]}"
    return False, "Hyperspace is not open on this Mac (the other Mac can't be seen from here)"


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
    """The show whose eye the loadable patches take (plan 43 C2): `name` (a file
    stem), else this Mac's last show if the library holds it, else the
    library's only show — (its path or None, its `headless.show_seed` or
    None when it kept no eye and no camera position, a line saying which).
    A show that no longer holds the eye (saved on this build before the
    migration ran) gives the eye its ``.bak-v2-eye`` kept. Raises
    LookupError for a `name` the library has no show of."""
    from hyperspace import headless
    from hyperspace.library import (
        LAST_INSTALL,
        LAST_SHOW,
        kept_eye,
        kept_look,
        show_eye,
        show_look,
    )

    shows = {p.name[: -len(SHOW_SUFFIX)]: p for p in show_files(library)}
    if name is not None:
        if name not in shows:
            raise LookupError(f"no show {name!r} under {library / PROJECTS}")
        path, how = shows[name], "--show"
    else:
        last = ""
        for file in (LAST_INSTALL, LAST_SHOW):
            try:
                last = last or (home / file).read_text().strip()
            except OSError:
                pass
        if last in shows:
            path, how = shows[last], "this Mac's last show"
        elif len(shows) == 1:
            path, how = next(iter(shows.values())), "the library's one show"
        else:
            why = "no show in the library" if not shows else (
                f"{len(shows)} shows and none is this Mac's last: name one with --show")
            return None, None, (f"show: none ({why}) — every loadable patch takes the build's "
                                "default eye, hands' and clouds' looks, and no bus cut")
    doc = _read(path)
    eye, _at = show_eye(doc)
    kept, kept_at = ({}, None) if eye else kept_eye(path)
    look, cuts = show_look(doc)
    k_look, k_cuts = ({}, None) if (look or cuts.cut) else kept_look(path)
    seed = headless.show_seed(doc, kept, kept_at, k_look, k_cuts)
    if kept:
        how += f", its eye from a backup of {path.name}"
    if k_look or (k_cuts is not None and k_cuts.cut):
        how += f", its look from a backup of {path.name}"
    session = seed["session"] if seed is not None else {}
    said = (", ".join(f"{k} {v:.4g}" for k, v in sorted(session.items())) if session
            else "no eye nor look (the build's defaults)")
    cut = (seed or {}).get("rig", {}).get("cut", [])
    said += (f"; {len(cut)} bus cut(s) into every loadable patch: "
             + ", ".join(f"{c['from']} → {c['to']}" for c in cut) if cut else "; no bus cut")
    return path, seed, f"show: {path.name[: -len(SHOW_SUFFIX)]} ({how}) — {said}"


def check(path: Path, library: Path, scratch: Path, *, picture=None,
          show: dict | None = None, file: str | None = None) -> Result:
    """Load, save, re-save and draw loadable patch file `path` (`picture`: the
    golden rig's, `golden_frames.picture`; a test may hand its own), the
    rig's show `show` (a `headless.show_seed`) open. An old file whose
    section the load did not read is an error: never written (`NOT_READ`).
    `file` is what the result calls it — its path under ``presets/``
    (``party/trip.json``, plan 48 stage 2), else its file name."""
    from hyperspace import graphmigrate, headless
    from hyperspace.library import LibraryError

    res = Result(file or path.name)
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
        res.error = ("its graph section was not read by this build (black) — writing its /11 "
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
        res.notes = [*res.notes, f"its /11 does not load: {e}"]
    if picture is None:
        picture = _golden_picture()
    try:
        before, _ = picture(path, library=library, show=show)
        after, _ = picture(nine, library=library, show=show)
    except Exception as e:  # noqa: BLE001 — a loadable patch the rig cannot draw is a skip, said
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
        # goldens emulate are retired, and a `/10` is drawn as it is wired)
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
    everything): every patch and this Mac's bindings.json
    still without the taper marker, each with its `retaper_routes.Change`.
    The loadable patches are retapered by their own resave."""
    from hyperspace import routing
    from hyperspace.fx import FxState

    rt = _retaper_tool()
    files = FxState().files
    out = [(p, rt.plan(p, files, kind="patch")) for p in rt.json_files(library / rt.PATCHES)]
    # (plan 44 D3: no desk templates — a `desk/` folder left over is never read,
    # never rewritten)
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
    """Whether `retaper_plan` would rewrite a document a loadable patch's load reads
    beside it (`headless.SHARED_FOLDERS`, the module presets — none today:
    the retaper rewrites patches and `bindings.json`, plan 44 D3 retired the
    desk templates) — else the library itself is what every loadable patch is
    computed against."""
    from hyperspace.headless import SHARED_FOLDERS
    for path, _c in todo:
        try:
            rel = path.relative_to(library)
        except ValueError:
            continue
        # (plan 50: `patches/` is shared for its groups' folders — a module
        # group's patches; a top-level patch is spawned, never read by a load)
        if len(rel.parts) > 2 and rel.parts[0] in SHARED_FOLDERS:
            return True
    return False


def retapered_copy(library: Path, todo, dest: Path) -> Path:
    """The folders copied beside a loadable patch for its load (`headless.SHARED_FOLDERS`:
    the module presets) copied to `dest`, each document
    of `retaper_plan`'s that lives there written as the retaper writes it —
    what a dry run or --to computes every loadable patch's /10 against, so it is what
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


@dataclass
class InstallMove:
    """One show on its way to an install file."""

    src: Path
    dest: Path
    data: bytes
    said: list[str] = field(default_factory=list)


def install_plan(library: Path) -> tuple[list[InstallMove], list[str]]:
    """Every show (and an install file a Mac saved into ``projects/``) as its
    ``installs/<stem>.json`` (`library.install_doc`), each read back through the new reader;
    ``startup`` naming no file cleared, bank slots naming nothing reported. Returns (the
    moves, words for what is left: a file that won't read, a place already holding others)."""
    from hyperspace.library import (
        LOADABLE as GROUP,
    )
    from hyperspace.library import (
        Library,
        LibraryError,
        _json_text,
        install_doc,
        install_stem,
    )

    todo: list[InstallMove] = []
    left: list[str] = []
    shows = show_files(library)
    if not shows:
        return todo, left
    with tempfile.TemporaryDirectory(prefix="hyperspace-names-") as machine:
        names = Library(library, machine=Path(machine), period=0.0)
        for path in shows:
            doc = _read(path)
            if doc is None:
                left.append(f"{path.name}: does not read — left as it is")
                continue
            try:
                new = install_doc(doc)
            except (LibraryError, ValueError, TypeError) as e:
                left.append(f"{path.name}: {e} — left as it is")
                continue
            said: list[str] = []
            start = new.get("startup")
            if start and names.path_of(GROUP, start, loose=True) is None:
                said.append(f"its startup {start!r} names no file: cleared")
                new["startup"] = None
            empty = [str(k + 1) for k, n in enumerate(new.get("bank") or [])
                     if n and names.path_of(GROUP, n, loose=True) is None]
            if empty:
                said.append(f"bank slots naming nothing, left as they are: {', '.join(empty)}")
            if not new.get("tuning"):
                said.append("it holds no tuning: opening it changes none")
            stem = install_stem(path.name)
            dest = library / INSTALLS / f"{stem}.json"
            data = _json_text(new).encode()
            if dest.exists() and dest.read_bytes() != data:
                left.append(f"{path.name}: installs/{dest.name} holds another file — left as it is")
                continue
            # it opens in the new reader, before its show goes
            try:
                names.project._take(json.loads(data), dest, dest.name)
            except (LibraryError, ValueError, TypeError) as e:
                left.append(f"{path.name}: its install file does not open ({e}) — left as it is")
                continue
            todo.append(InstallMove(path, dest, data, said))
    return todo, left


def install_write(todo: list[InstallMove]) -> list[str]:
    """Write `install_plan`'s files, each show removed only after (the backup holds it)."""
    said = []
    for m in todo:
        try:
            m.dest.parent.mkdir(parents=True, exist_ok=True)
            write(m.dest, m.data)
            m.src.unlink()
        except OSError as e:
            said.append(f"{m.src.name}: not moved — {e}")
    return said


def _nothing_in(folder: Path) -> bool:
    """Does `folder` hold nothing a person put there, every folder down?"""
    try:
        return all((p.name in NOTHING_FILES) or (p.is_dir() and not p.is_symlink() and _nothing_in(p))
                   for p in folder.iterdir())
    except OSError:
        return False


def is_home(library: Path, home: Path) -> bool:
    """The library is this Mac's home: its `trash/` and its ``.bak-`` files are the Mac's."""
    try:
        return library.resolve() == home.resolve()
    except OSError:
        return False


def trash_plan(library: Path, home: Path) -> list[Path]:
    """What goes first, after the backup (the owner, 2026-11-06): the library's trash and the
    hand-made ``presets-backup-*``; deleted, never converted. A library that is the Mac's own
    home keeps its trash: that one is the Mac's."""
    if not library.is_dir():
        return []
    return [d for d in sorted(library.iterdir()) if d.is_dir() and not d.is_symlink()
            and ((d.name == TRASH and not is_home(library, home))
                 or d.name.startswith(OLD_BACKUPS))]


def tidy_plan(library: Path) -> list[Path]:
    """What the run deletes at the end (§7a): the retired ``fx/`` folder and every
    ``.bak-v2-*`` the shows and loadable patches kept. Empty folders: `empty_folders`."""
    out = [library / "fx"] if (library / "fx").is_dir() else []
    for name in (PROJECTS, INSTALLS, OLD_LOADABLE, LOADABLE, "patches"):
        if (library / name).is_dir():
            out += [p for p in sorted((library / name).rglob("*.bak-v2-*")) if p.is_file()]
    return out


def empty_folders(library: Path) -> list[Path]:
    """Folders with nothing in them, the deepest first; those of `KEPT_FOLDERS` are kept."""
    out = []
    for d in sorted((p for p in library.rglob("*") if p.is_dir() and not p.is_symlink()),
                    key=lambda p: len(p.parts), reverse=True):
        if not (set(d.relative_to(library).parts) & KEPT_FOLDERS) and _nothing_in(d):
            out.append(d)
    return out


def delete(todo: list[Path]) -> list[str]:
    """Delete each file or folder; what can't go is said."""
    said = []
    for path in todo:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as e:
            said.append(f"{path.name}: not deleted — {e}")
    return said


def folder_move(library: Path) -> list[str]:
    """``presets/`` to ``loadable/``: a rename when there's no ``loadable/``. When there is,
    an old build saved into the old folder: file by file, never over one, what can't move
    said and left."""
    old, new = library / OLD_LOADABLE, library / LOADABLE
    if not old.is_dir():
        return []
    if not new.exists():
        old.rename(new)
        return []
    said = []
    for path in loadable_files(library):
        if not path.is_relative_to(old):
            continue
        dest = new / path.relative_to(old)
        if dest.exists():
            said.append(f"presets/{path.relative_to(old)}: loadable/ holds a file of that name "
                        "— left as it is")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        path.rename(dest)
    if not said and _nothing_in(old):
        shutil.rmtree(old)
    return said


# plan 50: the folders in a library root that hold no module presets — the
# document kinds', the shows', the trash, the old routing loadable patches
NOT_MODULES = (LOADABLE, OLD_LOADABLE, PROJECTS, INSTALLS, "patches", "playlists", "trash",
               "bindings", "media", "venues", "Docs")


def group_plan(library: Path) -> tuple[list[tuple[Path, Path, bytes]], list[str]]:
    """Plan 50 (one format): what moves to the patch's one shape — every
    module preset (``<library>/<group>/*.json``, ``hyperspace.preset/1``,
    one group's values) as a patch of that group,
    ``<library>/patches/<group>/<file>`` (``hyperspace.patch/2``, a
    ``group`` key: `patches.forward`), and every ``patch/1`` under
    ``<library>/patches/`` as its ``/2`` in place. Returns ((from, to, the
    bytes), the words for what is left: a file that will not read, a
    retired group's (`library.RETIRED_MODULES`: never read, left as it is),
    a destination already holding other bytes). A dot-file and a backup are
    left out, as everywhere."""
    from hyperspace import patches
    from hyperspace.library import RETIRED_MODULES, _json_text
    todo: list[tuple[Path, Path, bytes]] = []
    said: list[str] = []
    if not library.is_dir():
        return todo, said

    files = _retaper_tool().json_files          # (review fix 4: the one file list)
    for folder in sorted(d for d in library.iterdir() if d.is_dir()):
        if folder.name in NOT_MODULES or folder.name.startswith((".", BACKUP_PREFIX, OLD_BACKUPS)):
            continue
        for path in files(folder):
            doc = _read(path)
            if doc is None or doc.get("schema") != "hyperspace.preset/1":
                said.append(f"{folder.name}/{path.name}: not a module preset — left as it is")
                continue
            if folder.name in RETIRED_MODULES:
                said.append(f"{folder.name}/{path.name}: a retired group's — deleted")
                continue
            doc.setdefault(patches.GROUP_KEY, folder.name)
            try:
                new = patches.forward(doc)
            except ValueError as e:
                said.append(f"{folder.name}/{path.name}: {e} — left as it is")
                continue
            dest = library / "patches" / folder.name / path.name
            data = _json_text(new).encode()
            if dest.exists() and dest.read_bytes() != data:
                said.append(f"{folder.name}/{path.name}: patches/{folder.name}/{path.name} "
                            "holds another file — left as it is")
                continue
            todo.append((path, dest, data))
    for path in files(library / "patches"):
        doc = _read(path)
        if doc is None:                          # (review fix 5: said, as above)
            said.append(f"patches/{path.name}: does not read — left as it is")
            continue
        if doc.get("schema") != f"{patches.KIND}/1":
            continue                             # (already /2, or the next build's)
        todo.append((path, path, _json_text(patches.forward(doc)).encode()))
    return todo, said


def _patch_schema() -> str:
    from hyperspace import patches
    return patches.SCHEMA


def group_write(todo) -> list[str]:
    """Write `group_plan`'s files (after the run's backup): each to its
    place atomically (`write`), then a moved module preset's old file
    removed — the backup holds it. Returns what went wrong, in words."""
    said = []
    for src, dest, data in todo:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            write(dest, data)
            if src != dest:
                src.unlink()
                try:
                    src.parent.rmdir()                  # an emptied group folder goes
                except OSError:
                    pass
        except OSError as e:
            said.append(f"{src.name}: not moved — {e}")
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
    loadable patch), then renamed over the file."""
    tmp = path.parent / f".{path.name}.migrate-{time.time_ns()}.tmp"
    try:
        with open(tmp, "xb") as f:
            f.write(data)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _forced(r: Result, forced: set[str], stems: dict[str, int]) -> bool:
    """Whether ``--force`` names `r`: by its file under ``presets/`` less
    ``.json`` (``party/trip``), or by its stem alone (``trip``) only when no
    other loadable patch of the library has that stem (`stems`: each stem's count;
    review of #351 — one name never forces a loadable patch in every folder)."""
    if r.file.removesuffix(".json") in forced:
        return True
    stem = Path(r.file).stem
    return stem in forced and stems.get(stem, 1) == 1


def stem_counts(results) -> dict[str, int]:
    """Each file stem's count over `results` — counted once (`main`) and
    handed to `ambiguous_forces` and `_forced`."""
    stems: dict[str, int] = {}
    for r in results:
        stems[Path(r.file).stem] = stems.get(Path(r.file).stem, 0) + 1
    return stems


def ambiguous_forces(results, forced: set[str], stems: dict[str, int]) -> list[str]:
    """The ``--force`` names that are no loadable patch's path but a stem more than
    one loadable patch has (`stems`, `stem_counts`): each forces none, said, so the
    owner gives the folder path."""
    paths = {r.file.removesuffix(".json") for r in results}
    return sorted(n for n in forced if n not in paths and stems.get(n, 0) > 1)


def line(r: Result) -> str:
    """One loadable patch's report line."""
    head = f"{r.file:40s} {r.name!r:36s} {r.old.rpartition('/')[2] or '?':>2} → "
    if r.error:
        return f"{r.file:40s} {'':36s} {r.old.rpartition('/')[2]:>2} → --  SKIP: {r.error}"
    state = ("already /11, untouched" if r.unchanged and r.ok else
             "ok" if r.ok else "SKIP")
    why = [] if r.ok else [w for w in (
        "" if r.fixed else "its /11 is not a fixed point",
        "" if r.picture == "same" else f"round-trip picture {r.picture}") if w]
    out = f"{head}{r.new.rpartition('/')[2]}  round-trip picture: {r.picture}  fixed point: " \
          f"{'yes' if r.fixed else 'NO'}  {state}" + (f" ({'; '.join(why)})" if why else "")
    for n in r.notes:
        out += f"\n{'':44s}note: {n}"
    return out


def main(argv: list[str] | None = None, *, picture=None, running=app_running) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--library", type=Path, default=None,
                    help="the library folder (default: the config's [library] path, "
                         "else the machine home)")
    ap.add_argument("--show", default=None, metavar="NAME",
                    help="the show whose eye, looks and bus cuts an old file takes (its file "
                         "stem; default: this Mac's last show, else the library's only show)")
    ap.add_argument("--apply", action="store_true",
                    help="back the library up, then write: without it, nothing is written")
    ap.add_argument("--force", action="append", default=[], metavar="NAME",
                    help="write this loadable patch despite a picture or fixed-point difference: "
                         "its path under the folder less .json (party/trip), or its file "
                         "stem alone when no other folder has one of that stem; repeatable")
    ap.add_argument("--to", type=Path, default=None, metavar="FOLDER",
                    help="write each loadable patch that passed into FOLDER (the library is "
                         "only read; no backup)")
    a = ap.parse_args(argv)
    if a.to is not None and a.apply:
        ap.error("--to writes elsewhere; --apply rewrites the library: one of the two")
    home = machine_home()
    library = (a.library if a.library is not None else configured_library(home)).expanduser()
    library = library.resolve()
    if not (library / LOADABLE).is_dir() and not (library / OLD_LOADABLE).is_dir():
        print(f"no loadable patches at {library / LOADABLE} or {library / OLD_LOADABLE}",
              file=sys.stderr)
        return 2
    is_open, words = running()
    print(words)
    if a.apply and is_open:
        print("not run: quit Hyperspace on both Macs first", file=sys.stderr)
        return 2
    if a.apply:
        print("the other Mac can't be seen from here: it must be closed too, and stay closed "
              "until this finishes")
    try:
        _show, seed, said = rig_show(library, home, a.show)
    except LookupError as e:
        print(str(e), file=sys.stderr)
        return 2
    files = loadable_files(library)
    print(f"library: {library}  ({len(files)} loadable patches)"
          + ("" if a.apply else f"  — written to {a.to}" if a.to is not None
             else "  — dry run, nothing is written"))
    print(said)
    print("(round-trip picture: the old file as this build loads it, the show open, vs its "
          "/11 — not parity with an older build; eyeball dream patches live, hand check 366)")
    # (review 5: every /11 is computed against the module presets as the retaper leaves
    # them; a dry run and --to read a retapered scratch copy, so they report what --apply writes)
    retapers = retaper_plan(library, home)
    installs, stayed = install_plan(library) if a.to is None else ([], [])
    trash = trash_plan(library, home) if a.to is None else []
    tidy = tidy_plan(library) if a.to is None else []
    empties = empty_folders(library) if a.to is None else []
    if retapers:
        print(f"retaper first: {len(retapers)} document(s) without the taper marker — "
              + ", ".join(f"{c.kind} {p.name}" for p, c in retapers))
    for m in installs:
        print(f"show {m.src.name} → installs/{m.dest.name}")
        for words in m.said:
            print(f"  {words}")
    for words in stayed:
        print(f"  {words}")
    # plan 50: the module presets and the /1 patches into the one shape
    moves, left = group_plan(library) if a.to is None else ([], [])
    if moves:
        print(f"patches to write as {_patch_schema()}: {len(moves)} — "
              + ", ".join(f"{s.parent.name}/{s.name}" + (
                  f" → patches/{d.parent.name}/{d.name}" if s != d else "")
                  for s, d, _ in moves))
    for words in left:
        print(f"  {words}")
    for path in (*trash, *tidy):
        print(f"delete: {path.relative_to(library)}" + ("/" if path.is_dir() else ""))
    for path in empties:
        print(f"delete, nothing in it: {path.relative_to(library)}/")
    old_folder = a.to is None and (library / OLD_LOADABLE).is_dir()
    if old_folder:
        print(f"move: {OLD_LOADABLE}/ → {LOADABLE}/, last of all")
    if a.apply:
        stale = any((_read(p) or {}).get("schema") != NEWEST for p in files)
        if not (stale or retapers or installs or moves or trash or tidy or empties or old_folder
                or stayed):
            print("nothing to do: this library is already moved")
            return 0
        where = backup(library, home)
        print(f"backup: {where}")
        for problem in delete(trash):
            print(problem)
        for problem in retaper_write(retapers):
            print(problem)
        if retapers:
            print(f"retapered {len(retapers)} document(s) along the effect tapers")
        moves, _ = group_plan(library)          # (over what the retaper wrote)
        for problem in group_write(moves):
            print(problem)
        if moves:
            print(f"wrote {len(moves)} patch(es) as {_patch_schema()}")
    forced = set(a.force)
    results: list[Result] = []
    paths: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(prefix="hyperspace-migrate-") as scratch:
        # (review 2.7: a copy only when a document the loads read is retapered)
        read_from = (retapered_copy(library, retapers, Path(scratch) / "retapered")
                     if not a.apply and shared_retapers(library, retapers) else library)
        for k, path in enumerate(files):
            file = under_folder(library, path)
            r = check(path, read_from, Path(scratch) / str(k), picture=picture, show=seed,
                      file=file)
            results.append(r)
            paths[file] = path
            print(line(r), flush=True)
    counts: dict[str, int] = {}
    for r in results:
        counts[r.old] = counts.get(r.old, 0) + 1
    print("\nby schema found: " + ", ".join(f"{s}: {n}" for s, n in sorted(counts.items())))
    stems = stem_counts(results)
    for name in ambiguous_forces(results, forced, stems):
        print(f"--force {name}: {stems[name]} patches have that name in different folders — "
              f"give the folder path (party/{name}); none forced by it")
    writes = [r for r in results if not r.error and (not r.unchanged or a.to is not None)
              and (r.ok or _forced(r, forced, stems))]
    skipped = [r for r in results if not r.ok
               and (r.error or not _forced(r, forced, stems))]
    untouched = [r for r in results if r.ok and r.unchanged]
    troubles = list(stayed)
    if a.to is not None:
        a.to.mkdir(parents=True, exist_ok=True)
        for r in writes:
            (a.to / r.file).parent.mkdir(parents=True, exist_ok=True)
            write(a.to / r.file, r.data)
        print(f"wrote {len(writes)} as /11 into {a.to}, skipped {len(skipped)}")
    elif a.apply:
        for r in writes:
            write(paths[r.file], r.data)
        print(f"rewrote {len(writes)} as /11, left {len(untouched)} untouched (already /11), "
              f"skipped {len(skipped)}")
        # the shows, last of the file rewrites: `install_plan` again, over what is written now
        installs, stayed = install_plan(library)
        troubles = list(stayed)
        troubles += install_write(installs)
        print(f"wrote {len(installs)} install file(s)")
        troubles += delete(tidy_plan(library))
        troubles += delete(empty_folders(library))
        troubles += folder_move(library)
        for words in troubles:
            print(words)
    else:
        print(f"would rewrite {len(writes)} as /11, leave {len(untouched)} untouched "
              f"(already /11), skip {len(skipped)}"
              + (f"; retaper {len(retapers)} first" if retapers else "")
              + f"; write {len(installs)} install file(s); delete {len(trash) + len(tidy)} and "
                f"{len(empties)} empty folder(s)"
              + (f"; write {len(moves)} patch(es) as {_patch_schema()}" if moves else ""))
    if skipped:
        print("\nnot written" + (" (rerun with --force NAME to write one anyway)"
                                 if any(not r.error for r in skipped) else "") + ":")
        for r in skipped:
            why = r.error or "; ".join(w for w in (
                "" if r.fixed else "its /11 is not a fixed point",
                "" if r.picture == "same" else f"round-trip picture {r.picture}") if w)
            print(f"  {r.file.removesuffix('.json')}: {why}")
    return 1 if skipped or troubles else 0


if __name__ == "__main__":
    raise SystemExit(main())
