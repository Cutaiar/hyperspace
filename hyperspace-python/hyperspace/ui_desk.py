"""The APC40 drawn on screen (plan 14 WP7, decision 25 (a); plan 17 WP4).

**APC40-only** (plan 27 B2): with several MIDI desks listed, this draws
the first MIDI role's rows (`Bindings.active()` with no role) over
`apc40.LAYOUT` — the APC40 in every rig that lists it first. A second
desk (a `generic` profile) has no layout to draw; plan 29's generic
on-screen desk is what replaces this module for any profile.

A picture of the desk in the control window: every control of
`apc40.LAYOUT` at its place on the device, with its glyph — the same
glyph the ROUTING page prints first on a desk or session row and Learn
prints in its messages — so a row can be found on the device by looking.

**It takes the room it has** (`room`, plan 17 fork 1): the space left of
the panel, bottom-left, above the cheat sheet when that shows and under
the pad diagram when that is up (ui_pad.py); with the
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
a button's LED is filled when the device's would be (`routing.led_level`,
the rule midi.py lights by). A **bank pad** (clip rows 1, 4 and 5, plan 19
WP2) has three states, as on the device: the loaded preset's is green, a
slot that holds another preset is amber at half strength and reads that
preset's name, and an empty slot's is drawn as a dark control — its glyph
only, no label (`empty`); its hover still says what the pad is. The hover
names the control: glyph · param · its label · layer, and Akai's name.

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

**The offer** (plan 24 C3): while a mappable control is picked, the
empty ground of the right-hand section (`OFFER`, under the transport row)
lists the params this preset uses, ranked (`offer`, `learn.ranked`: what
its routes and macros move, what it set off the group default, the
effects and layers it has on, then what is already on the desk), and its
chip "all params ▾" opens every param, this preset's first and then a
menu per group — not the whole registry in one list. A click on one puts
the picked control there (`take`): `Learn.map_picked`, the same road the
page's click takes, which still works beside it.

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

from . import apc40, learn, ui, ui_routing
from .apc40 import GREEN, GREEN_BLINK, RED, RED_BLINK, YELLOW, YELLOW_BLINK
from .params import PERFORMANCE_GROUPS, Kind
from .routing import Binding, led_level

MIN_W = 300.0              # the window is never narrower, px
MIN_H = 120.0              # …or shorter (a control window with no room above the sheet)
LABEL_UNIT = 44.0          # a layout unit this wide or wider carries labels…
LABEL_UNIT_H = 32.0        # …if it is also this tall (a short, wide window: glyphs only)
EDGE = 12.0                # from the control window's edges, the panel and the sheet
PAD = 8.0
HEAD_H = 26.0              # the header's line: the layer, the preset, the chip
GLYPH_PX = 10.0            # the glyphs' type size
GAP = EDGE                 # from the cheat sheet
LABEL_PX = (11.0, 18.0)    # the labels' type size: 0.2 of a unit, kept in this range
LABEL_LINES = 2            # a label wraps to at most this many lines
BIG, PANEL = "big", "panel"    # the header's chip: hide the panel / bring it back
PICK_S = 20.0              # a picked control lets go by itself after this long with no click
PICK_MOVE = 12.0           # px the mouse must leave a pick's click by before a click can map
SAYS_S = 0.5               # how long the labels' texts are kept (a renamed preset shows by then)
LET_GO_TIP = "click to let go"     # the footer's picked line: on it where it fits, and on hover
# The offer (plan 24 C3): where the picked control's list of this preset's
# params is drawn, in layout units (x, y, w, h) — the right-hand section's
# empty ground between the transport row and the crossfader, so it covers
# no control and the desk's own layout never moves while a pick stands
OFFER = (apc40.RIGHT, 10.45, 4.0, 2.95)
OFFER_ALL = "all params ▾"          # its chip: every param, this preset's first, then by group
OFFER_SHORT = "all ▾"               # …where the long label does not fit beside the head
OFFER_PAD = (4.0, 3.0)              # its inner padding, px
OFFER_SPACING = (4.0, 1.0)          # …and its items' spacing: three items fit on the small desk
OFFER_CHIP_PAD = (5.0, 0.0)         # the chip's padding: one text line tall

# LED colours by the grid velocity (apc40's table); any other lit button red
_LED = {GREEN: (0.30, 0.85, 0.40), GREEN_BLINK: (0.30, 0.85, 0.40),
        RED: (1.0, 43 / 255, 43 / 255), RED_BLINK: (1.0, 43 / 255, 43 / 255),
        YELLOW: (0.95, 0.80, 0.25), YELLOW_BLINK: (0.95, 0.80, 0.25)}
_ON = (1.0, 43 / 255, 43 / 255)
FILLED = 0.5               # a "filled, not selected" pad: its colour at this strength
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
    why = learn.blocked(table, c.source)        # the rule `learn_control` refuses by
    if why == "invariant":
        return f"{name} is invariant (the session's)"
    if why == "global":
        return (f"{name} is on the global layer (the session's) — latch SHIFT off to map "
                "into the preset")
    return None


def picked(panel) -> apc40.Control | None:
    """The picked control (`Learn.control`), or None."""
    source = getattr(getattr(panel, "learn", None), "control", None)
    cs = apc40.controls(source) if source else []
    return cs[0] if cs else None


def _stamp(panel, source: str, now: float | None = None, frame: int = -1,
           pos: tuple[float, float] | None = None) -> dict:
    """The pick's own state: when the count last started (`at`), the
    frame of the click that made it and where that click was (`pos`,
    until the mouse has left it: `armed`), whether the footer has shown
    it yet (`foot`)."""
    now = time.monotonic() if now is None else now
    pk = _state(panel)["pick"] = {"source": source, "at": now, "frame": frame, "pos": pos,
                                  "foot": False}
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


def first_sight(panel) -> bool:
    """True once per pick, the first time the footer asks: whatever line
    the slot held then was said before the pick (or while the panel was
    hidden) and gives way to it; a line said later shows first."""
    pk = _state(panel).get("pick")
    if pk is None or pk.get("foot"):
        return False
    pk["foot"] = True
    return True


def armed(panel) -> bool:
    """May a click on a param map the picked control yet? Not until the
    mouse has left the spot of the click that picked it (`PICK_MOVE`): on
    the big desk that click brings the panel back under the mouse, and a
    second click there — a double click, or "click it again to let go" —
    must not land on whatever widget is now under it. The page is dimmed
    meanwhile all the same (`picking`), so that click does nothing at all."""
    pk = _state(panel).get("pick")
    if pk is None:
        return False
    pos = pk.get("pos")
    if pos is None:
        return True
    m = imgui.get_mouse_pos()
    if math.hypot(m.x - pos[0], m.y - pos[1]) < PICK_MOVE:
        return False
    pk["pos"] = None
    return True


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
    of the click that made it (that click is not a param's; nor is one
    more at the same spot: `armed`)."""
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
        if panel.open and ui.PAGE_KEYS[panel.page] == "routing":
            # ROUTING is never dimmed: a click there is the widget's own
            return (f"{c.glyph} picked: its line is framed · on any other page, click a "
                    f"param to put it there · click {c.glyph} again to let go"), True
        return (f"{c.glyph} picked: click a param to put it here · click {c.glyph} again "
                "to let go"), True
    b = lit_cached(panel, table).get(c.glyph)
    does = ((text(panel.reg, b) or "an empty slot") if b is not None
            else f"unmapped on the {table.layer} layer")
    return f"{why}: {does}", False


