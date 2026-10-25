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
from hyperspace.hands import HandSettings, HandsIO, features, skeleton
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
    for pid in ("ghost.on", "ghost.alpha", "ghost.mirror", "ghost.guide", "ghost.tethers",
                "ghost.style"):
        p = reg[pid]
        assert p.persist and part_of(p) == "session", pid
        # plan 21 R12 / WP6: only the switch and the opacity may follow a
        # hand or an LFO; the rest are settings (still learnable on the desk)
        assert p.modulatable is (pid in ("ghost.on", "ghost.alpha")), pid
    assert reg["ghost.on"].value is False and 0.0 < reg["ghost.alpha"].value <= 1.0
    assert G.GUIDES[reg["ghost.guide"].value] == "OFF" and reg["ghost.tethers"].value is False
    assert reg["ghost.style"].names == G.STYLES and G.STYLES[reg["ghost.style"].value] == "HANDS"


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


class Synth:
    """A tracker of synthetic hands with skeletons (`snapshot`), no camera."""

    status, on = "tracking", True

    def __init__(self):
        self.seq, self.now = 0, []

    def put(self, *hands_):
        self.seq, self.now = self.seq + 1, list(hands_)

    def snapshot(self):
        side = lambda h: h.type.name.lower()
        return (self.seq, 0.0, {side(h): (features(h), 1.0) for h in self.now},
                {side(h): skeleton(h) for h in self.now})


def boxed_io(box, dofs=("x", "y", "z", "roll", "pitch", "yaw")) -> HandsIO:
    io = HandsIO(HandSettings.from_config({"dofs": list(dofs)}), {}, source=Synth(),
                 out=NS(send=lambda m: None), clock=lambda: 0.0)
    io.box = box
    return io


def test_the_camera_frames_the_interaction_box_when_one_is_set():
    """Plan 18 fork 4: with a box, `box_of` is the box — and the axis
    ranges, as before, for a coordinate the box leaves open."""
    box = {"x": (-262.0, 262.0), "y": (71.5, 402.0), "z": (-148.0, 131.0)}
    io = boxed_io(None)
    before = G.box_of(io)
    assert before == ((-220.0, 220.0), (100.0, 350.0), (-100.0, 100.0))   # no box: today's
    io.box = box
    assert G.box_of(io) == ((-262.0, 262.0), (71.5, 402.0), (-148.0, 131.0))
    io.box = {**box, "y": None}                       # open: that coordinate's axis ranges
    st = {a.name: s for a, s in zip(io.axes, io.state)}
    st["right.y"].lo, st["right.y"].hi = 120.0, 300.0
    assert G.box_of(io) == ((-262.0, 262.0), (100.0, 350.0), (-148.0, 131.0))
    io.box = {"x": None, "y": None, "z": None}
    assert G.box_of(io) == G.box_of(boxed_io(None, dofs=("x", "y", "z"))) == before
    # a source with a box and no axes (and one from before a hot reload, with neither)
    assert G.box_of(NS(box={**box, "z": None})) == ((-262.0, 262.0), (71.5, 402.0),
                                                    (-100.0, 100.0))
    assert G.box_of(NS()) == before
    # and the camera frames it: the padded box's corners are in frame, one on the edge
    io.box = box
    m = G.basis("desktop")
    vp, _ = G.camera(G.box_of(io), m, 16 / 9)
    corners = np.array([(x, y, z) for x in box["x"] for y in box["y"] for z in box["z"]]) @ m.T
    lo, hi = corners.min(0) - G.PAD, corners.max(0) + G.PAD
    clip = np.array([(x, y, z, 1.0) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                     for z in (lo[2], hi[2])]) @ vp.T
    ndc = clip[:, :3] / clip[:, 3:]
    assert (clip[:, 3] > 0).all() and (np.abs(ndc) <= 1.0 + 1e-6).all()
    assert np.abs(ndc[:, :2]).max() > 0.99


