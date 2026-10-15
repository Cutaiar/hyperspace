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
import math
import re
from types import SimpleNamespace

import pytest
from conftest import (
    OWNER_KNOB,
    OWNER_PAD,
    boot_home,
    far_pads,
    old_shape_pads,
    opened_last,
)
from test_plan12_presets import DictSource, NullOut, feats, hold, offset

from hyperspace import apc40, lfo, preset, routing, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.library import F_KEYS, FACTORY, SLOTS, Library, LibraryError, bank_doc
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
    # the table before attach, as app.main reads it: the desk's session
    # param (`desk.slew`) is the table's and exists when the show lands
    table = Bindings.load(bindings_path(home), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = Router(reg, table)
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
    and the master dim (plan 15 WP3), through a preset load and a show load.
    Knob smoothing too (`desk.slew`, plan 18 WP2): no preset moves it, a
    show that does not name it leaves it, and a show save and load
    round-trips it."""
    from hyperspace.overlay import Output

    reg, control = rig.reg, rig.control
    out = Output(None, None)
    out.register(reg)
    reg["output.dim"].set(0.4)
    assert part_of(reg["output.dim"]) == "session"
    reg["tempo.bpm"].set(100.0)
    reg["master.gain"].set(2.0)
    reg["band.0.atk"].set(0.3)
    slew = reg["desk.slew"]
    slew.set(0.12)
    assert part_of(slew) == "session" and rig.router.table.slew == 0.12
    scene = control.scene
    put(rig.home, "FAST", values={"view.shape": 5, "tempo.bpm": 140.0, "desk.slew": 0.2,
                                  "scene.select": (scene + 1) % 3, "output.dim": 1.0})
    before = reg.snapshot(part="session")
    assert before["desk.slew"] == 0.12
    rig.presets.load("FAST")
    assert slew.value == 0.12 and "desk.slew is the session's, ignored" in rig.presets.notes
    assert rig.view.shape == 5
    assert rig.clock.bpm == 100.0 and rig.chain.gain == 2.0 and rig.chain.params[0].atk == 0.3
    assert control.scene == scene and reg.snapshot(part="session") == before
    assert out.dim == 0.4 and "output.dim is the session's, ignored" in rig.presets.notes
    rig.presets.load("TRIP")                          # the factory party preset, too
    assert rig.clock.bpm == 100.0 and reg.snapshot(part="session") == before
    assert out.dim == 0.4
    rig.lib.project.load("party")                     # a show load, startup preset and all
    assert rig.lib.current("presets") == "TUMBLE" and out.dim == 0.4
    assert slew.value == 0.12                         # the factory show names no smoothing
    rig.lib.project.save("mine")                      # a show keeps the number
    assert rig.lib.project.session["desk.slew"] == 0.12
    slew.set(0.03)
    rig.lib.project.load("mine")
    assert slew.value == 0.12 and not rig.lib.project.is_dirty()


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

def test_a_step_or_cycle_on_the_bank_skips_empty_slots(rig):
    """Audit R14: `preset.select` has twenty-four choices and most are
    empty. A learned step or toggle row walks the filled slots only: a step
    stops at the last filled one, a cycle wraps to the first; nothing ever
    lands on an empty slot. Setting a slot outright is unchanged."""
    pr, select = rig.lib.project, rig.reg["preset.select"]
    pr.put_slot(12, pr.bank[2])                   # F1–F8 filled, and slot 13
    filled = [k for k in range(SLOTS) if select.has(k)]
    assert filled == [*range(F_KEYS), 12]
    select.set(6)
    select.step(1)
    assert select.value == 7
    select.step(1)
    assert select.value == 12                     # over slots 9–12, not onto slot 9
    select.step(1)
    assert select.value == 12                     # the last filled: a step stays
    select.cycle(1)
    assert select.value == 0                      # a cycle wraps to the first filled
    select.cycle(-1)
    assert select.value == 12
    select.step(-2)
    assert select.value == 6
    select.step(3)
    assert select.value == 12
    assert pr.active == 12 and rig.lib.current("presets") == pr.bank[12]


def test_the_bank_names_the_house_presets(rig):
    pr = rig.lib.project
    # plan 19 WP1: twenty-four slots; the house show fills the F-keys' eight
    assert len(pr.bank) == SLOTS == 24 and pr.bank[0] == "BIG BLUE WAVE"
    eight = pr.bank[:F_KEYS]
    assert len(set(eight)) == F_KEYS and all(rig.lib.is_factory("presets", n) for n in eight)
    assert pr.bank[F_KEYS:] == [None] * (SLOTS - F_KEYS)
    select = rig.reg["preset.select"]
    assert select.names == eight + [f"SLOT {k + 1}" for k in range(F_KEYS, SLOTS)]
    assert [select.has(k) for k in range(SLOTS)] == [True] * F_KEYS + [False] * (SLOTS - F_KEYS)


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
    for _ in range(F_KEYS - 4):                            # the house show fills eight
        pr.cycle()
    assert pr.active == F_KEYS - 1
    pr.cycle()
    assert pr.active == 0                                  # wraps past the empty far slots
    pr.cycle(-1)
    assert pr.active == F_KEYS - 1                         # and backwards
    pr.put_slot(19, "WAKE")                                # a far slot is in the round
    pr.cycle()
    assert pr.active == 19 and rig.lib.current("presets") == "WAKE"
    pr.cycle()
    assert pr.active == 0


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
    assert doc["schema"] == "hyperspace.project/2"
    assert doc["bank"] == pr.bank[:F_KEYS] == bank_doc(pr.bank)     # eight in the file
    # an empty slot: a new name, made unique against what is there
    put(home, "PRESET 8")
    pr.bank[6] = pr.bank[7] = None
    reg["preset.save.6"].fire()
    reg["preset.save.7"].fire()
    assert pr.bank[6] == "PRESET 7" and pr.bank[7] == "PRESET 8 (2)"
    assert (home / "presets" / "preset-7.json").is_file()
    assert (json.loads((home / "projects" / "house.hyp.json").read_text())["bank"]
            == bank_doc(pr.bank))
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


# ---------------------------------------------------------------- home (plan 15 WP2)

def test_home_loads_what_the_show_starts_on(rig):
    """Decision 27: `preset.home` loads the show's "starts on" preset —
    from another preset, with unsaved edits, and it is a load like any
    other (D2): the values, the routes, the desk, the bank's light, a
    clean dot. A "starts on" picked later is where home goes next."""
    reg, lib, proj = rig.reg, rig.lib, rig.lib.project
    home = reg["preset.home"]
    assert (home.group, home.label, home.modulatable, home.persist) \
        == ("preset", "Home", True, False)
    assert proj.startup == "BIG BLUE WAVE" and home.get() is True      # lit: there is one
    launched = (reg.snapshot(part="performance"),
                [b.to_json() for b in rig.router.table.routes()],
                [b.to_json() for b in rig.router.table.desk()])
    reg["preset.load.2"].fire()
    reg["view.bright"].set_value(reg["view.bright"].value + 1.0)       # an unsaved edit
    assert lib.current("presets") == "STROBE CAGE" and lib.is_dirty("presets")
    assert proj.active == 2 and rig.view.shape != 17
    home.fire()
    assert lib.current("presets") == "BIG BLUE WAVE" and not lib.is_dirty("presets")
    assert proj.active == 0 and rig.view.shape == 17 and not lib.warning
    assert (reg.snapshot(part="performance"),
            [b.to_json() for b in rig.router.table.routes()],
            [b.to_json() for b in rig.router.table.desk()]) == launched
    # home follows "starts on": no pointer of its own
    proj.startup = "STROBE CAGE"
    home.fire()
    assert lib.current("presets") == "STROBE CAGE" and proj.active == 2
    # a "starts on" whose file is gone says so, as a launch does, and loads nothing
    proj.startup = "GONE"
    home.fire()
    assert lib.warning == "startup: no preset 'GONE'"
    assert lib.current("presets") == "STROBE CAGE"


def test_home_with_no_starts_on_says_so_and_loads_nothing(rig):
    reg, lib, proj = rig.reg, rig.lib, rig.lib.project
    reg["preset.load.2"].fire()
    reg["view.bright"].set_value(reg["view.bright"].value + 1.0)
    before = reg.snapshot(part="performance")
    proj.startup = None
    assert reg["preset.home"].get() is False                           # dark: nothing to go to
    reg["preset.home"].fire()
    assert lib.warning == ("home: this show names no 'starts on' preset — "
                           "pick one on the PRESETS page")
    assert lib.current("presets") == "STROBE CAGE" and lib.is_dirty("presets")
    assert reg.snapshot(part="performance") == before and proj.active == 2
    proj.startup = "BIG BLUE WAVE"                                     # picked: home goes there,
    reg["preset.home"].fire()                                          # and the note is gone
    assert lib.current("presets") == "BIG BLUE WAVE" and lib.warning == ""


def test_home_is_one_undo_step(tmp_path):
    """Home is one step under its own label — the push `Presets.load_doc`
    makes inside it is the same frame's and adds none — and one undo
    brings the look that was up back whole, its unsaved edit included;
    redo goes home again. A home that loads nothing leaves no step."""
    from test_undo import boot as undo_boot
    from test_undo import frames, labels, look, same_look, settle

    r = undo_boot(tmp_path / "home")                   # the party show: starts on TUMBLE
    reg, lib, proj = r.reg, r.lib, r.lib.project
    reg["preset.load.4"].fire()                        # TRIP
    settle(r)
    reg["view.bright"].step(7)                         # an unsaved edit of TRIP
    settle(r)
    trip = look(r)
    assert lib.current("presets") == "TRIP" and lib.is_dirty("presets")
    r.undo.clear()
    reg["preset.home"].fire()
    assert len(r.undo.stack) == 1                      # at once: the inner push opened none
    settle(r)
    assert labels(r) == ["home → TUMBLE"]
    assert lib.current("presets") == "TUMBLE" and proj.active == 0
    tumble = look(r)
    assert not same_look(tumble, trip)
    assert r.undo.undo() and r.undo.status == "undid home → TUMBLE"
    assert same_look(look(r), trip)
    assert lib.current("presets") == "TRIP" and lib.is_dirty("presets") and proj.active == 4
    frames(r, 5)
    assert same_look(look(r), trip) and r.undo.stack == []
    assert r.undo.redo() and r.undo.status == "redid home → TUMBLE"
    assert same_look(look(r), tumble) and lib.current("presets") == "TUMBLE"
    settle(r)
    # nothing to go home to, or a "starts on" with no file: no step
    r.undo.clear()
    for name in (None, "GONE"):
        proj.startup = name
        reg["preset.home"].fire()
        settle(r)
        assert r.undo.stack == [] and lib.current("presets") == "TUMBLE"


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

# (scene launch 5: 1–4 are the invariant render toggles since plan 24 C1)
DESK = [{"source": "cc:*:16", "target": "view.speed", "op": "abs", "feedback": "ring"},
        {"source": "note:0:86", "target": "view.points", "op": "toggle", "feedback": "led"}]
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
        # MASTER: invariant (the track faders are layered since plan 24 C2)
        desk=[*DESK, {"source": "cc:0:14", "target": "view.bright", "op": "abs"}],
        macros=MACROS)
    rig.presets.load("DESKED")
    assert preset.desk_json(table.desk()) == DESK and table.layer == "preset"
    assert any("cc:0:14 → view.bright" in n and "invariant" in n for n in rig.presets.notes)
    assert rig.presets.desk_notes and "cc:0:14" in rig.presets.desk_notes[0]
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
    (None: no key), else the factory files' layer (`file_desk`, plan 24 C1)."""
    spec = preset.FACTORY_PRESETS.get(slug)
    desk = preset.file_desk if spec is None else spec.desk
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
            assert routing.is_continuous(b.scheme) and b.op in routing.MOD_OPS, (path.name, row)
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
    # plan 24 C1: the generator writes `file_desk` — the fresh desk plus
    # the four render toggles, invariant now, which the factory files keep
    # (decision 23: no library file is rewritten) and a load drops quietly
    desk = preset.desk_json(preset.file_desk())
    assert desk and all("layer" not in d for d in desk)
    # plan 19 WP2: the sixteen shape pads left the fresh desk (42 rows → 26)
    # and no factory file maps a pad of clip rows 4 or 5 — they are the bank's;
    # plan 19 WP3: SCENE on device knobs 1–4 (26 → 30)
    assert len(desk) == 30 and not _on_bank_rows(desk)
    from_map = []
    for d in apc40.DEFAULT_MAP:
        if d.get("layer") == "preset" or d["target"] in apc40.TOGGLES:
            row = Binding.from_json(d).to_json()
            row.pop("layer", None)
            from_map.append(row)
    assert desk == from_map
    fresh = preset.desk_json(preset.fresh_desk())
    assert fresh == [d for d in desk if d["target"] not in apc40.TOGGLES] and len(fresh) == 26
    paths = sorted(preset.FACTORY_DIR.glob("*.json"))
    # 8 house, 9 party, 5 made from routing presets, plan 18's hands-orbit
    assert len(paths) == 23
    for path in paths:
        doc = json.loads(path.read_text())
        want = expected_desk(path.stem)
        if want is None:
            assert "desk" not in doc, path.name
        else:
            assert doc["desk"] == want, path.name
            assert not _on_bank_rows(doc["desk"]), path.name
    knobs = [f"cc:*:{0x10 + k}" for k in range(8)]
    rest = [d for d in desk if d["source"] not in knobs]       # the fresh layer less its knobs
    # plan 19 WP3: every factory preset's device knobs, D1–D8, as the plan's
    # table has them (None: dark). A file with no `desk` key gets the fresh layer
    scene = ("view.depth4", "camera.yaw", "camera.pitch", "view.pattern", None, None, None, None)
    table = {
        **{s: scene for s in ("big-blue-wave", "ember-orbit", "hex-engine", "inverse-halo",
                              "plasma-heart", "spiral-silk", "strobe-cage", "woven-lattice",
                              "party-tumble", "party-faces", "party-field",
                              "legacy6", "hands-play", "hands-orbit")},
        "hands-fx": ("fx.mix", "fx.acid.bend", "fx.acid.twist", "fx.acid.reach",
                     "fx.acid.breathe", "fx.acid.speed", "view.depth4", "camera.yaw"),
        "hands-pinch": ("fx.mix", "fx.huecycle.paint", "fx.huecycle.spread", "view.depth4",
                        "camera.yaw", "camera.pitch", "view.pattern", None),
        "lfo-breathe": ("macro.1", "fx.mix", "fx.plasma.level", "lfo.1.depth", "view.depth4",
                        "camera.yaw", "camera.pitch", None),
        "party-wake": preset.WAKE_KNOBS, "party-trip": preset.TRIP_KNOBS,
        "party-acid": preset.ACID_KNOBS, "party-mandala": preset.MANDALA_KNOBS,
        "party-noita": preset.NOITA_KNOBS, "party-tracer": preset.TRACER_KNOBS}
    assert set(table) == {p.stem for p in paths}
    # the six that already had eight are as plan 12 §6 and plan 14 left them
    assert preset.WAKE_KNOBS[:2] == ("dream.echo_mix", "dream.fade")
    assert preset.TRIP_KNOBS[0] == preset.ACID_KNOBS[0] == "fx.mix"
    assert preset.TRACER_KNOBS[-1] == "view.depth4"
    inv = routing.Bindings.factory()
    for path in paths:
        doc = json.loads(path.read_text())
        rows = doc.get("desk") or desk
        dial = dict.fromkeys(knobs)
        for d in rows:
            if d["source"] in knobs:
                assert (d["op"], d["feedback"]) == ("abs", "ring"), path.name
                dial[d["source"]] = d["target"]
        assert tuple(dial.values()) == tuple(table[path.stem]), path.name
        # the rest is the fresh layer's, in its order, the knobs after it
        assert [d for d in rows if d["source"] not in knobs] == rest, path.name
        # one row per control, and none on an invariant one but the four
        # render toggles a load drops quietly (plan 24 C1, decision 23)
        assert len({d["source"] for d in rows}) == len(rows), path.name
        assert [(d["source"], d["target"], d["op"], 1.0) for d in rows
                if inv.is_invariant(Binding.from_json({**d, "layer": "preset"}))] \
            == sorted(routing.TOGGLE_DESK_ROWS), path.name
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
    for name in ("legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play",
                 "hands-orbit"):                         # plan 18 WP4's, made the same way
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


# ------------------------------------------- plan 18 WP4: two hands on the camera

ORBIT = "hands-orbit"
ORBIT_ROWS = [("hand:right.x", "camera.yaw", 0.5), ("hand:right.pitch", "camera.pitch", 0.25),
              ("hand:left.x", "camera.pan.x", 0.1), ("hand:left.z", "camera.pan.y", 0.1),
              ("hand:left.y", "camera.zoom", 0.12)]      # not the plan's 0.3: 7.4× blacked the frame
# a camera the mouse moved before the hands came in: a scene-setter's bases
MOUSE = {"camera.yaw": 0.5, "camera.pitch": -0.2, "camera.zoom": 1.6,
         "camera.pan.x": 120.0, "camera.pan.y": -60.0}


def orbit(rig, mouse: dict | None = None):
    """`hands-orbit` loaded through the one loader, the camera then moved as
    the mouse moves it (bases), and two fake hands on the real hand chain
    (test_plan12_presets' harness: default feel, default ranges, no box)."""
    assert rig.presets.load(ORBIT) == [] and rig.presets.notes == []
    assert rig.router.table.dropped == []
    for pid, v in (mouse or {}).items():
        rig.reg[pid].set(v)
    src = DictSource()
    io = HandsIO(HandSettings.from_config(), {"enabled": True}, source=src, out=NullOut(),
                 clock=lambda: src.t)
    return src, io


def camera(rig) -> dict[str, float]:
    """The five camera params as the picture has them (effective)."""
    return {pid: rig.reg[pid].value for pid in MOUSE}


def test_hands_orbit_is_five_pushes_onto_the_camera(rig):
    """Plan 18 WP4 (fork 17 (a)): `hands-orbit` is five rows and nothing
    else — each a push, from a default hand axis named by axis, onto a
    real `camera.*` param, one performer per target, no pinch gate, no
    values, no desk key, no macro. It is a factory preset in the list, on
    no show's F-key; its file is the generator's; loaded on the default
    rig its five routes all stand."""
    routes = preset.hands_orbit_routes()
    assert [(b.source, b.target, b.value) for b in routes] == ORBIT_ROWS
    axes = {preset.hand(s, a) for s in "LR" for a in preset.HAND_AXES}
    for b in routes:
        p = rig.reg[b.target]
        assert b.target.startswith("camera.") and p.modulatable, b
        assert b.op == "push" and b.source in axes and b.when is None and b.scale is None, b
        assert b.is_performer and b.rest is None, b      # from the axis's own rest
    assert len({b.target for b in routes}) == len({b.source for b in routes}) == 5
    assert routing.referee(routes)[1] == []
    spec = preset.FACTORY_PRESETS[ORBIT]
    assert spec.routes is preset.hands_orbit_routes and spec.desk is None
    doc = json.loads((preset.FACTORY_DIR / f"{ORBIT}.json").read_text())
    assert doc == preset.generated(ORBIT)
    assert doc["values"] == {} and doc["macros"] == {} and "desk" not in doc
    assert rig.lib.is_factory("presets", ORBIT) and ORBIT in rig.lib.list("presets")
    for show in (FACTORY / "projects").glob("*.hyp.json"):
        proj = json.loads(show.read_text())
        # a bank names presets by name, in whatever case the show wrote it
        named = {preset.slug(n) for n in [*proj["bank"], proj.get("startup")] if n}
        assert named and preset.slug(doc["name"]) == ORBIT and ORBIT not in named, show.name
    orbit(rig)
    assert [b.to_json() for b in rig.router.table.routes()] == doc["routes"]
    assert [rig.router.table.owner(t).source for _, t, _ in ORBIT_ROWS] == \
        [s for s, _, _ in ORBIT_ROWS]


def test_an_absent_or_level_hand_leaves_the_orbit_camera_alone(rig):
    """Plan 12's rule for a hand row: no hand, and both hands in at rest
    (level, centred, at the bottom of the height range), add nothing — the
    camera stays exactly where the mouse left it, and the bases are never
    written."""
    src, io = orbit(rig, MOUSE)
    hold(rig, rig.router, src, io, {}, 10)
    assert camera(rig) == pytest.approx(MOUSE, abs=1e-9)
    assert not any(rig.reg[pid].modulated for pid in MOUSE)
    hold(rig, rig.router, src, io, {"left": feats("left"), "right": feats("right")})
    assert camera(rig) == pytest.approx(MOUSE, abs=1e-6)
    for pid, left_at in MOUSE.items():
        assert offset(rig.reg[pid]) == pytest.approx(0, abs=1e-6), pid
        assert rig.reg[pid].base == pytest.approx(left_at), pid
    # one hand alone at rest is the same
    for side in ("left", "right"):
        hold(rig, rig.router, src, io, {side: feats(side)})
        assert camera(rig) == pytest.approx(MOUSE, abs=1e-6), side


def test_each_orbit_axis_moves_its_camera_param_as_its_row_says(tmp_path):
    """Each row's axis swept across its range from the default camera: at
    rest the param is its base; the ends are what the depth says — the
    yaw a quarter turn each way, the pitch ±45° (an eighth of the whole
    turn it wraps over since 2026-10-14; ±44° of its old ±1.55), each pan
    ±400 px, the zoom up from 1× to 800^0.12 = 2.23× at the top and never
    below the base; the move is monotonic; no other camera param moves;
    the hand leaving brings the base back."""
    ends = {"camera.yaw": (-math.pi / 2, math.pi / 2),
            "camera.pitch": (-math.pi / 4, math.pi / 4),
            "camera.pan.x": (-400.0, 400.0), "camera.pan.y": (-400.0, 400.0),
            "camera.zoom": (1.0, 2.23)}                  # 800 ** 0.12, as measured
    assert math.degrees(ends["camera.pitch"][1]) == pytest.approx(45.0)
    for k, (source, target, depth) in enumerate(ORBIT_ROWS):
        side, axis = source.split(":")[1].split(".")
        seen = []
        for u in (0.0, 0.25, 0.5, 0.75, 1.0):
            r = boot(tmp_path / f"{k}-{u}")
            src, io = orbit(r)
            p = r.reg[target]
            base = camera(r)
            hold(r, r.router, src, io, {side: feats(side, **{axis: u})})
            seen.append(p.value)
            assert offset(p) == pytest.approx(depth * (u - (0.0 if axis == "y" else 0.5)),
                                              abs=0.02), (source, u)
            for other in MOUSE:
                if other != target:
                    assert r.reg[other].value == pytest.approx(base[other], abs=1e-6), \
                        (source, u, other)
                    assert offset(r.reg[other]) == pytest.approx(0, abs=1e-6), (source, other)
        rest = 0 if axis == "y" else 2
        assert seen[rest] == pytest.approx(base[target], abs=1e-6), (source, seen)
        tol = 2e-3 * (p.hi - p.lo)
        assert seen[0] == pytest.approx(ends[target][0], abs=tol), (source, seen)
        assert seen[-1] == pytest.approx(ends[target][1], rel=0.02, abs=tol), (source, seen)
        assert all(b > a - 1e-9 for a, b in itertools.pairwise(seen)), (source, seen)
        assert seen[-1] > seen[0]
        hold(r, r.router, src, io, {})                   # the hand at u = 1 leaves
        assert p.value == pytest.approx(base[target], abs=tol) and not p.modulated, source
        assert p.base == pytest.approx(base[target]), source


def test_the_orbit_hands_leaving_return_the_camera_to_where_the_mouse_left_it(rig):
    """Both hands at an end of every axis push all five params off a camera
    the mouse had moved; both hands out, each is back on the mouse's value
    and no row holds it. The mouse's bases were never written by a hand."""
    src, io = orbit(rig, MOUSE)
    hands = {"right": feats("right", x=1.0, pitch=1.0),
             "left": feats("left", x=0.0, z=1.0, y=1.0)}
    hold(rig, rig.router, src, io, hands)
    played = camera(rig)
    for pid, sign in (("camera.yaw", 1), ("camera.pitch", 1), ("camera.pan.x", -1),
                      ("camera.pan.y", 1), ("camera.zoom", 1)):
        assert sign * (played[pid] - MOUSE[pid]) > 0.1, (pid, played)
        assert rig.reg[pid].modulated and rig.reg[pid].base == pytest.approx(MOUSE[pid]), pid
    assert played["camera.yaw"] == pytest.approx(MOUSE["camera.yaw"] + math.pi / 2, abs=0.02)
    hold(rig, rig.router, src, io, {})
    assert camera(rig) == pytest.approx(MOUSE, abs=1e-3)
    assert not any(rig.reg[pid].modulated for pid in MOUSE)



# ------------------------------------------- plan 15 WP4: save-as from the desk

def fill_far(pr, name: str = "WAKE") -> None:
    """Every empty slot past the F-keys pointed at `name`: a bank with no
    room there (the show is written, as any slot change writes it)."""
    for k in range(F_KEYS, len(pr.bank)):
        if pr.bank[k] is None:
            pr.put_slot(k, name)


def party(tmp_path, full: bool = True):
    """The party show on a fresh home, slot 6 (ACID) emptied, TRIP loaded.
    `full`: slots 10–24 filled too, so the F-keys' holes are the only room
    (the tests written on the bank of eight)."""
    r = boot(tmp_path, None)
    pr = r.lib.project
    assert pr.bank == ["TUMBLE", "FACES", "FIELD", "WAKE", "TRIP", "ACID", "MANDALA", "NOITA",
                       "TRACER"] + [None] * 15
    if full:
        fill_far(pr)
    pr.clear_slot(5)
    r.reg["preset.load.4"].fire()
    assert r.lib.current("presets") == "TRIP" and pr.active == 4
    return r


def user_presets(home):
    return sorted(p.name for p in (home / "presets").glob("*.json"))


def test_save_new_never_overwrites(tmp_path):
    """Decision 29: the desk's save-as makes a new file every time. The
    made name's slug is free among the file stems of both preset folders
    (a user file with a factory file's stem would hide that preset), the
    listed names and the bank's names — so nothing is written over and no
    factory preset is shadowed, whatever the files are called inside."""
    import shutil

    r = party(tmp_path)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    # a factory folder with one more file: its stem is trip-4, its name is not
    factory = tmp_path.parent / f"{tmp_path.name}-factory"
    shutil.copytree(FACTORY, factory)
    (factory / "presets" / "trip-4.json").write_text(
        (FACTORY / "presets" / "party-wake.json").read_text().replace('"WAKE"', '"FOUR"', 1))
    lib.factory = factory
    assert lib.is_factory("presets", "FOUR")
    # the user's folder: trip-2.json under another name, a "TRIP 3" in a
    # file of another stem; and the bank names a "TRIP 5" that has no file
    two = put(home, "SOMETHING ELSE").rename(home / "presets" / "trip-2.json")
    three = put(home, "TRIP 3").rename(home / "presets" / "mine.json")
    kept = {p: p.read_bytes() for p in (two, three, factory / "presets" / "trip-4.json")}
    pr.bank[5] = "TRIP 5"
    pr.clear_slot(6)
    before = user_presets(home)
    reg["view.shape"].set(9)
    reg["preset.save_new"].fire()
    assert lib.current("presets") == "TRIP 6" and pr.bank[6] == "TRIP 6"
    assert user_presets(home) == sorted([*before, "trip-6.json"])
    assert all(p.read_bytes() == was for p, was in kept.items())
    assert lib.is_factory("presets", "FOUR") and lib.is_factory("presets", "TRIP")
    assert lib.read("presets", "TRIP")["values"]["view.shape"] != 9     # TRIP itself untouched
    assert json.loads((home / "presets" / "trip-6.json").read_text())["values"]["view.shape"] == 9
    assert not (home / "trash").exists()                    # nothing was replaced
    # held again and again: a new file each time, never the same one twice
    for n in (7, 8, 9):
        reg["preset.save_new"].fire()
        assert lib.current("presets") == f"TRIP {n}"
    assert user_presets(home) == sorted([*before, *[f"trip-{n}.json" for n in (6, 7, 8, 9)]])
    assert not (home / "trash").exists()
    # a file stem in another case is the same file on a filesystem that
    # folds case (this rig's): it counts too (review of PR #87)
    ten = put(home, "SUNSET").rename(home / "presets" / "Trip-10.json")
    was = ten.read_bytes()
    assert reg["preset.save_new"].fire() is True
    assert lib.current("presets") == "TRIP 11" and ten.read_bytes() == was
    assert "SUNSET" in lib.list("presets") and not (home / "trash").exists()
    # no preset loaded at all: PRESET 1, then PRESET 2
    lib._landed("presets", None, None)
    reg["preset.save_new"].fire()
    assert lib.current("presets") == "PRESET 1"
    reg["preset.save_new"].fire()
    assert lib.current("presets") == "PRESET 2"


def test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_preset(tmp_path):
    """The bank, the show's file, what is loaded and its clean dot: the new
    preset takes the first empty slot, the show is written at once (the
    factory show's first write makes your copy), and — as the panel's
    "as…" does — the new preset is the loaded one, so a second save counts
    on and Save on the panel writes the new file, not TRIP."""
    r = party(tmp_path)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    show = home / "projects" / "party.hyp.json"
    assert pr.next_empty() == 5
    pr.clear_slot(1)                                         # two holes: the first is taken first
    assert pr.next_empty() == 1
    reg["view.bright"].set(reg["view.bright"].value + 0.5)
    assert lib.is_dirty("presets")
    reg["preset.save_new"].fire()
    assert pr.bank[1] == "TRIP 2" and pr.active == 1 and pr.bank[4] == "TRIP"
    assert lib.current("presets") == "TRIP 2" and not lib.is_dirty("presets")
    assert lib.status == "saved TRIP 2 → F2" and pr.bank_error == ""
    assert json.loads(show.read_text())["bank"] == bank_doc(pr.bank) and not pr.is_dirty()
    assert reg["preset.select"].names[1] == "TRIP 2" and reg["preset.select"].value == 1
    assert not lib.is_factory("presets", "TRIP 2") and lib.is_factory("presets", "TRIP")
    doc = lib.read("presets", "TRIP 2")
    assert doc["name"] == "TRIP 2" and doc["values"]["view.bright"] == reg["view.bright"].value
    # the second counts on from the new one, into the next hole
    reg["preset.save_new"].fire()
    assert pr.bank[5] == "TRIP 3" and pr.active == 5 and lib.current("presets") == "TRIP 3"
    assert lib.status == "saved TRIP 3 → F6"
    assert json.loads(show.read_text())["bank"] == bank_doc(pr.bank)
    assert pr.next_empty() is None
    # the trigger is a session-side control: never saved, never performed
    p = reg["preset.save_new"]
    assert (p.group, p.persist, p.modulatable) == ("preset", False, False)
    # a launch finds the bank as it was left
    again = boot(home, None)
    assert again.lib.project.bank == pr.bank


def test_save_new_on_a_full_bank_saves_to_the_list_and_says_so(tmp_path):
    """A full bank: the preset is still made and loaded, it is in the
    list, the bank and the show's file are untouched, no pad is lit, and
    the warning says where it went — every time it happens."""
    r = boot(tmp_path, None)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    fill_far(pr)                                 # (plan 19 WP1: the party show has 15 empty)
    reg["preset.load.4"].fire()
    bank = list(pr.bank)
    assert pr.next_empty() is None
    shows = sorted(p.name for p in (home / "projects").iterdir())
    reg["preset.save_new"].fire()
    assert lib.warning == "saved TRIP 2 — the bank is full: it is in the preset list"
    assert pr.bank == bank and sorted(p.name for p in (home / "projects").iterdir()) == shows
    assert "TRIP 2" in lib.list("presets") and lib.current("presets") == "TRIP 2"
    assert pr.active == -1 and reg["preset.select"].value == -1
    assert not lib.is_dirty("presets") and not pr.is_dirty()
    said = dict(lib.said)
    reg["preset.save_new"].fire()
    assert lib.warning == "saved TRIP 3 — the bank is full: it is in the preset list"
    assert lib.said["warning"] == said["warning"] + 1
    # room made: the next save lands in it, and the old warning goes
    pr.clear_slot(2)
    assert lib.warning == ""
    reg["preset.save_new"].fire()
    assert pr.bank[2] == "TRIP 4" and lib.status == "saved TRIP 4 → F3" and lib.warning == ""
    # a disk that will not take the file: said, and the show goes on
    def full(*a, **k):
        raise LibraryError("disk full")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(lib, "save_as", full)
        pr.clear_slot(3)
        assert reg["preset.save_new"].fire() is False        # nothing saved: said so
    assert "disk full" in pr.bank_error and pr.bank[3] is None
    # the preset saves but the show's file will not take the bank: the
    # slot stays as the file has it, no pad is lit, and it is said
    # (review of PR #87)
    show = home / "projects" / "party.hyp.json"
    before, cur = show.read_text(), lib.current("presets")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pr, "write", full)
        assert reg["preset.save_new"].fire() is True
    name = lib.current("presets")
    assert name != cur and name in lib.list("presets")
    assert pr.bank[3] is None and pr.active == -1 and show.read_text() == before
    assert "disk full" in pr.bank_error and not pr.is_dirty()
    # the footer says why (plan 19 WP1: a show that cannot be backed up says so here)
    assert lib.warning == (f"saved {name} — the show could not be written: it is in the "
                           "preset list (disk full)")
    reg["preset.save_new"].fire()                            # the disk is back: F4, and no error
    assert pr.bank[3] == lib.current("presets") and pr.bank_error == ""


