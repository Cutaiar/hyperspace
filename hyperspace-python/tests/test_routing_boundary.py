"""routing.py's boundaries. The referee lives in the table's edit doors
(`Bindings.add` / `bind` / `enable` / `replace_owner`), and
`Router.modulate` never checks ownership — so the model holds only if
`Router.modulate` is the one place a performer's offset is written
(ARCHITECTURE §3.2, audit B8). An AST walk over the package holds that.
WP8 adds the import boundary and the frame-order test here. Plan 44 D2
extends the wall and the pin to routing_sources.py, the router's shared
half (`Sources`): below routing, and writing no param.
"""

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


class _Calls(ast.NodeVisitor):
    """Every `<receiver>.modulate(...)` call in a module, module level
    included, with the innermost enclosing def (or None)."""

    def __init__(self):
        self.stack: list[str] = []
        self.found: list[tuple[int, str | None, str]] = []

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "modulate":
            recv = ast.unparse(f.value)
            self.found.append((node.lineno, self.stack[-1] if self.stack else None, recv))
        self.generic_visit(node)


def test_only_router_modulate_calls_param_modulate():
    """The one performer path: `Param.modulate` has exactly one caller in
    the package, `Router.modulate` in routing.py. Adapters only `feed`.
    Calls on a *router* (`router.modulate(...)`, the pass itself) are the
    frame loop's and are the only ones excluded."""
    calls = {}
    for path in sorted(PKG.rglob("*.py")):
        v = _Calls()
        v.visit(ast.parse(path.read_text()))
        for line, fn, recv in v.found:
            if recv.split(".")[-1] == "router":
                continue                      # the pass, not a Param write
            calls.setdefault(path.relative_to(PKG).as_posix(), []).append((line, fn, recv))
    assert list(calls) == ["routing.py"], calls
    assert calls["routing.py"] == [(calls["routing.py"][0][0], "modulate", "p")], calls


# the calls that write a param (a Param's writers and the registry's
# commit): the shared sources make none — what they hold is read by each
# deck's pass, which writes its own registry (plan 44 D2). `step` is left
# out: a Follower's `step` (motion.py) is arithmetic, not a write
WRITES = {"modulate", "set", "set_norm", "nudge", "fire", "toggle", "apply", "restore",
          "begin_frame", "snapshot"}


def test_the_shared_sources_write_no_param():
    """The AST pin extended to the new file: routing_sources.py calls no
    param writer — no `modulate`, no `set`, no `apply` — and names no
    registry or param, so the one performer path stays `Router.modulate`
    and a `Sources` shared by two decks cannot write either's values."""
    tree = ast.parse((PKG / "routing_sources.py").read_text())
    found = [(n.lineno, n.func.attr) for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in WRITES]
    assert not found, found
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"Registry", "Param", "reg"}, names & {"Registry", "Param", "reg"}


# ---- the import boundary (audit R11) ----

# what routing.py may never import, at module level or lazily: the panel,
# the host, and every adapter that feeds it — they point at the table, the
# table points at the registry (ARCHITECTURE §1). Plan 44 D2: the same wall
# holds for routing_sources.py, which sits below routing (routing imports
# it back), so it may import neither routing nor the registry it never
# writes, nor anything that imports them
ABOVE = ("ui", "app", "hands", "midi", "bridge", "learn", "dream", "hotreload", "library")
SOURCES_ABOVE = (*ABOVE, "routing", "params", "loadable", "undo", "deck", "devices")
WALLS = {"routing.py": ABOVE, "routing_sources.py": SOURCES_ABOVE}
# the lazy imports each file is allowed: name resolution for key and pad
# rows (§1's "only lazily to resolve names") — pinned so a new one is a
# decision (the Library `Router.load_patch` took went with it, plan 13
# WP5). Plan 44 D2 moved that resolution (`_resolve`, behind
# `Sources.code`) into routing_sources.py, so routing.py has none now
LAZY = {"routing.py": set(), "routing_sources.py": {"glfw", "gamepad"}}


def _imports(tree):
    """(module, level, inside_a_def) for every import in the tree."""
    out = []
    stack = 0

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            nonlocal stack
            stack += 1
            self.generic_visit(node)
            stack -= 1

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ImportFrom(self, node):
            if node.level and not node.module:      # `from . import gamepad`
                out.extend((a.name, node.level, stack > 0) for a in node.names)
            else:
                out.append((node.module or "", node.level, stack > 0))

        def visit_Import(self, node):
            out.extend((a.name, 0, stack > 0) for a in node.names)

    V().visit(tree)
    return out


@pytest.mark.parametrize("name", sorted(WALLS))
def test_routing_imports_nothing_above_it(name):
    tree = ast.parse((PKG / name).read_text())
    lazy = set()
    for mod, level, inside in _imports(tree):
        if level == 0 and not mod.startswith("hyperspace"):
            if inside:
                lazy.add(mod)             # a third-party module imported lazily
            continue                      # the standard library and numpy
        head = mod.split(".")[0] if mod else ""
        if inside:
            lazy.add(head)                # allowed only if LAZY names it, below
            continue
        assert head not in WALLS[name], f"{name} imports {'.' * level}{mod}"
    assert lazy == LAZY[name], lazy


@pytest.mark.parametrize("name", ["routing", "routing_sources"])
def test_importing_routing_pulls_in_no_adapter_or_panel(name):
    """Fresh interpreter: `import hyperspace.routing` — and its shared
    half, plan 44 D2 — leaves the panel, the host and every adapter out of
    sys.modules; the shared half pulls in no registry and no table."""
    import subprocess
    import sys

    code = (f"import sys, hyperspace.{name}; "
            "print(' '.join(sorted(m for m in sys.modules if m.startswith('hyperspace.'))))")
    got = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, cwd=PKG.parent).stdout.split()
    wall = WALLS[f"{name}.py"]
    bad = [m for m in got if m.split(".")[1] in wall]
    assert not bad, bad
    assert f"hyperspace.{name}" in got
    if name == "routing":
        assert "hyperspace.params" in got and "hyperspace.routing_sources" in got
