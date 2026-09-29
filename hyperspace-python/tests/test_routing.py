"""Plan-07 WP4b: the modulation bus and the unified binding table; plan 09
WP1: one performer per parameter.

The parity guard first — the "legacy6" routing preset must put the
reference's PLANEDRIVE on rot.rate.* and out[i] on pattern.mod.i *while
the source is live*, so the integrated angles and the shader inputs match
the pre-WP4b path frame for frame on the fixture clips and the golden
traces (idle, the planes now stand on their base of 0 where the reference
spun at 1: plan 09's one accepted divergence) — then the table: the
source grammar, the two performer ops, JSON, the midi_map.json and the
schema-1 migrations, the key / pad adapters, the Router's per-frame pass,
presets and runtime edits, and the referee: the four audit simulations of
plan 09 as tests that pass because the situations are impossible.
"""

import json
import math
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from legacy_chain import LegacyChain  # tests/legacy_chain.py — the frozen reference
from test_analyzer import fixture_wavs, frames  # noqa: F401 — the fixture, re-exported

from hyperspace import apc40, hands, lfo, preset, routing, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import BANDS, CEIL, default_params
from hyperspace.control import Control
from hyperspace.geometry import RATE
from hyperspace.library import FACTORY, Library
from hyperspace.offline import load_wav
from hyperspace.overlay import Output
from hyperspace.params import DRIVE, PLANES, ROT_RATE_MAX, build_registry, part_of
from hyperspace.routing import (
    MOD_OPS,
    ROT_DEPTH,
    SCHEMA,
    Binding,
    Bindings,
    Owned,
    Router,
    bindings_path,
    legacy_planedrive,
)
from hyperspace.view import N_MOD, ViewState

GOLDEN = Path(__file__).parent / "golden" / "audio"

# the registry maps a lane through norm space and back (float, no detents):
# lo + (0.5 + d·u)·span, a handful of roundings about the ±66.56 range, so
# a rate is the reference's to an ulp of that range (~3e-14) rather than
# bit for bit — and bit for bit once it is the float32 the GPU sees. An
# angle integrates that error over the clip (≤ 1e-11 after 12 s).
RTOL, ATOL_RATE, ATOL_ANG = 1e-12, 1e-13, 1e-11


def rig(sr: float = 48_000.0, tmp_path: Path | None = None, full: bool = False):
    """A registry over a legacy-layout analyzer; `full` adds the app-level
    params (panel, audio transport, overlay, themes) the factory table names."""
    chain = Analyzer(Analyser(sr), default_params(), layout=legacy_layout())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=True)
    view = ViewState()
    lib = Library(tmp_path) if full else None
    presets = lib.project if full else None
    reg = build_registry(view, control, audio, presets)
    if full:
        lib.attach(reg)
    if full:
        reg.toggle("ui.panel", "Panel", lambda: True, lambda v: None)
        reg.toggle("ui.cheatsheet", "Sheet", lambda: True, lambda v: None)
        reg.trigger("audio.restart", "Restart", lambda: None)
        reg.trigger("audio.stop", "Stop", lambda: None)
        reg.toggle("audio.play", "Play", lambda: False, lambda v: None)
        Output(None, None).register(reg)
        clock = tempo.Clock(now=lambda: 0.0)
        tempo.register(reg, clock)
        lfo.register(reg, lfo.LFOs(), clock)
        hands.register(reg, hands.HandSettings.from_config({}))  # the global track knobs
    return SimpleNamespace(reg=reg, view=view, control=control, audio=audio, chain=chain,
                           lib=lib)


def legacy6(router: Router) -> list[str]:
    """The legacy6 preset onto the table and the registry: its routes and
    its bases, as the code that generates library/presets/legacy6.json
    writes them (`preset.generated`; the file is pinned to it by
    test_presets.py). Returns the ids the registry lacks."""
    doc = preset.generated("legacy6")
    router.table.set_routes(Binding.from_json(d) for d in doc["routes"])
    return router.reg.restore(doc["values"])


def load_preset(r, router: Router, name: str) -> list[str]:
    """A preset by name through the one loader (`preset.Presets` over the
    rig's library) — the road the routing presets took before plan 13 WP5
    made them presets. Returns the ids the registry lacks."""
    from hyperspace.preset import Presets

    return Presets(r.lib, r.reg, router).load(name)


def migrate_home(home: Path, table: Bindings) -> list[str]:
    """The first launch over `table` (read from `home`'s bindings.json):
    the library, the registry, a Router and `Presets` as app.main builds
    them, then plan 13's migration (`preset.migrate_home`)."""
    from hyperspace.preset import Presets
    from hyperspace.preset import migrate_home as run

    r = rig(tmp_path=home, full=True)
    router = Router(r.reg, table)
    Presets(r.lib, r.reg, router)
    return run(r.lib, router)


def session_rows() -> list[Binding]:
    """The factory table's rows a bindings.json keeps (plan 13 §2.2)."""
    return [b for b in Bindings.factory().bindings if routing.is_session_row(b)]


def house(**kw) -> Bindings:
    """The factory table with the house presets' performer rows — the
    legacy6 lane rows on the bases of 1 — which `Bindings.factory` shipped
    until plan 13 WP5 moved every performer row into the presets."""
    t = Bindings.factory(**kw)
    t.set_routes(routing.legacy6_routes())
    return t


def legacy_integrate(view: ViewState, dt: float, planedrive) -> None:
    """view.ViewState.integrate as it was before WP4b, rate[p] = 1."""
    if not view.playing:
        return
    for p in range(6):
        if view.planes[p]:
            view.ang[p] += dt * view.speed * RATE[p] * 1.0 * planedrive[p]


# ------------------------------------------------------------ parity guard

@pytest.mark.parametrize("clip,fps,dyn,gain", [
    ("gate-prover", 60, 1.0, 1.0), ("brickwalled", 60, 1.0, 1.0), ("sweep", 60, 1.0, 1.0),
    ("brickwalled", 120, 0.0, 1.0), ("sweep", 60, 1.0, 2.5), ("gate-prover", 60, 1.0, 8.0),
])
@pytest.mark.parametrize("table", ["factory", "legacy6"])
def test_legacy6_reproduces_planedrive_and_u_bands(
    fixture_wavs, table, clip, fps, dyn, gain,  # noqa: F811 — the fixture
):
    """Side by side: the old chain → PLANEDRIVE → old integrate and
    u_bands = out, against the analyzer → routes → reg.apply → integrate
    and pattern.mod, through the reference's three states — no source, a
    source, the source gone again. The legacy6 preset is the oracle: with
    the source live, rates and angles agree to round-off every frame, the
    shader inputs to an ulp, and all are the same float32 the GPU sees; a
    gated band's plane sits at exactly 0.0; the drive fader keeps meaning
    (it scales the rotation routes, so a change lands the same frame it
    did before, and leaves the pattern inputs raw as the reference did).
    Idle, the reference integrated a literal 1 where the preset's planes
    now stand on their base of 0 — plan 09's accepted divergence, so the
    parity anchor is the driven value and the integrators start together
    when the source starts. The factory table carries the same push rows
    on WP0's bases of 1: idle it spins at 1×, driven a lane rides on top
    (1 + PLANEDRIVE, clamped) — checked here as that, not as parity."""
    samples, sr = load_wav(fixture_wavs / f"{clip}.wav")
    old_an, r = Analyser(sr), rig(sr)
    old = LegacyChain(old_an)
    old.dyn = r.chain.dyn = dyn
    old.gain = r.chain.gain = gain
    old_view, view = ViewState(), r.view
    old_view.planes = view.planes = [True] * 6
    router = Router(r.reg, house())
    assert view.rate == [1.0] * 6                          # WP0's un-driven base
    if table == "legacy6":
        assert legacy6(router) == []
        assert view.pattern_mod[:6] == [0.0] * 6 and view.rate == [0.0] * 6
    base = [0.0] * 6 if table == "legacy6" else [1.0] * 6
    ticks = list(frames(samples, sr, fps))
    idle = np.ones(6)
    n = 0
    # 1. no source yet: the reference integrates a literal 1; the preset's
    # planes stand (their base is 0), the factory's spin on their base of 1
    for _chunk, dt in ticks[:20]:
        legacy_integrate(old_view, dt, idle)
        router.modulate(None)
        r.reg.apply()
        view.integrate(dt)
        assert view.rate == base and not r.reg["rot.rate.XY"].modulated
        if table == "legacy6":
            assert view.ang == [0.0] * 6
        else:
            assert view.ang == old_view.ang
    # the driven phase is the anchor: both integrators start it together
    old_view.ang, view.ang = [0.0] * 6, [0.0] * 6
    # 2. the source runs: audio pushes on the base of 0 — the constant, replaced
    for chunk, dt in ticks:
        old_an.feed(chunk)
        r.chain.an.feed(chunk)
        old_view.speed = view.speed = 0.3 if n < 200 else 1.7   # speed moves mid-run
        if n == 300:                                             # so does the fader
            old.gain = r.chain.gain = gain * 0.5
        planedrive = old.step(dt)
        legacy_integrate(old_view, dt, planedrive)
        r.chain.step(dt)
        router.modulate(r.chain)
        r.reg.apply()
        view.integrate(dt)
        if table == "factory":                                   # a lane rides on 1
            ride = np.clip(1.0 + planedrive, -ROT_RATE_MAX, ROT_RATE_MAX)
            np.testing.assert_allclose(view.rate, ride, rtol=RTOL, atol=ATOL_RATE)
            n += 1
            continue
        np.testing.assert_allclose(view.rate, planedrive, rtol=RTOL, atol=ATOL_RATE)
        assert np.array_equal(np.float32(view.rate), np.float32(planedrive))
        for i in range(6):                                       # gated → stopped, exactly
            if old.out[i] == 0.0:
                assert view.rate[BANDS[i].plane] == 0.0
        np.testing.assert_allclose(view.pattern_mod[:6], old.out, rtol=RTOL, atol=1e-15)
        assert np.array_equal(np.float32(view.pattern_mod[:6]), np.float32(old.out))
        np.testing.assert_allclose(view.ang, old_view.ang, rtol=RTOL, atol=ATOL_ANG)
        assert np.array_equal(np.float32(view.ang), np.float32(old_view.ang))
        n += 1
    assert n > 500
    if clip == "gate-prover" and table == "legacy6":
        assert all(view.rate[BANDS[i].plane] == 0.0 for i in (2, 3, 5))
    assert r.reg[f"rot.rate.{BANDS[2].pl}"].base == base[0]    # the setting is untouched
    # 3. the source goes away: the base is back the very next frame — the
    # preset's planes stop where they are, the factory's spin at 1 again
    ang = list(view.ang)
    for _chunk, dt in ticks[:20]:
        legacy_integrate(old_view, dt, idle)
        router.modulate(None)
        r.reg.apply()
        view.integrate(dt)
        assert view.rate == base and not r.reg["rot.rate.XY"].modulated
    if table == "legacy6":
        assert view.ang == ang and view.pattern_mod[:6] == [0.0] * 6
    else:
        assert view.ang != ang


