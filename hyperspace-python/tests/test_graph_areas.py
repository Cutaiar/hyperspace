"""Plan 28 N9 — the GRAPH page organised by concern; idle macros off the canvas.

The owner's words of 2026-10-20: "all things audio need to live in one
area; all things geometry should be grouped in another area; all things
shader should be grouped in another area … Also, there are macros sitting
there that don't connect to anything." So the auto layout lays the canvas
in titled areas left to right — controllers → audio (the small *other*
under it) → modulation → geometry → shaders (`graphview.AREA`, the one
table) — and a node with nothing in and nothing out (an unused macro, an
unpatched LFO, a group no cable reaches) is not drawn: its area shows one
idle line that expands to show them.

Headless, on N7's harness (tests/test_graph_legible.py): the shell's rig
with a factory preset loaded through the scratch library, a render graph
built by `graph.default_graph`, the APC40 as a real `devices.MidiDevice`
over a stand-in adapter, the page drawn for real on `imgui_node_editor`.
No preset is edited or added."""

from itertools import pairwise
from pathlib import Path

import pytest
from imgui_bundle import imgui
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, ui_graph
from hyperspace.routing import Binding

FACTORY = sorted(p.stem for p in (Path(graphview.__file__).parent / "library" / "presets")
                 .glob("*.json"))
CONCERNS = (graphview.AUDIO, graphview.GEOMETRY, graphview.SHADERS)


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def load(rig, name):
    """Factory preset `name` on the page (party-trip's render graph and
    devices, `party`), its state after two frames."""
    party(rig)
    rig.lib.load("presets", name)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


def drawn_ids(rig, monkeypatch):
    """The nodes the page draws next frame (its `_node` calls)."""
    seen: list[str] = []
    real = ui_graph._node
    monkeypatch.setattr(ui_graph, "_node", lambda st, n, drawn: (seen.append(n.id),
                                                                  real(st, n, drawn)))
    frame(rig.panel, "graph")
    monkeypatch.setattr(ui_graph, "_node", real)
    return seen


def columns(view, area):
    return {n.column for n in view.nodes if n.area == area}


# ---------------------------------------------------------------- the areas

def test_every_node_has_one_area_and_the_three_concerns_are_separate(rig):
    """Over every factory preset: every node is in one area of `ORDER`, by
    the one table; the areas' columns run left to right and never share a
    column — but *other*, which sits under the audio in its column — so no
    audio node stands in a geometry or shader column, nor any of those in
    another's; and no cable runs back or within a column: every wire reads
    left to right."""
    for name in FACTORY:
        view = load(rig, name)["view"]
        for n in view.nodes:
            assert n.area in graphview.ORDER, (name, n.id)
            assert n.area == graphview.area_of(n)
        last = -1
        for a in graphview.AREAS:
            cols = columns(view, a)
            if not cols:
                continue
            assert min(cols) > last, (name, a)
            last = max(cols)
        assert columns(view, graphview.OTHER) <= columns(view, graphview.AUDIO)
        for a in CONCERNS:
            others = set().union(*(columns(view, b) for b in graphview.AREAS if b != a))
            assert not columns(view, a) & others, (name, a)
        x = {n.id: n.column for n in view.nodes}
        back = [c.id for c in view.cables
                if x[graphview.node_of(view, c.src_port)] >= x[graphview.node_of(view, c.dst_port)]]
        assert back == [], (name, back)
    # what lands where, on the last one loaded and on party-trip
    view = load(rig, "party-trip")["view"]
    area = {n.id: n.area for n in view.nodes}
    assert {area[k] for k in ("device:apc40", "device:apc40/global", "source:key",
                              "device:leap", "device:pad")} == {graphview.CONTROLLERS}
    assert {area[k] for k in (graphview.ANALYZER, "group:band", "group:tempo", "group:master",
                              "group:audio", "group:scene")} == {graphview.AUDIO}
    assert {area[k] for k in ("lfo.1", "macro.1", "group:lfo")} == {graphview.MODULATION}
    assert {area[k] for k in ("render:shape", "render:eye", "render:ghost", "render:scene",
                              "render:hands", "render:cover", "group:hands",
                              "group:cloud")} == {graphview.GEOMETRY}
    assert {area[k] for k in ("render:history", "render:acid", "render:palette", "render:fx",
                              "render:capture", "render:output.1", "render:output.2",
                              "group:output")} == {graphview.SHADERS}
    assert {area[k] for k in ("group:preset", "group:ui", "group:desk",
                              "group:missing")} == {graphview.OTHER}


