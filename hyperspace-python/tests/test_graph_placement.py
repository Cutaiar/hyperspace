"""Plan 30 D1: placing an effect on any image edge from the preset.

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
from test_graph_json import Stub, _bare
from test_presets import boot, put

from hyperspace import graph as G
from hyperspace import preset
from hyperspace.library import FACTORY, PRESETS
from hyperspace.outputs import HANDS, SCENE, SCENE_HANDS, Switches, View

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


def _graph(views, *placed, effects=RUN):
    return G.default_graph(views, G.Wiring(placed=tuple(placed), run=_run(placed, effects)),
                           effects=effects)


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
    # refused at build too, same shape: the run is its wires (plan 33 R),
    # the two placements in a loop take no other place
    w = G.Wiring(placed=(G.EffectAt("palette", 1, after="acid.2"),
                         G.EffectAt("acid", 2, into="palette")), run=RUN)
    g = G.default_graph([View(S(), (10, 10))], w, effects=RUN)
    assert g.notes == [
        ("palette after 'acid.2' — that makes a loop (palette after acid.2 into palette); "
         "the default placement"),
        ("acid.2 into 'palette' — that makes a loop (acid.2 into palette after acid.2); "
         "the default placement")]
    assert [e.effect for e in g.nodes["fx"].effects] == list(RUN)
    # through a preset load: the note, the rest landed, the section kept
    rig = boot(tmp_path)
    stub = Stub()
    rig.presets.graph.attach(stub)
    section = {"nodes": [{"kind": "hands", "into": "scene"},
                         {"kind": "effect", "file": "palette", "after": "teapot"}]}
    put(rig.home, "Odd", values={"view.bright": 3.0}, graph=section)
    rig.lib.load(PRESETS, "Odd")
    assert rig.presets.notes == [f"graph: {teapot}; the default placement"]
    assert _bare(stub.wiring) == G.Wiring(hands="scene") and rig.reg["view.bright"].value == 3.0
    assert rig.presets.document("Odd")[preset.GRAPH_KEY] == section
    assert not rig.lib.is_dirty(PRESETS)


def test_the_section_round_trips_with_its_placements(tmp_path):
    """`after` / `into` read and written back plainly (instance 1 named
    only by its file when placed); each fixture's section is its spec's
    JSON; loaded from a scratch library it lands with no note and a clean
    dot, the renderer gets the placements, a save writes the section back
    one node per line."""
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
    # an unplaced instance 1 is still refused (it is the file itself)
    with pytest.raises(G.GraphError, match="2 or more"):
        G.read_graph({"nodes": [{"kind": "effect", "file": "palette"}]})
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
        assert missing == [] and rig.presets.notes == [], slug
        assert stub.wiring.placed == want[slug]
        assert not rig.lib.is_dirty(PRESETS), slug
        saved = rig.presets.document(slug)
        assert saved[preset.GRAPH_KEY] == doc["graph"]
        line = json.dumps(doc["graph"]["nodes"][0])
        assert f'"graph": {{"nodes": [\n  {line}\n ]}}' in preset.dumps(saved)
    assert rig.reg["fx.acid.2.on"].value and rig.reg["dream.on"].value


def test_no_factory_preset_changes_and_the_default_graph_is_identical():
    """No library preset places an effect (or carries a graph); with no
    placement the default graph is D0's — every effect in every run, no
    placed node, the readout split as before, the pool two — and a
    wiring whose placements were all refused builds the same graph."""
    for path in sorted((FACTORY / "presets").glob("*.json")):
        assert "graph" not in json.loads(path.read_text()), path.name
    vs = [View(S(through=True), (10, 10)), View(S(scene=False, through=True), (10, 10)),
          View(S(), (10, 10))]
    plain = G.default_graph(vs, G.Wiring(run=RUN), effects=RUN)     # (plan 33: by wires)
    assert G.Wiring().placed == () and plain.dormant == {} and plain.notes == []
    assert not [n for n in plain.order if isinstance(n, G.Effect) and n.placed]
    assert plain.nodes["hands"].readout == "through" and plain.pool == 2
    for end in G.FX_NAMES.values():
        assert [e.effect for e in plain.nodes[end].effects] == list(RUN)
    assert plain.nodes["history"].inputs["image"] is plain.nodes["scene"]
    assert plain.nodes["output.3"].inputs["hands"] is plain.nodes["hands"]
    refused = G.read_graph({"nodes": [{"kind": "effect", "file": "palette",
                                       "after": "teapot"}]}, effects=FILES)
    again = G.default_graph(vs, replace(refused.wiring(), run=RUN), effects=RUN)
    assert repr(again) == repr(plain) and refused.wiring() == G.Wiring()


# ---------------------------------------------------------------- the graph


def test_a_placed_effect_is_not_in_the_chain_run():
    """A placed effect has no node in any run; it sits on its edge — after
    the hands' layer for every consumer of the layer (a through
    composite, an output laying it over) but the readout; after an effect
    of the chain once per pipeline, named like the run's nodes; into an
    output's picture between it and its end. `Graph.effects` (the
    renderer's key) is still the whole stack."""
    vs = [View(S(), (10, 10)), View(S(through=True), (10, 10)),
          View(S(scene=False, through=True), (10, 10))]
    g = _graph(vs, G.EffectAt("palette", 1, after="hands"),
               G.EffectAt("palette", 2, into="output.2"),
               G.EffectAt("acid", 2, after="acid"))
    assert g.effects == RUN
    for end in G.FX_NAMES.values():
        run = [e.effect for e in g.nodes[end].effects]
        assert run == ["warp", "acid"], (end, run)
    hands, pal = g.nodes["hands"], g.nodes["palette"]
    assert pal.placed == "after" and pal.inputs["image"] is hands and pal.makes
    assert pal.see_through
    assert g.nodes["composite(scene+hands)"].inputs["over"] is pal
    assert g.nodes["composite(hands)"].inputs["over"] is pal
    assert g.nodes["output.1"].inputs["hands"] is pal
    assert all(g.nodes[f"output.{i}"].inputs["readout"] is hands for i in (1, 2, 3))
    assert hands.readout == "always"               # the guide is never folded
    # the second acid after each pipeline's acid
    for key, suffix in ((SCENE, ""), (SCENE_HANDS, "(scene+hands)"), (HANDS, "(hands)")):
        a2 = g.nodes["acid.2" + suffix]
        assert a2.inputs["image"] is g.nodes["acid" + suffix] and a2.placed == "after"
        assert g.nodes[G.FX_NAMES[key]].inputs["image"] is a2
    # into output 2: its picture through the palette 2, the end behind it
    out = g.nodes["output.2"]
    assert [e.effect for e in out.folds] == ["palette.2"]
    assert out.folds[0].inputs["image"] is g.nodes["fx(scene+hands)"]
    assert g.folds(1) and not g.folds(0)
    assert g.nodes["output.1"].inputs["image"] is g.nodes["fx"]
    # timed after what it reads: SYSTEM shows `palette` under `hands`
    order = [n.name for n in g.order]
    assert order.index("hands") < order.index("palette") < order.index("composite(scene+hands)")
    # the pool: two, the palette held (it folds the layer once), the
    # palette 2 held (it folds output 2's frame)
    assert g.pool == 4


