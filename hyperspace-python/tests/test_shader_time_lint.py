"""No shader multiplies time by a param (the owner, 2026-11-02; register
row 560): the lint over every shipped shader, and the lint's own tests.

`tests/shader_lint.py` is the detector; the rule, and why `u_phase *
u_drift` is a jump, are in its docstring and DECISIONS "Effects and the
look-back". A rate-like param is integrated by the host instead: an
effect's `// @clock` (fx.py), the patterns' `u_ptime`
(`Renderer._pattern_clock`).

The allowlist below is today's offenders, found by this lint on
2026-11-02, as exact (shader, param) pairs: a new product anywhere fails,
and so does a stale entry once its shader is ported. K2 (row 577) took
out warp's drift and scale and tripcolour's pulse; K4 (the RINGS
pattern's hue) shrinks it to empty.
"""

from __future__ import annotations

import pytest
from shader_lint import TIME_UNIFORMS, findings

from hyperspace import render as R
from hyperspace.fx import FxState, parse

# ---------------------------------------------------------------- the allowlist

# (shader, param symbol) → why it is still there. Shrinks to {} with K4
# (K2 ported warp and tripcolour, register row 577).
ALLOWLIST: dict[tuple[str, str], str] = {
    ("patterns", "m_colour"): "K4: RINGS' `pal(ph * 0.15 * m_colour() …)` — `ph` carries u_ptime",
}

# the patterns' param symbols: a mode reads its inputs only through these
# (tests/test_patterns.py holds that), so the finding names the input
PATTERN_ACCESSORS = {"m_scale", "m_glow", "m_warp", "m_speed", "m_colour", "m_sharp", "m_hue",
                     "m_spread"}
PATTERN_PROGRAMS = {
    "face": (R.FACE_FS_HEAD, R.FACE_FS_TAIL),
    "seed": (R.SEED_FS_HEAD, R.SEED_FS_TAIL),
    "tile": (R.TILE_FS_HEAD, R.SEED_FS_TAIL),
}


def effect_pairs(name: str, source: str) -> set[tuple[str, str]]:
    """The (effect, param uniform) products in one effect file: its @param
    uniforms are the params; u_time, u_phase and its @clock uniforms are
    the times. No exemption: a param a `@clock` integrates multiplied into
    `u_phase` again is the show's bug come back (K2 left nothing
    mid-port), and `u_drift_t * u_drift` is the rate applied twice."""
    spec = parse(name, source)
    params = {p.uniform for p in spec.params}
    times = set(TIME_UNIFORMS) | {c.uniform for c in spec.clocks}
    return {(name, p) for f in findings(source, params, times) for p in f.params}


def pattern_pairs() -> set[tuple[str, str]]:
    """The products in the face programs as render.py assembles them
    around patterns.glsl (the face, the seed, the tile)."""
    src = R.PATTERNS_GLSL.read_text()
    out: set[tuple[str, str]] = set()
    for head, tail in PATTERN_PROGRAMS.values():
        full = R._face_fragment(head, src, tail)
        out |= {("patterns", p) for f in findings(full, PATTERN_ACCESSORS) for p in f.params}
    return out


def test_no_shipped_shader_multiplies_time_by_a_param_beyond_the_allowlist():
    """Every effect file and the patterns, against the allowlist exactly:
    a new product is a failure (port it or integrate it with `@clock`); a
    pair no shader has any more is a stale entry to delete."""
    found: set[tuple[str, str]] = set()
    for name, spec in FxState().files.items():
        found |= effect_pairs(name, spec.source)
    found |= pattern_pairs()
    new = found - set(ALLOWLIST)
    stale = set(ALLOWLIST) - found
    assert not new, f"a shader multiplies time by a param: {sorted(new)} — integrate it (@clock)"
    assert not stale, f"ported: delete from ALLOWLIST: {sorted(stale)}"


# ---------------------------------------------------------------- the lint itself

HEAD = 'uniform float u_a; // @param 0 1 0.5 "A"\nuniform float u_b; // @param 0 1 0.5 "B"\n'


def pairs(body: str, clocks: str = "") -> set[str]:
    src = f"{clocks}{HEAD}vec4 effect(vec2 uv) {{\n{body}\nreturn src(uv);\n}}\n"
    return {p for _, p in effect_pairs("t", src)}


@pytest.mark.parametrize("body, want", [
    ("float t = u_phase * u_a;", {"u_a"}),                      # the direct product
    ("float t = u_a * u_phase;", {"u_a"}),                      # either side
    ("float t = u_time * u_b;", {"u_b"}),                       # the wall clock too
    ("float t = u_phase / u_a;", {"u_a"}),                      # a division is a rate
    ("float t = u_phase; t *= u_a;", {"u_a"}),                  # a compound product
    ("float r = u_a; r *= u_phase;", {"u_a"}),                  # … with the param on the left
    ("float r = u_a; r /= u_phase;", set()),                    # a param over time is no rate
    ("#define K (u_a * 2.0)\nfloat x = u_phase * K;", {"u_a"}),  # an object-like macro, expanded
    ("switch (int(u_b)) { case 1: { float t = u_phase * u_a; } break; default: break; }",
     {"u_a"}),                                                  # inside a switch
    ("float x; switch (int(u_b)) { case 0: x = u_phase * u_a; break; case 1: x = 1.0; }",
     {"u_a"}),
    ("float t = u_phase * 20.0; float x = sin(t * u_a);", {"u_a"}),    # through an alias
    ("float t = u_phase; vec2 p = (uv + vec2(t) * 0.1) * u_a;", {"u_a"}),  # a constructor is glass
    ("float r = u_a * 2.0; float x = u_phase * r;", {"u_a"}),  # a param alias too
    ("float t = u_phase * u_a; vec2 p = (uv + t) * u_b;", {"u_a", "u_b"}),  # warp's shape
    ("float x = u_a * sin(u_phase);", set()),                   # an amplitude, bounded
    ("float x = u_phase * 0.05 + u_a;", set()),                 # a phase offset
    ("float x = mod(u_phase, u_a);", set()),                    # a wrap
    ("float x = u_phase * TAU; float y = sin(uv.x * u_a + x);", set()),  # a constant rate
    ("vec2 h = hash22(uv); float x = sin(u_phase * (1.5 + h.y));", set()),  # a hash, no param
    ("float x = u_a * u_b;", set()),                            # no time at all
])
def test_the_lint_finds_a_product_of_time_and_a_param_and_nothing_else(body, want):
    assert pairs(body) == want


