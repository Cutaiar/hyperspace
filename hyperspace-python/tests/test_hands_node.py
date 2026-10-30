"""Plan 26 A3: the hands as a geometry node — in the scene or as a layer,
composited anywhere; the history as wiring.

The hands (`ghost.py`'s styles) draw through the shape's eye after the
Leap calibration (`ghost.shared_camera`), settled once a frame by the
graph's `Hands` node. With `Wiring(hands="scene")` they are solid
geometry inside the scene, drawn before the see-through shape, so the
shape's depth puts a hand in front of or behind it; as a layer they have
their own colour and depth, and a depth-aware composite hides the layer
where the shape's visible surface is nearer. The history captures what
it is wired to. `tests/test_graph.py` holds the graphs' shapes;
`tests/test_golden_frames.py` the pictures, byte for byte.

Offscreen renders from synthetic hands (`fake_hands`, test_ghost's pose);
no window, screen or tracker.
"""

from __future__ import annotations

import numpy as np
import pytest
from test_ghost import both, tracker
from test_outputs import H, W, fbo, keep_run, px, rig, scene_view, views
from wiredframe import Thru, wire_switches

from hyperspace import ghost as G
from hyperspace import outputs as O
from hyperspace.graph import HandsAt, Wiring
from hyperspace.graphmigrate import wired_wiring
from hyperspace.hands import core as hc

S = O.Switches

# ---------------------------------------------------------------- no GL


def _screen(vp, q, w, h):
    c = np.c_[q, np.ones(len(q))] @ vp.T
    return np.c_[(c[:, 0] / c[:, 3] + 1) * w / 2, (1 - c[:, 1] / c[:, 3]) * h / 2]


def _joints() -> np.ndarray:
    m = G.basis("desktop")
    pts = []
    for side, sk in both().items():
        p = G.pose(side, sk, m)
        pts += [p.joints.reshape(-1, 3), p.palm[None]]
    return np.concatenate(pts)


# the measured offsets of the hands' extent (4.3, 8.4 and 2.4 px), with a little margin
PX = {(960, 600): 5.0, (1920, 1080): 10.0, (1512, 982): 5.0}


@pytest.mark.parametrize("size", [(960, 600), (1920, 1080), (1512, 982)])
def test_the_default_calibration_puts_the_hands_where_the_ghost_camera_did(size):
    """The hands now draw through the shape's eye (47.6° across the
    shorter side), not the ghost camera's own (38° vertical, fitted to
    each output): a calibration of scale and offset cannot match it
    exactly. The default ("from the box") fits the padded box into a
    16:9 picture (`ghost.CAL_ASPECT`), so on a landscape output the
    hands' extent lands within 5 px of where it was at 16:10 and 10 px
    at 1080p."""
    w, h = size
    m, box = G.basis("desktop"), G.box_of(None)
    q = _joints()
    old = _screen(G.camera(box, m, w / h)[0], q, w, h)
    new = _screen(G.shared_camera(box, m, w / h)[0], q, w, h)
    for k in (0, 1):
        assert abs(old[:, k].min() - new[:, k].min()) < PX[size]
        assert abs(old[:, k].max() - new[:, k].max()) < PX[size]
    # the calibration is the room's, not the output's: the same world
    # whatever the output's shape
    assert np.allclose(G.calibration(box, m), G.calibration(box, m, aspect=G.CAL_ASPECT))


