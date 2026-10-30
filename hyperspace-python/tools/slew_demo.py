#!/usr/bin/env python3
"""Knob smoothing, shown headless (plan 18 WP2).

Builds the app's objects the way `app.main` does around the desk — the
library, the registry, the binding table with `desk.slew` declared before
the show lands, the router, the presets, a `MidiIO` over fake ports on a
clock the script moves, the `Undo` — with no window and no device, and
prints a transcript:

  1. a slow turn (one CC step every 50 ms for 2 s) on `camera.pan.x` and
     on `rot.rate.XY`, the base frame by frame with smoothing off and at
     80 ms: how many frames it moves on, the largest step, where it rests;
  2. a fast flick (50 CC steps in 5 frames);
  3. the ring messages sent back to the knob in both cases;
  4. a preset load in the middle of a glide;
  5. one turn at 80 ms as one undo step.

`--png` also draws the slow turn on `camera.pan.x` as base against time,
off and at 80 ms.

Every number is the adapter's own, read off the registry after each
`MidiIO.poll()`. It always runs on fresh temp homes of its own
(`HYPERSPACE_HOME` is set here, before anything reads it), each seeded
with the test corpus (`tests/conftest.py::seed`: TRIP is one of its
presets): it cannot touch ~/Hyperspace. What it cannot show is the desk: whether the APC40's
encoder re-bases cleanly with a value in flight, and how 80 ms feels.

  uv run python tools/slew_demo.py \\
      [--out docs/plans/assets/18-hand-and-knob-feel/slew-demo.txt] \\
      [--png docs/plans/assets/18-hand-and-knob-feel/slew.png]
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ["HYPERSPACE_HOME"] = str(Path(tempfile.mkdtemp(prefix="hyperspace-slew-demo-")) / "x")

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import mido
from conftest import seed

from hyperspace import apc40, lfo, routing, tempo, undo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.library import Library, Marks
from hyperspace.lookback import DreamState
from hyperspace.midi import MidiIO
from hyperspace.overlay import Output
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Bindings, Router, bindings_path
from hyperspace.view import ViewState

DT = 1 / 60
ON = routing.SLEW_DEFAULT_S
PAN, RATE = "camera.pan.x", "rot.rate.XY"
K_PAN, K_RATE = 0x30, 0x31              # track knobs 1 and 2, given to the two params
lines: list[str] = []


def say(text: str = "") -> None:
    lines.append(text)
    print(text)


class FakeIn:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)


class FakeOut:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


def cc(control: int, value: int) -> mido.Message:
    return mido.Message("control_change", channel=0, control=control, value=value)


def build(seconds: float) -> SimpleNamespace:
    """The host's objects around the desk, in `app.main`'s order, on a
    fresh home, with knob smoothing at `seconds` and K1 / K2 on the pan
    and on the XY rate."""
    home = Path(tempfile.mkdtemp(prefix="hyperspace-slew-demo-")) / "home"
    os.environ["HYPERSPACE_HOME"] = str(home)
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=True)
    view = ViewState()
    seed(home)
    lib = Library(home, period=0.0)
    reg = build_registry(view, control, audio, lib.project, dream=DreamState(), fx=FxState())
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    r = SimpleNamespace(t=100.0)
    clock = tempo.Clock(now=lambda: r.t)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(seed=1), clock)
    Output(None, None).register(reg)
    table = Bindings.load(bindings_path(home), legacy_midi=None)
    routing.register_desk(reg, table)       # before attach, as app._desk_table does
    lib.attach(reg)
    router = Router(reg, table)
    presets = Presets(lib, reg, router)
    inp, out = FakeIn(), FakeOut()
    midi = MidiIO(reg, table, inp=inp, out=out, clock=lambda: r.t)
    lib.project.load_startup()
    u = undo.Undo(reg, table, marks=Marks(lib), tag=lambda: tuple(s.name for s in chain.spec),
                  on_restore=router.sync_macros)
    undo.install(u)
    r.__dict__.update(lib=lib, reg=reg, table=table, presets=presets, midi=midi, inp=inp,
                      out=out, undo=u)
    give_knobs(r)
    reg["desk.slew"].set(seconds)
    for pid in (PAN, RATE):
        reg[pid].set_norm(64 / 127)         # the knob at its middle: 0 units, 0×
    frames(r, 40)                           # the rings re-base the knobs; the undo settles
    u.clear()
    out.sent.clear()
    return r


def give_knobs(r) -> None:
    desk = [b.to_json() for b in r.table.desk()
            if not (b.kind == "cc" and b.number in (K_PAN, K_RATE))]
    desk += [{"source": f"cc:0:{n}", "target": pid, "op": "abs", "feedback": "ring"}
             for n, pid in ((K_PAN, PAN), (K_RATE, RATE))]
    r.table.set_desk(desk)


def frames(r, n: int = 1) -> None:
    """`n` frames in app.frame's order, as far as the desk is concerned."""
    for _ in range(n):
        r.t += DT
        r.midi.poll()
        r.undo.tick(r.t)
        r.reg.apply()


