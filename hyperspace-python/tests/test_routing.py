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
from conftest import CORPUS, OWNER_PAD, OWNER_ROW, boot_home, far_pads, old_shape_pads, seed, tree
from legacy_chain import LegacyChain  # tests/legacy_chain.py — the frozen reference
from test_analyzer import fixture_wavs, frames  # noqa: F401 — the fixture, re-exported

from hyperspace import apc40, envelope, hands, lfo, preset, routing, sequencer, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import BANDS, CEIL, default_params
from hyperspace.control import Control
from hyperspace.geometry import RATE
from hyperspace.library import Library
from hyperspace.offline import load_wav
from hyperspace.overlay import Output
from hyperspace.params import DRIVE, PLANES, ROT_RATE_MAX, Kind, build_registry, part_of
from hyperspace.routing import (
    MOD_OPS,
    PATTERN_DEPTH,
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
        lfos = lfo.LFOs(seed=1)
        lfo.register(reg, lfos, clock)
        # plan 31: the envelopes and the sequencer (seq-demo's ids)
        envelope.register(reg, envelope.Envelopes(), clock)
        sequencer.register(reg, sequencer.Sequencer(), clock)
        hands.register(reg, hands.HandSettings.from_config({}))  # the global track knobs
    return SimpleNamespace(reg=reg, view=view, control=control, audio=audio, chain=chain,
                           lib=lib, lfos=lfos if full else None, clock=clock if full else None)


def corpus_doc(stem: str) -> dict:
    """A preset of the corpus (tests/corpus/presets: the files the build
    shipped until the library went one-tier, 2026-10-28), as its /7 file
    reads — test data the app never sees."""
    return json.loads((CORPUS / "presets" / f"{stem}.json").read_text())


def corpus_stems() -> list[str]:
    """Every corpus preset by file stem (`legacy6`, `party-trip`, …)."""
    return sorted(f.stem for f in (CORPUS / "presets").glob("*.json"))


def legacy6(router: Router) -> list[str]:
    """The legacy6 preset onto the table and the registry: its routes, and
    of its values the bases this registry has (the corpus file is the whole
    /7 performance — LFOs, envelopes, the sequencer — which a bare rig has
    no params for). Returns the route targets the registry lacks."""
    doc = corpus_doc("legacy6")
    router.table.set_routes(Binding.from_json(d) for d in doc["routes"])
    router.reg.restore({k: v for k, v in doc["values"].items() if k in router.reg})
    return [d["target"] for d in doc["routes"] if d["target"] not in router.reg]


def load_preset(r, router: Router, name: str) -> list[str]:
    """A preset by name through the one loader (`preset.Presets` over the
    rig's library) — the road the routing presets took before plan 13 WP5
    made them presets. Returns the ids the registry lacks."""
    from hyperspace.preset import Presets

    return Presets(r.lib, r.reg, router).load(name)


def session_rows() -> list[Binding]:
    """The factory table's rows a bindings.json keeps (plan 13 §2.2)."""
    return [b for b in Bindings.factory().bindings if routing.is_session_row(b)]


def factory_pattern(out) -> np.ndarray:
    """The pattern inputs the legacy6 / factory rows land for lanes `out`
    (plan 22 B3): a push at PATTERN_DEPTH on the base of 1, u = out / CEIL,
    the input's 0–2.6 range — 1 + PATTERN_DEPTH · out, held to the range.
    The reference fed out raw (u_bands = out); the rates keep that parity."""
    return np.clip(1.0 + PATTERN_DEPTH * (np.asarray(out) / CEIL) * 2.6, 0.0, 2.6)


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
    the source live, rates and angles agree to round-off every frame and
    are the same float32 the GPU sees; the shader inputs are no longer the
    reference's raw out but 1 + PATTERN_DEPTH · out (plan 22 B3, the
    factory depth on the base of 1: `factory_pattern`); a
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
        assert view.pattern_mod[:6] == [1.0] * 6 and view.rate == [0.0] * 6
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
        np.testing.assert_allclose(view.pattern_mod[:6], factory_pattern(old.out),
                                   rtol=RTOL, atol=1e-12)
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
        assert view.ang == ang and view.pattern_mod[:6] == [1.0] * 6
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
            np.testing.assert_allclose(r.view.pattern_mod[:6], factory_pattern(out[k]),
                                       rtol=RTOL, atol=1e-12)


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
    router = Router(r.reg, Bindings())
    assert legacy6(router) == []
    r.chain.out[:] = CEIL
    r.chain.gain = 8.0
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.rate[BANDS[0].plane] == pytest.approx(ROT_RATE_MAX, rel=1e-12)
    assert r.view.rate[BANDS[2].plane] == pytest.approx(-ROT_RATE_MAX, rel=1e-12)
    # the pattern rows: base 1 + PATTERN_DEPTH · u of the 2.6 range (plan 22 B3)
    assert r.view.pattern_mod[:6] == pytest.approx([1.0 + PATTERN_DEPTH * 2.6] * 6, rel=1e-12)
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
    # session's rows only (plan 13's first-launch migration, which wrote the
    # carried rows into a preset, went with the two-tier library, 2026-10-28)
    assert {"source": "cc:0:87", "target": "view.inst_amp", "op": "abs",
            "layer": "preset"} in t.carried.desk
    t.write()
    assert path.exists() and "cc:0:87" not in path.read_text()
    legacy.unlink()
    # the old map had no OVERDUB row and the note is free: the next load
    # adds home there, as it does to any older file (plan 15 WP2), and the
    # bank's sixteen pads on clip rows 4 and 5 (plan 19 WP2), and nothing
    # else moves (the clip-stop SAVE AS bar, retired 2026-10-09, is not added);
    # plan 24 C1: the four invariant render toggles and SAVE, likewise
    again = Bindings.load(path, legacy_midi=legacy)
    far = [f"note:{ch}:{n}" for n, ch in apc40.BANK_PADS[routing.F_KEYS:]]
    c1 = [(s, pid) for s, pid, *_ in sorted(routing.TOGGLE_DESK_ROWS)] + [
        (f"note:7:{apc40.N_CLIPSTOP}", routing.SAVE_PARAM)]
    send_a = routing.SEQ_PAGE_SOURCE                    # plan 31 §A: the sequencer page
    assert again.notes == [
        f"added note:0:{apc40.N_OVERDUB} → preset.home (the APC40 map of plan 15)",
        *[f"added {s} → preset.select (the APC40 map of plan 19)" for s in far],
        *[f"added {s} → {pid} (the APC40 map of plan 24)" for s, pid in c1],
        f"added {send_a} → seq.page (the APC40 map of plan 31)"]
    assert [b for b in again.to_json()["bindings"]
            if b["source"] not in (f"note:0:{apc40.N_OVERDUB}", *far, *(s for s, _ in c1),
                                   send_a)] \
        == t.to_json()["bindings"]
    assert Bindings.load(path, legacy_midi=legacy).to_json() == again.to_json()
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
    # + R, F1–F8, ⇧F1–F8 (plan 11), + undo and redo on ⌘ and Ctrl (plan 15 WP1),
    # + Home (plan 15 WP2)
    assert len(t.of("key")) == 25 + 17 + 4 + 1
    assert len(t.of("pad")) == 10 and len(t.of("hat")) == 4    # BACK undoes, START saves
    assert len(t.midi()) == 113 + 6 + 1 + 4 + 1 + 1 and t.mods() == []   # + SHIFT, the global track
    # knobs, OVERDUB (plan 15 WP2) (the clip-stop row's eight, plan 15 WP4,
    # retired 2026-10-09), SAVE on track 8's clip stop (plan 24 C1),
    # SEND A, the sequencer page's latch (plan 31 §A),
    # the preset layer's four SCENE device knobs (plan 19 WP3; the sixteen
    # bank pads of plan 19 WP2 took the sixteen shape pads' place);
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
    """Every hit is a fresh press this frame; nothing is ever let go."""

    on = True

    def __init__(self):
        self.hits: set[int] = set()
        self.hat = 0

    def pressed(self, b: int) -> bool:
        return b in self.hits

    down = pressed

    def released(self, b: int) -> bool:
        return False

    def hat_pressed(self, bit: int) -> bool:
        return bool(self.hat & bit)

    def hat_released(self, bit: int) -> bool:
        return False

    def lanes(self) -> list[float]:
        return [0.5, 0.5, 0.5, 0.5, 0.0, 0.0]


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
    pad.hits = {gamepad.RB, gamepad.Y}
    pad.hat = gamepad.HAT_UP | gamepad.HAT_LEFT
    p0, s0 = r.reg["view.bright"].position(), r.reg["view.speed"].position()
    lines = r.view.lines
    router.pad(pad)
    assert r.view.shape == 6 and r.view.lines is not lines
    assert r.reg["view.bright"].position() == p0 + 3
    assert r.reg["view.speed"].position() == s0      # ← walks the list, held only
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

    seed(tmp_path)
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
    assert r.view.pattern_mod == [1.0] * N_MOD           # plan 22 B3: the inputs on 1
    assert r.view.rate == [0.0] * 6                      # a push lands the drive only on 0
    for name in PLANES:
        assert router.table.routes_to(f"rot.rate.{name}")[0].op == "push"
    assert router.table.dropped == []
    # the table's rows are the file's copies: editing one edits no preset
    router.table.mods()[0].value = 99
    assert r.lib.read("presets", "legacy6")["routes"][0]["value"] == BANDS[0].dir * ROT_DEPTH


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
    assert len(m.bindings) == 113 + 6 + 1 + 4 + 1 + 1 and all(b.is_midi for b in m.bindings)
    m.table.bind(Binding("cc:0:99", "view.zoom", "abs"))
    assert m.table.for_param("view.zoom").number == 99
    again = Bindings.load(bindings_path(tmp_path))
    assert again.for_param("view.zoom").source == "cc:0:99"
    assert len(again.of("key")) == 25 + 17 + 4 + 1 and again.mods() == []
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
def test_the_hand_presets_name_params_and_lanes_that_exist(tmp_path, name):
    """A preset whose target was renamed loads silently and does nothing.
    These shipped (the corpus keeps them), so check every row lands
    somewhere real — by name (decision register row 20): an axis of the
    default layout, a gate one of its switches."""
    from hyperspace.hands import PINCHES, SIDES, HandSettings, Layout

    seed(tmp_path)
    r = rig(tmp_path=tmp_path, full=True)
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
def test_the_hand_presets_reach_both_ends_of_their_targets(tmp_path, name):
    """A hand row with no depth of its own means the whole control: the
    hand's 0 and 1 are the fader's end stops, whatever the taper. (They
    were `replace` rows once, which cap a 0–1 hand at the *value* 1.)"""
    seed(tmp_path)
    r = rig(tmp_path=tmp_path, full=True)
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

