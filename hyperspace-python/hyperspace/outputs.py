"""The render outputs, as the renderer sees them (plan 21 WP1).

One frame is drawn per loop; each output — a window on its own screen,
or an offscreen target standing in for one — shows what the preset's
graph wires into it (plan 35: its own wires; plan 36 T1, else All
outputs' by the rig's bus cable into that port, `graph.window_ports`) through
its window's two mutes, the picture and the hands, with its mirror and
its own dim. A mute is the window's, never the preset's structure: off,
the window ignores the picture (or the hands and the guide) wired into
it and shows its ground, the hands over — it builds nothing, so it never
rebuilds the graph (row 374). "Hands through the effects" is wiring in
the preset, not a switch (plan 35 O). This module is the pure half of
that: what a window's mutes are (`Switches`), where the frame sits in an
output of another shape (`fit`), and the one-frame record the renderer
fills in for an output (`View`, with `Handoff` for an output in another
window's context). `Renderer.draw_outputs` (render.py) does the
drawing. WP3 adds the rig's side: `Slot`, one listed output for the run
(app.py fills it from `[[output.screens]]`), and `Presenter`, which shows
a `Handoff` in another window's context. Plan 32 T9 adds `Offscreen`, a
texture-backed target on the renderer's context: a publish-only output
(`window = false`) is drawn into one, and a published output with a
window has one as its `tap`, the copy its publishers are handed.

Render stack (ARCHITECTURE §3): it only reads. This module imports
moderngl and glsl at most — never app, ui or params — and the
`output.N.*` params (WP4) write `Switches`, which the renderer reads.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import moderngl

from .glsl import QUAD_VS

MAX_OUTPUTS = 4


@dataclass
class Switches:
    """One window's mutes and its own look — what the output.N.* params
    write (WP4). Plan 35 O (row 374): `scene` is the picture mute (off: the
    window ignores the picture wired into it), `hands` the hands mute (off:
    it ignores the hands and the guide); read by its `Output` each frame,
    never a rebuild. The through switch is gone: "hands through the
    effects" is the preset's wiring."""

    scene: bool = True         # the picture (its label "picture"; the id is kept)
    hands: bool = True
    dim: float = 1.0           # this output's own dim, times the master's
    # plan 23 WP1: this output's picture mirrored as its last step, inside
    # the fit rect — the frame, the hands laid after and the readout alike,
    # so a Pepper's Ghost glass's own mirror is undone (the dim covers the
    # whole rect and needs none). Off, the output is bit-identical
    flip_x: bool = False       # left-right
    flip_y: bool = False       # top-bottom


def capped(size: tuple[int, int], cap: tuple[int, int] | None) -> tuple[int, int]:
    """The frame's size: output 1's framebuffer `size`, shrunk with its
    aspect kept until it fits inside `cap` (w, h), whichever side binds;
    never grown; None is no cap. A 2× HiDPI screen that looks 1920×1080
    is a 3840×2160 framebuffer — under a 1080p cap the scene, the
    look-back, the dream and every effect run at 1920×1080 and each output
    shows the frame scaled (`fit`, linear)."""
    w, h = max(int(size[0]), 1), max(int(size[1]), 1)
    if cap is None:
        return w, h
    k = min(cap[0] / w, cap[1] / h, 1.0)
    return max(1, round(w * k)), max(1, round(h * k))


def fit(src: tuple[int, int], dst: tuple[int, int]) -> tuple[int, int, int, int]:
    """The rect (x, y, w, h) in `dst` that shows `src` whole, centred, its
    aspect kept (fork F5: letterbox). Equal sizes give (0, 0, w, h); a
    zero-sized side gives the whole of `dst`."""
    sw, sh = int(src[0]), int(src[1])
    dw, dh = int(dst[0]), int(dst[1])
    if (sw, sh) == (dw, dh) or sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
        return 0, 0, max(dw, 0), max(dh, 0)
    scale = min(dw / sw, dh / sh)
    w = min(dw, max(1, round(sw * scale)))
    h = min(dh, max(1, round(sh * scale)))
    return (dw - w) // 2, (dh - h) // 2, w, h


