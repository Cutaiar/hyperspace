"""Plan 26 A2 — one camera: the shape through a shared 4×4 with depth,
`eye.*`, camera.zoom / camera.pan as the shape's world transform, and the
Leap calibration into the shape's units.

The parity bar: with the default eye, zoom 1 and pan 0, every vertex of
every shape at the three golden view configurations (tests/golden/geometry)
lands within half a logical pixel of where `geometry.project_h` — the
renderer's old path, and `project`'s, the parity oracle — puts it.
"""

import json
import math
import shutil
from pathlib import Path

import moderngl
import numpy as np
import pytest
from test_presets import boot

from hyperspace import geometry as G
from hyperspace import ghost, preset
from hyperspace.hands import core as hc
from hyperspace.params import EYE_DISTANCE_RANGE, EYE_FOV_RANGE, PAN_RANGE, part_of
from hyperspace.view import ViewState

GOLDEN = Path(__file__).parent / "golden" / "geometry"
FIXTURES = Path(__file__).parent / "fixtures" / "camera"
SIZES = ((1200, 800), (960, 600), (600, 960), (1920, 1080), (1000, 1000))


def golden_views() -> list[dict]:
    """The three view configurations the plan-00 traces were taken at, and
    their viewport (each trace holds the same three)."""
    seen: dict[str, dict] = {}
    for path in sorted(GOLDEN.glob("*.json")):
        d = json.loads(path.read_text())
        for v in d["views"]:
            key = json.dumps([v["ang"], v["yaw"], v["pitch"]])
            seen.setdefault(key, {"ang": v["ang"], "yaw": v["yaw"], "pitch": v["pitch"],
                                  "size": (d["viewport"]["width"], d["viewport"]["height"])})
    return list(seen.values())


def worst_vertex_error(dtype) -> float:
    worst = 0.0
    for v in golden_views():
        for i in range(len(G.SHAPES)):
            V = G.geom(i)["V"]
            ang = G.view_angles(i, v["ang"])
            for w, h in (v["size"], *SIZES):
                px, py, _, _ = G.project_h(V, ang, v["yaw"], v["pitch"], w=w, h=h)
                ex, ey = G.eye_project(V, ang, v["yaw"], v["pitch"], w=w, h=h, dtype=dtype)
                worst = max(worst, float(np.abs(ex - px).max()), float(np.abs(ey - py).max()))
    return worst


# ------------------------------------------------------------- the parity bar

def test_there_are_three_golden_views():
    views = golden_views()
    assert len(views) == 3 and all(v["size"] == (1200, 800) for v in views)


def test_the_default_eye_lands_every_vertex_within_half_a_pixel_of_project_h():
    """Every shape (all 26) at the three golden views, at the traces' 1200×800
    and five other sizes (portrait and square included): the matrix path
    in float64 is project_h to a millionth of a pixel, and in float32 — the
    arithmetic the vertex shader does — well inside half a logical pixel
    (measured: 2.3e-13 px and 1.1e-4 px)."""
    assert worst_vertex_error(np.float64) < 1e-6
    assert worst_vertex_error(np.float32) < 0.5 * 1e-2      # 1/100 of the bar


def test_project_is_still_the_oracle():
    """`project` stays project_h without the divisor: the parity oracle the
    traces check is untouched by the one camera."""
    v = golden_views()[0]
    V = G.geom(5)["V"]
    a = G.project(V, v["ang"], v["yaw"], v["pitch"])
    b = G.project_h(V, v["ang"], v["yaw"], v["pitch"])
    assert all(np.array_equal(x, y) for x, y in zip(a, b[:3]))


def test_the_default_eye_is_the_old_divide():
    """CAM3 − 0.9·z1 is an eye at CAM3 / 0.9; SCALE·min(w, h) px a unit at
    the origin is a field of view of ≈ 47.6° across the shorter side."""
    assert G.EYE_DISTANCE == pytest.approx(3.4 / 0.9)
    assert G.EYE_FOV == pytest.approx(47.61, abs=0.01)
    for w, h in SIZES:
        assert G.px_per_unit(w, h) == pytest.approx(0.30 * min(w, h), rel=1e-12)


