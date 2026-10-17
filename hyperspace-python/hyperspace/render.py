"""moderngl renderer — port of the draw() pipeline of hyperspace.html.

Plan 26 A2, one camera: the CPU takes the shape to 3D
(geometry.world_points: rotate4, the 4D divide, the yaw/pitch turntable)
and the vertex shaders take it to the clip through one shared 4×4, the
eye (`u_vp`, geometry.eye_matrix, the `eye.*` params), after the shape's
world transform (`u_model`: camera.zoom and camera.pan). The default eye
is project_h's old 3D divide, so at zoom 1 and pan 0 every vertex lands
within a ten-thousandth of a pixel of where project_h — the renderer's
path until A2, and geometry.project's, the parity oracle — puts it
(tests/test_camera.py). The dataclass it draws, ViewState, lives in
view.py so nothing has to import moderngl to hold a view.

Blending decision (plan 02 task 2): alpha-over in painter order, not
additive. The additive suggestion existed to avoid a CPU depth sort, but the
CPU already computes every edge depth per frame, so the argsort is free and
alpha-over + sort reproduces the reference compositing exactly.

Edges are screen-space quads, not GL lines: core-profile macOS caps line
width at 1 px, and the first comparison shots showed the near-edge weight
hierarchy (width 0.5–2 px scaled by depth and brightness) is a visible part
of the look. Widths below 1 px fold into alpha, the standard thin-line
trick, so far edges render correctly without MSAA. Since A2 the quads —
and the points', once point sprites — are expanded in the vertex shader
from the edge's two 3D ends, so they carry a real depth; their widths
are pixels × the zoom in world space (the default, the pre-A2 feel) or
pixels whatever the zoom in screen space (`view.screen_strokes`, plan 26
A2b). The scene's depth buffer
holds the shape's nearest visible surface (`DEPTH_ALPHA`), written after
its colour; the see-through shape itself is still painter-sorted.

The scene is drawn into a texture (SceneTarget — an FBO at the bound
framebuffer's size and sample count), and a post pass puts it on the
window over the look-back history (lookback.py): with the pipeline off
that pass is a copy and the output is bit-identical to drawing straight
to the window. With an effect on (fx.py) the post pass lands in the
effect chain's texture instead and the last effect writes the window.
`draw_scene` is the scene pass alone, for anything that wants the raw
frame.

Effects aimed at the faces (fx.py, plan 20) run before the scene pass, as
a second chain over a fixed-size picture of what a face shows
(`Renderer._face_picture`: a seed pass, the chain, mipmaps); the face
shader then draws that picture on every face, per face or in screen
space, in place of computing the pattern and the bitmap per fragment. So
the faces' effects are *in* the scene texture: the echoes and the dream
carry them, and the frame's effects run over them. With nothing aimed at
the faces none of it runs, nothing is allocated and the frame is
bit-identical. The ghost hands (ghost.py) are a geometry in the same
camera (plan 26 A3): by default their own layer, laid over the finished
frame (or onto it before the effects); wired into the scene, solid,
before the shape; off, the frame is untouched. Last of all the master
dim (`Renderer.dim`, the crossfader's `output.dim`; plan 15 WP3)
multiplies what is there — it draws nothing of its own, and at 1 it does
not run.

Plan 21: `Renderer.draw_outputs` shows that one frame on several outputs
(`outputs.View`), each through its own switches — the scene, the hands,
its own dim. The scene, the capture and the hands' layer run once a
frame; the look-back composite and the effect chain once per distinct
pipeline (`outputs.route`); the picture, the hands over it and the dim
once per output. `draw` is `draw_outputs` with one default view on the
bound framebuffer, and is the frame it always was, byte for byte.

Plan 26 A1: those passes are the nodes of a render graph (graph.py).
`_draw_frame` builds the default graph for the views' switches — or
reuses the last one while they do not change — and evaluates it: the
nodes run once each, in an order settled when the graph was built, and
each node is timed on the GPU (`PassTimer`, one line per node on the
SYSTEM page). The default graph is today's three pipelines; every golden
frame of A0 is drawn byte for byte. The passes themselves (`draw_scene`,
`_face_picture`, `_draw_cover`, `_compose`, `_show`, `dim_pass`) stay
here; the nodes call them.
"""

from __future__ import annotations

import math
import time
from dataclasses import replace
from pathlib import Path
from typing import Self

import moderngl
import numpy as np

from .fx import FACES, SCREEN, FxChain, FxState
from .geometry import (
    EYE_DISTANCE,
    EYE_FAR,
    EYE_FOV,
    EYE_NEAR,
    SCALE,
    eye_matrix,
    face_triangles,
    face_uvs,
    geom,
    model_matrix,
    view_angles,
    view_depth,
    w_masked,
    world_points,
)
from .ghost import Ghost, GhostState
from .glsl import QUAD_VS, common, common_mtime, gl_error
from .graph import Frame, Graph, Wiring, cloud_roles, default_graph, graph_key
from .lookback import DreamState, Lookback
from .outputs import Handoff, Switches, View, capped, fit
from .patterns import MODES, SPEED
from .tapers import clamp
from .view import N_MOD, RED, ViewState  # re-exported for callers that had them from here

PATTERNS_GLSL = Path(__file__).parent / "shaders" / "patterns.glsl"

BG = (0.0, 0.0, 0.0)

# the side, in texels, of the picture the faces' effects run over (plan 20
# fork F2): square, fixed, a constant and not a param — 512 cannot be told
# from it on a face and 2048 costs several times as much
FACE_PIC = 1024

# Plan 26 A2, the one camera: the scene's vertices arrive in 3D — the
# shape after the 4D tumble, the 4D divide and the yaw/pitch turntable
# (geometry.world_points), plus its copy's cell offset — and the vertex
# shaders take them to the clip through the shape's world transform
# (u_model: camera.zoom and camera.pan, geometry.model_matrix) and the
# eye (u_vp: the one shared 4×4, geometry.eye_matrix; the same matrix the
# ghost hands' Geometry takes). Edges and points are quads expanded here,
# in screen space, so they keep their pixel widths and carry a real depth.
# An edge end behind the eye is slid along the edge to just in front of it
# (EYE_W); a point behind it is dropped.
EYE_W = f"{EYE_NEAR * 1.2:.6f}"     # the nearest clip w a stroke end is kept at

# the shape's depth (the scene's depth buffer, for what is drawn after it
# or composited by depth) is its nearest *visible* surface: a fragment
# writes depth only above this alpha (`Renderer._depth_pass`). Faint
# fills and far edges stay see-through to depth as they are to the eye
DEPTH_ALPHA = 0.25

# plan 26 A3, the depth-aware composite (`LAYER_FS`, `Renderer.lay`): a
# layer's texel is hidden where the scene's visible surface is nearer the
# eye by more than this, in world units (shape radii; the default
# calibration puts about 170 mm of the Leap's box in one) — about 8 mm, so
# a fingertip touching a face is not cut by the depth buffers' rounding
LAYER_DEPTH_BIAS = 0.05

LINE_VS = """
#version 330
in vec3 in_a;        // the edge's two ends, the shape's 3D points + the copy's offset
in vec3 in_b;
in vec2 in_corner;   // x: which end (0 a, 1 b); y: which side of the edge (±1)
in float in_width;   // logical px
in float in_alpha;
uniform mat4 u_vp;   // the eye
uniform mat4 u_model; // the shape's world transform
uniform vec2 u_size; // logical viewport size
out float v_alpha;
void main() {
    vec4 ca = u_vp * (u_model * vec4(in_a, 1.0));
    vec4 cb = u_vp * (u_model * vec4(in_b, 1.0));
    const float W = """ + EYE_W + """;
    v_alpha = in_alpha;
    if (ca.w < W && cb.w < W) {          // wholly behind the eye: nothing
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    if (ca.w < W) ca = mix(ca, cb, (W - ca.w) / (cb.w - ca.w));
    if (cb.w < W) cb = mix(cb, ca, (W - cb.w) / (ca.w - cb.w));
    vec2 half_size = 0.5 * u_size;
    vec2 sa = ca.xy / ca.w * half_size;  // logical px about the centre
    vec2 sb = cb.xy / cb.w * half_size;
    vec2 d = sb - sa;
    float ln = max(length(d), 1e-6);
    vec2 n = vec2(-d.y, d.x) / ln * (0.5 * in_width * in_corner.y);
    vec4 c = in_corner.x < 0.5 ? ca : cb;
    gl_Position = vec4(c.xy + n / half_size * c.w, c.z, c.w);
}
"""

LINE_FS = """
#version 330
in float v_alpha;
uniform float u_depth_alpha;   // < 0 the colour pass; else the depth pass's threshold
out vec4 f_color;
void main() {
    if (u_depth_alpha >= 0.0 && v_alpha <= u_depth_alpha) discard;
    f_color = vec4(1.0, 1.0, 1.0, v_alpha);
}
"""

# the master dim: one full-screen triangle whose only output is its alpha,
# the factor; the blend function does the multiply (Renderer.dim_pass), so
# no texture is read
DIM_VS = """
#version 330
void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

DIM_FS = """
#version 330
uniform float u_factor;
out vec4 f_color;
void main() { f_color = vec4(0.0, 0.0, 0.0, u_factor); }
"""

# a frame texture onto an output (plan 21 WP1): 1:1 by texelFetch — the
# same bytes, as the look-back's post pass reads the scene — or scaled
# through the fit rect (the viewport) by the sampler. On an opaque ground
# the output keeps alpha 1 whatever the frame holds
SHOW_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform int u_scaled;
uniform ivec2 u_origin;      // the rect's origin (gl_FragCoord is window-relative)
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
    if (u_opaque != 0) c.a = 1.0;
    f_color = c;
}
"""

# a layer laid onto a picture (plan 26 A3, `Renderer.lay`: the graph's
# Composite node, and an output's hands over when its wiring is not plain
# over): premultiplied × its opacity — `ghost.COMPOSITE_FS`'s arithmetic,
# so plain over is the same bytes — mirrored by `u_flip` like the frame;
# depth-aware (`u_depth_on`), a texel is dropped where the scene's visible
# surface is nearer the eye than the layer's by more than `u_bias` (world
# units, both depths linearised through the eye's clip planes). Where the
# scene wrote no depth (the far plane) the layer always shows, and so does
# a texel whose resolved depth is the far plane: at a multisampled
# silhouette the colour is the samples' mean and the depth one sample
LAYER_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_layer;
uniform float u_alpha;
uniform ivec2 u_flip;
uniform int u_depth_on;
uniform sampler2D u_layer_depth;
uniform sampler2D u_scene_depth;
uniform vec2 u_clip;         // the eye's near and far planes
uniform float u_bias;
out vec4 f_color;
float lin(float d) {
    float z = d * 2.0 - 1.0;
    return 2.0 * u_clip.x * u_clip.y / (u_clip.y + u_clip.x - z * (u_clip.y - u_clip.x));
}
void main() {
    vec2 uv = v_uv;
    if (u_flip.x != 0) uv.x = 1.0 - uv.x;
    if (u_flip.y != 0) uv.y = 1.0 - uv.y;
    vec4 c = texture(u_layer, uv) * u_alpha;
    if (u_depth_on != 0) {
        float ds = texture(u_scene_depth, uv).r;
        float dl = texture(u_layer_depth, uv).r;
        if (ds < 1.0 && dl < 1.0 && lin(dl) > lin(ds) + u_bias) c = vec4(0.0);
    }
    f_color = c;
}
"""

FACE_VS = """
#version 330
in vec3 in_pos;      // the shape's 3D point + the copy's offset (see LINE_VS)
in float in_w4;      // the 4D divisor: × the clip w, so the uv is perspective-correct
                     // across both divides, as the old combined divisor made it
