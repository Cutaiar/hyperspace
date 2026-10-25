"""The media playhead: rate, a scrub latch on `pos`, a jog that coasts, loops.

Pure logic, stepped once a frame by each media channel: no GL, no threads,
no I/O. Rate acts at once (0 holds). `pos` is a latch: while it sits still
the clip plays on from wherever it is; the step it moves, the playhead is
put at pos * duration (so an LFO on `pos` drives the clip directly). `jog`
adds a push of 8 * jog seconds per second that springs in and coasts back
out; only that push is sprung, so the rate itself never lags.
"""

from __future__ import annotations

import math

from .. import motion

LOOPS = ("loop", "pingpong", "once")

JOG_GAIN = 8.0     # clip-seconds per second at full jog
JOG_HZ = 2.0       # how fast the push springs in and coasts out
_LATCH_EPS = 1e-6


class Transport:
    def __init__(self, duration: float):
        self.duration = max(float(duration), 0.0)
        self.reset()

    def reset(self, pos: float = 0.0) -> None:
        """Back to the start (or `pos`, 0..1): no coast, forward, not scrubbing."""
        self.playhead = max(0.0, min(float(pos), 1.0)) * self.duration
        self.last_pos = float(pos)
        self.scrubbing = False
        self.speed = 1.0
        self.coast = 0.0          # the jog's sprung contribution to speed
        self.coast_v = 0.0
        self.direction = 1.0      # pingpong sign

    def step(self, dt: float, rate: float, pos: float, jog: float, loop: str) -> float:
        """Advance one frame; returns the playhead in seconds."""
        self.coast, self.coast_v = motion.spring(
            self.coast, self.coast_v, JOG_GAIN * jog, dt, hz=JOG_HZ, damp=1.0)
        self.speed = rate + self.coast
        d = self.duration
        if d <= 0.0:
            self.playhead = 0.0
            self.last_pos = pos
            self.scrubbing = False
            return 0.0
        if abs(pos - self.last_pos) > _LATCH_EPS:
            self.last_pos = pos
            self.scrubbing = True
            self.playhead = max(0.0, min(pos, 1.0)) * d
            return self.playhead
        self.scrubbing = False
        if loop != "pingpong":
            self.direction = 1.0      # a flipped sign must not outlive pingpong
        p = self.playhead + self.direction * self.speed * dt
        if loop == "pingpong":
            n = math.floor(p / d)          # ends crossed; each odd one reflects
            q = p - n * d
            if n % 2:
                q = d - q
                self.direction = -self.direction
            p = q
        elif loop == "once":
            p = max(0.0, min(p, d))
        else:
            p %= d
        self.playhead = p
        return p
