"""Wave 3 P1: frame kinds in patches — a look-back, the scene and the rest
are held by a patch, and so is the dream (plan 90 H3: an effect, any number
of instances), so a "dream + fx + composite" patch exists.

- what is refused still is the rig's (`FIXTURE_KINDS`) and the look's one camera;
- a frame kind's params are the ones the canvas says are its, every
  `fx.dream.*` the dream's (plan 90 H2: the look-back's knobs are retired, its
  trail is public parts), the band scene's no node's;
- what can be made twice is renamed (hands 1 lands as `hands.2`, a trail's
  delay as `delay.2`); what a frame holds one of keeps its name, and a host that
  already has it refuses the spawn in words, nothing landed (the dream is an
  effect since plan 90 H3: a second one lands as `dream.2`);
- a spawn into an empty frame is the frame: every corpus loadable patch, whole.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from conftest import CORPUS, seed
from test_graph_groups import files, spawned, state, watch, wires
from test_patches import land, loadable, parts
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import (
    graphmigrate,
    graphview,
    headless,
    params,
    patches,
    ui_graph,
    undo,
)
from hyperspace.library import PATCHES
from hyperspace.patches import Host, spawn
from hyperspace.routing import Bindings

CORPUS_LOADABLES = sorted((CORPUS / "loadable").glob("*.json"))
# the wired-frame nodes of party-wake a "dream + fx + composite" cut names: its
# dream as it opens (plan 90 H3), Resize → Dream → Hue turn → Curve → Fade →
# Composite over the last Cut's picture
DREAM_CUT = ["render:resize.2", "render:dream", "render:hueturn", "render:curve.2",
             "render:fade.2", "render:fade.3", "render:composite.2"]


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)
    return shell_rig


def wake_doc() -> dict:
    """party-wake as it opens (plan 90 H2: its look-back public parts)."""
    return graphmigrate.forward(loadable("party-wake"), {}).doc


def cut(name: str = "wake", ids=None) -> dict:
    """The dream's chain and its composite cut out of party-wake."""
    doc, refused = patches.lift(*parts(wake_doc()), ids or DREAM_CUT)
    assert refused == []
    doc["name"] = name
    return doc


def on_graph(rig, name: str) -> None:
    rig.lib.load("loadable", name)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")


def put(rig, doc: dict, slug: str | None = None) -> str:
    """A patch in the rig's scratch library."""
    slug = slug or patches.slug(doc["name"])
    (rig.lib.home / PATCHES).mkdir(parents=True, exist_ok=True)
    (rig.lib.home / PATCHES / f"{slug}.json").write_text(json.dumps(doc))
    return slug


# ---------------------------------------------------------------- what a patch holds

@pytest.mark.parametrize("name", ["scene", "shape", "backdrop", "pattern", "lookback",
                                  "lookback.2", "dream", "hands", "hands.layer", "hands.guide",
                                  "hands.2", "acid", "composite.2", "segment",
                                  "cloud", "cloud.2", "backdrop.2"])
def test_a_patch_holds_the_frames_kinds(name):
    assert patches.held_words(name) is None


@pytest.mark.parametrize("name, words", [
    ("output.all", patches.WINDOW_WORDS), ("output.2", patches.WINDOW_WORDS),
    ("channel.a", patches.CHANNEL_WORDS), ("camera", patches.CAMERA_WORDS),
    ("fx", patches.NOT_HELD_WORDS), ("lookback.echo.1", patches.NOT_HELD_WORDS),
])
def test_the_meta_and_the_one_camera_stay_refused(name, words):
    assert patches.held_words(name) == words.format(name=name)


def test_every_frame_kind_is_held_and_every_meta_kind_refused():
    """The lists stay honest as a kind is added."""
    assert set(G.FRAME_KINDS) <= set(patches.MAY_HOLD)
    assert not set(patches.FIXTURE_KINDS) & set(patches.MAY_HOLD)
    assert set(patches.ONE_PER_FRAME) <= set(patches.MAY_HOLD)
    assert "dream" not in patches.ONE_PER_FRAME          # (plan 90 H3: an effect)


def test_save_still_refuses_the_camera_and_a_lane_envelope_in_words():
    spec, table, _values, _layout = parts(wake_doc())
    mem, said = patches.select(spec, table, ["render:scene", "render:camera", "env.2",
                                             "render:output.all"])
    assert mem.render == ("scene",)
    assert said == [patches.CAMERA_WORDS.format(name="camera"),
                    patches.LANE_ENV_WORDS.format(name="env.2", first=patches.FIRST_ENV),
                    patches.WINDOW_WORDS.format(name="output.all")]


