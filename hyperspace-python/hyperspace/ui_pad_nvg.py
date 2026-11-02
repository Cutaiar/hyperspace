"""The app's pen: the lab's drawings with NanoVG (plan 42's readouts).

`ui_pad_lab` holds the drawings — the browser lab's canvas code ported —
written against a `Pen`. This is the pen that draws them: NanoVG, which
imgui-bundle ships, a vector renderer with what Dear ImGui's draw list
lacks (gradients, feathered edges, tessellation in C), into an offscreen
texture the size of the room in the window's pixels, which the pad window
shows as an image.

  `NvgPen`   every one of `ui_pad_lab.DRAW_CALLS`, made on a NanoVG context
  `Surface`  the context and its framebuffer, made in the control
             window's GL context the first time a drawing asks (one extra
             call, `hello_imgui.init_gl_loader`, lets NanoVG reach GL
             outside imgui-bundle's own runner); kept on the panel

One renderer, no second one behind it: where NanoVG cannot draw — no GL
context (the tests' headless panel), NanoVG would not start (the reason in
`Surface.failed`), or ``HYPERSPACE_NANOVG=0`` — the room says so
(`Surface.why_not`) and Map and Lanes are the views to use. The terminal
is told once which it is (``pad drawings: …``).
"""

from __future__ import annotations

import os
import sys

from . import ui_pad_lab
from .ui_pad_lab import DESIGN_H, DESIGN_W, FONT_K, rgba

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONTS = {"ui": "Inter-Medium.ttf", "bold": "Inter-Bold.ttf", "mono": "JetBrainsMono-SemiBold.ttf",
         "sym": "DejaVuSans.ttf"}


class NvgPen(ui_pad_lab.Pen):
    """`ui_pad_lab.Pen`'s calls on a NanoVG context `vg` (the module `nvg`),
    in the lab's design space (the surface sets the transform). Every one
    of `DRAW_CALLS` is made here; the base keeps the hits."""

    def __init__(self, vg, nvg):
        super().__init__()
        self.vg, self.n = vg, nvg

    @property
    def live(self) -> bool:
        return self.vg is not None

    # ---- paths ----
    def path(self) -> None:
        self.n.begin_path(self.vg)

    def move(self, x, y) -> None:
        self.n.move_to(self.vg, x, y)

    def line(self, x, y) -> None:
        self.n.line_to(self.vg, x, y)

    def bez(self, c1x, c1y, c2x, c2y, x, y) -> None:
        self.n.bezier_to(self.vg, c1x, c1y, c2x, c2y, x, y)

    def quad(self, cx, cy, x, y) -> None:
        self.n.quad_to(self.vg, cx, cy, x, y)

    def close(self) -> None:
        self.n.close_path(self.vg)

    def rr(self, x, y, w, h, r) -> None:
        w = max(0.01, w)
        self.n.begin_path(self.vg)
        self.n.rounded_rect(self.vg, x, y, w, h, max(0.0, min(r, abs(w) / 2, h / 2)))

    def circle(self, cx, cy, r) -> None:
        self.n.begin_path(self.vg)
        self.n.circle(self.vg, cx, cy, r)

    def arc(self, cx, cy, r, a0, a1) -> None:
        """A clockwise arc, as canvas draws one (radians, y down)."""
        self.n.begin_path(self.vg)
        self.n.arc(self.vg, cx, cy, r, a0, a1, self.n.Winding.cw.value)

    def lines(self, *pts) -> None:
        self.n.begin_path(self.vg)
        self.n.move_to(self.vg, *pts[0])
        for q in pts[1:]:
            self.n.line_to(self.vg, *q)

    # ---- paint ----
    def _color(self, color, a: float):
        return self.n.rgba_f(*rgba(color, a))

    def fill(self, color, a: float = 1.0) -> None:
        self.n.fill_color(self.vg, self._color(color, a))
        self.n.fill(self.vg)

    def stroke(self, color, width: float = 1.0, a: float = 1.0, cap: str = "butt") -> None:
        self.n.stroke_color(self.vg, self._color(color, a))
        self.n.stroke_width(self.vg, width)
        self.n.line_cap(self.vg, getattr(self.n.LineCap, cap).value)
        self.n.stroke(self.vg)

    def glow_stroke(self, color, width: float, blur: float, layers: int = 8) -> None:
        """The current path (NanoVG keeps it) stroked wider and fainter, layer
        on layer, then the line itself."""
        for k in range(layers, 0, -1):
            self.stroke(color, width + 2 * blur * k / layers, a=0.55 / layers, cap="round")
        self.stroke(color, width, cap="round")

    def glow_rr(self, x, y, w, h, r, color, blur: float, a: float = 0.85) -> None:
        """A soft glow round a rounded box — a feathered box gradient, the
        way NanoVG draws drop shadows."""
        n, vg = self.n, self.vg
        paint = n.box_gradient(vg, x, y, w, h, r, blur, self._color(color, a),
                               self._color(color, 0.0))
        n.begin_path(vg)
        n.rect(vg, x - blur, y - blur, w + 2 * blur, h + 2 * blur)
        n.fill_paint(vg, paint)
        n.fill(vg)

    def text(self, s: str, x, y, *, size=13, color="text", align="center", weight=500,
             mono=False, a: float = 1.0) -> None:
        if not s:
            return
        n, vg = self.n, self.vg
        n.font_face(vg, "mono" if mono else "bold" if weight >= 650 else "ui")
        n.font_size(vg, size * FONT_K)
        n.fill_color(vg, self._color(color, a))
        h = {"center": n.Align.align_center, "left": n.Align.align_left,
             "right": n.Align.align_right}[align].value
        n.text_align(vg, h | n.Align.align_middle.value)
        n.text(vg, x, y, s)

    def alpha(self, a: float) -> None:
        self.n.global_alpha(self.vg, a)

    def save(self) -> None:
        self.n.save(self.vg)

    def restore(self) -> None:
        self.n.restore(self.vg)

    def translate(self, x, y) -> None:
        self.n.translate(self.vg, x, y)


