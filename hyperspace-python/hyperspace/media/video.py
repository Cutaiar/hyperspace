"""Video files as sources: decoded by PyAV on the source's own thread.

The frame thread only calls `want(t)` (it stores a float) and `latest()`.
This thread keeps the decoder at the wanted time: forward within a second
it just keeps decoding, anywhere else it seeks to the keyframe before the
time and decodes forward to it. Only the frame finally chosen is converted
to RGBA. When a scrub proxy exists (see `proxy.py`) the clip is read from
that, so every frame is a keyframe; when there is none and the clip is
short, one is queued on the proxy worker for the next open."""

from __future__ import annotations

import threading
from pathlib import Path

from . import pool, proxy
from .frame import CAP_FILE, MediaFrame, to_rgba
from .source import FETCHING, READY, Latest, error

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".gif", ".avi"}

PROXY_MAX_S = 600.0     # longer clips get no proxy
SEQUENTIAL_S = 1.0      # moving forward this far or less: decode on, no seek
_IDLE_S = 0.05
CLOSE_JOIN_S = 1.0      # how long close waits for the thread; then it is abandoned


def _probe(container, stream) -> tuple[float, float]:
    """(duration in seconds, frames per second) of the opened clip."""
    rate = stream.average_rate or stream.guessed_rate or 25
    fps = float(rate)
    dur = 0.0
    if stream.duration is not None and stream.time_base is not None:
        dur = float(stream.duration * stream.time_base)
    elif container.duration:
        dur = container.duration / 1_000_000.0
    return max(dur, 0.0), fps


class VideoSource:
    kind = "video"
    timed = True

    def __init__(self, sid: str, path: Path, cap: tuple[int, int] = CAP_FILE,
                 cache: Path | None = None):
        self.sid = sid
        self.path = Path(path)
        self.cap = cap
        self.cache = Path(cache) if cache is not None else None
        self.status = FETCHING
        self.duration = 0.0
        self.fps = 0.0
        self.read_path: Path = self.path   # what is actually decoded
        self._latest = Latest()
        self._want = 0.0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- called from the frame thread -------------------------------------

    def open(self) -> None:
        if getattr(self, "_thread", None) is not None:
            return
        self._stop.clear()
        self.status = FETCHING
        t = threading.Thread(target=self._run, name=f"media-video-{self.path.name}",
                             daemon=True)
        self._thread = t
        t.start()

    def latest(self) -> MediaFrame | None:
        return self._latest.get()

    def want(self, t: float) -> None:
        self._want = float(t)
        self._wake.set()

    def close(self) -> None:
        """Stop the thread and wait `CLOSE_JOIN_S` at most (less near the
        app's exit deadline). A thread stuck in `av.open` (a file still
        downloading) is abandoned: it is a daemon and sees `_stop` when the
        open returns, so the closer goes on to the next source (A-I1)."""
        t, self._thread = getattr(self, "_thread", None), None
        if t is None:
            return
        self._stop.set()
        self._wake.set()
        t.join(pool.left(CLOSE_JOIN_S))

    # -- the source's own thread ------------------------------------------

    def _run(self) -> None:
        import av
        container = None
        try:
            read = self.path
            if self.cache is not None:
                read = proxy.proxy_for(self.path, self.cache) or self.path
            container = av.open(str(read))
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            duration, fps = _probe(container, stream)
            if self._stop.is_set():
                return
            self.read_path, self.duration, self.fps = read, duration, fps
            if (self.cache is not None and read == self.path
                    and duration <= PROXY_MAX_S):
                proxy.submit(self.path, self.cache)
            self._play(container, stream)
        except Exception as e:  # noqa: BLE001 — a bad file must not kill the app
            if not self._stop.is_set():
                self.status = error(f"{type(e).__name__}: {e}")
        finally:
            if container is not None:
                try:
                    container.close()
                except Exception:  # noqa: BLE001, S110
                    pass

    def _play(self, container, stream) -> None:
        tb = float(stream.time_base)
        start = (stream.start_time or 0) * tb
        fps = self.fps
        w, h = stream.codec_context.width, stream.codec_context.height
        k = min(self.cap[0] / w, self.cap[1] / h, 1.0)
        size = (max(1, round(w * k)), max(1, round(h * k)))

        def when(fr) -> float:
            return fr.pts * tb - start if fr.pts is not None else 0.0

        it = None
        cur = nxt = None
        last_t = None
        shown = None   # pts of the frame last published
        while not self._stop.is_set():
            self._wake.clear()
            want0 = self._want
            t = min(max(want0, 0.0), self.duration or want0)
            if t == last_t and it is not None:
                self._wake.wait(_IDLE_S)
                continue
            last_t = t
            if it is None or (cur is not None and (
                    t < when(cur) - 1e-6 or t - when(cur) > SEQUENTIAL_S)):
                container.seek(int((t + start) / tb), stream=stream, backward=True)
                it = container.decode(stream)
                cur = nxt = None
            moved = False
            while True:
                if self._stop.is_set():
                    return
                if self._want != want0:   # the transport moved on: don't finish this one
                    moved = True
                    break
                if nxt is None:
                    nxt = next(it, None)
                    if nxt is None:
                        break
                if cur is None or when(nxt) <= t + 1e-6:
                    cur, nxt = nxt, None
                else:
                    break
            if moved:
                last_t = None
                continue
            if cur is not None and cur.pts != shown:
                shown = cur.pts
                if self._stop.is_set():
                    return
                rgba = cur.reformat(width=size[0], height=size[1],
                                    format="rgba").to_ndarray()
                ft = max(when(cur), 0.0)
                self._latest.put(MediaFrame(to_rgba(rgba), ft, round(ft * fps)))
                self.status = READY

