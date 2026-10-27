"""The gamepad drawn on screen — the desk's picture (ui_desk.py) for the pad.

A picture of the pad in the control window, top-left: every control of
`gamepad.LAYOUT` at its place on the device, with its glyph, so what the
pad does can be read at a glance instead of pieced together from the
ROUTING rows.

**It takes the room it has** (`room`): the top of the column left of the
panel — the whole window's width while the panel is hidden — and the
desk, which grows up from the bottom of that same column, keeps clear of
it (`ui_desk.room`'s `pad`). It is never more than `MAX_H` of the window
tall, so the desk always has the greater half.

What is lit is what a control **does**:

* a control with an enabled row in the table (`rows`) is lit and, once a
  layout unit is `LABEL_UNIT` wide, carries its param's label in
  the bright ink — the same words the desk prints (`ui_desk.text`);
* the six axes have a **built-in** meaning when no route claims them
  (`BUILT_IN`, app.frame: the left stick orbits, the right stick's Y
  zooms and its X rides the W planes' rates, the triggers ride the 4D
  depth). Such a lane is lit with its label in grey — nothing in the
  table, nothing to unbind, the app's own hand on it, as a grey label on
  the desk is a row that is the session's;
* every other control is dark: its glyph only.

Pad rows are the session's, not a layer's (`learn.learn_pad_button`), so
there is nothing here like the desk's two layers, and no picture of a
"preset" pad.

**The live pad shows through it**: a held button fills red, a stick well
carries the stick where it is now, and each axis lane fills from its rest
(`gamepad.AXIS_RESTS`) to where the axis sits — the pad's own feel is not
applied, this is the hardware. With no pad (none connected, or
``[gamepad] enabled = false``) the picture is the same, drawn from the
table alone, and the header says so.

Read-only: the hover names the control, its param and its source, and a
click does nothing. Learn pad is still the way onto a control — the
binding menu on any param (right-click → Learn pad), which the hover
points at.

A function over the Panel, like ui_desk: the cache lives on the panel, a
save of this file lands live (hotreload.MODULES). `ui.pad_diagram` (the
SYSTEM page, beside the desk's switch) hides it.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import gamepad, ui, ui_desk, ui_routing
from .routing import Binding

SCHEMES = ("pad", "hat", "axis")    # the schemes a pad control's row can have
EDGE = ui_desk.EDGE                 # from the control window's edges, as the desk sits
PAD = ui_desk.PAD
GAP = ui_desk.GAP                   # between this and the desk under it
HEAD_H = ui_desk.HEAD_H             # the header's line
GLYPH_PX = ui_desk.GLYPH_PX
MIN_W = 240.0                       # the window is never narrower…
MAX_UNIT = 58.0                     # …and a layout unit never wider than this
MAX_H = 0.42                        # …nor the window taller than this much of the display
# a layout unit this wide (and this tall) carries labels; under that, the
# glyphs alone. Lower than the desk's: a pad control is a whole unit or
# more where a desk pad is one small cell of a grid, and its words are short
LABEL_UNIT = 40.0
LABEL_UNIT_H = 28.0

# What an axis does with no route on it (app.frame, the free axes): the
# left stick orbits, the right stick's Y zooms about centre and its X
# rides the three W planes' rates, the triggers ride the 4D depth.
BUILT_IN = {
    "axis:LX": "Orbit yaw", "axis:LY": "Orbit pitch",
    "axis:RX": "4D spin (W planes)", "axis:RY": "Zoom",
    "axis:LT": "4D depth out", "axis:RT": "4D depth in",
}

_DARK = imgui.ImVec4(0.09, 0.09, 0.10, 1.0)    # a dark control's face
_OFF = imgui.ImVec4(0.34, 0.34, 0.37, 1.0)     # a mapped control's face, not held
_WELL = imgui.ImVec4(0.14, 0.14, 0.15, 1.0)    # a stick well's ground
_BLACK = imgui.ImVec4(0, 0, 0, 1)              # ink on a held control


def _table(panel):
    router = ui_routing.router_of(panel)
    return router.table if router is not None else None


def _state(panel) -> dict:
    return panel.__dict__.setdefault("_pad_state", {})


def rows(table) -> dict[str, Binding]:
    """{source: the row that acts} for every enabled pad, D-pad or axis
    row of the table — the first row a control has wins, as the adapters
    read them. Keyed by the layout's source, so a lane addressed by
    number (``axis:4``) lands on the control it names."""
    out: dict[str, Binding] = {}
    for b in table.of(*SCHEMES):
        if not b.enabled:
            continue
        c = gamepad.control(b.source)
        if c is not None:
            out.setdefault(c.source, b)
    return out


def _key(table) -> tuple:
    return (id(table.bindings), len(table.bindings),
            tuple(b.source for b in table.of(*SCHEMES)))


def rows_cached(panel, table) -> dict[str, Binding]:
    st = _state(panel)
    key = _key(table)
    if st.get("key") != key or st.get("table") is not table:
        st.update(key=key, table=table, rows=rows(table))
    return st["rows"]


# ---------------------------------------------------------------- the room

def room(display: tuple[float, float], panel_x: float | None
         ) -> tuple[float, float, float, float]:
    """(x, y, w, h) of the pad window: top-left, `EDGE` from the window's
    edges, as wide as the column left of the panel allows — `panel_x` is
    the panel's left edge, None while it is hidden — but never wider than
    `MAX_UNIT` a unit, and never taller than `MAX_H` of the display (the
    desk, which grows up from the foot of the same column, keeps the
    rest)."""
    dw, dh = display
    right = (dw if panel_x is None else panel_x) - EDGE
    w = max(MIN_W, min(right - EDGE, MAX_UNIT * gamepad.LAYOUT_W + 2 * PAD))
    unit = (w - 2 * PAD) / gamepad.LAYOUT_W
    tall = unit * gamepad.LAYOUT_H + 2 * PAD + HEAD_H
    if tall > MAX_H * dh:       # too tall for its half: the picture shrinks, both ways
        unit = max(1.0, (MAX_H * dh - 2 * PAD - HEAD_H) / gamepad.LAYOUT_H)
        w = max(MIN_W, unit * gamepad.LAYOUT_W + 2 * PAD)
        tall = unit * gamepad.LAYOUT_H + 2 * PAD + HEAD_H
    return EDGE, EDGE, float(int(w)), float(int(tall))


def _room(panel) -> tuple[float, float, float, float]:
    """`room` for this frame: the panel's edge is last frame's (the pad is
    drawn before the panel), its launch place before there is one."""
    io = imgui.get_io()
    display = (io.display_size.x, io.display_size.y)
    panel_x = None
    if panel.open:
        panel_x = getattr(panel, "_panel_x", None)
        if panel_x is None:
            panel_x = display[0] - ui.panel_w(display) - EDGE
    return room(display, panel_x)


# ---------------------------------------------------------------- the live pad

def _pad(panel):
    pad = getattr(panel, "pad", None)
    return pad if pad is not None and getattr(pad, "on", False) else None


def held(pad, c: gamepad.Control) -> bool:
    """Is this control pressed right now? False for an axis, and with no pad."""
    if pad is None:
        return False
    scheme, _, addr = c.source.partition(":")
    if scheme == "pad":
        return pad.down(gamepad.BUTTONS[addr])
    if scheme == "hat":
        return bool(pad.hat & gamepad.HATS[addr])
    return False


def lane(pad, name: str) -> float:
    """Where an axis sits, in [0, 1] (`Pad.lanes`), or its rest with no pad."""
    i = gamepad.AXES.index(name)
    return pad.lanes()[i] if pad is not None else gamepad.AXIS_RESTS[i]


def _stick(pad, c: gamepad.Control) -> tuple[float, float]:
    """Where a stick is, each in [-1, 1], x right and y **down** (what a
    draw list wants); (0, 0) with no pad."""
    xa, ya = ("LX", "LY") if c.glyph == "LS" else ("RX", "RY")
    return 2 * lane(pad, xa) - 1, 1 - 2 * lane(pad, ya)


# ---------------------------------------------------------------- what a control says

def says(panel, c: gamepad.Control, b: Binding | None) -> str:
    """What a lit control does: its row's param in the panel's words
    (`ui_desk.text`), else the built-in meaning of a free axis
    (`BUILT_IN`), else "" — a dark control."""
    if b is not None:
        return ui_desk.text(panel.reg, b)
    return BUILT_IN.get(c.source, "")


def label(panel, c: gamepad.Control, b: Binding | None) -> str:
    """The hover: "LB · view.shape · Shape · pad LB", then how to change
    it; a free axis names the app's own hand on it, a dark control says
    it is free."""
    said = says(panel, c, b)
    learn = "right-click a param → Learn pad, then press it here"
    if b is not None:
        return (f"{c.glyph} · {b.target} · {said} · {b.describe()}\n{c.name}"
                f"\n{learn} to move it")
    if said:
        return (f"{c.glyph} · {said} — the app's own, no row in the table\n{c.name}"
                f"\n{learn} to take it over")
    return f"{c.glyph} · free — nothing is mapped\n{c.name}\n{learn}"


# ---------------------------------------------------------------- drawing

def _v(x: float, y: float) -> imgui.ImVec2:
    return imgui.ImVec2(x, y)


def _lane_bar(dl, c: gamepad.Control, pad, x0: float, y0: float, x1: float, y1: float,
              edge: int, on: bool) -> None:
    """An axis lane: its track, the rest marked, and the fill from rest to
    where the axis sits — red under a live pad, grey when the picture is
    the table's alone (nothing is moving)."""
    cy = (y0 + y1) / 2
    dl.add_line(_v(x0, cy), _v(x1, cy), edge, 2.0)
    rest = gamepad.AXIS_RESTS[gamepad.AXES.index(c.address)]
    rx = x0 + rest * (x1 - x0)
    dl.add_line(_v(rx, y0), _v(rx, y1), edge, 1.0)
    if not on:
        return
    col = ui.u32(ui.RED) if pad is not None else ui.u32(ui.DIM)
    vx = x0 + lane(pad, c.address) * (x1 - x0)
    if abs(vx - rx) >= 1.0:
        dl.add_rect_filled(_v(min(rx, vx), cy - 3), _v(max(rx, vx), cy + 3), col, 1.5)
    dl.add_rect_filled(_v(vx - 2, y0), _v(vx + 2, y1), col, 1.0)


