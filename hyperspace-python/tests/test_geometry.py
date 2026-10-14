"""geometry.py's face extraction: the 2-face counts of the polytopes
(moved from test_control.py, audit D5; the 3D shapes' faces are in
test_shapes3d.py, the vertex / edge parity in test_core.py)."""

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


def test_warm_all_fills_every_shapes_caches(monkeypatch):
    # the startup warm: every cache the renderer reads, built off the frame
    for name in ("_cache", "_face_cache", "_tri_cache", "_uv_cache"):
        monkeypatch.setattr(geometry, name, {})
    geometry.warm_all(first=16).join(timeout=60)
    every = set(range(len(SHAPES)))
    assert set(geometry._cache) == every
    assert set(geometry._face_cache) == every
    assert set(geometry._tri_cache) == every
    assert set(geometry._uv_cache) == every
