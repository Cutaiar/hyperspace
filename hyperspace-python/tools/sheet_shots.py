#!/usr/bin/env python3
"""The control panel as it opens, and after one press of `/` (plan 16 WP1).

Not the app: a **hidden** GLFW window with the panel drawn over the same
headless objects `tools/undo_demo.py` builds — no render window, no MIDI
port, no audio device, no tracker — on a fresh temp home of its own. The
first picture is a `Panel` nobody has touched: no legend, the desk diagram
in the bottom-left corner. The second is the same panel after the `/` key
row has fired once through the router: the legend in the corner and the
desk above it.

  uv run python tools/sheet_shots.py   # → docs/plans/assets/16-paper-cuts/launch-*.png
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

from hyperspace.app import CONTROL_SIZE
from hyperspace.ui import Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "16-paper-cuts"


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "sheet shots", None, None)
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

    def draw(n: int = 12) -> None:
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
        print(f"wrote {OUT / name}  — cheatsheet {panel.cheatsheet}, desk {panel.desk}")

    draw()
    assert not panel.cheatsheet and panel.desk, "the launch state is not sheet off, desk on"
    shoot("launch-no-sheet.png")                      # nothing pressed: the launch state
    r.router.keys(demo.Keys(glfw.KEY_SLASH))          # the `/` row, through the router
    draw()
    assert panel.cheatsheet, "the / row did not bring the sheet up"
    shoot("launch-sheet-on.png")
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    sys.exit(main())