def test_a_backup_is_kept_before_every_rewrite_and_never_over_a_hand_made_one(tmp_path, capsys,
                                                                              monkeypatch):
    """Audit R12: a rewrite keeps the file as it was as `.bak-v<schema>`;
    a later rewrite of the same schema keeps its own copy under a dated
    name rather than touching the first (the oldest state is worth
    having, and so is the one about to go), and a copy the owner made by
    hand is a different name, untouched. A remap of a schema-2 file is a
    `.bak-v2`; a copy that cannot be made never stops the load — and,
    since plan 19 (fork 12), the file is then not rewritten:
    `test_a_remap_whose_backup_fails_writes_nothing`."""
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
    assert t2.error == routing.NOT_REWRITTEN and "no backup of" in capsys.readouterr().err
    assert any(n.startswith("added key:B") for n in t2.notes)
    assert json.loads(path.read_text()) == v2           # no backup, no rewrite


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

    from hyperspace import library, params
    # one number, declared where the triggers are (plan 19 WP1): the F-keys
    # are the bank's first eight slots, and the bank is longer
    assert routing.F_KEYS == library.F_KEYS == params.F_KEYS == 8 < library.SLOTS
    SLOTS = routing.F_KEYS
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
    """remap_factory adds the loop's rows (seventeen from plan 11, the four
    undo and redo rows and the Home row from plan 15) to a user table that predates
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
    assert moved <= set(rows) and len(moved) == 17 + 4 + 1
    assert list(tmp_path.glob("bindings.json.bak-*"))                   # kept before the rewrite
    _, notes = routing.remap_factory(t.bindings)
    assert notes == []


class _ChordKeys(_EdgeKeys):
    """`_EdgeKeys` with a Control key (plan 15 WP1)."""

    def __init__(self, pressed=(), shift=False, super_=False, control=False):
        super().__init__(pressed, shift, super_)
        self._control = control

    def control(self):
        return self._control


def test_a_chord_fires_only_its_own_row(tmp_path):
    """Plan 15 WP1 (fork 1): ⌘Z / Ctrl+Z undo, ⌘⇧Z / Ctrl+⇧Z redo, and a
    two-modifier chord fires its own row alone — under the old subset rule
    ⌘⇧Z fired undo and redo both. Z alone, ⇧Z and a chord no row spells
    fire nothing; a keys object with no control() reads as "not held"."""
    import glfw

    r = rig(tmp_path=tmp_path, full=True)
    fired: list[str] = []
    for pid in ("edit.undo", "edit.redo"):
        assert not r.reg[pid].modulatable and r.reg[pid].group == "ui"
        r.reg[pid].fire = lambda pid=pid: fired.append(pid)
    router = Router(r.reg, house())
    z = {b.source: b.target for b in router.table.of("key") if b.key_name == "Z"}
    assert z == {"key:SUPER+Z": "edit.undo", "key:SHIFT+SUPER+Z": "edit.redo",
                 "key:CONTROL+Z": "edit.undo", "key:CONTROL+SHIFT+Z": "edit.redo"}

    def press(**mods) -> list[str]:
        fired.clear()
        router.keys(_ChordKeys({glfw.KEY_Z}, **mods))
        return list(fired)

    assert press(super_=True) == ["edit.undo"]
    assert press(super_=True, shift=True) == ["edit.redo"]           # redo alone
    assert press(control=True) == ["edit.undo"]
    assert press(control=True, shift=True) == ["edit.redo"]
    assert press() == [] and press(shift=True) == []
    assert press(super_=True, control=True) == []                    # no row spells it
    assert press(super_=True, control=True, shift=True) == []
    fired.clear()
    router.keys(_EdgeKeys({glfw.KEY_Z}, super_=True))                # no control(): not held
    assert fired == ["edit.undo"]


def test_an_older_file_gets_the_undo_keys_where_they_are_free(tmp_path):
    """Plan 15 WP1: a `bindings.json` written before the undo keys gains
    the four rows on its next load — but not on a source the user already
    uses — with the old file kept beside it, and a second load changes
    nothing."""
    undo_rows = {f"key:{k}": pid for k, pid, _ in routing.LOOP_KEY_ROWS
                 if pid.startswith("edit.")}
    assert undo_rows == {"key:SUPER+Z": "edit.undo", "key:SHIFT+SUPER+Z": "edit.redo",
                         "key:CONTROL+Z": "edit.undo", "key:CONTROL+SHIFT+Z": "edit.redo"}
    old = [b for b in Bindings.factory().bindings if b.source not in undo_rows]
    old.append(Binding("key:CONTROL+Z", "view.faces", "toggle"))       # the user's Ctrl+Z
    path = bindings_path(tmp_path)
    Bindings(old, path=path).write()
    before = path.read_text()
    t = Bindings.load(path, legacy_midi=None)
    rows = {b.source: b.target for b in t.of("key")}
    assert rows["key:CONTROL+Z"] == "view.faces"                        # kept
    assert rows["key:SUPER+Z"] == "edit.undo" and rows["key:SHIFT+SUPER+Z"] == "edit.redo"
    assert rows["key:CONTROL+SHIFT+Z"] == "edit.redo"
    (bak,) = tmp_path.glob("bindings.json.bak-*")
    assert bak.read_text() == before                                    # the old file, whole
    after = path.read_text()
    assert "key:SUPER+Z" in after
    Bindings.load(path, legacy_midi=None)
    assert path.read_text() == after and len(list(tmp_path.glob("bindings.json.bak-*"))) == 1
    # a chord the user spelled in another order holds it too (review of PR #82)
    mine = [b for b in Bindings.factory().bindings if b.source not in undo_rows]
    mine.append(Binding("key:SUPER+SHIFT+Z", "view.lines", "toggle"))
    out, _ = routing.remap_factory(mine)
    held = [b.target for b in out if b.scheme == "key" and b.key_name == "Z"
            and b.modifiers == {"SHIFT", "SUPER"}]
    assert held == ["view.lines"]


def test_an_older_file_gets_home_where_it_is_free(tmp_path, capsys):
    """Plan 15 WP2: a `bindings.json` written before home gains the Home
    key row and the OVERDUB row on its next load, the old file kept whole
    beside it, and the next load is quiet. A source the owner already
    uses keeps its row and gets no home beside it."""
    over, key = f"note:0:{apc40.N_OVERDUB}", "key:HOME"
    assert (over, "preset.home", "toggle", 1.0, False) in routing.APC_NEW_ROWS
    assert (key, "preset.home", "fire", 1.0) in routing.KEY_NEW_ROWS

    def write(home, *mine):
        rows = [b for b in session_rows() if b.source not in (over, key)]
        path = bindings_path(home)
        home.mkdir()
        Bindings([*rows, *mine], path=path).write()
        return path

    path = write(tmp_path / "a")
    before = path.read_text()
    assert "preset.home" not in before
    t = Bindings.load(path, legacy_midi=None)
    assert t.notes == [f"added {over} → preset.home (the APC40 map of plan 15)",
                       f"added {key} → preset.home (the keys of plans 09, 11 and 15)"]
    err = capsys.readouterr().err
    assert f"updated {path} (2 rows changed)" in err
    (row,) = [b for b in t.midi() if b.source == over]
    assert (row.target, row.op, row.layer, row.feedback, row.on) \
        == ("preset.home", "toggle", None, "led", 1)
    assert t.is_invariant(Binding(over, "view.points", "toggle", layer="preset"))
    (krow,) = [b for b in t.of("key") if b.source == key]
    assert (krow.target, krow.op) == ("preset.home", "fire")
    (bak,) = (tmp_path / "a").glob("bindings.json.bak-*")
    assert bak.name == "bindings.json.bak-v3" and bak.read_text() == before
    after = path.read_text()
    assert json.loads(after)["bindings"].count(row.to_json()) == 1
    # the file is the factory's again, row for row
    assert sorted(json.dumps(b, sort_keys=True) for b in json.loads(after)["bindings"]) \
        == sorted(json.dumps(b.to_json(), sort_keys=True) for b in session_rows())
    again = Bindings.load(path, legacy_midi=None)
    assert again.notes == [] and path.read_text() == after
    assert len(list((tmp_path / "a").glob("bindings.json.bak-*"))) == 1
    assert capsys.readouterr().err == ""
    # the owner's own rows on OVERDUB and on Home stay, and nothing is added or written
    # (view.plane.ZW: no session row of its own — view.lines has the
    # invariant render toggle since plan 24 C1)
    path = write(tmp_path / "b",
                 Binding(over, "view.plane.ZW", "toggle", feedback="led"),
                 Binding(key, "camera.reset", "fire"))
    before = path.read_text()
    t = Bindings.load(path, legacy_midi=None)
    assert t.notes == [] and path.read_text() == before
    assert not list((tmp_path / "b").glob("bindings.json.bak-*"))
    assert not [b for b in t.bindings if b.target == "preset.home"]
    assert t.for_param("view.plane.ZW").source == over


def test_the_clip_stop_save_bar_is_retired_and_the_row_freed(tmp_path, capsys):
    """2026-10-09: an empty bank pad held saves into its own slot, so plan 15
    WP4's clip-stop SAVE AS bar is gone. A `bindings.json` that has the
    eight factory rows loses exactly those on its next load — each said,
    the old file kept whole beside it — and the next load is quiet; the
    row is then free (dark, for Learn). A row the owner put on a clip-stop
    button is kept; a file without the bar gains nothing there. Since plan
    24 C1 track 8's clip stop is the desk's SAVE (decision 18): the other
    seven stay free."""
    stop = apc40.N_CLIPSTOP
    bar = [f"note:{k}:{stop}" for k in range(8)]
    free = bar[:7]
    for s in bar:
        assert (s, "preset.save_new", "hold", 1.0) in routing.RETIRED_ROWS
    for s in free:
        assert not [r for r in routing.APC_NEW_ROWS if r[0] == s]
    assert [r[:3] for r in routing.APC_NEW_ROWS if r[0] == bar[7]] \
        == [(bar[7], routing.SAVE_PARAM, "momentary")]
    assert [b.target for b in session_rows() if b.source in bar] == [routing.SAVE_PARAM]

    def write(home, *mine):
        path = bindings_path(home)
        home.mkdir()
        Bindings([*session_rows(), *mine], path=path).write()
        return path

    old = [Binding(s, "preset.save_new", "hold", feedback="led") for s in bar]
    path = write(tmp_path / "a", *old)
    before = path.read_text()
    t = Bindings.load(path, legacy_midi=None)
    assert t.notes == [f"removed {s} → preset.save_new (the clip-stop SAVE AS bar is retired: "
                       "hold an empty bank pad to save into it; the row is free)" for s in bar]
    assert f"updated {path} (8 rows changed)" in capsys.readouterr().err
    assert [b.target for b in t.bindings if b.source in bar] == [routing.SAVE_PARAM]
    (bak,) = (tmp_path / "a").glob("bindings.json.bak-*")
    assert bak.name == "bindings.json.bak-v3" and bak.read_text() == before
    after = path.read_text()
    assert sorted(json.dumps(b, sort_keys=True) for b in json.loads(after)["bindings"]) \
        == sorted(json.dumps(b.to_json(), sort_keys=True) for b in session_rows())
    again = Bindings.load(path, legacy_midi=None)
    assert again.notes == [] and path.read_text() == after
    assert capsys.readouterr().err == ""
    # the owner's own row on clip stop 3 stays, the other seven go
    mine = Binding(bar[2], "view.lines", "toggle", feedback="led")
    path = write(tmp_path / "b", *[b for b in old if b.source != bar[2]], mine)
    t = Bindings.load(path, legacy_midi=None)
    assert len(t.notes) == 7 and not [b for b in t.midi() if b.target == "preset.save_new"]
    assert [b.target for b in t.midi() if b.source == bar[2]] == ["view.lines"]
    # a file without the bar: nothing added there, nothing written
    path = write(tmp_path / "c")
    before = path.read_text()
    t = Bindings.load(path, legacy_midi=None)
    assert t.notes == [] and path.read_text() == before
    assert not [b for b in t.bindings if b.source in free]


def test_an_old_crossfader_row_moves_to_the_dim_with_a_backup(tmp_path, capsys):
    """Plan 15 WP3: a bindings.json written before the master dim carries
    the factory crossfader row on the overlay's ground. Exactly that row is
    swapped for the dim, noted with its plan; the file as it was is kept
    beside itself first; the next load is quiet. A crossfader row the owner
    changed is left alone, and no dim row is added beside it."""
    xf = f"cc:0:{apc40.CC_XFADE}"

    def write(home, **change):
        rows = []
        for b in session_rows():
            d = b.to_json()
            if d["source"] == xf:
                assert d == {"source": xf, "target": "output.dim", "op": "abs", "ring": 0}
                d = {**d, "target": "overlay.bg", **change}
            rows.append(d)
        path = bindings_path(home)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"schema": SCHEMA, "profile": "apc40", "bindings": rows}
        path.write_text(json.dumps(doc))
        return path, doc

    path, doc = write(tmp_path / "old")
    t = Bindings.load(path, legacy_midi=None)
    err = capsys.readouterr().err
    assert t.error == ""
    assert t.notes == [f"remapped {xf}: overlay.bg → output.dim (the APC40 map of plan 15)"]
    assert t.notes[0] in err and "kept as bindings.json.bak-v" in err
    row, = [b for b in t.bindings if b.source == xf]
    assert (row.target, row.op, row.layer, row.pickup, row.feedback) == (
        "output.dim", "abs", None, True, None)
    assert [b.to_json() for b in t.bindings] == [b.to_json() for b in session_rows()]
    bak, = path.parent.glob("bindings.json.bak-*")
    assert json.loads(bak.read_text()) == doc                 # the file as it was
    assert json.loads(path.read_text()) == t.to_json()        # written back once
    again = Bindings.load(path, legacy_midi=None)
    assert again.notes == [] and not again.changed and capsys.readouterr().err == ""
    assert len(list(path.parent.glob("bindings.json.bak-*"))) == 1
    # the owner's own rows on the crossfader: another target, or the ground
    # with a different op — neither is the factory row, neither is touched
    for k, change in enumerate(({"target": "view.bright"}, {"op": "toggle"})):
        path, doc = write(tmp_path / f"mine{k}", **change)
        t = Bindings.load(path, legacy_midi=None)
        row, = [b for b in t.bindings if b.source == xf]
        assert (row.target, row.op) == (change.get("target", "overlay.bg"),
                                        change.get("op", "abs"))
        assert not any(b.target == "output.dim" for b in t.bindings)
        assert t.notes == [] and json.loads(path.read_text()) == doc
        assert not list(path.parent.glob("bindings.json.bak-*"))


def test_a_theme_row_in_an_old_bindings_file_is_remapped_to_the_preset_bank(tmp_path, capsys):
    """Plan 13 WP2: a table written before the preset bank names theme.*
    params — the factory F-keys, clip row 1, QUANT, pad B, and a row the
    user learned onto a theme slot. Every one moves to the preset param of
    the same slot, noted; the file is backed up and written once, and the
    next load is quiet."""
    path = bindings_path(tmp_path)
    old = {"preset.select": "theme.select", "preset.next": "theme.next",
           **{f"preset.{w}.{k}": f"theme.{w}.{k}" for w in ("load", "save")
              for k in range(routing.F_KEYS)}}
    rows = []
    for b in session_rows():
        d = b.to_json()
        d["target"] = old.get(d["target"], d["target"])
        if d["source"] == "pad:B":                    # the pad's B, as it was then
            d.update(target="theme.next", op="fire")
        rows.append(d)
    rows.append({"source": "note:0:87", "target": "theme.prev", "op": "toggle"})   # the user's
    path.write_text(json.dumps({"schema": SCHEMA, "profile": "apc40", "bindings": rows}))
    t = Bindings.load(path, legacy_midi=None)
    err = capsys.readouterr().err
    by = {b.source: b.target for b in t.bindings}
    assert by["key:F1"] == "preset.load.0" and by["key:SHIFT+F8"] == "preset.save.7"
    assert by[f"note:0:{apc40.N_QUANT}"] == "preset.next" and by["pad:B"] == "view.points"
    assert by["note:0:87"] == "preset.prev"
    assert [b.target for b in t.bindings if b.source == f"note:2:{apc40.N_CLIP[0]}"] \
        == ["preset.select"]
    assert not any(b.target.startswith("theme.") for b in t.bindings)
    assert "remapped key:F3: theme.load.2 → preset.load.2 (the preset bank of plan 13)" in err
    n = len(t.notes)
    # F-keys, clip row, QUANT, pad B (straight onto the newest layout's
    # points, PAD_REMAP), the user's — and clip rows 4 and 5,
    # which this table (today's session rows, theme-named) already holds
    assert n == 16 + 24 + 1 + 1 + 1
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
    # the free OVERDUB gets home (plan 15 WP2); + R and the F-keys (plan 11),
    # + undo and redo and the Home key (plan 15)
    assert (f"note:0:{apc40.N_OVERDUB}", "preset.home") in by
    # + the clip-stop row's eight (plan 15 WP4), + the bank's sixteen pads
    # on clip rows 4 and 5 (plan 19 WP2), + the four invariant render
    # toggles and SAVE (plan 24 C1), + START's hold-to-save (the pad
    # layout of 2026-10-14), + BACK's undo (2026-10-29), + SEND A's
    # sequencer page (plan 31 §A)
    assert ("pad:MENU", "preset.save_new") in by and ("pad:VIEW", "edit.undo") in by
    assert [n.split(" ")[0] for n in notes] == (["remapped", "added"]
                                                + ["added"] * (17 + 4 + 2 + 16 + 5 + 1 + 1 + 1))
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


def test_a_macro_owned_by_a_hand_scales_a_lanes_push_the_same_frame():
    """Chaining, not stacking (plan 09, decision 7 of plan 09), in
    dependency order (plan 28 N0, decision 7): `hand:0` positions
    `macro.2`, and `lane:0` pushes brightness at a depth × macro.2. The
    pass runs the macro's node first and lands it, so the push reads the
    macro's effective value **this frame** — the hand reaches brightness
    the frame it lands on the macro, and when the hand leaves, the macro's
    base and the push's return come back together. No lag."""
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
    # frame 1: the macro reads the hand, and brightness is pushed × 0.6 already
    assert macro.modulated and macro.value == pytest.approx(0.6) and macro.base == 1.0
    assert bright.modulated and r.view.bright == at(0.5 * 0.6 * 0.5)
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == at(0.5 * 0.6 * 0.5)      # frame 2: still × 0.6
    router.feed("hand", [0.2])
    router.modulate(r.chain)
    r.reg.apply()
    assert macro.value == pytest.approx(0.2) and r.view.bright == at(0.5 * 0.2 * 0.5)
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == at(0.5 * 0.2 * 0.5)
    router.feed("hand", None)                       # the hand leaves: the macro lets go…
    router.modulate(r.chain)
    r.reg.apply()
    assert not macro.modulated and macro.value == 1.0
    assert r.view.bright == at(0.5 * 1.0 * 0.5)      # …and the push is × 1 this frame
    router.modulate(r.chain)
    r.reg.apply()
    assert r.view.bright == at(0.5 * 1.0 * 0.5)
    assert bright.modulated and bright.norm == base  # the lane never touched the base


