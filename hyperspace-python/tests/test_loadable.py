"""Plan 13 WP2 — the loadable patch (``hyperspace.preset/2``), the project's bank of
loadable patch names (``hyperspace.project/2``), the F-keys and the startup loadable patch.

Every rig is built the way app.main builds it — Library, registry, attach,
the Router over the home's bindings.json, `LoadedPatch`, the startup loadable patch —
on a tmp_path home seeded with the corpus (conftest.seed: the loadable patches the
build once shipped and the house/party shows), never ~/Hyperspace. The
bank tests that were tests/test_themes.py (the inline theme bank) are
folded in here as the bank of names.
"""

import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import (
    OWNER_KNOB,
    OWNER_PAD,
    boot_home,
    far_pads,
    old_shape_pads,
    opened_last,
    seed,
)

from hyperspace import apc40, envelope, graphmigrate, lfo, loadable, routing, sequencer, tempo
from hyperspace import graph as G
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.library import F_KEYS, SLOTS, Library, LibraryError, bank_doc
from hyperspace.loadable import LoadedPatch
from hyperspace.lookback import DreamState
from hyperspace.params import PATCH_GROUPS, build_registry, part_of
from hyperspace.routing import Binding, Bindings, Router, bindings_path
from hyperspace.view import ViewState


def boot(home, show: str | None = "house"):
    """The app's construction order (app.main), headless — over a home
    seeded with the corpus (conftest.seed) that opened `show` last (the
    house moods, which these tests were written on; None: the seed's own
    mark, the party show)."""
    if show:
        opened_last(home, show)
    seed(home)
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
    # plan 31, as app.main: the envelopes and the sequencer beside the LFOs
    # (plan 36 T3: the corpus `/7` files hold their values)
    envelope.register(reg, envelope.Envelopes(), clock)
    sequencer.register(reg, sequencer.Sequencer(), clock)
    # the table before attach, as app.main reads it: the desk's meta controller
    # param (`desk.slew`) is the table's and exists when the show lands
    table = Bindings.load(bindings_path(home), legacy_midi=None)
    routing.register_desk(reg, table)
    lib.attach(reg)
    router = Router(reg, table)
    loaded_patch = LoadedPatch(lib, reg, router)
    lib.project.load_startup()
    return SimpleNamespace(lib=lib, reg=reg, view=view, control=control, chain=chain,
                           router=router, loaded_patch=loaded_patch, clock=clock, home=home)


@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path)


def put(home, name, **doc):
    """A user loadable patch file, the rest of the shape filled in."""
    body = {"schema": loadable.SCHEMA, "name": name, "values": {}, "routes": [],
            "desk": [], "macros": {}, **doc}
    path = home / "presets" / f"{name.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))
    return path


def expected(lib, values):
    """Every patch param: the file's value, else the value its object
    was built with (plan 44 D3: `_fresh_of`, never a `default.json`)."""
    out = {}
    for g in PATCH_GROUPS:
        out.update({k: v for k, v in lib._fresh_of(g).items()
                    if part_of(lib.reg[k]) == "patch"})
    out.update(values)
    return {k: out[k] for k in lib.reg.snapshot(part="patch") if k in out}


def boot_registry():
    """A bare registry with the clock's families (no library): the ids a
    loadable patch file may name (tests/test_stroke_space.py)."""
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain),
                         dream=DreamState(), fx=FxState())
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    envelope.register(reg, envelope.Envelopes(), clock)       # plan 31: seq-demo's ids
    sequencer.register(reg, sequencer.Sequencer(), clock)
    return reg


# ---------------------------------------------------------------- a load

def test_a_loadable_load_lands_every_base_and_replaces_every_route(rig):
    """D2: every patch param lands — the file's value, or its group
    default — and every performer row is the file's; the input rows stay."""
    lib, reg, table = rig.lib, rig.reg, rig.router.table
    reg["view.bright"].set(3.3)                         # a view base off default
    reg["fx.on"].set(not reg["fx.on"].value)            # an fx toggle (plan 36 T3: the
    #                                                     effects are the startup loadable patch's)
    reg["dream.fade"].set(2.0)                          # a dream value
    table.add(Binding("hand:7", "view.speed", "push", 0.3))    # a hand route
    keys = [b.to_json() for b in table.bindings
            if b.op not in routing.MOD_OPS and b.layer != "preset"]
    values = {"view.shape": 4, "fx.on": True, "lfo.1.depth": 0.25}
    routes = [{"source": "lfo:0", "target": "camera.zoom", "op": "push", "value": 0.1},
              {"source": "lane:2", "target": "view.bright", "op": "push", "value": 0.2,
               "enabled": False}]
    put(rig.home, "PARTIAL", values=values, routes=routes)
    assert rig.loaded_patch.load("PARTIAL") == []
    assert reg.snapshot(part="patch") == expected(lib, values)
    assert rig.view.shape == 4 and reg["lfo.1.depth"].value == 0.25
    assert reg["view.bright"].value == lib.defaults("view")["view.bright"]
    assert reg["dream.fade"].value == lib.defaults("dream")["dream.fade"]
    assert [b.to_json() for b in table.routes()] == routes   # exactly the file's, disabled too
    assert [b.to_json() for b in table.bindings
            if b.op not in routing.MOD_OPS and b.layer != "preset"] == keys
    assert table.desk() == []                               # the file's `desk: []`
    assert rig.loaded_patch.current == "PARTIAL" and not lib.is_dirty("presets")


def test_a_loadable_with_per_frame_echo_ids_is_read_in_seconds(rig):
    """Plan 14 WP6: a loadable patch file that still names the per-frame
    `dream.decay` / `dream.every` loads as 60 Hz frames in seconds — its
    values, a hand push on the decay (the same throw of decays), a desk
    knob on it — and the load says so, once."""
    from hyperspace.lookback import decay_per_frame, fade_of_decay

    put(rig.home, "OLDWAKE", values={"dream.on": True, "dream.decay": 0.93, "dream.every": 2},
        routes=[{"source": "hand:right.z", "target": "dream.decay", "op": "push",
                 "value": -0.12}],
        desk=[{"source": "cc:*:17", "target": "dream.decay", "op": "abs", "feedback": "ring"}])
    assert rig.loaded_patch.load("OLDWAKE") == []
    reg, table = rig.reg, rig.router.table
    assert reg["dream.fade"].value == pytest.approx(fade_of_decay(0.93))
    assert reg["dream.gap"].value == pytest.approx(2 / 60, abs=1e-6)
    assert len(rig.loaded_patch.notes) == 1 and "look-back read in seconds" in rig.loaded_patch.notes[0]
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


