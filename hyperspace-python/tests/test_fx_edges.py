"""Plan 39 T0 (W5, decision 7): `edges` is an effect file (shaders/fx/edges.glsl).

A Sobel over the wired picture's luma, premultiplied over transparent
black. Everything here is the FX mechanism's own (`fx.edges.*` params, one
pass, `FxChain.run_one`); what the lines *look* like is judged by eye (hand
check AJ.7) and held by the `edges-scene` fixture's goldens. The passes
below run on a see-through ground (`opaque=0`), so what is asserted is what
the alpha tail (`fx.FS_TAIL`) leaves: alpha lifted to cover the colour and
no further — on an opaque ground the tail writes alpha 1 whatever the
effect returns, as every effect's.
"""

import numpy as np
import pytest

from hyperspace.fx import FX_DIR, FxChain, FxState, parse

W, H = 64, 48

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def test_the_file_declares_its_three_params():
    spec = parse("edges", (FX_DIR / "edges.glsl").read_text())
    assert spec.label == "Edges" and spec.blend == 0 and spec.mix == 1.0   # @blend mix
    got = {p.key: (p.lo, p.hi, p.default, p.integer) for p in spec.params}
    assert got == {"threshold": (0.0, 1.0, 0.2, False),
                   "glow": (0.0, 4.0, 0.0, False),
                   "colour": (0.0, 2.0, 0.0, True)}
    colour, = (p for p in spec.params if p.key == "colour")
    assert colour.choices == ("white", "source", "direction")
    # the registry side: it is on the FX page like any file, off until switched on
    st = FxState()
    assert "edges" in st.specs and st.errors == {}
    assert st.values["edges"]["on"] is False and st.values["edges"]["threshold"] == 0.2


def run(ctx, picture: np.ndarray, **values) -> np.ndarray:
    """One `edges` pass over `picture` (H × W × 4, uint8, premultiplied) on a
    see-through ground: the pixels the tail leaves, H × W × 4 uint8."""
    st = FxState()
    st.values["edges"].update(on=True, **values)
    chain = FxChain(ctx, st)
    src = ctx.texture((W, H), 4, np.ascontiguousarray(picture).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one("edges", src, out, 0.0, opaque=0)
    assert ctx.error == "GL_NO_ERROR"
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    for o in (src, out):
        o.release()
    return px


def flat(rgb) -> np.ndarray:
    pic = np.zeros((H, W, 4), np.uint8)
    pic[...] = (*rgb, 255)
    return pic


def vertical_edge() -> np.ndarray:
    """Black on the left half, white on the right: a hard vertical edge
    between columns W/2 − 1 and W/2."""
    pic = flat((0, 0, 0))
    pic[:, W // 2:, :3] = 255
    return pic


def horizontal_edge() -> np.ndarray:
    """Black below, white above (rows run up from the texture's first)."""
    pic = flat((0, 0, 0))
    pic[H // 2:, :, :3] = 255
    return pic


@pytest.mark.parametrize("colour", [0, 1, 2])
@pytest.mark.parametrize("rgb", [(0, 0, 0), (128, 64, 200), (255, 255, 255)])
def test_a_flat_picture_makes_black(ctx, rgb, colour):
    """Every pixel 0, alpha included, after the tail — the glow up too."""
    px = run(ctx, flat(rgb), colour=colour, glow=4.0)
    assert not px.any(), (rgb, colour, px.max())


@pytest.mark.parametrize("colour", [0, 1])
def test_a_hard_vertical_edge_makes_a_bright_line_there_and_nothing_elsewhere(ctx, colour):
    px = run(ctx, vertical_edge(), colour=colour)
    edge = [W // 2 - 1, W // 2]
    # the two columns either side of the step are the line, at full
    # strength: white in white mode; in source mode the picture's own colour
    # there — white on the right, black on the left, which still covers
    # (alpha is the line's strength × the picture's, premultiplied)
    lit = px[:, edge]
    if colour == 0:
        assert (lit == 255).all()
    else:
        assert (px[:, W // 2] == 255).all()
        assert not px[:, W // 2 - 1, :3].any() and (px[:, W // 2 - 1, 3] == 255).all()
    rest = np.delete(px, edge, axis=1)
    assert not rest.any(), rest.max()


def test_the_threshold_drops_a_weak_edge(ctx):
    """A step of a fifth of full scale draws at the default threshold's
    side of nothing, and draws once the threshold is below it."""
    pic = flat((0, 0, 0))
    pic[:, W // 2:, :3] = 40                     # luma ≈ 0.16: below 0.2
    assert not run(ctx, pic).any()
    assert run(ctx, pic, threshold=0.05)[:, W // 2].min() > 0


def test_the_glow_widens_the_line(ctx):
    plain = run(ctx, vertical_edge())
    glow = run(ctx, vertical_edge(), glow=4.0)
    cols = lambda px: set(np.nonzero(px[H // 2, :, 3])[0])
    assert cols(plain) == {W // 2 - 1, W // 2}
    assert cols(plain) < cols(glow) and len(cols(glow)) == 6
    assert glow[H // 2, W // 2 + 2, 3] == 255          # glow 4: as bright as the line


def test_direction_colours_a_vertical_and_a_horizontal_edge_differently(ctx):
    v = run(ctx, vertical_edge(), colour=2)[H // 2, W // 2].astype(int)
    h = run(ctx, horizontal_edge(), colour=2)[H // 2, W // 2].astype(int)
    for px in (v, h):
        assert px[3] == 255 and px[:3].max() == 255 and px[:3].min() == 0   # one full hue
    # dark → light to the right is red; upward, chartreuse (hue 90°)
    assert tuple(v[:3]) == (255, 0, 0)
    assert h[1] == 255 and h[2] == 0 and 120 < h[0] < 135
    assert not (v[:3] == h[:3]).all()
