"""The kit's additions from Hyperspace's adoption, before and after, as
labelled images for a person to accept or reject — each drawn by the kit's
own code (no mock-ups), in the kit's light and dark themes and in the
theme Hyperspace hands it (`hyperspace.ui_kit.theme` / `tables`).

    xvfb-run -a uv run python hyperspace/dkit/dev/additions_sheet.py --out /tmp/sheet

Writes one PNG per addition (`<out>/<n>-<name>.png`). Each image is a grid:
a row per theme, BEFORE (what the kit did) on the left, AFTER (the
addition) on the right.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import glfw
import numpy as np
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from OpenGL import GL
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent

from hyperspace.dkit import comp_button as CB
from hyperspace.dkit import draw as D
from hyperspace.dkit import interact as I
from hyperspace.dkit import menu as M
from hyperspace.dkit import tokens as T
from hyperspace.dkit.ease import Anim
from hyperspace.dkit.rect import stretched_hit

CELL_W, CELL_H = 360, 150


def _boot(w: int, h: int):
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)
    glfw.window_hint(glfw.COCOA_RETINA_FRAMEBUFFER, False)
    win = glfw.create_window(w, h, "sheet", None, None)
    glfw.make_context_current(win)
    imgui.create_context()
    return win, GlfwRenderer(win)


def shot(theme_name: str, paint, frames: int = 3, w: int = CELL_W, h: int = CELL_H,
         host_type: bool = False) -> np.ndarray:
    """One cell: `paint(ui, dl)` drawn in a fresh context, `frames` frames
    (the first builds the atlas; popups open on the next). `theme_name`:
    "light", "dark" or "hyperspace" (the panel's palette and tables)."""
    win, impl = _boot(w, h)
    io = imgui.get_io()
    tables: dict = {}
    if theme_name == "hyperspace":
        from hyperspace import ui as hui
        from hyperspace import ui_kit
        hui.apply_style()
        theme, name, tables = ui_kit.theme(), "dark", ui_kit.tables()
        bg = imgui.get_style().color_(imgui.Col_.window_bg)
        bg = (bg.x, bg.y, bg.z)
        if host_type:
            fonts = Path(hui.__file__).parent / "fonts"
            faces = D.host_faces(io, {"regular": fonts / "Inter-Medium.ttf",
                                      "medium": fonts / "Inter-Medium.ttf",
                                      "semibold": fonts / "Inter-Bold.ttf"},
                                 fallback=fonts / "DejaVuSans.ttf")
        else:
            faces = D.load_faces(io)
    else:
        theme = T.LIGHT if theme_name == "light" else T.DARK
        name = theme_name
        bg = T.rgba(theme["background"])[:3]
        faces = D.load_faces(io)
    anim = Anim()
    px = None
    for _ in range(frames):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(bg[0], bg[1], bg[2], 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        imgui.set_next_window_pos(imgui.ImVec2(0, 0))
        imgui.set_next_window_size(imgui.ImVec2(w, h))
        imgui.push_style_color(imgui.Col_.window_bg, imgui.ImVec4(0, 0, 0, 0))
        imgui.begin("##sheet", None, imgui.WindowFlags_.no_decoration | imgui.WindowFlags_.no_background)
        ui = I.Ui(imgui.get_window_draw_list(), faces, theme, anim, theme_name=name,
                  tables=tables, unique_keys=False)
        with I.chrome(ui):
            paint(ui, ui.dl)
        imgui.end()
        imgui.pop_style_color()
        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()
        ui.frame_done(1 / 60)
        fw, fh = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, fw, fh, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(fh, fw, 3)[::-1].copy()
    impl.shutdown()
    glfw.terminate()
    return px


def label(ui, x, y, s, size=12.0):
    D.label(ui.dl, x, y, s, ui.faces, "regular", size, ui.col("muted-foreground"))


# ------------------------------------------------------------ the additions

CHIPS = (("tidy", "outline"), ("expand all", "outline"), ("patched only", "default"),
         ("save", "secondary"))


def chip_before(ui, dl):
    """`comp_button.button`, the general path: chrome only, the words being
    the host's either way."""
    t = CB._table_for(ui)
    x = 20
    for words, variant in CHIPS:
        w, h = CB.button_size("sm", words, ui.faces)
        CB.button(dl, x, 50, w, h, "", ui.faces, ui.theme, t, variant=variant, size="sm",
                  hot=1.0 if words == "tidy" else 0.0)
        x += w + 8
    label(ui, 20, 100, "comp_button.button (general path), chrome only")


def chip_after(ui, dl):
    """`comp_button.chip_chrome`, the lean path, the same four."""
    x = 20
    for words, variant in CHIPS:
        w, h = CB.button_size("sm", words, ui.faces)
        CB.chip_chrome(ui, dl, x, 50, w, h, variant, hot=1.0 if words == "tidy" else 0.0)
        x += w + 8
    label(ui, 20, 100, "comp_button.chip_chrome (lean), chrome only")


def _switch_row(ui, dl, row: bool):
    words = ("Points", "Lines", "Rotate")
    x, y, rh = 20, 44, 28
    sw, sh, _ = T.SWITCH_SIZES["sm"]
    for i, wd in enumerate(words):
        tw = D.text_w(wd, ui.faces, "regular", 14)
        w = rh + 7 + tw
        sx, sy = x + (rh - sw) / 2, y + (rh - sh) / 2
        I.switch(ui, f"s{i}{row}", sx, sy, i != 1, size="sm",
                 row=(x, y, w, rh) if row else None)
        D.label(dl, x + rh + 7, y, wd, ui.faces, "regular", 14, ui.col("foreground"),
                baseline_box=rh)
        if row:
            hit = (x, y, w, rh)
        else:
            r = stretched_hit(sx, sy, sw, sh, stretch=T.HIT_STRETCH, border=1.0)
            hit = (r.x, r.y, r.w, r.h)
        D.border(dl, hit[0], hit[1], hit[2], hit[3], (1.0, 0.2, 0.2, 0.9), 2.0, 1.0)
        x += w + 10


def switch_before(ui, dl):
    _switch_row(ui, dl, row=False)
    label(ui, 20, 100, "red: each switch's click target - the switch alone")
    label(ui, 20, 116, "(its words take no click; in a row it pokes 1-2 px into the next)", 11)


def switch_after(ui, dl):
    _switch_row(ui, dl, row=True)
    label(ui, 20, 100, "interact.switch(row=...): the target is the switch AND its words")


TAB_WORDS = ["Selection", "Patches", "Audio", "Routing", "Playlist", "Players", "System"]
TAB_ICONS = ["mouse_pointer_2", "layers", "audio_lines", "route", "list_music", "users", "cpu"]


def tabs_before(ui, dl):
    I.tabs(ui, "tb", 10, 40, 32, TAB_WORDS[:3], 1)
    label(ui, 10, 100, "interact.tabs: words, ids <key>.<i>, natural width")


def tabs_after(ui, dl):
    I.tabs(ui, "ta", 10, 40, 32, TAB_WORDS, 1, keys=[f"pane.{w.lower()}" for w in TAB_WORDS],
           icons=TAB_ICONS, w=300, active_ink="primary")
    label(ui, 10, 100, "keys=, icons=, w= (even), active_ink=")


def _narrow(ui, dl, box: bool):
    for i, (w, v) in enumerate(((56, 0.62), (72, 0.3), (240, 0.45))):
        y = 30 + i * 36
        I.slider(ui, f"n{i}{box}", 20, y, w, 28, v, fine=False, box=box and w < 100)
        if box and w < 100:
            D.label(dl, 20, y, f"{v * 30:.2f}", ui.faces, "regular", 14, ui.col("foreground"),
                    align="center", box_w=w, baseline_box=28, tabular=True)
        else:
            D.label(dl, 20 + w + 8, y, f"{v * 30:.2f}", ui.faces, "regular", 14,
                    ui.col("foreground"), baseline_box=28, tabular=True)


def box_before(ui, dl):
    _narrow(ui, dl, box=False)


def box_after(ui, dl):
    _narrow(ui, dl, box=True)


SHAPES = [f"shape {i:02d}" for i in range(1, 25)]


def _menu(ui, dl, cap):
    items = [M.Item(id=str(i), label=s, checked=i == 3) for i, s in enumerate(SHAPES)]
    I.select(ui, "shape", 20, 14, 200, SHAPES[3], items, size="sm", max_h=cap)
    if not imgui.is_popup_open("##sel.shape"):
        imgui.open_popup("##sel.shape")


def menu_before(ui, dl):
    _menu(ui, dl, None)


def menu_after(ui, dl):
    _menu(ui, dl, 220.0)


def type_cell(ui, dl):
    x = 20
    for words, variant in (("save", "secondary"), ("as…", "outline")):
        w, h = CB.button_size("sm", words, ui.faces)
        CB.button(dl, x, 40, w, h, words, ui.faces, ui.theme, CB._table_for(ui), variant=variant,
                  size="sm")
        x += w + 8
    D.kbd(dl, x + 4, 44, "R", ui.faces, ui.theme, T.kbd_table(ui.theme_name))
    I.select(ui, "t", 20, 80, 200, "Balanced", [M.Item(id="a", label="Balanced")], size="sm")


ADDITIONS = [
    ("chip-chrome", "Button: a lean chip path (comp_button.chip_chrome)",
     chip_before, chip_after, {"diff": True}),
    ("switch-row-hit", "Switch: a row-sized target (interact.switch row=)",
     switch_before, switch_after, {}),
    ("tabs-ids-icons", "Tabs: caller ids, icons, even width, accent (interact.tabs)",
     tabs_before, tabs_after, {"w": 420}),
    ("slider-value-box", "Slider: a value box where a track is too short (slider box=)",
     box_before, box_after, {"h": 150}),
    ("menu-scroll", "Menu: a height cap that scrolls (menu.popup / select max_h)",
     menu_before, menu_after, {"h": 760, "frames": 14}),
    ("host-type", "Theme: a host's own faces (draw.host_faces, span read from the file)",
     type_cell, type_cell, {"host_after": True}),
]


def compose(name: str, title: str, before, after, opts, out: Path) -> Path:
    w = opts.get("w", CELL_W)
    h = opts.get("h", CELL_H)
    frames = opts.get("frames", 3)
    rows = []
    themes = ("light", "dark", "hyperspace")
    for th in themes:
        a = shot(th, before, frames, w, h)
        b = shot(th, after, frames, w, h, host_type=opts.get("host_after", False))
        rows.append((th, a, b))
    if opts.get("diff"):
        band = slice(0, 90)                 # the drawing, above the captions (which differ)
        worst = max(int(np.abs(a[band].astype(int) - b[band].astype(int)).max())
                    for _, a, b in rows)
        title += f"   -   before vs after, every theme: max difference {worst} levels"
    pad, head, side = 10, 46, 92
    W = side + 2 * w + 3 * pad
    H = head + len(rows) * (h + pad) + pad + 18
    img = Image.new("RGB", (W, H), (40, 40, 44))
    d = ImageDraw.Draw(img)
    d.text((pad, 10), title, fill=(240, 240, 240))
    d.text((side + pad, head - 16), "BEFORE (what the kit did)", fill=(200, 200, 200))
    d.text((side + 2 * pad + w, head - 16), "AFTER (the addition)", fill=(255, 120, 120))
    for i, (th, a, b) in enumerate(rows):
        y = head + 4 + i * (h + pad)
        d.text((pad, y + h // 2 - 6), th, fill=(220, 220, 220))
        img.paste(Image.fromarray(a), (side + pad, y))
        img.paste(Image.fromarray(b), (side + 2 * pad + w, y))
    path = out / f"{name}.png"
    img.save(path)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", help="one addition's name")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for n, (name, title, before, after, opts) in enumerate(ADDITIONS, 1):
        if a.only and a.only != name:
            continue
        print(compose(f"{n}-{name}", f"{n}. {title}", before, after, opts, a.out))


if __name__ == "__main__":
    main()
