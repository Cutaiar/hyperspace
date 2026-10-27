"""Plan 30 D1: placing an effect on any image edge from the preset.

Plan 36 T3 (W3): a placement is an old section's word only — the one-way
migration writes it as the wires it stood for (`graphmigrate.placed_wires`)
and the builder places nothing. These tests read old sections, migrate them
(`wired_wiring`, `wiredframe`: the retired switch states laid on first, as
the builder placed on each output's state) and check the pictures and the
nodes the wires build.

A preset's `graph` section may say where an effect node sits:
`{"kind": "effect", "file": "palette", "after": "hands"}` — on the hands'
layer, every consumer of it reading the effect — or `"into":
"output.2"` — on that output's picture alone. A placed effect is not in
the chain's run. A placement this build cannot honour (a name out of the
vocabulary, both keys, a loop) is a note and the default placement; one
on a node the built graph lacks this frame is dormant, said in words.

The pure half first (the JSON, the vocabulary, the graph's shape, the
words), then the preset loads over a scratch library, then the GL half:
the hands fold and the shape does not, one output folds, the history
captures the folded scene. The fixtures' pictures are
`tests/test_golden_frames.py`'s.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_graph_json import Stub
from test_presets import boot, put
from wiredframe import Shows, Thru, graph, wire_switches

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace import preset
from hyperspace.graphmigrate import wired_wiring
from hyperspace.library import FACTORY, PRESETS
from hyperspace.outputs import Switches, View

S = Switches
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "presets"
PLACED = ("palette-hands", "palette-glass", "acid-scene")
RUN = ("warp", "acid", "acid.2", "palette", "palette.2")
FILES = {"warp", "acid", "palette", "kaleido"}


def _run(placed=(), effects=RUN) -> tuple[str, ...]:
    """The run a preset's wires give these effects (plan 33 R: the
    migration's, every effect not placed, in the order given)."""
    names = {e.name for e in placed}
    return tuple(e for e in effects if e not in names)


def _wiring(*placed, effects=RUN) -> G.Wiring:
    return G.Wiring(placed=tuple(placed), run=_run(placed, effects))


def _graph(views, *placed, effects=RUN, look="trail"):
    """`views` (a window's `Switches`, or a `Shows` its output's wiring:
    plan 35 T4, `tests/wiredframe.py`) over the run with `placed` placed —
    plan 36 T4: the look-back drawn (`look`), as the old words with it on."""
    if all(isinstance(v, Shows) for v in views):
        return graph(views, _wiring(*placed, effects=effects), effects=effects, look=look)
    return G.build_graph(views, wired_wiring(_wiring(*placed, effects=effects), look),
                         effects=effects)


def _end(g: G.Graph, n: int = 1) -> G.Node:
    """Output `n`'s end, behind its folds."""
    end = g.nodes[f"output.{n}"].inputs["image"]
    while isinstance(end, G.Effect):
        end = end.inputs["image"]
    return end


def _run_names(g: G.Graph, end: G.Node) -> list[str]:
    return [e.effect for e in G._effects_of(end.inputs["image"])]


def _fixture(slug: str) -> dict:
    return json.loads((FIXTURES / f"{slug}.json").read_text())


# ---------------------------------------------------------------- the JSON


def test_both_keys_at_once_are_refused():
    """`after` and `into` on one node: a note, that effect at the default
    placement (instance 1 is the file itself, always in the chain; an
    extra instance stays in the chain at its order), the rest standing."""
    spec = G.read_graph({"nodes": [
        {"kind": "effect", "file": "palette", "after": "hands", "into": "output.2"},
        {"kind": "effect", "file": "acid", "instance": 2, "after": "scene",
         "into": "history"},
        {"kind": "hands", "into": "scene"}]})
    assert spec.notes == (
        "palette after 'hands' and into 'output.2' at once — one of the two",
        "acid.2 after 'scene' and into 'history' at once — one of the two")
    assert spec.effects == (G.EffectAt("acid", 2),) and spec.wiring().placed == ()
    assert spec.wiring().hands == "scene"
    with pytest.raises(ValueError, match="at once — one of the two"):
        G.EffectAt("palette", 1, after="hands", into="output.2")