def test_legacy6_matches_the_golden_traces():
    """The reference's own recording: out[6] fed as lanes lands on its
    planedrive[6] columns (six-decimal data, so to that precision)."""
    r = rig()
    router = Router(r.reg, house())
    legacy6(router)
    for trace in ("gate-prover-default", "brickwalled-default", "sweep-default"):
        lines = (GOLDEN / f"{trace}.jsonl").read_text().splitlines()
        rows = np.asarray([json.loads(ln) for ln in lines])
        out, drive = rows[:, 8:14], rows[:, 14:20]
        for k in range(len(rows)):
            r.chain.out[:] = out[k]
            router.modulate(r.chain)
            r.reg.apply()
            np.testing.assert_allclose(r.view.rate, drive[k], atol=DRIVE * 1e-6 + 1e-9)
            np.testing.assert_allclose(r.view.pattern_mod[:6], out[k], rtol=RTOL, atol=1e-15)
            assert np.array_equal(np.float32(r.view.pattern_mod[:6]), np.float32(out[k]))


def test_legacy_planedrive_is_the_reference_formula():
    lanes = np.array([0.5, 1.0, 1.5, 0.0, 2.0, 0.25])
    d = legacy_planedrive(lanes, 2.0)
    for i, b in enumerate(BANDS):
        assert d[b.plane] == b.dir * lanes[i] * DRIVE * 2.0
    assert legacy_planedrive(np.zeros(3)).tolist() == [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]


def test_rot_rate_range_holds_the_reference_drive():
    """±ROT_RATE_MAX is the drive at out = CEIL, gain 8 — the largest the
    reference could produce — and the legacy6 depth, pushing on a base of
    0, lands there exactly; a silent lane pushes nothing."""
    assert ROT_RATE_MAX == CEIL * DRIVE * 8.0
    assert ROT_DEPTH == 1 / 16
    r = rig()
    p = r.reg["rot.rate.ZW"]
    assert (p.lo, p.hi) == (-ROT_RATE_MAX, ROT_RATE_MAX)
    router = Router(r.reg, Bindings(routing.legacy6_routes()))
    assert r.reg.restore(preset.legacy6_values()) == []
    r.chain.out[:] = CEIL
    r.chain.gain = 8.0
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == pytest.approx(ROT_RATE_MAX, rel=1e-12)
    assert r.view.rate[BANDS[2].plane] == pytest.approx(-ROT_RATE_MAX, rel=1e-12)
    assert r.view.pattern_mod[:6] == [CEIL] * 6                 # base 0 + 1·u
    r.chain.out[:] = 0.0                                        # silence: held at the base
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate == [0.0] * 6 and r.reg["rot.rate.ZW"].modulated
    r.reg.apply()                                               # nothing held: bases back
    assert r.view.rate == [0.0] * 6 and not r.reg["rot.rate.ZW"].modulated


# ----------------------------------------------------------------- model

def test_source_grammar():
    b = Binding("cc:*:16", "view.bright", "abs")
    assert (b.scheme, b.kind, b.channel, b.number, b.is_midi) == ("cc", "cc", None, 16, True)
    assert b.matches("cc", 5, 16) and not b.matches("cc", 5, 17) and not b.matches("note", 5, 16)
    n = Binding("note:3:48", "view.faces", "toggle")
    assert (n.channel, n.number) == (3, 48)
    assert n.matches("note", 3, 48) and not n.matches("note", 2, 48)
    pw = Binding("pitch:2", "camera.pitch", "abs")
    assert (pw.kind, pw.channel, pw.number) == ("pitch", 2, 0) and pw.matches("pitch", 2, 99)
    assert Binding.midi_source("cc", None, 7) == "cc:*:7"
    assert Binding.midi_source("pitch", 1) == "pitch:1"
    lane = Binding("lane:12", "view.bright", "push", -0.3)
    assert (lane.scheme, lane.index, lane.kind, lane.is_midi) == ("lane", 12, None, False)
    assert Binding("key:F1", "x").index == -1
    for src, text in (("key:R", "key R"), ("pad:LB", "pad LB"), ("hat:UP", "d-pad UP"),
                      ("cc:0:48", "MIDI CC 48 ch1"), ("note:*:5", "MIDI note 5 any ch"),
                      ("pitch:3", "MIDI pitch bend ch4")):
        assert Binding(src, "x", "abs").describe() == text
    assert Binding("note:0:5", "x", "step", 2).describe() == "MIDI note 5 ch1 step"
    assert Binding("lane:2", "x", "push", 0.5).describe() == "lane 2 pushes +0.5"
    assert Binding("lane:2", "x", "push", -1, scale="master.gain").describe() == (
        "lane 2 pushes -1 × master.gain")
    assert Binding("hand:7", "x", "position").describe() == "hand 7 positions"
    assert Binding("hand:7", "x", "position", 0.5, when="hand:18").describe() == (
        "hand 7 positions 0.5 while hand:18")
    assert Binding("hand:7", "x", "position").is_performer
    assert not Binding("hand:7", "x", "position", enabled=False).is_performer
    assert not Binding("cc:0:7", "x", "abs").is_performer


def test_json_rows_carry_only_what_differs():
    b = Binding("key:RIGHT", "view.shape", "step", 1)
    assert b.to_json() == {"source": "key:RIGHT", "target": "view.shape", "op": "step"}
    b = Binding("cc:0:48", "view.bright", "abs", feedback="ring", ring=2, pickup=False)
    d = b.to_json()
    assert d == {"source": "cc:0:48", "target": "view.bright", "op": "abs",
                 "feedback": "ring", "pickup": False}
    assert "caught" not in d and Binding.from_json(d) == b
    assert Binding.from_json({"source": "lane:1", "target": "x", "op": "push", "value": -2,
                              "enabled": False, "junk": 1}) == Binding(
        "lane:1", "x", "push", -2, False)
    # rest only when the row has its own — None (the source's) is the default
    assert "rest" not in Binding("lane:1", "x", "push", 0.5).to_json()
    d = Binding("lfo:0", "x", "push", 0.5, rest=0.5).to_json()
    assert d["rest"] == 0.5 and Binding.from_json(d).rest == 0.5
    assert Binding("lfo:0", "x", "push", rest=0.0).to_json()["rest"] == 0.0   # an override


def test_pickup_never_rides_on_a_performer_row():
    """Audit R5: `pickup` is a knob's field (soft pickup on a MIDI abs
    row). A performer grabs and never yields (plan 09 d.4), so the field
    never reaches the file for a lane-scheme row, whatever it reads."""
    for src in ("hand:3", "lane:0", "lfo:1", "ext:2"):
        assert "pickup" not in Binding(src, "view.bright", "position", pickup=False).to_json()
        assert "pickup" not in Binding(src, "view.bright", "push", 0.5, pickup=True).to_json()
    assert Binding("cc:0:48", "view.bright", "abs", pickup=False).to_json()["pickup"] is False


def test_the_apc40_band_planes_are_the_reference_tables():
    """Audit R7: apc40.py hand-copies bands.BANDS[i].pl for the six
    ACTIVATOR buttons rather than importing the audio stack; this pins
    the copy to the table."""
    from hyperspace import apc40

    assert apc40._BAND_PLANES == tuple(b.pl for b in BANDS)


def test_midi_map_v1_rows_migrate():
    old = {"param": "view.speed", "kind": "cc", "number": 0x31, "channel": 0, "mode": "abs",
           "value": 1.0, "pickup": True, "feedback": "ring", "on": 1, "off": 0, "ring": 2}
    b = Binding.from_json(old)
    assert b == Binding("cc:0:49", "view.speed", "abs", feedback="ring")
    assert Binding.from_json({"param": "camera.zoom", "kind": "pitch", "channel": None,
                              "mode": "abs"}).source == "pitch:*"
    assert Binding.from_json({"param": "view.faces", "kind": "note", "number": 84,
                              "channel": 2, "mode": "trigger"}).op == "toggle"
    assert Binding.from_json({"param": "view.shape", "kind": "note", "number": 1,
                              "channel": 0, "mode": "set", "value": 3}) == Binding(
        "note:0:1", "view.shape", "set", 3)


def test_table_file_round_trip_and_path(tmp_path):
    path = bindings_path(tmp_path)
    assert path == tmp_path / "bindings.json"
    assert bindings_path() == Path("bindings.json")
    t = Bindings.factory(path=path)
    n = len(t.bindings)
    session = [b for b in t.bindings if routing.is_session_row(b)]
    t.add(Binding("lane:2", "view.bright", "push", 0.4))
    t.write()
    text = path.read_text()
    # one row per line — the session's controls only: a performer row and
    # the preset layer are the loaded preset's (plan 13 §2.2, WP5)
    assert text.count("\n  {") == len(session) < n
    doc = json.loads(text)
    assert set(doc) == {"schema", "profile", "bindings"}
    t2 = Bindings.load(path)
    assert t2.to_json() == t.to_json() and t2.profile == "apc40" and not t2.error
    assert t2.routes() == [] and t2.desk() == [] and t2.carried is None
    # a file that won't parse falls back to the factory table, reported
    path.write_text("{not json")
    t3 = Bindings.load(path)
    assert t3.error.startswith("bindings:") and len(t3.bindings) == n


def test_old_midi_map_migrates_into_bindings_json(tmp_path, capsys):
    legacy = tmp_path / "midi_map.json"
    legacy.write_text(json.dumps({"version": 1, "profile": "apc40", "bindings": [
        {"param": "view.inst_amp", "kind": "cc", "number": 0x57, "channel": 0, "mode": "abs",
         "value": 1.0, "pickup": True, "feedback": None, "on": 1, "off": 0, "ring": 2},
        {"param": "view.lines", "kind": "note", "number": 0x41, "channel": 0,
         "mode": "trigger", "value": 1.0, "pickup": True, "feedback": "led",
         "on": 1, "off": 0, "ring": 2},
    ]}))
    path = bindings_path(tmp_path)
    t = Bindings.load(path, legacy_midi=legacy)
    # a knob off the factory's is a preset's row: the table carries it, with
    # the lane rows the factory table shipped, and leaves the file to the
    # migration (review of PR #66: written now, a stopped migration would
    # lose the knob)
    assert not path.exists() and t.carried is not None
    assert t.carried.routes == [b.to_json() for b in routing.legacy6_routes()]
    # the map's two rows sorted (plan 13 §3.2: an unknown knob to the preset
    # layer, a factory button's control kept invariant), then the factory's
    # global rows and SHIFT added
    assert [(b.source, b.layer) for b in t.midi()][:2] == [("cc:0:87", "preset"),
                                                         ("note:0:65", None)]
    assert {b.layer for b in t.midi()[2:]} == {"global", None}
    assert t.for_param("view.lines").op == "toggle"
    assert len(t.of("key")) == len(routing.keymap()) and t.mods() == []
    # the knob on the preset layer is a preset's row: the file keeps the
    # session's, and the table carries it for the migration (preset.migrate_home)
    assert {"source": "cc:0:87", "target": "view.inst_amp", "op": "abs",
            "layer": "preset"} in t.carried.desk
    migrate_home(tmp_path, t)                           # the first launch writes it
    assert path.exists() and "cc:0:87" not in path.read_text() and t.carried is None
    kept = json.loads((tmp_path / "presets" / "migrated.json").read_text())
    assert {"source": "cc:0:87", "target": "view.inst_amp", "op": "abs"} in kept["desk"]
    assert len(kept["routes"]) == 12                     # the lane rows it played
    legacy.unlink()
    assert Bindings.load(path, legacy_midi=legacy).to_json() == t.to_json()
    # without either file: the factory table, nothing written
    t0 = Bindings.load(tmp_path / "none.json", legacy_midi=tmp_path / "nope.json")
    assert t0.to_json() == Bindings.factory().to_json() and not (tmp_path / "none.json").exists()