def test_auto_layout_stacks_each_area_and_keeps_saved_positions(rig):
    """Each area's nodes are stacked down its columns under its title, never
    on one another; *other* is titled under the audio's last node; a node
    with a saved position keeps it on the canvas and takes no room in its
    column (the node under it moves up into it)."""
    st = load(rig, "party-trip")
    view = st["view"]
    lay = ui_graph.areas_of(st, view)
    assert set(lay.titles) == set(graphview.ORDER)
    for a, (tx, ty) in lay.titles.items():
        mine = [n for n in view.nodes if n.area == a and not n.idle]
        first = min(n.column for n in mine)
        assert tx == first * graphview.COL_W
        assert all(lay.nodes[n.id][1] >= ty + graphview.TITLE_H for n in mine
                   if n.column == first)
    for col in {n.column for n in view.nodes}:
        here = sorted(((lay.nodes[n.id][1], n) for n in view.nodes
                       if n.column == col and not n.idle), key=lambda t: t[0])
        for (y0, n0), (y1, _) in pairwise(here):
            assert y1 >= y0 + graphview.height(n0, collapsed=True) + graphview.GAP
    audio = [lay.nodes[n.id][1] for n in view.nodes if n.area == graphview.AUDIO]
    assert lay.titles[graphview.OTHER][1] > max(audio)
    # a saved position wins, and takes no room
    below = next(n.id for n in view.nodes if n.column == view.node("render:shape").column
                 and lay.nodes[n.id][1] > lay.nodes["render:shape"][1] and not n.idle)
    rig.lib.presets.layout["render:shape"] = [4000, 4000]
    frame(rig.panel, "graph")
    assert st["applied"]["render:shape"] == (4000.0, 4000.0)
    assert st["applied"][below][1] < lay.nodes[below][1]


def test_tidy_relays_into_areas_and_says_so(rig):
    """Tidy collapses every node, closes the idle lines, forgets every
    position and lays the canvas out in its areas again — and the head says
    so: the nodes it laid out, in how many areas, how many idle it left off."""
    st = load(rig, "party-trip")
    view = st["view"]
    ui_graph.toggle_idle(st, graphview.MODULATION)
    ui_graph.toggle_open(st, "render:shape")
    rig.lib.presets.layout["render:eye"] = [900, 40]
    frame(rig.panel, "graph")
    st["tidy"] = True
    frame(rig.panel, "graph")
    idle = sum(n.idle for n in view.nodes)
    assert idle == 12
    assert st["said"] == (f"laid out {len(view.nodes) - idle} nodes in 6 areas, every one "
                          f"collapsed · {idle} idle off the canvas")
    assert st["idle_open"] == set() and st["open"] == set() and rig.lib.presets.layout == {}
    lay = ui_graph.areas_of(st, view)
    assert all(st["applied"][n.id] == lay.nodes[n.id] for n in view.nodes)
    assert st["applied"][graphview.idle_id(graphview.MODULATION)] == lay.lines[
        graphview.MODULATION]


# ---------------------------------------------------------------- idle nodes