def test_a_hand_outside_the_box_fades_out():
    """Plan 18 fork 5: a hand tracked but outside the box is absent to the
    ghost too — no dim ghost; it fades over FADE_OUT where it left."""
    io = boxed_io({"x": (-200.0, 200.0), "y": (80.0, 400.0), "z": (-150.0, 150.0)})
    gh = G.Ghost(ctx=None, state=G.GhostState(on=True))
    gh.source = io
    inside = (hand("left", "open", (-90.0, 210.0, 0.0)), hand("right", "fist", (90.0, 200.0, 0.0)))
    for k in range(20):
        io.source.put(*inside)
        io.poll(1 / 60)
        seen = gh.step(k / 60)
    assert {s for s, _, _ in seen} == {"left", "right"} and gh.sides["right"].fade == 1.0
    last = io.skeleton["right"]
    fades, t = [], 20 / 60
    while gh.sides["right"].fade > 0.0:
        io.source.put(inside[0], hand("right", "fist", (300.0, 200.0, 0.0)))   # tracked, outside
        io.poll(1 / 60)
        assert set(io.skeleton) == {"left"} and io.outside["right"]["x"] == 300.0
        seen = {s: (sk, f) for s, sk, f in gh.step(t)}
        if "right" in seen:
            assert seen["right"][0] is last           # where it left, not where it is now
        assert seen["left"][1] == 1.0
        fades.append(gh.sides["right"].fade)
        t += 1 / 60
    assert len(fades) >= int(G.FADE_OUT * 60) - 1 and all(a > b for a, b in pairwise(fades))
    assert {s for s, _, _ in gh.step(t)} == {"left"}                 # gone: no dim ghost
    io.source.put(*inside)                            # back inside: fading up
    io.poll(1 / 60)
    assert 0.0 < {s: f for s, _, f in gh.step(t + 1 / 60)}["right"] <= 1.0


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
    if renderer is None and fx is not None:      # plan 33 R23: its run, as a load lands it
        from hyperspace.graphmigrate import wiring_of
        r.wiring = wiring_of(fx)
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


def test_a_failed_target_build_is_all_or_nothing(ctx, monkeypatch):
    """Plan 21 WP5 R3: a piece of the hands' layer the driver refuses (here
    the depth buffer) leaves nothing half-built — what was made is
    released, no target is kept — the frame is the frame without hands,
    `Ghost.error` says why once, and no frame raises. The old `_ensure`
    kept the texture and the size, so every later frame found them
    "ready" and raised on the missing framebuffer."""
    base, _ = frame(ctx)
    r = Renderer(ctx)
    frame(ctx, renderer=r, on=False, frames=1)            # the renderer's own targets first
    made, refused = [], []
    real_tex = moderngl.Context.texture

    def tex(self, *a, **k):
        t = real_tex(self, *a, **k)
        made.append(t)
        return t

    def no_depth(self, *a, **k):
        refused.append(1)
        raise moderngl.Error("out of memory")

    with monkeypatch.context() as m:
        m.setattr(moderngl.Context, "texture", tex)
        m.setattr(moderngl.Context, "depth_renderbuffer", no_depth)
        out, _ = frame(ctx, src=tracker(), renderer=r)     # four frames, none raises
    gh = r.ghost
    assert np.array_equal(out, base)
    assert len(refused) == 4                               # each frame tried from nothing
    assert gh._tex is None and gh._fbo is None and gh._msaa is None and gh._res == []
    assert gh.size == (0, 0)
    ours = [t for t in made if t.size == (W, H) and t.components == 4]
    assert len(ours) == 4 and all(type(t.mglo).__name__ == "InvalidObject" for t in ours)
    assert gh.error == "ghost layer 480×320: Error: out of memory"
    on, _ = frame(ctx, src=tracker(), renderer=r, t0=5.0)  # the driver relents: hands
    base_later, _ = frame(ctx, t0=5.0)
    assert not np.array_equal(on, base_later) and gh._fbo is not None


def test_one_reload_round_rebuilds_the_ghost_once(ctx, monkeypatch):
    """Plan 21 WP5 R5: a ghost.py save reloads ghost.py and render.py, and
    the reloader calls both `Renderer.on_reload` and `Ghost.on_reload`
    (app.main's target list, in that order). The ghost's programs are
    built once in that round, not twice; a render.py save alone (the
    Ghost not re-classed) rebuilds none of them. Two reloads in a row are
    harmless: the hands still draw and nothing is left in error."""
    _, r = frame(ctx, src=tracker())
    gh = r.ghost
    assert gh.geometry is not None
    builds = []
    real = G.Ghost._build
    with monkeypatch.context() as m:
        m.setattr(G.Ghost, "_build", lambda self: builds.append(1) or real(self))
        geo = gh.geometry
        r.on_reload()                                      # a render.py save
        assert builds == [] and gh.geometry is geo
        r.on_reload()                                      # a ghost.py save: both hooks
        gh.on_reload()
        assert len(builds) == 1
        gh.on_reload()                                     # and once more: still harmless
        assert len(builds) == 2
    out, _ = frame(ctx, src=tracker(), renderer=r, t0=5.0)
    base, _ = frame(ctx, t0=5.0)
    assert not np.array_equal(out, base) and gh.error == ""


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
    assert r1.stats["fx_on"]
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


