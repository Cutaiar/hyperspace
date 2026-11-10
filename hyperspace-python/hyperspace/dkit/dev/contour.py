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

import sys as _sys

_sys.path.insert(0, str(HERE))
from hyperspace.dkit.tokens import TOOLTIP

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
    # A Button's radius is SIZE-dependent (8 on the four small sizes, 10
    # above), so `geom` asks comp_button for it rather than trusting this
    # number; the entry carries the default. At rest a button has no chrome
    # outside its border box - the focus ring is a focus state and the
    # gallery is a rest-state pass - so outset is 0.
    #
    # `ring` is False because four of the six variants are FILLED boxes;
    # `geom` already promotes the outline variant, which is the one that
    # reads as a 1px border on an opaque fill. `ghost` and `link` paint
    # nothing at rest, so their radial march finds no step and reports NaN,
    # which does not fail - while the strict flat metric still holds them to
    # painting nothing on both sides, which is the real assertion there.
    # A ContextMenu panel is a menu panel: same radius, same 1px ring 1px
    # outside, same shadow-md. Only its min-width differs, and the cell pins
    # the width anyway.
    "contextmenu": {"radius": 10.0, "outset": 6, "ring": True},
    # The Combobox trigger is an InputGroup measured identical to the
    # Input, at rounded-lg: a 1px border on a transparent fill, so a
    # ring. No focus ring in a rest-state pass, so outset 0.
    "combobox": {"radius": 10.0, "outset": 0, "ring": True},
    "button": {"radius": 10.0, "outset": 0, "ring": False},
    # A group's cell is the whole group. Its four OUTER corners are all
    # rounded at 10 (the first member owns two, the last the other two) and
    # the inner seams are square, so marching the cell's corners is right
    # without sub-boxes. `in-data-[slot=button-group]:rounded-lg` puts every
    # size back to 10, measured.
    "buttongroup": {"radius": 10.0, "outset": 0, "ring": False},
    # rounded-[4px]. Off it is a 1px border on a transparent (light) or
    # near-transparent (dark) fill, which reads as a ring; on it is a filled
    # primary box. `geom` promotes the checked cells to filled.
    "checkbox": {"radius": 4.0, "outset": 0, "ring": True},
    # rounded-sm (6), a filled `muted` box, at the browser's intrinsic
    # size (the width law itself is test_kbd.py's).
    "kbd": {"radius": 6.0, "outset": 0, "ring": False},
}