in vec2 in_uv;       // face-local coordinates
in float in_alpha;
in float in_fid;     // face index within the shape
uniform mat4 u_vp;
uniform mat4 u_model;
out vec2 v_uv;
out float v_alpha;
out float v_fid;
void main() {
    gl_Position = (u_vp * (u_model * vec4(in_pos, 1.0))) * in_w4;
    v_uv = in_uv;
    v_alpha = in_alpha;
    v_fid = in_fid;
}
"""

# the bands a pattern may read as u_levels: the analyzer's first N_BANDS
# lanes (a layout has six; the band editor can make more or fewer)
N_BANDS = 8

# what the face program and the seed program both declare: everything the
# pattern and the bitmap read
FACE_UNIFORMS = f"""
uniform float u_time;
uniform float u_ptime;       // the patterns' clock: seconds × SPEED (Renderer._pattern_clock)
uniform float u_mod[{N_MOD}];  // pattern.mod.* — the routed pattern inputs
uniform float u_levels[{N_BANDS}];  // the analyzer's lanes, out / CEIL (Renderer.bands)
uniform int u_nlevels;        // how many of them there are (0: no audio)
uniform int u_mode;
uniform float u_mix;
uniform sampler2D u_bitmap;
uniform int u_bmp_on;
uniform float u_bmp_alpha;
uniform vec2 u_bmp_pos;      // path offset about the face centre, UV units
uniform vec2 u_bmp_scale;    // (w, h) in face-UV units, aspect preserved
"""

FACE_FS_HEAD = """
#version 330
in vec2 v_uv;
in float v_alpha;
in float v_fid;
out vec4 f_color;
""" + FACE_UNIFORMS + """
uniform sampler2D u_pic;     // the faces' effects' picture (Renderer._face_picture)
uniform int u_pic_on;        // 0 none: pattern and bitmap; 1 the picture per face; 2 in screen space
uniform vec2 u_pic_fb;       // the scene pass's framebuffer size, px
uniform float u_depth_alpha; // < 0 the colour pass; else the depth pass's threshold
"""

# the seed pass: a fullscreen triangle (glsl.QUAD_VS) over the picture
SEED_FS_HEAD = """
#version 330
in vec2 v_uv;
out vec4 f_color;
// the face fragment's other inputs, as face 0 at full alpha: a patterns.glsl
// that reads them by name compiles here as it does there
const float v_alpha = 1.0;
const float v_fid = 0.0;
""" + FACE_UNIFORMS

# what a face shows at its own `uv`: the pattern, then the bitmap over it.
# One function, called by the face fragment (per fragment, with its face's
# id) and by the seed (once per texel of the picture, as face 0)
FACE_PX = """
void face_px(vec2 uv, float fid, out vec3 rgb, out float shade) {
    rgb = vec3(1.0);
    shade = 1.0;
    if (u_mode != 0) {
        vec4 v = pattern(u_mode, uv, fid);
        v = clamp(v, 0.0, 1.0);
        shade = mix(1.0, 2.8 * v.a, u_mix);
        rgb = mix(vec3(1.0), v.rgb, u_mix);
    }
    if (u_bmp_on != 0) {
        vec2 q = (uv - 0.5 - u_bmp_pos) / u_bmp_scale + 0.5;
        if (q.x >= 0.0 && q.x <= 1.0 && q.y >= 0.0 && q.y <= 1.0) {
            vec4 b = texture(u_bitmap, vec2(q.x, 1.0 - q.y));
            float ba = b.a * u_bmp_alpha;
            rgb = mix(rgb, b.rgb, ba);
            shade = mix(shade, 2.8, ba);
        }
    }
}
"""

FACE_FS_TAIL = FACE_PX + """
void main() {
    vec3 rgb;
    float shade;
    if (u_pic_on != 0) {
        // the picture the faces' effects made, premultiplied by its
        // intensity: per face at the face's own uv (it turns with the
        // shape); in screen space at the fragment's place in the window,
        // the square picture centred and scaled to cover the longer side
        // (the faces are windows onto it)
        vec2 q = v_uv;
        if (u_pic_on == 2)
            q = (gl_FragCoord.xy - 0.5 * u_pic_fb) / max(u_pic_fb.x, u_pic_fb.y) + 0.5;
        vec4 t = texture(u_pic, q);
        shade = 2.8 * t.a;
        rgb = t.a > 1e-4 ? t.rgb / t.a : vec3(0.0);
    } else {
        face_px(v_uv, v_fid, rgb, shade);
    }
    float a = v_alpha * shade;
    if (a <= 0.0 || (u_depth_alpha >= 0.0 && a <= u_depth_alpha)) discard;
    f_color = vec4(rgb, a);
}
"""

# the seed: what face 0 shows, written premultiplied with alpha as its
# intensity — 2.8 is the face shader's full intensity, so a plain FLAT
# face (shade 1) is a mid-grey field a generator can light and a multiply
# can darken
SEED_FS_TAIL = FACE_PX + """
void main() {
    vec3 rgb;
    float shade;
    face_px(v_uv, v_fid, rgb, shade);
    float s = clamp(shade / 2.8, 0.0, 1.0);
    f_color = vec4(rgb * s, s);
}
"""


def _face_fragment(head: str, patterns: str, tail: str) -> str:
    """A face-side fragment shader: the shared helpers first (source
    string 1), then patterns.glsl (string 2) — a compile error names the
    file and its own line."""
    return head + "#line 1 1\n" + common() + "\n#line 1 2\n" + patterns + tail


# the faces' coverage mask for the look-back's occlusion: the same
# geometry as the face pass, written solid — a face covers the wake behind
# it however faint its fill (fills are drawn at a few percent alpha)
COVER_VS = """
#version 330
in vec3 in_pos;
in float in_w4;
uniform mat4 u_vp;
uniform mat4 u_model;
void main() {
    gl_Position = (u_vp * (u_model * vec4(in_pos, 1.0))) * in_w4;
}
"""

COVER_FS = """
#version 330
out vec4 f_color;
void main() { f_color = vec4(1.0); }
"""

POINT_VS = """
#version 330
in vec3 in_pos;      // the shape's 3D point + the copy's offset (see LINE_VS)
in vec2 in_corner;   // the quad's corner, (±1, ±1)
in float in_size;    // radius in framebuffer pixels
in float in_alpha;
uniform mat4 u_vp;
uniform mat4 u_model;
uniform vec2 u_px;   // the framebuffer viewport, px
out float v_alpha;
out vec2 v_corner;
void main() {
    vec4 c = u_vp * (u_model * vec4(in_pos, 1.0));
    v_alpha = in_alpha;
    v_corner = in_corner;
    if (c.w < """ + EYE_W + """) {        // behind the eye: nothing
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    gl_Position = vec4(c.xy + in_corner * in_size / (0.5 * u_px) * c.w, c.z, c.w);
}
"""

# the quad's corner stands in for gl_PointCoord: the same round dot
POINT_FS = """
#version 330
in float v_alpha;
in vec2 v_corner;
out vec4 f_color;
uniform vec3 u_color;
uniform float u_depth_alpha;   // < 0 the colour pass; else the depth pass's threshold
void main() {
    float a = v_alpha * (1.0 - smoothstep(0.8, 1.0, length(v_corner)));
    if (a <= 0.0 || (u_depth_alpha >= 0.0 && a <= u_depth_alpha)) discard;
    f_color = vec4(u_color, a);
}
"""

# the three vertex buffers' layouts, one row per vertex:
#   face  — position (3), 4D divisor, uv (2), alpha, face id
#   edge  — end a (3), end b (3), corner (end, side), width (logical px), alpha
#   point — position (3), corner (2), radius (framebuffer px), alpha
FACE_FORMAT = "3f 1f 2f 1f 1f"
LINE_FORMAT = "3f 3f 2f 1f 1f"
POINT_FORMAT = "3f 2f 1f 1f"

# a point's quad: two triangles over its four corners
_POINT_CORNERS = np.array([(-1, -1), (1, -1), (-1, 1), (1, -1), (1, 1), (-1, 1)],
                          dtype=np.float32)
# an edge's quad: (a, b, c) and (b, e, c) over its ends' two sides —
# (end, side): a = (0, +1), b = (0, −1), c = (1, +1), e = (1, −1)
_EDGE_CORNERS = np.array([(0, 1), (0, -1), (1, 1), (0, -1), (1, -1), (1, 1)],
                         dtype=np.float32)




# ---- instance layouts (plan 20 WP6): where each copy sits, in cells ----

LAYOUT_GRID, LAYOUT_HEX, LAYOUT_RING = 0, 1, 2     # params.INST_LAYOUT's order
# a cell — the spacing between neighbouring copies — in the world, shape
# radii: the old 0.72·min(w, h) px through the default eye (SCALE·min(w, h)
# px a unit at the origin), so a field at zoom 1 is spaced as it was
CELL = 0.72 / SCALE
_HEX_STEPS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))   # axial (q, r)


def _hex_spiral(n: int) -> np.ndarray:
    """The first `n` cells of a honeycomb spiral as (n, 2) float64 (gx, gy):
    the centre, then ring 1 (six cells), ring 2 (twelve), ring m (6m), each
    walked from axial (−m, m) taking m steps along each direction in turn.
    A cell's place does not depend on `n`."""
    out = [(0.0, 0.0)]
    m = 0
    while len(out) < n:
        m += 1
        q, r = -m, m
        for dq, dr in _HEX_STEPS:
            for _ in range(m):
                out.append((q + r / 2, r * math.sqrt(3.0) / 2))
                q, r = q + dq, r + dr
    return np.array(out[:n], dtype=np.float64).reshape(-1, 2)


def inst_positions(n: int, layout: int) -> tuple[np.ndarray, np.ndarray]:
    """(gx, gy) for `n` copies, float32, in cells: where each copy sits
    before `cell` scales it (`Renderer.draw_scene`, which asks only for
    n ≥ 2). A cell is the spacing between neighbours in every layout. Pure:
    no GL, no state.

    GRID (and any layout it does not know) — rows of ``ceil(sqrt(n))``,
    centred; the arithmetic `draw_scene` had inline, in the same order.
    HEX — a honeycomb spiral from the centre: whole hexagons at 7, 19, 37,
    61 and 91, and a copy never moves as the count grows.
    RING — one circle, copy 0 at the top, clockwise on screen (y is down),
    its radius ``1 / (2 sin(π / n))`` so neighbours stay one cell apart.

    No copies is two empty arrays and one copy is the centre, in every
    layout."""
    n = max(0, int(n))
    if n == 0:
        return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)
    if layout == LAYOUT_HEX:
        cells = _hex_spiral(n)
        return cells[:, 0].astype(np.float32), cells[:, 1].astype(np.float32)
    if layout == LAYOUT_RING:
        if n == 1:
            return np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.float32)
        radius = 1.0 / (2.0 * math.sin(math.pi / n))
        th = 2.0 * math.pi * np.arange(n, dtype=np.float64) / n
        return ((radius * np.sin(th)).astype(np.float32),
                (-radius * np.cos(th)).astype(np.float32))
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    k = np.arange(n, dtype=np.float32)
    gx = k % cols - (cols - 1) / 2      # grid position about the centre
    gy = k // cols - (rows - 1) / 2
    return gx, gy


def _samples_of(ctx: moderngl.Context, fbo: moderngl.Framebuffer) -> int:
    """The bound framebuffer's MSAA sample count. moderngl leaves `samples`
    unset on the detected default framebuffer, so the window is asked
    directly (GL_SAMPLES); a framebuffer we made knows its own."""
    if fbo is ctx.screen:
        try:
            from OpenGL import GL

            return int(GL.glGetIntegerv(GL.GL_SAMPLES)) if GL.glGetIntegerv(
                GL.GL_SAMPLE_BUFFERS) else 0
        except Exception:  # noqa: BLE001 — no PyOpenGL: draw without MSAA
            return 0
    return int(fbo.samples or 0)


def _readable_depth(ctx: moderngl.Context, size: tuple[int, int]) -> moderngl.Texture:
    """A depth texture a shader can read as a value: no comparison,
    nearest-sampled (attached, it is an ordinary depth buffer)."""
    t = ctx.depth_texture(size)
    t.compare_func = ""
    t.filter = (moderngl.NEAREST, moderngl.NEAREST)
    t.repeat_x = t.repeat_y = False
    return t


