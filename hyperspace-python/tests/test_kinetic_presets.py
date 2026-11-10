"""The kinetic presets (`presets/kinetic/`) open cleanly.

They are files for the owner's library, not part of the app (nothing ships:
DECISIONS "One tier"), so nothing else reads them. Each must land through the
library's own load with no unknown id and no note: a route dropped at load is
a gesture that does nothing on stage.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hyperspace import headless, library

KINETIC = Path(__file__).resolve().parents[1] / "presets" / "kinetic"
FILES = sorted(KINETIC.glob("*.json"))


def test_there_are_six():
    assert len(FILES) == 6


def test_only_comet_turns_the_grip_on(tmp_path):
    """The grip is a patch's own (plan 60): comet is thrown, so it carries
    the grip's values; clay's grab is its own turn rows, and the grip with
    them would turn the shape twice over."""
    on = [p.stem for p in FILES if json.loads(p.read_text())["values"].get("grip.on")]
    assert on == ["kinetic-comet"]
    clay = json.loads((KINETIC / "kinetic-clay.json").read_text())
    assert any(r["op"] == "turn" for r in clay["routes"])


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
