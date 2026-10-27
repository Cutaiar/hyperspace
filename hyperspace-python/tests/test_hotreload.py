"""HotReloader semantics, driven against a throwaway two-module package.

mod_a is the leaf, mod_b imports from it — the same shape as the real
package (bands → ui), so the rebind and partial-reload rules get exercised
without touching hyperspace's own modules on disk.
"""

import importlib
import os
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperspace.hotreload import HotReloader

A_V1 = """
    from dataclasses import dataclass

    VALUE = 1

    class Thing:
        def __init__(self):
            self.count = 0

        def speak(self):
            return "old"

    @dataclass
    class State:
        a: int = 1
"""

A_V2 = """
    from dataclasses import dataclass, field

    VALUE = 2

    class Thing:
        def __init__(self):
            self.count = 0

        def speak(self):
            return "new"

        def on_reload(self):
            self.rebuilt = True

    @dataclass
    class State:
        a: int = 1
        b: float = 2.5
        c: list = field(default_factory=lambda: [1, 2])
"""

B_V1 = """
    from .mod_a import VALUE

    def get():
        return VALUE
"""

_clock = [1_000_000_000.0]


def write(root, name, src):
    """Write a module with a strictly increasing mtime (fs resolution safe)."""
    f = root / f"{name}.py"
    f.write_text(textwrap.dedent(src))
    _clock[0] += 2
    os.utime(f, (_clock[0], _clock[0]))


@pytest.fixture
def pkg(tmp_path, monkeypatch):
    root = tmp_path / "hotpkg"
    root.mkdir()
    (root / "__init__.py").write_text("")
    write(root, "mod_a", A_V1)
    write(root, "mod_b", B_V1)
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    yield root
    for name in ("hotpkg", "hotpkg.mod_a", "hotpkg.mod_b"):
        sys.modules.pop(name, None)


def _reloader(targets):
    return HotReloader(targets, package="hotpkg", modules=("mod_a", "mod_b"), period=0.0)


def test_swap_keeps_state_rebinds_downstream_and_hooks(pkg):
    mod_a = importlib.import_module("hotpkg.mod_a")
    mod_b = importlib.import_module("hotpkg.mod_b")
    t = mod_a.Thing()
    t.count = 7
    r = _reloader(lambda: [(t, "mod_a", "Thing")])

    write(pkg, "mod_a", A_V2)
    assert r.poll(now=1.0)
    assert t.speak() == "new"          # methods are the new code
    assert t.count == 7                # state survived the swap
    assert t.rebuilt is True           # on_reload hook ran
    assert mod_b.get() == 2            # downstream from-import rebound
    assert r.error == "" and "mod_a" in r.status


def test_bad_save_keeps_last_good_until_fixed(pkg):
    mod_a = importlib.import_module("hotpkg.mod_a")
    importlib.import_module("hotpkg.mod_b")
    t = mod_a.Thing()
    r = _reloader(lambda: [(t, "mod_a", "Thing")])

    write(pkg, "mod_a", "def (broken\n")
    assert not r.poll(now=1.0)
    assert "mod_a" in r.error
    assert t.speak() == "old"          # last good code still runs
    assert not r.poll(now=2.0)         # a bad save errors once, not every poll

    write(pkg, "mod_a", A_V2)
    assert r.poll(now=3.0)
    assert r.error == ""
    assert t.speak() == "new"


def test_dataclass_backfill(pkg):
    mod_a = importlib.import_module("hotpkg.mod_a")
    importlib.import_module("hotpkg.mod_b")
    st = mod_a.State(a=9)
    r = _reloader(lambda: [(st, "mod_a", "State")])

    write(pkg, "mod_a", A_V2)
    assert r.poll(now=1.0)
    assert st.a == 9                   # existing state untouched
    assert st.b == 2.5                 # new field backfilled from default
    assert st.c == [1, 2]              # and from default_factory


def test_downstream_change_leaves_leaf_alone(pkg):
    mod_a = importlib.import_module("hotpkg.mod_a")
    mod_b = importlib.import_module("hotpkg.mod_b")
    t = mod_a.Thing()
    r = _reloader(lambda: [(t, "mod_a", "Thing")])

    write(pkg, "mod_b", "from .mod_a import VALUE\n\ndef get():\n    return VALUE + 10\n")
    assert r.poll(now=1.0)
    assert mod_b.get() == 11
    assert t.speak() == "old"          # mod_a was not reloaded
    assert not hasattr(t, "rebuilt")   # and its instances were not touched


def test_watchers_are_polled_on_the_same_cadence():
    calls = []
    w = SimpleNamespace(poll=lambda now: calls.append(now) or True, status="library: x")
    r = HotReloader(list, package="hotpkg", modules=(), period=1.0, watchers=[w])
    assert not r.poll(now=10.0)                       # no module changed
    assert calls == [10.0] and r.status == "library: x"
    r.poll(now=10.5)
    assert calls == [10.0]                            # gated by the same period


# ------------------------------------------------- the package's own watch list

def _watched() -> tuple[str, ...]:
    from hyperspace.hotreload import MODULES

    return MODULES


