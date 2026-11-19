"""Plan 63: the Mandelbrot effect (`shaders/fx/mandel.glsl`) and its Python
half (`hyperspace/mandel.py`).

The maths first, on the CPU against a float64 numpy oracle (`escape_counts`
with no periodicity check is the oracle): the smooth escape count, the
periodicity check and the cardioid test, the binomial expansion of the
perturbation recurrence, the reference orbit, the rebase, and the tile
border-fill rule. Then the drives and the reference's lifetime. Then the
shader, on Mesa, against its numpy float32 twin — the GPU and numpy at the
same precision should agree, and how far float32 sits from float64 is
measured on numpy alone. Frame times mean nothing here: `tools/mandel_bench.py`
is the rig's.
"""

import math

import numpy as np
import pytest

from hyperspace import mandel as M
from hyperspace.fx import FxChain, FxState, SpecError, parse

SEAHORSE = complex(-0.743643887037151, 0.131825904205330)
W, H = 64, 48


def values(**kw) -> dict:
    """The effect's defaults as FxState holds them, with `kw` over them."""
    v = dict(FxState().values["mandel"])
    v.update(kw)
    return v


def counts(n, inside) -> np.ndarray:
    return np.where(inside, -1.0, n)


def mismatch(a, b) -> float:
    """The share of pixels whose counts differ by more than one step."""
    return float(np.mean(np.abs(a - b) > 1.0))


# ---------------------------------------------------------------- the maths

def test_the_oracle_counts_known_points():
    c = np.array([0, -1, -2, 0.25, 1, 0.5j * 3, -0.75 + 0.1j])
    n, inside = M.escape_counts(c, 0, 2, 200)
    assert list(inside) == [True, True, True, True, False, False, False]
    # c = 1: 0, 1, 2, 5, 26, 677 — past |z|² > 10⁴ at the fifth step (n = 4), so
    # the smooth count is 4 + 1 − log₂ log 677
    assert n[4] == pytest.approx(5 - math.log2(math.log(677)))


def test_the_smooth_count_is_continuous_where_the_whole_count_steps():
    """Along a ray out of the set the whole step count jumps by one at a time;
    n + 1 − log₂ log|z| crosses each jump without one."""
    c = np.linspace(0.26, 0.6, 4000).astype(np.complex128)
    n, inside = M.escape_counts(c, 0, 2, 1000)
    assert not inside.any()
    assert np.all(np.abs(np.diff(n)) < 0.5)
    assert n[0] > n[-1] + 10                  # and it falls away from the set


@pytest.mark.parametrize("p", [2, 3, 5, 8])
def test_the_smooth_count_holds_for_every_power(p):
    c = np.linspace(1.0, 1.6, 2000).astype(np.complex128) * np.exp(0.3j)
    n, inside = M.escape_counts(c, 0, p, 500)
    assert not inside.any() and np.all(np.abs(np.diff(n)) < 0.5)


def test_periodicity_stops_the_inside_early_and_agrees_with_the_oracle():
    v = values()
    q = complex(v["centre_x"], v["centre_y"]) + M.offsets(96, 64, 1.0)
    pix = M.view_height(1.0) / 64
    n0, in0 = M.escape_counts(q, 0, 2, 1000)
    n1, in1 = M.escape_counts(q, 0, 2, 1000, periodic_eps=pix * M.PERIOD_EPS)
    assert np.mean(in0 != in1) < 0.002
    assert np.median(n1[in1]) < 200           # the inside settles long before the cap
    assert np.array_equal(n0[~in0], n1[~in0])  # and an escape counts the same


def test_the_cardioid_test_never_calls_an_outside_point_inside():
    q = M.offsets(400, 300, 1.0) - 0.5
    held = M.in_cardioid(q)
    _, inside = M.escape_counts(q, 0, 2, 2000)
    assert held.sum() > 0.4 * inside.sum()    # it takes most of the set
    assert not (held & ~inside).any()