def test_after_scene_and_into_the_history_in_the_graph():
    """`after: scene`: the history, the capture (or the history's
    composite) read the effect; the cover (the face buffer) and the
    depth ports still read the scene. `into: history`: the history alone,
    the capture keeping the scene."""
    vs = [View(S(), (10, 10))]
    g = _graph(vs, G.EffectAt("acid", 2, after="scene"))
    a2, scene = g.nodes["acid.2"], g.nodes["scene"]
    assert a2.inputs["image"] is scene and a2.makes and not a2.see_through
    assert g.nodes["history"].inputs["image"] is a2
    assert g.nodes["capture"].inputs["image"] is a2
    assert g.nodes["cover"].inputs["scene"] is scene
    assert g.readers(a2) == 2
    at = (G.EffectAt("acid", 2, after="scene"),)
    g = G.default_graph(vs, G.Wiring(blend="depth", history="scene+hands", placed=at,
                                     run=_run(at)), effects=RUN)
    a2 = g.nodes["acid.2"]
    assert g.nodes["composite(history)"].inputs["under"] is a2
    assert g.nodes["composite(history)"].inputs["depth"] is g.nodes["scene"]
    g = _graph(vs, G.EffectAt("acid", 2, into="history"))
    assert g.nodes["history"].inputs["image"] is g.nodes["acid.2"]
    assert g.nodes["capture"].inputs["image"] is g.nodes["scene"]


