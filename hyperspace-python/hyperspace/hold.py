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
handed the held wiring, the held rig cables (plan 36's bus from All
outputs into each window, `graph.RigWires`, which the renderer reads from
its `rig_source`) and the held extra hands states, and each held
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

and what a landing would take from the program, it keeps (plan 38 B3):
every `preset.GraphSection` landing — a load, a GRAPH edit, an undo —
settles the effect instances, the switches, the resizes and the extra
look-backs to its graph; while held it asks `keep`, which adds the held
program's own (snapshotted at the press), so their params, values, picks,
states and effect phases stay for the program until Take (which settles to
the live graph alone) or Drop (which lands the hold point). A load's delay
reset goes to the preview while held (`reset_delays`), and to the
projector's renderer at Take.

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

from .params import PERFORMANCE_GROUPS, lookback_ids, resize_ids, switch_id
from .undo import alike

# the performance groups the renderer reads, held for the program; the
# rest of the preset's part is one for both (the module's docstring)
HELD_GROUPS = ("view", "camera", "pattern", "dream", "fx", "backdrop", "switch", "resize")
# …less the params the integrator reads before either draw: holding the 3D
# switch alone would draw the program's pose with the preview's body
# (plan 38 B3: and the turn's speed and planes, which the draw never reads —
# held, they would only count as "changed" on the head's red line)
ONE_FOR_BOTH = ("view.three_d", "view.speed")
ONE_FOR_BOTH_PREFIXES = ("view.plane.",)
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
    without it there is no preview, and the hold still holds; `section`
    (optional) the presets' `GraphSection`, whose landings keep the held
    program's nodes while held (plan 38 B3)."""

    def __init__(self, reg, renderer, undo=None, make: Callable[[], Any] | None = None,
                 section=None):
        self.reg, self.renderer, self.undo, self.make = reg, renderer, undo, make
        self.section = section
        self.kept: dict[str, Any] = {}  # the program's node instances by kind, as engaged
        self.loaded = False             # a load reset the preview's delays while held
        self.on = False
        self.wiring = None              # the program's wiring, as engaged
        self.rig = None                 # …its rig cables (a `graph.RigWires`), as engaged
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
        self.rig = _rig(r)
        self.ghosts = dict(getattr(r, "ghost_states", None) or {})
        self.values = {p.id: _copy(p.base) for p in reg if held(p)}
        undo = self.undo
        self.point = undo.checkpoint() if undo is not None else None
        sec = self.section
        if sec is not None:
            self.kept = sec.names()
            sec.hold = self
        self.on, self.since, self.moved, self.error = True, now, 0, ""
        self.status = "held: the projector keeps this look"
        return True

    def take(self) -> bool:
        """The preview onto the projector: let go. False: nothing was held."""
        if not self.on:
            return False
        loaded = self.loaded
        self._release()
        self._settle()                  # the live graph's instances alone, now
        self._let_go()
        if loaded:                      # R19: a load's delays start empty — on the projector now
            reset = getattr(self.renderer, "reset_delays", None)
            if callable(reset):
                reset()
        self.status = "taken: the projector shows the preview"
        return True

    def drop(self) -> bool:
        """The preview back to the program, then let go: the preset's part
        put back as it was at the hold (an undo step), the rig's left. With
        no undo to ask, only the held params go back. False: nothing held."""
        if not self.on:
            return False
        undo, point = self.undo, self.point
        self._release()                 # the revert lands the hold point as it was
        if undo is not None and point is not None:
            undo.revert(_preset_part(point, self.reg), "drop the preview")
        else:
            todo = {pid: v for pid, v in self.values.items()
                    if pid in self.reg and not alike(self.reg[pid].base, v)}
            if todo:
                self.reg.restore(todo)
            self._settle()              # (the revert's landing settles in the branch above)
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
        self._release()
        self.on = False
        self.wiring, self.rig, self.ghosts, self.values, self.point = None, None, {}, {}, None
        self.moved, self.error, self.kept, self.loaded = 0, "", {}, False

    def _release(self) -> None:
        """The landings no longer keep the program's nodes."""
        sec = self.section
        if sec is not None and getattr(sec, "hold", None) is self:
            sec.hold = None

    def _settle(self) -> None:
        sec = self.section
        if sec is not None and callable(getattr(sec, "settle", None)):
            sec.settle()

    # ---- what a landing keeps while held (preset.GraphSection's seam)

    def keep(self, kind: str, names):
        """`names` (a landing's instances of `kind`) with the held program's
        own added, in `names`' own shape (a list keeps its order, the held
        ones after; None — every effect file — stays None). Off: `names`."""
        held = self.kept.get(kind) if self.on else None
        if kind == "fx" and self.on and held is None and kind in self.kept:
            return None                 # the program had every file: keep them all
        if names is None or not held:
            return names
        if isinstance(names, list):
            return [*names, *sorted(n for n in held if n not in names)]
        return frozenset(names) | frozenset(held)

    def program_only(self) -> frozenset[str]:
        """The param ids of the instances kept for the program alone — the
        held look's nodes the live graph no longer has. Not the preset's:
        `Presets._values` leaves them out, so a save while held writes, and
        the dirty dot weighs, the live graph's values only."""
        sec = self.section
        if not self.on or sec is None or not callable(getattr(sec, "names", None)):
            return frozenset()
        live = sec.names()
        ids: set[str] = set()
        for kind, held in self.kept.items():
            if not held:
                continue
            for n in set(held) - set(live.get(kind) or ()):
                if kind == "fx":
                    ids |= {p.id for p in self.reg if p.id.startswith(f"fx.{n}.")}
                elif kind == "switch":
                    ids.add(switch_id(n))
                elif kind == "resize":
                    ids.update(resize_ids(n))
                elif kind == "lookback":
                    ids.update(lookback_ids(n))
        return frozenset(ids)

    def reset_delays(self) -> None:
        """A load's delay reset while held (`Presets.load`, R19): the
        preview's delays start empty; the projector's keep their trail
        until Take, which resets them then."""
        self.loaded = True
        reset = getattr(self.preview, "reset_delays", None)
        if callable(reset):
            reset()

    # ---- what the program is

    def changed(self) -> list[str]:
        """The held params whose base the operator has moved, by id."""
        reg = self.reg
        return [pid for pid, v in self.values.items()
                if pid in reg and not alike(reg[pid].base, v)]

    def rewired(self) -> bool:
        """Has the graph changed since the hold — the preset's wires or the
        rig's bus cables (plan 36: both are drawn on GRAPH)?"""
        r = self.renderer
        return self.on and (getattr(r, "wiring", None) != self.wiring
                            or _cut(_rig(r)) != _cut(self.rig))

    @contextmanager
    def program(self, renderer=None) -> Iterator[None]:
        """Around the draw of the outputs: the held wiring, rig cables and
        look on `renderer` (the hold's own by default), the live ones back
        after — whatever the draw raised. Off, nothing changes. Plan 36's
        rule: the held copy is exactly what was landed at the press — no
        wire is filled in, none is defaulted."""
        if not self.on:
            yield
            return
        r = renderer if renderer is not None else self.renderer
        reg = self.reg
        back: list[tuple[Any, Any]] = []
        wiring, ghosts = getattr(r, "wiring", None), getattr(r, "ghost_states", None)
        source = getattr(r, "rig_source", None)
        try:
            for pid, v in self.values.items():
                p = reg.get(pid)
                if p is None or alike(p.base, v):
                    continue
                live = _copy(p.get())
                p.put(program_value(p, v))
                back.append((p, live))
            r.wiring = self.wiring
            r.rig_source = _HeldRig(self.rig)
            r.ghost_states = self.ghosts
            yield
        finally:
            r.wiring = wiring
            r.rig_source = source
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
            and not p.id.startswith(ONE_FOR_BOTH_PREFIXES)
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
# (plan 38 B1: and the rig's cables — `rig_source`, plan 36 T1 — so the
# preview's windows read the bus as the show has it, never every default
# standing as a renderer with none would)
MIRRORED = ("media", "cloud_source", "rig_source", "bands", "ghost_states", "wiring")


