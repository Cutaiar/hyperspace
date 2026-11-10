"""Flex conformance: every case in flexcases.json, against Chromium.

`flex_oracle.js` lays the cases out in a real browser and writes
flexgolden.json; this asserts `box.flex` agrees. Writing a flex
implementation from a reading of the spec and hoping is exactly the kind of
thing that stays subtly wrong forever — so conformance is a measurement,
the same trick the chrome diff uses.

    node hyperspace/dkit/dev/flex_oracle.js > hyperspace/dkit/dev/flexgolden.json   # regenerate
    uv run python -m pytest hyperspace/dkit/dev/test_flex.py -q

No GL, no display, no browser needed to run the tests — only to regenerate
the golden.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

from hyperspace.dkit.box import Item, Rect, flex

CASES = json.loads((HERE / "flexcases.json").read_text())["cases"]
GOLDEN = json.loads((HERE / "flexgolden.json").read_text())

# Chromium lays out in LayoutUnit, which is 1/64 px, so its reported rects
# are quantised: space-around over 3 items gave 241.656 (= 15466/64) where
# the exact value is 241.6667. The tolerance is that quantum, not slack —
# anything larger would hide a real disagreement.
TOL = 1.0 / 64 + 1e-6

JUSTIFY = {"flex-start": "start", "flex-end": "end", "center": "center",
           "space-between": "space-between", "space-around": "space-around",
           "space-evenly": "space-evenly"}
ALIGN = {"flex-start": "start", "flex-end": "end", "center": "center",
         "stretch": "stretch"}


def run(c) -> list[Rect]:
    items = []
    for it in c["items"]:
        w, h = it[0], it[1]
        grow = it[2] if len(it) > 2 else 0.0
        shrink = it[3] if len(it) > 3 else 1.0
        items.append(Item(w, h, grow, shrink))
    return flex(Rect(0, 0, *c["box"]), items,
                direction=c["dir"], gap=c["gap"],
                justify=JUSTIFY[c["justify"]], align=ALIGN[c["align"]],
                pad=tuple(c["pad"]))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_the_browser(case):
    got = run(case)
    want = GOLDEN[case["id"]]
    assert len(got) == len(want)
    for i, (g, w) in enumerate(zip(got, want)):
        assert g.x == pytest.approx(w[0], abs=TOL), f"{case['id']}[{i}].x"
        assert g.y == pytest.approx(w[1], abs=TOL), f"{case['id']}[{i}].y"
        assert g.w == pytest.approx(w[2], abs=TOL), f"{case['id']}[{i}].w"
        assert g.h == pytest.approx(w[3], abs=TOL), f"{case['id']}[{i}].h"


def test_every_case_is_covered_by_the_golden():
    assert {c["id"] for c in CASES} == set(GOLDEN)


def test_empty_is_empty():
    assert flex(Rect(0, 0, 100, 20), []) == []


def test_is_fast_enough_for_a_panel():
    """The whole reason this is hand-written rather than Taffy. A panel-sized
    layout must not cost a meaningful slice of a 16.7ms frame — and it is
    cached on container size anyway, so this is the worst case."""
    import time
    items = [Item(120, 20, grow=(i % 3 == 0)) for i in range(40)]
    box = Rect(0, 0, 1440, 34)
    flex(box, items)
    t0 = time.perf_counter()
    for _ in range(2000):
        flex(box, items)
    us = (time.perf_counter() - t0) / 2000 * 1e6
    assert us < 400, f"{us:.0f}us for 40 items is too slow"
    print(f"\n  40-item row: {us:.0f} us  "
          f"({us / 16700 * 100:.2f}% of a frame, uncached)")
