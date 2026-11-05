"""Measure where ImGui actually puts a 1px stroke and a fill edge.

Draws horizontal lines / fill edges at a range of sub-pixel offsets and prints
the coverage each lands on, so the kit's CSS inset is calibrated against the
real rasterizer instead of against an assumption about ImGui internals.
"""

from __future__ import annotations

import glfw
import numpy as np
import OpenGL.GL as GL
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

W, H = 200, 240


def main() -> None:
    if not glfw.init():
        raise SystemExit("no glfw")
    for hint, v in ((glfw.CONTEXT_VERSION_MAJOR, 3), (glfw.CONTEXT_VERSION_MINOR, 3),
                    (glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE),
                    (glfw.OPENGL_FORWARD_COMPAT, True), (glfw.VISIBLE, False),
                    (glfw.SAMPLES, 0)):
        glfw.window_hint(hint, v)
    win = glfw.create_window(W, H, "probe", None, None)
    glfw.make_context_current(win)
    imgui.create_context()
    impl = GlfwRenderer(win)

    BLACK = imgui.get_color_u32(imgui.ImVec4(0, 0, 0, 1))
    offsets = [0.0, 0.25, 0.5, 0.75, 1.0]

    for _ in range(2):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(1, 1, 1, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        dl = imgui.get_background_draw_list()
        # Block A: add_rect strokes, thickness 1, top edge at y = 20*i + off
        for i, off in enumerate(offsets):
            y = 20.0 * i + 10.0 + off
            dl.add_rect(imgui.ImVec2(20, y), imgui.ImVec2(180, y + 8),
                        BLACK, rounding=0.0, thickness=1.0)
        # Block B: add_rect_filled top edge at y = 120 + 20*i + off
        for i, off in enumerate(offsets):
            y = 120.0 + 20.0 * i + 10.0 + off
            dl.add_rect_filled(imgui.ImVec2(20, y), imgui.ImVec2(180, y + 8), BLACK)
        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()

    raw = GL.glReadPixels(0, 0, W, H, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    px = np.frombuffer(raw, np.uint8).reshape(H, W, 3)[::-1]
    col = px[:, 100, 0].astype(int)          # a column through the straight part

    def cov(v: int) -> float:
        return (255 - v) / 255.0

    print("add_rect (stroke, thickness=1) — top edge requested at y:")
    for i, off in enumerate(offsets):
        y = 20 * i + 10 + off
        rows = [(r, cov(col[r])) for r in range(int(y) - 2, int(y) + 3)
                if cov(col[r]) > 0.01]
        print(f"  y={y:6.2f} -> " + ", ".join(f"row {r}:{c:.2f}" for r, c in rows))

    print("add_rect_filled — top edge requested at y:")
    for i, off in enumerate(offsets):
        y = 120 + 20 * i + 10 + off
        rows = [(r, cov(col[r])) for r in range(int(y) - 2, int(y) + 3)
                if cov(col[r]) > 0.01]
        print(f"  y={y:6.2f} -> " + ", ".join(f"row {r}:{c:.2f}" for r, c in rows))

    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
