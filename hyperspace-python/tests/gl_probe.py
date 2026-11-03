"""Probe `glfw.init()` in a child process, once per session, so a GL-window
test skips instead of hanging.

On macOS `glfw.init()` runs `[NSApplication run]`. If a previous Python GUI
process died with a window open, AppKit shows the "reopen windows?" alert
(NSPersistentUIRestorer -> NSAlert runModal), and a hidden process blocks in
it forever (also when there is no window server for the session). Nothing
in the parent can interrupt that call, so the first GL-window test asks a
child with a hard timeout. The recovery: ENGINEERING.md §16, "Why
`glfwInit()` hangs on the Mac". Cached per process (so per xdist worker).
"""

from __future__ import annotations

import subprocess
import sys

TIMEOUT_S = 8.0
NO_DISPLAY = "no display for GL"
STUCK = ("glfw.init() did not complete in 8 s: a modal alert or no window "
         "server; see ENGINEERING §16")
PROBE_CODE = "import glfw,sys; sys.exit(0 if glfw.init() else 2)"

_cache: list = []                       # [None] or [reason]


def reason() -> str | None:
    """None when glfw.init() completes with success in a child; else why not."""
    if _cache:
        return _cache[0]
    try:
        r = subprocess.run([sys.executable, "-c", PROBE_CODE],
                           timeout=TIMEOUT_S, capture_output=True, check=False)
        why = None if r.returncode == 0 else NO_DISPLAY
    except subprocess.TimeoutExpired:           # (run() kills the child)
        why = STUCK
    except OSError:
        why = NO_DISPLAY
    _cache.append(why)
    return why


def require() -> None:
    """Skip the calling test unless glfw.init() works."""
    import pytest

    why = reason()
    if why:
        pytest.skip(why)
