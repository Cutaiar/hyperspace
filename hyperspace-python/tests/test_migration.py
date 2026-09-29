"""Plan 13 §6 (WP5) — the one-time migration of a home folder, headless.

Every test builds a home in tmp_path that looks like the owner's before
plan 13 (never ~/Hyperspace): a schema-1 ``projects/default.hyp.json``
with five filled slots (session ids among their values) and `modules`; a
schema-2 ``bindings.json`` with the factory rows, the house lane routes,
learned hand rows, a learned knob, a macro-scaled route and the macros'
`values`; a user routing preset in ``bindings/``; and a hand-made
``bindings.json.bak-mine``. Then it launches the app's way (`boot`:
library, registry, Router over the home's bindings.json, `Presets`,
`preset.migrate_home`, the startup preset) and checks what the first
launch leaves behind — and that a second launch changes nothing.
"""

import json
import re
from types import SimpleNamespace

import pytest

from hyperspace import hands, lfo, preset, routing, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.library import FACTORY, SESSION_GROUPS, Library
from hyperspace.lookback import DreamState
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import MOD_OPS, Binding, Bindings, Router, bindings_path
from hyperspace.view import ViewState

SLOT_NAMES = ["MY WAVE", "EMBER ORBIT", "LATE SET", "HANDS UP", "CLOSER"]
LEARNED = [  # what the owner learned: two hand rows (one gated) and a lane on a macro
    {"source": "hand:7", "target": "view.bright", "op": "position"},
    {"source": "hand:1", "target": "view.speed", "op": "push", "value": 0.4, "when": "hand:18"},
    {"source": "lane:3", "target": "fx.mix", "op": "push", "value": 0.2, "scale": "macro.2"},
]
KNOB = {"source": "cc:0:87", "target": "view.inst_amp", "op": "abs"}   # a learned knob
MACRO_VALUES = {**{f"macro.{k}": 1.0 for k in range(1, 9)}, "macro.2": 0.4}
ROUTING_PRESET = {"schema": routing.SCHEMA_V2, "name": "Show A", "profile": "apc40",
                  "bindings": [{"source": "hand:10", "target": "fx.acid.twist",
                                "op": "position"},
                               {"source": "hand:7", "target": "view.depth4", "op": "push",
                                "value": 0.3}],
                  "values": {"fx.acid.speed": 2.0, "tempo.bpm": 99.0}}
NEW_GLOBALS = {"hands.smooth", "hands.response", "hands.catch", "hands.sel.return",
               "tempo.bpm", routing.SHIFT_PARAM}


def named(rows: list[dict]) -> list[dict]:
    """`rows` with every hand lane named on the default layout — what the
    migration writes when `[hands]` is off (decision register row 20)."""
    return preset.name_hand_rows(rows, {}, hands.default_addresses())[0]


def slot(k: int) -> dict:
    """A main-era slot: a whole-surface snapshot — performance ids and the
    session's (the band scene, the drive, an analyzer strip)."""
    return {"name": SLOT_NAMES[k], "note": f"slot {k + 1}",
            "values": {"view.shape": k + 2, "view.bright": 1.0 + k / 4, "view.faces": k % 2 == 0,
                       "dream.decay": 0.9, "camera.zoom": 0.5 + k / 10,
                       "scene.select": k, "master.gain": 1.0 + k, "band.0.atk": 0.01 * (k + 1)}}


def project_v1() -> dict:
    return {"schema": "hyperspace.project/1", "name": "default",
            "values": {"view.shape": 9, "tempo.bpm": 128.0, "band.1.post": 0.7,
                       "hands.smooth": 0.3},
            "modules": {"band": "Balanced", "fx": "trip"},
            "bank": [slot(k) for k in range(5)] + [None, None, None]}


