"""The ghost hands (ghost.py): a synthetic open hand and fist, no camera.

The pass is the last thing a frame draws: on, the hands show over the
scene with FX on and come out the same whatever the effects; off — or on
with no tracker or no hand — the frame is the old frame bit for bit; the
target's alpha is never touched on an opaque ground; the look-back
history never holds them; a hand that leaves fades rather than freezing
or snapping.
"""

from __future__ import annotations

from itertools import pairwise
from types import SimpleNamespace as NS

import moderngl
import numpy as np
import pytest
from fake_hands import hand

from hyperspace import ghost as G
from hyperspace.fx import FxState
from hyperspace.hands import HandSettings, HandsIO, skeleton
from hyperspace.params import SESSION_GROUPS, part_of
from hyperspace.render import Renderer
from hyperspace.view import ViewState

W, H = 480, 320
VIEW = {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25}


def both(left="open", right="fist") -> dict:
    return {"left": skeleton(hand("left", left, (-90.0, 210.0, 0.0))),
            "right": skeleton(hand("right", right, (90.0, 200.0, 10.0)))}


def tracker(skel=None, mode="desktop") -> NS:
    """What the Ghost reads of a HandsIO: the skeletons present, the mode."""
    return NS(skeleton=both() if skel is None else skel, cfg={"mode": mode})


# ---------------------------------------------------------------- no GL

def test_the_params_are_session_off_by_default_and_learnable(tmp_path):
    from test_params import make

    reg = make(tmp_path)[0]
    assert "ghost" in SESSION_GROUPS
    for pid in ("ghost.on", "ghost.alpha", "ghost.mirror", "ghost.guide", "ghost.tethers"):
        p = reg[pid]
        assert p.persist and p.modulatable and part_of(p) == "session", pid
    assert reg["ghost.on"].value is False and 0.0 < reg["ghost.alpha"].value <= 1.0
    assert G.GUIDES[reg["ghost.guide"].value] == "OFF" and reg["ghost.tethers"].value is False


def test_the_box_is_the_calibrated_ranges_else_the_defaults():
    assert G.box_of(None) == ((-220.0, 220.0), (100.0, 350.0), (-100.0, 100.0))
    io = HandsIO(HandSettings.from_config({"dofs": ["x", "y", "roll"]}), {},
                 source=NS(latest=lambda: (0, 0.0, {})), out=NS(send=print))
    st = {a.name: s for a, s in zip(io.axes, io.state)}
    st["left.x"].lo, st["left.x"].hi = -180.0, 10.0
    st["right.x"].lo, st["right.x"].hi = -5.0, 160.0
    st["right.y"].lo, st["right.y"].hi = 120.0, 300.0
    (x, y, z) = G.box_of(io)
    assert x == (-180.0, 160.0)
    assert y == (min(120.0, st["left.y"].lo), max(300.0, st["left.y"].hi))
    assert z == (-100.0, 100.0)                      # no z axis in this setup: the default


def test_a_hand_the_setup_has_no_axis_for_is_still_in_frame():
    """Only right.x in the setup: the left hand's side of the box is its
    default range, not dropped."""
    io = HandsIO(HandSettings.from_config({"dofs": ["x"]}), {},
                 source=NS(latest=lambda: (0, 0.0, {})), out=NS(send=print))
    io.settings.axes[:] = [a for a in io.axes if a.side == "right"]
    io.state[:] = io.state[1:]
    io.state[0].lo, io.state[0].hi = 10.0, 150.0
    x = G.box_of(io)[0]
    assert x[0] <= -200.0 and x[1] == 150.0


