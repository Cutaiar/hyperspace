"""The preset & project library: files, shadowing, dirty state, live edits.

Every test builds its library on tmp_path (or points HYPERSPACE_HOME at
one) — nothing here may touch ~/Hyperspace.
"""

import json
import os
from types import SimpleNamespace

import pytest
from conftest import (
    OWNER_KNOB,
    OWNER_PAD,
    OWNER_PRESETS,
    OWNER_ROW,
    OWNER_SHOWS,
    boot_home,
    old_shape_pads,
    opened_last,
    tree,
)

from hyperspace import config, library, params, placement, preset, routing
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.bands import BANDS
from hyperspace.control import SCENES, Control
from hyperspace.library import FACTORY, Library, LibraryError, legacy_slot, migrate_doc, slug
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Bindings as _Bindings
from hyperspace.routing import Router as _Router
from hyperspace.view import ViewState

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


def make(home, show: str | None = "house"):
    """Over a home that opened `show` last — the house moods these tests
    were written on (None: a fresh home, which opens the party show)."""
    if show:
        opened_last(home, show)
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, audio, lib.project)
    lib.attach(reg)
    presets = Presets(lib, reg, _Router(reg, _Bindings()))    # the bank's loader, as app.py builds it
    return SimpleNamespace(lib=lib, reg=reg, view=view, control=control, chain=chain,
                           presets=presets)


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
    # the legacy theme bank became user presets and a schema-2 show
    # naming them, `mine` (plan 13 WP2, plan 14 WP3); an empty legacy slot
    # stays empty
    assert (home / "projects" / "mine.hyp.json").is_file()
    assert not (home / "projects" / "default.hyp.json").exists()
    r = make(home, show="mine")
    assert r.lib.project.bank[:2] == [None, "MINE"] and r.lib.project.startup == "MINE"
    doc = json.loads((home / "presets" / "mine.json").read_text())
    assert doc["schema"] == "hyperspace.preset/2" and doc["routes"]   # the factory lanes
    # the slot's session ids (scene, band, master) are dropped: a preset never has them (D9)
    assert doc["values"] == {"view.shape": 4, **{f"view.plane.{n}": True for n in library.PLANES}}
    atk, gain = r.chain.params[0].atk, r.chain.gain
    r.lib.project.load_slot(1)
    assert r.view.shape == 4 and r.chain.params[0].atk == atk and r.chain.gain == gain
    # no `desk` key: loading it gives the factory preset layer, not a dark desk
    # (review of PR #65 — an explicit [] would blank every preset control)
    assert "desk" not in doc
    table = r.lib.presets.router.table
    assert [b.source for b in table.desk()] == [
        b.source for b in routing.factory_desk() if b.layer == "preset"]
    # second run: nothing to do, nothing said (migrate itself; ensure_home is memoised)
    assert library.migrate(home, cwd) == []
    library.ensure_home(home, cwd)
    assert capsys.readouterr().err == ""


def test_config_explicit_path_keeps_working(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[output]\nbg = 0.5\n")
    cfg = config.load(p)
    assert cfg["output"]["bg"] == 0.5 and cfg["midi"]["enabled"] is True
    assert cfg["midi"]["map"] == str(tmp_path / "midi_map.json")


# ---------------------------------------------------------------- files

def test_factory_presets_ship_in_the_package():
    assert (FACTORY / "projects" / "party.hyp.json").is_file()      # what a fresh home opens
    assert (FACTORY / "projects" / "house.hyp.json").is_file()      # the house moods
    assert not (FACTORY / "projects" / "default.hyp.json").exists()   # plan 14 WP3
    names = {json.loads(p.read_text())["name"] for p in (FACTORY / "band").glob("*.json")}
    assert names == set(SCENES)
    doc = json.loads((FACTORY / "band" / "balanced.json").read_text())
    assert doc["schema"] == "hyperspace.preset/1" and doc["group"] == "band"
    # the analyzer contract: a layout next to the flat band.{i}.* values
    assert [b["curve"] for b in doc["layout"]["bands"]] == ["rect"] * 6
    assert doc["layout"]["bands"][0]["f"] == pytest.approx((20 * 60) ** 0.5)
    assert doc["layout"]["bands"][0]["q"] == pytest.approx((20 * 60) ** 0.5 / 40)
    assert doc["values"]["band.1.atk"] == 0.015
    # plan 11 (A1): the layout carries the band names, so a load keeps them
    assert [b["name"] for b in doc["layout"]["bands"]] == [b.id for b in BANDS]


def test_slug():
    assert slug("Kick & Sizzle") == "kick-sizzle"
    assert slug("  Slow Bass / Fast Air ") == "slow-bass-fast-air"
    assert slug("***") == "untitled"


def test_macros_are_performance_state(rig, tmp_path):
    """Plan 13 WP1 / WP2: the macros are performance state. A preset
    carries them and a project (the session) does not; the module strips
    still list no `macro` group (a macro's meaning is its subscribers,
    which live in the preset). The live table keeps them too until plan
    13 WP5 (test_routing)."""
    lib, reg = rig.lib, rig.reg
    assert "macro" not in lib.groups() and "view" in lib.groups()
    m = reg["macro.2"]
    m.set_value(0.3)
    lib.project.save_slot(0)
    assert lib.read("presets", lib.project.bank[0])["values"]["macro.2"] == pytest.approx(0.3)
    m.set_value(0.7)
    assert lib.is_dirty("presets")                   # the loaded preset tracks it
    lib.project.load_slot(0)
    assert m.value == pytest.approx(0.3)             # the preset brought it back
    path = lib.project.save("Show")
    doc = json.loads(path.read_text())
    assert "macro.2" not in doc["session"] and "values" not in doc
    assert "macro" not in doc["modules"]
    m.set_value(0.1)
    assert not lib.project.is_dirty()                # not the session's


def test_a_project_keeps_the_session_apart(rig, tmp_path):
    """Plan 13 §2.2 / §4: a project file (schema 2) holds the session part
    as `session` and the bank as names; the performance is the preset's.
    is_dirty sees the session, the bank and the startup preset; a file
    that lacks a session id takes the loaded state, so it opens clean."""
    lib, reg = rig.lib, rig.reg
    reg["view.shape"].set(5)
    reg["master.gain"].set(2.0)
    path = lib.project.save("Split")
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.project/2" and "values" not in doc
    assert doc["session"] == reg.snapshot(part="session")
    assert "master.gain" in doc["session"] and "view.shape" not in doc["session"]
    # the file holds the F-keys' eight (plan 19 WP1: `bank_doc`), the show 24
    assert doc["bank"] == lib.project.bank[:8] == library.bank_doc(lib.project.bank)
    assert doc["startup"] == "BIG BLUE WAVE"
    assert not lib.project.is_dirty()
    reg["view.shape"].set(6)                         # a performance move: the preset's
    assert not lib.project.is_dirty()
    reg["master.gain"].set(1.0)                      # a session move dirties the project
    assert lib.project.is_dirty()
    lib.project.save()
    lib.project.startup = "EMBER ORBIT"              # …as does the startup combo
    assert lib.project.is_dirty()
    lib.project.save()
    short = {k: v for k, v in doc.items() if k != "session"}
    short["session"] = {"master.gain": 3.0}
    (tmp_path / "projects" / "short.hyp.json").write_text(json.dumps(short))
    lib.project.load("short")
    assert rig.chain.gain == 3.0 and "band.0.atk" in lib.project.session
    assert not lib.project.is_dirty()


def test_list_user_shadows_factory(rig, tmp_path):
    lib = rig.lib
    assert lib.list("band") == sorted(SCENES, key=str.lower)
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


def test_a_band_preset_saved_from_the_strip_carries_its_layout(rig, tmp_path):
    """Audit A2: save_as fills the group's `extra` from its hook, so an
    eight-band preset restores eight bands — names included — onto a
    six-band analyzer instead of six and two missing ids."""
    lib, reg, control, chain = rig.lib, rig.reg, rig.control, rig.chain
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    control.add_band()
    control.add_band()
    chain.set_band(6, name="HIGH")
    reg["band.7.atk"].set_value(0.333)
    assert chain.n == 8
    path = lib.save_as("band", "Eight")
    doc = json.loads(path.read_text())
    assert len(doc["layout"]["bands"]) == 8 and doc["layout"]["bands"][6]["name"] == "HIGH"
    assert "band.7.atk" in doc["values"]
    assert lib.overwrite("band") == path             # the save chip takes the same road
    assert len(json.loads(path.read_text())["layout"]["bands"]) == 8

    other = make(tmp_path)                            # a fresh six-band rig, same home
    other.lib.on_layout("band", other.control.apply_layout)
    assert other.chain.n == 6
    assert other.lib.load("band", "Eight") == []      # nothing missing
    assert other.chain.n == 8 and other.chain.band_names[6] == "HIGH"
    assert other.chain.params[7].atk == chain.params[7].atk
    assert other.lib.current("band") == "Eight" and not other.lib.is_dirty("band")


def test_a_projects_inline_band_copy_carries_the_layout(rig, tmp_path):
    """Code review of PR #44 (A2): every band document the library writes
    is built by Library.document, so a band preset that has no file when
    the project is saved is copied inline with its layout. (Applying a
    module's layout on project load is a separate, older gap: Project._apply
    never ran the layout hook; filed for plan 11's library sweep.)"""
    lib, control, chain = rig.lib, rig.control, rig.chain
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    control.add_band()
    chain.set_band(6, name="HIGH")
    lib.save_as("band", "Gone")
    (tmp_path / "band" / "gone.json").unlink()        # current, but no file anywhere
    lib._sync(tmp_path / "band" / "gone.json")
    assert lib.current("band") == "Gone" and lib.path_of("band", "Gone") is None
    lib.project.save("P")
    inline = json.loads((tmp_path / "projects" / "p.hyp.json").read_text())["modules"]["band"]
    assert inline["name"] == "Gone" and "schema" not in inline and "group" not in inline
    assert [b.get("name") for b in inline["layout"]["bands"]][6] == "HIGH"
    assert len(inline["layout"]["bands"]) == 7 and "band.6.atk" in inline["values"]


def test_delete_is_user_only(rig, tmp_path):
    """Audit L5: `rename` had no caller and went; delete stays user-only.
    Plan 19 WP4 brings a rename back with a caller (the preset list), for
    the presets' group only: a module preset is named by shows and scenes."""
    lib = rig.lib
    lib.save_as("camera", "Wide")
    assert lib.list("camera") == ["Wide"] and lib.current("camera") == "Wide"
    with pytest.raises(LibraryError, match="only a preset can be renamed"):
        lib.rename("camera", "Wide", "Tall")
    assert not lib.delete("band", "Percussive")             # factory
    assert not lib.delete("camera", "never was")
    assert lib.delete("camera", "Wide")
    assert lib.list("camera") == [] and lib.current("camera") is None


def test_a_group_registered_after_attach_has_a_default_too(rig):
    """Audit L6: the overlay's output.* registered after attach(), so reset
    and the dirty dot ignored them until a preset saved them. Now a group's
    fresh values are adopted the first time anyone asks about it."""
    lib, reg = rig.lib, rig.reg
    late = SimpleNamespace(alpha=1.0)
    reg.continuous("late.alpha", "Alpha", lambda: late.alpha,
                   lambda v: setattr(late, "alpha", v), lo=0.0, hi=1.0, group="late")
    assert not lib.is_dirty("late")
    reg["late.alpha"].set_value(0.25)
    assert lib.is_dirty("late")
    assert lib.reset("late") is None and late.alpha == 1.0 and not lib.is_dirty("late")
    reg["late.alpha"].set_value(0.5)
    lib.project.new()                                  # a fresh project: fresh values everywhere
    assert late.alpha == 1.0


def test_the_home_is_ensured_once_per_process(tmp_path, monkeypatch):
    """Audit L5: config.load and Library() both ensure the home; the
    working-directory migration scan runs once."""
    home = tmp_path / "once"
    calls = []
    real = library.migrate
    monkeypatch.setattr(library, "migrate", lambda root, cwd=None: calls.append(root) or real(root, cwd))
    library.ensure_home(home)
    library.ensure_home(home)
    Library(home)
    assert calls == [home]


def test_a_project_restores_a_modules_layout(rig, tmp_path):
    """Audit L8: a project saved on eight bands comes back with eight —
    `Project._apply` takes the same road a strip load does, layout first."""
    lib, control, chain = rig.lib, rig.control, rig.chain
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})      # six bands: the fresh layout
    control.add_band()
    control.add_band()
    chain.set_band(7, name="TOP")
    lib.save_as("band", "Eight")                         # by name in the library…
    p = lib.project.save("Wide")
    lib.load("band", "Balanced")
    assert chain.n == 6
    assert lib.project.load("Wide") == []
    assert chain.n == 8 and chain.band_names[7] == "TOP" and lib.current("band") == "Eight"
    assert not lib.is_dirty("band")
    # an edit saved with the project comes back as an edit — dirty against
    # "Eight" — and the band the layout made has its build value as fresh
    rig.reg["band.7.atk"].set_value(0.9)
    edited = chain.params[7].atk                         # as detented by the taper
    lib.project.save("Wide")
    lib.load("band", "Balanced")
    lib.project.load("Wide")
    assert chain.params[7].atk == edited and lib.is_dirty("band")
    assert lib.defaults("band")["band.7.atk"] != edited
    # a new project goes back to the layout the app started with
    lib.project.new()
    assert chain.n == 6 and lib.current("band") == "Balanced"   # the party show's scene
    # …and the module as an inline copy, when its file is gone
    lib.project.load("Wide")
    (tmp_path / "band" / "eight.json").unlink()
    lib._sync(tmp_path / "band" / "eight.json")
    lib.project.save("Wide")
    lib.load("band", "Balanced")
    assert chain.n == 6
    assert lib.project.load(p) == []
    assert chain.n == 8 and chain.band_names[7] == "TOP"


