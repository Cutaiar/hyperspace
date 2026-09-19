"""The preset & project library: files, shadowing, dirty state, live edits.

Every test builds its library on tmp_path (or points HYPERSPACE_HOME at
one) — nothing here may touch ~/Hyperspace.
"""

import json
import os
from types import SimpleNamespace

import pytest

from hyperspace import config, library
from hyperspace.analysis import Analyser
from hyperspace.bands import PRESETS, Chain
from hyperspace.control import Control
from hyperspace.library import FACTORY, Library, LibraryError, legacy_slot, migrate_doc, slug
from hyperspace.params import build_registry
from hyperspace.render import ViewState

_clock = [1_000_000_000.0]


def touch(path):
    """Bump a file's mtime past anything the watcher has seen."""
    _clock[0] += 2
    os.utime(path, (_clock[0], _clock[0]))


def edit(path, fn):
    doc = json.loads(path.read_text())
    fn(doc)
    path.write_text(json.dumps(doc))
    touch(path)


def make(home):
    chain = Chain(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, audio, lib.bank)
    lib.attach(reg)
    return SimpleNamespace(lib=lib, reg=reg, view=view, control=control, chain=chain)


@pytest.fixture()
def rig(tmp_path):
    return make(tmp_path)


# ---------------------------------------------------------------- home