def test_the_eye_sees_its_field_of_view_across_the_shorter_side():
    """A point one unit right of the origin lands the same number of px
    from the centre in landscape and in portrait of the same short side."""
    P = np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0]])
    for w, h in ((1200, 800), (800, 1200)):
        c = P @ G.eye_matrix(w, h).T
        nx, ny = c[:, 0] / c[:, 3], c[:, 1] / c[:, 3]
        assert nx[0] * w / 2 == pytest.approx(G.px_per_unit(w, h))
        assert ny[1] * h / 2 == pytest.approx(G.px_per_unit(w, h))


def test_zoom_scales_the_shape_about_the_world_origin_and_pan_moves_it():
    """camera.zoom / camera.pan are the shape's world transform: the
    origin goes where the pan puts it — pan.y positive is down the screen,
    as it always was — and a vertex at depth 0 lands zoom × as far out."""
    V = np.array([[0.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]])
    w, h = 960, 600
    unit = G.px_per_unit(w, h)
    px, py = G.eye_project(V, [0.0] * 6, 0.0, 0.0, w=w, h=h, zoom=1.0, pan=(1.0, 0.5))
    assert (px[0], py[0]) == pytest.approx((w / 2 + unit, h / 2 + 0.5 * unit))
    px, py = G.eye_project(V, [0.0] * 6, 0.0, 0.0, w=w, h=h, zoom=0.5)
    assert px[1] - w / 2 == pytest.approx(0.5 * unit) and py[1] == pytest.approx(h / 2)
    # the zoom is in the world, not on the picture: a deep vertex is seen
    # in perspective at its scaled depth (the old 2D zoom would have
    # landed it at exactly zoom × its old offset)
    D = np.array([[1.0, 0.0, 0.5, 0.0]])          # a vertex toward the eye
    old_x, _, _, _ = G.project_h(D, [0.0] * 6, 0.0, 0.0, w=w, h=h)
    new_x, _ = G.eye_project(D, [0.0] * 6, 0.0, 0.0, w=w, h=h, zoom=2.0)
    assert abs((new_x[0] - w / 2) - 2.0 * (old_x[0] - w / 2)) > 10.0


def test_the_eye_params_are_the_rooms_and_default_to_the_old_view(tmp_path):
    rig = boot(tmp_path)
    reg = rig.reg
    for pid, default, (lo, hi) in (("eye.fov", G.EYE_FOV, EYE_FOV_RANGE),
                                   ("eye.distance", G.EYE_DISTANCE, EYE_DISTANCE_RANGE)):
        p = reg[pid]
        assert p.group == "eye" and part_of(p) == "session" and p.persist, pid
        assert not p.modulatable, pid
        assert p.value == pytest.approx(default) and (p.lo, p.hi) == (lo, hi), pid
        assert pid not in reg.snapshot(part="performance")
    assert rig.view.eye_fov == pytest.approx(G.EYE_FOV)
    pan = reg["camera.pan.x"]
    assert (pan.lo, pan.hi) == (-PAN_RANGE, PAN_RANGE) and pan.text() == "+0.00"


def test_the_pan_range_keeps_a_routed_pan_as_far_as_it_was():
    """hands-orbit's push of 0.1 on a hand across the box (0 → 1) moves the
    pan by 0.1 of its range: ±400 px before, ±1.2 units now — ≈ ±390 px on
    the 1080p screen the presets are converted at, within 5 %."""
    old = 0.1 * 8000.0 / 2.0
    new = 0.1 * 2.0 * PAN_RANGE / 2.0 * G.PAN_REF_PX
    assert new == pytest.approx(old, rel=0.05)


# --------------------------------------------------------------- the renderer

@pytest.fixture(scope="module")
def ctx():
    c = moderngl.create_context(standalone=True)
    yield c
    c.release()


def _view(**kw) -> ViewState:
    v = golden_views()[0]
    s = ViewState(shape=0, ang=list(v["ang"]), yaw=v["yaw"], pitch=v["pitch"],
                  faces=False, lines=False, points=True)
    for k, val in kw.items():
        setattr(s, k, val)
    return s


