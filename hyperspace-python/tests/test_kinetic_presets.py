"""The kinetic presets (`presets/kinetic/`) open cleanly.

They are files for the owner's library, not part of the app (nothing ships:
DECISIONS "One tier"), so nothing else reads them. Each must land through the
library's own load with no unknown id and no note: a route dropped at load is
a gesture that does nothing on stage. `grip/` holds two setups of the hand
rig (plan 60) for the grip's own strip.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hyperspace import grip, headless, library

KINETIC = Path(__file__).resolve().parents[1] / "presets" / "kinetic"
FILES = sorted(KINETIC.glob("*.json"))


GRIPS = sorted((KINETIC / "grip").glob("*.json"))


def test_there_are_six_and_two_grip_setups():
    assert len(FILES) == 6
    assert [p.stem for p in GRIPS] == ["gyro", "held"]


@pytest.mark.parametrize("path", GRIPS, ids=lambda p: p.stem)
def test_a_grip_setup_opens_from_the_grip_strip(path, tmp_path):
    """The grip is the meta controller's (grip.py), so no kinetic preset can
    set it: its two setups are patches of the grip group, for the HANDS
    page's strip."""
    doc = json.loads(path.read_text())
    folder = tmp_path / library.PATCHES / grip.GROUP
    folder.mkdir(parents=True)
    shutil.copy(path, folder / path.name)
    app = headless.make_app(tmp_path)
    state = grip.GripState()
    grip.register(app.reg, state)
    assert app.lib.load(grip.GROUP, path.stem) == []
    assert not app.lib.warning
    assert state.on
    for pid, value in doc["values"].items():
        assert app.reg[pid].value == pytest.approx(value), pid


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_a_kinetic_preset_opens_with_no_note(path, tmp_path):
    doc = json.loads(path.read_text())
    assert doc["name"] == path.stem
    folder = tmp_path / library.LOADABLE
    folder.mkdir(parents=True)
    shutil.copy(path, folder / path.name)
    app = headless.make_app(tmp_path)
    missing = app.loaded_patch.load(path.stem)
    assert missing == []
    assert not app.lib.warning
    live = {(b.source, b.target) for b in app.router.table.routes()}
    for row in doc["routes"]:
        assert (row["source"], row["target"]) in live, row
    for pid, value in doc["values"].items():
        assert app.reg[pid].base == pytest.approx(value), pid