@pytest.mark.parametrize("mode", sorted(G.MODES))
@pytest.mark.parametrize("aspect", [16 / 9, 4 / 3, 0.6])
def test_the_camera_fits_the_padded_box_in_frame(mode, aspect):
    m = G.basis(mode)
    box = ((-150.0, 140.0), (110.0, 330.0), (-90.0, 80.0))
    vp, _ = G.camera(box, m, aspect)
    st = np.array([(x, y, z) for x in box[0] for y in box[1] for z in box[2]]) @ m.T
    lo, hi = st.min(0) - G.PAD, st.max(0) + G.PAD
    corners = np.array([(x, y, z, 1.0) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])])
    clip = corners @ vp.T
    ndc = clip[:, :3] / clip[:, 3:]
    assert (clip[:, 3] > 0).all() and (np.abs(ndc) <= 1.0 + 1e-6).all()
    # and it fills: some corner touches the frame's edge
    assert np.abs(ndc[:, :2]).max() > 0.99


def test_desktop_keeps_left_on_the_left_and_mirror_flips_it():
    vp, _ = G.camera(G.box_of(None), G.basis("desktop"), 1.5)

    def screen_x(p, m):
        c = np.append(m @ np.asarray(p), 1.0) @ vp.T
        return c[0] / c[3]

    left, right = (-100.0, 200.0, 0.0), (100.0, 200.0, 0.0)
    assert screen_x(left, G.basis("desktop")) < 0 < screen_x(right, G.basis("desktop"))
    assert screen_x(left, G.basis("desktop", mirror=True)) > 0
    assert (G.basis("sideways") == G.basis("desktop")).all()


def test_a_hand_that_leaves_fades_out_where_it_was_and_comes_back_up():
    gh = G.Ghost(ctx=None, state=G.GhostState(on=True))
    src = tracker()
    gh.source = src
    seen = gh.step(0.0)
    assert {s for s, _, _ in seen} == {"left", "right"}
    for k in range(1, 20):
        gh.step(k / 60)
    assert gh.sides["left"].fade == 1.0
    last = src.skeleton["left"]
    src.skeleton = {"right": src.skeleton["right"]}       # the left hand leaves
    fades = []
    t = 20 / 60
    while gh.sides["left"].fade > 0.0:
        seen = {s: (sk, f) for s, sk, f in gh.step(t)}
        if "left" in seen:
            assert seen["left"][0] is last                # held where it was, not frozen live
        fades.append(gh.sides["left"].fade)
        t += 1 / 60
    assert len(fades) >= int(G.FADE_OUT * 60) - 1        # over FADE_OUT, not one frame
    assert all(a > b for a, b in pairwise(fades))
    assert "left" not in {s for s, _, _ in gh.step(t)}
    src.skeleton = both()
    gh.step(t + 1 / 60)
    assert 0.0 < gh.sides["left"].fade < 1.0              # back, fading up


def test_off_or_no_tracker_shows_nothing_and_forgets():
    gh = G.Ghost(ctx=None, state=G.GhostState(on=False))
    gh.source = tracker()
    assert gh.poses(0.0, 1.5) is None
    gh.state.on = True
    gh.source = None
    assert gh.poses(0.0, 1.5) is None
    gh.source = tracker({})
    assert gh.poses(0.0, 1.5) is None
    gh.source = tracker()
    poses, _, _ = gh.poses(0.1, 1.5)
    assert [p.side for p in poses] == ["left", "right"]
    assert poses[0].joints.shape == (5, 5, 3)
    gh.state.on = False
    gh.poses(0.2, 1.5)
    assert all(sd.fade == 0.0 and sd.skel is None for sd in gh.sides.values())


def test_a_pose_carries_the_skeleton_through_the_basis():
    sk = skeleton(hand("right", "open", (50.0, 220.0, -20.0)))
    p = G.pose("right", sk, G.basis("screentop"))
    assert np.allclose(p.palm, (-50.0, -220.0, -20.0))
    assert p.joints.shape == (5, 5, 3) and p.rots.shape == (5, 4, 4)
    assert np.allclose(p.joints[1, 4], G.basis("screentop") @ sk["digits"][1][3]["next"])
    spheres, tubes, tris = G.CapsuleHands.parts(p)
    assert len(tubes) == 19 and len(spheres) == 24 and len(tris) == 10     # no zero-length thumb bone
    palm_only = G.pose("left", {"palm": (0, 200, 0), "normal": (0, -1, 0),
                                "direction": (0, 0, -1), "width": 80.0, "digits": []},
                       G.basis("desktop"))
    spheres, tubes, tris = G.CapsuleHands.parts(palm_only)
    assert not spheres and not tubes and len(tris) == 16