def test_a_loadable_load_never_touches_a_meta_param(rig):
    """Plan 13 §10 exit 2: a tapped BPM survives TRIP, and so do the drive,
    an analyzer strip and the band scene, even when the file names them —
    and the master dim (plan 15 WP3), through a loadable patch load and a show load.
    Knob smoothing too (`desk.slew`, plan 18 WP2): no loadable patch moves it, a
    show that does not name it leaves it, and a show save and load
    round-trips it."""
    from hyperspace.overlay import Output

    reg, control = rig.reg, rig.control
    out = Output(None, None)
    out.register(reg)
    reg["output.dim"].set(0.4)
    assert part_of(reg["output.dim"]) == "shared_meta"
    reg["tempo.bpm"].set(100.0)
    reg["master.gain"].set(2.0)
    reg["band.0.atk"].set(0.3)
    slew = reg["desk.slew"]
    slew.set(0.12)
    assert part_of(slew) == "shared_meta" and rig.router.table.slew == 0.12
    scene = control.scene
    put(rig.home, "FAST", values={"view.shape": 5, "tempo.bpm": 140.0, "desk.slew": 0.2,
                                  "scene.select": (scene + 1) % 3, "output.dim": 1.0})
    before = reg.snapshot(part="shared_meta")
    assert before["desk.slew"] == 0.12
    rig.loaded_patch.load("FAST")
    assert slew.value == 0.12 and "desk.slew is the session's, ignored" in rig.loaded_patch.notes
    assert rig.view.shape == 5
    assert rig.clock.bpm == 100.0 and rig.chain.gain == 2.0 and rig.chain.params[0].atk == 0.3
    assert control.scene == scene and reg.snapshot(part="shared_meta") == before
    assert out.dim == 0.4 and "output.dim is the session's, ignored" in rig.loaded_patch.notes
    rig.loaded_patch.load("TRIP")                          # the party loadable patch, too
    assert rig.clock.bpm == 100.0 and reg.snapshot(part="shared_meta") == before
    assert out.dim == 0.4
    rig.lib.project.load("party")                     # a show load, startup loadable patch and all
    assert rig.lib.current("presets") == "TUMBLE" and out.dim == 0.4
    assert slew.value == 0.12                         # the party show names no smoothing
    rig.lib.project.save("mine")                      # a show keeps the number
    assert rig.lib.project.session["desk.slew"] == 0.12
    slew.set(0.03)
    rig.lib.project.load("mine")
    assert slew.value == 0.12 and not rig.lib.project.is_dirty()


def test_meta_ids_in_a_loadable_are_noted_and_ignored(rig):
    """Step 1: a meta controller id, an unknown id, a row that is not a performer
    and a second performer on a target are each noted; the unknown ids are
    returned, and the panel's warning says so in one line."""
    put(rig.home, "NOISY",
        values={"view.shape": 6, "tempo.bpm": 150.0, "scene.select": 2, "nebula.glow": 0.3},
        routes=[{"source": "key:X", "target": "view.faces", "op": "toggle"},
                {"source": "hand:7", "target": "view.bright", "op": "push", "value": 0.2},
                {"source": "hand:8", "target": "view.bright", "op": "push", "value": 0.4}])
    assert rig.loaded_patch.load("NOISY") == ["nebula.glow"]
    notes = rig.loaded_patch.notes
    assert "tempo.bpm is the session's, ignored" in notes
    assert "scene.select is the session's, ignored" in notes
    assert "1 unknown id(s): nebula.glow" in notes
    assert "dropped key:X → view.faces (toggle): not a performer row" in notes
    assert any(n.startswith("dropped hand:8 → view.bright") for n in notes)
    assert rig.lib.warning.startswith("preset NOISY: ")
    assert rig.view.shape == 6 and [b.source for b in rig.router.table.routes()] == ["hand:7"]


def test_a_value_that_will_not_land_leaves_the_state_whole(rig):
    """Review of PR #64: a hand-edited value that will not take refuses the
    load whole — the bases, the routes and the strip stay on the last loadable patch."""
    lib, reg = rig.lib, rig.reg
    snap, routes = reg.snapshot(), [b.to_json() for b in rig.router.table.routes()]
    put(rig.home, "BROKEN", values={"view.shape": 3, "view.speed": "fast"},
        routes=[{"source": "hand:7", "target": "view.bright", "op": "push"}])
    with pytest.raises(LibraryError, match="nothing loaded"):
        rig.loaded_patch.load("BROKEN")
    assert reg.snapshot() == snap
    assert [b.to_json() for b in rig.router.table.routes()] == routes
    assert lib.current("presets") == "BIG BLUE WAVE" and not lib.is_dirty("presets")


