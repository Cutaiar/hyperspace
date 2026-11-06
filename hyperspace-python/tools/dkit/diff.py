"""Diff the ImGui gallery against the React oracle, per cell.

    uv run python tools/dkit/diff.py /tmp/dkit

Two metrics, because one is not enough:

* STRICT — plain per-pixel max-channel delta. On straight edges, fills and flat
  regions the two rasterizers should agree exactly, so this must be 0 there. It
  is what catches a systematic half-pixel or whole-pixel misalignment.
* TOLERANT — the same delta, but a pixel may match any pixel within 1px in the
  other image (a 3x3 min, taken both directions so neither image can hide a
  feature). This is the agreed bar, "chrome matches within ~1px", stated
  geometrically.

The split matters: a 0.4px geometric difference across a black-on-white
antialiased edge is a ~115-level value delta. Judging an AA corner by STRICT
would report a failure that is really sub-pixel agreement; judging a straight
edge by TOLERANT alone would hide a real 1px offset. So corners are held to
TOLERANT and everything else to STRICT.

Run on the chrome pass (text hidden). Glyph rasterization is out of scope by
agreement — two rasterizers never agree, and the kit's job is the box.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import contour as C

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "spec.json").read_text())

PAD = 8            # how far outside a cell's rect to look, for chrome spill


def load(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGB")).astype(np.int16)


def _shifts(a: np.ndarray) -> list[np.ndarray]:
    """The 9 one-pixel translations of `a`, edge-padded."""
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    return [p[1 + dy: 1 + dy + a.shape[0], 1 + dx: 1 + dx + a.shape[1]]
            for dy in (-1, 0, 1) for dx in (-1, 0, 1)]


def tolerant_delta(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Max-channel delta allowing a 1px search, symmetric in a and b."""
    fwd = np.minimum.reduce([np.abs(a - s).max(axis=2) for s in _shifts(b)])
    rev = np.minimum.reduce([np.abs(b - s).max(axis=2) for s in _shifts(a)])
    return np.maximum(fwd, rev)


def corner_mask(shape: tuple[int, int]) -> np.ndarray:
    """True where a rounded corner arc lives.

    Walks contour.sub_boxes rather than the cell rect, so a slider's thumb
    and a switch's thumb - whose arcs are nowhere near their cell's corners -
    are excluded from the strict metric too. Leaving them in it would fail a
    third of a pixel of rasterizer disagreement as a hundred-level error,
    which is the thing the two-metric split exists to prevent.
    """
    m = np.zeros(shape, bool)
    for c in SPEC["cells"]:
        if c["kind"] not in C.KIND:
            continue
        for bx, by, bw, bh, r, _ring, outset, _only in C.sub_boxes(c):
            # the corner box must also cover chrome that lives outside the
            # box - a card's ring sits at x-1 and its shadow reaches ~3px
            # further, and a slider thumb's hover ring reaches 3px
            k = int(np.ceil(r)) + 2 + outset
            x = int(np.floor(bx - outset))
            y = int(np.floor(by - outset))
            w = int(np.ceil(bw + 2 * outset))
            h = int(np.ceil(bh + 2 * outset))
            for cx, cy in ((x, y), (x + w - k, y), (x, y + h - k),
                           (x + w - k, y + h - k)):
                m[max(cy, 0): cy + k, max(cx, 0): cx + k] = True
    return m


