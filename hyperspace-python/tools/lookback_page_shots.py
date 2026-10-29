#!/usr/bin/env python3
"""The look-back page as PNGs and its label table (plan 20 WP4, WP5).

Not the app: a **hidden** GLFW window at the control size with the panel
drawn over a real `Renderer` on the same GL context, so the thumbnail row
is the row of images the running app draws (the echoes from the atlas
texture, the dream buffer last) and not the one line of text a page gets
with no renderer. The renderer draws a turning tesseract offscreen with
look-back on until eight echoes are captured. There is **no dream
worker**: a stand-in source hands each submitted frame back as "the
dream" and says a canned status line, so the DREAM section is drawn as it
is with a worker attached, but the dream thumbnail is not a dream. A
fresh temp home of its own (`tools/undo_demo.py` sets `HYPERSPACE_HOME`
on import): no MIDI port, no audio device, no tracker.

  uv run python tools/lookback_page_shots.py                  # → lookback-page.png
  uv run python tools/lookback_page_shots.py --name NAME.png  # the same page, another file
  uv run python tools/lookback_page_shots.py --closed --name NAME.png   # the layer menu shut
  uv run python tools/lookback_page_shots.py --speed          # → lookback-speed.png
  uv run python tools/lookback_page_shots.py --labels         # → lookback-labels.txt

All land in docs/plans/assets/20-fx-dream-looks/. The page shot has the
layer menu open and one layer's hover up (`--closed`: shut). `--speed` is the top of
the DREAM section (the status, the layer menu, the speed cell and its
readout) three times: `dream.k` at the slow end, the default and the fast
end, each under a caption this tool draws. `--labels` writes the
table old label → new label → what the knob does: the new labels and the
sentences are read from the registry and the page, the old ones are the
frozen table below (what the page and the registry said before plan 20).
"""

# undo_demo is imported before anything of hyperspace's, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
# before anything loads glfw
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import undo_demo as demo

from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.lookback import LAYERS
from hyperspace.params import build_registry
from hyperspace.view import ViewState

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "20-fx-dream-looks"
RENDER_SIZE = (1280, 820)       # the offscreen scene the echoes are taken from

# what the page and the registry called each param before plan 20 WP4:
# id → (page label, registry label). "—" is a widget that had no label.
OLD = {
    "dream.on": ("Look-back", "Look-back"),
    "dream.echo_mix": ("echo", "Echo mix"),
    "dream.fade": ("fade", "Fade"),
    "dream.echoes": ("Echoes", "Echoes"),
    "dream.gap": ("spacing", "Spacing"),
    "dream.mix": ("dream", "Dream mix"),
    "dream.k": ("blend k", "Blend k"),
    "dream.step": ("step", "Step size"),
    "dream.steps": ("Steps", "Steps"),
    "dream.mask_decay": ("mask", "Mask decay"),
    "dream.jitter": ("Jitter", "Jitter"),
    "dream.octaves": ("—", "Octaves"),
    "dream.layer": ("net", "Layer"),
    "dream.hue": ("hue", "Hue shift"),
    "dream.sat": ("sat", "Saturation"),
    "dream.tint": ("Tint", "Tint"),
    "dream.tint_from": ("from", "Tint from"),
    "dream.tint_hue": ("tint hue", "Tint hue"),
    "dream.tint_sat": ("tint sat", "Tint sat"),
    "dream.darken": ("Darken", "Darken"),
    "dream.contrast": ("Contrast", "Contrast"),
    "dream.occlude": ("Occlude", "Occlude"),
    "dream.res": ("—", "Resolution"),
}


class StandIn:
    """In the dream worker's place: every submitted frame comes back, one
    submit late, as "the dream", and the status line is canned."""

    def __init__(self, reg):
        self.reg = reg
        self.pending = self.done = None

    def buffer(self, shape):
        import numpy as np

        return np.empty(shape, dtype=np.uint8)

    def submit(self, frame, frame_index):
        self.done, self.pending = self.pending, (frame.copy(), frame_index)

    def latest(self):
        return self.done

    def status(self) -> str:
        return f"mps · alias · {LAYERS[int(self.reg['dream.layer'].value)]} fp32 · 11.3 ms · 1 behind"


