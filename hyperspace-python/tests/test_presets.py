"""Plan 13 WP2 — the preset (``hyperspace.preset/2``), the project's bank of
preset names (``hyperspace.project/2``), the F-keys and the startup preset.

Every rig is built the way app.main builds it — Library, registry, attach,
the Router over the home's bindings.json, the routing kind, `Presets`, the
startup preset — on a tmp_path home, never ~/Hyperspace. The bank tests
that were tests/test_themes.py (the inline theme bank) are folded in here
as the bank of names.
"""

import json
from types import SimpleNamespace

import pytest

from hyperspace import lfo, preset, routing, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.library import FACTORY, SLOTS, Library, LibraryError
from hyperspace.lookback import DreamState
from hyperspace.params import PERFORMANCE_GROUPS, build_registry, part_of
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Bindings, Router, bindings_path
from hyperspace.view import ViewState


def boot(home):
    """The app's construction order (app.main), headless."""
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, audio, lib.project, dream=DreamState(), fx=FxState())
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    lib.on_load("band", control.scene_loaded)
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    lib.attach(reg)
    router = Router(reg, Bindings.load(bindings_path(home), legacy_midi=None))
    lib.routing(router)
    presets = Presets(lib, reg, router)
    lib.project.load_startup()
    return SimpleNamespace(lib=lib, reg=reg, view=view, control=control, chain=chain,
                           router=router, presets=presets, clock=clock, home=home)


@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path)


def put(home, name, **doc):
    """A user preset file, the rest of the shape filled in."""
    body = {"schema": preset.SCHEMA, "name": name, "values": {}, "routes": [],
            "desk": [], "macros": {}, "modules": {}, **doc}
    path = home / "presets" / f"{name.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))
    return path


def expected(lib, values):
    """Every performance param: the file's value, else its group default."""
    out = {}
    for g in PERFORMANCE_GROUPS:
        out.update(lib.resolved(g, {k: v for k, v in values.items()
                                    if lib.reg[k].group == g}))
    return out


# ---------------------------------------------------------------- a load

def test_a_preset_load_lands_every_base_and_replaces_every_route(rig):
    """D2: every performance param lands — the file's value, or its group
    default — and every performer row is the file's; the input rows stay."""
    lib, reg, table = rig.lib, rig.reg, rig.router.table
    reg["view.bright"].set(3.3)                         # a view base off default
    reg["fx.kaleido.on"].set(not reg["fx.kaleido.on"].value)   # an fx toggle
    reg["dream.decay"].set(0.5)                         # a dream value
    table.add(Binding("hand:7", "view.speed", "push", 0.3))    # a hand route
    keys = [b.to_json() for b in table.bindings if b.op not in routing.MOD_OPS]
    values = {"view.shape": 4, "fx.on": True, "lfo.1.depth": 0.25}
    routes = [{"source": "lfo:0", "target": "camera.zoom", "op": "push", "value": 0.1},
              {"source": "lane:2", "target": "view.bright", "op": "push", "value": 0.2,
               "enabled": False}]
    put(rig.home, "PARTIAL", values=values, routes=routes)
    assert rig.presets.load("PARTIAL") == []
    assert reg.snapshot(part="performance") == expected(lib, values)
    assert rig.view.shape == 4 and reg["lfo.1.depth"].value == 0.25
    assert reg["view.bright"].value == lib.defaults("view")["view.bright"]
    assert reg["dream.decay"].value == lib.defaults("dream")["dream.decay"]
    assert [b.to_json() for b in table.routes()] == routes   # exactly the file's, disabled too
    assert [b.to_json() for b in table.bindings if b.op not in routing.MOD_OPS] == keys
    assert rig.presets.current == "PARTIAL" and not lib.is_dirty("presets")


