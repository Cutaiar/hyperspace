"""The trackpad's pinch, which GLFW never reports (the owner, 2026-10-26).

macOS sends a pinch as magnify events; GLFW's view drops them. `install`
puts a local AppKit monitor in front of the windows that sums each
event's magnification, and `take` hands the sum over once — what the
GRAPH page zooms by (ui_graph._scroll). Off macOS, or without pyobjc,
`install` does nothing and `take` is always 0.0.

A pinch made while nothing takes it (another page, another window) is
dropped after `STALE_S`, so it never lands later as a jump.

Cold, as app is (hotreload.MODULES leaves it out): the monitor adds to
this module's globals, so a reloaded copy would sum nothing.
"""

from __future__ import annotations

import sys
import time

STALE_S = 0.1    # a sum nothing took for this long is thrown away

_sum = 0.0
_at = 0.0
_monitor = None


def _add(magnification: float) -> None:
    global _sum, _at
    now = time.monotonic()
    if now - _at > STALE_S:
        _sum = 0.0
    _sum += magnification
    _at = now


def take() -> float:
    """The pinch since the last take, as a magnification (0.1 ≈ 10%
    bigger; negative pinches in), then 0.0 until the fingers move again."""
    global _sum
    got, _sum = (_sum if time.monotonic() - _at <= STALE_S else 0.0), 0.0
    return got


def install() -> bool:
    """Start listening, once; False where there is no AppKit to ask."""
    global _monitor
    if _monitor is not None:
        return True
    if sys.platform != "darwin":
        return False
    try:
        from AppKit import NSEvent, NSEventMaskMagnify
    except ImportError:
        return False

    def seen(event):
        _add(float(event.magnification()))
        return event                     # the windows still get it

    _monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(NSEventMaskMagnify, seen)
    return _monitor is not None