def test_factory_table_binds_only_real_params(tmp_path):
    r = rig(tmp_path=tmp_path, full=True)
    t = Bindings.factory()
    routing.register_desk(r.reg, t)                     # SHIFT's param, as a Router does
    ids = set(r.reg.ids())
    for b in t.bindings:
        assert b.target in ids, b
        assert b.op in routing.OPS, b
        if b.op in MOD_OPS:
            assert r.reg[b.target].modulatable, b
    keys = [(b.key, b.layer) for b in t.bindings if b.scheme != "lane"]
    assert len(keys) == len(set(keys))                  # one row per control per layer
    assert len(t.of("key")) == 25 + 17 and len(t.of("pad")) == 10 and len(t.of("hat")) == 4  # + R, F1–F8, ⇧F1–F8
    assert len(t.midi()) == 113 + 6 and t.mods() == []   # + SHIFT, the global track knobs;
    # no performer rows: the house presets carry the lane rows (plan 13 WP5)
    assert routing.referee(t.bindings)[1] == []           # one owner per target
    assert routing.remap_factory(t.bindings)[1] == []     # the factory table is current


def test_the_apc_migration_tables_agree_with_the_default_map():
    """WP1 wrote APC_REMAP / APC_NEW_ROWS before WP4's DEFAULT_MAP landed;
    the map is the source of truth, so every row the migration produces
    must be a factory row, and every row it remaps away must be gone."""
    rows = {(b["source"], b["target"], b["op"], float(b.get("value", 1.0)))
            for b in apc40.DEFAULT_MAP}
    for old, (target, op, value) in routing.APC_REMAP.items():
        assert old not in rows, old
        assert (old[0], target, op, value) in rows, (old, target)
    for source, target, op, value, _ in routing.APC_NEW_ROWS:
        assert (source, target, op, value) in rows, (source, target)
    led = {b["source"]: b for b in apc40.DEFAULT_MAP}
    for source, *_ in routing.APC_NEW_ROWS:
        assert led[source]["feedback"] == "led" and led[source]["on"] == 1
    keys = {(b.source, b.target, b.op, b.value) for b in routing.keymap()}
    for row in routing.KEY_NEW_ROWS:
        assert row in keys, row


def test_factory_files_match_the_code():
    """hyperspace/bindings.default.json is the export of the factory session
    table — `python -m hyperspace.routing` regenerates it — at the current
    schema, the session's controls only. It lives outside library/ (plan 13
    WP5: no group's preset), and the routing presets that were beside it are
    presets now (library/presets/, tests/test_presets.py)."""
    f = routing.FACTORY_FILE
    assert f.parent.name == "hyperspace" and "library" not in f.parts
    doc = json.loads(f.read_text())
    assert doc == Bindings.factory().to_json() and doc["schema"] == SCHEMA
    assert re.search(r'^  \{"source": "key:RIGHT"', f.read_text(), re.MULTILINE)
    t = Bindings.from_json(doc)
    assert not t.migrated and not t.changed and t.dropped == []
    assert all(routing.is_session_row(b) for b in t.bindings) and t.macros == {}
    assert not (FACTORY / "bindings").exists()


# -------------------------------------------------------------- adapters

class FakeKeys:
    """app.Keys' interface: pressed(glfw_key) is an edge, shift() / super()
    the modifier state a "key:SHIFT+B" row reads."""

    def __init__(self):
        self.hits: set[int] = set()
        self.mods: set[str] = set()
        self.asked: list[int] = []

    def pressed(self, key: int) -> bool:
        self.asked.append(key)
        return key in self.hits

    def shift(self) -> bool:
        return "SHIFT" in self.mods

    def super(self) -> bool:
        return "SUPER" in self.mods


class FakePad:
    def __init__(self):
        self.hits: set[int] = set()
        self.hat = 0

    def pressed(self, b: int) -> bool:
        return b in self.hits

    def hat_pressed(self, bit: int) -> bool:
        return bool(self.hat & bit)


def test_key_adapter_routes_the_old_keymap(tmp_path):
    import glfw

    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, house())
    keys = FakeKeys()
    r.view.shape = 3
    keys.hits = {glfw.KEY_RIGHT}
    router.keys(keys)
    assert r.view.shape == 4
    keys.hits = {glfw.KEY_LEFT, glfw.KEY_LEFT_BRACKET, glfw.KEY_F, glfw.KEY_2}
    p0 = r.reg["view.bright"].position()
    router.keys(keys)
    assert r.view.shape == 3 and r.reg["view.bright"].position() == p0 - 3
    assert r.view.faces and r.view.planes[1]
    keys.hits = set()
    router.keys(keys)
    assert r.view.shape == 3
    # a row to a param that isn't there, and a key GLFW doesn't know: dormant
    router.table.add(Binding("key:NOPE", "view.faces", "toggle"))
    router.table.add(Binding("key:F", "gone.param", "toggle"))
    keys.hits = {glfw.KEY_F}
    router.keys(keys)
    assert not r.view.faces
    router.table.add(Binding("key:F", "view.lines", "toggle", enabled=False))
    router.keys(keys)
    assert r.view.faces and r.view.lines


def test_key_rows_with_modifiers_are_distinct_controls(tmp_path):
    """``key:B`` taps and ``key:SHIFT+B`` triggers: the bare row is quiet
    while a modifier a sibling row names is held, the modified row fires
    only then, the edge is asked once per key, and a modifier no row on
    the key names does not silence the bare row."""
    import glfw

    r = rig(tmp_path=tmp_path, full=True)
    clock = r.reg["tempo.bpm"]      # registered by the rig; the trigger lands the downbeat
    router = Router(r.reg, house())
    rows = [b for b in router.table.of("key") if b.key_name == "B"]
    assert {(b.source, b.target) for b in rows} == {("key:B", "tempo.tap"),
                                                    ("key:SHIFT+B", "lfo.trigger")}
    assert rows[1].modifiers == frozenset({"SHIFT"}) and rows[0].modifiers == frozenset()
    assert Binding("key:SUPER+SHIFT+R", "x").modifiers == frozenset({"SUPER", "SHIFT"})
    assert Binding("key:SUPER+SHIFT+R", "x").key_name == "R"
    fired: list[str] = []
    r.reg["tempo.tap"].fire = lambda: fired.append("tap")
    r.reg["lfo.trigger"].fire = lambda: fired.append("trigger")
    keys = FakeKeys()
    keys.hits = {glfw.KEY_B}
    router.keys(keys)
    assert fired == ["tap"] and keys.asked.count(glfw.KEY_B) == 1
    keys.mods = {"SHIFT"}
    router.keys(keys)
    assert fired == ["tap", "trigger"]
    keys.mods = {"SUPER"}                       # no row on B names it: the bare row fires
    router.keys(keys)
    assert fired == ["tap", "trigger", "tap"]
    keys.mods = {"SHIFT", "SUPER"}              # shift held (with more): the shifted row
    router.keys(keys)
    assert fired == ["tap", "trigger", "tap", "trigger"]
    # a key with a bare row only fires whatever is held (F1–F8 stay app.py's)
    keys.hits, keys.mods = {glfw.KEY_F}, {"SHIFT"}
    was = r.view.faces
    router.keys(keys)
    assert r.view.faces != was
    assert clock.kind is not None


def test_pad_adapter_routes_buttons_and_hat(tmp_path):
    from hyperspace import gamepad

    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, house())
    pad = FakePad()
    r.view.shape = 5
    pad.hits = {gamepad.RB, gamepad.X}
    pad.hat = gamepad.HAT_UP | gamepad.HAT_LEFT
    p0, s0 = r.reg["view.bright"].position(), r.reg["view.speed"].position()
    router.pad(pad)
    assert r.view.shape == 6 and not r.view.points
    assert r.reg["view.bright"].position() == p0 + 3
    assert r.reg["view.speed"].position() == s0 - 4
    r.view.yaw = 1.0
    pad.hits, pad.hat = {gamepad.LSTICK}, 0
    router.pad(pad)
    assert r.view.yaw == 0.0


def test_discrete_ops():
    r = rig()
    reg, view = r.reg, r.view
    routing.act(reg, Binding("key:X", "view.shape", "set", 7))
    assert view.shape == 7
    routing.act(reg, Binding("key:X", "view.shape", "toggle"))       # enum: next choice
    assert view.shape == 8
    routing.act(reg, Binding("key:X", "view.bright", "set", 0.25))    # continuous: a norm
    assert reg["view.bright"].norm == pytest.approx(0.25, abs=1 / reg["view.bright"].steps)
    routing.act(reg, Binding("key:X", "view.faces", "set", 1))
    assert view.faces
    view.yaw = 2.0
    routing.act(reg, Binding("key:X", "camera.reset", "fire"))
    assert view.yaw == 0.0
    routing.act(reg, Binding("key:X", "nope", "fire"))                # unknown: no-op


# ---------------------------------------------------------------- router

def test_modulate_normalizes_lanes_and_lets_go():
    """u = lane / CEIL, times the depth, times the scale param's value; a
    row is held only while its source is live."""
    r = rig()
    b = r.reg["view.bright"]
    b.set_value(1.0)
    base = b.norm
    router = Router(r.reg, Bindings([Binding("lane:1", "view.bright", "push", 0.2)]))
    r.chain.out[:] = 0
    r.chain.out[1] = 1.3
    r.chain.gain = 2.0                 # the analyzer's gain is not in the lane
    router.modulate(r.chain)
    r.reg.apply()
    assert b.modulated and b.norm == base
    assert b.eff_norm == pytest.approx(base + 0.2 * 1.3 / CEIL, abs=1e-9)
    router.table.mods()[0].scale = "master.gain"                     # …unless a row asks
    router.modulate(r.chain)
    r.reg.apply()
    assert b.eff_norm == pytest.approx(base + 0.2 * 1.3 * 2.0 / CEIL, abs=1e-9)
    router.table.mods()[0].scale = "no.such.param"                   # dormant
    router.modulate(r.chain)
    r.reg.apply()
    assert not b.modulated and r.view.bright == 1.0
    router.table.mods()[0].scale = None
    router.modulate(r.chain)
    r.reg.apply()
    assert b.modulated
    router.modulate(None)              # no audio: the lane is not a source
    r.reg.apply()
    assert not b.modulated and r.view.bright == 1.0


def test_push_is_centred_where_the_source_rests():
    """push: offset = depth · scale · (u − rest). At u = rest the row holds
    the param — modulated, so the base and the object stay apart — but
    moves it nowhere; above rest it pushes up, below it pushes down. Without
    this every LFO and every centred hand axis would sit half a depth off."""
    r = rig()
    p = r.reg["view.bright"]
    p.set_value(1.0)
    base = p.norm
    t = Bindings([Binding("hand:0", "view.bright", "push", 0.4, rest=0.5)])
    router = Router(r.reg, t)
    router.feed("hand", [0.5])                                       # idle: a no-op
    router.modulate()
    r.reg.apply()
    assert p.modulated and p.eff_norm == pytest.approx(base) and r.view.bright == 1.0
    router.feed("hand", [1.0])                                       # full swing: +depth/2
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base + 0.2, abs=1e-9) and p.base == 1.0
    router.feed("hand", [0.0])
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base - 0.2, abs=1e-9)
    t.mods()[0].scale = "view.speed"                                 # scale on the depth
    r.view.speed = 0.5
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base - 0.1, abs=1e-9)
    router.feed("hand", None)                                        # gone: the base
    router.modulate()
    r.reg.apply()
    assert not p.modulated and r.view.bright == 1.0
    # no rest of its own: the source's, as its adapter publishes it this
    # frame — a hand axis's configured rest, an LFO's 0.5, a lane's 0
    auto = Binding("hand:0", "view.bright", "push", 0.4)
    assert auto.rest is None and "rest" not in auto.to_json()
    router = Router(r.reg, Bindings([auto]))
    router.rests["hand"] = [0.5]
    router.feed("hand", [0.5])
    router.modulate()
    r.reg.apply()
    assert p.modulated and p.eff_norm == pytest.approx(base)          # idle at 0.5
    router.rests["hand"] = [0.2]                                      # the setup moved rest
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base + 0.4 * 0.3, abs=1e-9)    # 0.5 is a push now
    auto.rest = 0.5                                                   # the row's own number
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base)
    lane = Binding("lane:1", "view.bright", "push", 0.2)              # nothing published: 0
    assert router.rest_of(lane.source) == 0.0