def test_the_ghost_settles_its_hands_once_through_the_shared_camera():
    """`Ghost.settle` is the frame's poses and camera, through the eye the
    view hands it (`eye.*`) and the source's calibration; the fades step
    only there, so the scene and the layer draw the same frame."""
    import moderngl

    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    try:
        gh = G.Ghost(ctx)
        gh.state.on = True
        gh.source = tracker()
        gh.source.units = hc.Units(mm=150.0, origin=(0.0, 200.0, 0.0), tilt=10.0)
        poses, vp, eye = gh.settle(1.0, 1.6, 50.0, 4.0)
        want, want_eye = G.shared_camera(G.box_of(gh.source), G.basis("desktop"), 1.6,
                                         gh.source.units, fov=50.0, distance=4.0)
        assert np.allclose(vp, want) and np.allclose(eye, want_eye)
        assert gh.now is not None and gh.now[1] is vp
        fades = [p.fade for p in poses]
        gh.settle(1.0 + 1 / 60, 1.6)
        assert [p.fade for p in gh.now[0]] > fades or fades == [1.0, 1.0]
    finally:
        ctx.release()


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


# the hands placed in the world by hand: 200 mm a shape unit, no tilt, the
# palms ~2 units toward the eye from the shape's centre (FRONT) or ~2 away
# from it (BEHIND); the shape's radius is about 1
FRONT, BEHIND = -400.0, 400.0


def _rig(ctx, wiring=None, z0=None, *, effects=(), shape=True, **kw):
    r = rig(ctx, effects=effects, **kw)
    if wiring is not None:
        # (plan 33 R23: the rig's run kept; plan 36 T4: its look-back drawn
        # while the rig's `dream.on` is on, as the old words had it)
        from hyperspace.graphmigrate import look_of
        st = r.lookback.state
        r.wiring = wired_wiring(keep_run(r, wiring),
                                look_of({"dream.on": bool(st.on), "dream.mix": 0.0}))
    if z0 is not None and r.ghost.source is not None:
        r.ghost.source.units = hc.Units(mm=200.0, origin=(0.0, 205.0, z0), tilt=0.0)
    r._no_shape = not shape
    return r


def _draw(ctx, r, vs, frames=4, t0=2.0):
    """`frames` frames of `draw_outputs`; each target view's picture."""
    s = scene_view()
    s.lines, s.bright = True, 1.6
    if getattr(r, "_no_shape", False):
        s.instances = 0
    for k in range(frames):
        s.ang = [a + 0.05 for a in s.ang]
        r.draw_outputs(s, W, H, 1.0, vs, t_now=t0 + k / 30)
        assert ctx.fbo is vs[0].target and ctx.viewport == vs[0].rect
    assert ctx.error == "GL_NO_ERROR"
    return [px(ctx, v.target) if v.target is not None else None for v in vs]


def _interior(pic, ground) -> np.ndarray:
    """Where `pic` is not the ground in a pixel and its eight neighbours:
    the inside of what was drawn, no anti-aliased rim."""
    drawn = np.abs(pic - ground).sum(axis=2) > 0
    inner = drawn.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            inner &= np.roll(np.roll(drawn, dy, axis=0), dx, axis=1)
    return inner


def test_hands_in_the_scene_are_solid_and_in_front_of_or_behind_the_shape(ctx):
    """`Wiring(hands="scene")`: the hands are drawn into the scene first,
    solid (`ghost.alpha` not applied), the see-through shape after them,
    depth-tested. In front of the shape a hand hides it: inside the hand
    the frame is the hands-alone frame exactly. Behind it, the shape's
    strokes and fills are laid over the hand."""
    w = Wiring(hands="scene")
    ground = np.zeros((H, W, 4), int)
    ground[..., 3] = 255
    for z0, front in ((FRONT, True), (BEHIND, False)):
        alone = _draw(ctx, _rig(ctx, w, z0, shape=False, alpha=0.3), views(ctx, S()))[0]
        inner = _interior(alone, ground)
        assert inner.sum() > 200
        r = _rig(ctx, w, z0, alpha=0.3)
        got = _draw(ctx, r, views(ctx, S()))[0]
        assert r.stats["in_scene"] and not r.stats["layer"]
        same = np.all(got[inner] == alone[inner], axis=1)
        if front:
            assert same.all()
            front_alone, front_inner = alone, inner
        else:
            assert (~same).sum() > 0.3 * inner.sum()
    # solid: the hands alone in the scene are not at ghost.alpha 0.3 — the
    # palm is as bright as the layer's own opaque picture
    layer_alone = _draw(ctx, _rig(ctx, None, FRONT, shape=False, alpha=1.0),
                        views(ctx, S()))[0]
    assert abs(layer_alone[front_inner][..., :3].mean()
               - front_alone[front_inner][..., :3].mean()) < 6


