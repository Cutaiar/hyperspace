"""The kinetic presets (`loadable/kinetic/`) open cleanly.

They are files for the owner's library, not part of the app (nothing ships:
DECISIONS "One tier"), so nothing else reads them. Each must land through the
library's own load with no unknown id and no note: a route dropped at load is
a gesture that does nothing on stage. (Plan 90 H2: kinetic-clay holds a
look-back, which opens as public parts with the migration's own note; its
rows and values land retargeted, none dropped.) Each is opened from where its README
copies it: the library's `loadable/kinetic/`, by its folder-qualified name.
The README's own command is run too (`readme_copy`): it must land the files
in the library `[library] path` names, as desktop startup reads it
(`tests/test_copy_patches.py` has what it refuses).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import readme_copy

from hyperspace import graphmigrate, headless, library

KINETIC = Path(__file__).resolve().parents[1] / "loadable" / "kinetic"
FILES = sorted(KINETIC.glob("*.json"))


def _only_look_back_notes(warning: str) -> bool:
    """No warning, or only notes from the look-back's conversion to public parts."""
    return not warning or (graphmigrate.is_parts_note(warning) and "unknown id" not in warning
                           and "graph:" not in warning)


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
    folder = tmp_path / library.LOADABLE / "kinetic"
    folder.mkdir(parents=True)
    shutil.copy(path, folder / path.name)
    app = headless.make_app(tmp_path)
    missing = app.loaded_patch.load(f"kinetic/{path.stem}")
    assert missing == []
    assert _only_look_back_notes(app.lib.warning)
    # (plan 90 H2: what lands is the document as the look-back's migration
    # rewrites it — every row and value of it, none dropped)
    fwd = graphmigrate.forward(doc, {})
    assert len(fwd.doc["routes"]) == len(doc["routes"])
    doc = fwd.doc
    live = {(b.source, b.target) for b in app.router.table.routes()}
    for row in doc["routes"]:
        assert (row["source"], row["target"]) in live, row
    for pid, value in doc["values"].items():
        assert app.reg[pid].base == pytest.approx(value), pid


def test_the_readme_copies_into_the_library_the_config_names(tmp_path):
    drive, machine = tmp_path / "drive", tmp_path / "machine"
    (drive / library.LOADABLE).mkdir(parents=True)
    done = readme_copy.run(KINETIC / "README.md", machine, drive)
    assert done.returncode == 0, done.stderr
    assert f"{len(FILES)} copied" in done.stdout
    landed = drive / library.LOADABLE / "kinetic"
    assert sorted(q.name for q in landed.glob("*.json")) == [q.name for q in FILES]
    assert not (machine / library.LOADABLE).exists()     # never ~/Hyperspace
    # opened as desktop startup opens it: the library at `[library] path`
    app = headless.make_app(drive, machine=machine)
    assert app.loaded_patch.load(f"kinetic/{FILES[0].stem}") == []
    assert _only_look_back_notes(app.lib.warning)

