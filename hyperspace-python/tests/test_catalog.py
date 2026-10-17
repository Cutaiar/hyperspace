"""Plan 28 (spike): the catalog of closed 3D solids, the mathematical toys,
the scenes that put several shapes in one frame, plan 22's shortlist of
4-polytopes, and the Shape menu's groups.

The solids are appended after the Klein bottle (index is identity) and are
3D: at w = 0, untouched by the W planes. A scene
(`Shape.layers`) is several shapes sharing one centre, each layer at its
own scale, weight, colour and spin (`geometry.shape_view`).
"""

import numpy as np
import pytest

from hyperspace import geometry as G

CATALOG = list(range(26, len(G.SHAPES)))           # everything plan 28 added
SOLID_FAMILIES = ("Platonic solids", "Archimedean solids", "Catalan solids",
                  "Star polyhedra", "Compounds")
SOLIDS = [i for i in CATALOG if G.SHAPES[i].family in SOLID_FAMILIES]
SCENES = [i for i in CATALOG if G.SHAPES[i].family == "Scenes"]
BY_NAME = {s.name: i for i, s in enumerate(G.SHAPES)}

# V, E, F of every solid: the textbook counts. A star is counted as what is
# seen — its visible surface, the buried core left out
COUNTS = {
    "Tetrahedron": (4, 6, 4), "Cube": (8, 12, 6), "Octahedron": (6, 12, 8),
    "Dodecahedron": (20, 30, 12), "Icosahedron": (12, 30, 20),
    "Cuboctahedron": (12, 24, 14), "Truncated octahedron": (24, 36, 14),
    "Rhombicuboctahedron": (24, 48, 26), "Snub cube": (24, 60, 38),
    "Icosidodecahedron": (30, 60, 32), "Truncated icosahedron": (60, 90, 32),
    "Rhombic dodecahedron": (14, 24, 12), "Rhombic triacontahedron": (32, 60, 30),
    "Small stellated dodecahedron": (32, 90, 60), "Great stellated dodecahedron": (32, 90, 60),
    "Moravian star": (50, 144, 96), "Starburst": (32, 90, 60),
    "Stella octangula": (8, 12, 8), "Five tetrahedra": (20, 30, 20),
    "Five cubes": (20, 60, 30), "Cube + octahedron": (14, 24, 14),
    "Dodecahedron + icosahedron": (32, 60, 32),
}

