"""The APC40 drawn on screen (plan 14 WP7, decision 25 (a)).

A small picture of the desk in the control window, above the cheat
sheet: every control of `apc40.LAYOUT` at its place on the device, with
its glyph — the same glyph the ROUTING page prints first on a desk or
session row and Learn prints in its messages — so a row can be found on
the device by looking.

What is drawn is the **layer that is up** (`Bindings.active`): the
controls mapped on it and the invariant ones are lit, every other control
is dark, exactly as the device's own LEDs and rings are (plan 13 D8). ⇧
fills red while the global layer is up. A knob's arc is its ring — the
param's base (audit R6); a fader's cap the param's value; a button's LED
is filled when the device's would be (`routing.led_lit`, the rule midi.py lights by). The
hover names the control: glyph · param · layer, and Akai's name.

It reads the table, never the port: with no MIDI device (or `[midi]
enabled = false`) it draws the same picture from the router's table. The
lit map is rebuilt only when the table says the desk changed — its
serials (`layer_serial`, `desk_serial`, `redraw_serial`) or a row added
or dropped — and the values are read every frame.

A function over the Panel, like ui_lfo: the cache lives on the panel, a
save of this file lands live (hotreload.MODULES). `ui.desk` (the SYSTEM
page, beside the cheat sheet's switch) hides it.
"""

from __future__ import annotations

import math

from imgui_bundle import imgui

from . import apc40, ui, ui_routing
from .apc40 import GREEN, GREEN_BLINK, RED, RED_BLINK, YELLOW, YELLOW_BLINK
from .routing import Binding, led_lit

SIZE = (380.0, 290.0)      # the window, px — shorter when the control window is
PAD = 8.0
GLYPH_PX = 10.0            # the glyphs' type size
GAP = 12.0                 # from the cheat sheet (or the window's corner)

# LED colours by the grid velocity (apc40's table); any other lit button red
_LED = {GREEN: (0.30, 0.85, 0.40), GREEN_BLINK: (0.30, 0.85, 0.40),
        RED: (1.0, 43 / 255, 43 / 255), RED_BLINK: (1.0, 43 / 255, 43 / 255),
        YELLOW: (0.95, 0.80, 0.25), YELLOW_BLINK: (0.95, 0.80, 0.25)}
_ON = (1.0, 43 / 255, 43 / 255)
_DARK = imgui.ImVec4(0.09, 0.09, 0.10, 1.0)    # a dark control's face
_OFF = imgui.ImVec4(0.34, 0.34, 0.37, 1.0)     # a mapped control's face, LED off


def _table(panel):
    router = ui_routing.router_of(panel)
    return router.table if router is not None else None


def _key(table) -> tuple:
    """What changes the lit map: the table's serials and its rows."""
    return (table.layer, table.layer_serial, table.desk_serial,
            getattr(table, "redraw_serial", 0), id(table.bindings), len(table.bindings))


def lit(table) -> dict[str, Binding]:
    """{glyph: row} for every control the desk shows now — the invariant
    rows and the up layer's (`Bindings.active`), enabled; the first row a
    control has wins, as on the device. An any-channel row lights every
    control it names."""
    out: dict[str, Binding] = {}
    for b in table.active():
        if not b.enabled:
            continue
        for c in apc40.controls(b.source):
            out.setdefault(c.glyph, b)
    return out


def lit_cached(panel, table) -> dict[str, Binding]:
    st = panel.__dict__.setdefault("_desk_state", {})
    key = _key(table)
    if st.get("key") != key or st.get("table") is not table:
        st.update(key=key, table=table, lit=lit(table))
    return st["lit"]


def _layer_word(table, b: Binding) -> str:
    if b.layer is None:
        return "invariant"
    return f"{b.layer} layer"


def label(table, c: apc40.Control, b: Binding | None) -> str:
    """The hover: "D3 · view.bright · preset layer", then Akai's name."""
    if b is None:
        return f"{c.glyph} · unmapped — dark on the {table.layer} layer\n{c.name}"
    return f"{c.glyph} · {b.target} · {_layer_word(table, b)}\n{c.name}"


def _preset_name(panel) -> str:
    pr = ui_routing._presets(panel)
    cur = getattr(pr, "current", None) if pr is not None else None
    return cur or "no preset"


def _led(panel, b: Binding) -> tuple[float, float, float] | None:
    """The colour the device's LED shows for a lit button row, or None (off)."""
    p = panel.reg.get(b.target)
    if p is None or b.feedback != "led":
        return None
    try:
        on = led_lit(b, p)
    except (TypeError, ValueError):
        return None
    if not on:
        return None
    # the clip grid shows the row's colour (green, red, yellow); every
    # other button's LED is a plain on, drawn in the panel's red
    grid = b.kind == "note" and b.number in apc40.N_CLIP
    return _LED.get(int(b.on), _ON) if grid else _ON


def _norm(panel, b: Binding) -> float | None:
    p = panel.reg.get(b.target)
    if p is None:
        return None
    try:
        return max(0.0, min(1.0, float(p.norm)))
    except (TypeError, ValueError):
        return None


def _v(x: float, y: float) -> imgui.ImVec2:
    return imgui.ImVec2(x, y)


def _col(rgb, a: float = 1.0) -> int:
    return ui.u32(imgui.ImVec4(*rgb, a))


