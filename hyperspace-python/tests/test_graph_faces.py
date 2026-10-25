"""Plan 33 T4 — the faces, the pattern's media layer and the backdrop are
graph inputs (`shape.faces`, `pattern.media`, `backdrop.image`), and a
branch is made once a frame at the size its consumer asks.

The owner's headline graph is a channel through its own shaders onto the
faces (`media.a → huecycle.2 → shape.faces`); the rest is what keeps it
honest: faces left unwired draw as they always did (no 1024² pass), a
channel that reads nothing leaves the pattern on the faces, a branch into
the pattern's layer keeps the channel's aspect, a branch lays under the
scene at `backdrop.alpha`, and a branch read at two sizes is made once per
size and leaks nothing.

The channels are the real `MediaState` over fake stills (test_media_render's
pattern): no file is read. The GL half skips without a standalone context."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import graph as G
from hyperspace.media.channels import MediaState
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View

ROOT = Path(__file__).resolve().parents[1]
RED, BLUE = (255, 0, 0), (0, 0, 255)


def _rgba(w: int, h: int, colour=RED, right=None) -> np.ndarray:
    px = np.zeros((h, w, 4), np.uint8)
    px[..., 3] = 255
    px[..., :3] = colour
    if right is not None:
        px[:, w // 2:, :3] = right
    return px


class Still:
    """A still that is there at once (or, `gone`, a feed lost)."""

    kind, timed, duration, status = "still", False, 0.0, "ready"

    def __init__(self, pixels: np.ndarray):
        self.f = MediaFrame(pixels, 1.0, 0)
        self.gone = False

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def want(self, t: float) -> None:
        pass

    def latest(self):
        return None if self.gone else self.f


def _media(**sources) -> MediaState:
    by_id = {f"file:/fake/{c}.png": s for c, s in sources.items()}
    m = MediaState(opener=lambda sid, resolver: by_id[sid])
    for c in sources:
        m.assign(c, 0, f"file:/fake/{c}.png")
    m.poll(0.0, 0.0)
    return m


def section(*pairs, nodes=()):
    return {"nodes": list(nodes), "wires": [{"from": a, "to": b} for a, b in pairs]}


def _instance(file: str, n: int) -> dict:
    return {"kind": "effect", "file": file, "instance": n}


def test_the_faces_wires_are_the_wiring_now():
    """T4 builds what T3 held back: the faces' run, a branch onto the faces
    and into the pattern's layer are wires of the wiring; a channel straight
    into `backdrop.image` is the wiring's backdrop (the plan 32 path, node
    for node), a branch into it is a wire."""
    spec = G.read_graph(section(("frame", "fx.image"), ("pattern", "kaleido.image"),
                                ("kaleido", "shape.faces"), ("media.b", "pattern.media"),
                                ("media.c", "backdrop.image")))
    w = spec.wiring()
    assert w.backdrop == "c" and w.run == ()
    assert set(w.wires) == {G.Wire("pattern", "kaleido.image"), G.Wire("kaleido", "shape.faces"),
                            G.Wire("media.b", "pattern.media")}
    branch = G.read_graph(section(("frame", "fx.image"), ("media.b", "kaleido.2.image"),
                                  ("kaleido.2", "backdrop.image"),
                                  nodes=[_instance("kaleido", 2)])).wiring()
    assert branch.backdrop == "" and G.Wire("kaleido.2", "backdrop.image") in branch.wires


def test_the_faces_nodes_are_built_from_the_wires():
    """The pattern node, the shape's `faces` port, the backdrop's sink: the
    pattern node exists only when a wire touches it, `shape.faces` reads
    what is wired, and a branch under the scene is `grounded`'s `under`."""
    vs = [View(Switches(), (64, 48))]
    plain = G.build_graph(vs, G.Wiring(run=()), effects=("acid",))
    assert "pattern" not in plain.nodes and plain.nodes["shape"].inputs["faces"] is None
    assert G.Shape.INPUTS == {"faces": G.IMAGE}
    assert G.PatternNode.KIND == "pattern" and G.PatternNode.INPUTS == {"media": G.IMAGE}
    assert G.PatternNode.OUTPUT == G.IMAGE and G.PatternNode.MAKES
    assert G.BackdropNode.KIND == "backdrop" and G.BackdropNode.INPUTS == {"image": G.IMAGE}
    assert G.BackdropNode.OUTPUT is None
    spec = G.read_graph(section(("frame", "fx.image"), ("pattern", "acid.image"),
                                ("acid", "shape.faces")))
    g = G.build_graph(vs, spec.wiring(), effects=("acid",))
    pat, acid = g.nodes["pattern"], g.nodes["acid"]
    assert isinstance(pat, G.PatternNode) and acid.inputs["image"] is pat
    assert g.nodes["shape"].inputs["faces"] is acid and "acid" not in g.run
    order = [n.name for n in g.order]
    assert order.index("pattern") < order.index("acid") < order.index("shape")
    # a channel straight into the pattern's layer: no fitted node of its own
    spec = G.read_graph(section(("frame", "fx.image"), ("media.a", "pattern.media")))
    g = G.build_graph(vs, spec.wiring())
    assert g.nodes["pattern"].channel == "a" and not [n for n in g.nodes if n.startswith("media")]
    assert g.timed == G.build_graph(vs, G.Wiring(run=())).timed
    # a branch under the scene
    spec = G.read_graph(section(("frame", "fx.image"), ("media.b", "kaleido.2.image"),
                                ("kaleido.2", "backdrop.image"),
                                nodes=[_instance("kaleido", 2)]))
    g = G.build_graph(vs, spec.wiring(), effects=("kaleido", "kaleido.2"))
    under = g.nodes["backdrop"].inputs["under"]
    assert isinstance(under, G.Effect) and under.effect == "kaleido.2"
    assert g.nodes["backdrop"].under_alpha_of == "backdrop_alpha"
    assert g.nodes["scene"].ground == 0.0 and g.nodes["lookback"].inputs["image"].name == "backdrop"
    # (plan 35 T4: the backdrop is the composite itself — no sink beside it)
    assert isinstance(g.nodes["backdrop"], G.Composite)