def _app_swap_targets() -> set[tuple[str, str]]:
    """Every (module, class) pair app.py hands the reloader, read from the
    source of the `HotReloader(targets=lambda: [...])` call itself so the
    test and the app cannot drift apart."""
    import ast

    tree = _tree("app")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "HotReloader":
            (lam,) = [k.value for k in node.keywords if k.arg == "targets"]
            pairs = {(t.elts[1].value, t.elts[2].value)
                     for t in ast.walk(lam.body)
                     if isinstance(t, ast.Tuple) and len(t.elts) == 3
                     and all(isinstance(e, ast.Constant) for e in t.elts[1:])}
            assert pairs
            return pairs
    raise AssertionError("app.py builds no HotReloader")


def _source(name: str) -> Path:
    """The file behind `hyperspace.<name>`, without importing it (dream.py
    needs torch at import time)."""
    import hyperspace

    root = Path(hyperspace.__file__).parent / name.replace(".", "/")
    # `library.py` sits beside the `library/` preset folder: the file wins
    return root.with_suffix(".py") if root.with_suffix(".py").exists() else root / "__init__.py"


def _tree(name: str):
    import ast

    return ast.parse(_source(name).read_text())


def test_every_swap_target_lives_in_a_watched_module():
    """Audit H1: a swap target whose module is not watched can never fire,
    and the class it names must be defined (not merely re-exported) there."""
    import ast

    for mod, cls in sorted(_app_swap_targets()):
        assert mod in _watched(), f"{mod}.{cls} is a swap target but {mod} is not watched"
        defined = {n.name for n in _tree(mod).body if isinstance(n, ast.ClassDef)}
        assert cls in defined, f"{cls} is not defined in {mod}"