# ---------------------------------------------------------------- whose params

def test_a_frame_kinds_params_are_the_canvas_owners(tmp_path):
    """Over the whole registry: where `patches._param_rows` gives a frame
    kind's param an owner it is the node the canvas puts it on
    (`graphview.OWNERS`); no frame kind owns a shared meta group's param.
    (Plan 90 H3: the dream is an effect, no frame kind.)"""
    app = headless.make_app(tmp_path)
    frame_kinds = ("scene", "shape", "backdrop", "pattern")
    mem = patches._Members(frame_kinds)
    owned = 0
    for p in app.reg:
        pid = p.id
        who = patches._owner(pid, mem.param_rows, ())
        if who is None:
            continue
        owned += 1
        assert p.group in params.PATCH_GROUPS, pid
        rule = graphview.OWNERS.get(p.group)
        got = rule(pid, None) if callable(rule) and p.group != "fx" else (
            "shape" if pid == "fx.face_map" else rule)
        assert got == who, pid
    assert owned > 50


def test_the_dream_owns_its_knobs_and_the_trails_parts_their_own():
    """Plan 90 H3: the dream is an effect — it owns its `fx.dream.*`, no
    other part's; the trail's parts own their own."""
    only_dream = patches._Members(("dream",))
    for pid in ("fx.dream.on", "fx.dream.mix", "fx.dream.k", "fx.dream.layer"):
        assert only_dream.owns(pid), pid
    assert not only_dream.owns("fx.trail.level") and not only_dream.owns("delay.depth")
    trail, delay = patches._Members(("trail",)), patches._Members(("delay",))
    assert trail.owns("fx.trail.level") and not trail.owns("fx.dream.mix")
    assert delay.owns("delay.depth") and not delay.owns("fx.trail.level")


def test_a_frame_kinds_values_lift_and_keep_their_ids():
    """A shape's are `rot.*` and `view.*`, never renamed to `shape.*`; the
    pattern's `view.pattern*` are not the shape's."""
    doc, refused = patches.lift(*parts(wake_doc()), ["render:shape"])
    assert refused == [] and patches.check({**doc, "name": "s"}) == []
    assert "rot.rate.XY" in doc["values"] and "view.bright" in doc["values"]
    assert "view.pattern" not in doc["values"] and "view.media_alpha" not in doc["values"]
    assert not any(k.startswith("shape.") for k in doc["values"])
    doc, _ = patches.lift(*parts(wake_doc()), ["render:pattern"])
    assert "view.pattern" in doc["values"] and "view.bright" not in doc["values"]


# ---------------------------------------------------------------- the dream patch

def test_a_dream_and_a_composite_lift_as_a_patch():
    doc = cut()
    assert patches.check(doc) == []
    assert doc["schema"] == patches.SCHEMA == "hyperspace.patch/3"   # (plan 89's, no other)
    assert {patches.entry_name(e) for e in doc["nodes"]} == {
        "resize", "dream", "hueturn", "curve", "fade", "fade.2", "composite"}
    assert {"kind": "effect", "file": "dream"} in doc["nodes"]
    assert doc["wires"] == [{"from": "resize", "to": "dream.image"},
                            {"from": "dream", "to": "hueturn.image"},
                            {"from": "hueturn", "to": "curve.image"},
                            {"from": "curve", "to": "fade.image"},
                            {"from": "fade", "to": "fade.2.image"},       # the darken, the mix
                            {"from": "fade.2", "to": "composite.over"}]
    assert {(p["id"], p["was"]) for p in doc["ports"]} == {
        ("in", "cut.2"), ("in.2", "cut.2"), ("out", "composite.over")}
    assert "fx.dream.mix" in doc["values"] and "fx.trail.fade" not in doc["values"]
    assert not [k for k in doc["values"] if k.startswith("dream.")]


def test_a_dream_patch_spawns_where_the_host_has_no_dream():
    host = Host.of(*parts(loadable("party-noita"))[:2])
    landing = spawn(cut(), host)
    assert landing.taken == () and landing.refusal is None
    assert "dream" in [patches.entry_name(e) for e in landing.nodes]
    assert "dream" not in landing.renames
    assert landing.values["fx.dream.k"] == wake_doc()["values"]["fx.dream.k"]


