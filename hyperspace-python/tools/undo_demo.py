#!/usr/bin/env python3
"""Undo and the trash, shown headless (plan 15 WP1).

Builds the app's objects the way `app.main` does — library, registry,
hands' settings, clock and LFOs, the router over the home's
bindings.json, the presets, a Learn, a MidiIO over fake ports, a HandsIO
over synthetic hands, the startup preset, then the `Undo` — with no
window, and prints a transcript: a slider drag, a knob sweep, a hand
moving, a preset load, Ctrl+Z down the stack with the status line the
footer shows, a redo, a save over a preset and a delete with the trash
listed, and what `Undo.tick` costs a frame.

It always runs on a fresh temp home of its own (`HYPERSPACE_HOME` is set
here, before anything reads it): it cannot touch ~/Hyperspace.

  uv run python tools/undo_demo.py [--out docs/plans/assets/15-safety-net/undo-demo.txt]
"""

from __future__ import annotations

import importlib.util
import math
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

HOME = Path(tempfile.mkdtemp(prefix="hyperspace-undo-demo-")) / "home"
os.environ["HYPERSPACE_HOME"] = str(HOME)
# pyGLFW and imgui_bundle each ship a libglfw; point pyGLFW at imgui_bundle's
# before it loads, as app.py does (tools/undo_shot.py opens a hidden window)
if "PYGLFW_LIBRARY" not in os.environ:
    _spec = importlib.util.find_spec("imgui_bundle")
    _dylib = Path(_spec.origin).parent / "libglfw.3.dylib" if _spec and _spec.origin else None
    if _dylib is not None and _dylib.exists():
        os.environ["PYGLFW_LIBRARY"] = str(_dylib)

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "tests"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import glfw
import mido
from fake_hands import hand

from hyperspace import hands, lfo, preset, tempo, undo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.fx import FxState
from hyperspace.ghost import GhostState
from hyperspace.hands.core import features
from hyperspace.learn import Learn
from hyperspace.library import PRESETS, TRASH, Library, Marks
from hyperspace.lookback import DreamState
from hyperspace.midi import MidiIO
from hyperspace.overlay import Output
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Bindings, Router, bindings_path
from hyperspace.view import ViewState

DT = 1 / 60
lines: list[str] = []


def say(text: str = "") -> None:
    lines.append(text.replace(str(HOME), "<home>"))
    print(lines[-1])


class Ports:
    """A MIDI port pair nobody is plugged into: `queue` is what the desk sends."""

    def __init__(self):
        self.queue, self.sent = [], []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)

    def send(self, msg):
        self.sent.append(msg)


class Keys:
    """`app.Keys` as `Router.keys` reads it: one press, with its modifiers."""

    def __init__(self, key: int, *mods: str):
        self.key, self.mods = key, set(mods)

    def pressed(self, key):
        hit, self.key = key == self.key, None if key == self.key else self.key
        return hit

    def shift(self):
        return "SHIFT" in self.mods

    def super(self):
        return "SUPER" in self.mods

    def control(self):
        return "CONTROL" in self.mods


class Tracker:
    """`LeapSource.latest()` over synthetic hands."""

    status, on = "tracking", True

    def __init__(self, clock):
        self.clock, self.seq, self.hands = clock, 0, {}

    def put(self, *hs):
        self.seq += 1
        self.hands = {h.type.name.lower(): (features(h), h.confidence) for h in hs}

    def latest(self):
        return self.seq, self.clock(), self.hands

    def close(self):
        pass


def boot() -> SimpleNamespace:
    """app.main's construction order, without the windows."""
    r = SimpleNamespace(t=0.0)
    chain = Analyzer(Analyser())
    control = Control(chain)
    # no audio device: what the registry and the panel read off the engine
    audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
    view = ViewState()
    lib = Library(HOME, period=0.0)
    reg = build_registry(view, control, audio, lib.project, dream=DreamState(), fx=FxState(),
                         ghost=GhostState())
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    lib.on_load("band", control.scene_loaded)
    control.library = lib
    settings = hands.HandSettings.from_config({})
    hands.register(reg, settings)
    clock, lfos = tempo.Clock(now=lambda: r.t), lfo.LFOs(seed=1)
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    output = Output(None, None)                       # no window: its params only
    output.register(reg)
    lib.attach(reg)
    router = Router(reg, Bindings.load(bindings_path(HOME), legacy_midi=None))
    presets = Presets(lib, reg, router)
    preset.migrate_home(lib, router)
    learn = Learn(reg, router.table, lane=router.lane)
    ports = Ports()
    midi = MidiIO(reg, router.table, inp=ports, out=ports, learner=learn)
    tracker = Tracker(lambda: r.t)
    hands_io = hands.HandsIO(settings, {"out": ""}, source=tracker, clock=lambda: r.t)
    lib.project.load_startup()
    u = undo.Undo(reg, router.table, marks=Marks(lib),
                  tag=lambda: tuple(s.name for s in chain.spec),
                  on_restore=router.sync_macros)
    undo.install(u)
    r.__dict__.update(lib=lib, reg=reg, view=view, chain=chain, router=router, presets=presets,
                      clock=clock, lfos=lfos, midi=midi, ports=ports, tracker=tracker,
                      hands_io=hands_io, learn=learn, undo=u, cost=[], control=control,
                      audio=audio, settings=settings, output=output)
    return r