def test_an_idle_macro_is_not_drawn_and_a_connected_one_is(rig, monkeypatch):
    """party-trip's eight macros have no label, no subscriber and no cable:
    none is drawn. A subscriber made on the canvas draws its macro (as any
    node, in the modulation's stack); deleting it takes the macro off again.
    A route that names a macro as its `scale` keeps it drawn (the scale is
    said on the cable, not drawn as one)."""
    st = load(rig, "party-trip")
    view = st["view"]
    macros = [n.id for n in view.nodes if n.kind == "macro"]
    assert len(macros) == 8 and all(view.node(m).idle for m in macros)
    seen = drawn_ids(rig, monkeypatch)
    assert not set(macros) & set(seen) and "lfo.1" in seen and "lfo.2" not in seen
    sub = ui_graph.connect(rig.panel, "bus:macro.3", "base:view.bright")
    assert not isinstance(sub, graphview.Refusal)
    frame(rig.panel, "graph")
    view = st["view"]
    assert not view.node("macro.3").idle and ui_graph.drawn_node(st, view.node("macro.3"))
    assert "macro.3" in drawn_ids(rig, monkeypatch)
    lay = ui_graph.areas_of(st, view)
    assert lay.nodes["macro.3"][1] < lay.lines[graphview.MODULATION][1]
    cable = next(c for c in view.cables if c.kind == "sub")
    ui_graph.disconnect(rig.panel, cable)
    frame(rig.panel, "graph")
    assert st["view"].node("macro.3").idle and "macro.3" not in drawn_ids(rig, monkeypatch)
    # a route's scale names a macro: not idle
    rig.router.table.add(Binding("lane:0", "view.bright", "push", 0.3, scale="macro.5"))
    frame(rig.panel, "graph")
    assert not st["view"].node("macro.5").idle and st["view"].node("macro.6").idle


def test_the_idle_macros_line_expands_to_show_them_and_the_picker_still_offers_them(
        rig, monkeypatch):
    """The modulation area's one line says what it holds ("8 idle macros ·
    3 idle LFOs"); its **+** draws them under it, stacked; **-** takes them
    off. The picker still offers every idle macro, and one picked is drawn
    with the line shut (it has a label now)."""
    st = load(rig, "party-trip")
    view = st["view"]
    lay = ui_graph.areas_of(st, view)
    ids = lay.idle[graphview.MODULATION]
    assert ui_graph.idle_line(view, ids) == "8 idle macros · 3 idle LFOs"
    assert ui_graph.idle_line(view, lay.idle[graphview.GEOMETRY]) == "1 idle param group"
    line = lay.lines[graphview.MODULATION]
    assert all(lay.nodes[i] == line for i in ids)            # shut: they sit at the line
    ui_graph.toggle_idle(st, graphview.MODULATION)
    seen = drawn_ids(rig, monkeypatch)
    assert set(ids) <= set(seen)
    lay = ui_graph.areas_of(st, view)
    ys = [lay.nodes[i][1] for i in ids]
    assert min(ys) > line[1] and len(set(ys)) == len(ys)
    assert "group:cloud" not in seen                           # the geometry's stays shut
    ui_graph.toggle_idle(st, graphview.MODULATION)
    assert not set(ids) & set(drawn_ids(rig, monkeypatch))
    # the picker (N3) still offers them, and one picked is drawn
    free = ui_graph.macros_free(rig.panel, view)
    assert {m for m in ids if m.startswith("macro.")} <= set(free)
    ui_graph.show_macro(rig.panel, "macro.7", at=(600, 40))
    frame(rig.panel, "graph")
    assert "macro.7" in drawn_ids(rig, monkeypatch)
    assert "macro.7" not in ui_graph.areas_of(st, st["view"]).idle[graphview.MODULATION]


