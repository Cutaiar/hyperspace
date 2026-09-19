"""Plan-07 WP4b: the modulation bus and the unified binding table.

The parity guard first — the "legacy6" routing preset must put the
reference's PLANEDRIVE on rot.rate.* and out[i] on pattern.mod.i, so the
integrated angles and the shader inputs match the pre-WP4b path frame for
frame on the fixture clips and the golden traces — then the table: the
source grammar, the ops, JSON and the midi_map.json migration, the key /
pad adapters, the Router's per-frame pass, presets and runtime edits.
"""

import json
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
    PRESETS,
    ROT_DEPTH,
    Binding,
    Bindings,
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
    and pattern.mod, through the reference's three states — no source
    (rate 1), a source (rate = PLANEDRIVE; a gated band's plane at exactly
    0.0), and the source gone again (rate 1). Rates and angles agree to
    round-off every frame, the shader inputs to an ulp, and all are the
    same float32 the GPU sees; the drive fader keeps meaning (it scales the
    rotation routes, so a change lands the same frame it did before, and
    leaves the pattern inputs raw as the reference did). The factory table
    and the legacy6 preset carry the same rate rows (replace on a base of
    1); only the preset zeroes the pattern bases, so the pattern check is
    the preset's."""
    samples, sr = load_wav(fixture_wavs / f"{clip}.wav")
    old_an, r = Analyser(sr), rig(sr)
    old = LegacyChain(old_an)
    old.dyn = r.chain.dyn = dyn
    old.gain = r.chain.gain = gain
    old_view, view = ViewState(), r.view
    old_view.planes = view.planes = [True] * 6
    router = Router(r.reg, Bindings.factory())
    if table == "legacy6":
        assert router.apply_preset("legacy6") == []
        assert view.pattern_mod[:6] == [0.0] * 6
    assert view.rate == [1.0] * 6                          # WP0's un-driven base
    ticks = list(frames(samples, sr, fps))
    idle = np.ones(6)
    n = 0
    # 1. no source yet: the reference integrates a literal 1 — so do we
    for _chunk, dt in ticks[:20]:
        legacy_integrate(old_view, dt, idle)
        router.modulate(None)
        r.reg.apply()
        view.integrate(dt)
        assert view.rate == [1.0] * 6 and not r.reg["rot.rate.XY"].modulated
        assert view.ang == old_view.ang
    # 2. the source runs: audio replaces the constant
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
        np.testing.assert_allclose(view.rate, planedrive, rtol=RTOL, atol=ATOL_RATE)
        assert np.array_equal(np.float32(view.rate), np.float32(planedrive))
        for i in range(6):                                       # gated → stopped, exactly
            if old.out[i] == 0.0:
                assert view.rate[BANDS[i].plane] == 0.0
        if table == "legacy6":
            np.testing.assert_allclose(view.pattern_mod[:6], old.out, rtol=RTOL, atol=1e-15)
            assert np.array_equal(np.float32(view.pattern_mod[:6]), np.float32(old.out))
        np.testing.assert_allclose(view.ang, old_view.ang, rtol=RTOL, atol=ATOL_ANG)
        assert np.array_equal(np.float32(view.ang), np.float32(old_view.ang))
        n += 1
    assert n > 500
    if clip == "gate-prover":
        assert all(view.rate[BANDS[i].plane] == 0.0 for i in (2, 3, 5))
        assert r.reg[f"rot.rate.{BANDS[2].pl}"].base == 1.0     # the setting is untouched
    # 3. the source goes away: the reference's literal 1 is our base, back
    # the very next frame, and the integrators agree again
    for _chunk, dt in ticks[:20]:
        legacy_integrate(old_view, dt, idle)
        router.modulate(None)
        r.reg.apply()
        view.integrate(dt)
        assert view.rate == [1.0] * 6 and not r.reg["rot.rate.XY"].modulated
        np.testing.assert_allclose(view.ang, old_view.ang, rtol=RTOL, atol=ATOL_ANG)
    if table == "legacy6":
        assert view.pattern_mod[:6] == [0.0] * 6


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
    reference could produce — and the legacy6 depth lands there exactly."""
    assert ROT_RATE_MAX == CEIL * DRIVE * 8.0
    assert ROT_DEPTH == 1 / 16
    r = rig()
    p = r.reg["rot.rate.ZW"]
    assert (p.lo, p.hi) == (-ROT_RATE_MAX, ROT_RATE_MAX)
    r.chain.out[:] = CEIL
    r.chain.gain = 8.0
    Router(r.reg, Bindings(routing.legacy6_routes())).modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == pytest.approx(ROT_RATE_MAX, rel=1e-12)
    assert r.view.rate[BANDS[2].plane] == pytest.approx(-ROT_RATE_MAX, rel=1e-12)
    assert r.view.pattern_mod[:6] == [CEIL] * 6                 # base 1 + 1·u, clamped
    r.reg.apply()                                               # nothing held: bases back
    assert r.view.rate == [1.0] * 6
    # the additive twin lands the same number from a base of 0
    r.view.rate = [0.0] * 6
    rows = [Binding(f"lane:{i}", f"rot.rate.{b.pl}", "mod", b.dir * ROT_DEPTH, scale="master.gain")
            for i, b in enumerate(BANDS)]
    Router(r.reg, Bindings(rows)).modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == pytest.approx(ROT_RATE_MAX, rel=1e-12)


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
    lane = Binding("lane:12", "view.bright", "mod", -0.3)
    assert (lane.scheme, lane.index, lane.kind, lane.is_midi) == ("lane", 12, None, False)
    assert Binding("key:F1", "x").index == -1
    for src, text in (("key:R", "key R"), ("pad:LB", "pad LB"), ("hat:UP", "d-pad UP"),
                      ("cc:0:48", "MIDI CC 48 ch1"), ("note:*:5", "MIDI note 5 any ch"),
                      ("pitch:3", "MIDI pitch bend ch4")):
        assert Binding(src, "x", "abs").describe() == text
    assert Binding("note:0:5", "x", "step", 2).describe() == "MIDI note 5 ch1 step"
    assert Binding("lane:2", "x", "mod", 0.5).describe() == "lane 2 → mod +0.5"
    assert Binding("lane:2", "x", "mod", -1, scale="master.gain").describe() == (
        "lane 2 → mod -1 × master.gain")


def test_json_rows_carry_only_what_differs():
    b = Binding("key:RIGHT", "view.shape", "step", 1)
    assert b.to_json() == {"source": "key:RIGHT", "target": "view.shape", "op": "step"}
    b = Binding("cc:0:48", "view.bright", "abs", feedback="ring", ring=2, pickup=False)
    d = b.to_json()
    assert d == {"source": "cc:0:48", "target": "view.bright", "op": "abs",
                 "feedback": "ring", "pickup": False}
    assert "caught" not in d and Binding.from_json(d) == b
    assert Binding.from_json({"source": "lane:1", "target": "x", "op": "mod", "value": -2,
                              "enabled": False, "junk": 1}) == Binding(
        "lane:1", "x", "mod", -2, False)


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
    t.add(Binding("lane:2", "view.bright", "mod", 0.4))
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
        if b.op == "mod":
            assert r.reg[b.target].modulatable, b
    keys = [b.key for b in t.bindings if b.scheme != "lane"]
    assert len(keys) == len(set(keys))
    assert len(t.of("key")) == 23 and len(t.of("pad")) == 10 and len(t.of("hat")) == 4
    assert len(t.midi()) == 111 and len(t.mods()) == 12


def test_factory_files_match_the_code():
    """hyperspace/library/bindings/*.json are exports of the factory table
    and the routing presets — `python -m hyperspace.routing` regenerates."""
    d = routing.FACTORY_DIR
    assert json.loads((d / "default.json").read_text()) == Bindings.factory().to_json()
    for name, (routes, values) in PRESETS.items():
        preset = Bindings(routes, values=values).to_json()
        assert json.loads((d / f"{name}.json").read_text()) == preset
    assert re.search(r'^  \{"source": "key:RIGHT"', (d / "default.json").read_text(), re.MULTILINE)


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
    router = Router(r.reg, Bindings([Binding("lane:1", "view.bright", "mod", 0.2)]))
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


def test_replace_op_is_the_value_while_live():
    """replace: effective = value · scale · u in the param's units, the base
    untouched and back when the source stops; the offset goes through
    modulate() as norm_of(want) − base_norm, so range and wrap are mod's."""
    r = rig()
    rate, yaw = r.reg["rot.rate.XY"], r.reg["camera.yaw"]
    rate.set_value(1.0)
    yaw.set_value(3.0)
    t = Bindings([
        Binding("lane:0", "rot.rate.XY", "replace", -10.0),
        Binding("lane:1", "camera.yaw", "replace", 2 * np.pi, scale="view.speed"),
        Binding("lane:2", "gone.param", "replace", 1.0),               # dormant
        Binding("lane:2", "band.select", "replace", 1.0),              # dormant
        Binding("lane:2", "rot.rate.XZ", "replace", 1.0, scale="nope"),  # dormant
    ])
    router = Router(r.reg, t)
    r.chain.out[:] = [CEIL / 2, CEIL, 1.0, 0, 0, 0]                  # u = 0.5, 1, …
    r.view.speed = 0.25
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[0] == pytest.approx(-5.0, abs=1e-13) and rate.base == 1.0
    assert r.view.yaw == pytest.approx(np.pi / 2, abs=1e-12) and yaw.base == pytest.approx(3.0)
    assert r.view.rate[1] == 1.0 and not r.reg["rot.rate.XZ"].modulated
    r.chain.out[0] = CEIL                                            # u = 1: −10, in range
    r.view.speed = 1.25                                              # 2.5π: wraps to π/2
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[0] == pytest.approx(-10.0, abs=1e-13)
    assert r.view.yaw == pytest.approx(np.pi / 2, abs=1e-12)
    t.mods()[0].value = -1000.0                                      # clamps at the end stop
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[0] == -ROT_RATE_MAX
    router.modulate(None)
    r.reg.apply()
    assert r.view.rate[0] == 1.0 and r.view.yaw == pytest.approx(3.0)
    assert not rate.modulated and not yaw.modulated
    # a tapered target lands on the taper's own detent of the value
    b = r.reg["view.bright"]
    b.set_value(1.0)
    Router(r.reg, Bindings([Binding("lane:1", "view.bright", "replace", 2.0)])).modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == b.taper.map(b.taper.unmap(2.0)) and b.base == 1.0
    assert Binding.from_json(Binding("lane:1", "x", "replace", 2.0).to_json()).op == "replace"


def test_routes_sum_and_dormant_rows_are_no_ops():
    r = rig()
    b = r.reg["view.bright"]
    b.set_value(1.0)
    base = b.norm
    t = Bindings([
        Binding("lane:0", "view.bright", "mod", 0.2),
        Binding("lane:1", "view.bright", "mod", -0.1),
        Binding("lane:2", "view.bright", "mod", 5.0, enabled=False),   # off
        Binding("lane:9", "view.bright", "mod", 5.0),                  # no such lane
        Binding("lane:0", "band.select", "mod", 5.0),                  # not modulatable
        Binding("lane:0", "gone.param", "mod", 5.0),                   # not a param
        Binding("ext:0", "view.bright", "mod", 5.0),                   # no feed yet
    ])
    router = Router(r.reg, t)
    r.chain.out[:] = CEIL                                              # u = 1 everywhere
    r.control.selb = 2
    router.modulate(r.chain)
    r.reg.apply()
    assert b.eff_norm == pytest.approx(base + 0.1, abs=1e-9)
    assert r.control.selb == 2 and not r.reg["band.select"].modulated
    # WP4c's external lanes: a fed vector is a source like the analyzer's
    router.feed("ext", [0.5])
    router.modulate(r.chain)
    r.reg.apply()
    assert b.eff_norm == pytest.approx(min(base + 0.1 + 2.5, 1.0), abs=1e-9)
    router.feed("ext", None)
    router.modulate(r.chain)
    r.reg.apply()
    assert b.eff_norm == pytest.approx(base + 0.1, abs=1e-9)


def test_routes_are_editable_at_runtime():
    r = rig()
    router = Router(r.reg, Bindings.factory())
    r.chain.out[:] = 1.0
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == pytest.approx(DRIVE, rel=1e-12)   # replaced the base 1
    row = router.table.routes_to(f"rot.rate.{BANDS[0].pl}")[0]
    row.value = 0.0                                    # replace with 0: the plane stops
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == 0.0
    row.op = "mod"                                     # additive now: held at the base
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == pytest.approx(1.0)
    router.table.remove(row)
    router.modulate(r.chain)
    r.reg.apply()
    assert not r.reg[f"rot.rate.{BANDS[0].pl}"].modulated and r.view.rate[BANDS[0].plane] == 1.0
    added = router.table.add(Binding("lane:0", "view.bright", "mod", 0.5))
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
    router = Router(r.reg, Bindings([Binding("lane:0", "band.3.thr", "mod", 0.3)]))
    r.chain.out[0] = CEIL
    router.modulate(r.chain)
    r.reg.apply()
    assert r.chain.params[3].thr == thr._value_of_norm(base + 0.3)
    r.chain.step(1 / 60)                               # the chain reads the modulated value
    assert thr.norm == base                            # the user's setting is untouched


def test_apply_preset_replaces_routes_and_lands_bases(tmp_path):
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings.factory())
    router.table.add(Binding("lane:0", "view.bright", "mod", 0.5))
    n_inputs = len(router.table.of(*routing.INPUT_SCHEMES))
    r.view.rate[0] = 2.0
    assert router.apply_preset("legacy6") == []
    assert len(router.table.mods()) == 12 and not router.table.routes_to("view.bright")
    assert len(router.table.of(*routing.INPUT_SCHEMES)) == n_inputs
    assert r.view.pattern_mod == [0.0] * 6 + [1.0] * (N_MOD - 6)
    assert r.view.rate == [2.0] + [1.0] * 5              # rate bases are the user's
    for name in PLANES:
        assert router.table.routes_to(f"rot.rate.{name}")[0].op == "replace"
    # the preset's rows are copies: editing one never edits the preset
    router.table.mods()[0].value = 99
    assert PRESETS["legacy6"][0][0].value == DRIVE * CEIL


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
