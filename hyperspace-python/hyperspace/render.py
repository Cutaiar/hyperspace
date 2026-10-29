"""moderngl renderer — port of the draw() pipeline of hyperspace.html.

Plan 26 A2, one camera: the CPU takes the shape to 3D
(geometry.shape_world: per layer, world_points' rotate4, the 4D divide
and the yaw/pitch turntable) and the vertex shaders take it to the clip
through one shared 4×4, the eye (`u_vp`, geometry.eye_matrix, the `eye.*`
params), after each copy's place in the world (`in_inst`, below: the
camera's zoom and pan are a copy's scale and centre). The default eye
is project_h's old 3D divide, so at zoom 1 and pan 0 every vertex lands
within a ten-thousandth of a pixel of where project_h — the renderer's
path until A2, and geometry.project's, the parity oracle — puts it
(tests/test_camera.py). The dataclass it draws, ViewState, lives in
view.py so nothing has to import moderngl to hold a view.

The shape is taken to 3D once and drawn once per copy by instanced draws:
each copy is one vec4 (`in_inst`: its centre in the world, its scale, its
alpha) and the vertex shaders place it — a copy's point is the shape's
point × its scale + its centre, before the world transform and the eye.
A flat layout (or one copy) with Fit off is the field as it always was,
the same arithmetic (`Renderer._legacy_field`): the copies at scale 1, the
camera's zoom and pan the world transform (`u_model`), the strokes scaled
by the zoom on the CPU, so its frames are byte for byte what they were.
Fit and the 3D lattices are field.py's (`Renderer._field`): each copy's
scale and centre carry the camera, `u_model` is the identity, and edge
widths and point sizes are scaled per copy in the shaders (in world-space
strokes), folding into alpha below a pixel there. Either way a field of
thousands costs one 3D pass and a few kilobytes of upload a frame, and a
copy wholly off screen is not drawn.

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

A picture wired into the faces (`shape.faces`, plan 33 R: the faces'
run `pattern → … → shape.faces`, or any branch) is made before the scene
pass at a fixed size (FACE_PIC², `Renderer._face_picture`: the seed pass,
then the effects on its wires, mipmaps); the face shader then draws that
picture on every face, per face or in screen space, in place of
computing the pattern and the bitmap per fragment. So the faces'
effects are *in* the scene texture: the echoes and the dream carry them,
and the frame's run goes over them. With nothing wired into the faces
none of it runs, nothing is allocated and the frame is bit-identical.
The ghost hands (ghost.py) are a geometry in the same
camera (plan 26 A3): by default their own layer, laid over the finished
frame (or onto it before the effects); wired into the scene, solid,
before the shape; off, the frame is untouched. Last of all the master
dim (`Renderer.dim`, the crossfader's `output.dim`; plan 15 WP3)
multiplies what is there — it draws nothing of its own, and at 1 it does
not run.

Plan 21: `Renderer.draw_outputs` shows that one frame on several outputs
(`outputs.View`), each through its own mutes — the picture, the hands —
and its own dim. The scene, the capture and the hands' layer run once a
frame; each distinct picture an output shows once (its end, `Shown`);
the picture, the hands over it and the dim once per output. `draw` is
`draw_outputs` with one default view on the bound framebuffer, and is
the frame it always was, byte for byte.

Plan 26 A1: those passes are the nodes of a render graph (graph.py).
`_draw_frame` builds the graph — or reuses the last one while the views'
count and the wiring do not change — and evaluates it: the nodes run
once each, in an order settled when the graph was built, and each node
is timed on the GPU (`PassTimer`, one line per node on the SYSTEM page).
Plan 35 T4: every graph is a wired frame's (`graph.build_graph`; plan 36
T3: nothing else — `graph.EMPTY` until a preset lands); the pipelines are gone, and
every golden frame is drawn byte for byte. The passes themselves (`draw_scene`,
`_face_picture`, `_draw_cover`, `_compose`, `_show`, `dim_pass`) stay
here; the nodes call them.

Plan 34 D: each delay's two half-float pictures are the renderer's
(`DelayPair`, `delay_pair`), kept by name across graph rebuilds and
swapped once a frame before the graph runs (`_turn_delays`); a picture
of its own size is laid into a consumer of another shape by the refit
pass (`REFIT_FS`, `_refit`). GL allows one time query active at once, so
a node's query opened inside another's is a no-op (`PassTimer.time`,
ruling R5): `delay(write)` times its paint, effects inside it included.
"""

from __future__ import annotations

import math
import time
from dataclasses import replace
from pathlib import Path
from typing import Self

import moderngl
import numpy as np

from . import field as _field_mod
from .field import (  # noqa: F401 — re-exported: the layouts were render.py's
    LAYOUT_GRID,
    LAYOUT_HEX,
    LAYOUT_RING,
    MAX_INSTANCES,
    field,
    inst_positions,
)
from .field import is_3d as is_3d_layout
from .fx import SCREEN, FxChain, FxState
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
    shape_world,
)
from .ghost import Ghost, GhostState
from .glsl import QUAD_VS, common, common_mtime, gl_error
from .graph import (
    EMPTY,
    FACE_PIC,
    IMAGE,
    MEDIA_CHANNELS,
    Delay,
    Frame,
    Graph,
    Hands,
    HandsLayer,
    Output,
    Scene,
    SegmentNode,
    Wiring,
    build_graph,
    channel_into,
    cloud_roles,
    graph_key,
    param_prefix,
    picture,
    rig_of,
)
from .lookback import Dreamer, DreamState, Lookback
from .masks import MaskPasses
from .media_tex import COVER, FIT_FS, MediaTextures, UiTextures, fit_scale
from .outputs import Handoff, Presenter, PreviewTextures, Switches, View, capped, fit
from .patterns import MODES, SPEED
from .tapers import clamp
from .view import N_MOD, RED, ViewState  # re-exported for callers that had them from here

# plan 32 (final review B-I2): the MEDIA page's previews of channels nothing
# in the frame reads — each at most this often, at most this many a frame
PREVIEW_HZ = 10.0
PREVIEWS_PER_FRAME = 2

# the GRAPH page's shape wireframe (`Renderer.want_wire`): the shape's edges
# alone, white on black, in a square at most this many px a side, dropped
# this long after the page last asked for it
WIRE_PX_MAX = 1024
WIRE_DROP_S = 1.0

# plan 33 R29: how many frames a texture made at another size (`pool_at`, a
# `(name, size)` frame target) is kept after its last use before
# `_prune_sized` releases it — so a switch the sequencer flicks between two
# branches of other sizes reallocates nothing per flick (half a second at
# 60 fps: a few idle textures held, at most)
SIZED_KEEP_FRAMES = 30

PATTERNS_GLSL = Path(__file__).parent / "shaders" / "patterns.glsl"

BG = (0.0, 0.0, 0.0)

# the least depth the cue spreads over (draw_scene), in the shapes' unit
# (circumradius 1): a shape thinner than this toward the eye — flat, or
# turned flat — is cued over this much from its nearest point instead of
# over its own sliver. Over 40 random poses of every shape, 12 shapes are
# ever thinner and 1.2 % of poses
DEPTH_FLOOR = 1.0

# FACE_PIC (graph.py's, imported above): the side, in texels, of the
# picture the faces show while something other than the pattern is wired
# into them (plan 20 fork F2; plan 33 R: what `shape.faces` asks)
_UNSET = object()        # `_face_uniforms`: no media layer handed in

