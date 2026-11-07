"""The poi's guide (plan 47, the poi): the handle, the string and the
weight drawn over each output, so the performer sees what the shape is
swinging on.

An operator's guide, as the hands' readout is: drawn once a frame into
its own layer (with depth, so the handle and the string occlude each other
right, and multisampled) and laid over each output after the hands, never
through the effects or into the look-back. An output's hands switch
(`output.N.hands`) mutes it with the hands; `poi.guide` turns it off.
Nothing draws while the poi is off or has not yet written the pan.

**Where things are**, in the world the shape is drawn in (y up; the eye at
`eye.distance` on +z, `geometry.eye_matrix`):

- the poi's own space (`PoiState`: the wrist at its origin) sits on the
  pan's home (`pan_home`, x right and y down, so the world's y is −home.y);
- the **handle**: a tube from the wrist to the tip, a ball on each end;
- the **weight**: a marker on the shape's centre as drawn — the live pan,
  `(pan.x, −pan.y, 0)`, so it never parts from the shape — sized by the
  depth zoom the poi applies (zoom / home zoom), as the shape is;
- the **string**: a tube from the tip to the marker, bright while taut and
  dim while slack.

`rows` is the pure part (no GL), tested on its own; `PoiGuide` draws them
with the hands' `Geometry` (ghost.py: shaded spheres and tubes), and, knowing
the output's size and the eye, tells the poi the box it may swing in
(`PoiState.box`, `poi.box_for`), once a frame.
"""

from __future__ import annotations

import math

import moderngl
import numpy as np

from . import poi
from .geometry import EYE_DISTANCE, EYE_FOV, eye_matrix
from .ghost import COMPOSITE_FS, SAMPLES, Geometry
from .glsl import QUAD_VS

HANDLE_COL = (0.82, 0.84, 0.88)          # the handle: the Joy-Con's grey
TIP_COL = (0.42, 0.70, 1.0)              # the tip the string hangs from
WEIGHT_COL = (1.0, 43 / 255, 43 / 255)   # the panel's one accent (view.RED)
TAUT_COL = (1.0, 1.0, 1.0)
SLACK_COL = (0.55, 0.55, 0.6)
HANDLE_R = 0.035                         # world units: the shape's radius is 1
WRIST_R = 0.05
TIP_R = 0.06
STRING_R = 0.012
WEIGHT_R = 0.09
ALPHA = 0.9                              # the layer's opacity over the picture


def rows(state, pan, zoom: float) -> tuple[list, list] | None:
    """The guide's (sphere rows, tube rows) in the world — each sphere
    ``(x, y, z, r, R, G, B, A)``, each tube ``(ax, ay, az, bx, by, bz, r, R,
    G, B, A)``, as `Geometry.draw` takes them — or None when nothing
    shows: the poi off, the guide off, or no home yet (the poi has not
    written the pan). `pan` and `zoom` are the shape's as drawn
    (`ViewState.pan`, `.zoom`)."""
    if (state is None or not getattr(state, "on", False)
            or not getattr(state, "guide", True) or state.pan_home is None):
        return None
    hx, hy = float(state.pan_home[0]), -float(state.pan_home[1])

    def world(p):
        return (hx + float(p[0]), hy + float(p[1]), float(p[2]))

    wrist, tip = world(state.wrist), world(state.tip())
    weight = (float(pan[0]), -float(pan[1]), 0.0)
    home_zoom = state.zoom_home if state.zoom_home else 1.0
    size = max(0.25, min(4.0, float(zoom) / float(home_zoom)))
    taut = math.dist(state.ball, state.tip()) > state.length * 0.999
    string = TAUT_COL if taut else SLACK_COL
    spheres = [(*wrist, WRIST_R, *HANDLE_COL, 1.0),
               (*tip, TIP_R, *TIP_COL, 1.0),
               (*weight, WEIGHT_R * size, *WEIGHT_COL, 1.0)]
    tubes = [(*wrist, *tip, HANDLE_R, *HANDLE_COL, 1.0),
             (*tip, *weight, STRING_R, *string, 1.0)]
    return spheres, tubes