def boot(renderer=None) -> SimpleNamespace:
    """The registry and library the way the page reads them; with a
    renderer, `dream.*` is its look-back's own state."""
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    view = ViewState()
    lib = Library(demo.HOME, period=0.0)
    kw = {} if renderer is None else {"dream": renderer.lookback.state, "fx": renderer.fx.state}
    reg = build_registry(view, control, audio, lib.project, **kw)
    lib.attach(reg)
    return SimpleNamespace(chain=chain, control=control, audio=audio, view=view, lib=lib, reg=reg)


def labels() -> None:
    from hyperspace import ui_lookback

    r = boot()
    head = ("id", "page: old", "page: new", "registry: old", "registry: new", "reads")
    rows = [head + ("what it does",)]
    for title, ids in {"look-back": ("dream.on",), **ui_lookback.SECTIONS}.items():
        rows.append((f"— {title} —", "", "", "", "", "", ""))
        for pid in ids:
            p = r.reg[pid]
            old_page, old_reg = OLD[pid]
            reads = "on / off" if p.names is None and p.fmt is None else (
                " / ".join(p.names) if p.fmt is None else p.text())
            what = p.tip.split(". ")[0].rstrip(".") + "."       # the tip's first sentence
            rows.append((pid, old_page, ui_lookback.page_label(pid), old_reg, p.label, reads,
                         what))
    widths = [max(len(row[k]) for row in rows) for k in range(len(head))]
    out = ["The look-back page's labels, old → new (plan 20 WP4, WP5)", "",
           "Generated by tools/lookback_page_shots.py --labels. The new labels, the readouts (at",
           "the defaults) and the sentences (each tip's first) are read from the registry",
           "(params.build_registry) and the page (ui_lookback.SECTIONS, page_label); the old",
           "columns are that tool's frozen table of what both said before plan 20.", ""]
    for n, row in enumerate(rows):
        out.append("  ".join(c.ljust(w) for c, w in zip(row, widths)) + "  " + row[-1])
        if n == 0:
            out.append("  ".join("-" * w for w in widths) + "  " + "-" * 12)
    from hyperspace.lookback import LAYER_INFO

    out += ["", "dream.layer's menu (lookback.LAYER_INFO), in its order:"]
    out += [f"  {net:<10} {name:<12} {short}" for name, (net, short, _) in LAYER_INFO.items()]
    OUT.mkdir(parents=True, exist_ok=True)
    text = "\n".join(line.rstrip() for line in out) + "\n"
    (OUT / "lookback-labels.txt").write_text(text)
    print(text)
    print(f"wrote {OUT / 'lookback-labels.txt'}")


SPEED_ROWS_H = 150      # the DREAM title, status, chips and two rows of cells, in points


