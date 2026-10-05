"""Plan 13 WP2 — the preset (``hyperspace.preset/2``), the project's bank of
preset names (``hyperspace.project/2``), the F-keys and the startup preset.

Every rig is built the way app.main builds it — Library, registry, attach,
the Router over the home's bindings.json, `Presets`, the migration, the
startup preset — on a tmp_path home, never ~/Hyperspace. The bank tests
that were tests/test_themes.py (the inline theme bank) are folded in here
as the bank of names.
"""

import itertools
import json
import re
from types import SimpleNamespace

import pytest
from conftest import opened_last

from hyperspace import apc40, lfo, preset, routing, tempo
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


def boot(home, show: str | None = "house"):
    """The app's construction order (app.main), headless — over a home
    that opened `show` last (the house moods, which these tests were
    written on; None: a fresh home, which opens the party show)."""
    if show:
        opened_last(home, show)
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
    presets = Presets(lib, reg, router)
    preset.migrate_home(lib, router)          # plan 13 §6: nothing to do on a fresh home
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
    reg["dream.fade"].set(2.0)                          # a dream value
    table.add(Binding("hand:7", "view.speed", "push", 0.3))    # a hand route
    keys = [b.to_json() for b in table.bindings
            if b.op not in routing.MOD_OPS and b.layer != "preset"]
    values = {"view.shape": 4, "fx.on": True, "lfo.1.depth": 0.25}
    routes = [{"source": "lfo:0", "target": "camera.zoom", "op": "push", "value": 0.1},
              {"source": "lane:2", "target": "view.bright", "op": "push", "value": 0.2,
               "enabled": False}]
    put(rig.home, "PARTIAL", values=values, routes=routes)
    assert rig.presets.load("PARTIAL") == []
    assert reg.snapshot(part="performance") == expected(lib, values)
    assert rig.view.shape == 4 and reg["lfo.1.depth"].value == 0.25
    assert reg["view.bright"].value == lib.defaults("view")["view.bright"]
    assert reg["dream.fade"].value == lib.defaults("dream")["dream.fade"]
    assert [b.to_json() for b in table.routes()] == routes   # exactly the file's, disabled too
    assert [b.to_json() for b in table.bindings
            if b.op not in routing.MOD_OPS and b.layer != "preset"] == keys
    assert table.desk() == []                               # the file's `desk: []`
    assert rig.presets.current == "PARTIAL" and not lib.is_dirty("presets")


def test_a_preset_with_per_frame_echo_ids_is_read_in_seconds(rig):
    """Plan 14 WP6: a preset file that still names the per-frame
    `dream.decay` / `dream.every` loads as 60 Hz frames in seconds — its
    values, a hand push on the decay (the same throw of decays), a desk
    knob on it — and the load says so, once."""
    from hyperspace.lookback import decay_per_frame, fade_of_decay

    put(rig.home, "OLDWAKE", values={"dream.on": True, "dream.decay": 0.93, "dream.every": 2},
        routes=[{"source": "hand:right.z", "target": "dream.decay", "op": "push",
                 "value": -0.12}],
        desk=[{"source": "cc:*:17", "target": "dream.decay", "op": "abs", "feedback": "ring"}])
    assert rig.presets.load("OLDWAKE") == []
    reg, table = rig.reg, rig.router.table
    assert reg["dream.fade"].value == pytest.approx(fade_of_decay(0.93))
    assert reg["dream.gap"].value == pytest.approx(2 / 60, abs=1e-6)
    assert len(rig.presets.notes) == 1 and "look-back read in seconds" in rig.presets.notes[0]
    (row,) = table.routes()
    assert row.target == "dream.fade" and row.value < 0          # reach in: longer, as before
    # the throw spans as far as the old one (0.87 … 0.99 a frame), in
    # fade's own (log) norm about the base: reach in lasts, pull back snaps
    p = reg["dream.fade"]
    ends = [decay_per_frame(p._raw_value(p.norm + row.value * (u - 0.5))) for u in (0.0, 1.0)]
    assert ends[0] > 0.975 and ends[1] < 0.9, ends
    span = abs(p._raw_norm(fade_of_decay(0.99)) - p._raw_norm(fade_of_decay(0.87)))
    assert abs(row.value) == pytest.approx(span, abs=1e-3)
    assert any(b.target == "dream.fade" and b.source == "cc:*:17" for b in table.desk())


