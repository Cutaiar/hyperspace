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


def _modulate_calls(path: Path):
    """Every `<something>.modulate(...)` call in the file, as (line, enclosing def)."""
    tree = ast.parse(path.read_text())
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in ast.walk(node):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "modulate"):
                out.append((n.lineno, node.name))
    return out


def test_only_router_modulate_calls_param_modulate():
    """The one performer path: `Param.modulate` has exactly one caller in
    the package, `Router.modulate` in routing.py. Adapters only `feed`."""
    calls = {}
    for path in sorted(PKG.rglob("*.py")):
        for line, fn in _modulate_calls(path):
            calls.setdefault(path.relative_to(PKG).as_posix(), []).append((line, fn))
    # app.py calls router.modulate(...) — the pass itself, not a Param write
    calls.pop("app.py", None)
    assert list(calls) == ["routing.py"], calls
    assert calls["routing.py"] and all(fn == "modulate" for _, fn in calls["routing.py"]), \
        calls["routing.py"]
    assert len(calls["routing.py"]) == 1, calls["routing.py"]