def test_one_layer_composites_onto_many_targets_as_draw_does(ctx):
    """Plan 21 WP1: `layer` renders the hands once, `composite` lays them
    over any number of targets — each the same bytes `draw` leaves — and
    `tex` is the layer only while one was drawn. With nothing to show,
    `layer` says so and `composite` touches nothing."""
    def ground():
        fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        ctx.clear(0.1, 0.2, 0.3, 1.0)
        return fbo

    def px(fbo):
        return np.frombuffer(fbo.read(components=4), dtype=np.uint8).copy()

    a = Renderer(ctx).ghost
    a.state.on, a.state.alpha, a.source = True, 0.7, tracker()
    want = ground()
    assert a.draw(want, (0, 0, W, H), 1.0)
    b = Renderer(ctx).ghost
    b.state.on, b.state.alpha, b.source = True, 0.7, tracker()
    assert b.tex is None
    assert b.layer((W, H), 1.0) and b.tex is not None and b.tex.size == (W, H)
    for _ in range(2):
        got = ground()
        assert b.composite(got, (0, 0, W, H), opaque=True)
        assert ctx.fbo is got and ctx.viewport == (0, 0, W, H)
        assert np.array_equal(px(got), px(want))
        got.release()
    assert b.readout is None                           # no readout asked for: one layer
    b.source = tracker({})                             # no hand: no layer, nothing composited
    assert not b.layer((W, H), 2.0) and b.tex is None
    empty = ground()
    assert not b.composite(empty, (0, 0, W, H))
    assert np.array_equal(px(empty), px(ground()))
    assert ctx.error == "GL_NO_ERROR"


def test_the_readout_layer_is_the_guide_apart_from_the_hands(ctx):
    """Plan 21 WP2 (fork F3): `layer(…, readout=True)` with the guide on
    puts the hands alone in `tex` — the same bytes as a ghost with no
    guide — and the guide in `readout`, drawn behind the hands' depth:
    where the one-layer picture shows the guide, the readout shows the
    same colour; where a palm hides an ON HAND gauge, the readout is
    empty. With the guide off there is no readout."""
    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.7
    src = NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
             gates=io.gates)

    def layers(guide, readout):
        gh = Renderer(ctx).ghost
        gh.state.on, gh.state.alpha, gh.state.guide, gh.source = True, 1.0, guide, src
        for k in range(4):                                # faded fully in
            assert gh.layer((W, H), 1.0 + k / 30, readout=readout)
        rd = lambda t: np.frombuffer(t.read(), dtype=np.uint8).reshape(H, W, 4).astype(int)
        return gh, rd(gh.tex), (rd(gh.readout) if gh.readout is not None else None)

    _, hands_only, none = layers(0, True)
    assert none is None                                   # no guide: no readout
    for guide in (1, 2):
        _, single, none = layers(guide, False)
        assert none is None
        gh, hands, ro = layers(guide, True)
        assert np.array_equal(hands, hands_only), G.GUIDES[guide]
        solid = ro[..., 3] == 255
        assert solid.sum() > 150
        assert np.abs(ro[solid] - single[solid]).max() <= 1
        if guide == 2:                                    # on the palm: partly hidden by it
            hidden = (single[..., 3] == 255) & (np.abs(single - hands_only).sum(axis=2) == 0) \
                & (hands_only[..., 3] == 255)
            assert hidden.sum() > 500 and ro[hidden][..., 3].max() == 0
        gh.layer((W, H), 1.2, readout=False)              # asked for nothing: back to one layer
        assert gh.readout is None


# ---------------------------------------------------------------- ghost.style (plan 21 WP6)