def test_the_new_slot_loads_from_the_preset_row(tmp_path):
    """The pad over the new slot is an ordinary preset pad: clip row 1's
    button k loads what the save-as put there."""
    from test_midi import FakeIn, FakeOut, note, push

    from hyperspace.midi import MidiIO

    r = party(tmp_path)
    lib, reg, pr = r.lib, r.reg, r.lib.project
    inp, out = FakeIn(), FakeOut()
    desk = SimpleNamespace(midi=MidiIO(reg, r.router.table, inp=inp, out=out), inp=inp, out=out)
    reg["view.shape"].set(11)
    reg["preset.save_new"].fire()
    assert pr.bank[5] == "TRIP 2" and pr.active == 5
    push(desk, note(apc40.N_CLIP[0], channel=0), note(apc40.N_CLIP[0], 0, channel=0))
    assert lib.current("presets") == "TUMBLE" and pr.active == 0
    assert reg["view.shape"].value != 11
    push(desk, note(apc40.N_CLIP[0], channel=5), note(apc40.N_CLIP[0], 0, channel=5))
    assert lib.current("presets") == "TRIP 2" and pr.active == 5
    assert reg["view.shape"].value == 11 and not lib.is_dirty("presets")
    leds = [m.velocity for m in out.sent
            if m.type == "note_on" and m.note == apc40.N_CLIP[0] and m.channel == 5]
    assert leds[-1] == apc40.GREEN
    reg["preset.load.5"].fire()                              # and F6 is the same slot
    assert lib.current("presets") == "TRIP 2"