def test_the_echo_migration_keeps_every_depth_and_survives_bad_values(tmp_path):
    """Review of PR #76: a full-depth push has no `value` key and is still
    re-drawn; a macro's depth subscriber on such a route moves its ends to
    fade's units too; a value that is not a number is noted, never raised
    (one odd hand-edited file must not stop a launch)."""
    from hyperspace.lookback import fade_depth, migrate_row

    row, note = migrate_row({"source": "hand:right.z", "target": "dream.decay", "op": "push"})
    assert row["target"] == "dream.fade" and row["value"] == fade_depth(1.0, "hand:right.z")
    assert 0 < row["value"] <= 1 and "push" in note
    doc = {"schema": preset.SCHEMA, "name": "X", "values": {"dream.decay": 0.93},
           "routes": [{"source": "hand:right.y", "target": "dream.decay", "op": "push",
                       "value": 0.05}],
           "macros": {"macro.1": {"subs": [{"depth": {"source": "hand:right.y",
                                                      "target": "dream.decay"},
                                            "from": 0.0, "to": 0.05}]}}}
    new, _ = preset.echo_seconds(doc)
    sub = new["macros"]["macro.1"]["subs"][0]
    assert sub["depth"]["target"] == "dream.fade"
    assert sub["from"] == 0.0 and sub["to"] == new["routes"][0]["value"]
    # bad values: noted, not raised
    bad = {"schema": preset.SCHEMA, "name": "BAD", "values": {"dream.decay": "long"},
           "routes": [{"source": "hand:right.z", "target": "dream.decay", "op": "push",
                       "value": None}],
           "macros": {"macro.1": {"subs": [{"base": "dream.decay", "from": None, "to": 1}]}}}
    new, notes = preset.echo_seconds(bad)
    assert "dream.decay" not in new["values"] and new["routes"][0]["target"] == "dream.fade"
    assert any("not a number" in n for n in notes)
    put(tmp_path, "BAD", **{k: v for k, v in bad.items() if k not in ("schema", "name")})
    notes, written = preset.migrate_echo_home(tmp_path)
    assert len(written) == 1 and notes


def test_the_home_is_rewritten_in_seconds_once_with_backups(tmp_path):
    """Plan 14 WP6: a user preset and a look-back module preset naming the
    per-frame ids are rewritten once, each kept first as
    `<file>.bak-v2-frames`; a second run finds nothing."""
    from hyperspace.lookback import fade_of_decay

    home = tmp_path
    p = put(home, "MINE", values={"dream.decay": 0.9, "view.shape": 3})
    d = home / "dream" / "old.json"
    d.parent.mkdir()
    d.write_text(json.dumps({"schema": "hyperspace.preset/1", "group": "dream", "name": "old",
                             "values": {"dream.every": 3, "dream.mix": 0.2}}))
    before = p.read_text(), d.read_text()
    notes, written = preset.migrate_echo_home(home)
    assert sorted(written) == sorted([p, d]) and len(notes) == 2
    assert json.loads(p.read_text())["values"] == {"dream.fade": fade_of_decay(0.9),
                                                   "view.shape": 3}
    assert json.loads(d.read_text())["values"] == {"dream.gap": 0.05, "dream.mix": 0.2}
    assert (p.with_name(p.name + ".bak-v2-frames").read_text(),
            d.with_name(d.name + ".bak-v2-frames").read_text()) == before
    assert preset.migrate_echo_home(home) == ([], [])


