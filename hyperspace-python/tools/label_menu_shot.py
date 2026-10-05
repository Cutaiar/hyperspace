#!/usr/bin/env python3
"""The right-click menu opened from a row's label, as a PNG (plan 17 WP3).

Not the app: a **hidden** GLFW window with the panel drawn over the same
headless objects `tools/undo_demo.py` builds — no render window, no MIDI
port, no audio device, no tracker — on a fresh temp home of its own.

Unlike `tools/learn_shot.py`, the popup is opened the way a hand opens
it: imgui is fed a mouse position over the label and a right button going
down and up (`io.add_mouse_button_event`), so the picture exists only if
the label really opens the menu. The mouse cursor itself is not in the
picture (the OS draws it); a small red cross is drawn where it was.

  uv run python tools/label_menu_shot.py     # → docs/plans/assets/17-learn-and-the-desk/menu-on-label.png

`Hidden` is the hidden window, its frames, the fed mouse events and the
read-back, for any shot that needs a real click.
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
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "17-learn-and-the-desk"


class Hidden:
    """A hidden control window with the real Panel over `undo_demo.boot()`."""

    def __init__(self, title: str = "shot"):
        if not glfw.init():
            raise SystemExit("GLFW failed to initialise (no display?)")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        glfw.window_hint(glfw.VISIBLE, False)             # never shown
        self.win = glfw.create_window(*CONTROL_SIZE, title, None, None)
        if not self.win:
            glfw.terminate()
            raise SystemExit("could not create the hidden window")
        glfw.make_context_current(self.win)
        imgui.create_context()
        implot.create_context()
        apply_style()
        load_fonts()
        self.impl = GlfwRenderer(self.win)
        self.r = r = demo.boot()
        self.panel = panel = Panel(r.control, r.audio, r.view, bank=r.lib.project,
                                   registry=r.reg, library=r.lib)
        panel.clock, panel.lfos, panel.router, panel.learn = r.clock, r.lfos, r.router, r.learn
        panel.hands, panel.hand_settings, panel.output = r.hands_io, r.settings, r.output
        panel.midi, panel.undo = r.midi, r.undo
        self.mouse: tuple[float, float] | None = None
        self.cross = False          # draw a red cross where the fed mouse is

    def page(self, key: str) -> None:
        self.panel.reg["ui.page"].set(PAGE_KEYS.index(key))

    def draw(self, n: int = 4, button: tuple[int, bool] | None = None) -> None:
        """`n` frames; `button` (which, down) is fed on the first."""
        for k in range(n):
            demo.frames(self.r)
            glfw.poll_events()
            self.impl.process_inputs()
            io = imgui.get_io()
            if self.mouse is not None:
                io.add_mouse_pos_event(*self.mouse)
            if button is not None and k == 0:
                io.add_mouse_button_event(*button)
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            self.panel.draw(demo.DT, 60.0)
            if self.cross and self.mouse is not None:
                x, y = self.mouse
                dl, red = imgui.get_foreground_draw_list(), 0xFF2B2BFF
                dl.add_line(imgui.ImVec2(x - 7, y), imgui.ImVec2(x + 7, y), red, 2.0)
                dl.add_line(imgui.ImVec2(x, y - 7), imgui.ImVec2(x, y + 7), red, 2.0)
            imgui.render()
            self.impl.render(imgui.get_draw_data())
            GL.glFinish()

    def click(self, x: float, y: float, button: int = 0) -> None:
        """Move there, press, release — a frame or two each, as a hand does."""
        self.mouse = (x, y)
        self.draw(2)
        self.draw(2, (button, True))
        self.draw(3, (button, False))

    def save(self, name: str) -> Path:
        w, h = glfw.get_framebuffer_size(self.win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        OUT.mkdir(parents=True, exist_ok=True)
        Image.fromarray(px).save(OUT / name, optimize=True)
        return OUT / name

    def close(self) -> None:
        self.impl.shutdown()
        glfw.terminate()


def main() -> None:
    pid, page = "camera.zoom", "camera"
    h = Hidden("label menu shot")
    h.page(page)
    where: dict[str, tuple[float, float]] = {}
    opened: list[str] = []
    real_label, real_ctx = Panel._ctx_label, imgui.begin_popup_context_item

    def ctx_label(self, a):
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        where[a.id] = (lo.x + 18, (lo.y + hi.y) / 2)      # on the word, near its start
        return real_label(self, a)

    def begin_ctx(str_id=None, *a, **k):
        hit = real_ctx(str_id, *a, **k)
        if hit:
            opened.append(str_id)
        return hit

    Panel._ctx_label, imgui.begin_popup_context_item = ctx_label, begin_ctx
    try:
        h.draw(8)
        if pid not in where:
            raise SystemExit(f"{pid} has no label on the {page} page")
        h.cross = True
        spot = where[pid]
        h.click(*spot, button=1)                  # a right-click on the word ZOOM
        h.mouse = spot                            # the cross stays where the click was
        h.draw(6)
        if f"##ctx.{pid}" not in opened:
            raise SystemExit("the right-click on the label opened no menu")
        out = h.save("menu-on-label.png")
        print(f"wrote {out}  (right-click fed at {spot}; popup open: ##ctx.{pid})")
    finally:
        Panel._ctx_label, imgui.begin_popup_context_item = real_label, real_ctx
        h.close()


if __name__ == "__main__":
    sys.exit(main())