def _draw(ctx, s, w=600, h=400, depth=False, t=0.0):
    """One `draw_scene` into a plain framebuffer, with or without a depth
    texture: (RGBA as ints, top row first; the depth, top row first, or None)."""
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    tex = ctx.texture((w, h), 4)
    dep = ctx.depth_texture((w, h)) if depth else None
    fbo = ctx.framebuffer(color_attachments=[tex], depth_attachment=dep)
    fbo.use()
    ctx.viewport = (0, 0, w, h)
    try:
        r.draw_scene(s, w, h, t_now=t)
        img = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(h, w, 4)[::-1]
        z = None
        if dep is not None:
            z = np.frombuffer(dep.read(), dtype=np.float32).reshape(h, w)[::-1]
        assert ctx.error == "GL_NO_ERROR"
        return img.astype(int), (None if z is None else z.copy())
    finally:
        for res in (fbo, tex, dep):
            if res is not None:
                res.release()


def test_each_point_is_drawn_where_project_h_puts_it(ctx):
    """The 5-cell's five points alone: the pixel under each vertex's
    project_h position is lit red — and, panned one unit right, the pixel
    one unit's px to the right is."""
    w, h = 600, 400
    s = _view()
    V = G.geom(0)["V"]
    px, py, _, _ = G.project_h(V, s.ang, s.yaw, s.pitch, w=w, h=h)
    img, _ = _draw(ctx, s, w, h)
    for x, y in zip(px, py):
        r, g, _, _ = img[int(y), int(x)]
        assert r > 40 and r > 2 * g, (x, y, img[int(y), int(x)])   # a far point is dim
    # panned a unit right and zoomed: where eye_project (the shader's sum on
    # the CPU) puts each one — the shape moved in the world, seen in perspective
    img, _ = _draw(ctx, _view(pan=[1.0, 0.0], zoom=1.3), w, h)
    ex, ey = G.eye_project(V, s.ang, s.yaw, s.pitch, w=w, h=h, zoom=1.3, pan=(1.0, 0.0))
    assert not np.allclose(ex - px, ex[0] - px[0])     # not a 2D shift
    for x, y in zip(ex, ey):
        assert img[int(y), int(x)][0] > 40, (x, y)


def _rows(ctx, monkeypatch, s, **draw_kw):
    """One draw of `s`, and what it uploaded: the edges' and the points'
    vertex rows (edges: column 8 the width at scale 1, 9 the alpha; points:
    5 the radius at scale 1), the copies' rows (centre, scale, alpha), and
    the stroke-scale uniform the line and point programs were drawn with
    (1 world space: × the copy's scale in the shader; 0 screen space)."""
    from hyperspace.render import Renderer

    seen = {}
    real = Renderer.draw_scene

    def spy(self, *a, **k):
        real(self, *a, **k)
        seen["lines"] = np.frombuffer(self._lbuf.read(), dtype="f4").reshape(-1, 13).copy()
        seen["points"] = np.frombuffer(self._pbuf.read(), dtype="f4").reshape(-1, 10).copy()
        seen["copies"] = np.frombuffer(self._ibuf.read(), dtype="f4").reshape(-1, 4).copy()
        seen["wscale"] = (self._lines["u_wscale"].value, self._points["u_wscale"].value)
        seen["model"] = np.frombuffer(self._scene_mats[1], dtype="f4").reshape(4, 4).T.copy()

    monkeypatch.setattr(Renderer, "draw_scene", spy)
    try:
        _draw(ctx, s, **draw_kw)
    finally:
        monkeypatch.setattr(Renderer, "draw_scene", real)
    return seen


