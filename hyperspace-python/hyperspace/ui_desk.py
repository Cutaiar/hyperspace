"""The APC40 drawn on screen (plan 14 WP7, decision 25 (a); plan 17 WP4).

A picture of the desk in the control window: every control of
`apc40.LAYOUT` at its place on the device, with its glyph — the same
glyph the ROUTING page prints first on a desk or session row and Learn
prints in its messages — so a row can be found on the device by looking.

**It takes the room it has** (`room`, plan 17 fork 1): the space left of
the panel, bottom-left, above the cheat sheet when that shows; with the
panel hidden (`ui.panel`: H, DEVICE ON/OFF, the header's `big` chip) it is
the whole control window. There is no DESK page and no param for its
size. Once a layout unit is `LABEL_UNIT` px wide every lit control also
carries **what it does** (`text`): its param's label, or the value's name
for an enum `set` row (the bank row reads the presets' names). A label in
the bright ink is a row of the layer that is up; a grey one is invariant
— the same on both layers. Under that size the drawing is the glyphs
alone, as before.

What is drawn is the **layer that is up** (`Bindings.active`): the
controls mapped on it and the invariant ones are lit, every other control
is dark, exactly as the device's own LEDs and rings are (plan 13 D8), at
either size. ⇧ fills red while the global layer is up. A knob's arc is
its ring — the param's base (audit R6); a fader's cap the param's value;
a button's LED is filled when the device's would be (`routing.led_lit`,
the rule midi.py lights by). The hover names the control: glyph · param ·
its label · layer, and Akai's name.

It reads the table, never the port: with no MIDI device (or `[midi]
enabled = false`) it draws the same picture from the router's table. The
lit map is rebuilt only when the table says the desk changed — its
serials (`layer_serial`, `desk_serial`, `redraw_serial`) or a row added
or dropped — and the values are read every frame.

**A click picks a control** (`click`, plan 17 forks 2 and 3): it is
framed in red here and on its ROUTING line (which the rows scroll to,
`ui_routing.goto`), and the next click on a
param's widget — on a page drawn dimmed, taking no other input
(`Panel._draw`, `Panel._ctx`) — puts the control on that param, through
`Learn.map_picked`: the knob learn's road, its refusals, its undo step.
An invariant control, or any control while the global layer is up, is
picked for the look only (`mappable` says why) and dims nothing. A click
on the picked control, on the desk's empty ground or on the footer's
line lets go, and so does `PICK_S` seconds without a click (`tick`) —
a dimmed page is never left standing. While "Learn desk" is armed a
click completes it instead, as a knob bump would.

A function over the Panel, like ui_lfo: the cache lives on the panel, a
save of this file lands live (hotreload.MODULES). `ui.desk` (the SYSTEM
page, beside the cheat sheet's switch) hides it at any size. The window
is hit-tested — no widget per control; its one widget is the header's
chip — and never scrolls.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, replace

from imgui_bundle import imgui

from . import apc40, ui, ui_routing
from .apc40 import GREEN, GREEN_BLINK, RED, RED_BLINK, YELLOW, YELLOW_BLINK
from .params import Kind
from .routing import Binding, led_lit

MIN_W = 300.0              # the window is never narrower, px
MIN_H = 120.0              # …or shorter (a control window with no room above the sheet)
LABEL_UNIT = 44.0          # a layout unit this wide or wider carries labels
EDGE = 12.0                # from the control window's edges, the panel and the sheet
PAD = 8.0
HEAD_H = 26.0              # the header's line: the layer, the preset, the chip
GLYPH_PX = 10.0            # the glyphs' type size
GAP = EDGE                 # from the cheat sheet
LABEL_PX = (11.0, 18.0)    # the labels' type size: 0.2 of a unit, kept in this range
LABEL_LINES = 2            # a label wraps to at most this many lines
BIG, PANEL = "big", "panel"    # the header's chip: hide the panel / bring it back
PICK_S = 20.0              # a picked control lets go by itself after this long with no click
LET_GO_TIP = "click to let go"     # the footer's picked line: on it where it fits, and on hover

# LED colours by the grid velocity (apc40's table); any other lit button red
_LED = {GREEN: (0.30, 0.85, 0.40), GREEN_BLINK: (0.30, 0.85, 0.40),
        RED: (1.0, 43 / 255, 43 / 255), RED_BLINK: (1.0, 43 / 255, 43 / 255),
        YELLOW: (0.95, 0.80, 0.25), YELLOW_BLINK: (0.95, 0.80, 0.25)}
_ON = (1.0, 43 / 255, 43 / 255)
_DARK = imgui.ImVec4(0.09, 0.09, 0.10, 1.0)    # a dark control's face
_OFF = imgui.ImVec4(0.34, 0.34, 0.37, 1.0)     # a mapped control's face, LED off
_BLACK = imgui.ImVec4(0, 0, 0, 1)              # ink on a lit LED
_ON_LED = imgui.ImVec4(0.16, 0.05, 0.05, 1)    # an invariant label on a lit LED


def _table(panel):
    router = ui_routing.router_of(panel)
    return router.table if router is not None else None


def _state(panel) -> dict:
    return panel.__dict__.setdefault("_desk_state", {})


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
    st = _state(panel)
    key = _key(table)
    if st.get("key") != key or st.get("table") is not table:
        st.update(key=key, table=table, lit=lit(table))
    return st["lit"]


# ---------------------------------------------------------------- the pick

def mappable(table, c: apc40.Control) -> str | None:
    """Why a click on a param could not put this control on it, or None
    when it can: an invariant control is the session's on both layers
    (D6), and nothing is mapped while the global layer is up (D5) — what
    `Learn.learn_control` refuses, asked before the click."""
    name = apc40.named(c.source) or c.glyph
    if table.is_invariant(Binding(c.source, "", "abs", layer="preset")):
        return f"{name} is invariant (the session's)"
    if table.layer == "global":
        return (f"{name} is on the global layer (the session's) — latch SHIFT off to map "
                "into the preset")
    return None


def picked(panel) -> apc40.Control | None:
    """The picked control (`Learn.control`), or None."""
    source = getattr(getattr(panel, "learn", None), "control", None)
    cs = apc40.controls(source) if source else []
    return cs[0] if cs else None


def _stamp(panel, source: str, now: float | None = None, frame: int = -1) -> dict:
    now = time.monotonic() if now is None else now
    pk = _state(panel)["pick"] = {"source": source, "made": now, "at": now, "frame": frame}
    return pk


def let_go(panel) -> None:
    """Let the picked control go (a click on it, on the desk's ground, on
    the footer's line)."""
    lrn = getattr(panel, "learn", None)
    if lrn is not None and getattr(lrn, "control", None) is not None:
        lrn.pick(None)
    _state(panel).pop("pick", None)


def left(panel, now: float | None = None) -> float:
    """Seconds until the pick lets go by itself."""
    pk = _state(panel).get("pick")
    if pk is None:
        return PICK_S
    return max(0.0, PICK_S - ((time.monotonic() if now is None else now) - pk["at"]))


def made(panel) -> float:
    """When the pick was made (`time.monotonic`), 0.0 with none."""
    pk = _state(panel).get("pick")
    return pk["made"] if pk is not None else 0.0


def tick(panel, now: float | None = None) -> None:
    """Once a frame, desk shown or not: a pick lets go by itself after
    `PICK_S` seconds with no click anywhere in the window, and says so —
    a page is never left dimmed because someone walked away."""
    lrn = getattr(panel, "learn", None)
    source = getattr(lrn, "control", None)
    st = _state(panel)
    if source is None:
        st.pop("pick", None)
        return
    now = time.monotonic() if now is None else now
    pk = st.get("pick")
    if pk is None or pk["source"] != source:
        _stamp(panel, source, now)             # picked by something other than `click`
    elif imgui.is_mouse_clicked(0) or imgui.is_mouse_clicked(1):
        pk["at"] = now                         # someone is at it: the count starts again
    elif now - pk["at"] >= PICK_S:
        c = picked(panel)
        let_go(panel)
        lrn.said(f"{c.glyph if c is not None else source} let go — no click for {PICK_S:.0f} s")


def picking(panel) -> apc40.Control | None:
    """The picked control while a click on a param would map it — the
    state the open page dims for: a mappable pick, and not in the frame
    of the click that made it (that click is not a param's)."""
    c = picked(panel)
    table = _table(panel)
    if c is None or table is None:
        return None
    pk = _state(panel).get("pick")
    if pk is not None and pk["frame"] == imgui.get_frame_count():
        return None
    return c if mappable(table, c) is None else None


def pick_line(panel, table, c: apc40.Control) -> tuple[str, bool]:
    """What the desk's header says of the picked control, and whether a
    click on a param would map it: "D3 picked: click a param to put it
    here · click D3 again to let go", or why not and what the control
    does ("S3 (track fader 3) is invariant (the session's): SUB Post-drive")."""
    why = mappable(table, c)
    if why is None:
        return (f"{c.glyph} picked: click a param to put it here · click {c.glyph} again "
                "to let go"), True
    b = lit_cached(panel, table).get(c.glyph)
    does = text(panel.reg, b) if b is not None else f"unmapped on the {table.layer} layer"
    return f"{why}: {does}", False


def footer_line(panel, now: float | None = None) -> tuple[str, bool] | None:
    """The footer's picked line, with the seconds left: (words, whether a
    click on a param would map), None with nothing picked."""
    c, table = picked(panel), _table(panel)
    if c is None or table is None:
        return None
    line, can = pick_line(panel, table, c)
    secs = math.ceil(left(panel, now))
    if can:
        return f"{c.glyph} picked ({secs} s): click a param to put it here", True
    return f"{line} ({secs} s)", False


def click(panel, table, c: apc40.Control, b: Binding | None) -> None:
    """A left click on a control of the desk.

    1. "Learn desk" is armed → the click completes it, as a knob bump
       would: `Learn.learn_control`, its refusals (an invariant control,
       the global layer), its undo step. Nothing else happens.
    2. A hand learn is armed → nothing: the footer keeps saying what the
       learn waits for.
    3. The control is the picked one → it is let go.
    4. Otherwise → it is picked; ROUTING scrolls to its line if it is
       open, or when it next is (`ui_routing.goto` — the page is not
       changed, fork 2), its filter cleared; and a hidden panel comes back
       (the desk shrinks to its column and the pick is still framed)."""
    lrn = getattr(panel, "learn", None)
    if lrn is None:
        return
    if getattr(lrn, "learning", None) is not None:
        if lrn.accepts(c.source):
            lrn.learn_control(c.source, apc40)
        return
    if getattr(lrn, "control", None) == c.source:
        let_go(panel)
        return
    lrn.pick(c.source)
    _stamp(panel, c.source, frame=imgui.get_frame_count())
    ui_routing.goto(panel, c.source)        # ROUTING scrolls to its line, if or when it is open
    if not panel.open:
        _show_panel(panel, True)


def rect(panel, c: apc40.Control) -> tuple[float, float, float, float] | None:
    """Where the desk last drew a control, in screen px (x0, y0, x1, y1);
    None before it has drawn."""
    st = _state(panel)
    if "origin" not in st:
        return None
    (ox, oy), (sx, sy) = st["origin"], st["unit"]
    return (ox + c.x * sx + 1, oy + c.y * sy + 1,
            ox + (c.x + c.w) * sx - 1, oy + (c.y + c.h) * sy - 1)


def _show_panel(panel, on: bool) -> None:
    p = panel.reg.get("ui.panel")
    if p is not None:
        p.set(on)
    else:                                   # (a registry from before the panel's params)
        panel.open = on


def _hover(panel, table, c: apc40.Control, b: Binding | None) -> str:
    """The hover, and what a click would do now."""
    tip = label(table, c, b, panel.reg)
    lrn = getattr(panel, "learn", None)
    if lrn is None:
        return tip
    if getattr(lrn, "learning", None) is not None:
        return f"{tip}\nclick: learn {lrn.learning} here" if lrn.accepts(c.source) else tip
    if getattr(lrn, "control", None) == c.source:
        return f"{tip}\nclick: let go"
    if mappable(table, c) is None:
        return f"{tip}\nclick: pick it — then click a param to put it there"
    return f"{tip}\nclick: pick it — ROUTING shows its row"


# ---------------------------------------------------------------- the room

def room(display: tuple[float, float], panel_x: float | None,
         sheet: tuple[float, float] | None) -> tuple[float, float, float, float]:
    """(x, y, w, h) of the desk window. `panel_x`: the panel's left edge,
    None while it is hidden. `sheet`: the cheat sheet's (w, h), None
    while it is off.

    Bottom-left, `EDGE` from the window's edges. Its right edge is `EDGE`
    left of the panel, or of the window's right edge with the panel
    hidden; never narrower than `MIN_W`. The cheat sheet, when on: with
    the panel open the desk sits above it; with the panel hidden, beside
    it, full height. As tall as there is room for, capped so a layout
    unit is never taller than it is wide."""
    dw, dh = display
    x, bottom = EDGE, dh - EDGE
    right = (dw if panel_x is None else panel_x) - EDGE
    if sheet is not None:
        if panel_x is None:
            x += sheet[0] + GAP
        else:
            bottom -= sheet[1] + GAP
    w = max(MIN_W, right - x)
    unit = (w - 2 * PAD) / apc40.LAYOUT_W
    h = max(MIN_H, min(bottom - EDGE, unit * apc40.LAYOUT_H + 2 * PAD + HEAD_H))
    w, h = float(int(w)), float(int(h))          # whole pixels, as imgui places a window
    return x, bottom - h, w, h


def _room(panel) -> tuple[float, float, float, float]:
    """`room` for this frame: the panel's edge is last frame's (the desk
    is drawn before the panel), its launch place before there is one."""
    io = imgui.get_io()
    display = (io.display_size.x, io.display_size.y)
    panel_x = None
    if panel.open:
        panel_x = getattr(panel, "_panel_x", None)
        if panel_x is None:
            panel_x = display[0] - ui.PANEL_W - EDGE
    sheet = None
    if panel.cheatsheet:
        sheet = (getattr(panel, "_sheet_w", 0.0), getattr(panel, "_sheet_h", 0.0))
    return room(display, panel_x, sheet)


# ---------------------------------------------------------------- what a control says

def text(reg, b: Binding) -> str:
    """What a lit control does, in the panel's words (plan 17 fork 8): a
    `set` row on an enum → that value's name (the bank row reads the
    presets' names, a shape pad the shape's); a `step` row → the label and
    the step ("Brightness +3"); anything else → the param's label; a
    target the registry lacks (or a param with no label) → the id."""
    p = reg.get(b.target)
    if p is None:
        return b.target
    if b.op == "set" and p.kind is Kind.ENUM:
        names = p.names
        i = round(b.value)
        if 0 <= i < len(names) and names[i]:
            return str(names[i])
    if b.op == "step":
        return f"{p.label or b.target} {b.value:+g}"
    return p.label or b.target


_STEP = re.compile(r"^[+\-−]\d")      # a step's amount, the last word of `text` for a step row


def _cut(line: str, width: float) -> str:
    """`line` cut to `width` px with an ellipsis — keeping a step's amount
    at its end, so ▲ and ▼ on one param do not both read "Brightn…"."""
    if imgui.calc_text_size(line).x <= width:
        return line
    head, _, tail = line.rpartition(" ")
    if head and _STEP.match(tail):
        room_ = width - imgui.calc_text_size(f" {tail}").x
        return f"{ui.fit_text(head, max(0.0, room_))} {tail}"
    return ui.fit_text(line, width)


def wrap(text: str, width: float, lines: int) -> list[str]:
    """`text` on at most `lines` lines of `width` px in the current font:
    broken at spaces, the last line taking what is left, and each line cut
    with an ellipsis (`ui.fit_text`) if it is still too wide."""
    words = text.split()
    out: list[str] = []
    while words and len(out) < lines:
        if len(out) == lines - 1:
            line, words = " ".join(words), []
        else:
            line = words.pop(0)
            while words and imgui.calc_text_size(f"{line} {words[0]}").x <= width:
                line = f"{line} {words.pop(0)}"
        out.append(_cut(line, width))
    return out


def is_cut(text: str, rows: list[str]) -> bool:
    """Did `wrap` have to leave some of `text` out?"""
    return " ".join(rows) != " ".join(text.split())


_WRAPS: dict[tuple, list[str]] = {}     # (text, width, lines, px) → wrap(): measured once


def _wrapped(text: str, width: float, lines: int, px: float) -> list[str]:
    key = (text, round(width), lines, round(px, 1))
    hit = _WRAPS.get(key)
    if hit is None:
        if len(_WRAPS) > 4000:          # preset names come and go; never grows without end
            _WRAPS.clear()
        hit = _WRAPS[key] = wrap(text, width, lines)
    return hit


def label_px(unit: float) -> float:
    """The labels' type size for a layout unit `unit` px wide."""
    return max(LABEL_PX[0], min(LABEL_PX[1], 0.2 * unit))


def _layer_word(table, b: Binding) -> str:
    if b.layer is None:
        return "invariant"
    return f"{b.layer} layer"


def label(table, c: apc40.Control, b: Binding | None, reg=None) -> str:
    """The hover: "D3 · fx.kaleido.segments · Kaleidoscope segments ·
    preset layer", then Akai's name. Without a registry (or when the text
    is the id) the param's words are left out."""
    if b is None:
        return f"{c.glyph} · unmapped — dark on the {table.layer} layer\n{c.name}"
    says = text(reg, b) if reg is not None else b.target
    mid = b.target if says == b.target else f"{b.target} · {says}"
    return f"{c.glyph} · {mid} · {_layer_word(table, b)}\n{c.name}"


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


def _face(panel, table, c: apc40.Control, b: Binding | None):
    """A button's LED colour (None: off) — ⇧ lit while the global layer is up."""
    led = _led(panel, b) if b is not None else None
    if c.glyph == "⇧" and table.layer == "global":
        led = _ON
    return led


def _ring(dl, cx: float, cy: float, r: float, v: float | None) -> None:
    """The ring's arc: 7 o'clock round to 5 o'clock."""
    if v is not None:
        a0 = math.radians(135)
        dl.path_arc_to(_v(cx, cy), r, a0, a0 + math.radians(270) * v, 24)
        dl.path_stroke(ui.u32(ui.RED), thickness=2.0)


def _draw(panel, dl, table, c: apc40.Control, b: Binding | None,
          x0: float, y0: float, x1: float, y1: float) -> None:
    """One control at the small size: its glyph on its face."""
    on = b is not None
    edge = ui.u32(ui.DIM if on else ui.LINE)
    ink = ui.u32(ui.TEXT if on else ui.FAINT)
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if c.kind in ("grid", "button"):
        led = _face(panel, table, c, b)
        face = _col(led, 0.9) if led else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 2.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 2.0)
        _text(dl, c.glyph, cx, cy, ui.u32(_BLACK) if led else ink, w - 2)
    elif c.kind == "knob":
        r = min(w, h) / 2 - 1
        ky = y0 + r + 1
        dl.add_circle_filled(_v(cx, ky), r, ui.u32(_OFF if on else _DARK))
        dl.add_circle(_v(cx, ky), r, edge)
        _ring(dl, cx, ky, r, _norm(panel, b) if on and b.feedback == "ring" else None)
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