def _guided_poses(skel=None, guide=2, mirror=False, style=0):
    """(poses with their guide rows, view_proj, eye) from a Ghost with no
    GL drawn, the synthetic hands faded fully in."""
    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.7
    src = NS(skeleton=both() if skel is None else skel, cfg={"mode": "desktop"}, axes=io.axes,
             state=io.state, gates=io.gates)
    gh = G.Ghost(None)
    gh.state.on, gh.state.guide, gh.state.mirror, gh.state.style = True, guide, mirror, style
    gh.source = src
    for k in range(4):
        got = gh.poses(1.0 + k / 30, W / H)
    return got


def _palm_only() -> dict:
    sk = both()
    for v in sk.values():
        v["digits"] = []
    return sk


def test_every_style_draws_from_the_same_poses():
    """Each style is a pure function of one pose (no GL): something for
    every hand, a different picture from every other style, the same
    parts for the same pose, and openness read from the pose alone — 0 a
    fist, 1 open — which PALMS' orb and CAGE's size follow."""
    poses, _, _ = _guided_poses()
    assert G.STYLES == ["HANDS", "JOINTS", "PALMS", "CAGE", "MARIONETTE"]
    assert len(G.PARTS) == len(G.STYLES) and G.PARTS[0] is G.hands_parts
    for p in poses:
        drawn = []
        for name, fn in zip(G.STYLES, G.PARTS):
            a, b = fn(p), fn(p)
            assert repr(a) == repr(b), name                       # pure
            spheres, _, _ = a
            assert spheres, name
            assert all(np.all(np.isfinite(c)) and r > 0 for c, r in spheres), name
            drawn.append(repr(a))
        assert len(set(drawn)) == len(G.STYLES)
    left, right = poses                                           # left open, right a fist
    assert G.openness(left) == 1.0 and G.openness(right) == 0.0
    orb = lambda p: G.palms_parts(p)[0][0][1]
    cage = lambda p: np.ptp(np.array([c for c, _ in G.cage_parts(p)[0]]), axis=0).max()
    assert orb(left) / left.width > orb(right) / right.width
    assert cage(left) > 1.5 * cage(right)
    # the cage turns with the palm: a palm rolled a quarter turn turns its corners
    m = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])
    turned = G.HandPose(right.side, right.palm, m @ right.normal, right.direction, right.width,
                        right.joints, right.widths, right.rots, right.basis)
    a = np.array([c for c, _ in G.cage_parts(right)[0]]) - right.palm
    b = np.array([c for c, _ in G.cage_parts(turned)[0]]) - right.palm
    assert not np.allclose(a, b)
    # out-of-range or junk style indexes draw HANDS
    for bad in (-1, 5, 99, "x", None):
        assert G.style_parts(bad) is G.hands_parts


def test_a_style_never_draws_the_guide(ctx):
    """No style reads the guide: a pose's parts are the same with its guide
    rows or without. Drawn, the hands' layer with the readout split off
    is the same bytes as a ghost with no guide at all, in every style —
    the guide goes to the readout layer only."""
    poses, _, _ = _guided_poses()
    for p in poses:
        assert p.guide[0] and p.guide[1]
        bare = G.HandPose(p.side, p.palm, p.normal, p.direction, p.width, p.joints, p.widths,
                          p.rots, p.basis, p.fade, p.colour)
        for fn in G.PARTS:
            assert repr(fn(p)) == repr(fn(bare))
    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.7
    src = NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
             gates=io.gates)

    def layer(style, guide):
        gh = Renderer(ctx).ghost
        gh.state.on, gh.state.alpha, gh.state.guide, gh.state.style = True, 1.0, guide, style
        gh.source = src
        for k in range(4):
            assert gh.layer((W, H), 1.0 + k / 30, readout=True)
        rd = lambda t: np.frombuffer(t.read(), dtype=np.uint8)
        return rd(gh.tex), (rd(gh.readout) if gh.readout is not None else None)

    seen = set()
    for style in range(len(G.STYLES)):
        hands, none = layer(style, 0)
        assert none is None
        split, ro = layer(style, 2)
        assert np.array_equal(split, hands), G.STYLES[style]
        assert ro is not None and ro.reshape(-1, 4)[:, 3].max() == 255
        seen.add(hands.tobytes())
    assert len(seen) == len(G.STYLES)                             # five different layers


