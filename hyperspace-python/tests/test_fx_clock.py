"""`// @clock`: a rate-like param integrated by fx.py (register row 560),
and the UV-field continuity harness (`tests/uv_flow.py`) that shows why.

The parse and the state run anywhere; the GL half needs a standalone
context and skips without one. Nothing shipped is ported here (K2–K4 do
that): the harness is proven on a synthetic effect and its twin, on
warp's speed (integrated today — passes) and on warp's drift (multiplied
in the shader — the expected failure K2 turns into a pass).
"""

from __future__ import annotations

import math
import os
import shutil
import time

import numpy as np
import pytest
import uv_flow

from hyperspace.fx import (
    FX_DIR,
    HEAD_UNIFORMS,
    ClockSpec,
    FxChain,
    FxState,
    SpecError,
    fragment_source,
    parse,
)

# warp at an amount that shows: its default 0.2 moves the field ~2 px at most
WARP_SEEN = {"amount": 2.0}

# a scroll: the frame slides along x at `rate` screens a second (× speed)
CLOCKED = """// @label Scroll
// @speed 1
// @clock u_scroll rate
uniform float u_rate;    // @param 0 8 1 "Rate" screens a second
uniform float u_gain;    // @param 0 2 1 "Gain"
vec4 effect(vec2 uv) { return src(uv + vec2(u_scroll * 0.1, 0.0)) * u_gain; }
"""
# the same look written the old way: the shader multiplies the phase
TWIN = CLOCKED.replace("// @clock u_scroll rate\n", "").replace("u_scroll", "u_phase * u_rate")
WRAPPED = """// @label Pulse
// @clock u_beat rate tau
uniform float u_rate;    // @param 0 8 1 "Rate"
vec4 effect(vec2 uv) { return src(uv) * (0.5 + 0.5 * sin(u_beat)); }
"""


def write(d, name, text):
    (d / f"{name}.glsl").write_text(text)
    t = time.time() + len(list(d.iterdir()))
    os.utime(d / f"{name}.glsl", (t, t))


@pytest.fixture()
def fxdir(tmp_path):
    d = tmp_path / "fx"
    d.mkdir()
    shutil.copy(FX_DIR / "_lib.glsl", d / "_lib.glsl")
    write(d, "scroll", CLOCKED)
    write(d, "twin", TWIN)
    write(d, "pulse", WRAPPED)
    return d


# ---------------------------------------------------------------- the directive

def test_parse_reads_a_clock():
    s = parse("scroll", CLOCKED)
    assert s.clocks == [ClockSpec(uniform="u_scroll", rate="rate", period=None)]
    assert [p.key for p in s.params] == ["rate", "gain"]      # a clock declares no param
    assert parse("pulse", WRAPPED).clocks == [ClockSpec("u_beat", "rate", math.tau)]
    # the rate may be written as its uniform; a period as a number
    s = parse("x", "// @clock u_t u_rate 1.0\n" + WRAPPED.replace("// @clock u_beat rate tau\n", ""))
    assert s.clocks == [ClockSpec("u_t", "rate", 1.0)]


@pytest.mark.parametrize("line, why", [
    ("// @clock u_t", "wants <u_uniform> <rate-param>"),
    ("// @clock u_t rate 1 2", "wants <u_uniform> <rate-param>"),
    ("// @clock t rate", "u_lower_snake"),
    ("// @clock u_phase rate", "already has it"),
    ("// @clock u_time rate", "already has it"),
    ("// @clock u_t nope", "no @param of this file"),
    ("// @clock u_t speed", "no @param of this file"),       # speed is u_phase's already
    ("// @clock u_rate rate", "taken"),                        # a param's uniform
    ("// @clock u_t rate\n// @clock u_t gain", "taken"),       # twice
    ("// @clock u_t rate 0", "> 0"),
    ("// @clock u_t rate -1", "> 0"),
    ("// @clock u_t rate inf", "finite"),                       # `x %= inf` is inf for x < 0
    ("// @clock u_t rate 1e999", "finite"),
    ("// @clock u_t rate nan", "finite"),
    ("// @clock u_t rate soon", "bad period"),
])
def test_parse_refuses_a_bad_clock(line, why):
    src = CLOCKED.replace("// @clock u_scroll rate", line).replace("u_scroll", "u_t")
    with pytest.raises(SpecError, match=why):
        parse("scroll", src)


def test_the_file_may_not_declare_the_clocks_uniform():
    src = CLOCKED.replace("uniform float u_gain;", "uniform float u_scroll;\nuniform float u_gain;")
    with pytest.raises(SpecError, match="leave the uniform undeclared"):
        parse("scroll", src)
    # a declaration in the code, not on a @param line, is still one
    src = CLOCKED.replace("vec4 effect", "uniform float u_scroll;\nvec4 effect")
    with pytest.raises(SpecError, match="leave the uniform undeclared"):
        parse("scroll", src)
    # a comment that mentions the declaration is not one
    src = CLOCKED.replace("vec4 effect", "// fx.py adds `uniform float u_scroll;` for us\n"
                          "/* as if uniform float u_scroll; */\nvec4 effect")
    assert parse("scroll", src).clocks[0].uniform == "u_scroll"