def test_a_host_with_a_dream_takes_another_and_its_single_instance_nodes_are_said():
    """Plan 90 H3: a dream is never refused for a second dream — it lands as
    the next instance; `Landing.taken` names the single-instance nodes the
    host has, refused in words."""
    p = parts(wake_doc())
    landing = spawn(cut("dreamy"), Host.of(*p[:2]))
    assert landing.taken == () and landing.refusal is None
    assert landing.renames["dream"] == "dream.2"
    whole, _ = patches.lift(*p, ["render:scene", "render:shape", "render:dream"])
    landing = spawn({**whole, "name": "x"}, Host.of(*p[:2]))
    assert landing.taken == ("scene", "shape")
    assert all(patches.entry_name(e) in landing.taken or e.get("file") == "dream"
               for e in landing.nodes)
    assert landing.refusal == patches.TAKEN_WORDS.format(name="x", nodes="scene, shape")


def test_the_host_having_only_a_second_dream_leaves_the_first_free():
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "dream", "instance": 2}]})
    assert spawn(cut(), Host(names=patches.spec_names(spec))).taken == ()


def test_a_second_dream_is_held_and_lands_as_the_next_instance():
    """Plan 90 H3: any number of dreams (the hook passes all but one through,
    said): `dream.2` is saved like any effect, and lands renamed where the
    host already has it."""
    spec = G.read_graph({"frame": "wired",
                         "nodes": [{"kind": "effect", "file": "dream", "instance": 2}]})
    mem, said = patches.select(spec, Bindings([]), ["render:dream.2"])
    assert mem.render == ("dream.2",) and said == []
    doc = {"schema": patches.SCHEMA, "name": "d",
           "nodes": [{"kind": "effect", "file": "dream", "instance": 2}]}
    assert patches.check(doc) == []
    landing = spawn(doc, Host(names=frozenset({"dream", "dream.2"})))
    assert landing.taken == () and landing.refusal is None
    assert landing.renames.get("dream.2") not in (None, "dream", "dream.2")


def test_a_landing_from_before_a_hot_reload_still_lands(rig):
    """A sheet held open across a reload holds an old class's `Landing`,
    with no `refusal`: not an AttributeError."""
    on_graph(rig, "party-noita")
    old = SimpleNamespace(group={"nodes": []}, modifiers=(), lfos=(), envs=())
    assert ui_graph.group_edit(rig.panel)._spawn_refusal(old) is None


def test_a_spawn_of_a_shape_into_a_loadable_with_one_refuses_nothing_landed(rig):
    on_graph(rig, "party-wake")
    slug = put(rig, cut("shapely", ["render:shape"]))
    before, home = state(rig), files(rig.lib.home)
    u = watch(rig)
    try:
        n = len(u.stack)
        said = ui_graph.spawn(rig.panel, slug, (0.0, 0.0))
        assert said == patches.TAKEN_WORDS.format(name="shapely", nodes="shape")
        assert ui_graph._state(rig.panel)["note"] == said
        assert getattr(rig.panel, "spawn_question", None) is None    # no sheet: it could not land
        assert state(rig) == before and files(rig.lib.home) == home and len(u.stack) == n
    finally:
        undo.install(None)


def test_the_edit_refuses_a_landing_with_a_taken_node_as_well(rig):
    on_graph(rig, "party-wake")
    landing = spawn(cut("shapely", ["render:shape"]), Host(names=frozenset({"shape"})))
    before = state(rig)
    assert landing.refusal is not None
    assert ui_graph.group_edit(rig.panel).spawn(landing) == landing.refusal
    assert state(rig) == before