def bindings_v2() -> dict:
    """The owner's bindings.json at schema 2: the factory rows of the day
    (no layers, no SHIFT, no global track knobs), the house lane routes,
    the learned rows and knob, and the macros' bases as `values`."""
    rows = [{k: v for k, v in b.to_json().items() if k != "layer"}
            for b in Bindings.factory().bindings if b.target not in NEW_GLOBALS]
    rows += [b.to_json() for b in routing.legacy6_routes()]
    rows += [dict(r) for r in LEARNED] + [dict(KNOB)]
    return {"schema": routing.SCHEMA_V2, "profile": "apc40", "bindings": rows,
            "values": dict(MACRO_VALUES)}


def owners_home(home, *, project=True, routing_preset=True):
    (home / "projects").mkdir(parents=True, exist_ok=True)
    if project:
        (home / "projects" / "default.hyp.json").write_text(json.dumps(project_v1(), indent=1))
    bindings_path(home).write_text(json.dumps(bindings_v2(), indent=1))
    (home / "bindings.json.bak-mine").write_text("my own copy")
    if routing_preset:
        (home / "bindings").mkdir()
        (home / "bindings" / "show-a.json").write_text(json.dumps(ROUTING_PRESET))
    return home


def boot(home, hands_cfg=None):
    """app.main's order, headless; the migration's notes in `notes`."""
    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
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
    notes = preset.migrate_home(lib, router, hands_cfg)
    lib.project.load_startup()
    return SimpleNamespace(lib=lib, reg=reg, view=view, router=router, presets=presets,
                           notes=notes, home=home)


def read(path):
    return json.loads(path.read_text())


def preset_file(home, name):
    return read(home / "presets" / f"{preset.slug(name)}.json")


def tree(home) -> dict:
    """Every file under the home: path → (bytes, mtime)."""
    return {p.relative_to(home).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(home.rglob("*")) if p.is_file()}


@pytest.fixture()
def home(tmp_path):
    return owners_home(tmp_path)


# ---------------------------------------------------------------- the project

def test_a_schema_1_project_becomes_presets_and_a_schema_2_project(home):
    r = boot(home)
    doc = read(home / "projects" / "default.hyp.json")
    assert doc["schema"] == "hyperspace.project/2" and doc["name"] == "default"
    # the bank names the five slots' presets; the empty slots point at the
    # factory house presets their F-keys used to load (the seeds)
    seeds = read(FACTORY / "projects" / "default.hyp.json")["bank"]
    # slot 6, the first empty one, holds the project's own look (it differs from
    # every slot: view.shape 9); the rest point at the house presets
    assert doc["bank"] == [*SLOT_NAMES, "DEFAULT SAVED", *seeds[6:]]
    assert doc["startup"] == "DEFAULT SAVED"
    # the session: the project's own session ids, then the first slot's
    assert doc["session"]["tempo.bpm"] == 128.0 and doc["session"]["band.1.post"] == 0.7
    assert doc["session"]["hands.smooth"] == 0.3
    assert doc["session"]["scene.select"] == 0 and doc["session"]["master.gain"] == 1.0
    assert all(k.partition(".")[0] in SESSION_GROUPS for k in doc["session"])
    assert doc["modules"] == {"band": "Balanced"}                 # the session group's label
    table = bindings_v2()
    for k, name in enumerate(SLOT_NAMES):
        p = preset_file(home, name)
        assert p["schema"] == "hyperspace.preset/2" and p["name"] == name
        assert p["note"] == f"slot {k + 1}"
        perf = {pid: v for pid, v in slot(k)["values"].items()
                if pid.partition(".")[0] not in SESSION_GROUPS}
        assert p["values"] == {**MACRO_VALUES, **perf}            # the table's macros fill in
        assert p["modules"] == {"fx": "trip"}                     # the performance labels
        assert len(p["routes"]) == 12 + len(LEARNED)
        assert p["macros"] == {"macro.2": {"subs": [{"depth": {"source": "lane:3",
                                                                "target": "fx.mix"},
                                                      "from": 0.0, "to": 1.0}]}}
        assert any(d["source"] == KNOB["source"] for d in p["desk"])
    # the live state: the migrated project is the one open, its startup loaded
    assert r.lib.project.path == home / "projects" / "default.hyp.json"
    assert r.lib.project.bank[:5] == SLOT_NAMES and r.lib.current("presets") == "DEFAULT SAVED"
    assert r.view.shape == 9 and r.lib.project.active == 5     # the look it opened on (D11)
    assert not r.lib.error
    # F2 loads the second slot's preset through the one loader
    r.reg["preset.load.1"].fire()
    assert r.lib.current("presets") == "EMBER ORBIT" and r.view.shape == 3
    # the migrated project was table's full content too: nothing else noted
    assert any("default.hyp.json → hyperspace.project/2 (5 presets)" in n for n in r.notes)
    assert table["values"] == MACRO_VALUES