def play(r, pid: str, knob: int, schedule: dict[int, list[int]], n: int) -> list[float]:
    """`n` frames, `schedule[frame]` the CC values that arrive on it; the
    param's base after each frame."""
    p, out = r.reg[pid], []
    for k in range(n):
        r.inp.queue += [cc(knob, v) for v in schedule.get(k, [])]
        frames(r)
        out.append(p.base)
    return out


def rings(r, knob: int) -> list[int]:
    return [m.value for m in r.out.sent if m.type == "control_change" and m.control == knob]


def moves(bases: list[float], start: float) -> tuple[int, float]:
    steps = [abs(b - a) for a, b in zip([start, *bases], bases, strict=False)]
    return sum(s > 1e-9 for s in steps), max(steps)


SLOW = {3 * k: [65 + k] for k in range(40)}             # a CC step every 50 ms for 2 s
SLOW_N = 150
FLICK = {k: list(range(65 + 10 * k, 75 + 10 * k)) for k in range(5)}    # 50 steps in 5 frames
FLICK_N = 24


def slow_turn(pid: str, knob: int, unit: str, fmt: str) -> dict[float, list[float]]:
    p0 = None
    got: dict[float, list[float]] = {}
    sent: dict[float, list[int]] = {}
    for seconds in (0.0, ON):
        r = build(seconds)
        p0 = r.reg[pid].base
        got[seconds] = play(r, pid, knob, SLOW, SLOW_N)
        sent[seconds] = rings(r, knob)
        assert not r.midi._slews
    say(f"   {pid}: one detent is {abs(got[0.0][0] - p0):{fmt}} {unit}")
    say(f"   {'frame':>5} {'ms':>5} {'CC':>4}   {'off':>10}   {f'{ON * 1000:.0f} ms':>10}")
    for k in range(13):
        v = SLOW.get(k, [""])[0]
        say(f"   {k:5d} {k * DT * 1000:5.0f} {v!s:>4}   {got[0.0][k]:10{fmt}}   "
            f"{got[ON][k]:10{fmt}}")
    say("   …")
    for seconds in (0.0, ON):
        n, big = moves(got[seconds], p0)
        name = "off" if not seconds else f"{seconds * 1000:.0f} ms"
        say(f"   {name:>6}: the base moves on {n:3d} of {SLOW_N} frames, largest step "
            f"{big:{fmt}} {unit}, rests at {got[seconds][-1]:{fmt}} {unit}")
    assert got[0.0][-1] == got[ON][-1], "the two rest on different values"
    say(f"   the rest values are identical: {got[0.0][-1] == got[ON][-1]}")
    say(f"   ring messages sent: {len(sent[0.0])} and {len(sent[ON])}, identical: "
        f"{sent[0.0] == sent[ON]}  (first six: {sent[ON][:6]})")
    assert sent[0.0] == sent[ON]
    say()
    return got


