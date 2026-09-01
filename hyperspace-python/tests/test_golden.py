"""Plan-00 exit checks: the golden traces exist and are self-consistent."""

import json
from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"

# The V/E table from docs/ENGINEERING.md §2, in slider order.
VE_TABLE = [
    ("5-cell", 5, 10),
    ("3,3-duoprism", 9, 18),
    ("Cubic pyramid", 9, 20),
    ("Tesseract", 16, 32),
    ("Rectified 5-cell", 10, 30),
    ("4,8-duoprism", 32, 64),
    ("6,6-duoprism", 36, 72),
    ("16-cell", 8, 24),
    ("10,10-duoprism", 100, 200),
    ("Icosahedral prism", 24, 72),
    ("24-cell", 24, 96),
    ("Truncated tesseract", 64, 128),
    ("12,12-duoprism", 144, 288),
    ("Dodecahedral prism", 40, 80),
    ("20,20-duoprism", 400, 800),
    ("120-cell", 600, 1200),
    ("600-cell", 120, 720),
    ("Clifford torus", 512, 1024),
]


def geometry_files() -> list[Path]:
    return sorted((GOLDEN / "geometry").glob("*.json"))


def test_geometry_traces_present():
    assert len(geometry_files()) == 18, "expected one trace per shape"


@pytest.mark.parametrize("path", geometry_files(), ids=lambda p: p.stem)
def test_geometry_trace_consistent(path):
    data = json.loads(path.read_text())
    name, n, m = VE_TABLE[data["index"]]
    assert data["name"].startswith(name.split(" ")[0]), (data["name"], name)
    assert data["n"] == n and data["m"] == m, f"{data['name']}: V/E mismatch vs ENGINEERING §2"
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