def shots(name: str, speed: bool = False, closed: bool = False) -> None:
    import glfw
    import moderngl
    import numpy as np
    from imgui_bundle import imgui, implot
    from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
    from OpenGL import GL
    from PIL import Image, ImageDraw, ImageFont

    from hyperspace.app import CONTROL_SIZE
    from hyperspace.graph import Wiring
    from hyperspace.graphmigrate import look_of, wired_wiring
    from hyperspace.render import Renderer
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "look-back page shot", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    implot.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)

    # the renderer shares the window's context, as the app's two windows share one
    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    r = boot(renderer)
    reg, view = r.reg, r.view
    view.shape = 3
    view.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    reg["dream.on"].set(True)
    # plan 36 T3: a bare renderer draws the app's empty frame; the tool's
    # own wiring is today's frame, the look-back on (plan 36 T4: the echoes
    # and the dream, as an old file with `dream.on` drew them)
    renderer.wiring = wired_wiring(Wiring(), look_of({"dream.on": True,
                                                      "dream.mix": reg["dream.mix"].value}))
    renderer.dreamer.source = StandIn(reg)
    scene_tex = ctx.texture(RENDER_SIZE, 4)
    scene_fbo = ctx.framebuffer(color_attachments=[scene_tex])
    panel = Panel(r.control, r.audio, view, renderer=renderer, bank=r.lib.project,
                  registry=reg, library=r.lib)
    reg["ui.page"].set(PAGE_KEYS.index("lookback"))
    clock = [0.0]
    # where the DREAM section is drawn, in window points: (x0, y0, x1) at its title
    dream_at: list[tuple[float, float, float]] = []
    real_section = Panel._section

    def section(self, title, *a, **k):
        if title == "dream":
            pos = imgui.get_cursor_screen_pos()
            dream_at[:] = [(pos.x, pos.y, pos.x + imgui.get_content_region_avail().x)]
        return real_section(self, title, *a, **k)
    Panel._section = section

    def draw(n: int = 8) -> None:
        for _ in range(n):
            # the render window's frame, offscreen
            clock[0] += 1 / 60
            view.ang[3] += 0.03
            scene_fbo.use()
            ctx.viewport = (0, 0, *RENDER_SIZE)
            renderer.draw(view, *RENDER_SIZE, t_now=clock[0])
            # the control window's
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

    def grab() -> Image.Image:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        return Image.fromarray(px)

    def shoot(file: str, what: str) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        grab().save(OUT / file, optimize=True)
        print(f"wrote {OUT / file}  — {what}")

    def speed_sheet() -> None:
        """The top of the DREAM section at three speeds, one under another."""
        k = reg["dream.k"]
        was = k.base
        if not dream_at:
            raise SystemExit("the page drew no DREAM section: nothing to crop")
        scale = glfw.get_framebuffer_size(win)[0] / CONTROL_SIZE[0]
        font = ImageFont.load_default(size=int(15 * scale))
        tiles, said = [], []
        for v, where in ((k.lo, "the slow end"), (0.05, "the default"), (k.hi, "the fast end")):
            k.set_value(v)
            draw()
            x0, y0, x1 = dream_at[0]
            box = [int(c * scale) for c in (x0 - 8, y0 - 6, x1 + 8, y0 + SPEED_ROWS_H)]
            tile = grab().crop(tuple(box))
            cap = Image.new("RGB", (tile.width, int(30 * scale)), (0, 0, 0))
            text = f"dream.k = {v:g}, {where}"      # (the caption face has no ≈)
            ImageDraw.Draw(cap).text((int(8 * scale), int(7 * scale)), text,
                                     fill=(235, 235, 235), font=font)
            tiles += [cap, tile]
            said.append(f"{v:g} → {k.text()}")
        k.set_value(was)
        sheet = Image.new("RGB", (tiles[0].width, sum(t.height for t in tiles)))
        y = 0
        for t in tiles:
            sheet.paste(t, (0, y))
            y += t.height
        OUT.mkdir(parents=True, exist_ok=True)
        sheet.save(OUT / "lookback-speed.png", optimize=True)
        print(f"wrote {OUT / 'lookback-speed.png'}  — {'; '.join(said)}")

    def open_layer_menu(hover: str) -> None:
        """A click on the layer menu, then the mouse on `hover`'s line in
        it, so the picture has the menu open and that layer's hover up."""
        rects: dict[str, tuple] = {}
        real_combo, real_sel = imgui.begin_combo, imgui.selectable

        def combo(label, *a, **k):
            out = real_combo(label, *a, **k)
            if label == "##dream.layer" and not out:
                lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
                rects["menu"] = (lo.x, lo.y, hi.x, hi.y)
            return out

        def sel(label, *a, **k):
            out = real_sel(label, *a, **k)
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            rects[label.split("##", 1)[-1]] = (lo.x, lo.y, hi.x, hi.y)
            return out
        imgui.begin_combo, imgui.selectable = combo, sel
        io = imgui.get_io()
        try:
            draw(2)
            x0, y0, x1, y1 = rects["menu"]
            io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
            draw(1)
            io.add_mouse_button_event(0, True)
            draw(1)
            io.add_mouse_button_event(0, False)
            draw(2)
            x0, y0, x1, y1 = rects[f"layer.{hover}"]
            io.add_mouse_pos_event(x0 + 40, (y0 + y1) / 2)
            draw(4)
        finally:
            imgui.begin_combo, imgui.selectable = real_combo, real_sel

    draw(40)
    lb = renderer.lookback
    what = (f"{len(lb.thumbnails())} echoes at {lb.echo[0]}×{lb.echo[1]}, the stand-in's "
            f"frame {renderer.dreamer.dream_frame} as the dream")
    try:
        if speed:
            speed_sheet()
        elif closed:
            shoot(name, what + ", the layer menu closed")
        else:
            open_layer_menu("conv4_3")
            shoot(name, what + ", the layer menu open, conv4_3's hover up")
    finally:
        Panel._section = real_section
        impl.shutdown()
        glfw.terminate()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--labels" in args:
        sys.exit(labels())
    name = args[args.index("--name") + 1] if "--name" in args else "lookback-page.png"
    sys.exit(shots(name, speed="--speed" in args, closed="--closed" in args))