# --------------------------------------------------------- document kinds

def test_presets_are_the_librarys_one_document_kind(rig, tmp_path):
    """Audit L1, closed by plan 13 WP5: one preset system. The routing
    presets' kind is gone (was test_routing_presets_are_a_document_kind_of_
    the_library); what they were — legacy6, lfo-breathe, the hands-* — are
    presets, which list, shadow, load, save, dirty and delete through the
    library like any module's. A user's old bindings/ folder is no group."""
    from hyperspace.routing import Binding

    lib, router = rig.lib, rig.presets.router
    assert lib.kinds == ("presets",) and not hasattr(lib, "routing")
    (tmp_path / "bindings").mkdir()
    (tmp_path / "bindings" / "mine.json").write_text("{}")
    assert "bindings" not in lib.groups() and "presets" in lib.groups()
    names = lib.list("presets")
    assert {"legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play"} <= set(names)
    assert lib.is_factory("presets", "legacy6") and lib.current("presets") is None
    assert not lib.is_dirty("presets")                    # nothing loaded: never dirty
    rig.view.pattern_mod[0] = 0.4
    lib.load("presets", "legacy6")
    assert rig.view.pattern_mod[0] == 0.0                 # its bases land
    assert lib.current("presets") == "legacy6" and not lib.is_dirty("presets")
    assert len(router.table.routes()) == 12
    router.table.add(Binding("lane:2", "view.bright", "push", 0.3))
    assert lib.is_dirty("presets")
    path = lib.save_as("presets", "My Routes")
    assert path == tmp_path / "presets" / "my-routes.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.preset/2" and len(doc["routes"]) == 13
    assert lib.current("presets") == "My Routes" and not lib.is_dirty("presets")
    assert not lib.is_factory("presets", "My Routes")
    lib.load("presets", "hands-play")
    assert not router.table.routes_to("view.bright")[0].source.startswith("lane")
    lib.load("presets", "My Routes")
    assert [b.source for b in router.table.routes_to("view.bright")] == ["lane:2"]
    assert lib.delete("presets", "My Routes") and "My Routes" not in lib.list("presets")
    with pytest.raises(LibraryError):
        lib.load("presets", "no-such")
    # a shadow: a user file named like a factory one wins, and lifts on delete
    (tmp_path / "presets" / "legacy6.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/2", "name": "legacy6", "values": {}, "routes": [
            {"source": "lane:0", "target": "view.bright", "op": "push", "value": 0.1}]}))
    assert not lib.is_factory("presets", "legacy6")
    lib.load("presets", "legacy6")
    assert [b.target for b in router.table.routes()] == ["view.bright"]
    assert lib.delete("presets", "legacy6") and lib.is_factory("presets", "legacy6")


def test_a_bad_preset_is_reported_not_fatal(rig, tmp_path):
    """Was test_a_bad_routing_preset_is_reported_not_fatal: a preset of an
    unknown schema, or with a row that is no row, is refused with a
    LibraryError and the rest of the tree is fine."""
    lib = rig.lib
    d = tmp_path / "presets"
    d.mkdir()
    (d / "odd.json").write_text(json.dumps({"schema": "hyperspace.bindings/3", "name": "odd"}))
    with pytest.raises(LibraryError):
        lib.load("presets", "odd")
    (d / "worse.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/2", "name": "worse", "routes": [{"source": "lane:0"}]}))
    with pytest.raises(LibraryError):
        lib.load("presets", "worse")
    (d / "worst.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/2", "name": "worst", "routes": ["lane:0"]}))
    with pytest.raises(LibraryError):
        lib.load("presets", "worst")
    (d / "bare.json").write_text(json.dumps({"name": "bare", "values": {}}))    # no schema
    with pytest.raises(LibraryError):
        lib.load("presets", "bare")
    assert lib.list("band")                               # the rest of the tree is fine


def test_the_preset_kind_reaches_presets_at_call_time(rig):
    """Hot reload re-classes `Presets` in place; the kind's hooks must not
    hold the pre-reload bound methods (was the routing kind's test)."""
    lib = rig.lib
    seen = []
    rig.presets.signature = lambda: seen.append("sig") or ()
    lib.load("presets", "hands-play")
    assert seen == ["sig"]


def test_a_project_naming_the_old_routing_layer_is_ignored(rig, tmp_path):
    """A hand-edited project naming a `bindings` module (the routing
    presets' old group) loads, and names nothing current."""
    lib = rig.lib
    p = tmp_path / "projects" / "odd.hyp.json"
    p.write_text(json.dumps({"schema": "hyperspace.project/2", "name": "Odd",
                             "session": {}, "modules": {"bindings": "lfo-breathe"}}))
    assert lib.project.load("odd") == []
    assert lib.current("bindings") is None


