"""Scrub proxies: an intra-frame copy of a clip, so a jog wheel or a macro
sweeping `pos` can land on any frame without decoding from the last
keyframe. MJPEG in a .mov, no larger than 1280×720, the same frame rate.
They live in the app's own cache (`<home>/media-cache/proxies/`), never in
the shared folder, and are keyed by name, size and mtime so a replaced
clip makes a new proxy rather than reading a stale one."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from .pool import DaemonExecutor

MAX_SIZE = (1280, 720)


class _Cancelled(Exception):
    pass


# One worker of its own, so a transcode never takes a media.pool thread and
# only one runs at a time. cancel_all (app exit) must not wait for it: the
# worker is a daemon thread (pool.DaemonExecutor), so a transcode still
# running never holds the interpreter's exit either (final review A-m4).
# A hot reload reruns this module: the worker and the flags already made
# carry over, so cancel_all at exit still reaches a job in flight
_lock = globals().get("_lock") or threading.Lock()
_exec: DaemonExecutor | None = globals().get("_exec")
_flags: dict[str, threading.Event] = globals().get("_flags") or {}   # queued or running, by clip


def submit(path: Path, cache: Path) -> bool:
    """Queue a proxy for `path` unless one is already queued or running.
    True when queued."""
    global _exec
    key = str(path)
    with _lock:
        if key in _flags:
            return False
        if _exec is None:
            _exec = DaemonExecutor(1, "media-proxy")
        flag = _flags[key] = threading.Event()
        _exec.submit(_job, key, Path(path), Path(cache), flag)
        return True


def _job(key: str, path: Path, cache: Path, flag: threading.Event) -> None:
    try:
        if not flag.is_set():
            make_proxy(path, cache, flag)
    except Exception:  # noqa: BLE001 — no proxy just means slower seeks
        pass
    finally:
        with _lock:
            if _flags.get(key) is flag:
                del _flags[key]


def cancel_all() -> None:
    """Stop every queued and running proxy job and the worker, without
    waiting (app exit). A later `submit` starts a fresh worker."""
    global _exec
    with _lock:
        for f in _flags.values():
            f.set()
        ex, _exec = _exec, None
    if ex is not None:
        ex.shutdown(wait=False, cancel_futures=True)


def _key(path: Path) -> str:
    st = Path(path).stat()
    return f"{Path(path).stem}-{st.st_size}-{st.st_mtime_ns}.mov"


def proxy_for(path: Path, cache: Path) -> Path | None:
    """The finished proxy for `path` in `cache`, or None. Never raises."""
    try:
        p = Path(cache) / _key(path)
        return p if p.is_file() else None
    except OSError:
        return None


def make_proxy(path: Path, cache: Path,
               cancel: threading.Event | None = None) -> Path | None:
    """Write the proxy for `path` into `cache` and return its path. It is
    written to a temporary name and renamed, so `proxy_for` never sees a
    half-written file. `cancel` is checked every frame: when set, the
    temporary file is removed and None comes back. Raises if the clip will
    not decode. Runs on the proxy worker (see `submit`)."""
    import av

    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    final = cache / _key(path)
    tmp = final.with_name(final.stem + ".tmp.mov")
    try:
        with av.open(str(path)) as src:
            vs = src.streams.video[0]
            vs.thread_type = "AUTO"
            rate = vs.average_rate or vs.guessed_rate or 25
            w, h = vs.codec_context.width, vs.codec_context.height
            k = min(MAX_SIZE[0] / w, MAX_SIZE[1] / h, 1.0)
            w, h = max(2, round(w * k) // 2 * 2), max(2, round(h * k) // 2 * 2)
            with av.open(str(tmp), "w", format="mov") as dst:
                out = dst.add_stream("mjpeg", rate=rate)
                out.width, out.height, out.pix_fmt = w, h, "yuvj420p"
                out.options = {"qmin": "2", "qmax": "5"}
                n = 0
                for fr in src.decode(vs):
                    if cancel is not None and cancel.is_set():
                        raise _Cancelled
                    f = fr.reformat(width=w, height=h, format="yuvj420p")
                    f.pts = n
                    f.time_base = out.codec_context.time_base
                    n += 1
                    for pkt in out.encode(f):
                        dst.mux(pkt)
                for pkt in out.encode():
                    dst.mux(pkt)
            if n == 0:
                raise ValueError("no frames")
        os.replace(tmp, final)
    except _Cancelled:
        tmp.unlink(missing_ok=True)
        return None
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return final
