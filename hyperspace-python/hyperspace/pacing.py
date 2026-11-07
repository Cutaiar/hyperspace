"""What paces the loop (SC3a, plan 58): the swap of the first live display's
window, a floor under it, and a timer when nothing is being swapped.

A swap on a hidden window does not wait (measured: 13,047 fps), so the root
window that holds the renderer's context cannot pace; a display's window can,
and any display can go. So one window at a time waits for its display (swap
interval 1), every other does not (interval 0: two waiting swaps a frame halve
the rate, fork F6), and that window's swap is the frame's last.

A swap that should wait does not always: a locked Mac, a window occluded from
birth or minimised, a sleeping display. `Floor` bounds that, and must never touch
a healthy loop, so it trusts nothing about the displays:

- **A fixed cap, `CAP_HZ`, not a display's refresh.** `get_video_mode` doesn't
  decide what a swap does: a window on a 60 Hz display swaps at 119.5 fps here
  (row 782), and a VRR panel, a display reporting 0 or a mode change can all say
  less than the loop really runs at. A floor under the true rate halves the loop.
- **An average, not a frame's length.** A healthy 120 Hz loop has frames of 1 ms
  beside frames of 16 (sd 3–5 ms around 8.3). A burst of `BURST` frames passes
  untouched, and only a loop over the cap for longer than that waits.

With no display connected, no window live, or a frame that swapped nothing (a
raising draw holds the window on its last frame), nothing waits at all, so the
rate is `NO_DISPLAY_HZ`.

`choose` runs between frames, so a handover never lands inside one. It never
touches a window that is not in the list: one going away has already been
destroyed. Which window paces is the first in the list, in slot order: output 1
while it is live, as it has always been.

Render stack's edge (ARCHITECTURE §3): it knows windows and the clock, nothing of
the renderer. `glfw` is handed in, so a test can stand in for it.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

CAP_HZ = 240.0             # a swap that doesn't wait, at most: no display this runs on is faster
NO_DISPLAY_HZ = 60.0       # nothing is being swapped: the timer alone
BURST = 8                  # frames that may run ahead of the rate before any of them waits
LOOK_EVERY_S = 1.0         # how often the displays are counted (they can come and go)


class Floor:
    """The loop's average rate, at most: a token per frame, `hz` of them a second,
    `BURST` at most in hand. A frame with a token never waits, so a loop under the
    rate is never touched, however uneven; one with none sleeps until there is one.
    The tokens come by the clock, so a sleep's overshoot is made up and a stall earns
    no more than a burst."""

    def __init__(self, hz: float = NO_DISPLAY_HZ, clock: Callable[[], float] = time.perf_counter,
                 sleep: Callable[[float], None] = time.sleep):
        self.clock, self.sleep = clock, sleep
        self.hz = hz
        self.tokens = float(BURST)
        self.last = clock()

    def rate(self, hz: float) -> None:
        self.hz = hz

    def reset(self) -> None:
        self.tokens, self.last = float(BURST), self.clock()

    def wait(self) -> None:
        now = self.clock()
        self.tokens = min(self.tokens + (now - self.last) * self.hz, float(BURST))
        self.last = now
        self.tokens -= 1.0
        if self.tokens < 0.0:
            self.sleep(-self.tokens / self.hz)


class Pacer:
    """Which window waits for its display (`owner`, None with none live) and the
    floor under it. `choose` each frame, before any window is drawn; `swapped` when
    `owner` has swapped; `end_frame` once the frame's last swap is done."""

    def __init__(self, glfw: Any, clock: Callable[[], float] = time.perf_counter,
                 sleep: Callable[[float], None] = time.sleep):
        self.glfw = glfw
        self.clock = clock
        self.owner: Any = None
        self.floor = Floor(NO_DISPLAY_HZ, clock, sleep)
        self.displays = True           # any connected, as last counted
        self._swapped = False
        self._looked = -1e9

    def choose(self, live: Sequence[Any], current: Any) -> bool:
        """The first of `live` paces from now on: the old owner, if it is still
        live, stops waiting, the new one starts, and the floor starts counting
        afresh. `current` is the window left current. True on a handover."""
        want = live[0] if live else None
        if want is self.owner:
            return False
        glfw = self.glfw
        if self.owner is not None and self.owner in live:
            glfw.make_context_current(self.owner)
            glfw.swap_interval(0)
        if want is not None:
            glfw.make_context_current(want)
            glfw.swap_interval(1)
        glfw.make_context_current(current)
        self.owner = want
        self.floor.reset()
        return True

    def swapped(self) -> None:
        """`owner` swapped this frame, so its display may have paced it."""
        self._swapped = True

    def end_frame(self) -> None:
        """The frame's floor: `CAP_HZ` after a swap with a display connected, else
        `NO_DISPLAY_HZ`."""
        self._look()
        paced = self._swapped and self.owner is not None and self.displays
        self._swapped = False
        self.floor.rate(CAP_HZ if paced else NO_DISPLAY_HZ)
        self.floor.wait()

    def _look(self) -> None:
        now = self.clock()
        if now - self._looked < LOOK_EVERY_S:
            return
        self._looked = now
        try:
            self.displays = bool(self.glfw.get_monitors())
        except Exception:  # noqa: BLE001 — a window system that won't say must not stop a frame
            self.displays = True
