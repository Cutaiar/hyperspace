"""Plan 40 T2 (P2, D4, D7) — the group node: groups in the preset, folded
by default, open in place, Group and Ungroup.

A group is a region of the loaded preset (`preset.GROUPS_KEY`: ``{"id":
"group.1", "name", "patch"?, "nodes": [canvas ids], "open"}``) drawn on
GRAPH as one node. Folded — the owner's one sanctioned exception to plan
36's no-hidden-edge rule (D4) — its members are not drawn and neither is a
cable with both ends inside; every cable with one end inside is drawn
re-ended at the group node. Open, everything is drawn as if there were no
group, in a titled region. The renderer never hears the word: a grouped
preset's `graph.build_graph` has its ungrouped twin's `graph.signature`
(the goldens' half of the proof is `test_golden_frames.py`'s).

Headless, on the shell's rig (tests/test_ui_shell.py) with party-noita
loaded — warp → doublevision → fractals, K-knobs and hand rows on them —
and the page drawn for real on `imgui_node_editor`; the presets' half on
`headless.make_app`. No preset is edited or added: the grouped twins are
written into scratch libraries, and one is the fixture
tests/fixtures/groups/party-noita-grouped.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_graphview import _in_editor
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import devices, graphmigrate, graphview, headless, patches, preset, ui_graph, undo
from hyperspace import graph as G
from hyperspace.library import Marks
from hyperspace.outputs import Switches, View

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "groups" / "party-noita-grouped.json"
NOITA_CORE = ["render:warp", "render:doublevision", "render:fractals"]
ENTRY = {"id": "group.1", "name": "noita core", "nodes": NOITA_CORE, "open": False}


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def noita(rig, groups=None):
    """party-noita on the GRAPH page (its `groups` set as a load would),
    drawn twice. Returns the page's state."""
    rig.lib.load("presets", "party-noita")
    rig.lib.presets.groups = [{**g, "nodes": list(g["nodes"])} for g in groups or ()]
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


def count(view, folded=None) -> int:
    """How many cables the canvas draws, every node collapsed: one each for
    a single, each bundle's own."""
    singles, bundles = graphview.wiring(view, lambda nid: True, folded=folded)
    return len(singles) + sum(b.count for b in bundles)


def watch(rig):
    """The app's undo, with the library's marks, installed for the test."""
    u = undo.Undo(rig.reg, rig.router.table, marks=Marks(rig.lib))
    undo.install(u)
    u.tick(1.0)
    u.tick(2.0)
    return u


def grouped_twin(doc: dict, ids: list[str], name: str = "main run") -> dict:
    """`doc` with one folded group of `ids` — what a save of it writes."""
    out = {**doc, "schema": preset.GROUPS_SCHEMA,
           preset.GROUPS_KEY: [{"id": "group.1", "name": name, "nodes": ids, "open": False}]}
    if "media" in out:                              # (`document`'s order: groups before media)
        out["media"] = out.pop("media")
    return out


def main_run(doc: dict) -> tuple[str, ...]:
    """T1's main run (tests/test_patches.py): the effects wired one after
    another into All outputs' picture."""
    return G.run_back(G.read_graph(doc["graph"]), "output.all.image")


FACTORY = sorted(preset.FACTORY_DIR.glob("*.json"))
RUNS = {p.stem: main_run(json.loads(p.read_text())) for p in FACTORY}
NO_RUN = {slug for slug, run in RUNS.items() if not run}


# ---------------------------------------------------------------- in the preset (D7)

def test_the_schema_is_eight_and_the_key_absent_is_no_groups():
    """D7: 37B took no `/8`, so `groups` is `/8`; the ladder reads it; the
    one migration step is "the key is absent → no groups"."""
    assert preset.GROUPS_SCHEMA == "hyperspace.preset/8" and 8 in preset.VERSIONS
    assert preset.GROUPS_KEY == "groups"
    assert graphmigrate.groups_of({"schema": preset.WIRED_SCHEMA}) == []
    assert graphmigrate.groups_of({"groups": [ENTRY]}) == [ENTRY]
    assert graphmigrate.groups_of(None) == []


def test_one_rule_reads_a_group_number_for_the_load_and_for_group():
    """`graphmigrate.group_number` (a leaf both import) is the preset's and
    GRAPH's: a group landed after `group.0` and a hand-edited `group.x`
    is `group.1`, after `group.7` is `group.8`."""
    gn = graphmigrate.group_number
    assert preset.group_number is gn and not hasattr(graphview, "_group_n")
    assert [gn(x) for x in ("group.3", "group.0", "group.x", "mod.3", 3, None)] == [
        3, 0, 0, 0, 0, 0]
    from types import SimpleNamespace
    e = graphview.Edit()
    e.presets = SimpleNamespace(groups=[{"id": "group.0"}, {"id": "group.x"}])
    assert e.land_group({"nodes": ["render:warp"]})["id"] == "group.1"
    e.presets.groups.append({"id": "group.7"})
    assert e.land_group({"nodes": ["render:acid"]})["id"] == "group.8"


def test_a_preset_with_groups_round_trips_through_document_and_load_doc(tmp_path):
    app = headless.make_app(tmp_path)
    app.lib.load("presets", "party-noita")
    app.presets.groups = [dict(ENTRY, patch="noita-core")]
    doc = app.presets.document("noita grouped")
    assert doc["schema"] == "hyperspace.preset/8"
    assert doc["groups"] == [{"id": "group.1", "name": "noita core", "patch": "noita-core",
                              "nodes": NOITA_CORE, "open": False}]
    keys = list(doc)
    assert keys.index("groups") == keys.index("media") - 1      # after layout, before media
    text = preset.dumps(doc)
    assert '\n  {"id": "group.1"' in text                         # one group a line
    fresh = headless.make_app(tmp_path / "b")
    assert fresh.presets.load_doc(json.loads(text)) == []
    assert fresh.presets.notes == []
    assert fresh.presets.groups == doc["groups"]
    assert preset.dumps(fresh.presets.document("noita grouped")) == text


def test_the_fixture_twin_resaves_byte_for_byte(tmp_path):
    """The grouped fixture (party-noita and one group, `/8`) loaded and saved
    untouched is the same bytes — and so is every factory preset, with no
    groups, its `/7` (a preset from before this plan saves byte for byte)."""
    raw = FIXTURE.read_bytes()
    assert json.loads(raw)["schema"] == "hyperspace.preset/8"
    again, notes, _ = headless.resave(FIXTURE, tmp_path / "twin")
    assert notes == [] and again == raw
    for k, path in enumerate(FACTORY):
        data = path.read_bytes()
        again, _, _ = headless.resave(path, tmp_path / f"f{k}", factory=True)
        assert again == data and b'"groups"' not in again, path.name


