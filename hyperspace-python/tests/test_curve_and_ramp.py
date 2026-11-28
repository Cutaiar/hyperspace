"""The two public pieces that take over the look-back's and the
dream's private grade and coverage, so neither keeps its own.

- **Curve** — the remap row in the picture kind, named and knobbed
  as the lane modifier `curve` (shape −1 … 1, an exponent of 4^shape; invert).
  The old contrast `pow(c, contrast)` is Shape log₄(contrast).
- **The key's linear ramp** — at level 0, softness 1 on peak, a pixel's
  brightness is its coverage: the old trail's and dream's rule, a choice of
  Black is clear's (`key.<node>.ramp`)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import media_tex
from hyperspace.fx import FxChain, FxState

sys.path.insert(0, str(Path(__file__).parent))

moderngl = pytest.importorskip("moderngl")

W, H = 16, 8


def _ramp():
    """A premultiplied, opaque grey ramp across, a colour per row."""
    x = np.linspace(0, 255, W).round().astype(np.uint8)
    px = np.zeros((H, W, 4), np.uint8)
    for row, tint in enumerate([(1, 1, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1),
                                (1, 1, 0), (0, 1, 1), (1, 0, 1), (1, 0.5, 0.25)]):
        for c in range(3):
            px[row, :, c] = (x * tint[c]).round().astype(np.uint8)
    px[..., 3] = 255
    return px


def _curve(ctx, shape, invert=0, px=None):
    st = FxState()
    st.values["curve"].update(on=True, mix=1.0, shape=shape, invert=invert)
    chain = FxChain(ctx, st)
    px = _ramp() if px is None else px
    src = ctx.texture((W, H), 4, px.tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one("curve", src, out, 0.0, opaque=0, res=(W, H))
    assert chain.errors == {} and ctx.error == "GL_NO_ERROR"
    return np.frombuffer(out.read(components=4), np.uint8).reshape(H, W, 4).astype(int)


def test_curve_at_shape_0_leaves_the_picture(ctx):
    np.testing.assert_array_equal(_curve(ctx, 0.0), _ramp())


@pytest.mark.parametrize("contrast", [0.5, 1.5, 2.0, 3.0])
def test_curve_is_the_old_contrast_at_shape_log4(ctx, contrast):
    """The look-back's and the dream's `pow(max(c, 1e-6), contrast)`."""
    got = _curve(ctx, math.log(contrast, 4.0))
    c = _ramp()[..., :3] / 255.0
    want = np.round(np.power(np.maximum(c, 1e-6), contrast) * 255.0)
    assert np.abs(got[..., :3] - want).max() <= 1
    assert (got[..., 3] == 255).all()


def test_curve_inverted_is_bright_for_dark_within_its_alpha(ctx):
    got = _curve(ctx, 0.0, invert=1)
    np.testing.assert_allclose(got[0, :, 0], 255 - _ramp()[0, :, 0], atol=1)


def test_curve_takes_the_lane_modifiers_knobs():
    from hyperspace import modifiers

    spec = FxState().specs["curve"]
    lane = {s.key: s for s in modifiers.PARAMS["curve"]}
    assert [p.key for p in spec.params] == list(lane)
    shape = next(p for p in spec.params if p.key == "shape")
    assert (shape.lo, shape.hi, shape.default) == (lane["shape"].lo, lane["shape"].hi,
                                                    lane["shape"].default)


def test_the_linear_ramp_makes_brightness_the_coverage(ctx):
    """Level 0, softness 1, peak, keep colour: alpha = the pixel's peak — what
    the look-back's trail and the dream's lay did privately."""
    from test_black_is_clear import _passes

    _, mp = _passes(ctx)
    px = _ramp()
    src = ctx.texture((W, H), 4, px.tobytes())
    out = mp.key(src, "t", (W, H), media_tex.Key(level=0.0, soft=1.0, keep=True, ramp=1))
    got = np.frombuffer(out.read(), np.uint8).reshape(H, W, 4).astype(int)
    peak = px[..., :3].max(axis=2).astype(int)
    assert np.abs(got[..., 3] - peak).max() <= 1
    np.testing.assert_array_equal(got[..., :3], px[..., :3])       # colour kept


def test_the_smooth_ramp_is_the_default(ctx):
    from test_black_is_clear import _passes

    _, mp = _passes(ctx)
    px = _ramp()
    src = ctx.texture((W, H), 4, px.tobytes())
    a = mp.key(src, "a", (W, H), media_tex.Key(level=0.0, soft=1.0))
    b = mp.key(src, "b", (W, H), media_tex.Key(level=0.0, soft=1.0, ramp=0))
    assert a.read() == b.read()
    peak = px[0, :, 0] / 255.0
    got = np.frombuffer(a.read(), np.uint8).reshape(H, W, 4)[0, :, 3] / 255.0
    want = peak * peak * (3 - 2 * peak)                     # smoothstep(0, 1, peak)
    assert np.abs(got - want).max() <= 2 / 255


def test_curve_keeps_black_black_and_premultiplied_colour_within_alpha(ctx):
    """Shape −1 on premultiplied colour: exact black stays
    black, and a quarter-covered white stays a quarter covered."""
    px = np.zeros((H, W, 4), np.uint8)
    px[..., 3] = 255                               # opaque black
    px[0, :, :] = (64, 64, 64, 64)                 # white at a quarter's coverage
    got = _curve(ctx, -1.0, px=px)
    assert got[1:, :, :3].max() == 0
    assert got[0, :, 3].max() <= 65 and got[0, :, :3].max() <= got[0, :, 3].max()
    inv = _curve(ctx, 0.0, invert=1, px=px)
    np.testing.assert_allclose(inv[0, 0], (0, 0, 0, 64), atol=1)    # white inverted: clear-black


def test_curve_at_shape_0_leaves_a_kept_glow_as_it_is(ctx):
    """A picture keyed with keep colour has colour above its coverage (a glow);
    a neutral Curve passes it through, and a bent one keeps its brightness
    relative to it, never cutting it to its alpha."""
    px = np.zeros((H, W, 4), np.uint8)
    px[..., :] = (128, 64, 0, 51)                  # colour above alpha: a kept glow
    px[1, :, :] = (100, 0, 0, 0)                   # a glow with no coverage at all
    got = _curve(ctx, 0.0, px=px)
    np.testing.assert_allclose(got[..., :3], px[..., :3], atol=1)
    bent = _curve(ctx, 0.5, px=px)
    assert bent[0, 0, 0] > 51 and bent[1, 0, 0] > 0