# ---------------------------------------------------------------- the guide

RANGES = {"x": (-20.0, 220.0), "y": (100.0, 350.0), "z": (-100.0, 100.0),
          "roll": (-90.0, 90.0), "pitch": (-60.0, 60.0), "yaw": (-45.0, 45.0)}


def values(**ys) -> dict:
    """Every axis at ½ (a centred hand) unless given."""
    return {f: (ys.get(f, 0.5), *RANGES[f]) for f in RANGES}


def balls(side, vals, pinches=(False,) * 4, m=None):
    """{rgb: [positions]} of the guide's big balls (the values)."""
    sph, _ = G.guide(side, vals, list(pinches), np.zeros(3), 100.0,
                     G.basis("desktop") if m is None else m, 1.0)
    out = {}
    for row in sph:
        if row[3] >= 0.8 * G.GUIDE_BALL_R - 1e-6:
            out.setdefault(tuple(round(v, 3) for v in row[4:7]), []).append(np.array(row[:3]))
    return out


def test_one_axis_moved_moves_its_ball_only():
    """The point of the guide: a hand moved only right moves only the x
    ball, so the performer sees which motion is isolated."""
    rest = balls("right", values())
    for f, axis in (("x", 0), ("y", 1), ("z", 2)):
        moved = balls("right", values(**{f: 0.9}))
        changed = [rgb for rgb in rest if not all(
            np.allclose(a, b) for a, b in zip(rest[rgb], moved[rgb]))]
        assert changed == [tuple(round(v, 3) for v in G.AXIS_RGB[f])], (f, changed)
        ball = next(p for p in moved[changed[0]] if abs(p[axis]) > 1.0)
        assert ball[axis] == pytest.approx(80.0)        # 0.9 → +0.8 of the half-axis


def test_the_rings_put_the_dot_where_the_hand_points():
    """Pitch up: the dot rises. Yaw outward: it goes out — right on the
    right, left on the left. Roll thumb-up: the palm turns inward."""
    def dot(side, name, y):
        rgb = tuple(round(v, 3) for v in G.AXIS_RGB[G.RING_OF[name]])
        rest = {f: (0.5, *RANGES[f]) for f in (name,)}
        rest[name] = (y, *RANGES[name])
        got = balls(side, rest)[rgb]
        return got[0]
    assert dot("right", "pitch", 0.5)[2] < 0                     # neutral: fingers forward
    assert dot("right", "pitch", 1.0)[1] > 0                     # fingers up
    assert dot("right", "yaw", 1.0)[0] > 0 and dot("left", "yaw", 1.0)[0] < 0
    assert dot("right", "roll", 0.5)[1] < 0                      # neutral: palm down
    assert dot("right", "roll", 1.0)[0] < 0 and dot("left", "roll", 1.0)[0] > 0
    # mirrored, the yaw dot goes out on screen the way the mirrored hand does
    assert balls("right", {"yaw": (1.0, -45.0, 45.0)},
                 m=G.basis("desktop", mirror=True))[(0.3, 0.88, 0.36)][0][0] < 0


def _routed_rig(tmp_path, rows):
    """A real registry, routing table and HandsIO with `rows` (source
    addresses) as performer rows, the hand lanes published."""
    from test_params import make

    from hyperspace.routing import Binding, Bindings, Router

    reg = make(tmp_path)[0]
    router = Router(reg, Bindings([Binding(src, "view.bright", "position") for src in rows]))
    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    io.poll(1 / 60, router=router)                  # publishes hand:<name> → lane
    return router, io


