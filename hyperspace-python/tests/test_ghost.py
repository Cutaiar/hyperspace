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
    for pid in ("ghost.on", "ghost.alpha", "ghost.mirror"):
        p = reg[pid]
        assert p.persist and p.modulatable and part_of(p) == "session", pid
    assert reg["ghost.on"].value is False and 0.0 < reg["ghost.alpha"].value <= 1.0


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
    # the right hand is red, the left near-white
    r_px = on[:, W // 2:][changed[:, W // 2:]]
    assert r_px[:, 0].mean() > r_px[:, 2].mean() + 40


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
