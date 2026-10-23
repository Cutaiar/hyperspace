"""Plan 28 N9 — the GRAPH page organised by concern; idle macros off the canvas.

The owner's words of 2026-10-20: "all things audio need to live in one
area; all things geometry should be grouped in another area; all things
shader should be grouped in another area … Also, there are macros sitting
there that don't connect to anything." So the auto layout lays the canvas
in titled areas left to right — controllers → audio (the small *other*
under it) → modulation → geometry → shaders (`graphview.AREA`, the one
table) — each laid out by its own depth, the shaders' chain wrapped in
rows of four; and a node with nothing in and nothing out (an unused
macro, an unpatched LFO, a group no cable reaches, an effect switched off
with no cable) is not drawn: its area shows one idle line that expands to
show them, and the chain a through wire over the off effects. The head's
area chips and a click on a title frame an area.

Headless, on N7's harness (tests/test_graph_legible.py): the shell's rig
with a factory preset loaded through the scratch library, a render graph
built by `graph.default_graph` — party-trip's two-effect graph, and the
real chain of every effect file this build has, wired by each graph
fixture under tests/fixtures/presets — the APC40 as a real
`devices.MidiDevice` over a stand-in adapter, the page drawn for real on
`imgui_node_editor`. No preset is edited or added."""

import json
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed
from test_graph_legible import party
from test_graphview import views
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, ui, ui_graph
from hyperspace.fx import FxState
from hyperspace.outputs import Switches
from hyperspace.routing import Binding

FACTORY = sorted(p.stem for p in (Path(graphview.__file__).parent / "library" / "presets")
                 .glob("*.json"))
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "presets"
WIRED = sorted(p.stem for p in FIXTURES.glob("*.json")
               if "graph" in json.loads(p.read_text()))
REAL = tuple(FxState().names())          # every effect file: the app's chain
CONCERNS = (graphview.AUDIO, graphview.GEOMETRY, graphview.SHADERS)


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    return shell_rig


def load(rig, name, graph=None):
    """Factory preset `name` on the page (party-trip's render graph and
    devices, `party`, or render graph `graph`), its state after two frames."""
    party(rig)
    if graph is not None:
        rig.panel.renderer = NS(_graph=graph)
    rig.lib.load("presets", name)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    return ui_graph._state(rig.panel)


def real_graph(fixture=None):
    """The app's chain (every effect), wired as graph fixture `fixture` says."""
    wiring = G.read_graph(json.loads((FIXTURES / f"{fixture}.json").read_text())["graph"]
                          ).wiring() if fixture else G.Wiring()
    return G.default_graph(views(Switches(), Switches(through=True)), wiring, effects=REAL)


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


def back_wires(view, idle_open=()):
    """The drawn wires (cables between drawn nodes, the through wires) whose
    end is not right of their start on the laid-out canvas, less the
    shaders' row returns (`graphview.returns`)."""
    lay = graphview.layout(view, collapsed=lambda nid: True, idle_open=idle_open)
    shown = {n.id for n in view.nodes if not n.idle or n.area in set(idle_open)}
    x = {nid: xy[0] for nid, xy in lay.nodes.items()}
    ok = graphview.returns(view, lay)
    out = []
    for c in (*view.cables, *lay.throughs):
        a, b = graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)
        if a in shown and b in shown and x[a] >= x[b] and c.id not in ok:
            out.append(c.id)
    return out


# ---------------------------------------------------------------- the areas