def test_a_member_the_graph_lacks_is_dropped_with_a_note(tmp_path):
    app = headless.make_app(tmp_path)
    doc = json.loads((preset.FACTORY_DIR / "party-noita.json").read_text())
    doc = grouped_twin(doc, ["render:warp", "render:acid.3"], "acid wash")
    doc["groups"] += [{"id": "group.2", "name": "gone", "nodes": ["render:kaleido"],
                       "open": True},
                      {"id": "group.4", "name": "frame", "nodes": ["render:scene", "mod.9",
                                                                   "render:fractals"]},
                      {"id": "group.5", "name": "twice", "nodes": ["render:warp", "lfo.1"]},
                      "not a group"]
    app.presets.load_doc(doc)
    assert app.presets.notes == [
        "group acid wash: acid.3 is not in the preset — left out",
        "group gone: kaleido is not in the preset — left out",
        "group gone: nothing of it is in the preset — left out",
        "group frame: mod.9 is not in the preset — left out",
        "group frame: scene is the frame's; left out",
        "group twice: warp is in group acid wash already — left out",
        "groups: an entry that is not a group, ignored"]
    assert app.presets.groups == [
        {"id": "group.1", "name": "acid wash", "nodes": ["render:warp"], "open": False},
        {"id": "group.4", "name": "frame", "nodes": ["render:fractals"], "open": False},
        {"id": "group.5", "name": "twice", "nodes": ["lfo.1"], "open": False}]


def test_signature_changes_when_a_group_is_made_and_a_save_drops_a_deleted_member(tmp_path):
    app = headless.make_app(tmp_path)
    app.lib.load("presets", "party-noita")
    clean = app.presets.signature()
    assert not app.lib.is_dirty("presets")
    app.presets.groups = [dict(ENTRY)]
    assert app.presets.signature() != clean and app.lib.is_dirty("presets")
    app.presets.groups = []
    assert app.presets.signature() == clean and not app.lib.is_dirty("presets")
    # a member deleted since: the save leaves it out, and the group with it
    app.presets.groups = [dict(ENTRY, nodes=["render:warp", "render:acid.4"]),
                          dict(ENTRY, id="group.2", nodes=["render:acid.4"])]
    assert app.presets.document("x")["groups"] == [dict(ENTRY, nodes=["render:warp"])]
    app.presets.groups = [dict(ENTRY, nodes=["render:acid.4"])]
    doc = app.presets.document("x")
    assert "groups" not in doc and doc["schema"] == "hyperspace.preset/7"


# ---------------------------------------------------------------- the proof: the renderer learns nothing

def _views(n=2):
    return [View(Switches(), (64, 48)) for _ in range(n)]


def test_a_grouped_preset_builds_the_graph_of_its_ungrouped_twin(tmp_path):
    """For every factory preset, the section loaded with its main run
    grouped is its ungrouped twin's: the same section, and `build_graph`
    of it the same `graph.signature`. The presets with no main run are
    named (T1's `NO_RUN`)."""
    assert NO_RUN == {"big-blue-wave", "ember-orbit", "hands-orbit", "hands-play",
                      "hex-engine", "inverse-halo", "legacy6", "party-faces", "party-field",
                      "party-tumble", "party-wake", "plasma-heart", "spiral-silk",
                      "strobe-cage", "woven-lattice", "party-tracer"}
    app = headless.make_app(tmp_path)
    done = []
    for path in FACTORY:
        run = RUNS[path.stem]
        if not run:
            continue
        doc = json.loads(path.read_text())
        app.presets.load_doc(doc)
        flat = app.presets.graph.spec
        want = G.signature(G.build_graph(_views(), flat.wiring()))
        app.presets.load_doc(grouped_twin(doc, [f"render:{n}" for n in run]))
        assert app.presets.notes == [], path.stem
        assert app.presets.groups[0]["nodes"] == [f"render:{n}" for n in run], path.stem
        spec = app.presets.graph.spec
        assert spec.to_json() == flat.to_json(), path.stem
        assert G.signature(G.build_graph(_views(), spec.wiring())) == want, path.stem
        done.append(path.stem)
    assert len(done) == len(FACTORY) - len(NO_RUN) >= 9


def test_graph_and_render_never_hear_the_word():
    """graph.py and render.py name no group of the canvas's: a group is a
    fold on the canvas and a list in the file."""
    root = Path(__file__).resolve().parents[1] / "hyperspace"
    for name in ("graph.py", "render.py"):
        src = (root / name).read_text()
        assert "GROUPS_KEY" not in src and "VGroup" not in src and '"groups"' not in src, name


# ---------------------------------------------------------------- the model: folded, open (D4)

def test_a_folded_group_hides_its_members_and_inside_cables_and_reends_the_rest(rig):
    """Folded: the members are off the canvas and so is every cable with
    both ends inside (warp → doublevision → fractals); each cable with one
    end inside is drawn re-ended at the group node — the scene's picture
    into its in pin, its picture out to tripcolour, each desk row and hand
    row at its param's row. Counted: folded + hidden = open = ungrouped."""
    st = noita(rig)
    flat = count(st["view"])
    st = noita(rig, [ENTRY])
    view = st["view"]
    (g,) = view.groups
    assert g.id == "group.1" and not g.open and sorted(g.ids) == sorted(NOITA_CORE)
    assert set(NOITA_CORE) <= st["hide"]
    assert {c.id for c in view.cables if c.kind == "render" and c.ref.src in (
        "warp", "doublevision") and c.ref.node in ("doublevision", "fractals")} <= g.inside
    pics = [p for p in g.ports if p.type == graphview.IMAGE]
    assert [(p.direction, p.name) for p in pics] == [
        (graphview.IN, f"{view.node('render:warp').label} image ← scene"),
        (graphview.OUT, "fractals → tripcolour.image")]
    rows = [p for p in g.ports if p.param]
    assert rows and all(p.param.startswith(("fx.warp.", "fx.doublevision.", "fx.fractals."))
                        for p in rows)
    folded_n = count(view, graphview.folded(view))
    assert folded_n + len(g.inside) == flat
    # every crossing cable is drawn at one of the group's own pins
    singles, bundles = st["wiring"][1]
    drawn = [(c, a, b) for c, a, b in singles] + [
        (c, b.src_port, b.dst_port) for b in bundles for c in b.cables]
    for c, a, b in drawn:
        if c.id in g.ends:
            src, dst = g.ends[c.id]
            assert (src or a) == a and (dst or b) == b and (src == a or dst == b), c.id
    assert {pin for _c, a, b in drawn for pin in (a, b) if graphview.is_group_pin(pin)} == {
        p.id for p in g.ports}
    assert all(p.id in st["pin_xy"] for p in g.ports)          # drawn on the canvas
    # open: everything as if there were no group, plus a region
    st = noita(rig, [dict(ENTRY, open=True)])
    view = st["view"]
    assert not set(NOITA_CORE) & st["hide"]
    assert count(view, graphview.folded(view)) == flat
    assert "group.1" in st["regions"]


def test_a_rig_node_is_never_a_member_and_preset_only_keeps_the_group(rig):
    st = noita(rig)
    assert ui_graph.group_nodes(rig.panel, ["device:apc40", "analyzer"]) is None
    assert st["note"] == ("device:apc40 is the rig's; left out; analyzer is the rig's; left "
                          "out; nothing to group")
    st = noita(rig, [dict(ENTRY, nodes=[*NOITA_CORE, "device:apc40"])])
    (g,) = st["view"].groups
    assert g.ids == frozenset(NOITA_CORE)               # the rig's left out of the drawing too
    assert set(NOITA_CORE) <= graphview.preset_only(st["view"])
    assert ui_graph._id(st, "n:group.1") in st["names"]   # the folded node is on the canvas


# ---------------------------------------------------------------- the verbs

