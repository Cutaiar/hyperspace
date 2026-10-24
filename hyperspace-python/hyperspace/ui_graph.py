"""The GRAPH page (plan 28 N2, N3): both graphs on one canvas; the
modulation edited on it.

`page(panel, dt)` draws `graphview`'s model on one `imgui_node_editor`
canvas: the controllers, the analyzer, the LFOs, the modifiers and the
macros on the left, the params grouped under the render node that owns
them, the render graph's own image / geometry / mask cables, the
outputs last. Cables are coloured by what they carry (`COLOURS`); a value
cable's thickness follows its reading; a dormant one is faint.

**Legible by default** (plan 28 N7, the owner's decisions of 2026-10-20):
every node starts **collapsed** — its title and at most five short lines
(`graphview.summary`: what it holds, how much is patched, its live
reading), no row per port, one ``in`` and one ``out`` stub on its title
line. While either end of a pair is collapsed, every value / trigger
cable between the two nodes is **one wire** (`graphview.VBundle`, drawn
from stub to stub, as thick as it is many, capped; hover lists its
cables; selected, the side pane lists its rows, each route as ROUTING's
`_row`; Delete is refused in words). A render cable stays one wire each,
drawn to a collapsed node's stub. A node's **+** (or the head's **expand
all**) expands it: its ports as N2 drew them — the page's **patched
only** chip and the node's own **all ports / patched only** chip within
— and, both ends expanded, the real cables. A drag onto a collapsed
node's stub opens a picker of its ports (`open_land`, `land`) and lands
through `Edit.connect`; right-click a node for Learn on any of its params.
The collapse state is the page's UI state (`st["open"]`), saved nowhere.
**Tidy** collapses every node, forgets every position and says what it
did; the details chip shows only with a selection on a narrow page.

An expanded node folds its port groups (the hands' axes, the desk's
knobs) one by one. A desk template's node (plan 28 N5) is a subgraph:
collapsed it draws none of its rows; its **+** opens it and its rows are
cables (`is_open`, `drawn_cable`). A desk
layer that is down (SHIFT not latched, or latched) draws its node and its
ports faint. Hovering a cable says its reading and its depth; a
port, its reading; a device, its status. Selecting a route shows its
ROUTING row (`ui_routing._row`, the same widgets, the same table) beside
the canvas — below it while the page is narrow — selecting an effect's
node shows its strip (`ui_fx.strip`), and a modifier's node the
MODIFIERS strip's editor for it (`ui_routing.modifier_block`, plan 28
N7: GRAPH edits the routes and the modifiers; ROUTING points here).

**Editing the modulation** (plan 28 N3): a cable dragged between two
pins (`_create`) and a cable or node deleted (`_delete`) go through
`graphview.Edit` and the table's own calls — the same table ROUTING
edits, so either page shows the other's change next frame, and undo, the
preset's dirt and the referee are theirs. A taken param asks Replace /
Keep (ROUTING's prompt, `ui_routing.ask`); a refusal says why on the
page's head (`st["note"]`) and on the drag. Right-click: a param's `mod`
pin offers the param menu's Learn items (`Panel._ctx_learn_block`, the same
function), a cable offers "insert" (a modifier onto it) and delete, the
canvas the node picker (a modifier of each kind, a macro, and since plan
31 an LFO or an envelope, up to its bank's cap: `add_voice`), a modifier,
macro, LFO or extra envelope node delete (an LFO or envelope through its
bank, one undo step; a lane envelope 1–5 refused). A sequencer lane's
envelope binding is a ``lane`` cable: it is never deleted, only rebound
(a lane's pin dragged onto an envelope's ``fire`` base stub). A modifier node dropped onto a cable is inserted into
it (`dropped`). **The seam with N4** (render edits): `_create` and
`_delete` dispatch by the pins' type through `CREATE` / `DELETE`; value and
trigger cables are this file's handlers, image / geometry / mask N4's.

**Edits** (plan 28 N4, the render graph): a cable dragged between two
image ports is a wire in the preset's graph (`graphview.Edit.wire`),
type-checked while it is dragged — a port of another type, a port that
does not exist, a loop: the cable goes red and the tooltip says the
words a preset file would get; a geometry cable from a hands node into
the scene or the layer is where that node is drawn. Right-click the
canvas for the picker (an effect instance, a hands node, a composite);
right-click a render node to delete it, draw its hands as lines or set
a composite's blend;
Delete takes a selected render cable or node out of the graph. Each
edit is one undo step and dirties the preset; the renderer builds the
graph again from it. Render edits do not go through N3's `_act`:
their handlers (`_create_render`, `_delete_render_cable`,
`_delete_render_node`) land through `render_edit`, whose undo step is
pushed only once the edit is read back and accepted.

**The free graph** (plan 33 U): `frame`, `fx`, the pattern, the backdrop,
the switches and the shape's `faces` port are drawn like the other render
nodes (`graphview.build`). The picker adds an effect or a switch on no
wire, where the menu opened (`add_render`): faint, "reaches nothing",
until it is wired in. A render cable's menu offers "insert effect ▸
<file>" (`insert_effect`); a free effect node let go on a picture cable is
inserted into it (`dropped`, `Edit.place_effect`); a cable of the run
deleted takes its effect out, the run closed over it, and `frame →
fx.image` itself is kept (`graphview.RUN_KEPT`). A compile error colours
an effect node's title and is its hover (`effect_errors`). The selected
effect is the panel's one selection, shared with the FX page
(`Panel.fx_selected`, `share`, `select_effect`).

A node can be moved: where it is dropped is saved, in the
preset's ``layout`` for the look's nodes and the show's for the rig's
(`graphview.home`), and the preset (or the show) is dirty. An unplaced
node takes its place in its **area** (plan 28 N9, `graphview.layout`):
controllers → audio (the small *other* under it) → modulation → geometry
→ shaders, left to right, each titled faintly on the canvas behind its
nodes (`_titles`). A node with nothing in and nothing out — an unused
macro, an unpatched LFO, a group no cable reaches, a lost device — is
not drawn (`drawn_node`): its area shows one line in its place ("8 idle
macros · 3 idle LFOs", `_idle_line`) whose **+** shows them under it so
one can be patched; patched, it is drawn as any node. The picker still
offers every idle macro. **Tidy** (`tidy`) collapses every node, closes
the idle lines, forgets every position on the canvas and lays them all
out again in their areas — one undo step for the positions (`forget`) —
frames the canvas on them and says so on the head ("laid out 36 nodes in
6 areas, every one collapsed · 12 idle off the canvas", or "already
tidy"). The selection shows under the canvas on
the panel's narrow page; the **details beside / below** chip, drawn only
while something is selected, moves it (a page 720 px wide puts it in a
side column by itself, no chip).

**The editor context** is the widget's own C++ object: made on the first
draw of the page, held in the panel's state (``panel._graph``) — not in
this module — so a hot reload of this file keeps drawing on the same
context and makes no second one; destroyed by `close` (`Panel.close`,
which app.py calls on quit and on ⌘R before imgui shuts down). Its
settings file is off (`Config.settings_file = ""`): the positions are
the preset's and the show's, never a NodeEditor.json beside the app.
"""

from __future__ import annotations

import time

from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed

from . import graph as rgraph
from . import graphview, modifiers, ui, ui_fx, ui_routing, undo
from .bands import CEIL
from .graph import Effect
from .library import LibraryError
from .view import RED as RED_RGB

STATE = "_graph"         # the panel's attribute: survives a reload of this module
COLOURS = {
    graphview.VALUE: imgui.ImVec4(0.86, 0.86, 0.88, 1.0),
    graphview.TRIGGER: imgui.ImVec4(1.0, 0.74, 0.28, 1.0),
    graphview.IMAGE: imgui.ImVec4(*RED_RGB, 1.0),     # ui.RED: the one red
    graphview.GEOMETRY: imgui.ImVec4(0.38, 0.72, 1.0, 1.0),
    graphview.MASK: imgui.ImVec4(0.72, 0.52, 1.0, 1.0),
}
DORMANT_ALPHA = 0.22
THIN, THICK = 1.0, 4.5   # a value cable at rest and at full reading
WIRE = 2.5               # a render cable, a trigger
NODE_W = 190.0           # a node's inner width
PIN = 9.0                # a pin's square
SIDE_W = 320.0           # the side column, when the page is wide enough for it
WIDE = 720.0             # …which is this wide; narrower, the selection goes below
BELOW_H = 240.0          # the selection's height below the canvas
TIMES = 120              # draws the SYSTEM line's median is over
PATCHED_TIP = ("Patched only: an expanded node shows just its patched ports — "
               "its own all / patched chip flips it")
TIDY_TIP = ("Collapse every node, forget every position on the canvas and lay them all "
            "out again in their areas — controllers, audio, modulation, geometry, shaders "
            "(⌘Z puts the positions back)")
# plan 28 N9: the areas' titles on the canvas, and the idle lines
TITLE_SIZE = 30.0        # canvas units: an area's title at full zoom
TITLE_SCREEN = 18.0      # px: what it stays on screen while the canvas is zoomed out
TITLE_FLOOR = 12.0       # px: never smaller on screen (review round 1); a short word if need be
TITLE_GAP = 16.0         # canvas units kept clear before the next title on its row
THROUGH_ALPHA = 0.5      # a through wire over off effects: drawn, but plainly not a cable
THROUGH_NO_DELETE = ("a through wire stands for off effects: turn one on (FX) or open the "
                     "off effects line to edit its cables")
AREA_TIP = "Frame the canvas on this area's boxes (a click on its title does the same)" 
TITLE_ALPHA = 0.30       # faint: behind the nodes, never one of them
IDLE_TIP = ("Nothing in, nothing out: not drawn so the canvas stays readable. + shows "
            "them here to patch one; patched, it is drawn like any node. The picker "
            "(right-click the canvas) still offers every idle macro.")
BESIDE_TIP = ("Where the selection's details go: beside the canvas or under it — widen "
              "CONTROLS to give both room (on a page this wide they sit beside by themselves)")
# plan 28 N7: a bundle's thickness follows how many cables it holds, capped
FAINT_TIP = (f"{graphview.REACHES_NOTHING}: no path from it ends at an output, the faces, "
             "the pattern, the backdrop or the run — it never runs. Wire it in, or drop "
             "it on a picture cable")
BUNDLE_STEP = 0.5        # px a cable, past the first
BUNDLE_MAX = 7.0         # the cap: a bundle of ten cables or more (2.5 + 9 × 0.5)
EXPAND_TIP = "Expand this node: a row per port, its real cables"
COLLAPSE_TIP = "Collapse this node: its title and a few lines, one wire per neighbour"
ALL_TIP = ("Expand every node (a row per port, every cable) — or collapse them all back "
           "to a handful of boxes and wires")


# ---------------------------------------------------------------- state and context