class SceneTarget:
    """The texture the scene is drawn into: RGBA8 at the output's pixel
    size, through an MSAA renderbuffer that resolves into it when the
    output is multisampled. Recreated on resize, DPI change, or a target
    with a different sample count.

    Plan 26 A2: and a depth attachment on the framebuffer the scene is
    drawn into — the shape's nearest visible surface (`Renderer._depth_pass`),
    for whatever is drawn after it in the shared camera (A3: the hands).
    Single-sampled it is a depth texture (`depth`), which a depth-aware
    composite can read; multisampled it is a renderbuffer beside the
    colour one (`depth` None: A3 resolves it when a node needs it)."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.size = (0, 0)
        self.samples = -1
        self.tex: moderngl.Texture | None = None
        self.fbo: moderngl.Framebuffer | None = None      # on the texture
        self._msaa: moderngl.Framebuffer | None = None    # on the renderbuffer, if any
        self.depth: moderngl.Texture | None = None        # single-sampled: the depth
        self._depth_rb = None                             # multisampled: its renderbuffer
        # plan 26 A3: multisampled, the depth resolved for a node that reads
        # it (`depth_texture`), made on first ask: a depth texture and the
        # framebuffer the blit lands in (a colour renderbuffer beside it,
        # as a blit wants one)
        self._rdepth: moderngl.Texture | None = None
        self._rfbo: moderngl.Framebuffer | None = None
        self._rcol = None

    def ensure(self, size: tuple[int, int], samples: int) -> None:
        if size == self.size and samples == self.samples and self.tex is not None:
            return
        self.release()
        self.size, self.samples = size, samples
        self.tex = self.ctx.texture(size, 4)
        self.tex.repeat_x = self.tex.repeat_y = False
        if samples > 0:
            self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])
            rb = self.ctx.renderbuffer(size, 4, samples=samples)
            self._depth_rb = self.ctx.depth_renderbuffer(size, samples=samples)
            self._msaa = self.ctx.framebuffer(color_attachments=[rb],
                                              depth_attachment=self._depth_rb)
        else:
            self.depth = _readable_depth(self.ctx, size)
            self.fbo = self.ctx.framebuffer(color_attachments=[self.tex],
                                            depth_attachment=self.depth)

    @property
    def draw_fbo(self) -> moderngl.Framebuffer:
        return self._msaa if self._msaa is not None else self.fbo

    def resolve(self) -> None:
        """After the scene pass: the multisampled draw into the texture."""
        if self._msaa is not None:
            self.ctx.copy_framebuffer(self.fbo, self._msaa)

    def depth_texture(self) -> moderngl.Texture | None:
        """The scene's depth as a texture a shader reads (plan 26 A3, a
        depth-aware composite): the depth attachment itself when single-
        sampled; multisampled, resolved now (one sample per pixel) into a
        texture made on first ask. Call it after the scene pass."""
        if self.tex is None:
            return None
        if self._msaa is None:
            return self.depth
        if getattr(self, "_rdepth", None) is None:
            self._rcol = self.ctx.renderbuffer(self.size, 4)
            self._rdepth = _readable_depth(self.ctx, self.size)
            self._rfbo = self.ctx.framebuffer(color_attachments=[self._rcol],
                                              depth_attachment=self._rdepth)
        self.ctx.copy_framebuffer(self._rfbo, self._msaa)
        return self._rdepth

    def release(self) -> None:
        # getattr: a target from before A2 has no depth, from before A3 no
        # resolved one
        for res in (self._msaa, self.fbo, self.tex, getattr(self, "depth", None),
                    getattr(self, "_depth_rb", None), getattr(self, "_rfbo", None),
                    getattr(self, "_rdepth", None), getattr(self, "_rcol", None)):
            if res is not None:
                res.release()
        self._msaa = self.fbo = self.tex = self.depth = self._depth_rb = None
        self._rfbo = self._rdepth = self._rcol = None
        self.size, self.samples = (0, 0), -1


class CoverTarget:
    """The faces' coverage mask: one channel at the scene's pixel size, 1
    where a face was drawn this frame. The look-back's occlusion reads it
    (lookback.py, u_cover); single-sampled — the wake behind it is soft."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.size = (0, 0)
        self.tex: moderngl.Texture | None = None
        self.fbo: moderngl.Framebuffer | None = None

    def ensure(self, size: tuple[int, int]) -> None:
        if size == self.size and self.tex is not None:
            return
        self.release()
        self.size = size
        self.tex = self.ctx.texture(size, 1)
        self.tex.repeat_x = self.tex.repeat_y = False
        self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])

    def release(self) -> None:
        for res in (self.fbo, self.tex):
            if res is not None:
                res.release()
        self.fbo = self.tex = None
        self.size = (0, 0)


class FaceTarget:
    """The picture the faces show while an effect is aimed at them (plan
    20): one RGBA8 texture, FACE_PIC square, premultiplied with alpha as
    the face's intensity, mipmapped — per face it lands on a face a
    hundred or so pixels across. Made on first use, never resized."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.tex: moderngl.Texture | None = None
        self.fbo: moderngl.Framebuffer | None = None

    def ensure(self) -> None:
        if self.tex is not None:
            return
        tex = self.ctx.texture((FACE_PIC, FACE_PIC), 4)
        try:
            tex.repeat_x = tex.repeat_y = False
            tex.build_mipmaps()
            tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            fbo = self.ctx.framebuffer(color_attachments=[tex])
        except Exception:
            tex.release()
            raise
        self.tex, self.fbo = tex, fbo

    def release(self) -> None:
        for res in (self.fbo, self.tex):
            if res is not None:
                res.release()
        self.fbo = self.tex = None


class PassTimer:
    """GPU time per node of the render graph (plan 26 A0, per pass; A1,
    per node): a ``ctx.query(time=True)`` around each node's work, read
    back `LAG` frames later so the CPU does not wait on the GPU for a
    result, and kept as a rolling median over the last `WINDOW` frames in
    ms (`medians`), in the graph's order.

    `end_frame(names)` takes the frame's node names (`Graph.timed`): a
    node that ran more than once (the history painted for two pipelines)
    is summed into its frame's total; one that did not run counts 0 that
    frame; a name no longer in the graph (an output closed, a pipeline
    gone with its switch) drops out of the medians. Time queries never
    nest (GL allows one active per target), so the nodes are timed side
    by side, never one inside another.

    A context with no timer queries (`ctx.query(time=True)` raises) leaves
    `on` false and `note` saying why; `time` is then a no-op and the frame
    is drawn as without it. A query that fails mid-run turns the timer off
    the same way: timing never costs a frame."""

    LAG = 3          # frames between a query's end and its read
    WINDOW = 60      # frames in the rolling median

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.on = False
        self.note = ""
        self._free: list = []
        self._frame: list[tuple[str, object]] = []          # this frame's (node, query)
        # frames ended, not yet read: (the frame's node names, its queries)
        self._pending: list[tuple[list[str], list[tuple[str, object]]]] = []
        self._ms: dict[str, list[float]] = {}
        try:
            q = ctx.query(time=True)
            with q:
                pass
            # reading it back syncs with the GPU once, per Renderer: the
            # price of knowing the context really has timer queries
            _ = q.elapsed
            self._free.append(q)
            self.on = True
        except Exception as e:  # noqa: BLE001 — no timer queries on this context
            self.note = f"no GPU timer queries on this context ({type(e).__name__})"

    def _off(self, e: Exception) -> None:
        """Timing off for good: the note, and every query freed. A query
        still active (begun, its pass running) is ended by its `_Timed`
        first, so only the rest are released here."""
        self.on = False
        self.note = f"GPU timing off: {type(e).__name__}: {e}"[:120]
        held = [q for _, q in self._frame] + [q for _, f in self._pending for _, q in f]
        self._frame, self._pending = [], []
        for q in held + self._free:
            try:
                q.release()
            except Exception:  # noqa: BLE001, S110 — a stand-in or a lost context: nothing to free
                pass
        self._free = []

    def time(self, name: str) -> _Timed:
        """``with timer.time("scene"):`` — the node's GPU time, this frame."""
        if not self.on:
            return _Timed(None)
        try:
            q = self._free.pop() if self._free else self.ctx.query(time=True)
        except Exception as e:  # noqa: BLE001 — a driver that runs out: timing off
            self._off(e)
            return _Timed(None)
        self._frame.append((name, q))
        return _Timed(q, self)

    def end_frame(self, names: tuple[str, ...] | list[str] = ()) -> None:
        """Once a frame, after the last node: this frame's queries wait;
        the frame `LAG` frames back is read into the medians. `names` are
        this frame's nodes in order: the lines the medians keep."""
        if not self.on:
            return
        self._pending.append((list(names), self._frame))
        self._frame = []
        while len(self._pending) > self.LAG:
            names, done = self._pending.pop(0)
            totals = dict.fromkeys(names, 0.0)
            try:
                for name, q in done:
                    # blocks if the result is still not there LAG frames on
                    # (moderngl has no availability query to ask first)
                    totals[name] = totals.get(name, 0.0) + q.elapsed / 1e6
                    self._free.append(q)
            except Exception as e:  # noqa: BLE001 — a read that fails: timing off
                self._off(e)
                return
            ms_by: dict[str, list[float]] = {}
            for name, ms in totals.items():
                window = ms_by[name] = self._ms.get(name, [])
                window.append(ms)
                del window[:-self.WINDOW]
            self._ms = ms_by             # that frame's nodes, in its order

    def medians(self) -> dict[str, float]:
        """Node → median ms over the window, in the graph's order; empty
        until the first frame has been read back, and with no timer."""
        return {name: float(np.median(w)) for name, w in self._ms.items() if w}


class _Timed:
    """One node's query as a context manager; nothing with no query. A
    query whose begin or end raises turns the timer off, never the frame."""

    __slots__ = ("began", "q", "timer")

    def __init__(self, q, timer: PassTimer | None = None):
        self.q, self.timer, self.began = q, timer, False

    def __enter__(self) -> Self:
        if self.q is not None:
            try:
                self.q.__enter__()
                self.began = True
            except Exception as e:  # noqa: BLE001 — timing never costs a frame
                self.timer._off(e)
        return self

    def __exit__(self, *exc) -> bool:
        if self.began:
            try:
                self.q.__exit__(None, None, None)
            except Exception as e:  # noqa: BLE001 — timing never costs a frame
                self.timer._off(e)
        return False


