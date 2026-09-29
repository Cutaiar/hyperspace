"""Look-back — the frame history and the age-weighted composite (plan 07, WP6a).

The renderer draws the scene into a texture (render.py, SceneTarget) and
hands it here twice a frame: once to *composite* it onto the window over
the history, once to *capture* it into the history. The history is a ring
of downsampled frames — the echoes — plus one more buffer, the dream ``D``,
that a worker (WP6b, dream.py) fills asynchronously through the
LookbackSource slot below. With no worker the echoes alone are the
plain tracer; with one, ``D`` is the dreamed wake and the echoes a raw
trail under it.

The composite, per pixel (the spike's ``composite()`` in
tools/dream_bench/common.py, made per-layer):

    grade(c)  = pow(c, contrast) · (1 − darken)         a power curve keeps
                                                        black black; above 1
                                                        only the bright,
                                                        high-contrast regions
                                                        of a layer read
    chroma(c) = mix(own, lum(c) · tint_rgb, tint)       the dream buffer only:
                own = mix(lum(c), rotate(c, hue), sat)  its colours re-hued and
                                                        (de)saturated about the
                                                        grey axis, then crossed
                                                        into a tint of its
                                                        luminance — a chosen
                                                        colour, or the scene's
                                                        own mean hue
    layer i   = colour grade(L_i.rgb) at weight w_i,
                w_i = echo_mix · decay^age_i   (echoes, age in frames)
                w_D = mix, on grade(chroma(D))  (the dream buffer)
    wake      = layers over one another, oldest → newest, premultiplied:
                wake ← wake·(1 − a_i) + grade(L_i)·w_i,
                a_i = w_i · max(grade(L_i))     the layer's own luminance is
                                                its coverage — a black pixel
                                                covers nothing
    wake     ×= 1 − occlude · max(min(4 · max(scene.rgb), 1), faces)
                                                the render over the wake: where
                                                this frame drew a face (its
                                                coverage mask, render.py — the
                                                fills are a few percent alpha,
                                                so their light would barely
                                                cover) or anything bright, the
                                                wake beneath is held back
                                                (occlude 0 is the old additive
                                                glow over it)
    out.rgb   = min(scene.rgb + wake, 1)        additive under the scene, so
                                                the wireframe stays white-hot
    out.a     = scene.a ∪ wake.a                (a + b − a·b)

Alpha is what makes overlay mode work (overlay.py clears the ground to
see-through): the scene texture is premultiplied — colour Σ c·a over a
black ground at ``bg_alpha`` — and so are the echoes cut from it, so a
layer's colour never exceeds its coverage and the wake tints the desktop
only where content is or was. With an opaque ground ``scene.a`` is 1 and
the union is 1: exactly today's frame plus the wake. With the pipeline off
the post pass is a copy and the output is bit-identical to drawing the
scene straight to the window (tests/test_render.py asserts it).

The chroma stage is what makes the dream sit with the scene. The net's
gradient paints in its own primaries — red, green and blue activation
blobs whatever the frame's palette — so ``D`` is re-coloured here, on
the way in, every frame: a hue rotation and a saturation scale on its
own colours (sat 0 is greyscale), then a ``tint`` cross-fade to its
luminance times one colour. That colour is either ``tint_hue`` /
``tint_sat`` or, with ``tint_from`` on "scene", the hue of the scene's
mean colour at ``tint_sat`` — a scene with no chroma tints grey. The
mean is taken on the host from the newest echo at capture: with a
worker attached those pixels are read back for it anyway (the copy path
below), and without one scene mode does that read itself, one sync
point a frame. It is a frame stale by construction, which no eye sees.
The echoes are cut from the scene and already match it, so they pass
untouched. Chroma runs before the grade, so darken and contrast read
the same on every layer.

The history lives in one atlas texture, MAX_ECHOES slots of the echo size
stacked vertically, so a slot is an FBO viewport (no per-layer copies, no
array-texture attachment moderngl cannot make) and the composite samples
one texture in a loop. Echo size is ``dream.res`` on the short side, the
render's aspect kept, rounded to 8 px; 32 slots at 400×256 are 12.5 MiB.

The dream slot (WP6b builds against this; the copy path is the spike's
recommendation, ~1 ms round trip at 256 px):

    LookbackSource.submit(frame, frame_index)   after every capture, the
        newest echo as a (h, w, 4) uint8 array, rows bottom-up as GL reads
        them. The array is the source's own if it has ``buffer(shape)`` (a
        torch host alias: glReadPixels lands straight in the tensor's
        memory), else a numpy array this module keeps.
    LookbackSource.latest() → (pixels, frame_index) | None   the newest
        finished result, same layout, RGB premultiplied by the content
        mask (the compositor derives alpha from luminance, so where the
        mask is 0 the desktop stays clear); the frame index says which
        submit it answers, and a result already shown is skipped.
    Lookback.read_into(array) / write_from(array)   the two GL legs
        themselves, for a worker that drives them itself.

Ordering rule: the read waits for the render (glReadPixels is a sync
point, ~0.4 ms); the write is a plain texture upload before the
composite. A result lands a frame or two after its submit by design.
"""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import moderngl
import numpy as np

