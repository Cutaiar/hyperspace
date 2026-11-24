#!/usr/bin/env python3
"""Copy one of this repo's patch sets (``loadable/<set>/``) into the library.

    uv run python tools/copy_patches.py SET        # distort, kinetic …

The library is the folder ``[library] path`` names in ``~/Hyperspace/config.toml``,
read as desktop startup reads it (``config.load()``, `app.main`). The set goes into its
own folder there, ``<library>/loadable/<SET>/`` (`library.loadable_dir`), never loose
into ``loadable/``, and lists as ``<SET>/<name>``.

It refuses, writing nothing, when no ``[library] path`` is set (no library,
2026-11-23), when the folder it names is not there (a missing shared folder is
never created, D5: a mistyped name would fill a folder the app never reads), and
when it is the machine home (never a library).

It never overwrites (as ``tools/move_library.py``, D8): a file the library already
has is left alone — identical is ``have``, different is ``KEPT THEIRS``: the
library's own, perhaps edited and saved since the last copy, is kept and this
repo's is not copied. Quit Hyperspace first or not: the app follows new files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SETS = HERE / "loadable"


def _app():
    """The app's `config` and `library`, imported late (the tool runs from
    anywhere): the repo put on ``sys.path`` once."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from hyperspace import config, library
    return config, library


def sets() -> list[str]:
    """The patch sets this repo has: each folder of ``loadable/`` with a patch in it."""
    return sorted(d.name for d in SETS.iterdir() if d.is_dir() and any(d.glob("*.json")))


def destination() -> Path:
    """``<library>/loadable/``, or SystemExit saying why there is none."""
    config, library = _app()
    raw = config.load()["library"]["path"]
    where = library.home() / "config.toml"
    if not raw:
        raise SystemExit(f"no [library] path in {where}: no library, nothing copied")
    root = Path(raw)
    if not root.is_dir():
        raise SystemExit(f"[library] path {root} is not there: not created, nothing copied "
                         f"(fix the path in {where})")
    if root.resolve() == library.home().resolve():
        raise SystemExit(f"[library] path {root} is this Mac's home, never a library: "
                         f"nothing copied (point it at the shared folder in {where})")
    return library.loadable_dir(root)


def copy(name: str, out=print) -> list[tuple[str, str]]:
    """Copy set `name` in; one ("copied" | "have" | "KEPT THEIRS", file) per patch."""
    src = SETS / name
    files = sorted(src.glob("*.json"))
    if not files:
        raise SystemExit(f"no patch set {name!r}: the sets are {', '.join(sets())}")
    dest = destination() / name
    dest.mkdir(parents=True, exist_ok=True)
    done = []
    for f in files:
        target, data = dest / f.name, f.read_bytes()
        try:
            with open(target, "xb") as fh:       # never replaces a file already there
                fh.write(data)
            what = "copied"
        except FileExistsError:
            what = "have" if target.read_bytes() == data else "KEPT THEIRS"
        done.append((what, f.name))
        if what == "KEPT THEIRS":
            out(f"KEPT THEIRS {f.name} — the library's differs and is kept; "
                f"this repo's is not copied")
    counts = {w: sum(1 for d, _ in done if d == w) for w in ("copied", "have", "KEPT THEIRS")}
    out(f"{dest}: " + ", ".join(f"{n} {w}" for w, n in counts.items() if n))
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("set", help=f"the patch set: {', '.join(sets())}")
    copy(ap.parse_args(argv).set)
    return 0


if __name__ == "__main__":
    sys.exit(main())