def test_a_preset_load_never_touches_a_session_param(rig):
    """Plan 13 §10 exit 2: a tapped BPM survives TRIP, and so do the drive,
    an analyzer strip and the band scene, even when the file names them."""
    reg, control = rig.reg, rig.control
    reg["tempo.bpm"].set(100.0)
    reg["master.gain"].set(2.0)
    reg["band.0.atk"].set(0.3)
    scene = control.scene
    put(rig.home, "FAST", values={"view.shape": 5, "tempo.bpm": 140.0,
                                  "scene.select": (scene + 1) % 3})
    before = reg.snapshot(part="session")
    rig.presets.load("FAST")
    assert rig.view.shape == 5
    assert rig.clock.bpm == 100.0 and rig.chain.gain == 2.0 and rig.chain.params[0].atk == 0.3
    assert control.scene == scene and reg.snapshot(part="session") == before
    rig.presets.load("TRIP")                          # the factory party preset, too
    assert rig.clock.bpm == 100.0 and reg.snapshot(part="session") == before


def test_session_ids_in_a_preset_are_noted_and_ignored(rig):
    """Step 1: a session id, an unknown id, a row that is not a performer
    and a second performer on a target are each noted; the unknown ids are
    returned, and the panel's warning says so in one line."""
    put(rig.home, "NOISY",
        values={"view.shape": 6, "tempo.bpm": 150.0, "scene.select": 2, "nebula.glow": 0.3},
        routes=[{"source": "key:X", "target": "view.faces", "op": "toggle"},
                {"source": "hand:7", "target": "view.bright", "op": "push", "value": 0.2},
                {"source": "hand:8", "target": "view.bright", "op": "push", "value": 0.4}])
    assert rig.presets.load("NOISY") == ["nebula.glow"]
    notes = rig.presets.notes
    assert "tempo.bpm is the session's, ignored" in notes
    assert "scene.select is the session's, ignored" in notes
    assert "1 unknown id(s): nebula.glow" in notes
    assert "dropped key:X → view.faces (toggle): not a performer row" in notes
    assert any(n.startswith("dropped hand:8 → view.bright") for n in notes)
    assert rig.lib.warning.startswith("preset NOISY: ")
    assert rig.view.shape == 6 and [b.source for b in rig.router.table.routes()] == ["hand:7"]


def test_rotation_phases_survive_a_preset_load(rig):
    rig.view.ang = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    rig.lib.project.load_slot(1)
    assert rig.view.ang == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]    # the spin keeps flowing


def test_a_preset_carries_the_macros(rig):
    m = rig.reg["macro.1"]
    m.set_value(0.3)
    rig.lib.project.save_slot(4)
    assert rig.lib.read("presets", rig.lib.project.bank[4])["values"]["macro.1"] == 0.3
    m.set_value(0.8)
    rig.lib.project.load_slot(4)
    assert m.value == 0.3


# ---------------------------------------------------------------- the bank

def test_the_bank_names_the_house_presets(rig):
    pr = rig.lib.project
    assert len(pr.bank) == SLOTS and pr.bank[0] == "BIG BLUE WAVE"
    assert len(set(pr.bank)) == SLOTS and all(rig.lib.is_factory("presets", n) for n in pr.bank)
    assert rig.reg["preset.select"].names == pr.bank


def test_a_slot_names_a_preset_file(rig):
    """F<k> loads the file bank[k] names; an empty slot and a dangling name
    load nothing, change nothing, and say so."""
    lib, reg, pr = rig.lib, rig.reg, rig.lib.project
    reg["preset.load.1"].fire()
    assert lib.current("presets") == "EMBER ORBIT" and pr.active == 1 and rig.view.shape == 10
    pr.bank[5], pr.bank[3] = None, "NOPE"
    assert reg["preset.select"].names[5] == "SLOT 6"
    snap, routes = reg.snapshot(), [b.to_json() for b in rig.router.table.routes()]
    reg["preset.load.5"].fire()
    assert lib.warning.startswith("F6: an empty slot")
    reg["preset.load.3"].fire()
    assert lib.warning == "F4: no preset 'NOPE'"
    assert reg.snapshot() == snap and [b.to_json() for b in rig.router.table.routes()] == routes
    assert pr.active == 1 and lib.current("presets") == "EMBER ORBIT"


