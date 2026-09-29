"""geometry.py's face extraction: the 2-face counts of the polytopes
(moved from test_control.py, audit D5; the 3D shapes' faces are in
test_shapes3d.py, the vertex / edge parity in test_core.py)."""

import pytest

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