def footer_line(panel, now: float | None = None) -> tuple[str, bool] | None:
    """The footer's picked line, with the seconds left: (words, whether a
    click on a param would map), None with nothing picked."""
    c, table = picked(panel), _table(panel)
    if c is None or table is None:
        return None
    line, can = pick_line(panel, table, c)
    secs = math.ceil(left(panel, now))
    if not can:
        return f"{line} ({secs} s)", False
    if ui.PAGE_KEYS[panel.page] == "routing":
        return f"{c.glyph} picked ({secs} s): click a param on any other page", True
    return f"{c.glyph} picked ({secs} s): click a param to put it here", True


def offer(panel, table) -> tuple[list[tuple[str, str]], list[tuple[str, list[str]]]]:
    """What a picked control is offered (plan 24 C3): `learn.ranked` over
    every param a desk control may take (`ui_routing.desk_target`) — this
    preset's own first, ranked, then the rest by group. Built from the
    registry, the table and the library's group defaults, and kept while
    the pick, the table and the loaded preset stand."""
    st = _state(panel)
    lib = getattr(panel, "library", None)
    key = (getattr(getattr(panel, "learn", None), "control", None), _key(table),
           getattr(table, "macros_serial", 0),
           lib.current("presets") if lib is not None else None)
    hit = st.get("offer")
    if hit is not None and hit[0] == key:
        return hit[1]
    reg = panel.reg
    params = [(p.id, p.group) for p in reg if ui_routing.desk_target(p)]
    values = reg.snapshot()
    defaults: dict = {}
    if lib is not None and lib.reg is not None:
        for g in PERFORMANCE_GROUPS:
            defaults.update(lib.defaults(g))
    routed = {b.target for b in table.routes() if b.enabled}
    routed |= {s.base for m in table.macros.values() for s in m.subs if s.base}
    on_desk = {b.target for b in table.desk() if b.enabled}
    out = learn.ranked(params, values, defaults, routed, on_desk)
    st["offer"] = (key, out)
    return out