def test_cycle_flips_through_the_filled_slots(rig):
    pr = rig.lib.project
    pr.bank[2] = None
    assert pr.active == 0                                  # the startup preset's slot
    pr.cycle()
    assert pr.active == 1
    pr.cycle()
    assert pr.active == 3                                  # the empty slot is skipped
    for _ in range(SLOTS - 4):
        pr.cycle()
    assert pr.active == SLOTS - 1
    pr.cycle()
    assert pr.active == 0                                  # wraps
    pr.cycle(-1)
    assert pr.active == SLOTS - 1                          # and backwards


def test_shift_f_saves_the_live_state_as_the_slots_preset(rig):
    """⇧F<k>: the live state as the slot's preset in the user folder (a
    factory file is shadowed, never overwritten), the bank updated and the
    project written; an empty slot gets a new, unique name."""
    lib, reg, pr, home = rig.lib, rig.reg, rig.lib.project, rig.home
    factory = FACTORY / "presets" / "strobe-cage.json"
    before = factory.read_bytes()
    rig.view.shape = 12
    rig.router.table.add(Binding("hand:7", "view.speed", "push", 0.3))
    reg["preset.save.2"].fire()
    assert factory.read_bytes() == before                  # never overwritten…
    user = json.loads((home / "presets" / "strobe-cage.json").read_text())
    assert not lib.is_factory("presets", "STROBE CAGE")    # …shadowed
    assert user["name"] == "STROBE CAGE" and user["values"]["view.shape"] == 12
    assert {"source": "hand:7", "target": "view.speed", "op": "push", "value": 0.3} in user["routes"]
    assert "tempo.bpm" not in user["values"] and "master.gain" not in user["values"]
    assert pr.bank[2] == "STROBE CAGE" and pr.active == 2
    doc = json.loads((home / "projects" / "default.hyp.json").read_text())
    assert doc["schema"] == "hyperspace.project/2" and doc["bank"] == pr.bank
    # an empty slot: a new name, made unique against what is there
    put(home, "PRESET 8")
    pr.bank[6] = pr.bank[7] = None
    reg["preset.save.6"].fire()
    reg["preset.save.7"].fire()
    assert pr.bank[6] == "PRESET 7" and pr.bank[7] == "PRESET 8 (2)"
    assert (home / "presets" / "preset-7.json").is_file()
    assert json.loads((home / "projects" / "default.hyp.json").read_text())["bank"] == pr.bank
    assert not pr.is_dirty() and pr.bank_error == ""


def test_a_full_disk_does_not_stop_the_show(rig, monkeypatch):
    def full(*a, **k):
        raise LibraryError("disk full")
    monkeypatch.setattr(rig.lib, "save_as", full)
    rig.lib.project.save_slot(0)
    assert "disk full" in rig.lib.project.bank_error


# ---------------------------------------------------------------- startup

def test_the_startup_preset_loads_on_launch(tmp_path):
    """D11: the project names its startup preset and a launch loads it; a
    startup with no file says so and the app keeps running."""
    r = boot(tmp_path)
    assert r.lib.project.startup == "BIG BLUE WAVE"
    assert r.lib.current("presets") == "BIG BLUE WAVE" and r.lib.project.active == 0
    assert r.view.shape == 17 and len(r.router.table.routes()) == 12
    doc = json.loads((FACTORY / "projects" / "default.hyp.json").read_text())
    doc["startup"] = "GONE"
    (tmp_path / "projects" / "default.hyp.json").write_text(json.dumps(doc))
    r2 = boot(tmp_path)
    assert r2.lib.warning == "startup: no preset 'GONE'"
    assert r2.lib.current("presets") is None and r2.lib.project.active == -1
    r2.reg["preset.load.2"].fire()                          # and the bank still works
    assert r2.lib.current("presets") == "STROBE CAGE"