def test_strokes_keep_their_weight_whatever_the_zoom(ctx, monkeypatch):
    """In screen space (`view.screen_strokes` on, plan 26 A2b) the line width
    and the point radius do not scale with camera.zoom (plan 26 A2): the
    shape grows in the world, its strokes stay as heavy. On a one-copy
    view the zoom is the world transform and the copy is at scale 1; on
    the instanced field's own path (Fit) the zoom is in the copy's scale
    and the shaders are told not to apply it. World space, the default,
    is tests/test_stroke_space.py."""
    for fit in (False, True):
        a = _rows(ctx, monkeypatch, _view(lines=True, zoom=1.0, screen_strokes=True,
                                          inst_fit=fit))
        b = _rows(ctx, monkeypatch, _view(lines=True, zoom=2.5, screen_strokes=True,
                                          inst_fit=fit))
        assert np.array_equal(a["lines"][:, 8], b["lines"][:, 8])     # the edges' widths
        assert np.array_equal(a["points"][:, 5], b["points"][:, 5])   # the points' radii
        assert a["wscale"] == b["wscale"] == (0.0, 0.0)
        if not fit:
            assert a["copies"][0, 2] == b["copies"][0, 2] == 1.0
            assert a["model"][0, 0] == 1.0 and b["model"][0, 0] == np.float32(2.5)


def test_the_shapes_depth_is_its_nearest_visible_surface(ctx):
    """With a depth attachment the colour is exactly the frame without one
    (the see-through shape is painter-sorted, never depth-tested against
    itself), and the depth holds the shape where its strokes are over the
    threshold; a faint shape writes none."""
    from hyperspace.render import DEPTH_ALPHA

    s = _view(shape=3, lines=True, faces=True, bright=1.6)
    plain, _ = _draw(ctx, s)
    col, z = _draw(ctx, s, depth=True)
    assert np.array_equal(plain, col)
    lit = z < 1.0
    assert lit.any() and (col[lit][:, :3].max(axis=1) > 0).all()
    assert 0.5 < z[lit].min() < 1.0
    faint = _view(shape=3, lines=True, faces=True, bright=0.05)
    _, z = _draw(ctx, faint, depth=True)
    assert (z == 1.0).all() and DEPTH_ALPHA > 0.05


def test_the_scene_target_carries_a_depth_attachment(ctx):
    from hyperspace.render import SceneTarget

    t = SceneTarget(ctx)
    t.ensure((64, 48), 0)
    assert t.depth is not None and t.fbo.depth_attachment is t.depth
    t.ensure((64, 48), 4)
    assert t.depth is None and t.draw_fbo.depth_attachment is not None
    assert t.fbo.depth_attachment is None            # the resolve copies colour
    t.release()
    assert t.tex is None and t.depth is None


def test_a_shape_through_the_eye_draws_without_error(ctx):
    """camera.zoom at its top (40×) puts the eye inside the shape and a field
    of copies around it: the strokes behind the eye are cut, nothing
    raises, and the frame is still drawn."""
    for kw in ({"zoom": 40.0}, {"zoom": 40.0, "instances": 9},
               {"zoom": 3.0, "pan": [PAN_RANGE, -PAN_RANGE]}):
        img, _ = _draw(ctx, _view(shape=3, lines=True, faces=True, **kw), depth=True)
        assert np.isfinite(img).all()


# ------------------------------------------------------- the pan's migration

def test_a_preset_2_pan_in_px_is_read_in_world_units(tmp_path):
    """The fixture is a preset/2 file from before (its pan 162, −81 px),
    loaded through a scratch library: the pan lands in world units through
    the default eye on the 1080p screen (324 px a unit), the route's depth
    is the file's (a fraction of the range), and the preset is clean."""
    rig = boot(tmp_path)
    lib = rig.lib
    (lib.home / "presets").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "pan-px.json", lib.home / "presets" / "pan-px.json")
    lib.presets.load("PAN PX")
    assert rig.reg["camera.pan.x"].value == pytest.approx(0.5)
    assert rig.reg["camera.pan.y"].value == pytest.approx(-0.25)
    assert rig.view.pan == pytest.approx([0.5, -0.25])
    (b,) = rig.router.table.routes()
    assert (b.target, b.value) == ("camera.pan.x", 0.1)
    assert not lib.is_dirty("presets")
    assert rig.presets.notes == []                     # silent: nothing to say


def test_a_saved_preset_says_its_pan_is_in_world_units_and_loads_as_saved(tmp_path):
    rig = boot(tmp_path)
    rig.reg["camera.pan.x"].set(2.5)
    rig.reg["camera.pan.y"].set(-0.75)
    path = rig.presets.save_as("WORLD PAN")
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.preset/6"     # (row 394); a key marks the units
    assert doc[preset.UNITS_KEY] == {"camera.pan": "world"}
    assert doc["values"]["camera.pan.x"] == 2.5
    rig.reg["camera.pan.x"].set(0.0)
    rig.lib.presets.load("WORLD PAN")
    assert rig.view.pan == pytest.approx([2.5, -0.75])
    assert not rig.lib.is_dirty("presets")