def test_group_from_a_selection_refuses_scene_and_keeps_the_rest(rig):
    st = noita(rig)
    entry = ui_graph.group_nodes(rig.panel, ["render:scene", "render:warp",
                                             "render:doublevision", "group.7"])
    assert entry == {"id": "group.1", "name": "group 1",
                     "nodes": ["render:warp", "render:doublevision"], "open": False}
    assert st["note"] == ("scene is the frame's; left out; group.7 is a group: a group holds "
                          "nodes, not groups; left out")
    assert rig.lib.presets.groups == [entry]
    frame(rig.panel, "graph")
    assert [g.id for g in st["view"].groups] == ["group.1"]
    # a second group takes fractals and moves doublevision over, said
    two = ui_graph.group_nodes(rig.panel, ["render:doublevision", "render:fractals"])
    assert two["id"] == "group.2" and two["name"] == "group 2"
    assert st["note"] == "doublevision left group 1 for this group"
    assert [g["nodes"] for g in rig.lib.presets.groups] == [
        ["render:warp"], ["render:doublevision", "render:fractals"]]
    # its id is one past the highest held, never one held
    ui_graph.ungroup(rig.panel, "group.1")
    three = ui_graph.group_nodes(rig.panel, ["render:warp"])
    assert three["id"] == "group.3"


def test_the_right_click_menus_offer_group_with_two_nodes_selected(rig, monkeypatch):
    st = noita(rig)
    items = []
    monkeypatch.setattr(imgui, "menu_item_simple", lambda label, *a, **k: items.append(label)
                        or label.startswith("group "))
    _in_editor(rig, lambda: [ed.select_node(ed.NodeId(ui_graph._id(st, "n:" + nid)), True)
                             for nid in NOITA_CORE[:2]])
    _in_editor(rig, lambda: st.__setitem__("menu_sel", ui_graph.selected_ids(st)))
    assert st["menu_sel"] == NOITA_CORE[:2]
    st["menu"] = ("picker", "")
    st["menu_at"] = (0.0, 0.0)
    imgui.new_frame()
    imgui.begin("probe")
    ui_graph.menu(rig.panel, st, st["view"])
    imgui.end()
    imgui.end_frame()
    assert items[0] == "group 2 nodes"
    assert rig.lib.presets.groups[0]["nodes"] == NOITA_CORE[:2]
    # the group's own menu: open / fold, rename…, ungroup
    frame(rig.panel, "graph")
    items.clear()
    monkeypatch.setattr(imgui, "menu_item_simple", lambda label, *a, **k: items.append(label)
                        or label == "open")
    st["menu"] = ("node", "group.1")
    imgui.new_frame()
    imgui.begin("probe")
    ui_graph.menu(rig.panel, st, st["view"])
    imgui.end()
    imgui.end_frame()
    # (plan 40 T3: and save as patch…; update patch only for a group with a patch)
    assert items == ["open", "rename…", "save as patch…", "ungroup"]
    assert rig.lib.presets.groups[0]["open"] is True


def test_ungroup_leaves_every_node_and_cable_where_it_was(rig):
    st = noita(rig)
    flat = (rig.lib.presets.graph.spec.to_json(), [b.to_json() for b in rig.router.table.bindings],
            dict(rig.lib.presets.layout), count(st["view"]))
    st = noita(rig, [ENTRY])
    assert ui_graph.ungroup(rig.panel, "group.1") is None
    assert st["said"] == "noita core taken apart: its 3 nodes stay where they are"
    frame(rig.panel, "graph")
    view = st["view"]
    assert view.groups == [] and rig.lib.presets.groups == []
    assert (rig.lib.presets.graph.spec.to_json(), [b.to_json() for b in rig.router.table.bindings],
            dict(rig.lib.presets.layout), count(view)) == flat
    assert ui_graph.ungroup(rig.panel, "group.1") == "no group group.1"


def test_a_group_made_then_undone_is_gone_and_the_signature_is_back(rig):
    noita(rig)
    sig = rig.lib.presets.signature()
    u = watch(rig)
    try:
        ui_graph.group_nodes(rig.panel, NOITA_CORE)
        assert u.stack[-1].label == "group 3 nodes"
        assert rig.lib.presets.signature() != sig and rig.lib.is_dirty("presets")
        assert u.undo()
        assert rig.lib.presets.groups == [] and rig.lib.presets.signature() == sig
        assert u.redo() and len(rig.lib.presets.groups) == 1
    finally:
        undo.install(None)


def test_rename_open_and_fold_are_each_one_step(rig):
    noita(rig, [ENTRY])
    u = watch(rig)
    try:
        assert ui_graph.rename_group(rig.panel, "group.1", "  ") == graphview.GROUP_NEEDS_NAME
        assert ui_graph.rename_group(rig.panel, "group.1", "core") is None
        assert u.stack[-1].label == "rename noita core to core"
        u.tick(3.0)
        u.tick(4.0)
        assert ui_graph.set_open(rig.panel, "group.1", True) is None
        assert u.stack[-1].label == "open core"
        assert rig.lib.presets.groups[0] == dict(ENTRY, name="core", open=True)
        assert u.undo() and rig.lib.presets.groups[0]["open"] is False
        assert u.undo() and rig.lib.presets.groups[0]["name"] == "noita core"
    finally:
        undo.install(None)


def _moved(rig, st, nid, xy):
    _in_editor(rig, lambda: ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:" + nid)),
                                                 imgui.ImVec2(*xy)))
    frame(rig.panel, "graph")


def test_a_drag_of_the_title_moves_every_member_in_one_step(rig):
    """The open region's title dragged: every member by the same delta, in
    the preset's layout, one undo step; ⌘Z puts every member back."""
    st = noita(rig, [dict(ENTRY, open=True)])
    title = ui_graph.region_id("group.1")
    was = {m: tuple(st["applied"][m]) for m in NOITA_CORE}
    at = st["applied"][title]
    u = watch(rig)
    try:
        _moved(rig, st, title, (at[0] + 40, at[1] - 30))
        lay = rig.lib.presets.layout
        px, py = ui_graph.panned(st)
        assert {m: tuple(lay[m]) for m in NOITA_CORE} == {
            m: (round(x - px + 40), round(y - py - 30)) for m, (x, y) in was.items()}
        assert u.stack[-1].label == "move noita core"
        assert rig.lib.presets.groups[0]["nodes"] == NOITA_CORE   # nobody left
        frame(rig.panel, "graph")
        assert u.undo()
        assert not any(m in rig.lib.presets.layout for m in NOITA_CORE)
    finally:
        undo.install(None)


def test_a_drag_of_the_folded_node_moves_every_member(rig):
    st = noita(rig, [ENTRY])
    at = st["applied"]["group.1"]
    _moved(rig, st, "group.1", (at[0] + 100, at[1] + 10))
    lay = rig.lib.presets.layout
    assert set(NOITA_CORE) <= set(lay)
    frame(rig.panel, "graph")
    assert tuple(st["applied"]["group.1"]) == (at[0] + 100, at[1] + 10)