from .glsl import FALLBACK, QUAD_VS, common, gl_error

MAX_ECHOES = 32
RES = [128, 192, 256, 384]              # dream.res: the echo's short side, px
LAYERS = ["conv2_2", "conv3_3", "conv4_3", "inception3b", "inception4c", "inception4e"]
OCTAVES = ["1", "2 alt", "3 alt"]       # one octave a frame, in rotation (spike D)
TINT_FROM = ["colour", "scene"]         # dream.tint_from: the tint's hue source
OCCLUDE_GAIN = 4.0                      # scene brightness × this = its coverage of the wake


@dataclass
class DreamState:
    """The dream.* params' object (params.py binds to these fields).

    Defaults started as the spike's recommendation (docs/plans/assets/
    06-lookback-perf.md: conv3_3 at 256, two steps of 0.03, k 0.08, mask
    decay 0.97) and were pushed for a wake that lasts and reads at a
    glance while tuning (2026-09-25): k 0.05 and mask decay 0.99, so the
    dream holds ~20 frames and its region lingers ~100 after content
    leaves; ``D`` at 70 % darkened only to 90 %; eight echoes, two frames
    apart, fading 0.95 a frame. The render covers the wake where it drew
    (occlude 1). Colours as the net painted them (tint 0).
    """

    on: bool = False
    # the composite
    mix: float = 0.7          # the dream buffer's opacity
    echo_mix: float = 0.4     # the echoes' opacity (times decay^age)
    decay: float = 0.95       # per-frame age fade of an echo
    darken: float = 0.1       # 0 as bright as the frame … 1 black
    contrast: float = 1.0     # power curve on every layer; 1 is neutral
    occlude: float = 1.0      # 0 the wake adds over the render … 1 the render covers it
    # the dream buffer's chroma, before the grade
    hue: float = 0.0          # degrees of hue rotation on the net's own colours
    sat: float = 1.0          # their saturation; 0 is greyscale, 1 as the net painted
    tint: float = 0.0         # 0 those colours … 1 luminance × the tint colour
    tint_from: int = 0        # index into TINT_FROM: a chosen colour, or the scene's hue
    tint_hue: float = 200.0   # the tint colour's hue, degrees
    tint_sat: float = 1.0     # …and saturation; 0 tints grey
    echoes: int = 8           # ring depth; 0 = only the dream buffer
    every: int = 2            # capture cadence, frames
    res: int = 2              # index into RES → 256
    # the dream worker's (WP6b) — declared here so presets carry them
    steps: int = 2
    step: float = 0.03
    k: float = 0.05           # step × steps / k = 1.2, under dream.py's 1.5 guard
    layer: int = 1            # index into LAYERS → conv3_3
    octaves: int = 0          # index into OCTAVES
    mask_decay: float = 0.99
    jitter: int = 8


@runtime_checkable
class LookbackSource(Protocol):
    """The dream slot — see the module docstring for the contract."""

    def submit(self, frame: np.ndarray, frame_index: int) -> None: ...

    def latest(self) -> tuple[np.ndarray, int] | None: ...