def test_every_package_module_but_the_cold_core_is_watched():
    """Everything under hyperspace/ except app (its loop is on the stack)
    and hotreload itself; a new module goes on the list the day it lands."""
    import hyperspace

    root = Path(hyperspace.__file__).parent
    names = set()
    for f in root.rglob("*.py"):
        parts = list(f.relative_to(root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            names.add(".".join(parts))
    # offline is the tests' oracle harness; watchdog is cold like app — it
    # must outlive whatever a reload does, being what diagnoses a freeze
    # headless (row 394) is the tests' and tools/migrate_library.py's app,
    # never the running app's
    # pinch is cold too: its AppKit monitor adds to the module it was made
    # in, so a reloaded copy would sum nothing
    cold = {"app", "hotreload", "offline", "watchdog", "headless", "pinch"}
    assert names - cold == set(_watched()), sorted((names - cold) ^ set(_watched()))


def _module_level_from_imports(name: str) -> set[str]:
    """The watched modules `hyperspace.<name>` binds names from at module
    level (`from .x import y`, `from ..x import y`). A bare `from . import
    x` binds the module object, which a reload re-executes in place, so it
    is not an ordering constraint."""
    import ast

    pkg = name if _source(name).name == "__init__.py" else name.rpartition(".")[0]
    deps = set()
    for node in _tree(name).body:
        if not (isinstance(node, ast.ImportFrom) and node.level and node.module):
            continue
        base = pkg
        for _ in range(node.level - 1):                # `from ..x`: one package up
            base = base.rpartition(".")[0]
        target = f"{base}.{node.module}" if base else node.module
        deps.add(target)
        for alias in node.names:                      # `from .hands import panel`
            if f"{target}.{alias.name}" in _watched():
                deps.add(f"{target}.{alias.name}")
    return deps


def test_the_watch_list_is_in_dependency_order():
    """A module that `from .x import Name`s another must come after it, or a
    save of x leaves the importer holding the stale Name."""
    order = {m: i for i, m in enumerate(_watched())}
    late = []
    for name in _watched():
        for dep in _module_level_from_imports(name):
            if dep in order and order[dep] > order[name]:
                late.append(f"{name} imports {dep} but comes first")
    assert not late, late


def test_outputs_is_watched_before_render():
    """Plan 21 WP1: render.py imports `Switches`, `View` and `route` from
    outputs.py, so a save of outputs.py reloads render.py after it."""
    order = _watched()
    assert "outputs" in order and order.index("outputs") < order.index("render")


def test_dotted_names_reach_a_subpackage_module(pkg):
    """`hands.core` in MODULES is sys.modules['hyperspace.hands.core']."""
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    write(sub, "leaf", "def get():\n    return 1\n")
    importlib.invalidate_caches()
    leaf = importlib.import_module("hotpkg.sub.leaf")
    r = HotReloader(list, package="hotpkg", modules=("sub.leaf",), period=0.0)
    write(sub, "leaf", "def get():\n    return 2\n")
    assert r.poll(now=1.0)
    assert leaf.get() == 2
    for name in ("hotpkg.sub", "hotpkg.sub.leaf"):
        sys.modules.pop(name, None)


# ------------------------------------------------- an Enum survives a reload

A_ENUM_V1 = """
    from enum import Enum

    VALUE = 1

    class Kind(Enum):
        A = "a"
        B = "b"

    class Holder:
        def __init__(self):
            self.kind = Kind.B

        def is_b(self):
            return self.kind is Kind.B
"""

A_ENUM_V2 = A_ENUM_V1.replace("return self.kind is Kind.B", "return self.kind is Kind.B  # edited")
A_ENUM_V3 = A_ENUM_V1.replace('B = "b"', 'B = "b"\n        C = "c"')


def test_an_enum_a_reloaded_module_defines_keeps_its_identity(pkg):
    """Audit H2: re-executing a module built a new Enum class, so every
    live member stopped matching `is`. The reloader puts the first class
    back; a member added in the edit is reported and needs a restart."""
    write(pkg, "mod_a", A_ENUM_V1)
    mod_a = importlib.import_module("hotpkg.mod_a")
    importlib.import_module("hotpkg.mod_b")
    kind, h = mod_a.Kind, mod_a.Holder()
    r = _reloader(lambda: [(h, "mod_a", "Holder")])

    write(pkg, "mod_a", A_ENUM_V2)
    assert r.poll(now=1.0) and r.error == ""
    assert mod_a.Kind is kind and h.kind is mod_a.Kind.B and h.is_b()

    write(pkg, "mod_a", A_ENUM_V3)
    assert r.poll(now=2.0) and r.error == ""
    assert mod_a.Kind is kind and h.is_b()          # identity still held…
    assert "mod_a.Kind changed" in r.restart        # …and the new member needs a restart

    write(pkg, "mod_a", A_ENUM_V2)                  # a clean save later
    assert r.poll(now=3.0) and r.error == ""
    assert "mod_a.Kind changed" in r.restart        # the note stays until the restart


def test_a_module_imported_after_the_reloader_is_seen_not_reloaded(pkg):
    """A module that first lands in sys.modules after __init__ (an adapter
    opened later) has no recorded mtime; the first poll records it and
    reloads nothing. The next real edit to it reloads as usual."""
    mod_a = importlib.import_module("hotpkg.mod_a")
    t = mod_a.Thing()
    r = _reloader(lambda: [(t, "mod_a", "Thing")])
    mod_b = importlib.import_module("hotpkg.mod_b")   # after the reloader was built
    assert not r.poll(now=1.0)
    assert r.error == "" and r.status == ""
    assert not hasattr(t, "rebuilt")

    write(pkg, "mod_b", "from .mod_a import VALUE\n\ndef get():\n    return VALUE + 10\n")
    assert r.poll(now=2.0)
    assert mod_b.get() == 11


def test_a_syntax_error_names_the_file_by_its_path(pkg):
    """`hands/core.py:12`, not `hands.core.py:12`."""
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    write(sub, "leaf", "def get():\n    return 1\n")
    importlib.invalidate_caches()
    importlib.import_module("hotpkg.sub.leaf")
    r = HotReloader(list, package="hotpkg", modules=("sub.leaf",), period=0.0)
    write(sub, "leaf", "def (broken\n")
    assert not r.poll(now=1.0)
    assert r.error.startswith("hotpkg/sub/leaf.py:1:")
    for name in ("hotpkg.sub", "hotpkg.sub.leaf"):
        sys.modules.pop(name, None)


def test_an_unimported_optional_module_is_skipped(pkg):
    """dream, bridge and midi are watched but only imported behind their
    config gates; a cascade through one that is off must not KeyError."""
    mod_a = importlib.import_module("hotpkg.mod_a")
    write(pkg, "mod_opt", "VALUE = 0\n")            # on disk, never imported
    t = mod_a.Thing()
    r = HotReloader(lambda: [(t, "mod_a", "Thing")], package="hotpkg",
                    modules=("mod_a", "mod_opt", "mod_b"), period=0.0)
    write(pkg, "mod_a", A_V2)
    assert r.poll(now=1.0), r.error
    assert t.speak() == "new"
    assert "hotpkg.mod_opt" not in sys.modules


KIND_SCRIPT = """
import sys
from hyperspace.hotreload import HotReloader
from hyperspace import params as P
from hyperspace.params import Kind, Registry

reg = Registry()
st = {"on": False}
p = reg.toggle("x.on", "X", lambda: st["on"], lambda v: st.__setitem__("on", v))
r = HotReloader(lambda: [(reg, "params", "Registry"), (p, "params", "Param")],
                modules=("params",), period=0.0)
r._mtimes["params"] = 0.0                    # as if params.py had just been saved
assert r.poll(now=1.0), r.error
assert P.Kind is Kind, "Kind was re-created by the reload"
assert p.kind is P.Kind.TOGGLE
p.toggle()
assert st["on"] is True, "toggle() no longer recognises its own kind"
assert type(p) is P.Param and p.text()
print("ok")
"""


def test_reloading_params_keeps_kind_identity():
    """The same rule on the real module: a params.py reload through the
    reloader keeps `Kind`, and a live toggle still toggles. In a subprocess,
    because a real reload of hyperspace.params would leave this test
    session's other modules holding stale classes."""
    import subprocess

    out = subprocess.run([sys.executable, "-c", KIND_SCRIPT], capture_output=True, text=True,
                         check=False, cwd=str(Path(__file__).parents[1]), timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"