def test_the_scene_holds_the_hands_so_the_effects_bend_them_and_the_history_keeps_them(ctx):
    """In the scene the hands are part of the picture: an effect bends
    them with the shape and the look-back's echoes hold them — what the
    default graph never does (its history is the bare scene)."""
    bare = _rig(ctx, hands=False, echoes=True)
    _draw(ctx, bare, views(ctx, S()), frames=6)
    want = np.frombuffer(bare.lookback.atlas.read(), dtype=np.uint8)
    r = _rig(ctx, Wiring(hands="scene"), echoes=True)
    _draw(ctx, r, views(ctx, S()), frames=6)
    assert not np.array_equal(np.frombuffer(r.lookback.atlas.read(), dtype=np.uint8), want)
    # through an effect: the scene's output with the hands in it is the
    # hands bent with the shape, never laid over after
    plain = _draw(ctx, _rig(ctx, Wiring(hands="scene")), views(ctx, S()))[0]
    bent = _draw(ctx, _rig(ctx, Wiring(hands="scene"), effects=("warp",)),
                 views(ctx, S()))[0]
    over = _draw(ctx, _rig(ctx, None, effects=("warp",)), views(ctx, S()))[0]
    assert not np.array_equal(plain, bent) and not np.array_equal(bent, over)


def test_a_glass_without_the_scene_still_gets_the_hands_layer(ctx):
    """The same hands in the scene on one output and a clean layer on
    another (decision 3): the glass (scene off) shows the hands' layer
    exactly as the default graph's glass does (plan 35 T4: the glass's
    state is its output's wiring — a mute on an in-scene preset shows its
    ground and the guide, check 347)."""
    ra, rb = _rig(ctx, Wiring(hands="scene")), _rig(ctx)
    a = _draw(ctx, ra, views(ctx, *wire_switches(ra, S(), S(scene=False))))
    b = _draw(ctx, rb, views(ctx, *wire_switches(rb, S(), S(scene=False))))
    assert np.array_equal(a[1], b[1]) and a[1][..., :3].max() > 100
    assert not np.array_equal(a[0], b[0])


def test_the_guide_never_rides_the_scene(ctx):
    """With the hands in the scene and the guide on, the guide and its
    labels are the readout, laid on at the output: the scene texture (and
    so the history and the effects) is the same with the guide on or off;
    the output differs by the readout alone."""
    pics, scenes = [], []
    for guide in (0, 1):
        r = _rig(ctx, Wiring(hands="scene"), guide=guide)
        pics.append(_draw(ctx, r, views(ctx, S()))[0])
        scenes.append(np.frombuffer(r.scene.tex.read(), dtype=np.uint8).copy())
        assert r.stats["readout"] is bool(guide)
        assert "hands.guide" in r._graph.nodes
    assert np.array_equal(scenes[0], scenes[1])
    assert not np.array_equal(pics[0], pics[1])


def test_a_raising_hand_in_the_scene_costs_the_scene_nothing(ctx, monkeypatch):
    want = _draw(ctx, _rig(ctx, Wiring(hands="scene"), hands=False), views(ctx, S()))[0]
    r = _rig(ctx, Wiring(hands="scene"))
    with monkeypatch.context() as m:
        def boom(self, *a, **k):
            raise RuntimeError("in the scene")
        m.setattr(G.Geometry, "draw", boom)
        got = _draw(ctx, r, views(ctx, S()))[0]
    assert np.array_equal(got, want)
    assert r.ghost.error == "ghost hands in the scene: RuntimeError: in the scene"


