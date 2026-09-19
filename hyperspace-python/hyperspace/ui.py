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
Unbind. The layout — what sits where, which sections fold — is the one
hand-arranged thing left in this module.
"""

from __future__ import annotations

import math
import os

from imgui_bundle import imgui

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
    ("↑ ↓", "4D perspective (hold accelerates)"),
    ("[ ]  , .", "brightness · speed"),
    ("M", "mic on/off"),
    ("K / 0", "play-pause / restart track"),
    ("R", "reset view + camera"),
    ("F1–F8", "load theme · ⇧ saves"),
    ("Cmd+R", "restart process"),
    ("H / ?", "panel / this sheet"),
    ("T", "overlay: float the render over the screen"),
    ("G", "overlay: clicks through / back (orbit again)"),
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


class Panel:
    def __init__(self, control: Control, audio: AudioEngine, view: ViewState, renderer=None,
                 presets=None, registry: Registry | None = None):
        self.control = control
        self.audio = audio
        self.view = view
        self.renderer = renderer
        self.presets = presets
        self.reg = registry if registry is not None else build_registry(
            view, control, audio, presets
        )
        self.devices = input_devices()
        self.device_sel = next(
            (k for k, d in enumerate(self.devices) if d["loopback"]), 0
        )
        self.pin_in = [0.0] * N_MAX
        self.pin_out = [0.0] * N_MAX
        self.open = True
        self.cheatsheet = True
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

    # ---- widgets: each one reads, draws and writes a Param ----

    def _fader(self, pid: str) -> bool:
        """Full-width taper fader: micro label, readout, detent notch."""
        p = self.reg[pid]
        pos = p.position()
        imgui.push_id(pid)
        tag = ("log" if p.taper.log else "lin") if p.taper is not None else "lin"
        _micro(f"{p.label}  ·  {tag}")
        self._tip(p)
        imgui.same_line(imgui.get_content_region_avail().x - 64)
        imgui.text(p.text())
        imgui.set_next_item_width(-1)
        changed, pos2 = imgui.slider_int("##s", pos, 0, p.steps, "")
        self._tip(p)
        self._ctx(p)
        self._learn_frame(p)
        if p.taper is not None and p.taper.unity is not None:
            # detent notch: ticks at the fader position the grab centre
            # occupies at unity (frame inset by grab padding + half grab)
            r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            half = imgui.get_style().grab_min_size / 2 + 2.0
            nx = r0.x + half + (r1.x - r0.x - 2 * half) * p.taper.unity / p.steps
            dl = imgui.get_window_draw_list()
            notch = imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.35))
            dl.add_line(imgui.ImVec2(nx, r0.y), imgui.ImVec2(nx, r0.y + 3), notch)
            dl.add_line(imgui.ImVec2(nx, r1.y - 3), imgui.ImVec2(nx, r1.y), notch)
        imgui.pop_id()
        if changed and pos2 != pos:
            p.set_position(pos2)
            return True
        return False

    def _slider(self, pid: str, width: float = -1) -> bool:
        """Compact slider with the readout inside — untapered ranges."""
        p = self.reg[pid]
        imgui.set_next_item_width(width)
        v = p.base
        if p.integer:
            changed, nv = imgui.slider_int(f"##{pid}", int(v), int(p.lo), int(p.hi), p.text())
        else:
            flags = imgui.SliderFlags_.logarithmic if p.log else 0
            changed, nv = imgui.slider_float(f"##{pid}", float(v), p.lo, p.hi, p.text(), flags)
        self._tip(p)
        self._ctx(p)
        self._learn_frame(p)
        if changed:
            p.set_value(nv)
        return changed

    def _combo(self, pid: str, width: float = -1, tip: str | None = None) -> bool:
        p = self.reg[pid]
        imgui.set_next_item_width(width)
        changed, i = imgui.combo(f"##{pid}", p.base, p.names)
        self._tip(p, tip)
        self._ctx(p)
        self._learn_frame(p)
        if changed:
            p.set(i)
        return changed

    def _check(self, pid: str) -> bool:
        p = self.reg[pid]
        changed, on = imgui.checkbox(f"{p.label}##{pid}", bool(p.base))
        self._tip(p)
        self._ctx(p)
        self._learn_frame(p)
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
        if hit:
            p.toggle()
        return hit

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
            imgui.same_line(112)
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

    # ---- main draw ----

    def draw(self, dt: float, fps: float) -> None:
        if self.cheatsheet:
            self._draw_cheatsheet()
        if not self.open:
            return
        io = imgui.get_io()
        imgui.set_next_window_pos(
            imgui.ImVec2(io.display_size.x - 340, 12), imgui.Cond_.once
        )
        imgui.set_next_window_size(imgui.ImVec2(328, io.display_size.y - 24), imgui.Cond_.once)
        opened, self.open = imgui.begin("CONTROLS", self.open)
        if not opened:
            imgui.end()
            return

        v, c, a, r = self.view, self.control, self.audio, self.reg
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
        imgui.separator()

        # shape + view
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
        if v.faces:
            self._combo("view.pattern", 110)
            if v.pattern:
                imgui.same_line()
                self._slider("view.pattern_mix")
            if self.renderer is not None and self.renderer.pattern_error:
                imgui.text_colored(WARN, f"GLSL: {self.renderer.pattern_error}")
            self._bitmap_section()
        imgui.separator()
        self._output_section()

        # ---- themes: whole-surface save states on F1–F8 ----
        if self.presets is not None:
            pr = self.presets
            _micro("themes")
            if imgui.is_item_hovered():
                imgui.set_tooltip(
                    "Whole-surface save states — view, faders, all six band "
                    "strips. Click or F1–F8 loads; ⇧click or ⇧F1–F8 saves the "
                    "current state into the slot."
                )
            for k, slot in enumerate(pr.slots):
                if k:
                    imgui.same_line()
                lit = k == pr.active and slot is not None
                color = RED if lit else DIM if slot is None else imgui.ImVec4(0.92, 0.92, 0.92, 1)
                imgui.push_style_color(imgui.Col_.text, color)
                pid = f"theme.{'save' if io.key_shift else 'load'}.{k}"
                if imgui.small_button(f"{k + 1}##theme{k}"):
                    r[pid].fire()
                imgui.pop_style_color()
                if imgui.is_item_hovered() and slot is not None:
                    imgui.set_tooltip(slot["name"])
                self._ctx(r[f"theme.load.{k}"])
                self._learn_frame(r[f"theme.load.{k}"])
            if pr.error:
                imgui.text_colored(WARN, pr.error)
        imgui.separator()

        # ---- audio sources ----
        _micro("audio")
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

        # master faders
        self._fader("master.gain")
        self._fader("master.dyn")
        self._fader("master.trim")
        imgui.separator()

        # scene + reset-all (relabels to Undo while the window is open)
        _micro("scene")
        self._combo("scene.select", -92)
        imgui.same_line()
        self._button("scene.reset_all", "Undo" if c.undo_armed else "Reset all")

        imgui.spacing()
        self._meters(dt)
        imgui.spacing()

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
        imgui.same_line(imgui.get_content_region_avail().x - 40)
        self._button("band.reset", "Reset", small=True)
        for p in r.group("band"):
            if p.id.startswith("band.sel.") and p.kind is Kind.CONTINUOUS:
                self._fader(p.id)

        imgui.separator()
        imgui.text_disabled(f"{fps:5.1f} FPS")
        if self.reloader is not None and self.reloader.status:
            imgui.same_line()
            imgui.text_disabled(f"·  {self.reloader.status}")
        imgui.same_line()
        self._button("app.restart", "Restart", small=True)
        self._midi_status()
        imgui.end()

    def _bitmap_section(self) -> None:
        v = self.view
        # bitmap layer, composited over the pattern in the face shader
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
                v.bmp_file = picked[0]
        if v.bmp_file:
            imgui.same_line()
            if imgui.small_button("Clear##bmp"):
                v.bmp_file = ""
            else:
                imgui.same_line()
                imgui.text_disabled(v.bmp_file.rsplit("/", 1)[-1][:26])
        if self.renderer is not None and self.renderer.bitmap_error:
            imgui.text_colored(WARN, f"bitmap: {self.renderer.bitmap_error}")
        if v.bmp_file:
            self._slider("view.bmp_alpha")
            self._slider("view.bmp_scale")
            self._combo("view.bmp_mode", 110)
            if v.bmp_mode:
                imgui.same_line()
                self._slider("view.bmp_amp", 92)
                imgui.same_line()
                self._slider("view.bmp_rate")

    def _output_section(self) -> None:
        """Where the render window shows: screen, fullscreen, overlay (overlay.py)."""
        if self.output is None or "output.overlay" not in self.reg:
            return
        _micro("output")
        if imgui.is_item_hovered():
            imgui.set_tooltip(
                "The render window. Fullscreen covers a screen opaque; overlay "
                "floats it frameless and see-through above everything — "
                "including a fullscreen video. T toggles; G sends clicks through."
            )
        if len(self.reg["output.monitor"].names) > 1:
            self._combo("output.monitor")
        self._check("output.fullscreen")
        imgui.same_line()
        self._check("output.overlay")
        self._check("output.passthrough")
        self._slider("output.bg")
        self._slider("output.alpha")
        if self.output.error:
            imgui.text_colored(WARN, self.output.error)
        imgui.separator()

    def _midi_status(self) -> None:
        m = self.midi
        if m is None:
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


def format_infinity(v: float) -> str:  # convenience for tests
    return "off" if not math.isfinite(v) else f"{v:g}"