def test_a_preset_load_never_touches_a_session_param(rig):
    """Plan 13 §10 exit 2: a tapped BPM survives TRIP, and so do the drive,
    an analyzer strip and the band scene, even when the file names them —
    and the master dim (plan 15 WP3), through a preset load and a show load."""
    from hyperspace.overlay import Output

    reg, control = rig.reg, rig.control
    out = Output(None, None)
    out.register(reg)
    reg["output.dim"].set(0.4)
    assert part_of(reg["output.dim"]) == "session"
    reg["tempo.bpm"].set(100.0)
    reg["master.gain"].set(2.0)
    reg["band.0.atk"].set(0.3)
    scene = control.scene
    put(rig.home, "FAST", values={"view.shape": 5, "tempo.bpm": 140.0,
                                  "scene.select": (scene + 1) % 3, "output.dim": 1.0})
    before = reg.snapshot(part="session")
    rig.presets.load("FAST")
    assert rig.view.shape == 5
    assert rig.clock.bpm == 100.0 and rig.chain.gain == 2.0 and rig.chain.params[0].atk == 0.3
    assert control.scene == scene and reg.snapshot(part="session") == before
    assert out.dim == 0.4 and "output.dim is the session's, ignored" in rig.presets.notes
    rig.presets.load("TRIP")                          # the factory party preset, too
    assert rig.clock.bpm == 100.0 and reg.snapshot(part="session") == before
    assert out.dim == 0.4
    rig.lib.project.load("party")                     # a show load, startup preset and all
    assert rig.lib.current("presets") == "TUMBLE" and out.dim == 0.4


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


def test_a_value_that_will_not_land_leaves_the_state_whole(rig):
    """Review of PR #64: a hand-edited value that will not take refuses the
    load whole — the bases, the routes and the strip stay on the last preset."""
    lib, reg = rig.lib, rig.reg
    snap, routes = reg.snapshot(), [b.to_json() for b in rig.router.table.routes()]
    put(rig.home, "BROKEN", values={"view.shape": 3, "view.speed": "fast"},
        routes=[{"source": "hand:7", "target": "view.bright", "op": "push"}])
    with pytest.raises(LibraryError, match="nothing loaded"):
        rig.presets.load("BROKEN")
    assert reg.snapshot() == snap
    assert [b.to_json() for b in rig.router.table.routes()] == routes
    assert lib.current("presets") == "BIG BLUE WAVE" and not lib.is_dirty("presets")


def test_a_project_reload_keeps_the_loaded_preset(rig):
    """Review of PR #64: a project re-read from disk (or opened with no
    startup preset) keeps the preset that is loaded — its name, its clean
    reference and its slot's light."""
    lib, pr = rig.lib, rig.lib.project
    pr.load_slot(1)
    path = pr.save("Set")
    lib.poll(now=1.0)
    doc = json.loads(path.read_text())
    doc["session"]["master.gain"] = 3.0
    path.write_text(json.dumps(doc))
    import os
    os.utime(path, (2e9, 2e9))
    assert lib.poll(now=2.0) and rig.chain.gain == 3.0
    assert lib.current("presets") == "EMBER ORBIT" and not lib.is_dirty("presets")
    assert pr.active == 1
    doc["startup"] = None
    (rig.home / "projects" / "bare.hyp.json").write_text(json.dumps(doc))
    pr.load("bare")
    assert lib.current("presets") == "EMBER ORBIT" and pr.active == 1


