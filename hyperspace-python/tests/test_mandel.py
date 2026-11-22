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
    """Dive doubles; on the Mandelbrot slice c is unused (R → ∞), so its
    drive keeps plan 63's rate, one view height a second; z₀ there is an
    off-screen term, moved by the view times its measured scale (plan 80),
    never faster than the view."""
    spec = FxState().specs["mandel"]
    v = values(zoom=1e3, dive=0.25, c_drive_y=-1.0, z0_drive_x=0.5)
    c_y, z0_x = v["c_y"], v["z0_x"]
    M.advance(spec, v, 1.0)
    assert v["zoom"] == pytest.approx(2e3)
    h = M.view_height(2e3)
    assert v["c_y"] == pytest.approx(c_y - h)
    assert 0.0 < v["z0_x"] - z0_x <= 0.5 * h * (1 + 1e-9)


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


# ------------------------------------------- continuity at long horizons
#
# The generic sweep (`tests/test_step_continuity.py`) measures a knob step as
# displacement of a UV picture an effect bends; this effect paints over its
# input, and reads no clock. Time reaches it only through the drives (terms
# integrated in float64) and the reference orbit (remade as the view moves).
# So "a knob step is the same an hour in as a second in" is held here in
# those terms.

def test_the_shader_reads_no_clock():
    src = FxState().specs["mandel"].source
    assert "u_phase" not in src and "u_time" not in src
    assert not FxState().specs["mandel"].clocks


def test_the_picture_is_the_same_a_second_and_two_hours_in(rig):
    kw = {"centre_x": SEAHORSE.real, "centre_y": SEAHORSE.imag, "zoom": 1e6, "iters": 300.0}
    rig.v.update(kw)
    rig.chain.run_one("mandel", rig.src, rig.out, 1.0, opaque=1)
    early = rig.shot()
    rig.chain.run_one("mandel", rig.src, rig.out, 7231.9, opaque=1)
    late = rig.shot()
    assert np.array_equal(early, late)


def test_a_drive_held_an_hour_moves_by_the_view_and_no_more():
    """An hour of frames at 60 fps with Pan held at 10⁹×: the centre has gone
    the distance the rate says, to 0.01% — float64 rounds each frame's tiny
    step the same way, so the speed is that little off, steadily, and nothing
    jumps (nearer 10¹³× the step nears the centre's last digit: the deep
    tier's reach, row 881) — and a step of the drive an hour in moves the
    picture on screen as a step a second in does."""
    spec = FxState().specs["mandel"]
    v = values(zoom=1e9, centre_x=-0.75, pan_x=0.01)
    for _ in range(3600 * 60):
        M.advance(spec, v, 1 / 60)
    h = M.view_height(1e9)
    assert (v["centre_x"] + 0.75) / h == pytest.approx(0.01 * 3600, rel=1e-3)
    moved = []
    for when in (v, values(zoom=1e9, centre_x=-0.75)):
        w = dict(when, pan_x=0.02)          # one step up the drive
        x0 = w["centre_x"]
        M.advance(spec, w, 1 / 60)
        moved.append((w["centre_x"] - x0) / h)
    assert moved[0] == pytest.approx(moved[1], rel=1e-6)


def test_a_step_of_a_drive_moves_nothing_until_the_next_frame(rig):
    rig.v.update(zoom=1e5, centre_x=SEAHORSE.real, centre_y=SEAHORSE.imag, iters=200.0)
    before = rig.shot()
    rig.v["pan_x"] = 0.5             # the knob moves; no frame time has passed
    assert np.array_equal(rig.shot(), before)


def test_a_new_reference_redraws_the_same_picture(rig):
    """Deep in, a pan that carries the reference out of the view remakes it at
    the new centre: panning back shows the same picture to float32's error,
    so a remade reference never jumps the frame."""
    kw = {"centre_x": SEAHORSE.real, "centre_y": SEAHORSE.imag, "zoom": 1e6, "iters": 400.0}
    a = rig.steps(**kw)
    rig.shot(centre_x=SEAHORSE.real + 5 * M.view_height(1e6))
    rig.shot(centre_x=SEAHORSE.real + 0.45 * M.view_height(1e6))   # reference there, in view
    refs = rig.stats["references"]
    b = rig.steps(centre_x=SEAHORSE.real)
    assert rig.stats["references"] == refs and refs >= 2
    assert mismatch(a, b) < 0.05


