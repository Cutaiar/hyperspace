"""Tempo — one free-running clock, tapped into time (plan 09, decision 9).

There is no DJ Link, no MIDI clock and no drift correction: the performer
taps a tempo, presses the trigger on the one, and re-taps when the track
changes. Hz is the base unit everywhere else (lfo.py); this module turns
BPM and a division into a phase.

Two things a tap must never do decide the shape of `Clock`:

  * **Once triggered, a tap never moves a running synced LFO.** Tapping
    sets the BPM; after the first `trigger` — the global LFO trigger,
    ``lfo.trigger``, the one button pressed after tapping — the downbeat
    the LFOs read (`t0`) is the performer's and a tap does not touch it.
    So a re-tap mid-set changes the tempo, not the downbeat: a BPM change
    re-anchors `t0` so that ``beat(t)`` is continuous at the instant of
    the change, and every synced LFO keeps its place in the bar and runs
    faster or slower from there.
  * **The burst is its own bookkeeping.** Taps more than `GAP` apart
    start a new burst; the BPM is the mean interval of the burst's last
    `TAPS` (8) taps, measured from the oldest of those — the burst's
    first tap until the burst runs past eight, then the eighth-last — so
    a tempo change registers within a bar of tapping rather than being
    averaged against a minute of the old one. The one time a tap does set
    the downbeat is a clock that has never been triggered: there every
    tap places `t0` on the burst's first tap (with the nudge folded in,
    as `trigger` does), so a new app lines up without a second press.

``beat(t) = (t − t0) · bpm / 60 + nudge``, ``bar(t) = beat mod 4`` (4/4
assumed), ``phase(t, ratio) = (beat · ratio) mod 1`` — `ratio` in cycles
per beat, so a bar-long wave is 1/4 and a sixteenth is 4 (lfo.py's
DIVISIONS). `nudge` shifts the downbeat by a fraction of a beat without
touching the tempo — the APC40's NUDGE buttons step it by a hundredth.
`trigger` places `t0` so that ``beat(now) == 0`` with the current nudge
folded in: the swell lands on the "one" whatever the nudge reads, and a
nudge turned afterwards still moves the grid.

Time is handed in, never taken: `tick(t)` once a frame gives the clock
the loop's own `now`, and every call that takes an optional `t` reads it
by default, so a trigger fired from a key and the LFO step that follows
it in the same frame agree on what "now" is — the frame the trigger
fires, every synced LFO reads exactly phase 0. Nothing here imports from
the host: `register` takes the registry as a duck-typed argument, the
way hands/core.py does.
"""

from __future__ import annotations

import time

GAP = 2.0                # s between taps that starts a new burst
TAPS = 8                 # the BPM is the mean of the burst's last this many
BPM_LO, BPM_HI = 20.0, 300.0
BEATS_PER_BAR = 4
LIT = 0.15               # the fraction of a beat the beat light stays on
GROUP = "tempo"


def _clamp(x, a, b):
    return a if x < a else min(x, b)


class Clock:
    """Tap tempo, a downbeat, and the phase of any division at any time."""

    def __init__(self, bpm: float = 120.0, now=time.perf_counter):
        self.bpm = float(bpm)
        self.nudge = 0.0
        self.t = now()          # the frame's time; tick() keeps it current
        self.t0 = self.t        # the downbeat the LFOs read (trigger)
        self.taps: list[float] = []   # the current burst
        self._triggered = False

    # ---- time ----

    def tick(self, t: float) -> None:
        """Once a frame: the loop's `now`, the default `t` for everything below."""
        self.t = t

    def _t(self, t: float | None) -> float:
        return self.t if t is None else t

    # ---- tempo ----

    def tap(self, t: float | None = None) -> None:
        """One tap. A gap over GAP starts a burst; two or more taps set the BPM."""
        t = self._t(t)
        if self.taps and t - self.taps[-1] > GAP:
            self.taps = []
        self.taps.append(t)
        recent = self.taps[-TAPS:]               # a tempo change lands within a bar
        if len(recent) >= 2:
            mean = (recent[-1] - recent[0]) / (len(recent) - 1)
            if mean > 0.0:                       # two in one frame is not a tempo
                self.set_bpm(60.0 / mean, t)
        if not self._triggered:
            # never triggered: every tap puts the downbeat on the burst's
            # first tap — the nudge folded in exactly as trigger() does — so
            # a new app lines up without a second press. Once triggered, a
            # tap changes only the BPM; set_bpm above moved t0 just enough
            # to keep beat(t) continuous.
            self.t0 = self.taps[0] + self.nudge * 60.0 / self.bpm

    def set_bpm(self, bpm: float, t: float | None = None) -> None:
        """A new tempo that keeps ``beat(t)`` where it is: the downbeat is
        moved so nothing running jumps, only its rate changes."""
        t = self._t(t)
        bpm = _clamp(float(bpm), BPM_LO, BPM_HI)
        if bpm == self.bpm:
            return
        self.t0 = t - (t - self.t0) * self.bpm / bpm
        self.bpm = bpm

    def trigger(self, t: float | None = None) -> None:
        """The downbeat is now: ``beat(t) == 0`` exactly, so every synced
        LFO reads phase 0 this frame whatever the nudge. The nudge value is
        untouched — it is folded into where the downbeat is placed, so a
        *later* change of it still shifts the running phase as it should.
        The burst keeps counting."""
        t = self._t(t)
        self.t0 = t + self.nudge * 60.0 / self.bpm
        self._triggered = True

    # ---- phase ----

    def beat(self, t: float | None = None) -> float:
        return (self._t(t) - self.t0) * self.bpm / 60.0 + self.nudge

    def bar(self, t: float | None = None) -> float:
        """Beats into the bar, 0 ≤ bar < 4."""
        return self.beat(t) % BEATS_PER_BAR

    def phase(self, t: float | None = None, ratio: float = 1.0) -> float:
        """Where a wave of `ratio` cycles per beat is, in [0, 1)."""
        return (self.beat(t) * ratio) % 1.0

    def on_beat(self, t: float | None = None) -> bool:
        """The first LIT of every beat: the beat light and the METRONOME LED."""
        return self.beat(t) % 1.0 < LIT


def register(reg, clock: Clock) -> None:
    """The clock's params in the ``tempo`` group: bpm and nudge persist (a
    preset carries a tempo), tap is the key's and the APC's button."""
    if f"{GROUP}.bpm" in reg:
        return
    reg.continuous(f"{GROUP}.bpm", "BPM", lambda: clock.bpm,
                   lambda v: clock.set_bpm(float(v)), lo=BPM_LO, hi=BPM_HI,
                   fmt=lambda v: f"{v:.1f} BPM", group=GROUP,
                   tip="The clock's tempo. Tap it (B, the APC's TAP TEMPO) or set it "
                       "here; a change keeps every synced LFO where it is and only "
                       "alters its rate.")
    reg.trigger(f"{GROUP}.tap", "Tap tempo", clock.tap, group=GROUP,
                tip="Tap on the beat: two or more taps within 2 s of each other set "
                    "the BPM. Tapping never restarts the LFOs — the trigger does.")
    reg.continuous(f"{GROUP}.nudge", "Nudge", lambda: clock.nudge,
                   lambda v: setattr(clock, "nudge", float(v)), lo=-0.5, hi=0.5,
                   fmt=lambda v: f"{v:+.2f} beat", group=GROUP,
                   tip="Shift the downbeat by a fraction of a beat without changing "
                       "the tempo — the APC's NUDGE buttons step it by a hundredth.")
