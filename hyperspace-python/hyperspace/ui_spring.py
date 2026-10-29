"""A spring feel drawn as its curve — position over time.

Wherever the panel sets a spring (a route row's own feel, ui_routing; the
gamepad's stick feel on the SYSTEM page, ui) a small plot sits beside its
knobs: the spring's step response, a reading jumping from 0 to 1 and the
feel carrying it there, against a dashed line at the target. It is
motion.spring's own closed form at the knobs' real Hz and damping ratio,
so the curve is what a reading does under that feel: below ζ 1 it
overshoots and rings, at 1 it lands, above it creeps. A red playhead
sweeps it on a loop with a dot riding the curve; the SYSTEM page's larger
plot adds a square travelling a dashed track below, at that position.

The time axis fits the spring — out to where it has settled, its length
written at the axis' end — so a lazy and a tight spring both read as a
shape; the number says which is which. The geometry is pure (`window`,
`curve`, `playhead`) so tests read it with no imgui; `draw` is the one
function that touches a draw list. No state: the playhead is the imgui
clock modulo the loop.
"""

from __future__ import annotations

import math
from functools import lru_cache

from imgui_bundle import imgui

from . import motion, ui

SAMPLES = 64           # points along the curve
PAUSE = 0.5            # s the playhead rests at the end before it sweeps again
WINDOW_MIN = 0.05      # s, the shortest time axis
RING_CYCLES = 6        # an undamped spring never settles: show this many cycles
DASH = 4.0             # px, the target line's dashes
CURVE = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)


@lru_cache(maxsize=256)     # drawn every frame; the knobs change rarely
def settle(hz: float, damp: float) -> float:
    """Seconds until the spring stays within 2 % of its target, measured
    off the curve itself (critical damping's (1 + ωt)·e^(−ωt) lands later
    than its envelope says). Never, undamped."""
    if hz <= 0:
        return 0.0
    w = 2 * math.pi * hz
    z = max(damp, 0.0)
    if z <= 1e-6:
        return math.inf
    r = z * w if z <= 1 else w * (z - math.sqrt(z * z - 1))
    end = 8.0 / r                                # the slowest root's envelope, well past 2 %
    n = 400
    for i in range(n, -1, -1):
        t = end * i / n
        if abs(position(t, hz, damp) - 1.0) > 0.02:
            return end * min(i + 1, n) / n
    return 0.0


def window(hz: float, damp: float) -> float:
    """The time axis, s: out to where the spring has settled — at most
    RING_CYCLES of its own period, at least WINDOW_MIN."""
    if hz <= 0:
        return WINDOW_MIN
    return max(min(settle(hz, damp), RING_CYCLES / hz), WINDOW_MIN)


def position(t: float, hz: float, damp: float) -> float:
    """Where a reading that jumped 0 → 1 at t = 0 is after t s of the feel:
    motion.spring stepped once over the whole time, exact in closed form."""
    if t <= 0:
        return 0.0
    x, _ = motion.spring(0.0, 0.0, 1.0, t, hz, damp)
    return x


@lru_cache(maxsize=256)
def curve(hz: float, damp: float, n: int = SAMPLES) -> tuple[tuple[float, float], ...]:
    """(t, position) at n + 1 evenly spaced times across the window."""
    w = window(hz, damp)
    return tuple((w * i / n, position(w * i / n, hz, damp)) for i in range(n + 1))


def playhead(clock: float, hz: float, damp: float) -> float:
    """The playhead's time on the axis at this clock time: a sweep across
    the window, a PAUSE at its end, again."""
    w = window(hz, damp)
    return min(clock % (w + PAUSE), w)


def _dashed(dl, x0: float, x1: float, y: float, col: int) -> None:
    x = x0
    while x < x1:
        dl.add_line(imgui.ImVec2(x, y), imgui.ImVec2(min(x + DASH, x1), y), col, 1.0)
        x += 2 * DASH


def draw(hz: float, damp: float, width: float, height: float,
         track: bool = False) -> None:
    """The plot, `width` × `height` px at the cursor, as one item; with
    `track`, a square travelling a dashed track under it (inside the same
    height). Its tooltip says what it shows."""
    o = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    axis, faint, red = ui.u32(ui.LINE), ui.u32(ui.FAINT), ui.u32(ui.RED)
    th = min(18.0, height * 0.3) if track else 0.0     # the track's band
    pad = 3.0
    x0, x1 = o.x + pad, o.x + width - pad
    y0, y1 = o.y + pad, o.y + height - pad - th
    pts = curve(hz, damp)
    w = pts[-1][0]
    lo = min(0.0, min(y for _, y in pts))
    hi = max(1.0, max(y for _, y in pts))
    lo, hi = lo - 0.06 * (hi - lo), hi + 0.06 * (hi - lo)

    def at(t: float, y: float) -> imgui.ImVec2:
        return imgui.ImVec2(x0 + (x1 - x0) * t / w, y1 - (y1 - y0) * (y - lo) / (hi - lo))

    # the axes, the target dashed across, the curve
    base = at(0.0, 0.0).y
    dl.add_line(imgui.ImVec2(x0, y0), imgui.ImVec2(x0, y1), axis, 1.0)
    dl.add_line(imgui.ImVec2(x0, base), imgui.ImVec2(x1, base), axis, 1.0)
    _dashed(dl, x0, x1, at(0.0, 1.0).y, axis)
    dl.add_polyline([at(t, y) for t, y in pts], ui.u32(CURVE), 1.5, 0)
    # the playhead and where the curve is under it
    t = playhead(imgui.get_time(), hz, damp)
    y = position(t, hz, damp)
    p = at(t, y)
    dl.add_line(imgui.ImVec2(p.x, y0), imgui.ImVec2(p.x, y1), red, 1.0)
    dl.add_circle_filled(p, 2.5, ui.u32(CURVE))
    label = f"{w:.2f} s" if w < 10 else f"{w:.0f} s"
    sz = imgui.calc_text_size(label)
    if sz.y < (y1 - y0) * 0.6:          # bottom right: the curve has risen by then
        dl.add_text(imgui.ImVec2(x1 - sz.x, base - sz.y - 1), faint, label)
    if track:
        # the square: 0 at the track's left third, 1 at its right, so an
        # overshoot carries it past the target and back
        cy = y1 + pad + th / 2
        s = th - 4
        ta, tb = x0 + s / 2, x1 - s / 2
        _dashed(dl, x0, x1, cy, axis)
        span = (tb - ta) / (hi - lo)
        sx = ta + (y - lo) * span
        dl.add_rect(imgui.ImVec2(sx - s / 2, cy - s / 2), imgui.ImVec2(sx + s / 2, cy + s / 2),
                    ui.u32(CURVE), 0.0, 1.5)
    imgui.dummy(imgui.ImVec2(width, height))
    if imgui.is_item_hovered():
        st = settle(hz, damp)
        peak = max(y for _, y in pts)
        ui.tooltip(f"The spring at {hz:.2f} Hz, ζ {damp:.2f}: where a reading that jumps "
                   "from 0 to 1 is over time, the dashed line its target. "
                   + ("Undamped, it rings forever." if math.isinf(st) else
                      (f"It overshoots {100 * (peak - 1):.0f} % and " if peak > 1.005 else "It ")
                      + f"settles in about {st:.2f} s."))