def frames(r, n: int = 1, *, keys=None, hands_at=None) -> None:
    """`n` frames in app.frame's order (no windows): the clock, the key
    rows, the MIDI poll, the macros, `undo.tick`, the hands, the LFOs, the
    modulation pass, `reg.apply`, the integrator."""
    for _ in range(n):
        r.t += DT
        r.clock.tick(r.t)
        if keys is not None:
            r.router.keys(keys)
            keys = None
        r.midi.poll()
        r.router.follow_macros()
        t0 = time.perf_counter()
        r.undo.tick(r.t)
        r.cost.append(time.perf_counter() - t0)
        if hands_at is not None:
            r.tracker.put(*hands_at(r.t))
        r.hands_io.poll(DT, r.learn, r.router)
        r.lfos.step(DT, r.t, r.clock)
        r.lfos.publish(r.router)
        r.router.modulate(None)
        r.reg.apply()
        r.view.integrate(DT)


def settle(r) -> None:
    frames(r, math.ceil(undo.SETTLE_S / DT) + 3)


def stack(r) -> None:
    u = r.undo
    say(f"    undo stack ({len(u.stack)}): " + (" | ".join(s.label for s in u.stack) or "empty"))
    if u.redos:
        say(f"    redo stack ({len(u.redos)}): " + " | ".join(s.label for s in u.redos))


def press(r, name: str, *mods: str) -> None:
    """A key press through the table's key rows, then the status line."""
    chord = "+".join((*mods, name))
    frames(r, keys=Keys(getattr(glfw, f"KEY_{name}"), *mods))
    say(f"  {chord:<16} footer: ·  {r.undo.status}")


