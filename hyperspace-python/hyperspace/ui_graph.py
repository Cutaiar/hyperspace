"""The GRAPH page (plan 28 N2): both graphs on one canvas, read-only.

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

**Read-only**: no `begin_create` / `begin_delete` here (plan 28 N3 and N4
open them), so a drag from a pin makes nothing and Delete removes
nothing. A node can be moved: where it is dropped is saved, in the
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

from . import graphview, ui, ui_fx, ui_routing, undo
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
    return st


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