def test_a_rate_written_as_a_key_wins_over_a_uniform_of_that_spelling():
    """A @param key may itself start with `u_` (`uniform float u_u_rate;`
    is key `u_rate`): the rate word is resolved against the keys first,
    then the uniforms, never by stripping a prefix."""
    src = CLOCKED.replace("uniform float u_rate;", "uniform float u_u_rate;")
    by_key = src.replace("// @clock u_scroll rate", "// @clock u_scroll u_rate")
    assert parse("scroll", by_key).clocks[0].rate == "u_rate"           # the key, as is
    by_uniform = src.replace("// @clock u_scroll rate", "// @clock u_scroll u_u_rate")
    assert parse("scroll", by_uniform).clocks[0].rate == "u_rate"       # the uniform → its key
    both = src.replace("uniform float u_gain;", 'uniform float u_gain;\n'
                       'uniform float u_u_u_rate;  // @param 0 1 0 "Deep"')
    # `u_u_rate` names key u_u_rate (the deeper uniform's) before uniform u_u_rate
    assert parse("scroll", both.replace("// @clock u_scroll rate",
                                        "// @clock u_scroll u_u_rate")).clocks[0].rate == "u_u_rate"
    with pytest.raises(SpecError, match="no @param"):
        parse("scroll", src.replace("// @clock u_scroll rate", "// @clock u_scroll rate_"))


def test_a_clock_is_declared_in_the_head_and_changes_the_signature():
    s = parse("scroll", CLOCKED)
    src = fragment_source("", s.source, "", s.clocks)
    head = src.split("#line 1 1")[0]
    assert "uniform float u_scroll;" in head and "uniform float u_phase;" in head
    assert fragment_source("", s.source, "") == src.replace(
        "uniform float u_scroll;   // @clock: integrated by fx.py\n", "")
    assert s.signature() != parse("scroll", TWIN).signature()
    assert "u_phase" in HEAD_UNIFORMS and "u_src" in HEAD_UNIFORMS


# ---------------------------------------------------------------- the state

def test_the_clock_integrates_speed_times_rate_and_wraps_to_its_period(fxdir):
    st = FxState(fxdir)
    assert st.clocks == {"scroll": {"u_scroll": 0.0}, "twin": {}, "pulse": {"u_beat": 0.0}}
    st.values["scroll"].update(speed=2.0, rate=3.0)
    st.values["pulse"].update(speed=1.0, rate=4.0)
    st.advance(0.5)
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(3.0)        # 0.5 × 2 × 3
    assert st.phase["scroll"] == pytest.approx(1.0)                     # u_phase as before
    assert st.clocks["pulse"]["u_beat"] == pytest.approx(2.0)
    st.values["scroll"]["rate"] = 0.0                                   # a stilled rate holds
    st.values["pulse"]["rate"] = 8.0
    st.advance(0.5)
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(3.0)
    assert st.clocks["pulse"]["u_beat"] == pytest.approx((2.0 + 4.0) % math.tau)
    st.values["pulse"]["rate"] = -20.0                                  # backwards wraps too
    st.advance(0.5)
    assert 0.0 <= st.clocks["pulse"]["u_beat"] < math.tau


def test_a_knob_step_changes_the_rate_and_never_the_phase(fxdir):
    """The point of the directive, in numbers: the phase after a step is
    where it was plus the new rate × dt — no `phase × Δrate` term."""
    st = FxState(fxdir)
    st.values["scroll"]["rate"] = 1.0
    for _ in range(600):
        st.advance(1 / 60)
    before = st.clocks["scroll"]["u_scroll"]
    assert before == pytest.approx(10.0)
    st.values["scroll"]["rate"] = 1.1
    st.advance(1 / 60)
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(before + 1.1 / 60)
    # the twin's shader reads u_phase × rate: the same step moves it by phase × 0.1
    assert st.phase["twin"] * 1.1 - st.phase["twin"] * 1.0 == pytest.approx(1.0, abs=0.01)


def test_an_edit_keeps_a_clock_it_keeps_and_forgets_one_it_drops(fxdir):
    st = FxState(fxdir)
    st.values["scroll"]["rate"] = 1.0
    st.advance(1.0)
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(1.0)
    write(fxdir, "scroll", CLOCKED.replace('"Gain"', '"Loudness"'))     # the clock stays
    assert st.poll() == {"scroll"}
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(1.0)
    write(fxdir, "scroll", CLOCKED.replace("u_scroll", "u_slide"))      # renamed: starts over
    st.poll()
    assert st.clocks["scroll"] == {"u_slide": 0.0}
    (fxdir / "scroll.glsl").unlink()                                   # gone: forgotten
    st.poll()
    assert "scroll" not in st.clocks and "scroll" not in st.values


