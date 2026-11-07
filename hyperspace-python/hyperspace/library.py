"""The loadable patch & project library — the Ableton model over the registry.

Two kinds of file, both plain JSON you can open in a text editor:

  module preset   one registry *group* (view, camera, band…) — since
                  plan 50 a patch of one group, ``<root>/patches/<group>/``,
                  ``{"schema": "hyperspace.patch/2", "name", "group",
                  "values": {id: base}}`` (a ``hyperspace.preset/1`` from
                  before is read through `patches.forward`), produced by ``Registry.snapshot
                  (group)`` and applied with ``Registry.restore``. The
                  analyzer's loadable patches also carry ``layout`` (see the
                  contract in docs/plans/07-overhaul.md): restore hands the
                  layout to a hook registered with ``on_layout`` *before*
                  the values, so a loadable patch can rebuild its params first,
                  and a save asks the group's ``extra`` hook for it. The
                  analyzer's *scenes* are their own data, shipped with the
                  code (hyperspace/scenes/band/, control.py) — a band
                  loadable patch in the library is the user's own, and a strip
                  load tells the scene combo through ``on_load``.
  project         the show — ``{"schema": "hyperspace.project/3",
                  "name", "note", "startup": <loadable patch name>, "bank": [8–24
                  × <loadable patch name> | null], "session": <meta controller snapshot>,
                  "modules": {group: name | {"name", "values", …}}}``, in
                  a ``*.hyp.json`` file (params.PARTS is the split; plan
                  13 §2.2). ``session`` lands on a project load and a
                  loadable patch never touches it; ``modules`` names the meta controller
                  groups' module presets (the band strip's scene and
                  layout). The **bank** is twenty-four pointers to loadable patch
                  files (``SLOTS``; loadable.py) — the desk's pads: the
                  APC40's clip rows 1, 4 and 5 load one each
                  (``Project.load_slot``), F1–F8 the first eight
                  (``F_KEYS``), ⇧F1–F8 save the live state *as* it
                  (``save_slot``); ``startup`` is the loadable patch Home brings
                  up (``Project.home``) and a launch opens with, kept in
                  the file, set by nothing on the panel since 2026-10-28.
                  The file holds the bank only as far as its last filled
                  slot, never fewer than eight entries (``bank_doc``, plan
                  19 WP1), and the first write that makes a file's bank
                  longer keeps the eight-slot file beside it first
                  (``<file>.bak-v2-bank8``, ``Project.write``). A module
                  the project names by a loadable patch that carries a ``layout``
                  gets that layout back on load, the same road a strip
                  load takes. A schema-1 project is refused (no old-schema
                  support, 2026-10-25). Plan 44 D3 (``/3``): the show
                  is the meta controller, the pads and ``startup`` — the
                  bus cuts (plan 36 T1's ``rig``) and the hands' and
                  clouds' looks (``ghost.*`` but ``ghost.mirror``,
                  ``cloud.*``) are each loadable patch's now. A ``/2`` show is
                  read as its ``/3`` (`show_without_look`): what it held
                  of the look is handed to every loadable patch before ``/10``
                  a load reads while it is open (``Project.old_look``,
                  ``old_cuts``), and its first write keeps the ``/2``
                  beside it (``<file>.bak-v2-look``).

A third kind of document is *not* the library's own format but goes
through the same doors: a **document kind** registered with ``kind()``
— the loadable patches, ``hyperspace.preset/2`` (``/3`` since plan 31, written
only when needed: a build that takes /2 alone refuses one, `read`)
under ``presets/``, which loadable.py's ``LoadedPatch`` loads and writes (the
one kind since plan 13 WP5 made the routing loadable patches loadable patches). For such a group the
library does the file half — list, load / save as / delete / rename, the
dirty dot, the watch — and the kind's hooks do the document half:
``load(doc, path)`` applies it, ``document(name)`` is what a save
writes, ``signature()`` is what ``is_dirty`` compares. One strip
(ui_loadable.py) then serves every group.

Library layout — **one tier** (2026-10-28): every loadable patch is the user's,
listed, loaded, renamed and deleted alike. Nothing ships in the wheel,
nothing is "factory", nothing is hidden; a fresh library is empty, and
the app starts on a blank loadable patch in an unsaved show.

  $HYPERSPACE_HOME/<group>/<slug>.json       module presets (default ~/Hyperspace,
                                 or the [library] path, plan 25)
  $HYPERSPACE_HOME/presets/[<folder>/…/]<slug>.json
                                 loadable patches, in folders if the owner made
                                 any (plan 48): listed every folder down,
                                 less hidden ones, by folder-qualified name
                                 (``party/TRIP``; ``_index``, `path_slug`)
  $HYPERSPACE_HOME/patches/<slug>.json       patches (plan 40)
  $HYPERSPACE_HOME/projects/<slug>.hyp.json  shows
  $HYPERSPACE_HOME/config.toml, bindings.json (a midi_map.json is only
                                 migrated in and read once, routing.py)
  $HYPERSPACE_HOME/bindings/      the old routing presets: made loadable patches
                                 once (plan 13 WP5) and never read again,
                                 so no group (LEGACY_DIRS)
  <machine>/trash/<group>/[<folder>/]<slug>.<date>-<time>.json
                                 (this Mac's home, never the shared library:
                                 plan 48; a ``<library>/trash`` from before
                                 is listed, restorable, never emptied)
                                 a loadable patch file as it was before a save
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
*default* loadable patch (DEFAULT_NAMES, else one called "default", else the
values the objects were constructed with); a whole loadable patch (loadable.py)
fills them from the values the objects were constructed with alone
(`_fresh_of`, plan 44 D3 — never a ``default.json``), so a loadable patch is the
same state whatever it lands on; ids the registry doesn't know are reported in ``warning`` and
returned, never fatal. ``is_dirty(group)`` says whether the group's bases
have moved off what the loaded (or default) loadable patch would produce.

The tree is watched like source: ``poll()`` (hotreload.py calls it) picks
up an edited file and re-applies the loadable patch or project that is loaded
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
from .graph import BusCuts
from .graphmigrate import CAMERA_NODES, EYE_IDS, is_look_id, renamed_layout, retired
from .groupwords import group_word
from .palettecompat import palette_slice
from .params import (
    F_KEYS,
    PATCH_GROUPS,
    SHARED_META_GROUPS,
    UNITS,
    UNITS_KEY,
    Registry,
    fx_files,
    in_group,
    is_instance_id,
    pan_world,
    retaper_depths,
)
from .pointer import Through

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
# `session`, which the loadable patches hold since `/9` (`Project.old_eye`) —
# <file>.bak-v2-eye
EYE_BACKUP = "2-eye"
# LOOK_BACKUP (plan 44 D3): the copy `Project.write` makes before the first
# write of a `/2` show as `/3` — which drops its bus cuts (`rig`) and the
# hands' and clouds' looks from its `session`, each loadable patch's since `/10` —
# <file>.bak-v2-look
LOOK_BACKUP = "2-look"
LOADABLE = "presets"       # the loadable patches' group, a document kind (loadable.py)
# (plan 24 C3's desk templates, `<root>/desk/`, are retired — plan 44 D3,
# the owner, 2026-11-03: neither library held one)
# <root>/patches/<slug>.json (plan 40 P1): the patches — a group of nodes
# and its boundary, saved once, spawned anywhere (patches.py). A document
# kind of the library's own (`Library.__init__`), so the folder lists,
# renames and goes to the trash like the loadable patches'; but a patch is never
# loaded through the group's door — it is spawned (`patches.spawn`) — so
# the kind's `load` refuses, and its `document` and `signature` are never
# asked. Read through `read_patch` (the schema and `patches.check`),
# written through `save_patch`.
# Plan 50 (one format): a module preset is a **patch of one param group**,
# ``hyperspace.patch/2`` with a ``group`` key, under
# ``<root>/patches/<group>/<slug>.json`` (`group_dir`) — never listed among
# the spawnable patches (`_files` reads ``patches/`` one level), opened from
# its group's strip (`load`: a spawn that replaces the group's values)
PATCHES = "patches"
PATCH_SCHEMA = patchdoc.SCHEMA          # "hyperspace.patch/2" (plan 50)
PATCH_SPAWNED = "a patch is spawned, not loaded"
# what `read_patch` says of a patch of one group asked for by name
GROUP_PATCH_WORDS = "{name} is a patch of the {group} group: open it from that group's strip"
# what `read` says of a file in a group's folder that is no patch of that group
NOT_GROUP_WORDS = "{file} is {what}, not a patch of the {group} group"
# the groups `rename` serves: the loadable patches and the patches (a module preset
# is saved under another name instead)
RENAMABLE = (LOADABLE, PATCHES)
# plan 44 D6: a playlist (playlist.py), a kind of its own in ``<root>/playlists/``,
# read and written here and never landed: it names loadable patches, and holds no look
PLAYLISTS = "playlists"
PLAYLIST_KIND, PLAYLIST_VERSION = "hyperspace.playlist", 1
PLAYLIST_LANDED = "a playlist is played, not loaded"
# folders in a library root that are no group: the routing loadable patches' old
# folder, kept as it was by plan 13's migration and never read again
LEGACY_DIRS = ("bindings",)
# <home>/trash/<group>/: a loadable patch file as it was, copied there before a
# save overwrites it or a delete removes it (`to_trash`, plan 15 WP1).
# No group and never watched. Plan 19 WP4 lists it (`Library.trash`), puts a
# file back (`restore_trash`, never over a file) and empties it
# (`empty_trash`, the one delete in the app that keeps no copy)
TRASH = "trash"
# the trash's file names: <stem>.<YYYYMMDD-HHMMSS>[-n]<suffix> (`to_trash`)
_TRASHED = re.compile(r"(?P<stem>.+)\.(?P<stamp>\d{8}-\d{6})(?:-(?P<n>\d+))?(?P<suffix>\.[^.]+)")
HOME_ENV = "HYPERSPACE_HOME"
DEFAULT_HOME = Path("~/Hyperspace")

LOADABLE_SCHEMA = "hyperspace.preset/2" # a preset: the performance (loadable.py)
PROJECT_SCHEMA = "hyperspace.project/3"   # plan 44 D3: the meta controller, the pads, startup
PROJECT_V2 = "hyperspace.project/2"        # read as its /3 (`show_without_look`), once
PROJECT_V1 = "hyperspace.project/1"        # refused: no old-schema support (2026-10-25)
PROJECT_SUFFIX = ".hyp.json"
PROJECTS = "projects"
LAST_SHOW = "last_show"             # <home>/last_show: the show opened last
UNTITLED = "untitled"
# the tail of save-as's note on a full bank (`Project.save_new`)
BANK_FULL = "the bank is full: it is in the preset list"
# what `Project.home` says when the show names no startup loadable patch (plan 15 WP2)
HOME_UNSET = "home: this show names no startup preset"
# plan 28 N2: where the GRAPH page's nodes sit, ``{"<node id>": [x, y]}`` —
# a show's own key for the meta controller's nodes (devices, the analyzer, the LFOs,
# the outputs), a loadable patch's (loadable.LAYOUT_KEY) for the look's. No key: every
# node is laid out automatically, and nothing is dirty
LAYOUT = "layout"
# plan 36 T1: a `/2` show's own wires (`graph.BusCuts`) — the bus cuts,
# each loadable patch's since plan 44 D3 (loadable.BUS_KEY): read out of an old show
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

# the loadable patch a group resets to; any other group uses one named "default"
# if it has one, else the values its objects were built with
DEFAULT_NAMES = {"band": "Balanced"}

# the groups whose module presets are retired outright (plan 40 T5, D6:
# "It is not a useful representation of shaders anymore"): no strip, no
# entry in `groups()`, no default loadable patch — `defaults` is the fresh values
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
    """A loadable patch's file key from its folder-qualified name (plan 48 row
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
    """The one comparison key of a loadable patch name (plan 48): `path_slug`,
    lowered — folder segments stripped and case-folded, the leaf slugged
    (``Party /TRIP 2`` → ``party/trip-2``), as APFS would find the file.
    None for a name that could name no file (``../x``)."""
    try:
        return path_slug(name).lower()
    except LibraryError:
        return None


def fold_folder(folder: str) -> str | None:
    """`fold` of a folder alone: ``""`` for the top, None for one that
    could hold no loadable patch."""
    if not folder:
        return ""
    key = fold(f"{folder}/x")
    return None if key is None else key[:-2]


def harmless(name: str) -> str:
    """A loadable patch's own ``name`` as the list shows it (plan 48 review): a
    ``/`` in a listed name always means a folder, so a file whose own name
    holds one (``AC/DC``, from before folders) is listed with it made a
    ``" - "`` (``AC - DC``) — no reader splits it, no writer makes a
    folder of it; a save writes the shown name back into the file."""
    return name.replace("/", " - ")