def test_a_project_never_carries_the_loaded_preset(rig, tmp_path):
    """Audit L3, and plan 13 §2.2: `Project.io` is gone, and the loaded
    preset (routes and all) stays out of a project's modules — the bank
    names presets, the project holds the session."""
    lib = rig.lib
    lib.load("presets", "hands-play")
    doc = json.loads(lib.project.save("Set").read_text())
    assert "io" not in doc and "bindings" not in doc["modules"]
    assert "presets" not in doc["modules"]
    assert not hasattr(lib.project, "io")


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
    assert lib.project.name == "house" and lib.project.path is None   # the factory one
    lib.load("band", "Percussive")
    lib.save_as("view", "Mine")
    reg["camera.zoom"].set_value(3.0)
    reg["master.gain"].set(2.5)
    lib.project.save_slot(2)
    p = lib.project.save("Gig")
    assert p == tmp_path / "projects" / "gig.hyp.json"
    assert lib.project.list() == ["gig", "house", "party"]   # house, party: the factory ones
    doc = json.loads(p.read_text())
    assert doc["schema"] == "hyperspace.project/2" and doc["name"] == "Gig"
    # a performance group's label is the preset's, never the project's
    assert doc["modules"] == {"band": "Percussive"}
    assert doc["session"]["master.gain"] == 2.5 and "camera.zoom" not in doc["session"]
    assert doc["bank"][2] == "STROBE CAGE"
    assert lib.read("presets", "STROBE CAGE")["values"]["camera.zoom"] == 3.0   # the user's shadow
    assert "io" not in doc                                  # audit L3: never written, gone

    lib.project.new()
    assert lib.project.name == "untitled" and lib.project.path is None
    assert rig.chain.gain == 1.0                                     # a fresh session…
    assert lib.current("band") == "Balanced"                         # …the party show's scene,
    assert lib.project.bank[2] == "FIELD"                            # …its bank
    assert lib.current("presets") == "TUMBLE"                        # …and its first preset

    missing = lib.project.load("Gig")
    assert missing == [] and lib.project.path == p
    assert rig.chain.gain == 2.5
    assert lib.current("band") == "Percussive" and not lib.is_dirty("band")
    assert lib.project.active == 0                                   # the startup preset's slot
    # a module whose preset is gone is still "loaded", the values speak for it
    lib.save_as("band", "Mine")
    lib.project.save()
    lib.delete("band", "Mine")
    lib.project.load(p)
    assert lib.current("band") == "Mine" and not lib.is_dirty("band")
    # saving now keeps an inline copy so the project stays whole elsewhere
    doc = json.loads(lib.project.save().read_text())
    assert doc["modules"]["band"]["name"] == "Mine" and "band.0.atk" in doc["modules"]["band"]["values"]


def test_project_unknown_ids_and_a_short_bank(rig, tmp_path):
    p = tmp_path / "projects" / "odd.hyp.json"
    p.write_text(json.dumps({"schema": "hyperspace.project/2", "name": "Odd",
                             "session": {"master.gain": 2.0, "warp.core": 1},
                             "bank": ["ONE"]}))
    assert rig.lib.project.load("odd") == ["warp.core"]
    assert rig.chain.gain == 2.0
    # a short bank is padded with empty slots; nothing is seeded any more
    assert rig.lib.project.bank == ["ONE"] + [None] * (library.SLOTS - 1)
    assert rig.lib.project.name == "Odd" and rig.lib.project.path == p


def test_the_users_copy_of_the_last_show_opens_on_attach(tmp_path):
    r = make(tmp_path)
    r.reg["master.gain"].set(2.0)
    r.lib.load("band", "Tremolo Web")
    r.lib.project.save()                              # the factory house show: your copy
    r2 = make(tmp_path, show=None)
    assert r2.lib.project.path == tmp_path / "projects" / "house.hyp.json"
    assert r2.chain.gain == 2.0 and r2.lib.current("band") == "Tremolo Web"


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
    rig.view.shape = 3                                 # the performance, the preset's
    edit(p, lambda d: (d["session"].__setitem__("master.gain", 4.0),
                       d["bank"].__setitem__(0, "RENAMED")))
    assert lib.poll(now=2.0)
    assert rig.chain.gain == 4.0 and lib.project.bank[0] == "RENAMED"
    assert rig.view.shape == 3                         # an edit re-reads; no startup load


def test_a_band_presets_normalisation_switch_round_trips(rig):
    """Audit A10: `band.{i}.norm` is a persisted scene setting, never a
    performer's — saved with a band preset, restored by it, not ownable."""
    lib, reg, chain = rig.lib, rig.reg, rig.chain
    assert not reg["band.3.norm"].modulatable and reg["band.3.norm"].persist
    assert reg["band.sel.norm"].alias
    reg["band.3.norm"].set(1)
    assert chain.params[3].norm == 1
    path = lib.save_as("band", "Manual mid")
    assert json.loads(path.read_text())["values"]["band.3.norm"] == 1
    reg["band.3.norm"].set(0)
    assert lib.load("band", "Manual mid") == []
    assert chain.params[3].norm == 1



def test_factory_projects_are_listed_and_load_by_name(rig):
    """The load combo lists the factory projects (plan 12's `party`) beside
    the user's; opening one by name lands its bank without a user file,
    and its startup preset with it."""
    lib = rig.lib
    assert "party" in lib.project.list()
    assert lib.project.load("party") == []
    assert lib.project.name == "party" and lib.project.path is None
    assert lib.project.bank == ["TUMBLE", "FACES", "FIELD", "WAKE", "TRIP", "ACID", "MANDALA",
                                "NOITA", "TRACER"] + [None] * 15    # plan 19 WP1: slot 9
    assert lib.current("presets") == "TUMBLE" and lib.project.active == 0
    assert rig.view.shape == 10 and lib.current("band") == "Balanced"


# ------------------------------------------------ plan 15 WP1: the trash

def trash(home, group) -> list:
    d = home / library.TRASH / group
    return sorted(d.iterdir()) if d.is_dir() else []


def test_a_save_over_a_preset_keeps_the_old_file_in_the_trash(rig, tmp_path, monkeypatch,
                                                              capsys):
    """Every road that overwrites a user preset file copies it to
    `<home>/trash/<group>/` first — the strip's Save and as…, ⇧F — with
    the file's own name and a date; the copy is the old file, byte for
    byte. A copy that fails does not stop the save: the warning says so."""
    lib, reg = rig.lib, rig.reg
    path = lib.save_as("view", "Loud One")
    assert trash(tmp_path, "view") == []                     # a new file: nothing to keep
    first = path.read_bytes()
    reg["view.bright"].set_value(2.0)
    assert lib.overwrite("view") == path
    (kept,) = trash(tmp_path, "view")
    assert kept.read_bytes() == first and path.read_bytes() != first
    assert kept.name.startswith("loud-one.") and kept.suffix == ".json"
    stamp = kept.name[len("loud-one."):-len(".json")]
    assert len(stamp) == 15 and stamp[8] == "-" and stamp.replace("-", "").isdigit()
    # a preset (the document kind), by ⇧F: the bank's save
    lib.project.save_slot(2)
    name = lib.project.bank[2]
    mine = lib.path_of("presets", name)
    old = mine.read_bytes()
    assert trash(tmp_path, "presets") == []
    reg["view.shape"].set(7)
    lib.project.save_slot(2)
    (kept,) = trash(tmp_path, "presets")
    assert kept.read_bytes() == old and mine.read_bytes() != old
    # a factory preset saved over becomes a user shadow: nothing of yours was lost
    reg["band.0.atk"].set(0.7)
    lib.load("band", "Balanced")
    reg["band.0.atk"].set(0.7)
    lib.overwrite("band")
    assert trash(tmp_path, "band") == []
    # a copy that fails: the save goes on, and says the old file was not kept
    monkeypatch.setattr(library, "to_trash", lambda path, root: None)
    lib.warning = ""
    reg["view.bright"].set(3.0)
    assert lib.overwrite("view") == path
    assert json.loads(path.read_text())["values"]["view.bright"] == 3.0
    assert "could not be kept in the trash" in lib.warning
    assert len(trash(tmp_path, "view")) == 1


def test_a_delete_keeps_the_file_in_the_trash_or_does_not_delete(rig, tmp_path, monkeypatch,
                                                                 capsys):
    """A delete copies the file to the trash first; when the copy cannot
    be made the delete is refused (`LibraryError`, which the strip shows)
    and the file stays."""
    lib = rig.lib
    path = lib.save_as("camera", "Wide")
    body = path.read_bytes()
    assert lib.delete("camera", "Wide") and not path.exists()
    (kept,) = trash(tmp_path, "camera")
    assert kept.read_bytes() == body and lib.list("camera") == []
    assert not lib.delete("band", "Percussive") and trash(tmp_path, "band") == []   # factory
    # the copy fails (the trash is a file, say): nothing is deleted
    path = lib.save_as("camera", "Tall")
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / library.TRASH).write_text("not a folder")
    assert library.to_trash(path, blocked) is None
    assert "not copied to the trash" in capsys.readouterr().err
    monkeypatch.setattr(library, "to_trash", lambda path, root: None)
    with pytest.raises(LibraryError, match="not deleted"):
        lib.delete("camera", "Tall")
    assert path.exists() and lib.list("camera") == ["Tall"] and lib.current("camera") == "Tall"


def test_a_save_that_changes_nothing_trashes_nothing(rig, tmp_path):
    """Fork 6 (b): Save on an unchanged preset leaves the trash alone."""
    lib, reg = rig.lib, rig.reg
    lib.save_as("view", "Same")
    for _ in range(3):
        lib.overwrite("view")
        lib.save_as("view", "Same")
    assert trash(tmp_path, "view") == [] and not (tmp_path / library.TRASH).exists()
    rig.presets.save_as("LOOK")
    rig.presets.save_as("LOOK")
    assert not (tmp_path / library.TRASH).exists()
    reg["view.bright"].set_value(1.5)
    lib.overwrite("view")
    assert len(trash(tmp_path, "view")) == 1


