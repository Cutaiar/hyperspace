"""Every cross-module reference in the kit resolves on the module it names.

This exists for `HANDOFF.md` item 3. `box.py`, `interact.py` and
`comp_combobox.py` are to be split, and there are ~190 `B.x` / `I.x` / `C.x`
references across seventeen files — so the split has to leave those modules
as facades that re-export, or it is not a refactor, it is a rewrite of every
call site.

The test is DERIVED from the call sites rather than being a snapshot of the
public surface, which matters both ways round:

* it cannot go stale. A name nobody uses is not pinned, so the split is free
  to stop exporting it; a name somebody uses is pinned automatically, with no
  list to maintain.
* it fails the moment a facade is incomplete, naming the attribute and the
  file that wanted it — which is the one failure mode of a move-and-reexport
  that import-time errors do NOT catch, because `from x import *` and an
  explicit re-export list both import cleanly while missing names.

It is a static read of the source: no GL context, no window, and it covers
modules a test would otherwise have to boot one for.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# The kit's runtime is a package now (`hyperspace/dkit`); each of its
# modules keeps a one-line alias here, so both folders are read, and an
# import inside the package (`from . import tokens as T`, `from .tokens
# import RADII`) is the same binding as the bare one outside it.
PKG = HERE.parents[1] / "hyperspace" / "dkit"

# Modules whose attributes are checked. The kit's own, not third-party:
# `imgui.*` and `np.*` are not ours to keep stable.
OURS = {p.stem for p in [*HERE.glob("*.py"), *PKG.glob("*.py")]
        if not p.stem.startswith("test_") and p.stem != "__init__"}

# Attributes reached only inside a `try`/`except AttributeError` or via
# getattr-with-default are deliberately optional; none exist today, and if
# one is added it belongs here with a reason rather than silently passing.
OPTIONAL: dict[tuple[str, str], str] = {}


def _alias_map(tree: ast.Module) -> dict[str, str]:
    """{local name -> module name} for `import x as y` of OUR modules."""
    out = {}
    for n in ast.walk(tree):
        for name, asname in _module_imports(n):
            out[asname or name] = name
    return out


def _module_imports(n) -> list[tuple[str, str | None]]:
    """(module, as) for each of OUR modules node `n` imports as a module:
    `import x as y`, and inside the package `from . import x as y`."""
    if isinstance(n, ast.Import):
        return [(a.name, a.asname) for a in n.names if a.name in OURS]
    if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module is None:
        return [(a.name, a.asname) for a in n.names if a.name in OURS]
    return []


def _bound(fn) -> set[str]:
    """Every name bound anywhere inside one function body.

    Needed because an import alias can be SHADOWED locally, and then the
    attribute belongs to something else entirely. `test_components.py` does
    exactly this: `import draw as D` at the top and `D = _dashboard()` inside
    a test, so `D.lay_out` is the dashboard's, not draw's. The first version
    of this scanner reported those two as dangling references on a module
    that was fine - RETRO rows 35 and 51, a probe reporting a defect that is
    not there, which is why it was checked before being believed.
    """
    out = set()
    for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs:
        out.add(a.arg)
    for a in (fn.args.vararg, fn.args.kwarg):
        if a:
            out.add(a.arg)
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
    return out


def _local_imports(fn) -> dict[str, str]:
    """{local name -> module} for `import x as y` INSIDE one function.

    The kit does this constantly - `import menu as M` inside a function, to
    keep a module-level cycle from forming - and such an import is not a
    shadow of the same alias at module level, it is the same binding stated
    twice. Treating it as one made seven files report no references at all,
    which is how it was noticed: the skip count moved, not the pass count.
    """
    out = {}
    for n in ast.walk(fn):
        for name, asname in _module_imports(n):
            out[asname or name] = name
    return out


def _refs(path: Path):
    """(alias_module, attr, lineno) for every `alias.attr` in one file.

    Scope-aware: a reference inside a function that rebinds the alias is not
    a reference to the imported module. See `_bound`.
    """
    tree = ast.parse(path.read_text())
    aliases = _alias_map(tree)
    found = []

    def walk(node, scope: dict, shadowed: frozenset):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local = _local_imports(node)
            scope = {**scope, **local}
            # bound locally AND not by an import of the same module
            hides = (_bound(node) & set(scope)) - set(local)
            shadowed = shadowed | hides
        for child in ast.iter_child_nodes(node):
            if (isinstance(child, ast.Attribute)
                    and isinstance(child.value, ast.Name)
                    and child.value.id in scope
                    and child.value.id not in shadowed):
                found.append((scope[child.value.id], child.attr,
                              child.lineno))
            walk(child, scope, shadowed)

    walk(tree, dict(aliases), frozenset())
    return found


def _from_imports(path: Path):
    """(module, name, lineno) for every `from <our module> import <name>`.

    A second, stricter constraint on a facade than `_refs`: these fail at
    IMPORT time, so they are loud - but only in a module something imports,
    and they are the couplings most likely to be missed, because several of
    them reach for PRIVATE names across a module boundary.
    """
    tree = ast.parse(path.read_text())
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module in OURS and n.level in (0, 1):
            for al in n.names:
                if al.name != "*":
                    out.append((n.module, al.name, n.lineno))
    return out


SOURCES = sorted([*HERE.glob("*.py"), *(p for p in PKG.glob("*.py") if p.stem != "__init__")])


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_every_cross_module_reference_resolves(path):
    refs = _refs(path)
    if not refs:
        pytest.skip("no references to the kit's own modules")
    missing = []
    for mod_name, attr, line in refs:
        if (mod_name, attr) in OPTIONAL:
            continue
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:                      # pragma: no cover
            pytest.skip(f"{mod_name} will not import here: {exc}")
        if not hasattr(mod, attr):
            missing.append(f"{path.name}:{line} wants {mod_name}.{attr}")
    assert not missing, (
        "a module does not export something that is used:\n  "
        + "\n  ".join(missing)
        + "\n\nIf this is a facade after a split, re-export the name."
    )


def test_the_check_actually_finds_references():
    """A test derived from the source has to be shown to be reading it: if
    `_refs` silently returned nothing, every case above would pass vacuously.
    This is RETRO row 20's rule applied to the scanner rather than the code.
    """
    total = sum(len(_refs(p)) for p in SOURCES)
    assert total > 300, f"only {total} cross-module references found"
    # and the three modules item 3 splits are among the most referenced
    counted: dict[str, int] = {}
    for p in SOURCES:
        for mod, _attr, _line in _refs(p):
            counted[mod] = counted.get(mod, 0) + 1
    for m in ("box", "interact", "draw", "tokens"):
        assert counted.get(m, 0) > 10, f"{m}: only {counted.get(m, 0)} refs"


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_every_from_import_resolves(path):
    """`from box import Rect` has to keep working through a split too."""
    refs = _from_imports(path)
    if not refs:
        pytest.skip("no from-imports of the kit's own modules")
    missing = []
    for mod_name, name, line in refs:
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:                      # pragma: no cover
            pytest.skip(f"{mod_name} will not import here: {exc}")
        if not hasattr(mod, name):
            missing.append(f"{path.name}:{line} wants {mod_name}.{name}")
    assert not missing, (
        "a from-import names something the module does not export:\n  "
        + "\n  ".join(missing))


def test_the_private_names_that_cross_a_module_boundary_are_known():
    """The couplings a split is most likely to break, listed on purpose.

    A module's `_private` names are normally free to move. These are not:
    another module imports them by name, so a split that leaves them behind
    breaks at import. `HANDOFF.md` item 3 (3a-3c) grew this from two entries
    to nine; each one it added carries the reason beside it. Item 3a added
    none, because the box model's privates had no outside callers and the
    facade does not re-export them.

    This is a LEDGER, not a prohibition - if a split moves one, update the
    list and the importer together. It exists so the next person finds them
    before the ImportError does.
    """
    crossing = {}
    for p in SOURCES:
        for mod, name, _line in _from_imports(p):
            if name.startswith("_"):
                crossing.setdefault(f"{mod}.{name}", set()).add(p.name)
    assert crossing == {
        # item 3c moved these two out of comp_combobox with the rest of the
        # row model. comp_command imports them from the new home; the other
        # importers are the widget and the two pure modules split beside it.
        "combobox_items._is_row": {"comp_command.py", "comp_combobox.py",
                                   "combobox_measure.py"},
        "combobox_items._k": {"comp_command.py", "comp_combobox.py",
                              "combobox_measure.py", "combobox_select.py"},
        # item 3c: the widget reads both; neither had another caller.
        "combobox_measure._rows_node": {"comp_combobox.py"},
        "combobox_select._MISSING": {"comp_combobox.py"},
        # item 3b: the facade re-exports it because
        # test_a_fractional_delta_marks_the_device_precise_for_good flips
        # `I._PRECISE["seen"]`. Safe only while wheel.py MUTATES the dict
        # and never rebinds it - see wheel.py's docstring.
        "wheel._PRECISE": {"interact.py"},
        # item 3b: the primitives left in interact.py ARE the sandwich's
        # callers, so these cross by construction. comp_combobox also reaches
        # `I._sandwich_end` through the facade, which `_refs` covers.
        "uictx._sandwich_begin": {"interact.py"},
        "uictx._sandwich_end": {"interact.py"},
    }, (
        "the set of PRIVATE names imported across modules changed:\n  "
        + "\n  ".join(f"{k} <- {sorted(v)}" for k, v in sorted(crossing.items())))