def test_the_sizes_a_port_asks():
    """`Node.size_for`: the frame's size but for the faces (`FACE_PIC`²)
    and the pattern's layer (its head's own size: a channel's texture, else
    `FACE_PIC`²); an effect asks its input for what its consumer asked."""
    from types import SimpleNamespace

    face = (G.FACE_PIC, G.FACE_PIC)
    frame = SimpleNamespace(size=(320, 200), r=SimpleNamespace(
        media_texture=lambda c: SimpleNamespace(size=(64, 32)) if c == "a" else None))
    assert G.Node("x").size_for("image", frame) == (320, 200)
    assert G.Shape("shape").size_for("faces", frame) == face
    media = G.MediaNode("media.a", "a")
    eff = G.Effect("acid", image=media)
    assert eff.size_for("image", frame) == (320, 200)
    assert G.PatternNode("pattern", media=eff).size_for("media", frame) == (64, 32)
    gone = G.MediaNode("media.b", "b")
    assert G.PatternNode("pattern", media=gone).size_for("media", frame) == face
    assert G.PatternNode("pattern").size_for("media", frame) == face


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


def _empty(**kw):
    from hyperspace.view import ViewState

    return ViewState(lines=False, points=False, faces=False, **kw)


def _renderer(ctx, media=None, pairs=(), nodes=(), instances=None, values=None):
    """A renderer over `media` whose wiring is the section `pairs` says (a
    run's head always: the section as a load lands it)."""
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    st = r.fx.state
    if instances:
        st.set_instances(instances)
    for name, v in (values or {}).items():
        st.values[name].update(v)
    spec = G.read_graph(section(("frame", "fx.image"), *pairs, nodes=nodes),
                        effects=set(st.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r


def _draw(ctx, r, s, size=(160, 120), views=None, frames=1):
    vs = views or [View(Switches(), size, target=_fbo(ctx, *size))]
    for k in range(frames):
        r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def _centre(px, d=4):
    h, w = px.shape[:2]
    return px[h // 2 - d: h // 2 + d, w // 2 - d: w // 2 + d, :3].reshape(-1, 3)


HUE = {"huecycle": 2}
HUE_ON = {"huecycle.2": {"on": True, "mix": 1.0}}


def test_a_channel_through_effects_lands_on_the_faces(ctx):
    """The headline: a red still on a, `media.a → huecycle.2 → shape.faces`
    at mix 1 — the faces show the still through the effect (its clock a
    third of a turn on: red turned to green), neither red nor the pattern.
    The wire to the faces removed, huecycle.2 reaches nothing and the frame
    is the frame with no media."""
    plain = _draw(ctx, _renderer(ctx), _faces())[0]
    pairs = [("media.a", "huecycle.2.image"), ("huecycle.2", "shape.faces")]
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))), pairs, [_instance("huecycle", 2)],
                  HUE, HUE_ON)
    r.fx.state.phase["huecycle.2"] = 1 / 3
    (got,) = _draw(ctx, r, _faces())
    assert r.face_error == "" and "huecycle.2" in r.stats["effects"]
    c, base = _centre(got), _centre(plain)
    assert not (c[:, 0] > 2 * c[:, 1] + 20).any(), c[:4]               # not red
    assert (c[:, 1] > c[:, 0] + 20).mean() > 0.9, c[:4]                # turned: green
    assert not np.array_equal(c, base)                                 # and not the pattern
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))), pairs[:1], [_instance("huecycle", 2)],
                  HUE, HUE_ON)
    (cut,) = _draw(ctx, r, _faces())
    assert np.array_equal(cut, plain) and "huecycle.2" not in r.stats["effects"]