def test_two_trashings_in_one_second_do_not_collide(rig, tmp_path, monkeypatch):
    """A name taken in the same second gets -2, -3, …; the copy is made
    exclusively, so nothing in the trash is ever overwritten."""
    monkeypatch.setattr(library.time, "strftime", lambda fmt, *a: "20261004-120000")
    src = tmp_path / "view" / "x.json"
    src.parent.mkdir(parents=True)
    made = []
    for k in range(4):
        src.write_text(f"version {k}")
        made.append(library.to_trash(src, tmp_path))
    assert [p.name for p in made] == ["x.20261004-120000.json", "x.20261004-120000-2.json",
                                      "x.20261004-120000-3.json", "x.20261004-120000-4.json"]
    assert [p.read_text() for p in made] == [f"version {k}" for k in range(4)]
    assert all(p.parent == tmp_path / library.TRASH / "view" for p in made)
    assert library.to_trash(tmp_path / "view" / "gone.json", tmp_path) is None   # no source


def test_the_trash_is_no_group_and_is_never_watched(rig, tmp_path):
    """`trash` is listed as no group, its files as no presets, and the file
    watch never sees them: editing or adding a trashed file re-applies
    nothing."""
    lib, reg = rig.lib, rig.reg
    path = lib.save_as("view", "Keeper")
    reg["view.bright"].set_value(2.0)
    lib.overwrite("view")
    (kept,) = trash(tmp_path, "view")
    assert library.TRASH not in lib.groups() and "view" in lib.groups()
    assert lib.list("view") == ["Keeper"] and lib.list(library.TRASH) == []
    assert lib.path_of("view", kept.stem) is None
    lib.poll(now=1.0)
    assert not any(library.TRASH in p.parts for p in lib._mtimes)
    edit(kept, lambda d: d["values"].update({"view.bright": 9.0}))
    (kept.parent / "keeper.json").write_text(kept.read_text())     # a look-alike in the trash
    assert lib.poll(now=2.0) is False
    assert reg["view.bright"].value == 2.0 and lib.current("view") == "Keeper"
    assert json.loads(path.read_text())["values"]["view.bright"] == 2.0


# ------------------------------------------- plan 15 WP4: save-as's name and slot

def test_next_name_counts_on_from_a_trailing_number():
    """`next_name(base, taken)`: the first "<stem> <n>" whose slug is free.
    A base ending in a number after a stem counts on from it; any other
    base is its own stem and starts at 2; no base is PRESET, from 1."""
    nn = library.next_name
    assert nn("TRIP", set()) == "TRIP 2"
    assert nn("TRIP 2", set()) == "TRIP 3"
    assert nn("TRIP 2", {"trip-3"}) == "TRIP 4"                # a gap is skipped…
    assert nn("TRIP", {"trip-2", "trip-3", "trip-5"}) == "TRIP 4"
    assert nn("TRIP 2", {"trip-2"}) == "TRIP 3"                # …and the base's own number never reused
    assert nn("2001", set()) == "2001 2"                       # a number alone is a name
    assert nn("2001 2", set()) == "2001 3"
    assert nn("BIG BLUE WAVE", set()) == "BIG BLUE WAVE 2"
    assert nn("BIG BLUE WAVE 9", set()) == "BIG BLUE WAVE 10"
    assert nn("TRIP2", set()) == "TRIP2 2"                     # no space: not a count
    assert nn("TRIP  7", set()) == "TRIP 8"                    # any whitespace before it is
    assert nn("ACID (2)", set()) == "ACID (2) 2"
    for none in (None, "", "   "):
        assert nn(none, set()) == "PRESET 1"
    assert nn(None, {"preset-1", "preset-2"}) == "PRESET 3"
    # `taken` is slugs: a name that differs only in case or punctuation is taken
    assert nn("Trip", {slug("TRIP 2")}) == "Trip 3"
    assert nn("TRIP", {"trip-2"}) != nn("TRIP", set())


def test_next_empty_reads_the_banks_own_length(tmp_path):
    """Plan 15 §1 row 13: the next empty slot is read off the bank's own
    list — neither `library.SLOTS` nor `routing.F_KEYS` — so plan 19's
    bank of twenty-four answers with no change to it, and a save-as and
    the slot menu's two calls reach its far slots: the party show's first
    empty slot is 10, and that is where the desk's save-as lands."""
    import inspect

    r = make(tmp_path, None)
    pr = r.lib.project
    assert len(pr.bank) == library.SLOTS == 24 and routing.F_KEYS == 8
    assert pr.next_empty() == 9                                 # the party show: slot 10
    r.reg["preset.save_new"].fire()
    name = r.lib.current("presets")
    assert pr.bank[9] == name and pr.active == 9
    assert r.lib.status == f"saved {name} → slot 10"
    assert pr.next_empty() == 10
    pr.bank[6] = pr.bank[2] = None
    assert pr.next_empty() == 2                                 # a hole in the F-keys first
    pr.bank = [f"P{k}" for k in range(24)]                      # full
    assert pr.next_empty() is None
    pr.bank[23] = None
    assert pr.next_empty() == 23
    pr.bank[17] = None
    assert pr.next_empty() == 17
    r.reg["preset.save_new"].fire()                             # into slot 18
    name = r.lib.current("presets")
    assert pr.bank[17] == name and pr.active == 17
    assert r.lib.status == f"saved {name} → slot 18"
    pr.put_slot(23, "WAKE")
    assert pr.bank[23] == "WAKE" and pr.next_empty() is None
    assert r.lib.status == "slot 24: WAKE"
    pr.clear_slot(20)
    assert pr.bank[20] is None and pr.next_empty() == 20
    for fn in (library.Project.next_empty, library.Project.save_new, library.Project.put_slot,
               library.Project.clear_slot, library.Project._set_slot):
        src = inspect.getsource(fn)
        assert "SLOTS" not in src, fn.__name__


# ------------------------------------------- plan 19 WP1: a bank of twenty-four

def bak8(show):
    """The backups `Project.write` has made of an eight-slot show file."""
    return sorted(show.parent.glob(f"{show.name}.bak-v{library.BANK8_BACKUP}*"))


def quit_(home):
    """What a quit writes into the home: where the windows were (app.py)."""
    placement.save(home, (60, 80, 960, 900), [(1100, 80, 1280, 720)],
                   [placement.Screen("test", 0, 0, 2560, 1440)])


def test_the_bank_is_twenty_four_and_the_f_keys_eight(tmp_path):
    """One size for the bank, one for the F-keys: `library.SLOTS` slots,
    the first `F_KEYS` of them a function key's — the number `routing` and
    `params` hold too (neither may import `library`)."""
    assert library.SLOTS == 24
    assert library.F_KEYS == 8 == routing.F_KEYS == params.F_KEYS
    assert len(make(tmp_path).lib.project.bank) == 24
    assert len(library.Project(SimpleNamespace()).bank) == 24
    assert [library.slot_key(k) for k in (0, 7, 8, 11, 23)] == ["F1", "F8", "slot 9", "slot 12",
                                                                 "slot 24"]


def test_a_bank_is_written_as_far_as_its_last_filled_slot():
    """`bank_doc`: trailing empty slots left off, never fewer than eight
    entries, and a hole before a far slot kept — so slot k is entry k."""
    doc = library.bank_doc
    assert doc([None] * 24) == [None] * 8
    assert doc(["A", None, "C"] + [None] * 21) == ["A", None, "C"] + [None] * 5
    assert doc(["A"] * 8 + [None] * 16) == ["A"] * 8
    assert doc(["A"] * 8 + [None, None, "K"] + [None] * 13) == ["A"] * 8 + [None, None, "K"]
    assert doc(["A"] * 24) == ["A"] * 24
    assert doc(["A", "B"]) == ["A", "B"] + [None] * 6       # a short list is padded to eight
    bank = ["A"] * 8 + [None] * 16
    assert doc(bank) is not bank and len(bank) == 24        # a copy: the bank is not cut


def test_the_owner_home_is_shaped_like_the_owners(owner_home):
    """The fixture every "on a copy" test stands on: two shows with
    eight-name banks, three presets whose desks hold the sixteen shape pads
    as today's writer wrote them (one with a re-aimed pad and a learned
    knob), a bindings.json with the owner's row, and the machine's files."""
    home = owner_home
    for show in OWNER_SHOWS:
        doc = json.loads((home / "projects" / f"{show}.hyp.json").read_text())
        assert doc["schema"] == "hyperspace.project/2" and len(doc["bank"]) == 8
        assert all(doc["bank"]), show
    mine = json.loads((home / "projects" / "mine.hyp.json").read_text())
    assert mine["bank"][:3] == list(OWNER_PRESETS) and mine["startup"] == "NIGHT ONE"
    assert (home / "last_show").read_text().strip() == "mine"
    pads = old_shape_pads()
    assert len(pads) == 16 and {p["target"] for p in pads} == {"view.shape"}
    for name in OWNER_PRESETS:
        doc = json.loads((home / "presets" / f"{slug(name)}.json").read_text())
        assert doc["schema"] == "hyperspace.preset/2" and doc["name"] == name
        by_source = {row["source"]: row for row in doc["desk"]}
        for pad in pads:
            if name == "NIGHT TWO" and pad["source"] == OWNER_PAD["source"]:
                assert by_source[pad["source"]] == OWNER_PAD        # the pad the owner re-aimed
            else:
                assert by_source[pad["source"]] == pad, (name, pad["source"])
    two = json.loads((home / "presets" / "night-two.json").read_text())
    knob = preset.desk_json([preset.device_knob(*OWNER_KNOB)])[0]
    assert knob in two["desk"]                                      # the knob the owner learned
    table = json.loads((home / "bindings.json").read_text())
    source, target = OWNER_ROW
    assert [b["target"] for b in table["bindings"] if b["source"] == source] == [target]
    assert not any(b.get("layer") == "preset" for b in table["bindings"])
    assert json.loads((home / "windows.json").read_text())["schema"] == "hyperspace.windows/1"
    assert (home / "stall.log").is_file() and (home / "weights" / "model.safetensors").is_file()
    assert len(list((home / "trash" / "presets").glob("night-one.*.json"))) == 1
    assert os.environ["HYPERSPACE_HOME"] == str(home)