def test_an_unknown_placement_is_a_note_and_the_default(tmp_path):
    """A name outside the vocabulary (`scene`, `hands`, `hands.<n>`,
    `history`, `output.<n>`, an effect this build has), a name that is not
    a string, `into` a node whose inputs are geometry, an effect sitting
    on itself or a loop of them: each a note in the section's words, that
    effect at the default placement. Through a preset load: the note on
    the strip ("; the default placement"), the rest of the graph landed,
    the section kept as the file had it."""
    teapot = ("palette after 'teapot' — this build places after scene, hands, hands.2 …, "
              "history, output.1 …, or an effect")
    cases = [
        ({"file": "palette", "after": "teapot"}, teapot),
        ({"file": "palette", "into": "teapot"},
         "palette into 'teapot' — this build places into history, output.1 …, or an effect"),
        ({"file": "palette", "after": 3}, "palette after 3 — a node's name in quotes"),
        ({"file": "palette", "after": None}, "palette after None — a node's name in quotes"),
        ({"file": "palette", "instance": 2, "into": None},
         "palette.2 into None — a node's name in quotes"),
        ({"file": "palette", "after": "output.0"}, "palette after 'output.0' — this build"),
        ({"file": "palette", "after": "hands.1"}, "palette after 'hands.1' — this build"),
        ({"file": "palette", "into": "scene"},
         ("palette into 'scene' — its inputs are geometry, not a picture: after 'scene' "
          "folds its picture")),
        ({"file": "palette", "into": "hands"}, "palette into 'hands' — its inputs are geometry"),
        ({"file": "palette", "after": "palette"},
         "palette after 'palette' — an effect cannot sit after itself"),
        ({"file": "palette", "instance": 2, "after": "acid.3"},
         "palette.2 after 'acid.3' — this build places after"),
    ]
    for entry, why in cases:
        spec = G.read_graph({"nodes": [{"kind": "effect", **entry}]}, effects=FILES)
        assert len(spec.notes) == 1 and spec.notes[0].startswith(why), (entry, spec.notes)
        assert spec.wiring().placed == ()
        n = entry.get("instance", 1)
        assert spec.effects == ((G.EffectAt("palette", n),) if n > 1 else ())
    # the vocabulary, all honoured
    for where in ("scene", "hands", "hands.2", "history", "output.1", "output.12", "acid",
                  "acid.2", "warp"):
        spec = G.read_graph({"nodes": [{"kind": "effect", "file": "acid", "instance": 2},
                                       {"kind": "effect", "file": "palette", "after": where}]},
                            effects=FILES)
        assert spec.notes == () and spec.wiring().placed[0].after == where, where
    # without the build's files any well-formed effect name is read
    assert G.read_graph({"nodes": [{"kind": "effect", "file": "palette",
                                    "after": "teapot"}]}).notes == ()
    # a loop of placed effects: each in it at the default placement
    spec = G.read_graph({"nodes": [
        {"kind": "effect", "file": "palette", "after": "acid.2"},
        {"kind": "effect", "file": "acid", "instance": 2, "into": "palette"},
        {"kind": "effect", "file": "warp", "after": "hands"}]}, effects=FILES)
    assert spec.notes == (
        "palette after 'acid.2' — that makes a loop (palette after acid.2 into palette)",
        "acid.2 into 'palette' — that makes a loop (acid.2 into palette after acid.2)")
    assert spec.wiring().placed == (G.EffectAt("warp", 1, after="hands"),)
    assert G.EffectAt("acid", 2) in spec.effects
    # the migration: the run is its wires (plan 33 R), the two placements
    # in a loop take no other place (plan 36 T3: no build-time placement)
    w = G.Wiring(placed=(G.EffectAt("palette", 1, after="acid.2"),
                         G.EffectAt("acid", 2, into="palette")), run=RUN)
    g = G.build_graph([View(S(), (10, 10))], wired_wiring(w), effects=RUN)
    assert wired_wiring(w).placed == () and g.notes == []
    assert _run_names(g, _end(g)) == list(RUN)
    # through a preset load: the migration's note and the refusal said, the
    # rest landed, the entry kept on no wire (the `/7` reads no placement)
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    section = {"nodes": [{"kind": "hands", "into": "scene"},
                         {"kind": "effect", "file": "palette", "after": "teapot"}]}
    put(rig.home, "Odd", values={"view.bright": 3.0}, graph=section)
    rig.lib.load(PRESETS, "Odd")
    assert rig.presets.notes == [f"{teapot}: not wired (plan 36)"]
    assert G.in_scene_hands(stub.wiring) == [1] and rig.reg["view.bright"].value == 3.0
    saved = rig.presets.document("Odd")[preset.GRAPH_KEY]
    assert saved == rig.presets.graph.free_doc()
    assert {"kind": "effect", "file": "palette"} in saved["nodes"]
    assert not any(k in e for e in saved["nodes"] for k in G.PLACE_KEYS)


