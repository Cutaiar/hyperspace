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

import sys as _sys                                  # noqa: E402
_sys.path.insert(0, str(HERE))
from tokens import TOOLTIP                           # noqa: E402

# a square of `arrow` px turned 45 degrees has this half-diagonal
TOOLTIP_ARROW_HALF = TOOLTIP["arrow"] * math.sqrt(2.0) / 2.0
# Per-kind chrome geometry: the requested corner radius, how far the chrome
# reaches OUTSIDE the box (a card's ring is 1px out and its shadow ~3), and
# whether the corner reads as a filled step or as a thin ring.
KIND = {
    "badge": {"radius": 26.0, "outset": 0, "ring": False},
    "card":  {"radius": 14.0, "outset": 3, "ring": True},
    # A slider's and a switch's arcs do not sit at their cell's corners -
    # they belong to a thumb somewhere along the track, and to the track's
    # own end caps. So those kinds declare SUB-BOXES (see sub_boxes) and both
    # metrics walk those instead of the cell rect. Without that the thumb's
    # antialiased disc lands in the flat-region metric and reports a failure
    # that is really sub-pixel agreement, which is the exact mistake this
    # module exists to avoid.
    "slider": {"radius": 6.0, "outset": 3, "ring": True},
    "switch": {"radius": 9.195, "outset": 0, "ring": False},
    # Input and the Select trigger are rounded-lg (10); sm is rounded-md (8),
    # which `geom` takes from the cell's variant. Both read as a thin ring
    # (a 1px border on a transparent or near-transparent fill), and the
    # invalid Input's 3px ring reaches 3px outside its box.
    "input": {"radius": 10.0, "outset": 3, "ring": True},
    "select": {"radius": 10.0, "outset": 0, "ring": True},
    # the tooltip panel is a filled rounded-md box
    "tooltip": {"radius": 8.0, "outset": 0, "ring": False},
    # a ScrollArea is a 1px-bordered rounded-lg box; its thumb is a 3.5px
    # capsule, below the 3px the radial march can resolve, so the thumb is
    # held to the flat metric (where it has to be exact anyway)
    "scroll": {"radius": 10.0, "outset": 0, "ring": True},
    # a menu panel: rounded-lg, a 1px ring 1px outside, and shadow-md
    # reaching ~6px further
    "menu": {"radius": 10.0, "outset": 6, "ring": True},
}


def geom(cell):
    """(clamped radius, outset, is_ring) for one cell."""
    k = KIND[cell["kind"]]
    radius = k["radius"]
    if cell["kind"] == "select" and cell["variant"] == "sm":
        radius = 8.0                    # sm is rounded-md, not rounded-lg
    r = min(radius, min(cell["w"], cell["h"]) / 2.0)
    ring = k["ring"] or cell.get("variant") == "outline"
    return r, k["outset"], ring


def icon_boxes(cell):
    """Vector features measured geometrically rather than photometrically.

    Two kinds, both of them NOT axis-aligned, which is the whole reason the
    strict metric does not apply: it is documented as the test for straight
    edges, fills and flat areas, where two rasterizers must agree exactly.

    * icon strokes - the Select's chevron. Its body matches to 2 levels; the
      outermost pixel of each round line cap differs by up to 59, which is a
      cap a third of a pixel longer in one renderer.
    * the Tooltip's arrow - a 45 degree silhouette. Its straight edges agree
      to 0.27 px of width and its area to 7%, but Chromium paints the union
      of the rotated `rounded-[2px]` BOX and Radix's own svg polygon, so the
      tip is blunter than a sharp triangle and sharper than a pure r=2
      diamond. diff.py reports the arrow's area so this stays measured.
    """
    from tokens import SELECT, TOOLTIP
    if cell["kind"] == "select":
        cs = SELECT["chevron"]
        return [(cell["x"] + cell["w"] - 1.0 - SELECT["pad_r"] - cs,
                 cell["y"] + (cell["h"] - cs) / 2.0, cs, cs)]
    if cell["kind"] == "tooltip":
        return [arrow_box(cell)]
    if cell["kind"] == "scroll":
        # Only the thumb's two END CAPS. It is a 7px capsule, so r = 3.5 -
        # under the 3px the radial march can resolve, which drops it into
        # the flat metric where a cap's antialiasing reads as 3-5 levels.
        # Its straight sides stay strict, and they are exact; its geometry
        # is pinned three other ways (test_components against Chromium's own
        # numbers, and a pixel check in the demo against box.scroll_thumb).
        import sys as _s
        _s.path.insert(0, str(HERE))
        import box as _B
        from tokens import SCROLL as _SC
        vp = cell["h"] - 2.0
        t = _B.scroll_thumb(
            cell["x"] + 1.0 + cell["w"] - 2.0 - _SC["bar_w"], cell["y"] + 1.0,
            _SC["bar_w"], vp, vp, float(cell["content"]),
            cell["frac"] * (cell["content"] - vp),
            inset=_SC["track_inset"], thumb_w=_SC["thumb_w"],
            thumb_inset=_SC["thumb_inset"], thumb_min=_SC["thumb_min"])
        if t is None:
            return []
        cap = _SC["thumb_w"] / 2.0 + 1.0
        return [(t.x - 1, t.y - 1, t.w + 2, cap + 1),
                (t.x - 1, t.y + t.h - cap, t.w + 2, cap + 1)]
    return []


# Kinds that carry a SOFT shadow (blur > 4). The two rows against such a
# box's own edge are the one place draw.shadow's stacked rects cannot follow
# Chromium's triple box blur - see draw.shadow. Reported by diff.py as its
# own number rather than silently tolerated.
SOFT_SHADOW = {"menu": 2}


