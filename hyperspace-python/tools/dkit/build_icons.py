"""Turn Lucide's geometry into a path table Dear ImGui can stroke.

    cd prototypes/dashboard
    node ../../hyperspace-python/tools/dkit/dump_icons.js > /tmp/lucide.json
    cd ../../hyperspace-python
    uv run python tools/dkit/build_icons.py /tmp/lucide.json

Lucide is a good fit for a draw list: every icon is a 24x24 box of *stroked*
paths, 2px wide, round caps and joins — which is `path_line_to` /
`path_bezier_cubic_curve_to` + `path_stroke` almost exactly. So icons are
vector at any size, take their colour from a token, and need no atlas, no
texture and no new runtime dependency.

Everything awkward is resolved here rather than at runtime:

* relative commands are made absolute;
* `H`/`V` become lines, `circle`/`rect`/`line` become paths;
* **elliptical arcs become cubics**, because ImGui's `path_arc_to` only draws
  circular arcs in the x/y plane and Lucide's `A` commands are not all
  circular. The endpoint parameterisation in SVG 1.1 appendix F.6 gives the
  centre, and each sweep is split into <=90 degree pieces.

Output is `icons.py`: `{name: [[(op, *coords), ...], ...]}` — a list of
subpaths, each a list of ops, where op is "M", "L", "C" or "Z".
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
CMD = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])")

# how many cubic pieces an arc sweep is cut into; 90 degrees each is the
# standard bound for keeping the error under about a thousandth of the radius
ARC_MAX = math.pi / 2


def tokens(d: str):
    """(command, [numbers]) pairs, in order."""
    parts = [p for p in CMD.split(d) if p.strip()]
    i = 0
    while i < len(parts):
        c = parts[i]
        args = [float(n) for n in NUM.findall(parts[i + 1])] if i + 1 < len(parts) \
            and not CMD.fullmatch(parts[i + 1]) else []
        yield c, args
        i += 2 if args else 1


def arc_to_cubics(x0, y0, rx, ry, phi_deg, large, sweep, x, y):
    """SVG elliptical arc -> a list of cubic segments. SVG 1.1 F.6."""
    if rx == 0 or ry == 0 or (x0 == x and y0 == y):
        return [("L", x, y)]
    phi = math.radians(phi_deg)
    cs, sn = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x0 - x) / 2.0, (y0 - y) / 2.0
    x1 = cs * dx2 + sn * dy2
    y1 = -sn * dx2 + cs * dy2
    rx, ry = abs(rx), abs(ry)
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:                       # radii too small: scale them up (F.6.6)
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(num / den, 0.0))
    if large == sweep:
        co = -co
    cx1 = co * rx * y1 / ry
    cy1 = -co * ry * x1 / rx
    cx = cs * cx1 - sn * cy1 + (x0 + x) / 2.0
    cy = sn * cx1 + cs * cy1 + (y0 + y) / 2.0

    def ang(ux, uy, vx, vy):
        d = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1.0, min(1.0, (ux * vx + uy * vy) / d)))
        return -a if ux * vy - uy * vx < 0 else a

    th0 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dth = ang((x1 - cx1) / rx, (y1 - cy1) / ry,
              (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi

    n = max(1, math.ceil(abs(dth) / ARC_MAX))
    step = dth / n
    # the magic constant for approximating a circular arc with one cubic
    k = 4.0 / 3.0 * math.tan(step / 4.0)
    out, th = [], th0
    px, py = x0, y0
    for _ in range(n):
        th1 = th + step
        c0, s0 = math.cos(th), math.sin(th)
        c1, s1 = math.cos(th1), math.sin(th1)

        def pt(c_, s_):
            return (cs * rx * c_ - sn * ry * s_ + cx,
                    sn * rx * c_ + cs * ry * s_ + cy)

        ex, ey = pt(c1, s1)
        d0x, d0y = (-rx * s0, ry * c0)
        d1x, d1y = (-rx * s1, ry * c1)

        def tang(dx_, dy_):
            return (cs * dx_ - sn * dy_, sn * dx_ + cs * dy_)

        t0x, t0y = tang(d0x, d0y)
        t1x, t1y = tang(d1x, d1y)
        out.append(("C", px + k * t0x, py + k * t0y,
                    ex - k * t1x, ey - k * t1y, ex, ey))
        px, py, th = ex, ey, th1
    return out


def path_ops(d: str):
    """An SVG `d` -> subpaths of absolute M/L/C/Z ops."""
    subs, cur = [], []
    x = y = sx = sy = 0.0
    prev = qprev = None
    for c, a in tokens(d):
        up = c.upper()
        rel = c.islower()
        i = 0
        while True:
            if up == "Z":
                if cur:
                    cur.append(("Z",))
                    subs.append(cur)
                    cur = []
                x, y = sx, sy
                break
            if up == "M":
                nx, ny = a[i] + (x if rel else 0), a[i + 1] + (y if rel else 0)
                if cur:
                    subs.append(cur)
                cur = [("M", nx, ny)]
                x, y, sx, sy = nx, ny, nx, ny
                i += 2
                up = "L"                      # extra pairs after M are lineto
            elif up == "L":
                nx, ny = a[i] + (x if rel else 0), a[i + 1] + (y if rel else 0)
                cur.append(("L", nx, ny)); x, y = nx, ny; i += 2
            elif up == "H":
                nx = a[i] + (x if rel else 0)
                cur.append(("L", nx, y)); x = nx; i += 1
            elif up == "V":
                ny = a[i] + (y if rel else 0)
                cur.append(("L", x, ny)); y = ny; i += 1
            elif up == "C":
                c1 = (a[i] + (x if rel else 0), a[i + 1] + (y if rel else 0))
                c2 = (a[i + 2] + (x if rel else 0), a[i + 3] + (y if rel else 0))
                e = (a[i + 4] + (x if rel else 0), a[i + 5] + (y if rel else 0))
                cur.append(("C", *c1, *c2, *e)); x, y = e; i += 6
            elif up == "S":
                rx_, ry_ = (2 * x - prev[0], 2 * y - prev[1]) if prev else (x, y)
                c2 = (a[i] + (x if rel else 0), a[i + 1] + (y if rel else 0))
                e = (a[i + 2] + (x if rel else 0), a[i + 3] + (y if rel else 0))
                cur.append(("C", rx_, ry_, *c2, *e)); x, y = e; i += 4
            elif up in ("Q", "T"):
                # a quadratic raised to a cubic: C1 = P0 + 2/3 (Q - P0),
                # C2 = P2 + 2/3 (Q - P2). ImGui strokes cubics, not quadratics.
                if up == "Q":
                    qx = a[i] + (x if rel else 0)
                    qy = a[i + 1] + (y if rel else 0)
                    ex = a[i + 2] + (x if rel else 0)
                    ey = a[i + 3] + (y if rel else 0)
                    i += 4
                else:
                    qx, qy = (2 * x - qprev[0], 2 * y - qprev[1]) if qprev \
                        else (x, y)
                    ex = a[i] + (x if rel else 0)
                    ey = a[i + 1] + (y if rel else 0)
                    i += 2
                cur.append(("C", x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y),
                            ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey),
                            ex, ey))
                qprev = (qx, qy)
                x, y = ex, ey
            elif up == "A":
                e = (a[i + 5] + (x if rel else 0), a[i + 6] + (y if rel else 0))
                cur.extend(arc_to_cubics(x, y, a[i], a[i + 1], a[i + 2],
                                         bool(a[i + 3]), bool(a[i + 4]), *e))
                x, y = e; i += 7
            else:
                raise SystemExit(f"unhandled path command {c!r}")
            prev = (cur[-1][-4], cur[-1][-3]) if cur[-1][0] == "C" else None
            if up not in ("Q", "T"):
                qprev = None
            if i >= len(a):
                break
    if cur:
        subs.append(cur)
    return subs


# 4/3 * tan(pi/8): the control-point offset that makes a cubic match a
# quarter circle. Circles are built directly rather than through the arc
# code, because a circle written as two 180-degree arcs hits the one case
# where SVG's large-arc flag is ambiguous - which showed up as a notch in
# `circle` and as mangled dots in ellipsis, grip-vertical and info.
KAPPA = 0.5522847498307936


def circle_ops(cx, cy, r):
    k = KAPPA * r
    return [[
        ("M", cx + r, cy),
        ("C", cx + r, cy + k, cx + k, cy + r, cx, cy + r),
        ("C", cx - k, cy + r, cx - r, cy + k, cx - r, cy),
        ("C", cx - r, cy - k, cx - k, cy - r, cx, cy - r),
        ("C", cx + k, cy - r, cx + r, cy - k, cx + r, cy),
        ("Z",),
    ]]


def rect_ops(x, y, w, h, rx=0.0):
    if not rx:
        return [[("M", x, y), ("L", x + w, y), ("L", x + w, y + h),
                 ("L", x, y + h), ("Z",)]]
    return path_ops(
        f"M {x + rx} {y} H {x + w - rx} A {rx} {rx} 0 0 1 {x + w} {y + rx} "
        f"V {y + h - rx} A {rx} {rx} 0 0 1 {x + w - rx} {y + h} "
        f"H {x + rx} A {rx} {rx} 0 0 1 {x} {y + h - rx} V {y + rx} "
        f"A {rx} {rx} 0 0 1 {x + rx} {y} Z")


def convert(node):
    out = []
    for tag, at in node:
        f = lambda k, d=0.0, at=at: float(at.get(k, d))
        if tag == "path":
            out.extend(path_ops(at["d"]))
        elif tag == "circle":
            out.extend(circle_ops(f("cx"), f("cy"), f("r")))
        elif tag == "line":
            out.append([("M", f("x1"), f("y1")), ("L", f("x2"), f("y2"))])
        elif tag == "rect":
            out.extend(rect_ops(f("x"), f("y"), f("width"), f("height"),
                                f("rx")))
        elif tag in ("polyline", "polygon"):
            pts = [float(n) for n in NUM.findall(at["points"])]
            ops = [("M", pts[0], pts[1])]
            ops += [("L", pts[i], pts[i + 1]) for i in range(2, len(pts), 2)]
            if tag == "polygon":
                ops.append(("Z",))
            out.append(ops)
        else:
            raise SystemExit(f"unhandled element {tag!r}")
    return out


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lucide.json")
    data = json.loads(src.read_text())
    icons = {}
    for name, d in sorted(data.items()):
        if d.get("size", 24) != 24:
            raise SystemExit(f"{name}: unexpected viewBox {d['size']}")
        icons[name] = convert(d["node"])

    body = ['"""Lucide icon geometry, as draw-list paths. GENERATED — do not edit.\n\nBuilt by tools/dkit/build_icons.py from lucide-react\'s own node data;\nsee that file for how arcs and primitives are resolved. Lucide is ISC\nlicensed — fonts/ carries the notice.\n\nCoordinates are in Lucide\'s 24x24 box. draw.icon() scales them.\n"""\n\nBOX = 24.0\nSTROKE = 2.0          # Lucide\'s stroke-width, in BOX units\n\nICONS = {']
    for name, subs in icons.items():
        body.append(f"    {name.replace('-', '_')!r}: [")
        for sub in subs:
            parts = ", ".join(
                "(" + ", ".join([repr(o[0])] + [f"{v:.4g}" for v in o[1:]]) + ")"
                for o in sub)
            body.append(f"        [{parts}],")
        body.append("    ],")
    body.append("}\n")
    dest = HERE.parents[1] / "hyperspace" / "dkit" / "icons.py"   # the package's
    dest.write_text("\n".join(body))
    nops = sum(len(s) for subs in icons.values() for s in subs)
    print(f"wrote {dest.name}: {len(icons)} icons, "
          f"{sum(len(v) for v in icons.values())} subpaths, {nops} ops, "
          f"{dest.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
