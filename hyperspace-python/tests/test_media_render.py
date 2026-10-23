"""Plan 32 T6 — the render side of the media channels: `media_tex.MediaTextures`
(the upload), the fitted `media.<c>` graph node, the backdrop under the scene,
and the channels as wire ends.

The channels are the real `MediaState` over fake sources (`Still`, `Late`,
`OnGL`), opened by a fake opener: no file is read and no decode runs. The GL
half draws on a standalone context and skips without one."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from hyperspace import graph as G
from hyperspace.media import channels
from hyperspace.media.channels import MediaState
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def _rgba(w: int, h: int, top=RED, bottom=None) -> np.ndarray:
    """A w×h still, top row first: `top` above, `bottom` (default: `top`) below."""
    px = np.zeros((h, w, 4), np.uint8)
    px[..., 3] = 255
    px[: h // 2, :, :3] = top
    px[h // 2:, :, :3] = bottom if bottom is not None else top
    return px


class Still:
    """A still that is there at once: the same frame every read."""

    kind, timed, duration, status = "still", False, 0.0, "ready"

    def __init__(self, pixels: np.ndarray):
        self.f = MediaFrame(pixels, 1.0, 0)
        self.reads = 0

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def want(self, t: float) -> None:
        pass

    def latest(self):
        self.reads += 1
        return self.f


class Late(Still):
    """A still whose decode lands on another thread `delay` s after `start`:
    None until then — the frame thread must draw on without it."""

    def __init__(self, pixels: np.ndarray):
        super().__init__(pixels)
        self.ready: MediaFrame | None = None

    def start(self, delay: float) -> threading.Thread:
        def land():
            time.sleep(delay)
            self.ready = self.f
        t = threading.Thread(target=land, name="media-fake-late", daemon=True)
        t.start()
        return t

    def latest(self):
        self.reads += 1
        return self.ready


def _media(**sources) -> MediaState:
    """The eight channels with `sources` (channel → fake source) on slot 0."""
    by_id = {f"file:/fake/{c}.png": s for c, s in sources.items()}
    m = MediaState(opener=lambda sid, resolver: by_id[sid])
    for c in sources:
        m.assign(c, 0, f"file:/fake/{c}.png")
    m.poll(0.0, 0.0)
    return m


def _view(**kw) -> View:
    return View(Switches(**kw), (480, 320))


def _names(g: G.Graph) -> list[str]:
    return [n.name for n in g.order]


# ---------------------------------------------------------------- no GL

def test_the_graph_knows_the_channels_media_does():
    """graph.py may not import the media package (the render stack's rule),
    so it keeps the channel letters itself: the same eight, and the fit
    modes `media_tex` draws are the channels' in order."""
    from hyperspace import media_tex
    from hyperspace.media import frame

    assert G.MEDIA_CHANNELS == channels.CHANNELS
    assert media_tex.FITS == channels.FITS
    assert (media_tex.TEX_2D, media_tex.TEX_RECT) == (frame.TEX_2D, frame.TEX_RECT)
    assert MediaFrame(None, 0.0, 1, texture=3, tex_size=(2, 2)).tex_target == frame.TEX_2D


def test_no_backdrop_graph_unchanged():
    """No backdrop: the default graph is exactly today's, for the default
    views — node for node, in order — and `Wiring()` still compares equal
    to the default (the renderer's graph key)."""
    states = [{}, {"scene": False}, {"through": True}, {"hands": False},
              {"scene": False, "through": True}]
    one = G.default_graph([_view()])
    assert _names(one) == ["shape", "ghost", "scene", "cover", "hands", "history", "fx",
                           "capture", "output.1"]
    for kw in states:
        vs = [_view(**kw), _view()]
        base = G.default_graph(vs)
        off = G.default_graph(vs, G.Wiring(backdrop="", backdrop_history=False))
        assert _names(off) == _names(base)
        assert not any(isinstance(n, G.MediaNode) for n in base.order)
    assert G.Wiring() == G.Wiring(backdrop="")


def test_the_backdrop_wiring_is_checked():
    for bad in ("i", "A", "media.a", 1):
        with pytest.raises(ValueError, match="backdrop"):
            G.Wiring(backdrop=bad)
    with pytest.raises(ValueError, match="backdrop_history"):
        G.Wiring(backdrop="a", backdrop_history="yes")


def test_backdrop_history_toggle():
    """With a backdrop the scene is laid over the channel (`grounded`)
    before the history, so the effects bend both; the capture takes the
    scene alone with `backdrop_history` off, the composite with it on —
    and the hands-only pipeline has no backdrop."""
    vs = [_view(), _view(scene=False, through=True)]
    off = G.default_graph(vs, G.Wiring(backdrop="a"))
    on = G.default_graph(vs, G.Wiring(backdrop="a", backdrop_history=True))
    for g in (off, on):
        grounded = g.nodes["grounded"]
        assert isinstance(grounded, G.Composite) and grounded.blend == "over"
        assert grounded.inputs["over"] is g.nodes["scene"]
        media = grounded.inputs["under"]
        assert isinstance(media, G.MediaNode) and media.name == "media.a"
        assert media.channel == "a" and media.alpha_of == "backdrop_alpha"
        assert g.nodes["history"].inputs["image"] is grounded
        assert g.nodes["scene"].ground == 0.0        # see-through, laid over the backdrop
        assert g.nodes["composite(hands)"].inputs["under"] is None
    assert off.nodes["capture"].inputs["image"].name == "scene"
    assert on.nodes["capture"].inputs["image"].name == "grounded"
    assert G.default_graph(vs).nodes["scene"].ground is None
    # the history holding the hands: the hands laid onto what it captures
    both = G.default_graph(vs, G.Wiring(backdrop="b", backdrop_history=True,
                                        history="scene+hands"))
    held = both.nodes["capture"].inputs["image"]
    assert held.name == G.HISTORY_COMPOSITE and held.inputs["under"].name == "grounded"


def test_the_channels_are_wire_ends():
    """`media.a` … `media.h` leave a wire into any picture port; nothing
    goes into one, and there is no ninth."""
    ok = [G.Wire("media.c", "output.1.image"), G.Wire("media.a", "acid.image"),
          G.Wire("media.h", "history.image"), G.Wire("media.b", "output.2.hands")]
    for w in ok:
        assert G.wire_error(w) is None, w
    assert "no node" in G.wire_error(G.Wire("media.i", "output.1.image"))
    assert "nothing is wired into it" in G.wire_error(G.Wire("scene", "media.a.image"))
    assert G.wire_node_kind("media.d") == "media"
    spec = G.read_graph({"wires": [{"from": "media.c", "to": "output.2.image"}]})
    assert spec.notes == () and spec.wiring().wires == (G.Wire("media.c", "output.2.image"),)
    g = G.default_graph([_view(), _view()], spec.wiring())
    end = g.nodes["output.2"].inputs["image"]
    assert isinstance(end, G.Wired) and end.inputs["image"].name == "media.c"
    assert isinstance(end.inputs["image"], G.MediaNode)
    assert end.inputs["image"].alpha_of is None
    # the backdrop's channel wired too: two nodes, the wire's at alpha 1
    both = G.default_graph([_view()], G.Wiring(
        backdrop="c", wires=(G.Wire("media.c", "output.1.image"),)))
    assert both.nodes["media.c"].alpha_of == "backdrop_alpha"
    assert both.nodes["media.c(wire)"].alpha_of is None


def test_fit_scales():
    """The fit pass's uv scale (frame uv → picture uv about the centre):
    cover crops (≤ 1), contain letterboxes (≥ 1), stretch is 1."""
    from hyperspace.media_tex import fit_scale

    assert fit_scale(0, (200, 100), (100, 100)) == pytest.approx((0.5, 1.0))   # cover
    assert fit_scale(1, (200, 100), (100, 100)) == pytest.approx((1.0, 2.0))   # contain
    assert fit_scale(2, (200, 100), (100, 100)) == (1.0, 1.0)                  # stretch
    assert fit_scale(1, (100, 100), (100, 100)) == pytest.approx((1.0, 1.0))
    assert fit_scale(7, (200, 100), (100, 100)) == pytest.approx((0.5, 1.0))   # unknown: cover


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


def _renderer(ctx, media=None, wires=()):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    if wires:
        r.wiring = G.Wiring(wires=tuple(wires))
    return r


def _empty(**kw):
    """A view with nothing of the shape drawn."""
    from hyperspace.view import ViewState

    return ViewState(lines=False, points=False, faces=False, **kw)


def _shape(**kw):
    from hyperspace.view import ViewState

    return ViewState(shape=10, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25,
                     faces=True, pattern=2, **kw)


def _draw(ctx, r, s, size=(96, 64), views=None, frames=1):
    vs = views or [View(Switches(), size, target=_fbo(ctx, *size))]
    for k in range(frames):
        r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def test_upload_only_when_frame_moves(ctx):
    from hyperspace.media_tex import MediaTextures

    mt = MediaTextures(ctx)
    f = MediaFrame(_rgba(8, 4), 1.0, 0)
    a = mt.texture("a", f)
    assert mt.texture("a", f) is a and mt.uploads == 1
    assert a.size == (8, 4) and mt.flipped("a")
    assert mt.texture("a", MediaFrame(_rgba(8, 4, BLUE), 1.5, 1)) is a and mt.uploads == 2
    bigger = mt.texture("a", MediaFrame(_rgba(16, 8), 2.0, 2))     # a new size: a new texture
    assert bigger.size == (16, 8) and mt.uploads == 3
    assert mt.texture("a", None) is None and mt.uploads == 3
    mt.release()
    assert mt.texture("a", MediaFrame(_rgba(16, 8), 2.0, 2)) is not None and mt.uploads == 4
    mt.release()


def test_a_texture_frame_is_wrapped_never_uploaded(ctx):
    """A GPU frame (Syphon's) is the source's own texture, wrapped
    (`ctx.external_texture`), never copied; wrapping it again is free and
    releasing the wrapper leaves the source's texture alone."""
    from hyperspace.media_tex import MediaTextures

    mt = MediaTextures(ctx)
    own = ctx.texture((4, 2), 4, data=bytes([0, 255, 0, 255]) * 8)
    f = MediaFrame(None, 1.0, 1, texture=own.glo, tex_size=(4, 2))
    got = mt.texture("b", f)
    assert got.glo == own.glo and mt.uploads == 0 and not mt.flipped("b")
    assert mt.texture("b", MediaFrame(None, 1.1, 2, texture=own.glo, tex_size=(4, 2))) is got
    mt.release()
    assert np.frombuffer(own.read(), np.uint8)[:4].tolist() == [0, 255, 0, 255]


def test_unconsumed_channel_not_uploaded(ctx):
    """Channel b is playing but nothing reads it: never read, never
    uploaded — while the backdrop's channel a is, once a frame."""
    a, b = Still(_rgba(16, 9)), Still(_rgba(16, 9, BLUE))
    r = _renderer(ctx, _media(a=a, b=b))
    _draw(ctx, r, _empty(), frames=3)
    assert r._media_textures().uploads == 0 and a.reads == b.reads == 0
    _draw(ctx, r, _empty(backdrop=1), frames=3)
    assert b.reads == 0 and a.reads == 3                 # read once a frame
    assert r._media_textures().uploads == 1               # the frame never moved


def test_backdrop_under_scene(ctx):
    """A red still on channel a under the scene: with nothing of the shape
    drawn the frame is the still; with the shape, its faces are laid over
    it; at backdrop alpha 0.5, half red over the black ground."""
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))))
    (pic,) = _draw(ctx, r, _empty(backdrop=1))
    h, w = pic.shape[:2]
    assert tuple(pic[h // 2, w // 2, :3]) == RED and (pic[..., :3] == RED).all()
    assert r._graph.nodes["grounded"] and "media.a" in r._graph.timed
    (shaped,) = _draw(ctx, r, _shape(backdrop=1))
    assert (shaped[..., :3] != RED).any(axis=-1).any()      # the faces over the red
    assert (shaped[..., :3] == RED).all(axis=-1).any()      # and the still between them
    (half,) = _draw(ctx, r, _empty(backdrop=1, backdrop_alpha=0.5))
    assert abs(half[h // 2, w // 2, 0] - 128) <= 1 and half[h // 2, w // 2, 1] == 0
    # off again: the graph without it, the frame black
    (none,) = _draw(ctx, r, _empty(backdrop=0))
    assert "grounded" not in r._graph.nodes and (none[..., :3] == 0).all()


def test_backdrop_needs_the_channels(ctx):
    """A renderer with no media state draws no backdrop (and builds none)."""
    r = _renderer(ctx, None)
    (pic,) = _draw(ctx, r, _empty(backdrop=1))
    assert "grounded" not in r._graph.nodes and (pic[..., :3] == 0).all()


def test_the_graph_is_rebuilt_only_when_the_backdrop_changes(ctx):
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9)), b=Still(_rgba(16, 9, BLUE))))
    _draw(ctx, r, _empty(backdrop=1))
    g = r._graph
    _draw(ctx, r, _empty(backdrop=1, backdrop_alpha=0.3))
    assert r._graph is g                                    # alpha is per frame
    _draw(ctx, r, _empty(backdrop=1, backdrop_history=True))
    assert r._graph is not g and r._graph.wiring.backdrop_history
    assert r._graph.nodes["capture"].inputs["image"].name == "grounded"
    _draw(ctx, r, _empty(backdrop=2))
    assert r._graph.wiring.backdrop == "b" and not r.wiring.backdrop   # the base is the preset's


