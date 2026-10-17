"""4D polytope construction — port of the geometry section of hyperspace.html.

Vertex order is load-bearing: the golden traces index vertices by
construction order, so every builder walks in exactly the order the JS
did (JS Map insertion order == Python dict insertion order).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

PHI = (1 + math.sqrt(5)) / 2
IP1 = 1 / PHI
IP2 = 1 / (PHI * PHI)
PH2 = PHI * PHI
R5 = math.sqrt(5)


def _round6(x: float) -> float:
    # JS Math.round rounds half toward +inf; Python round() banker's-rounds.
    return math.floor(x * 1e6 + 0.5) / 1e6 + 0.0


def kkey(v) -> tuple:
    return tuple(_round6(x) for x in v)


def _perms() -> list[tuple[list[int], bool]]:
    out: list[list[int]] = []

    def walk(cur, rest):
        if not rest:
            out.append(cur[:])
            return
        for i in range(len(rest)):
            walk(cur + [rest[i]], rest[:i] + rest[i + 1 :])

    walk([], [0, 1, 2, 3])
    result = []
    for p in out:
        inv = sum(1 for i in range(4) for j in range(i + 1, 4) if p[i] > p[j])
        result.append((p, inv % 2 == 0))
    return result


PERMS = _perms()


def expand(base, mode: str, into: dict | None = None) -> dict:
    m = into if into is not None else {}
    for p, even in PERMS:
        if mode == "even" and not even:
            continue
        v = [base[p[0]], base[p[1]], base[p[2]], base[p[3]]]
        for s in range(16):
            w = [
                -v[0] if s & 1 else v[0],
                -v[1] if s & 2 else v[1],
                -v[2] if s & 4 else v[2],
                -v[3] if s & 8 else v[3],
            ]
            m[kkey(w)] = w
    return m


def d2(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def edges_by_min_dist(V, tol: float = 1e-4) -> list[list[int]]:
    mn = math.inf
    for i in range(len(V)):
        for j in range(i + 1, len(V)):
            d = d2(V[i], V[j])
            mn = min(mn, d)
    lim = mn * (1 + tol) + 1e-9
    return [
        [i, j]
        for i in range(len(V))
        for j in range(i + 1, len(V))
        if d2(V[i], V[j]) <= lim
    ]


def auto(V) -> dict:
    return {"V": V, "E": edges_by_min_dist(V)}


def cyc3(a: float, b: float, c: float) -> list[list[float]]:
    m: dict = {}
    for t in ([a, b, c], [b, c, a], [c, a, b]):
        for s in range(8):
            v = [-t[0] if s & 1 else t[0], -t[1] if s & 2 else t[1], -t[2] if s & 4 else t[2]]
            m[kkey(v)] = v
    return list(m.values())


def icosa3() -> list[list[float]]:
    return cyc3(0, 1, PHI)


def dodeca3() -> list[list[float]]:
    m: dict = {}
    for s in range(8):
        v = [-1 if s & 1 else 1, -1 if s & 2 else 1, -1 if s & 4 else 1]
        m[kkey(v)] = v
    for v in cyc3(0, IP1, PHI):
        m[kkey(v)] = v
    return list(m.values())


def prism(V3) -> dict:
    E3 = edges_by_min_dist(V3)
    min_l = min(math.sqrt(d2(V3[a], V3[b])) for a, b in E3)
    h, n = min_l / 2, len(V3)
    V = [[v[0], v[1], v[2], h] for v in V3] + [[v[0], v[1], v[2], -h] for v in V3]
    E: list[list[int]] = []
    for a, b in E3:
        E.append([a, b])
        E.append([a + n, b + n])
    for i in range(n):
        E.append([i, i + n])
    return {"V": V, "E": E}


def duoprism(n: int, m: int, equal_radii: bool = False) -> dict:
    r1 = 1.0 if equal_radii else 1 / (2 * math.sin(math.pi / n))
    r2 = 1.0 if equal_radii else 1 / (2 * math.sin(math.pi / m))
    V, E = [], []
    idx = lambda i, j: i * m + j
    for i in range(n):
        a = 2 * math.pi * i / n
        for j in range(m):
            b = 2 * math.pi * j / m
            V.append([r1 * math.cos(a), r1 * math.sin(a), r2 * math.cos(b), r2 * math.sin(b)])
    for i in range(n):
        for j in range(m):
            E.append([idx(i, j), idx((i + 1) % n, j)])
            E.append([idx(i, j), idx(i, (j + 1) % m)])
    return {"V": V, "E": E}


def simplex5() -> list[list[float]]:
    return [
        [1, 1, 1, -1 / R5],
        [1, -1, -1, -1 / R5],
        [-1, 1, -1, -1 / R5],
        [-1, -1, 1, -1 / R5],
        [0, 0, 0, 4 / R5],
    ]


# ---------------------------------------------------------------- builders

def _build_5cell() -> dict:
    V = simplex5()
    E = [[i, j] for i in range(5) for j in range(i + 1, 5)]
    return {"V": V, "E": E}


def _build_cubic_pyramid() -> dict:
    V, E = [], []
    for s in range(8):
        V.append([1 if s & 1 else -1, 1 if s & 2 else -1, 1 if s & 4 else -1, -0.25])
    V.append([0, 0, 0, 0.75])
    for i in range(8):
        for b in range(3):
            j = i ^ (1 << b)
            if j > i:
                E.append([i, j])
        E.append([i, 8])
    return {"V": V, "E": E}


def _build_tesseract() -> dict:
    V, E = [], []
    for s in range(16):
        V.append([
            1 if s & 1 else -1, 1 if s & 2 else -1,
            1 if s & 4 else -1, 1 if s & 8 else -1,
        ])
    for i in range(16):
        for b in range(4):
            j = i ^ (1 << b)
            if j > i:
                E.append([i, j])
    return {"V": V, "E": E}


def _build_rectified_5cell() -> dict:
    s5 = simplex5()
    V = [
        [(s5[i][k] + s5[j][k]) / 2 for k in range(4)]
        for i in range(5)
        for j in range(i + 1, 5)
    ]
    return auto(V)


def _build_16cell() -> dict:
    V = []
    for a in range(4):
        for s in (1, -1):
            v = [0, 0, 0, 0]
            v[a] = s
            V.append(v)
    E = []
    for i in range(8):
        for j in range(i + 1, 8):
            d = d2(V[i], V[j])
            if 1e-6 < d < 3.9:
                E.append([i, j])
    return {"V": V, "E": E}


def _build_24cell() -> dict:
    return auto(list(expand([1, 1, 0, 0], "all").values()))


def _build_trunc_tesseract() -> dict:
    a = 1 + math.sqrt(2)
    return auto(list(expand([1, a, a, a], "all").values()))


def _build_120cell() -> dict:
    m: dict = {}
    expand([0, 0, 2, 2], "all", m)
    expand([1, 1, 1, R5], "all", m)
    expand([IP2, PHI, PHI, PHI], "all", m)
    expand([IP1, IP1, IP1, PH2], "all", m)
    expand([0, IP2, 1, PH2], "even", m)
    expand([0, IP1, PHI, R5], "even", m)
    expand([IP1, 1, PHI, 2], "even", m)
    return auto(list(m.values()))


def _build_600cell() -> dict:
    m: dict = {}
    expand([2, 0, 0, 0], "all", m)
    expand([1, 1, 1, 1], "all", m)
    expand([PHI, 1, IP1, 0], "even", m)
    return auto(list(m.values()))


# ------------------------------------------ 3D shapes from trig equations
#
# Recognizable 3D shapes built from polar curves r(θ), parametric curves
# (x(t), y(t)), spherical functions r(θ, φ), and (u, v) surface patches.
# Built without a lift, they live in the w = 0 hyperplane of the same 4D
# pipeline, and a quarter turn of a W plane (XW/YW/ZW) flattens them: the
# turn carries a whole axis into w, which the 4D→3D divide drops. Two ways
# out, chosen per shape by Shape.w (plan 22): every builder takes an
# optional lift `w` of its own parameters — w(u, v) for a surface patch —
# which gives the surface real 4D extent and keeps its faces; or the shape
# stays 3D and its W planes are masked (view_angles).
#
# Curved surfaces have no planar edge cycles for the polytope face
# extraction to find, so these builders return an extra "F" key — explicit
# face cycles — which faces() honours ahead of extraction, and
# face_triangles() ear-clips when a cap polygon is nonconvex.


def _mesh3(grid, wrap_u: bool, wrap_v: bool) -> tuple[dict, list[list[int]]]:
    """Index an (nu, nv) grid of points into V/E/F, merging coincident
    points (kkey) so poles, seams, and r = 0 pinches become shared
    vertices. A point is (x, y, z), placed at w = 0, or (x, y, z, w) from
    a lifted builder; merging compares every coordinate given, so a lift
    that disagrees across a seam or a pole leaves it open. Quads that
    collapse below 3 distinct vertices are dropped, as is any cycle that
    revisits a vertex non-consecutively (face UVs need each cycle to be a
    simple polygon). Returns the geometry dict and the deduplicated index
    grid."""
    nu, nv = len(grid), len(grid[0])
    vid: dict = {}
    V: list[list[float]] = []
    idx: list[list[int]] = []
    for row in grid:
        r = []
        for p in row:
            k = kkey(p)
            if k not in vid:
                vid[k] = len(V)
                V.append([p[0], p[1], p[2], p[3] if len(p) > 3 else 0.0])
            r.append(vid[k])
        idx.append(r)

    seen: set = set()
    E: list[list[int]] = []

    def edge(a: int, b: int) -> None:
        if a != b and (a, b) not in seen:
            seen.add((a, b))
            seen.add((b, a))
            E.append([a, b])

    for i in range(nu if wrap_u else nu - 1):
        for j in range(nv):
            edge(idx[i][j], idx[(i + 1) % nu][j])
    for i in range(nu):
        for j in range(nv if wrap_v else nv - 1):
            edge(idx[i][j], idx[i][(j + 1) % nv])

    F: list[list[int]] = []
    for i in range(nu if wrap_u else nu - 1):
        for j in range(nv if wrap_v else nv - 1):
            quad = [
                idx[i][j],
                idx[(i + 1) % nu][j],
                idx[(i + 1) % nu][(j + 1) % nv],
                idx[i][(j + 1) % nv],
            ]
            cyc = [v for k, v in enumerate(quad) if v != quad[k - 1]]
            if len(cyc) >= 3 and len(set(cyc)) == len(cyc):
                F.append(cyc)
    return {"V": V, "E": E, "F": F}, idx


def param_surface(
    fn, nu: int, nv: int,
    u1: float = 2 * math.pi, v1: float = 2 * math.pi,
    wrap_u: bool = True, wrap_v: bool = True, w=None,
) -> dict:
    """Sample fn(u, v) -> (x, y, z) on an nu×nv grid. A wrapped axis is
    sampled half-open (the seam closes by index); an unwrapped axis
    includes its endpoint — coincident endpoints merge by kkey, which is
    how the Möbius half-twist seam finds its flipped partner column.

    The lift w(u, v), when given, is each point's fourth coordinate (fn
    may instead return all four itself). Seams and poles that weld by
    coincidence weld only where it agrees: the Möbius strip needs
    w(u1, 1 − v) == w(0, v), a pole needs w constant along it."""
    du = u1 / (nu if wrap_u else nu - 1)
    dv = v1 / (nv if wrap_v else nv - 1)
    if w is None:
        grid = [[fn(i * du, j * dv) for j in range(nv)] for i in range(nu)]
    else:
        grid = [[(*fn(i * du, j * dv), w(i * du, j * dv)) for j in range(nv)]
                for i in range(nu)]
    return _mesh3(grid, wrap_u, wrap_v)[0]


def spherical_surface(r_fn, n_theta: int = 32, n_phi: int = 17, w=None) -> dict:
    """Surface r(θ, φ) in spherical coordinates: azimuth θ ∈ [0, 2π),
    polar φ ∈ [0, π] measured from the +y pole (y is up on screen). The
    lift is w(θ, φ); the poles stay single vertices only where it does
    not depend on θ there."""

    def fn(th: float, ph: float):
        r = r_fn(th, ph)
        return (
            r * math.sin(ph) * math.cos(th),
            r * math.cos(ph),
            r * math.sin(ph) * math.sin(th),
        )

    return param_surface(fn, n_theta, n_phi, v1=math.pi, wrap_u=True, wrap_v=False, w=w)


def ring_prism(pts, depth: float, caps: bool = True, w=None,
               t1: float = 2 * math.pi) -> dict:
    """Extrude a closed 2D outline into a slab of the given thickness.
    Sides are quads; each cap, when the deduplicated outline is a simple
    polygon, is one big face (self-intersecting outlines like the rose
    just skip caps).

    The lift is w(t, z): t = t1·k/n is outline point k's parameter (the
    curve's own t when curve_prism calls), z = ±depth/2 the cap it is on.
    A cap stays one face, flat only if w is affine over it."""
    h = depth / 2
    if w is None:
        grid = [[(x, y, h), (x, y, -h)] for x, y in pts]
    else:
        n = len(pts)
        grid = [[(x, y, h, w(t1 * k / n, h)), (x, y, -h, w(t1 * k / n, -h))]
                for k, (x, y) in enumerate(pts)]
    g, idx = _mesh3(grid, wrap_u=True, wrap_v=False)
    if caps:
        for col in (0, 1):
            ring = [r[col] for r in idx]
            cyc = [v for k, v in enumerate(ring) if v != ring[k - 1]]
            if len(cyc) >= 3 and len(set(cyc)) == len(cyc):
                g["F"].append(cyc if col == 0 else cyc[::-1])
    return g


def curve_prism(xy_fn, n: int = 64, depth: float = 0.35,
                t1: float = 2 * math.pi, caps: bool = True, w=None) -> dict:
    """Extrude the closed parametric plane curve (x(t), y(t)), t ∈ [0, t1).
    The lift is w(t, z), as ring_prism's."""
    return ring_prism([xy_fn(t1 * k / n) for k in range(n)], depth, caps, w=w, t1=t1)