def take(panel, pid: str) -> bool:
    """The offer's item `pid` clicked: the picked control goes on it —
    `Learn.map_picked`, the one road a click on a param's widget takes."""
    lrn = getattr(panel, "learn", None)
    if lrn is None or getattr(lrn, "control", None) is None:
        return False
    return lrn.map_picked(pid, apc40)


def _offer_item(panel, pid: str, why: str, width: float) -> None:
    p = panel.reg.get(pid)
    name = (p.label if p is not None and p.label else pid)
    if imgui.selectable(f"{ui.fit_text(name, max(0.0, width))}##offer.{pid}", False)[0]:
        take(panel, pid)
    lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    _state(panel).setdefault("offer_rects", {})[pid] = (lo.x, lo.y, hi.x, hi.y)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"put {getattr(picked(panel), 'glyph', '')} on {name}\n{pid} · {why}")


def _offer_all(panel, used, rest) -> None:
    """The chip's popup: this preset's params, then every other param a
    menu per group."""
    if not imgui.begin_popup("##offer_all"):
        return
    ui._micro("this preset", ui.DIM)
    if not used:
        imgui.text_disabled("nothing it moves, routes or switches on")
    for pid, why in used:
        p = panel.reg.get(pid)
        if imgui.menu_item_simple(f"{p.label if p is not None else pid}   ({why})##all.{pid}"):
            take(panel, pid)
    imgui.separator()
    for group, ids in rest:
        if imgui.begin_menu(f"{group}##all.{group}"):
            for pid in ids:
                p = panel.reg.get(pid)
                if imgui.menu_item_simple(f"{p.label if p is not None else pid}##all.{pid}"):
                    take(panel, pid)
            imgui.end_menu()
    imgui.end_popup()


def _offer(panel, table, origin, unit) -> None:
    """The picked control's offer, in the `OFFER` ground: a chip that
    opens every param, then this preset's params, ranked (`offer`); a
    click on one maps the pick there. Drawn only while a click on a param
    would map it (`picking`)."""
    st = _state(panel)
    for k in ("offer_rects", "offer_box", "offer_chip"):
        st.pop(k, None)
    c = picking(panel)
    if c is None:
        return
    used, rest = offer(panel, table)
    (ox, oy), (sx, sy) = origin, unit
    x, y, w, h = OFFER
    imgui.set_cursor_screen_pos(_v(ox + x * sx, oy + y * sy))
    size = _v(w * sx, h * sy)
    st["offer_drawn"] = [pid for pid, _why in used]
    # compact inside: the small desk gives it about 107 × 79 px at the
    # default control size, which must hold the head and three items
    imgui.push_style_var(imgui.StyleVar_.window_padding, _v(*OFFER_PAD))
    shown = imgui.begin_child("##offer", size, imgui.ChildFlags_.borders)
    imgui.pop_style_var()
    if not shown:
        imgui.end_child()
        return
    lo = imgui.get_window_pos()
    st["offer_box"] = (lo.x, lo.y, lo.x + size.x, lo.y + size.y)
    imgui.push_font(ui._FONTS["ui"], LABEL_PX[0] if sx < LABEL_UNIT else label_px(sx))
    imgui.push_style_var(imgui.StyleVar_.item_spacing, _v(*OFFER_SPACING))
    try:
        ui._micro(f"{c.glyph} on", ui.RED)
        _offer_chip(panel)
        _offer_all(panel, used, rest)
        room_ = imgui.get_content_region_avail().x
        if not used:
            imgui.text_disabled(ui.fit_text("nothing of this preset's", room_))
        for pid, why in used:
            _offer_item(panel, pid, why, room_)
    finally:
        imgui.pop_style_var()
        imgui.pop_font()
        imgui.end_child()


def _chip_width(label: str) -> float:
    return imgui.calc_text_size(label.split("##")[0]).x + 2 * OFFER_CHIP_PAD[0]


