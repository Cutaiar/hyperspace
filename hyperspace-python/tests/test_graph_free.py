"""Plan 33 G and R: the free graph's vocabulary, then the run from wires.

New wire ends (`frame`, `fx.image`, `pattern`, `shape.faces`,
`backdrop.image`, `switch`), a wire from a channel into an effect as a
branch instead of a refusal, and `reaches` / `run_of` read off the wires
(data only). Then T3: the renderer builds each pipeline's run from the
preset graph's wires `frame → … → fx.image`, an effect on no wire has no
node. Row 394 (the owner, 2026-10-25): every preset, whatever its schema,
saves as `/6` and that save is a fixed point — what replaced the
byte-identical-to-an-older-build saves (Review Focus 1, R10). The pictures
are test_golden_frames.py's.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from hyperspace import graph as G
from hyperspace import graphview
from hyperspace.graphmigrate import wired_wiring

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
# plan 36 T3: the factory presets' sources (the factory files are their `/7`)
LIBRARY = ROOT / "tests" / "fixtures" / "factory-sources" / "presets"
SOURCES = {"presets": ROOT / "tests" / "fixtures" / "presets",
           "merge-31-32": ROOT / "tests" / "fixtures" / "merge-31-32",
           # R15 (final review): a /4 whose GRAPH layout is in the canvas's
           # old ids (render:media.a, render:hands …), as the owner's are
           "old-layout": ROOT / "tests" / "fixtures" / "old-canvas-layout"}
# R14 → R19: a route on each channel choice (a /4 and a /2): they load
# with a switch (T5) and save as /6 with it (row 394)
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


def old_sources() -> list[tuple[str, Path]]:
    """Every preset file this tree holds in an older schema or the newest,
    as (kind, path): the factory's sources (dial's too), every fixture under
    tests/fixtures/presets/, merge-31-32/, old-canvas-layout/ and
    plan33-driven/, and the bytes older builds saved, kept from the
    byte-identical tests row 394 retired (plan33-v4-saves/: the base build's
    `/2`–`/4` saves; plan35-v5-saves/: plan 33/34's `/5`) — `/2` to `/6`."""
    out = [("factory", p) for p in sorted(LIBRARY.glob("*.json"))]
    for kind, folder in {**SOURCES, "driven": DRIVEN, "v4-saves": SAVES,
                         "v5-saves": V5_SAVES}.items():
        out += [(kind, p) for p in sorted(folder.glob("*.json"))]
    return out


# the bytes plan 33/34 saved for six `/5` sources (recorded by 0cbbc15) —
# old files now, read like any other (row 394)
V5_SAVES = ROOT / "tests" / "fixtures" / "plan35-v5-saves"


def test_every_schema_is_among_the_sources():
    """The sources cover the whole ladder a load still reads: `/2` to `/6`
    (plan 39 T0: and a `/7` fixture, written in today's schema — a fixed
    point like any save)."""
    schemas = {json.loads(p.read_text())["schema"] for _, p in old_sources()}
    assert schemas - {"hyperspace.preset/7"} == {f"hyperspace.preset/{n}" for n in (2, 3, 4, 5, 6)}
    assert len(old_sources()) >= 95


def _six(raw: bytes, name: str) -> dict:
    """A save's document, checked for the newest schema in today's words."""
    doc = json.loads(raw)
    assert doc["schema"] == "hyperspace.preset/7", name
    graph = doc.get("graph")
    assert isinstance(graph, dict) and graph.get(G.FRAME_KEY) == G.WIRED_FRAME, name
    from hyperspace import graphmigrate as M

    assert not [k for k in doc["values"] if M.retired(k)], name
    lay = doc.get("layout") or {}
    assert lay == M.renamed_layout(lay), name            # today's canvas ids
    return doc


def test_every_old_preset_saves_as_six_and_is_a_fixed_point(tmp_path):
    """Row 394 (the owner, 2026-10-25: both Macs always on the newest
    schema): every preset — the factory's and every fixture, `/2` to `/6`
    — loaded into a scratch library and saved untouched is
    `hyperspace.preset/6`, its graph the wired frame, no retired id in its
    values and its GRAPH layout in today's canvas ids; and that `/6`,
    loaded and saved untouched again, is the same bytes."""
    for k, (kind, path) in enumerate(old_sources()):
        name = f"{kind}/{path.name}"
        first = saved_bytes(tmp_path / f"{k}a", kind, path)
        _six(first, name)
        again = tmp_path / f"{k}-six" / path.name
        again.parent.mkdir(parents=True)
        again.write_bytes(first)
        assert saved_bytes(tmp_path / f"{k}b", "presets", again) == first, name


def test_the_driven_channel_sources_keep_their_switches_through_six(tmp_path):
    """R19 (row 350): a route on `view.media` / `backdrop.channel` loads as a
    switch; saved, the `/6` carries the switch node, its routes on the
    select and the select at the old pick (`DRIVEN`'s two)."""
    for k, path in enumerate(sorted(DRIVEN.glob("*.json"))):
        doc = _six(saved_bytes(tmp_path / str(k), "driven", path), path.name)
        assert [n for n in doc["graph"]["nodes"] if n["kind"] == "switch"], path.name
        assert all(r["target"].endswith(".select") for r in doc["routes"]), path.name


def _five_rig(tmp_path, name):
    from test_plan31_wiring import make_app

    (tmp_path / "presets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCES["presets"] / f"{name}.json", tmp_path / "presets" / f"{name}.json")
    app = make_app(tmp_path)
    app.lib.load("presets", name)
    return app


def test_a_moved_node_in_an_old_layout_saves_in_todays_ids(tmp_path):
    """R14, row 394: the owner's glimmer-bug lands its layout in the wired
    frame's ids; a node moved on GRAPH — one the file placed, one it had no
    place for — saves `/6` with every key in today's ids (R15's old ids
    below `/6` are gone with the ladder), and reads back where it was."""
    app = _five_rig(tmp_path, "glimmer-bug")
    pr = app.presets
    assert "render:channel.a" in pr.layout and "render:media.a" not in pr.layout
    pr.layout["render:channel.a"] = [10, 20]
    pr.layout["render:hands.2"] = [30, 40]
    doc = pr.document("glimmer-bug")
    assert doc["schema"] == "hyperspace.preset/7"
    lay = doc["layout"]
    assert lay["render:channel.a"] == [10, 20] and lay["render:hands.2"] == [30, 40]
    assert not [k for k in lay if k.startswith(("render:media.", "render:ghost"))]
    assert list(lay) == sorted(lay)
    from hyperspace import graphmigrate as M

    assert M.renamed_layout(lay) == pr.layout        # and it reads back where it was


def test_an_edited_frame_saves_as_six_as_edited(tmp_path):
    """Row 394: any GRAPH edit — one plan 33's words could say (a picture
    taken off output 2), a copy, `ground`, a channel into All outputs, the
    faces' pattern taken off — saves `/6` with the edited frame as it stands, and
    no `backdrop.history` (the capture wire says it)."""
    app = _five_rig(tmp_path, "branch-two-sizes")
    gs = app.presets.graph
    wired = copy.deepcopy(gs.free_doc())
    head = next(w for w in wired["wires"] if w["to"] == "output.all.image")
    for name, wires in {
            "output 2's picture off": [w for w in wired["wires"]
                                       if w["to"] != "output.2.image"],
            "channel into All outputs": [w if w is not head else
                                         {"from": "channel.a", "to": "output.all.image"}
                                         for w in wired["wires"]],
            # (plan 36 T4: an old file's look-back off is no look-back — the
            # faces' pattern taken off instead)
            "plain faces": [w for w in wired["wires"] if w["to"] != "shape.faces"],
            "ground": [*wired["wires"], {"from": "ground", "to": "output.3.image"}]}.items():
        assert wires != wired["wires"], name
        edited = {**wired, "wires": wires}
        gs.land(G.read_graph(edited), copy.deepcopy(edited))
        doc = app.presets.document("branch-two-sizes")
        assert doc["schema"] == "hyperspace.preset/7", name
        assert doc["graph"] == G.read_graph(edited).to_json(), name
        assert "backdrop.history" not in doc["values"], name


def test_an_untouched_factory_preset_saves_as_its_load(tmp_path):
    """Row 394: party-trip untouched saves `/6`, its graph exactly the wired
    frame the load landed (`free_doc`) — the frame is the save."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.load("presets", "party-trip")
    doc = app.presets.document("party-trip")
    assert doc["schema"] == "hyperspace.preset/7"
    assert doc["graph"] == app.presets.graph.free_doc()


def saved_bytes(home: Path, kind: str, path: Path) -> bytes:
    """`path` loaded into a scratch library at `home` (a fixture copied in
    as a user's preset; a factory one by name) and saved untouched under
    the name it loaded as: the bytes on disk (`headless.resave`, the road
    tools/migrate_library.py takes)."""
    from hyperspace import headless

    raw, _, _ = headless.resave(path, home, factory=kind == "factory")
    return raw


def _module_run(app, module: str) -> tuple[str, ...]:
    """The run an fx module says alone: its values over the fx group's
    defaults, read as the migration reads a preset's."""
    from hyperspace import graphmigrate as M
    from hyperspace.library import _module_values

    doc = app.lib.read("fx", module)
    # (plan 36 T3: unfiltered — an effect the loaded graph does not name has
    # no param yet, and the module's values still say it)
    values = {**app.lib.defaults("fx"), **_module_values("fx", doc)}
    out, _ = M.migrate({"values": values}, app.presets.graph.specs())
    return main_run(G.read_graph(out["graph"]))


def main_run(spec) -> tuple[str, ...]:
    """The main run of a wired frame (plan 35 T3: every load's): the
    effects from the look-back into All outputs."""
    return G.run_back(spec, "output.all.image")


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
    # (its order is no param since T7, and no save writes one: row 394)
    assert app.lib.current("fx") == "mandala" and "fx.kaleido.order" not in app.reg
    # the save is `/6`, the module's run in its frame
    doc = app.presets.document("after")
    assert doc["schema"] == "hyperspace.preset/7"
    assert main_run(G.read_graph(doc["graph"])) == want
    assert "fx.kaleido.order" not in doc["values"]


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
    # (plan 36 T3: a refused wire of a `/7` is dropped, not kept)
    assert {"from": "hands", "to": "output.1.image"} not in gs.free_doc()["wires"]
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
    g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("acid", "wobble"))
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
    has foo still has its run (row 394: in the `/6` frame)."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    doc = {"schema": "hyperspace.preset/5", "name": "t", "graph": section(*MISSING_RUN),
           "values": {"fx.acid.on": True}}
    assert app.presets.load_doc(doc) == [] and app.presets.notes == []
    assert main_run(app.presets.graph.spec) == ("foo", "acid")
    out = app.presets.document("t")
    assert out["schema"] == "hyperspace.preset/7"
    assert main_run(G.read_graph(out["graph"])) == ("foo", "acid")


def test_a_driven_channel_choice_loads_as_a_switch_and_saves_as_six(tmp_path):
    """R19 (R14 → T5, row 350): a route on `view.media` or `backdrop.channel`
    loads as a switch over the eight channels into `pattern.media` /
    `backdrop.image`, the route retargeted onto its `select`, the select at
    the old choice — and, saved untouched, the preset is /6 (row 394), its
    graph the switches and their wires and its routes on the selects. The
    pictures are tests/test_graph_switch.py's."""
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
        assert doc["schema"] == "hyperspace.preset/7", name          # (row 394)
        assert [n for n in doc["graph"]["nodes"] if n["kind"] == "switch"] == [
            {"kind": "switch", **({"instance": 2} if sw == "switch.2" else {})}
            for sw, *_ in switches]
        assert [r["target"] for r in doc["routes"]] == [f"{sw}.select" for sw, *_ in switches]
        for sw, _, _, pick in switches:
            assert doc["values"][f"{sw}.select"] == pick
    assert sorted(p.name for p in DRIVEN.glob("*.json")) == [f"{n}.json" for n in sorted(want)]
    assert not [p for p in SAVES.glob("plan33--*.json")]


def test_an_effect_switched_on_in_no_run_adds_nothing_and_saves_as_six(tmp_path):
    """R13 (row 341): an effect switched on that no wire puts in a run draws
    nothing — a later save is /6 (as every save is, row 394), the run as it
    was."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.load("presets", "party-acid")
    gs = app.presets.graph
    run = main_run(gs.spec)
    # (plan 36 T3: an effect in no run exists only where the section names
    # it — one added on GRAPH and left on no wire)
    assert graphview.Edit(graph=gs, push=None).add_node("effect", "palette") is None
    off = "palette"
    assert off not in run           # (R25: the add switched it on — on, in no run)
    app.reg[f"fx.{off}.on"].set(True)
    assert main_run(gs.spec) == run
    doc = app.presets.document("after")
    assert doc["schema"] == "hyperspace.preset/7" and main_run(G.read_graph(doc["graph"])) == run


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
    assert want and len(want) < len(app.reg.fx_state.files)       # (plan 36 T3)
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
    r.wiring = wired_wiring(spec.wiring())
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
    assert spec.wiring().run == ("warp", "acid") and G.Wire("acid", "fx.image") in spec.wires
    assert not np.array_equal(got, with_acid)
    # the run without acid, from a state of its own stepped the same frames
    # (the clocks: two frames, then two more from the same start)
    bare = FxState(folder)
    bare.values["warp"]["on"] = True
    plain = Renderer(ctx, fx=bare)
    plain.wiring = wired_wiring(G.read_graph(section(("frame", "warp.image"),
                                        ("warp", "fx.image"))).wiring())
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
    return spec, G.build_graph(views(Switches()), wired_wiring(spec.wiring()),
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
    g = G.build_graph(views(Switches()), wired_wiring(spec.wiring()), effects=("palette", "acid", "acid.2"))
    assert {"palette", "acid.2"} <= {n.effect for n in _effect_nodes(g)}