def polar_prism(r_fn, n: int = 96, depth: float = 0.3, caps: bool = True, w=None) -> dict:
    """Extrude the closed polar curve r(θ), θ ∈ [0, 2π). Negative r
    reflects through the origin, as polar plotting conventions do. The
    lift is w(θ, z)."""
    return curve_prism(
        lambda t: (r_fn(t) * math.cos(t), r_fn(t) * math.sin(t)), n, depth, caps=caps, w=w
    )


def tube(curve_fn, n: int = 72, m: int = 8, radius: float = 0.32, w=None) -> dict:
    """Circular tube around a closed 3D curve, with parallel-transport
    frames; the loop's accumulated holonomy is unwound linearly along t so
    the seam ring meets itself without shear. The lift is w(t, a): t along
    the curve, a = 2π·j/m the grid's angle round the tube (before the
    holonomy unwind), so a w periodic in both closes both seams."""
    C = [np.asarray(curve_fn(2 * math.pi * i / n), dtype=np.float64) for i in range(n)]
    T = []
    for i in range(n):
        t = C[(i + 1) % n] - C[i - 1]
        T.append(t / np.linalg.norm(t))
    a0 = np.array([0.0, 0.0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    N = [a0 - (a0 @ T[0]) * T[0]]
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, n):
        v = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
        N.append(v / np.linalg.norm(v))
    v = N[-1] - (N[-1] @ T[0]) * T[0]
    v /= np.linalg.norm(v)
    holonomy = math.atan2(float(v @ np.cross(T[0], N[0])), float(v @ N[0]))
    grid = []
    for i in range(n):
        B = np.cross(T[i], N[i])
        off = -holonomy * i / n
        row = []
        for j in range(m):
            aj = 2 * math.pi * j / m + off
            p = C[i] + radius * (math.cos(aj) * N[i] + math.sin(aj) * B)
            if w is None:
                row.append((float(p[0]), float(p[1]), float(p[2])))
            else:
                row.append((float(p[0]), float(p[1]), float(p[2]),
                            w(2 * math.pi * i / n, 2 * math.pi * j / m)))
        grid.append(row)
    return _mesh3(grid, wrap_u=True, wrap_v=True)[0]


def _heart_xy(t: float) -> tuple[float, float]:
    """The classic parametric heart curve."""
    return (
        16 * math.sin(t) ** 3,
        13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t),
    )


# The lifts (plan 22). Each w is chosen so the shape keeps its volume
# through a full turn of every W plane (VOLUME_FLOOR, tests/test_shapes4d)
# and reads as a solid, never a sheet. The rules that choose it:
#   - w carries no linear part of x, y or z. A w that does (w = a·x, say)
#     only tilts the shape into another flat 3-space, which some W turn
#     still flattens.
#   - w is odd under each mirror of the shape that flips one axis. At a
#     quarter turn of a W plane, w takes that axis's place; if w were the
#     same on both sides of the mirror, the two halves would land on each
#     other and the surface would fold into a sheet.
#   - an extruded outline's w depends on z. Otherwise the walls, whose
#     extrusion runs along z alone, go edge-on together when ZW turns z
#     away.
#   - w agrees wherever the surface welds: poles, the rose's pinch, the
#     Möbius seam (w(2π, 1 − v) == w(0, v)).
# A lift cannot make a shape fatter than its own 3D proportions — at rest
# the divide drops w — so the rose is a little deeper (0.12 → 0.16) and
# the Möbius band a little wider (0.45 → 0.55) than they were at w = 0.
# The heart stays 3D, its W planes masked: under a lift its long walls
# read as a twisted ribbon (plan 22 A2, the turntable sheets).

def _build_heart() -> dict:
    return curve_prism(_heart_xy, n=64, depth=8.0)


def _build_star() -> dict:
    # {5/2} pentagram outline: 10 polar vertices alternating outer radius 1
    # and the pentagram's inner-vertex radius cos(2π/5)/cos(π/5) ≈ 0.382.
    # Lift: the two caps tip opposite ways in w, by sin t round the outline
    ri = math.cos(2 * math.pi / 5) / math.cos(math.pi / 5)
    pts = []
    for k in range(10):
        th = math.pi / 2 + k * math.pi / 5
        r = 1.0 if k % 2 == 0 else ri
        pts.append((r * math.cos(th), r * math.sin(th)))
    h = 0.35 / 2
    return ring_prism(pts, depth=0.35, w=lambda t, z: 0.6 * (z / h) * math.sin(t))


def _build_rose() -> dict:
    # each petal's wall twists through w, front against back; sin 4θ and
    # sin 8θ vanish where the petals meet, so the pinch stays one point
    return polar_prism(
        lambda th: math.cos(2 * th), n=96, depth=0.16, caps=False,
        w=lambda th, z: z * (3 * math.sin(4 * th) + math.sin(8 * th)),
    )


def _build_torus3() -> dict:
    R, r = 1.0, 0.45

    def fn(u: float, v: float):
        return (
            (R + r * math.cos(v)) * math.cos(u),
            r * math.sin(v),
            (R + r * math.cos(v)) * math.sin(u),
        )

    # the tube's upper and lower halves swing opposite ways in w, twice
    # round the ring
    return param_surface(fn, 32, 16, w=lambda u, v: 0.7 * math.sin(v) * math.sin(2 * u))


