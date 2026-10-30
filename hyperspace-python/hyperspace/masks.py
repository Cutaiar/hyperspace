"""The mask passes (plan 39 T2, W1–W3): a mask as its own wire.

A mask is a pattern — a pixel passes (1) or it does not (0); a value
between is only an edge the softness or the feather asked for — held as a
one-channel 8-bit texture at its maker's size. It never rides in a
picture's alpha (the owner, 2026-10-27: "alpha is not a mask"). Three
passes make, show and use one, each a fullscreen triangle over the
target's viewport (`glsl.QUAD_VS`), premultiplied in and out:

- `MATTE_FS`, picture → mask (the `matte` node): from the picture's
  brightness, its own coverage, or its closeness to a keyed hue; `key`
  where a pixel starts to pass, `soft` the edge's width, `invert`. Then,
  when `feather` > 0, `BLUR_FS` twice — across, then down — a separable
  Gaussian of one channel.
- `PROMOTE_FS`, mask → picture (W1's promotion: a mask wired where a
  picture is taken): white where it passes, black elsewhere, opaque,
  fitted into the consumer by cover as an own-sized node is.
- `CUT_FS`, picture + mask → picture (T3's `cut`): where the mask passes
  the picture, elsewhere cut away to transparent black, by `amount`.
- Plan 39 T4 (`segment`): `MOTION_FS` and `LEARN_FS`, motion mode's
  background model — the mask where the picture differs from the
  background it has learnt, and the background learning the picture;
  `DOWN_FS` and `readback`, a picture downsampled and read back for the
  segment worker (the dream's path); `feather`, a mask's blur alone.

Orientation: every mask a GL pass made has its first row at the bottom,
as every texture here; one uploaded from a CPU array as it is (the segment
worker's matte) has its top row first. Each pass that samples a mask —
`PROMOTE_FS`, `CUT_FS`, and `fit` through the promotion — takes `u_flip`
(`flip=`) and reads such a mask upside down, so it lands the right way up
(the flag is the maker's: `graph.mask_of`).

`MaskPasses` is the one object the renderer holds (`Renderer.mask_passes`):
the programs compiled once, the targets asked of the renderer's
`_frame_target` it is given (so they are kept and freed with every other
frame texture). This module imports moderngl, numpy and `glsl` only (a
test holds it to that); `graph.py` reaches it through the renderer, never
by import.
"""

from __future__ import annotations

from collections.abc import Callable

import moderngl
import numpy as np

from .glsl import QUAD_VS

# the sources `MATTE_FS` reads (`u_from`), in `view.MATTE_FROM`'s order
LUMA, ALPHA, CHROMA = 0, 1, 2
# the most px a feather blurs by each way (`BLUR_FS`'s loop bound)
MAX_FEATHER = 32

# picture → mask. `v` is how far a pixel is towards passing, 0–1: its
# brightness (premultiplied: a transparent pixel is dark), its coverage, or
# its closeness to the keyed colour's chroma (1 on it, 0 a full chroma
# circle's radius away — the pixel's colour unpremultiplied first, then
# its coverage on top, so a transparent pixel never passes). The mask is
# `v` at or past `key` — hard at `soft` 0, else a smoothstep `soft` either
# side — inverted on `u_invert`
MATTE_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform int u_from;
uniform float u_key;
uniform float u_soft;
uniform int u_invert;
uniform vec2 u_chroma;     // the keyed colour's chroma: sat · (cos, sin) of its hue
out vec4 f_color;

vec2 chroma_of(vec3 rgb) {
    float hi = max(rgb.r, max(rgb.g, rgb.b));
    float lo = min(rgb.r, min(rgb.g, rgb.b));
    float d = hi - lo;
    if (hi <= 0.0 || d <= 0.0) return vec2(0.0);
    float h;
    if (hi == rgb.r) h = mod((rgb.g - rgb.b) / d, 6.0);
    else if (hi == rgb.g) h = (rgb.b - rgb.r) / d + 2.0;
    else h = (rgb.r - rgb.g) / d + 4.0;
    float a = h / 6.0 * 6.28318530718;
    return (d / hi) * vec2(cos(a), sin(a));
}

