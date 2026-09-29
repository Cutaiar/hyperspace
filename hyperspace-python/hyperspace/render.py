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
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import moderngl
import numpy as np

from .fx import FxChain, FxState
from .geometry import face_triangles, face_uvs, geom, project_h
from .glsl import common, common_mtime, gl_error
from .lookback import DreamState, Lookback
from .tapers import clamp
from .view import N_MOD, RED, ViewState  # re-exported for callers that had them from here

PATTERNS_GLSL = Path(__file__).parent / "shaders" / "patterns.glsl"

BG = (0.0, 0.0, 0.0)

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

FACE_FS_HEAD = f"""
#version 330
in vec2 v_uv;
in float v_alpha;
in float v_fid;
out vec4 f_color;
uniform float u_time;
uniform float u_mod[{N_MOD}];  // pattern.mod.* — the routed pattern inputs
uniform int u_mode;
uniform float u_mix;
uniform sampler2D u_bitmap;
uniform int u_bmp_on;
uniform float u_bmp_alpha;
uniform vec2 u_bmp_pos;      // path offset about the face centre, UV units
uniform vec2 u_bmp_scale;    // (w, h) in face-UV units, aspect preserved
"""

FACE_FS_TAIL = """
void main() {
    vec3 rgb = vec3(1.0);
    float shade = 1.0;
    if (u_mode != 0) {
        vec4 v = pattern(u_mode, v_uv, v_fid);
        v = clamp(v, 0.0, 1.0);
        shade = mix(1.0, 2.8 * v.a, u_mix);
        rgb = mix(vec3(1.0), v.rgb, u_mix);
    }
    if (u_bmp_on != 0) {
        vec2 q = (v_uv - 0.5 - u_bmp_pos) / u_bmp_scale + 0.5;
        if (q.x >= 0.0 && q.x <= 1.0 && q.y >= 0.0 && q.y <= 1.0) {
            vec4 b = texture(u_bitmap, vec2(q.x, 1.0 - q.y));
            float ba = b.a * u_bmp_alpha;
            rgb = mix(rgb, b.rgb, ba);
            shade = mix(shade, 2.8, ba);
        }
    }
    float a = v_alpha * shade;
    if (a <= 0.0) discard;
    f_color = vec4(rgb, a);
}
"""

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