def _state(panel) -> dict:
    """The page's state on the panel. Every key by `setdefault`, so a key
    added by a later edit (N3, N4) lands on a dict an older build of this
    file made, across a hot reload."""
    st = panel.__dict__.setdefault(STATE, {})
    for k, v in (("editor", None), ("ids", {}), ("names", {}), ("applied", {}),
                 ("flip", set()), ("folds", set()), ("patched_only", True), ("view", None),
                 ("key", None), ("tidy", False), ("times", []), ("created", 0),
                 ("beside", False)):
        if k not in st:
            st[k] = v
    for k, make in EDIT_STATE:                     # plan 28 N3's keys
        st.setdefault(k, make())
    st.setdefault("said", "")               # plan 28 N4: the last render edit
    # plan 28 N7: the expanded nodes (every other one is collapsed: the
    # default), the bundles drawn last frame by id, how many wires were
    # drawn, a drag let go on a collapsed node's stub (its port picker)
    for k, make in (("open", set), ("bundles", dict), ("wires", int), ("land", lambda: None)):
        st.setdefault(k, make())
    st.setdefault("idle_open", set())       # plan 28 N9: the areas whose idle line is open
    return st


# plan 28 N3: the last refusal's words (shown on the head until the next
# edit), each drawn pin's canvas position (a drop onto a cable is found by
# it), the right-click menu's subject, the canvas point the picker opened at
EDIT_STATE = (("note", str), ("pin_xy", dict), ("menu", lambda: None), ("menu_at", tuple))


def editor(panel):
    """The panel's editor context, made on first use (settings file off)."""
    st = _state(panel)
    if st["editor"] is None:
        cfg = ed.Config()
        cfg.settings_file = ""
        st["editor"] = ed.create_editor(cfg)
        st["created"] += 1
        st["applied"] = {}      # a new context knows no position yet
    return st["editor"]


def close(panel) -> None:
    """Destroy the editor context, if the page ever made one — before
    imgui's own context goes (quit, ⌘R). Safe to call twice."""
    st = panel.__dict__.get(STATE)
    if not st or st.get("editor") is None:
        return
    ctx, st["editor"] = st["editor"], None
    st["applied"] = {}
    ed.destroy_editor(ctx)


def _id(st: dict, name: str) -> int:
    """A stable widget id for a pin, node or cable name (never 0)."""
    ids = st["ids"]
    k = ids.get(name)
    if k is None:
        k = ids[name] = len(ids) + 1
        st["names"][k] = name
    return k


# ---------------------------------------------------------------- the model, per frame

def _layouts(panel) -> tuple[dict | None, dict | None]:
    """(the loaded preset's layout map, the open show's), the live dicts —
    None where the panel has no library."""
    lib = getattr(panel, "library", None)
    presets = getattr(lib, "presets", None)
    project = getattr(lib, "project", None)
    pre = getattr(presets, "layout", None) if presets is not None else None
    if presets is not None and pre is None:
        pre = presets.layout = {}
    show = getattr(project, "layout", None) if project is not None else None
    if project is not None and show is None:
        show = project.layout = {}
    return pre, show


def _lanes(panel):
    a = getattr(panel, "audio", None)
    chain = getattr(a, "chain", None)
    if chain is None or not getattr(a, "on", False):
        return None
    return [float(v) / CEIL for v in chain.lanes[: chain.n]]


def view_of(panel) -> graphview.View | None:
    """The page's view: rebuilt when what it is made of moves
    (`graphview.key`), its readings refreshed every frame."""
    router = ui_routing.router_of(panel)
    if router is None:
        return None
    st = _state(panel)
    reg, table = panel.reg, router.table
    devices = getattr(panel, "devices", None)
    rgraph = getattr(getattr(panel, "renderer", None), "_graph", None)
    gs = getattr(getattr(getattr(panel, "library", None), "presets", None), "graph", None)
    spec = getattr(gs, "spec", None)
    lanes = _lanes(panel)
    k = graphview.key(table, reg, router, devices, rgraph, spec)
    if st["view"] is None or st["key"] != k:
        chain = getattr(getattr(panel, "audio", None), "chain", None)
        bands = (getattr(router, "labels", {}).get("lane")
                 or (getattr(chain, "band_names", None) if chain is not None else None))
        st["view"] = graphview.build(table, reg, router, devices, rgraph, spec,
                                     lanes=lanes, bands=bands, template=template_of(panel))
        st["key"] = k
    else:
        graphview.refresh(st["view"], reg, router, lanes, lambda nid: collapsed(st, nid))
    return st["view"]


def template_of(panel):
    """The loaded preset's desk template (plan 24 C3) as ``(name, rows)`` —
    the rows as the load expanded them, the ones a save compacts against
    (`preset.Presets._desk_part`), else the library's file — or None when
    the preset names none (every factory preset). Read when the view is
    rebuilt, not each frame: a load moves the table's rows, so the view's
    key moves with it."""
    presets = getattr(getattr(panel, "library", None), "presets", None)
    if presets is None or not hasattr(presets, "template_of_loaded"):
        return None
    try:
        ref = presets.template_of_loaded()
        if not ref:
            return None
        at_load = getattr(presets, "template_at_load", None)   # (none before a reload)
        held = at_load() if at_load is not None else None
        if held is not None and held[0] == ref:
            return ref, list(held[1])
        return ref, list(presets.lib.desk_template(ref).get("desk") or [])
    except LibraryError:            # a template that will not read: the overrides alone
        return None


def full(st: dict, nid: str) -> bool:
    """Does expanded node `nid` show every port, not just its patched ones?
    The page's **patched only** chip, flipped by the node's own."""
    return (not st["patched_only"]) != (nid in st["flip"])


def is_open(st: dict, nid: str) -> bool:
    """Is node `nid` expanded (plan 28 N7: every node starts collapsed — its
    title and a few lines, one wire per neighbour)? For a desk template's
    node (plan 28 N5) open is also when its rows are drawn as cables."""
    return nid in st.setdefault("open", set())


def collapsed(st: dict, nid: str) -> bool:
    """Is node `nid` collapsed (the default)?"""
    return not is_open(st, nid)


def toggle_open(st: dict, nid: str) -> None:
    """Expand a collapsed node, or collapse an expanded one."""
    st.setdefault("open", set())
    st["open"] ^= {nid}


def expand_all(st: dict, view: graphview.View, on: bool) -> None:
    """The head's **expand all** (`on`) / **collapse all**."""
    st["open"] = {n.id for n in view.nodes if drawn_node(st, n)} if on else set()


def drawn_node(st: dict, n: graphview.VNode) -> bool:
    """Is node `n` drawn (plan 28 N9)? Every node but an idle one
    (`graphview.VNode.idle`: nothing in, nothing out), which is drawn only
    while its area's idle line is open."""
    return not n.idle or n.area in st.setdefault("idle_open", set())


def _drawn_id(st: dict, view: graphview.View, nid: str) -> bool:
    n = view.node(nid)
    return n is None or drawn_node(st, n)


def toggle_idle(st: dict, area: str) -> None:
    """Open an area's idle line (its idle nodes drawn under it), or close it."""
    st.setdefault("idle_open", set())
    st["idle_open"] ^= {area}


def drawn_cable(st: dict, c: graphview.VCable) -> bool:
    """Is cable `c` drawn this frame as far as subgraphs go: one inside a
    collapsed subgraph node is not."""
    return not c.inside or is_open(st, c.inside)


def hidden_by(st: dict, view: graphview.View, pin: str) -> str:
    """The hover's extra line for a pin whose cables are inside a collapsed
    subgraph (a param's `base` stub a desk template sets): which node holds
    them; "" when none is hidden."""
    held = sorted({c.inside for c in view.cables
                   if c.dst_port == pin and c.inside and not is_open(st, c.inside)})
    names = [view.node(nid).label if view.node(nid) is not None else nid for nid in held]
    return "".join(f"\nset by desk {n} (collapsed: + shows it)" for n in names)


def shown(st: dict, n: graphview.VNode) -> list[graphview.VPort]:
    """The ports node `n` draws: none while it is collapsed (plan 28 N7);
    expanded, `graphview.visible` with this page's state — a desk
    template's node every mapped control."""
    if collapsed(st, n.id):
        return []
    if n.kind == graphview.TEMPLATE:
        return list(n.ports)
    return graphview.visible(n, full(st, n.id), st["folds"])


def forget(panel, view: graphview.View) -> None:
    """The tidy: every position of `view`'s nodes forgotten, in the preset's
    map and the show's — one undo step (the library's marks carry both
    maps, plan 28 N2), so ⌘Z puts them back."""
    pre, show = _layouts(panel)
    ids = {n.id for n in view.nodes}
    if not any(k in ids for m in (pre, show) if m for k in m):
        return
    undo.push("tidy the graph", load=True)
    for m in (pre, show):
        if m:
            for nid in [k for k in m if k in ids]:
                del m[nid]


TIDIED = "laid out {n} nodes in {k} areas, every one collapsed"
TIDIED_IDLE = " · {i} idle off the canvas"
ALREADY_TIDY = "already tidy"


def areas_of(st: dict, view: graphview.View, stored=None) -> graphview.Layout:
    """`graphview.layout` with this page's state: a collapsed node its
    title and lines, an expanded one its ports, the open idle lines'
    nodes under them."""
    return graphview.layout(
        view, stored, lambda nid: full(st, nid) or nid.startswith(f"{graphview.TEMPLATE}:"),
        st["folds"], collapsed=lambda nid: collapsed(st, nid),
        idle_open=st.setdefault("idle_open", set()))


def layout_of(st: dict, view: graphview.View, stored=None) -> dict:
    """`areas_of`'s node positions."""
    return areas_of(st, view, stored).nodes


def tidied(view: graphview.View) -> str:
    """What a tidy that did something says: the nodes it laid out (the
    drawn ones), in how many areas, and how many idle ones it left off."""
    shown = [n for n in view.nodes if not n.idle]
    said = TIDIED.format(n=len(shown), k=len({n.area for n in shown}))
    idle = len(view.nodes) - len(shown)
    return said + (TIDIED_IDLE.format(i=idle) if idle else "")


def tidy(panel, st: dict, view: graphview.View) -> str:
    """The head's **tidy** (plan 28 N7: it always does something you can
    see, or says why not): every node collapsed, every position on the
    canvas forgotten (`forget`, one undo step), every node laid out again
    in its area (plan 28 N9), the idle lines closed — and the head says
    what it did (`tidied`: "laid out 36 nodes in 6 areas, every one
    collapsed · 12 idle off the canvas"), or "already tidy" when nothing
    moved or folded. The canvas is framed on the nodes after it
    (`st["frame"]`)."""
    was_open = bool(st["open"]) or bool(st.setdefault("idle_open", set()))
    st["open"] = set()
    st["idle_open"] = set()
    st["flip"].clear()
    before = dict(st["applied"])
    forget(panel, view)
    auto = layout_of(st, view)
    moved = sum(1 for n in view.nodes if drawn_node(st, n) and (
                before.get(n.id) is None or tuple(round(v) for v in before[n.id])
                != tuple(round(v) for v in auto.get(n.id, (0.0, 0.0)))))
    said = tidied(view) if (moved or was_open) else ALREADY_TIDY
    st["note"], st["said"] = "", said
    st["frame"] = True
    return said


# ---------------------------------------------------------------- the page