def test_media_wire_to_output(ctx):
    """`media.c → output.1.image`: output 1 shows the channel, whatever the
    scene draws; output 2 keeps its switches."""
    m = _media(c=Still(_rgba(16, 9)))
    m.channels["c"].fit = 2                                  # stretch: fills
    r = _renderer(ctx, m, wires=[G.Wire("media.c", "output.1.image")])
    size = (96, 64)
    vs = [View(Switches(), size, target=_fbo(ctx, *size)),
          View(Switches(), size, target=_fbo(ctx, *size))]
    one, two = _draw(ctx, r, _shape(), views=vs, frames=2)
    assert (one[..., :3] == RED).all()
    assert not (two[..., :3] == RED).all(axis=-1).any()     # the shape on black


def test_fit_modes(ctx):
    """A 2:1 still (red over blue) in a 1:1 frame: contain leaves the top
    rows black, cover does not (and crops the sides), stretch fills; the
    still is the right way up in each."""
    m = _media(c=Still(_rgba(64, 32, RED, BLUE)))
    r = _renderer(ctx, m, wires=[G.Wire("media.c", "output.1.image")])
    got = {}
    for k, name in enumerate(channels.FITS):
        m.channels["c"].fit = k
        (got[name],) = _draw(ctx, r, _empty(), size=(64, 64))
    contain, cover, stretch = got["contain"], got["cover"], got["stretch"]
    assert (contain[:8, :, :3] == 0).all() and (contain[-8:, :, :3] == 0).all()
    assert tuple(contain[20, 32, :3]) == RED and tuple(contain[44, 32, :3]) == BLUE
    assert tuple(cover[0, 32, :3]) == RED and tuple(cover[63, 32, :3]) == BLUE
    assert tuple(stretch[0, 0, :3]) == RED and tuple(stretch[63, 63, :3]) == BLUE
    assert ((stretch[:, :, :3] == RED).all(-1) | (stretch[:, :, :3] == BLUE).all(-1)).mean() > 0.95


