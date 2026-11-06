"""Wave 3 P1: frame kinds in patches — the dream, a look-back, the scene and
the rest are held by a patch, so a "dream + fx + composite" patch exists.

- what is refused still is the meta controller's (`FIXTURE_KINDS`) and the look's one camera;
- a frame kind's params are the ones the canvas says are its, the look-back's
  and the dream's split by key, the band scene's no node's;
- what can be made twice is renamed (hands 1 lands as `hands.2`, a look-back
  as `lookback.2`); what a frame holds one of keeps its name, and a host that
  already has it refuses the spawn in words, nothing landed (the dream's is
  the sheet's since P2: tests/test_patches_replace_dream.py);
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
from hyperspace import graphview, headless, params, patches, ui_graph, ui_routing, undo
from hyperspace.library import PATCHES
from hyperspace.patches import Host, spawn
from hyperspace.routing import Bindings

CORPUS_LOADABLES = sorted((CORPUS / "presets").glob("*.json"))
# the wired-frame nodes of party-wake a "dream + fx + composite" cut names
DREAM_CUT = ["render:dream", "render:composite"]


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)
    return shell_rig


def wake_doc() -> dict:
    return loadable("party-wake")


def cut(name: str = "wake", ids=None) -> dict:
    """The dream and its composite cut out of party-wake."""
    doc, refused = patches.lift(*parts(wake_doc()), ids or DREAM_CUT)
    assert refused == []
    doc["name"] = name
    return doc


def on_graph(rig, name: str) -> None:
    rig.lib.load("presets", name)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")


def put(rig, doc: dict, slug: str | None = None) -> str:
    """A patch in the meta controller's scratch library."""
    slug = slug or patches.slug(doc["name"])
    (rig.lib.home / PATCHES).mkdir(parents=True, exist_ok=True)
    (rig.lib.home / PATCHES / f"{slug}.json").write_text(json.dumps(doc))
    return slug


# ---------------------------------------------------------------- what a patch holds

@pytest.mark.parametrize("name", ["scene", "shape", "backdrop", "pattern", "lookback",
                                  "lookback.2", "dream", "hands", "hands.layer", "hands.guide",
                                  "hands.2", "acid", "composite.2", "segment"])
def test_a_patch_holds_the_frames_kinds(name):
    assert patches.held_words(name) is None


@pytest.mark.parametrize("name, words", [
    ("output.all", patches.WINDOW_WORDS), ("output.2", patches.WINDOW_WORDS),
    ("channel.a", patches.CHANNEL_WORDS), ("cloud", patches.FIXTURE_WORDS),
    ("cloud.2", patches.FIXTURE_WORDS), ("camera", patches.CAMERA_WORDS),
    ("fx", patches.NOT_HELD_WORDS), ("lookback.echo.1", patches.NOT_HELD_WORDS),
])
def test_the_meta_and_the_one_camera_stay_refused(name, words):
    assert patches.held_words(name) == words.format(name=name)


def test_every_frame_kind_is_held_and_every_meta_kind_refused():
    """The lists stay honest as a kind is added."""
    assert set(G.FRAME_KINDS) <= set(patches.MAY_HOLD)
    assert not set(patches.FIXTURE_KINDS) & set(patches.MAY_HOLD)
    assert set(patches.ONE_PER_FRAME) <= set(patches.MAY_HOLD)


def test_save_still_refuses_the_camera_and_a_lane_envelope_in_words():
    spec, table, _values, _layout = parts(wake_doc())
    mem, said = patches.select(spec, table, ["render:scene", "render:camera", "env.2",
                                             "render:output.all"])
    assert mem.render == ("scene",)
    assert said == [patches.CAMERA_WORDS.format(name="camera"),
                    patches.LANE_ENV_WORDS.format(name="env.2", first=patches.FIRST_ENV),
                    patches.WINDOW_WORDS.format(name="output.all")]


# ---------------------------------------------------------------- whose params

def test_the_leaf_and_params_share_the_look_backs_keys():
    assert patches.is_lookback_key is params.is_lookback_key