def test_an_instance_has_its_own_clock(fxdir):
    st = FxState(fxdir)
    st.set_instances({"scroll": 2})
    st.values["scroll"]["rate"] = 1.0
    st.values["scroll.2"]["rate"] = 2.0
    st.advance(1.0)
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(1.0)
    assert st.clocks["scroll.2"]["u_scroll"] == pytest.approx(2.0)
    st.set_instances({})
    assert "scroll.2" not in st.clocks


def test_the_clocks_survive_a_hot_reload_of_fx(fxdir):
    """An FxState built before this module gained `clocks` has no dict:
    `_clocks` makes it on first use, so a reload mid-set keeps every speed
    phase and starts the new clocks at 0 — never an AttributeError on the
    frame."""
    st = FxState(fxdir)
    st.values["scroll"]["rate"] = 1.0
    del st.clocks
    st.advance(0.5)
    assert st.clocks == {"scroll": {"u_scroll": 0.5}, "pulse": {"u_beat": 0.5}}
    old = FxState(fxdir)
    del old.clocks
    assert old.load() == set()                                        # a reload re-reads
    old.advance(0.0)                                                  # the first frame makes it
    assert old.clocks == {"scroll": {"u_scroll": 0.0}, "pulse": {"u_beat": 0.0}}


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


def test_the_clock_reaches_the_shader(ctx, fxdir):
    """The uniform fx.py declares is bound each pass: a scroll of 0.25
    screens reads the source a quarter of the way along."""
    st = FxState(fxdir)
    st.values["scroll"].update(on=True, rate=1.0)
    chain = FxChain(ctx, st)
    assert chain.compile_all() == {}
    (src, _), (_, dst) = chain.pool((uv_flow.W, uv_flow.H))
    src.write(uv_flow.uv_source().tobytes())
    chain.run_one("scroll", src, dst, 1.0)
    chain.run_one("scroll", src, dst, 3.5)                            # dt is clamped to 0.25
    chain.run_one("scroll", src, dst, 3.75)                           # … twice: 0.5 s at rate 1
    assert st.clocks["scroll"]["u_scroll"] == pytest.approx(0.5)
    field = uv_flow.decode(dst.read(components=4, dtype="f2"))
    # a scroll of 0.05 screens: each pixel sampled 16 px to its right
    middle = field[uv_flow.H // 2, 40:200, 0] - (np.arange(40, 200) + 0.5)
    assert np.allclose(middle, 0.05 * uv_flow.W, atol=0.5)
    chain.release()


def test_a_clocked_rate_step_is_continuous_and_the_twins_jumps(ctx, fxdir):
    """The harness on the synthetic pair, an hour in: the `@clock` scroll
    moves on at the new rate; the twin, whose shader multiplies u_phase by
    the rate, lands somewhere else on the step frame."""
    clocked = uv_flow.run(ctx, FxState(fxdir), "scroll", "rate", 1.0, 1.1)
    twin = uv_flow.run(ctx, FxState(fxdir), "twin", "rate", 1.0, 1.1)
    assert clocked.continuous(), clocked
    assert clocked.rest and max(clocked.rest) < 1.0                   # ~0.5 px a frame
    # the negative, measured here and only here: the twin's still frames
    # drift under a pixel, its step frame is a jump of many screens
    assert not twin.continuous(), twin
    assert max(twin.rest) < 1.0 and max(twin.after) < 1.0, twin
    assert twin.step > 20 * twin.bound(), twin                        # not a near miss


def test_warps_speed_step_is_continuous(ctx):
    """Today's integrated effect clock passes the harness: stepping warp's
    speed 1 → 2 an hour in moves the field no further than its drift."""
    r = uv_flow.run(ctx, FxState(), "warp", "speed", 1.0, 2.0, values=WARP_SEEN)
    assert r.continuous(), r
    assert r.step < 1.0, r                                            # ~0.36 px: the drift, doubled


@pytest.mark.xfail(strict=True, reason="K2 ports warp and tripcolour to @clock: until then the "
                   "shader multiplies u_phase by the param and a knob step lands the field "
                   "somewhere else")
@pytest.mark.parametrize("effect, param, before, after, values", [
    ("warp", "drift", 1.0, 1.1, WARP_SEEN),          # ~15 px on the step, 0.05 px a frame between
    ("warp", "scale", 3.0, 3.3, WARP_SEEN),          # scale multiplies the scrolled offset: the same
    ("tripcolour", "pulse", 1.5, 1.6, {}),           # a colour effect: the decoded green jumps
])
def test_the_allowlisted_rate_params_step_continuously(ctx, effect, param, before, after,
                                                        values):
    """The show's bug, measured on each pair the lint's allowlist names
    for K2: a small step an hour in should move the field no further than
    its drift. Strict xfail: a port flips each case to a pass with no
    edit here but deleting the mark (and its allowlist entry)."""
    r = uv_flow.run(ctx, FxState(), effect, param, before, after, values=values)
    assert r.continuous(), r
