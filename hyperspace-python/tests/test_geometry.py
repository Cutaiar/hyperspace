"""geometry.py's face extraction: the 2-face counts of the polytopes
(moved from test_control.py, audit D5; the 3D shapes' faces are in
test_shapes3d.py, the vertex / edge parity in test_core.py)."""

import threading
import time

import pytest

from hyperspace import geometry
from hyperspace.geometry import SHAPES, faces

FACE_COUNTS = {
    "5-cell": 10,
    "Tesseract": 24,
    "16-cell": 32,
    "24-cell": 96,
    "Rectified 5-cell": 30,
    "Cubic pyramid": 18,
    "3,3-duoprism": 15,
    "Icosahedral prism": 70,
    "Dodecahedral prism": 54,
}


@pytest.mark.parametrize("name", FACE_COUNTS, ids=str)
def test_face_counts(name):
    i = next(k for k, s in enumerate(SHAPES) if s.name == name)
    assert len(faces(i)) == FACE_COUNTS[name]


@pytest.mark.slow
def test_face_counts_heavy():
    by_name = {s.name: i for i, s in enumerate(SHAPES)}
    assert len(faces(by_name["120-cell"])) == 720
    assert len(faces(by_name["600-cell"])) == 1200
    assert len(faces(by_name["Clifford torus"])) == 560


# ---- the startup warm and the faster builds

def _fresh_caches(monkeypatch):
    for name in ("_cache", "_face_cache", "_tri_cache", "_uv_cache", "_locks"):
        monkeypatch.setattr(geometry, name, {})


def test_warm_order_puts_the_startup_shape_first():
    n = len(SHAPES)
    assert geometry.warm_order() == list(range(n))
    order = geometry.warm_order(first=16)
    assert order[0] == 16 and sorted(order) == list(range(n))
    assert geometry.warm_order(first=n) == list(range(n))   # not a shape: no move


@pytest.mark.slow
def test_warm_all_fills_every_shapes_caches(monkeypatch):
    # the startup warm: every cache the renderer reads, for every shape in
    # the catalog (polytopes, solids, surfaces, curves, scenes), off the frame
    _fresh_caches(monkeypatch)
    t = geometry.warm_all(first=geometry.shape_index("600-cell"))
    assert t.daemon
    t.join(timeout=120)
    assert not t.is_alive()
    every = set(range(len(SHAPES)))
    assert set(geometry._cache) == every
    assert set(geometry._face_cache) == every
    assert set(geometry._tri_cache) == every
    assert set(geometry._uv_cache) == every


def test_a_frame_and_the_warmer_build_a_shape_once(monkeypatch):
    # the render thread asking for a shape the warmer is building waits
    # for the warmer's result instead of building it a second time
    _fresh_caches(monkeypatch)
    i = geometry.shape_index("24-cell")
    calls = []
    real = geometry._planar_cycles
    gate = threading.Event()

    def slow(g, *a, **k):
        calls.append(threading.current_thread().name)
        gate.wait(5)
        return real(g, *a, **k)

    monkeypatch.setattr(geometry, "_planar_cycles", slow)
    warmer = threading.Thread(target=geometry.warm, args=(i,))
    warmer.start()
    while not calls:
        time.sleep(0.001)
    got = []
    frame = threading.Thread(target=lambda: got.append(geometry.face_uvs(i)))
    frame.start()
    time.sleep(0.05)
    gate.set()
    warmer.join(5)
    frame.join(5)
    assert len(calls) == 1
    assert got[0] is geometry._uv_cache[i]


def _old_d2(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _old_classes(V, tol):
    ds = []
    for i in range(len(V)):
        for j in range(i + 1, len(V)):
            d = _old_d2(V[i], V[j])
            if not any(abs(d - x) <= x * tol for x in ds):
                ds.append(d)
    return ds


@pytest.mark.parametrize("build", [
    geometry._build_24cell, geometry._build_tesseract, geometry._build_16cell,
    geometry._build_cuboct, geometry._build_icosa,
], ids=lambda f: f.__name__)
def test_vectorised_edges_match_the_pair_walk(build):
    # the numpy pair distances, classes and edges are the nested loops' own
    V = build()["V"]
    n = len(V)
    mn = min(_old_d2(V[i], V[j]) for i in range(n) for j in range(i + 1, n))
    lim = mn * (1 + 1e-4) + 1e-9
    old = [[i, j] for i in range(n) for j in range(i + 1, n) if _old_d2(V[i], V[j]) <= lim]
    assert geometry.edges_by_min_dist(V) == old
    _, _, d = geometry._pair_d2(V)
    assert geometry._distance_classes(d, 1e-4) == _old_classes(V, 1e-4)
    two = sorted(_old_classes(V, 1e-4))[:2]
    old2 = [[i, j] for i in range(n) for j in range(i + 1, n)
            if any(abs(_old_d2(V[i], V[j]) - x) <= x * 1e-4 for x in two)]
    assert geometry.edges_by_classes(V, 2) == old2