@dataclass
class Handoff:
    """What `Renderer.draw_outputs` leaves for an output it cannot draw
    itself — one in another window's context (`View.presenter`, WP3). Every
    texture belongs to the renderer's context (a share group shares
    textures, not framebuffers or vertex arrays); WP3's presenter wraps
    each GL name with `ctx.external_texture` and, in its own context, in
    this order:

    1. clears its framebuffer to (0, 0, 0, `bg_alpha`);
    2. draws `frame` (RGBA8 or half float, below; `frame_size`, premultiplied, LINEAR) into
       `rect` (in its framebuffer, the view's `viewport` included) — 1:1 when `rect`'s size is `frame_size`, else scaled; with
       `bg_alpha` 1 it writes alpha 1. `frame` None: the ground only;
    3. lays `hands` (the hands' layer, premultiplied, frame-sized) over the
       same `rect` at `alpha`: colour ONE / ONE_MINUS_SRC_ALPHA, and alpha
       ZERO / ONE on an opaque ground (`bg_alpha` 1) — `Ghost.composite`'s
       blend; with `blend` "add" (plan 26 A3) colour ONE / ONE instead, and
       alpha ONE / ONE_MINUS_SRC_ALPHA on a see-through ground. None: no
       hands after the effects on this output;
    4. lays `readout` (the guide and the tethers' labels when they are a
       layer of their own, WP2 — on every output that shows the hands,
       over or through) into `rect` the same way. None: nothing;
    5. multiplies the whole framebuffer by `factor` when it is under 1
       (`Renderer.dim_pass`'s blend: colour only on an opaque ground,
       colour and alpha otherwise).

    The textures are valid until the next `draw_outputs`; the renderer's
    context must be flushed (`glFlush`) before the presenter's samples
    them (plan §1: otherwise it sees last frame's).

    Plan 30 D1: `frame` or `hands` may be a half-float texture of the
    effects' pool rather than RGBA8 — an output's frame through an effect
    placed into it, the hands' layer through one placed after the hands.
    The presenter wraps every name as "f1" (`Presenter._ext`); that
    declares the wrapper's dtype only, and a shader samples the texture
    by its name whatever its real format, so the picture is right."""

    frame: moderngl.Texture | None
    frame_size: tuple[int, int]
    rect: tuple[int, int, int, int]
    hands: moderngl.Texture | None = None
    readout: moderngl.Texture | None = None
    alpha: float = 1.0
    factor: float = 1.0
    bg_alpha: float = 1.0
    flip: tuple[bool, bool] = (False, False)   # plan 23 WP1: steps 2–4 mirrored in `rect`
    blend: str = "over"                        # plan 26 A3: step 3's blend, "over" or "add"

    @staticmethod
    def name(tex: moderngl.Texture | None) -> int | None:
        """A texture's GL name for `ctx.external_texture`, or None."""
        return None if tex is None else int(tex.glo)


@dataclass
class View:
    """One output, for one frame. `target` is a framebuffer on the
    renderer's context (the first output's window, or an offscreen
    stand-in); `presenter` an output in another window's context (WP3),
    which `draw_outputs` leaves a `handoff` for. `viewport` is the rect of
    `target` (or of the presenter's framebuffer) to draw (None: (0, 0) and
    `size`).

    `bg_alpha` is this output's own ground: its bars, its clear when it
    shows no pipeline, and whether its composites and dim keep alpha. The
    frame itself — the scene's clear, the effect chain — is drawn on
    `Renderer.bg_alpha`, once for every output: overlay is the first
    output's only (plan 21 §4), so an output's ground can make the frame
    opaque on it (alpha forced to 1) but never see-through."""

    switches: Switches
    size: tuple[int, int]                       # its framebuffer, px
    target: moderngl.Framebuffer | None = None  # on the renderer's context
    presenter: Any = None                       # WP3: another window's context
    bg_alpha: float = 1.0                       # this output's ground
    error: str = ""                             # set by draw_outputs, never raised
    viewport: tuple[int, int, int, int] | None = None
    handoff: Handoff | None = None              # set by draw_outputs for a presenter
    exc: BaseException | None = field(default=None, repr=False)   # what set `error`
    # plan 32 T9: this output's publishers (media/publish.py), each handed
    # its picture once the frame is drawn — `target`'s own texture when it
    # is an `Offscreen`'s, else a copy in `tap` (an `Offscreen`): a
    # window's framebuffer resolved into it, a presenter's hand-off
    # presented into it on the renderer's context
    publish: list = field(default_factory=list)
    tap: Any = None

    @property
    def rect(self) -> tuple[int, int, int, int]:
        if self.viewport is not None:
            return tuple(int(v) for v in self.viewport)
        return 0, 0, int(self.size[0]), int(self.size[1])