def vector_mask(shape: tuple[int, int]) -> np.ndarray:
    """True where a NON-AXIS-ALIGNED vector feature is drawn.

    Excluded from the strict metric for the reason corners are: that metric
    is the test for straight edges, fills and flat areas, where the two
    rasterizers must agree exactly. A round line cap and a 45 degree
    silhouette are neither. See contour.icon_boxes for what is in here and
    what each one measures instead - nothing is simply dropped: the chevron
    still has to land on the right pixels, and the arrow's area is reported
    below.
    """
    m = np.zeros(shape, bool)
    for c in SPEC["cells"]:
        for ix, iy, iw, ih in C.icon_boxes(c):
            m[max(int(iy), 0):int(np.ceil(iy + ih)),
              max(int(ix), 0):int(np.ceil(ix + iw))] = True
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--tol", type=int, default=2,
                    help="value delta a flat-region pixel may carry and still pass")
    ap.add_argument("--arc", type=float, default=1.0,
                    help="corner displacement allowed, in pixels")
    a = ap.parse_args()
    d = Path(a.dir)

    react, mine = load(d / "react.png"), load(d / "imgui.png")
    if react.shape != mine.shape:
        print(f"FAIL size: react {react.shape} vs imgui {mine.shape}")
        return 2

    strict = np.abs(react - mine).max(axis=2)
    tol = tolerant_delta(react, mine)
    corners = corner_mask(strict.shape) | vector_mask(strict.shape)
    arcs = C.measure(react.astype(float), mine.astype(float))

    print(f"canvas {react.shape[1]}x{react.shape[0]}   "
          f"flat tol {a.tol} levels   corner bar {a.arc} px")
    print(f"{'cell':22} {'flat: edges+fills':>20} {'corners (px)':>14}   verdict")
    print("-" * 76)

    failed = []
    for c in SPEC["cells"]:
        if c["kind"] not in C.KIND:      # text: measured by ink extent, see README
            continue
        # a Switch is 18.390625 px tall, so cell rects are not all integers
        x0, y0 = max(int(c["x"]) - PAD, 0), max(int(c["y"]) - PAD, 0)
        x1 = min(int(np.ceil(c["x"] + c["w"])) + PAD, strict.shape[1])
        y1 = min(int(np.ceil(c["y"] + c["h"])) + PAD, strict.shape[0])
        sl = (slice(y0, y1), slice(x0, x1))

        flat = ~corners[sl]                       # straight edges, fills, bg
        s_bad = int((strict[sl][flat] > a.tol).sum())
        s_max = int(strict[sl][flat].max()) if flat.any() else 0

        v = arcs.get(c["id"])
        arc = float(np.abs(v).max()) if v is not None and len(v) else float("nan")
        arc_ok = not (arc > a.arc)                # NaN (unsampled) does not fail

        ok = s_bad == 0 and arc_ok
        if not ok:
            failed.append(c["id"])
        print(f"{c['id']:22} max {s_max:3} / {s_bad:5} px   "
              f"{arc:10.3f}     {'ok' if ok else 'FAIL'}")

    inside = np.zeros(strict.shape, bool)
    for c in SPEC["cells"]:
        inside[max(int(c["y"]) - PAD, 0):int(np.ceil(c["y"] + c["h"])) + PAD,
               max(int(c["x"]) - PAD, 0):int(np.ceil(c["x"] + c["w"])) + PAD] = True
    bg = int((strict[~inside] > a.tol).sum())

    # text is advisory, so keep it out of the chrome summary
    textmask = np.zeros(strict.shape, bool)
    for c in SPEC["cells"]:
        if c["kind"] not in C.KIND:
            textmask[int(c["y"]):int(np.ceil(c["y"] + c["h"])),
                     int(c["x"]):int(np.ceil(c["x"] + c["w"]))] = True
    chrome = ~corners & ~textmask

    allarc = [float(np.abs(v).max()) for v in arcs.values() if len(v)]
    print("-" * 76)
    print(f"background pixels differing at all: {bg}")
    print(f"worst flat-region delta: {int(strict[chrome].max())} levels   "
          f"worst corner displacement: {max(allarc):.3f} px")

    # --- advisory: text, by ink extent (never a pass/fail) ------------------
    rows = [c for c in SPEC["cells"] if c["kind"] not in C.KIND]
    if rows:
        ga = react.max(axis=2)
        gb = mine.max(axis=2)

        def ink(img, c):
            box = img[int(c["y"]):int(np.ceil(c["y"] + c["h"])),
                      int(c["x"]):int(np.ceil(c["x"] + c["w"]))]
            # the page may be light-on-dark, so measure the departure from the
            # cell's own background rather than assuming dark ink
            bgv = np.median(np.concatenate([box[0], box[-1]]))
            r = np.abs(box.astype(int) - bgv) > 55
            if not r.any():
                return None
            ys, xs = np.where(r)
            return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)

        print()
        print("text (advisory - ink extent, px):")
        print(f"  {'cell':14} {'react':>9} {'imgui':>9} {'dw':>4} {'dh':>4}")
        for c in rows:
            ia, ib = ink(ga, c), ink(gb, c)
            if not ia or not ib:
                continue
            print(f"  {c['id']:14} {ia[0]:4}x{ia[1]:<4} {ib[0]:4}x{ib[1]:<4} "
                  f"{ib[0] - ia[0]:+4} {ib[1] - ia[1]:+4}")

    # --- advisory: the tooltip arrow, by area ------------------------------
    # A 45 degree edge is out of the strict metric, so the arrow is checked
    # as a SHAPE instead: total ink over its exposed tip, in square pixels.
    # Robust to how either rasterizer spreads its antialiasing.
    tips = [c for c in SPEC["cells"] if c["kind"] == "tooltip"]
    if tips:
        print()
        print("tooltip arrow (advisory - exposed tip area, px^2):")
        for c in tips:
            ax, ay, aw, ah = C.arrow_box(c)
            sl = (slice(int(ay), int(np.ceil(ay + ah)) + 1),
                  slice(int(ax), int(np.ceil(ax + aw)) + 1))
            # coverage against the panel's own fill and the page behind it
            fgv = float(react[int(c["y"]) + 4, int(c["x"]) + int(c["w"] / 2)].max())
            bgv = float(react[int(ay + ah) + 4, int(ax)].max())
            if abs(fgv - bgv) < 8:
                continue
            cov = lambda im: float(np.clip(
                (im[sl].max(axis=2) - bgv) / (fgv - bgv), 0, 1).sum())
            ca, cb = cov(react), cov(mine)
            print(f"  {c['id']:14} react {ca:7.3f}   imgui {cb:7.3f}   "
                  f"{cb - ca:+.3f}")

    amp = np.clip(tol.astype(np.int32) * 4, 0, 255).astype(np.uint8)
    sheet = np.concatenate(
        [react.astype(np.uint8), mine.astype(np.uint8), np.dstack([amp] * 3)],
        axis=1)
    Image.fromarray(sheet).save(d / "contact.png")
    print(f"wrote {d / 'contact.png'}  (react | imgui | tolerant diff x4)")

    if failed or bg:
        print(f"\nFAILING: {', '.join(failed) if failed else '(background)'}")
        return 1
    print("\nall cells within the bar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
