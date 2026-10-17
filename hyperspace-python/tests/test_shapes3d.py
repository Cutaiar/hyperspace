"""The 3D trig-shape family: polar / spherical / parametric builders.

These shapes are appended after the 18 polytopes (the slider index is the
identity the golden traces key on) and carry explicit face cycles instead
of relying on planar-cycle extraction. They are 3D (Shape.dims == 3): at
w = 0, untouched by the W planes (tests/test_shapes4d.py).
"""

import numpy as np
import pytest

from hyperspace import geometry as G

# the trig family (shapes 19–26); the plan 28 catalog after it has its own
# tests (tests/test_catalog.py)
NEW3D = [i for i, s in enumerate(G.SHAPES) if i >= 18 and not s.family]


def test_polytope_count_unchanged():
    # append-only: the first 18 indices must stay the polytopes the golden
    # traces were recorded against
    assert len(G.SHAPES) > 18
    assert G.SHAPES[17].name == "Clifford torus"


@pytest.mark.parametrize("i", NEW3D, ids=[G.SHAPES[i].name for i in NEW3D])
def test_shape3d_valid(i):
    g = G.geom(i)
    V, E, n, m = g["V"], g["E"], g["n"], g["m"]
    # 3D: in the w = 0 hyperplane
    assert G.SHAPES[i].dims == 3 and (V[:, 3] == 0).all()
    # unit circumradius like every other shape
    assert abs(np.linalg.norm(V, axis=1).max() - 1.0) < 1e-9
    # within the renderer's design envelope (≤600 V / ≤1200 E per shape)
    assert n <= 600 and m <= 1200
    assert E.min() >= 0 and E.max() < n
    # no degenerate or duplicate edges
    assert (E[:, 0] != E[:, 1]).all()
    assert len({frozenset(e) for e in E.tolist()}) == m
    # coincident grid points were merged: no two vertices closer than kkey
    d = np.linalg.norm(V[:, None, :] - V[None, :, :], axis=2)
    np.fill_diagonal(d, 1.0)
    assert d.min() > 1e-7


@pytest.mark.parametrize("i", NEW3D, ids=[G.SHAPES[i].name for i in NEW3D])
def test_shape3d_faces(i):
    g = G.geom(i)
    F = G.faces(i)
    assert F, "explicit face cycles expected"
    for cyc in F:
        assert len(cyc) >= 3
        assert len(set(cyc)) == len(cyc), "face cycles must be simple polygons"
        assert all(0 <= v < g["n"] for v in cyc)
    tris = G.face_triangles(i)
    # every cycle triangulates to exactly len − 2 triangles (fan or ear clip)
    assert len(tris) == sum(len(c) - 2 for c in F)
    assert (tris[:, 3] == np.repeat(np.arange(len(F)), [len(c) - 2 for c in F])).all()
    uv = G.face_uvs(i)
    assert uv.shape == (len(tris) * 3, 2)
    assert uv.min() >= 0.0 and uv.max() <= 1.0