# Plan 26 A2, the one camera: the scene's vertices arrive in 3D — the
# shape after the 4D tumble, the 4D divide and the yaw/pitch turntable
# (geometry.shape_world) — and the vertex shaders place each copy (in_inst:
# the point × the copy's scale + its centre, in the world; field.py, with
# the camera's zoom and pan) and take it to the clip through the world
# transform (u_model: the identity since the instanced field) and the
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
in vec3 in_a;        // the edge's two ends, the shape's 3D points
in vec3 in_b;
in vec2 in_corner;   // x: which end (0 a, 1 b); y: which side of the edge (±1)
in float in_width;   // logical px at scale 1 (below 1 it folds into alpha)
in float in_alpha;
in vec3 in_rgb;      // white, but for a scene's tinted layer (plan 28 catalog)
in vec4 in_inst;     // this copy: centre (xy, world), scale (z), alpha (w)
uniform mat4 u_vp;   // the eye
uniform mat4 u_model; // the world transform
uniform vec2 u_size; // logical viewport size
uniform float u_wscale; // 1: strokes scale with the copy (world space); 0: screen space
out float v_alpha;
out vec3 v_rgb;
void main() {
    vec3 o = vec3(in_inst.xy, 0.0);
    vec4 ca = u_vp * (u_model * vec4(in_a * in_inst.z + o, 1.0));
    vec4 cb = u_vp * (u_model * vec4(in_b * in_inst.z + o, 1.0));
    const float W = """ + EYE_W + """;
    float wk = in_width * mix(1.0, in_inst.z, u_wscale);
    v_alpha = in_alpha * min(wk, 1.0) * in_inst.w;
    v_rgb = in_rgb;
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
    vec2 n = vec2(-d.y, d.x) / ln * (0.5 * max(wk, 1.0) * in_corner.y);
    vec4 c = in_corner.x < 0.5 ? ca : cb;
    gl_Position = vec4(c.xy + n / half_size * c.w, c.z, c.w);
}
"""

LINE_FS = """
#version 330
in float v_alpha;
in vec3 v_rgb;
uniform float u_depth_alpha;   // < 0 the colour pass; else the depth pass's threshold
out vec4 f_color;
void main() {
    if (u_depth_alpha >= 0.0 && v_alpha <= u_depth_alpha) discard;
    f_color = vec4(v_rgb, v_alpha);
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

# plan 34 D (row 358): a picture of its own size laid into a target of
# another shape (`Renderer._refit`: the delay, the echoes, the dream, the
# resize) — the crop `u_crop` of the source (x0, y0, w, h in its GL uv)
# fitted about the centre by `u_scale` (`media_tex.fit_scale` of the crop's
# pixels into the target's), sampled inside `u_clamp` (min uv, max uv) so
# no neighbour bleeds in. Outside the fit, transparent black; inside, the
# texel as it is (premultiplied in, premultiplied out). Plan 34 T4: a crop
# past the source's edge (a resize's) is transparent black there too — a
# crop inside the source, every caller's before the resize, never is
REFIT_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform vec4 u_crop;
uniform vec2 u_scale;
uniform vec4 u_clamp;
out vec4 f_color;
void main() {
    vec2 q = 0.5 + (v_uv - 0.5) * u_scale;
    if (any(lessThan(q, vec2(0.0))) || any(greaterThan(q, vec2(1.0)))) {
        f_color = vec4(0.0);
        return;
    }
    vec2 uv = u_crop.xy + q * u_crop.zw;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) {
        f_color = vec4(0.0);
        return;
    }
    f_color = texture(u_src, clamp(uv, u_clamp.xy, u_clamp.zw));
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
in vec3 in_pos;      // the shape's 3D point (see LINE_VS)
in float in_w4;      // the 4D divisor: × the clip w, so the uv is perspective-correct
                     // across both divides, as the old combined divisor made it
in vec2 in_uv;       // face-local coordinates
in float in_alpha;
in float in_fid;     // face index within the shape
in vec4 in_inst;     // this copy: centre (xy, world), scale (z), alpha (w)
uniform mat4 u_vp;
uniform mat4 u_model;
out vec2 v_uv;
out float v_alpha;
out float v_fid;
void main() {
    vec4 q = vec4(in_pos * in_inst.z + vec3(in_inst.xy, 0.0), 1.0);
    gl_Position = (u_vp * (u_model * q)) * in_w4;
    v_uv = in_uv;
    v_alpha = in_alpha * in_inst.w;
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
uniform int u_bmp_flip;      // 1: the texture is in GL's row order (a feed's own), drawn as it is
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
            vec4 b = texture(u_bitmap, vec2(q.x, u_bmp_flip != 0 ? q.y : 1.0 - q.y));
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
in vec4 in_inst;
uniform mat4 u_vp;
uniform mat4 u_model;
void main() {
    vec4 q = vec4(in_pos * in_inst.z + vec3(in_inst.xy, 0.0), 1.0);
    gl_Position = (u_vp * (u_model * q)) * in_w4;
}
"""

COVER_FS = """
#version 330
out vec4 f_color;
void main() { f_color = vec4(1.0); }
"""

POINT_VS = """
#version 330
in vec3 in_pos;      // the shape's 3D point (see LINE_VS)
in vec2 in_corner;   // the quad's corner, (±1, ±1)
in float in_size;    // radius in framebuffer pixels at scale 1
in float in_alpha;
in vec3 in_rgb;      // RED, but for a scene's tinted layer (plan 28 catalog)
in vec4 in_inst;     // this copy: centre (xy, world), scale (z), alpha (w)
uniform mat4 u_vp;
uniform mat4 u_model;
uniform vec2 u_px;   // the framebuffer viewport, px
uniform float u_wscale; // 1: dots scale with the copy (world space); 0: screen space
out float v_alpha;
out vec2 v_corner;
out vec3 v_rgb;
void main() {
    vec4 c = u_vp * (u_model * vec4(in_pos * in_inst.z + vec3(in_inst.xy, 0.0), 1.0));
    // the diameter a whole number of pixels, as the point sprites the quads
    // replace were rasterised (the driver rounded gl_PointSize); under one
    // pixel the dot stays a pixel and folds into alpha
    float d = floor(2.0 * in_size * mix(1.0, in_inst.z, u_wscale) + 0.5);
    v_alpha = in_alpha * min(d, 1.0) * in_inst.w;
    v_corner = in_corner;
    v_rgb = in_rgb;
    if (c.w < """ + EYE_W + """) {        // behind the eye: nothing
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        return;
    }
    gl_Position = vec4(c.xy + in_corner * (0.5 * max(d, 1.0)) / (0.5 * u_px) * c.w, c.z, c.w);
}
"""

# the quad's corner stands in for gl_PointCoord: the same round dot
POINT_FS = """
#version 330
in float v_alpha;
in vec2 v_corner;
in vec3 v_rgb;
out vec4 f_color;
uniform float u_depth_alpha;   // < 0 the colour pass; else the depth pass's threshold
void main() {
    float a = v_alpha * (1.0 - smoothstep(0.8, 1.0, length(v_corner)));
    if (a <= 0.0 || (u_depth_alpha >= 0.0 && a <= u_depth_alpha)) discard;
    f_color = vec4(v_rgb, a);
}
"""

# the three vertex buffers' layouts, one row per vertex, and the copies':
#   face  — position (3), 4D divisor, uv (2), alpha, face id
#   edge  — end a (3), end b (3), corner (end, side), width (logical px), alpha, rgb (3)
#   point — position (3), corner (2), radius (framebuffer px), alpha, rgb (3)
#   inst  — per copy: centre (2, world), scale, alpha
FACE_FORMAT = "3f 1f 2f 1f 1f"
LINE_FORMAT = "3f 3f 2f 1f 1f 3f"
POINT_FORMAT = "3f 2f 1f 1f 3f"
INST_FORMAT = "4f/i"

# a point's quad: two triangles over its four corners
_POINT_CORNERS = np.array([(-1, -1), (1, -1), (-1, 1), (1, -1), (1, 1), (-1, 1)],
                          dtype=np.float32)
# an edge's quad: (a, b, c) and (b, e, c) over its ends' two sides —
# (end, side): a = (0, +1), b = (0, −1), c = (1, +1), e = (1, −1)
_EDGE_CORNERS = np.array([(0, 1), (0, -1), (1, 1), (0, -1), (1, -1), (1, 1)],
                         dtype=np.float32)




# a field's pixels in the world: through the default eye a unit at the
# origin is SCALE·min(w, h) px, so the field (field.py, laid out in px)
# keeps the world spacing it had — a cell is field.CELL / SCALE shape radii
# — whatever the eye (`Renderer._copies_of`)
CELL = 0.72 / SCALE


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


class DelayPair:
    """One delay's two pictures (plan 34 D, row 354): `read`, last frame's
    (what `graph.Delay` shows), and `write`, this frame's (what
    `graph.DelayWrite` paints into) — each (texture, framebuffer), RGBA
    half-float (an 8-bit feedback with a decay below 1 sticks and never
    fades), LINEAR, clamped, cleared to transparent black when made. Two
    distinct textures always: no pass reads what it writes.

    `turn()`, once a frame before the graph runs (`Renderer._turn_delays`):
    a pair written last frame swaps its sides and holds a frame; one not
    written holds nothing (strict z⁻¹). `idle` counts the frames no graph
    has held its delay: released at `SIZED_KEEP_FRAMES`."""

    def __init__(self) -> None:
        self.read: tuple[moderngl.Texture, moderngl.Framebuffer] | None = None
        self.write: tuple[moderngl.Texture, moderngl.Framebuffer] | None = None
        self.holds = False
        self.wrote = False
        self.idle = 0

    def target(self, ctx: moderngl.Context, size: tuple[int, int]) -> moderngl.Framebuffer:
        """The write side at `size`: made again only when missing or of
        another size (row 357: the read side is left alone, so the next
        frame still reads the frame before, at its old size)."""
        size = (int(size[0]), int(size[1]))
        if self.write is not None and tuple(self.write[0].size) == size:
            return self.write[1]
        self._free(self.write)
        self.write = None
        tex = ctx.texture(size, 4, dtype="f2")
        try:
            tex.repeat_x = tex.repeat_y = False
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            fbo = ctx.framebuffer(color_attachments=[tex])
        except Exception:
            tex.release()
            raise
        fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.write = (tex, fbo)
        return fbo

    def turn(self) -> None:
        if self.wrote:
            self.read, self.write = self.write, self.read
            self.holds = True
        else:
            self.holds = False
        self.wrote = False

    @staticmethod
    def _free(side) -> None:
        if side is not None:
            for res in (side[1], side[0]):
                res.release()

    def release(self) -> None:
        self._free(self.read)
        self._free(self.write)
        self.read = self.write = None
        self.holds = self.wrote = False


class FaceTarget:
    """The picture the faces show while something other than the pattern
    is wired into them (plan 20; plan 33 R: `shape.faces`), or the
    pattern's own picture for a consumer that binds one
    (`Renderer._pattern_picture`): one RGBA8 texture, FACE_PIC square,
    premultiplied with alpha as the face's intensity, mipmapped — per face
    it lands on a face a hundred or so pixels across. Made on first use,
    never resized."""

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
    node that ran more than once (the look-back painted for two ends)
    is summed into its frame's total; one that did not run counts 0 that
    frame; a name no longer in the graph (an output closed, a node
    unwired) drops out of the medians. Time queries never
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
        """``with timer.time("scene"):`` — the node's GPU time, this frame.
        Plan 34 D: inside another node's query (a delay's write painting an
        effect, which times its own pass) it is a no-op — GL allows one
        active per target, so the outer line holds the inner's time."""
        if not self.on or getattr(self, "_active", False):
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
                self.timer._active = True        # (plan 34 D: no query inside it)
            except Exception as e:  # noqa: BLE001 — timing never costs a frame
                self.timer._off(e)
        return self

    def __exit__(self, *exc) -> bool:
        if self.began:
            self.timer._active = False
            try:
                self.q.__exit__(None, None, None)
            except Exception as e:  # noqa: BLE001 — timing never costs a frame
                self.timer._off(e)
        return False


def _flush() -> None:
    """glFlush in the current context (the render context, at the end of a
    frame); best-effort — a thumbnail late by a frame costs nothing."""
    try:
        from OpenGL import GL

        GL.glFlush()
    except Exception:  # noqa: BLE001, S110 — no PyOpenGL, or no current context
        pass