def next_name(base: str | None, taken: set[str], *, key=None) -> str:
    """A name for a new loadable patch grown from `base`, the loaded patch's name
    (plan 15 WP4, fork 16): the first ``"<stem> <n>"`` whose slug is not in
    `taken`, a set of slugs. A base that ends in whitespace and a number
    after a non-empty stem counts on from that number (``TRIP 2`` →
    ``TRIP 3``); any other is its own stem and counting starts at 2
    (``TRIP`` → ``TRIP 2``, ``2001`` → ``2001 2``). With no base the stem
    is ``PRESET`` and counting starts at 1. `key` is what a candidate is
    compared by (`slug`; for a loadable patch in a folder the caller's
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
        # files only (review of #349: a folder named `mix.json` is no loadable patch)
        yield h, sorted(p for p in h.glob(pattern) if p.is_file())


# how long a kept walk of the loadable patches is trusted without a look at the
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
    """A show file's document without what plan 43 C2 made the loadable patches' —
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
    """The ids of a `/2` show's session that are a loadable patch's since plan 44
    D3: the hands' and the clouds' looks (`graphmigrate.is_look_id`, the
    one set `ten` hands on — `ghost.mirror` stays the room's). Any other id
    a show held stays the show's (the eye is plan 43 C2's own road)."""
    return [k for k in session if is_look_id(k)]


def show_look(doc: Any) -> tuple[dict[str, Any], BusCuts]:
    """What a `/2` show held of the look (plan 44 D3): the hands' and the
    clouds' values in its `session` (`_look_ids`) and its bus cuts (`rig`,
    `graph.BusCuts`) — ({}, no cut) for neither, and for any `/3`. The one
    reader: `Project._take`, `kept_look`, `headless.show_seed` and the
    migration tool all ask it."""
    if not isinstance(doc, dict) or doc.get("schema") not in (PROJECT_V2, None):
        return {}, BusCuts()
    session = doc.get("session")
    session = session if isinstance(session, dict) else {}
    return ({k: session[k] for k in _look_ids(session)}, BusCuts.read(doc.get(RIG)))


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
    cloud client take it for a loadable patch — then `os.replace`s the file, so a
    synced folder never carries a half-written loadable patch."""
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
    """Copy `path` — a loadable patch file about to be overwritten or deleted — to
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


def _move_file(src: Path, dst: Path) -> None:
    """Move `src` to `dst` (a path that is not there), its bytes as they
    were and never over a file (plan 48 stage 2): a hard link then an
    unlink; where the disk makes no links (a cloud mount), an exclusive
    copy of the bytes, then the unlink. LibraryError, and `dst` gone
    again, when either fails."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except FileExistsError as e:
        raise LibraryError(f"{dst.name}: already there — nothing moved") from e
    except OSError:
        try:
            data = src.read_bytes()
            with open(dst, "xb") as f:
                f.write(data)
            shutil.copystat(src, dst)
        except FileExistsError as e:
            raise LibraryError(f"{dst.name}: already there — nothing moved") from e
        except OSError as e:
            dst.unlink(missing_ok=True)
            raise LibraryError(f"{src.name}: not moved ({e})") from e
    try:
        src.unlink()
    except OSError as e:
        dst.unlink(missing_ok=True)
        raise LibraryError(f"{src.name}: not moved ({e})") from e


@dataclass(frozen=True)
class Trashed:
    """A file in the trash, as its view lists it (plan 19 WP4)."""

    path: Path          # <machine>/trash/presets/party/trip-3.20261004-011203.json
    group: str          # its group's folder: "presets", "fx", "projects", …
    name: str           # the name inside the file, else its stem; folder-qualified
                        # for a loadable patch from a folder ("party/TRIP", plan 48)
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

# (the shows' ladder only, since plan 50: a loadable patch's is `graphmigrate.forward`,
# a module preset's and a patch's `patches.forward` — review fix 8)
MIGRATIONS: dict[tuple[str, int], Any] = {
    # plan 44 D3: a /2 show less what each loadable patch holds now (read out first:
    # `Project._take`, `show_look`)
    ("hyperspace.project", 2): lambda doc: show_without_look(doc) or dict(doc),
}
# no project 1 → 2 step: a schema-1 show (an inline theme bank) is refused
# (`Project._take`) — no old-schema support since 2026-10-25
CURRENT = {"hyperspace.project": 3}


def migrate_doc(doc: dict, kind: str) -> dict:
    """Lift a file to the current version of its kind, or refuse it — a
    show (``hyperspace.project``), the one kind it serves since plan 50."""
    schema = doc.get("schema")
    if kind not in CURRENT:
        raise LibraryError(f"no ladder for {kind} here")
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
    tree and goes through its doors (the loadable patches, loadable.py). `schema` is
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
    `read` checks a file as it does a loadable patch's, and the doors that refuse —
    a patch is spawned (`patches.spawn`), never loaded, and what a save
    writes is `save_patch`'s document, never the live state's."""
    # (plan 50: every version the one ladder reads, `patches.forward`)
    return DocKind(patchdoc.KIND, patchdoc.READS, _patch_spawned, _patch_spawned,
                   _patch_spawned)


def _playlist_landed(*_args) -> Any:
    raise LibraryError(PLAYLIST_LANDED)


def _playlist_kind() -> DocKind:
    """The playlists' document kind (plan 44 D6), as `_patch_kind`: its schema and
    versions, so `read` checks the file, and the doors that refuse. `playlist.Playing`
    reads one with `read`; `save_playlist` writes one; nothing lands one."""
    return DocKind(PLAYLIST_KIND, (PLAYLIST_VERSION,), _playlist_landed, _playlist_landed,
                   _playlist_landed)


def group_folder(group: str, kinds=()) -> str:
    """The folder a group's files sit in, relative to a library root (plan
    50) — the one table, `Library.group_dir`'s and the test corpus's
    (tests/conftest.py `seed`, tools/desk_coverage.py): the loadable patches, the
    patches, the shows and any document kind (`kinds`) in their own
    ``<group>``; every other group's — a module group's patches of one
    group — in ``patches/<group>``."""
    if group in (LOADABLE, PATCHES, PROJECTS) or group in kinds:
        return group
    return f"{PATCHES}/{group}"


def forward_group(doc: dict, where: str = "") -> dict:
    """A patch of one param group in today's words (plan 50): a module
    loadable patch (``hyperspace.preset/1``) or a ``patch/1`` / ``/2`` through the
    one ladder (`patches.forward`) — LibraryError, in words, for a file it
    cannot read (another kind, a newer build's)."""
    try:
        return patchdoc.forward(doc)
    except ValueError as e:
        raise LibraryError(f"{where}{': ' if where else ''}{e}") from e


def scene_doc(path: Path) -> dict:
    """A band scene's file (hyperspace/scenes/band/, control.py) in today's
    words — a patch of the band group, through the one ladder
    (`forward_group`; the files are code data, read without a Library)."""
    if not path.is_file():
        raise LibraryError(f"no scene file {path.name}")
    return forward_group(_read_json(path), path.name)