def test_every_node_has_one_area_and_the_three_concerns_are_separate(rig):
    """Over every factory preset on party-trip's graph, and over party-trip
    on the app's whole chain wired by each graph fixture: every node is in
    one area of `ORDER`, by the one table; the areas' columns run left to
    right and never share a column — but *other*, under the audio in its
    column — so no audio node stands in a geometry or shader column, nor
    any of those in another's; and no drawn wire runs back or within a
    column but the shaders' row returns."""
    cases = [(name, None) for name in FACTORY]
    cases += [("party-trip", f) for f in (None, *WIRED)]
    for name, fixture in cases:
        graph = real_graph(fixture) if fixture is not None or name == "party-trip" else None
        view = load(rig, name, graph)["view"]
        for n in view.nodes:
            assert n.area in graphview.ORDER, (name, n.id)
            assert n.area == graphview.area_of(n)
        last = -1
        for a in graphview.AREAS:
            cols = columns(view, a)
            if not cols:
                continue
            assert min(cols) > last, (name, fixture, a)
            last = max(cols)
        assert columns(view, graphview.OTHER) <= columns(view, graphview.AUDIO)
        for a in CONCERNS:
            others = set().union(*(columns(view, b) for b in graphview.AREAS if b != a))
            assert not columns(view, a) & others, (name, a)
        assert back_wires(view) == [], (name, fixture)
        assert back_wires(view, graphview.AREAS) == [], (name, fixture)
    # what lands where, on party-trip's graph
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
    drawn = [n for n in view.nodes if not n.idle]
    for a, (tx, ty) in lay.titles.items():
        mine = [n for n in drawn if n.area == a]
        first = min(n.column for n in mine)
        assert tx == first * graphview.COL_W
        assert all(lay.nodes[n.id][1] >= ty + graphview.TITLE_H for n in mine
                   if n.column == first)
    for col in {n.column for n in drawn}:
        here = sorted(((lay.nodes[n.id][1], n) for n in drawn if n.column == col),
                      key=lambda t: t[0])
        for (y0, n0), (y1, _) in pairwise(here):
            assert y1 >= y0 + graphview.height(n0, collapsed=True) + graphview.GAP
    audio = [lay.nodes[n.id][1] for n in view.nodes if n.area == graphview.AUDIO]
    assert lay.titles[graphview.OTHER][1] > max(audio)
    # a saved position wins, and takes no room
    below = next(n.id for n in drawn if n.column == view.node("render:shape").column
                 and lay.nodes[n.id][1] > lay.nodes["render:shape"][1])
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
    # party-trip: 8 macros, 3 LFOs, the cloud, and acid and palette (off)
    # twice — and the media channels' and the backdrop's groups (plan 32)
    assert sum(n.idle for n in view.nodes) == 18
    assert st["said"] == (f"laid out {len(view.nodes) - 18} nodes in 6 areas, every one "
                          "collapsed · 18 idle off the canvas")
    assert st["idle_open"] == set() and st["open"] == set() and rig.lib.presets.layout == {}
    lay = ui_graph.areas_of(st, view)
    assert all(st["applied"][n.id] == lay.nodes[n.id] for n in view.nodes if not n.idle)
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
    assert ui_graph.idle_line(view, lay.idle[graphview.MODULATION]) == (
        "7 idle macros · 3 idle LFOs")
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
    LFO and a group node on no cable alone; a device only while lost or
    off (a connected one is drawn unmapped, a placeholder has rows); a
    modifier, the analyzer, a render node never by this rule (an off
    effect is `build`'s: `effect_off`). The idle words name an off device
    and a lost one apart."""
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
    off = V("device:bridge", "device", "bridge", grey=True, status="bridge · off")
    lost = V("device:pad", "device", "pad", grey=True, status="gamepad · not connected")
    assert graphview.idle_words([off, lost]) == "1 off device · 1 lost device"


def test_an_off_effect_with_no_cable_is_idle_and_a_through_wire_spans_it(rig, monkeypatch):
    """On the app's whole chain, party-trip: an effect switched off with no
    cable on any of its nodes is not drawn — the shaders' line counts them
    ("n off effects") — and a through wire runs over each hidden run from
    the node before it to the next one drawn, so the chain still reads
    from the history to the stack's end. An effect switched on (from the
    FX page) or with a desk row on its switch is drawn. The through wire
    is no render edge: Delete is refused in words, and it is no cable a
    modifier could be dropped onto. Opening the line lays the chain out
    in full, with no through wire."""
    st = load(rig, "party-trip", real_graph())
    view, reg = st["view"], rig.reg
    effects = [n for n in view.nodes if isinstance(n.ref, G.Effect)]
    off = {n.ref.effect for n in effects if not reg[f"fx.{n.ref.effect}.on"].value}
    assert off and off != {n.ref.effect for n in effects}
    for n in effects:
        cabled = any(c.kind != "render" for c in view.cables_of(n.id))
        assert n.idle == (n.ref.effect in off and not cabled), n.id
    hidden = {n.id for n in effects if n.idle}
    lay = ui_graph.areas_of(st, view)
    assert ui_graph.idle_line(view, lay.idle[graphview.SHADERS]).startswith(
        f"{len(hidden)} off effects")
    assert lay.throughs and all(c.kind == graphview.THROUGH for c in lay.throughs)
    for c in lay.throughs:
        a, b = graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)
        assert a not in hidden and b not in hidden and "off effect" in c.label
    # the chain reads end to end over the drawn nodes and the through wires
    succ: dict = {}
    for c in (*view.cables, *lay.throughs):
        a, b = graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)
        if c.kind in ("render", graphview.THROUGH) and a not in hidden and b not in hidden:
            succ.setdefault(a, set()).add(b)
    seen, todo = set(), ["render:history"]
    while todo:
        k = todo.pop()
        if k not in seen:
            seen.add(k)
            todo += list(succ.get(k, ()))
    assert "render:fx" in seen and "render:output.1" in seen
    assert not {c.id for c in lay.throughs} & {c.id for c in view.cables}
    # Delete on a through wire: refused in words
    said = []
    monkeypatch.setattr(ed, "reject_deleted_item", lambda: said.append("rejected"))
    assert ui_graph.delete_through(st) == ui_graph.THROUGH_NO_DELETE
    assert said == ["rejected"] and st["note"] == ui_graph.THROUGH_NO_DELETE
    # one switched on from the FX page, one with a desk row on its switch
    one, two = sorted(off)[:2]
    reg[f"fx.{one}.on"].set(1)
    rig.router.table.add(Binding("note:0:90", f"fx.{two}.on", "toggle"))
    frame(rig.panel, "graph")
    view = st["view"]
    for n in view.nodes:
        if isinstance(n.ref, G.Effect) and n.ref.effect in (one, two):
            assert not n.idle, n.id
    # the line opened: the whole chain, no through wire
    ui_graph.toggle_idle(st, graphview.SHADERS)
    frame(rig.panel, "graph")
    lay = ui_graph.areas_of(st, st["view"])
    assert lay.throughs == [] and all(n.id in lay.cols for n in st["view"].nodes
                                      if isinstance(n.ref, G.Effect))


def test_the_shader_chain_wraps_in_rows_of_four(rig):
    """The app's whole chain, laid out in full (the shaders' line open): the
    shaders take four columns, their depths in Z rows — every row left to
    right, a render cable inside a row running right, one from a row's end
    to the next row's start the only kind that runs back (`returns`); the
    whole canvas about ten columns, not twenty-three."""
    st = load(rig, "party-trip", real_graph())
    view = st["view"]
    for opened in ((), (graphview.SHADERS,)):
        lay = graphview.layout(view, collapsed=lambda nid: True, idle_open=opened)
        assert lay.spans[graphview.SHADERS] <= graphview.SHADER_ROW
        cols = 1 + max(lay.cols.values())
        assert cols <= 10, (opened, cols)
    lay = graphview.layout(view, collapsed=lambda nid: True, idle_open=(graphview.SHADERS,))
    assert lay.spans[graphview.SHADERS] == graphview.SHADER_ROW
    assert max(lay.rows.values()) >= 2
    back = graphview.returns(view, lay)
    assert back
    for c in view.cables:
        if c.kind != "render":
            continue
        a, b = graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)
        if view.node(a).area == view.node(b).area == graphview.SHADERS:
            if lay.rows[a] == lay.rows[b]:
                assert lay.cols[a] < lay.cols[b], c.id
            else:
                assert c.id in back and lay.rows[b] > lay.rows[a]
    # each row starts under the tallest column of the one before
    sh = [n for n in view.nodes if n.id in lay.cols and n.area == graphview.SHADERS]
    for r in range(1, max(lay.rows.values()) + 1):
        above = max(lay.nodes[n.id][1] for n in sh if lay.rows[n.id] == r - 1)
        assert all(lay.nodes[n.id][1] > above for n in sh if lay.rows[n.id] == r)


def test_the_modulation_has_its_own_depth(rig):
    """Check 265's patch (energy → smooth → combine with band 0 → acid mix)
    plus an LFO into a modifier, an LFO onto another LFO's depth and a
    macro onto an LFO's rate: the modulation laid out by its own depth —
    an LFO or macro fed by nothing at 0, a modifier one past what feeds it
    — so no cable runs within or back across its columns."""
    st = load(rig, "party-trip", real_graph())
    table, reg = rig.router.table, rig.reg
    lfo0 = rig.router.address("lfo", 0)
    sm = table.add_modifier("smooth", ["hand:right.energy"], reg)
    comb = table.add_modifier("combine", [sm.address, "lane:0"], reg)
    table.add(Binding(comb.address, "fx.acid.mix", "push", 0.5))
    curve = table.add_modifier("curve", [lfo0], reg)
    table.add(Binding(curve.address, "view.bright", "push", 0.3))
    table.add(Binding(lfo0, "lfo.2.depth", "push", 1.0))
    table.set_macros({"macro.1": {"subs": [{"base": "lfo.3.rate"}]}}, reg)
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    view = st["view"]
    lay = graphview.layout(view, collapsed=lambda nid: True)
    x = {nid: xy[0] for nid, xy in lay.nodes.items()}
    col = {n.id: n.column for n in view.nodes}
    assert col["lfo.1"] < col[curve.id] and col[sm.id] < col[comb.id]
    assert col["macro.1"] < col["lfo.3"] and col["lfo.1"] < col["lfo.2"]
    for c in view.cables:
        a, b = graphview.node_of(view, c.src_port), graphview.node_of(view, c.dst_port)
        if view.node(a).area == view.node(b).area == graphview.MODULATION:
            assert x[a] < x[b], c.id
    assert back_wires(view) == []


# ---------------------------------------------------------------- framing an area

def test_the_area_chips_and_a_title_click_frame_an_area(rig, monkeypatch):
    """The head names the five areas as chips; a click on one frames the
    canvas on that area's drawn boxes (and its idle line); so does a click
    on the canvas's background inside an area's title."""
    st = load(rig, "party-trip")
    chips, framed = [], []
    chip = ui.chip
    monkeypatch.setattr(ui, "chip", lambda label, *a, **k: chips.append(label)
                        or label == "MODULATION##area" or chip(label, *a, **k))
    nav = ed.navigate_to_selection
    monkeypatch.setattr(ed, "navigate_to_selection",
                        lambda *a: (framed.append(list(ed.get_selected_nodes())), nav(*a)))
    frame(rig.panel, "graph")
    assert [c for c in chips if c.endswith("##area")] == [
        f"{graphview.TITLES[a]}##area" for a in graphview.AREAS]
    monkeypatch.setattr(ui, "chip", chip)            # framed in the same frame
    ids = ui_graph.area_nodes(st, st["view"], graphview.MODULATION)
    assert framed and len(framed[-1]) == len(ids)
    assert graphview.idle_id(graphview.MODULATION) in ids and "lfo.1" in ids
    assert "frame_area" not in st
    # a click on GEOMETRY's title
    x0, y0, x1, y1 = st["title_rects"][graphview.GEOMETRY]
    monkeypatch.setattr(ed, "is_background_clicked", lambda: True)
    monkeypatch.setattr(imgui, "get_mouse_pos", lambda: imgui.ImVec2((x0 + x1) / 2,
                                                                     (y0 + y1) / 2))
    frame(rig.panel, "graph")
    assert st["frame_area"] == graphview.GEOMETRY


# ---------------------------------------------------------------- the titles

def test_area_titles_draw(rig, monkeypatch):
    """Each area's title is drawn on the canvas, large and faint, over its
    first column — six on party-trip (OTHER under AUDIO) — behind the nodes
    (before the first node is begun); sized to stay readable zoomed out,
    never under the floor on screen, a short word when the long one will
    not fit its room (to the next title on its row)."""
    st = load(rig, "party-trip")
    texts: list[tuple[str, float, float]] = []
    order: list[str] = []
    real = imgui.get_window_draw_list
    words = set(graphview.TITLES.values()) | set(graphview.SHORT_TITLES.values())

    class Spy:
        def __init__(self, dl):
            self.dl = dl

        def add_text(self, *a):
            if len(a) >= 5 and a[4] in words:
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
    assert [t[0] for t in texts] == [graphview.TITLES[a] for a in graphview.ORDER]
    assert order[:6] == ["title"] * 6 and order[6] == "node"
    lay = st["auto"][1]
    audio = next(t for t in texts if t[0] == "AUDIO")
    assert audio[1] == lay.titles[graphview.AUDIO][0]
    assert ui_graph.titles(lay)[0] == ("CONTROLLERS", 0.0, 0.0)
    # the room: to the next title on the row; OTHER (its own row) its column
    assert ui_graph.title_room(lay, graphview.CONTROLLERS) == (
        lay.titles[graphview.AUDIO][0] - ui_graph.TITLE_GAP)
    # the size: TITLE_SIZE at full zoom; zoomed out TITLE_SCREEN px on
    # screen, held to the room; never under TITLE_FLOOR px: the short word
    fit = ui_graph.title_fit
    assert fit("AUDIO", "AUD", 244.0, 1.0, 13.0, 40.0, 25.0) == ("AUDIO", ui_graph.TITLE_SIZE)
    text, size = fit("SHADERS", "SHD", 4000.0, 10.0, 13.0, 60.0, 30.0)
    assert text == "SHADERS" and size == pytest.approx(ui_graph.TITLE_SCREEN * 10.0)
    text, size = fit("CONTROLLERS", "CTRL", 244.0, 6.0, 13.0, 100.0, 35.0)
    assert text == "CTRL" and size >= ui_graph.TITLE_FLOOR * 6.0
    assert size * 35.0 / 13.0 <= 244.0 + 1e-6
    assert fit("CONTROLLERS", "CTRL", 10.0, 6.0, 13.0, 100.0, 35.0) == (
        "CTRL", ui_graph.TITLE_FLOOR * 6.0)


def test_the_page_draws_with_the_areas_in_every_state(rig):
    """The page drawn once per state on the app's whole chain: idle lines
    shut and open, every node expanded with every port, an area framed,
    after a tidy — nothing raises; the head counts the drawn nodes and the
    idle ones."""
    st = load(rig, "party-trip", real_graph())
    view = st["view"]
    idle = sum(n.idle for n in view.nodes)
    assert ui_graph.head_line(st, view).startswith(
        f"{len(view.nodes) - idle} nodes ({idle} idle)")
    for area in st["auto"][1].lines:
        ui_graph.toggle_idle(st, area)
    frame(rig.panel, "graph")
    assert ui_graph.head_line(st, view).startswith(f"{len(view.nodes)} nodes ({idle} idle)")
    ui_graph.expand_all(st, view, True)
    st["patched_only"] = False
    frame(rig.panel, "graph")
    st["frame_area"] = graphview.SHADERS
    frame(rig.panel, "graph")
    st["tidy"] = True
    frame(rig.panel, "graph")
    assert st["idle_open"] == set() and st["open"] == set()
    frame(rig.panel, "system")