def test_put_and_clear_slot_write_the_show_and_delete_no_file(tmp_path):
    """The PRESETS page's two slot items: "put preset here…" points a slot
    at any preset, "clear slot" empties it. Both write the show at once,
    neither writes, moves or deletes a preset file, and the lit slot
    follows the loaded preset."""
    r = boot(tmp_path, None)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    show = home / "projects" / "party.hyp.json"
    assert pr.factory and not show.exists()
    put(home, "MINE")
    files = user_presets(home)
    assert lib.current("presets") == "TUMBLE" and pr.active == 0
    pr.clear_slot(5)
    assert pr.bank[5] is None and json.loads(show.read_text())["bank"][5] is None
    assert json.loads(show.read_text())["bank"] == bank_doc(pr.bank)
    assert not pr.factory and not pr.is_dirty()             # your copy, written
    assert lib.status == "F6: cleared — ACID is still in the preset list"
    assert "ACID" in lib.list("presets") and lib.is_factory("presets", "ACID")
    pr.put_slot(5, "MINE")
    assert pr.bank[5] == "MINE" and json.loads(show.read_text())["bank"][5] == "MINE"
    assert lib.status == "F6: MINE" and lib.current("presets") == "TUMBLE" and pr.active == 0
    reg["preset.load.5"].fire()
    assert lib.current("presets") == "MINE" and pr.active == 5
    # the loaded preset's slot cleared: no pad lit; put back elsewhere: that one
    pr.clear_slot(5)
    assert pr.active == -1 and lib.current("presets") == "MINE"
    pr.put_slot(2, "MINE")
    assert pr.bank[2] == "MINE" and pr.active == 2
    # the slot of the loaded preset pointed elsewhere: its light goes
    pr.put_slot(2, "WAKE")
    assert pr.active == -1
    # a preset may sit in two slots; the light stays where it is
    reg["preset.load.3"].fire()
    pr.put_slot(7, "WAKE")
    assert pr.bank[3] == pr.bank[7] == "WAKE" and pr.active == 3
    # nothing loaded: no slot is lit — an empty slot least of all (review of PR #87)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(lib, "current", lambda group: None)
        pr.clear_slot(6)
        assert pr.bank[6] is None and pr.active == -1
        pr.put_slot(6, "MANDALA")
        assert pr.active == -1
    # a name with no file, a slot that is not there, an empty slot: nothing changes
    before, bank = show.read_text(), list(pr.bank)
    pr.put_slot(1, "NOPE")
    assert lib.warning == "F2: no preset 'NOPE'" and pr.bank == bank
    pr.put_slot(len(pr.bank), "WAKE")
    pr.clear_slot(-1)
    pr.clear_slot(5)
    assert pr.bank == bank and show.read_text() == before
    assert json.loads(show.read_text())["bank"] == bank_doc(pr.bank)
    assert user_presets(home) == files and not (home / "trash").exists()


