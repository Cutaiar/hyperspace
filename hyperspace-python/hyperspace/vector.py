"""Vector subjects (the Flow mark, after PR #214): a subject read from an
SVG instead of built from a formula.

An SVG mark made of pill-shaped bars is read as its stadia: each filled
`<path>` is walked (absolute and relative M L H V C S Q T Z), its on-curve
and control points bound it, and the bar is the stadium that box holds —
its axis the box's long middle line, its end radius half the short side.
A path that is not a stadium (an on-curve point off the pill's outline)
is refused by name: an arbitrary outline would need extruding with a
bevel, which the browser prototype does (`prototypes/subjects/`) and the
app does not yet.

`geometry` builds the subjects from what this returns
(`_build_stadia_flat`, `_build_stadia_capsules`), so another pill mark is
an SVG under `hyperspace/marks/` and two catalog lines.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

MARKS = Path(__file__).with_name("marks")

_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtZzAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "Z": 0}
# how far an on-curve point may sit off the stadium's outline, in end radii
STADIUM_TOL = 0.02


@dataclass(frozen=True)
class Stadium:
    """One pill in the source's own units, y down as SVG draws it: the
    centres of its two ends (a, b) and the end radius r."""
    a: tuple[float, float]
    b: tuple[float, float]
    r: float


def path_points(d: str) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """(on-curve points, every point including control points) of an SVG
    path `d`, made absolute. An arc (A) is refused: no mark here uses one."""
    toks = _TOKEN.findall(d)
    on: list = []
    every: list = []
    x = y = 0.0
    start = (0.0, 0.0)
    cmd = None
    k = 0
    while k < len(toks):
        t = toks[k]
        if t.isalpha():
            cmd = t
            k += 1
            if cmd in "Aa":
                raise ValueError("an arc (A) in an SVG mark is not read")
            if cmd in "Zz":
                x, y = start
                on.append((x, y))
            continue
        if cmd is None or cmd in "Zz":
            raise ValueError(f"an SVG path with a number where a command belongs: {d[:24]!r}")
        up = cmd.upper()
        n = _ARGS[up]
        args = toks[k:k + n]
        if len(args) < n or any(s.isalpha() for s in args):
            raise ValueError(f"an SVG path's {cmd} is short of numbers")
        nums = [float(v) for v in args]
        k += n
        ox, oy = (x, y) if cmd.islower() else (0.0, 0.0)
        if up == "H":
            pts = [(ox + nums[0], y)]
        elif up == "V":
            pts = [(x, oy + nums[0])]
        else:
            pts = [(ox + nums[j], oy + nums[j + 1]) for j in range(0, n, 2)]
        every.extend(pts)
        x, y = pts[-1]
        on.append((x, y))
        if up == "M":
            start = (x, y)
            cmd = "l" if cmd.islower() else "L"   # numbers after a moveto are linetos
    return on, every


def _to_segment(p, a, b) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def stadium_of(d: str) -> Stadium:
    """The stadium an SVG path draws, or ValueError if it draws another
    outline (an on-curve point off the pill's edge)."""
    on, every = path_points(d)
    if not on:
        raise ValueError("an empty SVG path")
    xs, ys = [p[0] for p in every], [p[1] for p in every]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if h >= w:
        r = w / 2
        a, b = (cx, y0 + r), (cx, y1 - r)
    else:
        r = h / 2
        a, b = (x0 + r, cy), (x1 - r, cy)
    if r <= 0:
        raise ValueError("an SVG path with no width")
    for p in on:
        if abs(_to_segment(p, a, b) - r) > STADIUM_TOL * r:
            raise ValueError(f"an SVG path that is not a stadium (a point at {p})")
    return Stadium(a, b, r)


def read_stadia(path: Path) -> tuple[list[Stadium], tuple[float, ...]]:
    """Every `<path>` of the SVG file as a Stadium, left to right, and the
    SVG's viewBox (x, y, w, h): the artboard the mark is centred on."""
    root = ElementTree.parse(path).getroot()
    box = root.get("viewBox")
    if box:
        vb = tuple(float(v) for v in box.replace(",", " ").split())
    else:
        vb = (0.0, 0.0, float(root.get("width")), float(root.get("height")))
    out = [stadium_of(el.get("d", "")) for el in root.iter()
           if el.tag.rsplit("}", 1)[-1] == "path"]
    if not out:
        raise ValueError(f"{path.name}: no <path> to read")
    return sorted(out, key=lambda s: (s.a[0] + s.b[0], s.a[1] + s.b[1])), vb


def mark(name: str) -> tuple[list[Stadium], tuple[float, ...]]:
    """A mark shipped under hyperspace/marks/, by its file stem."""
    return read_stadia(MARKS / f"{name}.svg")
