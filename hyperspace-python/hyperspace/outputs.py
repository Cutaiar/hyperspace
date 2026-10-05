"""The render outputs, as the renderer sees them (plan 21 WP1).

One frame is drawn per loop; each output — a window on its own screen,
or an offscreen target standing in for one — shows that frame through
its own switches: the scene on or off, the hands on or off, and its own
dim. This module is the pure half of that: what an output asks for
(`Switches`), which pipeline gives it (`route`), where the frame sits in
an output of another shape (`fit`), and the one-frame record the
renderer fills in for an output (`View`, with `Handoff` for an output in
another window's context). `Renderer.draw_outputs` (render.py) does the
drawing.

Render stack (ARCHITECTURE §3): it only reads. This module imports
moderngl and glsl at most — never app, ui or params — and the
`output.N.*` params (WP4) write `Switches`, which the renderer reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import moderngl

MAX_OUTPUTS = 4

# pipeline keys, in run order: the scene through the look-back and the
# effects; the scene with the hands laid on before the effects (WP2); the
# hands alone through the effects (WP2)
SCENE, SCENE_HANDS, HANDS = 0, 1, 2
PIPELINES = (SCENE, SCENE_HANDS, HANDS)
NAMES = {SCENE: "SCENE", SCENE_HANDS: "SCENE+HANDS", HANDS: "HANDS"}


@dataclass
class Switches:
    """What one output shows — what the output.N.* params write (WP4)."""

    scene: bool = True
    hands: bool = True
    through: bool = False      # hands through effects (WP2)
    dim: float = 1.0           # this output's own dim, times the master's


def route(sw: Switches, fx_active: bool, hands_visible: bool) -> tuple[int | None, bool]:
    """(pipeline key, or None for the ground; hands composited after).

    `hands_visible` is "the ghost hands are on and a hand shows this
    frame" (`Ghost.layer` drew); the hands are *shown* on this output when
    its own hands switch is on too (fork F7).

    | scene | hands shown | through and an effect on | pipeline | hands after |
    |  on   |    no       |          —               | SCENE    | no          |
    |  on   |    yes      |          no              | SCENE    | yes         |
    |  off  |    no       |          —               | None     | no          |
    |  off  |    yes      |          no              | None     | yes         |

    Hands through effects (WP2) adds the SCENE_HANDS and HANDS rows; until
    then the switch is read as off."""
    shown = bool(sw.hands) and bool(hands_visible)
    return (SCENE if sw.scene else None), shown


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
    2. draws `frame` (RGBA8, `frame_size`, premultiplied, LINEAR) into
       `rect` (in its framebuffer, the view's `viewport` included) — 1:1 when `rect`'s size is `frame_size`, else scaled; with
       `bg_alpha` 1 it writes alpha 1. `frame` None: the ground only;
    3. lays `hands` (the hands' layer, premultiplied, frame-sized) over the
       same `rect` at `alpha`: colour ONE / ONE_MINUS_SRC_ALPHA, and alpha
       ZERO / ONE on an opaque ground (`bg_alpha` 1) — `Ghost.composite`'s
       blend. None: no hands after the effects on this output;
    4. lays `readout` (the guide and the tethers' labels when they are a
       layer of their own, WP2) the same way. None: nothing;
    5. multiplies the whole framebuffer by `factor` when it is under 1
       (`Renderer.dim_pass`'s blend: colour only on an opaque ground,
       colour and alpha otherwise).

    The textures are valid until the next `draw_outputs`; the renderer's
    context must be flushed (`glFlush`) before the presenter's samples
    them (plan §1: otherwise it sees last frame's)."""

    frame: moderngl.Texture | None
    frame_size: tuple[int, int]
    rect: tuple[int, int, int, int]
    hands: moderngl.Texture | None = None
    readout: moderngl.Texture | None = None
    alpha: float = 1.0
    factor: float = 1.0
    bg_alpha: float = 1.0

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

    @property
    def rect(self) -> tuple[int, int, int, int]:
        if self.viewport is not None:
            return tuple(int(v) for v in self.viewport)
        return 0, 0, int(self.size[0]), int(self.size[1])