def test_a_placement_the_graph_lacks_is_dormant_and_said_in_words():
    """A node the built graph lacks this frame — no hands layer, an output
    not open, an output showing no picture, an effect not in this build —
    leaves the effect dormant: no node, so no pass, and the words say why
    (the OUTPUT page's line and the graph's)."""
    from hyperspace.ui import dormant_lines

    no_hands = [View(S(hands=False), (10, 10)), View(S(scene=False, hands=False), (10, 10))]
    g = _graph(no_hands, G.EffectAt("palette", 1, after="hands"),
               G.EffectAt("palette", 2, into="output.3"),
               G.EffectAt("acid", 2, into="output.2"),
               G.EffectAt("warp", 1, after="palette"),
               G.EffectAt("kaleido", 1, after="scene"))
    assert g.dormant == {
        "palette": "palette after hands — no hands layer this frame",
        "palette.2": "palette.2 into output.3 — no output 3 this frame",
        "acid.2": "acid.2 into output.2 — output 2 shows no picture this frame",
        "warp": "warp after palette — palette is dormant this frame",
        "kaleido": "kaleido after scene — no kaleido effect in this build"}
    assert not {"palette", "palette.2", "acid.2", "warp", "kaleido"} & set(g.nodes)
    assert [e.effect for e in g.nodes["fx"].effects] == ["acid"]   # none back in the run
    assert dormant_lines(g)[0] == "dormant: acid.2 into output.2 — output 2 shows no " \
        "picture this frame"
    assert dormant_lines(None) == []
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "palette", "after": "hands"}]})
    assert G.graph_words(spec, g.dormant) == \
        "graph: palette after hands — no hands layer this frame"
    # the hands back: the palette has its node and its words
    g = _graph([View(S(), (10, 10))], G.EffectAt("palette", 1, after="hands"))
    assert g.dormant == {} and isinstance(g.nodes["palette"], G.Effect)
    assert G.graph_words(spec, g.dormant) == "graph: palette on the hands"


def test_the_words_say_the_placements():
    """`graph_words`, the OUTPUT page's "shows:" line (`output_shows` with
    the output's number) and the LOOKBACK page's history line."""
    from types import SimpleNamespace as NS

    from hyperspace.ui import output_shows
    from hyperspace.ui_lookback import history_line

    spec = G.read_graph({"nodes": [
        {"kind": "effect", "file": "acid", "instance": 2, "after": "scene"},
        {"kind": "effect", "file": "palette", "after": "hands"},
        {"kind": "effect", "file": "palette", "instance": 2, "into": "output.2"}]})
    assert G.graph_words(spec) == ("graph: acid ×2 · palette ×2 · acid 2 before the history · "
                                   "palette on the hands · palette 2 on output 2 only")
    w = spec.wiring()
    assert output_shows(S(), True, True, 1.0, w, n=1) == (
        "scene + hands over the effects · acid 2 before the history · palette on the hands",
        "")
    assert output_shows(S(), True, True, 1.0, w, n=2)[0] == (
        "scene + hands over the effects · acid 2 before the history · palette on the hands"
        " · palette 2 on this output only")
    assert output_shows(S(scene=False, through=True), True, True, 1.0, w, n=3)[0] == \
        "hands through the effects · palette on the hands"
    assert output_shows(S(hands=False), True, True, 1.0, w, n=3)[0] == \
        "scene · acid 2 before the history"
    # without the number (or with no placement) the words are A4's
    assert output_shows(S(), True, True, 1.0, w) == ("scene + hands over the effects", "")
    assert history_line(NS(wiring=w)) == "history: the scene · acid 2 before the history"
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
    from test_outputs import rig, run, views

    def frame(placed: bool):
        r = rig(ctx, effects=())
        if placed:
            _palette(r)
            r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, after="hands"),))
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
    assert folded.stats["effects"] == ["palette"] and pal.placed == "after"
    names = g.timed_in(G.Frame(folded, ctx, None, 1, 1, 1.0, 0.0, [], (1, 1), 0, None,
                               (0, 0, 1, 1), stats={"effects": ["palette"]}))
    assert names.index("hands") < names.index("palette") < names.index("fx")
    assert not plain.stats["effects"]


def test_into_output_2_folds_one_output_only(ctx):
    """Two outputs showing the same pipeline: the palette placed into
    output 2 folds that output's picture; output 1 is byte for byte the
    frame with no palette; the chain ran once."""
    import numpy as np
    from test_outputs import rig, run, views

    def frame(placed: bool):
        r = rig(ctx, effects=("warp",), hands=False)
        if placed:
            _palette(r)
            r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, into="output.2"),))
        return r, run(ctx, r, views(ctx, S(), S()), frames=2)

    _, (a1, a2) = frame(False)
    r, (b1, b2) = frame(True)
    assert np.array_equal(a1, b1) and np.array_equal(a1, a2)
    assert not np.array_equal(a2, b2)
    assert r.stats["chain_runs"] == 1 and r.stats["effects"] == ["warp", "palette"]
    assert [e.effect for e in r._graph.nodes["output.2"].folds] == ["palette"]


