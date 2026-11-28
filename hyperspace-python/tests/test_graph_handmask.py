"""The hand mask: the polygon a hands node's thumbs and index fingers make on
screen, as a mask (`graph.HandMaskNode`, `graph.hand_polygon`,
`masks.MaskPasses.polygon`).

Each hand's thumb tip and index tip go through the camera the hands are
drawn with — the hands layer's, or the scene's — to the frame's pixels, and
the four are filled as one closed polygon. Synthetic hands (`test_ghost`'s
`both` and `tracker`); no tracker, window or screen.
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import numpy as np
import pytest
from test_ghost import both, tracker
from test_graph_resize import FACTORY_FRAME
from test_graph_wired import wired

from hyperspace import ghost, masks, params
from hyperspace import graph as G
from hyperspace.outputs import Switches, View
from hyperspace.view import HANDMASK_EYES, HandMaskState

HANDMASK = {"kind": "handmask"}
CUT = {"kind": "cut"}


def _spec(*pairs, nodes=(HANDMASK,)):
    spec = G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=list(nodes)))
    assert not spec.notes, spec.notes
    return spec


# ---------------------------------------------------------------- no GL

def _pose(side, thumb, index, fade=1.0):
    j = np.zeros((5, 5, 3))
    j[0, 4], j[1, 4] = thumb, index
    return NS(side=side, joints=j, fade=fade)


# a flat camera: x, y straight through to NDC
FLAT = np.eye(4)


def test_the_polygon_is_the_four_fingertips_in_pixels_round_their_centre():
    """Left thumb, left index, right index, right thumb through the camera to
    the frame's pixels (first row at the bottom), in order round their centre
    whatever order the hands came in — so the polygon never crosses itself."""
    now = ghost.Settled([_pose("right", (0.5, -0.5, 0), (0.5, 0.5, 0)),
                         _pose("left", (-0.5, -0.5, 0), (-0.5, 0.5, 0))], FLAT, None)
    pts, strength, why = G.hand_polygon(now, 1, (200, 100))
    assert why == "" and strength == 1.0
    assert sorted(map(tuple, pts.round(6).tolist())) == [(50.0, 25.0), (50.0, 75.0),
                                                         (150.0, 25.0), (150.0, 75.0)]
    # round the centre: consecutive corners share an x or a y (no diagonal edge)
    for a, b in zip(pts, np.roll(pts, -1, axis=0), strict=True):
        assert a[0] == b[0] or a[1] == b[1]


def test_the_polygon_is_seen_through_the_layers_eye_or_the_scenes():
    """`eye` 0 (the default) projects through the hands layer's camera
    (`Settled.layer`), 1 through the scene's — and a settle with no layer
    camera falls back to the scene's."""
    assert HANDMASK_EYES == ("layer", "scene") and HandMaskState().eye == 0
    half = np.diag([0.5, 0.5, 1.0, 1.0])
    poses = [_pose("left", (-1, -1, 0), (-1, 1, 0)), _pose("right", (1, -1, 0), (1, 1, 0))]
    now = ghost.Settled(poses, FLAT, None, layer=(half, None))
    layer = G.hand_polygon(now, 0, (100, 100))[0]
    scene = G.hand_polygon(now, 1, (100, 100))[0]
    assert layer.min() == 25.0 and layer.max() == 75.0
    assert scene.min() == 0.0 and scene.max() == 100.0
    alone = ghost.Settled(poses, FLAT, None)
    assert np.array_equal(G.hand_polygon(alone, 0, (100, 100))[0], scene)


