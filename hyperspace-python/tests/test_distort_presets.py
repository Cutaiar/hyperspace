"""The distortion patches (`presets/distort/`) open cleanly.

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

DISTORT = Path(__file__).resolve().parents[1] / "presets" / "distort"
FILES = sorted(DISTORT.glob("*.json"))


def test_there_are_twenty_three_and_each_wires_what_it_turns_on():
    assert len(FILES) == 23
    for p in FILES:
        doc = json.loads(p.read_text())
        wired = {w["to"].split(".")[0] for w in doc["graph"]["wires"]}
        on = {k.split(".")[1] for k, v in doc["values"].items()
              if k.startswith("fx.") and k.endswith(".on") and v}
        assert on and on <= wired and on <= {"shake", "wave", "blocks"}, p.stem
        # something rides an Amount, and a hand is on the patch: it plays
        riders = {r["source"] for r in doc["routes"] if r["target"].endswith(".amount")}
        hands = {r["source"] for r in doc["routes"] if r["source"].startswith("hand:")}
        assert riders & {"lane:0", "hand:right.y"} and hands, p.stem


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_a_distortion_patch_opens_with_no_note(path, tmp_path):
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
