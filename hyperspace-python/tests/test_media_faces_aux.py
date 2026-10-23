"""Plan 32 T7 — the faces read a media channel (`view.media`, where the one
bitmap file was), every effect gets a second picture input (`aux`), and the
two effects that use it (`displace`, `blend`).

The channels are the real `MediaState` over a fake still, opened by a fake
opener: no file is read. The GL half draws on a standalone context and
skips without one."""

from __future__ import annotations

import numpy as np
import pytest

from hyperspace import graph as G
from hyperspace.media.channels import MediaState
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View

RED = (255, 0, 0)


def _rgba(w: int, h: int, colour=RED) -> np.ndarray:
    px = np.zeros((h, w, 4), np.uint8)
    px[..., 3] = 255
    px[..., :3] = colour
    return px


class Still:
    """A still that is there at once: the same frame every read."""

    kind, timed, duration, status = "still", False, 0.0, "ready"

    def __init__(self, pixels: np.ndarray):
        self.f = MediaFrame(pixels, 1.0, 0)

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def want(self, t: float) -> None:
        pass

    def latest(self):
        return self.f


def _media(**sources) -> MediaState:
    """The eight channels with `sources` (channel → fake source) on slot 0."""
    by_id = {f"file:/fake/{c}.png": s for c, s in sources.items()}
    m = MediaState(opener=lambda sid, resolver: by_id[sid])
    for c in sources:
        m.assign(c, 0, f"file:/fake/{c}.png")
    m.poll(0.0, 0.0)
    return m


# ---------------------------------------------------------------- no GL

def test_aux_refusal_is_a_note():
    """`aux` takes a picture: a mask (the cover) or geometry wired into it
    is a note, and the graph is the default one; a picture from a channel,
    the scene or the history is a wire."""
    for src, words in (("cover", "a mask"), ("ghost", "geometry")):
        spec = G.read_graph({"wires": [{"from": src, "to": "blend.aux"}]})
        assert len(spec.notes) == 1 and words in spec.notes[0], spec.notes
        assert spec.wiring() == G.Wiring()
    for src in ("media.a", "scene", "history"):
        assert G.wire_error(G.Wire(src, "blend.aux")) is None, src
    assert "no port" in G.wire_error(G.Wire("scene", "blend.extra"))


def test_an_aux_wire_leaves_the_effect_in_its_run():
    """An effect whose aux is wired stays in each pipeline's run at its
    order: every node of it reads the channel on `aux`, its picture on
    `image` as before; nothing else of the graph moves."""
    assert G.Effect.INPUTS == {"image": G.IMAGE, "aux": G.IMAGE}
    assert "aux" in G.Effect.REFS
    effects = ("acid", "blend", "palette")
    vs = [View(Switches(), (96, 64)), View(Switches(through=True), (96, 64))]
    base = G.default_graph(vs, effects=effects)
    spec = G.read_graph({"wires": [{"from": "media.a", "to": "blend.aux"}]})
    assert spec.notes == ()
    g = G.default_graph(vs, spec.wiring(), effects=effects)
    blends = [n for n in g.order if isinstance(n, G.Effect) and n.effect == "blend"]
    assert len(blends) == 2
    assert {n.name for n in blends} == {n.name for n in base.order
                                        if isinstance(n, G.Effect) and n.effect == "blend"}
    for n in blends:
        assert isinstance(n.inputs["aux"], G.MediaNode) and n.inputs["aux"].channel == "a"
        assert n.inputs["image"].name == base.nodes[n.name].inputs["image"].name
    assert ([n.name for n in g.order if n.name != "media.a"]
            == [n.name for n in base.order])


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c


def _fbo(ctx, w, h):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4)])


def _px(f) -> np.ndarray:
    w, h = f.size
    return np.frombuffer(f.read(components=4), np.uint8).reshape(h, w, 4)[::-1].astype(int)