def test_a_schema_1_projects_saved_look_becomes_its_startup_preset(tmp_path):
    """The look a schema-1 project restored on open (its own performance
    `values`) never survives only in the backup: differing from every
    slot, it is `<PROJECT> SAVED` — the table's routes, desk and macros
    with it — the startup, in the first empty slot (a full bank: in no
    slot, said), through `put_preset` (a differing user preset of that
    name is kept: `<name> 2`); equal to a slot's, that slot is the startup
    and nothing more is written."""
    # differs, first empty slot 6; a user DEFAULT SAVED already there is kept
    home = owners_home(tmp_path / "a", routing_preset=False)
    (home / "presets").mkdir()
    mine = {"schema": "hyperspace.preset/2", "name": "DEFAULT SAVED", "values": {}}
    (home / "presets" / "default-saved.json").write_text(json.dumps(mine))
    r = boot(home)
    doc = read(home / "projects" / "default.hyp.json")
    assert doc["startup"] == "DEFAULT SAVED 2" and doc["bank"][5] == "DEFAULT SAVED 2"
    assert read(home / "presets" / "default-saved.json") == mine
    saved = preset_file(home, "DEFAULT SAVED 2")
    assert saved["values"]["view.shape"] == 9 and saved["values"]["macro.2"] == 0.4
    assert not any(k.partition(".")[0] in SESSION_GROUPS for k in saved["values"])
    assert saved["routes"] == preset_file(home, "MY WAVE")["routes"]
    assert KNOB in saved["desk"] and saved["macros"] == preset_file(home, "MY WAVE")["macros"]
    assert saved["modules"] == {"fx": "trip"}
    assert r.lib.current("presets") == "DEFAULT SAVED 2" and r.view.shape == 9
    assert any("own look → preset 'DEFAULT SAVED 2'" in n and "slot 6" in n for n in r.notes)
    # equal to slot 3's: that slot is the startup, no SAVED preset
    home = tmp_path / "b"
    owners_home(home, routing_preset=False)
    v1 = project_v1()
    v1["values"] = {**slot(2)["values"], "tempo.bpm": 128.0}
    (home / "projects" / "default.hyp.json").write_text(json.dumps(v1))
    r = boot(home)
    doc = read(home / "projects" / "default.hyp.json")
    assert doc["startup"] == "LATE SET" and "DEFAULT SAVED" not in doc["bank"]
    assert not (home / "presets" / "default-saved.json").exists()
    assert r.lib.current("presets") == "LATE SET" and doc["session"]["tempo.bpm"] == 128.0
    # a full bank: the startup, in no slot, and the note says so
    home = tmp_path / "c"
    owners_home(home, routing_preset=False)
    v1 = project_v1()
    v1["name"] = "gig"
    v1["bank"] = [dict(slot(k % 5), name=f"S{k}") for k in range(8)]
    (home / "projects" / "default.hyp.json").write_text(json.dumps(v1))
    r = boot(home)
    doc = read(home / "projects" / "default.hyp.json")
    assert doc["startup"] == "GIG SAVED" and "GIG SAVED" not in doc["bank"]
    assert preset_file(home, "GIG SAVED")["values"]["view.shape"] == 9
    assert any("GIG SAVED" in n and "no slot (the bank is full)" in n for n in r.notes)
    assert r.lib.current("presets") == "GIG SAVED"