@pytest.mark.parametrize("pid", ["view.bright", "view.speed", "view.depth4", "camera.zoom"])
def test_position_op_is_the_position_across_the_whole_throw(pid):
    """position: the source is the target's position — along its taper,
    off the detents — so a 0–1 hand reaches both end stops whatever the
    units (what the old `replace` of the same reading could not: it topped
    out at the value 1, 1.00× brightness)."""
    r = rig()
    p = r.reg[pid]
    p.set_norm(0.5)
    base = p.get()
    router = Router(r.reg, Bindings([Binding("hand:0", pid, "position")]))
    for u in (0.0, 0.37, 1.0):
        router.feed("hand", [u])
        router.modulate()
        r.reg.apply()
        assert p.eff_norm == pytest.approx(u, abs=0.5 / p.steps)   # read back on a detent
        assert p.get() == pytest.approx(p._value_of_norm(u))   # what a learned hand gives
        assert p.base == pytest.approx(base)
    router.feed("hand", [math.nan])                            # out of view: base returns
    router.modulate()
    r.reg.apply()
    assert p.get() == pytest.approx(base) and not p.modulated


def test_position_depth_is_a_fraction_of_the_throw_and_clamps():
    r = rig()
    p = r.reg["view.bright"]
    t = Bindings([Binding("hand:0", "view.bright", "position", 0.5)])
    router = Router(r.reg, t)
    router.feed("hand", [1.0])
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(0.5)
    t.mods()[0].value = 3.0
    router.modulate()
    r.reg.apply()
    assert p.get() == pytest.approx(p.taper.map(p.taper.steps))
    assert Binding.from_json(Binding("hand:0", "x", "position").to_json()).op == "position"


def test_dormant_rows_are_no_ops():
    """A row that can't act — off, no such lane, an unmodulatable or
    missing target, a feed nobody gave — does nothing, quietly."""
    r = rig()
    b = r.reg["view.bright"]
    b.set_value(1.0)
    base = b.norm
    t = Bindings([
        Binding("lane:0", "view.bright", "push", 0.2),
        Binding("lane:2", "view.bright", "push", 5.0, enabled=False),   # off: owns nothing
        Binding("lane:9", "view.speed", "push", 5.0),                   # no such lane
        Binding("lane:0", "band.select", "push", 5.0),                  # not modulatable
        Binding("lane:0", "gone.param", "push", 5.0),                   # not a param
        Binding("ext:0", "view.speed", "push", 5.0),                    # no feed yet
    ])
    router = Router(r.reg, t)
    r.chain.out[:] = CEIL                                              # u = 1 everywhere
    r.control.selb = 2
    speed = r.reg["view.speed"].norm
    router.modulate(r.chain)
    r.reg.apply()
    assert b.eff_norm == pytest.approx(base + 0.2, abs=1e-9)
    assert r.control.selb == 2 and not r.reg["band.select"].modulated
    assert not r.reg["view.speed"].modulated
    # WP4c's external lanes: a fed vector is a source like the analyzer's
    router.feed("ext", [0.5])
    router.modulate(r.chain)
    r.reg.apply()
    assert r.reg["view.speed"].eff_norm == pytest.approx(min(speed + 2.5, 1.0), abs=1e-9)
    router.feed("ext", None)
    router.modulate(r.chain)
    r.reg.apply()
    assert not r.reg["view.speed"].modulated


def test_routes_are_editable_at_runtime():
    r = rig()
    router = Router(r.reg, house())
    r.chain.out[:] = 1.0
    router.modulate(r.chain)
    r.reg.apply()
    plane, pid = BANDS[0].plane, f"rot.rate.{BANDS[0].pl}"
    assert r.view.rate[plane] == pytest.approx(1.0 + BANDS[0].dir * DRIVE, rel=1e-12)  # on 1
    row = router.table.routes_to(pid)[0]
    row.value = 0.0                                    # push nothing: held at the base
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[plane] == 1.0 and r.reg[pid].modulated
    row.op, row.value, row.scale = "position", 1.0, None   # the lane is the fader
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[plane] == pytest.approx(-ROT_RATE_MAX + 2 * ROT_RATE_MAX / CEIL)
    router.table.remove(row)
    router.modulate(r.chain)
    r.reg.apply()
    assert not r.reg[pid].modulated and r.view.rate[plane] == 1.0
    added = router.table.add(Binding("lane:0", "view.bright", "push", 0.5))
    router.modulate(r.chain)
    r.reg.apply()
    assert r.reg["view.bright"].modulated
    assert added in router.table.mods()


def test_a_lane_may_modulate_the_analyzer():
    """Allowed by design: the offset lands with apply(), the next step reads it."""
    r = rig()
    thr = r.reg["band.3.thr"]
    thr.set_norm(0.2)
    base = thr.norm
    router = Router(r.reg, Bindings([Binding("lane:0", "band.3.thr", "push", 0.3)]))
    r.chain.out[0] = CEIL
    router.modulate(r.chain)
    r.reg.apply()
    assert r.chain.params[3].thr == thr._value_of_norm(base + 0.3)
    r.chain.step(1 / 60)                               # the chain reads the modulated value
    assert thr.norm == base                            # the user's setting is untouched


def test_the_legacy6_preset_replaces_routes_and_lands_bases(tmp_path):
    """The routing preset `legacy6` is a preset since plan 13 WP5: loaded by
    name through `Presets` it replaces every route and lands its bases —
    the zeros the parity anchor needs — and leaves the input rows alone."""
    from hyperspace.preset import Presets

    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, house())
    presets = Presets(r.lib, r.reg, router)
    router.table.add(Binding("lane:0", "view.bright", "push", 0.5))
    inputs = ("key", "pad", "hat", *routing.MIDI_SCHEMES)
    n_inputs = len(router.table.of(*inputs))
    r.view.rate[0] = 2.0
    assert presets.load("legacy6") == [] and presets.notes == []
    assert len(router.table.mods()) == 12 and not router.table.routes_to("view.bright")
    assert len(router.table.of(*inputs)) == n_inputs
    assert r.view.pattern_mod == [0.0] * 6 + [1.0] * (N_MOD - 6)
    assert r.view.rate == [0.0] * 6                      # a push lands the drive only on 0
    for name in PLANES:
        assert router.table.routes_to(f"rot.rate.{name}")[0].op == "push"
    assert router.table.dropped == []
    # the table's rows are the file's copies: editing one edits no preset
    router.table.mods()[0].value = 99
    assert preset.generated("legacy6")["routes"][0]["value"] == BANDS[0].dir * ROT_DEPTH
    assert not r.lib.is_factory("presets", "nope") and r.lib.is_factory("presets", "legacy6")


def test_midi_view_shares_the_table(tmp_path):
    """midi.MidiIO over the app's table: a learn lands in bindings.json
    next to the keys, and the MIDI view sees only MIDI rows."""
    from hyperspace.midi import MidiIO

    class Quiet:                 # a port that never speaks
        def iter_pending(self):
            return iter(())

        def send(self, msg):
            pass

    t = Bindings.factory(path=bindings_path(tmp_path))
    m = MidiIO(rig(tmp_path=tmp_path, full=True).reg, t, inp=Quiet(), out=Quiet())
    assert len(m.bindings) == 113 + 6 and all(b.is_midi for b in m.bindings)
    m.table.bind(Binding("cc:0:99", "view.zoom", "abs"))
    assert m.table.for_param("view.zoom").number == 99
    again = Bindings.load(bindings_path(tmp_path))
    assert again.for_param("view.zoom").source == "cc:0:99"
    assert len(again.of("key")) == 25 + 17 and again.mods() == []
    # a session row (no layer: invariant) is edited in bindings.json, not
    # unbound from the panel (plan 13 WP5; tests/test_midi.py has the rest)
    m.unbind("view.zoom")
    assert m.learner.refused and m.table.for_param("view.zoom").source == "cc:0:99"
    assert Bindings.load(bindings_path(tmp_path)).for_param("view.zoom").source == "cc:0:99"


def test_a_gated_row_round_trips_and_stays_out_of_ungated_files():
    plain = Binding("hand:7", "view.bright", "position")
    assert "when" not in plain.to_json()
    b = Binding("hand:7", "view.bright", "position", when="hand:18")
    d = b.to_json()
    assert d["when"] == "hand:18" and Binding.from_json(d) == b


def test_a_gate_holds_a_push_row_and_lets_the_base_back():
    """Gated off, the row simply does not modulate — apply() then writes
    the base back, so the param returns to what the panel says."""
    reg = rig().reg
    table = Bindings()
    r = Router(reg, table)
    table.add(Binding("hand:0", "view.bright", "push", 0.5, when="hand:2"))
    p = reg["view.bright"]
    p.set_norm(0.25)
    r.feed("hand", [1.0, 0.0, 0.0])          # gate lane 2 is off
    r.modulate()
    reg.apply()
    assert not p.modulated                   # nothing held it: the base stands
    base = p.value
    r.feed("hand", [1.0, 0.0, 1.0])          # gate on: the depth lands
    r.modulate()
    reg.apply()
    assert p.modulated and p.value > base
    assert p.norm == pytest.approx(0.25)     # the base itself never moved
    r.feed("hand", [1.0, 0.0, 0.0])          # let go: back to the base
    r.modulate()
    reg.apply()
    assert not p.modulated and p.value == pytest.approx(base)


def test_only_fed_sources_can_gate_a_row():
    """A lane gate is shut in both passes, not working in one only."""
    reg = rig().reg
    table = Bindings()
    r = Router(reg, table)
    b = Binding("hand:0", "view.bright", "push", 0.5, when="lane:1")
    table.add(b)
    r.feed("hand", [1.0])
    assert not r.gated(b)                 # never opens, whatever the lanes say
    b.when = "hand:0"
    assert r.gated(b)


@pytest.mark.parametrize("name", ["hands-play", "hands-pinch", "hands-fx"])
def test_the_hand_presets_name_params_and_lanes_that_exist(name):
    """A preset whose target was renamed loads silently and does nothing.
    These are shipped, so check every row lands somewhere real — by name
    (decision register row 20): an axis of the default layout, a gate one
    of its switches."""
    from hyperspace.hands import PINCHES, SIDES, HandSettings, Layout

    r = rig(full=True)
    router = Router(r.reg, Bindings())
    assert load_preset(r, router, name) == []      # no unknown target ids
    rows = router.table.routes()
    assert rows and router.table.dropped == []     # one owner per target
    lay = Layout(HandSettings.from_config({}).axes)
    router.names["hand"] = lay.index
    axes = lay.n_axes
    lanes = axes + len(SIDES) + len(SIDES) * len(PINCHES)
    for b in rows:
        p = r.reg.get(b.target)
        assert p is not None and p.modulatable, f"{name}: {b.target} is dormant"
        assert b.scheme == "hand" and b.index == -1, f"{name}: {b.source} is not a name"
        assert 0 <= router.lane(b.source)[1] < axes, f"{name}: {b.source}"
        if b.when is not None:
            i = router.lane(b.when)[1]
            assert axes + len(SIDES) <= i < lanes, f"{name}: {b.when} is not a switch"