def test_a_strip_save_as_moves_the_banks_light(rig):
    """Review of PR #64: saving the live state from the strip under a name
    the bank does not hold puts the slot light out; one the bank names
    lights that slot."""
    lib, pr = rig.lib, rig.lib.project
    pr.load_slot(1)
    lib.save_as("presets", "Elsewhere")
    assert lib.current("presets") == "Elsewhere" and pr.active == -1
    lib.save_as("presets", "STROBE CAGE")
    assert pr.active == 2


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
    doc = json.loads((home / "projects" / "house.hyp.json").read_text())
    assert doc["schema"] == "hyperspace.project/2" and doc["bank"] == pr.bank
    # an empty slot: a new name, made unique against what is there
    put(home, "PRESET 8")
    pr.bank[6] = pr.bank[7] = None
    reg["preset.save.6"].fire()
    reg["preset.save.7"].fire()
    assert pr.bank[6] == "PRESET 7" and pr.bank[7] == "PRESET 8 (2)"
    assert (home / "presets" / "preset-7.json").is_file()
    assert json.loads((home / "projects" / "house.hyp.json").read_text())["bank"] == pr.bank
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
    doc = json.loads((FACTORY / "projects" / "house.hyp.json").read_text())
    doc["startup"] = "GONE"
    (tmp_path / "projects" / "house.hyp.json").write_text(json.dumps(doc))
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
    the table's (plan 13 WP4), `modules` names the performance groups'
    labels. (The base subscriber names a param nothing else in the test
    moves: the macro is the scene-setter of record, so a param a later
    module load moved would land back on the subscriber's value.)"""
    lib, table = rig.lib, rig.router.table
    desk = [{"source": "cc:0:48", "target": "view.bright", "op": "abs"}]
    macros = {"macro.1": {"label": "Heat", "subs": [
        {"base": "view.depth4", "from": 0.0, "to": 0.6}]}}
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
    assert preset.desk_json(table.desk()) == desk and table.macros_doc() == macros
    assert lib.current("fx") == "acid"


# ---------------------------------------------------------------- the desk and the macros

DESK = [{"source": "cc:*:16", "target": "view.speed", "op": "abs", "feedback": "ring"},
        {"source": "note:0:82", "target": "view.points", "op": "toggle", "feedback": "led"}]
MACROS = {"macro.1": {"label": "Heat", "subs": [
    {"base": "view.depth4", "from": 0.2, "to": 0.8},
    {"depth": {"source": "hand:7", "target": "view.bright"}, "from": 0.0, "to": 1.0}]}}


def test_a_preset_load_replaces_the_desk_and_the_macros(rig):
    """Plan 13 D2 / D4, §5 steps 4–5: the preset layer is the file's (a row
    on an invariant control dropped, its note in the load's), the layer
    drops to it, the global and invariant rows stay; the macros are the
    file's and their base subscribers land at once from the macros' bases
    — over `values` naming the same param (the macro is the scene-setter
    of record); an explicit `desk: []` leaves every preset control dark."""
    lib, reg, table = rig.lib, rig.reg, rig.router.table
    session = [b.to_json() for b in table.midi() if b.layer != "preset"]
    table.set_layer("global")
    put(rig.home, "DESKED", values={"macro.1": 0.5, "view.depth4": 1.0},
        routes=[{"source": "hand:7", "target": "view.bright", "op": "position"}],
        desk=[*DESK, {"source": "cc:0:7", "target": "view.bright", "op": "abs"}],
        macros=MACROS)
    rig.presets.load("DESKED")
    assert preset.desk_json(table.desk()) == DESK and table.layer == "preset"
    assert any("cc:0:7 → view.bright" in n and "invariant" in n for n in rig.presets.notes)
    assert rig.presets.desk_notes and "cc:0:7" in rig.presets.desk_notes[0]
    assert [b.to_json() for b in table.midi() if b.layer != "preset"] == session
    assert table.macros_doc() == MACROS
    depth4 = reg["view.depth4"]
    assert depth4.norm == pytest.approx(0.5, abs=1e-6)        # 0.2 + 0.5 · (0.8 − 0.2)
    assert not lib.is_dirty("presets")                        # landed before the clean reference
    assert rig.router.follow_macros() == []                   # nothing left to land next frame
    put(rig.home, "DARK", desk=[], macros={})
    rig.presets.load("DARK")
    assert table.desk() == [] and table.macros_doc() == {}
    assert [b.to_json() for b in table.midi() if b.layer != "preset"] == session


def test_a_preset_without_a_desk_gets_the_factory_preset_layer(rig):
    """A file with no `desk` key is a fresh preset's desk: the factory map's
    preset layer (plan 13 §3.2)."""
    table = rig.router.table
    put(rig.home, "EMPTY", desk=[])
    rig.presets.load("EMPTY")
    assert table.desk() == []
    path = put(rig.home, "BARE")
    doc = json.loads(path.read_text())
    del doc["desk"], doc["macros"]
    path.write_text(json.dumps(doc))
    rig.presets.load("BARE")
    fresh = [b for b in routing.factory_desk() if b.layer == "preset"]
    assert [b.to_json() for b in table.desk()] == [b.to_json() for b in fresh]
    assert preset.desk_json(table.desk()) == preset.desk_json(preset.fresh_desk())
    assert rig.presets.document("BARE")["desk"] == preset.desk_json(fresh)


def test_a_preset_with_a_desk_and_macros_round_trips(rig):
    """What the table holds is what a save writes: an edit of the desk or a
    macro moves the dirty dot, a save writes it, a load brings it back."""
    lib, table = rig.lib, rig.router.table
    put(rig.home, "SHOW", desk=DESK, macros=MACROS,
        routes=[{"source": "hand:7", "target": "view.bright", "op": "position"}])
    rig.presets.load("SHOW")
    assert not lib.is_dirty("presets")
    table.desk()[0].target = "view.instances"                 # the page's retarget
    assert lib.is_dirty("presets")
    table.macros["macro.1"].label = "Cold"
    path = rig.presets.save_as("SHOW")
    doc = json.loads(path.read_text())
    assert doc["desk"][0]["target"] == "view.instances" and "layer" not in doc["desk"][0]
    assert doc["macros"]["macro.1"]["label"] == "Cold"
    assert not lib.is_dirty("presets")
    rig.presets.load("TRIP")
    assert table.macros_doc() != doc["macros"]
    rig.presets.load("SHOW")
    assert preset.desk_json(table.desk()) == doc["desk"] and table.macros_doc() == doc["macros"]
    assert not lib.is_dirty("presets")


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

def test_a_project_load_brings_its_startup_preset(rig):
    rig.lib.project.load("party")
    assert rig.lib.current("presets") == "TUMBLE" and rig.view.shape == 10
    assert rig.lib.project.active == 0 and rig.lib.current("band") == "Balanced"


# ---------------------------------------------------------------- factory files



def boot_registry():
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain),
                         dream=DreamState(), fx=FxState())
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    return reg