def test_home_resolves_env_then_default(monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERSPACE_HOME", str(tmp_path / "lib"))
    assert library.home() == tmp_path / "lib"
    monkeypatch.delenv("HYPERSPACE_HOME")
    assert library.home() == library.DEFAULT_HOME.expanduser()


def test_first_run_migrates_working_directory_files(tmp_path, monkeypatch, capsys):
    cwd, home = tmp_path / "cwd", tmp_path / "home"
    cwd.mkdir()
    (cwd / "config.toml").write_text('[midi]\nport = "X"\n')
    (cwd / "midi_map.json").write_text('{"version": 1, "bindings": []}')
    (cwd / "presets.json").write_text(json.dumps({"version": 1, "slots": [
        None, {"name": "MINE", "scene": 3, "view": {"shape": 4, "planes": [True] * 6},
               "bands": [{"fn": 2, "atk": 0.5}], "master": {"gain": 2.0}},
    ]}))
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    cfg = config.load()
    assert cfg["midi"]["port"] == "X"
    assert cfg["midi"]["map"] == str(home / "midi_map.json")   # resolved into the home
    assert (home / "config.toml").read_text() == (cwd / "config.toml").read_text()
    assert (cwd / "config.toml").exists()                       # originals stay
    err = capsys.readouterr().err
    assert "config.toml" in err and "presets.json" in err
    # the legacy theme bank became the user's default project, seeds filling the gaps
    r = make(home)
    assert r.lib.bank.slots[0]["name"] == "BIG BLUE WAVE"
    assert r.lib.bank.slots[1]["values"] == {
        "view.shape": 4, **{f"view.plane.{n}": True for n in library.PLANES},
        "scene.select": 3, "band.0.fn": 2, "band.0.atk": 0.5, "master.gain": 2.0,
    }
    r.lib.bank.load(1)
    assert r.view.shape == 4 and r.chain.params[0].atk == 0.5 and r.chain.gain == 2.0
    # second run: nothing to do, nothing said
    library.ensure_home(home, cwd)
    assert capsys.readouterr().err == ""


def test_config_explicit_path_keeps_working(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[overlay]\nbg = 0.5\n")
    cfg = config.load(p)
    assert cfg["overlay"]["bg"] == 0.5 and cfg["midi"]["enabled"] is True
    assert cfg["midi"]["map"] == str(tmp_path / "midi_map.json")


# ---------------------------------------------------------------- files

def test_factory_presets_ship_in_the_package():
    assert (FACTORY / "projects" / "default.hyp.json").is_file()
    names = {json.loads(p.read_text())["name"] for p in (FACTORY / "band").glob("*.json")}
    assert names == {s["name"] for s in PRESETS}
    doc = json.loads((FACTORY / "band" / "balanced.json").read_text())
    assert doc["schema"] == "hyperspace.preset/1" and doc["group"] == "band"
    # the analyzer contract: a layout next to the flat band.{i}.* values
    assert [b["curve"] for b in doc["layout"]["bands"]] == ["rect"] * 6
    assert doc["layout"]["bands"][0]["f"] == pytest.approx((20 * 60) ** 0.5)
    assert doc["layout"]["bands"][0]["q"] == pytest.approx((20 * 60) ** 0.5 / 40)
    assert doc["values"]["band.1.atk"] == 0.015


def test_slug():
    assert slug("Kick & Sizzle") == "kick-sizzle"
    assert slug("  Slow Bass / Fast Air ") == "slow-bass-fast-air"
    assert slug("***") == "untitled"


def test_list_user_shadows_factory(rig, tmp_path):
    lib = rig.lib
    assert lib.list("band") == sorted((s["name"] for s in PRESETS), key=str.lower)
    assert lib.is_factory("band", "Balanced")
    assert lib.list("nothing") == []
    assert "band" in lib.groups() and "view" in lib.groups()
    # a user file with the factory slug takes over; the name is what the file says
    user = tmp_path / "band" / "balanced.json"
    user.parent.mkdir()
    doc = json.loads((FACTORY / "band" / "balanced.json").read_text())
    doc["values"]["band.0.atk"] = 0.123
    user.write_text(json.dumps(doc))
    assert lib.list("band").count("Balanced") == 1
    assert not lib.is_factory("band", "Balanced")
    lib.load("band", "Balanced")
    assert rig.chain.params[0].atk == 0.123
    # deleting the shadow brings the factory one back
    assert lib.delete("band", "Balanced")
    assert lib.is_factory("band", "Balanced") and lib.current("band") == "Balanced"
    assert not lib.delete("band", "Balanced")     # factory files are read-only


# ---------------------------------------------------------------- presets

def test_load_fills_missing_ids_from_the_default_preset(rig, tmp_path):
    lib = rig.lib
    (tmp_path / "band").mkdir()
    (tmp_path / "band" / "sparse.json").write_text(json.dumps({
        "schema": "hyperspace.preset/1", "group": "band", "name": "Sparse",
        "values": {"band.3.atk": 0.9, "band.9.atk": 1.0},
    }))
    lib.load("band", "Kick & Sizzle")
    assert rig.chain.params[0].fn == 12
    missing = lib.load("band", "Sparse")
    assert missing == ["band.9.atk"] and "band.9.atk" in lib.warning
    assert rig.chain.params[3].atk == 0.9
    assert rig.chain.params[0].fn == 1               # Balanced, not Kick & Sizzle
    assert lib.current("band") == "Sparse" and not lib.is_dirty("band")


def test_dirty_save_as_overwrite_reset(rig, tmp_path):
    lib, reg = rig.lib, rig.reg
    assert lib.current("view") is None and not lib.is_dirty("view")
    reg["view.bright"].set_value(2.0)
    assert lib.is_dirty("view")
    path = lib.save_as("view", "Loud One")
    assert path == tmp_path / "view" / "loud-one.json"
    assert lib.current("view") == "Loud One" and not lib.is_dirty("view")
    assert lib.list("view") == ["Loud One"]
    doc = json.loads(path.read_text())
    assert doc["group"] == "view" and doc["values"]["view.bright"] == 2.0
    assert set(doc["values"]) == {p.id for p in reg.group("view") if p.persist}

    reg["view.shape"].set(9)
    assert lib.is_dirty("view")
    assert lib.overwrite("view") == path
    assert not lib.is_dirty("view")
    assert json.loads(path.read_text())["values"]["view.shape"] == 9

    assert lib.reset("view") is None                 # view has no default preset: fresh
    assert rig.view.bright == 1.0 and rig.view.shape == 3
    assert lib.current("view") is None
    # band resets to Balanced by name
    reg["band.0.atk"].set(0.7)
    assert lib.reset("band") == "Balanced"
    assert rig.chain.params[0].atk == 0.25 and lib.current("band") == "Balanced"
    # a factory preset overwritten becomes a user shadow, the factory file untouched
    reg["band.0.atk"].set(0.7)
    assert lib.overwrite("band") == tmp_path / "band" / "balanced.json"
    assert json.loads((FACTORY / "band" / "balanced.json").read_text())["values"]["band.0.atk"] == 0.25


def test_rename_and_delete_are_user_only(rig, tmp_path):
    lib = rig.lib
    lib.save_as("camera", "Wide")
    assert lib.rename("camera", "Wider")
    assert lib.list("camera") == ["Wider"] and lib.current("camera") == "Wider"
    assert not (tmp_path / "camera" / "wide.json").exists()
    assert json.loads((tmp_path / "camera" / "wider.json").read_text())["name"] == "Wider"
    assert not lib.rename("band", "Nope", "Percussive")     # factory
    assert not lib.delete("camera", "never was")
    assert lib.delete("camera", "Wider")
    assert lib.list("camera") == [] and lib.current("camera") is None


def test_next_prev_cycle_by_name(rig):
    lib = rig.lib
    names = lib.list("band")
    assert lib.next("band") == names[0]
    assert lib.next("band") == names[1]
    assert lib.prev("band") == names[0]
    assert lib.prev("band") == names[-1]              # wraps
    assert lib.next("view") is None                   # nothing to cycle


def test_layout_hook_runs_before_values(rig):
    seen = []
    rig.lib.on_layout("band", lambda layout: seen.append((len(layout["bands"]),
                                                          rig.chain.params[0].fn)))
    rig.lib.load("band", "Kick & Sizzle")
    assert seen == [(6, 1)]                           # six bands; values not yet applied


def test_bad_files_are_reported_not_fatal(rig, tmp_path):
    lib = rig.lib
    d = tmp_path / "view"
    d.mkdir()
    (d / "broken.json").write_text("{not json")
    (d / "future.json").write_text(json.dumps({"schema": "hyperspace.preset/9", "name": "F",
                                               "group": "view", "values": {}}))
    (d / "other.json").write_text(json.dumps({"schema": "hyperspace.preset/1", "name": "O",
                                              "group": "camera", "values": {}}))
    assert lib.list("view") == ["broken", "F", "O"]  # listed by name, or by file
    with pytest.raises(LibraryError, match="broken.json"):
        lib.load("view", "broken")
    with pytest.raises(LibraryError, match="newer"):
        lib.load("view", "F")
    with pytest.raises(LibraryError, match="camera preset"):
        lib.load("view", "O")
    with pytest.raises(LibraryError, match="no preset"):
        lib.load("view", "nope")


def test_schema_migration_table():
    with pytest.raises(LibraryError, match="no schema"):
        migrate_doc({}, "hyperspace.preset")
    with pytest.raises(LibraryError, match="not a hyperspace.project"):
        migrate_doc({"schema": "hyperspace.preset/1"}, "hyperspace.project")
    library.MIGRATIONS[("hyperspace.preset", 0)] = lambda d: {"schema": d["schema"], "values": d["v"]}
    try:
        out = migrate_doc({"schema": "hyperspace.preset/0", "v": {"a": 1}}, "hyperspace.preset")
        assert out == {"schema": "hyperspace.preset/1", "values": {"a": 1}}
    finally:
        del library.MIGRATIONS[("hyperspace.preset", 0)]
    with pytest.raises(LibraryError, match="no migration"):
        migrate_doc({"schema": "hyperspace.preset/0"}, "hyperspace.preset")


def test_legacy_slot_conversion():
    assert legacy_slot({"name": "X", "view": {"pan": [1, 2], "unknown": 3}}) == {
        "name": "X", "values": {"camera.pan.x": 1, "camera.pan.y": 2}}


# ---------------------------------------------------------------- projects

def test_project_save_load_new(rig, tmp_path):
    lib, reg = rig.lib, rig.reg
    assert lib.project.name == "default" and lib.project.path is None   # the factory one
    lib.load("band", "Percussive")
    lib.save_as("view", "Mine")
    reg["camera.zoom"].set_value(3.0)
    reg["master.gain"].set(2.5)
    lib.bank.save(2)
    p = lib.project.save("Gig")
    assert p == tmp_path / "projects" / "gig.hyp.json"
    assert lib.project.list() == ["default", "gig"]  # default: the bank save's autosave
    doc = json.loads(p.read_text())
    assert doc["schema"] == "hyperspace.project/1" and doc["name"] == "Gig"
    assert doc["modules"] == {"band": "Percussive", "view": "Mine"}
    assert doc["values"]["camera.zoom"] == 3.0 and doc["bank"][2]["name"] == "STROBE CAGE"
    assert doc["io"] == {}

    lib.project.new()
    assert lib.project.name == "untitled" and lib.project.path is None
    assert rig.view.zoom == 1.0 and rig.chain.gain == 1.0     # fresh state
    assert lib.current("band") is None and lib.bank.slots[2]["values"] == \
        json.loads((FACTORY / "projects" / "default.hyp.json").read_text())["bank"][2]["values"]

    missing = lib.project.load("Gig")
    assert missing == [] and lib.project.path == p
    assert rig.view.zoom == 3.0 and rig.chain.gain == 2.5
    assert lib.current("band") == "Percussive" and not lib.is_dirty("band")
    assert lib.bank.slots[2]["values"]["camera.zoom"] == 3.0 and lib.bank.active == -1
    # a module whose preset is gone is still "loaded", the values speak for it
    lib.delete("view", "Mine")
    lib.project.load(p)
    assert lib.current("view") == "Mine" and not lib.is_dirty("view")
    # saving now keeps an inline copy so the project stays whole elsewhere
    doc = json.loads(lib.project.save().read_text())
    assert doc["modules"]["view"]["name"] == "Mine" and "view.bright" in doc["modules"]["view"]["values"]


def test_project_unknown_ids_and_bank_seeding(rig, tmp_path):
    p = tmp_path / "projects" / "odd.hyp.json"
    p.write_text(json.dumps({"schema": "hyperspace.project/1", "name": "Odd",
                             "values": {"view.shape": 6, "warp.core": 1},
                             "bank": [{"name": "ONE", "values": {}}]}))
    assert rig.lib.project.load("odd") == ["warp.core"]
    assert rig.view.shape == 6
    slots = rig.lib.bank.slots
    assert slots[0]["name"] == "ONE" and slots[1]["name"] == "EMBER ORBIT"
    assert rig.lib.project.name == "Odd" and rig.lib.project.path == p


def test_user_default_project_opens_on_attach(tmp_path):
    r = make(tmp_path)
    r.reg["view.bright"].set_value(2.0)
    r.lib.load("band", "Tremolo Web")
    r.lib.project.save()
    r2 = make(tmp_path)
    assert r2.lib.project.path == tmp_path / "projects" / "default.hyp.json"
    assert r2.view.bright == 2.0 and r2.lib.current("band") == "Tremolo Web"


# ---------------------------------------------------------------- live editing

def test_editing_the_loaded_preset_reflects_in_the_app(rig, tmp_path):
    lib = rig.lib
    assert not lib.poll(now=1.0)                      # quiet tree
    path = lib.save_as("view", "Live")
    assert not lib.poll(now=2.0)                      # our own write is not an edit
    edit(path, lambda d: d["values"].__setitem__("view.bright", 3.0))
    assert lib.poll(now=3.0)
    assert rig.view.bright == 3.0 and "view/Live" in lib.status
    # a file for a preset that is not loaded changes nothing but the listing
    other = tmp_path / "view" / "other.json"
    other.write_text(json.dumps({"schema": "hyperspace.preset/1", "group": "view",
                                 "name": "Other", "values": {"view.bright": 0.1}}))
    touch(other)
    assert lib.poll(now=4.0)
    assert rig.view.bright == 3.0 and lib.list("view") == ["Live", "Other"]
    # a half-written save is reported and the last good state stays
    path.write_text("{")
    touch(path)
    assert not lib.poll(now=5.0)
    assert "live.json" in lib.error and rig.view.bright == 3.0
    edit(other, lambda d: d.__setitem__("name", "Renamed"))
    assert lib.poll(now=6.0)
    assert lib.list("view") == ["live", "Renamed"] and lib.error == ""   # still broken: by file


def test_editing_the_open_project_reloads_it(rig, tmp_path):
    lib = rig.lib
    p = lib.project.save("Set")
    lib.poll(now=1.0)
    edit(p, lambda d: (d["values"].__setitem__("view.shape", 8),
                       d["bank"][0].__setitem__("name", "RENAMED")))
    assert lib.poll(now=2.0)
    assert rig.view.shape == 8 and lib.bank.slots[0]["name"] == "RENAMED"

