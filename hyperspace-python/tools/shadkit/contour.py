"""Measure corner-arc agreement geometrically, in pixels.

The agreed bar — "chrome matches within ~1px" — is a statement about geometry,
but a value delta across an antialiased edge is not: a 0.3px difference on a
black-on-white corner is a ~115-level delta, while the same 0.3px on a
#e5e5e5 border is ~7. Both are the same error. So corners are measured as a
distance, not a brightness.

For each rounded corner, march radially out from the arc centre and find where
the ink profile sits in each image:

* a filled badge gives a step — take the 50% crossing;
* an outline badge gives a thin ring — take the ink centroid.

Either way the result is a radius in pixels; the number that matters is the
difference between the two images, in pixels.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "spec.json").read_text())
# Per-kind chrome geometry: the requested corner radius, how far the chrome
# reaches OUTSIDE the box (a card's ring is 1px out and its shadow ~3), and
# whether the corner reads as a filled step or as a thin ring.
KIND = {
    "badge": {"radius": 26.0, "outset": 0, "ring": False},
    "card":  {"radius": 14.0, "outset": 3, "ring": True},
}


def geom(cell):
    """(clamped radius, outset, is_ring) for one cell."""
    k = KIND[cell["kind"]]
    r = min(k["radius"], min(cell["w"], cell["h"]) / 2.0)
    ring = k["ring"] or cell.get("variant") == "outline"
    return r, k["outset"], ring

# (dx, dy) toward the corner's centre, and the angle range of its arc
CORNERS = {
    "tl": (180.0, 270.0),
    "tr": (270.0, 360.0),
    "br": (0.0, 90.0),
    "bl": (90.0, 180.0),
}


def sample(img: np.ndarray, x: float, y: float):
    """Bilinear sample; img may be HxW or HxWx3."""
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    if x0 < 0 or y0 < 0 or x0 + 1 >= img.shape[1] or y0 + 1 >= img.shape[0]:
        return np.full(img.shape[2], np.nan) if img.ndim == 3 else np.nan
    fx, fy = x - x0, y - y0
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def ray(img, cx, cy, ang, r, n=160):
    """Sample along a ray from r*0.45 to r*1.55. Returns (radii, values)."""
    lo, hi = r * 0.45, r * 1.55
    rs = np.linspace(lo, hi, n)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    vs = np.array([sample(img, cx + rr * ca, cy + rr * sa) for rr in rs])
    return rs, vs          # (n,) or (n, 3)


def pick_channel(va, vb) -> int:
    """The channel with the most contrast along the ray, over both images."""
    c = [max(abs(v[0, k] - v[-1, k]) for v in (va, vb)) for k in range(va.shape[1])]
    return int(np.argmax(c))


def edge_radius(rs, vs, filled: bool):
    """Where the boundary sits along this ray, in pixels from the centre."""
    if np.isnan(vs).any():
        return None
    v_in, v_out = vs[0], vs[-1]
    if filled:
        # 4 levels is enough to localise a step to a fraction of a pixel;
        # #f5f5f5 on white is only 10.
        if abs(v_in - v_out) < 4:
            return None
        t = (vs - v_out) / (v_in - v_out)   # 1 inside, 0 outside
        for i in range(len(t) - 1):
            if t[i] >= 0.5 > t[i + 1]:
                f = (t[i] - 0.5) / (t[i] - t[i + 1])
                return float(rs[i] + f * (rs[i + 1] - rs[i]))
        return None
    ink = np.clip(v_out - vs, 0, None)      # a ring darker than its surround
    if ink.sum() < 1.0:
        return None
    return float((ink * rs).sum() / ink.sum())


def measure(react: np.ndarray, mine: np.ndarray) -> dict:
    out = {}
    for c in SPEC["cells"]:
        r, _, ring = geom(c)
        filled = not ring
        deltas = []
        for name, (a0, a1) in CORNERS.items():
            cx = c["x"] + r if "l" in name else c["x"] + c["w"] - r
            cy = c["y"] + r if "t" in name else c["y"] + c["h"] - r
            for ang in np.linspace(a0 + 6, a1 - 6, 14):
                rr, vr = ray(react, cx, cy, ang, r)
                _, vm = ray(mine, cx, cy, ang, r)
                if np.isnan(vr).any() or np.isnan(vm).any():
                    continue
                k = pick_channel(vr, vm)
                er = edge_radius(rr, vr[:, k], filled)
                em = edge_radius(rr, vm[:, k], filled)
                if er is not None and em is not None:
                    deltas.append(em - er)
        out[c["id"]] = np.array(deltas) if deltas else np.array([])
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    a = ap.parse_args()
    d = Path(a.dir)
    react = np.asarray(Image.open(d / "react.png").convert("RGB")).astype(float)
    mine = np.asarray(Image.open(d / "imgui.png").convert("RGB")).astype(float)

    res = measure(react, mine)
    print("corner arc position, imgui minus react, in PIXELS")
    print(f"{'cell':22} {'n':>4} {'mean':>7} {'max|d|':>7}   verdict")
    print("-" * 56)
    worst = 0.0
    for k, v in res.items():
        if not len(v):
            print(f"{k:22} {'--':>4} {'(no arc sampled)':>24}")
            continue
        m = float(np.abs(v).max())
        worst = max(worst, m)
        print(f"{k:22} {len(v):4} {v.mean():+7.3f} {m:7.3f}   "
              f"{'ok' if m <= 1.0 else 'OVER 1px'}")
    print("-" * 56)
    print(f"worst corner displacement anywhere: {worst:.3f} px")
    print("bar is 1.0 px — " + ("PASS" if worst <= 1.0 else "FAIL"))


if __name__ == "__main__":
    main()
