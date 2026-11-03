"""The live-device lock: tests marked `live` take turns across processes.

It is the one thing that keeps two live tests from running at once: two
xdist workers of one run (`--dist load` hands a test to any worker, row
605) and two pytest processes on the machine — a second Claude session,
a second worktree, the owner's own run.

Why it matters (2026-11-01): `glfw.init()`, a camera or audio open, a
Syphon / NDI loopback or a real HID pad can block inside a C call while
another process holds the window system or the device, rather than
fail. pytest-timeout's thread method then kills the worker (a hang
fails by name instead of stalling the run at 99 %), but the test still
never ran; taking turns is the mitigation that lets it run.

The lock is `fcntl.flock` on one file under the temp folder: the kernel
drops it when the holder's file closes or its process dies, so a killed
worker never leaves it held. Waiting is bounded: `WAIT_S` while another
run holds it, `RUN_WAIT_S` while the holder is a worker of the waiter's
own run (a holder writes its run's id into the file), so one run's live
tests queue for each other without skipping, and a stuck other run
costs a skip, never a block forever.
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
# how long it waits while a worker of its own run holds it: the run's live
# tier queues through the lock (34 tests, ~25 s serial on the M3 Max,
# 2026-11-03), kept under the 120 s per-test timeout, which counts the wait
RUN_WAIT_S = 90.0
POLL_S = 0.1
SKIP_REASON = "another test run holds the live devices"

# the system calls, through names a test can replace for this module alone
_open, _close, _flock = os.open, os.close, fcntl.flock


def lock_path() -> Path:
    """One file per account (a file another account made may refuse us)."""
    return Path(tempfile.gettempdir()) / f"hyperspace-tests-live-{os.getuid()}.lock"


def holder(fd: int) -> str:
    """The run id the lock's holder wrote into the file ("" for none)."""
    try:
        return os.pread(fd, 128, 0).decode("ascii", "replace").strip()
    except OSError:
        return ""


def acquire(path: Path | None = None, wait_s: float | None = None,
            poll_s: float = POLL_S, run: str = "",
            run_wait_s: float | None = None) -> int | None:
    """An open file descriptor holding the exclusive lock on `path` (the
    machine's, `lock_path()`, by default), or None when it could not be
    had within `wait_s` seconds (`WAIT_S`, read at the call) — or, while
    the holder is a worker of the same `run` (a run id, written into the
    file once held), within `run_wait_s` (`RUN_WAIT_S`)."""
    path = lock_path() if path is None else Path(path)
    wait_s = WAIT_S if wait_s is None else wait_s
    run_wait_s = RUN_WAIT_S if run_wait_s is None else run_wait_s
    fd = _open(path, os.O_RDWR | os.O_CREAT, 0o600)
    start = time.monotonic()
    try:
        while True:
            try:
                _flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                ours = bool(run) and holder(fd) == run
                if time.monotonic() - start >= (max(wait_s, run_wait_s) if ours else wait_s):
                    _close(fd)
                    return None
                time.sleep(poll_s)
        if run:
            os.ftruncate(fd, 0)
            os.pwrite(fd, run.encode("ascii", "replace"), 0)
        return fd
    except BaseException:
        _close(fd)
        raise


def release(fd: int) -> None:
    try:
        with contextlib.suppress(OSError):
            os.ftruncate(fd, 0)         # (no holder's id left behind)
        _flock(fd, fcntl.LOCK_UN)
    finally:
        _close(fd)


@contextlib.contextmanager
def held(path: Path | None = None, wait_s: float | None = None, poll_s: float = POLL_S,
         run: str = "", run_wait_s: float | None = None):
    """Hold the lock for the block. Yields None when held, else the reason
    the caller skips with: another run holds it past the wait, or the lock
    file cannot be opened or locked (an OSError: permissions, ENOLCK)."""
    fd, why_not = None, None
    try:
        fd = acquire(path, wait_s, poll_s, run, run_wait_s)
    except OSError as e:
        why_not = f"the live-device lock cannot be taken: {e}"
    if why_not:                         # (yielded outside the handler: a skip
        yield why_not                   # thrown in here chains no OSError)
        return
    try:
        yield None if fd is not None else SKIP_REASON
    finally:
        if fd is not None:
            release(fd)