void main() {
    vec4 c = texture(u_src, v_uv);
    float v;
    if (u_from == 1) {
        v = c.a;
    } else if (u_from == 2) {
        vec3 rgb = c.a > 0.0 ? c.rgb / c.a : vec3(0.0);
        v = (1.0 - clamp(distance(chroma_of(rgb), u_chroma), 0.0, 1.0)) * c.a;
    } else {
        v = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
    }
    float m = u_soft > 0.0 ? smoothstep(u_key - u_soft, u_key + u_soft, v)
                           : (v >= u_key ? 1.0 : 0.0);
    if (u_invert != 0) m = 1.0 - m;
    f_color = vec4(m, 0.0, 0.0, 1.0);
}
"""

# one channel blurred along `u_step` (one texel across, or down): a
# Gaussian of `u_radius` px each way (sigma half of it), each tap held
# inside the texture's edge texels (never wrapped, whatever its repeat)
BLUR_FS = f"""
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform vec2 u_step;
uniform float u_radius;
out vec4 f_color;
void main() {{
    vec2 half_texel = 0.5 / vec2(textureSize(u_src, 0));
    float sigma = max(u_radius * 0.5, 0.5);
    float sum = 0.0;
    float wsum = 0.0;
    for (int i = -{MAX_FEATHER}; i <= {MAX_FEATHER}; i++) {{
        float x = float(i);
        if (abs(x) > u_radius) continue;
        float w = exp(-0.5 * x * x / (sigma * sigma));
        sum += texture(u_src, clamp(v_uv + u_step * x, half_texel, 1.0 - half_texel)).r * w;
        wsum += w;
    }}
    f_color = vec4(sum / wsum, 0.0, 0.0, 1.0);
}}
"""

# mask → picture (W1): the mask laid into the consumer's viewport about the
# centre by `u_scale` (cover: `cover_scale`), sampled inside its edge
# texels, white where it passes, black elsewhere, opaque — a grey picture,
# premultiplied. Plan 39 T4: `u_flip` reads a rows-top-first mask upside
# down (as `CUT_FS` does), so a segment's matte lands the right way up
PROMOTE_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_mask;
uniform vec2 u_scale;
uniform int u_flip;
out vec4 f_color;
void main() {
    vec2 half_texel = 0.5 / vec2(textureSize(u_mask, 0));
    vec2 uv = clamp(0.5 + (v_uv - 0.5) * u_scale, half_texel, 1.0 - half_texel);
    if (u_flip != 0) uv.y = 1.0 - uv.y;
    float m = texture(u_mask, uv).r;
    f_color = vec4(vec3(m), 1.0);
}
"""

# picture + mask → picture (W3, T3's `cut`): the mask sampled bilinearly at
# the picture's size, fitted by cover (`u_scale`, `cover_scale` of the mask
# into the picture: where the promoted picture shows it); where it passes
# the picture, elsewhere the picture × (1 − amount) — 1 cuts to transparent
# black, 0.5 dims; `u_invert` keeps the hole and cuts the rest.
# Premultiplied in and out, so colour and alpha go together. Plan 39 T3:
# `u_flip` reads the mask upside down — for a mask whose rows are top first
# (a CPU array uploaded as it is: T4's segment worker), where every mask a
# GL pass made has its first row at the bottom
CUT_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform sampler2D u_mask;
uniform vec2 u_scale;
uniform int u_invert;
uniform float u_amount;
uniform int u_flip;
uniform int u_scaled;      // 1 when u_src is not the target's size
uniform ivec2 u_origin;    // the target rect's origin (gl_FragCoord is window-relative)
out vec4 f_color;
void main() {
    vec2 half_texel = 0.5 / vec2(textureSize(u_mask, 0));
    vec2 uv = clamp(0.5 + (v_uv - 0.5) * u_scale, half_texel, 1.0 - half_texel);
    if (u_flip != 0) uv.y = 1.0 - uv.y;
    float m = texture(u_mask, uv).r;
    if (u_invert != 0) m = 1.0 - m;
    // the picture 1:1 by texelFetch (fx.FS_TAIL's `here`: llvmpipe does not
    // land a 1:1 read through a LINEAR sampler on its texel)
    vec4 c = u_scaled != 0 ? texture(u_src, v_uv)
                           : texelFetch(u_src, ivec2(gl_FragCoord.xy) - u_origin, 0);
    f_color = c * mix(1.0, m, clamp(u_amount, 0.0, 1.0));
}
"""


# plan 39 T4 (W4, motion mode): the mask where the picture differs from the
# background model — `d` the largest channel's difference (premultiplied,
# alpha included), the mask `smoothstep(sense − soft, sense + soft, d)`;
# and the model learning the picture, `bg ← mix(bg, picture, k)` (k from
# `segment.learn`'s seconds)
MOTION_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform sampler2D u_bg;
uniform float u_sense;
uniform float u_soft;
out vec4 f_color;
void main() {
    vec4 d4 = abs(texture(u_src, v_uv) - texture(u_bg, v_uv));
    float d = max(max(d4.r, d4.g), max(d4.b, d4.a));
    float m = smoothstep(u_sense - u_soft, u_sense + u_soft, d);
    f_color = vec4(m, 0.0, 0.0, 1.0);
}
"""