def test_the_section_round_trips_with_its_placements(tmp_path):
    """`after` / `into` read and written back plainly in an old section
    (instance 1 named only by its file when placed); each fixture's section
    is its spec's JSON; loaded from a scratch library it lands with the
    migration's note alone and a clean dot, each placement the wires it
    stood for (plan 36 T3), and a save writes the section back one node per
    line, no placement in it."""
    section = {"nodes": [
        {"kind": "effect", "file": "acid", "instance": 2, "after": "scene"},
        {"kind": "effect", "file": "palette", "after": "hands"},
        {"kind": "effect", "file": "palette", "instance": 2, "into": "output.2"}]}
    spec = G.read_graph(section)
    assert spec.to_json() == section and G.read_graph(spec.to_json()) == spec
    assert spec.effect_counts() == {"acid": 2, "palette": 2}
    assert [(e.name, e.where) for e in spec.wiring().placed] == [
        ("acid.2", ("after", "scene")), ("palette", ("after", "hands")),
        ("palette.2", ("into", "output.2"))]
    # plan 33 R21: an unplaced instance 1 is the file kept on no wire (it was
    # refused while instance 1 was the stack's, always there)
    kept = G.read_graph({"nodes": [{"kind": "effect", "file": "palette"}]})
    assert kept.effects == (G.EffectAt("palette", 1),) and not kept.wiring().placed
    want = {"palette-hands": (G.EffectAt("palette", 1, after="hands"),),
            "palette-glass": (G.EffectAt("palette", 1, into="output.2"),),
            "acid-scene": (G.EffectAt("acid", 2, after="scene"),)}
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    for slug in PLACED:
        doc = _fixture(slug)
        assert G.read_graph(doc["graph"]).to_json() == doc["graph"]
        dst = rig.home / "presets" / f"{slug}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text((FIXTURES / f"{slug}.json").read_text())
        missing = rig.lib.load(PRESETS, slug)
        assert missing == [] and rig.presets.notes == [] and rig.presets.migrated, slug
        assert stub.wiring.placed == () and stub.wiring.wired, slug
        (e,) = want[slug]
        assert any(w.dst == f"{e.name}.image" for w in stub.wiring.wires), slug
        assert not rig.lib.is_dirty(PRESETS), slug
        saved = rig.presets.document(slug)
        assert not any(k in n for n in saved[preset.GRAPH_KEY]["nodes"] for k in G.PLACE_KEYS)
        assert saved[preset.GRAPH_KEY] == rig.presets.graph.free_doc()     # (row 394)
        line = json.dumps(saved[preset.GRAPH_KEY]["nodes"][0])
        assert f'"graph": {{"frame": "wired",\n "nodes": [\n  {line}' in preset.dumps(saved)
    assert rig.reg["fx.acid.2.on"].value and rig.reg["dream.on"].value


def test_no_factory_preset_changes_and_the_default_graph_is_identical():
    """No library preset places an effect (or carries a graph); with no
    placement the frame is D0's — every effect in every run (the through
    outputs' copies too, plan 35 T4), no placed node, the readout split as
    before, the pool two — and a wiring whose placements were all refused
    builds the same graph."""
    for path in sorted((FACTORY / "presets").glob("*.json")):      # (plan 36 T3: /7)
        nodes = json.loads(path.read_text())["graph"]["nodes"]
        assert not any(k in e for e in nodes for k in G.PLACE_KEYS), path.name
    for path in sorted(preset.FACTORY_SOURCES.glob("*.json")):         # (their sources)
        assert "graph" not in json.loads(path.read_text()), path.name
    shows = [Shows(through=True), Shows(scene=False, through=True), Shows()]
    plain = graph(shows, G.Wiring(run=RUN), effects=RUN)     # (plan 33: by wires)
    assert G.Wiring().placed == () and plain.dormant == {} and plain.notes == []
    assert not [n for n in plain.order if isinstance(n, G.Effect)
                and n.placed in ("after", "into")]
    assert plain.nodes["hands.layer"].readout == "downstream" and plain.pool == 2
    for k in (1, 2, 3):
        assert _run_names(plain, _end(plain, k)) == list(RUN)
    assert "lookback" not in plain.nodes          # (plan 36 T4: the old words' off)
    assert plain.nodes["output.3"].inputs["hands"] is plain.nodes["hands.layer"]
    refused = G.read_graph({"nodes": [{"kind": "effect", "file": "palette",
                                       "after": "teapot"}]}, effects=FILES)
    again = graph(shows, replace(refused.wiring(), run=RUN), effects=RUN)
    assert repr(again) == repr(plain) and refused.wiring() == G.Wiring()