def test_the_bank_calls_are_no_undo_step(tmp_path):
    """A save-as from the desk, a slot filled, a slot cleared: nothing live
    changes, so none of them is an undo step (plan 15 WP4)."""
    from test_undo import boot as undo_boot
    from test_undo import settle

    r = undo_boot(tmp_path / "home")
    reg, pr = r.reg, r.lib.project
    reg["preset.load.4"].fire()
    settle(r)
    r.undo.clear()
    pr.clear_slot(5)
    settle(r)
    reg["preset.save_new"].fire()
    settle(r)
    pr.put_slot(0, "WAKE")
    settle(r)
    assert pr.bank[5] == "TRIP 2" and pr.bank[0] == "WAKE"
    assert r.undo.stack == [] and not r.undo.undo()


def test_rename_and_trash_are_no_undo_step(tmp_path):
    """Plan 19 WP4 (§1 row 10): hide, unhide, rename (of the loaded preset
    too), × on yours, restore and empty write files and change nothing
    live, so none is an undo step — undo cannot put a file back; the
    trash is the net."""
    from test_undo import boot as undo_boot
    from test_undo import settle

    r = undo_boot(tmp_path / "home")
    reg, lib = r.reg, r.lib
    reg["preset.load.4"].fire()
    settle(r)
    reg["preset.save_new"].fire()                     # TRIP 2, yours, loaded
    settle(r)
    r.undo.clear()
    steps = []
    for fn, *args in ((lib.hide, "presets", "WAKE"), (lib.unhide, "presets", "WAKE"),
                      (lib.rename, "presets", "TRIP 2", "SUNRISE"),
                      (lib.delete, "presets", "SUNRISE")):
        fn(*args)
        settle(r)
        steps.append(len(r.undo.stack))
    (item,) = [t for t in lib.trash() if t.name == "SUNRISE"]
    lib.restore_trash(item)
    settle(r)
    lib.empty_trash()
    settle(r)
    steps.append(len(r.undo.stack))
    assert steps == [0, 0, 0, 0, 0] and not r.undo.undo()
    assert "SUNRISE" in lib.list("presets") and lib.trash() == []


