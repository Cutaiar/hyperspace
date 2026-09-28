"""Plan-00 exit checks: the golden traces exist and are self-consistent."""

import json
from pathlib import Path

import pytest

from hyperspace.geometry import SHAPES, geom

GOLDEN = Path(__file__).parent / "golden"

# The expected V/E counts come from the code, not a third copy of the
# table (audit D6): the trace's index is the slider index, so the shape it
# was recorded from is geometry.SHAPES[index] and its counts are geom()'s.
def geometry_files() -> list[Path]:
    return sorted((GOLDEN / "geometry").glob("*.json"))


def test_geometry_traces_present():
    assert len(geometry_files()) == 18, "expected one trace per shape"


@pytest.mark.parametrize("path", geometry_files(), ids=lambda p: p.stem)
def test_geometry_trace_consistent(path):
    data = json.loads(path.read_text())
    shape = SHAPES[data["index"]]
    g = geom(data["index"])
    n, m = g["n"], g["m"]
    assert data["name"].startswith(shape.name.split(" ")[0]), (data["name"], shape.name)
    assert data["n"] == n and data["m"] == m, f"{data['name']}: V/E mismatch vs geometry.geom"
    assert len(data["V"]) == n * 4
    assert len(data["E"]) == m * 2
    assert all(0 <= e < n for e in data["E"])
    # unit circumradius: the farthest vertex sits at exactly 1
    radii = [
        sum(data["V"][i * 4 + d] ** 2 for d in range(4)) ** 0.5 for i in range(n)
    ]
    assert abs(max(radii) - 1.0) < 1e-9
    assert len(data["views"]) == 3
    for v in data["views"]:
        assert len(v["px"]) == n and len(v["py"]) == n and len(v["pd"]) == n


def test_audio_manifest():
    manifest = json.loads((GOLDEN / "audio" / "manifest.json").read_text())
    recorded = {k: v for k, v in manifest["clips"].items() if v["status"] == "recorded"}
    assert recorded, "no audio traces recorded"
    for key, entry in recorded.items():
        assert entry["noiseFloorRms"] < 0.05, f"{key}: noise floor over budget"
        trace = GOLDEN / "audio" / entry["file"]
        assert trace.exists(), f"{key}: trace file missing"
        lines = trace.read_text().splitlines()
        assert len(lines) == entry["frames"]
        row = json.loads(lines[0])
        assert len(row) == 20  # t + pos + inp[6] + out[6] + planedrive[6]