def test_a_member_dragged_out_leaves_the_group(rig):
    st = noita(rig, [dict(ENTRY, open=True)])
    u = watch(rig)
    try:
        x, y = st["applied"]["render:fractals"]
        _moved(rig, st, "render:fractals", (x + 3000, y + 3000))
        assert rig.lib.presets.groups[0]["nodes"] == NOITA_CORE[:2]
        assert st["said"] == "fractals left noita core"
        px, py = ui_graph.panned(st)
        assert rig.lib.presets.layout["render:fractals"] == [round(x + 3000 - px),
                                                             round(y + 3000 - py)]
        assert u.stack[-1].label == "render:fractals leaves noita core"
        frame(rig.panel, "graph")
        (g,) = st["view"].groups
        assert g.ids == frozenset(NOITA_CORE[:2])            # the region shrinks
        # a member nudged inside its region stays
        x, y = st["applied"]["render:warp"]
        _moved(rig, st, "render:warp", (x + 5, y + 5))
        assert rig.lib.presets.groups[0]["nodes"] == NOITA_CORE[:2]
    finally:
        undo.install(None)


def test_two_members_dragged_out_together_leave_in_one_step(rig):
    """Two members of an open group box-selected and dragged out in one
    drop: both leave, both positions written, **one** undo step — and one
    ⌘Z puts both back in the group."""
    st = noita(rig, [dict(ENTRY, open=True)])
    u = watch(rig)
    try:
        n = len(u.stack)
        at = {m: st["applied"][m] for m in NOITA_CORE[1:]}

        def drag():
            for m, (x, y) in at.items():
                ed.set_node_position(ed.NodeId(ui_graph._id(st, "n:" + m)),
                                     imgui.ImVec2(x + 3000, y + 3000))
        _in_editor(rig, drag)
        frame(rig.panel, "graph")
        assert rig.lib.presets.groups[0]["nodes"] == NOITA_CORE[:1]
        assert len(u.stack) == n + 1 and u.stack[-1].label == "2 nodes leave noita core"
        assert st["said"] == "doublevision, fractals left noita core"
        px, py = ui_graph.panned(st)
        assert {m: rig.lib.presets.layout[m] for m in at} == {
            m: [round(x + 3000 - px), round(y + 3000 - py)] for m, (x, y) in at.items()}
        frame(rig.panel, "graph")
        assert u.undo() and rig.lib.presets.groups[0]["nodes"] == NOITA_CORE
    finally:
        undo.install(None)


def test_the_last_member_leaving_takes_the_group():
    from types import SimpleNamespace
    pre = SimpleNamespace(groups=[{"id": "group.1", "name": "one", "nodes": ["render:warp"],
                                   "open": True}], layout={})
    e = graphview.Edit()
    e.presets = pre
    assert e.leave_group("group.1", "render:warp", (10, 20)) is None
    assert pre.groups == [] and pre.layout == {"render:warp": [10, 20]}
    assert e.said == "warp left one, the last of it: the group is gone"


# ---------------------------------------------------------------- the drawing

def test_the_group_node_side_pane_hover_and_status_draw(rig, monkeypatch):
    """Selected, a group's side pane draws: its name (Enter renames), its
    provenance, what it waits for (T4's words, the APC40 listed and lost),
    its members as chips — a click opens the group and selects the member
    — its boundary in words, and T3's chips' seam."""
    rig.panel.devices = devices.DeviceRegistry([
        {"role": "apc40", "kind": "midi", "enabled": True, "port": "APC40",
         "profile": "apc40"}])
    st = noita(rig, [dict(ENTRY, patch="noita-core")])
    view = st["view"]
    (g,) = view.groups
    status = ui_graph.group_status(rig.panel, view, g)
    # (the hand rows on warp's params wait for a leap this rig lists none of)
    assert status.startswith("waits for ") and " apc40 (lost): D2, D3" in status
    words = graphview.group_words(view, g)
    assert words[0] == "in: picture · out: picture"
    assert any(" → fx.warp." in w for w in words[1:])
    tip = ui_graph.group_tip(rig.panel, view, g).split("\n")
    labels = ", ".join(view.node(m).label for m in NOITA_CORE)
    assert tip[:4] == ["noita core", f"3 nodes: {labels}", "from patch noita-core", words[0]]
    assert tip[-2:] == [status, "+ opens it in place"]
    seams, chips = [], []
    monkeypatch.setattr(ui_graph, "_group_chips", lambda panel, grp: seams.append(grp.id))
    real_chip = ui_graph.ui.chip
    monkeypatch.setattr(ui_graph.ui, "chip", lambda label, *a, **k: chips.append(label) or (
        label.startswith(view.node("render:fractals").label + "##graph.group.")
        or real_chip(label, *a, **k)))
    _in_editor(rig, lambda: ed.select_node(ed.NodeId(ui_graph._id(st, "n:group.1"))))
    frame(rig.panel, "graph")
    assert ui_graph._selection(st, st["view"])[0] == "group"
    frame(rig.panel, "graph")
    assert seams and seams[-1] == "group.1"
    assert rig.lib.presets.groups[0]["open"] is True           # the chip opened it
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    sel = ui_graph._selection(st, st["view"])
    assert sel[0] == "node" and sel[1].id == "render:fractals"


def test_a_folded_groups_last_picture_outlet_is_on_the_want_list(rig):
    st = noita(rig, [ENTRY])
    view = st["view"]
    (g,) = view.groups
    assert g.thumb == "render:fractals"
    st["seen_rect"] = None
    want = ui_graph.thumb_wants(st, view, lambda nid: ((0.0, 0.0), (10.0, 10.0)))
    assert want.get("fractals") == view.node("render:fractals").thumb
    assert "warp" not in want                                  # a hidden member is not


def test_a_drag_onto_a_group_pin_lands_on_its_member(rig):
    st = noita(rig, [ENTRY])
    (g,) = st["view"].groups
    pin = next(p.id for p in g.ports if p.direction == graphview.IN
               and p.type == graphview.IMAGE)
    assert graphview.real_pin(st["view"], pin) == "rin:warp/image"
    assert graphview.real_pin(st["view"], "rin:warp/image") == "rin:warp/image"


def test_a_drop_on_a_folded_groups_stub_is_refused_in_words(rig):
    """A cable let go on a folded group's stub would open an empty picker
    (the group is no node with ports): refused while held, in words."""
    st = noita(rig, [ENTRY])
    view = st["view"]
    assert ui_graph.stub_refusal(view, graphview.stub_in("group.1"), "out:lane:3") == (
        "noita core is folded: drop it on one of its pins, or open it (+)")
    assert graphview.land_choices(view, ui_graph.edit_of(rig.panel, view), "out:lane:3",
                                  "group.1") == []           # (what it would have offered)


def test_deleting_a_group_node_is_refused_in_words(rig, monkeypatch):
    st = noita(rig, [ENTRY])
    got = []
    names = iter([ui_graph._id(st, "n:group.1")])

    class Id:                               # (what the widget fills in: the deleted node)
        def __init__(self, v=0):
            self.v = v

        def id(self):
            return self.v

    def query(nk):
        nk.v = next(names, 0)
        return bool(nk.v)

    def delete():
        with monkeypatch.context() as m:
            m.setattr(ed, "begin_delete", lambda: True)
            m.setattr(ed, "end_delete", lambda: None)
            m.setattr(ed, "NodeId", Id)
            m.setattr(ed, "query_deleted_node", query)
            m.setattr(ed, "query_deleted_link", lambda lk: False)
            m.setattr(ed, "reject_deleted_item", lambda: got.append("rejected"))
            ui_graph._delete(rig.panel, st, st["view"])
    _in_editor(rig, delete)
    assert got == ["rejected"]
    assert st["note"] == graphview.GROUP_NO_DELETE.format(name="noita core")
    assert rig.lib.presets.groups == [ENTRY]