# plan 22's shortlist, as it measured them (docs/plans/22-polytope-shortlist.md):
# V, E, F and the faces by size
POLYTOPES = {
    "Snub 24-cell": (96, 432, 480, {3: 480}),
    "Rectified 24-cell": (96, 288, 240, {3: 96, 4: 144}),
    "Bitruncated 5-cell": (30, 60, 40, {3: 20, 6: 20}),
    "Omnitruncated 5-cell": (120, 240, 150, {4: 90, 6: 60}),
    "Grand antiprism": (100, 500, 720, {3: 700, 5: 20}),
    "Disphenoidal 288-cell": (48, 336, 576, {3: 576}),
    # the rest of it: every candidate its sheet drew and every form it gave
    # a recipe for (the star polychora as below)
    "Truncated 5-cell": (20, 40, 30, {3: 20, 6: 10}),
    "Cantellated 5-cell": (30, 90, 80, {3: 50, 4: 30}),
    "Runcinated 5-cell": (20, 60, 70, {3: 40, 4: 30}),
    "Cantitruncated 5-cell": (60, 120, 80, {3: 20, 4: 30, 6: 30}),
    "Runcitruncated 5-cell": (60, 150, 120, {3: 40, 4: 60, 6: 20}),
    "Rectified tesseract": (32, 96, 88, {3: 64, 4: 24}),
    "Truncated 16-cell": (48, 120, 96, {3: 64, 6: 32}),
    "Cantellated tesseract": (96, 288, 248, {3: 128, 4: 120}),
    "Runcinated tesseract": (64, 192, 208, {3: 64, 4: 144}),
    "Bitruncated tesseract": (96, 192, 120, {3: 32, 4: 24, 6: 64}),
    "Cantitruncated tesseract": (192, 384, 248, {3: 64, 4: 96, 6: 64, 8: 24}),
    "Runcitruncated tesseract": (192, 480, 368, {3: 128, 4: 192, 8: 48}),
    "Runcitruncated 16-cell": (192, 480, 368, {3: 64, 4: 240, 6: 64}),
    "Omnitruncated tesseract": (384, 768, 464, {4: 288, 6: 128, 8: 48}),
    "Truncated 24-cell": (192, 384, 240, {4: 144, 6: 96}),
    "Cantellated 24-cell": (288, 864, 720, {3: 288, 4: 432}),
    "Runcinated 24-cell": (144, 576, 672, {3: 384, 4: 288}),
    "Bitruncated 24-cell": (288, 576, 336, {3: 192, 8: 144}),
    "Cantitruncated 24-cell": (576, 1152, 720, {3: 192, 4: 288, 6: 96, 8: 144}),
    "Rectified 600-cell": (720, 3600, 3600, {3: 3600}),
    "Dual runcinated 5-cell": (30, 70, 60, {4: 60}),
    # the stars: faces where they are triangles or convex pentagons; a
    # {5/2} pentagram face needs points the face pipeline does not have,
    # so those two are drawn as lines
    "Grand 600-cell": (120, 720, 1200, {3: 1200}),
    "Great 120-cell": (120, 720, 720, {5: 720}),
    "Small stellated 120-cell": (120, 1200, 0, {}),
    "Great grand stellated 120-cell": (600, 1200, 0, {}),
    # its cheap extras: V = nm, E = 2nm for a duoprism; a prism of a solid
    # with (V, E, F) has (2V, 2E + V, 2F + E)
    "3,4-duoprism": (12, 24, 19, {3: 4, 4: 15}),
    "5,5-duoprism": (25, 50, 35, {4: 25, 5: 10}),
    "3,8-duoprism": (24, 48, 35, {3: 8, 4: 24, 8: 3}),
    "5,10-duoprism": (50, 100, 65, {4: 50, 5: 10, 10: 5}),
    "8,8-duoprism": (64, 128, 80, {4: 64, 8: 16}),
    "Pentagonal antiprism prism": (20, 50, 44, {3: 20, 4: 20, 5: 4}),
    "Heptagonal antiprism prism": (28, 70, 60, {3: 28, 4: 28, 7: 4}),
    "Octagonal antiprism prism": (32, 80, 68, {3: 32, 4: 32, 8: 4}),
    "Icosidodecahedral prism": (60, 150, 124, {3: 40, 4: 60, 5: 24}),
    "Truncated icosahedral prism": (120, 240, 154, {4: 90, 5: 24, 6: 40}),
}


def test_the_catalog_is_appended_after_the_klein_bottle():
    assert G.SHAPES[25].name == "Klein bottle" and G.SHAPES[26].name == "Tetrahedron"
    # a scene comes after every shape it names
    for i in SCENES:
        assert all(G.shape_index(L.shape) < i for L in G.SHAPES[i].layers)


@pytest.mark.parametrize("name", POLYTOPES, ids=str)
def test_a_shortlisted_polytope_has_the_counts_plan_22_measured(name):
    # V / E / F as the shortlist checked them against a convex hull
    from collections import Counter

    i = BY_NAME[name]
    g, F = G.geom(i), G.faces(i)
    n, m, f, sizes = POLYTOPES[name]
    assert G.SHAPES[i].dims == 4
    assert (g["n"], g["m"], len(F)) == (n, m, f)
    assert dict(Counter(len(c) for c in F)) == sizes


def test_the_menu_holds_every_shape_once_by_kind():
    seen = [i for _, _, ids in G.menu() for i in ids]
    assert sorted(seen) == list(range(len(G.SHAPES)))
    for sec, fam, ids in G.menu():
        if sec != "Scenes":
            assert all(G.SHAPES[i].dims == int(sec[0]) for i in ids), fam
        assert all(G.SHAPES[i].family == fam for i in ids)
        assert ids == sorted(ids)                    # index order within a family
    sections = [sec for sec, _, _ in G.menu()]
    assert sections == sorted(sections, key=["4D", "3D", "Scenes"].index)


