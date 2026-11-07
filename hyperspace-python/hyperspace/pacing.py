"""What paces the loop (SC3a, plan 58): the swap of the first live display's
window, a floor under it, and a timer when no display is live.

A swap on a hidden window does not wait (measured: 13,047 fps), so the root
window that holds the renderer's context cannot pace; a display's window can,
and any display can go. So one window at a time waits for its display (swap
interval 1), every other does not (interval 0: two waiting swaps a frame halve
the rate, fork F6), and that window's swap is the frame's last.

A swap that should wait does not always: a locked Mac, a window occluded from
birth or minimised, a sleeping display. `Floor` always waits to at least the
fastest connected display's refresh × `FLOOR_MARGIN`, just above the rate a
waiting swap gives, so it never meets a swap that does wait and bounds one that
does not (measured, locked: 1,360–1,720 fps without it, 125.9 with it). The
fastest connected, not the pacing window's own: on macOS a swap on a window on a
60 Hz display can run at another display's 120 (measured: 119.5 fps on one, 60 Hz
by `get_video_mode`), and a floor under its own display's 63 would have cut the
loop in half.

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

FLOOR_MARGIN = 1.05        # the floor's rate over the display's refresh
NO_DISPLAY_HZ = 60.0       # no display live: the timer alone
UNKNOWN_HZ = 240.0         # no display says its refresh: a bound that can't cap a real one
REFRESH_EVERY_S = 1.0      # how often the displays' refreshes are looked up (they can change)
SPIN_S = 0.0015            # the end of a wait is spun: a sleep overshoots by a millisecond or so


class Floor:
    """The loop's slowest allowed period: `wait` sleeps to just short of the
    next tick and spins the rest. Each tick is a period after the last, not
    after now, so a loop slower than the floor falls behind it and never waits;
    behind by more than a period, it starts again from now, so a stall is never
    paid back as a burst."""

    def __init__(self, hz: float = NO_DISPLAY_HZ, clock: Callable[[], float] = time.perf_counter,
                 sleep: Callable[[float], None] = time.sleep):
        self.clock, self.sleep = clock, sleep
        self.period = 1.0 / hz
        self.next = clock()

    def rate(self, hz: float) -> None:
        self.period = 1.0 / hz

    def reset(self) -> None:
        self.next = self.clock()

    def wait(self) -> None:
        self.next += self.period
        now = self.clock()
        if self.next < now - self.period:
            self.next = now
            return
        if self.next - now > SPIN_S:
            self.sleep(self.next - now - SPIN_S)
        while self.clock() < self.next:
            pass


class Pacer:
    """Which window waits for its display (`owner`, None with none live) and the
    floor under it. `choose` each frame, before any window is drawn; `end_frame`
    once the frame's last swap is done."""

    def __init__(self, glfw: Any, clock: Callable[[], float] = time.perf_counter,
                 sleep: Callable[[float], None] = time.sleep):
        self.glfw = glfw
        self.clock = clock
        self.owner: Any = None
        self.floor = Floor(NO_DISPLAY_HZ, clock, sleep)
        self.refresh = 0.0             # the fastest display, as last looked up; 0: none live
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
        self._looked = -1e9
        self.floor.reset()
        return True

    def end_frame(self) -> None:
        """The frame's floor: the fastest display's refresh × `FLOOR_MARGIN`, or
        `NO_DISPLAY_HZ` with no display live."""
        self._look()
        self.floor.wait()

    def _look(self) -> None:
        now = self.clock()
        if now - self._looked < REFRESH_EVERY_S:
            return
        self._looked = now
        self.refresh = 0.0 if self.owner is None else self._fastest()
        self.floor.rate(self.refresh * FLOOR_MARGIN if self.owner is not None else NO_DISPLAY_HZ)

    def _fastest(self) -> float:
        """The highest refresh of the connected displays; `UNKNOWN_HZ` when the
        window system won't say, which must not stop a frame."""
        glfw = self.glfw
        try:
            hz = max((float(glfw.get_video_mode(m).refresh_rate) for m in glfw.get_monitors()),
                     default=0.0)
        except Exception:  # noqa: BLE001 — a display that went between two calls
            return UNKNOWN_HZ
        return hz if hz > 0 else UNKNOWN_HZ
