"""Easing, and the per-widget animation store an immediate-mode UI needs.

shadcn animates on `transition-all 150ms cubic-bezier(0.4, 0, 0.2, 1)` — the
Tailwind `ease-in-out` curve. Dear ImGui holds no per-widget state between
frames, so a hover that is supposed to take 150ms has nowhere to live. This
module is that nowhere: a dict keyed by widget id, stepped once a frame.

Per REVIEW.md, per-frame code does no scans of a whole history and no cache
rebuilds — so `step` is O(live widgets) and drops anything that stopped being
drawn, rather than growing without bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# cubic-bezier(0.4, 0, 0.2, 1): P0 (0,0), P1 (0.4,0), P2 (0.2,1), P3 (1,1)
STANDARD = (0.4, 0.0, 0.2, 1.0)
DURATION = 0.15          # seconds, shadcn's `duration-150`


def _bez(a: float, b: float, t: float) -> float:
    """One axis of a cubic Bezier with P0=0 and P3=1."""
    u = 1.0 - t
    return 3.0 * u * u * t * a + 3.0 * u * t * t * b + t * t * t


def _bez_prime(a: float, b: float, t: float) -> float:
    u = 1.0 - t
    return (3.0 * u * u * a
            + 6.0 * u * t * (b - a)
            + 3.0 * t * t * (1.0 - b))


def cubic_bezier(x: float, curve=STANDARD) -> float:
    """y for a given x on a CSS cubic-bezier, x and y in [0, 1].

    Newton-Raphson on X(t) = x, falling back to bisection where the
    derivative is flat (which it is at both ends of the standard curve).
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    x1, y1, x2, y2 = curve
    t = x
    for _ in range(8):
        err = _bez(x1, x2, t) - x
        if abs(err) < 1e-6:
            return _bez(y1, y2, t)
        d = _bez_prime(x1, x2, t)
        if abs(d) < 1e-6:
            break
        t -= err / d
    lo, hi = 0.0, 1.0
    for _ in range(32):
        t = (lo + hi) / 2.0
        if _bez(x1, x2, t) < x:
            lo = t
        else:
            hi = t
    return _bez(y1, y2, t)


@dataclass
class _Track:
    value: float
    target: float
    elapsed: float
    start: float
    seen: int


class Anim:
    """Per-id eased values.

    Call `to(id, target)` while drawing — it returns the value for *this*
    frame — then `step(dt)` once at the end of the frame.
    """

    def __init__(self, duration: float = DURATION, curve=STANDARD) -> None:
        self.duration = duration
        self.curve = curve
        self._t: dict[str, _Track] = {}
        self._frame = 0
        # Per-widget state that is NOT eased, but still has to survive from
        # one frame to the next: a slider's value while Shift-fine is
        # overriding the stock widget, which sliders are in Ctrl+click text
        # entry, and how long each id has been hovered without a break.
        #
        # It lives here because `Anim` is the one object the kit already
        # threads across frames - interact.Ui is rebuilt every frame
        # (dashboard.py:569), so anything kept on the Ui is lost immediately.
        # That is not a hypothetical: the tooltip's hover clock was reset on
        # every frame and the tooltip could never reach its delay.
        # (mostly dicts by widget id; also the frame's "dt" and the "kbd" flag)
        self.store: dict[str, Any] = {"drag": {}, "texting": {}, "hover": {}}

    def to(self, key: str, target: float) -> float:
        tr = self._t.get(key)
        if tr is None:
            # first sight of a widget is not a transition: start settled, or
            # every hover state would fade in when the page first draws
            self._t[key] = _Track(target, target, self.duration, target,
                                  self._frame)
            return target
        tr.seen = self._frame
        if target != tr.target:
            tr.start = tr.value
            tr.target = target
            tr.elapsed = 0.0
        return tr.value

    def step(self, dt: float) -> None:
        self._frame += 1
        dead = []
        for k, tr in self._t.items():
            if tr.elapsed < self.duration:
                tr.elapsed = min(tr.elapsed + dt, self.duration)
                f = cubic_bezier(tr.elapsed / self.duration, self.curve)
                tr.value = tr.start + (tr.target - tr.start) * f
            elif self._frame - tr.seen > 120:
                # not drawn for two seconds at 60fps: let it go, so the store
                # stays O(live widgets)
                dead.append(k)
        for k in dead:
            del self._t[k]

    def settled(self) -> bool:
        return all(tr.elapsed >= self.duration for tr in self._t.values())

    def __len__(self) -> int:
        return len(self._t)


def mix(a, b, f: float):
    """Blend two RGBA tuples the way a browser does: PREMULTIPLIED.

    Interpolating straight RGBA is wrong whenever one end is transparent.
    `transparent` is transparent *black*, so a fade from it to an opaque
    colour drags the hue through black and the widget visibly darkens before
    it lightens — measured as a dip to 20 on a sidebar whose rest value is 23
    and whose hover value is 38.

    Premultiplying removes that: a fully transparent endpoint contributes no
    colour at all, only alpha, which is what CSS does.
    """
    ar, ag, ab, aa = a
    br, bg, bb, ba = b
    pa = (ar * aa, ag * aa, ab * aa, aa)
    pb = (br * ba, bg * ba, bb * ba, ba)
    r, g, bl, al = (x + (y - x) * f for x, y in zip(pa, pb))
    if al <= 1e-6:
        return (0.0, 0.0, 0.0, 0.0)
    return (r / al, g / al, bl / al, al)


def over(src, dst):
    """Composite `src` over `dst`, premultiplied - the Porter-Duff OVER.

    The companion to `mix`. `mix` blends two colours by a factor, which is
    what a transition does; this stacks one on top of another, which is what
    PAINTING does, and the kit needs it to fold CSS's group opacity into
    flat colours.

    `opacity` on an element is not the same as alpha on each of its layers.
    CSS composites the element's own fill and border FIRST and applies the
    opacity to that composite; scaling both layers' alpha instead leaves the
    fill showing through a semi-transparent border that should have covered
    it. On a disabled Input that came out as 2 levels across the border -
    small, but it was the only thing in the gallery above 1.
    """
    sr, sg, sb, sa = src
    dr, dg, db, da = dst
    oa = sa + da * (1.0 - sa)
    if oa <= 1e-6:
        return (0.0, 0.0, 0.0, 0.0)
    f = lambda cs, cd: (cs * sa + cd * da * (1.0 - sa)) / oa
    return (f(sr, dr), f(sg, dg), f(sb, db), oa)