# ---------------------------------------------------------------- the graph


def test_a_placed_effect_is_not_in_the_chain_run():
    """A placed effect has no node in any run; migrated (plan 36 T3) it sits
    on its edge as wires — after the hands' layer for every consumer of the
    layer (a through composite, an output laying it over) but the readout;
    after an effect of the run (the original: one instance is one node);
    into an output's picture between it and the window. `Graph.effects`
    (the renderer's key) is still the whole stack."""
    shows = [Shows(), Shows(through=True), Shows(scene=False, through=True)]
    g = _graph(shows, G.EffectAt("palette", 1, after="hands"),
               G.EffectAt("palette", 2, into="output.2"),
               G.EffectAt("acid", 2, after="acid"))
    assert g.effects == RUN
    hands, pal = g.nodes["hands.layer"], g.nodes["palette"]
    assert pal.placed == "wire" and pal.inputs["image"] is hands and pal.makes
    assert pal.see_through
    assert g.nodes["composite"].inputs["over"] is pal
    assert g.nodes["composite.2"].inputs["over"] is pal
    assert g.nodes["output.1"].inputs["hands"] is pal
    assert all(g.nodes[f"output.{i}"].inputs["readout"] is hands for i in (1, 2, 3))
    assert hands.readout == "always"               # the guide is never folded
    # the second acid after acid, in output 1's run
    a2 = g.nodes["acid.2"]
    assert a2.inputs["image"] is g.nodes["acid"]
    assert _run_names(g, _end(g, 1)) == ["warp", "acid", "acid.2"]
    # into output 2: its picture through the palette 2
    assert _run_names(g, _end(g, 2))[-1] == "palette.2"
    assert "palette.2" not in _run_names(g, _end(g, 1))
    order = [n.name for n in g.order]
    assert order.index("hands.layer") < order.index("palette") < order.index("composite")


def test_after_scene_and_into_the_history_in_the_graph():
    """`after: scene`: the history, the capture (or the history's
    composite) read the effect; the cover (the face buffer) and the
    depth ports still read the scene. `into: history`: the history alone,
    the capture keeping the scene."""
    vs = [View(S(), (10, 10))]
    g = _graph(vs, G.EffectAt("acid", 2, after="scene"))
    a2, scene = g.nodes["acid.2"], g.nodes["scene"]
    assert a2.inputs["image"] is scene and a2.makes and not a2.see_through
    # (plan 36 T4: the trail added onto it, held back by it, and recording it)
    assert g.nodes["composite"].inputs["under"] is a2
    assert g.nodes["lookback"].inputs["occluder"] is a2
    assert g.nodes["lookback(capture)"].inputs["image"] is a2
    assert g.nodes["lookback(cover)"].inputs["scene"] is scene
    assert g.readers(a2) == 3
    at = (G.EffectAt("acid", 2, after="scene"),)
    g = G.build_graph(vs, wired_wiring(G.Wiring(blend="depth", history="scene+hands", placed=at,
                                                run=_run(at)), "trail"), effects=RUN)
    a2 = g.nodes["acid.2"]
    assert g.nodes["composite"].inputs["under"] is a2
    assert g.nodes["composite"].inputs["depth"] is g.nodes["scene"]
    g = _graph(vs, G.EffectAt("acid", 2, into="history"))
    assert g.nodes["composite"].inputs["under"] is g.nodes["acid.2"]
    assert g.nodes["lookback(capture)"].inputs["image"] is g.nodes["scene"]