# ------------------------------------------- plan 19 WP1: a bank of twenty-four

def test_save_new_lands_past_the_f_keys_and_a_full_bank_says_so(tmp_path):
    """The desk's save-as on the party show: F1–F8 and slot 9 are filled,
    so fifteen saves fill slots 10–24, each said by its slot; the sixteenth
    finds the bank full and saves to the list. A factory show's first
    write makes your copy: there is no eight-slot file of yours to keep,
    so no backup."""
    r = boot(tmp_path, None)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    show = home / "projects" / "party.hyp.json"
    reg["preset.load.4"].fire()
    assert lib.current("presets") == "TRIP" and pr.next_empty() == 9 and not show.exists()
    for n in range(15):
        assert reg["preset.save_new"].fire() is True
        assert pr.bank[9 + n] == f"TRIP {n + 2}" and pr.active == 9 + n
        assert lib.status == f"saved TRIP {n + 2} → slot {10 + n}"
        assert json.loads(show.read_text())["bank"] == bank_doc(pr.bank)
    assert pr.next_empty() is None and len(json.loads(show.read_text())["bank"]) == SLOTS
    assert reg["preset.select"].names[9:] == [f"TRIP {n}" for n in range(2, 17)]
    assert all(reg["preset.select"].has(k) for k in range(SLOTS))
    bank = list(pr.bank)
    assert reg["preset.save_new"].fire() is True
    assert lib.warning == "saved TRIP 17 — the bank is full: it is in the preset list"
    assert pr.bank == bank and "TRIP 17" in lib.list("presets") and pr.active == -1
    assert not list(home.rglob("*.bak-*")) and not pr.is_dirty()


