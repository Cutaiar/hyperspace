"""Hold — the projector keeps its look while the operator builds the next
one (plan 38, the owner, 2026-10-27).

The owner's ask: hold the render setup that is on the projector while the
node operator previews changes that are not on the main output yet, so the
room never watches a scene being built.

**Held**, every render output (each window, each publish-only output) is
the *program*: drawn by the app's one renderer from the wiring and the
look as they were when the hold was engaged. Everything the operator does
meanwhile — a GRAPH edit, a new preset, a knob turned — lands as ever (the
registry, `Renderer.wiring`, undo, the dirty dot) and is the *preview*:
drawn by a second renderer (`preview_renderer`), and only on frames the
GRAPH page shows it behind its canvas (`outputs.Preview`). Modulation —
the bands, the LFOs, the hands — rides on both: the program is the held
bases plus this frame's offsets, so the projector stays live.

**Take** puts the preview on the projector: the hold lets go and the next
frame draws the program from what is landed — a cut, the look-back's
trails going on (they are the program renderer's). **Drop** puts the
preview back to the program: one undo step back to the hold point, the
preset's part only (its look, its graph, its routes and desk — never the
rig's session params), then the hold lets go. Both are undoable like any
replacing action.

How the program is drawn (`program`): around the draw, the renderer is
handed the held wiring (and the held extra hands states), and each held
param whose base the operator moved is written to its object
(`Param.put`, never `set`: no base moves, no undo step, no dirty dot) and
the live value put back after. A param nobody moved costs one compare.
Only the groups the renderer reads are held (`HELD_GROUPS`); what is one
for both:

- the turn — `rot.*`, speed, the planes, the 3D switch: the angles are
  integrated once a frame, before either draw (`ViewState.integrate`);
- the media channels (`media.*`): a channel decodes once for every reader,
  so a source switched shows on both;
- the modulators (`lfo`, `env`, `seq`, `macro`, `mod`) and the routes:
  their offsets are this frame's, read once — a route added under hold
  moves the program's param too;
- an effect instance a new preset removed: the program's node reads
  through (`FxState.live` is False for it) until Take or Drop.

Imports only `undo` (for `alike`) and the param groups; the registry, the
renderer and the undo object arrive as arguments and are used duck-typed,
so the tests drive it without GL."""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import Any

from .params import PERFORMANCE_GROUPS
from .undo import alike

# the performance groups the renderer reads, held for the program; the
# rest of the preset's part is one for both (the module's docstring)
HELD_GROUPS = ("view", "camera", "pattern", "dream", "fx", "backdrop", "switch", "resize")
# …less the params the integrator reads before either draw: holding the 3D
# switch alone would draw the program's pose with the preview's body
ONE_FOR_BOTH = ("view.three_d",)
# the preview's long side at most: the GRAPH page's backdrop, not a show
PREVIEW_MAX = 1280

ENGAGE_TIP = ("Hold the projector on what it shows now. Every output keeps this look — "
              "live, still moving with the music — while you build the next one; the "
              "GRAPH page shows your changes behind the nodes. TAKE puts them on the "
              "projector, DROP throws them away.")
TAKE_TIP = ("Put the preview on the projector: the hold lets go and every output shows "
            "what you built (a cut).")
DROP_TIP = ("Throw away what changed since HOLD — the look, the graph, the routes — and "
            "let go: the projector never moved, so nothing changes there.")


