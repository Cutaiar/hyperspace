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
worker never leaves it held. A holder writes `<run id>:<pid>` into the
file once it holds the lock and clears it before letting go, so an
empty file under a held lock is a holder that names no run (an older
build's, or one caught between taking the lock and writing). A waiter
of a run waits without bound while a live worker of its own run holds
it — that holder's own per-test timeout bounds the turn, and a run
never skips its own live tests; `WAIT_S` behind another run's holder,
`RUN_WAIT_S` behind one that names none (or names this run with a pid
that is gone: a killed worker's id under an older build's lock), each
holder's time counted on its own; then it gives up with the reason,
never blocking forever on anyone else.
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
# how long it waits for a holder that names no run (an older build's run)
RUN_WAIT_S = 90.0
POLL_S = 0.1
SKIP_REASON = "another test run holds the live devices"
UNKNOWN_REASON = "a test run that names no run id (an older build's) holds the live devices"

# the system calls, through names a test can replace for this module alone
_open, _close, _flock = os.open, os.close, fcntl.flock


def lock_path() -> Path:
    """One file per account (a file another account made may refuse us)."""
    return Path(tempfile.gettempdir()) / f"hyperspace-tests-live-{os.getuid()}.lock"


def holder(fd: int) -> str:
    """What the lock's holder wrote into the file, `<run id>:<pid>` ("" for none)."""
    try:
        return os.pread(fd, 160, 0).decode("ascii", "replace").strip()
    except OSError:
        return ""


def run_of(who: str) -> tuple[str, int | None]:
    """(run id, pid) of what `holder` read; ("", None) for nothing."""
    rid, _, pid = who.rpartition(":")
    return (rid, int(pid)) if rid and pid.isdigit() else (who, None)


def _alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for(path: Path | None = None, wait_s: float | None = None,
             poll_s: float = POLL_S, run: str = "",
             run_wait_s: float | None = None) -> tuple[int | None, str]:
    """(an open file descriptor holding the exclusive lock on `path` —
    the machine's, `lock_path()`, by default — and ""), or (None, the
    reason) when the wait ran out. Behind a live worker of `run` the wait
    is not counted; behind another run's holder each run's time is
    counted on its own up to `wait_s` (`WAIT_S`, read at the call);
    behind a holder that names no run — or names `run` with a pid that is
    gone — up to `run_wait_s` (`RUN_WAIT_S`). With no `run` every holder
    is another run's, waited for `wait_s`."""
    path = lock_path() if path is None else Path(path)
    wait_s = WAIT_S if wait_s is None else wait_s
    run_wait_s = RUN_WAIT_S if run_wait_s is None else run_wait_s
    fd = _open(path, os.O_RDWR | os.O_CREAT, 0o600)
    behind: dict[str, float] = {}           # holder's run id ("" none) → time behind it
    last = time.monotonic()
    try:
        while True:
            try:
                _flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                now, (rid, pid) = time.monotonic(), run_of(holder(fd))
                step, last = now - last, now
                if run and rid == run and _alive(pid):
                    time.sleep(poll_s)              # our own run's turn: not counted
                    continue
                key = rid if rid and (not run or rid != run) else ""
                behind[key] = behind.get(key, 0.0) + step
                bound = wait_s if key or not run else max(wait_s, run_wait_s)
                if behind[key] >= bound:
                    _close(fd)
                    if key or not run:
                        return None, f"{SKIP_REASON} ({key or 'no id'}) past {bound:g} s"
                    return None, f"{UNKNOWN_REASON} past {bound:g} s"
                time.sleep(poll_s)
        if run:                             # written whole, then trimmed: no empty moment
            data = f"{run}:{os.getpid()}".encode("ascii", "replace")
            os.pwrite(fd, data, 0)
            os.ftruncate(fd, len(data))
        return fd, ""
    except BaseException:
        _close(fd)
        raise


def acquire(path: Path | None = None, wait_s: float | None = None,
            poll_s: float = POLL_S, run: str = "",
            run_wait_s: float | None = None) -> int | None:
    """`wait_for`'s file descriptor, or None when the wait ran out."""
    return wait_for(path, wait_s, poll_s, run, run_wait_s)[0]


def release(fd: int) -> None:
    """Clear the id, then let go: an empty file is a free lock or a holder
    that names no run, never a run that has left."""
    try:
        with contextlib.suppress(OSError):
            os.ftruncate(fd, 0)
        _flock(fd, fcntl.LOCK_UN)
    finally:
        _close(fd)


@contextlib.contextmanager
def held(path: Path | None = None, wait_s: float | None = None, poll_s: float = POLL_S,
         run: str = "", run_wait_s: float | None = None):
    """Hold the lock for the block. Yields None when held, else the reason
    the caller skips with: whose holder it waited behind and how long, or
    that the lock file cannot be opened or locked (an OSError:
    permissions, ENOLCK)."""
    fd, why_not = None, None
    try:
        fd, why_not = wait_for(path, wait_s, poll_s, run, run_wait_s)
    except OSError as e:
        why_not = f"the live-device lock cannot be taken: {e}"
    if fd is None:                      # (yielded outside the handler: a skip
        yield why_not                   # thrown in here chains no OSError)
        return
    try:
        yield None
    finally:
        release(fd)