def test_active_follows_the_loaded_preset_from_one_place(tmp_path):
    """`Project.follow` is the one spelling of "the lit slot follows the
    loaded preset": kept where it is while that slot still names it, else
    the first slot that names it, else none; none when nothing is loaded.
    A preset on two slots lights the one that was pressed."""
    import inspect

    from hyperspace import library

    r = boot(tmp_path, None)
    lib, reg, pr = r.lib, r.reg, r.lib.project
    pr.put_slot(13, "WAKE")                                # WAKE on F4 and on slot 14
    pr.load_slot(13)
    assert lib.current("presets") == "WAKE" and pr.active == 13       # the one pressed
    reg["preset.load.3"].fire()
    assert pr.active == 3
    reg["preset.select"].set(13)
    assert pr.active == 13 and reg["preset.select"].value == 13
    pr.put_slot(20, "FACES")                               # another slot changes: it stays
    assert pr.active == 13
    pr.clear_slot(13)                                      # its slot cleared: the other one
    assert pr.active == 3
    pr.clear_slot(3)                                       # no slot names it: none
    assert pr.active == -1 and lib.current("presets") == "WAKE"
    pr.put_slot(22, "WAKE")                                # one names it again
    assert pr.active == 22
    lib.load("presets", "FACES")                           # the strip: the first slot that names it
    assert pr.active == 1
    lib.load("presets", "hands-play")                      # a preset in no slot
    assert pr.active == -1
    pr.active = 5
    with pytest.MonkeyPatch.context() as mp:               # nothing loaded: none
        mp.setattr(lib, "current", lambda group: None)
        pr.follow()
    assert pr.active == -1
    # the four sites call it, and nothing else looks a preset up in the bank
    for fn in (library.Project._set_slot, library.Project._apply, library.Marks.put,
               preset.Presets._landed):
        src = inspect.getsource(fn)
        assert "follow()" in src and "bank.index" not in src, fn.__qualname__
    assert inspect.getsource(library).count("bank.index(") == 1
    assert "pr.bank.index(" not in inspect.getsource(preset)