def expected_desk(slug: str) -> list[dict] | None:
    """What the generator gives a factory preset's `desk`: its entry's
    (None: no key), else the factory preset layer."""
    spec = preset.FACTORY_PRESETS.get(slug)
    desk = preset.fresh_desk if spec is None else spec.desk
    return None if desk is None else preset.desk_json(desk())


def test_the_factory_presets_are_preset_2_performance_files():
    """Every factory preset is a performance file; its macros are the
    generator's (plan 13 WP5: lfo-breathe's Breathe, none elsewhere)."""
    reg_ids = {p.id: p for p in boot_registry()}
    for path in sorted((FACTORY / "presets").glob("*.json")):
        doc = json.loads(path.read_text())
        assert doc["schema"] == preset.SCHEMA, path.name
        spec = preset.FACTORY_PRESETS.get(path.stem)
        macros = {} if spec is None else {k: m.to_json() for k, m in spec.macros().items()}
        assert doc["macros"] == macros, path.name
        for pid in doc["values"]:
            assert part_of(reg_ids[pid]) == "performance", (path.name, pid)
        for row in doc["routes"]:
            b = Binding.from_json(row)
            assert b.scheme in routing.LANE_SCHEMES and b.op in routing.MOD_OPS, (path.name, row)
    assert json.loads((preset.FACTORY_DIR / "lfo-breathe.json").read_text())["macros"]
    for name in ("house", "party"):
        proj = json.loads((FACTORY / "projects" / f"{name}.hyp.json").read_text())
        assert proj["schema"] == "hyperspace.project/2" and proj["startup"] == proj["bank"][0]
        names = {json.loads(p.read_text())["name"] for p in (FACTORY / "presets").glob("*.json")}
        assert {n for n in proj["bank"] if n} <= names, name


