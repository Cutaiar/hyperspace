#!/usr/bin/env python3
"""The ROUTING page with its filter typed, beside the same page without, as
a PNG (plan 17 WP5).

Not the app: a **hidden** GLFW window with the panel drawn over the same
headless objects `tools/undo_demo.py` builds — no render window, no MIDI
port, no audio device, no tracker — on a fresh temp home of its own. It
loads TRIP, opens ROUTING, reads the panel back; puts "kaleido" in the
filter (the state write the field makes: nobody types here) and reads it
back again. Left: every row. Right: the red "N of M rows", the × chip and
only the lines that say "kaleido".

  uv run python tools/routing_filter_shot.py
      # → docs/plans/assets/17-learn-and-the-desk/routing-filter.png
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

from hyperspace import ui_routing
from hyperspace.app import CONTROL_SIZE
from hyperspace.library import PRESETS
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "17-learn-and-the-desk"
PRESET, TEXT, GAP = "TRIP", "kaleido", 16


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "routing filter shot", None, None)
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
    r.lib.load(PRESETS, PRESET)
    panel.reg["ui.page"].set(PAGE_KEYS.index("routing"))

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

    def read() -> Image.Image:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        return Image.fromarray(px)

    draw(12)
    every = read()
    n_all = ui_routing.found(panel, r.router)
    ui_routing._state(panel)["find"] = TEXT           # what typing in the field writes
    draw(12)
    some = read()
    n, m = ui_routing.found(panel, r.router)
    sheet = Image.new("RGB", (every.width + GAP + some.width, max(every.height, some.height)),
                      (40, 40, 40))
    sheet.paste(every, (0, 0))
    sheet.paste(some, (every.width + GAP, 0))
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "routing-filter.png", optimize=True)
    print(f"wrote {OUT / 'routing-filter.png'}  — {PRESET}: {n_all[1]} rows; "
          f"{TEXT!r}: {n} of {m} rows")
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    sys.exit(main())