# ------------------------------ plan 19 WP2: a preset saved before the bank's rows

def _files(home) -> dict:
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted((home / "presets").glob("*.json"))}


def _on_bank_rows(rows) -> list:
    """The rows of a desk that sit on a pad of clip rows 4 or 5."""
    far = set(far_pads())
    return [r for r in rows if (r.source if isinstance(r, Binding) else r["source"]) in far]


def test_an_old_preset_loads_without_its_shape_pads_and_its_file_is_untouched(owner_home):
    """The owner's files (on a copy), fork 4. A preset saved before plan
    19 holds the sixteen shape pads of clip rows 4–5 in its `desk`. At a
    load those sixteen exact old factory rows are dropped **quietly** — no
    note, no warning line — while a pad the owner re-aimed is dropped
    **with** the existing "that control is invariant" note; a learned
    device knob is kept; the preset's dot is clean; and **no preset file
    changes by a byte or a tick** — the file keeps the rows until the
    owner saves."""
    home = owner_home
    before = _files(home)
    assert set(before) == {"night-one.json", "night-two.json", "night-three.json"}
    for name in before:                                    # each file does hold the sixteen
        desk = json.loads((home / "presets" / name).read_text())["desk"]
        assert len(_on_bank_rows(desk)) == 16, name
    r = boot_home(home)                                    # the launch lands NIGHT ONE
    lib, table, pr, presets = r.lib, r.router.table, r.lib.project, r.presets
    # saved before plan 19: the fresh layer had no device knob then (WP3's SCENE)
    fresh = len([b for b in preset.fresh_desk() if not preset._is_device_knob(b)])
    # NIGHT ONE: the sixteen exact rows — nothing said
    assert lib.current("presets") == "NIGHT ONE"
    assert presets.desk_notes == [] and presets.notes == [] and lib.warning == ""
    assert _on_bank_rows(table.desk()) == [] and len(table.desk()) == fresh
    assert not lib.is_dirty("presets")
    # NIGHT TWO: fifteen quiet, the owner's re-aimed pad with its note, the knob kept
    pr.load_slot(1)
    said = (f"dropped {OWNER_PAD['source']} → {OWNER_PAD['target']}: that control is "
            "invariant, the session's (plan 13 D6)")
    assert lib.current("presets") == "NIGHT TWO"
    assert presets.desk_notes == [said] and presets.notes == [said]
    assert lib.warning == f"preset NIGHT TWO: {said}"       # one note: no "(+15 more)"
    assert _on_bank_rows(table.desk()) == []
    knob = preset.device_knob(*OWNER_KNOB)
    assert [(b.source, b.target) for b in table.desk() if b.source == knob.source] \
        == [(knob.source, knob.target)]
    assert len(table.desk()) == fresh + 1 and not lib.is_dirty("presets")
    # the pad the owner had re-aimed is the bank's now, on both layers
    kind, ch, n = OWNER_PAD["source"].split(":")
    assert [b.target for b in table.dispatch(kind, int(ch), int(n))] == ["preset.select"]
    # NIGHT THREE (WAKE's eight device knobs): quiet, the eight kept
    lib.warning = ""
    lib.load("presets", "NIGHT THREE")
    assert presets.desk_notes == [] and lib.warning == ""
    assert [b.target for b in table.desk() if b.kind == "cc"
            and b.number in apc40.DEVICE_KNOBS] == list(preset.WAKE_KNOBS)
    assert not lib.is_dirty("presets")
    # an undo's restore of a desk meets the same rule (`set_desk(load=False)`)
    notes = table.set_desk([*old_shape_pads(), OWNER_PAD], load=False)
    assert notes == [said]
    lib.load("presets", "NIGHT ONE")
    # every load, from the bank, the list and the file watch: no file moved
    lib.poll()
    assert _files(home) == before
    assert len(list((home / "trash" / "presets").iterdir())) == 1      # nothing new in the trash
    # emptying the list is fork 4's way back: every row on those pads is noted again
    with pytest.MonkeyPatch.context() as m:
        m.setattr(routing, "RETIRED_DESK_ROWS", frozenset())
        lib.load("presets", "NIGHT ONE")
        assert len(presets.desk_notes) == 16 and "(+15 more)" in lib.warning


