"""Plan 26 A4b: the point-cloud geometry node — a cloud device's frames
(plan 27 B4's `devices.PointCloud`, `DeviceRegistry.clouds`) drawn as
points in the shared camera.

The renderer is handed the device registry (`Renderer.cloud_source`); a
listed `cloud` device puts a point-cloud node (`graph.PointCloud`, kind
`cloud`) into the default scene, solid, before the see-through shape. The
fixture recording (`tests/fixtures/clouds/knot.npz`, B4's) is played by a
real `cloud` device from a scratch home; no sensor. The pictures with the
shape are `tests/test_golden_frames.py`'s (`cloud/*`).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest
from test_outputs import H, W, px, rig, views

from hyperspace import devices
from hyperspace import graph as G
from hyperspace import outputs as O
from hyperspace.geometry import EYE_DISTANCE, EYE_FOV, eye_matrix
from hyperspace.view import ViewState

FIXTURE = Path(__file__).parent / "fixtures" / "clouds" / "knot.npz"
S = O.Switches
# the test shape (10, the 4D shape at the default view) lies inside |z| < 0.98
# in the world: a point nearer than this is in front of all of it
NEAR_Z = 1.1


def registry(home: Path, file: str = "clouds/knot.npz", copy: bool = True,
             role: str = "scan") -> devices.DeviceRegistry:
    """A device registry over a scratch home whose config lists one
    recorded cloud (the fixture copied into the home, as the owner would)."""
    if copy:
        (home / "clouds").mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURE, home / "clouds" / "knot.npz")
    reg = devices.DeviceRegistry([{"role": role, "kind": "cloud", "file": file}],
                                 devices.Context(home=home), clock=lambda: 0.0)
    reg.open_all()
    return reg


# ---------------------------------------------------------------- no GL


def test_a_listed_cloud_is_the_scenes_first_geometry_and_none_listed_changes_nothing():
    """`build_graph(…, clouds)`: one `cloud` node per listed role, named
    by the naming rule (`cloud`, `cloud.2`), solid, the scene's first
    geometries (before the hands and the shape), each its own timed line;
    with none the graph is today's, node for node."""
    vs = [O.View(S(), (W, H))]
    plain = G.build_graph(vs)
    assert [n.name for n in G.build_graph(vs, None, ()).order] == \
        [n.name for n in plain.order]
    assert plain.clouds == () and not any(n.KIND == G.CLOUD_KIND for n in plain.order)
    g = G.build_graph(vs, G.Wiring(hands="scene"), ("scan", "lidar"))
    assert g.clouds == ("scan", "lidar")
    scene = g.nodes["scene"]
    geoms = scene.geometries()
    assert [n.name for n in geoms] == ["cloud", "cloud.2", "hands", "shape"]
    assert [n.role for n in geoms[:2]] == ["scan", "lidar"]
    assert [n.source for n in geoms[:2]] == ["cloud:scan", "cloud:lidar"]
    assert all(n.SOLID and n.TIMED and n.OUTPUT == G.GEOMETRY for n in geoms[:2])
    assert g.timed[:3] == ["cloud", "cloud.2", "hands"]
    # the rest of the graph is the one without clouds
    assert [n.name for n in g.order if n.KIND != G.CLOUD_KIND] == \
        [n.name for n in G.build_graph(vs, G.Wiring(hands="scene")).order]


def test_the_listed_roles_are_the_cloud_devices_of_the_registry(tmp_path):
    """`cloud_roles`: the `cloud` devices a registry lists, open or not, in
    list order; none for no registry or one that raises."""
    assert G.cloud_roles(None) == ()
    devs = [NS(kind="midi", role="apc"), NS(kind="cloud", role="scan"),
            NS(kind="cloud", role="lidar")]
    assert G.cloud_roles(devs) == ("scan", "lidar")

    class Broken:
        def __iter__(self):
            raise RuntimeError("mid-change")

    assert G.cloud_roles(Broken()) == ()
    missing = registry(tmp_path, copy=False)          # listed, its file not there
    assert G.cloud_roles(missing) == ("scan",) and missing.clouds == {}


