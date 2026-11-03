"""The live-device lock: tests marked `live` take turns across processes.

Within one run xdist already gives every `live` test to one worker
(`xdist_group("live")`, tests/conftest.py). This lock covers the other
pytest processes on the machine — a second Claude session, a second
worktree, the owner's own run — which xdist cannot see.

Why it matters (2026-11-01): `glfw.init()`, a camera or audio open, a
Syphon / NDI loopback or a real HID pad can block inside a C call while
another process holds the window system or the device, rather than
fail. pytest-timeout's thread method then kills the worker (a hang
fails by name instead of stalling the run at 99 %), but the test still
never ran; taking turns is the mitigation that lets it run.

The lock is `fcntl.flock` on one file under the temp folder: the kernel
drops it when the holder's file closes or its process dies, so a killed
worker never leaves it held. Waiting is bounded (`WAIT_S`); a test that
cannot have it skips, it never blocks forever.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import tempfile
import time
from pathlib import Path

# how long a live test waits for another run's live tests before it skips
WAIT_S = 60.0
POLL_S = 0.1
SKIP_REASON = "another test run holds the live devices"


def lock_path() -> Path:
    """One file per account (a file another account made may refuse us)."""
    return Path(tempfile.gettempdir()) / f"hyperspace-tests-live-{os.getuid()}.lock"


def acquire(path: Path | None = None, wait_s: float | None = None,
            poll_s: float = POLL_S) -> int | None:
    """An open file descriptor holding the exclusive lock on `path` (the
    machine's, `lock_path()`, by default), or None when it could not be
    had within `wait_s` seconds (`WAIT_S`, read at the call)."""
    path = lock_path() if path is None else Path(path)
    wait_s = WAIT_S if wait_s is None else wait_s
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + wait_s
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    return None
                time.sleep(poll_s)
    except BaseException:
        os.close(fd)
        raise


def release(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


@contextlib.contextmanager
def held(path: Path | None = None, wait_s: float | None = None, poll_s: float = POLL_S):
    """Hold the lock for the block. Yields None when held, else the reason
    the caller skips with: another run holds it past the wait, or the lock
    file cannot be opened or locked (an OSError: permissions, ENOLCK)."""
    try:
        fd = acquire(path, wait_s, poll_s)
    except OSError as e:
        yield f"the live-device lock cannot be taken: {e}"
        return
    try:
        yield None if fd is not None else SKIP_REASON
    finally:
        if fd is not None:
            release(fd)