def _offer_chip(panel) -> None:
    """The head's chip, beside "D5 ON" when it fits there: the long label,
    else the short one, else the short one on a line of its own — never
    wider than the room it is drawn in."""
    after = imgui.get_item_rect_max().x + imgui.get_style().item_spacing.x
    right = imgui.get_window_pos().x + imgui.get_window_width() - OFFER_PAD[0]
    label = next((lb for lb in (OFFER_ALL, OFFER_SHORT) if after + _chip_width(lb) <= right),
                 None)
    if label is not None:
        imgui.same_line()
    else:
        label = OFFER_SHORT
    imgui.push_style_var(imgui.StyleVar_.frame_padding, _v(*OFFER_CHIP_PAD))
    imgui.push_style_var(imgui.StyleVar_.frame_rounding, 999.0)
    hit = imgui.button(f"{label}##offer")
    imgui.pop_style_var(2)
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    _state(panel)["offer_chip"] = (a.x, a.y, b.x, b.y)
    if hit:
        imgui.open_popup("##offer_all")
    if imgui.is_item_hovered():
        imgui.set_tooltip("Every param: this preset's first, then the rest by group")


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
    m = imgui.get_mouse_pos()
    _stamp(panel, c.source, frame=imgui.get_frame_count(), pos=(m.x, m.y))
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
         sheet: tuple[float, float] | None,
         pad_h: float = 0.0) -> tuple[float, float, float, float]:
    """(x, y, w, h) of the desk window. `panel_x`: the panel's left edge,
    None while it is hidden. `sheet`: the cheat sheet's (w, h), None
    while it is off. `pad_h`: the height of the pad diagram over it
    (ui_pad.py), 0 while that is off.

    Bottom-left, `EDGE` from the window's edges. Its right edge is `EDGE`
    left of the panel, or of the window's right edge with the panel
    hidden; never narrower than `MIN_W`. The cheat sheet, when on: with
    the panel open the desk sits above it; with the panel hidden, beside
    it, full height. As tall as there is room for — under the pad
    diagram, when that is up — capped so a layout unit is never taller
    than it is wide."""
    dw, dh = display
    x, bottom = EDGE, dh - EDGE
    top = EDGE + (pad_h + GAP if pad_h else 0.0)
    right = (dw if panel_x is None else panel_x) - EDGE
    if sheet is not None:
        if panel_x is None:
            x += sheet[0] + GAP
        else:
            bottom -= sheet[1] + GAP
    w = max(MIN_W, right - x)
    unit = (w - 2 * PAD) / apc40.LAYOUT_W
    h = max(MIN_H, min(bottom - top, unit * apc40.LAYOUT_H + 2 * PAD + HEAD_H))
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
    # the pad diagram sits at the top of the same column, and is drawn
    # before this (ui.Panel._draw), so its height is this frame's
    pad_h = getattr(panel, "_pad_h", 0.0) if getattr(panel, "pad_diagram", False) else 0.0
    return room(display, panel_x, sheet, pad_h)


# ---------------------------------------------------------------- what a control says

# What a few targets do, where their label alone does not say it on the
# desk (the owner's findings, 2026-10-16): MASTER select and PAN only
# matter in overlay mode, which config.toml's [output] overlay must allow;
# STOP ALL resets the bands to the selected scene and a second press within
# 8 s undoes it; QUANT walks the bank, not the preset list (the pad's B)
DESK_WORDS = {
    "overlay.on": "Overlay (if config allows)",
    "overlay.passthrough": "Click-through (overlay)",
    "scene.reset_all": "Reset all bands (again: undo)",
    "preset.next": "Next bank preset",
}
# an enum `set` row whose choice's name alone does not say what the
# button does: the word goes before the name (the track-select row, G7:
# "band SUB" — the band strip the device knobs follow under SHIFT)
SET_WORDS = {"band.select": "band"}