def test_a_palm_only_hand_draws_in_every_style(ctx):
    """A skeleton with no digits (bindings that gave none): every style
    still draws the hand — a palm orb (HANDS: its palm disc, as ever) —
    on both sides of the frame."""
    poses, _, _ = _guided_poses(_palm_only(), guide=0)
    for p in poses:
        assert not len(p.joints)
        for name, fn in zip(G.STYLES, G.PARTS):
            spheres, _, tris = fn(p)
            assert spheres or tris, name
            if name != "HANDS":
                assert any(np.allclose(c, p.palm) and r >= 0.3 * p.width
                           for c, r in spheres), name
    base, _ = frame(ctx)
    for style in range(len(G.STYLES)):
        r = Renderer(ctx)
        r.ghost.state.style = style
        out, _ = frame(ctx, src=tracker(_palm_only()), renderer=r)
        changed = np.abs(out[..., :3].astype(int) - base[..., :3]).sum(axis=2) > 30
        assert changed[:, : W // 2].sum() > 100 and changed[:, W // 2:].sum() > 100, style
        assert r.ghost.error == ""


def _old_parts(p):
    """CapsuleHands.parts as it stood on the parent commit (b7aa67a), frozen."""
    import math
    col_r = G.FINGER_R * p.width
    spheres, tubes, tris = [], [], []
    n = p.normal / max(np.linalg.norm(p.normal), 1e-9)
    if len(p.joints):
        for d in range(len(p.joints)):
            for b in range(4):
                w = p.widths[d, b]
                r = G.BONE_R * w if w > 0 else col_r
                if d == 0 and b == 0:
                    continue
                a, e = p.joints[d, b], p.joints[d, b + 1]
                if np.linalg.norm(e - a) > 1e-3:
                    tubes.append((a, e, r))
                spheres.append((e, r))
                if b == 0 or (d == 0 and b == 1):
                    spheres.append((a, r))
        ring = ([p.joints[d, 0] for d in (1,)] + [p.joints[d, 1] for d in (1, 2, 3, 4)]
                + [p.joints[d, 0] for d in (4, 3, 2)])
    else:
        f = p.direction / max(np.linalg.norm(p.direction), 1e-9)
        s = np.cross(n, f)
        ring = [p.palm + f * 0.55 * p.width * math.cos(a) + s * 0.5 * p.width * math.sin(a)
                for a in np.linspace(0.0, 2 * math.pi, 16, endpoint=False)]
    c = np.mean(ring, axis=0)
    for k in range(len(ring)):
        tris.append(((c, n), (ring[k], n), (ring[(k + 1) % len(ring)], n)))
    if len(p.joints):
        tb, tm = p.joints[0, 1], p.joints[0, 2]
        ib, ik = p.joints[1, 0], p.joints[1, 1]
        tris.append(((tb, n), (tm, n), (ik, n)))
        tris.append(((tb, n), (ik, n), (ib, n)))
    return spheres, tubes, tris


class _OldCapsuleHands(G.Geometry):
    """CapsuleHands.draw as it stood on the parent commit (b7aa67a), with
    the guide inside it behind two flags — frozen, to hold HANDS to it."""

    def draw(self, poses, view_proj, eye, *, hands=True, guide=True):
        s_rows, t_rows, m_rows = [], [], []
        for p in poses:
            if hands:
                col = (*p.colour, float(p.fade))
                spheres, tubes, tris = _old_parts(p)
                s_rows += [(*c, r, *col) for c, r in spheres]
                t_rows += [(*a, *b, r, *col) for a, b, r in tubes]
                for tri in tris:
                    m_rows += [(*q, *nn, *col) for q, nn in tri]
            if guide:
                s_rows += p.guide[0]
                t_rows += p.guide[1]
        vp = np.asarray(view_proj, dtype="f4").T.tobytes()
        ey = tuple(float(x) for x in eye)
        for prog in self.progs:
            prog["u_vp"].write(vp)
            prog["u_eye"].value = ey
        for rows, buf, vao, verts in ((m_rows, self._mesh, self.vaos[2], None),
                                      (s_rows, self._inst_s, self.vaos[0], self._n_s),
                                      (t_rows, self._inst_t, self.vaos[1], self._n_t)):
            if not rows:
                continue
            data = np.asarray(rows, dtype="f4")
            buf.orphan(max(data.nbytes, buf.size))
            buf.write(data.tobytes())
            if verts is None:
                vao.render(moderngl.TRIANGLES, vertices=len(data))
            else:
                vao.render(moderngl.TRIANGLES, vertices=verts, instances=len(data))


def test_hands_is_the_old_geometry_byte_for_byte(ctx):
    """HANDS through the new `Geometry` — the guide's rows passed in by
    `Ghost` as `extra` — draws the same bytes as the parent commit's
    `CapsuleHands.draw` with the guide inside it, in each of the three
    ways the pass calls it (hands and guide, hands alone, the guide alone),
    for full and palm-only hands, mirrored or not, the guide beside or on
    the hand. (Also checked once at the layer and whole-frame level
    against hashes taken on the parent commit when this was built.)"""
    new, old = G.Geometry(ctx), _OldCapsuleHands(ctx)
    assert G.CapsuleHands.parts is G.hands_parts
    depth = ctx.depth_renderbuffer((W, H))
    target = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)],
                             depth_attachment=depth)

    def shot(geo, *a, **k):
        target.use()
        ctx.viewport = (0, 0, W, H)
        ctx.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
        ctx.disable(moderngl.BLEND)
        ctx.enable(moderngl.DEPTH_TEST)
        geo.draw(*a, **k)
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        return target.read(components=4)

    n = 0
    for skel in (None, _palm_only(), both("open", "open")):
        for guide in (1, 2):
            for mirror in (False, True):
                poses, vp, eye = _guided_poses(skel, guide, mirror)
                guides = [p.guide for p in poses]
                for (parts, extra), legacy in (((G.hands_parts, guides), {}),
                                               ((G.hands_parts, None), {"guide": False}),
                                               ((None, guides), {"hands": False})):
                    want = shot(old, poses, vp, eye, **legacy)
                    got = shot(new, poses, vp, eye, parts, extra)
                    assert got == want, (guide, mirror, legacy)
                    assert any(want), legacy
                    n += 1
    assert n == 36
    target.release()
    depth.release()
    new.release()
    old.release()