def test_patches_select_is_the_one_rule_for_lift_and_group():
    """One classifier (T1's, factored): `lift` and `Edit.group` both read
    `patches.select`; its words are the lift's."""
    import inspect
    assert "select(" in inspect.getsource(patches.lift)
    assert "patches.select(" in inspect.getsource(graphview.Edit.group)
    assert "patches.crossing(" in inspect.getsource(graphview._boundary)


# ---------------------------------------------------------------- plan 40 T3: save, browse, spawn
#
# A group becomes a file (save as patch: that file, nothing else) and a
# file becomes a group in any preset (spawn: through today's doors in load
# order, one undo step; the conflicts asked first — tests/test_ui_routing.py
# drives the sheet — and nothing attached by itself, D2). The patch is the
# spec's example, tests/fixtures/patches/acid-wash.json, put into the rig's
# scratch library; the host is party-trip (K1 there is view.bright: the
# sheet asks), whose own effects are none of the patch's, so the first
# spawn keeps the patch's ids and a second one takes `.2`.

ACID_WASH = Path(__file__).resolve().parent / "fixtures" / "patches" / "acid-wash.json"
ACID = ["render:acid", "render:delay", "render:wobble", "mod.1"]


def files(root: Path) -> dict[str, bytes]:
    """Every file under `root`, by its path: what a spawn may not change."""
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file()}


def with_patch(rig, doc: dict | None = None, slug: str = "acid-wash") -> None:
    """A patch in the rig's scratch library (its user folder)."""
    d = rig.lib.home / "patches"
    d.mkdir(parents=True, exist_ok=True)
    text = ACID_WASH.read_text() if doc is None else json.dumps(doc)
    (d / f"{slug}.json").write_text(text)


def trip(rig):
    """party-trip on GRAPH with acid-wash in the library, drawn twice."""
    with_patch(rig)
    rig.lib.load("presets", "party-trip")
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


def wires(rig) -> list[tuple[str, str]]:
    return [(w.src, w.dst) for w in rig.lib.presets.graph.spec.wires]


def state(rig) -> tuple:
    """Everything a spawn may add, as it stands."""
    pre, table = rig.lib.presets, rig.router.table
    return (pre.signature(), dict(pre.layout), [dict(g) for g in pre.groups],
            pre.graph.spec.to_json(), [b.to_json() for b in table.bindings],
            table.modifiers_doc(rig.reg), table.macros_doc())


def spawned(rig, slug="acid-wash", at=(100.0, 50.0), keep=False, splice=None):
    """Spawn `slug` and answer the sheet: every row the patch's, or (`keep`)
    every row the preset's."""
    from hyperspace import ui_routing
    assert ui_graph.spawn(rig.panel, slug, at, splice=splice) is None
    if ui_routing.sheet(rig.panel) is not None:
        if keep:
            ui_routing.keep_all(rig.panel)
        return ui_routing.settle_sheet(rig.panel, True)
    return None


def test_spawn_lands_through_the_doors_as_one_step_and_one_undo_takes_it_all(rig):
    """acid-wash into party-trip (P3): the sheet asks about K1 (party-trip's
    view.bright) and, answered for the patch, the whole landing is one undo
    step — acid, wobble and delay in the section with their two wires and
    their values, mod.1 reading the right hand, the lane route, the hand's
    route through mod.1, K1 on the patch's speed, the group folded with its
    pins open and its layout at the drop point. No file is written. One ⌘Z
    takes every part of it away: the signature, the layout and the groups
    are as they were."""
    st = trip(rig)
    pre, table, reg = rig.lib.presets, rig.router.table, rig.reg
    before, wired, home = state(rig), wires(rig), files(rig.lib.home)
    u = watch(rig)
    try:
        n = len(u.stack)
        assert spawned(rig) is None
        assert len(u.stack) == n + 1 and u.stack[-1].label == "spawn acid wash"
        assert {"acid", "wobble", "delay"} <= patches.spec_names(pre.graph.spec)
        # D2: the section's wires are the host's and the patch's own — nothing to the scene
        assert sorted(wires(rig)) == sorted([*wired, ("acid", "wobble.image"),
                                             ("wobble", "delay.image")])
        assert reg["fx.acid.speed"].value == pytest.approx(0.4)
        assert reg["fx.wobble.amount"].value == pytest.approx(0.3)
        assert reg["fx.acid.on"].value and reg["fx.wobble.on"].value
        m = table.modifier("mod.1")
        assert m.kind == "smooth" and m.inputs == ("hand:right.y",)
        rows = {(b.source, b.target) for b in table.routes()}
        assert {("lane:0", "fx.acid.speed"), ("mod:1", "fx.wobble.amount")} <= rows
        assert [b.target for b in table.desk() if b.source == "cc:0:48"] == ["fx.acid.speed"]
        (g,) = pre.groups
        assert {k: g[k] for k in ("id", "name", "patch", "open")} == {
            "id": "group.1", "name": "acid wash", "patch": "acid-wash", "open": False}
        assert sorted(g["nodes"]) == sorted(ACID) and "kept_by_host" not in g
        assert [p["id"] for p in g["ports"]] == ["in", "out"]
        assert {k: pre.layout[k] for k in ACID} == {
            "render:acid": [100, 50], "render:wobble": [360, 50], "render:delay": [620, 50],
            "mod.1": [100, 250]}
        assert rig.lib.is_dirty("presets") and files(rig.lib.home) == home
        frame(rig.panel, "graph")
        (vg,) = st["view"].groups
        opened = [p.name for p in vg.ports if "/open:" in p.id]
        assert opened == ["in · open (was scene)", "out · open (was output.all.image)"]
        assert vg.real[graphview.group_pin("group.1", graphview.IN, "open:in")] == \
            "rin:acid/image"
        assert u.undo()
        assert state(rig) == before and wires(rig) == wired
        assert table.modifier("mod.1") is None and pre.groups == []
        assert [b.target for b in table.desk() if b.source == "cc:0:48"] == ["view.bright"]
        assert files(rig.lib.home) == home
    finally:
        undo.install(None)


BREATH = {"schema": "hyperspace.patch/1", "name": "breath", "note": "",
          "nodes": [{"kind": "effect", "file": "acid"}], "wires": [],
          "values": {"fx.acid.on": True, "lfo.1.rate": 0.3}, "modifiers": [],
          "routes": [{"source": "lfo:0", "target": "fx.acid.speed", "op": "push", "value": 0.2}],
          "desk": [],
          "macros": {"macro.3": {"label": "wash", "subs": [
              {"base": "fx.acid.speed", "from": 0.1, "to": 0.9}]}},
          "lfos": [1], "envs": [], "ports": [],
          "layout": {"render:acid": [0, 0], "lfo.1": [0, 200]}}