class Hold:
    """The hold: off, or on with the program's wiring and look.

    `reg` is the app's registry; `renderer` the one that draws the outputs
    (`Renderer.wiring` and `ghost_states` are the live, edited ones);
    `undo` (optional) the app's `undo.Undo`, which holds the point to drop
    back to; `make` (optional) builds the preview renderer on first use —
    without it there is no preview, and the hold still holds."""

    def __init__(self, reg, renderer, undo=None, make: Callable[[], Any] | None = None):
        self.reg, self.renderer, self.undo, self.make = reg, renderer, undo, make
        self.on = False
        self.wiring = None              # the program's wiring, as engaged
        self.ghosts: dict = {}          # …and its extra hands nodes' states
        self.values: dict[str, Any] = {}    # held param id → its base when engaged
        self.point = None               # the undo state Drop goes back to
        self.since = 0.0                # the frame clock when engaged
        self.moved = 0                  # held params the program put back last frame
        self.preview = None             # the preview renderer, made on first use
        self.error = ""                 # why the preview could not be drawn
        self.status = ""                # what the last engage / take / drop did

    # ---- the switch

    def engage(self, now: float = 0.0) -> bool:
        """Hold the projector on what is landed now. False: it already was."""
        if self.on:
            return False
        r, reg = self.renderer, self.reg
        self.wiring = getattr(r, "wiring", None)
        self.ghosts = dict(getattr(r, "ghost_states", None) or {})
        self.values = {p.id: _copy(p.base) for p in reg if held(p)}
        undo = self.undo
        self.point = undo.checkpoint() if undo is not None else None
        self.on, self.since, self.moved, self.error = True, now, 0, ""
        self.status = "held: the projector keeps this look"
        return True

    def take(self) -> bool:
        """The preview onto the projector: let go. False: nothing was held."""
        if not self.on:
            return False
        self._let_go()
        self.status = "taken: the projector shows the preview"
        return True

    def drop(self) -> bool:
        """The preview back to the program, then let go: the preset's part
        put back as it was at the hold (an undo step), the rig's left. With
        no undo to ask, only the held params go back. False: nothing held."""
        if not self.on:
            return False
        undo, point = self.undo, self.point
        if undo is not None and point is not None:
            undo.revert(_preset_part(point, self.reg), "drop the preview")
        else:
            todo = {pid: v for pid, v in self.values.items()
                    if pid in self.reg and not alike(self.reg[pid].base, v)}
            if todo:
                self.reg.restore(todo)
        self._let_go()
        self.status = "dropped: back to what the projector shows"
        return True

    def toggle(self, on: bool, now: float = 0.0) -> None:
        """The `output.hold` toggle: on engages, off takes."""
        if on:
            self.engage(now)
        else:
            self.take()

    def _let_go(self) -> None:
        self.on = False
        self.wiring, self.ghosts, self.values, self.point = None, {}, {}, None
        self.moved, self.error = 0, ""

    # ---- what the program is

    def changed(self) -> list[str]:
        """The held params whose base the operator has moved, by id."""
        reg = self.reg
        return [pid for pid, v in self.values.items()
                if pid in reg and not alike(reg[pid].base, v)]

    def rewired(self) -> bool:
        """Has the graph changed since the hold?"""
        return self.on and getattr(self.renderer, "wiring", None) != self.wiring

    @contextmanager
    def program(self, renderer=None) -> Iterator[None]:
        """Around the draw of the outputs: the held wiring and look on
        `renderer` (the hold's own by default), the live ones back after —
        whatever the draw raised. Off, nothing changes."""
        if not self.on:
            yield
            return
        r = renderer if renderer is not None else self.renderer
        reg = self.reg
        back: list[tuple[Any, Any]] = []
        wiring, ghosts = getattr(r, "wiring", None), getattr(r, "ghost_states", None)
        try:
            for pid, v in self.values.items():
                p = reg.get(pid)
                if p is None or alike(p.base, v):
                    continue
                live = _copy(p.get())
                p.put(program_value(p, v))
                back.append((p, live))
            r.wiring = self.wiring
            r.ghost_states = self.ghosts
            yield
        finally:
            r.wiring = wiring
            if ghosts is not None:
                r.ghost_states = ghosts
            for p, live in reversed(back):
                p.put(live)
            self.moved = len(back)

    # ---- the preview

    def preview_renderer(self):
        """The renderer that draws the preview, made on first use (`make`);
        None without one, or when it would not build (`error` says why)."""
        if self.preview is None and self.make is not None:
            try:
                self.preview = self.make()
            except Exception as e:  # noqa: BLE001 — no preview must not cost the hold
                self.make, self.error = None, f"{type(e).__name__}: {e}"
        return self.preview

    def draw_preview(self, s, w: int, h: int, size: tuple[int, int], target, view_of) -> bool:
        """The preview frame: the live wiring and look, drawn by the preview
        renderer into `target` (a framebuffer of the render context, made at
        the size `preview_size` gives) — `view_of(size, target)` is the
        `outputs.View` to draw it as. `w`, `h` are output 1's logical size,
        so strokes and points keep the projector's proportions. True when
        drawn; a raise is said in `error`, never passed on."""
        pr = self.preview_renderer()
        if pr is None:
            return False
        try:
            mirror(self.renderer, pr)
            pr.draw_outputs(s, max(w, 1), max(h, 1), size[0] / max(w, 1),
                            [view_of(size, target)])
        except Exception as e:  # noqa: BLE001 — the preview must not cost the program
            self.error = f"{type(e).__name__}: {e}"
            return False
        self.error = ""
        return True