def test_a_depth_aware_layer_goes_behind_the_shape(ctx):
    """`Wiring(blend="depth")`: the hands' layer is laid on over, except
    where the shape's visible surface is nearer (`render.LAYER_DEPTH_BIAS`):
    in front of the shape it is plain over, byte for byte; behind it, the
    hidden texels show the picture under them exactly."""
    for z0, front in ((FRONT, True), (BEHIND, False)):
        over = _draw(ctx, _rig(ctx, None, z0), views(ctx, S()))[0]
        depth = _draw(ctx, _rig(ctx, Wiring(blend="depth"), z0), views(ctx, S()))[0]
        bare = _draw(ctx, _rig(ctx, None, z0, hands=False), views(ctx, S()))[0]
        if front:
            assert np.array_equal(depth, over)
            continue
        hidden = np.abs(depth - over).sum(axis=2) > 0
        assert hidden.sum() > 50
        assert np.array_equal(depth[hidden], bare[hidden])
    # through an effect too: the composite before the chain hides it
    ra = _rig(ctx, None, BEHIND, effects=("warp",))
    a = _draw(ctx, ra, views(ctx, *wire_switches(ra, Thru())))[0]
    rb = _rig(ctx, Wiring(blend="depth"), BEHIND, effects=("warp",))
    b = _draw(ctx, rb, views(ctx, *wire_switches(rb, Thru())))[0]
    assert not np.array_equal(a, b)


def test_the_scenes_depth_resolves_out_of_the_multisampled_target(ctx):
    """The scene drawn multisampled (output 1 is 4× MSAA in the app):
    `SceneTarget.depth_texture` resolves the depth for a node that reads
    it — the shape's visible surface nearer than the far plane, the
    ground at it — and the frame is the same with or without the ask."""
    r = _rig(ctx, Wiring(blend="depth"), BEHIND)
    v = O.View(S(), (W, H), target=fbo(ctx, samples=4))
    _draw(ctx, r, [v], frames=2)
    d = np.frombuffer(r.scene.depth_texture().read(), dtype="f4")
    assert r.scene._msaa is not None and d.max() == 1.0 and d.min() < 0.999


def test_the_presenter_carries_the_hands_the_readout_and_the_dim_in_every_wiring(ctx):
    """A second output in another context (`Presenter`) under each wiring:
    its picture is the target view's, byte for byte — the scene with the
    hands in it, the glass's layer, the hands added (`blend` "add" rides the
    hand-off), the readout and the dim. A
    depth-aware over is the target's alone (the depth stays in this
    context): the presenter lays the layer plain over."""
    from test_outputs import _presented

    for wiring in (Wiring(hands="scene"), Wiring(history="scene+hands"), Wiring(blend="add")):
        r = _rig(ctx, wiring, alpha=0.7, dim=0.8, guide=1)
        pairs = [(S(dim=0.5), (W, H)), (S(scene=False), (W, H)),
                 (Thru(scene=False), (640, 300))]
        got = _presented(ctx, r, pairs)
        for (sw, size), (want, shown) in zip(pairs, got, strict=True):
            assert np.array_equal(want, shown), (wiring, sw, size)
        assert any(p[0][..., :3].max() > 100 for p in got)
    # the hand-off itself: hands over on the glass, the readout everywhere
    r = _rig(ctx, Wiring(hands="scene"), guide=1, dim=0.5)
    sws = wire_switches(r, S(), S(), S(scene=False))     # (plan 35 T4: the glass's wiring)
    pv1 = O.View(sws[1], (W, H), presenter=object())
    pv2 = O.View(sws[2], (W, H), presenter=object())
    _draw(ctx, r, [views(ctx, sws[0])[0], pv1, pv2], frames=2)
    assert pv1.handoff.hands is None and pv1.handoff.readout is r.ghost.readout
    assert pv2.handoff.hands is r.ghost.tex and pv2.handoff.readout is r.ghost.readout
    assert pv1.handoff.factor == pytest.approx(0.5) and pv1.handoff.frame is not None
    assert pv1.handoff.blend == pv2.handoff.blend == "over"
    # add rides the hand-off; depth-aware goes plain over there
    for blend, want in (("add", "add"), ("depth", "over")):
        r = _rig(ctx, Wiring(blend=blend))
        pv = O.View(S(), (W, H), presenter=object())
        _draw(ctx, r, [views(ctx, S())[0], pv], frames=2)
        assert pv.handoff.hands is r.ghost.tex and pv.handoff.blend == want


