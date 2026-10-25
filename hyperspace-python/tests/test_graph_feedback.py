"""Plan 34 L: feedback's words — `delay`, `resize`, `echo.<k>`, `dream` —
and the loop check that counts the default graph's hidden edges
(`FRAME_EDGES`), so a loop through the faces, the backdrop or the frame
is refused when the section is read, not left to land dormant at build
(data only: `read_graph`, `wire_loops`, `sink_loops`, `reaches`). The
delay's node, the echoes' and the resize's are T2–T4's."""

from __future__ import annotations

import pytest

from hyperspace import graph as G
from hyperspace import graphmigrate as M

RUN = ("frame", "fx.image")


def section(*pairs, nodes=()):
    return {"nodes": list(nodes), "wires": [{"from": a, "to": b} for a, b in pairs]}


def test_the_new_kinds_read_and_round_trip():
    spec = G.read_graph(section(
        RUN, ("scene", "delay.image"), ("delay", "shape.faces"), ("media.a", "resize.image"),
        ("resize", "output.2.image"), ("echo.3", "output.3.image"), ("dream", "acid.2.aux"),
        nodes=[{"kind": "delay"}, {"kind": "delay", "instance": 2}, {"kind": "resize"},
               {"kind": "echo", "index": 3}, {"kind": "dream"},
               {"kind": "effect", "file": "acid", "instance": 2}]))
    assert spec.notes == ()
    assert G.read_graph(spec.to_json()) == spec
    assert spec.delays == (G.DelayAt(1), G.DelayAt(2))
    assert spec.resizes == (G.ResizeAt(1),)
    assert spec.echoes == (G.EchoAt(3),)
    assert spec.dream == G.DreamAt()
    assert G.DelayAt(2).to_json() == {"kind": "delay", "instance": 2}
    assert G.EchoAt(3).to_json() == {"kind": "echo", "index": 3}
    assert G.DreamAt().to_json() == {"kind": "dream"} and G.DreamAt().n == 1
    assert G.read_graph(section(RUN)).dream is None


def test_the_new_names_are_reserved_kinds():
    for name, kind in (("delay", "delay"), ("delay.2", "delay"), ("resize", "resize"),
                       ("resize.3", "resize"), ("echo.7", "echo"), ("dream", "dream")):
        assert G.wire_node_kind(name) == kind
    assert {"delay", "resize", "echo", "dream"} <= set(G.RESERVED)
    with pytest.raises(ValueError):
        G.EffectAt("resize", 1, after="scene")


@pytest.mark.parametrize(("pair", "name", "entry"), [
    (("scene", "delay.2.image"), "delay.2", '{"kind": "delay"}'),
    (("media.a", "resize.image"), "resize", '{"kind": "resize"}'),
    (("echo.3", "output.2.image"), "echo.3", '{"kind": "echo", "index": 3}'),
    (("dream", "output.2.image"), "dream", '{"kind": "dream"}'),
])
def test_a_wire_into_an_undeclared_node_is_refused(pair, name, entry):
    w = G.Wire(*pair)
    spec = G.read_graph(section(RUN, pair))
    assert spec.notes == (f"wire {w} — no {name} node in this graph (add one: {entry})",)
    assert w not in spec.wires


@pytest.mark.parametrize("index", [0, 33, "3"])
def test_an_echo_index_out_of_range_is_unreadable(index):
    with pytest.raises(G.GraphError) as err:
        G.read_graph(section(RUN, nodes=[{"kind": "echo", "index": index}]))
    assert str(err.value) == (f"echo node: index {index!r}, a whole number from 1 to "
                              f"{G.MAX_ECHOES}")
    with pytest.raises(G.GraphError) as err:
        G.read_graph(section(RUN, nodes=[{"kind": "echo"}]))
    assert str(err.value) == "echo node: names no index (echo.1 is the newest)"


def test_two_of_one_instance_are_unreadable():
    for entry, words in (({"kind": "delay"}, "two delay nodes of instance 1"),
                         ({"kind": "resize", "instance": 2}, "two resize nodes of instance 2"),
                         ({"kind": "echo", "index": 3}, "two echo nodes of instance 3"),
                         ({"kind": "dream"}, "two dream nodes of instance 1")):
        with pytest.raises(G.GraphError, match=words):
            G.read_graph(section(RUN, nodes=[entry, dict(entry)]))


SINK_LOOPS = [
    ([("scene", "shape.faces")], 0, "LOOP_FACES", "shape → scene → shape"),
    ([("history", "shape.faces")], 0, "LOOP_FACES", "shape → scene → history → shape"),
    ([("frame", "shape.faces")], 0, "LOOP_FACES",
     "shape → scene → history → frame → shape"),
    ([("frame", "acid.image"), ("acid", "fx.image"), ("acid", "shape.faces")], 2,
     "LOOP_FACES", "shape → scene → history → frame → acid → shape"),
    ([("pattern", "acid.2.image"), ("acid.2", "shape.faces"), ("scene", "acid.2.aux")], 2,
     "LOOP_FACES", "acid.2 → shape → scene → acid.2"),
    ([("scene", "pattern.media")], 0, "LOOP_FACES", "pattern → shape → scene → pattern"),
    ([("history", "backdrop.image")], 0, "LOOP_BACKDROP", "backdrop → history → backdrop"),
]


