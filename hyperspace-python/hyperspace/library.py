"""The preset & project library — the Ableton model over the registry.

Two kinds of file, both plain JSON you can open in a text editor:

  module preset   one registry *group* (view, camera, band…) —
                  ``{"schema": "hyperspace.preset/1", "group", "name",
                  "values": {id: base}}``, produced by ``Registry.snapshot
                  (group)`` and applied with ``Registry.restore``. The
                  analyzer's presets also carry ``layout`` (see the
                  contract in docs/plans/07-overhaul.md): restore hands the
                  layout to a hook registered with ``on_layout`` *before*
                  the values, so a preset can rebuild its params first,
                  and a save asks the group's ``extra`` hook for it. The
                  analyzer's *scenes* are their own data, shipped with the
                  code (hyperspace/scenes/band/, control.py) — a band
                  preset in the library is the user's own, and a strip
                  load tells the scene combo through ``on_load``.
  project         the show — ``{"schema": "hyperspace.project/3",
                  "name", "note", "startup": <preset name>, "bank": [8–24
                  × <preset name> | null], "session": <session snapshot>,
                  "modules": {group: name | {"name", "values", …}}}``, in
                  a ``*.hyp.json`` file (params.PARTS is the split; plan
                  13 §2.2). ``session`` lands on a project load and a
                  preset never touches it; ``modules`` names the session
                  groups' module presets (the band strip's scene and
                  layout). The **bank** is twenty-four pointers to preset
                  files (``SLOTS``; preset.py) — the desk's pads: the
                  APC40's clip rows 1, 4 and 5 load one each
                  (``Project.load_slot``), F1–F8 the first eight
                  (``F_KEYS``), ⇧F1–F8 save the live state *as* it
                  (``save_slot``); ``startup`` is the preset Home brings
                  up (``Project.home``) and a launch opens with, kept in
                  the file, set by nothing on the panel since 2026-10-28.
                  The file holds the bank only as far as its last filled
                  slot, never fewer than eight entries (``bank_doc``, plan
                  19 WP1), and the first write that makes a file's bank
                  longer keeps the eight-slot file beside it first
                  (``<file>.bak-v2-bank8``, ``Project.write``). A module
                  the project names by a preset that carries a ``layout``
                  gets that layout back on load, the same road a strip
                  load takes. A schema-1 project is refused (no old-schema
                  support, 2026-10-25). Plan 44 D3 (``/3``): the show
                  is the rig's session, the pads and ``startup`` — the
                  bus cuts (plan 36 T1's ``rig``) and the hands' and
                  clouds' looks (``ghost.*`` but ``ghost.mirror``,
                  ``cloud.*``) are each preset's now. A ``/2`` show is
                  read as its ``/3`` (`show_without_look`): what it held
                  of the look is handed to every preset before ``/10``
                  a load reads while it is open (``Project.old_look``,
                  ``old_cuts``), and its first write keeps the ``/2``
                  beside it (``<file>.bak-v2-look``).

A third kind of document is *not* the library's own format but goes
through the same doors: a **document kind** registered with ``kind()``
— the presets, ``hyperspace.preset/2`` (``/3`` since plan 31, written
only when needed: a build that takes /2 alone refuses one, `read`)
under ``presets/``, which preset.py's ``Presets`` loads and writes (the
one kind since plan 13 WP5 made the routing presets presets). For such a group the
library does the file half — list, load / save as / delete / rename, the
dirty dot, the watch — and the kind's hooks do the document half:
``load(doc, path)`` applies it, ``document(name)`` is what a save
writes, ``signature()`` is what ``is_dirty`` compares. One strip
(ui_presets.py) then serves every group.

Library layout — **one tier** (2026-10-28): every preset is the user's,
listed, loaded, renamed and deleted alike. Nothing ships in the wheel,
nothing is "factory", nothing is hidden; a fresh library is empty, and
the app starts on a blank preset in an unsaved show.

  $HYPERSPACE_HOME/<group>/<slug>.json       module presets (default ~/Hyperspace,
                                 or the [library] path, plan 25)
  $HYPERSPACE_HOME/presets/[<folder>/…/]<slug>.json
                                 presets, in folders if the owner made
                                 any (plan 48): listed every folder down,
                                 less hidden ones, by folder-qualified name
                                 (``party/TRIP``; ``_index``, `path_slug`)
  $HYPERSPACE_HOME/patches/<slug>.json       patches (plan 40)
  $HYPERSPACE_HOME/projects/<slug>.hyp.json  shows
  $HYPERSPACE_HOME/config.toml, bindings.json (a midi_map.json is only
                                 migrated in and read once, routing.py)
  $HYPERSPACE_HOME/bindings/      the old routing presets: made presets
                                 once (plan 13 WP5) and never read again,
                                 so no group (LEGACY_DIRS)
  <machine>/trash/<group>/[<folder>/]<slug>.<date>-<time>.json
                                 (this Mac's home, never the shared library:
                                 plan 48; a ``<library>/trash`` from before
                                 is listed, restorable, never emptied)
                                 a preset file as it was before a save
                                 overwrote it or a delete removed it
                                 (``to_trash``, plan 15) or a rename replaced
                                 it: no group, never watched; listed,
                                 restored and emptied from the PRESETS page
                                 (``trash``, ``restore_trash``,
                                 ``empty_trash``, plan 19 WP4)

``home()`` is the one resolver for that folder (config.py and the binding
table path go through it). On the first run the working-directory ``config.toml``
and ``midi_map.json`` are copied in — originals are left alone.

Which show opens (decision 22, plan 14 WP3): the one opened last, its
name in ``<home>/last_show`` (one line, written by every load and save
as). None, or one that is gone or will not read (the reason in `error`),
and the app starts on an unsaved show called ``untitled`` with an empty
bank (``_open_default``).

Loading a module preset fills ids it doesn't name from the group's
*default* preset (DEFAULT_NAMES, else one called "default", else the
values the objects were constructed with); a whole preset (preset.py)
fills them from the values the objects were constructed with alone
(`_fresh_of`, plan 44 D3 — never a ``default.json``), so a preset is the
same state whatever it lands on; ids the registry doesn't know are reported in ``warning`` and
returned, never fatal. ``is_dirty(group)`` says whether the group's bases
have moved off what the loaded (or default) preset would produce.

The tree is watched like source: ``poll()`` (hotreload.py calls it) picks
up an edited file and re-applies the preset or project that is loaded
from it, so a tweak in an editor shows in the running app. A ``schema``
string on every file plus MIGRATIONS below is how the formats grow.
"""

from __future__ import annotations

import copy
import itertools
import json
import math
import os
import re
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import patches as patchdoc
from . import undo
from .graph import RigWires
from .graphmigrate import CAMERA_NODES, EYE_IDS, renamed_layout, retired
from .palettecompat import palette_slice
from .params import (
    F_KEYS,
    PERFORMANCE_GROUPS,
    SESSION_GROUPS,
    UNITS,
    UNITS_KEY,
    Registry,
    fx_files,
    is_instance_id,
    pan_world,
    part_of_id,
    retaper_depths,
)

SLOTS = 24                # the bank: F1–F8, then the desk's clip rows 4 and 5
# F_KEYS (8) is the slots a function key reaches, and a show file's bank is
# never shorter. It is imported from params, where the F-keys' load / save
# triggers are declared (params may not import library); `library.F_KEYS`
# is the name the rest of the app reads.
# BANK8_BACKUP: the copy `Project.write` makes before the first write that
# puts more than F_KEYS entries in a show file, <file>.bak-v2-bank8
# (routing.backup's schema argument)
BANK8_BACKUP = "2-bank8"
# SPRING_BACKUP: the copy `Project.write` makes before the first write that
# drops a show's stick spring as it was stored before 2026-10-29
# (`desk.pad.hz` / `.damp`, read as today's knobs by routing.renamed_session),
# <file>.bak-v2-spring
SPRING_BACKUP = "2-spring"
# EYE_BACKUP (plan 43 C2): the copy `Project.write` makes before the first
# write that drops a show's eye — `eye.fov` / `eye.distance` in its
# `session`, which the presets hold since `/9` (`Project.old_eye`) —
# <file>.bak-v2-eye
EYE_BACKUP = "2-eye"
# LOOK_BACKUP (plan 44 D3): the copy `Project.write` makes before the first
# write of a `/2` show as `/3` — which drops its bus cuts (`rig`) and the
# hands' and clouds' looks from its `session`, each preset's since `/10` —
# <file>.bak-v2-look
LOOK_BACKUP = "2-look"
PRESETS = "presets"       # the presets' group, a document kind (preset.py)
# (plan 24 C3's desk templates, `<root>/desk/`, are retired — plan 44 D3,
# the owner, 2026-11-03: neither library held one)
# <root>/patches/<slug>.json (plan 40 P1): the patches — a group of nodes
# and its boundary, saved once, spawned anywhere (patches.py). A document
# kind of the library's own (`Library.__init__`), so the folder lists,
# renames and goes to the trash like the presets'; but a patch is never
# loaded through the group's door — it is spawned (`patches.spawn`) — so
# the kind's `load` refuses, and its `document` and `signature` are never
# asked. Read through `read_patch` (the schema and `patches.check`),
# written through `save_patch`
PATCHES = "patches"
PATCH_SCHEMA = patchdoc.SCHEMA          # "hyperspace.patch/1"
PATCH_SPAWNED = "a patch is spawned, not loaded"
# the groups `rename` serves: the presets and the patches (a module preset
# is saved under another name instead)
RENAMABLE = (PRESETS, PATCHES)
# folders in a library root that are no group: the routing presets' old
# folder, kept as it was by plan 13's migration and never read again
LEGACY_DIRS = ("bindings",)
# <home>/trash/<group>/: a preset file as it was, copied there before a
# save overwrites it or a delete removes it (`to_trash`, plan 15 WP1).
# No group and never watched. Plan 19 WP4 lists it (`Library.trash`), puts a
# file back (`restore_trash`, never over a file) and empties it
# (`empty_trash`, the one delete in the app that keeps no copy)
TRASH = "trash"
# the trash's file names: <stem>.<YYYYMMDD-HHMMSS>[-n]<suffix> (`to_trash`)
_TRASHED = re.compile(r"(?P<stem>.+)\.(?P<stamp>\d{8}-\d{6})(?:-(?P<n>\d+))?(?P<suffix>\.[^.]+)")
HOME_ENV = "HYPERSPACE_HOME"
DEFAULT_HOME = Path("~/Hyperspace")

PRESET_SCHEMA = "hyperspace.preset/1"      # a module preset (one group)
PERFORMANCE_SCHEMA = "hyperspace.preset/2" # a preset: the performance (preset.py)
PROJECT_SCHEMA = "hyperspace.project/3"   # plan 44 D3: the rig's session, the pads, startup
PROJECT_V2 = "hyperspace.project/2"        # read as its /3 (`show_without_look`), once
PROJECT_V1 = "hyperspace.project/1"        # refused: no old-schema support (2026-10-25)
PROJECT_SUFFIX = ".hyp.json"
PROJECTS = "projects"
LAST_SHOW = "last_show"             # <home>/last_show: the show opened last
UNTITLED = "untitled"
# the tail of save-as's note on a full bank (`Project.save_new`)
BANK_FULL = "the bank is full: it is in the preset list"
# what `Project.home` says when the show names no startup preset (plan 15 WP2)
HOME_UNSET = "home: this show names no startup preset"
# plan 28 N2: where the GRAPH page's nodes sit, ``{"<node id>": [x, y]}`` —
# a show's own key for the rig's nodes (devices, the analyzer, the LFOs,
# the outputs), a preset's (preset.LAYOUT_KEY) for the look's. No key: every
# node is laid out automatically, and nothing is dirty
LAYOUT = "layout"
# plan 36 T1: a `/2` show's own wires (`graph.RigWires`) — the bus cuts,
# each preset's since plan 44 D3 (preset.BUS_KEY): read out of an old show
# once (`show_look`), never written
RIG = "rig"


def read_layout(value: Any) -> tuple[dict[str, list[float]], int]:
    """A file's ``layout`` value as {node id: [x, y]} (whole canvas units),
    and how many entries were not a name and two finite numbers (dropped).
    None is an empty map; a value that is no map, an empty map and one drop.
    R14 (plan 35 T5): a layout saved in the canvas's old ids is read in the
    wired frame's (`graphmigrate.renamed_layout`), so its positions stay."""
    out, bad = read_positions(value)
    return renamed_layout(out), bad


def read_positions(value: Any) -> tuple[dict[str, list[float]], int]:
    """`read_layout` in the file's own ids, nothing renamed: what a build
    from before plan 35 read (R15 — a save below `/6` writes these back)."""
    if value is None:
        return {}, 0
    if not isinstance(value, dict):
        return {}, 1
    out: dict[str, list[float]] = {}
    bad = 0
    for k, xy in value.items():
        try:
            x, y = (float(v) for v in xy)
        except (TypeError, ValueError):
            bad += 1
            continue
        if not (isinstance(k, str) and k and math.isfinite(x) and math.isfinite(y)):
            bad += 1
            continue
        out[k] = [round(x), round(y)]
    return out, bad

# the preset a group resets to; any other group uses one named "default"
# if it has one, else the values its objects were built with
DEFAULT_NAMES = {"band": "Balanced"}

# the groups whose module presets are retired outright (plan 40 T5, D6:
# "It is not a useful representation of shaders anymore"): no strip, no
# entry in `groups()`, no default preset — `defaults` is the fresh values
# even where an old `<library>/fx/default.json` survives. Their params are
# untouched: the effects are the graph's (the FX page, D10, stays)
RETIRED_MODULES = ("fx",)

# working-directory files that move into the library home on first run
MIGRATED_FILES = ("config.toml", "midi_map.json")


class LibraryError(Exception):
    pass


# library roots that were named but not there at launch (plan 25 D5): no
# write may land under one — `_write_text` and `to_trash` refuse it, so a
# writer that forgot to ask `Library.writable` still creates nothing
_missing: set[Path] = set()


def missing_text(path: Path) -> str:
    """What a write into a missing shared library says (plan 25 D5)."""
    return (f"shared library not found at {path} — not saved; fix [library] path or the "
            "folder, then restart")


def _refuse_missing(path: Path) -> None:
    for root in _missing:
        if path == root or root in path.parents:
            raise LibraryError(missing_text(root))


# ---------------------------------------------------------------- home

def home() -> Path:
    """The library folder: $HYPERSPACE_HOME, else ~/Hyperspace. Not created."""
    raw = os.environ.get(HOME_ENV)
    return (Path(raw) if raw else DEFAULT_HOME).expanduser()


_ensured: set[Path] = set()   # homes this process has already made and migrated


def ensure_home(root: Path | None = None, cwd: Path | None = None) -> Path:
    """Create the library home and pull in the working-directory files —
    once per home per process: config.load and Library() both ask, and
    the first-run migration should not scan the working directory twice."""
    root = home() if root is None else root
    if root in _ensured and (root / PROJECTS).is_dir():
        return root
    (root / PROJECTS).mkdir(parents=True, exist_ok=True)
    for msg in migrate(root, cwd):
        print(msg, file=sys.stderr)
    _ensured.add(root)
    return root


def migrate(root: Path, cwd: Path | None = None) -> list[str]:
    """First-run move of config and MIDI map; returns what moved.

    Copies, never deletes — a file already in the home is never touched,
    so this is a no-op from the second run on.
    """
    cwd = Path.cwd() if cwd is None else cwd
    done = []
    for name in MIGRATED_FILES:
        src, dst = cwd / name, root / name
        if src.is_file() and not dst.exists():
            shutil.copyfile(src, dst)
            done.append(f"library: copied {src} → {dst}")
    return done


# ---------------------------------------------------------------- files

def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "untitled"


def path_slug(name: str) -> str:
    """A preset's file key from its folder-qualified name (plan 48 row
    584): ``party/TRIP 2`` → ``party/trip-2`` — the folder as it is on
    disk (each segment stripped of spaces at its ends), the leaf through
    `slug`. ``/`` is only ever the folder separator: a segment that is
    empty, ``.``, ``..`` or hidden (``.cache``) — and so an absolute path
    — raises LibraryError, so a name can never point a read or a write
    outside ``presets/``. `slug` itself stays flat: shows, module presets
    and patches have no folders, and a ``/`` in their names is a ``-``."""
    name = str(name)
    folder, _, leaf = name.rpartition("/")
    parts = [s.strip() for s in folder.split("/")] if "/" in name else []
    if any(not s or s.startswith(".") for s in parts):
        raise LibraryError(f"{name}: not a preset name — a folder may not be empty, "
                           "hidden or '..'")
    return "/".join([*parts, slug(leaf)])


