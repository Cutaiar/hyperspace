"""imgui control surface — every widget is a view onto one registry Param.

Built to be read across a room (ENGINEERING §7): black ground, soft rounded
controls, a rounded sans for words and a semibold mono for numbers, white
text, red #ff2b2b as the only accent. A fader fills red up to its value so
where it sits reads at a glance; the open page is a red pill on the rail.
The hint-readout system of the HTML is replaced by native tooltips.

Nothing here owns state. The panel draws params.Registry entries through a
handful of widget helpers (_fader, _slider, _combo, _check, _button) that
read the live value, draw, and write back through the Param, so a value
moved by a hotkey, the gamepad or a MIDI knob shows on the next frame with
no extra plumbing. Right-clicking any widget opens the binding menu: it
names the param id and, when a MIDI adapter is attached, offers Learn /
Unbind.

The surface is a left rail of pages (PAGES), one per registry group or
two; each page is a stack of sections, and a section whose group the
library knows carries its preset strip (ui_presets.py) under the title.
Every page fits the control window without scrolling. A modulated param
draws its *base* as the handle and a white ghost bar at the *effective*
value (params.py: `base` vs `eff_norm`), so the setting stays where the
user put it while a lane rides on top. The layout — what sits where — is
the one hand-arranged thing left here.
"""

from __future__ import annotations

import math
import os

from imgui_bundle import imgui

from . import ui_bands, ui_fx, ui_lookback, ui_presets, ui_routing
from .analyzer import N_MAX
from .audio import AudioEngine, input_devices
from .bands import BANDS, CEIL, KNEE, NOM
from .control import Control
from .geometry import SHAPES, geom
from .params import (  # noqa: F401 — PATTERNS et al. re-exported for callers
    BMP_PATHS,
    INST_MOTION,
    PATTERNS,
    PLANES,
    Kind,
    Param,
    Registry,
    build_registry,
)
from .render import ViewState

# ---- palette: black ground, three greys of text, one red ----
RED = imgui.ImVec4(1.0, 43 / 255, 43 / 255, 1.0)
TEXT = imgui.ImVec4(0.96, 0.96, 0.96, 1.0)      # values, names: what is read first
DIM = imgui.ImVec4(0.70, 0.70, 0.72, 1.0)       # labels and idle state, still legible
FAINT = imgui.ImVec4(0.58, 0.58, 0.61, 1.0)     # notes and hints, the quietest text
WARN = imgui.ImVec4(1, 0.45, 0.35, 1)
FILL = imgui.ImVec4(1.0, 43 / 255, 43 / 255, 0.42)  # a fader's value fill
GHOST = imgui.ImVec4(1, 1, 1, 0.92)             # the effective value under modulation
LINE = imgui.ImVec4(0.24, 0.24, 0.26, 1.0)      # rules and frames

# meter landmarks (ENGINEERING §4): nominal 38.5%, knee 48.1% of full scale
PIN_AT = CEIL * 0.92
PIN_HOLD = 0.5

# the panel: a rail of pages on the left, the page beside it, a footer
PANEL_W = 540   # leaves the cheat sheet its column in the control window (app.CONTROL_SIZE)
RAIL_W = 112
LABEL_W = 104    # the label column in a _row
ROUND = 8.0      # corner radius of frames; chips and grabs go rounder

# ---- font atlas (ENGINEERING §7) ----
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
    ("F1–F8", "load theme · ⇧ saves"),
    ("Cmd+R", "restart process"),
    ("H / ?", "panel / this sheet"),
    ("T", "overlay: float over the screen"),
    ("G", "overlay: clicks through / back"),
    ("Esc / Q", "quit"),
    # Xbox-layout gamepad, Bluetooth or USB (gamepad.py holds the map)
    ("pad A B", "pause · next theme"),
    ("pad X Y", "points · faces"),
    ("LB / RB", "previous / next shape"),
    ("d-pad", "brightness ↑↓ · speed ←→"),
    ("sticks", "orbit · zoom — click resets"),
    ("LT / RT", "4D depth out / in"),
    ("view/menu", "panel / this sheet"),
    # any control ↔ any MIDI message, through the registry (midi.py)
    ("right-click", "a control: MIDI learn / unbind"),
]

# ---- the pages: (key, rail label, the group whose dirty dot the rail shows) ----
# One page per registry group where a group is a module of its own; the
# view group is big enough to split into View / Faces & Pattern / Bitmap,
# and those two sub-pages say so in their section notes. The audio page
# holds the source and the master faders (the level into the analyser);
# the analyzer page the scene and meters, then the band editor
# (ui_bands.py); the routing page is the matrix (ui_routing.py); the fx
# page the effect stack (ui_fx.py).
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
    ("presets", "presets", None),
    ("system", "system", None),
]
PAGE_KEYS = [k for k, _, _ in PAGES]