@dataclass(frozen=True)
class _Job:
    """A label still to draw: its text, the room it has, the lines that
    room holds at the labels' size, its ink, how it sits — "mid" centred
    both ways, "top" centred across and hung from the top, "left" on one
    line from the left — and, for a pad, its face's colour (a label drawn
    across a run of pads covers the edges between them with it)."""

    says: str
    x0: float
    y0: float
    x1: float
    y1: float
    lines: int
    ink: int
    how: str
    face: int | None = None
    run: bool = False


def _draw_big(panel, dl, table, c: apc40.Control, b: Binding | None,
              x0: float, y0: float, x1: float, y1: float, lh: float) -> _Job | None:
    """One control at the labelled size: its face, its glyph small in the
    top-left corner, and — returned, for the label pass, which draws in
    the labels' type — the room its label has. `lh` is a label line's
    height. A dark control gets no label (D8)."""
    on = b is not None
    edge = ui.u32(ui.DIM if on else ui.LINE)
    small = ui.u32(ui.DIM if on else ui.FAINT)          # the glyph: small and dim
    # whose row it is: the up layer's in the bright ink, an invariant one grey
    ink = ui.u32(ui.TEXT if on and b.layer is not None else ui.DIM)
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    gsz = imgui.calc_text_size(c.glyph)
    says = text(panel.reg, b) if on else ""
    if c.kind in ("grid", "button"):
        led = _face(panel, table, c, b)
        face = _col(led, 0.9) if led else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 3.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 3.0)
        if led:
            small = ui.u32(_BLACK)
            ink = ui.u32(_BLACK if b.layer is not None else _ON_LED)
        below = int((h - gsz.y - 1) / lh)               # lines that fit under the glyph
        if below >= 1:
            dl.add_text(_v(x0 + 3, y0 + 1), small, c.glyph)
            return _Job(says, x0 + 3, y0 + gsz.y, x1 - 3, y1 - 1, min(LABEL_LINES, below),
                        ink, "mid", face) if on else None
        # a low button: the label beside the glyph, on its line
        dl.add_text(_v(x0 + 3, (y0 + y1 - gsz.y) / 2), small, c.glyph)
        return _Job(says, x0 + gsz.x + 7, y0, x1 - 3, y1, 1, ink, "mid", face) if on else None
    if c.kind == "knob":
        lines = LABEL_LINES if h - LABEL_LINES * lh >= 0.45 * h else 1
        r = max(4.0, min((h - lines * lh - 4) / 2, 0.3 * w))
        ky = y0 + r + 1
        dl.add_circle_filled(_v(cx, ky), r, ui.u32(_OFF if on else _DARK))
        dl.add_circle(_v(cx, ky), r, edge)
        _ring(dl, cx, ky, r, _norm(panel, b) if on and b.feedback == "ring" else None)
        dl.add_text(_v(x0 + 1, y0), small, c.glyph)
        return _Job(says, x0 + 1, ky + r + 2, x1 - 1, y1, lines, ink, "top") if on else None
    v = _norm(panel, b) if on else None
    if w > h:                    # the crossfader: glyph and label on a line, the slot under it
        dl.add_text(_v(x0 + 3, y0 + 1), small, c.glyph)
        sy = min(y1 - 6, y0 + max(gsz.y, lh) + 4 + (h - max(gsz.y, lh) - 4) / 2)
        dl.add_line(_v(x0 + 6, sy), _v(x1 - 6, sy), edge, 2.0)
        if v is not None:
            gx = x0 + 6 + v * (w - 12)
            dl.add_rect_filled(_v(gx - 5, sy - 8), _v(gx + 5, sy + 8), ui.u32(ui.RED), 2.0)
        return _Job(says, x0 + gsz.x + 9, y0, x1 - 3, y0 + lh + 2, 1, ink,
                    "left") if on else None
    # a fader: the glyph in the corner, the slot, the label at the foot
    dl.add_text(_v(x0 + 1, y0), small, c.glyph)
    top, bot = y0 + gsz.y + 4, y1 - LABEL_LINES * lh - 8
    dl.add_line(_v(cx, top), _v(cx, bot), edge, 2.0)
    if v is not None:
        gy = bot - v * (bot - top)
        half = min(0.3 * w, 16.0)
        dl.add_rect_filled(_v(cx - half, gy - 4), _v(cx + half, gy + 4), ui.u32(ui.RED), 2.0)
    return _Job(says, x0 + 1, y1 - LABEL_LINES * lh - 2, x1 - 1, y1, LABEL_LINES, ink,
                "top") if on else None