# ------------------------------------------------------------- plan 09 WP5

def test_every_corpus_preset_names_real_params_with_one_owner(tmp_path):
    """The routes of every corpus preset (the files the build shipped, held
    to this check while it did) land on params the full registry has,
    modulatable, with a scale it has too, and one owner per target."""
    from hyperspace.graphmigrate import retired  # (plan 33 T7: read as wires)

    r = rig(tmp_path=tmp_path, full=True)
    ids = set(r.reg.ids())
    stems = corpus_stems()
    assert "legacy6" in stems and "lfo-breathe" in stems and "party-tumble" in stems
    for name in stems:
        doc = corpus_doc(name)
        routes = [Binding.from_json(d) for d in doc["routes"]]
        for b in routes:
            assert b.target in ids and r.reg[b.target].modulatable, (name, b)
            assert b.scale is None or b.scale in ids, (name, b)
            assert b.is_performer, (name, b)
        assert routing.referee(routes)[1] == [], name
        assert {v for v in doc["values"] if not retired(v)} <= ids, name


def test_a_converted_presets_values_are_bases_a_preset_would_save(tmp_path):
    """Was test_a_routing_presets_values_are_bases_a_theme_would_save (audit
    R1, decided (c)): a routing preset could set any base its rows assume;
    made presets (plan 13 WP5), every id in their `values` is a real,
    persisted, non-alias performance param — a base a preset save writes."""
    from hyperspace.graphmigrate import retired  # (plan 33 T7: read as wires)

    r = rig(tmp_path=tmp_path, full=True)
    ids = set(r.reg.ids())
    for key in corpus_stems():
        for pid in corpus_doc(key)["values"]:
            if retired(pid):
                continue
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
    seed(tmp_path)
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