def test_a_schema_1_project_opened_later_is_migrated_on_the_same_road(home, capsys):
    """A schema-1 project the launch did not see (put in the folder since)
    is migrated when it is opened: presets, schema 2, a backup."""
    r = boot(home)
    later = project_v1()
    later["name"] = "gig"
    later["bank"] = [dict(slot(0), name="GIG ONE"), None]
    later["values"] = dict(slot(0)["values"])          # its look is slot 1's: no SAVED
    path = home / "projects" / "gig.hyp.json"
    path.write_text(json.dumps(later))
    assert set(r.lib.project.load("gig")) <= {"hands.smooth"}     # no hands in this rig
    assert read(path)["schema"] == "hyperspace.project/2" and read(path)["bank"][0] == "GIG ONE"
    assert read(path.with_name("gig.hyp.json.bak-v1")) == later
    assert r.lib.current("presets") == "GIG ONE"
    assert "gig.hyp.json → hyperspace.project/2" in capsys.readouterr().err


# ---------------------------------------------------------------- bindings.json

def test_bindings_json_performer_rows_move_into_the_startup_preset(home):
    r = boot(home)
    doc = read(bindings_path(home))
    assert set(doc) == {"schema", "profile", "bindings"} and doc["schema"] == routing.SCHEMA
    rows = [Binding.from_json(d) for d in doc["bindings"]]
    # the session's controls only: no performer row, no preset-layer row,
    # no macros, no values
    assert not any(b.op in MOD_OPS for b in rows)
    assert not any(b.layer == "preset" for b in rows)
    assert all(routing.is_session_row(b) for b in rows)
    # keys, pad, the invariant rows, and the band strip's device knobs now global
    assert any(b.source == "key:RIGHT" for b in rows) and any(b.scheme == "pad" for b in rows)
    strip = {b.source: b.layer for b in rows if b.target.startswith("band.sel.")}
    assert strip and set(strip.values()) == {"global"}
    assert any(b.target == "band.0.post" and b.layer is None for b in rows)     # a fader
    assert any(b.target == routing.SHIFT_PARAM for b in rows)
    assert not any(b.source == KNOB["source"] for b in rows)
    # the startup preset holds them, and the launch put them live
    start = preset_file(home, "MY WAVE")
    assert [d for d in start["routes"] if d["source"].startswith("hand:")] == named(LEARNED[:2])
    assert {"source": "lane:3", "target": "fx.mix", "op": "push", "value": 0.2} in start["routes"]
    assert {**KNOB, "layer": "preset"} not in start["desk"] and KNOB in start["desk"]
    live = r.router.table
    hand = [b for b in live.routes() if b.source == "hand:right.y"]
    assert [(b.target, b.op) for b in hand] == [("view.bright", "position")]
    assert live.owner("view.bright").source == "hand:right.y"      # the learned row plays
    assert any(b.source == KNOB["source"] and b.layer == "preset" for b in live.desk())
    assert live.macros_doc() == start["macros"] and r.reg["macro.2"].value == 0.4
    assert live.carried is None and not r.lib.is_dirty("presets")