# ---------------------------------------------------------------- WP3: the list

@dataclass
class Slot:
    """One output the config lists (`[[output.screens]]`, or the one
    `[output]` window when there is no list), for the whole run: its place
    `n` (1-based — `output.2.*` is always the second entry, opened or
    not), its name, its switches (the config's launch values; the
    output.N.* params write them, WP4), and its window — or, for a later
    output whose screen is not connected, `missing`, the reason it was not
    opened (fork F9). `output` is its `overlay.Output`, `presenter` its
    `Presenter` (outputs after the first), `error` the last present that
    raised ("" once one succeeds), `size` its framebuffer at the last frame.
    The app fills it; the renderer never sees it, only the `View` built
    from it each frame.

    Plan 32 T9: `syphon` / `ndi` are the names it is published under ("" =
    not), `publishers` the publishers made for them, `window` false for a
    publish-only output — no window ever, drawn into `offscreen`; a
    published output with a window copies its picture into `tap`."""

    n: int
    name: str = ""
    switches: Switches = field(default_factory=Switches)
    monitor: int = -1
    fullscreen: bool = False
    win: Any = None
    missing: str = ""
    output: Any = None
    presenter: Any = None
    error: str = ""
    size: tuple[int, int] = (0, 0)
    window: bool = True
    syphon: str = ""
    ndi: str = ""
    publishers: list = field(default_factory=list)
    offscreen: Any = None
    tap: Any = None

    @property
    def label(self) -> str:
        """"output 2 (projector)", or "output 2" with no name."""
        return f"output {self.n} ({self.name})" if self.name else f"output {self.n}"

    @property
    def opened(self) -> bool:
        """It has a window (a publish-only output never has)."""
        return self.win is not None

    @property
    def publish_only(self) -> bool:
        return not self.window

    @property
    def drawn(self) -> bool:
        """It gets a picture each frame: a window, or publish-only with
        something to publish (`missing` says why one is not)."""
        return self.opened or (self.publish_only and not self.missing)