@pytest.mark.parametrize("p", range(2, 9))
def test_the_binomial_expansion_is_the_difference_of_powers(p):
    rng = np.random.default_rng(p)
    Z = rng.normal(size=50) + 1j * rng.normal(size=50)
    d = (rng.normal(size=50) + 1j * rng.normal(size=50)) * 0.3
    assert np.allclose(M.binomial_delta(Z, d, p), (Z + d) ** p - Z ** p, rtol=1e-10, atol=1e-12)


def test_the_expansion_keeps_a_tiny_delta_that_subtraction_loses_in_float32():
    Z = np.complex64(0.6 + 0.3j)
    d = np.complex64(3e-9 + 1e-9j)
    exact = (complex(Z) + complex(d)) ** 3 - complex(Z) ** 3
    got = complex(M.binomial_delta(np.array([Z]), np.array([d]), 3)[0])
    naive = complex((Z + d) ** 3 - Z ** 3)
    assert abs(got - exact) < 1e-3 * abs(exact)
    assert abs(naive - exact) > 0.1 * abs(exact)


def test_the_reference_orbit_is_the_iteration_and_ends_past_the_bail():
    ref = M.reference_orbit(0.5 + 0.5j, 0j, 2, 1000)
    z = 0j
    for k in range(1, len(ref)):
        z = z * z + (0.5 + 0.5j)
        assert ref[k] == z
    assert abs(ref[-1]) ** 2 > M.BAIL and abs(ref[-2]) ** 2 <= M.BAIL
    assert len(M.reference_orbit(-0.1 + 0.1j, 0j, 2, 300)) == 301   # inside: the whole cap


def test_the_rebase_rule():
    Z0 = np.array([0j, 0j, 0.5 + 0j])
    d = np.array([0.1 + 0j, 0.1 + 0j, 0.1 + 0j])
    z = np.array([0.05 + 0j, 0.3 + 0j, 0.55 + 0j])
    assert list(M.rebase(z, d, Z0)) == [True, False, True]


@pytest.mark.parametrize(("label", "q", "zoom", "kw"), [
    ("seahorse", SEAHORSE, 1e6, {}),
    ("deeper", SEAHORSE, 1e9, {}),
    ("julia", 0.30 + 0.45j, 1e5, {"slice": 1.0}),
    ("tilt", -0.7436 + 0.1318j, 1e5, {"slice": 0.4}),
    ("cubic", -0.5279 + 0.6189j, 1e6, {"power": 3}),
])
def test_perturbation_in_float64_is_the_oracle(label, q, zoom, kw):
    """The recurrence, the binomial expansion and the rebase together: δ against
    a reference, all in float64, counts what the direct float64 iteration
    counts."""
    v = values(**kw)
    p, iters = int(v["power"]), 800
    off = M.offsets(48, 32, zoom)
    s = float(v["slice"])
    c_ref, z_ref = M.terms(q, v)
    ref = M.reference_orbit(c_ref, z_ref, p, iters)
    n, ins, _ = M.perturbed_counts(ref, (1 - s) * off, s * off, p, iters, dtype=np.complex128)
    c, z0 = M.terms(q + off, v)
    n0, in0 = M.escape_counts(c, z0, p, iters)
    assert mismatch(counts(n, ins), counts(n0, in0)) < 0.02, label


def test_without_the_rebase_a_reference_that_escapes_early_glitches():
    """The reference at a point that escapes early: in float32, as the shader
    runs, δ grows to the size of z and loses its precision unless the rebase
    carries the pixel back to the orbit's start."""
    q, zoom, iters = SEAHORSE + 2e-5, 1e5, 800
    off = M.offsets(48, 32, zoom)
    ref = M.reference_orbit(q, 0j, 2, iters)
    assert len(ref) < 200                         # this reference escapes early
    n0, in0 = M.escape_counts(q + off, 0, 2, iters)
    on = M.perturbed_counts(ref, off, 0, 2, iters)
    off_rule = M.perturbed_counts(ref, off, 0, 2, iters, rebasing=False)
    good = mismatch(counts(*on[:2]), counts(n0, in0))
    bad = mismatch(counts(*off_rule[:2]), counts(n0, in0))
    assert good < 0.1 and on[2] > 0
    assert bad > 2 * good


