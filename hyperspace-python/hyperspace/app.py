"""Hyperspace entry point — two GLFW windows on one GL context.

The *render* window is pure moderngl output, the thing on the projector or
TV: no imgui in it, ever. The *control* window holds every widget — the
CONTROLS panel, the cheat sheet, the hot-reload error toast — in its own
imgui context and GlfwRenderer. Keys are polled, not callback-driven, so
they work from whichever window is focused (the control window defers to
imgui while it is typing); the mouse orbits, pans and zooms in the render
window only. overlay.py owns where the render window goes (screen,
fullscreen, overlay) through the output.* params.

  ← / →  shape      space  pause      P  points     R  reset view
  [ / ]  brightness , / .  speed      1–6  planes   H  panel
  M  mic on/off     K  play/pause     0  restart    Esc/Q  quit
  Cmd+R  restart the whole process (same terminal, cold reload)
  ↑ / ↓  4D perspective — holding accelerates toward the range limit
  drag  orbit       ⇧drag / right-drag  pan   scroll  zoom about cursor
  L  lines          F  faces          ?  cheat sheet
  T  overlay: float the render over the screen    G  clicks through it
  F1–F8  load theme (whole-surface save state)    ⇧F1–F8  save theme

Every input path — keys, the Xbox-layout gamepad, a MIDI controller, the
analyzer's lanes — is one binding table over the parameter registry
(params.py, routing.py): a row names a source, a param id and an
operation, nothing touches state directly. The table is bindings.json
(factory default in routing.py; MIDI rows editable from the panel by
right-click → Learn).

The in-app cheat sheet (ui.CHEATSHEET) is the canonical human list —
keep it in sync when adding bindings.

The engine hot-reloads (hotreload.py): save any module under hyperspace/
while the app runs and live objects pick the code up in place; a broken
save keeps the last good version and shows the error in the control
window. This file is the one cold piece — its loop is on the stack — so
keep it thin: put anything you'll want to iterate on live in the modules
it calls.
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys
import time
from pathlib import Path

# pyGLFW and imgui_bundle each ship a libglfw; loading both trips ObjC class
# collisions on macOS. Point pyGLFW at imgui_bundle's copy before it loads.
if "PYGLFW_LIBRARY" not in os.environ:
    _spec = importlib.util.find_spec("imgui_bundle")
    if _spec and _spec.origin:
        _dylib = Path(_spec.origin).parent / "libglfw.3.dylib"
        if _dylib.exists():
            os.environ["PYGLFW_LIBRARY"] = str(_dylib)

import glfw
import moderngl
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

from . import config, gamepad
from .audio import AudioEngine
from .control import Control
from .gamepad import Pad
from .hotreload import HotReloader
from .library import Library
from .overlay import GlfwBackend, Output
from .params import Registry, build_registry
from .presets import SLOTS
from .render import Renderer, ViewState
from .routing import Bindings, Router, bindings_path
from .ui import Panel, apply_style, load_fonts

TITLE = "Hyperspace"
RENDER_SIZE = (1280, 820)
# wide enough for the cheat sheet on the left and the panel on the right
CONTROL_SIZE = (820, 820)

# 4D perspective hold keys move depth4 in the taper's own log space —
# octaves of (depth − 1) — so travel feels even across the whole throw.
# The rate eases in quadratically from a tap-sized nudge to full speed.
D4_RATE0 = 0.45   # octaves/s at the instant of the press
D4_RATE1 = 3.6    # octaves/s once the ramp completes
D4_RAMP = 1.8     # seconds of hold to reach full rate

# the key / pad / MIDI / lane binding tables live in routing.py (bindings.json)


def act(reg: Registry, pid: str, op: str, arg: int = 0) -> None:
    p = reg.get(pid)
    if p is None:
        return
    if op == "step":
        p.step(arg)
    elif op == "toggle":
        p.toggle()
    elif op == "fire":
        p.fire()


def _err(where: str, e: Exception) -> str:
    return f"{where}: {type(e).__name__}: {e}"[:160]


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001, S110 — teardown is best-effort
        pass


def _restart(audio, impl, midi_io, ctrl_win) -> None:
    # execv swaps the process image in place — same PID, same terminal,
    # same stdio — so stdout doesn't detach and the user's shell keeps
    # owning the child. The OS reclaims the GL contexts and audio device
    # on image swap; we still stop the audio stream first so Core Audio
    # doesn't complain about a stream vanishing mid-callback.
    if midi_io is not None:
        _quiet(midi_io.close)
    _quiet(audio.stop)
    _quiet(lambda: glfw.make_context_current(ctrl_win))  # imgui's GL objects live there
    _quiet(impl.shutdown)
    _quiet(glfw.terminate)
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _windows():
    """The two GLFW windows on one shared GL context: render first, then controls."""
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 4)
    # creation-time hints: the framebuffer keeps alpha so overlay mode can
    # clear to see-through (the other modes clear opaque), and fullscreen
    # must not minimise when the control window takes focus (overlay.py)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, True)
    glfw.window_hint(glfw.AUTO_ICONIFY, False)
    render_win = glfw.create_window(*RENDER_SIZE, TITLE, None, None)
    if not render_win:
        glfw.terminate()
        raise SystemExit("could not create the render window")
    # the control window is an ordinary opaque window; the shared context
    # lets both sides see the same buffers, textures and programs
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, False)
    glfw.window_hint(glfw.SAMPLES, 0)
    ctrl_win = glfw.create_window(*CONTROL_SIZE, f"{TITLE} — controls", None, render_win)
    if not ctrl_win:
        glfw.terminate()
        raise SystemExit("could not create the control window")
    # render left, controls flush right on the primary screen's work area;
    # they overlap on a narrow laptop screen until one goes to a projector
    mon = glfw.get_primary_monitor()
    if mon:
        x, y, w, _ = glfw.get_monitor_workarea(mon)
        glfw.set_window_pos(render_win, x + 16, y + 16)
        glfw.set_window_pos(ctrl_win, max(x + w - CONTROL_SIZE[0] - 16, x + 16), y + 16)
    return render_win, ctrl_win


def _make_output(win, reg: Registry, cfg: dict) -> Output:
    """The render window's output settings, seeded from config."""
    out = Output(win, GlfwBackend(glfw))
    out.register(reg)
    # [output] in config.toml; the pre-split [overlay] section still counts
    oc = {**cfg.get("overlay", {}), **cfg.get("output", {})}
    out.monitor = int(oc.get("monitor", -1))
    out.fullscreen = bool(oc.get("fullscreen", False))
    out.overlay = bool(oc.get("on_start", False))
    out.passthrough = bool(oc.get("passthrough", True))
    out.bg = float(oc.get("bg", 0.0))
    out.alpha = float(oc.get("alpha", 1.0))
    return out


