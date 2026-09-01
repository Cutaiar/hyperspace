"""imgui control surface — port of the HTML drawer's semantics (plan 03).

Instrument-panel aesthetic per ENGINEERING §7: black ground, square corners
everywhere, hairline rules, white text, red #ff2b2b as the only accent.
The hint-readout system of the HTML is replaced by native tooltips (noted
as a divergence in the plan results). All state lives in Control /
AudioEngine / ViewState — this module only draws and forwards edits.
"""

from __future__ import annotations

import math
import os

from imgui_bundle import imgui

from . import tapers
from .audio import AudioEngine, input_devices
from .bands import BANDS, CEIL, KNEE, NOM, PRESETS, SHAPERS
from .control import Control
from .geometry import SHAPES, geom
from .render import ViewState

RED = imgui.ImVec4(1.0, 43 / 255, 43 / 255, 1.0)
DIM = imgui.ImVec4(0.62, 0.62, 0.62, 1.0)

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
    }
    for k, v in colors.items():
        s.set_color_(k, imgui.ImVec4(*v))


PATTERNS = [
    "FLAT", "RINGS", "PLAID", "MOIRE", "BLOOM", "CAUSTIC",
    "HEX", "SPIRAL", "CELLS", "PLASMA", "WEAVE", "EMBER",
]

INST_MOTION = ["STILL", "ORBIT", "WAVE", "RIPPLE"]
BMP_PATHS = ["STILL", "ORBIT", "FIG-8", "SWAY"]

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
    ("H / ?", "panel / this sheet"),
    ("Esc / Q", "quit"),
    # Xbox-layout gamepad, Bluetooth or USB (gamepad.py holds the map)
    ("pad A B", "pause · next theme"),
    ("pad X Y", "points · faces"),
    ("LB / RB", "previous / next shape"),
    ("d-pad", "brightness ↑↓ · speed ←→"),
    ("sticks", "orbit · zoom — click resets"),
    ("LT / RT", "4D depth out / in"),
    ("view/menu", "panel / this sheet"),
]