class Renderer:
    def __init__(self, ctx: moderngl.Context, dream: DreamState | None = None,
                 fx: FxState | None = None):
        self.ctx = ctx
        # clear alpha: 1 is the opaque black ground; overlay mode lowers it
        # so whatever is behind the window shows through (overlay.py)
        self.bg_alpha = 1.0
        # the scene texture and the look-back post pass over it; the blank
        # texture takes the sampler units before the scene pass, so the
        # scene texture is never bound while it is the render target
        self.scene = SceneTarget(ctx)
        self.lookback = Lookback(ctx, dream)
        self.fx = FxChain(ctx, fx)      # the effect stack after the post pass
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
        self._patterns_mtime = (0.0, 0.0)   # (patterns.glsl, _common.glsl)
        self._reload_check = 0
        self._t0 = time.perf_counter()   # the one wall clock: patterns, instances, effects
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
        try:
            src = PATTERNS_GLSL.read_text()
            self._patterns_mtime = self._shader_mtime()
            # the shared helpers first (source string 1), then the file
            # (string 2): an error names the file and its own line
            prog = self.ctx.program(
                vertex_shader=FACE_VS,
                fragment_shader=(FACE_FS_HEAD + "#line 1 1\n" + common() + "\n#line 1 2\n"
                                 + src + FACE_FS_TAIL),
            )
        except Exception as e:  # noqa: BLE001 — a bad edit must not kill the app
            self.pattern_error = gl_error(e, {1: "_common.glsl:", 2: "patterns.glsl:"})
            return
        if self._face_prog is not None:
            self._face_prog.release()
        if self._fvao is not None:
            self._fvao.release()
        self._face_prog = prog
        self._fvao = self.ctx.vertex_array(
            prog,
            [(self._fbuf, "2f 1f 2f 1f 1f", "in_pos", "in_wc", "in_uv", "in_alpha", "in_fid")],
        )
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
        t = self.now(t_now)
        target = ctx.fbo
        if target is None:
            raise RuntimeError("Renderer.draw: no framebuffer bound (call fbo.use())")
        vx, vy, vw, vh = target.viewport
        try:
            self._draw_frame(s, w, h, dpr, t, target, (vx, vy, vw, vh))
        finally:
            target.use()
            ctx.viewport = (vx, vy, vw, vh)
            ctx.enable(moderngl.BLEND)

    def _draw_frame(self, s: ViewState, w: int, h: int, dpr: float, t: float,
                    target: moderngl.Framebuffer, vp: tuple[int, int, int, int]) -> None:
        """draw()'s body: scene, cover, pull, composite, capture, effects."""
        ctx = self.ctx
        vx, vy, vw, vh = vp
        self.scene.ensure((max(vw, 1), max(vh, 1)), _samples_of(ctx, target))
        for unit in range(4):
            self._blank.use(location=unit)
        self.scene.draw_fbo.use()
        ctx.viewport = (0, 0, max(vw, 1), max(vh, 1))
        self.draw_scene(s, w, h, dpr, t)
        self.scene.resolve()
        lb = self.lookback
        cover = self._draw_cover(w, h) if lb.wants_cover() else None
        target.viewport = (vx, vy, vw, vh)
        lb.pull()
        fx = self.fx
        fx.tick()
        # an opaque ground keeps the whole chain at alpha 1 (plan 14 WP1)
        fx.opaque = getattr(self, "bg_alpha", 1.0) >= 1.0
        if fx.active():
            # the post pass into the chain's first texture; the chain ends
            # on the window. The history captures the scene, not the effects.
            buf = fx.begin(self.scene.size)
            lb.composite(self.scene.tex, buf, cover)
            lb.capture(self.scene.tex, buf)
            fx.run(target, t)
        else:
            lb.composite(self.scene.tex, target, cover)
            lb.capture(self.scene.tex, target)

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
        pattern time for deterministic renders."""
        g = geom(s.shape)
        px, py, pd, wc = project_h(g["V"], s.ang, s.yaw, s.pitch, d4=s.depth4, w=w, h=h)

        # camera: zoom about the view centre, then pan (both in logical px)
        zoom = max(s.zoom, 1e-3)
        px = (px - w / 2) * zoom + w / 2 + s.pan[0]
        py = (py - h / 2) * zoom + h / 2 + s.pan[1]

        # synchronized instance grid, spaced pre-zoom so the camera sees a field
        n_inst = max(1, int(s.instances))
        t_m = self.now(t_now)
        if n_inst > 1:
            cols = math.ceil(math.sqrt(n_inst))
            rows = math.ceil(n_inst / cols)
            cell = min(w, h) * 0.72 * zoom
            k = np.arange(n_inst, dtype=np.float32)
            gx = k % cols - (cols - 1) / 2      # grid position about the centre
            gy = k // cols - (rows - 1) / 2
            offs = np.stack([gx * cell, gy * cell], axis=1).astype(np.float32)
            if s.inst_motion and s.inst_amp > 0.0:
                # trigonometric motion over the grid: each instance's phase
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
                p["u_time"].value = t_m
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
                    ph = t_m * s.bmp_rate
                    if s.bmp_mode == 1:      # orbit
                        ox, oy = math.cos(ph), math.sin(ph)
                    elif s.bmp_mode == 2:    # figure-8
                        ox, oy = math.sin(ph), math.sin(2.0 * ph) * 0.5
                    elif s.bmp_mode == 3:    # sway
                        ox, oy = math.sin(ph), 0.0
                    else:                    # still
                        ox = oy = 0.0
                    p["u_bmp_pos"].value = (s.bmp_amp * ox, s.bmp_amp * oy)
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