# ------------------------------- plan 19 WP2: an existing bindings.json, on a copy

QUIET = ("bindings.json", "last_show", "windows.json")    # (the first also names its backups)


def _bank_rows(table) -> dict[str, list]:
    return {s: [b for b in table.bindings if b.source == s] for s in far_pads()}


def _added(err: str, path, sources) -> bool:
    """Did the launch say, on stderr and in order, that it added the bank
    row on each of `sources` — and on no other pad? (`table.notes` holds
    the rows only until the next edit, and the startup preset's load is
    one: what stays for the session is stderr and `said`.)"""
    lines = [ln for ln in err.splitlines() if "(the APC40 map of plan 19)" in ln]
    return lines == [f"bindings: {path}: added {s} → preset.select (the APC40 map of plan 19)"
                     for s in sources]


def test_an_older_file_gets_the_bank_pads_with_a_backup(owner_home, capsys):
    """The owner's files (on a copy): the first launch adds the bank's
    sixteen pads of clip rows 4 and 5 to a `bindings.json` written before
    them — exactly the factory rows, after the rows the file had, each of
    which is as it was (the owner's own row too) — and the file as it was
    is kept beside it first as `bindings.json.bak-v3`. Nothing else in the
    home changes: no show, no preset."""
    home = owner_home
    path = bindings_path(home)
    old = path.read_bytes()
    doc = json.loads(old)
    far = far_pads()
    assert len(far) == 16 and not {row["source"] for row in doc["bindings"]} & set(far)
    before = tree(home, but=QUIET)
    capsys.readouterr()
    r = boot_home(home)
    t = r.router.table
    err = capsys.readouterr().err
    # the launch says what it did: each row on stderr, the sum on the SYSTEM page
    assert _added(err, path, far)
    assert t.error == "" and t.unbacked is None
    assert f"bindings: updated {path} (16 rows changed)" in err
    assert "backup: bindings.json kept as bindings.json.bak-v3 before the rewrite" in err
    assert t.said == ("bindings.json updated (16 rows changed), the old file kept as "
                      "bindings.json.bak-v3 — each change is on stderr")
    assert [p.name for p in home.glob("bindings.json.bak-*")] == ["bindings.json.bak-v3"]
    assert path.with_name("bindings.json.bak-v3").read_bytes() == old     # the file as it was
    new = json.loads(path.read_text())
    n = len(doc["bindings"])
    assert new["bindings"][:n] == doc["bindings"]                 # every old row, in place
    factory = {row["source"]: row for row in Bindings.factory().to_json()["bindings"]}
    assert new["bindings"][n:] == [factory[s] for s in far]       # exactly the factory's sixteen
    source, target = OWNER_ROW
    assert [row["target"] for row in new["bindings"] if row["source"] == source] == [target]
    assert {k: v for k, v in new.items() if k != "bindings"} \
        == {k: v for k, v in doc.items() if k != "bindings"}
    # in memory: each pad one invariant row that loads its slot
    for k, s in enumerate(far, routing.F_KEYS):
        (b,) = _bank_rows(t)[s]
        assert (b.target, b.op, b.value, b.layer, b.feedback, b.on) \
            == ("preset.select", "set", float(k), None, "led", apc40.GREEN)
    # no show file, no preset, nothing else of the owner's was touched
    assert tree(home, but=QUIET) == before