def mirror(main, pr) -> None:
    """The preview renderer `pr` reads what the main one does this frame:
    the media channels, the clouds, the rig's bus cables, the bands, the
    hands (their source and the table that lights the guide) and the live
    wiring — not the dim or
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


class _HeldRig:
    """The program's `rig_source` while held: the rig cables as they were
    at the press (plan 38 B1), in the shape `graph.rig_of` reads (`rig`)."""

    __slots__ = ("rig",)

    def __init__(self, rig):
        self.rig = rig


def _rig(r):
    """The rig cables `r` draws from — its `rig_source`'s `rig`, read the
    way `graph.rig_of` does (duck-typed: hold imports no graph)."""
    return getattr(getattr(r, "rig_source", None), "rig", None)


def _cut(rig) -> frozenset:
    """The cables `rig` cuts, as `graph.rig_of` reads it: None, or no
    `RigWires`, cuts none (plan 38 B3 M8)."""
    return frozenset(getattr(rig, "cut", None) or ())


def canvas_renderer(panel):
    """The renderer the GRAPH canvas reads (plan 38 B3): while the projector
    is held and the preview has been drawn, the preview's — its graph is
    the edited one, so a new node's refs, the dormant lines and the
    refusals describe what TAKE would put up; else the panel's own."""
    hold, r = getattr(panel, "hold", None), getattr(panel, "renderer", None)
    pr = getattr(hold, "preview", None) if hold is not None and hold.on else None
    if pr is not None and getattr(pr, "_graph", None) is not None:
        return pr
    return r


def _copy(v):
    return copy.copy(v) if isinstance(v, list | dict) else v