LEARN_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform sampler2D u_bg;
uniform float u_k;
out vec4 f_color;
void main() {
    f_color = mix(texture(u_bg, v_uv), texture(u_src, v_uv), clamp(u_k, 0.0, 1.0));
}
"""

# a picture into a smaller target (the readback for the segment worker):
# trilinear over its mipmaps, a box-ish downsample, as the dream's DOWN_FS
DOWN_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
out vec4 f_color;
void main() { f_color = texture(u_src, v_uv); }
"""
MOTION_SOFT = 0.04      # motion's edge either side of `sense`


def cover_scale(src: tuple[int, int], dst: tuple[int, int]) -> tuple[float, float]:
    """The cover fit's scale from `dst`'s uv to `src`'s about the centre —
    `media_tex.fit_scale(COVER, …)`, written out because this module imports
    no media module (a test holds the two equal)."""
    sw, sh = max(int(src[0]), 1), max(int(src[1]), 1)
    dw, dh = max(int(dst[0]), 1), max(int(dst[1]), 1)
    k = max(dw / sw, dh / sh)
    return (dw / (sw * k), dh / (sh * k))


def chroma(hue: float, sat: float) -> tuple[float, float]:
    """The keyed colour's chroma, as `MATTE_FS` measures a pixel's: `sat`
    along the hue's angle (`hue` 0–1 round the wheel, 0 red, 1/3 green)."""
    a = float(hue) * 2.0 * np.pi
    s = min(max(float(sat), 0.0), 1.0)
    return (s * float(np.cos(a)), s * float(np.sin(a)))


# what `MaskPasses` asks of the renderer: `_frame_target(key, size, dtype,
# components)` → (texture, framebuffer), kept by key
FrameTarget = Callable[..., tuple[moderngl.Texture, moderngl.Framebuffer]]