def text(reg, b: Binding) -> str:
    """What a lit control does, in the panel's words (plan 17 fork 8): a
    `set` row on an enum → that value's name (the bank row reads the
    presets' names, a scene pad the scene's; `SET_WORDS` puts a word
    before it — "band SUB"); a `step` row → the label and the step
    ("Brightness +3"); a toggle row on an enum, which steps it → the
    label, the value now and "next" ("SUB Transfer: SQ · next"); a target
    in `DESK_WORDS` → its words; anything else → the param's label; a
    target the registry lacks (or a param with no label) → the id. A bank
    pad whose slot is empty says nothing (`empty`): "" — it is drawn as a
    dark control."""
    p = reg.get(b.target)
    if p is None:
        return b.target
    if b.op == "set" and p.kind is Kind.ENUM:
        if empty(reg, b):
            return ""
        names = p.names
        i = round(b.value)
        if 0 <= i < len(names) and names[i]:
            word = SET_WORDS.get(b.target)
            return f"{word} {names[i]}" if word else str(names[i])
    if b.op == "toggle" and p.kind is Kind.ENUM:
        return f"{p.label or b.target}: {p.text()} · next"
    if b.target in DESK_WORDS:
        return DESK_WORDS[b.target]
    if b.op == "step":
        return f"{p.label or b.target} {b.value:+g}"
    return p.label or b.target


def empty(reg, b: Binding | None) -> bool:
    """Is this a `set` row on an enum that says which of its choices hold
    something (`Param.has`: the bank's `preset.select`), on a choice that
    holds nothing — a bank pad whose slot is empty? Such a pad is dark on
    the device (D8) and pressing it only says the slot is empty."""
    p = reg.get(b.target) if b is not None else None
    has = getattr(p, "has", None)
    if p is None or has is None or b.op != "set" or p.kind is not Kind.ENUM:
        return False
    try:
        return not has(round(b.value))
    except (TypeError, ValueError):
        return False


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


# (text, width, lines, px) → (wrap()'s rows, each row's width, whether it was cut): measured once
_WRAPS: dict[tuple, tuple[list[str], list[float], bool]] = {}


def _wrapped(text: str, width: float, lines: int, px: float
             ) -> tuple[list[str], list[float], bool]:
    key = (text, round(width), lines, round(px, 1))
    hit = _WRAPS.get(key)
    if hit is None:
        if len(_WRAPS) > 4000:          # preset names come and go; never grows without end
            _WRAPS.clear()
        rows = wrap(text, width, lines)
        hit = _WRAPS[key] = (rows, [imgui.calc_text_size(r).x for r in rows],
                             is_cut(text, rows))
    return hit


def _says(panel, table, shown: dict[str, Binding]) -> dict[str, str]:
    """{glyph: `text`} for the lit controls, kept while the lit map stands
    and for at most `SAYS_S` (an enum's names are asked of the app — the
    bank's are its presets' — and can change under a row that did not)."""
    st = _state(panel)
    now = time.monotonic()
    hit = st.get("says")
    if hit is None or hit[0] is not shown or not 0 <= now - hit[1] < SAYS_S:
        hit = st["says"] = (shown, now, {g: text(panel.reg, b) for g, b in shown.items()})
    return hit[2]


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
    if reg is not None and empty(reg, b):
        says = f"slot {round(b.value) + 1}: empty"
    mid = b.target if says == b.target else f"{b.target} · {says}"
    return f"{c.glyph} · {mid} · {_layer_word(table, b)}\n{c.name}"


def _preset_name(panel) -> str:
    pr = ui_routing._presets(panel)
    cur = getattr(pr, "current", None) if pr is not None else None
    return cur or "no preset"


def _led(panel, b: Binding) -> tuple[float, float, float] | None:
    """The colour the device's LED shows for a lit button row, or None
    (off). A row at level 1 (`routing.led_level`: a bank pad whose slot
    holds a preset that is not the loaded one) shows the profile's
    "filled" colour — amber on the clip grid — at `FILLED` strength."""
    p = panel.reg.get(b.target)
    if p is None or b.feedback != "led":
        return None
    try:
        level = led_level(b, p)
    except (TypeError, ValueError):
        return None
    if not level:
        return None
    if level == 1:
        filled = apc40.filled_of(b.number, int(b.on)) if b.kind == "note" else None
        rgb = _LED.get(filled) if filled is not None else None
        return None if rgb is None else tuple(FILLED * x for x in rgb)
    # the clip grid shows the row's colour (green, red, yellow); every
    # other button's LED is a plain on, drawn in the panel's red
    grid = b.kind == "note" and b.number in apc40.N_CLIP
    return _LED.get(int(b.on), _ON) if grid else _ON