def held(p) -> bool:
    """Is this param part of the program's look — a persisted, real, set
    (not fired, not typed) param of a group the renderer reads?"""
    return (p.persist and not p.alias and p.group in HELD_GROUPS and p.id not in ONE_FOR_BOTH
            and getattr(p.kind, "value", p.kind) not in ("trigger", "text"))


def program_value(p, base):
    """What `p`'s object holds for the program: the held `base`, plus the
    offset modulation put on the live base this frame (a continuous
    param's, in its norm — the offset `Param.apply` added), so a held
    param a band drives still moves with the band. A list, or a discrete
    param, is the held base."""
    lo = getattr(p, "_base", None)
    if lo is None or isinstance(base, list) or getattr(p.kind, "value", p.kind) != "continuous":
        return _copy(base)
    off = p.eff_norm - lo
    u = p._norm_of(base) + off
    if not math.isfinite(u):
        return _copy(base)
    u = u % 1.0 if p.wrap else min(max(u, 0.0), 1.0)
    v = p._value_of_norm(u)
    return round(v) if getattr(p, "integer", False) else v


def preview_size(full: tuple[int, int], cap: tuple[int, int] | None = None) -> tuple[int, int]:
    """The preview's size: output 1's framebuffer `full` under the render
    cap `cap`, shrunk (aspect kept) to `PREVIEW_MAX` on its long side."""
    w, h = max(int(full[0]), 1), max(int(full[1]), 1)
    if cap is not None:
        k = min(1.0, cap[0] / w, cap[1] / h)
        w, h = max(round(w * k), 1), max(round(h * k), 1)
    k = min(1.0, PREVIEW_MAX / max(w, h))
    return max(round(w * k), 1), max(round(h * k), 1)


# the main renderer's inputs the preview renderer reads the same way —
# handed over every frame, as `app.frame` hands them to the main one
MIRRORED = ("media", "cloud_source", "bands", "ghost_states", "wiring")


def mirror(main, pr) -> None:
    """The preview renderer `pr` reads what the main one does this frame:
    the media channels, the clouds, the bands, the hands (their source and
    the table that lights the guide) and the live wiring — not the dim or
    the window's ground: the preview is the look, not the room."""
    for name in MIRRORED:
        setattr(pr, name, getattr(main, name, None))
    if pr.ghost_states is None:
        pr.ghost_states = {}
    g, pg = getattr(main, "ghost", None), getattr(pr, "ghost", None)
    if g is not None and pg is not None:
        pg.source, pg.router = g.source, g.router
    pr.max_frame = None                 # the preview's own size is its cap
    pr.bg_alpha, pr.dim = 1.0, 1.0


def preview_renderer(main):
    """A second renderer on the main one's context, for the preview: the
    same params' objects (the look-back's `DreamState`, the effects'
    `FxState`, the hands' `GhostState`), so a knob turned shows in both,
    and the same clock, so an effect's phase moves once a frame. Its
    look-back has no dream worker: the preview shows the echoes, the dream
    is the projector's."""
    from .render import Renderer

    pr = Renderer(main.ctx, dream=main.lookback.state, fx=main.fx.state,
                  ghost=main.ghost.state)
    pr._t0 = main._t0
    mirror(main, pr)
    return pr


def register(reg, hold: Hold, now: Callable[[], float] = lambda: 0.0) -> list[str]:
    """`output.hold` (a toggle: on holds, off takes), `output.take` and
    `output.drop` — rig controls like `output.fullscreen`: group `output`,
    never persisted, not modulatable; learnable onto a desk button."""
    rig = {"group": "output", "modulatable": False}
    reg.toggle("output.hold", "Hold projector", lambda: hold.on,
               lambda v: hold.toggle(bool(v), now()), tip=ENGAGE_TIP, persist=False, **rig)
    # lit while held: a desk button learned onto either says there is a preview
    reg.trigger("output.take", "Take preview", hold.take, tip=TAKE_TIP,
                lit=lambda: hold.on, **rig)
    reg.trigger("output.drop", "Drop preview", hold.drop, tip=DROP_TIP,
                lit=lambda: hold.on, **rig)
    return ["output.hold", "output.take", "output.drop"]


def _preset_part(state, reg):
    """An undo state with only the preset's bases (the performance groups)
    — Drop puts the look back, never the rig."""
    bases = getattr(state, "bases", None)
    if bases is None:
        return state
    keep = {pid: v for pid, v in bases.items()
            if (p := reg.get(pid)) is None or p.group in PERFORMANCE_GROUPS}
    return replace(state, bases=keep)


def _copy(v):
    return copy.copy(v) if isinstance(v, list | dict) else v
