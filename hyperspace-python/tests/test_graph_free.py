"""Plan 33 G and R: the free graph's vocabulary, then the run from wires.

New wire ends (`frame`, `fx.image`, `pattern`, `shape.faces`,
`backdrop.image`, `switch`), a wire from a channel into an effect as a
branch instead of a refusal, and `reaches` / `run_of` read off the wires
(data only). Then T3: the renderer builds each pipeline's run from the
preset graph's wires `frame → … → fx.image`, an effect on no wire has no
node, and an untouched pre-33 preset saves byte for byte as the base
build writes it (Review Focus 1). The pictures are test_golden_frames.py's.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

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


# ---------------------------------------------------------------- R: the run from wires (T3)

ROOT = Path(__file__).resolve().parents[1]
SAVES = ROOT / "tests" / "fixtures" / "plan33-v4-saves"
LIBRARY = ROOT / "hyperspace" / "library" / "presets"
SOURCES = {"presets": ROOT / "tests" / "fixtures" / "presets",
           "merge-31-32": ROOT / "tests" / "fixtures" / "merge-31-32"}
# R14 → R19: a route on each channel choice (a /4 and a /2). Since T5 they
# load with a switch and save as /5 (row 347), so they are not byte sources
DRIVEN = ROOT / "tests" / "fixtures" / "plan33-driven"


def test_the_wiring_holds_the_run_and_leaves_its_wires_out():
    """A section that says a run: `Wiring.run` is it, in wire order, and
    its wires are no edge (a middle effect is not shortened to D1's
    `after`); the faces' run is edges (T4) and a channel straight into the
    backdrop is the wiring's backdrop; an effect that reaches nothing has no
    wire built. A section with no run's head says none (None: the stack,
    until T7)."""
    spec = G.read_graph(section(("frame", "a.image"), ("a", "b.image"), ("b", "c.image"),
                                ("c", "fx.image"), ("media.b", "backdrop.image"),
                                ("pattern", "kaleido.image"), ("kaleido", "shape.faces"),
                                ("media.a", "acid.2.image"), ("history", "palette.image"),
                                ("palette", "output.2.image"),
                                nodes=[{"kind": "effect", "file": "acid", "instance": 2}]))
    assert not spec.notes
    w = spec.wiring()
    assert w.run == ("a", "b", "c") and w.placed == () and w.backdrop == "b"
    assert w.wires == (G.Wire("pattern", "kaleido.image"), G.Wire("kaleido", "shape.faces"),
                       G.Wire("history", "palette.image"), G.Wire("palette", "output.2.image"))
    assert G.read_graph(section(("frame", "fx.image"))).wiring().run == ()
    assert G.read_graph(section(("hands", "output.2.hands"))).wiring().run is None
    assert G.Wiring().run is None


def v4_sources() -> list[tuple[str, Path]]:
    """Every factory preset file (dial's too) and every fixture under
    tests/fixtures/presets/ and tests/fixtures/merge-31-32/, as (kind, path)
    — but a `/5` fixture (plan 33 T4's proofs), which no build before plan
    33 reads and `test_a_free_fixture_saves_as_five` holds instead."""
    out = [("factory", p) for p in sorted(LIBRARY.glob("*.json"))]
    for kind, folder in SOURCES.items():
        out += [(kind, p) for p in sorted(folder.glob("*.json"))
                if json.loads(p.read_text()).get("schema") != "hyperspace.preset/5"]
    return out


def test_a_free_fixture_saves_as_five(tmp_path):
    """Plan 33 T4's proof presets say what `/4` cannot (a channel through
    effects onto the faces, under the scene, at two sizes), and T5's a
    switch: loaded and saved untouched they stay `/5`, their graph section
    as written."""
    for k, name in enumerate(("media-chain-faces", "media-chain-backdrop",
                              "branch-two-sizes", "switch-faces")):
        path = SOURCES["presets"] / f"{name}.json"
        doc = json.loads(saved_bytes(tmp_path / str(k), "presets", path))
        assert doc["schema"] == "hyperspace.preset/5", name
        assert doc["graph"] == json.loads(path.read_text())["graph"], name


def saved_bytes(home: Path, kind: str, path: Path) -> bytes:
    """`path` loaded into a scratch library at `home` (a fixture copied in
    as a user's preset) and saved untouched under its own name: the bytes
    on disk. The app's registry, library, router and presets
    (`test_plan31_wiring.make_app`). Uses nothing plan 33 added, so the
    same function run against the base build records its bytes."""
    from test_plan31_wiring import make_app

    home.mkdir(parents=True, exist_ok=True)
    os.environ["HYPERSPACE_HOME"] = str(home)       # (the autouse fixture puts it back)
    if kind != "factory":
        (home / "presets").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, home / "presets" / path.name)
    app = make_app(home)
    app.lib.load("presets", path.stem)
    return app.presets.save_as(path.stem).read_bytes()


def record_saves(out: Path, scratch: Path) -> None:
    """Write each source's saved bytes under `out` as `<kind>--<file>`."""
    out.mkdir(parents=True, exist_ok=True)
    for k, (kind, path) in enumerate(v4_sources()):
        (out / f"{kind}--{path.name}").write_bytes(saved_bytes(scratch / str(k), kind, path))


def test_an_untouched_v4_preset_saves_byte_identical(tmp_path):
    """Review Focus 1 (R4, R10): every factory preset and every fixture,
    loaded into a scratch library and saved untouched on this build, is the
    file the base build (plan-31-32-integration @ 3547a7a) writes for the
    same input, byte for byte — so the second Mac, on the older build,
    keeps reading it — and no saved file carries a plan-33 word.

    The base's bytes are checked in under tests/fixtures/plan33-v4-saves/,
    recorded once by running this module's `record_saves` against a
    checkout of 3547a7a (`git worktree add --detach <scratch>/base 3547a7a`,
    then from this hyperspace-python, with the base's package and tests
    first on the path: ``PYTHONPATH=<scratch>/base/hyperspace-python:
    <scratch>/base/hyperspace-python/tests python`` importing this file by
    its path and calling ``record_saves(SAVES, <scratch>/homes)``; the
    worktree removed after). The sources are this tree's: no library file
    or fixture changed since 3547a7a."""
    sources = v4_sources()
    assert len(sources) >= 25 + 11 + 2
    assert sorted(p.name for p in SAVES.glob("*.json")) == sorted(
        f"{kind}--{path.name}" for kind, path in sources)
    for k, (kind, path) in enumerate(sources):
        got = saved_bytes(tmp_path / str(k), kind, path)
        want = (SAVES / f"{kind}--{path.name}").read_bytes()
        assert got == want, f"{kind}/{path.name}"
        doc = json.loads(got)
        assert doc["schema"] != "hyperspace.preset/5", path.name
        graph = doc.get("graph") or {}
        assert not [n for n in graph.get("nodes", []) if n.get("kind") == "switch"], path.name
        for w in graph.get("wires", []):
            assert G.wire_node_kind(w["from"]) not in ("frame", "pattern", "switch"), path.name
            into = G.wire_node_kind(w["to"].rpartition(".")[0])
            assert into not in ("fx", "shape", "pattern", "backdrop", "switch"), path.name
        assert "switch" not in json.dumps(doc.get("routes", [])), path.name


def _module_run(app, module: str) -> tuple[str, ...]:
    """The run an fx module says alone: its values over the fx group's
    defaults, read as the migration reads a preset's."""
    from hyperspace import graphmigrate as M
    from hyperspace.library import _module_values

    doc = app.lib.read("fx", module)
    values = app.lib.resolved("fx", _module_values("fx", doc))
    out, _ = M.migrate({"values": values}, app.presets.graph.specs())
    return G.run_of(G.read_graph(out["graph"]))


def test_loading_an_fx_module_replaces_the_run(tmp_path):
    """R12: a party preset, then the mandala module — the graph's main run
    is mandala's (its effects on, in its order), not the preset's; the
    module's values landed; the save says it in /4 terms."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.load("presets", "party-acid")
    gs = app.presets.graph
    acid_run = G.run_of(gs.spec)
    want = _module_run(app, "mandala")
    assert want and want != acid_run and {"plasma", "kaleido"} <= set(want)
    app.lib.load("fx", "mandala")
    assert G.run_of(gs.spec) == want
    assert gs.spec.wiring().run == want
    assert app.reg["fx.kaleido.order"].value == 8 and app.lib.current("fx") == "mandala"
    # the save says it in /4 terms: no free word, the run as orders
    doc = app.presets.document("after")
    assert doc["schema"] != "hyperspace.preset/5"
    assert "graph" not in doc


def test_loading_an_fx_module_keeps_branches(tmp_path):
    """R12: a section with a branch (`media.a → acid.2 → output.2.image`)
    and a run, then a module — the run is the module's and the branch, its
    node and every other wire stay."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    branch = [("media.a", "acid.2.image"), ("acid.2", "output.2.image")]
    doc = {"schema": "hyperspace.preset/4", "name": "t",
           "graph": section(*branch, ("frame", "warp.image"), ("warp", "fx.image"),
                            nodes=[{"kind": "effect", "file": "acid", "instance": 2}]),
           "values": {"fx.acid.2.on": True, "fx.warp.on": True}}
    assert app.presets.load_doc(doc) == []
    gs = app.presets.graph
    assert G.run_of(gs.spec) == ("warp",)
    app.lib.load("fx", "mandala")
    assert G.run_of(gs.spec) == _module_run(app, "mandala")
    for a, b in branch:
        assert G.Wire(a, b) in gs.spec.wires
    assert {"kind": "effect", "file": "acid", "instance": 2} in gs.free_doc()["nodes"]
    assert G.Wire("warp", "fx.image") not in gs.spec.wires


def test_a_module_lands_its_run_over_a_refused_wire_and_says_when_it_cannot(tmp_path):
    """A loaded graph with a refused wire (said at its load) still takes an
    fx module's run, the refused wire kept in the section as the file had
    it; a graph this build cannot read at all takes none, and a note says
    so plainly."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    doc = {"schema": "hyperspace.preset/4", "name": "t", "values": {"fx.warp.on": True},
           "graph": section(("frame", "warp.image"), ("warp", "fx.image"),
                            ("ghost", "output.1.image"))}
    app.presets.load_doc(doc)
    assert any("ghost makes geometry" in n for n in app.presets.notes)
    gs = app.presets.graph
    app.lib.load("fx", "mandala")
    assert G.run_of(gs.spec) == _module_run(app, "mandala")
    assert {"from": "ghost", "to": "output.1.image"} in gs.free_doc()["wires"]
    app.presets.load_doc({"schema": "hyperspace.preset/4", "name": "u", "values": {},
                          "graph": {"nodes": [{"kind": "teapot"}]}})
    app.lib.load("fx", "mandala")
    assert gs.spec is None
    assert app.presets.notes[-1] == ("fx module mandala: its run is not applied — the "
                                     "preset's graph is not one this build reads")


def test_the_module_hook_survives_a_hot_reload(tmp_path):
    """A `Presets` re-classed by a hot reload is never re-initialised (and a
    Library from before has no apply hooks): the next preset load registers
    the fx module hook again, so a module after it still replaces the run."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.__dict__.pop("_apply_hooks", None)          # as before the hook existed
    app.lib.load("presets", "party-acid")
    app.lib.load("fx", "mandala")
    assert G.run_of(app.presets.graph.spec) == _module_run(app, "mandala")


def test_a_driven_channel_choice_loads_as_a_switch_and_saves_as_five(tmp_path):
    """R19 (R14 → T5, row 350): a route on `view.media` or `backdrop.channel`
    loads as a switch over the eight channels into `pattern.media` /
    `backdrop.image`, the route retargeted onto its `select`, the select at
    the old choice — and, saved untouched, the preset is /5 (row 347: /4
    cannot say a switch), its graph the switches and their wires and its
    routes on the selects. These two sources left the byte-identical set
    for this; the pictures are tests/test_graph_switch.py's."""
    from test_plan31_wiring import make_app

    want = {"driven-channels": (("switch", "pattern.media", "view.media", 2),
                                ("switch.2", "backdrop.image", "backdrop.channel", 3)),
            "driven-media-v2": (("switch", "pattern.media", "view.media", 2),)}
    for k, (name, switches) in enumerate(want.items()):
        app = make_app(tmp_path / str(k))
        src = json.loads((DRIVEN / f"{name}.json").read_text())
        assert app.presets.load_doc(src) == [] and app.presets.notes == [], name
        assert [b.target for b in app.router.table.routes()] == [
            f"{sw}.select" for sw, *_ in switches]
        free = app.presets.graph.free_doc()
        for sw, end, old, pick in switches:
            assert app.reg[f"{sw}.select"].value == pick, (name, sw)
            assert {"from": sw, "to": end} in free["wires"]
            for i, c in enumerate("abcdefgh", 1):
                assert {"from": f"media.{c}", "to": f"{sw}.in{i}"} in free["wires"]
            assert not [w for w in free["wires"] if w["to"] == end and w["from"] != sw]
        doc = app.presets.document(name)
        assert doc["schema"] == "hyperspace.preset/5", name
        assert [n for n in doc["graph"]["nodes"] if n["kind"] == "switch"] == [
            {"kind": "switch", **({"instance": 2} if sw == "switch.2" else {})}
            for sw, *_ in switches]
        assert [r["target"] for r in doc["routes"]] == [f"{sw}.select" for sw, *_ in switches]
        for sw, _, _, pick in switches:
            assert doc["values"][f"{sw}.select"] == pick
    assert sorted(p.name for p in DRIVEN.glob("*.json")) == [f"{n}.json" for n in sorted(want)]
    assert not [p for p in SAVES.glob("plan33--*.json")]


def test_an_effect_switched_on_in_no_run_adds_nothing_and_saves_as_five(tmp_path):
    """R13 (row 341): an effect switched on that no wire puts in a run draws
    nothing and is said nowhere in /4 — a later save is /5, the run as it
    was."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.load("presets", "party-acid")
    gs = app.presets.graph
    run = G.run_of(gs.spec)
    off = next(n for n in sorted(app.reg.fx_state.specs)
               if n not in run and not app.reg[f"fx.{n}.on"].value)
    app.reg[f"fx.{off}.on"].set(True)
    assert G.run_of(gs.spec) == run
    doc = app.presets.document("after")
    assert doc["schema"] == "hyperspace.preset/5" and G.run_of(G.read_graph(doc["graph"])) == run


def _loaded(ctx, tmp_path, slug: str | None = None, doc: dict | None = None):
    """The app's presets over a scratch library, a renderer attached as
    app.py attaches it, and `slug` (or `doc`) loaded."""
    from test_plan31_wiring import make_app

    from hyperspace.render import Renderer

    app = make_app(tmp_path)
    r = Renderer(ctx, fx=app.reg.fx_state)
    app.presets.graph.attach(r)
    if slug is not None:
        app.lib.load("presets", slug)
    if doc is not None:
        assert app.presets.load_doc(doc) == []
    return app, r


def _effect_nodes(g) -> list:
    return [n for n in g.nodes.values() if isinstance(n, G.Effect)]


moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def test_only_wired_effects_have_nodes(ctx, tmp_path):
    """PARTY-ACID migrated: the scene pipeline's effect nodes are exactly
    its run (the effects on with mix > 0, in its order), not one per file."""
    from test_outputs import run, views

    from hyperspace.outputs import Switches

    app, r = _loaded(ctx, tmp_path, "party-acid")
    want = G.run_of(app.presets.graph.spec)
    assert want and len(want) < len(app.reg.fx_state.specs)
    run(ctx, r, views(ctx, Switches()), frames=1)
    g = r._graph
    assert [e.effect for e in g.nodes["fx"].effects] == list(want) == list(g.run)
    assert sorted(n.effect for n in _effect_nodes(g)) == sorted(want)


def test_the_run_order_is_the_wire_order(ctx, tmp_path):
    """`frame → wobble → acid → fx.image`: wobble runs before acid however
    their orders sort them."""
    from test_outputs import run, views

    from hyperspace.outputs import Switches

    doc = {"schema": "hyperspace.preset/2", "name": "t",
           "graph": section(("frame", "wobble.image"), ("wobble", "acid.image"),
                            ("acid", "fx.image")),
           "values": {"fx.acid.on": True, "fx.acid.order": 1, "fx.wobble.on": True,
                      "fx.wobble.order": 90}}
    _, r = _loaded(ctx, tmp_path, doc=doc)
    run(ctx, r, views(ctx, Switches()), frames=1)
    g = r._graph
    assert [e.effect for e in g.nodes["fx"].effects] == ["wobble", "acid"]
    order = [n.name for n in g.order]
    assert order.index("wobble") < order.index("acid")
    assert r.stats["effects"] == ["wobble", "acid"]


def test_an_unreached_effect_is_never_run(ctx, tmp_path):
    """`media.a → acid.2.image` alone: acid.2 reaches nothing, so it has no
    node and never runs, on or not (row 349) — and no channel is read for it."""
    from test_outputs import run, views

    from hyperspace.outputs import Switches

    doc = {"schema": "hyperspace.preset/2", "name": "t",
           "graph": section(("media.a", "acid.2.image"),
                            nodes=[{"kind": "effect", "file": "acid", "instance": 2}]),
           "values": {"fx.acid.2.on": True, "fx.acid.on": True}}
    app, r = _loaded(ctx, tmp_path, doc=doc)
    assert app.reg["fx.acid.2.on"].value
    run(ctx, r, views(ctx, Switches()), frames=2)
    g = r._graph
    assert "acid.2" not in {n.effect for n in _effect_nodes(g)}
    assert "acid.2" not in r.stats["effects"] and "acid" in r.stats["effects"]
    assert not [n for n in g.nodes if n.startswith("media.")]


def test_order_changes_do_not_rebuild_the_graph(ctx, tmp_path):
    """`fx.acid.order` (declared until T7) moves nothing — nor does its
    target: the run is its wires, and the graph keys on the effect files
    present."""
    from test_outputs import run, views

    from hyperspace.outputs import Switches

    app, r = _loaded(ctx, tmp_path, "party-acid")
    vs = views(ctx, Switches())
    run(ctx, r, vs, frames=1)
    g = r._graph
    app.reg["fx.acid.order"].set(0 if app.reg["fx.acid.order"].value else 7)
    app.reg["fx.acid.target"].set(1 - app.reg["fx.acid.target"].value)
    run(ctx, r, vs, frames=1)
    assert r._graph is g


def test_a_wired_effect_whose_file_goes_reads_through_and_returns(ctx, tmp_path):
    """Review Focus 3: `acid.glsl` removed from the effects folder while
    acid is wired in the run — the folder watch picks it up, the graph is
    built again with no acid node (the run reads through it: the picture is
    the run without acid), a dormant note names it, nothing raises and the
    wires stay; put back, the node is back."""
    import numpy as np
    from test_outputs import run, views

    from hyperspace.fx import FX_DIR, FxState
    from hyperspace.outputs import Switches
    from hyperspace.render import Renderer

    folder = tmp_path / "fx"
    shutil.copytree(FX_DIR, folder)
    st = FxState(folder)
    for n in ("acid", "warp"):
        st.values[n]["on"] = True
    r = Renderer(ctx, fx=st)
    spec = G.read_graph(section(("frame", "warp.image"), ("warp", "acid.image"),
                                ("acid", "fx.image")))
    r.wiring = spec.wiring()
    vs = views(ctx, Switches())
    with_acid = run(ctx, r, vs, frames=2)[0]
    assert [e.effect for e in r._graph.nodes["fx"].effects] == ["warp", "acid"]
    gone = folder / "acid.glsl"
    kept = gone.read_bytes()
    gone.unlink()
    assert "acid" in st.poll() and "acid" not in st.specs
    got = run(ctx, r, vs, frames=2)[0]
    g = r._graph
    assert [e.effect for e in g.nodes["fx"].effects] == ["warp"]
    assert g.dormant["acid"].endswith("no acid effect in this build")
    assert r.wiring.run == ("warp", "acid") and G.Wire("acid", "fx.image") in spec.wires
    assert not np.array_equal(got, with_acid)
    # the run without acid, from a state of its own stepped the same frames
    # (the clocks: two frames, then two more from the same start)
    bare = FxState(folder)
    bare.values["warp"]["on"] = True
    plain = Renderer(ctx, fx=bare)
    plain.wiring = G.read_graph(section(("frame", "warp.image"),
                                        ("warp", "fx.image"))).wiring()
    pvs = views(ctx, Switches())
    run(ctx, plain, pvs, frames=2)
    assert np.array_equal(got, run(ctx, plain, pvs, frames=2)[0])
    gone.write_bytes(kept)
    os.utime(gone, (1, 1))                             # a stamp the watch has not seen
    assert "acid" in st.poll() and "acid" in st.specs
    st.values["acid"]["on"] = True
    run(ctx, r, vs, frames=1)
    assert [e.effect for e in r._graph.nodes["fx"].effects] == ["warp", "acid"]
    assert "acid" not in r._graph.dormant
