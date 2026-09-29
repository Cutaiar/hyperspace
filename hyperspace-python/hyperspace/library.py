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
                  band presets are also the analyzer's *scenes*: the scene
                  combo reads them (``read``, or ``factory_doc`` with no
                  library) and ``adopt``s the one it landed; a strip load
                  tells the combo through ``on_load`` (control.py).
  project         everything — ``{"schema": "hyperspace.project/1",
                  "name", "values": <performance snapshot>, "session":
                  <session snapshot>, "modules": {group: name | {"name",
                  "values", …}}, "bank": [8 × {"name", "values"} |
                  null]}``, in a ``*.hyp.json`` file (params.PARTS is the
                  split; an older file with no ``session`` loads, its
                  session ids read out of ``values``). The F1–F8 theme
                  bank is the project's (``Project.load_slot`` /
                  ``save_slot``): emulator-style save states of the
                  performance, macros included, which never move a
                  session param. A module the project names by a preset
                  that carries a ``layout`` gets that layout back on
                  load, the same road a strip load takes. A project never
                  carries a routing preset: the live table is
                  ``<home>/bindings.json``, one file for the rig.

A third kind of document is *not* the library's own format but goes
through the same doors: a **document kind** registered with ``kind()``
— the routing presets, ``hyperspace.bindings/2`` under ``bindings/``,
which the router loads and writes (``Router.apply_doc`` /
``preset_doc``; ``Library.routing`` wires it). For such a group the
library does the file half — list, user-shadows-factory, load / save as
/ delete, the dirty dot, the watch — and the kind's hooks do the
document half: ``load(doc, path)`` applies it, ``document(name)`` is
what a save writes, ``signature()`` is what ``is_dirty`` compares. One
strip (ui_presets.py) then serves every group.

Library layout — the same tree in two places, the user's shadowing the
factory's file of the same name:

  hyperspace/library/<group>/<slug>.json     factory, read-only, in the wheel
  $HYPERSPACE_HOME/<group>/<slug>.json       user (default ~/Hyperspace)
  $HYPERSPACE_HOME/projects/<slug>.hyp.json  user projects
  $HYPERSPACE_HOME/config.toml, bindings.json (a midi_map.json is only
                                 migrated in and read once, routing.py)

``home()`` is the one resolver for that folder (config.py and the binding
table path go through it). On the first run the working-directory ``config.toml``
and ``midi_map.json`` are copied in and a legacy ``presets.json`` theme
bank becomes the user's default project — originals are left alone.

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
import json
import os
import re
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .params import PLANES, SESSION_GROUPS, Registry, part_of

SLOTS = 8                 # the F1–F8 theme bank
BINDINGS = "bindings"     # the routing presets' group: the one document kind (routing.PRESET_DIR)
HOME_ENV = "HYPERSPACE_HOME"
DEFAULT_HOME = Path("~/Hyperspace")
FACTORY = Path(__file__).with_name("library")

PRESET_SCHEMA = "hyperspace.preset/1"
PROJECT_SCHEMA = "hyperspace.project/1"
PROJECT_SUFFIX = ".hyp.json"
PROJECTS = "projects"
DEFAULT_PROJECT = "default"
UNTITLED = "untitled"

# the preset a group resets to; any other group uses one named "default"
# if it has one, else the values its objects were built with
DEFAULT_NAMES = {"band": "Balanced"}

# working-directory files that move into the library home on first run
MIGRATED_FILES = ("config.toml", "midi_map.json")
LEGACY_BANK = "presets.json"