def test_both_hands_are_needed_and_the_mask_fades_with_the_fainter():
    poses = [_pose("left", (-1, -1, 0), (-1, 1, 0), fade=0.25),
             _pose("right", (1, -1, 0), (1, 1, 0), fade=0.8)]
    assert G.hand_polygon(ghost.Settled(poses, FLAT, None), 1, (10, 10))[1] == 0.25
    one = G.hand_polygon(ghost.Settled(poses[1:], FLAT, None), 1, (10, 10))
    assert one == (None, 0.0, G.HANDMASK_ONE_HAND)
    assert G.hand_polygon(None, 1, (10, 10)) == (None, 0.0, G.HANDMASK_NO_HANDS)
    # a palm-only skeleton has no fingertips: no hand for the polygon
    palm = NS(side="left", joints=np.zeros((0, 5, 3)), fade=1.0)
    got = G.hand_polygon(ghost.Settled([palm, poses[1]], FLAT, None), 1, (10, 10))
    assert got[2] == G.HANDMASK_ONE_HAND
    # a hand faded out is gone
    gone = [poses[0], _pose("right", (1, -1, 0), (1, 1, 0), fade=0.0)]
    assert G.hand_polygon(ghost.Settled(gone, FLAT, None), 1, (10, 10))[2] == G.HANDMASK_ONE_HAND


def test_a_fingertip_behind_the_eye_makes_no_polygon():
    behind = np.eye(4)
    behind[3] = (0.0, 0.0, -1.0, 0.0)            # w = −z: a point at z ≥ 0 is behind
    poses = [_pose("left", (-1, -1, 1), (-1, 1, -1)), _pose("right", (1, -1, -1), (1, 1, -1))]
    assert G.hand_polygon(ghost.Settled(poses, behind, None), 1, (10, 10))[2] == G.HANDMASK_BEHIND


def test_a_hand_mask_reads_round_trips_and_takes_only_hands():
    spec = _spec(("hands", "handmask.hands"), ("channel.a", "cut.image"),
                 ("handmask", "cut.mask"), ("cut", "output.2.image"), nodes=(HANDMASK, CUT))
    assert spec.handmasks == (G.HandMaskAt(1),)
    assert {"kind": "handmask"} in spec.to_json()["nodes"]
    assert G.HandMaskAt(2).to_json() == {"kind": "handmask", "instance": 2}
    assert G.read_graph(spec.to_json()).handmasks == spec.handmasks
    bad = G.read_graph(wired(("shape", "handmask.hands"), ("handmask", "output.2.image"),
                             *FACTORY_FRAME, nodes=[HANDMASK]))
    took = G.HANDMASK_TAKES_HANDS.format(dst="handmask.hands")
    assert bad.notes == (f"wire shape → handmask.hands — {took}",)
    pic = G.read_graph(wired(("channel.a", "cut.mask"), ("cut", "output.2.image"),
                             ("channel.a", "cut.image"), *FACTORY_FRAME, nodes=[CUT]))
    assert pic.notes            # (a picture is never a mask: the rule stands)
    # a hand mask's name is reserved: no effect file is named for it
    assert not G._PLACE_EFFECT.fullmatch("handmask")


def test_the_graph_builds_the_hand_mask_on_its_hands_node():
    spec = _spec(("hands", "handmask.hands"), ("channel.a", "cut.image"),
                 ("handmask", "cut.mask"), ("cut", "output.2.image"), nodes=(HANDMASK, CUT))
    g = G.build_graph([View(Switches(), (64, 48)) for _ in range(2)], spec.wiring())
    hm = next(n for n in g.order if isinstance(n, G.HandMaskNode))
    assert isinstance(hm.inputs["hands"], G.Hands)
    cut = next(n for n in g.order if isinstance(n, G.CutNode))
    assert cut.inputs["mask"] is hm
    assert g.order.index(hm.inputs["hands"]) < g.order.index(hm)


def test_declare_handmasks_comes_and_goes():
    reg = params.Registry()
    params.declare_handmasks(reg, ["handmask", "handmask.2"])
    ids = [p.id for p in reg if p.group == params.HANDMASK_GROUP]
    assert ids == [*params.handmask_ids("handmask"), *params.handmask_ids("handmask.2")]
    assert params.handmask_ids("handmask") == ["handmask.eye", "handmask.grow",
                                                "handmask.feather", "handmask.invert"]
    assert all(params.is_handmask_id(i) for i in ids)
    assert not params.is_handmask_id("handmask.key") and not params.is_handmask_id("cut.invert")
    assert params.HANDMASK_GROUP in params.PATCH_GROUPS
    reg["handmask.2.grow"].set(12.0)
    assert reg["handmask.grow"].lo == -64.0 and reg["handmask.feather"].hi == 32.0
    assert reg["handmask.eye"].choices == list(HANDMASK_EYES)
    assert all(reg[i].modulatable for i in ids)
    assert reg.handmask_state["handmask.2"].grow == 12.0
    params.declare_handmasks(reg, ["handmask"])
    assert [p.id for p in reg if p.group == params.HANDMASK_GROUP] == \
        params.handmask_ids("handmask")
    assert list(reg.handmask_state) == ["handmask"]