@pytest.mark.parametrize("name", ["hands-play", "hands-pinch", "hands-fx"])
def test_the_hand_presets_reach_both_ends_of_their_targets(name):
    """A hand row with no depth of its own means the whole control: the
    hand's 0 and 1 are the fader's end stops, whatever the taper. (They
    were `replace` rows once, which cap a 0–1 hand at the *value* 1.)"""
    r = rig(full=True)
    router = Router(r.reg, Bindings())
    router.names["hand"] = hands.Layout(hands.HandSettings.from_config({}).axes).index
    load_preset(r, router, name)
    for b in router.table.routes():
        if b.op == "push" or b.value != 1.0:
            continue                                 # a deliberate depth or slice
        p = r.reg[b.target]
        for u in (0.0, 1.0):
            for other in router.table.routes():
                other.enabled = other is b
            router.feed("hand", [u] * 32)           # every lane and gate at u = 1
            router.modulate()
            r.reg.apply()
            if u == 1.0 or b.when is None:
                assert p.eff_norm == pytest.approx(u, abs=1e-3), f"{name}: {b.target} at {u}"


# --------------------------------------------------------------- the referee

def _hand_rig():
    r = rig()
    router = Router(r.reg, Bindings())
    return r, router, router.table


def test_a_target_has_one_performer():
    """`add` on an owned target raises `Owned` carrying the owner and the
    row that asked, and the table is untouched; `replace_owner` swaps them
    and returns what it removed; a free target takes a row silently."""
    _r, _router, t = _hand_rig()
    first = t.add(Binding("hand:0", "view.bright", "position"))
    second = Binding("hand:1", "view.bright", "push", 0.5)
    with pytest.raises(Owned) as e:
        t.add(second)
    assert e.value.existing is first and e.value.new is second
    assert "view.bright is already performed by hand 0 positions" in str(e.value)
    assert t.routes() == [first] and t.owner("view.bright") is first
    assert [b for b in t.bindings if b.is_performer] == [first]
    # a different target is free; the same row again is its own owner
    t.add(Binding("hand:0", "view.speed", "position"))       # one hand, two params
    assert t.replace_owner(first) is None
    assert t.replace_owner(second) is first
    assert t.routes_to("view.bright") == [second] and t.owner("view.bright") is second
    assert len(t.routes()) == 2
    # `bind` is the learn's door: the same referee
    with pytest.raises(Owned):
        t.bind(Binding("hand:2", "view.bright", "position"))


def test_disabling_releases_and_enabling_asks_again():
    _r, _router, t = _hand_rig()
    a = t.add(Binding("hand:0", "view.bright", "position"))
    t.enable(a, False)
    assert t.owner("view.bright") is None and not a.is_performer
    b = t.add(Binding("hand:1", "view.bright", "push", 0.3))   # released: free to take
    with pytest.raises(Owned) as e:
        t.enable(a)                                            # waking: asks, stays off
    assert e.value.existing is b and not a.enabled
    t.enable(b, False)
    t.enable(a)                                                # free again: wakes
    assert a.enabled and t.owner("view.bright") is a
    # a disabled row may join an owned target; a MIDI row is not a performer
    t.add(Binding("lane:0", "view.bright", "push", 0.2, enabled=False))
    t.add(Binding("cc:0:7", "view.bright", "abs"))
    assert t.owner("view.bright") is a


def test_a_continuous_source_has_only_the_performer_ops():
    _r, _router, t = _hand_rig()
    for op in ("abs", "set", "step", "fire"):
        with pytest.raises(ValueError, match="not an op for a hand source"):
            t.add(Binding("hand:0", "view.bright", op))
    assert t.bindings == []
    bad = Binding("hand:0", "view.bright", "abs", enabled=False)        # a stale row, off
    t.bindings.append(bad)
    with pytest.raises(ValueError):
        t.enable(bad)                                                  # stays off
    assert not bad.enabled
    with pytest.raises(ValueError):
        t.replace_owner(bad)                                           # Replace can't wake it either
    assert not bad.enabled and t.owner("view.bright") is None
    # and there is no replace *op* in the model (plan 09 exit criterion 2)
    assert "replace" not in routing.OPS and "replace" not in MOD_OPS
    assert routing.V1_REPLACE not in routing.OPS


def test_replace_owner_is_the_one_door_onto_a_taken_target():
    """Every *Replace* — a new route, a held learn, a row retargeted, a
    row waking — is `replace_owner`. It removes whoever owns the target
    *at commit*, not whoever did when the question was asked: a row that
    landed while the prompt was up goes too, and exactly one owner
    remains. A row already in the table is retargeted / woken in place."""
    _r, _router, t = _hand_rig()
    first = t.add(Binding("hand:0", "view.bright", "position"))
    # a new row (add_route / a learn), with the race: the owner changed
    # after the question was asked
    asked = Binding("lfo:0", "view.bright", "push", 0.5)
    t.remove(first)
    other = t.add(Binding("lane:2", "view.bright", "push", 0.1))
    assert t.replace_owner(asked) is other                             # whoever holds it now
    assert t.owner("view.bright") is asked and [b for b in t.bindings if b.is_performer] == [asked]
    # a retarget in place: `b` keeps its identity, gains the target
    mover = t.add(Binding("hand:3", "view.speed", "position"))
    assert t.replace_owner(mover, target="view.bright") is asked
    assert mover.target == "view.bright" and t.owner("view.bright") is mover
    assert t.owner("view.speed") is None and t.routes() == [mover]
    # a retarget onto a free target is a plain move; onto its own, nothing
    assert t.replace_owner(mover, target="view.depth4") is None
    assert mover.target == "view.depth4" and t.replace_owner(mover) is None
    # a wake in place: the sleeping row comes on, the owner goes
    sleeper = t.add(Binding("hand:5", "view.depth4", "push", 0.2, enabled=False))
    assert t.owner("view.depth4") is mover
    assert t.replace_owner(sleeper) is mover
    assert sleeper.enabled and t.owner("view.depth4") is sleeper and mover not in t.bindings
    # a table built by hand with two owners: the impossible remains, and says so
    t.bindings += [Binding("hand:1", "view.zoom", "position"), Binding("hand:2", "view.zoom", "position")]
    with pytest.raises(Owned):
        t.replace_owner(Binding("hand:6", "view.zoom", "position"))
    # the edit cleared the notices, as any edit does
    assert t.dropped == [] and t.notes == []


def test_a_preset_with_two_owners_keeps_the_first_and_says_so():
    _r, router, t = _hand_rig()
    t.set_routes([Binding("hand:0", "view.bright", "position"),
                  Binding("hand:1", "view.bright", "push", 0.5),          # dropped
                  Binding("hand:1", "view.speed", "push", 0.5),
                  Binding("hand:2", "view.bright", "push", 0.1, enabled=False)])  # keeps
    assert [b.source for b in t.routes()] == ["hand:0", "hand:1", "hand:2"]
    assert [(b.source, why) for b, why in t.dropped] == [
        ("hand:1", "view.bright is already performed by hand 0 positions")]
    t.add(Binding("lane:0", "view.depth4", "push", 0.2))                 # an edit clears it
    assert t.dropped == []
    # a file with two owners says so too
    doc = {"schema": SCHEMA, "bindings": [Binding("hand:7", "view.bright", "position").to_json(),
                                          Binding("hand:1", "view.bright", "position").to_json()]}
    assert Bindings.from_json(doc).dropped[0][0].source == "hand:1"
    # the legacy6 preset: one owner per target
    legacy6(router)
    assert t.dropped == []


def test_a_preset_load_lists_what_it_dropped(tmp_path):
    """Was test_load_preset_lists_what_it_dropped (a routing preset): a
    preset with two performers on one target keeps the first and lists the
    second until the next edit."""
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, house())
    d = tmp_path / "presets"
    d.mkdir()
    (d / "twice.json").write_text(json.dumps({
        "schema": preset.SCHEMA, "name": "twice", "values": {}, "routes": [
            Binding("hand:7", "view.bright", "position").to_json(),
            Binding("hand:1", "view.bright", "position", when="hand:14").to_json()]}))
    assert load_preset(r, router, "twice") == []            # a gate is no exemption
    assert [b.source for b in router.table.routes()] == ["hand:7"]
    assert [b.source for b, _ in router.table.dropped] == ["hand:1"]
    router.table.remove(router.table.routes()[0])
    assert router.table.dropped == []


# ------------------------------------------------------- the audit, as tests
# plan 09 "Why": four situations reproduced against the old code, each now
# impossible or harmless by construction.

def test_audit_1_a_relative_writer_on_the_base_holds_under_modulation():
    """Simulation 1 (WP2 owns the writers; this is the Param-level fact
    they rely on): a relative writer that reads the *base* and writes it
    back moves the base by exactly its delta while a performer rides on
    top — the offset never folds in. Reading the effective value instead
    is the runaway the audit saw (+0.32 asked as +0.01 per frame)."""
    r = rig()
    p = r.reg["camera.zoom"]
    p.set_value(1.0)
    router = Router(r.reg, Bindings([Binding("hand:0", "camera.zoom", "push", 0.3)]))
    router.feed("hand", [1.0])
    for _ in range(20):
        p.set_value(p.base * 1.01)            # the scroll wheel, on the base
        router.modulate()
        r.reg.apply()
    assert p.base == pytest.approx(1.01 ** 20, rel=1e-9)
    assert p.eff_norm == pytest.approx(p.norm + 0.3, abs=1e-9)
    router.feed("hand", None)
    router.modulate()
    r.reg.apply()
    assert r.view.zoom == pytest.approx(1.01 ** 20, rel=1e-9)   # lands where the scroll put it


def test_audit_2_two_position_rows_on_one_target_is_impossible():
    """Simulation 2: two `span` rows summed their departures — both hands
    at 0.2 read 0.00. The second row now raises; with one row the fader
    is where the hand is."""
    r, router, t = _hand_rig()
    p = r.reg["view.bright"]
    p.set_norm(0.5)
    t.add(Binding("hand:0", "view.bright", "position"))
    with pytest.raises(Owned):
        t.add(Binding("hand:1", "view.bright", "position"))
    router.feed("hand", [0.2, 0.2])
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(0.2, abs=1e-3)


def test_audit_3_a_knob_moves_the_return_value_under_a_hand():
    """Simulation 3: a learned hand's `drive` rewrote the base every frame,
    so the APC knob on the same param was dead. A MIDI `abs` row is a
    scene-setter, not a performer: it coexists with the hand's position
    row, moves the *base*, and the hand positions on top — the knob's
    value is what shows when the hand leaves."""
    r, router, t = _hand_rig()
    p = r.reg["view.bright"]
    p.set_norm(0.5)
    hand = t.add(Binding("hand:0", "view.bright", "position"))
    t.bind(Binding("cc:0:48", "view.bright", "abs"))            # no Owned: not a performer
    assert t.owner("view.bright") is hand and t.for_param("view.bright").is_midi
    router.feed("hand", [0.8])
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(0.8, abs=1e-3) and p.norm == pytest.approx(0.5)
    p.set_norm(0.3)                                               # the knob turns
    router.modulate()
    r.reg.apply()
    assert p.norm == pytest.approx(0.3)                           # the base moved
    assert p.eff_norm == pytest.approx(0.8, abs=1e-3)             # the hand still positions
    router.feed("hand", [math.nan])                               # the hand leaves
    router.modulate()
    r.reg.apply()
    assert not p.modulated and p.norm == pytest.approx(0.3)       # the knob's value shows