def test_a_project_reload_keeps_the_loaded_loadable(rig):
    """Review of PR #64: a project re-read from disk (or opened with no
    startup loadable patch) keeps the loadable patch that is loaded — its name, its clean
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


def test_rotation_phases_survive_a_loadable_load(rig):
    rig.view.ang = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    rig.lib.project.load_slot(1)
    assert rig.view.ang == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]    # the spin keeps flowing


def test_a_loadable_carries_the_macros(rig):
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


def test_the_bank_names_the_house_loadables(rig):
    pr = rig.lib.project
    # plan 19 WP1: twenty-four slots; the house show fills the F-keys' eight
    assert len(pr.bank) == SLOTS == 24 and pr.bank[0] == "BIG BLUE WAVE"
    eight = pr.bank[:F_KEYS]
    assert len(set(eight)) == F_KEYS and all(n in rig.lib.list("presets") for n in eight)
    assert pr.bank[F_KEYS:] == [None] * (SLOTS - F_KEYS)
    select = rig.reg["preset.select"]
    assert select.names == eight + [f"SLOT {k + 1}" for k in range(F_KEYS, SLOTS)]
    assert [select.has(k) for k in range(SLOTS)] == [True] * F_KEYS + [False] * (SLOTS - F_KEYS)


def test_a_slot_names_a_loadable_file(rig):
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
    assert pr.active == 0                                  # the startup loadable patch's slot
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


def test_shift_f_saves_the_live_state_as_the_slots_loadable(rig):
    """⇧F<k>: the live state as the slot's loadable patch in the library (the
    slot's file written over, its old text in the trash), the bank updated
    and the project written; an empty slot gets a new, unique name."""
    reg, pr, home = rig.reg, rig.lib.project, rig.home
    rig.view.shape = 12
    rig.router.table.add(Binding("hand:7", "view.speed", "push", 0.3))
    reg["preset.save.2"].fire()
    user = json.loads((home / "presets" / "strobe-cage.json").read_text())
    assert user["name"] == "STROBE CAGE" and user["values"]["view.shape"] == 12
    assert {"source": "hand:7", "target": "view.speed", "op": "push", "value": 0.3} in user["routes"]
    assert "tempo.bpm" not in user["values"] and "master.gain" not in user["values"]
    assert pr.bank[2] == "STROBE CAGE" and pr.active == 2
    doc = json.loads((home / "projects" / "house.hyp.json").read_text())
    assert doc["schema"] == "hyperspace.project/3"   # (plan 44 D3)
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

def test_the_startup_loadable_loads_on_launch(tmp_path):
    """D11: the project names its startup loadable patch and a launch loads it; a
    startup with no file says so and the app keeps running."""
    r = boot(tmp_path)
    assert r.lib.project.startup == "BIG BLUE WAVE"
    assert r.lib.current("presets") == "BIG BLUE WAVE" and r.lib.project.active == 0
    assert r.view.shape == 17 and len(r.router.table.routes()) == 12
    doc = json.loads((tmp_path / "projects" / "house.hyp.json").read_text())
    doc["startup"] = "GONE"
    (tmp_path / "projects" / "house.hyp.json").write_text(json.dumps(doc))
    r2 = boot(tmp_path)
    assert r2.lib.warning == "startup: no preset 'GONE'"
    assert r2.lib.current("presets") is None and r2.lib.project.active == -1
    r2.reg["preset.load.2"].fire()                          # and the bank still works
    assert r2.lib.current("presets") == "STROBE CAGE"


# ---------------------------------------------------------------- home (plan 15 WP2)

def test_home_loads_what_the_show_starts_on(rig):
    """Decision 27: `preset.home` loads the show's "starts on" loadable patch —
    from another loadable patch, with unsaved edits, and it is a load like any
    other (D2): the values, the routes, the desk, the bank's light, a
    clean dot. A "starts on" picked later is where home goes next."""
    reg, lib, proj = rig.reg, rig.lib, rig.lib.project
    home = reg["preset.home"]
    assert (home.group, home.label, home.modulatable, home.persist) \
        == ("preset", "Home", True, False)
    assert proj.startup == "BIG BLUE WAVE" and home.get() is True      # lit: there is one
    launched = (reg.snapshot(part="patch"),
                [b.to_json() for b in rig.router.table.routes()],
                [b.to_json() for b in rig.router.table.desk()])
    reg["preset.load.2"].fire()
    reg["view.bright"].set_value(reg["view.bright"].value + 1.0)       # an unsaved edit
    assert lib.current("presets") == "STROBE CAGE" and lib.is_dirty("presets")
    assert proj.active == 2 and rig.view.shape != 17
    home.fire()
    assert lib.current("presets") == "BIG BLUE WAVE" and not lib.is_dirty("presets")
    assert proj.active == 0 and rig.view.shape == 17 and not lib.warning
    assert (reg.snapshot(part="patch"),
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
    before = reg.snapshot(part="patch")
    proj.startup = None
    assert reg["preset.home"].get() is False                           # dark: nothing to go to
    reg["preset.home"].fire()
    assert lib.warning == "home: this show names no startup preset"
    assert lib.current("presets") == "STROBE CAGE" and lib.is_dirty("presets")
    assert reg.snapshot(part="patch") == before and proj.active == 2
    proj.startup = "BIG BLUE WAVE"                                     # picked: home goes there,
    reg["preset.home"].fire()                                          # and the note is gone
    assert lib.current("presets") == "BIG BLUE WAVE" and lib.warning == ""


def test_home_is_one_undo_step(tmp_path):
    """Home is one step under its own label — the push `LoadedPatch.load_doc`
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


def test_module_labels_are_dropped_and_a_missing_id_is_the_build_value(rig):
    """Plan 44 D3 (row 540 resolved, the owner, 2026-11-03): an old file's
    `modules` labels name nothing any more — every performance strip lands
    clean and unnamed — and a value the file leaves out is the value its
    object was built with, never the group's default module preset (the
    library's `dream/default.json`, here `wake`'s values as the default)."""
    lib, reg = rig.lib, rig.reg
    wake = lib.read("dream", "wake")
    (rig.home / "patches" / "dream" / "default.json").write_text(json.dumps({**wake, "name": "default"}))
    lib._sync()
    lib.label("camera", "stale")                          # a label from before
    put(rig.home, "LABELS", schema="hyperspace.preset/9", values={"dream.mix": 0.25},
        modules={"dream": "wake", "fx": "trip"})
    rig.loaded_patch.load("LABELS")
    assert lib.current("dream") is None and lib.current("camera") is None
    assert lib.current("fx") is None and not lib.is_dirty("dream")
    assert reg["dream.mix"].base == pytest.approx(0.25)
    assert reg["dream.echoes"].base == lib._fresh_of("dream")["dream.echoes"]
    assert reg["dream.echoes"].base != wake["values"]["dream.echoes"]   # no default.json
    doc = rig.loaded_patch.document("LABELS")
    assert "modules" not in doc and doc["schema"] == "hyperspace.preset/10"
    reg["dream.mix"].set(0.3)
    assert lib.is_dirty("dream")                            # the dot is live against the load


def test_the_fx_presets_are_retired(rig):
    """Plan 40 T5 (D6, the owner: "retired outright"): no fx group in the
    library's list (so no fx strip), and the fx defaults are the fresh
    values even where an old library still keeps an `fx/default.json`; the
    load hook and its migration are gone (D10: the FX page is untouched)."""
    lib = rig.lib
    assert "fx" not in lib.groups() and lib.list("fx") == []
    fresh = lib._fresh_of("fx")
    assert lib.defaults("fx") == fresh and lib.default_name("fx") is None
    old = rig.home / "fx"
    old.mkdir()
    (old / "default.json").write_text(json.dumps({
        "schema": "hyperspace.preset/1", "group": "fx", "name": "default",
        "values": {"fx.mix": 0.25}}))
    lib._defaults.clear()
    assert lib.defaults("fx") == fresh and "fx" not in lib.groups()
    # (the hook, its watch and the run they landed: no name of theirs is left)
    assert not [n for n in dir(LoadedPatch) if "fx" in n]
    assert not [n for n in dir(graphmigrate) if "module" in n or n.endswith("_runs")]
    assert "fx" not in getattr(lib, "_apply_hooks", {})


# ---------------------------------------------------------------- save

def test_a_loadable_round_trips(rig):
    """Save then load gives the same signature; `desk` and `macros` are
    the table's (plan 13 WP4), `modules` names the patch groups'
    labels. (The base subscriber names a param nothing else in the test
    moves: the macro is the scene-setter of record, so a param a later
    module load moved would land back on the subscriber's value.)"""
    lib, table = rig.lib, rig.router.table
    desk = [{"source": "cc:0:48", "target": "view.bright", "op": "abs"}]
    macros = {"macro.1": {"label": "Heat", "subs": [
        {"base": "view.depth4", "from": 0.0, "to": 0.6}]}}
    put(rig.home, "SRC", values={"view.shape": 3}, desk=desk, macros=macros, note="a note",
        routes=[{"source": "hand:7", "target": "view.speed", "op": "push", "value": 0.3}])
    rig.loaded_patch.load("SRC")
    lib.load("dream", "wake")
    rig.reg["camera.zoom"].set(2.0)
    sig = rig.loaded_patch.signature()
    path = rig.loaded_patch.save_as("Round Trip")
    assert path == rig.home / "presets" / "round-trip.json"
    doc = json.loads(path.read_text())
    # (row 394: every save is the newest schema)
    assert doc["schema"] == "hyperspace.preset/10" and doc["name"] == "Round Trip"
    assert doc["desk"] == desk and doc["macros"] == macros and doc["note"] == "a note"
    assert "modules" not in doc                     # (plan 44 D3: the labels are retired)
    # every performance base, the media family's too — and no retired id
    # (plan 33 T7: the wires say them; row 394: nothing writes them back)
    snap = rig.reg.snapshot(part="patch")
    assert doc["values"] == snap
    from hyperspace.graphmigrate import retired
    assert not [k for k in doc["values"] if retired(k)]
    rig.reg["camera.zoom"].set(1.0)
    rig.lib.project.load_slot(0)                            # something else in between
    rig.loaded_patch.load("Round Trip")
    assert rig.loaded_patch.signature() == sig and not lib.is_dirty("presets")
    assert loadable.desk_json(table.desk()) == desk and table.macros_doc() == macros
    assert lib.current("dream") is None             # (plan 44 D3: no module label)


