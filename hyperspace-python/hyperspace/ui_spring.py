"""A spring feel drawn as a spring — a coil, a damper and a mass.

Wherever the panel sets a spring (a route row's own feel, ui_routing; the
gamepad's stick feel on the SYSTEM page, ui) a small picture sits beside
its knobs: a wall on the left, a coil and a dashpot in parallel from it
to a red mass, and the mass plucked and let go over and over. The pluck
is motion.spring's own closed form, at the knobs' real Hz and damping
ratio, so what the mass does is what a reading does under that feel: a
tight spring snaps back, a lazy one swings slowly, below ζ 1 it rings,
above it creeps home. The coil's wire thickens with the frequency (the
stiffness); the damper's piston grows with the damping ratio.

The geometry is pure (`pose`, `period`, `coil`) so tests read it with no
imgui; `draw` is the one function that touches a draw list. No state:
the pluck's phase is the imgui clock modulo `period`.
"""

from __future__ import annotations

import math

from imgui_bundle import imgui

from . import motion, ui

TURNS = 7              # the coil's turns
COIL_SAMPLES = 14      # points per turn
SWING = 0.28           # the pluck: the mass starts this fraction of the width out
REST_AT = 0.62         # the mass's rest, a fraction of the width from the wall
MASS_W = 0.13          # the mass, a fraction of the width
HOLD = 0.35            # s the mass is held out before each release
PERIOD_MIN, PERIOD_MAX = 1.2, 4.0    # s, one pluck to the next


def settle(hz: float, damp: float) -> float:
    """Seconds for a released spring to come within ~2 % of rest: the
    slowest root's envelope, e^(−rt) = 0.02 at rt ≈ 4."""
    if hz <= 0:
        return 0.0
    w = 2 * math.pi * hz
    z = max(damp, 0.0)
    if z <= 1e-6:
        return math.inf
    r = z * w if z <= 1 else w * (z - math.sqrt(z * z - 1))
    return 4.0 / r


def period(hz: float, damp: float) -> float:
    """One pluck to the next, s: the hold, then long enough to see it
    settle, within PERIOD_MIN … PERIOD_MAX."""
    return min(max(HOLD + settle(hz, damp), PERIOD_MIN), PERIOD_MAX)


def pose(t: float, hz: float, damp: float) -> float:
    """The mass's displacement at clock time t, 1 fully plucked, 0 at
    rest, negative past it (a ringing spring compresses): held at 1 for
    HOLD, then released — motion.spring stepped once over the whole time,
    exact in closed form."""
    s = t % period(hz, damp) - HOLD
    if s <= 0:
        return 1.0
    x, _ = motion.spring(1.0, 0.0, 0.0, s, hz, damp)
    return x


def coil(x0: float, x1: float, cy: float, amp: float,
         turns: int = TURNS) -> list[tuple[float, float]]:
    """A coil from x0 to x1 about the line y = cy, drawn as a helix seen
    from the side: a sine across, and each turn swung back along the axis
    and forward again so it reads as a loop. Straight leads of a turn's width at both ends."""
    lead = min(abs(x1 - x0) * 0.08, 6.0)
    a, b = x0 + lead, x1 - lead
    n = turns * COIL_SAMPLES
    pitch = (b - a) / turns
    pts = [(x0, cy), (a, cy)]
    for i in range(1, n):
        u = i / n
        th = u * turns * math.tau
        lean = 0.45 * pitch * (math.cos(th) - 1)   # 0 at the turn's ends, back mid-loop
        pts.append((a + (b - a) * u + lean, cy - amp * math.sin(th)))
    pts += [(b, cy), (x1, cy)]
    return pts


def _wire(hz: float) -> float:
    """The coil's line width from its frequency, log-spaced over the knob."""
    lo, hi = math.log(motion.HZ_MIN), math.log(motion.HZ_MAX)
    u = (math.log(min(max(hz, motion.HZ_MIN), motion.HZ_MAX)) - lo) / (hi - lo)
    return 1.0 + 1.8 * u