def test_every_rewrite_keeps_a_backup_and_never_over_a_hand_made_one(home, capsys):
    before_project = (home / "projects" / "default.hyp.json").read_text()
    before_bindings = bindings_path(home).read_text()
    # a backup of that name is there already (a WP3-era build's): kept
    (home / "bindings.json.bak-v2").write_text("an older backup")
    r = boot(home)
    err = capsys.readouterr().err
    assert (home / "projects" / "default.hyp.json.bak-v1").read_text() == before_project
    assert (home / "bindings.json.bak-v2").read_text() == "an older backup"
    dated = sorted(home.glob("bindings.json.bak-v2-*"))
    assert len(dated) == 1 and dated[0].read_text() == before_bindings
    assert (home / "bindings.json.bak-mine").read_text() == "my own copy"
    # one note per rewritten file, naming its backup, on stderr and summed up
    assert "migrate: default.hyp.json → hyperspace.project/2 (5 presets); the old file " \
           "kept as default.hyp.json.bak-v1" in err
    assert f"the old file kept as {dated[0].name}" in err
    assert r.lib.warning.startswith("plan 13 migration: 2 file(s) rewritten")
    # the user routing preset is not rewritten at all
    assert read(home / "bindings" / "show-a.json") == ROUTING_PRESET
    assert not list((home / "bindings").glob("*.bak-*"))


def test_a_rewrite_whose_backup_cannot_be_made_is_not_done(home, monkeypatch, capsys):
    """A backup that fails leaves the file as it was: never a rewrite
    without its copy."""
    def refuse(p, data):
        raise OSError("read-only")

    monkeypatch.setattr(routing, "_write_new", refuse)
    before = (tree(home)["projects/default.hyp.json"][0], tree(home)["bindings.json"][0])
    r = boot(home)
    assert (tree(home)["projects/default.hyp.json"][0], tree(home)["bindings.json"][0]) == before
    assert any("NOT migrated: no backup could be made" in n for n in r.notes)
    # the project that stayed will take the table's part on the next try:
    # no MIGRATED stand-in, and bindings.json keeps it meanwhile
    assert not (home / "presets" / "migrated.json").exists()
    assert r.router.table.carried is not None
    assert sorted(p.name for p in home.glob("*.bak-*")) == ["bindings.json.bak-mine"]
    monkeypatch.undo()
    again = boot(home)                                   # the next launch tries again
    assert read(home / "projects" / "default.hyp.json")["schema"] == "hyperspace.project/2"
    assert again.router.table.carried is None


# ---------------------------------------------------------------- routes-only files

def test_routes_only_files_become_full_presets(home):
    """Decision 10, the user's side: a routing preset becomes a full preset
    — its values (less the session's), the effects its routes drive
    switched on (PR #29's rule), its routes, its macros, no `desk` — and
    the file stays where it was, untouched, with a note that the folder is
    no longer read. The factory side: the routing presets that shipped are
    factory presets (tests/test_presets.py pins them)."""
    r = boot(home)
    made = preset_file(home, "Show A")
    assert made["schema"] == "hyperspace.preset/2" and "desk" not in made
    assert made["values"] == {"fx.acid.speed": 2.0, "fx.on": True, "fx.acid.on": True}
    assert made["routes"] == named(ROUTING_PRESET["bindings"]) and made["macros"] == {}
    assert read(home / "bindings" / "show-a.json") == ROUTING_PRESET
    assert (home / "bindings" / preset.NOT_READ).is_file()
    assert "bindings" not in r.lib.groups()
    r.presets.load("Show A")
    assert r.reg["fx.acid.on"].value is True and r.reg["tempo.bpm"].value != 99.0
    assert [b.source for b in r.router.table.routes()] == ["hand:right.pitch", "hand:right.y"]
    assert len(r.router.table.desk()) == len(preset.fresh_desk())    # no desk: the factory layer
    # the factory's
    for name in ("legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play"):
        assert r.lib.is_factory("presets", name)
    assert not (FACTORY / "bindings").exists()


# ---------------------------------------------------------------- once

def test_the_migration_runs_once(home):
    first = boot(home)
    assert first.notes
    after = tree(home)
    second = boot(home)
    assert second.notes == [] and tree(home) == after
    assert second.lib.current("presets") == "DEFAULT SAVED" and not second.lib.error
    assert [b.source for b in second.router.table.routes() if b.source.startswith("hand")] \
        == ["hand:right.y", "hand:left.y"]