def page(panel, dt: float) -> None:
    t0 = time.perf_counter()
    ui._micro("graph")
    view = view_of(panel)
    if view is None:
        imgui.separator()
        imgui.text_disabled("no router attached")
        return
    st = _state(panel)
    sel = _selection(st, view)
    share(panel, st, sel)
    _head(panel, st, view, sel is not None)
    imgui.separator()
    avail = imgui.get_content_region_avail()
    wide = st["beside"] or avail.x >= WIDE
    cw = avail.x - (SIDE_W + imgui.get_style().item_spacing.x if sel and wide else 0.0)
    ch = avail.y - (BELOW_H if sel and not wide else 0.0)
    _canvas(panel, st, view, imgui.ImVec2(max(cw, 80.0), max(ch, 80.0)))
    if sel:
        if wide:
            imgui.same_line()
        if imgui.begin_child("##graph.side", imgui.ImVec2(SIDE_W if wide else 0.0, 0.0)):
            _side(panel, st, view, sel)
        imgui.end_child()
    times = st["times"]
    times.append(time.perf_counter() - t0)
    del times[:-TIMES]


def share(panel, st: dict, sel) -> None:
    """Plan 33 U: the one effect selection (`Panel.fx_selected`) both ways.
    Moved elsewhere since this page last looked (the FX page's row, its
    "show on GRAPH": `select_effect`), the canvas selects that effect's node
    (next frame, `_select`); an effect node selected on the canvas is the
    panel's selection."""
    shared = getattr(panel, "fx_selected", None)
    if shared != st.get("fx_seen"):
        st["fx_seen"] = shared
        if shared:
            st["select"] = shared
        return
    if st.get("select"):                    # the canvas has yet to move to it
        return
    n = sel[1] if sel is not None and sel[0] == "node" else None
    if n is not None and isinstance(n.ref, Effect) and n.ref.effect != shared:
        panel.fx_selected = st["fx_seen"] = n.ref.effect


def select_effect(panel, name: str) -> None:
    """Select effect instance `name` (plan 33 U, the FX page's "show on
    GRAPH"): the panel's selection, and its node selected and centred on the
    canvas next frame — its area's idle line opened if it sits there."""
    st = _state(panel)
    panel.fx_selected = st["fx_seen"] = name
    st["select"] = name


def effect_node(view: graphview.View, name: str) -> graphview.VNode | None:
    """The node effect instance `name` is drawn as: its scene pipeline's
    (named by the instance), else its first."""
    hits = [n for n in view.nodes if isinstance(n.ref, Effect) and n.ref.effect == name]
    return next((n for n in hits if n.ref.name == name), hits[0] if hits else None)


def _select(st: dict, view: graphview.View) -> None:
    """Inside the editor, the nodes drawn: the selection `select_effect` (or
    the FX page) asked for, selected and brought on screen."""
    name = st.get("select")
    if not name:
        return
    n = effect_node(view, name)
    if n is None:
        st.pop("select", None)
        return
    if not drawn_node(st, n):               # on its area's idle line: opened, then next frame
        st.setdefault("idle_open", set()).add(n.area)
        return
    st.pop("select", None)
    ed.clear_selection()
    ed.select_node(ed.NodeId(_id(st, "n:" + n.id)))
    ed.navigate_to_selection(False)


def beside_chip(selected: bool, width: float, beside: bool) -> str | None:
    """The head's details chip (plan 28 N7): shown only while something is
    selected and the page is narrower than `WIDE` (that wide, the details
    sit beside the canvas by themselves), labelled by what a click does."""
    if not selected or width >= WIDE:
        return None
    return "details below" if beside else "details beside"


def head_line(st: dict, view: graphview.View) -> str:
    """The head's counts: the nodes drawn (and how many sit idle, plan 28
    N9), the wires drawn last frame (a bundle is one), the cables they
    stand for, how many are live."""
    live = sum(1 for c in view.cables if not c.dormant)
    drawn = sum(1 for n in view.nodes if drawn_node(st, n))
    idle = sum(1 for n in view.nodes if n.idle)
    nodes = f"{drawn} nodes" + (f" ({idle} idle)" if idle else "")
    return (f"{nodes}  ·  {st['wires']} wires  ·  {len(view.cables)} cables"
            f"  ·  {live} live")


def _head(panel, st: dict, view: graphview.View, selected: bool = False) -> None:
    width = imgui.get_content_region_avail().x
    any_open = bool(st["open"])
    if ui.chip("collapse all##graph" if any_open else "expand all##graph"):
        expand_all(st, view, not any_open)
    if imgui.is_item_hovered():
        imgui.set_tooltip(ALL_TIP)
    imgui.same_line()
    if ui.lit_chip("patched only##graph", st["patched_only"]):
        st["patched_only"] = not st["patched_only"]
        st["flip"].clear()
    if imgui.is_item_hovered():
        imgui.set_tooltip(PATCHED_TIP)
    imgui.same_line()
    if ui.chip("tidy##graph"):
        st["tidy"] = True
    if imgui.is_item_hovered():
        imgui.set_tooltip(TIDY_TIP)
    label = beside_chip(selected, width, st["beside"])
    if label is not None:
        imgui.same_line()
        if ui.chip(f"{label}##graph"):
            st["beside"] = not st["beside"]
        if imgui.is_item_hovered():
            imgui.set_tooltip(BESIDE_TIP)
    # the counts after the chips, cut to what is left of the line
    imgui.same_line()
    line = head_line(st, view)
    imgui.text_disabled(ui.fit_text(line, imgui.get_content_region_avail().x))
    if imgui.is_item_hovered():
        imgui.set_tooltip(line)
    _area_chips(st)
    if st["note"]:
        imgui.text_colored(ui.WARN, st["note"])
    elif st["said"]:                        # plan 28 N4: the last render edit
        imgui.text_disabled(st["said"])
    else:
        imgui.text_disabled(EDIT_HINT)


def _area_chips(st: dict) -> None:
    """The head's area chips (review round 1): CONTROLLERS · AUDIO ·
    MODULATION · MEDIA · GEOMETRY · SHADERS, wrapped to the page; a click frames
    the canvas on that area (`frame_area`, next frame)."""
    for i, a in enumerate(graphview.AREAS):
        label = f"{graphview.TITLES[a]}##area"
        if i:
            imgui.same_line()
            if imgui.get_content_region_avail().x < ui.chip_w(label):
                imgui.new_line()
        if ui.chip(label):
            st["frame_area"] = a
        if imgui.is_item_hovered():
            imgui.set_tooltip(AREA_TIP)


def _place(panel, st: dict, view: graphview.View) -> None:
    """Every node where it belongs this frame: the preset's or the show's
    position, else its place in its area (`areas_of`) — and each area's
    idle line; set on the canvas only when that
    differs from what was last set, so a node being dragged is left alone.
    A tidy (`tidy`) collapses every node and forgets the canvas's positions
    in both maps first."""
    if st["tidy"]:
        st["tidy"] = False
        tidy(panel, st, view)
    pre, show = _layouts(panel)
    stored = {**(show or {}), **(pre or {})}
    k = (id(view), frozenset(st["open"]), frozenset(st["flip"]), st["patched_only"],
         frozenset(st["folds"]), frozenset(st["idle_open"]),
         tuple(sorted((n, tuple(xy)) for n, xy in stored.items())))
    held = st.get("auto")
    if held is None or held[0] != k:          # the areas, kept while nothing moves them
        held = st["auto"] = (k, areas_of(st, view, stored))
    lay = held[1]
    auto = lay.nodes
    applied = st["applied"]
    for n in view.nodes:
        if not drawn_node(st, n):              # N9: an idle node is not on the canvas
            continue
        xy = stored.get(n.id) or auto.get(n.id) or (0.0, 0.0)
        target = (float(xy[0]), float(xy[1]))
        if applied.get(n.id) != target:
            ed.set_node_position(ed.NodeId(_id(st, "n:" + n.id)), imgui.ImVec2(*target))
            applied[n.id] = target
    for area, xy in lay.lines.items():        # plan 28 N9: each area's idle line
        lid = graphview.idle_id(area)
        target = (float(xy[0]), float(xy[1]))
        if applied.get(lid) != target:
            ed.set_node_position(ed.NodeId(_id(st, "n:" + lid)), imgui.ImVec2(*target))
            applied[lid] = target


def _moved(panel, st: dict, view: graphview.View) -> None:
    """A node dropped somewhere new is saved where it lives (the preset's
    map or the show's, `graphview.home`) — once the mouse lets go."""
    if imgui.is_mouse_down(imgui.MouseButton_.left):
        return
    pre, show = _layouts(panel)
    applied = st["applied"]
    for n in view.nodes:
        if not drawn_node(st, n):              # plan 28 N9: an idle node is not on the canvas
            continue
        p = ed.get_node_position(ed.NodeId(_id(st, "n:" + n.id)))
        now = (float(round(p.x)), float(round(p.y)))
        was = applied.get(n.id)
        if was is None or (round(was[0]), round(was[1])) == now:
            continue
        applied[n.id] = now
        m = pre if graphview.home(n) == graphview.PRESET else show
        if m is not None:
            m[n.id] = [int(now[0]), int(now[1])]
        if n.kind == "modifier" or isinstance(n.ref, Effect):   # (plan 33 U: an effect too)
            size = ed.get_node_size(ed.NodeId(_id(st, "n:" + n.id)))
            dropped(panel, view, n.id, (now[0] + size.x / 2, now[1] + size.y / 2))


def _canvas(panel, st: dict, view: graphview.View, size: imgui.ImVec2) -> None:
    ed.set_current_editor(editor(panel))
    ed.begin("##graph", size)
    _place(panel, st, view)
    lay = st["auto"][1]
    _titles(st, lay)                    # plan 28 N9: behind the nodes
    st["errors"] = effect_errors(panel, view)
    drawn: set[str] = set()
    for n in view.nodes:
        if drawn_node(st, n):
            _node(st, n, drawn)
    _select(st, view)                   # plan 33 U: the FX page's selection, here too
    for area in lay.lines:
        _idle_line(st, view, area, lay.idle.get(area, []))
    # plan 28 N7: one wire per node pair while either end is collapsed
    singles, bundles = _wiring(st, view)
    wires = 0
    for c, a, b in singles:
        if a in drawn and b in drawn:
            _cable(st, c, a, b)
            wires += 1
    st["bundles"] = {}
    for b in bundles:
        if b.src_port in drawn and b.dst_port in drawn:
            _bundle(st, b)
            st["bundles"][b.id] = b
            wires += 1
    st["wires"] = wires
    held = ui_routing._state(panel).pop("reveal", None)     # "Route a lane here…"
    if held is not None:
        reveal(st, view, held)
    if st.pop("frame", False):          # a tidy: the canvas framed on its nodes
        ed.navigate_to_content()
    area = st.pop("frame_area", None)   # N9: an area chip or a title clicked
    if area is not None:
        frame_area(st, view, area)
    _title_click(st)
    _create(panel, st, view)
    _delete(panel, st, view)
    _menus(panel, st, view)
    _hover(st, view)
    _moved(panel, st, view)
    ed.end()