def test_an_eight_slot_show_loads_and_is_not_rewritten(owner_home):
    """The owner's files, rule 1 (on a copy): a show with an eight-name
    bank opens, padded to twenty-four in memory, clean — and is not
    rewritten: after a launch, preset loads, home, opening the other show
    and a quit, every file in the home but `last_show` and `windows.json`
    (written as they always were) has the bytes and the mtime it had."""
    home = owner_home
    before = tree(home, but=("last_show", "windows.json"))
    r = boot_home(home)                                   # the launch: `mine`, opened last
    lib, pr = r.lib, r.lib.project
    assert pr.name == "mine" and pr.path == home / "projects" / "mine.hyp.json"
    assert len(pr.bank) == 24 and pr.bank[:3] == list(OWNER_PRESETS)
    assert all(pr.bank[:8]) and pr.bank[8:] == [None] * 16
    assert not pr.is_dirty() and lib.current("presets") == "NIGHT ONE" and pr.active == 0
    assert [r.reg["preset.select"].has(k) for k in (0, 7, 8, 23)] == [True, True, False, False]
    r.reg["preset.load.1"].fire()                          # F2
    assert lib.current("presets") == "NIGHT TWO" and pr.active == 1
    r.reg["preset.select"].set(4)                          # a pad of clip row 1
    r.reg["preset.home"].fire()
    assert lib.current("presets") == "NIGHT ONE" and not pr.is_dirty()
    pr.load_slot(12)                                       # an empty far slot: said, nothing else
    assert lib.warning == "slot 13: an empty slot"
    lib.poll()
    assert tree(home, but=("last_show", "windows.json")) == before
    pr.load("party")                                       # the user copy of the party show
    assert pr.path == home / "projects" / "party.hyp.json" and not pr.is_dirty()
    assert len(pr.bank) == 24 and pr.bank[8:] == [None] * 16      # no TRACER: the file is yours
    r.reg["preset.load.7"].fire()
    lib.poll()
    quit_(home)
    assert tree(home, but=("last_show", "windows.json")) == before
    assert not list(home.rglob("*.bak-*"))
    # and a second launch finds the same
    again = boot_home(home)
    assert again.lib.project.name == "party" and not again.lib.project.is_dirty()
    assert tree(home, but=("last_show", "windows.json")) == before


def test_loading_never_rewrites_a_preset_file(owner_home):
    """The owner's files (on a copy): every preset in the home and in the
    factory folder loads — from the bank, the strip and the file watch —
    and no preset file changes by a byte or a tick of its mtime."""
    home = owner_home
    def presets_of(root):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                for p in sorted((root / "presets").glob("*.json"))}
    before, factory = presets_of(home), presets_of(FACTORY)
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    for k in range(8):
        pr.load_slot(k)
        assert lib.current("presets") == pr.bank[k] and not lib.is_dirty("presets"), pr.bank[k]
    for name in lib.list("presets"):
        lib.load("presets", name)
        lib.poll()
    assert set(OWNER_PRESETS) <= set(lib.list("presets"))
    assert presets_of(home) == before and presets_of(FACTORY) == factory
    assert len(list((home / "trash" / "presets").iterdir())) == 1        # nothing new in the trash


def test_a_show_that_uses_only_the_first_eight_is_written_with_eight(owner_home):
    """The owner's files, rule 2 (on a copy): a show that uses only slots
    1–8 is written in the shape it has today — eight entries — whatever
    rewrites it: "starts on", a slot put or cleared, save. No backup is
    made: nothing about the file's shape changes."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    show = home / "projects" / "mine.hyp.json"
    was = json.loads(show.read_text())
    pr.startup = "NIGHT TWO"                               # "starts on" (ui_presets.set_starts_on)
    pr.write()
    doc = json.loads(show.read_text())
    assert doc == {**was, "startup": "NIGHT TWO"} and len(doc["bank"]) == 8
    assert list(doc) == list(was)                          # the same keys in the same order
    pr.put_slot(3, "NIGHT THREE")
    pr.clear_slot(6)
    pr.save()
    doc = json.loads(show.read_text())
    assert len(doc["bank"]) == 8 and doc["bank"][3] == "NIGHT THREE" and doc["bank"][6] is None
    r.reg["preset.save.6"].fire()                          # ⇧F7 into the hole
    assert len(json.loads(show.read_text())["bank"]) == 8 and pr.bank[6] == "PRESET 7"
    assert not list(home.rglob("*.bak-*")) and not pr.is_dirty() and pr.bank_error == ""
    assert lib.warning == ""
    # a far slot filled and cleared again: the file is back to eight entries
    pr.put_slot(15, "WAKE")
    assert len(json.loads(show.read_text())["bank"]) == 16
    pr.clear_slot(15)
    assert len(json.loads(show.read_text())["bank"]) == 8


def test_the_first_write_past_slot_eight_keeps_the_eight_slot_file(owner_home):
    """The owner's files, rule 3 (on a copy): the first write that makes a
    show file's bank longer than eight keeps the eight-slot file beside it
    first, `<file>.bak-v2-bank8`, never over a file already there; a second
    far write makes no second backup. **No backup, no write**: the slot is
    put back, the file is as it was, and the footer says why — from the
    slot menu, from ⇧click and from the desk's save-as."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    show = home / "projects" / "mine.hyp.json"
    old = show.read_bytes()
    pr.put_slot(11, "NIGHT TWO")
    assert pr.bank[11] == "NIGHT TWO" and lib.status == "slot 12: NIGHT TWO"
    assert [p.name for p in bak8(show)] == ["mine.hyp.json.bak-v2-bank8"]
    assert bak8(show)[0].read_bytes() == old               # the file from before any far slot
    doc = json.loads(show.read_text())
    assert doc["schema"] == "hyperspace.project/2"         # the schema stays (fork 2)
    assert len(doc["bank"]) == 12 and doc["bank"][8:] == [None, None, None, "NIGHT TWO"]
    assert doc["bank"][:8] == json.loads(old)["bank"] and not pr.is_dirty()
    # a second far write, a save and "starts on": the long bank is on disk, no second copy
    pr.put_slot(20, "WAKE")
    pr.startup = "WAKE"
    pr.write()
    pr.save()
    r.reg["preset.save_new"].fire()
    assert len(bak8(show)) == 1 and bak8(show)[0].read_bytes() == old
    assert len(json.loads(show.read_text())["bank"]) == 21
    # a launch reads the long bank back
    again = boot_home(home).lib.project
    assert again.bank == pr.bank and again.bank[20] == "WAKE" and not again.is_dirty()

    # ---- no backup, no write: the other show, its eight-slot file still on disk
    pr.load("party")
    show = home / "projects" / "party.hyp.json"
    old = show.read_bytes()
    mine = (home / "projects" / "mine.hyp.json.bak-v2-bank8")
    own = show.with_name(show.name + ".bak-v2-bank8")
    own.write_text("a copy the owner made by hand")        # a name already taken
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(routing, "backup", lambda path, schema: None)
        said = dict(lib.said)
        why = "party.hyp.json: not written — no backup of the eight-slot file could be made"
        pr.put_slot(9, "WAKE")                             # the slot menu
        assert pr.bank[9] is None and show.read_bytes() == old
        assert pr.bank_error == f"presets: {why}"
        assert lib.warning == f"slot 10: not changed — {why}"
        assert lib.said["warning"] == said.get("warning", 0) + 1     # the footer shows it
        assert not pr.is_dirty()
        pr.save_slot(12)                                   # ⇧click on a far slot
        assert pr.bank[12] is None and show.read_bytes() == old
        assert lib.current("presets") == "PRESET 13" and pr.active == -1   # in no slot: none lit
        assert "PRESET 13" in lib.list("presets")          # the preset is saved, and listed
        assert lib.warning == f"saved PRESET 13 — slot 13 not changed — {why}"
        assert r.reg["preset.save_new"].fire() is True     # the desk's save-as: F1–F8 are full
        name = lib.current("presets")
        assert name in lib.list("presets") and name not in pr.bank and pr.active == -1
        assert show.read_bytes() == old and not pr.is_dirty()
        assert lib.warning == (f"saved {name} — the show could not be written: it is in the "
                               f"preset list ({why})")
        # a write that keeps the bank at eight needs no backup, and goes through
        pr.put_slot(2, "NIGHT ONE")
        assert pr.bank[2] == "NIGHT ONE" and json.loads(show.read_text())["bank"][2] == "NIGHT ONE"
        assert pr.bank_error == ""
        # save as onto that eight-slot file from a show with a far slot: refused,
        # and the open show is still the one it was (review of PR #104)
        pr.load("mine")
        held, as_was = (pr.name, pr.path, pr.stem), show.read_bytes()
        with pytest.raises(LibraryError, match="no backup"):
            pr.save("party")
        assert (pr.name, pr.path, pr.stem) == held and show.read_bytes() == as_was
        pr.load("party")
    assert own.read_text() == "a copy the owner made by hand" and mine.is_file()
    assert [p for p in bak8(show) if p != own] == []       # nothing was copied, nothing written
    # the disk is back: the same call writes, the copy taken first under a free name
    old = show.read_bytes()
    pr.put_slot(9, "WAKE")
    assert pr.bank[9] == "WAKE" and len(json.loads(show.read_text())["bank"]) == 10
    made = [p for p in bak8(show) if p != own]
    assert len(made) == 1 and made[0].read_bytes() == old
    assert own.read_text() == "a copy the owner made by hand"      # never over an existing file
    # the same eight-slot file again — the far slot cleared, or a write that
    # failed after its backup and is tried again: it is kept already, no second copy
    pr.clear_slot(9)
    assert show.read_bytes() == old
    pr.put_slot(4, "NIGHT TWO")                            # …and a different eight-slot file
    copies = len(bak8(show))
    with pytest.MonkeyPatch.context() as mp:
        def full(*a, **k):
            raise LibraryError("disk full")
        mp.setattr(library, "_write_json", full)
        pr.put_slot(9, "WAKE")
        pr.put_slot(9, "WAKE")
    assert pr.bank[9] is None and len(bak8(show)) == copies + 1
    pr.put_slot(9, "WAKE")
    assert pr.bank[9] == "WAKE" and len(bak8(show)) == copies + 1


