"""A fractal's cells on the GPU (plan 64): one mesh, drawn once per cell.

`fractal.walk` decides on the CPU which cells are drawn and how strongly;
`fractal.instances` makes one row a cell — its centre already in the view
(4D, before the divide), its radius and its alpha. Here each kind of mesh
(a split's new edges and new corners, the whole shape's outline, the solid's
faces) is uploaded once per fractal, and the vertex shaders do the rest:
place the corner in its cell, turn it with the view, the 4D divide, the
depth cue and the fade along w (`FRAC_PLACE`, which is `fractal.Walk.place`
in float32), then the scene pass's own stroke, dot and face rules and the
eye. Nothing is sorted: the lines, dots and faces blend additively
(`view.frac_additive`; the owner's decision 3, 2026-11-18, to look at
before anything depends on it). The CPU path (`fractal.frame`, painter
sorted) stays the default and the oracle.

World space throughout: a cell is the shape's own geometry, placed in the
world like every other shape (through `u_model`, camera.zoom and pan and the
world's offset) and seen through the one eye (`u_vp`). The field's copies
(field.py) are drawn one draw each, the copy a uniform.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import moderngl
import numpy as np

from . import fractal
from .geometry import EYE_NEAR

EYE_W = f"{EYE_NEAR * 1.2:.6f}"      # render.EYE_W: the nearest clip w a stroke end keeps

# where a corner of a cell lands: `fractal.Walk.place`, in GLSL
FRAC_PLACE = """
uniform mat4 u_turn;     // the view's turn of the shape: x (a row) lands at x · u_turn
uniform vec4 u_view;     // zoom, d4 (the 4D eye), the eye's distance, w_gone
uniform vec3 u_wfade;    // w_near, w_far, w_lost (fractal.W_*)
uniform vec2 u_pan;      // the walk's p.xy: camera.pan, y up
uniform vec2 u_clamp;    // the cue's ends, (−far, top)
uniform mat4 u_off;      // the world's offset on the shape (identity: none)
uniform vec4 u_inst;     // this copy: centre (xy, world), scale (z), alpha (w)

