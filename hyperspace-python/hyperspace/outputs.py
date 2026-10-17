"""The render outputs, as the renderer sees them (plan 21 WP1).

One frame is drawn per loop; each output — a window on its own screen,
or an offscreen target standing in for one — shows that frame through
its own switches: the scene on or off, the hands on or off, and its own
dim. This module is the pure half of that: what an output asks for
(`Switches`), which pipeline gives it (`route`), where the frame sits in
an output of another shape (`fit`), and the one-frame record the
renderer fills in for an output (`View`, with `Handoff` for an output in
another window's context). `Renderer.draw_outputs` (render.py) does the
drawing. WP3 adds the rig's side: `Slot`, one listed output for the run
(app.py fills it from `[[output.screens]]`), and `Presenter`, which shows
a `Handoff` in another window's context.

Render stack (ARCHITECTURE §3): it only reads. This module imports
moderngl and glsl at most — never app, ui or params — and the
`output.N.*` params (WP4) write `Switches`, which the renderer reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import moderngl

from .glsl import QUAD_VS

MAX_OUTPUTS = 4

# pipeline keys, in run order: the scene through the look-back and the
# effects; the scene with the hands laid on before the effects (WP2); the
# hands alone through the effects (WP2)
SCENE, SCENE_HANDS, HANDS = 0, 1, 2
PIPELINES = (SCENE, SCENE_HANDS, HANDS)
NAMES = {SCENE: "SCENE", SCENE_HANDS: "SCENE+HANDS", HANDS: "HANDS"}


@dataclass
class Switches:
    """What one output shows — what the output.N.* params write (WP4)."""

    scene: bool = True
    hands: bool = True
    through: bool = False      # hands through effects (WP2)
    dim: float = 1.0           # this output's own dim, times the master's
    # plan 23 WP1: this output's picture mirrored as its last step, inside
    # the fit rect — the frame, the hands laid after and the readout alike,
    # so a Pepper's Ghost glass's own mirror is undone (the dim covers the
    # whole rect and needs none). Off, the output is bit-identical
    flip_x: bool = False       # left-right
    flip_y: bool = False       # top-bottom


def route(sw: Switches, fx_active: bool, hands_visible: bool) -> tuple[int | None, bool]:
    """(pipeline key, or None for the ground; hands composited after).

    `hands_visible` is "the ghost hands are on and a hand shows this
    frame" (`Ghost.layer` drew); the hands are *shown* on this output when
    its own hands switch is on too (fork F7).

    | scene | hands shown | through and an effect on | pipeline    | hands after |
    |  on   |    no       |          —               | SCENE       | no          |
    |  on   |    yes      |          no              | SCENE       | yes         |
    |  on   |    yes      |          yes             | SCENE_HANDS | no          |
    |  off  |    no       |          —               | None        | no          |
    |  off  |    yes      |          no              | None        | yes         |
    |  off  |    yes      |          yes             | HANDS       | no          |

    So with no effect on, or no hand shown, the through switch changes
    nothing: every output is SCENE or the ground (WP2; fork F2 makes
    "scene off, hands through" the hands alone through the chain)."""
    shown = bool(sw.hands) and bool(hands_visible)
    through = shown and bool(sw.through) and bool(fx_active)
    if sw.scene:
        return (SCENE_HANDS, False) if through else (SCENE, shown)
    return (HANDS, False) if through else (None, shown)


def capped(size: tuple[int, int], cap: tuple[int, int] | None) -> tuple[int, int]:
    """The frame's size: output 1's framebuffer `size`, shrunk with its
    aspect kept until it fits inside `cap` (w, h), whichever side binds;
    never grown; None is no cap. A 2× HiDPI screen that looks 1920×1080
    is a 3840×2160 framebuffer — under a 1080p cap the scene, the
    look-back, the dream and every effect run at 1920×1080 and each output
    shows the frame scaled (`fit`, linear)."""
    w, h = max(int(size[0]), 1), max(int(size[1]), 1)
    if cap is None:
        return w, h
    k = min(cap[0] / w, cap[1] / h, 1.0)
    return max(1, round(w * k)), max(1, round(h * k))


def fit(src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int, int, int]:
    """The rect (x, y, w, h) in `dst` that shows `src` whole, centred, its
    aspect kept (fork F5: letterbox). Equal sizes give (0, 0, w, h); a
    zero-sized side gives the whole of `dst`."""
    sw, sh = int(src[0]), int(src[1])
    dw, dh = int(dst[0]), int(dst[1])
    if (sw, sh) == (dw, dh) or sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
        return 0, 0, max(dw, 0), max(dh, 0)
    scale = min(dw / sw, dh / sh)
    w = min(dw, max(1, round(sw * scale)))
    h = min(dh, max(1, round(sh * scale)))
    return (dw - w) // 2, (dh - h) // 2, w, h


@dataclass
class Handoff:
    """What `Renderer.draw_outputs` leaves for an output it cannot draw
    itself — one in another window's context (`View.presenter`, WP3). Every
    texture belongs to the renderer's context (a share group shares
    textures, not framebuffers or vertex arrays); WP3's presenter wraps
    each GL name with `ctx.external_texture` and, in its own context, in
    this order:

    1. clears its framebuffer to (0, 0, 0, `bg_alpha`);
    2. draws `frame` (RGBA8 or half float, below; `frame_size`, premultiplied, LINEAR) into
       `rect` (in its framebuffer, the view's `viewport` included) — 1:1 when `rect`'s size is `frame_size`, else scaled; with
       `bg_alpha` 1 it writes alpha 1. `frame` None: the ground only;
    3. lays `hands` (the hands' layer, premultiplied, frame-sized) over the
       same `rect` at `alpha`: colour ONE / ONE_MINUS_SRC_ALPHA, and alpha
       ZERO / ONE on an opaque ground (`bg_alpha` 1) — `Ghost.composite`'s
       blend; with `blend` "add" (plan 26 A3) colour ONE / ONE instead, and
       alpha ONE / ONE_MINUS_SRC_ALPHA on a see-through ground. None: no
       hands after the effects on this output;
    4. lays `readout` (the guide and the tethers' labels when they are a
       layer of their own, WP2 — on every output that shows the hands,
       over or through) into `rect` the same way. None: nothing;
    5. multiplies the whole framebuffer by `factor` when it is under 1
       (`Renderer.dim_pass`'s blend: colour only on an opaque ground,
       colour and alpha otherwise).

    The textures are valid until the next `draw_outputs`; the renderer's
    context must be flushed (`glFlush`) before the presenter's samples
    them (plan §1: otherwise it sees last frame's).

    Plan 30 D1: `frame` or `hands` may be a half-float texture of the
    effects' pool rather than RGBA8 — an output's frame through an effect
    placed into it, the hands' layer through one placed after the hands.
    The presenter wraps every name as "f1" (`Presenter._ext`); that
    declares the wrapper's dtype only, and a shader samples the texture
    by its name whatever its real format, so the picture is right."""

    frame: moderngl.Texture | None
    frame_size: tuple[int, int]
    rect: tuple[int, int, int, int]
    hands: moderngl.Texture | None = None
    readout: moderngl.Texture | None = None
    alpha: float = 1.0
    factor: float = 1.0
    bg_alpha: float = 1.0
    flip: tuple[bool, bool] = (False, False)   # plan 23 WP1: steps 2–4 mirrored in `rect`
    blend: str = "over"                        # plan 26 A3: step 3's blend, "over" or "add"

    @staticmethod
    def name(tex: moderngl.Texture | None) -> int | None:
        """A texture's GL name for `ctx.external_texture`, or None."""
        return None if tex is None else int(tex.glo)


@dataclass
class View:
    """One output, for one frame. `target` is a framebuffer on the
    renderer's context (the first output's window, or an offscreen
    stand-in); `presenter` an output in another window's context (WP3),
    which `draw_outputs` leaves a `handoff` for. `viewport` is the rect of
    `target` (or of the presenter's framebuffer) to draw (None: (0, 0) and
    `size`).

    `bg_alpha` is this output's own ground: its bars, its clear when it
    shows no pipeline, and whether its composites and dim keep alpha. The
    frame itself — the scene's clear, the effect chain — is drawn on
    `Renderer.bg_alpha`, once for every output: overlay is the first
    output's only (plan 21 §4), so an output's ground can make the frame
    opaque on it (alpha forced to 1) but never see-through."""

    switches: Switches
    size: tuple[int, int]                       # its framebuffer, px
    target: moderngl.Framebuffer | None = None  # on the renderer's context
    presenter: Any = None                       # WP3: another window's context
    bg_alpha: float = 1.0                       # this output's ground
    error: str = ""                             # set by draw_outputs, never raised
    viewport: tuple[int, int, int, int] | None = None
    handoff: Handoff | None = None              # set by draw_outputs for a presenter
    exc: BaseException | None = field(default=None, repr=False)   # what set `error`

    @property
    def rect(self) -> tuple[int, int, int, int]:
        if self.viewport is not None:
            return tuple(int(v) for v in self.viewport)
        return 0, 0, int(self.size[0]), int(self.size[1])


# ---------------------------------------------------------------- WP3: the list

@dataclass
class Slot:
    """One output the config lists (`[[output.screens]]`, or the one
    `[output]` window when there is no list), for the whole run: its place
    `n` (1-based — `output.2.*` is always the second entry, opened or
    not), its name, its switches (the config's launch values; the
    output.N.* params write them, WP4), and its window — or, for a later
    output whose screen is not connected, `missing`, the reason it was not
    opened (fork F9). `output` is its `overlay.Output`, `presenter` its
    `Presenter` (outputs after the first), `error` the last present that
    raised ("" once one succeeds), `size` its framebuffer at the last frame.
    The app fills it; the renderer never sees it, only the `View` built
    from it each frame."""

    n: int
    name: str = ""
    switches: Switches = field(default_factory=Switches)
    monitor: int = -1
    fullscreen: bool = False
    win: Any = None
    missing: str = ""
    output: Any = None
    presenter: Any = None
    error: str = ""
    size: tuple[int, int] = (0, 0)

    @property
    def label(self) -> str:
        """"output 2 (projector)", or "output 2" with no name."""
        return f"output {self.n} ({self.name})" if self.name else f"output {self.n}"

    @property
    def opened(self) -> bool:
        return self.win is not None


# a frame texture or a layer into a rect of a presenter's framebuffer:
# 1:1 by texelFetch (the renderer's SHOW_FS) or scaled by the sampler,
# times `u_k` (1 for the frame, ghost.alpha for a layer); on an opaque
# ground the frame writes alpha 1
PRESENT_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform int u_scaled;
uniform ivec2 u_origin;      // the rect's origin (gl_FragCoord is window-relative)
uniform float u_k;
uniform int u_opaque;
uniform ivec2 u_flip;        // plan 23 WP1: mirror x / y inside the rect (0 0: as drawn)
out vec4 f_color;
void main() {
    vec4 c;
    if (u_scaled != 0) {
        vec2 uv = v_uv;
        if (u_flip.x != 0) uv.x = 1.0 - uv.x;
        if (u_flip.y != 0) uv.y = 1.0 - uv.y;
        c = texture(u_src, uv);
    } else {
        ivec2 q = ivec2(gl_FragCoord.xy) - u_origin;
        ivec2 n = textureSize(u_src, 0);
        if (u_flip.x != 0) q.x = n.x - 1 - q.x;
        if (u_flip.y != 0) q.y = n.y - 1 - q.y;
        c = texelFetch(u_src, q, 0);
    }
    c *= u_k;
    if (u_opaque != 0) c.a = 1.0;
    f_color = c;
}
"""

# the dim: blending only (render.DIM_FS, `Renderer.dim_pass`'s blend)
PRESENT_DIM_FS = """
#version 330
uniform float u_factor;
out vec4 f_color;
void main() { f_color = vec4(0.0, 0.0, 0.0, u_factor); }
"""


class Presenter:
    """One output after the first (plan 21 WP3): a moderngl handle on that
    window's context and its own programs and vertex arrays — a share
    group shares textures and programs, never framebuffers or vertex
    arrays, so the renderer's cannot draw here (§1 row 1).

    `present(handoff, size)` follows `Handoff`'s five steps in this
    context: the ground, the frame into its rect, the hands, the readout,
    the dim. The handoff's textures belong to the renderer's context and
    are wrapped by GL name (`ctx.external_texture`); the caller has flushed
    that context first. Builds nothing until the first `present`, which
    runs with this context current; `on_reload` only marks the programs
    stale (a reload runs in whatever context is current), so the next
    `present` rebuilds them here. Leaves this context's window
    framebuffer bound, a raise included."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._prog = self._vao = self._dim = self._dim_vao = None
        self._ext: dict[tuple[int, tuple[int, int]], moderngl.Texture] = {}
        self._stale = False
        self.presented = 0

    def _build(self) -> None:
        if getattr(self, "_stale", False):
            self._drop()
            self._stale = False
        if self._prog is not None:
            return
        ctx, made = self.ctx, []
        try:
            prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=PRESENT_FS)
            made.append(prog)
            vao = ctx.vertex_array(prog, [])
            made.append(vao)
            dim = ctx.program(vertex_shader=QUAD_VS, fragment_shader=PRESENT_DIM_FS)
            made.append(dim)
            dim_vao = ctx.vertex_array(dim, [])
        except Exception:
            for res in made:
                res.release()
            raise
        self._prog, self._vao, self._dim, self._dim_vao = prog, vao, dim, dim_vao

    def _wrap(self, tex) -> moderngl.Texture:
        """The renderer's texture as this context sees it, by GL name."""
        key = (int(Handoff.name(tex)), tuple(int(v) for v in tex.size))
        have = self._ext.get(key)
        if have is None:
            if len(self._ext) > 16:      # names of textures long gone
                self._ext.clear()
            have = self._ext[key] = self.ctx.external_texture(key[0], key[1], 4, 0, "f1")
        return have

    def present(self, ho: Handoff, size: tuple[int, int], target=None) -> None:
        """Draw `ho` into this window's framebuffer (`target`: another
        framebuffer on this context, for the tests) of `size` px."""
        ctx = self.ctx
        fb = target if target is not None else ctx.screen
        full = (0, 0, int(size[0]), int(size[1]))
        try:
            self._build()
            fb.use()
            ctx.viewport = full
            ctx.clear(0.0, 0.0, 0.0, float(ho.bg_alpha))                         # 1
            opaque = ho.bg_alpha >= 1.0
            prog, vao = self._prog, self._vao
            prog["u_src"].value = 0
            fl = tuple(int(bool(v)) for v in getattr(ho, "flip", (False, False)))
            prog["u_flip"].value = fl                    # steps 2–4 alike; 5 covers it all
            rect = tuple(int(v) for v in ho.rect)
            if ho.frame is not None and rect[2] > 0 and rect[3] > 0:            # 2
                ctx.viewport = rect
                ctx.disable(moderngl.BLEND)
                self._wrap(ho.frame).use(location=0)
                prog["u_scaled"].value = int(tuple(rect[2:]) != tuple(ho.frame_size))
                prog["u_origin"].value = rect[:2]
                prog["u_k"].value = 1.0
                prog["u_opaque"].value = int(opaque)
                vao.render(moderngl.TRIANGLES, vertices=3)
            add = getattr(ho, "blend", "over") == "add"
            for layer, plus in ((ho.hands, add), (ho.readout, False)):          # 3, 4
                if layer is None or rect[2] <= 0 or rect[3] <= 0:
                    continue
                ctx.viewport = rect
                ctx.enable(moderngl.BLEND)
                rgb = moderngl.ONE if plus else moderngl.ONE_MINUS_SRC_ALPHA
                ctx.blend_func = ((moderngl.ONE, rgb, moderngl.ZERO, moderngl.ONE) if opaque else
                                  (moderngl.ONE, rgb, moderngl.ONE,
                                   moderngl.ONE_MINUS_SRC_ALPHA))
                self._wrap(layer).use(location=0)
                prog["u_scaled"].value = 1          # as Ghost.composite samples it
                prog["u_origin"].value = rect[:2]
                prog["u_k"].value = float(ho.alpha)
                prog["u_opaque"].value = 0
                vao.render(moderngl.TRIANGLES, vertices=3)
            factor = min(max(float(ho.factor), 0.0), 1.0)
            if factor < 1.0:                                                    # 5
                ctx.viewport = full
                ctx.enable(moderngl.BLEND)
                ctx.blend_func = (moderngl.ZERO, moderngl.SRC_ALPHA, moderngl.ZERO,
                                  moderngl.ONE if opaque else moderngl.SRC_ALPHA)
                self._dim["u_factor"].value = factor
                self._dim_vao.render(moderngl.TRIANGLES, vertices=3)
            self.presented += 1
        finally:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            fb.use()
            ctx.viewport = full

    def on_reload(self) -> None:
        """Hot reload: rebuild at the next `present`, in this context."""
        self._stale = True

    def _drop(self) -> None:
        for res in (self._dim_vao, self._dim, self._vao, self._prog):
            if res is not None:
                try:
                    res.release()
                except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                    pass
        self._prog = self._vao = self._dim = self._dim_vao = None
        self._ext = {}

    def release(self) -> None:
        """Free the programs and arrays; call with this context current."""
        self._drop()