# ---------------------------------------- review fixes (Devin, PR #462)

def test_deep_periodicity_compares_parts_and_finds_no_false_inside(rig):
    """At Centre (0, 1), 10¹², every pixel escapes. Subtracting two float32 z's
    (each Z + δ, δ's digits gone) read them as one cycle and painted it black;
    the check compares (Zₘ − Z_saved) + (δ − δ_saved)."""
    q, zoom = 1j, 1e12
    off = M.offsets(W, H, zoom)
    ref = M.reference_orbit(q, 0j, 2, 512)
    eps = M.view_height(zoom) / H * M.PERIOD_EPS
    n, ins, _ = M.perturbed_counts(ref, off, 0, 2, 512, periodic_eps=eps)
    n0, in0 = M.escape_counts(q + off, 0, 2, 512)
    assert not in0.any() and not ins.any()
    assert mismatch(counts(n, ins), counts(n0, in0)) < 0.02
    got = rig.steps(centre_x=0.0, centre_y=1.0, zoom=zoom, iters=512.0, skip=1)
    assert rig.stats["perturb"] and not (got < 0).any()
    assert mismatch(got, counts(n0, in0)) < 0.05


def test_a_rebase_from_a_start_off_zero_keeps_a_tiny_delta():
    """A Julia reference starting at 1 (c = 0): z − Z₀ taken from the full
    float32 z rounded a 10⁻⁹ δ to zero and the point never escaped; taken as
    (Zₘ − Z₀) + δ it escapes where the oracle says."""
    ref = M.reference_orbit(0j, 1 + 0j, 2, 512)
    n, ins, _ = M.perturbed_counts(ref, np.array([0j]), np.array([1e-9 + 0j]), 2, 512)
    n0, in0 = M.escape_counts(np.array([0j]), np.array([1 + 1e-9 + 0j]), 2, 512)
    assert not in0[0] and not ins[0]
    assert abs(n[0] - n0[0]) < 1.0


def test_a_deep_julia_view_off_zero_is_its_oracle(rig):
    v = {"slice": 1.0, "c_x": 0.0, "c_y": 0.0, "centre_x": 1.0, "centre_y": 0.0,
         "zoom": 1e9, "iters": 512.0, "skip": 1}
    got = rig.steps(**v)
    assert rig.stats["perturb"]
    want = oracle(rig.v)
    assert (want < 0).mean() > 0.2 and (want >= 0).mean() > 0.2    # the circle crosses it
    assert mismatch(got, want) < 0.05


def test_a_deleted_instance_frees_its_gl_objects(rig):
    rig.shot(iters=32.0)
    st = rig.chain.mandel.states["mandel"]
    assert st.border.tex is not None            # the skip ran: three targets made
    rig.st.hold([])                             # a patch without it lands
    rig.chain.tick()
    assert "mandel" not in rig.chain.mandel.states
    assert st.border.tex is None and st.tiles.tex is None and st.ref.tex is None


def test_a_reload_of_the_module_drops_the_old_objects(rig):
    rig.shot(iters=32.0)
    gl = rig.chain.mandel
    st = gl.states["mandel"]

    class Old(M.Gl):            # what a live Gl is once mandel.py is reloaded
        pass

    gl.__class__ = Old
    rig.chain.tick()
    assert rig.chain.mandel is None and st.border.tex is None and gl.tiles_prog is None
    rig.shot()                  # made again, by the module as it is now
    assert type(rig.chain.mandel) is M.Gl


def test_a_reload_of_fx_drops_them_too(rig):
    rig.shot(iters=32.0)
    st = rig.chain.mandel.states["mandel"]
    rig.chain.on_reload()
    assert rig.chain.mandel is None and st.border.tex is None
    rig.shot()
    assert rig.chain.mandel is not None


# ---------------------------------------------------------------- plan 80

# 1. With nothing wired in, it draws (row 1000)

def test_it_says_it_is_a_generator_and_an_ordinary_effect_does_not():
    from hyperspace import fx

    assert M.GENERATOR is True
    assert fx.HOOKS[FxState().specs["mandel"].hook] is M
    assert not FxState().specs["acid"].hook