def _build_trefoil() -> dict:
    def c(t: float):
        return (
            (2 + math.cos(3 * t)) * math.cos(2 * t),
            (2 + math.cos(3 * t)) * math.sin(2 * t),
            1.5 * math.sin(3 * t),
        )

    # the knot's outer lobes go one way in w, its inner crossings the other
    return tube(c, n=72, m=8, radius=0.55, w=lambda t, a: 1.5 * math.cos(3 * t))


def _build_starfruit() -> dict:
    # the four quarters between the poles alternate in w; 0 at the poles
    return spherical_surface(
        lambda th, ph: 1.0 + 0.5 * math.cos(5 * th) * math.sin(ph) ** 5, 40, 15,
        w=lambda th, ph: 0.6 * math.sin(2 * ph) * math.sin(2 * th),
    )


def _build_mobius() -> dict:
    def fn(u: float, v: float):
        h = v - 0.5
        rr = 1 + 0.55 * h * math.cos(u / 2)
        return (rr * math.cos(u), 0.55 * h * math.sin(u / 2), rr * math.sin(u))

    # the band saddles through w twice round; 0 at the seam, which welds
    return param_surface(fn, 65, 5, v1=1.0, wrap_u=False, wrap_v=False,
                         w=lambda u, v: 0.5 * math.sin(2 * u))


def _klein_xyz(u: float, v: float) -> tuple[float, float, float]:
    """The classic 'bottle' immersion of the Klein bottle in 3D, u ∈ [0, π]:
    the body swells up from the base (fattest at u = π/4), the neck curls
    over and comes back down through the body's side (thinnest at 3π/4)
    to meet the base again. Where the neck passes through, the surface
    crosses itself — unavoidable in 3D."""
    cu, su, cv, sv = math.cos(u), math.sin(u), math.cos(v), math.sin(v)
    x = -(2 / 15) * cu * (3 * cv - 30 * su + 90 * cu**4 * su - 60 * cu**6 * su
                          + 5 * cu * cv * su)
    y = -(1 / 15) * su * (3 * cv - 3 * cu**2 * cv - 48 * cu**4 * cv + 48 * cu**6 * cv
                          - 60 * su + 5 * cu * cv * su - 5 * cu**3 * cv * su
                          - 80 * cu**5 * cv * su + 80 * cu**7 * cv * su)
    z = (2 / 15) * (3 + 5 * cu * su) * sv
    return x, y, z


def _build_klein() -> dict:
    # Lifted into w, it no longer crosses itself: where the neck passes
    # through the body (u ≈ 0.49 against u ≈ 2.56), sin 2u puts the two
    # sheets at least 1.56 apart in w. The sin v · cos 2u term is odd in v,
    # so the z-mirror cannot fold the surface at a quarter turn of ZW
    # (the rules above the heart). The seam: u = π meets u = 0 with v
    # flipped to π − v (nv even puts the flip on the grid), where both
    # terms agree, so it welds by kkey like the Möbius strip's —
    # 37 × 16 samples, 36 × 16 vertices. Centred on its bounding box.
    nu, nv = 37, 16
    pts = [_klein_xyz(math.pi * i / (nu - 1), 2 * math.pi * j / nv)
           for i in range(nu) for j in range(nv)]
    cx = (max(p[0] for p in pts) + min(p[0] for p in pts)) / 2
    cy = (max(p[1] for p in pts) + min(p[1] for p in pts)) / 2

    def fn(u: float, v: float):
        x, y, z = _klein_xyz(u, v)
        return (x - cx, y - cy, z)

    return param_surface(
        fn, nu, nv, u1=math.pi, wrap_u=False, wrap_v=True,
        w=lambda u, v: math.sin(2 * u) + 0.5 * math.sin(v) * math.cos(2 * u),
    )


# ----------------------------------------- the catalog: closed 3D solids
#
# Art-direction spike (plan 28): the closed solids of 3D — the five
# Platonic solids, Archimedean and Catalan solids, two Kepler–Poinsot
# stars, the classic compounds, spiked stars — and a few mathematical toys
# (the Hopf fibration, an armillary sphere, a geodesic sphere, the
# Sierpinski tetrahedron). Every 3D one is `mask`: it stays a rigid 3D
# body and its W planes turn it in 3D planes. A solid's faces come from
# the polytope extraction (its faces are planar, convex polygons); a star
# or a compound, whose faces cross, brings its own "F".

# dodeca3's five-fold axes (its face normals): the corners of its dual
# icosahedron, which is not icosa3 — that one is turned a quarter turn
DODECA_AXES = cyc3(0, PHI, 1)


def perm3(base, mode: str = "all") -> list[list[float]]:
    """Every permutation of a 3-tuple ("all"), only the even ones
    ("even" — the cyclic shifts), with every sign change; deduplicated."""
    ps = [(0, 1, 2), (1, 2, 0), (2, 0, 1)]
    if mode == "all":
        ps += [(0, 2, 1), (2, 1, 0), (1, 0, 2)]
    m: dict = {}
    for p in ps:
        for s in range(8):
            v = [-base[p[k]] if s >> k & 1 else base[p[k]] for k in range(3)]
            m[kkey(v)] = [x + 0.0 for x in v]
    return list(m.values())


def _w0(V3) -> list[list[float]]:
    return [[float(v[0]), float(v[1]), float(v[2]), 0.0] for v in V3]


def solid(V3) -> dict:
    """A convex solid from its vertices: edges by the shortest distance
    (every Platonic and Archimedean solid has one edge length), faces by
    extraction when it is drawn."""
    return auto(_w0(V3))


def _boundary_faces(g: dict) -> list[list[int]]:
    """faces() for a geometry dict that is not in SHAPES (a core to stellate,
    a compound's part): planar cycles that pass the support test."""
    h = {"V": np.asarray(g["V"], dtype=np.float64),
         "E": np.asarray(g["E"], dtype=np.int32), "n": len(g["V"])}
    return [c for c in _planar_cycles(h) if _is_boundary_face(h["V"], c)]


def _merge(parts) -> dict:
    """One geometry from several, coincident vertices welded (kkey): each
    part keeps its own edges and faces ("F", extracted when it has none),
    re-indexed onto the merged vertices."""
    vid: dict = {}
    V: list[list[float]] = []
    E: list[list[int]] = []
    F: list[list[int]] = []
    seen: set = set()
    for g in parts:
        F_g = g["F"] if "F" in g else _boundary_faces(g)
        ix = []
        for v in g["V"]:
            k = kkey(v)
            if k not in vid:
                vid[k] = len(V)
                V.append([float(x) for x in v])
            ix.append(vid[k])
        for a, b in g["E"]:
            e = frozenset((ix[a], ix[b]))
            if len(e) == 2 and e not in seen:
                seen.add(e)
                E.append([ix[a], ix[b]])
        F.extend([ix[v] for v in c] for c in F_g)
    return {"V": V, "E": E, "F": F}


def _rot3(axis, ang: float) -> np.ndarray:
    a = np.asarray(axis, dtype=np.float64)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def _turned(g: dict, R: np.ndarray) -> dict:
    V = [list(R @ np.asarray(v[:3], dtype=np.float64)) + [0.0] for v in g["V"]]
    return {**g, "V": V}


def _scaled(g: dict, s: float) -> dict:
    return {**g, "V": [[x * s for x in v] for v in g["V"]]}


# the five Platonic solids, at the coordinates their duals and compounds share
def _tetra3(parity: int = 0) -> list[list[float]]:
    return [[(-1) ** (s & 1), (-1) ** (s >> 1 & 1), (-1) ** (s >> 2 & 1)]
            for s in range(8) if s.bit_count() % 2 == parity]


def _build_tetra() -> dict:
    return solid(_tetra3())


def _build_cube() -> dict:
    return solid(perm3([1, 1, 1]))


def _build_octa() -> dict:
    return solid(perm3([1, 0, 0]))


def _build_dodeca() -> dict:
    return solid(dodeca3())


def _build_icosa() -> dict:
    return solid(icosa3())


# Archimedean and Catalan solids (coordinates: the standard Cartesian forms)
def _build_cuboct() -> dict:
    return solid(perm3([1, 1, 0]))


def _build_trunc_oct() -> dict:
    return solid(perm3([0, 1, 2]))


def _build_rhombicuboct() -> dict:
    return solid(perm3([1, 1, 1 + math.sqrt(2)]))


def _build_icosidodeca() -> dict:
    return solid(perm3([0, 0, PHI], "even") + perm3([0.5, PHI / 2, PH2 / 2], "even"))


def _build_trunc_icosa() -> dict:
    return solid(perm3([0, 1, 3 * PHI], "even") + perm3([1, 2 + PHI, 2 * PHI], "even")
                 + perm3([PHI, 2, PHI ** 3], "even"))


def _build_snub_cube() -> dict:
    # even permutations with an even number of minus signs, odd ones with
    # an odd number: one hand of the chiral snub (t the tribonacci constant)
    t = (1 + (19 + 3 * math.sqrt(33)) ** (1 / 3) + (19 - 3 * math.sqrt(33)) ** (1 / 3)) / 3
    base = [1, 1 / t, t]
    V = []
    for p, even in [((0, 1, 2), 1), ((1, 2, 0), 1), ((2, 0, 1), 1),
                    ((0, 2, 1), 0), ((2, 1, 0), 0), ((1, 0, 2), 0)]:
        for s in range(8):
            if s.bit_count() % 2 == (0 if even else 1):
                V.append([-base[p[k]] if s >> k & 1 else base[p[k]] for k in range(3)])
    return solid(V)


def _build_rhombic_dodeca() -> dict:
    # the cube's corners and the octahedron's, edges only between the two
    return solid(perm3([1, 1, 1]) + perm3([2, 0, 0]))


