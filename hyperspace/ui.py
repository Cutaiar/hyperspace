"""imgui control surface — port of the HTML drawer's semantics (plan 03).

Instrument-panel aesthetic per ENGINEERING §7: black ground, square corners
everywhere, hairline rules, white text, red #ff2b2b as the only accent.
The hint-readout system of the HTML is replaced by native tooltips (noted
as a divergence in the plan results). All state lives in Control /
AudioEngine / ViewState — this module only draws and forwards edits.
"""

from __future__ import annotations

import math

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
    ("P / F", "points / faces"),
    ("1–6", "planes XY XZ YZ XW YW ZW"),
    ("↑ ↓", "4D perspective (hold accelerates)"),
    ("[ ]  , .", "brightness · speed"),
    ("M", "mic on/off"),
    ("K / 0", "play-pause / restart track"),
    ("R", "reset view + camera"),
    ("H / ?", "panel / this sheet"),
    ("Esc / Q", "quit"),
]


class Panel:
    def __init__(self, control: Control, audio: AudioEngine, view: ViewState, renderer=None):
        self.control = control
        self.audio = audio
        self.view = view
        self.renderer = renderer
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
        imgui.text_disabled(f"{label}  [{'log' if taper.log else 'lin'}]")
        if tip and imgui.is_item_hovered():
            imgui.set_tooltip(tip)
        imgui.same_line(imgui.get_content_region_avail().x - 64)
        imgui.text(fmt(value))
        imgui.set_next_item_width(-1)
        changed, pos2 = imgui.slider_int("##s", pos, 0, taper.steps, "")
        if tip and imgui.is_item_hovered():
            imgui.set_tooltip(tip)
        imgui.pop_id()
        if changed and pos2 != pos:
            return True, taper.map(pos2)
        return False, value

    # ---- meters ----

    def _meters(self, dt: float) -> None:
        a = self.audio.chain
        dl = imgui.get_window_draw_list()
        origin = imgui.get_cursor_screen_pos()
        bw, gap, mh = 24.0, 10.0, 96.0
        for i, band in enumerate(BANDS):
            x0 = origin.x + i * (bw + gap)
            y1 = origin.y + mh
            sel = i == self.control.selb
            # frame
            dl.add_rect(
                imgui.ImVec2(x0, origin.y), imgui.ImVec2(x0 + bw, y1),
                imgui.color_convert_float4_to_u32(RED if sel else imgui.ImVec4(0.3, 0.3, 0.3, 1)),
            )
            for col, (val, pin) in enumerate(
                ((a.inp[i], self.pin_in), (a.out[i], self.pin_out))
            ):
                cx0 = x0 + 2 + col * (bw / 2 - 2)
                cx1 = cx0 + bw / 2 - 4
                hh = min(val, CEIL) / CEIL * (mh - 4)
                pin[i] = pin[i] + dt if val >= PIN_AT else 0.0
                over = pin[i] >= PIN_HOLD and (int(imgui.get_time() * 4) % 2 == 0)
                color = (
                    (1.0, 0.25, 0.25, 1.0) if over
                    else (0.92, 0.92, 0.92, 0.9) if col == 0
                    else (1.0, 43 / 255, 43 / 255, 0.9)
                )
                dl.add_rect_filled(
                    imgui.ImVec2(cx0, y1 - 2 - hh), imgui.ImVec2(cx1, y1 - 2),
                    imgui.color_convert_float4_to_u32(imgui.ImVec4(*color)),
                )
            # landmarks: nominal and knee
            for lv, alpha in ((NOM, 0.8), (KNEE, 0.5)):
                ly = y1 - 2 - lv / CEIL * (mh - 4)
                dl.add_line(
                    imgui.ImVec2(x0, ly), imgui.ImVec2(x0 + bw, ly),
                    imgui.color_convert_float4_to_u32(imgui.ImVec4(0.6, 0.6, 0.6, alpha)),
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
        imgui.set_cursor_screen_pos(imgui.ImVec2(origin.x, origin.y + mh + 2))
        for i, band in enumerate(BANDS):
            if i:
                imgui.same_line(origin.x - imgui.get_window_pos().x + i * (bw + gap))
            imgui.text_colored(RED if i == self.control.selb else DIM, band.id)

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

        # signature readout
        imgui.text_colored(RED, f"{sh.cells or '—'}")
        imgui.same_line()
        imgui.text_disabled("CELLS")
        imgui.text(sh.name.upper())
        imgui.text_disabled(f"{sh.alias.upper()}  ·  {g['n']}V {g['m']}E  ·  {sh.sym}")
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

        # ---- audio sources ----
        imgui.text_disabled("AUDIO")
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
        imgui.text_disabled("SCENE")
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