def test_a_placement_with_nothing_to_sit_on_is_said_and_wired_nowhere():
    """Plan 36 T3: a placement on a picture the frame does not have — an
    output wired to show nothing — drew nothing: the migration wires it
    nowhere and says so; one after a node nothing reads (no hands laid) is
    wired after it, unread — no node built; the rest is the run."""
    at = (G.EffectAt("palette", 1, after="hands"), G.EffectAt("acid", 2, into="output.2"))
    sec = M.wired_of(_wiring(*at), placements=False)
    sec = {**sec, "wires": [w for w in sec["wires"] if not w["to"].startswith(
        ("output.all.hands", "output.all.guide"))] + [{"from": "ground", "to": "output.2.image"}]}
    notes: list[str] = []
    got = M.placed_wires(sec, notes=notes)
    assert notes == [("acid.2 into 'output.2' — output 2 shows no picture: it drew nothing, "
                      "so it is not wired (plan 36)")]
    assert {"from": "hands.layer", "to": "palette.image"} in got["wires"]
    g = G.build_graph([View(S(), (10, 10))] * 2, G.read_graph(got).wiring(), effects=RUN)
    assert not {"palette", "acid.2"} & set(g.nodes)
    assert _run_names(g, _end(g)) == ["warp", "acid", "palette.2"]


def test_the_words_say_the_placements():
    """`graph_words` of an old section (the words an old file's placements
    had) and `placement_words`; a `/7` frame has none (plan 36 T3)."""
    spec = G.read_graph({"nodes": [
        {"kind": "effect", "file": "acid", "instance": 2, "after": "scene"},
        {"kind": "effect", "file": "palette", "after": "hands"},
        {"kind": "effect", "file": "palette", "instance": 2, "into": "output.2"}]})
    assert G.graph_words(spec) == ("graph: acid ×2 · palette ×2 · acid 2 before the history · "
                                   "palette on the hands · palette 2 on output 2 only")
    assert wired_wiring(spec.wiring()).placed == ()
    for e, words in ((G.EffectAt("acid", 2, into="history"), "acid 2 into the history only"),
                     (G.EffectAt("palette", 1, after="history"),
                      "palette after the history"),
                     (G.EffectAt("palette", 1, after="hands.2"), "palette on hands 2"),
                     (G.EffectAt("palette", 1, after="output.3"),
                      "palette on output 3 only"),
                     (G.EffectAt("palette", 1, after="acid.2"), "palette after acid 2"),
                     (G.EffectAt("palette", 1, into="warp"), "palette before warp")):
        assert G.placement_words(e) == words


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


def _palette(r, name="palette"):
    r.fx.state.values[name].update(on=True, mix=1.0, hue_from=170.0, hue_to=230.0)


def _read(tex):
    import numpy as np

    kind = {"f1": np.uint8, "f2": np.float16, "f4": np.float32}[tex.dtype]
    w, h = tex.size
    return np.frombuffer(tex.read(), dtype=kind).reshape(h, w, tex.components)


def test_after_hands_folds_the_hands_layer_and_not_the_shape(ctx):
    """The palette after the hands on the synthetic pose: the scene's
    texture is byte for byte the scene with no palette (the shape is not
    folded), the output differs from the unfolded one only where the
    hands' layer covers it — and there it does; the palette ran once a
    frame, on the layer, timed under its own name after `hands`."""
    import numpy as np
    from test_outputs import keep_run, rig, run, views

    def frame(placed: bool):
        r = rig(ctx, effects=())
        if placed:
            _palette(r)
            r.wiring = wired_wiring(keep_run(r, G.Wiring(placed=(G.EffectAt("palette", 1, after="hands"),))))
        calls = []
        real = r.fx.run_one

        def run_one(name, src, dst, t, **kw):
            calls.append((name, src, kw))
            real(name, src, dst, t, **kw)

        r.fx.run_one = run_one
        pic = run(ctx, r, views(ctx, S()), frames=2)[0]
        return r, pic, _read(r.scene.tex).copy(), _read(r.ghost.tex).copy(), calls

    plain, a, scene_a, layer_a, _ = frame(False)
    folded, b, scene_b, layer_b, calls = frame(True)
    assert np.array_equal(scene_a, scene_b)              # the shape is not folded
    assert np.array_equal(layer_a, layer_b)              # the hands drawn alike …
    cover = layer_a[::-1, :, 3] > 0                      # (GL rows bottom first)
    assert cover.any() and not cover.all()
    differ = (a != b).any(axis=2)
    assert differ.any() and not (differ & ~cover).any()  # … folded only where they are
    g = folded._graph
    pal = g.nodes["palette"]
    assert [c[0] for c in calls] == ["palette"] * 2      # once a frame
    assert all(c[1] is folded.ghost.tex and c[2] == {"opaque": 0} for c in calls)
    assert folded.stats["effects"] == ["palette"] and pal.placed == "wire"   # (plan 36 T3)
    names = g.timed_in(G.Frame(folded, ctx, None, 1, 1, 1.0, 0.0, [], (1, 1), 0, None,
                               (0, 0, 1, 1), stats={"effects": ["palette"]}))
    assert names.index("hands.layer") < names.index("palette")
    assert not plain.stats["effects"]