def test_the_next_save_of_an_old_preset_writes_the_desk_without_the_pads(owner_home):
    """…and the next save writes the desk as it is live — without the
    rows on clip rows 4–5 — the old file going to the trash first (plan
    15's rule), byte for byte. The other presets' files are not touched."""
    home = owner_home
    before = _files(home)
    r = boot_home(home)
    lib = r.lib
    r.lib.project.load_slot(1)                             # NIGHT TWO
    path = home / "presets" / "night-two.json"
    trash = home / "trash" / "presets"
    assert not list(trash.glob("night-two.*.json"))
    r.reg["view.bright"].set(r.reg["view.bright"].value * 0.9)
    assert lib.is_dirty("presets")
    assert lib.overwrite("presets") == path
    doc = json.loads(path.read_text())
    assert _on_bank_rows(doc["desk"]) == []
    knob = preset.desk_json([preset.device_knob(*OWNER_KNOB)])[0]
    # (the fresh layer less the device knobs it gained in plan 19 WP3, + the learned one)
    fresh = [b for b in preset.fresh_desk() if not preset._is_device_knob(b)]
    assert knob in doc["desk"] and len(doc["desk"]) == len(fresh) + 1
    (kept,) = list(trash.glob("night-two.*.json"))
    assert kept.read_bytes() == before["night-two.json"][0]        # the old file, whole
    assert len(_on_bank_rows(json.loads(kept.read_text())["desk"])) == 16
    after = _files(home)
    assert {k: v for k, v in after.items() if k != "night-two.json"} \
        == {k: v for k, v in before.items() if k != "night-two.json"}
    # it loads clean and quiet from now on
    lib.load("presets", "NIGHT ONE")
    lib.load("presets", "NIGHT TWO")
    assert r.presets.desk_notes == [] and not lib.is_dirty("presets")


# ------------------------------- plan 19 WP3: a user's desk and the re-cut

def test_a_users_desk_is_untouched_by_the_recut(owner_home):
    """The owner's files (on a copy): a preset saved before plan 19 carries
    its own `desk`, and the factory re-cut does not reach it. NIGHT ONE's
    eight device knobs stay dark — D1 turned moves no 4D depth; NIGHT TWO
    keeps the knob the owner learned (D3) and the seven dark ones; NIGHT
    THREE keeps WAKE's eight as saved. No file changes. A user file with
    **no** `desk` key gets the fresh layer by the standing rule, and so
    the four SCENE knobs."""
    from hyperspace import apc40

    home = owner_home
    before = _files(home)
    r = boot_home(home)
    lib, table = r.lib, r.router.table

    def dials() -> dict[str, str]:
        return {b.source: b.target for b in table.desk()
                if b.kind == "cc" and b.number in apc40.DEVICE_KNOBS}
    assert lib.current("presets") == "NIGHT ONE" and dials() == {}       # all eight dark
    assert [b.target for b in table.dispatch("cc", 0, 0x10)] == []        # D1 does nothing
    lib.load("presets", "NIGHT TWO")
    knob = preset.device_knob(*OWNER_KNOB)
    assert dials() == {knob.source: knob.target}                         # D3 alone, learned
    lib.load("presets", "NIGHT THREE")
    assert list(dials().values()) == list(preset.WAKE_KNOBS)
    assert not lib.is_dirty("presets")
    lib.poll()
    assert _files(home) == before
    # a user preset with no desk key: the fresh layer, SCENE on D1–D4
    doc = json.loads((home / "presets" / "night-one.json").read_text())
    doc.pop("desk")
    doc["name"] = "NO DESK"
    (home / "presets" / "no-desk.json").write_text(preset.dumps(doc))
    lib.poll()
    lib.load("presets", "NO DESK")
    assert list(dials().values()) == list(apc40.SCENE)


def test_a_saved_route_onto_a_setting_is_dropped_with_a_note(rig):
    """Plan 21 R12: a preset saved while `ghost.mirror` (or `.guide`,
    `.tethers`) was modulatable may carry a hand's route onto it. Loading
    it drops that route with a note — no crash, the other routes land —
    and the file on disk is not rewritten."""
    path = put(rig.home, "MIRRORED", routes=[
        {"source": "hand:right.x", "target": "ghost.mirror", "op": "position"},
        {"source": "hand:left.roll", "target": "ghost.guide", "op": "position"},
        {"source": "lfo:0", "target": "ghost.tethers", "op": "push", "value": 0.5},
        {"source": "hand:right.y", "target": "view.inst_amp", "op": "position"}])
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    rig.presets.load("MIRRORED")
    table = rig.router.table
    for pid in ("ghost.mirror", "ghost.guide", "ghost.tethers"):
        assert not table.routes_to(pid), pid
    assert table.owner("view.inst_amp").source == "hand:right.y"
    notes = rig.presets.notes
    assert "dropped hand:right.x → ghost.mirror: not modulatable" in notes
    assert "dropped hand:left.roll → ghost.guide: not modulatable" in notes
    assert "dropped lfo:0 → ghost.tethers: not modulatable" in notes
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert rig.reg["ghost.mirror"].value is False
