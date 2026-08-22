"""Hyperspace entry point — GLFW window around the renderer.

Keyboard mirrors the reference where the feature exists yet:
  ← / →   previous / next shape        space   pause rotation
  P       toggle points                R       reset view + angles
  [ / ]   brightness down / up         , / .   speed down / up
  1-6     toggle rotation plane        Esc/Q   quit

Audio, transport and the control panel arrive in plans 03–04.
"""

from __future__ import annotations

import time

import glfw
import moderngl

from .geometry import SHAPES, geom
from .render import Renderer, ViewState, clamp

TITLE = "Hyperspace"


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 4)
    win = glfw.create_window(1200, 800, TITLE, None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create a window")
    glfw.make_context_current(win)
    glfw.swap_interval(1)  # vsync

    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    s = ViewState()
    drag = {"on": False, "x": 0.0, "y": 0.0}

    def title() -> None:
        sh = SHAPES[s.shape]
        g = geom(s.shape)
        glfw.set_window_title(
            win, f"{TITLE} — {sh.name} · {g['n']}V {g['m']}E · {sh.sym}"
        )

    def on_key(_w, key, _sc, action, _mods) -> None:
        if action not in (glfw.PRESS, glfw.REPEAT):
            return
        if key in (glfw.KEY_ESCAPE, glfw.KEY_Q):
            glfw.set_window_should_close(win, True)
        elif key == glfw.KEY_RIGHT:
            s.shape = min(len(SHAPES) - 1, s.shape + 1)
            title()
        elif key == glfw.KEY_LEFT:
            s.shape = max(0, s.shape - 1)
            title()
        elif key == glfw.KEY_SPACE:
            s.playing = not s.playing
        elif key == glfw.KEY_P:
            s.points = not s.points
        elif key == glfw.KEY_R:
            s.ang = [0.0] * 6
            s.yaw = s.pitch = 0.0
        elif key == glfw.KEY_LEFT_BRACKET:
            s.bright = clamp(s.bright - 0.1, 0.1, 2.0)
        elif key == glfw.KEY_RIGHT_BRACKET:
            s.bright = clamp(s.bright + 0.1, 0.1, 2.0)
        elif key == glfw.KEY_COMMA:
            s.speed = clamp(s.speed - 0.05, 0.0, 2.0)
        elif key == glfw.KEY_PERIOD:
            s.speed = clamp(s.speed + 0.05, 0.0, 2.0)
        elif glfw.KEY_1 <= key <= glfw.KEY_6:
            p = key - glfw.KEY_1
            s.planes[p] = not s.planes[p]

    def on_mouse(_w, button, action, _mods) -> None:
        if button == glfw.MOUSE_BUTTON_LEFT:
            drag["on"] = action == glfw.PRESS
            drag["x"], drag["y"] = glfw.get_cursor_pos(win)

    def on_cursor(_w, x, y) -> None:
        if drag["on"]:
            s.yaw += (x - drag["x"]) * 0.005
            s.pitch = clamp(s.pitch + (y - drag["y"]) * 0.005, -1.55, 1.55)
            drag["x"], drag["y"] = x, y

    glfw.set_key_callback(win, on_key)
    glfw.set_mouse_button_callback(win, on_mouse)
    glfw.set_cursor_pos_callback(win, on_cursor)
    title()

    last = time.perf_counter()
    while not glfw.window_should_close(win):
        now = time.perf_counter()
        dt = min(now - last, 0.05)  # the reference's dt clamp
        last = now

        s.integrate(dt)  # PLANEDRIVE ≡ 1 until plan 03 wires the chain in

        w, h = glfw.get_window_size(win)
        fbw, fbh = glfw.get_framebuffer_size(win)
        ctx.viewport = (0, 0, fbw, fbh)
        renderer.draw(s, max(w, 1), max(h, 1), dpr=fbw / max(w, 1))

        glfw.swap_buffers(win)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