def test_a_texture_frame_through_the_fit_pass(ctx):
    """A source with `gl_poll` (Syphon) is asked through it — once a frame,
    on the frame thread — and never through `latest`; its texture is in
    GL's row order (row 0 at the bottom), drawn as it is."""
    own = ctx.texture((8, 4), 4)
    rows = np.zeros((4, 8, 4), np.uint8)
    rows[..., 3] = 255
    rows[:2, :, 2] = 255                 # GL rows 0–1 (the bottom): blue
    rows[2:, :, 0] = 255                 # rows 2–3 (the top): red
    own.write(rows.tobytes())

    class OnGL(Still):
        def __init__(self):
            super().__init__(_rgba(2, 2))
            self.polls = 0

        def gl_poll(self):
            self.polls += 1
            return MediaFrame(None, 1.0, 1, texture=own.glo, tex_size=(8, 4))

    src = OnGL()
    m = _media(d=src)
    m.channels["d"].fit = 2
    r = _renderer(ctx, m, wires=[G.Wire("media.d", "output.1.image")])
    (pic,) = _draw(ctx, r, _empty(), size=(32, 32), frames=3)
    assert src.polls == 3 and src.reads == 0 and r._media_textures().uploads == 0
    assert tuple(pic[0, 16, :3]) == RED and tuple(pic[31, 16, :3]) == BLUE