def test_dream_fx_composite_saved_spawned_and_undone_through_the_doors(rig):
    """The ask, end to end: on party-wake its dream group (plan 90 H3: Resize
    → Dream → Hue turn → Curve → Fade (darken) → Fade (mix) → Composite,
    folded as "dream") saved
    as a patch; back on party-wake it lands beside the host's as a second
    dream, never refused; on party-noita (no dream) spawned as one undo step,
    its values landed, its pins open, nothing wired to the host (D2); ⌘Z
    takes it all away."""
    on_graph(rig, "party-wake")
    pre = rig.lib.loaded_patch
    group = next(g for g in pre.groups if g["name"] == graphmigrate.DREAM_GROUP)
    assert group["nodes"] == DREAM_CUT
    rig.reg["fx.dream.k"].set_value(0.31)
    assert ui_graph.save_patch(rig.panel, group["id"], "dream wash", "") is None
    doc = rig.lib.read_patch("dream-wash")
    assert patches.check(doc) == []
    assert {patches.entry_name(n) for n in doc["nodes"]} == {
        "resize", "dream", "hueturn", "curve", "fade", "fade.2", "composite"}
    assert doc["values"]["fx.dream.k"] == pytest.approx(0.31)

    # back on its own loadable patch it is a second dream: no sheet to replace one
    assert spawned(rig, "dream-wash") is None, ui_graph._state(rig.panel).get("note")
    assert {"dream", "dream.2"} <= patches.spec_names(rig.lib.loaded_patch.graph.spec)

    on_graph(rig, "party-noita")
    pre = rig.lib.loaded_patch
    assert "dream" not in patches.spec_names(pre.graph.spec)
    before, wired, home = state(rig), wires(rig), files(rig.lib.home)
    u = watch(rig)
    try:
        n = len(u.stack)
        assert spawned(rig, "dream-wash") is None
        assert len(u.stack) == n + 1 and u.stack[-1].label == "spawn dream wash"
        assert "dream" in patches.spec_names(pre.graph.spec)
        assert rig.reg["fx.dream.k"].value == pytest.approx(0.31)
        # D2: the patch's own wires and nothing else; every port an open pin
        new = set(wires(rig)) - set(wired)
        assert new == {tuple(w.values()) for w in pre.graph.spec.to_json()["wires"]
                       if tuple(w.values()) in new}
        assert ("dream", "hueturn.image") in new
        assert not any(a in {s for s, _ in wired} for a, _ in new)
        group = pre.groups[-1]
        assert {p["id"] for p in group["ports"]} >= {"in", "out"}
        assert files(rig.lib.home) == home
        u.undo()
        assert state(rig) == before
    finally:
        undo.install(None)


def test_a_trails_delay_lands_as_a_second_delay_with_its_own_knobs(rig):
    """What can be made twice is renamed (plan 90 H2: the look-back's trail
    is public parts, and its delay is such a part): `delay.2`, `delay.2.*`;
    the host's `delay.*` untouched. Wire as saved reads it in where the
    first one's picture came from."""
    on_graph(rig, "party-wake")
    doc, refused = patches.lift(*rig.lib.loaded_patch.parts(), ["render:delay"])
    assert refused == []
    doc["name"] = "ring"
    doc["values"] = {**doc["values"], "delay.depth": 3}
    doc["ports"] = [p for p in doc["ports"] if "to" in p]     # (its outlet's port is taken)
    slug = put(rig, doc)
    host_depth = rig.reg["delay.depth"].value
    assert spawned(rig, slug) is None, ui_graph._state(rig.panel).get("note")
    spec = rig.lib.loaded_patch.graph.spec
    assert "delay.2" in patches.spec_names(spec)
    assert rig.reg["delay.2.depth"].value == 3
    assert rig.reg["delay.depth"].value == host_depth
    e = ui_graph.group_edit(rig.panel)
    assert e.wire_as_saved(rig.lib.loaded_patch.groups[-1]["id"]) is None, e.said
    assert any(w.src == "resize" and w.dst == "delay.2.image" for w in
               rig.lib.loaded_patch.graph.spec.wires)


def test_hands_one_lifts_as_a_new_hands():
    """Hands 1 is always the frame's: in a patch it is the next hands, its
    layer with it, its `ghost.*` values `ghost.2.*`."""
    doc = wake_doc()
    doc["values"] = {**doc["values"], "ghost.alpha": 0.7}
    got, refused = patches.lift(*parts(doc), ["render:hands", "render:hands.layer"])
    assert refused == []
    assert {patches.entry_name(e) for e in got["nodes"]} == {"hands.2", "hands.2.layer"}
    assert got["values"]["ghost.2.alpha"] == 0.7 and "ghost.alpha" not in got["values"]
    assert {"from": "hands.2", "to": "hands.2.layer.hands"} in got["wires"]
    assert patches.check({**got, "name": "h"}) == []
    landing = spawn({**got, "name": "h"}, Host(names=frozenset({"hands", "hands.2"})))
    assert {patches.entry_name(e) for e in landing.nodes} == {"hands.3", "hands.3.layer"}
    assert landing.values["ghost.3.alpha"] == 0.7


