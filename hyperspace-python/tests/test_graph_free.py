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

import copy
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
    33 reads and `test_a_free_fixture_saves_as_six` holds instead, and a
    `/6` one (plan 35 T3's wired frames), which none before plan 35 reads."""
    out = [("factory", p) for p in sorted(LIBRARY.glob("*.json"))]
    for kind, folder in SOURCES.items():
        out += [(kind, p) for p in sorted(folder.glob("*.json"))
                if json.loads(p.read_text()).get("schema") not in ("hyperspace.preset/5",
                                                                    "hyperspace.preset/6")]
    return out


# ruling R10 (plan 35 T3 review): the lowest schema that loses nothing — a
# `/5` file re-saved untouched is the bytes a plan 33/34 build writes, so the
# other Mac keeps reading it. Those bytes were recorded once by the base
# build (0cbbc15, `git archive`d) loading and saving each source untouched
V5_SAVES = ROOT / "tests" / "fixtures" / "plan35-v5-saves"
V5_SOURCES = ("media-chain-faces", "media-chain-backdrop", "branch-two-sizes", "switch-faces",
              "delay-trails")


def test_an_untouched_v5_preset_saves_byte_identical(tmp_path):
    """Plan 33 T4's proof presets (a channel through effects onto the
    faces, under the scene, at two sizes), T5's switch and plan 34's
    trails: loaded and saved untouched, each is `/5` again, byte for byte
    what the plan 33/34 build writes (R10, superseding row 385's "nothing
    writes /5")."""
    assert sorted(p.stem for p in V5_SAVES.glob("*.json")) == sorted(V5_SOURCES)
    for k, name in enumerate(V5_SOURCES):
        path = SOURCES["presets"] / f"{name}.json"
        got = saved_bytes(tmp_path / str(k), "presets", path)
        assert json.loads(got)["schema"] == "hyperspace.preset/5", name
        assert got == (V5_SAVES / f"{name}.json").read_bytes(), name


def _five_rig(tmp_path, name):
    from test_plan31_wiring import make_app

    (tmp_path / "presets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCES["presets"] / f"{name}.json", tmp_path / "presets" / f"{name}.json")
    app = make_app(tmp_path)
    app.lib.load("presets", name)
    return app


def test_an_edited_v5_preset_sayable_in_v5_saves_v5(tmp_path):
    """R10: an edit plan 33's words can say (branch-two-sizes' second
    picture taken off output 2) saves `/5`, its graph the frame's round trip
    in the old ids — no marker, no new id — which reads back as the edited
    frame."""
    from hyperspace import graphmigrate as M

    app = _five_rig(tmp_path, "branch-two-sizes")
    gs = app.presets.graph
    wired = copy.deepcopy(gs.free_doc())
    cut = [w for w in wired["wires"] if w["to"] != "output.2.image"]
    assert len(cut) == len(wired["wires"]) - 1
    edited = {**wired, "wires": cut}
    gs.land(G.read_graph(edited), copy.deepcopy(edited))
    doc = app.presets.document("branch-two-sizes")
    assert doc["schema"] == "hyperspace.preset/5"
    graph = doc["graph"]
    assert G.FRAME_KEY not in graph
    assert not any(w["to"].startswith("output.2.") for w in graph["wires"])
    assert {"from": "frame", "to": "fx.image"} in graph["wires"] or any(
        w["from"] == "frame" for w in graph["wires"])
    assert "backdrop.history" in doc["values"]
    again, _ = M.migrate({"values": doc["values"], "graph": graph}, gs.specs())
    assert G.read_graph(again["graph"]).to_json() == G.read_graph(edited).to_json()


def test_a_frame_edit_needing_new_words_saves_v6(tmp_path):
    """R10: `/6` only for what the wired frame alone can say — a copy, a
    `ground`, a picture into All outputs that is not the look-back's run, a
    capture deleted."""
    app = _five_rig(tmp_path, "branch-two-sizes")
    gs = app.presets.graph
    wired = copy.deepcopy(gs.free_doc())
    head = next(w for w in wired["wires"] if w["to"] == "output.all.image")
    for name, wires in {
            "channel into All outputs": [w if w is not head else
                                         {"from": "channel.a", "to": "output.all.image"}
                                         for w in wired["wires"]],
            "no capture": [w for w in wired["wires"] if w["to"] != "lookback.capture"],
            "ground": [*wired["wires"], {"from": "ground", "to": "output.3.image"}]}.items():
        edited = {**wired, "wires": wires}
        gs.land(G.read_graph(edited), copy.deepcopy(edited))
        doc = app.presets.document("branch-two-sizes")
        assert doc["schema"] == "hyperspace.preset/6", name
        assert doc["graph"] == G.read_graph(edited).to_json(), name


def test_the_round_trip_is_canonical(tmp_path):
    """Plan 35 M (row 384, Review Focus 4): for every fixture and every one
    of the 38 sources, the wired frame the load landed, put back below `/6`
    (`legacy_section`, its values by `legacy_values`) and loaded again,
    is the same wired frame — and one `/4` cannot say is given back as it
    is, `legacy_values` reading it as needing `/6`."""
    from test_plan31_wiring import make_app

    from hyperspace import graphmigrate as M

    sources = [*v4_sources(), *((kind, p) for kind, folder in SOURCES.items()
                                for p in sorted(folder.glob("*.json"))
                                if (kind, p) not in v4_sources())]
    said = 0
    for k, (kind, path) in enumerate(sources):
        home = tmp_path / str(k)
        if kind != "factory":
            (home / "presets").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, home / "presets" / path.name)
        app = make_app(home)
        app.lib.load("presets", path.stem)
        gs = app.presets.graph
        wired = gs.free_doc()
        assert wired[G.FRAME_KEY] == G.WIRED_FRAME, path.name
        doc = app.presets.document(path.stem)
        specs, driven = gs.specs(), M.targets(doc)
        back = M.legacy_section(wired)
        if doc["schema"] == M.WIRED_SCHEMA:
            assert M.needs_free(wired, doc["values"], driven, specs), path.name
            assert M.unwired(wired, specs) is None, path.name
            continue
        said += 1
        again = {k: v for k, v in doc.items() if k != "graph"}
        if doc["schema"] == M.FREE_SCHEMA:
            # (R10: a `/5` save is the frame's round trip in plan 33's words)
            assert M.unwired(wired, specs) is not None, path.name
            back = doc["graph"]
        if back is not None:
            again["graph"] = back
        out, _ = M.migrate(again, specs)
        assert (G.read_graph(out["graph"]).to_json()
                == G.read_graph(wired).to_json()), path.name
    assert said >= 38


def test_an_edited_frame_saves_as_v6(tmp_path):
    """Plan 35 M (Review Focus 4): any edit to the frame fails the round
    trip — the capture's wire deleted, or a channel in place of the run's
    last wire into All outputs — so the section `needs_free` and the save
    is `/6`; untouched, the same preset saves below it."""
    from test_plan31_wiring import make_app

    from hyperspace import graphmigrate as M

    app = make_app(tmp_path)
    app.lib.load("presets", "party-trip")
    gs = app.presets.graph
    wired = copy.deepcopy(gs.free_doc())
    assert app.presets.document("party-trip")["schema"] != M.WIRED_SCHEMA
    last = next(w for w in wired["wires"] if w["to"] == "output.all.image")
    edits = {"capture": [w for w in wired["wires"]
                         if (w["from"], w["to"]) != ("scene", "lookback.capture")],
             "channel": [w if w is not last else {"from": "channel.a", "to": "output.all.image"}
                         for w in wired["wires"]]}
    for name, wires in edits.items():
        edited = {**wired, "wires": wires}
        assert len(wires) == len(wired["wires"]) - (name == "capture"), name
        doc = app.presets.document("party-trip")
        assert M.needs_free(edited, doc["values"], M.targets(doc), gs.specs()), name
        gs.land(G.read_graph(edited), copy.deepcopy(edited))
        saved = app.presets.document("party-trip")
        assert saved["schema"] == "hyperspace.preset/6", name
        assert saved["graph"] == G.read_graph(edited).to_json(), name


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
    return main_run(G.read_graph(out["graph"]))


def main_run(spec) -> tuple[str, ...]:
    """The main run of a wired frame (plan 35 T3: every load's): the
    effects from the look-back into All outputs."""
    return G.run_of(spec, "lookback", "output.all.image")


def test_loading_an_fx_module_replaces_the_run(tmp_path):
    """R12: a party preset, then the mandala module — the graph's main run
    is mandala's (its effects on, in its order), not the preset's; the
    module's values landed; the save says it in /4 terms."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.load("presets", "party-acid")
    gs = app.presets.graph
    acid_run = main_run(gs.spec)
    want = _module_run(app, "mandala")
    assert want and want != acid_run and {"plasma", "kaleido"} <= set(want)
    app.lib.load("fx", "mandala")
    assert main_run(gs.spec) == want
    # (its order is no param since T7: held for a /4 save, the module's)
    assert gs.held_values()["fx.kaleido.order"] == 8.0 and app.lib.current("fx") == "mandala"
    assert "fx.kaleido.order" not in app.reg
    # the save says it in /4 terms: no free word, the run as orders (plan
    # 35: the module's run where the old one stood — the round trip holds)
    doc = app.presets.document("after")
    assert doc["schema"] not in ("hyperspace.preset/5", "hyperspace.preset/6")
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
    assert main_run(gs.spec) == ("warp",)
    app.lib.load("fx", "mandala")
    assert main_run(gs.spec) == _module_run(app, "mandala")
    for a, b in branch:                                 # (in the new ids: plan 35 V2)
        assert G.Wire(G.new_id(a), b) in gs.spec.wires
    assert {"kind": "effect", "file": "acid", "instance": 2} in gs.free_doc()["nodes"]
    assert G.Wire("warp", "output.all.image") not in gs.spec.wires


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
    # (plan 35 V2: the old `ghost` is `hands` now, said as such)
    assert any("hands makes geometry" in n for n in app.presets.notes), app.presets.notes
    gs = app.presets.graph
    app.lib.load("fx", "mandala")
    assert main_run(gs.spec) == _module_run(app, "mandala")
    assert {"from": "hands", "to": "output.1.image"} in gs.free_doc()["wires"]
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
    assert main_run(app.presets.graph.spec) == _module_run(app, "mandala")


def test_a_module_load_keeps_a_faces_run_that_shares_an_effect(tmp_path):
    """Final review (1): a faces run `pattern → acid → shape.faces`, then
    the `acid` module (acid on, no faces run of its own). The faces run
    keeps acid; the main run is the module's minus acid, closed over the
    gap; no wire is refused and no note is lost."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    doc = {"schema": "hyperspace.preset/5", "name": "t",
           "graph": section(("frame", "fx.image"), ("pattern", "acid.image"),
                            ("acid", "shape.faces")),
           "values": {"fx.acid.on": True}}
    assert app.presets.load_doc(doc) == []
    gs = app.presets.graph
    assert G.run_of(gs.spec, "pattern", "shape.faces") == ("acid",)
    want = tuple(n for n in _module_run(app, "acid") if n != "acid")
    assert want and "acid" in _module_run(app, "acid")
    app.lib.load("fx", "acid")
    assert G.run_of(gs.spec, "pattern", "shape.faces") == ("acid",)
    assert main_run(gs.spec) == want
    assert gs.spec.notes == ()
    assert app.presets.notes == []


