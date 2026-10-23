"""The media channels' textures (plan 32 R): one GL texture per channel,
and the fit pass's shader that lays one into a frame.

`MediaTextures.texture(c, f)` is the one place a channel's picture
becomes a texture, on the frame thread, only when something in the frame
reads the channel (`Renderer.media_texture`, the `media.<c>` graph node):
a channel nothing reads this frame plays on — its clock runs in
`MediaState.poll` — but is never read here, so never uploaded. A frame
of pixels (a still, a decoded video frame, a camera's) is written into
the channel's texture only when its `(frame, t)` moved, into a texture
made again only when its size changed, with mipmaps for the faces'
sampling. A GPU frame (a texture name in the renderer's share group)
never comes through the CPU: a `GL_TEXTURE_2D` one is wrapped as it is
(`ctx.external_texture`; releasing the wrapper never deletes the source's
texture), and a `GL_TEXTURE_RECTANGLE` one — what a Syphon client's
IOSurface-backed texture is on macOS GL, which neither moderngl nor a
`sampler2D` can read — is blitted on the GPU into the channel's own 2D
texture when its frame moved (`blits`), mipmapped like an upload. The
blit is the one place this module calls GL itself (PyOpenGL, imported
only when a rectangle frame arrives: it comes with syphon-python).

The way up: an uploaded frame's rows are top first (`MediaFrame.pixels`)
and GL puts the first row at v = 0, so the texture holds the picture
upside down in GL's terms and whoever samples it flips v (`flipped`); a
GPU frame is in GL's own row order (row 0 at the bottom) and is drawn as
it is. Uploading the rows reversed would be a copy of every frame on the
frame thread, which the plan forbids.

Plan 32 T6 found the Syphon spike's "read as 2D" wrong: binding the
client's texture as 2D is GL_INVALID_OPERATION and reads whatever 2D
texture was bound before (`test_a_syphon_frame_samples_through_the_fit_pass`
samples the real thing).

Render stack (ARCHITECTURE §3): moderngl and numpy only; the frame is
duck-typed (`pixels`, `texture`, `tex_size`, `frame`, `t`, `size`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl

TEX_2D, TEX_RECT = 0x0DE1, 0x84F5      # = media.frame's (a GPU frame's `tex_target`)

# how a channel's picture fills a frame of another shape: `channels.FITS`,
# by index (`media.<c>.fit`); a test holds the two equal
FITS = ("cover", "contain", "stretch")
COVER, CONTAIN, STRETCH = range(len(FITS))


def fit_scale(fit: int, src: tuple[int, int], dst: tuple[int, int]) -> tuple[float, float]:
    """The fit pass's scale from the frame's uv to the picture's, about the
    centre: `uv_src = 0.5 + (uv - 0.5) · scale`. Cover crops (each ≤ 1),
    contain letterboxes (each ≥ 1; outside [0, 1] is transparent), stretch
    is 1, 1. An unknown fit is cover."""
    if fit == STRETCH:
        return (1.0, 1.0)
    sw, sh = max(src[0], 1), max(src[1], 1)
    dw, dh = max(dst[0], 1), max(dst[1], 1)
    k = (min if fit == CONTAIN else max)(dw / sw, dh / sh)
    return (dw / (sw * k), dh / (sh * k))


# the fit pass (`Renderer._media_fit`): the channel's texture into a frame-
# sized target, fitted, premultiplied — by its own alpha (a PNG's) and by
# `u_alpha` (the backdrop's fader) — with the letterbox transparent black
FIT_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform vec2 u_scale;      // frame uv → picture uv, about the centre (fit_scale)
uniform int u_flip;        // the texture's first row is the picture's top (an upload)
uniform float u_alpha;
out vec4 f_color;
void main() {
    vec2 uv = 0.5 + (v_uv - 0.5) * u_scale;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) {
        f_color = vec4(0.0);
        return;
    }
    if (u_flip != 0) uv.y = 1.0 - uv.y;
    vec4 c = texture(u_src, uv);
    f_color = vec4(c.rgb * c.a, c.a) * u_alpha;
}
"""


@dataclass
class _Slot:
    """One channel's texture: the one it owns (uploads), or the wrapper of
    a GPU frame's, and what it holds."""

    tex: moderngl.Texture | None = None      # owned: made here, written here
    key: tuple | None = None                 # the (frame, t) written into it
    ext: moderngl.Texture | None = None      # a GPU frame's texture, wrapped
    ext_key: tuple | None = None             # (its name, its size)
    flipped: bool = True                     # what `texture` last returned is an upload
    fbo: moderngl.Framebuffer | None = None  # on `tex`: a rectangle frame's blit lands here


