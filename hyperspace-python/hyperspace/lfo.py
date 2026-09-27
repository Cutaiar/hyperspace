"""Four LFOs — performers that own a parameter, and are themselves ownable.

An LFO is a source like a hand or an audio lane: `LFOs.step` runs once a
frame and `publish` hands the four outputs to the router as ``lfo:<i>``
(plan 09, decisions 7 and 8). Every knob on an LFO — shape, rate, sync,
depth, phase — is a registry param, modulatable and persistent, which is
what makes them chainable: a hand can own LFO 1's depth while LFO 1 owns
brightness, and a preset carries the whole arrangement. Layering is a
property of the graph, never two performers on one knob.

Per LFO:

  shape   sine · tri · saw · square · random — random is sample-and-hold,
          one value per cycle, drawn when the cycle count changes
  sync    Hz, or a division: 4 bars · 2 bars · 1 bar · 1/2 · 1/4 · 1/8 ·
          1/16 (DIVISIONS, in cycles per beat of the 4/4 clock)
  rate    Hz, used only in Hz mode; the phase integrates rate · dt
  depth   0–1; the output is ``u = 0.5 + 0.5 · depth · wave`` with the
          wave in [−1, 1], so an LFO *rests* at 0.5 (REST) — the rest a
          push row is centred on (decision 6) — and depth 0 is silence
  phase   0–1, an offset added on top of the cycle in either mode
  reset   a trigger: this one LFO's cycle restarts now, in either mode —
          a per-LFO gesture hook

In a division the phase is the clock's, ``clock.phase(t, ratio) + phase``
(tempo.py), so bar-long waves land on the downbeat and the **global
trigger** — ``lfo.trigger``, the one button pressed after tapping a tempo
— re-aligns all of them at once: it sets the clock's downbeat to now and
every synced LFO reads its own phase offset that same frame. Free-running
Hz LFOs are untouched by it. A per-LFO `reset` in a division keeps its
own offset from the clock (`shift`), so one LFO can be restarted without
moving the clock or the others; the global trigger clears those offsets.

Frame order (app.py): the LFOs step after the bridge and before
`Router.modulate`, so an LFO that owns another LFO's depth lands one frame
before that LFO's output does — the same one-frame lag every modulated
value has, and no recursion.

Nothing here imports from the host: the clock, the registry and the
router are duck-typed arguments, the boundary rule hands/ has
(tests/test_lfo_boundary.py).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

SHAPES = ["sine", "tri", "saw", "square", "random"]
SYNCS = ["Hz", "4 bars", "2 bars", "1 bar", "1/2", "1/4", "1/8", "1/16"]
# a division's cycles per beat: a bar of 4/4 is a quarter cycle per beat
DIVISIONS = {"4 bars": 1 / 16, "2 bars": 1 / 8, "1 bar": 1 / 4, "1/2": 1 / 2,
             "1/4": 1.0, "1/8": 2.0, "1/16": 4.0}
RATE_LO, RATE_HI = 0.01, 20.0
N = 4
REST = 0.5
GROUP = "lfo"
RANDOM = SHAPES.index("random")


def wave(shape: int, x: float) -> float:
    """The shape's value at phase x ∈ [0, 1), in [−1, 1]. Random is not
    here — it is a held value, not a function of the phase."""
    if shape == 0:
        return math.sin(2 * math.pi * x)
    if shape == 1:
        return 1.0 - 4.0 * abs(x - 0.5)
    if shape == 2:
        return 2.0 * x - 1.0
    if shape == 3:
        return 1.0 if x < 0.5 else -1.0
    return 0.0


@dataclass
class LFO:
    """One oscillator: its settings (the params) and its running state."""

    shape: int = 0
    rate: float = 1.0
    sync: int = 0            # index into SYNCS; 0 is Hz
    depth: float = 1.0
    phase: float = 0.0
    # runtime, never saved
    acc: float = field(default=0.0, repr=False)     # Hz: the integrated cycles
    shift: float = field(default=0.0, repr=False)   # division: this LFO's offset (reset)
    hold: float = field(default=0.0, repr=False)    # random: the held value
    cycle: int | None = field(default=None, repr=False)  # the cycle `hold` was drawn in
    x: float = field(default=0.0, repr=False)       # this frame's phase
    out: float = field(default=REST, repr=False)    # this frame's u

    @property
    def synced(self) -> bool:
        return self.sync > 0

    @property
    def ratio(self) -> float:
        """Cycles per beat in a division; 0 in Hz mode."""
        return DIVISIONS[SYNCS[self.sync]] if self.synced else 0.0

    def wave_at(self, x: float) -> float:
        return self.hold if self.shape == RANDOM else wave(self.shape, x)

    def step(self, dt: float, t: float, clock, rng: random.Random) -> float:
        if self.synced:
            cycles = clock.beat(t) * self.ratio + self.shift
        else:
            self.acc += self.rate * dt
            cycles = self.acc
        cycles += self.phase
        self.x = cycles % 1.0
        if self.shape == RANDOM:
            k = math.floor(cycles)
            if k != self.cycle:           # once per cycle: a new value, held
                self.cycle, self.hold = k, rng.uniform(-1.0, 1.0)
        self.out = REST + 0.5 * self.depth * self.wave_at(self.x)
        return self.out

    def restart(self, clock=None, t: float | None = None) -> None:
        """The cycle begins now (its `phase` offset stays on top)."""
        if self.synced:
            self.shift = 0.0 if clock is None else -clock.beat(t) * self.ratio
        else:
            self.acc = 0.0
        self.cycle = None                 # random: a fresh draw


class LFOs:
    """The bank of N: stepped once a frame, published as the ``lfo`` source."""

    def __init__(self, n: int = N, seed: int | None = None):
        self.lfos = [LFO() for _ in range(n)]
        self.rng = random.Random(seed)
        self.outputs = [REST] * n

    def __len__(self) -> int:
        return len(self.lfos)

    def __getitem__(self, i: int) -> LFO:
        return self.lfos[i]

    @property
    def labels(self) -> list[str]:
        return [f"LFO {i + 1}" for i in range(len(self.lfos))]

    def step(self, dt: float, t: float, clock) -> list[float]:
        """One frame: every LFO's output for time t, in [0, 1]."""
        self.outputs = [lf.step(dt, t, clock, self.rng) for lf in self.lfos]
        return self.outputs

    def reset(self, i: int, clock=None, t: float | None = None) -> None:
        """One LFO restarts now, in either mode; the clock and the rest stay."""
        self.lfos[i].restart(clock, t)

    def trigger(self, clock=None, t: float | None = None) -> None:
        """The global trigger: the downbeat is now and every synced LFO
        restarts together. Free-running (Hz) ones are untouched."""
        if clock is not None:
            clock.trigger(t)
        for lf in self.lfos:
            if lf.synced:
                lf.shift = 0.0
                lf.cycle = None

    def publish(self, router) -> None:
        """This frame's outputs to the router as the ``lfo`` source, with
        the lane names and the rest a push row on an LFO is centred on."""
        router.feed(GROUP, self.outputs)
        if not hasattr(router, "labels"):    # a Router from before a hot reload
            router.labels = {}
        router.labels[GROUP] = self.labels
        if not hasattr(router, "rests"):     # plan 09 WP1 adds it; until then, here
            router.rests = {}
        router.rests[GROUP] = [REST] * len(self.lfos)


