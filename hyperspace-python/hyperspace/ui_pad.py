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

**The pad in hand** (plan 42): the picture is the model read
(`gamepad.layout_for`, `gamepad.shown_model` — while lost, the one the
entry's ``controller =`` names): a DualSense or an Edge draws its own
glyphs (✕ where an Xbox pad's A is), its touchpad with each finger on it
(every ``touch:`` row lights it), a tilt bubble that rings red on a shake
(every ``motion:`` row), the Edge's back and Fn buttons, and the light
bar's colour beside the header's word.

Read-only: the hover names the control, its param and its source, and a
click does nothing. Learn pad is still the way onto a control — the
binding menu on any param (right-click → Learn pad), which the hover
points at.

A function over the Panel, like ui_desk: the cache lives on the panel, a
save of this file lands live (hotreload.MODULES). `ui.pad_diagram` (the
SYSTEM page, beside the desk's switch) hides it.
"""

from __future__ import annotations

import math

from imgui_bundle import imgui

from . import gamepad, ui, ui_desk, ui_pad_nvg, ui_pad_views, ui_routing
from .routing import PAIR_SCHEME, Binding, layout_of, pair_poles

SCHEMES = ("pad", "hat", "axis", "pair", "touch", "motion")   # the schemes a pad control's row can have
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


def rows(table, model=None) -> dict[str, Binding]:
    """{source: the row that acts} for every enabled pad, D-pad or axis
    row of the table — the first row a control has wins, as the adapters
    read them. Keyed by the layout's source, so a lane addressed by
    number (``axis:4``) lands on the control it names. `model`, the pad
    read: its own layout's rows stand in for the table's (`layout_of`)."""
    out: dict[str, Binding] = {}
    every = gamepad.layout_for(gamepad.models.MODELS["edge"])   # every control a pad can have
    layout = layout_of(model)
    for b in layout.rows:
        out[b.source] = b
    for b in table.of(*SCHEMES):
        if not b.enabled or layout.hides(b):
            continue
        poles = pair_poles(":".join(b.parts)) if b.scheme == PAIR_SCHEME else None
        for pole in poles or ():         # plan 56: a pair's row is on both its poles
            out.setdefault(pole.source, b)
        c = gamepad.control_in(every, b.source)
        if c is not None:
            out.setdefault(c.source, b)
    return out


def source_rows(table, model=None) -> dict[str, Binding]:
    """{source: the row that acts} by the exact address a row names — the
    lanes view's (``touch:pinch`` apart from ``touch:x``), where `rows`
    folds every touch row onto the touchpad. `model` as `rows`."""
    layout = layout_of(model)
    out: dict[str, Binding] = {b.source: b for b in layout.rows}
    for b in table.of(*SCHEMES):
        if b.enabled and not layout.hides(b):
            out.setdefault(b.source, b)
    return out


def _model(panel):
    """The model of the pad read now, for its own layout; None with no pad."""
    return getattr(_pad(panel), "model", None)


def _stick_quiet(panel, source: str) -> bool:
    """Is a route on this stick address not heard now? A Joy-Con's, with the
    totem off (`PadDevice._quiet_stick`)."""
    if not getattr(_model(panel), "layout", ()):
        return False
    if source not in ("axis:LX", "axis:LY") and not source.startswith("axis:L."):
        return False
    reg = getattr(panel, "reg", None)
    return not (reg is not None and "totem.on" in reg and reg["totem.on"].value)


def built_in(panel, source: str) -> str:
    """What an axis does with no route on it, for the pad read now: `BUILT_IN`,
    less what a pad with a layout of its own keeps free (`PadDevice._no_camera_job`)."""
    model = _model(panel)
    if getattr(model, "layout", ()):
        if source in ("axis:LT", "axis:RT"):
            return ""
        if source in ("axis:LX", "axis:LY"):
            reg = getattr(panel, "reg", None)
            if reg is not None and "totem.on" in reg and reg["totem.on"].value:
                return ""
    return BUILT_IN.get(source, "")


def view_of(panel) -> str:
    """The pad window's readout (`ui.pad_view`): one of ui_pad_views.VIEWS."""
    k = int(panel.__dict__.get("pad_view", 0) or 0)
    return ui_pad_views.VIEWS[k] if 0 <= k < len(ui_pad_views.VIEWS) else "map"


def step_view(panel) -> None:
    """The next readout, round: what a click on the header's name does."""
    k = (ui_pad_views.VIEWS.index(view_of(panel)) + 1) % len(ui_pad_views.VIEWS)
    reg = getattr(panel, "reg", None)
    if reg is not None and "ui.pad_view" in reg:
        reg["ui.pad_view"].set(k)
    else:
        panel.pad_view = k


def _key(table) -> tuple:
    """What the pad's cached rows depend on, without a scan of the rows
    (the pad window reads it every frame): the list (its identity and
    length: a row added, removed, put in another's stead) and the table's
    serials for a row edited in place (`rows_serial`: enabled, re-pointed,
    retargeted; `redraw_serial`: a desk or GRAPH edit)."""
    return (id(table.bindings), len(table.bindings), getattr(table, "rows_serial", 0),
            getattr(table, "redraw_serial", 0))


def rows_cached(panel, table) -> dict[str, Binding]:
    st = _state(panel)
    model = _model(panel)
    key = (*_key(table), getattr(model, "id", ""))
    if st.get("key") != key or st.get("table") is not table:
        st.update(key=key, table=table, rows=rows(table, model))
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
        return pad.down(gamepad.ALL_BUTTONS[addr])
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
    # by the control, not its glyph: a Sony face calls the left stick L3 (plan 42)
    xa, ya = ("LX", "LY") if c.source == "pad:LSTICK" else ("RX", "RY")
    return 2 * lane(pad, xa) - 1, 1 - 2 * lane(pad, ya)


# ---------------------------------------------------------------- what a control says

def says(panel, c: gamepad.Control, b: Binding | None) -> str:
    """What a lit control does: its row's param in the panel's words
    (`ui_desk.text`), else the built-in meaning of a free axis
    (`BUILT_IN`), else "" — a dark control."""
    if b is not None and not _stick_quiet(panel, c.source):
        said = ui_desk.text(panel.reg, b)
        if b.scheme == PAIR_SCHEME:
            poles = pair_poles(":".join(b.parts))
            return f"{said} {'+' if poles and poles[0].source == c.source else '−'}"
        return said
    return built_in(panel, c.source)


def label(panel, c: gamepad.Control, b: Binding | None) -> str:
    """The hover: "LB · view.shape · Shape · pad LB", then how to change
    it; a free axis names the app's own hand on it, a dark control says
    it is free."""
    said = says(panel, c, b)
    learn = "right-click a param → Learn pad, then press it here"
    other = gamepad.paired_with(c.source, gamepad.shown_model(getattr(panel, "pad", None)))
    if other is not None:             # plan 56: one degree of freedom with its partner
        learn += f"\none axis with {gamepad.glyph(other) or other}: right-click a param → Learn pair"
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


def _lanes(pad, which: str) -> dict[str, float]:
    """A pad's touch or motion lanes by name ({} with none)."""
    read = getattr(pad, f"{which}_lanes", None) if pad is not None else None
    got = read() if read is not None else None
    names = gamepad.gesture.TOUCH_LANES if which == "touch" else gamepad.gesture.MOTION_LANES
    return dict(zip(names, got, strict=True)) if got is not None else {}


def _touchpad(dl, pad, c: gamepad.Control, x0: float, y0: float, x1: float, y1: float,
              edge: int, on: bool) -> None:
    """The touchpad: its face (red while clicked) and each finger on it,
    where it is (plan 42)."""
    down = held(pad, c)
    face = ui.u32(ui.RED) if down else ui.u32(_OFF if on else _DARK)
    dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 4.0)
    dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 4.0)
    t = _lanes(pad, "touch")
    r = max(2.5, 0.18 * (y1 - y0))
    for xs, ys in (("x", "y"), ("x2", "y2")):
        x, y = t.get(xs), t.get(ys)
        if x is None or y is None or not (math.isfinite(x) and math.isfinite(y)):
            continue
        dl.add_circle_filled(_v(x0 + x * (x1 - x0), y0 + (1 - y) * (y1 - y0)), r,
                             ui.u32(_BLACK if down else ui.RED))


def _tilt(dl, pad, cx: float, cy: float, r: float, edge: int, on: bool) -> None:
    """The tilt bubble: a well with a dot where the pad leans — right
    side down to the right, the far edge up upward — its ring red on a
    shake (plan 42)."""
    m = _lanes(pad, "motion")
    dl.add_circle_filled(_v(cx, cy), r, ui.u32(_WELL))
    ring = ui.u32(ui.RED) if m.get("shake") else edge
    dl.add_circle(_v(cx, cy), r, ring, 0, 2.0 if m.get("shake") else 1.0)
    dl.add_line(_v(cx - r, cy), _v(cx + r, cy), edge, 1.0)
    dl.add_line(_v(cx, cy - r), _v(cx, cy + r), edge, 1.0)
    if not m:
        return
    dx = 2 * m["roll"] - 1
    dy = 1 - 2 * m["pitch"]
    knob = max(3.0, r * 0.22)
    col = ui.u32(ui.RED) if on else ui.u32(ui.DIM)
    dl.add_circle_filled(_v(cx + dx * (r - knob), cy + dy * (r - knob)), knob, col)


def _draw(panel, dl, pad, c: gamepad.Control, b: Binding | None, said: str,
          x0: float, y0: float, x1: float, y1: float) -> None:
    """One control at the small size: its glyph on its face."""
    on = bool(said)
    down = held(pad, c)
    edge = ui.u32(ui.DIM if on else ui.LINE)
    ink = ui.u32(ui.TEXT if on else ui.FAINT)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if c.kind == "touchpad":
        _touchpad(dl, pad, c, x0, y0, x1, y1, edge, on)
        ui_desk._text(dl, c.glyph, cx, cy, ink, x1 - x0 - 2)
        return
    if c.kind == "tilt":
        r = min((x1 - x0) / 2, (y1 - y0) / 2) - 1
        _tilt(dl, pad, cx, y0 + r + 1, r, edge, on)
        ui_desk._text(dl, c.glyph, cx, y1 - 5, ink, x1 - x0)
        return
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
    if c.kind == "touchpad":
        _touchpad(dl, pad, c, x0, y0, x1, y1, edge, on)
        dl.add_text(_v(x0 + 3, y0 + 1), small, c.glyph)
        return ui_desk._Job(said, x0 + gsz.x + 7, y0, x1 - 3, y1, 1, ink, "mid") if on else None
    if c.kind == "tilt":
        lines = ui_desk.LABEL_LINES
        r = max(4.0, min((y1 - y0 - lines * lh - 4) / 2, 0.42 * (x1 - x0)))
        dl.add_text(_v(x0 + 1, y0), small, c.glyph)
        _tilt(dl, pad, cx, y0 + r + 1, r, edge, on)
        return ui_desk._Job(said, x0 + 1, y0 + 2 * r + 4, x1 - 1, y1, lines, ink,
                            "top") if on else None
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
    ui_pad_nvg.sweep(panel, imgui.get_frame_count())   # each frame: quiet rooms let go
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
    table = _table(panel)
    if view_of(panel) == "lanes" and table is not None:   # every lane, readable: as tall as that takes
        h = max(h, ui_pad_views.lanes_height(w - 2 * PAD, _pad(panel) or getattr(panel, "pad", None),
                                             _says_of(panel, table)) + 2 * PAD + HEAD_H)
    imgui.push_style_var(imgui.StyleVar_.window_padding, _v(PAD, PAD))
    if imgui.begin_child("##pad.inline", _v(w, h), imgui.ChildFlags_.borders
                         | imgui.ChildFlags_.always_use_window_padding,
                         imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse):
        _body(panel, table)
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
    if source in ("hid", "tape"):
        model = getattr(getattr(pad, "model", None), "name", "") or "pad"
        link = getattr(pad, "link", "") or source
        bat = getattr(getattr(pad, "report", None), "battery", -1)
        battery = f", battery {min(100, bat * 10)} %" if isinstance(bat, int) and bat >= 0 else ""
        word = "tape" if source == "tape" else link
        return word, (f"{model} over {link}{battery} — read over hidapi (pads/hid.py): the "
                      "touchpad, the motion sensors and, on an Edge, the back and Fn buttons"
                      + (", played from a recording" if source == "tape" else "") + ".")
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
    light = getattr(getattr(_pad(panel), "effects", None), "light", None)
    if light is not None and _pad(panel).has("light"):
        imgui.same_line()
        p = imgui.get_cursor_screen_pos()
        side = HEAD_H * 0.55
        imgui.get_window_draw_list().add_rect_filled(
            _v(p.x, p.y + (HEAD_H - side) / 2 - 2), _v(p.x + side, p.y + (HEAD_H + side) / 2 - 2),
            ui.u32(imgui.ImVec4(*(c / 255 for c in light), 1.0)), 2.0)
        imgui.dummy(_v(side, 1))
        if imgui.is_item_hovered():
            ui.tooltip("The light bar now: its identity colour, or what a sink row sends "
                       "(right-click a param → Learn sink ▸ light bar hue).")
    imgui.same_line()
    view = view_of(panel)
    ui._micro(f"{view} ▸", ui.TEXT)
    if imgui.is_item_hovered():
        ui.tooltip(ui_pad_views.VIEW_TIP)
        if imgui.is_mouse_clicked(imgui.MouseButton_.left):
            step_view(panel)
    _totem(panel)
    _poi(panel)
    if table is not None:
        imgui.same_line()
        n = len(rows_cached(panel, table))
        room = imgui.get_content_region_avail().x       # narrow in GRAPH's side panel
        said = next((w for w in (f"{n} mapped", str(n)) if imgui.calc_text_size(w).x <= room), "")
        if said:
            imgui.text_colored(ui.DIM, said)
            if imgui.is_item_hovered():
                ui.tooltip(f"{n} controls with a row in bindings.json. A grey label is the "
                           "app's own hand on a free axis, not a row.")
    imgui.set_cursor_pos(start)          # the line is HEAD_H tall whatever is on it
    imgui.dummy(_v(1, HEAD_H - imgui.get_style().item_spacing.y))


def totem_word(reg) -> tuple[str, str] | None:
    """The totem's word for the header (plan 47, an experiment): "totem
    off", or the three live planes (``totem YZ · XZ · ZW``); None with no
    totem in the registry. The hover is the button map."""
    state = getattr(reg, "totem", None)
    if state is None or "totem.on" not in reg:
        return None
    from . import totem
    tip = ("The Joy-Con as a 4D totem (plan 47, an experiment) — click to switch it "
           f"{'off' if state.on else 'on'}. Its gyro turns three planes, one per axis "
           "(x → YZ, y → XZ, z → XY); X / Y / B throw x / y / z into W (XW, YW, ZW); "
           "A (or ↓; a Joy-Con's − or +) resets the shape to the world's axes from where the pad is; the "
           "tilt moves the shape.")
    if not state.on:
        return "totem off", tip
    word = f"totem {totem.readout(state)}"
    if totem.reading(state) is None:       # none taken, or its device gone (LOST_S)
        word += " (no pad)"
    return word, tip + (f" Last: {state.note}." if state.note else "")


def _totem(panel) -> None:
    """The totem's word in the header, after the view's; a click switches it."""
    reg = getattr(panel, "reg", None)
    said = totem_word(reg) if reg is not None else None
    if said is None:
        return
    word, tip = said
    imgui.same_line()
    on = bool(reg["totem.on"].value)
    ui._micro(word, ui.RED if on else ui.DIM)
    if imgui.is_item_hovered():
        ui.tooltip(tip)
        if imgui.is_mouse_clicked(imgui.MouseButton_.left):
            reg["totem.on"].set(not on)


def poi_word(reg) -> tuple[str, str] | None:
    """The poi's word for the header (plan 47, the poi): "poi off", or its
    dials (``poi 1.00 · 0.30 · 0.20``: length, weight, springiness); None
    with no poi in the registry."""
    state = getattr(reg, "poi", None)
    if state is None or "poi.on" not in reg:
        return None
    from . import poi
    tip = ("The Joy-Con as the handle of a poi (plan 47, an experiment) — click to "
           f"switch it {'off' if state.on else 'on'}. The shape is the weight on the "
           "string: swing the pad and it flies round. Length · weight · springiness; "
           "its dials are in the Poi window (\"dials\" beside this) while it is on. "
           "A (or ↓) resets.")
    if not state.on:
        return "poi off", tip
    word = f"poi {poi.readout(state)}"
    if state.driving is None:
        word += " (no pad)"
    return word, tip + (f" Last: {state.note}." if state.note else "")


def _poi(panel) -> None:
    """The poi's word in the header, after the totem's; a click switches it."""
    reg = getattr(panel, "reg", None)
    said = poi_word(reg) if reg is not None else None
    if said is None:
        return
    word, tip = said
    imgui.same_line()
    on = bool(reg["poi.on"].value)
    ui._micro(word, ui.RED if on else ui.DIM)
    if imgui.is_item_hovered():
        ui.tooltip(tip)
        if imgui.is_mouse_clicked(imgui.MouseButton_.left):
            reg["poi.on"].set(not on)
    if on:
        _poi_dials_word(panel, reg)


POI_DIALS = ("length", "weight", "spring", "gravity", "drag", "hand")
POI_W = 300.0                       # the Poi window's width on first use


def _poi_dials_word(panel, reg) -> None:
    """After the poi's word while it is on: "dials", a click shows or hides
    the Poi window (`poi_window`)."""
    imgui.same_line()
    shown = bool(getattr(panel, "poi_dials", True))
    ui._micro("dials", ui.TEXT if shown else ui.DIM)
    if imgui.is_item_hovered():
        ui.tooltip(f"The poi's dials in their own window — click to {'hide' if shown else 'show'} "
                   "it. Length, weight, springiness, gravity, drag, the hand's push; the "
                   "depth and string switches; reset.")
        if imgui.is_mouse_clicked(imgui.MouseButton_.left):
            panel.poi_dials = not shown


def poi_window(panel) -> None:
    """The Poi window, while the poi is on and its "dials" word has not hidden
    it: the six dials (`POI_DIALS`), the depth and string switches and reset.
    A top-level window of its own, movable, so the pad window's room stays the
    pad's — drawn each frame beside the pad window (Panel._draw), whether the
    header that shows it is the floating pad's or GRAPH's side pane's. It
    keeps in front of the panel, as the alert banner does, but never of an
    open popup (a slider's Learn menu). Shown again each time the poi comes
    on (`panel._poi_was_on`)."""
    reg = getattr(panel, "reg", None)
    state = getattr(reg, "poi", None) if reg is not None else None
    on = state is not None and "poi.on" in reg and bool(reg["poi.on"].value)
    if on and not getattr(panel, "_poi_was_on", False):
        panel.poi_dials = True
    panel._poi_was_on = on
    if not on or not getattr(panel, "poi_dials", True) or "poi.length" not in reg:
        return
    io = imgui.get_io()
    imgui.set_next_window_pos(_v(io.display_size.x / 2, EDGE), imgui.Cond_.first_use_ever,
                              _v(0.5, 0.0))
    imgui.set_next_window_size(_v(POI_W, 0), imgui.Cond_.first_use_ever)
    opened, shown = imgui.begin("Poi", True, imgui.WindowFlags_.no_focus_on_appearing
                                | imgui.WindowFlags_.no_collapse)
    try:
        if not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id):
            try:
                imgui.internal.bring_window_to_display_front(imgui.internal.get_current_window())
            except Exception:  # noqa: BLE001, S110 — an imgui without the internal call
                pass
        if opened:
            for key in POI_DIALS:
                panel.half(f"poi.{key}", label=key)
            panel._check("poi.depth", "depth zooms")
            if "poi.guide" in reg:
                imgui.same_line()
                panel._check("poi.guide", "show string")
            if "poi.reset" in reg:
                panel._button("poi.reset", "reset")
    finally:
        imgui.end()
    if not shown:
        panel.poi_dials = False


