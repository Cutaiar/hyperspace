"""A feel drawn live — the reading, and what the feel makes of it, over time.

Wherever the panel sets a feel (motion.py) a plot sits with its knobs: a
route row's own feel (ui_routing._feel_line), a smooth modifier's in
GRAPH's side pane (ui_routing.modifier_block), the gamepad's stick feel
on the SYSTEM page (ui). It scrolls the last few seconds, newest at the
right: the source's reading as it comes, dim, and the reading after the
feel, white — what the Router hands on, read from the Router itself
(`Router.felt_now` for a row, the modifier's output lane for a smooth,
`Router.felt_lanes` for the pad). Move the stick and the plot is the feel
working on it: a spring's overshoot and ring, follow's attack out and
release home. A gap is where the source was not live.

The panel samples as it draws (`sample`: one Trace per plot, held on the
panel), so a plot fills while it is on screen and the Router keeps
nothing for it. The span fits the feel — twice its settle time
(motion.settle), within SPAN_MIN … SPAN_MAX — so a lazy feel and a tight
one both have room to finish. `span`, `Trace` and `busiest` are pure;
`draw` is the one function that touches a draw list.
"""

from __future__ import annotations

import math
from collections import deque

from imgui_bundle import imgui

from . import motion, ui
from .motion import Motion

SPAN_MIN, SPAN_MAX = 2.0, 8.0     # s of history a plot shows
RING_CYCLES = 3        # an undamped spring never settles: this many of its periods
MAX_SAMPLES = int(SPAN_MAX * 120)  # a trace's memory, at up to 120 frames a second
TRACES = "_feel_traces"            # the panel's dict of them
KEEP = 64              # past this many traces, the ones not sampled lately go
FELT = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)
READ = imgui.ImVec4(0.92, 0.92, 0.92, 0.32)


def span(m: Motion) -> float:
    """Seconds of history for this feel: twice how long it takes to settle
    (follow: out and home), within SPAN_MIN … SPAN_MAX."""
    if m.mode == "follow":
        s = motion.settle(m) + motion.settle(m, home=True)
    elif m.mode == "spring":
        s = motion.settle(m)
        if math.isinf(s):
            s = RING_CYCLES * m.dur
    else:
        s = 0.0
    return min(max(2 * s, SPAN_MIN), SPAN_MAX)


class Trace:
    """One plot's samples, oldest first: (time, reading, felt), NaN where
    the source was not live."""

    __slots__ = ("pts",)

    def __init__(self):
        self.pts: deque = deque(maxlen=MAX_SAMPLES)

    def push(self, now: float, raw: float | None, felt: float | None) -> None:
        r = math.nan if raw is None else float(raw)
        f = math.nan if felt is None else float(felt)
        if self.pts and now <= self.pts[-1][0]:     # drawn twice in a frame: one sample
            self.pts[-1] = (now, r, f)
            return
        self.pts.append((now, r, f))
        while self.pts and self.pts[0][0] < now - SPAN_MAX:
            self.pts.popleft()

    def since(self, now: float, s: float) -> list[tuple[float, float, float]]:
        """The samples of the last `s` seconds."""
        return [p for p in self.pts if p[0] >= now - s]

    @property
    def last(self) -> float:
        return self.pts[-1][0] if self.pts else -math.inf


def sample(panel, key, raw: float | None, felt: float | None,
           now: float | None = None) -> Trace:
    """This frame's reading and felt value into the panel's trace for
    `key` (made on first sight). Traces not sampled for SPAN_MAX go once
    there are more than KEEP."""
    now = imgui.get_time() if now is None else now
    store = panel.__dict__.setdefault(TRACES, {})
    tr = store.get(key)
    if not isinstance(tr, Trace):                # new, or from before a hot reload
        if len(store) >= KEEP:
            for k in [k for k, t in store.items() if t.last < now - SPAN_MAX]:
                del store[k]
        tr = store[key] = Trace()
    tr.push(now, raw, felt)
    return tr