def test_a_spawn_with_a_voice_and_a_subscriber_is_one_step_through_the_banks(tmp_path):
    """The app's own rig (`headless.make_app`: the LFO and envelope banks):
    a patch with an LFO and a macro lands its voice by `bank.add` (lfo.1 →
    lfo.5, past party-trip's four), its knob's value, its route on the new
    lane and the macro's subscriber merged (`set_macros`) — one undo step,
    and one ⌘Z takes the voice, the value, the route, the subscriber, the
    group and its layout back off."""
    assert patches.check(BREATH) == []
    app = headless.make_app(tmp_path)
    app.lib.load("presets", "party-trip")
    pre, table, reg = app.presets, app.router.table, app.reg
    u = undo.Undo(reg, table, marks=Marks(app.lib), banks=pre.banks)
    undo.install(u)
    try:
        u.tick(1.0)
        u.tick(2.0)
        e = graphview.Edit(table, reg, app.router, graph=pre.graph,
                           push=lambda label: undo.push(label, load=True))
        e.presets = pre
        before = (pre.signature(), dict(pre.layout), list(pre.groups), table.macros_doc())
        landing = patches.spawn(BREATH, patches.Host.of(pre.graph.spec, table, pre.banks()),
                                (40.0, 60.0))
        assert landing.renames == {"lfo.1": "lfo.5"}
        n = len(u.stack)
        assert e.spawn(landing) is None
        assert len(u.stack) == n + 1 and u.stack[-1].label == "spawn breath"
        assert pre.banks()["lfo"].doc() == [1, 2, 3, 4, 5]
        assert reg["lfo.5.rate"].value == pytest.approx(0.3)
        assert ("lfo:4", "fx.acid.speed") in {(b.source, b.target) for b in table.routes()}
        assert table.macros_doc()["macro.3"]["subs"] == [
            {"base": "fx.acid.speed", "from": 0.1, "to": 0.9}]
        assert pre.groups[0]["nodes"] == ["render:acid", "lfo.5", "macro.3"]
        assert pre.layout["lfo.5"] == [40, 260]
        assert e.spawn(landing) == graphview.SPAWN_STALE.format(name="breath")   # landed once
        assert u.undo()
        assert (pre.signature(), dict(pre.layout), list(pre.groups),
                table.macros_doc()) == before
        assert pre.banks()["lfo"].doc() == [1, 2, 3, 4] and "lfo.5.rate" not in reg
    finally:
        undo.install(None)


def test_a_spawn_with_no_conflict_lands_at_once(rig):
    """A patch whose rows collide with nothing: no sheet, one step, the
    spawn said on the head."""
    from hyperspace import ui_routing
    doc = json.loads(ACID_WASH.read_text())
    doc["desk"] = []
    trip(rig)
    with_patch(rig, doc, "quiet-wash")
    assert ui_graph.spawn(rig.panel, "quiet-wash", (0, 0)) is None
    assert ui_routing.sheet(rig.panel) is None
    assert rig.lib.presets.groups[0]["patch"] == "quiet-wash"
    st = ui_graph._state(rig.panel)
    assert st["said"].startswith("spawned acid wash: 4 nodes, its pins open")
    # P4: no sheet asked, so the spawn says what its rows wait for (this rig lists no leap)
    assert st["said"].endswith("; waits for leap (not in this rig): right hand y")


def test_a_landing_refused_after_its_dry_run_leaves_no_undo_step(rig, monkeypatch):
    """`Edit.spawn` pushes its one step after the dry run; were the real
    landing then refused (the dry run rules it out), nothing was written,
    so the step closes empty and leaves the stack — no empty ⌘Z."""
    doc = json.loads(ACID_WASH.read_text())
    doc["desk"] = []
    trip(rig)
    with_patch(rig, doc, "quiet-wash")
    before = state(rig)
    real = graphview._land
    monkeypatch.setattr(graphview, "_land", lambda edit, d, label, said, dry=False, rig=None:
                        real(edit, d, label, said, dry=dry, rig=rig) if dry else "refused")
    u = watch(rig)
    try:
        n = len(u.stack)
        assert ui_graph.spawn(rig.panel, "quiet-wash", (0, 0)) == "refused"
        assert len(u.stack) == n + 1                    # pushed before the first write…
        u.tick(10.0)
        u.tick(11.0)
        assert len(u.stack) == n and state(rig) == before
    finally:
        undo.install(None)


def test_a_source_conflict_the_table_refuses_leaves_the_hosts_rows_whole():
    """A one-owner source answered "the patch" whose row the referee refuses
    (`abs` is no op for a hand axis): the host's row on that source stays —
    the refusal is asked before any row moves — and the refusal is a note."""
    from types import SimpleNamespace

    from hyperspace.routing import Binding, Bindings
    host = Binding("hand:right.y", "view.bright", "position")
    table = Bindings([host])
    row = {"source": "hand:right.y", "target": "fx.acid.speed", "op": "abs", "value": 0.5}
    c = patches.Conflict("source", "hand:right.y", "view.bright", "fx.acid.speed", row,
                         host.to_json())
    landing = SimpleNamespace(routes=[row], desk=[], conflicts=[c])
    e = graphview.Edit(table)
    notes: list[str] = []
    assert e._spawn_rows(landing, {0: graphview.PATCH_SIDE}, notes) == []
    assert table.bindings == [host]
    (note,) = notes
    assert note.startswith("hand:right.y → fx.acid.speed: 'abs' is not an op for a hand source")


def test_a_spawn_whose_devices_are_all_there_says_no_wait(rig):
    """The same spawn into a rig whose leap is connected: no "waits for"."""
    from test_device_wants import _Live

    doc = json.loads(ACID_WASH.read_text())
    doc["desk"] = []
    trip(rig)
    with_patch(rig, doc, "quiet-wash")
    rig.panel.devices = devices.DeviceRegistry(devices=[_Live("leap", ("hand", "hands"))])
    assert ui_graph.spawn(rig.panel, "quiet-wash", (0, 0)) is None
    said = ui_graph._state(rig.panel)["said"]
    assert said.startswith("spawned acid wash: 4 nodes") and "waits for" not in said


def test_a_row_the_sheet_kept_for_the_preset_waits_for_nothing(rig):
    """acid-wash's K1 kept for the preset (the sheet's **keep all existing**):
    the patch's K1 never landed, so only the hand's row is said to wait."""
    trip(rig)
    spawned(rig, keep=True)
    said = ui_graph._state(rig.panel)["said"]
    assert said.endswith("; waits for leap (not in this rig): right hand y")
    assert "apc40" not in said


def test_splice_on_a_cable_lands_the_patch_in_the_run_in_one_step(rig):
    """Dropped on `scene → plasma.image` (D2's splice, `render_insert`'s
    shape): the cable goes, scene → acid … delay → plasma come, in the same
    undo step; no pin is left open. A patch with two inlets is no drop
    target: refused in words, nothing changed."""
    st = trip(rig)
    pre = rig.lib.presets
    cable = next(c for c in st["view"].cables if c.kind == "render"
                 and (c.ref.src, c.ref.dst) == ("scene", "plasma.image"))
    e = ui_graph.render_edit(rig.panel)
    ports = patches.read(json.loads(ACID_WASH.read_text())).ports
    assert graphview.splice_target(e, cable, "acid wash", ports) is None
    two = [*ports, {"id": "in.2", "type": "image", "to": "wobble.aux", "was": "scene"}]
    assert graphview.splice_target(e, cable, "x", two) == (
        "x has 2 picture inlets and 1 outlet: a splice needs one of each")
    u = watch(rig)
    try:
        n = len(u.stack)
        assert spawned(rig, splice=cable) is None
        assert len(u.stack) == n + 1
        assert u.stack[-1].label == "splice acid wash into scene → plasma.image"
        w = wires(rig)
        assert ("scene", "plasma.image") not in w
        assert {("scene", "acid.image"), ("acid", "wobble.image"), ("wobble", "delay.image"),
                ("delay", "plasma.image")} <= set(w)
        assert G.run_of(pre.graph.spec, "scene", "delay.image") == ("acid", "wobble")
        assert G.run_back(pre.graph.spec, "output.all.image") == (
            "plasma", "kaleido", "zoomblur", "huecycle")
        assert "ports" not in pre.groups[0]
        assert graphview.open_ports(pre.graph.spec, pre.groups[0]) == []
        assert u.undo() and ("scene", "plasma.image") in wires(rig) and pre.groups == []
    finally:
        undo.install(None)


