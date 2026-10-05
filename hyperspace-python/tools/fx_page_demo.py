#!/usr/bin/env python3
"""The FX page's chips and which strip is open, shown headless (plan 16 WP2),
and the face target on the page (plan 20 WP2).

Not the app: the registry, the library and the live `FxState` the way the
FX page reads them, on a fresh temp home of its own (`tools/undo_demo.py`
sets `HYPERSPACE_HOME` on import, before anything reads it) — no render
window, no MIDI port, no audio device.

  uv run python tools/fx_page_demo.py            # the transcript → fx-select.txt
  uv run python tools/fx_page_demo.py --shots    # the page as PNGs, from a hidden window
  uv run python tools/fx_page_demo.py --faces    # plan 20 WP2's three PNGs, the same way

The first two land in docs/plans/assets/16-paper-cuts/. The transcript opens an
effect by name, moves it and another through the stack, and loads
presets with different orders: the same effect stays open throughout.
The shots are the FX page with two effects on and another open but off
(fx-chips.png), and an off effect's strip saying why it is not running
(fx-idle.png, plan 16 WP3).

--faces lands in docs/plans/assets/20-fx-dream-looks/: the page with two
effects aimed at the faces and one on the frame, both status rows, the
per face / screen chips and the open strip's target combo
(fx-page-faces.png), the same with Faces off (fx-page-faces-off.png), and
the page with nothing aimed at the faces (fx-page-frame-only.png). Hidden-window renders, not the app on a screen.
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
from hyperspace.fx import FxState
from hyperspace.library import Library
from hyperspace.params import build_registry
from hyperspace.view import ViewState

ASSETS = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets"
OUT = ASSETS / "16-paper-cuts"
OUT20 = ASSETS / "20-fx-dream-looks"
lines: list[str] = []


def say(text: str = "") -> None:
    lines.append(text)
    print(text)


def boot() -> SimpleNamespace:
    """What the FX page needs: the registry over a live FxState, the library."""
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    view = ViewState()
    fx = FxState()
    lib = Library(demo.HOME, period=0.0)
    reg = build_registry(view, control, audio, lib.project, fx=fx)
    lib.attach(reg)
    return SimpleNamespace(chain=chain, control=control, audio=audio, view=view, fx=fx,
                           lib=lib, reg=reg)


def stack(r) -> None:
    """The chips in stack order: ● on, ○ off, [brackets] round the open one."""
    fx, sel = r.fx, r.fx.selected()
    chips = []
    for n in fx.names():
        chip = f"{'●' if fx.values[n]['on'] else '○'} {n}"
        chips.append(f"[{chip}]" if n == sel else f" {chip} ")
    say("    " + " ".join(chips))
    say(f"    open: {sel}   (fx.select reads {r.reg['fx.select'].value}, "
        f"sel_name {fx.sel_name!r})")


def transcript() -> None:
    r = boot()
    fx, reg = r.fx, r.reg
    say("The FX page: which strip is open is a name, not a place in the stack")
    say("=====================================================================")
    say()
    say("at launch — nothing chosen, so the first effect is open")
    stack(r)
    say()
    say('fx.select("kaleido") — what a click on the kaleidoscope\'s name does')
    fx.select("kaleido")
    stack(r)
    on = {n: fx.values[n]["on"] for n in fx.names()}
    say(f"    effects switched by that: {sum(on.values())} (a click on the name never toggles)")
    say()
    was = fx.values["kaleido"]["order"]
    say(f"fx.kaleido.order {was} → 99 — its order slider dragged to the far end")
    for k in range(was, 100):
        reg["fx.kaleido.order"].set_value(k)
        assert fx.selected() == "kaleido"
    stack(r)
    say()
    was = fx.values["huecycle"]["order"]
    say(f"fx.huecycle.order {was} → 0 — another effect moved past it")
    reg["fx.huecycle.order"].set_value(0)
    stack(r)
    say()
    for name in ("mandala", "acid", "noita tripping balls"):
        say(f'preset load: fx "{name}" — lands every fx.*.order')
        missing = r.lib.load("fx", name)
        assert missing == [], missing
        stack(r)
        say()
    say("fx.select ← 0 — a desk row or a test that writes an index still works")
    reg["fx.select"].set(0)
    stack(r)
    say()
    say("fx.glimmer.on toggled — what a click on glimmer's LED does; the open strip stays")
    reg["fx.glimmer.on"].toggle()
    stack(r)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fx-select.txt").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'fx-select.txt'}")


def harness() -> SimpleNamespace:
    """A hidden window at the control size with the Panel on the FX page:
    `draw(n)` runs n frames, `shoot(out, name, what)` reads the window back
    into a PNG, `close()` ends it. `r` is boot()'s."""
    import glfw
    import numpy as np
    from imgui_bundle import imgui, implot
    from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
    from OpenGL import GL
    from PIL import Image

    from hyperspace.app import CONTROL_SIZE
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "fx page shot", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    implot.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)

    r = boot()
    fx, reg = r.fx, r.reg
    panel = Panel(r.control, r.audio, r.view, bank=r.lib.project, registry=reg, library=r.lib)
    panel.renderer = SimpleNamespace(face_error="",
                                     fx=SimpleNamespace(state=fx, error=lambda n: ""))
    reg["ui.page"].set(PAGE_KEYS.index("fx"))

    def draw(n: int = 8) -> None:
        for _ in range(n):
            glfw.poll_events()
            impl.process_inputs()
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            panel.draw(1 / 60, 60.0)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()

    def shoot(out: Path, name: str, what: str) -> None:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        out.mkdir(parents=True, exist_ok=True)
        Image.fromarray(px).save(out / name, optimize=True)
        print(f"wrote {out / name}  — {what}")

    def close() -> None:
        impl.shutdown()
        glfw.terminate()

    return SimpleNamespace(r=r, panel=panel, draw=draw, shoot=shoot, close=close)