def test_into_output_2_folds_one_output_only(ctx):
    """Two outputs showing the same pipeline: the palette placed into
    output 2 folds that output's picture; output 1 is byte for byte the
    frame with no palette; the chain ran once."""
    import numpy as np
    from test_outputs import keep_run, rig, run, views

    def frame(placed: bool):
        r = rig(ctx, effects=("warp",), hands=False)
        if placed:
            _palette(r)
            r.wiring = wired_wiring(keep_run(r, G.Wiring(placed=(G.EffectAt("palette", 1, into="output.2"),))))
        return r, run(ctx, r, views(ctx, S(), S()), frames=2)

    _, (a1, a2) = frame(False)
    r, (b1, b2) = frame(True)
    assert np.array_equal(a1, b1) and np.array_equal(a1, a2)
    assert not np.array_equal(a2, b2)
    assert r.stats["effects"] == ["warp", "palette"]
    # (plan 36 T3: the palette a wire into output 2's picture, no fold)
    assert _run_names(r._graph, _end(r._graph, 2))[-1] == "palette"


def test_after_scene_feeds_the_history_the_folded_picture(ctx):
    """A second acid after the scene: the capture's source is the
    effect's folded texture (a pool texture, not the scene's), the
    history reads the same one, and the effect ran once a frame for both;
    the frame differs from the one without it."""
    import numpy as np
    from test_outputs import keep_run, rig, run, views

    r = rig(ctx, effects=(), hands=False, echoes=True)
    st = r.fx.state
    st.set_instances({"acid": 2})
    st.values["acid.2"].update(on=True, mix=1.0, twist=1.5, bend=0.05)
    r.wiring = wired_wiring(keep_run(r, G.Wiring(placed=(G.EffectAt("acid", 2, after="scene"),))),
                            "trail")
    seen = []
    real = r.lookback.capture

    def capture(src, target):
        seen.append(src)
        real(src, target)

    r.lookback.capture = capture
    got = run(ctx, r, views(ctx, S()), frames=3)[0]
    g = r._graph
    a2 = g.nodes["acid.2"]
    assert (g.nodes["lookback(capture)"].inputs["image"] is a2
            and g.nodes["composite"].inputs["under"] is a2)
    assert len(seen) == 3 and all(s is not r.scene.tex for s in seen)
    assert all(any(s is t for t in r.fx._tex) for s in seen)      # the effect's held texture
    assert r.stats["effects"] == ["acid.2"]
    plain = rig(ctx, effects=(), hands=False, echoes=True)
    want = run(ctx, plain, views(ctx, S()), frames=3)[0]
    assert not np.array_equal(got, want)