def test_a_splice_that_raises_the_sheet_lands_the_splice_with_its_answers(rig):
    """Dropped on `scene → plasma.image` with K1 colliding (party-trip's
    view.bright): the sheet goes up and nothing lands; **keep all existing**
    + Spawn lands the *splice* — the cable taken out, the run through the
    patch — with K1 left on brightness and kept by the group, one step."""
    from hyperspace import ui_routing
    st = trip(rig)
    pre, table = rig.lib.presets, rig.router.table
    cable = next(c for c in st["view"].cables if c.kind == "render"
                 and (c.ref.src, c.ref.dst) == ("scene", "plasma.image"))
    wired = wires(rig)
    u = watch(rig)
    try:
        n = len(u.stack)
        assert ui_graph.spawn(rig.panel, "acid-wash", (0.0, 0.0), splice=cable) is None
        assert ui_routing.sheet(rig.panel) is not None
        assert wires(rig) == wired and pre.groups == [] and len(u.stack) == n
        ui_routing.keep_all(rig.panel)
        assert ui_routing.settle_sheet(rig.panel, True) is None
        assert len(u.stack) == n + 1
        assert u.stack[-1].label == "splice acid wash into scene → plasma.image"
        w = wires(rig)
        assert ("scene", "plasma.image") not in w
        assert {("scene", "acid.image"), ("delay", "plasma.image")} <= set(w)
        assert [b.target for b in table.desk() if b.source == "cc:0:48"] == ["view.bright"]
        (g,) = pre.groups
        assert [k["source"] for k in g["kept_by_host"]] == ["cc:0:48"]
        assert ui_graph._state(rig.panel)["said"].startswith("spliced acid wash")
    finally:
        undo.install(None)


def test_wire_as_saved_wires_the_free_ports_and_refuses_a_taken_one(rig):
    """**wire as saved** (D2's chip): scene → acid.image lands, delay →
    output.all.image is refused in words while party-trip's run holds it —
    one undo step for the press; with the port freed, a second press lands
    it and no pin is open, so the chip is gone."""
    st = trip(rig)
    pre = rig.lib.presets
    spawned(rig)
    u = watch(rig)
    try:
        n = len(u.stack)
        assert ui_graph.wire_as_saved(rig.panel, "group.1") == "output.all.image is taken"
        assert len(u.stack) == n + 1 and u.stack[-1].label == "wire acid wash as saved"
        assert ("scene", "acid.image") in wires(rig)
        assert ("delay", "output.all.image") not in wires(rig)
        assert st["said"] == "wired as saved: scene → acid.image"
        assert [p["id"] for p in graphview.open_ports(pre.graph.spec, pre.groups[0])] == ["out"]
        frame(rig.panel, "graph")
        cable = next(c for c in st["view"].cables if c.kind == "render"
                     and (c.ref.src, c.ref.dst) == ("huecycle", "output.all.image"))
        assert ui_graph._render_said(rig.panel, ui_graph.render_edit(rig.panel),
                                     lambda e: e.unwire(cable)) is None
        assert ui_graph.wire_as_saved(rig.panel, "group.1") is None
        assert ("delay", "output.all.image") in wires(rig)
        assert graphview.open_ports(pre.graph.spec, pre.groups[0]) == []
        assert ui_graph.wire_as_saved(rig.panel, "group.1") == "no pin of acid wash is open"
    finally:
        undo.install(None)


def test_wire_as_saved_refuses_a_node_the_preset_lacks():
    """A port whose `was` names a node the host does not have is refused,
    named, and nothing lands (pure, on the edit layer)."""
    spec = G.read_graph({"frame": "wired", "wires": [{"from": "shape", "to": "scene.geometry"}],
                         "nodes": [{"kind": "effect", "file": "acid"}]})
    entry = {"id": "group.1", "name": "g", "nodes": ["render:acid"],
             "ports": [{"id": "in", "type": "image", "to": "acid.image", "was": "tripcolour"}]}
    assert graphview.open_ports(spec, entry) == [entry["ports"][0]]

    class GS:
        def __init__(self):
            self.spec = spec

        def files(self):
            return None

        def land(self, *a):
            raise AssertionError("nothing lands")

    def no_step(label):
        raise AssertionError("no undo step")

    e = graphview.Edit(graph=GS(), push=no_step)
    e.presets = type("P", (), {"groups": [entry], "layout": {}})()
    assert e.wire_as_saved("group.1") == "no node tripcolour"


def test_a_second_spawn_takes_the_next_ids_and_its_kept_rows_are_said(rig):
    """Twice (P3): the second copy is `.2` everywhere and a second group;
    its K1 collides with the first copy's, and **keep all existing** keeps
    the first's — the second's row is not in the table, it is in the
    group's `kept_by_host` and said on the node ("K1 kept by the preset");
    the fresh ids are on the group's hover for the session (never saved)."""
    st = trip(rig)
    pre, table = rig.lib.presets, rig.router.table
    spawned(rig)
    spawned(rig, at=(100.0, 400.0), keep=True)
    g1, g2 = pre.groups
    assert (g1["id"], g2["id"]) == ("group.1", "group.2") and "kept_by_host" not in g1
    assert sorted(g2["nodes"]) == ["mod.2", "render:acid.2", "render:delay.2",
                                   "render:wobble.2"]
    assert {"acid.2", "wobble.2", "delay.2"} <= patches.spec_names(pre.graph.spec)
    assert g2["renames"] == {"acid": "acid.2", "delay": "delay.2", "wobble": "wobble.2",
                             "mod.1": "mod.2"}
    assert [b.target for b in table.desk() if b.source == "cc:0:48"] == ["fx.acid.speed"]
    (kept,) = g2["kept_by_host"]
    assert kept["source"] == "cc:0:48" and kept["target"] == "fx.acid.2.speed"
    assert graphview.kept_words(kept) == "K1 kept by the preset"
    assert ("lane:0", "fx.acid.2.speed") in {(b.source, b.target) for b in table.routes()}
    frame(rig.panel, "graph")
    vg = st["view"].group("group.2")
    assert vg.kept_by_host == [kept]
    tip = ui_graph.group_tip(rig.panel, st["view"], vg)
    assert "spawned as acid → acid.2, delay → delay.2, wobble → wobble.2, mod.1 → mod.2" in tip
    saved = pre.document("trip twice")["groups"]
    assert "renames" not in saved[1] and "ports" not in saved[1]
    assert saved[1]["kept_by_host"] == [kept]