def test_float32_perturbation_beats_float32_direct_deep_in():
    """What the tier switch is for: at 10⁵× float32 direct has lost the view,
    float32 perturbation has not."""
    zoom, iters = 1e5, 800
    off = M.offsets(48, 32, zoom)
    n0, in0 = M.escape_counts(SEAHORSE + off, 0, 2, iters)
    nd, ind = M.escape_counts((SEAHORSE + off).astype(np.complex64), 0, 2, iters,
                              dtype=np.complex64)
    ref = M.reference_orbit(SEAHORSE, 0j, 2, iters)
    npt, inp, _ = M.perturbed_counts(ref, off, 0, 2, iters)
    direct, pert = mismatch(counts(nd, ind), counts(n0, in0)), mismatch(counts(npt, inp),
                                                                         counts(n0, in0))
    assert pert < 0.12 and direct > 2 * pert


# ---------------------------------------------------------- the tile rule

def test_a_tile_is_flagged_by_its_border_alone():
    inside = np.ones((32, 48), bool)
    inside[5:10, 5:10] = False          # a hole in tile (0, 0): its border is still inside
    inside[16, 20] = False              # one border pixel of tile (1, 1) out
    flags = M.tile_flags(inside)
    assert flags.shape == (2, 3)
    assert flags[0, 0] and not flags[1, 1] and flags[0, 1] and flags[1, 2]


def test_a_tile_cut_short_at_the_edge_reads_its_own_last_row_and_column():
    inside = np.ones((20, 20), bool)    # tiles of 16 and 4
    inside[19, 18] = False              # the last row: the short tile's border
    flags = M.tile_flags(inside)
    assert flags.shape == (2, 2) and flags[0, 0] and not flags[1, 1]
    inside = np.ones((20, 20), bool)
    inside[17, 17] = False              # inside the short tile, not on its border
    assert M.tile_flags(inside)[1, 1]


def test_the_border_mask_is_where_the_rule_reads():
    e = M.is_edge(20, 18)
    assert e[0].all() and e[15].all() and e[16].all() and e[17].all() and e[:, 19].all()
    assert not e[1:15, 1:15].any() and not e[1:15, 17:19].any()


def test_filling_the_mandelbrot_set_by_tiles_changes_almost_nothing():
    q = -0.5 + M.offsets(256, 192, 1.0)
    _, inside = M.escape_counts(q, 0, 2, 500)
    filled = M.fill_tiles(inside)
    assert M.tile_flags(inside).sum() >= 10    # tiles really are skipped
    assert np.mean(filled != inside) < 0.001


@pytest.mark.parametrize(("kw", "ok"), [
    ({}, True),
    ({"slice": 1.0}, True),
    ({"slice": 1.0, "z0_x": 0.3}, True),        # a Julia slice: z₀ is the screen
    ({"z0_x": 0.1}, False),                     # the Mandelbrot slice off z₀ = 0 has holes
    ({"slice": 0.5}, False),
    ({"interior": 1}, False),                   # a coloured inside needs every pixel
    ({"skip": 1}, False),
    ({"power": 5}, True),
])
def test_where_the_skip_may_run(kw, ok):
    assert M.skip_valid(values(**kw)) is ok


# ------------------------------------------------- sizes, tiers, drives

def test_the_render_size_keeps_the_aspect_and_never_upscales_past_the_output():
    assert M.render_size(0, 1920, 1080) == (960, 540)
    assert M.render_size(1, 1920, 1080) == (1440, 810)
    assert M.render_size(2, 1920, 1080) == (1920, 1080)
    assert M.render_size(2, 3840, 2160) == (1920, 1080)
    assert M.render_size(0, 640, 480) == (640, 480)


def test_the_tier_switches_past_ten_thousand():
    assert not M.perturbs(values(zoom=9e3))
    assert M.perturbs(values(zoom=2e4))
    assert M.perturbs(values(zoom=1.0, tier=2))
    assert not M.perturbs(values(zoom=1e9, tier=1))