def _well(dl, pad, c: gamepad.Control, cx: float, cy: float, r: float,
          edge: int, on: bool) -> None:
    """A stick well: the ring, its centre, and the stick in it."""
    dl.add_circle_filled(_v(cx, cy), r, ui.u32(_WELL))
    dl.add_circle(_v(cx, cy), r, edge)
    dx, dy = _stick(pad, c)
    knob = max(3.0, r * 0.34)
    col = ui.u32(ui.RED) if on and pad is not None else edge
    dl.add_circle_filled(_v(cx + dx * (r - knob), cy + dy * (r - knob)), knob, col)


def _draw(panel, dl, pad, c: gamepad.Control, b: Binding | None, said: str,
          x0: float, y0: float, x1: float, y1: float) -> None:
    """One control at the small size: its glyph on its face."""
    on = bool(said)
    down = held(pad, c)
    edge = ui.u32(ui.DIM if on else ui.LINE)
    ink = ui.u32(ui.TEXT if on else ui.FAINT)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if c.kind == "button":
        face = ui.u32(ui.RED) if down else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 3.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 3.0)
        ui_desk._text(dl, c.glyph, cx, cy, ui.u32(_BLACK) if down else ink, x1 - x0 - 2)
    elif c.kind == "stick":
        r = min((x1 - x0) / 2, (y1 - y0) / 2) - 1
        _well(dl, pad, c, cx, y0 + r + 1, r, ui.u32(ui.RED) if down else edge, on)
        ui_desk._text(dl, c.glyph, cx, y1 - 5, ink, x1 - x0)
    else:
        gw = imgui.calc_text_size(f"{c.glyph} ").x
        _lane_bar(dl, c, pad, x0 + gw, y0 + 1, x1 - 2, y1 - 1, edge, on)
        ui_desk._text(dl, c.glyph, x0 + gw / 2, cy, ink, gw)


