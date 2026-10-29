"""Plan 34 L: feedback's words — `delay`, `resize`, `echo.<k>`, `dream` —
and the loop check, so a loop through the faces, the backdrop or the frame
is refused, not left to land dormant at build (data only: `read_graph`,
`wire_loops`, `reaches`). Plan 36 T2: over drawn wires only — the old
hidden edges (`FRAME_EDGES`) are gone, and an old section's loop through
them is the migration's to leave out. The delay's node, the echoes' and
the resize's are T2–T4's."""

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


# plan 36 T2: plan 34's hidden edges (`FRAME_EDGES`) are gone — an old
# section is read as it stands, and a wire of it that closed a loop through
# them closes one through the frame its migration draws: the migration
# leaves it out, in the wired frame's words (`graphmigrate.wired_section`),
# the frame standing — (the old wires, the one left out, as migrated, its
# words, the loop's path in the new ids)
SINK_LOOPS = [
    ([("scene", "shape.faces")], ("scene", "shape.faces"), "LOOP_FACES",
     "shape → scene → shape"),
    ([("history", "shape.faces")], ("lookback", "shape.faces"), "LOOP_FACES",
     "shape → scene → lookback → shape"),
    ([("frame", "acid.image"), ("acid", "fx.image"), ("acid", "shape.faces")],
     ("acid", "shape.faces"), "LOOP_FACES", "shape → scene → lookback → acid → shape"),
    ([("pattern", "acid.2.image"), ("acid.2", "shape.faces"), ("scene", "acid.2.aux")],
     ("scene", "acid.2.aux"), "LOOP_FACES", "acid.2 → shape → scene → acid.2"),
    ([("scene", "pattern.media")], ("scene", "pattern.media"), "LOOP_FACES",
     "pattern → shape → scene → pattern"),
    ([("history", "backdrop.image")], ("lookback", "backdrop.image"), "LOOP_BACKDROP",
     "backdrop → lookback → backdrop"),
    ([("frame", "acid.image"), ("acid", "history.image")], ("acid", "lookback.image"),
     "LOOP_PLAIN", "lookback → acid → lookback"),
]


@pytest.mark.parametrize(("pairs", "refused", "words", "path"), SINK_LOOPS)
def test_each_old_hidden_edge_loop_is_left_out_by_the_migration(pairs, refused, words, path):
    """Review Focus 2, plan 36 T2: a loop the old hidden edges closed is no
    longer the read's (nothing hidden is read) — the migration leaves the
    wire closing it out, in words that say which drawn wire it runs
    through and point at a delay; the rest stands, and the wired frame
    reads with no note."""
    nodes = [{"kind": "effect", "file": "acid", "instance": 2}] if "acid.2" in str(pairs) else []
    old = section(*pairs, nodes=nodes)
    assert not any("loop" in n for n in G.read_graph(old).notes)
    doc, notes = M.seven({"values": {}, "graph": old}, {})
    bad = G.Wire(*refused)
    assert notes == [f"wire {bad} — {getattr(G, words).format(path=path)}"]
    spec = G.read_graph(doc["graph"])
    assert spec.notes == () and bad not in spec.wires
    assert G.Wire("shape", "scene.geometry") in spec.wires          # the frame stands


def test_the_later_wire_closing_a_sink_loop_is_the_one_refused():
    pairs = SINK_LOOPS[2][0]
    doc, _ = M.seven({"values": {}, "graph": section(*pairs)}, {})
    spec = G.read_graph(doc["graph"])
    # (plan 36 T4: the look-back off in the old values — its picture, the scene)
    assert G.Wire("scene", "acid.image") in spec.wires
    assert G.Wire("acid", "output.all.image") in spec.wires
    assert G.Wire("acid", "shape.faces") not in spec.wires


def test_loop_words_name_the_drawn_wire():
    assert G.loop_words("a → b → a", {("scene", "shape"), ("lookback", "backdrop")}) == (
        G.LOOP_FACES.format(path="a → b → a"))
    assert G.loop_words("a → b → a", {("lookback", "backdrop")}) == (
        G.LOOP_BACKDROP.format(path="a → b → a"))
    assert G.loop_words("lookback → acid → lookback", {("acid", "lookback")}) == (
        G.LOOP_PLAIN.format(path="lookback → acid → lookback"))
    for name in ("FRAME_EDGES", "HIDDEN_EDGES", "IMPLICIT_EDGES", "LOOP_FRAME", "sink_loops"):
        assert not hasattr(G, name), name


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
    assert doc["schema"] == "hyperspace.preset/7"
    # (plan 36 T4: an echo is its look-back's pin now — the look-back's node)
    kind = "lookback" if node["kind"] == "echo" else node["kind"]
    wires = doc["graph"]["wires"]
    assert ([n for n in doc["graph"]["nodes"] if n.get("kind") == kind]
            or any(w["from"] == kind or w["to"].startswith(f"{kind}.") for w in wires))
