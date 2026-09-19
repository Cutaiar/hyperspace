"""imgui control surface — every widget is a view onto one registry Param.

Instrument-panel aesthetic per ENGINEERING §7: black ground, square corners
everywhere, hairline rules, white text, red #ff2b2b as the only accent.
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
Every page fits the control window's 820 px without scrolling. A
modulated param draws its *base* as the handle and a red hairline ghost
at the *effective* value (params.py: `base` vs `eff_norm`), so the
setting stays where the user put it while a lane rides on top. The
layout — what sits where — is the one hand-arranged thing left here.
"""

from __future__ import annotations

import math
import os

from imgui_bundle import imgui

from . import ui_presets
from .analyzer import N_MAX
from .audio import AudioEngine, input_devices
from .bands import BANDS, CEIL, KNEE, NOM, SHAPERS
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

RED = imgui.ImVec4(1.0, 43 / 255, 43 / 255, 1.0)
DIM = imgui.ImVec4(0.62, 0.62, 0.62, 1.0)
WARN = imgui.ImVec4(1, 0.4, 0.3, 1)

# meter landmarks (ENGINEERING §4): nominal 38.5%, knee 48.1% of full scale
PIN_AT = CEIL * 0.92
PIN_HOLD = 0.5

# the panel: a rail of pages on the left, the page beside it, a footer
PANEL_W = 420   # leaves the cheat sheet its column in an 820 px control window
RAIL_W = 76
LABEL_W = 78     # the micro-label column in a _row

# ---- monospace font atlas (ENGINEERING §7) ----
# Three roles, one face: BASE for controls and readouts, MICRO for the
# uppercase micro-labels (tracking baked in via glyph_extra_advance_x —
# imgui has no letter-spacing), BIG for the signature cell-count readout.
# With the 1.92 dynamic atlas one loaded font renders at every size.

FONT_BASE = 13.0
FONT_MICRO = 9.5
FONT_BIG = 44.0

_FONT_CANDIDATES = [
    "/System/Library/Fonts/SFNSMono.ttf",          # macOS: SF Mono
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "C:/Windows/Fonts/consola.ttf",                # Windows: Consolas
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]

_FONTS: dict[str, imgui.ImFont | None] = {"mono": None, "micro": None}


def load_fonts() -> None:
    """Build the monospace atlas; call once after create_context.

    Falls back silently to the imgui default face when no candidate file
    exists — every helper below passes None to push_font, which keeps the
    current face and only changes size, so nothing else needs to care.
    """
    io = imgui.get_io()
    path = next((p for p in _FONT_CANDIDATES if os.path.exists(p)), None)
    if path is None:
        return
    _FONTS["mono"] = io.fonts.add_font_from_file_ttf(path, FONT_BASE)
    cfg = imgui.ImFontConfig()
    cfg.glyph_extra_advance_x = 1.9  # ≈ .2em tracking at the micro size
    _FONTS["micro"] = io.fonts.add_font_from_file_ttf(path, FONT_MICRO, cfg)
    io.font_default = _FONTS["mono"]


def _micro(text: str, color: imgui.ImVec4 | None = None) -> None:
    """An uppercase micro-label in the tracked micro face."""
    imgui.push_font(_FONTS["micro"], FONT_MICRO)
    if color is None:
        imgui.text_disabled(text.upper())
    else:
        imgui.text_colored(color, text.upper())
    imgui.pop_font()


def _micro_width(text: str) -> float:
    """What _micro(text) will take, for right-aligning things beside it."""
    imgui.push_font(_FONTS["micro"], FONT_MICRO)
    w = imgui.calc_text_size(text.upper()).x
    imgui.pop_font()
    return w


