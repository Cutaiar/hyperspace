"""Plan 33 G: the free graph's vocabulary (data only, no render).

New wire ends (`frame`, `fx.image`, `pattern`, `shape.faces`,
`backdrop.image`, `switch`), a wire from a channel into an effect as a
branch instead of a refusal, and `reaches` / `run_of` read off the wires.
"""

from __future__ import annotations

import pytest

from hyperspace import graph as G

REFUSAL = ("fx.image takes the run from frame; to replace an output's picture wire it "
           "into output.N.image")


def section(*pairs, nodes=()):
    return {"nodes": list(nodes), "wires": [{"from": a, "to": b} for a, b in pairs]}


def test_a_channel_into_an_effect_is_a_branch_not_a_refusal():
    spec = G.read_graph(section(("media.a", "acid.2.image")))
    assert not spec.notes
    assert G.Wire("media.a", "acid.2.image") in spec.wires
    assert "acid.2" not in G.reaches(spec)
    assert spec.wiring().placed == ()            # not shortened to `after media.a`


def test_a_branch_to_the_faces_reaches():
    spec = G.read_graph(section(("media.a", "acid.2.image"), ("acid.2", "tripcolour.2.image"),
                                ("tripcolour.2", "shape.faces")))
    assert not spec.notes
    assert G.reaches(spec) >= {"media.a", "acid.2", "tripcolour.2"}


def test_the_run_is_read_from_frame_to_fx():
    spec = G.read_graph(section(("frame", "acid.image"), ("acid", "wobble.image"),
                                ("wobble", "fx.image")))
    assert not spec.notes
    assert G.run_of(spec) == ("acid", "wobble")
    assert G.reaches(spec) >= {"frame", "acid", "wobble"}


def test_the_faces_run_and_a_switch_ends_a_run():
    spec = G.read_graph(section(("pattern", "acid.image"), ("acid", "shape.faces")))
    assert G.run_of(spec, "pattern", "shape.faces") == ("acid",)
    assert G.run_of(spec) == ()
    sw = G.read_graph(section(("frame", "switch.in1"), ("switch", "acid.image"),
                              ("acid", "fx.image"), nodes=[{"kind": "switch"}]))
    assert G.run_of(sw) == ()


def test_fx_image_refuses_a_branch_not_from_frame():
    spec = G.read_graph(section(("media.a", "acid.2.image"), ("acid.2", "fx.image")))
    assert any(n.endswith(REFUSAL) for n in spec.notes), spec.notes
    ctx = G._WireCtx(wires=(G.Wire("media.a", "acid.2.image"),))
    assert G.wire_error(G.Wire("acid.2", "fx.image"), ctx) == REFUSAL
    ok = G._WireCtx(wires=(G.Wire("frame", "acid.2.image"),))
    assert G.wire_error(G.Wire("acid.2", "fx.image"), ok) is None
    assert G.wire_error(G.Wire("frame", "fx.image"), ok) is None


def test_a_loop_through_aux_is_refused():
    spec = G.read_graph(section(("acid.2", "tripcolour.2.image"),
                                ("tripcolour.2", "acid.2.aux")))
    assert any("makes a loop" in n and "acid.2" in n for n in spec.notes), spec.notes
    loops = G.wire_loops([G.Wire("acid.2", "tripcolour.2.image"),
                          G.Wire("tripcolour.2", "acid.2.aux")])
    assert len(loops) == 2


def test_reserved_names_are_no_effect():
    for name in ("frame", "fx", "pattern", "shape", "backdrop", "switch", "switch.2"):
        assert G.wire_node_kind(name) == name.partition(".")[0]
    with pytest.raises(ValueError):
        G.EffectAt("frame", 1, after="scene")
    assert G.wire_node_kind("acid") == "effect"
    assert G.wire_node_kind("frames") == "effect"


def test_a_switch_takes_eight_pictures():
    nodes = [{"kind": "switch"}]
    spec = G.read_graph(section(("media.a", "switch.in1"), ("media.h", "switch.in8"),
                                ("switch", "pattern.media"), nodes=nodes))
    assert not spec.notes
    assert G.reaches(spec) >= {"media.a", "media.h", "switch"}
    ctx = G._WireCtx(switches=frozenset({"switch"}))
    why = G.wire_error(G.Wire("media.a", "switch.in9"), ctx)
    assert why == "switch has no port 'in9' (it takes in1, …, in8)"
    spec = G.read_graph(section(("media.a", "switch.in9"), nodes=nodes))
    assert any("switch has no port 'in9'" in n for n in spec.notes)


def test_a_switch_is_a_node_kind_that_may_stand_alone():
    spec = G.read_graph({"nodes": [{"kind": "switch"}, {"kind": "switch", "instance": 2}]})
    assert [s.name for s in spec.switches] == ["switch", "switch.2"]
    assert spec.to_json() == {"nodes": [{"kind": "switch"}, {"kind": "switch", "instance": 2}]}
    assert G.reaches(spec) == frozenset()
    with pytest.raises(G.GraphError):
        G.read_graph({"nodes": [{"kind": "switch"}, {"kind": "switch"}]})
    assert G.SINKS == ("output", "fx", "shape", "pattern", "backdrop", "history")