def _labels(dl, jobs: list[_Job], px: float, lh: float, last: bool = False) -> list[_Job]:
    """Draw the labels (the labels' type, `px`, is pushed). A label that
    would be cut at this size is not drawn but returned, for a second pass
    at the smallest size — `last`, which draws whatever fits."""
    small: list[_Job] = []
    for j in jobs:
        # the lines the room holds at this size (a second pass fits more)
        lines = j.lines if not last else max(1, min(LABEL_LINES, int((j.y1 - j.y0 + 1) / lh)))
        rows = _wrapped(j.says, j.x1 - j.x0, lines, px)
        if not last and is_cut(j.says, rows):
            small.append(j)
            continue
        y = j.y0 if j.how != "mid" else j.y0 + max(0.0, (j.y1 - j.y0 - len(rows) * lh) / 2)
        widths = [imgui.calc_text_size(row).x for row in rows]
        if j.run and j.face is not None and rows:      # over the edges between the run's pads
            half, cx = max(widths) / 2 + 4, (j.x0 + j.x1) / 2
            dl.add_rect_filled(_v(cx - half, y), _v(cx + half, y + len(rows) * lh), j.face)
        for row, tw in zip(rows, widths):
            x = j.x0 if j.how == "left" else j.x0 + max(0.0, (j.x1 - j.x0 - tw) / 2)
            dl.add_text(_v(x, y), j.ink, row)
            y += lh
    return small