def test_every_solid_has_a_count_and_every_count_a_solid():
    assert {G.SHAPES[i].name for i in SOLIDS} == set(COUNTS)


@pytest.mark.parametrize("i", SOLIDS, ids=lambda i: G.SHAPES[i].name)
def test_a_solid_has_its_textbook_counts(i):
    g, F = G.geom(i), G.faces(i)
    assert (g["n"], g["m"], len(F)) == COUNTS[G.SHAPES[i].name]


@pytest.mark.parametrize("i", CATALOG, ids=lambda i: G.SHAPES[i].name)
def test_a_catalog_shape_is_well_formed(i):
    s, g = G.SHAPES[i], G.geom(i)
    V, E = g["V"], g["E"]
    if s.dims == 3:
        assert (V[:, 3] == 0).all(), "a 3D shape stays in w = 0"
    assert abs(np.linalg.norm(V, axis=1).max() - 1.0) < 1e-9
    assert (E[:, 0] != E[:, 1]).all()
    assert len({frozenset(e) for e in E.tolist()}) == g["m"]
    for cyc in G.faces(i):
        assert len(set(cyc)) == len(cyc) >= 3
    uv = G.face_uvs(i)
    assert uv.size == 0 or (uv.min() >= 0.0 and uv.max() <= 1.0)


@pytest.mark.parametrize("name", ["Tetrahedron", "Cube", "Octahedron", "Dodecahedron",
                                  "Icosahedron"])
def test_a_platonic_solid_is_regular(name):
    # one edge length, one face size, every corner on the sphere
    i = BY_NAME[name]
    g, F = G.geom(i), G.faces(i)
    V = g["V"]
    lens = np.linalg.norm(V[g["E"][:, 0]] - V[g["E"][:, 1]], axis=1)
    assert np.ptp(lens) < 1e-9
    assert len({len(c) for c in F}) == 1
    assert np.allclose(np.linalg.norm(V, axis=1), 1.0)


@pytest.mark.parametrize("name", ["Small stellated dodecahedron", "Great stellated dodecahedron",
                                  "Moravian star", "Starburst"])
def test_a_star_is_closed_like_a_sphere(name):
    # what shows of a star is one closed surface: every edge on two faces,
    # V − E + F = 2; its points on the circumsphere, its valleys inside it
    i = BY_NAME[name]
    g, F = G.geom(i), G.faces(i)
    count: dict = {}
    for c in F:
        for k in range(len(c)):
            e = frozenset((c[k], c[(k + 1) % len(c)]))
            count[e] = count.get(e, 0) + 1
    assert set(count.values()) == {2} and len(count) == g["m"]
    assert g["n"] - g["m"] + len(F) == 2
    r = np.linalg.norm(g["V"], axis=1)
    assert r.min() < 0.6 < r.max() == pytest.approx(1.0)


def test_a_kepler_star_is_spikes_on_its_buried_core():
    # the small stellated dodecahedron: 12 points at the icosahedron's
    # corners, 20 valleys at a buried dodecahedron's; the great stellated:
    # 20 points at the dodecahedron's, 12 valleys at an icosahedron's
    for name, points, valleys in (("Small stellated dodecahedron", 12, 20),
                                  ("Great stellated dodecahedron", 20, 12)):
        r = np.round(np.linalg.norm(G.geom(BY_NAME[name])["V"], axis=1), 9)
        assert sorted(np.unique(r, return_counts=True)[1].tolist()) == sorted([points, valleys])
        assert (r == 1.0).sum() == points


@pytest.mark.parametrize("name,k", [("Five tetrahedra", 5), ("Five cubes", 5),
                                    ("Stella octangula", 2)])