# ---- GL: one fullscreen triangle (glsl.QUAD_VS), two fragment programs ----

DOWN_FS = """
#version 330
uniform sampler2D u_scene;   // mipmapped: trilinear is a proper box-ish downsample
in vec2 v_uv;
out vec4 f_color;
void main() { f_color = texture(u_scene, v_uv); }
"""

# the post pass's fragment shader body — source string 2; string 1 is
# shaders/_common.glsl (hue_rotate, LUMA), prepended by post_fs()
POST_FS = f"""
#line 1 2
uniform sampler2D u_scene;   // this frame, fetched exactly: off = a copy
uniform sampler2D u_ring;    // the history atlas, MAX_ECHOES slots stacked in v
uniform sampler2D u_dream;   // the dream buffer D
uniform sampler2D u_cover;   // the faces' coverage mask at the scene's size (render.py)
uniform int u_has_cover;     // 0 = no mask this frame: brightness alone covers
uniform ivec2 u_origin;      // the target viewport's origin (gl_FragCoord is window-relative)
uniform int u_n;             // echoes this frame, oldest first
uniform float u_w[MAX_ECHOES];    // echo weight: echo_mix · decay^age
uniform float u_off[MAX_ECHOES];  // the echo's slot origin in atlas v
uniform float u_slot;        // one slot's height in atlas v
uniform float u_pad;         // half a texel in v: a slot never bleeds into its neighbour
uniform float u_dream_w;     // the dream buffer's weight; 0 = none
uniform float u_darken;
uniform float u_contrast;
uniform float u_occlude;     // 0 the wake adds over the render … 1 the render covers it
uniform float u_hue;        // the dream's hue rotation, radians
uniform float u_sat;         // …and saturation scale about the grey axis
uniform float u_tint;        // 0 the dream's own colours … 1 luminance × the tint
uniform vec3 u_tint_rgb;     // the tint colour: chosen, or the scene's hue (Lookback.tint_rgb)
in vec2 v_uv;
out vec4 f_color;

const float OCCLUDE_GAIN = {OCCLUDE_GAIN};

vec3 grade(vec3 c) {{
    return pow(max(c, vec3(1e-6)), vec3(u_contrast)) * (1.0 - u_darken);
}}

// the dream's colours, re-hued and (de)saturated, crossed into a tint of
// its luminance
vec3 chroma(vec3 c) {{
    float l = dot(c, LUMA);
    vec3 own = mix(vec3(l), hue_rotate(c, u_hue), u_sat);  // _common.glsl
    return clamp(mix(own, l * u_tint_rgb, u_tint), 0.0, 1.0);
}}

// one layer over the wake so far, premultiplied; coverage is the graded
// layer's own luminance (a black pixel covers nothing), so the wake
// never paints a transparent ground opaque
void layer(vec4 t, float w, inout vec3 wake, inout float wa) {{
    vec3 c = grade(t.rgb);
    float a = w * max(c.r, max(c.g, c.b));
    wake = wake * (1.0 - a) + c * w;
    wa = wa + a - wa * a;
}}

void main() {{
    vec4 scene = texelFetch(u_scene, ivec2(gl_FragCoord.xy) - u_origin, 0);
    vec3 wake = vec3(0.0);
    float wa = 0.0;
    float y = clamp(v_uv.y, u_pad, 1.0 - u_pad) * u_slot;
    for (int i = 0; i < u_n; i++)
        layer(texture(u_ring, vec2(v_uv.x, u_off[i] + y)), u_w[i], wake, wa);
    if (u_dream_w > 0.0)
        layer(vec4(chroma(texture(u_dream, v_uv).rgb), 1.0), u_dream_w, wake, wa);
    // the render over the wake: where this frame drew, the wake beneath is
    // held back — by the faces' geometry (drawn at a few percent alpha, so
    // their brightness would barely cover) and by brightness (the wireframe)
    float cover = min(max(scene.r, max(scene.g, scene.b)) * OCCLUDE_GAIN, 1.0);
    if (u_has_cover != 0)
        cover = max(cover, texelFetch(u_cover, ivec2(gl_FragCoord.xy) - u_origin, 0).r);
    cover *= u_occlude;
    wake *= 1.0 - cover;
    wa *= 1.0 - cover;
    f_color = vec4(min(scene.rgb + wake, 1.0), scene.a + wa - scene.a * wa);
}}
"""


