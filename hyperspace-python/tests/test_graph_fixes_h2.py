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
    try:
        write.run(frame)                    # (the pair is a stand-in: it stops after)
    except Exception:
        pass
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
