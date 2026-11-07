"""A hot reload through the real swap, over the real app's long-lived objects (HR, row 802).

Plan 44 D5a gave `DeckLibrary` and `DeckProject` slots over a hot base, and from that day
no save before `library` on the list completed: `swap: TypeError: __class__ assignment:
'DeckLibrary' object layout differs from 'DeckLibrary'`. Nothing failed, because no reload
test assigned a `__class__` on a class whose base had reloaded. The fast tier holds the
rule on every real class in a hot module, with Python's own check; the `live` tier (real
windows take the focus on a Mac, so `--all`, not CI) runs a save through the real app.
"""

import importlib
import json
import os
import subprocess
import sys
import types
import typing
from enum import Enum
from pathlib import Path

import pytest

from hyperspace.hotreload import MODULES

ROOT = Path(__file__).parents[1]
PACKAGE = "hyperspace"


def test_a_save_reaches_every_live_object_of_the_real_app(gl_window_ok, tmp_path):
    """`app.main`, in a process of its own, with `tools/drive_hot_reload.py` marking the
    first module on the list saved, so every module reloads and every target is re-classed:
    no error, none left on an old class, `Renderer.on_reload` ran, the frames after it draw."""
    env = dict(os.environ, HYPERSPACE_TOUCH=MODULES[0], TMPDIR=str(tmp_path))
    out = subprocess.run(
        [sys.executable, "tools/app_driver.py", "tools/drive_hot_reload.py",
         "--out", str(tmp_path / "run"), "--every", "100000"],
        capture_output=True, text=True, check=False, cwd=str(ROOT), env=env, timeout=110)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    assert f"reloaded: {MODULES[0]}" in out.stdout, out.stdout[-2000:] + out.stderr[-2000:]


# ---- the rule: what a reload makes, handed to Python's own check

def _remake(cls: type, hot: set[str], made: dict[type, type]) -> type:
    """`cls` as a reload makes it: a new class with the same slots over its hot bases,
    themselves new; a base outside `hot` stays the same object, as an Enum does
    (`hotreload._keep_enums`). No method or field: a layout comes from neither."""
    if cls.__module__ not in hot or issubclass(cls, Enum):
        return cls
    if cls not in made:
        ns: dict[str, typing.Any] = {"__module__": cls.__module__}
        if "__slots__" in vars(cls):
            ns["__slots__"] = vars(cls)["__slots__"]
        if "__orig_bases__" in vars(cls):      # (typing refuses a plain `Generic` base)
            ns["__orig_bases__"] = vars(cls)["__orig_bases__"]
        bases = tuple(_remake(b, hot, made) for b in cls.__bases__)
        made[cls] = type(cls)(cls.__name__, bases, ns)
        if getattr(made[cls], "__abstractmethods__", None):
            made[cls].__abstractmethods__ = frozenset()    # an instance is all this needs
    return made[cls]


def refusal(cls: type, hot: set[str]) -> str | None:
    """Why a live `cls` can't be re-classed after a reload of `hot`; None when it can."""
    old, new = _remake(cls, hot, {}), _remake(cls, hot, {})
    obj = old.__new__(old)
    try:
        obj.__class__ = new
    except TypeError as e:
        return str(e)
    return None


def _classes(owner, module: str):
    """The classes `owner` (a module, or a class) defines, and any nested in them."""
    for c in list(vars(owner).values()):
        if isinstance(c, type) and c.__module__ == module and c is not owner:
            yield c
            yield from _classes(c, module)


def report(importer=importlib.import_module) -> None:
    """Every class of every hot module against `refusal`, as one line of JSON. Run in a
    process of its own: it imports all of them, torch and the media adapters included.
    Only a third-party package that isn't there is skipped: any other import error,
    and one of our own above all, fails here, so no class leaves the rule for it."""
    names = [f"{PACKAGE}.{name}" for name in MODULES]
    hot = set(names)
    wrong, unmodelled, skipped, checked = {}, {}, {}, 0
    for name in names:
        try:
            mod = importer(name)
        except ModuleNotFoundError as e:
            if (e.name or PACKAGE).split(".")[0] == PACKAGE:
                raise
            skipped[name] = str(e)
            continue
        for cls in dict.fromkeys(_classes(mod, name)):
            if issubclass(cls, Enum) or typing.is_typeddict(cls):
                continue            # kept across a reload; a dict at runtime
            where = f"{name}.{cls.__qualname__}"
            try:
                why = refusal(cls, hot)
            except Exception as e:  # noqa: BLE001 — named, and the test fails on it
                unmodelled[where] = f"{type(e).__name__}: {e}"
                continue
            checked += 1
            if why:
                wrong[where] = why
    print(json.dumps({"wrong": wrong, "unmodelled": unmodelled, "skipped": skipped,
                      "checked": checked}))


REPORT = "import sys; sys.path.insert(0, 'tests'); import test_hot_reload_app as t; t.report()"
# no module of the app's own core may go unread for want of an import
CORE = {"library", "deck", "render", "outputs", "ui", "routing", "params", "loadable", "motion",
        "hands.core", "media.mixer"}


def test_every_class_in_a_hot_module_can_be_re_classed_after_a_reload():
    """Over a hot class, a hot class can't add to the layout: it can't declare slots, and
    it can't be slotless over one that declares any (it gains a `__dict__`). A class that
    needs slots there takes them from `hot_slots.py`. CI's only guard: the real app's test
    is `live`. A module whose optional dependency is missing is skipped by name; CORE is not."""
    out = subprocess.run([sys.executable, "-c", REPORT], capture_output=True, text=True,
                         check=False, cwd=str(ROOT), timeout=110)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert not got["wrong"], got["wrong"]
    assert not got["unmodelled"], got["unmodelled"]
    assert not {f"{PACKAGE}.{name}" for name in CORE} & set(got["skipped"]), got["skipped"]
    assert got["checked"] > 300, got