def _tool():
    if "golden_frames" in sys.modules:
        return sys.modules["golden_frames"]
    spec = importlib.util.spec_from_file_location("golden_frames",
                                                  ROOT / "tools" / "golden_frames.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["golden_frames"] = mod
    spec.loader.exec_module(mod)
    return mod


def _rig_frame(ctx, slug, wiring=None, size=(240, 150), frames=4):
    """`slug` loaded as the golden tool loads it (its section landed, or the
    renderer's wiring then replaced by `wiring`), `frames` frames; the last
    picture and the renderer."""
    tool = _tool()
    rig = tool.Rig(slug, "absent", ctx)
    if wiring is not None:
        rig.renderer.wiring = wiring
    try:
        f = _fbo(ctx, *size)
        vs = [View(Switches(), size, target=f)]
        for _ in range(frames):
            rig.frame(vs, size, 1.0)
        assert ctx.error == "GL_NO_ERROR"
        return _px(f), rig.renderer
    finally:
        rig.close()


def test_faces_unwired_draw_as_today(ctx):
    """PARTY-FACES, its section landed (a run, faces unwired): every pixel
    is the frame the pre-plan-33 wiring draws — the faces drawn per face
    with no 1024² pass and nothing of the faces' picture allocated."""
    got, r = _rig_frame(ctx, "party-faces")
    assert r.wiring.wired and not [w for w in r.wiring.wires          # (plan 35: wired)
                                             if w.dst == "shape.faces"]
    assert r.face_pic.tex is None and r._pic is None and not getattr(r, "_pools", {})
    base, _ = _rig_frame(ctx, "party-faces", wiring=G.Wiring())
    assert got[..., :3].max() > 40 and np.array_equal(got, base)


def test_faces_fall_back_to_the_pattern_when_the_branch_reads_nothing(ctx):
    """Review Focus 4: the channel feeding the faces has nothing (an empty
    slot), or loses its feed mid-show: the faces show the pattern that
    frame — the faces-unwired frame — never black."""
    s = _faces(pattern=2)
    unwired = _draw(ctx, _renderer(ctx, _media()), s)[0]
    assert unwired[..., :3].max() > 40
    pairs = [("media.a", "huecycle.2.image"), ("huecycle.2", "shape.faces")]
    r = _renderer(ctx, _media(), pairs, [_instance("huecycle", 2)], HUE, HUE_ON)
    (got,) = _draw(ctx, r, s)
    assert np.array_equal(got, unwired) and r.face_error == "" and r._pic is None
    still = Still(_rgba(16, 9))
    r = _renderer(ctx, _media(a=still), pairs, [_instance("huecycle", 2)], HUE, HUE_ON)
    (shown,) = _draw(ctx, r, s)
    assert not np.array_equal(shown, unwired)
    still.gone = True                                         # the feed lost
    (lost,) = _draw(ctx, r, s)
    assert np.array_equal(lost, unwired)


def test_a_branch_into_pattern_media_keeps_the_channels_aspect(ctx):
    """A 2:1 still through an effect into `pattern.media`: the picture the
    pattern's layer draws is made at the channel's own size (2:1, as
    `view.media_scale` expects), not the raw texture and not a square."""
    pairs = [("media.a", "huecycle.2.image"), ("huecycle.2", "pattern.media")]
    r = _renderer(ctx, _media(a=Still(_rgba(32, 16))), pairs, [_instance("huecycle", 2)],
                  HUE, HUE_ON)
    seen = []
    real = r.draw_scene

    def spy(s, *a, **k):
        seen.append(r._face_media(s))
        return real(s, *a, **k)

    r.draw_scene = spy
    _draw(ctx, r, _faces(media_alpha=0.8))
    (tex, upright), = seen
    assert tex.size == (32, 16) and tex is not r.media_texture("a") and upright
    assert "huecycle.2" in r.stats["effects"]


def test_a_branch_under_the_scene(ctx):
    """`media.b → kaleido.2.image`, `kaleido.2 → backdrop.image`: an empty
    shape's frame is the still, folded by the kaleidoscope at the frame's
    size, at `backdrop.alpha` over the black ground."""
    size = (96, 64)
    m = _media(b=Still(_rgba(16, 9, RED, right=BLUE)))
    m.channels["b"].fit = 2                                   # stretch: fills
    pairs = [("media.b", "kaleido.2.image"), ("kaleido.2", "backdrop.image")]
    r = _renderer(ctx, m, pairs, [_instance("kaleido", 2)], {"kaleido": 2},
                  {"kaleido.2": {"on": True, "mix": 1.0}})
    (got,) = _draw(ctx, r, _empty(backdrop_alpha=0.5), size=size)
    assert "kaleido.2" in r.stats["effects"] and "backdrop" in r._graph.nodes
    # the reference: the same pass over the fitted still, by hand
    src = r._media_fit("b", size)
    out = ctx.texture(size, 4)
    fbo = ctx.framebuffer(color_attachments=[out])
    r.fx.run_one("kaleido.2", src, fbo, 2.0)
    ref = np.frombuffer(out.read(), np.uint8).reshape(size[1], size[0], 4)[::-1].astype(int)
    want = np.round(ref[..., :3] * 0.5)
    assert np.abs(got[..., :3] - want).max() <= 2
    straight = _renderer(ctx, m, [("media.b", "backdrop.image")])
    (plain,) = _draw(ctx, straight, _empty(backdrop_alpha=0.5), size=size)
    assert np.abs(got[..., :3] - plain[..., :3]).max() > 40     # the fold shows


def test_a_branch_read_at_two_sizes_is_made_once_each_and_does_not_leak(ctx):
    """Review Focus 5: acid.2 read by the faces (1024²) and by output 2's
    picture (the frame's size) runs two passes a frame — one per size — and
    neither the effects' pool nor the sized pools grow over 100 frames."""
    size = (160, 120)
    pairs = [("media.a", "acid.2.image"), ("acid.2", "shape.faces"),
             ("acid.2", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9, RED, right=BLUE))), pairs,
                  [_instance("acid", 2)], {"acid": 2}, {"acid.2": {"on": True, "mix": 1.0}})
    vs = [View(Switches(), size, target=_fbo(ctx, *size)),
          View(Switches(), size, target=_fbo(ctx, *size))]
    s = _faces()
    counts = []
    for k in range(110):
        r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
        counts.append(r.stats["effects"].count("acid.2"))
        if k == 9:
            at10 = (len(r.fx._tex), {k: len(v) for k, v in r._pools.items()}, len(r._frames))
    assert ctx.error == "GL_NO_ERROR"
    assert set(counts) == {2}
    assert (len(r.fx._tex), {k: len(v) for k, v in r._pools.items()}, len(r._frames)) == at10
    assert (G.FACE_PIC, G.FACE_PIC) in r._pools