def test_the_party_presets_routes_are_the_codes():
    """`python -m hyperspace.preset` regenerates the five party presets'
    routes from `preset.FACTORY_PRESETS`; the files may not drift from the
    code. The house presets carry the lane rows the factory table shipped."""
    assert preset.PARTY[:8] == preset.PARTY_BANK == (
        "party-tumble", "party-faces", "party-field", "party-wake", "party-trip",
        "party-acid", "party-mandala", "party-noita")
    for slug in preset.PARTY:
        doc = json.loads((preset.FACTORY_DIR / f"{slug}.json").read_text())
        routes = [b.to_json() for b in preset.FACTORY_PRESETS[slug].routes()]
        assert doc["routes"] == routes, slug
        assert doc["name"] == slug.split("-", 1)[1].upper()
    lanes = [b.to_json() for b in routing.legacy6_routes()]
    for name in json.loads((FACTORY / "projects" / "house.hyp.json").read_text())["bank"]:
        path = preset.FACTORY_DIR / f"{name.lower().replace(' ', '-')}.json"
        assert json.loads(path.read_text())["routes"] == lanes, name


def test_every_factory_presets_desk_is_the_generators():
    """Plan 13 WP4, re-cut in WP5: every factory preset's `desk` is what
    `python -m hyperspace.preset` writes — the factory map's preset layer,
    plus plan 12 §6's eight device knobs on WAKE and TRIP and the Breathe
    macro on lfo-breathe's device knob 1; the presets made from routes-only
    files other than lfo-breathe carry no `desk` key (a load gives them the
    factory layer)."""
    desk = preset.desk_json(preset.fresh_desk())
    assert desk and all("layer" not in d for d in desk)
    from_map = []
    for d in apc40.DEFAULT_MAP:
        if d.get("layer") == "preset":
            row = Binding.from_json(d).to_json()
            row.pop("layer")
            from_map.append(row)
    assert desk == from_map
    paths = sorted(preset.FACTORY_DIR.glob("*.json"))
    assert len(paths) == 22                  # 8 house, 9 party, 5 made from routing presets
    for path in paths:
        doc = json.loads(path.read_text())
        want = expected_desk(path.stem)
        if want is None:
            assert "desk" not in doc, path.name
        else:
            assert doc["desk"] == want, path.name
    knobs = [f"cc:*:{0x10 + k}" for k in range(8)]
    for slug, targets in (("party-wake", preset.WAKE_KNOBS), ("party-trip", preset.TRIP_KNOBS),
                          ("party-acid", preset.ACID_KNOBS),
                          ("party-mandala", preset.MANDALA_KNOBS),
                          ("party-noita", preset.NOITA_KNOBS),
                          ("party-tracer", preset.TRACER_KNOBS)):
        rows = json.loads((preset.FACTORY_DIR / f"{slug}.json").read_text())["desk"]
        assert rows[:len(desk)] == desk
        assert [(d["source"], d["target"], d["op"], d["feedback"]) for d in rows[len(desk):]] \
            == [(k, t, "abs", "ring") for k, t in zip(knobs, targets, strict=True)]
    breathe = json.loads((preset.FACTORY_DIR / "lfo-breathe.json").read_text())["desk"]
    assert breathe[-1] == {"source": "cc:*:16", "target": "macro.1", "op": "abs",
                           "feedback": "ring"}
    for slug in ("party-tumble", "party-faces", "party-field"):
        assert json.loads((preset.FACTORY_DIR / f"{slug}.json").read_text())["desk"] == desk