def test_the_rule_imports_in_the_lists_order(capsys):
    """Row 812: `report` imports in `MODULES`'s order, with the importer passed in, so
    this test patches nothing in a worker the other tests share."""
    seen = []

    def record(name):
        seen.append(name)
        raise ModuleNotFoundError("not here", name="third_party")

    report(record)
    assert seen == [f"{PACKAGE}.{name}" for name in MODULES]
    assert len(json.loads(capsys.readouterr().out)["skipped"]) == len(MODULES)


@pytest.mark.parametrize("error", [
    ModuleNotFoundError("No module named 'hyperspace.gone'", name="hyperspace.gone"),
    ImportError("cannot import name 'X' from partially initialized module",
                name="hyperspace.ui_desk"),
    ImportError("cannot open shared object file"),
    ImportError("libfoo.so: cannot open shared object file", name="third_party"),
])
def test_the_rule_skips_only_a_missing_third_party_package(error):
    """Only a third-party `ModuleNotFoundError` skips. A cycle in `from .x import Name`
    form, or a package that's there and won't load, fails rather than leave classes unread."""
    def importer(_name):
        raise error

    with pytest.raises(ImportError):
        report(importer)


def _hot(source: str) -> tuple[type, set[str]]:
    """The class `V` of `source`, as a module named `hotmod` defines it; `Cold` is cold."""
    mod = types.ModuleType("hotmod")
    mod.__dict__["Cold"] = type("Cold", (), {"__slots__": ("c",), "__module__": "coldmod"})
    exec(source, mod.__dict__)  # noqa: S102 — this file's own literals
    return mod.V, {"hotmod"}


GENERIC = """
from typing import Generic, TypeVar
T = TypeVar('T')
class Lib(Generic[T]): pass
class V(Lib[int]):
    __slots__ = ('a',)
"""
SLOTTED_DATACLASS = """
from dataclasses import dataclass
class Lib: pass
@dataclass(slots=True)
class V(Lib):
    a: int = 0
"""
ABSTRACT = """
from abc import ABC, abstractmethod
class V(ABC):
    @abstractmethod
    def f(self): ...
"""


@pytest.mark.parametrize(("source", "refused"), [
    # what D5a did
    ("class Lib: pass\nclass V(Lib):\n    __slots__ = ('a',)", True),
    ("class Lib: pass\nclass V(Lib):\n    __slots__ = ['a']", True),
    # a slotless class over a slotted one gains a __dict__: refused, even over empty slots
    ("class S:\n    __slots__ = ('x',)\nclass V(S): pass", True),
    ("class S:\n    __slots__ = ()\nclass V(S): pass", True),
    # the spellings a reading of the source would miss
    ("class Lib: pass\nclass V(Lib):\n    __slots__: tuple = ('a',)", True),
    (GENERIC, True),
    ("class Lib: pass\nAlias = Lib\nclass V(Alias):\n    __slots__ = ('a',)", True),
    (SLOTTED_DATACLASS, True),
    # how it is done, and what was always fine
    ("class Lib: pass\nclass V(Cold, Lib): pass", False),
    ("class Lib: pass\nclass V(Lib): pass", False),
    ("class S:\n    __slots__ = ('x',)\nclass V(S):\n    __slots__ = ()", False),
    ("class Lib: pass\nclass V(Lib):\n    __slots__ = ()", False),
    ("class V(Cold):\n    __slots__ = ('a',)", False),
    ("class V:\n    __slots__ = ('a',)", False),
    (ABSTRACT, False),
])
def test_the_rule_sees_what_it_should(source, refused):
    cls, hot = _hot(source)
    assert bool(refusal(cls, hot)) is refused


def test_the_decks_views_hold_their_fields_on_a_cold_base():
    from hyperspace import hot_slots
    from hyperspace.library import DeckInstall, DeckLibrary

    assert issubclass(DeckLibrary, hot_slots.DeckLibrarySlots)
    assert issubclass(DeckInstall, hot_slots.DeckInstallSlots)
    assert "__slots__" not in vars(DeckLibrary) and "__slots__" not in vars(DeckInstall)
    assert refusal(DeckLibrary, {"hyperspace.library"}) is None


COLD = """
import importlib, json, pkgutil, sys
import hyperspace
names = sorted(m.name for m in pkgutil.walk_packages(hyperspace.__path__, "hyperspace."))
bad = {}
for name in names:
    for k in [k for k in sys.modules if k == "hyperspace" or k.startswith("hyperspace.")]:
        del sys.modules[k]
    try:
        importlib.import_module(name)
    except (AttributeError, ImportError) as e:
        if isinstance(e, AttributeError) or "circular" in str(e) or "partially" in str(e):
            bad[name] = f"{type(e).__name__}: {e}"
    except Exception:
        pass            # an optional dependency's own failure: not a cycle
print(json.dumps({"n": len(names), "bad": bad}))
"""


def test_every_module_imports_alone():
    """Each of the package's modules imports first, into a process with none of the
    package loaded. A cycle the app's own order never meets still broke
    the report above whenever a set's order put the module first: `ui_pane` read by
    `ui_graph`, and `ui_desk` read by `ui_pad`, half made (row 808, ui_diagram.py)."""
    out = subprocess.run([sys.executable, "-c", COLD], capture_output=True, text=True,
                         check=False, cwd=str(ROOT), timeout=110)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["n"] > 100 and not got["bad"], got["bad"]
