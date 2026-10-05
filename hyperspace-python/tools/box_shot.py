#!/usr/bin/env python3
"""The HANDS page with an interaction box set, as a PNG (plan 18 WP1).

Not the app and not the camera: a **hidden** GLFW window with the panel
drawn over the headless objects `tools/box_demo.py` builds, on a fresh
temp home of its own, with **synthetic hands** (`tests/fake_hands.py`).
A synthetic sweep sets the box; then the left hand is held inside it (a
filled dot) and the right one 60 mm past its x face (tracked but outside:
a hollow ring, `◌` in the status line, every one of its axes let go).

  uv run python tools/box_shot.py   # → docs/plans/assets/18-hand-and-knob-feel/box-hands-page.png
"""

# ruff: noqa: I001 — box_demo (through undo_demo) is imported first, on
# purpose: it sets HYPERSPACE_HOME to a temp home and points pyGLFW at
# imgui_bundle's libglfw before anything loads glfw
from __future__ import annotations

import sys
from pathlib import Path

import box_demo
import undo_demo as demo
from fake_hands import hand

import glfw
import numpy as np
from imgui_bundle import imgui, implot
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from OpenGL import GL
from PIL import Image

from hyperspace.app import CONTROL_SIZE
from hyperspace.hands import panel as hands_panel
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "18-hand-and-knob-feel"


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "box shot", None, None)
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
    box = box_demo.box_set(r)                         # an old file, then a synthetic sweep
    io = r.hands_io
    panel = Panel(r.control, r.audio, r.view, bank=r.lib.project, registry=r.reg,
                  library=r.lib)
    panel.clock, panel.lfos, panel.router, panel.learn = r.clock, r.lfos, r.router, r.learn
    panel.hands, panel.hand_settings, panel.output = io, r.settings, r.output
    panel.midi, panel.undo = r.midi, r.undo
    panel.reg["ui.page"].set(PAGE_KEYS.index("hands"))
    face = box["x"][1]
    held = lambda t: (hand("left", "open", (-120.0, 170.0, 40.0)),
                      hand("right", "open", (face + 60.0, 330.0, -50.0)))

    for _ in range(12):
        demo.frames(r, hands_at=held)
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        panel.draw(demo.DT, 60.0)
        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()

    w, h = glfw.get_framebuffer_size(win)
    raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
    if not px.any():
        raise SystemExit("the hidden window read back black: no picture on this machine")
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(px).save(OUT / "box-hands-page.png", optimize=True)
    print(f"wrote {OUT / 'box-hands-page.png'}  — synthetic hands; status {hands_panel._ins(io)}; "
          f"box {hands_panel._box_text(box)}; note: {io.cal_note}")
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    sys.exit(main())
