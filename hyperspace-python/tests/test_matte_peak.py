"""Plan 90 (H2, Q23): Matte gains Key's `peak` measure and its `linear` ramp.

One measure list and one ramp for the two (plan 67 §3.11: "one key: measure,
then threshold") — the GLSL that measures a pixel and ramps it is written once
(`glsl.KEY_SHAPE`) and read by Key's pass (`glsl.KEY_RAMP`) and Matte's
(`masks.MATTE_FS`). Appended choices: a saved `matte.from` 0–2 and every matte
without a `ramp` draw as they did. The look-back's occluder, `min(4 · peak, 1)`,
is a Matte on peak, linear, key ⅛, soft ⅛ (plan 90 §10.2)."""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_faces import Still, _media
from test_graph_masks import _draw, _mask, _mask_px, _ramp, _renderer

from hyperspace import glsl, masks, params, view
from hyperspace.view import MatteState, ViewState


def test_matte_from_appends_peak():
    assert view.MATTE_FROM == ("luma", "alpha", "chroma", "peak")
    assert masks.PEAK == 3


def test_matte_takes_the_keys_ramps():
    assert MatteState().ramp == 0
    reg = params.Registry()
    params.declare_mattes(reg, ["matte"])
    assert reg["matte.from"].choices == list(view.MATTE_FROM)
    assert reg["matte.ramp"].choices == list(view.KEY_RAMPS) == ["smooth", "linear"]
    reg["matte.ramp"].set(1)
    assert reg.matte_state["matte"].ramp == 1
    assert params.is_matte_id("matte.2.ramp")


def test_key_and_matte_share_one_measure_and_one_ramp():
    # (written once: both passes carry the same text, neither its own copy)
    assert glsl.KEY_SHAPE in glsl.KEY_RAMP
    assert glsl.KEY_SHAPE in masks.MATTE_FS
    for fs in (glsl.KEY_RAMP, masks.MATTE_FS):
        assert "smoothstep" not in fs.replace(glsl.KEY_SHAPE, "")
        assert "0.2126" not in fs.replace(glsl.KEY_SHAPE, "")


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")


def _s(**kw) -> ViewState:
    return ViewState(lines=False, points=False, faces=False, mattes={"matte": MatteState(**kw)})


def _flat(rgb, w=64, h=48) -> np.ndarray:
    px = np.zeros((h, w, 4), np.uint8)
    px[..., :3] = rgb
    px[..., 3] = 255
    return px


def test_peak_passes_a_saturated_colour_luma_does_not(ctx):
    media = _media(a=Still(_flat((200, 0, 0))))
    r = _renderer(ctx, media)
    _draw(ctx, r, _s(source=3, key=0.5))
    assert (_mask_px(_mask(r)) == 255).all()
    assert r._graph.nodes["matte"].said == "64×48 mask · peak at 0.50"
    r = _renderer(ctx, media)
    _draw(ctx, r, _s(source=0, key=0.5))
    assert (_mask_px(_mask(r)) == 0).all()


def test_linear_peak_at_an_eighth_is_four_times_the_peak(ctx):
    """The look-back's occluder: min(4 · peak, 1), to the byte's rounding."""
    px = _ramp()
    r = _renderer(ctx, _media(a=Still(px)))
    _draw(ctx, r, _s(source=3, key=0.125, soft=0.125, ramp=1))
    got = _mask_px(_mask(r))[24]
    peak = px[24, :, :3].max(axis=1) / 255.0
    want = np.minimum(4.0 * peak, 1.0) * 255.0
    assert np.abs(got - want).max() <= 1.0, (got, want.round())


def test_linear_is_a_straight_line_smooth_is_not(ctx):
    media = _media(a=Still(_ramp()))
    rows = {}
    for ramp in (0, 1):
        r = _renderer(ctx, media)
        _draw(ctx, r, _s(source=3, key=0.5, soft=0.5, ramp=ramp))
        rows[ramp] = _mask_px(_mask(r))[24]
    x = np.linspace(0, 255, 64).round()
    assert np.abs(rows[1] - x).max() <= 1.0          # (v − 0) / 1: the ramp itself
    assert np.abs(rows[0] - x).max() > 10            # a smoothstep bends it


def test_a_saved_matte_draws_as_it_did(ctx):
    """The defaults (luma, smooth) are the old pass's bytes: a matte saved
    before peak and linear existed reads ramp 0."""
    media = _media(a=Still(_ramp()))
    r = _renderer(ctx, media)
    _draw(ctx, r, _s(soft=0.2))
    row = _mask_px(_mask(r))[24]
    v = np.linspace(0, 255, 64).round() / 255.0          # luma of a grey is its value
    t = np.clip((v - 0.3) / 0.4, 0.0, 1.0)
    want = t * t * (3.0 - 2.0 * t) * 255.0
    assert np.abs(row - want).max() <= 1.0



def _key(ctx, level, soft, m, ramp) -> float:
    """Key's ramp (`glsl.KEY_RAMP`, peak) for one grey pixel `m`, read back as float."""
    prog = ctx.program(
        vertex_shader="#version 330\nin vec2 p; void main() { gl_Position = vec4(p, 0, 1); }",
        fragment_shader="#version 330\n" + glsl.KEY_RAMP + """
uniform float m;
out vec4 o;
void main() { o = vec4(key_ramp(vec3(m))); }""")
    for k, v in (("u_measure", 0), ("u_level", level), ("u_soft", soft), ("u_keep", 0),
                 ("u_invert", 0), ("u_ramp", ramp), ("m", m)):
        if k in prog:                 # (the compiler drops a uniform it can fold)
            prog[k].value = v
    vbo = ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], "f4").tobytes())
    vao = ctx.vertex_array(prog, [(vbo, "2f", "p")])
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((1, 1), 4, dtype="f4")])
    fbo.use()
    vao.render()
    got = float(np.frombuffer(fbo.read(components=4, dtype="f4"), "f4")[0])
    for x in (fbo, vao, vbo, prog):
        x.release()
    return got


@pytest.mark.parametrize("ramp", [0, 1])
def test_a_narrow_ramp_has_a_coverage_at_its_level(ctx, ramp):
    """Devin on #520: a softness too small to move the upper edge in float32
    (level 0.5, softness 1e-8) gave 0 / 0 at the level. The ramp takes its
    width, as the old linear branch divided by the softness itself."""
    assert np.float32(0.5) + np.float32(1e-8) == np.float32(0.5)     # (the edge does not move)
    got = _key(ctx, 0.5, 1e-8, 0.5, ramp)
    assert np.isfinite(got) and got == 0.0
    assert _key(ctx, 0.5, 1e-8, 0.75, ramp) == 1.0
    assert _key(ctx, 0.25, 0.5, 0.5, ramp) == pytest.approx(0.5, abs=1e-6)


def test_a_narrow_smooth_matte_keeps_its_edges(ctx):
    """Devin on #520 (second pass): the smooth ramp's upper edge is the key
    plus the softness, not the lower edge plus twice it — rebuilt from a
    rounded lower edge, an alpha Matte keyed at 1, softness 1.49e-7, gave an
    opaque pixel about 0.35 where the old pass gave 0.5."""
    opaque = _flat((255, 255, 255))
    r = _renderer(ctx, _media(a=Still(opaque)))
    _draw(ctx, r, _s(source=1, key=1.0, soft=1.4901161193847656e-7))
    got = _mask_px(_mask(r))
    assert np.abs(got.astype(int) - 128).max() <= 1, np.unique(got)
