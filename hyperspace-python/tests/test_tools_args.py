"""An argparse attribute is a string in disguise: `--preset` makes `args.preset`, and a rename of
the reads alone crashes the tool on its first run, which no import shows (review of SEM's rename).
Every `args.x` a tool reads must be a flag or a `dest` that tool declares."""

import ast
from pathlib import Path

import pytest

TOOLS = sorted((Path(__file__).resolve().parents[1] / "tools").glob("*.py"))


def dests(tree: ast.Module) -> set[str]:
    out = {"func"}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_subparsers":
            out |= {k.value.value for k in n.keywords if k.arg == "dest"}
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument":
            dest = next((k.value.value for k in n.keywords if k.arg == "dest"), None)
            flags = [a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            long = [f for f in flags if f.startswith("--")] or flags
            out.add(dest or long[0].lstrip("-").replace("-", "_"))
    return out


@pytest.mark.parametrize("tool", TOOLS, ids=lambda p: p.stem)
def test_every_args_attribute_a_tool_reads_is_a_flag_it_declares(tool):
    tree = ast.parse(tool.read_text())
    declared = dests(tree)
    if declared == {"func"}:
        return                      # (no argparse here)
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}   # (a dict called args)
    read = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and id(n) not in called
            and isinstance(n.value, ast.Name) and n.value.id == "args"}
    assert not read - declared, read - declared