def soft_shadow_band(cell):
    """The band just outside a soft-shadowed box, as a rect, or None."""
    n = SOFT_SHADOW.get(cell["kind"])
    if not n:
        return None
    return (cell["x"] - n, cell["y"] + cell["h"],
            cell["w"] + 2 * n, float(n))


def arrow_box(cell):
    """The Tooltip arrow's exposed tip, as a rect: (x, y, w, h).

    The panel sits above its anchor, so the arrow's centre is `arrow_dy`
    inside the panel's bottom edge and only the part below that edge shows.
    """
    half = TOOLTIP_ARROW_HALF
    vis = half - TOOLTIP["arrow_dy"]
    cx = cell["x"] + cell["w"] / 2.0
    return (cx - vis - 1.0, cell["y"] + cell["h"], 2.0 * vis + 2.0, vis + 2.0)


def sub_boxes(cell):
    """The rounded boxes inside a cell whose arcs are worth measuring.

    For a Badge or a Card that is the cell itself. For a Slider it is each
    thumb (a 1px-bordered disc, so a ring) plus the track's own end caps; for
    a Switch, the track and the thumb. Returns (x, y, w, h, radius, is_ring,
    outset) per box.

    This exists because the radial march below finds a corner by walking out
    from the arc's centre, and a slider thumb's centre is wherever its value
    puts it - nowhere near the cell's corner. Measuring the cell's corners
    instead would sample flat track and return nothing, while leaving the
    thumb's antialiased edge inside the strict metric, where a third of a
    pixel of rasterizer disagreement reads as a hundred levels.

    `corners` exists for a subtler reason, and it was a real false alarm. A
    Switch's thumb sits ON one end of its own track, so that end's arc centre
    is INSIDE the thumb: the ray starts in thumb colour and the step it finds
    is thumb-to-background, not track-to-background. In light that self-
    cancels (thumb and page are both white, so the contrast guard rejects the
    ray) but in dark it does not, and it reported 0.996 px on a track that is
    actually fine. So the track declares only the two corners the thumb is
    not standing on.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    k = cell["kind"]
    if k == "slider":
        import box as B
        from tokens import SLIDER
        track, _, thumbs = B.slider_geom(
            cell["x"], cell["y"], cell["w"], cell["h"], cell["fracs"],
            track_h=SLIDER["track_h"], thumb=SLIDER["thumb"])
        out = [(t.x, t.y, t.w, t.h, t.w / 2.0, True, 3, None) for t in thumbs]
        # the track's rounded ends: a 4px bar, so r = 2 - below the 3px floor
        # the march can resolve, so it contributes nothing and is listed only
        # so corner_mask excludes it from the strict metric.
        out.append((track.x, track.y, track.w, track.h, track.h / 2.0, False,
                    0, None))
        return out
    if k == "switch":
        import box as B
        track, off, on = B.switch_geom(cell["x"], cell["y"], cell["variant"])
        t = on if cell["on"] else off
        # The thumb stands on one end of the track, so each box has one end
        # that cannot be measured and one that can - and they are opposite
        # ends, so between them all four arcs get measured once against a
        # clean background.
        #
        #   * the TRACK's arc on the thumb's end has its centre inside the
        #     thumb, so the ray starts in thumb colour.
        #   * the THUMB's arc on that same end is 1px from the track's edge
        #     (16px thumb in an 18px track), so the ray exits through a
        #     sliver of track into the page: the profile is dark-light-dark
        #     rather than a step, and the 50% crossing is unstable on it.
        #
        # The slider's thumb does not need this: at 12px against a 4px track
        # it overhangs vertically, so its rays reach the page cleanly even at
        # the ends.
        near = ("tr", "br") if cell["on"] else ("tl", "bl")
        far = ("tl", "bl") if cell["on"] else ("tr", "br")
        return [(track.x, track.y, track.w, track.h, track.h / 2.0, False, 0,
                 far),
                (t.x, t.y, t.w, t.h, t.w / 2.0, False, 0, far)]
    r, outset, ring = geom(cell)
    return [(cell["x"], cell["y"], cell["w"], cell["h"], r, ring, outset, None)]

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
    # the ring may be darker than its surround (light theme) or lighter
    # (dark theme), so take the magnitude of the departure either way
    ink = np.abs(vs - v_out)
    if ink.sum() < 1.0:
        return None
    return float((ink * rs).sum() / ink.sum())


def measure(react: np.ndarray, mine: np.ndarray) -> dict:
    out = {}
    for c in SPEC["cells"]:
        if c["kind"] not in KIND:        # text cells are advisory, not chrome
            continue
        deltas = []
        for bx, by, bw, bh, r, ring, _os, only in sub_boxes(c):
          filled = not ring
          # an arc smaller than ~3px spans too few samples for the radial
          # march to resolve; it stays in the flat metric instead
          if r < 3.0:
              continue
          for name, (a0, a1) in CORNERS.items():
            if only is not None and name not in only:
                continue
            cx = bx + r if "l" in name else bx + bw - r
            cy = by + r if "t" in name else by + bh - r
            for ang in np.linspace(a0 + 6, a1 - 6, 14):
                rr, vr = ray(react, cx, cy, ang, r)
                _, vm = ray(mine, cx, cy, ang, r)
                if np.isnan(vr).any() or np.isnan(vm).any():
                    continue
                ch = pick_channel(vr, vm)
                er = edge_radius(rr, vr[:, ch], filled)
                em = edge_radius(rr, vm[:, ch], filled)
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