class LibraryError(Exception):
    pass


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
    """First-run move of config, MIDI map and theme bank; returns what moved.

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
    src, dst = cwd / LEGACY_BANK, root / PROJECTS / f"{DEFAULT_PROJECT}{PROJECT_SUFFIX}"
    if src.is_file() and not dst.exists():
        try:
            doc = _read_json(src)
            bank = [legacy_slot(s) if s else None for s in doc.get("slots", [])[:SLOTS]]
        except LibraryError as e:
            done.append(f"library: {src} not migrated ({e})")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            _write_json(dst, {"schema": PROJECT_SCHEMA, "name": DEFAULT_PROJECT,
                              "values": {}, "modules": {}, "bank": bank})
            done.append(f"library: theme bank {src} → project {dst}")
    return done


# ---------------------------------------------------------------- files

def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "untitled"


def _read_json(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise LibraryError(f"{path.name}: {e}") from e
    if not isinstance(doc, dict):
        raise LibraryError(f"{path.name}: not a JSON object")
    return doc


def _write_json(path: Path, doc: dict) -> None:
    _write_text(path, json.dumps(doc, indent=1) + "\n")


def _write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    except OSError as e:
        raise LibraryError(f"{path.name}: {e}") from e


# ---- versioning: schema "<kind>/<n>"; each step lifts a doc one version ----

MIGRATIONS: dict[tuple[str, int], Any] = {
    # ("hyperspace.preset", 1): lambda doc: {...},   # 1 → 2, when there is one
}
CURRENT = {"hyperspace.preset": 1, "hyperspace.project": 1}


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
    tree and goes through its doors (the routing presets). `schema` is
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


def factory_doc(group: str, name: str, factory: Path = FACTORY) -> dict:
    """A factory preset by name, without a Library: the file in the wheel,
    lifted to the current schema. The scene combo reads its scenes this
    way when no library is attached (control.py); with one, ``Library.read``
    is the same file with the user's shadow honoured."""
    path = factory / group / f"{slug(name)}.json"
    if not path.is_file():
        raise LibraryError(f"{group}: no factory preset {name!r}")
    return migrate_doc(_read_json(path), "hyperspace.preset")


# ---- the pre-registry theme format (presets.json) → {name, values} ----

_LEGACY_VIEW = {
    "shape": "view.shape", "speed": "view.speed", "depth4": "view.depth4",
    "bright": "view.bright", "points": "view.points", "lines": "view.lines",
    "playing": "view.rotate", "faces": "view.faces", "instances": "view.instances",
    "inst_motion": "view.inst_motion", "inst_amp": "view.inst_amp",
    "inst_rate": "view.inst_rate", "pattern": "view.pattern",
    "pattern_mix": "view.pattern_mix", "bmp_file": "view.bmp_file",
    "bmp_alpha": "view.bmp_alpha", "bmp_scale": "view.bmp_scale",
    "bmp_mode": "view.bmp_mode", "bmp_amp": "view.bmp_amp", "bmp_rate": "view.bmp_rate",
    "yaw": "camera.yaw", "pitch": "camera.pitch", "zoom": "camera.zoom",
}
_LEGACY_LISTS = {
    "planes": [f"view.plane.{n}" for n in PLANES],
    "pan": ["camera.pan.x", "camera.pan.y"],
    "rate": [f"rot.rate.{n}" for n in PLANES],
    "pattern_mod": [f"pattern.mod.{k}" for k in range(8)],
}


def legacy_slot(slot: dict) -> dict:
    """A presets.json theme as a bank slot: {name, values} keyed by param id."""
    values: dict[str, Any] = {}
    for key, v in slot.get("view", {}).items():
        if key in _LEGACY_VIEW:
            values[_LEGACY_VIEW[key]] = v
        elif key in _LEGACY_LISTS:
            values.update(zip(_LEGACY_LISTS[key], v))
    if "scene" in slot:
        values["scene.select"] = slot["scene"]
    for i, band in enumerate(slot.get("bands", [])):
        for key, v in band.items():
            values[f"band.{i}.{key}"] = v
    for key, v in slot.get("master", {}).items():
        values[f"master.{key}"] = v
    out = {"name": slot.get("name", ""), "values": values}
    if slot.get("note"):
        out["note"] = slot["note"]
    return out


# ---------------------------------------------------------------- project