def geom(cell):
    """(clamped radius, outset, is_ring) for one cell."""
    k = KIND[cell["kind"]]
    radius = k["radius"]
    if cell["kind"] == "select" and cell["variant"] == "sm":
        radius = 8.0                    # sm is rounded-md, not rounded-lg
    if cell["kind"] == "button":
        # Ask the source for it. xs/sm/icon-xs/icon-sm are rounded-md (8) and
        # the rest rounded-lg (10); copying either number here would go stale
        # the moment BUTTON_SIZES moved.
        from hyperspace.dkit import comp_button as CB
        radius = CB.button_radius(cell["size"])
    r = min(radius, min(cell["w"], cell["h"]) / 2.0)
    ring = k["ring"] or cell.get("variant") == "outline"
    if cell["kind"] == "checkbox" and cell.get("on"):
        ring = False                    # a checked box is a filled primary box
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
    from hyperspace.dkit.tokens import SELECT
    if cell["kind"] == "select":
        cs = SELECT["chevron"]
        return [(cell["x"] + cell["w"] - 1.0 - SELECT["pad_r"] - cs,
                 cell["y"] + (cell["h"] - cs) / 2.0, cs, cs)]
    if cell["kind"] == "combobox":
        # The trigger's trailing chevron: the same Lucide `chevron-down` the
        # Select draws, and it differs the same way - body to 2 levels, the
        # outermost pixel of each round cap by up to 59, which is the figure
        # this cell reported on its first run. Geometry from the measured
        # tokens, not from a copy of them.

        from hyperspace.dkit.comp_combobox import COMBOBOX as _CB
        g = _CB["field_icon"]
        return [(cell["x"] + cell["w"] - _CB["field_chevron_right"] - g,
                 cell["y"] + (cell["h"] - g) / 2.0, g, g)]
    if cell["kind"] == "checkbox":
        # The tick, and only on a CHECKED box: an unchecked one has none, and
        # leaving it in the flat metric is what holds both sides to "no tick
        # here" - and keeps the dark `input/30` fill under strict compare.
        #
        # The box is Lucide's own `check` path, scaled into the indicator's
        # 14px padding box as ?probe measured it (14 x 14 at 1,1), padded by
        # a pixel past the stroke. Anchored on the CELL, not on the draw
        # code's constants, so a tick drawn in the wrong place moves the
        # ink and not the hole (RETRO row 44). Its perimeter is all fill,
        # which is the background icon_ink needs.
        if not cell.get("on"):
            return []

        from hyperspace.dkit.icons import BOX, ICONS, STROKE
        pts = [(op[1], op[2]) for sub in ICONS["check"] for op in sub
               if op[0] in ("M", "L")]
        k = (cell["w"] - 2.0) / BOX             # 14 / 24
        pad = STROKE * k / 2.0 + 1.0
        x0 = cell["x"] + 1.0 + min(p[0] for p in pts) * k - pad
        x1 = cell["x"] + 1.0 + max(p[0] for p in pts) * k + pad
        y0 = cell["y"] + 1.0 + min(p[1] for p in pts) * k - pad
        y1 = cell["y"] + 1.0 + max(p[1] for p in pts) * k + pad
        return [(x0, y0, x1 - x0, y1 - y0)]
    if cell["kind"] == "tooltip":
        return [arrow_box(cell)]
    if cell["kind"] == "scroll":
        # Only the thumb's two END CAPS. It is a 7px capsule, so r = 3.5 -
        # under the 3px the radial march can resolve, which drops it into
        # the flat metric where a cap's antialiasing reads as 3-5 levels.
        # Its straight sides stay strict, and they are exact; its geometry
        # is pinned three other ways (test_components against Chromium's own
        # numbers, and a pixel check in the demo against box.scroll_thumb).
        from hyperspace.dkit import box as _B
        from hyperspace.dkit.tokens import SCROLL as _SC
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
# A ContextMenu panel carries the same shadow-md - measured on ?probe as
# the identical two-layer box-shadow - so it has the same two rows.
SOFT_SHADOW = {"menu": 2, "contextmenu": 2}


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


def icon_ink(img, box):
    """An icon's ink MASS and CENTROID inside `box`, for one image.

    The photometric metric cannot judge a stroked icon - a round line cap a
    third of a pixel longer reads as 59 levels - so icon_boxes drops those
    pixels from it. That left the icon measured by nothing at all: its
    position, its colour and even whether it was drawn were invisible, which
    is how the Combobox trigger shipped a chevron 3px too far right in ink
    at half the strength the browser uses. Both bugs were found by eye in the
    first pixel pass and NEITHER could be caught by the cell afterwards,
    because the excluded region is derived from the same token the draw site
    reads - move the token and the hole moves with it.

    Mass and centroid are aggregate, so they survive the cap disagreement
    while still answering the three questions that matter:

      * is it there at all          mass > 0
      * is it in the right place    centroid, to a fraction of a pixel
      * is it the right colour      mass, which scales with the ink's alpha

    `bg` is the median of the box's PERIMETER rather than a token, so this
    works in both themes without being told which. Not the modal level of
    the whole box, which was the first attempt and is degenerate on a small
    box: a scroll thumb's end cap fills most of its own box, so the mode was
    the THUMB and "ink" came out as the background around it - reported as a
    2.36px centroid shift between two images that are pixel-identical there.
    A box's perimeter is background for every shape here: field around a
    chevron, page and track around a cap.

    Returns (mass, cx, cy) with the centroid relative to the box's origin,
    or (0.0, nan, nan) for a box with no ink.
    """
    x, y, w, h = box
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    x1, y1 = int(np.ceil(x + w)), int(np.ceil(y + h))
    sub = img[max(y0, 0):y1, max(x0, 0):x1]
    if sub.size == 0:
        return 0.0, float("nan"), float("nan")
    v = sub.max(axis=2).astype(float) if sub.ndim == 3 else sub.astype(float)
    if min(v.shape) < 3:
        return 0.0, float("nan"), float("nan")
    ring = np.concatenate([v[0, :], v[-1, :], v[1:-1, 0], v[1:-1, -1]])
    bg = float(np.median(ring))
    ink = np.abs(v - bg)
    mass = float(ink.sum())
    if mass <= 0.0:
        return 0.0, float("nan"), float("nan")
    ys, xs = np.mgrid[0:ink.shape[0], 0:ink.shape[1]]
    return (mass,
            float((ink * xs).sum() / mass) + (max(x0, 0) - x),
            float((ink * ys).sum() / mass) + (max(y0, 0) - y))