# ---------------------------------------------------------------- module labels

def test_module_labels_are_recorded_and_never_chain_load(rig):
    """D3: `modules` sets the strip's label with a clean dot; the group's
    values are the preset's (over the group default), never the module
    preset's file; a group the file does not name shows no label."""
    lib, reg = rig.lib, rig.reg
    lib.load("dream", "wake")
    trip = lib.read("fx", "trip")["values"]
    assert trip["fx.kaleido.on"] is True
    put(rig.home, "LABELS", values={"fx.on": True}, modules={"fx": "trip"})
    rig.presets.load("LABELS")
    assert lib.current("fx") == "trip" and not lib.is_dirty("fx")
    assert reg.snapshot("fx") == lib.resolved("fx", {"fx.on": True})
    assert reg["fx.kaleido.on"].value == lib.defaults("fx")["fx.kaleido.on"] != trip["fx.kaleido.on"]
    assert lib.current("dream") is None
    reg["fx.mix"].set(0.3)
    assert lib.is_dirty("fx")                               # the dot is live against the load


# ---------------------------------------------------------------- save

def test_a_preset_round_trips(rig):
    """Save then load gives the same signature; `desk` and `macros` are
    carried verbatim (plan 13 WP4 wires them), `modules` names the
    performance groups' labels."""
    lib = rig.lib
    desk = [{"source": "cc:0:48", "target": "view.bright", "op": "abs"}]
    macros = {"macro.1": {"label": "Heat", "subs": [
        {"base": "fx.plasma.level", "from": 0.0, "to": 0.6}]}}
    put(rig.home, "SRC", values={"view.shape": 3}, desk=desk, macros=macros, note="a note",
        routes=[{"source": "hand:7", "target": "view.speed", "op": "push", "value": 0.3}])
    rig.presets.load("SRC")
    lib.load("fx", "acid")
    rig.reg["camera.zoom"].set(2.0)
    sig = rig.presets.signature()
    path = rig.presets.save_as("Round Trip")
    assert path == rig.home / "presets" / "round-trip.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.preset/2" and doc["name"] == "Round Trip"
    assert doc["desk"] == desk and doc["macros"] == macros and doc["note"] == "a note"
    assert doc["modules"] == {"fx": "acid"}
    assert doc["values"] == rig.reg.snapshot(part="performance")
    rig.reg["camera.zoom"].set(1.0)
    rig.lib.project.load_slot(0)                            # something else in between
    rig.presets.load("Round Trip")
    assert rig.presets.signature() == sig and not lib.is_dirty("presets")
    assert rig.presets.desk == desk and rig.presets.macros == macros
    assert lib.current("fx") == "acid"


def test_a_preset_edited_on_disk_is_re_applied(rig):
    path = put(rig.home, "LIVE", values={"view.shape": 2})
    rig.presets.load("LIVE")
    rig.lib.poll(now=1.0)
    doc = json.loads(path.read_text())
    doc["values"]["view.shape"] = 9
    path.write_text(json.dumps(doc))
    import os
    os.utime(path, (2e9, 2e9))
    assert rig.lib.poll(now=2.0)
    assert rig.view.shape == 9 and rig.lib.current("presets") == "LIVE"


# ---------------------------------------------------------------- the project