def thumb_source(frame: Frame, name: str, how: str,
                 pulled: frozenset[str] | None = None) -> moderngl.Texture | None:
    """The picture node `name`'s thumbnail is copied from, this frame
    (plan 37 C1; `how` is `graphview.THUMBS`' word for its kind) — or None:
    it made nothing this frame (no such node built, not pulled behind a
    switch, reading nothing, a hands layer with no hand drawn).

    - ``picture``: a node whose output is a picture, asked for it
      (`graph.picture`: the texture it made, else painted once into a
      frame texture of its own);
    - ``scene``: a geometry (the shape, a cloud): the picture of the first
      scene that draws it (the page draws it faint);
    - ``layer``: a hands node: the first hands layer drawing it, else the
      scene it is drawn in;
    - ``window``: an output after the first: its presenter's picture (the
      `Handoff`'s frame, a texture of this context: no readback), or a
      publish-only output's own target; output 1 is the page's `Preview`,
      never asked here."""
    g = frame.graph
    node = g.nodes.get(name) if g is not None else None
    if node is None:
        return None
    if how == "window":
        if not isinstance(node, Output) or not 0 < node.index < len(frame.views):
            return None
        v = frame.views[node.index]
        if v.handoff is not None:
            return v.handoff.frame
        own = getattr(v.target, "color_attachments", None) if v.target is not None else None
        return own[0] if own and isinstance(own[0], moderngl.Texture) else None
    if how in ("scene", "layer"):
        if how == "layer":
            layer = next((n for n in g.order if isinstance(n, HandsLayer)
                          and n.inputs.get("geometry") is node), None)
            if layer is not None:
                return layer.image(frame)
        scene = next((n for n in g.order if isinstance(n, Scene)
                      and any(x is node for x in n.inputs.values())), None)
        if scene is None:
            return None
        node = scene
    if getattr(node, "OUTPUT", None) != IMAGE:
        return None
    # (review: every kind — a composite, a delay, a resize, a copy behind a
    # switch's unpicked input made nothing this frame, and painting it would
    # pull its inputs: the gated effects, the unpicked channels read and
    # uploaded — plan 33 S. First, before `reads`, which reads a channel)
    if pulled is not None and node.name not in pulled:
        return None
    if not node.reads(frame):
        return None
    return picture(frame, node)


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
        # plan 36 T4 (W4): one ring per look-back node, by its name
        # (`ring`) — `lookback`'s is this one, on the `dream.*` params'
        # state — and the dream node's buffer and worker slot, apart from
        # any look-back (`dreamer.source`: app.py hangs the worker there)
        self.lookback = Lookback(ctx, dream)
        self.rings: dict[str, Lookback] = {self.lookback.name: self.lookback}
        self.dreamer = Dreamer(ctx, self.lookback.state)
        self.fx = FxChain(ctx, fx)      # every effect node's programs and textures
        # the picture the faces show while something other than the
        # pattern is wired into them (plan 33 R: `shape.faces`, painted by
        # the graph at FACE_PIC², `graph.Shape.prepare`). Nothing is
        # allocated until then. face_error says why it could not be made
        # (the frame is then drawn as with the faces unwired); _pic is the
        # picture the graph hands the one scene pass it wraps, _face_layer
        # what the pattern's media layer reads that pass (False: no frame
        # running — the wiring's channel, `_face_media`)
        self.face_pic = FaceTarget(ctx)
        self.pattern_pic = FaceTarget(ctx)
        self.face_error = ""
        self._pic: moderngl.Texture | None = None
        self._face_layer = False
        # plan 36 T2: the faces plain this scene pass — `shape.faces` unwired,
        # no pattern drawn (`graph.Shape.prepare`; False outside a frame)
        self._face_plain = False
        self.ghost = Ghost(ctx, ghost)  # the hands, last, over everything (ghost.py)
        # plan 21: the outputs. A picture with more than one consumer (or
        # one not drawn here) ends in a frame texture, one per end (plan 35:
        # keyed by the end's name), made on first use; the program that
        # shows one on an output, too. `stats` is what the last frame ran
        self._frames: dict[str, tuple[moderngl.Texture, moderngl.Framebuffer]] = {}
        self._show_prog: moderngl.Program | None = None
        self._show_vao: moderngl.VertexArray | None = None
        # plan 26 A3: the program a Composite node lays a layer with, on
        # first use; and the wiring the frame is built from — plan 36 T3
        # (W3): the empty frame (black) until a preset's graph lands one
        self._lay_prog: moderngl.Program | None = None
        self._lay_vao: moderngl.VertexArray | None = None
        self.wiring = EMPTY
        # plan 26 A4b: what the point-cloud nodes read — the device
        # registry (app hands it over; duck-typed: `clouds` and its
        # devices' kinds). None: no cloud is drawn
        self.cloud_source = None
        # plan 36 T1: whoever holds the rig's own wires (the open show,
        # `library.Project.rig`, by `app`); None: every bus cable standing
        self.rig_source = None
        # plan 26 A4: the extra hands nodes' states, by node name (`ghost.2`
        # …), handed over by whoever declared their params (the preset's
        # graph section, `preset.GraphSection`); their Ghosts, made on
        # first use (`ghost_of`)
        self.ghost_states: dict[str, GhostState] = {}
        self._ghosts: dict[str, Ghost] = {}
        # plan 26 A4b: the cloud nodes' GL (`graph._CloudGL`), made on first
        # draw; the getattr guards stay for a hot-reloaded renderer
        self._cloud_gl = None
        self.stats: dict = {"ends": [], "chain_runs": 0, "direct": True}
        # plan 26 A0: GPU time per node, `stats["gpu_ms"]` (the SYSTEM page)
        self.timer = PassTimer(ctx)
        # plan 26 A1: the render graph for the last frame's views, reused
        # while their count and the wiring do not change (graph.graph_key)
        self._graph: Graph | None = None
        self.cover = CoverTarget(ctx)
        self._face_verts = 0           # face vertices in _fbuf from the last scene pass (one copy)
        self._copies = 0               # copies the last scene pass drew (rows in _ibuf)
        self._scene_mats = (b"", b"")  # …and the camera they were drawn in (u_vp, u_model)
        self._blank = ctx.texture((1, 1), 4)
        self._lbuf = ctx.buffer(reserve=1200 * 6 * 13 * 4, dynamic=True)
        self._pbuf = ctx.buffer(reserve=600 * 6 * 10 * 4, dynamic=True)
        self._fbuf = ctx.buffer(reserve=2160 * 3 * 8 * 4, dynamic=True)
        self._ibuf = ctx.buffer(reserve=MAX_INSTANCES * 4 * 4, dynamic=True)   # the copies
        self._build_wire_programs()
        # the media channels (plan 32, media/channels.MediaState): app.main
        # hands the app's own; None draws no media anywhere. Their textures
        # (`media_tex.MediaTextures`) and the fit pass's program are made on
        # first use; `_media_now` is what this frame read and fitted, so a
        # channel is read (a Syphon feed's `gl_poll`) and fitted once a frame
        # however many nodes read it. `scene_ground`: the alpha the scene
        # clears to while a scene node says so (0 over the backdrop), None
        # the window's ground
        self.media = None
        self.media_tex: MediaTextures | None = None
        self._media_now: dict = {}
        self._fit_prog: moderngl.Program | None = None
        self._fit_vao: moderngl.VertexArray | None = None
        self.scene_ground: float | None = None
        # plan 32 T10: what the MEDIA page shows — the channels whose live
        # picture it draws (`media_watch`, read once at the end of the next
        # frame, `_for_the_panel`) and its thumbnails (`ui_upload`)
        self.media_watch: set[str] = set()
        self.ui_tex: UiTextures | None = None
        # plan 37 C1: the GRAPH page's thumbnails — the nodes it has on
        # screen (`PreviewTextures.want`), copied at the end of the next
        # frame (`_thumbnails`) from that frame (`_thumb_frame`, held only
        # until then)
        self.thumbs = PreviewTextures(ctx)
        self._thumb_frame: Frame | None = None
        self._view_now: ViewState | None = None    # the frame's (`_draw_frame`)
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
        # plan 39 T4: the segment nodes' workers (`segmenter`), made from
        # `segment_cfg` (the config's [segment], app.py hands it over) on a
        # node's first need — None, as the hold's preview renderer is given,
        # makes none: its segments pass their pictures through — and motion
        # mode's background models (`motion_pair`), each by its node's name
        self.segment_cfg: dict | None = None
        self._segmenters: dict = {}
        self._motions: dict[str, DelayPair] = {}
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
            inst = (self._ibuf, INST_FORMAT, "in_inst")
            lvao = ctx.vertex_array(lines, [(self._lbuf, LINE_FORMAT, "in_a", "in_b",
                                             "in_corner", "in_width", "in_alpha", "in_rgb"),
                                            inst])
            made.append(lvao)
            # the coverage pass reads the face buffer's position and divisor only
            cover_prog = ctx.program(vertex_shader=COVER_VS, fragment_shader=COVER_FS)
            made.append(cover_prog)
            cvao = ctx.vertex_array(cover_prog,
                                    [(self._fbuf, "3f 1f 16x", "in_pos", "in_w4"), inst])
            made.append(cvao)
            pvao = ctx.vertex_array(points, [(self._pbuf, POINT_FORMAT, "in_pos", "in_corner",
                                              "in_size", "in_alpha", "in_rgb"), inst])
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
        if getattr(self, "_ibuf", None) is None:     # a renderer from before the instanced draws
            self._ibuf = self.ctx.buffer(reserve=MAX_INSTANCES * 4 * 4, dynamic=True)
        self._build_wire_programs()
        for res in olds:
            res.release()
        self._build_face_program()
        # the faces' pictures are made again from the module as it is now
        # (app.py's reloader does not re-class them), rebuilt on next use. A
        # renderer from before the face target existed gets them here; one
        # from before plan 33 T7 lets its faces chain (`face_fx`) go
        old_fx, old_pic = getattr(self, "face_fx", None), getattr(self, "face_pic", None)
        old_pat = getattr(self, "pattern_pic", None)
        self.__dict__.pop("face_fx", None)
        self.face_pic = FaceTarget(self.ctx)
        self.pattern_pic = FaceTarget(self.ctx)
        self.face_error = ""
        self._pic = None
        self._face_layer = False
        self._face_plain = False
        for res in (old_fx, old_pic, old_pat):
            if res is not None:
                res.release()
        # plan 33 R: the effects' textures at other sizes (`pool_at`)
        self._release_pools()
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
        # plan 39 T2: the mask passes, likewise — compiled again from
        # masks.py as it is now on the next ask (`mask_passes`)
        mp = self.__dict__.pop("_mask_passes", None)
        if mp is not None:
            mp.release()
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
        # plan 37 C1: the thumbnails' textures and pass, made again from
        # outputs.py as it is now (the page wants them again next frame)
        if getattr(self, "thumbs", None) is not None:
            self.thumbs.close()
        self.thumbs = None
        self._drop_wire()               # (the page asks again next frame)
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
        # plan 32 R: the channels' textures and the fit pass's program, made
        # again from media_tex.py as it is now on the next frame that reads
        # a channel (a still uploads again; a feed's next frame would anyway)
        if getattr(self, "media_tex", None) is not None:
            self.media_tex.release()
        self.media_tex = None
        self._media_now = {}
        for res in (getattr(self, "_fit_vao", None), getattr(self, "_fit_prog", None)):
            if res is not None:
                res.release()
        self._fit_prog = self._fit_vao = None

    def _face_media(self, s: ViewState) -> tuple[moderngl.Texture, bool] | None:
        """The texture the faces draw over their pattern (plan 32 T7, row
        331: where the one bitmap file was) and whether it is in GL's row
        order. Plan 33 R: what the preset's graph wires into `pattern.media`
        — not `view.media`. In a frame, what the graph's pattern node read
        for this scene pass (`graph.PatternNode.layer`, handed over as
        `_face_layer`: a channel's raw texture, or a branch's picture at its
        head's size). Outside one (the FACES page's tiles, a tool) the
        channel the wiring puts in (`_channel_layer`) — straight, or through
        a switch at its pick (`graph.channel_into`, plan 33 T7; getattr: a
        view state from before the switch has no picks). None — the layer
        off — with nothing wired, no media state, or nothing on the
        channel."""
        got = getattr(self, "_face_layer", False)
        if got is not False:
            return got
        wiring = getattr(self, "wiring", None)
        c = channel_into(getattr(wiring, "wires", ()), "pattern.media",
                         getattr(s, "switch", None))
        return self._channel_layer(c) if c else None

    def _channel_layer(self, c: str) -> tuple[moderngl.Texture, bool] | None:
        """Channel `c`'s raw texture (`media_texture`: at its own size and
        aspect) and whether it is in GL's row order — the layer a channel
        wired straight into `pattern.media` draws — or None (nothing on it)."""
        if not c or c not in MEDIA_CHANNELS:
            return None
        tex = self.media_texture(c)
        if tex is None:
            return None
        return tex, not self._media_textures().flipped(c)

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
                [(self._fbuf, FACE_FORMAT, "in_pos", "in_w4", "in_uv", "in_alpha", "in_fid"),
                 (self._ibuf, INST_FORMAT, "in_inst")],
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
                for ring in self.rings.values():
                    ring.on_reload()
                self.dreamer.on_reload()

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
        exactly once, whatever the mutes). Once per distinct picture an
        output shows (its end, plan 35 `Shown`): the look-back composite and
        the effects wired to it, ending straight on the view when it is the
        end's only consumer at the frame size, else in a frame texture. Once per
        view: the picture (nothing, a 1:1 copy, or scaled into
        `outputs.fit`'s rect with the rest cleared to the view's ground),
        the hands over it, the dim (master × the view's). A view with a
        `presenter` instead of a `target` is left a `Handoff`.

        A view that raises records `view.error` (and `view.exc`) and the
        loop goes on to the next; a pipeline that raises records it on its
        views, which show their ground; the hands failing never costs the
        frame or the dim (`Ghost.error`). Every exit — a raise in the
        once-a-frame passes included — binds `views[0].target` again with
        its rect and blending. `stats` says what ran.

        Plan 32 T9: then each view's publishers (`View.publish`) are handed
        its picture (`_publish`)."""
        if not views or views[0].target is None:
            raise RuntimeError("Renderer.draw_outputs: the first view needs a target "
                               "on this context")
        ctx = self.ctx
        t = self.now(t_now)
        for v in views:
            v.error, v.exc, v.handoff = "", None, None
        self._media_now = {}          # plan 32 R: nothing read or fitted yet this frame
        first = views[0]
        target, vp = first.target, first.rect
        try:
            if self._swatch_step(s, t):          # it bound its own: the target again
                target.use()
                ctx.viewport = vp
            self._draw_frame(s, w, h, dpr, t, views)
            self._publish(views, t)
            self._for_the_panel()
        finally:
            target.use()
            ctx.viewport = vp
            ctx.enable(moderngl.BLEND)

    # ---- plan 32 T9: the outputs published out

    def _publish(self, views: list[View], t: float) -> None:
        """Each view's publishers (media/publish.py) handed its picture, a
        texture of this context with GL's rows: a publish-only view's own
        target texture (an `outputs.Offscreen`'s), else a copy in its `tap`
        — a window's framebuffer resolved into it (multisampled or not),
        a presenter's hand-off presented into it here, as that window's
        context shows it. A publisher (or a copy) that raises costs no
        view and no other publisher: the publisher is told (`fail`: its
        status and SYSTEM line say so, and it is said once) and
        `stats["publish_errors"]` names it, ``"<kind> out <name>"`` → the
        error."""
        errors: dict[str, str] = {}
        for v in views:
            pubs = getattr(v, "publish", None)
            if not pubs:
                continue
            try:
                tex = self._published(v)
            except Exception as e:  # noqa: BLE001 — a copy must not take the frame down
                tex = None
                for p in pubs:
                    _pub_failed(p, f"{type(e).__name__}: {e}", errors)
            if tex is None:
                continue
            for p in pubs:
                try:
                    p.publish(tex, t)
                except Exception as e:  # noqa: BLE001 — one publisher must not stop the rest
                    _pub_failed(p, f"{type(e).__name__}: {e}", errors)
        stats = getattr(self, "stats", None)
        if isinstance(stats, dict):
            stats["publish_errors"] = errors

    def _published(self, v: View) -> moderngl.Texture | None:
        """`v`'s picture as a texture (`_publish`), or None with none to give.
        A window's (output 1's or a presenter's) is its hand-off presented
        into its tap at the window's size under the render cap
        (`capped`, as the frame is): a 2× retina window publishes the
        frame, not a 4K upscale of it."""
        tgt = v.target
        own = getattr(tgt, "color_attachments", None) if tgt is not None else None
        if own and isinstance(own[0], moderngl.Texture) and getattr(v, "tap", None) is None:
            return own[0]
        tap, ho = getattr(v, "tap", None), v.handoff
        if tap is None or ho is None or v.size[0] <= 0 or v.size[1] <= 0:
            return None
        size = capped(v.size, getattr(self, "max_frame", None))
        ho = replace(ho, rect=fit(ho.frame_size, size))
        pres = getattr(self, "_tap_presenter", None)
        if pres is None:
            pres = self._tap_presenter = Presenter(self.ctx)
        pres.present(ho, size, target=tap.fit(size))
        return tap.tex

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
        while something is wired into `shape.faces`), the scene, the cover, the
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
        stats = {"ends": [], "chain_runs": 0, "direct": True, "captures": 0,
                 "effects": [], "layer": False, "readout": False,
                 "routes": [(None, False)] * len(views)}
        self.stats = stats
        # (the frame's view state, for the backdrop the graph is built with:
        # kept on the renderer so `_graph_for` keeps its one-argument shape)
        self._view_now = s
        # plan 33 R: the frame's size (what `_media_fit` keys its targets
        # by), and the textures made last frame at another size kept only
        # while something still asks for them
        self._frame_size = size
        self._prune_sized()
        graph = self._graph_for(views)
        # plan 34 D: each delay's pair turns — last frame's write is now
        # what its delay reads
        self._turn_delays(graph)
        # plan 36 T4: a ring no look-back of this graph holds forgets its
        # history (it starts clean when one is drawn again); the dream
        # forgets `D` with no dream node, so the worker sleeps
        self._idle_rings(graph)
        # plan 39 T4: a segment no node of this graph holds lets its worker
        # and its background model go, after `SIZED_KEEP_FRAMES`
        self._tend_segments(graph)
        # plan 30 D1: "an effect is on" means one of the pipelines' runs: an
        # effect the preset placed on an edge runs there (and moves its
        # clock in `run_one`) but bends no pipeline, so with only placed
        # effects on a through output stands down as with none. Plan 33 R:
        # the runs are the graph's (its wires), each effect asked `live`
        fx_on = any(fx.state.live(n) for n in getattr(graph, "run", ()))
        stats["fx_on"] = fx_on
        # plan 33 S: each switch's `select`, read once for the frame
        # (`ViewState.switch`, the `switch[.n].select` params' — getattr: a
        # view state from before the switch has none): what the switches
        # pass and what the graph pulls, never a rebuild
        selects = dict(getattr(s, "switch", None) or {})
        # plan 34 Z: each resize's values likewise (`ViewState.resize`)
        resizes = dict(getattr(s, "resize", None) or {})
        frame = Frame(self, ctx, s, w, h, dpr, t, views, size, _samples_of(ctx, target),
                      target, vp, bg_alpha=getattr(self, "bg_alpha", 1.0), fx_on=fx_on,
                      stats=stats, selects=selects, resizes=resizes)
        timer = self._pass_timer()
        self._thumb_frame = None
        try:
            graph.evaluate(frame)
            self._thumb_frame = frame       # plan 37 C1: the panel's thumbnails read it
        finally:
            timer.end_frame(graph.timed_in(frame))
            stats["gpu_ms"] = timer.medians()
            stats["gpu_note"] = timer.note

    def _graph_for(self, views: list[View], s: ViewState | None = None) -> Graph:
        """The render graph for these views: the last one while their count
        and the wiring have not changed (`graph.graph_key`,
        `Renderer.wiring`), else one built from them (`graph.build_graph`;
        plan 36 T3: a wired frame only, `graph.EMPTY` for none). getattr: a renderer
        from before the graph
        (or the wiring) has none. Plan 26 A4b: the `cloud` devices the
        registry lists (`cloud_source`) are part of the key, so listing
        one adds its point-cloud node to the scene. Plan 33 R: so are the
        effect files present (`FxState.specs`, as a set): each pipeline's
        run is the wiring's (`Wiring.run`, its wires), so a file that goes
        or comes builds again and a toggle does not (an off node reads
        through). A wiring that says no run (no preset's graph reached it)
        has the empty one (R23, plan 33 T7). A new graph
        fits the effects' texture pool to what it needs (`Graph.pool`).
        Plan 28 N4: the preset's wires are part of the key — they ride in
        the wiring (`Wiring.wires`, `Wiring.placed`, `Wiring.composites`),
        so an edit on the GRAPH page that lands a new `GraphSpec` builds
        the graph again, with the same refusals (a dormant wire, a loop).
        Plan 35 B, T4: every frame is a wired frame, keyed by the views'
        count alone — a window's switches are mutes, read by each output
        every frame, never a rebuild. Plan 36 T1: the rig's own wires
        (`rig_source`, the open show: `graph.rig_of`) are part of the key —
        a bus cable cut on GRAPH builds again."""
        # (`s`: the view state, unread since plan 36 T3 — the backdrop is
        # the section's wires, never laid on per frame)
        wiring = getattr(self, "wiring", None) or EMPTY
        key = graph_key(views)
        clouds = cloud_roles(getattr(self, "cloud_source", None))
        rig = rig_of(getattr(self, "rig_source", None))
        fx = getattr(self, "fx", None)
        st = fx.state if fx is not None else None
        effects = frozenset(st.specs) if st is not None else frozenset()
        graph = getattr(self, "_graph", None)
        if (graph is None or graph.key != key or getattr(graph, "wiring", None) != wiring
                or getattr(graph, "clouds", ()) != clouds
                or getattr(graph, "rig", None) != rig
                or frozenset(getattr(graph, "effects", ())) != effects):
            graph = self._graph = build_graph(views, wiring, clouds, tuple(sorted(effects)),
                                              rig)
            if fx is not None and hasattr(fx, "fit_pool"):
                fx.fit_pool(graph.pool)
            # plan 26 A4: a second hands node's Ghost the new graph does
            # not hold goes with the old graph
            self.drop_ghosts({param_prefix(n.name) for n in graph.nodes.values()
                              if isinstance(n, Hands)})
        return graph

    # ---- plan 32 T10: what the control panel draws of the media ----

    def _for_the_panel(self) -> None:
        """The end of a frame, this context current: the channels the MEDIA
        page asked for (`media_watch`, emptied here, so a page no longer
        drawn stops costing after one frame) and the thumbnails it handed
        over uploaded. A channel the frame read already has its texture,
        shown as it is; one nothing read gets a small preview
        (`MediaTextures.preview`), each at most `PREVIEW_HZ` a second and
        `PREVIEWS_PER_FRAME` a frame, round robin — eight clips playing
        under an open page cost two small copies a frame, not eight full
        uploads (final review B-I2). Never raises: the panel's pictures
        must not take the frame down."""
        watch = getattr(self, "media_watch", None) or ()
        self.media_watch = set()
        media = getattr(self, "media", None)
        now = self._media_frame_now()
        idle = sorted(c for c in watch if ("raw", c) not in now)
        if media is not None and idle:
            at = self.__dict__.setdefault("_preview_at", {})
            last = getattr(self, "_preview_last", "")
            idle.sort(key=lambda c: (c <= last, c))      # round robin: after the last one
            t = time.monotonic()
            mt = self._media_textures()
            made = 0
            for c in idle:
                if made >= PREVIEWS_PER_FRAME:
                    break
                if t - at.get(c, -1e9) < 1.0 / PREVIEW_HZ:
                    continue
                at[c] = t
                try:
                    if mt.preview(c, media.frame(c)):
                        made += 1
                        self._preview_last = c
                except Exception:  # noqa: BLE001, S110 — a preview not made stays dark
                    pass
        ui = getattr(self, "ui_tex", None)
        if ui is not None:
            try:
                ui.upload()
            except Exception:  # noqa: BLE001, S110 — a thumbnail not made stays a dark box
                pass
        self._wire()
        self._thumbnails()

    # ---- plan 37 C1: the GRAPH page's thumbnails ----

    def _thumbs(self) -> PreviewTextures:
        """The thumbnails, made on first use (getattr: a renderer from
        before plan 37, or after a reload, has none)."""
        th = getattr(self, "thumbs", None)
        if th is None:
            th = self.thumbs = PreviewTextures(self.ctx)
        return th

    def _thumbnails(self) -> None:
        """The end of a frame (`_for_the_panel`): each node the GRAPH page
        wanted since the last frame (`PreviewTextures.take`) copied into its
        thumbnail from this frame's picture of it (`thumb_source`), then the
        names not wanted for a second dropped. Nothing wanted, nothing done:
        a closed page costs nothing. A painted node is painted again here
        (`graph.picture`, into a frame texture of its own: counted as
        `PreviewTextures.repainted`) with the GPU timer muted, so the
        SYSTEM page's per-node times stay the frame's, and on a copy of the
        frame's `stats`, so its counts stay the frame's. When anything was
        copied, the render context is flushed (`glFlush`, as app.py's
        `_gl_flush` does for a presenter — not `ctx.finish`, a full sync):
        the control window's context samples the thumbnails, and output 1's
        swap is not always the next thing to flush. Never raises: the
        panel's pictures must not take the frame down."""
        frame, self._thumb_frame = getattr(self, "_thumb_frame", None), None
        th = getattr(self, "thumbs", None)
        if th is None:
            if frame is None:
                return
            th = self._thumbs()
        wanted = th.take()
        th.begin_frame()
        if wanted and frame is not None:
            timer = getattr(self, "timer", None)
            was = getattr(timer, "_active", False) if timer is not None else False
            if timer is not None:
                timer._active = True        # (`PassTimer.time` is then a no-op)
            # (the frame's counts as the frame left them: restored in place
            # after, so `self.stats` — the same dict — says what the frame ran)
            saved = {k: list(v) if isinstance(v, list) else v for k, v in frame.stats.items()}
            try:
                pulled = frame.graph.pulled(frame) if frame.graph is not None else None
                for name, how in wanted.items():
                    held = len(frame.data)
                    try:
                        src = thumb_source(frame, name, how, pulled)
                    except Exception as e:  # noqa: BLE001 — one node's picture: not the rest
                        th.error = f"{name}: {type(e).__name__}: {e}"[:120]
                        continue
                    # (a picture the frame had not made — painted, or made
                    # into a texture — leaves a new entry in the frame's data)
                    if src is not None:
                        th.put(name, src, repainted=len(frame.data) > held)
            finally:
                frame.stats.clear()
                frame.stats.update(saved)
                if timer is not None:
                    timer._active = was
            if th.count:
                _flush()
        th.end_frame()

    # ---- the shape node's wireframe (GRAPH's side panel) ----

    def want_wire(self, px: int) -> None:
        """The GRAPH page shows the shape node's details: draw the shape's
        wireframe into a `px` square at the end of the next frame (`_wire`),
        and every frame after until the page has not asked for
        `WIRE_DROP_S` — then its texture is freed, so a page not showing it
        costs nothing."""
        self.wire_asked = (max(16, min(int(px), WIRE_PX_MAX)), time.monotonic())

    def wire_texture(self) -> moderngl.Texture | None:
        """The wireframe as last drawn (GL's rows), or None: never asked, or dropped."""
        got = self.__dict__.get("_wire_gl")
        return got[0] if got is not None else None

    def _drop_wire(self) -> None:
        got, self._wire_gl = self.__dict__.get("_wire_gl"), None
        for res in (got or ())[::-1]:
            try:
                res.release()
            except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                pass

    def _wire(self) -> None:
        """The end of a frame (`_for_the_panel`), when the page asked: the
        shape as this frame drew it (`_thumb_frame`'s view state: its shape,
        angles, 3D hold, yaw and pitch) through `draw_scene` with the edges
        alone — no faces, no points, one copy, the camera's zoom and pan and
        the eye left at rest, brightness 1 — over black, into the wire's
        own square. The scene pass's buffers it writes are rewritten by the
        next frame's before anything reads them; what the cover pass reads
        of the last pass (`_face_verts`, `_copies`, `_scene_mats`) is put
        back; flushed, as the thumbnails are. Never raises: the panel's pictures must not take the frame down."""
        asked = getattr(self, "wire_asked", None)
        if asked is None:
            return
        px, at = asked
        if time.monotonic() - at >= WIRE_DROP_S:
            self.wire_asked = None
            self._drop_wire()
            return
        frame = getattr(self, "_thumb_frame", None)
        if frame is None:
            return
        ctx = self.ctx
        saved = (self._face_verts, self._copies, self._scene_mats)
        try:
            got = self.__dict__.get("_wire_gl")
            if got is None or tuple(got[0].size) != (px, px):
                self._drop_wire()
                tex = ctx.texture((px, px), 4)
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                got = self._wire_gl = (tex, ctx.framebuffer(color_attachments=[tex]))
            ws = replace(frame.s, faces=False, points=False, lines=True, lines_alpha=1.0,
                         bright=1.0, instances=1, inst_fit=False, zoom=1.0, pan=[0.0, 0.0],
                         eye_fov=EYE_FOV, eye_distance=EYE_DISTANCE, screen_strokes=False)
            got[1].use()
            ctx.viewport = (0, 0, px, px)
            ctx.clear(0.0, 0.0, 0.0, 1.0)
            self.draw_scene(ws, px, px, clear=False)
            _flush()                    # (the control window samples it: as `_thumbnails`)
            self.wire_error = ""
        except Exception as e:  # noqa: BLE001 — a wireframe not drawn stays black
            self.wire_error = f"{type(e).__name__}: {e}"[:120]
        finally:
            self._face_verts, self._copies, self._scene_mats = saved
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def media_shown(self, c: str) -> tuple[moderngl.Texture, bool] | None:
        """Channel `c`'s raw texture as this frame read it, and whether its
        rows are top first (`MediaTextures.flipped`) — or None: nothing read
        it this frame, or it had no picture. Reads nothing itself: the MEDIA
        page draws it after the frame (`media_watch` asks for it)."""
        now = self._media_frame_now()
        if ("raw", c) in now:            # the frame read it: its own texture
            tex = now[("raw", c)]
            return None if tex is None else (tex, self._media_textures().flipped(c))
        return self._media_textures().shown(c)        # else the page's preview

    def _ui_textures(self) -> UiTextures:
        ui = getattr(self, "ui_tex", None)
        if ui is None:
            ui = self.ui_tex = UiTextures(self.ctx)
        return ui

    def ui_texture(self, key):
        """A picture the panel handed over (`ui_upload`), once uploaded; else None."""
        return self._ui_textures().get(key)

    def ui_upload(self, key, size: tuple[int, int], data: bytes) -> None:
        """RGBA8 pixels for the panel, uploaded at the end of the next frame."""
        self._ui_textures().put(key, size, data)

    # ---- plan 32 R: the media channels' pictures ----

    def _media_textures(self) -> MediaTextures:
        """The channels' textures, made on first use (getattr: a renderer
        from before the media, or after a reload, has none)."""
        mt = getattr(self, "media_tex", None)
        if mt is None:
            mt = self.media_tex = MediaTextures(self.ctx)
        return mt

    def _media_frame_now(self) -> dict:
        now = getattr(self, "_media_now", None)
        if now is None:
            now = self._media_now = {}
        return now

    def media_now(self, c: str) -> tuple[object | None, int]:
        """Channel `c`'s newest frame this frame — the `MediaFrame` its
        texture was uploaded from (None: black) — and its fit (`media.<c>.
        fit`: 0 cover): the segment's shortcut to a camera's or a feed's CPU
        pixels (plan 39 T4), read once a frame with the texture."""
        self.media_texture(c)
        ch = getattr(getattr(self, "media", None), "channels", {}).get(c)
        return self._media_frame_now().get(("frame", c)), int(getattr(ch, "fit", 0) or 0)

    def media_texture(self, c: str) -> moderngl.Texture | None:
        """Channel `c`'s raw texture this frame — the picture at its own
        size and aspect, for the faces — or None (black). The channel is
        read once a frame however often this is asked (`MediaState.frame`:
        a Syphon feed through its `gl_poll`, here on the frame thread) and
        uploaded only when its frame moved. Never waits: a frame not
        decoded yet is None. Rows are top first unless the texture is a
        feed's own (`MediaTextures.flipped`)."""
        media = getattr(self, "media", None)
        if media is None:
            return None
        now = self._media_frame_now()
        key = ("raw", c)
        if key not in now:
            try:
                f = media.frame(c)
            except Exception:  # noqa: BLE001 — a channel must not take the frame down
                f = None
            now[("frame", c)] = f         # (plan 39 T4: `media_now`)
            now[key] = self._media_textures().texture(c, f)
        return now[key]

    def _media_fit(self, c: str, size: tuple[int, int],
                   alpha: float = 1.0) -> moderngl.Texture | None:
        """Channel `c` fitted to a frame of `size` (`media.<c>.fit`: cover,
        contain, stretch), premultiplied by `alpha`: one pass into a
        texture of the renderer's (`_frame_target`, one per channel and
        alpha 1 or not), once a frame per (channel, size, alpha, fit). With
        no picture it is transparent black — a texture all the same, so an
        `IMAGE` port always has one. Leaves its target bound."""
        ch = getattr(getattr(self, "media", None), "channels", {}).get(c)
        fit = int(getattr(ch, "fit", 0) or 0)
        size = (int(size[0]), int(size[1]))
        alpha = min(max(float(alpha), 0.0), 1.0)
        now = self._media_frame_now()
        key = ("fit", c, size, alpha, fit)
        if key in now:
            return now[key]
        src = self.media_texture(c)
        # (plan 33 R: fitted at another size than the frame's — a branch on
        # the faces — it is a target of its own, `(name, size)`)
        name = f"media.{c}" if alpha >= 1.0 else f"media.{c}@alpha"
        at = getattr(self, "_frame_size", None)
        out, fbo = self._frame_target(name if at is None or size == tuple(at)
                                      else (name, size), size)
        ctx = self.ctx
        fbo.use()
        ctx.viewport = (0, 0, *size)
        if src is None or alpha <= 0.0:
            ctx.clear(0.0, 0.0, 0.0, 0.0)
        else:
            prog, vao = self._fit_program()
            ctx.disable(moderngl.BLEND)
            try:
                src.use(location=0)
                prog["u_src"].value = 0
                prog["u_scale"].value = fit_scale(fit, tuple(src.size), size)
                prog["u_flip"].value = int(self._media_textures().flipped(c))
                prog["u_alpha"].value = alpha
                vao.render(moderngl.TRIANGLES, vertices=3)
            finally:
                ctx.enable(moderngl.BLEND)
        now[key] = out
        return out

    def _fit_program(self) -> tuple[moderngl.Program, moderngl.VertexArray]:
        """The fit pass's program (`media_tex.FIT_FS`), built on first use."""
        prog, vao = getattr(self, "_fit_prog", None), getattr(self, "_fit_vao", None)
        if prog is not None and vao is not None:
            return prog, vao
        prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=FIT_FS)
        try:
            vao = self.ctx.vertex_array(prog, [])
        except Exception:
            prog.release()
            raise
        self._fit_prog, self._fit_vao = prog, vao
        return prog, vao

    def _refit(self, tex: moderngl.Texture, dst: moderngl.Framebuffer,
               crop: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
               fit: int = COVER, filter: str = "linear",
               clamp: tuple[float, float, float, float] | None = None,
               mip: bool = False) -> None:
        """`tex`'s `crop` (x0, y0, w, h in its GL uv) fitted by `fit`
        (`media_tex.FITS`) into `dst`'s viewport, blending off, the texels
        as they are (premultiplied in and out), transparent black outside
        the fit (plan 34 D, row 358; `REFIT_FS`). `clamp` (min u, min v,
        max u, max v) bounds the samples (the crop itself when None). The
        filter is a sampler object's (`_sampler`: linear, or nearest; `mip`
        trilinear from mipmaps built here), so the texture's own filter —
        a shared one's, the scene's — is never changed. Blending is on
        again on every exit."""
        prog, vao = self._refit_program()
        ctx = self.ctx
        rect = tuple(dst.viewport)
        x0, y0, cw, ch = (float(v) for v in crop)
        lo_hi = clamp if clamp is not None else (x0, y0, x0 + cw, y0 + ch)
        sampler = self._sampler(filter, mip)
        dst.use()
        ctx.viewport = rect
        ctx.disable(moderngl.BLEND)
        try:
            if mip:
                was = tex.filter
                tex.build_mipmaps()
                tex.filter = was
            tex.use(location=0)
            sampler.use(location=0)
            prog["u_src"].value = 0
            prog["u_crop"].value = (x0, y0, cw, ch)
            prog["u_scale"].value = fit_scale(
                fit, (max(cw * tex.size[0], 1.0), max(ch * tex.size[1], 1.0)),
                (int(rect[2]), int(rect[3])))
            prog["u_clamp"].value = tuple(float(v) for v in lo_hi)
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            sampler.clear(location=0)
            ctx.enable(moderngl.BLEND)

    def _refit_program(self) -> tuple[moderngl.Program, moderngl.VertexArray]:
        """`_refit`'s program (`REFIT_FS`), built on first use (getattr: a
        renderer from before plan 34 has none)."""
        prog, vao = getattr(self, "_refit_prog", None), getattr(self, "_refit_vao", None)
        if prog is not None and vao is not None:
            return prog, vao
        prog = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=REFIT_FS)
        try:
            vao = self.ctx.vertex_array(prog, [])
        except Exception:
            prog.release()
            raise
        self._refit_prog, self._refit_vao = prog, vao
        return prog, vao

    def _sampler(self, filter: str = "linear", mip: bool = False
                 ) -> moderngl.Sampler:
        """A sampler object for `_refit`, made once per (filter, mip) and
        kept: clamped, linear (trilinear with `mip`) or nearest."""
        cache = self.__dict__.setdefault("_samplers", {})
        key = (filter, bool(mip))
        got = cache.get(key)
        if got is None:
            if filter == "nearest":
                f = (moderngl.NEAREST_MIPMAP_NEAREST if mip else moderngl.NEAREST,
                     moderngl.NEAREST)
            else:
                f = (moderngl.LINEAR_MIPMAP_LINEAR if mip else moderngl.LINEAR,
                     moderngl.LINEAR)
            got = cache[key] = self.ctx.sampler(repeat_x=False, repeat_y=False, filter=f)
        return got

    def _compose(self, v: View, key: str | None, after: bool,
                 frames: dict[str, moderngl.Texture | None], failed: set[str],
                 size: tuple[int, int], readout: moderngl.Texture | None = None,
                 lay=None, blend: str = "over", ghost: Ghost | None = None,
                 readout_ghost: Ghost | None = None,
                 hands_tex: moderngl.Texture | None = None) -> None:
        """One view's picture: its end's frame (`key`, the end's name, plan
        35 `Shown`: `shown(lookback)` …; already there when it was drawn
        direct; None, its ground), the hands over it in the same rect, the readout layer over
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
        if v.target is None or getattr(v, "tap", None) is not None:
            if v.target is None and v.presenter is None:
                raise RuntimeError("a view needs a target or a presenter")
            # a presenter's hand-off — and (plan 32 T9) a published
            # window's, which `_published` presents into its tap at the
            # capped size (the window itself is drawn below as ever)
            rx, ry, rw, rh = v.rect
            ix, iy, iw, ih = fit(size, (rw, rh))
            v.handoff = Handoff(frame, size, (rx + ix, ry + iy, iw, ih),
                                hands=((hands_tex if hands_tex is not None else gh.tex)
                                       if after else None), readout=readout,
                                alpha=float(gh.state.alpha), factor=factor,
                                bg_alpha=float(v.bg_alpha), flip=flip,
                                blend="add" if blend == "add" else "over")
            if v.target is None:
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

    def _frame_target(self, key, size: tuple[int, int], dtype: str = "f1",
                      components: int = 4
                      ) -> tuple[moderngl.Texture, moderngl.Framebuffer]:
        """The frame texture for an end (plan 35: by its name): RGBA8 at the frame's size,
        LINEAR (a 1:1 show reads it by texelFetch), made on first use and
        again when the frame's size changes. Plan 33 R: a key that is
        `(name, size)` (a picture made at another size, `graph.Frame.key`)
        lives while some frame asks for it (`_prune_sized`) — R16: as does
        any other key, after `SIZED_KEEP_FRAMES` idle. Plan 34 D:
        `dtype` "f2" a half-float one (a delay's picture refitted, which
        must not quantise); a stored texture of another dtype is made
        again. Plan 39 T2: `components` 1 a one-channel one (a mask,
        `masks.MaskPasses`), likewise made again when it differs."""
        frames = getattr(self, "_frames", None)
        if frames is None:
            frames = self._frames = {}
        # R16 (final review): every key asked for is marked — a string
        # key (an end's `shown(...)`, a `#fit`) is pruned when idle as a
        # `(name, size)` one is, so a load leaves nothing of the last preset
        self.__dict__.setdefault("_sized_used", set()).add(key)
        have = frames.get(key)
        if (have is not None and have[0].size == size
                and getattr(have[0], "dtype", "f1") == dtype
                and getattr(have[0], "components", 4) == components):
            return have
        if have is not None:
            for res in (have[1], have[0]):
                res.release()
            del frames[key]
        tex = (self.ctx.texture(size, components) if dtype == "f1"
               else self.ctx.texture(size, components, dtype=dtype))
        try:
            tex.repeat_x = tex.repeat_y = False
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            fbo = self.ctx.framebuffer(color_attachments=[tex])
        except Exception:
            tex.release()
            raise
        frames[key] = (tex, fbo)
        return tex, fbo

    def mask_passes(self) -> MaskPasses:
        """The mask passes (plan 39 T2, `masks.MaskPasses`): compiled on
        first ask and kept, handed `_frame_target` for their one-channel
        targets (late-bound, so a spy on it sees their asks too). What the
        graph's mask nodes paint through (`graph.MatteNode`, `MaskPicture`)."""
        got = self.__dict__.get("_mask_passes")
        if got is None:
            got = self._mask_passes = MaskPasses(
                self.ctx, lambda *a, **k: self._frame_target(*a, **k))
        return got

    def _release_frames(self) -> None:
        for tex, fbo in (getattr(self, "_frames", None) or {}).values():
            fbo.release()
            tex.release()
        self._frames = {}

    def pool_at(self, size: tuple[int, int], n: int
                ) -> list[tuple[moderngl.Texture, moderngl.Framebuffer]]:
        """The effects' half-float textures at `size`, at least `n` (plan 33
        R, `graph.Frame.pool`): a branch made at a size not the frame's —
        the faces' FACE_PIC², the pattern's layer at its channel's — paints
        through these, as one at the frame's size does through the chain's
        pool (`FxChain.pool`), so neither is made again for the other. Grown
        by appending; a size no frame asked for is released
        (`_prune_sized`)."""
        size = (int(size[0]), int(size[1]))
        pools = self.__dict__.setdefault("_pools", {})
        self.__dict__.setdefault("_pools_used", set()).add(size)
        pool = pools.setdefault(size, [])
        while len(pool) < n:
            tex = self.ctx.texture(size, 4, dtype="f2")
            try:
                tex.repeat_x = tex.repeat_y = False
                fbo = self.ctx.framebuffer(color_attachments=[tex])
            except Exception:
                tex.release()
                raise
            pool.append((tex, fbo))
        return list(pool)

    def _release_pools(self) -> None:
        for pool in (getattr(self, "_pools", None) or {}).values():
            for tex, fbo in pool:
                fbo.release()
                tex.release()
        self._pools = {}
        self._pools_used = set()

    def delay_pair(self, name: str) -> DelayPair:
        """Delay `name`'s pair (plan 34 D, row 354), made on first ask and
        kept by name across graph rebuilds — an edit elsewhere on GRAPH
        does not cut the feedback; a preset load does (`reset_delays`, R19)
        (__dict__: a renderer from before plan 34 has none)."""
        pairs = self.__dict__.setdefault("_delays", {})
        got = pairs.get(name)
        if got is None:
            got = pairs[name] = DelayPair()
        return got

    def segmenter(self, name: str):
        """Segment node `name`'s worker (plan 39 T4, `segment.SegmentWorker`),
        made on its first need from `segment_cfg` and kept by name across
        graph rebuilds — or None on a renderer with no `segment_cfg` (the
        hold's preview: only the program renderer runs a model). Closed when
        no graph has held its node for `SIZED_KEEP_FRAMES` (`_tend_segments`)
        and in `close`. `segment_factory(cfg, name)`, when set, makes it
        instead (tests). segment.py is imported here, on the first need,
        never by graph.py nor on `import hyperspace.app`."""
        cfg = getattr(self, "segment_cfg", None)
        if cfg is None:
            return None
        workers = self.__dict__.setdefault("_segmenters", {})
        got = workers.get(name)
        if got is None:
            make = getattr(self, "segment_factory", None)
            if make is None:
                from . import segment

                make = segment.make_worker
            got = workers[name] = make(cfg, name)
        return got

    def motion_pair(self, name: str) -> DelayPair:
        """Segment node `name`'s background model in motion mode (plan 39
        T4): a half-float pair on the delay's pattern (`DelayPair`), made on
        first ask and kept by name across graph rebuilds; the node writes
        one side and turns it once a frame. Released with its worker."""
        pairs = self.__dict__.setdefault("_motions", {})
        got = pairs.get(name)
        if got is None:
            got = pairs[name] = DelayPair()
        return got

    def _tend_segments(self, graph: Graph) -> None:
        """Once a frame: each worker and background model whose segment no
        node of `graph` is counts a frame idle, and goes at
        `SIZED_KEEP_FRAMES` (half a second at 60 fps) — the worker stopped
        (never joined here: its thread ends after any run in hand, `close`
        joins it at the exit), the pair released. Never raises."""
        workers = self.__dict__.get("_segmenters") or {}
        pairs = self.__dict__.get("_motions") or {}
        stopped = self.__dict__.get("_stopped")
        if stopped:                      # (those stopped earlier, once their threads end)
            self._stopped = [w for w in stopped if getattr(w, "alive", False)]
        if not workers and not pairs:
            return
        held = {n.name for n in getattr(graph, "nodes", {}).values()
                if isinstance(n, SegmentNode)}
        idle = self.__dict__.setdefault("_segment_idle", {})
        for name in {*workers, *pairs}:
            if name in held:
                idle.pop(name, None)
                continue
            idle[name] = idle.get(name, 0) + 1
            if idle[name] < SIZED_KEEP_FRAMES:
                continue
            del idle[name]
            try:
                w = workers.pop(name, None)
                if w is not None:
                    # (stopped, never joined here: the frame thread does not
                    # wait on a model's last run — `close` joins at the exit)
                    w.stop()
                    self.__dict__.setdefault("_stopped", []).append(w)
                pair = pairs.pop(name, None)
                if pair is not None:
                    pair.release()
            except Exception:  # noqa: BLE001, S110 — a lost context: nothing to free
                pass

    def close(self, timeout: float = 1.0) -> None:
        """This renderer's own segment workers closed (plan 39 T4; app.py's
        close list, at quit and restart) — all stopped first, then joined
        against one shared deadline of `timeout` seconds, the ones
        `_tend_segments` stopped earlier too — never anything another
        renderer shares (the hold's preview has none of its own). Threads
        only: the GL it holds goes with its context, which may not be
        current at this point of the exit."""
        workers = [*(self.__dict__.get("_segmenters") or {}).values(),
                   *(self.__dict__.get("_stopped") or [])]
        for w in workers:
            try:
                w.stop()
            except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                pass
        end = time.perf_counter() + timeout
        for w in workers:
            try:
                w.close(max(0.0, end - time.perf_counter()))
            except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                pass
        self._segmenters = {}
        self._stopped = []

    def reset_delays(self) -> None:
        """R19 (final review, row 354): a preset load landed a new section —
        at the next turn every pair holds nothing (as on its first frame),
        so no trail of the last preset shows in the new one. A GRAPH edit
        or rebuild does not ask: the feedback runs on across those. The
        textures are kept; only what they hold is forgotten."""
        self.__dict__["_delays_reset"] = True

    def _turn_delays(self, graph: Graph) -> None:
        """Once a frame, before the graph runs: every pair turns (a pair
        written last frame now reads it; one not written holds nothing). A
        pair whose delay is in no node of `graph` counts a frame idle and
        is released at `SIZED_KEEP_FRAMES`, with its refitted picture
        (`<name>#fit`); one in the graph is idle 0. After `reset_delays`
        (a load, R19) every pair holds nothing this frame. Never raises."""
        pairs = getattr(self, "_delays", None)
        reset = getattr(self, "_delays_reset", False)
        if reset:
            self._delays_reset = False
        if not pairs:
            return
        if reset:
            for pair in pairs.values():
                pair.wrote = False      # (so `turn` holds nothing this frame)
        held = {n.name for n in getattr(graph, "nodes", {}).values() if isinstance(n, Delay)}
        for name in list(pairs):
            pair = pairs[name]
            pair.turn()
            if name in held:
                pair.idle = 0
                continue
            pair.idle += 1
            if pair.idle < SIZED_KEEP_FRAMES:
                continue
            del pairs[name]
            try:
                pair.release()
                fit = (getattr(self, "_frames", None) or {}).pop(name + "#fit", None)
                if fit is not None:
                    fit[1].release()
                    fit[0].release()
            except Exception:  # noqa: BLE001, S110 — a lost context: nothing to free
                pass

    def _prune_sized(self) -> None:
        """Once a frame, first: release the pools (`pool_at`) and the frame
        textures (R16: every key — `(name, size)`, an end's `shown(...)`, a
        `#fit`, a channel's fit) that no frame has asked for in the last
        `SIZED_KEEP_FRAMES` — a channel whose clip changed size, a branch
        unwired, the preset before a load — so pictures never pile up,
        and (R29) a switch flicked every frame between branches of other
        sizes reallocates nothing: the branch not picked keeps its
        textures for the next flick."""
        # (__dict__: a renderer from before a hot reload has no idle counts;
        # a key's count is the frames since it was last asked for)
        idle = self.__dict__.setdefault("_sized_idle", {})

        def stale(key, used: set) -> bool:
            if key[1] in used:
                idle.pop(key, None)
                return False
            idle[key] = idle.get(key, 0) + 1
            if idle[key] < SIZED_KEEP_FRAMES:
                return False
            del idle[key]
            return True

        pools = getattr(self, "_pools", None) or {}
        used = getattr(self, "_pools_used", None) or set()
        for size in [k for k in pools if stale(("pool", k), used)]:
            for tex, fbo in pools.pop(size):
                fbo.release()
                tex.release()
        self._pools_used = set()
        frames = getattr(self, "_frames", None) or {}
        used = getattr(self, "_sized_used", None)
        if used is None:
            used = self._sized_used = set()
        for key in [k for k in frames if stale(("frame", k), used)]:
            tex, fbo = frames.pop(key)
            try:
                fbo.release()
                tex.release()
            except Exception:  # noqa: BLE001, S110 — a lost context: nothing to free
                pass
        used.clear()

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

    def ring(self, name: str = "lookback", state: DreamState | None = None) -> Lookback:
        """Look-back `name`'s ring (plan 36 T4), made on first ask: its own
        echoes, clock and atlas. `lookback`'s is `self.lookback` (the
        `dream.*` params' state); another's reads `state` (its
        `dream.<n>.*`, `ViewState.lookback`) when given, else a default."""
        rings = self.__dict__.setdefault("rings", {})
        got = rings.get(name)
        if got is None:
            if name == "lookback" and getattr(self, "lookback", None) is not None:
                got = self.lookback
            else:
                got = Lookback(self.ctx, state if state is not None else DreamState(), name)
            rings[name] = got
        elif state is not None and got.state is not state:
            got.state = state
        return got

    def _idle_rings(self, graph: Graph) -> None:
        """Each ring whose look-back this graph does not hold forgets its
        history; every one but `lookback`'s is also dropped then, its textures
        released (made again, clean, when a graph holds it). No dream node:
        `D` forgotten."""
        rings = getattr(self, "rings", None) or {}
        held = set(getattr(graph, "nodes", {}))
        for name in list(rings):
            if name in held:
                continue
            rings[name].idle()
            if name != "lookback":
                rings.pop(name).release_ring()
        dreamer = getattr(self, "dreamer", None)
        if dreamer is not None and "dream" not in held:
            dreamer.idle()

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

    def _face_picture(self, s: ViewState, t: float, paint=None) -> moderngl.Texture | None:
        """The picture the faces show this frame, or None for "as ever"
        (the pattern per face). Plan 33 R: `paint` paints what the graph
        wires into `shape.faces` at FACE_PIC² into a framebuffer
        (`graph.Shape.prepare`) — from the pattern through effects, the
        faces' chain as it always ran: the seed (what face 0 shows: pattern
        and bitmap, premultiplied by its intensity) into the first texture,
        the effects one after another, the last into the picture — then
        the picture's mipmaps.

        None, with nothing run and nothing allocated, unless something is
        to be painted, the faces are on, there is a copy to draw and the
        face program built. A pass that raises is caught here: `face_error`
        says why, the frame is drawn as with the faces unwired, and the
        caller binds the scene's framebuffer next whatever this left bound."""
        # getattr: a renderer from before a hot reload has no face picture
        pic = getattr(self, "face_pic", None)
        seed, vao = getattr(self, "_seed_prog", None), getattr(self, "_seed_vao", None)
        if (paint is None or pic is None or seed is None or vao is None
                or self._face_prog is None or not s.faces or int(s.instances) <= 0):
            self.face_error = ""     # no pass asked for: nothing is wrong with it
            return None
        ctx = self.ctx
        try:
            pic.ensure()
            paint(pic.fbo)
            pic.tex.build_mipmaps()
        except Exception as e:  # noqa: BLE001 — the faces' effects must not take the frame down
            self.face_error = f"faces: {type(e).__name__}: {e}"[:160]
            return None
        finally:
            ctx.enable(moderngl.BLEND)
        self.face_error = ""
        return pic.tex

    def _pattern_into(self, dst: moderngl.Framebuffer, s: ViewState, t: float,
                      media) -> None:
        """The pattern as a picture (plan 33 R, `graph.PatternNode`): the
        seed — what face 0 shows, the pattern and `media` (the layer's
        (texture, GL row order) or None) over it, premultiplied by its
        intensity — into `dst` at its own viewport, blending off, as the
        faces' chain always seeded its first texture. Transparent black
        while the seed did not build. Leaves `dst` bound."""
        ctx = self.ctx
        seed, vao = getattr(self, "_seed_prog", None), getattr(self, "_seed_vao", None)
        dst.use()
        if seed is None or vao is None:
            ctx.clear(0.0, 0.0, 0.0, 0.0, viewport=tuple(dst.viewport))
            return
        ctx.disable(moderngl.BLEND)
        try:
            self._face_uniforms(seed, s, t, media=media)
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)

    def _pattern_picture(self, s: ViewState, t: float, media) -> moderngl.Texture:
        """The pattern's picture as a texture (plan 33 R): `_pattern_into` a
        FACE_PIC² `FaceTarget` of its own (`pattern_pic`), mipmapped — what
        a consumer that binds the pattern's picture reads (a composite, an
        output's hands port). getattr: a renderer from before plan 33."""
        pic = getattr(self, "pattern_pic", None)
        if pic is None:
            pic = self.pattern_pic = FaceTarget(self.ctx)
        pic.ensure()
        self._pattern_into(pic.fbo, s, t, media)
        pic.tex.build_mipmaps()
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
                       ptime: float | None = None, media=_UNSET) -> None:
        """What the pattern and the bitmap read, on `p` — the face program
        or the seed — with the bitmap's texture on unit 0. The patterns'
        clock is the live one unless a still pins it (`ptime`); the clocks
        are set only if the patterns read them (an edit may not). `media`:
        the media layer's (texture, GL row order) or None, as the pattern
        node read it (plan 33 R); left out, `_face_media`'s."""
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
        # the media layer (plan 32, row 331: a channel where the bitmap file
        # was), with the bitmap's alpha, size and path. Each uniform guarded:
        # a program that never reads the layer (an edit, a frozen test
        # program) has had them trimmed
        def put(name, value):
            try:
                p[name].value = value
            except KeyError:
                pass

        # (plan 33 R: the layer is what `pattern.media` reads — `media`,
        # handed in by the pattern node, else `_face_media` — never
        # `view.media`)
        if media is _UNSET:
            media = self._face_media(s) if s.media_alpha > 0.0 else None
        got = media if s.media_alpha > 0.0 else None
        put("u_bmp_on", int(got is not None))
        if got is not None:
            tex, upright = got
            tex.use(location=0)
            put("u_bitmap", 0)
            put("u_bmp_flip", int(upright))
            tw, th = tex.size
            put("u_bmp_scale", (s.media_scale, s.media_scale * th / tw))
            put("u_bmp_alpha", float(s.media_alpha))
            # the layer's own path about the face centre — independent
            # of the instance-grid motion
            ph = t * s.media_rate
            if s.media_mode == 1:      # orbit
                ox, oy = math.cos(ph), math.sin(ph)
            elif s.media_mode == 2:    # figure-8
                ox, oy = math.sin(ph), math.sin(2.0 * ph) * 0.5
            elif s.media_mode == 3:    # sway
                ox, oy = math.sin(ph), 0.0
            else:                      # still
                ox = oy = 0.0
            put("u_bmp_pos", (s.media_amp * ox, s.media_amp * oy))

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
            one = replace(s, pattern=mode, pattern_mix=1.0, media_alpha=0.0)
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
        if self._face_verts and self._copies:
            ctx.disable(moderngl.BLEND)
            # the scene pass's camera, as it drew those vertices
            vp, model = self._scene_mats
            self._cover_prog["u_vp"].write(vp)
            self._cover_prog["u_model"].write(model)
            self._cvao.render(moderngl.TRIANGLES, vertices=self._face_verts,
                              instances=self._copies)
            ctx.enable(moderngl.BLEND)
        return self.cover.tex

    def clear_scene(self) -> None:
        """The scene's clear, into whatever is bound: the premultiplied
        ground (black at `bg_alpha`) and the depth to the far plane. The
        scene node clears before its solid geometry (plan 26 A3); a scene
        of the shape alone clears inside `draw_scene`, as it always did.
        Plan 32 R: at `scene_ground` instead while a scene node sets it
        (0 over the backdrop)."""
        self.ctx.clear(*BG, self._scene_ground())

    def _scene_ground(self) -> float:
        """The scene's ground alpha: `scene_ground` while a scene node sets
        it (plan 32 R: 0, see-through over the backdrop), else `bg_alpha`."""
        g = getattr(self, "scene_ground", None)
        return float(g) if g is not None else float(getattr(self, "bg_alpha", 1.0))

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
        (`geometry.shape_world`), the GPU on to the clip through each
        copy's place (its scale and centre, the camera's zoom and pan with
        them: `_copies_of`, field.py) and the eye (`eye.*`,
        `geometry.eye_matrix`). The see-through shape is painter-sorted
        as before and drawn with the depth test on but no depth written
        (whatever solid geometry is already in the depth buffer hides it;
        A3's hands), then `_depth_pass` writes its nearest visible
        surface for what comes after.

        Plan 26 A3: `clear` False draws over what is bound — the scene node
        cleared it and drew the solid geometry (the hands) first, whose
        depth hides the shape behind them."""
        g = geom(s.shape)
        # a 3D shape is drawn with no W turn and cues on its depth toward
        # the 3D camera; a 4D shape is turned to its body first, and with
        # the 3D switch holding it (ViewState.held, set by integrate) by
        # its 3D angles alone; a scene, each layer at its own
        # (geometry.shape_world, plan 28's catalog)
        P, w4, pd = shape_world(s.shape, s.ang, s.yaw, s.pitch, d4=s.depth4,
                                flat=getattr(s, "held", False), body=getattr(s, "body", None))
        # a scene's per-layer weights (geometry._scene_style), else None
        st = g.get("style")

        # the camera: the shape's world transform and the eye, as the vertex
        # shaders take them (column-major). Two ways to place the copies:
        # a flat layout (or one copy) with Fit off is the field it always was — the
        # copies' offsets in the world at scale 1, the camera's zoom and pan
        # the world transform (`model_matrix`), the strokes scaled on the
        # CPU — so its frames are byte for byte what they were; Fit and the
        # 3D lattices are field.py's, each copy's own scale and centre with
        # the camera in them, the world transform the identity, the strokes
        # scaled per copy in the shaders (`_copies_of`)
        zoom = max(s.zoom, 1e-3)
        legacy = not getattr(s, "inst_fit", False) and (
            int(s.instances) <= 1 or not is_3d_layout(int(getattr(s, "inst_layout", 0))))
        model = model_matrix(zoom, s.pan) if legacy else model_matrix(1.0, (0.0, 0.0))
        vp = eye_matrix(w, h, getattr(s, "eye_fov", EYE_FOV),
                        getattr(s, "eye_distance", EYE_DISTANCE))
        mats = (np.asarray(vp, dtype="f4").T.tobytes(),
                np.asarray(model, dtype="f4").T.tobytes())
        self._scene_mats = mats

        n_inst = max(0, int(s.instances))   # 0: the ground alone (returns below)
        t_m = self.now(t_now)

        near, far = pd.min(), pd.max()
        span = max(far - near, 1e-6)
        if span < DEPTH_FLOOR:
            # a shape turned flat toward the eye (the Orbit face-on, the Flow
            # mark) has almost no depth, and stretching that sliver over the
            # whole cue would put it at its dimmest: the cue never spans less
            # than DEPTH_FLOOR back from the nearest point. Face-on it draws
            # at full weight, a tilt dims its far side; a shape any deeper
            # draws as it always did
            near, span = far - DEPTH_FLOOR, DEPTH_FLOOR
        E = g["E"]
        edepth = (pd[E[:, 0]] + pd[E[:, 1]]) * 0.5
        order = np.argsort(edepth, kind="stable")  # painter: far first

        t = (edepth[order] - near) / span
        dens = clamp(340 / max(g["m"], 1), 0.42, 1)
        heavy = g["m"] > 500
        B = s.bright * dens
        alpha = np.clip((0.10 + 0.90 * t * t) * B, 0.015, 1)

        # the reference's depth- and brightness-scaled line width (CSS px)
        # at scale 1. Plan 26 A2b (view.screen_strokes): in world space (the
        # default) LINE_VS scales it by the copy's scale — the camera's zoom
        # with it — so a stroke grows and shrinks with the shape as it did
        # before A2 and a zoomed-out field thins out naturally; in screen
        # space it keeps its weight whatever the shape's size in the world
        # (A2). The shape's strokes only: the hands are not drawn here —
        # A3's tubes are world-sized geometry (ghost.py WIRE_R / BONE_R) that
        # never follows camera.zoom, and A4's hand lines are 1 px edges drawn
        # by ghost.Geometry, not by this width, in both modes
        screen_strokes = getattr(s, "screen_strokes", False)
        # the shaders scale a stroke by its copy (field path, world space);
        # the legacy path scales it here, by the zoom, as before
        wsc = 0.0 if screen_strokes or legacy else 1.0
        sz = 1.0 if screen_strokes or not legacy else zoom
        wscale = clamp(0.75 + 0.35 * s.bright, 0.6, 1.35)
        width = ((0.35 + 0.85 * t) if heavy else (0.5 + 1.5 * t)) * wscale
        if st is not None:
            # a scene: each edge's density, weight and width are its own
            # layer's, not the whole compound's
            em = st["e_m"][order]
            edens = np.clip(340 / np.maximum(em, 1), 0.42, 1)
            alpha = np.clip((0.10 + 0.90 * t * t) * s.bright * edens, 0.015, 1)
            alpha = alpha * st["e_alpha"][order]
            width = np.where(em > 500, 0.35 + 0.85 * t, 0.5 + 1.5 * t) * wscale
            width = width * st["e_width"][order]
        # the edges' alpha: depth × brightness × density (floored above),
        # a sub-pixel width folded in, × the lines opacity (plan 24 C2) —
        # before the vertex fill, so the depth pass's skip test (`draws`)
        # sees the faded alpha. On the legacy path the zoom (`sz`) is in the
        # width and the fold is done here, as before; on the field path
        # LINE_VS folds per copy (this alpha an upper bound)
        if legacy:
            width = width * sz
            alpha = alpha * np.minimum(width, 1.0) * s.lines_alpha
            width = np.maximum(width, 1.0)
        else:
            alpha = alpha * s.lines_alpha

        # premultiplied ground: black at bg_alpha, so SRC_ALPHA/ONE_MINUS
        # blending leaves the framebuffer correctly composited for a
        # transparent window (colour = Σ c·a, alpha = 1 − Π(1 − a)). The
        # clear clears the depth too (to the far plane)
        bg_alpha = self._scene_ground()       # (plan 32 R: 0 over the backdrop)
        if clear:
            self.ctx.clear(*BG, bg_alpha)
        # cut-through: the plain blend also blends alpha (a² + (1 − a)·dst),
        # so a faint fill lowers the ground's alpha and a transparent window
        # shows the desktop through it. Off: alpha composites over the ground
        # (a + (1 − a)·dst), never below it — the lowest layer shows instead.
        # Only on a see-through ground (overlay mode): on an opaque one the
        # frame stays alpha 1 everywhere, so the desktop never shows through
        # the window (plan 14 WP1 — the Pepper's Ghost rig)
        # plan 39 T1 (alpha is honest): the see-through *window*'s ground
        # (`bg_alpha`), never a laid-over scene's zero one (`scene_ground`):
        # a scene in a composite's `over` (PR #240) or laid over the
        # backdrop (`backdrop.scene`, plan 32 R — the case that moved the
        # backdrop goldens). There the plain blend squared the alpha
        # against a colour of c·a, so what lay under showed too much
        if s.cut_through and float(getattr(self, "bg_alpha", 1.0)) < 1.0:
            blend = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        else:
            blend = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
                     moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ctx.blend_func = blend

        # ---- face fills, under the wireframe (agent-validated prototype) ----
        self._face_verts = 0
        self._copies = 0
        if s.faces:
            self._maybe_reload_patterns()
        if n_inst == 0:
            # no copies: the cleared ground is the scene. No vertex buffer is
            # written and nothing is bound here, so the caller's target and
            # the passes after this one are as on any other frame
            return
        # the copies: where each goes, how big, how bright — far to near,
        # those wholly off screen dropped (`_copies_of`)
        inst = self._copies_of(s, w, h, t_m, P, vp, dpr, legacy)
        if not len(inst):
            return                     # every copy is off screen: the ground alone
        self._ibuf.orphan(inst.nbytes)
        self._ibuf.write(inst.tobytes())
        copies = len(inst)
        self._copies = copies
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
                    if st is not None:
                        fa = fa * st["f_alpha"][to[:, 3]]
                    uv = face_uvs(s.shape).reshape(-1, 3, 2)[torder]
                    fverts = np.empty((len(tris) * 3, 8), dtype=np.float32)
                    for corner in range(3):
                        fverts[corner::3, 0:3] = P[to[:, corner]]
                        fverts[corner::3, 3] = w4[to[:, corner]]
                        fverts[corner::3, 4] = uv[:, corner, 0]
                        fverts[corner::3, 5] = uv[:, corner, 1]
                        fverts[corner::3, 6] = fa
                        fverts[corner::3, 7] = to[:, 3]
                    self._fbuf.orphan(fverts.nbytes)
                    self._fbuf.write(fverts.tobytes())
                    p = self._face_prog
                    self._camera_uniforms(p, mats, -1.0)
                    self._face_uniforms(p, s, t_m)
                    if getattr(self, "_face_plain", False):
                        # plan 36 T2: `shape.faces` unwired — plain faces, no
                        # pattern and no media layer (mode 0: FACE_PX's flat face)
                        p["u_mode"].value = 0
                        try:
                            p["u_bmp_on"].value = 0
                        except KeyError:
                            pass
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
                    self._fvao.render(moderngl.TRIANGLES, vertices=len(fverts), instances=copies)
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
                rgb = st["e_rgb"][order] if st is not None else (1.0, 1.0, 1.0)
                verts = np.empty((m * 6, 13), dtype=np.float32)
                for k in range(6):
                    verts[k::6, 0:3] = P[eo[:, 0]]
                    verts[k::6, 3:6] = P[eo[:, 1]]
                    verts[k::6, 6:8] = _EDGE_CORNERS[k]
                    verts[k::6, 8] = width
                    verts[k::6, 9] = alpha
                    verts[k::6, 10:13] = rgb
                self._lbuf.orphan(verts.nbytes)
                self._lbuf.write(verts.tobytes())
                self._camera_uniforms(self._lines, mats, -1.0)
                self._lines["u_size"].value = (float(w), float(h))
                self._lines["u_wscale"].value = wsc
                self._lvao.render(moderngl.TRIANGLES, vertices=len(verts), instances=copies)
                draws.append((self._lvao, len(verts), self._lines, float(alpha.max())))

            if s.points and not g.get("curve"):   # a curve (plan 28) has no corners to dot
                tp = (pd - near) / span
                order_p = np.argsort(pd, kind="stable")
                # radius in framebuffer px (× dpr) at scale 1; POINT_VS scales
                # it by the copy in world space (plan 26 A2b) and rounds the
                # diameter to whole pixels, as the point sprites the quads
                # replace were rasterised (the driver rounded gl_PointSize —
                # measured: with it the quads draw the sprites' frame byte for
                # byte, without it every dot grows)
                r = ((1.0 if heavy else 1.7) + 2.3 * tp * tp) * dpr
                if legacy:
                    # × the zoom in world space, rounded here as before: the
                    # shader's own rounding of a whole diameter is the identity
                    r = np.floor(2.0 * r * sz + 0.5) / 2.0
                # the points' alpha: depth × brightness, floored, × the points
                # opacity (plan 24 C2) after the floor — the one place it is derived
                PB = s.bright * clamp(dens * 1.5, 0.55, 1)
                pa = np.clip((0.32 + 0.68 * tp) * PB, 0.05, 1) * s.points_alpha
                prgb = RED
                if st is not None:
                    # a layer's weight scales its points' alpha and size; a
                    # tinted layer's points take its tint, the rest stay red
                    pa = pa * st["p_alpha"]
                    r = r * np.sqrt(st["p_alpha"])
                    prgb = np.where(st["p_tinted"][:, None], st["p_rgb"], RED)[order_p]
                n = g["n"]
                pverts = np.empty((n * 6, 10), dtype=np.float32)
                for k in range(6):
                    pverts[k::6, 0:3] = P[order_p]
                    pverts[k::6, 3:5] = _POINT_CORNERS[k]
                    pverts[k::6, 5] = r[order_p]
                    pverts[k::6, 6] = pa[order_p]
                    pverts[k::6, 7:10] = prgb
                self._pbuf.orphan(pverts.nbytes)
                self._pbuf.write(pverts.tobytes())
                self._camera_uniforms(self._points, mats, -1.0)
                vpx = self.ctx.viewport
                self._points["u_px"].value = (float(max(vpx[2], 1)), float(max(vpx[3], 1)))
                self._points["u_wscale"].value = wsc
                self._pvao.render(moderngl.TRIANGLES, vertices=len(pverts), instances=copies)
                draws.append((self._pvao, len(pverts), self._points, float(pa.max())))

            if has_depth:
                self._depth_pass(fbo, draws, mats, blend, copies)
        finally:
            if has_depth:
                self.ctx.disable(moderngl.DEPTH_TEST)
                fbo.depth_mask = True
                fbo.use()

    def _depth_pass(self, fbo: moderngl.Framebuffer, draws: list[tuple], mats: tuple,
                    blend: tuple, copies: int = 1) -> None:
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
                vao.render(moderngl.TRIANGLES, vertices=n, instances=copies)
        finally:
            for _, _, prog, _ in live:
                prog["u_depth_alpha"].value = -1.0
            ctx.blend_func = blend

    @staticmethod
    def _camera_uniforms(prog: moderngl.Program, mats: tuple, depth_alpha: float) -> None:
        """The one camera on a scene program: the eye and the world
        transform, and which pass (the colour pass: no depth threshold)."""
        prog["u_vp"].write(mats[0])
        prog["u_model"].write(mats[1])
        prog["u_depth_alpha"].value = depth_alpha

    def _field(self, s: ViewState, w: int, h: int, t: float) -> np.ndarray:
        """The copies this scene pass lays out: `field.field`'s rows
        (centre px, scale, alpha), far to near, none culled — the camera's
        pan handed over in px through the default eye (`CELL`). Its own
        method so a test can see what the pass was handed."""
        return field(_PanPx(s, SCALE * min(w, h)), w, h, t)

    def _legacy_field(self, s: ViewState, t: float) -> np.ndarray:
        """The copies of a flat layout with Fit off, as the field was laid out
        before the instanced draws — the same float arithmetic: (m, 4) rows
        of (x, y) in the world at scale 1 (a cell CELL shape radii, y up),
        scale 1, alpha 1, before the world transform; none culled. Its own
        method so a test can see what the pass was handed."""
        n = max(0, int(s.instances))
        if n == 0:
            return np.zeros((0, 4), dtype=np.float64)
        inst = np.zeros((max(n, 1), 4), dtype=np.float64)
        inst[:, 2:] = 1.0
        if n > 1:
            gx, gy = _field_mod.inst_positions(n, int(getattr(s, "inst_layout", 0)))
            gx, gy = gx.astype(np.float64), gy.astype(np.float64)
            spacing = max(float(getattr(s, "inst_spacing", 1.0)), 0.05)
            ox, oy = gx * CELL, gy * CELL
            if spacing != 1.0:
                ox, oy = ox * spacing, oy * spacing
            if s.inst_motion and s.inst_amp > 0.0:
                # trigonometric motion over the field: each instance's
                # phase comes from its position, so the field moves as
                # one figure (field._motion's flat formulas)
                ph = t * s.inst_rate
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
            inst[:, 0] = ox.astype(np.float32)
            inst[:, 1] = (-oy).astype(np.float32)
        return inst

    def _copies_of(self, s: ViewState, w: int, h: int, t: float, P: np.ndarray,
                   vp: np.ndarray, dpr: float, legacy: bool = False) -> np.ndarray:
        """The instance rows for the scene pass, (m, 4) float32: each copy's
        centre in the world (x, y on the plane through the origin, y up),
        its scale and its alpha. A copy wholly off screen through the eye
        is dropped (its bounding box's corners, projected).

        `legacy` (a flat layout, Fit off): the field as it was before the
        instanced draws, the same float arithmetic — a cell CELL shape
        radii, the motion's formulas — at scale 1 and alpha 1, before the
        world transform (the camera's zoom and pan, `model_matrix`).
        Otherwise `_field`'s px through the default eye (SCALE·min(w, h)
        px a unit), so the field keeps its world spacing whatever the eye;
        the camera is in the rows and the world transform is the identity."""
        if legacy:
            inst = self._legacy_field(s, t)
            if not len(inst):
                return np.zeros((0, 4), dtype=np.float32)
            # where the copies land in the world, for the cull alone
            zoom = max(float(s.zoom), 1e-3)
            seen = inst.copy()
            seen[:, 0] = inst[:, 0] * zoom + float(s.pan[0])
            seen[:, 1] = inst[:, 1] * zoom - float(s.pan[1])
            seen[:, 2] = zoom
        else:
            rows = self._field(s, w, h, t)
            if not len(rows):
                return np.zeros((0, 4), dtype=np.float32)
            ppu0 = SCALE * min(w, h)
            inst = np.empty((len(rows), 4), dtype=np.float64)
            inst[:, 0] = (rows[:, 0] - w / 2) / ppu0
            inst[:, 1] = -(rows[:, 1] - h / 2) / ppu0
            inst[:, 2:] = rows[:, 2:]
            seen = inst
        if len(P):
            # each copy's box (the shape's bounding box × its scale + its
            # centre) through the eye: a box in front of the eye projects
            # inside its corners' projections, so this reach is exact for
            # the box; a corner at or behind the eye keeps the copy. The pad
            # is a stroke's reach past its vertices (a dot's radius, half a
            # line), × the copy's scale in world-space strokes
            lo, hi = P.min(axis=0), P.max(axis=0)
            box = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                            for z in (lo[2], hi[2])])
            k = seen[:, 2]
            q = k[:, None, None] * box[None] + np.c_[seen[:, :2], np.zeros(len(seen))][:, None]
            c = q @ np.asarray(vp)[:3, :3].T + np.asarray(vp)[:, 3][:3]
            cw = q @ np.asarray(vp)[3, :3] + np.asarray(vp)[3, 3]
            front = (cw > EYE_NEAR).all(axis=1)
            cw = np.where(cw > EYE_NEAR, cw, 1.0)
            x = (c[..., 0] / cw + 1.0) * (w / 2)
            y = (1.0 - c[..., 1] / cw) * (h / 2)
            scale = 1.0 if getattr(s, "screen_strokes", False) else np.maximum(k, 1.0)
            pad = 6.0 * dpr * scale
            keep = ~front | ((x.max(axis=1) + pad >= 0) & (x.min(axis=1) - pad <= w)
                             & (y.max(axis=1) + pad >= 0) & (y.min(axis=1) - pad <= h))
            inst = inst[keep]
        return inst.astype(np.float32)


def _pub_name(p) -> str:
    return f"{getattr(p, 'kind', '?')} out {getattr(p, 'name', '?')}"


def _pub_failed(p, why: str, errors: dict) -> None:
    """`Renderer._publish`: publisher `p` failed for `why` — told
    (`fail`, when it has one: its status, said once) and recorded."""
    errors[_pub_name(p)] = why
    fail = getattr(p, "fail", None)
    if callable(fail):
        try:
            fail(why)
        except Exception:  # noqa: BLE001, S110 — telling it must not take the frame down
            pass


class _PanPx:
    """A view whose camera.pan is in px (field.py's unit) — the world pan ×
    `ppu` — and is otherwise the view itself."""

    def __init__(self, s, ppu: float):
        self._s = s
        self.pan = (float(s.pan[0]) * ppu, float(s.pan[1]) * ppu)

    def __getattr__(self, name):
        return getattr(self._s, name)


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
    t_now: float = 0.0, media=None, wiring: Wiring | None = None,
) -> np.ndarray:
    """Render one frame to an FBO; returns (h, w, 3) uint8. For tests/tools.
    Pattern time defaults to 0.0 so offscreen renders are deterministic.
    `media`: the channels the frame reads (`Renderer.media`), None for none;
    `wiring`: the graph's (`Renderer.wiring` — plan 33 R: a channel on the
    faces is the wire `media.<c> → pattern.media`), None today's frame —
    plan 36 T3: said here, as the tool's own wiring, by the one-way
    migration of a preset with no section (`graphmigrate.wired_wiring`),
    never by the renderer, whose own is the empty frame."""
    own = ctx is None
    if own:
        ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h))])
    fbo.use()
    ctx.viewport = (0, 0, w, h)
    r = Renderer(ctx)
    r.media = media
    if wiring is None:
        from .graphmigrate import wired_wiring
        wiring = wired_wiring(Wiring())
    r.wiring = wiring
    r.draw(s, w, h, t_now=t_now)
    data = np.frombuffer(fbo.read(components=3), dtype=np.uint8).reshape(h, w, 3)[::-1]
    fbo.release()
    if own:
        ctx.release()
    return data.copy()