def _build_rhombic_triaconta() -> dict:
    # the hull of the dodecahedron–icosahedron compound: each crossing pair
    # of edges spans one golden rhombus, so the edges run only between the
    # dodecahedron's 20 corners and the icosahedron's 12
    return solid(dodeca3() + [v[:3] for v in _dual_icosa()["V"]])


# the Kepler–Poinsot stars, drawn as what is seen: every face is a {5/2}
# pentagram, and what shows of it is its five tips (the inner pentagon is
# buried inside the star). A tip at outer corner P_k ends at two corners of
# the inner pentagon, c − (P_j − c)/φ² for j = k + 2 and k + 3.
def _pentagram_tips(V3: list, rings: list[list[int]]) -> dict:
    vid: dict = {}
    V: list[list[float]] = []

    def at(p) -> int:
        k = kkey(p)
        if k not in vid:
            vid[k] = len(V)
            V.append([float(x) for x in p])
        return vid[k]

    F: list[list[int]] = []
    for ring in rings:
        P = np.asarray([V3[r] for r in ring], dtype=np.float64)
        c = P.mean(axis=0)
        inner = [c - (P[j] - c) / PH2 for j in range(5)]
        for k in range(5):
            F.append([at(P[k]), at(inner[(k + 3) % 5]), at(inner[(k + 2) % 5])])
    seen: set = set()
    E: list[list[int]] = []
    for f in F:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            if frozenset((a, b)) not in seen:
                seen.add(frozenset((a, b)))
                E.append([a, b])
    return {"V": _w0(V), "E": E, "F": F}


def _rings_at(V3: list, axes: list) -> list[list[int]]:
    """For each of the 12 five-fold axes, the five corners of V3 one level
    in from the top along it — the second distinct height — in order round
    the axis."""
    V = np.asarray(V3, dtype=np.float64)
    V = V / np.linalg.norm(V, axis=1).max()
    rings = []
    for a in axes:
        n = np.asarray(a, dtype=np.float64)
        n /= np.linalg.norm(n)
        h = V @ n
        level = sorted({round(float(x), 6) for x in h}, reverse=True)[1]
        idx = [i for i in range(len(V)) if abs(h[i] - level) < 1e-5]
        assert len(idx) == 5, (a, level, len(idx))
        u = V[idx[0]] - (V[idx[0]] @ n) * n
        u /= np.linalg.norm(u)
        w = np.cross(n, u)
        idx.sort(key=lambda i: math.atan2(V[i] @ w, V[i] @ u))
        rings.append(idx)
    return rings


def _build_small_stellated() -> dict:
    # {5/2, 5}: the icosahedron's corners; a face is the pentagram on the
    # five neighbours of a corner. Twelve pentagonal spikes on a buried
    # dodecahedron
    V3 = icosa3()
    return _pentagram_tips(V3, _rings_at(V3, V3))


def _build_great_stellated() -> dict:
    # {5/2, 3}: the dodecahedron's corners; a face is the pentagram on the
    # five corners one level in from a face. Twenty triangular spikes on a
    # buried icosahedron
    V3 = dodeca3()
    return _pentagram_tips(V3, _rings_at(V3, DODECA_AXES))


# compounds: several solids sharing one centre, crossing each other
def _five(part: dict) -> dict:
    """Five copies of a part turned by fifths of a turn about a five-fold
    axis: the cube's and the tetrahedron's places inside a dodecahedron."""
    return _merge([_turned(part, _rot3(DODECA_AXES[0], 2 * math.pi * k / 5)) for k in range(5)])


def _build_stella() -> dict:
    return _merge([solid(_tetra3(0)), solid(_tetra3(1))])


def _build_five_tetra() -> dict:
    return _five(solid(_tetra3()))


def _build_five_cubes() -> dict:
    return _five(solid(perm3([1, 1, 1])))


def _build_cube_octa() -> dict:
    # dual compound: the octahedron's edges cross the cube's at their midpoints
    return _merge([solid(perm3([1, 1, 1])), solid(perm3([2, 0, 0]))])


def _dual_icosa() -> dict:
    # the icosahedron dual to dodeca3, scaled so each of its edges crosses
    # a dodecahedron edge at both their midpoints
    d, i = solid(dodeca3()), solid(DODECA_AXES)
    mid = lambda g: float(np.linalg.norm(np.add(g["V"][g["E"][0][0]], g["V"][g["E"][0][1]]) / 2))
    return _scaled(i, mid(d) / mid(i))


def _build_dodeca_icosa() -> dict:
    return _merge([solid(dodeca3()), _dual_icosa()])


# spiked stars: a pyramid on every face of a core, the core buried
def _spiked(core: dict, height: float) -> dict:
    """A pyramid on every face of a convex core, its apex `height` edge
    lengths out along the face's normal. What shows is the spikes' sides."""
    V = np.asarray(core["V"], dtype=np.float64)
    edge = float(np.linalg.norm(V[core["E"][0][0]] - V[core["E"][0][1]]))
    parts = []
    for cyc in _boundary_faces(core):
        P = V[np.asarray(cyc)][:, :3]
        c = P.mean(axis=0)
        n = np.cross(P[1] - P[0], P[2] - P[0])
        n /= np.linalg.norm(n)
        if n @ c < 0:
            n = -n
        apex = c + n * height * edge
        k = len(cyc)
        Vp = _w0(list(P) + [apex])
        parts.append({"V": Vp,
                      "E": [[a, (a + 1) % k] for a in range(k)] + [[a, k] for a in range(k)],
                      "F": [[a, (a + 1) % k, k] for a in range(k)]})
    return _merge(parts)


def _build_moravian() -> dict:
    # the Moravian (Herrnhut) star: 26 points on a rhombicuboctahedron
    return _spiked(_build_rhombicuboct(), 1.6)


def _build_starburst() -> dict:
    return _spiked(_build_icosa(), 2.2)


# mathematical toys
def _circle(n: int, f) -> dict:
    """A closed curve of n segments, f(t) for t ∈ [0, 2π): lines only."""
    return {"V": [list(f(2 * math.pi * k / n)) for k in range(n)],
            "E": [[k, (k + 1) % n] for k in range(n)], "F": [], "curve": True}


def _build_hopf() -> dict:
    # The Hopf fibration: the 3-sphere filled with great circles, any two
    # of them linked once. The fibre over a point of the 2-sphere at
    # latitude 2η, longitude α is (cos η·e^it, sin η·e^i(t+α)); three
    # latitudes of eight fibres each, every ring a nest of Villarceau
    # circles on a torus
    parts = []
    for r, eta in enumerate((0.22 * math.pi, 0.32 * math.pi, 0.42 * math.pi)):
        for k in range(8):
            al = 2 * math.pi * (k + 0.5 * r) / 8
            parts.append(_circle(36, lambda t, e=eta, a=al: (
                math.cos(e) * math.cos(t), math.cos(e) * math.sin(t),
                math.sin(e) * math.cos(t + a), math.sin(e) * math.sin(t + a))))
    return {**_merge(parts), "curve": True}


def _build_armillary() -> dict:
    # the celestial sphere's rings: the equator, the tropics and the polar
    # circles (±23.44°, ±66.56°), the ecliptic and two colures. y is the pole
    tilt = math.radians(23.44)
    rings = []
    for lat in (0.0, tilt, -tilt, math.pi / 2 - tilt, tilt - math.pi / 2):
        rings.append(_circle(48, lambda t, b=lat: (
            math.cos(b) * math.cos(t), math.sin(b), math.cos(b) * math.sin(t))))
    rings.append(_circle(48, lambda t: (
        math.cos(t), math.sin(t) * math.sin(tilt), math.sin(t) * math.cos(tilt))))
    for lon in (0.0, math.pi / 2):
        rings.append(_circle(48, lambda t, l=lon: (
            math.cos(t) * math.cos(l), math.sin(t), math.cos(t) * math.sin(l))))
    return {**_merge([{**r, "V": _w0(r["V"])} for r in rings]), "curve": True}


def _build_geodesic() -> dict:
    # the icosahedron, each face cut into nine (frequency 3), pushed out
    # onto the sphere: Fuller's dome, closed
    ico = solid(icosa3())
    V = np.asarray(ico["V"], dtype=np.float64)[:, :3]
    f = 3
    tris = []
    for a, b, c in _boundary_faces(ico):
        P = lambda i, j, a=a, b=b, c=c: (V[a] * (f - i - j) + V[b] * i + V[c] * j) / f
        for i in range(f):
            for j in range(f - i):
                tris.append([P(i, j), P(i + 1, j), P(i, j + 1)])
                if i + j < f - 1:
                    tris.append([P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)])
    parts = []
    for t in tris:
        t = [p / np.linalg.norm(p) for p in t]
        parts.append({"V": _w0(t), "E": [[0, 1], [1, 2], [2, 0]], "F": [[0, 1, 2]]})
    return _merge(parts)


def _build_sierpinski() -> dict:
    # the Sierpinski tetrahedron, three levels deep: 64 tetrahedra
    def split(T, depth):
        if depth == 0:
            return [T]
        out = []
        for k in range(4):
            out += split([(T[k] + T[j]) / 2 for j in range(4)], depth - 1)
        return out

    T0 = [np.asarray(v, dtype=np.float64) for v in _tetra3()]
    six = [[a, b] for a in range(4) for b in range(a + 1, 4)]
    return _merge([{"V": _w0(T), "E": six, "F": [[1, 2, 3], [0, 3, 2], [0, 1, 3], [0, 2, 1]]}
                   for T in split(T0, 3)])


