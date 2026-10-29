"""A feel drawn as its curve — position over time.

Wherever the panel sets a feel (motion.py) a small plot sits beside its
knobs: a route row's own feel (ui_routing._feel_line), a smooth
modifier's in GRAPH's side pane (ui_routing.modifier_block), the
gamepad's stick feel on the SYSTEM page (ui). The curve is where a
reading goes under that feel, its target dashed behind it —
motion.response, the feel's own kernels, so the plot is what the Router
does to a reading:

  spring   a step: the reading jumps 0 → 1 and the spring carries it.
           Below ζ 1 it overshoots and rings, at 1 it lands, above it
           creeps.
  follow   a push and a let-go: the reading jumps to 1 and the attack
           carries it out, then drops back to rest and the release
           brings it home — one edge per knob.

A red playhead sweeps the curve on a loop with a dot riding it; the
SYSTEM page's larger plot adds a square travelling a dashed track below,
at that position. The time axis fits the feel — out to where it has
settled, its length written at the bottom right — so a lazy and a tight
feel both read as a shape, and the number says which is which.

The geometry is pure (`let_go`, `window`, `position`, `curve`,
`playhead`) so tests read it with no imgui; `draw` is the one function
that touches a draw list. No state: the playhead is the imgui clock
modulo the loop.
"""

from __future__ import annotations

import math
from functools import lru_cache

from imgui_bundle import imgui

from . import motion, ui
from .motion import Motion

SAMPLES = 64           # points along the curve
PAUSE = 0.5            # s the playhead rests at the end before it sweeps again
WINDOW_MIN = 0.05      # s, the shortest time axis
RING_CYCLES = 6        # an undamped spring never settles: show this many cycles
DASH = 4.0             # px, the target's dashes
CURVE = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)


def _edges(m: Motion) -> tuple[float, float]:
    """follow's plot: how long the push holds, how long after the let-go
    it runs — each to its edge's settle, and at least a third of the plot,
    so an instant edge still shows its plateau. Both instant: WINDOW_MIN
    halved."""
    out, home = motion.settle(m), motion.settle(m, home=True)
    if out + home <= 0:
        return WINDOW_MIN / 2, WINDOW_MIN / 2
    third = (out + home) / 3
    return max(out, third), max(home, third)


def let_go(m: Motion) -> float | None:
    """When the reading drops back to rest on the plot: follow's push
    holds until its attack has arrived. A spring's is a step: never."""
    return _edges(m)[0] if m.mode == "follow" else None


def window(m: Motion) -> float:
    """The time axis, s: out to where the feel has settled. A spring: at
    most RING_CYCLES of its own period (undamped, it never settles)."""
    if m.mode == "follow":
        return sum(_edges(m))
    if m.mode == "spring" and m.hz > 0:
        return max(min(motion.settle(m), RING_CYCLES / m.hz), WINDOW_MIN)
    return WINDOW_MIN


def target(m: Motion, t: float) -> float:
    """The reading itself at t: 1 from the jump, 0 again after the let-go."""
    g = let_go(m)
    return 1.0 if g is None or t < g else 0.0


def position(m: Motion, t: float) -> float:
    """Where the feel has carried the reading by t (motion.response)."""
    g = let_go(m)
    if g is None or t <= g:
        return motion.response(m, t)
    return motion.response(m, t - g, x=motion.response(m, g), target=0.0)


@lru_cache(maxsize=256)    # drawn every frame; the knobs change rarely
def curve(m: Motion, n: int = SAMPLES) -> tuple[tuple[float, float], ...]:
    """(t, position) at n + 1 evenly spaced times across the window."""
    w = window(m)
    return tuple((w * i / n, position(m, w * i / n)) for i in range(n + 1))


def playhead(clock: float, m: Motion) -> float:
    """The playhead's time on the axis at this clock time: a sweep across
    the window, a PAUSE at its end, again."""
    w = window(m)
    return min(clock % (w + PAUSE), w)


