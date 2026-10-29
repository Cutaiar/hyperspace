"""A feel drawn — its shape, and the feel working live.

Wherever the panel sets a feel (motion.py) two plots sit with its knobs:
a route row's own feel (ui_routing._feel_line), a smooth modifier's in
GRAPH's side pane (ui_routing.modifier_block), the gamepad's stick feel
on the SYSTEM page (ui). `draw` lays them out, side by side or stacked.

**The shape** (`shape`) is what the setting does to any reading: how a
jump travels, against the reading dashed — motion.response, the feel's
own kernels.

  spring   a step: the reading jumps 0 → 1 and the spring carries it.
           Below bounce 0 it creeps, at 0 it lands, above it overshoots
           and rings.
  follow   a push and a let-go: the reading jumps to 1 and the attack
           carries it out, then drops back to rest and the release
           brings it home — one edge per knob.

It is static — a picture of the knobs, which moves only as they do;
what the stick is doing is the live plot's.

**The live plot** (`live`) scrolls the last few seconds, newest at the
right: the reading as it comes, dim, and after the feel, white — what
the Router hands on, read from the Router itself (`Router.felt_now` for
a row, the modifier's output lane for a smooth, `Router.felt_lanes` for
the pad). A gap is where the source was not live.

The panel samples as it draws (`sample`: one Trace per plot, held on the
panel), so a live plot fills while it is on screen and the Router keeps
nothing for it. The shape's time axis fits the feel (`window`, out to
where it has settled) and the live plot shows twice that (`span`), so a
lazy feel and a tight one both read.
Everything but `shape`, `live` and `draw` is pure.
"""

from __future__ import annotations

import math
from collections import deque
from functools import lru_cache

from imgui_bundle import imgui

from . import motion, ui
from .motion import Motion

SAMPLES = 64           # points along the shape
WINDOW_MIN = 0.05      # s, the shape's shortest time axis
RING_CYCLES = 6        # an undamped spring never settles: the shape shows this many periods
SPAN_MIN, SPAN_MAX = 2.0, 8.0     # s of history the live plot shows
MAX_SAMPLES = int(SPAN_MAX * 120)  # a trace's memory, at up to 120 frames a second
TRACES = "_feel_traces"            # the panel's dict of them
KEEP = 64              # past this many traces, the ones not sampled lately go
SHAPE_W = 140.0        # the shape beside the live plot, px at most
THUMB_W, THUMB_H = 64.0, 32.0      # a preset's shape in the spring picker
PICK_W = 250.0         # the spring picker's list, px at least: a thumbnail, a name, its knobs
DASH = 4.0             # px, the reading's dashes on the shape
FELT = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)
READ = imgui.ImVec4(0.92, 0.92, 0.92, 0.32)


# ---- the shape ----

def _edges(m: Motion) -> tuple[float, float]:
    """follow's shape: how long the push holds, how long after the let-go
    it runs — each to its edge's settle, and at least a third of the plot,
    so an instant edge still shows its plateau. Both instant: WINDOW_MIN
    halved."""
    out, home = motion.settle(m), motion.settle(m, home=True)
    if out + home <= 0:
        return WINDOW_MIN / 2, WINDOW_MIN / 2
    third = (out + home) / 3
    return max(out, third), max(home, third)


def let_go(m: Motion) -> float | None:
    """When the reading drops back to rest on the shape: follow's push
    holds until its attack has arrived. A spring's is a step: never."""
    return _edges(m)[0] if m.mode == "follow" else None


def window(m: Motion) -> float:
    """The shape's time axis, s: out to where the feel has settled. A
    spring: at most RING_CYCLES of its own period (undamped, it never
    settles)."""
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
def curve(m: Motion, n: int = SAMPLES,
          end: float | None = None) -> tuple[tuple[float, float], ...]:
    """(t, position) at n + 1 evenly spaced times across the window, or
    out to `end` (the spring picker's shared axis)."""
    w = window(m) if end is None else end
    return tuple((w * i / n, position(m, w * i / n)) for i in range(n + 1))


