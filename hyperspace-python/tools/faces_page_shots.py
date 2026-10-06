#!/usr/bin/env python3
"""The FACES page (plan 22 B2) as PNGs.

Not the app: a **hidden** GLFW window at the control size, with the panel
drawn over a real `Renderer` on the same GL context, so the pattern chips'
swatches are the renderer's own (`Renderer.want_swatches`) and not the
placeholder discs a headless page draws. The renderer draws a turning
tesseract offscreen each frame; the faces page is open. A fresh temp home
of its own (`tools/undo_demo.py` sets `HYPERSPACE_HOME` on import): no
MIDI port, no audio device, no tracker. A Router over an empty table
stands in for the app's, so the "+ source" offers show; and three
inputs get routes in b2-hex.png (an analyzer lane is not live here, so
the lane routes read as not moving; an LFO route rides its input, and its
slider shows base → effective).

  uv run python tools/faces_page_shots.py

writes, into docs/plans/assets/22-face-patterns/:

  b2-rings.png      RINGS, nothing driven: the offers
  b2-hex.png        HEX with four inputs driven and one off neutral
  b2-flat.png       FLAT: its note and the dimmed rows
  b2-hover.png      CAUSTIC with a mode chip's hover up (its one line)
"""

# undo_demo is imported before anything of hyperspace's, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import undo_demo as demo

from hyperspace import lfo, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.params import build_registry
from hyperspace.patterns import MODES
from hyperspace.routing import Binding, Bindings, Macro, Router, Sub
from hyperspace.view import ViewState

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "22-face-patterns"
RENDER_SIZE = (960, 640)


def boot(renderer) -> SimpleNamespace:
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    view = ViewState()
    lib = Library(demo.HOME, period=0.0)
    reg = build_registry(view, control, audio, lib.project, dream=renderer.lookback.state,
                         fx=renderer.fx.state)
    t = SimpleNamespace(t=0.0)
    clock = tempo.Clock(now=lambda: t.t)
    lfos = lfo.LFOs(seed=1)
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    lib.attach(reg)
    return SimpleNamespace(chain=chain, control=control, audio=audio, view=view, lib=lib,
                           reg=reg, lfos=lfos, clock=clock, t=t)


def main() -> int:
    import glfw
    import moderngl
    import numpy as np
    from imgui_bundle import imgui, implot
    from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
    from OpenGL import GL
    from PIL import Image

    from hyperspace.app import CONTROL_SIZE
    from hyperspace.render import Renderer
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "faces page shot", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    implot.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)

    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    r = boot(renderer)
    reg, view = r.reg, r.view
    view.shape = 3
    view.faces = True
    view.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    scene_fbo = ctx.framebuffer(color_attachments=[ctx.texture(RENDER_SIZE, 4)])
    panel = Panel(r.control, r.audio, view, renderer=renderer, bank=r.lib.project,
                  registry=reg, library=r.lib)
    router = panel.router = Router(reg, Bindings([]))
    router.labels["lane"] = list(r.chain.band_names)   # as the audio engine publishes them
    panel.lfos = r.lfos
    reg["ui.page"].set(PAGE_KEYS.index("faces"))
    clock = [3.0]
    rects: dict[str, tuple] = {}
    real_inv = imgui.invisible_button

    def inv(label, *a, **k):
        out = real_inv(label, *a, **k)
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        rects[label.split("##", 1)[-1]] = (lo.x, lo.y, hi.x, hi.y)
        return out
    imgui.invisible_button = inv

    def draw(n: int = 24) -> None:
        for _ in range(n):
            clock[0] += 1 / 60
            r.t.t = clock[0]
            r.lfos.step(1 / 60, clock[0], r.clock)
            r.lfos.publish(router)
            router.modulate()
            reg.apply()
            view.ang[3] += 0.01
            scene_fbo.use()
            ctx.viewport = (0, 0, *RENDER_SIZE)
            renderer.draw(view, *RENDER_SIZE, t_now=clock[0])
            ctx.screen.use()
            glfw.poll_events()
            impl.process_inputs()
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            panel.draw(1 / 60, 60.0)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()

    def shoot(file: str, what: str) -> None:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        OUT.mkdir(parents=True, exist_ok=True)
        # the panel's column only: the desk diagram left of it is not this page
        x0 = int(panel._panel_x * w / CONTROL_SIZE[0]) - 8
        Image.fromarray(px[:, max(x0, 0):]).save(OUT / file, optimize=True)
        print(f"wrote {OUT / file}  — {what}")

    try:
        reg["view.pattern"].set(1)
        draw(40)
        shoot("b2-rings.png", "RINGS, nothing driven: each row offers the convention's source")

        reg["view.pattern"].set(MODES.index(next(m for m in MODES if m.name == "HEX")))
        for b in (Binding("lane:0", "pattern.mod.0", "push", 0.5),
                  Binding("lane:1", "pattern.mod.1", "push", 0.5),
                  Binding("lfo:0", "pattern.mod.6", "push", 0.8)):
            router.table.add(b)
        router.table.macros = {"macro.2": Macro("wash", [Sub(depth=("lfo:0", "pattern.mod.6"))]),
                               "macro.4": Macro("", [Sub(base="pattern.mod.7", lo=0.0, hi=2.6)])}
        reg["macro.2"].set_value(1.0) if "macro.2" in reg else None
        reg["pattern.mod.5"].set_value(1.8)
        draw(40)
        shoot("b2-hex.png", "HEX: SCALE and GLOW on lanes, HUE on LFO 1 × macro, SPREAD's "
                            "base a macro's, SHARP off neutral")

        reg["view.pattern"].set(0)
        draw(30)
        shoot("b2-flat.png", "FLAT: its note, the rows dimmed")

        caustic = next(k for k, m in enumerate(MODES) if m.name == "CAUSTIC")
        reg["view.pattern"].set(caustic)
        draw(30)
        io = imgui.get_io()
        x0, y0, x1, y1 = rects[f"mode.{MODES.index(next(m for m in MODES if m.name == 'EMBER'))}"]
        io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        draw(20)
        shoot("b2-hover.png", "CAUSTIC on show, EMBER's chip hovered: its one line")
    finally:
        imgui.invisible_button = real_inv
        impl.shutdown()
        glfw.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
