"""The media worker pool: three threads for jobs that end (a still decode,
a thumbnail, a proxy). Blocking reads that never end belong on the
source's own thread. Created on first use, so importing costs nothing."""

from __future__ import annotations

import itertools
import threading
from concurrent.futures import Future, ThreadPoolExecutor

WORKERS = 3

_lock = threading.Lock()
_pool: ThreadPoolExecutor | None = None
_count = itertools.count()


def _name_thread():
    threading.current_thread().name = f"media-pool-{next(_count)}"


def submit(fn, *a, **kw) -> Future:
    global _pool
    with _lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(WORKERS, thread_name_prefix="media-pool",
                                       initializer=_name_thread)
        return _pool.submit(fn, *a, **kw)


def shutdown(wait: bool = True) -> None:
    """Stop the pool (app exit); a later `submit` starts a fresh one."""
    global _pool
    with _lock:
        p, _pool = _pool, None
    if p is not None:
        p.shutdown(wait=wait, cancel_futures=True)