def test_the_cloud_params_are_session_and_default_to_a_cloud_at_the_shapes_size():
    """cloud.* — a session group (a preset never moves them); the scale
    puts the fixture (±3 units) at about the shape's size (radius 1)."""
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import SESSION_GROUPS, build_registry

    chain = Analyzer(Analyser())
    view = ViewState()
    reg = build_registry(view, Control(chain), NS(chain=chain))
    assert "cloud" in SESSION_GROUPS
    ids = [p.id for p in reg if p.group == "cloud"]
    assert ids == ["cloud.size", "cloud.scale", "cloud.bright", "cloud.colors"]
    assert reg["cloud.size"].value == 2.0 and reg["cloud.scale"].value == 0.3
    assert reg["cloud.bright"].value == 1.0 and reg["cloud.colors"].value is True
    reg["cloud.scale"].set(0.5)
    assert view.cloud_scale == 0.5
    pts = devices.read_clouds(FIXTURE).points
    assert 0.8 < float(np.abs(pts).max()) * 0.3 < 1.0


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def _view(**kw) -> ViewState:
    s = ViewState(instances=0)          # no shape: the cloud alone on the ground
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _draw(ctx, r, vs, s, reg=None, frames=3, t0=2.0, dt=0.0):
    """`frames` frames: the registry polled at the frame's clock (as
    `app.frame` does before drawing), then `draw_outputs`."""
    for k in range(frames):
        now = t0 + k * dt
        if reg is not None:
            reg.poll(1 / 60, now)
        r.draw_outputs(s, W, H, 1.0, vs, t_now=now)
    assert ctx.error == "GL_NO_ERROR"
    return px(ctx, vs[0].target)


def _project(points: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray]:
    """The shared camera on the CPU: (x, y) in pixels, top row first, and
    the clip w (> 0: in front of the eye)."""
    vp = eye_matrix(W, H, EYE_FOV, EYE_DISTANCE)
    q = np.c_[points.astype(np.float64) * scale, np.ones(len(points))]
    c = q @ vp.T
    return np.c_[(c[:, 0] / c[:, 3] + 1) * W / 2, (1 - c[:, 1] / c[:, 3]) * H / 2], c[:, 3]


def test_the_node_draws_the_fixtures_points_where_the_shared_camera_puts_them(ctx, tmp_path):
    """A recorded cloud device listed: the scene gains the `cloud` node and
    every point of the frame the device published is drawn at its place
    through the eye (the CPU projection), in its own colour — each pixel
    under a point's centre is the colour of one of the points whose dot
    covers it — and the ground far from every point is untouched."""
    reg = registry(tmp_path)
    r = rig(ctx, effects=(), hands=False)
    r.cloud_source = reg
    vs = views(ctx, S())
    s = _view()
    pic = _draw(ctx, r, vs, s, reg)
    assert r._graph.clouds == ("scan",) and "cloud" in r._graph.nodes
    cloud = reg.clouds["cloud:scan"]
    assert r.stats["clouds"] == {"cloud": cloud.n} and cloud.n >= 96
    xy, cw = _project(cloud.points, s.cloud_scale)
    assert (cw > 0).all()
    inside = (xy[:, 0] > 3) & (xy[:, 0] < W - 3) & (xy[:, 1] > 3) & (xy[:, 1] < H - 3)
    assert inside.sum() > 0.9 * cloud.n
    cols = np.rint(np.clip(cloud.colors, 0, 1) * 255).astype(int)
    rad = s.cloud_size
    checked = 0
    for k in np.flatnonzero(inside)[::7]:
        x, y = int(xy[k, 0]), int(xy[k, 1])
        centre = np.array([x + 0.5, y + 0.5])
        near = np.linalg.norm(xy - centre, axis=1) < rad + 0.75
        got = pic[y, x, :3]
        assert got.sum() > 0, (k, x, y)
        assert np.abs(cols[near] - got).max(axis=1).min() <= 2, (k, got, cols[near])
        checked += 1
    assert checked > 10
    # far from every point (more than a dot and a pixel away): the ground
    yy, xx = np.mgrid[0:H:5, 0:W:5]
    grid = np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]
    dist = np.min(np.linalg.norm(grid[:, None, :] - xy[None, :, :], axis=2), axis=1)
    far = grid[dist > rad + 2].astype(int)
    assert len(far) > 1000
    assert (pic[far[:, 1], far[:, 0], :3] == 0).all()
    # the colours switched off: every point white × the brightness
    pic2 = _draw(ctx, r, vs, _view(cloud_colors=False, cloud_bright=0.5), reg)
    x, y = (int(v) for v in xy[np.flatnonzero(inside)[0]])
    assert np.abs(pic2[y, x, :3] - 128).max() <= 1


def test_a_missing_cloud_draws_nothing_and_raises_nothing(ctx, tmp_path):
    """A `cloud` entry whose file is not there: the node is in the graph
    (the device is listed) and the frame is the frame with no registry,
    byte for byte; a registry with no cloud device adds no node; a source
    whose `clouds` raises draws nothing either."""
    s = _view(instances=1, shape=10)
    want = _draw(ctx, rig(ctx, effects=(), hands=False), views(ctx, S()), s)
    missing = registry(tmp_path, copy=False)
    r = rig(ctx, effects=(), hands=False)
    r.cloud_source = missing
    got = _draw(ctx, r, views(ctx, S()), s, missing)
    assert "cloud" in r._graph.nodes and r.stats["clouds"] == {"cloud": 0}
    assert "cloud_error" not in r.stats
    assert (got == want).all()

    r2 = rig(ctx, effects=(), hands=False)
    r2.cloud_source = devices.DeviceRegistry([], devices.Context(home=tmp_path))
    got2 = _draw(ctx, r2, views(ctx, S()), s)
    assert not any(n.KIND == G.CLOUD_KIND for n in r2._graph.order)
    assert (got2 == want).all()

    class Raising:
        def __iter__(self):
            return iter([NS(kind="cloud", role="scan")])

        @property
        def clouds(self):
            raise RuntimeError("the registry is mid-change")

    r3 = rig(ctx, effects=(), hands=False)
    r3.cloud_source = Raising()
    assert (_draw(ctx, r3, views(ctx, S()), s) == want).all()


