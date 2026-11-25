"""The control window's imgui backend: GLFW's input from imgui_bundle's
Python backend, the drawing from Dear ImGui's own C++ OpenGL 3 one.

The Python backend draws through PyOpenGL, a dozen calls a draw list and
three a command, each a ctypes call: most of a millisecond a frame. Only the
draw is swapped. The Python renderer's objects stay, as its `_update_textures`
still makes the font textures and `replay.py` draws the GRAPH canvas with its
shader and buffers (`replay.BACKEND_ATTRS`); and the clip rects are left in
framebuffer pixels after the draw, as its `render` left them for `replay.grab`.
"""

from __future__ import annotations

from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

GLSL = "#version 330"


class ControlRenderer(GlfwRenderer):
    """`GlfwRenderer`, drawing in C++. One imgui context, on the GL context
    current when it is made. A build with no C++ backend, or one that will
    not start, draws as `GlfwRenderer` does (`native` False)."""

    native = False

    def __init__(self, window, attach_callbacks: bool = True) -> None:
        super().__init__(window, attach_callbacks)
        start = getattr(getattr(imgui, "backends", None), "opengl3_init", None)
        self.native = bool(start is not None and start(GLSL))

    def render(self, draw_data: imgui.ImDrawData) -> None:
        if not self.native:
            super().render(draw_data)
            return
        self._update_textures()             # (so C++ finds every texture made)
        imgui.backends.opengl3_new_frame()  # its shader and buffers, the first time
        imgui.backends.opengl3_render_draw_data(draw_data)
        draw_data.scale_clip_rects(self.io.display_framebuffer_scale)

    def shutdown(self) -> None:
        super().shutdown()                  # the textures, which are the Python backend's
        if self.native:
            self.native = False
            imgui.backends.opengl3_shutdown()
