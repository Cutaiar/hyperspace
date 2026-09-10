"""Hyperspace entry point — GLFW window, moderngl scene, imgui panel.

Input is polled per frame rather than callback-driven so imgui's own GLFW
callbacks stay undisturbed; anything imgui claims (want_capture_*) is left
to it.

  ← / →  shape      space  pause      P  points     R  reset view
  [ / ]  brightness , / .  speed      1–6  planes   H  panel
  M  mic on/off     K  play/pause     0  restart    Esc/Q  quit
  Cmd+R  restart the whole process (same terminal, cold reload)
  ↑ / ↓  4D perspective — holding accelerates toward the range limit
  drag  orbit       ⇧drag / right-drag  pan   scroll  zoom about cursor
  L  lines          F  faces          ?  cheat sheet overlay
  F1–F8  load theme (whole-surface save state)    ⇧F1–F8  save theme

Every input path — keys, the Xbox-layout gamepad, a MIDI controller —
is a binding table over the parameter registry (params.py): a key names
a param id and an operation, nothing touches state directly. KEYMAP,
PADMAP and HATMAP below are the keyboard and gamepad tables; the MIDI
table lives in midi_map.json (midi.py, apc40.py) and is editable from
the panel by right-click → Learn.

The in-app cheat sheet (ui.CHEATSHEET) is the canonical human list —
keep it in sync when adding bindings.

The engine hot-reloads (hotreload.py): save any module under hyperspace/
while the app runs and live objects pick the code up in place; a broken
save keeps the last good version and shows the error in an overlay. This
file is the one cold piece — its loop is on the stack — so keep it thin:
put anything you'll want to iterate on live in the modules it calls.
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
from .overlay import GlfwBackend, Overlay
from .params import Registry, build_registry
from .presets import SLOTS, Presets
from .render import Renderer, ViewState
from .ui import Panel, apply_style, load_fonts

TITLE = "Hyperspace"

# 4D perspective hold keys move depth4 in the taper's own log space —
# octaves of (depth − 1) — so travel feels even across the whole throw.
# The rate eases in quadratically from a tap-sized nudge to full speed.
D4_RATE0 = 0.45   # octaves/s at the instant of the press
D4_RATE1 = 3.6    # octaves/s once the ramp completes
D4_RAMP = 1.8     # seconds of hold to reach full rate

# ---- binding tables: (input, param id, op, arg) ----
# op: "step" moves arg detents, "toggle" flips (or fires), "fire" fires.
KEYMAP = [
    (glfw.KEY_RIGHT, "view.shape", "step", 1),
    (glfw.KEY_LEFT, "view.shape", "step", -1),
    (glfw.KEY_SPACE, "view.rotate", "toggle", 0),
    (glfw.KEY_P, "view.points", "toggle", 0),
    (glfw.KEY_L, "view.lines", "toggle", 0),
    (glfw.KEY_F, "view.faces", "toggle", 0),
    (glfw.KEY_H, "ui.panel", "toggle", 0),
    (glfw.KEY_SLASH, "ui.cheatsheet", "toggle", 0),
    (glfw.KEY_LEFT_BRACKET, "view.bright", "step", -3),
    (glfw.KEY_RIGHT_BRACKET, "view.bright", "step", 3),
    (glfw.KEY_COMMA, "view.speed", "step", -4),
    (glfw.KEY_PERIOD, "view.speed", "step", 4),
    (glfw.KEY_M, "audio.mic", "toggle", 0),
    (glfw.KEY_K, "audio.play", "toggle", 0),
    (glfw.KEY_0, "audio.restart", "fire", 0),
    (glfw.KEY_T, "overlay.on", "toggle", 0),
    (glfw.KEY_G, "overlay.passthrough", "toggle", 0),
    *[(glfw.KEY_1 + p, f"view.plane.{n}", "toggle", 0)
      for p, n in enumerate(("XY", "XZ", "YZ", "XW", "YW", "ZW"))],
]
PADMAP = [
    (gamepad.A, "view.rotate", "toggle", 0),
    (gamepad.B, "theme.next", "fire", 0),
    (gamepad.X, "view.points", "toggle", 0),
    (gamepad.Y, "view.faces", "toggle", 0),
    (gamepad.LB, "view.shape", "step", -1),
    (gamepad.RB, "view.shape", "step", 1),
    (gamepad.VIEW, "ui.panel", "toggle", 0),
    (gamepad.MENU, "ui.cheatsheet", "toggle", 0),
    (gamepad.LSTICK, "camera.reset", "fire", 0),
    (gamepad.RSTICK, "camera.reset", "fire", 0),
]
HATMAP = [
    (gamepad.HAT_UP, "view.bright", "step", 3),
    (gamepad.HAT_DOWN, "view.bright", "step", -3),
    (gamepad.HAT_LEFT, "view.speed", "step", -4),
    (gamepad.HAT_RIGHT, "view.speed", "step", 4),
]


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


def _restart(audio, impl, midi_io) -> None:
    # execv swaps the process image in place — same PID, same terminal,
    # same stdio — so stdout doesn't detach and the user's shell keeps
    # owning the child. The OS reclaims the GL context and audio device
    # on image swap; we still stop the audio stream first so Core Audio
    # doesn't complain about a stream vanishing mid-callback.
    if midi_io is not None:
        _quiet(midi_io.close)
    _quiet(audio.stop)
    _quiet(impl.shutdown)
    _quiet(glfw.terminate)
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _make_overlay(win, reg: Registry, panel, cfg: dict) -> Overlay:
    """Overlay state with its params; entering hides the panel and sheet."""
    shown = {}

    def hide():
        shown["panel"], shown["sheet"] = panel.open, panel.cheatsheet
        panel.open = panel.cheatsheet = False

    def restore():
        panel.open = shown.get("panel", True)
        panel.cheatsheet = shown.get("sheet", True)

    ov = Overlay(win, GlfwBackend(glfw), on_enter=hide, on_leave=restore)
    ov.register(reg)
    oc = cfg.get("overlay", {})
    ov.passthrough = bool(oc.get("passthrough", False))
    ov.bg = float(oc.get("bg", 0.0))
    ov.alpha = float(oc.get("alpha", 1.0))
    ov.on = bool(oc.get("on_start", False))
    return ov


def _open_midi(reg: Registry, cfg: dict):
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
        mapping = midi.MidiMap(Path(mc.get("map", "midi_map.json")), mc.get("profile", "apc40"))
        return midi.MidiIO(reg, mapping, port=mc.get("port"), profile=mc.get("profile", "apc40"))
    except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
        print(f"midi: {e}", file=sys.stderr)
        return None


class Keys:
    """Edge detection and hold timing over polled key state."""

    def __init__(self, win):
        self.win = win
        self.prev: dict[int, bool] = {}
        self.down_since: dict[int, float] = {}

    def pressed(self, key: int) -> bool:
        down = glfw.get_key(self.win, key) == glfw.PRESS
        was = self.prev.get(key, False)
        self.prev[key] = down
        return down and not was

    def held(self, key: int) -> float:
        """Seconds the key has been continuously down; 0.0 when up."""
        if glfw.get_key(self.win, key) != glfw.PRESS:
            self.down_since.pop(key, None)
            return 0.0
        now = time.perf_counter()
        return now - self.down_since.setdefault(key, now)

    def down(self, *keys: int) -> bool:
        return any(glfw.get_key(self.win, k) == glfw.PRESS for k in keys)


def _ride_depth(p, octaves: float) -> None:
    """Move 4D depth by a number of octaves of (depth − 1) — the taper's own space."""
    u = math.log2(max(p.value - 1.0, 1e-6) / 0.05)
    p.set_value(1.0 + 0.05 * 2.0 ** (u + octaves))


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 4)
    # a creation-time hint: the framebuffer keeps alpha so overlay mode can
    # clear to see-through; normal mode clears opaque (overlay.py)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, True)
    win = glfw.create_window(1280, 820, TITLE, None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create a window")
    glfw.make_context_current(win)
    glfw.swap_interval(1)

    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    s = ViewState()

    imgui.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)
    io = imgui.get_io()
    # hot-reloaded panel code can raise mid-window; let imgui unwind the
    # stack itself instead of asserting the process away
    io.config_error_recovery = True
    io.config_error_recovery_enable_assert = False

    cfg = config.load()
    audio = AudioEngine()
    control = Control(audio.chain)
    presets = Presets(s, control, audio)
    reg = build_registry(s, control, audio, presets)
    panel = Panel(control, audio, s, renderer, presets, registry=reg)
    overlay = _make_overlay(win, reg, panel, cfg)
    panel.overlay = overlay
    midi_io = _open_midi(reg, cfg)
    panel.midi = midi_io
    # panel state and chain must stay one object even after source changes
    # the live objects that get re-classed on a hot reload; re-evaluated
    # each swap so recreated ones (the chain after a source attach) count
    reloader = HotReloader(targets=lambda: [
        (renderer, "render", "Renderer"),
        (s, "render", "ViewState"),
        (panel, "ui", "Panel"),
        (control, "control", "Control"),
        (audio, "audio", "AudioEngine"),
        (audio.chain, "bands", "Chain"),
        *[(p, "bands", "Params") for p in audio.chain.params],
        *([(audio.analyser, "analysis", "Analyser")] if audio.analyser is not None else []),
        (reg, "params", "Registry"),
        *[(p, "params", "Param") for p in reg],
        (overlay, "overlay", "Overlay"),
        *([(midi_io, "midi", "MidiIO"), (midi_io.map, "midi", "MidiMap")] if midi_io else []),
    ])
    panel.reloader = reloader
    keys = Keys(win)
    pad = Pad()
    drag = {"btn": None, "x": 0.0, "y": 0.0}
    depth4, yaw, pitch, zoom = reg["view.depth4"], reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]

    # smoke-test escape hatch: HYPERSPACE_FRAMES=n closes after n frames
    frames_left = int(os.environ.get("HYPERSPACE_FRAMES", "0")) or None

    last = time.perf_counter()
    fps = 0.0
    while not glfw.window_should_close(win):
        if frames_left is not None:
            frames_left -= 1
            if frames_left <= 0:
                glfw.set_window_should_close(win, True)
        glfw.poll_events()
        impl.process_inputs()
        # the imgui frame starts BEFORE input handling: with the 1.87+ event
        # queue, io.mouse_wheel and want_capture_* only hold this frame's
        # values once new_frame() has run — reading them earlier sees zeros.
        imgui.new_frame()
        now = time.perf_counter()
        dt = min(now - last, 0.05)
        last = now
        fps = fps * 0.95 + (1.0 / max(now and dt, 1e-6)) * 0.05

        # the chain object is recreated on source attach; keep bindings fresh
        control.chain = audio.chain
        reloader.poll()

        # ---- polled input, deferring to imgui ----
        if not io.want_capture_keyboard:
            if keys.pressed(glfw.KEY_ESCAPE) or keys.pressed(glfw.KEY_Q):
                glfw.set_window_should_close(win, True)
            for key, pid, op, arg in KEYMAP:
                if keys.pressed(key):
                    act(reg, pid, op, arg)
            if keys.pressed(glfw.KEY_R):
                if keys.down(glfw.KEY_LEFT_SUPER, glfw.KEY_RIGHT_SUPER):
                    _restart(audio, impl, midi_io)
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
            save = keys.down(glfw.KEY_LEFT_SHIFT, glfw.KEY_RIGHT_SHIFT)
            for k in range(SLOTS):
                if keys.pressed(glfw.KEY_F1 + k):
                    act(reg, f"theme.{'save' if save else 'load'}.{k}", "fire")

        # ---- gamepad: a second hand on the same controls (imgui never
        # claims it, so it works even while the panel has keyboard focus) ----
        pad.poll()
        if pad.on:
            for btn, pid, op, arg in PADMAP:
                if pad.pressed(btn):
                    act(reg, pid, op, arg)
            for bit, pid, op, arg in HATMAP:
                if pad.hat_pressed(bit):
                    act(reg, pid, op, arg)
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

        # ---- overlay: window attributes follow the overlay.* params ----
        overlay.apply()
        renderer.bg_alpha = overlay.bg_alpha

        w, h = glfw.get_window_size(win)
        if not io.want_capture_mouse:
            x, y = glfw.get_cursor_pos(win)
            left = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
            right = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
            shift = keys.down(glfw.KEY_LEFT_SHIFT, glfw.KEY_RIGHT_SHIFT)
            # shift+drag pans too — a trackpad has no right button to hold
            btn = "pan" if (right or (left and shift)) else "orbit" if left else None
            if btn != drag["btn"]:
                drag.update(btn=btn, x=x, y=y)
            elif btn == "orbit":
                yaw.set_value(yaw.value + (x - drag["x"]) * 0.005)
                pitch.set_value(pitch.value + (y - drag["y"]) * 0.005)
                drag.update(x=x, y=y)
            elif btn == "pan":
                s.pan[0] += x - drag["x"]
                s.pan[1] += y - drag["y"]
                drag.update(x=x, y=y)
            if io.mouse_wheel:
                factor = 2.0 ** (io.mouse_wheel * 0.15)
                old = s.zoom
                zoom.set_value(old * factor)
                factor = s.zoom / old
                # zoom about the cursor: keep the point under it fixed
                cx, cy = w / 2 + s.pan[0], h / 2 + s.pan[1]
                s.pan[0] += (cx - x) * (factor - 1)
                s.pan[1] += (cy - y) * (factor - 1)
        else:
            drag["btn"] = None

        # ---- audio + rotation + draw, guarded: hot-reloaded code may raise;
        # record it and keep the loop alive so the next save can fix it ----
        ok = True
        try:
            audio.step(dt)
            s.integrate(dt, audio.chain.planedrive if audio.on else None)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("step", e)

        fbw, fbh = glfw.get_framebuffer_size(win)
        ctx.viewport = (0, 0, fbw, fbh)
        try:
            renderer.draw(
                s, max(w, 1), max(h, 1), dpr=fbw / max(w, 1),
                bands=audio.chain.out if audio.on else None,
            )
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("render.draw", e)

        try:
            panel.draw(dt, fps)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("panel.draw", e)
        if ok:
            reloader.runtime_error = ""

        if panel.restart_requested:
            panel.restart_requested = False
            _restart(audio, impl, midi_io)

        if reloader.error or reloader.runtime_error:
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
            imgui.text_colored(
                imgui.ImVec4(1, 0.4, 0.3, 1),
                f"HOT RELOAD  {reloader.error or reloader.runtime_error}",
            )
            imgui.text_disabled("last good code keeps running — fix the file and save")
            imgui.end()

        imgui.render()
        impl.render(imgui.get_draw_data())

        glfw.swap_buffers(win)

    if midi_io is not None:
        midi_io.close()
    audio.stop()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
