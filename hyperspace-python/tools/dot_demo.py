#!/usr/bin/env python3
"""The dirty dot and the save label, as a picture (plan 19 WP5).

  uv run python tools/dot_demo.py
      docs/plans/assets/19-presets-and-the-desk/dirty-dot.png: the PRESETS
      page's bank and preset strip in four states — your own preset clean
      and edited ("save"), a factory one clean and edited ("save copy") —
      stacked, each cropped from a **hidden** GLFW window at the control
      size (`app.CONTROL_SIZE`) over the headless objects of
      `tools/undo_demo.py`: not the app, no render window, no MIDI port.
      What the page draws, not what a projector or a screen across a room
      shows.

The home is a fresh temp folder built like the owner's
(`tests/conftest.py::build_owner_home`); `undo_demo` sets
`HYPERSPACE_HOME` to it before anything reads it, so this cannot touch
~/Hyperspace. `Shooter` is shared with tools/trash_demo.py (WP4).
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
# before anything loads glfw
from __future__ import annotations

from pathlib import Path

import undo_demo as demo

from conftest import build_owner_home

from hyperspace import ui_presets
from hyperspace.library import PRESETS

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "19-presets-and-the-desk"
CAPTION_H = 26


class Shooter:
    """A hidden GLFW window at the control size with a Panel over a booted
    headless rig (`demo.boot()`), drawing frames and reading them back."""

    def __init__(self, r, page: str = "presets"):
        import glfw
        from imgui_bundle import imgui, implot
        from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

        from hyperspace.app import CONTROL_SIZE
        from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

        if not glfw.init():
            raise SystemExit("GLFW failed to initialise (no display?)")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        glfw.window_hint(glfw.VISIBLE, False)             # never shown
        self.win = glfw.create_window(*CONTROL_SIZE, "shot", None, None)
        if not self.win:
            glfw.terminate()
            raise SystemExit("could not create the hidden window")
        glfw.make_context_current(self.win)
        imgui.create_context()
        implot.create_context()
        apply_style()
        load_fonts()
        self.impl = GlfwRenderer(self.win)
        self.r = r
        panel = Panel(r.control, r.audio, r.view, bank=r.lib.project, registry=r.reg,
                      library=r.lib)
        panel.clock, panel.lfos, panel.router, panel.learn = r.clock, r.lfos, r.router, r.learn
        panel.hands, panel.hand_settings, panel.output = r.hands_io, r.settings, r.output
        panel.midi, panel.undo = r.midi, r.undo
        panel.reg["ui.page"].set(PAGE_KEYS.index(page))
        self.panel = panel
        self.glfw, self.imgui = glfw, imgui
        self.hooks: list = []                 # called inside each frame, after the panel

    def draw(self, n: int = 6, *, mouse: tuple | None = None) -> None:
        from OpenGL import GL

        glfw, imgui = self.glfw, self.imgui
        for _ in range(n):
            demo.frames(self.r)
            glfw.poll_events()
            self.impl.process_inputs()
            if mouse is not None:
                io = imgui.get_io()
                io.add_mouse_pos_event(*mouse)
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            self.panel.draw(demo.DT, 60.0)
            for hook in self.hooks:
                hook()
            imgui.render()
            self.impl.render(imgui.get_draw_data())
            GL.glFinish()

    def click(self, rect, button: int = 0) -> None:
        """A real mouse click in the middle of `rect`, over three frames."""
        io = self.imgui.get_io()
        x, y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        io.add_mouse_pos_event(x, y)
        self.draw(1)
        io.add_mouse_pos_event(x, y)
        io.add_mouse_button_event(button, True)
        self.draw(1)
        io.add_mouse_pos_event(x, y)
        io.add_mouse_button_event(button, False)
        self.draw(2)

    def grab(self):
        """The window's pixels as a PIL image (framebuffer pixels: on a
        Retina screen twice the window's points)."""
        import numpy as np
        from OpenGL import GL
        from PIL import Image

        w, h = self.glfw.get_framebuffer_size(self.win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        return Image.fromarray(px)

    def scale(self) -> float:
        w, _h = self.glfw.get_framebuffer_size(self.win)
        ww, _wh = self.glfw.get_window_size(self.win)
        return w / ww

    def crop(self, box: tuple[float, float, float, float]):
        s = self.scale()
        return self.grab().crop(tuple(round(v * s) for v in box))

    def close(self) -> None:
        self.impl.shutdown()
        self.glfw.terminate()


def captioned(images: list, captions: list[str]):
    """Stack `images` with a caption bar over each."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    w = max(im.width for im in images)
    h = sum(im.height + CAPTION_H * 2 for im in images)
    out = Image.new("RGB", (w, h), (24, 24, 26))
    y = 0
    for im, cap in zip(images, captions):
        ImageDraw.Draw(out).text((12, y + 12), cap, fill=(200, 200, 205), font=font)
        y += CAPTION_H * 2
        out.paste(im, (0, y))
        y += im.height
    return out


def main() -> None:
    build_owner_home(demo.HOME)
    r = demo.boot()
    lib, reg, pr = r.lib, r.reg, r.lib.project
    lib.warning = ""
    shot = Shooter(r)
    st = ui_presets._state(shot.panel)
    crops, caps = [], []

    def state(slot: int, edit: bool, caption: str) -> None:
        pr.load_slot(slot)
        if edit:
            reg["view.bright"].set(reg["view.bright"].value * 0.6 + 0.1)
        shot.draw(8)
        rects = st["rects"]
        top = rects[f"preset.{max(0, slot - slot % 2)}"][1] - 8
        bottom = rects["strip.presets.name"][3] + 10
        left = rects["preset.0"][0] - 12
        right = rects["preset.1"][2] + 12
        crops.append(shot.crop((left, top, right, bottom)))
        drawn = st["save"]["strip.presets"]
        caps.append(f"{caption}  —  chip: {drawn[0]!r}, {'lit' if drawn[1] else 'quiet'}")
        print(f"{caption}: loaded {lib.current(PRESETS)}, dirty {lib.is_dirty(PRESETS)}, "
              f"chip {drawn}, dot {rects.get('strip.presets.dot')}, "
              f"slot dot {rects.get('preset.dot')}")

    try:
        state(1, False, "yours (NIGHT TWO), clean")
        state(1, True, "yours (NIGHT TWO), edited")
        state(4, False, "factory (TRIP), clean")
        state(4, True, "factory (TRIP), edited")
    finally:
        shot.close()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "dirty-dot.png"
    captioned(crops, caps).save(out, optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