class Renderer:
    def __init__(self, ctx: moderngl.Context, dream: DreamState | None = None,
                 fx: FxState | None = None, ghost: GhostState | None = None):
        self.ctx = ctx
        # clear alpha: 1 is the opaque black ground; overlay mode lowers it
        # so whatever is behind the window shows through (overlay.py)
        self.bg_alpha = 1.0
        # the master dim (overlay.Output.dim, handed over each frame by
        # app.frame): 1 is the frame as drawn, 0 is black. Its program is
        # built on first use (dim_pass); dim_error says why it could not be
        self.dim = 1.0
        self.dim_error = ""
        # the render cap (overlay.Output.max_frame, output.render, handed
        # over each frame by app.frame): the frame fits inside it; None, no
        # cap — the frame is output 1's framebuffer, as before
        self.max_frame: tuple[int, int] | None = None
        self._dim_prog: moderngl.Program | None = None
        self._dim_vao: moderngl.VertexArray | None = None
        # the scene texture and the look-back post pass over it; the blank
        # texture takes the sampler units before the scene pass, so the
        # scene texture is never bound while it is the render target
        self.scene = SceneTarget(ctx)
        self.lookback = Lookback(ctx, dream)
        self.fx = FxChain(ctx, fx)      # the effect stack after the post pass
        # the effects aimed at the faces: a second chain over the same
        # state, borrowing the first's programs, and the picture it ends
        # on. Nothing is allocated until an effect is aimed at the faces.
        # face_error says why a face pass could not run (the frame is then
        # drawn as with no face effect); _pic is the picture _draw_frame
        # hands the one scene pass it wraps
        self.face_fx = FxChain(ctx, self.fx.state, target=FACES, programs=self.fx)
        self.face_pic = FaceTarget(ctx)
        self.face_error = ""
        self._pic: moderngl.Texture | None = None
        self.ghost = Ghost(ctx, ghost)  # the hands, last, over everything (ghost.py)
        # plan 21: the outputs. A pipeline with more than one consumer (or
        # one not drawn here) ends in a frame texture, one per pipeline key,
        # made on first use; the program that shows one on an output, too.
        # `stats` is what the last frame ran
        self._frames: dict[int, tuple[moderngl.Texture, moderngl.Framebuffer]] = {}
        self._show_prog: moderngl.Program | None = None
        self._show_vao: moderngl.VertexArray | None = None
        # plan 26 A3: the program a Composite node lays a layer with, on
        # first use; and the wiring the default graph is built from (where
        # the hands are drawn, how their layer is laid on, what the history
        # captures) — today's frame until A4 reads one from a preset
        self._lay_prog: moderngl.Program | None = None
        self._lay_vao: moderngl.VertexArray | None = None
        self.wiring = Wiring()
        # plan 26 A4b: what the point-cloud nodes read — the device
        # registry (app hands it over; duck-typed: `clouds` and its
        # devices' kinds). None: no cloud is drawn
        self.cloud_source = None
        # plan 26 A4: the extra hands nodes' states, by node name (`ghost.2`
        # …), handed over by whoever declared their params (the preset's
        # graph section, `preset.GraphSection`); their Ghosts, made on
        # first use (`ghost_of`)
        self.ghost_states: dict[str, GhostState] = {}
        self._ghosts: dict[str, Ghost] = {}
        # plan 26 A4b: the cloud nodes' GL (`graph._CloudGL`), made on first
        # draw; the getattr guards stay for a hot-reloaded renderer
        self._cloud_gl = None
        self.stats: dict = {"pipelines": [], "chain_runs": 0, "direct": True}
        # plan 26 A0: GPU time per node, `stats["gpu_ms"]` (the SYSTEM page)
        self.timer = PassTimer(ctx)
        # plan 26 A1: the render graph for the last frame's views, reused
        # while their switches do not change (graph.graph_key)
        self._graph: Graph | None = None
        self.cover = CoverTarget(ctx)
        self._face_verts = 0           # face vertices in _fbuf from the last scene pass
        self._scene_mats = (b"", b"")  # …and the camera they were drawn in (u_vp, u_model)
        self._blank = ctx.texture((1, 1), 4)
        self._lbuf = ctx.buffer(reserve=1200 * 2 * 3 * 4, dynamic=True)
        self._pbuf = ctx.buffer(reserve=600 * 4 * 4, dynamic=True)
        self._fbuf = ctx.buffer(reserve=2160 * 3 * 7 * 4, dynamic=True)
        self._build_wire_programs()
        # bitmap layer over the faces, loaded from disk on demand
        self.bitmap_error = ""
        self._bmp_tex: moderngl.Texture | None = None
        self._bmp_file = ""
        # face program is assembled around the user-editable patterns.glsl
        self.pattern_error = ""
        self._face_prog: moderngl.Program | None = None
        self._fvao: moderngl.VertexArray | None = None
        self._seed_prog: moderngl.Program | None = None    # the face picture's first pass
        self._seed_vao: moderngl.VertexArray | None = None
        self._patterns_mtime = (0.0, 0.0)   # (patterns.glsl, _common.glsl)
        self._reload_check = 0
        self._t0 = time.perf_counter()   # the one wall clock: patterns, instances, effects
        # the analyzer's lanes, normalized, set by the app each frame (app._bands):
        # render input for the patterns that draw the bands (u_levels)
        self.bands: tuple[float, ...] = ()
        self._ptime = 0.0                  # the patterns' clock (_pattern_clock) …
        self._ptime_at: float | None = None   # … and the wall time it was last moved to
        self._ptile: tuple | None = None   # the tiles' program, vao, and the mtimes it read
        self._tile_fbos: dict[int, moderngl.Framebuffer] = {}   # pattern_tile's, by size
        # the FACES page's swatches (want_swatches): mode → (texture, framebuffer)
        self._swatches: dict[int, tuple] = {}
        self._swatch_frame = self._swatch_until = self._swatch_next = 0
        self.swatch_error = ""
        self._build_face_program()
        ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def _build_wire_programs(self) -> None:
        """Compile the line, point and coverage programs and their VAOs; the
        live ones are replaced only once every new one exists, so a shader
        edit that fails to compile leaves the last good set drawing."""
        ctx = self.ctx
        made: list = []          # released again if a later step raises
        try:
            lines = ctx.program(vertex_shader=LINE_VS, fragment_shader=LINE_FS)
            made.append(lines)
            points = ctx.program(vertex_shader=POINT_VS, fragment_shader=POINT_FS)
            made.append(points)
            points["u_color"].value = RED
            lvao = ctx.vertex_array(lines, [(self._lbuf, LINE_FORMAT, "in_a", "in_b",
                                             "in_corner", "in_width", "in_alpha")])
            made.append(lvao)
            # the coverage pass reads the face buffer's position and divisor only
            cover_prog = ctx.program(vertex_shader=COVER_VS, fragment_shader=COVER_FS)
            made.append(cover_prog)
            cvao = ctx.vertex_array(cover_prog,
                                    [(self._fbuf, "3f 1f 16x", "in_pos", "in_w4")])
            made.append(cvao)
            pvao = ctx.vertex_array(points, [(self._pbuf, POINT_FORMAT, "in_pos", "in_corner",
                                              "in_size", "in_alpha")])
        except Exception:
            for res in made:
                res.release()
            raise
        self._lines, self._points, self._lvao, self._cover_prog, self._cvao, self._pvao = (
            lines, points, lvao, cover_prog, cvao, pvao)

    def on_reload(self) -> None:
        """Hot-swap hook (hotreload.py): recompile every GL program so edits
        to the shader strings in this module land; the buffers persist. The
        old programs are released only after the new ones compiled, so a
        bad edit keeps the last good set (the face program already does
        this). An attribute a newer __init__ would have added is missing
        until a restart, and the reloader reports the AttributeError rather
        than this hook guessing at a value (audit H3)."""
        olds = (self._lvao, self._pvao, self._cvao, self._lines, self._points, self._cover_prog)
        self._build_wire_programs()
        for res in olds:
            res.release()
        self._build_face_program()
        # the faces' chain and its picture are made again from the modules
        # as they are now (app.py's reloader does not re-class them); they
        # hold a copy program and three textures, rebuilt on next use. A
        # renderer from before the face target existed gets them here
        old_fx, old_pic = getattr(self, "face_fx", None), getattr(self, "face_pic", None)
        self.face_fx = FxChain(self.ctx, self.fx.state, target=FACES, programs=self.fx)
        self.face_pic = FaceTarget(self.ctx)
        self.face_error = ""
        self._pic = None
        for res in (old_fx, old_pic):
            if res is not None:
                res.release()
        # not the ghost hands': their programs live in ghost.py, and the
        # reloader calls `Ghost.on_reload` itself whenever ghost.py (or a
        # module before it) changed — calling it here too rebuilt them twice
        # in one round, and again on a save that never touched them
        # the dim's program: dropped, and built again from this module's
        # current source the next frame that dims (an edit may also have
        # fixed what would not build). getattr: a renderer made before the
        # dim existed has none of these
        for res in (getattr(self, "_dim_vao", None), getattr(self, "_dim_prog", None)):
            if res is not None:
                res.release()
        self._dim_prog = self._dim_vao = None
        self.dim_error = ""
        # plan 21's frame textures and the program that shows them: dropped,
        # made again from this module's source on next use. getattr: a
        # renderer from before the outputs existed has none of them
        self._release_frames()
        # plan 26 A1: the graph is built again from graph.py as it is now
        # (its nodes are not re-classed; they hold no GL resources), and so
        # is the timer — the one from before the reload is this module's
        # old `PassTimer`, with an `end_frame` of another shape
        self._graph = None
        self._drop_timer()
        # plan 26 A4b: the point clouds' program and buffers, made again
        # from graph.py's source on the next frame that draws a cloud
        if getattr(self, "_cloud_gl", None) is not None:
            self._cloud_gl.release()
        self._cloud_gl = None
        # plan 26 A4: an extra hands node's Ghost is not a reload target
        # (the reloader re-classes the renderer's own): released, and made
        # again from ghost.py as it is now on next use, over the same state
        self.drop_ghosts()
        for res in (getattr(self, "_show_vao", None), getattr(self, "_show_prog", None),
                    getattr(self, "_lay_vao", None), getattr(self, "_lay_prog", None)):
            if res is not None:
                res.release()
        self._show_prog = self._show_vao = self._lay_prog = self._lay_vao = None
        # the tiles' and swatches' program: its head and tail are this
        # module's strings, so it is made again from them on next use
        # (patterns.glsl's own saves rebuild it by mtime)
        for res in (getattr(self, "_ptile", None) or ())[:2]:
            if res is not None:
                res.release()
        self._ptile = None

    def _sync_bitmap(self, path: str) -> None:
        """(Re)load the overlay texture when the selected file changes."""
        if path == self._bmp_file:
            return
        self._bmp_file = path
        if self._bmp_tex is not None:
            self._bmp_tex.release()
            self._bmp_tex = None
        self.bitmap_error = ""
        if not path:
            return
        try:
            from PIL import Image

            img = Image.open(path).convert("RGBA")
            self._bmp_tex = self.ctx.texture(img.size, 4, img.tobytes())
            self._bmp_tex.build_mipmaps()
            self._bmp_tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        except Exception as e:  # noqa: BLE001 — a bad file must not kill the app
            self.bitmap_error = str(e).strip().splitlines()[-1][:160]

    def _build_face_program(self) -> None:
        """The face program and the seed program (the face picture's first
        pass), from one read of patterns.glsl: replaced together or not at
        all, so the picture is always what the faces would have drawn."""
        ctx = self.ctx
        made: list = []          # released again if a later step raises
        try:
            src = PATTERNS_GLSL.read_text()
            self._patterns_mtime = self._shader_mtime()
            prog = ctx.program(vertex_shader=FACE_VS,
                               fragment_shader=_face_fragment(FACE_FS_HEAD, src, FACE_FS_TAIL))
            made.append(prog)
            seed = ctx.program(vertex_shader=QUAD_VS,
                               fragment_shader=_face_fragment(SEED_FS_HEAD, src, SEED_FS_TAIL))
            made.append(seed)
            fvao = ctx.vertex_array(
                prog,
                [(self._fbuf, FACE_FORMAT, "in_pos", "in_w4", "in_uv", "in_alpha", "in_fid")],
            )
            made.append(fvao)
            svao = ctx.vertex_array(seed, [])
        except Exception as e:  # noqa: BLE001 — a bad edit must not kill the app
            for res in made:
                res.release()
            self.pattern_error = gl_error(e, {1: "_common.glsl:", 2: "patterns.glsl:"})
            return
        # getattr: a renderer from before the seed existed has neither
        for res in (self._fvao, getattr(self, "_seed_vao", None), self._face_prog,
                    getattr(self, "_seed_prog", None)):
            if res is not None:
                res.release()
        self._face_prog, self._fvao, self._seed_prog, self._seed_vao = prog, fvao, seed, svao
        prog["u_pic"].value = 1          # its own unit: the bitmap has 0
        self.pattern_error = ""

    def now(self, t_now: float | None = None) -> float:
        """Seconds on the renderer's clock, or `t_now` when a caller pins it."""
        return t_now if t_now is not None else time.perf_counter() - self._t0

    @staticmethod
    def _shader_mtime() -> tuple[float, float]:
        """patterns.glsl's and _common.glsl's mtimes — both, so a save of
        either is a change even when it does not move the newer one."""
        return PATTERNS_GLSL.stat().st_mtime, common_mtime()

    def _maybe_reload_patterns(self) -> None:
        """Every 30 frames: rebuild the face program when patterns.glsl or
        _common.glsl was saved — also after a build that failed, so a fix
        lands — and have the look-back recompile on a _common.glsl save."""
        self._reload_check += 1
        if self._reload_check % 30:
            return
        try:
            mtime = self._shader_mtime()
        except OSError:
            return
        if mtime != self._patterns_mtime:
            shared_changed = mtime[1] != self._patterns_mtime[1]
            self._patterns_mtime = mtime
            self._build_face_program()
            if shared_changed:
                self.lookback.on_reload()

    def draw(
        self, s: ViewState, w: int, h: int, dpr: float = 1.0,
        t_now: float | None = None,
    ) -> None:
        """One frame at logical size (w, h) into the bound framebuffer's
        viewport; dpr scales point sizes only — positions are logical and
        the viewport handles resolution. The scene goes to its texture,
        then the post pass (lookback.py) puts it on the target. `t_now`
        pins the clock (offscreen renders and tests); otherwise the frame
        reads the renderer's own, and the patterns, the instance motion
        and the effect chain all see the same second.

        The target is captured once and bound again, with its viewport and
        blending, on every exit — a raise included. The frame binds half a
        dozen offscreen framebuffers; one left bound made every later
        frame draw into it while the window swapped a stale picture (the
        owner's freeze, plan 14 WP1: WAKE without a dream worker left the
        look-back's atlas bound, with no error anywhere)."""
        ctx = self.ctx
        target = ctx.fbo
        if target is None:
            raise RuntimeError("Renderer.draw: no framebuffer bound (call fbo.use())")
        vp = tuple(target.viewport)
        # one output, today's: the default switches on the bound framebuffer
        view = View(Switches(), (vp[2], vp[3]), target=target,
                    bg_alpha=getattr(self, "bg_alpha", 1.0), viewport=vp)
        self.draw_outputs(s, w, h, dpr, [view], t_now)
        if view.exc is not None:
            # what the view caught is raised here, as it was before there
            # were views — the frame finished, the dim ran, the target bound
            raise view.exc

    def draw_outputs(self, s: ViewState, w: int, h: int, dpr: float, views: list[View],
                     t_now: float | None = None) -> None:
        """One frame, a picture per output (plan 21 WP1): `views[0]` is the
        first output — a framebuffer on this context; its rect sets the
        frame's size and its framebuffer the scene's sample count (fork
        F12) — and every view shows that frame through its own switches.

        Once a frame: the face picture, the scene pass, the cover, the
        look-back's tick and pull, the hands' layer (only while some view
        shows hands), the look-back's capture (from the scene texture,
        exactly once, whatever the switches). Once per distinct pipeline
        (`outputs.route`): the look-back composite and the effect chain,
        ending straight on the view when it is the pipeline's only
        consumer at the frame size, else in a frame texture. Once per
        view: the picture (nothing, a 1:1 copy, or scaled into
        `outputs.fit`'s rect with the rest cleared to the view's ground),
        the hands over it, the dim (master × the view's). A view with a
        `presenter` instead of a `target` is left a `Handoff`.

        A view that raises records `view.error` (and `view.exc`) and the
        loop goes on to the next; a pipeline that raises records it on its
        views, which show their ground; the hands failing never costs the
        frame or the dim (`Ghost.error`). Every exit — a raise in the
        once-a-frame passes included — binds `views[0].target` again with
        its rect and blending. `stats` says what ran."""
        if not views or views[0].target is None:
            raise RuntimeError("Renderer.draw_outputs: the first view needs a target "
                               "on this context")
        ctx = self.ctx
        t = self.now(t_now)
        for v in views:
            v.error, v.exc, v.handoff = "", None, None
        first = views[0]
        target, vp = first.target, first.rect
        try:
            if self._swatch_step(s, t):          # it bound its own: the target again
                target.use()
                ctx.viewport = vp
            self._draw_frame(s, w, h, dpr, t, views)
        finally:
            target.use()
            ctx.viewport = vp
            ctx.enable(moderngl.BLEND)

    def _pass_timer(self) -> PassTimer:
        """The GPU node timer (getattr: a renderer from before a hot reload
        has none, and gets one). A timer of another class — this module's
        `PassTimer` as it was before a reload, whose `end_frame` and
        pending frames have the old shape — is dropped for a fresh one:
        the timer is not a reload target, only the renderer is."""
        timer = getattr(self, "timer", None)
        if timer is None or type(timer) is not PassTimer:
            self._drop_timer()
            timer = self.timer = PassTimer(self.ctx)
        return timer

    def _drop_timer(self) -> None:
        """Free the timer's queries, whatever shape it has (its own `_off`
        knows), and forget it; best-effort — a timer never costs a frame."""
        timer = getattr(self, "timer", None)
        self.timer = None
        off = getattr(timer, "_off", None)
        if off is not None:
            try:
                off(RuntimeError("replaced"))
            except Exception:  # noqa: BLE001, S110 — a stand-in or a lost context: nothing to free
                pass

    def _timed(self, name: str) -> _Timed:
        """``with self._timed("fx"):`` — the pass's GPU time (plan 26 A0)."""
        return self._pass_timer().time(name)

    def _draw_frame(self, s: ViewState, w: int, h: int, dpr: float, t: float,
                    views: list[View]) -> None:
        """draw_outputs()'s body (plan 26 A1): the frame's size under the
        render cap, the chain's clocks, then the render graph for these
        views — built from their switches, or the last frame's while they
        have not changed — evaluated once, every node timed on the GPU
        (`PassTimer`): `stats["gpu_ms"]` is each node's rolling median in
        ms and `stats["gpu_note"]` why there is none, whatever the frame
        did.

        What the nodes run is the frame as it was: the face picture (only
        while an effect is aimed at the faces), the scene, the cover, the
        hands' layer, each pipeline once (the look-back composite, the
        hands onto it, the effects), the capture, then each view's
        picture, the ghost hands over it and its dim."""
        ctx = self.ctx
        first = views[0]
        target = first.target
        vp = first.rect
        # the frame's size: output 1's framebuffer under the render cap
        # (`max_frame`, output.render; getattr: a renderer from before the
        # cap has none). Capped, output 1 is no longer drawn direct — it is
        # shown scaled like any output of another size — and the scene's
        # strokes keep their on-screen width through a dpr scaled alike
        full = (max(vp[2], 1), max(vp[3], 1))
        size = capped(full, getattr(self, "max_frame", None))
        dpr *= size[0] / full[0]
        target.viewport = vp
        # the chain's folder watch and ground, once a frame, before the
        # graph: whether an effect is on steers the hands' readout and the
        # routes. An opaque ground keeps the whole chain at alpha 1 (plan
        # 14 WP1)
        fx = self.fx
        fx.tick()
        fx.opaque = getattr(self, "bg_alpha", 1.0) >= 1.0
        stats = {"pipelines": [], "chain_runs": 0, "direct": True, "captures": 0,
                 "effects": [], "layer": False, "readout": False,
                 "routes": [(None, False)] * len(views)}
        self.stats = stats
        graph = self._graph_for(views)
        # plan 30 D1: "an effect is on" means one of the chain's runs: an
        # effect the preset placed on an edge runs there (and moves its
        # clock in `run_one`) but bends no pipeline, so with only placed
        # effects on a through output stands down as with none
        placed = getattr(graph, "placed_names", frozenset())
        fx_on = any(n not in placed for n in fx.state.chain(getattr(fx, "target", 0)))
        stats["fx_on"] = fx_on
        frame = Frame(self, ctx, s, w, h, dpr, t, views, size, _samples_of(ctx, target),
                      target, vp, bg_alpha=getattr(self, "bg_alpha", 1.0), fx_on=fx_on,
                      stats=stats)
        timer = self._pass_timer()
        try:
            graph.evaluate(frame)
        finally:
            timer.end_frame(graph.timed_in(frame))
            stats["gpu_ms"] = timer.medians()
            stats["gpu_note"] = timer.note

    def _graph_for(self, views: list[View]) -> Graph:
        """The render graph for these views: the last one while their
        switches and the wiring have not changed (`graph.graph_key`,
        `Renderer.wiring`), else the default graph built from them
        (`graph.default_graph`). getattr: a renderer from before the graph
        (or the wiring) has none. Plan 26 A4b: the `cloud` devices the
        registry lists (`cloud_source`) are part of the key, so listing
        one adds its point-cloud node to the scene. Plan 30 D0: so is the
        effect stack's list in order (`FxState.names()`): each pipeline's
        run of effect nodes is built from it, and an effect switched on or
        off changes nothing here (an off node reads through). A new graph
        fits the effects' texture pool to what it needs (`Graph.pool`)."""
        key = graph_key(views)
        wiring = getattr(self, "wiring", None) or Wiring()
        clouds = cloud_roles(getattr(self, "cloud_source", None))
        fx = getattr(self, "fx", None)
        effects = tuple(fx.state.names()) if fx is not None else ()
        graph = getattr(self, "_graph", None)
        if (graph is None or graph.key != key or getattr(graph, "wiring", None) != wiring
                or getattr(graph, "clouds", ()) != clouds
                or getattr(graph, "effects", ()) != effects):
            graph = self._graph = default_graph(views, wiring, clouds, effects)
            if fx is not None and hasattr(fx, "fit_pool"):
                fx.fit_pool(graph.pool)
            # plan 26 A4: a second hands node's Ghost the new graph does
            # not hold goes with the old graph
            self.drop_ghosts({n for n in graph.nodes if n.startswith("ghost.")})
        return graph

    def _compose(self, v: View, key: int | None, after: bool,
                 frames: dict[int, moderngl.Texture | None], failed: set[int],
                 size: tuple[int, int], readout: moderngl.Texture | None = None,
                 lay=None, blend: str = "over", ghost: Ghost | None = None,
                 readout_ghost: Ghost | None = None,
                 hands_tex: moderngl.Texture | None = None) -> None:
        """One view's picture: the pipeline's frame (`key`, the pipeline its
        end node closes, `outputs.SCENE` …; already there when it was drawn
        direct), the hands over it in the same rect, the readout layer over
        that when there is one, its dim. `lay(target, rect, opaque, flip)`
        lays the hands when the output's wiring is not plain over (plan 26
        A3: add, depth-aware); a presenter's hand-off carries `blend` and
        honours add, and lays a depth-aware layer plain over (the depths
        stay in this context). `ghost` is the Ghost whose layer is laid
        over and `readout_ghost` the one whose readout goes on (plan 26 A4:
        each hands node's own; the renderer's when None). `hands_tex` (plan
        30 D1): the picture of the hands laid over when it is not the
        Ghost's own layer — an effect placed after the hands folds it — for
        a presenter's hand-off (a target view lays it through `lay`)."""
        ctx = self.ctx
        gh = ghost if ghost is not None else self.ghost
        rg = readout_ghost if readout_ghost is not None else gh
        factor = clamp(getattr(self, "dim", 1.0) * float(v.switches.dim), 0.0, 1.0)
        # plan 23 WP1: this output's mirror, its last step — the frame, the
        # hands laid after and the readout, never the hands-through pass
        # (the graph's Composite node, inside the frame this flips whole)
        flip = (bool(getattr(v.switches, "flip_x", False)),
                bool(getattr(v.switches, "flip_y", False)))
        frame = None if key is None or key in failed else frames.get(key)
        if v.target is None:
            if v.presenter is None:
                raise RuntimeError("a view needs a target or a presenter")
            rx, ry, rw, rh = v.rect
            ix, iy, iw, ih = fit(size, (rw, rh))
            v.handoff = Handoff(frame, size, (rx + ix, ry + iy, iw, ih),
                                hands=((hands_tex if hands_tex is not None else gh.tex)
                                       if after else None), readout=readout,
                                alpha=float(gh.state.alpha), factor=factor,
                                bg_alpha=float(v.bg_alpha), flip=flip,
                                blend="add" if blend == "add" else "over")
            return
        tgt, rect = v.target, v.rect
        opaque = v.bg_alpha >= 1.0
        fx_, fy, fw, fh = fit(size, rect[2:])
        inner = (rect[0] + fx_, rect[1] + fy, fw, fh)
        if key is None or key in failed:
            tgt.use()
            ctx.viewport = rect
            ctx.clear(0.0, 0.0, 0.0, float(v.bg_alpha), viewport=rect)
        elif frame is not None:
            self._show(tgt, rect, inner, frame, size, opaque, float(v.bg_alpha), flip)
        # the hands last, onto the target: no effect, echo or dream touches
        # them and the history (captured from the scene) never holds them
        if after or readout is not None:
            try:
                if after and lay is not None:
                    lay(tgt, inner, opaque, flip)
                elif after:
                    gh.composite(tgt, inner, opaque=opaque, flip=flip)
                if readout is not None:      # the guide and its labels, never bent
                    rg.composite_readout(tgt, inner, opaque=opaque, flip=flip)
            except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
                self._hands_failed(e, tgt, rect)
        # the dim, after everything: the scene, the look-back, every effect
        # and the hands dim alike, and the history and the dream worker
        # never hold it. At 1 the pass does not run and the frame is
        # bit-identical
        dim = getattr(self, "dim", 1.0) * float(v.switches.dim)
        if dim < 1.0:
            self.dim_pass(tgt, rect, dim, opaque=opaque)

    def _show(self, tgt: moderngl.Framebuffer, rect: tuple, inner: tuple,
              tex: moderngl.Texture, size: tuple[int, int], opaque: bool,
              bg_alpha: float, flip: tuple[bool, bool] = (False, False)) -> None:
        """A frame texture onto `tgt`: 1:1 when `inner` is the frame's size,
        else scaled into `inner` with the rest of `rect` the ground;
        mirrored inside `inner` by `flip` (x, y; plan 23 WP1)."""
        prog, vao = self._show_program()
        ctx = self.ctx
        tgt.use()
        if tuple(inner) != tuple(rect):
            ctx.clear(0.0, 0.0, 0.0, bg_alpha, viewport=rect)
        ctx.viewport = inner
        ctx.disable(moderngl.BLEND)
        try:
            tex.use(location=0)
            prog["u_src"].value = 0
            prog["u_scaled"].value = int(tuple(inner[2:]) != tuple(size))
            prog["u_origin"].value = (int(inner[0]), int(inner[1]))
            prog["u_opaque"].value = int(opaque)
            prog["u_flip"].value = (int(bool(flip[0])), int(bool(flip[1])))
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)

    def _show_program(self) -> tuple[moderngl.Program, moderngl.VertexArray]:
        """The program that shows a frame texture, built on first use;
        getattr: a renderer from before the outputs has none."""
        prog, vao = getattr(self, "_show_prog", None), getattr(self, "_show_vao", None)
        if prog is not None and vao is not None:
            return prog, vao
        prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=SHOW_FS)
        try:
            vao = self.ctx.vertex_array(prog, [])
        except Exception:
            prog.release()
            raise
        self._show_prog, self._show_vao = prog, vao
        return prog, vao

    def lay(self, tex: moderngl.Texture | None, target: moderngl.Framebuffer, rect: tuple,
            blend: str = "over", alpha: float = 1.0, opaque: bool = True,
            flip: tuple[bool, bool] = (False, False), depth: moderngl.Texture | None = None,
            scene_depth: moderngl.Texture | None = None) -> bool:
        """A layer (`tex`, premultiplied, frame-sized) into `target`'s
        `rect` at `alpha` (plan 26 A3, the Composite node's blend): "over"
        — `Ghost.composite`'s blend and arithmetic, the same bytes — "add",
        or "depth": over, hidden where `scene_depth` is nearer than the
        layer's own `depth` (`LAYER_FS`, `LAYER_DEPTH_BIAS`; plain over when
        either depth is missing). On an opaque ground the target's alpha is
        left as it is; on a see-through one the layer adds its coverage
        (add: its colour only). Leaves `target` bound with `rect` and the
        frame's blend on, a raise included. False when there is no layer."""
        if tex is None:
            return False
        prog, vao = self._lay_program()
        ctx = self.ctx
        aware = blend == "depth" and depth is not None and scene_depth is not None
        try:
            target.use()
            ctx.viewport = tuple(rect)
            ctx.enable(moderngl.BLEND)
            one, inv = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
            if blend == "add":
                ctx.blend_func = ((one, one, moderngl.ZERO, one) if opaque else
                                  (one, one, one, inv))
            else:
                ctx.blend_func = ((one, inv, moderngl.ZERO, one) if opaque else
                                  (one, inv, one, inv))
            tex.use(location=0)
            prog["u_layer"].value = 0
            prog["u_alpha"].value = float(alpha)
            prog["u_flip"].value = (int(bool(flip[0])), int(bool(flip[1])))
            prog["u_depth_on"].value = int(aware)
            if aware:
                depth.use(location=1)
                scene_depth.use(location=2)
                prog["u_layer_depth"].value = 1
                prog["u_scene_depth"].value = 2
                prog["u_clip"].value = (float(EYE_NEAR), float(EYE_FAR))
                prog["u_bias"].value = float(LAYER_DEPTH_BIAS)
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            target.use()
            ctx.viewport = tuple(rect)
        return True

    def _lay_program(self) -> tuple[moderngl.Program, moderngl.VertexArray]:
        """`lay`'s program, built on first use (getattr: a renderer from
        before A3 has none)."""
        prog, vao = getattr(self, "_lay_prog", None), getattr(self, "_lay_vao", None)
        if prog is not None and vao is not None:
            return prog, vao
        prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=LAYER_FS)
        try:
            vao = self.ctx.vertex_array(prog, [])
        except Exception:
            prog.release()
            raise
        self._lay_prog, self._lay_vao = prog, vao
        return prog, vao

    def _frame_target(self, key, size: tuple[int, int]
                      ) -> tuple[moderngl.Texture, moderngl.Framebuffer]:
        """The frame texture for a pipeline: RGBA8 at the frame's size,
        LINEAR (a 1:1 show reads it by texelFetch), made on first use and
        again when the frame's size changes."""
        frames = getattr(self, "_frames", None)
        if frames is None:
            frames = self._frames = {}
        have = frames.get(key)
        if have is not None and have[0].size == size:
            return have
        if have is not None:
            for res in (have[1], have[0]):
                res.release()
            del frames[key]
        tex = self.ctx.texture(size, 4)
        try:
            tex.repeat_x = tex.repeat_y = False
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            fbo = self.ctx.framebuffer(color_attachments=[tex])
        except Exception:
            tex.release()
            raise
        frames[key] = (tex, fbo)
        return tex, fbo

    def _release_frames(self) -> None:
        for tex, fbo in (getattr(self, "_frames", None) or {}).values():
            fbo.release()
            tex.release()
        self._frames = {}

    def _hands_failed(self, e: Exception, target: moderngl.Framebuffer, vp: tuple,
                      ghost: Ghost | None = None) -> None:
        """The hands raised: say why (the first reason, kept, on the hands
        node's own `ghost`, the renderer's when None) and put back the
        state the frame's other passes expect."""
        gh = ghost if ghost is not None else self.ghost
        if not gh.error:
            gh.error = f"ghost hands: {type(e).__name__}: {e}"[:160]
        self._rebind(target, vp)

    def ghost_of(self, name: str) -> Ghost:
        """The `Ghost` that draws hands node `name` (plan 26 A4): `ghost` is
        the renderer's own (`self.ghost`, `ghost.*`); another (`ghost.2` …)
        is made on first ask over its state in `ghost_states` — the one the
        registry's `ghost.2.*` params write (`preset.GraphSection`), a
        fresh one when none was handed over — and follows the first's
        tracker and routing table. A state handed over again later
        replaces the Ghost. getattr: a renderer from before A4."""
        if name == "ghost":
            return self.ghost
        ghosts = self.__dict__.setdefault("_ghosts", {})
        state = (getattr(self, "ghost_states", None) or {}).get(name)
        gh = ghosts.get(name)
        if gh is None or (state is not None and gh.state is not state):
            if gh is not None:
                gh.release()
            gh = ghosts[name] = Ghost(self.ctx, state if state is not None else GhostState())
        gh.source, gh.router = self.ghost.source, self.ghost.router
        return gh

    def drop_ghosts(self, keep: set[str] = frozenset()) -> None:
        """Release every extra hands node's `Ghost` not named in `keep`
        (a graph that no longer holds it, a hot reload)."""
        ghosts = getattr(self, "_ghosts", None) or {}
        for name in [n for n in ghosts if n not in keep]:
            ghosts.pop(name).release()

    @staticmethod
    def _view_failed(v: View, what: str, e: Exception) -> None:
        if not v.error:
            v.error, v.exc = f"{what}: {type(e).__name__}: {e}"[:160], e

    def _rebind(self, target: moderngl.Framebuffer, vp: tuple) -> None:
        ctx = self.ctx
        ctx.disable(moderngl.DEPTH_TEST)
        target.use()
        ctx.viewport = tuple(vp)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def _face_picture(self, s: ViewState, t: float) -> moderngl.Texture | None:
        """The picture the faces show this frame, or None for "as ever":
        the seed (what face 0 shows: pattern and bitmap, premultiplied by
        its intensity) into the faces' chain, every effect aimed at the
        faces over it, the last one into the picture's texture, then its
        mipmaps.

        None, with nothing run and nothing allocated, unless an effect
        aimed at the faces is running, the faces are on, there is a copy to
        draw and the face program built. A pass that raises is caught
        here: `face_error` says why, the frame is drawn as with no face
        effect, and the caller binds the scene's framebuffer next whatever
        this left bound."""
        # getattr: a renderer from before a hot reload has no face chain
        chain = getattr(self, "face_fx", None)
        pic = getattr(self, "face_pic", None)
        seed, vao = getattr(self, "_seed_prog", None), getattr(self, "_seed_vao", None)
        if (chain is None or pic is None or seed is None or vao is None
                or self._face_prog is None or not s.faces or int(s.instances) <= 0
                or not chain.active()):
            self.face_error = ""     # no pass asked for: nothing is wrong with it
            return None
        ctx = self.ctx
        try:
            first = chain.begin((FACE_PIC, FACE_PIC))
            pic.ensure()
            first.use()
            ctx.viewport = (0, 0, FACE_PIC, FACE_PIC)
            ctx.disable(moderngl.BLEND)
            self._face_uniforms(seed, s, t)
            vao.render(moderngl.TRIANGLES, vertices=3)
            chain.run(pic.fbo, t)
            pic.tex.build_mipmaps()
        except Exception as e:  # noqa: BLE001 — the faces' effects must not take the frame down
            self.face_error = f"faces: {type(e).__name__}: {e}"[:160]
            return None
        finally:
            ctx.enable(moderngl.BLEND)
        self.face_error = ""
        return pic.tex

    def _pattern_clock(self, s: ViewState, t: float) -> float:
        """The patterns' clock, u_ptime: wall seconds times the SPEED input,
        integrated — so a SPEED that a lane moves changes how fast the
        pattern goes and never where it is (t · SPEED would jump the phase
        by t · ΔSPEED, minutes into a set). Moved once per new `t`: the
        seed and the face pass of one frame read the same value. The first
        call and a clock run backwards set it to t · SPEED, as if SPEED had
        always been what it is now."""
        speed = _speed(s)
        if self._ptime_at is None or t < self._ptime_at:
            self._ptime = t * speed
        else:
            self._ptime += (t - self._ptime_at) * speed
        self._ptime_at = t
        return self._ptime

    def _face_uniforms(self, p: moderngl.Program, s: ViewState, t: float,
                       ptime: float | None = None) -> None:
        """What the pattern and the bitmap read, on `p` — the face program
        or the seed — with the bitmap's texture on unit 0. The patterns'
        clock is the live one unless a still pins it (`ptime`); the clocks
        are set only if the patterns read them (an edit may not)."""
        if ptime is None:
            ptime = self._pattern_clock(s, t)
        bands = tuple(float(v) for v in (getattr(self, "bands", ()) or ())[:N_BANDS])
        for name, v in (("u_time", t), ("u_ptime", ptime), ("u_nlevels", len(bands))):
            try:
                p[name].value = v
            except KeyError:
                pass
        try:                        # trimmed by the driver, like u_mod below
            ub = p["u_levels"]
            n = getattr(ub, "array_length", N_BANDS) or N_BANDS
            ub.value = (bands + (0.0,) * N_BANDS)[:n]
        except KeyError:
            pass
        p["u_mode"].value = int(s.pattern)
        p["u_mix"].value = float(s.pattern_mix)
        # the driver trims the array to the highest index a pattern
        # reads; upload exactly that many
        u_mod = p["u_mod"]
        u_mod.value = tuple(float(v) for v in s.pattern_mod[: u_mod.array_length])
        self._sync_bitmap(s.bmp_file)
        bmp_on = self._bmp_tex is not None and s.bmp_alpha > 0.0
        p["u_bmp_on"].value = int(bmp_on)
        if bmp_on:
            self._bmp_tex.use(location=0)
            p["u_bitmap"].value = 0
            tw, th = self._bmp_tex.size
            p["u_bmp_scale"].value = (s.bmp_scale, s.bmp_scale * th / tw)
            p["u_bmp_alpha"].value = float(s.bmp_alpha)
            # the bitmap's own path about the face centre — independent
            # of the instance-grid motion
            ph = t * s.bmp_rate
            if s.bmp_mode == 1:      # orbit
                ox, oy = math.cos(ph), math.sin(ph)
            elif s.bmp_mode == 2:    # figure-8
                ox, oy = math.sin(ph), math.sin(2.0 * ph) * 0.5
            elif s.bmp_mode == 3:    # sway
                ox, oy = math.sin(ph), 0.0
            else:                    # still
                ox = oy = 0.0
            p["u_bmp_pos"].value = (s.bmp_amp * ox, s.bmp_amp * oy)

    def _tile_program(self) -> tuple:
        """The program and vao a pattern tile or swatch is drawn with: the
        seed's fragment with the face index a uniform, from the patterns
        file as it is now — rebuilt after a save. A save that does not
        compile raises once and keeps the last good program, as the face
        program does (its own build says why on the panel); it is tried
        again after the next save, not once a frame. Raises while there
        has never been a good one."""
        old = self._ptile
        if old is None or old[2] != self._patterns_mtime:
            mtime = self._patterns_mtime
            # this save is tried whatever happens; the last good one stays
            self._ptile = (None, None, mtime) if old is None else (*old[:2], mtime)
            prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=_face_fragment(
                TILE_FS_HEAD, PATTERNS_GLSL.read_text(), SEED_FS_TAIL))
            self._ptile = (prog, self.ctx.vertex_array(prog, []), mtime)
            if old is not None and old[0] is not None:
                for res in old[:2]:
                    res.release()
        if self._ptile[0] is None:
            raise RuntimeError("patterns.glsl does not compile (the panel says why)")
        return self._ptile[:2]

    def _tile_draw(self, fbo: moderngl.Framebuffer, size: int, s: ViewState, t: float,
                   ptime: float, fid: float, opaque: bool = False) -> None:
        """Face `fid`'s pattern for `s`, alone, into `fbo` (`size`²): the
        viewport and blending are put back, `fbo` is left bound. `opaque`
        keeps the alpha at 1 (a swatch the panel draws as it is: the
        premultiplied colour over black)."""
        ctx = self.ctx
        prog, vao = self._tile_program()
        self._face_uniforms(prog, s, t, ptime=ptime)
        try:
            prog["v_fid"].value = float(fid)
        except KeyError:                       # a pattern that ignores the face index
            pass
        fbo.color_mask = (True, True, True, True)
        fbo.use()
        vp = ctx.viewport
        ctx.viewport = (0, 0, size, size)
        ctx.clear(0.0, 0.0, 0.0, 1.0 if opaque else 0.0)
        ctx.disable(moderngl.BLEND)
        if opaque:
            # the alpha stays the clear's 1: moderngl sets the mask on use()
            fbo.color_mask = (True, True, True, False)
            fbo.use()
        try:
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            if opaque:
                fbo.color_mask = (True, True, True, True)
                fbo.use()               # the mask back on, for whatever binds next
            ctx.enable(moderngl.BLEND)
            ctx.viewport = vp

    def pattern_tile(self, s: ViewState, size: int = 128, t_now: float = 0.0,
                     fid: float = 0.0) -> np.ndarray:
        """What face `fid` shows of `s`'s pattern, alone: `size`² RGB, the
        pattern premultiplied by its intensity over black — the seed pass's
        picture (FLAT is mid-grey) at a pinned time, its clock at
        `t_now` · SPEED (how far the pattern has gone by then; the live
        clock is not touched). For tools and tests (tools/pattern_sheet.py);
        raises when patterns.glsl does not compile. Leaves the viewport and
        blending as it found them; its own framebuffer stays bound."""
        fbo = self._tile_fbos.get(size)
        if fbo is None:
            fbo = self._tile_fbos[size] = self.ctx.framebuffer(
                color_attachments=[self.ctx.texture((size, size), 4)])
        self._tile_draw(fbo, size, s, t_now, t_now * _speed(s), fid)
        img = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(size, size, 3)
        return img[::-1].copy()

    # ---- the FACES page's swatches: every mode, small, on the live inputs ----

    def want_swatches(self) -> None:
        """The FACES page is on show: keep the swatches drawing for the next
        SWATCH_HOLD frames. Nothing is drawn while no page asks."""
        self._swatch_until = self._swatch_frame + SWATCH_HOLD

    def swatch(self, mode: int) -> moderngl.Texture | None:
        """Mode `mode`'s swatch — SWATCH² RGBA, premultiplied, GL's way up —
        or None until one is drawn."""
        got = self._swatches.get(mode)
        return None if got is None else got[0]

    def _swatch_step(self, s: ViewState, t: float) -> bool:
        """While a page wants them, one mode's swatch a frame, round robin:
        what face 0 shows of that mode on this view's inputs (its mix and
        bitmap aside), on the patterns' live clock — so a strip of them
        moves with the faces at 1/N_PATTERNS of the frame rate, for one small
        quad a frame. A failure says so in `swatch_error` and never costs
        the frame. True when it drew (another framebuffer is bound)."""
        self._swatch_frame += 1
        if self._swatch_frame > self._swatch_until:
            return False
        mode = self._swatch_next % N_PATTERNS
        self._swatch_next = mode + 1
        try:
            got = self._swatches.get(mode)
            if got is None:
                tex = self.ctx.texture((SWATCH, SWATCH), 4)
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                got = self._swatches[mode] = (tex, self.ctx.framebuffer(color_attachments=[tex]))
            one = replace(s, pattern=mode, pattern_mix=1.0, bmp_alpha=0.0)
            self._tile_draw(got[1], SWATCH, one, t, self._ptime, 0.0, opaque=True)
            self.swatch_error = ""
        except Exception as e:  # noqa: BLE001 — a swatch must not take the frame down
            self.swatch_error = f"swatch: {type(e).__name__}: {e}"[:160]
        return True

    def dim_pass(self, target: moderngl.Framebuffer, vp: tuple[int, int, int, int],
                 factor: float, opaque: bool = True) -> bool:
        """Multiply what is on `target`'s viewport `vp` by `factor` (0 black
        … 1 untouched): one full-screen triangle, blending only — nothing
        is read and nothing is drawn. On an opaque ground the colour scales
        and the alpha is left exactly as it was, so the Pepper's Ghost
        window stays opaque black (plan 14 WP1); on overlay's see-through
        ground the frame is premultiplied, so colour and alpha both scale
        and the render fades off the desktop. The multiply is linear in the
        framebuffer's values; a curve for the bottom of the throw would go
        here, on `factor`.

        Leaves `target` bound with that viewport and the blend function as
        the scene pass sets it. A driver that refuses the program leaves
        the frame undimmed, says why once on `dim_error`, and is not asked
        again until a reload. True when it dimmed. Called once per frame
        with the master; plan 21 calls it once per output with master ×
        that output's own dim."""
        ctx = self.ctx
        if getattr(self, "_dim_prog", None) is None and not self._build_dim():
            return False
        try:
            target.use()
            ctx.viewport = vp
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.ZERO, moderngl.SRC_ALPHA, moderngl.ZERO,
                              moderngl.ONE if opaque else moderngl.SRC_ALPHA)
            self._dim_prog["u_factor"].value = clamp(float(factor), 0.0, 1.0)
            self._dim_vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            target.use()
            ctx.viewport = vp
        return True

    def _build_dim(self) -> bool:
        """The dim's program and its (attribute-less) vertex array, both or
        neither; a failure is recorded, never raised, and not retried."""
        if getattr(self, "dim_error", ""):
            return False
        prog = None
        try:
            prog = self.ctx.program(vertex_shader=DIM_VS, fragment_shader=DIM_FS)
            vao = self.ctx.vertex_array(prog, [])
        except Exception as e:  # noqa: BLE001 — the dim must not take the frame down
            if prog is not None:
                prog.release()
            self.dim_error = f"dim: {type(e).__name__}: {e}"[:160]
            return False
        self._dim_prog, self._dim_vao = prog, vao
        return True

    def _draw_cover(self, w: int, h: int) -> moderngl.Texture:
        """The faces again, solid, into the coverage mask — from the vertices
        the scene pass left in the face buffer."""
        ctx = self.ctx
        self.cover.ensure(self.scene.size)
        self.cover.fbo.use()
        ctx.viewport = (0, 0, *self.scene.size)
        ctx.clear(0.0, 0.0, 0.0, 0.0)
        if self._face_verts:
            ctx.disable(moderngl.BLEND)
            # the scene pass's camera, as it drew those vertices
            vp, model = self._scene_mats
            self._cover_prog["u_vp"].write(vp)
            self._cover_prog["u_model"].write(model)
            self._cvao.render(moderngl.TRIANGLES, vertices=self._face_verts)
            ctx.enable(moderngl.BLEND)
        return self.cover.tex

    def clear_scene(self) -> None:
        """The scene's clear, into whatever is bound: the premultiplied
        ground (black at `bg_alpha`) and the depth to the far plane. The
        scene node clears before its solid geometry (plan 26 A3); a scene
        of the shape alone clears inside `draw_scene`, as it always did."""
        self.ctx.clear(*BG, getattr(self, "bg_alpha", 1.0))

    def draw_scene(
        self, s: ViewState, w: int, h: int, dpr: float = 1.0,
        t_now: float | None = None, clear: bool = True,
    ) -> None:
        """The scene pass alone, into whatever is bound: clear, faces, edges,
        points. The pattern uniforms come from `s.pattern_mod`; `t_now` pins
        pattern time for deterministic renders. With `s.instances` at 0 it
        clears to the ground and draws nothing; the passes after it (cover,
        look-back, effects, ghost hands, dim) run as on any frame. Called on
        its own it shows no face picture, as it shows no frame effect: the
        faces' effects are `draw`'s (`_draw_frame` hands the picture over
        for the one scene pass it wraps).

        Plan 26 A2, the one camera: the CPU takes the shape to 3D
        (`geometry.world_points`), the GPU on to the clip through the
        shape's world transform (camera.zoom / camera.pan,
        `geometry.model_matrix`) and the eye (`eye.*`,
        `geometry.eye_matrix`). The see-through shape is painter-sorted
        as before and drawn with the depth test on but no depth written
        (whatever solid geometry is already in the depth buffer hides it;
        A3's hands), then `_depth_pass` writes its nearest visible
        surface for what comes after.

        Plan 26 A3: `clear` False draws over what is bound — the scene node
        cleared it and drew the solid geometry (the hands) first, whose
        depth hides the shape behind them."""
        g = geom(s.shape)
        # a shape whose W planes are masked is drawn at its own angles
        # (geometry.view_angles); every other shape at the view's
        ang = view_angles(s.shape, s.ang)
        P, w4, pd = world_points(g["V"], ang, s.yaw, s.pitch, d4=s.depth4)
        if w_masked(s.shape):
            # its w is 0 at every angle, so the depth cue (pd: fade, width,
            # draw order) would sit flat at its dimmest; it cues on its
            # depth toward the 3D camera (yaw and pitch included, so a
            # camera turned round never puts the far side on top), as a 4D
            # shape cues on its depth toward the 4D eye
            pd = view_depth(g["V"], ang, s.yaw, s.pitch, d4=s.depth4)

        # the camera: the shape's world transform and the eye, as the
        # vertex shaders take them (column-major)
        zoom = max(s.zoom, 1e-3)
        model = model_matrix(zoom, s.pan)
        vp = eye_matrix(w, h, getattr(s, "eye_fov", EYE_FOV),
                        getattr(s, "eye_distance", EYE_DISTANCE))
        mats = (np.asarray(vp, dtype="f4").T.tobytes(),
                np.asarray(model, dtype="f4").T.tobytes())
        self._scene_mats = mats

        # synchronized instances in a layout (grid, honeycomb or ring:
        # inst_positions), in the world: a cell is CELL shape radii, and the
        # field is scaled and moved as one by the world transform, so
        # zooming out shows a field as it always did
        n_inst = max(0, int(s.instances))   # 0: the ground alone (returns below)
        t_m = self.now(t_now)
        if n_inst > 1:
            gx, gy = inst_positions(n_inst, int(s.inst_layout))
            gx, gy = gx.astype(np.float64), gy.astype(np.float64)
            ox, oy = gx * CELL, gy * CELL
            if s.inst_motion and s.inst_amp > 0.0:
                # trigonometric motion over the field: each instance's phase
                # comes from its position, so the field moves as one figure
                ph = t_m * s.inst_rate
                if s.inst_motion == 1:    # ORBIT — circles in a traveling wave
                    th = ph + (gx + gy) * 0.9
                    dx, dy = np.cos(th), np.sin(th)
                elif s.inst_motion == 2:  # WAVE — bob by column, sway by row
                    dx = 0.35 * np.sin(ph * 0.7 + gy * 1.1)
                    dy = np.sin(ph + gx * 1.1)
                else:                     # RIPPLE — radial swell from the centre
                    rr = np.hypot(gx, gy)
                    u = np.sin(ph - rr * 1.2) / np.maximum(rr, 1.0)
                    dx, dy = gx * u, gy * u
                ox = ox + s.inst_amp * CELL * dx
                oy = oy + s.inst_amp * CELL * dy
            # the cells are laid out y down the screen; the world's y is up
            offs = np.stack([ox, -oy], axis=1).astype(np.float32)
        else:
            offs = np.zeros((1, 2), dtype=np.float32)

        near, far = pd.min(), pd.max()
        span = max(far - near, 1e-6)
        E = g["E"]
        edepth = (pd[E[:, 0]] + pd[E[:, 1]]) * 0.5
        order = np.argsort(edepth, kind="stable")  # painter: far first

        t = (edepth[order] - near) / span
        dens = clamp(340 / max(g["m"], 1), 0.42, 1)
        heavy = g["m"] > 500
        B = s.bright * dens
        alpha = np.clip((0.10 + 0.90 * t * t) * B, 0.015, 1)

        # the reference's depth- and brightness-scaled line width (CSS px).
        # Plan 26 A2b (view.screen_strokes): in world space (the default)
        # the width is × the zoom, so a stroke grows and shrinks with the
        # shape as it did before A2; in screen space it keeps its weight
        # whatever the shape's size in the world (A2). The shape's strokes
        # only: the hands are not drawn here — A3's tubes are world-sized
        # geometry (ghost.py WIRE_R / BONE_R) that never follows
        # camera.zoom (the zoom is the shape's scale, not the hands'), and
        # A4's hand lines are 1 px edges drawn by ghost.Geometry, not by
        # this width, in both modes
        sz = 1.0 if getattr(s, "screen_strokes", False) else zoom
        wscale = clamp(0.75 + 0.35 * s.bright, 0.6, 1.35)
        width = ((0.35 + 0.85 * t) if heavy else (0.5 + 1.5 * t)) * wscale * sz
        draw_w = np.maximum(width, 1.0)
        # the edges' alpha, final: depth × brightness × density (floored
        # above), sub-pixel width folded in, × the lines opacity (plan 24
        # C2) — after the floor and before the vertex fill, so the depth
        # pass's skip test (`draws`) sees the faded alpha
        alpha = alpha * np.minimum(width, 1.0) * s.lines_alpha

        # premultiplied ground: black at bg_alpha, so SRC_ALPHA/ONE_MINUS
        # blending leaves the framebuffer correctly composited for a
        # transparent window (colour = Σ c·a, alpha = 1 − Π(1 − a)). The
        # clear clears the depth too (to the far plane)
        bg_alpha = getattr(self, "bg_alpha", 1.0)
        if clear:
            self.ctx.clear(*BG, bg_alpha)
        # cut-through: the plain blend also blends alpha (a² + (1 − a)·dst),
        # so a faint fill lowers the ground's alpha and a transparent window
        # shows the desktop through it. Off: alpha composites over the ground
        # (a + (1 − a)·dst), never below it — the lowest layer shows instead.
        # Only on a see-through ground (overlay mode): on an opaque one the
        # frame stays alpha 1 everywhere, so the desktop never shows through
        # the window (plan 14 WP1 — the Pepper's Ghost rig)
        if s.cut_through and bg_alpha < 1.0:
            blend = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        else:
            blend = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
                     moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ctx.blend_func = blend

        # ---- face fills, under the wireframe (agent-validated prototype) ----
        self._face_verts = 0
        if s.faces:
            self._maybe_reload_patterns()
        if n_inst == 0:
            # no copies: the cleared ground is the scene. No vertex buffer is
            # written and nothing is bound here, so the caller's target and
            # the passes after this one are as on any other frame
            return
        # the see-through shape: tested against what depth is there, never
        # writing any (the painter order is its own order); `_depth_pass`
        # writes its visible surface afterwards
        fbo = self.ctx.fbo
        has_depth = getattr(fbo, "depth_attachment", None) is not None
        if has_depth:
            fbo.depth_mask = False
            fbo.use()
            self.ctx.enable(moderngl.DEPTH_TEST)
        draws: list[tuple] = []        # (vao, vertices, program, the most alpha a fragment has)
        try:
            if s.faces and self._face_prog is not None:
                tris = face_triangles(s.shape)
                if len(tris):
                    td = (pd[tris[:, 0]] + pd[tris[:, 1]] + pd[tris[:, 2]]) / 3.0
                    torder = np.argsort(td, kind="stable")
                    tt = (td[torder] - near) / span
                    nfaces = int(tris[:, 3].max()) + 1
                    fdens = min(1.0, 24.0 / max(nfaces, 1))
                    fa = (0.010 + 0.055 * tt * tt) * s.bright * (0.35 + 0.65 * fdens)
                    to = tris[torder]
                    uv = face_uvs(s.shape).reshape(-1, 3, 2)[torder]
                    fverts = np.empty((len(tris) * 3, 8), dtype=np.float32)
                    for corner in range(3):
                        fverts[corner::3, 0:3] = P[to[:, corner]]
                        fverts[corner::3, 3] = w4[to[:, corner]]
                        fverts[corner::3, 4] = uv[:, corner, 0]
                        fverts[corner::3, 5] = uv[:, corner, 1]
                        fverts[corner::3, 6] = fa
                        fverts[corner::3, 7] = to[:, 3]
                    fverts = self._tile(fverts, offs)
                    self._fbuf.orphan(fverts.nbytes)
                    self._fbuf.write(fverts.tobytes())
                    p = self._face_prog
                    self._camera_uniforms(p, mats, -1.0)
                    self._face_uniforms(p, s, t_m)
                    # the faces' effects' picture, when _draw_frame made one for
                    # this pass: on its own unit, per face or in screen space.
                    # Set every frame — a program keeps its uniforms
                    pic = getattr(self, "_pic", None)
                    if pic is None:
                        p["u_pic_on"].value = 0
                    else:
                        pic.use(location=1)
                        screen = int(getattr(self.fx.state, "face_map", 0)) == SCREEN
                        p["u_pic_on"].value = 2 if screen else 1
                        p["u_pic_fb"].value = tuple(float(x) for x in self.scene.size)
                    self._fvao.render(moderngl.TRIANGLES, vertices=len(fverts))
                    self._face_verts = len(fverts)
                    # a fill is at most 2.8× its vertex alpha: the face shader's
                    # shade is mix(1, 2.8·v.a, mix) with v clamped to [0, 1] in
                    # FACE_PX, mix(shade, 2.8, ba) under a bitmap, and 2.8·t.a
                    # from an RGBA8 picture — the depth pass's skip bound rests
                    # on that clamp (patterns.glsl cannot exceed it)
                    draws.append((self._fvao, len(fverts), p, float(fa.max()) * 2.8))

            if s.lines:
                eo = E[order]
                m = g["m"]
                verts = np.empty((m * 6, 10), dtype=np.float32)
                for k in range(6):
                    verts[k::6, 0:3] = P[eo[:, 0]]
                    verts[k::6, 3:6] = P[eo[:, 1]]
                    verts[k::6, 6:8] = _EDGE_CORNERS[k]
                    verts[k::6, 8] = draw_w
                    verts[k::6, 9] = alpha
                verts = self._tile(verts, offs, cols=(0, 3))   # both ends
                self._lbuf.orphan(verts.nbytes)
                self._lbuf.write(verts.tobytes())
                self._camera_uniforms(self._lines, mats, -1.0)
                self._lines["u_size"].value = (float(w), float(h))
                self._lvao.render(moderngl.TRIANGLES, vertices=len(verts))
                draws.append((self._lvao, len(verts), self._lines, float(alpha.max())))

            if s.points:
                tp = (pd - near) / span
                order_p = np.argsort(pd, kind="stable")
                # radius in framebuffer px (× dpr), × the zoom in world space
                # (plan 26 A2b, `sz` above; 1 in screen space) — before the
                # rounding: the diameter is a whole number of pixels, as the
                # point sprites the quads replace were rasterised (the driver
                # rounded gl_PointSize — measured: with it the quads draw the
                # sprites' frame byte for byte, without it every dot grows)
                r = ((1.0 if heavy else 1.7) + 2.3 * tp * tp) * dpr * sz
                r = np.floor(2.0 * r + 0.5) / 2.0
                # the points' alpha: depth × brightness, floored, × the points
                # opacity (plan 24 C2) after the floor — the one place it is derived
                PB = s.bright * clamp(dens * 1.5, 0.55, 1)
                pa = np.clip((0.32 + 0.68 * tp) * PB, 0.05, 1) * s.points_alpha
                n = g["n"]
                pverts = np.empty((n * 6, 7), dtype=np.float32)
                for k in range(6):
                    pverts[k::6, 0:3] = P[order_p]
                    pverts[k::6, 3:5] = _POINT_CORNERS[k]
                    pverts[k::6, 5] = r[order_p]
                    pverts[k::6, 6] = pa[order_p]
                pverts = self._tile(pverts, offs)
                self._pbuf.orphan(pverts.nbytes)
                self._pbuf.write(pverts.tobytes())
                self._camera_uniforms(self._points, mats, -1.0)
                vpx = self.ctx.viewport
                self._points["u_px"].value = (float(max(vpx[2], 1)), float(max(vpx[3], 1)))
                self._pvao.render(moderngl.TRIANGLES, vertices=len(pverts))
                draws.append((self._pvao, len(pverts), self._points, float(pa.max())))

            if has_depth:
                self._depth_pass(fbo, draws, mats, blend)
        finally:
            if has_depth:
                self.ctx.disable(moderngl.DEPTH_TEST)
                fbo.depth_mask = True
                fbo.use()

    def _depth_pass(self, fbo: moderngl.Framebuffer, draws: list[tuple], mats: tuple,
                    blend: tuple) -> None:
        """The shape's depth, after its colour (plan 26 A2): the same draws
        again with the colour left as it is (the blend keeps the
        destination) and depth written, only by fragments whose alpha is
        over `DEPTH_ALPHA` — the nearest visible surface. A draw none of
        whose fragments can reach the threshold is skipped (a plain fill
        never does at brightness 1)."""
        live = [d for d in draws if d[3] > DEPTH_ALPHA]
        if not live:
            return
        ctx = self.ctx
        fbo.depth_mask = True
        fbo.use()
        ctx.blend_func = moderngl.ZERO, moderngl.ONE
        try:
            for vao, n, prog, _ in live:
                prog["u_depth_alpha"].value = DEPTH_ALPHA
                vao.render(moderngl.TRIANGLES, vertices=n)
        finally:
            for _, _, prog, _ in live:
                prog["u_depth_alpha"].value = -1.0
            ctx.blend_func = blend

    @staticmethod
    def _camera_uniforms(prog: moderngl.Program, mats: tuple, depth_alpha: float) -> None:
        """The one camera on a scene program: the eye and the shape's world
        transform, and which pass (the colour pass: no depth threshold)."""
        prog["u_vp"].write(mats[0])
        prog["u_model"].write(mats[1])
        prog["u_depth_alpha"].value = depth_alpha

    @staticmethod
    def _tile(verts: np.ndarray, offs: np.ndarray, cols: tuple[int, ...] = (0,)) -> np.ndarray:
        """Replicate a per-instance vertex array across the instance field:
        each copy's (x, y) world offset added to every 3D point in the row,
        the points starting at the columns `cols` names — (0,) for a face
        or a point, (0, 3) for an edge's two ends (`LINE_FORMAT`)."""
        if len(offs) == 1 and not offs.any():
            return verts
        out = np.tile(verts, (len(offs), 1))
        per = len(verts)
        for k, (ox, oy) in enumerate(offs):
            for c in cols:
                out[k * per : (k + 1) * per, c] += ox
                out[k * per : (k + 1) * per, c + 1] += oy
        return out


