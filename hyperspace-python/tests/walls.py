"""What the import walls share (`test_*_boundary.py`, row 788): a wall names a module by its
stem and holds wherever that module's code goes when it is split, so a split can't step out
from behind it by moving the code to a new file. `audio` is `audio.py`, every `audio_*.py`
beside it, and everything under an `audio/` package."""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "hyperspace"


def family(stem: str, pkg: Path = PKG) -> list[Path]:
    """`stem`'s files. Empty is an error: a wall on nothing would pass for ever."""
    found = [pkg / f"{stem}.py", *pkg.glob(f"{stem}_*.py"), *(pkg / stem).rglob("*.py")]
    out = sorted(f for f in found if f.is_file())
    assert out, f"the wall names {stem}, and {pkg} has no such module"
    return out


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