def test_the_canvas_knows_the_hand_mask():
    from hyperspace import graphview as gv

    assert gv.LABELS["handmask"] == "Hand mask"
    assert gv.PICKER_GROUP["handmask"] == "masks"
    assert gv.FRAME_CLASS["handmask"] is G.HandMaskNode
    assert gv.drop_refusal("handmask") == gv.MASK_NODE.format(label="Hand mask")
    stand = gv._stand_in("handmask")
    assert stand.said == G.HANDMASK_UNWIRED


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")

SIZE = (96, 64)
OUT = [("hands", "handmask.hands"), ("handmask", "output.2.image")]


def frame_hands() -> dict:
    """Both hands open, each thumb's tip moved 120 mm below its index tip: the
    four fingertips a frame on screen, as a performer's two L-shapes make."""
    sk = both("open", "open")
    for side in sk.values():
        d = side["digits"]
        d[0][3]["next"] = tuple(np.asarray(d[1][3]["next"], float) + (0.0, -120.0, 0.0))
    return sk


def _renderer(ctx, pairs=OUT, skel=None, nodes=(HANDMASK,)):
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    spec = _spec(*pairs, nodes=nodes)
    r.wiring = spec.wiring()
    g = r.ghost
    g.state.on, g.state.alpha, g.state.guide = True, 1.0, 0
    g.source = tracker(frame_hands() if skel is None else skel)
    return r


def _s(**kw):
    from hyperspace.view import ViewState

    return ViewState(lines=False, points=False, faces=False,
                     handmasks={"handmask": HandMaskState(**kw)})


def _fbo(ctx, w, h):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4)])


def _draw(ctx, r, s, frames=12):
    vs = [View(Switches(), SIZE, target=_fbo(ctx, *SIZE)) for _ in range(2)]
    for k in range(frames):                  # (the hands fade in over the first frames)
        r.draw_outputs(s, *SIZE, 1.0, vs, t_now=2.0 + k / 10)
    assert ctx.error == "GL_NO_ERROR"
    return vs


def _mask(r):
    keys = [k for k in r._frames if isinstance(k, tuple) and k[0] == "handmask#mask"]
    assert len(keys) == 1, keys
    tex = r._frames[keys[0]][0]
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w).astype(int)   # first row bottom


def _inside(pts, x, y) -> bool:
    """Even-odd: is pixel centre (x, y) inside polygon `pts`?"""
    inside = False
    for (ax, ay), (bx, by) in zip(pts, np.roll(pts, 1, axis=0), strict=True):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def test_the_mask_passes_inside_the_fingertips_polygon(ctx):
    """Wired from the hands, the mask passes inside the polygon the four
    fingertips make through the layer's camera and nowhere else, give or
    take the one-pixel anti-aliased edge."""
    r = _renderer(ctx)
    _draw(ctx, r, _s())
    pts, strength, why = G.hand_polygon(r.ghost.now, 0, SIZE)
    assert why == "" and strength == 1.0
    m = _mask(r)
    assert m.max() == 255 and m.min() == 0
    inside = np.array([[_inside(pts, x + 0.5, y + 0.5) for x in range(SIZE[0])]
                       for y in range(SIZE[1])])
    assert inside.sum() > 100
    # every pixel well inside passes and every one well outside does not
    far = _far_from_edge(pts, 1.5)
    assert (m[inside & far] == 255).all()
    assert (m[~inside & far] == 0).all()


def _far_from_edge(pts, d):
    ys, xs = np.mgrid[0:SIZE[1], 0:SIZE[0]] + 0.5
    best = np.full(xs.shape, np.inf)
    for a, b in zip(pts, np.roll(pts, 1, axis=0), strict=True):
        e = b - a
        t = np.clip(((xs - a[0]) * e[0] + (ys - a[1]) * e[1]) / max(e @ e, 1e-9), 0, 1)
        best = np.minimum(best, np.hypot(xs - a[0] - t * e[0], ys - a[1] - t * e[1]))
    return best > d


