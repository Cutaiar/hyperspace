"""The poi's guide (plan 47, the poi: hyperspace/poi_guide.py): the
handle, the string and the weight's marker where they are in the world,
drawn over each output that shows the hands — and nothing at all with the
poi or the guide off."""

import math
from types import SimpleNamespace

import numpy as np
import pytest
from test_poi import FakePad, circle, on, rig

from hyperspace import geometry, poi, poi_guide
from hyperspace.render import Renderer

W, H = 320, 240


def hanging(**dials):
    reg, state, view = rig(**dials)
    pad = FakePad()
    on(reg, state, pad, settle=120)
    return reg, state, view, pad


def project(p, fov=geometry.EYE_FOV, distance=geometry.EYE_DISTANCE):
    """A world point to (column, row) in a W×H picture, rows down."""
    clip = geometry.eye_matrix(W, H, fov, distance) @ np.array([*p, 1.0])
    ndc = clip[:3] / clip[3]
    return (ndc[0] + 1) / 2 * W, (1 - ndc[1]) / 2 * H


def test_nothing_shows_with_the_poi_off_the_guide_off_or_no_home_yet():
    reg, state, view = rig()
    assert poi_guide.rows(state, view.pan, view.zoom) is None          # off
    assert poi_guide.rows(None, view.pan, view.zoom) is None
    state.on = True
    assert poi_guide.rows(state, view.pan, view.zoom) is None          # no home yet
    reg, state, view, _ = hanging()
    assert poi_guide.rows(state, view.pan, view.zoom) is not None
    reg["poi.guide"].set(False)
    assert poi_guide.rows(state, view.pan, view.zoom) is None
    assert not reg["poi.guide"].persist and not reg["poi.guide"].modulatable


def test_the_weight_sits_on_the_shape_and_the_string_runs_tip_to_weight():
    reg, state, view, pad = hanging()
    circle(reg, state, pad, 1.3)                      # somewhere mid-swing
    spheres, tubes = poi_guide.rows(state, view.pan, view.zoom)
    wrist, tip, weight = (s[:3] for s in spheres)
    assert weight == pytest.approx((view.pan[0], -view.pan[1], 0.0))  # the shape's centre
    handle, string = tubes
    assert handle[:3] == pytest.approx(wrist) and handle[3:6] == pytest.approx(tip)
    assert string[:3] == pytest.approx(tip) and string[3:6] == pytest.approx(weight)
    home = state.pan_home
    assert tip == pytest.approx(tuple(np.add([home[0], -home[1], 0.0], state.tip())))
    assert spheres[2][4:7] == poi_guide.WEIGHT_COL


def test_the_handle_follows_the_pan_home_and_the_marker_grows_with_the_depth_zoom():
    reg, state, view, pad = hanging(gravity=0.0, drag=0.0)
    reg["camera.pan.x"].set(1.0)                      # a knob moves home
    state.ball = [0.0, 0.0, 1.0 + poi.HANDLE]         # toward the eye
    state.ball_v = [0.0, 0.0, 0.0]
    for _ in range(2):
        pad.frame()
        poi.step(state, pad, reg, 1 / 60)
    spheres, _ = poi_guide.rows(state, view.pan, view.zoom)
    assert spheres[0][0] == pytest.approx(1.0 + state.wrist[0])       # the wrist at home
    assert spheres[2][3] == pytest.approx(poi_guide.WEIGHT_R * 2 ** poi.DEPTH_OCTAVES,
                                          rel=0.02)


def test_the_string_is_bright_taut_and_dim_slack():
    _, state, view, _ = hanging()
    _, tubes = poi_guide.rows(state, view.pan, view.zoom)
    assert tubes[1][7:10] == poi_guide.TAUT_COL       # hanging: the weight on it
    state.ball = list(np.add(state.tip(), [0.1, -0.1, 0.0]))
    _, tubes = poi_guide.rows(state, view.pan, view.zoom)
    assert tubes[1][7:10] == poi_guide.SLACK_COL


def _frame(ctx, r, view):
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    r.draw(view, W, H, t_now=1.0)
    out = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4)[::-1].copy()
    fbo.release()
    return out


def test_the_renderer_lays_the_guide_over_the_output_where_the_weight_and_tip_are(ctx):
    _, state, view, _ = hanging()
    r = Renderer(ctx)
    before = _frame(ctx, r, view)                     # no poi handed over: as ever
    r.poi_source = state
    out = _frame(ctx, r, view)
    assert r.poi_guide is not None and r.poi_guide.error == ""
    spheres, _ = poi_guide.rows(state, view.pan, view.zoom)
    cx, cy = project(spheres[2][:3])
    red = out[int(cy), int(cx)]
    assert red[0] > 150 and red[1] < 90                # the weight's marker, the accent
    tx, ty = project(spheres[1][:3])                  # the handle (end-on at rest)
    assert out[int(ty), int(tx)][:3].astype(int).sum() > 120
    assert not np.array_equal(out[int(ty), int(tx)], before[int(ty), int(tx)])
    far = (5, 5)
    assert np.array_equal(out[far], before[far])       # the rest of the picture untouched
    state.on = False
    assert np.array_equal(_frame(ctx, r, view), before)


def test_an_outputs_hands_switch_mutes_the_guide(ctx):
    _, state, view, _ = hanging()
    r = Renderer(ctx)
    r.poi_source = state
    lit = _frame(ctx, r, view)
    r.poi_source = None
    plain = _frame(ctx, r, view)
    r.poi_source = state
    from hyperspace.outputs import Switches
    sw = Switches(hands=False)
    seen = []
    real = r._compose

    def compose(v, *a, **k):
        v.switches = sw
        seen.append(v)
        return real(v, *a, **k)
    r._compose = compose
    muted = _frame(ctx, r, view)
    assert seen and not np.array_equal(lit, plain)
    assert np.array_equal(muted[..., :3], plain[..., :3])


def test_the_tip_projects_inside_the_picture_at_rest():
    _, state, view, _ = hanging()
    spheres, _ = poi_guide.rows(state, view.pan, view.zoom)
    for p in spheres:
        x, y = project(p[:3])
        assert 0 <= x < W and 0 <= y < H and math.isfinite(x)


def test_the_guide_tells_the_poi_what_this_output_shows_whether_or_not_it_draws():
    """Row 817: the box is the real output's, through this view's eye, with
    nothing drawn and no GL touched (the poi's guide switched off)."""
    state = poi.PoiState(on=True, guide=False)
    view = SimpleNamespace(pan=(0.0, 0.0), zoom=1.0, eye_fov=50.0, eye_distance=6.0)
    guide = poi_guide.PoiGuide(None)
    assert guide.layer((1000, 500), view, state) is False
    assert state.box == poi.box_for(1000, 500, 50.0, 6.0)
    assert state.box != poi.DEFAULT_BOX
