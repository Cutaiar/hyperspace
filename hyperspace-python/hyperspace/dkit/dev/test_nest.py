"""Nested layout, against Chromium's own.

`test_flex.py` pins ONE line of flex to the browser. This pins the tree: a
column whose height is the sum of its children, a row whose height is the
tallest of them, and what `auto` resolves to inside a padded parent. Nesting
is where a hand-written layout drifts, and it drifts quietly - every box
still has a plausible size, just not the right one.

    node hyperspace/dkit/dev/nest_oracle.js > hyperspace/dkit/dev/nestgolden.json
    uv run python -m pytest hyperspace/dkit/dev/test_nest.py -q

No GL and no display: this is arithmetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

from hyperspace.dkit import box as B

CASES = json.loads((HERE / "nestcases.json").read_text())["cases"]
GOLD = json.loads((HERE / "nestgolden.json").read_text())


def build(spec: dict, path: str = "") -> B.Node:
    """A nestcases.json node into a box.Node, keyed by its path in the tree
    so the golden's `.0.1` addressing lines up."""
    return B.Node(
        w=spec.get("w"), h=spec.get("h"),
        dir=spec.get("dir", "column"),
        gap=float(spec.get("gap", 0.0)),
        pad=tuple(spec.get("pad", (0, 0, 0, 0))),
        grow=float(spec.get("grow", 0.0)),
        shrink=float(spec.get("shrink", 1.0)),
        justify=spec.get("justify", "start"),
        align=spec.get("align", "stretch"),
        key=path,
        kids=tuple(build(k, f"{path}.{i}")
                   for i, k in enumerate(spec.get("kids", ()))),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_matches_chromium(case):
    want = GOLD[case["id"]]
    root = build(case["root"])
    x, y, w, h = case["at"]
    B.measure_tree(root)
    got = B.place_tree(
        root,
        B.Rect(float(x), float(y),
               root.mw if w is None else float(w),
               root.mh if h is None else float(h)),
    )
    assert set(got) == set(want), (
        f"node set differs: {sorted(set(got) ^ set(want))}")
    for path in sorted(want):
        gx, gy, gw, gh = want[path]
        r = got[path]
        for name, a, b in (("x", r.x, gx), ("y", r.y, gy),
                           ("w", r.w, gw), ("h", r.h, gh)):
            assert abs(a - b) < 0.02, (
                f"{case['id']} node {path!r} {name}: "
                f"kit {a:.3f} vs chromium {b:.3f}")


def test_the_golden_was_actually_captured():
    """A golden silently missing a case would make this suite vacuous."""
    assert len(GOLD) == len(CASES)
    assert all(c["id"] in GOLD for c in CASES)
    assert all(len(GOLD[c["id"]]) > 1 for c in CASES)
