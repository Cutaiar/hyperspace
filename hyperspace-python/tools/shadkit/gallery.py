"""Render the shadkit gallery to a PNG, headless.

The hidden-window pattern is lifted from tools/sheet_shots.py:40-85 — the
project's established way to screenshot imgui without a display, black-frame
guard included.

    HYPERSPACE_HOME=$(mktemp -d) uv run python tools/shadkit/gallery.py \
        --out /tmp/shadkit

Writes <out>/imgui.png at exactly the spec's canvas size.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import glfw
import numpy as np
import OpenGL.GL as GL
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import draw as D          # noqa: E402
import gradient as G      # noqa: E402
import tokens as T        # noqa: E402

SPEC = json.loads((HERE / "spec.json").read_text())


def render(theme_name: str, tess: float | None = None) -> np.ndarray:
    cv = SPEC["canvas"]
    w, h = int(cv["w"]), int(cv["h"])
    theme = T.LIGHT if theme_name == "light" else T.DARK

    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)
    glfw.window_hint(glfw.SAMPLES, 0)          # the panel window uses 0 too
    win = glfw.create_window(w, h, "shadkit", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    if tess is not None:
        imgui.get_style().circle_tessellation_max_error = tess
    impl = GlfwRenderer(win)

    bg = T.rgba(cv["bg"] if theme_name == "light" else theme["background"])
    grad_tex = G.upload_1d(G.ramp_oklab(*G.CARD_GRADIENT, n=256))

    # Two frames: the first builds the font atlas and settles the backend.
    for _ in range(2):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(bg[0], bg[1], bg[2], 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        dl = imgui.get_background_draw_list()
        for cell in SPEC["cells"]:
            if cell["kind"] == "badge":
                D.badge(dl, cell, theme, T.BADGE)
            elif cell["kind"] == "card":
                D.card(dl, cell, theme, grad_tex)
        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()

    fw, fh = glfw.get_framebuffer_size(win)
    raw = GL.glReadPixels(0, 0, fw, fh, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    px = np.frombuffer(raw, dtype=np.uint8).reshape(fh, fw, 3)[::-1]
    if not px.any():
        raise SystemExit("the hidden window read back black: no picture on this machine")
    if (fw, fh) != (w, h):
        raise SystemExit(f"framebuffer is {fw}x{fh}, spec wants {w}x{h} "
                         "(HiDPI or a window-manager resize)")
    impl.shutdown()
    glfw.terminate()
    return px.copy()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/shadkit")
    ap.add_argument("--theme", default="light", choices=("light", "dark"))
    ap.add_argument("--tess", type=float, default=None,
                    help="ImGui circle_tessellation_max_error")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    px = render(a.theme, a.tess)
    dest = out / "imgui.png"
    Image.fromarray(px).save(dest)
    print(f"wrote {dest}  {px.shape[1]}x{px.shape[0]}  theme={a.theme}")


if __name__ == "__main__":
    main()
