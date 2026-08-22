"""moderngl renderer — port of the draw() pipeline of hyperspace.html.

The transform runs on the CPU through geometry.project(), the exact code the
parity tests proved against the golden traces; the GPU only rasterises. At
≤600 vertices / ≤1200 edges per shape the per-frame numpy cost is nothing,
and reusing the proven path is what makes "visually indistinguishable"
achievable by construction.

Blending decision (plan 02 task 2): alpha-over in painter order, not
additive. The additive suggestion existed to avoid a CPU depth sort, but the
CPU already computes every edge depth per frame, so the argsort is free and
alpha-over + sort reproduces the reference compositing exactly.

Edges are screen-space quads, not GL lines: core-profile macOS caps line
width at 1 px, and the first comparison shots showed the near-edge weight
hierarchy (width 0.5–2 px scaled by depth and brightness) is a visible part
of the look. Widths below 1 px fold into alpha, the standard thin-line
trick, so far edges render correctly without MSAA.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import moderngl
import numpy as np

from .geometry import RATE, face_triangles, geom, project

BG = (0.0, 0.0, 0.0)
RED = (1.0, 43 / 255, 43 / 255)

LINE_VS = """
#version 330
in vec2 in_pos;      // pixel coordinates, logical space
in float in_alpha;
uniform vec2 u_size; // logical viewport size
out float v_alpha;
void main() {
    gl_Position = vec4(2.0 * in_pos.x / u_size.x - 1.0,
                       1.0 - 2.0 * in_pos.y / u_size.y, 0.0, 1.0);
    v_alpha = in_alpha;
}
"""

LINE_FS = """
#version 330
in float v_alpha;
out vec4 f_color;
void main() { f_color = vec4(1.0, 1.0, 1.0, v_alpha); }
"""

POINT_VS = """
#version 330
in vec2 in_pos;
in float in_size;    // diameter in framebuffer pixels
in float in_alpha;
uniform vec2 u_size;
out float v_alpha;
void main() {
    gl_Position = vec4(2.0 * in_pos.x / u_size.x - 1.0,
                       1.0 - 2.0 * in_pos.y / u_size.y, 0.0, 1.0);
    gl_PointSize = in_size;
    v_alpha = in_alpha;
}
"""

POINT_FS = """
#version 330
in float v_alpha;
out vec4 f_color;
uniform vec3 u_color;
void main() {
    vec2 d = gl_PointCoord * 2.0 - 1.0;
    float a = v_alpha * (1.0 - smoothstep(0.8, 1.0, length(d)));
    if (a <= 0.0) discard;
    f_color = vec4(u_color, a);
}
"""


def clamp(x, a, b):
    return a if x < a else min(x, b)


@dataclass
class ViewState:
    """Mirror of the reference's S object (render-relevant fields)."""

    shape: int = 3
    speed: float = 0.30
    depth4: float = 2.6
    bright: float = 1.0
    points: bool = True
    playing: bool = True
    planes: list[bool] = field(default_factory=lambda: [False, False, True, True, False, False])
    ang: list[float] = field(default_factory=lambda: [0.0] * 6)
    yaw: float = 0.0
    pitch: float = 0.0
    faces: bool = False          # translucent face fills under the wireframe
    zoom: float = 1.0            # camera magnification about the view centre
    pan: list[float] = field(default_factory=lambda: [0.0, 0.0])  # logical px
    instances: int = 1           # synchronized copies in a centred grid

    def integrate(self, dt: float, planedrive=None) -> None:
        """The frame() angle update: ang[p] += dt·speed·RATE[p]·drive."""
        if not self.playing:
            return
        for p in range(6):
            if self.planes[p]:
                drive = 1.0 if planedrive is None else planedrive[p]
                self.ang[p] += dt * self.speed * RATE[p] * drive