class MaskPasses:
    """The mask passes' programs, compiled once on the renderer's context,
    and the passes themselves. `frame_target` is the renderer's
    (`Renderer._frame_target`): a matte's mask and its feather's half-way
    texture are frame textures of their own key and size, one channel."""

    def __init__(self, ctx: moderngl.Context, frame_target: FrameTarget):
        self.ctx = ctx
        self.frame_target = frame_target
        self._progs: dict[str, tuple[moderngl.Program, moderngl.VertexArray]] = {}
        for name, fs in (("matte", MATTE_FS), ("blur", BLUR_FS), ("promote", PROMOTE_FS),
                         ("cut", CUT_FS), ("motion", MOTION_FS), ("learn", LEARN_FS),
                         ("down", DOWN_FS)):
            prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=fs)
            try:
                vao = ctx.vertex_array(prog, [])
            except Exception:
                prog.release()
                raise
            self._progs[name] = (prog, vao)

        self._mip = None            # (the readback's trilinear sampler, made on first use)

    def release(self) -> None:
        for prog, vao in self._progs.values():
            vao.release()
            prog.release()
        self._progs = {}
        if self._mip is not None:
            self._mip.release()
            self._mip = None

    def _run(self, name: str, dst: moderngl.Framebuffer, rect: tuple[int, int, int, int],
             textures: tuple[moderngl.Texture, ...], **uniforms) -> None:
        """One pass of program `name` into `dst`'s `rect`, blending off,
        `textures` bound to units 0, 1 … in the program's sampler order."""
        prog, vao = self._progs[name]
        ctx = self.ctx
        dst.use()
        ctx.viewport = rect
        ctx.disable(moderngl.BLEND)
        try:
            for unit, tex in enumerate(textures):
                tex.use(location=unit)
            for key, value in uniforms.items():
                if key in prog:
                    prog[key].value = value
            vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)

    def matte(self, src: moderngl.Texture, key, size: tuple[int, int], *, source: int = LUMA,
              level: float = 0.5, soft: float = 0.0, invert: bool = False,
              feather: float = 0.0, hue: float = 1.0 / 3.0, sat: float = 1.0
              ) -> moderngl.Texture:
        """Picture `src` → a one-channel mask at `size` (`src`'s texels
        sampled straight across: the mask is the picture's own size), kept
        under frame key `(key, size)`; feathered by two `BLUR_FS` passes —
        across into `(key + "/blur", size)`, then down back into the mask —
        when `feather` > 0. Returns the mask."""
        size = (int(size[0]), int(size[1]))
        rect = (0, 0, *size)
        out, fbo = self.frame_target((key, size), size, components=1)
        self._run("matte", fbo, rect, (src,), u_src=0, u_from=int(source),
                  u_key=float(level), u_soft=max(float(soft), 0.0),
                  u_invert=int(bool(invert)), u_chroma=chroma(hue, sat))
        radius = min(max(float(feather), 0.0), float(MAX_FEATHER))
        if radius > 0.0:
            half, hfbo = self.frame_target((f"{key}/blur", size), size, components=1)
            self._run("blur", hfbo, rect, (out,), u_src=0, u_step=(1.0 / size[0], 0.0),
                      u_radius=radius)
            self._run("blur", fbo, rect, (half,), u_src=0, u_step=(0.0, 1.0 / size[1]),
                      u_radius=radius)
        return out

    def feather(self, mask: moderngl.Texture, key, radius: float) -> moderngl.Texture:
        """Mask `mask` blurred by `radius` px (plan 39 T4: a segment's matte,
        `BLUR_FS` twice) into a target of its own at the mask's size, kept
        under frame key `key` (the half-way one `(key, "/blur")`) — its rows
        as `mask`'s (a blur does not mind which way up). `mask` itself at
        radius 0."""
        radius = min(max(float(radius), 0.0), float(MAX_FEATHER))
        if radius <= 0.0:
            return mask
        size = (int(mask.size[0]), int(mask.size[1]))
        rect = (0, 0, *size)
        half, hfbo = self.frame_target((key, "/blur"), size, components=1)
        out, fbo = self.frame_target(key, size, components=1)
        self._run("blur", hfbo, rect, (mask,), u_src=0, u_step=(1.0 / size[0], 0.0),
                  u_radius=radius)
        self._run("blur", fbo, rect, (half,), u_src=0, u_step=(0.0, 1.0 / size[1]),
                  u_radius=radius)
        return out

    def motion(self, src: moderngl.Texture, bg: moderngl.Texture | None,
               dst: moderngl.Framebuffer, *, sense: float, soft: float = MOTION_SOFT) -> None:
        """Motion mode's mask into `dst`'s viewport (plan 39 T4, `MOTION_FS`):
        1 where picture `src` differs from background `bg` past `sense`,
        both read 1:1 at `dst`'s size. No background yet: nothing passes."""
        rect = tuple(int(v) for v in dst.viewport)
        if bg is None:
            dst.use()
            self.ctx.viewport = rect
            self.ctx.clear(0.0, 0.0, 0.0, 1.0, viewport=rect)
            return
        self._run("motion", dst, rect, (src, bg), u_src=0, u_bg=1,
                  u_sense=float(sense), u_soft=max(float(soft), 1e-4))

    def learn(self, src: moderngl.Texture, bg: moderngl.Texture | None,
              dst: moderngl.Framebuffer, k: float) -> None:
        """The background model's step into `dst` (`LEARN_FS`): `bg` moved
        towards picture `src` by `k` (0 still, 1 the picture itself); with no
        `bg` yet, the picture itself."""
        rect = tuple(int(v) for v in dst.viewport)
        self._run("learn", dst, rect, (src, bg if bg is not None else src), u_src=0, u_bg=1,
                  u_k=1.0 if bg is None else float(k))

    def readback(self, src: moderngl.Texture, key, size: tuple[int, int],
                 out: np.ndarray | None = None) -> np.ndarray:
        """Picture `src` downsampled to `size` (trilinear over its mipmaps:
        the dream's path) into an RGBA8 target kept under frame key `key`,
        and read back once into `out` (an (h, w, 4) uint8 array; a new one
        when None or another shape) — its rows bottom first, as GL's are."""
        size = (int(size[0]), int(size[1]))
        _, fbo = self.frame_target(key, size)
        if self._mip is None:
            self._mip = self.ctx.sampler(filter=(moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR),
                                         repeat_x=False, repeat_y=False)
        src.build_mipmaps()
        self._mip.use(location=0)
        try:
            self._run("down", fbo, (0, 0, *size), (src,), u_src=0)
        finally:
            self._mip.clear(location=0)
        shape = (size[1], size[0], 4)
        if out is None or out.shape != shape or out.dtype != np.uint8:
            out = np.empty(shape, np.uint8)
        fbo.read_into(out, components=4)
        return out

    def promote(self, mask: moderngl.Texture, dst: moderngl.Framebuffer, *,
                flip: bool = False) -> None:
        """Mask `mask` as a picture into `dst`'s viewport (W1): white where
        it passes, black elsewhere, opaque, fitted by cover. `flip`: its rows
        are top first (plan 39 T4), so it is read upside down."""
        rect = tuple(int(v) for v in dst.viewport)
        self._run("promote", dst, rect, (mask,), u_mask=0,
                  u_scale=cover_scale(mask.size, rect[2:]), u_flip=int(bool(flip)))

    def cut(self, src: moderngl.Texture, mask: moderngl.Texture, dst: moderngl.Framebuffer,
            *, invert: bool = False, amount: float = 1.0, flip: bool = False) -> None:
        """Picture `src` cut by `mask` into `dst`'s viewport (W3, `CUT_FS`):
        what passes stays, the rest goes to transparent black by `amount`
        (1 all the way, 0.5 dimmed by half, 0 not at all); `invert` keeps
        the hole and cuts the rest. `src` is read 1:1 — the picture at
        `dst`'s size; the mask is fitted into it by cover, as the promotion
        fits it, sampled bilinearly. `flip`: the mask's rows are top first
        (a CPU array uploaded as it is — plan 39 T4's segment sets it), so
        it is read upside down. Callers: the `cut` node (plan 39 T3,
        `graph.CutNode`), and T4's `segment.fg` / `.bg` (the bg inverted)."""
        rect = tuple(int(v) for v in dst.viewport)
        self._run("cut", dst, rect, (src, mask), u_src=0, u_mask=1,
                  u_scale=cover_scale(mask.size, rect[2:]),
                  u_invert=int(bool(invert)), u_amount=float(amount),
                  u_flip=int(bool(flip)),
                  u_scaled=int(tuple(rect[2:]) != tuple(src.size)), u_origin=rect[:2])

    def fit(self, mask: moderngl.Texture, key, size: tuple[int, int], *,
            flip: bool = False) -> moderngl.Texture:
        """Mask `mask` refitted by cover to `size`, one channel (`PROMOTE_FS`
        into an R8 target: its red is the mask), kept under frame key `key` —
        what a mask port that reads the frame's pixels 1:1 binds
        (`lookback.cover`), so the mask lands where its promoted picture
        shows it. `flip` (plan 39 T4): its rows are top first — the refit
        turns it the right way up, as every GL mask is. Returns `mask`
        itself when it is that size already and needs no turning."""
        size = (int(size[0]), int(size[1]))
        if tuple(mask.size) == size and not flip:
            return mask
        out, fbo = self.frame_target(key, size, components=1)
        fbo.viewport = (0, 0, *size)
        self.promote(mask, fbo, flip=flip)
        return out