def register(reg, lfos: LFOs, clock) -> None:
    """Every LFO knob as a param in the ``lfo`` group, plus the global
    trigger. All of them modulatable and persistent: a performer can own
    an LFO's depth, and a preset carries the arrangement."""
    if f"{GROUP}.trigger" in reg:
        return
    reg.trigger(f"{GROUP}.trigger", "LFO trigger", lambda: lfos.trigger(clock), group=GROUP,
                lit=clock.on_beat,
                tip="The downbeat is now: every synced LFO restarts together, on this "
                    "press (⇧B, the APC's METRONOME — its LED blinks on the beat). "
                    "Free-running Hz LFOs are untouched.")
    hz = lambda v: f"{v:.2f} Hz" if v < 10 else f"{v:.1f} Hz"
    for i, lf in enumerate(lfos.lfos):
        p, name = f"{GROUP}.{i + 1}", f"LFO {i + 1}"
        reg.enum(f"{p}.shape", f"{name} shape", lambda lf=lf: lf.shape,
                 lambda v, lf=lf: setattr(lf, "shape", int(v)), SHAPES, group=GROUP,
                 tip="The wave. Random is sample-and-hold: one value per cycle.")
        reg.continuous(f"{p}.rate", f"{name} rate", lambda lf=lf: lf.rate,
                       lambda v, lf=lf: setattr(lf, "rate", float(v)),
                       lo=RATE_LO, hi=RATE_HI, log=True, fmt=hz, group=GROUP,
                       tip="Cycles per second while Sync is Hz; a division ignores it.")
        reg.enum(f"{p}.sync", f"{name} sync", lambda lf=lf: lf.sync,
                 lambda v, lf=lf: setattr(lf, "sync", int(v)), SYNCS, group=GROUP,
                 tip="Free-running at the rate, or locked to the clock: a division "
                     "lands on the downbeat and follows the global trigger.")
        reg.continuous(f"{p}.depth", f"{name} depth", lambda lf=lf: lf.depth,
                       lambda v, lf=lf: setattr(lf, "depth", float(v)),
                       lo=0.0, hi=1.0, fmt=lambda v: f"depth {v:.2f}", group=GROUP,
                       tip="How far the output swings about its rest of 0.5; 0 is still.")
        reg.continuous(f"{p}.phase", f"{name} phase", lambda lf=lf: lf.phase,
                       lambda v, lf=lf: setattr(lf, "phase", float(v)),
                       lo=0.0, hi=1.0, wrap=True, fmt=lambda v: f"phase {v:.2f}",
                       group=GROUP,
                       tip="An offset into the cycle, on top of the clock or the "
                           "free-running phase.")
        reg.trigger(f"{p}.reset", f"{name} reset", lambda i=i: lfos.reset(i, clock),
                    group=GROUP,
                    tip="This LFO's cycle restarts now, in either mode — the clock and "
                        "the other LFOs stay where they are.")
