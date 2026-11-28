"""Plan 26 A4b: the point-cloud geometry node — a cloud device's frames
(plan 27 B4's `devices.PointCloud`, `DeviceRegistry.clouds`) drawn as
points in the shared camera.

Plan 93: the node is the loadable patch's own (`{"kind": "cloud", "device":
<role>}`), drawn where a wire puts it into the scene, solid, before the
see-through shape; posed and copied as the shape is. The renderer is handed
the device registry (`Renderer.cloud_source`); a file from before `/13`
drew a cloud per listed device, which `graphmigrate.thirteen` says as those
nodes and wires (`with_clouds` here). The fixture recording
(`tests/fixtures/clouds/knot.npz`, B4's) is played by a real `cloud` device
from a scratch home; no sensor. The pictures with the shape are
`tests/test_golden_frames.py`'s (`cloud/*`).
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
from hyperspace import graphmigrate as M
from hyperspace import outputs as O
from hyperspace.geometry import EYE_DISTANCE, EYE_FOV, eye_matrix, turn_matrix
from hyperspace.graphmigrate import wired_wiring
from hyperspace.view import CloudState, ViewState

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


def with_clouds(wiring: G.Wiring, roles=("scan",)) -> G.Wiring:
    """`wiring` (the old words) wired, with a cloud node per role wired into its
    scene, as a file from before `/13` is read with those devices listed
    (`thirteen`)."""
    doc, _, n = M.thirteen({"graph": M.wired_of(wiring)}, tuple(roles))
    assert n == len(roles)
    return G.read_graph(doc["graph"]).wiring()


# ---------------------------------------------------------------- no GL


def test_a_wired_cloud_is_the_scenes_first_geometry_and_none_changes_nothing():
    """A cloud node per role wired first into the scene (an old file's clouds,
    `thirteen`), named by the naming rule (`cloud`, `cloud.2`), solid, the
    scene's first geometries (before the hands and the shape), each its own
    timed line; with none the graph is today's, node for node."""
    vs = [O.View(S(), (W, H))]
    plain = G.build_graph(vs)
    assert [n.name for n in G.build_graph(vs, None).order] == \
        [n.name for n in plain.order]
    assert not any(n.KIND == G.CLOUD_KIND for n in plain.order)
    g = G.build_graph(vs, with_clouds(G.Wiring(hands="scene"), ("scan", "lidar")))
    scene = g.nodes["scene"]
    geoms = scene.geometries()
    assert [n.name for n in geoms] == ["cloud", "cloud.2", "hands", "shape"]
    assert [n.role for n in geoms[:2]] == ["scan", "lidar"]
    assert [n.source for n in geoms[:2]] == ["cloud:scan", "cloud:lidar"]
    assert all(n.SOLID and n.TIMED and n.OUTPUT == G.GEOMETRY for n in geoms[:2])
    assert g.timed[:3] == ["cloud", "cloud.2", "hands"]
    # the rest of the graph is the one without clouds
    assert [n.name for n in g.order if n.KIND != G.CLOUD_KIND] == \
        [n.name for n in G.build_graph(vs, wired_wiring(G.Wiring(hands="scene"))).order]


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


def test_the_cloud_params_are_numbered_and_default_to_a_cloud_at_the_shapes_size():
    """cloud[.n].* — a patch group, declared as the graph names its clouds
    (plan 93, `declare_clouds`): the first keeps plan 26 A4b's four ids, then
    the shape's pose and copies under the same keys (`camera.*`, `view.inst_*`
    by the one pair of helpers); the scale puts the fixture (±3 units) at
    about the shape's size (radius 1)."""
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import PATCH_GROUPS, build_registry, declare_clouds

    chain = Analyzer(Analyser())
    view = ViewState()
    reg = build_registry(view, Control(chain), NS(chain=chain))
    assert "cloud" in PATCH_GROUPS and not [p for p in reg if p.group == "cloud"]
    declare_clouds(reg, ["cloud", "cloud.2"])
    ids = [p.id for p in reg if p.group == "cloud"]
    assert ids[:4] == ["cloud.size", "cloud.scale", "cloud.bright", "cloud.colors"]
    assert ids[4:16] == [f"cloud.{k}" for k in (
        "yaw", "pitch", "pan.x", "pan.y", "instances", "inst_layout", "inst_motion",
        "inst_amp", "inst_rate", "inst_fit", "inst_spacing", "inst_persp")]
    assert ids[16:] == [f"cloud.2.{k}" for k in (x.partition(".")[2] for x in ids[:16])]
    for k in ("yaw", "pitch", "pan.x", "instances", "inst_layout", "inst_spacing"):
        mine, shapes = reg[f"cloud.2.{k}"], reg[f"camera.{k}" if k in ("yaw", "pitch", "pan.x")
                                                 else f"view.{k}"]
        assert (mine.lo, mine.hi, mine.kind, mine.choices) == \
            (shapes.lo, shapes.hi, shapes.kind, shapes.choices), k
    assert reg["cloud.size"].value == 2.0 and reg["cloud.scale"].value == 0.3
    assert reg["cloud.bright"].value == 1.0 and reg["cloud.colors"].value is True
    assert reg["cloud.instances"].value == 1
    reg["cloud.2.scale"].set(0.5)
    reg["cloud.2.yaw"].set(0.25)
    assert view.clouds["cloud.2"].scale == 0.5 == view.clouds["cloud.2"].zoom
    assert view.clouds["cloud.2"].yaw == 0.25 and view.clouds["cloud"].scale == 0.3
    declare_clouds(reg, ["cloud"])
    assert "cloud.2.size" not in reg and list(view.clouds) == ["cloud"]
    pts = devices.read_clouds(FIXTURE).points
    assert 0.8 < float(np.abs(pts).max()) * 0.3 < 1.0