class PoiGuide:
    """The guide's layer: `layer(size, view, state)` once a frame (False
    when nothing shows), `lay(target, rect, opaque, flip)` onto each
    output. Built on first use; a driver that refuses a piece says why on
    `error` and the guide stays off — the frame goes on without it."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.geometry: Geometry | None = None
        self._comp = self._vao = None
        self.size = (0, 0)
        self._tex = self._fbo = self._msaa = None
        self._res: list = []
        self.shown = False
        self.error = ""
        self._failed = False

    def _build(self) -> bool:
        if self._failed:
            return False
        if self.geometry is not None:
            return True
        made: list = []
        try:
            geo = Geometry(self.ctx)
            made.append(geo)
            comp = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=COMPOSITE_FS)
            made.append(comp)
            vao = self.ctx.vertex_array(comp, [])
        except Exception as e:  # noqa: BLE001 — the guide must not take the frame down
            for r in made:
                r.release()
            self.error = f"poi guide: {type(e).__name__}: {e}"[:160]
            self._failed = True
            return False
        self.geometry, self._comp, self._vao = geo, comp, vao
        return True

    def _ensure(self, size: tuple[int, int]) -> bool:
        if size == self.size and self._fbo is not None:
            return True
        self.release_targets()
        ctx = self.ctx
        made: list = []
        try:
            tex = ctx.texture(size, 4)
            made.append(tex)
            tex.repeat_x = tex.repeat_y = False
            n = min(SAMPLES, int(getattr(ctx, "max_samples", 0) or 0))
            if n > 1:
                rb = ctx.renderbuffer(size, 4, samples=n)
                made.append(rb)
                depth = ctx.depth_renderbuffer(size, samples=n)
                made.append(depth)
                msaa = ctx.framebuffer(color_attachments=[rb], depth_attachment=depth)
                made.append(msaa)
                fbo = ctx.framebuffer(color_attachments=[tex])
                made.append(fbo)
            else:
                depth = ctx.depth_renderbuffer(size)
                made.append(depth)
                msaa = None
                fbo = ctx.framebuffer(color_attachments=[tex], depth_attachment=depth)
                made.append(fbo)
        except Exception as e:  # noqa: BLE001
            for r in reversed(made):
                r.release()
            self.error = f"poi guide: {type(e).__name__}: {e}"[:160]
            return False
        self._tex, self._fbo, self._msaa, self._res, self.size = tex, fbo, msaa, made, size
        return True

    def release_targets(self) -> None:
        for r in reversed(self._res):
            r.release()
        self._res = []
        self._tex = self._fbo = self._msaa = None
        self.size = (0, 0)

    def release(self) -> None:
        self.release_targets()
        for r in (self._vao, self._comp):
            if r is not None:
                r.release()
        if self.geometry is not None:
            self.geometry.release()
        self.geometry = self._comp = self._vao = None

    def layer(self, size: tuple[int, int], view, state) -> bool:
        """Draw the guide at `size` (the frame's) through the shape's eye
        (`view.eye_fov`, `.eye_distance`); False — no GL touched — when
        nothing shows. Leaves blending on and the depth test off, and its
        own framebuffer bound: the caller binds its target next."""
        self.shown = False
        w, h = max(int(size[0]), 1), max(int(size[1]), 1)
        fov = float(getattr(view, "eye_fov", EYE_FOV))
        distance = float(getattr(view, "eye_distance", EYE_DISTANCE))
        if state is not None and hasattr(state, "box"):
            # the box the poi holds the hand and the weight in: what this
            # output shows (poi.box_for), set whether or not the guide draws
            state.box = poi.box_for(w, h, fov, distance)
        got = rows(state, getattr(view, "pan", (0.0, 0.0)), getattr(view, "zoom", 1.0))
        if got is None:
            return False
        if not self._build() or not self._ensure((w, h)):
            return False
        ctx = self.ctx
        vp = eye_matrix(w, h, fov, distance)
        eye = np.array([0.0, 0.0, distance])
        draw = self._msaa if self._msaa is not None else self._fbo
        try:
            draw.use()
            ctx.viewport = (0, 0, w, h)
            ctx.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
            ctx.disable(moderngl.BLEND)
            ctx.enable(moderngl.DEPTH_TEST)
            spheres, tubes = got
            self.geometry.draw([None], vp, eye, None, [(spheres, tubes)])
            if self._msaa is not None:
                ctx.copy_framebuffer(self._fbo, self._msaa)
        finally:
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.shown = True
        return True

    def lay(self, target, vp, opaque: bool = True,
            flip: tuple[bool, bool] = (False, False)) -> bool:
        """The layer over `target`'s rect `vp`, premultiplied, at `ALPHA`;
        on an opaque ground the target's alpha is left as it is (as the
        hands' composite). Leaves `target` bound with `vp`. False when
        `layer` drew nothing this frame."""
        if not self.shown or self._tex is None or self._comp is None:
            return False
        ctx = self.ctx
        try:
            target.use()
            ctx.viewport = tuple(vp)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = ((moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ZERO,
                               moderngl.ONE) if opaque else
                              (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ONE,
                               moderngl.ONE_MINUS_SRC_ALPHA))
            self._tex.use(location=0)
            self._comp["u_hands"].value = 0
            self._comp["u_alpha"].value = ALPHA
            self._comp["u_flip"].value = (int(bool(flip[0])), int(bool(flip[1])))
            self._vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            target.use()
            ctx.viewport = tuple(vp)
        return True
