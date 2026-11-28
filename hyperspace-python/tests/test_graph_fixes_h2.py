"""Plan 90 (H2b): the graph fixes the look-back's retirement found, each on
its own — a stack's delay records whether or not its reader is drawn; a
composite never paints into the texture its `over` is made in; a section's
`keys` save on one line and go with their node."""

from __future__ import annotations

import json
from types import SimpleNamespace

from hyperspace import graph as G
from hyperspace import loadable
from hyperspace.outputs import Switches, View

STACKED = {"frame": "wired", "nodes": [{"kind": "delay"}, {"kind": "effect", "file": "trail"}],
           "wires": [{"from": "shape", "to": "scene.geometry"},
                     {"from": "scene", "to": "output.all.image"},
                     {"from": "scene", "to": "delay.image"},
                     {"from": "delay", "to": "trail.stack"},
                     {"from": "trail", "to": "output.2.image"}]}


def _graph(section):
    spec = G.read_graph(section, effects={"trail"})
    assert not spec.notes, spec.notes
    return G.build_graph([View(Switches(), (10, 10)), View(Switches(), (10, 10))],
                         spec.wiring(), effects=("trail",))


def test_a_delay_read_as_a_stack_is_marked_so_by_the_build():
    assert _graph(STACKED).nodes["delay"].read_as_stack is True
    plain = {**STACKED, "nodes": [{"kind": "delay"}],
             "wires": [*STACKED["wires"][:3], {"from": "delay", "to": "output.2.image"}]}
    assert _graph(plain).nodes["delay"].read_as_stack is False


def test_its_write_asks_for_the_stack_though_its_reader_is_not_drawn():
    """The write is what records: it asks the renderer for the stack each
    frame (`Renderer.delay_stack` makes it on the first ask), whether or not
    the Trail reading it was drawn this frame."""
    g = _graph(STACKED)
    asked: list[str] = []
    r = SimpleNamespace(delay_pair=lambda name: None,
                        delay_stack=lambda name: asked.append(name))
    frame = SimpleNamespace(r=r, graph=g)
    write = g.nodes["delay(write)"]
    write.run(frame)                          # (no pair: the write stops after the ask)
    assert asked == ["delay"]


def test_a_wired_frame_saves_its_keys_on_one_line():
    doc = {"schema": loadable.SAVE_SCHEMA, "name": "k",
           "graph": {"frame": "wired", "nodes": [{"kind": "effect", "file": "fade"}],
                     "wires": [{"from": "scene", "to": "fade.image"}], "keys": ["fade"]}}
    text = loadable.dumps(doc)
    assert '\n "keys": ["fade"]}' in text and json.loads(text) == doc


def test_a_deleted_node_leaves_the_keys(tmp_path):
    from test_graph_edit import wired_rig
    section = {"frame": "wired", "nodes": [{"kind": "effect", "file": "fade"}],
               "wires": [{"from": "shape", "to": "scene.geometry"},
                         {"from": "scene", "to": "fade.image"},
                         {"from": "fade", "to": "output.all.image"}],
               "keys": ["fade"]}
    rig, e, _ = wired_rig(tmp_path, section)
    assert rig.loaded_patch.graph.spec.to_json().get("keys") == ["fade"]
    assert e.drop_node("fade") is None
    assert "keys" not in rig.loaded_patch.graph.spec.to_json()


# ---------------------------------------------------------------- the cover (Devin on #521)

def _wired(ctx, wires, nodes=(), media=None):
    """A fresh renderer on a wired frame (`wires` as pairs) — and its views."""
    from test_graph_faces import _fbo

    from hyperspace.render import Renderer
    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    spec = G.read_graph({"frame": "wired", "nodes": list(nodes),
                         "wires": [{"from": a, "to": b} for a, b in wires]},
                        effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r, [View(Switches(), (96, 64), target=_fbo(ctx, 96, 64))]


def _draw(ctx, r, s, vs, k=0):
    from test_graph_faces import _px
    r.draw_outputs(s, 96, 64, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return _px(vs[0].target)


def test_a_cover_behind_an_unpicked_switch_input_is_not_drawn(ctx):
    """A cut by the cover on a switch's input 1, a still on input 2, input 2
    picked on a fresh renderer: the scene behind input 1 is not run, so the
    cover is not drawn (at the scene's 0 × 0) — input 2 shows."""
    from test_graph_switch import BLUE, Still, _centre, _empty, _media, _rgba
    r, vs = _wired(ctx, [("shape", "scene.geometry"), ("pattern", "shape.faces"),
                         ("scene", "cut.image"), ("scene.cover", "cut.mask"),
                         ("cut", "switch.in1"), ("channel.b", "switch.in2"),
                         ("switch", "output.1.image")],
                   [{"kind": "switch"}, {"kind": "cut"}],
                   _media(b=Still(_rgba(16, 9, BLUE))))
    got = _centre(_draw(ctx, r, _empty({"switch": 2}), vs))
    assert got[2] > 200 and got[0] < 30, got


def test_every_frame_size_reads_the_one_cover():
    """`Cover.image` is the root frame's cover: a frame at another size, made
    before the cover was drawn (a resize's, the faces'), reads it too."""
    g = _graph({**STACKED, "nodes": [{"kind": "cut"}],
                "wires": [STACKED["wires"][0], {"from": "scene", "to": "cut.image"},
                          {"from": "scene.cover", "to": "cut.mask"},
                          {"from": "cut", "to": "output.all.image"}]})
    cover = g.nodes[G.COVER]
    root = SimpleNamespace(cover="the mask")
    sized = SimpleNamespace(cover=None, root=root)
    root.root = root
    assert cover.image(sized) == "the mask"


def test_a_scene_with_no_shape_leaves_no_faces_for_the_cover(ctx):
    """The face state the last scene pass left is cleared when the scene
    draws no shape: the cover of a scene whose shape was unwired is empty."""
    import numpy as np
    from test_graph_switch import _empty
    r, vs = _wired(ctx, [("shape", "scene.geometry"), ("pattern", "shape.faces"),
                         ("scene", "output.1.image")])
    s = _empty()
    s.faces = True
    _draw(ctx, r, s, vs)
    assert r._face_verts > 0 or r._cover_cells is not None
    bare = G.read_graph({"frame": "wired", "wires": [{"from": "scene", "to": "output.1.image"}]},
                        effects=set(r.fx.state.specs))
    r.wiring = bare.wiring()
    _draw(ctx, r, s, vs, 1)
    tex = r._draw_cover(*vs[0].size)
    assert not np.frombuffer(tex.read(), dtype=np.uint8).any()