def shots() -> None:
    from hyperspace import ui_fx
    h = harness()
    fx, reg, draw = h.r.fx, h.r.reg, h.draw
    # the chips: two effects on, another open (outlined) and off
    reg["fx.warp.on"].set(True)
    reg["fx.tripcolour.on"].set(True)
    fx.select("fractals")
    draw()
    h.shoot(OUT, "fx-chips.png", f"on: {fx.chain()}, open: {fx.selected()} "
                          f"(on={fx.values['fractals']['on']})")
    # plan 16 WP3: an open effect that is off says so, with "turn on" beside
    # the line and its rows dimmed
    fx.select("kaleido")
    draw()
    h.shoot(OUT, "fx-idle.png", f"open: {fx.selected()}, why idle: {ui_fx.why_idle(fx, 'kaleido')}")
    h.close()


def faces() -> None:
    """Plan 20 WP2: the face target on the page."""
    from hyperspace import ui_fx
    from hyperspace.fx import BLENDS, FACES, FRAME
    h = harness()
    fx, reg, draw = h.r.fx, h.r.reg, h.draw
    # nothing aimed at the faces: the page as it was, with the one-line note
    for name in ("plasma", "kaleido", "huecycle"):
        reg[f"fx.{name}.on"].set(True)
    fx.select("kaleido")
    draw()
    h.shoot(OUT20, "fx-page-frame-only.png",
            f"frame: {fx.chain(FRAME)}, faces: {fx.chain(FACES)}, open: {fx.selected()}")
    # two effects aimed at the faces (one on, one off), one more on the
    # faces and running, the rest on the frame; the open strip is a face one
    reg["fx.kaleido.target"].set(FACES)
    reg["fx.zoomblur.target"].set(FACES)
    reg["fx.zoomblur.on"].set(True)
    reg["fx.glimmer.target"].set(FACES)         # aimed at the faces and off: the outline
    reg["fx.kaleido.blend"].set(BLENDS.index("multiply"))   # the blend combo's longest entry
    reg["view.faces"].set(True)
    draw()
    h.shoot(OUT20, "fx-page-faces.png",
            f"frame: {fx.chain(FRAME)}, faces: {fx.chain(FACES)}, open: {fx.selected()}, "
            f"map: {reg['fx.face_map'].text()}")
    # the same with Faces off: the row says so, and the open strip offers "faces on"
    reg["view.faces"].set(False)
    draw()
    h.shoot(OUT20, "fx-page-faces-off.png",
            f"view.faces off, why idle: {ui_fx.why_idle(fx, 'kaleido', h.r.view.faces)}")
    h.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(shots() if "--shots" in args else faces() if "--faces" in args else transcript())