def effect_errors(panel, view: graphview.View) -> dict[str, str]:
    """Plan 33 U: each effect node whose file did not compile, by node id →
    the error (`ui_fx`'s words): its title is drawn in the error colour and
    its hover says it."""
    chain = getattr(getattr(panel, "renderer", None), "fx", None)
    fx = getattr(chain, "state", None)
    if fx is None:
        return {}
    out = {}
    for n in view.nodes:
        if isinstance(n.ref, Effect) and n.ref.effect in fx.specs:
            try:
                err = ui_fx._error(chain, fx, n.ref.effect)
            except Exception:  # noqa: BLE001 — a chain that cannot say draws no error
                err = ""
            if err:
                out[n.id] = err
    return out


def titles(lay: graphview.Layout) -> list[tuple[str, float, float]]:
    """The areas' titles to draw (plan 28 N9): (words, x, y) in canvas units,
    over each area's first column, in `graphview.ORDER`."""
    return [(graphview.TITLES.get(a, a.upper()), *lay.titles[a])
            for a in graphview.ORDER if a in lay.titles]


def title_room(lay: graphview.Layout, area: str) -> float:
    """How wide area `area`'s title may be, in canvas units: to the next
    title on its row (less `TITLE_GAP`), else its own columns."""
    x, y = lay.titles[area]
    nxt = [tx for a, (tx, ty) in lay.titles.items() if a != area and ty == y and tx > x]
    if nxt:
        return min(nxt) - x - TITLE_GAP
    return lay.spans.get(area, 1) * graphview.COL_W - (graphview.COL_W - NODE_W)


def title_fit(words: str, short: str, room: float, zoom: float, em: float,
              per_em: float, per_em_short: float) -> tuple[str, float]:
    """An area title's words and size in canvas units (review round 1):
    `TITLE_SIZE`, larger while the canvas is zoomed out so it stays
    `TITLE_SCREEN` px on screen, held to its `room` — and never under
    `TITLE_FLOOR` px on screen: when the word will not fit at that, its
    short form (CTRL, MOD …), at the floor if even that will not.
    `zoom` is the editor's (canvas units a screen pixel: 4 is zoomed out
    four times); `per_em` / `per_em_short` the words' widths at the font's
    size `em`."""
    want = max(TITLE_SIZE, TITLE_SCREEN * zoom)
    floor = TITLE_FLOOR * zoom
    for text, w in ((words, per_em), (short, per_em_short)):
        fits = room * em / w if w > 0 else want
        if fits >= floor:
            return text, min(want, fits)
    return short, floor


def _titles(st: dict, lay: graphview.Layout) -> None:
    """Each area's title, faint and large, on the canvas's own draw list
    (canvas units inside the editor), its foot on the title row's — drawn
    before the nodes, so behind them, and no node of its own (nothing to
    select or drag; a click on it frames its area: `_title_click`)."""
    dl = imgui.get_window_draw_list()
    k = ui.TEXT
    col = ui.u32(imgui.ImVec4(k.x, k.y, k.z, TITLE_ALPHA))
    font, em = imgui.get_font(), imgui.get_font_size()
    zoom = ed.get_current_zoom() or 1.0
    foot = graphview.TITLE_H - 12.0
    rects = st["title_rects"] = {}
    for (words, x, y), area in zip(titles(lay), (a for a in graphview.ORDER
                                                 if a in lay.titles), strict=True):
        short = graphview.SHORT_TITLES.get(area, words)
        text, size = title_fit(words, short, title_room(lay, area), zoom, em,
                               imgui.calc_text_size(words).x, imgui.calc_text_size(short).x)
        wide = imgui.calc_text_size(text).x * size / em
        dl.add_text(font, size, imgui.ImVec2(x, y + foot - size), col, text)
        dl.add_line(imgui.ImVec2(x, y + foot + 2.0), imgui.ImVec2(x + NODE_W, y + foot + 2.0),
                    col, 1.0)
        rects[area] = (x, y + foot - size, x + max(wide, NODE_W), y + foot + 2.0)


def _title_click(st: dict) -> None:
    """A click on the canvas's background inside an area's title frames
    that area (next frame, `frame_area`)."""
    if not ed.is_background_clicked():
        return
    m = imgui.get_mouse_pos()                  # canvas units, inside the editor
    for area, (x0, y0, x1, y1) in st.get("title_rects", {}).items():
        if x0 <= m.x <= x1 and y0 <= m.y <= y1:
            st["frame_area"] = area


def area_nodes(st: dict, view: graphview.View, area: str) -> list[str]:
    """The canvas ids an area's framing selects: its drawn nodes and its
    idle line (the head's area chips, a click on its title)."""
    ids = [n.id for n in view.nodes if n.area == area and drawn_node(st, n)]
    lay = st.get("auto")
    if lay and area in lay[1].lines:
        ids.append(graphview.idle_id(area))
    return ids


def frame_area(st: dict, view: graphview.View, area: str) -> list[str]:
    """Frame the canvas on area `area` (review round 1: how "at a glance"
    holds on a page 390 px wide): its nodes selected, the view brought to
    them, the selection cleared again. Inside the editor. Returns the ids."""
    ids = area_nodes(st, view, area)
    if not ids:
        return ids
    ed.clear_selection()
    for nid in ids:
        ed.select_node(ed.NodeId(_id(st, "n:" + nid)), True)
    ed.navigate_to_selection(True)
    ed.clear_selection()
    return ids


def idle_line(view: graphview.View, ids) -> str:
    """An area's idle line's words: its idle nodes by kind."""
    held = set(ids)
    return graphview.idle_words(n for n in view.nodes if n.id in held)


def _idle_line(st: dict, view: graphview.View, area: str, ids) -> None:
    """An area's idle line (plan 28 N9): one small node standing for the
    nodes with nothing in and nothing out, its **+** drawing them under it
    (its **-** taking them off again)."""
    lid = graphview.idle_id(area)
    ed.begin_node(ed.NodeId(_id(st, "n:" + lid)))
    imgui.push_id(lid)
    opened = area in st["idle_open"]
    imgui.text_disabled(ui.fit_text(idle_line(view, ids), NODE_W - 30))
    imgui.same_line(NODE_W - 30 - PIN)
    if imgui.small_button("-" if opened else "+"):
        toggle_idle(st, area)
    if imgui.is_item_hovered():
        ed.suspend()
        imgui.set_tooltip(IDLE_TIP)
        ed.resume()
    imgui.dummy(imgui.ImVec2(NODE_W, 0))
    imgui.pop_id()
    ed.end_node()


def _pin(st: dict, pin: str, kind, port: graphview.VPort, stub: str, drawn: set[str]) -> None:
    ed.begin_pin(ed.PinId(_id(st, pin)), kind)
    p0 = imgui.get_cursor_screen_pos()
    imgui.dummy(imgui.ImVec2(PIN, PIN))
    dl = imgui.get_window_draw_list()
    col = ui.u32(COLOURS.get(port.type, ui.DIM) if port.patched else ui.DIM)
    p1 = imgui.ImVec2(p0.x + PIN, p0.y + PIN)
    if stub == graphview.BASE:           # base: a square (many setters, last touch wins)
        dl.add_rect(p0, p1, col, 0.0, 1.5)
    elif stub == graphview.DEPTH:        # depth: a diamond
        cx, cy = p0.x + PIN / 2, p0.y + PIN / 2
        dl.add_quad(imgui.ImVec2(cx, p0.y), imgui.ImVec2(p1.x, cy), imgui.ImVec2(cx, p1.y),
                    imgui.ImVec2(p0.x, cy), col, 1.5)
    else:                                # mod, a source, a render port: a disc
        c = imgui.ImVec2(p0.x + PIN / 2, p0.y + PIN / 2)
        if port.patched:
            dl.add_circle_filled(c, PIN / 2, col)
        else:
            dl.add_circle(c, PIN / 2, col, 0, 1.5)
    ed.end_pin()
    drawn.add(pin)
    st["pin_xy"][pin] = (p0.x + PIN / 2, p0.y + PIN / 2)     # canvas units, inside the editor


def _wiring(st: dict, view: graphview.View):
    """`graphview.wiring` for this frame, kept while the view and the
    expanded nodes hold (only the bundles' readings move each frame)."""
    lay = st["auto"][1] if st.get("auto") else areas_of(st, view)
    k = (id(view), frozenset(st["open"]), frozenset(st["idle_open"]), id(lay))
    held = st.get("wiring")
    if held is None or held[0] != k:
        st["throughs"] = {c.id: c for c in lay.throughs}
        held = st["wiring"] = (k, graphview.wiring(
            view, lambda nid: collapsed(st, nid), lambda c: drawn_cable(st, c),
            lambda nid: _drawn_id(st, view, nid), lay.throughs))
    else:
        graphview.readings(held[1][1])
    return held[1]


def wire_of(st: dict, view: graphview.View, b) -> str | None:
    """The drawn wire a row's cable is this frame: its bundle's id, or its
    own cable's id; None while it is not drawn."""
    c = next((x for x in view.cables if x.ref is b), None)
    if c is None:
        return None
    bundle = next((x for x in st["bundles"].values() if any(y is c for y in x.cables)), None)
    return bundle.id if bundle is not None else c.id


def reveal(st: dict, view: graphview.View, b) -> str | None:
    """A route just made elsewhere ("Route a lane here…", plan 28 N7):
    select the wire it is drawn in — its bundle, or its own cable — and
    bring it on screen; the side pane lists its row first (`st["focus"]`).
    Returns the wire's id, or None (not drawn)."""
    wid = wire_of(st, view, b)
    if wid is None:
        return None
    ed.clear_selection()
    ed.select_link(ed.LinkId(_id(st, "c:" + wid)))
    ed.navigate_to_selection(False)
    st["focus"] = b
    return wid


def _stub(st: dict, pin: str, kind, lit: bool, drawn: set[str]) -> None:
    """A node's single in or out stub (plan 28 N7): where its bundles and
    its collapsed render cables end, and where a drag lands to pick a port."""
    _pin(st, pin, kind, graphview.VPort(pin, "", "", patched=lit), "", drawn)