def post_fs(shared: str) -> str:
    """The post pass's fragment shader over `shared`, the helpers from
    shaders/_common.glsl — read when the programs are built, so an edit
    lands on the next rebuild like everywhere else."""
    return f"\n#version 330\n#define MAX_ECHOES {MAX_ECHOES}\n#line 1 1\n{shared}\n{POST_FS}"


def tint_colour(hue: float, sat: float) -> tuple[float, float, float]:
    """The tint colour for `hue` in degrees at `sat`, full value."""
    return colorsys.hsv_to_rgb((float(hue) / 360.0) % 1.0, max(0.0, min(float(sat), 1.0)), 1.0)


def scene_tint(mean, sat: float) -> tuple[float, float, float]:
    """The tint colour from a scene's mean colour (r, g, b in [0, 1]): its
    hue at `sat`, full value; grey when the mean has no chroma, or there
    is no mean yet."""
    if mean is None:
        return (1.0, 1.0, 1.0)
    r, g, b = (float(v) for v in mean)
    if max(r, g, b) - min(r, g, b) < 1e-4:
        return (1.0, 1.0, 1.0)
    return tint_colour(colorsys.rgb_to_hsv(r, g, b)[0] * 360.0, sat)


MEAN_STRIDE = 4     # mean_colour samples every 4th row and column: 0.1 ms at 400×256


def mean_colour(pixels: np.ndarray) -> tuple[float, float, float]:
    """The mean r, g, b of an (h, w, 4) uint8 image, in [0, 1] — off a
    MEAN_STRIDE grid of its pixels, which a hue cannot tell from the whole."""
    sub = pixels[::MEAN_STRIDE, ::MEAN_STRIDE].reshape(-1, 4)[:, :3]
    m = sub.mean(axis=0, dtype=np.float32) / 255.0
    return (float(m[0]), float(m[1]), float(m[2]))