def test_a_compound_shares_its_corners(name, k):
    # the five cubes use each dodecahedron corner twice, the five
    # tetrahedra once; the stella octangula's two tetrahedra fill a cube
    g = G.geom(BY_NAME[name])
    assert g["n"] == (20 if k == 5 else 8)
    assert np.allclose(np.linalg.norm(g["V"], axis=1), 1.0)


def test_dual_compounds_cross_at_their_edges_midpoints():
    for name in ("Cube + octahedron", "Dodecahedron + icosahedron"):
        g = G.geom(BY_NAME[name])
        V, E = g["V"], g["E"]
        mids = (V[E[:, 0]] + V[E[:, 1]]) / 2
        keys = [G.kkey(m) for m in mids]
        # every midpoint is shared by exactly one edge of the other solid
        assert all(keys.count(k) == 2 for k in keys), name


def test_the_hopf_fibration_lies_on_the_3_sphere_in_linked_great_circles():
    i = BY_NAME["Hopf fibration"]
    g = G.geom(i)
    assert G.SHAPES[i].dims == 4 and G.faces(i) == []
    assert np.allclose(np.linalg.norm(g["V"], axis=1), 1.0)
    # each fibre is a great circle: its 36 points span a plane through 0
    for k in range(0, g["n"], 36):
        P = g["V"][k:k + 36]
        assert np.linalg.svd(P, compute_uv=False)[2] < 1e-9


# ---------------------------------------------------------------- scenes

@pytest.mark.parametrize("i", SCENES, ids=lambda i: G.SHAPES[i].name)
def test_a_scene_is_its_layers_in_order(i):
    s, g = G.SHAPES[i], G.geom(i)
    rows = g["layers"]
    assert len(rows) == len(s.layers)
    assert rows[0][0] == 0 and rows[-1][1] == g["n"]
    for (a, b, j, spin), L in zip(rows, s.layers):
        assert G.SHAPES[j].name == L.shape and spin == L.spin
        own = G.geom(j)["V"] * L.scale
        assert np.allclose(g["V"][a:b], own / max(x.scale for x in s.layers))
    # faces only from the layers that draw them
    assert len(G.faces(i)) == sum(len(G.faces(j)) for _, _, j, _ in rows
                                  if s.layers[[r[2] for r in rows].index(j)].faces > 0)


def test_a_scene_turns_each_layer_at_its_own_angles():
    # a layer is drawn where its own shape would be, scaled, at its own
    # shape's angles (a 3D layer has no W turn) times its spin
    i = BY_NAME["Celestial tesseract"]
    g = G.geom(i)
    ang, yaw, pitch = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], 0.4, 0.25
    px, py, pd, _ = G.shape_view(i, ang, yaw, pitch)
    for a, b, j, spin in g["layers"]:
        la = [x * spin for x in G.view_angles(j, ang)]
        qx, qy, qd, _ = G.project_h(g["V"][a:b], la, yaw, pitch)
        assert np.allclose(px[a:b], qx) and np.allclose(py[a:b], qy)
        if G.is_3d(j):
            qd = G.view_depth(g["V"][a:b], la, yaw, pitch)
        assert np.allclose(pd[a:b], qd)


def test_the_star_pokes_through_the_tesseract():
    # the scene's point: at rest, the star's tips reach past the faces of
    # the tesseract's inner cube while the glome stays round them both
    i = BY_NAME["Celestial tesseract"]
    g = G.geom(i)
    P = G.project3(g["V"], [0.0] * 6)
    (h0, h1, _, _), (t0, t1, _, _), (s0, s1, _, _) = g["layers"]
    inner = np.abs(P[t0:t1][g["V"][t0:t1, 3] < 0]).max()       # the w < 0 cube's half side
    star = np.abs(P[s0:s1]).max(axis=1)
    assert (star > inner).sum() >= 6
    assert np.linalg.norm(P[h0:h1], axis=1).max() > np.linalg.norm(P[t0:t1], axis=1).max()