def test_a_clouds_copies_integrate_their_rate_as_the_shapes():
    s = ViewState()
    s.clouds["cloud"] = CloudState(inst_rate=2.0)
    s.integrate(0.5)
    assert s.clouds["cloud"].inst_phase == pytest.approx(1.0)
    s.seed_phases(3.0)
    assert s.clouds["cloud"].inst_phase == pytest.approx(6.0)


def test_a_cloud_naming_no_device_or_one_not_listed_says_so():
    assert G.cloud_said("", None) == G.CLOUD_NO_DEVICE
    devs = [NS(kind="cloud", role="scan")]
    assert G.cloud_said("lidar", devs) == G.CLOUD_NOT_LISTED.format(role="lidar")
    assert G.cloud_said("scan", devs) == G.CLOUD_WAITING.format(role="scan")


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


def _view(cloud: dict | None = None, **kw) -> ViewState:
    s = ViewState(instances=0)          # no shape: the cloud alone on the ground
    for k, v in kw.items():
        setattr(s, k, v)
    s.clouds["cloud"] = CloudState(**(cloud or {}))
    return s


def _clouded(ctx, reg=None, roles=("scan",)):
    """A rig whose wiring draws a cloud node per role (`with_clouds`)."""
    r = rig(ctx, effects=(), hands=False)
    r.wiring = with_clouds(r.old_wiring, roles)
    r.cloud_source = reg
    return r


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
    r = _clouded(ctx, reg)
    vs = views(ctx, S())
    s = _view()
    pic = _draw(ctx, r, vs, s, reg)
    assert "cloud" in r._graph.nodes
    cloud = reg.clouds["cloud:scan"]
    assert r.stats["clouds"] == {"cloud": cloud.n} and cloud.n >= 96
    xy, cw = _project(cloud.points, s.clouds["cloud"].scale)
    assert (cw > 0).all()
    inside = (xy[:, 0] > 3) & (xy[:, 0] < W - 3) & (xy[:, 1] > 3) & (xy[:, 1] < H - 3)
    assert inside.sum() > 0.9 * cloud.n
    cols = np.rint(np.clip(cloud.colors, 0, 1) * 255).astype(int)
    rad = s.clouds["cloud"].size
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
    pic2 = _draw(ctx, r, vs, _view({"colors": False, "bright": 0.5}), reg)
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
    r = _clouded(ctx, missing)
    got = _draw(ctx, r, views(ctx, S()), s, missing)
    assert "cloud" in r._graph.nodes and r.stats["clouds"] == {"cloud": 0}
    assert "cloud_error" not in r.stats
    assert (got == want).all()

    r2 = _clouded(ctx, devices.DeviceRegistry([], devices.Context(home=tmp_path)))
    got2 = _draw(ctx, r2, views(ctx, S()), s)        # (a node whose device is not listed)
    assert r2.stats["clouds"] == {"cloud": 0} and (got2 == want).all()
    r4 = rig(ctx, effects=(), hands=False)              # no cloud node: the devices add none
    r4.cloud_source = registry(tmp_path)
    got4 = _draw(ctx, r4, views(ctx, S()), s, r4.cloud_source)
    assert not any(n.KIND == G.CLOUD_KIND for n in r4._graph.order)
    assert (got4 == want).all()

    class Raising:
        def __iter__(self):
            return iter([NS(kind="cloud", role="scan")])

        @property
        def clouds(self):
            raise RuntimeError("the registry is mid-change")

    r3 = _clouded(ctx, Raising())
    assert (_draw(ctx, r3, views(ctx, S()), s) == want).all()


def test_the_buffer_is_uploaded_only_when_the_frame_id_moves(ctx, tmp_path):
    """Drawn at 60 Hz, the 12 fps recording is uploaded once per recorded
    frame, not per drawn frame; a graph rebuilt for new switches keeps the
    buffer."""
    reg = registry(tmp_path)
    r = _clouded(ctx, reg)
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
    s = _view({"scale": 0.6, "size": 6.0}, instances=1, shape=10, bright=1.6)
    alone = _draw(ctx, rig(ctx, effects=(), hands=False), views(ctx, S()), s)
    r = _clouded(ctx, reg)
    both = _draw(ctx, r, views(ctx, S()), s, reg)
    cloud = reg.clouds["cloud:scan"]
    look = s.clouds["cloud"]
    xy, _ = _project(cloud.points, look.scale)
    cols = np.rint(np.clip(cloud.colors, 0, 1) * 255).astype(int)
    front = back = 0
    for k in range(cloud.n):
        x, y = int(xy[k, 0]), int(xy[k, 1])
        if not (0 <= x < W and 0 <= y < H) or alone[y, x, :3].sum() < 30:
            continue                     # only where the shape drew something
        near = np.linalg.norm(xy - (x + 0.5, y + 0.5), axis=1) < look.size + 0.75
        is_point = np.abs(cols[near] - both[y, x, :3]).max(axis=1).min() <= 2
        # the eye at z = +distance: a point with a larger z is nearer
        if cloud.points[k, 2] * look.scale > NEAR_Z:
            front += 1
            assert is_point, k
        elif cloud.points[k, 2] * look.scale < -NEAR_Z:
            back += not is_point
    assert front > 0 and back > 0