def test_a_pan_moves_the_picture_the_same_on_screen_at_any_depth():
    spec = FxState().specs["mandel"]
    moved = []
    for zoom in (1.0, 1e6):
        v = values(zoom=zoom, centre_x=-0.5, pan_x=1.0)
        M.advance(spec, v, 0.1)
        moved.append((v["centre_x"] + 0.5) / M.view_height(zoom))   # in view heights
    assert moved == pytest.approx([0.1, 0.1])


def test_dive_doubles_and_every_drive_moves_by_the_view():
    spec = FxState().specs["mandel"]
    v = values(zoom=1e3, dive=0.25, c_drive_y=-1.0, z0_drive_x=0.5)
    c_y, z0_x = v["c_y"], v["z0_x"]
    M.advance(spec, v, 1.0)
    assert v["zoom"] == pytest.approx(2e3)
    h = M.view_height(2e3)
    assert v["c_y"] == pytest.approx(c_y - h)
    assert v["z0_x"] == pytest.approx(z0_x + 0.5 * h)


def test_a_drive_at_rest_writes_nothing_and_a_term_stays_in_range():
    spec = FxState().specs["mandel"]
    v = values()
    before = dict(v)
    M.advance(spec, v, 0.5)
    assert v == before
    v = values(centre_x=2.4, pan_x=1.0, zoom=0.5)
    M.advance(spec, v, 10.0)
    assert v["centre_x"] == 2.5


def test_the_drives_run_only_while_the_effect_draws():
    st = FxState()
    v = st.values["mandel"]
    v.update(pan_y=1.0)
    st.advance(0.5)
    assert v["centre_y"] == 0.0
    v["on"] = True
    st.advance(0.5)
    assert v["centre_y"] == pytest.approx(0.5 * M.VIEW)


class _Tex:
    size = (M.REF_W, 1)


def test_the_reference_is_kept_until_a_term_changes_or_it_leaves_the_view():
    v = values(zoom=1e6)
    ref = M.Reference(q=complex(v["centre_x"], v["centre_y"]), key=M.terms_key(v), tex=_Tex())
    assert not ref.stale(v, 1.5)
    v["centre_x"] += 0.4 * M.view_height(1e6)        # a pan inside the view
    assert not ref.stale(v, 1.5)
    v["centre_x"] += 0.5 * M.view_height(1e6)        # out of it
    assert ref.stale(v, 1.5)
    for k, x in (("c_x", 0.1), ("power", 3), ("iters", 1000), ("slice", 0.5), ("z0_y", 0.2)):
        w = values(zoom=1e6)
        w[k] = x
        assert ref.stale(w, 1.5), k


def test_the_file_declares_its_hook_and_a_wrong_hook_is_refused():
    assert FxState().specs["mandel"].hook == "mandel"
    with pytest.raises(SpecError, match="@hook"):
        parse("x", "// @hook nothing\nvec4 effect(vec2 uv) { return vec4(0.0); }")


def test_the_zoom_reads_in_figures_and_a_power_of_ten():
    from hyperspace.fx import _fmt
    z = next(p for p in FxState().specs["mandel"].params if p.key == "zoom")
    assert _fmt(z)(1.0) == "1.00×" and _fmt(z)(4.2e7) == "4.2e+07×"


# ---------------------------------------------------------- the shader

moderngl = pytest.importorskip("moderngl")


