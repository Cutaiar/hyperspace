"""A knob step is the same size an hour in as a second in (register row
580; K4 of the post-show plan, after row 560).

The time lint (`tests/shader_lint.py`) reads products of a time and a
param in the source; it cannot see a param that scales *space* where the
time hides inside a call (`fract((uv + mod(u_phase, 1e4) * 0.001) *
u_scale)`), a hash, or the host. So this module measures instead, over
every shipped effect's every param (`speed` and each `@param`) and every
face pattern's every input but SPEED, with no reading of the source at
all: the picture's change for a small step of the knob, taken with every
clock stopped at the same phase, early in a set and late in one.

- **The step alone.** `uv_flow.jump`: the effect over the UV source at
  the knob's value and at one step on, both with the clocks at the same
  phase, so no frame's own motion is in it — a param the host integrates
  (`speed`, a `@clock`'s rate) moves nothing.
- **Small.** A hundredth of a detent for an effect (a whole one for an
  integer param), a tenth for a pattern input (the tile is 8-bit): small
  enough that a change of shape is a fraction of a pixel, while a phase
  carried by time is shifted by `phase × Δ` — whole screens an hour in.
- **Early and late.** The early size is the largest over six phases from
  0.1 to 98 (a slow wave in the effect's own clock, acid's `sin(T / 143)`,
  has turned by then, so a shape change the clock modulates is seen at its
  full size); the late one the smaller of an hour and two hours.
- **The rule.** Late at most 4 × early + a floor (0.5 px of the 320 × 200
  field; 0.5 of 255 levels on a 64² pattern tile). A knob that changes a
  shape — glimmer's size, fractals' cells, wobble's frequency, kaleido's
  segments — changes it by the same amount whenever it moves, and passes
  however large that is; one whose change grows with the clock fails by
  twenty times (warp's drift and scale, tripcolour's pulse and RINGS'
  colour before K4: see the PR). What it cannot see: a rate under a
  sine that has wrapped by phase 98 at a hundredth of a detent (a rate
  of more than ~6 rad a unit) — the lint's product rule catches those.

The pairs the time lint still allowlists (K2's, today) are left to the
lint: a growth there is expected until the port, and no xfail mark is
needed once they go.
"""

from __future__ import annotations

import shutil

import numpy as np
import pytest
import uv_flow
from test_shader_time_lint import ALLOWLIST as TIME_ALLOWLIST

from hyperspace import fx
from hyperspace import patterns as P
from hyperspace.params import Registry

moderngl = pytest.importorskip("moderngl")

EARLY = (0.137, 0.71, 7.3, 23.1, 61.7, 97.9)    # phases, seconds at speed 1
LATE = (3613.7, 7231.9)                          # an hour and two in; not round
FACTOR = 4.0
FX_FLOOR_PX = 0.5
FX_FRACTION = 0.01                               # of a detent, for a float param
PATTERN_FLOOR = 0.5                              # levels of 255
PATTERN_FRACTION = 0.1
PATTERN_SIZE = 64
PATTERN_DETENT = 2.6 / 100                       # pattern.mod.*: 0 … 2.6, RAW_STEPS


@pytest.fixture(scope="module")
def gl():
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield ctx
    ctx.release()


def grows(early: float, late: float, floor: float) -> bool:
    return late > FACTOR * early + floor


# ---------------------------------------------------------------- effects

def small_step(r: Registry, state: fx.FxState, name: str, key: str,
               fraction: float = FX_FRACTION) -> tuple[float, float]:
    """`key`'s value and a `fraction` of one detent on — the registry's own
    detent (`Param.step`: the taper, log or linear, wrapped or not); down
    from the top; a whole detent for an integer."""
    v = state.values[name]
    par = r[f"fx.{name}.{key}"]
    before = v[key]
    par.step(1)
    if v[key] == before:
        par.step(-2)
    after = v[key]
    v[key] = before
    spec = state.files[name]
    p = next((p for p in spec.params if p.key == key), None)
    if p is not None and p.integer:
        return before, after
    d = after - before
    if p is not None and p.wrap and abs(d) > (p.hi - p.lo) / 2:    # stepped over the seam
        d -= np.sign(d) * (p.hi - p.lo)
    return before, before + d * fraction


def effect_report(ctx, state: fx.FxState, name: str, keys=None) -> dict[str, tuple[float, float]]:
    """key → (early, late) step sizes, px, for effect `name` on `state`:
    every amount-type param but the one stepped at half its range, so the
    effect shows (their defaults are calm: PR #304)."""
    r = Registry()
    fx.declare(r, state)
    spec = state.files[name]
    v = state.values[name]
    rest = dict(v)
    keys = keys or ["speed", *[p.key for p in spec.params if not p.choices]]
    chain = fx.FxChain(ctx, state)
    out = {}
    try:
        (src, _), (_, dst) = chain.pool((uv_flow.W, uv_flow.H))
        src.write(uv_flow.uv_source().tobytes())
        for key in keys:
            v.clear()
            v.update(rest)
            v.update({p.key: p.hi / 2 for p in spec.params if p.amount and p.key != key})
            v.update(on=True, mix=1.0)
            before, after = small_step(r, state, name, key)

            def at(ph, key=key, before=before, after=after):
                return uv_flow.jump(chain, src, dst, name, key, before, after, ph)
            out[key] = (max(at(ph) for ph in EARLY), min(at(ph) for ph in LATE))
        assert not chain.errors, chain.errors
    finally:
        v.clear()
        v.update(rest)
        chain.release()
    return out