@pytest.mark.skipif(not __import__("importlib").util.find_spec("syphon"),
                    reason="syphon-python is not installed")
def test_a_syphon_frame_samples_through_the_fit_pass(ctx):
    """Syphon's texture as the server publishes it, sampled by the fit
    pass: its colours land, the way up GL's (row 0 at the bottom). The
    spike read it as 2D; it is a rectangle (an IOSurface's), so it is
    blitted into the channel's own 2D texture on the GPU, never uploaded."""
    import gc

    import syphon
    from test_media_live import _gl_context

    from hyperspace.media.frame import TEX_RECT
    from hyperspace.media.source import READY
    from hyperspace.media.syphon import SyphonKind

    made = _gl_context()
    if made is None:
        pytest.skip("no GL context")
    glfw, win, gctx = made
    w, h = 64, 32
    tex = gctx.texture((w, h), 4)
    fbo = gctx.framebuffer([tex])
    fbo.use()
    gctx.clear(1.0, 0.0, 0.0, 1.0, viewport=(0, h // 2, w, h // 2))   # the top: red
    gctx.clear(0.0, 0.0, 1.0, 1.0, viewport=(0, 0, w, h // 2))        # the bottom: blue
    gctx.finish()
    srv = syphon.SyphonOpenGLServer("hs-t6-fit")
    src = f = r = m = None
    k = SyphonKind("syphon", {})
    k.open()
    try:
        src = None
        t0 = time.monotonic()
        while src is None and time.monotonic() - t0 < 6.0:
            srv.publish_frame_texture(tex.glo, size=(w, h))
            glfw.poll_events()
            k.poll(0.016, time.monotonic())
            src = next((s for sid, s in k.media_sources().items()
                        if sid.endswith("/hs-t6-fit")), None)
            time.sleep(0.016)
        assert src is not None, k.media_sources()
        src.open()
        f = None
        t0 = time.monotonic()
        while f is None and time.monotonic() - t0 < 3.0:
            srv.publish_frame_texture(tex.glo, size=(w, h))
            f = src.gl_poll()
            time.sleep(0.016)
        assert f is not None and src.status == READY
        assert f.tex_target == TEX_RECT                 # an IOSurface's: not 2D

        class Feed:
            kind, timed, duration, status = "syphon", False, 0.0, READY

            def open(self):
                pass

            def close(self):
                pass

            def want(self, t):
                pass

            def latest(self):
                return None

            def gl_poll(self):
                return src.gl_poll()

        m = _media(e=Feed())
        m.channels["e"].fit = 2
        r = _renderer(gctx, m, wires=[G.Wire("media.e", "output.1.image")])
        out = gctx.framebuffer(color_attachments=[gctx.renderbuffer((32, 32), 4)])
        vs = [View(Switches(), (32, 32), target=out)]
        errors = []
        for k_ in range(3):
            srv.publish_frame_texture(tex.glo, size=(w, h))
            _ = gctx.error             # (what Syphon's own calls left: not the frame's)
            r.draw_outputs(_empty(), 32, 32, 1.0, vs, t_now=2.0 + k_ / 60)
            errors.append(gctx.error)
        assert errors == ["GL_NO_ERROR"] * 3
        pic = _px(out)
        assert tuple(pic[2, 16, :3]) == RED and tuple(pic[29, 16, :3]) == BLUE
        mt = r._media_textures()
        assert mt.uploads == 0 and mt.blits >= 1 and mt.error == ""
        src.close()
        src.shut()
    finally:
        k.close()
        srv.stop()
        # everything holding the window's GL — Syphon's client, server and
        # image, the renderer — freed while its context is still current:
        # freed later, their deletes would land in whatever context is
        # current then (the module's: GL_INVALID_VALUE in the next test)
        if r is not None:
            r._media_textures().release()
        src = f = r = m = srv = k = None
        gc.collect()
        gctx.release()
        glfw.destroy_window(win)
        # the window's context was current: the module's is again, for the
        # tests after this one, in any order
        ctx.__enter__()


def test_render_thread_never_waits(ctx):
    """A still whose decode lands 0.3 s from now: twenty frames are drawn
    before it does, black under the scene, none waiting for it — then the
    still shows."""
    late = Late(_rgba(16, 9))
    r = _renderer(ctx, _media(a=late))
    s = _empty(backdrop=1)
    _draw(ctx, r, s)                                    # programs built, graph made
    t0 = time.perf_counter()
    late.start(0.3)
    for _ in range(20):
        (pic,) = _draw(ctx, r, s)
    took = time.perf_counter() - t0
    assert took < 0.3, took
    assert late.ready is None and (pic[..., :3] == 0).all()
    deadline = time.monotonic() + 3.0
    while late.ready is None and time.monotonic() < deadline:
        time.sleep(0.01)
    (pic,) = _draw(ctx, r, s)
    assert (pic[..., :3] == RED).all()


# ---------------------------------------------------------------- an effect after the scene

def test_an_effect_after_the_scene_sits_after_the_backdrop_too():
    """D1's `after: scene` (the acid-scene fixture's placement) over a
    backdrop sits after `grounded` — the scene laid over the channel — so
    it bends both rather than folding the see-through scene opaque; with no
    backdrop the graph is the base's, node for node."""
    placed = (G.EffectAt("acid", 2, after="scene"),)
    effects = ("acid", "acid.2")
    vs = [_view()]
    base = G.default_graph(vs, G.Wiring(placed=placed), effects=effects)
    assert base.nodes["acid.2"].inputs["image"] is base.nodes["scene"]
    on = G.default_graph(vs, G.Wiring(placed=placed, backdrop="a"), effects=effects)
    a2 = on.nodes["acid.2"]
    assert a2.inputs["image"] is on.nodes["grounded"]
    assert on.nodes["grounded"].inputs["over"] is on.nodes["scene"]
    assert on.nodes["history"].inputs["image"] is a2
    assert on.nodes["capture"].inputs["image"] is on.nodes["scene"]   # the scene alone
    hist = G.default_graph(vs, G.Wiring(placed=placed, backdrop="a", backdrop_history=True),
                           effects=effects)
    assert hist.nodes["capture"].inputs["image"] is hist.nodes["acid.2"]
    off = G.default_graph(vs, G.Wiring(placed=placed, backdrop=""), effects=effects)
    assert _names(off) == _names(base)


def test_the_backdrop_shows_through_an_effect_after_the_scene(ctx):
    """A red still under the scene with a second acid after the scene: the
    effect runs, and its picture still carries the red — bent, not
    covered by an opaque fold of the scene."""
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))))
    st = r.fx.state
    st.set_instances({"acid": 2})
    st.values["acid.2"].update(on=True, mix=1.0, twist=1.5, bend=0.05)
    assert not r.fx.compile_all()
    r.wiring = G.Wiring(placed=(G.EffectAt("acid", 2, after="scene"),))

    def red(pic):
        return ((pic[..., 0] > 200) & (pic[..., 1] < 60) & (pic[..., 2] < 60)).mean()

    (pic,) = _draw(ctx, r, _empty(backdrop=1), frames=2)
    assert "acid.2" in r.stats["effects"]
    assert r._graph.nodes["acid.2"].inputs["image"] is r._graph.nodes["grounded"]
    assert red(pic) > 0.5, red(pic)
    (shaped,) = _draw(ctx, r, _shape(backdrop=1), frames=2)
    assert "acid.2" in r.stats["effects"] and red(shaped) > 0.2, red(shaped)