def test_the_buffer_is_uploaded_only_when_the_frame_id_moves(ctx, tmp_path):
    """Drawn at 60 Hz, the 12 fps recording is uploaded once per recorded
    frame, not per drawn frame; a graph rebuilt for new switches keeps the
    buffer."""
    reg = registry(tmp_path)
    r = rig(ctx, effects=(), hands=False)
    r.cloud_source = reg
    s = _view()
    _draw(ctx, r, views(ctx, S()), s, reg, frames=4, dt=1 / 60)      # 0.05 s: frame 0
    slot = r._cloud_gl.slots["cloud"]
    assert slot["uploads"] == 1 and slot["key"][0] == 0
    _draw(ctx, r, views(ctx, S()), s, reg, frames=3, t0=2.0 + 1 / 12 + 1e-3, dt=1 / 60)
    assert slot["uploads"] == 2 and slot["key"][0] == 1
    _draw(ctx, r, views(ctx, S(), S(scene=False)), s, reg, frames=2, t0=2.1)
    assert r._cloud_gl.slots["cloud"] is slot and slot["uploads"] == 2


def test_a_point_in_front_of_the_shape_hides_it_and_one_behind_is_hidden(ctx, tmp_path):
    """Solid, with a real depth: the cloud (bigger dots) scaled round the shape, the
    points in front of the shape's surface are drawn over its strokes,
    and the shape's bright strokes are laid over the points behind it."""
    reg = registry(tmp_path)
    s = _view(instances=1, shape=10, bright=1.6, cloud_scale=0.6, cloud_size=6.0)
    alone = _draw(ctx, rig(ctx, effects=(), hands=False), views(ctx, S()), s)
    r = rig(ctx, effects=(), hands=False)
    r.cloud_source = reg
    both = _draw(ctx, r, views(ctx, S()), s, reg)
    cloud = reg.clouds["cloud:scan"]
    xy, _ = _project(cloud.points, s.cloud_scale)
    cols = np.rint(np.clip(cloud.colors, 0, 1) * 255).astype(int)
    front = back = 0
    for k in range(cloud.n):
        x, y = int(xy[k, 0]), int(xy[k, 1])
        if not (0 <= x < W and 0 <= y < H) or alone[y, x, :3].sum() < 30:
            continue                     # only where the shape drew something
        near = np.linalg.norm(xy - (x + 0.5, y + 0.5), axis=1) < s.cloud_size + 0.75
        is_point = np.abs(cols[near] - both[y, x, :3]).max(axis=1).min() <= 2
        # the eye at z = +distance: a point with a larger z is nearer
        if cloud.points[k, 2] * s.cloud_scale > NEAR_Z:
            front += 1
            assert is_point, k
        elif cloud.points[k, 2] * s.cloud_scale < -NEAR_Z:
            back += not is_point
    assert front > 0 and back > 0


def test_the_per_node_timer_names_the_cloud(ctx, tmp_path):
    """The cloud's draw is its own line on the SYSTEM page: `cloud`,
    before the scene's."""
    from hyperspace.render import PassTimer

    reg = registry(tmp_path)
    r = rig(ctx, effects=(), hands=False)
    r.cloud_source = reg
    _draw(ctx, r, views(ctx, S()), _view(), reg, frames=2)
    assert r._graph.timed[:2] == ["cloud", "scene"]
    if not r.timer.on:
        pytest.skip(f"this context has no timer queries: {r.timer.note}")
    _draw(ctx, r, views(ctx, S()), _view(), reg, frames=PassTimer.LAG + 3)
    ms = r.stats["gpu_ms"]
    assert list(ms) == r._graph.timed and list(ms)[:2] == ["cloud", "scene"]


def test_a_hot_reload_rebuilds_the_clouds_program_and_the_picture_is_the_same(ctx, tmp_path):
    """`Renderer.on_reload` releases the clouds' GL objects; the next frame
    makes them again from graph.py's source and draws the same picture."""
    reg = registry(tmp_path)
    r = rig(ctx, effects=(), hands=False)
    r.cloud_source = reg
    vs = views(ctx, S())
    before = _draw(ctx, r, vs, _view(), reg)
    old = r._cloud_gl
    r.on_reload()
    assert r._cloud_gl is None and old.slots == {}
    after = _draw(ctx, r, vs, _view(), reg)
    assert r._cloud_gl is not old and (after == before).all()