def _draw_big(panel, dl, pad, c: gamepad.Control, b: Binding | None, said: str,
              x0: float, y0: float, x1: float, y1: float, lh: float) -> ui_desk._Job | None:
    """One control at the labelled size: its face, its glyph small in the
    corner, and — returned, for ui_desk's label pass — the room its label
    has. A free axis's label is grey (the app's own hand, no row); a dark
    control gets none."""
    on = bool(said)
    down = held(pad, c)
    edge = ui.u32(ui.DIM if on else ui.LINE)
    small = ui.u32(ui.DIM if on else ui.FAINT)         # the glyph: small and dim
    # whose words they are: a row's in the bright ink, a built-in grey
    ink = ui.u32(ui.TEXT if b is not None else ui.DIM)
    cx = (x0 + x1) / 2
    gsz = imgui.calc_text_size(c.glyph)
    if c.kind == "button":
        face = ui.u32(ui.RED) if down else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 3.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 3.0)
        if down:
            small = ink = ui.u32(_BLACK)
        below = int((y1 - y0 - gsz.y - 1) / lh)        # lines that fit under the glyph
        if below >= 1:
            dl.add_text(_v(x0 + 3, y0 + 1), small, c.glyph)
            return ui_desk._Job(said, x0 + 3, y0 + gsz.y, x1 - 3, y1 - 1,
                                min(ui_desk.LABEL_LINES, below), ink, "mid",
                                face) if on else None
        # a low button: the label beside the glyph, on its line
        dl.add_text(_v(x0 + 3, (y0 + y1 - gsz.y) / 2), small, c.glyph)
        return ui_desk._Job(said, x0 + gsz.x + 7, y0, x1 - 3, y1, 1, ink,
                            "mid", face) if on else None
    if c.kind == "stick":
        lines = ui_desk.LABEL_LINES
        r = max(4.0, min((y1 - y0 - lines * lh - 4) / 2, 0.42 * (x1 - x0)))
        dl.add_text(_v(x0 + 1, y0), small, c.glyph)
        _well(dl, pad, c, cx, y0 + r + 1, r, ui.u32(ui.RED) if down else edge, on)
        return ui_desk._Job(said, x0 + 1, y0 + 2 * r + 4, x1 - 1, y1, lines, ink,
                            "top") if on else None
    # an axis lane: the glyph, the bar on its line, the label under both
    dl.add_text(_v(x0 + 1, y0), small, c.glyph)
    _lane_bar(dl, c, pad, x0 + gsz.x + 5, y0 + 1, x1 - 2, y0 + gsz.y - 1, edge, on)
    return ui_desk._Job(said, x0 + 1, y0 + gsz.y + 1, x1 - 1, y1, 1, ink,
                        "left") if on else None