def test_the_guide_lights_what_the_table_routes(tmp_path):
    """The owner's case: rows on the left hand, none on the right — the
    left gauge lit, the right one dark, by name or by lane index."""
    router, io = _routed_rig(tmp_path, ["hand:left.x", "hand:left.roll",
                                        f"hand:{io_index('left.pitch')}"])
    assert G.routed_names(router, io) == {"left.x", "left.roll", "left.pitch"}
    for st in io.state:
        st.follow.y = 0.5
    left, right = (G.guide_values(io, s, G.routed_names(router, io)) for s in ("left", "right"))
    assert {f for f, v in left.items() if v[3]} == {"x", "roll", "pitch"}
    assert not any(v[3] for v in right.values()) and set(right) == set(left)
    b = router.table.bindings[0]
    b.enabled = False                               # a disabled row drives nothing
    assert "left.x" not in G.routed_names(router, io)
    assert G.routed_names(None, io) is None         # no table: everything lit
    assert all(v[3] for v in G.guide_values(io, "right", None).values())


def io_index(name: str) -> int:
    return HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                   out=NS(send=print)).layout.index[name]


def test_routed_axes_keep_their_colour_and_the_rest_go_grey_and_small():
    vals = {"x": (0.7, -20.0, 220.0, True), "y": (0.5, 100.0, 350.0, False),
            "roll": (0.5, -90.0, 90.0, False), "pitch": (0.5, -60.0, 60.0, True)}
    sph, tubes = G.guide("right", vals, [False] * 4, np.zeros(3), 100.0,
                         G.basis("desktop"), 1.0)
    x_ball = next(r for r in sph if r[0] > 1.0 and r[3] == G.GUIDE_BALL_R)
    assert np.allclose(x_ball[4:7], G.AXIS_RGB["x"])                     # routed: colour
    y_ball = next(r for r in sph if abs(r[1]) < 1e-9 and abs(r[0]) < 1e-9
                  and r[3] == G.GUIDE_BALL_R * G.UNROUTED_SIZE)
    assert np.allclose(y_ball[4:7], G.UNROUTED_RGB)                      # not: grey, smaller
    x_line = next(t for t in tubes if abs(t[0]) > 1.0 and abs(t[3]) > 1.0)
    y_line = next(t for t in tubes if abs(t[1]) > 1.0 and abs(t[4]) > 1.0)
    assert x_line[6] > y_line[6]                                         # and thinner
    grey = [t for t in tubes if np.allclose(t[7:10], [v * 0.55 for v in G.UNROUTED_RGB])]
    red = [t for t in tubes if np.allclose(t[7:10], [v * 0.55 for v in G.AXIS_RGB["x"]])]
    assert grey and red            # the roll arc grey, the pitch arc in its own (x) red


def test_the_arcs_span_the_reach_and_no_more():
    """Roll ±90°: the arc is the lower half only (a palm cannot face up
    past thumb-up); pitch ±60°: never behind the hand. Calibrated ranges
    narrow the arc further."""
    def arc(name, lo, hi):
        _, tubes = G.guide("right", {name: (0.5, lo, hi, True)}, [False] * 4,
                           np.zeros(3), 100.0, G.basis("desktop"), 1.0)
        rgb = [v * 0.55 for v in G.AXIS_RGB[G.RING_OF[name]]]
        return np.array([p for t in tubes if np.allclose(t[7:10], rgb)
                         for p in (t[:3], t[3:6])])
    r = 0.78 * 100.0
    roll = arc("roll", -90.0, 90.0)
    assert roll[:, 1].max() <= 1e-6 and roll[:, 1].min() == pytest.approx(-r)
    pitch = arc("pitch", -60.0, 60.0)
    assert pitch[:, 2].max() < 0                                     # all in front
    assert pitch[:, 1].max() == pytest.approx(r * np.sin(np.radians(60)), abs=1e-6)
    narrow = arc("yaw", -20.0, 30.0)
    span = np.degrees(np.arctan2(narrow[:, 0], -narrow[:, 2]))
    assert span.min() == pytest.approx(-20.0, abs=1e-6) and span.max() < 30.0 + 1e-6