def _module_values(group: str, doc: dict) -> dict[str, Any]:
    """A module preset's values as they land: a camera module from before
    plan 26 A2 (no `units` marker) stored its pan in logical px, read in
    world units here (`params.pan_world`), as a whole loadable patch's is in
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
    """The open show — the meta controller (plan 13 §2.2): its file (None until
    saved), the meta controller values, the shared meta groups' module labels, and the
    loadable patch bank, the desk's pads.

    ``session`` / ``modules`` / ``bank`` / ``startup`` are what the *file*
    holds; ``save()`` refreshes ``session`` and ``modules`` from the live
    state, ``write()`` puts the document back on disk as it is — what a
    pad save uses, so the desk persists the bank without turning the
    whole project into a snapshot of the moment.

    ``session`` is the meta controller part of the registry (params.PARTS: tempo,
    hands, the analyzer, output), landed on a project load and never
    touched by a loadable patch. The **bank** is ``SLOTS`` loadable patch names (or None):
    a slot is a pointer to a loadable patch file (loadable.py), loaded through
    ``Library.loaded_patch`` — the APC40's clip rows 1, 4 and 5 load one each,
    F<k+1> the first ``F_KEYS``, ⇧F<k+1> saves the live state as that
    loadable patch (``slot_key`` names a slot). A show file's shorter bank is
    padded in memory and the file is left as it is (``_take``,
    ``bank_doc``). ``startup`` is the loadable patch a launch and Home bring up
    (D11); since 2026-10-28 nothing on the panel sets it — the file keeps
    what it says.
    """

    def __init__(self, lib: Library):
        self.lib = lib
        self.name = UNTITLED
        self.note = ""
        self.path: Path | None = None
        self.session: dict[str, Any] = {}     # the meta controller part
        self.modules: dict[str, Any] = {}     # shared meta groups' module labels
        self.bank: list[str | None] = [None] * SLOTS
        self.startup: str | None = None
        self.active = -1          # the slot last loaded, -1 until one is
        self.bank_error = ""
        self._saved: tuple = ([None] * SLOTS, None)   # bank and startup as on disk
        # plan 28 N2: the GRAPH page's positions of the meta controller's nodes, and
        # those as on disk (`is_dirty`)
        self.layout: dict[str, list[float]] = {}
        self._saved_layout: dict[str, list[float]] = {}
        # plan 44 D3: what an old show (`/2`) held of the look — the hands'
        # and clouds' values in its session, its bus cuts — read out by
        # `_take` and handed to every loadable patch before `/10` a load reads while
        # this show is open (`graphmigrate.ten`); never written back
        self.old_look: dict[str, Any] = {}
        self.old_cuts = BusCuts()
        # plan 43 C2: what an old show (before the eye was the loadable patch's) kept
        # of the camera — the eye in its `session`, the camera node's GRAPH
        # position in its `layout` — read out of the file by `_take` and
        # handed to every loadable patch before `/9` a load reads while this show is
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
        # plan 43 C2: the eye is the loadable patch's — an old show's is read out of
        # its session (as the spring's old ids are read as today's), held for
        # the loadable patches before `/9` (`old_eye`), and never landed or written
        # as the show's
        self.old_eye = {pid: self.session.pop(pid) for pid in EYE_IDS if pid in self.session}
        self.modules = dict(doc.get("modules") or {})
        bank = [str(s) if isinstance(s, str) and s else None
                for s in list(doc.get("bank") or [])[:SLOTS]]
        self.bank = bank + [None] * (SLOTS - len(bank))
        self.startup = str(doc["startup"]) if doc.get("startup") else None
        self.active = -1
        self._saved = (list(self.bank), self.startup)
        self.layout, _ = read_layout(doc.get(LAYOUT))
        # (plan 43 C2: and the camera node's position, the look's now — the
        # loadable patches before `/9` take it, `old_eye`'s road)
        # (under today's id or the old canvas's, `CAMERA_NODES` — `read_layout`
        # renames the old one, but neither may stay the show's)
        found = [self.layout.pop(k) for k in CAMERA_NODES if k in self.layout]
        self.camera_at = list(found[0]) if found else None
        # (review 2.2: a show whose first write on this build — the bank's
        # autosave, say — already moved its eye into `<file>.bak-v2-eye`
        # still hands that eye to the loadable patches before `/9`, until the tool
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
        name, note, path, stem, meta controller, modules, bank, startup and the
        bank and startup as on disk — copies, so a later edit of the live
        show never reaches a mark; then the GRAPH page's positions of the
        meta controller's nodes, live and as on disk; then what an old show kept of the
        camera (plan 43 C2) and of the look (plan 44 D3; the bus cuts are
        the loadable patch's: `Marks`)."""
        return (self.name, self.note, self.path, getattr(self, "_stem", None),
                copy.deepcopy(self.session), copy.deepcopy(self.modules), list(self.bank),
                self.startup, (list(self._saved[0]), self._saved[1]),
                # plan 28 N2: the GRAPH page's positions of the meta controller's nodes
                copy.deepcopy(getattr(self, "layout", {})),
                copy.deepcopy(getattr(self, "_saved_layout", {})),
                # plan 43 C2: what an old show kept of the camera, for its loadable patches
                dict(getattr(self, "old_eye", {})), getattr(self, "camera_at", None),
                # plan 44 D3: and of the look
                dict(getattr(self, "old_look", {})), getattr(self, "old_cuts", BusCuts()))

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
        if len(mark) > self.MARK_EYE:      # plan 43 C2: an old show's eye, for its loadable patches
            self.old_eye, self.camera_at = dict(mark[self.MARK_EYE]), mark[self.MARK_EYE + 1]
        if len(mark) > self.MARK_LOOK:     # plan 44 D3: and its look, for its loadable patches
            self.old_look, self.old_cuts = dict(mark[self.MARK_LOOK]), mark[self.MARK_LOOK + 1]
        self.session, self.modules = copy.deepcopy(session), copy.deepcopy(modules)
        self.bank = list(bank)
        self._saved = (list(saved[0]), saved[1])

    def ident(self) -> tuple:
        """Which show this is: its name, file and stem. (The bank and startup may
        differ: they are written to the show's file the moment they change.)"""
        return (self.name, self.path, getattr(self, "_stem", None))

    @staticmethod
    def ident_of(mark: tuple) -> tuple:
        """`ident` as of a `mark`."""
        return (mark[0], mark[2], mark[3])

    def _apply(self) -> list[str]:
        """Push the document's meta controller into the registry; returns unknown
        ids. A module's `layout` lands first (a project saved on eight
        bands comes back with eight, audit L8), then the meta controller values
        — the live state as saved, edits included — and each module is
        recorded as the group's current loadable patch, the reference its dirty
        dot compares against, the way a strip load records it. Only a
        shared meta group's module counts: a patch group's label is the
        loadable patch's (loadable.py)."""
        lib = self.lib
        # a document kind is never the project's (the loaded patch, the
        # only kind since plan 13 WP5): what it has landed survives a project
        # load, and so do the patch groups' references — the loaded
        # loadable patch's, which their dirty dots compare against (plan 14 WP4)
        kept = {g: lib.landed(g) for g in (*lib._kinds, *PATCH_GROUPS)}
        lib._current.clear()
        lib._loaded.clear()
        lib._adopted.clear()
        for group, mark in kept.items():
            if mark[0] is not None or mark[1] is not None:
                lib.reland(group, mark)
        docs: list[tuple[str, str, dict | None]] = []
        for group, ref in self.modules.items():
            if group in lib._kinds or group not in SHARED_META_GROUPS:
                continue                              # a loadable patch's, or a document kind's
            if isinstance(ref, dict):                 # inline copy of a loadable patch
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
        # an old show's extra hands node settings (`ghost.2.*`, plan 26 A4; the
        # look goes to the loadable patches, `old_look`, and `ghost.2.mirror`,
        # no param since LY1, is read by nothing): held back, not unknown
        missing = [pid for pid in missing if not is_instance_id(pid)]
        # ids the file lacks (a param added since) take the state this load
        # left, so an untouched project is not dirty the moment it opens
        for pid, v in (lib.reg.snapshot(part="shared_meta") if lib.reg is not None else {}).items():
            self.session.setdefault(pid, v)
        for group, name, doc in docs:
            vals = (lib.reg.snapshot(group) if doc is None
                    else lib.resolved(group, _module_values(group, doc)))
            lib._landed(group, name, vals)
            hook = lib._load_hooks.get(group)
            if hook is not None:
                hook(name)
        # a shared meta group the show names no module preset for: clean as the
        # show left it — the section's dot compares against the show, not fresh
        # defaults (plan 14 WP4)
        if lib.reg is not None:
            named = {g for g, _n, _d in docs}
            for group in SHARED_META_GROUPS:
                if group not in named and group not in lib._kinds:
                    lib._landed(group, None, lib.reg.snapshot(group))
        # the bank lights the slot naming the loadable patch still loaded, if any
        self.follow()
        return missing

    # ---- the bank: SLOTS pointers to loadable patch files ----

    def follow(self) -> None:
        """`active` follows the loaded patch — the one place (plan 19
        WP1): kept where it is when that slot still names it, else the
        first slot that names it, else −1; −1 when nothing is loaded."""
        lib, cur = self.lib, self.lib.current(LOADABLE)
        if cur is None:                               # nothing loaded: no slot is lit
            self.active = -1
            return
        # a slot names it when it is the same string or reads (as a pad
        # loads it, loosely) the same file: `Ac/Dc`, `Party/TRIP` (plan 48
        # review); one look at the library for every slot
        snap = lib._lookup(LOADABLE) if hasattr(lib, "_lookup") else None
        target = None if snap is None else lib._resolve(LOADABLE, cur, snap, loose=True)

        def names(n: str | None) -> bool:
            return n is not None and (n == cur or (
                target is not None and lib._resolve(LOADABLE, n, snap, loose=True) == target))

        if not (0 <= self.active < len(self.bank) and names(self.bank[self.active])):
            self.active = next((k for k, n in enumerate(self.bank) if names(n)), -1)

    def _loader(self):
        return getattr(self.lib, "loaded_patch", None)

    @property
    def active(self) -> int:
        """The slot lit (`load_slot`, `follow`): that of the loadable patch loaded on
        the deck this view is of, so one deck's load moves no other's light
        (plan 44 D5a, `LoadedPatch.active_slot`). No loadable patches yet: this object's."""
        slot = getattr(getattr(self.lib, "loaded_patch", None), "active_slot", None)
        return slot if slot is not None else self.__dict__.get("active", -1)

    @active.setter
    def active(self, k: int) -> None:
        pre = getattr(self.lib, "loaded_patch", None)
        if getattr(pre, "active_slot", None) is not None:
            pre.active_slot = k
        else:
            self.__dict__["active"] = k

    @property
    def lit(self) -> int:
        """The slot a bank pad shows lit: `active`. `DeckProject`'s is the deck
        off air's, the deck a press would load."""
        return self.active

    def load_slot(self, k: int) -> bool | None:
        """Slot k (F<k+1> for the first eight): the loadable patch it names,
        through the one loader. An empty slot, or a name with no file,
        loads nothing and says so. `active` is the slot that was asked
        for, so a loadable patch on two slots lights the one pressed. True when
        it loaded."""
        if not 0 <= k < len(self.bank):
            return None
        lib, name, key = self.lib, self.bank[k], slot_key(k)
        loaded_patch = self._loader()
        if name is None:
            lib.say(warning=f"{key}: an empty slot — hold its pad" + (
                f" (or ⇧{key})" if k < F_KEYS else "") + " to save the live state into it")
            return None
        if loaded_patch is None or lib.path_of(LOADABLE, name, loose=True) is None:
            lib.say(warning=f"{key}: no preset {name!r}")
            return None
        try:
            loaded_patch.load(name)
        except LibraryError as e:                     # a bad file: said, never fatal
            lib.error = f"library: {e}"
            return None
        self.active = k
        return True

    def save_slot(self, k: int) -> None:
        """⇧F<k+1>: the live state as the loadable patch slot k names — a new one,
        ``PRESET <k+1>``, for an empty slot — written over its file (the
        old text kept in the trash); the bank and the project file with
        it. A show file that cannot take
        the slot (`write`) leaves the bank as the file has it: the loadable patch
        is saved and in the list, and the footer says why."""
        loaded_patch = self._loader()
        if not 0 <= k < len(self.bank) or self.lib.reg is None:
            return
        if loaded_patch is None:
            self.bank_error = "presets: no preset loader"
            return
        was = self.bank[k]
        name = was or self._fresh_name(k)
        try:
            loaded_patch.save_as(name)
        except LibraryError as e:                     # a full disk must not stop the show
            self.bank_error = f"presets: {e}"
            return
        self.bank[k] = name
        self.active = k
        try:
            self.write()
        except (LibraryError, OSError) as e:
            self.bank[k] = was
            self.follow()                             # the light goes where the loadable patch is
            self._refused(f"saved {name} — {slot_key(k)} not changed", e)
            return
        self.bank_error = ""

    def _fresh_name(self, k: int) -> str:
        """``PRESET <k+1>``, made unique against every loadable patch there is."""
        taken = ({slug(n) for n in self.lib.list(LOADABLE)}
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
        state as a **new** loadable patch in slot k — `save_new`'s loadable patch, its name
        (`next_name`, from the loaded one: TRIP → TRIP 2) and its show
        write, in slot k rather than the next empty one. **A filled slot
        takes the new loadable patch too**: the slot points at it, and the loadable patch
        it named keeps its file, untouched, and stays in the list, unpadded
        — exactly as "free this pad (keeps the preset)" leaves it. Nothing
        is overwritten and nothing goes to the trash (owner, 2026-10-09 and
        2026-10-14). True when slot k now names the new loadable patch; False for a
        slot the bank does not have, a save that failed, or a show file
        that could not take the slot (the loadable patch is then saved and in the
        list, slot k is as it was, and `bank_error` and the footer say why)."""
        if not 0 <= k < len(self.bank):
            return False
        return self._save_new(k)

    def save_empty(self, k: int) -> bool:
        """#158's hold (2026-10-09): an **empty** bank pad held midi.HOLD_S
        saves into its slot (`save_into`); a filled pad held only loads —
        nothing happens here and False is returned, so a long press that
        loaded a loadable patch blinks nothing (`Param.held` on `preset.select`).
        Saving onto a filled slot is the two-handed save's alone."""
        if not 0 <= k < len(self.bank) or self.bank[k] is not None:
            return False
        return self.save_into(k)

    def save_new(self) -> bool:
        """The live state as a **new** loadable patch, named from the loaded one
        (`next_name`), into the next empty slot (`preset.save_new`, plan 15
        WP4: learnable onto any button; the desk itself saves by holding an
        empty pad, `save_into`).
        It never overwrites: the name's slug is free among the loadable patch
        folder's file stems, every listed name (`_taken`) and the bank's
        names. The new loadable patch becomes the loaded one with a
        clean dot, as the panel's "as…" does, so a second save counts on.
        A full bank saves to the list and says so. The show is written at
        once; no undo step — nothing live changes. True when a loadable patch was
        saved; False when none was (the reason is in `bank_error`), which
        the desk reads as "nothing to confirm" (midi.py blinks no light)."""
        return self._save_new(None)

    def _save_new(self, at: int | None) -> bool:
        """`save_new` into slot `at`, or the next empty one when None."""
        lib, loaded_patch = self.lib, self._loader()
        if lib.reg is None:
            return False
        if loaded_patch is None:
            self.bank_error = "presets: no preset loader"
            return False
        # stems as slugs: on a filesystem that folds case, `Trip-2.json`
        # is the file a save of "TRIP 2" would write over. Plan 48 row 587:
        # the new loadable patch lands beside the loaded one — in its folder, the
        # library's root for a top-level one or none loaded
        taken = lib._taken(LOADABLE) | {lib._fold(LOADABLE, n) for n in self.bank if n}
        folder, base = lib.folder_of(LOADABLE, lib.current(LOADABLE))
        leaf = next_name(base, taken, key=lambda n: lib._fold(
            LOADABLE, f"{folder}/{n}" if folder else n))
        name = f"{folder}/{leaf}" if folder else leaf
        try:
            loaded_patch.save_as(name)
        except (LibraryError, OSError) as e:          # a full disk must not stop the show
            self.bank_error = f"presets: {e}"
            return False
        self.bank_error = ""
        k = self.next_empty() if at is None else at
        if k is None:
            lib.say(warning=f"saved {name} — {BANK_FULL}")
            return True
        was = self.bank[k]          # a filled slot (`save_into`): its loadable patch stays listed
        self.bank[k] = name
        self.active = k
        try:
            self.write()
        except (LibraryError, OSError) as e:
            # the loadable patch is saved and loaded, but the show could not take
            # it: the bank stays as the show's file has it, and it is said
            self.bank[k] = was
            self.active = -1
            self.bank_error = f"presets: {e}"
            lib.say(warning=f"saved {name} — the show could not be written: it is in "
                            f"the preset list ({e})")
            # `save_new` saved what it was asked to (the list has it); a
            # save into slot `at` did not land there — False, so the desk
            # blinks nothing over a slot that still names the old loadable patch
            return at is None
        self._room()
        kept = f" ({was} is still in the preset list)" if was is not None else ""
        lib.say(f"saved {name} → {slot_key(k)}{kept}")
        return True

    def put_slot(self, k: int, name: str) -> None:
        """Point slot k at a preset: the file must exist, else a warning and
        nothing changes. The show is written at once; no loadable patch file is
        written or deleted; no undo step."""
        if not 0 <= k < len(self.bank):
            return
        if self.lib.path_of(LOADABLE, name, loose=True) is None:
            self.lib.say(warning=f"{slot_key(k)}: no preset {name!r}")
            return
        self._set_slot(k, name, f"{slot_key(k)}: {name}")

    def clear_slot(self, k: int) -> None:
        """Empty slot k: the show is written at once; the loadable patch's file
        stays in the list."""
        if 0 <= k < len(self.bank) and self.bank[k] is not None:
            self._set_slot(k, None, f"{slot_key(k)}: cleared — {self.bank[k]} is still in "
                                    "the preset list")

    def _set_slot(self, k: int, name: str | None, said: str) -> None:
        """One slot's pointer, written into the show now; `active` follows
        the loaded patch to a slot that names it, or to none (`follow`).
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
        `preset.prev`). `preset.list.*` walk the list instead (`walk`)."""
        filled = [k for k, s in enumerate(self.bank) if s is not None]
        if not filled:
            return
        if self.active in filled:
            k = filled[(filled.index(self.active) + step) % len(filled)]
        else:
            k = filled[0] if step > 0 else filled[-1]
        self.load_slot(k)

    def walk(self, step: int = 1) -> str | None:
        """Load the next (step 1) or previous (−1) loadable patch of the loadable patch
        list — the list the PRESETS page shows and its ◀ ▶ step
        (`Library.list`: by name, case folded), wrapping at both ends;
        from a loadable patch not in it (none loaded) the first or the last
        (`Library.next` / `prev`). The list is read from disk each step, so a loadable patch saved
        a moment ago (`save_new`, the strip's "as…") is in it. On
        `preset.list.next` / `prev`, which no factory row reaches (2026-11-04:
        Learn puts them on a control) — not the bank,
        which the desk walks (`cycle`). A load is the drop-down's pick:
        one undo step; a bad file shows on the library's error line and
        the show runs on. Returns the name loaded, or None."""
        lib = self.lib
        if self._loader() is None:
            return None
        try:
            return lib.next(LOADABLE) if step > 0 else lib.prev(LOADABLE)
        except (LibraryError, OSError) as e:
            lib.error = f"library: {e}"
            return None

    def load_startup(self) -> bool | None:
        """The project's startup loadable patch (D11), if it names one: a launch
        and a project load bring it up. A name with no file says so and
        the app keeps running on what it has. True when it loaded."""
        lib, loaded_patch, name = self.lib, self._loader(), self.startup
        if loaded_patch is None or not name:
            return None
        if lib.path_of(LOADABLE, name, loose=True) is None:
            lib.say(warning=f"startup: no preset {name!r}")
            return None
        try:
            loaded_patch.load(name)
        except LibraryError as e:
            lib.error = f"library: {e}"
            return None
        return True

    def home(self) -> bool | None:
        """Home (plan 15 WP2, decision 27): load the show's startup loadable patch
        — the `preset.home` trigger, on the Home key and the desk's
        OVERDUB. It is a load like any other (D2), and one undo step under
        its own label: the push inside `LoadedPatch.load_doc` is the same
        frame's and is ignored (undo.py). A show that names no startup
        loadable patch says so and loads nothing; so does a name with no file, in
        `load_startup`'s words (neither opens a step). True when it loaded."""
        lib, name = self.lib, self.startup
        if not name:
            lib.say(warning=HOME_UNSET)
            return None
        if lib.warning == HOME_UNSET:                 # it names one now
            lib.warning = ""
        if self._loader() is not None and lib.path_of(LOADABLE, name, loose=True) is not None:
            undo.push_on(lib.reg, f"home → {name}", load=True)
        return self.load_startup()

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
        loadable patch comes up with it unless `startup` is off (the file watch
        re-reading an edited project). A schema-1 file is refused
        (`_take`)."""
        lib = self.lib
        if isinstance(name, Path) or str(name).endswith(PROJECT_SUFFIX):
            path = Path(name)
        else:
            path = self.path_for(name)
        doc = _read_json(path)
        # the file is read, nothing replaced yet: one step on the meta controller's
        # stack for the show; the startup loadable patch it brings up is a load, a step
        # on its deck's (undo.py, plan 44 D5b)
        undo.push_meta(f"show {doc.get('name') or path.name[: -len(PROJECT_SUFFIX)]}", load=True)
        self._take(doc, path, path.name)
        missing = self._apply()
        lib.report(missing, path.name)
        lib.say(f"show: {self.name}")
        lib.remember(self.stem)
        if startup:
            self.load_startup()
        apart = mirrors_apart(self.session)
        if apart:
            lib.say(warning=f"{path.name}: {', '.join(apart)} differs from the Mirror, and "
                            "there is one Mirror now: those hands follow it. To flip one "
                            "window, use its Flip X in the OUTPUT section")
        return missing

    def new(self, name: str = UNTITLED) -> None:
        """A fresh show: default state, an empty bank, no file yet (not
        remembered until it is saved)."""
        lib = self.lib
        # one step on the meta controller's stack, and one on the deck's: a new
        # show puts every group's fresh values on both (undo.py, plan 44 D5b)
        undo.push_meta("new show", load=True)
        undo.push_on(lib.reg, "new show", load=True)
        self._take({"schema": PROJECT_SCHEMA, "name": name}, None)
        self.name = name
        lib._fresh_layouts()                          # the layout the app started with…
        lib.restore(lib._fresh_all())                 # …and every group's fresh values
        self._apply()
        lib.say(f"show: new {name}")
        self.load_startup()

    def save(self, name: str | None = None) -> Path:
        """The meta controller into the project file (as `name` if given), with the
        bank and startup as held."""
        lib = self.lib
        held = (self.name, self.path, self.session, self.modules)
        if name:
            self.name = name
            self.path = self.path_for(name)
        elif self.path is None:
            self.path = self.path_for(self.name)
        self.session = {**self._held_back(), **lib.reg.snapshot(part="shared_meta")}
        self.modules = {}
        for group, cur in lib._current.items():
            if cur is None or group in lib._kinds or group not in SHARED_META_GROUPS:
                continue                              # a loadable patch's label, or a kind's
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
        GRAPH position in its `layout` (both the loadable patches' since `/9`: this
        write drops them) keeps it first as ``<file>.bak-v2-eye``.
        And (plan 44 D3) the first write of a `/2` show — written `/3`,
        without its bus cuts and the hands' and clouds' looks, each loadable patch's
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
        """Does the live state differ from the file — the meta controller values,
        the bank or the startup loadable patch? Never saved counts as dirty."""
        reg = self.lib.reg
        if reg is None:
            return False
        return (self.path is None
                or not undo.alike(self.session, {**self._held_back(),
                                                 **reg.snapshot(part="shared_meta")})
                or (self.bank, self.startup) != self._saved
                or getattr(self, "layout", {}) != getattr(self, "_saved_layout", {}))

    def _held_back(self) -> dict:
        """The ids of node instances an old show holds and the registry lacks
        now (`ghost.2.*`, plan 26 A4; `ghost.2.mirror` always, no param since
        LY1): kept by a save and never counted as an edit. The old reader goes
        in CL1."""
        reg = self.lib.reg
        return {pid: v for pid, v in (self.session or {}).items()
                if is_instance_id(pid) and (reg is None or pid not in reg)}


def mirrors_apart(session: dict) -> list[str]:
    """The `ghost.<n>.mirror` ids an old show holds at another value than its
    `ghost.mirror`. No param since LY1, so nothing reads them and the picture
    changes: what `Project.load` says (REVIEW: a removed id reads an old file as
    it was, or reports it). Goes with the old reader, in CL1."""
    room = bool(session.get("ghost.mirror", False))
    return [pid for pid, v in session.items()
            if pid.startswith("ghost.") and pid.endswith(".mirror")
            and is_instance_id(pid) and bool(v) != room]


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


_KEPT_LOOKS: dict[tuple[str, int], tuple[dict[str, Any], BusCuts]] = {}


def kept_look(path: Path) -> tuple[dict[str, Any], BusCuts]:
    """What a show's ``.bak-v2-look`` copy kept of the look (`show_look`)
    — the oldest copy — or ({}, no cut): a `/2` show whose first write on
    this build made it `/3` still hands its old look to the loadable patches before
    `/10` (plan 44 D3), until the tool writes it into them. Remembered per
    show file and its folder's state, as `kept_eye`."""
    try:
        key = (str(path), path.parent.stat().st_mtime_ns)
    except OSError:
        return {}, BusCuts()
    hit = _KEPT_LOOKS.get(key)
    if hit is not None:
        return dict(hit[0]), hit[1]
    found: tuple[dict[str, Any], BusCuts] = ({}, BusCuts())
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

class _Landings:
    """One stack's share of what has landed in the library: the groups it answers
    for (`_mine`), read and put back. The two marks' common part."""

    def __init__(self, lib: Library):
        self.lib = lib

    def _mine(self, group: str, kinds) -> bool:
        raise NotImplementedError

    def _groups(self) -> set[str]:
        lib = self.lib
        kinds = lib._kinds
        return {g for g in lib.landed_groups() if self._mine(g, kinds)}

    def lands(self) -> dict:
        """{group: landed} — each of this stack's groups' name, reference and
        re-apply road, by reference: cheap enough to read every frame."""
        lib = self.lib
        return {g: lib.landed(g) for g in self._groups()}

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

    def _reland(self, landed: dict) -> None:
        """Every one of this stack's groups as `landed` has it: a group that had
        no landing then has none now (`Library.reland`)."""
        lib = self.lib
        for group in self._groups() - set(landed):
            lib.reland(group, (None, None, None))
        for group, was in landed.items():
            lib.reland(group, was)


class Marks(_Landings):
    """What is loaded on one `Deck`, for an undo step that undoes a load (undo.py;
    plan 15 WP1, fork 2; per deck since plan 44 D5a, scoped to the loadable patch since
    D5b): that deck's landed names and clean references, and the loaded patch's
    note. Opaque to undo.py, which only calls `take`, `before` and `put` — so
    after undoing a load the library says the earlier loadable patch is loaded
    again, and Save cannot write the earlier look over the later file.

    The meta controller's half is `MetaMarks`, on its own stack: the show, the
    shared meta groups' labels, each group's layout. So a deck's undo never relands
    the one strip the meta controller has."""

    def _mine(self, group: str, kinds) -> bool:
        return group in kinds or group not in SHARED_META_GROUPS

    def _show(self) -> tuple:
        """Which show this is, and the GRAPH page's positions of its fixture nodes
        (plan 28 N2): a tidy on a deck moves them, and undoing it puts them back
        while the show is the same one."""
        pr = self.lib.project
        return (pr.ident(), copy.deepcopy(getattr(pr, "layout", {})))

    def take(self) -> tuple:
        """(`_show`, {group: landed}, the loaded patch's note and the notes
        its load left for the panel, the loaded patch's graph — plan 26
        A4, `loadable.GraphSection.mark`, None with no loadable patches), the
        loaded patch's GRAPH page layout (plan 28 N2, `LoadedPatch.layout`),
        the media channels' bins (plan 32, `LoadedPatch.media`), the GRAPH
        page's groups (plan 40 T2, `LoadedPatch.groups`) and the floor under
        their numbers (row 563, `LoadedPatch.group_high`), the loadable patch's bus
        cuts (plan 44 D3, `LoadedPatch.bus`) and its node mode (plan 57,
        `LoadedPatch.node_mode`)."""
        pre = self.lib.loaded_patch
        gs = getattr(pre, "graph", None)
        return (self._show(), self.lands(),
                (getattr(pre, "note", ""), list(getattr(pre, "notes", ())),
                 list(getattr(pre, "desk_notes", ()))),
                gs.mark() if gs is not None else None,
                copy.deepcopy(getattr(pre, "layout", None) or {}),
                self._bins(pre),
                copy.deepcopy(getattr(pre, "groups", None) or []),
                getattr(pre, "group_high", 0),
                getattr(pre, "bus", None),
                getattr(pre, "node_mode", None))

    @staticmethod
    def _bins(pre):
        """The media channels' bins (plan 32), None without them."""
        media = getattr(pre, "media", None)
        return media.to_json() if media is not None else None

    def equal(self, mark: tuple) -> bool:
        """Would `put(mark)` change nothing now? So not by another show's name: the
        show is `MetaMarks`', and across a change of show `put` leaves it be."""
        now = self.take()
        if mark[1:] != now[1:]:
            return False
        return mark[0][0] != now[0][0] or mark[0][1] == now[0][1]

    def before(self, mark: tuple) -> None:
        """First in a restore: the loaded patch's graph goes back first of all
        (plan 26 A4): an effect instance's params (`fx.acid.2.*`) exist before
        their values land."""
        gs = getattr(self.lib.loaded_patch, "graph", None)
        if mark[3] is not None and gs is not None:
            gs.put(mark[3])

    def put(self, mark: tuple) -> None:
        """Last in a restore: each of the deck's groups' name, reference and
        re-apply road as they were (`Library.reland`; a group that had none then
        has none now), the loaded patch's note and its load's notes for the
        panel, and the bank's lit slot. While the show is the same one its GRAPH
        page positions go back too (the undo of a tidy; they are not in its file
        until it is saved). The rest of the show is `MetaMarks`'."""
        lib, pr = self.lib, self.lib.project
        (show, landed, note, _graph, layout, bins, groups, group_high, bus) = mark[:9]
        # (plan 57: a step from before a hot reload has no node mode)
        mode = mark[9] if len(mark) > 9 else None
        if show[0] == pr.ident():
            pr.layout = copy.deepcopy(show[1])
        self._reland(landed)
        pre = lib.loaded_patch
        if pre is not None:
            pre.note, pre.notes, pre.desk_notes = note[0], list(note[1]), list(note[2])
            pre.layout = copy.deepcopy(layout)   # the GRAPH page's positions (plan 28 N2)
            media = getattr(pre, "media", None)
            if bins is not None and media is not None:
                media.from_json(bins)            # the bins (plan 32)
            pre.groups = copy.deepcopy(groups)   # the GRAPH page's groups (plan 40 T2)
            pre.group_high = max(pre.group_high, group_high)   # …and their floor (row 563)
            if bus is not None:                  # the bus cuts (plan 44 D3)
                pre.bus = bus
            if mode is not None:                 # the node mode (plan 57)
                pre.node_mode = mode
        pr.follow()


class MetaMarks(_Landings):
    """What is loaded on the meta controller, for its stack (plan 44 D5b): the
    show's own fields, the shared meta groups' landed names and clean references (the
    one strip the meta controller has) and each group's layout. `lib` is the one
    library. **The show's mark is here and on no deck's stack:** a show is what is
    set for a performance, so undoing a show load is ⌘Z in a meta section, and the
    startup loadable patch it brought up is a load on its deck's stack."""

    def _mine(self, group: str, kinds) -> bool:
        return group in SHARED_META_GROUPS and group not in kinds

    def take(self) -> tuple:
        """(the show's mark, {group: landed}, {group: its `extra` hook's dict —
        the band layout})."""
        lib = self.lib
        return (lib.project.mark(), self.lands(),
                {g: copy.deepcopy(hook()) for g, hook in lib._extra_hooks.items()})

    def before(self, mark: tuple) -> None:
        """First in a restore: a group whose layout differs from the mark's gets
        it back through its own `on_layout` hook, so its params exist before their
        values land — the order `_apply_doc` keeps."""
        lib = self.lib
        for group, extra in mark[2].items():
            hook, now = lib._layout_hooks.get(group), lib._extra_hooks.get(group)
            if hook is None or now is None or not extra or extra.get("layout") is None:
                continue
            if now() != extra:
                hook(extra["layout"])
                lib._fresh_of(group)

    def put(self, mark: tuple) -> None:
        """Last in a restore: the shared meta groups' names, references and re-apply
        roads as they were. The show's own fields go back (`Project.remark`) only
        when the show itself differs — the undo of a show load. Otherwise the bank
        and startup are left as they are: they are in the show's file the moment
        they change, and reverting them in memory would make the show's dirty dot
        lie. `last_show` is never rewritten."""
        pr = self.lib.project
        show, landed, _extras = mark
        if Project.ident_of(show) != pr.ident():
            pr.remark(show)
        self._reland(landed)
        pr.follow()


# ---------------------------------------------------------------- library

class Library:
    """Module presets, loadable patches and projects over one registry.

    Built before the registry (the loadable patch bank's params need the
    project's bank), bound to it with ``attach(reg)``, which also captures
    the fresh-object values and applies the show a launch opens. `home` is
    the library tree — the one tier; tests pass a tmp_path and never touch
    ~/Hyperspace. A document kind (`kind`; loadable.py's `LoadedPatch`) adds a
    group whose files the library keeps and someone else applies;
    ``presets`` is the `LoadedPatch` the bank loads through (None until app.py
    builds it after the router).
    """

    # the panel's deck's, once pointed (plan 44 D5a); one deck's own: `DeckLibrary`
    reg = Through("reg")
    loaded_patch = Through("loaded_patch")

    def __init__(self, home_dir: Path | None = None, *, machine: Path | None = None,
                 period: float = 0.5):
        # `home` is the library root — loadable patches, shows, module groups, the
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
        self.reg = None            # (`reg`, below: the panel's deck's, once pointed)
        self.status = ""
        self.error = ""
        self.warning = ""
        # how many times `say` set each of `status` and `warning`: a line
        # said again in the same words shows again (the footer, ui.py).
        # Every line is set through `say`; only a clear ("") is assigned
        self.said: dict[str, int] = {}
        self._fresh: dict[str, Any] = {}
        self._current: dict[str, str | None] = {}     # group → loaded patch name
        self._loaded: dict[str, Any] = {}             # group → what that load produced
        self._layout_hooks: dict[str, Any] = {}
        self._extra_hooks: dict[str, Any] = {}    # group → what a save adds beside values
        self._load_hooks: dict[str, Any] = {}     # group → told the name after a load
        self._adopted: dict[str, Any] = {}        # group → how to re-apply an adopted loadable patch
        self._kinds: dict[str, DocKind] = {}      # group → a document kind of its own
        self._kinds[PATCHES] = _patch_kind()      # plan 40 T1: spawned, never loaded
        self._kinds[PLAYLISTS] = _playlist_kind()  # plan 44 D6: played, never landed
        self._fresh_extra: dict[str, dict] = {}   # group → its extra (layout) at attach
        self._defaults: dict[str, dict[str, Any]] = {}   # defaults(group), until a file moves
        self._docs: dict[Path, tuple[float, dict]] = {}   # parsed files, by mtime
        self._mtimes: dict[Path, float] = {}
        self._next = 0.0
        self.loaded_patch = None        # loadable.LoadedPatch, set by its constructor (`presets`, below)
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
        last (plan 15 WP4: two loadable patches put into slots one after the other,
        a slot cleared twice). Every line that reports something that just
        happened goes through here (plan 16 WP7: an empty F-key pressed
        twice, home with no startup loadable patch pressed twice); a plain assignment
        is for clearing a line, and is not counted — so nothing that
        assigned the same words every frame could hold the footer open."""
        said = self.__dict__.setdefault("said", {})   # (a Library from before a hot reload)
        if status is not None:
            self.status = status
            said["status"] = said.get("status", 0) + 1
        if warning is not None:
            self.warning = warning
            said["warning"] = said.get("warning", 0) + 1

    # ---- which deck (plan 44 D5a): this object is the panel's view ----

    @property
    def base(self) -> Library:
        """The one library, whichever view this is (`DeckLibrary`)."""
        return self

    def on_deck(self, loaded_patch=None) -> DeckLibrary:
        """The library as one deck sees it (`DeckLibrary`), for `presets`; None:
        they are not built yet, and the `LoadedPatch` handed it says so."""
        return DeckLibrary(self, loaded_patch)

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
                and in_group(reg[k], group)}       # (a shared meta key of the group left out)

    def _fresh_all(self) -> dict[str, Any]:
        for g in {p.group for p in (self.reg or []) if p.persist and p.group}:
            self._fresh_of(g)
        return dict(self._fresh)

    def kind(self, group: str, schema: str, *, load, document, signature,
             versions: tuple[int, ...] = (1,), text=None) -> None:
        """Register a document kind for `group` (see DocKind): its files
        live under ``<root>/<group>/`` like any loadable patch's, the strip drives
        them, and the hooks apply and produce them."""
        self._kinds[group] = DocKind(schema, tuple(versions), load, document, signature, text)

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(self._kinds)

    def on_layout(self, group: str, hook) -> None:
        """Register who rebuilds a group's params from a loadable patch's `layout`."""
        self._layout_hooks[group] = hook

    def extra(self, group: str, hook) -> None:
        """Register what a save of this group writes beside its values — the
        analyzer's ``{"layout": …}`` — so a loadable patch saved from the strip
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
        """Every group with a loadable patch folder, a persisted param or a document
        kind — less ``macro``: a macro's meaning is its subscribers, which
        live in the loadable patch, so it gets no module-preset strip (plan 13 §9);
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
                # plan 50: a group whose patches of one group have a folder
                if (root / PATCHES).is_dir():
                    out.update(d.name for d in (root / PATCHES).iterdir()
                               if d.is_dir() and not d.name.startswith("."))
        return sorted(out - set(RETIRED_MODULES))

    def group_dir(self, root: Path, group: str) -> Path:
        """Where `group`'s files live under `root` (plan 50): a document
        kind's — the loadable patches, the patches — in ``<root>/<group>/``; every
        other group's, its patches of one group (what module presets
        were), in ``<root>/patches/<group>/`` (`group_folder`, the one table)."""
        return root / group_folder(group, self._kinds)

    def _files(self, group: str) -> dict[str, Path]:
        """file key → path, every file of the group's folder (`group_dir`):
        the stem, and for the loadable patches (plan 48 row 584) the path under
        ``presets/`` less ``.json`` — ``party/deep/c`` — every folder down,
        less hidden ones (``.cache``)."""
        out: dict[str, Path] = {}
        for root in self._roots():
            d = self.group_dir(root, group)
            if not d.is_dir():
                continue
            if group != LOADABLE:
                out.update((p.name[:-5], p) for p in d.glob("*.json"))
                continue
            for p in self._tree(d)[0]:
                out[p.relative_to(d).as_posix()[:-5]] = p
        return out

    def _tree(self, d: Path) -> tuple[list[Path], list[str]]:
        """The loadable patches' folder walked (`_walk_dirs`): its ``*.json`` files
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
        """Every loadable patch file by `fold` of its key (``party/trip``), kept
        with the walk — a list per key: two files may fold to one
        (`_resolve` refuses to pick)."""
        out: dict[str | None, list[Path]] = {}
        for root in self._roots():
            d = root / LOADABLE
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
            d = root / LOADABLE
            if d.is_dir():
                for f in self._tree(d)[1]:
                    if fold_folder(f) == want:
                        return f
        return None

    def _prefix(self, group: str, path: Path | None) -> str:
        """The folder a loadable patch file sits in under ``presets/``, ending in
        ``/`` (``party/``) — ``""`` at the top, for any other group, or a
        path outside the library (plan 48)."""
        if group != LOADABLE or path is None:
            return ""
        try:
            rel = path.parent.relative_to(self.home / group).as_posix()
        except ValueError:
            return ""
        return "" if rel == "." else f"{rel}/"

    def _fold(self, group: str, name: str) -> str | None:
        """What a name is compared by — case and spacing folded: its slug,
        and for a loadable patch its folder too (``party/trip-2``, `path_slug`
        lowered); None for a loadable patch name that could not name a file
        (``../x``)."""
        return slug(name) if group != LOADABLE else fold(name)

    def folder_of(self, group: str, name: str | None) -> tuple[str, str]:
        """(folder, leaf) of a loadable patch name — one rule (plan 48 review): a
        ``/`` in a listed name always means a folder (a file's own ``/`` is
        listed as ``" - "``, `harmless`), so the name is split at its last
        ``/``; ``""`` is the top. Any other group has no folders."""
        if not name:
            return "", name or ""
        return split_name(name) if group == LOADABLE else ("", name)

    def _leaf(self, group: str, path: Path) -> str:
        """The name a file is listed by, less its folder: its own ``name``
        (else its stem), for a loadable patch with any ``/`` made harmless."""
        return self._shown(group, self._name_of(path))

    @staticmethod
    def _shown(group: str, name: str) -> str:
        return harmless(name) if group == LOADABLE else name

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

        A loadable patch in a folder under ``presets/`` is listed by its
        **folder-qualified** name (plan 48 row 584): ``party/TRIP`` for
        ``presets/party/trip.json`` whose own ``name`` is ``TRIP`` — the
        file keeps the leaf, the folder is the path. A top-level loadable patch's
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
        the slug, and for a loadable patch its folder and slug compared by `fold`
        (``Party/Trip`` finds ``presets/party/trip.json``, as APFS does).
        With `loose` — a **read** only: a load, a pad, the startup loadable patch,
        what a show still names — a loadable patch name whose folder is not on
        disk also tries its `slug` among the top-level files, an old show's
        ``Ac/Dc`` for the top-level ``ac-dc.json`` (plan 48 review). A
        writer (`save_as`, `delete`, `rename`) never takes that road:
        ``party/TRIP`` typed with no ``party/`` is a new file in a new
        folder, never the top-level ``party-trip.json``. None for none, and
        for a loadable patch name that could not name a file inside ``presets/``
        (``../x``, ``/etc/x``). Two files that answer to one spelling
        (``trip_2.json`` and ``trip-2.json``) resolve to neither by a fold:
        the file key spelled as on disk finds its own, any other spelling
        neither (a loose read says which two)."""
        say = (lambda text: self.say(warning=text)) if loose else None
        return self._resolve(group, name, self._lookup(group), loose=loose, say=say)

    def _lookup(self, group: str) -> tuple:
        """What `_resolve` reads, taken once per operation (review of #334:
        a rename or a frame's ask lists the folder once): the index, the
        file keys, and for the loadable patches the files by `fold` and the folders
        on disk folded."""
        files = self._files(group)
        idx = self._index(group, files)
        if group != LOADABLE:
            return idx, files, {}, set()
        folders: set[str | None] = set()
        for root in self._roots():
            if (root / LOADABLE).is_dir():
                hit = self._walked(root / LOADABLE)
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
        if group != LOADABLE:
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
        """Every loadable patch of the group by name, case folded — the PRESETS
        page's list, the strip's arrows, the pad's walk."""
        return sorted(self._index(group), key=str.lower)

    def _taken(self, group: str) -> set[str]:
        """The slugs a new file of the group may not take: every file stem
        in the folder and every listed name — on a filesystem that folds
        case `Trip-2.json` is the file a save of "TRIP 2" would write over
        (`save_new`, `rename`). For the loadable patches each is folded with its
        folder (`_fold`: ``party/trip-2``), so a name is taken only in its
        own folder (plan 48)."""
        if group != LOADABLE:
            return ({slug(s) for s in self._files(group)}
                    | {slug(n) for n in self.list(group)})
        out = {self._fold(group, s) for s in self._files(group)}
        out |= {self._fold(group, n) for n in self.list(group)}
        out.discard(None)
        return out  # type: ignore[return-value]

    def still_named(self, name: str, path: Path | None = None) -> list[str]:
        """What in the open show still names the loadable patch `name` (or, given,
        the file at `path`): its slots (``F6``, ``slot 12``) and its
        ``startup``."""
        pr, key = self.project, self._fold(LOADABLE, name)
        snap = self._lookup(LOADABLE)                   # one look for every slot
        target = path or self._resolve(LOADABLE, name, snap, loose=True)

        def names(n: str | None) -> bool:
            return bool(n) and (n == name or (key is not None and self._fold(LOADABLE, n) == key)
                                or (target is not None
                                    and self._resolve(LOADABLE, n, snap, loose=True) == target))
        out = [slot_key(k) for k, n in enumerate(pr.bank) if names(n)]
        if names(pr.startup):
            out.append("the startup preset")
        return out

    def read(self, group: str, name: str) -> dict:
        path = self.path_of(group, name, loose=True)
        if path is None:
            raise LibraryError(f"{group_word(group)}: no preset {name!r}")
        doc = copy.deepcopy(self._doc(path))
        kind = self._kinds.get(group)
        if kind is not None:                       # its own format: checked, not lifted
            schema = str(doc.get("schema") or "")
            k, _, v = schema.rpartition("/")
            if k != kind.schema or not v.isdigit() or int(v) not in kind.versions:
                raise LibraryError(f"{path.name}: schema {schema!r} is not a {kind.schema}")
            return doc
        # plan 50: a patch of one param group, through the one ladder (a
        # module preset from before reads as its `patch/2`; one that never
        # said its group is the folder's). Review fix 7: anything else in a
        # group's folder — a whole loadable patch, a canvas patch, another group's —
        # is refused, the mismatch named
        if not isinstance(doc, dict):
            raise LibraryError(f"{path.name}: not a JSON object")
        if (doc.get("schema") == f"{patchdoc.MODULE_KIND}/{patchdoc.MODULE_VERSION}"
                and patchdoc.GROUP_KEY not in doc):
            doc[patchdoc.GROUP_KEY] = group
        if patchdoc.GROUP_KEY not in doc:
            what = ("a whole preset" if patchdoc.shape_of(doc) == patchdoc.LOADABLE_SHAPE
                    else "a canvas patch" if str(doc.get("schema", "")).startswith(
                        f"{patchdoc.KIND}/") else f"schema {doc.get('schema')!r}")
            raise LibraryError(NOT_GROUP_WORDS.format(file=path.name, what=what,
                                                      group=group_word(group)))
        doc = forward_group(doc, path.name)
        refused = patchdoc.check(doc)
        if refused:
            raise LibraryError(f"{path.name}: " + "; ".join(refused))
        if doc[patchdoc.GROUP_KEY] != group:
            raise LibraryError(NOT_GROUP_WORDS.format(
                file=path.name,
                what=f"a patch of the {group_word(doc[patchdoc.GROUP_KEY])} group",
                group=group_word(group)))
        return doc

    # ---- patches (plan 40 T1) ----

    def read_patch(self, name: str) -> dict:
        """The patch `name`: its file under ``<root>/patches/``, checked —
        the schema (`read`) and the shape (`patches.check`), after the one
        ladder (`patches.forward`: a ``patch/1`` reads as its ``/2``, plan
        50). A patch that is not there, that check refuses, or that is one
        group's (spawned from that group's strip), raises LibraryError with
        the reasons in words."""
        doc = forward_group(self.read(PATCHES, name), name)
        if patchdoc.names_group(doc):
            raise LibraryError(GROUP_PATCH_WORDS.format(
                name=name, group=group_word(doc[patchdoc.GROUP_KEY])))
        refused = patchdoc.check(doc)      # (an empty `group`: one line, review fix 6)
        if refused:
            path = self.path_of(PATCHES, name)
            raise LibraryError(f"{path.name if path else name}: " + "; ".join(refused))
        # wave 0 T1: a file from before (no `units` marker) has its depths
        # onto the effects' retapered params read as they were, measured
        # against this meta controller's effect files — the one door a patch comes in
        # by, so a spawn lands what tools/retaper_routes.py would write
        doc, _ = retaper_depths(doc, fx_files(self.reg))
        return doc

    def save_patch(self, doc: dict) -> Path:
        """Write patch `doc` as ``<home>/patches/<slug of its name>.json``
        — atomically (`_write_text`), a different text already there copied
        to the trash first, as `save_as` does — and nothing else: no loadable patch,
        show or binding is touched. A document `patches.check` refuses is
        not written (LibraryError)."""
        self.writable()
        refused = patchdoc.check(doc)
        name = str(doc.get("name") or "").strip() if isinstance(doc, dict) else ""
        if not name:
            refused = ["a patch needs a name", *refused]
        if refused:
            raise LibraryError("patch not saved: " + "; ".join(refused))
        return self._write_kind(PATCHES, name, doc)

    def save_playlist(self, doc: dict, key: str | None = None) -> Path:
        """Write playlist `doc`, as `save_as` does: over the file `key` (else its name)
        resolves to, so a save never leaves a second file of one name, else a new
        ``<home>/playlists/<slug>.json``. `playlist.Playlist.to_doc` is what makes one, and
        a nameless one is refused."""
        self.writable()
        name = str(doc.get("name") or "").strip()
        if not name:
            raise LibraryError("playlist not saved: a playlist needs a name")
        return self._write_kind(PLAYLISTS, name, doc, self.path_of(PLAYLISTS, key or name))

    def _write_kind(self, group: str, name: str, doc: dict, path: Path | None = None) -> Path:
        """`doc` at `path`, by default ``<home>/<group>/<slug of name>.json``: atomically, a
        different text already there copied to the trash first."""
        path = path if path is not None else self.home / group / f"{slug(name)}.json"
        text = _json_text(doc)
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
        self.say(f"{group}: saved {name}")
        return path

    # ---- defaults & values ----

    def default_name(self, group: str) -> str | None:
        if group in RETIRED_MODULES:   # plan 40 T5: an old fx/default.json is no default
            return None
        name = DEFAULT_NAMES.get(group, "default")
        return name if self.path_of(group, name) is not None else None

    def defaults(self, group: str) -> dict[str, Any]:
        """What reset(group) produces: the default loadable patch over the fresh values.
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
        """A loadable patch's values over the group's defaults, ids this registry
        has — the one fill-in for a partial file, whichever road applies it
        (a strip load, or the scene combo re-tuning from a scene)."""
        out = self.defaults(group)
        out.update(values)
        # (review of #351: a group's shared meta key — `ghost.mirror` — is no
        # module preset's to set, whatever a file says: `params.in_group`)
        return {k: v for k, v in out.items() if k in self.reg and in_group(self.reg[k], group)}

    def _landed(self, group: str, name: str | None, loaded: dict[str, Any] | None,
                reapply=None) -> None:
        """One place for what "the group's current preset" means: its name,
        the values it produced (what is_dirty compares against) and, for a
        loadable patch someone else applied, how to apply it again when its file
        changes on disk. The loadable patches' is their own (`_owner`, plan 44 D3)."""
        owner = self._owner(group)
        if owner is not None:
            owner.landing = (name, loaded, reapply)
            return
        labels = self._labels(group)
        if labels is not None:
            labels[group] = (name, loaded, reapply)
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
        state as it now stands being what "clean" means — a loadable patch's
        module label (plan 13 D3): the strip shows the name and a clean
        dot, and nothing is loaded. None: no module preset, but the state
        as it stands is still what "clean" means — a loadable patch that names no
        module for the group landed it, and the section's dot compares against
        that, not fresh defaults (plan 14 WP4)."""
        loaded = self.reg.snapshot(group) if self.reg is not None else None
        self._landed(group, name, loaded)

    def landed(self, group: str) -> tuple:
        """The group's landed state, opaque, for an undo to hand back."""
        owner = self._owner(group)
        if owner is not None:
            return tuple(owner.landing)
        labels = self._labels(group)
        if labels is not None:
            return labels.get(group, (None, None, None))
        return (self._current.get(group), self._loaded.get(group), self._adopted.get(group))

    def _owner(self, group: str):
        """Who keeps `group`'s landing when it is not the library (plan 44
        D3): the loadable patches kind's `LoadedPatch` — its `landing`, (current, what
        its load produced, how to re-apply) — so a deck's dirty dot is its
        own; None for every other group."""
        pre = self.loaded_patch
        if group == LOADABLE and pre is not None and hasattr(type(pre), "landing"):
            return pre
        return None

    def _labels(self, group: str) -> dict | None:
        """Where a patch group's landing is kept: on the deck's loadable patches
        (`LoadedPatch.labels`, plan 44 D5a), since what a section's dot compares
        against is that deck's. None: a shared meta group, or no loadable patches yet,
        kept here, the one strip the meta controller has."""
        if group not in PATCH_GROUPS:
            return None
        return getattr(self.loaded_patch, "labels", None)

    def landed_groups(self) -> set[str]:
        """Every group with a landing: the library's and the loadable patches'."""
        out = {*self._current, *self._loaded, *self._adopted}
        if self._owner(LOADABLE) is not None:
            out.add(LOADABLE)
        out.update(getattr(self.loaded_patch, "labels", ()))
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
        return self.landed(group)[0]

    def load(self, group: str, name: str) -> list[str]:
        """Apply a loadable patch; returns the ids it names that this registry lacks."""
        if group not in self._kinds:
            self._need_reg()
        doc = self.read(group, name)
        return self._apply_doc(group, name, doc, path=self.path_of(group, name, loose=True))

    def _apply_doc(self, group: str, name: str, doc: dict, *, path: Path | None = None,
                   quiet: bool = False) -> list[str]:
        """One road in for a loadable patch document, wherever it came from — the
        strip, the project's module list, a file edited on disk: a kind's
        loader, or the layout hook first and then the values over the
        group's defaults. `quiet` (a project load) leaves `status` alone."""
        kind = self._kinds.get(group)
        if kind is not None:
            try:
                missing = list(kind.load(doc, path) or [])
            except (ValueError, KeyError, TypeError, AttributeError, OSError) as e:
                raise LibraryError(f"{group_word(group)}/{name}: {e}") from e
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
            self._push(group, f"{group_word(group)}: {doc.get('name') or name}")
            hook = self._layout_hooks.get(group)
            if hook is not None and doc.get("layout") is not None:
                hook(doc["layout"])                    # rebuild params first
                self._fresh_of(group)                  # …and their build values are "fresh"
            # plan 50: a patch of one group replaces that group's values —
            # what `patches.spawn` of it says (`Landing.replaces`; nothing can
            # collide, so no sheet). Landed here directly (review fix 3): the
            # spawn would only hand its values back, at a full read's cost
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
        self.report(missing, f"{group_word(group)}/{name}")
        if not quiet:
            self.say(f"{group_word(group)}: {self.current(group)}")
        hook = self._load_hooks.get(group)
        if hook is not None:
            hook(self.current(group))
        return missing

    def land_unsaved(self, group: str, name: str, doc: dict) -> list[str]:
        """Apply `doc` as the group's current loadable patch `name` that no file
        holds (plan 35 T7's `LoadedPatch.new`): the one road in (`_apply_doc`,
        no path), then nothing to be clean against — dirty until it is saved,
        the Project's own rule for a show never saved. Returns the unknown
        ids."""
        missing = self._apply_doc(group, name, doc)
        self._landed(group, name, ())
        return missing

    def adopt(self, group: str, name: str, reapply) -> None:
        """A loadable patch applied by someone else — the scene combo landing a
        scene's values on the analyzer itself: make it the group's current
        loadable patch, with the group's state as it now stands as what "clean"
        means (the combo applies no layout, so the file's layout ids are
        not the reference), and `reapply` as what poll() calls when the
        file changes on disk, in place of a whole load."""
        loaded = self.reg.snapshot(group) if self.reg is not None else None
        again = self.current(group) == name
        self._landed(group, name, loaded, reapply)
        if again:
            # the same scene set again — a knob on `scene.select` sends the
            # same choice many times in one turn: no news, and the footer's
            # slot is not taken from a line that is (review of PR #92)
            self.status = f"{group_word(group)}: {name}"
        else:
            self.say(f"{group_word(group)}: {name}")

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
        """Write the group's bases as a loadable patch and make it current — over
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
        if group == LOADABLE:
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
            path = self.group_dir(self.home, group) / f"{slug(name)}.json"   # (plan 50)
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
        self.say(f"{group_word(group)}: saved {name}"
                 + (f" (was {renamed})" if renamed else ""))
        hook = self._load_hooks.get(group)
        if kind is not None and hook is not None:   # a kind's current moved: say so
            hook(name)                               # (the bank's light, loadable.py)
        return path

    def document(self, group: str, name: str, *, extra: dict | None = None) -> dict:
        """The group's bases as a loadable patch document — with whatever the
        group's `extra` hook adds beside the values (the analyzer's layout),
        unless the caller brought its own. Every band document the library
        writes is built here: a file, or a project's inline module copy. A
        document kind's is its own hook's. Plan 50: a group's document is a
        patch of one param group (`patches.group_doc`, ``hyperspace.patch/2``)."""
        kind = self._kinds.get(group)
        if kind is not None:
            return kind.document(name)
        reg = self._need_reg()
        if extra is None and group in self._extra_hooks:
            extra = self._extra_hooks[group]()
        beside = dict(extra or {})
        if group == "camera":
            beside[UNITS_KEY] = dict(UNITS)  # its pan is in world units (plan 26 A2)
        return patchdoc.group_doc(group, name, reg.snapshot(group), extra=beside)

    def overwrite(self, group: str, *, extra: dict | None = None) -> Path | None:
        """Save over the current loadable patch (its old text kept in the trash)."""
        cur = self.current(group)
        return None if cur is None else self.save_as(group, cur, extra=extra)

    def delete(self, group: str, name: str) -> bool:
        """Remove a loadable patch. The file is copied to the trash first
        (`to_trash`), and a copy that fails **refuses the delete**
        (`LibraryError`): a full disk cannot make a delete unrecoverable
        (plan 15 fork 6). False when there is no such loadable patch."""
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
        still = self.still_named(shown, path) if group == LOADABLE else []
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
        if group == LOADABLE:
            if still:
                self.say(warning=f"{shown} is in the trash — {_and(still)} still "
                                 f"name{'s' if len(still) == 1 else ''} it; restore it from "
                                 "the trash, or clear the slot")
            else:
                self.say(f"{shown} is in the trash — the PRESETS section's trash can restore it")
        return True

    def rename(self, group: str, old: str, new: str) -> Path:
        """Rename a loadable patch (plan 19 WP4): the file, the name inside it, and
        every show in the home that names it. Raises LibraryError and
        changes nothing when `old` is not a loadable patch of the loadable patches' group
        (or a patch), `new` is empty or taken, or the old file cannot be
        kept in the trash. No undo step: the nets are the old file in
        ``trash/presets/``, each rewritten show in ``trash/projects/``, and
        renaming it back.

        In order, so that a stop at any point loses nothing:

        1. refuse — an empty name, a name whose slug is taken (`_taken`: a
           file stem in the folder or a listed name, less this loadable patch's
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
           edit); the loaded patch keeps its clean reference under the new
           name, so an unsaved edit stays one, and the load hook is told;
        5. every ``hyperspace.project/2`` show in ``<home>/projects`` whose
           bank or startup names the old loadable patch is copied to the trash,
           then written with the new name — the open show through its
           `Project` (its dot and the bank's light stay right). A show whose
           copy or write fails is left as it is; a schema-1 show is left
           alone; both are named in the warning. *Stopped mid-way: the
           shows done name the new name and their old files are in the
           trash; the rest name the old one*;
        6. `Project.follow()`; the status says how many shows changed."""
        self.writable()
        # plan 40 T1: a patch renames the same way, less step 5 (no show
        # names a patch; a group's provenance slug is the loadable patch's to keep)
        if group not in RENAMABLE:
            raise LibraryError(f"{group_word(group)}: only a preset can be renamed (or a patch)")
        snap = self._lookup(group)                 # one look for the whole rename
        idx, files = snap[0], snap[1]
        path = self._resolve(group, old, snap, loose=False)
        if path is None:
            raise LibraryError(f"no preset {old!r}")
        new = (new or "").strip()
        # plan 48 row 584: a rename keeps the folder — `new` is the leaf
        # (the folder may be spelled in front of it, as the list spells it);
        # moving a loadable patch between folders is `move` (stage 2)
        pre = self._prefix(group, path)
        leaf = new[len(pre):].strip() if pre and new.startswith(pre) else new
        if group == LOADABLE and "/" in leaf:
            raise LibraryError(f"{new}: a rename keeps the folder — a name has no '/' "
                               "(the row's right-click: move to ▸)")
        if not leaf:
            raise LibraryError("a preset needs a name")
        new = pre + leaf
        stem = path.name[:-5]
        if new == old:
            return path
        doc = _read_json(path)
        # (`snap`, taken above, is the library as it was before: steps 4–6,
        # `_follow_many`, read what named the file from it)
        in_place = slug(leaf) == stem
        # `_taken` less this loadable patch's own stem and name — in its own folder
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
        self._follow_many({path: new}, snap, "renamed", f"{old} → {new}",  # 4–6.
                          group=group)
        return dst

    def _repoint_by(self, to) -> tuple[int, list[str]]:
        """Step 5 of `rename` (and of a move, a folder's rename — plan 48
        stage 2, many loadable patches at once): `to(n)` is the name a slot or the
        startup naming `n` takes now, None to leave it. Every user show with
        a hit is copied to the trash once, then written; the open show
        through its `Project` (its dot and the bank's light stay right).
        Returns (shows written, shows left as they were with why)."""

        def hit(n) -> bool:
            return isinstance(n, str) and bool(n) and to(n) is not None

        def moved(n):
            return to(n) if hit(n) else n

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
                pr.bank = [moved(n) for n in pr.bank]
                pr.startup = moved(pr.startup)
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
            doc["bank"] = [moved(n) for n in bank]
            if hit(doc.get("startup")):
                doc["startup"] = moved(doc.get("startup"))
            try:
                _write_json(show, doc)
            except LibraryError as e:
                left.append(f"{label} ({e})")
                continue
            self._sync(show)
            done += 1
        # the open show with no file yet (a new show): its bank in memory
        if pr.path is None and (any(hit(n) for n in pr.bank) or hit(pr.startup)):
            pr.bank = [moved(n) for n in pr.bank]
            pr.startup = moved(pr.startup)
        return done, left

    # ---- folders (plan 48 stage 2): move, make, rename, remove ----

    def folders(self) -> list[str]:
        """Every folder under ``presets/``, every folder down, spelled as on
        disk (``party``, ``party/deep``) — empty ones too, less hidden
        ones; sorted case folded."""
        out: set[str] = set()
        for root in self._roots():
            d = root / LOADABLE
            if d.is_dir():
                out.update(self._tree(d)[1])
        return sorted(out, key=str.lower)

    def _owned(self, path: Path, snap: tuple, group: str = LOADABLE) -> set[str]:
        """What names the file `path`, folded: its listed names and its file
        key (and, at the top, its raw stem, as before plan 48)."""
        idx, files = snap[0], snap[1]
        mine = {self._fold(group, n) for n, p in idx.items() if p == path}
        mine |= {self._fold(group, s) for s, p in files.items() if p == path}
        if not self._prefix(group, path):
            mine.add(path.name[:-5])
        mine -= {None, ""}
        return mine  # type: ignore[return-value]

    def _shown_name(self, path: Path, snap: tuple) -> str:
        """The name the list gave the file at `path` in `snap`."""
        for n, p in snap[0].items():
            if p == path:
                return n
        return self._prefix(LOADABLE, path) + self._leaf(LOADABLE, path)

    def _follow_many(self, moves: dict[Path, str], snap: tuple, verb: str, what: str,
                     *, group: str = LOADABLE) -> tuple[int, list[str]]:
        """After files were renamed or moved (`moves`: each old path → the
        name it is listed by now; `snap` the library as it was before) —
        `rename`'s steps 4–6, and a move's and a folder rename's: the loaded
        loadable patch's name follows (its clean reference kept, the load hook
        told); then, for the loadable patches, every show's slots and startup
        (`_repoint_by`: a slot naming a file by any spelling that found it
        before — its name, its file key, a loose read, review of #334) and
        `Project.follow()`. The status says how many shows (a patch: none
        names one)."""
        byfold: dict[str, str] = {}
        for p, now in moves.items():
            for k in self._owned(p, snap, group):
                byfold[k] = now
        listed = {n: moves[p] for n, p in snap[0].items() if p in moves}

        def to(n) -> str | None:
            if not isinstance(n, str) or not n:
                return None
            if n in listed:
                return listed[n]
            k = self._fold(group, n)
            if k is not None and k in byfold:
                return byfold[k]
            target = self._resolve(group, n, snap, loose=True)
            return moves.get(target) if target is not None else None

        cur = self.current(group)          # (plan 44 D3: the loadable patches' own)
        now = to(cur) if cur is not None else None
        if now is not None and now != cur:
            self._landed(group, now, self.landed(group)[1])
            hook = self._load_hooks.get(group)
            if hook is not None:
                hook(now)
        if group != LOADABLE:
            self.say(f"{verb} {what}")
            return 0, []
        done, left = self._repoint_by(to)
        self.project.follow()
        self.say(f"{verb} {what} ({done} show{'' if done == 1 else 's'} updated)")
        if left:
            self.say(warning=f"{verb} {what}; not updated: {', '.join(left)}")
        return done, left

    @staticmethod
    def _folder_name(name: str) -> str:
        """One segment of a folder's name, as typed, stripped; LibraryError
        for an empty one, one with a ``/``, a hidden one (``.cache``), one
        ending ``.json`` (it would read as a loadable patch's file) or one with a
        control character (a pasted NUL: review of #349)."""
        name = (name or "").strip()
        if not name:
            raise LibraryError("a folder needs a name")
        if any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise LibraryError("a folder's name may not hold a control character")
        if name.lower().endswith(".json"):
            raise LibraryError(f"{name}: a folder's name may not end in '.json' "
                               "(it would read as a preset)")
        if "/" in name:
            raise LibraryError(f"{name}: a folder's name has no '/' — make it inside "
                               "the folder it belongs in")
        if name.startswith("."):
            raise LibraryError(f"{name}: a folder's name may not start with '.' "
                               "(the list skips hidden folders)")
        return name

    def _existing_folder(self, folder: str) -> str:
        """`folder` spelled as it is on disk; ``""`` for the top;
        LibraryError for a folder that is not there."""
        folder = (folder or "").strip().strip("/")
        on_disk = self._folder_on_disk(folder)
        if on_disk is None:
            raise LibraryError(f"no folder {folder!r} under presets/")
        return on_disk

    def move(self, name: str, folder: str) -> Path:
        """Move the loadable patch `name` into `folder` (``""``: the top; else a
        folder on disk) — plan 48 stage 2. The file moves whole, its bytes
        as they were (`_move_file`), its stem and inner ``name`` kept, so it
        is listed as ``<folder>/<leaf>``. Then, as a rename does
        (`_follow_many`): the loaded patch's name follows if it is the one
        moved, and every show in the home that names it — the open show's
        bank and startup too, written as a rename writes it — names it by
        the new name, each show copied to the trash first. No undo step
        (a rename has none): moving it back is the net. Refused, nothing
        moved, for no such loadable patch, no such folder, or a folder that already
        has a loadable patch of that name or that file. Returns the new path."""
        self.writable()
        snap = self._lookup(LOADABLE)
        path = self._resolve(LOADABLE, name, snap, loose=False)
        if path is None:
            raise LibraryError(f"no preset {name!r}")
        folder = self._existing_folder(folder)
        if fold_folder(self._prefix(LOADABLE, path)[:-1]) == fold_folder(folder):
            return path
        leaf = self._leaf(LOADABLE, path)
        new = f"{folder}/{leaf}" if folder else leaf
        base = self.home / LOADABLE
        dst = (base / folder if folder else base) / path.name
        idx, files = snap[0], snap[1]
        taken = ({self._fold(LOADABLE, s) for s, p in files.items() if p != path}
                 | {self._fold(LOADABLE, n) for n, p in idx.items() if p != path})
        if self._fold(LOADABLE, new) in taken or dst.exists():
            raise LibraryError(f"{leaf}: {folder or 'the top level'} already has a preset "
                               "by that name — rename one first")
        _move_file(path, dst)
        self._sync(path, dst)
        self._follow_many({path: new}, snap, "moved",
                          f"{self._shown_name(path, snap)} → {new}")
        return dst

    def make_folder(self, parent: str, name: str) -> str:
        """Make the folder `name` inside `parent` (``""``: the top) under
        ``presets/`` and return it (``party/deep``). Refused when `parent`
        is not on disk, `name` is empty, holds a ``/`` or is hidden, or a
        folder of that name (case folded) is there already."""
        self.writable()
        parent = self._existing_folder(parent)
        name = self._folder_name(name)
        full = f"{parent}/{name}" if parent else name
        if self._folder_on_disk(full) is not None:
            raise LibraryError(f"{full}: that folder is already there")
        try:
            (self.home / LOADABLE / full).mkdir(parents=True, exist_ok=False)
        except FileExistsError as e:
            raise LibraryError(f"{full}: that name is taken (by a file)") from e
        except (OSError, ValueError) as e:
            raise LibraryError(f"{full}: {e}") from e
        self._sync()
        self.say(f"made the folder {full}")
        return full

    def rename_folder(self, folder: str, name: str) -> str:
        """Rename the folder `folder` (``party/deep``) to `name` in the same
        parent and return it. Every loadable patch inside, every folder down, keeps
        its file and its leaf — ``party/deep/C`` becomes ``party/deeper/C``
        — and the loaded patch and every show's slots follow, as a move
        does (`_follow_many`). One step on disk (the folder's own rename),
        never over another folder. Refused for no such folder, the top, or
        a name taken in the parent."""
        self.writable()
        if not (folder or "").strip().strip("/"):
            raise LibraryError("the top level is not a folder to rename")
        folder = self._existing_folder(folder)
        name = self._folder_name(name)
        parent = folder.rpartition("/")[0]
        full = f"{parent}/{name}" if parent else name
        if full == folder:
            return folder
        src, dst = self.home / LOADABLE / folder, self.home / LOADABLE / full
        # review of #349: taken unless `dst` is this very folder (a change of
        # case on a disk that folds case) — asked of the disk, not of a fold:
        # on a case-sensitive volume `Party` beside `party` is another folder
        try:
            itself = dst.exists() and src.samefile(dst)
        except (OSError, ValueError):
            itself = False
        if os.path.lexists(dst) and not itself:
            raise LibraryError(f"{full}: that name is taken — pick another")
        if (not itself and fold_folder(full) != fold_folder(folder)
                and self._folder_on_disk(full) is not None):
            raise LibraryError(f"{full}: that name is taken — pick another")
        snap = self._lookup(LOADABLE)
        moves: dict[Path, str] = {}
        for p in snap[1].values():
            if not p.is_relative_to(src):
                continue
            sub = p.parent.relative_to(src).as_posix()
            pre = full if sub == "." else f"{full}/{sub}"
            moves[p] = f"{pre}/{self._leaf(LOADABLE, p)}"
        try:
            src.rename(dst)
        except (OSError, ValueError) as e:
            raise LibraryError(f"{folder}: not renamed ({e})") from e
        self._sync(*moves, *(dst / p.relative_to(src) for p in moves))
        self._follow_many(moves, snap, "renamed the folder", f"{folder} → {full}")
        return full

    HELD_SAID = 3       # entries `held` names before "and n more"

    def held(self, folder: str) -> list[str]:
        """What keeps the folder `folder` under ``presets/`` from being
        removed (review of #349): every entry in it but a Finder
        ``.DS_Store`` — loadable patches, folders, hidden files, anything — by name
        (a folder with a ``/``), the first HELD_SAID then ``n more``; [] for
        an empty folder, and for one that is not there."""
        folder = (folder or "").strip().strip("/")
        on_disk = self._folder_on_disk(folder) if folder else None
        if not on_disk:
            return []
        try:
            got = sorted((p.name + "/" if p.is_dir() else p.name)
                         for p in (self.home / LOADABLE / on_disk).iterdir()
                         if p.name != ".DS_Store")
        except OSError as e:
            return [f"(unreadable: {e})"]
        if len(got) > self.HELD_SAID:
            got = [*got[: self.HELD_SAID], f"{len(got) - self.HELD_SAID} more"]
        return got

    def remove_folder(self, folder: str) -> None:
        """Remove an empty folder under ``presets/`` (a Finder
        ``.DS_Store`` goes with it). Refused when it holds anything else —
        a loadable patch, a folder, any file, hidden or not: a remove never deletes
        what the trash could not give back."""
        self.writable()
        if not (folder or "").strip().strip("/"):
            raise LibraryError("the top level is not a folder to remove")
        folder = self._existing_folder(folder)
        d = self.home / LOADABLE / folder
        held = self.held(folder)
        if held:
            raise LibraryError(f"{folder}: not empty — it holds {_and(held)}; move or "
                               "trash what is in it first")
        try:
            (d / ".DS_Store").unlink(missing_ok=True)
            d.rmdir()
        except OSError as e:
            raise LibraryError(f"{folder}: not removed ({e})") from e
        self._sync()
        self.say(f"removed the folder {folder}")

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
        loadable patch from a folder one folder down per folder, plan 48), newest
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
                    # would make it a loadable patch (review of PR #117)
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
                    if folder and group.name == LOADABLE:
                        name = f"{folder}/{name}"
                    out.append(Trashed(path, group.name, name,
                                       _when(m["stamp"]) if m else "", folder, old))
        return sorted(out, key=lambda t: (not t.old, _order(t.path), t.path.name),
                      reverse=True)

    def restore_trash(self, item: Trashed) -> str:
        """Put a trashed file back as ``<home>/<group>/<stem><suffix>`` —
        never over a file: the target is created exclusively. When the stem
        is taken (a file of that stem in the group's folder), or for a
        loadable patch the name inside is taken by another listed one, it is
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
        if sub and group == LOADABLE:
            # review of #334: the folder as it is on disk now (APFS folds
            # case), so what is taken there is read from the right place
            sub = self._folder_on_disk(sub) or sub
        filename = f"{m['stem']}{m['suffix']}"
        show = group == PROJECTS
        suffix = PROJECT_SUFFIX if show and filename.endswith(PROJECT_SUFFIX) else ".json"
        stem = filename.removesuffix(suffix)
        # plan 50: ``trash/patches/<group>/`` is a patch of one group — it
        # goes back among that group's (`group_dir`)
        if group == PATCHES and sub and "/" not in sub:
            group, sub = sub, ""
        # only the loadable patches have folders (plan 48): a file a non-preset group
        # kept deeper goes back where that group lists it
        sub = sub if group == LOADABLE else ""
        folder = self.group_dir(self.home, group) / sub if sub else self.group_dir(self.home,
                                                                                  group)
        pre = f"{sub}/" if sub and group == LOADABLE else ""
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
                      if p.parent == folder} if group == LOADABLE else set())
        taken = {slug(s) for s in stems} | names
        renamed = slug(stem) in {slug(s) for s in stems} or (
            group == LOADABLE and slug(name) in names)
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
        if group == LOADABLE and self.warning.startswith(f"{pre}{self._shown(group, name)} is in the trash"):
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

    def _push(self, group: str, label: str) -> None:
        """A load of one group's values: one step on the stack that watches them
        (plan 44 D5b), the meta controller's for a shared meta group, else the deck's."""
        if group in SHARED_META_GROUPS:
            undo.push_meta(label, load=True)
        else:
            undo.push_on(self.reg, label, load=True)

    def is_dirty(self, group: str) -> bool:
        """Have the group's bases moved off the loaded (or default) loadable patch?
        For a document kind: has its signature moved since the last load or
        save (nothing loaded yet is never dirty). Floats compare within
        undo's tolerance (`undo.alike`, plan 16 WP7): the last bits a
        performer leaves in a base it took light no dot."""
        owner = self._owner(group)
        if owner is not None:                # plan 44 D3: the loadable patches' own dot
            return owner.is_dirty()
        kind = self._kinds.get(group)
        ref = self.landed(group)[1]
        if kind is not None:
            return ref is not None and not undo.alike(kind.signature(), ref)
        reg = self._need_reg()
        if ref is None:
            ref = self.resolved(group, {})
        snap = reg.snapshot(group)
        return any(not undo.alike(snap.get(k), v) for k, v in ref.items())

    def reset(self, group: str) -> str | None:
        """Back to the group's default loadable patch (or its fresh values)."""
        name = self.default_name(group)
        if name is not None:
            self.load(group, name)
            return name
        if group in self._kinds:
            return None
        self._need_reg()
        # (the other branch pushes in `load`)
        self._push(group, f"reset {group_word(group)}")
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
                    # the loadable patches every folder down (plan 48), as `_files` lists them
                    # (plan 50: and the patches of one group, a folder down)
                    for f in (self._tree(d)[0] if d.name == LOADABLE else
                              [*d.glob("*.json"), *d.glob("*/*.json")] if d.name == PATCHES
                              else d.glob("*.json")):
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
                    hit.append(f"{group_word(group)}/{name}")
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


# ------------------------------------------------- one deck's view (plan 44 D5a)

class DeckProject(Project):
    """The one show as one deck sees it: every field is the show's (it shares
    the show's `__dict__`), but `lib` is that deck's `DeckLibrary`, so a bank
    verb this object does (a pad on that deck's table) loads, saves and lights
    on that deck. What a deck's `preset.*` params close over, so what a row reaches.

    A load is a meta controller verb (the owner, 2026-11-06, register row 700), the
    named exception to "a row acts only on the `Deck` its player is on": `load_slot`,
    `cycle`, `walk` and `home`, whichever deck's param was pressed, land on the deck
    off air and step from what it holds; nothing on air changes. `meta` (the
    `MetaController`) says where (`row_load`), or why not. No patch can press any
    `preset.*`: `routing.meta_refusal` refuses a patch's row on one at every door. A
    person's save does not change the picture, so it stays on its own deck, as does the panel's load,
    which is the plain `Project`'s and the intentional one. `meta` None (no second
    deck): a load lands on this deck."""

    __slots__ = ("lib", "meta")

    def __init__(self, lib: DeckLibrary):        # never `Project.__init__`: nothing is new
        self.__dict__ = lib.base.project.__dict__
        self.lib = lib
        self.meta = None

    def _landing(self, what: str) -> Project | None:
        """The view a row's load lands on; None when it may not, and that is said."""
        if self.meta is None:
            return self
        where, why = self.meta.row_load()
        if why is None and where is None:     # never this deck: it may be on air (row 700)
            why = "not loaded: there is no deck off air to load"
        if why is not None:
            self.lib.say(warning=f"{what}: {why}")
            return None
        return where

    def _say_loaded(self, where: Project) -> None:
        name = getattr(where._loader(), "current", None)    # the look's own name
        if self.meta is not None and name:
            where.lib.say(status=self.meta.loaded_words(name))

    @property
    def lit(self) -> int:
        # (a press lands off air, so that is the deck a bank pad's light is about)
        where = self.meta.off_air_project() if self.meta is not None else None
        return self.active if where is None else where.active

    def load_slot(self, k: int) -> bool | None:
        if not (0 <= k < len(self.bank) and self.bank[k] is not None):
            return Project.load_slot(self, k)   # loads nothing: it says how to fill it
        where = self._landing(slot_key(k))
        if where is None:
            return None
        done = Project.load_slot(where, k)
        if done:
            self._say_loaded(where)
        return done

    def cycle(self, step: int = 1) -> None:
        where = self._landing("the pads")
        if where is not None:
            Project.cycle(where, step)        # (its `load_slot` says what loaded)

    def walk(self, step: int = 1) -> str | None:
        where = self._landing("the preset list")
        if where is None:
            return None
        name = Project.walk(where, step)
        if name:
            self._say_loaded(where)
        return name

    def home(self) -> bool | None:
        if not self.startup:
            return Project.home(self)           # loads nothing: it says so
        where = self._landing("home")
        if where is None:
            return None
        done = Project.home(where)
        if done:
            self._say_loaded(where)
        return done


class DeckLibrary(Library):
    """The library as one deck sees it: every file, hook and meta controller label is
    the one library's (it shares its `__dict__`), but `presets` and `reg` are
    this deck's, always, with nothing to remember to say. `LoadedPatch.lib` is one,
    so its load, save, new and marks cannot reach another deck, whichever the
    panel is on; the plain `Library` is the panel's view of the same state
    (`Library.pointer`). The loadable patches kind's and load hooks are this deck's too."""

    __slots__ = ("_project", "base", "own")

    def __init__(self, base: Library, loaded_patch=None):   # never `Library.__init__`: nothing is new
        self.__dict__ = base.__dict__
        self.base, self.own = base, loaded_patch
        self._project = DeckProject(self)

    def on_deck(self, loaded_patch=None) -> DeckLibrary:
        """This view, for its first `LoadedPatch` (`Deck.build` makes it before them,
        for the deck's bank params); another's is a view of its own."""
        if loaded_patch is None or self.own is loaded_patch:
            return self
        if self.own is None:
            self.own = loaded_patch
            return self
        return DeckLibrary(self.base, loaded_patch)

    @property
    def loaded_patch(self):
        return self.own if self.own is not None else self.base.loaded_patch

    @property
    def reg(self):
        return self.own.reg if self.own is not None else self.base.reg

    @property
    def project(self) -> DeckProject:
        return self._project

    @property
    def _kinds(self) -> dict[str, DocKind]:
        kinds = self.__dict__["_kinds"]
        return kinds if self.own is None else {**kinds, LOADABLE: self.own.doc_kind}

    @property
    def _load_hooks(self) -> dict[str, Any]:
        hooks = self.__dict__["_load_hooks"]
        return hooks if self.own is None else {**hooks, LOADABLE: self.own._landed}