class Offscreen:
    """An RGBA8 texture and its framebuffer on the renderer's context,
    made at the size `fit` asks for and made again when that changes
    (plan 32 T9): a publish-only output's target, a published window's
    tap. `tex` is what a publisher is handed."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.tex: moderngl.Texture | None = None
        self.fbo: moderngl.Framebuffer | None = None

    @property
    def size(self) -> tuple[int, int] | None:
        return None if self.tex is None else tuple(self.tex.size)

    def fit(self, size: tuple[int, int]) -> moderngl.Framebuffer:
        size = (max(int(size[0]), 1), max(int(size[1]), 1))
        if self.fbo is None or self.size != size:
            self.release()
            tex = self.ctx.texture(size, 4)
            try:
                self.fbo = self.ctx.framebuffer(color_attachments=[tex])
            except Exception:
                tex.release()
                raise
            self.tex = tex
        return self.fbo

    def release(self) -> None:
        """Free both; a bound framebuffer is never released (moderngl
        rebinds it after the next one is made: GL_INVALID_OPERATION), so
        the default framebuffer is bound first when it is this one."""
        fbo, tex, self.fbo, self.tex = self.fbo, self.tex, None, None
        if fbo is not None:
            try:
                if self.ctx.fbo is fbo:
                    self.ctx.screen.use()
                fbo.release()
            except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                pass
        if tex is not None:
            try:
                tex.release()
            except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                pass



class Preview:
    """Output 1's picture for the control window (2026-10-26: the GRAPH
    page's backdrop): a publisher in shape — `_draw_render` adds it to
    output 1's view, with this tap when the window has none of its own, on
    a frame after the page `want`ed it — that keeps the texture it is
    handed. Wanted only while the page draws it, so a closed page costs no
    copy. `tex` is a texture of the render context, which the control
    window's shares; None before the first picture."""

    kind = "preview"
    name = ""
    status = "waiting"
    fps = 0.0
    readback_ms = 0.0

    def __init__(self, ctx: moderngl.Context | None = None):
        self.tap = Offscreen(ctx) if ctx is not None else None
        self.tex: Any = None
        self.wanted = False

    def want(self) -> None:
        """The page draws the picture this frame: copy it next frame."""
        self.wanted = True

    def take(self) -> bool:
        """Was it wanted since the last frame? (and forget the wish)"""
        wanted, self.wanted = self.wanted, False
        return wanted

    def publish(self, tex, t: float) -> None:
        self.tex, self.status = tex, "sending"

    def fail(self, why: str) -> None:
        self.tex, self.status = None, f"error: {why}"

    def close(self) -> None:
        self.tex = None
        if self.tap is not None:
            self.tap.release()

# ---------------------------------------------------------------- plan 37 C1: the thumbnails

# the long side of a node's thumbnail on GRAPH, in texels (P1)
THUMB_PX = 192
# a thumbnail not wanted for this long is dropped (its texture freed)
THUMB_DROP_S = 1.0
# a node that made nothing this long shows black (dimmed before that)
THUMB_BLACK_S = 1.0
# the downsample pass (plan 37 C1): 4×4 bilinear taps over the footprint
# of one thumbnail texel — each tap averages 2×2 source texels, so a
# 1920-wide picture's ten texels a thumbnail texel are read eight across,
# in one draw, with no mipmap built on (and no filter changed on) a
# texture the frame owns. Written opaque: the picture over black, so a
# see-through layer reads on the node as it would on a black window
THUMB_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform vec2 u_step;          // one thumbnail texel, in the source's uv
out vec4 f_color;
void main() {
    vec4 c = vec4(0.0);
    for (int j = 0; j < 4; ++j)
        for (int i = 0; i < 4; ++i)
            c += texture(u_src, v_uv + (vec2(i, j) - 1.5) * 0.25 * u_step);
    f_color = vec4(c.rgb / 16.0, 1.0);
}
"""


def thumb_size(src: tuple[int, int], px: int = THUMB_PX) -> tuple[int, int]:
    """A thumbnail's size for a picture of size `src`: its long side `px`,
    the picture's aspect (never under one texel, never above the source)."""
    w, h = max(int(src[0]), 1), max(int(src[1]), 1)
    k = min(px / max(w, h), 1.0)
    return max(1, round(w * k)), max(1, round(h * k))