def flick() -> None:
    got, sent, landed = {}, {}, {}
    for seconds in (0.0, ON):
        r = build(seconds)
        p = r.reg[PAN]
        p0, span = p.base, p.hi - p.lo
        got[seconds] = play(r, PAN, K_PAN, FLICK, FLICK_N)
        sent[seconds] = rings(r, K_PAN)
        n, big = moves(got[seconds], p0)
        landed[seconds] = next(k for k, b in enumerate(got[seconds]) if b == got[seconds][-1])
        name = "off" if not seconds else f"{seconds * 1000:.0f} ms"
        say(f"   {name:>6}: moves on {n:2d} frames, largest frame-to-frame move "
            f"{big / span * 100:4.1f} % of the throw, at rest from frame {landed[seconds]} "
            f"({landed[seconds] * DT * 1000:.0f} ms) at {got[seconds][-1]:.2f} units")
    assert got[0.0][-1] == got[ON][-1] and sent[0.0] == sent[ON]
    say(f"   the last message arrives on frame 4 ({4 * DT * 1000:.0f} ms); the glide lands "
        f"{(landed[ON] - 4) * DT * 1000:.0f} ms after it (the first frame at or after "
        f"{ON * 1000:.0f} ms)")
    say(f"   the rest values are identical: True; ring messages identical: "
        f"{sent[0.0] == sent[ON]} ({len(sent[ON])} sent)")
    say()


def load_mid_glide() -> None:
    r = build(ON)
    reg, dim = r.reg, r.reg["output.dim"]
    pan = reg[PAN]
    r.inp.queue.append(cc(apc40.CC_XFADE, 127))         # the crossfader at full: caught
    frames(r, 10)
    r.inp.queue += [cc(K_PAN, 127), cc(apc40.CC_XFADE, 0)]
    frames(r, 2)
    say(f"   2 frames into a turn to the end and a fade to black: pan {pan.base:.2f} units, "
        f"dim {dim.base:.3f}; gliding: {sorted(r.midi._slews)}")
    r.presets.load("TRIP")
    loaded = pan.base
    say(f"   load TRIP: pan is {loaded:.2f} units (the preset's)")
    frames(r)
    say(f"   next frame: pan {pan.base:.2f} units, dim {dim.base:.3f}; gliding: "
        f"{sorted(r.midi._slews)}")
    frames(r, 20)
    xfade = next(b for b in r.table.midi() if b.target == "output.dim")
    say(f"   20 frames on: pan {pan.base:.2f} units (the load's value stands), dim "
        f"{dim.base:.3f} (the session's: it arrived), the crossfader still caught: "
        f"{xfade.caught}")
    assert pan.base == loaded and dim.base == 0.0 and xfade.caught
    say()


def one_step() -> None:
    r = build(ON)
    p = r.reg[PAN]
    was = p.base
    play(r, PAN, K_PAN, SLOW, 120)
    say(f"   after the 2 s turn: {len(r.undo.stack)} step on the stack, still open "
        f"(label {r.undo.stack[0].label!r})")
    frames(r, 40)
    say(f"   {undo.SETTLE_S * 1000:.0f} ms of quiet after the landing: "
        f"{[s.label for s in r.undo.stack]}")
    assert len(r.undo.stack) == 1
    r.undo.undo()
    frames(r, 20)
    say(f"   undo: pan back at {p.base:.2f} units (was {was:.2f}); nothing glides on: "
        f"{not r.midi._slews}")
    assert abs(p.base - was) < 1e-6
    say()


# ---------------------------------------------------------------- the plot