def test_write_factory_regenerates_every_factory_file(tmp_path):
    """Was test_write_factory_rewrites_only_the_routes_and_the_desk: the
    generator rewrites the party presets' routes, desk and macros and every
    other preset's desk from code, and writes the presets made from routing
    presets whole; everything else in a file is data it keeps."""
    for path in preset.FACTORY_DIR.glob("*.json"):
        spec = preset.FACTORY_PRESETS.get(path.stem)
        if spec is not None and spec.values is not None:
            continue                                     # written whole: none to start from
        doc = json.loads(path.read_text())
        doc["routes"] = [] if path.stem in preset.PARTY else doc["routes"]
        doc["desk"], doc["macros"] = [], {"macro.2": {"label": "stale", "subs": []}} \
            if path.stem in preset.PARTY else doc["macros"]
        (tmp_path / path.name).write_text(json.dumps(doc))
    preset.write_factory(tmp_path)
    for path in preset.FACTORY_DIR.glob("*.json"):
        assert (tmp_path / path.name).read_text() == path.read_text(), path.name
    assert sorted(p.name for p in tmp_path.glob("*.json")) == \
        sorted(p.name for p in preset.FACTORY_DIR.glob("*.json"))


def test_every_factory_presets_hand_rows_are_named():
    """Decision register row 20 (plan 13 WP5b): no factory preset names a
    hand lane by number — every hand source, every gate and every macro
    subscriber's route is `hand:<name>` on the default layout's names, so
    a rig that reorders `[hands] dofs` keeps every preset on its axes."""
    from hyperspace.hands import default_addresses

    names = {f"hand:{n}" for n in default_addresses()}
    seen = 0
    for path in sorted(preset.FACTORY_DIR.glob("*.json")):
        text = path.read_text()
        assert not re.search(r'"hand:\d', text), path.name
        doc = json.loads(text)
        addrs = [a for d in doc.get("routes") or [] for a in (d["source"], d.get("when"))]
        addrs += [s["depth"]["source"] for m in (doc.get("macros") or {}).values()
                  for s in m.get("subs") or [] if "depth" in s]
        for a in addrs:
            if a is not None and a.startswith("hand:"):
                assert a in names, (path.name, a)
                seen += 1
    assert seen > 40                                 # the party presets and the hands-* ones


def test_the_routing_presets_are_full_factory_presets(rig):
    """Decision 10: `legacy6`, `lfo-breathe` and the three `hands-*` are full
    presets under library/presets/ — a load lands every performance base
    (its values, else the defaults) and replaces every route; nothing is
    left under library/bindings/ and no `bindings` group is listed."""
    assert not (FACTORY / "bindings").exists() and "bindings" not in rig.lib.groups()
    for name in ("legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play"):
        assert rig.lib.is_factory("presets", name), name
        doc = json.loads((preset.FACTORY_DIR / f"{name}.json").read_text())
        assert doc == preset.generated(name), name
        rig.reg["view.shape"].set(5)
        rig.presets.load(name)
        assert rig.presets.notes == [] and rig.lib.current("presets") == name
        assert [b.to_json() for b in rig.router.table.routes()] == doc["routes"]
        assert rig.view.shape == rig.lib.defaults("view")["view.shape"], name   # D2