def test_ear_clip_covers_nonconvex_cap():
    # the heart's front cap is nonconvex: fan triangulation from vertex 0
    # would spill outside; ear clipping must reproduce the polygon's area
    heart = next(i for i in NEW3D if G.SHAPES[i].name == "Heart")
    g = G.geom(heart)
    caps = [c for c in G.faces(heart) if len(c) > 4]
    assert len(caps) == 2, "front and back cap"
    for cyc in caps:
        xy = G._face_xy(g["V"][np.asarray(cyc)])
        poly_area = 0.5 * abs(
            float(np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - np.roll(xy[:, 0], -1) * xy[:, 1]))
        )
        pos = {v: k for k, v in enumerate(cyc)}
        tri_area = 0.0
        tris = G.face_triangles(heart)
        for a, b, c, fi in tris:
            if G.faces(heart)[fi] is not cyc:
                continue
            pa, pb, pc = xy[pos[int(a)]], xy[pos[int(b)]], xy[pos[int(c)]]
            tri_area += 0.5 * abs(
                (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
            )
        # a fan on this cap overshoots the true area; ear clipping matches it
        assert abs(tri_area - poly_area) < 1e-6 * max(poly_area, 1.0)


def test_polytope_fan_triangulation_preserved():
    # convex polytope faces must keep the original fan from cyc[0] —
    # bit-identical output guards the visual parity already signed off
    for i in (0, 3, 7, 10, 16):
        tris = G.face_triangles(i)
        k = 0
        for fi, cyc in enumerate(G.faces(i)):
            for j in range(1, len(cyc) - 1):
                assert tuple(tris[k][:3]) == (cyc[0], cyc[j], cyc[j + 1])
                assert tris[k][3] == fi
                k += 1
        assert k == len(tris)


def test_mobius_seam_merges():
    # the u = 2π column coincides with the u = 0 column flipped in v; kkey
    # dedup must weld the strip closed (Euler check: V − E + F = 0 for a
    # closed Möbius band would need the boundary… just check the weld)
    mob = next(i for i in NEW3D if G.SHAPES[i].name == "Möbius strip")
    g = G.geom(mob)
    assert g["n"] == 65 * 5 - 5, "endpoint column welded onto the start column"


def test_rose_pinches_at_origin():
    # r = cos 2θ passes through r = 0 four times; those grid points must
    # collapse to one shared front vertex and one shared back vertex
    rose = next(i for i in NEW3D if G.SHAPES[i].name == "Rose")
    g = G.geom(rose)
    on_axis = np.sum((np.abs(g["V"][:, 0]) < 1e-9) & (np.abs(g["V"][:, 1]) < 1e-9))
    assert on_axis == 2


KLEIN = next(i for i, s in enumerate(G.SHAPES) if s.name == "Klein bottle")


def test_the_klein_bottle_is_appended_after_the_mobius_strip():
    # index is identity: the 26th shape, every earlier index where it was;
    # the plan 28 catalog starts after it
    assert KLEIN == 25 == NEW3D[-1]
    assert G.SHAPES[24].name == "Möbius strip"
    assert G.SHAPES[26].family


def test_the_klein_bottle_seam_welds_into_a_closed_grid():
    # 37 × 16 samples; the u = π column lands on the u = 0 column flipped
    # in v and merges by kkey, leaving a closed 36 × 16 grid of quads —
    # no gap, no sliver, no doubled face — with the Klein bottle's χ = 0
    g, F = G.geom(KLEIN), G.faces(KLEIN)
    assert g["n"] == 36 * 16 and g["m"] == 2 * g["n"] and len(F) == g["n"]
    assert all(len(c) == 4 for c in F)
    assert len({frozenset(c) for c in F}) == len(F)
    assert g["n"] - g["m"] + len(F) == 0
    # every edge borders exactly two faces: closed, nothing open at the seam
    count: dict = {}
    for c in F:
        for k in range(4):
            e = frozenset((c[k], c[(k + 1) % 4]))
            count[e] = count.get(e, 0) + 1
    assert set(count.values()) == {2} and len(count) == g["m"]


def test_the_klein_bottle_crosses_itself_in_3d():
    # sample the surface finely: in xyz the neck passes through the body
    # (far-apart parameters, the same point) — as every Klein bottle in 3D
    u = np.linspace(0, np.pi, 120, endpoint=False)
    v = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    uv = [(a, b) for a in u for b in v]
    P = np.array([G._klein_xyz(a, b) for a, b in uv])
    U = np.array([a for a, _ in uv])
    crossings = 0
    for k in range(0, len(P), 1200):
        d = np.linalg.norm(P[k:k + 1200, None] - P[None], axis=2)
        i, j = np.nonzero(d < 0.03)
        i = i + k
        far = (np.abs(U[i] - U[j]) > 0.5) & (np.abs(U[i] - U[j]) < np.pi - 0.5)
        crossings += int(far.sum())
    assert crossings > 0, "the 3D immersion should cross itself"
