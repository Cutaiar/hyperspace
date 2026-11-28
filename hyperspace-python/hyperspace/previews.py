"""Effect previews: every effect file put through the test card,
as a still and a short loop, for GRAPH's effect picker.

The picker (`ui_effect_picker`) shows a tile per effect file: what the
effect does to straight lines, a circle and flat colour, at the file's own
defaults. This module makes those pictures, lazily and off the frame's
critical path:

- **A still** per file, at its defaults, the card through it at
  `STILL_T` seconds into its clock.
- **A loop** per file, `LOOP_FRAMES` frames over `LOOP_S` seconds of its
  clock at its default speed, made once and kept: the tile plays it while
  hovered. It is a cut of the effect's clock, not a seamless cycle (an
  effect's motion has no period in general), so it jumps back at its end.
- **Lazily**: nothing is made until the picker asks (`want`, each frame it
  is open); the renderer makes at most `PASSES_PER_FRAME` passes a frame at
  its end (`make`, from `Renderer._for_the_panel`, where the thumbnails are
  made), stills first. A closed picker costs nothing.
- **Invalidated** when an effect's file changes: the cache reads the show's
  own `FxState.files` (which the chain's hot reload keeps current,
  ENGINEERING §15), and a file whose program source (the file, `_lib.glsl`
  and `_common.glsl`) is not what its pictures were made from is made
  again.

Nothing here touches the show: the passes run on a chain and an `FxState`
of this module's own (the show's state holds only the effects its graph
names, `FxState.hold`), with the file's defaults, into textures of its
own. Nothing reaches an output, and nothing is saved: the previews are view
state, made again after a restart or a reload.

**Memory.** Each file's still and loop share one RGBA8 atlas of
`ATLAS_COLS` × `ATLAS_ROWS` cells of `PREVIEW_W` × `PREVIEW_H` (cell 0 the
still, cells 1… the loop): 960 × 540 × 4 = 2.07 MB a file, so the 28 files
on this build (27 effects with the Mandelbrot, and the test card) are 58.1 MB of
textures, all
kept once made (`ATLAS_BYTES`, `bytes_kept`), plus the card, the aux
picture and the work picture at `WORK_W` × `WORK_H` (2.1 MB each, the work
picture 2.8 MB mipmapped).

**The aux.** An effect that reads a second picture (`fx.EffectSpec.aux`:
Blend and Displace on this build) is previewed with a known one wired into
its aux, `AUX_FS`'s soft disc, so its tile shows what it does with one. Each is made once a session and kept: a file that is gone
from the folder has its atlas freed.

**Families.** The picker groups the tiles by family, read from data, never
from a list in code: a file's own ``// @family <name>`` line when it has
one (`fx.EffectSpec.family`, the hook the shader roundup's families will
fill), else the band its ``@order`` sits in (`ORDER_FAMILIES`, one table).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import moderngl

from .fx import FX_DIR, FxChain, FxState, clock_rate
from .glsl import QUAD_VS

CARD_EFFECT = "testcard"        # the effect file that draws the card (shaders/fx/testcard.glsl)

# a tile's picture, px (16:9, the stage's aspect; a thumbnail's long side,
# `outputs.THUMB_PX`)
PREVIEW_W, PREVIEW_H = 192, 108
# the loop: this many seconds of the effect's clock at its default speed …
LOOP_S = 2.0
# … in this many frames (12 a second)
LOOP_FRAMES = 24
# the still: the card through the effect this far into its clock (an
# effect at phase 0 can be the plain card: a shake, a wave at rest)
STILL_T = 0.6
# one atlas a file: the still in cell 0, the loop in cells 1 … LOOP_FRAMES
ATLAS_COLS, ATLAS_ROWS = 5, 5
ATLAS_W, ATLAS_H = ATLAS_COLS * PREVIEW_W, ATLAS_ROWS * PREVIEW_H
ATLAS_BYTES = ATLAS_W * ATLAS_H * 4
# passes made at a frame's end at most (the card's own counts as one; a
# cell is one: the effect at the work size, shrunk into its cell)
PASSES_PER_FRAME = 3
# every pass is made at this size, told it truly (`u_res`), and shrunk into
# its cell through mipmaps: an effect that reads its neighbours by the
# pixel (edges, a blur, a glint's halo) sees pixels, and a knob in px (a
# cell, a split) is twice what it is against a 1080p frame — close to the
# stage, where a smaller picture told it was bigger read between its pixels
# (the edges drew nothing). The card is drawn at it too
WORK_W, WORK_H = 960, 540

# the families by `@order` band (`@order` draws nothing; it is a
# stack position, so it already groups the files by what they do).
# DEBT: family-from-order-band
ORDER_FAMILIES: tuple[tuple[int, str], ...] = (
    (10, "generators"),         # 0–9: draw a picture of their own (plasma, the test card)
    (30, "distort"),            # 10–29: move the picture (warp, wave, kaleidoscope …)
    (50, "split"),              # 30–49: split it (double vision, deconverge, prism)
    (80, "glow and texture"),   # 50–79: bloom, glimmer, edges, fractals, oil slick
    (100, "colour"),            # 80–99: trip colour, hue cycle, grain, fade, palette
)
FAMILY_ORDER = tuple(name for _, name in ORDER_FAMILIES)
OTHER = "other"


def family_of(spec) -> str:
    """The family effect file `spec` is grouped under: its `@family`, else
    its `@order` band's (`ORDER_FAMILIES`)."""
    own = (getattr(spec, "family", "") or "").strip().lower()
    if own:
        return own
    order = int(getattr(spec, "order", 50))
    return next((name for top, name in ORDER_FAMILIES if order < top), OTHER)