# ---------------------------------------------------------------- the desk and the macros

# (scene launch 5: 1–4 are the invariant render toggles since plan 24 C1)
DESK = [{"source": "cc:*:16", "target": "view.speed", "op": "abs", "feedback": "ring"},
        {"source": "note:0:86", "target": "view.points", "op": "toggle", "feedback": "led"}]
MACROS = {"macro.1": {"label": "Heat", "subs": [
    {"base": "view.depth4", "from": 0.2, "to": 0.8},
    {"depth": {"source": "hand:7", "target": "view.bright"}, "from": 0.0, "to": 1.0}]}}


def test_a_loadable_load_replaces_the_desk_and_the_macros(rig):
    """Plan 13 D2 / D4, §5 steps 4–5: the patch layer is the file's (a row
    on an invariant control dropped, its note in the load's), the layer
    drops to it, the global and invariant rows stay; the macros are the
    file's and their base subscribers land at once from the macros' bases
    — over `values` naming the same param (the macro is the scene-setter
    of record); an explicit `desk: []` leaves every loadable patch control dark."""
    lib, reg, table = rig.lib, rig.reg, rig.router.table
    meta_rows = [b.to_json() for b in table.midi() if b.layer != "preset"]
    table.set_layer("global")
    put(rig.home, "DESKED", values={"macro.1": 0.5, "view.depth4": 1.0},
        routes=[{"source": "hand:7", "target": "view.bright", "op": "position"}],
        # MASTER: invariant (the track faders are layered since plan 24 C2)
        desk=[*DESK, {"source": "cc:0:14", "target": "view.bright", "op": "abs"}],
        macros=MACROS)
    rig.loaded_patch.load("DESKED")
    assert loadable.desk_json(table.desk()) == DESK and table.layer == "preset"
    assert any("cc:0:14 → view.bright" in n and "invariant" in n for n in rig.loaded_patch.notes)
    assert rig.loaded_patch.desk_notes and "cc:0:14" in rig.loaded_patch.desk_notes[0]
    assert [b.to_json() for b in table.midi() if b.layer != "preset"] == meta_rows
    assert table.macros_doc() == MACROS
    depth4 = reg["view.depth4"]
    assert depth4.norm == pytest.approx(0.5, abs=1e-6)        # 0.2 + 0.5 · (0.8 − 0.2)
    assert not lib.is_dirty("presets")                        # landed before the clean reference
    assert rig.router.follow_macros() == []                   # nothing left to land next frame
    put(rig.home, "DARK", desk=[], macros={})
    rig.loaded_patch.load("DARK")
    assert table.desk() == [] and table.macros_doc() == {}
    assert [b.to_json() for b in table.midi() if b.layer != "preset"] == meta_rows


def test_a_loadable_without_a_desk_gets_the_fresh_loadable_layer(rig):
    """A file with no `desk` key is a fresh loadable patch's desk: the default
    map's patch layer (`loadable.fresh_desk`, plan 13 §3.2)."""
    table = rig.router.table
    put(rig.home, "EMPTY", desk=[])
    rig.loaded_patch.load("EMPTY")
    assert table.desk() == []
    path = put(rig.home, "BARE")
    doc = json.loads(path.read_text())
    del doc["desk"], doc["macros"]
    path.write_text(json.dumps(doc))
    rig.loaded_patch.load("BARE")
    fresh = [b for b in routing.factory_desk() if b.layer == "preset"]
    assert [b.to_json() for b in table.desk()] == [b.to_json() for b in fresh]
    assert loadable.desk_json(table.desk()) == loadable.desk_json(loadable.fresh_desk())
    assert rig.loaded_patch.document("BARE")["desk"] == loadable.desk_json(fresh)


def test_a_loadable_with_a_desk_and_macros_round_trips(rig):
    """What the table holds is what a save writes: an edit of the desk or a
    macro moves the dirty dot, a save writes it, a load brings it back."""
    lib, table = rig.lib, rig.router.table
    put(rig.home, "SHOW", desk=DESK, macros=MACROS,
        routes=[{"source": "hand:7", "target": "view.bright", "op": "position"}])
    rig.loaded_patch.load("SHOW")
    assert not lib.is_dirty("presets")
    table.desk()[0].target = "view.instances"                 # the page's retarget
    assert lib.is_dirty("presets")
    table.macros["macro.1"].label = "Cold"
    path = rig.loaded_patch.save_as("SHOW")
    doc = json.loads(path.read_text())
    assert doc["desk"][0]["target"] == "view.instances" and "layer" not in doc["desk"][0]
    assert doc["macros"]["macro.1"]["label"] == "Cold"
    assert not lib.is_dirty("presets")
    rig.loaded_patch.load("TRIP")
    assert table.macros_doc() != doc["macros"]
    rig.loaded_patch.load("SHOW")
    assert loadable.desk_json(table.desk()) == doc["desk"] and table.macros_doc() == doc["macros"]
    assert not lib.is_dirty("presets")


def test_a_loadable_edited_on_disk_is_re_applied(rig):
    path = put(rig.home, "LIVE", values={"view.shape": 2})
    rig.loaded_patch.load("LIVE")
    rig.lib.poll(now=1.0)
    doc = json.loads(path.read_text())
    doc["values"]["view.shape"] = 9
    path.write_text(json.dumps(doc))
    import os
    os.utime(path, (2e9, 2e9))
    assert rig.lib.poll(now=2.0)
    assert rig.view.shape == 9 and rig.lib.current("presets") == "LIVE"


# ---------------------------------------------------------------- the project

def test_a_project_load_brings_its_startup_loadable(rig):
    rig.lib.project.load("party")
    assert rig.lib.current("presets") == "TUMBLE" and rig.view.shape == 10
    assert rig.lib.project.active == 0 and rig.lib.current("band") == "Balanced"


# ---------------------------------------------------------------- the corpus loadable patches

