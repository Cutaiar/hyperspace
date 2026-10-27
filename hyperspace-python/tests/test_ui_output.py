"""Plan 35 T6 (U): the OUTPUT page as a view of the wires, headless.

Each window's block says what its picture port is wired to (`ui.
shows_line`), offers the graph's pictures in a combo (`graphview.
picture_sources`, `picture_choices`) whose pick is a GRAPH edit
(`graphview.set_picture`: `render_wire` into `output.N.image`, `ground`
for "nothing", the override removed for "as All outputs"), keeps the two
mutes as the window's own (never the preset), and writes "hands through the
effects" as wiring (`graphview.set_through`: `graphmigrate.through_wires`,
plan 36 T1 — only the wires it names). Every edit lands through GRAPH's `_land`: one
undo step, the same refusals, and an edit put back saves in the lowest
schema again (R10)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from test_graph_edit import free_rig

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace import graphview
from hyperspace.ui import shows_line

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "presets"
DEFAULT = M.wired_of(G.Wiring())          # the factory frame, as a load wires it
ACID = M.wired_section(M.renamed({"wires": [{"from": "frame", "to": "acid.image"},
                                            {"from": "acid", "to": "fx.image"}]}),
                       G.read_graph({"wires": [{"from": "frame", "to": "acid.image"},
                                               {"from": "acid", "to": "fx.image"}]}))


def _with(section: dict, *pairs) -> dict:
    """`section` with `pairs` wired — each in place of the wire into its
    port (plan 36 T2: the faces' pattern wire too: one wire into a port)."""
    out = copy.deepcopy(section)
    into = {b for _, b in pairs if b not in G.MANY_PORTS}
    out["wires"] = [*(w for w in out.get("wires", []) if w["to"] not in into),
                    *({"from": a, "to": b} for a, b in pairs)]
    return out


def _pairs(section: dict) -> list[tuple[str, str]]:
    return [(w["from"], w["to"]) for w in section.get("wires", [])]


def test_the_output_block_says_what_it_shows():
    """`shows:` is the source of the window's picture port, by its label;
    "as All outputs" with no wire of its own; "nothing — its ground" for a
    `ground` wire, or with nothing anywhere."""
    blank = json.loads((FIXTURES / "blank-frame.json").read_text())["graph"]
    cases = {
        "default": (DEFAULT, "shows: as All outputs", "shows: as All outputs"),
        "channel": (_with(DEFAULT, ("channel.a", "output.2.image")),
                    "shows: as All outputs", "shows: Channel A"),
        "blank": (blank, "shows: nothing — its ground", "shows: nothing — its ground"),
    }
    for name, (section, one, two) in cases.items():
        spec = G.read_graph(section)
        assert spec.wired and not spec.notes, name
        assert shows_line(spec, 1) == one, name
        assert shows_line(spec, 2) == two, name
    # `ground` into a window's picture: nothing, though All outputs has one
    spec = G.read_graph(_with(DEFAULT, ("ground", "output.2.image")))
    assert shows_line(spec, 2) == "shows: nothing — its ground"
    # All outputs' own block: its picture's source
    assert shows_line(G.read_graph(DEFAULT), None) == "shows: Look-back"
    assert shows_line(G.read_graph(blank), None) == "shows: nothing — its ground"


def test_the_combo_offers_the_graphs_pictures_in_area_order():
    """`picture_sources`: every picture-making node the section reaches or
    declares, MEDIA → SCENE → LOOK-BACK → EFFECTS; no geometry, no window."""
    spec = G.read_graph(_with(ACID, ("channel.a", "shape.faces")))
    assert graphview.picture_sources(spec) == [
        "channel.a", "scene", "hands.layer", "lookback", "acid"]
    assert graphview.picture_choices(spec, "output.2.image") == [
        "as All outputs", "nothing", "channel.a", "scene", "hands.layer", "lookback", "acid"]
    assert graphview.picture_choices(spec, "output.all.image")[0] == "nothing"
    assert graphview.picture_now(spec, "output.2.image") == "as All outputs"
    assert graphview.picture_now(spec, "output.all.image") == "acid"


def test_output_offers_a_channel_with_a_source_and_picking_wires_it(tmp_path):
    """R17: OUTPUT's combo also offers every channel whose bin holds a
    source, though nothing wires it yet — after the graph's own pictures,
    by label — and its pick wires `channel.<c>` straight into the window's
    picture (or All outputs'), one landing. An empty channel is not
    offered, nor is a filled one on the look-back's capture."""
    from types import SimpleNamespace as NS

    reg = NS(media=NS(channels={"a": NS(bin=[None, None]), "c": NS(bin=[None, "clip-1"]),
                                "b": NS(bin=["still-2"])}))
    spec = G.read_graph(DEFAULT)
    got = graphview.picture_choices(spec, "output.2.image", reg)
    # (plan 36 T2: the faces' pattern is a picture of the graph's: a wire's)
    assert got == ["as All outputs", "nothing", "pattern", "scene", "hands.layer", "lookback",
                   "channel.b", "channel.c"]
    assert graphview.picture_label(spec, "channel.b") == "Channel B"
    assert graphview.picture_choices(spec, "output.all.image", reg)[-2:] == [
        "channel.b", "channel.c"]
    assert "channel.b" not in graphview.picture_choices(spec, "lookback.capture", reg)
    # a channel the graph wires already is listed once, where the graph has it
    both = G.read_graph(_with(DEFAULT, ("channel.c", "shape.faces")))
    assert graphview.picture_choices(both, "output.2.image", reg) == [
        "as All outputs", "nothing", "channel.c", "scene", "hands.layer", "lookback",
        "channel.b"]
    rig, e, pushed = free_rig(tmp_path, *_pairs(DEFAULT))
    assert graphview.set_picture(e, "output.2.image", "channel.b") is None
    assert G.Wire("channel.b", "output.2.image") in rig.presets.graph.spec.wires
    assert shows_line(rig.presets.graph.spec, 2) == "shows: Channel B" and len(pushed) == 1
    assert graphview.set_picture(e, "output.all.image", "channel.c") is None
    assert G.Wire("channel.c", "output.all.image") in rig.presets.graph.spec.wires
    assert len(pushed) == 2


def test_picking_a_picture_wires_the_output(tmp_path):
    """The combo's pick of `channel.a` lands `channel.a → output.2.image` in
    one undo step; "nothing" is `ground` there; "as All outputs" removes
    the override, and the undo steps back through each."""
    from test_undo import settle

    # (the section's own wire first: the order a landing writes, `_frame_order`)
    section = {**DEFAULT, "wires": [{"from": "channel.a", "to": "shape.faces"},
                                    *(w for w in DEFAULT["wires"] if w["to"] != "shape.faces")]}
    rig, e, pushed = free_rig(tmp_path, *_pairs(section), undo_rig=True)
    before = rig.presets.graph.spec.to_json()
    assert graphview.set_picture(e, "output.2.image", "channel.a") is None
    spec = rig.presets.graph.spec
    assert G.Wire("channel.a", "output.2.image") in spec.wires and len(pushed) == 1
    assert graphview.picture_now(spec, "output.2.image") == "channel.a"
    assert shows_line(spec, 2) == "shows: Channel A"
    settle(rig)
    assert graphview.set_picture(e, "output.2.image", "nothing") is None
    assert G.Wire("ground", "output.2.image") in rig.presets.graph.spec.wires
    settle(rig)
    assert graphview.set_picture(e, "output.2.image", "as All outputs") is None
    assert rig.presets.graph.spec.to_json() == before and len(pushed) == 3
    settle(rig)
    # (a pick that is so already lands nothing)
    assert graphview.set_picture(e, "output.2.image", "as All outputs") is None
    assert e.said == "already so" and len(pushed) == 3
    assert rig.undo.undo()
    assert G.Wire("ground", "output.2.image") in rig.presets.graph.spec.wires
    assert rig.undo.undo()
    assert G.Wire("channel.a", "output.2.image") in rig.presets.graph.spec.wires
    assert rig.undo.undo()
    assert rig.presets.graph.spec.to_json() == before
    # the same refusals GRAPH gives: a picture is no geometry
    assert graphview.set_picture(e, "output.2.image", "shape") is not None
    # All outputs' block: "nothing" takes its picture's wire away
    assert graphview.set_picture(e, "output.all.image", "nothing") is None
    assert graphview.picture_now(rig.presets.graph.spec, "output.all.image") == "nothing"


def test_through_writes_the_wiring(tmp_path):
    """`set_through(e, 2, True)` lands `through_wires(…, 2)` — the
    composite and the copies of the run into the window's picture, `ground`
    on its hands, one undo step; `False` takes them and their wires away,
    the section its former `to_json()` again. Plan 36 T1: a picture picked
    while through is that one wire — the chain stays, faint."""
    rig, e, pushed = free_rig(tmp_path, *_pairs(ACID))
    gs = rig.presets.graph
    before = gs.spec.to_json()
    want = M.through_wires(G.read_graph(before), 2)
    assert graphview.set_through(e, 2, True) is None and len(pushed) == 1
    got = gs.spec.to_json()
    assert all(x in got["nodes"] for x in want if "kind" in x)
    assert all(x in got["wires"] for x in want if "kind" not in x)
    assert G.through_layer(gs.spec.wiring(), 2) == "hands.layer"
    assert graphview.is_through(gs.spec, 2) and not graphview.is_through(gs.spec, 1)
    assert shows_line(gs.spec, 2) == "shows: as All outputs · the hands through the effects"
    assert graphview.set_through(e, 2, True) is None and e.said == "already so"
    assert graphview.set_through(e, 2, False) is None and len(pushed) == 2
    assert gs.spec.to_json() == before
    # a picture picked while through: that one wire — the chain stays,
    # reaching nothing (faint), and so does the ground on the hands
    assert graphview.set_through(e, 2, True) is None
    thru = gs.spec.to_json()
    assert graphview.set_picture(e, "output.2.image", "scene") is None
    got = gs.spec.to_json()
    assert got["nodes"] == thru["nodes"]
    assert sorted(map(str, got["wires"])) == sorted(map(str, [
        *(x for x in thru["wires"] if x["to"] != "output.2.image"),
        {"from": "scene", "to": "output.2.image"}]))
    assert {"composite", "copy"} <= graphview.unreached(gs.spec)
    # refused in words: a window with its own picture, a frame laying no hands
    why = graphview.set_through(e, 2, True)
    assert why == graphview.THROUGH_OWN_PICTURE.format(label="Output 2", src="Scene")


def test_through_needs_a_hands_layer_over_all_outputs(tmp_path):
    """R11: "hands through the effects" puts All outputs' hands layer
    through; a frame that lays none has no hands to put through."""
    blank = json.loads((FIXTURES / "blank-frame.json").read_text())["graph"]
    _, e, pushed = free_rig(tmp_path, *_pairs(blank))
    assert graphview.set_through(e, 2, True) == graphview.THROUGH_NO_LAYER
    assert pushed == []


def test_a_picture_put_back_saves_the_untouched_frame(tmp_path):
    """A factory preset, a picture picked for output 2 and put back — the
    frame is the migrated one again, so the save is the untouched preset's
    (row 394: `/6` either way, and the same graph)."""
    from test_plan31_wiring import make_app

    app = make_app(tmp_path)
    app.lib.load("presets", "party-trip")
    gs = app.presets.graph
    untouched = app.presets.document("party-trip")
    assert untouched["schema"] == M.WIRED_SCHEMA
    e = graphview.Edit(graph=gs, push=lambda label: None)
    assert graphview.set_picture(e, "output.2.image", "scene") is None
    assert G.Wire("scene", "output.2.image") in gs.spec.wires    # (plan 28's words: /2)
    assert graphview.set_picture(e, "output.2.image", "nothing") is None
    edited = app.presets.document("party-trip")
    assert edited["schema"] == M.WIRED_SCHEMA and edited["graph"] != untouched["graph"]
    assert graphview.set_picture(e, "output.2.image", "as All outputs") is None
    assert app.presets.document("party-trip") == untouched
    assert graphview.set_through(e, 2, True) is None      # (party-trip lays All outputs' hands)
    assert app.presets.document("party-trip")["graph"] != untouched["graph"]
    assert graphview.set_through(e, 2, False) is None
    assert app.presets.document("party-trip") == untouched


def test_open_on_graph_selects_the_window(tmp_path):
    """"open on GRAPH": the GRAPH page, the window's node selected there
    on its next draw (the request then spent)."""
    from test_ui_shell import build_rig, frame

    from hyperspace import ui_graph
    from hyperspace.ui import PAGE_KEYS

    with build_rig(tmp_path) as rig:
        ui_graph.select_node(rig.panel, "output.2")
        assert rig.panel.page == PAGE_KEYS.index("graph")
        assert ui_graph._state(rig.panel)["select_node"] == "render:output.2"
        for _ in range(2):
            frame(rig.panel)
        assert "select_node" not in ui_graph._state(rig.panel)


def test_the_mutes_are_not_the_preset(tmp_path, monkeypatch):
    """Row 374: `output.2.scene` ("picture") is the window's mute — toggling
    it leaves the preset clean and its section as it was. The page draws
    each window's combo, its two mutes and "hands through the effects"."""
    from test_presets import put
    from test_ui_shell import _output_page, build_rig

    from hyperspace.library import PRESETS

    with build_rig(tmp_path) as rig:
        put(rig.lib.home, "Free", schema="hyperspace.preset/6", graph=ACID)
        rig.lib.load(PRESETS, "Free")
        gs = rig.lib.presets.graph
        before = gs.spec.to_json()
        assert not rig.lib.is_dirty(PRESETS)
        rig.reg["output.2.scene"].set(False)
        assert not rig.lib.is_dirty(PRESETS) and gs.spec.to_json() == before
        drawn, _ = _output_page(rig, monkeypatch)
        assert drawn.count("picture") == 4 and drawn.count("hands through the effects") == 4
        assert rig.reg["output.2.scene"].value is False
        assert not rig.lib.is_dirty(PRESETS) and gs.spec.to_json() == before