def test_grow_and_invert_move_the_edge(ctx):
    r = _renderer(ctx)
    _draw(ctx, r, _s())
    plain = (_mask(r) > 127).sum()
    r2 = _renderer(ctx)
    _draw(ctx, r2, _s(grow=6.0))
    assert (_mask(r2) > 127).sum() > plain
    r3 = _renderer(ctx)
    _draw(ctx, r3, _s(grow=-4.0))
    assert (_mask(r3) > 127).sum() < plain
    r4 = _renderer(ctx)
    _draw(ctx, r4, _s(invert=True))
    assert (_mask(r4) > 127).sum() == SIZE[0] * SIZE[1] - plain


def test_one_hand_makes_a_mask_that_passes_nothing(ctx):
    one = frame_hands()
    del one["right"]
    r = _renderer(ctx, skel=one)
    _draw(ctx, r, _s())
    assert _mask(r).max() == 0
    hm = next(n for n in r._graph.order if isinstance(n, G.HandMaskNode))
    assert hm.said == hm.refused == G.HANDMASK_ONE_HAND


def _px(f) -> np.ndarray:
    w, h = f.size
    return np.frombuffer(f.read(components=4), np.uint8).reshape(h, w, 4).astype(int)


def test_the_hand_mask_cuts_a_picture(ctx):
    """Into a cut's mask, the hands' polygon cuts the scene: outside it the
    output is the ground where, uncut, the shape draws."""
    from hyperspace.view import ViewState

    def shown(pairs, nodes):
        r = _renderer(ctx, pairs=pairs, nodes=nodes)
        s = ViewState(handmasks={"handmask": HandMaskState(grow=8.0)})
        vs = _draw(ctx, r, s)
        return r, _px(vs[1].target)

    _, whole = shown([("hands", "handmask.hands"), ("scene", "output.2.image")], (HANDMASK,))
    r, cut = shown([("hands", "handmask.hands"), ("scene", "cut.image"),
                    ("handmask", "cut.mask"), ("cut", "output.2.image")], (HANDMASK, CUT))
    m = _mask(r)
    out, inn = m == 0, m == 255
    assert out.any() and inn.any()
    assert whole[..., :3][out].any()                  # the shape draws outside the hands…
    assert not cut[..., :3][out].any()                # …and the cut takes it away there
    assert np.array_equal(cut[inn], whole[inn])       # inside, the scene as it was


def test_the_polygon_pass_fills_a_polygon(ctx):
    store = {}

    def target(key, size, dtype="f1", components=4):
        if key not in store:
            t = ctx.texture(size, components, dtype=dtype)
            store[key] = (t, ctx.framebuffer([t]))
        return store[key]

    mp = masks.MaskPasses(ctx, target)
    tex = mp.polygon([(10, 10), (50, 10), (50, 40), (10, 40)], "m", (64, 48))
    a = np.frombuffer(tex.read(), np.uint8).reshape(48, 64)
    assert a[25, 30] == 255 and a[5, 5] == 0 and a[45, 60] == 0
    assert a[25, 9] == 0 and a[25, 10] == 255
    half = np.frombuffer(mp.polygon([(10.5, 10), (50, 10), (50, 40), (10.5, 40)], "m", (64, 48)
                                    ).read(), np.uint8).reshape(48, 64)
    assert half[25, 10] in (127, 128)            # (a pixel centred on the edge: half way)
    soft = np.frombuffer(mp.polygon([(10, 10), (50, 10), (50, 40), (10, 40)], "m", (64, 48),
                                    feather=10.0, strength=0.5).read(), np.uint8).reshape(48, 64)
    assert soft[25, 30] in range(126, 130) and 0 < soft[25, 12] < soft[25, 30]
    none = np.frombuffer(mp.polygon([], "m", (64, 48), invert=True).read(), np.uint8)
    assert (none == 255).all()
    mp.release()