def test_a_frame_kinds_params_are_the_canvas_owners(tmp_path):
    """Over the whole registry: where `patches._param_rows` gives a frame
    kind's param an owner it is the node the canvas puts it on
    (`graphview.OWNERS`, the dream's on the dream's since P2); no frame kind
    owns a shared meta group's param."""
    app = headless.make_app(tmp_path)
    frame_kinds = ("scene", "shape", "backdrop", "pattern", "lookback", "dream")
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


def test_the_dream_and_a_look_back_split_dream_by_key():
    only_dream = patches._Members(("dream",))
    only_look = patches._Members(("lookback",))
    for member, yes, no in ((only_dream, "dream.mix", "dream.fade"),
                            (only_look, "dream.fade", "dream.mix")):
        assert member.owns(yes) and not member.owns(no)
    second = patches._Members(("lookback.2",))
    assert second.owns("dream.2.fade") and not second.owns("dream.fade")
    assert not second.owns("dream.2.mix")


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
    assert doc["schema"] == "hyperspace.patch/2"       # no schema moved
    assert {e["kind"] for e in doc["nodes"]} == {"dream", "composite"}
    assert doc["wires"] == [{"from": "dream", "to": "composite.over"}]
    assert {(p["id"], p["was"]) for p in doc["ports"]} == {
        ("in", "scene"), ("in.2", "lookback"), ("out", "output.all.image")}
    assert "dream.mix" in doc["values"] and "dream.fade" not in doc["values"]


def test_a_dream_patch_spawns_where_the_host_has_no_dream():
    host = Host.of(*parts(loadable("party-noita"))[:2])
    landing = spawn(cut(), host)
    assert landing.taken == () and landing.refusal is None
    assert "dream" in [patches.entry_name(e) for e in landing.nodes]
    assert "dream" not in landing.renames
    assert landing.values["dream.mix"] == wake_doc()["values"]["dream.mix"]


def test_a_host_has_a_single_instance_node_and_the_landing_says_so():
    """`Landing.taken` names it, whichever it is; the dream's is the sheet's
    since P2 (`Landing.replacing`), the rest refuse in words."""
    p = parts(wake_doc())
    landing = spawn(cut("dreamy"), Host.of(*p[:2]))
    assert landing.taken == ("dream",) and landing.refusal is None
    whole, _ = patches.lift(*p, ["render:scene", "render:shape", "render:dream"])
    landing = spawn({**whole, "name": "x"}, Host.of(*p[:2]))
    assert landing.taken == ("dream", "scene", "shape")
    assert all(patches.entry_name(e) in landing.taken for e in landing.nodes)
    assert landing.refusal == patches.TAKEN_WORDS.format(name="x", nodes="scene, shape")


def test_the_host_having_only_a_second_dream_leaves_the_first_free():
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "dream", "instance": 2}]})
    assert spawn(cut(), Host(names=patches.spec_names(spec))).taken == ()