MISSING_RUN = (("frame", "foo.image"), ("foo", "acid.image"), ("acid", "fx.image"))


def test_a_run_reads_through_an_effect_file_this_machine_lacks():
    """R27: `frame → foo → acid → fx.image` with no `foo` on this machine
    is no refused run: the section's run keeps foo (no note), and the
    renderer draws `frame → acid → fx.image`, foo dormant and named."""
    from test_graphview import views

    from hyperspace.outputs import Switches
    spec = G.read_graph(section(*MISSING_RUN), effects={"acid", "wobble"})
    assert spec.notes == ()
    assert G.run_of(spec) == ("foo", "acid")
    g = G.build_graph(views(Switches()), spec.wiring(), effects=("acid", "wobble"))
    assert g.run == ("acid",)
    assert [e.effect for e in G._effects_of(g.outputs[0].inputs["image"].inputs["image"])
            ] == ["acid"]
    assert "no foo effect in this build" in g.dormant["foo"]
    # a wire on a missing effect that is no run's stays refused
    branch = G.read_graph(section(("frame", "fx.image"), ("media.a", "foo.image"),
                                  ("foo", "output.2.image")), effects={"acid"})
    assert len(branch.notes) == 2 and all("no foo effect" in n for n in branch.notes)


def test_the_missing_effects_wires_survive_a_save(tmp_path):
    """R27: a preset whose run names `foo`, loaded on a machine without
    it, loads with no note and saves its wires unchanged, so the Mac that
    has foo still has its run (R10: `/5`, the file's own section)."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    doc = {"schema": "hyperspace.preset/5", "name": "t", "graph": section(*MISSING_RUN),
           "values": {"fx.acid.on": True}}
    assert app.presets.load_doc(doc) == [] and app.presets.notes == []
    assert main_run(app.presets.graph.spec) == ("foo", "acid")
    out = app.presets.document("t")
    # (R10: untouched, the file's own section, `/5`, as the base wrote it)
    assert out["schema"] == "hyperspace.preset/5"
    assert out["graph"]["wires"] == section(*MISSING_RUN)["wires"]


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
                assert {"from": f"channel.{c}", "to": f"{sw}.in{i}"} in free["wires"]
            assert not [w for w in free["wires"] if w["to"] == end and w["from"] != sw]
        doc = app.presets.document(name)
        assert doc["schema"] == "hyperspace.preset/5", name          # (R10)
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
    run = main_run(gs.spec)
    off = next(n for n in sorted(app.reg.fx_state.specs)
               if n not in run and not app.reg[f"fx.{n}.on"].value)
    app.reg[f"fx.{off}.on"].set(True)
    assert main_run(gs.spec) == run
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
    want = main_run(app.presets.graph.spec)
    assert want and len(want) < len(app.reg.fx_state.specs)
    run(ctx, r, views(ctx, Switches()), frames=1)
    g = r._graph
    # (plan 35: the wired frame's end reads the run — `g.run`, no `fx` node)
    assert list(want) == list(g.run)
    end = g.outputs[0].inputs["image"]
    assert [e.effect for e in G._effects_of(end.inputs["image"])] == list(want)
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
    assert list(g.run) == ["wobble", "acid"]
    end = g.outputs[0].inputs["image"]
    assert [e.effect for e in G._effects_of(end.inputs["image"])] == ["wobble", "acid"]
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
    end = r._graph.outputs[0].inputs["image"]          # (plan 35 T4: where `fx` was)
    assert [e.effect for e in G._effects_of(end.inputs["image"])] == ["warp", "acid"]
    gone = folder / "acid.glsl"
    kept = gone.read_bytes()
    gone.unlink()
    assert "acid" in st.poll() and "acid" not in st.specs
    got = run(ctx, r, vs, frames=2)[0]
    g = r._graph
    assert [e.effect for e in G._effects_of(g.outputs[0].inputs["image"].inputs["image"])
            ] == ["warp"]
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
    end = r._graph.outputs[0].inputs["image"]          # (plan 35 T4: where `fx` was)
    assert [e.effect for e in G._effects_of(end.inputs["image"])] == ["warp", "acid"]
    assert "acid" not in r._graph.dormant


# ---------------------------------------------------------------- no shortcut in a free section
# The owner, 2026-10-24: a glimmer wired only `zoomblur → glimmer.image`
# drew on the output (split_wires shortened the wire to D1's `after
# zoomblur`) while GRAPH drew it faint and the FX page said "reaches
# nothing". In a section with a `frame` run a wire is a wire: nothing comes
# out of glimmer, so it reaches nothing and is not drawn — all three agree.

GLIMMER = SOURCES["presets"] / "glimmer-bug.json"


def _glimmer_section(swap: bool = False) -> dict:
    """The owner's saved section; `swap`: `glimmer → switch.in1` in place
    of `zoomblur → switch.in1`."""
    sec = copy.deepcopy(json.loads(GLIMMER.read_text())["graph"])
    if swap:
        sec["wires"] = [({"from": "glimmer", "to": "switch.in1"}
                         if w == {"from": "zoomblur", "to": "switch.in1"} else w)
                        for w in sec["wires"]]
    return sec


def _glimmer_graph(sec: dict):
    from test_graphview import views

    from hyperspace.outputs import Switches
    spec = G.read_graph(sec)
    return spec, G.build_graph(views(Switches()), spec.wiring(),
                                 effects=("glimmer", "zoomblur", "displace"))


def test_the_owners_glimmer_with_no_output_is_unreached_and_not_drawn():
    from hyperspace import graphview, ui_fx

    spec, g = _glimmer_graph(_glimmer_section())
    assert not spec.notes
    assert "glimmer" not in {e.name for e in spec.wiring().placed}
    assert "glimmer" in graphview.unreached(spec)
    assert "glimmer" in dict(ui_fx.groups(spec))[ui_fx.UNREACHED]
    assert "glimmer" not in {n.effect for n in _effect_nodes(g)}
    assert "zoomblur" in {n.effect for n in _effect_nodes(g)}


def test_wiring_its_output_then_draws_it():
    from hyperspace import graphview, ui_fx

    spec, g = _glimmer_graph(_glimmer_section(swap=True))
    assert not spec.notes
    assert "glimmer" not in graphview.unreached(spec)
    assert "glimmer" in dict(ui_fx.groups(spec))[ui_fx.BACKDROP]
    assert ui_fx.UNREACHED not in dict(ui_fx.groups(spec))
    assert "glimmer" in {n.effect for n in _effect_nodes(g)}


def test_an_explicit_after_still_places_in_a_free_section():
    spec = G.read_graph(section(("frame", "fx.image"),
                                nodes=[{"kind": "effect", "file": "palette", "after": "hands"},
                                       {"kind": "effect", "file": "acid", "instance": 2,
                                        "after": "scene"}]))
    assert not spec.notes
    placed = {e.name: e.where for e in spec.wiring().placed}
    assert placed == {"palette": ("after", "hands"), "acid.2": ("after", "scene")}
    from test_graphview import views

    from hyperspace.outputs import Switches
    g = G.build_graph(views(Switches()), spec.wiring(), effects=("palette", "acid", "acid.2"))
    assert {"palette", "acid.2"} <= {n.effect for n in _effect_nodes(g)}