def test_lfo_breathes_macro_moves_brightness_up_and_speed_down(rig):
    """Hand check 39's machine half: lfo-breathe loads with Breathe (macro.1,
    device knob 1) at the bottom; turning it up brightens the picture from
    1× to 2× while the spin slows from 0.25× to a crawl, both over the
    knob's whole throw, and the LFO's push on the fx mix deepens with it."""
    reg, router, table = rig.reg, rig.router, rig.router.table
    rig.loaded_patch.load("lfo-breathe")
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
    """Plan 14 WP1: app.py listens to every loadable patch load (a loadable patch that turns
    the dream on with no worker is a banner); a listener that raises is a
    note, never a failed load."""
    heard: list = []
    rig.loaded_patch.listeners.append(heard.append)
    rig.loaded_patch.listeners.append(lambda name: 1 / 0)
    name = rig.lib.list("presets")[0]
    assert rig.loaded_patch.load(name) == []
    assert heard == [rig.lib.current("presets")]
    assert rig.lib.warning.startswith("preset listener: ZeroDivisionError")
    assert not rig.loaded_patch.note.startswith("preset listener")   # the loadable patch's own note


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


def user_loadables(home):
    return sorted(p.name for p in (home / "presets").glob("*.json"))


def test_save_new_never_overwrites(tmp_path):
    """Decision 29: the desk's save-as makes a new file every time. The
    made name's slug is free among the loadable patch folder's file stems, the
    listed names and the bank's names — so nothing is written over,
    whatever the files are called inside."""
    r = party(tmp_path)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    # the folder: a file whose stem is trip-4 and whose name is not,
    # trip-2.json under another name, a "TRIP 3" in a file of another
    # stem; and the bank names a "TRIP 5" that has no file
    four = home / "presets" / "trip-4.json"
    four.write_text((home / "presets" / "party-wake.json").read_text()
                    .replace('"WAKE"', '"FOUR"', 1))
    two = put(home, "SOMETHING ELSE").rename(home / "presets" / "trip-2.json")
    three = put(home, "TRIP 3").rename(home / "presets" / "mine.json")
    kept = {p: p.read_bytes() for p in (two, three, four)}
    assert "FOUR" in lib.list("presets")
    pr.bank[5] = "TRIP 5"
    pr.clear_slot(6)
    before = user_loadables(home)
    reg["view.shape"].set(9)
    reg["preset.save_new"].fire()
    assert lib.current("presets") == "TRIP 6" and pr.bank[6] == "TRIP 6"
    assert user_loadables(home) == sorted([*before, "trip-6.json"])
    assert all(p.read_bytes() == was for p, was in kept.items())
    assert lib.read("presets", "TRIP")["values"]["view.shape"] != 9     # TRIP itself untouched
    assert json.loads((home / "presets" / "trip-6.json").read_text())["values"]["view.shape"] == 9
    assert not (home / "trash").exists()                    # nothing was replaced
    # held again and again: a new file each time, never the same one twice
    for n in (7, 8, 9):
        reg["preset.save_new"].fire()
        assert lib.current("presets") == f"TRIP {n}"
    assert user_loadables(home) == sorted([*before, *[f"trip-{n}.json" for n in (6, 7, 8, 9)]])
    assert not (home / "trash").exists()
    # a file stem in another case is the same file on a filesystem that
    # folds case (this rig's): it counts too (review of PR #87)
    ten = put(home, "SUNSET").rename(home / "presets" / "Trip-10.json")
    was = ten.read_bytes()
    assert reg["preset.save_new"].fire() is True
    assert lib.current("presets") == "TRIP 11" and ten.read_bytes() == was
    assert "SUNSET" in lib.list("presets") and not (home / "trash").exists()
    # no loadable patch loaded at all: PRESET 1, then PRESET 2
    lib._landed("presets", None, None)
    reg["preset.save_new"].fire()
    assert lib.current("presets") == "PRESET 1"
    reg["preset.save_new"].fire()
    assert lib.current("presets") == "PRESET 2"


def test_save_new_fills_the_next_empty_slot_and_becomes_the_loaded_loadable(tmp_path):
    """The bank, the show's file, what is loaded and its clean dot: the new
    loadable patch takes the first empty slot, the show is written at once, and —
    as the panel's "as…" does — the new loadable patch is the loaded one, so a
    second save counts on and Save on the panel writes the new file, not
    TRIP."""
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
    """A full bank: the loadable patch is still made and loaded, it is in the
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
    # the loadable patch saves but the show's file will not take the bank: the
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


def test_the_new_slot_loads_from_the_loadable_row(tmp_path):
    """The pad over the new slot is an ordinary loadable patch pad: clip row 1's
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
    at any loadable patch, "clear slot" empties it. Both write the show at once,
    neither writes, moves or deletes a loadable patch file, and the lit slot
    follows the loaded patch."""
    r = boot(tmp_path, None)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    show = home / "projects" / "party.hyp.json"
    put(home, "MINE")
    files = user_loadables(home)
    assert lib.current("presets") == "TUMBLE" and pr.active == 0
    pr.clear_slot(5)
    assert pr.bank[5] is None and json.loads(show.read_text())["bank"][5] is None
    assert json.loads(show.read_text())["bank"] == bank_doc(pr.bank)
    assert not pr.is_dirty()                                # written
    assert lib.status == "F6: cleared — ACID is still in the preset list"
    assert "ACID" in lib.list("presets")
    pr.put_slot(5, "MINE")
    assert pr.bank[5] == "MINE" and json.loads(show.read_text())["bank"][5] == "MINE"
    assert lib.status == "F6: MINE" and lib.current("presets") == "TUMBLE" and pr.active == 0
    reg["preset.load.5"].fire()
    assert lib.current("presets") == "MINE" and pr.active == 5
    # the loaded patch's slot cleared: no pad lit; put back elsewhere: that one
    pr.clear_slot(5)
    assert pr.active == -1 and lib.current("presets") == "MINE"
    pr.put_slot(2, "MINE")
    assert pr.bank[2] == "MINE" and pr.active == 2
    # the slot of the loaded patch pointed elsewhere: its light goes
    pr.put_slot(2, "WAKE")
    assert pr.active == -1
    # a loadable patch may sit in two slots; the light stays where it is
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
    assert user_loadables(home) == files and not (home / "trash").exists()


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
    """Plan 19 WP4 (§1 row 10): rename (of the loaded patch too), ×,
    restore and empty write files and change nothing live, so none is an
    undo step — undo cannot put a file back; the trash is the net."""
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
    for fn, *args in ((lib.rename, "presets", "TRIP 2", "SUNRISE"),
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
    assert steps == [0, 0, 0] and not r.undo.undo()
    assert "SUNRISE" in lib.list("presets") and lib.trash() == []


# ------------------------------------------- plan 19 WP1: a bank of twenty-four

def test_save_new_lands_past_the_f_keys_and_a_full_bank_says_so(tmp_path):
    """The desk's save-as on the party show: F1–F8 and slot 9 are filled,
    so fifteen saves fill slots 10–24, each said by its slot; the sixteenth
    finds the bank full and saves to the list. The show's file grows to
    twenty-four slots in place: no backup."""
    r = boot(tmp_path, None)
    lib, reg, pr, home = r.lib, r.reg, r.lib.project, r.home
    show = home / "projects" / "party.hyp.json"
    reg["preset.load.4"].fire()
    assert lib.current("presets") == "TRIP" and pr.next_empty() == 9
    assert len(json.loads(show.read_text())["bank"]) == 9           # as the corpus has it
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


def test_active_follows_the_loaded_loadable_from_one_place(tmp_path):
    """`Project.follow` is the one spelling of "the lit slot follows the
    loaded preset": kept where it is while that slot still names it, else
    the first slot that names it, else none; none when nothing is loaded.
    A loadable patch on two slots lights the one that was pressed."""
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
    lib.load("presets", "hands-play")                      # a loadable patch in no slot
    assert pr.active == -1
    pr.active = 5
    with pytest.MonkeyPatch.context() as mp:               # nothing loaded: none
        mp.setattr(lib, "current", lambda group: None)
        pr.follow()
    assert pr.active == -1
    # the four sites call it, and nothing else looks a loadable patch up in the bank
    for fn in (library.Project._set_slot, library.Project._apply, library.Marks.put,
               loadable.LoadedPatch._landed):
        src = inspect.getsource(fn)
        assert "follow()" in src and "bank.index" not in src, fn.__qualname__
    # (plan 48: `follow` resolves each slot to its file, so a slot naming
    # the loadable patch by another spelling lights too — the one look-up is there)
    assert inspect.getsource(library).count("bank.index(") == 0
    assert "enumerate(self.bank)" in inspect.getsource(library.Project.follow)
    assert "pr.bank.index(" not in inspect.getsource(loadable)


# ------------------------------ plan 19 WP2: a loadable patch saved before the bank's rows

def _files(home) -> dict:
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted((home / "presets").glob("*.json"))}


def _on_bank_rows(rows) -> list:
    """The rows of a desk that sit on a pad of clip rows 4 or 5."""
    far = set(far_pads())
    return [r for r in rows if (r.source if isinstance(r, Binding) else r["source"]) in far]


# the owner's three files among the corpus `build_owner_home` seeds
NIGHT_FILES = {"night-one.json", "night-two.json", "night-three.json"}
DEVICE_KNOBS = [f"cc:*:{0x10 + k}" for k in range(8)]           # D1–D8


def _is_device_knob(b: Binding) -> bool:
    return b.kind == "cc" and b.number in apc40.DEVICE_KNOBS


def wake_knobs(home) -> list[str]:
    """WAKE's eight device knobs, D1–D8, as the corpus file has them."""
    doc = json.loads((home / "presets" / "party-wake.json").read_text())
    by_source = {d["source"]: d["target"] for d in doc["desk"]}
    return [by_source[s] for s in DEVICE_KNOBS]