def _faces(**kw):
    from hyperspace.view import ViewState

    return ViewState(shape=3, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25,
                     faces=True, lines=False, points=False, bright=2.0, zoom=1.6,
                     media_scale=1.0, **kw)


def _draw(ctx, r, s, size=(96, 64), frames=1):
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    for k in range(frames):
        r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return _px(vs[0].target)


def _renderer(ctx, media=None, wires=()):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    if wires:
        r.wiring = G.Wiring(wires=tuple(wires))
    return r


def test_faces_show_channel(ctx):
    """A red still on channel c, `view.media = 3`: the faces are red where
    the bitmap was drawn; `view.media = 0` is the frame with no media."""
    r = _renderer(ctx, _media(c=Still(_rgba(16, 9))))
    plain = _draw(ctx, _renderer(ctx), _faces(), size=(160, 120))
    off = _draw(ctx, r, _faces(media=0), size=(160, 120))
    assert np.array_equal(off, plain)
    on = _draw(ctx, r, _faces(media=3), size=(160, 120))
    h, w = on.shape[:2]
    centre = on[h // 2 - 4: h // 2 + 4, w // 2 - 4: w // 2 + 4, :3].reshape(-1, 3)
    assert (centre[:, 0] > 2 * centre[:, 1] + 20).all(), centre[:4]
    assert (centre[:, 0] > 2 * centre[:, 2] + 20).all()
    # the base frame's centre is grey, not red
    base = plain[h // 2, w // 2, :3]
    assert abs(int(base[0]) - int(base[1])) < 10
    # a channel with nothing on it draws the plain faces
    assert np.array_equal(_draw(ctx, r, _faces(media=5), size=(160, 120)), plain)


def _chain(ctx):
    from hyperspace.fx import FxChain

    chain = FxChain(ctx)
    assert chain.compile_all() == {}
    return chain


def _tex(ctx, px: np.ndarray):
    h, w = px.shape[:2]
    return ctx.texture((w, h), 4, data=np.ascontiguousarray(px[::-1]).tobytes())


def _one(ctx, chain, name, src_px, aux_px=None):
    h, w = src_px.shape[:2]
    src = _tex(ctx, src_px)
    aux = _tex(ctx, aux_px) if aux_px is not None else None
    out = ctx.texture((w, h), 4)
    fbo = ctx.framebuffer(color_attachments=[out])
    fbo.use()
    ctx.viewport = (0, 0, w, h)
    chain.run_one(name, src, fbo, 1.0, aux=aux)
    got = np.frombuffer(out.read(), np.uint8).reshape(h, w, 4)[::-1].astype(int)
    for res in (fbo, out, src, *([aux] if aux is not None else [])):
        res.release()
    assert ctx.error == "GL_NO_ERROR"
    return got


def _noise(w=32, h=24, seed=3):
    px = np.random.default_rng(seed).integers(0, 256, (h, w, 4), dtype=np.uint8)
    px[..., 3] = 255
    return px


def _checker(w=32, h=24, cell=4):
    yy, xx = np.mgrid[0:h, 0:w]
    on = ((xx // cell + yy // cell) % 2).astype(bool)
    px = np.zeros((h, w, 4), np.uint8)
    px[..., 3] = 255
    px[on, :3] = 255
    return px


def test_unwired_aux_reads_black(ctx):
    """Blend over with nothing on aux: the input, unchanged — in every
    mode; and displace with nothing on aux moves nothing."""
    chain = _chain(ctx)
    v = chain.state.values["blend"]
    v.update(on=True, mix=1.0)
    src = _noise()
    for mode in range(5):
        v["mode"] = mode
        assert np.array_equal(_one(ctx, chain, "blend", src), src), mode
    chain.state.values["displace"].update(on=True, mix=1.0, amount=0.5)
    assert np.array_equal(_one(ctx, chain, "displace", src), src)


def test_aux_wired_from_channel(ctx):
    """`media.a → blend.aux`, blend over at mix 1: the frame is the still."""
    m = _media(a=Still(_rgba(16, 9)))
    m.channels["a"].fit = 2                                  # stretch: fills
    r = _renderer(ctx, m, wires=[G.Wire("media.a", "blend.aux")])
    r.fx.state.values["blend"].update(on=True, mix=1.0, mode=0)
    from hyperspace.view import ViewState

    pic = _draw(ctx, r, ViewState(lines=False, points=False, faces=False), frames=2)
    assert "blend" in r.stats["effects"]
    assert (pic[..., :3] == RED).all()
    # the blend's mix is the amount: half the still over the black ground
    r.fx.state.values["blend"]["mix"] = 0.5
    half = _draw(ctx, r, ViewState(lines=False, points=False, faces=False))
    assert abs(half[10, 10, 0] - 128) <= 2 and half[10, 10, 1] == 0


def test_displace_moves_pixels(ctx):
    """A gradient on aux displaces a checker: the centre row moves; an aux
    of flat mid-grey moves nothing (to within a hair: 128 of 255 is not
    quite the middle)."""
    chain = _chain(ctx)
    chain.state.values["displace"].update(on=True, mix=1.0, amount=0.2, mode=0)
    src = _checker()
    h, w = src.shape[:2]
    ramp = np.zeros((h, w, 4), np.uint8)
    ramp[..., :3] = np.linspace(0, 255, w, dtype=np.uint8)[None, :, None]
    ramp[..., 3] = 255
    got = _one(ctx, chain, "displace", src, ramp)
    assert (got[h // 2, :, :3] != src[h // 2, :, :3]).any()
    assert np.abs(got - src).sum() > w * h * 20
    grey = np.full((h, w, 4), 128, np.uint8)
    grey[..., 3] = 255
    flat = _one(ctx, chain, "displace", src, grey)
    assert np.abs(flat - src).max() <= 8           # (128 is a hair above the middle)
    # red/green mode reads the aux's red and green
    chain.state.values["displace"]["mode"] = 1
    assert np.abs(_one(ctx, chain, "displace", src, ramp) - src).sum() > w * h * 20


def test_blend_modes_with_an_aux(ctx):
    """Each mode with a red aux over a grey input: over is red, multiply
    keeps red alone, screen lifts red, difference flips it, luma key shows
    the aux only above its key."""
    chain = _chain(ctx)
    v = chain.state.values["blend"]
    v.update(on=True, mix=1.0)
    src = np.full((8, 8, 4), 100, np.uint8)
    src[..., 3] = 255
    aux = _rgba(8, 8)
    want = {0: (255, 0, 0), 1: (100, 0, 0), 2: (255, 100, 100), 3: (155, 100, 100)}
    for mode, rgb in want.items():
        v["mode"] = mode
        got = _one(ctx, chain, "blend", src, aux)[4, 4, :3]
        assert np.abs(got - np.array(rgb)).max() <= 2, (mode, got)
    v.update(mode=4, key=0.1, soft=0.0)                # red's luma is 0.299: shown
    assert np.abs(_one(ctx, chain, "blend", src, aux)[4, 4, :3] - RED).max() <= 2
    v["key"] = 0.6                                     # keyed out: the input
    assert np.array_equal(_one(ctx, chain, "blend", src, aux), src)


def test_old_effects_still_compile(ctx):
    """Every effect file compiles with the new header, and one that never
    reads `aux` draws the same with an aux bound as without."""
    from hyperspace import fx

    chain = _chain(ctx)
    assert {"displace", "blend"} <= set(chain.state.specs)
    for line in ("uniform sampler2D u_aux;", "uniform int u_aux_on;", "uniform vec2 u_aux_size;"):
        assert line in fx.FS_HEAD
    src, aux = _noise(), _noise(seed=9)
    for name in sorted(chain.state.specs):
        assert chain.ready(name), name
        if name in ("displace", "blend"):
            continue
        chain.state.values[name].update(on=True, mix=1.0)
        assert np.array_equal(_one(ctx, chain, name, src),
                              _one(ctx, chain, name, src, aux)), name