def test_after_scene_feeds_the_history_the_folded_picture(ctx):
    """A second acid after the scene: the capture's source is the
    effect's folded texture (a pool texture, not the scene's), the
    history reads the same one, and the effect ran once a frame for both;
    the frame differs from the one without it."""
    import numpy as np
    from test_outputs import rig, run, views

    r = rig(ctx, effects=(), hands=False, echoes=True)
    st = r.fx.state
    st.set_instances({"acid": 2})
    st.values["acid.2"].update(on=True, mix=1.0, twist=1.5, bend=0.05)
    r.wiring = G.Wiring(placed=(G.EffectAt("acid", 2, after="scene"),))
    seen = []
    real = r.lookback.capture

    def capture(src, target):
        seen.append(src)
        real(src, target)

    r.lookback.capture = capture
    got = run(ctx, r, views(ctx, S()), frames=3)[0]
    g = r._graph
    a2 = g.nodes["acid.2"]
    assert g.nodes["capture"].inputs["image"] is a2 and g.nodes["history"].inputs["image"] is a2
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
    from test_outputs import H, W, rig, run, views

    from hyperspace.ghost import GhostState

    r = rig(ctx, effects=(), alpha=0.7)
    _palette(r)
    r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, after="hands"),))
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
    r.wiring = G.Wiring(hands="scene", extra=(G.HandsAt(2),),
                        placed=(G.EffectAt("palette", 1, after="hands.2"),))
    calls = []
    real = r.fx.run_one

    def run_one(name, src, dst, t, **kw):
        calls.append(src)
        real(name, src, dst, t, **kw)

    r.fx.run_one = run_one
    pv = View(S(scene=False), (W, H), presenter=object())
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
            r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, into="output.2"),))
        pv = View(S(), (W, H), presenter=object())
        return r, run(ctx, r, [views(ctx, S())[0], pv], frames=2)[0], pv

    plain, a1, pa = frame(False)
    r, b1, pb = frame(True)
    assert np.array_equal(a1, b1)
    assert pb.handoff.frame is not None and any(pb.handoff.frame is t for t in r.fx._tex)
    assert pa.handoff.frame is not None and not any(pa.handoff.frame is t
                                                    for t in plain.fx._tex)


def test_a_placed_effect_alone_bends_no_pipeline(ctx):
    """With only a placed effect on, `fx_on` is off: a through output
    stands down for the scene's pipeline (no SCENE+HANDS run, no second
    frame texture), no chain runs — and the placed effect still runs."""
    from test_outputs import rig, run, views

    r = rig(ctx, effects=())
    _palette(r)
    r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, after="hands"),))
    run(ctx, r, views(ctx, S(), S(through=True)), frames=2)
    assert r.fx.active() and r.stats["fx_on"] is False
    assert r.stats["chain_runs"] == 0 and r.stats["effects"] == ["palette"]
    assert r.stats["routes"] == [(SCENE, True), (SCENE, True)]
    assert SCENE_HANDS not in r.stats["pipelines"]


def test_into_a_through_output_standing_down_to_its_ground_is_dormant_for_the_frame(ctx):
    """The palette into output 2, a hands-through glass with the scene off,
    and no effect of the run on: the output stands down to its ground with
    the hands over (`settle` → no end, the layer over), so there is nothing
    to fold — the palette runs nowhere, the output's pixels are the frame
    with no placement, and the words say so through the dormant path
    (`Graph.dormant` → OUTPUT's `dormant:` line, `graph_words`). The next
    frame with an effect on bends the pipeline: the palette folds it and
    the words go."""
    import numpy as np
    from test_outputs import rig, run, views

    from hyperspace.ui import dormant_lines

    glass = S(scene=False, hands=True, through=True)
    said = "palette into output 2 — output 2 stands down this frame"

    def frame(placed: bool):
        r = rig(ctx, effects=())
        if placed:
            _palette(r)
            r.wiring = G.Wiring(placed=(G.EffectAt("palette", 1, into="output.2"),))
        return r, run(ctx, r, views(ctx, S(), glass), frames=2)

    _, (a1, a2) = frame(False)
    r, (b1, b2) = frame(True)
    g = r._graph
    assert [e.effect for e in g.nodes["output.2"].folds] == ["palette"]
    assert r.stats["routes"][1] == (None, True)            # its ground, the hands over
    assert "palette" not in r.stats["effects"]
    assert np.array_equal(a1, b1) and np.array_equal(a2, b2)   # no pixel moved
    assert g.dormant == {"palette": said} and g.stood == {"palette"}
    assert f"dormant: {said}" in dormant_lines(g)
    spec = G.read_graph({"nodes": [{"kind": "effect", "file": "palette", "into": "output.2"}]})
    assert G.graph_words(spec, g.dormant) == f"graph: {said}"
    # an effect of the run on: the glass's pipeline bends, the palette folds it
    r.fx.state.values["warp"]["on"] = True
    run(ctx, r, views(ctx, S(), glass), frames=1)
    g = r._graph
    assert r.stats["routes"][1][0] is not None
    assert "palette" in r.stats["effects"]
    assert "palette" not in g.dormant and not g.stood