def test_a_second_hands_node_on_a_presenter_glass_matches_the_target(ctx):
    """A graph with a second hands node (``ghost.2``, its own state) laid
    on the glass: a presenter output shows what a target view shows, byte
    for byte, in each output's switches, and the glass is lit (review
    pass, Minor 4)."""
    from test_outputs import _presented

    r = rig(ctx, effects=(), guide=1, dim=0.8)
    r.ghost_states = {"ghost.2": G.GhostState(on=True, alpha=0.25, guide=1)}
    r.wiring = wired_wiring(Wiring(hands="scene", extra=(HandsAt(2),)))
    pairs = [(S(dim=0.5), (640, 400)), (S(scene=False), (640, 400)),
             (Thru(scene=False), (640, 300))]
    got = _presented(ctx, r, pairs)
    assert r.ghost_of("ghost.2") is not r.ghost
    for (sw, size), (want, shown) in zip(pairs, got, strict=True):
        assert np.array_equal(want, shown), (sw, size)
    assert any(p[1][..., :3].max() > 50 for p in got[1:])     # the glass is lit


def test_the_mirror_and_an_output_flip_each_flip_the_hands_once(ctx):
    """`ghost.mirror` mirrors the hands in the Leap basis (about the box's
    centre, the middle of the picture); an output's flip mirrors the
    whole picture. In the scene both apply once each: mirror and flip
    together put the hands back where neither does."""
    ground = np.zeros((H, W, 4), int)
    ground[..., 3] = 255
    w = Wiring(hands="scene")

    def mask(mirror=False, flip=False):
        r = _rig(ctx, w, shape=False)
        r.ghost.state.mirror = mirror
        got = _draw(ctx, r, views(ctx, S(flip_x=flip)))[0]
        return np.abs(got - ground).sum(axis=2) > 0

    plain = mask()

    def iou(a, b):
        return (a & b).sum() / (a | b).sum()

    assert iou(mask(mirror=True), plain[:, ::-1]) > 0.9
    assert iou(mask(flip=True), plain[:, ::-1]) > 0.98
    assert iou(mask(mirror=True, flip=True), plain) > 0.9
    assert iou(mask(mirror=True), plain) < 0.5


def test_the_hands_have_their_own_line_when_the_scene_draws_them(ctx):
    """Per-node GPU timing: inside the scene the hands' draw is its own
    line (`hands`, plan 35 T4's name), beside the scene's; as a layer it
    is the layer's (`hands.layer`), as before."""
    from hyperspace.render import PassTimer

    r = _rig(ctx, Wiring(hands="scene"))
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    vs = views(ctx, *wire_switches(r, S(), S(scene=False)))
    _draw(ctx, r, vs, frames=PassTimer.LAG + 3)
    ms = r.stats["gpu_ms"]
    assert list(ms) == r._graph.timed
    assert list(ms)[:2] == ["hands", "scene"] and "hands.layer" in ms
    r.wiring = wired_wiring(Wiring())
    _draw(ctx, r, vs, frames=PassTimer.LAG + 2)
    assert "hands" not in r.stats["gpu_ms"] and "hands.layer" in r.stats["gpu_ms"]