def _gl_current() -> bool:
    """Is a GL context current on this thread? (GLFW's; asked quietly, as
    GLFW warns when a headless panel asks before it is initialised.)"""
    import warnings
    try:
        import glfw
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return bool(glfw.get_current_context())
    except Exception:  # noqa: BLE001 — GLFW set to raise, or no GLFW: no context
        return False


class Surface:
    """NanoVG's context and its framebuffer, in the control window's GL
    context. `ready()` makes them the first time it is asked, where a GL
    context is current; `failed` says why it could not."""

    def __init__(self):
        self.vg = None
        self.nvg = None
        self.fb = None
        self.fb_size = (0, 0)
        self.failed = ""
        self.said = ""

    def _say(self, words: str) -> None:
        """Which pen draws, on the terminal — once."""
        if words != self.said:
            self.said = words
            print(f"pad drawings: {words}", file=sys.stderr)

    def ready(self) -> bool:
        if self.vg is not None:
            return True
        if self.failed:
            return False
        if os.environ.get("HYPERSPACE_NANOVG", "1") == "0":
            self._say("off (HYPERSPACE_NANOVG=0)")
            return False
        if not _gl_current():
            return False                # no GL context (a headless panel): not now, not failed
        try:
            from imgui_bundle import hello_imgui
            from imgui_bundle import nanovg as nvg
            hello_imgui.init_gl_loader()
            flags = (nvg.nvg_imgui.NvgCreateFlags.antialias.value
                     | nvg.nvg_imgui.NvgCreateFlags.stencil_strokes.value)
            vg = nvg.nvg_imgui.create_nvg_context_hello_imgui(flags)
            for name, file in FONTS.items():
                if nvg.create_font(vg, name, os.path.join(_FONT_DIR, file)) < 0:
                    raise RuntimeError(f"font {file} would not load")
            for face in ("ui", "bold", "mono"):
                nvg.add_fallback_font(vg, face, "sym")       # ✕ ○ □ △ ▲ ◀ …
        except Exception as e:  # noqa: BLE001 — a GL that will not take NanoVG: the room says why
            self.failed = f"{type(e).__name__}: {e}"[:160]
            self._say(f"off (NanoVG would not start: {self.failed})")
            return False
        self.vg, self.nvg = vg, nvg
        self._say("NanoVG")
        return True

    def why_not(self) -> str:
        """Why NanoVG is not drawing, in a few words (after `ready` said no)."""
        if self.failed:
            return f"NanoVG would not start: {self.failed}"
        if os.environ.get("HYPERSPACE_NANOVG", "1") == "0":
            return "NanoVG is off (HYPERSPACE_NANOVG=0)"
        return "no OpenGL here for NanoVG"

    def render(self, view: str, r, st: dict, w_px: int, h_px: int) -> tuple[int, NvgPen]:
        """Draw `view` into the framebuffer (made or remade to w_px × h_px),
        the design space fitted and centred; (texture id, the pen — its
        hits in design space) back."""
        nvg = self.nvg
        if self.fb is None or self.fb_size != (w_px, h_px):
            self.fb = nvg.nvg_imgui.NvgFramebuffer(self.vg, max(1, w_px), max(1, h_px), 0)
            self.fb_size = (w_px, h_px)
        pen = NvgPen(self.vg, nvg)
        raised: list[BaseException] = []

        def draw(vg, width, height):
            # an error here is held and raised after the frame is ended and
            # the framebuffer let go, so the GL state is never left half-way
            try:
                s = min(width / DESIGN_W, height / DESIGN_H)
                nvg.save(vg)
                nvg.translate(vg, (width - DESIGN_W * s) / 2, (height - DESIGN_H * s) / 2)
                nvg.scale(vg, s, s)
                ui_pad_lab.VIEWS[view](pen, r, st)
            except Exception as e:  # noqa: BLE001 — re-raised below
                raised.append(e)
            finally:
                nvg.restore(vg)
        from imgui_bundle import imgui
        nvg.nvg_imgui.render_nvg_to_frame_buffer(self.vg, self.fb, draw,
                                                 imgui.ImVec4(0, 0, 0, 0))
        if raised:
            raise raised[0]
        return self.fb.texture_id, pen


def surface_of(panel) -> Surface:
    """The panel's one surface (kept on the panel: a hot reload of this
    module keeps the GL objects it made)."""
    s = panel.__dict__.get("_pad_nvg")
    if s is None:
        s = panel.__dict__["_pad_nvg"] = Surface()
    return s