class MediaTextures:
    """The channels' textures on one context (see the module). `uploads`
    counts the frames written from the CPU and `blits` the rectangle
    frames copied on the GPU, for the tests and the SYSTEM page; `error`
    says why the last rectangle frame could not be copied ("" when it
    could)."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.uploads = 0
        self.blits = 0
        self.error = ""
        self._slots: dict[str, _Slot] = {}
        self._read_fbo: int | None = None     # GL's name: the blit's read framebuffer

    def texture(self, c: str, f: Any) -> moderngl.Texture | None:
        """Channel `c`'s texture holding frame `f` (a `MediaFrame`), or None
        for no frame (black). Written only when `f` moved; made again only
        when its size changed; a GPU frame wrapped, never written."""
        if f is None:
            return None
        slot = self._slots.setdefault(c, _Slot())
        if getattr(f, "texture", None) is not None:
            if getattr(f, "tex_target", TEX_2D) == TEX_RECT:
                return self._blitted(slot, f)
            want = (int(f.texture), tuple(f.tex_size))
            if slot.ext is None or slot.ext_key != want:
                if slot.ext is not None:
                    slot.ext.release()            # the wrapper only: not the source's texture
                slot.ext = self.ctx.external_texture(want[0], want[1], 4, 0, "f1")
                # GL's default minifier wants mipmaps a wrapped texture lacks:
                # without this it is incomplete and samples black
                slot.ext.filter = (moderngl.LINEAR, moderngl.LINEAR)
                slot.ext.repeat_x = slot.ext.repeat_y = False
                slot.ext_key = want
            slot.flipped = False
            return slot.ext
        tex = self._owned(slot, tuple(f.size))
        key = (f.frame, f.t)
        if slot.key != key:
            tex.write(f.pixels)
            tex.build_mipmaps()
            slot.key = key
            self.uploads += 1
        slot.flipped = True
        return tex

    def _owned(self, slot: _Slot, size: tuple[int, int]) -> moderngl.Texture:
        """The channel's own texture at `size`: made again (empty) when the
        size changed."""
        tex = slot.tex
        if tex is None or tuple(tex.size) != size:
            for res in (slot.fbo, tex):
                if res is not None:
                    res.release()
            slot.fbo = None
            tex = slot.tex = self.ctx.texture(size, 4)
            tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            tex.repeat_x = tex.repeat_y = False
            slot.key = None
        return tex

    def _blitted(self, slot: _Slot, f: Any) -> moderngl.Texture | None:
        """A rectangle frame's texture copied on the GPU into the channel's
        own (see the module) when its frame moved; None when GL refused
        (`error` says why) — black, never a raise on the frame thread."""
        size = (int(f.tex_size[0]), int(f.tex_size[1]))
        tex = self._owned(slot, size)
        slot.flipped = False                 # GL's row order: drawn as it is
        key = ("rect", int(f.texture), f.frame, f.t)
        if slot.key == key:
            return tex
        ctx = self.ctx
        if slot.fbo is None:
            slot.fbo = ctx.framebuffer(color_attachments=[tex])
        prev = ctx.fbo
        _ = ctx.error                        # a stale error is not the blit's
        try:
            from OpenGL import GL  # syphon-python's: only a rectangle frame gets here

            if self._read_fbo is None:
                self._read_fbo = int(GL.glGenFramebuffers(1))
            GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self._read_fbo)
            GL.glFramebufferTexture2D(GL.GL_READ_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                      TEX_RECT, int(f.texture), 0)
            GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, slot.fbo.glo)
            w, h = size
            GL.glBlitFramebuffer(0, 0, w, h, 0, 0, w, h, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
            GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self._read_fbo)
            GL.glFramebufferTexture2D(GL.GL_READ_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                      TEX_RECT, 0, 0)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        except Exception as e:  # noqa: BLE001 — a feed must not take the frame down
            self.error = f"{type(e).__name__}: {e}"[:120]
            return None
        finally:
            if prev is not None:
                prev.use()                   # moderngl binds what it thinks is bound
        tex.build_mipmaps()
        slot.key = key
        self.blits += 1
        self.error = ""
        return tex

    def flipped(self, c: str) -> bool:
        """Whether channel `c`'s texture, as `texture` last returned it, holds
        the picture top row first (an upload: flip v to sample it upright)."""
        slot = self._slots.get(c)
        return True if slot is None else slot.flipped

    def release(self) -> None:
        """Every texture made here, and every wrapper, released; the next
        `texture` uploads afresh."""
        for slot in self._slots.values():
            for res in (slot.fbo, slot.tex, slot.ext):
                if res is not None:
                    res.release()
        self._slots = {}
        if self._read_fbo is not None:
            try:
                from OpenGL import GL

                GL.glDeleteFramebuffers(1, [self._read_fbo])
            except Exception:  # noqa: BLE001, S110 — a lost context: nothing to free
                pass
            self._read_fbo = None


UI_TEXTURES = 256       # the most thumbnails kept; the least recently drawn goes first


class UiTextures:
    """Small pictures the control panel draws — the MEDIA page's library
    thumbnails (plan 32 T10) — as textures of the render context. The page
    decodes a thumbnail's PNG on the media pool and hands the pixels here
    (`put`); the renderer makes the texture in its own frame (`upload`),
    with its context current, so the panel never makes a GL object on the
    control window's context (the share group shares textures, not the
    state moderngl keeps for its context). `get` is the texture once made,
    None until then. At most `limit` are kept: the one drawn least
    recently is released first."""

    def __init__(self, ctx: moderngl.Context, limit: int = UI_TEXTURES):
        self.ctx = ctx
        self.limit = limit
        self._tex: dict[Any, moderngl.Texture] = {}   # oldest first (insertion order)
        self._todo: dict[Any, tuple[tuple[int, int], bytes]] = {}

    def get(self, key) -> moderngl.Texture | None:
        tex = self._tex.pop(key, None)
        if tex is not None:
            self._tex[key] = tex          # drawn now: the newest
        return tex

    def put(self, key, size: tuple[int, int], data: bytes) -> None:
        """Queue RGBA8 pixels `data` of `size`, rows top first, for `upload`."""
        if key not in self._tex:
            self._todo[key] = (tuple(size), data)

    def upload(self) -> None:
        """On the frame thread, the render context current: what was put."""
        todo, self._todo = self._todo, {}
        for key, (size, data) in todo.items():
            tex = self.ctx.texture(size, 4, data)
            tex.repeat_x = tex.repeat_y = False
            self._tex[key] = tex
        while len(self._tex) > self.limit:
            old = next(iter(self._tex))
            self._tex.pop(old).release()

    def release(self) -> None:
        for tex in self._tex.values():
            tex.release()
        self._tex, self._todo = {}, {}
