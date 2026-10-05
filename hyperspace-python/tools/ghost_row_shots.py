#!/usr/bin/env python3
"""The HANDS page's ghost controls with every line showing, as a PNG.

Not the app and not the camera: a **hidden** GLFW window at the control
window's size with the panel drawn over the headless objects
`tools/undo_demo.py` builds, on a fresh temp home of its own. The ghost
is on with a guide and tethers, the tracker's mode is screentop (the
"unmeasured" note) and the ghost reports an error — every ghost line the
page can draw. The second picture is a crop of the panel round them.

  uv run python tools/ghost_row_shots.py [name]
      → docs/plans/assets/21-outputs-and-the-hands/<name>.png  (default ghost-row)
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's
# libglfw before anything loads glfw
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import undo_demo as demo

import glfw
import numpy as np
from imgui_bundle import imgui, implot
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from OpenGL import GL
from PIL import Image

from hyperspace.app import CONTROL_SIZE
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "21-outputs-and-the-hands"
ERROR = "ghost tethers: OSError: cannot open resource"


def main(name: str = "ghost-row") -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "ghost row shot", None, None)
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
    panel.renderer = SimpleNamespace(ghost=SimpleNamespace(error=ERROR))
    r.hands_io.cfg["mode"] = "screentop"
    for pid, v in (("ghost.on", True), ("ghost.guide", 1), ("ghost.tethers", True),
                   ("ghost.style", 1)):
        r.reg[pid].set(v)
    panel.reg["ui.page"].set(PAGE_KEYS.index("hands"))
    rects: dict[str, tuple[float, float, float, float]] = {}
    real = imgui.button

    def button(label, *a, **k):                 # where each button is, as the tests find it
        hit = real(label, *a, **k)
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        rects[label.split("##", 1)[-1]] = (lo.x, lo.y, hi.x, hi.y)
        return hit
    imgui.button = button

    def draw(n: int = 1, mouse=None) -> None:
        for _ in range(n):
            demo.frames(r)
            glfw.poll_events()
            impl.process_inputs()
            if mouse is not None:               # a simulated mouse, after the backend's own
                mouse(imgui.get_io())
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            panel.draw(demo.DT, 60.0)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()

    def shoot(stem: str) -> None:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        OUT.mkdir(parents=True, exist_ok=True)
        img = Image.fromarray(px)
        img.save(OUT / f"{stem}.png", optimize=True)
        # the panel's top half, where the ghost lines are
        s = w / CONTROL_SIZE[0]
        x0 = int((CONTROL_SIZE[0] - 540 - 12) * s)
        img.crop((x0, 0, w, int(h * 0.45))).save(OUT / f"{stem}-crop.png", optimize=True)
        print(f"wrote {OUT / f'{stem}.png'} and the crop — framebuffer {w}×{h} (scale {s:g})")

    try:
        draw(8)
        shoot(name)
        if "ghost.more" in rects:               # the "more ▸" popup, opened by a click
            x0, y0, x1, y1 = rects["ghost.more"]
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
            draw(2, lambda io: io.add_mouse_pos_event(x, y))
            draw(1, lambda io: io.add_mouse_button_event(0, True))
            draw(1, lambda io: io.add_mouse_button_event(0, False))
            draw(4, lambda io: io.add_mouse_pos_event(x - 200, y + 300))
            shoot(f"{name}-more")
    finally:
        imgui.button = real
        impl.shutdown()
        glfw.terminate()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