class PreviewTextures:
    """The GRAPH page's thumbnails (plan 37 C1, P1): a small texture per
    node name, its long side `THUMB_PX`, the picture's aspect — `Preview`'s
    pattern, one per node. The page `want`s, each frame it draws, the
    names it has on screen (each with how its picture is found:
    `graphview.THUMBS`); the renderer, at the end of its next frame
    (`Renderer._for_the_panel`), `take`s the wish and `put`s each wanted
    node's picture, which one downsample pass (`THUMB_FS`) copies into
    that node's texture, and calls `end_frame`. A name not wanted for
    `THUMB_DROP_S` is dropped and its texture freed, so a node off screen,
    hidden or collapsed off the canvas costs nothing after a second.

    A node wanted that made nothing this frame keeps its last thumbnail:
    `shade(name)` is 1 when it was copied the renderer's last frame, `DIM`
    while it is less than `THUMB_BLACK_S` old, 0 (black) after — a number
    the page multiplies the picture by, never a copy. `count` is the
    copies the last frame made (the SYSTEM line), `kept` the textures
    held. The textures are the render context's, which the control
    window's shares, as `Preview`'s is; with no context (a test, a
    stand-in) `put` keeps only the name and the time."""

    DIM = 0.45

    def __init__(self, ctx: moderngl.Context | None = None, clock=None):
        self.ctx = ctx
        self.clock = clock if clock is not None else time.monotonic
        self.wanted: dict[str, str] = {}
        self.asked: dict[str, float] = {}       # name → when it was last wanted
        self.made: dict[str, float] = {}        # name → when it was last copied
        self.tex: dict[str, Any] = {}           # name → (texture, framebuffer)
        self.sizes: dict[str, tuple[int, int]] = {}   # name → the picture's own size
        self.frame = 0                          # the renderer's frames ended
        self.made_in: dict[str, int] = {}       # name → the frame it was last copied in
        self.count = 0
        self.error = ""
        self._prog = self._vao = self._sampler = None

    # ---- the page's side

    def want(self, ids) -> None:
        """The page draws these nodes this frame: copy each next frame.
        `ids` names → how (a mapping), or names (each "picture")."""
        now = self.clock()
        items = ids.items() if hasattr(ids, "items") else ((i, "picture") for i in ids)
        for name, how in items:
            self.wanted[name] = how
            self.asked[name] = now

    def get(self, name: str):
        """`name`'s thumbnail texture, or None (never copied, or dropped)."""
        got = self.tex.get(name)
        return got[0] if got is not None else None

    def size_of(self, name: str) -> tuple[int, int] | None:
        """The size of the picture `name`'s thumbnail was last copied from."""
        return self.sizes.get(name)

    def shade(self, name: str) -> float:
        """1 copied the last frame; `DIM` while the last copy is under
        `THUMB_BLACK_S` old; 0 after that, or never copied."""
        if self.made_in.get(name) == self.frame and self.frame:
            return 1.0
        at = self.made.get(name)
        if at is None or self.clock() - at >= THUMB_BLACK_S:
            return 0.0
        return self.DIM

    @property
    def kept(self) -> int:
        return len(self.asked)

    # ---- the renderer's side

    def take(self) -> dict[str, str]:
        """What was wanted since the last frame (and forget the wish)."""
        wanted, self.wanted = self.wanted, {}
        return wanted

    def begin_frame(self) -> None:
        """A frame's copies start: none counted yet."""
        self.frame += 1
        self.count = 0

    def put(self, name: str, src) -> bool:
        """`src` (a texture of the render context) copied into `name`'s
        thumbnail by one downsample pass; True when it was. A pass that
        raises leaves the last thumbnail (`error` says why)."""
        try:
            size = tuple(int(v) for v in src.size)
            if self.ctx is not None:
                self._copy(name, src, size)
        except Exception as e:  # noqa: BLE001 — a thumbnail must not take the frame down
            self.error = f"{type(e).__name__}: {e}"[:120]
            return False
        self.sizes[name] = size
        self.made[name] = self.clock()
        self.made_in[name] = self.frame
        self.count += 1
        return True

    def end_frame(self) -> None:
        """Drop every name not wanted for `THUMB_DROP_S` (its texture freed)."""
        now = self.clock()
        for name in [n for n, at in self.asked.items() if now - at >= THUMB_DROP_S]:
            self.drop(name)

    def drop(self, name: str) -> None:
        for d in (self.asked, self.made, self.sizes, self.made_in, self.wanted):
            d.pop(name, None)
        got = self.tex.pop(name, None)
        if got is not None:
            for res in (got[1], got[0]):
                try:
                    res.release()
                except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                    pass

    def close(self) -> None:
        for name in list(self.tex) + list(self.asked):
            self.drop(name)
        for res in (self._vao, self._prog, self._sampler):
            if res is not None:
                try:
                    res.release()
                except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                    pass
        self._prog = self._vao = self._sampler = None

    def _target(self, name: str, size: tuple[int, int]):
        want = thumb_size(size)
        got = self.tex.get(name)
        if got is not None and tuple(got[0].size) == want:
            return got
        if got is not None:
            self.tex.pop(name)
            for res in (got[1], got[0]):
                res.release()
        tex = self.ctx.texture(want, 4)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        try:
            fbo = self.ctx.framebuffer(color_attachments=[tex])
        except Exception:
            tex.release()
            raise
        got = self.tex[name] = (tex, fbo)
        return got

    def _copy(self, name: str, src, size: tuple[int, int]) -> None:
        ctx = self.ctx
        if self._prog is None:
            self._prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=THUMB_FS)
            self._vao = ctx.vertex_array(self._prog, [])
            # a sampler of our own: the source's filter (NEAREST on a
            # texelFetch target) is never changed, and taps blend
            self._sampler = ctx.sampler(filter=(moderngl.LINEAR, moderngl.LINEAR),
                                        repeat_x=False, repeat_y=False)
        tex, fbo = self._target(name, size)
        fbo.use()
        ctx.viewport = (0, 0, *tex.size)
        blend = moderngl.BLEND
        ctx.disable(blend)
        try:
            src.use(location=0)
            self._sampler.use(location=0)
            self._prog["u_src"].value = 0
            self._prog["u_step"].value = (1.0 / tex.size[0], 1.0 / tex.size[1])
            self._vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            self._sampler.clear(location=0)
            ctx.enable(blend)