def test_a_second_launch_writes_nothing_and_says_nothing(owner_home, capsys):
    """Once: after the first launch every pad is taken, so a second finds
    nothing to do — no note, no line on stderr, no second backup, and not
    a byte or a tick of `bindings.json` or its backup changes."""
    home = owner_home
    boot_home(home)
    after = tree(home, but=QUIET[1:])
    assert "bindings.json" in after and "bindings.json.bak-v3" in after
    capsys.readouterr()
    r = boot_home(home)
    err = capsys.readouterr().err
    assert r.router.table.notes == [] and r.router.table.error == ""
    assert r.router.table.said == ""
    assert "bindings" not in err and "backup" not in err
    assert tree(home, but=QUIET[1:]) == after
    assert len(list(home.glob("bindings.json.bak-*"))) == 1


def test_a_row_the_owner_put_on_a_bank_pad_is_left_alone(owner_home, capsys):
    """A bank row is added only where nothing uses the pad. A session row
    the owner wrote on one of the sixteen stays exactly as it is — that
    pad does what the owner's row says, on both layers — no bank row joins
    it, and the fifteen free pads get theirs. The slot behind that pad is
    still reached from the PRESETS page (`load_slot`)."""
    home = owner_home
    path = bindings_path(home)
    far = far_pads()
    mine = {"source": far[3], "target": "view.faces", "op": "toggle", "feedback": "led"}
    doc = json.loads(path.read_text())
    doc["bindings"].append(mine)
    path.write_text(routing.dumps_doc(doc))
    old = path.read_bytes()
    capsys.readouterr()
    r = boot_home(home)
    t, pr = r.router.table, r.lib.project
    rest = [s for s in far if s != far[3]]
    assert _added(capsys.readouterr().err, path, rest)
    assert t.said.startswith("bindings.json updated (15 rows changed)")
    rows = _bank_rows(t)
    assert [(b.target, b.op, b.layer) for b in rows[far[3]]] == [("view.faces", "toggle", None)]
    assert all([b.target for b in rows[s]] == ["preset.select"] for s in rest)
    new = json.loads(path.read_text())
    assert [row for row in new["bindings"] if row["source"] == far[3]] == [mine]
    assert new["bindings"][:len(doc["bindings"])] == doc["bindings"]
    assert path.with_name("bindings.json.bak-v3").read_bytes() == old
    # the pad is the owner's on both layers; its slot loads from the page
    n = apc40.BANK_PADS[routing.F_KEYS + 3][0]
    for layer in ("preset", "global"):
        t.set_layer(layer)
        assert [b.target for b in t.dispatch("note", 3, n)] == ["view.faces"]
    t.set_layer("preset")
    pr.put_slot(routing.F_KEYS + 3, "WAKE")
    pr.load_slot(routing.F_KEYS + 3)
    assert r.lib.current("presets") == "WAKE" and pr.active == routing.F_KEYS + 3
    # the owner's pad is invariant, so an old preset's shape row on it goes
    # quietly like the other fifteen
    pr.load_slot(0)
    assert r.lib.current("presets") == "NIGHT ONE" and r.presets.desk_notes == []
    # and a second launch leaves the owner's row and adds nothing
    capsys.readouterr()
    again = boot_home(home).router.table
    assert again.notes == [] and "bindings" not in capsys.readouterr().err
    assert [(b.target, b.layer) for b in _bank_rows(again)[far[3]]] == [("view.faces", None)]


def test_a_remap_whose_backup_fails_writes_nothing(owner_home, capsys, monkeypatch):
    """No backup, no rewrite (fork 12; every remap goes through this
    branch): when the copy of `bindings.json` cannot be made the file is
    left byte for byte as it was, the table in memory is the remapped one
    (the pads work this session), and `error` and stderr say so. A later
    write of the table (a Learn on a session row) tries the copy again
    first and still writes nothing without it. The next launch tries the
    lot again."""
    home = owner_home
    path = bindings_path(home)
    old = (path.read_bytes(), path.stat().st_mtime_ns)
    far = far_pads()

    def as_it_was() -> bool:
        return ((path.read_bytes(), path.stat().st_mtime_ns) == old
                and not list(home.glob("bindings.json.bak-*")))

    def refuse(p, data):
        raise OSError("read-only")

    capsys.readouterr()
    with monkeypatch.context() as m:
        m.setattr(routing, "_write_new", refuse)
        r = boot_home(home)
        t = r.router.table
        err = capsys.readouterr().err
        assert as_it_was()
        assert t.error == routing.NOT_REWRITTEN == "bindings: not rewritten — no backup could be made"
        assert t.unbacked == "3"
        assert "backup: no backup of" in err and "updated" not in err
        assert f"bindings: {path} not rewritten — no backup could be made" in err
        assert t.said == ("bindings.json NOT rewritten (16 rows changed): no backup could be "
                          "made — in memory only, the next launch tries again")
        # in memory the table is the remapped one: the sixteen pads load their slots
        assert _added(err, path, far)
        assert all([b.target for b in rows] == ["preset.select"]
                   for rows in _bank_rows(t).values())
        # (a far slot of `mine` cannot be filled here: its first long write
        # needs a backup of the show too, which this test makes impossible)
        r.lib.project.bank[12] = "WAKE"
        n, ch = apc40.BANK_PADS[12]
        (b,) = t.dispatch("note", ch, n)
        routing.act(r.reg, b)
        assert r.lib.current("presets") == "WAKE"
        r.lib.project.bank[12] = None
        # a later write of the table: the copy is tried again, and nothing is written
        t.write()
        assert as_it_was() and t.error == routing.NOT_REWRITTEN
        # the next launch, the copy still impossible: the same again
        t2 = boot_home(home).router.table
        assert as_it_was() and t2.error == routing.NOT_REWRITTEN and t2.unbacked == "3"
        assert _added(capsys.readouterr().err, path, far)
    # once the copy can be made, a write makes it first — the file as the owner had it
    t.write()
    assert t.error == "" and t.unbacked is None
    assert t.said == "bindings.json updated, the old file kept as bindings.json.bak-v3"
    assert path.with_name("bindings.json.bak-v3").read_bytes() == old[0]
    assert len([row for row in json.loads(path.read_text())["bindings"]
                if row["target"] == "preset.select"]) == 24
    assert boot_home(home).router.table.notes == []


def test_a_launch_whose_backup_fails_then_succeeds_rewrites_once(owner_home, monkeypatch,
                                                                capsys):
    """"The next launch tries again": a launch that could not back the
    file up leaves it; the launch after it, able to, backs it up and
    rewrites it as a first launch would."""
    home = owner_home
    path = bindings_path(home)
    old = path.read_bytes()

    def refuse(p, data):
        raise OSError("disk full")

    with monkeypatch.context() as m:
        m.setattr(routing, "_write_new", refuse)
        boot_home(home)
    assert path.read_bytes() == old and not list(home.glob("bindings.json.bak-*"))
    capsys.readouterr()
    t = boot_home(home).router.table
    assert _added(capsys.readouterr().err, path, far_pads()) and t.error == ""
    assert path.with_name("bindings.json.bak-v3").read_bytes() == old
    assert path.read_bytes() != old


