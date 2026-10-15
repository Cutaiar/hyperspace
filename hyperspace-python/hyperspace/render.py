"""moderngl renderer — port of the draw() pipeline of hyperspace.html.

The transform runs on the CPU through geometry.project_h(), the one
transform (geometry.project, the parity oracle, is it without the divisor);
the GPU only rasterises. The dataclass it draws, ViewState, lives in
view.py so nothing has to import moderngl to hold a view. At
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
bit-identical. The ghost hands (ghost.py) go over the finished frame in their
own pass and camera; off, the frame is untouched. Last of all the master
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
from .geometry import face_triangles, face_uvs, geom, project_h, view_angles, view_depth, w_masked
from .ghost import Ghost, GhostState
from .glsl import QUAD_VS, common, common_mtime, gl_error
from .lookback import DreamState, Lookback
from .outputs import HANDS, NAMES, PIPELINES, SCENE, Handoff, Switches, View, capped, fit, route
from .patterns import MODES, SPEED
from .tapers import clamp
from .view import N_MOD, RED, ViewState  # re-exported for callers that had them from here

PATTERNS_GLSL = Path(__file__).parent / "shaders" / "patterns.glsl"

BG = (0.0, 0.0, 0.0)

# the side, in texels, of the picture the faces' effects run over (plan 20
# fork F2): square, fixed, a constant and not a param — 512 cannot be told
# from it on a face and 2048 costs several times as much
FACE_PIC = 1024

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

FACE_VS = """
#version 330
in vec2 in_pos;      // pixel coordinates, logical space
in float in_wc;      // combined homogeneous divisor (perspective-correct uv)
in vec2 in_uv;       // face-local coordinates
in float in_alpha;
in float in_fid;     // face index within the shape
uniform vec2 u_size;
out vec2 v_uv;
out float v_alpha;
out float v_fid;
void main() {
    float nx = 2.0 * in_pos.x / u_size.x - 1.0;
    float ny = 1.0 - 2.0 * in_pos.y / u_size.y;
    gl_Position = vec4(nx * in_wc, ny * in_wc, 0.0, in_wc);
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
    if (a <= 0.0) discard;
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
in vec2 in_pos;
in float in_wc;
uniform vec2 u_size;
void main() {
    float nx = 2.0 * in_pos.x / u_size.x - 1.0;
    float ny = 1.0 - 2.0 * in_pos.y / u_size.y;
    gl_Position = vec4(nx * in_wc, ny * in_wc, 0.0, in_wc);
}
"""

COVER_FS = """
#version 330
out vec4 f_color;
void main() { f_color = vec4(1.0); }
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




# ---- instance layouts (plan 20 WP6): where each copy sits, in cells ----

LAYOUT_GRID, LAYOUT_HEX, LAYOUT_RING = 0, 1, 2     # params.INST_LAYOUT's order
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


class SceneTarget:
    """The texture the scene is drawn into: RGBA8 at the output's pixel
    size, through an MSAA renderbuffer that resolves into it when the
    output is multisampled. Recreated on resize, DPI change, or a target
    with a different sample count."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.size = (0, 0)
        self.samples = -1
        self.tex: moderngl.Texture | None = None
        self.fbo: moderngl.Framebuffer | None = None      # on the texture
        self._msaa: moderngl.Framebuffer | None = None    # on the renderbuffer, if any

    def ensure(self, size: tuple[int, int], samples: int) -> None:
        if size == self.size and samples == self.samples and self.tex is not None:
            return
        self.release()
        self.size, self.samples = size, samples
        self.tex = self.ctx.texture(size, 4)
        self.tex.repeat_x = self.tex.repeat_y = False
        self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])
        if samples > 0:
            rb = self.ctx.renderbuffer(size, 4, samples=samples)
            self._msaa = self.ctx.framebuffer(color_attachments=[rb])

    @property
    def draw_fbo(self) -> moderngl.Framebuffer:
        return self._msaa if self._msaa is not None else self.fbo

    def resolve(self) -> None:
        """After the scene pass: the multisampled draw into the texture."""
        if self._msaa is not None:
            self.ctx.copy_framebuffer(self.fbo, self._msaa)

    def release(self) -> None:
        for res in (self._msaa, self.fbo, self.tex):
            if res is not None:
                res.release()
        self._msaa = self.fbo = self.tex = None
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


# the passes `PassTimer` reports, in frame order (plan 26 A0): what the
# SYSTEM page lists, one line each. After A1 they become the graph's nodes
GPU_PASSES = ("scene", "cover", "hands", "lookback", "fx", "compose")


class PassTimer:
    """GPU time per pass of `Renderer._draw_frame` (plan 26 A0): a
    ``ctx.query(time=True)`` around each pass, read back `LAG` frames
    later so the CPU does not wait on the GPU for a result, and kept as a
    rolling median over the last `WINDOW` frames in ms (`medians`).

    A pass that runs more than once a frame (the look-back composite per
    pipeline and then the capture; the compose per output) is summed into
    its frame's total; a pass that did not run in a frame counts 0 that
    frame. Time queries never nest (GL allows one active per target), so
    the passes are timed side by side, never one inside another.

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
        self._frame: list[tuple[str, object]] = []          # this frame's (pass, query)
        self._pending: list[list[tuple[str, object]]] = []  # ended, not yet read
        self._ms: dict[str, list[float]] = {p: [] for p in GPU_PASSES}
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
        held = [q for _, q in self._frame] + [q for f in self._pending for _, q in f]
        self._frame, self._pending = [], []
        for q in held + self._free:
            try:
                q.release()
            except Exception:  # noqa: BLE001, S110 — a stand-in or a lost context: nothing to free
                pass
        self._free = []

    def time(self, name: str) -> _Timed:
        """``with timer.time("scene"):`` — the pass's GPU time, this frame."""
        if not self.on:
            return _Timed(None)
        try:
            q = self._free.pop() if self._free else self.ctx.query(time=True)
        except Exception as e:  # noqa: BLE001 — a driver that runs out: timing off
            self._off(e)
            return _Timed(None)
        self._frame.append((name, q))
        return _Timed(q, self)

    def end_frame(self) -> None:
        """Once a frame, after the last pass: this frame's queries wait;
        the frame `LAG` frames back is read into the medians."""
        if not self.on:
            return
        self._pending.append(self._frame)
        self._frame = []
        while len(self._pending) > self.LAG:
            done = self._pending.pop(0)
            totals = dict.fromkeys(GPU_PASSES, 0.0)
            try:
                for name, q in done:
                    # blocks if the result is still not there LAG frames on
                    # (moderngl has no availability query to ask first)
                    totals[name] = totals.get(name, 0.0) + q.elapsed / 1e6
                    self._free.append(q)
            except Exception as e:  # noqa: BLE001 — a read that fails: timing off
                self._off(e)
                return
            for name, ms in totals.items():
                window = self._ms.setdefault(name, [])
                window.append(ms)
                del window[:-self.WINDOW]

    def medians(self) -> dict[str, float]:
        """Pass → median ms over the window, in `GPU_PASSES` order; empty
        until the first frame has been read back, and with no timer."""
        return {name: float(np.median(w)) for name, w in self._ms.items() if w}


class _Timed:
    """One pass's query as a context manager; nothing with no query. A
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
        self.stats: dict = {"pipelines": [], "chain_runs": 0, "direct": True}
        # plan 26 A0: GPU time per pass, `stats["gpu_ms"]` (the SYSTEM page)
        self.timer = PassTimer(ctx)
        self.cover = CoverTarget(ctx)
        self._face_verts = 0           # face vertices in _fbuf from the last scene pass
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
            lvao = ctx.vertex_array(lines, [(self._lbuf, "2f 1f", "in_pos", "in_alpha")])
            made.append(lvao)
            # the coverage pass reads the face buffer's position and divisor only
            cover_prog = ctx.program(vertex_shader=COVER_VS, fragment_shader=COVER_FS)
            made.append(cover_prog)
            cvao = ctx.vertex_array(cover_prog, [(self._fbuf, "2f 1f 16x", "in_pos", "in_wc")])
            made.append(cvao)
            pvao = ctx.vertex_array(points,
                                    [(self._pbuf, "2f 1f 1f", "in_pos", "in_size", "in_alpha")])
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
        for res in (getattr(self, "_show_vao", None), getattr(self, "_show_prog", None)):
            if res is not None:
                res.release()
        self._show_prog = self._show_vao = None
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
                [(self._fbuf, "2f 1f 2f 1f 1f", "in_pos", "in_wc", "in_uv", "in_alpha", "in_fid")],
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
        """The GPU pass timer (getattr: a renderer from before a hot reload
        has none, and gets one)."""
        timer = getattr(self, "timer", None)
        if timer is None:
            timer = self.timer = PassTimer(self.ctx)
        return timer

    def _timed(self, name: str) -> _Timed:
        """``with self._timed("fx"):`` — the pass's GPU time (plan 26 A0)."""
        return self._pass_timer().time(name)

    def _draw_frame(self, s: ViewState, w: int, h: int, dpr: float, t: float,
                    views: list[View]) -> None:
        """draw_outputs()'s body, timed per pass on the GPU (`PassTimer`):
        `stats["gpu_ms"]` is each pass's rolling median in ms and
        `stats["gpu_note"]` why there is none, whatever the frame did."""
        timer = self._pass_timer()
        try:
            self._frame_passes(s, w, h, dpr, t, views)
        finally:
            timer.end_frame()
            self.stats["gpu_ms"] = timer.medians()
            self.stats["gpu_note"] = timer.note

    def _frame_passes(self, s: ViewState, w: int, h: int, dpr: float, t: float,
                      views: list[View]) -> None:
        """The frame's passes: the face picture (only while an effect is
        aimed at the faces), scene, cover, pull, the hands' layer, each
        pipeline once (composite, capture, effects), then each view's
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
        self.scene.ensure(size, _samples_of(ctx, target))
        for unit in range(4):
            self._blank.use(location=unit)
        # the faces' effects first, into their own picture: finished before
        # the scene pass begins and not bound again this frame. The scene
        # pass below shows it, so everything after — the echoes, the dream,
        # the frame's effects — sees the faces' effects as part of the scene
        clock = self._timed
        with clock("scene"):         # the face picture, the scene, the resolve
            self._pic = self._face_picture(s, t)
            try:
                self.scene.draw_fbo.use()
                ctx.viewport = (0, 0, *size)
                self.draw_scene(s, w, h, dpr, t)
            finally:
                self._pic = None         # handed to that one scene pass only
            self.scene.resolve()
        lb = self.lookback
        cover = None
        if lb.wants_cover():
            with clock("cover"):
                cover = self._draw_cover(w, h)
        target.viewport = vp
        lb.tick(t)                       # echo time is seconds (plan 14 WP6)
        lb.pull()
        fx = self.fx
        fx.tick()
        # an opaque ground keeps the whole chain at alpha 1 (plan 14 WP1)
        fx.opaque = getattr(self, "bg_alpha", 1.0) >= 1.0
        fx_on = fx.active()
        stats = {"pipelines": [], "chain_runs": 0, "direct": True, "captures": 0,
                 "layer": False}
        self.stats = stats
        # the hands' layer, once, before any pipeline that might want it —
        # only while some view shows hands. A pass that raises (a malformed
        # skeleton, a font, a driver) is caught, as the faces' is: the frame
        # goes on without the hands, `Ghost.error` says why (the first
        # reason, kept), the target is bound again and the dim still runs —
        # a rig at black must never flash full because of the hands
        # With an effect on and some view's hands going through it, the
        # guide and the tethers' labels are drawn into a layer of their own
        # (`Ghost.readout`, fork F3) and laid over after everything, so the
        # effects never bend them; otherwise they are in the hands' layer
        hands = False
        if any(v.switches.hands for v in views):
            through = fx_on and any(v.switches.hands and v.switches.through for v in views)
            try:
                with self._timed("hands"):
                    hands = bool(self.ghost.layer(size, t, readout=through))
            except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
                self._hands_failed(e, target, vp)
        readout = self.ghost.readout if hands else None
        stats["layer"], stats["readout"] = hands, readout is not None
        routes = [route(v.switches, fx_on, hands) for v in views]
        # each distinct pipeline once, in key order. The history is
        # captured after the first composite of the scene, from the scene
        # texture: it never holds the hands, the effects or the dim
        users: dict[int, list[int]] = {}
        for i, (key, _) in enumerate(routes):
            if key is not None:
                users.setdefault(key, []).append(i)
        frames: dict[int, moderngl.Texture | None] = {}   # key → its texture; None: drawn direct
        failed: set[int] = set()
        for key in PIPELINES:
            if key not in users:
                continue
            only = views[users[key][0]]
            # a flipped output (plan 23 WP1) takes the frame through a
            # texture: the mirror is `_show`'s, at the output stage
            direct = (len(users[key]) == 1 and only.target is not None
                      and tuple(only.rect[2:]) == size
                      and not getattr(only.switches, "flip_x", False)
                      and not getattr(only.switches, "flip_y", False))
            stats["pipelines"].append(key)
            try:
                if direct:
                    dst, tex = only.target, None
                    dst.viewport = only.rect
                else:
                    tex, dst = self._frame_target(key, size)
                    stats["direct"] = False
                self._pipeline(key, dst, cover, t, fx_on, stats, (target, vp))
                frames[key] = tex
            except Exception as e:  # noqa: BLE001 — one pipeline must not take the others down
                failed.add(key)
                for i in users[key]:
                    self._view_failed(views[i], f"{NAMES[key]}", e)
                self._rebind(target, vp)
        # the history, exactly once, from the scene texture, after every
        # pipeline has composited it: a capture changes the echoes' weights,
        # ages and tint, so one before a second pipeline's composite would
        # give two outputs different echoes in one frame. With no view
        # showing the scene it runs all the same — the history and the
        # dream go on, so switching the scene back on shows no gap
        stats["captures"] = 1
        with self._timed("lookback"):
            lb.capture(self.scene.tex, self.scene.fbo)
        if fx_on and not stats["chain_runs"]:
            fx.state.advance_to(t)       # …and so do the effects' clocks
        for i, v in enumerate(views):
            key, after = routes[i]
            # the readout goes on every output that shows the hands, over
            # or through: in its own layer the guide is in neither
            ro = readout if v.switches.hands else None
            try:
                with self._timed("compose"):
                    self._compose(v, key, after, frames, failed, size, ro)
            except Exception as e:  # noqa: BLE001 — one view must not take the others down
                self._view_failed(v, "output", e)
                self._rebind(target, vp)

    def _pipeline(self, key: int, dst: moderngl.Framebuffer, cover, t: float, fx_on: bool,
                  stats: dict, restore: tuple) -> None:
        """One pipeline into `dst` (its viewport). SCENE: the look-back
        composite and, with an effect on, the chain after it. SCENE_HANDS
        (WP2): the composite, the hands over it, then the chain — the
        effects bend the hands with the shape. HANDS: the ground, the hands,
        the chain; no look-back (the echoes are the scene's, and the scene
        is off). Both only ever with an effect on (`outputs.route`)."""
        lb, fx, ctx = self.lookback, self.fx, self.ctx
        clock = self._timed
        if not fx_on:
            with clock("lookback"):
                lb.composite(self.scene.tex, dst, cover)
            return
        # the post pass into the chain's first texture; the chain ends on
        # `dst`. The history is captured after every pipeline's composite
        # (`_draw_frame`), from the scene texture: never the hands or effects
        size = self.scene.size
        buf = fx.begin(size)
        if key == HANDS:
            buf.use()
            ctx.viewport = (0, 0, *size)
            ctx.clear(0.0, 0.0, 0.0, getattr(self, "bg_alpha", 1.0))
        else:
            with clock("lookback"):
                lb.composite(self.scene.tex, buf, cover)
        if key != SCENE:
            # the hands onto the chain's input (fork F1: after the look-back
            # composite, before the first effect). Failing, the chain still
            # runs on the scene alone and `Ghost.error` says why
            try:
                with clock("hands"):
                    self.ghost.composite(buf, (0, 0, *size), opaque=fx.opaque)
            except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
                self._hands_failed(e, *restore)
        with clock("fx"):
            fx.run(dst, t)
        stats["chain_runs"] += 1

    def _compose(self, v: View, key: int | None, after: bool,
                 frames: dict[int, moderngl.Texture | None], failed: set[int],
                 size: tuple[int, int], readout: moderngl.Texture | None = None) -> None:
        """One view's picture: the pipeline's frame (already there when it
        was drawn direct), the hands over it in the same rect, the readout
        layer over that when there is one, its dim."""
        ctx, gh = self.ctx, self.ghost
        factor = clamp(getattr(self, "dim", 1.0) * float(v.switches.dim), 0.0, 1.0)
        # plan 23 WP1: this output's mirror, its last step — the frame, the
        # hands laid after and the readout, never the hands-through pass
        # (`_pipeline`'s composite, inside the frame this flips whole)
        flip = (bool(getattr(v.switches, "flip_x", False)),
                bool(getattr(v.switches, "flip_y", False)))
        frame = None if key is None or key in failed else frames.get(key)
        if v.target is None:
            if v.presenter is None:
                raise RuntimeError("a view needs a target or a presenter")
            rx, ry, rw, rh = v.rect
            ix, iy, iw, ih = fit(size, (rw, rh))
            v.handoff = Handoff(frame, size, (rx + ix, ry + iy, iw, ih),
                                hands=gh.tex if after else None, readout=readout,
                                alpha=float(gh.state.alpha), factor=factor,
                                bg_alpha=float(v.bg_alpha), flip=flip)
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
                if after:
                    gh.composite(tgt, inner, opaque=opaque, flip=flip)
                if readout is not None:      # the guide and its labels, never bent
                    gh.composite_readout(tgt, inner, opaque=opaque, flip=flip)
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

    def _frame_target(self, key: int, size: tuple[int, int]
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

    def _hands_failed(self, e: Exception, target: moderngl.Framebuffer, vp: tuple) -> None:
        """The hands raised: say why (the first reason, kept) and put back
        the state the frame's other passes expect."""
        if not self.ghost.error:
            self.ghost.error = f"ghost hands: {type(e).__name__}: {e}"[:160]
        self._rebind(target, vp)

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
            self._cover_prog["u_size"].value = (float(w), float(h))
            self._cvao.render(moderngl.TRIANGLES, vertices=self._face_verts)
            ctx.enable(moderngl.BLEND)
        return self.cover.tex

    def draw_scene(
        self, s: ViewState, w: int, h: int, dpr: float = 1.0,
        t_now: float | None = None,
    ) -> None:
        """The scene pass alone, into whatever is bound: clear, faces, edges,
        points. The pattern uniforms come from `s.pattern_mod`; `t_now` pins
        pattern time for deterministic renders. With `s.instances` at 0 it
        clears to the ground and draws nothing; the passes after it (cover,
        look-back, effects, ghost hands, dim) run as on any frame. Called on
        its own it shows no face picture, as it shows no frame effect: the
        faces' effects are `draw`'s (`_draw_frame` hands the picture over
        for the one scene pass it wraps)."""
        g = geom(s.shape)
        # a shape whose W planes are masked is drawn at its own angles
        # (geometry.view_angles); every other shape at the view's
        ang = view_angles(s.shape, s.ang)
        px, py, pd, wc = project_h(g["V"], ang, s.yaw, s.pitch, d4=s.depth4, w=w, h=h)
        if w_masked(s.shape):
            # its w is 0 at every angle, so the depth cue (pd: fade, width,
            # draw order) would sit flat at its dimmest; it cues on its
            # depth toward the 3D camera (yaw and pitch included, so a
            # camera turned round never puts the far side on top), as a 4D
            # shape cues on its depth toward the 4D eye
            pd = view_depth(g["V"], ang, s.yaw, s.pitch, d4=s.depth4)

        # camera: zoom about the view centre, then pan (both in logical px)
        zoom = max(s.zoom, 1e-3)
        px = (px - w / 2) * zoom + w / 2 + s.pan[0]
        py = (py - h / 2) * zoom + h / 2 + s.pan[1]

        # synchronized instances in a layout (grid, honeycomb or ring:
        # inst_positions), spaced pre-zoom so the camera sees a field
        n_inst = max(0, int(s.instances))   # 0: the ground alone (returns below)
        t_m = self.now(t_now)
        if n_inst > 1:
            cell = min(w, h) * 0.72 * zoom
            gx, gy = inst_positions(n_inst, int(s.inst_layout))
            offs = np.stack([gx * cell, gy * cell], axis=1).astype(np.float32)
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
                offs[:, 0] += s.inst_amp * cell * dx
                offs[:, 1] += s.inst_amp * cell * dy
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

        # premultiplied ground: black at bg_alpha, so SRC_ALPHA/ONE_MINUS
        # blending leaves the framebuffer correctly composited for a
        # transparent window (colour = Σ c·a, alpha = 1 − Π(1 − a))
        bg_alpha = getattr(self, "bg_alpha", 1.0)
        self.ctx.clear(*BG, bg_alpha)
        # cut-through: the plain blend also blends alpha (a² + (1 − a)·dst),
        # so a faint fill lowers the ground's alpha and a transparent window
        # shows the desktop through it. Off: alpha composites over the ground
        # (a + (1 − a)·dst), never below it — the lowest layer shows instead.
        # Only on a see-through ground (overlay mode): on an opaque one the
        # frame stays alpha 1 everywhere, so the desktop never shows through
        # the window (plan 14 WP1 — the Pepper's Ghost rig)
        if s.cut_through and bg_alpha < 1.0:
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        else:
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
                                   moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        self._lines["u_size"].value = (float(w), float(h))

        # ---- face fills, under the wireframe (agent-validated prototype) ----
        self._face_verts = 0
        if s.faces:
            self._maybe_reload_patterns()
        if n_inst == 0:
            # no copies: the cleared ground is the scene. No vertex buffer is
            # written and nothing is bound here, so the caller's target and
            # the passes after this one are as on any other frame
            return
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
                fverts = np.empty((len(tris) * 3, 7), dtype=np.float32)
                for corner in range(3):
                    fverts[corner::3, 0] = px[to[:, corner]]
                    fverts[corner::3, 1] = py[to[:, corner]]
                    fverts[corner::3, 2] = wc[to[:, corner]]
                    fverts[corner::3, 3] = uv[:, corner, 0]
                    fverts[corner::3, 4] = uv[:, corner, 1]
                    fverts[corner::3, 5] = fa
                    fverts[corner::3, 6] = to[:, 3]
                fverts = self._tile(fverts, offs)
                self._fbuf.orphan(fverts.nbytes)
                self._fbuf.write(fverts.tobytes())
                p = self._face_prog
                p["u_size"].value = (float(w), float(h))
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

        if s.lines:
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
