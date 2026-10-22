"""The step sequencer — five lanes of eight steps, read straight off the clock.

A sequencer is a source like the LFOs (plan 31 §S): `Sequencer.step` runs
once a frame, fires each lane's envelope on the steps it crosses, and
`publish` hands the router five trigger-kind lanes, ``seq:<i>``, that
pulse on the frame a lane fires, so a lane can drive ``preset.next`` or a
strobe as well as its envelope. Every step is a registry param —
``seq.<l>.<s>``, a toggle in v1 — so the APC40's clip grid is a plain
toggle row with LED feedback, and Learn, undo, the preset and "a
performer owns a step" all come with it (decision 4). The model stores a
step as a float, 0 off and > 0 its velocity, so the toggle can become a
velocity later without a new file format (decision 5).

Per sequencer (all global, decisions 5–6):

  span    1/2 bar · 1 bar · 2 bars · 4 bars — the time the eight steps
          cover, so a step is a 16th, an 8th, a quarter or a half
          (``steps_per_beat = 8 / (bars · 4)``)
  length  1–8: the pattern wraps after this many steps
  swing   0–0.5 of a step: how late every odd step lands
  run     the transport; session state, never in a preset (decision 8)

Per lane: the eight steps, `mute`, and `env`, the envelope it fires —
lane l fires envelope l by default (decision 3).

**The position is the clock's, never integrated.** ``s(t) = (clock.beat(t)
+ shift) · steps_per_beat``, so the grid cannot drift from the synced
LFOs, a `set_bpm` (which keeps the beat continuous) needs nothing, and a
frame's length does not matter. Each frame fires every step k in
(k_last, K], in order, where K is the last boundary s has reached — odd
boundaries sit `swing` late — and each fire carries ``at = t_k``, the
clock time of that boundary found by inverting tempo.py's ``beat``, so an
envelope fired from a step that fell between two frames renders exactly.
Three things are not crossings and fire nothing extra:

  * **A stall.** More than `length` steps in one call — a two-second
    hitch, a laptop lid — fires only the current step: one hit late is a
    glitch, a burst of sixteen is a drum roll nobody played.
  * **A step backwards** — a backward nudge, a swing turned up past s.
    `k_last` stays where it is, so the steps already fired do not fire
    again on the way back up. A jump back of more than a whole pattern
    (STEPS) is a re-anchored clock, not a nudge, and starts afresh.
  * **A span change** rescales s, so it re-anchors and starts at the
    next boundary.

**Re-align.** `Clock.trigger` — the global ``lfo.trigger`` — bumps
`clock.epoch`; a new epoch fires step 0 that call, at the trigger time,
so the button that puts the LFOs on the one puts the grid there too, and
clears the sequencer's own offset. ``seq.trigger`` is the per-LFO
`reset`'s counterpart: the sequencer alone restarts at step 0, keeping an
offset (`shift`, in beats) from the clock, which stays where it is. It is
held to the next `step` and lands at that step's t, whichever path fired
it — a key before the step or the panel after it — so step 0's time is
always a frame's own.

**Transport.** `run` gates firing only. While it is off nothing fires and
`pulses` stay 0, but `k_last` keeps following the clock, so turning it
on starts at the first boundary after the last stepped frame — never a
catch-up — and the grid is where the clock says. `playhead` is None while
stopped (the clip-stop row goes dark rather than marching over a silent
pattern); `seq.step` reads 0 then, else the 1-based step. The call that
sees `run` go off sets `stopped` (one frame) and calls the optional
``release(lane, env, at)`` for every lane, so a gate the pattern opened
can close; what releasing means is the host's (wave 2: `envs.release`).

Callbacks, both 0-based in the lane like the router's addresses
(``seq:0`` is lane 1, the param ids are 1-based ``seq.1.3``):

  fire(lane, env, at, velocity)    a step on an unmuted lane
  release(lane, env, at)           `run` went off

Class-level defaults for the runtime state, so a hot-reloaded instance
keeps its `k_last` and one from before an attribute existed still steps.
Nothing here imports from the host: the clock, the registry and the
router are duck-typed arguments (tests/test_sequencer.py, the boundary
rule of lfo.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

LANES = 5
STEPS = 8
SPANS = ["1/2 bar", "1 bar", "2 bars", "4 bars"]
BARS = {"1/2 bar": 0.5, "1 bar": 1.0, "2 bars": 2.0, "4 bars": 4.0}
BEATS_PER_BAR = 4            # 4/4, as tempo.py assumes
SWING_HI = 0.5
ENV_HI = 16                  # the envelope bank's cap (plan 31 decision 3)
REST = 0.0                   # a trigger lane rests low: a pulse is its rising edge
REALIGN = STEPS              # a jump back further than this is a re-anchor, not a nudge
GROUP = "seq"


def _clamp(x, a, b):
    # tapers.clamp again — the price of importing nothing from the host
    return a if x < a else min(x, b)


@dataclass
class Lane:
    """One row of the grid: its steps (0 off, > 0 a velocity), mute, and
    the envelope it fires."""

    steps: list[float] = field(default_factory=lambda: [0.0] * STEPS)
    mute: bool = False
    env: int = 1


class Sequencer:
    """Five lanes × eight steps over a span, stepped off the tempo clock."""

    LANES = LANES
    STEPS = STEPS

    # runtime, never saved; class-level so a hot-reloaded instance keeps
    # what it has and one from before an attribute existed gets a default
    k_last: int | None = None       # the last step boundary crossed (absolute, off the clock)
    epoch_seen: int | None = None   # the clock epoch last seen
    playhead: int | None = None     # 0..length-1 while running, else None
    pulses: tuple | list = (0.0,) * LANES   # per lane: the velocity fired this call
    shift: float = 0.0              # beats: seq.trigger's offset from the clock
    pending: bool = False           # a seq.trigger held for the next step
    last_spb: float | None = None   # the span last stepped in
    was_running: bool = False
    stopped: bool = False           # this call saw `run` go off

    def __init__(self):
        self.lanes = [Lane(env=i + 1) for i in range(LANES)]
        self.span = SPANS.index("1 bar")
        self.length = STEPS
        self.swing = 0.0
        self.run = False

    @property
    def steps_per_beat(self) -> float:
        """8 steps over the span: 4 (16ths) at 1/2 bar … 0.5 (halves) at 4 bars."""
        return STEPS / (BARS[SPANS[self.span]] * BEATS_PER_BAR)

    @property
    def labels(self) -> list[str]:
        return [f"Seq {i + 1}" for i in range(LANES)]

    # ---- the grid in step units ----

    def boundary(self, k: int) -> float:
        """Where step k starts, in steps: odd steps sit `swing` late."""
        return k + (self.swing if k % 2 else 0.0)

    def reached(self, s: float) -> int:
        """The last step whose boundary s has reached."""
        f = math.floor(s)
        if f % 2 and s < f + self.swing:
            return f - 1
        return f

    def time_of(self, k: int, clock) -> float:
        """t_k: the clock time step k's boundary falls on — tempo.py's
        ``beat(t) = (t − t0) · bpm / 60 + nudge`` inverted."""
        beat = self.boundary(k) / self.steps_per_beat - self.shift
        return clock.t0 + (beat - clock.nudge) * 60.0 / clock.bpm

    # ---- the frame ----

    def restart(self) -> None:
        """``seq.trigger``: step 0 now, the clock untouched — held to the
        next `step`, which fires it at its own t."""
        self.pending = True

    def step(self, t: float, clock, fire, release=None) -> list[float]:
        """One frame at time t: fire every step crossed since the last call
        (see the module docstring), set `playhead` and `pulses`, and return
        `pulses`."""
        spb = self.steps_per_beat
        length = int(_clamp(self.length, 1, STEPS))
        restart = False
        epoch = getattr(clock, "epoch", 0)
        if self.epoch_seen is not None and epoch != self.epoch_seen:
            self.shift = 0.0             # the global trigger re-aligns the grid to the clock
            restart = True
        self.epoch_seen = epoch
        if self.pending:                 # after the epoch: a held restart is the later word
            self.pending = False
            self.shift = -clock.beat(t)
            restart = True
        s = (clock.beat(t) + self.shift) * spb
        k = self.reached(s)
        if restart:
            # step 0's boundary is the trigger's time, and it fires this call
            # even when the float puts s a hair under 0 (the nudge folded in)
            self.k_last, k = -1, max(k, 0)
        elif self.k_last is None or spb != self.last_spb:
            # first call, or a new span: start at the next boundary — one
            # exactly now counts, so a fresh clock at beat 0 fires step 0
            self.k_last = k - 1 if s == self.boundary(k) else k
        self.last_spb = spb

        running = bool(self.run)
        self.stopped = self.was_running and not running
        self.was_running = running
        pulses = [0.0] * LANES
        if k < self.k_last:
            if self.k_last - k > REALIGN:
                self.k_last = k          # a re-anchored clock: start afresh
            # else a nudge back: hold k_last, so nothing fires twice
        else:
            crossed = range(self.k_last + 1, k + 1)
            if len(crossed) > length:    # a stall: the current step, no burst
                crossed = range(k, k + 1)
            if running:
                for j in crossed:
                    at = self.time_of(j, clock)
                    i_step = j % length
                    for i, lane in enumerate(self.lanes):
                        v = lane.steps[i_step]
                        if v > 0.0 and not lane.mute:
                            fire(i, lane.env, at, v)
                            pulses[i] = max(pulses[i], v)
            self.k_last = k
        self.pulses = pulses
        self.playhead = (max(k, 0) % length) if running else None
        if self.stopped and release is not None:
            for i, lane in enumerate(self.lanes):
                release(i, lane.env, t)
        return pulses

    def publish(self, router) -> None:
        """This frame's pulses to the router as the ``seq`` source: trigger
        lanes resting at 0, so a pulse is the rising edge a trigger param
        fires on."""
        router.feed(GROUP, list(self.pulses))
        router.labels[GROUP] = self.labels
        router.rests[GROUP] = [REST] * LANES
        # a pulse is a hit, not a level: each lane's signal kind is a
        # trigger (decision 10), as a threshold modifier's output is — on a
        # router that keeps kinds (routing.Router.lane_kinds)
        kinds = getattr(router, "lane_kinds", None)
        if isinstance(kinds, dict):
            kinds[GROUP] = ["trigger"] * LANES


def register(reg, seq: Sequencer, clock=None) -> None:
    """The grid and its globals as params in the ``seq`` group. The steps,
    mutes, envelope ids, span, length and swing persist — the pattern is
    the preset's (decision 8); `run` and the read-only playhead do not.
    `clock` is unused today and taken for the shape of lfo.register."""
    if f"{GROUP}.run" in reg:
        return
    g = GROUP
    for li, lane in enumerate(seq.lanes):
        p, name = f"{g}.{li + 1}", f"Seq lane {li + 1}"
        for si in range(STEPS):
            def put(v, lane=lane, si=si):
                # on keeps a velocity it already has: the toggle is a view
                # of a float, so a later velocity survives a press
                if not v:
                    lane.steps[si] = 0.0
                elif lane.steps[si] <= 0.0:
                    lane.steps[si] = 1.0
            reg.toggle(f"{p}.{si + 1}", f"{name} step {si + 1}",
                       lambda lane=lane, si=si: lane.steps[si] > 0.0, put, group=g,
                       tip="This step fires the lane's envelope when the playhead "
                           "reaches it.")
        reg.toggle(f"{p}.mute", f"{name} mute", lambda lane=lane: lane.mute,
                   lambda v, lane=lane: setattr(lane, "mute", bool(v)), group=g,
                   tip="A muted lane keeps its pattern and fires nothing.")
        # not lane-driven: retargeting a lane mid-gate would strand the
        # envelope it opened
        reg.continuous(f"{p}.env", f"{name} envelope", lambda lane=lane: lane.env,
                       lambda v, lane=lane: setattr(lane, "env", int(_clamp(round(v), 1, ENV_HI))),
                       lo=1, hi=ENV_HI, integer=True, fmt=lambda v: f"env {int(v)}",
                       group=g, modulatable=False,
                       tip="The envelope this lane's steps fire.")
    reg.enum(f"{g}.span", "Seq span", lambda: seq.span,
             lambda v: setattr(seq, "span", int(_clamp(int(v), 0, len(SPANS) - 1))), SPANS,
             group=g,
             tip="The time the eight steps cover: 1/2 bar is 16ths, 1 bar 8ths, 2 bars "
                 "quarters, 4 bars halves.")
    reg.continuous(f"{g}.length", "Seq length", lambda: seq.length,
                   lambda v: setattr(seq, "length", int(_clamp(round(v), 1, STEPS))),
                   lo=1, hi=STEPS, integer=True, fmt=lambda v: f"{int(v)} steps", group=g,
                   tip="The pattern wraps after this many steps.")
    reg.continuous(f"{g}.swing", "Seq swing", lambda: seq.swing,
                   lambda v: setattr(seq, "swing", float(_clamp(v, 0.0, SWING_HI))),
                   lo=0.0, hi=SWING_HI, fmt=lambda v: f"swing {v:.2f}", group=g,
                   tip="How late every odd step lands, as a fraction of a step.")
    reg.toggle(f"{g}.run", "Seq run", lambda: seq.run,
               lambda v: setattr(seq, "run", bool(v)), group=g, persist=False,
               tip="The transport. Starting waits for the next step; the grid is "
                   "always where the clock is.")
    reg.continuous(f"{g}.step", "Seq step",
                   lambda: 0 if seq.playhead is None else seq.playhead + 1,
                   lambda v: None, lo=0, hi=STEPS, integer=True,
                   fmt=lambda v: "stopped" if int(v) == 0 else f"step {int(v)}",
                   group=g, persist=False, modulatable=False,
                   tip="The playhead, read only: 0 while stopped.")
    reg.trigger(f"{g}.trigger", "Seq restart", seq.restart, group=g,
                lit=lambda: seq.playhead == 0,
                tip="The pattern restarts at step 0 on this press; the clock and the "
                    "LFOs stay where they are. The LFO trigger re-aligns both.")