@lru_cache(maxsize=1)
def presets_axis() -> float:
    """The spring picker's one time axis: the slowest preset's window, so
    each thumbnail shows how soon its spring lands beside the others."""
    return max(window(Motion("spring", dur=d, bounce=b)) for d, b in motion.SPRINGS.values())


# ---- the live feel ----

def span(m: Motion) -> float:
    """Seconds of history the live plot shows: twice the shape's window,
    within SPAN_MIN … SPAN_MAX."""
    return min(max(2 * window(m), SPAN_MIN), SPAN_MAX)


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
    `key`, made on first sight. Traces not sampled for SPAN_MAX go once
    there are KEEP."""
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
    the pad's plots show that stick. The first on a tie, or all still."""
    best, at = -1.0, 0
    for i, tr in enumerate(traces):
        vals = [r for _, r, _ in tr.since(now, s) if math.isfinite(r)]
        rng = max(vals) - min(vals) if vals else 0.0
        if rng > best + 1e-6:
            best, at = rng, i
    return at


# ---- the tooltips ----

def _lands(m: Motion) -> str:
    if m.mode == "follow":
        return (f"It arrives in about {motion.settle(m):.2f} s and comes home in about "
                f"{motion.settle(m, home=True):.2f} s.")
    st = motion.settle(m)
    if math.isinf(st):
        return "With no damping it rings forever."
    peak = max(y for _, y in curve(m))
    over = f"It overshoots {100 * (peak - 1):.0f} % and " if peak > 1.005 else "It "
    return f"{over}settles in about {st:.2f} s."


def _named(m: Motion) -> str:
    d = m.describe()
    return d[0].upper() + d[1:]


def describe_shape(m: Motion) -> str:
    what = ("a reading pushed from rest to 1 and let go" if m.mode == "follow" else
            "a reading that jumps from 0 to 1")
    return f"{_named(m)}: {what}, dashed, and where the feel carries it. {_lands(m)}"


def describe_live(m: Motion, s: float) -> str:
    return (f"{_named(m)}, live: the last {s:.0f} s, newest at the right. Dim: the "
            "reading as it comes. White: after the feel — what the param gets. "
            f"{_lands(m)}")


# ---- drawing ----

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


def _shape_at(dl, m: Motion, x: float, y: float, width: float, height: float,
              end: float | None = None, label: bool = True) -> None:
    """The shape drawn into `dl` at (x, y): the axes, the reading dashed (a
    step, or a push and its let-go), the curve — out to `end` when given —
    and, with `label`, the axis' length."""
    axis, faint, line = ui.u32(ui.LINE), ui.u32(ui.FAINT), ui.u32(FELT)
    pad = 3.0
    x0, x1 = x + pad, x + width - pad
    y0, y1 = y + pad, y + height - pad
    pts = curve(m, end=end)
    w = pts[-1][0]
    lo = min(0.0, min(v for _, v in pts))
    hi = max(1.0, max(v for _, v in pts))
    lo, hi = lo - 0.06 * (hi - lo), hi + 0.06 * (hi - lo)

    def at(t: float, v: float) -> imgui.ImVec2:
        return imgui.ImVec2(x0 + (x1 - x0) * t / w, y1 - (y1 - y0) * (v - lo) / (hi - lo))

    base = at(0.0, 0.0).y
    dl.add_line(imgui.ImVec2(x0, y0), imgui.ImVec2(x0, y1), axis, 1.0)
    dl.add_line(imgui.ImVec2(x0, base), imgui.ImVec2(x1, base), axis, 1.0)
    g = let_go(m)
    _dashed(dl, at(0.0, 1.0), at(w if g is None else min(g, w), 1.0), axis)
    if g is not None and g < w:
        _dashed(dl, at(g, 1.0), at(g, 0.0), axis)
    dl.add_polyline([at(t, v) for t, v in pts], line, 1.5, 0)
    if not label:
        return
    text = f"{w:.2f} s" if w < 10 else f"{w:.0f} s"
    sz = imgui.calc_text_size(text)
    # bottom right: a spring has risen by then; a follow's release has come
    # home, so its label goes top right
    ly = base - sz.y - 1 if g is None else y0
    if sz.y < (y1 - y0) * 0.6 and sz.x < (x1 - x0) * 0.5:
        dl.add_text(imgui.ImVec2(x1 - sz.x, ly), faint, text)