def _bright(led) -> bool:
    """Is a face this colour bright enough to want black ink (a lit LED;
    a "filled" one at `FILLED` strength keeps the light inks)?"""
    return led is not None and max(led) > 0.7


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
    on = b is not None and not empty(panel.reg, b)     # an empty bank slot's pad is dark
    edge = ui.u32(ui.DIM if on else ui.LINE)
    ink = ui.u32(ui.TEXT if on else ui.FAINT)
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if c.kind in ("grid", "button"):
        led = _face(panel, table, c, b)
        face = _col(led, 0.9) if led else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 2.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 2.0)
        _text(dl, c.glyph, cx, cy, ui.u32(_BLACK) if _bright(led) else ink, w - 2)
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
              x0: float, y0: float, x1: float, y1: float, lh: float, says: str) -> _Job | None:
    """One control at the labelled size: its face, its glyph small in the
    top-left corner, and — returned, for the label pass, which draws in
    the labels' type — the room its label has. `lh` is a label line's
    height. A dark control gets no label (D8), and an empty bank slot's
    pad is drawn as one (`empty`)."""
    on = b is not None and not empty(panel.reg, b)
    edge = ui.u32(ui.DIM if on else ui.LINE)
    small = ui.u32(ui.DIM if on else ui.FAINT)          # the glyph: small and dim
    # whose row it is: the up layer's in the bright ink, an invariant one grey
    ink = ui.u32(ui.TEXT if on and b.layer is not None else ui.DIM)
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    gsz = imgui.calc_text_size(c.glyph)
    if c.kind in ("grid", "button"):
        led = _face(panel, table, c, b)
        face = _col(led, 0.9) if led else ui.u32(_OFF if on else _DARK)
        dl.add_rect_filled(_v(x0, y0), _v(x1, y1), face, 3.0)
        dl.add_rect(_v(x0, y0), _v(x1, y1), edge, 3.0)
        if _bright(led):
            small = ui.u32(_BLACK)
            ink = ui.u32(_BLACK if b.layer is not None else _ON_LED)
        elif led:                   # filled, not selected: the name in the bright ink
            ink = ui.u32(ui.TEXT)
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
        rows, widths, cut = _wrapped(j.says, j.x1 - j.x0, lines, px)
        if not last and cut:
            small.append(j)
            continue
        y = j.y0 if j.how != "mid" else j.y0 + max(0.0, (j.y1 - j.y0 - len(rows) * lh) / 2)
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
    alone = False                   # the picked line has the header to itself
    if c is not None:
        line, can = pick_line(panel, table, c)
        line = f"{line} · {math.ceil(left(panel))} s"
        words = (ui._micro_width("apc40") + ui._micro_width(f"{table.layer} layer  ·  shift")
                 + imgui.calc_text_size(f"{_preset_name(panel)}").x + 40)
        alone = imgui.calc_text_size(line).x > end - start.x - words
    if alone:
        imgui.text_colored(ui.RED if can else ui.DIM, ui.fit_text(line, end - start.x))
        if imgui.is_item_hovered():
            imgui.set_tooltip(line)
    else:
        ui._micro("apc40")
    if alone:
        pass
    elif table is None:
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
    big = sx >= LABEL_UNIT and sy >= LABEL_UNIT_H
    px = label_px(sx)
    lh = round(px * 1.12)
    dl = imgui.get_window_draw_list()
    mouse = imgui.get_mouse_pos()
    hovered = imgui.is_window_hovered()
    tip = hit = frame = None
    source = getattr(getattr(panel, "learn", None), "control", None)
    jobs: list[tuple[apc40.Control, _Job]] = []
    says = _says(panel, table, shown) if big else {}
    imgui.push_font(ui._FONTS["ui"], GLYPH_PX if not big else max(GLYPH_PX, 0.16 * sx))
    try:
        st = _state(panel)
        st["origin"], st["unit"] = (origin.x, origin.y), (sx, sy)
        for c in apc40.LAYOUT:
            x0, y0, x1, y1 = rect(panel, c)
            b = shown.get(c.glyph)
            if big:
                job = _draw_big(panel, dl, table, c, b, x0, y0, x1, y1, lh,
                                says.get(c.glyph, ""))
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
    # the picked control's offer, over the empty ground it owns (`OFFER`):
    # a child window of this one, so the desk's own hover and clicks are
    # not this window's while the mouse is on it
    _offer(panel, table, (origin.x, origin.y), (sx, sy))
    if tip is not None:
        imgui.set_tooltip(tip)
    # the window is hit-tested: a left click on a control is `click`; on
    # the ground between the controls it lets the picked control go
    if hovered and imgui.is_mouse_clicked(0) and mouse.y >= origin.y:
        if hit is not None:
            click(panel, table, *hit)
        else:
            let_go(panel)
