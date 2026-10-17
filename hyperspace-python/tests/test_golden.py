"""Plan-00 exit checks: the golden traces exist and are self-consistent."""

import json
import re
from pathlib import Path

import pytest

from hyperspace.geometry import SHAPES, geom

GOLDEN = Path(__file__).parent / "golden"
ENGINEERING = Path(__file__).parents[1] / "docs" / "ENGINEERING.md"


def ve_table() -> list[tuple[str, int, int]]:
    """The V/E rows of ENGINEERING §1, parsed, in slider order — the one
    table readers cite, so it is the one this file checks against the
    code (audit D6: no third copy here). Both shape tables are read; a
    row is `| # | name | … | V | E |`."""
    text = ENGINEERING.read_text()
    section = text[text.index("## 1. Geometry"):text.index("## 2. Rendering")]
    rows = []
    for line in section.splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|.*\|\s*(\d+)\s*\|\s*(\d+)\s*\|$", line)
        if m:
            rows.append((m.group(2), int(m.group(3)), int(m.group(4))))
    return rows


def geometry_files() -> list[Path]:
    return sorted((GOLDEN / "geometry").glob("*.json"))


def test_geometry_traces_present():
    assert len(geometry_files()) == 18, "expected one trace per shape"


def test_the_engineering_table_matches_the_code():
    """ENGINEERING §1 lists every shape's V and E; the numbers are geom()'s."""
    rows = ve_table()
    assert len(rows) == len(SHAPES) == 58
    for i, (name, n, m) in enumerate(rows):
        g = geom(i)
        first = SHAPES[i].name.split(" ")[0].lower()[:4]
        assert name.lower().startswith(first), (i, name, SHAPES[i].name)
        assert (g["n"], g["m"]) == (n, m), (
            f"row {i + 1} {name}: ENGINEERING says {n}/{m}, geom {g['n']}/{g['m']}"
        )


@pytest.mark.parametrize("path", geometry_files(), ids=lambda p: p.stem)
def test_geometry_trace_consistent(path):
    """The trace is self-consistent and names the shape at its slider index
    (its V/E against the code is test_core's `test_construction_exact`)."""
    data = json.loads(path.read_text())
    shape = SHAPES[data["index"]]
    n, m = data["n"], data["m"]
    assert data["name"].startswith(shape.name.split(" ")[0]), (data["name"], shape.name)
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