def test_a_home_with_no_project_keeps_its_routes_in_a_migrated_preset(tmp_path):
    home = owners_home(tmp_path, project=False, routing_preset=False)
    r = boot(home)
    kept = preset_file(home, preset.MIGRATED)
    assert kept["name"] == "MIGRATED"
    assert [d for d in kept["routes"] if d["source"].startswith("hand:")] == named(LEARNED[:2])
    assert KNOB in kept["desk"] and kept["macros"]["macro.2"]["subs"]
    assert kept["values"]["macro.2"] == 0.4 and "view.shape" in kept["values"]
    assert not any(k.partition(".")[0] in SESSION_GROUPS for k in kept["values"])
    # the user's default project, made from the factory's, starts on it
    doc = read(home / "projects" / "default.hyp.json")
    factory = read(FACTORY / "projects" / "default.hyp.json")
    assert doc["schema"] == "hyperspace.project/2" and doc["startup"] == "MIGRATED"
    assert doc["bank"] == ["MIGRATED", *factory["bank"][:7]]     # the last house preset off
    assert any(f"{factory['bank'][7]!r} left the bank" in n for n in r.notes)
    assert r.lib.current("presets") == "MIGRATED"
    assert r.router.table.owner("view.bright").source == "hand:right.y"
    assert not any(b.op in MOD_OPS for b in Bindings.load(bindings_path(home)).bindings)
    # a user default already at schema 2 keeps its bank, one slot along, and a backup
    home2 = tmp_path / "two"
    owners_home(home2, project=False, routing_preset=False)
    mine = dict(factory, bank=["EMBER ORBIT", None, "HEX ENGINE", None, None, None, None, None],
                startup="EMBER ORBIT")
    (home2 / "projects" / "default.hyp.json").write_text(json.dumps(mine))
    boot(home2)
    doc2 = read(home2 / "projects" / "default.hyp.json")
    assert doc2["bank"] == ["MIGRATED", "EMBER ORBIT", None, "HEX ENGINE", None, None, None, None]
    assert doc2["startup"] == "MIGRATED"
    assert read(home2 / "projects" / "default.hyp.json.bak-v2") == mine


def test_an_equal_preset_is_pointed_at_and_a_users_is_never_overwritten(tmp_path):
    """`preset.put_preset`: an equal preset (the user's, else the
    factory's) is pointed at and nothing written; a factory one that
    differs is shadowed by a user file; a user file that differs is never
    touched — the new one takes a numbered name."""
    house = read(preset.FACTORY_DIR / "ember-orbit.json")
    name, path = preset.put_preset(tmp_path, dict(house, note="another note"))
    assert (name, path) == ("EMBER ORBIT", None)                # equal to the factory's
    changed = dict(house, values={**house["values"], "view.shape": 3})
    name, path = preset.put_preset(tmp_path, changed)
    assert name == "EMBER ORBIT" and path == tmp_path / "presets" / "ember-orbit.json"
    assert preset.put_preset(tmp_path, changed) == ("EMBER ORBIT", None)   # now the user's
    other = dict(house, values={**house["values"], "view.shape": 4})
    mine = path.read_text()
    name, path2 = preset.put_preset(tmp_path, other)
    assert name == "EMBER ORBIT 2" and path2 == tmp_path / "presets" / "ember-orbit-2.json"
    assert path.read_text() == mine                             # never overwritten
    assert read(path2)["name"] == "EMBER ORBIT 2"