void frac_place(vec4 x, vec4 centre, float R, out vec3 P, out float w4, out float pd,
                out float along) {
    vec4 Q = centre + R * (x * u_turn);
    float zoom = u_view.x, d4 = u_view.y, dist = u_view.z, w_gone = u_view.w;
    float rho = d4 - Q.w;
    w4 = max(rho, w_gone);
    vec3 world = Q.xyz * (d4 / w4);
    P = vec3(world.xy - u_pan, world.z) / zoom;
    along = smoothstep(0.0, 1.0, (rho - w_gone) / (u_wfade.x - w_gone))
          * smoothstep(0.0, 1.0, (u_wfade.z - rho) / (u_wfade.z - u_wfade.y));
    vec3 wd = zoom * (u_off * vec4(P, 1.0)).xyz + vec3(u_pan, 0.0);
    float range_ = length(vec3(wd.xy, dist - wd.z));
    pd = clamp(-log2(max(range_, 1e-9) / dist), u_clamp.x, u_clamp.y);
}
"""

_HEAD = """
#version 330
in vec4 in_cell;         // the cell: its centre in the view (4D, before the divide)
in vec2 in_cr;           // …its radius in the view, its alpha
uniform mat4 u_vp;
uniform mat4 u_model;
uniform vec2 u_tspan;    // the cue's near end and its span (draw_scene's near, span)
""" + FRAC_PLACE

# render.LINE_VS, its width and alpha made here from the cue (draw_scene's
# rules for a styled shape: e_width 1, e_rgb white)
LINE_VS = _HEAD + """
in vec4 in_a;
in vec4 in_b;
in vec2 in_corner;
uniform vec2 u_size;
uniform float u_wscale;
uniform vec4 u_stroke;   // bright × density, wscale, the lines' opacity, heavy (0 / 1)
uniform float u_legacy;  // 1: the legacy path (the fold here, as draw_scene's)
out float v_alpha;
out vec3 v_rgb;
void main() {
    vec3 Pa, Pb;
    float wa, wb, pda, pdb, la, lb;
    frac_place(in_a, in_cell, in_cr.x, Pa, wa, pda, la);
    frac_place(in_b, in_cell, in_cr.x, Pb, wb, pdb, lb);
    float t = ((pda + pdb) * 0.5 - u_tspan.x) / u_tspan.y;
    float alpha = clamp((0.10 + 0.90 * t * t) * u_stroke.x, 0.015, 1.0) * (in_cr.y * min(la, lb));
    float width = (u_stroke.w > 0.5 ? 0.35 + 0.85 * t : 0.5 + 1.5 * t) * u_stroke.y;
    if (u_legacy > 0.5) {
        alpha = alpha * min(width, 1.0) * u_stroke.z;
        width = max(width, 1.0);
    } else {
        alpha = alpha * u_stroke.z;
    }
    vec3 o = vec3(u_inst.xy, 0.0);
    vec4 ca = u_vp * (u_model * vec4(Pa * u_inst.z + o, 1.0));
    vec4 cb = u_vp * (u_model * vec4(Pb * u_inst.z + o, 1.0));
    const float W = """ + EYE_W + """;
    float wk = width * mix(1.0, u_inst.z, u_wscale);
    v_alpha = alpha * min(wk, 1.0) * u_inst.w;
    v_rgb = vec3(1.0);
    if ((ca.w < W && cb.w < W) || v_alpha <= 0.0) {
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    if (ca.w < W) ca = mix(ca, cb, (W - ca.w) / (cb.w - ca.w));
    if (cb.w < W) cb = mix(cb, ca, (W - cb.w) / (ca.w - cb.w));
    vec2 half_size = 0.5 * u_size;
    vec2 sa = ca.xy / ca.w * half_size;
    vec2 sb = cb.xy / cb.w * half_size;
    vec2 d = sb - sa;
    float ln = max(length(d), 1e-6);
    vec2 n = vec2(-d.y, d.x) / ln * (0.5 * max(wk, 1.0) * in_corner.y);
    vec4 c = in_corner.x < 0.5 ? ca : cb;
    gl_Position = vec4(c.xy + n / half_size * c.w, c.z, c.w);
}
"""

# render.POINT_VS, its radius and alpha made here (draw_scene's point rules)
POINT_VS = _HEAD + """
in vec4 in_pos;
in vec2 in_corner;
uniform vec2 u_px;
uniform float u_wscale;
uniform vec4 u_dot;      // bright × clamp(dens · 1.5), the points' opacity, dpr, heavy
uniform float u_legacy;
uniform vec3 u_rgb;      // RED
out float v_alpha;
out vec2 v_corner;
out vec3 v_rgb;
void main() {
    vec3 P;
    float w4, pd, along;
    frac_place(in_pos, in_cell, in_cr.x, P, w4, pd, along);
    float tp = (pd - u_tspan.x) / u_tspan.y;
    float r = ((u_dot.w > 0.5 ? 1.0 : 1.7) + 2.3 * tp * tp) * u_dot.z;
    if (u_legacy > 0.5) r = floor(2.0 * r + 0.5) / 2.0;
    float pa = clamp((0.32 + 0.68 * tp) * u_dot.x, 0.05, 1.0) * u_dot.y;
    float k = in_cr.y * along;
    pa = pa * k;
    r = r * sqrt(k);
    vec4 c = u_vp * (u_model * vec4(P * u_inst.z + vec3(u_inst.xy, 0.0), 1.0));
    float d = floor(2.0 * r * mix(1.0, u_inst.z, u_wscale) + 0.5);
    v_alpha = pa * min(d, 1.0) * u_inst.w;
    v_corner = in_corner;
    v_rgb = u_rgb;
    if (c.w < """ + EYE_W + """ || v_alpha <= 0.0) {
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    gl_Position = vec4(c.xy + in_corner * (0.5 * max(d, 1.0)) / (0.5 * u_px) * c.w, c.z, c.w);
}
"""

# render.FACE_VS: each corner carries its triangle's three, for the
# triangle's own cue (the mean of its corners') and fade (the least)
FACE_VS = _HEAD + """
in vec4 in_c0;
in vec4 in_c1;
in vec4 in_c2;
in float in_k;           // which of the three this vertex is
in vec2 in_uv;
in float in_fid;
uniform vec2 u_face;     // brightness, × (0.35 + 0.65 · the faces' density)
out vec2 v_uv;
out float v_alpha;
out float v_fid;
void main() {
    vec3 P0, P1, P2;
    float w0, w1, w2, d0, d1, d2, l0, l1, l2;
    frac_place(in_c0, in_cell, in_cr.x, P0, w0, d0, l0);
    frac_place(in_c1, in_cell, in_cr.x, P1, w1, d1, l1);
    frac_place(in_c2, in_cell, in_cr.x, P2, w2, d2, l2);
    float tt = ((d0 + d1 + d2) / 3.0 - u_tspan.x) / u_tspan.y;
    float fa = (0.010 + 0.055 * tt * tt) * u_face.x * u_face.y
             * (in_cr.y * min(l0, min(l1, l2)));
    vec3 P = in_k < 0.5 ? P0 : (in_k < 1.5 ? P1 : P2);
    float w4 = in_k < 0.5 ? w0 : (in_k < 1.5 ? w1 : w2);
    vec4 q = vec4(P * u_inst.z + vec3(u_inst.xy, 0.0), 1.0);
    gl_Position = (u_vp * (u_model * q)) * w4;
    v_uv = in_uv;
    v_alpha = fa * u_inst.w;
    v_fid = in_fid;
}
"""

# render.COVER_VS: the faces written solid, for the look-back's occlusion
COVER_VS = _HEAD + """
in vec4 in_c0;
in vec4 in_c1;
in vec4 in_c2;
in float in_k;
void main() {
    vec4 x = in_k < 0.5 ? in_c0 : (in_k < 1.5 ? in_c1 : in_c2);
    vec3 P;
    float w4, pd, along;
    frac_place(x, in_cell, in_cr.x, P, w4, pd, along);
    vec4 q = vec4(P * u_inst.z + vec3(u_inst.xy, 0.0), 1.0);
    gl_Position = (u_vp * (u_model * q)) * w4;
}
"""

# the parity probe (tests): `frac_place` of each mesh point in each cell,
# out by transform feedback — P (3), the divisor, the cue, the fade
PROBE_VS = """
#version 330
in vec4 in_pos;
in vec4 in_cell;
in vec2 in_cr;
""" + FRAC_PLACE + """
out vec3 o_P;
out float o_w4;
out float o_pd;
out float o_along;
void main() {
    frac_place(in_pos, in_cell, in_cr.x, o_P, o_w4, o_pd, o_along);
}
"""

INST_FORMAT = "4f 2f/i"
_EDGE_CORNERS = np.array([(0, 1), (0, -1), (1, 1), (0, -1), (1, -1), (1, 1)], dtype=np.float32)
_POINT_CORNERS = np.array([(-1, -1), (1, -1), (-1, 1), (1, -1), (1, 1), (-1, 1)],
                          dtype=np.float32)


def line_mesh(V: np.ndarray, E: np.ndarray) -> np.ndarray:
    """Edges E of points V (4D) as quads: six vertices an edge of (a, b,
    corner) — "4f 4f 2f", render's edge quad with 4D ends."""
    out = np.empty((len(E) * 6, 10), dtype=np.float32)
    for k in range(6):
        out[k::6, 0:4] = V[E[:, 0]]
        out[k::6, 4:8] = V[E[:, 1]]
        out[k::6, 8:10] = _EDGE_CORNERS[k]
    return out


def point_mesh(V: np.ndarray) -> np.ndarray:
    """Points V (4D) as quads: six vertices a point of (pos, corner) — "4f 2f"."""
    out = np.empty((len(V) * 6, 6), dtype=np.float32)
    for k in range(6):
        out[k::6, 0:4] = V
        out[k::6, 4:6] = _POINT_CORNERS[k]
    return out


def face_mesh(spec: fractal.Fractal) -> np.ndarray:
    """The solid's triangles: three vertices each of (its three corners, which
    one this is, its uv, its face) — "4f 4f 4f 1f 2f 1f"."""
    T = spec.tris
    out = np.empty((len(T) * 3, 16), dtype=np.float32)
    for k in range(3):
        out[k::3, 0:4] = spec.V[T[:, 0]]
        out[k::3, 4:8] = spec.V[T[:, 1]]
        out[k::3, 8:12] = spec.V[T[:, 2]]
        out[k::3, 12] = k
        out[k::3, 13:15] = spec.tri_uv[:, k]
        out[k::3, 15] = spec.tri_face
    return out


def put(prog: moderngl.Program, name: str, value) -> None:
    """A uniform, by bytes or by value; nothing when the compiler dropped it."""
    if name not in prog:
        return
    u = cast(moderngl.Uniform, prog[name])
    if isinstance(value, bytes):
        u.write(value)
    else:
        u.value = value


def blend(ctx: moderngl.Context, func: tuple) -> None:
    """`ctx.blend_func = func` (moderngl's stubs give it no setter)."""
    cast(Any, ctx).blend_func = func


def view_uniforms(prog: moderngl.Program, wk: fractal.Walk, near: float, span: float) -> None:
    """The walk's view on a program of this module (`FRAC_PLACE`)."""
    put(prog, "u_turn", np.ascontiguousarray(wk.M.T, dtype="f4").tobytes())
    put(prog, "u_view", (float(wk.zoom), float(wk.d4), float(wk.dist), float(wk.w_gone)))
    put(prog, "u_wfade", (float(wk.w_near), float(wk.w_far), float(wk.w_lost)))
    put(prog, "u_pan", (float(wk.p[0]), float(wk.p[1])))
    put(prog, "u_clamp", (float(-wk.spec.far), float(wk.top)))
    off = np.eye(4) if wk.off is None else wk.off
    put(prog, "u_off", np.ascontiguousarray(np.asarray(off).T, dtype="f4").tobytes())
    put(prog, "u_tspan", (float(near), float(span)))


class Meshes:
    """One fractal's meshes on the GPU, uploaded once (`CellDraw.meshes`)."""

    def __init__(self, ctx: moderngl.Context, spec: fractal.Fractal):
        nv = spec.new_V
        self.buffers = {
            "lines": ctx.buffer(line_mesh(nv, spec.new_E).tobytes()),
            "outline": ctx.buffer(line_mesh(spec.V, spec.E).tobytes()),
            "dots": ctx.buffer(point_mesh(nv[spec.new_dot]).tobytes()),
            "corners": ctx.buffer(point_mesh(spec.V).tobytes()),
            "faces": ctx.buffer(face_mesh(spec).tobytes()),
        }
        self.counts = {"lines": len(spec.new_E) * 6, "outline": len(spec.E) * 6,
                       "dots": int(spec.new_dot.sum()) * 6, "corners": len(spec.V) * 6,
                       "faces": len(spec.tris) * 3}

    def release(self) -> None:
        for b in self.buffers.values():
            b.release()


class CellDraw:
    """The GPU path's programs, meshes and instance buffers (render's
    `Renderer._cells`, made on first use)."""

    def __init__(self, ctx: moderngl.Context, line_fs: str, point_fs: str, cover_fs: str):
        self.ctx = ctx
        self.lines = ctx.program(vertex_shader=LINE_VS, fragment_shader=line_fs)
        self.points = ctx.program(vertex_shader=POINT_VS, fragment_shader=point_fs)
        self.cover = ctx.program(vertex_shader=COVER_VS, fragment_shader=cover_fs)
        self.face: moderngl.Program | None = None
        self._face_fs: str | None = None
        self.inst = {k: ctx.buffer(reserve=64 * 24, dynamic=True)
                     for k in ("lines", "outline", "corners", "faces")}
        self.counts = dict.fromkeys(self.inst, 0)
        self._meshes: dict[str, Meshes] = {}
        self._vaos: dict[tuple, moderngl.VertexArray] = {}

    def release(self) -> None:
        for v in self._vaos.values():
            v.release()
        for m in self._meshes.values():
            m.release()
        for b in self.inst.values():
            b.release()
        for p in (self.lines, self.points, self.cover, self.face):
            if p is not None:
                p.release()

    def face_program(self, face_fs: str) -> moderngl.Program | None:
        """The face program: this module's FACE_VS over the faces' own
        fragment shader (render's, patterns.glsl in it); rebuilt when that
        changes. None while it does not compile (render says why)."""
        if face_fs != self._face_fs:
            try:
                prog = self.ctx.program(vertex_shader=FACE_VS, fragment_shader=face_fs)
            except Exception:  # noqa: BLE001 — the faces' own program reports it
                return None
            for key in [k for k in self._vaos if k[0] == "faces"]:
                self._vaos.pop(key).release()
            if self.face is not None:
                self.face.release()
            self.face, self._face_fs = prog, face_fs
            put(prog, "u_pic", 1)
        return self.face

    def meshes(self, spec: fractal.Fractal, name: str) -> Meshes:
        m = self._meshes.get(name)
        if m is None:
            m = self._meshes[name] = Meshes(self.ctx, spec)
        return m

    def upload(self, rows: dict[str, np.ndarray]) -> None:
        """This frame's instance rows (`fractal.instances`)."""
        for k, buf in self.inst.items():
            a = np.ascontiguousarray(rows[k], dtype="f4")
            self.counts[k] = len(a)
            if len(a):
                if buf.size < a.nbytes:
                    buf.orphan(max(a.nbytes, buf.size * 2))
                buf.write(a.tobytes())

    def vao(self, name: str, mesh: str, kind: str, prog: moderngl.Program) -> moderngl.VertexArray:
        """The vertex array of mesh `mesh` of fractal `name`, drawn per row of
        instance buffer `kind` by `prog`."""
        key = (("faces" if prog is self.face else "x"), name, mesh, kind, id(prog))
        v = self._vaos.get(key)
        if v is None:
            buf = self._meshes[name].buffers[mesh]
            fmt = {"lines": ("4f 4f 2f", "in_a", "in_b", "in_corner"),
                   "outline": ("4f 4f 2f", "in_a", "in_b", "in_corner"),
                   "dots": ("4f 2f", "in_pos", "in_corner"),
                   "corners": ("4f 2f", "in_pos", "in_corner"),
                   "faces": ("4f 4f 4f 1f 2f 1f", "in_c0", "in_c1", "in_c2", "in_k",
                             "in_uv", "in_fid")}[mesh]
            if prog is self.cover:
                fmt = ("4f 4f 4f 1f 12x", "in_c0", "in_c1", "in_c2", "in_k")
            v = self._vaos[key] = self.ctx.vertex_array(
                prog, [(buf, *fmt), (self.inst[kind], INST_FORMAT, "in_cell", "in_cr")])
        return v

    def draw(self, name: str, mesh: str, kind: str, prog: moderngl.Program,
             copies: np.ndarray) -> Callable[[], None] | None:
        """Draw mesh `mesh` once per cell of `kind` and per copy (`copies`:
        render's rows, centre xy, scale, alpha); returns the same draw again,
        for the depth pass, or None when there is nothing to draw."""
        n, cells = self._meshes[name].counts[mesh], self.counts[kind]
        if not n or not cells or not len(copies):
            return None
        v = self.vao(name, mesh, kind, prog)

        def go() -> None:
            for row in copies:
                put(prog, "u_inst", tuple(float(x) for x in row))
                v.render(moderngl.TRIANGLES, vertices=n, instances=cells)

        go()
        return go


def probe(ctx: moderngl.Context, wk: fractal.Walk, X: np.ndarray,
          rows: np.ndarray) -> np.ndarray:
    """`FRAC_PLACE` of points X (n, 4, the shape's own frame) in each cell
    of `rows` (`fractal.instances`'s), cell by cell, by transform feedback:
    (cells · n, 6) float32 — P, the divisor, the cue, the fade. What the
    parity test holds against `Walk.place`."""
    prog = ctx.program(vertex_shader=PROBE_VS, varyings=("o_P", "o_w4", "o_pd", "o_along"))
    vb = ctx.buffer(np.ascontiguousarray(X, dtype="f4").tobytes())
    ib = ctx.buffer(np.ascontiguousarray(rows, dtype="f4").tobytes())
    out = ctx.buffer(reserve=len(X) * len(rows) * 6 * 4)
    vao = ctx.vertex_array(prog, [(vb, "4f", "in_pos"), (ib, INST_FORMAT, "in_cell", "in_cr")])
    try:
        view_uniforms(prog, wk, 0.0, 1.0)
        vao.transform(out, mode=moderngl.POINTS, vertices=len(X), instances=len(rows))
        return np.frombuffer(out.read(), dtype="f4").reshape(-1, 6).copy()
    finally:
        for res in (vao, out, ib, vb, prog):
            res.release()