def test_a_presenter_lays_the_folded_hands_and_shows_the_folded_frame(ctx):
    """An output in another context (a presenter: the projector and the
    glass on the rig, `app._open_presenters`) gets what a target view
    shows: with the palette after the hands its hand-off's hands are the
    palette's folded texture, not the Ghost's; with the layer drawn by
    hands 2, folded from that Ghost at its opacity; with the palette into
    output 2, output 2's hand-off frame is the folded one and output 1 is
    byte for byte the frame without it."""
    import numpy as np
    from test_outputs import H, W, keep_run, rig, run, views

    from hyperspace.ghost import GhostState

    r = rig(ctx, effects=(), alpha=0.7)
    _palette(r)
    r.wiring = wired_wiring(keep_run(r, G.Wiring(placed=(G.EffectAt("palette", 1, after="hands"),))))
    pv = View(S(), (W, H), presenter=object())
    run(ctx, r, [views(ctx, S())[0], pv], frames=2)
    assert r._graph.nodes["output.2"].inputs["hands"] is r._graph.nodes["palette"]
    ho = pv.handoff
    assert ho.hands is not None and ho.hands is not r.ghost.tex
    assert any(ho.hands is t for t in r.fx._tex)              # the held, folded picture
    assert ho.alpha == pytest.approx(0.7)
    # the layer made by hands 2: that Ghost's picture folded, its opacity
    r = rig(ctx, effects=())
    _palette(r)
    r.ghost_states = {"ghost.2": GhostState(on=True, alpha=0.25)}
    # (unwired: `wire_switches` lays the states on, then writes the placement)
    r.wiring = keep_run(r, G.Wiring(hands="scene", extra=(G.HandsAt(2),),
                                    placed=(G.EffectAt("palette", 1, after="hands.2"),)))
    calls = []
    real = r.fx.run_one

    def run_one(name, src, dst, t, **kw):
        calls.append(src)
        real(name, src, dst, t, **kw)

    r.fx.run_one = run_one
    # (plan 35 T4: the glass's state — the scene off, the hands over — is
    # its output's wiring; the scene holding hands 1, the layer is hands 2's)
    pv = View(wire_switches(r, S(), Thru(scene=False, through=False))[1], (W, H),
              presenter=object())
    run(ctx, r, [views(ctx, S())[0], pv], frames=2)
    g2 = r.ghost_of("ghost.2")
    from types import SimpleNamespace as NS
    assert r._graph.nodes["palette"].ghost(NS(r=r)) is g2
    assert calls and all(src is g2.tex for src in calls)
    assert pv.handoff.hands is not None and pv.handoff.hands not in (g2.tex, r.ghost.tex)
    assert pv.handoff.alpha == pytest.approx(0.25)

    # into output 2, output 2 a presenter
    def frame(placed: bool):
        r = rig(ctx, effects=("warp",), hands=False)
        if placed:
            _palette(r)
            r.wiring = wired_wiring(keep_run(r, G.Wiring(placed=(G.EffectAt("palette", 1, into="output.2"),))))
        pv = View(S(), (W, H), presenter=object())
        return r, run(ctx, r, [views(ctx, S())[0], pv], frames=2)[0], pv

    plain, a1, pa = frame(False)
    r, b1, pb = frame(True)
    assert np.array_equal(a1, b1)
    assert pb.handoff.frame is not None and pa.handoff.frame is not None
    assert "palette" in r.stats["effects"] and "palette" not in plain.stats["effects"]


def test_a_placed_effect_alone_bends_no_pipeline(ctx):
    """With only a placed effect on, `fx_on` is off: no chain runs — and
    the placed effect still runs. Plan 36 T1: the through output shows its
    own chain as wired (its copy reads through), no stand-down to the
    run's end."""
    from test_outputs import keep_run, rig, run, wviews

    r = rig(ctx, effects=("warp",))
    r.fx.state.values["warp"]["on"] = False      # (in the run, off: a copy to stand down)
    _palette(r)
    r.wiring = keep_run(r, G.Wiring(placed=(G.EffectAt("palette", 1, after="hands"),)))
    run(ctx, r, wviews(ctx, r, S(), Thru()), frames=2)
    assert r.fx.state.live("palette") and r.stats["fx_on"] is False
    assert r.stats["chain_runs"] == 0 and r.stats["effects"] == ["palette"]
    assert r.stats["routes"] == [("shown(warp)", True), ("shown(copy)", False)]
    assert r.stats["ends"] == ["shown(warp)", "shown(copy)"]


def test_into_a_through_output_folds_its_chain_every_frame(ctx):
    """The palette into output 2, a hands-through glass with the scene off,
    and no effect of the run on. Plan 36 T1 (no stand-down): the output
    shows its chain as wired — the hands alone through the run's copy —
    so the palette folds it this frame, nothing is dormant, and with an
    effect of the run on it folds it still."""
    from test_outputs import rig, run, wviews

    glass = Thru(scene=False)
    r = rig(ctx, effects=())
    _palette(r)
    r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, into="output.2"),), run=("warp",))
    run(ctx, r, wviews(ctx, r, S(), glass), frames=2)
    g = r._graph
    assert _run_names(g, _end(g, 2))[-1] == "palette"     # (plan 36 T3: a wire, no fold)
    assert r.stats["routes"][1][0] is not None
    assert "palette" in r.stats["effects"]
    assert "palette" not in g.dormant and not g.stood
    r.fx.state.values["warp"]["on"] = True
    run(ctx, r, wviews(ctx, r, S(), glass), frames=1)
    assert "palette" in r.stats["effects"] and "palette" not in r._graph.dormant
