"""imgui control surface — every widget is a view onto one registry Param.

Built to be read across a room (ENGINEERING.md, control-surface conventions): black ground, soft rounded
controls, a rounded sans for words and a semibold mono for numbers, white
text, red #ff2b2b as the only accent. A fader fills red up to its value so
where it sits reads at a glance; the open page is a red pill on the rail.
The hint-readout system of the HTML is replaced by native tooltips.

Nothing here owns state. The panel draws params.Registry entries through a
handful of widget helpers (_fader, _slider, _combo, _check, _button) that
read the live value, draw, and write back through the Param, so a value
moved by a hotkey, the gamepad or a MIDI knob shows on the next frame with
no extra plumbing. Right-clicking any widget opens the binding menu: it
names the param id and offers Learn (the host's `learn.Learn`: a knob or a hand completes it) /
Unbind.

The surface is a left rail of pages (PAGES), one per registry group or
two; each page is a stack of sections, and a section whose group the
library knows carries its preset strip (ui_presets.py) under the title.
Every page fits the control window without scrolling. A modulated param
draws its *base* as the handle and a white ghost bar at the *effective*
value (params.py: `base` vs `eff_norm`), so the setting stays where the
user put it while a lane rides on top; its tooltip names the performer
(routing.py: the table's owner row). The layout — what sits where — is
the one hand-arranged thing left here.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable

from imgui_bundle import imgui

from . import (
    apc40,
    learn,
    ui_bands,
    ui_desk,
    ui_fx,
    ui_lfo,
    ui_lookback,
    ui_patterns,
    ui_presets,
    ui_routing,
)
from .analyzer import N_MAX
from .audio import AudioEngine
from .bands import CEIL, KNEE
from .control import Control
from .geometry import SHAPES, geom
from .hands import panel as ui_hands
from .outputs import HANDS, SCENE, SCENE_HANDS, route
from .params import PLANES, Kind, Param, Registry, build_registry
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

# the panel: a rail of pages on the left, the page beside it, a footer
MESSAGE_S = 4.0  # how long the footer's message slot shows a line after it changes
CANCEL_TIP = "click to cancel"  # the footer's armed-learn line: on it where it fits, and on hover
PANEL_W = 540   # leaves the cheat sheet its column in the control window (app.CONTROL_SIZE)
RAIL_W = 112
LABEL_W = 104    # the label column in a _row
HALF_LABEL_W = 78    # the label column in a half-width table cell (Panel.half)
LABEL_GAP = 12   # px between a label cell's text room and its control (Panel._label_cell)
ROUND = 8.0      # corner radius of frames; chips and grabs go rounder
# the dirty dot (plan 19 WP5): a filled red disc 12 px across beside a
# preset's name — where the "●" glyph left about 7 px of ink — and the
# rail's dot, radius 5, beside a page whose group has moved off its preset
DOT_R = 6.0
RAIL_DOT_R = 5.0

# ---- font atlas (ENGINEERING.md, control-surface conventions) ----
# Four roles. UI for words (buttons, combos, names), MICRO for the
# uppercase field labels (tracking baked in via glyph_extra_advance_x —
# imgui has no letter-spacing), NUM for value readouts (monospaced, so a
# moving number does not jitter), BIG for the signature cell-count
# readout. With the 1.92 dynamic atlas each face renders at every size.
#
# Weight is what makes type read at a distance. The SF faces are variable
# fonts and FreeType picks a named instance from the high 16 bits of the
# face index: SF Rounded's list runs Ultrathin … Black, so 6 is Medium and
# 8 Bold; SF Mono's runs Light … Heavy, so 4 is Semibold.

FONT_BASE = 16.0
FONT_MICRO = 12.5
FONT_NUM = 16.0
FONT_BIG = 52.0

_SF_ROUNDED = "/System/Library/Fonts/SFNSRounded.ttf"
_SF_MONO = "/System/Library/Fonts/SFNSMono.ttf"
# (path, face index) per role; the first that exists wins
_FONT_CANDIDATES = {
    "ui": [(_SF_ROUNDED, 6 << 16), ("/System/Library/Fonts/Avenir Next.ttc", 5),
           ("C:/Windows/Fonts/seguisb.ttf", 0),
           ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0)],
    "micro": [(_SF_ROUNDED, 8 << 16), ("/System/Library/Fonts/Avenir Next.ttc", 0),
              ("C:/Windows/Fonts/segoeuib.ttf", 0),
              ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)],
    "num": [(_SF_MONO, 4 << 16), ("/System/Library/Fonts/Menlo.ttc", 1),
            ("C:/Windows/Fonts/consolab.ttf", 0),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 0)],
}
# glyphs a face lacks (arrows, ⇧, ●, ×) come from these, merged in behind it
_FALLBACKS = [(_SF_MONO, 3 << 16), ("/System/Library/Fonts/Menlo.ttc", 0),
              ("/System/Library/Fonts/Apple Symbols.ttf", 0)]

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


def _micro(text: str, color: imgui.ImVec4 | None = None) -> None:
    """An uppercase field label in the tracked label face."""
    imgui.push_font(_FONTS["micro"], FONT_MICRO)
    imgui.text_colored(DIM if color is None else color, text.upper())
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


def chip(label: str, size: imgui.ImVec2 | None = None) -> bool:
    """A compact pill button — small_button, with room to breathe."""
    imgui.push_style_var(imgui.StyleVar_.frame_padding, CHIP_PAD)
    imgui.push_style_var(imgui.StyleVar_.frame_rounding, 999.0)
    hit = imgui.button(label, size if size is not None else imgui.ImVec2(0, 0))
    imgui.pop_style_var(2)
    return hit


def lit_chip(label: str, lit: bool, color: imgui.ImVec4 | None = None,
             size: imgui.ImVec2 | None = None) -> bool:
    """A chip that is solid red while on — a lit key, readable from the floor."""
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
        imgui.set_tooltip(tip)
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


def output_shows(sw, fx_on: bool, visible: bool, master: float) -> tuple[str, str]:
    """What one render output shows, in words, and why it is black ("" when
    it is not) — the OUTPUT page's "shows:" line (plan 21 WP4, fork F8:
    words, no picture). It is `outputs.route`'s answer for the output's
    switches, whether an effect is on and whether a hand shows (`visible`:
    the ghost hands are on and the layer drew, fork F7), with master × its
    own dim. The reasons: "nothing" (scene and hands off), "no hand" (the
    scene off and no hand showing), "dim" (its own dim at 0), "master" (the
    crossfader at black — the footer already says "dim black")."""
    key, after = route(sw, fx_on, visible)
    own = float(sw.dim)
    if key is None and not after:
        if not sw.scene and not sw.hands:
            return "black — nothing switched on", "nothing"
        return "black — the scene is off and no hand shows", "no hand"
    if own <= 0.0:
        return "black — dim 0", "dim"
    if master <= 0.0:
        return "black — master dim", "master"
    if key == SCENE:
        words = "scene + hands over the effects" if after else "scene"
    elif key == SCENE_HANDS:
        words = "scene + hands through the effects"
    elif key == HANDS:
        words = "hands through the effects"
    else:
        words = "hands"
    factor = min(1.0, master * own)
    if factor < 1.0:
        words += f" · {min(99, max(1, round(factor * 100)))}%"
    return words, ""


def chip_w(*labels: str) -> float:
    """Width of chips in a row at the default spacing — flush a group of
    them right with same_line(avail - chip_w(...))."""
    s = imgui.get_style()
    w = sum(imgui.calc_text_size(lb.split("##")[0]).x + 2 * CHIP_PAD.x for lb in labels)
    return w + s.item_spacing.x * max(len(labels) - 1, 0)


def button_w(*labels: str) -> float:
    """chip_w for full-size buttons (frame padding from the style)."""
    s = imgui.get_style()
    w = sum(imgui.calc_text_size(lb.split("##")[0]).x + 2 * s.frame_padding.x for lb in labels)
    return w + s.item_spacing.x * max(len(labels) - 1, 0)


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
    ("1–6", "planes XY XZ YZ XW YW ZW"),
    ("↑ ↓", "4D depth · hold accelerates"),
    ("[ ]  , .", "brightness · speed"),
    ("M", "mic on/off"),
    ("K / 0", "play-pause / restart track"),
    ("R", "reset view + camera"),
    ("F1–F8", "load preset · ⇧ saves"),
    ("B", "tap tempo · ⇧B LFO trigger"),
    ("Cmd+Z", "undo · ⇧ redo (or Ctrl+Z)"),
    ("Home", "home preset (fn ←)"),
    ("Cmd+R", "restart process"),
    ("H / ?", "panel / this sheet"),
    ("T", "overlay (if config.toml allows)"),
    ("G", "overlay: clicks through / back"),
    ("Esc / Q", "quit"),
    # Xbox-layout gamepad, Bluetooth or USB (gamepad.py holds the map)
    ("pad X / B", "previous / next in the preset list"),
    ("pad A Y", "faces · lines"),
    ("LB / RB", "previous / next shape"),
    ("d-pad", "brightness ↑↓ · speed ←→"),
    ("sticks", "orbit · zoom ↕ 4D spin ↔ — click resets each"),
    ("LT / RT", "4D depth out / in"),
    # any control ↔ any MIDI message, through the registry (midi.py)
    ("right-click", "a control: learn desk / hand / pad · unbind"),
    # the APC40's glyphs, as the desk above and the ROUTING rows print them
    ("APC40", "K D knobs · S faders · G row·col · B ⇧"),
]

# ---- the pages: (key, rail label, the group — or groups — whose dirty dot the rail shows) ----
# One page per registry group where a group is a module of its own; the
# view group is big enough to split into View / Faces & Pattern / Bitmap,
# and those two sub-pages say so in their section notes. The audio page
# holds the source and the master faders (the level into the analyser);
# the analyzer page the scene and meters, then the band editor
# (ui_bands.py); the routing page is the matrix (ui_routing.py); the fx
# page the effect stack (ui_fx.py); the faces page the pattern browser
# and its eight inputs (ui_patterns.py); the hands page is the Ultraleap live
# view and setup (hands/panel.py); the lfo page the clock and the four
# LFOs (ui_lfo.py).
PAGES = [
    ("output", "output", "output"),
    ("view", "view", "view"),
    ("faces", "faces", "pattern"),
    ("bitmap", "bitmap", None),
    ("camera", "camera", "camera"),
    ("lookback", "lookback", "dream"),
    ("fx", "fx", "fx"),
    ("audio", "audio", "master"),
    ("analyzer", "analyzer", "band"),
    ("routing", "routing", None),
    ("lfo", "lfo", ("lfo", "tempo")),
    ("hands", "hands", "hands"),
    ("presets", "presets", "presets"),     # the loaded preset's dirty dot
    ("system", "system", None),
]
PAGE_KEYS = [k for k, _, _ in PAGES]


class Panel:
    def __init__(self, control: Control, audio: AudioEngine, view: ViewState, renderer=None,
                 bank=None, registry: Registry | None = None, library=None):
        self.control = control
        self.audio = audio
        self.view = view
        self.renderer = renderer
        # app.restart (the SYSTEM page's button, Cmd+R's param) sets it; app.frame
        # polls it after the panel draws and restarts the process
        self.restart_requested = False
        self.library = library      # library.Library, or None: no strips, no project row
        # the F1–F8 preset bank is the open project's (library.Project)
        self.bank = bank if bank is not None else (
            library.project if library is not None else None
        )
        self.reg = registry if registry is not None else build_registry(
            view, control, audio, self.bank
        )
        self.pin_in = [0.0] * N_MAX
        self.pin_out = [0.0] * N_MAX
        self.open = True
        self.cheatsheet = False     # off at every launch; / brings it up (plan 16 WP1)
        self.desk = True            # the APC40, left of the panel; the whole window without it
        self.page = 1               # index into PAGES; the view page opens first
        self.ghosts = 0             # ghost markers drawn this frame (tests read it)
        self._file_dialog = None
        self._bmp_dialog = None
        self.reloader = None  # set by app.py; panel only reads status off it
        self.config_error = ""  # set by app.py: config.toml failed to parse (SYSTEM page)
        self.config_notes: list[str] = []  # set by app.py: config.toml wants a rename
        self.dream_error = ""  # set by app.py: why the dream worker is off (SYSTEM, LOOKBACK)
        self.watchdog = None   # set by app.py (watchdog.Watchdog): the stall log line
        self.render_watch = None   # set by app.py (watchdog.RenderWatch): the red banner
        self.midi = None      # set by app.py when an adapter is up (midi.MidiIO)
        self.pad = None       # set by app.py unless [gamepad] enabled = false (gamepad.Pad)
        self.learn = None     # set by app.py: the armed param and the held question (learn.Learn)
        self.undo = None      # set by app.py (undo.Undo): its status shows in the footer
        self.bridge = None    # set by app.py when [bridge] is enabled (bridge.Bridge)
        self.router = None    # set by app.py (routing.Router); else found via midi's table
        self.output = None    # set by app.py (overlay.Output); its params draw below
        self.hands = None          # set by app.py when the tracker is on (hands.HandsIO)
        self.hand_settings = None  # set by app.py (hands.HandSettings): the HANDS page
        self.clock = None          # set by app.py (tempo.Clock): the LFO page's beat light
        self.lfos = None           # set by app.py (lfo.LFOs): the LFO page's scopes
        self._register_panel_params()

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
        r.enum("ui.page", "Page", lambda: self.page,
               lambda i: setattr(self, "page", int(i)), [lb for _, lb, _ in PAGES],
               group="ui", persist=False, modulatable=False,
               tip="Which page of the panel is open.")

    # ---- binding menu: every widget gets one on right-click ----

    def _ctx(self, a: Param, key: str = "", extra=None) -> None:
        """The param's context menu, attached to the last drawn item.

        `a` is the drawn param — the bindings hang off it; the modulation
        line reads the one it stands for (a band.sel.* alias → its band).
        `key` tells apart several items that stand for one param (the rail's
        pills all set ``ui.page``), so each gets its own popup. `extra`,
        when given, is called inside the popup after the param's own items
        to draw the caller's (a bank slot's "put preset here…")."""
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
        if lrn is None:
            imgui.text_disabled("no learn")
        elif lrn.learning == a.id:
            imgui.text_colored(RED, self._learn_hint())
            if imgui.menu_item_simple("Cancel learn"):
                lrn.arm(None)
        else:
            self._ctx_learn(a, p)
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
        imgui.set_tooltip(f"click: put {c.glyph} on {a.label or a.id}")
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
        the table: the loaded preset's desk rows, the routes ("(off)" when
        disabled; the hand rows through hands/panel.py), then the session's
        rows, dim — those are never an item (D5, D6). Returns (the desk
        rows, the routes) an Unbind would remove."""
        table = self._table()
        if table is None:
            return [], []
        # the same question `Learn.unbind` asks, so the lines are what it removes
        desk, routes, session = learn.bound(table, (a.id, p.id))
        for b in desk:
            op = "" if b.op in ("abs", "rel") else f" · {ui_routing._op_text(b)}"
            imgui.text(self._row_name(b) + op)
        ui_hands.ctx_rows(self, p, gate=False)
        for b in routes:                # ctx_rows drew the hand's rows on the real param
            if b.scheme != "hand" or b.target != p.id or self.router is None:
                imgui.text(self._row_name(b) + ("" if b.enabled else " (off)"))
        for b in session:
            where = "global layer" if b.layer == "global" else "invariant"
            imgui.text_disabled(f"{self._row_name(b)} · {where}")
        return desk, routes

    def _ctx_unbind(self, a: Param, p: Param, desk: list, routes: list) -> None:
        """The one Unbind (plan 17 WP1): drawn only when it would remove
        something — a plain item with one kind bound, a submenu (desk /
        route / both) with both. `Learn.unbind` does it: one undo step, the
        loaded preset edited, no file written."""
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

    def _ctx_learn(self, a: Param, p: Param) -> None:
        """The Learn items of a param not armed (plan 17 WP2, fork 5).
        **Learn desk**: wherever a desk row can go — not a file path, not
        SHIFT's own param (what `ui_routing._desk_targets` leaves out) —
        with or without a MIDI adapter. **Learn hand ▸ left / right**: only
        with a tracker, on a param a hand can drive (the real one is
        modulatable), for the sides the rig's axes have. **Learn pad**:
        while a gamepad is connected, wherever Learn desk is offered — a
        button, the D-pad, a stick or a trigger completes it
        (`gamepad.learn_from`)."""
        lrn = self.learn
        if self._desk_target(a) and imgui.menu_item_simple("Learn desk"):
            lrn.arm(a.id, "desk")
        sides = self._hand_sides() if p.modulatable else []
        if sides and imgui.begin_menu("Learn hand"):
            for side in sides:
                if imgui.menu_item_simple(side):
                    lrn.arm(a.id, f"hand:{side}")
            imgui.end_menu()
        pad = getattr(self, "pad", None)
        if (pad is not None and pad.on and self._desk_target(a)
                and imgui.menu_item_simple("Learn pad")):
            lrn.arm(a.id, "pad")

    def _hand_sides(self) -> list[str]:
        """The hands this rig's axes belong to, left first; none without a
        tracker."""
        axes = getattr(self.hands, "axes", None) or []
        return [s for s in ("left", "right") if any(getattr(x, "side", None) == s for x in axes)]

    def _learn_hint(self) -> str:
        """What the armed learn waits for (its `want`, plan 17 WP2), in the
        words the menu, the footer, ROUTING and SYSTEM all print. A bare
        learn (`want` None) waits for whatever this rig has."""
        want = getattr(self.learn, "want", None)
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
            imgui.set_tooltip(t)

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
        b = r.table.owner(p.id) if r is not None else None
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
        x = r0.x + inset + (r1.x - r0.x - 2 * inset) * p.eff_norm
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
            imgui.set_tooltip(self._mod_line(p))
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
        span = r1.x - r0.x - 2 * half
        xa = r0.x + half + span * origin
        xb = r0.x + half + span * min(max(norm, 0.0), 1.0)
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

    # ---- widgets: each one reads, draws and writes a Param ----

    def _real(self, p: Param) -> Param:
        """The param behind a band.sel.* alias — where the base and the
        modulation state live. An alias reads the object, so through it a
        fader would show the *effective* value and write the base back."""
        return self.reg.real(p)

    def _fader(self, pid: str) -> bool:
        """Full-width taper fader: label and readout over a filled track, detent notch."""
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
        changed, pos2 = self._track(
            lambda: imgui.slider_int("##s", pos, 0, p.steps,
                                     text.replace("%", "%%") if inside else ""),
            p.norm, self._origin(p), p.steps, knob=not inside,
        )
        imgui.pop_font()
        imgui.pop_style_var()
        self._tip(a, lambda: self._hint(a, p))
        self._ctx(a)
        self._learn_frame(a)
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        half = self._grab_half(r1.x - r0.x, p.steps)
        if p.taper is not None and p.taper.unity is not None:
            # detent notch: ticks at the fader position the grab centre
            # occupies at unity (frame inset by grab padding + half grab)
            nx = r0.x + half + (r1.x - r0.x - 2 * half) * p.taper.unity / p.steps
            dl = imgui.get_window_draw_list()
            notch = u32(imgui.ImVec4(1, 1, 1, 0.55))
            dl.add_line(imgui.ImVec2(nx, r0.y + 2), imgui.ImVec2(nx, r0.y + 6), notch, 2.0)
            dl.add_line(imgui.ImVec2(nx, r1.y - 6), imgui.ImVec2(nx, r1.y - 2), notch, 2.0)
        self._ghost(p, half)
        imgui.pop_id()
        if changed and pos2 != pos:
            p.set_position(pos2)
            return True
        return False

    def _slider(self, pid: str, width: float = -1) -> bool:
        """Compact slider with the readout inside — untapered ranges."""
        a = self.reg[pid]
        p = self._real(a)
        imgui.set_next_item_width(width)
        v = p.base
        # the readout is imgui's printf format: a "%" in it ("60%") is doubled
        text = (self._mod_text(p) if p.modulated else p.text()).replace("%", "%%")
        imgui.push_font(_FONTS["num"], FONT_NUM)
        if p.integer:
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
        self._tip(a, lambda: self._hint(a, p))
        self._ctx(a)
        self._learn_frame(a)
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        self._ghost(p, self._grab_half(r1.x - r0.x, steps))
        if changed:
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
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        imgui.get_window_draw_list().add_text(
            imgui.ImVec2(pos.x, pos.y + (fh - FONT_MICRO) / 2 - 1),
            u32(DIM if color is None else color), text.upper())
        imgui.pop_font()
        imgui.dummy(imgui.ImVec2(width - LABEL_GAP, fh))
        imgui.same_line(0, LABEL_GAP)

    def _row(self, pid: str, width: float = -1, label: str | None = None,
             label_w: float = LABEL_W) -> bool:
        """A labelled compact slider: label in a column, slider beside it."""
        p = self.reg[pid]
        self._label_cell(p.label if label is None else label, width=label_w)
        self._ctx_label(p)      # the label opens the menu the slider's `_ctx` draws
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

    def _combo(self, pid: str, width: float = -1, tip: str | None = None) -> bool:
        a = self.reg[pid]
        p = self._real(a)
        imgui.set_next_item_width(width)
        changed, i = imgui.combo(f"##{pid}", p.base, p.names)
        self._tip(a, tip)
        self._ctx(a)
        self._learn_frame(a)
        self._mod_dot(p)
        if changed:
            p.set(i)
        return changed

    def _check(self, pid: str, label: str | None = None) -> bool:
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
        """A toggle drawn as a chip that goes solid red while on (plane keys, the preset bank)."""
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
            imgui.same_line(imgui.get_content_region_avail().x - _micro_width(note) - 4)
            _micro(note, FAINT)
        lib = self.library
        if group is not None and lib is not None and lib.reg is not None:
            ui_presets.strip(self, group)
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
                imgui.set_tooltip(f"{name} {lo:.0f}–{hi:.0f} Hz{self._lane_plane(i)}")
            # every meter has the menu (plan 17 WP3), each under its own
            # key — the key the rail's pills use — so no two popups share
            # an id with each other or with the band combo's on a page
            self._ctx(self.reg["band.select"], f".{i}")
            self._learn_frame(self.reg["band.select"])   # armed from a meter: framed on it
        # band tags, centred under their bars, in the micro face
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        for i, name in enumerate(a.band_names):
            tw = imgui.calc_text_size(name).x
            imgui.set_cursor_screen_pos(
                imgui.ImVec2(origin.x + i * (bw + gap) + (bw - tw) / 2, origin.y + mh + 4)
            )
            imgui.text_colored(RED if i == self.control.selb else DIM, name)
        imgui.pop_font()
        imgui.set_cursor_screen_pos(imgui.ImVec2(origin.x, origin.y + mh + 4 + FONT_MICRO + 4))

    # ---- main draw: rail · page · footer ----

    def draw(self, dt: float, fps: float) -> None:
        try:
            self._draw(dt, fps)
        finally:
            # the red banner, its own window, last and in front: a render
            # window that stopped or a dream worker that is off shows even
            # with the panel hidden or a page that raised
            self._alert_banner()

    def _draw(self, dt: float, fps: float) -> None:
        # Replace / Keep, its own window, before anything can return: a
        # held hand learn is never parked behind a hidden or collapsed panel
        ui_routing.modal(self)
        ui_desk.tick(self)      # a picked control lets go by itself (ui_desk.PICK_S)
        if self.cheatsheet:
            self._draw_cheatsheet()
        if getattr(self, "desk", True):     # (a Panel from before a hot reload)
            ui_desk.diagram(self)
        if not self.open:
            return
        io = imgui.get_io()
        imgui.set_next_window_pos(
            imgui.ImVec2(io.display_size.x - PANEL_W - 12, 12), imgui.Cond_.once
        )
        imgui.set_next_window_size(imgui.ImVec2(PANEL_W, io.display_size.y - 24),
                                   imgui.Cond_.once)
        opened, self.open = imgui.begin("CONTROLS", self.open)
        # where the panel is: the desk takes the room left of it (ui_desk.room;
        # drawn before the panel, it reads this next frame)
        self._panel_x = imgui.get_window_pos().x
        if not opened:
            imgui.end()
            return
        self.ghosts = 0
        self.page = max(0, min(self.page, len(PAGES) - 1))
        foot = imgui.get_frame_height_with_spacing()
        self._rail(foot)
        imgui.same_line()
        # the page: a child so its own scroll, if it ever needs one, never
        # moves the rail; every page is laid out to fit without it
        if imgui.begin_child("##page", imgui.ImVec2(0, -foot)):
            key = PAGE_KEYS[self.page]
            # a desk control is picked and can be mapped (plan 17 WP4): the
            # page is drawn disabled — dimmed, no widget takes a click — and
            # the click on a param is `_ctx_pick`'s. Never ROUTING: there the
            # picked control's own line is what the user came for. The rail
            # and the footer are outside it: pages change, the line lets go
            self._picking = key != "routing" and ui_desk.picking(self) is not None
            if self._picking:
                imgui.begin_disabled()
            try:
                getattr(self, f"_page_{key}")(dt)
            finally:
                if self._picking:
                    imgui.end_disabled()
                self._picking = False
        imgui.end_child()
        self._footer(fps)
        imgui.end()

    def _rail(self, foot: float) -> None:
        """The page list down the left: one pill per page, the open one solid
        red, a dot where the page's group has moved off its preset."""
        if not imgui.begin_child("##rail", imgui.ImVec2(RAIL_W, -foot)):
            imgui.end_child()
            return
        r0 = imgui.get_window_pos()
        dl = imgui.get_window_draw_list()
        w, h = RAIL_W - 12, FONT_MICRO + 16
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        for k, (_key, label, group) in enumerate(PAGES):
            lit = k == self.page
            p0 = imgui.get_cursor_screen_pos()
            if imgui.invisible_button(f"##page{k}", imgui.ImVec2(w, h)):
                self.reg["ui.page"].set(k)
            hov = imgui.is_item_hovered()   # the pill's hover, read before the
            imgui.pop_font()                # menu becomes the last item; the menu
            self._ctx(self.reg["ui.page"], f".{k}")   # opens in the panel's own face
            imgui.push_font(_FONTS["micro"], FONT_MICRO)
            p1 = imgui.ImVec2(p0.x + w, p0.y + h)
            if lit or hov:
                dl.add_rect_filled(p0, p1, u32(RED) if lit else
                                   imgui.get_color_u32(imgui.Col_.button_hovered), h / 2)
            dl.add_text(imgui.ImVec2(p0.x + 12, p0.y + (h - FONT_MICRO) / 2 - 1),
                        u32(imgui.ImVec4(1, 1, 1, 1) if lit else TEXT if hov else DIM),
                        label.upper())
            groups = (group,) if isinstance(group, str) else (group or ())
            if any(ui_presets.dirty(self, g, polled=True) for g in groups):
                dl.add_circle_filled(imgui.ImVec2(p1.x - 11, p0.y + h / 2), RAIL_DOT_R,
                                     u32(imgui.ImVec4(1, 1, 1, 1) if lit else RED))
        imgui.pop_font()
        # the rule between rail and page
        x = r0.x + RAIL_W - 1
        dl.add_line(imgui.ImVec2(x, r0.y), imgui.ImVec2(x, r0.y + imgui.get_window_height()),
                    u32(LINE))
        imgui.end_child()

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
        u, lib, lrn = getattr(self, "undo", None), self.library, getattr(self, "learn", None)
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
            room -= imgui.calc_text_size(f"{lib.project.name} ●").x + 2 * gap
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
                imgui.set_tooltip(f"{note} ({tip})" if tip else note)
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
            proj = lib.project
            text = f"{proj.name}{' ●' if proj.is_dirty() else ''}"
            imgui.same_line(imgui.get_content_region_avail().x - imgui.calc_text_size(text).x)
            imgui.text_colored(RED if proj.is_dirty() else DIM, text)
            if imgui.is_item_hovered():
                imgui.set_tooltip("the open show — PRESETS page")

    # ---- pages ----

    def _page_output(self, dt: float) -> None:
        """Where the render window shows: screen, fullscreen, overlay (overlay.py)."""
        self._section("output", "output", note="T overlay · G click-through")
        if self.output is None or "output.overlay" not in self.reg:
            imgui.text_disabled("no render window attached")
            return
        if "output.dim" in self.reg:        # the master dim: the crossfader (plan 15 WP3)
            self._row("output.dim")
            # a driver that refused the dim's program: the fader moves and
            # the picture does not — say so here (Renderer.dim_error)
            err = getattr(self.renderer, "dim_error", "")
            if err:
                imgui.text_colored(WARN, f"{err} — the picture is not dimmed")
        self._output_blocks()
        if len(self.reg["output.monitor"].names) > 1:
            self._combo("output.monitor")
        if "output.render" in self.reg:     # the render cap, on the toggles' row
            size = getattr(getattr(self.renderer, "scene", None), "size", None)
            tip = self.reg["output.render"].tip
            self._combo("output.render", width=96,
                        tip=f"{tip}\nDrawing {size[0]}×{size[1]} now." if size else None)
            imgui.same_line()
        self._check("output.fullscreen")
        imgui.same_line()
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
        try:
            fx_on = bool(r.fx.active())
        except Exception:  # noqa: BLE001 — no renderer, or a stand-in
            fx_on = False
        visible = bool((getattr(r, "stats", None) or {}).get("layer", False))
        dim = self.reg.get("output.dim")
        return fx_on, visible, (dim.value if dim is not None else 1.0)

    def black_outputs(self) -> list[int]:
        """The opened outputs showing nothing for a reason other than the
        master dim (which the footer already says): the footer names them
        on every page (plan 21 WP4)."""
        fx_on, visible, master = self._outputs_now()
        return [sl.n for sl in (getattr(self, "outputs", None) or [])
                if sl.opened and output_shows(sl.switches, fx_on, visible, master)[1]
                not in ("", "master")]

    @staticmethod
    def _black_text(ns: list[int]) -> str:
        if not ns:
            return ""
        which = f"output {ns[0]}" if len(ns) == 1 else f"outputs {', '.join(map(str, ns))}"
        return f"·  {which} black"

    def _output_blocks(self) -> None:
        """One block per render output the config lists (plan 21 WP4): its
        number and name and its three switches, its own dim (with two or
        more outputs), why a switch can do nothing, and "shows:" — what it
        shows in words (fork F8), in the warning colour when it is black.
        An output that did not open is one disabled line saying why; under
        the blocks, which output paces the loop and the frame's size."""
        slots = getattr(self, "outputs", None) or []
        if not slots:
            return
        several = len(slots) > 1
        fx_on, visible, master = self._outputs_now()
        ghost = self.reg.get("ghost.on")
        # the switches line up after the widest "N  name", which is cut so
        # the three ticks always fit the page's width
        ticks = sum(imgui.calc_text_size(s).x for s in ("scene", "hands", "through effects"))
        ticks += 3 * (imgui.get_frame_height() + 2 * imgui.get_style().item_inner_spacing.x)
        ticks += 2 * imgui.get_style().item_spacing.x
        room = max(imgui.get_content_region_avail().x - ticks - 8, 40)
        labels = {sl.n: fit_text(f"{sl.n}  {sl.name}" if sl.name else f"{sl.n}", room)
                  for sl in slots}
        col = imgui.get_cursor_pos_x() + 8 + max(imgui.calc_text_size(t).x
                                                 for t in labels.values())
        for sl in slots:
            pre = f"output.{sl.n}"
            name = sl.name or ("output" if several else "")
            if not sl.opened or f"{pre}.scene" not in self.reg:
                imgui.text_disabled(fit_text(f"{sl.n}  {name} — {sl.missing or 'not opened'}",
                                             imgui.get_content_region_avail().x))
                continue
            imgui.align_text_to_frame_padding()
            imgui.text(labels[sl.n])
            imgui.same_line(col)
            self._check(f"{pre}.scene", "scene")
            imgui.same_line()
            self._check(f"{pre}.hands", "hands")
            imgui.same_line()
            self._check(f"{pre}.through", "through effects")
            # the mirror (plan 23 WP1): two ticks at the right of the dim row,
            # or of the "shows:" line when the output has no dim of its own
            flips = [(pid, t) for pid, t in ((f"{pre}.flip_x", "flip X"),
                                             (f"{pre}.flip_y", "flip Y")) if pid in self.reg]
            st = imgui.get_style()
            fw = sum(imgui.calc_text_size(t).x + imgui.get_frame_height()
                     + st.item_inner_spacing.x + st.item_spacing.x for _, t in flips)
            if f"{pre}.dim" in self.reg:
                self._row(f"{pre}.dim", width=-(fw + 8) if flips else -1, label="dim")
                for pid, t in flips:
                    imgui.same_line()
                    self._check(pid, t)
                flips = []
            sw = sl.switches
            why = []
            if sw.hands and ghost is not None and not ghost.value:
                why.append("hands: ghost hands are off (HANDS page)")
            elif sw.hands and getattr(self, "hands", None) is None:
                why.append("hands: no tracker")
            if sw.through and not fx_on:
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
                    imgui.set_tooltip(line)
            words, black = output_shows(sw, fx_on, visible, master)
            if not flips:
                imgui.text_colored(WARN if black else FAINT, f"shows: {words}")
                continue
            # no dim row: the ticks at the right of the "shows:" line, the
            # words cut to the room left of them
            avail = imgui.get_content_region_avail().x
            imgui.align_text_to_frame_padding()
            imgui.text_colored(WARN if black else FAINT,
                               fit_text(f"shows: {words}", max(avail - fw - 8, 40)))
            for k, (pid, t) in enumerate(flips):
                imgui.same_line(imgui.get_cursor_start_pos().x + avail - fw if k == 0 else 0.0)
                self._check(pid, t)
        if several:
            w, h = slots[0].size
            size = f" · frame {w}×{h}" if w and h else ""
            imgui.text_colored(FAINT, fit_text(f"paced by output 1{size} · below: output 1's "
                                               "window", imgui.get_content_region_avail().x))
        imgui.dummy(imgui.ImVec2(0, 2))

    def _page_view(self, dt: float) -> None:
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
        _micro(f"{g['n']}V {g['m']}E  ·  {sh.sym}")
        imgui.end_group()
        imgui.spacing()

        self._section("view", "view")
        self._combo("view.shape")
        self._fader("view.bright")
        self._fader("view.speed")
        self._fader("view.depth4")
        imgui.spacing()
        # the plane keys tile the row, solid red while a plane spins
        kw = (imgui.get_content_region_avail().x
              - imgui.get_style().item_spacing.x * (len(PLANES) - 1)) / len(PLANES)
        for p, name in enumerate(PLANES):
            if p:
                imgui.same_line()
            self._lit_button(f"view.plane.{name}", name, v.planes[p], width=kw)
        self._check("view.points")
        imgui.same_line()
        self._check("view.lines")
        imgui.same_line()
        self._check("view.rotate")
        imgui.same_line()
        self._check("view.faces")
        self._slider("view.instances")
        if v.instances > 1:
            # the field's one row: how the copies are laid out, how they
            # move, and — while they move — by how much and how fast
            self._combo("view.inst_layout", 84)
            imgui.same_line()
            self._combo("view.inst_motion", 96)
            if v.inst_motion:
                imgui.same_line()
                self._slider("view.inst_amp", 84)
                imgui.same_line()
                self._slider("view.inst_rate")
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

    def _page_bitmap(self, dt: float) -> None:
        """Bitmap layer, composited over the pattern in the face shader."""
        v = self.view
        self._section("bitmap", note="saved with view")
        if imgui.button("Load bitmap"):
            try:
                from imgui_bundle import portable_file_dialogs as pfd

                self._bmp_dialog = pfd.open_file(
                    "Choose a bitmap", "",
                    ["Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"],
                )
            except Exception as e:  # noqa: BLE001 — dialog is best-effort
                if self.renderer is not None:
                    self.renderer.bitmap_error = f"file dialog unavailable: {e}"
        if imgui.is_item_hovered():
            imgui.set_tooltip(
                "Image layered over the face pattern, with its own alpha "
                "fader and an oscillation path about the face centre."
            )
        if self._bmp_dialog is not None and self._bmp_dialog.ready():
            picked = self._bmp_dialog.result()
            self._bmp_dialog = None
            if picked:
                self.reg["view.bmp_file"].set(picked[0])
        imgui.same_line()
        self._path("view.bmp_file")
        if self.renderer is not None and self.renderer.bitmap_error:
            imgui.text_colored(WARN, f"bitmap: {self.renderer.bitmap_error}")
        if not v.bmp_file:
            imgui.text_disabled("no bitmap loaded — the faders below wait for one")
            return
        self._row("view.bmp_alpha")
        self._row("view.bmp_scale")
        self._label_cell("path")
        self._combo("view.bmp_mode", 140)
        if v.bmp_mode:
            imgui.same_line()
            self._slider("view.bmp_amp", 110)
            imgui.same_line()
            self._slider("view.bmp_rate")

    def _page_camera(self, dt: float) -> None:
        self._section("camera", "camera")
        self._row("camera.zoom")
        self._row("camera.yaw")
        self._row("camera.pitch")
        self._row("camera.pan.x")
        self._row("camera.pan.y")
        imgui.spacing()
        self._button("camera.reset", "Reset view")
        imgui.same_line()
        imgui.text_disabled("R  ·  stick click")

    def _page_lookback(self, dt: float) -> None:
        ui_lookback.page(self, dt)     # the frame history and its composite

    def _page_fx(self, dt: float) -> None:
        ui_fx.page(self, dt)           # the effect stack over the frame

    def _page_audio(self, dt: float) -> None:
        a = self.audio
        self._section("audio source")
        mic_on = a.on and a.mode == "mic"
        self._button("audio.mic", "Stop mic" if mic_on else "Listen to mic")
        imgui.same_line()
        if imgui.button("Load track"):
            try:
                from imgui_bundle import portable_file_dialogs as pfd

                self._file_dialog = pfd.open_file(
                    "Choose a track", "", ["Audio", "*.wav *.mp3 *.flac *.ogg"]
                )
            except Exception as e:  # noqa: BLE001 — dialog is best-effort
                a.error = f"file dialog unavailable: {e}"
        if a.on:
            imgui.same_line()
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
        else:
            imgui.text_disabled("no source — the shape spins on its own")

        # transport
        if a.mode == "file":
            self._button("audio.play", "Pause" if a.playing else "Play")
            imgui.same_line()
            self._button("audio.restart", "Restart")
            imgui.same_line()
            pos, dur = a.position(), a.duration()
            imgui.align_text_to_frame_padding()
            _readout(f"{int(pos // 60)}:{int(pos % 60):02d} / "
                     f"{int(dur // 60)}:{int(dur % 60):02d}", DIM)
        imgui.spacing()

        # the level into the analyser: what every band sees
        self._section("master", "master")
        self._fader("master.gain")
        self._fader("master.dyn")
        self._fader("master.trim")

    def _page_analyzer(self, dt: float) -> None:
        """Scene, meters, then the band editor (ui_bands.py): the
        spectrogram with the bands over it and the selected band's strip."""
        c = self.control
        self._section("bands", "band")
        # scene + reset-all (relabels to Undo while the window is open)
        self._label_cell("scene")
        self._combo("scene.select", -(button_w("Reset all") + imgui.get_style().item_spacing.x))
        imgui.same_line()
        self._button("scene.reset_all", "Undo" if c.undo_armed else "Reset all")
        imgui.spacing()
        self._meters(dt)
        ui_bands.section(self, dt)

    def _page_routing(self, dt: float) -> None:
        """The routing matrix — lanes → params (ui_routing.py)."""
        ui_routing.page(self, dt)

    def _page_lfo(self, dt: float) -> None:
        """The tap-tempo clock and the four LFOs (ui_lfo.py)."""
        ui_lfo.page(self, dt)

    def _page_hands(self, dt: float) -> None:
        """The Ultraleap hands: live view and setup (hands/panel.py)."""
        ui_hands.page(self, dt)

    def _page_presets(self, dt: float) -> None:
        """Plan 14 WP4, top to bottom: the show (its name, show ▾ · save ·
        save as · new), starts on ▾, the eight preset buttons, the preset
        strip, and "more" folded over the module presets (ui_presets)."""
        self._section("show")
        if self.library is None:
            imgui.text_disabled("no library attached")
        else:
            ui_presets.show_block(self)
            ui_presets.starts_on(self)
            imgui.spacing()
        ui_presets.preset_bank(self)
        imgui.spacing()
        ui_presets.preset_strip(self)
        imgui.separator()
        ui_presets.overview(self)

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
            lines = [(f"library: {missing} — NOT FOUND, saves are off "
                      "(restart once it is there)", True)]
        else:
            lines = [(f"library: {root}", False)]
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
                imgui.set_tooltip(
                    "this machine's own files: config.toml, bindings.json, windows.json, "
                    "hands.json, last_show, logs" if text.startswith("machine:") else
                    "presets and shows as JSON ([library] path, else $HYPERSPACE_HOME); "
                    "edit a file and the app follows")

    def _page_system(self, dt: float) -> None:
        self._section("system")
        self._check("ui.cheatsheet")
        imgui.same_line()
        if "ui.desk" in self.reg:   # (a registry from before a hot reload lacks it)
            self._check("ui.desk")
            imgui.same_line()
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
        imgui.spacing()
        self._section("midi")
        if "desk.slew" in self.reg:     # knob smoothing (a registry with no table lacks it)
            self._row("desk.slew")
        self._midi_status()
        self._learn_status()
        if "desk.pad.feel" in self.reg:    # the sticks' feel (routing._register_pad_feel)
            imgui.spacing()
            self._section("gamepad")
            self._row("desk.pad.feel")
            mode = self.reg["desk.pad.feel"].text()
            for k in {"follow": ("attack", "release"), "spring": ("hz", "damp")}.get(mode, ()):
                self._row(f"desk.pad.{k}")
        imgui.spacing()
        self._section("bridge")
        self._bridge_status()

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
        if dismissible and imgui.small_button("dismiss##alerts"):
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
                imgui.set_tooltip("a frame took over 2 s, or kill -USR1 asked for a dump: "
                                  "every thread's stack, newest at the end")

    def _bridge_status(self) -> None:
        """The DAW bridge's one sign of life (audit P3): off, a port error,
        no port yet, or the ports, the encoding and what has gone out."""
        b = self.bridge
        if b is None:
            imgui.text_disabled("no bridge — [bridge] enabled = false")
            return
        if b.error:
            imgui.text_colored(WARN, f"bridge: {b.error}")
            return
        if not b.on:
            imgui.text_disabled("bridge: no port")
            return
        imgui.text_disabled(f"bridge: {b.name}  ·  {b.encoding}, {b.room} lanes"
                            f"  ·  {b.sent} sent")

    def _midi_status(self) -> None:
        m = self.midi
        if m is None:
            imgui.text_disabled("no MIDI adapter")
            return
        if m.error:
            imgui.text_colored(WARN, f"MIDI: {m.error}")
            return
        if not m.on:
            imgui.text_disabled("MIDI: no device")
            return
        imgui.text_disabled(f"MIDI: {m.name}  ·  {len(m.bindings)} bindings")
        if m.last:
            imgui.same_line()
            imgui.text_disabled(f"·  {m.last}")

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
