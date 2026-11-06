"""Render the dkit gallery to a PNG, headless.

The hidden-window pattern is lifted from tools/sheet_shots.py:40-85 — the
project's established way to screenshot imgui without a display, black-frame
guard included.

    HYPERSPACE_HOME=$(mktemp -d) uv run python tools/dkit/gallery.py \
        --out /tmp/dkit

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
from ease import Anim     # noqa: E402
import gradient as G      # noqa: E402
import tokens as T        # noqa: E402

SPEC = json.loads((HERE / "spec.json").read_text())


def _menu_items():
    import menu as M
    return [M.heading("Node"),
            M.Item(id="open", label="Open", shortcut="K"),
            M.Item(id="dup", label="Duplicate"),
            M.sep(),
            M.Item(id="del", label="Delete", variant="destructive")]

# Geist ships only as a variable woff2, which stb_truetype can read neither of.
# tools/dkit/fonts holds static instances cut from that exact file at the
# three weights shadcn uses, so the comparison is the same typeface.
FACES = dict(D.FACE_FILES)


def load_faces():
    # 1.92 builds the atlas lazily; there is no Build() any more
    return D.load_faces(imgui.get_io(), HERE)


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
    # 1:1 pixels on a Retina Mac too, or the framebuffer comes back at 2x and
    # the size check below trips. No-op off macOS.
    glfw.window_hint(glfw.COCOA_RETINA_FRAMEBUFFER, False)
    win = glfw.create_window(w, h, "dkit", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    if tess is not None:
        imgui.get_style().circle_tessellation_max_error = tess
    impl = GlfwRenderer(win)

    bg = T.rgba(cv["bg"] if theme_name == "light" else theme["background"])
    LL = T.LIGHT_L if theme_name == "light" else T.DARK_L
    grad_tex = G.upload_1d(G.ramp_oklab(*G.card_gradient(LL), n=256))
    faces = load_faces()
    badges = T.badge_table(theme_name)
    global MENU_CELL_ITEMS
    MENU_CELL_ITEMS = _menu_items()
    sliders = T.slider_table(theme_name)
    switches = T.switch_table(theme_name)
    inputs = T.input_table(theme_name)
    selects = T.select_table(theme_name)
    tips = T.tooltip_table(theme_name)
    ink = T.rgba("foreground", theme=theme)

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
                D.badge(dl, cell, theme, badges)
            elif cell["kind"] == "card":
                D.card(dl, cell, theme, grad_tex)
            elif cell["kind"] == "slider":
                D.slider(dl, cell["x"], cell["y"], cell["w"], cell["h"],
                         cell["fracs"], theme, sliders)
            elif cell["kind"] == "switch":
                D.switch(dl, cell["x"], cell["y"], 1.0 if cell["on"] else 0.0,
                         theme, switches, size=cell["variant"])
            elif cell["kind"] == "input":
                D.field(dl, cell["x"], cell["y"], cell["w"], cell["h"],
                        theme, inputs,
                        invalid=cell["variant"] == "invalid",
                        disabled=cell["variant"] == "disabled")
            elif cell["kind"] == "select":
                D.select_trigger(dl, cell["x"], cell["y"], cell["w"],
                                 cell["h"], theme, selects,
                                 size=cell["variant"])
            elif cell["kind"] == "tooltip":
                # The oracle pins the TRIGGER at the cell's bottom centre and
                # lets Radix place the panel, so the arrow is centred there.
                D.tooltip_panel(dl, cell["x"], cell["y"], cell["w"],
                                cell["h"], theme, tips,
                                arrow_at=cell["x"] + cell["w"] / 2.0)
            elif cell["kind"] == "scroll":
                # the box, then the overlay thumb at a pinned scroll
                D.box(dl, cell["x"], cell["y"], cell["w"], cell["h"],
                      # Tailwind's bare `border` is border-border, NOT
                      # input. They are the same #e5e5e5 in light and differ
                      # in dark (10% vs 15% white), so this only showed up
                      # on the dark pass - 510 pixels of it.
                      border_col=T.rgba("border", theme=theme),
                      radius=T.RADII["lg"], border_w=1.0)
                vp = cell["h"] - 2.0
                D.scroll_bar(dl, cell["x"] + 1.0, cell["y"] + 1.0,
                             cell["w"] - 2.0, vp, vp, float(cell["content"]),
                             cell["frac"] * (cell["content"] - vp), theme)
            elif cell["kind"] == "menu":
                # The chrome that menu.popup draws, without the popup - the
                # one component the kit shipped with NO cell here, which is
                # how six wrong row metrics survived in it.
                import menu as M
                import interact as I
                mui = I.Ui(dl, faces, theme, Anim(), theme_name=theme_name)
                M.panel_chrome(mui, dl, cell["x"], cell["y"],
                               cell["w"], cell["h"])
                M.rows(mui, MENU_CELL_ITEMS, cell["x"] + M.PAD,
                       cell["y"] + M.PAD, cell["w"] - 2 * M.PAD,
                       "gallery.menu", chrome_only=True)
            elif cell["kind"] == "text":
                D.text_cell(dl, cell, faces, ink)
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
    ap.add_argument("--out", default="/tmp/dkit")
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
