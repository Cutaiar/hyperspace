"""Plan 65: GRAPH draws an effect's `aux` port only when its file reads one
(`fx.EffectSpec.aux`: Blend and Displace on this build), or when a saved
wire goes into it — that wire still loads, is drawn and can be deleted. A
copy follows the effect it copies."""

from __future__ import annotations

from test_graph_edit import wired_rig
from test_graphview import views

from hyperspace import graph as G
from hyperspace import graphview
from hyperspace.outputs import Switches

SECTION = {"frame": "wired", "nodes": [{"kind": "effect", "file": "wave"},
                                       {"kind": "effect", "file": "displace", "slots": 2},
                                       {"kind": "effect", "file": "acid"}],
           "wires": [{"from": "shape", "to": "scene.geometry"},
                     {"from": "scene", "to": "wave.image"},
                     {"from": "wave", "to": "displace.image"},
                     {"from": "scene", "to": "displace.aux"},
                     {"from": "scene", "to": "acid.aux"},
                     {"from": "displace", "to": "output.all.image"}]}


def _ports(view, name):
    n = view.node(f"render:{name}")
    assert n is not None, name
    return {p.name for p in n.ports if p.direction == graphview.IN}


def test_the_aux_port_only_where_the_file_reads_it_or_a_wire_goes_in(tmp_path):
    rig, _, _ = wired_rig(tmp_path, SECTION)
    spec = rig.loaded_patch.graph.spec
    assert not spec.notes, spec.notes
    g = G.build_graph(views(Switches(), Switches()), spec.wiring())
    view = graphview.build(rig.router.table, rig.reg, rig.router, None, g, spec)
    assert "aux" in _ports(view, "displace")             # it reads one
    assert "aux" not in _ports(view, "wave")             # it doesn't
    assert "aux" in _ports(view, "acid")                 # it doesn't, but a saved wire goes in
    assert "aux 2" in _ports(view, "displace")           # its slot 2's (plan 89)
    c = next(c for c in view.cables if c.dst_port == "rin:acid/aux")
    assert c.src_port == "rout:scene"                    # drawn, so it can be deleted
    assert {"image"} <= _ports(view, "wave")


def test_with_no_effect_state_to_ask_every_port_is_drawn():
    assert graphview.aux_shown(object(), "wave")