def draw(hz: float, damp: float, width: float, height: float | None = None,
         tip: bool = True) -> None:
    """The picture, `width` × `height` px at the cursor (height: the frame
    height), as one item; its tooltip says what it shows."""
    h = imgui.get_frame_height() if height is None else height
    o = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    line, text = ui.u32(ui.LINE), ui.u32(ui.DIM)
    x_wall = o.x + 3
    y0, y1 = o.y + 2, o.y + h - 2
    # the wall: a post and its hatching
    dl.add_line(imgui.ImVec2(x_wall, y0), imgui.ImVec2(x_wall, y1), text, 1.5)
    k = y0
    while k < y1 - 2:
        dl.add_line(imgui.ImVec2(x_wall, k + 4), imgui.ImVec2(x_wall - 3, k + 1), line, 1.0)
        k += 4
    span = width - 6
    mw = max(span * MASS_W, 8.0)
    xm = x_wall + span * (REST_AT + SWING * pose(imgui.get_time(), hz, damp)) - mw / 2
    xm = min(max(xm, x_wall + 10), o.x + width - mw - 1)
    # the spring above the middle, the damper below it
    cy_s, cy_d = y0 + (y1 - y0) * 0.32, y0 + (y1 - y0) * 0.78
    amp = (y1 - y0) * 0.24
    pts = [imgui.ImVec2(px, py) for px, py in coil(x_wall, xm, cy_s, amp)]
    dl.add_polyline(pts, text, _wire(hz), 0)
    # the dashpot: a cylinder off the wall, a rod from the mass, a piston
    # whose face grows with the damping ratio (none at ζ 0)
    cyl0, cyl1 = x_wall + span * 0.12, x_wall + span * 0.38
    ch = (y1 - y0) * 0.18
    dl.add_line(imgui.ImVec2(x_wall, cy_d), imgui.ImVec2(cyl0, cy_d), text, 1.0)
    dl.add_line(imgui.ImVec2(cyl0, cy_d - ch), imgui.ImVec2(cyl0, cy_d + ch), text, 1.0)
    dl.add_line(imgui.ImVec2(cyl0, cy_d - ch), imgui.ImVec2(cyl1, cy_d - ch), text, 1.0)
    dl.add_line(imgui.ImVec2(cyl0, cy_d + ch), imgui.ImVec2(cyl1, cy_d + ch), text, 1.0)
    z = min(max(damp, 0.0), motion.DAMP_MAX) / motion.DAMP_MAX
    if z > 0:
        dl.add_rect_filled(imgui.ImVec2(cyl0 + 1, cy_d - ch + 1),
                           imgui.ImVec2(cyl1, cy_d + ch - 1),
                           ui.u32(imgui.ImVec4(1, 1, 1, 0.06 + 0.22 * z)))
    rod = x_wall + span * REST_AT - mw / 2 - (cyl0 + cyl1) / 2   # at rest: mid-cylinder
    xp = min(max(xm - rod, cyl0 + 3), cyl1 - 1)
    dl.add_line(imgui.ImVec2(xp, cy_d - ch * (0.3 + 0.7 * z)),
                imgui.ImVec2(xp, cy_d + ch * (0.3 + 0.7 * z)), text, 2.0)
    dl.add_line(imgui.ImVec2(xp, cy_d), imgui.ImVec2(xm, cy_d), text, 1.0)
    # the mass
    dl.add_rect_filled(imgui.ImVec2(xm, y0), imgui.ImVec2(xm + mw, y1), ui.u32(ui.RED), 3.0)
    imgui.dummy(imgui.ImVec2(width, h))
    if tip and imgui.is_item_hovered():
        s = settle(hz, damp)
        ui.tooltip(f"The spring at {hz:.2f} Hz, ζ {damp:.2f}, plucked and let go: "
                   + ("it rings and never settles" if math.isinf(s) else
                      f"{'rings, then ' if damp < 1 else ''}settles in about {s:.2f} s")
                   + ". The coil thickens with the frequency, the damper's piston "
                     "with the damping.")
