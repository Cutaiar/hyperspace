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
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from OpenGL import GL
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import comp_button as CB
import comp_combobox as CC
import draw as D
import gradient as G
import interact as I
import menu as M
import tokens as T
from ease import Anim

SPEC = json.loads((HERE / "spec.json").read_text())


def _menu_items():
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
    checkboxes = T.checkbox_table(theme_name)
    kbds = T.kbd_table(theme_name)
    inputs = T.input_table(theme_name)
    selects = T.select_table(theme_name)
    tips = T.tooltip_table(theme_name)
    buttons = CB.button_table(theme_name)
    combos = CC.combobox_table(theme_name)
    ink = T.rgba("foreground", theme=theme)

    # Two frames: the first builds the font atlas and settles the backend.
    for _ in range(2):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(bg[0], bg[1], bg[2], 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        dl = imgui.get_background_draw_list()
        # ONE Ui for the frame, inside `interact.chrome()`. The audit that
        # found this missing was looking for ImGui's blue nav cursor and its
        # pale text selection, neither of which has a shadcn counterpart.
        # Neither can actually appear here today - the gallery submits no
        # widgets, and the green diff is the proof at 0 background pixels -
        # and `_sandwich_begin` clears nav_cursor per component anyway. It is
        # held for the whole frame regardless, so a cell that one day DOES
        # submit a widget cannot reintroduce either, and so the harness sets
        # the style up the same way dashboard.py does.
        mui = I.Ui(dl, faces, theme, Anim(), theme_name=theme_name)
        with I.chrome(mui):
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
                elif cell["kind"] == "kbd":
                    # The width is the SPEC's - the browser's intrinsic one -
                    # as a Button's is: the kit's text widths run a few
                    # percent wide of Chromium's (see draw.kbd), so drawing
                    # at the kit's own width would measure the font loader,
                    # not the Kbd. test_kbd.py checks the width law.
                    # The tooltip variant sits on a tooltip-coloured ground,
                    # which is what its `in-data-[slot=tooltip-content]`
                    # restyle is drawn against.
                    tip = cell["variant"] == "tooltip"
                    if tip:
                        D.fill(dl, cell["x"] - 6, cell["y"] - 6,
                               cell["w"] + 12, cell["h"] + 12,
                               T.rgba("foreground", theme=theme))
                    D.kbd(dl, cell["x"], cell["y"], cell["text"], faces,
                          theme, kbds, in_tooltip=tip, glyphs=False,
                          w=cell["w"])
                elif cell["kind"] == "checkbox":
                    # the canvas colour is the backdrop a disabled checked
                    # box folds its group opacity against - see draw.checkbox
                    D.checkbox(dl, cell["x"], cell["y"],
                               1.0 if cell["on"] else 0.0, bool(cell["on"]),
                               theme, checkboxes,
                               disabled=cell.get("disabled", False),
                               backdrop=bg)
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
                    # The ROOT rect, not the viewport. `scroll_bar` insets by the
                    # region's own border itself - that is what its `border`
                    # argument is for, and interact.scroll_area passes the root
                    # the same way - so handing it the already-inset viewport
                    # counted the border TWICE: the track came out at (y+2, 114)
                    # where the browser's is (y+1, 116), putting the thumb 1px
                    # left, 1px down at frac 0, and 0.59px short at frac 1.
                    #
                    # `viewport_h` stays cell.h - 2, which IS the browser's
                    # clientHeight - the ratio that sizes the thumb is the
                    # viewport's, while the track it slides in is the bar's.
                    D.scroll_bar(dl, cell["x"], cell["y"], cell["w"], cell["h"],
                                 vp, float(cell["content"]),
                                 cell["frac"] * (cell["content"] - vp), theme)
                elif cell["kind"] == "menu":
                    # The chrome that menu.popup draws, without the popup - the
                    # one component the kit shipped with NO cell here, which is
                    # how six wrong row metrics survived in it.
                    M.panel_chrome(mui, dl, cell["x"], cell["y"],
                                   cell["w"], cell["h"])
                    M.rows(mui, MENU_CELL_ITEMS, cell["x"] + M.PAD,
                           cell["y"] + M.PAD, cell["w"] - 2 * M.PAD,
                           "gallery.menu", chrome_only=True)
                elif cell["kind"] == "combobox":
                    # The CLOSED trigger, which in this component IS the input.
                    # field_chrome rather than _input_trigger: the latter submits
                    # a real imgui.input_text, and a widget outside any window
                    # makes ImGui auto-create its "Debug" window over the canvas.
                    #
                    # The open PANEL is not a cell: its chrome is literally
                    # menu.panel_chrome now, so `menu.panel` and
                    # `contextmenu.panel` already measure it. What is still
                    # outside the diff is the panel's ROWS - see HANDOFF.
                    CC.field_chrome(mui, cell["x"], cell["y"], cell["w"],
                                    cell["h"], combos, text=False,
                                    disabled=cell["variant"] == "disabled")
                elif cell["kind"] == "contextmenu":
                    # Identical chrome to the `menu` cell by design: a
                    # ContextMenu routes its panel through menu.popup, and since
                    # menu.py's six row metrics were corrected the only thing
                    # comp_context_menu still overrides is min_w (144, min-w-36
                    # against the DropdownMenu's min-w-32). The cell is here to
                    # hold the REAL ContextMenu component to that, rather than
                    # inferring it from the DropdownMenu's cell passing.
                    M.panel_chrome(mui, dl, cell["x"], cell["y"],
                                   cell["w"], cell["h"])
                    M.rows(mui, MENU_CELL_ITEMS, cell["x"] + M.PAD,
                           cell["y"] + M.PAD, cell["w"] - 2 * M.PAD,
                           "gallery.ctxmenu", chrome_only=True)
                elif cell["kind"] == "button":
                    # label "" is the chrome pass: the oracle paints its text
                    # transparent, so the kit must draw none. Everything being
                    # measured here - the size-dependent radius, the padding-box
                    # fill, the disabled double-dim - is independent of it.
                    CB.button(dl, cell["x"], cell["y"], cell["w"], cell["h"],
                              "", faces, theme, buttons,
                              variant=cell["variant"], size=cell["size"],
                              disabled=cell.get("disabled", False))
                elif cell["kind"] == "buttongroup":
                    # The members are tiled from the PINNED widths rather than
                    # from button_group_place's intrinsic ones, for the same
                    # reason the spec pins them: an intrinsic width is a text
                    # measurement. The joins are the thing under test.
                    ori = cell["orientation"]
                    rects, cx, cy = [], cell["x"], cell["y"]
                    for m in cell["members"]:
                        if ori == "horizontal":
                            rects.append((cx, cell["y"], float(m), cell["h"]))
                            cx += m
                        else:
                            rects.append((cell["x"], cy, cell["w"], float(m)))
                            cy += m
                    for r, j in zip(rects, CB.button_group(rects, ori)):
                        CB.button(dl, r[0], r[1], r[2], r[3], "", faces, theme,
                                  buttons, variant=cell["variant"],
                                  size="default", join=j)
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
