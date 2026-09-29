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


def make(home):
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
    # the legacy theme bank became user presets and a schema-2 default
    # project naming them (plan 13 WP2); an empty legacy slot stays empty
    r = make(home)
    assert r.lib.project.bank[:2] == [None, "MINE"] and r.lib.project.startup == "MINE"
    doc = json.loads((home / "presets" / "mine.json").read_text())
    assert doc["schema"] == "hyperspace.preset/2" and doc["routes"]   # the factory lanes
    # the slot's session ids (scene, band, master) are dropped: a preset never has them (D9)
    assert doc["values"] == {"view.shape": 4, **{f"view.plane.{n}": True for n in library.PLANES}}
    atk, gain = r.chain.params[0].atk, r.chain.gain
    r.lib.project.load_slot(1)
    assert r.view.shape == 4 and r.chain.params[0].atk == atk and r.chain.gain == gain
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
    assert (FACTORY / "projects" / "default.hyp.json").is_file()
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
    assert doc["bank"] == lib.project.bank and doc["startup"] == "BIG BLUE WAVE"
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
    """Audit L5: `rename` had no caller and is gone; delete stays user-only."""
    lib = rig.lib
    lib.save_as("camera", "Wide")
    assert lib.list("camera") == ["Wide"] and lib.current("camera") == "Wide"
    assert not hasattr(lib, "rename")
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
    assert chain.n == 6 and lib.current("band") is None
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

def _routed(rig, tmp_path):
    from hyperspace import routing
    from hyperspace.routing import Bindings, Router

    router = Router(rig.reg, Bindings.factory(path=routing.bindings_path(tmp_path)))
    rig.lib.routing(router)
    return router


def test_routing_presets_are_a_document_kind_of_the_library(rig, tmp_path):
    """Audit L1: one preset system. The routing presets list, shadow, load,
    save, dirty and delete through the library like any module's, while
    the router applies and produces the documents."""
    from hyperspace.routing import SCHEMA, Binding

    lib = rig.lib
    router = _routed(rig, tmp_path)
    assert "bindings" in lib.kinds and "bindings" in lib.groups()
    assert lib.list("bindings") == ["default", "hands-fx", "hands-pinch", "hands-play",
                                    "legacy6", "lfo-breathe", "party-faces", "party-field", "party-trip", "party-tumble", "party-wake"]
    assert lib.is_factory("bindings", "legacy6") and lib.current("bindings") is None
    assert not lib.is_dirty("bindings")                  # nothing loaded: never dirty
    rig.view.pattern_mod[0] = 0.4
    assert lib.load("bindings", "legacy6") == []
    assert rig.view.pattern_mod[0] == 0.0                 # its bases land
    assert lib.current("bindings") == "legacy6" and not lib.is_dirty("bindings")
    assert len(router.table.routes()) == 12
    router.table.add(Binding("lane:2", "view.bright", "push", 0.3))
    assert lib.is_dirty("bindings")
    path = lib.save_as("bindings", "My Routes")
    assert path == tmp_path / "bindings" / "my-routes.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == SCHEMA and doc["name"] == "My Routes" and len(doc["bindings"]) == 13
    assert lib.current("bindings") == "My Routes" and not lib.is_dirty("bindings")
    assert "My Routes" in lib.list("bindings") and not lib.is_factory("bindings", "My Routes")
    assert lib.next("bindings") == "party-faces"          # the next by name order
    mine = lambda: [b for b in router.table.routes_to("view.bright") if b.source == "lane:2"]
    assert not mine()                                     # the user's row went with the load
    assert lib.load("bindings", "My Routes") == [] and mine()
    assert lib.reset("bindings") == "default" and lib.current("bindings") == "default"
    assert lib.delete("bindings", "My Routes") and "My Routes" not in lib.list("bindings")
    with pytest.raises(LibraryError):
        lib.load("bindings", "no-such")
    # a shadow: a user file named like a factory one wins, and lifts on delete
    (tmp_path / "bindings").mkdir(exist_ok=True)
    (tmp_path / "bindings" / "legacy6.json").write_text(json.dumps(
        {"schema": SCHEMA, "bindings": [{"source": "lane:0", "target": "view.bright",
                                          "op": "push", "value": 0.1}]}))
    assert not lib.is_factory("bindings", "legacy6")
    lib.load("bindings", "legacy6")
    assert [b.target for b in router.table.routes()] == ["view.bright"]
    assert lib.delete("bindings", "legacy6") and lib.is_factory("bindings", "legacy6")


def test_a_routing_preset_edited_on_disk_is_re_applied(rig, tmp_path):
    lib = rig.lib
    router = _routed(rig, tmp_path)
    lib.load("bindings", "legacy6")
    path = lib.save_as("bindings", "Live")
    assert not lib.poll(now=1.0)
    edit(path, lambda d: d["bindings"].__setitem__(0, {"source": "lane:5", "target": "view.bright",
                                                        "op": "push", "value": 0.7}))
    assert lib.poll(now=2.0)
    assert router.table.routes_to("view.bright")[0].value == 0.7 and "bindings/Live" in lib.status
    assert not lib.is_dirty("bindings")