def test_a_shape_that_is_not_a_scene_is_drawn_as_before():
    # shape_view on one shape is project_h at view_angles, the depth cue
    # swapped for a 3D one: the renderer's old path, to the bit
    ang, yaw, pitch = [0.3, 0.1, 0.7, 0.2, 0.5, 0.9], 0.4, -0.2
    for i in (3, 18, 21, BY_NAME["Cube"]):
        V = G.geom(i)["V"]
        a = G.view_angles(i, ang)
        want = list(G.project_h(V, a, yaw, pitch))
        if G.is_3d(i):
            want[2] = G.view_depth(V, a, yaw, pitch)
        for got, w in zip(G.shape_view(i, ang, yaw, pitch), want):
            assert np.array_equal(got, w)


# ------------------------------------------------------- vector subjects

FLOW_MARK, FLOW_CAPS = BY_NAME["Flow mark"], BY_NAME["Flow capsules"]


def _bars(V: np.ndarray, faces: list) -> list:
    """Each bar's (x centre, width, height), left to right."""
    out = []
    for c in faces:
        P = V[np.asarray(c)]
        out.append((P[:, 0].mean(), np.ptp(P[:, 0]), np.ptp(P[:, 1])))
    return sorted(out)


def test_the_flow_mark_is_five_stadia_as_the_svg_draws_them():
    # five bars of one width on one pitch, their heights the SVG's: the
    # two outer bars tallest, then the middle one, the two short ones equal
    g = G.geom(FLOW_MARK)
    V, F = g["V"], G.faces(FLOW_MARK)
    assert all(G.SHAPES[i].dims == 3 and G.SHAPES[i].family == "Vector marks"
               for i in (FLOW_MARK, FLOW_CAPS))
    assert len(F) == 5 and (V[:, 2] == 0).all() and g.get("flat") and g.get("curve")
    bars = _bars(V, F)
    widths = [b[1] for b in bars]
    assert np.ptp(widths) < 1e-9
    assert np.ptp(np.diff([b[0] for b in bars])) < 1e-3          # one pitch
    h = [b[2] / widths[0] for b in bars]                          # height in widths
    svg = [(bot - top) / (2 * G.FLOW_R) for _, top, bot in G.FLOW_BARS]
    assert h == pytest.approx(svg, abs=1e-3)
    assert h[0] == pytest.approx(h[4], abs=0.01) and h[1] == pytest.approx(h[3])
    assert h[0] > h[2] > h[1]


def test_the_flow_mark_shows_one_picture_through_its_bars():
    # its face UVs are the mark's own plane: a corner's UV is an affine
    # function of where it is, the same for every bar
    g = G.geom(FLOW_MARK)
    V, F = g["V"], G.faces(FLOW_MARK)
    P = np.concatenate([V[np.asarray(c), :2] for c in F])
    uv = np.concatenate([np.asarray(f) for f in g["FUV"]])
    A = np.hstack([P, np.ones((len(P), 1))])
    fit = np.linalg.lstsq(A, uv, rcond=None)[0]
    assert np.allclose(A @ fit, uv)
    assert fit[0, 0] > 0 and fit[0, 0] == pytest.approx(fit[1, 1])  # square, not stretched


def test_the_flow_capsules_are_the_marks_bars_lifted():
    # each bar, seen face-on, has the flat mark's outline; in depth it is
    # round, one bar's width deep; its UVs wrap it, v running up the bar
    caps, mark = G.geom(FLOW_CAPS), G.geom(FLOW_MARK)
    V = caps["V"]
    assert np.allclose(V[:, :2].min(0), mark["V"][:, :2].min(0))
    assert np.allclose(V[:, :2].max(0), mark["V"][:, :2].max(0))
    width = _bars(mark["V"], G.faces(FLOW_MARK))[0][1]
    assert np.ptp(V[:, 2]) == pytest.approx(width)
    for cyc, f in zip(G.faces(FLOW_CAPS), caps["FUV"]):
        u, v = np.asarray(f).T
        assert np.ptp(u) <= 1 / 16 + 1e-9                      # no quad spans the seam
        dy, dv = np.subtract.outer(V[cyc, 1], V[cyc, 1]), np.subtract.outer(v, v)
        assert (dy * dv >= -1e-12).all()                     # v rises with y