def _build_lissajous() -> dict:
    # a Lissajous knot: cos(3t + 0.7), cos(2t + 0.2), cos 7t — three
    # coprime frequencies close into a knot
    g = _circle(240, lambda t: (math.cos(3 * t + 0.7), math.cos(2 * t + 0.2), math.cos(7 * t)))
    g["V"] = _w0(g["V"])
    return g


def _build_loxodrome() -> dict:
    # two rhumb lines, pole to pole and back, half a turn apart: each
    # crosses every meridian at the same angle, so it winds ever tighter
    # into the poles
    k, n = 0.35, 120
    pts = [(0.0, -1.0, 0.0)]
    for half in (0, 1):
        for j in range(1, n):
            s = -1 + 2 * j / n if half == 0 else 1 - 2 * j / n
            lat = math.asin(s)
            lon = math.log(math.tan(math.pi / 4 + lat / 2)) / k + math.pi * half
            pts.append((math.cos(lat) * math.cos(lon), s, math.cos(lat) * math.sin(lon)))
        if half == 0:
            pts.append((0.0, 1.0, 0.0))
    m = len(pts)
    return {"V": _w0(pts), "E": [[i, (i + 1) % m] for i in range(m)], "F": [], "curve": True}


# ----------------------------------------------------------- scenes
#
# A scene is several shapes in one frame, sharing its centre: a sphere
# round a hypercube round a star. Each layer is a shape of SHAPES (by
# name) at its own scale, drawn with its own weights and colour, turning
# at its own multiple of the view's angles (spin −1 counter-turns, 0 holds
# still); a layer keeps its shape's own way of filling w, so a masked star
# turns in 3D inside a tesseract turning in 4D. The scene's geometry is
# its layers' in order (geom's "layers" says which rows are whose), and
# its faces are the layers' own faces — a support test over the whole
# compound would reject them.

@dataclass(frozen=True)
class Layer:
    shape: str                    # a SHAPES name
    scale: float = 1.0            # circumradius, against the scene's largest layer
    spin: float = 1.0             # multiple of the view's angles
    lines: float = 1.0            # line alpha; 0 hides them
    width: float = 1.0            # line width
    faces: float = 1.0            # face alpha; 0 draws no faces
    points: float = 1.0           # point alpha and size; 0 hides them
    tint: tuple = (1.0, 1.0, 1.0)  # the lines' colour (the points keep theirs × tint)


GOLD = (1.0, 0.80, 0.38)
ICE = (0.55, 0.78, 1.0)


def _build_scene(layers) -> dict:
    V: list = []
    E: list = []
    F: list = []
    parts = []
    for L in layers:
        j = shape_index(L.shape)
        g = geom(j)
        off, eoff, foff = len(V), len(E), len(F)
        V.extend((g["V"] * L.scale).tolist())
        E.extend((g["E"] + off).tolist())
        if L.faces > 0:
            F.extend([[v + off for v in c] for c in faces(j)])
        parts.append((off, len(V), eoff, len(E), foff, len(F), j, L))
    return {"V": V, "E": E, "F": F, "layers": parts}


# How a shape fills the fourth dimension (Shape.w):
#   native  a 4-polytope or a 4D surface, built with real w-extent
#   flat    a 3D shape at w = 0: a W plane's quarter turn flattens it
#   lift    a 3D surface given w-extent by a lift of its parameters
#   mask    a 3D shape kept 3D: its W planes turn it in 3D (view_angles)
W_KINDS = ("native", "flat", "lift", "mask")


@dataclass(frozen=True)
class Shape:
    name: str
    alias: str
    cells: int
    sym: str
    build: object = field(repr=False)
    w: str = "native"
    family: str = ""              # the catalog's group (plan 28): "", or e.g. "Platonic"
    layers: tuple = ()            # a scene's layers (Layer), empty for one shape

    def __post_init__(self) -> None:
        if self.w not in W_KINDS:
            raise ValueError(f"{self.name}: w must be one of {W_KINDS}, not {self.w!r}")



def _build_orbit() -> dict:
    g = _circle(64, lambda t: (math.cos(t), 0.0, math.sin(t)))
    g["V"] = _w0(g["V"])
    return g


def _kepler_layers() -> tuple:
    # Kepler's model of the six planets' spheres (Mysterium Cosmographicum,
    # 1596): each Platonic solid inscribed in one planet's sphere and
    # circumscribing the next one's. Outside in: Saturn, the cube,
    # Jupiter, the tetrahedron, Mars, the dodecahedron, Earth, the
    # icosahedron, Venus, the octahedron, Mercury. A solid's insphere over
    # its circumsphere sets the next radius; the inner shells turn faster
    nest = [("Cube", 1 / math.sqrt(3)), ("Tetrahedron", 1 / 3),
            ("Dodecahedron", 0.7946544722917661), ("Icosahedron", 0.7946544722917661),
            ("Octahedron", 1 / math.sqrt(3))]
    planets = [(0.95, 0.80, 0.50), (0.95, 0.62, 0.38), (1.0, 0.42, 0.32),
               (0.45, 0.70, 1.0), (1.0, 0.92, 0.62), (0.80, 0.80, 0.84)]
    out = [Layer("Armillary sphere", 1.0, spin=0.12, lines=0.45, width=0.8, faces=0,
                 points=0, tint=planets[0])]
    r = 1.0
    for k, (name, ratio) in enumerate(nest):
        out.append(Layer(name, r, spin=(-1) ** k * (0.35 + 0.25 * k), faces=0.6,
                         points=0.5, width=0.9 + 0.1 * k))
        r *= ratio
        out.append(Layer("Orbit", r, spin=0.3 + 0.3 * k, lines=0.9, faces=0, points=0,
                         tint=planets[k + 1]))
    return tuple(out)


def scene(name: str, alias: str, sym: str, layers: tuple, w: str = "mask") -> Shape:
    """A Shape that is several shapes in one frame (Layer, _build_scene)."""
    return Shape(name, alias, 0, sym, lambda: _build_scene(layers), w=w, family="Scene",
                 layers=layers)