def test_an_old_loadable_loads_without_its_shape_pads_and_its_file_is_untouched(owner_home):
    """The owner's files (on a copy), fork 4. A loadable patch saved before plan
    19 holds the sixteen shape pads of clip rows 4–5 in its `desk`. At a
    load those sixteen exact old factory rows are dropped **quietly** — no
    note, no warning line — while a pad the owner re-aimed is dropped
    **with** the existing "that control is invariant" note; a learned
    device knob is kept; the loadable patch's dot is clean; and **no loadable patch file
    changes by a byte or a tick** — the file keeps the rows until the
    owner saves."""
    home = owner_home
    before = _files(home)
    assert NIGHT_FILES <= set(before)
    for name in NIGHT_FILES:                               # each file does hold the sixteen
        desk = json.loads((home / "presets" / name).read_text())["desk"]
        assert len(_on_bank_rows(desk)) == 16, name
    r = boot_home(home)                                    # the launch lands NIGHT ONE
    lib, table, pr, loaded_patch = r.lib, r.router.table, r.lib.project, r.loaded_patch
    # saved before plan 19: the fresh layer had no device knob then (WP3's SCENE)
    fresh = len([b for b in loadable.fresh_desk() if not _is_device_knob(b)])
    # NIGHT ONE: the sixteen exact rows — nothing said
    assert lib.current("presets") == "NIGHT ONE"
    assert loaded_patch.desk_notes == [] and loaded_patch.notes == [] and lib.warning == ""
    assert _on_bank_rows(table.desk()) == [] and len(table.desk()) == fresh
    assert not lib.is_dirty("presets")
    # NIGHT TWO: fifteen quiet, the owner's re-aimed pad with its note, the knob kept
    pr.load_slot(1)
    said = (f"dropped {OWNER_PAD['source']} → {OWNER_PAD['target']}: that control is "
            "invariant, the session's (plan 13 D6)")
    assert lib.current("presets") == "NIGHT TWO"
    assert loaded_patch.desk_notes == [said] and loaded_patch.notes == [said]
    assert lib.warning == f"preset NIGHT TWO: {said}"       # one note: no "(+15 more)"
    assert _on_bank_rows(table.desk()) == []
    knob = loadable.device_knob(*OWNER_KNOB)
    assert [(b.source, b.target) for b in table.desk() if b.source == knob.source] \
        == [(knob.source, knob.target)]
    assert len(table.desk()) == fresh + 1 and not lib.is_dirty("presets")
    # the pad the owner had re-aimed is the bank's now, on both layers
    kind, ch, n = OWNER_PAD["source"].split(":")
    assert [b.target for b in table.dispatch(kind, int(ch), int(n))] == ["preset.select"]
    # NIGHT THREE (WAKE's eight device knobs): quiet, the eight kept
    lib.warning = ""
    lib.load("presets", "NIGHT THREE")
    assert loaded_patch.desk_notes == [] and lib.warning == ""
    assert [b.target for b in table.desk() if _is_device_knob(b)] == wake_knobs(home)
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
        assert len(loaded_patch.desk_notes) == 16 and "(+15 more)" in lib.warning


def test_the_next_save_of_an_old_loadable_writes_the_desk_without_the_pads(owner_home):
    """…and the next save writes the desk as it is live — without the
    rows on clip rows 4–5 — the old file going to the trash first (plan
    15's rule), byte for byte. The other loadable patches' files are not touched."""
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
    knob = loadable.desk_json([loadable.device_knob(*OWNER_KNOB)])[0]
    # (the fresh layer less the device knobs it gained in plan 19 WP3, + the learned one)
    fresh = [b for b in loadable.fresh_desk() if not _is_device_knob(b)]
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
    assert r.loaded_patch.desk_notes == [] and not lib.is_dirty("presets")


# ------------------------------- plan 19 WP3: a user's desk and the re-cut

