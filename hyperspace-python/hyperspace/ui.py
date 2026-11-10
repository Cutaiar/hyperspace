"""imgui control surface — every widget is a view onto one registry Param.

Built to be read across a room (ENGINEERING.md, control-surface conventions): black ground, soft rounded
controls, a rounded sans for words and a semibold mono for numbers, white
text, red #ff2b2b as the only accent. A fader fills red up to its value so
where it sits reads at a glance.
The hint-readout system of the HTML is replaced by native tooltips.

Nothing here owns state. The panel draws params.Registry entries through a
handful of widget helpers (_fader, _slider, _combo, _check, _button) that
read the live value, draw, and write back through the Param, so a value
moved by a hotkey, the gamepad or a MIDI knob shows on the next frame with
no extra plumbing. Right-clicking any widget opens the binding menu: it
names the param id and offers Learn (the host's `learn.Learn`: a knob or a hand completes it) /
Unbind.

The surface is GRAPH, always drawn, with a side pane that shows one view
at a time (ui_pane.py, plan 49): the selection's details, or a section,
each a page's body, one per registry group or two, and a block in it
whose group the library knows carries its preset strip (ui_loadable.py)
under the title. `ui.page` is the view: what the pane's chips, a key row,
a pad or ⌘[ / ⌘] bring up (`PAGE_KEYS`, `Panel.go_page`). A modulated param
draws its *base* as the handle and a white ghost bar at the *effective*
value (params.py: `base` vs `eff_norm`), so the setting stays where the
user put it while a lane rides on top; its tooltip names the performer
(routing.py: the table's owner row). The layout — what sits where — is
the one hand-arranged thing left here.
"""

from __future__ import annotations

import math
import os
import time
from collections.abc import Callable
from typing import Any, cast

from imgui_bundle import imgui

from . import (
    apc40,
    devices,
    field,
    gamepad,
    graphview,
    learn,
    ui_bands,
    ui_browse,
    ui_camera,
    ui_desk,
    ui_displays,
    ui_feel,
    ui_fields,
    ui_graph,
    ui_kit,
    ui_lfo,
    ui_loadable,
    ui_lookback,
    ui_media,
    ui_pad,
    ui_pane,
    ui_patterns,
    ui_players,
    ui_playlist,
    ui_routing,
    ui_seq,
    ui_view,
    undo,
)
from . import players as players_mod
from .analyzer import N_MAX
from .audio import AudioEngine
from .bands import CEIL, KNEE
from .control import Control
from .geometry import SHAPES, geom, menu
from .graph import (
    ALL_OUTPUTS,
    EMPTY,
    GROUND,
    Wiring,
    bus_cuts_of,
    graph_words,
    hands_words,
    in_scene_hands,
    layer_words,
    output_placement_words,
    output_ports,
    through_layer,
    through_of,
    wire_words,
)
from .groupwords import group_title
from .hands import panel as ui_hands
from .media import publish
from .params import PLANES, Kind, Param, Registry, build_registry, dial_id, part_of
from .pointer import Through, deck_number
from .view import RED as RED_RGB
from .view import ViewState

# ---- palette: black ground, three greys of text, one red ----
RED = imgui.ImVec4(*RED_RGB, 1.0)     # the points' colour (view.RED): one red everywhere
TEXT = imgui.ImVec4(0.96, 0.96, 0.96, 1.0)      # values, names: what is read first
DIM = imgui.ImVec4(0.70, 0.70, 0.72, 1.0)       # labels and idle state, still legible
FAINT = imgui.ImVec4(0.58, 0.58, 0.61, 1.0)     # notes and hints, the quietest text
WARN = imgui.ImVec4(1, 0.45, 0.35, 1)
NOM = 1.0  # the meters' nominal line — a band working normally (the chain has no use for it)
FILL = imgui.ImVec4(1.0, 43 / 255, 43 / 255, 0.42)  # a fader's value fill
GHOST = imgui.ImVec4(1, 1, 1, 0.92)             # the effective value under modulation
LINE = imgui.ImVec4(0.24, 0.24, 0.26, 1.0)      # rules, frames, idle marks — the one grey line

# meter landmarks (ENGINEERING §4): nominal 38.5%, knee 48.1% of full scale
PIN_AT = CEIL * 0.92
PIN_HOLD = 0.5

# the panel: GRAPH and its side pane of sections (ui_pane.py), a footer
MESSAGE_S = 4.0  # how long the footer's message slot shows a line after it changes
CANCEL_TIP = "click to cancel"  # the footer's armed-learn line: on it where it fits, and on hover
PANEL_W = 540   # beside the left column the panel is never narrower (panel_w)
PANEL_EDGE = 12.0   # the panel's margin from the control window's edges (panel_rect)
COLUMN_MAX = 0.5    # the desk and pad column never takes more of the window than this (panel_w)
DESK_ASPECT = 4 / 3   # at launch the desk diagram left of the panel is this wide per unit of height
LABEL_W = 104    # the label column in a _row
HALF_LABEL_W = 78    # the label column in a half-width table cell (Panel.half)
SLIDER_MIN = 60.0   # a slider sharing a row in a narrow pane is never thinner
# the kit's fields (`ui_fields`): a slider's row (the 12 px thumb, its ring, and
# room to press); a switch's, a select's, a button's row (the panel's frame
# height); how far a detent's tick stands off the track, above and below
FIELD_SLIDER_H = 20.0
FIELD_ROW_H = 28.0
FIELD_NOTCH = 3.0
LABEL_GAP = 12   # px between a label cell's text room and its control (Panel._label_cell)
SCENE_COMBO_MIN = 100   # px; the analyzer's scene combo keeps this beside its label and Reset all
ROUND = 8.0      # corner radius of frames; chips and grabs go rounder
# the dirty dot (plan 19 WP5): a filled red disc 12 px across beside a
# loadable patch's name — where the "●" glyph left about 7 px of ink — and the
# side pane's chip dot, radius 5, on a section whose group has moved off its loadable patch
DOT_R = 6.0
HEADER_DOT_R = 5.0

# ---- font atlas (ENGINEERING.md, control-surface conventions) ----
# Four roles. UI for words (buttons, combos, names), MICRO for the
# uppercase field labels (tracking baked in via glyph_extra_advance_x —
# imgui has no letter-spacing), NUM for value readouts (monospaced, so a
# moving number does not jitter), BIG for the signature cell-count
# readout. With the 1.92 dynamic atlas each face renders at every size.
#
# The faces ship in hyperspace/fonts/ (its README: sources, licences), so
# the panel draws, and the tests measure, the same on every machine.
# Weight is what makes type read at a distance: Inter Medium for words,
# Bold for the small labels, JetBrains Mono SemiBold for numbers.

FONT_BASE = 16.0
FONT_MICRO = 12.5
TAG_GAP = 3.0       # px kept between two meter tags (`tag_px`)
# the sizes a tag may be, largest first: glyphs land on whole pixels, so width
# is not linear in size and each is measured. Past the last a tag is left out
TAG_SIZES = (FONT_MICRO, 11.0, 10.0)
FONT_NUM = 16.0
FONT_BIG = 52.0

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
# (path, face index) per role; the first that exists wins
_FONT_CANDIDATES = {
    "ui": [(os.path.join(_FONT_DIR, "Inter-Medium.ttf"), 0)],
    "micro": [(os.path.join(_FONT_DIR, "Inter-Bold.ttf"), 0)],
    "num": [(os.path.join(_FONT_DIR, "JetBrainsMono-SemiBold.ttf"), 0)],
}
# glyphs a face lacks (planet symbols, ⊂, ◌, ▾) come from these, merged in behind it
_FALLBACKS = [(os.path.join(_FONT_DIR, "DejaVuSans.ttf"), 0)]

_FONTS: dict[str, imgui.ImFont | None] = {"ui": None, "micro": None, "num": None}


def _add_font(role: str, size: float, tracking: float = 0.0) -> None:
    io = imgui.get_io()
    hit = next(((p, n) for p, n in _FONT_CANDIDATES[role] if os.path.exists(p)), None)
    if hit is None:
        return
    cfg = imgui.ImFontConfig()
    cfg.font_no = hit[1]
    cfg.glyph_extra_advance_x = tracking
    _FONTS[role] = io.fonts.add_font_from_file_ttf(hit[0], size, cfg)
    for path, no in _FALLBACKS:
        if os.path.exists(path) and path != hit[0]:
            m = imgui.ImFontConfig()
            m.merge_mode = True
            m.font_no = no
            io.fonts.add_font_from_file_ttf(path, size, m)


def panel_w(display: tuple[float, float], desk: bool = True, pad: bool = False) -> float:
    """The panel's width beside the left column in a control window of
    `display` (w, h). The column is as wide as what is up in it wants:
    the desk diagram a `DESK_ASPECT` slice of the window's height, the pad
    diagram its own width (`ui_pad.room`, far narrower), the wider of the
    two when both are up. Never more than `COLUMN_MAX` of the window, so
    the graph keeps room; the panel never under `PANEL_W` either, and a
    narrow window keeps the panel whole and the column takes what is left
    (ui_desk.room). On the default window (app.CONTROL_SIZE) the desk and
    the panel come out the same size."""
    from . import ui_pad  # (late: ui_pad imports this module)
    dw, dh = display
    want = 0.0
    if desk:
        want = DESK_ASPECT * (dh - 2 * PANEL_EDGE)
    if pad:
        want = max(want, ui_pad.room(display, None)[2])
    room = dw - 3 * PANEL_EDGE
    return float(int(max(PANEL_W, room - min(want, COLUMN_MAX * room))))


def panel_rect(display: tuple[float, float], desk: bool = False,
               pad: bool = False) -> tuple[float, float, float, float]:
    """(x, y, w, h) of CONTROLS in a control window of `display`: pinned,
    never dragged. With the left column up (the `desk` or the `pad`
    diagram) it is `panel_w` wide at the right; without, it fills the
    window. Both `PANEL_EDGE` from the window's edges, and never wider
    than the window allows: in a window too narrow for `PANEL_W` beside
    the column, the panel keeps the window and the column is under it
    (the graph is primary; nothing can drag it back into view)."""
    dw, dh = display
    full = dw - 2 * PANEL_EDGE
    w = min(panel_w(display, desk, pad), full) if desk or pad else full
    return float(int(dw - w - PANEL_EDGE)), PANEL_EDGE, float(int(w)), dh - 2 * PANEL_EDGE


def load_fonts() -> None:
    """Build the atlas; call once after create_context.

    A role with no candidate on disk stays None — push_font(None, size)
    keeps the current face and only changes size, so the imgui default
    face stands in and nothing else needs to care.
    """
    _add_font("ui", FONT_BASE)
    _add_font("micro", FONT_MICRO, tracking=1.1)   # ≈ .09em at the label size
    _add_font("num", FONT_NUM)
    if _FONTS["ui"] is not None:
        imgui.get_io().font_default = _FONTS["ui"]
    ui_kit.load_faces(imgui.get_io())      # the kit's, for the sections drawn on it


TIP_CH = 65   # a tooltip wraps at this many characters: a readable line (the owner, 2026-10-26)

# Shift-drag fine mode (wave 2 T2, register rows 607–608): while ⇧ is held a
# drag on a continuous slider or fader moves the value FINE as far as the
# mouse moves the grab; once ⇧ has been held in a drag, the rest of that
# drag is relative, so letting ⇧ go goes back to coarse without a jump.
FINE = 0.1
FINE_TIP = "FINE  ·  ⇧ held: a drag moves a tenth as far"


def tooltip(text: str) -> None:
    """A hover's words as a tooltip, wrapped at `TIP_CH` characters of the
    tooltip's face — where `imgui.set_tooltip` never wraps — and drawn as
    they are (set_tooltip reads its text as a format: a % went wrong)."""
    if imgui.begin_tooltip():
        imgui.push_text_wrap_pos(imgui.calc_text_size("0").x * TIP_CH)
        imgui.text_unformatted(text)
        imgui.pop_text_wrap_pos()
        imgui.end_tooltip()


def _micro(text: str, color: imgui.ImVec4 | None = None) -> None:
    """An uppercase field label in the tracked label face."""
    imgui.push_font(_FONTS["micro"], FONT_MICRO)
    imgui.text_colored(DIM if color is None else color, text.upper())
    imgui.pop_font()


def fit_micro(text: str, width: float, least: float = 12.0) -> str:
    """`text` as `_micro` draws it (upper case, the micro face), cut to
    `width` with an ellipsis; "" where the room is under `least` (plan 49
    stage 2: a note, a strip's head, a node's ports in the side pane)."""
    if width < least:
        return ""
    imgui.push_font(_FONTS["micro"], FONT_MICRO)
    try:
        return fit_text(text.upper(), width)
    finally:
        imgui.pop_font()


def _micro_width(text: str) -> float:
    """What _micro(text) will take, for right-aligning things beside it."""
    imgui.push_font(_FONTS["micro"], FONT_MICRO)
    w = imgui.calc_text_size(text.upper()).x
    imgui.pop_font()
    return w


def _readout(text: str, color: imgui.ImVec4 | None = None) -> None:
    """A value in the readout face: semibold, monospaced, white."""
    imgui.push_font(_FONTS["num"], FONT_NUM)
    imgui.text_colored(TEXT if color is None else color, text)
    imgui.pop_font()


def _readout_width(text: str) -> float:
    imgui.push_font(_FONTS["num"], FONT_NUM)
    w = imgui.calc_text_size(text).x
    imgui.pop_font()
    return w


def u32(c: imgui.ImVec4) -> int:
    return imgui.color_convert_float4_to_u32(c)


# ---- chips: the small rounded buttons the strips and rows are made of ----

CHIP_PAD = imgui.ImVec2(10, 3)


def chip(label: str, size: imgui.ImVec2 | None = None, **kit) -> bool:
    """A compact pill button — small_button, with room to breathe. `kit`:
    what the kit's chip can do besides (`ui_fields.chip`: an icon, a
    variant, a reveal); the stock chip draws its words and ignores them."""
    if ui_kit.ready():                  # on the kit (hyperspace/dkit): the same size and id
        return ui_fields.chip(label, size, **kit)
    imgui.push_style_var(imgui.StyleVar_.frame_padding, CHIP_PAD)
    imgui.push_style_var(imgui.StyleVar_.frame_rounding, 999.0)
    hit = imgui.button(label, size if size is not None else imgui.ImVec2(0, 0))
    imgui.pop_style_var(2)
    return hit


def button(label: str, size: imgui.ImVec2 | None = None) -> bool:
    """`imgui.button`, on the kit where it is there (`ui_fields.chip`, the
    stock button's size and id: its words and the frame padding)."""
    if ui_kit.ready():
        return ui_fields.chip(label, size, pad=imgui.get_style().frame_padding, pill=False)
    return imgui.button(label, size if size is not None else imgui.ImVec2(0, 0))


def small_button(label: str) -> bool:
    """`imgui.small_button` — a button with no vertical padding — on the kit
    where it is there, as `button`."""
    if ui_kit.ready():
        return ui_fields.chip(label, pad=imgui.ImVec2(imgui.get_style().frame_padding.x, 0),
                              pill=False)
    return imgui.small_button(label)


def _arrow_icon(direction) -> str:
    """Lucide's chevron for an `imgui.Dir` (whose str is a bare number here)."""
    d = imgui.Dir
    return {int(d.left): "chevron_left", int(d.right): "chevron_right",
            int(d.up): "chevron_up", int(d.down): "chevron_down"}[int(direction)]


def arrow_button(str_id: str, direction) -> bool:
    """`imgui.arrow_button` — a frame-high square with an arrow — on the kit
    where it is there: the kit's Button with Lucide's chevron, the same id."""
    if ui_kit.ready():
        name = _arrow_icon(direction)
        fh = imgui.get_frame_height()
        return ui_fields.chip(str_id, imgui.ImVec2(fh, fh), pill=False, icon=name)
    return imgui.arrow_button(str_id, direction)


def input_text_with_hint(label: str, hint: str, text: str, flags: int = 0) -> tuple[bool, str]:
    """`imgui.input_text_with_hint`, on the kit where it is there (a label
    that is all id, ``##…``: `ui_fields.text_field`, the same id and room)."""
    if ui_kit.ready() and label.startswith("##"):
        return ui_fields.text_field(label, hint, text, flags)
    return imgui.input_text_with_hint(label, hint, text, flags)


def input_text(label: str, text: str, flags: int = 0) -> tuple[bool, str]:
    """`imgui.input_text`, on the kit where it is there, as `input_text_with_hint`."""
    if ui_kit.ready() and label.startswith("##"):
        return ui_fields.text_field(label, "", text, flags)
    return imgui.input_text(label, text, flags)


def checkbox(label: str, value: bool) -> tuple[bool, bool]:
    """`imgui.checkbox` — `(clicked, value)` — for a check with no param
    behind it (`Panel._check` draws a param's); on the kit where it is
    there, the same footprint and id (`ui_fields.check`)."""
    if ui_kit.ready():
        return ui_fields.check(label, value)
    return imgui.checkbox(label, value)


def chip_group(labels, lit=None, tips=None) -> int | None:
    """Chips side by side as ONE group, each `lit` (a list; None: none lit)
    solid red while on, `tips` (a list; None for none) their hovers; on the
    kit joined — one border between members, the outer corners rounded
    (`comp_button.button_group`) — and as plain chips without it. The index
    clicked, or None."""
    lit = lit or [None] * len(labels)
    hit = None
    joins = None
    if ui_kit.ready():
        CB = ui_kit.mod("comp_button")
        joins = CB.button_group([(0, 0, 1, 1)] * len(labels), "horizontal")
    for i, label in enumerate(labels):
        if i:
            imgui.same_line(0, 0 if joins else -1)
        if joins:           # (through `chip`, so whatever wraps the panel's chips sees these)
            on = lit[i]
            clicked = chip(label, lit=bool(on), color=DIM if on is False else None,
                           join=joins[i])
        elif (on := lit[i]) is not None:
            clicked = lit_chip(label, on)
        else:
            clicked = chip(label)
        if tips and tips[i] and imgui.is_item_hovered():
            tooltip(tips[i])
        if clicked:
            hit = i
    return hit


def lit_chip(label: str, lit: bool, color: imgui.ImVec4 | None = None,
             size: imgui.ImVec2 | None = None) -> bool:
    """A chip that is solid red while on — a lit key, readable from the floor."""
    if ui_kit.ready():                  # on the kit (hyperspace/dkit): the same size and id
        return ui_fields.chip(label, size, lit=lit, color=color or DIM)
    if lit:
        imgui.push_style_color(imgui.Col_.button, RED)
        imgui.push_style_color(imgui.Col_.button_hovered, imgui.ImVec4(1.0, 0.40, 0.40, 1))
        imgui.push_style_color(imgui.Col_.button_active, imgui.ImVec4(0.8, 0.12, 0.12, 1))
        imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(1, 1, 1, 1))
    else:
        imgui.push_style_color(imgui.Col_.text, color or DIM)
    hit = chip(label, size)
    imgui.pop_style_color(4 if lit else 1)
    return hit


def dirty_dot(tip: str) -> tuple[float, float, float, float]:
    """The dirty dot (plan 19 WP5): a filled disc of radius `DOT_R` in
    `RED`, in a cell of its own on the current line — call it after
    ``same_line`` beside the name it belongs to. The cell is one text line
    tall, never taller than the frame items beside it, so no row grows;
    the disc is centred on the item before it (the name), so it sits on
    that item's middle whatever the line's height. `tip` is its hover.
    Returns the disc's bounding box on screen (x0, y0, x1, y1)."""
    a, b = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    cy = (a.y + b.y) / 2
    at = imgui.get_cursor_screen_pos()
    imgui.dummy(imgui.ImVec2(2 * DOT_R, imgui.get_text_line_height()))
    cx = at.x + DOT_R
    imgui.get_window_draw_list().add_circle_filled(imgui.ImVec2(cx, cy), DOT_R, u32(RED))
    if imgui.is_item_hovered():
        tooltip(tip)
    return (cx - DOT_R, cy - DOT_R, cx + DOT_R, cy + DOT_R)


def fit_text(text: str, width: float) -> str:
    """`text`, or its start and an ellipsis when it is wider than `width`
    pixels in the current font (the footer's message beside the show's name)."""
    if imgui.calc_text_size(text).x <= width:
        return text
    lo, hi = 0, len(text)
    while lo < hi:                      # the longest start that fits with its "…"
        mid = (lo + hi + 1) // 2
        if imgui.calc_text_size(text[:mid] + "…").x <= width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"


GROUND_WORDS = "nothing — its ground"
THROUGH_WORDS = "hands through the effects"     # OUTPUT's checkbox (plan 35 O)
OPEN_ON_GRAPH = "open on GRAPH"                 # a window's block: its node selected there
NAME_ROOM = 64.0     # px: an OUTPUT block name needs this beside its ticks, or they go under it