SHAPES = [
    Shape("5-cell", "hypertetrahedron", 5, "{3,3,3}", _build_5cell),
    Shape("3,3-duoprism", "triangle × triangle", 6, "{3}×{3}", lambda: duoprism(3, 3)),
    Shape("Cubic pyramid", "hyperpyramid", 7, "({4,3}) ∨ •", _build_cubic_pyramid),
    Shape("Tesseract", "hypercube · hyperhexahedron", 8, "{4,3,3}", _build_tesseract),
    Shape("Rectified 5-cell", "truncation series", 10, "r{3,3,3}", _build_rectified_5cell),
    Shape("4,8-duoprism", "square × octagon", 12, "{4}×{8}", lambda: duoprism(4, 8)),
    Shape("6,6-duoprism", "hexagon × hexagon", 12, "{6}×{6}", lambda: duoprism(6, 6)),
    Shape("16-cell", "hyperoctahedron", 16, "{3,3,4}", _build_16cell),
    Shape("10,10-duoprism", "decagon × decagon", 20, "{10}×{10}", lambda: duoprism(10, 10)),
    Shape("Icosahedral prism", "hyperprism", 22, "{3,5}×{ }", lambda: prism(icosa3())),
    Shape("24-cell", "no 3D counterpart exists", 24, "{3,4,3}", _build_24cell),
    Shape("Truncated tesseract", "truncation series", 24, "t{4,3,3}", _build_trunc_tesseract),
    Shape("12,12-duoprism", "dodecagon × dodecagon", 24, "{12}×{12}", lambda: duoprism(12, 12)),
    Shape("Dodecahedral prism", "hyperprism", 32, "{5,3}×{ }", lambda: prism(dodeca3())),
    Shape("20,20-duoprism", "icosagon × icosagon", 40, "{20}×{20}", lambda: duoprism(20, 20)),
    Shape("120-cell", "hyperdodecahedron", 120, "{5,3,3}", _build_120cell),
    Shape("600-cell", "hypericosahedron", 600, "{3,3,5}", _build_600cell),
    Shape("Clifford torus", "flat torus on the 3-sphere", 0, "S¹ × S¹", lambda: duoprism(32, 16, True)),
    # -------- 3D shapes from trig equations (appended: index is identity)
    Shape("Heart", "3D · classic heart curve, extruded", 0, "x=16 sin³t", _build_heart, w="mask"),
    Shape("Star", "4D lift · pentagram prism", 0, "{5/2} polar", _build_star, w="lift"),
    Shape("Rose", "4D lift · four-petal rose, extruded", 0, "r=cos 2θ", _build_rose, w="lift"),
    Shape("Torus", "4D lift · the donut", 0, "(R+r cos v)e^iu", _build_torus3, w="lift"),
    Shape("Trefoil knot", "4D lift · tube round a (2,3) torus knot", 0, "sin 3t · e^2it",
          _build_trefoil, w="lift"),
    Shape("Starfruit", "4D lift · spherical star", 0, "r=1+½cos 5θ sin⁵φ",
          _build_starfruit, w="lift"),
    Shape("Möbius strip", "4D lift · one-sided band", 0, "half-twist band",
          _build_mobius, w="lift"),
    Shape("Klein bottle", "4D · one-sided bottle, no self-crossing", 0, "χ=0 · one side",
          _build_klein, w="lift"),
    # -------- plan 28 spike: the catalog of closed 3D solids, all masked
    Shape("Tetrahedron", "Platonic · 4 triangles", 0, "{3,3}", _build_tetra,
          w="mask", family="Platonic"),
    Shape("Cube", "Platonic · 6 squares", 0, "{4,3}", _build_cube, w="mask", family="Platonic"),
    Shape("Octahedron", "Platonic · 8 triangles", 0, "{3,4}", _build_octa,
          w="mask", family="Platonic"),
    Shape("Dodecahedron", "Platonic · 12 pentagons", 0, "{5,3}", _build_dodeca,
          w="mask", family="Platonic"),
    Shape("Icosahedron", "Platonic · 20 triangles", 0, "{3,5}", _build_icosa,
          w="mask", family="Platonic"),
    Shape("Cuboctahedron", "Archimedean · 8 triangles, 6 squares", 0, "r{4,3}", _build_cuboct,
          w="mask", family="Archimedean"),
    Shape("Truncated octahedron", "Archimedean · the space-filler", 0, "t{3,4}",
          _build_trunc_oct, w="mask", family="Archimedean"),
    Shape("Rhombicuboctahedron", "Archimedean · 8 triangles, 18 squares", 0, "rr{4,3}",
          _build_rhombicuboct, w="mask", family="Archimedean"),
    Shape("Snub cube", "Archimedean · chiral, 38 faces", 0, "sr{4,3}", _build_snub_cube,
          w="mask", family="Archimedean"),
    Shape("Icosidodecahedron", "Archimedean · 20 triangles, 12 pentagons", 0, "r{5,3}",
          _build_icosidodeca, w="mask", family="Archimedean"),
    Shape("Truncated icosahedron", "Archimedean · the football, C₆₀", 0, "t{3,5}",
          _build_trunc_icosa, w="mask", family="Archimedean"),
    Shape("Rhombic dodecahedron", "Catalan · 12 rhombi", 0, "V3.4.3.4", _build_rhombic_dodeca,
          w="mask", family="Catalan"),
    Shape("Rhombic triacontahedron", "Catalan · 30 golden rhombi", 0, "V3.5.3.5",
          _build_rhombic_triaconta, w="mask", family="Catalan"),
    Shape("Small stellated dodecahedron", "Kepler–Poinsot · 12 points", 0, "{5/2,5}",
          _build_small_stellated, w="mask", family="Star"),
    Shape("Great stellated dodecahedron", "Kepler–Poinsot · 20 points", 0, "{5/2,3}",
          _build_great_stellated, w="mask", family="Star"),
    Shape("Moravian star", "spiked rhombicuboctahedron · 26 points", 0, "Herrnhut",
          _build_moravian, w="mask", family="Star"),
    Shape("Starburst", "spiked icosahedron · 20 points", 0, "{3,5} + pyramids",
          _build_starburst, w="mask", family="Star"),
    Shape("Stella octangula", "compound · two tetrahedra", 0, "2{3,3}", _build_stella,
          w="mask", family="Compound"),
    Shape("Five tetrahedra", "compound · chiral, in a dodecahedron", 0, "5{3,3}",
          _build_five_tetra, w="mask", family="Compound"),
    Shape("Five cubes", "compound · in a dodecahedron", 0, "5{4,3}", _build_five_cubes,
          w="mask", family="Compound"),
    Shape("Cube + octahedron", "compound · duals, edges crossing", 0, "{4,3}+{3,4}",
          _build_cube_octa, w="mask", family="Compound"),
    Shape("Dodecahedron + icosahedron", "compound · duals, edges crossing", 0, "{5,3}+{3,5}",
          _build_dodeca_icosa, w="mask", family="Compound"),
    Shape("Hopf fibration", "4D · the 3-sphere in linked great circles", 0, "S³ → S²",
          _build_hopf, family="Toy"),
    Shape("Armillary sphere", "celestial rings · tropics, ecliptic, colures", 0, "23.44°",
          _build_armillary, w="mask", family="Toy"),
    Shape("Geodesic sphere", "icosahedron, frequency 3", 0, "{3,5+}₃,₀", _build_geodesic,
          w="mask", family="Toy"),
    Shape("Sierpinski tetrahedron", "fractal · 64 tetrahedra, dimension 2", 0, "level 3",
          _build_sierpinski, w="mask", family="Toy"),
    Shape("Lissajous knot", "curve · frequencies 3, 2, 7", 0, "cos(3t+.7), cos(2t+.2), cos 7t",
          _build_lissajous, w="mask", family="Toy"),
    Shape("Loxodrome", "curve · two rhumb lines, pole to pole", 0, "λ = ln tan(π/4+φ/2)/k",
          _build_loxodrome, w="mask", family="Toy"),
    Shape("Orbit", "curve · one great circle", 0, "S¹", _build_orbit, w="mask", family="Toy"),
    # -------- scenes: several shapes in one frame (Layer), after the shapes
    # they name
    scene("Celestial tesseract", "scene · glome ⊃ tesseract ⊃ star", "S³ ⊃ {4,3,3} ⊃ {5/2,5}", (
        Layer("Hopf fibration", 1.0, spin=0.4, lines=1.0, width=1.0, faces=0, points=0,
              tint=ICE),
        Layer("Tesseract", 1.0, faces=1.4, points=0.6),
        Layer("Small stellated dodecahedron", 0.62, spin=-0.7, width=1.3, faces=2.2,
              points=1.4, tint=GOLD),
    ), w="native"),
    scene("Celestial cube", "scene · armillary ⊃ cube ⊃ star", "23.44° ⊃ {4,3} ⊃ {5/2,3}", (
        Layer("Armillary sphere", 1.0, spin=0.25, lines=0.6, width=0.9, faces=0, points=0,
              tint=ICE),
        Layer("Cube", 1.0, faces=1.5, points=0.5),
        Layer("Great stellated dodecahedron", 0.82, spin=-0.6, width=1.2, faces=2.0,
              points=1.3, tint=GOLD),
    )),
    scene("Mysterium Cosmographicum", "scene · Kepler's nested solids, 1596",
          "♄ {4,3} ♃ {3,3} ♂ {5,3} ♁ {3,5} ♀ {3,4} ☿", _kepler_layers()),
]


_cache: dict[int, dict] = {}


def geom(i: int) -> dict:
    """Built geometry, normalised to unit circumradius, cached.

    Returns {"V": float64 (n,4), "E": int32 (m,2), "n": int, "m": int}.
    """
    if i in _cache:
        return _cache[i]
    g = SHAPES[i].build()
    mx = max(math.hypot(*v) for v in g["V"])
    V = np.asarray(g["V"], dtype=np.float64) / mx
    E = np.asarray(g["E"], dtype=np.int32)
    _cache[i] = {"V": V, "E": E, "n": len(g["V"]), "m": len(g["E"])}
    if "F" in g:  # explicit face cycles from a 3D surface builder
        _cache[i]["F"] = g["F"]
    if g.get("curve"):  # a curve's samples are not corners: no points drawn
        _cache[i]["curve"] = True
    if "layers" in g:  # a scene: whose rows are whose, and how each draws
        _cache[i].update(_scene_style(g["layers"], len(g["V"]), len(g["E"]), len(g["F"])))
    return _cache[i]


def shape_index(name: str) -> int:
    """The SHAPES index of the shape called `name`."""
    for i, s in enumerate(SHAPES):
        if s.name == name:
            return i
    raise KeyError(name)


def _scene_style(parts, n: int, m: int, nf: int) -> dict:
    """A scene's per-row weights: "layers" — (first vertex, end, the
    layer's shape, its spin) per layer — and "style": per edge its alpha,
    width, colour and its own shape's edge count (what the line density
    reads), per vertex its alpha, colour and whether it is tinted, per
    face its alpha."""
    st = {"e_alpha": np.ones(m), "e_width": np.ones(m), "e_rgb": np.ones((m, 3)),
          "e_m": np.ones(m), "p_alpha": np.ones(n), "p_rgb": np.ones((n, 3)),
          "p_tinted": np.zeros(n, bool), "f_alpha": np.ones(nf)}
    layers = []
    for a, b, ea, eb, fa, fb, j, L in parts:
        layers.append((a, b, j, float(L.spin)))
        st["e_alpha"][ea:eb] = L.lines
        st["e_width"][ea:eb] = L.width
        st["e_rgb"][ea:eb] = L.tint
        st["e_m"][ea:eb] = eb - ea
        st["p_alpha"][a:b] = 0.0 if geom(j).get("curve") else L.points
        st["p_rgb"][a:b] = L.tint
        st["p_tinted"][a:b] = tuple(L.tint) != (1.0, 1.0, 1.0)
        st["f_alpha"][fa:fb] = L.faces
    return {"layers": layers, "style": st}


# ------------------------------------------------------------- transforms

# the six rotation planes, in the reference's order: the name the panel,
# the registry (params.PLANES) and the routing table use, and the two
# axes it turns. One table, so the names can never drift from the maths.
PLANES = [("XY", 0, 1), ("XZ", 0, 2), ("YZ", 1, 2), ("XW", 0, 3), ("YW", 1, 3), ("ZW", 2, 3)]
PLANE_NAMES = [name for name, _, _ in PLANES]
RATE = [0.62, 0.47, 0.31, 1.00, 0.79, 0.55]
CAM3 = 3.4


def rotate4(V: np.ndarray, ang) -> np.ndarray:
    """Sequential per-plane rotation, exactly as draw() applies it in-place."""
    v = V.copy()
    for p in range(6):
        _, a, b = PLANES[p]
        c, s = math.cos(ang[p]), math.sin(ang[p])
        va, vb = v[:, a].copy(), v[:, b].copy()
        v[:, a] = va * c - vb * s
        v[:, b] = va * s + vb * c
    return v


# A masked shape (Shape.w == "mask") is 3D and stays 3D: the W planes
# cannot move it. Each W plane's angle turns it in a 3D plane instead, so
# whatever drives that plane — the bass bands by default (bands.BANDS:
# SUB → ZW, BASS → XW, MIDB → YW) — still moves it. w becomes z: XW → XZ
# and YW → YZ squeeze the same axis a W turn would, with depth instead of
# collapse; ZW, with no z left to become, takes the plane left over, XY.
W_REMAP = {3: 1, 4: 2, 5: 0}


