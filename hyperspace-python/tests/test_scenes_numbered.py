"""Plan 92 phase 2: the one world and a second camera.

A scene is a camera onto the one world (the owner, 2026-11-28): `scene` is
declared by a wire, as the frame's own; `scene.<n>` by its entry
(`{"kind": "scene", "instance": n}`), its eye `eye.<n>.fov`, `.distance`,
`.yaw`, `.pitch` (`params.declare_scenes`, read as `Frame.eyes`), its pins
`scene.<n>.cover` and `scene.<n>.depth`, its target its own
(`render.ScenePass`). One shape seen by two scenes is one object: posed once
a frame (`Renderer.pose_shape`), drawn through each scene's eye
(`Renderer.draw_posed`). The picker adds the next scene seeing what the first
sees, its eye on the world's origin; a patch's scene spawns as the next one.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from test_graph_edit import wired_rig

from hyperspace import geometry, graphview, params, patches
from hyperspace import graph as G
from hyperspace.patches import Host, spawn
from hyperspace.view import EyeState, ViewState

SIZE = (160, 100)
TURN = math.radians(60)
TESSERACT = 3                     # (geometry.SHAPES[3], the tesseract)


def _two(*extra: dict, nodes=({"kind": "scene", "instance": 2},)) -> dict:
    """One tesseract, seen by two scenes, each into its own output."""
    return {"frame": "wired", "nodes": list(nodes), "wires": [
        {"from": "shape", "to": "scene.geometry"}, {"from": "shape", "to": "scene.2.geometry"},
        {"from": "scene", "to": "output.1.image"}, {"from": "scene.2", "to": "output.2.image"},
        *extra]}


def _one(*extra: dict) -> dict:
    return {"frame": "wired", "nodes": [], "wires": [
        {"from": "shape", "to": "scene.geometry"}, {"from": "scene", "to": "output.1.image"},
        *extra]}


def _fbo(ctx, w, h):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4)])


def _px(f) -> np.ndarray:
    w, h = f.size
    return np.frombuffer(f.read(components=4), np.uint8).reshape(h, w, 4)[::-1].astype(int)


def _draw(ctx, s, section, n=2):
    """(renderer, each output's pixels) of one frame of `section`."""
    from hyperspace.outputs import Switches, View
    from hyperspace.render import Renderer
    r = Renderer(ctx)
    r.wiring = G.read_graph(section).wiring()
    vs = [View(Switches(), SIZE, target=_fbo(ctx, *SIZE)) for _ in range(n)]
    r.draw_outputs(s, *SIZE, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    return r, [_px(v.target) for v in vs]


# ---------------------------------------------------------------- the section

def test_a_second_scene_is_declared_by_its_entry():
    spec = G.read_graph(_two())
    assert spec.scenes == (G.SceneAt(2),) and spec.notes == ()
    assert G.SceneAt(2).to_json() == {"kind": "scene", "instance": 2}
    assert G.SceneAt(1).to_json() == {"kind": "scene"} and G.scene_name(1) == "scene"
    assert G.wire_node_kind("scene.2", wired=True) == "scene"
    assert G.entry_declares("scene", 2) and not G.entry_declares("scene", 1)
    assert "scene" in G.NUMBERED_FRAME_KINDS


def test_a_wire_to_an_undeclared_scene_is_refused_in_words():
    spec = G.read_graph(_two(nodes=()))
    assert any('no scene.2 node in this graph (add one: {"kind": "scene", "instance": 2})'
               in n for n in spec.notes)


@pytest.mark.parametrize("n", [0, -1, True, "2"])
def test_a_scenes_instance_is_a_whole_number_from_1(n):
    with pytest.raises(G.GraphError):
        G.read_graph({"frame": "wired", "nodes": [{"kind": "scene", "instance": n}]})


def test_a_scenes_pins_are_its_own():
    assert G.scene_pin("scene.2.cover") == ("scene.2", "cover")
    assert G.scene_pin("scene.depth") == ("scene", "depth") and G.scene_pin("scene") is None
    assert G.pin_node("scene.3.depth") == "scene.3" and G.pin_node("scene.cover") == "scene"
    assert G.is_many_port("scene.2.geometry") and G.is_many_port("scene.geometry")
    assert not G.is_many_port("shape.faces")
    doc = _two({"from": "scene.2.depth", "to": "output.2.depth"})
    assert G.read_graph(doc).notes == ()                    # its depth where a depth goes
    doc["wires"].append({"from": "scene.2.cover", "to": "output.1.image"})
    said = ("wire scene.2.cover → output.1.image — scene.2.cover is scene.2's faces' "
            "coverage mask: it goes into a mask port (a cut's mask)")
    assert G.read_graph(doc).notes == (said,)


def test_two_scenes_build_side_by_side_each_with_its_own_cover():
    doc = _two({"from": "scene.2.cover", "to": "cut.mask"}, {"from": "scene", "to": "cut.image"},
               nodes=({"kind": "scene", "instance": 2}, {"kind": "cut"}))
    doc["wires"] = [w for w in doc["wires"] if w["to"] != "output.1.image"]
    doc["wires"].append({"from": "cut", "to": "output.1.image"})
    spec = G.read_graph(doc)
    assert spec.notes == ()
    from test_graph_masks import _views
    g = G.build_graph(_views(), spec.wiring())
    assert {"scene", "scene.2", "scene.2(cover)"} <= set(g.nodes)
    assert g.nodes["scene.2(cover)"].of() == "scene.2"
    assert g.nodes["scene.2"].geometries() == g.nodes["scene"].geometries()   # one shape


# ---------------------------------------------------------------- the eye

def test_the_eye_orbits_the_origin_and_is_the_old_one_at_rest():
    assert np.array_equal(geometry.eye_matrix(160, 100), geometry.eye_matrix(160, 100, yaw=0.0))
    pos = geometry.eye_position(4.0, math.pi / 2, 0.0)
    assert np.allclose(pos, [4.0, 0.0, 0.0])
    up = geometry.eye_position(4.0, 0.0, 0.5)
    assert up[1] > 0 and np.isclose(np.linalg.norm(up), 4.0)
    # the origin is the centre of the picture, whatever the orbit
    for yaw, pitch in ((0.7, 0.2), (-2.0, -1.0)):
        c = geometry.eye_matrix(160, 100, yaw=yaw, pitch=pitch) @ np.array([0, 0, 0, 1.0])
        assert np.allclose(c[:2] / c[3], 0.0)


def test_declare_scenes_comes_and_goes_and_keeps_the_first():
    from types import SimpleNamespace as NS

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    chain = Analyzer(Analyser())
    view = ViewState()
    reg = params.build_registry(view, Control(chain), NS(chain=chain))
    assert {"eye.fov", "eye.distance"} <= {p.id for p in reg} and reg.eye_state is view.eyes
    # (the first eye keeps exactly its ids: no orbit, so no saved show moves)
    assert "eye.yaw" not in reg and "eye.pitch" not in reg
    got = params.declare_scenes(reg, ["scene", "scene.2", "scene.3"])
    assert sorted(got) == sorted(f"eye.{n}.{k}" for n in (2, 3) for k in params.EYE_KEYS)
    assert reg["eye.2.yaw"].group == "eye" and "eye" in params.PATCH_GROUPS
    # a new scene's eye is the default eye, on the world's origin
    assert view.eyes["scene.2"] == EyeState()
    reg["eye.2.yaw"].set(TURN)
    assert view.eyes["scene.2"].eye_yaw == pytest.approx(TURN)
    assert params.declare_scenes(reg, ["scene", "scene.2"]) == [
        f"eye.3.{k}" for k in params.EYE_KEYS]
    assert "scene.3" not in view.eyes and "eye.fov" in reg
    assert params.is_eye_id("eye.2.pitch") and params.is_eye_id("eye.12.fov")
    assert not params.is_eye_id("eye.fov") and not params.is_eye_id("eye.1.fov")
    assert patches.EYE_KEYS == params.EYE_KEYS


def test_each_eye_is_on_its_scenes_node():
    rule = graphview.OWNERS["eye"]
    ctx = graphview._Ctx(names={"scene", "scene.2"})
    assert rule("eye.fov", ctx) == "scene" and rule("eye.2.yaw", ctx) == "scene.2"
    assert rule("eye.3.yaw", ctx) is None                  # (no such scene in the frame)
    assert params.eye_prefix("scene.2") == "eye.2" and params.eye_prefix("scene") == "eye"


# ---------------------------------------------------------------- the proof

def test_two_outputs_show_one_tesseract_from_two_angles_posed_once(ctx):
    """The proof (plan 92 §7.2): one tesseract seen by two scenes, each into
    its own output through its own eye — two angles on the one object — and
    its CPU half (turn, projection, sort) made once that frame."""
    s = ViewState(shape=TESSERACT, eyes={"scene.2": EyeState(eye_yaw=TURN)})
    r, (front, side) = _draw(ctx, s, _two())
    assert r.stats.get("posed") == 1                       # once a frame, not once a scene
    assert (front[..., :3] > 0).sum() > 100 and (side[..., :3] > 0).sum() > 100
    assert not np.array_equal(front, side)                 # two angles
    # each is what one scene draws through that eye: the first, at rest…
    _, (alone,) = _draw(ctx, ViewState(shape=TESSERACT), _one(), n=1)
    assert np.array_equal(front, alone)
    # …and the second, the tesseract seen from 60° round: the same as the
    # first scene's eye standing there (the orbit is the eye's alone)
    _, (turned,) = _draw(ctx, ViewState(shape=TESSERACT, eyes={"scene.2": EyeState(eye_yaw=TURN)}),
                         {"frame": "wired", "nodes": [{"kind": "scene", "instance": 2}],
                          "wires": [{"from": "shape", "to": "scene.2.geometry"},
                                    {"from": "scene.2", "to": "output.1.image"}]}, n=1)
    assert np.array_equal(side, turned)


def test_a_second_scene_at_the_default_eye_draws_as_the_first(ctx):
    _, (a, b) = _draw(ctx, ViewState(shape=TESSERACT, faces=True), _two())
    assert np.array_equal(a, b)


def test_each_scene_has_its_own_target(ctx):
    r, _ = _draw(ctx, ViewState(shape=TESSERACT), _two())
    one, two = r.scene_pass_of("scene"), r.scene_pass_of("scene.2")
    assert one is not two and one.target.tex is not None and two.target.tex is not None
    assert one.target.tex is not two.target.tex and r.scene is one.target
    # a graph without the second scene lets its targets go
    from hyperspace.outputs import Switches, View
    r.wiring = G.read_graph(_one()).wiring()
    r.draw_outputs(ViewState(shape=TESSERACT), *SIZE, 1.0,
                   [View(Switches(), SIZE, target=_fbo(ctx, *SIZE))], t_now=2.0)
    assert "scene.2" not in r._scene_passes()


# ---------------------------------------------------------------- GRAPH

def test_the_picker_adds_the_next_scene_seeing_what_the_first_sees(tmp_path):
    rig, e, _ = wired_rig(tmp_path, _one({"from": "hands", "to": "scene.geometry"}))
    assert "scene" not in graphview.picked(e) and "scene" not in graphview.ONCE
    assert e.add_node("scene") is None and e.added == "scene.2"
    got = rig.loaded_patch.graph.spec.wires
    # (its wires copied in the first's order: the draw order)
    first = [w.src for w in got if w.dst == "scene.geometry"]
    assert sorted(first) == ["hands", "shape"]
    assert [w.src for w in got if w.dst == "scene.2.geometry"] == first
    assert {f"eye.2.{k}" for k in params.EYE_KEYS} <= {p.id for p in rig.reg}
    assert rig.view.eyes["scene.2"] == EyeState()          # on the world's origin
    assert e.add_node("scene") is None and e.added == "scene.3"
    assert e.drop_node("render:scene.2") is None
    spec = rig.loaded_patch.graph.spec
    assert [x.name for x in spec.scenes] == ["scene.3"]
    assert "eye.2.fov" not in rig.reg and "eye.3.fov" in rig.reg


def test_a_scenes_eye_params_are_listed_on_its_node(tmp_path):
    rig, _e, _ = wired_rig(tmp_path, _two())
    two = graphview.param_ids(rig.reg, "render:scene.2")
    assert set(two) == {f"eye.2.{k}" for k in params.EYE_KEYS}
    one = graphview.param_ids(rig.reg, "render:scene")
    assert {"eye.fov", "eye.distance"} <= set(one) and not any(params.is_eye_id(p) for p in one)


# ---------------------------------------------------------------- patches

def test_a_patchs_scene_spawns_as_the_next_one_its_eye_renamed():
    doc = {"schema": patches.SCHEMA, "name": "camera", "nodes": [
        {"kind": "scene", "instance": 2}], "wires": [
        {"from": "shape", "to": "scene.2.geometry"}],
        "values": {"eye.2.yaw": 0.5}}
    landing = spawn(doc, Host(names=frozenset({"scene", "scene.2", "shape"})))
    assert landing.taken == () and landing.refusal is None
    assert landing.renames["scene.2"] == "scene.3"
    assert {"kind": "scene", "instance": 3} in [dict(n) for n in landing.nodes]
    assert landing.values == {"eye.3.yaw": 0.5}
    assert "scene" not in patches.ONE_PER_FRAME


def test_a_patchs_first_scene_lands_beside_the_hosts():
    doc = {"schema": patches.SCHEMA, "name": "view", "nodes": [{"kind": "scene"}]}
    assert patches.check(doc) == []
    landing = spawn(doc, Host(names=frozenset({"scene"})))
    assert landing.taken == () and landing.renames["scene"] == "scene.2"
    assert {"kind": "scene", "instance": 2} in [dict(n) for n in landing.nodes]