def _wired(ctx, pairs, values):
    from test_graph_faces import _fbo

    from hyperspace import graph as G
    from hyperspace.graphmigrate import wired_wiring
    from hyperspace.outputs import Switches, View
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    r = Renderer(ctx)
    r.ghost.state.on = False
    for name, v in values.items():
        r.fx.state.values[name].update(v)
    spec = G.read_graph({"nodes": [], "wires": [{"from": a, "to": b} for a, b in pairs]},
                        effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = wired_wiring(spec.wiring())
    views = [View(Switches(), (96, 64), target=_fbo(ctx, 96, 64))]
    return r, ViewState(lines=False, points=False, faces=False), views


def _drawn(ctx, r, s, views):
    from test_graph_faces import _px

    r.draw_outputs(s, 96, 64, 1.0, views, t_now=1.0)
    assert ctx.error == "GL_NO_ERROR"
    return _px(views[0].target)[..., :3].astype(float)


def test_with_nothing_wired_in_it_draws_the_whole_frame(ctx):
    """The owner's report: mandel → output.1 with nothing into mandel.image
    was black, with no note. It paints the whole frame from nothing, so it
    draws — the same picture as with a picture wired in (at mix 1 that
    picture is not seen) — and an ordinary effect with no input still reads
    nothing."""
    on = {"mandel": {"on": True, "iters": 64.0, "output": 1}}
    r, s, vs = _wired(ctx, [("mandel", "output.1.image")], on)
    alone = _drawn(ctx, r, s, vs)
    assert alone.max() > 100, "the frame is black with nothing wired in"
    r2, s2, vs2 = _wired(ctx, [("frame", "mandel.image"), ("mandel", "output.1.image")], on)
    fed = _drawn(ctx, r2, s2, vs2)
    assert np.abs(alone - fed).max() <= 2.0
    r3, s3, vs3 = _wired(ctx, [("acid", "output.1.image")], {"acid": {"on": True}})
    assert _drawn(ctx, r3, s3, vs3).max() < 5


def test_with_nothing_wired_in_and_switched_off_it_draws_nothing(ctx):
    r, s, vs = _wired(ctx, [("mandel", "output.1.image")],
                      {"mandel": {"on": False, "iters": 64.0, "output": 1}})
    assert _drawn(ctx, r, s, vs).max() < 5


# 2. The coloured inside is how fast a point settles (row 1001)

def apart(a, b, rel=0.02) -> float:
    """The share of pixels whose counts differ by more than a step and more
    than `rel` of the count: a settle count is smooth and runs to thousands,
    so float32's last bits move it by a fraction of a step at 1474.87 and by
    a few steps at 6000 — neither is a different colour."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.mean(np.abs(a - b) > np.maximum(1.0, rel * np.abs(a))))

SEA = complex(-0.743643887037151, 0.131825904205330)


def _settle_counts(zoom, iters, w=40, h=24):
    off = M.offsets(w, h, zoom)
    eps = M.view_height(zoom) / h * M.PERIOD_EPS
    ref = M.reference_orbit(SEA, 0j, 2, iters)
    oracle = M.escape_counts(SEA + off, 0j, 2, iters, periodic_eps=eps, settle=True)
    f32 = M.perturbed_counts(ref, off, 0, 2, iters, periodic_eps=eps, settle=True)[:2]
    old = M.escape_counts(SEA + off, 0j, 2, iters, periodic_eps=eps)
    return oracle, f32, old


@pytest.mark.parametrize("zoom", [1e6, 9e6])
def test_the_coloured_inside_under_perturbation_is_the_float64_oracle(zoom):
    """The owner's views: the seahorse at 1e6 and 9e6, Steps 6000. The cause
    of the flat grey, the blocks and the odd bands was the colour rule, not
    the rebase alone: the step the periodicity check caught a point at
    hangs on a tolerance of 5 % of a pixel, so deep in most of the inside
    never settles that close before the cap even in float64 (the flat grey
    — the old rule's oracle, below), and what does is quantised by Brent's
    window (bands, discs) and, in float32 after a rebase, by the last bit
    (blocks). How fast a point settles, from its cycle's multiplier
    (`Settle`), is smooth, and float32 perturbation gives the float64
    oracle's."""
    (n0, i0), (n1, i1), (old, old_in) = _settle_counts(zoom, 6000)
    both = i0 & i1
    assert both.mean() > 0.3                        # there is an inside to colour
    assert np.mean(i0 != i1) < 0.01
    assert apart(np.where(both, n0, 0), np.where(both, n1, 0)) < 0.03
    # the old rule: a handful of values (bands), and at 9e6 most of the inside
    # at the cap (the flat grey); the new: a spread of values to colour by
    # (what is still at the cap is a ring slower than 6000 steps, or an
    # outside point still running there)
    assert np.unique(old[old_in]).size < 30
    assert np.unique(np.round(n0[i0])).size > 3 * np.unique(old[old_in]).size
    if zoom > 5e6:
        assert np.mean(old[old_in] == 6000) > 0.8


def test_settling_is_the_multiplier_not_the_tolerance():
    """Inside the main cardioid c's fixed point has multiplier λ = 1 −
    √(1 − 4c); the settle count is ln K / ln|λ| whatever the periodicity's
    tolerance: 0 at the nucleus, slower toward the edge."""
    c = np.array([0.0 + 0j, 0.1 + 0.1j, -0.3 + 0.2j, 0.2 + 0.0j])
    lam = np.abs(1 - np.sqrt(1 - 4 * c))
    want = np.array([math.log(M.SETTLE_K) / math.log(x) if x > 0 else 0.0 for x in lam])
    for eps in (1e-4, 1e-8, 1e-12):
        n, ins = M.escape_counts(c, 0j, 2, 4000, periodic_eps=eps, settle=True)
        assert ins.all()
        assert n == pytest.approx(want, abs=0.6)


def test_the_shader_holds_the_settle_constants():
    import re
    from pathlib import Path

    text = (Path(M.__file__).parent / "shaders" / "fx" / "mandel.glsl").read_text()
    ln = float(re.search(r"LN_SETTLE_K = (-?[\d.e+-]+);", text).group(1))
    near = float(re.search(r"SETTLE_NEAR = ([\d.e+-]+);", text).group(1))
    assert ln == pytest.approx(math.log(M.SETTLE_K), rel=1e-12)
    assert near == M.SETTLE_NEAR
    assert f"BORDER = {M.BORDER};" in text


def test_the_gpu_coloured_inside_is_its_float32_twin_deep_in(rig):
    """The pass at the seahorse, 1e6, the inside coloured: the GPU against
    numpy's float32 perturbation with the same rule, and the float64
    oracle."""
    zoom, iters = 1e6, 3000
    got = rig.steps(centre_x=SEA.real, centre_y=SEA.imag, zoom=zoom, iters=float(iters),
                    interior=1, tier=2)
    assert rig.stats["perturb"]
    off = M.offsets(W, H, zoom)
    eps = M.view_height(zoom) / H * M.PERIOD_EPS
    ref = M.reference_orbit(SEA, 0j, 2, iters)
    n, ins, _ = M.perturbed_counts(ref, off, 0, 2, iters, periodic_eps=eps, settle=True)
    n0, i0 = M.escape_counts(SEA + off, 0j, 2, iters, periodic_eps=eps, settle=True)
    assert i0.mean() > 0.3
    got = np.where(got < 0, 0.0, got)           # rig.steps reads a count of 0 as -1
    assert apart(got, n) < 0.05
    assert apart(got, n0) < 0.08


def test_the_coloured_inside_in_the_direct_tier_is_the_oracle(rig):
    got = rig.steps(centre_x=-0.5, centre_y=0.0, zoom=1.0, iters=600.0, interior=1, skip=1)
    assert not rig.stats["perturb"]
    q = complex(-0.5, 0.0) + M.offsets(W, H, 1.0)
    n0, _ = M.escape_counts(q, 0j, 2, 600, periodic_eps=M.view_height(1.0) / H * M.PERIOD_EPS,
                            settle=True)
    got = np.where(got < 0, 0.0, got)
    assert apart(got, n0) < 0.05


# 3. An off-screen term's drive answers the picture, not the zoom alone (row 1002)

def _brightness_change(v, key, delta, w=64, h=36, it=300):
    def pic(vv):
        q = complex(vv["centre_x"], vv["centre_y"]) + M.offsets(w, h, vv["zoom"])
        c, z = M.terms(q, vv)
        n, ins = M.escape_counts(c, z, int(vv["power"]), it)
        return np.where(ins, 0.0, 1 - np.abs(1 - np.mod(n / 64.0, 2.0)))
    return float(np.mean(np.abs(pic({**v, key: v[key] + delta}) - pic(v))))


def _held(v, rate_key, seconds=1.0, fps=60):
    spec = FxState().specs["mandel"]
    v = dict(v, **{rate_key: 1.0})
    for _ in range(int(seconds * fps)):
        M.advance(spec, v, 1 / fps)
    return v


JULIA = dict(slice=1.0, centre_x=0.0, centre_y=0.0, zoom=1.7, c_x=-0.8, c_y=0.156, iters=300.0)


def test_c_on_a_julia_slice_is_slowed_to_what_the_picture_takes():
    """The owner's view: a Julia slice at zoom 1.7, where a view height is
    1.8 units of c and 0.03 of c tears the set apart. A second of the c
    drive at full throw used to move c by 1.8; now by its measured share,
    well under a tenth of the view — and that second changes the picture
    within ×10 of a quarter-second of pan, where plan 63's rate changed it
    many times as much."""
    v = values(**JULIA)
    h = M.view_height(1.7)
    moved = _held(v, "c_drive_x")["c_x"] - v["c_x"]
    assert 0.0 < moved < 0.1 * h
    pan = _brightness_change(v, "centre_x", 0.25 * h)
    term = _brightness_change(v, "c_x", moved)
    assert pan / 10 < term < pan * 10, (term, pan)


def test_the_measured_scale_follows_the_picture_across_views():
    """R (`sensitivity`) against the picture: a step of R·d in c changes it
    about as much as a pan of d, over Julia views where plan 63's rate (the
    view height, for both) was off by orders of magnitude."""
    for cx, cy, zoom, cen in [(-0.1, 0.65, 20.0, (0.3, 0.1)), (0.285, 0.01, 300.0, (0.31, 0.12)),
                              (-0.4, 0.6, 20.0, (0.3, 0.1))]:
        v = values(slice=1.0, c_x=cx, c_y=cy, zoom=zoom, centre_x=cen[0], centre_y=cen[1],
                   iters=400.0)
        r = M.sensitivity(v)["c"]
        d = 0.01 * M.view_height(zoom)
        assert r < 1.0
        pan = _brightness_change(v, "centre_x", d)
        term = _brightness_change(v, "c_x", r * d)
        assert pan / 6 < term < pan * 6, (cx, cy, zoom, term, pan)


def test_an_unused_term_and_pan_keep_their_rates_and_the_rate_never_jumps():
    spec = FxState().specs["mandel"]
    h = M.view_height(1.7)
    v = values(**dict(JULIA, slice=0.0, centre_x=-0.5, c_drive_x=1.0))   # c is the screen
    before = v["c_x"]
    M.advance(spec, v, 0.5)
    assert v["c_x"] - before == pytest.approx(0.5 * h)          # unused: plan 63's rate
    j = values(**JULIA)
    p = dict(j, pan_x=1.0)
    M.advance(spec, p, 0.5)
    assert p["centre_x"] == pytest.approx(0.5 * h)              # pan as it was
    j = dict(j, c_drive_x=1.0)
    steps = []
    for _ in range(120):
        x = j["c_x"]
        M.advance(spec, j, 1 / 60)
        steps.append(j["c_x"] - x)
    steps = np.array(steps)
    assert (steps > 0).all()
    assert (steps[1:] / steps[:-1]).max() < 2.0                 # eased: no jump


# 4. Cost: the packed border pass, and the skip that rests (rows 1003, 1004)

def test_the_packed_border_slots_are_a_tiles_border():
    for w, h in [(16, 16), (40, 24), (33, 17)]:
        edge = M.is_edge(w, h)
        th, tw = -(-h // M.TILE), -(-w // M.TILE)
        for ty in range(th):
            for tx in range(tw):
                got = set()
                for i in range(M.BORDER):
                    x, y = M.border_slot(i)
                    got.add((min(tx * M.TILE + x, w - 1), min(ty * M.TILE + y, h - 1)))
                part = edge[ty * M.TILE:(ty + 1) * M.TILE, tx * M.TILE:(tx + 1) * M.TILE]
                ys, xs = np.nonzero(part)
                want = {(tx * M.TILE + int(x), ty * M.TILE + int(y)) for x, y in zip(xs, ys)}
                assert got == want, (w, h, tx, ty)


def test_the_skip_with_the_packed_pass_flags_what_the_rule_flags(ctx):
    r = Rig(ctx, 160, 128)
    try:
        r.steps(skip=0, iters=400.0, zoom=1.0, centre_x=-0.5)
        assert r.stats["skip"]
        st = r.chain.mandel.states["mandel"]
        flags = np.frombuffer(st.tiles.tex.read(), np.uint8).reshape(8, 10, 4)[..., 0] > 127
        q = complex(-0.5, 0.0) + M.offsets(160, 128, 1.0)
        _, ins = M.escape_counts(q, 0j, 2, 400,
                                 periodic_eps=M.view_height(1.0) / 128 * M.PERIOD_EPS)
        want = M.tile_flags(ins)
        assert want.any() and np.mean(flags != want) < 0.03
    finally:
        r.release()


class _QCtx:
    """A context whose queries count what `n` says when read (a query is
    used again once read, as on the GPU)."""

    def __init__(self, n):
        self.n, self.made = n, 0

    def query(self, samples=False):
        self.made += 1
        ctx = self

        class Q:
            @property
            def samples(self):
                return ctx.n

        return Q()


def test_the_skip_rests_where_few_tiles_are_flagged_and_looks_again():
    g = M.SkipGate()
    ctx = _QCtx(5)                            # 5 % flagged
    assert g.want()
    g.issue(ctx, 100)
    for _ in range(M.SKIP_LAG):
        g.read()
        assert g.on                           # not read yet: the CPU never waits
    g.read()
    assert not g.on and g.flagged == pytest.approx(0.05)
    runs = [g.want() for _ in range(2 * M.SKIP_PROBE)]
    assert sum(runs) == 2                     # one probe every SKIP_PROBE passes
    ctx.n = 80
    g.issue(ctx, 100)
    assert ctx.made == 1                      # the read query is used again
    for _ in range(M.SKIP_LAG + 1):
        g.read()
    assert g.on and g.flagged == pytest.approx(0.8)


def test_a_context_with_no_queries_keeps_the_skip_on():
    class NoQ:
        def query(self, samples=False):
            raise RuntimeError("no queries")

    g = M.SkipGate()
    assert g.issue(NoQ(), 10) is None
    assert g.on and not g.queries and g.want()


def test_on_the_gpu_the_skip_turns_itself_off_and_the_picture_stays(ctx):
    """The whole set at zoom 1: the cardioid test makes its inside cheap and
    under SKIP_MIN of the tiles are flagged, so after SKIP_LAG passes the
    skip rests — and the picture is the same either way."""
    r = Rig(ctx, 160, 128)
    try:
        kw = {"iters": 400.0, "zoom": 1.0, "centre_x": -0.5, "skip": 0}
        first = r.steps(**kw)
        assert r.stats["skip"]
        for _ in range(M.SKIP_LAG + 1):
            r.steps(**kw)
        assert r.stats["skip_valid"] and not r.stats["skip"]
        assert r.stats["flagged"] < M.SKIP_MIN
        assert mismatch(first, r.steps(**kw)) < 0.01
    finally:
        r.release()


def test_the_binomial_without_an_array_is_the_difference_for_every_power(rig):
    """p = 2's closed form and the walked powers for the rest, through the
    pass deep in: each power against its float32 twin."""
    for p in (2, 3, 5):
        zoom = 3e5
        q = complex(-0.1, 0.85) if p > 2 else SEA
        got = rig.steps(centre_x=q.real, centre_y=q.imag, zoom=zoom, iters=300.0, power=p,
                        skip=1, tier=2)
        ref = M.reference_orbit(q, 0j, p, 300)
        n, ins, _ = M.perturbed_counts(ref, M.offsets(W, H, zoom), 0, p, 300,
                                       periodic_eps=M.view_height(zoom) / H * M.PERIOD_EPS)
        assert mismatch(got, counts(n, ins)) < 0.05, p