def fit_atlas(size: tuple[int, int], max_tex: int) -> tuple[int, int]:
    """The echo size shrunk, aspect kept and 8-px rounded down, so the atlas
    (MAX_ECHOES slots stacked) is at most `max_tex` on each side."""
    ew, eh = size
    k = min(1.0, max_tex / (eh * MAX_ECHOES), max_tex / ew)
    if k >= 1.0:
        return size
    return max(8, int(ew * k) // 8 * 8), max(8, int(eh * k) // 8 * 8)


def echo_size(res: int, w: int, h: int) -> tuple[int, int]:
    """The echo's size: `res` on the short side, the render's aspect, 8-px rounded."""
    w, h = max(w, 1), max(h, 1)
    if w >= h:
        return max(8, round(res * w / h / 8) * 8), res
    return res, max(8, round(res * h / w / 8) * 8)


class Lookback:
    """The history ring, the dream slot and the post pass, on one GL context."""

    def __init__(self, ctx: moderngl.Context, state: DreamState | None = None,
                 source: LookbackSource | None = None):
        self.ctx = ctx
        self.state = state if state is not None else DreamState()
        self.source = source
        self.frame = 0                 # frames captured while on
        self.dream_frame = -1          # the submit `D` answers; −1 = nothing shown yet
        self.scene_mean: tuple[float, float, float] | None = None   # newest echo's, scene mode
        self.echo = (0, 0)             # slot size (w, h)
        self.atlas: moderngl.Texture | None = None
        self.dream: moderngl.Texture | None = None
        self._fbo: moderngl.Framebuffer | None = None
        self._captures: list[tuple[int, int]] = []   # (slot, frame), oldest first
        self._next = 0                 # the slot the next downsample lands in
        self._host: np.ndarray | None = None          # staging for a source without buffer()
        self._w = np.zeros(MAX_ECHOES, dtype="f4")
        self._off = np.zeros(MAX_ECHOES, dtype="f4")
        self.error = ""                # _common.glsl did not compile: on the fallback
        self.ring_error = ""           # the history textures could not be made (_ensure)
        self._build_programs()

    def _build_programs(self) -> None:
        ctx = self.ctx
        try:
            self._post = ctx.program(vertex_shader=QUAD_VS, fragment_shader=post_fs(common()))
            self.error = ""
        except Exception as e:  # noqa: BLE001 — a bad edit must not kill the show
            self.error = gl_error(e, {1: "_common.glsl:", 2: "post pass line "})
            self._post = ctx.program(vertex_shader=QUAD_VS, fragment_shader=post_fs(FALLBACK))
        self._down = ctx.program(vertex_shader=QUAD_VS, fragment_shader=DOWN_FS)
        self._post_vao = ctx.vertex_array(self._post, [])
        self._down_vao = ctx.vertex_array(self._down, [])
        self._post["u_scene"].value = 0
        self._post["u_ring"].value = 1
        self._post["u_dream"].value = 2
        self._post["u_cover"].value = 3
        self._post["u_slot"].value = 1.0 / MAX_ECHOES
        self._down["u_scene"].value = 0

    def on_reload(self) -> None:
        """Hot-swap hook (hotreload.py), and the renderer's call when
        _common.glsl is saved: recompile the programs; the ring persists.
        The old programs go only once the new ones exist."""
        old = (self._post_vao, self._down_vao, self._post, self._down)
        self._build_programs()
        for res in old:
            res.release()

    # ---- the ring ----

    def max_texture(self) -> int:
        """The driver's GL_MAX_TEXTURE_SIZE (16384 on Apple silicon)."""
        try:
            return int(self.ctx.info["GL_MAX_TEXTURE_SIZE"])
        except Exception:  # noqa: BLE001 — a context without the query: the common floor
            return 8192

    def _ensure(self, w: int, h: int) -> bool:
        """The atlas and the dream buffer at the echo size for this render
        size, the slot shrunk (aspect kept) so the atlas fits the driver's
        largest texture — a portrait window at res 384 would otherwise ask
        for a 36 864 px tall atlas and raise every frame. False, with the
        reason on `ring_error`, when the textures cannot be made: nothing
        is captured then (plan 14 WP1)."""
        size = fit_atlas(echo_size(RES[max(0, min(self.state.res, len(RES) - 1))], w, h),
                         self.max_texture())
        if size == self.echo and self.atlas is not None:
            return True
        self.release_ring()
        ew, eh = size
        try:
            self.atlas = self.ctx.texture((ew, eh * MAX_ECHOES), 4)
            self.atlas.repeat_x = self.atlas.repeat_y = False
            self.dream = self.ctx.texture((ew, eh), 4)
            self.dream.repeat_x = self.dream.repeat_y = False
            self._fbo = self.ctx.framebuffer(color_attachments=[self.atlas])
        except Exception as e:  # noqa: BLE001 — no history this frame, never a stuck ring
            self.release_ring()
            self.ring_error = f"look-back: no history at {ew}×{eh}: {e}"[:160]
            return False
        self.ring_error = ""
        self.echo = size
        self._fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self._captures.clear()
        self._next = 0
        self.dream_frame = -1
        self._host = None
        self._post["u_pad"].value = 0.5 / eh
        return True

    def release_ring(self) -> None:
        for res in (self._fbo, self.atlas, self.dream):
            if res is not None:
                res.release()
        self._fbo = self.atlas = self.dream = None
        self.echo = (0, 0)

    def slot_viewport(self, slot: int) -> tuple[int, int, int, int]:
        ew, eh = self.echo
        return (0, slot * eh, ew, eh)

    def layers(self, now: int | None = None) -> list[tuple[int, int]]:
        """(slot, age) of the echoes to composite, oldest first — the newest
        `echoes` captures, aged against `now` (default: the frame being drawn)."""
        n = max(0, min(int(self.state.echoes), MAX_ECHOES))
        if n == 0 or not self._captures:
            return []
        now = self.frame + 1 if now is None else now
        return [(slot, now - f) for slot, f in self._captures[-n:]]

    def weights(self, now: int | None = None) -> list[tuple[int, float]]:
        """(slot, weight) per echo, oldest first: echo_mix · decay^age."""
        s = self.state
        return [(slot, s.echo_mix * s.decay ** age) for slot, age in self.layers(now)]

    # ---- the frame: pull → composite → capture ----

    def wants_cover(self) -> bool:
        """Whether the renderer should draw the faces' coverage mask this
        frame: only while the look-back is on and the render occludes."""
        return bool(self.state.on) and float(self.state.occlude) > 0.0

    def composite(self, scene: moderngl.Texture, target: moderngl.Framebuffer,
                  cover: moderngl.Texture | None = None) -> None:
        """The post pass into `target`'s viewport: scene ⊕ wake, or a copy when
        off. `cover` is the faces' coverage mask at the scene's size (render.py
        draws it when wants_cover()); without it brightness alone occludes."""
        s, ctx, p = self.state, self.ctx, self._post
        x, y, _, _ = target.viewport
        target.use()
        ctx.disable(moderngl.BLEND)      # the texture is already composited; write it
        scene.use(location=0)
        (cover if cover is not None else scene).use(location=3)
        p["u_has_cover"].value = int(cover is not None)
        n = 0
        dream_w = 0.0
        if s.on and self.atlas is not None:
            self.atlas.use(location=1)
            self.dream.use(location=2)
            for slot, wgt in self.weights():
                self._w[n], self._off[n] = wgt, slot / MAX_ECHOES
                n += 1
            if self.dream_frame >= 0:
                dream_w = float(s.mix)
        else:
            scene.use(location=1)
            scene.use(location=2)
        p["u_origin"].value = (x, y)
        p["u_n"].value = n
        if n:
            p["u_w"].write(self._w.tobytes())
            p["u_off"].write(self._off.tobytes())
        p["u_dream_w"].value = dream_w
        p["u_darken"].value = float(s.darken)
        p["u_contrast"].value = float(s.contrast)
        p["u_occlude"].value = float(s.occlude)
        if dream_w > 0.0:
            p["u_hue"].value = math.radians(float(s.hue))
            p["u_sat"].value = float(s.sat)
            p["u_tint"].value = float(s.tint)
            p["u_tint_rgb"].value = self.tint_rgb()
        self._post_vao.render(moderngl.TRIANGLES, vertices=3)
        ctx.enable(moderngl.BLEND)

    def capture(self, scene: moderngl.Texture, target: moderngl.Framebuffer) -> None:
        """After the composite: this frame into the ring (on the cadence) and,
        with a source attached, out to it. `target` is bound again on every
        return, a raise included: `_ensure` binds the atlas, and the early
        return on a frame with nothing to capture (off the cadence, no
        worker, no scene tint) once left it bound for good (plan 14 WP1)."""
        try:
            self._capture(scene, target)
        finally:
            target.use()

    def _capture(self, scene: moderngl.Texture, target: moderngl.Framebuffer) -> None:
        s = self.state
        if not s.on:
            self.idle()
            return
        _, _, w, h = target.viewport
        if not self._ensure(w, h):
            return
        self.frame += 1
        commit = self.frame % max(1, int(s.every)) == 0
        want_mean = self.scene_tinted()
        if not commit and self.source is None and not want_mean:
            return
        # the slot's previous occupant is the oldest capture; it goes even
        # when this frame is not committed, so an echo never shows a frame
        # newer than its age says
        slot = self._next
        self._captures = [c for c in self._captures if c[0] != slot]
        self._downsample(scene, slot)
        if commit:
            self._captures.append((slot, self.frame))
            self._next = (slot + 1) % MAX_ECHOES
        if self.source is not None or want_mean:
            # one read serves both: the worker's copy path and the scene's
            # mean colour for the tint (taken before the worker owns the slot)
            buf = self._buffer(self.source)
            self.read_into(buf, slot)
            if want_mean:
                self.scene_mean = mean_colour(buf)
            if self.source is not None:
                self.source.submit(buf, self.frame)

    def scene_tinted(self) -> bool:
        """Whether the dream's tint takes its hue from the scene this frame."""
        return int(self.state.tint_from) == 1

    def tint_rgb(self) -> tuple[float, float, float]:
        """The tint colour the composite uses this frame: the chosen hue and
        saturation, or the newest echo's mean hue at that saturation."""
        s = self.state
        if self.scene_tinted():
            return scene_tint(self.scene_mean, s.tint_sat)
        return tint_colour(s.tint_hue, s.tint_sat)

    def pull(self) -> bool:
        """A finished dream result, if the source has a new one, into `D`."""
        if self.source is None or self.dream is None:
            return False
        got = self.source.latest()
        if got is None:
            return False
        pixels, index = got
        if index == self.dream_frame:
            return False
        self.write_from(pixels, index)
        return True

    def idle(self) -> None:
        """Off: forget the history so a re-enable starts clean."""
        self._captures.clear()
        self.dream_frame = -1
        self.scene_mean = None

    def _downsample(self, scene: moderngl.Texture, slot: int) -> None:
        scene.build_mipmaps()            # sets LINEAR_MIPMAP_LINEAR on the texture
        self._fbo.use()
        self.ctx.viewport = self.slot_viewport(slot)
        self.ctx.disable(moderngl.BLEND)
        scene.use(location=0)
        self._down_vao.render(moderngl.TRIANGLES, vertices=3)
        self.ctx.enable(moderngl.BLEND)

    def _buffer(self, source) -> np.ndarray:
        ew, eh = self.echo
        shape = (eh, ew, 4)
        alloc = getattr(source, "buffer", None)
        if alloc is not None:
            buf = alloc(shape)
            if buf is not None:
                return buf
        if self._host is None or self._host.shape != shape:
            self._host = np.empty(shape, dtype=np.uint8)
        return self._host

    # ---- the copy path: the two GL legs WP6b's worker rides ----

    def newest(self) -> int | None:
        """The slot holding the newest downsample, or None before the first."""
        if self.atlas is None:
            return None
        if self._captures:
            return self._captures[-1][0]
        return None

    def read_into(self, array: np.ndarray, slot: int | None = None) -> None:
        """glReadPixels of one echo into `array` ((h, w, 4) uint8, any
        writable buffer — a torch host alias included), rows bottom-up."""
        if self._fbo is None:
            raise RuntimeError("lookback: no history yet")
        if slot is None:
            slot = self.newest()
            if slot is None:
                raise RuntimeError("lookback: nothing captured yet")
        self._fbo.read_into(array, viewport=self.slot_viewport(slot), components=4)

    def write_from(self, array: np.ndarray, frame_index: int = 0) -> None:
        """Upload a dream result ((h, w, 4) uint8 at the echo size) into `D`."""
        if self.dream is None:
            raise RuntimeError("lookback: no history yet")
        self.dream.write(array)
        self.dream_frame = frame_index

    def write_slot(self, slot: int, array: np.ndarray, frame_index: int | None = None) -> None:
        """Put pixels straight into an echo slot (tests, tools); with a frame
        index it also counts as a capture."""
        ew, eh = self.echo
        self.atlas.write(array, viewport=(0, slot * eh, ew, eh))
        if frame_index is not None:
            self._captures = [c for c in self._captures if c[0] != slot]
            self._captures.append((slot, frame_index))
            self._captures.sort(key=lambda c: c[1])
            self._next = (slot + 1) % MAX_ECHOES

    # ---- what the panel shows ----

    def thumbnails(self) -> list[dict[str, Any]]:
        """The echoes newest first, as imgui image coordinates into the atlas
        (v flipped: GL rows are bottom-up) with their age and weight."""
        if self.atlas is None:
            return []
        out = []
        for (slot, age), (_, wgt) in zip(reversed(self.layers()), reversed(self.weights())):
            v0, v1 = (slot + 1) / MAX_ECHOES, slot / MAX_ECHOES
            out.append({"slot": slot, "age": age, "weight": wgt, "uv0": (0.0, v0),
                        "uv1": (1.0, v1)})
        return out