def test_the_guide_takes_every_feature_from_the_frame_and_the_pinches():
    """No axis for a feature: its native reading over the default range."""
    io = HandsIO(HandSettings.from_config({"dofs": ["x", "pitch"]}), {},
                 source=NS(latest=lambda: (0, 0.0, {})), out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.7
    io.frame["right"] = {"x": 0.0, "y": 225.0, "z": 0.0, "roll": 45.0, "pitch": 0.0,
                         "yaw": -45.0, "grab": 0.25}
    vals = G.guide_values(io, "right")
    assert set(vals) == set(G.GUIDE_FEATURES)
    assert vals["x"][:3] == (0.7, -20.0, 220.0)              # the setup's axis: shaped
    assert vals["y"][:3] == (0.5, 100.0, 350.0)              # native over the default range
    assert vals["roll"][0] == 0.75 and vals["yaw"][0] == 0.0 and vals["grab"][0] == 0.25
    io.gates["right"]["middle"].on = True
    assert G.guide_pinches(io, "right") == [False, True, False, False]
    sph, _ = G.guide("right", {}, [False, True, False, False], np.zeros(3), 100.0,
                     G.basis("desktop"), 1.0)
    assert len([r for r in sph if tuple(r[4:7]) == G.PINCH_RGB]) == 1


def test_the_grab_ring_closes_with_the_hand():
    def ring(g):
        _, tubes = G.guide("right", {"grab": (g, 0.0, 1.0, True)}, [False] * 4,
                           np.zeros(3), 100.0, G.basis("desktop"), 1.0)
        pts = np.array([t[:3] for t in tubes if np.allclose(t[7:10],
                                                            [v * 0.8 for v in G.GRAB_RGB])])
        return np.ptp(pts[:, 0])
    assert ring(0.0) > 2.5 * ring(1.0) > 0


# ---------------------------------------------------------------- tethers

def test_a_tether_names_what_its_mark_drives_from_a_fixed_anchor(tmp_path):
    router, io = _routed_rig(tmp_path, ["hand:left.x", "hand:left.y", "hand:left.pinch.index"])
    router.table.bindings.append(type(router.table.bindings[0])(
        "hand:left.y", "view.speed", "push"))
    rows = G.routed_rows(router, io)
    assert rows == {"left.x": ["Brightness"], "left.y": ["Brightness", "Speed"],
                    "left.pinch.index": ["Brightness"]}
    vals = values()
    anchors_a, anchors_b = {}, {}
    G.guide("left", vals, [False] * 4, np.zeros(3), 100.0, G.basis("desktop"), 1.0, anchors_a)
    G.guide("left", values(x=0.95, roll=0.9), [True] * 4, np.zeros(3), 100.0,
            G.basis("desktop"), 1.0, anchors_b)
    assert all(np.allclose(anchors_a[k], anchors_b[k]) for k in anchors_a)   # never the ball
    teth = G.tethers("left", rows, anchors_a)
    assert [t[2] for t in teth] == ["Brightness", "Brightness · Speed", "Brightness"]
    assert np.allclose(teth[0][0], (-100.0, 0.0, 0.0))     # the left hand's x line's outer end
    assert teth[0][1] == G.AXIS_RGB["x"] and teth[2][1] == G.PINCH_RGB
    assert G.tethers("right", rows, anchors_a) == []       # nothing routed on the right
    long = G.tethers("left", {"left.x": ["A very long parameter label indeed", "and more"]},
                     anchors_a)
    assert len(long[0][2]) == G.TETHER_LABEL_MAX and long[0][2].endswith("…")


def test_the_labels_stack_at_the_hands_edge_in_frame_without_crossing():
    vp, _ = G.camera(G.box_of(None), G.basis("desktop"), 1.5)
    items = [(np.array([-150.0, 150.0 + 40 * k, 0.0]), (1, 1, 1), f"p{k}") for k in range(5)]
    out = G.layout_tethers(items, vp, (960, 640), lambda text, h: 3.0 * h)
    assert len(out) == 5
    xs = {round(box[0]) for _, box, _, _, _ in out}
    assert xs == {round(G.TETHER_MARGIN * 640)}            # the left edge: a left-side hand
    ys = [box[1] for _, box, _, _, _ in out]
    assert ys == sorted(ys) and ys[0] >= 0 and ys[-1] + out[-1][1][3] <= 640
    anchors_y = [a[1] for a, _, _, _, _ in out]
    assert anchors_y == sorted(anchors_y)                   # sorted the same way: no crossing
    assert [t for *_, t in out] == ["p4", "p3", "p2", "p1", "p0"]   # highest hand mark on top
    right = [(np.array([150.0, 200.0, 0.0]), (1, 1, 1), "q")]
    (_, box, end, _, _), = G.layout_tethers(right, vp, (960, 640), lambda text, h: 3.0 * h)
    assert box[0] + box[2] == pytest.approx(960 - G.TETHER_MARGIN * 640) and end[0] < box[0]


# ---------------------------------------------------------------- GL

@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def frame(ctx, *, src=None, on=True, alpha=1.0, fx: FxState | None = None, frames=4,
          renderer: Renderer | None = None, t0: float = 2.0):
    """(RGBA frame, renderer) after `frames` frames at 30 fps."""
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
    r = renderer or Renderer(ctx, fx=fx)
    r.ghost.state.on, r.ghost.state.alpha = on, alpha
    r.ghost.source = src
    s = ViewState(ang=list(VIEW["ang"]), yaw=VIEW["yaw"], pitch=VIEW["pitch"])
    for k in range(frames):
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=t0 + k / 30)
        assert ctx.fbo is fbo                       # the frame ends on its target
    out = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4)[::-1].copy()
    fbo.release()
    return out, r