def test_a_schema_1_user_project_is_refused_until_the_migration(tmp_path):
    """Plan 13 WP2 does not migrate a user's schema-1 project (WP5 does):
    it is refused with a clear error and the factory default stands in; a
    save over it keeps the old file as a backup first."""
    old = {"schema": "hyperspace.project/1", "name": "default", "values": {},
           "modules": {}, "bank": [{"name": "MINE", "values": {"view.shape": 3}}]}
    (tmp_path / "projects").mkdir(parents=True)
    (tmp_path / "projects" / "default.hyp.json").write_text(json.dumps(old))
    (tmp_path / "projects" / "gig.hyp.json").write_text(json.dumps(old))
    r = boot(tmp_path)
    assert "schema-1 project; plan 13's migration (WP5) converts it" in r.lib.error
    assert r.lib.project.path is None and r.lib.project.bank[0] == "BIG BLUE WAVE"
    with pytest.raises(LibraryError, match=r"gig.hyp.json is a schema-1 project.*WP5"):
        r.lib.project.load("gig")
    assert r.lib.project.bank[0] == "BIG BLUE WAVE"          # the refused load changed nothing
    r.lib.project.save_slot(0)
    assert json.loads((tmp_path / "projects" / "default.hyp.json").read_text())["schema"] \
        == "hyperspace.project/2"
    bak = tmp_path / "projects" / "default.hyp.json.bak-v1"
    assert json.loads(bak.read_text()) == old


def test_a_project_load_brings_its_startup_preset(rig):
    rig.lib.project.load("party")
    assert rig.lib.current("presets") == "TUMBLE" and rig.view.shape == 10
    assert rig.lib.project.active == 0 and rig.lib.current("band") == "Balanced"


# ---------------------------------------------------------------- factory files

def test_the_factory_presets_are_preset_2_performance_files():
    reg_ids = {p.id: p for p in boot_registry()}
    for path in sorted((FACTORY / "presets").glob("*.json")):
        doc = json.loads(path.read_text())
        assert doc["schema"] == preset.SCHEMA, path.name
        assert doc["desk"] == [] and doc["macros"] == {}, path.name
        for pid in doc["values"]:
            assert part_of(reg_ids[pid]) == "performance", (path.name, pid)
        for row in doc["routes"]:
            b = Binding.from_json(row)
            assert b.scheme in routing.LANE_SCHEMES and b.op in routing.MOD_OPS, (path.name, row)
    for name in ("default", "party"):
        proj = json.loads((FACTORY / "projects" / f"{name}.hyp.json").read_text())
        assert proj["schema"] == "hyperspace.project/2" and proj["startup"] == proj["bank"][0]
        names = {json.loads(p.read_text())["name"] for p in (FACTORY / "presets").glob("*.json")}
        assert {n for n in proj["bank"] if n} <= names, name


def boot_registry():
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain),
                         dream=DreamState(), fx=FxState())
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    return reg


def test_the_party_presets_routes_are_the_codes():
    """`python -m hyperspace.preset` regenerates the five party presets'
    routes from routing.PRESETS; the files may not drift from the code.
    The house presets carry the factory table's lane rows."""
    for slug, name in preset.PARTY.items():
        doc = json.loads((preset.FACTORY_DIR / f"{slug}.json").read_text())
        assert doc["routes"] == [b.to_json() for b in routing.PRESETS[name][0]], slug
        assert doc["name"] == slug.split("-", 1)[1].upper()
    lanes = [b.to_json() for b in routing.legacy6_routes()]
    for name in json.loads((FACTORY / "projects" / "default.hyp.json").read_text())["bank"]:
        path = preset.FACTORY_DIR / f"{name.lower().replace(' ', '-')}.json"
        assert json.loads(path.read_text())["routes"] == lanes, name


def test_write_factory_rewrites_only_the_routes(tmp_path):
    for slug in preset.PARTY:
        doc = json.loads((preset.FACTORY_DIR / f"{slug}.json").read_text())
        doc["routes"] = []
        (tmp_path / f"{slug}.json").write_text(json.dumps(doc))
    preset.write_factory(tmp_path)
    for slug in preset.PARTY:
        assert (tmp_path / f"{slug}.json").read_text() == \
            (preset.FACTORY_DIR / f"{slug}.json").read_text()
