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

An Xbox-layout gamepad (Bluetooth or USB) is a second hand on the same
controls — see gamepad.py for the index map and ui.CHEATSHEET for the
bindings: A pause · B next theme · X points · Y faces · LB/RB shape ·
d-pad brightness/speed · sticks orbit/zoom (click resets) · LT/RT 4D
depth · View panel · Menu cheat sheet.

The in-app cheat sheet (ui.CHEATSHEET) is the canonical list — keep the
two in sync when adding bindings.

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

from . import gamepad
from .audio import AudioEngine
from .control import Control
from .gamepad import Pad
from .geometry import SHAPES
from .hotreload import HotReloader
from .presets import SLOTS, Presets
from .render import Renderer, ViewState, clamp
from .tapers import T_DEPTH
from .ui import Panel, apply_style, load_fonts

TITLE = "Hyperspace"

# 4D perspective hold keys move depth4 in the taper's own log space —
# octaves of (depth − 1) — so travel feels even across the whole throw.
# The rate eases in quadratically from a tap-sized nudge to full speed.
D4_RATE0 = 0.45   # octaves/s at the instant of the press
D4_RATE1 = 3.6    # octaves/s once the ramp completes
D4_RAMP = 1.8     # seconds of hold to reach full rate
D4_LO = T_DEPTH.map(0)
D4_HI = T_DEPTH.map(T_DEPTH.steps)


def _err(where: str, e: Exception) -> str:
    return f"{where}: {type(e).__name__}: {e}"[:160]