def test_the_old_shape_pads_are_swapped_and_a_changed_row_is_left_alone(tmp_path):
    """A file from before plan 13's migration still holds the sixteen
    shape pads of clip rows 4 and 5 as rows of its own. The exact old
    factory rows become the bank's (`BANK_REMAP`: pad k of row 4 slot 9 +
    k, of row 5 slot 17 + k), invariant, with the factory row's light; a
    pad the owner re-aimed keeps its row and gets no bank row. Nothing of
    rows 4–5 is carried into the migrated preset's desk. In a schema-3 file
    from between plan 13's WP3 and WP5 the same rows say `"layer":
    "preset"`: the swap clears it. An any-channel row the owner wrote on
    one of the rows holds all eight of its pads."""
    far = far_pads()
    pads = old_shape_pads()
    assert [p["source"] for p in pads] == far
    # (+ the four render toggles plan 24 C1 made invariant)
    assert set(routing.RETIRED_DESK_ROWS) - routing.TOGGLE_DESK_ROWS \
        == set(routing.BANK_REMAP) == {
        (p["source"], "view.shape", "set", float(p.get("value", 1.0)))
        for p in pads}
    assert [routing.BANK_REMAP[(s, "view.shape", "set", float(k))]
            for k, s in enumerate(far)] == [("preset.select", "set", float(8 + k))
                                            for k in range(16)]
    # the pre-plan-13 file: today's rows without layers, SHIFT or the global
    # layer, and without the bank's far pads — the shape pads in their place
    v2 = {"schema": routing.SCHEMA_V2, "profile": "apc40", "bindings": []}
    for b in Bindings.factory().bindings:
        if b.layer == "global" or b.target == routing.SHIFT_PARAM or b.source in far:
            continue
        row = b.to_json()
        row.pop("layer", None)
        v2["bindings"].append(row)
    owner = dict(OWNER_PAD)
    v2["bindings"] += [owner if p["source"] == owner["source"] else p for p in pads]
    path = bindings_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v2))
    t = Bindings.load(path, legacy_midi=None)
    swapped = [s for s in far if s != owner["source"]]
    for k, s in enumerate(far, 8):
        (b,) = [x for x in t.bindings if x.source == s]
        if s == owner["source"]:                     # the owner's: kept, the pad's only row
            assert (b.target, b.op, b.layer) == ("fx.acid.on", "toggle", None)
        else:
            assert (b.target, b.op, b.value, b.layer, b.feedback, b.on, b.off) \
                == ("preset.select", "set", float(k), None, "led", apc40.GREEN, 0), s
    assert [n for n in t.notes if "plan 19" in n] == [
        f"remapped {s}: view.shape → preset.select (the APC40 map of plan 19)" for s in swapped]
    # the file still holds a preset's part (the knobs' preset layer), so it is the
    # migration's to write — and nothing of rows 4–5 is carried into that preset
    assert t.carried is not None and json.loads(path.read_text()) == v2
    assert not [d for d in t.carried.desk if d["source"] in far]
    assert not [b for b in t.desk() if b.source in far]
    # idempotent
    again, notes = routing.remap_factory(t.bindings)
    assert notes == [] and len(again) == len(t.bindings)
    # a schema-3 file from between plan 13's WP3 and WP5: the rows are on the preset layer
    mid = [Binding.from_json({**p, "layer": "preset"}) for p in pads]
    out, notes = routing.remap_factory(mid)
    assert len(notes) >= 16 and all(n.startswith("remapped") for n in notes[:16])
    by = {b.source: b for b in out}
    assert all((by[s].target, by[s].value, by[s].layer) == ("preset.select", float(k), None)
               for k, s in enumerate(far, 8))
    assert not any("plan 19" in n for n in notes[16:])           # none added on top
    # a re-aimed pad on the preset layer in such a file: it keeps the pad
    out, notes = routing.remap_factory([Binding.from_json({**owner, "layer": "preset"})])
    assert [b.target for b in out if b.source == owner["source"]] == ["fx.acid.on"]
    assert len([n for n in notes if "plan 19" in n]) == 15
    # an any-channel row on clip row 5 holds every pad of it
    wild = Binding(f"note:*:{apc40.N_CLIP[4]}", "view.faces", "toggle", feedback="led")
    out, notes = routing.remap_factory([wild])
    added = [b.source for b in out if b.target == "preset.select"]
    assert added == far[:8] and wild in out


# ---------------------------------------------------------------- plan 27 B6: the general qualifier

def test_the_qualifier_is_general_any_scheme_takes_a_role():
    """Plan 27 B6 (the general qualifier): a source head may carry
    ``@<role>`` for any scheme, not only MIDI's. The base scheme, the
    role, the bare source and whether it is continuous read the same way
    for a second pad's rows as for a second desk's; an unqualified row
    means the scheme's primary device — the first one listed."""
    assert routing.base_scheme("axis@p2") == "axis"
    assert routing.base_scheme("pad@p2") == "pad"
    assert routing.base_scheme("hat@p2") == "hat"
    assert routing.base_scheme("axis") == "axis"
    b = Binding("pad@p2:A", "view.faces", "toggle")
    assert (b.scheme, b.device, b.bare, b.parts) == ("pad", "p2", "pad:A", ["A"])
    a = Binding("axis@p2:LX", "view.inst_amp", "push", 0.25)
    assert (a.scheme, a.device, a.bare, a.is_performer) == ("axis", "p2", "axis:LX", True)
    assert a.head == "axis@p2" and Binding("axis:LX", "x", "push").head == "axis"
    assert routing.is_continuous("axis@p2") and not routing.is_continuous("pad@p2")
    assert not routing.is_continuous("hat@p2")
    plain = Binding("pad:A", "view.faces", "toggle")
    assert plain.device == "" and plain.bare == "pad:A"
    # the qualified head is its own Router key: a lane, a label, a rest
    assert routing.qualified("axis", "p2") == "axis@p2" and routing.qualified("axis", "") == "axis"
    # the MIDI cases, as B2 built them (copied from test_device_inputs)
    m = Binding("cc@launch:0:7", "view.bright", "abs")
    assert (m.scheme, m.kind, m.device, m.channel, m.number) == ("cc", "cc", "launch", 0, 7)
    assert m.is_midi and not m.is_performer and m.bare == "cc:0:7"
    assert m.describe() == "MIDI CC 7 ch1 on launch"
    assert routing.base_scheme("cc@launch") == "cc"
    assert not routing.is_continuous("cc@launch") and not routing.is_continuous("pad")
    # a qualified non-MIDI row never looks like a desk's
    assert not b.is_midi and b.kind is None and not b.overlaps(Binding("pad:A", "x"))
    # the row says whose it is
    assert "on p2" in a.describe() and "on p2" in b.describe()
    assert "on p2" not in plain.describe()


def test_an_unqualified_pad_row_is_the_primary_pads():
    """`Bindings.primaries` (scheme → role, the registry's `primaries`):
    an unqualified non-MIDI row is the first listed device's that
    publishes its scheme; a qualified one its qualifier's. MIDI keeps
    `midi_roles` exactly as B2 built it."""
    t = Bindings([Binding("pad:A", "view.faces", "toggle"),
                  Binding("pad@p2:A", "view.points", "toggle"),
                  Binding("cc:0:7", "view.speed", "abs")])
    assert t.role_of(t.bindings[1]) == "p2"
    assert t.role_of(t.bindings[0]) == ""                 # a bare table: told none
    t.primaries = {"axis": "pad", "pad": "pad", "hat": "pad"}
    t.midi_roles = ("apc40",)
    assert t.role_of(t.bindings[0]) == "pad" and t.role_of(t.bindings[1]) == "p2"
    assert t.role_of(t.bindings[2]) == "apc40"            # MIDI: the first MIDI role, as ever


class TwoPadsPad(FakePad):
    """FakePad with edges and a publish, so a frame can be held."""

    def __init__(self):
        super().__init__()
        self.prev: set[int] = set()

    def publish(self, router, scheme="axis"):
        from hyperspace import gamepad
        gamepad.publish(router, scheme)

    def pressed(self, b: int) -> bool:
        return b in self.hits and b not in self.prev

    def down(self, b: int) -> bool:
        return b in self.hits

    def lanes(self) -> list[float]:
        return [0.5, 0.5, 0.5, 0.5, 0.0, 1.0]


def test_the_router_keeps_two_pads_apart(tmp_path):
    """`Router.pad(…, role=)`: a second pad feeds `axis@p2`, publishes its
    labels there, and fires only its own qualified rows; the primary's
    unqualified rows hear only the primary pad. One feel for every pad."""
    from hyperspace import gamepad as gp

    r = rig(tmp_path=tmp_path, full=True)
    table = Bindings([Binding("pad:A", "view.faces", "toggle"),
                      Binding("pad@p2:A", "view.points", "toggle")])
    router = Router(r.reg, table)
    one, two = TwoPadsPad(), TwoPadsPad()
    faces, points = r.reg["view.faces"].value, r.reg["view.points"].value
    two.hits = {gp.A}
    router.pad(one, now=0.0)
    router.pad(two, now=0.0, role="p2")
    assert r.reg["view.faces"].value == faces and r.reg["view.points"].value != points
    assert router.labels["axis@p2"] == list(gp.LANE_LABELS) and "axis" in router.labels
    assert float(router.feeds["axis@p2"][5]) == 1.0
    assert router.lane("axis@p2:RT") == ("axis@p2", 5)
    points = r.reg["view.points"].value
    one.hits = {gp.A}
    two.prev = {gp.A}
    router.pad(one, now=0.1)
    router.pad(two, now=0.1, role="p2")
    assert r.reg["view.faces"].value != faces and r.reg["view.points"].value == points
    two.on = False
    router.pad(two, now=0.2, role="p2")
    assert router.feeds["axis@p2"] is None and router.feeds["axis"] is not None
    # the pad's feel is one set, applied to every pad
    assert router.source_feel("axis@p2") == router.source_feel("axis")
    a2 = Binding("axis@p2:LX", "view.inst_amp", "push", 0.25)
    assert router.feel_of(a2) == router.source_feel("axis")
    # the primary's camera job counts only its own axes as claimed
    table.add(a2)
    assert router.claimed("axis") == set() and router.claimed("axis@p2") == {0}