def _node(st: dict, n: graphview.VNode, drawn: set[str]) -> None:
    ed.begin_node(ed.NodeId(_id(st, "n:" + n.id)))
    imgui.push_id(n.id)
    shut = collapsed(st, n.id)
    # (plan 33 U: `frame` takes no wire, but each pipeline's picture feeds it)
    has_in = (any(p.direction == graphview.IN for p in n.ports)
              or isinstance(n.ref, graphview.FrameNode))
    has_out = any(p.direction == graphview.OUT for p in n.ports)
    # the title line: [in stub] label [+ / -] [out stub]
    if has_in:
        _stub(st, graphview.stub_in(n.id), ed.PinKind.input, n.wires > 0, drawn)
        imgui.same_line()
    # a desk layer that is down (plan 28 N5) reads like a lost device: faint;
    # (plan 33 U) so does a node that reaches nothing; a compile error is red
    err = st.get("errors", {}).get(n.id)
    imgui.push_style_color(imgui.Col_.text, ui.WARN if err else ui.FAINT if (
        n.grey or not n.up or n.faint) else ui.TEXT)
    imgui.text(ui.fit_text(n.label, NODE_W - 40 - 2 * PIN))
    imgui.pop_style_color()
    imgui.same_line(NODE_W - 30 - PIN)          # the + clear of the out stub
    if imgui.small_button("+" if shut else "-"):
        toggle_open(st, n.id)
    if imgui.is_item_hovered():
        ed.suspend()
        imgui.set_tooltip(EXPAND_TIP if shut else COLLAPSE_TIP)
        ed.resume()
    if has_out:
        imgui.same_line(NODE_W - PIN)
        _stub(st, graphview.stub_out(n.id), ed.PinKind.output, n.wires > 0, drawn)
    if shut:                                    # its title and at most five lines
        for line in graphview.summary(n):
            imgui.text_disabled(ui.fit_text(line, NODE_W))
        imgui.dummy(imgui.ImVec2(NODE_W, 0))
        imgui.pop_id()
        ed.end_node()
        return
    if n.kind == graphview.TEMPLATE:          # a subgraph: every mapped control
        every = True
    else:
        every = full(st, n.id)
        if imgui.small_button("patched only" if every else "all ports"):
            st["flip"] ^= {n.id}
    ports = shown(st, n)
    group = None
    many = graphview.grouped(n, every)
    for port in (n.ports if many else ports):
        if many and port.group != group:
            group = port.group
            folded = (n.id, group) in st["folds"]
            count = sum(1 for p in n.ports if p.group == group)
            if imgui.small_button(f"{'+' if folded else '-'} {group or 'misc'} ({count})"
                                  f"##{group}"):
                st["folds"] ^= {(n.id, group)}
        if port not in ports:
            continue
        _port(st, port, drawn)
    imgui.dummy(imgui.ImVec2(NODE_W, 0))
    imgui.pop_id()
    ed.end_node()


def _port(st: dict, port: graphview.VPort, drawn: set[str]) -> None:
    text = ui.fit_text(port.name, NODE_W - 4 * PIN - 40)
    if port.direction == graphview.OUT:
        # a desk layer's port (plan 28 N5): lit while its layer is up, faint while down
        imgui.text_colored(ui.FAINT if not port.up else ui.TEXT if port.layer else ui.DIM, text)
        imgui.same_line(NODE_W - PIN)
        _pin(st, port.pins[0], ed.PinKind.output, port, "", drawn)
        return
    for pin in port.pins:
        stub = pin.partition(":")[0] if port.param is not None else ""
        _pin(st, pin, ed.PinKind.input, port, stub, drawn)
        imgui.same_line()
    imgui.text_colored(ui.TEXT if port.patched else ui.DIM, text)


def _cable(st: dict, c: graphview.VCable, a: str | None = None, b: str | None = None) -> None:
    """One cable, from pin `a` to pin `b` (its own ends, or a collapsed
    node's stub for a render cable: plan 28 N7)."""
    k = COLOURS.get(c.type, ui.DIM)
    col = imgui.ImVec4(k.x, k.y, k.z, DORMANT_ALPHA if c.dormant else
                       THROUGH_ALPHA if c.kind == graphview.THROUGH else k.w)
    if c.type == graphview.VALUE:
        u = c.live if c.live is not None else 0.0
        thick = THIN + (THICK - THIN) * max(0.0, min(1.0, abs(u)))
    else:
        thick = WIRE
    ed.link(ed.LinkId(_id(st, "c:" + c.id)), ed.PinId(_id(st, a or c.src_port)),
            ed.PinId(_id(st, b or c.dst_port)), col, thick)


def bundle_thickness(count: int) -> float:
    """A bundle's line (plan 28 N7): a single cable's resting width, a
    little more for each cable past the first, capped at `BUNDLE_MAX`."""
    return min(BUNDLE_MAX, WIRE + BUNDLE_STEP * max(0, count - 1))


def _bundle(st: dict, b: graphview.VBundle) -> None:
    """The one wire between two nodes while either is collapsed: coloured
    by what it carries, as thick as it is many, faint while dormant."""
    k = COLOURS.get(b.type, ui.DIM)
    col = imgui.ImVec4(k.x, k.y, k.z, DORMANT_ALPHA if b.dormant else k.w)
    ed.link(ed.LinkId(_id(st, "c:" + b.id)), ed.PinId(_id(st, b.src_port)),
            ed.PinId(_id(st, b.dst_port)), col, bundle_thickness(b.count))


def _said(v: float | None) -> str:
    return "not live" if v is None else f"{v:.2f}"


def cable_tip(view: graphview.View, c: graphview.VCable) -> str:
    """What hovering a cable says: from and to, the reading, the depth."""
    src = view.owner(c.src_port)
    dst = view.owner(c.dst_port)
    a = f"{src[0].label} {src[1].name}" if src and src[1] else c.src_port
    b = f"{dst[0].label} {dst[1].name}" if dst and dst[1] else c.dst_port
    lines = [f"{a}  →  {b}  ({c.dst_port.partition(':')[0]})"]
    if c.kind != "render":
        lines.append(f"reading {_said(c.live)}")
    if c.depth is not None:
        lines.append(f"depth {c.depth:+.2f}")
    if c.label:
        lines.append(c.label)
    if c.dormant:
        lines.append("dormant")
    return "\n".join(lines)


def _hover(st: dict, view: graphview.View) -> None:
    tip = None
    names = st["names"]
    link = ed.get_hovered_link().id()
    pin = ed.get_hovered_pin().id()
    node = ed.get_hovered_node().id()
    if link:
        cid = names.get(link, "")[2:]
        bundle = st["bundles"].get(cid)
        c = next((x for x in view.cables if x.id == cid), None) if bundle is None else None
        through = st.get("throughs", {}).get(cid)
        tip = (graphview.bundle_tip(view, bundle) if bundle is not None
               else cable_tip(view, c) if c is not None
               else f"{through.label}\n{THROUGH_NO_DELETE}" if through is not None else None)
    elif pin and graphview.is_stub(names.get(pin, "")):
        n = view.node(graphview.stub_node(names[pin]))
        if n is not None:
            side = "in" if graphview.pin_kind(names[pin]) == graphview.STUB_IN else "out"
            tip = (f"{n.label} {side}: {n.wires} cable{'s' if n.wires != 1 else ''}\n"
                   f"drag a cable here to pick one of its ports")
    elif pin:
        hit = view.owner(names.get(pin, ""))
        if hit is not None and hit[1] is not None:
            port = hit[1]
            stub = names.get(pin, "").partition(":")[0] if port.param else ""
            tip = (f"{port.param or port.addr or port.id}{'  ' + stub if stub else ''}\n"
                   f"{port.name}: {_said(port.live)}")
            tip += hidden_by(st, view, names.get(pin, ""))
    elif node:
        n = view.node(names.get(node, "")[2:])
        err = st.get("errors", {}).get(n.id) if n is not None else None
        if err:                             # plan 33 U: a compile error is its hover
            tip = f"{n.label}\n{err}"
        elif n is not None and n.faint:
            tip = f"{n.label}\n{FAINT_TIP}"
        elif n is not None and n.status:
            tip = f"{n.label}\n{n.status}"
    if tip:
        ed.suspend()
        imgui.set_tooltip(tip)
        ed.resume()


# ---------------------------------------------------------------- render edits (plan 28 N4)
#
# The render graph's edits, beside N3's below and on its contract: a drag's
# handler is `CREATE[type]` (image / geometry / mask → `_create_render`), a
# deleted cable's `DELETE["render"]`, a deleted node's
# `DELETE_NODE["render" / "output"]`; each handler accepts or rejects the
# widget's item itself. They do not go through N3's `_act` (an undo step
# pushed before the edit, even one refused): `render_edit` reads each edit
# back and pushes its undo step (`load=True`: the library's marks carry the
# graph) only when it lands. A refusal is the head's note; a landing's
# words are `st["said"]`.

def render_edit(panel) -> graphview.Edit:
    """The render edits on this panel's loaded preset (its `GraphSection`),
    pins named through the renderer's last graph, one undo step each."""
    lib = getattr(panel, "library", None)
    gs = getattr(getattr(lib, "presets", None), "graph", None)
    rg = getattr(getattr(panel, "renderer", None), "_graph", None)
    return graphview.Edit(graph=gs, render=rg, push=lambda label: undo.push(label, load=True))


def _render_said(panel, e: graphview.Edit, fn, st: dict | None = None) -> str | None:
    """Run render edit `fn(e)`: a refusal is the head's note, a landing's
    words the head's line (`st`: the page's state). Returns the refusal,
    or None."""
    st = st if st is not None else _state(panel)
    why = fn(e)
    _note(st, why)
    if why is None:
        st["said"] = e.said
    return why


def _note(st: dict, why: str | None) -> None:
    """The head after an edit: a refusal's words (`why`), or none for an
    edit that landed — and either way the last render edit's line goes
    (a render landing puts its own back after this). Inside one delete of
    a selection (`st["held"]` present) the first refusal's words stay for
    the frame: a later landing or refusal there does not wipe them."""
    st["said"] = ""
    if st.get("held"):
        return
    st["note"] = why or ""
    if why and "held" in st:
        st["held"] = True


def new_link() -> tuple[int, int] | None:
    """The two pins' widget ids of a cable being dragged this frame, in drag
    order, or None."""
    a, b = ed.PinId(), ed.PinId()
    if ed.query_new_link(a, b) and a.id() and b.id():
        return a.id(), b.id()
    return None


def _create_render(panel, st: dict, view: graphview.View, a: str, b: str) -> None:
    """An image / geometry / mask cable dragged (either end first): checked
    while it is held — red, and the words a preset file would get — and a
    wire when it is let go."""
    src, dst = graphview.Edit.ordered(a, b)
    e = render_edit(panel)
    why = e.wire(src, dst, dry=True)
    if why:
        _drag_tip(why)
        ed.reject_new_item(imgui.ImVec4(*REFUSED_RGB), WIRE)
    elif ed.accept_new_item(COLOURS[graphview.IMAGE], WIRE):
        _render_said(panel, e, lambda e: e.wire(src, dst), st)


def _delete_render_cable(panel, st: dict, view: graphview.View, c) -> None:
    """Delete pressed on a render cable: unwired, or kept with the words
    (the default graph's own edge). A cable of a render node this delete
    just took out goes with it, saying nothing over the node's words."""
    gone = st.get("dropped") or set()
    if view is not None and gone and any(
            view.pins.get(p, ("",))[0] in gone for p in (c.src_port, c.dst_port)):
        ed.accept_deleted_item()
        return
    if _render_said(panel, render_edit(panel), lambda e: e.unwire(c), st) is None:
        ed.accept_deleted_item()
    else:
        ed.reject_deleted_item()


def _delete_render_node(panel, st: dict, view: graphview.View, n) -> None:
    """Delete pressed on a render node: an extra effect instance, hands
    node or composite out of the graph; the frame's own nodes stay, said."""
    if _render_said(panel, render_edit(panel), lambda e: e.drop_node(n.id), st) is None:
        st.setdefault("dropped", set()).add(n.id)
        ed.accept_deleted_item(False)
    else:
        ed.reject_deleted_item()


def render_picker(panel, at=None) -> None:
    """The picker's render items: an effect instance per file, a switch, a
    hands node, a composite (`graphview.picker`). Plan 33 U: an effect or a
    switch lands unwired (faint, "reaches nothing") where the menu opened
    (`at`, canvas units)."""
    e = render_edit(panel)
    items = graphview.picker(e)
    effects = [(f, label) for kind, f, label in items if kind == "effect"]
    if effects and imgui.begin_menu("effect"):
        for f, label in effects:
            if imgui.menu_item_simple(label):
                add_render(panel, e, "effect", f, at)
        imgui.end_menu()
    for kind, _, label in items:
        if kind != "effect" and imgui.menu_item_simple(label):
            add_render(panel, e, kind, None, at)