def _open_midi(reg: Registry, cfg: dict, table: Bindings):
    """The adapter, only when configured — the core never imports it."""
    mc = cfg.get("midi", {})
    if not mc.get("enabled", True):
        return None
    try:
        from . import midi
    except ImportError as e:
        print(f"midi: adapter unavailable ({e})", file=sys.stderr)
        return None
    try:
        mapping = midi.MidiMap(table=table)
        return midi.MidiIO(reg, mapping, port=mc.get("port"), profile=mc.get("profile", "apc40"))
    except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
        print(f"midi: {e}", file=sys.stderr)
        return None


def _open_bridge(reg: Registry, cfg: dict):
    """The lanes bridge (bridge.py), only when [bridge] enabled — the same rule."""
    if not cfg.get("bridge", {}).get("enabled", False):
        return None
    try:
        from . import bridge
        return bridge.Bridge(reg, cfg["bridge"])
    except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
        print(f"bridge: {e}", file=sys.stderr)
        return None


class Keys:
    """Edge detection and hold timing over polled key state, across both windows.

    A key counts as down when it is down in the render window, or in the
    control window while imgui is not typing (`typing` is io.want_capture_
    keyboard, set each frame after new_frame()).
    """

    def __init__(self, render_win, ctrl_win):
        self.render_win, self.ctrl_win = render_win, ctrl_win
        self.typing = False
        self.prev: dict[int, bool] = {}
        self.down_since: dict[int, float] = {}

    def _down(self, key: int) -> bool:
        if glfw.get_key(self.render_win, key) == glfw.PRESS:
            return True
        return not self.typing and glfw.get_key(self.ctrl_win, key) == glfw.PRESS

    def pressed(self, key: int) -> bool:
        down = self._down(key)
        was = self.prev.get(key, False)
        self.prev[key] = down
        return down and not was

    def held(self, key: int) -> float:
        """Seconds the key has been continuously down; 0.0 when up."""
        if not self._down(key):
            self.down_since.pop(key, None)
            return 0.0
        now = time.perf_counter()
        return now - self.down_since.setdefault(key, now)

    def down(self, *keys: int) -> bool:
        return any(self._down(k) for k in keys)