def hand_mask(ctx, src, solid: bool = False) -> np.ndarray:
    """Where the hands cover the frame: the ghost alone over black.
    `solid`: only where they cover it fully (the hands' own alpha 1)."""
    r = Renderer(ctx)
    gh = r.ghost
    gh.state.on, gh.state.alpha, gh.source = True, 1.0, src
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    for k in range(4):
        gh.draw(fbo, (0, 0, W, H), k / 30)
    rgb = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1]
    fbo.release()
    if solid:
        a = np.frombuffer(gh._tex.read(), dtype=np.uint8).reshape(H, W, 4)[::-1, :, 3]
        return a == 255
    return rgb.max(axis=2) > 0


def test_on_draws_both_hands_and_off_is_the_old_frame_exactly(ctx):
    base, _ = frame(ctx)                               # no tracker at all: today's frame
    off, _ = frame(ctx, src=tracker(), on=False)
    assert np.array_equal(off, base)
    empty, _ = frame(ctx, src=tracker({}), on=True)    # on, but no hand in the box
    assert np.array_equal(empty, base)
    on, _ = frame(ctx, src=tracker(), on=True)
    changed = np.abs(on[..., :3].astype(int) - base[..., :3]).sum(axis=2) > 30
    left, right = changed[:, : W // 2].sum(), changed[:, W // 2:].sum()
    assert left > 400 and right > 400, (left, right)   # one hand on each side
    # both near-white: the left a little cool, the right a little warm
    l_px = on[:, : W // 2][changed[:, : W // 2]].astype(int)
    r_px = on[:, W // 2:][changed[:, W // 2:]].astype(int)
    assert l_px[:, 2].mean() > l_px[:, 0].mean() and r_px[:, 0].mean() > r_px[:, 2].mean()
    assert r_px[:, 1].mean() > 0.7 * r_px[:, 0].mean()        # not red: a white


def test_a_shader_the_driver_refuses_leaves_the_frame_and_says_why(ctx, monkeypatch):
    base, _ = frame(ctx)
    monkeypatch.setattr(G, "COMPOSITE_FS", "#version 330\nvoid main() { nope; }")
    out, r = frame(ctx, src=tracker())
    assert np.array_equal(out, base)                   # no hands, no half-built pass
    assert r.ghost.error.startswith("ghost:") and r.ghost.geometry is None
    monkeypatch.undo()
    r.ghost.on_reload()                                # a fixed edit builds again
    out, _ = frame(ctx, src=tracker(), renderer=r, t0=5.0)
    assert not np.array_equal(out, base) and r.ghost.error == ""


def test_the_target_alpha_is_untouched(ctx):
    base, _ = frame(ctx)
    for alpha in (1.0, 0.4):
        on, _ = frame(ctx, src=tracker(), alpha=alpha)
        assert np.array_equal(on[..., 3], base[..., 3])
        assert on[..., 3].min() == 255


def test_the_guide_draws_beside_and_on_the_hand_and_keeps_the_alpha(ctx):
    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.7
    src = NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
             gates=io.gates)
    plain, _ = frame(ctx, src=src)
    for g in (1, 2):
        r = Renderer(ctx)
        r.ghost.state.guide = g
        out, _ = frame(ctx, src=src, renderer=r)
        diff = np.abs(out[..., :3].astype(int) - plain[..., :3]).sum(axis=2) > 30
        assert diff.sum() > 300, G.GUIDES[g]
        assert out[..., 3].min() == 255


def test_tethers_draw_only_when_toggled_and_keep_the_alpha(ctx, tmp_path):
    router, io = _routed_rig(tmp_path, ["hand:left.x", "hand:left.roll", "hand:right.y"])
    for st in io.state:
        st.follow.y = 0.6
    src = NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
             gates=io.gates, layout=io.layout, frame=io.frame)

    def shot(tethers):
        r = Renderer(ctx)
        r.ghost.router = router
        r.ghost.state.guide, r.ghost.state.tethers = 1, tethers
        return frame(ctx, src=src, renderer=r)

    gimbals, _ = shot(False)
    tethered, r = shot(True)
    diff = np.abs(tethered[..., :3].astype(int) - gimbals[..., :3]).sum(axis=2) > 30
    assert diff[:, : W // 4].sum() > 50 and diff[:, 3 * W // 4:].sum() > 20   # both edges
    assert tethered[..., 3].min() == 255 and r.ghost.error == ""
    r2 = Renderer(ctx)
    r2.ghost.router = router
    r2.ghost.state.guide, r2.ghost.state.tethers = 0, True     # no guide: no tethers
    plain, _ = frame(ctx, src=src)
    no_guide, _ = frame(ctx, src=src, renderer=r2)
    assert np.array_equal(no_guide, plain)


def _tethered(ctx, tmp_path):
    """A renderer drawing the guide beside each hand with tethers on, its
    ghost.* params in a registry of its own, and the source it reads."""
    from hyperspace.params import Registry

    router, io = _routed_rig(tmp_path, ["hand:left.x", "hand:left.roll", "hand:right.y"])
    for st in io.state:
        st.follow.y = 0.6
    src = NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
             gates=io.gates, layout=io.layout, frame=io.frame)
    r = Renderer(ctx)
    reg = Registry()
    G.register(reg, r.ghost.state)
    r.ghost.router = router
    reg["ghost.guide"].set(1)
    reg["ghost.tethers"].set(True)
    return r, reg, src


@pytest.mark.parametrize("where", ["build", "label"])
def test_a_failed_label_build_writes_no_param(ctx, tmp_path, monkeypatch, where):
    """Plan 21 WP5 R2: the tethers' labels failing — their program will not
    build, or a label will not rasterise (a font) — leaves `ghost.tethers`
    as the performer set it (the render stack only reads), says why once
    on `Ghost.error`, still draws the hands and the guide, and is not
    tried again every frame. Off and on again tries afresh."""
    gimbals_r, _, src = _tethered(ctx, tmp_path)
    gimbals_r.ghost.state.tethers = False
    gimbals, _ = frame(ctx, src=src, renderer=gimbals_r)
    r, reg, src = _tethered(ctx, tmp_path)
    tries = []
    with monkeypatch.context() as m:
        if where == "build":
            def refuse(self, ctx):
                tries.append(1)
                raise RuntimeError("no program")
            m.setattr(G.TetherLabels, "__init__", refuse)
        else:
            def no_font(self, text, px):
                tries.append(1)
                raise OSError("no font")
            m.setattr(G.TetherLabels, "_label", no_font)
        out, _ = frame(ctx, src=src, renderer=r)          # four frames, none raises
    assert reg["ghost.tethers"].value is True and r.ghost.state.tethers is True
    assert len(tries) == 1                                # once, not every frame
    assert r.ghost.error.startswith("ghost tethers: ")
    assert np.array_equal(out, gimbals)                   # the hands and the guide, no tethers
    assert out[..., 3].min() == 255
    # switched off and on: tried again, and now the labels draw
    r.ghost.state.on = False
    frame(ctx, src=src, renderer=r, on=False, frames=1)
    assert r.ghost.error == ""
    again, _ = frame(ctx, src=src, renderer=r, t0=4.0)
    gimbals_later, _ = frame(ctx, src=src, renderer=gimbals_r, t0=4.0)
    assert r.ghost.error == ""
    assert (np.abs(again[..., :3].astype(int) - gimbals_later[..., :3]).sum(axis=2) > 30).sum() > 50


def test_an_open_hand_and_a_fist_differ(ctx):
    open_ = hand_mask(ctx, tracker(both(right="open")))
    fist = hand_mask(ctx, tracker(both(right="fist")))
    right = (slice(None), slice(W // 2, None))
    assert open_[right].sum() > fist[right].sum() * 1.2   # the fingers stretched out
    assert np.array_equal(open_[:, : W // 2], fist[:, : W // 2])   # the left one did not move


def test_the_effects_never_touch_the_hands(ctx):
    """With every pixel of the hands solid (alpha 1), the hands come out
    the same with the FX chain on as off — while the rest of the frame
    changes — and the look-back history (the scene texture) never sees them."""
    src = tracker()
    mask = hand_mask(ctx, src)
    inner = hand_mask(ctx, src, solid=True)          # not the antialiased rim
    assert inner.sum() > 500
    plain, r0 = frame(ctx, src=src)
    fx = FxState()
    fx.values["warp"]["on"] = True
    effected, r1 = frame(ctx, src=src, fx=fx)
    assert r1.fx.active()
    outside = ~mask
    assert np.abs(effected[outside].astype(int) - plain[outside]).sum() > 1000   # FX ran
    assert np.array_equal(effected[inner], plain[inner])                          # not on the hands
    # the scene texture — what the history captures — holds no hand
    _, r2 = frame(ctx, src=src, on=False)
    for r in (r0, r2):
        r.scene.tex.use()
    scene_on = np.frombuffer(r0.scene.tex.read(), dtype=np.uint8)
    scene_off = np.frombuffer(r2.scene.tex.read(), dtype=np.uint8)
    assert np.array_equal(scene_on, scene_off)


def test_a_see_through_ground_gains_the_hands_coverage(ctx):
    """Overlay mode: the hands must show on the desktop, so there the
    composite adds their coverage to the ground's alpha."""
    r = Renderer(ctx)
    r.bg_alpha = 0.0
    out, _ = frame(ctx, src=tracker(), renderer=r)
    mask = hand_mask(ctx, tracker())
    assert out[..., 3][mask].max() == 255


def test_a_hand_that_leaves_fades_out_on_screen(ctx):
    src = tracker()
    r = Renderer(ctx)
    full, _ = frame(ctx, src=src, renderer=r)
    src.skeleton = {"right": src.skeleton["right"]}
    fading, _ = frame(ctx, src=src, renderer=r, frames=2, t0=3.0)
    left = (slice(None), slice(None, W // 2))
    gone, _ = frame(ctx, src=src, renderer=r, frames=12, t0=4.0)
    none, _ = frame(ctx, src=tracker({"right": src.skeleton["right"]}))
    lit = lambda a: a[left][..., :3].astype(int).sum()
    assert lit(full) > lit(fading) > lit(gone)
    assert np.array_equal(gone[left], none[left])
