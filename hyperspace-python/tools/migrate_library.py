#!/usr/bin/env python3
"""Rewrite a library's presets as the newest schema, once (row 394).

    uv run python tools/migrate_library.py [--library PATH] [--show NAME] [--apply]
                                           [--force NAME …]
    uv run python tools/migrate_library.py --library PATH --to FOLDER [--force NAME …]

The owner's decision of 2026-10-25: both Macs always run the newest build,
so every preset in the library is moved to the newest schema and old
schemas stop circulating. Since plan 44 D3 (rows 611–625) that is
``hyperspace.preset/10`` — plan 36 T3's graph that says everything (every
edge a wire, ``/7``), the GRAPH page's groups (``/8``), the one orbit
camera (``/9``, plan 43 C2: the eye in every preset's ``values``) and the
look made whole (``/10``: the hands' and clouds' looks — ``ghost.*`` but
``ghost.mirror``, ``cloud.*`` — in ``values`` and the bus cuts in
``bus``, where until now the open show held them; no ``modules`` labels,
no ``desk_template``) — and every show to ``hyperspace.project/3`` (the
rig's session, the pads and ``startup``). A load reads an older file
through the one-way migration (`graphmigrate.seven`, then `nine`, then
`ten`), so a library not yet at ``/9`` takes the ``/9`` step first in the
same pass: one run, one backup. Each preset in ``<library>/presets/``,
every folder down as the library lists them (plan 48; not ``trash/``,
not a hidden folder, not a backup, not a dot-file) is loaded and saved untouched
by the app itself (`hyperspace.headless.resave`: the registry, library,
router and presets the tests save through) in a scratch library — the
library's module presets beside it, and **the rig's
show open** (below) — and three checks are made:

- it loads (a file this build refuses is left as it is);
- the ``/10`` is a fixed point: loaded and saved untouched again it is the
  same bytes;
- its save round-trips the picture: the original file and its ``/10`` are
  each drawn on the golden-frame rig (tools/golden_frames.py `picture`:
  offscreen, the clock pinned, hands present, eight windows on the rig as
  it ships, `SHIPPED`: each shows its own wires, else All outputs' by its
  bus cables), the same show open, and every output's hash must match.
  Both are drawn by *this* build — the original through the same one-way
  migration a load runs — so "round-trip picture: same" proves the
  written ``/10`` draws what this build draws of the old file with the
  rig's show open (the eye included), never that it draws what an older
  build drew. That parity is the migration's tests and the eye: a preset
  with a look-back or a dream is eyeballed live on the old and new build
  (hand check 366, party-wake).

**The rig's show** (plan 43 C2, plan 44 D3): an old preset drew through
the eye, the hands' and clouds' looks and the bus cuts the open show held,
so its ``/10`` takes that show's — the eye and the looks from its
``session``, the camera node's GRAPH position from its ``layout``, the
cuts from its ``rig`` — exactly as the app hands them to an old preset's
load (`library.Project.old_eye`, `old_look`, `old_cuts`): **the show's
cuts are written into every preset the library holds** (as the ``/9``
step wrote the show's eye into every preset), since each preset now says
for itself which cables stand.
The show is ``--show NAME`` (a file stem under ``<library>/projects/``),
else this Mac's last show (``<home>/last_show``), else the library's one
show; none (or a show that holds no eye, nor a ``.bak-v2-eye`` copy of
itself that does) is the build's default eye, and the tool says which.
Every show in ``<library>/projects/`` that is ``/2`` or holds the eye or
the camera's position is then rewritten as ``/3`` without them
(`library.show_without_eye`, `show_without_look`), ``<file>.bak-v2-look``
kept beside a ``/2`` and ``<file>.bak-v2-eye`` beside a ``/3`` that still
held the eye (the app's own backups, `library.LOOK_BACKUP`, `EYE_BACKUP`).

**The retaper first** (wave 0 T1, tools/retaper_routes.py): one bump moves
everything, so ``--apply`` measures every document of the library still
without the taper marker (``units["fx.depth"] == "taper"``) along the
effect tapers before anything else — the patches and this Mac's ``bindings.json`` (kept as ``bindings.json.bak-v3``) as
retaper_routes.py writes them. A preset is retapered by its own resave
(its load measures an unmarked file's depths, its save writes the marker),
so every ``/10`` is along the tapers. The dry run says what it would
retaper.

**One format** (plan 50): every module preset — ``<library>/<group>/*.json``,
``hyperspace.preset/1``, one group's values — is written as a patch of
that group, ``<library>/patches/<group>/<file>`` (``hyperspace.patch/2``
with a ``group`` key, `patches.forward`), its old file removed (the backup
holds it); every ``patch/1`` under ``<library>/patches/`` is written as
its ``/2`` in place. A retired group's files (``fx/``) and a file that
does not read are left as they are, said. ``--to`` moves none. The dry run
lists them.

An old file (before ``/7``) whose load says its section was "not read"
(the build refused it: black) is **not written**, whatever ``--force``
says: its ``/10`` would carry the old words with the migration lost for
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
the retapered module presets; a dry run computes against a retapered scratch
copy, so it says what --apply writes), in place and
atomically (a dot-named temp file renamed over it), under its own file
name, then the shows. A file whose bytes the save would not change
(already ``/10`` and a fixed point) is left untouched. A preset that failed
a check is **not written** and is listed at the end — unless ``--force
NAME`` (its file stem; repeatable) names it, which writes it despite a
picture or fixed-point difference (a file that does not load has nothing
to write). No name changes. **Run it between shows, with both Macs on this
build**: a Mac on an older build refuses a ``/10`` and a ``/3`` show.

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
NEWEST = "hyperspace.preset/10"           # plan 44 D3 (rows 611–625)
SHOW_NEWEST = "hyperspace.project/3"
# what a load note says of a graph section the build refused (preset.py:
# `GraphSection.read`, `UNWIRED_SAID`)
NOT_READ = "not read — black"


@dataclass
class Result:
    """What one preset's checks found."""

    file: str                       # the file's path under presets/ (party/trip.json), kept
    name: str = ""                  # the preset's own name
    old: str = "?"                  # its schema as found
    new: str = ""                   # the schema it saves as
    notes: list[str] = field(default_factory=list)
    error: str = ""                 # it does not load (nothing to write)
    fixed: bool = False             # the /10 re-saves as itself
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
    """The library's presets: ``presets/`` every folder down, as the library
    lists them (`library._walk`, plan 48 stage 2: hidden folders skipped,
    never through a link) — a dot-file (a write's temp file), a backup
    (``.bak-``) and anything in ``trash/`` left out."""
    from hyperspace.library import _walk

    folder = library / PRESETS
    if not folder.is_dir():
        return []
    return [p for p in _walk(folder)
            if p.is_file() and not p.name.startswith(".") and ".bak-" not in p.name]


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
    from hyperspace.library import (
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
            return None, None, (f"show: none ({why}) — every preset takes the build's "
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
    said += (f"; {len(cut)} bus cut(s) into every preset: "
             + ", ".join(f"{c['from']} → {c['to']}" for c in cut) if cut else "; no bus cut")
    return path, seed, f"show: {path.name[: -len(SHOW_SUFFIX)]} ({how}) — {said}"


def check(path: Path, library: Path, scratch: Path, *, picture=None,
          show: dict | None = None, file: str | None = None) -> Result:
    """Load, save, re-save and draw preset file `path` (`picture`: the
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
        res.error = ("its graph section was not read by this build (black) — writing its /10 "
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
        res.notes = [*res.notes, f"its /10 does not load: {e}"]
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
    The presets are retapered by their own resave."""
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
    """Whether `retaper_plan` would rewrite a document a preset's load reads
    beside it (`headless.SHARED_FOLDERS`, the module presets — none today:
    the retaper rewrites patches and `bindings.json`, plan 44 D3 retired the
    desk templates) — else the library itself is what every preset is
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
    """The folders copied beside a preset for its load (`headless.SHARED_FOLDERS`:
    the module presets) copied to `dest`, each document
    of `retaper_plan`'s that lives there written as the retaper writes it —
    what a dry run or --to computes every preset's /10 against, so it is what
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
    """Every show in the library that is ``/2`` (plan 44 D3) or holds the eye
    or the camera's GRAPH position (plan 43 C2), with its bytes as ``/3``
    without them (`library.show_without_eye`, `show_without_look`)."""
    from hyperspace.library import show_text, show_without_eye, show_without_look
    out = []
    for path in show_files(library):
        doc = _read(path)
        if doc is None:
            continue
        new = show_without_eye(doc) or doc
        new = show_without_look(new) or new
        if new is not doc:
            out.append((path, show_text(new).encode()))
    return out


def show_write(todo) -> list[str]:
    """Write `show_plan`'s shows, each kept first (`routing.backup`, the
    app's own) as ``<file>.bak-v2-look`` when it was ``/2``, else
    ``<file>.bak-v2-eye``; no backup, no write."""
    from hyperspace import routing
    from hyperspace.library import EYE_BACKUP, LOOK_BACKUP, PROJECT_V2
    said = []
    for path, data in todo:
        tag = LOOK_BACKUP if (_read(path) or {}).get("schema") == PROJECT_V2 else EYE_BACKUP
        if routing.backup(path, tag) is None:
            said.append(f"{path.name}: not rewritten — no backup could be made")
            continue
        write(path, data)
    return said


# plan 50: the folders in a library root that hold no module presets — the
# document kinds', the shows', the trash, the old routing presets
NOT_MODULES = (PRESETS, PROJECTS, "patches", "trash", "bindings")


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
        if folder.name in NOT_MODULES or folder.name.startswith((".", BACKUP_PREFIX)):
            continue
        for path in files(folder):
            doc = _read(path)
            if doc is None or doc.get("schema") != "hyperspace.preset/1":
                said.append(f"{folder.name}/{path.name}: not a module preset — left as it is")
                continue
            if folder.name in RETIRED_MODULES:
                said.append(f"{folder.name}/{path.name}: a retired group's — left as it is")
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
    preset), then renamed over the file."""
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
    other preset of the library has that stem (`stems`: each stem's count;
    review of #351 — one name never forces a preset in every folder)."""
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
    """The ``--force`` names that are no preset's path but a stem more than
    one preset has (`stems`, `stem_counts`): each forces none, said, so the
    owner gives the folder path."""
    paths = {r.file.removesuffix(".json") for r in results}
    return sorted(n for n in forced if n not in paths and stems.get(n, 0) > 1)


def line(r: Result) -> str:
    """One preset's report line."""
    head = f"{r.file:40s} {r.name!r:36s} {r.old.rpartition('/')[2] or '?':>2} → "
    if r.error:
        return f"{r.file:40s} {'':36s} {r.old.rpartition('/')[2]:>2} → --  SKIP: {r.error}"
    state = ("already /10, untouched" if r.unchanged and r.ok else
             "ok" if r.ok else "SKIP")
    why = [] if r.ok else [w for w in (
        "" if r.fixed else "its /10 is not a fixed point",
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
                    help="the show whose eye, looks and bus cuts the presets take (its file "
                         "stem; default: "
                         "this Mac's last show, else the library's only show)")
    ap.add_argument("--apply", action="store_true",
                    help="back the library up, retaper, then rewrite every preset that "
                         "passed as /10 and every show as /3")
    ap.add_argument("--force", action="append", default=[], metavar="NAME",
                    help="write this preset despite a picture or fixed-point difference: "
                         "its path under presets/ less .json (party/trip), or its file "
                         "stem alone when no other folder has a preset of that stem; "
                         "repeatable")
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
          "/10 — not parity with an older build; eyeball dream presets live, hand check 366)")
    # (review 5: every preset's /10 is computed against the module presets as the
    # retaper leaves them — with --apply the library is backed up and
    # retapered first; a dry run and --to read a retapered scratch copy, so
    # they report what --apply writes. --to writes only presets.)
    retapers = retaper_plan(library, home)
    shows = show_plan(library) if a.to is None else []
    if retapers:
        print(f"retaper first: {len(retapers)} document(s) without the taper marker — "
              + ", ".join(f"{c.kind} {p.name}" for p, c in retapers))
    if shows:
        print(f"shows to rewrite as /3: {len(shows)} — "
              + ", ".join(p.name for p, _ in shows) + " (each kept as .bak-v2-look or "
              ".bak-v2-eye)")
    # plan 50: the module presets and the /1 patches into the one shape
    moves, left = group_plan(library) if a.to is None else ([], [])
    if moves:
        print(f"patches to write as {_patch_schema()}: {len(moves)} — "
              + ", ".join(f"{s.parent.name}/{s.name}" + (
                  f" → patches/{d.parent.name}/{d.name}" if s != d else "")
                  for s, d, _ in moves))
    for words in left:
        print(f"  {words}")
    if a.apply:
        where = backup(library, home)
        print(f"backup: {where}")
        for problem in retaper_write(retapers):
            print(problem)
        if retapers:
            print(f"retapered {len(retapers)} document(s) along the effect tapers")
        moves, _ = group_plan(library)          # (over what the retaper wrote)
    forced = set(a.force)
    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="hyperspace-migrate-") as scratch:
        # (review 2.7: a copy only when a document the loads read is retapered)
        read_from = (retapered_copy(library, retapers, Path(scratch) / "retapered")
                     if not a.apply and shared_retapers(library, retapers) else library)
        for k, path in enumerate(files):
            r = check(path, read_from, Path(scratch) / str(k), picture=picture, show=seed,
                      file=path.relative_to(library / PRESETS).as_posix())
            results.append(r)
            print(line(r), flush=True)
    counts: dict[str, int] = {}
    for r in results:
        counts[r.old] = counts.get(r.old, 0) + 1
    print("\nby schema found: " + ", ".join(f"{s}: {n}" for s, n in sorted(counts.items())))
    stems = stem_counts(results)
    for name in ambiguous_forces(results, forced, stems):
        print(f"--force {name}: {stems[name]} presets have that name in different folders — "
              "give the folder path (party/{name}); none forced by it".replace("{name}", name))
    writes = [r for r in results if not r.error and (not r.unchanged or a.to is not None)
              and (r.ok or _forced(r, forced, stems))]
    skipped = [r for r in results if not r.ok
               and (r.error or not _forced(r, forced, stems))]
    untouched = [r for r in results if r.ok and r.unchanged]
    if a.to is not None:
        a.to.mkdir(parents=True, exist_ok=True)
        for r in writes:
            (a.to / r.file).parent.mkdir(parents=True, exist_ok=True)
            write(a.to / r.file, r.data)
        print(f"wrote {len(writes)} as /10 into {a.to}, skipped {len(skipped)}")
    elif a.apply:
        for r in writes:
            write(library / PRESETS / r.file, r.data)
        print(f"rewrote {len(writes)} as /10, left {len(untouched)} untouched (already /10), "
              f"skipped {len(skipped)}")
        for problem in show_write(shows):
            print(problem)
        if shows:
            print(f"rewrote {len(shows)} show(s) as /3")
        for problem in group_write(moves):
            print(problem)
        if moves:
            print(f"wrote {len(moves)} patch(es) as {_patch_schema()}")
    else:
        print(f"would rewrite {len(writes)} as /10, leave {len(untouched)} untouched "
              f"(already /10), skip {len(skipped)}"
              + (f"; retaper {len(retapers)} first" if retapers else "")
              + (f"; rewrite {len(shows)} show(s) as /3" if shows else "")
              + (f"; write {len(moves)} patch(es) as {_patch_schema()}" if moves else ""))
    if skipped:
        print("\nnot written" + (" (rerun with --force NAME to write one anyway)"
                                 if any(not r.error for r in skipped) else "") + ":")
        for r in skipped:
            why = r.error or "; ".join(w for w in (
                "" if r.fixed else "its /10 is not a fixed point",
                "" if r.picture == "same" else f"round-trip picture {r.picture}") if w)
            print(f"  {r.file.removesuffix('.json')}: {why}")
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
