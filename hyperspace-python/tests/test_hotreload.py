"""HotReloader semantics, driven against a throwaway two-module package.

mod_a is the leaf, mod_b imports from it — the same shape as the real
package (bands → ui), so the rebind and partial-reload rules get exercised
without touching hyperspace's own modules on disk.
"""

import importlib
import os
import sys
import textwrap
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
