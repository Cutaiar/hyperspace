#!/usr/bin/env python3
"""The control panel's footer saying what was undone, as a PNG (plan 15 WP1).

Not the app: a **hidden** GLFW window with the panel drawn over the same
headless objects `tools/undo_demo.py` builds — no render window, no MIDI
port, no audio device, no tracker — on a fresh temp home of its own. It
drags a slider, loads a preset, presses undo twice, and reads the panel
back after each, so the picture is what the footer's message slot draws.

  uv run python tools/undo_shot.py     # → docs/plans/assets/15-safety-net/undo-footer*.png
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
# before anything loads glfw
from __future__ import annotations

import sys
from pathlib import Path

import undo_demo as demo

import glfw
import numpy as np
from imgui_bundle import imgui, implot
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from OpenGL import GL
from PIL import Image

from hyperspace import undo
from hyperspace.app import CONTROL_SIZE
from hyperspace.library import PRESETS
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "15-safety-net"


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "undo shot", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    implot.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)

    r = demo.boot()
    panel = Panel(r.control, r.audio, r.view, bank=r.lib.project, registry=r.reg,
                  library=r.lib)
    panel.clock, panel.lfos, panel.router, panel.learn = r.clock, r.lfos, r.router, r.learn
    panel.hands, panel.hand_settings, panel.output = r.hands_io, r.settings, r.output
    panel.midi, panel.undo = r.midi, r.undo
    panel.reg["ui.page"].set(PAGE_KEYS.index("view"))

    def draw(n: int = 8) -> None:
        for _ in range(n):
            demo.frames(r)
            glfw.poll_events()
            impl.process_inputs()
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            panel.draw(demo.DT, 60.0)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()

    def shoot(name: str) -> None:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        OUT.mkdir(parents=True, exist_ok=True)
        Image.fromarray(px).save(OUT / name, optimize=True)
        print(f"wrote {OUT / name}  — footer: {r.undo.status!r}")

    draw()
    bright = r.reg["view.bright"]
    b0 = bright.base
    for k in range(24):                               # a drag
        bright.set(b0 * (1 + 0.02 * (k + 1)))
        draw(1)
    draw(40)
    r.lib.load(PRESETS, "FACES")                      # a load
    draw(40)
    undo.undo()                                       # what Cmd+Z fires
    draw()
    shoot("undo-footer-load.png")
    draw(20)
    undo.undo()
    draw()
    shoot("undo-footer.png")
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    sys.exit(main())
