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

from hyperspace import routing
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import BANDS, CEIL, DRIVE, default_params
from hyperspace.control import Control
from hyperspace.geometry import RATE
from hyperspace.library import Library
from hyperspace.offline import load_wav
from hyperspace.overlay import Output
from hyperspace.params import PLANES, ROT_RATE_MAX, build_registry
from hyperspace.render import N_MOD, ViewState
from hyperspace.routing import (
    MOD_OPS,
    PRESETS,
    ROT_DEPTH,
    SCHEMA,
    Binding,
    Bindings,
    Owned,
    Router,
    bindings_path,
    legacy_planedrive,
)

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
    presets = lib.bank if full else None
    reg = build_registry(view, control, audio, presets)
    if full:
        lib.attach(reg)
    if full:
        reg.toggle("ui.panel", "Panel", lambda: True, lambda v: None)
        reg.toggle("ui.cheatsheet", "Sheet", lambda: True, lambda v: None)
        reg.toggle("audio.mic", "Mic", lambda: False, lambda v: None)
        reg.trigger("audio.restart", "Restart", lambda: None)
        reg.trigger("audio.stop", "Stop", lambda: None)
        reg.toggle("audio.play", "Play", lambda: False, lambda v: None)
        Output(None, None).register(reg)
    return SimpleNamespace(reg=reg, view=view, control=control, audio=audio, chain=chain)


def legacy_integrate(view: ViewState, dt: float, planedrive) -> None:
    """render.ViewState.integrate as it was before WP4b, rate[p] = 1."""
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
    router = Router(r.reg, Bindings.factory())
    assert view.rate == [1.0] * 6                          # WP0's un-driven base
    if table == "legacy6":
        assert router.apply_preset("legacy6") == []
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
    router = Router(r.reg, Bindings.factory())
    router.apply_preset("legacy6")
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
    assert r.reg.restore(routing.legacy6_values()) == []
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
    # rest only when it isn't 0 — a lane's rows stay as short as they were
    assert "rest" not in Binding("lane:1", "x", "push", 0.5).to_json()
    d = Binding("lfo:0", "x", "push", 0.5, rest=0.5).to_json()
    assert d["rest"] == 0.5 and Binding.from_json(d).rest == 0.5


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
    t.add(Binding("lane:2", "view.bright", "push", 0.4))
    t.write()
    text = path.read_text()
    assert text.count("\n  {") == n + 1                 # one row per line
    t2 = Bindings.load(path)
    assert t2.to_json() == t.to_json() and t2.profile == "apc40" and not t2.error
    assert t2.routes_to("view.bright")[0].value == 0.4
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
    assert "migrated 2 rows" in capsys.readouterr().err
    assert path.exists()                                # written once, then the file rules
    assert [b.source for b in t.midi()] == ["cc:0:87", "note:0:65"]
    assert t.for_param("view.lines").op == "toggle"
    assert len(t.of("key")) == len(routing.keymap()) and len(t.mods()) == 12
    legacy.unlink()
    assert Bindings.load(path, legacy_midi=legacy).to_json() == t.to_json()
    # without either file: the factory table, nothing written
    t0 = Bindings.load(tmp_path / "none.json", legacy_midi=tmp_path / "nope.json")
    assert t0.to_json() == Bindings.factory().to_json() and not (tmp_path / "none.json").exists()


def test_factory_table_binds_only_real_params(tmp_path):
    r = rig(tmp_path=tmp_path, full=True)
    t = Bindings.factory()
    ids = set(r.reg.ids())
    for b in t.bindings:
        assert b.target in ids, b
        assert b.op in routing.OPS, b
        if b.op in MOD_OPS:
            assert r.reg[b.target].modulatable, b
    keys = [b.key for b in t.bindings if b.scheme != "lane"]
    assert len(keys) == len(set(keys))
    assert len(t.of("key")) == 23 and len(t.of("pad")) == 10 and len(t.of("hat")) == 4
    assert len(t.midi()) == 111 and len(t.mods()) == 12
    assert routing.referee(t.bindings)[1] == []           # one owner per target


def test_factory_files_match_the_code():
    """hyperspace/library/bindings/*.json are exports of the factory table
    and the routing presets — `python -m hyperspace.routing` regenerates —
    and every file there, the hand-written hand presets included, is at
    the current schema with one owner per target."""
    d = routing.FACTORY_DIR
    assert json.loads((d / "default.json").read_text()) == Bindings.factory().to_json()
    for name, (routes, values) in PRESETS.items():
        preset = Bindings(routes, values=values).to_json()
        assert json.loads((d / f"{name}.json").read_text()) == preset
    assert re.search(r'^  \{"source": "key:RIGHT"', (d / "default.json").read_text(), re.MULTILINE)
    for path in sorted(d.glob("*.json")):
        doc = json.loads(path.read_text())
        assert doc["schema"] == SCHEMA, path.name
        t = Bindings.from_json(doc)
        assert not t.migrated and t.dropped == [], path.name
        assert all(b.op in MOD_OPS for b in t.bindings if b.scheme in routing.LANE_SCHEMES)