def add_render(panel, e: graphview.Edit, kind: str, file: str | None = None, at=None):
    """A render node the picker adds (`Edit.add_node`), one undo step, put
    where the menu opened. Returns the refusal, or None."""
    why = _render_said(panel, e, lambda e: e.add_node(kind, file))
    if why is None and e.added:
        _place_new(panel, f"render:{e.added}", at)
    return why


def insert_effect(panel, cable: graphview.VCable, file: str) -> str | None:
    """A render cable's "insert effect ▸ <file>" (plan 33 U): the next
    instance of `file` onto it, one undo step. Returns the refusal, or None."""
    return _render_said(panel, render_edit(panel), lambda e: e.insert_effect(cable, file))


def render_node_menu(panel, n) -> None:
    """A render node's menu items: a hands node drawn solid or as lines, a
    composite's blend, delete."""
    e = render_edit(panel)
    name, _ = graphview.spec_name(n.id, e.render)
    kind = rgraph.wire_node_kind(name) if name else None
    if kind in ("ghost", "layer"):
        for how in rgraph.DRAWS:
            if imgui.menu_item_simple(f"draw {how}"):
                _render_said(panel, e, lambda e, how=how: e.set_node(name, draw=how))
    if kind == "composite":
        for how in rgraph.BLENDS:
            if imgui.menu_item_simple(f"laid {how}"):
                _render_said(panel, e, lambda e, how=how: e.set_node(name, blend=how))
    if imgui.menu_item_simple("delete"):
        _render_said(panel, e, lambda e: e.drop_node(n.id))


# ---------------------------------------------------------------- the selection

def _selection(st: dict, view: graphview.View):
    """The selected cable or node (the first), as ("cable", VCable) or
    ("node", VNode); None. Asked of last frame's canvas."""
    if st["editor"] is None:
        return None
    ed.set_current_editor(st["editor"])
    names = st["names"]
    for lk in ed.get_selected_links():
        cid = names.get(lk.id(), "")[2:]
        b = st["bundles"].get(cid)
        if b is not None:                       # plan 28 N7: a bundle's rows
            return ("bundle", b)
        c = next((x for x in view.cables if x.id == cid), None)
        if c is not None:
            return ("cable", c)
    for nk in ed.get_selected_nodes():
        n = view.node(names.get(nk.id(), "")[2:])
        if n is not None:
            return ("node", n)
    return None


def _side(panel, st: dict, view: graphview.View, sel) -> None:
    what, obj = sel
    router = ui_routing.router_of(panel)
    if what != "bundle" or not any(c.ref is st.get("focus") for c in obj.cables):
        st["focus"] = None                      # another selection: no row first
    if what == "bundle":                        # plan 28 N7: each of its rows
        b = obj
        ui._micro("bundle")
        imgui.text_wrapped(graphview.bundle_tip(view, b).split("\n")[0])
        imgui.text_disabled(f"{b.count} cable{'s' if b.count != 1 else ''} · "
                            f"{graphview.EXPAND_TO_EDIT} on the canvas")
        imgui.separator()
        rows = [c.ref for c in b.cables if c.kind == "route"]
        focus = st.get("focus")
        if any(r is focus for r in rows):       # the route just made: first
            rows = [focus] + [r for r in rows if r is not focus]
        route_rows(panel, rows)
        for c in b.cables:                      # the rest: a desk row, a subscriber …
            if c.kind != "route":
                imgui.text_disabled(ui.fit_text(
                    f"{graphview.cable_words(view, c)}  {c.label}".rstrip(),
                    imgui.get_content_region_avail().x))
        return
    if what == "cable":
        c = obj
        ui._micro(c.kind)
        _route_row(panel, router, view, c)
        return
    n = obj
    if isinstance(n.ref, Effect):
        ui_fx.strip(panel, n.ref.effect)
        return
    m = router.table.modifier(n.id) if router is not None and n.kind == "modifier" else None
    if m is not None:                           # plan 28 N7: the MODIFIERS strip's editor
        ui._micro("modifier")
        if ui_routing.modifier_block(panel, router, m, stacked=True):
            ui_routing.remove_modifier(panel, m.id)
        return
    ui._micro(n.kind)
    imgui.text(n.label)
    if n.status:
        imgui.text_disabled(n.status)
    for port in n.ports:
        if port.patched:
            imgui.text_disabled(f"{port.name}: {_said(port.live)}")


def _route_row(panel, router, view: graphview.View, c: graphview.VCable) -> None:
    """A cable in the side pane: a route as its ROUTING row (`ui_routing._row`,
    the one table — its × deletes it, one undo step); anything else in words."""
    if c.kind == "route" and router is not None:
        rows = router.table.routes()
        k = next((i for i, b in enumerate(rows) if b is c.ref), None)
        if k is not None:
            if ui_routing._row(panel, router, c.ref, k):
                undo.push(f"delete route {c.ref.source} → {c.ref.target}")
                router.table.remove(c.ref)
            return
    imgui.text_wrapped(cable_tip(view, c))


def route_rows(panel, rows) -> None:
    """Routes `rows` as the side pane lists a bundle's (plan 28 N7): each
    its ROUTING row (`ui_routing._row`), under its own id, the source
    combo's list built once for the lot (as ROUTING's page did)."""
    router = ui_routing.router_of(panel)
    if router is None:
        return
    rst = ui_routing._state(panel)
    rst["sources"] = ui_routing._sources(panel, router) if rows else None
    view = _state(panel)["view"]
    try:
        for i, b in enumerate(rows):
            imgui.push_id(f"rows{i}")
            if i:
                imgui.separator()
            _route_row(panel, router, view, graphview.VCable("", "", "", ref=b, kind="route"))
            imgui.pop_id()
    finally:
        rst["sources"] = None                   # this draw's only


def timing_line(panel) -> str:
    """The SYSTEM page's line for this page: its draw's median over the
    last draws, in ms — "" until it has been drawn."""
    st = panel.__dict__.get(STATE)
    times = sorted(st["times"]) if st else []
    if not times:
        return ""
    v = st["view"]
    size = f"  ({len(v.nodes)} nodes, {len(v.cables)} cables)" if v is not None else ""
    return f"graph page: {times[len(times) // 2] * 1000:.2f} ms median{size}"


# ---------------------------------------------------------------- editing (plan 28 N3)
#
# The page's edits, as plain functions over the panel (the tests drive
# these, as test_ui_routing drives ROUTING's): each builds a
# `graphview.Edit` on the page's view and the router's table, names one
# undo step before it changes anything, and settles what came back — a
# `graphview.Ask` becomes ROUTING's Replace / Keep prompt (`ui_routing.ask`),
# a `graphview.Refusal` the head's note. The canvas's gestures below call
# them; `CREATE` / `DELETE` are the dispatch by type N4 extends.

EDIT_HINT = ("drag pin to pin: a cable  ·  right-click: Learn, insert, add  ·  "
             "Delete: the selection")
MENU = "##graph.menu"
REFUSED_RGB = (1.0, 0.45, 0.35, 1.0)       # ui.WARN: a drag the table would refuse


def edit_of(panel, view: graphview.View | None = None) -> graphview.Edit | None:
    """The page's `Edit` on the router's table (None: no router)."""
    router = ui_routing.router_of(panel)
    if router is None:
        return None
    if view is None:
        view = view_of(panel)
    table = router.table
    profile = ui.apc40 if getattr(table, "profile", None) == "apc40" else None
    # plan 28 N4: render requests reach the preset's graph too (no undo push
    # of their own here: `_act` pushed one; the canvas's render gestures use
    # `render_edit` instead)
    lib = getattr(panel, "library", None)
    return graphview.Edit(table, panel.reg, router, view, profile,
                          graph=getattr(getattr(lib, "presets", None), "graph", None),
                          render=getattr(getattr(panel, "renderer", None), "_graph", None))


def _settle(panel, res):
    """Settle what an edit returned: an Ask puts up the prompt, a Refusal
    is the head's note; anything else clears the note. Returns `res`."""
    st = _state(panel)
    if isinstance(res, graphview.Ask):
        ui_routing.ask(panel, res.old, res.new, res.commit)
        _note(st, None)
    elif isinstance(res, graphview.Refusal):
        _note(st, str(res))
    else:
        _note(st, None)
    return res


def _act(panel, label: str, why: str | None, fn):
    """One edit: refused before anything moves (`why`), else one undo step
    named `label`, then `fn()` settled by `_settle`."""
    if why is not None:
        return _settle(panel, graphview.Refusal(why))
    undo.push(label)
    return _settle(panel, fn())


def _name(view: graphview.View | None, pin: str) -> str:
    hit = view.owner(pin) if view is not None else None
    if hit is None or hit[1] is None:
        return pin.partition(":")[2] or pin
    return hit[1].param or hit[1].addr or f"{hit[0].label} {hit[1].name}"


def connect(panel, a: str, b: str):
    """A cable dragged from pin `a` to pin `b` (either order): a route, a
    setter row, a macro's subscriber, a modifier's input, or a cable's end
    moved (`graphview.Edit.connect`)."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"connect {_name(e.view, a)} → {_name(e.view, b)}",
                e.refusal(a, b), lambda: e.connect(a, b))


def disconnect(panel, cable: graphview.VCable):
    """Delete a cable (`graphview.Edit.disconnect`): a route and its depth
    subscribers, a preset desk row, a subscriber, a modifier's input."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"delete cable {cable.id}", None, lambda: e.disconnect(cable))