def split_name(name: str) -> tuple[str, str]:
    """``party/deep/TRIP`` → (``party/deep``, ``TRIP``); a bare name's
    folder is ``""`` (plan 48)."""
    folder, _, leaf = str(name).rpartition("/")
    return folder, leaf


def fold(name: str) -> str | None:
    """The one comparison key of a preset name (plan 48): `path_slug`,
    lowered — folder segments stripped and case-folded, the leaf slugged
    (``Party /TRIP 2`` → ``party/trip-2``), as APFS would find the file.
    None for a name that could name no file (``../x``)."""
    try:
        return path_slug(name).lower()
    except LibraryError:
        return None


def fold_folder(folder: str) -> str | None:
    """`fold` of a folder alone: ``""`` for the top, None for one that
    could hold no preset."""
    if not folder:
        return ""
    key = fold(f"{folder}/x")
    return None if key is None else key[:-2]


def harmless(name: str) -> str:
    """A preset's own ``name`` as the list shows it (plan 48 review): a
    ``/`` in a listed name always means a folder, so a file whose own name
    holds one (``AC/DC``, from before folders) is listed with it made a
    ``" - "`` (``AC - DC``) — no reader splits it, no writer makes a
    folder of it; a save writes the shown name back into the file."""
    return name.replace("/", " - ")


def next_name(base: str | None, taken: set[str], *, key=None) -> str:
    """A name for a new preset grown from `base`, the loaded preset's name
    (plan 15 WP4, fork 16): the first ``"<stem> <n>"`` whose slug is not in
    `taken`, a set of slugs. A base that ends in whitespace and a number
    after a non-empty stem counts on from that number (``TRIP 2`` →
    ``TRIP 3``); any other is its own stem and counting starts at 2
    (``TRIP`` → ``TRIP 2``, ``2001`` → ``2001 2``). With no base the stem
    is ``PRESET`` and counting starts at 1. `key` is what a candidate is
    compared by (`slug`; for a preset in a folder the caller's
    `Library._fold` of the qualified name, plan 48 — the one fold)."""
    key = key or slug
    base = (base or "").strip()
    if not base:
        stem, n = "PRESET", 1
    else:
        m = re.fullmatch(r"(.*\S)\s+(\d+)", base, re.DOTALL)
        stem, n = (m.group(1), int(m.group(2)) + 1) if m else (base, 2)
    while key(f"{stem} {n}") in taken:
        n += 1
    return f"{stem} {n}"


def slot_key(k: int) -> str:
    """What a slot is called in a message and on the page: "F3" for the
    first F_KEYS, "slot 12" after."""
    return f"F{k + 1}" if k < F_KEYS else f"slot {k + 1}"


def bank_doc(bank: list[str | None]) -> list[str | None]:
    """A bank as a show file holds it: trailing empty slots left off, never
    shorter than F_KEYS."""
    out = list(bank)
    while len(out) > F_KEYS and out[-1] is None:
        out.pop()
    return out + [None] * (F_KEYS - len(out))


def _walk(folder: Path, pattern: str = "*.json") -> list[Path]:
    """Every file matching `pattern` under `folder`, every folder down,
    sorted — less hidden folders (``.cache``, a cloud client's own) and
    never through a link to a folder (plan 48)."""
    return [p for _here, found in _walk_dirs(folder, pattern) for p in found]


def _walk_dirs(folder: Path, pattern: str = "*.json"):
    """The one walker (`_walk`, `Library._tree`): each folder under
    `folder` (itself first), every folder down, with its files matching
    `pattern`, sorted — less hidden folders and never through a link to a
    folder."""
    for here, dirs, _files in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        h = Path(here)
        yield h, sorted(h.glob(pattern))


# how long a kept walk of the presets is trusted without a look at the
# disk (review of #334): a folder's mtime alone misses a file added in
# the same tick on a coarse filesystem (HFS+ 1 s, SMB 2 s) or a cloud mount
WALK_TTL = 1.0
_now = time.monotonic       # (a test moves the clock)


