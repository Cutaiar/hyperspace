"""The dream's GL half and its values (plan 07 WP6, plan 36 T4) — and the old
look-back's units, which a load still converts.

Plan 90 (H2): the look-back is retired. Its ring, its atlas and its trail pass
(`Lookback`, `POST_FS`) are public parts now — a delay keeping its pictures
(`stack.DelayStack`), read by the Trail and Read effect files — and a saved
look-back opens as them (`graphmigrate.lookbacks`). What stays here until H3:

- `DreamState`, the `dream.*` params' object: the dream node's own knobs and
  the shared `darken`, `contrast` and `res` it still reads (Q26: a migrated
  look-back's parts got copies of those values).
- `Dreamer`, the dream node's GL half: its buffer `D` and the copy path to
  the worker (`LookbackSource`, dream.py). Once a frame while `dream.on` it
  pulls a finished result into `D` and submits its input, downsampled to
  `dream.res` on its short side and read back once; `lay` draws the input
  with `D` over it at `dream.mix`, re-hued, (de)saturated, tinted and graded
  (`DREAM_FS`): ``grade(c) = pow(c, contrast) · (1 − darken)``, coverage the
  graded buffer's own peak brightness, premultiplied over.
- The look-back's per-frame units, read as 60 Hz frames (plan 14 WP6):
  ``dream.decay`` → a fade in seconds, ``dream.every`` → a gap in seconds
  (`migrate_values`, `migrate_row`) — `loadable.echo_seconds` runs them on
  an old file before the ladder, whose last step makes the look-back public
  parts.

The dream slot (WP6b):

    LookbackSource.submit(frame, frame_index)   after every submit, the
        input as a (h, w, 4) uint8 array, rows bottom-up as GL reads them.
        The array is the source's own if it has ``buffer(shape)`` (a torch
        host alias: glReadPixels lands straight in the tensor's memory),
        else a numpy array this module keeps.
    LookbackSource.latest() → (pixels, frame_index) | None   the newest
        finished result, same layout, RGB premultiplied by the content mask;
        the frame index says which submit it answers, and a result already
        shown is skipped.

Ordering rule: the read waits for the render (glReadPixels is a sync point,
~0.4 ms); the write is a plain texture upload before the lay. A result lands
a frame or two after its submit by design.
"""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import moderngl
import numpy as np

from . import writes
from .glsl import FALLBACK, QUAD_VS, common, gl_error

RES = [128, 192, 256, 384]              # dream.res: the echo's short side, px
# dream.layer's choices in their stored order: a loadable patch saves the index, so
# a new layer is appended, never inserted. The menu's order is LAYER_INFO's.
LAYERS = ["conv2_2", "conv3_3", "conv4_3", "inception3b", "inception4c", "inception4e",
          "conv1_1", "conv1_2", "conv2_1", "conv3_1", "conv3_2", "conv4_1", "conv4_2",
          "conv5_1", "conv5_2", "conv5_3",
          "conv1", "conv2", "conv3", "inception3a", "inception4a", "inception4b",
          "inception4d", "inception5a", "inception5b"]
