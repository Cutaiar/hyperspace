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


@dataclass(frozen=True)
class Shape:
    name: str
    alias: str
    cells: int
    sym: str
    build: object = field(repr=False)


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
    return _cache[i]


# ------------------------------------------------------------- transforms

PLANES = [[0, 1], [0, 2], [1, 2], [0, 3], [1, 3], [2, 3]]
RATE = [0.62, 0.47, 0.31, 1.00, 0.79, 0.55]
CAM3 = 3.4


def rotate4(V: np.ndarray, ang) -> np.ndarray:
    """Sequential per-plane rotation, exactly as draw() applies it in-place."""
    v = V.copy()
    for p in range(6):
        a, b = PLANES[p]
        c, s = math.cos(ang[p]), math.sin(ang[p])
        va, vb = v[:, a].copy(), v[:, b].copy()
        v[:, a] = va * c - vb * s
        v[:, b] = va * s + vb * c
    return v


def project(
    V: np.ndarray, ang, yaw: float, pitch: float,
    d4: float = 2.6, w: int = 1200, h: int = 800,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The full draw() transform: 4D rotate → 4D→3D → view → 3D→2D.

    Returns (px, py, pd) matching the reference renderer at viewport (w, h),
    DPR 1. pd is the post-rotation w-coordinate used for depth cueing.
    """
    v = rotate4(V, ang)
    k = d4 / (d4 - v[:, 3])
    x, y, z = v[:, 0] * k, v[:, 1] * k, v[:, 2] * k
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x1 = x * cy + z * sy
    z1 = -x * sy + z * cy
    y1 = y * cp - z1 * sp
    z1 = y * sp + z1 * cp
    k2 = CAM3 / (CAM3 - z1 * 0.9)
    scale = min(w, h) * 0.30
    px = w / 2 + x1 * k2 * scale
    py = h / 2 - y1 * k2 * scale
    return px, py, v[:, 3].copy()
