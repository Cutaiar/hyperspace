"""4D polytope construction — port of the geometry section of hyperspace.html.

Vertex order is load-bearing: the golden traces index vertices by
construction order, so every builder walks in exactly the order the JS
did (JS Map insertion order == Python dict insertion order).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.random import default_rng

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

    def __post_init__(self) -> None:
        if self.w not in W_KINDS:
            raise ValueError(f"{self.name}: w must be one of {W_KINDS}, not {self.w!r}")


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
    return _cache[i]


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


def w_masked(i: int) -> bool:
    """Whether shape i keeps its W planes masked (Shape.w == "mask")."""
    return SHAPES[i].w == "mask"


def view_angles(i: int, ang):
    """The angles shape i is drawn at: `ang` itself, unless the shape's W
    planes are masked — then a new list with each W angle added onto its
    3D plane (W_REMAP) and the W planes at 0. A pure function of the
    view's angles, read where the frame is drawn: the integrator and the
    rot.* params are untouched, so a rate or a phase routed to a W plane
    lands on the 3D plane alike, and every other shape's pose never
    depends on which shapes were shown before it."""
    if not w_masked(i):
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
        np.hstack([A, default_rng(1).standard_normal((4, 2))])
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


# ------------------------------------------------------------ the one camera
#
# Plan 26 A2. The renderer's path is no longer project_h: the CPU takes a
# vertex to 3D (`world_points`: rotate4, the 4D divide, the yaw/pitch
# turntable) and the GPU takes it on to the clip through two 4×4s — the
# shape's world transform (`model_matrix`: camera.zoom scales it about the
# world origin, camera.pan moves it) and the eye (`eye_matrix`: a fixed
# perspective camera, the `eye.*` params). The default eye IS project_h's
# 3D divide: CAM3 − 0.9·z1 is an eye at CAM3 / 0.9 on +z looking at the
# origin, and min(w, h)·SCALE px per unit at the origin is a field of view
# across the shorter side with tan(fov / 2) = 1 / (2·SCALE·distance). With
# the default eye, zoom 1 and pan 0, `eye_project` lands every vertex
# where project_h puts it (tests/test_camera.py: within a millionth of a
# pixel in float64, and the float32 the GPU sees well inside half a pixel);
# project / project_h stay the parity oracle.

SCALE = 0.30                         # project_h's px per unit at the origin, × min(w, h)
EYE_DISTANCE = CAM3 / 0.9            # world units from the eye to the origin
EYE_FOV = math.degrees(2.0 * math.atan(1.0 / (2.0 * SCALE * EYE_DISTANCE)))   # ≈ 47.6°
EYE_NEAR = 0.05                      # the eye's clip planes, world units: depth for
EYE_FAR = 1000.0                     # the scene's depth test, nothing the picture shows
# a preset/2 file's camera.pan is in logical px; through the default eye a
# px at the origin is min(w, h)·SCALE of a unit, and the reference screen
# is the 1080p render cap (the projector the party runs on): 324 px a unit
PAN_REF_PX = SCALE * 1080.0


def world_points(V: np.ndarray, ang, yaw: float, pitch: float, d4: float = 2.6):
    """The CPU's half of the one camera: (P, div4, w) — P (n, 3) the
    vertices after the 4D tumble, the 4D divide and the yaw/pitch
    turntable (x right, y up, z toward the eye), in the shape's own units
    (the unit circumradius), before camera.zoom/pan; div4 the 4D divisor,
    which the face shader multiplies into its clip w so the faces' uv
    stays perspective-correct across the 4D divide as well; w the rotated
    4D w, project_h's pd (the depth cue)."""
    x, y, z, v, div4 = _to3(V, ang, d4)
    x1, y1, z1 = _camera(x, y, z, yaw, pitch)
    return np.stack([x1, y1, z1], axis=1), div4, v[:, 3].copy()


def model_matrix(zoom: float = 1.0, pan=(0.0, 0.0)) -> np.ndarray:
    """camera.zoom / camera.pan as the shape's world transform, 4×4
    (column vectors): scale about the world origin, then move. pan is in
    world units — the shape's unit circumradius — with pan.y positive
    *down* the screen, as it always was (so a stored or routed pan keeps
    its direction): world y is up, so it moves by −pan.y."""
    m = np.eye(4)
    m[0, 0] = m[1, 1] = m[2, 2] = float(zoom)
    m[0, 3], m[1, 3] = float(pan[0]), -float(pan[1])
    return m


def eye_matrix(w: float, h: float, fov: float = EYE_FOV, distance: float = EYE_DISTANCE,
               near: float = EYE_NEAR, far: float = EYE_FAR) -> np.ndarray:
    """The eye's view-projection, 4×4 (column vectors): at `distance` on
    +z looking at the world origin, y up, `fov` degrees across the
    shorter side of a (w, h) picture (the longer side sees more), OpenGL
    clip space. The defaults are project_h's divide (module comment)."""
    f = 1.0 / math.tan(math.radians(fov) / 2.0)
    aspect = max(float(w), 1e-6) / max(float(h), 1e-6)
    p = np.zeros((4, 4))
    if aspect >= 1.0:
        p[0, 0], p[1, 1] = f / aspect, f
    else:
        p[0, 0], p[1, 1] = f, f * aspect
    p[2, 2] = (far + near) / (near - far)
    p[2, 3] = 2.0 * far * near / (near - far)
    p[3, 2] = -1.0
    view = np.eye(4)
    view[2, 3] = -float(distance)
    return p @ view


def eye_project(V: np.ndarray, ang, yaw: float, pitch: float, d4: float = 2.6,
                w: int = 1200, h: int = 800, *, zoom: float = 1.0, pan=(0.0, 0.0),
                fov: float = EYE_FOV, distance: float = EYE_DISTANCE,
                dtype=np.float64) -> tuple[np.ndarray, np.ndarray]:
    """(px, py) in logical pixels, y down, through the one camera: what
    the scene's vertex shader computes (`render.FACE_VS`, `LINE_VS`), on
    the CPU. `dtype=np.float32` does the GPU's arithmetic (positions and
    the matrix in float32). With the default eye, zoom 1 and pan 0 it is
    project_h's (px, py)."""
    P, _, _ = world_points(V, ang, yaw, pitch, d4)
    mvp = (eye_matrix(w, h, fov, distance) @ model_matrix(zoom, pan)).astype(dtype)
    q = np.concatenate([P, np.ones((len(P), 1))], axis=1).astype(dtype)
    c = q @ mvp.T
    nx, ny = c[:, 0] / c[:, 3], c[:, 1] / c[:, 3]
    return (w / 2 + nx * (w / 2)).astype(np.float64), (h / 2 - ny * (h / 2)).astype(np.float64)


def px_per_unit(w: float, h: float, fov: float = EYE_FOV,
                distance: float = EYE_DISTANCE) -> float:
    """Logical px a world unit spans at the world origin (depth 0) through
    the eye: what a pan moves the shape's centre by on screen. The default
    eye's is project_h's min(w, h)·SCALE."""
    return min(float(w), float(h)) / 2.0 / math.tan(math.radians(fov) / 2.0) / float(distance)


def pan_px_to_world(px: float) -> float:
    """A preset/2 file's camera.pan (logical px) in world units, through
    the default eye at the reference screen (`PAN_REF_PX`): the shape's
    centre lands where it did on that screen."""
    return float(px) / PAN_REF_PX


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