def _runs(jobs: list[tuple[apc40.Control, _Job]]) -> list[_Job]:
    """Adjacent pads of one row whose text is the same share one label,
    drawn across the run (the clip-stop row reads "Save as a new preset"
    once). Each pad is still its own control to the mouse."""
    out: list[_Job] = []
    prev: apc40.Control | None = None
    for c, job in jobs:
        last = out[-1] if out else None
        if (prev is not None and last is not None and c.kind in ("grid", "button")
                and prev.kind == c.kind and prev.y == c.y and prev.h == c.h
                and abs(prev.x + prev.w - c.x) < 1e-6
                and replace(last, x0=job.x0, x1=job.x1, run=False) == job):
            out[-1] = replace(last, x1=job.x1, run=True)   # the run's label reaches this pad
        else:
            out.append(job)
        prev = c
    return out


def diagram(panel) -> None:
    """The desk window: a header (the layer up, the loaded preset, the
    `big` / `panel` chip), then every control at its place — in the room
    `room` gives it."""
    table = _table(panel)
    x, y, w, h = _room(panel)
    imgui.set_next_window_pos(_v(x, y), imgui.Cond_.always)
    imgui.set_next_window_size(_v(w, h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.6)
    flags = (imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_move
             | imgui.WindowFlags_.no_focus_on_appearing | imgui.WindowFlags_.no_nav
             | imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse
             | imgui.WindowFlags_.no_saved_settings)
    imgui.push_style_var(imgui.StyleVar_.window_padding, _v(PAD, PAD))
    imgui.begin("##desk", None, flags)
    try:
        _body(panel, table)
    finally:
        imgui.end()
        imgui.pop_style_var()


def _chip(panel) -> None:
    """The header's one widget, flush right: `big` hides the panel (the
    desk takes the window), `panel` brings it back. Nothing new behind
    it: it sets `ui.panel`, as H and DEVICE ON/OFF do."""
    name = BIG if panel.open else PANEL
    if ui.chip(f"{name}##desk"):
        _show_panel(panel, not panel.open)
    if imgui.is_item_hovered():
        imgui.set_tooltip("Hide the panel: the desk takes the whole window and every lit "
                          "control carries its name (H brings the panel back)"
                          if name == BIG else "Bring the panel back (H)")


def _header(panel, table) -> None:
    """One line `HEAD_H` tall: apc40 · the layer up · the loaded preset,
    and the chip at the right. While a control is picked the line says so
    — what is picked, what the next click does, how to let go, the
    seconds left — after the preset's name where there is room (the big
    desk), in place of the line's other words where there is not."""
    start = imgui.get_cursor_pos()
    full = imgui.get_content_region_avail().x
    end = start.x + full - ui.chip_w(BIG) - 8        # where the words stop: the chip
    imgui.set_cursor_pos(_v(start.x, start.y + 3))
    c = picked(panel) if table is not None else None
    line = can = None
    if c is not None:
        line, can = pick_line(panel, table, c)
        line = f"{line} · {math.ceil(left(panel))} s"
        words = (ui._micro_width("apc40") + ui._micro_width(f"{table.layer} layer  ·  shift")
                 + imgui.calc_text_size(f"{_preset_name(panel)}").x + 40)
        if imgui.calc_text_size(line).x > end - start.x - words:
            imgui.text_colored(ui.RED if can else ui.DIM, ui.fit_text(line, end - start.x))
            if imgui.is_item_hovered():
                imgui.set_tooltip(line)
            imgui.set_cursor_pos(_v(start.x + full - ui.chip_w(BIG if panel.open else PANEL),
                                    start.y))
            _chip(panel)
            imgui.set_cursor_pos(start)
            imgui.dummy(_v(1, HEAD_H - imgui.get_style().item_spacing.y))
            return
    ui._micro("apc40")
    if table is None:
        imgui.same_line()
        imgui.text_disabled("no desk table")
    else:
        glob = table.layer == "global"
        imgui.same_line()
        ui._micro(f"{table.layer} layer" + ("  ·  shift" if glob else ""),
                  ui.RED if glob else ui.DIM)
        if imgui.is_item_hovered():
            imgui.set_tooltip("The layer that is up — SHIFT (⇧) latches it. Lit controls do "
                              "something on it; dark ones do nothing.")
        imgui.same_line()
        room_ = end - imgui.get_cursor_pos_x()
        imgui.text_colored(ui.TEXT, ui.fit_text(_preset_name(panel), max(0.0, room_)))
        if line is not None:
            imgui.same_line(0, 20)
            imgui.text_colored(ui.RED if can else ui.DIM, line)
    imgui.set_cursor_pos(_v(start.x + full - ui.chip_w(BIG if panel.open else PANEL), start.y))
    _chip(panel)
    imgui.set_cursor_pos(start)          # the line is HEAD_H tall whatever is on it
    imgui.dummy(_v(1, HEAD_H - imgui.get_style().item_spacing.y))


def _body(panel, table) -> None:
    _header(panel, table)
    if table is None:
        return
    shown = lit_cached(panel, table)
    origin = imgui.get_cursor_screen_pos()
    avail = imgui.get_content_region_avail()
    sx = avail.x / apc40.LAYOUT_W
    sy = avail.y / apc40.LAYOUT_H
    big = sx >= LABEL_UNIT
    px = label_px(sx)
    lh = round(px * 1.12)
    dl = imgui.get_window_draw_list()
    mouse = imgui.get_mouse_pos()
    hovered = imgui.is_window_hovered()
    tip = hit = frame = None
    source = getattr(getattr(panel, "learn", None), "control", None)
    jobs: list[tuple[apc40.Control, _Job]] = []
    imgui.push_font(ui._FONTS["ui"], GLYPH_PX if not big else max(GLYPH_PX, 0.16 * sx))
    try:
        st = _state(panel)
        st["origin"], st["unit"] = (origin.x, origin.y), (sx, sy)
        for c in apc40.LAYOUT:
            x0, y0, x1, y1 = rect(panel, c)
            b = shown.get(c.glyph)
            if big:
                job = _draw_big(panel, dl, table, c, b, x0, y0, x1, y1, lh)
                if job is not None:
                    jobs.append((c, job))
            else:
                _draw(panel, dl, table, c, b, x0, y0, x1, y1)
            if hovered and x0 <= mouse.x < x1 and y0 <= mouse.y < y1:
                tip, hit = _hover(panel, table, c, b), (c, b)
            if c.source == source:
                frame = (x0, y0, x1, y1)
    finally:
        imgui.pop_font()
    labels = _runs(jobs)
    st["labels"] = [j.says for j in labels]     # each label's text, for the tests and the tools
    for size, last in ((px, False), (LABEL_PX[0], True)):
        if not labels:
            break
        imgui.push_font(ui._FONTS["ui"], size)
        try:        # a label cut at the labels' size is drawn at the smallest, with more lines
            labels = _labels(dl, labels, size, round(size * 1.12), last or size <= LABEL_PX[0])
        finally:
            imgui.pop_font()
    if frame is not None:           # the picked control: a red frame, at either size
        x0, y0, x1, y1 = frame
        dl.add_rect(_v(x0 - 2, y0 - 2), _v(x1 + 2, y1 + 2), ui.u32(ui.RED), 4.0, 2.5)
    imgui.dummy(avail)
    if tip is not None:
        imgui.set_tooltip(tip)
    # the window is hit-tested: a left click on a control is `click`; on
    # the ground between the controls it lets the picked control go
    if hovered and imgui.is_mouse_clicked(0) and mouse.y >= origin.y:
        if hit is not None:
            click(panel, table, *hit)
        else:
            let_go(panel)