class Mouse:
    """Orbit, pan and zoom from the render window's mouse — no imgui to defer to.

    Buttons and cursor are polled; the wheel arrives by callback and is
    drained once per frame.
    """

    def __init__(self, win, reg: Registry, view: ViewState):
        self.win, self.view = win, view
        self.yaw, self.pitch, self.zoom = reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]
        self.pan_x, self.pan_y = reg["camera.pan.x"], reg["camera.pan.y"]
        self.drag = {"btn": None, "x": 0.0, "y": 0.0}
        self._wheel = 0.0
        glfw.set_scroll_callback(win, self._on_scroll)

    def _on_scroll(self, _win, _dx: float, dy: float) -> None:
        self._wheel += dy

    def poll(self, shift: bool) -> None:
        win, s, drag = self.win, self.view, self.drag
        x, y = glfw.get_cursor_pos(win)
        left = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
        right = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
        # shift+drag pans too — a trackpad has no right button to hold
        btn = "pan" if (right or (left and shift)) else "orbit" if left else None
        if btn != drag["btn"]:
            drag.update(btn=btn, x=x, y=y)
        elif btn == "orbit":
            self.yaw.set_value(self.yaw.value + (x - drag["x"]) * 0.005)
            self.pitch.set_value(self.pitch.value + (y - drag["y"]) * 0.005)
            drag.update(x=x, y=y)
        elif btn == "pan":
            self.pan_x.set_value(self.pan_x.value + x - drag["x"])
            self.pan_y.set_value(self.pan_y.value + y - drag["y"])
            drag.update(x=x, y=y)
        wheel, self._wheel = self._wheel, 0.0
        if wheel:
            factor = 2.0 ** (wheel * 0.15)
            old = s.zoom
            self.zoom.set_value(old * factor)
            factor = s.zoom / old
            # zoom about the cursor: keep the point under it fixed
            w, h = glfw.get_window_size(win)
            cx, cy = w / 2 + s.pan[0], h / 2 + s.pan[1]
            self.pan_x.set_value(self.pan_x.value + (cx - x) * (factor - 1))
            self.pan_y.set_value(self.pan_y.value + (cy - y) * (factor - 1))


def _ride_depth(p, octaves: float) -> None:
    """Move 4D depth by a number of octaves of (depth − 1) — the taper's own space."""
    u = math.log2(max(p.value - 1.0, 1e-6) / 0.05)
    p.set_value(1.0 + 0.05 * 2.0 ** (u + octaves))


