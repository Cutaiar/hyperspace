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
  project         the show — ``{"schema": "hyperspace.project/2",
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
                  support, 2026-10-25). Plan 36 T1: ``rig``, the
                  show's own wires — ``{"cut": [{"from", "to"}, …]}``, the
                  bus cables from All outputs into a window this show has
                  cut on GRAPH (``graph.RigWires``); absent, every one
                  stands.

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
  $HYPERSPACE_HOME/presets/<slug>.json       presets
  $HYPERSPACE_HOME/patches/<slug>.json       patches (plan 40)
  $HYPERSPACE_HOME/projects/<slug>.hyp.json  shows
  $HYPERSPACE_HOME/config.toml, bindings.json (a midi_map.json is only
                                 migrated in and read once, routing.py)
  $HYPERSPACE_HOME/bindings/      the old routing presets: made presets
                                 once (plan 13 WP5) and never read again,
                                 so no group (LEGACY_DIRS)
  $HYPERSPACE_HOME/trash/<group>/<slug>.<date>-<time>.json
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

Loading a preset fills ids it doesn't name from the group's *default*
preset (DEFAULT_NAMES, else one called "default", else the values the
objects were constructed with), so a preset is the same state whatever it
lands on; ids the registry doesn't know are reported in ``warning`` and
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
from .graphmigrate import renamed_layout, retired
from .palettecompat import palette_slice
from .params import (
    F_KEYS,
    PERFORMANCE_GROUPS,
    SESSION_GROUPS,
    UNITS,
    UNITS_KEY,
    Registry,
    is_instance_id,
    pan_world,
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
PRESETS = "presets"       # the presets' group, a document kind (preset.py)
# <root>/desk/<slug>.json (plan 24 C3): the desk templates — named sets of
# preset-layer rows a preset's desk can start from (`desk_template`,
# preset.py `expand_desk`). A module-preset group in the library's tree,
# which [library] path shares (plan 25). Its files are their own format,
# DESK_SCHEMA, read only through `desk_template`: the `desk` *param* group
# (desk.slew, desk.pad.*) has no module-preset strip, and a template is
# never applied as its module preset
DESK = "desk"
DESK_SCHEMA = "hyperspace.desk/1"
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
PROJECT_SCHEMA = "hyperspace.project/2"
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
RIG = "rig"            # plan 36 T1: a show's own wires (`graph.RigWires`)


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


def next_name(base: str | None, taken: set[str]) -> str:
    """A name for a new preset grown from `base`, the loaded preset's name
    (plan 15 WP4, fork 16): the first ``"<stem> <n>"`` whose slug is not in
    `taken`, a set of slugs. A base that ends in whitespace and a number
    after a non-empty stem counts on from that number (``TRIP 2`` →
    ``TRIP 3``); any other is its own stem and counting starts at 2
    (``TRIP`` → ``TRIP 2``, ``2001`` → ``2001 2``). With no base the stem
    is ``PRESET`` and counting starts at 1."""
    base = (base or "").strip()
    if not base:
        stem, n = "PRESET", 1
    else:
        m = re.fullmatch(r"(.*\S)\s+(\d+)", base, re.DOTALL)
        stem, n = (m.group(1), int(m.group(2)) + 1) if m else (base, 2)
    while slug(f"{stem} {n}") in taken:
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


def to_trash(path: Path, root: Path) -> Path | None:
    """Copy `path` — a preset file about to be overwritten or deleted — to
    ``<root>/trash/<folder>/<stem>.<YYYYMMDD-HHMMSS><suffix>``, `<folder>`
    being the file's own folder name (``presets``, ``band``, ``fx``…). A
    name taken in the same second gets ``-2``, ``-3``, …; the copy is
    created exclusively, so nothing in the trash is ever overwritten.
    Returns the path written, or None when the copy failed (said on
    stderr): the caller decides what that means — a save goes on and
    warns, a delete is refused."""
    folder = root / TRASH / path.parent.name
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

    path: Path          # <home>/trash/presets/trip-3.20261004-011203.json
    group: str          # its folder: "presets", "fx", "projects", …
    name: str           # the name inside the file, else its stem
    when: str           # "Oct 4 01:12", from the stamp in the file name ("" if none)


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
}
# no project 1 → 2 step: a schema-1 show (an inline theme bank) is refused
# (`Project._take`) — no old-schema support since 2026-10-25
CURRENT = {"hyperspace.preset": 1, "hyperspace.project": 2}


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
        # plan 36 T1: the rig's own wires — the bus cables from All outputs
        # into each window, which this show has cut (`graph.RigWires`) — and
        # those as on disk; the renderer reads `rig` (its `rig_source`)
        self.rig = RigWires()
        self._saved_rig = RigWires()

    # ---- documents ----

    def _take(self, doc: dict, path: Path | None, where: str = "project") -> None:
        if doc.get("schema") == PROJECT_V1:
            raise LibraryError(f"{where} is a schema-1 show, which this build does not read "
                               "(no old-schema support, 2026-10-25)")
        doc = migrate_doc(doc, "hyperspace.project")
        self.name = str(doc.get("name") or (path.name[: -len(PROJECT_SUFFIX)] if path
                                            else UNTITLED))
        self.note = str(doc.get("note") or "")
        self.path = path
        # the file's own name, which a launch finds the show by (`stem`)
        self._stem = where[: -len(PROJECT_SUFFIX)] if where.endswith(PROJECT_SUFFIX) else None
        from .routing import renamed_session  # the stick spring's old ids, as today's
        self.session = renamed_session(dict(doc.get("session") or {}))
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
        self._saved_layout = copy.deepcopy(self.layout)
        self.rig = self._saved_rig = RigWires.read(doc.get(RIG))

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
        rig = getattr(self, "rig", RigWires()).to_json()
        if rig:                          # plan 36 T1; every cable standing writes none
            doc[RIG] = rig
        return doc

    def mark(self) -> tuple:
        """The show as held, opaque, for an undo to hand back (`remark`):
        name, note, path, stem, session, modules, bank, startup and the
        bank and startup as on disk — copies, so a later edit of the live
        show never reaches a mark; then the GRAPH page's positions of the
        rig's nodes, and (plan 36 T1) the rig's wires, live and as on disk
        (immutable: held as they are)."""
        return (self.name, self.note, self.path, getattr(self, "_stem", None),
                copy.deepcopy(self.session), copy.deepcopy(self.modules), list(self.bank),
                self.startup, (list(self._saved[0]), self._saved[1]),
                # plan 28 N2: the GRAPH page's positions of the rig's nodes
                copy.deepcopy(getattr(self, "layout", {})),
                copy.deepcopy(getattr(self, "_saved_layout", {})),
                getattr(self, "rig", RigWires()), getattr(self, "_saved_rig", RigWires()))

    # the mark's fixed head, and where its later parts start
    MARK_LAYOUT = 9          # the GRAPH page's layout, and as on disk (plan 28 N2)
    MARK_RIG = 11            # the rig's wires, and as on disk (plan 36 T1)

    def remark(self, mark: tuple) -> None:
        """Put back what `mark()` returned: the show's own fields, nothing
        else — no file is read or written, no value lands (undo.py does
        that), and `active` is the caller's to recompute (`Marks.put`)."""
        (self.name, self.note, self.path, self._stem,
         session, modules, bank, self.startup, saved) = mark[:self.MARK_LAYOUT]
        if len(mark) > self.MARK_LAYOUT:   # plan 28 N2: the show's layout, and as on disk
            self.layout = copy.deepcopy(mark[self.MARK_LAYOUT])
            self._saved_layout = copy.deepcopy(mark[self.MARK_LAYOUT + 1])
        if len(mark) > self.MARK_RIG:      # plan 36 T1: the rig's wires, and as on disk
            self.rig, self._saved_rig = mark[self.MARK_RIG], mark[self.MARK_RIG + 1]
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
        cur = self.lib.current(PRESETS)
        if cur is None:                               # nothing loaded: no slot is lit
            self.active = -1
        elif not 0 <= self.active < len(self.bank) or self.bank[self.active] != cur:
            self.active = self.bank.index(cur) if cur in self.bank else -1

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
        if presets is None or lib.path_of(PRESETS, name) is None:
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
        # is the file a save of "TRIP 2" would write over
        taken = lib._taken(PRESETS) | {slug(n) for n in self.bank if n}
        name = next_name(lib.current(PRESETS), taken)
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
        if self.lib.path_of(PRESETS, name) is None:
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
        if lib.path_of(PRESETS, name) is None:
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
        if self._loader() is not None and lib.path_of(PRESETS, name) is not None:
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
        ``<file>.bak-v2-spring``; no backup, no write."""
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
        self.path = path
        _write_json(self.path, doc)
        self.lib._sync(self.path)
        self._saved = (list(self.bank), self.startup)
        self._saved_layout = copy.deepcopy(getattr(self, "layout", {}))
        self._saved_rig = getattr(self, "rig", RigWires())
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
                or getattr(self, "layout", {}) != getattr(self, "_saved_layout", {})
                or getattr(self, "rig", RigWires()) != getattr(self, "_saved_rig", RigWires()))

    def _held_back(self) -> dict:
        """The session's settings of node instances the registry lacks now
        (`ghost.2.*` while no preset's graph holds the second hands node,
        plan 26 A4): kept by a save and never counted as an edit."""
        reg = self.lib.reg
        return {pid: v for pid, v in (self.session or {}).items()
                if is_instance_id(pid) and (reg is None or pid not in reg)}


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
        the media channels' bins (plan 32, `Presets.media`) and the GRAPH
        page's groups (plan 40 T2, `Presets.groups`)."""
        lib, pre = self.lib, self.lib.presets
        gs = getattr(pre, "graph", None)
        return (lib.project.mark(), self.lands(),
                {g: copy.deepcopy(hook()) for g, hook in lib._extra_hooks.items()},
                (getattr(pre, "note", ""), list(getattr(pre, "notes", ())),
                 list(getattr(pre, "desk_notes", ()))),
                gs.mark() if gs is not None else None,
                copy.deepcopy(getattr(pre, "layout", None) or {}),
                self._bins(pre),
                copy.deepcopy(getattr(pre, "groups", None) or []))

    @staticmethod
    def _bins(pre):
        """The media channels' bins (plan 32), None without them."""
        media = getattr(pre, "media", None)
        return media.to_json() if media is not None else None

    def lands(self) -> dict:
        """{group: landed} — every group's name, reference and re-apply
        road, by reference: cheap enough to read every frame."""
        lib = self.lib
        return {g: lib.landed(g) for g in {*lib._current, *lib._loaded, *lib._adopted}}

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
            # file until it is saved; so do the rig's wires (plan 36 T1: the
            # undo of a bus cable cut on GRAPH)
            pr.layout = copy.deepcopy(show[Project.MARK_LAYOUT])
            if len(show) > Project.MARK_RIG:
                pr.rig = show[Project.MARK_RIG]
        for group in {*lib._current, *lib._loaded, *lib._adopted} - set(landed):
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
        """slug → path, every file of the group's folder."""
        out: dict[str, Path] = {}
        for root in self._roots():
            d = root / group
            if d.is_dir():
                out.update((p.name[:-5], p) for p in d.glob("*.json"))
        return out

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

    def _index(self, group: str) -> dict[str, Path]:
        """display name → path; a name is also reachable by its slug.

        Two files of one folder with the same name inside — a cloud
        client's conflict copy, ``hi-frek (Dan's conflicted copy …).json``
        beside ``hi-frek.json`` (plan 25) — are both listed: the file whose
        stem is the name's slug keeps the name (else the lower stem), and
        the other is listed under its file stem, to be loaded, renamed or
        deleted."""
        out: dict[str, Path] = {}
        for p in self._files(group).values():
            name = self._name_of(p)
            prev = out.get(name)
            if prev is not None:
                want = slug(name)
                keep, other = ((prev, p) if prev.name[:-5] == want
                               else (p, prev) if p.name[:-5] == want
                               else tuple(sorted((prev, p), key=lambda q: q.name)))
                out[name] = keep
                out.setdefault(other.name[:-5], other)
                continue
            out[name] = p
        return out

    def path_of(self, group: str, name: str) -> Path | None:
        idx = self._index(group)
        return idx.get(name) or self._files(group).get(slug(name))

    def list(self, group: str) -> list[str]:
        """Every preset of the group by name, case folded — the PRESETS
        page's list, the strip's arrows, the pad's walk."""
        return sorted(self._index(group), key=str.lower)

    def _taken(self, group: str) -> set[str]:
        """The slugs a new file of the group may not take: every file stem
        in the folder and every listed name — on a filesystem that folds
        case `Trip-2.json` is the file a save of "TRIP 2" would write over
        (`save_new`, `rename`)."""
        return ({slug(s) for s in self._files(group)}
                | {slug(n) for n in self.list(group)})

    def still_named(self, name: str, path: Path | None = None) -> list[str]:
        """What in the open show still names the preset `name` (or, given,
        the file at `path`): its slots (``F6``, ``slot 12``) and its
        ``startup``."""
        pr, key = self.project, slug(name)

        def names(n: str | None) -> bool:
            return bool(n) and (n == name or slug(n) == key
                                or (path is not None and self.path_of(PRESETS, n) == path))
        out = [slot_key(k) for k, n in enumerate(pr.bank) if names(n)]
        if names(pr.startup):
            out.append("the startup preset")
        return out

    def read(self, group: str, name: str) -> dict:
        path = self.path_of(group, name)
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
            if old != text and to_trash(path, self.home) is None:
                self.say(warning=f"{PATCHES}/{path.name}: overwritten — the old file could "
                                 "not be kept in the trash")
        _write_text(path, text)
        self._sync(path)
        self.say(f"{PATCHES}: saved {name}")
        return path

    def desk_template(self, name: str) -> dict:
        """The desk template `name` (plan 24 C3): its file under
        ``<root>/desk/``, as ``{"schema": DESK_SCHEMA, "name", "note"?, "desk":
        [row, …]}`` — the rows in a preset's ``desk`` form (no ``layer``).
        A template that is not there, or not that format, raises
        LibraryError; the caller says so and goes on without it."""
        path = self.path_of(DESK, name)
        if path is None:
            raise LibraryError(f"no desk template {name!r}")
        doc = copy.deepcopy(self._doc(path))
        if doc.get("schema") != DESK_SCHEMA:
            raise LibraryError(f"{path.name}: schema {doc.get('schema')!r} is not "
                               f"{DESK_SCHEMA}")
        rows = doc.get("desk")
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise LibraryError(f"{path.name}: its desk is not a list of rows")
        return doc

    # ---- defaults & values ----

    def default_name(self, group: str) -> str | None:
        if group == DESK:          # its folder holds desk templates, never module presets:
            return None            # a template named "default" is no group default
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
        changes on disk."""
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
        return (self._current.get(group), self._loaded.get(group), self._adopted.get(group))

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
        return self._current.get(group)

    def load(self, group: str, name: str) -> list[str]:
        """Apply a preset; returns the ids it names that this registry lacks."""
        if group not in self._kinds:
            self._need_reg()
        doc = self.read(group, name)
        return self._apply_doc(group, name, doc, path=self.path_of(group, name))

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
            self._landed(group, doc.get("name") or name, kind.signature())
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
            self.say(f"{group}: {self._current[group]}")
        hook = self._load_hooks.get(group)
        if hook is not None:
            hook(self._current[group])
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
        path = self.path_of(group, name) or self.home / group / f"{slug(name)}.json"
        kind = self._kinds.get(group)
        text = (kind.text(doc) if kind is not None and kind.text is not None
                else _json_text(doc))
        if path.is_file():
            try:
                old = path.read_text()
            except (OSError, ValueError):
                old = None                               # unreadable as text: keep it anyway
            if old != text and to_trash(path, self.home) is None:
                self.say(warning=f"{group}/{path.name}: overwritten — the old file could "
                                 "not be kept in the trash")
        _write_text(path, text)
        self._sync(path)
        self._landed(group, name, kind.signature() if kind is not None
                     else self.resolved(group, doc["values"]))
        self.say(f"{group}: saved {name}")
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
        if to_trash(path, self.home) is None:
            raise LibraryError(f"{path.name}: not deleted — it could not be kept in the "
                               f"trash ({self.home / TRASH})")
        try:
            path.unlink()
        except OSError as e:
            raise LibraryError(f"{path.name}: {e}") from e
        self._sync(path)
        if self._current.get(group) == name and self.path_of(group, name) is None:
            self._landed(group, None, None)
        if group == PRESETS:
            # what still points at it (plan 19 WP4): the open show's slots and
            # startup — not cleared for the owner, so a restore to the old
            # name makes them work again
            still = self.still_named(name)
            if still:
                self.say(warning=f"{name} is in the trash — {_and(still)} still "
                                 f"name{'s' if len(still) == 1 else ''} it; restore it from "
                                 "the trash, or clear the slot")
            else:
                self.say(f"{name} is in the trash — the PRESETS page's trash can restore it")
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
        path = self.path_of(group, old)
        if path is None:
            raise LibraryError(f"no preset {old!r}")
        new = (new or "").strip()
        if not new:
            raise LibraryError("a preset needs a name")
        stem = path.name[:-5]
        if new == old:
            return path
        doc = _read_json(path)
        mine = {stem} | {slug(n) for n, p in self._index(group).items() if p == path}
        in_place = slug(new) == stem
        # `_taken` less this preset's own stem and name
        taken = ({slug(s) for s, p in self._files(group).items() if p != path}
                 | {slug(n) for n, p in self._index(group).items() if p != path})
        if slug(new) in taken:
            raise LibraryError(f"{new}: that name is taken — pick another")
        kind = self._kinds.get(group)
        doc["name"] = new
        text = (kind.text(doc) if kind is not None and kind.text is not None
                else _json_text(doc))
        dst = path if in_place else self.home / group / f"{slug(new)}.json"
        if in_place:
            # 2–3 in one: keep the old text, then write over it
            if to_trash(path, self.home) is None:
                raise LibraryError(f"{path.name}: not renamed — it could not be kept in the "
                                   f"trash ({self.home / TRASH})")
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
            if to_trash(path, self.home) is None:          # 3.
                dst.unlink(missing_ok=True)
                raise LibraryError(f"{path.name}: not renamed — it could not be kept in the "
                                   f"trash ({self.home / TRASH})")
            try:
                path.unlink()
            except OSError as e:
                dst.unlink(missing_ok=True)
                raise LibraryError(f"{path.name}: not renamed ({e})") from e
        self._sync(path, dst)                              # 4.
        cur = self._current.get(group)
        if cur is not None and (cur == old or slug(cur) in mine):
            self._landed(group, new, self._loaded.get(group))
            hook = self._load_hooks.get(group)
            if hook is not None:
                hook(new)
        if group == PATCHES:
            self.say(f"renamed {old} → {new}")
            return dst
        done, left = self._repoint(old, new, mine)         # 5.
        self.project.follow()                              # 6.
        self.say(f"renamed {old} → {new} ({done} show{'' if done == 1 else 's'} updated)")
        if left:
            self.say(warning=f"renamed {old} → {new}; not updated: {', '.join(left)}")
        return dst

    def _repoint(self, old: str, new: str, mine: set[str]) -> tuple[int, list[str]]:
        """Step 5 of `rename`: every user show naming the old preset (by its
        name, or a slug of it or of its file stem) names the new one, each
        copied to the trash first. Returns (shows written, shows left as
        they were with why)."""

        def hit(n) -> bool:
            return isinstance(n, str) and bool(n) and (n == old or slug(n) in mine)

        pr, done, left = self.project, 0, []
        for show in sorted((self.home / PROJECTS).glob(f"*{PROJECT_SUFFIX}")):
            label = show.name[: -len(PROJECT_SUFFIX)]
            if pr.path is not None and show == pr.path:
                if not (any(hit(n) for n in pr.bank) or hit(pr.startup)):
                    continue
                if to_trash(show, self.home) is None:
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
            if to_trash(show, self.home) is None:
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

    def _in_trash(self, path: Path) -> bool:
        """Does `path` — its symlinks and any ``..`` resolved — lie under
        ``<home>/trash/``, one folder down? The guard on every file the
        trash's view restores or deletes."""
        try:
            root = (self.home / TRASH).resolve()
            real = path.resolve()
        except OSError:
            return False
        return real.parent.parent == root

    def trash(self) -> list[Trashed]:
        """Every file under ``<home>/trash/<folder>/``, newest first — what
        "empty" removes, and nothing else: what you see is what goes."""
        root = self.home / TRASH
        if not root.is_dir():
            return []
        out = []
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            for path in folder.iterdir():
                # only what `to_trash` writes: <stem>.<stamp>[-n]<suffix>, never a
                # dotfile — a Finder `.DS_Store` is not the owner's, and a restore
                # would make it a preset (review of PR #117)
                m = _TRASHED.fullmatch(path.name)
                if (m is None or path.name.startswith(".")
                        or not (path.is_file() or path.is_symlink())):
                    continue
                stem = m["stem"]
                if stem.endswith(PROJECT_SUFFIX[:-5]) and folder.name == PROJECTS:
                    stem = stem[: -len(PROJECT_SUFFIX[:-5])]
                name = stem
                if path.is_file() and self._in_trash(path):
                    try:
                        name = str(_read_json(path).get("name") or stem)
                    except LibraryError:
                        pass
                out.append(Trashed(path, folder.name, name, _when(m["stamp"]) if m else ""))
        return sorted(out, key=lambda t: (_order(t.path), t.path.name), reverse=True)

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
        if not path.is_file() or not self._in_trash(path):
            raise LibraryError(f"{path.name}: not in the trash ({self.home / TRASH})")
        m = _TRASHED.fullmatch(path.name)
        if m is None or path.name.startswith("."):
            raise LibraryError(f"{path.name}: not restored — not a file the trash kept")
        filename = f"{m['stem']}{m['suffix']}"
        show = item.group == PROJECTS
        suffix = PROJECT_SUFFIX if show and filename.endswith(PROJECT_SUFFIX) else ".json"
        stem = filename.removesuffix(suffix)
        folder = self.home / item.group
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
            stems = set(self._files(item.group))
            names = ({slug(n) for n in self.list(item.group)}
                     if item.group == PRESETS else set())
        taken = {slug(s) for s in stems} | names
        renamed = slug(stem) in {slug(s) for s in stems} or (
            item.group == PRESETS and slug(name) in names)
        if renamed:
            if doc is None:
                raise LibraryError(f"{path.name}: not restored — {stem} is taken and the file "
                                   "would not read, so it cannot be renamed")
            new = next_name(name, taken)
            doc["name"] = new
            stem = slug(new)
            kind = self._kinds.get(item.group)
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
        if item.group == PRESETS and self.warning.startswith(f"{name} is in the trash"):
            self.warning = ""                              # what × said is no longer so
        now = str(doc["name"]) if renamed else name
        what = f"show {now}" if show else now
        if renamed:
            self.say(f"restored as {what} — {name} is taken")
        else:
            self.say(f"restored {what}" + (" — it is in the show list" if show else ""))
        try:
            path.unlink()                                  # only after the write
        except OSError as e:
            self.say(warning=f"restored {now}; its copy stays in the trash ({e})")
        return now

    def empty_trash(self) -> int:
        """Delete every file `trash()` lists, and then the trash's folders
        left empty — the one delete in the app that keeps no copy (the
        panel asks twice). A path that does not resolve under
        ``<home>/trash/`` (a symlink out, a ``..``) is refused and left,
        and said. Returns how many files went."""
        self.writable()
        gone, refused = 0, []
        for item in self.trash():
            path = item.path
            if path.is_symlink() or not self._in_trash(path):
                refused.append(path.name)
                continue
            try:
                path.unlink()
                gone += 1
            except OSError as e:
                refused.append(f"{path.name} ({e})")
        root = self.home / TRASH
        if root.is_dir():
            for folder in root.iterdir():
                if folder.is_dir() and not folder.is_symlink():
                    try:
                        folder.rmdir()                     # only when it is empty
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
                    for f in d.glob("*.json"):
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
            for group, name in list(self._current.items()):
                if name is not None and self.path_of(group, name) in changed:
                    reapply = self._adopted.get(group)
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
