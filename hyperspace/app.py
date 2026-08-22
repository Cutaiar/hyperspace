"""Hyperspace entry point — GLFW window, moderngl scene, imgui panel.

Input is polled per frame rather than callback-driven so imgui's own GLFW
callbacks stay undisturbed; anything imgui claims (want_capture_*) is left
to it.

  ← / →  shape      space  pause      P  points     R  reset view
  [ / ]  brightness , / .  speed      1–6  planes   H  panel
  M  mic on/off     K  play/pause     0  restart    Esc/Q  quit
  drag  orbit       right-drag  pan   scroll  zoom about cursor
"""

from __future__ import annotations

import importlib.util
import os
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

from .audio import AudioEngine
from .control import Control
from .geometry import SHAPES
from .render import Renderer, ViewState, clamp
from .ui import Panel, apply_style

TITLE = "Hyperspace"


class Keys:
    """Edge detection over polled key state."""

    def __init__(self, win):
        self.win = win
        self.prev: dict[int, bool] = {}

    def pressed(self, key: int) -> bool:
        down = glfw.get_key(self.win, key) == glfw.PRESS
        was = self.prev.get(key, False)
        self.prev[key] = down
        return down and not was


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
    impl = GlfwRenderer(win)
    io = imgui.get_io()

    audio = AudioEngine()
    control = Control(audio.chain)
    panel = Panel(control, audio, s)
    # panel state and chain must stay one object even after source changes
    keys = Keys(win)
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
        now = time.perf_counter()
        dt = min(now - last, 0.05)
        last = now
        fps = fps * 0.95 + (1.0 / max(now and dt, 1e-6)) * 0.05

        # the chain object is recreated on source attach; keep bindings fresh
        control.chain = audio.chain

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
            if keys.pressed(glfw.KEY_F):
                s.faces = not s.faces
            if keys.pressed(glfw.KEY_H):
                panel.open = not panel.open
            if keys.pressed(glfw.KEY_R):
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

        w, h = glfw.get_window_size(win)
        if not io.want_capture_mouse:
            x, y = glfw.get_cursor_pos(win)
            left = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
            right = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
            btn = "orbit" if left else "pan" if right else None
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

        # ---- audio + rotation ----
        audio.step(dt)
        s.integrate(dt, audio.chain.planedrive if audio.on else None)

        # ---- draw ----
        fbw, fbh = glfw.get_framebuffer_size(win)
        ctx.viewport = (0, 0, fbw, fbh)
        renderer.draw(s, max(w, 1), max(h, 1), dpr=fbw / max(w, 1))

        imgui.new_frame()
        panel.draw(dt, fps)
        imgui.render()
        impl.render(imgui.get_draw_data())

        glfw.swap_buffers(win)

    audio.stop()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