def test_a_solid_draw_that_raises_leaves_no_face_layer_behind():
    """Final review (11): the shape's `prepare` sets the faces' layer and
    picture for the one scene pass; a solid geometry drawn between prepare
    and the shape's draw that raises must not leave them for the next
    pass — `Scene.run` puts both back whatever happens."""
    from contextlib import nullcontext
    from types import SimpleNamespace as NS

    class Solid(G.Node):
        KIND, OUTPUT, SOLID = "solidtest", G.GEOMETRY, True

        def draw(self, frame, clear=True):
            raise RuntimeError("solid draw failed")

    class Faces(G.Node):
        KIND, OUTPUT = "facestest", G.GEOMETRY

        def prepare(self, frame):
            frame.r._face_layer, frame.r._pic = "layer", "pic"

        def draw(self, frame, clear=True):
            frame.r._face_layer, frame.r._pic = False, None

    fbo = NS(use=lambda: None)
    r = NS(scene=NS(ensure=lambda *a: None, draw_fbo=fbo, resolve=lambda: None),
           _blank=NS(use=lambda location: None), clear_scene=lambda: None,
           _face_layer=False, _pic=None)
    frame = NS(r=r, ctx=NS(viewport=None), size=(8, 8), samples=0,
               timed=lambda name: nullcontext())
    scene = G.Scene("scene", geometries=[Solid("solid"), Faces("faces")])
    with pytest.raises(RuntimeError):
        scene.run(frame)
    assert r._face_layer is False and r._pic is None
