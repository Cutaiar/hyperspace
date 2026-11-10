"""The names `tools/` looks things up by, against the tables that spell them.

The app addresses a face pattern, an instance layout and an instance motion
by INDEX, so respelling those tables cannot break it — and the suite says
so. The tools do not: several of them pick a look by NAME
(`PATTERN_NAMES.index("bloom")`, `m.name == "hex"`), and nothing in the
fast tier runs a tool, because each one opens a GL window and renders.

So a respelling breaks them silently, which is exactly what happened when
the interface stopped shouting (2026-11-10): four tools went on asking for
`BLOOM`, `FCC`, `HEX` and `CUBIC`, and every one would have raised
`ValueError` the next time somebody made a demo. The review caught it; this
is the test that would have.

It reads the tools as TEXT rather than importing them: importing a tool
pulls in GL, and what is being checked is which names the source asks for,
which is a property of the source.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from hyperspace.field import NAMES as LAYOUTS
from hyperspace.params import INST_LAYOUT, INST_MOTION
from hyperspace.patterns import NAMES as MODE_NAMES

TOOLS = Path(__file__).resolve().parents[1] / "tools"

# the table each name a tool asks for has to be in. `NAMES` is imported from
# two places (`field` and `patterns`) and the tools spell it the same way, so
# a name under that one is allowed to be in either.
TABLES = {
    "NAMES": set(LAYOUTS) | set(MODE_NAMES),
    "PATTERN_NAMES": set(MODE_NAMES),
    "INST_LAYOUT": set(INST_LAYOUT),
    "INST_MOTION": set(INST_MOTION),
    "MODE_NAMES": set(MODE_NAMES),
}
# `m.name == "hex"` over `MODES`: the attribute, and which table it names
BY_ATTR = {"name": set(MODE_NAMES) | set(LAYOUTS)}


def _tool_files() -> list[Path]:
    return sorted(p for p in TOOLS.glob("*.py") if not p.name.startswith("_"))


def _asked(tree: ast.AST) -> list[tuple[int, str, str]]:
    """(line, table, name) for every lookup by name in `tree`."""
    out: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        # TABLE.index("name")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "index" and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in TABLES):
            out.append((node.lineno, node.func.value.id, node.args[0].value))
        # m.name == "hex"
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and isinstance(node.left, ast.Attribute)
                and node.left.attr in BY_ATTR
                and isinstance(node.comparators[0], ast.Constant)
                and isinstance(node.comparators[0].value, str)):
            out.append((node.lineno, f".{node.left.attr}", node.comparators[0].value))
    return out


def test_every_name_a_tool_looks_up_is_in_its_table():
    """The lookups themselves. A tool that asks for a name no table spells
    raises `ValueError` the moment it runs, and no other test runs it."""
    bad: list[str] = []
    for path in _tool_files():
        for line, table, name in _asked(ast.parse(path.read_text())):
            allowed = TABLES.get(table) or BY_ATTR.get(table.lstrip("."), set())
            if name not in allowed:
                bad.append(f"{path.name}:{line}: {table} has no {name!r}")
    assert not bad, "a tool asks for a name no table spells:\n" + "\n".join(bad)


def test_a_tool_that_takes_a_name_from_the_command_line_folds_its_case():
    """The other half, and the one a lookup test cannot see: an argument
    somebody types. Both of these used to force the case — `.upper()` on
    `--only`, and a default spelled in capitals — so `--only rings` was
    turned into `RINGS` and refused before anything rendered.

    Read as text because both lines sit inside a `main` that needs GL.
    """
    sheets = (TOOLS / "faces_sheets.py").read_text()
    only = next(ln for ln in sheets.splitlines() if "a.only.split" in ln)
    assert ".lower()" in only, f"faces_sheets --only does not fold case: {only.strip()}"

    shots = (TOOLS / "layout_shots.py").read_text()
    for arg in ("layout", "motion"):
        line = next(ln for ln in shots.splitlines()
                    if f'reg["view.inst_{arg}"].set(' in ln)
        assert f"{arg}.lower()" in line, f"layout_shots --page {arg} does not fold case"
    sig = next(ln for ln in shots.splitlines() if ln.startswith("def page("))
    for word in re.findall(r'"([A-Za-z]+)"', sig):
        assert word.islower() or "." in word, f"page()'s default is capitalised: {word}"


@pytest.mark.parametrize("table", sorted(TABLES))
def test_the_tables_themselves_are_lower_case(table):
    """The interface's own rule (DECISIONS, 2026-11-10), so a name added
    later cannot quietly bring the capitals back."""
    odd = [n for n in TABLES[table] if n != n.lower()]
    assert not odd, f"{table} holds capitals: {sorted(odd)}"