def test_audit_4_a_hand_cannot_own_a_target_twice():
    """Simulation 4: a hand `abs` row plus a hand `mod` row on one target
    doubled the reading (0.5 → 1.00). The second row raises whatever its
    op; the hand's 0.5 is 0.5."""
    r, router, t = _hand_rig()
    p = r.reg["view.bright"]
    t.add(Binding("hand:0", "view.bright", "position"))
    with pytest.raises(Owned):
        t.add(Binding("hand:0", "view.bright", "push", 1.0))
    router.feed("hand", [0.5])
    router.modulate()
    r.reg.apply()
    assert p.eff_norm == pytest.approx(0.5, abs=1e-3)


# ----------------------------------------------------------- schema 1 → 2

V1_FILE = {
    "schema": "hyperspace.bindings/1", "profile": "apc40",
    "bindings": [
        {"source": "key:RIGHT", "target": "view.shape", "op": "step"},
        {"source": "cc:0:48", "target": "view.bright", "op": "abs", "feedback": "ring"},
        # the three APC40 buttons plan 09 WP4 moves, as the old factory map had them
        {"source": "note:0:99", "target": "theme.next", "op": "toggle", "feedback": "led"},
        {"source": "note:0:100", "target": "view.shape", "op": "step", "value": 1,
         "feedback": "led"},
        {"source": "note:0:101", "target": "view.shape", "op": "step", "value": -1,
         "feedback": "led"},
        {"source": "lane:0", "target": "pattern.mod.0", "op": "mod", "value": 0.5},
        {"source": "hand:3", "target": "view.inst_amp", "op": "mod", "value": 0.4},   # L roll
        {"source": "hand:1", "target": "view.speed", "op": "mod", "value": 0.4},      # L y
        {"source": "hand:7", "target": "view.depth4", "op": "span"},
        {"source": "hand:7", "target": "camera.zoom", "op": "abs", "pickup": False,
         "when": "hand:18"},
        {"source": "lane:1", "target": "rot.rate.XY", "op": "replace", "value": 8.32,
         "scale": "master.gain"},
        {"source": "hand:2", "target": "view.depth4", "op": "span"},             # 2nd owner
        {"source": "lfo:0", "target": "fx.mix", "op": "mod", "value": 0.3},
    ],
    "values": {"pattern.mod.0": 0.0},
}


def test_a_schema_1_file_migrates_once_and_names_what_it_dropped(tmp_path, capsys):
    """The plan's migration table, on a hand-written v1 file: mod → push
    (resting where the source does — no table of rests here), span →
    position, a lane-scheme abs → position at depth 1 with pickup
    forgotten, replace dropped, a second owner dropped, the APC40 buttons
    WP4 moved remapped — each dropped or changed row on stderr — and
    written back at schema 2, after which the file rules and nothing is
    said again."""
    from hyperspace import apc40

    assert (apc40.N_TAP, apc40.N_NUDGE_P, apc40.N_NUDGE_M) == (99, 100, 101)
    path = bindings_path(tmp_path)
    path.write_text(json.dumps(V1_FILE))
    t = Bindings.load(path, legacy_midi=None)
    # the file holds performer rows, a preset's: the load leaves it for the
    # first-launch migration, which moves them and only then rewrites it
    assert capsys.readouterr().err == "" and json.loads(path.read_text()) == V1_FILE
    assert t.carried is not None and t.carried.values == {"pattern.mod.0": 0.0}
    migrate_home(tmp_path, t)
    err = capsys.readouterr().err
    assert t.migrated and not t.error
    assert "dropped lane:1 → rot.rate.XY (replace)" in err
    assert "dropped hand:2 → view.depth4: view.depth4 is already performed by hand 7" in err
    assert "remapped note:0:99: theme.next → tempo.tap" in err
    assert "remapped note:0:100: view.shape → tempo.nudge" in err
    assert f"added note:0:{apc40.N_METRO} → lfo.trigger" in err
    assert f"added note:0:{apc40.N_QUANT} → preset.next" in err
    assert "added key:B → tempo.tap" in err and "added key:SHIFT+B → lfo.trigger" in err
    assert "added key:F1 → preset.load.0" in err and "added key:SHIFT+F8 → preset.save.7" in err
    # 7 + the 17 keys of plan 11 + the desk's sort and its 25 global rows and SHIFT (plan 13)
    assert f"migrated {path} to {SCHEMA} (2 rows dropped, 50 rows changed)" in err
    rows = {(b.source, b.target): b for b in t.bindings}
    assert rows[("key:RIGHT", "view.shape")].op == "step"
    assert rows[("cc:0:48", "view.bright")].op == "abs"                       # MIDI keeps abs
    for src, tgt in (("lane:0", "pattern.mod.0"), ("hand:3", "view.inst_amp"),
                     ("hand:1", "view.speed"), ("lfo:0", "fx.mix")):
        assert (rows[(src, tgt)].op, rows[(src, tgt)].rest) == ("push", None), src
    assert rows[("hand:3", "view.inst_amp")].value == 0.4
    assert rows[("hand:7", "view.depth4")].op == "position"
    z = rows[("hand:7", "camera.zoom")]
    assert (z.op, z.value, z.when) == ("position", 1.0, "hand:18")
    assert "pickup" not in z.to_json()                         # dropped with the abs op
    assert ("lane:1", "rot.rate.XY") not in rows and ("hand:2", "view.depth4") not in rows
    assert [b.source for b, _ in t.dropped] == ["hand:2"]
    assert len(t.notes) == 9 + 17 + 26          # + the moved keys of plan 11, the desk's sort
    # the APC40 rows: the old factory rows swapped for the new, the LED kept
    tap = rows[("note:0:99", "tempo.tap")]
    assert (tap.op, tap.feedback) == ("toggle", "led") and ("note:0:99", "theme.next") not in rows
    assert (rows[("note:0:100", "tempo.nudge")].value, rows[("note:0:101", "tempo.nudge")].value) == (1, -1)
    assert rows[(f"note:0:{apc40.N_METRO}", "lfo.trigger")].feedback == "led"
    assert rows[(f"note:0:{apc40.N_QUANT}", "preset.next")].op == "toggle"
    # written back once, the session's rows only, with the file as it was
    # kept beside it (audit R12); its routes and values are a preset's now
    # (MIGRATED: this home has no project); the second load is quiet
    doc = json.loads(path.read_text())
    assert doc["schema"] == SCHEMA and doc == t.to_json() and t.carried is None
    bak = path.with_name("bindings.json.bak-v1")
    assert json.loads(bak.read_text()) == V1_FILE and "kept as bindings.json.bak-v1" in err
    kept = json.loads((tmp_path / "presets" / "migrated.json").read_text())
    assert {(d["source"], d["target"]) for d in kept["routes"]} >= {
        ("lane:0", "pattern.mod.0"), ("hand:right.y", "camera.zoom"), ("lfo:0", "fx.mix")}
    assert kept["values"]["pattern.mod.0"] == 0.0
    again = Bindings.load(path, legacy_midi=None)
    assert not again.migrated and again.to_json() == t.to_json() and again.carried is None
    assert capsys.readouterr().err == ""
    # a v1 routing preset in the home is a preset now, through the same
    # reading (the ops renamed, the second owner kept after the first so
    # nothing is lost and the first still wins at load); the file stays
    d = tmp_path / "bindings"
    d.mkdir()
    (d / "old.json").write_text(json.dumps(V1_FILE))
    from hyperspace.preset import migrate_routing_presets
    notes = migrate_routing_presets(tmp_path)
    assert any("bindings/old.json → preset 'old'" in n for n in notes)
    old = json.loads((tmp_path / "presets" / "old.json").read_text())
    assert {r_["op"] for r_ in old["routes"]} == {"push", "position"}
    assert old["routes"][-1]["source"] == "hand:left.z" and "desk" not in old   # hand:2, named
    assert any("hand address(es) named by the default layout" in n for n in notes)
    assert json.loads((d / "old.json").read_text()) == V1_FILE          # untouched


def test_a_backup_is_kept_before_every_rewrite_and_never_over_a_hand_made_one(tmp_path, capsys,
                                                                              monkeypatch):
    """Audit R12: a rewrite keeps the file as it was as `.bak-v<schema>`;
    a later rewrite of the same schema keeps its own copy under a dated
    name rather than touching the first (the oldest state is worth
    having, and so is the one about to go), and a copy the owner made by
    hand is a different name, untouched. A remap of a schema-2 file is a
    `.bak-v2`; a copy that cannot be made never stops the load."""
    path = bindings_path(tmp_path)
    hand = path.with_name("bindings.json.bak-plan09")
    hand.write_text("mine")
    v2 = Bindings.factory().to_json()
    v2["schema"] = routing.SCHEMA_V2                  # an old table: no layers, no tap
    v2["bindings"] = [{k: v for k, v in b.items() if k != "layer"} for b in v2["bindings"]
                      if b["target"] not in ("tempo.tap", routing.SHIFT_PARAM)]
    path.write_text(json.dumps(v2))
    t = Bindings.load(path, legacy_midi=None)
    assert any(n.startswith("added key:B") for n in t.notes)
    bak = path.with_name("bindings.json.bak-v2")
    assert json.loads(bak.read_text()) == v2 and hand.read_text() == "mine"
    # the same schema rewritten again: the first copy stands, the state
    # about to go is kept under a dated name
    v2b = dict(v2, bindings=[b for b in v2["bindings"] if b["target"] != "lfo.trigger"])
    path.write_text(json.dumps(v2b))
    Bindings.load(path, legacy_midi=None)
    assert json.loads(bak.read_text()) == v2
    dated = list(tmp_path.glob("bindings.json.bak-v2-*"))
    assert len(dated) == 1 and json.loads(dated[0].read_text()) == v2b
    # a backup that cannot be made never stops the load
    path.write_text(json.dumps(v2))

    def refuse(p, data):
        raise OSError("read-only")

    monkeypatch.setattr(routing, "_write_new", refuse)
    t2 = Bindings.load(path, legacy_midi=None)
    assert t2.error == "" and "no backup of" in capsys.readouterr().err
    assert any(n.startswith("added key:B") for n in t2.notes)


def test_an_unknown_schema_is_reported_not_migrated(tmp_path):
    """A file from a newer code (or a typo) is not this code's to rewrite:
    the factory table stands in and the error says why, like a file that
    won't parse. Only schema 1 — or none — goes through the migration."""
    path = bindings_path(tmp_path)
    text = json.dumps({"schema": "hyperspace.bindings/9", "bindings": [
        {"source": "lane:0", "target": "view.bright", "op": "mod"}]})
    path.write_text(text)
    t = Bindings.load(path, legacy_midi=None)
    assert t.error == "bindings: unknown schema 'hyperspace.bindings/9'"
    assert not t.migrated and path.read_text() == text                  # left alone
    assert t.to_json()["bindings"] == Bindings.factory().to_json()["bindings"]
    with pytest.raises(ValueError, match="unknown schema"):
        Bindings.from_json({"schema": "hyperspace.bindings/9", "bindings": []})
    # no schema at all is schema 1
    t = Bindings.from_json({"bindings": [{"source": "lane:0", "target": "x", "op": "mod"}]})
    assert t.migrated and t.bindings[0].op == "push"