def test_products_through_a_user_function_are_found():
    """A formal parameter takes its call sites' taint (fractals' `shape(uv,
    T)`), and a function's result carries what it returns."""
    src = (HEAD + "float shape(vec2 p, float T) { return cos(p.x + T * u_a); }\n"
           "float clock() { return u_phase * 2.0; }\n"
           "vec4 effect(vec2 uv) { float T = u_phase; float s = shape(uv, T);"
           " float c = clock() * u_b; return src(uv) * s * c; }\n")
    assert {p for _, p in effect_pairs("t", src)} == {"u_a", "u_b"}


def test_a_clock_uniform_is_a_time_and_nothing_is_exempt():
    """`@clock u_t a`: `u_t * u_b` is a product of a time (the clock) and a
    param — found; `u_phase * u_a` is the show's bug even though the host
    integrates `a` too — found; `u_t * u_a` is the rate applied twice (the
    porting mistake) — found."""
    clock = "// @clock u_t a\n"
    assert pairs("vec2 p = uv + vec2(u_t) * 0.1;", clock) == set()
    assert pairs("vec2 p = uv + vec2(u_t * u_b) * 0.1;", clock) == {"u_b"}
    assert pairs("float t = u_phase * u_a;", clock) == {"u_a"}
    assert pairs("float t = u_time * u_a;", clock) == {"u_a"}
    assert pairs("float t = u_phase * u_b;", clock) == {"u_b"}
    assert pairs("vec2 p = uv + vec2(u_t * u_a) * 0.1;", clock) == {"u_a"}
    assert pairs("float t = u_t; t *= u_a;", clock) == {"u_a"}
    assert pairs("float t = (u_phase + u_t) * u_a;", clock) == {"u_a"}


def test_a_ported_shader_that_brings_the_product_back_is_flagged():
    """Warp and tripcolour as K2 left them, with the old line put back
    beside the clock: every factor of the clock's rate is found again."""
    files = FxState().files
    warp = files["warp"].source
    assert effect_pairs("warp", warp) == set()
    back = warp.replace("vec2 p = centred(uv);",
                        "vec2 p = centred(uv);\n    float t = u_phase * u_drift;\n"
                        "    p += vec2(t) * 0.1 * u_scale;")
    assert back != warp
    assert effect_pairs("warp", back) == {("warp", "u_drift"), ("warp", "u_scale")}
    trip = files["tripcolour"].source
    assert effect_pairs("tripcolour", trip) == set()
    pulse = trip.replace("sin(u_pulse_t)", "sin(u_phase * u_pulse)")
    assert pulse != trip
    assert effect_pairs("tripcolour", pulse) == {("tripcolour", "u_pulse")}


def test_a_function_with_a_precision_qualifier_is_a_function():
    """`highp float f(…)` is read as a function (its body checked, its
    formals tainted by the call), not skipped as a statement."""
    src = (HEAD + "highp float scaled(float x) { return x * u_a; }\n"
           "vec4 effect(vec2 uv) { float y = scaled(u_phase); return src(uv) * y; }\n")
    assert {p for _, p in effect_pairs("t", src)} == {"u_a"}


def test_a_function_like_macro_naming_a_param_or_a_time_fails_the_lint():
    """The lint expands object-like macros and refuses function-like ones
    that touch a time or a param: write those as a GLSL function, which it
    can read (a preprocessor with argument substitution is not worth
    carrying for shaders we write ourselves)."""
    from shader_lint import LintError
    with pytest.raises(LintError, match="RATE"):
        pairs("#define RATE(x) ((x) * u_a)\nfloat t = RATE(u_phase);")
    with pytest.raises(LintError, match="AT"):
        pairs("#define AT(x) (u_phase * (x))\nfloat t = AT(2.0);")
    assert pairs("#define HALF(x) ((x) * 0.5)\nfloat t = HALF(u_phase) + u_a;") == set()


def test_the_lint_reads_every_shipped_effect_through_to_the_end():
    """The detector saw each file whole: every `effect` body and every
    helper function was parsed (a construct it skipped would hide a
    product), checked by the tokens' last line reaching the file's."""
    from shader_lint import _functions, tokenize
    for name, spec in FxState().files.items():
        toks = tokenize(spec.source)
        funcs, _ = _functions(toks)
        assert "effect" in funcs, name
        assert toks[-1].line == len(spec.source.rstrip("\n").split("\n")), name
