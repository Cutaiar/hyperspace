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
    rig.lib.presets.groups = [dict(g) for g in groups or ()]
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
    assert items == ["open", "rename…", "ungroup"]
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