@pytest.mark.parametrize(("pairs", "refused", "words", "path"), SINK_LOOPS)
def test_each_sink_loop_is_refused_at_read(pairs, refused, words, path):
    """Review Focus 2: every loop the hidden edges close is refused when
    the section is read, the wire refused the one closing it, in words
    that say which hidden edge it runs through and point at a delay."""
    nodes = [{"kind": "effect", "file": "acid", "instance": 2}] if "acid.2" in str(pairs) else []
    spec = G.read_graph(section(*pairs, nodes=nodes))
    bad = G.Wire(*pairs[refused])
    assert spec.notes == (f"wire {bad} — {getattr(G, words).format(path=path)}",)
    assert bad not in spec.wires
    for i, pair in enumerate(pairs):
        if i != refused:
            assert G.Wire(*pair) in spec.wires


def test_the_later_wire_closing_a_sink_loop_is_the_one_refused():
    pairs = SINK_LOOPS[3][0]
    spec = G.read_graph(section(*pairs))
    assert G.run_of(spec) == ("acid",)
    assert G.Wire("frame", "acid.image") in spec.wires
    assert G.Wire("acid", "shape.faces") not in spec.wires


def test_loop_words_name_the_hidden_edge():
    assert G.loop_words("a → b → a", {("scene", "shape"), ("history", "backdrop")}) == (
        G.LOOP_FACES.format(path="a → b → a"))
    assert G.loop_words("a → b → a", {("history", "backdrop")}) == (
        G.LOOP_BACKDROP.format(path="a → b → a"))
    assert G.loop_words("history → frame → history", {("frame", "history")}) == (
        G.LOOP_FRAME.format(path="history → frame → history"))
    spec = G.read_graph(section(("frame", "acid.image"), ("acid", "history.image")))
    assert spec.notes == ("wire acid → history.image — " + G.LOOP_FRAME.format(
        path="history → frame → acid → history"),)


def test_a_loop_through_a_delay_is_legal():
    spec = G.read_graph(section(RUN, ("scene", "delay.image"), ("delay", "shape.faces"),
                                nodes=[{"kind": "delay"}]))
    assert spec.notes == ()
    pairs = [("delay", "zoomblur.2.image"), ("zoomblur.2", "composite.under"),
             ("scene", "composite.over"), ("composite", "delay.image"),
             ("composite", "output.1.image")]
    spec = G.read_graph(section(*pairs, nodes=[
        {"kind": "composite"}, {"kind": "effect", "file": "zoomblur", "instance": 2},
        {"kind": "delay"}]))
    assert spec.notes == ()
    assert G.wire_loops(list(spec.wires)) == {}
    assert G.sink_loops(list(spec.wires)) == {}


def test_a_delay_into_itself_is_still_refused():
    spec = G.read_graph(section(RUN, ("delay", "delay.image"), nodes=[{"kind": "delay"}]))
    assert spec.notes == ("wire delay → delay.image — delay into itself makes a loop",)


@pytest.mark.parametrize("dst", ["delay.image", "acid.aux", "output.2.image"])
def test_frame_feeds_the_run_only(dst):
    spec = G.read_graph(section(RUN, ("frame", dst), nodes=[{"kind": "delay"}]))
    assert spec.notes == (f"wire frame → {dst} — {G.FRAME_SOURCE_REFUSAL}",)
    ok = G.read_graph(section(("frame", "acid.image"), ("acid", "fx.image")))
    assert ok.notes == ()


def test_a_delay_reaches_only_when_read():
    spec = G.read_graph(section(RUN, ("scene", "delay.image"), nodes=[{"kind": "delay"}]))
    assert "delay" not in G.reaches(spec)
    assert G.Wire("scene", "delay.image") not in spec.wiring().wires
    spec = G.read_graph(section(RUN, ("scene", "delay.image"), ("delay", "output.2.image"),
                                nodes=[{"kind": "delay"}]))
    assert {"delay", "scene"} <= G.reaches(spec)
    assert {G.Wire("scene", "delay.image"), G.Wire("delay", "output.2.image")} <= set(
        spec.wiring().wires)


@pytest.mark.parametrize(("node", "pairs"), [
    ({"kind": "delay"}, [("scene", "delay.image"), ("delay", "output.2.image")]),
    ({"kind": "resize"}, [("media.a", "resize.image"), ("resize", "output.2.image")]),
    ({"kind": "echo", "index": 2}, [("echo.2", "output.2.image")]),
    ({"kind": "dream"}, [("dream", "output.2.image")]),
])
def test_the_new_words_load_and_save_as_six(tmp_path, node, pairs):
    """Plan 34's feedback words (a delay, a resize, an echo, the dream) on a
    wire and as a bare entry read with no note, and a preset holding them
    saves `/6` with the node in its frame (row 394)."""
    from test_plan31_wiring import make_app

    sec = section(RUN, *pairs, nodes=[node])
    spec = G.read_graph(sec)
    assert spec.notes == ()
    assert G.read_graph({"nodes": [node]}).notes == ()
    app = make_app(tmp_path)
    assert app.presets.load_doc({"schema": "hyperspace.preset/5", "name": "fb",
                                 "values": {}, "graph": sec}) == []
    doc = app.presets.document("fb")
    assert doc["schema"] == "hyperspace.preset/6"
    assert [n for n in doc["graph"]["nodes"] if n.get("kind") == node["kind"]]