def test_pan_world_leaves_a_marked_or_panless_document_alone():
    marked = {"values": {"camera.pan.x": 3.0}, "units": {"camera.pan": "world"}}
    assert preset.pan_world(marked) == (marked, False)
    plain = {"values": {"view.bright": 1.0}, "macros": {}}
    assert preset.pan_world(plain) == (plain, False)
    sub = {"base": "camera.pan.x", "from": 0.25, "to": 0.75}
    old = {"values": {"camera.pan.x": 324.0, "camera.pan.y": 0.0},
           "macros": {"macro.1": {"label": "", "subs": [dict(sub)]}}}
    new, changed = preset.pan_world(old)
    assert changed and new["values"] == {"camera.pan.x": 1.0, "camera.pan.y": 0.0}
    # a subscriber's ends are fractions of the range (`Sub.at` lands a norm)
    assert new["macros"]["macro.1"]["subs"] == [sub]
    assert old["values"]["camera.pan.x"] == 324.0      # a copy: the file's dict is untouched


def test_every_factory_pan_lands_inside_the_new_range():
    """The factory files keep their px (decision 23: byte-identical); each
    converts to a pan well inside ±PAN_RANGE (party-mandala's 190 px is
    0.59 of a radius)."""
    for path in sorted((preset.FACTORY_DIR).glob("*.json")):
        doc, _ = preset.pan_world(json.loads(path.read_text()))
        for pid in preset.PAN_IDS:
            v = doc.get("values", {}).get(pid, 0.0)
            assert abs(v) < PAN_RANGE / 4, (path.name, pid, v)
    mandala, _ = preset.pan_world(json.loads((preset.FACTORY_DIR / "party-mandala.json")
                                             .read_text()))
    assert mandala["values"]["camera.pan.x"] == pytest.approx(190.0 / 324.0)


# ---------------------------------------------------------- the calibration

def test_units_round_trip_through_hands_json(tmp_path, capsys):
    path = tmp_path / "hands.json"
    hc.save_calibration(path, {}, None, hc.Units(mm=120.0, origin=(0.0, 210.0, -5.0), tilt=20))
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.hands/3"
    assert doc["units"] == {"mm": 120.0, "origin": [0.0, 210.0, -5.0], "tilt": 20}
    assert hc.load_units(path) == hc.Units(120.0, (0.0, 210.0, -5.0), 20.0)
    hc.save_calibration(path, {}, None)
    assert json.loads(path.read_text())["units"] == {"mm": None, "origin": None,
                                                     "tilt": hc.UNITS_TILT}
    assert hc.load_units(path) == hc.Units()
    assert capsys.readouterr().err == ""


def test_an_older_or_bad_units_entry_is_from_the_box(tmp_path, capsys):
    path = tmp_path / "hands.json"
    path.write_text(json.dumps({"schema": "hyperspace.hands/2", "axes": {}, "box": None}))
    assert hc.load_units(path) == hc.Units()
    path.write_text(json.dumps({"schema": CAL3, "axes": {},
                                "units": {"mm": -3, "origin": [1, 2], "tilt": "steep"}}))
    assert hc.load_units(path) == hc.Units()
    err = capsys.readouterr().err
    assert "units.mm" in err and "units.origin" in err and "units.tilt" in err


CAL3 = "hyperspace.hands/3"


def test_a_2_file_is_kept_beside_itself_before_the_first_save(tmp_path):
    """The schema bump keeps the old file: a /2 hands.json is copied to
    hands.json.bak-v2 by the first save of this build, then rewritten /3."""
    from hyperspace.hands import HandSettings, HandsIO

    path = tmp_path / "hands.json"
    old = json.dumps({"schema": "hyperspace.hands/2", "axes": {}, "box": None})
    path.write_text(old)
    io = HandsIO(HandSettings.from_config(), source=object(), out=object(), cal_path=path)
    io.reset_ranges()
    assert (tmp_path / "hands.json.bak-v2").read_text() == old
    assert json.loads(path.read_text())["schema"] == CAL3
    assert "kept as hands.json.bak-v2" in io.cal_note


