#!/usr/bin/env python3
"""The instance layouts, offscreen, and the VIEW page that picks them (plan 20 WP6).

  uv run python tools/layout_shots.py           # the render grid → inst-layouts.png
  uv run python tools/layout_shots.py --page    # the VIEW page   → view-page-layout.png
  uv run python tools/layout_shots.py --page RING RIPPLE /tmp/ring.png   # another state
  uv run python tools/layout_shots.py --page HEX ORBIT /tmp/d.png --driven   # lanes on the rates

Both land in docs/plans/assets/20-fx-dream-looks/.

The render grid is the real pipeline (render.py) on a standalone context:
one row per layout — GRID, HEX, RING — at 7, 19 and 37 copies, and a last
row with a motion on in each layout (mid-motion, the clock pinned). Each
tile's camera is zoomed to fit its field, and its label says by how much.
An offscreen render, not the rig: it shows what the scene pass puts in the
framebuffer, not what a projector shows.

The page shot is the control panel's VIEW page at the control size, drawn
in a hidden GLFW window (never shown) with seven copies in HEX and ORBIT
on: the layout combo, the motion combo, amp and rate in one row, and the
rotation rates two to a row. `tools/undo_demo.py` is imported first: it
sets HYPERSPACE_HOME to a fresh temp home before anything reads it.
"""

# undo_demo is imported before anything of hyperspace's, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import undo_demo as demo
from PIL import Image, ImageDraw

from hyperspace.params import INST_LAYOUT, INST_MOTION
from hyperspace.render import inst_positions
from hyperspace.view import ViewState

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "plans" / "assets" / "20-fx-dream-looks"
W, H = 420, 420
LABEL = 22
T = 3.1                       # the pinned clock: mid-motion on the last row


def view(n: int, layout: int, motion: int = 0) -> ViewState:
    s = ViewState(shape=3, faces=True, pattern=2, bright=1.4, points=True, lines=True,
                  instances=n, inst_layout=layout, inst_motion=motion, inst_amp=0.35,
                  inst_rate=1.0)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    s.yaw, s.pitch = 0.4, 0.25
    gx, gy = inst_positions(n, layout)
    span = float(max(np.abs(gx).max(), np.abs(gy).max())) + 0.75
    s.zoom = 1.0 / (2 * 0.72 * span)         # the field's extent fills the tile
    return s


def render(ctx, s: ViewState) -> np.ndarray:
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    r.draw(s, W, H, t_now=T)
    img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(H, W, 3)[::-1].copy()
    fbo.release()
    return img


def grid() -> None:
    import moderngl

    ctx = moderngl.create_context(standalone=True)
    rows: list[list[tuple[str, ViewState]]] = []
    for layout, name in enumerate(INST_LAYOUT):
        rows.append([(f"{name} · {n}", view(n, layout)) for n in (7, 19, 37)])
    moving = ((0, 19, 2), (1, 19, 1), (2, 12, 3))      # GRID WAVE, HEX ORBIT, RING RIPPLE
    rows.append([(f"{INST_LAYOUT[lay]} · {n} · {INST_MOTION[m]}", view(n, lay, m))
                 for lay, n, m in moving])
    sheet = Image.new("RGB", (3 * W, len(rows) * (H + LABEL)), "black")
    d = ImageDraw.Draw(sheet)
    for i, row in enumerate(rows):
        for j, (label, s) in enumerate(row):
            img = render(ctx, s)
            assert img.any(), label
            x, y = j * W, i * (H + LABEL)
            sheet.paste(Image.fromarray(img), (x, y + LABEL))
            d.text((x + 6, y + 5), f"{label}   (zoom {s.zoom:.2f})", fill="white")
            print(f"{label:>24}: mean {img.mean():6.2f}  zoom {s.zoom:.3f}")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "inst-layouts.png"
    sheet.save(path, optimize=True)
    print("wrote", path.relative_to(ROOT))


def page(layout: str = "HEX", motion: str = "ORBIT", name: str = "view-page-layout.png",
         driven: bool = False) -> None:
    import glfw
    from imgui_bundle import imgui, implot
    from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
    from OpenGL import GL

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.app import CONTROL_SIZE
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "view page shot", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    implot.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)

    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    v = ViewState()
    lib = Library(demo.HOME, period=0.0)
    reg = build_registry(v, control, audio, lib.project)
    lib.attach(reg)
    panel = Panel(control, audio, v, bank=lib.project, registry=reg, library=lib)
    reg["ui.page"].set(PAGE_KEYS.index("view"))
    reg["view.instances"].set(7)
    reg["view.inst_layout"].set(INST_LAYOUT.index(layout))
    reg["view.inst_motion"].set(INST_MOTION.index(motion))

    room: list[float] = []
    draw_page = Panel._page_view

    def measured(self, dt):
        draw_page(self, dt)
        room.append(imgui.get_content_region_avail().y + imgui.get_style().item_spacing.y)
    Panel._page_view = measured

    for _ in range(8):
        if driven:
            # a lane on every plane rate, as the party presets route them:
            # the cells read `base → effective`
            for k, plane in enumerate(("XY", "XZ", "YZ", "XW", "YW", "ZW")):
                reg[f"rot.rate.{plane}"].modulate(0.05 * (k + 1) * (-1) ** k)
            reg.apply()
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        panel.draw(1 / 60, 60.0)
        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()
    w, h = glfw.get_framebuffer_size(win)
    raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
    px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
    if not px.any():
        raise SystemExit("the hidden window read back black: no picture on this machine")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    Image.fromarray(px).save(path, optimize=True)
    print(f"wrote {path}  — 7 copies, {layout}, {motion}; "
          f"room under the last row {room[-1]:.0f} px (logical)")
    Panel._page_view = draw_page
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--page" in args:
        # optional: a layout and a motion by name, and a file name, to look
        # at another state of the row (`--page RING RIPPLE ring.png`)
        rest = [a for a in args if a not in ("--page", "--driven")]
        sys.exit(page(*rest, driven="--driven" in args))
    sys.exit(grid())
