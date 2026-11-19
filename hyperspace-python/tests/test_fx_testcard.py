"""The test card (`shaders/fx/testcard.glsl`): a generator drawn in place of
its picture, so the effects after it show what they do to straight lines.

Held here: it is the same card whatever comes in, opaque; its lines are
where the knobs say; and at mix 0 the picture comes through untouched.
"""

import numpy as np
import pytest

from hyperspace.fx import FX_DIR, FxChain, FxState, parse

W, H = 96, 64

moderngl = pytest.importorskip("moderngl")


def run(ctx, picture: np.ndarray, **values) -> np.ndarray:
    st = FxState()
    st.values["testcard"].update(on=True, **values)
    chain = FxChain(ctx, st)
    src = ctx.texture((W, H), 4, np.ascontiguousarray(picture).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one("testcard", src, out, 0.0, opaque=0)
    assert ctx.error == "GL_NO_ERROR" and st.errors == {}
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    for o in (src, out):
        o.release()
    return px


def speckle(seed: int) -> np.ndarray:
    pic = np.random.default_rng(seed).integers(0, 256, (H, W, 4), dtype=np.uint8)
    pic[..., 3] = 255
    return pic


def test_it_declares_a_still_generator():
    spec = parse("testcard", (FX_DIR / "testcard.glsl").read_text())
    assert spec.label == "Test card" and spec.blend == 0 and spec.speed == 0.0
    assert [p.key for p in spec.params] == ["grid", "line", "circle", "bars", "ground"]
    assert not spec.clocks and not any(p.amount for p in spec.params)
    # palette stays the last of the old stack's orders (test_fx_palette.py)
    st = FxState()
    assert spec.order < st.specs["palette"].order and st.errors == {}


def test_it_is_the_same_card_whatever_comes_in_and_opaque(ctx):
    a, b = run(ctx, speckle(1)), run(ctx, speckle(2))
    assert np.array_equal(a, b)
    assert (a[..., 3] == 255).all()
    see_through = np.zeros((H, W, 4), np.uint8)
    assert np.array_equal(run(ctx, see_through), a)


def test_mix_zero_is_the_picture(ctx):
    pic = speckle(3)
    assert np.abs(run(ctx, pic, mix=0.0).astype(int) - pic).max() <= 1


def test_the_grid_runs_through_the_centre_at_its_spacing(ctx):
    """Grid 8 on a 64-px-high frame is a line every 8 px, one through the
    centre each way; with no circle and no bars the card is its own mirror."""
    px = run(ctx, speckle(4), grid=8.0, line=1.0, circle=0.0, bars=0.0, ground=0.0)
    lum = px[..., 1].astype(int)
    row = lum[H // 2 + 4]                       # a row between two lines: only the uprights
    lit = np.flatnonzero(row > 96)
    centres = np.unique(np.round(lit / 8.0) * 8).astype(int)
    assert list(centres) == list(range(0, W + 1, 8))[:len(centres)] and len(centres) >= 11
    assert row[W // 2 - 4] < 16                 # dark between them
    assert np.abs(lum - lum[::-1]).max() <= 2 and np.abs(lum - lum[:, ::-1]).max() <= 2
    # the cross through the centre is heavier than a grid line
    assert lum[H // 2 + 4, W // 2 - 2:W // 2 + 2].sum() > \
           1.5 * lum[H // 2 + 4, W // 2 + 6:W // 2 + 10].sum()


def test_the_circle_and_the_bars_are_where_they_say(ctx):
    plain = run(ctx, speckle(5), grid=2.0, circle=0.0, bars=0.0, ground=0.0)
    ring = run(ctx, speckle(5), grid=2.0, circle=0.5, bars=0.0, ground=0.0)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx + 0.5 - W / 2, yy + 0.5 - H / 2)
    changed = (ring != plain).any(-1)
    assert changed.any() and np.abs(r[changed] - 0.25 * H).max() <= 3      # diameter ½ a height
    bars = run(ctx, speckle(5), bars=0.25)
    foot = bars[2, :, :3].astype(int)           # row 2 is near the frame's foot (y up)
    assert len({tuple(foot[k * 16 + 8]) for k in range(6)}) == 6           # six colours
    assert (foot.max(-1) - foot.min(-1)).min() > 100                       # every one a colour
    top = bars[H - 3, :, :3].astype(int)
    assert (top.max(-1) - top.min(-1)).max() == 0                          # grey up above