def matches(spec, query: str) -> bool:
    """Does effect file `spec` answer the search `query`: every word of it
    found in the file's label, its tip, its name or its family (any case)."""
    words = query.lower().split()
    if not words:
        return True
    text = " ".join((getattr(spec, "label", ""), getattr(spec, "tip", ""),
                     getattr(spec, "name", ""), family_of(spec))).lower()
    return all(w in text for w in words)


def families(specs: Iterable[Any], query: str = "") -> list[tuple[str, list[Any]]]:
    """The picker's groups: (family, its files) for the files answering
    `query`, the families in `FAMILY_ORDER` then any others by name, the
    files in each by `@order` then label. An empty family is left out."""
    out: dict[str, list[Any]] = {}
    for s in specs:
        if matches(s, query):
            out.setdefault(family_of(s), []).append(s)
    rank = {f: i for i, f in enumerate(FAMILY_ORDER)}
    keys = sorted(out, key=lambda f: (rank.get(f, len(rank)), f))
    return [(f, sorted(out[f], key=lambda s: (s.order, s.label.lower()))) for f in keys]


def preview_values(spec) -> dict[str, Any]:
    """An effect file's values for its preview: on, its defaults — its
    `@mix` unless that is 0 (a pass that starts as a no-op would show the
    plain card: it is shown at full mix), its speed and blend, every knob
    at its default."""
    v: dict[str, Any] = {"on": True, "mix": float(spec.mix) if spec.mix > 0 else 1.0,
                         "speed": float(spec.speed), "blend": int(spec.blend)}
    for p in spec.params:
        v[p.key] = round(p.default) if p.integer else float(p.default)
    return v


def card_values(spec) -> dict[str, Any]:
    """The test card file's values for the card the previews are made over:
    its defaults, its Line widened by the work size over a tile's, so Line
    is a line's width in a tile's pixels, as it is on a thumbnail
    (`Renderer.card`) — a 1.5 px line of a 960 px card would be lost in a
    192 px tile."""
    v = preview_values(spec)
    if "line" in v:
        v["line"] = float(v["line"]) * WORK_H / PREVIEW_H
    return v


SHRINK = ""     # `FxChain.run_one` of a name no file has copies its picture: the shrink

# the second picture wired into the aux of an effect that reads one
# (`fx.EffectSpec.aux`: Blend, Displace), so its preview shows what it does
# with one: a soft disc, white at its centre fading to black at its rim and
# clear outside it (premultiplied), warm so a blend's modes read against the
# card's greys — Displace bulges the grid by its brightness, Blend lays it on
AUX_RADIUS = 0.42               # the disc's radius, in frame heights
AUX_TINT = (1.0, 0.62, 0.25)    # its colour at the centre
AUX_FS = """
#version 330
in vec2 v_uv;
out vec4 f_color;
uniform vec2 u_res;
uniform float u_radius;
uniform vec3 u_tint;
void main() {
    vec2 p = (v_uv - 0.5) * vec2(u_res.x / u_res.y, 1.0);
    float r = length(p) / u_radius;
    float a = 1.0 - smoothstep(0.97, 1.0, r);          // a hard rim, eased over a pixel
    float lum = 1.0 - smoothstep(0.0, 1.0, r);          // bright at the centre, dark at the rim
    f_color = vec4(mix(vec3(0.0), u_tint, lum) * a, a);
}
"""