class Rig:
    """One chain, a source and a float target the effect paints into."""

    def __init__(self, ctx, w=W, h=H):
        self.ctx, self.w, self.h = ctx, w, h
        self.st = FxState()
        self.v = self.st.values["mandel"]
        self.v.update(on=True, cycle=4096.0)
        self.chain = FxChain(ctx, self.st)
        self.src = ctx.texture((w, h), 4)
        self.out = ctx.framebuffer(color_attachments=[ctx.texture((w, h), 4, dtype="f4")])

    def shot(self, **kw) -> np.ndarray:
        self.v.update(kw)
        self.chain.run_one("mandel", self.src, self.out, 0.0, opaque=1)
        assert self.ctx.error == "GL_NO_ERROR"
        assert not self.chain.errors, self.chain.errors
        return (np.frombuffer(self.out.read(components=4, dtype="f4"), np.float32)
                .reshape(self.h, self.w, 4).copy())

    def steps(self, **kw) -> np.ndarray:
        """The pass's counts back from Output steps (cycle above the cap, so
        brightness = count / cycle), the inside -1."""
        px = self.shot(**kw)
        n = px[..., 0].astype(np.float64) * self.v["cycle"]
        return np.where(n == 0, -1.0, n)

    @property
    def stats(self) -> dict:
        return self.chain.mandel.states["mandel"].stats

    def release(self):
        self.chain.release()
        self.src.release()
        self.out.release()


@pytest.fixture
def rig(ctx):
    r = Rig(ctx)
    yield r
    r.release()


def twin_direct(v, w=W, h=H):
    """The shader's direct tier in numpy float32, periodicity and all."""
    zoom = float(v["zoom"])
    q = (complex(v["centre_x"], v["centre_y"]) + M.offsets(w, h, zoom)).astype(np.complex64)
    c, z0 = M.terms(q, v)
    n, ins = M.escape_counts(c.astype(np.complex64), np.complex64(z0) if np.isscalar(z0)
                             else z0.astype(np.complex64), int(v["power"]), M.steps(v),
                             periodic_eps=M.view_height(zoom) / h * M.PERIOD_EPS,
                             dtype=np.complex64)
    return counts(n, ins)


def oracle(v, w=W, h=H):
    q = complex(v["centre_x"], v["centre_y"]) + M.offsets(w, h, float(v["zoom"]))
    c, z0 = M.terms(q, v)
    return counts(*M.escape_counts(c, z0, int(v["power"]), M.steps(v)))


@pytest.mark.parametrize("kw", [
    {},
    {"power": 4, "centre_x": 0.0},
    {"slice": 1.0, "centre_x": 0.0},
    {"slice": 0.5, "z0_x": 0.2},
], ids=["mandelbrot", "power-4", "julia", "tilt"])
def test_the_direct_tier_is_its_float32_twin(rig, kw):
    v = values(iters=300.0, skip=1, cycle=4096.0, **kw)
    got = rig.steps(**{k: v[k] for k in v if k not in ("on",)})
    assert not rig.stats["perturb"]
    assert mismatch(got, twin_direct(rig.v)) < 0.02
    assert mismatch(got, oracle(rig.v)) < 0.05


def test_the_perturbation_tier_deep_in_is_its_float32_twin_and_near_the_oracle(rig):
    got = rig.steps(centre_x=SEAHORSE.real, centre_y=SEAHORSE.imag, zoom=1e6, iters=600.0,
                    skip=1)
    assert rig.stats["perturb"]
    v = rig.v
    ref = M.reference_orbit(SEAHORSE, 0j, 2, 600)
    off = M.offsets(W, H, 1e6)
    n, ins, _ = M.perturbed_counts(ref, off, 0, 2, 600,
                                   periodic_eps=M.view_height(1e6) / H * M.PERIOD_EPS)
    assert mismatch(got, counts(n, ins)) < 0.03
    assert mismatch(got, oracle(v)) < 0.12
    direct = rig.steps(tier=1)
    assert mismatch(direct, oracle(v)) > 2 * mismatch(got, oracle(v))


def test_the_skip_fills_whole_tiles_and_moves_almost_nothing(ctx):
    r = Rig(ctx, 160, 128)
    try:
        kw = {"iters": 400.0, "zoom": 1.0, "centre_x": -0.5}
        on = r.steps(skip=0, **kw)
        assert r.stats["skip"]
        tiles = np.frombuffer(r.chain.mandel.states["mandel"].tiles.fbo.read(components=4),
                              np.uint8).reshape(8, 10, 4)[..., 0] > 127
        off = r.steps(skip=1, **kw)
        assert not r.stats["skip"]
        assert tiles.sum() >= 4
        assert np.array_equal(tiles, M.tile_flags(off < 0))
        assert np.mean((on < 0) != (off < 0)) < 0.002
    finally:
        r.release()


