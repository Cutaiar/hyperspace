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
STUCK = (f"glfw.init() did not complete in {TIMEOUT_S:g} s: a modal alert or no "
         "window server; see ENGINEERING §16")
INIT_FALSE = 3                          # the child's exit when glfw.init() says no
PROBE_CODE = f"import glfw,sys; sys.exit(0 if glfw.init() else {INIT_FALSE})"
# AppKit reads NSUserDefaults' argument domain from the process's argv: the
# probe child asks AppKit not to restore (or offer to restore) saved windows,
# so it never shows the reopen-windows alert itself. This holds for this
# process only and writes no default (`defaults read org.python.python` is
# unchanged); whether it also stops an alert armed by an earlier crash could
# not be checked safely here (that needs the owner's saved state armed).
APPKIT_ARGS = ("-ApplePersistenceIgnoreState", "YES")

_cache: list = []                       # [None] or [reason]


def _run_child(cmd: list[str], timeout: float) -> tuple[int, str]:
    """(exit code, stderr) of `cmd`; on `timeout`, SIGTERM, a second's grace,
    then SIGKILL, and TimeoutExpired."""
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        _, err = p.communicate(timeout=timeout)
        return p.returncode, err or ""
    except subprocess.TimeoutExpired:
        p.terminate()
        try:
            p.wait(1.0)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
        raise


def _tail(err: str, n: int = 200) -> str:
    err = " ".join(err.split())
    return err[-n:]


def reason() -> str | None:
    """None when glfw.init() completes with success in a child; else why not."""
    if _cache:
        return _cache[0]
    try:
        code, err = _run_child([sys.executable, "-c", PROBE_CODE, *APPKIT_ARGS], TIMEOUT_S)
        if code == 0:
            why = None
        elif code == INIT_FALSE:
            why = NO_DISPLAY + (f": {_tail(err)}" if err.strip() else "")
        else:
            why = f"the glfw probe failed (exit {code}): {_tail(err) or 'no stderr'}"
    except subprocess.TimeoutExpired:
        why = STUCK
    except OSError as e:
        why = f"the glfw probe could not start: {e}"
    _cache.append(why)
    return why


def require() -> None:
    """Skip the calling test unless glfw.init() works."""
    import pytest

    why = reason()
    if why:
        pytest.skip(why)
