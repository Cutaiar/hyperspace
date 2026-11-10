"""Render every icon in the table, for eyes and for the diff.

    uv run python hyperspace/dkit/dev/icon_sheet.py --out /tmp/dkit

Writes <out>/icons-imgui.png. `icon_sheet.html` renders the same grid with
the real lucide-react components at the same cell size, so the two can be
compared — arcs converted to cubics are exactly the kind of thing that is
wrong in a way nobody notices by eye.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import glfw
import numpy as np
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from OpenGL import GL
from PIL import Image

HERE = Path(__file__).resolve().parent

from hyperspace.dkit import draw as D

CELL = 64
ICON = 24               # drawn at Lucide's native box, 1 unit = 1 px
COLS = 10


def grid():
    names = sorted(D.ICONS)
    rows = (len(names) + COLS - 1) // COLS
    return names, COLS * CELL, rows * CELL


def render(label: bool) -> np.ndarray:
    names, w, h = grid()
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    for hint, v in ((glfw.CONTEXT_VERSION_MAJOR, 3), (glfw.CONTEXT_VERSION_MINOR, 3),
                    (glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE),
                    (glfw.OPENGL_FORWARD_COMPAT, True), (glfw.VISIBLE, False),
                    (glfw.SAMPLES, 0), (glfw.COCOA_RETINA_FRAMEBUFFER, False)):
        glfw.window_hint(hint, v)
    win = glfw.create_window(w, h, "icons", None, None)
    glfw.make_context_current(win)
    imgui.create_context()
    impl = GlfwRenderer(win)
    ink = (0.04, 0.04, 0.04, 1.0)

    for _ in range(2):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(1, 1, 1, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        dl = imgui.get_background_draw_list()
        for i, n in enumerate(names):
            cx = (i % COLS) * CELL + (CELL - ICON) / 2
            cy = (i // COLS) * CELL + (CELL - ICON) / 2
            if not D.icon(dl, n, cx, cy, ICON, ink):
                raise SystemExit(f"icon {n} did not draw")
        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()

    fw, fh = glfw.get_framebuffer_size(win)
    raw = GL.glReadPixels(0, 0, fw, fh, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    px = np.frombuffer(raw, np.uint8).reshape(fh, fw, 3)[::-1]
    if not px.any():
        raise SystemExit("read back black")
    impl.shutdown()
    glfw.terminate()
    return px.copy()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/dkit")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    px = render(False)
    dest = out / "icons-imgui.png"
    Image.fromarray(px).save(dest)
    names, w, h = grid()
    print(f"wrote {dest}  {w}x{h}  {len(names)} icons at {ICON}px")


if __name__ == "__main__":
    main()