def shows_line(spec, n: int | None, slots=(), bus_cuts=None) -> str:
    """The OUTPUT page's "shows:" (plan 35 U), read off the wired frame
    (`graphview.page_spec`: None is the factory frame): window `n`'s
    picture port — its own wire's source by its title (`graphview.
    label_of`: "Channel A"), "as All outputs" with no wire of its own, or
    "nothing — its ground" for a `ground` wire or nothing anywhere; a
    window putting the hands through the effects says so after. `n` None:
    All outputs' own picture. The mutes are not read: they are the
    window's ticks beside the words. `bus_cuts` (plan 36 T1): the loaded patch's
    wires — a window whose bus cable is cut shows nothing by it."""
    spec = graphview.page_spec(spec)
    alls = graphview.picture_now(spec, f"{graphview.rgraph.ALL_OUTPUTS}.image")
    if n is None:
        now = alls
    else:
        now = graphview.picture_now(spec, f"output.{n}.image", bus_cuts)
        if now == graphview.AS_ALL and alls == graphview.NOTHING:
            now = graphview.NOTHING
    words = GROUND_WORDS if now == graphview.NOTHING else graphview.picture_label(
        spec, now, slots)
    if n is not None and graphview.is_through(spec, n, bus_cuts):
        words += f" · the {THROUGH_WORDS}"
    return f"shows: {words}"


def output_shows(sw, fx_on: bool, visible: bool, master: float,
                 wiring: Wiring | None = None, n: int | None = None,
                 bus_cuts=None) -> tuple[str, str]:
    """What one render output shows, in words, and why it is black ("" when
    it is not) — plan 21 WP4, fork F8: words, no picture; plan 35 T6: the
    picture combo's hover, its black words after `shows_line`'s, and the
    footer's black outputs: its window's mutes (`sw`: the picture, the hands),
    whether an effect is on, whether a hand shows (`visible`: the ghost
    hands are on and the layer drew, fork F7), with master × its own dim.
    The reasons: "nothing" (both muted), "no hand" (the picture muted and no
    hand showing), "dim" (its own dim at 0), "master" (the MASTER fader at
    black — the footer already says "dim black").

    Plan 35 T4: the words read the wires (plan 36 T3: None is the empty
    frame, `graph.EMPTY`) — "hands through the
    effects" where output `n`'s picture is a chain over the layer laid on
    (`graph.through_layer`; it bends only with an effect on and a hand
    drawn, else the hands go over), "scene + hands in the scene" where the
    scene holds them (`graph.hands_words`), a layer's node when there are
    two, "as lines", a blend that is not plainly over; a picture or hands
    by a wire of the output's own (plan 28 N4); the effects placed on what
    it shows (plan 30 D1, `graph.output_placement_words`). Plan 36 T1:
    `rig`, the show's bus wires — a port whose bus cable is cut is empty."""
    w = wiring if wiring is not None else EMPTY
    k = n if n is not None else 1
    shown = bool(sw.hands) and bool(visible)
    thru = through_of(w, k, bus_cuts)
    got = output_ports(w, k, bus_cuts)
    through = thru is not None
    bent = through and shown and fx_on
    # (a through over nothing is the hands alone: no scene in its picture)
    picture = (bool(sw.scene) and got["image"] is not None
               and not (through and thru[1] is None))
    inside = bool(in_scene_hands(w)) and picture
    after = shown and not bent and not inside and got["hands"] is not None
    own = float(sw.dim)
    # plan 28 N4: the loadable patch's wires into this output's own ports (a
    # through's chain and a port wired to show nothing are not "a wire")
    ports = ({x.port: x for x in w.wires if x.node == f"output.{k}" and x.src != GROUND}
             if n is not None else {})
    if through:
        ports.pop("image", None)
    if ports:
        if own <= 0.0:
            return "black — dim 0", "dim"
        if master <= 0.0:
            return "black — master dim", "master"
        if "image" in ports and sw.scene:
            words = wire_words(ports["image"]).partition(" shows ")[2] + " by a wire"
        elif not picture and not after:
            words = "ground"
        else:
            words = output_shows(sw, fx_on, visible, 1.0, w)[0]
        words += "".join(" · " + wire_words(x) for p, x in sorted(ports.items())
                         if p != "image")
        if "image" not in ports and w.placed:
            words += output_placement_words(w, k, picture, after or bent)
        factor = min(1.0, master * own)
        if factor < 1.0:
            words += f" · {min(99, max(1, round(factor * 100)))}%"
        return words, ""
    if not picture and not after and not bent:
        if not sw.scene and not sw.hands:
            return "black — nothing switched on", "nothing"
        return "black — the scene is off and no hand shows", "no hand"
    if own <= 0.0:
        return "black — dim 0", "dim"
    if master <= 0.0:
        return "black — master dim", "master"
    if bent:
        words = "scene + hands through the effects" if picture else "hands through the effects"
    elif picture:
        words = "scene + hands over the effects" if after else "scene"
    else:
        words = "hands"
    if inside:
        words = "scene + " + hands_words(w, sw, k, bus_cuts)
    elif after or bent:
        # a layer laid on: its node, "as lines", its blend
        words += layer_words(w, thru[0] if bent else got["hands"])
    if n is not None and w.placed:
        words += output_placement_words(w, k, picture, after or bent)
    factor = min(1.0, master * own)
    if factor < 1.0:
        words += f" · {min(99, max(1, round(factor * 100)))}%"
    return words, ""


def dormant_lines(graph) -> list[str]:
    """The OUTPUT page's lines for the built graph's placed effects that
    run nowhere this frame (plan 30 D1: `Graph.dormant` — `dormant:
    palette after hands — no hands layer this frame`) and its placements
    refused at build (`Graph.notes`); none with no graph."""
    dormant = getattr(graph, "dormant", None) or {}
    return ([f"dormant: {w}" for _, w in sorted(dormant.items())]
            + list(getattr(graph, "notes", None) or []))


def desk_log_lines(midi) -> list[str]:
    """The SYSTEM page's desk log (plan 24 C1): the MIDI adapter's last
    twenty desk events, newest first (`midi.DeskLog.lines`); none with no
    adapter, or one from before a hot reload that has no log yet."""
    log = getattr(midi, "desk_log", None) if midi is not None else None
    return log.lines() if log is not None else []


def chip_w(*labels: str) -> float:
    """Width of chips in a row at the default spacing — flush a group of
    them right with same_line(avail - chip_w(...))."""
    s = imgui.get_style()
    w = sum(imgui.calc_text_size(lb.split("##")[0]).x + 2 * CHIP_PAD.x for lb in labels)
    return w + s.item_spacing.x * max(len(labels) - 1, 0)


def flush_right(w: float) -> None:
    """On this row, go to where `w` px end at the content's right edge. `same_line`
    counts from the window's edge, so `same_line(avail - w)` alone stops the window's
    padding short and overruns a row budgeted to `avail` (audit U10)."""
    imgui.same_line(imgui.get_cursor_pos_x() + imgui.get_content_region_avail().x - w)


def button_w(*labels: str) -> float:
    """chip_w for full-size buttons (frame padding from the style)."""
    s = imgui.get_style()
    w = sum(imgui.calc_text_size(lb.split("##")[0]).x + 2 * s.frame_padding.x for lb in labels)
    return w + s.item_spacing.x * max(len(labels) - 1, 0)


def check_w(label: str) -> float:
    """A checkbox's width with its label: the box, the inner gap, the words."""
    s = imgui.get_style()
    words = label.split("##")[0]
    return imgui.get_frame_height() + (s.item_inner_spacing.x + imgui.calc_text_size(words).x
                                       if words else 0.0)


def tag_px(width_at: Callable[[float], float], room: float) -> float:
    """The largest of `TAG_SIZES` at which a tag `width_at` that size measures
    fits `room`; the smallest if none does."""
    return next((px for px in TAG_SIZES if width_at(px) <= room), TAG_SIZES[-1])


def tags_shown(spans: list[tuple[float, float]], first: int, gap: float = TAG_GAP) -> list[int]:
    """Which of these tags (x0, x1 each) to draw so that none touches another:
    `first` for certain (the selected band's), then each in order that keeps
    `gap` from those already kept."""
    kept = [first] if 0 <= first < len(spans) else []
    for i, (x0, x1) in enumerate(spans):
        if i not in kept and all(x1 + gap <= spans[k][0] or spans[k][1] + gap <= x0
                                 for k in kept):
            kept.append(i)
    return sorted(kept)


def beside(w: float) -> bool:
    """The next item, `w` wide, on the line of the item before when it ends
    by the region's right edge; else on a row of its own (plan 49 stage 2:
    a page's row of chips or ticks in the side pane's 240–320 px). Call it
    where `imgui.same_line()` stood. True when it stayed on the line."""
    right = imgui.get_cursor_screen_pos().x + imgui.get_content_region_avail().x
    if imgui.get_item_rect_max().x + imgui.get_style().item_spacing.x + w <= right + 0.5:
        imgui.same_line()
        return True
    return False


def device_lines(registry) -> list[str]:
    """The SYSTEM page's device lines, one per listed device, in the
    list's order: ``role  ·  kind  ·  status  ·  n sources  ·  last``
    (the last part only when the device has one)."""
    out = []
    for role, kind, status, n, last in registry.lines():
        line = f"{role}  ·  {kind}  ·  {status}  ·  {n} source{'' if n == 1 else 's'}"
        if last:
            line += f"  ·  {last}"
        out.append(line)
    return out


def wanted_lines(registry, table) -> list[str]:
    """Plan 40 T4: the SYSTEM page's lines under the device lines, one per
    device role the loaded patch's rows want and the meta controller lacks — "wanted
    by the preset: leap — not set up on this Mac; 3 rows wait" (`devices.wants`,
    `devices.wanted_lines`); none without a registry or a table."""
    if registry is None or table is None:
        return []
    return devices.wanted_lines(devices.wants(table, registry))


# the wants the menu offers by their own items (desk, the hands, the pad)
_OWN_WANTS = frozenset(("desk", "hand:left", "hand:right", "pad", *learn.PAIR_WANTS))


def learn_wants(lrn) -> list[str]:
    """What else the param menu offers to learn (plan 27 B2): every want
    the registry lists (`Learn.wants`) beyond the desk, the hands and the
    pad, which have their own items — a new device's role."""
    wants = getattr(lrn, "wants", None)
    return [w for w in (wants() if callable(wants) else ())
            if w not in _OWN_WANTS and not w.startswith(learn.ONLY)]


def sink_items(lrn) -> list[tuple[str, str]]:
    """The param menu's "Learn sink ▸" items (plan 27 B3): (port address,
    item text) for every sink port the meta controller lists (`Learn.sinks`) —
    ``bridge:3  ·  pitch ch4``; none without a registry or a sink."""
    sinks = getattr(lrn, "sinks", None)
    ports = sinks() if callable(sinks) else ()
    return [(pt.address, f"{pt.address}  ·  {pt.label}" if pt.label else pt.address)
            for pt in ports]


def apply_style() -> None:
    s = imgui.get_style()
    s.window_rounding = 12.0
    s.child_rounding = 10.0
    s.popup_rounding = 10.0
    s.frame_rounding = ROUND
    s.grab_rounding = ROUND
    s.scrollbar_rounding = 12.0
    s.tab_rounding = ROUND
    s.window_border_size = 1.0
    s.popup_border_size = 1.0
    s.frame_border_size = 0.0
    s.window_padding = imgui.ImVec2(14, 12)
    s.frame_padding = imgui.ImVec2(10, 6)
    s.item_spacing = imgui.ImVec2(8, 7)
    s.item_inner_spacing = imgui.ImVec2(7, 6)
    s.grab_min_size = 18.0
    s.scrollbar_size = 12.0
    put = imgui.Col_
    colors = {
        put.window_bg: (0.035, 0.035, 0.04, 0.97),
        put.child_bg: (0.0, 0.0, 0.0, 0.0),
        put.frame_bg: (0.13, 0.13, 0.145, 1.0),
        put.frame_bg_hovered: (0.18, 0.18, 0.20, 1.0),
        put.frame_bg_active: (0.22, 0.22, 0.24, 1.0),
        put.slider_grab: (1.0, 43 / 255, 43 / 255, 1.0),
        put.slider_grab_active: (1.0, 0.45, 0.45, 1.0),
        put.button: (0.17, 0.17, 0.19, 1.0),
        put.button_hovered: (0.24, 0.24, 0.27, 1.0),
        put.button_active: (0.45, 0.10, 0.10, 1.0),
        put.header: (0.20, 0.20, 0.22, 1.0),
        put.header_hovered: (0.26, 0.26, 0.29, 1.0),
        put.header_active: (0.30, 0.30, 0.33, 1.0),
        put.check_mark: (1.0, 1.0, 1.0, 1.0),   # a white tick on a solid red box
        put.checkbox_selected_bg: (1.0, 43 / 255, 43 / 255, 1.0),
        put.resize_grip: (0.22, 0.22, 0.24, 0.6),
        put.resize_grip_hovered: (0.36, 0.36, 0.40, 1.0),
        put.resize_grip_active: (1.0, 43 / 255, 43 / 255, 1.0),
        put.separator_hovered: (0.36, 0.36, 0.40, 1.0),
        put.separator_active: (1.0, 43 / 255, 43 / 255, 1.0),
        put.nav_cursor: (1.0, 43 / 255, 43 / 255, 1.0),
        put.text_link: (1.0, 43 / 255, 43 / 255, 1.0),
        put.drag_drop_target: (1.0, 43 / 255, 43 / 255, 1.0),
        put.table_border_light: (0.16, 0.16, 0.18, 1.0),
        put.table_border_strong: (LINE.x, LINE.y, LINE.z, 1.0),
        put.table_header_bg: (0.10, 0.10, 0.11, 1.0),
        put.separator: (LINE.x, LINE.y, LINE.z, 1.0),
        put.border: (0.20, 0.20, 0.22, 1.0),
        put.title_bg: (0.06, 0.06, 0.07, 1.0),
        put.title_bg_active: (0.08, 0.08, 0.09, 1.0),
        put.title_bg_collapsed: (0.06, 0.06, 0.07, 1.0),
        put.text: (TEXT.x, TEXT.y, TEXT.z, 1.0),
        put.text_disabled: (FAINT.x, FAINT.y, FAINT.z, 1.0),
        put.popup_bg: (0.07, 0.07, 0.08, 0.98),
        put.scrollbar_bg: (0.0, 0.0, 0.0, 0.0),
        put.scrollbar_grab: (0.22, 0.22, 0.24, 1.0),
        put.scrollbar_grab_hovered: (0.30, 0.30, 0.33, 1.0),
        put.scrollbar_grab_active: (0.36, 0.36, 0.40, 1.0),
        put.text_selected_bg: (1.0, 43 / 255, 43 / 255, 0.35),
    }
    for k, v in colors.items():
        s.set_color_(k, imgui.ImVec4(*v))


# the corner key legend, in the spirit of the HTML's #keys overlay
CHEATSHEET = [
    ("drag", "orbit view"),
    ("⇧drag", "pan (or right-drag)"),
    ("scroll", "zoom about cursor"),
    ("← →", "previous / next shape"),
    ("space", "pause rotation"),
    ("P / L / F", "points / lines / faces"),
    ("O", "who is on air: the player screen"),
    ("1–6", "planes XY XZ YZ XW YW ZW"),
    ("↑ ↓", "4D depth · hold accelerates"),
    ("[ ]  , .", "brightness · speed"),
    ("M", "mic on/off"),
    ("K / 0", "play-pause / restart track"),
    ("R", "reset view + camera"),
    ("F1–F8", "load off air · ⇧ saves"),
    ("B", "tap tempo · ⇧B LFO trigger"),
    ("Cmd+Z", "undo, after a change here · ⇧ redo (or Ctrl+Z)"),
    ("Home", "home patch, off air (fn ←)"),
    ("Cmd+R", "restart process"),
    ("Cmd+[ ]", "panel section back · forward"),
    ("H / ?", "panel / this sheet"),
    ("T", "overlay (if config.toml allows)"),
    ("G", "overlay: clicks through / back"),
    ("Q", "quit"),
    # Xbox-layout gamepad, Bluetooth or USB (gamepad.py holds the map)
    ("pad S N · E W", "faces · lines · points · screen strokes"),
    ("pad BACK", "held: the base chase keeps what the sources moved"),
    ("LB / RB", "previous / next shape"),
    ("d-pad ↑ / ↓", "brightness"),
    ("sticks", "orbit · zoom ↕ 4D spin ↔ — click resets each"),
    ("LT / RT", "4D depth out / in"),
    # any control ↔ any MIDI message, through the registry (midi.py)
    ("right-click", "a control: learn desk / hand / pad · unbind"),
    # the APC40's glyphs, as the desk above and the ROUTING rows print them
    ("APC40", "K D knobs · S faders · G row·col · B ⇧"),
    # the APC40 rows whose labels alone do not say it (2026-10-16)
    ("APC40 G7 G9 G10", "analyzer band (⇧ D knobs follow) · next transfer · reset"),
    ("APC40 clip pads", "load off air · hold an empty one: save"),
    ("APC40 QUANT", "next bank patch, off air"),
    ("APC40 STOP ALL", "reset the analyzer · again within 8 s: undo"),
    ("APC40 MASTER PAN", "overlay · click-through (if config allows)"),
]

# ---- `ui.page`'s slots ----
# Plan 49 stage 3: there are no pages to switch. GRAPH is always drawn and
# every other name is a section of its side pane (`ui_pane.SECTIONS`, which
# also holds what each one's params are), drawn by the body that was the
# page: `ui.page` is the pane's one view, and setting it shows the section
# of that name (`Panel.go_page`). The list stays, in its order,
# because the param's value is an index and a binding's `set` stores it:
# every index a key row, a pad or an old show holds names what it always
# named. Never reorder it; a new section goes at the end. FX's slot is the
# fx section. GRAPH's shows the selection (the canvas is always there).
# the sections that hold the meta controller's params: ⌘Z there takes its stack
# (plan 44 D5b, `Panel.in_meta_section`). The owner named analyzer, hands and
# output; audio holds the master faders and nothing of a loadable patch (row 692)
META_SECTIONS = ("output", "audio", "analyzer", "hands")

# The analyzer is one for both looks, so what it hears of the video on air reaches the
# look off air's routes. The owner accepts this (2026-11-06, row 790) and wants it said.
VIDEO_SOUND_REACHES = "Off air reacts to on air's video sound."

PAGE_KEYS = ["output", "view", "faces", "media", "camera", "lookback", "fx", "audio", "analyzer",
             "routing", "graph", "lfo", "seq", "hands", "loadable", "system", "players", "playlist"]


View = tuple[int, "str | None"]     # (a PAGE_KEYS index, the node selected in the selection view)
SETTLE_NOTES = 10    # frames a step waits for its view to land before taking what landed


def view_of(panel) -> View:
    """What the side pane shows, as the history keeps it: `Panel.page`, and
    in the selection's view (GRAPH's slot) the node selected there
    (`Panel.graph_selected`; None for nothing, a cable, a group or several).
    A section's view is its slot alone: a node selected while it is up is
    no step of its own."""
    page = getattr(panel, "page", 0)
    graph = PAGE_KEYS.index("graph")
    return (page, getattr(panel, "graph_selected", None) if page == graph else None)


def go_view(panel, view: View) -> None:
    """Bring `view` back (⌘[ / ⌘]): the slot straight on `Panel.page`, and
    in the selection's view its node selected again and centred on the
    canvas (`ui_graph.select_id`), or nothing selected (Esc's request) —
    only where the canvas's selection differs."""
    page, nid = view
    panel.page = page
    if page != PAGE_KEYS.index("graph") or getattr(panel, "graph_selected", None) == nid:
        return
    if nid is not None:
        ui_graph.select_id(panel, nid)
    else:
        ui_graph._state(panel)["deselect"] = True


class PageHistory:
    """The side pane's views, back and forward as a browser's are (⌘[ /
    ⌘]): each a `View`, so the selection's view keeps which node it showed.
    `note` records the view now — a chip, a key row, a pad, a click on the
    canvas, a selection, a step here — dropping the forward run when it is a
    new visit; `step(-1)` / `step(1)` returns the view to go to (`go_view`),
    or None at either end. After a step, notes wait up to `SETTLE_NOTES`
    frames for that view's selection to land (it lands a frame or two
    later); one that never does (its node deleted since) takes the step's
    place in the list, so the forward run is kept, and is folded into a
    neighbour it now repeats, so no step goes nowhere. A note on another
    slot is a new visit at once."""

    def __init__(self, view):
        self.visited, self.at = [self._view(view)], 0
        self.landing: View | None = None
        self.wait = 0

    @staticmethod
    def _view(view) -> View:
        return view if isinstance(view, tuple) else (int(view), None)   # (a bare slot)

    def note(self, view) -> None:
        view = self._view(view)
        landing, self.landing = self.landing, None
        if landing is not None and view[0] == landing[0]:   # (another slot: a new visit)
            if view != landing and self.wait > 0:
                self.wait -= 1
                self.landing = landing          # its selection not landed yet
                return
            self.visited[self.at] = view        # as it landed
            at = self.at                        # …and one with a neighbour just like it goes,
            if at + 1 < len(self.visited) and self.visited[at + 1] == view:
                del self.visited[at + 1]        # so no ⌘[ / ⌘] lands where it was
            elif at > 0 and self.visited[at - 1] == view:
                del self.visited[at]
                self.at = at - 1
            return
        if view == self.visited[self.at]:
            return
        del self.visited[self.at + 1:]
        self.visited.append(view)
        self.at = len(self.visited) - 1

    def step(self, by: int) -> View | None:
        i = self.at + by
        if not 0 <= i < len(self.visited):
            return None
        self.at = i
        self.landing, self.wait = self.visited[i], SETTLE_NOTES
        return self.visited[i]