def _says_of(panel, table):
    """`says(source)` for a view: (the words, the row) — a row's param in
    the panel's words, else an axis's built-in meaning, else nothing."""
    st = _state(panel)
    model = _model(panel)
    key = (*_key(table), getattr(model, "id", ""))
    if st.get("src_key") != key or st.get("src_table") is not table:
        st.update(src_key=key, src_table=table, src_rows=source_rows(table, model))
    rows_ = st["src_rows"]

    def says_(source: str) -> tuple[str, Binding | None]:
        b = rows_.get(source)
        if b is not None and not _stick_quiet(panel, source):
            return ui_desk.text(panel.reg, b), b
        return built_in(panel, source), None
    return says_


def _body(panel, table) -> None:
    _header(panel, table)
    if table is None:
        imgui.text_disabled("no table")
        return
    view = view_of(panel)
    if view != "map":          # plan 42's readouts: the room is the map's, so the desk keeps
        origin = imgui.get_cursor_screen_pos()
        avail = imgui.get_content_region_avail()
        ui_pad_views.draw(
            view, panel, imgui.get_window_draw_list(), origin.x, origin.y, avail.x, avail.y,
            _pad(panel) or getattr(panel, "pad", None), _says_of(panel, table))
        imgui.dummy(avail)
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
        layout = gamepad.layout_for(gamepad.shown_model(getattr(panel, "pad", None)))
        st["layout"] = layout
        for c in layout:
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