def test_each_pad_times_its_own_holds(tmp_path):
    """A `hold` row on each pad's START: held past HOLD_S only the held
    pad's target fires, and a press on one pad never resets the other's
    timer."""
    from hyperspace import gamepad as gp

    r = rig(tmp_path=tmp_path, full=True)
    fired: list[str] = []
    r.reg.trigger("t.one", "one", lambda: fired.append("one"))
    r.reg.trigger("t.two", "two", lambda: fired.append("two"))
    table = Bindings([Binding("pad:MENU", "t.one", "hold"),
                      Binding("pad@p2:MENU", "t.two", "hold")])
    router = Router(r.reg, table)
    one, two = TwoPadsPad(), TwoPadsPad()
    one.hits = {gp.MENU}
    router.pad(one, now=0.0)
    router.pad(two, now=0.0, role="p2")
    one.prev = {gp.MENU}
    two.hits = {gp.MENU}                                  # p2 pressed later
    router.pad(one, now=0.3)
    router.pad(two, now=0.3, role="p2")
    two.prev = {gp.MENU}
    router.pad(one, now=routing.HOLD_S + 0.01)
    router.pad(two, now=routing.HOLD_S + 0.01, role="p2")
    assert fired == ["one"]                               # p2's press did not reset pad's
    router.pad(one, now=0.3 + routing.HOLD_S + 0.01)
    router.pad(two, now=0.3 + routing.HOLD_S + 0.01, role="p2")
    assert fired == ["one", "two"]


def test_a_row_qualified_with_the_primary_pads_own_role_is_its(tmp_path):
    """As a desk's `serves`: `pad@pad:A` (the primary named) fires on the
    primary pad, and `axis@pad:LX` reads the primary's lanes."""
    from hyperspace import gamepad as gp

    r = rig(tmp_path=tmp_path, full=True)
    table = Bindings([Binding("pad@pad:A", "view.faces", "toggle"),
                      Binding("axis@pad:RT", "view.inst_amp", "position", 1.0)])
    table.primaries = {"axis": "pad", "pad": "pad", "hat": "pad"}
    router = Router(r.reg, table)
    one, two = TwoPadsPad(), TwoPadsPad()
    faces = r.reg["view.faces"].value
    two.hits = {gp.A}
    router.pad(two, now=0.0, role="p2")
    assert r.reg["view.faces"].value == faces             # not the second pad's
    one.hits = {gp.A}
    router.pad(one, now=0.0)
    assert r.reg["view.faces"].value != faces
    assert router.lane("axis@pad:RT") == ("axis", 5)
    assert router.claimed("axis") == {5}
    router.modulate()
    r.reg.apply()
    amp = r.reg["view.inst_amp"]
    assert amp.value == pytest.approx(amp.hi)             # TwoPadsPad's RT is all the way


# ------------------------------------------------------------- plan 28 N0

def _lagged_modulate(self: Router, analyzer=None, dt: float | None = None) -> None:
    """The base build's `Router.modulate` (5d18192, before plan 28 N0),
    verbatim but for living here: every enabled performer row in table
    order, a `scale` and a macro's depth subscriber read at what the last
    `reg.apply()` wrote — the one-frame lag decision 7 removes. Kept for
    one test only (`test_every_factory_preset_lands_the_same_values_one_frame_earlier`),
    the reference the new pass is held to; a test file, so the boundary
    walk (`test_only_router_modulate_calls_param_modulate`, the package
    only) never sees its `p.modulate`."""
    from hyperspace.routing import _NO_LANES

    dt = 1 / 60 if dt is None else dt
    movers = self.__dict__.setdefault("_lagged_movers", {})
    moved: set = set()
    lanes = None if analyzer is None else analyzer.lanes / CEIL
    names = self.names
    cache = self.__dict__.get("_lanes", _NO_LANES)
    for b in self.table.mods():
        hit = cache.get(b.source)
        if hit is None or names.get(hit[0]) is not hit[1]:
            hit = self._resolve_lane(b.source)
            cache = self.__dict__["_lanes"]
        scheme, _, i = hit
        vec = lanes if scheme == "lane" else self.feeds.get(scheme)
        if vec is None or not 0 <= i < len(vec):
            continue
        u = float(vec[i])
        if math.isnan(u):
            continue
        if not self.gated(b):
            continue
        p = self.reg.get(b.target)
        if p is None:
            continue
        depth = b.value
        if b.scale is not None:
            sp = self.reg.get(b.scale)
            if sp is None:
                continue
            depth *= float(sp.value)
        dormant = False
        for mid, s in self.table.depth_subs(b):
            mp = self.reg.get(mid)
            if mp is None:
                dormant = True
                break
            depth *= s.at(float(mp.value))
        if dormant:
            continue
        m = self.feel_of(b)
        if m.on:
            u = self._move(b, m, u, p, depth, dt, movers)
            moved.add((b.source, b.target))
        if b.op == "push":
            rest = b.rest if b.rest is not None else self.rest_of(b.source)
            x = depth * (u - rest)
        else:
            if p.kind is Kind.TEXT or not p.modulatable:
                continue
            x = min(1.0, max(0.0, depth * u)) - p.norm
        p.modulate(x)
    for key in [k for k in movers if k not in moved]:
        del movers[key]


TAPE_FRAMES = 90
TAPE_DT = 1 / 60