def _mtime(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _read_json(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise LibraryError(f"{path.name}: {e}") from e
    if not isinstance(doc, dict):
        raise LibraryError(f"{path.name}: not a JSON object")
    return doc


def _json_text(doc: dict) -> str:
    """A document as the library writes it — the one spelling, so a save
    can tell whether the file on disk already says the same."""
    return json.dumps(doc, indent=1) + "\n"


def show_text(doc: dict) -> str:
    """A show (or any library document) as `Project.write` spells it."""
    return _json_text(doc)


def show_without_eye(doc: dict) -> dict | None:
    """A show file's document without what plan 43 C2 made the presets' —
    the eye in its `session` (`EYE_IDS`) and the camera node's position in
    its `layout` (``render:camera``, or the old canvas id ``render:eye``) —
    as `Project.write` would write it; None when it holds neither (nothing
    to rewrite). Pure: tools/migrate_library.py's step over the shows."""
    session = doc.get("session")
    layout = doc.get(LAYOUT)
    eye = isinstance(session, dict) and any(k in session for k in EYE_IDS)
    cam = isinstance(layout, dict) and any(k in layout for k in CAMERA_NODES)
    if not (eye or cam):
        return None
    out = dict(doc)
    if eye:
        out["session"] = {k: v for k, v in session.items() if k not in EYE_IDS}
    if cam:
        rest = {k: v for k, v in layout.items() if k not in CAMERA_NODES}
        if rest:
            out[LAYOUT] = rest
        else:
            out.pop(LAYOUT)
    return out


def _look_ids(session: dict) -> list[str]:
    """The ids of a `/2` show's session that are a preset's since plan 44
    D3: every performance id (`params.part_of_id`: the hands' look, the
    clouds' — `ghost.mirror` stays the room's) but the eye, plan 43 C2's
    own road (`EYE_IDS`)."""
    return [k for k in session if isinstance(k, str) and k not in EYE_IDS
            and part_of_id(k) == "performance"]


def show_look(doc: Any) -> tuple[dict[str, Any], RigWires]:
    """What a `/2` show held of the look (plan 44 D3): the hands' and the
    clouds' values in its `session` (`_look_ids`) and its bus cuts (`rig`,
    `graph.RigWires`) — ({}, no cut) for neither, and for any `/3`. The one
    reader: `Project._take`, `kept_look`, `headless.show_seed` and the
    migration tool all ask it."""
    if not isinstance(doc, dict) or doc.get("schema") not in (PROJECT_V2, None):
        return {}, RigWires()
    session = doc.get("session")
    session = session if isinstance(session, dict) else {}
    return ({k: session[k] for k in _look_ids(session)}, RigWires.read(doc.get(RIG)))


def show_without_look(doc: dict) -> dict | None:
    """A `/2` show's document as its `/3` (plan 44 D3): the schema, without
    its bus cuts (`rig`) and without the look's ids in its `session`
    (`_look_ids`); None for a document that is not `/2` (nothing to
    rewrite). The eye is `show_without_eye`'s. Pure: the version step a
    load reads an old show through, and tools/migrate_library.py's."""
    if not isinstance(doc, dict) or doc.get("schema") != PROJECT_V2:
        return None
    out = dict(doc)
    out["schema"] = PROJECT_SCHEMA
    out.pop(RIG, None)
    session = doc.get("session")
    if isinstance(session, dict):
        drop = set(_look_ids(session))
        out["session"] = {k: v for k, v in session.items() if k not in drop}
    return out


def _write_json(path: Path, doc: dict) -> None:
    _write_text(path, _json_text(doc))


_tmp_ids = itertools.count(1)


def _write_text(path: Path, text: str) -> None:
    """Write `path` atomically (plan 25): the text goes to a dot-named temp
    file beside it — never ``*.json``, so neither the library's globs nor a
    cloud client take it for a preset — then `os.replace`s the file, so a
    synced folder never carries a half-written preset."""
    _refuse_missing(path)
    tmp = path.parent / f".{path.name}.{os.getpid()}-{next(_tmp_ids)}.tmp"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "x", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise LibraryError(f"{path.name}: {e}") from e


def to_trash(path: Path, root: Path, origin: str | None = None) -> Path | None:
    """Copy `path` — a preset file about to be overwritten or deleted — to
    ``<root>/trash/<origin>/<stem>.<YYYYMMDD-HHMMSS><suffix>``, `<origin>`
    the folder it came from relative to the library (``presets``,
    ``presets/party``, ``band``…; the file's own folder name when not
    given). The library passes its **machine** home as `root` (plan 48
    row 586, `Library._to_trash`): the trash is this Mac's, never in a
    synced library. A
    name taken in the same second gets ``-2``, ``-3``, …; the copy is
    created exclusively, so nothing in the trash is ever overwritten.
    Returns the path written, or None when the copy failed (said on
    stderr): the caller decides what that means — a save goes on and
    warns, a delete is refused."""
    folder = root / TRASH / (origin or path.parent.name)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    try:
        _refuse_missing(folder)
    except LibraryError as e:
        print(f"library: {path.name} not copied to the trash ({e})", file=sys.stderr)
        return None
    try:
        data = path.read_bytes()
        folder.mkdir(parents=True, exist_ok=True)
        for n in range(1, 1000):
            dst = folder / f"{path.stem}.{stamp}{'' if n == 1 else f'-{n}'}{path.suffix}"
            try:
                with open(dst, "xb") as f:
                    f.write(data)
            except FileExistsError:
                continue
            except OSError:
                dst.unlink(missing_ok=True)       # no half-written copy left behind
                raise
            return dst
        raise OSError(f"no free name under {folder}")
    except OSError as e:
        print(f"library: {path.name} not copied to the trash ({e})", file=sys.stderr)
        return None


@dataclass(frozen=True)
class Trashed:
    """A file in the trash, as its view lists it (plan 19 WP4)."""

    path: Path          # <machine>/trash/presets/party/trip-3.20261004-011203.json
    group: str          # its group's folder: "presets", "fx", "projects", …
    name: str           # the name inside the file, else its stem; folder-qualified
                        # for a preset from a folder ("party/TRIP", plan 48)
    when: str           # "Oct 4 01:12", from the stamp in the file name ("" if none)
    folder: str = ""    # the folder under the group it came from ("party"), plan 48
    old: bool = False   # in the library's own trash, from before plan 48 (row 586):
                        # listed and restorable, never emptied by the app


def _when(stamp: str) -> str:
    """``20261004-011203`` → ``Oct 4 01:12``."""
    try:
        t = time.strptime(stamp, "%Y%m%d-%H%M%S")
    except ValueError:
        return ""
    return f"{time.strftime('%b', t)} {t.tm_mday} {time.strftime('%H:%M', t)}"


def _order(path: Path) -> tuple[str, int]:
    """A trashed file's place in time: its stamp, then its ``-n``."""
    m = _TRASHED.fullmatch(path.name)
    return (m["stamp"], int(m["n"] or 1)) if m else ("", 0)


# ---- versioning: schema "<kind>/<n>"; each step lifts a doc one version ----

MIGRATIONS: dict[tuple[str, int], Any] = {
    # ("hyperspace.preset", 1): lambda doc: {...},   # 1 → 2, when there is one
    # plan 44 D3: a /2 show less what each preset holds now (read out first:
    # `Project._take`, `show_look`)
    ("hyperspace.project", 2): lambda doc: show_without_look(doc) or dict(doc),
}
# no project 1 → 2 step: a schema-1 show (an inline theme bank) is refused
# (`Project._take`) — no old-schema support since 2026-10-25
CURRENT = {"hyperspace.preset": 1, "hyperspace.project": 3}


def migrate_doc(doc: dict, kind: str) -> dict:
    """Lift a file to the current version of its kind, or refuse it."""
    schema = doc.get("schema")
    if not isinstance(schema, str) or "/" not in schema:
        raise LibraryError(f"no schema (expected {kind}/{CURRENT[kind]})")
    k, _, v = schema.rpartition("/")
    if k != kind or not v.isdigit():
        raise LibraryError(f"schema {schema!r} is not a {kind}")
    version = int(v)
    while version < CURRENT[kind]:
        step = MIGRATIONS.get((kind, version))
        if step is None:
            raise LibraryError(f"no migration from {schema}")
        doc = step(doc)
        version += 1
        doc["schema"] = f"{kind}/{version}"
    if version > CURRENT[kind]:
        raise LibraryError(f"{schema} is newer than this build ({kind}/{CURRENT[kind]})")
    return doc


@dataclass(frozen=True)
class DocKind:
    """A document format that is not the library's own but lives in its
    tree and goes through its doors (the presets, preset.py). `schema` is
    the kind half of the file's ``schema`` string, `versions` the ones
    `load` can take; `load(doc, path)` applies a file (returning the ids
    it named that nothing has), `document(name)` is what a save writes,
    `signature()` is the group's state as `is_dirty` compares it."""

    schema: str
    versions: tuple[int, ...]
    load: Callable[[dict, Path | None], list[str]]
    document: Callable[[str], dict]
    signature: Callable[[], Any]
    text: Callable[[dict], str] | None = None   # the file's text, when json.dumps is not it


def _patch_spawned(*_args) -> Any:
    raise LibraryError(PATCH_SPAWNED)


def _patch_kind() -> DocKind:
    """The patches' document kind (plan 40 T1): its schema and versions, so
    `read` checks a file as it does a preset's, and the doors that refuse —
    a patch is spawned (`patches.spawn`), never loaded, and what a save
    writes is `save_patch`'s document, never the live state's."""
    kind, _, v = PATCH_SCHEMA.rpartition("/")
    return DocKind(kind, (int(v),), _patch_spawned, _patch_spawned, _patch_spawned)


def scene_doc(path: Path) -> dict:
    """A band scene's file (hyperspace/scenes/band/, control.py), lifted to
    the current module-preset schema — the analyzer's scenes are code data,
    read without a Library."""
    if not path.is_file():
        raise LibraryError(f"no scene file {path.name}")
    return migrate_doc(_read_json(path), "hyperspace.preset")


def _module_values(group: str, doc: dict) -> dict[str, Any]:
    """A module preset's values as they land: a camera module from before
    plan 26 A2 (no `units` marker) stored its pan in logical px, read in
    world units here (`params.pan_world`), as a whole preset's is in
    `preset.load_doc` — every road a module's values take (a strip load,
    a project's module list, a file re-applied, the group's default under
    `defaults`/`resolved`)."""
    if group == "camera":
        doc, _ = pan_world(doc)
    elif group == "fx":
        # plan 30 N8: a palette saved as centre/width is read as its slice
        doc, _ = palette_slice(doc)
    return dict(doc.get("values") or {})


# ---------------------------------------------------------------- project

class Project:
    """The open show — the session (plan 13 §2.2): its file (None until
    saved), the session values, the session groups' module labels, and the
    preset bank, the desk's pads.

    ``session`` / ``modules`` / ``bank`` / ``startup`` are what the *file*
    holds; ``save()`` refreshes ``session`` and ``modules`` from the live
    state, ``write()`` puts the document back on disk as it is — what a
    pad save uses, so the desk persists the bank without turning the
    whole project into a snapshot of the moment.

    ``session`` is the session part of the registry (params.PARTS: tempo,
    hands, the analyzer, output), landed on a project load and never
    touched by a preset. The **bank** is ``SLOTS`` preset names (or None):
    a slot is a pointer to a preset file (preset.py), loaded through
    ``Library.presets`` — the APC40's clip rows 1, 4 and 5 load one each,
    F<k+1> the first ``F_KEYS``, ⇧F<k+1> saves the live state as that
    preset (``slot_key`` names a slot). A show file's shorter bank is
    padded in memory and the file is left as it is (``_take``,
    ``bank_doc``). ``startup`` is the preset a launch and Home bring up
    (D11); since 2026-10-28 nothing on the panel sets it — the file keeps
    what it says.
    """

    def __init__(self, lib: Library):
        self.lib = lib
        self.name = UNTITLED
        self.note = ""
        self.path: Path | None = None
        self.session: dict[str, Any] = {}     # the session part
        self.modules: dict[str, Any] = {}     # session groups' module labels
        self.bank: list[str | None] = [None] * SLOTS
        self.startup: str | None = None
        self.active = -1          # the slot last loaded, -1 until one is
        self.bank_error = ""
        self._saved: tuple = ([None] * SLOTS, None)   # bank and startup as on disk
        # plan 28 N2: the GRAPH page's positions of the rig's nodes, and
        # those as on disk (`is_dirty`)
        self.layout: dict[str, list[float]] = {}
        self._saved_layout: dict[str, list[float]] = {}
        # plan 44 D3: what an old show (`/2`) held of the look — the hands'
        # and clouds' values in its session, its bus cuts — read out by
        # `_take` and handed to every preset before `/10` a load reads while
        # this show is open (`graphmigrate.ten`); never written back
        self.old_look: dict[str, Any] = {}
        self.old_cuts = RigWires()
        # plan 43 C2: what an old show (before the eye was the preset's) kept
        # of the camera — the eye in its `session`, the camera node's GRAPH
        # position in its `layout` — read out of the file by `_take` and
        # handed to every preset before `/9` a load reads while this show is
        # open (`graphmigrate.nine`), so the library draws as before; never
        # written back (`to_doc`; `write` keeps the old file, EYE_BACKUP)
        self.old_eye: dict[str, Any] = {}
        self.camera_at: list[float] | None = None

    # ---- documents ----

    def _take(self, doc: dict, path: Path | None, where: str = "project") -> None:
        if doc.get("schema") == PROJECT_V1:
            raise LibraryError(f"{where} is a schema-1 show, which this build does not read "
                               "(no old-schema support, 2026-10-25)")
        # plan 44 D3: what a /2 show held of the look, before the version
        # step drops it (`show_without_look`) — else what its first write on
        # this build kept beside it (`kept_look`)
        self.old_look, self.old_cuts = show_look(doc)
        if path is not None and not self.old_look and not self.old_cuts.cut:
            self.old_look, self.old_cuts = kept_look(path)
        doc = migrate_doc(doc, "hyperspace.project")
        self.name = str(doc.get("name") or (path.name[: -len(PROJECT_SUFFIX)] if path
                                            else UNTITLED))
        self.note = str(doc.get("note") or "")
        self.path = path
        # the file's own name, which a launch finds the show by (`stem`)
        self._stem = where[: -len(PROJECT_SUFFIX)] if where.endswith(PROJECT_SUFFIX) else None
        from .routing import renamed_session  # the stick spring's old ids, as today's
        self.session = renamed_session(dict(doc.get("session") or {}))
        # plan 43 C2: the eye is the preset's — an old show's is read out of
        # its session (as the spring's old ids are read as today's), held for
        # the presets before `/9` (`old_eye`), and never landed or written
        # as the show's
        self.old_eye = {pid: self.session.pop(pid) for pid in EYE_IDS if pid in self.session}
        # how many shows this project object has taken: a hands node of a
        # preset's graph is seeded from a show's session once per show
        # opened (plan 26 A4, preset.GraphSection)
        self.opened = getattr(self, "opened", 0) + 1
        self.modules = dict(doc.get("modules") or {})
        bank = [str(s) if isinstance(s, str) and s else None
                for s in list(doc.get("bank") or [])[:SLOTS]]
        self.bank = bank + [None] * (SLOTS - len(bank))
        self.startup = str(doc["startup"]) if doc.get("startup") else None
        self.active = -1
        self._saved = (list(self.bank), self.startup)
        self.layout, _ = read_layout(doc.get(LAYOUT))
        # (plan 43 C2: and the camera node's position, the look's now — the
        # presets before `/9` take it, `old_eye`'s road)
        # (under today's id or the old canvas's, `CAMERA_NODES` — `read_layout`
        # renames the old one, but neither may stay the show's)
        found = [self.layout.pop(k) for k in CAMERA_NODES if k in self.layout]
        self.camera_at = list(found[0]) if found else None
        # (review 2.2: a show whose first write on this build — the bank's
        # autosave, say — already moved its eye into `<file>.bak-v2-eye`
        # still hands that eye to the presets before `/9`, until the tool
        # writes it into them)
        if path is not None and not self.old_eye:
            self.old_eye, kept_at = kept_eye(path)
            if self.camera_at is None and kept_at is not None:
                self.camera_at = kept_at
        self._saved_layout = copy.deepcopy(self.layout)

    @property
    def stem(self) -> str:
        """The show's file name less ``.hyp.json`` — what `last_show` holds
        and `path_for` finds again, whatever `name` the file carries inside
        (review of PR #75: a copied or hand-edited file's name can differ)."""
        if self.path is not None:
            return self.path.name[: -len(PROJECT_SUFFIX)]
        return getattr(self, "_stem", None) or slug(self.name)

    def to_doc(self) -> dict:
        doc: dict[str, Any] = {"schema": PROJECT_SCHEMA, "name": self.name}
        if self.note:
            doc["note"] = self.note
        doc.update(startup=self.startup, bank=bank_doc(self.bank), session=self.session,
                   modules=self.modules)
        layout = getattr(self, "layout", None)
        if layout:                       # plan 28 N2; a show with none writes none
            doc[LAYOUT] = {k: list(layout[k]) for k in sorted(layout)}
        return doc

    def mark(self) -> tuple:
        """The show as held, opaque, for an undo to hand back (`remark`):
        name, note, path, stem, session, modules, bank, startup and the
        bank and startup as on disk — copies, so a later edit of the live
        show never reaches a mark; then the GRAPH page's positions of the
        rig's nodes, live and as on disk; then what an old show kept of the
        camera (plan 43 C2) and of the look (plan 44 D3; the bus cuts are
        the preset's: `Marks`)."""
        return (self.name, self.note, self.path, getattr(self, "_stem", None),
                copy.deepcopy(self.session), copy.deepcopy(self.modules), list(self.bank),
                self.startup, (list(self._saved[0]), self._saved[1]),
                # plan 28 N2: the GRAPH page's positions of the rig's nodes
                copy.deepcopy(getattr(self, "layout", {})),
                copy.deepcopy(getattr(self, "_saved_layout", {})),
                # plan 43 C2: what an old show kept of the camera, for its presets
                dict(getattr(self, "old_eye", {})), getattr(self, "camera_at", None),
                # plan 44 D3: and of the look
                dict(getattr(self, "old_look", {})), getattr(self, "old_cuts", RigWires()))

    # the mark's fixed head, and where its later parts start
    MARK_LAYOUT = 9          # the GRAPH page's layout, and as on disk (plan 28 N2)
    MARK_EYE = 11            # an old show's eye and camera position (plan 43 C2)
    MARK_LOOK = 13           # an old show's look and bus cuts (plan 44 D3)

    def remark(self, mark: tuple) -> None:
        """Put back what `mark()` returned: the show's own fields, nothing
        else — no file is read or written, no value lands (undo.py does
        that), and `active` is the caller's to recompute (`Marks.put`)."""
        (self.name, self.note, self.path, self._stem,
         session, modules, bank, self.startup, saved) = mark[:self.MARK_LAYOUT]
        if len(mark) > self.MARK_LAYOUT:   # plan 28 N2: the show's layout, and as on disk
            self.layout = copy.deepcopy(mark[self.MARK_LAYOUT])
            self._saved_layout = copy.deepcopy(mark[self.MARK_LAYOUT + 1])
        if len(mark) > self.MARK_EYE:      # plan 43 C2: an old show's eye, for its presets
            self.old_eye, self.camera_at = dict(mark[self.MARK_EYE]), mark[self.MARK_EYE + 1]
        if len(mark) > self.MARK_LOOK:     # plan 44 D3: and its look, for its presets
            self.old_look, self.old_cuts = dict(mark[self.MARK_LOOK]), mark[self.MARK_LOOK + 1]
        self.session, self.modules = copy.deepcopy(session), copy.deepcopy(modules)
        self.bank = list(bank)
        self._saved = (list(saved[0]), saved[1])

    @staticmethod
    def same_show(a: tuple, b: tuple) -> bool:
        """Do two marks name one show — the same name, file and stem?
        (The bank and startup may differ: they are written to the show's
        file the moment they change.)"""
        return (a[0], a[2], a[3]) == (b[0], b[2], b[3])

    def _apply(self) -> list[str]:
        """Push the document's session into the registry; returns unknown
        ids. A module's `layout` lands first (a project saved on eight
        bands comes back with eight, audit L8), then the session values
        — the live state as saved, edits included — and each module is
        recorded as the group's current preset, the reference its dirty
        dot compares against, the way a strip load records it. Only a
        session group's module counts: a performance group's label is the
        preset's (preset.py)."""
        lib = self.lib
        # a document kind is never the project's (the loaded preset, the
        # only kind since plan 13 WP5): what it has landed survives a project
        # load, and so do the performance groups' references — the loaded
        # preset's, which their dirty dots compare against (plan 14 WP4)
        kept = {g: lib.landed(g) for g in (*lib._kinds, *PERFORMANCE_GROUPS)}
        lib._current.clear()
        lib._loaded.clear()
        lib._adopted.clear()
        for group, mark in kept.items():
            if mark[0] is not None or mark[1] is not None:
                lib.reland(group, mark)
        docs: list[tuple[str, str, dict | None]] = []
        for group, ref in self.modules.items():
            if group in lib._kinds or group not in SESSION_GROUPS:
                continue                              # a preset's, or a document kind's
            if isinstance(ref, dict):                 # inline copy of a preset
                name, doc = str(ref.get("name") or ""), dict(ref)
            else:                                     # by name in the library
                name = str(ref)
                try:
                    doc = lib.read(group, name)
                except LibraryError:                  # gone from the library: not dirty
                    doc = None
            docs.append((group, name, doc))
            hook = lib._layout_hooks.get(group)
            if doc is not None and hook is not None and doc.get("layout") is not None:
                hook(doc["layout"])                   # its params exist before the values land
                lib._fresh_of(group)                  # …and their build values are "fresh"
        missing = lib.restore(self.session) if self.session else []
        # an extra hands node's settings (`ghost.2.*`, plan 26 A4) wait for
        # the preset whose graph declares the node (`GraphSection` seeds it
        # from this session): held back, not unknown
        missing = [pid for pid in missing if not is_instance_id(pid)]
        # ids the file lacks (a param added since) take the state this load
        # left, so an untouched project is not dirty the moment it opens
        for pid, v in (lib.reg.snapshot(part="session") if lib.reg is not None else {}).items():
            self.session.setdefault(pid, v)
        for group, name, doc in docs:
            vals = (lib.reg.snapshot(group) if doc is None
                    else lib.resolved(group, _module_values(group, doc)))
            lib._landed(group, name, vals)
            hook = lib._load_hooks.get(group)
            if hook is not None:
                hook(name)
        # a session group the show names no module preset for: clean as the
        # show left it — the rail's dot compares against the show, not fresh
        # defaults (plan 14 WP4)
        if lib.reg is not None:
            named = {g for g, _n, _d in docs}
            for group in SESSION_GROUPS:
                if group not in named and group not in lib._kinds:
                    lib._landed(group, None, lib.reg.snapshot(group))
        # the bank lights the slot naming the preset still loaded, if any
        self.follow()
        return missing

    # ---- the bank: SLOTS pointers to preset files ----

    def follow(self) -> None:
        """`active` follows the loaded preset — the one place (plan 19
        WP1): kept where it is when that slot still names it, else the
        first slot that names it, else −1; −1 when nothing is loaded."""
        lib, cur = self.lib, self.lib.current(PRESETS)
        if cur is None:                               # nothing loaded: no slot is lit
            self.active = -1
            return
        # a slot names it when it is the same string or reads (as a pad
        # loads it, loosely) the same file: `Ac/Dc`, `Party/TRIP` (plan 48
        # review); one look at the library for every slot
        snap = lib._lookup(PRESETS) if hasattr(lib, "_lookup") else None
        target = None if snap is None else lib._resolve(PRESETS, cur, snap, loose=True)

        def names(n: str | None) -> bool:
            return n is not None and (n == cur or (
                target is not None and lib._resolve(PRESETS, n, snap, loose=True) == target))

        if not (0 <= self.active < len(self.bank) and names(self.bank[self.active])):
            self.active = next((k for k, n in enumerate(self.bank) if names(n)), -1)

    def _loader(self):
        return getattr(self.lib, "presets", None)

    def load_slot(self, k: int) -> None:
        """Slot k (F<k+1> for the first eight): the preset it names,
        through the one loader. An empty slot, or a name with no file,
        loads nothing and says so. `active` is the slot that was asked
        for, so a preset on two slots lights the one pressed."""
        if not 0 <= k < len(self.bank):
            return
        lib, name, key = self.lib, self.bank[k], slot_key(k)
        presets = self._loader()
        if name is None:
            lib.say(warning=f"{key}: an empty slot — hold its pad" + (
                f" (or ⇧{key})" if k < F_KEYS else "") + " to save the live state into it")
            return
        if presets is None or lib.path_of(PRESETS, name, loose=True) is None:
            lib.say(warning=f"{key}: no preset {name!r}")
            return
        try:
            presets.load(name)
        except LibraryError as e:                     # a bad file: said, never fatal
            lib.error = f"library: {e}"
            return
        self.active = k

    def save_slot(self, k: int) -> None:
        """⇧F<k+1>: the live state as the preset slot k names — a new one,
        ``PRESET <k+1>``, for an empty slot — written over its file (the
        old text kept in the trash); the bank and the project file with
        it. A show file that cannot take
        the slot (`write`) leaves the bank as the file has it: the preset
        is saved and in the list, and the footer says why."""
        presets = self._loader()
        if not 0 <= k < len(self.bank) or self.lib.reg is None:
            return
        if presets is None:
            self.bank_error = "presets: no preset loader"
            return
        was = self.bank[k]
        name = was or self._fresh_name(k)
        try:
            presets.save_as(name)
        except LibraryError as e:                     # a full disk must not stop the show
            self.bank_error = f"presets: {e}"
            return
        self.bank[k] = name
        self.active = k
        try:
            self.write()
        except (LibraryError, OSError) as e:
            self.bank[k] = was
            self.follow()                             # the light goes where the preset is
            self._refused(f"saved {name} — {slot_key(k)} not changed", e)
            return
        self.bank_error = ""

    def _fresh_name(self, k: int) -> str:
        """``PRESET <k+1>``, made unique against every preset there is."""
        taken = ({slug(n) for n in self.lib.list(PRESETS)}
                 | {slug(n) for n in self.bank if n})
        base = name = f"PRESET {k + 1}"
        n = 1
        while slug(name) in taken:
            n += 1
            name = f"{base} ({n})"
        return name

    def next_empty(self) -> int | None:
        """The first empty slot, None on a full bank. The bank's own list
        is the one place its size is read (plan 15 §1 row 13)."""
        return next((k for k in range(len(self.bank)) if self.bank[k] is None), None)

    def save_into(self, k: int) -> bool:
        """The desk's two-handed save (plan 24 C1, decision 18: SAVE held, a
        bank pad tapped — `Param.save_into`, midi.py `_save_tap`): the live
        state as a **new** preset in slot k — `save_new`'s preset, its name
        (`next_name`, from the loaded one: TRIP → TRIP 2) and its show
        write, in slot k rather than the next empty one. **A filled slot
        takes the new preset too**: the slot points at it, and the preset
        it named keeps its file, untouched, and stays in the list, unpadded
        — exactly as "free this pad (keeps the preset)" leaves it. Nothing
        is overwritten and nothing goes to the trash (owner, 2026-10-09 and
        2026-10-14). True when slot k now names the new preset; False for a
        slot the bank does not have, a save that failed, or a show file
        that could not take the slot (the preset is then saved and in the
        list, slot k is as it was, and `bank_error` and the footer say why)."""
        if not 0 <= k < len(self.bank):
            return False
        return self._save_new(k)

    def save_empty(self, k: int) -> bool:
        """#158's hold (2026-10-09): an **empty** bank pad held midi.HOLD_S
        saves into its slot (`save_into`); a filled pad held only loads —
        nothing happens here and False is returned, so a long press that
        loaded a preset blinks nothing (`Param.held` on `preset.select`).
        Saving onto a filled slot is the two-handed save's alone."""
        if not 0 <= k < len(self.bank) or self.bank[k] is not None:
            return False
        return self.save_into(k)

    def save_new(self) -> bool:
        """The live state as a **new** preset, named from the loaded one
        (`next_name`), into the next empty slot (`preset.save_new`, plan 15
        WP4: learnable onto any button; the desk itself saves by holding an
        empty pad, `save_into`).
        It never overwrites: the name's slug is free among the preset
        folder's file stems, every listed name (`_taken`) and the bank's
        names. The new preset becomes the loaded one with a
        clean dot, as the panel's "as…" does, so a second save counts on.
        A full bank saves to the list and says so. The show is written at
        once; no undo step — nothing live changes. True when a preset was
        saved; False when none was (the reason is in `bank_error`), which
        the desk reads as "nothing to confirm" (midi.py blinks no light)."""
        return self._save_new(None)

    def _save_new(self, at: int | None) -> bool:
        """`save_new` into slot `at`, or the next empty one when None."""
        lib, presets = self.lib, self._loader()
        if lib.reg is None:
            return False
        if presets is None:
            self.bank_error = "presets: no preset loader"
            return False
        # stems as slugs: on a filesystem that folds case, `Trip-2.json`
        # is the file a save of "TRIP 2" would write over. Plan 48 row 587:
        # the new preset lands beside the loaded one — in its folder, the
        # library's root for a top-level one or none loaded
        taken = lib._taken(PRESETS) | {lib._fold(PRESETS, n) for n in self.bank if n}
        folder, base = lib.folder_of(PRESETS, lib.current(PRESETS))
        leaf = next_name(base, taken, key=lambda n: lib._fold(
            PRESETS, f"{folder}/{n}" if folder else n))
        name = f"{folder}/{leaf}" if folder else leaf
        try:
            presets.save_as(name)
        except (LibraryError, OSError) as e:          # a full disk must not stop the show
            self.bank_error = f"presets: {e}"
            return False
        self.bank_error = ""
        k = self.next_empty() if at is None else at
        if k is None:
            lib.say(warning=f"saved {name} — {BANK_FULL}")
            return True
        was = self.bank[k]          # a filled slot (`save_into`): its preset stays listed
        self.bank[k] = name
        self.active = k
        try:
            self.write()
        except (LibraryError, OSError) as e:
            # the preset is saved and loaded, but the show could not take
            # it: the bank stays as the show's file has it, and it is said
            self.bank[k] = was
            self.active = -1
            self.bank_error = f"presets: {e}"
            lib.say(warning=f"saved {name} — the show could not be written: it is in "
                            f"the preset list ({e})")
            # `save_new` saved what it was asked to (the list has it); a
            # save into slot `at` did not land there — False, so the desk
            # blinks nothing over a slot that still names the old preset
            return at is None
        self._room()
        kept = f" ({was} is still in the preset list)" if was is not None else ""
        lib.say(f"saved {name} → {slot_key(k)}{kept}")
        return True

    def put_slot(self, k: int, name: str) -> None:
        """Point slot k at a preset: the file must exist, else a warning and
        nothing changes. The show is written at once; no preset file is
        written or deleted; no undo step."""
        if not 0 <= k < len(self.bank):
            return
        if self.lib.path_of(PRESETS, name, loose=True) is None:
            self.lib.say(warning=f"{slot_key(k)}: no preset {name!r}")
            return
        self._set_slot(k, name, f"{slot_key(k)}: {name}")

    def clear_slot(self, k: int) -> None:
        """Empty slot k: the show is written at once; the preset's file
        stays in the list."""
        if 0 <= k < len(self.bank) and self.bank[k] is not None:
            self._set_slot(k, None, f"{slot_key(k)}: cleared — {self.bank[k]} is still in "
                                    "the preset list")

    def _set_slot(self, k: int, name: str | None, said: str) -> None:
        """One slot's pointer, written into the show now; `active` follows
        the loaded preset to a slot that names it, or to none (`follow`).
        A show file that cannot be written leaves the slot as it was, and
        the footer says why."""
        lib, was = self.lib, self.bank[k]
        self.bank[k] = name
        try:
            self.write()
        except (LibraryError, OSError) as e:          # said, and the bank as on disk
            self.bank[k] = was
            self._refused(f"{slot_key(k)}: not changed", e)
            return
        self.bank_error = ""
        self.follow()
        self._room()
        lib.say(said)

    def _refused(self, what: str, e: Exception) -> None:
        """A bank change the show's file could not take: the reason under
        the bank (`bank_error`) and on the footer (`Library.say`)."""
        self.bank_error = f"presets: {e}"
        self.lib.say(warning=f"{what} — {e}")

    def _room(self) -> None:
        """The bank changed: an earlier "the bank is full" is no longer news."""
        if self.lib.warning.endswith(BANK_FULL):
            self.lib.warning = ""

    def cycle(self, step: int = 1) -> None:
        """Flip to the next filled slot — the APC's QUANT (`preset.next` /
        `preset.prev`). The pad's d-pad ← / → walk the list instead (`walk`)."""
        filled = [k for k, s in enumerate(self.bank) if s is not None]
        if not filled:
            return
        if self.active in filled:
            k = filled[(filled.index(self.active) + step) % len(filled)]
        else:
            k = filled[0] if step > 0 else filled[-1]
        self.load_slot(k)

    def walk(self, step: int = 1) -> str | None:
        """Load the next (step 1) or previous (−1) preset of the preset
        list — the list the PRESETS page shows and its ◀ ▶ step
        (`Library.list`: by name, case folded), wrapping at both ends;
        from a preset not in it (none loaded) the first or the last
        (`Library.next` / `prev`). The list is read from disk each step, so a preset saved
        a moment ago (`save_new`, the strip's "as…") is in it. The pad's
        d-pad → / ← held (`preset.list.next` / `prev`, 2026-10-29) — not the bank,
        which the desk walks (`cycle`). A load is the drop-down's pick:
        one undo step; a bad file shows on the library's error line and
        the show runs on. Returns the name loaded, or None."""
        lib = self.lib
        if self._loader() is None:
            return None
        try:
            return lib.next(PRESETS) if step > 0 else lib.prev(PRESETS)
        except (LibraryError, OSError) as e:
            lib.error = f"library: {e}"
            return None

    def load_startup(self) -> None:
        """The project's startup preset (D11), if it names one: a launch
        and a project load bring it up. A name with no file says so and
        the app keeps running on what it has."""
        lib, presets, name = self.lib, self._loader(), self.startup
        if presets is None or not name:
            return
        if lib.path_of(PRESETS, name, loose=True) is None:
            lib.say(warning=f"startup: no preset {name!r}")
            return
        try:
            presets.load(name)
        except LibraryError as e:
            lib.error = f"library: {e}"

    def home(self) -> None:
        """Home (plan 15 WP2, decision 27): load the show's startup preset
        — the `preset.home` trigger, on the Home key and the desk's
        OVERDUB. It is a load like any other (D2), and one undo step under
        its own label: the push inside `Presets.load_doc` is the same
        frame's and is ignored (undo.py). A show that names no startup
        preset says so and loads nothing; so does a name with no file, in
        `load_startup`'s words (neither opens a step)."""
        lib, name = self.lib, self.startup
        if not name:
            lib.say(warning=HOME_UNSET)
            return
        if lib.warning == HOME_UNSET:                 # it names one now
            lib.warning = ""
        if self._loader() is not None and lib.path_of(PRESETS, name, loose=True) is not None:
            undo.push(f"home → {name}", load=True)
        self.load_startup()

    # ---- API ----

    def list(self) -> list[str]:
        """Every show by file stem."""
        names = {p.name[: -len(PROJECT_SUFFIX)]
                 for p in (self.lib.home / PROJECTS).glob(f"*{PROJECT_SUFFIX}")}
        return sorted(names)

    def path_for(self, name: str) -> Path:
        return self.lib.home / PROJECTS / f"{slug(name)}{PROJECT_SUFFIX}"

    def load(self, name: str | Path, *, startup: bool = True) -> list[str]:
        """Open a show by name or path; returns unknown ids. Its startup
        preset comes up with it unless `startup` is off (the file watch
        re-reading an edited project). A schema-1 file is refused
        (`_take`)."""
        lib = self.lib
        if isinstance(name, Path) or str(name).endswith(PROJECT_SUFFIX):
            path = Path(name)
        else:
            path = self.path_for(name)
        doc = _read_json(path)
        # the file is read, nothing replaced yet: one undo step for the show
        # and the startup preset it brings up (undo.py)
        undo.push(f"show {doc.get('name') or path.name[: -len(PROJECT_SUFFIX)]}", load=True)
        self._take(doc, path, path.name)
        missing = self._apply()
        lib.report(missing, path.name)
        lib.say(f"show: {self.name}")
        lib.remember(self.stem)
        if startup:
            self.load_startup()
        return missing

    def new(self, name: str = UNTITLED) -> None:
        """A fresh show: default state, an empty bank, no file yet (not
        remembered until it is saved)."""
        lib = self.lib
        undo.push("new show", load=True)              # one undo step (undo.py, plan 15)
        self._take({"schema": PROJECT_SCHEMA, "name": name}, None)
        self.name = name
        lib._fresh_layouts()                          # the layout the app started with…
        lib.restore(lib._fresh_all())                 # …and every group's fresh values
        self._apply()
        lib.say(f"show: new {name}")
        self.load_startup()

    def save(self, name: str | None = None) -> Path:
        """The session into the project file (as `name` if given), with the
        bank and startup as held."""
        lib = self.lib
        held = (self.name, self.path, self.session, self.modules)
        if name:
            self.name = name
            self.path = self.path_for(name)
        elif self.path is None:
            self.path = self.path_for(self.name)
        self.session = {**self._held_back(), **lib.reg.snapshot(part="session")}
        self.modules = {}
        for group, cur in lib._current.items():
            if cur is None or group in lib._kinds or group not in SESSION_GROUPS:
                continue                              # a preset's label, or a kind's
            if lib.path_of(group, cur) is not None:
                self.modules[group] = cur
            else:                                     # not in any library: keep a copy
                doc = lib.document(group, cur)
                self.modules[group] = {k: v for k, v in doc.items()
                                       if k not in ("schema", "group")}
        try:
            self.write()
        except (LibraryError, OSError):
            # nothing was written (a backup that could not be made, a full
            # disk): the show is still the one it was, under its own name
            self.name, self.path, self.session, self.modules = held
            raise
        lib.say(f"show: saved {self.name}")
        lib.remember(self.stem)
        return self.path

    def write(self) -> Path:
        """Write the document as held — the bank's autosave.

        The first write that makes a show file's bank longer than F_KEYS
        (plan 19 WP1) — the file on disk parses and holds at most eight
        slots, the document about to be written holds more — keeps the
        eight-slot file first as ``<file>.bak-v2-bank8`` (never over a
        file already there). **No backup, no write**: it raises
        LibraryError and the file is as it was; the callers put the slot
        back. The next write finds a long bank on disk and makes no
        second copy. A build from before plan 19 reads a long bank by
        cutting it to eight, and drops the far slots' names from the file
        the next time it writes that show; the backup is the file from
        before any far slot existed.

        Likewise the first write over a file that holds the stick spring as
        stored before 2026-10-29 (`desk.pad.hz` / `.damp`, which this
        write drops: they were read as today's knobs) keeps it first as
        ``<file>.bak-v2-spring``; and (plan 43 C2) the first write over a
        file that holds the eye in its `session` (`eye.*`) or the camera's
        GRAPH position in its `layout` (both the presets' since `/9`: this
        write drops them) keeps it first as ``<file>.bak-v2-eye``.
        And (plan 44 D3) the first write of a `/2` show — written `/3`,
        without its bus cuts and the hands' and clouds' looks, each preset's
        now — keeps it first as ``<file>.bak-v2-look``. No backup, no write."""
        self.lib.writable()
        path = self.path_for(self.name) if self.path is None else self.path
        try:
            old = json.loads(path.read_text()) if path.is_file() else None
        except (OSError, ValueError):
            old = None
        doc = self.to_doc()
        if isinstance(old, dict):
            from .routing import PAD_FEEL_OLD, backup
            if (len(doc["bank"]) > F_KEYS and _bank_len(old) <= F_KEYS
                    and not _kept(path) and backup(path, BANK8_BACKUP) is None):
                raise LibraryError(f"{path.name}: not written — no backup of the "
                                   "eight-slot file could be made")
            session = old.get("session")
            if (isinstance(session, dict) and any(k in session for k in PAD_FEEL_OLD)
                    and not _kept(path, SPRING_BACKUP)
                    and backup(path, SPRING_BACKUP) is None):
                raise LibraryError(f"{path.name}: not written — no backup of the show "
                                   "with its stick spring as it was stored could be made")
            # (the eye in its session or the camera's position in its layout:
            # whatever of either this write drops — `show_without_eye`)
            if (show_without_eye(old) is not None and not _kept(path, EYE_BACKUP)
                    and backup(path, EYE_BACKUP) is None):
                raise LibraryError(f"{path.name}: not written — no backup of the show "
                                   "with its eye could be made")
            if (old.get("schema") == PROJECT_V2 and not _kept(path, LOOK_BACKUP)
                    and backup(path, LOOK_BACKUP) is None):
                raise LibraryError(f"{path.name}: not written — no backup of the /2 show "
                                   "could be made")
        self.path = path
        _write_json(self.path, doc)
        self.lib._sync(self.path)
        self._saved = (list(self.bank), self.startup)
        self._saved_layout = copy.deepcopy(getattr(self, "layout", {}))
        return self.path

    def is_dirty(self) -> bool:
        """Does the live state differ from the file — the session values,
        the bank or the startup preset? Never saved counts as dirty."""
        reg = self.lib.reg
        if reg is None:
            return False
        return (self.path is None
                or not undo.alike(self.session, {**self._held_back(),
                                                 **reg.snapshot(part="session")})
                or (self.bank, self.startup) != self._saved
                or getattr(self, "layout", {}) != getattr(self, "_saved_layout", {}))

    def _held_back(self) -> dict:
        """The session's settings of node instances the registry lacks now
        (`ghost.2.*` while no preset's graph holds the second hands node,
        plan 26 A4): kept by a save and never counted as an edit."""
        reg = self.lib.reg
        return {pid: v for pid, v in (self.session or {}).items()
                if is_instance_id(pid) and (reg is None or pid not in reg)}


def show_eye(doc: Any) -> tuple[dict[str, Any], list[float] | None]:
    """What a show document kept of the camera (plan 43 C2): the eye in its
    `session` (`EYE_IDS`) and the camera node's GRAPH position in its
    `layout` (either id, `CAMERA_NODES`) — ({}, None) for neither. The one
    reader of a show's camera: `Project._take`, `kept_eye`,
    `headless.show_seed` and the migration tool all ask it."""
    if not isinstance(doc, dict):
        return {}, None
    session = doc.get("session")
    session = session if isinstance(session, dict) else {}
    layout, _ = read_layout(doc.get(LAYOUT))
    at = next((layout[k] for k in CAMERA_NODES if k in layout), None)
    return ({pid: session[pid] for pid in EYE_IDS if pid in session},
            list(at) if at is not None else None)


# (path, the folder's state) → what `kept_eye` found there: a show opened
# again finds it with one stat, not a glob and a parse (review 3.5)
_KEPT_EYES: dict[tuple[str, int], tuple[dict[str, Any], list[float] | None]] = {}


def kept_eye(path: Path) -> tuple[dict[str, Any], list[float] | None]:
    """The eye (and the camera's GRAPH position) a show's ``.bak-v2-eye``
    copy kept — the oldest copy that holds an eye (`show_eye`) — or ({},
    None): what an old show's `session` held before its first write on
    this build dropped it (plan 43 C2, `Project.write`). Remembered per
    show file and its folder's state (a new backup changes the folder), so
    a show from this build — which has no such copy — costs a stat."""
    try:
        key = (str(path), path.parent.stat().st_mtime_ns)
    except OSError:
        return {}, None
    hit = _KEPT_EYES.get(key)
    if hit is not None:
        return dict(hit[0]), hit[1]
    found: tuple[dict[str, Any], list[float] | None] = ({}, None)
    # (plan 44 D3: a /2 show the tool rewrote as /3 kept itself as `.bak-v2-look`)
    baks = [*sorted(path.parent.glob(f"{path.name}.bak-v{EYE_BACKUP}*")),
            *sorted(path.parent.glob(f"{path.name}.bak-v{LOOK_BACKUP}*"))]
    for bak in baks:
        try:
            eye, at = show_eye(json.loads(bak.read_text()))
        except (OSError, ValueError):
            continue
        if eye:
            found = (eye, at)
            break
    _KEPT_EYES[key] = found
    return dict(found[0]), found[1]


_KEPT_LOOKS: dict[tuple[str, int], tuple[dict[str, Any], RigWires]] = {}


def kept_look(path: Path) -> tuple[dict[str, Any], RigWires]:
    """What a show's ``.bak-v2-look`` copy kept of the look (`show_look`)
    — the oldest copy — or ({}, no cut): a `/2` show whose first write on
    this build made it `/3` still hands its old look to the presets before
    `/10` (plan 44 D3), until the tool writes it into them. Remembered per
    show file and its folder's state, as `kept_eye`."""
    try:
        key = (str(path), path.parent.stat().st_mtime_ns)
    except OSError:
        return {}, RigWires()
    hit = _KEPT_LOOKS.get(key)
    if hit is not None:
        return dict(hit[0]), hit[1]
    found: tuple[dict[str, Any], RigWires] = ({}, RigWires())
    for bak in sorted(path.parent.glob(f"{path.name}.bak-v{LOOK_BACKUP}*")):
        try:
            found = show_look(json.loads(bak.read_text()))
        except (OSError, ValueError):
            continue
        break
    _KEPT_LOOKS[key] = found
    return dict(found[0]), found[1]


def _kept(path: Path, tag: str = BANK8_BACKUP) -> bool:
    """Is the file at `path` already kept, byte for byte, in one of its
    backups under `tag` (the eight-slot bank's, the stick spring's)? Then a
    write that failed after its backup, tried again, makes no second copy
    of the same file."""
    try:
        data = path.read_bytes()
        return any(p.read_bytes() == data
                   for p in path.parent.glob(f"{path.name}.bak-v{tag}*"))
    except OSError:
        return False


def _and(items: list[str]) -> str:
    """``F6``, ``F6 and the startup preset``, ``F2, F6 and slot 9``."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _bank_len(doc: dict) -> int:
    """How many slots a show document on disk holds (0 for none, or for a
    `bank` that is no list)."""
    bank = doc.get("bank")
    return len(bank) if isinstance(bank, list) else 0


# ---------------------------------------------------------------- marks

class Marks:
    """What is loaded, for an undo step that undoes a load (undo.py; plan
    15 WP1, fork 2): the show's own fields, every group's landed name and
    clean reference, each group's layout, and the loaded preset's note.
    Opaque to undo.py, which only calls `take`, `before` and `put` — so
    after undoing a load the library says the earlier preset is loaded
    again, and Save cannot write the earlier look over the later file."""

    def __init__(self, lib: Library):
        self.lib = lib

    def take(self) -> tuple:
        """(the show's mark, {group: landed}, {group: its `extra` hook's
        dict — the band layout}, the loaded preset's note and the notes
        its load left for the panel, the loaded preset's graph — plan 26
        A4, `preset.GraphSection.mark`, None with no presets), the
        loaded preset's GRAPH page layout (plan 28 N2, `Presets.layout`),
        the media channels' bins (plan 32, `Presets.media`), the GRAPH
        page's groups (plan 40 T2, `Presets.groups`) and the floor under
        their numbers (row 563, `Presets.group_high`), and the preset's bus
        cuts (plan 44 D3, `Presets.bus`)."""
        lib, pre = self.lib, self.lib.presets
        gs = getattr(pre, "graph", None)
        return (lib.project.mark(), self.lands(),
                {g: copy.deepcopy(hook()) for g, hook in lib._extra_hooks.items()},
                (getattr(pre, "note", ""), list(getattr(pre, "notes", ())),
                 list(getattr(pre, "desk_notes", ()))),
                gs.mark() if gs is not None else None,
                copy.deepcopy(getattr(pre, "layout", None) or {}),
                self._bins(pre),
                copy.deepcopy(getattr(pre, "groups", None) or []),
                getattr(pre, "group_high", 0),
                getattr(pre, "bus", None))

    @staticmethod
    def _bins(pre):
        """The media channels' bins (plan 32), None without them."""
        media = getattr(pre, "media", None)
        return media.to_json() if media is not None else None

    def lands(self) -> dict:
        """{group: landed} — every group's name, reference and re-apply
        road, by reference: cheap enough to read every frame."""
        lib = self.lib
        return {g: lib.landed(g) for g in lib.landed_groups()}

    def mend(self, pre: dict, lands: dict) -> None:
        """After the restore of a step that is not a load: a group whose
        landed state the restore itself moved (`pre` is `lands()` from
        just before it) — a `scene.select` put back adopts its scene —
        gets the step's own back, so the strip names what it named before
        the step. A group the restore left alone is left alone: a slider
        undone after a save-as stays on the new name (plan 15 fork 2)."""
        lib = self.lib
        now = self.lands()
        for group in {*pre, *now}:
            if now.get(group) != pre.get(group):
                lib.reland(group, lands.get(group, (None, None, None)))

    def before(self, mark: tuple) -> None:
        """First in a restore: a group whose layout differs from the
        mark's gets it back through its own `on_layout` hook, so its
        params exist before their values land — the order `_apply_doc`
        keeps. The loaded preset's graph goes back first of all (plan 26
        A4): an effect instance's params (`fx.acid.2.*`) exist before their
        values land."""
        lib = self.lib
        gs = getattr(lib.presets, "graph", None)
        if len(mark) > 4 and mark[4] is not None and gs is not None:
            gs.put(mark[4])
        for group, extra in mark[2].items():
            hook, now = lib._layout_hooks.get(group), lib._extra_hooks.get(group)
            if hook is None or now is None or not extra or extra.get("layout") is None:
                continue
            if now() != extra:
                hook(extra["layout"])
                lib._fresh_of(group)

    def put(self, mark: tuple) -> None:
        """Last in a restore: every group's name, reference and re-apply
        road as they were (`Library.reland`; a group that had none then
        has none now), the loaded preset's note and its load's notes for the
        panel, and the bank's lit slot.
        The show's own fields go back (`Project.remark`) only when the
        show itself differs — the undo of a show load. Otherwise the bank
        and startup are left as they are: they are in the show's file
        the moment they change, and reverting them in memory would make
        the show's dirty dot lie. `last_show` is never rewritten."""
        lib, pr = self.lib, self.lib.project
        show, landed, _extras, note = mark[:4]
        if not Project.same_show(show, pr.mark()):
            pr.remark(show)
        elif len(show) > Project.MARK_LAYOUT:
            # the same show: its GRAPH page positions still go back (plan 28
            # N2; the undo of a tidy) — unlike the bank, they are not in its
            # file until it is saved
            pr.layout = copy.deepcopy(show[Project.MARK_LAYOUT])
        for group in lib.landed_groups() - set(landed):
            lib.reland(group, (None, None, None))
        for group, was in landed.items():
            lib.reland(group, was)
        if lib.presets is not None:
            lib.presets.note, lib.presets.notes, lib.presets.desk_notes = (
                note[0], list(note[1]), list(note[2]))
            if len(mark) > 5:            # the GRAPH page's positions (plan 28 N2)
                lib.presets.layout = copy.deepcopy(mark[5])
            media = getattr(lib.presets, "media", None)
            if len(mark) > 6 and mark[6] is not None and media is not None:
                media.from_json(mark[6])     # the bins (plan 32)
            if len(mark) > 7:                # the GRAPH page's groups (plan 40 T2)
                lib.presets.groups = copy.deepcopy(mark[7])
            if len(mark) > 8:                # and the floor under their numbers (row 563)
                lib.presets.group_high = max(lib.presets.group_high, mark[8])
            if len(mark) > 9 and mark[9] is not None:   # the bus cuts (plan 44 D3)
                lib.presets.bus = mark[9]
        pr.follow()


# ---------------------------------------------------------------- library

class Library:
    """Module presets, presets and projects over one registry.

    Built before the registry (the preset bank's params need the
    project's bank), bound to it with ``attach(reg)``, which also captures
    the fresh-object values and applies the show a launch opens. `home` is
    the library tree — the one tier; tests pass a tmp_path and never touch
    ~/Hyperspace. A document kind (`kind`; preset.py's `Presets`) adds a
    group whose files the library keeps and someone else applies;
    ``presets`` is the `Presets` the bank loads through (None until app.py
    builds it after the router).
    """

    def __init__(self, home_dir: Path | None = None, *, machine: Path | None = None,
                 period: float = 0.5):
        # `home` is the library root — presets, shows, module groups, the
        # trash; `machine` the home for this machine's own files (last_show
        # here; config, bindings, windows, logs in app.py). The same folder
        # unless [library] path points elsewhere (plan 25)
        self.home = ensure_home(home_dir) if home_dir is None else Path(home_dir)
        self.machine = self.home if machine is None else Path(machine)
        # a named shared library that is not there (D5): never created,
        # nothing written into it, nothing listed — said once here and in
        # red on the SYSTEM page for as long as it runs
        self.missing: Path | None = None
        if (home_dir is not None and self.machine != self.home
                and not self.home.is_dir()):
            self.missing = self.home
            _missing.add(self.home)
        else:
            _missing.discard(self.home)
            (self.home / PROJECTS).mkdir(parents=True, exist_ok=True)
        self.period = period
        self.reg: Registry | None = None
        self.status = ""
        self.error = ""
        self.warning = ""
        # how many times `say` set each of `status` and `warning`: a line
        # said again in the same words shows again (the footer, ui.py).
        # Every line is set through `say`; only a clear ("") is assigned
        self.said: dict[str, int] = {}
        self._fresh: dict[str, Any] = {}
        self._current: dict[str, str | None] = {}     # group → loaded preset name
        self._loaded: dict[str, Any] = {}             # group → what that load produced
        self._layout_hooks: dict[str, Any] = {}
        self._extra_hooks: dict[str, Any] = {}    # group → what a save adds beside values
        self._load_hooks: dict[str, Any] = {}     # group → told the name after a load
        self._adopted: dict[str, Any] = {}        # group → how to re-apply an adopted preset
        self._kinds: dict[str, DocKind] = {}      # group → a document kind of its own
        self._kinds[PATCHES] = _patch_kind()      # plan 40 T1: spawned, never loaded
        self._fresh_extra: dict[str, dict] = {}   # group → its extra (layout) at attach
        self._defaults: dict[str, dict[str, Any]] = {}   # defaults(group), until a file moves
        self._docs: dict[Path, tuple[float, dict]] = {}   # parsed files, by mtime
        self._mtimes: dict[Path, float] = {}
        self._next = 0.0
        self.presets = None        # preset.Presets, set by its constructor
        self.project = Project(self)
        if self.missing is not None:
            text = missing_text(self.missing)
            print(f"library: {text}", file=sys.stderr)
            self.say(warning=text)
        self._open_default()
        self._mtimes = self._scan()

    def writable(self) -> None:
        """Raise LibraryError when the shared library is missing (plan 25
        D5): every write into the library asks first."""
        missing = self.__dict__.get("missing")      # (a Library from before a hot reload)
        if missing is not None:
            raise LibraryError(missing_text(missing))

    def say(self, status: str | None = None, *, warning: str | None = None) -> None:
        """Set `status` or `warning` and count it in `said`, so the footer
        shows the line again even when its words are the ones it showed
        last (plan 15 WP4: two presets put into slots one after the other,
        a slot cleared twice). Every line that reports something that just
        happened goes through here (plan 16 WP7: an empty F-key pressed
        twice, home with no startup preset pressed twice); a plain assignment
        is for clearing a line, and is not counted — so nothing that
        assigned the same words every frame could hold the footer open."""
        said = self.__dict__.setdefault("said", {})   # (a Library from before a hot reload)
        if status is not None:
            self.status = status
            said["status"] = said.get("status", 0) + 1
        if warning is not None:
            self.warning = warning
            said["warning"] = said.get("warning", 0) + 1

    def attach(self, reg: Registry) -> list[str]:
        """Bind the registry; its state right now is what "default" means.
        A group registered later is adopted the first time it is asked
        about (`_fresh_of`), so ``reset`` and ``is_dirty`` work for it too."""
        self.reg = reg
        self._fresh = reg.snapshot()
        # what a group's `extra` hook says now — the analyzer's layout as the
        # app started — is the fresh layout `Project.new` goes back to
        self._fresh_extra = {g: hook() for g, hook in self._extra_hooks.items()}
        self._defaults.clear()
        missing = self.project._apply()
        self.report(missing, self.project.name)
        return missing

    def _fresh_layouts(self) -> None:
        """Every group with a layout hook back to the layout it started with."""
        for group, extra in self._fresh_extra.items():
            hook = self._layout_hooks.get(group)
            if hook is not None and extra and extra.get("layout") is not None:
                hook(extra["layout"])
                self._fresh_of(group)

    def _fresh_of(self, group: str) -> dict[str, Any]:
        """The values a group's objects were built with — captured at
        attach(), or, for a param registered after it (a band a layout
        made, audit L6), the first time anyone asks about its group; a
        newly adopted id drops the group's cached defaults."""
        reg = self.reg
        if reg is not None:
            new = [k for k in reg.snapshot(group) if k not in self._fresh]
            if new:
                snap = reg.snapshot(group)
                self._fresh.update((k, snap[k]) for k in new)
                self._defaults.pop(group, None)
        return {k: v for k, v in self._fresh.items() if reg is not None and k in reg
                and reg[k].group == group}

    def _fresh_all(self) -> dict[str, Any]:
        for g in {p.group for p in (self.reg or []) if p.persist and p.group}:
            self._fresh_of(g)
        return dict(self._fresh)

    def kind(self, group: str, schema: str, *, load, document, signature,
             versions: tuple[int, ...] = (1,), text=None) -> None:
        """Register a document kind for `group` (see DocKind): its files
        live under ``<root>/<group>/`` like any preset's, the strip drives
        them, and the hooks apply and produce them."""
        self._kinds[group] = DocKind(schema, tuple(versions), load, document, signature, text)

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(self._kinds)

    def on_layout(self, group: str, hook) -> None:
        """Register who rebuilds a group's params from a preset's `layout`."""
        self._layout_hooks[group] = hook

    def extra(self, group: str, hook) -> None:
        """Register what a save of this group writes beside its values — the
        analyzer's ``{"layout": …}`` — so a preset saved from the strip
        carries it without the caller knowing (plan 07 contract; audit A2).
        Registered after attach(), what it says now is the group's fresh extra."""
        self._extra_hooks[group] = hook
        if self.reg is not None and group not in self._fresh_extra:
            self._fresh_extra[group] = hook()

    def on_apply(self, group: str, hook) -> None:
        """Register who is handed a module preset of this group as it lands
        — ``hook(name, doc)``, after its values, inside its undo step (plan
        33 R12 registered the fx module's run here; plan 40 T5 retired it,
        and no group registers one today). A load through the strip, a step
        or a file watch: not a rename, not a show."""
        self.__dict__.setdefault("_apply_hooks", {})[group] = hook

    def on_load(self, group: str, hook) -> None:
        """Register who is told the name a load of this group landed — the
        scene combo, so a strip load moves the selected scene."""
        self._load_hooks[group] = hook

    def last_show(self) -> str | None:
        """The show opened last (`<machine>/last_show`), or None — a machine
        file: two machines sharing a library each open their own last show."""
        try:
            name = (self._machine() / LAST_SHOW).read_text().strip()
        except OSError:
            return None
        return name or None

    def remember(self, name: str) -> None:
        """Note `name` — a show's file name less ``.hyp.json``
        (`Project.stem`) — as the show a launch opens (decision 22); a
        write that fails costs only the memory."""
        if name == self.last_show():
            return
        try:
            (self._machine() / LAST_SHOW).write_text(f"{name}\n")
        except OSError as e:
            print(f"library: {LAST_SHOW} not written ({e})", file=sys.stderr)

    def _machine(self) -> Path:
        return self.__dict__.get("machine") or self.home   # (one from before a hot reload)

    def _open_default(self) -> None:
        """The show a launch opens (decision 22): the one opened last
        (`last_show`), if its file is there and reads. Otherwise — no
        last show, a remembered one that is gone or will not open (the
        reason in `error`), a schema-1 file — an unsaved show called
        ``untitled`` with an empty bank, which a save writes into the
        library."""
        name = self.last_show()
        if name:
            user = self.project.path_for(name)
            if user.is_file():
                try:
                    self.project._take(_read_json(user), user, user.name)
                    return
                except LibraryError as e:
                    self.error = f"library: {e}"
        self.project._take({"schema": PROJECT_SCHEMA, "name": UNTITLED}, None)

    # ---- the tree ----

    def _roots(self):
        """The library's one root — none while a named shared library is
        missing (D5: nothing listed, nothing written)."""
        if self.__dict__.get("missing") is None:
            yield self.home

    def groups(self) -> list[str]:
        """Every group with a preset folder, a persisted param or a document
        kind — less ``macro``: a macro's meaning is its subscribers, which
        live in the preset, so it gets no module-preset strip (plan 13 §9);
        and less the retired module groups (`RETIRED_MODULES`, plan 40 T5),
        whatever an old library still keeps in their folders."""
        out = {p.group for p in (self.reg or [])
               if p.persist and p.group and p.group != "macro"}
        out.update(self._kinds)
        for root in self._roots():
            if root.is_dir():
                out.update(d.name for d in root.iterdir()
                           if d.is_dir() and d.name not in (PROJECTS, TRASH, *LEGACY_DIRS)
                           and not d.name.startswith("."))
        return sorted(out - set(RETIRED_MODULES))

    def _files(self, group: str) -> dict[str, Path]:
        """file key → path, every file of the group's folder: the stem, and
        for the presets (plan 48 row 584) the path under ``presets/`` less
        ``.json`` — ``party/deep/c`` — every folder down, less hidden ones
        (``.cache``)."""
        out: dict[str, Path] = {}
        for root in self._roots():
            d = root / group
            if not d.is_dir():
                continue
            if group != PRESETS:
                out.update((p.name[:-5], p) for p in d.glob("*.json"))
                continue
            for p in self._tree(d)[0]:
                out[p.relative_to(d).as_posix()[:-5]] = p
        return out

    def _tree(self, d: Path) -> tuple[list[Path], list[str]]:
        """The presets' folder walked (`_walk_dirs`): its ``*.json`` files
        and its folders (``party``, ``party/deep``)."""
        hit = self._walked(d)
        return hit["files"], hit["folders"]

    def _walked(self, d: Path) -> dict:
        """`_tree`'s walk, kept (plan 48 review) until a folder's mtime
        moves (a file or folder made, removed or renamed in it), the
        library writes (`_sync`) or WALK_TTL passes (a coarse or cloud
        filesystem's mtime may not move) — as `_doc` keeps a parse: the
        panel asks for the list every frame. Beside it, built on first ask,
        the files by `fold` (`byfold`, `path_of`'s miss)."""
        walks = self.__dict__.setdefault("_walks", {})   # (a Library from before a reload)
        hit = walks.get(d)
        now = _now()
        if (hit is not None and now - hit["at"] < WALK_TTL
                and all(_mtime(p) == m for p, m in hit["stamps"].items())):
            return hit
        stamps: dict[Path, int | None] = {}
        files: list[Path] = []
        folders: list[str] = []
        for h, found in _walk_dirs(d):
            stamps[h] = _mtime(h)
            files.extend(found)
            if h != d:
                folders.append(h.relative_to(d).as_posix())
        walks[d] = hit = {"at": now, "stamps": stamps, "files": files, "folders": folders}
        return hit

    def _byfold(self) -> dict[str | None, list[Path]]:
        """Every preset file by `fold` of its key (``party/trip``), kept
        with the walk — a list per key: two files may fold to one
        (`_resolve` refuses to pick)."""
        out: dict[str | None, list[Path]] = {}
        for root in self._roots():
            d = root / PRESETS
            if not d.is_dir():
                continue
            hit = self._walked(d)
            if "byfold" not in hit:
                byfold: dict[str | None, list[Path]] = {}
                for p in sorted(hit["files"]):
                    byfold.setdefault(fold(p.relative_to(d).as_posix()[:-5]), []).append(p)
                hit["byfold"] = byfold
            for k, ps in hit["byfold"].items():
                out.setdefault(k, []).extend(ps)
        return out

    def _folder_on_disk(self, folder: str) -> str | None:
        """The folder under ``presets/`` that `folder` names, spelled as it
        is on disk (``Party`` for ``party``: APFS folds case, so both are
        one folder and the list says it one way) — None when there is none."""
        want = fold_folder(folder)
        if want is None:
            return None
        if want == "":
            return ""
        for root in self._roots():
            d = root / PRESETS
            if d.is_dir():
                for f in self._tree(d)[1]:
                    if fold_folder(f) == want:
                        return f
        return None

    def _prefix(self, group: str, path: Path | None) -> str:
        """The folder a preset file sits in under ``presets/``, ending in
        ``/`` (``party/``) — ``""`` at the top, for any other group, or a
        path outside the library (plan 48)."""
        if group != PRESETS or path is None:
            return ""
        try:
            rel = path.parent.relative_to(self.home / group).as_posix()
        except ValueError:
            return ""
        return "" if rel == "." else f"{rel}/"

    def _fold(self, group: str, name: str) -> str | None:
        """What a name is compared by — case and spacing folded: its slug,
        and for a preset its folder too (``party/trip-2``, `path_slug`
        lowered); None for a preset name that could not name a file
        (``../x``)."""
        return slug(name) if group != PRESETS else fold(name)

    def folder_of(self, group: str, name: str | None) -> tuple[str, str]:
        """(folder, leaf) of a preset name — one rule (plan 48 review): a
        ``/`` in a listed name always means a folder (a file's own ``/`` is
        listed as ``" - "``, `harmless`), so the name is split at its last
        ``/``; ``""`` is the top. Any other group has no folders."""
        if not name:
            return "", name or ""
        return split_name(name) if group == PRESETS else ("", name)

    def _leaf(self, group: str, path: Path) -> str:
        """The name a file is listed by, less its folder: its own ``name``
        (else its stem), for a preset with any ``/`` made harmless."""
        return self._shown(group, self._name_of(path))

    @staticmethod
    def _shown(group: str, name: str) -> str:
        return harmless(name) if group == PRESETS else name

    def _doc(self, path: Path) -> dict:
        """The parsed file, re-read only when its mtime moved (UI polls per frame)."""
        try:
            mtime = path.stat().st_mtime
        except OSError as e:
            raise LibraryError(f"{path.name}: {e}") from e
        hit = self._docs.get(path)
        if hit is None or hit[0] != mtime:
            self._docs[path] = hit = (mtime, _read_json(path))
        return hit[1]

    def _name_of(self, path: Path) -> str:
        try:
            return str(self._doc(path).get("name") or path.name[:-5])
        except LibraryError:
            return path.name[:-5]

    def _index(self, group: str, files: dict[str, Path] | None = None) -> dict[str, Path]:
        """display name → path; a name is also reachable by its slug.

        Two files of one folder with the same name inside — a cloud
        client's conflict copy, ``hi-frek (Dan's conflicted copy …).json``
        beside ``hi-frek.json`` (plan 25) — are both listed: the file whose
        stem is the name's slug keeps the name (else the lower stem), and
        the other is listed under its file stem, to be loaded, renamed or
        deleted.

        A preset in a folder under ``presets/`` is listed by its
        **folder-qualified** name (plan 48 row 584): ``party/TRIP`` for
        ``presets/party/trip.json`` whose own ``name`` is ``TRIP`` — the
        file keeps the leaf, the folder is the path. A top-level preset's
        name is bare, as before, so the rule above holds per folder. A
        file's own ``/`` is listed as ``" - "`` (`harmless`): a ``/`` in a
        listed name is always a folder."""
        out: dict[str, Path] = {}
        for p in (self._files(group) if files is None else files).values():
            pre = self._prefix(group, p)
            leaf = self._leaf(group, p)
            name = pre + leaf
            prev = out.get(name)
            if prev is not None:
                want = slug(leaf)
                keep, other = ((prev, p) if prev.name[:-5] == want
                               else (p, prev) if p.name[:-5] == want
                               else tuple(sorted((prev, p), key=lambda q: q.name)))
                out[name] = keep
                out.setdefault(self._prefix(group, other) + other.name[:-5], other)
                continue
            out[name] = p
        return out

    def path_of(self, group: str, name: str, *, loose: bool = False) -> Path | None:
        """The file a name resolves to: a listed name; else a file key —
        the slug, and for a preset its folder and slug compared by `fold`
        (``Party/Trip`` finds ``presets/party/trip.json``, as APFS does).
        With `loose` — a **read** only: a load, a pad, the startup preset,
        what a show still names — a preset name whose folder is not on
        disk also tries its `slug` among the top-level files, an old show's
        ``Ac/Dc`` for the top-level ``ac-dc.json`` (plan 48 review). A
        writer (`save_as`, `delete`, `rename`) never takes that road:
        ``party/TRIP`` typed with no ``party/`` is a new file in a new
        folder, never the top-level ``party-trip.json``. None for none, and
        for a preset name that could not name a file inside ``presets/``
        (``../x``, ``/etc/x``). Two files that answer to one spelling
        (``trip_2.json`` and ``trip-2.json``) resolve to neither by a fold:
        the file key spelled as on disk finds its own, any other spelling
        neither (a loose read says which two)."""
        say = (lambda text: self.say(warning=text)) if loose else None
        return self._resolve(group, name, self._lookup(group), loose=loose, say=say)

    def _lookup(self, group: str) -> tuple:
        """What `_resolve` reads, taken once per operation (review of #334:
        a rename or a frame's ask lists the folder once): the index, the
        file keys, and for the presets the files by `fold` and the folders
        on disk folded."""
        files = self._files(group)
        idx = self._index(group, files)
        if group != PRESETS:
            return idx, files, {}, set()
        folders: set[str | None] = set()
        for root in self._roots():
            if (root / PRESETS).is_dir():
                hit = self._walked(root / PRESETS)
                if "folded" not in hit:                 # kept with the walk, as byfold
                    hit["folded"] = {fold_folder(f) for f in hit["folders"]}
                folders |= hit["folded"]
        return idx, files, self._byfold(), folders

    @staticmethod
    def _resolve(group: str, name: str, snap: tuple, *, loose: bool,
                 say=None) -> Path | None:
        """`path_of` over a `_lookup` snapshot. A fold that two files answer
        to (``trip_2`` / ``trip-2``; ``Trip`` / ``trip`` on a case-sensitive
        disk) is never settled by sort order: a name that is a file key as
        on disk (``trip_2``) finds that file, any other spelling neither,
        and `say` (a loose read's) is told which two."""
        idx, files, byfold, folders = snap
        hit = idx.get(name)
        if hit is not None:
            return hit
        if group != PRESETS:
            return files.get(slug(name))
        key = fold(name)
        if key is None:
            return None
        hit = files.get(name)                       # a file key, as it is on disk
        if hit is not None:
            return hit

        def one(k: str | None) -> Path | None:
            found = byfold.get(k) or []
            if len(found) == 1:
                return found[0]
            if found and say is not None:
                say(f"{name}: two presets answer to that name — "
                    f"{found[0].name} and {found[1].name}; rename one")
            return None

        if byfold.get(key) or not loose:
            return one(key)
        folder = split_name(name)[0]
        if folder and fold_folder(folder) not in folders:
            return one(slug(name))                  # a top-level key has no "/"
        return None

    def list(self, group: str) -> list[str]:
        """Every preset of the group by name, case folded — the PRESETS
        page's list, the strip's arrows, the pad's walk."""
        return sorted(self._index(group), key=str.lower)

    def _taken(self, group: str) -> set[str]:
        """The slugs a new file of the group may not take: every file stem
        in the folder and every listed name — on a filesystem that folds
        case `Trip-2.json` is the file a save of "TRIP 2" would write over
        (`save_new`, `rename`). For the presets each is folded with its
        folder (`_fold`: ``party/trip-2``), so a name is taken only in its
        own folder (plan 48)."""
        if group != PRESETS:
            return ({slug(s) for s in self._files(group)}
                    | {slug(n) for n in self.list(group)})
        out = {self._fold(group, s) for s in self._files(group)}
        out |= {self._fold(group, n) for n in self.list(group)}
        out.discard(None)
        return out  # type: ignore[return-value]

    def still_named(self, name: str, path: Path | None = None) -> list[str]:
        """What in the open show still names the preset `name` (or, given,
        the file at `path`): its slots (``F6``, ``slot 12``) and its
        ``startup``."""
        pr, key = self.project, self._fold(PRESETS, name)
        snap = self._lookup(PRESETS)                   # one look for every slot
        target = path or self._resolve(PRESETS, name, snap, loose=True)

        def names(n: str | None) -> bool:
            return bool(n) and (n == name or (key is not None and self._fold(PRESETS, n) == key)
                                or (target is not None
                                    and self._resolve(PRESETS, n, snap, loose=True) == target))
        out = [slot_key(k) for k, n in enumerate(pr.bank) if names(n)]
        if names(pr.startup):
            out.append("the startup preset")
        return out

    def read(self, group: str, name: str) -> dict:
        path = self.path_of(group, name, loose=True)
        if path is None:
            raise LibraryError(f"{group}: no preset {name!r}")
        doc = copy.deepcopy(self._doc(path))
        kind = self._kinds.get(group)
        if kind is not None:                       # its own format: checked, not lifted
            schema = str(doc.get("schema") or "")
            k, _, v = schema.rpartition("/")
            if k != kind.schema or not v.isdigit() or int(v) not in kind.versions:
                raise LibraryError(f"{path.name}: schema {schema!r} is not a {kind.schema}")
            return doc
        doc = migrate_doc(doc, "hyperspace.preset")
        if doc.get("group", group) != group:
            raise LibraryError(f"{path.name} is a {doc['group']} preset, not {group}")
        return doc

    # ---- patches (plan 40 T1) ----

    def read_patch(self, name: str) -> dict:
        """The patch `name`: its file under ``<root>/patches/``, checked —
        the schema (`read`) and the shape (`patches.check`). A patch that is
        not there, or that check refuses, raises LibraryError with the
        reasons in words."""
        doc = self.read(PATCHES, name)
        refused = patchdoc.check(doc)
        if refused:
            path = self.path_of(PATCHES, name)
            raise LibraryError(f"{path.name if path else name}: " + "; ".join(refused))
        # wave 0 T1: a file from before (no `units` marker) has its depths
        # onto the effects' retapered params read as they were, measured
        # against this rig's effect files — the one door a patch comes in
        # by, so a spawn lands what tools/retaper_routes.py would write
        doc, _ = retaper_depths(doc, fx_files(self.reg))
        return doc

    def save_patch(self, doc: dict) -> Path:
        """Write patch `doc` as ``<home>/patches/<slug of its name>.json``
        — atomically (`_write_text`), a different text already there copied
        to the trash first, as `save_as` does — and nothing else: no preset,
        show or binding is touched. A document `patches.check` refuses is
        not written (LibraryError)."""
        self.writable()
        refused = patchdoc.check(doc)
        name = str(doc.get("name") or "").strip() if isinstance(doc, dict) else ""
        if not name:
            refused = ["a patch needs a name", *refused]
        if refused:
            raise LibraryError("patch not saved: " + "; ".join(refused))
        path = self.home / PATCHES / f"{slug(name)}.json"
        text = _json_text(doc)
        if path.is_file():
            try:
                old = path.read_text()
            except (OSError, ValueError):
                old = None                               # unreadable as text: keep it anyway
            if old != text and self._to_trash(path) is None:
                self.say(warning=f"{PATCHES}/{path.name}: overwritten — the old file could "
                                 "not be kept in the trash")
        _write_text(path, text)
        self._sync(path)
        self.say(f"{PATCHES}: saved {name}")
        return path

    # ---- defaults & values ----

    def default_name(self, group: str) -> str | None:
        if group in RETIRED_MODULES:   # plan 40 T5: an old fx/default.json is no default
            return None
        name = DEFAULT_NAMES.get(group, "default")
        return name if self.path_of(group, name) is not None else None

    def defaults(self, group: str) -> dict[str, Any]:
        """What reset(group) produces: the default preset over the fresh values.
        Cached until a file in the tree moves (_sync, poll) or attach()."""
        if group in self._kinds:                   # no values of its own to fall back on
            return {}
        out = self._fresh_of(group)
        hit = self._defaults.get(group)
        if hit is not None and hit.keys() == out.keys():   # a layout can change the ids
            return dict(hit)
        name = self.default_name(group)
        if name is not None:
            try:
                out.update(_module_values(group, self.read(group, name)))
            except LibraryError as e:
                self.error = f"library: {e}"
                return out                             # not cached: the file may be fixed
        self._defaults[group] = dict(out)
        return out

    def resolved(self, group: str, values: dict[str, Any]) -> dict[str, Any]:
        """A preset's values over the group's defaults, ids this registry
        has — the one fill-in for a partial file, whichever road applies it
        (a strip load, or the scene combo re-tuning from a scene)."""
        out = self.defaults(group)
        out.update(values)
        return {k: v for k, v in out.items() if k in self.reg}

    def _landed(self, group: str, name: str | None, loaded: dict[str, Any] | None,
                reapply=None) -> None:
        """One place for what "the group's current preset" means: its name,
        the values it produced (what is_dirty compares against) and, for a
        preset someone else applied, how to apply it again when its file
        changes on disk. The presets' is their own (`_owner`, plan 44 D3)."""
        owner = self._owner(group)
        if owner is not None:
            owner.landing = (name, loaded, reapply)
            return
        self._current[group] = name
        if loaded is None:
            self._loaded.pop(group, None)
        else:
            self._loaded[group] = loaded
        if reapply is None:
            self._adopted.pop(group, None)
        else:
            self._adopted[group] = reapply

    def label(self, group: str, name: str | None) -> None:
        """Record `name` as the group's current module preset, the group's
        state as it now stands being what "clean" means — a preset's
        module label (plan 13 D3): the strip shows the name and a clean
        dot, and nothing is loaded. None: no module preset, but the state
        as it stands is still what "clean" means — a preset that names no
        module for the group landed it, and the rail's dot compares against
        that, not fresh defaults (plan 14 WP4)."""
        loaded = self.reg.snapshot(group) if self.reg is not None else None
        self._landed(group, name, loaded)

    def landed(self, group: str) -> tuple:
        """The group's landed state, opaque, for an undo to hand back."""
        owner = self._owner(group)
        if owner is not None:
            return tuple(owner.landing)
        return (self._current.get(group), self._loaded.get(group), self._adopted.get(group))

    def _owner(self, group: str):
        """Who keeps `group`'s landing when it is not the library (plan 44
        D3): the presets kind's `Presets` — its `landing`, (current, what
        its load produced, how to re-apply) — so a deck's dirty dot is its
        own; None for every other group."""
        pre = self.__dict__.get("presets")
        if group == PRESETS and pre is not None and hasattr(type(pre), "landing"):
            return pre
        return None

    def landed_groups(self) -> set[str]:
        """Every group with a landing: the library's and the presets'."""
        out = {*self._current, *self._loaded, *self._adopted}
        if self._owner(PRESETS) is not None:
            out.add(PRESETS)
        return out

    def reland(self, group: str, mark: tuple) -> None:
        """Put back what landed() returned — the analyzer's reset undo."""
        self._landed(group, *mark)

    def restore(self, values: dict[str, Any]) -> list[str]:
        """restore() in registry order, whatever order the file had."""
        reg = self._need_reg()
        ordered = {p.id: values[p.id] for p in reg if p.id in values}
        reg.restore(ordered)
        return [k for k in values if k not in reg]

    def _need_reg(self) -> Registry:
        if self.reg is None:
            raise LibraryError("library not attached to a registry")
        return self.reg

    def report(self, missing: list[str], where: str) -> None:
        if missing:
            shown = ", ".join(missing[:4]) + ("…" if len(missing) > 4 else "")
            self.say(warning=f"{where}: {len(missing)} unknown id(s): {shown}")
            print(f"library: {self.warning}", file=sys.stderr)

    # ---- presets: the surface the strip draws ----

    def current(self, group: str) -> str | None:
        owner = self._owner(group)
        if owner is not None:
            return owner.landing[0]
        return self._current.get(group)

    def load(self, group: str, name: str) -> list[str]:
        """Apply a preset; returns the ids it names that this registry lacks."""
        if group not in self._kinds:
            self._need_reg()
        doc = self.read(group, name)
        return self._apply_doc(group, name, doc, path=self.path_of(group, name, loose=True))

    def _apply_doc(self, group: str, name: str, doc: dict, *, path: Path | None = None,
                   quiet: bool = False) -> list[str]:
        """One road in for a preset document, wherever it came from — the
        strip, the project's module list, a file edited on disk: a kind's
        loader, or the layout hook first and then the values over the
        group's defaults. `quiet` (a project load) leaves `status` alone."""
        kind = self._kinds.get(group)
        if kind is not None:
            try:
                missing = list(kind.load(doc, path) or [])
            except (ValueError, KeyError, TypeError, AttributeError, OSError) as e:
                raise LibraryError(f"{group}/{name}: {e}") from e
            if path is not None:
                self._sync(path)                       # a migrated user file, rewritten once
            # its listed name: the file's own, under its folder (plan 48) —
            # or, for a conflict copy listed under its stem, the name it was
            # loaded by, so the list's ◀ ▶ step on from it
            shown = (self._prefix(group, path) + self._shown(group, str(doc["name"]))
                     if path is not None and doc.get("name") else None)
            if shown is None or (shown != name and self.path_of(group, shown) != path):
                shown = name if path is not None else (doc.get("name") or name)
            self._landed(group, shown, kind.signature())
        else:
            # a module preset load, step or file-watch re-apply: one undo
            # step, the layout it may rebuild included (undo.py, plan 15)
            undo.push(f"{group}: {doc.get('name') or name}", load=True)
            hook = self._layout_hooks.get(group)
            if hook is not None and doc.get("layout") is not None:
                hook(doc["layout"])                    # rebuild params first
                self._fresh_of(group)                  # …and their build values are "fresh"
            values = _module_values(group, doc)
            # (an old module file's retired ids — plan 33 T7's orders and
            # targets — are no unknown ids: the wires say them now)
            missing = [k for k in values if k not in self.reg and not retired(k)]
            resolved = self.resolved(group, values)
            self.restore(resolved)
            # (getattr: a Library from before a hot reload has no apply hooks)
            apply = getattr(self, "_apply_hooks", {}).get(group)
            if apply is not None:
                apply(name, doc)
                # plan 36 T3: a hook that lands a graph declares params (an
                # fx module's effects exist once its run names them): their
                # values land now, and are no longer missing
                late = self.resolved(group, values)
                if late != resolved:
                    self.restore(late)
                    resolved = late
                missing = [k for k in values if k not in self.reg and not retired(k)]
            self._landed(group, doc.get("name") or name, resolved)
        self.report(missing, f"{group}/{name}")
        if not quiet:
            self.say(f"{group}: {self.current(group)}")
        hook = self._load_hooks.get(group)
        if hook is not None:
            hook(self.current(group))
        return missing

    def land_unsaved(self, group: str, name: str, doc: dict) -> list[str]:
        """Apply `doc` as the group's current preset `name` that no file
        holds (plan 35 T7's `Presets.new`): the one road in (`_apply_doc`,
        no path), then nothing to be clean against — dirty until it is saved,
        the Project's own rule for a show never saved. Returns the unknown
        ids."""
        missing = self._apply_doc(group, name, doc)
        self._landed(group, name, ())
        return missing

    def adopt(self, group: str, name: str, reapply) -> None:
        """A preset applied by someone else — the scene combo landing a
        scene's values on the analyzer itself: make it the group's current
        preset, with the group's state as it now stands as what "clean"
        means (the combo applies no layout, so the file's layout ids are
        not the reference), and `reapply` as what poll() calls when the
        file changes on disk, in place of a whole load."""
        loaded = self.reg.snapshot(group) if self.reg is not None else None
        again = self._current.get(group) == name
        self._landed(group, name, loaded, reapply)
        if again:
            # the same scene set again — a knob on `scene.select` sends the
            # same choice many times in one turn: no news, and the footer's
            # slot is not taken from a line that is (review of PR #92)
            self.status = f"{group}: {name}"
        else:
            self.say(f"{group}: {name}")

    def _step(self, group: str, n: int) -> str | None:
        names = self.list(group)
        if not names:
            return None
        cur = self.current(group)
        k = (names.index(cur) + n) % len(names) if cur in names else (0 if n > 0 else -1)
        self.load(group, names[k])
        return names[k]

    def next(self, group: str) -> str | None:
        return self._step(group, 1)

    def prev(self, group: str) -> str | None:
        return self._step(group, -1)

    def save_as(self, group: str, name: str, *, extra: dict | None = None) -> Path:
        """Write the group's bases as a preset and make it current — over
        the file the name already resolves to (`path_of`: the one the list
        found it by, whatever its stem — one tier, 2026-10-28: a save never
        leaves a second file of the same name beside the first), else a new
        ``<slug>.json``. A file already there whose text differs is copied
        to the trash first (`to_trash`); a save that changes nothing trashes
        nothing, and a copy that fails does not stop the save — `warning`
        says the old file was not kept (plan 15 fork 6)."""
        self.writable()
        doc = self.document(group, name, extra=extra)
        path = self.path_of(group, name)
        renamed = None
        if group == PRESETS:
            # plan 48 row 587: a folder-qualified name is written in its
            # folder (made if need be); the file holds the leaf, and the
            # name is spelled as the list will spell it — the folder as it is
            # on disk (review: `Party/NEW` into an existing `party/`)
            folder, leaf = self.folder_of(group, name)
            if not leaf.strip():                        # "party/", "party/   "
                raise LibraryError("a preset needs a name")
            if path is not None:
                raw = self._name_of(path)
                if raw != harmless(raw):
                    renamed = raw                       # its own "/" goes (the ruling)
                folder = self._prefix(group, path)[:-1]  # as on disk
            else:
                key = path_slug(name)              # LibraryError on ../ or /abs
                folder = key.rpartition("/")[0]
                folder = self._folder_on_disk(folder) or folder
                leaf = leaf.strip()
                path = self.home / group / (f"{folder}/" if folder else "") / f"{slug(leaf)}.json"
            doc["name"] = leaf
            name = f"{folder}/{leaf}" if folder else leaf
        elif path is None:
            path = self.home / group / f"{slug(name)}.json"
        kind = self._kinds.get(group)
        text = (kind.text(doc) if kind is not None and kind.text is not None
                else _json_text(doc))
        if path.is_file():
            try:
                old = path.read_text()
            except (OSError, ValueError):
                old = None                               # unreadable as text: keep it anyway
            if old != text and self._to_trash(path) is None:
                self.say(warning=f"{group}/{path.name}: overwritten — the old file could "
                                 "not be kept in the trash")
        _write_text(path, text)
        self._sync(path)
        self._landed(group, name, kind.signature() if kind is not None
                     else self.resolved(group, doc["values"]))
        # review of #334: a file's own "/" written as " - " is said, once —
        # the next save finds the name it now holds
        self.say(f"{group}: saved {name}" + (f" (was {renamed})" if renamed else ""))
        hook = self._load_hooks.get(group)
        if kind is not None and hook is not None:   # a kind's current moved: say so
            hook(name)                               # (the bank's light, preset.py)
        return path

    def document(self, group: str, name: str, *, extra: dict | None = None) -> dict:
        """The group's bases as a preset document — with whatever the
        group's `extra` hook adds beside the values (the analyzer's layout),
        unless the caller brought its own. Every band document the library
        writes is built here: a file, or a project's inline module copy. A
        document kind's is its own hook's."""
        kind = self._kinds.get(group)
        if kind is not None:
            return kind.document(name)
        reg = self._need_reg()
        doc = {"schema": PRESET_SCHEMA, "group": group, "name": name,
               "values": reg.snapshot(group)}
        if group == "camera":
            doc[UNITS_KEY] = dict(UNITS)     # its pan is in world units (plan 26 A2)
        if extra is None and group in self._extra_hooks:
            extra = self._extra_hooks[group]()
        if extra:
            doc.update(extra)
        return doc

    def overwrite(self, group: str, *, extra: dict | None = None) -> Path | None:
        """Save over the current preset (its old text kept in the trash)."""
        cur = self.current(group)
        return None if cur is None else self.save_as(group, cur, extra=extra)

    def delete(self, group: str, name: str) -> bool:
        """Remove a preset. The file is copied to the trash first
        (`to_trash`), and a copy that fails **refuses the delete**
        (`LibraryError`): a full disk cannot make a delete unrecoverable
        (plan 15 fork 6). False when there is no such preset."""
        self.writable()
        path = self.path_of(group, name)
        if path is None:
            return False
        # its listed name (review of #334: what a restore matches the
        # warning by) and, while the file is there to resolve to, what in
        # the open show still names it — not cleared for the owner, so a
        # restore to the old name makes them work again (plan 19 WP4)
        shown = (name if self._index(group).get(name) == path
                 else self._prefix(group, path) + self._leaf(group, path))
        still = self.still_named(shown, path) if group == PRESETS else []
        if self._to_trash(path) is None:
            raise LibraryError(f"{path.name}: not deleted — it could not be kept in the "
                               f"trash ({self._trash_dir()})")
        try:
            path.unlink()
        except OSError as e:
            raise LibraryError(f"{path.name}: {e}") from e
        self._sync(path)
        if self.current(group) in (name, shown) and self.path_of(group, shown) is None:
            self._landed(group, None, None)
        if group == PRESETS:
            if still:
                self.say(warning=f"{shown} is in the trash — {_and(still)} still "
                                 f"name{'s' if len(still) == 1 else ''} it; restore it from "
                                 "the trash, or clear the slot")
            else:
                self.say(f"{shown} is in the trash — the PRESETS page's trash can restore it")
        return True

    def rename(self, group: str, old: str, new: str) -> Path:
        """Rename a preset (plan 19 WP4): the file, the name inside it, and
        every show in the home that names it. Raises LibraryError and
        changes nothing when `old` is not a preset of the presets' group
        (or a patch), `new` is empty or taken, or the old file cannot be
        kept in the trash. No undo step: the nets are the old file in
        ``trash/presets/``, each rewritten show in ``trash/projects/``, and
        renaming it back.

        In order, so that a stop at any point loses nothing:

        1. refuse — an empty name, a name whose slug is taken (`_taken`: a
           file stem in the folder or a listed name, less this preset's
           own). A new name with the old file's slug (case or spacing)
           keeps the file's stem: the file is rewritten in place, its old
           text kept in the trash first;
        2. the new file ``presets/<slug(new)>.json`` is written, created
           exclusively — the old document with only ``name`` changed, in the
           kind's own text. *Stopped here: two files, one look; nothing lost*;
        3. the old file is copied to the trash (`to_trash`) — a copy that
           fails removes the new file and raises — and then removed.
           *Stopped after the copy: both files and the copy. After the
           removal: the new file and the copy; the shows still name the old
           name (a slot says "no preset", the trash holds it)*;
        4. both paths are synced (our own writes: the watcher sees no
           edit); the loaded preset keeps its clean reference under the new
           name, so an unsaved edit stays one, and the load hook is told;
        5. every ``hyperspace.project/2`` show in ``<home>/projects`` whose
           bank or startup names the old preset is copied to the trash,
           then written with the new name — the open show through its
           `Project` (its dot and the bank's light stay right). A show whose
           copy or write fails is left as it is; a schema-1 show is left
           alone; both are named in the warning. *Stopped mid-way: the
           shows done name the new name and their old files are in the
           trash; the rest name the old one*;
        6. `Project.follow()`; the status says how many shows changed."""
        self.writable()
        # plan 40 T1: a patch renames the same way, less step 5 (no show
        # names a patch; a group's provenance slug is the preset's to keep)
        if group not in RENAMABLE:
            raise LibraryError(f"{group}: only a preset can be renamed (or a patch)")
        snap = self._lookup(group)                 # one look for the whole rename
        idx, files = snap[0], snap[1]
        path = self._resolve(group, old, snap, loose=False)
        if path is None:
            raise LibraryError(f"no preset {old!r}")
        new = (new or "").strip()
        # plan 48 row 584: a rename keeps the folder — `new` is the leaf
        # (the folder may be spelled in front of it, as the list spells it);
        # moving a preset between folders is stage 2's
        pre = self._prefix(group, path)
        leaf = new[len(pre):].strip() if pre and new.startswith(pre) else new
        if group == PRESETS and "/" in leaf:
            raise LibraryError(f"{new}: a rename keeps the folder — a name has no '/' "
                               "(move the file in Finder to change its folder)")
        if not leaf:
            raise LibraryError("a preset needs a name")
        new = pre + leaf
        stem = path.name[:-5]
        if new == old:
            return path
        doc = _read_json(path)
        # what names this file, folded: its listed names and its file key
        # (and, at the top, its raw stem, as before plan 48)
        mine = {self._fold(group, n) for n, p in idx.items() if p == path}
        mine |= {self._fold(group, s) for s, p in files.items() if p == path}
        if not pre:
            mine.add(stem)
        mine -= {None, ""}
        # review of #334: what each slot resolved to before the rename (a
        # loose read, as a pad loads it), so a slot naming it by an old
        # spelling (`Ac/Dc`) follows it too
        # (`snap`, taken above, is the library as it was before)
        named = lambda n: self._resolve(group, n, snap, loose=True) == path
        in_place = slug(leaf) == stem
        # `_taken` less this preset's own stem and name — in its own folder
        taken = ({self._fold(group, s) for s, p in files.items() if p != path}
                 | {self._fold(group, n) for n, p in idx.items() if p != path})
        if self._fold(group, new) in taken:
            raise LibraryError(f"{leaf}: that name is taken — pick another")
        kind = self._kinds.get(group)
        doc["name"] = leaf
        text = (kind.text(doc) if kind is not None and kind.text is not None
                else _json_text(doc))
        dst = path if in_place else path.parent / f"{slug(leaf)}.json"
        if in_place:
            # 2–3 in one: keep the old text, then write over it
            if self._to_trash(path) is None:
                raise LibraryError(f"{path.name}: not renamed — it could not be kept in the "
                                   f"trash ({self._trash_dir()})")
            _write_text(path, text)
        else:
            try:
                with open(dst, "x") as f:                  # 2. never over a file
                    f.write(text)
            except FileExistsError as e:
                raise LibraryError(f"{new}: that name is taken — pick another") from e
            except OSError as e:
                dst.unlink(missing_ok=True)
                raise LibraryError(f"{dst.name}: {e}") from e
            if self._to_trash(path) is None:          # 3.
                dst.unlink(missing_ok=True)
                raise LibraryError(f"{path.name}: not renamed — it could not be kept in the "
                                   f"trash ({self._trash_dir()})")
            try:
                path.unlink()
            except OSError as e:
                dst.unlink(missing_ok=True)
                raise LibraryError(f"{path.name}: not renamed ({e})") from e
        self._sync(path, dst)                              # 4.
        cur = self.current(group)
        if cur is not None and (cur == old or self._fold(group, cur) in mine):
            self._landed(group, new, self.landed(group)[1])
            hook = self._load_hooks.get(group)
            if hook is not None:
                hook(new)
        if group == PATCHES:
            self.say(f"renamed {old} → {new}")
            return dst
        done, left = self._repoint(old, new, mine, named)  # 5.
        self.project.follow()                              # 6.
        self.say(f"renamed {old} → {new} ({done} show{'' if done == 1 else 's'} updated)")
        if left:
            self.say(warning=f"renamed {old} → {new}; not updated: {', '.join(left)}")
        return dst

    def _repoint(self, old: str, new: str, mine: set[str],
                 named=lambda n: False) -> tuple[int, list[str]]:
        """Step 5 of `rename`: every user show naming the old preset (by its
        name, or a slug of it or of its file stem) names the new one, each
        copied to the trash first. Returns (shows written, shows left as
        they were with why)."""

        def hit(n) -> bool:
            return isinstance(n, str) and bool(n) and (
                n == old or self._fold(PRESETS, n) in mine or named(n))

        pr, done, left = self.project, 0, []
        for show in sorted((self.home / PROJECTS).glob(f"*{PROJECT_SUFFIX}")):
            label = show.name[: -len(PROJECT_SUFFIX)]
            if pr.path is not None and show == pr.path:
                if not (any(hit(n) for n in pr.bank) or hit(pr.startup)):
                    continue
                if self._to_trash(show) is None:
                    left.append(f"{label} (it could not be kept in the trash)")
                    continue
                was = (list(pr.bank), pr.startup)
                pr.bank = [new if hit(n) else n for n in pr.bank]
                pr.startup = new if hit(pr.startup) else pr.startup
                try:
                    pr.write()
                except (LibraryError, OSError) as e:
                    pr.bank, pr.startup = was
                    left.append(f"{label} ({e})")
                    continue
                done += 1
                continue
            try:
                doc = _read_json(show)
            except LibraryError as e:
                left.append(f"{label} (would not read: {e})")
                continue
            bank = doc.get("bank") if isinstance(doc.get("bank"), list) else []
            if not (any(hit(n) for n in bank) or hit(doc.get("startup"))):
                continue
            if doc.get("schema") != PROJECT_SCHEMA:
                left.append(f"{label} (a {doc.get('schema')} show: plan 13's migration owns it)")
                continue
            if self._to_trash(show) is None:
                left.append(f"{label} (it could not be kept in the trash)")
                continue
            doc["bank"] = [new if hit(n) else n for n in bank]
            if hit(doc.get("startup")):
                doc["startup"] = new
            try:
                _write_json(show, doc)
            except LibraryError as e:
                left.append(f"{label} ({e})")
                continue
            self._sync(show)
            done += 1
        # the open show with no file yet (a new show): its bank in memory
        if pr.path is None and (any(hit(n) for n in pr.bank) or hit(pr.startup)):
            pr.bank = [new if hit(n) else n for n in pr.bank]
            pr.startup = new if hit(pr.startup) else pr.startup
        return done, left

    # ---- the trash: a view of it, restore, empty (plan 19 WP4) ----

    def _trash_dir(self) -> Path:
        """``<machine>/trash`` — this Mac's trash (plan 48 row 586): what
        a save overwrote, a delete removed or a rename replaced, never in
        a synced library, so one Mac's deletes do not fill the other's."""
        return self._machine() / TRASH

    def _old_trash(self) -> Path | None:
        """``<library>/trash`` when the library is a folder of its own
        (plan 25): the trash every Mac wrote into before plan 48 — listed
        and restorable, never written, never emptied (row 586). None when
        the library is the machine home (the same folder) or missing."""
        if self.__dict__.get("missing") is not None:
            return None
        try:                                           # a symlinked home is the same folder
            if self.home.resolve() == self._machine().resolve():
                return None
        except OSError:
            return None
        old = self.home / TRASH
        return old if old.is_dir() else None

    def _to_trash(self, path: Path) -> Path | None:
        """`to_trash` into this Mac's trash, under the folder `path` came
        from relative to the library (``presets/party``), so a restore puts
        it back there."""
        try:
            origin = path.parent.relative_to(self.home).as_posix()
        except ValueError:
            origin = path.parent.name
        return to_trash(path, self._machine(), origin)

    def _trash_roots(self) -> list[tuple[Path, Path, bool]]:
        """(root, root resolved, whether it is the old library trash) for
        this Mac's trash and the library's old one, each resolved once."""
        out: list[tuple[Path, Path, bool]] = []
        for root, old in ((self._trash_dir(), False), (self._old_trash(), True)):
            if root is None:
                continue
            try:
                resolved = root.resolve()
            except OSError:
                continue
            if all(resolved != r for _root, r, _old in out):   # one folder, listed once
                out.append((root, resolved, old))
        return out

    @staticmethod
    def _under(path: Path, roots) -> tuple[Path, str, str, bool] | None:
        """Where a trashed file lies among `roots` (`_trash_roots`) — its
        symlinks and any ``..`` resolved: (the trash root, its group, the
        folder under the group, whether it is the old library trash), or
        None when it lies in none at least one folder down."""
        try:
            real = path.resolve()
        except OSError:
            return None
        for root, resolved, old in roots:
            try:
                parts = real.parent.relative_to(resolved).parts
            except ValueError:
                continue
            if parts and not any(p.startswith(".") for p in parts):
                return root, parts[0], "/".join(parts[1:]), old
        return None

    def _trash_of(self, path: Path) -> tuple[Path, str, str, bool] | None:
        """`_under` both trashes: the guard on every file the trash's view
        restores or deletes."""
        return self._under(path, self._trash_roots())

    def trash(self) -> list[Trashed]:
        """Every file under this Mac's ``<machine>/trash/<group>/…`` (a
        preset from a folder one folder down per folder, plan 48), newest
        first — what "empty" removes, and nothing else: what you see is
        what goes; then the library's old trash (`_old_trash`), each marked
        ``old``: restorable (a copy: the file stays), never emptied."""
        out = []
        roots = self._trash_roots()
        for root, _resolved, old in roots:
            if not root.is_dir():
                continue
            for group in sorted(root.iterdir()):
                if not group.is_dir() or group.name.startswith("."):
                    continue
                for path in _walk(group, "*"):
                    # only what `to_trash` writes: <stem>.<stamp>[-n]<suffix>, never a
                    # dotfile — a Finder `.DS_Store` is not the owner's, and a restore
                    # would make it a preset (review of PR #117)
                    m = _TRASHED.fullmatch(path.name)
                    if (m is None or path.name.startswith(".")
                            or not (path.is_file() or path.is_symlink())):
                        continue
                    stem = m["stem"]
                    if stem.endswith(PROJECT_SUFFIX[:-5]) and group.name == PROJECTS:
                        stem = stem[: -len(PROJECT_SUFFIX[:-5])]
                    name = stem
                    if path.is_file() and self._under(path, roots) is not None:
                        try:
                            name = self._shown(group.name,
                                               str(_read_json(path).get("name") or stem))
                        except LibraryError:
                            pass
                    folder = path.parent.relative_to(group).as_posix()
                    folder = "" if folder == "." else folder
                    if folder and group.name == PRESETS:
                        name = f"{folder}/{name}"
                    out.append(Trashed(path, group.name, name,
                                       _when(m["stamp"]) if m else "", folder, old))
        return sorted(out, key=lambda t: (not t.old, _order(t.path), t.path.name),
                      reverse=True)

    def restore_trash(self, item: Trashed) -> str:
        """Put a trashed file back as ``<home>/<group>/<stem><suffix>`` —
        never over a file: the target is created exclusively. When the stem
        is taken (a file of that stem in the group's folder), or for a
        preset the name inside is taken by another listed one, it is
        restored under the next free name (`next_name`) with that name
        written inside, and the status says so. Only after the write
        succeeds is the trash copy removed. A restored show is listed, not
        opened; a restore loads nothing. Returns the name it now has."""
        self.writable()
        path = item.path
        where = self._trash_of(path) if path.is_file() else None
        if where is None:
            raise LibraryError(f"{path.name}: not in the trash ({self._trash_dir()})")
        m = _TRASHED.fullmatch(path.name)
        if m is None or path.name.startswith("."):
            raise LibraryError(f"{path.name}: not restored — not a file the trash kept")
        # the group and the folder it came from are where it lies in the
        # trash (plan 48: ``trash/presets/party/`` → ``presets/party/``)
        _root, group, sub, _old = where
        if sub and group == PRESETS:
            # review of #334: the folder as it is on disk now (APFS folds
            # case), so what is taken there is read from the right place
            sub = self._folder_on_disk(sub) or sub
        filename = f"{m['stem']}{m['suffix']}"
        show = group == PROJECTS
        suffix = PROJECT_SUFFIX if show and filename.endswith(PROJECT_SUFFIX) else ".json"
        stem = filename.removesuffix(suffix)
        # only the presets have folders (plan 48): a file a non-preset group
        # kept deeper goes back where that group lists it
        sub = sub if group == PRESETS else ""
        folder = self.home / group / sub if sub else self.home / group
        pre = f"{sub}/" if sub and group == PRESETS else ""
        data = path.read_bytes()
        try:
            doc = json.loads(data)
            doc = doc if isinstance(doc, dict) else None
        except ValueError:
            doc = None
        name = str((doc or {}).get("name") or stem)
        if show:
            stems = {p.name[: -len(PROJECT_SUFFIX)] for root in self._roots()
                     for p in (root / PROJECTS).glob(f"*{PROJECT_SUFFIX}")}
            names = {slug(s) for s in stems}
        else:
            # what is taken in the folder it goes back to
            stems = {p.name[:-5] for p in self._files(group).values() if p.parent == folder}
            names = ({slug(n[len(pre):]) for n, p in self._index(group).items()
                      if p.parent == folder} if group == PRESETS else set())
        taken = {slug(s) for s in stems} | names
        renamed = slug(stem) in {slug(s) for s in stems} or (
            group == PRESETS and slug(name) in names)
        if renamed:
            if doc is None:
                raise LibraryError(f"{path.name}: not restored — {stem} is taken and the file "
                                   "would not read, so it cannot be renamed")
            new = next_name(name, taken)
            doc["name"] = new
            stem = slug(new)
            kind = self._kinds.get(group)
            text = (kind.text(doc) if kind is not None and kind.text is not None
                    else _json_text(doc))
            data = text.encode()
        dst = folder / f"{stem}{suffix}"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with open(dst, "xb") as f:                     # never over a file
                f.write(data)
        except FileExistsError as e:
            raise LibraryError(f"{dst.name}: not restored — a file is there") from e
        except OSError as e:
            dst.unlink(missing_ok=True)
            raise LibraryError(f"{dst.name}: not restored ({e})") from e
        self._sync(dst)
        if group == PRESETS and self.warning.startswith(f"{pre}{self._shown(group, name)} is in the trash"):
            self.warning = ""                              # what × said is no longer so
        now = pre + self._shown(group, str(doc["name"]) if renamed else name)
        what = f"show {now}" if show else now
        if renamed:
            self.say(f"restored as {what} — {pre}{name} is taken")
        else:
            self.say(f"restored {what}" + (" — it is in the show list" if show else ""))
        if where[3]:
            # the library's old trash is never written (plan 48 review): a
            # restore from it is a copy, and the file stays where it is —
            # the other Mac may be restoring it too
            return now
        try:
            path.unlink()                                  # only after the write
        except OSError as e:
            self.say(warning=f"restored {now}; its copy stays in the trash ({e})")
        return now

    def empty_trash(self) -> int:
        """Delete every file `trash()` lists, and then the trash's folders
        left empty — the one delete in the app that keeps no copy (the
        panel asks twice). This Mac's trash only (plan 48 row 586): the
        library's old trash (`_old_trash`) is listed but never emptied
        here. A path that does not resolve under ``<machine>/trash/`` (a
        symlink out, a ``..``) is refused and left, and said. Returns how
        many files went."""
        self.writable()
        gone, refused, roots = 0, [], self._trash_roots()
        for item in self.trash():
            if item.old:
                continue
            path = item.path
            where = None if path.is_symlink() else self._under(path, roots)
            if where is None or where[3]:
                refused.append(path.name)
                continue
            try:
                path.unlink()
                gone += 1
            except OSError as e:
                refused.append(f"{path.name} ({e})")
        root = self._trash_dir()
        if root.is_dir():
            # the folders left empty, deepest first (`os.walk` bottom-up
            # never goes through a link)
            for here, dirs, _files in os.walk(root, topdown=False, followlinks=False):
                for d in dirs:
                    folder = Path(here) / d
                    if not folder.is_symlink():
                        try:
                            folder.rmdir()                 # only when it is empty
                        except OSError:
                            pass
        if refused:
            self.say(warning=f"trash: emptied {gone}; left {', '.join(refused[:4])}"
                             + (f" (+{len(refused) - 4} more)" if len(refused) > 4 else "")
                             + " — not in the trash folder")
        else:
            self.say(f"trash: {gone} file{'' if gone == 1 else 's'} deleted for good")
        return gone

    def is_dirty(self, group: str) -> bool:
        """Have the group's bases moved off the loaded (or default) preset?
        For a document kind: has its signature moved since the last load or
        save (nothing loaded yet is never dirty). Floats compare within
        undo's tolerance (`undo.alike`, plan 16 WP7): the last bits a
        performer leaves in a base it took light no dot."""
        owner = self._owner(group)
        if owner is not None:                # plan 44 D3: the presets' own dot
            return owner.is_dirty()
        kind = self._kinds.get(group)
        if kind is not None:
            ref = self._loaded.get(group)
            return ref is not None and not undo.alike(kind.signature(), ref)
        reg = self._need_reg()
        ref = self._loaded.get(group)
        if ref is None:
            ref = self.resolved(group, {})
        snap = reg.snapshot(group)
        return any(not undo.alike(snap.get(k), v) for k, v in ref.items())

    def reset(self, group: str) -> str | None:
        """Back to the group's default preset (or its fresh values)."""
        name = self.default_name(group)
        if name is not None:
            self.load(group, name)
            return name
        if group in self._kinds:
            return None
        self._need_reg()
        undo.push(f"reset {group}", load=True)        # the other branch pushes in `load`
        self.restore(self.resolved(group, {}))
        self._landed(group, None, None)
        return None

    # ---- watching: an editor save shows up in the running app ----

    def _scan(self) -> dict[Path, float]:
        out: dict[Path, float] = {}
        for root in self._roots():
            if not root.is_dir():
                continue
            for d in root.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    # the presets every folder down (plan 48), as `_files` lists them
                    for f in self._tree(d)[0] if d.name == PRESETS else d.glob("*.json"):
                        try:
                            out[f] = f.stat().st_mtime
                        except OSError:
                            pass
        return out

    def _sync(self, *paths: Path) -> None:
        """Our own writes are not edits: bring the mtime table up to date."""
        for p in paths:
            try:
                self._mtimes[p] = p.stat().st_mtime
            except OSError:
                self._mtimes.pop(p, None)
            self._docs.pop(p, None)
        self.__dict__.get("_walks", {}).clear()     # our own write: walk again
        self._defaults.clear()

    def poll(self, now: float | None = None) -> bool:
        """Re-apply whatever is loaded from a file that changed on disk."""
        now = time.monotonic() if now is None else now
        if now < self._next:
            return False
        self._next = now + self.period
        seen = self._scan()
        changed = {p for p in seen.keys() | self._mtimes.keys()
                   if seen.get(p) != self._mtimes.get(p)}
        self._mtimes = seen
        if not changed:
            return False
        for p in changed:
            self._docs.pop(p, None)
        self._defaults.clear()
        if self.reg is None:
            return True
        hit = []
        try:
            for group in sorted(self.landed_groups()):
                name, _loaded, reapply = self.landed(group)
                if name is not None and self.path_of(group, name, loose=True) in changed:
                    if reapply is not None:            # by the road it came in
                        reapply()
                    else:
                        self.load(group, name)
                    hit.append(f"{group}/{name}")
            if self.project.path in changed:
                self.project.load(self.project.path, startup=False)
                hit.append(f"project {self.project.name}")
            self.error = ""
        except LibraryError as e:                     # a half-saved file: keep running
            self.error = f"library: {e}"
            return False
        if hit:
            self.say(f"library: {', '.join(hit)} · {time.strftime('%H:%M:%S')}")
        return True