def _gpu_block(stats: dict, head: str) -> list[str]:
    """A GPU block of the SYSTEM page, from a renderer's `stats`."""
    ms = stats.get("gpu_ms") or {}
    note = stats.get("gpu_note") or ""
    ends = [f"ends: {' · '.join(stats['ends'])}"] if stats.get("ends") else []
    if not ms:
        return [f"{head}: {note}"] if note else []
    width = max(len(name) for name in ms)
    return ([f"{head} per node, ms (median of the last frames):"]
            + [f"  {name:<{width}}  {v:6.2f}" for name, v in ms.items()] + ends)


class Panel:
    # plan 44 D5a: what the panel shows is the deck its own pointer is on
    # (`deck.MetaController.panel_pointer`, set by app.py), read each time; with
    # no pointer (a panel from a test) these are plain attributes
    reg = Through("reg")
    view = Through("view")
    renderer = Through("renderer")
    router = Through("router")
    learn = Through("learn")
    undo = Through("undo")
    lfos = Through("lfos")
    envs = Through("envs")
    seq = Through("seq")
    deck = Through(None)

    displays: Any = None  # set by app.py (displays.Running): a row per display (SC2)

    def __init__(self, control: Control, audio: AudioEngine, view: ViewState, renderer=None,
                 bank=None, registry: Registry | None = None, library=None):
        self.control = control
        self.audio = audio
        self.view = view
        self.renderer = renderer
        # app.restart (the SYSTEM page's button, Cmd+R's param) sets it; app.frame
        # polls it after the panel draws and restarts the process
        self.restart_requested = False
        # plan 33 U: the effect instance selected — on GRAPH (its node) or in
        # the fx section (its row): one selection both show; saved nowhere
        self.fx_selected: str | None = None
        # 2026-10-31: the canvas's selection, published for whoever is not
        # the graph view — a controller's node mode, the side pane. The one
        # selected canvas node's id (`render:acid.2`, a modifier's id); None
        # while nothing, a cable, a bundle, a group or several nodes are
        # selected. Written by `ui_graph.publish` every frame the panel draws
        # (plan 49 stage 3: GRAPH is always drawn), and let go by
        # `ui_graph.settle` when a loadable patch lands without the node. With the
        # panel hidden it is as of the last frame drawn. An effect's node is
        # `fx_selected` as well (`ui_graph.share`).
        # `graph_selected_at`: imgui's frame count when it last changed.
        self.graph_selected: str | None = None
        self.graph_selected_at: int = 0
        self.library = library      # library.Library, or None: no strips, no project row
        # the F1–F8 loadable patch bank is the open project's (library.Install)
        self.bank = bank if bank is not None else (
            library.install if library is not None else None
        )
        self.reg = registry if registry is not None else build_registry(
            view, control, audio, self.bank
        )
        self.pin_in = [0.0] * N_MAX
        self.pin_out = [0.0] * N_MAX
        self.open = True
        self.cheatsheet = False     # off at every launch; / brings it up (plan 16 WP1)
        # the APC40 left of the panel: off at launch, the panel filling the
        # window instead (the owner, 2026-10-26: GRAPH is where the time goes);
        # the SYSTEM page's switch brings it back
        self.desk = False
        # the gamepad over the desk in the same column (ui_pad.py): off at
        # every launch, as the cheat sheet is — the desk keeps its room
        # until the SYSTEM page's switch asks for the pad
        self.pad_diagram = False
        self.pad_view = 0       # ui_pad_views.VIEWS: map, faithful, lanes, cockpit
        self.poi_dials = True   # the Poi window (ui_pad.poi_window): shown each time the poi comes on
        # the side pane's view, an index into PAGE_KEYS (`ui.page`, `go_page`),
        # its one owner (`ui_pane.showing`); GRAPH's slot is the selection, the launch's view
        self.page = PAGE_KEYS.index("graph")
        self._focus_seen = self.page            # what `go_page` last acted on (`_draw`)
        self.history = PageHistory(self.page)   # ⌘[ / ⌘]: back and forward (app.frame)
        self.ghosts = 0             # ghost markers drawn this frame (tests read it)
        self._file_dialog = None
        self.reloader = None  # set by app.py; panel only reads status off it
        self.config_error = ""  # set by app.py: config.toml failed to parse (SYSTEM page)
        self.config_notes: list[str] = []  # set by app.py: config.toml wants a rename
        self.graph_start_zoom = 1.0  # set by app.py: GRAPH's first zoom, off the display (plan 58 SM2)
        # GRAPH frames every node in what the pane leaves of the canvas when it opens
        # and on every load (`ui_graph.ask_fit`), never closer than the start zoom
        self.graph_fit = True
        self.dream_error = ""  # set by app.py: why the dream worker is off (SYSTEM, LOOKBACK)
        self.watchdog = None   # set by app.py (watchdog.Watchdog): the stall log line
        self.render_watch = None   # set by app.py (watchdog.RenderWatch): the red banner
        self.midi = None      # set by app.py when an adapter is up (midi.MidiIO)
        self.pad = None       # set by app.py unless [gamepad] enabled = false (gamepad.Pad)
        self.learn = None     # set by app.py: the armed param and the held question (learn.Learn)
        self.undo = None      # set by app.py (undo.Undo): its status shows in the footer
        self.meta_undo = None  # the meta controller's stack (plan 44 D5b): so does its
        self.meta = None       # set by app.py (deck.MetaController): GRAPH's head, the player screen
        self.playing = None    # set by app.py (playlist.Playing): the playlist section
        self._fine_drag = None   # the slider a Shift drag holds (`_fine`): its id, mouse x, throw
        self._shift = self._mouse_down = False   # this frame's ⇧ and left button (`_fine_frame`)
        self.devices = None   # set by app.py (devices.DeviceRegistry): the SYSTEM page's lines
        self.media = None     # set by app.py (app.MediaIO): the MEDIA page's folder and channels
        self.canvas_tap = None   # set by app.py (outputs.CanvasTap): the GRAPH canvas as `panel:graph`
        self.canvas_px = None    # GRAPH's canvas this frame (ui_graph.page), else None
        self.dialog_error = ""   # why the file dialog would not open (`open_file_dialog`)
        self.router = None    # set by app.py (routing.Router); else found via midi's table
        self.output = None    # set by app.py (overlay.Output); its params draw below
        self.hands = None          # set by app.py when the tracker is on (hands.HandsIO)
        self.hand_settings = None  # set by app.py (hands.HandSettings): the HANDS page
        self.clock = None          # set by app.py (tempo.Clock): the LFO page's beat light
        self.lfos = None           # set by app.py (lfo.LFOs): the LFO page's scopes
        # set by app.py (deck.Deck, plan 44 D1); `pointer`'s once it has one
        self.deck = None
        self.pointer = None
        self._register_panel_params()

    def close(self) -> None:
        """Let go of what the panel holds outside Python: the GRAPH page's
        node editor context (ui_graph.py, plan 28 N2). app.py calls it on
        quit and on ⌘R, before imgui shuts down; a panel that never drew
        the page holds none — the GRAPH canvas's tap (`canvas_tap`,
        2026-11-02) and the pad drawings' NanoVG (ui_pad_nvg) go with it,
        while the control window's GL is up. Safe to call twice."""
        ui_graph.close(self)
        tap, self.canvas_tap = getattr(self, "canvas_tap", None), None
        if tap is not None:
            tap.close()
        from . import ui_pad_nvg
        ui_pad_nvg.close(self)

    def _register_panel_params(self) -> None:
        """The panel's own state as ``ui.*`` params: the window, the sheet,
        the page. Everything else the factory table names (``audio.mic``,
        ``audio.device``, ``app.restart``) is declared by `build_registry`,
        so a key row resolves with or without a panel."""
        r = self.reg
        if "ui.panel" in r:
            return
        r.toggle("ui.panel", "Control panel",
                 lambda: self.open, lambda on: setattr(self, "open", bool(on)), group="ui",
                 persist=False, modulatable=False)
        r.toggle("ui.cheatsheet", "Cheat sheet",
                 lambda: self.cheatsheet,
                 lambda on: setattr(self, "cheatsheet", bool(on)), group="ui",
                 persist=False, modulatable=False,
                 tip="Keys, pad and desk legend, bottom-left of this window. "
                     "/ toggles it.")
        r.toggle("ui.desk", "Desk diagram",
                 lambda: self.desk,
                 lambda on: setattr(self, "desk", bool(on)), group="ui",
                 persist=False, modulatable=False,
                 tip="The APC40 drawn left of the panel: the controls the layer that is "
                     "up maps lit, each with the glyph the ROUTING rows print. Hide the "
                     "panel (H, or the desk's big chip) and it fills the window, every lit "
                     "control named.")
        r.toggle("ui.pad_diagram", "Pad diagram",
                 lambda: self.pad_diagram,
                 lambda on: setattr(self, "pad_diagram", bool(on)), group="ui",
                 persist=False, modulatable=False,
                 tip="The gamepad drawn over the desk, top-left: every control it sends, "
                     "lit where a row maps it and named with what it does. A grey label "
                     "is the app's own hand on a free axis (orbit, zoom, the 4D spin).")
        from . import ui_pad_views
        r.enum("ui.pad_view", "Pad view", lambda: self.__dict__.get("pad_view", 0),
               lambda i: setattr(self, "pad_view", int(i)), list(ui_pad_views.VIEW_LABELS),
               group="ui", persist=False, modulatable=False, tip=ui_pad_views.VIEW_TIP)
        r.enum("ui.page", "Side pane view", lambda: self.page, lambda i: Panel.go_page(self, i),
               list(PAGE_KEYS), group="ui", persist=False, modulatable=False,
               tip="What GRAPH's side pane shows, at its full height: a section, or graph "
                   "for what is selected on the canvas. ⌘[ / ⌘] step back and forward.")

    def in_meta_section(self) -> bool | str | None:
        """What ⌘Z goes by, through `undo.where`: its meta stack here, else the
        panel's deck's. **What is under the mouse decides:** a param undo watches
        says by its own layer, wherever it is drawn (a mixed section: hands with
        `ghost.*`, SYSTEM with `desk.slew`, a fixture node in the selection); else the
        section under it (`ui_pane.where`); else the deck. Over the player screen, its
        own window too, `undo.BOARD`: the meta stack, for a player's moves alone (row
        800). None over the playlist (its popup on GRAPH's deck row, `ui_playlist.popup`):
        no stack, since an edit there is on none of them (`undo.here`)."""
        p = getattr(self, "_param_under", None)
        if p is not None and undo.watched(p):
            return part_of(p) != "patch"
        if ui_players.over(self):
            return undo.BOARD
        section = ui_pane.where(self)
        if section == ui_playlist.UNDER:   # a list's edits are files, on no stack (row 709)
            return None
        return section in META_SECTIONS

    def go_page(self, i) -> None:
        """`ui.page`'s setter, and `_draw` for an index set straight (⌘[ /
        ⌘]): slot `i` of `PAGE_KEYS` is the side pane's view from the next
        draw (`ui_pane.showing`) — its section, or, for GRAPH's slot, the
        selection. Plan 49 stage 3: no page changes; the canvas is always
        drawn. Saved indices mean what they meant: the section of the name
        the page had."""
        self.page = self._focus_seen = int(i)

    # ---- binding menu: every widget gets one on right-click ----

    def _ctx(self, a: Param, key: str = "", extra=None) -> None:
        """The param's context menu, attached to the last drawn item.

        `a` is the drawn param — the bindings hang off it; the modulation
        line reads the one it stands for (a band.sel.* alias → its band).
        `key` tells apart several items that stand for one param, so each
        gets its own popup. `extra`,
        when given, is called inside the popup after the param's own items
        to draw the caller's (a bank slot's "put preset here…")."""
        if imgui.is_item_hovered():             # what ⌘Z goes by (`in_meta_section`)
            self._param_under = a
        if getattr(self, "_picking", False):    # a desk control is picked: the click is its
            self._ctx_pick(a)
            return
        if not imgui.begin_popup_context_item(self._ctx_id(a, key)):
            return
        _micro(a.id, DIM)
        p = self._real(a)
        if p.modulated:
            imgui.text_disabled(f"modulated: {self._mod_text(p)}")
        lrn = self.learn
        desk, routes = self._ctx_lines(a, p)    # what is bound here, a line each
        # Learn is the host's, not the MIDI adapter's, and it says what it
        # waits for (plan 17 WP2): the desk, or one hand — nothing else can
        # complete it
        self._ctx_learn_block(a, p)
        if lrn is not None:
            self._ctx_unbind(a, p, desk, routes)
        ui_hands.ctx_rows(self, p, lines=False)     # the hand rows' "Gate: … ▸"
        ui_routing.ctx_item(self, a)    # "Route a lane here…" — the routing matrix
        if extra is not None:
            extra()
        imgui.end_popup()

    def _ctx_pick(self, a: Param) -> None:
        """"Click a control, then a param" (plan 17 WP4, fork 3): while a
        desk control is picked the page is drawn disabled (`_draw`) and
        this stands in for the menu on every param widget, and on a
        row's label (`_ctx_label`). The item under the mouse — hover is
        asked with `allow_when_disabled` — gets the learn's red frame, and
        a left click on it puts the picked control there:
        `Learn.map_picked`, the knob learn's road. The widget itself takes
        no click: it is disabled. A param no desk control can go on
        (`_desk_target`) is not a target; and no click maps until the
        mouse has left the spot of the click that picked (`ui_desk.armed`)."""
        if not self._desk_target(a) \
                or not imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            return
        c = ui_desk.picked(self)
        if c is None or self.learn is None or not ui_desk.armed(self):
            return
        self._frame_item()
        tooltip(f"click: put {c.glyph} on {a.label or a.id}")
        if imgui.is_mouse_clicked(0):
            self.learn.map_picked(a.id, apc40)

    @staticmethod
    def _ctx_id(a: Param, key: str = "") -> str:
        """The menu's popup id: one per drawn param (and `key`)."""
        return f"##ctx.{a.id}{key}"

    def _ctx_label(self, a: Param) -> None:
        """The last item — a row's label — opens the param's menu too
        (plan 17 WP3): the label is where the name is, and where a hand
        lands when it means "this control". Only the opening: the popup
        itself is drawn by the `_ctx` of the widget beside it, so the two
        calls must sit in one id scope (the same window, the same
        `push_id`) to name the same popup. While a desk control is picked
        the label is the pick's target like the widget (`_ctx_pick`)."""
        if getattr(self, "_picking", False):
            self._ctx_pick(a)
            return
        imgui.open_popup_on_item_click(self._ctx_id(a), imgui.PopupFlags_.mouse_button_right)

    @staticmethod
    def _desk_target(a: Param) -> bool:
        """Can a desk control be put on this param? The rule "Learn desk"
        is offered by (plan 17 WP3: Learn only where it can act) — the one
        ROUTING's desk rows offer their targets by (`ui_routing.desk_target`)."""
        return ui_routing.desk_target(a)

    def _table(self):
        """The live binding table — the router's, else the learn object's —
        never the MIDI adapter's: the menu reads and edits the table with
        or without one (plan 17 WP1). None on a panel with neither."""
        router = ui_routing.router_of(self)
        if router is not None:
            return router.table
        return getattr(self.learn, "table", None)

    def _row_name(self, b) -> str:
        """A row in the menu's and the message's words: a desk row by its
        control ("K1 (track knob 1)": the glyph, then Akai's name), a route
        as the router describes it ("R height positions")."""
        table = self._table()
        if b.is_midi:
            named = apc40.named(b.source) if getattr(table, "profile", None) == "apc40" else None
            return named or b.describe()
        router = ui_routing.router_of(self)
        return router.describe(b) if router is not None else b.describe()

    def _route_source(self, b) -> str:
        """A route's source alone, in its adapter's words ("R height",
        "LFO 1"), for the Unbind submenu."""
        router = ui_routing.router_of(self)
        if router is not None:
            scheme, i = router.lane(b.source)
            names = router.labels.get(scheme) or []
            if 0 <= i < len(names):
                return names[i]
        return b.source

    def _ctx_lines(self, a: Param, p: Param) -> tuple[list, list]:
        """The menu's lines, one per thing bound to the param, read from
        the table: the loaded patch's desk rows, the routes ("(off)" when
        disabled; the hand rows through hands/panel.py), then the meta controller's
        rows, dim — those are never an item (D5, D6). Returns (the desk
        rows, the routes) an Unbind would remove."""
        table = self._table()
        if table is None:
            return [], []
        # the same question `Learn.unbind` asks, so the lines are what it removes
        desk, routes, meta_rows = learn.bound(table, (a.id, p.id))
        for b in desk:
            op = "" if b.op in ("abs", "rel") else f" · {ui_routing._op_text(b)}"
            imgui.text(self._row_name(b) + op)
        ui_hands.ctx_rows(self, p, gate=False)
        for b in routes:                # ctx_rows drew the hand's rows on the real param
            if b.scheme != "hand" or b.target != p.id or self.router is None:
                imgui.text(self._row_name(b) + ("" if b.enabled else " (off)"))
        for b in meta_rows:
            where = "global layer" if b.layer == "global" else "invariant"
            imgui.text_disabled(f"{self._row_name(b)} · {where}")
        for b in learn.sinks_of(table, (a.id, p.id)):     # the meta controller's, out (plan 27 B3)
            imgui.text_disabled(f"→ {b.target} · sink" + ("" if b.enabled else " (off)"))
        return desk, routes

    def _ctx_unbind(self, a: Param, p: Param, desk: list, routes: list) -> None:
        """The one Unbind (plan 17 WP1): drawn only when it would remove
        something — a plain item with one kind bound, a submenu (desk /
        route / both) with both. `Learn.unbind` does it: one undo step, the
        loaded patch edited, no file written."""
        if not desk and not routes:
            return
        ids, lrn = (a.id, p.id), self.learn
        if not (desk and routes):
            if imgui.menu_item_simple("Unbind"):
                lrn.unbind(ids, name=self._row_name)
            return
        if not imgui.begin_menu("Unbind"):
            return
        table = self._table()
        glyphs = ", ".join(ui_routing.control_glyph(table, b) for b in desk)
        sources = ", ".join(self._route_source(b) for b in routes)
        if imgui.menu_item_simple(f"desk — {glyphs}"):
            lrn.unbind(ids, routes=False, name=self._row_name)
        if imgui.menu_item_simple(f"route — {sources}"):
            lrn.unbind(ids, desk=False, name=self._row_name)
        if imgui.menu_item_simple("both"):
            lrn.unbind(ids, name=self._row_name)
        imgui.end_menu()

    def _ctx_learn_block(self, a: Param, p: Param) -> None:
        """The menu's Learn block: "no learn" without one; while `a` is
        armed, what it waits for and Cancel; else the Learn items
        (`_ctx_learn`). The param menu and the GRAPH page's `mod` pin
        menu (plan 28 N3) both draw it."""
        lrn = self.learn
        if lrn is None:
            imgui.text_disabled("no learn")
        elif lrn.learning == a.id:
            imgui.text_colored(RED, self._learn_hint())
            if imgui.menu_item_simple("Cancel learn"):
                lrn.arm(None)
        else:
            self._ctx_learn(a, p)

    def _ctx_learn(self, a: Param, p: Param) -> None:
        """The Learn items of a param not armed (plan 17 WP2, fork 5).
        **Learn desk**: wherever a desk row can go — not a file path, not
        SHIFT's own param, not a meta param (what `ui_routing._desk_targets`
        leaves out) — with or without a MIDI adapter. **Learn hand ▸ left /
        right**: only with a tracker, on a param a hand can drive (the real
        one is modulatable and no meta param), for the sides the meta controller's
        axes have. **Learn pad**: while a gamepad is connected, wherever a
        pad button can go (`ui_routing.pad_target`, a meta param too) — a
        button, the D-pad, a stick or a trigger completes it
        (`gamepad.learn_from`). **Route from ▸** (the owner, 2026-10-24:
        "there is no Learn option for routing one of the LFOs there";
        2026-10-28: one submenu per kind, the macros among them): on a
        modulatable param that is no trigger, **LFO ▸** and **envelope ▸**
        — the bank's voices, the one already driving it checked, then new
        LFO / new envelope — and on a param a base subscriber may name,
        **macro ▸** — the meta controller's knobs by label, one already setting it
        checked; a pick is the cable a drag on GRAPH makes
        (`ui_graph.route_from_menu`). It sits after the Learn items, before
        Learn sink, and is no Learn: an LFO has no gesture to wait for.

        **With players** (plan 55's meta controller and a device registry: the
        app), the Learn items are one submenu (the owner, 2026-11-07: "nested
        by player … dynamically based on which controller is routed to which
        player"): **Learn ▸ Learn Player 1–4 ▸** each controller that player
        holds, by name (`_learn_player`), which only that controller completes
        (`learn.only_want`); then **Any desk** (the old Learn desk: any MIDI
        desk, or a click on the desk diagram) and the pad's pair learns. A rig
        with no players keeps the flat items below."""
        lrn = cast(learn.Learn, self.learn)
        if getattr(self, "meta", None) is not None and getattr(self, "devices", None) is not None:
            if imgui.begin_menu("Learn"):
                for n in players_mod.NUMBERS:
                    self._learn_player(a, p, n)
                imgui.separator()
                if self._desk_target(a) and imgui.menu_item_simple("Any desk"):
                    lrn.arm(a.id, "desk")
                self._learn_pairs(a, p)
                # plugged in, held by nobody (the board's tray): said, so it is found
                for h in ui_players.tray(self):
                    imgui.text_disabled(f"{h.name}: nobody holds it — press "
                                        f"{ui_players.KEY} and drag it to a player")
                imgui.end_menu()
            ui_graph.route_from_menu(self, p)
            self._learn_sinks(a, p)
            return
        if self._desk_target(a) and imgui.menu_item_simple("Learn desk"):
            lrn.arm(a.id, "desk")
        sides = self._hand_sides() if ui_routing.route_target(p) else []
        if sides and imgui.begin_menu("Learn hand"):
            for side in sides:
                if imgui.menu_item_simple(side):
                    lrn.arm(a.id, f"hand:{side}")
            imgui.end_menu()
        pad = getattr(self, "pad", None)
        if (pad is not None and pad.on and ui_routing.pad_target(a)
                and imgui.menu_item_simple("Learn pad")):
            lrn.arm(a.id, "pad")
        self._learn_pairs(a, p)
        # any other device the registry lists can be armed for by its role
        # (plan 27 B2, `Learn.wants`): "Learn <role>", on a param a lane
        # can drive; the device completes it from its own `learn`
        if ui_routing.route_target(p):
            for want in learn_wants(lrn):
                if imgui.menu_item_simple(f"Learn {want}"):
                    lrn.arm(a.id, want)
        # the owner, 2026-10-24: an LFO or an envelope onto the param — no
        # gesture to wait for, so not a Learn; the cable a drag on GRAPH
        # makes (`ui_graph.route_from_menu`)
        ui_graph.route_from_menu(self, p)
        self._learn_sinks(a, p)

    def _learn_pairs(self, a: Param, p: Param) -> None:
        """plan 56: two presses, one axis. A pair moves along a range, so a
        param with one; "(spring)" a route, on what a route can carry."""
        lrn, pad = self.learn, getattr(self, "pad", None)
        if pad is not None and pad.on and self._desk_target(a) and p.kind in (
                Kind.CONTINUOUS, Kind.ENUM):
            if imgui.menu_item_simple("Learn pair"):
                lrn.arm(a.id, learn.PAIR_WANT)
            if (p.modulatable and p.kind is Kind.CONTINUOUS and not p.integer
                    and imgui.menu_item_simple("Learn pair (spring)")):
                lrn.arm(a.id, learn.PAIR_SPRING_WANT)

    def _learn_sinks(self, a: Param, p: Param) -> None:
        """plan 27 B3: the param *out* to a sink port — the meta controller's ports
        (`Learn.sinks`), a pick lands at once as a meta row
        (`Learn.learn_sink`): no prompt, no undo step, no loadable patch dirt."""
        lrn = self.learn
        ports = sink_items(lrn) if p.kind is not Kind.TRIGGER else []
        if ports and imgui.begin_menu("Learn sink"):
            for address, text in ports:
                if imgui.menu_item_simple(text):
                    lrn.learn_sink(a.id, address)
            imgui.end_menu()

    def player_learns(self, a: Param, p: Param, number: int) -> list[tuple[str, str | None]]:
        """Learn ▸ Learn Player `number`'s items: (label, want) for each
        controller the player holds that can drive this param — a MIDI desk
        wherever a desk row can go, a pad wherever a pad row can, the hands
        on a param a hand can drive (one item per side: ``Ultraleap hands ·
        left``), any other device on a param a lane can drive. Each arms
        what only that controller completes (`learn.only_want`; the hands'
        own side). A controller not connected has want None: drawn, not
        armable. A plain function of the rig, so a test reads it."""
        out: list[tuple[str, str | None]] = []
        for h, d in ui_players.learnable(self, number):
            kind = getattr(d, "kind", "")
            on = h.state == "on"
            name = h.name if h.name.lower() == h.role.lower() else f"{h.name}  ·  {h.role}"
            if kind == "hands":
                sides = self._hand_sides() if ui_routing.route_target(p) else []
                out += [(f"{name}  ·  {side}", f"hand:{side}" if on else None) for side in sides]
                continue
            fits = (self._desk_target(a) if kind == "midi"
                    else ui_routing.pad_target(a) if kind == "gamepad"
                    else ui_routing.route_target(p))
            if fits:
                out.append((name if on else f"{name}  ·  not connected",
                            learn.only_want(h.role) if on else None))
        return out

    def _learn_player(self, a: Param, p: Param, number: int) -> None:
        """One player's submenu (`player_learns`), greyed when it holds nothing
        that can drive this param."""
        items = self.player_learns(a, p, number)
        if not imgui.begin_menu(f"Learn Player {number}", bool(items)):
            return
        for label, want in items:
            if imgui.menu_item(label, "", False, want is not None)[0] and want is not None:
                cast(learn.Learn, self.learn).arm(a.id, want)
        imgui.end_menu()

    def _hand_sides(self) -> list[str]:
        """The hands this meta controller's axes belong to, left first; none without a
        tracker."""
        axes = getattr(self.hands, "axes", None) or []
        return [s for s in ("left", "right") if any(getattr(x, "side", None) == s for x in axes)]

    def _learn_hint(self) -> str:
        """What the armed learn waits for (its `want`, plan 17 WP2), in the
        words the menu, the footer, ROUTING and SYSTEM all print. A bare
        learn (`want` None) waits for whatever this rig has."""
        want = getattr(self.learn, "want", None)
        only = getattr(self.learn, "_only_device", lambda w: None)(want)
        if only is not None:            # Learn ▸ Learn Player n ▸ <controller>
            name = ui_players.device_words(only)
            kind = getattr(only, "kind", "")
            if kind == "midi":
                diagram = (str((getattr(only, "entry", None) or {}).get("profile") or "apc40")
                           == "apc40" and hasattr(ui_desk, "click"))
                return (f"turn a knob, move a fader or press a button on {name}"
                        + (", or click one on the diagram…" if diagram else "…"))
            if kind == "gamepad":
                return f"press a button or push a stick or a trigger on {name}…"
            return f"move a control on {name}…"
        if want == "desk":
            # a click on the on-screen desk completes it once the desk is
            # clickable (plan 17 WP4: `ui_desk.click`)
            knob, click = self.midi is not None, hasattr(ui_desk, "click")
            if knob and click:
                return "turn a knob or press a button on the desk, or click one on the diagram…"
            if knob:
                return "turn a knob or press a button on the desk…"
            if click:
                return "click a control on the desk diagram…"
            return "nothing to learn from (no MIDI)"
        if want in ("hand:left", "hand:right"):
            return f"move the {want.partition(':')[2]} hand…"
        if want == "pad":
            return "press a pad button or the D-pad, or push a stick or a trigger…"
        if want in learn.PAIR_WANTS:
            first = self.learn.__dict__.get("pair_first")
            return (f"{first} is the + pole: press the − pole…" if first
                    else "press the + pole, then the − pole…")
        knob, hand = self.midi is not None, self.hands is not None
        if knob and hand:
            return "move a control or a hand…"
        if hand:
            return "move a hand…"
        if knob:
            return "move a control…"
        return "nothing to learn from (no MIDI, no hands)"

    def _learn_frame(self, p: Param) -> None:
        """Red outline around the last item while it is armed to learn."""
        if self.learn is None or self.learn.learning != p.id:
            return
        self._frame_item()

    @staticmethod
    def _frame_item() -> None:
        """The learn's red outline around the last item (armed to learn;
        the target of a picked desk control)."""
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        dl = imgui.get_window_draw_list()
        dl.add_rect(
            imgui.ImVec2(r0.x - 2, r0.y - 2), imgui.ImVec2(r1.x + 2, r1.y + 2),
            u32(RED), ROUND + 2, 2.0,
        )

    def _tip(self, p: Param, text: str | Callable[[], str] | None = None) -> None:
        """Tooltip on the last item: the param's tip, a string, or a
        callable built only on hover (a table lookup for every widget
        every frame is not worth it)."""
        if not imgui.is_item_hovered():
            return
        t = p.tip if text is None else (text() if callable(text) else text)
        if t:
            tooltip(t)

    # ---- modulation ghosts: the base is the handle, the effective a white bar ----

    @staticmethod
    def _eff_text(p: Param) -> str:
        """The effective value's readout, in the param's own format."""
        v = p.value
        if p.kind is Kind.CONTINUOUS:
            return p.fmt(v)
        if p.kind is Kind.ENUM:
            names = p.names
            return names[v] if 0 <= v < len(names) else "—"
        if p.kind is Kind.TOGGLE:
            return "on" if v else "off"
        return ""

    def _performer(self, p: Param) -> str:
        """Who performs `p` — "performed by <row>" from the table's owner,
        named as its adapter names it ("R height positions",
        `Router.describe`), or "" with no router attached or no owner (a
        source the table doesn't name, a test holding the param by hand)."""
        r = self.router
        b = r.performer_of(p.id) if r is not None else None
        return "" if b is None else f"performed by {r.describe(b)}"

    def _mod_text(self, p: Param) -> str:
        """`base → effective` — a modulated param's readout."""
        return f"{p.text()} → {self._eff_text(p)}"

    def _mod_line(self, p: Param) -> str:
        """The tooltip's line: the readout with its label and who is doing it."""
        who = self._performer(p)
        text = f"{p.label}: {self._mod_text(p)}"
        return f"{text}, {who}" if who else f"{text} (modulated)"

    def _hint(self, a: Param, p: Param) -> str:
        """A widget's tooltip: its tip, plus the modulation line while a
        source rides it (`a` is the drawn param, `p` the one it reads).
        Built on hover only — pass it to _tip as a callable."""
        if not p.modulated:
            return a.tip
        line = self._mod_line(p)
        return f"{a.tip}\n{line}" if a.tip else line

    def _ghost(self, p: Param, inset: float = 0.0) -> None:
        """A white bar over the last slider at the effective position."""
        if not p.modulated:
            return
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        x0, span = self._throw(r0, r1, inset)
        x = x0 + span * p.eff_norm
        dl = imgui.get_window_draw_list()
        dl.add_rect_filled(imgui.ImVec2(x - 1.5, r0.y + 3), imgui.ImVec2(x + 1.5, r1.y - 3),
                           u32(GHOST), 1.5)
        self.ghosts += 1

    def _mod_dot(self, p: Param) -> None:
        """A red dot in the corner of the last item: a discrete param is being driven."""
        if not p.modulated:
            return
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        dl = imgui.get_window_draw_list()
        dl.add_circle_filled(imgui.ImVec2(r1.x - 5, r0.y + 5), 3.5, u32(RED))
        if imgui.is_item_hovered():
            tooltip(self._mod_line(p))
        self.ghosts += 1

    # ---- the track: every slider's rounded ground and red value fill ----

    @staticmethod
    def _grab_half(width: float, steps: int = 0) -> float:
        """Half the grab plus imgui's 2 px grab padding: how far in from
        either end of the frame the grab's centre travels. An integer slider
        with few steps widens its grab to a step's share of the throw."""
        s = imgui.get_style()
        usable = width - 4.0
        g = s.grab_min_size
        if steps:
            g = max(usable / (steps + 1), g)
        return min(g, usable) / 2 + 2.0

    @staticmethod
    def _origin(p: Param) -> float:
        """Where the fill starts: zero on a range that spans it, else the left end."""
        if p.kind is Kind.CONTINUOUS and p.lo < 0 < p.hi and not p.log:
            try:
                return p._norm_of(0.0)
            except Exception:  # noqa: BLE001 — a taper that cannot place 0
                return 0.0
        return 0.0

    def _track(self, draw, norm: float, origin: float = 0.0, steps: int = 0,
               knob: bool = True) -> tuple:
        """Draw a slider through `draw()` over a rounded track filled red
        from `origin` to `norm` (both 0..1 along the throw); returns what
        draw() returned.

        The slider draws on the upper channel with its own frame colours
        made clear, and the track goes in underneath once the item's rect
        and hover state are known — so the grab and the readout sit on top
        of the fill without imgui needing a filled-slider widget. Without
        `knob` the grab is clear too and a bright edge under the fill's end
        marks the value, so a readout drawn inside is never red-on-red.
        """
        dl = imgui.get_window_draw_list()
        dl.channels_split(2)
        dl.channels_set_current(1)
        clear = imgui.ImVec4(0, 0, 0, 0)
        cols = [imgui.Col_.frame_bg, imgui.Col_.frame_bg_hovered, imgui.Col_.frame_bg_active]
        if not knob:
            cols += [imgui.Col_.slider_grab, imgui.Col_.slider_grab_active]
        for c in cols:
            imgui.push_style_color(c, clear)
        out = draw()
        imgui.pop_style_color(len(cols))
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        active, hovered = imgui.is_item_active(), imgui.is_item_hovered()
        dl.channels_set_current(0)
        bg = (imgui.Col_.frame_bg_active if active else
              imgui.Col_.frame_bg_hovered if hovered else imgui.Col_.frame_bg)
        dl.add_rect_filled(r0, r1, imgui.get_color_u32(bg), ROUND)
        half = self._grab_half(r1.x - r0.x, steps)
        x0, span = self._throw(r0, r1, half)
        xa = x0 + span * origin
        xb = x0 + span * min(max(norm, 0.0), 1.0)
        lo, hi = min(xa, xb), max(xa, xb)
        if lo == r0.x + half:
            lo = r0.x               # a fill from the left end runs into the corner
        if hi - lo > 0.5:
            flags = imgui.ImDrawFlags_.round_corners_left if lo == r0.x else 0
            dl.add_rect_filled(imgui.ImVec2(lo, r0.y), imgui.ImVec2(hi, r1.y), u32(FILL),
                               ROUND if flags else 0.0, flags)
        if not knob:
            edge = imgui.ImVec4(1.0, 0.45, 0.45, 1) if active or hovered else RED
            dl.add_rect_filled(imgui.ImVec2(xb - 2, r0.y + 3), imgui.ImVec2(xb + 2, r1.y - 3),
                               u32(edge), 2.0)
        dl.channels_merge()
        return out

    # ---- Shift-drag fine mode (wave 2 T2): a tenth of the drag ----

    def _fine_frame(self) -> None:
        """Once a frame, before any widget: read ⇧ and the button once,
        and forget a fine drag whose button is up — whether or not its
        slider is still drawn (a page change mid-drag leaves nothing)."""
        io = imgui.get_io()
        self._shift = io.key_shift
        self._mouse_down = imgui.is_mouse_down(0)
        if not self._mouse_down:
            self._fine_drag = None

    def _fine(self, p: Param, t0: float, x0: float, span: float) -> tuple[bool, float | None]:
        """After a continuous slider's draw: `(own, t)` — `own` when a
        Shift drag holds this slider (imgui's write this frame is to be
        dropped), `t` the throw fraction (0..1) to write, or None to write
        nothing. `(False, None)` lets imgui's own drag stand; an integer
        never has the mode.

        imgui's sliders are absolute — the grab goes where the mouse is —
        and have no slow modifier (Alt slows only a *drag* widget, and
        Shift speeds one up), so the panel moves the value itself: the
        drag that ⇧ joins is taken over from the value it had, and each
        frame the mouse moves adds its movement along the throw × `FINE`
        while ⇧ is held, × 1 once it is let go — relative until the
        button comes up, so neither edge jumps. On the press's own frame
        nothing is written (the slider's jump to the mouse is dropped, and
        a base between detents, or on a log range, stays exactly as it
        was); joined mid-drag, the mouse's last-frame place is the anchor,
        so this frame's movement counts at the fine rate. `t0` is the
        value before this frame's imgui write; `x0`, `span` the throw
        (`_throw`). One drag is one undo step: the writes come every frame
        the mouse moves, as a plain drag's do (`undo.SETTLE_S`)."""
        if p.integer:
            return False, None
        return self._fine_throw(t0, span)

    def _fine_throw(self, t0: float, span: float) -> tuple[bool, float | None]:
        """`_fine` for the item just drawn, whatever it writes to."""
        if not imgui.is_item_active():
            return False, None
        shift = getattr(self, "_shift", False)
        if not getattr(self, "_mouse_down", False):
            return False, None          # a typed value (Ctrl+click): imgui's
        io = imgui.get_io()
        key = imgui.get_item_id()
        st = getattr(self, "_fine_drag", None)
        if st is None or st["id"] != key:
            if not shift:
                return False, None
            x = io.mouse_pos.x if imgui.is_item_activated() else io.mouse_pos_prev.x
            st = self._fine_drag = {"id": key, "x": x, "t": t0,
                                    "lo": min(t0, 0.0), "hi": max(t0, 1.0)}
        x = io.mouse_pos.x
        moved, st["x"] = x - st["x"], x
        if moved == 0 or span <= 0:
            return True, None
        st["t"] = min(max(st["t"] + moved / span * (FINE if shift else 1.0), st["lo"]), st["hi"])
        return True, st["t"]

    @staticmethod
    def _throw(r0, r1, half: float) -> tuple[float, float]:
        """Where a slider's grab centre travels: its left end and length
        in screen px, `half` in from either end of the frame."""
        return r0.x + half, r1.x - r0.x - 2 * half

    def _raw_slider(self, key: str, value: float, lo: float, hi: float, fmt: str, tip: str,
                    width: float = -1, log: bool = False, dim: bool = False,
                    num: bool = True) -> tuple[bool, float]:
        """A float slider with no `Param` behind it (a route's depth, GRAPH's
        backdrop; row 731): `(changed, value)`, as `imgui.slider_float` gives
        them, with ⇧-drag fine mode and its tooltip. Drawn as `Panel._slider`
        draws a param's, and for the same reason: the readout and the fill
        are the value's, where imgui's own would follow the mouse through a
        fine drag. `log` when the throw is logarithmic (`lo` > 0); `num` for
        the readouts' face, off for words that need the room. A value a
        file left outside the range is not pulled in by a fine drag: it can
        come in, and go no further out."""
        if ui_kit.ready():              # on the kit (hyperspace/dkit): a track, its readout beside
            return ui_fields.inline_raw(self, key, value, lo, hi, fmt, tip, width, log, dim, num)
        value = float(value)
        log = log and lo > 0
        t0 = (math.log(max(value, lo) / lo) / math.log(hi / lo) if log
              else (value - lo) / ((hi - lo) or 1.0))
        origin = -lo / (hi - lo) if lo < 0 < hi else 0.0
        text = (fmt % value).replace("%", "%%")
        flags = imgui.SliderFlags_.logarithmic if log else 0
        imgui.set_next_item_width(width)
        if num:
            imgui.push_font(_FONTS["num"], FONT_NUM)
        if dim:
            imgui.push_style_color(imgui.Col_.text, DIM)
        changed, v = self._track(
            lambda: imgui.slider_float(f"##{key}", value, lo, hi, text, flags),
            t0, origin, knob=False)
        if dim:
            imgui.pop_style_color()
        if num:
            imgui.pop_font()
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        own, t = self._fine_throw(t0, self._throw(r0, r1, self._grab_half(r1.x - r0.x))[1])
        if own:
            changed = t is not None     # a frame the mouse did not move writes nothing
            v = value if t is None else lo * (hi / lo) ** t if log else lo + t * (hi - lo)
        shift = getattr(self, "_shift", False)
        st = getattr(self, "_fine_drag", None)
        hovered = imgui.is_item_hovered()
        if shift and not hovered and st is not None and st["id"] == imgui.get_item_id():
            tooltip(FINE_TIP)
        elif hovered:
            tooltip(f"{FINE_TIP}\n{tip}" if shift else tip)
        if changed:
            undo.by_hand(True)          # (typed into it: row 757)
        return changed, v

    def _fine_tip(self, a: Param, p: Param) -> None:
        """The slider's tooltip, led by "FINE" while ⇧ is held over a
        control that has a fine mode (continuous, not an integer), and
        shown alone while a fine drag goes on off the track, where no
        hover would show it."""
        if p.integer or not getattr(self, "_shift", False):
            self._tip(a, lambda: self._hint(a, p))
            return
        st = getattr(self, "_fine_drag", None)
        if st is not None and st["id"] == imgui.get_item_id() and not imgui.is_item_hovered():
            tooltip(FINE_TIP)
            return
        self._tip(a, lambda: "\n".join(t for t in (FINE_TIP, self._hint(a, p)) if t))

    # ---- widgets: each one reads, draws and writes a Param ----

    def _real(self, p: Param) -> Param:
        """The param behind a band.sel.* alias — where the base and the
        modulation state live. An alias reads the object, so through it a
        fader would show the *effective* value and write the base back."""
        return self.reg.real(p)

    def _fader(self, pid: str) -> bool:
        """Full-width taper fader: label and readout over a filled track, detent notch."""
        if ui_kit.ready():              # on the kit (hyperspace/dkit): a slider field
            return ui_fields.inline_fader(self, pid)
        a = self.reg[pid]           # what the widget is: id, label, tip, binding
        p = self._real(a)           # what it reads and writes
        pos = p.position()
        imgui.push_id(pid)
        tag = ("log" if p.taper.log else "lin") if p.taper is not None else "lin"
        # readout: the setting, or `base → effective` while a lane rides it.
        # In a narrow column (the band strip) the taper tag goes first, then
        # the readout moves inside the fader frame, so nothing overprints.
        text = self._mod_text(p) if p.modulated else p.text()
        avail = imgui.get_content_region_avail().x
        tw = _readout_width(text)
        tag_w = _micro_width(f"  ·  {tag}")
        show_tag = _micro_width(a.label) + tag_w + tw + 16 <= avail
        inside = _micro_width(a.label) + tw + 16 > avail
        # label and readout share a baseline: the label steps down by the
        # difference in the two faces' sizes
        y0 = imgui.get_cursor_pos_y()
        drop = (FONT_NUM - FONT_MICRO) * 0.8
        imgui.set_cursor_pos_y(y0 + drop)
        _micro(a.label)
        self._tip(a)
        self._ctx_label(a)      # the label opens the menu the fader's `_ctx` draws
        if show_tag:
            imgui.same_line(0, 0)
            imgui.set_cursor_pos_y(y0 + drop)
            _micro(f"  ·  {tag}", FAINT)
        if not inside:
            imgui.same_line(avail - tw - 2)
            imgui.set_cursor_pos_y(y0)
            _readout(text, RED if p.modulated else None)
        imgui.set_next_item_width(-1)
        imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(10, 8))
        imgui.push_font(_FONTS["num"], FONT_NUM)
        t0 = p.norm
        changed, pos2 = self._track(
            lambda: imgui.slider_int(f"##{pid}", pos, 0, p.steps,
                                     text.replace("%", "%%") if inside else ""),
            p.norm, self._origin(p), p.steps, knob=not inside,
        )
        imgui.pop_font()
        imgui.pop_style_var()
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        half = self._grab_half(r1.x - r0.x, p.steps)
        x0, span = self._throw(r0, r1, half)
        own, t = self._fine(p, t0, x0, span)
        if own:
            changed, pos2 = t is not None, pos if t is None else round(t * p.steps)
        self._fine_tip(a, p)
        self._ctx(a)
        self._learn_frame(a)
        if p.taper is not None and p.taper.unity is not None:
            # detent notch: ticks at the fader position the grab centre
            # occupies at unity (frame inset by grab padding + half grab)
            nx = x0 + span * p.taper.unity / p.steps
            dl = imgui.get_window_draw_list()
            notch = u32(imgui.ImVec4(1, 1, 1, 0.55))
            dl.add_line(imgui.ImVec2(nx, r0.y + 2), imgui.ImVec2(nx, r0.y + 6), notch, 2.0)
            dl.add_line(imgui.ImVec2(nx, r1.y - 6), imgui.ImVec2(nx, r1.y - 2), notch, 2.0)
        self._ghost(p, half)
        imgui.pop_id()
        if changed and pos2 != pos:
            undo.by_hand(True)          # (typed into it: row 757)
            p.set_position(pos2)
            return True
        return False

    def _slider(self, pid: str, width: float = -1) -> bool:
        """Compact slider with the readout inside. A tapered range slides
        over its detents (the instance count's), as a fader does."""
        if ui_kit.ready():              # on the kit (hyperspace/dkit): a track, its readout beside
            return ui_fields.inline_slider(self, pid, width)
        a = self.reg[pid]
        p = self._real(a)
        imgui.set_next_item_width(width)
        v = p.base
        # the readout is imgui's printf format: a "%" in it ("60%") is doubled
        text = (self._mod_text(p) if p.modulated else p.text()).replace("%", "%%")
        imgui.push_font(_FONTS["num"], FONT_NUM)
        t0 = p.norm
        if p.taper is not None:
            steps = p.steps
            changed, pos = self._track(lambda: imgui.slider_int(
                f"##{pid}", p.position(), 0, steps, text),
                p.norm, self._origin(p), steps, knob=False)
            nv = p.taper.map(pos)
        elif p.integer:
            steps = int(p.hi) - int(p.lo)
            changed, nv = self._track(lambda: imgui.slider_int(
                f"##{pid}", int(v), int(p.lo), int(p.hi), text),
                p.norm, self._origin(p), steps, knob=False)
        else:
            steps = 0
            flags = imgui.SliderFlags_.logarithmic if p.log else 0
            changed, nv = self._track(lambda: imgui.slider_float(
                f"##{pid}", float(v), p.lo, p.hi, text, flags),
                p.norm, self._origin(p), knob=False)
        imgui.pop_font()
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        half = self._grab_half(r1.x - r0.x, steps)
        own, t = self._fine(p, t0, *self._throw(r0, r1, half))
        if own:
            changed = t is not None     # a frame the mouse did not move writes nothing
            if changed:
                # the throw fraction back to a value: a taper's detent, or
                # the untapered range's own (log) mapping, as the param reads it
                nv = (p.taper.map(round(t * steps)) if p.taper is not None
                      else p._value_of_norm(t))
        self._fine_tip(a, p)
        self._ctx(a)
        self._learn_frame(a)
        self._ghost(p, half)
        if changed:
            undo.by_hand(True)          # (typed into it: row 757)
            p.set_value(nv)
        return changed

    @staticmethod
    def _label_cell(text: str, color: imgui.ImVec4 | None = None,
                    width: float = LABEL_W) -> None:
        """A field label centred on the height of the control beside it.

        Drawn, not laid out: a dummy one control tall is the item (tooltips
        attach to it), so the row's height and baseline stay the control's
        and anything after it on the line lines up with the first control.
        `width` is the label column, measured from where the label starts:
        at a line's start (or a table cell's) that is the column every row
        shares, and after `same_line()` mid-line it is the label's own room
        — the control beside it never lands back over the line's start."""
        pos = imgui.get_cursor_screen_pos()
        fh = FONT_NUM + 2 * imgui.get_style().frame_padding.y
        words = text.upper()
        if ui_kit.ready():
            # cut to its column: the stock slider's opaque frame hid a label's
            # overflow, the kit's thin track does not ("KNOB SMOOTHING" ran
            # into its fill). The whole label is the cell's tooltip.
            words = fit_micro(text, width - LABEL_GAP, 0.0) or words[:1]
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        imgui.get_window_draw_list().add_text(
            imgui.ImVec2(pos.x, pos.y + (fh - FONT_MICRO) / 2 - 1),
            u32(DIM if color is None else color), words)
        imgui.pop_font()
        imgui.dummy(imgui.ImVec2(width - LABEL_GAP, fh))
        if words != text.upper() and imgui.is_item_hovered():
            tooltip(text)
        imgui.same_line(0, LABEL_GAP)

    def _row(self, pid: str, width: float = -1, label: str | None = None,
             label_w: float = LABEL_W) -> bool:
        """A labelled compact slider: label in a column, slider beside it —
        or, for an enum (whose write a slider's `set_value` refuses), its
        choices in a combo."""
        p = self.reg[pid]
        self._label_cell(p.label if label is None else label, width=label_w)
        self._ctx_label(p)      # the label opens the menu the slider's `_ctx` draws
        if self._real(p).kind is Kind.ENUM:
            return self._combo(pid, width)
        return self._slider(pid, width)

    def half(self, pid: str, label: str | None = None, label_w: float = HALF_LABEL_W) -> bool:
        """`_row` for a half-width table cell: a short label in a narrow column."""
        return self._row(pid, label=label, label_w=label_w)

    def _lane_plane(self, i: int) -> str:
        """The meter tooltip's suffix: which rotation planes lane `i` drives,
        read from the live table's ``rot.rate.*`` rows — none, no suffix. A
        push row has a direction (the sign of its depth); a position row
        only names the plane."""
        router = self.router
        if router is None:
            return ""
        planes = []
        for b in router.table.of("lane"):
            if b.index == i and b.enabled and b.target.startswith("rot.rate."):
                plane = b.target.rsplit(".", 1)[-1]
                if b.op == "push":
                    plane += " forward" if b.value >= 0 else " reverse"
                planes.append(plane)
        return f" → {', '.join(planes)}" if planes else ""

    def _combo(self, pid: str, width: float = -1, tip: str | None = None,
               rows: int = -1) -> bool:
        """A drop-down of the enum's choices; `rows` the most the list shows
        before it scrolls (imgui's default, eight, at -1)."""
        if ui_kit.ready():              # on the kit (hyperspace/dkit): a Select, short enums
            got = ui_fields.inline_select(self, pid, width, tip)
            if got is not None:
                return got
        a = self.reg[pid]
        p = self._real(a)
        imgui.set_next_item_width(width)
        changed, i = imgui.combo(f"##{pid}", p.base, p.names, rows)
        self._tip(a, tip)
        self._ctx(a)
        self._learn_frame(a)
        self._mod_dot(p)
        if changed:
            p.set(i)
        return changed

    def _shape_combo(self) -> bool:
        """view.shape as a menu grouped by kind (geometry.menu): 4D, 3D and
        Scenes, each in families — regular polytopes, Platonic solids … —
        in index order. The index stays the shape's identity — a loadable patch
        holds it — so only the menu groups them."""
        a = self.reg["view.shape"]
        p = self._real(a)
        cur = int(p.base)
        changed = False
        imgui.set_next_item_width(-1)
        # as tall as the window allows: the groups are the point of it
        if imgui.begin_combo("##view.shape", p.names[cur], imgui.ComboFlags_.height_largest):
            section = None
            for sec, fam, ids in menu():
                if sec != section:
                    imgui.separator_text(sec)
                    section = sec
                if fam != sec:
                    imgui.text_colored(FAINT, f"  {fam}")
                for i in ids:
                    hit, _ = imgui.selectable(f"    {SHAPES[i].name}##shape{i}", i == cur)
                    if i == cur:
                        imgui.set_item_default_focus()
                    if hit and i != cur:
                        p.set(i)
                        changed = True
            imgui.end_combo()
        self._tip(a)
        self._ctx(a)
        self._learn_frame(a)
        self._mod_dot(p)
        return changed

    def _check(self, pid: str, label: str | None = None) -> bool:
        if ui_kit.ready():              # on the kit (hyperspace/dkit): a Switch, the same room
            return ui_fields.inline_check(self, pid, label)
        a = self.reg[pid]
        p = self._real(a)
        text = a.label if label is None else label
        changed, on = imgui.checkbox(f"{text}##{pid}", bool(p.base))
        self._tip(a)
        self._ctx(a)
        self._learn_frame(a)
        self._mod_dot(p)
        if changed:
            p.set(on)
        return changed

    def _button(self, pid: str, label: str | None = None, small: bool = False) -> bool:
        if ui_kit.ready():              # on the kit (hyperspace/dkit): a Button, the same room
            return ui_fields.inline_button(self, pid, label, small)
        p = self.reg[pid]
        text = f"{p.label if label is None else label}##{pid}"
        hit = chip(text) if small else imgui.button(text)
        self._tip(p)
        self._ctx(p)
        self._learn_frame(p)
        if hit:
            p.toggle()  # fires a trigger, flips a toggle
        return hit

    def _lit_button(self, pid: str, label: str, lit: bool, color: imgui.ImVec4 | None = None,
                    width: float = 0.0) -> bool:
        """A toggle drawn as a chip that goes solid red while on (plane keys, the loadable patch bank)."""
        p = self.reg[pid]
        # its own id space: the same param often has a check or slider on the
        # same page (the FX strip under its chip), and two visible items with
        # one id is an imgui conflict
        hit = lit_chip(f"{label}##chip.{pid}", lit, color, imgui.ImVec2(width, 0))
        self._tip(p)
        self._ctx(p)
        self._learn_frame(p)
        self._mod_dot(p)
        if hit:
            p.toggle()
        return hit

    def _path(self, pid: str, clear: bool = True) -> None:
        """A Kind.TEXT param (a file path): read-only name, full path on hover."""
        p = self.reg[pid]
        v = p.base or ""
        imgui.align_text_to_frame_padding()
        imgui.text_colored(TEXT if v else FAINT, v.rsplit("/", 1)[-1][:28] if v else "none")
        self._tip(p, v or p.tip)
        self._ctx(p)
        self._learn_frame(p)
        if v and clear:
            imgui.same_line()
            if chip(f"clear##{pid}"):
                p.set("")

    # ---- sections: a title, the group's preset strip, a rule ----

    def _section(self, title: str, group: str | None = None, note: str | None = None) -> None:
        """Header of a section. `group` draws the library's strip for it; a
        section whose params are saved by another group says so in `note`."""
        _micro(title, TEXT)
        if note:
            # plan 49 stage 2: cut to what the title leaves it (the side pane)
            room = imgui.get_content_region_avail().x - _micro_width(title) - 16
            if _micro_width(note) > room:
                note = fit_micro(note, room, 24.0)
        if note:
            flush_right(_micro_width(note) + 4)
            _micro(note, FAINT)
        lib = self.library
        if group is not None and lib is not None and lib.reg is not None:
            ui_loadable.strip(self, group)
        imgui.separator()
        imgui.dummy(imgui.ImVec2(0, 1))

    # ---- overlays ----

    def _draw_cheatsheet(self) -> None:
        io = imgui.get_io()
        imgui.set_next_window_pos(
            imgui.ImVec2(12, io.display_size.y - 12), imgui.Cond_.always, imgui.ImVec2(0, 1)
        )
        imgui.set_next_window_bg_alpha(0.6)
        flags = (
            imgui.WindowFlags_.no_decoration
            | imgui.WindowFlags_.always_auto_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_focus_on_appearing
            | imgui.WindowFlags_.no_nav
        )
        imgui.push_style_var(imgui.StyleVar_.item_spacing, imgui.ImVec2(8, 4))
        imgui.begin("##cheatsheet", None, flags)
        col = max(_readout_width(key) for key, _ in CHEATSHEET)
        x0 = imgui.get_cursor_pos_x()
        right = 0.0
        for key, action in CHEATSHEET:
            imgui.set_cursor_pos_x(x0 + col - _readout_width(key))
            _readout(key, RED)
            imgui.same_line(x0 + col + 14)
            imgui.text_colored(DIM, action)
            right = max(right, imgui.get_item_rect_max().x)
        # the desk sits above it (ui_desk). The height is taken from the
        # rows just laid out, not `get_window_height()`: on the sheet's
        # first frame the window has no size yet, and the desk would be
        # drawn one frame in the wrong place (plan 16 WP7)
        style = imgui.get_style()
        self._sheet_h = (imgui.get_cursor_pos_y() - style.item_spacing.y
                         + style.window_padding.y)
        # …and its width the same way: with the panel hidden the desk
        # sits beside the sheet (ui_desk.room, plan 17 WP4)
        self._sheet_w = right - imgui.get_window_pos().x + style.window_padding.x
        imgui.end()
        imgui.pop_style_var()

    # ---- meters ----

    def _meters(self, dt: float) -> None:
        # meter geometry per the reference (.meters / .meter .bar CSS):
        # six full-width bars, 4 px apart, 78 px tall, two columns inside
        # with a 1 px gap; red zone panes stack above the knee and nominal
        # lines so the bar reads as working range / headroom / peak zone.
        a = self.audio.chain
        dl = imgui.get_window_draw_list()
        origin = imgui.get_cursor_screen_pos()
        gap, mh = 4.0, 78.0
        n = a.n   # the analyzer's N bands; the strip draws whatever it has
        bw = (imgui.get_content_region_avail().x - (n - 1) * gap) / n
        zone = u32(imgui.ImVec4(1.0, 43 / 255, 43 / 255, 0.07))
        blink = (imgui.get_time() % 0.62) < 0.31  # the 620 ms annunciator
        for i, name in enumerate(a.band_names):
            x0 = origin.x + i * (bw + gap)
            y1 = origin.y + mh
            sel = i == self.control.selb
            # headroom zones, stacked: one pane down to nominal, one to knee
            for lv in (NOM, KNEE):
                dl.add_rect_filled(
                    imgui.ImVec2(x0 + 1, origin.y + 1),
                    imgui.ImVec2(x0 + bw - 1, y1 - 1 - lv / CEIL * (mh - 2)),
                    zone,
                )
            for col, (val, pin) in enumerate(
                ((a.inp[i], self.pin_in), (a.out[i], self.pin_out))
            ):
                colw = (bw - 2 - 1) / 2  # 1 px frame each side, 1 px between
                cx0 = x0 + 1 + col * (colw + 1)
                cx1 = cx0 + colw
                hh = min(val, CEIL) / CEIL * (mh - 2)
                fill = (0.92, 0.92, 0.92, 0.9) if col == 0 else (1.0, 43 / 255, 43 / 255, 0.9)
                dl.add_rect_filled(
                    imgui.ImVec2(cx0, y1 - 1 - hh), imgui.ImVec2(cx1, y1 - 1),
                    u32(imgui.ImVec4(*fill)),
                )
                # over annunciator: a blinking cap on the driven column —
                # the ceiling is an asymptote, a column only sits against
                # the top by being pushed there
                pin[i] = pin[i] + dt if val >= PIN_AT else 0.0
                if pin[i] >= PIN_HOLD:
                    cap = u32(imgui.ImVec4(1.0, 43 / 255, 43 / 255, 1.0 if blink else 0.15))
                    dl.add_rect_filled(
                        imgui.ImVec2(cx0, origin.y + 1),
                        imgui.ImVec2(cx1, origin.y + 4),
                        cap,
                    )
            # landmark hairlines over everything: nominal white, knee red
            for lv, cc in ((NOM, (1, 1, 1, 0.32)), (KNEE, (1.0, 43 / 255, 43 / 255, 0.38))):
                ly = y1 - 1 - lv / CEIL * (mh - 2)
                dl.add_line(imgui.ImVec2(x0 + 1, ly), imgui.ImVec2(x0 + bw - 1, ly), u32(imgui.ImVec4(*cc)))
            # frame: the selected band's goes red and heavier
            dl.add_rect(
                imgui.ImVec2(x0, origin.y), imgui.ImVec2(x0 + bw, y1),
                u32(RED if sel else LINE), 4.0, 2.0 if sel else 1.0,
            )
            # click to select
            imgui.set_cursor_screen_pos(imgui.ImVec2(x0, origin.y))
            if imgui.invisible_button(f"##meter{i}", imgui.ImVec2(bw, mh)):
                self.reg["band.select"].set(i)
            if imgui.is_item_hovered():
                lo, hi = a.edges(i)
                tooltip(f"{name} {lo:.0f}–{hi:.0f} Hz{self._lane_plane(i)}")
            # every meter has the menu (plan 17 WP3), each under its own
            # key, so no two popups share an id with each other or with the
            # band combo's
            self._ctx(self.reg["band.select"], f".{i}")
            self._learn_frame(self.reg["band.select"])   # armed from a meter: framed on it
        # band tags, centred under their bars, in the micro face — smaller
        # where the widest would touch its neighbour (a narrow pane), and
        # the ones that still would left out: a meter's hover names its band
        def widest(px: float) -> float:
            imgui.push_font(_FONTS["micro"], px)
            w = max((imgui.calc_text_size(name).x for name in a.band_names), default=0.0)
            imgui.pop_font()
            return w
        imgui.push_font(_FONTS["micro"], tag_px(widest, bw + gap - TAG_GAP))
        right = origin.x + n * bw + (n - 1) * gap
        spans = []
        for i, name in enumerate(a.band_names):
            tw = imgui.calc_text_size(name).x
            x = origin.x + i * (bw + gap) + (bw - tw) / 2
            x = max(min(x, right - tw), origin.x)
            spans.append((x, x + tw))
        for i in tags_shown(spans, self.control.selb):
            imgui.set_cursor_screen_pos(imgui.ImVec2(spans[i][0], origin.y + mh + 4))
            imgui.text_colored(RED if i == self.control.selb else DIM, a.band_names[i])
        imgui.pop_font()
        imgui.set_cursor_screen_pos(imgui.ImVec2(origin.x, origin.y + mh + 4 + FONT_MICRO + 4))

    # ---- main draw: GRAPH and its side pane · footer ----

    def draw(self, dt: float, fps: float) -> None:
        try:
            self._fine_frame()      # ⇧ and the button, read once; a finished fine drag forgotten
            self._draw(dt, fps)
        finally:
            # the red banner, its own window, last and in front: a render
            # window that stopped or a dream worker that is off shows even
            # with the panel hidden or a page that raised
            self._alert_banner()

    def _draw(self, dt: float, fps: float) -> None:
        ui_pane.left(self)
        # Replace / Keep, its own window, before anything can return: a
        # held hand learn is never parked behind a hidden or collapsed panel
        ui_routing.modal(self)
        ui_browse.draw(self)    # the patches' file explorer, while it is up: its own window
        self.canvas_px = None   # the GRAPH page sets it when it draws (replay.grab reads it)
        ui_desk.tick(self)      # a picked control lets go by itself (ui_desk.PICK_S)
        ui_graph.settle(self)   # a loadable patch landed without the published node: let it go
        if self.cheatsheet:
            self._draw_cheatsheet()
        # the pad first: the desk reads its height to keep clear of it (ui_desk.room)
        ui_pad.diagram(self)
        # the poi's dials, their own window while the poi is on (plan 47): out
        # of the pad window, whose room stays the pad's; GRAPH's side pane too
        ui_pad.poi_window(self)
        # the player screen, large (ui_players.py): over everything, the panel folded too
        ui_players.window(self)
        if getattr(self, "desk", True):     # (a Panel from before a hot reload)
            ui_desk.diagram(self)
        if not self.open:
            return
        # pinned, never dragged: the whole window, or right of the left column
        # while the desk or the pad diagram is up (`panel_left`). H, the
        # desk's chip and `ui.panel` show and hide it; there is no title bar.
        # It stays behind the windows over it (cheat sheet, poi, players)
        # when clicked. The name stays: `replay` and the tests find the page by it.
        x, y, w, h = self.panel_rect()
        imgui.set_next_window_pos(imgui.ImVec2(x, y), imgui.Cond_.always)
        imgui.set_next_window_size(imgui.ImVec2(w, h), imgui.Cond_.always)
        imgui.begin("CONTROLS", None,
                    imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_move
                    | imgui.WindowFlags_.no_saved_settings
                    | imgui.WindowFlags_.no_bring_to_front_on_focus)
        self._panel_x = x
        self.ghosts = 0
        self.page = max(0, min(self.page, len(PAGE_KEYS) - 1))
        if self.page != getattr(self, "_focus_seen", None):   # set straight, not through ui.page
            self.go_page(self.page)
        # the footer's line and its separator: short by the separator, CONTROLS
        # overflowed by a few points and wore a scrollbar from its second frame.
        # The page fills itself and never scrolls (the pane does): its first
        # frame's content would give it a scrollbar, and the canvas a narrower
        # second frame, which the editor answers by moving the view.
        foot = imgui.get_frame_height_with_spacing() + imgui.get_style().item_spacing.y + 1.0
        if imgui.begin_child("##page", imgui.ImVec2(0, -foot), 0, imgui.WindowFlags_.no_scrollbar):
            # a desk control is picked and can be mapped (plan 17 WP4): the
            # canvas and the sections are drawn disabled — dimmed, no widget
            # takes a click — and the click on a param is `_ctx_pick`'s. Never
            # the routing section: there the picked control's own line is what
            # the user came for. The pane's chips and the footer stay live:
            # the view moves, the line lets go (`ui_graph.page`, `ui_pane._body`)
            self._picking = ui_desk.picking(self) is not None
            try:
                self._page_graph(dt)
            finally:
                self._picking = False
        imgui.end_child()
        self._footer(fps)
        imgui.end()

    def panel_rect(self) -> tuple[float, float, float, float]:
        """`panel_rect` for this frame's control window and what is up in
        the column left of the panel (the desk, the pad diagram)."""
        io = imgui.get_io()
        return panel_rect((io.display_size.x, io.display_size.y),
                          bool(getattr(self, "desk", True)),
                          bool(getattr(self, "pad_diagram", False)))

    def panel_left(self) -> float | None:
        """The panel's left edge this frame, None while it is hidden: the
        desk and the pad take the room left of it (their `room`)."""
        return self.panel_rect()[0] if self.open else None

    def _message(self, now: float | None = None) -> tuple[str, bool]:
        """The footer's one message slot (plan 15 WP1): the newest of the
        undo's status ("undid Brightness 1.20× → 0.85×"), the library's
        status and the library's warning, for `MESSAGE_S` after it
        changed — so it shows on every page — then ("", False). The second
        item is whether it is a warning. The panel remembers the strings
        it last saw; its first look only remembers them, so a launch says
        nothing. The undo's line is keyed by `said_at` too: the same
        words said again ("nothing to undo") show again; so is a library
        line set through `Library.say`, by its count (plan 15 WP4).

        The learn's line is the fourth (plan 17 WP2): what the last learn
        or unbind did (`Learn.last`), in the warning colour when it was a
        refusal — so a refusal is seen on every page — keyed by the
        learn's count of things said, so the same refusal twice shows
        twice. `_msg["key"]` names whose line is up."""
        now = time.monotonic() if now is None else now
        st = self.__dict__.setdefault(     # (a Panel from before a hot reload has none)
            "_msg", {"seen": None, "text": "", "warn": False, "at": -MESSAGE_S})
        lib, lrn = self.library, getattr(self, "learn", None)
        # whichever of the two stacks spoke last (plan 44 D5b)
        u = max((x for x in (getattr(self, "undo", None), getattr(self, "meta_undo", None))
                 if x is not None), key=lambda x: getattr(x, "said_at", 0.0), default=None)
        said = getattr(lib, "said", None) or {}
        cur = {"status": (getattr(lib, "status", "") or "", said.get("status", 0)),
               "warning": (getattr(lib, "warning", "") or "", said.get("warning", 0)),
               "undo": (getattr(u, "status", "") or "", getattr(u, "said_at", 0.0)),
               "learn": (getattr(lrn, "last", "") or "", getattr(lrn, "said_n", 0))}
        seen, st["seen"] = st["seen"], cur
        if seen is not None:
            for key in ("status", "warning", "undo", "learn"):   # the later wins a tie
                text, was = cur[key][0], seen.get(key, cur[key])  # (no such key before a reload)
                if not isinstance(was, tuple):             # remembered before a hot reload
                    was = (was, cur[key][1])
                if key == "undo" and cur[key][1] < was[1]:
                    continue                               # a stack that spoke earlier: old news
                if cur[key] != was and text:
                    warn = key == "warning" or (key == "learn" and getattr(lrn, "refused", False))
                    st.update(text=text, warn=warn, at=now, key=key)
        return (st["text"], st["warn"]) if now - st["at"] < MESSAGE_S else ("", False)

    def _footer_room(self) -> float:
        """The width left on the footer's line for the message: from the
        cursor to the show's name, which sits flush right, less the dim
        readout that follows the message while the picture is dimmed."""
        room = imgui.get_content_region_avail().x
        gap = imgui.get_style().item_spacing.x
        lib = self.library
        if lib is not None and lib.reg is not None:
            room -= imgui.calc_text_size(f"{lib.install.name} ●").x + 2 * gap
        dim = self.reg.get("output.dim")
        if dim is not None and dim.value < 1.0:
            room -= imgui.calc_text_size(f"·  dim {dim.text()}").x + gap
        black = self._black_text(self.black_outputs())
        if black:
            room -= imgui.calc_text_size(black).x + gap
        return room

    def _footer(self, fps: float) -> None:
        imgui.separator()
        imgui.push_font(_FONTS["num"], FONT_MICRO + 1)
        imgui.text_colored(FAINT, f"{fps:5.1f} FPS")
        imgui.pop_font()
        ui_players.footer(self)
        note, warn = self._message()
        color = WARN if warn else FAINT
        # an armed learn has the slot, on every page (plan 17 WP2): what it
        # waits for, in red, and a click on it cancels. Any line just said —
        # a refusal that left it armed, a library warning, an undo — shows
        # first, for its MESSAGE_S
        lrn = self.learn
        armed = lrn is not None and bool(getattr(lrn, "learning", None))
        tip = ""
        # a picked desk control has it the same way (plan 17 WP4): what is
        # picked, the seconds until it lets go by itself, and a click on the
        # line lets go at once. Whatever the slot held when the pick was
        # first seen here was said before it and gives way; a line said
        # after it (a refusal, an undo) shows first, as for a learn
        pick = None if armed else ui_desk.footer_line(self)
        if pick is not None and ui_desk.first_sight(self):
            note, self._msg["at"] = "", -MESSAGE_S
        picked_line = False         # is the slot's line the pick's own?
        if armed and not note:      # a fresh line (a refusal, a warning, an undo) shows first
            note, color, tip = f"learning {lrn.learning} — {self._learn_hint()}", RED, CANCEL_TIP
        elif pick is not None and not note:
            note, color, tip = pick[0], RED if pick[1] else DIM, ui_desk.LET_GO_TIP
            picked_line = True
        if note:
            # the message slot: one faint line (a warning in its colour),
            # cut to the room left of the show's name; the whole on hover
            imgui.same_line()
            room = self._footer_room()
            line = f"·  {note}"
            if tip and imgui.calc_text_size(f"{line} ({tip})").x <= room:
                line = f"{line} ({tip})"     # said on the line where there is room for it
            imgui.text_colored(color, fit_text(line, room))
            if imgui.is_item_hovered():
                tooltip(f"{note} ({tip})" if tip else note)
            if armed and imgui.is_item_clicked():
                lrn.arm(None)
            elif picked_line and imgui.is_item_clicked():
                ui_desk.let_go(self)
        elif self.reloader is not None and self.reloader.status:
            imgui.same_line()
            imgui.text_disabled(f"·  {self.reloader.status}")
        # the master dim (plan 15 WP3), on every page while it is under
        # full ("dim 40%", "dim black"): a dark picture is never a mystery
        dim = self.reg.get("output.dim")
        if dim is not None and dim.value < 1.0:
            imgui.same_line()
            imgui.text_colored(WARN, f"·  dim {dim.text()}")
        # …and an output black for another reason — its switches, its own
        # dim — named on every page too (plan 21 WP4)
        black = self._black_text(self.black_outputs())
        if black:
            imgui.same_line()
            imgui.text_colored(WARN, black)
        lib = self.library
        if lib is not None and lib.reg is not None:
            proj = lib.install
            text = f"{proj.name}{' ●' if proj.is_dirty() else ''}"
            flush_right(imgui.calc_text_size(text).x)
            imgui.text_colored(RED if proj.is_dirty() else DIM, text)
            if imgui.is_item_hovered():
                tooltip("the open install — the patches section")

    # ---- pages ----

    def _page_players(self, dt: float) -> None:
        """Who is on air, and what they hold (ui_players.py)."""
        ui_players.section(self, dt)


    def _page_output(self, dt: float) -> None:
        """Where the render window shows: screen, fullscreen, overlay (overlay.py)."""
        self._section("output", "output", note="T overlay · G click-through")
        if self.output is None or "output.overlay" not in self.reg:
            imgui.text_disabled("no render window attached")
            return
        if "output.dim" in self.reg:        # the master dim: the desk's MASTER fader (plan 44 D5d)
            self._row("output.dim")
            # a driver that refused the dim's program: the fader moves and
            # the picture does not — say so here (Renderer.dim_error)
            err = getattr(self.renderer, "dim_error", "")
            if err:
                imgui.text_colored(WARN, f"{err} — the picture is not dimmed")
        rows = self.displays
        if rows is not None:                # which display shows what (SC2)
            ui_displays.section(self, rows)
        self._output_blocks()
        for want in ui_graph.window_wants(self):   # plan 44 D3: a window the meta controller lacks
            imgui.text_colored(WARN, want)
        if rows is None and len(self.reg["output.monitor"].names) > 1:
            self._combo("output.monitor")
        if "output.render" in self.reg:     # the render cap, on the toggles' row
            size = getattr(getattr(self.renderer, "scene", None), "size", None)
            tip = self.reg["output.render"].tip
            self._combo("output.render", width=96,
                        tip=f"{tip}\nDrawing {size[0]}×{size[1]} now." if size else None)
            beside(check_w(self.reg["output.fullscreen" if rows is None else "output.overlay"].label))
        if rows is None:                    # (with rows, fullscreen is a display's)
            self._check("output.fullscreen")
            beside(check_w(self.reg["output.overlay"].label))
        # decision 21 (a): overlay only when the config asks — shut, the
        # toggle is drawn disabled with the reason, and its three overlay-only
        # settings (click-through, ground, opacity) would do nothing
        allowed = getattr(self.output, "allowed", True)
        imgui.begin_disabled(not allowed)
        self._check("output.overlay")
        if allowed:
            self._check("output.passthrough")
            self._row("output.bg")
            self._row("output.alpha")
        imgui.end_disabled()
        if not allowed:
            imgui.text_disabled(f"overlay {self.output.GATED}")
        if self.output.error:
            imgui.text_colored(WARN, self.output.error)

    def _outputs_now(self) -> tuple[bool, bool, float]:
        """(an effect is on, a ghost hand showed last frame, the master dim):
        what `output_shows` reads, from the renderer as it last drew. Any
        piece missing (no renderer, a stand-in) reads as off / full."""
        r = self.renderer
        # as the renderer drew it (`Frame.fx_on`, its `stats["fx_on"]`: an
        # effect of a pipeline's run is live — plan 30 D1, a placed effect
        # bends no pipeline; plan 33 T7, the run is the wires, so no
        # effect's own state says it)
        drawn = (getattr(r, "stats", None) or {}).get("fx_on")
        fx_on = drawn if isinstance(drawn, bool) else False
        visible = bool((getattr(r, "stats", None) or {}).get("layer", False))
        dim = self.reg.get("output.dim")
        return fx_on, visible, (dim.value if dim is not None else 1.0)

    def graph_now(self):
        """(the renderer's wiring, the loaded patch's graph spec or None):
        what the OUTPUT page says in words (plan 26 A4). Any piece missing
        (no renderer, no loadable patches) reads as the empty frame (plan 36 T3:
        `graph.EMPTY`). Plan 35 T5: the wired frame itself, in the new ids,
        on every page."""
        loaded_patch = getattr(getattr(self, "library", None), "loaded_patch", None)
        gs = getattr(loaded_patch, "graph", None)
        # (no renderer: the landed loadable patch's own wiring — what it would hand one)
        wiring = (getattr(self.renderer, "wiring", None) or getattr(gs, "wiring", None)
                  or EMPTY)
        return wiring, getattr(gs, "spec", None)

    def select_graph_node(self, nid: str) -> None:
        """Select canvas node `nid` on GRAPH — `graph_selected`'s form:
        `render:acid.2`, a modifier's id — centred next frame, the page
        opened: the request path OUTPUT's "open on GRAPH" takes
        (`ui_graph.select_id`), for whoever drives the selection from
        outside the graph view."""
        ui_graph.select_id(self, nid)

    def graph_selected_params(self) -> list[str]:
        """The registry ids under `graph_selected` (`graphview.params_of`:
        a copy's are its original's), the continuous ones first, each run in
        registry order; [] with nothing selected or a node with no param
        (`ui_graph.node_params`). Asked, not drawn: nothing per frame."""
        nid = getattr(self, "graph_selected", None)
        return [] if nid is None else ui_graph.node_params(self, nid)

    def bus_cuts_now(self):
        """The loaded patch's bus cuts (plan 44 D3; plan 36 T1's were the show's:
        `graph.BusCuts`), what the OUTPUT page's words and edits read;
        with no loadable patches, every cable standing."""
        return bus_cuts_of(getattr(getattr(self, "library", None), "loaded_patch", None))

    def black_outputs(self) -> list[int]:
        """The opened outputs showing nothing for a reason other than the
        master dim (which the footer already says): the footer names them
        on every page (plan 21 WP4)."""
        fx_on, visible, master = self._outputs_now()
        wiring, _ = self.graph_now()
        bus_cuts = self.bus_cuts_now()
        return [sl.n for sl in (getattr(self, "outputs", None) or [])
                if getattr(sl, "drawn", sl.opened) and output_shows(sl.switches, fx_on, visible, master, wiring,
                                         n=sl.n, bus_cuts=bus_cuts)[1]
                not in ("", "master")]

    @staticmethod
    def _black_text(ns: list[int]) -> str:
        if not ns:
            return ""
        which = f"output {ns[0]}" if len(ns) == 1 else f"outputs {', '.join(map(str, ns))}"
        return f"·  {which} black"

    def _output_blocks(self) -> None:
        """One block per render output the config lists (plan 21 WP4), a
        view of the wires (plan 35 U): its number and name, its two mutes
        ("picture", "hands": the window's, never the loadable patch) and "hands
        through the effects" (the loadable patch's wiring, `graphview.set_through`),
        its own dim and flips (with two or more outputs), why a tick can do
        nothing, and "shows:" — its picture port's source in words
        (`shows_line`) as a combo of the graph's pictures that sets it
        (`graphview.set_picture`), in the warning colour when it is black —
        with "open on GRAPH" beside it. Above them, All outputs' block: the
        same combo, nothing else. An output that did not open is one
        disabled line saying why; under the blocks, the last edit's words
        and which output paces the loop and the frame's size."""
        slots = getattr(self, "outputs", None) or []
        if not slots:
            return
        # (a slot nothing shows and nothing's missing from says nothing: SC2 keeps all of
        # them for the run, and the rows say which display shows what)
        slots_all, slots = slots, [sl for sl in slots if getattr(sl, "drawn", sl.opened) or sl.missing]
        several = len(slots) > 1
        fx_on, visible, master = self._outputs_now()
        ghost = self.reg.get("ghost.on")
        # plan 26 A4: the render graph the outputs are wired by — the
        # loaded patch's `graph` section, or the default; plan 35 U: the
        # wired frame the pages read and edit (`graphview.page_spec`)
        wiring, spec = self.graph_now()
        bus_cuts = self.bus_cuts_now()
        frame = graphview.page_spec(spec)
        said = graph_words(spec, getattr(getattr(self.renderer, "_graph", None),
                                         "dormant", None))
        # (the blocks' rows closer together: four windows of four rows each,
        # and All outputs', fit the page unscrolled — popped after the loop)
        imgui.push_style_var(imgui.StyleVar_.item_spacing,
                             imgui.ImVec2(imgui.get_style().item_spacing.x, 4))
        imgui.align_text_to_frame_padding()
        imgui.text(graphview.label_of(ALL_OUTPUTS))
        imgui.same_line()
        self._picture_combo(frame, f"{ALL_OUTPUTS}.image", shows_line(frame, None, slots), -1,
                            False, f"{graphview.hover_of(ALL_OUTPUTS)}\n{said}", slots)
        # the switches line up after the widest "N  name", which is cut so
        # the three ticks always fit the page's width
        ticks = sum(imgui.calc_text_size(s).x for s in ("picture", "hands", THROUGH_WORDS))
        ticks += 3 * (imgui.get_frame_height() + 2 * imgui.get_style().item_inner_spacing.x)
        ticks += 3 * imgui.get_style().item_spacing.x
        # plan 49 stage 2: in the side pane the ticks go under the name,
        # wrapped where they would pass the edge (`beside`)
        narrow = imgui.get_content_region_avail().x - ticks - 8 < NAME_ROOM
        room = (imgui.get_content_region_avail().x if narrow
                else max(imgui.get_content_region_avail().x - ticks - 8, 40))
        labels = {sl.n: fit_text(f"{sl.n}  {sl.name}" if sl.name else f"{sl.n}", room)
                  for sl in slots}
        col = imgui.get_cursor_pos_x() + 8 + max((imgui.calc_text_size(t).x
                                                  for t in labels.values()), default=0.0)
        for sl in slots:
            pre = f"output.{sl.n}"
            name = sl.name or ("output" if several else "")
            if not getattr(sl, "drawn", sl.opened) or f"{pre}.scene" not in self.reg:
                imgui.text_disabled(fit_text(f"{sl.n}  {name} — {sl.missing or 'not opened'}",
                                             imgui.get_content_region_avail().x))
                continue
            imgui.align_text_to_frame_padding()
            imgui.text(labels[sl.n])
            if not narrow:
                imgui.same_line(col)
            # plan 35 O (row 374): the window's two mutes (the meta controller's, never
            # the loadable patch); "hands through the effects" is the loadable patch's
            # wiring, written from here (T6, `graphview.set_through`)
            self._check(f"{pre}.scene", "picture")
            beside(check_w("hands"))
            self._check(f"{pre}.hands", "hands")
            beside(check_w(THROUGH_WORDS))
            self._through_check(frame, sl.n, slots, bus_cuts)
            # the mirror (plan 23 WP1): two ticks at the right of the dim row,
            # or of the "shows:" line when the output has no dim of its own
            # (with rows, a window's flips are on its display's row)
            flips = [(pid, t) for pid, t in ((f"{pre}.flip_x", "flip X"),
                                             (f"{pre}.flip_y", "flip Y")) if pid in self.reg
                     and (self.displays is None or not sl.opened)]
            st = imgui.get_style()
            fw = sum(imgui.calc_text_size(t).x + imgui.get_frame_height()
                     + st.item_inner_spacing.x + st.item_spacing.x for _, t in flips)
            if narrow and flips:            # the pane: the flips on a row of their own
                fw = 0.0
            # (one shown, the master dim is its dim, unless it has a launch dim of its own)
            if f"{pre}.dim" in self.reg and (several or float(sl.switches.dim) < 1.0):
                self._row(f"{pre}.dim", width=-(fw + 8) if fw else -1, label="dim")
                for i, (pid, t) in enumerate(flips):
                    if not narrow or i:
                        beside(check_w(t))
                    self._check(pid, t)
                flips = []
            sw = sl.switches
            why = []
            if sw.hands and ghost is not None and not ghost.value:
                why.append("hands: ghost hands are off (HANDS section)")
            elif sw.hands and getattr(self, "hands", None) is None:
                why.append("hands: no tracker")
            if through_layer(wiring, sl.n, bus_cuts) is not None and not fx_on:
                why.append("through: no effect on")
            # one line for what is wrong: its present's error first (warning
            # colour, the whole on hover), then why a switch can do nothing
            if sl.error:
                why.insert(0, sl.error)
            if why:
                line = " · ".join(why)
                imgui.text_colored(WARN if sl.error else FAINT,
                                   fit_text(line, imgui.get_content_region_avail().x))
                if imgui.is_item_hovered():
                    tooltip(line)
            # plan 26 A4: the words say the wiring too — the switches above
            # and the loaded patch's graph set it (`hands: in the scene`);
            # the whole graph in words on the line's hover
            # plan 30 D1: the effects placed on what it shows, and on hover
            # why a placed one runs nowhere this frame (`Graph.dormant`)
            # plan 35 U: "shows:" is the window's picture port as the wires
            # say it, and the combo that sets it (`graphview.set_picture`);
            # the retired route table's words (`output_shows`) on its hover,
            # and after the words when it is black or dimmed
            words, black = output_shows(sw, fx_on, visible, master, wiring, n=sl.n, bus_cuts=bus_cuts)
            line = shows_line(frame, sl.n, slots, bus_cuts)
            factor = min(1.0, master * float(sw.dim))
            if black:
                line += f" · {words}"
            elif 0.0 < factor < 1.0:
                line += f" · {min(99, max(1, round(factor * 100)))}%"
            tip = f"{words}\n{hands_words(wiring, sw, sl.n, bus_cuts)}\n{said}"
            gw = chip_w(OPEN_ON_GRAPH) + st.item_spacing.x
            self._picture_combo(frame, f"{pre}.image", line, -(gw + (fw + 8 if flips else 0)),
                                bool(black), tip, slots, bus_cuts=bus_cuts)
            imgui.same_line()
            if chip(f"{OPEN_ON_GRAPH}##graph.{pre}"):
                ui_graph.select_node(self, pre)
            if imgui.is_item_hovered():
                tooltip(f"select {graphview.label_of(pre, slots)} on the canvas "
                                  "and bring it on screen")
            for pid, t in flips:            # no dim row: the ticks at the right of this one
                beside(check_w(t))
                self._check(pid, t)
        imgui.pop_style_var()
        # plan 30 D1: a placed effect that runs nowhere this frame, and why
        for line in dormant_lines(getattr(self.renderer, "_graph", None)):
            imgui.text_colored(FAINT, fit_text(line, imgui.get_content_region_avail().x))
            if imgui.is_item_hovered():
                tooltip(line)
        self._edit_said("output_said")
        if several:
            w, h = slots_all[0].size
            size = f" · frame {w}×{h}" if w and h else ""
            pace = next((sl.n for sl in slots_all if sl.opened), 1)
            imgui.text_colored(FAINT, fit_text(f"paced by output {pace}{size} · below: output 1's "
                                               "window", imgui.get_content_region_avail().x))
        imgui.dummy(imgui.ImVec2(0, 2))

    # ---- plan 35 U: the pages' graph edits (OUTPUT, LOOKBACK) ----

    def _graph_edit(self, fn, key: str) -> None:
        """Page edit `fn(edit)` on the loaded patch's graph — GRAPH's own
        `render_edit`: one undo step, its refusals — its words (a refusal,
        or what it did) kept under `key` for the page's line."""
        e = ui_graph.render_edit(self)
        try:
            why = fn(e)
        except Exception as err:  # noqa: BLE001 — a page's edit must not kill the app
            why = f"edit failed: {err}"
        setattr(self, key, why or e.said)

    def _edit_said(self, key: str) -> None:
        """The page's last graph edit's words, faint, one line (the whole on hover)."""
        line = getattr(self, key, "")
        if line:
            imgui.text_colored(FAINT, fit_text(line, imgui.get_content_region_avail().x))
            if imgui.is_item_hovered():
                tooltip(line)

    def _picture_combo(self, frame, port: str, line: str, width: float, warn: bool,
                       tip: str, slots=(), key: str = "output_said", bus_cuts=None) -> None:
        """A picture port as a combo (plan 35 U): closed, `line` (its
        "shows:" or "records:" words, in the warning colour when `warn`);
        open, `graphview.picture_choices` by their titles, the pick a
        `graphview.set_picture` edit. `tip` on the closed combo's hover;
        `rig` the show's bus wires (plan 36 T1: "as All outputs" is the
        bus cable while it stands)."""
        imgui.set_next_item_width(width)
        if warn:
            imgui.push_style_color(imgui.Col_.text, WARN)
        # (a chip's padding: the row is a line of words with its chip
        # beside it, and four windows' blocks fit the page unscrolled)
        imgui.push_style_var(imgui.StyleVar_.frame_padding, CHIP_PAD)
        opened = imgui.begin_combo(f"##picture.{port}", line)
        imgui.pop_style_var()
        if warn:
            imgui.pop_style_color()
        pick = None
        if opened:
            now = graphview.picture_now(frame, port, bus_cuts)
            # (R17: an output's combo also offers each channel with a source)
            for item in graphview.picture_choices(frame, port, self.reg):
                chosen = item == now
                text = graphview.picture_label(frame, item, slots)
                if imgui.selectable(f"{text}##{port}.{item}", chosen)[0] and not chosen:
                    pick = item
                if chosen:
                    imgui.set_item_default_focus()
            imgui.end_combo()
        elif tip and imgui.is_item_hovered():
            tooltip(tip)
        if pick is not None:
            self._graph_edit(lambda e: graphview.set_picture(e, port, pick), key)

    def _through_check(self, frame, n: int, slots=(), bus_cuts=None) -> None:
        """Window `n`'s "hands through the effects" (plan 35 O): ticked while
        its picture is a chain over the hands layer laid on; a tick is
        `graphview.set_through`. Drawn disabled, with why on its hover,
        where it can do nothing (`graphview.through_refusal`)."""
        on = graphview.is_through(frame, n, bus_cuts)
        why = None if on else graphview.through_refusal(frame, n, slots, bus_cuts)
        imgui.begin_disabled(why is not None)
        changed, v = checkbox(f"{THROUGH_WORDS}##through.{n}", on)
        imgui.end_disabled()
        if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            tooltip(why or "the hands bent by the effects on this output (written "
                              "into the patch's graph: a composite before the effects)")
        if changed:
            self._graph_edit(lambda e: graphview.set_through(e, n, v), "output_said")

    def _page_view(self, dt: float) -> None:
        """The VIEW section, on the kit (hyperspace/dkit) where it is there
        (`ui_view.page`); else `_view_stock`."""
        ui_view.page(self, dt)

    def _view_hero(self) -> None:
        """VIEW's head: the big cell count, the shape's names beside it."""
        v = self.view
        sh = SHAPES[v.shape]
        g = geom(v.shape)
        # signature readout — the big cell count is the panel's identity
        # (reference #cells: large white numeral), the shape's names in a
        # block beside it so the header costs the page one numeral's height
        imgui.push_font(_FONTS["micro"], FONT_BIG)
        imgui.text(f"{sh.cells or '—'}")
        imgui.pop_font()
        imgui.same_line(0, 16)
        imgui.begin_group()
        _micro("cells", FAINT)
        imgui.push_font(_FONTS["micro"], FONT_BASE + 4)
        imgui.text(sh.name.upper())
        imgui.pop_font()
        _micro(sh.alias, RED)
        _micro(f"{sh.dims}D  ·  {g['n']}V {g['m']}E  ·  {sh.sym}")
        imgui.end_group()
        imgui.spacing()

    def _view_stock(self, dt: float) -> None:
        """VIEW as the stock widgets draw it: the section without the kit."""
        v = self.view
        sh = SHAPES[v.shape]
        self._view_hero()
        self._section("view", "view")
        self._shape_combo()
        self._fader("view.bright")
        self._fader("view.speed")
        self._fader("view.depth4")
        imgui.spacing()
        # the plane keys tile the row, solid red while a plane spins
        kw = (imgui.get_content_region_avail().x
              - imgui.get_style().item_spacing.x * (len(PLANES) - 1)) / len(PLANES)
        # the W planes cannot act on a 3D shape, nor on a 4D one while the
        # 3D switch holds its w: their keys dim (still switchable — the
        # next 4D shape, or the switch going off, picks them up)
        held = ("a 3D shape has no w" if sh.dims == 3
                else "the 3D switch holds w" if v.three_d else "")
        for p, name in enumerate(PLANES):
            if p:
                imgui.same_line()
            inert = held and name.endswith("W")
            if inert:
                imgui.push_style_var(imgui.StyleVar_.alpha, 0.35)
            self._lit_button(f"view.plane.{name}", name, v.planes[p], width=kw)
            if inert:
                imgui.pop_style_var()
                if imgui.is_item_hovered():
                    tooltip(f"{name} does nothing now: {held}")
        self._check("view.points")
        for pid in ("view.lines", "view.rotate", "view.faces", "view.three_d"):
            beside(check_w(self.reg[pid].label))
            self._check(pid)
        # the two layers' opacities (plan 24 C2), side by side, and at the
        # row's end the strokes in world space (grow with the zoom) or screen
        # space (plan 26 A2b) — one row, so a field's rows fit beneath
        sp = imgui.get_style().item_spacing.x
        strokes_w = check_w(self.reg["view.screen_strokes"].label)
        half = (imgui.get_content_region_avail().x - strokes_w - 2 * sp) / 2
        if half < SLIDER_MIN:       # a narrow pane: the two share the row, the check under
            half = (imgui.get_content_region_avail().x - sp) / 2
        self._slider("view.points_alpha", half)
        imgui.same_line()
        self._slider("view.lines_alpha", half)
        beside(strokes_w)
        self._check("view.screen_strokes")
        # the count, and Fit beside it: whole copies only, framed to the screen
        fit_w = imgui.calc_text_size("Fit").x + imgui.get_frame_height() + 2 * imgui.get_style(
            ).item_inner_spacing.x
        self._slider("view.instances", imgui.get_content_region_avail().x - fit_w
                     - imgui.get_style().item_spacing.x)
        imgui.same_line()
        self._check("view.inst_fit")
        if v.instances > 1:
            # the field's rows: how the copies are laid out, how they move
            # and — while they move — by how much and how fast; then how far
            # apart, and a lattice's depth
            # every layout at once: the flat three and the six lattices
            self._combo("view.inst_layout", 104, rows=len(field.NAMES))
            beside(96)
            self._combo("view.inst_motion", 96)
            if v.inst_motion:
                beside(84)
                self._slider("view.inst_amp", 84)
                beside(SLIDER_MIN)
                self._slider("view.inst_rate")
            if field.is_3d(v.inst_layout):
                half = (imgui.get_content_region_avail().x - imgui.get_style().item_spacing.x) / 2
                self._slider("view.inst_spacing", half)
                imgui.same_line()
                self._slider("view.inst_persp")
            else:
                self._slider("view.inst_spacing")
        imgui.spacing()

        # per-plane rate: what a lane drives to spin a plane (base 1, signed);
        # two to a row, so the field's row above has room on the page. The
        # cell says only the plane (the section and the tooltip say "rate"):
        # a driven rate reads `base → effective`, which needs the width
        self._section("rotation", "rot")
        if imgui.begin_table("##rot.rate", 2, imgui.TableFlags_.sizing_stretch_same):
            for name in PLANES:
                imgui.table_next_column()
                self.half(f"rot.rate.{name}", name, label_w=32)
            imgui.end_table()

    def _page_faces(self, dt: float) -> None:
        ui_patterns.page(self, dt)     # the faces, the pattern browser, the eight inputs

    def _page_media(self, dt: float) -> None:
        """The media channels (plan 32 U): the missing banner, the library,
        the eight channels and their bins, the backdrop's and the faces'
        pickers (ui_media.py). The bitmap page's one file is a channel now."""
        ui_media.draw(self, dt)

    def open_file_dialog(self, title: str, filters: list[str]):
        """The native file dialog (portable_file_dialogs), or None with the
        reason in `self.dialog_error` — best effort: a Mac without it still
        has the rest of the page. Poll the dialog's `ready()` / `result()`
        on later frames, as the audio page's Load track does."""
        self.dialog_error = ""
        try:
            from imgui_bundle import portable_file_dialogs as pfd

            return pfd.open_file(title, "", filters)
        except Exception as e:  # noqa: BLE001 — dialog is best-effort
            self.dialog_error = f"file dialog unavailable: {e}"
            return None

    def _page_camera(self, dt: float) -> None:
        """The CAMERA section, on the kit (hyperspace/dkit) where it is there
        (`ui_camera.page`); else `_camera_stock`."""
        ui_camera.page(self, dt)

    def _camera_stock(self, dt: float) -> None:
        """CAMERA as the stock widgets draw it: the section without the kit."""
        self._section("camera", "camera")
        self._row("camera.zoom")
        self._row("camera.yaw")
        self._row("camera.pitch")
        self._row("camera.pan.x")
        self._row("camera.pan.y")
        imgui.spacing()
        # plan 43 C2: one orbit camera, the loadable patch's — zoom and pan move the
        # shape in the world, the eye (plan 26 A2) is what the world is seen
        # through; one section, saved with the loadable patch
        self._row("eye.fov")
        self._row("eye.distance")
        imgui.spacing()
        self._button("camera.reset", "Reset view")
        beside(imgui.calc_text_size("R  ·  stick click").x)
        imgui.text_disabled("R  ·  stick click")
        if self.reg.get("world.reset") is not None:     # plan 59: the world's offsets, the meta controller's
            self._button("world.reset", "Reset world")

    def _page_lookback(self, dt: float) -> None:
        ui_lookback.page(self, dt)     # the frame history and its composite

    def _page_audio(self, dt: float) -> None:
        a = self.audio
        self._section("audio source")
        mic_on = a.on and a.mode == "mic"
        self._button("audio.mic", "Stop mic" if mic_on else "Listen to mic")
        if "audio.mix" in self.reg:       # plan 45 V3: the videos' sound, summed
            mix_on = a.on and a.mode == "mix"
            words = "Stop video sound" if mix_on else "Listen to video sound"
            beside(button_w(words))
            self._button("audio.mix", words)
            if mix_on:      # true only then; the hover says it before the press (row 790)
                imgui.push_text_wrap_pos(0.0)
                imgui.text_colored(DIM, VIDEO_SOUND_REACHES)
                imgui.pop_text_wrap_pos()
        else:
            beside(button_w("Load track"))
        if button("Load track"):
            self._file_dialog = self.open_file_dialog(
                "Choose a track", ["Audio", "*.wav *.mp3 *.flac *.ogg"])
            if self._file_dialog is None:
                a.error = self.dialog_error
        if a.on:
            beside(button_w("Stop"))
            self._button("audio.stop", "Stop")
        if self._file_dialog is not None and self._file_dialog.ready():
            picked = self._file_dialog.result()
            self._file_dialog = None
            if picked:
                a.start_file(picked[0])
        if "audio.device" in self.reg and (getattr(a, "devices", None) or "audio.rescan" in self.reg):
            if getattr(a, "devices", None):
                self._combo("audio.device", width=-(button_w("rescan") + 8))
                imgui.same_line()
            if "audio.rescan" in self.reg:
                self._button("audio.rescan", "rescan")
        if a.error:
            imgui.text_colored(WARN, a.error)
        elif a.on:
            # the analyser's rate — the track's for a file, not the capture rate
            rate = getattr(a, "rate", getattr(a, "sr", 0.0))
            imgui.text_disabled(f"{a.label}  ·  {rate / 1000:.1f} kHz")
            mx = getattr(a, "_mixer", None)
            if a.mode == "mix" and mx is not None:
                if getattr(mx, "failed", False):        # the mixer's error is the source's
                    imgui.text_colored(WARN, f"video sound silent — {mx.state}")
                elif not getattr(mx, "playing", 0):
                    imgui.push_text_wrap_pos(0.0)   # (longer than the pane's narrow widths)
                    imgui.text_disabled("silent until an on-air channel's sound is on (MEDIA)")
                    imgui.pop_text_wrap_pos()
        else:
            imgui.text_disabled("no source — the shape spins on its own")

        # transport
        if a.mode == "file":
            self._button("audio.play", "Pause" if a.playing else "Play")
            beside(button_w("Restart"))
            self._button("audio.restart", "Restart")
            pos, dur = a.position(), a.duration()
            clock = (f"{int(pos // 60)}:{int(pos % 60):02d} / "
                     f"{int(dur // 60)}:{int(dur % 60):02d}")
            beside(_readout_width(clock))           # measured as printed (a 100-minute set)
            imgui.align_text_to_frame_padding()
            _readout(clock, DIM)
        imgui.spacing()

        # the level into the analyser: what every band sees
        self._section("master", "master")
        self._fader("master.gain")
        self._fader("master.dyn")
        self._fader("master.trim")

    def _page_analyzer(self, dt: float) -> None:
        """The ANALYZER page — scene, meters, then the band editor
        (ui_bands.py): the spectrogram with the bands over it and the
        selected band's strip. GRAPH's side pane draws it as its
        analyzer section (ui_pane.py, plan 49): the page is the section at
        full height."""
        c = self.control
        self._section(group_title("band"), "band")
        # scene + reset-all (relabels to Undo while the window is open); where
        # the three would leave the combo too little, the button takes a row
        # and the label only its own room
        reset = "Undo" if c.undo_armed else "Reset all"
        take = button_w("Reset all") + imgui.get_style().item_spacing.x
        roomy = imgui.get_content_region_avail().x - LABEL_W - take >= SCENE_COMBO_MIN
        self._label_cell("scene", width=LABEL_W if roomy
                         else imgui.calc_text_size("SCENE").x + LABEL_GAP + 4)
        self._combo("scene.select", -take if roomy else -1)
        if roomy:
            imgui.same_line()
        self._button("scene.reset_all", reset)
        imgui.spacing()
        self._meters(dt)
        ui_bands.section(self, dt)

    def _page_graph(self, dt: float) -> None:
        """Both graphs on one canvas, edited through `graphview.Edit` (ui_graph.py,
        plan 28 N2; the edits N3 and N4)."""
        ui_graph.page(self, dt)

    def _page_routing(self, dt: float) -> None:
        """The routing matrix — lanes → params (ui_routing.py)."""
        ui_routing.page(self, dt)

    def _page_lfo(self, dt: float) -> None:
        """The tap-tempo clock and the four LFOs (ui_lfo.py)."""
        ui_lfo.page(self, dt)

    def _page_seq(self, dt: float) -> None:
        """The step sequencer's grid and the envelopes (ui_seq.py)."""
        ui_seq.page(self, dt)

    def _page_hands(self, dt: float) -> None:
        """The Ultraleap hands: live view and setup (hands/panel.py)."""
        ui_hands.page(self, dt)

    def _page_loadable(self, dt: float) -> None:
        """The PRESETS page, 2026-10-28, top to bottom
        (ui_loadable.page): the preset strip — ◀ name ● ▶ · new · save ·
        as… — then every loadable patch as a list that fills the room it has, its
        trash at the foot, the patches fold, one line for the show, and the
        library's notes. GRAPH's side pane draws it as its loadable patches section
        (ui_pane.py, plan 49)."""
        if self.library is None:
            self._section("loadable")
            imgui.text_disabled("no library attached")
            return
        ui_loadable.page(self)

    def library_lines(self) -> list[tuple[str, bool]]:
        """The SYSTEM page's library lines (plan 25), each with whether it
        is an error: the library root and, when it is elsewhere, the
        machine home; a shared library that was not there at launch says
        so, red, for as long as the app runs."""
        lib = self.library
        root = lib.home
        machine = getattr(lib, "machine", root)
        missing = getattr(lib, "missing", None)
        if missing is not None:
            lines = [((f"library: {missing} — NOT FOUND, saves are off "
                      "(restart once it is there)"), True)]
        else:
            lines = [(f"library: {root}", False)]
            said = getattr(lib, "not_moved", "")
            if said:
                lines.append((said, True))
        if machine != root:
            lines.append((f"machine: {machine}", False))
        return lines

    def _library_lines(self) -> None:
        for text, bad in self.library_lines():
            if bad:
                imgui.text_colored(WARN, text)
            else:
                imgui.text_disabled(text)
            if imgui.is_item_hovered():
                tooltip(
                    "this machine's own files: config.toml, bindings.json, windows.json, "
                    "hands.json, last_show, logs" if text.startswith("machine:") else
                    "patches and installs as JSON ([library] path, else $HYPERSPACE_HOME); "
                    "edit a file and the app follows")

    def gpu_lines(self) -> list[str]:
        """The SYSTEM page's GPU timing (plan 26 A0, per node since A1): a
        heading, then one line per node of the render graph (graph.py) of
        the last frames, its rolling median in ms
        (`Renderer.stats["gpu_ms"]`, render.PassTimer) — plan 30 D0: a line
        per effect that ran a pass (`acid`, a copy, the graph's `Effect`
        nodes, `Graph.timed_in`) before its end's own (`shown(acid)`, the
        work beyond its effects); with no timer queries on the context, the
        one line saying so. Plan 35 T4: then the ends that ran the last
        frame (`stats["ends"]`, where the pipelines were). Nothing before a
        frame has been timed, or with no renderer. With two decks (D5e): the deck on
        air's, by its number, whichever the panel is on, as `deck2_gpu_lines` is the
        deck off air's; the panel's own would read the deck off air twice."""
        fade = getattr(self, "fade", None)
        if fade is None:
            return _gpu_block(getattr(self.renderer, "stats", None) or {}, "gpu")
        stats = getattr(fade.on_air.renderer, "stats", None) or {}
        return _gpu_block(stats, f"deck {deck_number(fade.decks, fade.on_air)} (on air) gpu")

    def deck2_gpu_lines(self) -> list[str]:
        """Plan 44 D4, §8: the second GPU block, what the deck off air costs —
        a block like the first while it draws (a fade, or the panel's backdrop),
        one line otherwise, and what its draw raised, or its last warm draw's.
        Named by its number: either deck can be off air (D5c)."""
        fade = getattr(self, "fade", None)
        if fade is None:
            return []
        mixed = getattr(fade.on_air.renderer, "mix_error", "")
        deck = f"deck {deck_number(fade.decks, fade.off_air)}"
        said = [f"{deck}: {e}" for e in (fade.error, fade.warm_error, mixed) if e]
        if not (fade.drew or fade.previewed):
            return [f"{deck}: off air, draws nothing", *said]
        stats = getattr(fade.off_air.renderer, "stats", None) or {}
        return [*_gpu_block(stats, f"{deck} gpu"), *said]

    def _gpu_timing(self) -> None:
        for text in (*self.gpu_lines(), *self.deck2_gpu_lines()):
            imgui.text_disabled(text)

    def _page_system(self, dt: float) -> None:
        self._section("system")
        self._check("ui.cheatsheet")
        if "ui.desk" in self.reg:   # (a registry from before a hot reload lacks it)
            beside(check_w(self.reg["ui.desk"].label))
            self._check("ui.desk")
        if "ui.pad_diagram" in self.reg:
            beside(check_w(self.reg["ui.pad_diagram"].label))
            self._check("ui.pad_diagram")
            if "ui.pad_view" in self.reg:
                beside(110)
                self._combo("ui.pad_view", width=110)
        beside(chip_w("Restart process"))
        self._button("app.restart", "Restart process", small=True)
        if self.reloader is not None:
            imgui.text_disabled(f"hot reload: {self.reloader.status or 'watching'}")
            if self.reloader.error:
                imgui.text_colored(WARN, self.reloader.error)
            if self.reloader.restart:
                imgui.text_colored(WARN, self.reloader.restart)
        if self.library is not None:
            self._library_lines()
        if self.config_error:
            imgui.text_colored(WARN, self.config_error)
        for note in self.config_notes:
            imgui.text_disabled(note)
        if self.dream_error:
            imgui.text_colored(WARN, self.dream_error)
        self._stall_status()
        self._gpu_timing()
        graph_ms = ui_graph.timing_line(self)     # plan 28 N2: the GRAPH page's own draw
        if graph_ms:
            imgui.text_disabled(graph_ms)
            # plan 49 stage 2: what of it the side pane's open sections took
            pane_ms = ui_pane.timing_line(self)
            if pane_ms:
                imgui.text_disabled(fit_text(pane_ms, imgui.get_content_region_avail().x))
        thumbs = ui_graph.thumbnail_line(self)    # plan 37 C1: the GRAPH page's thumbnails
        if thumbs:
            imgui.text_disabled(thumbs)
        sound, warn = ui_media.mixer_line(self)   # plan 45 V2: the media mixer's stream
        if sound and warn:
            imgui.text_colored(WARN, sound)
        elif sound:
            imgui.text_disabled(sound)
        imgui.spacing()
        self._section("devices")
        self._device_lines()
        self._publish_lines()
        imgui.spacing()
        self._section("midi")
        if "desk.slew" in self.reg:     # knob smoothing (a registry with no table lacks it)
            self._row("desk.slew")
        self._desk_log()
        self._learn_status()
        if "desk.pad.feel" in self.reg:    # the sticks' feel (routing._register_pad_feel)
            imgui.spacing()
            self._section("gamepad")
            # the feel (a spring's loadable patch beside it) and its two knobs, the
            # feel's shape over the feel working live beside them, as tall as
            # they are (ui_feel) — beside, since the page has no height to spare
            feel = self.router.source_feel("axis") if self.router is not None else None
            plotted = feel is not None and feel.on
            sp = imgui.get_style().item_spacing.x
            avail = imgui.get_content_region_avail().x
            plot_w = min(self.PAD_FEEL_W, avail * 0.4)
            ctl = (avail - plot_w - sp - LABEL_W
                   if plotted else -1)          # a control's width, after its label
            mode = self.reg["desk.pad.feel"].text()
            imgui.begin_group()
            if mode == "spring" and feel is not None and "desk.pad.spring" in self.reg:
                feel_w = max(ctl * 0.45, 60.0)
                self._row("desk.pad.feel", feel_w)
                imgui.same_line()
                spring = self.reg["desk.pad.spring"]      # its loadable patches drawn as their curves
                picked = ui_feel.spring_picker("##desk.pad.spring", feel, ctl - feel_w - sp)
                self._tip(spring)
                self._ctx(spring)
                if picked is not None:
                    spring.set(spring.names.index(picked))
            else:
                self._row("desk.pad.feel", ctl)
            for k in {"follow": ("attack", "release"),
                      "spring": ("duration", "bounce")}.get(mode, ()):
                self._row(f"desk.pad.{k}", ctl)
            imgui.end_group()
            if plotted:
                imgui.same_line()
                self._pad_feel_plot(feel, plot_w, imgui.get_item_rect_size().y)
            # (the sticks' dials, the loadable patch's, are on the GRAPH page's pad node)

    PAD_FEEL_W = 220.0   # the sticks' feel plots (ui_feel), px at most, beside its knobs

    def _pad_raw_lanes(self):
        """The lanes as the pad reads them: its own, since the shared feed is what routes
        hear, and a quiet stick reads NaN there while it orbits (`Router.pad`)."""
        pad = self.pad
        return pad.lanes() if pad is not None and pad.on else self.router.feeds.get("axis")

    def _pad_feel_plot(self, feel, width: float, height: float) -> None:
        """The sticks' feel, its shape over the feel working live: every
        axis lane sampled each frame — as the pad reads it (`_pad_raw_lanes`)
        and after the feel (`Router.felt_lanes`, the camera job's
        followers) — and the one that moved most lately drawn, named in its
        corner."""
        router = self.router
        raws = self._pad_raw_lanes()
        felts = router.felt_lanes("axis")
        n = max(len(raws) if raws is not None else 0, len(felts or ()))
        traces = [ui_feel.sample(self, ("pad", i),
                                 float(raws[i]) if raws is not None and i < len(raws) else None,
                                 felts[i] if felts is not None and i < len(felts) else None)
                  for i in range(n)]
        if not traces:
            ui_feel.draw(feel, None, width, height, stacked=True)
            return
        i = ui_feel.busiest(traces, imgui.get_time(), ui_feel.span(feel))
        names = router.labels.get("axis") or []
        ui_feel.draw(feel, traces[i], width, height,
                     title=names[i] if i < len(names) else f"axis {i}", stacked=True)

    # ---- the sticks as dials (gamepad.dial, a prototype) ----

    DIAL_R = 52.0        # the clock face's radius, px
    DIAL_ROW = 16.0      # a legend line's height, px
    DIAL_WIDE = 380.0    # under this the legend goes under the face, not beside it

    def pad_reads_here(self) -> bool:
        """Does the pad the panel draws read the `Deck` the panel shows? A pad reads the
        deck it drives, so on the other deck its sticks say nothing about this one's dials."""
        pad = self.pad
        listed = self.devices if self.devices is not None else ()
        d = next((d for d in listed if pad is not None and getattr(d, "io", None) is pad), None)
        pointer = getattr(d, "pointer", None)
        return pointer is None or pointer.deck.reg is self.reg

    def _dials(self) -> None:
        """Both sticks as clock faces, one above the other, with their legends: the
        eight sectors clockwise from N, the param each one's route drives (FAINT "·"
        where none does) and how far it reads now. A sector fills out to its reading;
        the stick is a white dot. Under them each stick's reading and the swap: this
        deck's loadable patch's (`pad.dial.*`). A pad on the other deck moves nothing
        here, and the faces say so. The GRAPH page's pad node draws it (ui_graph)."""
        pad = self.pad
        routed: dict[str, str] = {}
        router = self.router
        if router is not None:
            for b in router.table.mods():
                if b.enabled and b.scheme == "axis" and b.source not in routed:
                    p = self.reg.get(b.target)
                    routed[b.source] = p.label if p is not None else b.target
        here = self.pad_reads_here()
        on = pad is not None and pad.on and here
        lanes = pad.dials() if on else [0.0] * len(gamepad.DIAL_LANES)
        n = gamepad.DIAL
        for j, stick in enumerate(gamepad.DIAL_STICKS):
            pid = dial_id(stick)
            side, mode = pid.rpartition(".")[2], self.reg[pid].text()
            xy = None
            if on:
                ax, ay = gamepad.DIAL_STICKS[stick]
                xy = (pad.axes[ax] if ax < len(pad.axes) else 0.0,
                      pad.axes[ay] if ay < len(pad.axes) else 0.0)
            names = [routed.get(f"axis:{stick}.{k}") for k in gamepad.COMPASS]
            self._dial(lanes[j * n:(j + 1) * n], names, xy, f"{side} stick · {mode}")
        for stick in gamepad.DIAL_STICKS:
            self._row(dial_id(stick))
        self._button("pad.dial.swap", small=True)
        imgui.push_text_wrap_pos(0.0)
        if not here:
            imgui.text_disabled("this pad is on the other deck: it reads that deck's dials")
        if not any(routed.get(f"axis:{n}") for n in gamepad.DIAL_LANES):
            imgui.text_disabled("no route reads a dial (axis:L.N … R.NW)")
        imgui.pop_text_wrap_pos()

    def _dial(self, vals, names, xy, title: str) -> None:
        """One stick: its face on the left and its legend to the right, or, where that
        leaves the names no room (the GRAPH page's side pane, under `DIAL_WIDE`), the
        title, the face, then the legend under it."""
        n, row = gamepad.DIAL, self.DIAL_ROW
        step = math.tau / n
        origin = imgui.get_cursor_screen_pos()
        avail = imgui.get_content_region_avail().x
        wide = avail >= self.DIAL_WIDE
        bar_w = 64.0 if wide else 40.0
        if wide:
            r = self.DIAL_R
            h = max(2 * r + 8, (n + 1) * row + 4)
            c = imgui.ImVec2(origin.x + r + 4, origin.y + h / 2)
            lx = origin.x + 2 * r + 24
            y0 = origin.y + (h - (n + 1) * row) / 2       # the title's line
        else:
            r = min(self.DIAL_R, (avail - 8) / 2)
            c = imgui.ImVec2(origin.x + avail / 2, origin.y + row + 6 + r)
            lx = origin.x
            y0 = origin.y
            h = row + 2 * r + 12 + n * row + 4
        name_w = max(40.0, origin.x + avail - lx - 36 - bar_w - 10)
        dl = imgui.get_window_draw_list()

        def at(theta: float, rad: float) -> imgui.ImVec2:   # θ clockwise from up
            return imgui.ImVec2(c.x + rad * math.sin(theta), c.y - rad * math.cos(theta))

        dl.add_circle(c, r, u32(LINE), 48, 1.0)
        for k in range(n):
            a0, a1 = (k - 0.5) * step, (k + 0.5) * step
            v = float(vals[k]) if k < len(vals) else 0.0
            if v > 0.002:
                dl.path_clear()
                dl.path_line_to(c)
                dl.path_arc_to(c, r * v, a0 - math.pi / 2, a1 - math.pi / 2, 12)
                dl.path_fill_convex(u32(imgui.ImVec4(FILL.x, FILL.y, FILL.z, 0.25 + 0.6 * v)))
            dl.add_line(at(a0, 6), at(a0, r), u32(LINE), 1.0)
        if xy is not None:
            x, y = xy
            m = math.hypot(x, y)
            if m > 1.0:
                x, y = x / m, y / m
            dl.add_circle_filled(imgui.ImVec2(c.x + x * r, c.y + y * r), 4.0, u32(TEXT))
        # the legend: the title, then a line per sector, clockwise from N
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        dl.add_text(imgui.ImVec2(lx, y0), u32(DIM), title.upper())
        imgui.pop_font()
        first = y0 + row if wide else c.y + r + 8      # the N line
        for k in range(n):
            v = float(vals[k]) if k < len(vals) else 0.0
            name = names[k] if k < len(names) else None
            y = first + k * row
            live = v > 0.002
            dl.add_text(imgui.ImVec2(lx, y), u32(TEXT if live else FAINT), gamepad.COMPASS[k])
            dl.add_text(imgui.ImVec2(lx + 36, y),
                        u32(TEXT if live else DIM if name else FAINT),
                        fit_text(name, name_w) if name else "·")
            bx = lx + 36 + name_w + 10
            by = y + row / 2 - 2
            dl.add_rect_filled(imgui.ImVec2(bx, by), imgui.ImVec2(bx + bar_w, by + 4),
                               u32(LINE), 2.0)
            if live:
                dl.add_rect_filled(imgui.ImVec2(bx, by), imgui.ImVec2(bx + bar_w * min(v, 1.0),
                                                                    by + 4), u32(RED), 2.0)
        imgui.dummy(imgui.ImVec2(avail, h))

    def alerts(self) -> list[str]:
        """What the red banner says: a live render error or render stall
        (watchdog.RenderWatch), and why the dream worker is off."""
        out: list[str] = []
        rw = self.render_watch
        if rw is not None:
            try:
                out += rw.alerts()
            except Exception as e:  # noqa: BLE001 — the banner must not take the panel down
                out.append(f"render watch: {type(e).__name__}: {e}"[:160])
        if self.dream_error and not getattr(self, "_dream_waved", False):
            out.append(self.dream_error)        # dismissible: SYSTEM and LOOKBACK keep it
        return out

    def dismiss_alerts(self) -> None:
        """The banner's dismiss: the render watch's sticky lines and the
        dream's reason; a live render error or stall stays."""
        if self.render_watch is not None:
            self.render_watch.dismiss()
        self._dream_waved = True

    def _alert_banner(self) -> None:
        """A red strip across the bottom of the control window, one line per
        alert — impossible to miss from across the room — in front of every
        other window without taking focus. A render error that recovered
        and the warnings stay until "dismiss"."""
        lines = self.alerts()
        if not lines:
            return
        rw = self.render_watch
        io = imgui.get_io()
        imgui.set_next_window_pos(imgui.ImVec2(0, io.display_size.y), imgui.Cond_.always,
                                  imgui.ImVec2(0, 1))
        imgui.set_next_window_size(imgui.ImVec2(io.display_size.x, 0), imgui.Cond_.always)
        imgui.push_style_color(imgui.Col_.window_bg, imgui.ImVec4(0.62, 0.05, 0.05, 0.96))
        imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(1, 1, 1, 1))
        imgui.begin("##alerts", None,
                    imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_move
                    | imgui.WindowFlags_.no_focus_on_appearing | imgui.WindowFlags_.no_nav
                    | imgui.WindowFlags_.no_saved_settings)
        try:
            imgui.internal.bring_window_to_display_front(imgui.internal.get_current_window())
        except Exception:  # noqa: BLE001, S110 — an imgui without the internal call: drawn last
            pass
        for line in lines:
            imgui.text_wrapped(line)
        dismissible = (rw is not None and getattr(rw, "dismissible", False)) or (
            self.dream_error and not getattr(self, "_dream_waved", False))
        if dismissible and small_button("dismiss##alerts"):
            self.dismiss_alerts()
        imgui.end()
        imgui.pop_style_color(2)

    def _stall_status(self) -> None:
        """The stall log's line (watchdog.py), once it has entries."""
        wd = self.watchdog
        if wd is None:
            return
        if wd.error:
            imgui.text_colored(WARN, wd.error)
        line = wd.status()
        if line:
            imgui.text_colored(WARN, line)
            if imgui.is_item_hovered():
                tooltip("a frame took over 2 s, or kill -USR1 asked for a dump: "
                                  "every thread's stack, newest at the end")

    def _device_lines(self) -> None:
        """One line per listed device (plan 27 B1): `role · kind · status ·
        n sources · last` — `connected`, `lost` (the hardware is not there;
        it reconnects itself), `off` (its entry says so) or `error: …`
        (in the warning colour; the registry tries again). Replaces the
        MIDI and bridge lines; the HANDS page keeps its own status."""
        regs = self.devices
        if regs is None:
            imgui.text_disabled("no device registry")
            return
        for line in device_lines(regs):
            parts = line.split("  ·  ")
            if len(parts) > 2 and parts[2].startswith("error"):
                imgui.text_colored(WARN, line)
            else:
                imgui.text_disabled(line)
        if not len(regs):
            imgui.text_disabled("no devices — drag one from the player board's tray")
        for line in devices.wanted_lines(ui_graph.panel_wants(self)):
            imgui.text_colored(WARN, line)          # plan 40 T4: what the loadable patch waits for

    def _publish_lines(self) -> None:
        """Plan 32 T9: one line per output published out (a sink of the
        meta controller's): `<kind> out <name> — <fps> fps, readback <ms> ms`, or its
        error in the warning colour (media/publish.py)."""
        for line in publish.lines(getattr(self, "outputs", None)):
            if " — error" in line:
                imgui.text_colored(WARN, line)
            else:
                imgui.text_disabled(line)

    def _desk_log(self) -> None:
        """The desk event log (plan 24 C1): the last twenty presses on the
        APC40 — the control, what it did, the layer it was read on —
        newest first, under a fold so the page stays short."""
        lines = desk_log_lines(self.midi)
        if not lines:
            return
        opened = imgui.tree_node(f"desk log — the last {len(lines)} presses##desklog")
        if imgui.is_item_hovered():
            tooltip("each press on the desk: the control, what it did, and the "
                              "layer it was read on (both: the same on either layer)")
        if opened:
            for line in lines:
                imgui.text_disabled(line)
            imgui.tree_pop()

    def _learn_status(self) -> None:
        """The armed param and what the last learn did — a knob's or a
        hand's, so the line is there with no MIDI adapter at all; a refusal
        (the global layer, an invariant control — plan 13 D5, D6) in the
        warning colour. The ROUTING page's head shows the same line."""
        lrn = self.learn
        if lrn is None:
            return
        refused = getattr(lrn, "refused", False)
        if lrn.learning and not (refused and lrn.last):
            imgui.text_colored(RED, f"learning {lrn.learning} — {self._learn_hint()}")
        elif lrn.last:
            if refused:         # (a refusal leaves the learn armed, plan 17 fork 6: say both)
                still = f" — still learning {lrn.learning}" if lrn.learning else ""
                imgui.push_style_color(imgui.Col_.text, WARN)
                imgui.text_wrapped(f"learn: {lrn.last}{still}")
                imgui.pop_style_color()
            else:
                imgui.text_disabled(f"learn: {lrn.last}")
        imgui.text_disabled("right-click any control to learn or unbind")