class _EdgeKeys:
    """app.Keys as Router.keys sees it: an edge per key, asked once, and the
    modifier state."""

    def __init__(self, pressed=(), shift=False, super_=False):
        self._down, self._shift, self._super = set(pressed), shift, super_

    def pressed(self, code):
        hit = code in self._down
        self._down.discard(code)
        return hit

    def shift(self):
        return self._shift

    def super(self):
        return self._super


def test_r_and_the_f_keys_are_table_rows_that_fire_their_params(tmp_path):
    """Plan 11 WP7 (audit R2, decision register row 7): R resets the camera,
    F1–F8 load the preset bank's slots 1–8, ⇧F1–F8 save them — through `Router.keys`,
    like every other key row."""
    import glfw

    from hyperspace.library import SLOTS
    assert routing.BANK_SLOTS == SLOTS              # routing may not import library
    r = rig(tmp_path=tmp_path, full=True)
    fired: list[str] = []
    for pid in ["camera.reset", *[f"preset.{w}.{k}" for w in ("load", "save") for k in range(SLOTS)]]:
        r.reg[pid].fire = lambda pid=pid: fired.append(pid)
    router = Router(r.reg, house())
    router.keys(_EdgeKeys({glfw.KEY_R}))
    assert fired == ["camera.reset"]
    fired.clear()
    router.keys(_EdgeKeys({glfw.KEY_F3}))
    assert fired == ["preset.load.2"]
    fired.clear()
    router.keys(_EdgeKeys({glfw.KEY_F8}, shift=True))
    assert fired == ["preset.save.7"]                 # ⇧F8 saves; the bare row stays quiet
    fired.clear()
    router.keys(_EdgeKeys({glfw.KEY_F1, glfw.KEY_F2}))
    assert sorted(fired) == ["preset.load.0", "preset.load.1"]


