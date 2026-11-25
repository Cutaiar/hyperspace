"""The Kinect demo patch (`loadable/kinect/`) opens cleanly: no unknown id, no
note, no dropped route, and every look of its switch is wired. A file for the
owner's library, copied by its README's command, as the other patch sets are
(`tests/test_kinetic_presets.py`)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import readme_copy

from hyperspace import headless, library

KINECT = Path(__file__).resolve().parents[1] / "loadable" / "kinect"
PATCH = KINECT / "kinect-mirror.json"


def test_it_opens_with_no_note(tmp_path):
    doc = json.loads(PATCH.read_text())
    folder = tmp_path / library.LOADABLE / "kinect"
    folder.mkdir(parents=True)
    shutil.copy(PATCH, folder / PATCH.name)
    app = headless.make_app(tmp_path)
    assert app.loaded_patch.load("kinect/kinect-mirror") == []
    assert not app.lib.warning
    live = {(b.source, b.target) for b in app.router.table.routes()}
    for row in doc["routes"]:
        assert (row["source"], row["target"]) in live, row
    for pid, value in doc["values"].items():
        assert app.reg[pid].base == pytest.approx(value), pid


def test_every_look_is_wired_and_every_effect_it_turns_on():
    doc = json.loads(PATCH.read_text())
    to = {w["to"] for w in doc["graph"]["wires"]}
    assert {f"switch.in{k}" for k in range(1, 6)} <= to
    on = {k.split(".")[1] for k, v in doc["values"].items() if k.startswith("fx.") and k.endswith(".on") and v}
    assert on <= {t.split(".")[0] for t in to}
    assert set(doc["media"]["channels"]["b"]) == {"kinect:room/depth", "kinect:room/color"}


def test_the_readme_copies_into_the_library_the_config_names(tmp_path):
    drive, machine = tmp_path / "drive", tmp_path / "machine"
    (drive / library.LOADABLE).mkdir(parents=True)
    done = readme_copy.run(KINECT / "README.md", machine, drive)
    assert done.returncode == 0, done.stderr
    assert (drive / library.LOADABLE / "kinect" / PATCH.name).exists()
