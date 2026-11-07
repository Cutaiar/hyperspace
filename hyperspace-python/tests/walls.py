"""What the import walls share (`test_*_boundary.py`, row 788): a wall names a module by its
stem and holds wherever that module's code goes when it is split, so a split can't step out
from behind it by moving the code to a new file. `audio` is `audio.py`, every `audio_*.py`
beside it, and everything under an `audio/` package.

`family` runs while pytest collects, so it never raises: an error there would stop the whole
tier. A stem with no file comes back as the file it should be, and the tests reading it fail
by name, with `test_type_ratchet.py::test_every_module_a_wall_names_is_there`."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


def family(stem: str, pkg: Path = PKG) -> list[Path]:
    """`stem`'s files. Never empty: a wall on nothing would pass for ever."""
    found = [pkg / f"{stem}.py", *pkg.glob(f"{stem}_*.py"), *(pkg / stem).rglob("*.py")]
    return sorted(f for f in found if f.is_file()) or [pkg / f"{stem}.py"]


def shown(f: Path, pkg: Path = PKG) -> str:
    """A file as a test's id: `audio.py`, `hands/core.py`."""
    return f.relative_to(pkg).as_posix()


def imports(path: Path) -> list[tuple[str, int]]:
    """(module, level) for every import in the file, lazy ones too."""
    out = []
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.ImportFrom):
            out.append((n.module or "", n.level))
        elif isinstance(n, ast.Import):
            out += [(a.name, 0) for a in n.names]
    return out


def module_of(path: Path, pkg: Path = PKG) -> tuple[str, ...]:
    """A file's place below the package: `hands/core.py` is ("hands", "core"), and a package's
    `__init__.py` is the package."""
    parts = path.relative_to(pkg).with_suffix("").parts
    return parts[:-1] if parts[-1] == "__init__" else parts


def inside(path: Path, mod: str, level: int, pkg: Path = PKG) -> tuple[str, ...] | None:
    """What a relative import in `path` names, below the package; None if it climbs out. A bare
    `from . import x` names the package it's in, not x, so a wall reading x refuses it."""
    here = module_of(path, pkg)
    base = here if path.name == "__init__.py" else here[:-1]
    if level - 1 > len(base):
        return None
    return (*base[: len(base) - (level - 1)], *(mod.split(".") if mod else ()))


class Reach(NamedTuple):
    """One import: `mod` as written; `ours`, what it names below the package (empty if it climbs
    out, None if it isn't ours); `lazy`, inside a function."""
    mod: str
    ours: tuple[str, ...] | None
    lazy: bool


def reaches(path: Path, pkg: Path = PKG) -> list[Reach]:
    """Every import in the file. `from . import x` names x, unlike `inside`, one Reach a name."""
    out: list[Reach] = []
    depth = 0

    def named(mod: str, level: int, a: str | None) -> tuple[str, ...]:
        full = mod if a is None else f"{mod}.{a}" if mod else a
        return inside(path, full, level, pkg) or ()

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            nonlocal depth
            depth += 1
            self.generic_visit(node)
            depth -= 1

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ImportFrom(self, node):
            mod = node.module or ""
            if node.level and not mod:
                out.extend(Reach(a.name, named("", node.level, a.name), depth > 0) for a in node.names)
            elif node.level:
                out.append(Reach(mod, named(mod, node.level, None), depth > 0))
            elif mod == "hyperspace":
                out.extend(Reach(a.name, (a.name,), depth > 0) for a in node.names)
            elif mod.startswith("hyperspace."):
                out.append(Reach(mod, tuple(mod.split(".")[1:]), depth > 0))
            else:
                out.append(Reach(mod, None, depth > 0))

        def visit_Import(self, node):
            for a in node.names:
                ours = tuple(a.name.split(".")[1:]) if a.name.split(".")[0] == "hyperspace" else None
                out.append(Reach(a.name, ours, depth > 0))

    V().visit(ast.parse(path.read_text()))
    return out