class Renderer:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._lines = ctx.program(vertex_shader=LINE_VS, fragment_shader=LINE_FS)
        self._points = ctx.program(vertex_shader=POINT_VS, fragment_shader=POINT_FS)
        self._points["u_color"].value = RED
        self._lbuf = ctx.buffer(reserve=1200 * 2 * 3 * 4, dynamic=True)
        self._pbuf = ctx.buffer(reserve=600 * 4 * 4, dynamic=True)
        self._fbuf = ctx.buffer(reserve=2160 * 3 * 3 * 4, dynamic=True)
        self._lvao = ctx.vertex_array(self._lines, [(self._lbuf, "2f 1f", "in_pos", "in_alpha")])
        self._fvao = ctx.vertex_array(self._lines, [(self._fbuf, "2f 1f", "in_pos", "in_alpha")])
        self._pvao = ctx.vertex_array(
            self._points, [(self._pbuf, "2f 1f 1f", "in_pos", "in_size", "in_alpha")]
        )
        ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def draw(self, s: ViewState, w: int, h: int, dpr: float = 1.0) -> None:
        """One frame at logical size (w, h); dpr scales point sizes only —
        positions are logical and the viewport handles resolution."""
        g = geom(s.shape)
        px, py, pd = project(g["V"], s.ang, s.yaw, s.pitch, d4=s.depth4, w=w, h=h)

        # camera: zoom about the view centre, then pan (both in logical px)
        zoom = max(s.zoom, 1e-3)
        px = (px - w / 2) * zoom + w / 2 + s.pan[0]
        py = (py - h / 2) * zoom + h / 2 + s.pan[1]

        # synchronized instance grid, spaced pre-zoom so the camera sees a field
        n_inst = max(1, int(s.instances))
        if n_inst > 1:
            cols = math.ceil(math.sqrt(n_inst))
            rows = math.ceil(n_inst / cols)
            cell = min(w, h) * 0.72 * zoom
            offs = np.array(
                [
                    ((k % cols - (cols - 1) / 2) * cell, (k // cols - (rows - 1) / 2) * cell)
                    for k in range(n_inst)
                ],
                dtype=np.float32,
            )
        else:
            offs = np.zeros((1, 2), dtype=np.float32)

        near, far = pd.min(), pd.max()
        span = max(far - near, 1e-6)
        E = g["E"]
        edepth = (pd[E[:, 0]] + pd[E[:, 1]]) * 0.5
        order = np.argsort(edepth, kind="stable")  # painter: far first

        t = (edepth[order] - near) / span
        dens = clamp(340 / max(g["m"], 1), 0.42, 1)
        B = s.bright * dens
        heavy = g["m"] > 500
        alpha = np.clip((0.10 + 0.90 * t * t) * B, 0.015, 1)

        # the reference's depth- and brightness-scaled line width (CSS px),
        # scaled by the camera so a zoomed-out field thins out naturally
        wscale = clamp(0.75 + 0.35 * s.bright, 0.6, 1.35)
        width = ((0.35 + 0.85 * t) if heavy else (0.5 + 1.5 * t)) * wscale * zoom
        draw_w = np.maximum(width, 1.0)
        alpha = alpha * np.minimum(width, 1.0)  # sub-pixel width folds into alpha

        self.ctx.clear(*BG)
        self._lines["u_size"].value = (float(w), float(h))

        # ---- face fills, under the wireframe (agent-validated prototype) ----
        if s.faces:
            tris = face_triangles(s.shape)
            if len(tris):
                td = (pd[tris[:, 0]] + pd[tris[:, 1]] + pd[tris[:, 2]]) / 3.0
                torder = np.argsort(td, kind="stable")
                tt = (td[torder] - near) / span
                nfaces = int(tris[:, 3].max()) + 1
                fdens = min(1.0, 24.0 / max(nfaces, 1))
                fa = (0.010 + 0.055 * tt * tt) * s.bright * (0.35 + 0.65 * fdens)
                to = tris[torder]
                fverts = np.empty((len(tris) * 3, 3), dtype=np.float32)
                for corner in range(3):
                    fverts[corner::3, 0] = px[to[:, corner]]
                    fverts[corner::3, 1] = py[to[:, corner]]
                    fverts[corner::3, 2] = fa
                fverts = self._tile(fverts, offs)
                self._fbuf.orphan(fverts.nbytes)
                self._fbuf.write(fverts.tobytes())
                self._fvao.render(moderngl.TRIANGLES, vertices=len(fverts))

        eo = E[order]
        x0, y0 = px[eo[:, 0]], py[eo[:, 0]]
        x1, y1 = px[eo[:, 1]], py[eo[:, 1]]
        dx, dy = x1 - x0, y1 - y0
        ln = np.maximum(np.hypot(dx, dy), 1e-6)
        nx, ny = -dy / ln * draw_w * 0.5, dx / ln * draw_w * 0.5

        m = g["m"]
        verts = np.empty((m * 6, 3), dtype=np.float32)
        ax, ay = x0 + nx, y0 + ny
        bx, by = x0 - nx, y0 - ny
        cx_, cy_ = x1 + nx, y1 + ny
        ex, ey = x1 - nx, y1 - ny
        # two triangles per edge: (a, b, c) and (b, e, c)
        verts[0::6, 0], verts[0::6, 1] = ax, ay
        verts[1::6, 0], verts[1::6, 1] = bx, by
        verts[2::6, 0], verts[2::6, 1] = cx_, cy_
        verts[3::6, 0], verts[3::6, 1] = bx, by
        verts[4::6, 0], verts[4::6, 1] = ex, ey
        verts[5::6, 0], verts[5::6, 1] = cx_, cy_
        for k in range(6):
            verts[k::6, 2] = alpha
        verts = self._tile(verts, offs)
        self._lbuf.orphan(verts.nbytes)
        self._lbuf.write(verts.tobytes())
        self._lvao.render(moderngl.TRIANGLES, vertices=len(verts))

        if s.points:
            tp = (pd - near) / span
            order_p = np.argsort(pd, kind="stable")
            r = ((1.0 if heavy else 1.7) + 2.3 * tp * tp) * dpr * zoom
            PB = s.bright * clamp(dens * 1.5, 0.55, 1)
            pa = np.clip((0.32 + 0.68 * tp) * PB, 0.05, 1)
            pverts = np.empty((g["n"], 4), dtype=np.float32)
            pverts[:, 0] = px[order_p]
            pverts[:, 1] = py[order_p]
            pverts[:, 2] = 2.0 * r[order_p]  # diameter
            pverts[:, 3] = pa[order_p]
            pverts = self._tile(pverts, offs)
            self._pbuf.orphan(pverts.nbytes)
            self._pbuf.write(pverts.tobytes())
            self._points["u_size"].value = (float(w), float(h))
            self._pvao.render(moderngl.POINTS, vertices=len(pverts))

    @staticmethod
    def _tile(verts: np.ndarray, offs: np.ndarray) -> np.ndarray:
        """Replicate a per-instance vertex array across the instance grid."""
        if len(offs) == 1 and not offs.any():
            return verts
        out = np.tile(verts, (len(offs), 1))
        per = len(verts)
        for k, (ox, oy) in enumerate(offs):
            out[k * per : (k + 1) * per, 0] += ox
            out[k * per : (k + 1) * per, 1] += oy
        return out


def render_offscreen(
    s: ViewState, w: int = 1200, h: int = 800, ctx: moderngl.Context | None = None
) -> np.ndarray:
    """Render one frame to an FBO; returns (h, w, 3) uint8. For tests/tools."""
    own = ctx is None
    if own:
        ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h))])
    fbo.use()
    ctx.viewport = (0, 0, w, h)
    Renderer(ctx).draw(s, w, h)
    data = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(h, w, 3)[::-1]
    fbo.release()
    if own:
        ctx.release()
    return data.copy()
