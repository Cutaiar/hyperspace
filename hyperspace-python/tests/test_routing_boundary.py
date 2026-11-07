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
from walls import family, module_of, reaches, shown

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


@pytest.mark.parametrize("path", family("routing_sources"), ids=shown)
def test_the_shared_sources_write_no_param(path):
    """The AST pin extended to the new file: routing_sources.py calls no
    param writer — no `modulate`, no `set`, no `apply` — and names no
    registry or param, so the one performer path stays `Router.modulate`
    and a `Sources` shared by two decks cannot write either's values."""
    tree = ast.parse(path.read_text())
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
# Globbed (row 788): a split stays behind its own family's wall, and a name on a wall means its
# split too, `ui` meaning `ui_pane`, as test_app_boundary's gated check does.
FILES = family("routing")
SOURCES = family("routing_sources")
# the lazy imports each family is allowed: name resolution for key and pad
# rows (§1's "only lazily to resolve names") — pinned so a new one is a
# decision (the Library `Router.load_patch` took went with it, plan 13
# WP5). Plan 44 D2 moved that resolution (`_resolve`, behind
# `Sources.code`) into routing_sources.py, so routing.py has none now
LAZY = {"routing": set(), "routing_sources": {"glfw", "gamepad"}}


def _members(family_name: str) -> list:
    return SOURCES if family_name == "routing_sources" else [f for f in FILES if f not in SOURCES]


def _family(path) -> str:
    return "routing_sources" if path in SOURCES else "routing"


def _own(path, head: str) -> bool:
    """`head` is the same family's: a split importing its other half is behind the same wall."""
    return head in {module_of(f)[0] for f in _members(_family(path))}


def _crosses(path, head: str) -> bool:
    wall = SOURCES_ABOVE if path in SOURCES else ABOVE
    return not _own(path, head) and head.split("_")[0] in wall


@pytest.mark.parametrize("path", FILES, ids=shown)
def test_routing_imports_nothing_above_it(path):
    for r in reaches(path):
        if r.ours is None or r.lazy:      # lazy ones are pinned below; the rest are third-party
            continue
        head = r.ours[0] if r.ours else ""
        assert not _crosses(path, head), f"{shown(path)} imports {r.mod}"


@pytest.mark.parametrize("name", sorted(LAZY))
def test_the_lazy_imports_are_the_pinned_ones(name):
    got = set()
    for path in _members(name):
        for r in reaches(path):
            if r.lazy:
                head = r.mod if r.ours is None else (r.ours[0] if r.ours else "")
                if not _own(path, head):
                    got.add(head)
    assert got == LAZY[name], got


def test_a_name_on_a_wall_means_its_split_too():
    routing, sources = PKG / "routing.py", PKG / "routing_sources.py"
    assert _crosses(routing, "ui") and _crosses(routing, "ui_pane")
    assert not _crosses(routing, "params") and not _crosses(routing, "routing_sources")
    assert _crosses(sources, "params_x") and _crosses(sources, "routing")
    assert not _crosses(sources, "routing_sources") and not _crosses(sources, "motion")


@pytest.mark.parametrize("path", FILES, ids=shown)
def test_importing_routing_pulls_in_no_adapter_or_panel(path):
    """Fresh interpreter: `import hyperspace.routing` — and its shared
    half, plan 44 D2 — leaves the panel, the host and every adapter out of
    sys.modules; the shared half pulls in no registry and no table."""
    import subprocess
    import sys

    name = ".".join(module_of(path))
    code = (f"import sys, hyperspace.{name}; "
            "print(' '.join(sorted(m for m in sys.modules if m.startswith('hyperspace.'))))")
    got = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, cwd=PKG.parent).stdout.split()
    bad = [m for m in got if _crosses(path, m.split(".")[1])]
    assert not bad, bad
    assert f"hyperspace.{name}" in got
    if name == "routing":
        assert "hyperspace.params" in got and "hyperspace.routing_sources" in got