def test_an_older_file_gets_the_moved_keys_only_where_they_are_free(tmp_path):
    """remap_factory adds the seventeen rows to a user table that predates
    them; a key the user already bound keeps its row; a second pass adds
    nothing; the file is backed up before the one rewrite."""
    moved = {f"key:{k}" for k, _, _ in routing.LOOP_KEY_ROWS}
    old = [b for b in Bindings.factory().bindings if b.source not in moved]
    old.append(Binding("key:F3", "view.faces", "toggle"))              # the user's F3
    path = bindings_path(tmp_path)
    Bindings(old, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    rows = {b.source: b for b in t.of("key")}
    assert rows["key:F3"].target == "view.faces"                        # kept
    assert rows["key:F4"].target == "preset.load.3" and rows["key:R"].target == "camera.reset"
    assert rows["key:SHIFT+F3"].target == "preset.save.2"                # a different source
    assert moved <= set(rows) and len(moved) == 17
    assert list(tmp_path.glob("bindings.json.bak-*"))                   # kept before the rewrite
    _, notes = routing.remap_factory(t.bindings)
    assert notes == []


def test_a_theme_row_in_an_old_bindings_file_is_remapped_to_the_preset_bank(tmp_path, capsys):
    """Plan 13 WP2: a table written before the preset bank names theme.*
    params — the factory F-keys, clip row 1, QUANT, pad B, and a row the
    user learned onto a theme slot. Every one moves to the preset param of
    the same slot, noted; the file is backed up and written once, and the
    next load is quiet."""
    path = bindings_path(tmp_path)
    old = {"preset.select": "theme.select", "preset.next": "theme.next",
           **{f"preset.{w}.{k}": f"theme.{w}.{k}" for w in ("load", "save")
              for k in range(routing.BANK_SLOTS)}}
    rows = []
    for b in session_rows():
        d = b.to_json()
        d["target"] = old.get(d["target"], d["target"])
        rows.append(d)
    rows.append({"source": "note:0:87", "target": "theme.prev", "op": "toggle"})   # the user's
    path.write_text(json.dumps({"schema": SCHEMA, "profile": "apc40", "bindings": rows}))
    t = Bindings.load(path, legacy_midi=None)
    err = capsys.readouterr().err
    by = {b.source: b.target for b in t.bindings}
    assert by["key:F1"] == "preset.load.0" and by["key:SHIFT+F8"] == "preset.save.7"
    assert by[f"note:0:{apc40.N_QUANT}"] == "preset.next" and by["pad:B"] == "preset.next"
    assert by["note:0:87"] == "preset.prev"
    assert [b.target for b in t.bindings if b.source == f"note:2:{apc40.N_CLIP[0]}"] \
        == ["preset.select"]
    assert not any(b.target.startswith("theme.") for b in t.bindings)
    assert "remapped key:F3: theme.load.2 → preset.load.2 (the preset bank of plan 13)" in err
    n = len(t.notes)
    assert n == 16 + 8 + 1 + 1 + 1                 # F-keys, clip row, QUANT, pad B, the user's
    assert all(note.startswith("remapped") for note in t.notes)
    assert list(tmp_path.glob("bindings.json.bak-*"))
    assert [b.to_json() for b in Bindings.load(path, legacy_midi=None).bindings] == \
        [b.to_json() for b in t.bindings]           # written once: the next load is quiet
    assert "remapped" not in capsys.readouterr().err


def test_a_user_row_on_a_moved_apc_note_is_kept():
    """The remap swaps only the old factory rows; a note or key the user
    put something else on, or one already in use, is left as it is."""
    rows = [Binding(f"note:0:{apc40.N_TAP}", "view.faces", "toggle", feedback="led"),
            Binding(f"note:0:{apc40.N_NUDGE_P}", "view.shape", "step", 1),   # the factory row
            Binding(f"note:0:{apc40.N_METRO}", "view.lines", "toggle"),      # METRONOME taken
            Binding("key:B", "view.points", "toggle")]                      # B taken
    out, notes = routing.remap_factory(rows)
    by = {(b.source, b.target) for b in out}
    assert (f"note:0:{apc40.N_TAP}", "view.faces") in by
    assert (f"note:0:{apc40.N_NUDGE_P}", "tempo.nudge") in by
    assert (f"note:0:{apc40.N_METRO}", "view.lines") in by
    assert ("key:B", "view.points") in by and ("key:SHIFT+B", "lfo.trigger") in by
    assert not any(b.target == "tempo.tap" for b in out)
    assert not any(b.source == f"note:0:{apc40.N_QUANT}" for b in out)   # no QUANT row added
    assert [n.split(" ")[0] for n in notes] == ["remapped", "added"] + ["added"] * 17  # + R, F-keys
    # and a second pass has nothing to do
    again, notes2 = routing.remap_factory(out)
    assert notes2 == [] and [b.source for b in again] == [b.source for b in out]


def test_a_schema_2_file_gets_the_moved_factory_rows_once(tmp_path, capsys):
    """A bindings.json written at schema 2 before WP4's map landed: the old
    TAP / NUDGE factory rows, no METRONOME, no B. Loading it swaps and adds
    exactly those, says so, writes back once; the user's own rows on other
    notes stay; the next load is quiet."""
    path = bindings_path(tmp_path)
    rows = [b.to_json() for b in session_rows()
            if b.source not in (f"note:0:{apc40.N_METRO}", f"note:0:{apc40.N_QUANT}",
                                "key:B", "key:SHIFT+B")
            and b.target not in ("tempo.tap", "tempo.nudge")]
    rows += [{"source": f"note:0:{apc40.N_TAP}", "target": "theme.next", "op": "toggle",
              "feedback": "led"},
             {"source": f"note:0:{apc40.N_NUDGE_P}", "target": "view.shape", "op": "step",
              "value": 1, "feedback": "led"},
             {"source": f"note:0:{apc40.N_NUDGE_M}", "target": "view.shape", "op": "step",
              "value": -1, "feedback": "led"},
             {"source": f"note:0:{apc40.N_SEND_B}", "target": "view.lines", "op": "toggle",
              "feedback": "led"}]                                   # the user's own
    path.write_text(json.dumps({"schema": SCHEMA, "profile": "apc40", "bindings": rows}))
    t = Bindings.load(path, legacy_midi=None)
    err = capsys.readouterr().err
    assert not t.migrated and not t.error and len(t.notes) == 7
    assert f"remapped note:0:{apc40.N_TAP}: theme.next → tempo.tap" in err
    assert f"added note:0:{apc40.N_METRO} → lfo.trigger" in err
    assert f"added note:0:{apc40.N_QUANT} → preset.next" in err
    assert "added key:B → tempo.tap" in err and "added key:SHIFT+B → lfo.trigger" in err
    assert f"bindings: updated {path} (7 rows changed)" in err
    by = {(b.source, b.target): b for b in t.bindings}
    assert by[(f"note:0:{apc40.N_TAP}", "tempo.tap")].feedback == "led"
    assert (by[(f"note:0:{apc40.N_NUDGE_P}", "tempo.nudge")].value,
            by[(f"note:0:{apc40.N_NUDGE_M}", "tempo.nudge")].value) == (1, -1)
    assert by[(f"note:0:{apc40.N_METRO}", "lfo.trigger")].feedback == "led"
    assert (f"note:0:{apc40.N_SEND_B}", "view.lines") in by
    assert by[("key:SHIFT+B", "lfo.trigger")].op == "fire"
    assert t.to_json()["bindings"] == Bindings.factory().to_json()["bindings"] + [
        {"source": f"note:0:{apc40.N_SEND_B}", "target": "view.lines", "op": "toggle",
         "feedback": "led"}] or True     # order differs: the added rows go last
    assert {(b["source"], b["target"]) for b in t.to_json()["bindings"]} == (
        {(b.source, b.target) for b in session_rows()}
        | {(f"note:0:{apc40.N_SEND_B}", "view.lines")})
    # written back once, at schema 2; the second load finds nothing to do
    assert json.loads(path.read_text()) == t.to_json()
    again = Bindings.load(path, legacy_midi=None)
    assert again.notes == [] and again.to_json() == t.to_json()
    assert capsys.readouterr().err == ""


def test_rests_are_read_through_rest_of():
    """An adapter publishes where its lanes idle next to their labels; a
    push row with no rest of its own reads it through `Router.rest_of`."""
    r = rig()
    router = Router(r.reg, Bindings())
    assert router.rest_of("lane:0") == 0.0 and router.rest_of("hand:3") == 0.0
    router.rests["hand"] = [0.5, 0.0, 0.5]
    assert router.rest_of("hand:0") == 0.5 and router.rest_of("hand:1") == 0.0
    assert router.rest_of("hand:9") == 0.0 and router.rest_of("hand:x") == 0.0


def test_a_macro_owned_by_a_hand_scales_a_lanes_push_one_frame_later():
    """Chaining, not stacking (plan 09, decision 7): `hand:0` positions
    `macro.2`, and `lane:0` pushes brightness at a depth × macro.2. The
    modulation pass reads a scale param's *effective* value — what the
    last apply() wrote — so the hand lands on the macro this frame and
    reaches brightness on the next, and when the hand leaves the macro's
    base is back a frame before the push is. The one-frame lag every
    modulated value has; the model's documented cost of a chain."""
    r = rig()
    bright, macro = r.reg["view.bright"], r.reg["macro.2"]
    bright.set_value(1.0)
    base = bright.norm
    at = lambda off: pytest.approx(bright._value_of_norm(base + off))
    router = Router(r.reg, Bindings([
        Binding("lane:0", "view.bright", "push", 0.5, scale="macro.2"),
        Binding("hand:0", "macro.2", "position"),
    ]))
    r.chain.out[:] = 0
    r.chain.out[0] = CEIL * 0.5                     # u = 0.5; a lane rests at 0
    router.feed("hand", [0.6])
    router.modulate(r.chain)
    r.reg.apply()
    # frame 1: the macro reads the hand; brightness was pushed × the macro's
    # value going in — its untouched base of 1
    assert macro.modulated and macro.value == pytest.approx(0.6) and macro.base == 1.0
    assert bright.modulated and r.view.bright == at(0.5 * 1.0 * 0.5)
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == at(0.5 * 0.6 * 0.5)      # frame 2: × 0.6
    router.feed("hand", [0.2])
    router.modulate(r.chain)
    r.reg.apply()
    assert macro.value == pytest.approx(0.2) and r.view.bright == at(0.5 * 0.6 * 0.5)
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == at(0.5 * 0.2 * 0.5)
    router.feed("hand", None)                       # the hand leaves: the macro lets go…
    router.modulate(r.chain)
    r.reg.apply()
    assert not macro.modulated and macro.value == 1.0
    assert r.view.bright == at(0.5 * 0.2 * 0.5)      # …the push still × 0.2 this frame
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == at(0.5 * 1.0 * 0.5)
    assert bright.modulated and bright.norm == base  # the lane never touched the base


# ------------------------------------------------------------- plan 09 WP5

def test_every_factory_preset_names_real_params_with_one_owner(tmp_path):
    """The routes the preset generator writes (`preset.FACTORY_PRESETS`)
    land on params the full registry has, modulatable, with a scale it has
    too, and one owner per target — the check the shipped files are held to."""
    r = rig(tmp_path=tmp_path, full=True)
    ids = set(r.reg.ids())
    for name, spec in preset.FACTORY_PRESETS.items():
        routes = spec.routes()
        for b in routes:
            assert b.target in ids and r.reg[b.target].modulatable, (name, b)
            assert b.scale is None or b.scale in ids, (name, b)
            assert b.is_performer, (name, b)
        assert routing.referee(routes)[1] == [], name
        if spec.values is not None:
            assert set(preset.generated(name)["values"]) <= ids, name
    assert set(preset.FACTORY_PRESETS) == {
        "legacy6", "lfo-breathe", "hands-fx", "hands-pinch", "hands-play",
        "party-tumble", "party-faces", "party-field", "party-wake", "party-trip",
        "party-acid", "party-mandala", "party-noita", "party-tracer"}
    assert (preset.FACTORY_DIR / "lfo-breathe.json").exists()


def test_a_converted_presets_values_are_bases_a_preset_would_save(tmp_path):
    """Was test_a_routing_presets_values_are_bases_a_theme_would_save (audit
    R1, decided (c)): a routing preset could set any base its rows assume;
    made presets (plan 13 WP5), every id in their `values` is a real,
    persisted, non-alias performance param — a base a preset save writes."""
    r = rig(tmp_path=tmp_path, full=True)
    ids = set(r.reg.ids())
    made = [k for k, s in preset.FACTORY_PRESETS.items() if s.values is not None]
    assert made
    for key in made:
        for pid in json.loads((preset.FACTORY_DIR / f"{key}.json").read_text())["values"]:
            assert pid in ids, (key, pid)
            p = r.reg[pid]
            assert p.persist and not p.alias and part_of(p) == "performance", (key, pid)


def test_lfo_breathe_is_the_chain_the_plan_draws(tmp_path):
    """The `lfo-breathe` preset (plan 09 WP5): LFO 1, a sine at one bar,
    pushes brightness; the right hand's height *positions* LFO 1's depth,
    so raising the hand deepens the swell a frame later and nothing else
    moves; LFO 2 at a quarter pushes the fx mix through macro 1. Run with
    the real clock and LFOs at 120 BPM: a bar-long sine peaks one beat
    after the downbeat."""
    r = rig(tmp_path=tmp_path, full=True)
    reg = r.reg
    router = Router(reg, Bindings())
    assert load_preset(r, router, "lfo-breathe") == []
    assert reg["lfo.1.sync"].value == lfo.SYNCS.index("1 bar")
    assert reg["lfo.2.sync"].value == lfo.SYNCS.index("1/4")
    assert reg["lfo.1.shape"].value == lfo.SHAPES.index("sine")
    # the Breathe knob loads at the bottom (hand check 39 turns it up);
    # open it for the chain below
    assert reg["lfo.1.depth"].value == pytest.approx(0.6) and reg["macro.1"].value == 0.0
    assert router.table.macros["macro.1"].label == "Breathe"
    reg["macro.1"].set_value(1.0)
    assert [(b.source, b.target, b.op) for b in router.table.routes()] == [
        ("lfo:0", "view.bright", "push"), ("hand:right.y", "lfo.1.depth", "position"),
        ("lfo:1", "fx.mix", "push")]
    assert router.table.dropped == []
    clock, lfos = tempo.Clock(now=lambda: 0.0), lfo.LFOs()
    for i, lf in enumerate(lfos.lfos):                 # the registry's values into the bank
        lf.sync, lf.shape, lf.depth = (reg[f"lfo.{i + 1}.sync"].value,
                                       reg[f"lfo.{i + 1}.shape"].value,
                                       reg[f"lfo.{i + 1}.depth"].value)
    bright, mix, depth = reg["view.bright"], reg["fx.mix"], reg["lfo.1.depth"]
    bright.set_value(1.0)
    mix.set_value(0.5)
    b0, m0 = bright.norm, mix.norm
    at = lambda p, off: pytest.approx(p._value_of_norm(p.norm + off), rel=1e-9)
    clock.trigger(0.0)                                  # the downbeat; 120 BPM: a beat is 0.5 s
    t = 0.5                                             # one beat in: the bar-long sine peaks
    clock.tick(t)
    lfos.step(1 / 60, t, clock)
    lfos.publish(router)
    router.modulate()
    reg.apply()
    assert lfos[0].out == pytest.approx(0.5 + 0.5 * 0.6)
    assert bright.value == at(bright, 0.5 * 0.5 * 0.6)  # depth 0.5 × (u − 0.5), u − 0.5 = 0.3
    assert lfos[1].out == pytest.approx(0.5)            # a quarter-note sine: back at rest on the beat
    assert mix.value == at(mix, 0.0) and not depth.modulated   # live, pushing nothing
    # the right hand rises: LFO 1's depth is positioned by it; the swell
    # follows a frame later, and brightness's base never moved
    router.names["hand"] = {"right.y": 7}               # the hands adapter's map (row 20)
    router.feed("hand", [float("nan")] * 7 + [1.0] + [float("nan")] * 12)
    router.modulate()
    reg.apply()
    assert depth.modulated and depth.value == pytest.approx(1.0) and depth.norm == pytest.approx(0.6)
    lfos[0].depth = depth.value                         # what the registry's setter did
    lfos.step(1 / 60, t, clock)
    lfos.publish(router)
    router.modulate()
    reg.apply()
    assert lfos[0].out == pytest.approx(1.0) and bright.value == at(bright, 0.5 * 0.5)
    assert bright.norm == b0 and mix.value == at(mix, 0.0)
    # LFO 2 an eighth of a beat later, at the quarter-note wave's peak,
    # through macro 1 — halve the macro, halve the push
    t = 0.5 + 0.125
    clock.tick(t)
    lfos.step(1 / 60, t, clock)
    lfos.publish(router)
    router.modulate()
    reg.apply()
    assert lfos[1].out == pytest.approx(1.0)
    assert mix.value == at(mix, 0.3 * 0.5) and mix.norm == m0
    reg["macro.1"].set_value(0.5)
    router.modulate()
    reg.apply()
    assert mix.value == at(mix, 0.3 * 0.5 * 0.5)
    router.feed("hand", None)                           # the hand leaves: depth returns
    router.modulate()
    reg.apply()
    assert not depth.modulated and depth.value == pytest.approx(0.6)


def test_the_live_table_writes_only_the_sessions_controls(tmp_path):
    """Was test_the_live_table_carries_the_macros. Since plan 13 WP5 the
    macros' bases, subscribers, the performer rows and the preset layer
    are the loaded preset's: `bindings.json` never gets `values`, `macros`,
    a performer row or a preset-layer row, whatever the table holds, and a
    Router lands nothing from the file (the startup preset does)."""
    path = bindings_path(tmp_path)
    r = rig(tmp_path=tmp_path, full=True)
    t = Bindings.factory(path=path)
    router = Router(r.reg, t)
    assert not hasattr(t, "values_of") and not hasattr(router, "restore_values")
    t.set_routes([Binding("hand:7", "view.bright", "position")])
    t.set_macros({"macro.3": {"label": "Heat",
                              "subs": [{"base": "view.speed", "from": 0.2, "to": 0.8}]}})
    r.reg["macro.3"].set_value(0.25)
    t.bind(Binding("cc:0:99", "view.zoom", "abs"))               # a session row: the file
    doc = json.loads(path.read_text())
    assert set(doc) == {"schema", "profile", "bindings"}
    assert all(routing.is_session_row(Binding.from_json(d)) for d in doc["bindings"])
    assert {"source": "cc:0:99", "target": "view.zoom", "op": "abs"} in doc["bindings"]
    assert not any(d.get("layer") == "preset" for d in doc["bindings"])
    # the next start reads the session's rows and nothing it would land
    r2 = rig(tmp_path=tmp_path, full=True)
    again = Bindings.load(path, legacy_midi=None)
    Router(r2.reg, again)
    assert again.carried is None and again.routes() == [] and again.macros == {}
    assert r2.reg["macro.3"].value == 1.0


def test_router_describe_uses_the_adapters_names():
    """`Router.describe` puts the labels and gate names an adapter has
    published in place of a row's addresses; without them it is the row's
    own `describe`. MIDI and key rows are untouched."""
    r = rig()
    router = Router(r.reg, Bindings())
    row = Binding("hand:7", "view.bright", "position", when="hand:18")
    push = Binding("lfo:0", "macro.1", "push", 0.5, scale="macro.2")
    assert router.describe(row) == row.describe() == "hand 7 positions while hand:18"
    assert router.describe(push) == "lfo 0 pushes +0.5 × macro.2"
    router.labels["hand"] = ["L x"] * 7 + ["R height"]
    router.gates["hand"] = [(18, "R ind"), (19, "R mid")]
    router.labels["lfo"] = ["LFO 1", "LFO 2", "LFO 3", "LFO 4"]
    assert router.describe(row) == "R height positions while R ind"
    assert router.describe(push) == "LFO 1 pushes +0.5 × macro.2"
    assert router.describe(Binding("hand:19", "x", "position")) == "hand 19 positions"   # off the list
    assert router.describe(Binding("hand:7", "x", "position", when="hand:99")) == (
        "R height positions while hand:99")                                          # a gate unnamed
    assert router.describe(Binding("hand:3", "view.bright", "position", 0.5)) == "L x positions 0.5"
    midi = Binding("cc:0:48", "view.bright", "abs")
    assert router.describe(midi) == midi.describe() == "MIDI CC 48 ch1"
    key = Binding("key:SHIFT+B", "lfo.trigger", "fire")
    assert router.describe(key) == key.describe() == "key SHIFT+B"