def test_a_migrated_preset_never_hides_a_factory_preset_of_another_name(tmp_path):
    """Review of PR #66: the library keys files by slug, so a user file
    `party-trip.json` would take the factory TRIP (same slug, another
    display name) off the list and off F5. A routing preset the owner saved
    as `party-trip` becomes `party-trip 2`; TRIP still loads by F-key."""
    home = owners_home(tmp_path, routing_preset=False)
    (home / "bindings").mkdir()
    (home / "bindings" / "party-trip.json").write_text(json.dumps(
        {"schema": routing.SCHEMA_V2, "name": "party-trip", "bindings": [
            {"source": "hand:7", "target": "fx.mix", "op": "position"}]}))
    r = boot(home)
    assert not (home / "presets" / "party-trip.json").exists()
    assert preset_file(home, "party-trip 2")["routes"][0]["target"] == "fx.mix"
    assert "TRIP" in r.lib.list("presets") and r.lib.is_factory("presets", "TRIP")
    r.lib.project.load("party")
    r.reg["preset.load.4"].fire()
    assert r.lib.current("presets") == "TRIP"


def test_a_preset_that_cannot_be_written_never_stops_the_launch(home):
    """Review of PR #66: a read-only presets folder (a full disk) is said,
    not fatal; nothing is marked done, so the next launch tries again."""
    (home / "presets").mkdir()
    (home / "presets").chmod(0o555)
    try:
        r = boot(home)                                   # no exception
        assert any("NOT converted" in n for n in r.notes)
        assert not (home / "bindings" / preset.NOT_READ).exists()
        assert read(home / "bindings" / "show-a.json") == ROUTING_PRESET
    finally:
        (home / "presets").chmod(0o755)
    again = boot(home)
    assert (home / "bindings" / preset.NOT_READ).exists()
    assert preset_file(home, "Show A")["routes"] == named(ROUTING_PRESET["bindings"])
    assert read(home / "projects" / "default.hyp.json")["schema"] == "hyperspace.project/2"
    assert again.router.table.carried is None


def test_a_launch_that_could_not_rewrite_bindings_json_does_not_take_the_default(home):
    """Review of PR #66: when the projects were converted but bindings.json
    was not rewritten, the next launch finds its routes already in a preset
    — no MIGRATED, the default project left as the first launch made it —
    and only rewrites bindings.json."""
    boot(home)
    project = (home / "projects" / "default.hyp.json").read_text()
    bindings_path(home).write_text(json.dumps(bindings_v2()))    # as if the rewrite never landed
    r = boot(home)
    assert not (home / "presets" / "migrated.json").exists()
    assert (home / "projects" / "default.hyp.json").read_text() == project
    assert r.lib.current("presets") == "DEFAULT SAVED"
    assert not any(b.op in MOD_OPS for b in Bindings.load(bindings_path(home)).bindings)
    assert any("already in a preset" in n for n in r.notes)


# ---------------------------------------------------------------- hand names

def test_the_migration_names_the_hand_rows(tmp_path):
    """Decision register row 20 (plan 13 WP5b): every preset the migration
    writes names its hand lanes — sources, gates — by the layout the rig
    has at migration time: the rig's `[hands] dofs` when `[hands]` is
    enabled, else the default layout; a note says which. It runs once,
    and a user preset with numbers loaded later is read as it is."""
    DEFAULT = "the default layout (dofs x, y, z, roll, pitch, yaw)"
    home = owners_home(tmp_path / "off")
    r = boot(home, {"enabled": False, "dofs": ["roll"]})    # configured, off: the default
    assert f"bindings.json: 3 hand address(es) named by {DEFAULT}" in r.notes
    assert f"bindings/show-a.json: 2 hand address(es) named by {DEFAULT}" in r.notes
    for p in sorted((home / "presets").glob("*.json")):
        assert not re.search(r'"hand:\d', p.read_text()), p.name
    rows = [d for d in preset_file(home, "MY WAVE")["routes"] if d["source"].startswith("hand:")]
    assert [(d["source"], d.get("when")) for d in rows] == [
        ("hand:right.y", None), ("hand:left.y", "hand:right.pinch.index")]
    assert [d["source"] for d in preset_file(home, "Show A")["routes"]] == [
        "hand:right.pitch", "hand:right.y"]
    assert boot(home).notes == []                            # once
    # the rig's own layout, [hands] on with its dofs reordered: lane 7 is
    # the right hand's second axis — x on this rig — and the note says so
    rig = owners_home(tmp_path / "rig")
    dofs = ["y", "x", "z", "roll", "pitch", "yaw"]
    r2 = boot(rig, {"enabled": True, "dofs": dofs})
    layout = f"the rig's layout ([hands] dofs {', '.join(dofs)})"
    assert f"bindings.json: 3 hand address(es) named by {layout}" in r2.notes
    rows = [d for d in preset_file(rig, "MY WAVE")["routes"] if d["source"].startswith("hand:")]
    assert [(d["source"], d.get("when")) for d in rows] == [
        ("hand:right.x", None), ("hand:left.x", "hand:right.pinch.index")]
    # a user preset saved with numbers later (an older build's) still reads
    (home / "presets" / "numbers.json").write_text(json.dumps(
        {"schema": preset.SCHEMA, "name": "numbers", "values": {},
         "routes": [{"source": "hand:7", "target": "view.bright", "op": "position",
                     "when": "hand:18"}]}))
    r.lib._sync(home / "presets" / "numbers.json")
    assert r.presets.load("numbers") == []
    row = r.router.table.owner("view.bright")
    assert (row.source, row.when) == ("hand:7", "hand:18")   # not rewritten at load
    assert r.router.lane(row.source) == ("hand", 7)


