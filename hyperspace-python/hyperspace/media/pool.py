"""The media worker pool: three threads for jobs that end (a still decode,
a folder scan, a live feed let go), and the thumbnails' one worker of
their own. Blocking reads that never end belong on the source's own
thread. Created on first use, so importing costs nothing.

The workers are daemon threads (`DaemonExecutor`), not the standard
library's: `concurrent.futures` joins every `ThreadPoolExecutor` worker at
interpreter exit, even after `shutdown(wait=False)`, so one worker stuck
reading a cloud file still downloading would hold Quit for as long as the
download takes (final review A-I1). A daemon worker dies with the process.

Thumbnails queue on their own worker (`submit_thumb`), so a fast scroll
through a big new library never puts a still a channel wants behind a
pile of thumbnail jobs (A-m2), and at most `THUMB_QUEUE` wait: past that
the oldest not yet started is dropped (its row has scrolled past; asked
again, it queues again).

App exit shares one deadline (A-m1): `begin_exit` starts it, and every
close on the way out waits `left(its own bound)` at most, so the whole
exit is held to `EXIT_S` rather than the sum of each part's bound."""

from __future__ import annotations

import collections
import itertools
import queue
import threading
import time
from concurrent.futures import Future

WORKERS = 3
THUMB_QUEUE = 16     # thumbnail jobs waiting at most; the oldest past this is dropped
EXIT_S = 2.0         # the app's whole exit (review focus 3)


class DaemonExecutor:
    """`concurrent.futures.ThreadPoolExecutor`'s `submit` and `shutdown`
    on daemon threads that nothing joins at interpreter exit. Workers
    start as jobs arrive, up to `workers`, and are named
    ``<name>-<n>``."""

    def __init__(self, workers: int, name: str):
        self._n = workers
        self._name = name
        self._q: queue.SimpleQueue = queue.SimpleQueue()
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []
        self._count = itertools.count()
        self._shut = False

    def submit(self, fn, *a, **kw) -> Future:
        f: Future = Future()
        with self._lock:
            if self._shut:
                raise RuntimeError("cannot schedule new futures after shutdown")
            self._q.put((f, fn, a, kw))
            if len(self._threads) < self._n:
                t = threading.Thread(target=self._run, name=f"{self._name}-{next(self._count)}",
                                     daemon=True)
                self._threads.append(t)
                t.start()
        return f

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                return
            f, fn, a, kw = item
            if not f.set_running_or_notify_cancel():
                continue
            try:
                r = fn(*a, **kw)
            except BaseException as e:  # noqa: BLE001 — the job's, handed to its Future
                f.set_exception(e)
            else:
                f.set_result(r)

    def shutdown(self, wait: bool = True, cancel_futures: bool = False,
                 timeout: float | None = None) -> None:
        """No more jobs; with `cancel_futures` the queued ones are dropped.
        `wait` joins the workers, `timeout` s at most when given."""
        with self._lock:
            self._shut = True
            threads = list(self._threads)
        if cancel_futures:
            while True:
                try:
                    item = self._q.get_nowait()
                except queue.Empty:
                    break
                if item is not None:
                    item[0].cancel()
        for _ in threads:
            self._q.put(None)
        if wait:
            end = None if timeout is None else time.monotonic() + timeout
            for t in threads:
                t.join(None if end is None else max(end - time.monotonic(), 0.0))

    @property
    def threads(self) -> list[threading.Thread]:
        return list(self._threads)


# a hot reload reruns this module: the executors and the exit deadline
# already made carry over, so app exit still finds them (A-m4)
_lock = globals().get("_lock") or threading.Lock()
_pool: DaemonExecutor | None = globals().get("_pool")
_thumbs: DaemonExecutor | None = globals().get("_thumbs")
_thumb_jobs: collections.deque = globals().get("_thumb_jobs") or collections.deque()
_exit_at: float | None = globals().get("_exit_at")


def submit(fn, *a, **kw) -> Future:
    global _pool
    with _lock:
        if _pool is None:
            _pool = DaemonExecutor(WORKERS, "media-pool")
        return _pool.submit(fn, *a, **kw)


def submit_thumb(fn, *a, **kw) -> Future:
    """A thumbnail job on the thumbnails' own worker; past `THUMB_QUEUE`
    waiting, the oldest not yet started is cancelled."""
    global _thumbs
    with _lock:
        if _thumbs is None:
            _thumbs = DaemonExecutor(1, "media-thumb")
        f = _thumbs.submit(fn, *a, **kw)
        jobs = _thumb_jobs
        while jobs and jobs[0].done():
            jobs.popleft()
        jobs.append(f)
        waiting = [j for j in jobs if not j.running() and not j.done()]
        for old in waiting[:max(len(waiting) - THUMB_QUEUE, 0)]:
            old.cancel()
        return f


def shutdown(wait: bool = True, timeout: float | None = None) -> None:
    """Stop the pool and the thumbnail worker (app exit); a later `submit`
    starts fresh ones. Queued jobs are dropped; a running one finishes on
    its daemon thread or dies with the process."""
    global _pool, _thumbs
    with _lock:
        ps, _pool, _thumbs = (_pool, _thumbs), None, None
        _thumb_jobs.clear()
    for p in ps:
        if p is not None:
            p.shutdown(wait=wait, cancel_futures=True,
                       timeout=None if timeout is None else left(timeout))


# -- the exit deadline ---------------------------------------------------------

def begin_exit(budget: float = EXIT_S) -> None:
    """App exit starts: every `left` from now on counts down to one deadline."""
    global _exit_at
    _exit_at = time.monotonic() + budget


def left(bound: float) -> float:
    """How long a close on the way out may wait: `bound`, cut to what is
    left of the exit's deadline once `begin_exit` has run."""
    at = _exit_at
    if at is None:
        return bound
    return min(bound, max(at - time.monotonic(), 0.0))


def end_exit() -> None:
    """Forget the deadline (tests; an exit that was not)."""
    global _exit_at
    _exit_at = None