# name → (net, short, long), in the menu's order: by net, shallow → deep.
# The layer menu, its hovers and the docs read these words. They are from
# two contact sheets (docs/plans/assets/20-fx-dream-looks/dream-layers*.jpg,
# tools/dream_layer_sheet.py: one to two seconds of dreaming at the
# defaults, 256 px, on the owner's laptop over MPS) and from depth; "slower" is over 25 ms
# a frame (two passes) there, where conv3_3 takes about 19.
LAYER_INFO: dict[str, tuple[str, str, str]] = {
    "conv1_1": ("VGG16", "flat colour, fine dots",
        ("The first layer: colours pushed to a few flat, bold ones under a fine "
         "mesh of dots. Almost no shapes of its own.")),
    "conv1_2": ("VGG16", "colour split, fine dots",
        ("Colours split into a fine red-and-blue dot mesh along every edge. Still "
         "no shapes of its own.")),
    "conv2_1": ("VGG16", "fine hatching",
        "Fine hatching and moiré, muted colour: the picture looks engraved."),
    "conv2_2": ("VGG16", "dense neon cells",
        ("A dense mesh of small neon cells, green and magenta, that fills whatever "
         "is lit. Strong and busy.")),
    "conv3_1": ("VGG16", "woven stripes",
        "Short stripes woven at angles, a fine textile texture."),
    "conv3_2": ("VGG16", "fine maze",
        "A fine maze of little loops and stripes; the start of the classic swirl."),
    "conv3_3": ("VGG16", "small loops, the classic",
        ("Small loops, rings and swirls woven together: the classic Deep Dream "
         "texture, and the default.")),
    "conv4_1": ("VGG16", "soft rings",
        "Soft rings and dots, spaced out over a smoother ground."),
    "conv4_2": ("VGG16", "eyelets and scales",
        "Eye-like rings and scale-like cells, larger than conv3's."),
    "conv4_3": ("VGG16", "blots and eyes, slower",
        ("Bigger blots with eye-like rings where lines meet. Slower: about 27 ms a "
         "frame at 256 px.")),
    "conv5_1": ("VGG16", "large swirls, slower",
        ("The deepest VGG layers: large soft swirls and blobs, detail gathered at "
         "the corners. Slower: about 28 ms a frame.")),
    "conv5_2": ("VGG16", "large swirls, slower",
        ("Large soft swirls and blobs, like conv5_1, a little looser. Slower: "
         "about 30 ms a frame.")),
    "conv5_3": ("VGG16", "largest blobs, slower",
        ("VGG's last layer: the largest blobs and swirls; by its depth, the most "
         "object-like VGG gets. Slower: about 30 ms a frame.")),
    "conv1": ("GoogLeNet", "coarse colour dots",
        "GoogLeNet's first layer: a coarse grid of bold coloured dots."),
    "conv2": ("GoogLeNet", "rainbow ripples",
        "Fine wavy lines in rainbow fringes, like moiré."),
    "conv3": ("GoogLeNet", "specks and dashes",
        "Small specks and dashes along the edges, light on the ground."),
    "inception3a": ("GoogLeNet", "ripples and scales",
        "Ripples and scale-like waves, the first of the inception blocks."),
    "inception3b": ("GoogLeNet", "rings and pits",
        "Small rings with dark pits in them, eyelets over everything."),
    "inception4a": ("GoogLeNet", "rings and curls",
        "Concentric rings and curls, larger than 3b's."),
    "inception4b": ("GoogLeNet", "curls and stars",
        "Curls and small starbursts; the start of the creature-like forms."),
    "inception4c": ("GoogLeNet", "shells and spirals",
        ("Big shell- and fan-like spirals. Deep Dream's well-known eyes, dog faces "
         "and pagodas come from around here (4c to 5a) given time and strength.")),
    "inception4d": ("GoogLeNet", "creature textures",
        ("Patchy, fur- and skin-like textures with the odd eye; object-like parts "
         "given time.")),
    "inception4e": ("GoogLeNet", "large soft forms",
        "Larger, softer wavy forms; less fine texture than 4c and 4d."),
    "inception5a": ("GoogLeNet", "faint relief, slower",
        ("Deep and coarse: a faint relief at the default strength, larger forms "
         "with more. Slower: about 28 ms a frame.")),
    "inception5b": ("GoogLeNet", "faint relief, slower",
        ("GoogLeNet's last block: the faintest at the default strength, the "
         "largest forms. Slower: about 29 ms a frame.")),
}
OCTAVES = ["1", "2 alt", "3 alt"]       # one octave a frame, in rotation (spike D)
TINT_FROM = ["colour", "scene"]         # dream.tint_from: the tint's hue source
REF_HZ = 60.0                           # the frame rate the old per-frame units meant
FADE_LO, FADE_HI = 0.02, 10.0           # dream.fade: an echo's half-life, seconds (log)
GAP_LO, GAP_HI = 0.0, 0.25              # dream.gap: seconds between captures (0 = every frame)
OLD_DECAY = 0.95                        # the per-frame decay's old default, for a row with no base


# ---- the old per-frame units (plan 14 WP6) ----

def fade_of_decay(decay: float, hz: float = REF_HZ) -> float:
    """The half-life, in seconds, of a per-frame `decay` at `hz`: the
    seconds after which decay^(age·hz) is one half. Rounded to 4 places,
    clamped to the fader (a decay of 1 never fades: the longest fade)."""
    d = float(decay)
    if not math.isfinite(d):
        raise ValueError(f"decay {decay!r} is not a number")
    if d >= 1.0:
        return FADE_HI
    if d <= 0.0:
        return FADE_LO
    return round(min(max(math.log(0.5) / (hz * math.log(d)), FADE_LO), FADE_HI), 4)