# -------------------------------------------------------------- adapters

class FakeKeys:
    """app.Keys' interface: pressed(glfw_key) is an edge."""

    def __init__(self):
        self.hits: set[int] = set()

    def pressed(self, key: int) -> bool:
        return key in self.hits


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
    router = Router(r.reg, Bindings.factory())
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


def test_pad_adapter_routes_buttons_and_hat(tmp_path):
    from hyperspace import gamepad

    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
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
    # a lane's rows rest at 0: the row as it always was
    lane = Binding("lane:1", "view.bright", "push", 0.2)
    assert lane.rest == 0.0
    Router(r.reg, Bindings([lane])).modulate(r.chain)


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
    router = Router(r.reg, Bindings.factory())
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


def test_apply_preset_replaces_routes_and_lands_bases(tmp_path):
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
    router.table.add(Binding("lane:0", "view.bright", "push", 0.5))
    n_inputs = len(router.table.of(*routing.INPUT_SCHEMES))
    r.view.rate[0] = 2.0
    assert router.apply_preset("legacy6") == []
    assert len(router.table.mods()) == 12 and not router.table.routes_to("view.bright")
    assert len(router.table.of(*routing.INPUT_SCHEMES)) == n_inputs
    assert r.view.pattern_mod == [0.0] * 6 + [1.0] * (N_MOD - 6)
    assert r.view.rate == [0.0] * 6                      # a push lands the drive only on 0
    for name in PLANES:
        assert router.table.routes_to(f"rot.rate.{name}")[0].op == "push"
    assert router.table.dropped == []
    # the preset's rows are copies: editing one never edits the preset
    router.table.mods()[0].value = 99
    assert PRESETS["legacy6"][0][0].value == BANDS[0].dir * ROT_DEPTH