def test_save_as_patch_writes_that_file_and_nothing_else(rig):
    """**Save as patch…** on party-noita's grouped core: `patches.lift` over
    the loaded parts, `Library.save_patch` — one new file, the spec's shape,
    listed — and the group names it (one undo step, the dirty dot); **update
    patch** writes it again with nothing else touched; a group holding what
    no patch may (a hand-edited preset's `scene`) is refused in words and
    nothing is written."""
    from hyperspace import library
    noita(rig, [ENTRY])
    home = files(rig.lib.home)
    u = watch(rig)
    try:
        assert ui_graph.save_patch(rig.panel, "group.1", "  ", "") == graphview.PATCH_NEEDS_NAME
        assert ui_graph.save_patch(rig.panel, "group.1", "noita core", "the middle") is None
        after = files(rig.lib.home)
        assert set(after) - set(home) == {"patches/noita-core.json"}
        assert {k: v for k, v in after.items() if k in home} == home
        doc = json.loads(after["patches/noita-core.json"])
        assert doc["schema"] == "hyperspace.patch/1" and doc["name"] == "noita core"
        assert doc["note"] == "the middle"
        assert [e.get("file") for e in doc["nodes"]] == ["doublevision", "fractals", "warp"]
        assert [(p["id"], p["was"]) for p in doc["ports"]] == [
            ("in", "scene"), ("out", "tripcolour.image")]
        assert "noita core" in rig.lib.list(library.PATCHES)
        assert rig.lib.presets.groups[0]["patch"] == "noita-core"
        assert u.stack[-1].label == "save noita core as patch noita core"
        assert ui_graph._state(rig.panel)["said"] == "saved noita core as a patch"
        assert ui_graph.save_patch(rig.panel, "group.1", "noita core", "the middle") is None
        assert files(rig.lib.home) == after             # the same text: nothing moved
        assert ui_graph._state(rig.panel)["said"] == "updated patch noita core"
        rig.lib.presets.groups[0]["nodes"].append("render:scene")
        assert ui_graph.save_patch(rig.panel, "group.1", "bad", "") == (
            "scene is the frame's; left out")
        assert files(rig.lib.home) == after
    finally:
        undo.install(None)


def test_save_as_patch_never_replaces_another_patch_of_that_name(rig):
    """**Save as patch…** named like a patch the library has (acid wash,
    the user's) from a group that is not that patch's: refused in words,
    nothing written, the group unchanged. The group that *is* acid wash's
    (its `patch` the slug) updates it: the file rewritten."""
    with_patch(rig)
    noita(rig, [ENTRY])
    home = files(rig.lib.home)
    assert ui_graph.save_patch(rig.panel, "group.1", "Acid Wash", "") == (
        "a patch named Acid Wash exists — Update patch, or another name")
    assert files(rig.lib.home) == home and "patch" not in rig.lib.presets.groups[0]
    rig.lib.presets.groups[0]["patch"] = "acid-wash"
    assert ui_graph.save_patch(rig.panel, "group.1", "acid wash", "") is None
    after = files(rig.lib.home)
    assert after["patches/acid-wash.json"] != home["patches/acid-wash.json"]
    assert json.loads(after["patches/acid-wash.json"])["nodes"][0]["file"] == "doublevision"


def test_the_browser_lists_each_patch_with_its_boundary_in_words(rig, monkeypatch):
    """The head's **patches** chip opens the list: each patch's name, its
    note and its boundary in words (the desk's glyph for K1); the canvas's
    menu offers **spawn ▸** with the same list, at the click."""
    st = trip(rig)
    (row,) = ui_graph.patch_list(rig.panel)
    assert (row["name"], row["slug"]) == ("acid wash", "acid-wash")
    assert row["note"].startswith("acid → wobble through a delay")
    assert row["words"] == "in: picture · out: picture · wants: band 1, K1, right hand y"
    drawn = []
    real_selectable, real_chip = imgui.selectable, ui_graph.ui.chip
    monkeypatch.setattr(ui_graph.ui, "chip", lambda label, *a, **k: (
        label == "patches##graph" or real_chip(label, *a, **k)))
    monkeypatch.setattr(imgui, "selectable", lambda label, *a, **k: (
        drawn.append(label), real_selectable(label, *a, **k))[1])
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    assert "acid wash##patch.acid-wash" in drawn
    monkeypatch.undo()
    spawns = []
    monkeypatch.setattr(ui_graph, "spawn", lambda panel, slug, at=None, splice=None:
                        spawns.append((slug, at)))
    monkeypatch.setattr(imgui, "begin_menu", lambda label, *a: label == "spawn")
    monkeypatch.setattr(imgui, "end_menu", lambda: None)
    monkeypatch.setattr(imgui, "menu_item_simple", lambda label, *a, **k:
                        label == "acid wash##spawn.acid-wash")
    st["pan"] = (10.0, 20.0)
    ui_graph._spawn_menu(rig.panel, (110.0, 220.0))
    assert spawns == [("acid-wash", (100.0, 200.0))]


def test_the_spawn_menu_open_two_frames_lists_the_patches_once(rig, monkeypatch):
    """The canvas's **spawn ▸** (and a drag) asks for the list every frame:
    the library is listed and each file looked up once per `ui_presets`
    poll, not once a frame; our own save re-lists at once."""
    from hyperspace import ui_presets
    trip(rig)
    ui_presets.invalidate(rig.panel, "patches")
    lists, paths = [], []
    lib = rig.panel.library
    real_list, real_path = lib.list, lib.path_of
    monkeypatch.setattr(lib, "list", lambda g, **k: (lists.append(g), real_list(g, **k))[1])
    monkeypatch.setattr(lib, "path_of", lambda g, n: (paths.append(n), real_path(g, n))[1])
    monkeypatch.setattr(imgui, "begin_menu", lambda *a: False)
    ui_graph._spawn_menu(rig.panel, (0.0, 0.0))
    first = list(paths)
    assert lists == ["patches"] and first.count("acid wash") == 1
    ui_graph._spawn_menu(rig.panel, (0.0, 0.0))
    assert lists == ["patches"] and paths == first          # the second frame: no disk
    ui_presets.invalidate(rig.panel, "patches")
    assert [r["slug"] for r in ui_graph.patch_list(rig.panel)] == ["acid-wash"]
    assert lists == ["patches", "patches"]


def test_a_dragged_patch_lights_a_cable_it_can_splice_into_and_lands_on_release(rig,
                                                                                 monkeypatch):
    """The drag (hand check 396 covers the gesture itself): while a browser
    line is dragged, a picture cable under the pointer lights when the
    patch's one inlet and one outlet match it; let go there, it is spliced."""
    st = trip(rig)
    cable = next(c for c in st["view"].cables if c.kind == "render"
                 and (c.ref.src, c.ref.dst) == ("scene", "plasma.image"))
    monkeypatch.setattr(graphview, "cable_near", lambda *a, **k: cable)
    st["patch_drag"] = "acid-wash"
    ui_graph._drop_target(rig.panel, st, st["view"])
    assert st["drop_cable"] == cable.id and st["drop_why"] == ""
    got = []
    monkeypatch.setattr(ui_graph, "spawn", lambda panel, slug, at=None, splice=None:
                        got.append((slug, splice)))
    ui_graph._patch_drop(rig.panel, st, st["view"])
    assert got == [("acid-wash", cable)] and st["patch_drag"] is None