def insert_modifier(panel, cable: graphview.VCable, kind: str):
    """A modifier (`kind`, or an existing one's id) into `cable`."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"insert {kind} into {cable.id}", None,
                lambda: e.insert_modifier(cable, kind))


def _place_new(panel, nid: str, at) -> None:
    """A node the picker made goes where the picker opened (the preset's
    layout: modifiers and macros are the preset's)."""
    pre, _ = _layouts(panel)
    if at and pre is not None:
        pre[nid] = [round(at[0]), round(at[1])]


def add_modifier(panel, kind: str, at=None):
    """The picker's "+ modifier ▸ <kind>": a new node, placed at `at`."""
    e = edit_of(panel)
    if e is None:
        return None
    res = _act(panel, f"add modifier {kind}", None, lambda: e.add_modifier(kind))
    if isinstance(res, modifiers.Modifier):
        _place_new(panel, res.id, at)
    return res


def show_macro(panel, mid: str, at=None):
    """The picker's "+ macro ▸ <n>": the macro onto the canvas (its label set)."""
    e = edit_of(panel)
    if e is None:
        return None
    res = _act(panel, f"show {mid}", None, lambda: e.show_macro(mid))
    if not isinstance(res, graphview.Refusal):
        _place_new(panel, mid, at)
    return res


def remove_node(panel, nid: str):
    """Delete a node (`graphview.Edit.remove_node`): a modifier, a macro, a
    render node, an LFO or an extra envelope (plan 31 G1: through its bank,
    one undo step — the bank's membership is in the undo state). A lane
    envelope (1–5) is refused before any undo step is pushed."""
    e = edit_of(panel)
    if e is None:
        return None
    hit = graphview.voice_of(nid)
    why = voice_refusal(e.view.node(nid) if e.view is not None else None, nid) if hit else None
    return _act(panel, f"delete node {nid}", why, lambda: e.remove_node(nid))


def voice_refusal(n, nid: str | None = None) -> str | None:
    """Why a bank voice's node may not be deleted (a lane envelope), or None."""
    nid = n.id if n is not None else nid or ""
    hit = graphview.voice_of(nid)
    if hit is not None and hit[0] == "env" and hit[1] in graphview.LANE_ENVS:
        return graphview.LANE_ENV_KEPT.format(label=n.label if n is not None else nid)
    return None


def add_refusal(panel, scheme: str) -> str | None:
    """Why the picker's "+ LFO" / "+ envelope" is greyed: no such bank, or
    the bank at its cap; None when one can be added."""
    bank = graphview.bank_of(ui_routing.router_of(panel), scheme)
    if bank is None:
        return graphview.NO_BANK.format(what=graphview.BANK_WORDS[scheme][0])
    return graphview.bank_refusal(bank, scheme)


def add_voice(panel, scheme: str, at=None):
    """The picker's "LFO" / "envelope" (plan 31 G1): a new voice in its
    bank (`graphview.Edit.add_voice`), one undo step, placed at `at` in the
    preset's layout (a bank's membership is the preset's). Its node id, or
    the Refusal at the cap."""
    e = edit_of(panel)
    if e is None:
        return None
    res = _act(panel, f"add {graphview.BANK_WORDS[scheme][0]}", add_refusal(panel, scheme),
               lambda: e.add_voice(scheme))
    if isinstance(res, str) and not isinstance(res, graphview.Refusal):
        _place_new(panel, res, at)
    return res


def dropped(panel, view: graphview.View, nid: str, centre) -> graphview.VCable | None:
    """A modifier node let go at `centre` (canvas units): if it is still
    free — no cable in or out — and lands on a route or a modifier's input
    cable (`graphview.cable_near`, by the curve the widget draws), it is
    inserted there. Plan 33 U: a free effect node (`kind` "effect": in the
    section, no cable in or out) let go on a picture cable is inserted into
    it the same way (`Edit.place_effect`, one undo step). Returns the cable
    it went into, or None."""
    n = view.node(nid)
    if n is None or view.cables_of(nid):
        return None
    pins = _state(panel)["pin_xy"]
    if n.kind == "render" and isinstance(n.ref, Effect):
        c = graphview.cable_near(view, pins, centre, kinds=("render",), skip=(nid,))
        if c is None or c.type != graphview.IMAGE:
            return None
        why = _render_said(panel, render_edit(panel), lambda e: e.place_effect(c, n.ref.effect))
        return None if why is not None else c
    if n.kind != "modifier":
        return None
    c = graphview.cable_near(view, pins, centre, skip=(nid,))
    if c is None:
        return None
    res = insert_modifier(panel, c, nid)
    return None if isinstance(res, graphview.Refusal) else c


def macros_free(panel, view: graphview.View) -> list[str]:
    """The macros the picker offers: the rig's knobs doing nothing yet (no
    label, no subscriber). Every macro is a node (its knob is modulatable),
    so picking one names it and brings it to where the picker opened."""
    router = ui_routing.router_of(panel)
    macros = router.table.macros if router is not None else {}
    return [p.id for p in panel.reg.group("macro")
            if (macros.get(p.id) is None or macros[p.id].empty)]


# ---- the canvas's gestures ----

def _value_drag(panel, st: dict, view: graphview.View, a: str, b: str) -> None:
    """A drag between two value / trigger pins, held: the refusal's words
    in red while it would be refused; let go, `connect`."""
    e = edit_of(panel, view)
    why = e.refusal(a, b) if e is not None else "no router"
    if why is not None:
        _drag_tip(why)
        ed.reject_new_item(imgui.ImVec4(*REFUSED_RGB), 2.0)
    elif ed.accept_new_item(COLOURS[graphview.VALUE], 2.0):
        connect(panel, a, b)


def _drag_tip(text: str) -> None:
    ed.suspend()
    imgui.set_tooltip(text)
    ed.resume()


# a drag's handler by the signal type it carries (the seam: N4 maps
# graphview.IMAGE / GEOMETRY / MASK to its own)
CREATE = {graphview.VALUE: _value_drag, graphview.TRIGGER: _value_drag,
          graphview.IMAGE: _create_render, graphview.GEOMETRY: _create_render,
          graphview.MASK: _create_render}


def _drag_type(view: graphview.View, a: str, b: str) -> str:
    """The type a drag is dispatched by: a render type if either end has one."""
    e = graphview.Edit(None, None, None, view)
    types = [e.type_of(a), e.type_of(b)]
    return next((t for t in types if t in graphview.RENDER_TYPES), types[0])


def _create(panel, st: dict, view: graphview.View) -> None:
    """The widget's create query: a pin dragged onto another pin."""
    if ed.begin_create(COLOURS[graphview.VALUE], 2.0):
        got = new_link()
        if got is not None:
            pa, pb = st["names"].get(got[0]), st["names"].get(got[1])
            if pa and pb:                   # plan 28 N7: a one-output node's out stub
                pa, pb = graphview.stub_pin(view, pa), graphview.stub_pin(view, pb)
            if pa and pb and pa != pb:
                if graphview.is_stub(pa) or graphview.is_stub(pb):   # plan 28 N7
                    _stub_drag(panel, st, view, pa, pb)
                else:
                    CREATE.get(_drag_type(view, pa, pb), _create_render)(panel, st, view,
                                                                         pa, pb)
        ed.end_create()                 # only after a begin that opened (the widget asserts)


# ---- plan 28 N7: a drag onto a collapsed node's stub, and landing it ----

BOTH_STUBS = "drag from a port: expand one of the two nodes first"
LAND_HINT = "let go: pick one of {label}'s ports"
LAND = "##graph.land"


def stub_refusal(view: graphview.View, a: str, b: str) -> str | None:
    """Why a drag between pins `a` and `b`, one of them a node's stub, can
    open no port picker: both are stubs (once a one-output node's out stub
    stands for its output, `graphview.stub_pin`), or both are outputs
    (inputs)."""
    if graphview.is_stub(a) and graphview.is_stub(b):
        return BOTH_STUBS
    stub, fixed = (a, b) if graphview.is_stub(a) else (b, a)
    into = graphview.pin_kind(stub) == graphview.STUB_IN
    if into == (not graphview.is_output(fixed)):
        return graphview.SAME_SIDE
    return None


def _stub_drag(panel, st: dict, view: graphview.View, a: str, b: str) -> None:
    """A cable dragged onto (or from) a collapsed node's stub: held, it says
    which node's ports it will offer; let go, the picker opens (`st["land"]`,
    drawn by `_menus`) — what it lands on goes through `land`."""
    why = stub_refusal(view, a, b)
    if why is not None:
        _drag_tip(why)
        ed.reject_new_item(imgui.ImVec4(*REFUSED_RGB), 2.0)
        return
    stub, fixed = (a, b) if graphview.is_stub(a) else (b, a)
    nid = graphview.stub_node(stub)
    n = view.node(nid)
    _drag_tip(LAND_HINT.format(label=n.label if n is not None else nid))
    if ed.accept_new_item(COLOURS[graphview.VALUE], 2.0):
        open_land(panel, st, view, fixed, nid)


def open_land(panel, st: dict, view: graphview.View, fixed: str, nid: str) -> list:
    """The port picker for a drag from pin `fixed` let go on node `nid`'s
    stub: its choices (`graphview.land_choices`, each with the refusal
    `Edit.connect` would give) held in `st["land"]` until one is picked or
    the menu closes; the next `_menus` opens it. Returns the choices."""
    e = edit_of(panel, view) if not _is_render_pin(view, fixed) else render_edit(panel)
    choices = graphview.land_choices(view, e, fixed, nid)
    st["land"] = {"fixed": fixed, "node": nid, "choices": choices, "open": True}
    return choices


def _is_render_pin(view: graphview.View, pin: str) -> bool:
    return graphview.Edit(None, None, None, view).is_render(pin)


def land(panel, fixed: str, pin: str):
    """A port picked from a stub's picker: the cable from `fixed` to `pin`
    (either order) as if it had been dragged there — a value cable through
    `connect` (`Edit.connect`, one undo step), a render cable through the
    render edits (`Edit.wire`). The picker closes."""
    st = _state(panel)
    st["land"] = None
    view = st["view"]
    if view is not None and _is_render_pin(view, fixed):
        src, dst = graphview.Edit.ordered(fixed, pin)
        return _render_said(panel, render_edit(panel), lambda e: e.wire(src, dst), st)
    return connect(panel, fixed, pin)


def _land_menu(panel, st: dict, view: graphview.View) -> None:
    """The stub's picker: the node's ports a drag may land on, by port
    group when there are more than twelve; a refused one is left out (and
    when every one is, the first refusal is said)."""
    held = st["land"]
    n = view.node(held["node"])
    label = n.label if n is not None else held["node"]
    ui._micro(f"onto {label}")
    ok = [c for c in held["choices"] if c[3] is None]
    if not ok:
        first = next((c[3] for c in held["choices"] if c[3]), None)
        imgui.text_disabled(graphview.NOTHING_TAKES.format(label=label)
                            + (f": {first}" if first else ""))
        return
    groups: dict[str, list] = {}
    for c in ok:
        groups.setdefault(c[2] or "", []).append(c)
    nested = len(ok) > 12 and len(groups) > 1
    for g, items in groups.items():
        if nested and not imgui.begin_menu(f"{g or 'misc'} ({len(items)})"):
            continue
        for pin, text, _, _ in items:
            if imgui.menu_item_simple(f"{text}##{pin}"):
                land(panel, held["fixed"], pin)
        if nested:
            imgui.end_menu()


def _value_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a value / trigger cable: the session's rows are
    kept (and say so); anything else goes (`disconnect`)."""
    b = c.ref if c.kind == "setter" else None
    if b is not None and graphview.is_session_row(b):
        ed.reject_deleted_item()
        _note(st, graphview.SESSION_ROW.format(what=b.source))
    elif ed.accept_deleted_item():
        disconnect(panel, c)


def _unknown_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    ed.reject_deleted_item()


# a delete's handler by the cable's kind ("render" is N4's)
DELETE = {"route": _value_cut, "setter": _value_cut, "sub": _value_cut,
          "input": _value_cut, "render": _delete_render_cable}


def _value_node_cut(panel, st: dict, view: graphview.View, n: graphview.VNode) -> None:
    """Delete pressed on a modifier or a macro node: it goes, without its
    cables (`accept_deleted_item(False)`): a route on a removed modifier's
    lane stays, dormant, as on ROUTING."""
    if ed.accept_deleted_item(False):
        remove_node(panel, n.id)


def _rig_node_cut(panel, st: dict, view: graphview.View, n: graphview.VNode) -> None:
    """Delete pressed on the rig's node (a device, the analyzer, an LFO, a
    group): kept, said."""
    ed.reject_deleted_item()
    _note(st, graphview.NOT_REMOVABLE.format(label=n.label))


def _voice_node_cut(panel, st: dict, view: graphview.View, n: graphview.VNode) -> None:
    """Delete pressed on an LFO or an envelope node (plan 31 G1): it goes
    through its bank, without its cables (a route on its lane stays,
    dormant); a lane envelope is kept, said."""
    why = voice_refusal(n)
    if why is not None:
        ed.reject_deleted_item()
        _note(st, why)
    elif ed.accept_deleted_item(False):
        remove_node(panel, n.id)


def _lane_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a sequencer lane's binding: kept — a lane always
    fires an envelope — and the head says how to rebind it."""
    ed.reject_deleted_item()
    _note(st, graphview.LANE_NO_DELETE)