def test_a_second_dream_stays_out_and_never_becomes_the_live_one():
    """`dream.2` may be declared but no wire may touch it: a save refuses it
    in words; a file holding it (never saved: `check` refuses it) is not
    renumbered onto `dream`."""
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "dream", "instance": 2}]})
    mem, said = patches.select(spec, Bindings([]), ["render:dream.2"])
    assert mem.render == () and said == [patches.SECOND_DREAM_WORDS.format(name="dream.2")]
    doc = {"schema": patches.SCHEMA, "name": "d", "nodes": [{"kind": "dream", "instance": 2}]}
    assert patches.check(doc) == [patches.SECOND_DREAM_WORDS.format(name="dream.2")]
    landing = spawn(doc, Host())
    assert landing.renames == {} and landing.taken == ()
    assert spawn(doc, Host(names=frozenset({"dream"}))).taken == ()
    assert spawn(doc, Host(names=frozenset({"dream.2"}))).taken == ("dream.2",)


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
    """The ask, end to end: on party-wake a group of the dream, its composite
    and an effect saved as a patch; on party-noita (no dream) spawned as one
    undo step, its values landed, its pins open, nothing wired to the host
    (D2) — wire as saved reads through it; ⌘Z takes it all away."""
    on_graph(rig, "party-wake")
    e = ui_graph.group_edit(rig.panel)
    assert graphview.render_add(e, "effect", "acid") is None
    entry = ui_graph.group_nodes(rig.panel, ["render:dream", "render:composite", "render:acid"])
    assert entry["nodes"] == ["render:dream", "render:composite", "render:acid"]
    rig.reg["dream.mix"].set_value(0.31)
    assert ui_graph.save_patch(rig.panel, "group.1", "dream wash", "") is None
    doc = rig.lib.read_patch("dream-wash")
    assert patches.check(doc) == []
    assert {patches.entry_name(n) for n in doc["nodes"]} == {"dream", "composite", "acid"}

    # back on its own loadable patch the sheet asks to replace that dream (P2), not here
    assert ui_graph.spawn(rig.panel, "dream-wash") is None
    assert ui_routing.sheet(rig.panel)[0].replacing == ("dream",)
    assert ui_routing.settle_sheet(rig.panel, False) is None

    on_graph(rig, "party-noita")
    pre = rig.lib.loaded_patch
    assert "dream" not in patches.spec_names(pre.graph.spec)
    rig.reg["dream.mix"].set_value(0.9)
    before, wired, home = state(rig), wires(rig), files(rig.lib.home)
    mix = rig.reg["dream.mix"].value
    u = watch(rig)
    try:
        n = len(u.stack)
        assert spawned(rig, "dream-wash") is None
        assert len(u.stack) == n + 1 and u.stack[-1].label == "spawn dream wash"
        assert "dream" in patches.spec_names(pre.graph.spec)
        assert rig.reg["dream.mix"].value == pytest.approx(0.31)
        # D2: the patch's own wires and nothing else; every port an open pin
        new = set(wires(rig)) - set(wired)
        assert new == {tuple(w.values()) for w in pre.graph.spec.to_json()["wires"]
                       if tuple(w.values()) in new}
        assert ("dream", "composite.2.over") in new or ("dream", "composite.over") in new
        assert not any(a in {s for s, _ in wired} for a, _ in new)
        group = pre.groups[-1]
        assert {p["id"] for p in group["ports"]} >= {"in", "out"}
        assert files(rig.lib.home) == home
        u.undo()
        assert state(rig) == before
        assert rig.reg["dream.mix"].value == pytest.approx(mix)
    finally:
        undo.install(None)


def test_a_look_back_lands_as_a_second_look_back_with_its_own_knobs(rig):
    """A look-back is made twice: `lookback.2`, `dream.2.*`; the host's
    `dream.*` untouched. The section keeps the second one's entry though a
    wire names it (it is what declares it)."""
    on_graph(rig, "party-wake")
    doc, refused = patches.lift(*rig.lib.loaded_patch.parts(), ["render:lookback"])
    assert refused == []
    doc["name"] = "ring"
    doc["values"] = {**doc["values"], "dream.gap": 3.0}
    doc["ports"] = [p for p in doc["ports"] if "to" in p]     # (its outlet's port is taken)
    slug = put(rig, doc)
    host_gap = rig.reg["dream.gap"].value
    assert spawned(rig, slug) is None, ui_graph._state(rig.panel).get("note")
    spec = rig.lib.loaded_patch.graph.spec
    assert "lookback.2" in patches.spec_names(spec)
    assert rig.reg["dream.2.gap"].value == pytest.approx(3.0)
    assert rig.reg["dream.gap"].value == host_gap
    # wired: `_land` keeps the entry (it declares it), and the section reads
    e = ui_graph.group_edit(rig.panel)
    assert e.wire_as_saved(rig.lib.loaded_patch.groups[-1]["id"]) is None, e.said
    assert any(w.src == "scene" and w.dst == "lookback.2.image" for w in
               rig.lib.loaded_patch.graph.spec.wires)
    assert any(x.get("kind") == "lookback" and x.get("instance") == 2
               for x in rig.lib.loaded_patch.graph.spec.to_json()["nodes"])


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
    what a load would hold). What is left out is the meta controller's alone. The literal
    "a load is a spawn into an empty frame" of plan 50 is therefore true of
    the graph; `LoadedPatch.load_doc` stays the replace landing (row 660)."""
    doc = json.loads(path.read_text())
    p = parts(doc)
    spec = p[0]
    whole, refused = patches.lift(*p, everything(p))
    for why in refused:
        assert any(word in why for word in ("rig's", "camera", "media channel", "subscriber")), why
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
