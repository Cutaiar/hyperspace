"""The preset & project library — the Ableton model over the registry.

Two kinds of file, both plain JSON you can open in a text editor:

  module preset   one registry *group* (view, camera, band…) —
                  ``{"schema": "hyperspace.preset/1", "group", "name",
                  "values": {id: base}}``, produced by ``Registry.snapshot
                  (group)`` and applied with ``Registry.restore``. The
                  analyzer's presets also carry ``layout`` (see the
                  contract in docs/plans/07-overhaul.md): restore hands the
                  layout to a hook registered with ``on_layout`` *before*
                  the values, so a preset can rebuild its params first.
  project         everything — ``{"schema": "hyperspace.project/1",
                  "name", "values": <full snapshot>, "modules": {group:
                  name | {"name", "values"}}, "bank": [8 × {"name",
                  "values"} | null], "io": {...}}``, in a ``*.hyp.json``
                  file. The F1–F8 theme bank (presets.py) lives inside it.

Library layout — the same tree in two places, the user's shadowing the
factory's file of the same name:

  hyperspace/library/<group>/<slug>.json     factory, read-only, in the wheel
  $HYPERSPACE_HOME/<group>/<slug>.json       user (default ~/Hyperspace)
  $HYPERSPACE_HOME/projects/<slug>.hyp.json  user projects
  $HYPERSPACE_HOME/config.toml, midi_map.json

``home()`` is the one resolver for that folder (config.py and the MIDI map
path go through it). On the first run the working-directory ``config.toml``
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
from pathlib import Path
from typing import Any

from .params import PLANES, Registry
from .presets import SLOTS, Presets

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


def ensure_home(root: Path | None = None, cwd: Path | None = None) -> Path:
    """Create the library home and pull in the working-directory files."""
    root = home() if root is None else root
    (root / PROJECTS).mkdir(parents=True, exist_ok=True)
    for msg in migrate(root, cwd):
        print(msg, file=sys.stderr)
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
                              "values": {}, "modules": {}, "bank": bank, "io": {}})
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
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1) + "\n")
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
    """The open project: its file (None until saved) and its sections.

    ``values`` / ``modules`` / ``io`` are what the *file* holds; only
    ``save()`` refreshes them from the live state. ``write()`` puts the
    in-memory document back on disk as it is — that is what a theme-slot
    save uses, so F-key saves persist without turning the whole project
    into a snapshot of the moment. ``io`` is kept verbatim for the
    adapters (MIDI profile/map, audio device or track) to fill.
    """

    def __init__(self, lib: Library):
        self.lib = lib
        self.name = DEFAULT_PROJECT
        self.path: Path | None = None
        self.values: dict[str, Any] = {}
        self.modules: dict[str, Any] = {}
        self.bank: list[dict | None] = [None] * SLOTS
        self.io: dict[str, Any] = {}

    # ---- documents ----

    def _take(self, doc: dict, path: Path | None) -> None:
        doc = migrate_doc(doc, "hyperspace.project")
        self.name = str(doc.get("name") or (path.name[: -len(PROJECT_SUFFIX)] if path
                                            else UNTITLED))
        self.path = path
        self.values = dict(doc.get("values") or {})
        self.modules = dict(doc.get("modules") or {})
        self.io = dict(doc.get("io") or {})
        bank = list(doc.get("bank") or [])[:SLOTS]
        bank += [None] * (SLOTS - len(bank))
        # an empty slot is seeded from the factory bank, as it always was
        seeds = self.lib.factory_bank()
        self.bank = [s if s else seeds[k] for k, s in enumerate(bank)]

    def to_doc(self) -> dict:
        return {"schema": PROJECT_SCHEMA, "name": self.name, "values": self.values,
                "modules": self.modules, "bank": self.bank, "io": self.io}

    def _apply(self) -> list[str]:
        """Push the document's state into the registry; returns unknown ids."""
        lib = self.lib
        lib._current.clear()
        lib._loaded.clear()
        missing = lib.restore(self.values) if self.values else []
        for group, ref in self.modules.items():
            if isinstance(ref, dict):                 # inline copy of a preset
                name = str(ref.get("name") or "")
                vals = lib._resolve(group, ref.get("values") or {})
            else:                                     # by name in the library
                name = str(ref)
                try:
                    vals = lib._resolve(group, lib.read(group, name).get("values") or {})
                except LibraryError:
                    vals = lib.reg.snapshot(group)   # gone from the library: not dirty
            lib._current[group] = name
            lib._loaded[group] = vals
        lib.bank.active = -1
        return missing

    # ---- API ----

    def list(self) -> list[str]:
        return sorted(p.name[: -len(PROJECT_SUFFIX)]
                      for p in (self.lib.home / PROJECTS).glob(f"*{PROJECT_SUFFIX}"))

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
        lib.restore(lib._fresh)
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
        self.values = lib.reg.snapshot()
        self.modules = {}
        for group, cur in lib._current.items():
            if cur is None:
                continue
            if lib.path_of(group, cur) is not None:
                self.modules[group] = cur
            else:                                     # not in any library: keep a copy
                self.modules[group] = {"name": cur, "values": lib.reg.snapshot(group)}
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


# ---------------------------------------------------------------- library