def test_a_bad_routing_preset_is_reported_not_fatal(rig, tmp_path):
    lib = rig.lib
    _routed(rig, tmp_path)
    (tmp_path / "bindings").mkdir()
    (tmp_path / "bindings" / "odd.json").write_text(json.dumps({"schema": "hyperspace.bindings/9"}))
    with pytest.raises(LibraryError):
        lib.load("bindings", "odd")
    (tmp_path / "bindings" / "worse.json").write_text(json.dumps(
        {"schema": "hyperspace.bindings/2", "bindings": [{"source": "lane:0"}]}))
    with pytest.raises(LibraryError):
        lib.load("bindings", "worse")
    (tmp_path / "bindings" / "worst.json").write_text(json.dumps(
        {"schema": "hyperspace.bindings/2", "bindings": ["lane:0"]}))     # a row that is no dict
    with pytest.raises(LibraryError):
        lib.load("bindings", "worst")
    assert lib.list("band")                               # the rest of the tree is fine
    # a schema-1 user file is rewritten once; one that will not take the
    # rewrite is reported rather than migrated and announced on every load
    old = tmp_path / "bindings" / "old.json"
    old.write_text(json.dumps({"bindings": [{"source": "lane:0", "target": "view.bright",
                                              "op": "mod", "value": 0.2}]}))
    old.chmod(0o444)
    try:
        with pytest.raises(LibraryError):
            lib.load("bindings", "old")
    finally:
        old.chmod(0o644)
    assert lib.load("bindings", "old") == []
    assert json.loads(old.read_text())["schema"] == "hyperspace.bindings/3"
    # a user's schema-2 routing preset still loads (plan 13 WP3: the kind
    # reads schemas 1–3), its macro scale moved to a depth subscriber
    v2 = tmp_path / "bindings" / "v2.json"
    v2.write_text(json.dumps({"schema": "hyperspace.bindings/2", "bindings": [
        {"source": "lfo:1", "target": "fx.mix", "op": "push", "value": 0.3,
         "scale": "macro.1"}]}))
    assert lib.load("bindings", "v2") == []
    doc = json.loads(v2.read_text())
    assert doc["schema"] == "hyperspace.bindings/3" and "scale" not in doc["bindings"][0]
    assert doc["macros"]["macro.1"]["subs"][0]["depth"] == {"source": "lfo:1",
                                                            "target": "fx.mix"}
    assert (tmp_path / "bindings" / "v2.json.bak-v2").exists()
    # a routing preset saved from the strip keeps one row per line, like the factory files
    path = lib.save_as("bindings", "Rows")
    lines = path.read_text().splitlines()
    assert sum(line.startswith("  {") for line in lines) == len(json.loads(path.read_text())["bindings"])
    assert json.loads(path.read_text())["name"] == "Rows"


def test_the_routing_kind_reaches_the_router_at_call_time(rig, tmp_path):
    """Hot reload re-classes the router in place; the kind's hooks must not
    hold the pre-reload bound methods."""
    lib = rig.lib
    router = _routed(rig, tmp_path)
    seen = []
    router.signature = lambda: seen.append("sig") or []
    lib.load("bindings", "default")
    assert seen == ["sig"]


def test_a_project_naming_the_routing_layer_is_ignored_before_and_after_the_kind(rig, tmp_path):
    """app.py attaches the library before it registers the routing kind, so
    a project file naming a `bindings` module (hand-edited) must be skipped
    by name, not by registration."""
    lib = rig.lib
    p = tmp_path / "projects" / "odd.hyp.json"
    p.write_text(json.dumps({"schema": "hyperspace.project/2", "name": "Odd",
                             "session": {}, "modules": {"bindings": "lfo-breathe"}}))
    assert lib.project.load("odd") == []
    assert lib.current("bindings") is None
    _routed(rig, tmp_path)
    assert lib.current("bindings") is None and not lib.is_dirty("bindings")


def test_a_project_never_carries_the_routing_layer(rig, tmp_path):
    """Audit L3: `Project.io` is gone and the routing presets stay out of a
    project's modules — the live table is one file for the rig."""
    lib = rig.lib
    _routed(rig, tmp_path)
    lib.load("bindings", "hands-play")
    doc = json.loads(lib.project.save("Set").read_text())
    assert "io" not in doc and "bindings" not in doc["modules"]
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
    assert lib.project.name == "default" and lib.project.path is None   # the factory one
    lib.load("band", "Percussive")
    lib.save_as("view", "Mine")
    reg["camera.zoom"].set_value(3.0)
    reg["master.gain"].set(2.5)
    lib.project.save_slot(2)
    p = lib.project.save("Gig")
    assert p == tmp_path / "projects" / "gig.hyp.json"
    assert lib.project.list() == ["default", "gig", "party"]   # party: the factory one
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
    assert rig.chain.gain == 1.0 and lib.current("band") is None    # a fresh session…
    assert lib.project.bank[2] == "STROBE CAGE"                      # …the factory bank
    assert lib.current("presets") == "BIG BLUE WAVE"                 # …and its startup preset

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


def test_user_default_project_opens_on_attach(tmp_path):
    r = make(tmp_path)
    r.reg["master.gain"].set(2.0)
    r.lib.load("band", "Tremolo Web")
    r.lib.project.save()
    r2 = make(tmp_path)
    assert r2.lib.project.path == tmp_path / "projects" / "default.hyp.json"
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
    assert lib.project.bank == ["TUMBLE", "FACES", "FIELD", "WAKE", "TRIP", None, None, None]
    assert lib.current("presets") == "TUMBLE" and lib.project.active == 0
    assert rig.view.shape == 10 and lib.current("band") == "Balanced"