DELETE["lane"] = _lane_cut


def _feeds_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a pipeline's picture into `frame` (plan 33 U): kept —
    it is what frame is, no wire — and the head says so."""
    ed.reject_deleted_item()
    _note(st, graphview.FEEDS_NO_DELETE)


DELETE[graphview.FEEDS] = _feeds_cut

# a node delete's handler by the node's kind (the seam: N4 maps "render"
# and "output"); a kind not listed is the rig's
DELETE_NODE = {"modifier": _value_node_cut, "macro": _value_node_cut,
               "lfo": _voice_node_cut, "env": _voice_node_cut,
               "render": _delete_render_node, "output": _delete_render_node}


def delete_bundle(st: dict, b: graphview.VBundle) -> str:
    """Delete pressed on a bundle (plan 28 N7): kept, and the head says how
    to edit its cables ("expand a node to edit its cables"). Returns the words."""
    ed.reject_deleted_item()
    _note(st, graphview.EXPAND_TO_EDIT)
    return graphview.EXPAND_TO_EDIT


def delete_through(st: dict) -> str:
    """Delete pressed on a through wire (plan 28 N9): kept — it is no render
    edge — and the head says what it stands for. Returns the words."""
    ed.reject_deleted_item()
    _note(st, THROUGH_NO_DELETE)
    return THROUGH_NO_DELETE


def _delete(panel, st: dict, view: graphview.View) -> None:
    """The widget's delete query: the selection's nodes first, by kind
    (`DELETE_NODE`), then its cables, by kind (`DELETE`). The first
    refusal's words stay on the head for the frame (`st["held"]`, `_note`)."""
    if ed.begin_delete():
        names = st["names"]
        st["dropped"] = set()           # N4: render nodes this delete took out
        st["held"] = False
        try:
            nk = ed.NodeId()
            while ed.query_deleted_node(nk):
                n = view.node(names.get(nk.id(), "")[2:])
                if n is None:
                    ed.reject_deleted_item()
                    continue
                DELETE_NODE.get(n.kind, _rig_node_cut)(panel, st, view, n)
            lk = ed.LinkId()
            while ed.query_deleted_link(lk):
                cid = names.get(lk.id(), "")[2:]
                if cid in st["bundles"]:                # plan 28 N7: refused in words
                    delete_bundle(st, st["bundles"][cid])
                    continue
                if cid in st.get("throughs", {}):       # N9: a through wire, refused
                    delete_through(st)
                    continue
                c = next((x for x in view.cables if x.id == cid), None)
                if c is None:
                    ed.reject_deleted_item()
                    continue
                DELETE.get(c.kind, _unknown_cut)(panel, st, view, c)
        finally:
            st.pop("held", None)
        ed.end_delete()


def _menus(panel, st: dict, view: graphview.View) -> None:
    """Right-click on the canvas: a pin's menu, a cable's, a node's, the
    picker on the background. Opened and drawn with the editor suspended."""
    at = imgui.get_mouse_pos()                 # canvas units, inside the editor
    names = st["names"]
    ed.suspend()
    pin, link, node = ed.PinId(), ed.LinkId(), ed.NodeId()
    subject = None
    if ed.show_pin_context_menu(pin):
        subject = ("pin", names.get(pin.id(), ""))
    elif ed.show_link_context_menu(link):
        subject = ("cable", names.get(link.id(), "")[2:])
    elif ed.show_node_context_menu(node):
        subject = ("node", names.get(node.id(), "")[2:])
    elif ed.show_background_context_menu():
        subject = ("picker", "")
    if subject is not None:
        st["menu"], st["menu_at"] = subject, (at.x, at.y)
        imgui.open_popup(MENU)
    if imgui.begin_popup(MENU):
        menu(panel, st, view)
        imgui.end_popup()
    held = st["land"]                       # plan 28 N7: a drag let go on a stub
    if held is not None:
        if held.pop("open", False):
            imgui.open_popup(LAND)
        if imgui.begin_popup(LAND):
            _land_menu(panel, st, view)
            imgui.end_popup()
        else:
            st["land"] = None               # closed without a pick
    ed.resume()


def menu(panel, st: dict, view: graphview.View) -> None:
    """The open right-click menu's items, for `st["menu"]`."""
    what, name = st["menu"] or ("", "")
    if what == "pin":
        _pin_menu(panel, view, name)
    elif what == "cable":
        b = st["bundles"].get(name)
        c = next((x for x in view.cables if x.id == name), None) if b is None else None
        if b is not None:
            _bundle_menu(panel, st, view, b)
        elif c is not None:
            _cable_menu(panel, view, c)
    elif what == "node":
        n = view.node(name)
        if n is not None:
            _node_menu(panel, view, n)
    elif what == "picker":
        picker(panel, view, st["menu_at"])


def port_param(pin: str) -> str | None:
    """The param a ``mod:`` pin is the performer stub of; None for any other pin."""
    kind, _, pid = pin.partition(":")
    return pid if kind == graphview.MOD and pid else None


def _pin_menu(panel, view: graphview.View, pin: str) -> None:
    """A pin's menu: on a param's `mod` stub, the param menu's Learn items
    — the same function the panel's widgets' menu calls (`Panel._ctx_learn_block`:
    desk, hand ▸ left / right, pad, a role, sink), or Cancel while armed —
    so a learn from here lands as a cable next frame (the view is rebuilt
    from the table); any other pin says what it is."""
    pid = port_param(pin)
    a = panel.reg.get(pid) if pid else None
    ui._micro(pid or pin)
    if a is None:
        hit = view.owner(pin)
        if hit is not None and hit[1] is not None:
            imgui.text_disabled(f"{hit[0].label} · {hit[1].name}")
        return
    panel._ctx_learn_block(a, panel._real(a))


def _cable_menu(panel, view: graphview.View, c: graphview.VCable) -> None:
    """A cable's menu: insert a modifier of a kind (a route's or a
    modifier input's), delete."""
    imgui.text_disabled(cable_tip(view, c).splitlines()[0])
    if c.kind in ("route", "input") and imgui.begin_menu("insert"):
        for kind in modifiers.KINDS:
            if imgui.menu_item_simple(kind):
                insert_modifier(panel, c, kind)
        imgui.end_menu()
    if c.kind == graphview.FEEDS:               # plan 33 U: what frame is, no wire
        imgui.text_disabled(graphview.FEEDS_NO_DELETE)
        return
    if c.kind == "render" and c.type == graphview.IMAGE:
        files = [f for kind, f, _ in graphview.picker(render_edit(panel)) if kind == "effect"]
        if files and imgui.begin_menu("insert effect"):     # plan 33 U
            for f in files:
                if imgui.menu_item_simple(f):
                    insert_effect(panel, c, f)
            imgui.end_menu()
    if imgui.menu_item_simple("delete"):
        if c.kind == "render":                  # N4: unwire, its own undo step
            _render_said(panel, render_edit(panel), lambda e: e.unwire(c))
        else:
            disconnect(panel, c)


def _bundle_menu(panel, st: dict, view: graphview.View, b: graphview.VBundle) -> None:
    """A bundle's menu (plan 28 N7): what it holds, expand its ends (its
    cables appear), and no delete — "expand a node to edit its cables"."""
    imgui.text_disabled(graphview.bundle_tip(view, b).split("\n")[0])
    imgui.text_disabled(f"{b.count} cable{'s' if b.count != 1 else ''}")
    if imgui.menu_item_simple("expand both ends"):
        st["open"] |= {b.src, b.dst}
    imgui.menu_item_simple(f"delete: {graphview.EXPAND_TO_EDIT}", enabled=False)


def learn_params(n: graphview.VNode) -> dict[str, list[str]]:
    """The params a node's right-click offers Learn on (plan 28 N7, so a
    collapsed render node can be learned without expanding): each param
    port's id, by its port group."""
    out: dict[str, list[str]] = {}
    for p in n.ports:
        if p.param is not None and p.direction == graphview.IN:
            out.setdefault(p.group or "", []).append(p.param)
    return out


def _node_menu(panel, view: graphview.View, n: graphview.VNode) -> None:
    imgui.text_disabled(n.label)
    st = _state(panel)
    if imgui.menu_item_simple("collapse" if is_open(st, n.id) else "expand"):
        toggle_open(st, n.id)
    params = learn_params(n)
    if params and imgui.begin_menu("learn"):            # N3's param Learn, per param
        nested = len(params) > 1
        for g, pids in params.items():
            if nested and not imgui.begin_menu(f"{g or 'misc'} ({len(pids)})"):
                continue
            for pid in pids:
                p = panel.reg.get(pid)
                if imgui.begin_menu(f"{p.label if p is not None and p.label else pid}##{pid}"):
                    _pin_menu(panel, view, f"{graphview.MOD}:{pid}")
                    imgui.end_menu()
            if nested:
                imgui.end_menu()
        imgui.end_menu()
    if n.kind in ("modifier", "macro") and imgui.menu_item_simple("delete"):
        remove_node(panel, n.id)
    if n.kind in graphview.BANK_SCHEMES:          # plan 31 G1: an LFO, an envelope
        why = voice_refusal(n)
        if imgui.menu_item_simple("delete", enabled=why is None):
            remove_node(panel, n.id)
        if why is not None and imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            imgui.set_tooltip(why)
    if n.kind in ("render", "output"):
        render_node_menu(panel, n)


def picker(panel, view: graphview.View, at=None) -> None:
    """The node picker (right-click on the canvas): a modifier of each
    kind, a macro not on the canvas yet; the node lands where the menu
    opened."""
    ui._micro("add")
    if imgui.begin_menu("modifier"):
        for kind in modifiers.KINDS:
            if imgui.menu_item_simple(kind):
                add_modifier(panel, kind, at)
        imgui.end_menu()
    for scheme in graphview.BANK_SCHEMES:       # plan 31 G1: another LFO, envelope
        why = add_refusal(panel, scheme)
        one = graphview.BANK_WORDS[scheme][0]
        if imgui.menu_item_simple(one if why is None else f"{one}: {why}",
                                  enabled=why is None):
            add_voice(panel, scheme, at)
    render_picker(panel, at)                    # N4 (and plan 33 U): an effect, a switch …
    free = macros_free(panel, view)
    if free and imgui.begin_menu("macro"):
        for mid in free:
            if imgui.menu_item_simple(mid):
                show_macro(panel, mid, at)
        imgui.end_menu()
