#!/usr/bin/env python3
"""The right-click menu with its Unbind submenu open, as a PNG (plan 17 WP1).

Not the app: a **hidden** GLFW window with the panel drawn over the same
headless objects `tools/undo_demo.py` builds — no render window, no MIDI
port, no audio device, no tracker — on a fresh temp home of its own.

Nothing is clicked. The popup is opened by answering the menu's
`begin_popup_context_item` with `open_popup` + `begin_popup` on the same
id (what a right-click on the widget does), and the submenu by telling
imgui the mouse is over its item, so the picture is the menu the panel's
own code draws, in a real imgui popup.

  uv run python tools/learn_shot.py unbind   # → docs/plans/assets/17-learn-and-the-desk/menu-unbind.png
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
from hyperspace.routing import Binding
from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "17-learn-and-the-desk"

# which shot: (the param whose menu opens, its page, the submenu to open, the file)
SHOTS = {
    "unbind": ("view.speed", "view", "Unbind", "menu-unbind.png"),
}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "unbind"
    pid, page, submenu, name = SHOTS[which]
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "learn shot", None, None)
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
    panel.reg["ui.page"].set(PAGE_KEYS.index(page))
    # Speed in TUMBLE has a knob and a hand route; an LFO route, off, beside them
    r.router.table.add(Binding("lfo:0", pid, "push", 0.3, enabled=False))

    st = {"ask": False, "opened": False, "anchor": None, "sub": None, "mouse": None}
    real_ctx, real_menu = imgui.begin_popup_context_item, imgui.begin_menu

    def begin_ctx(str_id=None, *a, **k):
        """The menu of `pid`, opened without a click: the same popup id, in
        the same id scope, as the right-click opens."""
        if str_id != f"##ctx.{pid}":
            return real_ctx(str_id, *a, **k)
        if st["anchor"] is None:                      # where the widget is
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            st["anchor"] = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2)
        if st["ask"] and not st["opened"]:
            imgui.open_popup(str_id)
            st["opened"] = True
        return imgui.begin_popup(str_id)

    def begin_menu(label, *a, **k):
        hit = real_menu(label, *a, **k)
        if label == submenu:                          # where to hold the mouse
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            st["sub"] = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2)
        return hit

    imgui.begin_popup_context_item, imgui.begin_menu = begin_ctx, begin_menu

    def draw(n: int = 8) -> None:
        for _ in range(n):
            demo.frames(r)
            glfw.poll_events()
            impl.process_inputs()
            if st["mouse"] is not None:
                imgui.get_io().add_mouse_pos_event(*st["mouse"])
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            panel.draw(demo.DT, 60.0)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()

    draw()
    if st["anchor"] is None:
        raise SystemExit(f"{pid} is not drawn on the {page} page")
    st["mouse"] = st["anchor"]                        # the popup opens at the mouse
    draw(3)
    st["ask"] = True
    draw(4)
    if st["sub"] is not None:
        st["mouse"] = st["sub"]                       # hover the submenu's item: it opens
        draw(30)
    w, h = glfw.get_framebuffer_size(win)
    raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
    if not px.any():
        raise SystemExit("the hidden window read back black: no picture on this machine")
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(px).save(OUT / name, optimize=True)
    print(f"wrote {OUT / name}  (popup opened: {st['opened']}, submenu found: {st['sub']})")
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    sys.exit(main())