def time_allowlisted(name: str) -> set[str]:
    """The keys of `name` whose uniform the time lint still allowlists."""
    by_uniform = {p.uniform: p.key for p in fx.FxState().files[name].params}
    return {by_uniform[u] for (shader, u) in TIME_ALLOWLIST if shader == name and u in by_uniform}


EFFECTS = sorted(fx.FxState().files)


@pytest.mark.parametrize("name", EFFECTS)
def test_every_knob_of_every_effect_steps_the_same_an_hour_in(gl, name):
    """Each param's small step, late against early: no growth. A failure
    names the param and both sizes; the fix is the shader's — integrate a
    rate (`// @clock`) or add a time offset after the param scales the
    coordinate, never before."""
    report = effect_report(gl, fx.FxState(), name)
    bad = {k: (round(e, 3), round(l, 3)) for k, (e, l) in report.items()
           if grows(e, l, FX_FLOOR_PX) and k not in time_allowlisted(name)}
    assert not bad, f"{name}: a step lands further the longer the set runs " \
                    f"(key: (early px, late px)): {bad}"


# the harness's own proof, on effects written for it: what the lint
# cannot read (a time inside a builtin call, a param scaling the
# coordinate after), what it passes (a param scaling a bounded field)
LIB_SCALED = """// @label Scaled
// @speed 1
uniform float u_scale;  // @param 0.5 8 2 log "Scale"
vec4 effect(vec2 uv) {
    return src(fract((uv + vec2(mod(u_phase, 10000.0) * 0.001, 0.0)) * u_scale));
}
"""
LIB_FIXED = LIB_SCALED.replace(
    "fract((uv + vec2(mod(u_phase, 10000.0) * 0.001, 0.0)) * u_scale)",
    "fract(uv * u_scale + vec2(mod(u_phase, 10000.0) * 0.001, 0.0))")
LIB_BOUNDED = LIB_SCALED.replace(
    "fract((uv + vec2(mod(u_phase, 10000.0) * 0.001, 0.0)) * u_scale)",
    "fract((uv + 0.05 * vec2(sin(u_phase), cos(u_phase * 0.7))) * u_scale)")


@pytest.fixture()
def made(tmp_path):
    d = tmp_path / "fx"
    d.mkdir()
    shutil.copy(fx.FX_DIR / "_lib.glsl", d / "_lib.glsl")
    for n, text in (("scaled", LIB_SCALED), ("fixed", LIB_FIXED), ("bounded", LIB_BOUNDED)):
        (d / f"{n}.glsl").write_text(text)
    return d


def test_the_harness_sees_a_param_scaling_a_scrolled_coordinate_the_lint_cannot(gl, made):
    """`(uv + mod(u_phase, …) · 0.01) · u_scale`: the lint reads `mod(…)`
    as opaque and passes it; the harness measures the step and fails it.
    The time offset added after the scale (`uv · u_scale + …`) and a scale
    over a bounded wobble both pass."""
    from shader_lint import TIME_UNIFORMS, findings
    src = LIB_SCALED
    assert not findings(src, {"u_scale"}, set(TIME_UNIFORMS))       # invisible to the lint
    state = fx.FxState(made)
    early, late = effect_report(gl, state, "scaled", ["scale"])["scale"]
    assert grows(early, late, FX_FLOOR_PX), (early, late)
    assert late > 20 * early, (early, late)                          # not a near miss
    for name in ("fixed", "bounded"):
        e, l = effect_report(gl, fx.FxState(made), name, ["scale"])["scale"]
        assert not grows(e, l, FX_FLOOR_PX), (name, e, l)


# ---------------------------------------------------------------- the face patterns

@pytest.fixture(scope="module")
def tiles(gl):
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    r = Renderer(gl)
    assert r.pattern_error == ""

    def tile(mode: int, k: int, v: float, t: float) -> np.ndarray:
        mods = [1.0] * P.N_INPUTS
        mods[k] = v
        return r.pattern_tile(ViewState(pattern=mode, pattern_mod=mods), PATTERN_SIZE, t,
                              5.0).astype(float)
    return tile


def pattern_report(tile, mode: int) -> dict[str, tuple[float, float]]:
    """input name → (early, late): the mean change, levels, of a tenth of a
    detent up from the design (1.0) at `u_ptime` = each phase (SPEED is 1,
    so the tile's clock is the phase)."""
    out = {}
    up = 1.0 + PATTERN_DETENT * PATTERN_FRACTION
    for k, inp in enumerate(P.INPUTS):
        if k == P.SPEED:            # integrated by the renderer (_pattern_clock), tested there
            continue

        def at(t, k=k):
            return float(np.abs(tile(mode, k, up, t) - tile(mode, k, 1.0, t)).mean())
        out[inp.name] = (max(at(t) for t in EARLY), min(at(t) for t in LATE))
    return out


@pytest.mark.parametrize("mode", range(1, len(P.MODES)), ids=[m.name for m in P.MODES[1:]])
def test_every_input_of_every_pattern_steps_the_same_an_hour_in(tiles, mode):
    """The face patterns' clock is integrated (`u_ptime`), but a mode can
    still multiply it into a term an input scales — RINGS' colour did,
    `pal(ph · 0.15 · m_colour())` with `ph` carrying the clock, until K4."""
    report = pattern_report(tiles, mode)
    bad = {k: (round(e, 2), round(l, 2)) for k, (e, l) in report.items()
           if grows(e, l, PATTERN_FLOOR)}
    assert not bad, f"{P.MODES[mode].name}: an input's step grows with the clock " \
                    f"(input: (early levels, late levels)): {bad}"
