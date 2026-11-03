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
  the knob's value and at one step on, both with the clocks where the
  phase left them at the first value, so no frame's own motion is in it
  — a param the host integrates (`speed`, a `@clock`'s rate) moves nothing.
- **Small.** A hundredth of a detent for an effect (a whole one for an
  integer param), a tenth for a pattern input (the tile is 8-bit): small
  enough that a change of shape is a fraction of a pixel, while a phase
  carried by time is shifted by `phase × Δ` — whole screens an hour in.
  A detent is the registry's own (`Param.step`), one down from the top.
- **Early and late.** The early size is the largest over six phases from
  0.1 to 98 (a slow wave in the effect's own clock, acid's `sin(T / 143)`,
  has turned by then, so a shape change the clock modulates is seen at its
  full size); the late one the smaller of an hour and two hours.
- **The rule.** Late at most 4 × early + a floor (0.5 px of the 320 × 200
  field; 0.5 of 255 levels on a 64² pattern tile). A knob that changes a
  shape — glimmer's size, fractals' cells, wobble's frequency, kaleido's
  segments — changes it by the same amount whenever it moves, and passes
  however large that is; one whose change grows with the clock is twenty
  times its early size and more (warp's drift and scale, tripcolour's
  pulse and RINGS' colour before K4: see the PR).
- **Aux.** An effect with an aux input (displace, blend) reads a second
  picture there, the UV map turned half a turn (`uv_flow.uv_mirror`), so
  its knobs move the field; every other effect ignores it.
- **What it cannot see.** A rate under a sine that has wrapped by phase 98
  at a hundredth of a detent (a rate of more than ~6 rad a unit) — the
  lint's product rule catches those. A knob whose effect needs an aux
  that changes with time (the aux here is still), or another param far
  from its default and half the amounts (each knob is stepped alone, from
  the others' defaults). A choice param (a picker, not a knob) is never
  stepped itself; every knob is measured under each of its settings. The face patterns' SPEED (integrated by the renderer, tested in
  `test_patterns.py`).

The time lint's allowlist is not consulted: while a pair sits on it the
pair fails here too (its `stale` assertion, not this module, owns the
list). GL is the conftest's per-test `ctx`; every chain is released.
"""

from __future__ import annotations

import itertools
import shutil

import numpy as np
import pytest
import uv_flow

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
WALL_T0 = 100.0                                  # u_time where a speed of 0 leaves it


def grows(early: float, late: float, floor: float) -> bool:
    return late > FACTOR * early + floor


def declared(state: fx.FxState) -> Registry:
    """A registry with `state`'s effects declared on it: the knobs whose
    `Param.step` is the detent measured here, bound to `state.values`."""
    r = Registry()
    fx.declare(r, state)
    return r


# the shipped effects, read once for the module (collection and every test)
_SHIPPED = fx.FxState()
EFFECTS = sorted(_SHIPPED.files)


@pytest.fixture(scope="module")
def shipped() -> tuple[fx.FxState, Registry]:
    """The shipped effects declared once for the module (no GL: each test
    makes its chain on its own `ctx` and releases it). Every test leaves
    the values as it found them."""
    return _SHIPPED, declared(_SHIPPED)


# ---------------------------------------------------------------- effects

def detent(r: Registry, state: fx.FxState, name: str, key: str) -> tuple[float, float]:
    """`key`'s value and one detent on, by the registry's own `Param.step`
    (the taper, log or linear, wrapped or not) — one down from the top,
    where a step up is a no-op. Leaves the value as it found it."""
    v = state.values[name]
    par = r[f"fx.{name}.{key}"]
    before = v[key]
    par.step(1)
    if v[key] == before:
        par.step(-1)
    after = v[key]
    v[key] = before
    return before, after


def small_step(r: Registry, state: fx.FxState, name: str, key: str,
               fraction: float = FX_FRACTION) -> tuple[float, float]:
    """`key`'s value and a `fraction` of one detent on (`detent`); a whole
    detent for an integer."""
    before, after = detent(r, state, name, key)
    p = next((p for p in state.specs[name].params if p.key == key), None)
    if p is not None and p.integer:
        return before, after
    d = after - before
    if p is not None and p.wrap and abs(d) > (p.hi - p.lo) / 2:    # stepped over the seam
        d -= np.sign(d) * (p.hi - p.lo)
    return before, before + d * fraction


def wall(phase: float, speed: float) -> float:
    """The wall time (`u_time`) at which `phase` stands at `speed`: the
    same set, so a `u_time × param` product is as late as the phase; at
    speed 0 the phase never moved, and the wall clock is `WALL_T0`."""
    return phase / abs(speed) if speed else WALL_T0


def effect_report(ctx, state: fx.FxState, r: Registry, name: str,
                  keys=None) -> dict[str, list[tuple[float, float]]]:
    """key → [(early, late)] step sizes, px, one pair per setting of the
    effect's choices, for effect `name` on `state`
    (declared on `r`): every amount-type param but the one stepped at half
    its range, so the effect shows (their defaults are calm: PR #304); a
    second picture on the aux input (`uv_flow.uv_mirror`)."""
    spec = state.specs[name]
    v = state.values[name]
    rest = dict(v)
    keys = keys or ["speed", *[p.key for p in spec.params if not p.choices]]
    chain = fx.FxChain(ctx, state)
    aux = ctx.texture((uv_flow.W, uv_flow.H), 4, dtype="f2")
    out = {}
    try:
        (src, _), (_, dst) = chain.pool((uv_flow.W, uv_flow.H))
        src.write(uv_flow.uv_source().tobytes())
        aux.write(uv_flow.uv_mirror().tobytes())
        choices = [p for p in spec.params if p.choices]
        for key in keys:
            # under every setting of the effect's choices (a knob may act
            # in one mode only: blend's key is the luma key's)
            for pick in itertools.product(*(range(len(c.choices)) for c in choices)):
                v.clear()
                v.update(rest)
                v.update({p.key: p.hi / 2 for p in spec.params if p.amount and p.key != key})
                v.update({c.key: i for c, i in zip(choices, pick, strict=True)})
                v.update(on=True, mix=1.0)
                a, b = small_step(r, state, name, key)
                speed = v["speed"]
                e = max(uv_flow.jump(chain, src, dst, name, key, a, b, ph, wall(ph, speed), aux)
                        for ph in EARLY)
                l = min(uv_flow.jump(chain, src, dst, name, key, a, b, ph, wall(ph, speed), aux)
                        for ph in LATE)
                out.setdefault(key, []).append((e, l))
        assert not chain.errors, chain.errors
    finally:
        v.clear()
        v.update(rest)
        aux.release()
        chain.release()
    return out


def test_a_knob_at_its_top_is_measured_one_detent_down(shipped):
    """`detent` is one detent everywhere: up one, or down one from the top
    (fade's level, palette's ends and its anchors sit there by default) —
    never two."""
    state, r = shipped
    fade = state.specs["fade"].params[0]
    assert fade.key == "level" and state.values["fade"]["level"] == fade.hi
    assert detent(r, state, "palette", "anchors") == (4, 3)
    for name, spec in state.specs.items():
        for p in spec.params:
            if p.choices:
                continue
            par = r[f"fx.{name}.{p.key}"]
            before, after = detent(r, state, name, p.key)
            k0 = par.position()
            state.values[name][p.key] = after
            k1 = par.position()
            state.values[name][p.key] = before
            assert (k1 - k0) % par.steps in (1, par.steps - 1), (name, p.key, before, after)


@pytest.mark.parametrize("name", EFFECTS)
def test_every_knob_of_every_effect_steps_the_same_an_hour_in(ctx, shipped, name):
    """Each param's small step, late against early: no growth. A failure
    names the param and both sizes; the fix is the shader's — integrate a
    rate (`// @clock`) or add a time offset after the param scales the
    coordinate, never before."""
    state, r = shipped
    report = effect_report(ctx, state, r, name)
    bad = {k: [(round(e, 3), round(l, 3)) for e, l in pairs if grows(e, l, FX_FLOOR_PX)]
           for k, pairs in report.items()}
    bad = {k: x for k, x in bad.items() if x}
    assert not bad, f"{name}: a step lands further the longer the set runs " \
                    f"(key: (early px, late px)): {bad}"


@pytest.mark.parametrize("name, keys", [("displace", ["amount", "angle"]),
                                        ("blend", ["key", "soft"])])
def test_an_aux_effects_knobs_are_measured_through_its_aux(ctx, shipped, name, keys):
    """With nothing on the aux input displace and blend draw their input
    through, and every step reads zero: the harness wires the turned UV
    map in, so each knob's step is seen (and then held to the rule)."""
    state, r = shipped
    report = effect_report(ctx, state, r, name, keys)
    assert all(any(e > 0.0 and l > 0.0 for e, l in pairs) for pairs in report.values()), report


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
    for n, text in (("scaled", LIB_SCALED), ("fixed", LIB_FIXED), ("bounded", LIB_BOUNDED),
                    ("clocked", LIB_CLOCKED)):
        (d / f"{n}.glsl").write_text(text)
    return d


# a scroll on a `@clock`: the rate is integrated by the host
LIB_CLOCKED = """// @label Clocked
// @speed 1
// @clock u_scroll rate
uniform float u_rate;  // @param 0 8 3 "Rate"
vec4 effect(vec2 uv) { return src(fract(uv + vec2(u_scroll * 0.01, 0.0))); }
"""


def test_a_clock_stands_where_the_hour_left_it_and_its_rate_step_moves_nothing(ctx, made):
    """`uv_flow.stand` puts a `@clock` at phase × its rate (as `uv_flow.run`
    seeds it), and `jump` stands the clocks once, at the first value: a
    step of the integrated rate changes no pixel at any hour."""
    state = fx.FxState(made)
    state.values["clocked"]["rate"] = 3.0
    uv_flow.stand(state, "clocked", 100.0)
    assert state.phase["clocked"] == 100.0
    assert state.clocks["clocked"]["u_scroll"] == pytest.approx(300.0)
    r = declared(state)
    [(early, late)] = effect_report(ctx, state, r, "clocked", ["rate"])["rate"]
    assert early == late == 0.0


def test_the_harness_sees_a_param_scaling_a_scrolled_coordinate_the_lint_cannot(ctx, made):
    """`(uv + mod(u_phase, 1e4) · 0.001) · u_scale`: the lint reads `mod(…)`
    as opaque and passes it; the harness measures the step and fails it —
    not a near miss: late is past twice the rule's bound (4 · early + 0.5),
    a margin of the rule's own, since the bare ratio depends on the driver
    (17× on Mesa's llvmpipe, more on the Mac).
    The time offset added after the scale (`uv · u_scale + …`) and a scale
    over a bounded wobble both pass."""
    from shader_lint import TIME_UNIFORMS, findings
    assert not findings(LIB_SCALED, {"u_scale"}, set(TIME_UNIFORMS))   # invisible to the lint
    state = fx.FxState(made)
    r = declared(state)
    [(early, late)] = effect_report(ctx, state, r, "scaled", ["scale"])["scale"]
    assert grows(early, late, FX_FLOOR_PX), (early, late)
    bound = FACTOR * early + FX_FLOOR_PX
    assert late > 2 * bound, (early, late, bound)                    # not a near miss
    for name in ("fixed", "bounded"):
        [(e, l)] = effect_report(ctx, state, r, name, ["scale"])["scale"]
        assert not grows(e, l, FX_FLOOR_PX), (name, e, l)


# ---------------------------------------------------------------- the face patterns

def pattern_ups(tmp_path) -> list[float]:
    """Each pattern input's value a `PATTERN_FRACTION` of one detent up from
    the design (1.0): the detent the registry's own `pattern.mod.<k>`
    steps (`Param.step`), on a registry built as the app builds it."""
    from test_params import make

    reg, view = make(tmp_path)[:2]
    ups = []
    for k in range(P.N_INPUTS):
        view.pattern_mod[k] = 1.0
        reg[f"pattern.mod.{k}"].step(1)
        ups.append(1.0 + (view.pattern_mod[k] - 1.0) * PATTERN_FRACTION)
        view.pattern_mod[k] = 1.0
    return ups


def pattern_report(tile, mode: int, ups: list[float]) -> dict[str, tuple[float, float]]:
    """input name → (early, late): the mean change, levels, of `ups[k]`
    against the design (1.0) at `u_ptime` = each phase (SPEED is 1, so the
    tile's clock is the phase)."""
    def at(k: int, t: float) -> float:
        return float(np.abs(tile(mode, k, ups[k], t) - tile(mode, k, 1.0, t)).mean())
    return {inp.name: (max(at(k, t) for t in EARLY), min(at(k, t) for t in LATE))
            for k, inp in enumerate(P.INPUTS)
            if k != P.SPEED}        # integrated by the renderer (_pattern_clock), tested there


def test_every_input_of_every_pattern_steps_the_same_an_hour_in(ctx, tmp_path):
    """The face patterns' clock is integrated (`u_ptime`), but a mode can
    still multiply it into a term an input scales — RINGS' colour did,
    `pal(ph · 0.15 · m_colour())` with `ph` carrying the clock, until K4.
    One test and one Renderer on the test's own `ctx` (conftest: a
    Renderer has no release, so it lives exactly as long as the context)."""
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    ups = pattern_ups(tmp_path)
    assert all(1.0 < u < 1.01 for u in ups), ups     # a tenth of a detent of 0 … 2.6
    r = Renderer(ctx)
    assert r.pattern_error == ""

    def tile(mode: int, k: int, v: float, t: float) -> np.ndarray:
        mods = [1.0] * P.N_INPUTS
        mods[k] = v
        return r.pattern_tile(ViewState(pattern=mode, pattern_mod=mods), PATTERN_SIZE, t,
                              5.0).astype(float)
    bad = {f"{P.MODES[mode].name} {k}": (round(e, 2), round(l, 2))
           for mode in range(1, len(P.MODES))
           for k, (e, l) in pattern_report(tile, mode, ups).items()
           if grows(e, l, PATTERN_FLOOR)}
    assert not bad, "an input's step grows with the clock " \
                    f"(mode input: (early levels, late levels)): {bad}"