class Panel:
    def __init__(self, control: Control, audio: AudioEngine, view: ViewState, renderer=None,
                 presets=None, registry: Registry | None = None, library=None):
        self.control = control
        self.audio = audio
        self.view = view
        self.renderer = renderer
        self.library = library      # library.Library, or None: no strips, no project row
        self.presets = presets if presets is not None else (
            library.bank if library is not None else None
        )
        self.reg = registry if registry is not None else build_registry(
            view, control, audio, self.presets
        )
        self.devices = input_devices()
        self.device_sel = next(
            (k for k, d in enumerate(self.devices) if d["loopback"]), 0
        )
        self.pin_in = [0.0] * N_MAX
        self.pin_out = [0.0] * N_MAX
        self.open = True
        self.cheatsheet = True
        self.page = 1               # index into PAGES; the view page opens first
        self.ghosts = 0             # ghost markers drawn this frame (tests read it)
        self._file_dialog = None
        self._bmp_dialog = None
        self.reloader = None  # set by app.py; panel only reads status off it
        self.midi = None      # set by app.py when an adapter is up (midi.MidiIO)
        self.router = None    # set by app.py (routing.Router); else found via midi's table
        self.output = None    # set by app.py (overlay.Output); its params draw below
        self.restart_requested = False  # main loop polls after draw() and execv's
        self._register_panel_params()

    def _register_panel_params(self) -> None:
        """Params that only exist once there is a panel and an audio device list."""
        r = self.reg
        if "ui.panel" in r:
            return
        r.toggle("ui.panel", "Control panel",
                 lambda: self.open, lambda on: setattr(self, "open", bool(on)), group="ui",
                 persist=False, modulatable=False)
        r.toggle("ui.cheatsheet", "Cheat sheet",
                 lambda: self.cheatsheet,
                 lambda on: setattr(self, "cheatsheet", bool(on)), group="ui",
                 persist=False, modulatable=False)
        r.enum("ui.page", "Page", lambda: self.page,
               lambda i: setattr(self, "page", int(i)), [lb for _, lb, _ in PAGES],
               group="ui", persist=False, modulatable=False,
               tip="Which page of the panel is open.")
        r.trigger("app.restart", "Restart process",
                  lambda: setattr(self, "restart_requested", True), group="ui",
                  modulatable=False,
                  tip="Restart the process (Cmd+R). Full cold reload; view state is lost.")
        a = self.audio
        r.toggle("audio.mic", "Mic",
                 lambda: bool(a.on and a.mode == "mic"), self._set_mic, group="audio",
                 persist=False,
                 tip="Listen to the selected input device.")
        r.enum("audio.device", "Input device",
               lambda: self.device_sel, lambda i: setattr(self, "device_sel", i),
               lambda: [("● " if d["loopback"] else "") + d["name"] for d in self.devices],
               group="audio", persist=False, modulatable=False)

    def _set_mic(self, on: bool) -> None:
        a = self.audio
        if on and self.devices:
            if not (a.on and a.mode == "mic"):
                a.start_mic(self.devices[self.device_sel]["index"])
        elif not on and a.on and a.mode == "mic":
            a.stop()

    # ---- binding menu: every widget gets one on right-click ----

    def _ctx(self, p: Param) -> None:
        """The param's context menu, attached to the last drawn item."""
        if not imgui.begin_popup_context_item(f"##ctx.{p.id}"):
            return
        _micro(p.id, DIM)
        if p.modulated:
            imgui.text_disabled(f"modulated: {p.text()} → {self._eff_text(p)}")
        m = self.midi
        if m is None:
            imgui.text_disabled("no MIDI adapter")
        else:
            b = m.binding_for(p.id)
            if m.learning == p.id:
                imgui.text_colored(RED, "move a control…")
                if imgui.menu_item_simple("Cancel learn"):
                    m.learn(None)
            else:
                if b is not None:
                    imgui.text(b.describe())
                if imgui.menu_item_simple("Learn MIDI"):
                    m.learn(p.id)
                if b is not None and imgui.menu_item_simple("Unbind"):
                    m.unbind(p.id)
        ui_routing.ctx_item(self, p)    # "Route a lane here…" — the routing matrix
        imgui.end_popup()

    def _learn_frame(self, p: Param) -> None:
        """Red outline around the last item while it is armed to learn."""
        if self.midi is None or self.midi.learning != p.id:
            return
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        dl = imgui.get_window_draw_list()
        dl.add_rect(
            imgui.ImVec2(r0.x - 2, r0.y - 2), imgui.ImVec2(r1.x + 2, r1.y + 2),
            u32(RED), ROUND + 2, 2.0,
        )

    def _tip(self, p: Param, text: str | None = None) -> None:
        t = p.tip if text is None else text
        if t and imgui.is_item_hovered():
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
            imgui.set_tooltip(f"{p.label}: {p.text()} → {self._eff_text(p)} (modulated)")
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
        if p.alias and p.id.startswith("band.sel."):
            return self.reg.get(f"band.{self.control.selb}.{p.id[9:]}") or p
        return p

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
        text = f"{p.text()} → {self._eff_text(p)}" if p.modulated else p.text()
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
            lambda: imgui.slider_int("##s", pos, 0, p.steps, text if inside else ""),
            p.norm, self._origin(p), p.steps, knob=not inside,
        )
        imgui.pop_font()
        imgui.pop_style_var()
        self._tip(a)
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
        text = f"{p.text()} → {self._eff_text(p)}" if p.modulated else p.text()
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
        self._tip(a)
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
        `width` is the label column; a half-width table cell passes less
        (the offset is from the cell's own start)."""
        pos = imgui.get_cursor_screen_pos()
        fh = FONT_NUM + 2 * imgui.get_style().frame_padding.y
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        imgui.get_window_draw_list().add_text(
            imgui.ImVec2(pos.x, pos.y + (fh - FONT_MICRO) / 2 - 1),
            u32(DIM if color is None else color), text.upper())
        imgui.pop_font()
        imgui.dummy(imgui.ImVec2(width - 12, fh))
        imgui.same_line(width)

    def _row(self, pid: str, width: float = -1, label: str | None = None,
             label_w: float = LABEL_W) -> bool:
        """A labelled compact slider: label in a column, slider beside it."""
        p = self.reg[pid]
        self._label_cell(p.label if label is None else label, width=label_w)
        return self._slider(pid, width)

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

    def _check(self, pid: str) -> bool:
        a = self.reg[pid]
        p = self._real(a)
        changed, on = imgui.checkbox(f"{a.label}##{pid}", bool(p.base))
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
        """A toggle drawn as a chip that goes solid red while on (plane keys, themes)."""
        p = self.reg[pid]
        hit = lit_chip(f"{label}##{pid}", lit, color, imgui.ImVec2(width, 0))
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
        for key, action in CHEATSHEET:
            imgui.set_cursor_pos_x(x0 + col - _readout_width(key))
            _readout(key, RED)
            imgui.same_line(x0 + col + 14)
            imgui.text_colored(DIM, action)
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
        n = a.n   # N bands (plan 07); WP5b replaces this strip
        bw = (imgui.get_content_region_avail().x - (n - 1) * gap) / n
        u32 = imgui.color_convert_float4_to_u32
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
                # the legacy plane table drives six lanes by position until WP4b routes
                plane = (f" → {BANDS[i].pl} plane, {'forward' if BANDS[i].dir > 0 else 'reverse'}"
                         if n == 6 else "")
                imgui.set_tooltip(f"{name} {lo:.0f}–{hi:.0f} Hz{plane}")
            if i == 0:
                self._ctx(self.reg["band.select"])
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
        if self.cheatsheet:
            self._draw_cheatsheet()
        if not self.open:
            return
        io = imgui.get_io()
        imgui.set_next_window_pos(
            imgui.ImVec2(io.display_size.x - PANEL_W - 12, 12), imgui.Cond_.once
        )
        imgui.set_next_window_size(imgui.ImVec2(PANEL_W, io.display_size.y - 24),
                                   imgui.Cond_.once)
        opened, self.open = imgui.begin("CONTROLS", self.open)
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
            getattr(self, f"_page_{PAGE_KEYS[self.page]}")(dt)
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
            hov = imgui.is_item_hovered()
            p1 = imgui.ImVec2(p0.x + w, p0.y + h)
            if lit or hov:
                dl.add_rect_filled(p0, p1, u32(RED) if lit else
                                   imgui.get_color_u32(imgui.Col_.button_hovered), h / 2)
            dl.add_text(imgui.ImVec2(p0.x + 12, p0.y + (h - FONT_MICRO) / 2 - 1),
                        u32(imgui.ImVec4(1, 1, 1, 1) if lit else TEXT if hov else DIM),
                        label.upper())
            if group is not None and ui_presets.dirty(self, group, polled=True):
                dl.add_circle_filled(imgui.ImVec2(p1.x - 11, p0.y + h / 2), 3.5,
                                     u32(imgui.ImVec4(1, 1, 1, 1) if lit else RED))
        imgui.pop_font()
        self._ctx(self.reg["ui.page"])
        # the rule between rail and page
        x = r0.x + RAIL_W - 1
        dl.add_line(imgui.ImVec2(x, r0.y), imgui.ImVec2(x, r0.y + imgui.get_window_height()),
                    u32(LINE))
        imgui.end_child()

    def _footer(self, fps: float) -> None:
        imgui.separator()
        imgui.push_font(_FONTS["num"], FONT_MICRO + 1)
        imgui.text_colored(FAINT, f"{fps:5.1f} FPS")
        imgui.pop_font()
        if self.reloader is not None and self.reloader.status:
            imgui.same_line()
            imgui.text_disabled(f"·  {self.reloader.status}")
        lib = self.library
        if lib is not None and lib.reg is not None:
            proj = lib.project
            text = f"{proj.name}{' ●' if proj.is_dirty() else ''}"
            imgui.same_line(imgui.get_content_region_avail().x - imgui.calc_text_size(text).x)
            imgui.text_colored(RED if proj.is_dirty() else DIM, text)
            if imgui.is_item_hovered():
                imgui.set_tooltip("the open project — PRESETS page")

    # ---- pages ----

    def _page_output(self, dt: float) -> None:
        """Where the render window shows: screen, fullscreen, overlay (overlay.py)."""
        self._section("output", "output", note="T overlay · G click-through")
        if self.output is None or "output.overlay" not in self.reg:
            imgui.text_disabled("no render window attached")
            return
        if len(self.reg["output.monitor"].names) > 1:
            self._combo("output.monitor")
        self._check("output.fullscreen")
        imgui.same_line()
        self._check("output.overlay")
        self._check("output.passthrough")
        self._row("output.bg")
        self._row("output.alpha")
        if self.output.error:
            imgui.text_colored(WARN, self.output.error)

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
            self._combo("view.inst_motion", 140)
            if v.inst_motion:
                imgui.same_line()
                self._slider("view.inst_amp", 110)
                imgui.same_line()
                self._slider("view.inst_rate")
        imgui.spacing()

        # per-plane rate: what a lane drives to spin a plane (base 1, signed)
        self._section("rotation", "rot")
        for name in PLANES:
            self._row(f"rot.rate.{name}")

    def _page_faces(self, dt: float) -> None:
        self._section("faces & pattern", note="saved with view")
        self._check("view.faces")
        imgui.same_line()
        self._combo("view.pattern", 140)
        imgui.same_line()
        self._slider("view.pattern_mix")
        if self.renderer is not None and self.renderer.pattern_error:
            imgui.text_colored(WARN, f"GLSL: {self.renderer.pattern_error}")
        imgui.spacing()
        # the pattern's modulation inputs — u_bands to the shaders today;
        # base 1 is the un-driven look, a routed lane rides on it
        self._section("pattern inputs", "pattern")
        for k, p in enumerate(self.reg.group("pattern")):
            if p.kind is Kind.CONTINUOUS:
                self._row(p.id, label=f"mod {k + 1}")

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
        if self.devices:
            self._combo("audio.device")
        if a.error:
            imgui.text_colored(WARN, a.error)
        elif a.on:
            imgui.text_disabled(f"{a.label}  ·  {self.audio.sr / 1000:.0f} kHz")
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

    def _page_presets(self, dt: float) -> None:
        """The project and everything it carries: the theme bank, the modules."""
        self._section("project")
        if self.library is None:
            imgui.text_disabled("no library attached")
        else:
            ui_presets.project_row(self)
            imgui.spacing()
        ui_presets.theme_bank(self)
        imgui.spacing()
        imgui.separator()
        ui_presets.overview(self)

    def _page_system(self, dt: float) -> None:
        self._section("system")
        self._check("ui.cheatsheet")
        imgui.same_line()
        self._button("app.restart", "Restart process", small=True)
        if self.reloader is not None:
            imgui.text_disabled(f"hot reload: {self.reloader.status or 'watching'}")
            if self.reloader.error:
                imgui.text_colored(WARN, self.reloader.error)
        if self.library is not None:
            imgui.text_disabled(f"library: {self.library.home}")
            if imgui.is_item_hovered():
                imgui.set_tooltip("$HYPERSPACE_HOME — presets and projects as JSON; "
                                  "edit a file and the app follows")
        imgui.spacing()
        self._section("midi")
        self._midi_status()

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
        imgui.text_disabled(f"MIDI: {m.name}  ·  {len(m.map.bindings)} bindings")
        if m.learning:
            imgui.same_line()
            imgui.text_colored(RED, f"learning {m.learning}")
        elif m.last:
            imgui.same_line()
            imgui.text_disabled(f"·  {m.last}")
        imgui.text_disabled("right-click any control to learn or unbind")


def format_infinity(v: float) -> str:  # convenience for tests
    return "off" if not math.isfinite(v) else f"{v:g}"