def busiest(traces: list[Trace], now: float, s: float) -> int:
    """Which trace moved most in the last `s` seconds (its reading's range):
    the pad's plot shows that stick. The first on a tie, or all still."""
    best, at = -1.0, 0
    for i, tr in enumerate(traces):
        vals = [r for _, r, _ in tr.since(now, s) if math.isfinite(r)]
        rng = max(vals) - min(vals) if vals else 0.0
        if rng > best + 1e-6:
            best, at = rng, i
    return at


def describe(m: Motion, s: float) -> str:
    """The plot's tooltip: the feel, what the two lines are, how it lands."""
    if m.mode == "follow":
        lands = (f"It arrives in about {motion.settle(m):.2f} s and comes home in about "
                 f"{motion.settle(m, home=True):.2f} s.")
    else:
        st = motion.settle(m)
        lands = ("With no damping it rings forever." if math.isinf(st) else
                 f"It settles in about {st:.2f} s.")
    return (f"{m.describe()[0].upper()}{m.describe()[1:]}, live: the last {s:.0f} s, newest "
            "at the right. Dim: the reading as it comes. White: after the feel — what "
            f"the param gets. {lands}")


def _lines(dl, pts: list[imgui.ImVec2 | None], col: int, thick: float) -> None:
    """A polyline broken at each None (a gap where nothing was live)."""
    run: list[imgui.ImVec2] = []
    for p in [*pts, None]:
        if p is not None:
            run.append(p)
            continue
        if len(run) > 1:
            dl.add_polyline(run, col, thick, 0)
        run = []


def draw(m: Motion, trace: Trace | None, width: float, height: float,
         title: str = "") -> None:
    """The live plot, `width` × `height` px at the cursor, as one item (a
    feel that is off draws nothing); `title` in its top left."""
    if not m.on:
        return
    o = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    axis, faint = ui.u32(ui.LINE), ui.u32(ui.FAINT)
    now = imgui.get_time()
    s = span(m)
    pad = 3.0
    x0, x1 = o.x + pad, o.x + width - pad
    y0, y1 = o.y + pad, o.y + height - pad
    pts = trace.since(now, s) if trace is not None else []
    vals = [v for _, r, f in pts for v in (r, f) if math.isfinite(v)]
    lo, hi = min([0.0, *vals]), max([1.0, *vals])
    lo, hi = lo - 0.06 * (hi - lo), hi + 0.06 * (hi - lo)

    def at(t: float, y: float) -> imgui.ImVec2 | None:
        if not math.isfinite(y):
            return None
        return imgui.ImVec2(x1 - (x1 - x0) * (now - t) / s,
                            y1 - (y1 - y0) * (y - lo) / (hi - lo))

    dl.add_rect(imgui.ImVec2(o.x, o.y), imgui.ImVec2(o.x + width, o.y + height), axis, 4.0)
    for level in (0.0, 1.0):                     # the reading's range, dotted faintly
        y = y1 - (y1 - y0) * (level - lo) / (hi - lo)
        x = x0
        while x < x1:
            dl.add_line(imgui.ImVec2(x, y), imgui.ImVec2(min(x + 2, x1), y), axis, 1.0)
            x += 6
    _lines(dl, [at(t, r) for t, r, _ in pts], ui.u32(READ), 1.0)
    _lines(dl, [at(t, f) for t, _, f in pts], ui.u32(FELT), 1.5)
    head = at(*pts[-1][::2]) if pts else None   # the newest felt value
    if head is not None:
        dl.add_circle_filled(head, 2.5, ui.u32(ui.RED))
    if title:
        dl.add_text(imgui.ImVec2(x0 + 2, y0), faint, title)
    if not vals:
        note = "not live"
        sz = imgui.calc_text_size(note)
        dl.add_text(imgui.ImVec2(o.x + (width - sz.x) / 2, o.y + (height - sz.y) / 2),
                    faint, note)
    label = f"{s:.0f} s"
    sz = imgui.calc_text_size(label)
    if sz.y < (y1 - y0) * 0.6:
        dl.add_text(imgui.ImVec2(x1 - sz.x - 2, y1 - sz.y), faint, label)
    imgui.dummy(imgui.ImVec2(width, height))
    if imgui.is_item_hovered():
        ui.tooltip(describe(m, s))