def _hot_error_toast(msg: str) -> None:
    """The hot-reload failure notice, top-left of the control window."""
    imgui.set_next_window_pos(imgui.ImVec2(12, 12), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.7)
    imgui.begin(
        "##hoterr", None,
        imgui.WindowFlags_.no_decoration
        | imgui.WindowFlags_.always_auto_resize
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_focus_on_appearing
        | imgui.WindowFlags_.no_nav,
    )
    imgui.text_colored(imgui.ImVec4(1, 0.4, 0.3, 1), f"HOT RELOAD  {msg}")
    imgui.text_disabled("last good code keeps running — fix the file and save")
    imgui.end()


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise")
    render_win, ctrl_win = _windows()

    # the render side: moderngl on the render window's context, vsynced
    glfw.make_context_current(render_win)
    glfw.swap_interval(1)
    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    s = ViewState()

    # the control side: imgui on the control window's context. Its swap
    # never waits for a vblank — two vsynced swaps a frame would halve the
    # rate — so it paces itself off the render window.
    glfw.make_context_current(ctrl_win)
    glfw.swap_interval(0)
    ui_gl = moderngl.create_context()  # a handle on the control context; it only clears
    ui_ctx = imgui.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(ctrl_win)
    io = imgui.get_io()
    # hot-reloaded panel code can raise mid-window; let imgui unwind the
    # stack itself instead of asserting the process away
    io.config_error_recovery = True
    io.config_error_recovery_enable_assert = False

    cfg = config.load()
    audio = AudioEngine()
    control = Control(audio.chain)
    library = Library()                    # presets, projects, the theme bank
    presets = library.bank
    # dream.* drives the renderer's look-back (lookback.py); the post pass
    # runs inside renderer.draw
    reg = build_registry(s, control, audio, presets, dream=renderer.lookback.state)
    # an analyzer preset carries its band layout; the library hands it to
    # control before restoring values (07-overhaul contracts)
    library.on_layout("band", control.apply_layout)
    library.attach(reg)
    panel = Panel(control, audio, s, renderer, presets, registry=reg, library=library)
    output = _make_output(render_win, reg, cfg)
    panel.output = output
    # one binding table for keys, pad, MIDI and lanes (an old midi_map.json migrates)
    mc = cfg.get("midi", {})
    router = Router(reg, Bindings.load(
        bindings_path(library.home), mc.get("profile", "apc40"),
        Path(mc.get("map", "midi_map.json")),
    ))
    midi_io = _open_midi(reg, cfg, router.table)
    panel.midi = midi_io
    bridge_io = _open_bridge(reg, cfg)
    # panel state and chain must stay one object even after source changes
    # the live objects that get re-classed on a hot reload; re-evaluated
    # each swap so recreated ones (the chain after a source attach) count
    reloader = HotReloader(targets=lambda: [
        (renderer, "render", "Renderer"),
        (renderer.lookback, "lookback", "Lookback"),
        (renderer.lookback.state, "lookback", "DreamState"),
        (s, "render", "ViewState"),
        (panel, "ui", "Panel"),
        (control, "control", "Control"),
        (audio, "audio", "AudioEngine"),
        (audio.chain, "bands", "Chain"),
        *[(p, "bands", "Params") for p in audio.chain.params],
        *([(audio.analyser, "analysis", "Analyser")] if audio.analyser is not None else []),
        (reg, "params", "Registry"),
        *[(p, "params", "Param") for p in reg],
        (output, "overlay", "Output"),
        (router, "routing", "Router"),
        *([(midi_io, "midi", "MidiIO"), (midi_io.map, "midi", "MidiMap")] if midi_io else []),
        *([(bridge_io, "bridge", "Bridge")] if bridge_io else []),
    ], watchers=[library])
    panel.reloader = reloader
    keys = Keys(render_win, ctrl_win)
    mouse = Mouse(render_win, reg, s)
    pad = Pad()
    depth4, yaw, pitch, zoom = reg["view.depth4"], reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]

    # smoke-test escape hatch: HYPERSPACE_FRAMES=n closes after n frames
    frames_left = int(os.environ.get("HYPERSPACE_FRAMES", "0")) or None

    last = time.perf_counter()
    fps = 0.0
    while not (glfw.window_should_close(render_win) or glfw.window_should_close(ctrl_win)):
        if frames_left is not None:
            frames_left -= 1
            if frames_left <= 0:
                glfw.set_window_should_close(render_win, True)
        glfw.poll_events()
        # the control window's imgui frame starts BEFORE input handling:
        # with the 1.87+ event queue, want_capture_keyboard only holds this
        # frame's value once new_frame() has run — reading it earlier sees
        # last frame's. The render window has no imgui to defer to.
        imgui.set_current_context(ui_ctx)
        impl.process_inputs()
        imgui.new_frame()
        keys.typing = io.want_capture_keyboard
        now = time.perf_counter()
        dt = min(now - last, 0.05)
        last = now
        fps = fps * 0.95 + (1.0 / max(now and dt, 1e-6)) * 0.05

        # the chain object is recreated on source attach; keep bindings fresh
        control.chain = audio.chain
        reloader.poll()

        # ---- polled keys, from either window ----
        if keys.pressed(glfw.KEY_ESCAPE) or keys.pressed(glfw.KEY_Q):
            glfw.set_window_should_close(render_win, True)
        router.keys(keys)
        if keys.pressed(glfw.KEY_R):
            if keys.down(glfw.KEY_LEFT_SUPER, glfw.KEY_RIGHT_SUPER):
                _restart(audio, impl, midi_io, ctrl_win)
            else:
                act(reg, "camera.reset", "fire")
        # ↑/↓ ride depth4 toward its range limit, accelerating with hold
        for key, sgn in ((glfw.KEY_UP, 1.0), (glfw.KEY_DOWN, -1.0)):
            hold = keys.held(key)
            if hold > 0.0:
                ramp = min(hold / D4_RAMP, 1.0)
                rate = D4_RATE0 + (D4_RATE1 - D4_RATE0) * ramp * ramp
                _ride_depth(depth4, sgn * rate * dt)
        # F1–F8 flip whole-surface themes; with ⇧ held they save instead
        shift = keys.down(glfw.KEY_LEFT_SHIFT, glfw.KEY_RIGHT_SHIFT)
        for k in range(SLOTS):
            if keys.pressed(glfw.KEY_F1 + k):
                act(reg, f"theme.{'save' if shift else 'load'}.{k}", "fire")

        # ---- gamepad: a second hand on the same controls (imgui never
        # claims it, so it works even while the panel has keyboard focus) ----
        pad.poll()
        if pad.on:
            router.pad(pad)
            # analog: left stick orbits, right-stick Y zooms about centre,
            # triggers ride depth4 in its own log space (LT out, RT in)
            lx, ly = pad.axis(gamepad.AX_LX), pad.axis(gamepad.AX_LY)
            if lx:
                yaw.set_value(yaw.value + lx * 2.2 * dt)
            if ly:
                pitch.set_value(pitch.value + ly * 2.2 * dt)
            zoom_v = pad.axis(gamepad.AX_RY)
            if zoom_v:
                zoom.set_value(zoom.value * 2.0 ** (-zoom_v * 1.2 * dt))
            d4 = pad.trigger(gamepad.AX_RT) - pad.trigger(gamepad.AX_LT)
            if d4:
                _ride_depth(depth4, d4 * 2.4 * dt)

        # ---- MIDI controller: routed through the same registry ----
        if midi_io is not None:
            try:
                midi_io.poll()
            except Exception as e:  # noqa: BLE001 — hot-reloaded code may raise
                reloader.runtime_error = _err("midi", e)

        # ---- output: the render window follows the output.* params ----
        output.apply()
        renderer.bg_alpha = output.bg_alpha

        # ---- mouse: orbit / pan / zoom, render window only ----
        mouse.poll(shift)

        # ---- audio + rotation + draw, guarded: hot-reloaded code may raise;
        # record it and keep the loop alive so the next save can fix it ----
        ok = True
        try:
            audio.step(dt)
            if bridge_io is not None:   # lanes out, external lanes in (bridge.py)
                bridge_io.step(audio.chain if audio.on else None, router)
            # the lanes are a modulation source like any other (routing.py);
            # once every source has spoken for this frame, land base +
            # offsets on the objects before the integrator reads them
            router.modulate(audio.chain if audio.on else None)
            reg.apply()
            s.integrate(dt)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("step", e)

        # ---- render window: its own size and DPI (a 1080p projector next
        # to a retina laptop) ----
        glfw.make_context_current(render_win)
        w, h = glfw.get_window_size(render_win)
        fbw, fbh = glfw.get_framebuffer_size(render_win)
        ctx.viewport = (0, 0, fbw, fbh)
        try:
            renderer.draw(s, max(w, 1), max(h, 1), dpr=fbw / max(w, 1))
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("render.draw", e)
        glfw.swap_buffers(render_win)

        # ---- control window: black ground, then the imgui frame opened above ----
        glfw.make_context_current(ctrl_win)
        ui_gl.clear(0.0, 0.0, 0.0, 1.0)
        try:
            panel.draw(dt, fps)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("panel.draw", e)
        if ok:
            reloader.runtime_error = ""

        if panel.restart_requested:
            panel.restart_requested = False
            _restart(audio, impl, midi_io, ctrl_win)

        if reloader.error or reloader.runtime_error:
            _hot_error_toast(reloader.error or reloader.runtime_error)

        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(ctrl_win)

    if midi_io is not None:
        midi_io.close()
    if bridge_io is not None:
        bridge_io.close()
    audio.stop()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