def test_a_users_desk_is_untouched_by_the_recut(owner_home):
    """The owner's files (on a copy): a loadable patch saved before plan 19 carries
    its own `desk`, and plan 19's re-cut does not reach it. NIGHT ONE's
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
    knob = loadable.device_knob(*OWNER_KNOB)
    assert dials() == {knob.source: knob.target}                         # D3 alone, learned
    lib.load("presets", "NIGHT THREE")
    assert list(dials().values()) == wake_knobs(home)
    assert not lib.is_dirty("presets")
    lib.poll()
    assert _files(home) == before
    # a user loadable patch with no desk key: the fresh layer, SCENE on D1–D4
    doc = json.loads((home / "presets" / "night-one.json").read_text())
    doc.pop("desk")
    doc["name"] = "NO DESK"
    (home / "presets" / "no-desk.json").write_text(loadable.dumps(doc))
    lib.poll()
    lib.load("presets", "NO DESK")
    assert list(dials().values()) == list(apc40.SCENE)


def test_a_saved_route_onto_a_setting_is_dropped_with_a_note(rig):
    """Plan 21 R12: a loadable patch saved while `ghost.mirror` (or `.guide`,
    `.tethers`) was modulatable may carry a hand's route onto it. Loading
    it drops that route with a note — no crash, the other routes land —
    and the file on disk is not rewritten."""
    path = put(rig.home, "MIRRORED", routes=[
        {"source": "hand:right.x", "target": "ghost.mirror", "op": "position"},
        {"source": "hand:left.roll", "target": "ghost.guide", "op": "position"},
        {"source": "lfo:0", "target": "ghost.tethers", "op": "push", "value": 0.5},
        {"source": "hand:right.y", "target": "view.inst_amp", "op": "position"}])
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    rig.loaded_patch.load("MIRRORED")
    table = rig.router.table
    for pid in ("ghost.mirror", "ghost.guide", "ghost.tethers"):
        assert not table.routes_to(pid), pid
    assert table.owner("view.inst_amp").source == "hand:right.y"
    notes = rig.loaded_patch.notes
    assert ("dropped hand:right.x → ghost.mirror: ghost.mirror is the meta controller's, "
            "tuned before the show; no preset row may drive it") in notes     # (row 743)
    assert "dropped hand:left.roll → ghost.guide: not modulatable" in notes
    assert "dropped lfo:0 → ghost.tethers: not modulatable" in notes
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert rig.reg["ghost.mirror"].value is False


# ---- plan 35 T3: the wired frame's schema (row 385) ----

WIRED_FIXTURES = ("blank-frame", "channel-out-only", "through-one-output")
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "presets"


def test_a_wired_loadable_saves_as_v6(rig):
    """Row 385, row 394: every save is the newest schema — plan 43 C2:
    `hyperspace.preset/9` — the frame edited or not; the ladder reads `/2`
    … `/9` (plan 40 T2's `/8` a `/7` with groups) — and a `/10` file is
    refused in its words."""
    assert loadable.VERSIONS == (2, 3, 4, 5, 6, 7, 8, 9, 10)
    assert graphmigrate.WIRED_SCHEMA == loadable.WIRED_SCHEMA == "hyperspace.preset/7"
    rig.loaded_patch.load_doc({"schema": loadable.SCHEMA, "name": "edited", "values": {}})
    section = rig.loaded_patch.graph.free_doc()
    assert section["frame"] == "wired"
    edited = {**section, "wires": [w for w in section["wires"]
                                   if w["to"] != "lookback.capture"]}
    assert rig.loaded_patch.document("edited")["schema"] == "hyperspace.preset/10"
    rig.loaded_patch.graph.land(G.read_graph(edited), edited)
    doc = rig.loaded_patch.document("edited")
    assert doc["schema"] == "hyperspace.preset/10" and doc["graph"] == edited
    put(rig.home, "ELEVEN", schema="hyperspace.preset/11")
    rig.lib.poll()
    with pytest.raises(LibraryError, match="is not a hyperspace.preset"):
        rig.lib.read("presets", "ELEVEN")


@pytest.mark.parametrize("name", WIRED_FIXTURES)
def test_a_wired_frame_loadable_saves_and_loads(tmp_path, name):
    """Each of T3's `/6` fixtures, loaded, saved and loaded into a fresh rig,
    lands the same `GraphSpec`, and saves `/7` (plan 36 T3) — the second
    load reads it as it is."""
    src = FIXTURE_DIR / f"{name}.json"
    assert json.loads(src.read_text())["schema"] == "hyperspace.preset/6"
    spec, saved = None, None
    for home in (tmp_path / "a", tmp_path / "b"):
        (home / "presets").mkdir(parents=True, exist_ok=True)
        (home / "presets" / src.name).write_text(saved or src.read_text())
        r = boot(home)
        r.loaded_patch.load(name)
        got = r.loaded_patch.graph.spec
        assert got is not None and got.wired and not got.notes
        assert [n for n in r.loaded_patch.notes if n.startswith("graph:")] == []
        if spec is not None:
            assert got == spec
        spec = got
        saved = r.loaded_patch.save_as(name).read_text()
        assert json.loads(saved)["schema"] == "hyperspace.preset/10"


# ---------------------------------------------------------------- a new loadable patch (plan 35 T7)

def _fresh_patch(lib):
    return {k: v for k, v in lib._fresh_all().items()
            if k in lib.reg and lib.reg[k].group in PATCH_GROUPS
            and not loadable.is_instance_id(k) and not loadable.is_switch_id(k)
            and lib.reg[k].group != "modifiers"}


def _spoil(rig, name):
    """A loaded corpus loadable patch with a route and a desk row of its own."""
    rig.loaded_patch.load(name)
    table = rig.router.table
    table.add(Binding("hand:7", "view.bright", "position"))
    table.set_desk([*table.desk(), Binding("cc:0:14", "view.speed", "abs", layer="preset")])


@pytest.mark.parametrize("name", ["big-blue-wave", "hex-engine"])
def test_a_new_loadable_is_fresh_values_and_the_scene_chain(rig, name):
    """Plan 35 T7 (row 387): the library's fresh values for every
    patch group whatever was loaded, no loadable patch routes, the desk the
    fresh patch layer (written explicitly), the meta controller as it was, and
    (plan 36 T5, W5) a frame of the scene chain alone — a shape on every
    window."""
    lib, reg, table = rig.lib, rig.reg, rig.router.table
    _spoil(rig, name)
    kept = reg.snapshot(part="shared_meta")
    assert rig.loaded_patch.new() == [loadable.NEW_SAID]
    for k, v in _fresh_patch(lib).items():
        assert reg[k].value == v, k
    assert table.routes() == []
    assert loadable.desk_json(table.desk()) == loadable.desk_json(loadable.fresh_desk())
    doc = rig.loaded_patch.document(loadable.UNTITLED_PATCH)
    assert doc["desk"] == loadable.desk_json(loadable.fresh_desk())
    assert doc["routes"] == []
    assert reg.snapshot(part="shared_meta") == kept
    spec = rig.loaded_patch.graph.spec
    assert spec.to_json() == {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"}],
            "wires": [{"from": "shape", "to": "scene.geometry"},
                      {"from": "scene", "to": "output.all.image"}]}   # (plan 36 T3: hands written)
    assert G.reaches(spec) == frozenset({"shape", "scene"})
    assert lib.current("presets") == loadable.UNTITLED_PATCH
    assert lib.is_dirty("presets")
    assert lib.path_of("presets", loadable.UNTITLED_PATCH) is None


def test_a_new_loadable_does_not_depend_on_what_was_loaded(rig):
    after = []
    for name in ("big-blue-wave", "hex-engine"):
        _spoil(rig, name)
        rig.loaded_patch.new()
        after.append((rig.reg.snapshot(part="patch"),
                      rig.loaded_patch.document(loadable.UNTITLED_PATCH)))
    assert after[0] == after[1]


def test_a_new_loadable_undoes_in_one_step(rig):
    from hyperspace import undo
    from hyperspace.library import Marks

    u = undo.Undo(rig.reg, rig.router.table, marks=Marks(rig.lib))
    undo.install(u)
    try:
        _spoil(rig, "big-blue-wave")
        u.tick(1.0)
        u.tick(2.0)
        before = rig.reg.snapshot(part="patch")
        loaded = rig.lib.current("presets")
        rig.loaded_patch.new()
        assert u.stack[-1].label == "new preset"
        assert u.undo()
    finally:
        undo.install(None)
    assert rig.reg.snapshot(part="patch") == before
    assert rig.lib.current("presets") == loaded
    assert len(rig.router.table.routes()) >= 1
    assert rig.lib.is_dirty("presets")        # (the spoiled loadable patch's dot, back)


def test_a_new_loadable_empties_the_bins_macros_and_modifiers(rig):
    """T7's deferred check (final review): after a loadable patch with a channel's
    bin, a macro and a modifier, New leaves no bin filled, no macro
    subscriber and no modifier — and its save writes none of them."""
    doc = json.loads((rig.home / "presets" / "lfo-breathe.json").read_text())
    doc.update(name="full", media={"channels": {"a": ["local:x.png"]}},
               modifiers=[{"id": "mod.1", "kind": "smooth", "in": ["hand:right.energy", None]}])
    rig.loaded_patch.load_doc(doc)
    table, media = rig.router.table, rig.loaded_patch.media
    assert media.to_json()["channels"] and table.modifiers_doc(rig.reg)
    assert [m for m in table.macros_doc().values() if m.get("subs")]
    rig.loaded_patch.new()
    assert not media.to_json().get("channels")
    assert not table.modifiers_doc(rig.reg)
    assert not [m for m in table.macros_doc().values() if m.get("subs")]
    saved = rig.loaded_patch.document("blank")
    assert not saved.get("modifiers") and not (saved.get("media") or {}).get("channels")
    assert not [m for m in saved["macros"].values() if m.get("subs")]


def test_a_new_loadable_saves_and_loads_back_as_the_scene_chain(rig):
    _spoil(rig, "big-blue-wave")
    rig.loaded_patch.new()
    rig.loaded_patch.save_as("blank")
    _spoil(rig, "hex-engine")
    rig.loaded_patch.load("blank")
    assert rig.loaded_patch.graph.spec.to_json() == {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"}],
            "wires": [{"from": "shape", "to": "scene.geometry"},
                      {"from": "scene", "to": "output.all.image"}]}
    assert len(rig.loaded_patch.layout) == 3
    assert rig.router.table.routes() == []
    assert loadable.desk_json(rig.router.table.desk()) == loadable.desk_json(loadable.fresh_desk())


@pytest.fixture(scope="module")
def gl_ctx():
    try:
        import moderngl

        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c


def test_a_new_loadable_draws_a_shape(rig, gl_ctx):
    """Plan 36 T5 (W5; was plan 35 T7's black): the new loadable patch's frame,
    drawn on two views through the bus, is not the ground alone — the
    shape is on each window."""
    from test_graph_frame import SIZE, _fbo, _px, _tool

    from hyperspace.outputs import Switches, View

    rig.loaded_patch.new()
    spec = rig.loaded_patch.graph.spec
    gl = _tool().Rig("legacy6", "present", gl_ctx)
    try:
        gl.renderer.wiring = spec.wiring()
        vs = [View(Switches(), SIZE, target=_fbo(gl_ctx)) for _ in range(2)]
        for _ in range(3):
            gl.frame(vs, SIZE, 1.0)
        assert gl_ctx.error == "GL_NO_ERROR"
        for v in vs:
            assert not v.error, v.error
            assert (_px(v.target)[..., :3] > 0).any()
    finally:
        gl.close()


# ---- plan 34 T4: the resize's values (Review Focus 6) ----

RESIZE_OLD = {"nodes": [{"kind": "resize", "instance": 2}],
              "wires": [{"from": "frame", "to": "fx.image"},
                        {"from": "media.a", "to": "resize.2.image"}]}


def _resize_section(section=RESIZE_OLD):
    return graphmigrate.wired_section(graphmigrate.renamed(section), G.read_graph(section))


def test_resize_values_save_and_load_with_the_loadable(tmp_path):
    """A loadable patch whose graph holds `resize.2` carries its values: saved and
    loaded into a fresh rig, `resize.2.crop_x` lands with no unknown-id
    note, and the file is `/6` (row 394).
    A loadable patch without the entry undeclares `resize.2.*`; one with the entry
    and no wire still declares it (the reach does not decide)."""
    a, b = tmp_path / "a", tmp_path / "b"
    r = boot(a)
    put(a, "CROP", graph=_resize_section(), values={"resize.2.crop_x": 0.3})
    r.lib.poll()
    assert r.loaded_patch.load("CROP") == []
    assert r.reg["resize.2.crop_x"].value == 0.3
    saved = r.loaded_patch.save_as("CROP").read_text()
    assert json.loads(saved)["schema"] == "hyperspace.preset/10"
    assert json.loads(saved)["values"]["resize.2.crop_x"] == 0.3
    (b / "presets").mkdir(parents=True)
    (b / "presets" / "crop.json").write_text(saved)
    r = boot(b)
    assert r.loaded_patch.load("CROP") == []
    assert r.reg["resize.2.crop_x"].value == 0.3
    assert not [n for n in r.loaded_patch.notes if "unknown id" in n]
    put(b, "PLAIN", values={})
    r.lib.poll()
    r.loaded_patch.load("PLAIN")
    assert not [p for p in r.reg if p.id.startswith("resize.2.")]
    unwired = {**_resize_section(), "wires": [
        w for w in _resize_section()["wires"] if w["to"] != "resize.2.image"]}
    put(b, "UNWIRED", graph=unwired, values={"resize.2.crop_x": 0.7})
    r.lib.poll()
    r.loaded_patch.load("UNWIRED")
    assert "resize.2" not in G.reaches(r.loaded_patch.graph.spec)
    assert r.reg["resize.2.crop_x"].value == 0.7


def test_a_new_loadable_carries_no_resize_values(rig):
    put(rig.home, "CROP", graph=_resize_section(), values={"resize.2.crop_x": 0.3})
    rig.lib.poll()
    rig.loaded_patch.load("CROP")
    assert "resize.2.crop_x" in rig.reg
    rig.loaded_patch.new()
    assert not [p for p in rig.reg if loadable.is_resize_id(p.id)]
    doc = rig.loaded_patch.document(loadable.UNTITLED_PATCH)
    assert not [k for k in doc["values"] if k.startswith("resize")]