class Project:
    """The open project: its file (None until saved), its sections, and
    the F1–F8 theme bank.

    ``values`` / ``session`` / ``modules`` / ``bank`` are what the *file*
    holds; only ``save()`` refreshes ``values``, ``session`` and
    ``modules`` from the live state. ``write()`` puts the in-memory
    document back on disk as it is — that is what a theme-slot save uses,
    so F-key saves persist without turning the whole project into a
    snapshot of the moment.

    The file's state is split by params.PARTS (plan 13 §4, D9): ``values``
    is the performance part (the look, the LFOs, the macros) and
    ``session`` the session part (tempo, hands, the analyzer, output). An
    older file with no ``session`` key, whose ``values`` held both, is
    split in memory when it is read, and both parts restore on load.

    A theme (one of the eight slots) is a save state of the performance:
    ``snapshot(part="performance")``, macros included. Loading one cuts the
    whole look over in a single frame. A slot restores the performance
    modules it names, whole: every id in a group the slot mentions is set,
    from the slot or else from the group's defaults, so a theme is the same
    state whatever it lands on, while a group it never mentions is left
    alone. A slot never moves a session param: an id it names there (the
    house themes and party slots set ``scene.select``) stays in the file
    but a load ignores it, so a theme no longer resets a tapped BPM or the
    band scene. Rotation phases are never in a slot: a theme changes the
    look, not where the spin is. Empty slots come back seeded with the
    eight house moods (hyperspace/library/projects/default.hyp.json).
    """

    def __init__(self, lib: Library):
        self.lib = lib
        self.name = DEFAULT_PROJECT
        self.path: Path | None = None
        self.values: dict[str, Any] = {}      # the performance part
        self.session: dict[str, Any] = {}     # the session part
        self.modules: dict[str, Any] = {}
        self.bank: list[dict | None] = [None] * SLOTS
        self.active = -1          # last theme slot loaded, -1 until one is
        self.bank_error = ""

    # ---- documents ----

    def _take(self, doc: dict, path: Path | None) -> None:
        doc = migrate_doc(doc, "hyperspace.project")
        self.name = str(doc.get("name") or (path.name[: -len(PROJECT_SUFFIX)] if path
                                            else UNTITLED))
        self.path = path
        # an older file's `values` held the session ids too: they move to
        # `session` here, so both parts restore and the next save splits them
        self.values, self.session = {}, dict(doc.get("session") or {})
        for pid, v in (doc.get("values") or {}).items():
            if self._is_session(pid):
                self.session.setdefault(pid, v)
            else:
                self.values[pid] = v
        self.modules = dict(doc.get("modules") or {})
        bank = list(doc.get("bank") or [])[:SLOTS]
        bank += [None] * (SLOTS - len(bank))
        # an empty slot is seeded from the factory bank, as it always was
        seeds = self.lib.factory_bank()
        self.bank = [s if s else seeds[k] for k, s in enumerate(bank)]

    def _is_session(self, pid: str) -> bool:
        """Is this id in the session part? By its param's group once the
        registry is attached; before that (the default project is read in
        Library.__init__) by its id's first segment, which is the group for
        every persisted param (tests/test_params.py)."""
        reg = self.lib.reg
        if reg is not None and pid in reg:
            return part_of(reg[pid]) == "session"
        return pid.partition(".")[0] in SESSION_GROUPS

    def _performance(self, values: dict[str, Any]) -> dict[str, Any]:
        """`values` less its session ids (ids nobody knows stay, to be reported)."""
        return {pid: v for pid, v in values.items() if not self._is_session(pid)}

    def to_doc(self) -> dict:
        return {"schema": PROJECT_SCHEMA, "name": self.name, "values": self.values,
                "session": self.session, "modules": self.modules, "bank": self.bank}

    def _apply(self) -> list[str]:
        """Push the document's state into the registry; returns unknown ids.
        A module's `layout` lands first (a project saved on eight bands
        comes back with eight, audit L8), then the project's own values —
        the live state as saved, edits included: the session part, then
        the performance part — and each module is
        recorded as the group's current preset, the reference its dirty
        dot compares against, the way a strip load records it."""
        lib = self.lib
        lib._current.clear()
        lib._loaded.clear()
        lib._adopted.clear()
        docs: list[tuple[str, str, dict | None]] = []
        for group, ref in self.modules.items():
            if group in lib._kinds or group == BINDINGS:   # never carried; an old file's is ignored
                continue
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
        if self.values:
            missing += lib.restore(self.values)
        # ids the file lacks (the macros, in a file from before plan 13 WP1;
        # a param added since) take the state this load left, so an
        # untouched project is not dirty the moment it opens
        for part, held in (("performance", self.values), ("session", self.session)):
            for pid, v in (lib.reg.snapshot(part=part) if lib.reg is not None else {}).items():
                held.setdefault(pid, v)
        for group, name, doc in docs:
            vals = (lib.reg.snapshot(group) if doc is None
                    else lib.resolved(group, doc.get("values") or {}))
            lib._landed(group, name, vals)
            hook = lib._load_hooks.get(group)
            if hook is not None:
                hook(name)
        self.active = -1
        return missing

    # ---- the theme bank: performance save states inside the project ----

    @property
    def slots(self) -> list[dict | None]:
        return self.bank

    def capture(self, name: str) -> dict[str, Any]:
        return {"name": name, "values": self.lib.reg.snapshot(part="performance")}

    def save_slot(self, k: int) -> None:
        """⇧F<k+1>: the surface into slot k, and the project file with it."""
        if not 0 <= k < SLOTS or self.lib.reg is None:
            return
        old = self.bank[k]
        name = old["name"] if old else f"THEME {k + 1}"
        self.bank[k] = self.capture(name)
        self.active = k
        try:
            self.write()
            self.bank_error = ""
        except LibraryError as e:                     # a full disk must not stop the show
            self.bank_error = f"themes: {e}"

    def load_slot(self, k: int) -> None:
        """F<k+1>: slot k onto the surface, whole per performance group it
        names. Its session ids (a house theme's ``scene.select``) are ignored."""
        if not 0 <= k < SLOTS or self.bank[k] is None or self.lib.reg is None:
            return
        values = self._performance(self.bank[k].get("values") or {})
        lib, reg = self.lib, self.lib.reg
        groups = {reg[pid].group for pid in values if pid in reg}
        merged: dict[str, Any] = {}
        for g in groups:
            merged.update(lib.defaults(g))
        merged.update(values)
        missing = lib.restore(merged)
        lib.report(missing, self.bank[k]["name"])
        self.active = k

    def cycle(self, step: int = 1) -> None:
        """Flip to the next saved slot — the pad's and the APC's theme button."""
        filled = [k for k, s in enumerate(self.bank) if s is not None]
        if not filled:
            return
        if self.active in filled:
            k = filled[(filled.index(self.active) + step) % len(filled)]
        else:
            k = filled[0]
        self.load_slot(k)

    # ---- API ----

    def list(self) -> list[str]:
        """Every project by name: the factory ones and the user's, a user
        file of the same name shadowing the factory's (as every group does)."""
        names = {p.name[: -len(PROJECT_SUFFIX)]
                 for root in self.lib._roots()
                 for p in (root / PROJECTS).glob(f"*{PROJECT_SUFFIX}")}
        return sorted(names)

    def path_for(self, name: str) -> Path:
        return self.lib.home / PROJECTS / f"{slug(name)}{PROJECT_SUFFIX}"

    def load(self, name: str | Path) -> list[str]:
        """Open a project by name (user library) or path; returns unknown ids."""
        lib = self.lib
        if isinstance(name, Path) or str(name).endswith(PROJECT_SUFFIX):
            path = Path(name)
        else:
            path = self.path_for(name)
            if not path.is_file():                    # a factory project by name
                path = lib.factory / PROJECTS / path.name
        self._take(_read_json(path), path if lib._is_user(path) else None)
        missing = self._apply()
        lib.report(missing, path.name)
        lib.status = f"project: {self.name}"
        return missing

    def new(self, name: str = UNTITLED) -> None:
        """A fresh project: default state, the factory bank, no file yet."""
        lib = self.lib
        self._take(_read_json(lib.factory / PROJECTS / f"{DEFAULT_PROJECT}{PROJECT_SUFFIX}"),
                   None)
        self.name = name
        lib._fresh_layouts()                          # the layout the app started with…
        lib.restore(lib._fresh_all())                 # …and every group's fresh values
        self._apply()
        lib.status = f"project: new {name}"

    def save(self, name: str | None = None) -> Path:
        """Snapshot everything into the project file (as `name` if given)."""
        lib = self.lib
        if name:
            self.name = name
            self.path = self.path_for(name)
        elif self.path is None:
            self.path = self.path_for(self.name)
        self.values = lib.reg.snapshot(part="performance")
        self.session = lib.reg.snapshot(part="session")
        self.modules = {}
        for group, cur in lib._current.items():
            if cur is None or group in lib._kinds or group == BINDINGS:
                continue                              # the routing layer is the rig's, not the project's
            if lib.path_of(group, cur) is not None:
                self.modules[group] = cur
            else:                                     # not in any library: keep a copy
                doc = lib.document(group, cur)
                self.modules[group] = {k: v for k, v in doc.items()
                                       if k not in ("schema", "group")}
        self.write()
        lib.status = f"project: saved {self.name}"
        return self.path

    def write(self) -> Path:
        """Write the document as held — the theme bank's autosave."""
        if self.path is None:
            self.path = self.path_for(self.name)
        _write_json(self.path, self.to_doc())
        self.lib._sync(self.path)
        return self.path

    def is_dirty(self) -> bool:
        """Does the live state differ from the file? Never saved counts as dirty."""
        reg = self.lib.reg
        if reg is None:
            return False
        return (self.path is None or self.values != reg.snapshot(part="performance")
                or self.session != reg.snapshot(part="session"))


