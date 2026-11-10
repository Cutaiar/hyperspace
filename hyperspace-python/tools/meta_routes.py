#!/usr/bin/env python3
"""List the rows a library holds that the hard rule will drop (register row 743).

    uv run python tools/meta_routes.py <library path>

**Read-only. It writes nothing,** to the library or anywhere else, and the
path has no default: **the owner runs this.** No patch row may drive a meta
controller param (`params.is_meta_id`), so a load drops such a
row with a note (`routing.referee`, `Bindings.set_desk`, `routing.settle_bases`)
and the next save of that loadable patch writes the file without it. This says, before
any of that happens, which files hold one, and so which params to think about
moving into the loadable patch.

The documents read, every folder down as the library lists them (plan 48; not
``trash/``, not a dot-folder):

- the loadable patches, ``<library>/presets/**/*.json``: their ``routes`` and ``desk``
  rows and their macros' base and depth subscribers. Each is **dropped at load**;
- the patches, ``<library>/patches/**/*.json``: the same keys. A patch naming
  one is **refused whole** when it is read (`patches.check`, register row 744),
  so it says so: edit the file, or take the row out and save the patch again.

A file that does not parse, or holds a row or subscriber this build cannot read,
is named and passed over. A row's `scale` naming a
meta param is not listed: it reads the param and never moves it (row 18 (a)).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.library import _walk
from hyperspace.routing import Binding, Macro, meta_row_refusal

LOADABLE, PATCHES = "loadable", "patches"


@dataclass(frozen=True)
class Found:
    """One row that would drop: the file, the key and the row in words."""
    path: Path
    key: str
    pair: str                # "source → target", or the subscriber's
    words: str               # the row as listed


def documents(folder: Path) -> Iterator[Path]:
    """Every JSON file the library's walker lists under `folder`, less the trash."""
    for p in _walk(folder):
        if "trash" not in p.relative_to(folder).parts:
            yield p


def _row(path: Path, key: str, r: Mapping, layer: str | None) -> Found | None:
    """`r`, if it is a row the rule refuses: the door's own test."""
    if not isinstance(r.get("source"), str) or not isinstance(r.get("target"), str):
        return None
    b = Binding.from_json({**r, "layer": layer} if layer else dict(r))
    if meta_row_refusal(b) is None:
        return None
    pair = f"{b.source} → {b.target}"
    return Found(path, key, pair, f"{pair}  {b.op} {b.value}")


def _subs(path: Path, macros: Mapping) -> Iterator[Found]:
    for mid, m in macros.items():
        for pid in Macro.from_json(m).meta_subs():
            pair = f"{mid} → {pid}"
            yield Found(path, "macros", pair, pair)


def scan_doc(path: Path, doc: Mapping) -> list[Found]:
    """What in one parsed document the rule refuses."""
    found: list[Found] = []
    for key, layer in (("routes", None), ("desk", "preset")):
        rows = doc.get(key) or ()
        for r in rows if isinstance(rows, list) else ():
            hit = _row(path, key, r, layer) if isinstance(r, Mapping) else None
            if hit is not None:
                found.append(hit)
    macros = doc.get("macros")
    if isinstance(macros, Mapping):
        found += _subs(path, macros)
    return found


def scan(folder: Path) -> tuple[int, list[Found], list[str]]:
    """(documents read, what they hold, the files that did not parse)."""
    n, found, bad = 0, [], []
    for p in documents(folder):
        try:
            doc = json.loads(p.read_text())
            hits = scan_doc(p, doc) if isinstance(doc, Mapping) else []
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
            bad.append(f"{p}: {e!r}")
            continue
        n += 1
        found += hits
    return n, found, bad


def report(library: Path, kind: str, then: str, out: Iterable[Found], n: int) -> list[str]:
    found = list(out)
    files = {f.path for f in found}
    lines = [f"{kind}: {len(found)} row(s) in {len(files)} of {n} file(s), {then}"]
    lines += [f"  {f.path.relative_to(library / kind)}  [{f.key}]  {f.words}" for f in found]
    for pair, k in Counter(f.pair for f in found).most_common():
        lines.append(f"  {k:4d} × {pair}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("library", type=Path, help="the library folder (read, never written)")
    a = ap.parse_args(argv)
    if not a.library.is_dir():
        print(f"no such folder: {a.library}", file=sys.stderr)
        return 2
    lines: list[str] = []
    bad: list[str] = []
    for kind, then in ((LOADABLE, "dropped at the next load of each"),
                       (PATCHES, "each patch refused whole when read")):
        n, found, unread = scan(a.library / kind)
        lines += report(a.library, kind, then, found, n)
        bad += unread
    lines += [f"could not read {b}" for b in bad]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