def test_a_converted_preset_switches_on_the_effects_its_routes_drive(rig):
    """PR #29's rule for a routes-only file made a full preset: an effect a
    route drives is switched on (`fx.on`, `fx.<name>.on`, `dream.on`) unless
    the file names it — `hands-fx` turns Acid on, so the hand plays into it."""
    fx = preset.generated("hands-fx")["values"]
    assert fx["fx.on"] is True and fx["fx.acid.on"] is True and fx["fx.acid.speed"] == 4.0
    rig.presets.load("hands-fx")
    assert rig.reg["fx.on"].value is True and rig.reg["fx.acid.on"].value is True
    # plan 14 WP5: hands-pinch's fx.mix row plays into the hue cycle, from 0
    assert preset.generated("hands-pinch")["values"] == {"fx.mix": 0.0, "fx.huecycle.on": True,
                                                         "fx.on": True}
    assert preset.generated("lfo-breathe")["values"]["fx.on"] is True
    assert "fx.on" not in preset.generated("hands-play")["values"]
    assert "fx.on" not in preset.generated("legacy6")["values"]
    rows = [Binding("hand:1", "dream.mix", "position"), Binding("hand:2", "fx.warp.amount",
                                                                "push", 0.2)]
    assert preset.effects_on(rows, {"fx.warp.on": False}) == {
        "fx.warp.on": False, "fx.on": True, "dream.on": True}                # named: kept
    ids = set(rig.reg.ids())
    assert preset.effects_on([Binding("hand:1", "fx.nosuch.x", "push", 0.1)], {},
                             lambda pid: pid in ids) == {"fx.on": True}


def test_lfo_breathes_macro_moves_brightness_up_and_speed_down(rig):
    """Hand check 39's machine half: lfo-breathe loads with Breathe (macro.1,
    device knob 1) at the bottom; turning it up brightens the picture from
    1× to 2× while the spin slows from 0.25× to a crawl, both over the
    knob's whole throw, and the LFO's push on the fx mix deepens with it."""
    reg, router, table = rig.reg, rig.router, rig.router.table
    rig.presets.load("lfo-breathe")
    knob = reg["macro.1"]
    bright, speed = reg["view.bright"], reg["view.speed"]
    assert knob.value == 0.0 and table.macros["macro.1"].label == "Breathe"
    assert bright.value == pytest.approx(1.0) and speed.value == pytest.approx(0.25)
    row = next(b for b in table.desk() if b.source == "cc:*:16")
    assert row.target == "macro.1" and row.op == "abs" and row.feedback == "ring"
    seen = []
    for m in (0.0, 0.25, 0.5, 0.75, 1.0):
        knob.set_norm(m)
        router.follow_macros()
        seen.append((bright.value, speed.value))
    assert all(b2 > b1 and s2 < s1 for (b1, s1), (b2, s2) in itertools.pairwise(seen))
    assert seen[-1][0] == pytest.approx(2.0) and seen[-1][1] < 0.08
    # the depth subscriber: LFO 2's push on the fx mix scales with the knob
    mix = reg["fx.mix"]
    mix.set_norm(0.5)                       # room to push either way
    router.feed("lfo", [0.5, 1.0])
    router.rests["lfo"] = [0.5, 0.5]
    pushes = []
    for m in (0.0, 1.0):
        knob.set_norm(m)
        router.modulate()
        reg.apply()
        pushes.append(mix.eff_norm - mix.norm)
    assert pushes[0] == pytest.approx(0.0, abs=1e-9) and pushes[1] > 0.1


def test_a_load_tells_the_listeners_its_name(rig):
    """Plan 14 WP1: app.py listens to every preset load (a preset that turns
    the dream on with no worker is a banner); a listener that raises is a
    note, never a failed load."""
    heard: list = []
    rig.presets.listeners.append(heard.append)
    rig.presets.listeners.append(lambda name: 1 / 0)
    name = rig.lib.list("presets")[0]
    assert rig.presets.load(name) == []
    assert heard == [rig.lib.current("presets")]
    assert rig.lib.warning.startswith("preset listener: ZeroDivisionError")
    assert not rig.presets.note.startswith("preset listener")   # the preset's own note