def test_save_as_lands_on_slot_nine_once_the_f_keys_are_full(owner_home):
    """`next_empty` reads the bank's own length, unchanged: on the owner's
    show, F1–F8 full, the desk's save-as lands in slot 9, then 10 — the
    eight-slot file kept once."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    show = home / "projects" / "mine.hyp.json"
    old = show.read_bytes()
    assert pr.next_empty() == 8
    assert r.reg["preset.save_new"].fire() is True
    assert pr.bank[8] == "NIGHT ONE 2" == lib.current("presets") and pr.active == 8
    assert lib.status == "saved NIGHT ONE 2 → slot 9"
    assert json.loads(show.read_text())["bank"] == [*json.loads(old)["bank"], "NIGHT ONE 2"]
    r.reg["preset.save_new"].fire()
    assert pr.bank[9] == "NIGHT ONE 3" and lib.status == "saved NIGHT ONE 3 → slot 10"
    assert len(bak8(show)) == 1 and bak8(show)[0].read_bytes() == old
    r.reg["preset.select"].set(8)                          # what a pad of clip row 4 will send
    assert lib.current("presets") == "NIGHT ONE 2" and pr.active == 8


def test_a_long_bank_read_by_eight_slots_shows_the_first_eight(owner_home):
    """Fork 2's known cost, stated: the schema stays `hyperspace.project/2`,
    so a build from before plan 19 opens a long bank by cutting it to
    eight (`_take`'s `[:SLOTS]` with SLOTS = 8). It shows slots 1–8
    correctly, and its next write of that show drops the far slots'
    names from the file. The presets' files are untouched, and
    `.bak-v2-bank8` is the file from before any far slot existed."""
    home = owner_home
    r = boot_home(home)
    pr = r.lib.project
    show = home / "projects" / "mine.hyp.json"
    eight = json.loads(show.read_text())["bank"]
    pr.put_slot(8, "WAKE")
    pr.put_slot(23, "TRIP")
    doc = json.loads(show.read_text())
    assert len(doc["bank"]) == 24 and doc["schema"] == "hyperspace.project/2"
    presets_before = {p.name: p.read_bytes() for p in (home / "presets").glob("*.json")}
    # the older build's reading of the file (library.py before plan 19, SLOTS = 8)
    old_slots = 8
    bank = [str(s) if isinstance(s, str) and s else None
            for s in list(doc.get("bank") or [])[:old_slots]]
    bank += [None] * (old_slots - len(bank))
    assert bank == eight == pr.bank[:8]                    # slots 1–8, right
    # …and what it writes back: eight entries, the far names gone from the file
    show.write_text(json.dumps({**doc, "bank": bank}, indent=1) + "\n")
    again = boot_home(home).lib.project
    assert again.bank == eight + [None] * 16 and not again.is_dirty()
    assert {p.name: p.read_bytes() for p in (home / "presets").glob("*.json")} == presets_before
    assert json.loads(bak8(show)[0].read_text())["bank"] == eight


# ------------------------------------------- plan 19 WP4: hide, rename, the trash

def test_hiding_a_factory_preset_takes_it_off_the_list_and_nothing_else(owner_home):
    """The owner's files (on a copy): × on a factory preset writes
    `<home>/hidden.json` and nothing else — its stem, never a display name
    — and takes it off `list()` only. `list(hidden=True)` keeps it; a slot
    and "starts on" that name it still load it; a user preset is never
    hidden by it. Unhide puts it back, again touching only `hidden.json`."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    assert pr.bank[3] == "WAKE" and lib.is_factory("presets", "WAKE")
    factory_wake = lib.path_of("presets", "WAKE")
    factory_bytes = factory_wake.read_bytes()
    before = tree(home)
    assert lib.hide("presets", "WAKE")
    assert lib.status == "hidden WAKE — F4 still loads it"
    assert tree(home, but=("hidden.json",)) == before          # nothing else written
    assert json.loads((home / "hidden.json").read_text()) == {
        "schema": "hyperspace.hidden/1", "presets": ["party-wake"]}
    assert "WAKE" not in lib.list("presets") and "WAKE" in lib.list("presets", hidden=True)
    assert lib.hidden() == {"party-wake"} and factory_wake.read_bytes() == factory_bytes
    # a slot and "starts on" still load it; a load is no edit of a file
    pr.load_slot(3)
    assert lib.current("presets") == "WAKE" and pr.active == 3
    pr.startup = "WAKE"                                        # (in memory: no write)
    lib.load("presets", "NIGHT ONE")
    pr.load_startup()
    assert lib.current("presets") == "WAKE"
    pr.startup = "NIGHT ONE"
    assert tree(home, but=("hidden.json",)) == before
    # a user preset is never hidden by it, and a second hide writes nothing
    assert not lib.hide("presets", "NIGHT TWO") and "NIGHT TWO" in lib.list("presets")
    hidden = tree(home)
    assert lib.hide("presets", "WAKE") and tree(home) == hidden
    # a new Library reads it back
    assert "WAKE" not in Library(home, period=0.0).list("presets")
    # unhide: back on the list, only hidden.json rewritten
    assert lib.unhide("presets", "WAKE") and "WAKE" in lib.list("presets")
    assert json.loads((home / "hidden.json").read_text())["presets"] == []
    assert tree(home, but=("hidden.json",)) == before
    assert not lib.unhide("presets", "WAKE")                   # not hidden: nothing to do


def test_a_user_file_that_shadows_a_hidden_factory_preset_shows_as_itself(tmp_path):
    lib = make(tmp_path).lib
    assert lib.hide("presets", "TRIP")
    stem = lib.path_of("presets", "TRIP").name                # party-trip.json, the factory's
    (tmp_path / "presets").mkdir(exist_ok=True)
    (tmp_path / "presets" / stem).write_text(
        (FACTORY / "presets" / stem).read_text())              # your copy under the same stem
    assert "TRIP" in lib.list("presets") and not lib.is_factory("presets", "TRIP")


def test_a_made_up_name_never_collides_with_a_hidden_preset(owner_home, tmp_path):
    """`Project.save_new` and `_fresh_name` ask the list with
    `hidden=True`: with TRACER loaded and a hidden factory preset called
    "TRACER 2" (its stem says nothing of the name), save-as makes
    "TRACER 3"; an empty slot's ⇧-save skips a hidden "PRESET 10"."""
    import shutil

    r = boot_home(owner_home)
    lib, pr = r.lib, r.lib.project
    factory = tmp_path / "factory"
    shutil.copytree(FACTORY, factory)
    for stem, name in (("party-tracer-two", "TRACER 2"), ("odd-one", "PRESET 10")):
        doc = json.loads((factory / "presets" / "party-tracer.json").read_text())
        (factory / "presets" / f"{stem}.json").write_text(preset.dumps({**doc, "name": name}))
    lib.factory = factory
    assert lib.hide("presets", "TRACER 2") and lib.hide("presets", "PRESET 10")
    assert "TRACER 2" not in lib.list("presets")
    lib.load("presets", "TRACER")
    assert lib.hidden() == {"party-tracer-two", "odd-one"}
    assert pr.save_new() and lib.current("presets") == "TRACER 3"
    assert lib.path_of("presets", "TRACER 2") == factory / "presets" / "party-tracer-two.json"
    pr.save_slot(9)                                            # an empty slot: PRESET 10…
    assert pr.bank[9] == "PRESET 10 (2)"
    assert lib.path_of("presets", "PRESET 10").parent == factory / "presets"


def test_an_unreadable_hidden_list_is_kept_before_it_is_replaced(owner_home, monkeypatch):
    """`hidden.json` that will not parse reads as nothing hidden, with a
    warning; the first rewrite keeps it beside itself
    (`hidden.json.bak-v0`); a backup that cannot be made means no
    rewrite — and nothing else in the home changes either way."""
    home = owner_home
    bad = b'{"schema": "hyperspace.hidden/1", "presets": [ "party-wake",'
    (home / "hidden.json").write_bytes(bad)
    r = boot_home(home)
    lib = r.lib
    assert lib.hidden() == frozenset() and "WAKE" in lib.list("presets")
    assert lib.warning.startswith("hidden.json:") and "nothing is hidden" in lib.warning
    before = tree(home)
    with monkeypatch.context() as m:
        m.setattr(routing, "backup", lambda path, schema: None)
        with pytest.raises(LibraryError, match="not rewritten"):
            lib.hide("presets", "WAKE")
    assert tree(home) == before and "WAKE" in lib.list("presets")
    assert lib.hide("presets", "WAKE")
    assert (home / "hidden.json.bak-v0").read_bytes() == bad
    assert json.loads((home / "hidden.json").read_text())["presets"] == ["party-wake"]
    assert tree(home, but=("hidden.json",)) == {k: v for k, v in before.items()
                                                if k != "hidden.json"}
    # the next write finds a good file: no second backup
    assert lib.hide("presets", "TRIP")
    assert sorted(p.name for p in home.glob("hidden.json*")) == ["hidden.json",
                                                                 "hidden.json.bak-v0"]


def _shows_naming(r, name: str) -> None:
    """The owner's two shows both name `name` on a slot and as "starts on",
    and `mine` (open, `name` loaded from F2) is clean."""
    pr = r.lib.project
    pr.load("party", startup=False)
    pr.put_slot(5, name)
    pr.startup = name
    pr.write()
    pr.load("mine", startup=False)
    pr.startup = name
    pr.write()
    pr.load_slot(1)
    assert r.lib.current("presets") == name and pr.active == 1 and not pr.is_dirty()


def _trashed(home, folder: str) -> list:
    d = home / "trash" / folder
    return sorted(d.iterdir()) if d.is_dir() else []


def test_rename_updates_every_show_and_keeps_each_old_file(owner_home):
    """The owner's files (on a copy): rename NIGHT TWO → SUNRISE. The new
    file is the old document with only its name changed; the old file is
    in `trash/presets/` byte for byte; `mine` (open) and the user copy of
    `party` name SUNRISE on their slots and as "starts on", each old show
    file in `trash/projects/` byte for byte; the open show's dot is clean
    and its light on the slot. A schema-1 show naming it is left alone, and
    so is a show whose copy cannot be made — both named in the warning.
    Factory shows are never written; nothing else in the home changes."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    _shows_naming(r, "NIGHT TWO")
    shows = home / "projects"
    old1 = {"schema": "hyperspace.project/1", "name": "old",
            "bank": [{"name": "NIGHT TWO", "view": {}}], "startup": "NIGHT TWO"}
    (shows / "old.hyp.json").write_text(json.dumps(old1))
    spare = json.loads((shows / "party.hyp.json").read_text())
    (shows / "spare.hyp.json").write_text(json.dumps({**spare, "name": "spare"}))
    (shows / "other.hyp.json").write_text(json.dumps({**spare, "name": "other",
                                                      "bank": ["WAKE"], "startup": None}))
    lib.poll()
    preset_before = (home / "presets" / "night-two.json").read_bytes()
    show_before = {s: (shows / f"{s}.hyp.json").read_bytes()
                   for s in ("mine", "party", "old", "spare", "other")}
    factory_before = {p.name: p.read_bytes() for p in (FACTORY / "projects").iterdir()}
    trash_before = {p.name for p in home.rglob("trash/**/*") if p.is_file()}
    before = tree(home)
    real = library.to_trash
    with pytest.MonkeyPatch.context() as m:
        m.setattr(library, "to_trash",
                  lambda p, root: None if p.name == "spare.hyp.json" else real(p, root))
        new = lib.rename("presets", "NIGHT TWO", "SUNRISE")
    assert new == home / "presets" / "sunrise.json"
    assert not (home / "presets" / "night-two.json").exists()
    doc, was = json.loads(new.read_text()), json.loads(preset_before)
    assert doc == {**was, "name": "SUNRISE"}
    (kept,) = [p for p in _trashed(home, "presets") if p.name.startswith("night-two.")]
    assert kept.read_bytes() == preset_before
    for s in ("mine", "party"):
        d = json.loads((shows / f"{s}.hyp.json").read_text())
        assert "SUNRISE" in d["bank"] and "NIGHT TWO" not in d["bank"], s
        assert d["startup"] == "SUNRISE", s
        (k,) = [p for p in _trashed(home, "projects") if p.name.startswith(f"{s}.hyp.")]
        assert k.read_bytes() == show_before[s] and k.name.endswith(".json")
    for s in ("old", "spare", "other"):                            # left as they were
        assert (shows / f"{s}.hyp.json").read_bytes() == show_before[s], s
    assert {p.name for p in _trashed(home, "projects")} == {
        p.name for p in _trashed(home, "projects") if p.name.startswith(("mine.", "party."))}
    assert lib.status == "renamed NIGHT TWO → SUNRISE (2 shows updated)"
    assert "spare (it could not be kept in the trash)" in lib.warning
    assert "old (a hyperspace.project/1 show" in lib.warning and "other" not in lib.warning
    # the open show, through its Project: the name on the slot, clean, the light on it
    assert pr.bank[1] == "SUNRISE" and pr.startup == "SUNRISE" and not pr.is_dirty()
    assert lib.current("presets") == "SUNRISE" and pr.active == 1
    assert "SUNRISE" in lib.list("presets") and "NIGHT TWO" not in lib.list("presets")
    # nothing else changed; the factory shows never
    changed = {"presets/night-two.json", "presets/sunrise.json", "projects/mine.hyp.json",
               "projects/party.hyp.json"}
    after = tree(home, but=("trash/",))
    assert {k: v for k, v in after.items() if k not in changed} == {
        k: v for k, v in before.items() if k not in changed and not k.startswith("trash/")}
    assert trash_before <= {p.name for p in home.rglob("trash/**/*") if p.is_file()}
    assert {p.name: p.read_bytes() for p in (FACTORY / "projects").iterdir()} == factory_before
    # the other show, opened: its slot has the new name and loads it
    pr.load("party")
    assert pr.bank[5] == "SUNRISE" and lib.current("presets") == "SUNRISE"


def test_rename_refuses_a_taken_name_and_a_factory_preset(owner_home):
    """Refused, nothing on disk changed: a factory preset ("save copy,
    then rename the copy"), an empty name, a name taken by a preset of
    yours, by a factory preset's name or its file stem, by a hidden one,
    or by another spelling of the same slug. A rename that only changes
    case or spacing keeps the file's stem: rewritten in place, its old
    text in the trash."""
    home = owner_home
    r = boot_home(home)
    lib = r.lib
    assert lib.hide("presets", "WAKE")
    before = tree(home)
    for old, new, why in (("TRIP", "MY TRIP", "factory preset: save copy, then rename the copy"),
                          ("NIGHT TWO", "   ", "needs a name"),
                          ("NIGHT TWO", "NIGHT ONE", "taken"),
                          ("NIGHT TWO", "night  one!", "taken"),
                          ("NIGHT TWO", "TRIP", "taken"),
                          ("NIGHT TWO", "party-trip", "taken"),
                          ("NIGHT TWO", "WAKE", "taken"),          # hidden, still taken
                          ("GONE", "X", "no preset")):
        with pytest.raises(LibraryError, match=why):
            lib.rename("presets", old, new)
        assert tree(home) == before, (old, new)
    assert lib.rename("presets", "NIGHT TWO", "NIGHT TWO") == home / "presets" / "night-two.json"
    assert tree(home) == before                                    # the same name: nothing
    old = (home / "presets" / "night-two.json").read_bytes()
    assert lib.rename("presets", "NIGHT TWO", "Night Two") == home / "presets" / "night-two.json"
    assert json.loads((home / "presets" / "night-two.json").read_text())["name"] == "Night Two"
    assert [p.read_bytes() for p in _trashed(home, "presets")
            if p.name.startswith("night-two.")] == [old]
    assert "Night Two" in lib.list("presets") and "NIGHT TWO" not in lib.list("presets")
    assert lib.project.bank[1] == "Night Two"


def test_a_rename_that_cannot_keep_the_old_file_changes_nothing(owner_home):
    """`to_trash` failing: the new file written first is removed again, the
    old one is where it was, no show is touched — and so for the in-place
    case: nothing is written over a file whose copy failed."""
    home = owner_home
    r = boot_home(home)
    lib = r.lib
    before = tree(home)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(library, "to_trash", lambda path, root: None)
        for new in ("SUNRISE", "night two"):
            with pytest.raises(LibraryError, match="could not be kept in the trash"):
                lib.rename("presets", "NIGHT TWO", new)
            assert tree(home) == before, new
    assert "NIGHT TWO" in lib.list("presets") and "SUNRISE" not in lib.list("presets")
    assert lib.project.bank[1] == "NIGHT TWO"


def test_renaming_the_loaded_preset_keeps_its_unsaved_edit(owner_home):
    """The loaded preset renamed: the name changes, the dot stays lit (the
    clean reference is the one it had), and save writes the new file."""
    home = owner_home
    r = boot_home(home)
    lib, reg = r.lib, r.reg
    lib.project.load_slot(1)
    reg["view.bright"].set(reg["view.bright"].value * 0.5 + 0.1)
    assert lib.is_dirty("presets")
    lib.rename("presets", "NIGHT TWO", "SUNRISE")
    assert lib.current("presets") == "SUNRISE" and lib.is_dirty("presets")
    assert lib.project.active == 1
    path = lib.overwrite("presets")
    assert path == home / "presets" / "sunrise.json" and not lib.is_dirty("presets")
    assert json.loads(path.read_text())["name"] == "SUNRISE"
    assert not (home / "presets" / "night-two.json").exists()


def test_a_deleted_preset_says_which_slots_still_name_it(owner_home):
    """× on your own preset is plan 15's delete, unchanged; new is what is
    said: which slots and "starts on" still name it. The slots are not
    cleared for the owner — a restore to the old name makes them work."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    show = (home / "projects" / "mine.hyp.json").read_bytes()
    assert lib.delete("presets", "NIGHT ONE")                 # F1 and "starts on"
    assert lib.warning == ("NIGHT ONE is in the trash — F1 and 'starts on' still name it; "
                           "restore it from the trash, or clear the slot")
    assert pr.bank[0] == "NIGHT ONE" and pr.startup == "NIGHT ONE"
    assert (home / "projects" / "mine.hyp.json").read_bytes() == show
    pr.load("party", startup=False)                          # a show that names it nowhere
    assert lib.delete("presets", "NIGHT THREE")
    assert lib.status == "NIGHT THREE is in the trash — the preset list's trash can restore it"
    # your copy of a factory preset: the factory one is back (the shadow rule)
    lib.load("presets", "TRIP")
    lib.overwrite("presets")
    assert not lib.is_factory("presets", "TRIP")
    assert lib.delete("presets", "TRIP") and lib.is_factory("presets", "TRIP")
    assert lib.status == "your TRIP is in the trash — the factory TRIP is back"


def test_the_watcher_never_resurrects_or_reloads(owner_home):
    """Every file × , rename, restore and empty write or remove is synced
    as the library's own (`_sync`): the next `poll()` sees no edit — it
    applies nothing, recreates nothing — and `current` is right after each."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    loads = []
    real = lib.load
    lib.load = lambda *a, **k: (loads.append(a), real(*a, **k))[1]
    clock = [10_000.0]

    def poll() -> bool:
        clock[0] += 10
        return lib.poll(clock[0])

    pr.load_slot(1)
    assert lib.current("presets") == "NIGHT TWO"
    loads.clear()
    lib.rename("presets", "NIGHT TWO", "SUNRISE")
    assert not poll() and lib.current("presets") == "SUNRISE"
    assert not (home / "presets" / "night-two.json").exists()
    lib.delete("presets", "SUNRISE")
    assert not poll() and lib.current("presets") is None
    assert not (home / "presets" / "sunrise.json").exists()
    (item,) = [t for t in lib.trash() if t.name == "SUNRISE"]
    lib.restore_trash(item)
    assert not poll() and lib.current("presets") is None       # a restore loads nothing
    lib.hide("presets", "WAKE")
    lib.empty_trash()
    assert not poll()
    assert loads == [] and lib.list("presets").count("SUNRISE") == 1
    assert "NIGHT TWO" not in lib.list("presets", hidden=True)


def test_restore_never_overwrites(owner_home):
    """The owner's files (on a copy): a restore creates its target
    exclusively. A free stem comes back as it was, byte for byte; a taken
    stem (NIGHT ONE: the copy the home already had in its trash) and a
    taken name (NIGHT THREE, whose name another file now has) each come
    back under the next free name, written inside, and say so. The trash
    copy goes only after the write: a write that fails leaves it. A
    restored show is listed, not opened. Nothing else changes."""
    home = owner_home
    r = boot_home(home)
    lib, pr = r.lib, r.lib.project
    night_one = (home / "presets" / "night-one.json").read_bytes()
    # a taken stem
    (item,) = [t for t in lib.trash() if t.name == "NIGHT ONE"]
    assert item.group == "presets" and item.when
    before = tree(home, but=("trash/",))
    assert lib.restore_trash(item) == "NIGHT ONE 2"
    assert lib.status == "restored as NIGHT ONE 2 — NIGHT ONE is taken"
    assert not item.path.exists()
    assert json.loads((home / "presets" / "night-one-2.json").read_text())["name"] == "NIGHT ONE 2"
    assert (home / "presets" / "night-one.json").read_bytes() == night_one
    assert tree(home, but=("trash/", "presets/night-one-2.json")) == before
    # a free stem: back as it was, and the slot that named it loads it again
    three = (home / "presets" / "night-three.json").read_bytes()
    lib.delete("presets", "NIGHT THREE")
    (item,) = [t for t in lib.trash() if t.name == "NIGHT THREE"]
    assert lib.restore_trash(item) == "NIGHT THREE" and lib.status == "restored NIGHT THREE"
    assert (home / "presets" / "night-three.json").read_bytes() == three
    pr.load_slot(2)
    assert lib.current("presets") == "NIGHT THREE"
    # a taken name: another file of yours now carries it
    lib.delete("presets", "NIGHT THREE")
    other = home / "presets" / "elsewhere.json"
    other.write_text(preset.dumps({**json.loads(three), "name": "NIGHT THREE"}))
    (item,) = [t for t in lib.trash() if t.name == "NIGHT THREE"]
    assert lib.restore_trash(item) == "NIGHT THREE 2"
    assert json.loads((home / "presets" / "night-three-2.json").read_text())["name"] == \
        "NIGHT THREE 2"
    assert json.loads(other.read_text())["name"] == "NIGHT THREE"
    # a write that fails: the trash copy stays
    lib.delete("presets", "NIGHT TWO")
    (item,) = [t for t in lib.trash() if t.name == "NIGHT TWO"]
    os.chmod(home / "presets", 0o555)
    try:
        with pytest.raises(LibraryError, match="not restored"):
            lib.restore_trash(item)
    finally:
        os.chmod(home / "presets", 0o755)
    assert item.path.exists() and not (home / "presets" / "night-two.json").exists()
    assert lib.restore_trash(item) == "NIGHT TWO" and not item.path.exists()
    # a show: the copy a rename kept, under the next free name; not opened
    lib.rename("presets", "NIGHT TWO", "SUNRISE")
    (item,) = [t for t in lib.trash() if t.group == "projects" and t.name == "mine"]
    assert lib.restore_trash(item) == "mine 2" and lib.status == "restored as show mine 2 — " \
        "mine is taken"
    shown = json.loads((home / "projects" / "mine-2.hyp.json").read_text())
    assert shown["name"] == "mine 2" and "NIGHT TWO" in shown["bank"]
    assert "mine-2" in pr.list() and pr.name == "mine"
    # not in the trash: refused
    with pytest.raises(LibraryError, match="not in the trash"):
        lib.restore_trash(library.Trashed(home / "presets" / "sunrise.json", "presets",
                                          "SUNRISE", ""))
    assert (home / "presets" / "sunrise.json").exists()


def test_empty_trash_removes_only_the_trash(owner_home, tmp_path):
    """The owner's files (on a copy): empty removes exactly the files
    `trash()` lists and the folders left empty, and nothing outside
    `<home>/trash/`: a symlink in the trash pointing out, a symlinked
    folder, and a path with `..` are refused and left, and said."""
    home = owner_home
    r = boot_home(home)
    lib = r.lib
    lib.delete("presets", "NIGHT THREE")
    lib.rename("presets", "NIGHT TWO", "SUNRISE")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.json").write_text("{}")
    (outside / "dir").mkdir()
    (outside / "dir" / "also.20261004-010102.json").write_text("{}")
    (home / "trash" / "presets" / "evil.20261004-010101.json").symlink_to(outside / "keep.json")
    (home / "trash" / "fx").symlink_to(outside / "dir", target_is_directory=True)
    listed = lib.trash()
    real = [t.path for t in listed if not t.path.is_symlink() and t.path.parent.name != "fx"]
    assert len(real) == 4                       # the home's own, NIGHT THREE, NIGHT TWO, mine
    assert listed == sorted(listed, key=lambda t: (library._order(t.path), t.path.name),
                            reverse=True)                     # newest first
    before = tree(home, but=("trash/",))
    with pytest.MonkeyPatch.context() as m:
        sneaky = library.Trashed(home / "trash" / "presets" / ".." / ".." / "presets" /
                                 "night-one.json", "presets", "NIGHT ONE", "")
        m.setattr(lib, "trash", lambda: [*listed, sneaky])
        assert lib.empty_trash() == 4
    assert not any(p.exists() for p in real)
    assert "evil.20261004-010101.json" in lib.warning and "night-one.json" in lib.warning
    assert "also.20261004-010102.json" in lib.warning
    assert (outside / "keep.json").read_text() == "{}"
    assert (outside / "dir" / "also.20261004-010102.json").exists()
    assert (home / "presets" / "night-one.json").exists()
    assert tree(home, but=("trash/",)) == before
    assert not (home / "trash" / "projects").exists()           # emptied, removed
    assert (home / "trash" / "presets").is_dir()                # the symlink is still in it
    assert sorted(p.name for p in (home / "trash").iterdir()) == ["fx", "presets"]


def test_the_trash_lists_only_what_it_kept(owner_home):
    """Review of PR #117: a Finder `.DS_Store` (or any file `to_trash` did
    not write) in a trash folder is not listed, not restored and not
    emptied — a restore would have made it a preset."""
    home = owner_home
    lib = boot_home(home).lib
    junk = [home / "trash" / "presets" / ".DS_Store", home / "trash" / "presets" / "notes.txt"]
    for p in junk:
        p.write_bytes(b"\x00\x01Bud1")
    assert [t.path.name.split(".")[0] for t in lib.trash()] == ["night-one"]
    with pytest.raises(LibraryError, match="not a file the trash kept"):
        lib.restore_trash(library.Trashed(junk[0], "presets", "", ""))
    assert ".DS_Store" not in lib.list("presets", hidden=True)
    assert lib.empty_trash() == 1 and all(p.exists() for p in junk)


def test_deleting_your_copy_of_a_hidden_factory_preset_says_it_is_hidden(owner_home):
    """Review of PR #117: × on your ACID while the factory ACID is hidden
    says the factory one is hidden, not that it is back."""
    lib = boot_home(owner_home).lib
    assert lib.hide("presets", "ACID")
    lib.load("presets", "ACID")
    lib.overwrite("presets")                                   # your copy, acid.json
    assert "ACID" in lib.list("presets") and not lib.is_factory("presets", "ACID")
    assert lib.delete("presets", "ACID")
    assert lib.status == ("your ACID is in the trash — the factory ACID is hidden: show "
                          "hidden in the list brings it back")
    assert "ACID" not in lib.list("presets") and lib.is_factory("presets", "ACID")
