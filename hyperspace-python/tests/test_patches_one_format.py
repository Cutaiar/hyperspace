"""Plan 50: one saved format — a patch, a group and a preset are one
document shape (`patches.shape_of`); every fragment comes in through one
ladder (`patches.forward`: a ``patch/1`` and a ``hyperspace.preset/1``
module preset read as their ``patch/2``); a module preset is a **patch of
one param group** under ``<library>/patches/<group>/``, loaded from its
strip as a spawn that replaces that group's values; and the migration
tool's step moves a library's module presets and ``/1`` patches into the
shape, a backup first.

Old files are opened end to end (REVIEW.md: not only the converter): an
old module preset in a group's folder loads from the strip, an old
``patch/1`` spawns from GRAPH's library door, and a corpus preset
round-trips byte for byte through the preset's one loader."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
from conftest import CORPUS, seed

from hyperspace import headless, patches
from hyperspace.library import PATCHES, LibraryError

ROOT = Path(__file__).resolve().parents[1]
ACID_WASH = ROOT / "tests" / "fixtures" / "patches" / "acid-wash.json"
WAKE = CORPUS / "patches" / "dream" / "wake.json"
OLD_MODULE = {"schema": "hyperspace.preset/1", "group": "dream", "name": "OLD",
              "note": "a module preset from before plan 50",
              "values": {"dream.mix": 0.25, "dream.echoes": 12}}


def _tool():
    if "migrate_library" in sys.modules:
        return sys.modules["migrate_library"]
    spec = importlib.util.spec_from_file_location("migrate_library",
                                                  ROOT / "tools" / "migrate_library.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_library"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- the ladder and the shape

def test_the_one_ladder_reads_every_fragment_as_its_patch_2():
    old = copy.deepcopy(OLD_MODULE)
    new = patches.forward(old)
    assert old == OLD_MODULE                                   # the input is never changed
    assert new == {"schema": "hyperspace.patch/2", "name": "OLD",
                   "note": "a module preset from before plan 50", "group": "dream",
                   "values": {"dream.mix": 0.25, "dream.echoes": 12}}
    one = json.loads(ACID_WASH.read_text())
    assert one["schema"] == "hyperspace.patch/1"
    two = patches.forward(one)
    assert two == {**one, "schema": "hyperspace.patch/2"}
    assert patches.forward(two) == two                        # /2 is a fixed point
    assert patches.check(one) == [] and patches.check(two) == []
    for bad, words in (({"schema": "hyperspace.patch/3"}, "newer than this build"),
                       ({"schema": "hyperspace.preset/10"}, "is not a hyperspace.patch"),
                       ({"schema": "hyperspace.preset/2", "group": "dream"}, "newer"),
                       ({"name": "no schema"}, "is not a hyperspace.patch")):
        with pytest.raises(ValueError, match=words):
            patches.forward(bad)


def test_shape_of_reads_the_one_shape_three_ways():
    preset_doc = json.loads((CORPUS / "presets" / "party-trip.json").read_text())
    assert patches.shape_of(preset_doc) == patches.PRESET_SHAPE
    assert patches.shape_of(json.loads(ACID_WASH.read_text())) == patches.PATCH_SHAPE
    assert patches.shape_of(json.loads(WAKE.read_text())) == patches.GROUP_SHAPE
    assert patches.shape_of(patches.forward(OLD_MODULE)) == patches.GROUP_SHAPE
    # a preset is a patch that fills the frame: it writes no ports
    assert "ports" not in preset_doc


def test_a_group_patch_spawns_as_its_values_replacing_its_group():
    doc = patches.forward(OLD_MODULE)
    assert patches.check(doc) == []
    landing = patches.spawn(doc, patches.Host())
    assert landing.replaces == "dream" and landing.values == OLD_MODULE["values"]
    assert landing.conflicts == () and landing.nodes == () and landing.group == {}
    # a group patch holds values only: the canvas, rows and voices are refused in words
    said = patches.check({**doc, "routes": [], "nodes": []})
    assert said == [patches.GROUP_ONLY_WORDS.format(key="nodes", group="dream"),
                    patches.GROUP_ONLY_WORDS.format(key="routes", group="dream")]
    assert patches.read(doc).group == "dream" and patches.read(doc).layout == {}


def test_the_corpus_is_in_the_one_shape():
    for path in sorted((CORPUS / "patches" / "dream").glob("*.json")):
        doc = json.loads(path.read_text())
        assert doc["schema"] == "hyperspace.patch/2" and doc["group"] == "dream", path.name
        assert patches.check(doc) == [] and patches.forward(doc) == doc
    assert not (CORPUS / "dream").exists()
    for path in sorted((CORPUS / "presets").glob("*.json")):
        assert b'"modules"' not in path.read_bytes(), path.name


def test_the_presets_ladder_is_one_function_the_load_reads_through():
    """A whole preset's steps (`seven`, `nine`, `ten`) are one function,
    `graphmigrate.forward`, which the load runs: a `/10` passes untouched,
    a `/2` comes out `/7`-shaped and said."""
    import inspect

    from hyperspace import graphmigrate, preset
    assert "graphmigrate.forward(" in inspect.getsource(preset.Presets.load_doc)
    new = json.loads((CORPUS / "presets" / "party-trip.json").read_text())
    fwd = graphmigrate.forward(copy.deepcopy(new), {})
    assert fwd.doc == new and fwd.notes == () and fwd.migrated == ""
    old = json.loads((ROOT / "tests" / "fixtures" / "factory-sources" / "presets"
                      / "party-trip.json").read_text())
    fwd = graphmigrate.forward(old, {})
    assert fwd.migrated.startswith(f"{old['schema']} migrated to hyperspace.preset/10")
    assert "modules" not in fwd.doc and "desk_template" not in fwd.doc


# ---------------------------------------------------------------- end to end

def test_a_corpus_preset_round_trips_byte_for_byte_through_the_one_loader(tmp_path):
    for k, name in enumerate(("party-trip", "party-noita", "seq-demo")):
        data = (CORPUS / "presets" / f"{name}.json").read_bytes()
        again, notes, _ = headless.resave(CORPUS / "presets" / f"{name}.json", tmp_path / str(k))
        assert again == data and notes == [], name


def test_a_module_preset_lives_and_loads_as_a_patch_of_its_group(tmp_path):
    seed(tmp_path, "dream")
    app = headless.make_app(tmp_path)
    lib, reg = app.lib, app.reg
    assert (tmp_path / PATCHES / "dream" / "wake.json").is_file()
    assert lib.list("dream") == ["default", "tracer-only", "wake"]
    # never among the spawnable patches, and refused by name at GRAPH's door
    assert lib.list(PATCHES) == []
    assert lib.load("dream", "wake") == []
    assert reg["dream.echoes"].value == 24 and reg["dream.mix"].value == pytest.approx(0.5)
    assert lib.current("dream") == "wake" and not lib.is_dirty("dream")
    # a save writes the one shape into the group's folder, the old text to the trash
    reg["dream.mix"].set_value(0.9)
    path = lib.save_as("dream", "WAKE LOUD")
    assert path == tmp_path / PATCHES / "dream" / "wake-loud.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.patch/2" and doc["group"] == "dream"
    assert doc["values"]["dream.mix"] == pytest.approx(0.9)
    assert set(doc) == {"schema", "name", "group", "values"}
    assert lib.list(PATCHES) == []
    with pytest.raises(LibraryError, match="a patch of the dream group"):
        shutil.copy(path, tmp_path / PATCHES / "loud.json")
        lib._sync()
        lib.read_patch("loud")


def test_an_old_module_preset_in_its_folder_opens_end_to_end(tmp_path):
    folder = tmp_path / PATCHES / "dream"
    folder.mkdir(parents=True)
    (folder / "old.json").write_text(json.dumps(OLD_MODULE))
    app = headless.make_app(tmp_path)
    assert app.lib.list("dream") == ["OLD"]
    assert app.lib.load("dream", "OLD") == []
    assert app.reg["dream.mix"].value == pytest.approx(0.25)
    assert app.reg["dream.echoes"].value == 12
    # a re-save writes it in today's words, where it was
    path = app.lib.overwrite("dream")
    assert path == folder / "old.json"
    assert json.loads(path.read_text())["schema"] == "hyperspace.patch/2"


def test_an_old_patch_1_reads_as_its_2_through_the_library(tmp_path):
    (tmp_path / PATCHES).mkdir(parents=True)
    shutil.copy(ACID_WASH, tmp_path / PATCHES / "acid-wash.json")
    app = headless.make_app(tmp_path)
    doc = app.lib.read_patch("acid-wash")
    assert doc["schema"] == "hyperspace.patch/2"
    host = patches.Host.of(app.presets.graph.spec, app.router.table, app.presets.banks())
    landing = patches.spawn(doc, host)
    assert {e.get("file") for e in landing.nodes if e.get("kind") == "effect"} == {
        "acid", "wobble"}
    assert landing.replaces == ""


# ---------------------------------------------------------------- the migration's step

def _old_library(root: Path) -> Path:
    (root / "presets").mkdir(parents=True)
    (root / "dream").mkdir()
    (root / "dream" / "old.json").write_text(json.dumps(OLD_MODULE))
    (root / "dream" / ".tmp.json").write_text("{}")
    (root / "camera").mkdir()
    (root / "camera" / "wide.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/1", "name": "Wide",
         "values": {"camera.zoom": 0.7}, "units": {"camera.pan": "world"}}))
    (root / "fx").mkdir()
    (root / "fx" / "wobbly.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/1", "group": "fx", "name": "wobbly", "values": {}}))
    (root / PATCHES).mkdir()
    shutil.copy(ACID_WASH, root / PATCHES / "acid-wash.json")
    return root


def test_the_tool_moves_module_presets_and_patch_1_into_the_shape(tmp_path):
    tool = _tool()
    root = _old_library(tmp_path / "lib")
    moves, left = tool.group_plan(root)
    assert sorted((s.relative_to(root).as_posix(), d.relative_to(root).as_posix())
                  for s, d, _ in moves) == [
        ("camera/wide.json", "patches/camera/wide.json"),
        ("dream/old.json", "patches/dream/old.json"),
        ("patches/acid-wash.json", "patches/acid-wash.json")]
    assert left == ["fx/wobbly.json: a retired group's — left as it is"]
    assert (root / "dream" / "old.json").is_file()            # planning writes nothing
    assert tool.group_write(moves) == []
    assert not (root / "camera").exists()                     # an emptied folder goes
    assert [p.name for p in (root / "dream").iterdir()] == [".tmp.json"]   # (not emptied)
    assert (root / "fx" / "wobbly.json").is_file()
    wide = json.loads((root / PATCHES / "camera" / "wide.json").read_text())
    assert wide == {"schema": "hyperspace.patch/2", "name": "Wide", "group": "camera",
                    "values": {"camera.zoom": 0.7}, "units": {"camera.pan": "world"}}
    acid = json.loads((root / PATCHES / "acid-wash.json").read_text())
    assert acid["schema"] == "hyperspace.patch/2"
    assert tool.group_plan(root) == ([], ["fx/wobbly.json: a retired group's — left as it is"])
    # and the app opens what the step wrote
    app = headless.make_app(root)
    assert app.lib.list("camera") == ["Wide"] and app.lib.load("camera", "Wide") == []
    assert app.reg["camera.zoom"].value == pytest.approx(0.7)
    assert app.lib.list(PATCHES) == ["acid wash"]


def test_the_tool_dry_run_writes_nothing_and_apply_backs_up_first(tmp_path, monkeypatch, capsys):
    tool = _tool()
    root = _old_library(tmp_path / "lib")
    machine = tmp_path / "machine"
    monkeypatch.setenv("HYPERSPACE_HOME", str(machine))
    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
    assert tool.main(["--library", str(root)]) == 0
    out = capsys.readouterr().out
    assert "patches to write as hyperspace.patch/2: 3" in out
    assert "dream/old.json → patches/dream/old.json" in out
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) == before
    assert tool.main(["--library", str(root), "--apply"]) == 0
    out = capsys.readouterr().out
    (backup,) = [p for p in machine.iterdir() if p.name.startswith(tool.BACKUP_PREFIX)]
    assert (backup / "dream" / "old.json").read_text() == json.dumps(OLD_MODULE)
    assert "wrote 3 patch(es) as hyperspace.patch/2" in out
    assert (root / PATCHES / "dream" / "old.json").is_file()


# ---------------------------------------------------------------- review fixes (PR #352)

def test_a_group_never_holds_the_rigs_kinds_one_list_with_graphview():
    """Review fix 1: a media channel, a window, All outputs and a cloud are
    the rig's (`patches.RIG_KINDS`, `graphview.RIG_KINDS` the same list):
    Group refuses them, so a group never carries what no patch can."""
    from hyperspace import graph as G
    from hyperspace import graphview
    assert graphview.RIG_KINDS is patches.RIG_KINDS
    spec = G.read_graph({"frame": "wired", "wires": [
        {"from": "channel.a", "to": "warp.image"}, {"from": "warp", "to": "output.all.image"}]})
    held, said = patches.groupable(spec, None, ["render:channel.a", "render:warp",
                                                "render:output.all"])
    assert held.render == ("warp",)
    assert said == [patches.CHANNEL_WORDS.format(name="channel.a"),
                    patches.WINDOW_WORDS.format(name="output.all")]


def test_an_empty_group_key_is_one_refusal_and_one_reading():
    """Review fix 6: `check` and `shape_of` read the key the same way — a
    `group` present but empty or not text is a group patch's key that names
    nothing, refused in one line whatever else the file holds."""
    canvas = patches.forward(json.loads(ACID_WASH.read_text()))
    for bad in ("", None, 3):
        doc = {**canvas, "group": bad}
        assert patches.shape_of(doc) == patches.GROUP_SHAPE
        assert patches.check(doc) == [patches.GROUP_EMPTY_WORDS.format(value=bad)]
        assert not patches.names_group(doc)


def test_a_groups_folder_refuses_what_is_no_patch_of_that_group(tmp_path):
    """Review fix 7: in `patches/dream/`, a whole preset, a canvas patch and
    another group's patch are each refused, the mismatch named — never
    landed as dream values."""
    folder = tmp_path / PATCHES / "dream"
    folder.mkdir(parents=True)
    shutil.copy(CORPUS / "presets" / "dial.json", folder / "dial.json")
    shutil.copy(ACID_WASH, folder / "acid.json")
    (folder / "cam.json").write_text(json.dumps(patches.group_doc("camera", "cam", {})))
    (folder / "blank.json").write_text(json.dumps({**patches.group_doc("dream", "b", {}),
                                                    "group": ""}))
    app = headless.make_app(tmp_path)
    for name, words in (("dial", "dial.json is a whole preset, not a patch of the dream group"),
                        ("acid wash", "acid.json is a canvas patch, not a patch of the dream"),
                        ("cam", "cam.json is a patch of the camera group, not a patch of"),
                        ("b", "the key names no param group")):
        with pytest.raises(LibraryError, match=words):
            app.lib.read("dream", name)


def test_the_tool_says_an_unreadable_patch(tmp_path):
    """Review fix 5: a `patches/*.json` that does not read is left, said."""
    tool = _tool()
    root = _old_library(tmp_path / "lib")
    (root / PATCHES / "torn.json").write_text("{not json")
    _moves, left = tool.group_plan(root)
    assert "patches/torn.json: does not read — left as it is" in left


def test_a_headless_resave_sees_the_librarys_patches(tmp_path):
    """Review fix 2: the scratch home a resave loads in holds the library's
    `patches/`, every folder down — the module groups' patches with it."""
    lib = tmp_path / "lib"
    (lib / PATCHES / "dream").mkdir(parents=True)
    shutil.copy(WAKE, lib / PATCHES / "dream" / "wake.json")
    shutil.copy(ACID_WASH, lib / PATCHES / "acid-wash.json")
    assert headless.SHARED_FOLDERS == (PATCHES,)
    headless.resave(CORPUS / "presets" / "dial.json", tmp_path / "scratch", library=lib)
    home = tmp_path / "scratch" / "library"
    assert (home / PATCHES / "dream" / "wake.json").is_file()
    assert (home / PATCHES / "acid-wash.json").is_file()