def describe(m: Motion) -> str:
    """The plot's tooltip: the feel, what the curve is, how it lands."""
    pts = curve(m)
    if m.mode == "follow":
        out, home = motion.settle(m), motion.settle(m, home=True)
        return (f"Follow, attack {m.atk * 1000:.0f} ms, release {m.rel * 1000:.0f} ms: a "
                "reading pushed from rest to 1 and let go, dashed, and where the feel "
                f"carries it. It arrives in about {out:.2f} s and comes home in about "
                f"{home:.2f} s.")
    st = motion.settle(m)
    peak = max(y for _, y in pts)
    return (f"Spring, {m.hz:.2f} Hz, ζ {m.damp:.2f}: a reading that jumps from 0 to 1, "
            "dashed, and where the spring carries it. "
            + ("Undamped, it rings forever." if math.isinf(st) else
               (f"It overshoots {100 * (peak - 1):.0f} % and " if peak > 1.005 else "It ")
               + f"settles in about {st:.2f} s."))


def _dashed(dl, a: imgui.ImVec2, b: imgui.ImVec2, col: int) -> None:
    """A dashed line, horizontal or vertical."""
    length = math.hypot(b.x - a.x, b.y - a.y)
    if length <= 0:
        return
    ux, uy = (b.x - a.x) / length, (b.y - a.y) / length
    d = 0.0
    while d < length:
        e = min(d + DASH, length)
        dl.add_line(imgui.ImVec2(a.x + ux * d, a.y + uy * d),
                    imgui.ImVec2(a.x + ux * e, a.y + uy * e), col, 1.0)
        d += 2 * DASH


def draw(m: Motion, width: float, height: float, track: bool = False) -> None:
    """The plot, `width` × `height` px at the cursor, as one item (a
    feel that is off draws nothing); with `track`, a square travelling a
    dashed track under it, inside the same height."""
    if not m.on:
        return
    o = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    axis, faint, red, line = (ui.u32(ui.LINE), ui.u32(ui.FAINT), ui.u32(ui.RED),
                              ui.u32(CURVE))
    th = min(18.0, height * 0.3) if track else 0.0     # the track's band
    pad = 3.0
    x0, x1 = o.x + pad, o.x + width - pad
    y0, y1 = o.y + pad, o.y + height - pad - th
    pts = curve(m)
    w = pts[-1][0]
    lo = min(0.0, min(y for _, y in pts))
    hi = max(1.0, max(y for _, y in pts))
    lo, hi = lo - 0.06 * (hi - lo), hi + 0.06 * (hi - lo)

    def at(t: float, y: float) -> imgui.ImVec2:
        return imgui.ImVec2(x0 + (x1 - x0) * t / w, y1 - (y1 - y0) * (y - lo) / (hi - lo))

    # the axes, the reading dashed (a step, or a push and its let-go), the curve
    base = at(0.0, 0.0).y
    dl.add_line(imgui.ImVec2(x0, y0), imgui.ImVec2(x0, y1), axis, 1.0)
    dl.add_line(imgui.ImVec2(x0, base), imgui.ImVec2(x1, base), axis, 1.0)
    g = let_go(m)
    _dashed(dl, at(0.0, 1.0), at(w if g is None else g, 1.0), axis)
    if g is not None:
        _dashed(dl, at(g, 1.0), at(g, 0.0), axis)
    dl.add_polyline([at(t, y) for t, y in pts], line, 1.5, 0)
    # the playhead and where the curve is under it
    t = playhead(imgui.get_time(), m)
    y = position(m, t)
    p = at(t, y)
    dl.add_line(imgui.ImVec2(p.x, y0), imgui.ImVec2(p.x, y1), red, 1.0)
    dl.add_circle_filled(p, 2.5, line)
    label = f"{w:.2f} s" if w < 10 else f"{w:.0f} s"
    sz = imgui.calc_text_size(label)
    # bottom right: a spring has risen by then; a follow's release has come
    # home, so its label goes top right
    ly = base - sz.y - 1 if g is None else y0
    if sz.y < (y1 - y0) * 0.6:
        dl.add_text(imgui.ImVec2(x1 - sz.x, ly), faint, label)
    if track:
        # the square: rest at the left, the target near the right, so an
        # overshoot carries it past and back
        cy = y1 + pad + th / 2
        s = th - 4
        ta, tb = x0 + s / 2, x1 - s / 2
        _dashed(dl, imgui.ImVec2(x0, cy), imgui.ImVec2(x1, cy), axis)
        sx = ta + (y - lo) * (tb - ta) / (hi - lo)
        dl.add_rect(imgui.ImVec2(sx - s / 2, cy - s / 2), imgui.ImVec2(sx + s / 2, cy + s / 2),
                    line, 0.0, 1.5)
    imgui.dummy(imgui.ImVec2(width, height))
    if imgui.is_item_hovered():
        ui.tooltip(describe(m))
