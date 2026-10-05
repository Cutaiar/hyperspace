"""Live-code the listed modules — the patterns.glsl contract, for Python.

Save a module named in MODULES while the app runs and it picks the change
up (a module not listed in MODULES needs a restart); a
broken save keeps the last good version running and surfaces the error,
never kills the app.

How it works: on a change, the changed module and everything after it in
MODULES (dependency order, leaves first) is re-executed with
importlib.reload, so downstream ``from x import y`` bindings rebind to the
fresh objects. Then every registered long-lived instance is re-classed in
place (``obj.__class__ = NewClass``) so it keeps all its state — GL
buffers, audio streams, fader positions — while its methods resolve
through the newly saved module's globals. app.py itself is the cold core:
its main loop is on the stack and cannot be reloaded, which is why it
stays tiny.

Contract for hot classes:
  - state in __init__, behaviour in methods; edits to methods land live
  - a class that must rebuild derived resources after a swap defines
    on_reload() — Renderer uses it to recompile its GL programs
  - dataclass instances get newly added fields backfilled from their
    defaults, so adding a ViewState field plus its slider is one save
  - a changed __init__ does NOT re-run on live instances; attributes it
    would have added are missing until restart (the frame guard in app.py
    catches the resulting error and shows it instead of crashing)
  - an Enum defined in a reloaded module keeps its identity: the class the
    process first built is put back after the re-execution, so a live
    object's member still `is` the module's (params.Kind was the case that
    bit — audit H2). A member added or removed in the edit needs a restart
    and `error` says so.

A watched module that was never imported (an optional adapter behind its
config gate — dream, bridge, midi) is skipped, not an error.

Data is watched the same way: `watchers` are objects with a ``poll(now)``
(the preset library) that get polled on the same cadence, so a preset
JSON saved in an editor lands like a module save does.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys
import time
from enum import Enum
from pathlib import Path

# dependency order, leaves first: a change reloads its module and every
# module after it, so cross-module imports always rebind fresh. Every
# module in the package but app (the cold core) and this one is here; a
# module that `from .x import Name`s another comes after it, and a
# subpackage's modules are named with a dot (tests/test_hotreload.py
# holds both rules against the package's own imports).
MODULES = (
    "analysis", "tapers", "undo", "placement", "geometry", "bands", "analyzer", "audio", "tempo", "lfo", "glsl",
    "lookback", "dream", "fx", "ghost", "outputs", "view", "render", "params", "library", "control", "config",
    "overlay", "gamepad", "apc40", "routing", "preset", "learn", "midi", "bridge",
    "hands.signal", "hands.tape", "hands.core", "hands", "ui_presets", "ui_lookback", "ui_bands", "ui_routing", "ui_fx",
    "ui_lfo", "ui_desk", "hands.panel", "ui",
)


def _enums(mod) -> dict[str, type[Enum]]:
    """The Enum classes a module defines (not ones it imports)."""
    return {name: obj for name, obj in vars(mod).items()
            if isinstance(obj, type) and issubclass(obj, Enum) and obj is not Enum
            and obj.__module__ == mod.__name__}


def _keep_enums(mod, kept: dict[str, type[Enum]]) -> list[str]:
    """After a reload, put each kept Enum class back under its name so live
    members keep matching; returns the names whose members changed."""
    changed = []
    for name, old in kept.items():
        new = vars(mod).get(name)
        if new is old or not (isinstance(new, type) and issubclass(new, Enum)):
            continue
        if [(m.name, m.value) for m in new] != [(m.name, m.value) for m in old]:
            changed.append(name)
        setattr(mod, name, old)
    return changed


def _backfill_dataclass(obj) -> None:
    """Give a re-classed dataclass instance any newly added fields."""
    for f in dataclasses.fields(type(obj)):
        if hasattr(obj, f.name):
            continue
        if f.default is not dataclasses.MISSING:
            setattr(obj, f.name, f.default)
        elif f.default_factory is not dataclasses.MISSING:
            setattr(obj, f.name, f.default_factory())


class HotReloader:
    """Watches a package's modules and hot-swaps live instances.

    `targets` is a callable returning [(obj, module_name, class_name)];
    it is re-evaluated each reload so recreated objects (the chain after a
    source attach) are picked up. `error` holds the last failed reload,
    `runtime_error` the last frame-guard failure (app.py writes it),
    `status` the last successful swap — or a watcher's own `status` when
    one of those picked something up — and `restart` why the process
    needs restarting (an Enum whose members changed), kept until it is.
    """

    def __init__(self, targets, package: str = "hyperspace",
                 modules: tuple[str, ...] = MODULES, period: float = 0.5, watchers=()):
        self.targets = targets
        self.package = package
        self.modules = modules
        self.period = period
        self.watchers = list(watchers)
        self.error = ""
        self.runtime_error = ""
        self.status = ""
        self.restart = ""
        self._next = 0.0
        self._mtimes: dict[str, float] = {}
        for name, f in self._files():
            self._mtimes[name] = f.stat().st_mtime

    def _rel(self, f: Path) -> str:
        """A file's path from the package's parent (hyperspace/hands/core.py)."""
        pkg = sys.modules.get(self.package)
        root = Path(pkg.__file__).parent.parent if getattr(pkg, "__file__", None) else None
        try:
            return str(f.relative_to(root)) if root else f.name
        except ValueError:
            return f.name

    def _files(self):
        for name in self.modules:
            mod = sys.modules.get(f"{self.package}.{name}")
            if mod is not None and getattr(mod, "__file__", None):
                yield name, Path(mod.__file__)

    def poll(self, now: float | None = None) -> bool:
        """Check for edits; returns True when a swap happened."""
        now = time.monotonic() if now is None else now
        if now < self._next:
            return False
        self._next = now + self.period
        for w in self.watchers:
            if w.poll(now) and getattr(w, "status", ""):
                self.status = w.status
        changed = []
        for name, f in self._files():
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue
            if name not in self._mtimes:
                self._mtimes[name] = mtime  # imported since __init__: seen, not changed
            elif mtime != self._mtimes[name]:
                self._mtimes[name] = mtime  # a bad save must not re-error every poll
                changed.append((name, f))
        if not changed:
            return False

        # refuse to reload anything unless every changed file parses
        for name, f in changed:
            try:
                compile(f.read_text(), str(f), "exec")
            except SyntaxError as e:
                self.error = f"{self._rel(f)}:{e.lineno}: {e.msg}"[:160]
                return False

        first = min(self.modules.index(name) for name, _ in changed)
        notes = []
        try:
            for name in self.modules[first:]:
                mod = sys.modules.get(f"{self.package}.{name}")
                if mod is None:
                    continue            # an optional adapter that is off
                kept = _enums(mod)
                importlib.reload(mod)
                notes += [f"{name}.{e} changed — restart to use its new members"
                          for e in _keep_enums(mod, kept)]   # sticky: self.restart
        except Exception as e:  # noqa: BLE001 — a bad edit must not kill the app
            self.error = f"{type(e).__name__}: {e}"[:160]
            return False

        try:
            for obj, mod, clsname in self.targets():
                newcls = getattr(sys.modules[f"{self.package}.{mod}"], clsname)
                if type(obj) is newcls:
                    continue  # module untouched this round
                obj.__class__ = newcls
                if dataclasses.is_dataclass(newcls):
                    _backfill_dataclass(obj)
                hook = getattr(obj, "on_reload", None)
                if hook is not None:
                    hook()
        except Exception as e:  # noqa: BLE001
            self.error = f"swap: {type(e).__name__}: {e}"[:160]
            return False

        for note in notes:
            if note not in self.restart:
                self.restart = f"{self.restart}; {note}" if self.restart else note
        self.error = ""
        self.runtime_error = ""
        names = ", ".join(name for name, _ in changed)
        self.status = f"hot: {names} · {time.strftime('%H:%M:%S')}"
        return True
