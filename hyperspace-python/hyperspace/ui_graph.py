"""The GRAPH page (plan 28 N2, N3): both graphs on one canvas; the
modulation edited on it.

`page(panel, dt)` draws `graphview`'s model on one `imgui_node_editor`
canvas: the controllers, the analyzer, the LFOs, the modifiers and the
macros on the left, the params grouped under the render node that owns
them, the render graph's own image / geometry / mask cables, the
outputs last. Cables are coloured by what they carry (`COLOURS`); a value
cable's thickness follows its reading; a dormant one is faint. A node
shows only its patched ports while it is collapsed — the page's
**patched only** chip collapses every node, a node's own chip flips it —
and an expanded node folds its port groups (the hands' axes, the desk's
knobs) one by one. Hovering a cable says its reading and its depth; a
port, its reading; a device, its status. Selecting a route shows its
ROUTING row (`ui_routing._row`, the same widgets, the same table) beside
the canvas — below it while the page is narrow — and selecting an effect's
node shows its strip (`ui_fx.strip`).

**Editing the modulation** (plan 28 N3): a cable dragged between two
pins (`_create`) and a cable or node deleted (`_delete`) go through
`graphview.Edit` and the table's own calls — the same table ROUTING
edits, so either page shows the other's change next frame, and undo, the
preset's dirt and the referee are theirs. A taken param asks Replace /
Keep (ROUTING's prompt, `ui_routing.ask`); a refusal says why on the
page's head (`st["note"]`) and on the drag. Right-click: a param's `mod`
pin offers the param menu's Learn items (`Panel._ctx_learn_block`, the same
function), a cable offers "insert" (a modifier onto it) and delete, the
canvas the node picker (a modifier of each kind, a macro), a modifier or
macro node delete. A modifier node dropped onto a cable is inserted into
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

A node can be moved: where it is dropped is saved, in the
preset's ``layout`` for the look's nodes and the show's for the rig's
(`graphview.home`), and the preset (or the show) is dirty. An unplaced
node takes `graphview.auto_layout`'s column; **tidy** forgets every
position on the canvas and lays them all out again — one undo step
(`forget`). The selection shows under the canvas on the panel's narrow
page; **beside** (or a page 720 px wide) puts it in a side column.

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
PATCHED_TIP = ("Patched only: every node shows just its patched ports — "
               "a node's own ± flips it")
TIDY_TIP = ("Forget every position on the canvas and lay every node out again by kind "
            "(⌘Z puts them back)")
BESIDE_TIP = ("The selection beside the canvas instead of under it — widen CONTROLS "
              "to give both room (it is beside by itself on a page this wide)")


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
                                     lanes=lanes, bands=bands)
        st["key"] = k
    else:
        graphview.refresh(st["view"], reg, router, lanes)
    return st["view"]


def expanded(st: dict, nid: str) -> bool:
    """Is node `nid` showing every port? The page's chip, flipped by the node's own."""
    return (not st["patched_only"]) != (nid in st["flip"])


def shown(st: dict, n: graphview.VNode) -> list[graphview.VPort]:
    """The ports node `n` draws (`graphview.visible` with this page's state)."""
    return graphview.visible(n, expanded(st, n.id), st["folds"])


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
    _head(panel, st, view)
    imgui.separator()
    sel = _selection(st, view)
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


def _head(panel, st: dict, view: graphview.View) -> None:
    live = sum(1 for c in view.cables if not c.dormant)
    imgui.text_disabled(f"{len(view.nodes)} nodes  ·  {len(view.cables)} cables  ·  {live} live")
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
    imgui.same_line()
    if ui.lit_chip("beside##graph", st["beside"]):
        st["beside"] = not st["beside"]
    if imgui.is_item_hovered():
        imgui.set_tooltip(BESIDE_TIP)
    if st["note"]:
        imgui.text_colored(ui.WARN, st["note"])
    elif st["said"]:                        # plan 28 N4: the last render edit
        imgui.text_disabled(st["said"])
    else:
        imgui.text_disabled(EDIT_HINT)


def _place(panel, st: dict, view: graphview.View) -> None:
    """Every node where it belongs this frame: the preset's or the show's
    position, else the automatic column; set on the canvas only when that
    differs from what was last set, so a node being dragged is left alone.
    A tidy forgets the canvas's positions in both maps first."""
    if st["tidy"]:
        st["tidy"] = False
        forget(panel, view)
    pre, show = _layouts(panel)
    stored = {**(show or {}), **(pre or {})}
    auto = graphview.auto_layout(view, stored, lambda nid: expanded(st, nid), st["folds"])
    applied = st["applied"]
    for n in view.nodes:
        xy = stored.get(n.id) or auto.get(n.id) or (0.0, 0.0)
        target = (float(xy[0]), float(xy[1]))
        if applied.get(n.id) != target:
            ed.set_node_position(ed.NodeId(_id(st, "n:" + n.id)), imgui.ImVec2(*target))
            applied[n.id] = target


def _moved(panel, st: dict, view: graphview.View) -> None:
    """A node dropped somewhere new is saved where it lives (the preset's
    map or the show's, `graphview.home`) — once the mouse lets go."""
    if imgui.is_mouse_down(imgui.MouseButton_.left):
        return
    pre, show = _layouts(panel)
    applied = st["applied"]
    for n in view.nodes:
        p = ed.get_node_position(ed.NodeId(_id(st, "n:" + n.id)))
        now = (float(round(p.x)), float(round(p.y)))
        was = applied.get(n.id)
        if was is None or (round(was[0]), round(was[1])) == now:
            continue
        applied[n.id] = now
        m = pre if graphview.home(n) == graphview.PRESET else show
        if m is not None:
            m[n.id] = [int(now[0]), int(now[1])]
        if n.kind == "modifier":
            size = ed.get_node_size(ed.NodeId(_id(st, "n:" + n.id)))
            dropped(panel, view, n.id, (now[0] + size.x / 2, now[1] + size.y / 2))


def _canvas(panel, st: dict, view: graphview.View, size: imgui.ImVec2) -> None:
    ed.set_current_editor(editor(panel))
    ed.begin("##graph", size)
    _place(panel, st, view)
    drawn: set[str] = set()
    for n in view.nodes:
        _node(st, n, drawn)
    for c in view.cables:
        if c.src_port in drawn and c.dst_port in drawn:
            _cable(st, c)
    _create(panel, st, view)
    _delete(panel, st, view)
    _menus(panel, st, view)
    _hover(st, view)
    _moved(panel, st, view)
    ed.end()


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


def _node(st: dict, n: graphview.VNode, drawn: set[str]) -> None:
    ed.begin_node(ed.NodeId(_id(st, "n:" + n.id)))
    imgui.push_id(n.id)
    imgui.push_style_color(imgui.Col_.text, ui.FAINT if n.grey else ui.TEXT)
    imgui.text(ui.fit_text(n.label, NODE_W - 24))
    imgui.pop_style_color()
    imgui.same_line(NODE_W - 12)
    full = expanded(st, n.id)
    if imgui.small_button("-" if full else "+"):
        st["flip"] ^= {n.id}
    ports = shown(st, n)
    group = None
    many = graphview.grouped(n, full)
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
        imgui.text_colored(ui.DIM, text)
        imgui.same_line(NODE_W - PIN)
        _pin(st, port.pins[0], ed.PinKind.output, port, "", drawn)
        return
    for pin in port.pins:
        stub = pin.partition(":")[0] if port.param is not None else ""
        _pin(st, pin, ed.PinKind.input, port, stub, drawn)
        imgui.same_line()
    imgui.text_colored(ui.TEXT if port.patched else ui.DIM, text)


def _cable(st: dict, c: graphview.VCable) -> None:
    k = COLOURS.get(c.type, ui.DIM)
    col = imgui.ImVec4(k.x, k.y, k.z, DORMANT_ALPHA if c.dormant else k.w)
    if c.type == graphview.VALUE:
        u = c.live if c.live is not None else 0.0
        thick = THIN + (THICK - THIN) * max(0.0, min(1.0, abs(u)))
    else:
        thick = WIRE
    ed.link(ed.LinkId(_id(st, "c:" + c.id)), ed.PinId(_id(st, c.src_port)),
            ed.PinId(_id(st, c.dst_port)), col, thick)


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
        c = next((x for x in view.cables if x.id == cid), None)
        tip = cable_tip(view, c) if c is not None else None
    elif pin:
        hit = view.owner(names.get(pin, ""))
        if hit is not None and hit[1] is not None:
            port = hit[1]
            stub = names.get(pin, "").partition(":")[0] if port.param else ""
            tip = (f"{port.param or port.addr or port.id}{'  ' + stub if stub else ''}\n"
                   f"{port.name}: {_said(port.live)}")
    elif node:
        n = view.node(names.get(node, "")[2:])
        if n is not None and n.status:
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
    st["note"] = why or ""
    if why is None:
        st["said"] = e.said
    return why


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


def render_picker(panel) -> None:
    """The picker's render items: an effect instance per file, a hands
    node, a composite (`graphview.picker`)."""
    e = render_edit(panel)
    items = graphview.picker(e)
    effects = [(f, label) for kind, f, label in items if kind == "effect"]
    if effects and imgui.begin_menu("effect"):
        for f, label in effects:
            if imgui.menu_item_simple(label):
                _render_said(panel, e, lambda e, f=f: e.add_node("effect", f))
        imgui.end_menu()
    for kind, _, label in items:
        if kind != "effect" and imgui.menu_item_simple(label):
            _render_said(panel, e, lambda e, kind=kind: e.add_node(kind))


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
    if what == "cable":
        c = obj
        ui._micro(c.kind)
        if c.kind == "route" and router is not None:
            rows = router.table.routes()
            k = next((i for i, b in enumerate(rows) if b is c.ref), None)
            if k is not None and ui_routing._row(panel, router, c.ref, k):
                undo.push(f"delete route {c.ref.source} → {c.ref.target}")
                router.table.remove(c.ref)
            return
        imgui.text_wrapped(cable_tip(view, c))
        return
    n = obj
    if isinstance(n.ref, Effect):
        ui_fx.strip(panel, n.ref.effect)
        return
    ui._micro(n.kind)
    imgui.text(n.label)
    if n.status:
        imgui.text_disabled(n.status)
    for port in n.ports:
        if port.patched:
            imgui.text_disabled(f"{port.name}: {_said(port.live)}")


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
        st["note"] = ""
    elif isinstance(res, graphview.Refusal):
        st["note"] = str(res)
    else:
        st["note"] = ""
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
    """Delete a node (`graphview.Edit.remove_node`)."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"delete node {nid}", None, lambda: e.remove_node(nid))


def dropped(panel, view: graphview.View, nid: str, centre) -> graphview.VCable | None:
    """A modifier node let go at `centre` (canvas units): if it is still
    free — no cable in or out — and lands on a route or a modifier's input
    cable (`graphview.cable_near`, by the curve the widget draws), it is
    inserted there. Returns the cable it went into, or None."""
    n = view.node(nid)
    if n is None or n.kind != "modifier" or view.cables_of(nid):
        return None
    c = graphview.cable_near(view, _state(panel)["pin_xy"], centre, skip=(nid,))
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
            if pa and pb and pa != pb:
                CREATE.get(_drag_type(view, pa, pb), _create_render)(panel, st, view, pa, pb)
        ed.end_create()                 # only after a begin that opened (the widget asserts)


def _value_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a value / trigger cable: the session's rows are
    kept (and say so); anything else goes (`disconnect`)."""
    b = c.ref if c.kind == "setter" else None
    if b is not None and graphview.is_session_row(b):
        ed.reject_deleted_item()
        st["note"] = graphview.SESSION_ROW.format(what=b.source)
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
    st["note"] = graphview.NOT_REMOVABLE.format(label=n.label)


# a node delete's handler by the node's kind (the seam: N4 maps "render"
# and "output"); a kind not listed is the rig's
DELETE_NODE = {"modifier": _value_node_cut, "macro": _value_node_cut,
               "render": _delete_render_node, "output": _delete_render_node}


def _delete(panel, st: dict, view: graphview.View) -> None:
    """The widget's delete query: the selection's nodes first, by kind
    (`DELETE_NODE`), then its cables, by kind (`DELETE`)."""
    if ed.begin_delete():
        names = st["names"]
        st["dropped"] = set()           # N4: render nodes this delete took out
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
            c = next((x for x in view.cables if x.id == cid), None)
            if c is None:
                ed.reject_deleted_item()
                continue
            DELETE.get(c.kind, _unknown_cut)(panel, st, view, c)
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
    ed.resume()


def menu(panel, st: dict, view: graphview.View) -> None:
    """The open right-click menu's items, for `st["menu"]`."""
    what, name = st["menu"] or ("", "")
    if what == "pin":
        _pin_menu(panel, view, name)
    elif what == "cable":
        c = next((x for x in view.cables if x.id == name), None)
        if c is not None:
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
    if imgui.menu_item_simple("delete"):
        if c.kind == "render":                  # N4: unwire, its own undo step
            _render_said(panel, render_edit(panel), lambda e: e.unwire(c))
        else:
            disconnect(panel, c)


def _node_menu(panel, view: graphview.View, n: graphview.VNode) -> None:
    imgui.text_disabled(n.label)
    if n.kind in ("modifier", "macro") and imgui.menu_item_simple("delete"):
        remove_node(panel, n.id)
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
    render_picker(panel)                        # N4: an effect, hands, a composite
    free = macros_free(panel, view)
    if free and imgui.begin_menu("macro"):
        for mid in free:
            if imgui.menu_item_simple(mid):
                show_macro(panel, mid, at)
        imgui.end_menu()