# ---------------------------------------------------------------- library

class Library:
    """Presets, projects and the theme bank over one registry.

    Built before the registry (the theme params need the project's bank),
    bound to it with ``attach(reg)``, which also captures the fresh-object
    values and opens the user's default project (or the factory one).
    `home` is the user tree; tests pass a tmp_path and never touch
    ~/Hyperspace. A document kind (`kind`, `routing`) adds a group whose
    files the library keeps and someone else applies.
    """

    def __init__(self, home_dir: Path | None = None, *, factory: Path = FACTORY,
                 period: float = 0.5):
        self.home = ensure_home(home_dir) if home_dir is None else Path(home_dir)
        (self.home / PROJECTS).mkdir(parents=True, exist_ok=True)
        self.factory = factory
        self.period = period
        self.reg: Registry | None = None
        self.status = ""
        self.error = ""
        self.warning = ""
        self._fresh: dict[str, Any] = {}
        self._current: dict[str, str | None] = {}     # group → loaded preset name
        self._loaded: dict[str, Any] = {}             # group → what that load produced
        self._layout_hooks: dict[str, Any] = {}
        self._extra_hooks: dict[str, Any] = {}    # group → what a save adds beside values
        self._load_hooks: dict[str, Any] = {}     # group → told the name after a load
        self._adopted: dict[str, Any] = {}        # group → how to re-apply an adopted preset
        self._kinds: dict[str, DocKind] = {}      # group → a document kind of its own
        self._fresh_extra: dict[str, dict] = {}   # group → its extra (layout) at attach
        self._defaults: dict[str, dict[str, Any]] = {}   # defaults(group), until a file moves
        self._docs: dict[Path, tuple[float, dict]] = {}   # parsed files, by mtime
        self._mtimes: dict[Path, float] = {}
        self._next = 0.0
        self.project = Project(self)
        self._open_default()
        self._mtimes = self._scan()

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

    def routing(self, router) -> None:
        """The routing presets as a document kind: ``bindings/*.json``,
        ``hyperspace.bindings/2`` (a user's schema-1 file is migrated by
        the router and rewritten once), applied and written by the router.
        The hooks look the router's methods up at call time, so a hot
        reload that re-classes the router reaches them."""
        from . import routing

        versions = routing.SCHEMA_VERSIONS
        self.kind(BINDINGS, routing.SCHEMA.rpartition("/")[0],
                  load=lambda doc, path: router.apply_doc(doc, path),
                  document=lambda name: router.preset_doc(name),
                  signature=lambda: router.signature(),
                  versions=versions, text=lambda doc: routing.dumps_doc(doc))

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

    def on_load(self, group: str, hook) -> None:
        """Register who is told the name a load of this group landed — the
        scene combo, so a strip load moves the selected scene."""
        self._load_hooks[group] = hook

    def _open_default(self) -> None:
        """The user's default project if there is one, else the factory's."""
        user = self.project.path_for(DEFAULT_PROJECT)
        path = user if user.is_file() else self.factory / PROJECTS / user.name
        try:
            self.project._take(_read_json(path), user if path == user else None)
        except LibraryError as e:
            self.error = f"library: {e}"
            self.project._take({"schema": PROJECT_SCHEMA}, None)

    def factory_bank(self) -> list[dict | None]:
        path = self.factory / PROJECTS / f"{DEFAULT_PROJECT}{PROJECT_SUFFIX}"
        try:
            bank = list(_read_json(path).get("bank") or [])[:SLOTS]
        except LibraryError:
            bank = []
        return bank + [None] * (SLOTS - len(bank))

    # ---- the tree ----

    def _is_user(self, path: Path) -> bool:
        return self.home in path.parents

    def _roots(self):
        yield self.factory
        yield self.home

    def groups(self) -> list[str]:
        """Every group with a preset folder, a persisted param or a document
        kind — less ``macro``: a macro's meaning is its subscribers, which
        live in the preset, so it gets no module-preset strip (plan 13 §9)."""
        out = {p.group for p in (self.reg or [])
               if p.persist and p.group and p.group != "macro"}
        out.update(self._kinds)
        for root in self._roots():
            if root.is_dir():
                out.update(d.name for d in root.iterdir()
                           if d.is_dir() and d.name != PROJECTS and not d.name.startswith("."))
        return sorted(out)

    def _files(self, group: str) -> dict[str, Path]:
        """slug → path, the user's file shadowing the factory's."""
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
        """display name → path; a name is also reachable by its slug."""
        return {self._name_of(p): p for p in self._files(group).values()}

    def path_of(self, group: str, name: str) -> Path | None:
        idx = self._index(group)
        return idx.get(name) or self._files(group).get(slug(name))

    def is_factory(self, group: str, name: str) -> bool:
        p = self.path_of(group, name)
        return p is not None and not self._is_user(p)

    def list(self, group: str) -> list[str]:
        return sorted(self._index(group), key=str.lower)

    def read(self, group: str, name: str) -> dict:
        path = self.path_of(group, name)
        if path is None:
            raise LibraryError(f"{group}: no preset {name!r}")
        doc = copy.deepcopy(self._doc(path))
        kind = self._kinds.get(group)
        if kind is not None:                       # its own format: checked, not lifted
            schema = str(doc.get("schema") or "")
            k, _, v = schema.rpartition("/")
            if not schema:                          # routing's v1 files carried none
                return doc
            if k != kind.schema or not v.isdigit() or int(v) not in kind.versions:
                raise LibraryError(f"{path.name}: schema {schema!r} is not a {kind.schema}")
            return doc
        doc = migrate_doc(doc, "hyperspace.preset")
        if doc.get("group", group) != group:
            raise LibraryError(f"{path.name} is a {doc['group']} preset, not {group}")
        return doc

    # ---- defaults & values ----

    def default_name(self, group: str) -> str | None:
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
                out.update(self.read(group, name).get("values") or {})
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
            self.warning = f"{where}: {len(missing)} unknown id(s): {shown}"
            print(f"library: {self.warning}", file=sys.stderr)

    # ---- presets: the surface WP5a draws ----

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
            hook = self._layout_hooks.get(group)
            if hook is not None and doc.get("layout") is not None:
                hook(doc["layout"])                    # rebuild params first
                self._fresh_of(group)                  # …and their build values are "fresh"
            values = doc.get("values") or {}
            missing = [k for k in values if k not in self.reg]
            resolved = self.resolved(group, values)
            self.restore(resolved)
            self._landed(group, doc.get("name") or name, resolved)
        self.report(missing, f"{group}/{name}")
        if not quiet:
            self.status = f"{group}: {self._current[group]}"
        hook = self._load_hooks.get(group)
        if hook is not None:
            hook(self._current[group])
        return missing

    def adopt(self, group: str, name: str, reapply) -> None:
        """A preset applied by someone else — the scene combo landing a
        scene's values on the analyzer itself: make it the group's current
        preset, with the group's state as it now stands as what "clean"
        means (the combo applies no layout, so the file's layout ids are
        not the reference), and `reapply` as what poll() calls when the
        file changes on disk, in place of a whole load."""
        loaded = self.reg.snapshot(group) if self.reg is not None else None
        self._landed(group, name, loaded, reapply)
        self.status = f"{group}: {name}"

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
        """Write the group's bases as a user preset and make it current."""
        doc = self.document(group, name, extra=extra)
        path = self.home / group / f"{slug(name)}.json"
        kind = self._kinds.get(group)
        if kind is not None and kind.text is not None:
            _write_text(path, kind.text(doc))
        else:
            _write_json(path, doc)
        self._sync(path)
        self._landed(group, name, kind.signature() if kind is not None
                     else self.resolved(group, doc["values"]))
        self.status = f"{group}: saved {name}"
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
        if extra is None and group in self._extra_hooks:
            extra = self._extra_hooks[group]()
        if extra:
            doc.update(extra)
        return doc

    def overwrite(self, group: str, *, extra: dict | None = None) -> Path | None:
        """Save over the current preset (a factory one gets a user shadow)."""
        cur = self.current(group)
        return None if cur is None else self.save_as(group, cur, extra=extra)

    def delete(self, group: str, name: str) -> bool:
        """Remove a user preset; a factory one stays, a shadow just lifts."""
        path = self.path_of(group, name)
        if path is None or not self._is_user(path):
            return False
        path.unlink()
        self._sync(path)
        if self._current.get(group) == name and self.path_of(group, name) is None:
            self._landed(group, None, None)
        return True

    def is_dirty(self, group: str) -> bool:
        """Have the group's bases moved off the loaded (or default) preset?
        For a document kind: has its signature moved since the last load or
        save (nothing loaded yet is never dirty)."""
        kind = self._kinds.get(group)
        if kind is not None:
            ref = self._loaded.get(group)
            return ref is not None and kind.signature() != ref
        reg = self._need_reg()
        ref = self._loaded.get(group)
        if ref is None:
            ref = self.resolved(group, {})
        snap = reg.snapshot(group)
        return any(snap.get(k) != v for k, v in ref.items())

    def reset(self, group: str) -> str | None:
        """Back to the group's default preset (or its fresh values)."""
        name = self.default_name(group)
        if name is not None:
            self.load(group, name)
            return name
        if group in self._kinds:
            return None
        self._need_reg()
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
                self.project.load(self.project.path)
                hit.append(f"project {self.project.name}")
            self.error = ""
        except LibraryError as e:                     # a half-saved file: keep running
            self.error = f"library: {e}"
            return False
        if hit:
            self.status = f"library: {', '.join(hit)} · {time.strftime('%H:%M:%S')}"
        return True