def _ndc(vp, pts):
    q = np.concatenate([pts, np.ones((len(pts), 1))], axis=1) @ vp.T
    return q[:, :3] / q[:, 3:4]


BOX = ((-200.0, 200.0), (100.0, 350.0), (-120.0, 120.0))


def test_the_shared_camera_frames_the_padded_box_like_the_ghost_camera():
    """The hands draw through `shared_camera` (plan 26 A3): the shape's
    eye after the calibration. From the box it frames the padded box as
    `camera` frames it on a 16:9 picture (`ghost.CAL_ASPECT`, the party
    projector's; A3 tuned it from A2's square on the shorter side, which
    drew the hands at two thirds of their size on a landscape output):
    its centre at the picture's centre, every corner in a 16:9 frame, the
    box touching its edge. The calibration is the room's, not an
    output's: the box lands at the same place in the world whatever the
    output's shape (a portrait output sees it cut at the sides)."""
    m = ghost.basis("desktop")
    lo, hi = ghost.stage_box(BOX, m)
    corners = np.array([(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])])
    ref, _ = ghost.shared_camera(BOX, m, ghost.CAL_ASPECT)
    c = _ndc(ref, corners)
    assert (np.abs(c[:, :2]) <= 1.0 + 1e-9).all() and (np.abs(c[:, 2]) < 1).all()
    assert np.abs(c[:, :2]).max() == pytest.approx(1.0, abs=1e-9)
    cal = ghost.calibration(BOX, m)
    for aspect in (16 / 9, 1.0, 9 / 16):
        vp, eye = ghost.shared_camera(BOX, m, aspect)
        assert np.allclose(ghost.calibration(BOX, m), cal)
        # the same world: on any landscape picture the box's height is the same
        if aspect >= 1.0:
            assert _ndc(vp, corners)[:, 1] == pytest.approx(c[:, 1], abs=1e-9)
        assert _ndc(vp, ((lo + hi) / 2)[None])[0, :2] == pytest.approx([0.0, 0.0], abs=1e-12)
        # the eye is above and behind the hands, as the ghost camera stands
        centre = (lo + hi) / 2
        back = (eye - centre) / np.linalg.norm(eye - centre)
        e = math.radians(ghost.ELEVATION)
        assert back == pytest.approx([0.0, math.sin(e), math.cos(e)], abs=1e-9)
        # up stays up, right stays right
        assert _ndc(vp, (centre + [0, 50, 0])[None])[0, 1] > 0
        assert _ndc(vp, (centre + [50, 0, 0])[None])[0, 0] > 0


def test_a_calibration_in_mm_puts_the_hands_at_that_scale():
    """`mm` millimetres make one shape unit: a point that far right of the
    origin (with no tilt) lands where the shape's unit point does."""
    m = ghost.basis("desktop")
    u = hc.Units(mm=100.0, origin=(0.0, 200.0, 0.0), tilt=0.0)
    cal = ghost.calibration(BOX, m, u)
    p = cal @ np.array([100.0, 200.0, 0.0, 1.0])
    assert p[:3] == pytest.approx([1.0, 0.0, 0.0])
    vp, _ = ghost.shared_camera(BOX, m, 1.5, u)
    a = _ndc(vp, np.array([[100.0, 200.0, 0.0]]))[0]
    b = _ndc(G.eye_matrix(1.5, 1.0), np.array([[1.0, 0.0, 0.0]]))[0]
    assert a == pytest.approx(b)


def test_ghost_mirror_flips_the_hands_in_the_shared_camera_too():
    p = np.array([[150.0, 220.0, 0.0]])
    plain, _ = ghost.shared_camera(BOX, ghost.basis("desktop"), 1.5)
    mirror, _ = ghost.shared_camera(BOX, ghost.basis("desktop", True), 1.5)
    a = _ndc(plain, p @ ghost.basis("desktop").T)[0]
    b = _ndc(mirror, p @ ghost.basis("desktop", True).T)[0]
    assert a[0] == pytest.approx(-b[0]) and a[1] == pytest.approx(b[1])