# ---------------------------------------------------------------- the window

def diagram(panel) -> None:
    """The pad window: a header (the pad's state, how many controls are
    mapped), then every control at its place — in the room `room` gives
    it. `panel._pad_h` is left behind for `ui_desk.room`, which keeps the
    desk clear of it; it is 0 while this is off."""
    if not getattr(panel, "pad_diagram", False):
        panel._pad_h = 0.0
        return
    x, y, w, h = _room(panel)
    panel._pad_h, panel._pad_w = h, w
    imgui.set_next_window_pos(_v(x, y), imgui.Cond_.always)
    imgui.set_next_window_size(_v(w, h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.6)
    flags = (imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_move
             | imgui.WindowFlags_.no_focus_on_appearing | imgui.WindowFlags_.no_nav
             | imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse
             | imgui.WindowFlags_.no_saved_settings)
    imgui.push_style_var(imgui.StyleVar_.window_padding, _v(PAD, PAD))
    imgui.begin("##pad", None, flags)
    try:
        _body(panel, _table(panel))
    finally:
        imgui.end()
        imgui.pop_style_var()


def inline(panel) -> None:
    """The same picture inside the current window, as wide as it has room
    for and as tall as the pad's shape needs: the GRAPH page's details for
    the pad node (ui_graph._node_side), whether or not the floating one is up."""
    w = imgui.get_content_region_avail().x
    h = (w - 2 * PAD) / gamepad.LAYOUT_W * gamepad.LAYOUT_H + 2 * PAD + HEAD_H
    imgui.push_style_var(imgui.StyleVar_.window_padding, _v(PAD, PAD))
    if imgui.begin_child("##pad.inline", _v(w, h), imgui.ChildFlags_.borders
                         | imgui.ChildFlags_.always_use_window_padding,
                         imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse):
        _body(panel, _table(panel))
    imgui.end_child()
    imgui.pop_style_var()


def state(panel) -> tuple[str, str]:
    """The header's state (the word, the whole of it for the hover): how
    the pad is read, or why there is none."""
    pad = getattr(panel, "pad", None)
    if pad is None:
        return "off", "The pad is off: [gamepad] enabled = false in config.toml."
    source = getattr(pad, "source", None)
    read = "The pad is read raw, over Bluetooth or USB (gamepad.py)."
    if source == "usb":
        return "over USB", f"{read} This one is a wired 360-protocol pad, over libusb."
    if source == "glfw":
        return "on", read
    note = getattr(getattr(pad, "usb_pad", None), "note", "")
    return "no pad", f"{read} None is connected" + (f" — {note}." if note else ".")


def _header(panel, table) -> None:
    """One line `HEAD_H` tall: gamepad · how it is read · what is mapped."""
    start = imgui.get_cursor_pos()
    ui._micro("gamepad")
    imgui.same_line()
    word, why = state(panel)
    ui._micro(word, ui.RED if _pad(panel) is not None else ui.DIM)
    if imgui.is_item_hovered():
        ui.tooltip(f"{why} The picture is the table's, with or without a pad.")
    if table is not None:
        imgui.same_line()
        n = len(rows_cached(panel, table))
        imgui.text_colored(ui.DIM, f"{n} mapped")
        if imgui.is_item_hovered():
            ui.tooltip("Controls with a row in bindings.json. A grey label is the "
                              "app's own hand on a free axis, not a row.")
    imgui.set_cursor_pos(start)          # the line is HEAD_H tall whatever is on it
    imgui.dummy(_v(1, HEAD_H - imgui.get_style().item_spacing.y))


def _body(panel, table) -> None:
    _header(panel, table)
    if table is None:
        imgui.text_disabled("no table")
        return
    mapped = rows_cached(panel, table)
    pad = _pad(panel)
    origin = imgui.get_cursor_screen_pos()
    avail = imgui.get_content_region_avail()
    sx = avail.x / gamepad.LAYOUT_W
    sy = avail.y / gamepad.LAYOUT_H
    big = sx >= LABEL_UNIT and sy >= LABEL_UNIT_H
    px = ui_desk.label_px(sx)
    lh = round(px * 1.12)
    dl = imgui.get_window_draw_list()
    mouse = imgui.get_mouse_pos()
    hovered = imgui.is_window_hovered()
    tip = None
    jobs: list[ui_desk._Job] = []
    imgui.push_font(ui._FONTS["ui"], GLYPH_PX if not big else max(GLYPH_PX, 0.16 * sx))
    try:
        st = _state(panel)
        st["origin"], st["unit"] = (origin.x, origin.y), (sx, sy)
        for c in gamepad.LAYOUT:
            x0, y0, x1, y1 = rect(panel, c)
            b = mapped.get(c.source)
            said = says(panel, c, b)
            if big:
                job = _draw_big(panel, dl, pad, c, b, said, x0, y0, x1, y1, lh)
                if job is not None:
                    jobs.append(job)
            else:
                _draw(panel, dl, pad, c, b, said, x0, y0, x1, y1)
            if hovered and x0 <= mouse.x < x1 and y0 <= mouse.y < y1:
                tip = label(panel, c, b)
    finally:
        imgui.pop_font()
    st["labels"] = [j.says for j in jobs]   # each label's text, for the tests and the tools
    for size, last in ((px, False), (ui_desk.LABEL_PX[0], True)):
        if not jobs:
            break
        imgui.push_font(ui._FONTS["ui"], size)
        try:    # a label cut at the labels' size is drawn at the smallest, with more lines
            jobs = ui_desk._labels(dl, jobs, size, round(size * 1.12),
                                   last or size <= ui_desk.LABEL_PX[0])
        finally:
            imgui.pop_font()
    imgui.dummy(avail)
    if tip is not None:
        ui.tooltip(tip)


def rect(panel, c: gamepad.Control) -> tuple[float, float, float, float] | None:
    """Where the pad last drew a control, in screen px (x0, y0, x1, y1);
    None before it has drawn."""
    st = _state(panel)
    if "origin" not in st:
        return None
    (ox, oy), (sx, sy) = st["origin"], st["unit"]
    return (ox + c.x * sx + 1, oy + c.y * sy + 1,
            ox + (c.x + c.w) * sx - 1, oy + (c.y + c.h) * sy - 1)