def test_the_guide_on_the_hand_reads_the_same_in_every_style_but_hands(ctx):
    """Review of PR #122: an ON HAND gauge sits at the palm, where PALMS,
    JOINTS, CAGE and MARIONETTE put a solid far bigger than a guide ball.
    In those styles the guide is drawn over the style, never hidden by it:
    the readout layer is the same bytes in all four (the guide alone, no
    style in front of it), and in the single layer the guide's solid
    pixels are those same pixels, with the style still drawn round them.
    HANDS keeps its gauge partly behind the palm (byte for byte, above)."""
    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.5                                     # the balls at the palm
    src = NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
             gates=io.gates)

    def layer(style, guide, readout):
        gh = Renderer(ctx).ghost
        gh.state.on, gh.state.alpha, gh.state.guide, gh.state.style = True, 1.0, guide, style
        gh.source = src
        for k in range(4):
            assert gh.layer((W, H), 1.0 + k / 30, readout=readout)
        rd = lambda t: np.frombuffer(t.read(), dtype=np.uint8).reshape(H, W, 4).astype(int)
        return rd(gh.tex), (rd(gh.readout) if gh.readout is not None else None)

    ros = {}
    for style in range(1, len(G.STYLES)):
        _, ro = layer(style, 2, True)
        ros[style] = ro
        single, _ = layer(style, 2, False)
        bare, _ = layer(style, 0, False)
        solid = ro[..., 3] == 255
        assert solid.sum() > 150, G.STYLES[style]
        assert np.abs(single[solid] - ro[solid]).max() <= 1, G.STYLES[style]
        # the style is still there round the guide
        rest = (bare[..., 3] > 0) & (ro[..., 3] == 0)
        assert rest.sum() > 200 and np.array_equal(single[rest], bare[rest]), G.STYLES[style]
    first = ros[1]
    for style, ro in ros.items():
        assert np.array_equal(ro, first), G.STYLES[style]
    # HANDS: the palm still hides part of its gauge
    _, hands_ro = layer(0, 2, True)
    assert (hands_ro[..., 3] == 255).sum() < (first[..., 3] == 255).sum()