class Panel:
    def __init__(self, control: Control, audio: AudioEngine, view: ViewState, renderer=None,
                 presets=None):
        self.control = control
        self.audio = audio
        self.view = view
        self.renderer = renderer
        self.presets = presets
        self.devices = input_devices()
        self.device_sel = next(
            (k for k, d in enumerate(self.devices) if d["loopback"]), 0
        )
        self.pin_in = [0.0] * 6
        self.pin_out = [0.0] * 6
        self.open = True
        self.cheatsheet = True
        self._file_dialog = None
        self._bmp_dialog = None
        self.reloader = None  # set by app.py; panel only reads status off it

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
            imgui.text_colored(RED, f"{key:>10s}")
            imgui.same_line(104)
            imgui.text_disabled(action)
        imgui.end()

    # ---- taper-backed slider: integer positions, truthful readouts ----

    def _taper_slider(self, label: str, taper: tapers.Taper, value: float, fmt, tip="") :
        pos = taper.unmap(value)
        imgui.push_id(label)
        _micro(f"{label}  ·  {'log' if taper.log else 'lin'}")
        if tip and imgui.is_item_hovered():
            imgui.set_tooltip(tip)
        imgui.same_line(imgui.get_content_region_avail().x - 64)
        imgui.text(fmt(value))
        imgui.set_next_item_width(-1)
        changed, pos2 = imgui.slider_int("##s", pos, 0, taper.steps, "")
        if tip and imgui.is_item_hovered():
            imgui.set_tooltip(tip)
        if taper.unity is not None:
            # detent notch: ticks at the fader position the grab centre
            # occupies at unity (frame inset by grab padding + half grab)
            r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            half = imgui.get_style().grab_min_size / 2 + 2.0
            nx = r0.x + half + (r1.x - r0.x - 2 * half) * taper.unity / taper.steps
            dl = imgui.get_window_draw_list()
            notch = imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.35))
            dl.add_line(imgui.ImVec2(nx, r0.y), imgui.ImVec2(nx, r0.y + 3), notch)
            dl.add_line(imgui.ImVec2(nx, r1.y - 3), imgui.ImVec2(nx, r1.y), notch)
        imgui.pop_id()
        if changed and pos2 != pos:
            return True, taper.map(pos2)
        return False, value

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
        bw = (imgui.get_content_region_avail().x - 5 * gap) / 6
        u32 = imgui.color_convert_float4_to_u32
        zone = u32(imgui.ImVec4(1.0, 43 / 255, 43 / 255, 0.07))
        blink = (imgui.get_time() % 0.62) < 0.31  # the 620 ms annunciator
        for i, band in enumerate(BANDS):
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
                self.control.selb = i
            if imgui.is_item_hovered():
                imgui.set_tooltip(
                    f"{band.id} {band.lo:g}–{band.hi:g} Hz → {band.pl} plane, "
                    f"{'forward' if band.dir > 0 else 'reverse'}"
                )
        # band tags, centred under their bars, in the micro face
        imgui.push_font(_FONTS["micro"], FONT_MICRO)
        for i, band in enumerate(BANDS):
            tw = imgui.calc_text_size(band.id).x
            imgui.set_cursor_screen_pos(
                imgui.ImVec2(origin.x + i * (bw + gap) + (bw - tw) / 2, origin.y + mh + 4)
            )
            imgui.text_colored(RED if i == self.control.selb else DIM, band.id)
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

        v, c, a = self.view, self.control, self.audio
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
        changed, idx = imgui.slider_int("##shape", v.shape, 0, len(SHAPES) - 1, sh.name)
        if changed:
            v.shape = idx
        ch, val = self._taper_slider("Brightness", tapers.T_BRIGHT, v.bright, tapers.fmt_gain)
        if ch:
            v.bright = val
        ch, val = self._taper_slider(
            "Speed", tapers.T_SPEED, v.speed,
            lambda x: "stop" if x <= 0 else f"{x:.3f}" if x < 1 else f"{x:.2f}",
        )
        if ch:
            v.speed = val
        ch, val = self._taper_slider("4D depth", tapers.T_DEPTH, v.depth4, lambda x: f"{x:.2f}")
        if ch:
            v.depth4 = val

        imgui.spacing()
        for p, name in enumerate(("XY", "XZ", "YZ", "XW", "YW", "ZW")):
            if p:
                imgui.same_line()
            imgui.push_style_color(imgui.Col_.text, RED if v.planes[p] else DIM)
            if imgui.small_button(name):
                v.planes[p] = not v.planes[p]
            imgui.pop_style_color()
        _, v.points = imgui.checkbox("Points", v.points)
        imgui.same_line()
        _, v.lines = imgui.checkbox("Lines", v.lines)
        imgui.same_line()
        _, v.playing = imgui.checkbox("Rotate", v.playing)
        imgui.same_line()
        _, v.faces = imgui.checkbox("Faces", v.faces)
        if imgui.is_item_hovered():
            imgui.set_tooltip(
                "Translucent fills on the true 2-faces, under the wireframe. "
                "First build per shape takes a moment (extraction is cached)."
            )
        changed, n = imgui.slider_int("##inst", v.instances, 1, 100, "%d instance(s)")
        if changed:
            v.instances = n
        if imgui.is_item_hovered():
            imgui.set_tooltip(
                "Synchronized copies in a grid — scroll to zoom out over the field, "
                "right-drag to pan."
            )
        if v.instances > 1:
            imgui.set_next_item_width(110)
            changed, m = imgui.combo("##imot", v.inst_motion, INST_MOTION)
            if changed:
                v.inst_motion = m
            if imgui.is_item_hovered():
                imgui.set_tooltip(
                    "Trigonometric motion over the instance grid — each copy's "
                    "phase comes from its grid position, so the field moves as "
                    "one figure."
                )
            if v.inst_motion:
                imgui.same_line()
                imgui.set_next_item_width(92)
                _, v.inst_amp = imgui.slider_float("##iamp", v.inst_amp, 0.0, 1.0, "amp %.2f")
                imgui.same_line()
                imgui.set_next_item_width(-1)
                _, v.inst_rate = imgui.slider_float("##irate", v.inst_rate, 0.0, 6.0, "rate %.1f")
        if v.faces:
            imgui.set_next_item_width(110)
            changed, m = imgui.combo("##pat", v.pattern, PATTERNS)
            if changed:
                v.pattern = m
            if imgui.is_item_hovered():
                imgui.set_tooltip(
                    "Face pattern — edit hyperspace/shaders/patterns.glsl while the "
                    "app runs; it hot-reloads on save. Patterns read the six band "
                    "outputs as uniforms."
                )
            if v.pattern:
                imgui.same_line()
                imgui.set_next_item_width(-1)
                changed, mx = imgui.slider_float("##pmix", v.pattern_mix, 0.0, 1.0, "mix %.2f")
                if changed:
                    v.pattern_mix = mx
            if self.renderer is not None and self.renderer.pattern_error:
                imgui.text_colored(
                    imgui.ImVec4(1, 0.4, 0.3, 1), f"GLSL: {self.renderer.pattern_error}"
                )
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
                imgui.text_colored(
                    imgui.ImVec4(1, 0.4, 0.3, 1), f"bitmap: {self.renderer.bitmap_error}"
                )
            if v.bmp_file:
                imgui.set_next_item_width(-1)
                _, v.bmp_alpha = imgui.slider_float(
                    "##balpha", v.bmp_alpha, 0.0, 1.0, "bitmap alpha %.2f"
                )
                imgui.set_next_item_width(-1)
                _, v.bmp_scale = imgui.slider_float(
                    "##bscale", v.bmp_scale, 0.05, 2.0, "bitmap size %.2f"
                )
                imgui.set_next_item_width(110)
                changed, m = imgui.combo("##bpath", v.bmp_mode, BMP_PATHS)
                if changed:
                    v.bmp_mode = m
                if imgui.is_item_hovered():
                    imgui.set_tooltip(
                        "The bitmap's own path about the face centre — "
                        "independent of the instance-grid motion."
                    )
                if v.bmp_mode:
                    imgui.same_line()
                    imgui.set_next_item_width(92)
                    _, v.bmp_amp = imgui.slider_float(
                        "##bamp", v.bmp_amp, 0.0, 0.5, "amp %.2f"
                    )
                    imgui.same_line()
                    imgui.set_next_item_width(-1)
                    _, v.bmp_rate = imgui.slider_float(
                        "##brate", v.bmp_rate, 0.0, 6.0, "rate %.1f"
                    )
        imgui.separator()

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
                imgui.push_style_color(
                    imgui.Col_.text,
                    RED if lit else DIM if slot is None else imgui.ImVec4(0.92, 0.92, 0.92, 1.0),
                )
                if imgui.small_button(f"{k + 1}##theme{k}"):
                    if imgui.get_io().key_shift:
                        pr.save(k)
                    else:
                        pr.load(k)
                imgui.pop_style_color()
                if imgui.is_item_hovered() and slot is not None:
                    imgui.set_tooltip(slot["name"])
            if pr.error:
                imgui.text_colored(imgui.ImVec4(1, 0.4, 0.3, 1), pr.error)
        imgui.separator()

        # ---- audio sources ----
        _micro("audio")
        mic_on = a.on and a.mode == "mic"
        if imgui.button("Stop mic" if mic_on else "Listen to mic"):
            if mic_on:
                a.stop()
            elif self.devices:
                a.start_mic(self.devices[self.device_sel]["index"])
        imgui.same_line()
        if imgui.button("Load track"):
            try:
                from imgui_bundle import portable_file_dialogs as pfd

                self._file_dialog = pfd.open_file(
                    "Choose a track", "", ["Audio", "*.wav *.mp3 *.flac *.ogg"]
                )
            except Exception as e:  # noqa: BLE001 — dialog is best-effort
                a.error = f"file dialog unavailable: {e}"
        if a.on and imgui.button("Stop"):
            a.stop()
        if self._file_dialog is not None and self._file_dialog.ready():
            picked = self._file_dialog.result()
            self._file_dialog = None
            if picked:
                a.start_file(picked[0])
        if self.devices:
            imgui.set_next_item_width(-1)
            _, self.device_sel = imgui.combo(
                "##dev", self.device_sel,
                [("● " if d["loopback"] else "") + d["name"] for d in self.devices],
            )
        if a.error:
            imgui.text_colored(imgui.ImVec4(1, 0.4, 0.3, 1), a.error)
        elif a.on:
            imgui.text_disabled(f"{a.label}  ·  {self.audio.sr / 1000:.0f} kHz")

        # transport
        if a.mode == "file":
            if imgui.button("Pause" if a.playing else "Play"):
                a.toggle_play()
            imgui.same_line()
            if imgui.button("Restart"):
                a.restart()
            imgui.same_line()
            pos, dur = a.position(), a.duration()
            imgui.text_disabled(
                f"{int(pos // 60)}:{int(pos % 60):02d} / {int(dur // 60)}:{int(dur % 60):02d}"
            )

        # master faders
        ch, val = self._taper_slider(
            "Audio drive", tapers.T_DRIVE, a.chain.gain, tapers.fmt_gain,
            "Master gain on the six band faders, after the transfer stage. Only does "
            "anything while a source is attached.",
        )
        if ch:
            a.chain.gain = val
        ch, val = self._taper_slider(
            "Dynamics", tapers.T_DYN, a.chain.dyn, tapers.fmt_gain,
            "How much of the range a limiter took is put back. At 0 the chain is a "
            "plain level follower.",
        )
        if ch:
            a.chain.dyn = val
        ch, val = self._taper_slider(
            "Input trim", tapers.T_TRIM, a.chain.trim, tapers.fmt_db,
            "One offset added to all six per-band trims, at the very head of the chain — "
            "moves a whole song down into the 56 dB working window.",
        )
        if ch:
            a.chain.trim = val
        imgui.separator()

        # scene + reset-all (relabels to Undo while the window is open)
        _micro("scene")
        imgui.set_next_item_width(-92)
        changed, k = imgui.combo("##scene", c.scene, [p["name"] for p in PRESETS])
        if changed:
            c.select_scene(k)
        imgui.same_line()
        if imgui.button("Undo" if c.undo_armed else "Reset all"):
            c.reset_all_clicked()
        if imgui.is_item_hovered():
            imgui.set_tooltip(
                "Reloads the selected scene across all six bands. Undoable for 8 s."
            )

        imgui.spacing()
        self._meters(dt)
        imgui.spacing()

        # per-band transfer selects
        for i in range(6):
            if i:
                imgui.same_line()
            imgui.set_next_item_width(46)
            changed, fn = imgui.combo(f"##fn{i}", a.chain.params[i].fn,
                                      [s.tag for s in SHAPERS])
            if changed:
                c.set_shaper(i, fn)
            if imgui.is_item_hovered():
                imgui.set_tooltip(SHAPERS[a.chain.params[i].fn].name)
        imgui.separator()

        # selected-band strip
        b = BANDS[c.selb]
        P = a.chain.params[c.selb]
        imgui.text_colored(RED, f"{b.id} · {SHAPERS[P.fn].tag}")
        imgui.same_line()
        imgui.text_disabled(f"{b.lo:g}–{b.hi:g} Hz → {b.pl}")
        imgui.same_line(imgui.get_content_region_avail().x - 40)
        if imgui.small_button("Reset"):
            c.reset_band()
        if imgui.is_item_hovered():
            imgui.set_tooltip("Puts this band's whole strip back to the selected scene.")
        for knob in tapers.KNOBS:
            ch, val = self._taper_slider(
                knob.label, knob.t, getattr(P, knob.key), knob.fmt, knob.tip
            )
            if ch:
                setattr(P, knob.key, val)

        imgui.separator()
        imgui.text_disabled(f"{fps:5.1f} FPS")
        if self.reloader is not None and self.reloader.status:
            imgui.same_line()
            imgui.text_disabled(f"·  {self.reloader.status}")
        imgui.end()


def format_infinity(v: float) -> str:  # convenience for tests
    return "off" if not math.isfinite(v) else f"{v:g}"