def decay_per_frame(fade: float, hz: float = REF_HZ) -> float:
    """What a half-life of `fade` seconds fades an echo per frame at `hz`."""
    return 0.5 ** (1.0 / (max(float(fade), 1e-9) * hz))


def gap_of_every(every: float, hz: float = REF_HZ) -> float:
    """Every `every` frames at `hz`, in seconds between captures."""
    e = float(every)
    if not math.isfinite(e):
        raise ValueError(f"every {every!r} is not a number")
    return round(min(max(e / hz, GAP_LO), GAP_HI), 6)


# old id → (new id, the value's conversion)
LEGACY = {"dream.decay": ("dream.fade", fade_of_decay),
          "dream.every": ("dream.gap", gap_of_every)}


def fade_norm(fade: float) -> float:
    """dream.fade's fader position (log over FADE_LO…FADE_HI)."""
    f = min(max(float(fade), FADE_LO), FADE_HI)
    return math.log(f / FADE_LO) / math.log(FADE_HI / FADE_LO)


def migrate_values(values: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """`values` with the per-frame look-back ids read as 60 Hz frames and
    written in seconds (LEGACY), in place in the order; a new id the dict
    already names wins over the old one. Returns (the values, a note per
    id converted); the dict itself when there was nothing to convert."""
    if not any(k in LEGACY for k in values):
        return values, []
    out: dict[str, Any] = {}
    notes = []
    for k, v in values.items():
        if k in LEGACY:
            new, conv = LEGACY[k]
            if new in values:
                notes.append(f"{k} dropped: {new} is named")
                continue
            try:
                out[new] = conv(v)
            except (TypeError, ValueError):
                notes.append(f"{k} {v!r} is not a number, dropped")
                continue
            notes.append(f"{k} {v} → {new} {out[new]}")
        else:
            out[k] = v
    return out, notes


def migrate_row(row: dict, values: dict[str, Any] | None = None) -> tuple[dict, str | None]:
    """A route or desk row (its JSON) on an old per-frame id, on the new
    one. A push on ``dream.decay`` keeps its reach: its depth is re-drawn
    so the same hand throw spans the same decays, read at the base the
    file gives (`values`, the old or new id) or the default. Returns (the
    row, a note or None); the row itself when it was not on an old id."""
    target = row.get("target")
    if target not in LEGACY:
        return row, None
    new = LEGACY[target][0]
    out = dict(row, target=new)
    note = f"{target} → {new}"
    if target == "dream.decay" and out.get("op") == "push":
        # a push at the default depth (1) has no "value" key in its file
        depth = out.get("value", 1.0)
        new_depth = fade_depth(depth, out.get("source"), values)
        if new_depth is None:
            note += f" (push {depth!r} left as it was: not a number)"
        else:
            out["value"] = new_depth
            note += f" (push {float(depth):+g} → {new_depth:+g})"
    return out, note


def old_decay_base(values: dict[str, Any] | None) -> float:
    """The per-frame decay a file's pushes on ``dream.decay`` were drawn
    about: its ``dream.fade`` or ``dream.decay``, else the old default —
    a value that is not a number counts as the default."""
    vals = values or {}
    try:
        if "dream.fade" in vals:
            base = decay_per_frame(float(vals["dream.fade"]))
        else:
            base = float(vals.get("dream.decay", OLD_DECAY))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return OLD_DECAY
    return base if math.isfinite(base) else OLD_DECAY


def fade_depth(depth, source, values: dict[str, Any] | None = None) -> float | None:
    """A push depth on ``dream.decay`` (its linear 0–1 norm) as one on
    ``dream.fade`` spanning the same decays, about the file's base
    (`old_decay_base`); None when `depth` is not a number. A push adds
    depth · (u − rest): on a height (rest 0) the throw spans base … base +
    depth, on a centred axis base ± depth / 2."""
    try:
        depth = float(depth)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(depth):
        return None
    base = old_decay_base(values)
    height = str(source or "").endswith(".y")
    a, b = (base, base + depth) if height else (base - depth / 2, base + depth / 2)
    a, b = (min(max(x, 1e-6), 1.0) for x in (a, b))
    return round(fade_norm(fade_of_decay(b)) - fade_norm(fade_of_decay(a)), 4)


@dataclass
class DreamState(writes.Observed):
    """The dream.* params' object (params.py binds to these fields).

    Defaults started as the spike's recommendation (docs/plans/assets/
    06-lookback-perf.md: conv3_3 at 256, two steps of 0.03, k 0.08, mask
    decay 0.97) and were pushed for a wake that lasts and reads at a
    glance while tuning (2026-09-25): k 0.05 and mask decay 0.99, so the
    dream holds ~20 frames and its region lingers ~100 after content
    leaves; ``D`` at 70 % darkened only to 90 %; eight echoes, two frames
    apart, fading 0.95 a frame — in seconds since plan 14 WP6, an echo
    every 1/30 s halving every 0.225 s. The render covers the wake where
    it drew (occlude 1). Colours as the net painted them (tint 0).
    """

    on: bool = False          # plan 36 T4: the dream node's own — off, it passes through
    # the composite
    mix: float = 0.7          # the dream buffer's opacity
    darken: float = 0.1       # 0 as bright as the frame … 1 black
    contrast: float = 1.0     # power curve on every layer; 1 is neutral
    # the dream buffer's chroma, before the grade
    hue: float = 0.0          # degrees of hue rotation on the net's own colours
    sat: float = 1.0          # their saturation; 0 is greyscale, 1 as the net painted
    tint: float = 0.0         # 0 those colours … 1 luminance × the tint colour
    tint_from: int = 0        # index into TINT_FROM: a chosen colour, or the scene's hue
    tint_hue: float = 200.0   # the tint colour's hue, degrees
    tint_sat: float = 1.0     # …and saturation; 0 tints grey
    res: int = 2              # index into RES → 256
    # the dream worker's (WP6b) — declared here so loadable patches carry them
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


# ---- GL: one fullscreen triangle (glsl.QUAD_VS), three fragment programs ----

DOWN_FS = """
#version 330
uniform sampler2D u_scene;   // mipmapped: trilinear is a proper box-ish downsample
in vec2 v_uv;
out vec4 f_color;
void main() { f_color = texture(u_scene, v_uv); }
"""

# plan 36 T4: the dream node's pass — its input with the dream buffer laid
# over at `mix`, re-coloured (chroma) and graded as the look-back's layers
# are, premultiplied over: the dream buffer's own luminance is its coverage
DREAM_FS = """
#line 1 2
uniform sampler2D u_in;      // the dream's input picture
uniform int u_has_in;        // 0 = nothing wired in: D over transparent black
uniform sampler2D u_dream;   // the dream buffer D
uniform float u_dream_w;     // dream.mix
uniform float u_darken;
uniform float u_contrast;
uniform float u_hue;         // the dream's hue rotation, radians
uniform float u_sat;         // …and saturation scale about the grey axis
uniform float u_tint;        // 0 the dream's own colours … 1 luminance × the tint
uniform vec3 u_tint_rgb;     // the tint colour: chosen, or its input's hue (Dreamer.tint_rgb)
in vec2 v_uv;
out vec4 f_color;

vec3 grade(vec3 c) {
    return pow(max(c, vec3(1e-6)), vec3(u_contrast)) * (1.0 - u_darken);
}

vec3 chroma(vec3 c) {
    float l = dot(c, LUMA);
    vec3 own = mix(vec3(l), hue_rotate(c, u_hue), u_sat);  // _common.glsl
    return clamp(mix(own, l * u_tint_rgb, u_tint), 0.0, 1.0);
}

void main() {
    vec4 under = u_has_in != 0 ? texture(u_in, v_uv) : vec4(0.0);
    vec3 c = grade(chroma(texture(u_dream, v_uv).rgb));
    float a = u_dream_w * max(c.r, max(c.g, c.b));
    f_color = vec4(under.rgb * (1.0 - a) + c * u_dream_w, under.a + a - under.a * a);
}
"""


def post_fs(shared: str, body: str) -> str:
    """A pass's fragment shader over `shared`, the helpers from
    shaders/_common.glsl — read when the programs are built, so an edit
    lands on the next rebuild like everywhere else. `body` is the dream's
    (DREAM_FS; plan 90 H2: the look-back's trail pass is retired)."""
    return f"\n#version 330\n#line 1 1\n{shared}\n{body}"


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


def echo_size(res: int, w: int, h: int) -> tuple[int, int]:
    """The echo's size: `res` on the short side, the render's aspect, 8-px rounded."""
    w, h = max(w, 1), max(h, 1)
    if w >= h:
        return max(8, round(res * w / h / 8) * 8), res
    return res, max(8, round(res * h / w / 8) * 8)


class Dreamer:
    """The dream node's GL half (plan 36 T4, W4): the dream buffer `D` and
    the copy path to the worker (`LookbackSource`, dream.py), apart from
    any look-back. Once a frame while `dream.on` (the `dream` node's
    `run`): `pull` a finished result into `D`, then `submit` the node's
    input — downsampled to `dream.res` on its short side, read back once
    (the copy path; the input's mean colour for a tint from it, the same
    read) — so the worker dreams whatever is wired in. `lay` draws the
    input with `D` over it at `dream.mix`, re-hued, (de)saturated, tinted
    and graded (DREAM_FS). Off (`idle`): no submit, so the worker sleeps,
    and `D` is forgotten — the node passes its input through.

    One worker, one GPU job: one live dream at a time (decision D2, the
    graph refuses a second)."""

    def __init__(self, ctx: moderngl.Context, state: DreamState | None = None,
                 source: LookbackSource | None = None):
        self.ctx = ctx
        self.state = state if state is not None else DreamState()
        self.source = source
        self.frame = 0                 # submits made
        self.dream_frame = -1          # the submit `D` answers; −1 = nothing shown yet
        self.input_mean: tuple[float, float, float] | None = None   # tint from the input
        self.size = (0, 0)             # D's size (w, h) = the submit's
        self.dream: moderngl.Texture | None = None
        self._small: moderngl.Texture | None = None    # the input, downsampled
        self._fbo: moderngl.Framebuffer | None = None
        self._host: np.ndarray | None = None          # staging for a source without buffer()
        self.error = ""
        self.ring_error = ""
        self._build_programs()

    def _build_programs(self) -> None:
        ctx = self.ctx
        try:
            self._prog = ctx.program(vertex_shader=QUAD_VS,
                                     fragment_shader=post_fs(common(), DREAM_FS))
            self.error = ""
        except Exception as e:  # noqa: BLE001 — a bad edit must not kill the show
            self.error = gl_error(e, {1: "_common.glsl:", 2: "dream pass line "})
            self._prog = ctx.program(vertex_shader=QUAD_VS,
                                     fragment_shader=post_fs(FALLBACK, DREAM_FS))
        self._down = ctx.program(vertex_shader=QUAD_VS, fragment_shader=DOWN_FS)
        self._vao = ctx.vertex_array(self._prog, [])
        self._down_vao = ctx.vertex_array(self._down, [])
        self._prog["u_in"].value = 0
        self._prog["u_dream"].value = 2
        self._down["u_scene"].value = 0

    def on_reload(self) -> None:
        """Hot-swap hook (hotreload.py), and the renderer's call when
        _common.glsl is saved: the programs again; `D` persists. The old
        programs go only once the new ones exist."""
        old = (self._vao, self._down_vao, self._prog, self._down)
        self._build_programs()
        for res in old:
            res.release()

    def _ensure(self, w: int, h: int) -> bool:
        size = echo_size(RES[max(0, min(self.state.res, len(RES) - 1))], w, h)
        if size == self.size and self.dream is not None:
            return True
        self.release()
        try:
            self.dream = self.ctx.texture(size, 4)
            self.dream.repeat_x = self.dream.repeat_y = False
            self._small = self.ctx.texture(size, 4)
            self._fbo = self.ctx.framebuffer(color_attachments=[self._small])
        except Exception as e:  # noqa: BLE001 — no dream this frame, never a stuck one
            self.release()
            self.ring_error = f"dream: no buffer at {size[0]}×{size[1]}: {e}"[:160]
            return False
        self.ring_error = ""
        self.size = size
        self.dream_frame = -1
        self._host = None
        return True

    def release(self) -> None:
        for res in (self._fbo, self._small, self.dream):
            if res is not None:
                res.release()
        self._fbo = self._small = self.dream = None
        self.size = (0, 0)

    def wants_input(self) -> bool:
        """Whether this frame's input is read back: for the worker, or for
        the tint's hue."""
        return self.source is not None or self.scene_tinted()

    def submit(self, picture: moderngl.Texture, w: int, h: int) -> None:
        """This frame's input (`picture`, at the frame's size w × h) to the
        worker: downsampled into the submit buffer, read back once, handed
        over (`LookbackSource.submit`) — and its mean colour kept when the
        tint takes its hue from the input. Nothing without a worker or a
        tint to read for."""
        if not self.wants_input() or not self._ensure(w, h):
            return
        fbo = self.ctx.fbo
        try:
            picture.build_mipmaps()
            self._fbo.use()
            self.ctx.viewport = (0, 0, *self.size)
            self.ctx.disable(moderngl.BLEND)
            picture.use(location=0)
            self._down_vao.render(moderngl.TRIANGLES, vertices=3)
            self.ctx.enable(moderngl.BLEND)
            buf = self._buffer(self.source)
            self._fbo.read_into(buf, components=4)
        finally:
            fbo.use()
        self.frame += 1
        if self.scene_tinted():
            self.input_mean = mean_colour(buf)
        if self.source is not None:
            self.source.submit(buf, self.frame)

    def _buffer(self, source) -> np.ndarray:
        ew, eh = self.size
        shape = (eh, ew, 4)
        alloc = getattr(source, "buffer", None)
        if alloc is not None:
            buf = alloc(shape)
            if buf is not None:
                return buf
        if self._host is None or self._host.shape != shape:
            self._host = np.empty(shape, dtype=np.uint8)
        return self._host

    def pull(self) -> bool:
        """A finished dream result, if the source has a new one, into `D`
        (one of another size — a `dream.res` changed since its submit — is
        skipped)."""
        if self.source is None or self.dream is None:
            return False
        got = self.source.latest()
        if got is None:
            return False
        pixels, index = got
        if index == self.dream_frame:
            return False
        if tuple(np.shape(pixels)[:2]) != (self.size[1], self.size[0]):
            return False
        self.write_from(pixels, index)
        return True

    def write_from(self, array: np.ndarray, frame_index: int = 0) -> None:
        """Upload a dream result ((h, w, 4) uint8 at the submit size) into `D`."""
        if self.dream is None:
            raise RuntimeError("dream: no buffer yet")
        self.dream.write(array)
        self.dream_frame = frame_index

    def shows(self) -> bool:
        """Whether `D` is laid over the input this frame: on, with a result
        landed. Otherwise the node is its input, untouched."""
        return bool(self.state.on) and self.dream is not None and self.dream_frame >= 0

    def idle(self) -> None:
        """Off: no submit (the worker sleeps), and `D` forgotten so turning
        it on again starts clean."""
        self.dream_frame = -1
        self.input_mean = None

    def scene_tinted(self) -> bool:
        """Whether the dream's tint takes its hue from its input this frame."""
        return int(self.state.tint_from) == 1

    def tint_rgb(self) -> tuple[float, float, float]:
        """The tint colour the dream pass uses this frame: the chosen hue
        and saturation, or the input's mean hue at that saturation."""
        s = self.state
        if self.scene_tinted():
            return scene_tint(self.input_mean, s.tint_sat)
        return tint_colour(s.tint_hue, s.tint_sat)

    def lay(self, picture: moderngl.Texture | None, target: moderngl.Framebuffer) -> None:
        """The dream pass into `target`'s viewport: `picture` (None: nothing
        under) with `D` over it (`shows` must hold)."""
        s, ctx, p = self.state, self.ctx, self._prog
        target.use()
        ctx.disable(moderngl.BLEND)
        if picture is not None:
            picture.use(location=0)
        self.dream.use(location=2)
        p["u_has_in"].value = int(picture is not None)
        p["u_dream_w"].value = float(s.mix)
        p["u_darken"].value = float(s.darken)
        p["u_contrast"].value = float(s.contrast)
        p["u_hue"].value = math.radians(float(s.hue))
        p["u_sat"].value = float(s.sat)
        p["u_tint"].value = float(s.tint)
        p["u_tint_rgb"].value = self.tint_rgb()
        self._vao.render(moderngl.TRIANGLES, vertices=3)
        ctx.enable(moderngl.BLEND)
