"""The point-cloud test patch (`loadable/clouds/`) opens cleanly: no note, every cloud
declared with the device its README says, the wired two in the scene, every
value landed. A file for the owner's library, copied by its README's command,
as the other patch sets are (`tests/test_kinect_preset.py`)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import readme_copy

from hyperspace import headless, library

CLOUDS = Path(__file__).resolve().parents[1] / "loadable" / "clouds"
PATCH = CLOUDS / "cloud-test.json"


def test_it_opens_with_no_note_and_its_clouds_as_the_readme_says(tmp_path):
    doc = json.loads(PATCH.read_text())
    folder = tmp_path / library.LOADABLE / "clouds"
    folder.mkdir(parents=True)
    shutil.copy(PATCH, folder / PATCH.name)
    app = headless.make_app(tmp_path)
    assert app.loaded_patch.load("clouds/cloud-test") == []
    assert app.loaded_patch.migrated == ""
    spec = app.loaded_patch.graph.spec
    assert [(c.name, c.device) for c in spec.clouds] == [
        ("cloud", "scan"), ("cloud.2", "room"), ("cloud.3", "")]
    geo = [w.src for w in spec.wires if w.dst == "scene.geometry"]
    assert "cloud" in geo and "cloud.2" in geo and "cloud.3" not in geo
    for pid, value in doc["values"].items():
        assert app.reg[pid].base == pytest.approx(value), pid
    assert app.reg["cloud.instances"].base == 4


def test_the_readme_copies_into_the_library_the_config_names(tmp_path):
    drive, machine = tmp_path / "drive", tmp_path / "machine"
    (drive / library.LOADABLE).mkdir(parents=True)
    done = readme_copy.run(CLOUDS / "README.md", machine, drive)
    assert done.returncode == 0, done.stderr
    assert (drive / library.LOADABLE / "clouds" / PATCH.name).exists()