def test_how_it_computes_never_changes_what_it_shows(ctx):
    """Size, Tier and Skip black choose how the picture is made, not what it is
    (so `tests/test_step_continuity.py` holds them at their defaults): at the
    sweep's own 320×200, every Size is the output itself; direct and
    perturbation agree at zoom 1 to float32's error; the skip moves only
    pixels of the inside."""
    r = Rig(ctx, 320, 200)
    try:
        kw = {"iters": 200.0, "cycle": 4096.0, "zoom": 1.0}
        base = r.steps(size=0, tier=1, skip=0, **kw)
        for size in range(len(M.SIZES)):
            assert np.array_equal(r.steps(size=size, tier=1, skip=0), base), size
            assert r.stats["size"] == (320, 200)
        assert mismatch(r.steps(size=0, tier=2, skip=0), base) < 0.02
        assert np.mean(r.steps(size=0, tier=1, skip=1) != base) < 0.002
    finally:
        r.release()


def test_the_size_renders_at_its_lines_and_upscales(ctx):
    r = Rig(ctx, 960, 720)
    try:
        px = r.shot(size=0, iters=48.0, skip=1)
        assert r.stats["size"] == (720, 540)
        assert px[..., 0].max() > 0 and np.all(px[..., 3] == 1.0)
        r.shot(size=2)
        assert r.stats["size"] == (960, 720)
    finally:
        r.release()


def test_the_reference_is_made_again_only_when_it_must_be(rig):
    kw = {"centre_x": SEAHORSE.real, "centre_y": SEAHORSE.imag, "zoom": 1e6, "iters": 200.0}
    rig.shot(**kw)
    assert rig.stats["references"] == 1
    rig.shot(centre_x=SEAHORSE.real + 0.2 * M.view_height(1e6))
    assert rig.stats["references"] == 1
    rig.shot(c_x=0.1)                      # a term the Mandelbrot slice does not read: still a term
    assert rig.stats["references"] == 2
    rig.shot(centre_x=SEAHORSE.real + 3 * M.view_height(1e6))
    assert rig.stats["references"] == 3


def test_inside_black_coloured_and_the_ramp(rig):
    kw = {"iters": 200.0, "cycle": 64.0, "skip": 1}
    black = rig.shot(interior=0, output=0, **kw)
    coloured = rig.shot(interior=1)
    inside = black[..., 0] == 0
    assert inside.mean() > 0.1
    assert coloured[inside][:, 0].max() > 0
    ramp = rig.shot(interior=0, output=1)
    assert np.abs(ramp[..., 0] - ramp[..., 2]).max() > 0.2      # coloured, not grey
    assert np.all(ramp[inside][:, :3] == 0)
    assert np.all(black[..., 0] == black[..., 1])               # steps: grey


def test_a_drive_moves_the_picture_through_the_pass(rig):
    rig.v.update(pan_x=1.0)
    rig.shot(iters=32.0)
    rig.chain.run_one("mandel", rig.src, rig.out, 0.2, opaque=1)
    assert rig.v["centre_x"] == pytest.approx(-0.5 + 0.2 * M.VIEW)


def test_every_size_is_a_choice_of_lines():
    names = next(p for p in FxState().specs["mandel"].params if p.key == "size").choices
    assert tuple(int(n) for n in names) == M.SIZES
    assert math.isclose(M.PERTURB_AT, 1e4)


def test_the_rig_bench_runs_and_prints_a_line_a_size(capsys):
    """`tools/mandel_bench.py --quick` end to end (its numbers are the rig's)."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "tools" / "mandel_bench.py"
    spec = importlib.util.spec_from_file_location("mandel_bench", path)
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    assert bench.main(["--quick", "--out", "96x64"]) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith(("whole", "minibrot"))]
    assert len(lines) == 2 * len(M.SIZES)
    assert any("perturb" in ln for ln in lines) and any("direct" in ln for ln in lines)