def _restart(audio, impl) -> None:
    # execv swaps the process image in place — same PID, same terminal,
    # same stdio — so stdout doesn't detach and the user's shell keeps
    # owning the child. The OS reclaims the GL context and audio device
    # on image swap; we still stop the audio stream first so Core Audio
    # doesn't complain about a stream vanishing mid-callback.
    try:
        audio.stop()
    except Exception:  # noqa: BLE001
        pass
    try:
        impl.shutdown()
    except Exception:  # noqa: BLE001
        pass
    try:
        glfw.terminate()
    except Exception:  # noqa: BLE001
        pass
    os.execv(sys.executable, [sys.executable, *sys.argv])


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


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 4)
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

    audio = AudioEngine()
    control = Control(audio.chain)
    presets = Presets(s, control, audio)
    panel = Panel(control, audio, s, renderer, presets)
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
    ])
    panel.reloader = reloader
    keys = Keys(win)
    pad = Pad()
    drag = {"btn": None, "x": 0.0, "y": 0.0}

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
            if keys.pressed(glfw.KEY_RIGHT):
                s.shape = min(len(SHAPES) - 1, s.shape + 1)
            if keys.pressed(glfw.KEY_LEFT):
                s.shape = max(0, s.shape - 1)
            if keys.pressed(glfw.KEY_SPACE):
                s.playing = not s.playing
            if keys.pressed(glfw.KEY_P):
                s.points = not s.points
            if keys.pressed(glfw.KEY_L):
                s.lines = not s.lines
            if keys.pressed(glfw.KEY_F):
                s.faces = not s.faces
            if keys.pressed(glfw.KEY_H):
                panel.open = not panel.open
            if keys.pressed(glfw.KEY_SLASH):
                panel.cheatsheet = not panel.cheatsheet
            cmd = (
                glfw.get_key(win, glfw.KEY_LEFT_SUPER) == glfw.PRESS
                or glfw.get_key(win, glfw.KEY_RIGHT_SUPER) == glfw.PRESS
            )
            if keys.pressed(glfw.KEY_R):
                if cmd:
                    _restart(audio, impl)
                else:
                    s.ang = [0.0] * 6
                    s.yaw = s.pitch = 0.0
                    s.zoom, s.pan = 1.0, [0.0, 0.0]
            if keys.pressed(glfw.KEY_LEFT_BRACKET):
                s.bright = clamp(s.bright - 0.1, 0.13, 4.0)
            if keys.pressed(glfw.KEY_RIGHT_BRACKET):
                s.bright = clamp(s.bright + 0.1, 0.13, 4.0)
            if keys.pressed(glfw.KEY_COMMA):
                s.speed = clamp(s.speed - 0.05, 0.0, 4.0)
            if keys.pressed(glfw.KEY_PERIOD):
                s.speed = clamp(s.speed + 0.05, 0.0, 4.0)
            if keys.pressed(glfw.KEY_M):
                if audio.on and audio.mode == "mic":
                    audio.stop()
                elif panel.devices:
                    audio.start_mic(panel.devices[panel.device_sel]["index"])
            if keys.pressed(glfw.KEY_K):
                audio.toggle_play()
            if keys.pressed(glfw.KEY_0):
                audio.restart()
            for p in range(6):
                if keys.pressed(glfw.KEY_1 + p):
                    s.planes[p] = not s.planes[p]
            # ↑/↓ ride depth4 toward its range limit, accelerating with hold
            for key, sgn in ((glfw.KEY_UP, 1.0), (glfw.KEY_DOWN, -1.0)):
                hold = keys.held(key)
                if hold > 0.0:
                    ramp = min(hold / D4_RAMP, 1.0)
                    rate = D4_RATE0 + (D4_RATE1 - D4_RATE0) * ramp * ramp
                    u = math.log2(max(s.depth4 - 1.0, 1e-6) / 0.05)
                    s.depth4 = clamp(
                        1.0 + 0.05 * 2.0 ** (u + sgn * rate * dt), D4_LO, D4_HI
                    )
            # F1–F8 flip whole-surface themes; with ⇧ held they save instead
            save = (
                glfw.get_key(win, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
                or glfw.get_key(win, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS
            )
            for k in range(SLOTS):
                if keys.pressed(glfw.KEY_F1 + k):
                    (presets.save if save else presets.load)(k)

        # ---- gamepad: a second hand on the same controls (imgui never
        # claims it, so it works even while the panel has keyboard focus) ----
        pad.poll()
        if pad.on:
            if pad.pressed(gamepad.A):
                s.playing = not s.playing
            if pad.pressed(gamepad.B):
                presets.cycle()
            if pad.pressed(gamepad.X):
                s.points = not s.points
            if pad.pressed(gamepad.Y):
                s.faces = not s.faces
            if pad.pressed(gamepad.LB):
                s.shape = max(0, s.shape - 1)
            if pad.pressed(gamepad.RB):
                s.shape = min(len(SHAPES) - 1, s.shape + 1)
            if pad.pressed(gamepad.VIEW):
                panel.open = not panel.open
            if pad.pressed(gamepad.MENU):
                panel.cheatsheet = not panel.cheatsheet
            if pad.pressed(gamepad.LSTICK) or pad.pressed(gamepad.RSTICK):
                s.ang = [0.0] * 6
                s.yaw = s.pitch = 0.0
                s.zoom, s.pan = 1.0, [0.0, 0.0]
            if pad.hat_pressed(gamepad.HAT_UP):
                s.bright = clamp(s.bright + 0.1, 0.13, 4.0)
            if pad.hat_pressed(gamepad.HAT_DOWN):
                s.bright = clamp(s.bright - 0.1, 0.13, 4.0)
            if pad.hat_pressed(gamepad.HAT_LEFT):
                s.speed = clamp(s.speed - 0.05, 0.0, 4.0)
            if pad.hat_pressed(gamepad.HAT_RIGHT):
                s.speed = clamp(s.speed + 0.05, 0.0, 4.0)
            # analog: left stick orbits, right-stick Y zooms about centre,
            # triggers ride depth4 in its own log space (LT out, RT in)
            s.yaw += pad.axis(gamepad.AX_LX) * 2.2 * dt
            s.pitch = clamp(
                s.pitch + pad.axis(gamepad.AX_LY) * 2.2 * dt, -1.55, 1.55
            )
            zoom_v = pad.axis(gamepad.AX_RY)
            if zoom_v:
                s.zoom = clamp(s.zoom * 2.0 ** (-zoom_v * 1.2 * dt), 0.05, 40.0)
            d4 = pad.trigger(gamepad.AX_RT) - pad.trigger(gamepad.AX_LT)
            if d4:
                u = math.log2(max(s.depth4 - 1.0, 1e-6) / 0.05)
                s.depth4 = clamp(
                    1.0 + 0.05 * 2.0 ** (u + d4 * 2.4 * dt),
                    T_DEPTH.map(0), T_DEPTH.map(T_DEPTH.steps),
                )

        w, h = glfw.get_window_size(win)
        if not io.want_capture_mouse:
            x, y = glfw.get_cursor_pos(win)
            left = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
            right = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
            shift = (
                glfw.get_key(win, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
                or glfw.get_key(win, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS
            )
            # shift+drag pans too — a trackpad has no right button to hold
            btn = "pan" if (right or (left and shift)) else "orbit" if left else None
            if btn != drag["btn"]:
                drag.update(btn=btn, x=x, y=y)
            elif btn == "orbit":
                s.yaw += (x - drag["x"]) * 0.005
                s.pitch = clamp(s.pitch + (y - drag["y"]) * 0.005, -1.55, 1.55)
                drag.update(x=x, y=y)
            elif btn == "pan":
                s.pan[0] += x - drag["x"]
                s.pan[1] += y - drag["y"]
                drag.update(x=x, y=y)
            if io.mouse_wheel:
                factor = 2.0 ** (io.mouse_wheel * 0.15)
                new_zoom = clamp(s.zoom * factor, 0.05, 40.0)
                factor = new_zoom / s.zoom
                # zoom about the cursor: keep the point under it fixed
                cx, cy = w / 2 + s.pan[0], h / 2 + s.pan[1]
                s.pan[0] += (cx - x) * (factor - 1)
                s.pan[1] += (cy - y) * (factor - 1)
                s.zoom = new_zoom
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
            _restart(audio, impl)

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

    audio.stop()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