def miter_pixels(cell):
    """The single pixels where Chromium under-covers a square border corner.

    Measured, and it is a property of the BROWSER, not of the kit. An element
    with any non-zero border-radius has its whole border rasterized as one
    antialiased path, so where two present border segments meet at a corner
    whose radius is 0, each segment's miter edge is drawn at partial coverage
    and the two compose to ~0.75 rather than 1.0. On `border` over white that
    is 235 where full coverage is 229 - a 6-level deficit on exactly one
    pixel per such corner.

    A ButtonGroup is the only place in the kit that mixes radii on one
    element, and the arithmetic picks out precisely the members where it can
    happen:

      * a member with NO rounded corner (a middle one) has its border drawn
        as four axis-aligned rects, with no path antialiasing - measured
        exact at 229;
      * a member whose square corner has one of its two adjoining borders
        DROPPED (the last one's leading corners) has no join to miter -
        also measured exact;
      * which leaves the FIRST member's two trailing corners, in both
        orientations, and nothing else.

    So this is not "the pixels that failed". It is a closed-form list of the
    corners where the browser's own rasterizer cannot reach full coverage,
    and ImGui - which strokes the border as one rect - is the side that is
    geometrically right. Excluded from the strict metric and REPORTED, the
    way soft_shadow_band is.

    Returns [(x, y), ...] in absolute canvas pixels.
    """
    if cell["kind"] != "buttongroup":
        return []
    from hyperspace.dkit import comp_button as CB

    ori = cell["orientation"]
    rects, cx, cy = [], cell["x"], cell["y"]
    for m in cell["members"]:
        if ori == "horizontal":
            rects.append((cx, cell["y"], float(m), cell["h"]))
            cx += m
        else:
            rects.append((cell["x"], cy, cell["w"], float(m)))
            cy += m

    # corner name -> the two sides that meet there, as indices into
    # `borders` = (top, right, bottom, left)
    ADJ = {"tl": (0, 3), "tr": (0, 1), "br": (2, 1), "bl": (2, 3)}
    out = []
    for (x, y, w, h), j in zip(rects, CB.button_group(rects, ori)):
        if not j.corners:                 # no radius at all: plain rects
            continue
        for name, (s0, s1) in ADJ.items():
            if name in j.corners:         # rounded: it is an arc, not a miter
                continue
            if j.borders[s0] <= 0.0 or j.borders[s1] <= 0.0:
                continue                  # a dropped side cannot form a join
            px = x if name in ("tl", "bl") else x + w - 1.0
            py = y if name in ("tl", "tr") else y + h - 1.0
            out.append((int(px), int(py)))
    return out


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
    k = cell["kind"]
    if k == "slider":
        from hyperspace.dkit import box as B
        from hyperspace.dkit.tokens import SLIDER
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
        from hyperspace.dkit import box as B
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
        ("tr", "br") if cell["on"] else ("tl", "bl")
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
    x0, y0 = math.floor(x), math.floor(y)
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