# ---------------------------------------------------------------- nothing lost

def _union(docs):
    routes, desk, macros = set(), set(), {}
    for d in docs:
        routes |= {json.dumps(Binding.from_json(x).to_json(), sort_keys=True)
                   for x in d.get("routes") or []}
        desk |= {(x["source"], x["target"], x["op"]) for x in d.get("desk") or []}
        macros.update(d.get("macros") or {})
    return routes, desk, macros


def test_nothing_is_lost(home):
    """The union of the routes, preset-layer rows, macros and performance
    values the home held before is what its presets hold after."""
    raw = bindings_v2()
    table = Bindings.from_json(raw)                    # the rows as the table reads them
    # every hand lane by name after (row 20): the same rows, renamed
    before_routes = {json.dumps(x, sort_keys=True)
                     for x in named([b.to_json() for b in table.routes()])}
    before_routes |= {json.dumps(Binding.from_json(x).to_json(), sort_keys=True)
                      for x in named(ROUTING_PRESET["bindings"])}
    before_desk = {(b.source, b.target, b.op) for b in table.desk()}
    assert (KNOB["source"], KNOB["target"], "abs") in before_desk
    before_macros = table.macros_doc()
    boot(home)
    docs = [read(p) for p in sorted((home / "presets").glob("*.json"))]
    routes, desk, macros = _union(docs)
    assert routes == before_routes
    assert desk == before_desk
    assert macros == before_macros
    # the performance values: every slot's, and the macros' bases, in its preset
    for k, name in enumerate(SLOT_NAMES):
        held = preset_file(home, name)["values"]
        for pid, v in {**slot(k)["values"], **raw["values"]}.items():
            if pid.partition(".")[0] not in SESSION_GROUPS:
                assert held[pid] == (slot(k)["values"].get(pid, v)), (name, pid)
    # the project's own look (what it restored on open) is a preset too
    saved = preset_file(home, "DEFAULT SAVED")["values"]
    for pid, v in {**raw["values"], **project_v1()["values"]}.items():
        if pid.partition(".")[0] not in SESSION_GROUPS:
            assert saved[pid] == project_v1()["values"].get(pid, v), pid
    # the session values went to the project, not lost
    session = read(home / "projects" / "default.hyp.json")["session"]
    for pid in ("scene.select", "master.gain", "band.0.atk", "tempo.bpm", "hands.smooth"):
        assert pid in session, pid
    made = preset_file(home, "Show A")["values"]
    assert made["fx.acid.speed"] == 2.0                   # its session id (tempo.bpm) dropped