def shape(m: Motion, width: float, height: float) -> None:
    """The feel's shape, `width` × `height` px at the cursor, as one item."""
    o = imgui.get_cursor_screen_pos()
    _shape_at(imgui.get_window_draw_list(), m, o.x, o.y, width, height)
    imgui.dummy(imgui.ImVec2(width, height))
    if imgui.is_item_hovered():
        ui.tooltip(describe_shape(m))


def spring_picker(label: str, m: Motion, width: float) -> str | None:
    """A spring preset combo, `width` wide, whose list draws each preset's
    shape beside its name and knobs, all on one time axis (`presets_axis`),
    so what is picked can be seen: snappy lands early, lazy late, wobbly
    rings. Closed, it reads the preset `m` is, or custom. Returns the name
    picked this frame, None while none was."""
    name = motion.spring_name(m.dur, m.bounce)
    picked = None
    imgui.set_next_window_size_constraints(imgui.ImVec2(max(PICK_W, width), 0.0),
                                           imgui.ImVec2(1e9, 1e9))
    imgui.set_next_item_width(width)
    if imgui.begin_combo(label, name or motion.CUSTOM):
        dl = imgui.get_window_draw_list()
        end = presets_axis()
        fh = imgui.get_text_line_height()
        for nm, (dur, bounce) in motion.SPRINGS.items():
            imgui.push_id(nm)
            o = imgui.get_cursor_screen_pos()
            if imgui.selectable("##pick", nm == name, 0, imgui.ImVec2(0.0, THUMB_H))[0]:
                picked = nm
            _shape_at(dl, Motion("spring", dur=dur, bounce=bounce), o.x, o.y, THUMB_W, THUMB_H,
                      end=end, label=False)
            tx = o.x + THUMB_W + 10
            dl.add_text(imgui.ImVec2(tx, o.y + THUMB_H / 2 - fh), ui.u32(ui.TEXT), nm)
            dl.add_text(imgui.ImVec2(tx, o.y + THUMB_H / 2), ui.u32(ui.FAINT),
                        f"{dur * 1000:.0f} ms · bounce {bounce * 100:.0f} %")
            imgui.pop_id()
        imgui.end_combo()
    return picked


def live(m: Motion, trace: Trace | None, width: float, height: float,
         title: str = "") -> None:
    """The feel working live, `width` × `height` px at the cursor, as one
    item; `title` in its top left."""
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
    newest = at(*pts[-1][::2]) if pts else None   # the newest felt value
    if newest is not None:
        dl.add_circle_filled(newest, 2.5, ui.u32(ui.RED))
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
        ui.tooltip(describe_live(m, s))


def draw(m: Motion, trace: Trace | None, width: float, height: float,
         title: str = "", stacked: bool = False) -> None:
    """Both plots in `width` × `height` px at the cursor, as one group (a
    feel that is off draws nothing): the shape left of the live plot (at
    most SHAPE_W, 40 % of the width), or `stacked` over it, half the
    height each; `title` on the live one."""
    if not m.on:
        return
    sp = imgui.get_style().item_spacing
    imgui.begin_group()
    if stacked:
        h = (height - sp.y) / 2
        shape(m, width, h)
        live(m, trace, width, h, title)
    else:
        w = min(SHAPE_W, width * 0.4)
        shape(m, w, height)
        imgui.same_line()
        live(m, trace, width - w - sp.x, height, title)
    imgui.end_group()