# a frame texture or a layer into a rect of a presenter's framebuffer:
# 1:1 by texelFetch (the renderer's SHOW_FS) or scaled by the sampler,
# times `u_k` (1 for the frame, ghost.alpha for a layer); on an opaque
# ground the frame writes alpha 1
PRESENT_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform int u_scaled;
uniform ivec2 u_origin;      // the rect's origin (gl_FragCoord is window-relative)
uniform float u_k;
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
    c *= u_k;
    if (u_opaque != 0) c.a = 1.0;
    f_color = c;
}
"""

# the dim: blending only (render.DIM_FS, `Renderer.dim_pass`'s blend)
PRESENT_DIM_FS = """
#version 330
uniform float u_factor;
out vec4 f_color;
void main() { f_color = vec4(0.0, 0.0, 0.0, u_factor); }
"""


class Presenter:
    """One output after the first (plan 21 WP3): a moderngl handle on that
    window's context and its own programs and vertex arrays — a share
    group shares textures and programs, never framebuffers or vertex
    arrays, so the renderer's cannot draw here (§1 row 1).

    `present(handoff, size)` follows `Handoff`'s five steps in this
    context: the ground, the frame into its rect, the hands, the readout,
    the dim. The handoff's textures belong to the renderer's context and
    are wrapped by GL name (`ctx.external_texture`); the caller has flushed
    that context first. Builds nothing until the first `present`, which
    runs with this context current; `on_reload` only marks the programs
    stale (a reload runs in whatever context is current), so the next
    `present` rebuilds them here. Leaves this context's window
    framebuffer bound, a raise included."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._prog = self._vao = self._dim = self._dim_vao = None
        self._ext: dict[tuple[int, tuple[int, int]], moderngl.Texture] = {}
        self._stale = False
        self.presented = 0

    def _build(self) -> None:
        if getattr(self, "_stale", False):
            self._drop()
            self._stale = False
        if self._prog is not None:
            return
        ctx, made = self.ctx, []
        try:
            prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=PRESENT_FS)
            made.append(prog)
            vao = ctx.vertex_array(prog, [])
            made.append(vao)
            dim = ctx.program(vertex_shader=QUAD_VS, fragment_shader=PRESENT_DIM_FS)
            made.append(dim)
            dim_vao = ctx.vertex_array(dim, [])
        except Exception:
            for res in made:
                res.release()
            raise
        self._prog, self._vao, self._dim, self._dim_vao = prog, vao, dim, dim_vao

    def _wrap(self, tex) -> moderngl.Texture:
        """The renderer's texture as this context sees it, by GL name."""
        key = (int(Handoff.name(tex)), tuple(int(v) for v in tex.size))
        have = self._ext.get(key)
        if have is None:
            if len(self._ext) > 16:      # names of textures long gone
                self._ext.clear()
            have = self._ext[key] = self.ctx.external_texture(key[0], key[1], 4, 0, "f1")
        return have

    def present(self, ho: Handoff, size: tuple[int, int], target=None) -> None:
        """Draw `ho` into this window's framebuffer (`target`: another
        framebuffer on this context, for the tests) of `size` px."""
        ctx = self.ctx
        fb = target if target is not None else ctx.screen
        full = (0, 0, int(size[0]), int(size[1]))
        try:
            self._build()
            fb.use()
            ctx.viewport = full
            ctx.clear(0.0, 0.0, 0.0, float(ho.bg_alpha))                         # 1
            opaque = ho.bg_alpha >= 1.0
            prog, vao = self._prog, self._vao
            prog["u_src"].value = 0
            fl = tuple(int(bool(v)) for v in getattr(ho, "flip", (False, False)))
            prog["u_flip"].value = fl                    # steps 2–4 alike; 5 covers it all
            rect = tuple(int(v) for v in ho.rect)
            if ho.frame is not None and rect[2] > 0 and rect[3] > 0:            # 2
                ctx.viewport = rect
                ctx.disable(moderngl.BLEND)
                self._wrap(ho.frame).use(location=0)
                prog["u_scaled"].value = int(tuple(rect[2:]) != tuple(ho.frame_size))
                prog["u_origin"].value = rect[:2]
                prog["u_k"].value = 1.0
                prog["u_opaque"].value = int(opaque)
                vao.render(moderngl.TRIANGLES, vertices=3)
            add = getattr(ho, "blend", "over") == "add"
            for layer, plus in ((ho.hands, add), (ho.readout, False)):          # 3, 4
                if layer is None or rect[2] <= 0 or rect[3] <= 0:
                    continue
                ctx.viewport = rect
                ctx.enable(moderngl.BLEND)
                rgb = moderngl.ONE if plus else moderngl.ONE_MINUS_SRC_ALPHA
                ctx.blend_func = ((moderngl.ONE, rgb, moderngl.ZERO, moderngl.ONE) if opaque else
                                  (moderngl.ONE, rgb, moderngl.ONE,
                                   moderngl.ONE_MINUS_SRC_ALPHA))
                self._wrap(layer).use(location=0)
                prog["u_scaled"].value = 1          # as Ghost.composite samples it
                prog["u_origin"].value = rect[:2]
                prog["u_k"].value = float(ho.alpha)
                prog["u_opaque"].value = 0
                vao.render(moderngl.TRIANGLES, vertices=3)
            factor = min(max(float(ho.factor), 0.0), 1.0)
            if factor < 1.0:                                                    # 5
                ctx.viewport = full
                ctx.enable(moderngl.BLEND)
                ctx.blend_func = (moderngl.ZERO, moderngl.SRC_ALPHA, moderngl.ZERO,
                                  moderngl.ONE if opaque else moderngl.SRC_ALPHA)
                self._dim["u_factor"].value = factor
                self._dim_vao.render(moderngl.TRIANGLES, vertices=3)
            self.presented += 1
        finally:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            fb.use()
            ctx.viewport = full

    def on_reload(self) -> None:
        """Hot reload: rebuild at the next `present`, in this context."""
        self._stale = True

    def _drop(self) -> None:
        for res in (self._dim_vao, self._dim, self._vao, self._prog):
            if res is not None:
                try:
                    res.release()
                except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                    pass
        self._prog = self._vao = self._dim = self._dim_vao = None
        self._ext = {}

    def release(self) -> None:
        """Free the programs and arrays; call with this context current."""
        self._drop()