class Library:
    """Presets, projects and the theme bank over one registry.

    Built before the registry (theme params need the bank), bound to it
    with ``attach(reg)``, which also captures the fresh-object values and
    opens the user's default project (or the factory one). `home` is the
    user tree; tests pass a tmp_path and never touch ~/Hyperspace.
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
        self._loaded: dict[str, dict[str, Any]] = {}  # group → what that load produced
        self._layout_hooks: dict[str, Any] = {}
        self._docs: dict[Path, tuple[float, dict]] = {}   # parsed files, by mtime
        self._mtimes: dict[Path, float] = {}
        self._next = 0.0
        self.project = Project(self)
        self.bank = Presets(self)
        self._open_default()
        self._mtimes = self._scan()

    def attach(self, reg: Registry) -> list[str]:
        """Bind the registry; its state right now is what "default" means."""
        self.reg = reg
        self._fresh = reg.snapshot()
        missing = self.project._apply()
        self.report(missing, self.project.name)
        return missing

    def on_layout(self, group: str, hook) -> None:
        """Register who rebuilds a group's params from a preset's `layout`."""
        self._layout_hooks[group] = hook

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
        """Every group with a preset folder or a persisted param."""
        out = {p.group for p in (self.reg or []) if p.persist and p.group}
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
        doc = migrate_doc(copy.deepcopy(self._doc(path)), "hyperspace.preset")
        if doc.get("group", group) != group:
            raise LibraryError(f"{path.name} is a {doc['group']} preset, not {group}")
        return doc

    # ---- defaults & values ----

    def default_name(self, group: str) -> str | None:
        name = DEFAULT_NAMES.get(group, "default")
        return name if self.path_of(group, name) is not None else None

    def defaults(self, group: str) -> dict[str, Any]:
        """What reset(group) produces: the default preset over the fresh values."""
        out = {k: v for k, v in self._fresh.items() if self.reg and k in self.reg
               and self.reg[k].group == group}
        name = self.default_name(group)
        if name is not None:
            try:
                out.update(self.read(group, name).get("values") or {})
            except LibraryError as e:
                self.error = f"library: {e}"
        return out

    def _resolve(self, group: str, values: dict[str, Any]) -> dict[str, Any]:
        """A preset's values over the group's defaults, ids this registry has."""
        out = self.defaults(group)
        out.update(values)
        return {k: v for k, v in out.items() if k in self.reg}

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
        self._need_reg()
        doc = self.read(group, name)
        hook = self._layout_hooks.get(group)
        if hook is not None and doc.get("layout") is not None:
            hook(doc["layout"])                        # rebuild params first
        values = doc.get("values") or {}
        missing = [k for k in values if k not in self.reg]
        resolved = self._resolve(group, values)
        self.restore(resolved)
        self._current[group] = doc.get("name") or name
        self._loaded[group] = resolved
        self.report(missing, f"{group}/{name}")
        self.status = f"{group}: {self._current[group]}"
        return missing

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
        reg = self._need_reg()
        doc = {"schema": PRESET_SCHEMA, "group": group, "name": name,
               "values": reg.snapshot(group)}
        if extra:                                      # e.g. the analyzer's layout
            doc.update(extra)
        path = self.home / group / f"{slug(name)}.json"
        _write_json(path, doc)
        self._sync(path)
        self._current[group] = name
        self._loaded[group] = self._resolve(group, doc["values"])
        self.status = f"{group}: saved {name}"
        return path

    def overwrite(self, group: str, *, extra: dict | None = None) -> Path | None:
        """Save over the current preset (a factory one gets a user shadow)."""
        cur = self.current(group)
        return None if cur is None else self.save_as(group, cur, extra=extra)

    def rename(self, group: str, new: str, name: str | None = None) -> bool:
        """Rename a user preset (factory ones are read-only)."""
        name = self.current(group) if name is None else name
        path = None if name is None else self.path_of(group, name)
        if path is None or not self._is_user(path):
            return False
        doc = _read_json(path)
        doc["name"] = new
        dst = path.with_name(f"{slug(new)}.json")
        _write_json(dst, doc)
        if dst != path:
            path.unlink()
        self._sync(path, dst)
        if self._current.get(group) == name:
            self._current[group] = new
        return True

    def delete(self, group: str, name: str) -> bool:
        """Remove a user preset; a factory one stays, a shadow just lifts."""
        path = self.path_of(group, name)
        if path is None or not self._is_user(path):
            return False
        path.unlink()
        self._sync(path)
        if self._current.get(group) == name and self.path_of(group, name) is None:
            self._current[group] = None
            self._loaded.pop(group, None)
        return True

    def is_dirty(self, group: str) -> bool:
        """Have the group's bases moved off the loaded (or default) preset?"""
        reg = self._need_reg()
        ref = self._loaded.get(group)
        if ref is None:
            ref = self._resolve(group, {})
        # over the ids the preset governs: a param registered after attach()
        # (the overlay's) is outside every preset until something saves it
        snap = reg.snapshot(group)
        return any(snap.get(k) != v for k, v in ref.items())

    def reset(self, group: str) -> str | None:
        """Back to the group's default preset (or its fresh values)."""
        name = self.default_name(group)
        if name is not None:
            self.load(group, name)
            return name
        self._need_reg()
        self.restore(self._resolve(group, {}))
        self._current[group] = None
        self._loaded.pop(group, None)
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
        if self.reg is None:
            return True
        hit = []
        try:
            for group, name in list(self._current.items()):
                if name is not None and self.path_of(group, name) in changed:
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