def test_idle_rule_per_kind():
    """`is_idle` by kind: a macro idle only while empty and uncabled; an
    LFO and a group node on no cable alone; a device only while lost (a
    connected one is drawn unmapped, a placeholder has rows); a modifier,
    the analyzer, a render node never."""
    from hyperspace.routing import Macro, Sub
    V = graphview.VNode
    assert graphview.is_idle(V("macro.1", "macro", "m"), {})
    assert not graphview.is_idle(V("macro.1", "macro", "m"), {"macro.1": Macro("named")})
    assert not graphview.is_idle(V("macro.1", "macro", "m"),
                                 {"macro.1": Macro("", [Sub(base="view.bright")])})
    assert not graphview.is_idle(V("macro.1", "macro", "m", wires=1), {})
    assert graphview.is_idle(V("lfo.2", "lfo", "LFO 2"))
    assert graphview.is_idle(V("group:cloud", "group", "cloud"))
    knob = graphview.VPort("param:lfo.2.rate", "rate", "in", param="lfo.2.rate")
    assert not graphview.is_idle(V("lfo.2", "lfo", "LFO 2", ports=[knob]), named={"lfo.2.rate"})
    assert graphview.is_idle(V("device:pad", "device", "pad", grey=True))
    assert not graphview.is_idle(V("device:pad", "device", "pad"))
    assert not graphview.is_idle(V("device:pad", "device", "pad", grey=True, placeholder=True))
    for kind in ("modifier", "analyzer", "render", "output", "source", "template"):
        assert not graphview.is_idle(V("x", kind, "x"))


# ---------------------------------------------------------------- the titles

def test_area_titles_draw(rig, monkeypatch):
    """Each area's title is drawn on the canvas, large and faint, over its
    first column — six on party-trip (OTHER under AUDIO) — behind the nodes
    (before the first node is begun)."""
    st = load(rig, "party-trip")
    texts: list[tuple[str, float, float]] = []
    order: list[str] = []
    real = imgui.get_window_draw_list

    class Spy:
        def __init__(self, dl):
            self.dl = dl

        def add_text(self, *a):
            if len(a) >= 5 and a[4] in graphview.TITLES.values():
                texts.append((a[4], a[2].x, a[2].y))
                order.append("title")
            return self.dl.add_text(*a)

        def __getattr__(self, k):
            return getattr(self.dl, k)

    monkeypatch.setattr(imgui, "get_window_draw_list", lambda: Spy(real()))
    begin = ui_graph.ed.begin_node
    monkeypatch.setattr(ui_graph.ed, "begin_node", lambda nid: (order.append("node"),
                                                                begin(nid)))
    frame(rig.panel, "graph")
    words = [t[0] for t in texts]
    assert words == [graphview.TITLES[a] for a in graphview.ORDER]
    assert order[:6] == ["title"] * 6 and order[6] == "node"
    lay = st["auto"][1]
    audio = next(t for t in texts if t[0] == "AUDIO")
    assert audio[1] == lay.titles[graphview.AUDIO][0]
    assert ui_graph.titles(lay)[0] == ("CONTROLLERS", 0.0, 0.0)
    # its size: TITLE_SIZE at full zoom; zoomed out, TITLE_SCREEN px on screen,
    # but never wider than its area's columns
    assert ui_graph.title_size("AUDIO", 1, 1.0, 13.0, 40.0) == ui_graph.TITLE_SIZE
    assert ui_graph.title_size("SHADERS", 7, 10.0, 13.0, 60.0) == pytest.approx(
        ui_graph.TITLE_SCREEN * 10.0)
    one = ui_graph.title_size("CONTROLLERS", 1, 10.0, 13.0, 100.0)
    assert one * 100.0 / 13.0 == pytest.approx(ui_graph.NODE_W)


def test_the_page_draws_with_the_areas_in_every_state(rig):
    """The page drawn once per state on every concern: idle lines shut and
    open, every node expanded with every port, after a tidy — nothing
    raises; the head counts the drawn nodes and the idle ones."""
    st = load(rig, "party-trip")
    view = st["view"]
    assert ui_graph.head_line(st, view).startswith(f"{len(view.nodes) - 12} nodes (12 idle)")
    for area in st["auto"][1].lines:
        ui_graph.toggle_idle(st, area)
    frame(rig.panel, "graph")
    assert ui_graph.head_line(st, view).startswith(f"{len(view.nodes)} nodes (12 idle)")
    ui_graph.expand_all(st, view, True)
    st["patched_only"] = False
    frame(rig.panel, "graph")
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert st["idle_open"] == set() and st["open"] == set()
    frame(rig.panel, "system")