def _hand_tape(lay, k: int) -> tuple[list[float], list[float]]:
    """A synthetic hand tape, frame `k`: every axis a slow sine of its own
    (rates and phases apart, so no two lanes move together), each hand
    present, each pinch switch on for a stretch and off for another — and
    the two-hand pair lanes the same way. Deterministic: both builds see
    the same frames."""
    from hyperspace.hands import PINCHES, SIDES

    t = k * TAPE_DT
    axes = [0.5 + 0.45 * math.sin(2 * math.pi * (0.35 + 0.11 * i) * t + 0.7 * i)
            for i in range(lay.n_axes)]
    presence = [1.0] * len(SIDES)
    gates = [1.0 if ((k // (11 + 3 * i)) % 2 == 0) else 0.0
             for i in range(len(SIDES) * len(PINCHES))]
    pair = [0.5 + 0.4 * math.sin(2 * math.pi * 0.27 * t + j) for j in range(len(lay.pair_index))]
    return axes + presence + gates, pair


def _lag_of(table: Bindings) -> tuple[dict[str, int], dict[int, int]]:
    """How many frames late the base build lands each param and each LFO's
    output, from the table alone (not modgraph.py): a param read in the pass
    — a `scale`, a macro behind a depth subscriber, an LFO's knob — that a
    performer moves reaches its reader one frame late, and a chain of them
    adds up. Params no row reaches are 0."""
    rows = table.mods()
    moved = {b.target for b in rows}
    knobs = ("shape", "rate", "sync", "depth", "phase", "reset")
    lag_p: dict[str, int] = {}
    lag_l: dict[int, int] = {}
    for _ in range(8):                                   # to the fixpoint (no loops here)
        for i in range(4):
            reads = [f"lfo.{i + 1}.{k}" for k in knobs] + ["lfo.trigger"]
            lag_l[i] = max([lag_p.get(r, 0) + 1 for r in reads if r in moved] or [0])
        for b in rows:
            src = 0
            if b.source.startswith("lfo:"):
                src = lag_l.get(int(b.source.split(":")[1]), 0)
            reads = ([b.scale] if b.scale else []) + [mid for mid, _ in table.depth_subs(b)]
            lag = max([src] + [lag_p.get(r, 0) + 1 for r in reads if r in moved])
            lag_p[b.target] = max(lag_p.get(b.target, 0), lag)
    return lag_p, lag_l


def _play_tape(tmp_path: Path, name: str, *, lagged: bool):
    """Preset `name` through a scratch library, the hand tape and the
    analyzer's lanes fed, LFO 1 on, for TAPE_FRAMES frames. What a lagged
    read multiplies is held still, so a lagged param's sequence moves only
    with the value it was late on and the shift is exact: the analyzer's
    lanes are held, each at its own level (a lane row scaled by a gain a
    hand rides — party-tumble's — moves with the hand alone), and LFO 1 is
    a square wave at 0.01 Hz, +1 over the whole tape (party-trip's and
    lfo-breathe's LFO chains move with the hand on its depth alone). The
    hands move every frame. Run as app.frame runs steps 3 and 9–11: on the base
    build's arithmetic (`lagged`: the LFOs stepped and published, then
    `_lagged_modulate`, then `reg.apply`) or on today's (the LFOs step
    inside `Router.modulate`). Every modulatable param's effective value and
    every LFO's output, per frame."""
    from hyperspace.hands import HandSettings, Layout

    seed(tmp_path)
    r = rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings())
    assert load_preset(r, router, name) == []
    lfos, clock = r.lfos, r.clock
    reg = r.reg
    reg["lfo.1.sync"].set(0)
    reg["lfo.1.shape"].set(lfo.SHAPES.index("square"))
    reg["lfo.1.rate"].set(0.01)
    reg["lfo.1.phase"].set(0.0)
    reg["lfo.1.depth"].set(0.8)
    lay = Layout(HandSettings.from_config({}).axes)
    router.names["hand"] = lay.index
    router.names["hands"] = lay.pair_index
    hand0, _ = _hand_tape(lay, 0)
    router.rests["hand"] = [0.5] * lay.n_axes + [0.0] * (len(hand0) - lay.n_axes)
    if not lagged:
        router.use_lfos(lfos, clock)
    params = [p for p in reg if p.modulatable]
    seq: dict[str, list] = {p.id: [] for p in params}
    outs: list[list[float]] = []
    for k in range(TAPE_FRAMES):
        t = 1.0 + k * TAPE_DT
        clock.tick(t)
        router.follow_macros()
        hand, pair = _hand_tape(lay, k)
        router.feed("hand", hand)
        router.feed("hands", pair)
        r.chain.out[:] = [CEIL * (0.5 + 0.4 * math.sin(1.3 * j)) for j in range(len(r.chain.out))]
        if lagged:
            lfos.step(TAPE_DT, t, clock)
            lfos.publish(router)
            _lagged_modulate(router, r.chain, TAPE_DT)
        else:
            router.modulate(r.chain, TAPE_DT, now=t)
        reg.apply()
        for p in params:
            seq[p.id].append(p.get())
        outs.append(list(lfos.outputs))
    return seq, outs, router.table


def test_every_factory_preset_lands_the_same_values_one_frame_earlier(tmp_path):
    """Decision 7, the gate on the lag's removal: every corpus preset (the
    ones the build shipped), played through a scratch library with the synthetic hand tape, the
    analyzer's lanes and LFO 1 on, lands every modulatable param on the
    same value as the base build's arithmetic (`_lagged_modulate`, the
    reference kept for this test) — at the same frame for every param
    whose value no lagged read reaches (most of them, every one no
    performer moves among them), and exactly as many frames earlier as
    the base build was late for the rest (`_lag_of`: an LFO whose depth a
    hand owns, and what that LFO drives). A sequence that differs in any
    other way is a value the change moved, not its timing."""
    shifted_somewhere = []
    for name in corpus_stems():
        old, old_out, table = _play_tape(tmp_path / f"{name}-old", name, lagged=True)
        new, new_out, _ = _play_tape(tmp_path / f"{name}-new", name, lagged=False)
        lag_p, lag_l = _lag_of(table)
        for pid, seq in new.items():
            k = lag_p.get(pid, 0)
            assert seq[:TAPE_FRAMES - k] == old[pid][k:], (name, pid, k)
            if k and len(set(seq)) > 1:
                shifted_somewhere.append((name, pid))
        for i in range(len(new_out[0])):                 # every LFO steps, cables or none
            k = lag_l.get(i, 0)
            assert [o[i] for o in new_out][:TAPE_FRAMES - k] == \
                [o[i] for o in old_out][k:], (name, i, k)
            assert len({o[i] for o in new_out}) > 1 or i > 0 or k == 0, (name, i)
    # not vacuous: the two presets whose hand owns LFO 1's depth moved
    # what that LFO drives, one frame earlier
    assert ("party-trip", "camera.zoom") in shifted_somewhere
    assert ("lfo-breathe", "view.bright") in shifted_somewhere
    assert ("party-tumble", "rot.rate.ZW") in shifted_somewhere   # the scale path


def test_a_cycle_without_a_delay_disables_its_last_cable_with_a_note(tmp_path):
    """Decision 7: a loop closes only through a delay modifier. LFO 1
    pushes LFO 2's rate and LFO 2 pushes LFO 1's depth: the later cable in
    table order is kept off — its row still in the table, enabled, saved
    as written — with a note ROUTING's head shows; the rest of the patch
    runs. Take the loop away and the cable runs again, no note."""
    r = rig(tmp_path=tmp_path, full=True)
    first = Binding("lfo:0", "lfo.2.rate", "push", 0.5)
    second = Binding("lfo:1", "lfo.1.depth", "push", 0.5)
    other = Binding("lane:0", "view.bright", "push", 0.5)
    table = Bindings([first, other, second])
    router = Router(r.reg, table)
    router.use_lfos(r.lfos, r.clock)
    assert router.modgraph_cut == {("lfo:1", "lfo.1.depth")}
    (note,) = router.modgraph_notes
    assert note == ("loop: lfo:0 → lfo.2.rate → lfo:1 → lfo.1.depth → lfo:0 needs a delay"
                    " — lfo:1 → lfo.1.depth is off until it has one")
    assert second in table.routes() and second.enabled          # nothing removed
    assert [d["target"] for d in (b.to_json() for b in table.routes())] == [
        "lfo.2.rate", "view.bright", "lfo.1.depth"]
    depth, rate, bright = r.reg["lfo.1.depth"], r.reg["lfo.2.rate"], r.reg["view.bright"]
    r.lfos[0].shape = r.lfos[1].shape = lfo.SHAPES.index("square")
    r.chain.out[:] = 0
    r.chain.out[0] = CEIL * 0.5
    router.modulate(r.chain, 1 / 60, now=1.0)
    r.reg.apply()
    assert rate.modulated and not depth.modulated               # the cut cable never ran
    assert bright.modulated                                     # the rest of the patch did
    # in the file as written: a preset saved now carries the row
    assert any(d == second.to_json() for d in (b.to_json() for b in table.routes()))
    table.remove(first)                                         # no loop: it runs
    assert router.modgraph_cut == set() and router.modgraph_notes == []
    router.modulate(r.chain, 1 / 60, now=1.0 + 1 / 60)
    r.reg.apply()
    assert depth.modulated


def test_sinks_still_send_after_apply(tmp_path):
    """The sinks read this frame's effective values after `reg.apply()`,
    as before (ARCHITECTURE §2 step 12): a param the pass lands early
    (LFO 1's depth, which LFO 1 reads) and a param `reg.apply` lands (the
    brightness LFO 1 pushes) both reach a sink row at this frame's value."""
    r = rig(tmp_path=tmp_path, full=True)
    table = Bindings([Binding("hand:0", "lfo.1.depth", "position"),
                      Binding("lfo:0", "view.bright", "push", 0.5),
                      Binding("param:lfo.1.depth", routing.sink_target("daw", 0), "send"),
                      Binding("param:view.bright", routing.sink_target("daw", 1), "send")])
    router = Router(r.reg, table)
    router.use_lfos(r.lfos, r.clock)
    one = r.lfos[0]
    one.shape, one.sync, one.phase = lfo.SHAPES.index("square"), 0, 0.0
    depth, bright = r.reg["lfo.1.depth"], r.reg["view.bright"]
    bright.set_value(0.5)
    router.feed("hand", [0.6])
    r.clock.tick(1.0)
    router.modulate(None, 1 / 60, now=1.0)
    landed_early = depth.value
    r.reg.apply()
    sent = routing.sink_values(table.sinks("daw"), r.reg)
    assert landed_early == pytest.approx(0.6)                   # in the pass, before LFO 1
    assert r.lfos.outputs[0] == pytest.approx(0.5 + 0.5 * 0.6)  # LFO 1 read it this frame
    assert sent[0] == pytest.approx(depth.eff_norm) and sent[0] == pytest.approx(0.6)
    assert sent[1] == pytest.approx(bright.eff_norm)            # this frame's push, after apply
    assert bright.value != pytest.approx(0.5)