def test_a_hands_layer_is_taken_with_its_hands(rig):
    """A layer alone would land as a layer of a hands no one holds (its port
    refuses `hands`, its values for no param): said at the lift, and at a
    file's read. With its hands, it lands whole."""
    p = parts(wake_doc())
    doc, refused = patches.lift(*p, ["render:hands.layer", "render:composite"])
    assert refused == [patches.LAYER_WORDS.format(name="hands.layer", of="hands")]
    assert [e["kind"] for e in doc["nodes"]] == ["composite"]
    on_graph(rig, "party-wake")
    doc, refused = patches.lift(*rig.lib.loaded_patch.parts(), ["render:hands", "render:hands.layer"])
    assert refused == []
    doc["name"] = "ghosts"
    slug = put(rig, doc)
    on_graph(rig, "party-noita")
    assert spawned(rig, slug) is None
    said = ui_graph._state(rig.panel)["said"]
    assert "no param" not in said, said
    assert {"hands.2", "hands.2.layer"} <= patches.spec_names(rig.lib.loaded_patch.graph.spec)
    assert rig.reg["ghost.2.alpha"].value == doc["values"]["ghost.2.alpha"]


def test_a_file_an_older_build_saved_with_a_layer_alone_still_reads():
    """Files on disk are a format: `hands.2.layer` without `hands.2` was a
    legal save, so only a new save refuses it. It reads, and spawns as it
    did, its values for no param said by the landing."""
    doc = {"schema": "hyperspace.patch/1", "name": "old layer",
           "nodes": [{"kind": "layer", "instance": 2}], "values": {"ghost.2.alpha": 0.5}}
    assert patches.check(doc) == []
    landing = spawn(patches.forward(doc), Host())
    assert [patches.entry_name(e) for e in landing.nodes] == ["hands.2.layer"]
    assert landing.values == {"ghost.2.alpha": 0.5}


SCENE_THREE = {"frame": "wired", "nodes": [{"kind": "hands", "instance": 2}],
               "wires": [{"from": "hands.2", "to": "scene.geometry"},
                         {"from": "shape", "to": "scene.geometry"},
                         {"from": "hands", "to": "scene.geometry"}]}


def test_an_inlet_into_the_scene_says_where_it_drew():
    """The scene and two hands lifted without the shape between them: the
    shape's inlet says which of the patch's own wires it drew before."""
    spec = G.read_graph(SCENE_THREE)
    doc, refused = patches.lift(spec, Bindings([]), {}, {},
                                ["render:scene", "render:hands", "render:hands.2"])
    assert refused == []
    port = next(p for p in doc["ports"] if p["was"] == "shape")
    assert port["before"] == "hands.2"                # (hands 1 lifts as hands.2)
    landed = spawn({**doc, "name": "s"}, Host(names=frozenset({"hands.2"})))
    assert next(p for p in landed.ports if p["was"] == "shape")["before"] == "hands.3"


def test_wire_as_saved_puts_a_scene_inlet_back_in_its_draw_order(rig):
    """Host order hands.2, shape, hands; the scene and both hands cut and
    spawned where only the shape is left; wire as saved: the shape draws
    between them again, not last."""
    on_graph(rig, "party-noita")
    doc, refused = patches.lift(G.read_graph(SCENE_THREE), Bindings([]), {}, {},
                                ["render:scene", "render:hands", "render:hands.2"])
    assert refused == []
    slug = put(rig, {**doc, "name": "three", "ports": [
        p for p in doc["ports"] if p["was"] == "shape"]})
    host = loadable("party-noita")
    host["graph"] = {"frame": "wired", "nodes": [{"kind": "shape"}]}
    assert rig.lib.loaded_patch.load_doc(host) is not None
    assert spawned(rig, slug) is None, ui_graph._state(rig.panel).get("note")
    gid = rig.lib.loaded_patch.groups[-1]["id"]
    assert graphview.open_ports(rig.lib.loaded_patch.graph.spec, rig.lib.loaded_patch.groups[-1])
    e = ui_graph.group_edit(rig.panel)
    assert e.wire_as_saved(gid) is None, e.said
    into = [w.src for w in rig.lib.loaded_patch.graph.spec.all_wires() if w.dst == "scene.geometry"]
    assert into == ["hands.3", "shape", "hands.2"]