def _text(dl, s: str, cx: float, cy: float, color: int, room: float) -> None:
    """`s` centred on (cx, cy) if it fits in `room` px."""
    size = imgui.calc_text_size(s)
    if size.x <= room:
        dl.add_text(_v(cx - size.x / 2, cy - size.y / 2), color, s)


def _draw(panel, dl, table, c: apc40.Control, b: Binding | None,
          x0: float, y0: float, x1: float, y1: float) -> None:
    on = b is not None
    edge = ui.u32(ui.DIM if on else ui.LINE)
    ink = ui.u32(ui.TEXT if on else ui.FAINT)
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    shift = c.glyph == "⇧"
    if c.kind in ("grid", "button"):
        led = _led(panel, b) if on else None
        if shift and table.layer == "global":
            led = (1.0, 43 / 255, 43 / 255)
        face = _col(led, 0.9) if led else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 2.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 2.0)
        _text(dl, c.glyph, cx, cy, ui.u32(imgui.ImVec4(0, 0, 0, 1)) if led else ink, w - 2)
    elif c.kind == "knob":
        r = min(w, h) / 2 - 1
        ky = y0 + r + 1
        dl.add_circle_filled(_v(cx, ky), r, ui.u32(_OFF if on else _DARK))
        dl.add_circle(_v(cx, ky), r, edge)
        v = _norm(panel, b) if on and b.feedback == "ring" else None
        if v is not None:        # the ring: 7 o'clock round to 5 o'clock
            a0 = math.radians(135)
            dl.path_arc_to(_v(cx, ky), r, a0, a0 + math.radians(270) * v, 24)
            dl.path_stroke(ui.u32(ui.RED), thickness=2.0)
        _text(dl, c.glyph, cx, ky, ink, 2 * r)
    else:                        # a fader: vertical, or the crossfader across
        across = w > h
        v = _norm(panel, b) if on else None
        if across:              # the glyph at the left end, the slot after it
            lx = x0 + 16
            dl.add_line(_v(lx, cy), _v(x1 - 4, cy), edge, 2.0)
            if v is not None:
                gx = lx + v * (x1 - 4 - lx)
                dl.add_rect_filled(_v(gx - 4, y0 + 1), _v(gx + 4, y1 - 1), ui.u32(ui.RED), 1.5)
            _text(dl, c.glyph, x0 + 7, cy, ink, 16)
        else:
            top, bot = y0 + 2, y1 - 12
            dl.add_line(_v(cx, top), _v(cx, bot), edge, 2.0)
            if v is not None:
                gy = bot - v * (bot - top)
                dl.add_rect_filled(_v(x0 + 3, gy - 3), _v(x1 - 3, gy + 3), ui.u32(ui.RED), 1.5)
            _text(dl, c.glyph, cx, y1 - 5, ink, w + 4)


def diagram(panel) -> None:
    """The desk window: a header (the layer up, the loaded preset), then
    every control at its place. Bottom-left of the control window, just
    above the cheat sheet when that shows."""
    table = _table(panel)
    io = imgui.get_io()
    below = getattr(panel, "_sheet_h", 0.0) + GAP if panel.cheatsheet else 0.0
    imgui.set_next_window_pos(_v(12, io.display_size.y - 12 - below), imgui.Cond_.always,
                              _v(0, 1))
    room = io.display_size.y - 24 - below
    imgui.set_next_window_size(_v(SIZE[0], max(120.0, min(SIZE[1], room))), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.6)
    flags = (imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_move
             | imgui.WindowFlags_.no_focus_on_appearing | imgui.WindowFlags_.no_nav
             | imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_saved_settings)
    imgui.push_style_var(imgui.StyleVar_.window_padding, _v(PAD, PAD))
    imgui.begin("##desk", None, flags)
    try:
        _body(panel, table)
    finally:
        imgui.end()
        imgui.pop_style_var()


def _body(panel, table) -> None:
    ui._micro("apc40")
    if table is None:
        imgui.same_line()
        imgui.text_disabled("no desk table")
        return
    glob = table.layer == "global"
    imgui.same_line()
    ui._micro(f"{table.layer} layer" + ("  ·  shift" if glob else ""),
              ui.RED if glob else ui.DIM)
    if imgui.is_item_hovered():
        imgui.set_tooltip("The layer that is up — SHIFT (⇧) latches it. Lit controls do "
                          "something on it; dark ones do nothing.")
    imgui.same_line()
    imgui.text_colored(ui.TEXT, _preset_name(panel))
    shown = lit_cached(panel, table)
    origin = imgui.get_cursor_screen_pos()
    avail = imgui.get_content_region_avail()
    sx = avail.x / apc40.LAYOUT_W
    sy = avail.y / apc40.LAYOUT_H
    dl = imgui.get_window_draw_list()
    mouse = imgui.get_mouse_pos()
    hovered = imgui.is_window_hovered()
    tip = None
    imgui.push_font(ui._FONTS["ui"], GLYPH_PX)
    try:
        for c in apc40.LAYOUT:
            x0, y0 = origin.x + c.x * sx + 1, origin.y + c.y * sy + 1
            x1, y1 = origin.x + (c.x + c.w) * sx - 1, origin.y + (c.y + c.h) * sy - 1
            b = shown.get(c.glyph)
            _draw(panel, dl, table, c, b, x0, y0, x1, y1)
            if hovered and x0 <= mouse.x < x1 and y0 <= mouse.y < y1:
                tip = label(table, c, b)
    finally:
        imgui.pop_font()
    imgui.dummy(avail)
    if tip is not None:
        imgui.set_tooltip(tip)