def test_the_per_node_timer_names_the_cloud(ctx, tmp_path):
    """The cloud's draw is its own line on the SYSTEM page: `cloud`,
    before the scene's."""
    from hyperspace.render import PassTimer

    reg = registry(tmp_path)
    r = _clouded(ctx, reg)
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
    r = _clouded(ctx, reg)
    vs = views(ctx, S())
    before = _draw(ctx, r, vs, _view(), reg)
    old = r._cloud_gl
    r.on_reload()
    assert r._cloud_gl is None and old.slots == {}
    after = _draw(ctx, r, vs, _view(), reg)
    assert r._cloud_gl is not old and (after == before).all()


def _lit(pic) -> np.ndarray:
    """The lit pixels' (x, y), as floats."""
    ys, xs = np.nonzero(pic[..., :3].sum(axis=2) > 0)
    return np.c_[xs, ys].astype(np.float64)


def test_the_cloud_is_posed_as_the_shape_is(ctx, tmp_path):
    """Plan 93: the cloud's turn is the shape's turntable (`turn_matrix`: yaw,
    then pitch) and its pan moves it in world units, y down: each point drawn
    where the CPU's projection of the posed point puts it."""
    reg = registry(tmp_path)
    r = _clouded(ctx, reg)
    vs = views(ctx, S())
    pose = {"yaw": 0.7, "pitch": -0.4, "pan": [0.3, -0.2], "size": 1.0}
    pic = _draw(ctx, r, vs, _view(pose), reg)
    cloud = reg.clouds["cloud:scan"]
    turned = cloud.points.astype(np.float64) @ turn_matrix(0.7, -0.4).T
    xy, _ = _project(turned + np.array([0.3, 0.2, 0.0]) / 0.3, 0.3)
    lit = _lit(pic)
    # every point drawn is within a dot of a projected posed point, and the
    # other way round
    d = np.min(np.linalg.norm(lit[:, None] - (xy[None] - 0.5), axis=2), axis=1)
    assert len(lit) > 50 and np.percentile(d, 99) < 2.5
    inside = (xy[:, 0] > 2) & (xy[:, 0] < W - 2) & (xy[:, 1] > 2) & (xy[:, 1] < H - 2)
    d2 = np.min(np.linalg.norm(xy[inside][:, None] - 0.5 - lit[None], axis=2), axis=1)
    assert np.percentile(d2, 99) < 2.5
    assert not (pic == _draw(ctx, r, vs, _view({"size": 1.0}), reg)).all()


def test_the_cloud_is_copied_as_the_shape_is(ctx, tmp_path):
    """Plan 93: `instances` copies of the cloud at the shape's lattice
    (`Renderer._copies_of`, the field's rows): two copies draw the points twice,
    one copy at each row's centre and scale; 0 draws nothing."""
    from hyperspace.geometry import EYE_NEAR  # noqa: F401 — (the eye the rows are culled by)

    reg = registry(tmp_path)
    r = _clouded(ctx, reg)
    vs = views(ctx, S())
    one = _draw(ctx, r, vs, _view({"size": 1.0}), reg)
    assert r.stats["clouds"]["cloud"] == reg.clouds["cloud:scan"].n
    two_s = _view({"size": 1.0, "instances": 2, "scale": 0.1})
    two = _draw(ctx, r, vs, two_s, reg)
    n = reg.clouds["cloud:scan"].n
    assert r.stats["clouds"]["cloud"] == 2 * n
    rows = r._copies_of(two_s.clouds["cloud"], W, H, np.zeros((0, 3)),
                        eye_matrix(W, H, EYE_FOV, EYE_DISTANCE), 1.0)
    assert len(rows) == 2 and rows[0][0] != rows[1][0]
    lit = _lit(two)
    for cx, cy, k, _ in rows:          # each copy's points about its own centre
        q = (reg.clouds["cloud:scan"].points.astype(np.float64) * k
             + np.array([cx, cy, 0.0]))
        xy, _ = _project(q, 1.0)
        near = np.min(np.linalg.norm(xy[:, None] - 0.5 - lit[None], axis=2), axis=1)
        assert np.percentile(near, 95) < 2.5
    assert not (one == two).all()
    none = _draw(ctx, r, vs, _view({"instances": 0}), reg)
    assert r.stats["clouds"]["cloud"] == 0 and not none[..., :3].any()