def test_a_read_orders_ports_by_number():
    doc = {"ports": [{"id": f"in.{n}"} for n in (10, 2, 3)] + [{"id": "out"}, {"id": "in"}]}
    assert [p["id"] for p in patches.read(doc).ports] == ["in", "in.2", "in.3", "in.10", "out"]


def test_read_keeps_the_scenes_draw_order():
    """The scene's geometry takes several wires; their order is the draw
    order, so a patch holding the scene does not sort it away."""
    doc = {"schema": patches.SCHEMA, "name": "s",
           "nodes": [{"kind": "scene"}, {"kind": "shape"}, {"kind": "hands", "instance": 2}],
           "wires": [{"from": "shape", "to": "scene.geometry"},
                     {"from": "hands.2", "to": "scene.geometry"}]}
    assert [w["from"] for w in patches.read(doc).wires] == ["shape", "hands.2"]
    doc["wires"].reverse()
    assert [w["from"] for w in patches.read(doc).wires] == ["hands.2", "shape"]


# ---------------------------------------------------------------- the empty frame

def everything(p) -> list[str]:
    spec, table, _values, _layout = p
    ids = [f"render:{n}" for n in sorted(patches.spec_names(spec))]
    return ids + [m.id for m in table.modifiers]


def hands_moved(name: str) -> str:
    """A name of the frame as a spawn lands it: hands 1 is the next hands."""
    if name == "hands" or name.startswith("hands."):
        _base, n, suffix = patches._family(name)
        return f"hands.{n + 1}{suffix}"
    return name


@pytest.mark.parametrize("path", CORPUS_LOADABLES, ids=lambda p: p.stem)
def test_a_whole_loadable_spawned_into_an_empty_frame_is_that_loadable(path):
    """Every corpus loadable patch's section lifted whole, spawned into a frame with
    nothing in it, its pins wired as saved, is the section again (hands one
    number on: the empty frame's own hands 1 is the meta controller's; `spec_names` is
    what a load would hold). What is left out is the rig's alone. The literal
    "a load is a spawn into an empty frame" of plan 50 is therefore true of
    the graph; `LoadedPatch.load_doc` stays the replace landing (row 660)."""
    doc = json.loads(path.read_text())
    p = parts(doc)
    spec = p[0]
    whole, refused = patches.lift(*p, everything(p))
    for why in refused:
        assert any(word in why for word in ("meta controller's", "camera", "media channel", "subscriber")), why
    whole["name"] = path.stem
    assert patches.check(whole) == [], path.stem
    landing = spawn(whole, Host())
    assert landing.taken == (), path.stem
    held = {n for n in patches.spec_names(spec)
            if patches.held_words(n) is None}
    landed = {patches.entry_name(e) for e in landing.nodes}
    want = {hands_moved(n) for n in held}
    assert want <= landed | {n for w in landing.wires
                             for n in (patches._node_of(w["from"]), w["to"].rpartition(".")[0])}
    # the section reads, its own wires and the ports as they were saved
    ground = G.read_graph({"frame": "wired"})
    empty = (ground, Bindings([]), {}, {})
    got = land(empty, landing)[0]
    assert not got.notes, (path.stem, got.notes)

    def norm(s, f=lambda x: x):
        out = set()
        for w in s.all_wires():
            node, port = w.dst.rpartition(".")[::2]
            src = patches._node_of(w.src)
            pin = w.src[len(src):]
            out.add((f(src) + pin, f(node), port))
        return out
    assert norm(got) == norm(spec, hands_moved), path.stem

    # …and the same draw order into the scene
    def geometry(s, f=lambda x: x):
        return [f(w.src) for w in s.all_wires() if w.dst == "scene.geometry"]
    assert geometry(got) == geometry(spec, hands_moved), path.stem


def test_a_new_loadable_holds_a_scene_so_a_whole_frame_is_refused_there(tmp_path):
    """A new loadable patch's section is the scene chain: a whole frame says so,
    rather than land a second scene."""
    app = headless.make_app(tmp_path)
    app.loaded_patch.new()
    p = parts(wake_doc())
    whole, _ = patches.lift(*p, everything(p))
    landing = spawn({**whole, "name": "x"},
                    Host.of(app.loaded_patch.graph.spec, app.router.table))
    assert set(landing.taken) == {"scene", "shape"}
