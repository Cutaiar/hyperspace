"""Plan 42's example patches (docs/plans/assets/42-controllers/patches/)
are patches this build spawns: the touchpad's and the motion sensors'
rows are rig rows like a hand's."""

import json
from pathlib import Path

import pytest

from hyperspace import patches

HERE = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "42-controllers" / "patches"


@pytest.mark.parametrize("name", ["touch-burst", "shake-hit"])
def test_the_example_patches_check_and_read(name):
    doc = json.loads((HERE / f"{name}.json").read_text())
    assert patches.check(doc) == []
    p = patches.read(doc)
    sources = {r["source"].partition(":")[0] for r in doc["routes"]}
    assert sources & {"touch", "motion"}
    assert p is not None
