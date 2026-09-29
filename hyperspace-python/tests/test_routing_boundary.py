"""routing.py's boundaries. The referee lives in the table's edit doors
(`Bindings.add` / `bind` / `enable` / `replace_owner`), and
`Router.modulate` never checks ownership — so the model holds only if
`Router.modulate` is the one place a performer's offset is written
(ARCHITECTURE §3.2, audit B8). An AST walk over the package holds that.
WP8 adds the import boundary and the frame-order test here.
"""

import ast
from pathlib import Path

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


# ---- the import boundary (audit R11) ----

# what routing.py may never import, at module level or lazily: the panel,
# the host, and every adapter that feeds it — they point at the table, the
# table points at the registry (ARCHITECTURE §1)
ABOVE = ("ui", "app", "hands", "midi", "bridge", "learn", "dream", "hotreload", "library")
# the lazy imports routing.py is allowed: name resolution for key and pad
# rows (§1's "only lazily to resolve names") — pinned so a new one is a
# decision (the Library `Router.load_preset` took went with it, plan 13 WP5)
LAZY = {"glfw", "gamepad"}


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


def test_routing_imports_nothing_above_it():
    tree = ast.parse((PKG / "routing.py").read_text())
    lazy = set()
    for name, level, inside in _imports(tree):
        if level == 0 and not name.startswith("hyperspace"):
            if inside:
                lazy.add(name)            # a third-party module imported lazily
            continue                      # the standard library and numpy
        head = name.split(".")[0] if name else ""
        if inside:
            lazy.add(head)                # allowed only if LAZY names it, below
            continue
        assert head not in ABOVE, f"routing.py imports {'.' * level}{name}"
    assert lazy == LAZY, lazy


def test_importing_routing_pulls_in_no_adapter_or_panel():
    """Fresh interpreter: `import hyperspace.routing` leaves the panel,
    the host and every adapter out of sys.modules."""
    import subprocess
    import sys

    code = ("import sys, hyperspace.routing; "
            "print(' '.join(sorted(m for m in sys.modules if m.startswith('hyperspace.'))))")
    got = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, cwd=PKG.parent).stdout.split()
    bad = [m for m in got if m.split(".")[1] in ABOVE]
    assert not bad, bad
    assert "hyperspace.routing" in got and "hyperspace.params" in got