def main() -> None:
    r = boot()
    reg, lib, u = r.reg, r.lib, r.undo
    watched = [p for p in reg if undo.watched(p)]
    say("Hyperspace — undo and the trash, headless (tools/undo_demo.py; plan 15 WP1)")
    say(f"home: {HOME}  (a temp folder made by this script)")
    say(f"show: {lib.project.name}   preset: {lib.current(PRESETS)}   "
        f"registry: {len(reg)} params, {len(watched)} watched   "
        f"table: {len(r.router.table.routes())} routes, {len(r.router.table.desk())} desk rows")
    frames(r, 30)
    stack(r)

    say()
    say("1. Drag one slider over 24 frames (view.bright), then let go")
    bright = reg["view.bright"]
    b0 = bright.base
    for k in range(24):
        bright.set(b0 * (1 + 0.02 * (k + 1)))
        frames(r)
    say(f"    {bright.label}: {bright.fmt(b0)} -> {bright.fmt(bright.base)}   "
        f"({len(u.stack)} step on the stack while still dragging)")
    settle(r)
    stack(r)

    say()
    say("2. Sweep a knob on the desk: CC messages through MidiIO, one a frame")
    knob = next(b for b in r.router.table.active()
                if b.kind == "cc" and b.op == "abs" and b.feedback == "ring"
                and b.layer == "preset" and b.target != "view.bright"
                and undo.watched(reg[b.target]))
    kp = reg[knob.target]
    k0 = kp.base
    start = round(kp.norm * 127)
    sweep = list(range(start, 128))[:30] if start < 90 else list(range(start, 0, -1))[:30]
    for v in sweep:
        r.ports.queue.append(mido.Message("control_change", channel=knob.channel or 0,
                                          control=knob.number, value=v))
        frames(r)
    say(f"    {r.midi.control_name(knob)} -> {knob.target}: {len(sweep)} messages, "
        f"{kp.fmt(k0)} -> {kp.fmt(kp.base)}")
    settle(r)
    stack(r)

    say()
    say("3. Two hands move through the box for 2 s (the preset's own hand routes)")
    held: set[str] = set()
    seen: dict[str, list[float]] = {}
    before = {p.id: p.base for p in watched}

    def moving(t):
        return (hand("right", at=(120 * math.sin(t * 2.3), 220 + 110 * math.sin(t * 1.7),
                                  90 * math.sin(t * 3.1))),
                hand("left", at=(-140 + 60 * math.sin(t * 1.9), 200 + 90 * math.cos(t * 1.3),
                                 40 * math.sin(t * 2.0))))
    travel: dict[str, list[float]] = {}
    for _ in range(120):
        frames(r, hands_at=moving)
        for p in watched:
            if p.modulated and p.kind.value == "continuous":
                held.add(p.id)
                seen.setdefault(p.id, []).append(p.value)
                travel.setdefault(p.id, []).append(p.eff_norm)
    frames(r, 30)                                        # the hands are gone: the bases show
    far = sorted(held, key=lambda pid: min(travel[pid]) - max(travel[pid]))
    for pid in far[:4]:                                  # the four that travelled furthest
        p = reg[pid]
        say(f"    {pid}: performed {p.fmt(min(seen[pid]))} … {p.fmt(max(seen[pid]))}, "
            f"base {p.fmt(before[pid])} before and {p.fmt(p.base)} after")
    drift = max((abs(p.base - before[p.id]) for p in watched
                 if isinstance(p.base, float) and p.id in before), default=0.0)
    say(f"    {len(held)} watched params were held by a performer; the largest change of any "
        f"watched base was {drift:.1e} (the tolerance is {undo.REL_TOL:g} relative)")
    stack(r)

    say()
    say("4. Load a preset (F2, a key row -> preset.load.1)")
    frames(r, keys=Keys(glfw.KEY_F2))
    say(f"    preset: {lib.current(PRESETS)}   {bright.label}: {bright.fmt(bright.base)}   "
        f"routes: {len(r.router.table.routes())}")
    settle(r)
    stack(r)

    say()
    say("5. Ctrl+Z down the stack (the key rows fire edit.undo); the footer's line each time")

    def where() -> str:
        return (f"preset {lib.current(PRESETS)}, {bright.label} {bright.fmt(bright.base)}, "
                f"{knob.target} {kp.fmt(kp.base)}")
    say(f"    before: {where()}")
    for _ in range(4):
        press(r, "Z", "CONTROL")
        say(f"    now:    {where()}")
        frames(r, 5)
    stack(r)

    say()
    say("6. Redo (Cmd+Shift+Z fires edit.redo alone), three times")
    for _ in range(3):
        press(r, "Z", "SHIFT", "SUPER")
        say(f"    now:    {where()}")
        frames(r, 5)
    stack(r)

    say()
    say("7. The trash: save over a user preset, then delete it")
    path = r.presets.save_as("DEMO")
    say(f"    saved {path}  (new: nothing to keep)")
    bright.set(bright.base * 0.5)
    lib.overwrite(PRESETS)
    say(f"    saved over it with {bright.label} {bright.fmt(bright.base)}")
    lib.overwrite(PRESETS)
    say("    saved again, nothing changed (trashes nothing)")
    lib.delete(PRESETS, "DEMO")
    say(f"    deleted DEMO; {path.name} exists: {path.exists()}")
    say(f"    {HOME / TRASH}:")
    for f in sorted((HOME / TRASH).rglob("*")):
        if f.is_file():
            say(f"      {f.relative_to(HOME / TRASH)}   {f.stat().st_size} bytes")
    settle(r)
    say("    (a save and a delete are not undo steps: their net is the trash)")
    stack(r)

    say()
    say("8. What Undo.tick costs a frame")
    r.cost.clear()
    frames(r, 1200)
    idle = sorted(r.cost)
    say(f"    idle, {len(idle)} frames: median {statistics.median(idle) * 1e6:.0f} µs, "
        f"99th percentile {idle[int(len(idle) * 0.99)] * 1e6:.0f} µs, "
        f"max {idle[-1] * 1e6:.0f} µs")
    r.cost.clear()
    for k in range(600):
        bright.set(1.0 + 0.5 * math.sin(k * 0.05))
        frames(r)
    drag = sorted(r.cost)
    say(f"    during a drag, {len(drag)} frames: median {statistics.median(drag) * 1e6:.0f} µs, "
        f"99th percentile {drag[int(len(drag) * 0.99)] * 1e6:.0f} µs, "
        f"max {drag[-1] * 1e6:.0f} µs")
    say("    (the budget is 0.5 ms; a frame at 60 Hz is 16 667 µs)")

    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