# ------------------------------------------- camera module presets (review fix 1)

def _old_module(lib, name="off-right"):
    (lib.home / "camera").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "old-camera-module.json", lib.home / "camera" / f"{name}.json")


def test_an_old_camera_module_loads_at_its_converted_pan(tmp_path):
    """A camera module preset saved before A2 (the CAMERA page's strip;
    fixture `old-camera-module.json`, pan 190, −81 px, no marker) lands at
    the converted pan through a scratch library — not at 190 radii clamped
    to 12 — and is clean."""
    rig = boot(tmp_path)
    _old_module(rig.lib)
    rig.lib.load("camera", "Off Right")
    assert rig.view.pan == pytest.approx([190.0 / 324.0, -0.25])
    assert rig.view.zoom == pytest.approx(0.8)
    assert not rig.lib.is_dirty("camera")


def test_an_old_camera_default_fills_a_preset_at_its_converted_pan(tmp_path):
    """The same file as the group's default (`camera/default.json`): what
    `defaults` and `resolved` fill a preset with — a preset that names no
    pan lands at the converted pan, not 190 radii."""
    rig = boot(tmp_path)
    _old_module(rig.lib, "default")
    rig.lib._defaults.clear()
    assert rig.lib.defaults("camera")["camera.pan.x"] == pytest.approx(190.0 / 324.0)
    doc = json.loads((FIXTURES / "pan-px.json").read_text())
    for pid in ("camera.pan.x", "camera.pan.y"):
        del doc["values"][pid]
    doc["name"] = "NO PAN"
    (rig.lib.home / "presets").mkdir(parents=True, exist_ok=True)
    (rig.lib.home / "presets" / "no-pan.json").write_text(json.dumps(doc))
    rig.lib.presets.load("NO PAN")
    assert rig.view.pan == pytest.approx([190.0 / 324.0, -0.25])


def test_a_camera_module_saved_now_says_its_pan_is_in_world_units(tmp_path):
    rig = boot(tmp_path)
    rig.reg["camera.pan.x"].set(3.0)
    path = rig.lib.save_as("camera", "World")
    doc = json.loads(path.read_text())
    assert doc[preset.UNITS_KEY] == {"camera.pan": "world"}
    rig.reg["camera.pan.x"].set(0.0)
    rig.lib.load("camera", "World")
    assert rig.view.pan[0] == pytest.approx(3.0) and not rig.lib.is_dirty("camera")
    # another group's module carries no marker
    assert preset.UNITS_KEY not in rig.lib.document("view", "V")


def test_a_presets_json_theme_is_still_converted():
    """`library.legacy_slot` (the old presets.json themes) writes no
    marker, so its px pan is converted when the slot's preset loads."""
    from hyperspace.library import legacy_slot

    slot = legacy_slot({"name": "OLD", "view": {"pan": [190.0, -81.0], "zoom": 0.7}})
    assert preset.UNITS_KEY not in slot and slot["values"]["camera.pan.x"] == 190.0
    doc, changed = preset.pan_world(slot)
    assert changed and doc["values"]["camera.pan.x"] == pytest.approx(190.0 / 324.0)


def test_a_hand_edited_units_that_is_no_object_is_no_marker(tmp_path):
    """`"units": "world"` (a string) neither raises nor counts as the
    marker: the preset loads and its pan is read in px."""
    out, _ = preset.pan_world({"units": "world", "values": {"camera.pan.x": 324.0}})
    assert out["values"]["camera.pan.x"] == pytest.approx(1.0)
    odd = {"units": None, "values": None}
    assert preset.pan_world(odd) == (odd, False)
    rig = boot(tmp_path)
    doc = json.loads((FIXTURES / "pan-px.json").read_text())
    doc.update(name="ODD UNITS", units="world")
    (rig.lib.home / "presets").mkdir(parents=True, exist_ok=True)
    (rig.lib.home / "presets" / "odd-units.json").write_text(json.dumps(doc))
    rig.lib.presets.load("ODD UNITS")
    assert rig.view.pan == pytest.approx([0.5, -0.25])