def w_masked(i: int, flat: bool = False) -> bool:
    """Whether shape i keeps its W planes masked (Shape.w == "mask"), or
    every shape does: `flat` is the view's 3D switch (ViewState.three_d,
    plan 28), which takes the fourth dimension out of every shape."""
    return flat or SHAPES[i].w == "mask"


def view_angles(i: int, ang, flat: bool = False):
    """The angles shape i is drawn at: `ang` itself, unless the shape's W
    planes are masked — then a new list with each W angle added onto its
    3D plane (W_REMAP) and the W planes at 0. A pure function of the
    view's angles, read where the frame is drawn: the integrator and the
    rot.* params are untouched, so a rate or a phase routed to a W plane
    lands on the 3D plane alike, and every other shape's pose never
    depends on which shapes were shown before it. `flat` masks any shape
    (w_masked)."""
    if not w_masked(i, flat):
        return ang
    out = [float(a) for a in ang]
    for p, q in W_REMAP.items():
        out[q] += out[p]
        out[p] = 0.0
    return out


def project(
    V: np.ndarray, ang, yaw: float, pitch: float,
    d4: float = 2.6, w: int = 1200, h: int = 800,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The full draw() transform: 4D rotate → 4D→3D → view → 3D→2D.

    Returns (px, py, pd) matching the reference renderer at viewport (w, h),
    DPR 1. pd is the post-rotation w-coordinate used for depth cueing. This
    is the parity oracle the golden traces are checked against; it is
    `project_h` — the renderer's path — without the homogeneous divisor, so
    the two can never disagree (tests/test_core.py pins it on every shape).
    """
    px, py, pd, _ = project_h(V, ang, yaw, pitch, d4=d4, w=w, h=h)
    return px, py, pd


# ------------------------------------------------------------------ faces

_face_cache: dict[int, list[list[int]]] = {}


def _planar_cycles(g: dict, plane_tol: float = 1e-5, max_len: int = 64) -> list[list[int]]:
    """Every closed cycle of edges lying in one 2-plane (walk from each edge
    path a→b→c, stepping to the unique in-plane neighbour until closure)."""
    V, E, n = g["V"], g["E"], g["n"]
    adj: list[list[int]] = [[] for _ in range(n)]
    for a, b in E:
        adj[int(a)].append(int(b))
        adj[int(b)].append(int(a))

    found: set[frozenset] = set()
    faces: list[list[int]] = []
    for a in range(n):
        for b in adj[a]:
            for c in adj[b]:
                if c == a:
                    continue
                e1 = V[b] - V[a]
                e1 = e1 / np.linalg.norm(e1)
                w = V[c] - V[b]
                w2 = w - (w @ e1) * e1
                nw = np.linalg.norm(w2)
                if nw < plane_tol:
                    continue  # collinear
                e2 = w2 / nw

                def inplane(p, origin=V[a], e1=e1, e2=e2):
                    d = p - origin
                    r = d - (d @ e1) * e1 - (d @ e2) * e2
                    return np.linalg.norm(r) < plane_tol

                cyc = [a, b, c]
                ok = True
                while True:
                    prev, cur = cyc[-2], cyc[-1]
                    nxt = None
                    for cand in adj[cur]:
                        if cand != prev and inplane(V[cand]):
                            nxt = cand
                            break
                    if nxt is None or len(cyc) > max_len:
                        ok = False
                        break
                    if nxt == a:
                        break
                    if nxt in cyc:
                        ok = False
                        break
                    cyc.append(nxt)
                if ok and len(cyc) >= 3:
                    key = frozenset(cyc)
                    if key not in found:
                        found.add(key)
                        faces.append(cyc)
    return faces


def _is_boundary_face(V: np.ndarray, cyc: list[int], tol: float = 1e-7) -> bool:
    """Support test: a planar cycle is a true 2-face iff all other vertices,
    projected into the plane's 2D orthogonal complement, fit in an open
    half-plane (max angular gap > π). Rejects central cycles — equatorial
    squares of the 16-cell, central hexagons of the 24-cell — which are real
    planar edge cycles the 1-skeleton alone cannot tell from faces."""
    idx = np.asarray(cyc)
    P = V[idx]
    centre = P.mean(axis=0)
    e1 = P[1] - P[0]
    e1 = e1 / np.linalg.norm(e1)
    w = P[2] - P[1]
    w = w - (w @ e1) * e1
    e2 = w / np.linalg.norm(w)
    A = np.stack([e1, e2]).T
    q_basis, _ = np.linalg.qr(
        np.hstack([A, np.random.default_rng(1).standard_normal((4, 2))])
    )
    o1, o2 = q_basis[:, 2], q_basis[:, 3]
    mask = np.ones(len(V), bool)
    mask[idx] = False
    D = V[mask] - centre
    q = np.stack([D @ o1, D @ o2], axis=1)
    r = np.linalg.norm(q, axis=1)
    q = q[r > tol]
    if len(q) == 0:
        return True
    ang = np.sort(np.arctan2(q[:, 1], q[:, 0]))
    gaps = np.diff(np.concatenate([ang, [ang[0] + 2 * np.pi]]))
    return bool(gaps.max() > np.pi + 1e-9)


def faces(i: int) -> list[list[int]]:
    """Boundary 2-faces of shape i as vertex cycles. Cached like geom().
    Explicit "F" cycles from a builder (curved 3D surfaces, where no planar
    edge cycles exist) win over planar-cycle extraction."""
    if i not in _face_cache:
        g = geom(i)
        if "F" in g:
            _face_cache[i] = [list(c) for c in g["F"]]
        else:
            _face_cache[i] = [c for c in _planar_cycles(g) if _is_boundary_face(g["V"], c)]
    return _face_cache[i]


def _face_xy(P: np.ndarray) -> np.ndarray:
    """Project a face cycle onto its own centred 2-plane basis, oriented
    CCW. Best-effort for the slightly non-planar quads of curved grids.

    A larger polygon that is not planar — a lifted shape's cap, whose
    outline the lift has bent through w — is projected onto its
    least-squares plane instead: the basis through its first two corners
    can fold such an outline over itself, and the ear clip and the UVs
    both need it simple. Every planar face keeps the basis it always had."""
    c = P.mean(axis=0)
    e1 = P[0] - c
    e1 = e1 / np.linalg.norm(e1)
    w = P[1] - c
    w = w - (w @ e1) * e1
    e2 = w / np.linalg.norm(w)
    D = P - c
    if len(P) > 4:
        off = D - np.outer(D @ e1, e1) - np.outer(D @ e2, e2)
        if np.abs(off).max() > 1e-6 * np.abs(D).max():
            e1, e2 = np.linalg.svd(D, full_matrices=False)[2][:2]
    xy = np.stack([D @ e1, D @ e2], axis=1)
    area = float(
        np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1])
    )
    if area < 0:
        xy[:, 1] = -xy[:, 1]
    return xy


def _ear_clip(xy: np.ndarray) -> list[tuple[int, int, int]]:
    """Triangulate a simple CCW polygon by ear clipping; positions are
    indices into xy. Falls back to a fan over whatever remains if no ear
    is found (degenerate input)."""

    def cross(o: int, a: int, b: int) -> float:
        return float(
            (xy[a, 0] - xy[o, 0]) * (xy[b, 1] - xy[o, 1])
            - (xy[a, 1] - xy[o, 1]) * (xy[b, 0] - xy[o, 0])
        )

    idx = list(range(len(xy)))
    out: list[tuple[int, int, int]] = []
    while len(idx) > 3:
        n = len(idx)
        for k in range(n):
            o, a, b = idx[k - 1], idx[k], idx[(k + 1) % n]
            if cross(o, a, b) <= 1e-12:
                continue  # reflex or collinear corner — not an ear
            if any(
                q not in (o, a, b)
                and cross(o, a, q) >= -1e-12
                and cross(a, b, q) >= -1e-12
                and cross(b, o, q) >= -1e-12
                for q in idx
            ):
                continue  # another vertex sits inside the candidate ear
            out.append((o, a, b))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        out.append((idx[0], idx[1], idx[2]))
    else:
        out.extend((idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1))
    return out


def _tri_cycle(cyc: list[int], V: np.ndarray) -> list[tuple[int, int, int]]:
    """Triangulate one face cycle. Convex polygons keep the original fan
    from cyc[0] (bit-identical to the old output for every polytope face);
    nonconvex caps — hearts, stars — get ear-clipped."""
    n = len(cyc)
    if n == 3:
        return [(cyc[0], cyc[1], cyc[2])]
    xy = _face_xy(V[np.asarray(cyc)])
    x, y = xy[:, 0], xy[:, 1]
    xr, yr = np.roll(x, -1), np.roll(y, -1)
    turn = (xr - x) * (np.roll(y, -2) - y) - (yr - y) * (np.roll(x, -2) - x)
    if bool((turn > -1e-9).all()):
        return [(cyc[0], cyc[k], cyc[k + 1]) for k in range(1, n - 1)]
    return [(cyc[a], cyc[b], cyc[c]) for a, b, c in _ear_clip(xy)]


_tri_cache: dict[int, np.ndarray] = {}


def face_triangles(i: int) -> np.ndarray:
    """Triangulation of faces(i): int32 (T, 3) vertex indices, plus the
    face index each triangle came from in the fourth column. Cached."""
    if i not in _tri_cache:
        V = geom(i)["V"]
        tris = []
        for fi, cyc in enumerate(faces(i)):
            for a, b, c in _tri_cycle(cyc, V):
                tris.append((a, b, c, fi))
        _tri_cache[i] = np.asarray(tris, dtype=np.int32).reshape(-1, 4)
    return _tri_cache[i]


_uv_cache: dict[int, np.ndarray] = {}


def face_uvs(i: int) -> np.ndarray:
    """Face-local UVs for face_triangles(i): float64 (T*3, 2) in [0,1].

    Each face is a planar regular polygon; projecting its cycle into the
    face's own orthonormal 2-plane basis gives 2D coordinates, normalised so
    the circumradius spans 0.5 about a (0.5, 0.5) centre with CCW winding.
    Congruent faces therefore carry identical UV polygons (up to the cycle's
    n-fold starting rotation), which is what makes one pattern land with the
    same scale and framing on every face.
    """
    if i in _uv_cache:
        return _uv_cache[i]
    g = geom(i)
    V = g["V"]
    per_face: list[np.ndarray] = []
    for cyc in faces(i):
        xy = _face_xy(V[np.asarray(cyc)])   # the face in its own CCW 2-plane basis
        r = np.linalg.norm(xy, axis=1).max()
        per_face.append(xy / (2 * r) + 0.5)
    tris = face_triangles(i)
    # map triangle corner vertex ids back to positions within their cycle
    cyc_pos = [{v: k for k, v in enumerate(cyc)} for cyc in faces(i)]
    uv = np.empty((len(tris) * 3, 2))
    for t_i, (a, b, c, fi) in enumerate(tris):
        fuv, pos = per_face[fi], cyc_pos[fi]
        uv[t_i * 3 + 0] = fuv[pos[int(a)]]
        uv[t_i * 3 + 1] = fuv[pos[int(b)]]
        uv[t_i * 3 + 2] = fuv[pos[int(c)]]
    _uv_cache[i] = uv
    return uv


def _to3(V: np.ndarray, ang, d4: float):
    """4D rotate, then the 4D→3D perspective divide: (x, y, z, the rotated
    4D points, the divisor). project_h's first half and project3's whole."""
    v = rotate4(V, ang)
    div4 = d4 - v[:, 3]
    k = d4 / div4
    return v[:, 0] * k, v[:, 1] * k, v[:, 2] * k, v, div4


def project3(V: np.ndarray, ang, d4: float = 2.6) -> np.ndarray:
    """The (n, 3) cloud the renderer views: rotated in 4D and divided down
    to 3D, before the camera. What the volume ratio is measured on."""
    x, y, z, _, _ = _to3(V, ang, d4)
    return np.stack([x, y, z], axis=1)


def _camera(x, y, z, yaw: float, pitch: float):
    """The 3D camera's turn: yaw about y, then pitch. (x1, y1, z1); the
    larger z1, the nearer the camera. project_h's middle step."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x1 = x * cy + z * sy
    z1 = -x * sy + z * cy
    y1 = y * cp - z1 * sp
    z1 = y * sp + z1 * cp
    return x1, y1, z1


def view_depth(V: np.ndarray, ang, yaw: float, pitch: float, d4: float = 2.6) -> np.ndarray:
    """How near each vertex is to the 3D camera, nearer larger: z after the
    4D divide and the camera's yaw and pitch, the depth the 3D divide
    reads. What a masked shape's depth cue reads, as a 4D shape's reads
    w (the depth the 4D divide reads)."""
    x, y, z, _, _ = _to3(V, ang, d4)
    return _camera(x, y, z, yaw, pitch)[2]


def project_h(
    V: np.ndarray, ang, yaw: float, pitch: float,
    d4: float = 2.6, w: int = 1200, h: int = 800,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The one transform: project()'s (px, py, pd) plus the combined
    homogeneous divisor per vertex.

    The 4D→3D and 3D→2D steps are each perspective divides; restricted to a
    planar face their composition is one projective map, so the product of
    the two divisors is exactly the w that makes GPU attribute interpolation
    perspective-correct across that face.
    """
    x, y, z, v, div4 = _to3(V, ang, d4)
    x1, y1, z1 = _camera(x, y, z, yaw, pitch)
    div3 = CAM3 - z1 * 0.9
    k2 = CAM3 / div3
    scale = min(w, h) * 0.30
    px = w / 2 + x1 * k2 * scale
    py = h / 2 - y1 * k2 * scale
    return px, py, v[:, 3].copy(), div4 * div3


def shape_view(
    i: int, ang, yaw: float, pitch: float, d4: float = 2.6, w: int = 1200, h: int = 800,
    flat: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """What the renderer draws shape i at: project_h's (px, py, pd, wc) at
    the shape's own angles (view_angles), with pd its depth cue — w for a
    4D shape, the depth toward the 3D camera for a masked one (view_depth).
    A scene (Shape.layers) projects each layer at its own angles: the
    view's, masked as its shape is, times its spin."""
    g = geom(i)
    out = [np.empty(g["n"]) for _ in range(4)]
    for a, b, j, spin in g.get("layers") or [(0, g["n"], i, 1.0)]:
        la = view_angles(j, ang, flat)
        if spin != 1.0:
            la = [float(x) * spin for x in la]
        V = g["V"][a:b] if "layers" in g else g["V"]
        px, py, pd, wc = project_h(V, la, yaw, pitch, d4=d4, w=w, h=h)
        if w_masked(j, flat):
            # its w is 0 at every angle, so the depth cue (pd: fade, width,
            # draw order) would sit flat at its dimmest; it cues on its
            # depth toward the 3D camera (yaw and pitch included, so a
            # camera turned round never puts the far side on top), as a 4D
            # shape cues on its depth toward the 4D eye
            pd = view_depth(V, la, yaw, pitch, d4=d4)
        if "layers" not in g:
            return px, py, pd, wc
        for k, arr in enumerate((px, py, pd, wc)):
            out[k][a:b] = arr
    return out[0], out[1], out[2], out[3]


# ----------------------------------------------------------- volume ratio
#
# How much volume a shape keeps on screen: the projected 3D cloud's
# smallest singular value over its largest (centred). 1 is a ball, 0 a
# plane or a line. A w = 0 shape reads ~0 at a quarter turn of any W
# plane; tools/turntable.py sweeps it, tests/test_shapes4d.py gates on it.

# the floor a lifted or masked shape must keep through a full turn of each
# W plane (plan 22, Stream A's acceptance), calibrated on the 18 4D shapes
# the app already draws as volumes. Their worst case through every W plane
# — from rest and from generic poses, which 2000 random poses of all six
# planes never undercut — is the cubic pyramid's 0.30; then the
# 4,8-duoprism 0.53, the dodecahedral prism 0.64, the tesseract 0.94, the
# Clifford torus 0.97, the 24-cell 1.00. A flat shape's quarter turn reads
# 0.000. The floor is half the 4D worst case: a shape held to it is never
# asked to be rounder than a polytope already is, and the targets' own 3D
# proportions — what a mask leaves them — mostly clear it (heart 0.40,
# torus 0.43, star 0.33, Möbius band 0.158 at its old 0.45 width; the
# rose's 0.118 at its old 0.12 depth did not — 0.192 and 0.157 now).
VOLUME_FLOOR = 0.15
# a pose with every plane turned, for sweeps that are not from rest
GENERIC_POSE = (0.3, 0.7, 1.1, 0.5, 0.9, 1.3)


def volume_ratio(P: np.ndarray) -> float:
    """Smallest over largest singular value of the centred point cloud P."""
    P = np.asarray(P, dtype=np.float64)
    s = np.linalg.svd(P - P.mean(axis=0), compute_uv=False)
    return float(s[-1] / s[0]) if s[0] > 0 else 0.0


def edge_on_share(V: np.ndarray, P: np.ndarray, tris: np.ndarray) -> float:
    """The share of a shape's face area the 4D→3D projection turns
    edge-on: faces drawn at under a tenth of their true (4D) area. The
    second gate beside the volume ratio — it catches a cloud whose volume
    passes while its faces still read as a sheet: tests/test_shapes4d.py
    holds every lifted or masked shape to at most 0.15 through each W
    plane. V the 4D vertices, P their 3D projection, tris the face
    triangles' (T, 3) vertex indices."""
    def area(X):
        a, b = X[tris[:, 1]] - X[tris[:, 0]], X[tris[:, 2]] - X[tris[:, 0]]
        aa, bb, ab = (a * a).sum(1), (b * b).sum(1), (a * b).sum(1)
        return 0.5 * np.sqrt(np.maximum(aa * bb - ab * ab, 0.0))

    true = area(V)
    total = true.sum()
    return float(true[area(P) < 0.1 * true].sum() / total) if total > 0 else 0.0


def _sweep(i: int, plane: str, steps: int, pose, d4: float, measure) -> np.ndarray:
    p = PLANE_NAMES.index(plane)
    V = geom(i)["V"]
    base = [0.0] * 6 if pose is None else [float(a) for a in pose]
    out = np.empty(steps)
    for k in range(steps):
        ang = list(base)
        ang[p] = 2 * math.pi * k / steps
        out[k] = measure(V, project3(V, view_angles(i, ang), d4))
    return out


def sweep_ratios(i: int, plane: str, steps: int = 72, pose=None,
                 d4: float = 2.6) -> np.ndarray:
    """volume_ratio of shape i at each of `steps` angles round one full
    turn of `plane`, the other planes held at `pose` (0 when None). Drawn
    as the renderer draws it, through view_angles."""
    return _sweep(i, plane, steps, pose, d4, lambda V, P: volume_ratio(P))


def sweep_edge_on(i: int, plane: str, steps: int = 72, pose=None,
                  d4: float = 2.6) -> np.ndarray:
    """edge_on_share of shape i round one turn of `plane`, as sweep_ratios."""
    tris = face_triangles(i)[:, :3]
    return _sweep(i, plane, steps, pose, d4, lambda V, P: edge_on_share(V, P, tris))