def test_midi_view_shares_the_table(tmp_path):
    """midi.MidiMap over the app's table: a learn lands in bindings.json
    next to the keys, and the MIDI view sees only MIDI rows."""
    from hyperspace.midi import MidiMap

    t = Bindings.factory(path=bindings_path(tmp_path))
    m = MidiMap(table=t)
    assert len(m.bindings) == 111 and all(b.is_midi for b in m.bindings)
    m.bind(Binding("cc:0:99", "view.zoom", "abs"))
    assert m.for_param("view.zoom").number == 99
    again = Bindings.load(bindings_path(tmp_path))
    assert again.for_param("view.zoom").source == "cc:0:99"
    assert len(again.of("key")) == 23 and len(again.mods()) == 12
    m.unbind("view.zoom")
    assert Bindings.load(bindings_path(tmp_path)).for_param("view.zoom") is None


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
    These are shipped, so check every row lands somewhere real."""
    from hyperspace.hands import PINCHES, SIDES, HandSettings

    r = rig(full=True)
    router = Router(r.reg, Bindings())
    assert router.load_preset(name) == []          # no unknown target ids
    rows = router.table.routes()
    assert rows and router.table.dropped == []     # one owner per target
    axes = len(HandSettings.from_config({}).axes)
    lanes = axes + len(SIDES) + len(SIDES) * len(PINCHES)
    for b in rows:
        p = r.reg.get(b.target)
        assert p is not None and p.modulatable, f"{name}: {b.target} is dormant"
        assert b.scheme == "hand" and 0 <= b.index < axes, f"{name}: {b.source}"
        if b.when is not None:
            i = int(b.when.split(":")[1])
            assert axes + len(SIDES) <= i < lanes, f"{name}: {b.when} is not a switch"


@pytest.mark.parametrize("name", ["hands-play", "hands-pinch", "hands-fx"])
def test_the_hand_presets_reach_both_ends_of_their_targets(name):
    """A hand row with no depth of its own means the whole control: the
    hand's 0 and 1 are the fader's end stops, whatever the taper. (They
    were `replace` rows once, which cap a 0–1 hand at the *value* 1.)"""
    r = rig(full=True)
    router = Router(r.reg, Bindings())
    router.load_preset(name)
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
    assert t.performers() == [first]
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
    doc = Bindings([Binding("hand:7", "view.bright", "position"),
                    Binding("hand:1", "view.bright", "position")]).to_json()
    assert Bindings.from_json(doc).dropped[0][0].source == "hand:1"
    # apply_preset: the factory presets have one owner per target
    router.apply_preset("legacy6")
    assert t.dropped == []


def test_load_preset_lists_what_it_dropped(tmp_path):
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
    d = tmp_path / "bindings"
    d.mkdir()
    (d / "twice.json").write_text(Bindings([
        Binding("hand:7", "view.bright", "position"),
        Binding("hand:1", "view.bright", "position", when="hand:14"),   # a gate is no exemption
    ]).dumps())
    assert router.load_preset("twice", tmp_path) == []
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
    with a rest by scheme (an LFO and a centred default hand axis 0.5,
    else 0), span → position, a lane-scheme abs → position at depth 1 with
    pickup forgotten, replace dropped, a second owner dropped — each
    dropped row on stderr — and written back at schema 2, after which the
    file rules and nothing is said again."""
    from hyperspace.hands.core import BIPOLAR, DEFAULT_DOFS

    assert DEFAULT_DOFS[3] in BIPOLAR and DEFAULT_DOFS[1] not in BIPOLAR   # what 0.5 / 0 mean
    path = bindings_path(tmp_path)
    path.write_text(json.dumps(V1_FILE))
    t = Bindings.load(path, legacy_midi=None)
    err = capsys.readouterr().err
    assert t.migrated and not t.error
    assert "dropped lane:1 → rot.rate.XY (replace)" in err
    assert "dropped hand:2 → view.depth4: view.depth4 is already performed by hand 7" in err
    assert f"migrated {path} to {SCHEMA} (2 rows dropped)" in err
    rows = {(b.source, b.target): b for b in t.bindings}
    assert rows[("key:RIGHT", "view.shape")].op == "step"
    assert rows[("cc:0:48", "view.bright")].op == "abs"                       # MIDI keeps abs
    pat, roll, height = (rows[("lane:0", "pattern.mod.0")], rows[("hand:3", "view.inst_amp")],
                         rows[("hand:1", "view.speed")])
    assert (pat.op, pat.rest) == ("push", 0.0)
    assert (roll.op, roll.rest, roll.value) == ("push", 0.5, 0.4)
    assert (height.op, height.rest) == ("push", 0.0)
    assert rows[("hand:7", "view.depth4")].op == "position"
    z = rows[("hand:7", "camera.zoom")]
    assert (z.op, z.value, z.pickup, z.when) == ("position", 1.0, True, "hand:18")
    lfo = rows[("lfo:0", "fx.mix")]
    assert (lfo.op, lfo.rest) == ("push", 0.5)
    assert ("lane:1", "rot.rate.XY") not in rows and ("hand:2", "view.depth4") not in rows
    assert [b.source for b, _ in t.dropped] == ["hand:2"]
    assert t.values == {"pattern.mod.0": 0.0}
    # written back once, at schema 2; the second load is quiet
    doc = json.loads(path.read_text())
    assert doc["schema"] == SCHEMA and doc == t.to_json()
    again = Bindings.load(path, legacy_midi=None)
    assert not again.migrated and again.to_json() == t.to_json() and capsys.readouterr().err == ""
    # a v1 preset file loads through the same door
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
    d = tmp_path / "bindings"
    d.mkdir()
    (d / "old.json").write_text(json.dumps(V1_FILE))
    router.load_preset("old", tmp_path)
    assert {b.op for b in router.table.routes()} == {"push", "position"}
    assert [b.source for b, _ in router.table.dropped] == ["hand:2"]


def test_default_rest_follows_the_default_dof_layout():
    from hyperspace.hands.core import BIPOLAR, DEFAULT_DOFS

    n = len(DEFAULT_DOFS)
    for side in range(2):
        for k, dof in enumerate(DEFAULT_DOFS):
            assert routing.default_rest(f"hand:{side * n + k}") == (0.5 if dof in BIPOLAR else 0.0)
    assert routing.default_rest(f"hand:{2 * n}") == 0.0          # a presence lane
    assert routing.default_rest("lfo:3") == 0.5
    assert routing.default_rest("lane:0") == routing.default_rest("ext:2") == 0.0
    assert routing.default_rest("hand:x") == 0.0


def test_rests_default_a_push_rows_rest():
    """An adapter publishes where its lanes idle next to their labels; the
    page reads it through `Router.rest_of` when it adds a push row."""
    r = rig()
    router = Router(r.reg, Bindings())
    assert router.rest_of("lane:0") == 0.0 and router.rest_of("hand:3") == 0.0
    router.rests["hand"] = [0.5, 0.0, 0.5]
    assert router.rest_of("hand:0") == 0.5 and router.rest_of("hand:1") == 0.0
    assert router.rest_of("hand:9") == 0.0 and router.rest_of("hand:x") == 0.0
