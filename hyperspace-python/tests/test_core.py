"""Plan-01 checks.

Geometry: exact parity against the golden traces — construction (V/E) to
float64 precision, projection to float32-storage precision.

Audio: behavioural checks, per the relaxed bar — the chain must exhibit the
documented behaviours (gate, dynamics recovery, headroom discipline), not
match the reference frame-by-frame. Final judge of the audio feel is the
user, by eye, in plan 02+.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import bands, geometry
from hyperspace.offline import run_wav

ROOT = Path(__file__).parent.parent
GOLDEN = Path(__file__).parent / "golden"
FIXTURES = Path(__file__).parent / "fixtures"

GEOMETRY_TRACES = sorted((GOLDEN / "geometry").glob("*.json"))


# ---------------------------------------------------------------- geometry

@pytest.mark.parametrize("path", GEOMETRY_TRACES, ids=lambda p: p.stem)
def test_construction_exact(path):
    ref = json.loads(path.read_text())
    g = geometry.geom(ref["index"])
    assert g["n"] == ref["n"] and g["m"] == ref["m"]
    V_ref = np.asarray(ref["V"]).reshape(-1, 4)
    np.testing.assert_allclose(g["V"], V_ref, rtol=0, atol=1e-12)
    E_ref = np.asarray(ref["E"], dtype=np.int32).reshape(-1, 2)
    np.testing.assert_array_equal(g["E"], E_ref)


@pytest.mark.parametrize("path", GEOMETRY_TRACES, ids=lambda p: p.stem)
def test_projection_matches(path):
    ref = json.loads(path.read_text())
    g = geometry.geom(ref["index"])
    w, h = ref["viewport"]["width"], ref["viewport"]["height"]
    for view in ref["views"]:
        px, py, pd = geometry.project(g["V"], view["ang"], view["yaw"], view["pitch"], w=w, h=h)
        # golden values passed through Float32Array — compare at that precision
        np.testing.assert_allclose(px, np.asarray(view["px"]), rtol=0, atol=1e-3)
        np.testing.assert_allclose(py, np.asarray(view["py"]), rtol=0, atol=1e-3)
        np.testing.assert_allclose(pd, np.asarray(view["pd"]), rtol=0, atol=1e-6)


# -------------------------------------------------------------- unit props

def test_soft_ceil_properties():
    xs = np.linspace(0, 30, 4000)
    ys = np.array([bands.soft_ceil(x, bands.KNEE, bands.CEIL) for x in xs])
    below = xs <= bands.KNEE
    np.testing.assert_array_equal(ys[below], xs[below])  # identity below the knee
    assert np.all(np.diff(ys) > 0), "must be strictly increasing"
    assert ys.max() < bands.CEIL, "asymptote is never reached"


def test_presets_load():
    from hyperspace.analysis import Analyser

    chain = bands.Chain(Analyser())
    for k in range(len(bands.PRESETS)):
        chain.apply_preset(k)
        for p in chain.params:
            assert 0 <= p.fn < len(bands.SHAPERS)
            assert p.atk > 0 and p.dec > 0
    assert len(bands.PRESETS) == 11


# ------------------------------------------------------ chain behaviours

@pytest.fixture(scope="module")
def fixture_wavs():
    if not (FIXTURES / "gate-prover.wav").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "gen_test_audio.py"), "--out", str(FIXTURES)],
            check=True,
        )
    return FIXTURES


def settled(x: np.ndarray, t: np.ndarray) -> np.ndarray:
    return x[t >= 2.0]


def test_gate_prover_behaviour(fixture_wavs):
    """The defining proof: driven bands move, empty bands sit at exactly zero."""
    r = run_wav(fixture_wavs / "gate-prover.wav")
    out = settled(r["out"], r["t"])
    assert out[:, 0].mean() > 0.5, "SUB must be driven by the 50 Hz tone"
    assert out[:, 4].mean() > 0.2, "UPR must be driven by the 3 kHz tone"
    for i, name in ((2, "MIDB"), (3, "MID"), (5, "AIR")):
        assert np.all(out[:, i] == 0.0), f"{name} must gate to exactly zero"
    # gated bands leave their planes at the +1 idle drive? No — a gated band
    # drives 0; the plane stops. That is the documented contract.
    drive = settled(r["drive"], r["t"])
    for i in (2, 3, 5):
        plane = bands.BANDS[i].plane
        assert np.all(drive[:, plane] == 0.0)


def test_dynamics_recovery(fixture_wavs):
    """dyn=1 must show more output variation than dyn=0, band by band.

    Run at 120 fps — the cadence the golden traces were recorded at; the
    analyser's per-call smoothing makes spread cadence-sensitive (measured:
    BASS sd 0.167@60fps vs 0.234@120fps against reference 0.235). Thresholds
    are ones the reference itself satisfies on this fixture.
    """
    r1 = run_wav(fixture_wavs / "brickwalled.wav", fps=120, dyn=1.0)
    r0 = run_wav(fixture_wavs / "brickwalled.wav", fps=120, dyn=0.0)
    sd1 = settled(r1["out"], r1["t"]).std(axis=0)
    sd0 = settled(r0["out"], r0["t"]).std(axis=0)
    for i, band in enumerate(bands.BANDS):
        assert sd1[i] > sd0[i] * 1.05, f"{band.id}: sd {sd1[i]:.3f} vs {sd0[i]:.3f}"


def test_dynamics_spread_matches_reference(fixture_wavs):
    """Settled per-band sd within 0.08 of the reference trace, both dyn
    settings, at matched cadence — strong evidence of a faithful port
    without brittle frame-level comparison."""
    for trace, dyn in (("brickwalled-default.jsonl", 1.0), ("brickwalled-dyn0.jsonl", 0.0)):
        rows = np.asarray(
            [json.loads(line) for line in (GOLDEN / "audio" / trace).read_text().splitlines()]
        )
        ref_sd = rows[rows[:, 1] >= 2.0][:, 8:14].std(axis=0)
        r = run_wav(fixture_wavs / "brickwalled.wav", fps=120, dyn=dyn)
        our_sd = settled(r["out"], r["t"]).std(axis=0)
        for i, band in enumerate(bands.BANDS):
            assert abs(our_sd[i] - ref_sd[i]) < 0.08, (
                f"{trace} {band.id}: sd {our_sd[i]:.3f} vs reference {ref_sd[i]:.3f}"
            )


def test_headroom_discipline(fixture_wavs):
    """No NaNs, nothing at or above the asymptote, warm-up doesn't pin."""
    for clip in ("gate-prover.wav", "brickwalled.wav", "sweep.wav"):
        r = run_wav(FIXTURES / clip)
        for key in ("inp", "out"):
            arr = r[key]
            assert np.all(np.isfinite(arr)), f"{clip}:{key} has non-finite values"
            assert arr.max() < bands.CEIL, f"{clip}:{key} touched the asymptote"


def test_golden_coarse_agreement(fixture_wavs):
    """Loose cross-check against the reference trace: same bands active on
    gate-prover, settled means in the same neighbourhood. Not frame parity —
    that bar was dropped deliberately (see plan 01 Results)."""
    trace_path = GOLDEN / "audio" / "gate-prover-default.jsonl"
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    ref = np.asarray(rows)
    ref_out = ref[ref[:, 1] >= 2.0][:, 8:14]  # settled, out channels
    ours = settled(run_wav(FIXTURES / "gate-prover.wav")["out"], run_wav(FIXTURES / "gate-prover.wav")["t"])
    for i in range(6):
        ref_m, our_m = ref_out[:, i].mean(), ours[:, i].mean()
        if ref_m == 0.0:
            assert our_m == 0.0, f"band {i}: reference gated, ours did not"
        else:
            assert abs(our_m - ref_m) < 0.30, f"band {i}: mean {our_m:.3f} vs reference {ref_m:.3f}"
