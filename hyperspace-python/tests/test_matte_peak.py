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