def plot(path: Path, got: dict[float, list[float]]) -> None:
    """Base against time for the slow turn on camera.pan.x, off and at
    80 ms: two lines, one axis, drawn with PIL at 2× and scaled down."""
    from PIL import Image, ImageDraw, ImageFont

    s = 2
    w, h = 920 * s, 440 * s
    left, right, top, bottom = 76 * s, 150 * s, 64 * s, 52 * s
    surface, ink, soft, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    colour = {0.0: "#2a78d6", ON: "#eb6834"}
    label = {0.0: "off: a detent at a time", ON: f"{ON * 1000:.0f} ms glide"}
    img = Image.new("RGB", (w, h), surface)
    d = ImageDraw.Draw(img)

    def font(px):
        return ImageFont.load_default(size=px * s)

    n = 66                                  # the first 1.1 s: the staircase is legible
    t_max = n * DT * 1000
    lo = min(min(v[:n]) for v in got.values())
    hi = max(max(v[:n]) for v in got.values())
    lo, hi = min(lo, 0.0), (int(hi / 2) + 1) * 2

    def x(ms):
        return left + (w - left - right) * ms / t_max

    def y(v):
        return h - bottom - (h - top - bottom) * (v - lo) / (hi - lo)

    d.text((left, 16 * s), "A slow knob turn on camera.pan.x: the base, frame by frame",
           font=font(17), fill=ink)
    d.text((left, 38 * s), "one CC step every 50 ms; both rest on the same detents",
           font=font(12), fill=soft)
    for v in range(0, int(hi) + 1, 2):
        d.line([(left, y(v)), (w - right, y(v))], fill=grid, width=s)
        d.text((left - 8 * s, y(v)), f"{v}", font=font(12), fill=soft, anchor="rm")
    for ms in range(0, int(t_max) + 1, 200):
        d.text((x(ms), h - bottom + 8 * s), f"{ms}", font=font(12), fill=soft, anchor="ma")
    d.text((left - 8 * s, top - 16 * s), "units", font=font(12), fill=soft, anchor="rm")
    d.text((w - right, h - bottom + 26 * s), "ms", font=font(12), fill=soft, anchor="ra")
    d.line([(left, h - bottom), (w - right, h - bottom)], fill=soft, width=s)
    for seconds, vals in got.items():
        pts = [(x(0), y(0.0))]
        for k, v in enumerate(vals[:n]):
            t = (k + 1) * DT * 1000
            if seconds == 0.0:
                pts.append((x(t), pts[-1][1]))          # held until the frame: a staircase
            pts.append((x(t), y(v)))
        d.line(pts, fill=colour[seconds], width=2 * s, joint="curve")
    # direct labels at the right end, the series colour as a mark beside ink text
    ends = {sec: y(vals[n - 1]) for sec, vals in got.items()}
    gap = 18 * s
    if abs(ends[0.0] - ends[ON]) < gap:
        mid = (ends[0.0] + ends[ON]) / 2
        first = min(ends, key=ends.get)
        ends = {sec: mid + (-gap / 2 if sec == first else gap / 2) for sec in ends}
    for seconds, yy in ends.items():
        x0 = w - right + 10 * s
        d.line([(x0, yy), (x0 + 16 * s, yy)], fill=colour[seconds], width=2 * s)
        d.text((x0 + 22 * s, yy), label[seconds].split(":")[0], font=font(12), fill=ink,
               anchor="lm")
    # the legend, top left of the plot
    for i, seconds in enumerate(got):
        yy = top + 6 * s + i * 20 * s
        d.line([(left + 12 * s, yy), (left + 34 * s, yy)], fill=colour[seconds], width=2 * s)
        d.text((left + 42 * s, yy), label[seconds], font=font(12), fill=ink, anchor="lm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((w // s, h // s), Image.LANCZOS).save(path)


def main(argv: list[str]) -> None:
    def arg(flag):
        return Path(argv[argv.index(flag) + 1]) if flag in argv else None

    say("Knob smoothing (plan 18 WP2): desk.slew, off and at "
        f"{ON * 1000:.0f} ms (the app's default). 60 frames a second.")
    say()
    say("1. A slow turn: one CC step every 50 ms for 2 s (CC 64 → 104), the base per frame")
    pan = slow_turn(PAN, K_PAN, "units", ".3f")
    slow_turn(RATE, K_RATE, "×", ".3f")
    say("2. A fast flick on camera.pan.x: 50 CC steps in 5 frames (CC 64 → 114)")
    flick()
    say("3. The rings: in 1 and 2 the CC sent back to the knob is the same list, off and on —")
    say("   during a glide the ring carries the knob's own target, never the base in flight.")
    say()
    say("4. A preset load in the middle of a glide")
    load_mid_glide()
    say(f"5. One turn is one undo step at {ON * 1000:.0f} ms")
    one_step()
    say("Not shown here: the APC40 itself. Whether its encoder re-bases cleanly with a")
    say("value in flight, and how 80 ms feels under the hand, are for the machine.")
    out, png = arg("--out"), arg("--png")
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n")
    if png is not None:
        plot(png, pan)


if __name__ == "__main__":
    main(sys.argv[1:])