def apply_style() -> None:
    s = imgui.get_style()
    for attr in (
        "window_rounding", "child_rounding", "frame_rounding", "popup_rounding",
        "scrollbar_rounding", "grab_rounding", "tab_rounding",
    ):
        setattr(s, attr, 0.0)  # square corners everywhere — considered, not default
    s.window_border_size = 1.0
    s.frame_border_size = 0.0
    put = imgui.Col_
    colors = {
        put.window_bg: (0.02, 0.02, 0.02, 0.96),
        put.child_bg: (0.0, 0.0, 0.0, 0.0),
        put.frame_bg: (0.09, 0.09, 0.09, 1.0),
        put.frame_bg_hovered: (0.14, 0.14, 0.14, 1.0),
        put.frame_bg_active: (0.18, 0.18, 0.18, 1.0),
        put.slider_grab: (1.0, 43 / 255, 43 / 255, 1.0),
        put.slider_grab_active: (1.0, 0.35, 0.35, 1.0),
        put.button: (0.10, 0.10, 0.10, 1.0),
        put.button_hovered: (0.18, 0.18, 0.18, 1.0),
        put.button_active: (0.30, 0.08, 0.08, 1.0),
        put.header: (0.14, 0.14, 0.14, 1.0),
        put.header_hovered: (0.20, 0.20, 0.20, 1.0),
        put.header_active: (0.24, 0.24, 0.24, 1.0),
        put.check_mark: (1.0, 43 / 255, 43 / 255, 1.0),
        put.separator: (0.22, 0.22, 0.22, 1.0),
        put.border: (0.25, 0.25, 0.25, 1.0),
        put.title_bg: (0.04, 0.04, 0.04, 1.0),
        put.title_bg_active: (0.07, 0.07, 0.07, 1.0),
        put.text: (0.92, 0.92, 0.92, 1.0),
        put.popup_bg: (0.05, 0.05, 0.05, 0.98),
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
# and those two sub-pages say so in their section notes. The analyzer
# page holds today's master faders, scene, meters and band strip as they
# are — WP5b replaces that one section with the band editor.
PAGES = [
    ("output", "output", "output"),
    ("view", "view", "view"),
    ("faces", "faces", "pattern"),
    ("bitmap", "bitmap", None),
    ("camera", "camera", "camera"),
    ("audio", "audio", None),
    ("analyzer", "analyzer", "band"),
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
        imgui.end_popup()

    def _learn_frame(self, p: Param) -> None:
        """Red outline around the last item while it is armed to learn."""
        if self.midi is None or self.midi.learning != p.id:
            return
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        dl = imgui.get_window_draw_list()
        dl.add_rect(
            imgui.ImVec2(r0.x - 1, r0.y - 1), imgui.ImVec2(r1.x + 1, r1.y + 1),
            imgui.color_convert_float4_to_u32(RED),
        )

    def _tip(self, p: Param, text: str | None = None) -> None:
        t = p.tip if text is None else text
        if t and imgui.is_item_hovered():
            imgui.set_tooltip(t)

    # ---- modulation ghosts: the base is the handle, the effective a hairline ----

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
        """A red hairline over the last slider at the effective position."""
        if not p.modulated:
            return
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        x = r0.x + inset + (r1.x - r0.x - 2 * inset) * p.eff_norm
        dl = imgui.get_window_draw_list()
        dl.add_line(imgui.ImVec2(x, r0.y + 1), imgui.ImVec2(x, r1.y - 1),
                    imgui.color_convert_float4_to_u32(RED), 1.0)
        self.ghosts += 1

    def _mod_dot(self, p: Param) -> None:
        """A red tick in the corner of the last item: a discrete param is being driven."""
        if not p.modulated:
            return
        r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        dl = imgui.get_window_draw_list()
        dl.add_rect_filled(imgui.ImVec2(r1.x - 4, r0.y + 1), imgui.ImVec2(r1.x - 1, r0.y + 4),
                           imgui.color_convert_float4_to_u32(RED))
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"{p.label}: {p.text()} → {self._eff_text(p)} (modulated)")
        self.ghosts += 1

    # ---- widgets: each one reads, draws and writes a Param ----

    def _real(self, p: Param) -> Param:
        """The param behind a band.sel.* alias — where the base and the
        modulation state live. An alias reads the object, so through it a
        fader would show the *effective* value and write the base back."""
        if p.alias and p.id.startswith("band.sel."):
            return self.reg.get(f"band.{self.control.selb}.{p.id[9:]}") or p
        return p

    def _fader(self, pid: str) -> bool:
        """Full-width taper fader: micro label, readout, detent notch."""
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
        tw = imgui.calc_text_size(text).x
        label = f"{a.label}  ·  {tag}"
        if _micro_width(label) + tw + 12 > avail:
            label = a.label
        inside = _micro_width(label) + tw + 12 > avail
        _micro(label)
        self._tip(a)
        if not inside:
            imgui.same_line(avail - tw - 4)
            imgui.text(text)
        imgui.set_next_item_width(-1)
        changed, pos2 = imgui.slider_int("##s", pos, 0, p.steps, text if inside else "")
        self._tip(a)
        self._ctx(a)
        self._learn_frame(a)
        half = imgui.get_style().grab_min_size / 2 + 2.0
        if p.taper is not None and p.taper.unity is not None:
            # detent notch: ticks at the fader position the grab centre
            # occupies at unity (frame inset by grab padding + half grab)
            r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            nx = r0.x + half + (r1.x - r0.x - 2 * half) * p.taper.unity / p.steps
            dl = imgui.get_window_draw_list()
            notch = imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.35))
            dl.add_line(imgui.ImVec2(nx, r0.y), imgui.ImVec2(nx, r0.y + 3), notch)
            dl.add_line(imgui.ImVec2(nx, r1.y - 3), imgui.ImVec2(nx, r1.y), notch)
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
        if p.integer:
            changed, nv = imgui.slider_int(f"##{pid}", int(v), int(p.lo), int(p.hi), text)
        else:
            flags = imgui.SliderFlags_.logarithmic if p.log else 0
            changed, nv = imgui.slider_float(f"##{pid}", float(v), p.lo, p.hi, text, flags)
        self._tip(a)
        self._ctx(a)
        self._learn_frame(a)
        self._ghost(p, imgui.get_style().grab_min_size / 2 + 2.0)
        if changed:
            p.set_value(nv)
        return changed

    def _row(self, pid: str, width: float = -1, label: str | None = None) -> bool:
        """A labelled compact slider: micro label in a column, slider beside it."""
        p = self.reg[pid]
        _micro(p.label if label is None else label)
        self._tip(p)
        imgui.same_line(LABEL_W)
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
        hit = imgui.small_button(text) if small else imgui.button(text)
        self._tip(p)
        self._ctx(p)
        self._learn_frame(p)
        if hit:
            p.toggle()  # fires a trigger, flips a toggle
        return hit

    def _lit_button(self, pid: str, label: str, lit: bool, small: bool = True,
                    color: imgui.ImVec4 | None = None) -> bool:
        """A toggle drawn as a red-when-on text button (plane keys, themes)."""
        p = self.reg[pid]
        imgui.push_style_color(imgui.Col_.text, color or (RED if lit else DIM))
        hit = (imgui.small_button if small else imgui.button)(f"{label}##{pid}")
        imgui.pop_style_color()
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
        imgui.text_disabled(v.rsplit("/", 1)[-1][:28] if v else "none")
        self._tip(p, v or p.tip)
        self._ctx(p)
        self._learn_frame(p)
        if v and clear:
            imgui.same_line()
            if imgui.small_button(f"clear##{pid}"):
                p.set("")

    # ---- sections: a micro title, the group's preset strip, a hairline ----

    def _section(self, title: str, group: str | None = None, note: str | None = None) -> None:
        """Header of a section. `group` draws the library's strip for it; a
        section whose params are saved by another group says so in `note`."""
        _micro(title)
        if note:
            imgui.same_line(imgui.get_content_region_avail().x - _micro_width(note) - 4)
            _micro(note, DIM)
        lib = self.library
        if group is not None and lib is not None and lib.reg is not None:
            ui_presets.strip(self, group)
        imgui.separator()

    # ---- overlays ----

    def _draw_cheatsheet(self) -> None:
        io = imgui.get_io()
        imgui.set_next_window_pos(
            imgui.ImVec2(12, io.display_size.y - 12), imgui.Cond_.always, imgui.ImVec2(0, 1)
        )
        imgui.set_next_window_bg_alpha(0.45)
        flags = (
            imgui.WindowFlags_.no_decoration
            | imgui.WindowFlags_.always_auto_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_focus_on_appearing
            | imgui.WindowFlags_.no_nav
        )
        imgui.begin("##cheatsheet", None, flags)
        for key, action in CHEATSHEET:
            imgui.text_colored(RED, f"{key:>11s}")
            imgui.same_line(100)
            imgui.text_disabled(action)
        imgui.end()

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
            # frame
            dl.add_rect(
                imgui.ImVec2(x0, origin.y), imgui.ImVec2(x0 + bw, y1),
                u32(RED if sel else imgui.ImVec4(0.25, 0.25, 0.25, 1)),
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
        """The page list down the left: micro-labels, the open one red, a
        dirty dot where the page's group has moved off its preset."""
        if not imgui.begin_child("##rail", imgui.ImVec2(RAIL_W, -foot)):
            imgui.end_child()
            return
        r0 = imgui.get_window_pos()
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        for k, (_key, label, group) in enumerate(PAGES):
            lit = k == self.page
            imgui.push_style_color(imgui.Col_.text, RED if lit else DIM)
            hit, _ = imgui.selectable(f"{label.upper()}##page{k}", lit, 0,
                                      imgui.ImVec2(RAIL_W - 14, 0))
            imgui.pop_style_color()
            if hit:
                self.reg["ui.page"].set(k)
            if group is not None and ui_presets.dirty(self, group, polled=True):
                imgui.same_line(RAIL_W - 14)
                imgui.text_colored(RED, "●")
        imgui.pop_font()
        self._ctx(self.reg["ui.page"])
        # the hairline between rail and page
        dl = imgui.get_window_draw_list()
        x = r0.x + RAIL_W - 1
        dl.add_line(imgui.ImVec2(x, r0.y), imgui.ImVec2(x, r0.y + imgui.get_window_height()),
                    imgui.color_convert_float4_to_u32(imgui.ImVec4(0.22, 0.22, 0.22, 1)))
        imgui.end_child()

    def _footer(self, fps: float) -> None:
        imgui.separator()
        imgui.text_disabled(f"{fps:5.1f} FPS")
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
        # (reference #cells: large white numeral, dim micro sub-label)
        imgui.push_font(_FONTS["mono"], FONT_BIG)
        imgui.text(f"{sh.cells or '—'}")
        big_h = imgui.get_item_rect_size().y
        imgui.pop_font()
        imgui.same_line()
        # sit the CELLS sub-label on the numeral's baseline
        imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + big_h - FONT_MICRO - 8)
        _micro("cells")
        imgui.text(sh.name.upper())
        _micro(sh.alias, RED)
        _micro(f"{g['n']}V {g['m']}E  ·  {sh.sym}")
        imgui.spacing()

        self._section("view", "view")
        self._combo("view.shape")
        self._fader("view.bright")
        self._fader("view.speed")
        self._fader("view.depth4")
        imgui.spacing()
        for p, name in enumerate(PLANES):
            if p:
                imgui.same_line()
            self._lit_button(f"view.plane.{name}", name, v.planes[p])
        self._check("view.points")
        imgui.same_line()
        self._check("view.lines")
        imgui.same_line()
        self._check("view.rotate")
        imgui.same_line()
        self._check("view.faces")
        self._slider("view.instances")
        if v.instances > 1:
            self._combo("view.inst_motion", 110)
            if v.inst_motion:
                imgui.same_line()
                self._slider("view.inst_amp", 92)
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
        self._combo("view.pattern", 110)
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
        _micro("path")
        imgui.same_line(LABEL_W)
        self._combo("view.bmp_mode", 110)
        if v.bmp_mode:
            imgui.same_line()
            self._slider("view.bmp_amp", 92)
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
            imgui.text_disabled(
                f"{int(pos // 60)}:{int(pos % 60):02d} / {int(dur // 60)}:{int(dur % 60):02d}"
            )

    def _page_analyzer(self, dt: float) -> None:
        """Master faders, scene, meters and the selected band's strip — the
        six-band chain as it is today. WP5b replaces the band section."""
        c, a, r = self.control, self.audio, self.reg
        self._section("master", "master")
        self._fader("master.gain")
        self._fader("master.dyn")
        self._fader("master.trim")
        imgui.spacing()

        # ---- bands (WP5b: the editor goes here) ----
        self._section("bands", "band")
        # scene + reset-all (relabels to Undo while the window is open)
        _micro("scene")
        imgui.same_line(LABEL_W)
        self._combo("scene.select", -92)
        imgui.same_line()
        self._button("scene.reset_all", "Undo" if c.undo_armed else "Reset all")
        imgui.spacing()
        self._meters(dt)
        # per-band transfer selects
        for i in range(a.chain.n):
            if i:
                imgui.same_line()
            self._combo(f"band.{i}.fn", 46, SHAPERS[a.chain.params[i].fn].name)
        imgui.separator()
        # selected-band strip — the band.sel.* aliases follow the selection
        P = a.chain.params[c.selb]
        lo, hi = a.chain.edges(c.selb)
        imgui.text_colored(RED, f"{a.chain.band_names[c.selb]} · {SHAPERS[P.fn].tag}")
        imgui.same_line()
        imgui.text_disabled(f"{lo:.0f}–{hi:.0f} Hz")
        imgui.same_line()
        self._combo("band.sel.curve", 64)
        imgui.same_line(imgui.get_content_region_avail().x - 40)
        self._button("band.reset", "Reset", small=True)
        # ten faders (f, q, the eight knobs) in two columns so the page fits
        if imgui.begin_table("##bandstrip", 2, imgui.TableFlags_.sizing_stretch_same):
            for p in r.group("band"):
                if p.id.startswith("band.sel.") and p.kind is Kind.CONTINUOUS:
                    imgui.table_next_column()
                    self._fader(p.id)
            imgui.end_table()

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