N_PATTERNS = len(MODES)
SWATCH = 64         # px: a mode's swatch (want_swatches), drawn smaller on the FACES page
SWATCH_HOLD = 30    # frames the swatches keep drawing after the page last asked


def _speed(s: ViewState) -> float:
    """The SPEED pattern input (patterns.SPEED), never below a standstill."""
    return max(float(s.pattern_mod[SPEED]), 0.0) if len(s.pattern_mod) > SPEED else 1.0


# a face's pattern on its own (Renderer.pattern_tile): the seed's fragment
# with the face index a uniform, so a tile can be any face
TILE_FS_HEAD = """
#version 330
in vec2 v_uv;
out vec4 f_color;
const float v_alpha = 1.0;
uniform float v_fid;
""" + FACE_UNIFORMS


def render_offscreen(
    s: ViewState, w: int = 1200, h: int = 800, ctx: moderngl.Context | None = None,
    t_now: float = 0.0,
) -> np.ndarray:
    """Render one frame to an FBO; returns (h, w, 3) uint8. For tests/tools.
    Pattern time defaults to 0.0 so offscreen renders are deterministic."""
    own = ctx is None
    if own:
        ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h))])
    fbo.use()
    ctx.viewport = (0, 0, w, h)
    Renderer(ctx).draw(s, w, h, t_now=t_now)
    data = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(h, w, 3)[::-1]
    fbo.release()
    if own:
        ctx.release()
    return data.copy()
