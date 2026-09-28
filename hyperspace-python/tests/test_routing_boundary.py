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
