"""Live-code the whole engine — the patterns.glsl contract, for Python.

Save any watched module while the app runs and it picks the change up; a
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

Data is watched the same way: `watchers` are objects with a ``poll(now)``
(the preset library) that get polled on the same cadence, so a preset
JSON saved in an editor lands like a module save does.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys
import time
from pathlib import Path

# dependency order, leaves first: a change reloads its module and every
# module after it, so cross-module imports always rebind fresh
MODULES = (
    "analysis", "tapers", "geometry", "bands", "analyzer", "control", "audio", "render",
    "params", "library", "presets", "overlay", "apc40", "routing", "midi", "bridge",
    "ui_presets", "ui_bands", "ui_routing", "ui",
)


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
    one of those picked something up.
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
        self._next = 0.0
        self._mtimes: dict[str, float] = {}
        for name, f in self._files():
            self._mtimes[name] = f.stat().st_mtime

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
            if mtime != self._mtimes.get(name):
                self._mtimes[name] = mtime  # a bad save must not re-error every poll
                changed.append((name, f))
        if not changed:
            return False

        # refuse to reload anything unless every changed file parses
        for name, f in changed:
            try:
                compile(f.read_text(), str(f), "exec")
            except SyntaxError as e:
                self.error = f"{name}.py:{e.lineno}: {e.msg}"[:160]
                return False

        first = min(self.modules.index(name) for name, _ in changed)
        try:
            for name in self.modules[first:]:
                importlib.reload(sys.modules[f"{self.package}.{name}"])
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

        self.error = ""
        self.runtime_error = ""
        names = ", ".join(name for name, _ in changed)
        self.status = f"hot: {names} · {time.strftime('%H:%M:%S')}"
        return True