def cell_rect(k: int) -> tuple[int, int, int, int]:
    """Cell `k`'s viewport in its atlas (x, y, w, h; GL's, y up)."""
    return (k % ATLAS_COLS) * PREVIEW_W, (k // ATLAS_COLS) * PREVIEW_H, PREVIEW_W, PREVIEW_H


def cell_uv(k: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """Cell `k`'s corners for imgui (`add_image`'s uv0, uv1): top left then
    bottom right, flipped, as GL's rows run up."""
    x, y, w, h = cell_rect(k)
    return (x / ATLAS_W, (y + h) / ATLAS_H), ((x + w) / ATLAS_W, y / ATLAS_H)


def loop_t(k: int) -> float:
    """The clock time of loop frame `k` (0 …)."""
    return k * LOOP_S / LOOP_FRAMES


class EffectPreviews:
    """The previews of every effect file, on the render context.

    The page's side (any context; makes no GL object): `want` each frame
    the picker is open, `picture` to draw a tile. The renderer's side (its
    own context current): `make` at its frame's end, `release`.

    `made[name]` is the cells drawn for file `name` since its program last
    changed; `passes` the passes the last `make` ran (at most `budget`)."""

    def __init__(self, show: FxState | None = None, ctx: moderngl.Context | None = None,
                 budget: int = PASSES_PER_FRAME):
        self.show = show                        # the show's FxState: the files, kept current
        self.ctx = ctx
        self.budget = budget
        self.stills: set[str] = set()           # the files the page wants a still of
        self.loops: list[str] = []              # … and a loop of, first first
        self.atlas: dict[str, tuple[moderngl.Texture, moderngl.Framebuffer]] = {}
        self.made: dict[str, set[int]] = {}
        self.key: dict[str, tuple] = {}         # file → what its cells' program was built from
        self.passes = 0
        self.error = ""
        self._own: FxState | None = None        # this module's state and chain (made on first use)
        self._chain: FxChain | None = None
        self._card: tuple[moderngl.Texture, moderngl.Framebuffer] | None = None
        self._card_key: tuple | None = None
        self._blank: moderngl.Texture | None = None     # what the card is painted over
        self._work: tuple[moderngl.Texture, moderngl.Framebuffer] | None = None
        self._aux: tuple[moderngl.Texture, moderngl.Framebuffer] | None = None

    # ---- the page's side

    def want(self, stills: Iterable[str], loop: str | None = None) -> None:
        """The picker shows these files' tiles this frame, and plays `loop`'s."""
        self.stills.update(stills)
        if loop is not None and loop not in self.loops:
            self.loops.append(loop)

    def picture(self, name: str, t: float | None = None):
        """What file `name`'s tile shows: (texture, uv0, uv1) — the loop's
        frame at time `t` (s, any clock) when `t` is given and the loop is
        whole, else the still; None before either is made."""
        got = self.atlas.get(name)
        cells = self.made.get(name, ())
        if got is None or not cells:
            return None
        if t is not None and self.looped(name):
            k = 1 + int((t % LOOP_S) / LOOP_S * LOOP_FRAMES) % LOOP_FRAMES
        elif 0 in cells:
            k = 0
        else:
            return None
        return (got[0], *cell_uv(k))

    def looped(self, name: str) -> bool:
        """Is file `name`'s loop whole?"""
        return len(self.made.get(name, ())) > LOOP_FRAMES

    def failed(self, name: str) -> str:
        """Why file `name` shows the plain card: its parse or compile
        error, "" when it runs."""
        if self._chain is not None and self._own is not None and name in self._own.specs:
            return self._chain.error(name)
        return (getattr(self.show, "errors", None) or {}).get(name, "")

    @property
    def bytes_kept(self) -> int:
        """The textures' bytes: every atlas kept and the card."""
        work = WORK_W * WORK_H * 4
        return (len(self.atlas) * ATLAS_BYTES + (work if self._card is not None else 0)
                + (work if self._aux is not None else 0)
                + (work * 4 // 3 if self._work is not None else 0))

    # ---- the renderer's side

    def make(self) -> int:
        """At a frame's end, the render context current: at most `budget`
        passes of what the page wanted since the last call — the card when
        it changed, then the stills, then the loops — and the wish cleared.
        Returns the passes run. Never raises (a failure is `error`)."""
        stills, loops = self.stills, self.loops
        self.stills, self.loops = set(), []
        self.passes = 0
        if not stills and not loops:
            return 0
        try:
            own, chain, ctx = self._sync(stills | set(loops))
            todo = [(n, 0) for n in sorted(stills | set(loops), key=lambda n: n not in loops)]
            todo += [(n, k) for n in loops for k in range(1, LOOP_FRAMES + 1)]
            for name, k in todo:
                if self.passes >= self.budget:
                    break
                if name not in own.specs or k in self.made.get(name, ()):
                    continue
                card = self._card_ready(own, chain, ctx)
                if card is None or self.passes >= self.budget:
                    break
                self._pass(own, chain, ctx, card, name, k)
        except Exception as e:  # noqa: BLE001 — a preview must not take the frame down
            self.error = f"{type(e).__name__}: {e}"[:160]
        return self.passes

    def release(self) -> None:
        """Every GL object this cache made."""
        for tex, fbo in self.atlas.values():
            fbo.release()
            tex.release()
        self.atlas.clear()
        self.made.clear()
        self.key.clear()
        if self._card is not None:
            self._card[1].release()
            self._card[0].release()
            self._card = None
        if self._blank is not None:
            self._blank.release()
            self._blank = None
        for got in (self._work, self._aux):
            if got is not None:
                got[1].release()
                got[0].release()
        self._work = self._aux = None
        if self._chain is not None:
            self._chain.release()
            self._chain = None

    # ---- inside

    def _sync(self, names: set[str]) -> tuple[FxState, FxChain, moderngl.Context]:
        """This cache's own state made the show's files as they are now
        (the show's chain polls the folder): a file whose program changed
        has its cells forgotten, a file gone its atlas released. Returns
        (its state, its chain, the context)."""
        ctx = self.ctx
        if ctx is None:
            raise RuntimeError("no GL context")
        show = self.show
        files = dict(getattr(show, "files", None) or getattr(show, "specs", None) or {})
        if self._own is None:
            self._own = FxState(getattr(show, "dir", None) or FX_DIR)
        own = self._own
        own.lib = getattr(show, "lib", own.lib)
        own.common = getattr(show, "common", own.common)
        own.files = files
        own.held = None
        own.specs = {n: s for n, s in files.items() if "." not in n}
        for n, s in own.specs.items():
            if n not in own.values:
                own._adopt(s)
        chain = self._chain
        if chain is None:
            chain = self._chain = FxChain(ctx, own)
        for name in list(self.atlas):
            if name not in own.specs:
                tex, fbo = self.atlas.pop(name)
                fbo.release()
                tex.release()
                self.made.pop(name, None)
                self.key.pop(name, None)
        for name in names | {CARD_EFFECT}:
            spec = own.specs.get(name)
            if spec is None:
                continue
            # (what its program is built from; the same string objects frame to
            # frame until a reload, so the compare is by identity, no text built)
            src = (spec.source, own.lib, own.common, tuple(spec.clocks))
            if self.key.get(name) != src:
                self.key[name] = src
                self.made[name] = set()
                own._adopt(spec)
                if name == CARD_EFFECT:
                    self._card_key = None
        return own, chain, ctx

    def _card_ready(self, own: FxState, chain: FxChain,
                    ctx: moderngl.Context) -> moderngl.Texture | None:
        """The test card at the work size, drawn now if it is not (one pass
        of the budget): the `testcard` file's picture at its defaults, its
        lines widened for a tile (`card_values`). A mid grey when there is
        no test card file. The card's texture, or None when the budget is
        spent."""
        if self._card is None:
            tex = ctx.texture((WORK_W, WORK_H), 4)
            tex.repeat_x = tex.repeat_y = False
            self._card = (tex, ctx.framebuffer(color_attachments=[tex]))
            self._card_key = None
        spec = own.specs.get(CARD_EFFECT)
        key = self.key.get(CARD_EFFECT, ()) if spec is not None else ("grey",)
        tex, fbo = self._card
        if self._card_key == key:
            return tex
        if self.passes >= self.budget:
            return None
        if spec is None:
            fbo.clear(0.5, 0.5, 0.5, 1.0)
        else:
            own.values[CARD_EFFECT] = card_values(spec)
            self._at(own, spec, CARD_EFFECT, 0.0)
            blank = self._blank
            if blank is None:
                blank = self._blank = ctx.texture((1, 1), 4, bytes(4))
            chain.run_one(CARD_EFFECT, blank, fbo, 0.0, opaque=1, res=(WORK_W, WORK_H))
        self._card_key = key
        self.passes += 1
        return tex

    def _aux_picture(self, ctx: moderngl.Context) -> moderngl.Texture:
        """The aux picture (`AUX_FS`) at the work size, drawn on first use."""
        got = self._aux
        if got is None:
            tex = ctx.texture((WORK_W, WORK_H), 4)
            tex.repeat_x = tex.repeat_y = False
            fbo = ctx.framebuffer(color_attachments=[tex])
            prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=AUX_FS)
            for key, value in (("u_res", (float(WORK_W), float(WORK_H))),
                               ("u_radius", AUX_RADIUS), ("u_tint", AUX_TINT)):
                uniform = prog[key]
                if isinstance(uniform, moderngl.Uniform):
                    uniform.value = value
            vao = ctx.vertex_array(prog, [])
            fbo.use()
            fbo.clear(0.0, 0.0, 0.0, 0.0)
            ctx.disable(moderngl.BLEND)
            try:
                vao.render(moderngl.TRIANGLES, vertices=3)
            finally:
                ctx.enable(moderngl.BLEND)
                vao.release()
                prog.release()
            got = self._aux = (tex, fbo)
        return got[0]

    @staticmethod
    def _at(own: FxState, spec, name: str, t: float) -> None:
        """Effect `name`'s clocks at `t` s of its default speed: its phase
        and each `@clock`'s, as `FxState.advance` would have them from 0,
        and the state's last time `t`, so the pass moves nothing."""
        v = own.values[name]
        speed = float(v["speed"])
        own.phase[name] = t * speed
        ph: dict[str, float] = {}
        for c in spec.clocks:
            x = t * speed * clock_rate(c, v)
            ph[c.uniform] = x % c.period if c.period else x
        own._clocks()[name] = ph
        own._t_last = t

    def _pass(self, own: FxState, chain: FxChain, ctx: moderngl.Context,
              card: moderngl.Texture, name: str, k: int) -> None:
        """Cell `k` of file `name`'s atlas: the card through the effect at
        its defaults, `STILL_T` (the still, cell 0) or `loop_t(k - 1)` s
        into its clock, made at the work size and shrunk into the cell. The
        test card's own tile is the card as the others see it."""
        got = self.atlas.get(name)
        if got is None:
            tex = ctx.texture((ATLAS_W, ATLAS_H), 4)
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            tex.repeat_x = tex.repeat_y = False
            got = self.atlas[name] = (tex, ctx.framebuffer(color_attachments=[tex]))
            got[1].clear(0.0, 0.0, 0.0, 1.0)
        work_fb = self._work
        if work_fb is None:
            w = ctx.texture((WORK_W, WORK_H), 4)
            w.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            w.repeat_x = w.repeat_y = False
            work_fb = self._work = (w, ctx.framebuffer(color_attachments=[w]))
        spec = own.specs[name]
        own.values[name] = card_values(spec) if name == CARD_EFFECT else preview_values(spec)
        t = STILL_T if k == 0 else loop_t(k - 1)
        self._at(own, spec, name, t)
        work, wfbo = work_fb
        aux = self._aux_picture(ctx) if getattr(spec, "aux", False) else None
        chain.run_one(name, card, wfbo, t, opaque=1, aux=aux)
        work.build_mipmaps()
        fbo = got[1]
        fbo.viewport = cell_rect(k)
        chain.run_one(SHRINK, work, fbo, t, opaque=1)     # (no such effect: a copy)
        fbo.viewport = (0, 0, ATLAS_W, ATLAS_H)
        self.made.setdefault(name, set()).add(k)
        self.passes += 1
