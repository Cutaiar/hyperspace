"""A hot reload through the real swap, over the real app's long-lived objects (HR, row 802).

Plan 44 D5a gave `DeckLibrary` and `DeckProject` slots over a hot base, and from that day
no save before `library` on the list completed: `swap: TypeError: __class__ assignment:
'DeckLibrary' object layout differs from 'DeckLibrary'`. Nothing failed, because every
reload test here ran a throwaway package or an empty target list, and the test of the
target list reads names from source: none ever assigned a `__class__` on one of the app's
own objects. The first test below does; the second names the rule, on every class.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_hotreload import _source, _watched

ROOT = Path(__file__).parents[1]


def test_a_save_reaches_every_live_object_of_the_real_app(gl_window_ok, tmp_path):
    """`app.main`, in a process of its own, with `tools/drive_hot_reload.py` saving the
    first module on the list, so every module reloads and every target is re-classed:
    no error, none left on an old class, `Renderer.on_reload` ran, the frames after it draw."""
    first = _watched()[0]
    env = dict(os.environ, HYPERSPACE_TOUCH=first, TMPDIR=str(tmp_path))
    out = subprocess.run(
        [sys.executable, "tools/app_driver.py", "tools/drive_hot_reload.py",
         "--out", str(tmp_path / "run"), "--every", "100000"],
        capture_output=True, text=True, check=False, cwd=str(ROOT), env=env, timeout=110)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    assert f"reloaded: {first}" in out.stdout, out.stdout[-2000:] + out.stderr[-2000:]


def slots_over_a_hot_base(source: str, hot: set[str]) -> list[str]:
    """The classes in `source` that add slots over a class named in `hot`."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        slots = [s.value for s in node.body
                 if isinstance(s, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "__slots__" for t in s.targets)]
        adds = any(not (isinstance(v, ast.Tuple | ast.List) and not v.elts) for v in slots)
        bases = {b.id if isinstance(b, ast.Name) else b.attr for b in node.bases
                 if isinstance(b, ast.Name | ast.Attribute)}
        if adds and bases & hot:
            found.append(node.name)
    return found


def test_no_hot_class_adds_slots_over_another_hot_class():
    """Python can't re-class such an object once the base was reloaded: the two classes'
    layouts come from two different bases. A class that needs slots there takes them from
    a base in `hotreload.py`, which no reload re-executes. By name, so it needs no import
    of a module behind an optional device (a class that shares a name with a hot one is
    told to look again, which is cheap)."""
    trees = {name: _source(name).read_text() for name in _watched()}
    hot = {n.name for text in trees.values() for n in ast.walk(ast.parse(text))
           if isinstance(n, ast.ClassDef)}
    assert "Library" in hot and "Project" in hot
    wrong = {name: bad for name, text in trees.items()
             if (bad := slots_over_a_hot_base(text, hot))}
    assert not wrong, wrong


@pytest.mark.parametrize(("source", "found"), [
    ("class V(Lib):\n    __slots__ = ('a',)\n", ["V"]),               # what D5a did
    ("class V(mod.Lib):\n    __slots__ = ['a']\n", ["V"]),
    ("class V(Cold, Lib):\n    __slots__ = ()\n", []),                # how it is done
    ("class V(Lib):\n    pass\n", []),
    ("class V(Cold):\n    __slots__ = ('a',)\n", []),
    ("class V:\n    __slots__ = ('a',)\n", []),
])
def test_the_rule_sees_what_it_should(source, found):
    assert slots_over_a_hot_base(source, {"Lib"}) == found


def test_the_decks_views_hold_their_fields_on_a_cold_base():
    from hyperspace import hotreload
    from hyperspace.library import DeckLibrary, DeckProject

    assert issubclass(DeckLibrary, hotreload.DeckLibrarySlots)
    assert issubclass(DeckProject, hotreload.DeckProjectSlots)
    assert "__slots__" not in vars(DeckLibrary) and "__slots__" not in vars(DeckProject)
