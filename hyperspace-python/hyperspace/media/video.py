"""Video files as sources: decoded by PyAV on the source's own thread.

The frame thread only calls `want(t)` (it stores a float) and `latest()`.
This thread keeps the decoder at the wanted time: forward within a second
it just keeps decoding, anywhere else it seeks to the keyframe before the
time and decodes forward to it. Only the frame finally chosen is converted
to RGBA. When a scrub proxy exists (see `proxy.py`) the clip is read from
that, so every frame is a keyframe; when there is none and the clip is
short, one is queued on the proxy worker for the next open.

**The soundtrack** (plan 45, V1). A video's audio track is decoded to
memory by a `Soundtrack` on a second thread of the source's own
(`media-audio-<name>`), always from the original file (a proxy is MJPEG
with no audio), as float32 stereo at `AUDIO_RATE`, so the mixer (V2) adds
every track in one buffer at one rate. **The transport is the one clock
and the soundtrack is its slave**: the same `want(t)` the video thread
follows reaches the soundtrack, which keeps the samples around that
position; nothing here has a clock, a stream or a playhead of its own,
and V4 reads samples by the transport's position. **Nothing is read until
something asks for sound** (`Soundtrack.enable`, V2's play-audio toggle):
a window decode demuxes the video's packets too, so an unheard soundtrack
would read the whole clip for nothing. **The memory policy**: a track of
`AUDIO_WINDOW_S` or less is held whole (static, never re-decoded; its
thread then ends and its file closes); a longer one is held as a window of
`AUDIO_WINDOW_S` centred on the wanted position, decoded straight into one
buffer of the window's size and re-decoded when the position is more than
`AUDIO_RECENTRE_S` from the window's centre, so a two-hour film holds
`AUDIO_WINDOW_BYTES` (46 MB) — twice that for the moment a new window is
decoded while the old one stays readable — never the film. `read(at, n)`
is zeros wherever nothing is held, so a reader outside the window hears
silence, never blocks and never raises. Nothing in this module plays
sound."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import pool, proxy
from .frame import CAP_FILE, MediaFrame, to_rgba
from .source import FETCHING, READY, Latest, error

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".gif", ".avi"}

PROXY_MAX_S = 600.0     # longer clips get no proxy
SEQUENTIAL_S = 1.0      # moving forward this far or less: decode on, no seek
_IDLE_S = 0.05
CLOSE_JOIN_S = 1.0      # how long close waits for the thread; then it is abandoned

# the soundtrack (plan 45 V1)
AUDIO_RATE = 48_000     # every track is resampled to this: the mixer's one rate (V2)
AUDIO_CHANNELS = 2      # stereo: mono is doubled, surround downmixed, by the resampler
AUDIO_WINDOW_S = 120.0  # the memory bound: a longer track is held as this much around the position
AUDIO_RECENTRE_S = AUDIO_WINDOW_S / 4   # the window follows once the position is this far off its centre
AUDIO_WINDOW_BYTES = int(AUDIO_WINDOW_S * AUDIO_RATE) * AUDIO_CHANNELS * 4   # 46 MB, float32
NO_AUDIO = "none"       # a Soundtrack's status for a file with no audio track: silence, no note
OFF = "off"             # a Soundtrack's status while nothing asks for sound: no thread, no read


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


# -- the soundtrack ----------------------------------------------------------

def audio_window(want: float, duration: float) -> tuple[float, float]:
    """The seconds of the track a soundtrack holds for a transport at
    `want`: the whole track when it is `AUDIO_WINDOW_S` or shorter, else
    `AUDIO_WINDOW_S` centred on `want` and kept inside the track. A track
    of unknown length (0) is windowed from `want` on, never held whole."""
    d = max(float(duration), 0.0)
    w = AUDIO_WINDOW_S
    if d <= 0.0:
        start = max(float(want) - w / 2.0, 0.0)
        return start, start + w
    if d <= w:
        return 0.0, d
    start = min(max(float(want) - w / 2.0, 0.0), d - w)
    return start, start + w


def _audio_duration(container, stream) -> float:
    """The audio stream's length in seconds (the container's when the
    stream does not say)."""
    if stream.duration is not None and stream.time_base is not None:
        return max(float(stream.duration * stream.time_base), 0.0)
    if container.duration:
        return max(container.duration / 1_000_000.0, 0.0)
    return 0.0


class _Follower:
    """A source's own thread, following the transport: `open` starts it,
    `want(t)` hands it the transport's position (a float store and a wake),
    `close` stops it and joins it `timeout` at most. Each start gets a stop
    event of its own, handed to `_run`: a thread `close` abandoned (stuck in
    `av.open` on a file still downloading, A-I1) sees *its* stop when the
    open returns and ends, and can never resume beside the thread a later
    `open` started. A subclass defines `_run(stop)` and keeps `status`."""

    def __init__(self, name: str):
        self._name = name
        self._want = 0.0
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _start(self) -> None:
        if getattr(self, "_thread", None) is not None:
            return
        stop = self._stop = threading.Event()
        self.status = FETCHING
        t = threading.Thread(target=self._run, args=(stop,), name=self._name, daemon=True)
        self._thread = t
        t.start()

    def open(self) -> None:
        self._start()

    def want(self, t: float) -> None:
        self._want = float(t)
        self._wake.set()

    def close(self, timeout: float = CLOSE_JOIN_S) -> None:
        t, self._thread = getattr(self, "_thread", None), None
        if t is None:
            return
        self._stop.set()
        self._wake.set()
        t.join(timeout)

    def _run(self, stop: threading.Event) -> None:
        raise NotImplementedError


@dataclass(frozen=True, eq=False)
class _Window:
    """What a soundtrack holds: `data` (n × channels float32, read-only)
    whose first sample is sample `start` of the track at `AUDIO_RATE`."""

    start: int
    data: np.ndarray

    @property
    def end(self) -> int:
        return self.start + len(self.data)


class Soundtrack(_Follower):
    """A video's audio track in memory, following the transport (see the
    module docstring). **Nothing is read until something asks for sound**:
    `enable()` (V2's play-audio toggle) starts the thread, `disable()` ends
    it and lets the samples go; until then `status` is OFF and the file is
    not opened — a window decode demuxes the video's packets too, so a
    soundtrack nobody hears would read the whole clip for nothing. Once
    enabled, `status` is FETCHING until the file is probed, then READY
    (samples held), NO_AUDIO (no track: `read` is silence for good) or
    `error(...)` (the window that failed; an older one stays readable).
    `duration` is the track's in seconds, `rate` and `channels` what `read`
    returns in. `want(t)` is the transport's position in seconds, as the
    video's. `read(at, n)` is the n samples from sample `at` as an
    (n, channels) float32 array, zeros wherever nothing is held; it never
    blocks and never raises. `held` is the span of seconds in memory,
    `nbytes` what that costs. A track held whole ends its thread and
    closes its file once it is in."""

    rate = AUDIO_RATE
    channels = AUDIO_CHANNELS

    def __init__(self, path: Path):
        super().__init__(f"media-audio-{Path(path).name}")
        self.path = Path(path)
        self.status = OFF
        self.enabled = False        # something asks for sound
        self.duration = 0.0
        self.whole = False          # the whole track is held, never re-decoded
        self._opened = False
        self._win: _Window | None = None

    # -- called from the frame thread (through the VideoSource) -----------

    def open(self) -> None:
        """The source opened; the thread starts only once sound is asked for."""
        self._opened = True
        if self.enabled:
            self._start()

    def enable(self) -> None:
        """Something asks for sound: decode from here on (and from `open`)."""
        self.enabled = True
        if self._opened:
            self._start()

    def disable(self) -> None:
        """Nothing asks any more: the thread ends, the samples are let go."""
        self.enabled = False
        self.close()
        self._win = None
        self.whole = False
        self.status = OFF

    def want(self, t: float) -> None:
        self._want = float(t)
        if self._thread is not None and not self.whole:   # whole: nothing left to follow
            self._wake.set()

    # -- what V2 reads ----------------------------------------------------

    def read(self, at: int, n: int) -> np.ndarray:
        """`n` samples from sample `at` (counted at `rate` from the start of
        the clip) as (n, channels) float32: the track where it is held,
        zeros everywhere else. The reader's own array, safe to write."""
        n = max(int(n), 0)
        out = np.zeros((n, self.channels), np.float32)
        w = self._win
        if w is None or n == 0:
            return out
        at = int(at)
        lo, hi = max(at, w.start), min(at + n, w.end)
        if hi > lo:
            out[lo - at:hi - at] = w.data[lo - w.start:hi - w.start]
        return out

    @property
    def held(self) -> tuple[float, float] | None:
        """(from, to) in seconds of the samples in memory; None with none."""
        w = self._win
        if w is None:
            return None
        return (w.start / self.rate, w.end / self.rate)

    @property
    def nbytes(self) -> int:
        w = self._win
        return 0 if w is None else int(w.data.nbytes)

    # -- the soundtrack's own thread --------------------------------------

    def _run(self, stop: threading.Event) -> None:
        import av
        container = None
        try:
            container = av.open(str(self.path))
            if stop.is_set():        # abandoned while the open hung: touch nothing
                return
            if not container.streams.audio:
                self.status = NO_AUDIO
                return
            stream = container.streams.audio[0]
            self.duration = _audio_duration(container, stream)
            # the transport's zero is the video's first frame (as `_play`'s
            # `start`); audio pts are on the same container timeline
            origin = 0.0
            if container.streams.video:
                vs = container.streams.video[0]
                origin = float((vs.start_time or 0) * vs.time_base)
            self.whole = 0.0 < self.duration <= AUDIO_WINDOW_S
            self._follow(container, stream, origin, stop)
        except Exception as e:  # noqa: BLE001 — a bad track must not kill the app
            if not stop.is_set():
                self.status = error(f"{type(e).__name__}: {e}")
        finally:
            if container is not None:
                try:
                    container.close()
                except Exception:  # noqa: BLE001, S110
                    pass

    def _follow(self, container, stream, origin: float, stop: threading.Event) -> None:
        """Keep the window at the transport's position until stopped — or,
        for a track held whole, until it is in: then the thread ends and
        the file closes. A window that fails or comes back empty leaves the
        old one readable; the next move past the recentre distance tries
        again."""
        centre = None
        while not stop.is_set():
            self._wake.clear()
            a, b = audio_window(self._want, self.duration)
            c = (a + b) / 2.0
            if centre is not None and (self.whole or abs(c - centre) <= AUDIO_RECENTRE_S):
                self._wake.wait(_IDLE_S)
                continue
            try:
                win = self._decode(container, stream, origin, a, b, stop)
            except Exception as e:  # noqa: BLE001 — this window's failure, not the track's
                if stop.is_set():
                    return
                self.status = error(f"{type(e).__name__}: {e}")
                centre = c
            else:
                if win is None:          # stopped, or the transport moved on: start over
                    if stop.is_set():
                        return
                    continue
                centre = c
                if len(win.data):
                    self._win = win
                    self.status = READY
                elif self.whole:         # a track that says it has sound and has none
                    self.status = NO_AUDIO
            if self.whole:
                return

    def _left(self, a: float, b: float) -> bool:
        """Whether the transport has moved far enough from the window
        `a`..`b` that another window is wanted in its place."""
        na, nb = audio_window(self._want, self.duration)
        return abs((na + nb) - (a + b)) / 2.0 > AUDIO_RECENTRE_S

    def _decode(self, container, stream, origin: float, a: float, b: float,
                stop: threading.Event) -> _Window | None:
        """Seconds `a`..`b` of the track (transport time: the container's
        pts less `origin`) as one `_Window` at `rate`, stereo float32,
        decoded straight into one buffer of the window's size — no other
        copy is held. None when stopped, or when the transport left for
        another window before this one was done (`_left`)."""
        import av
        tb = float(stream.time_base)
        container.seek(max(int((a + origin) / tb), 0), stream=stream, backward=True)
        resampler = av.AudioResampler(format="flt", layout="stereo", rate=self.rate)
        cap = round((b - a) * self.rate)
        data = np.zeros((cap, self.channels), np.float32)
        off = None     # the row the first resampled sample lands on (< 0: before `a`)
        n = 0          # resampled samples so far
        for fr in container.decode(stream):
            if stop.is_set() or (not self.whole and self._left(a, b)):
                return None
            if fr.pts is None:
                continue
            t = fr.pts * tb - origin
            if off is None:
                off = round((t - a) * self.rate)
            if t > b:
                break
            for o in resampler.resample(fr):
                n += _lay(data, off + n, _packed(o))
        if off is not None:
            for o in resampler.resample(None):
                n += _lay(data, off + n, _packed(o))
        filled = 0 if off is None else min(max(off + n, 0), cap)
        if filled < cap:
            data = data[:filled].copy()       # hold only what is there
        data.flags.writeable = False
        return _Window(round(a * self.rate), data)


def _lay(data: np.ndarray, at: int, chunk: np.ndarray) -> int:
    """Copy `chunk` into `data` from row `at`, clipped to `data`; returns
    `chunk`'s length, so a caller can count on."""
    lo, hi = max(at, 0), min(at + len(chunk), len(data))
    if hi > lo:
        data[lo:hi] = chunk[lo - at:hi - at]
    return len(chunk)


def _packed(frame) -> np.ndarray:
    """A resampled (packed float, stereo) frame as (n, 2) float32."""
    return frame.to_ndarray().reshape(-1, AUDIO_CHANNELS)


class VideoSource(_Follower):
    kind = "video"
    timed = True
    audio: Soundtrack | None = None    # the track (plan 45); None on a source made before it

    def __init__(self, sid: str, path: Path, cap: tuple[int, int] = CAP_FILE,
                 cache: Path | None = None):
        super().__init__(f"media-video-{Path(path).name}")
        self.sid = sid
        self.path = Path(path)
        self.cap = cap
        self.cache = Path(cache) if cache is not None else None
        self.status = FETCHING
        self.duration = 0.0
        self.fps = 0.0
        self.read_path: Path = self.path   # what is actually decoded
        self.audio = Soundtrack(self.path)  # always from the original: a proxy has no sound
        self._latest = Latest()

    # -- called from the frame thread -------------------------------------

    def open(self) -> None:
        self._start()
        if self.audio is not None:
            self.audio.open()

    def latest(self) -> MediaFrame | None:
        return self._latest.get()

    def want(self, t: float) -> None:
        """The transport's position: the one clock, handed to both threads."""
        super().want(t)
        if self.audio is not None:
            self.audio.want(t)

    def close(self, timeout: float = CLOSE_JOIN_S) -> None:
        """Stop both threads and wait `timeout` at most for the two together
        (less near the app's exit deadline). A thread stuck in `av.open` (a
        file still downloading) is abandoned: it is a daemon and sees its
        own stop when the open returns, so the closer goes on to the next
        source (A-I1)."""
        end = time.monotonic() + pool.left(timeout)
        super().close(max(end - time.monotonic(), 0.0))
        if self.audio is not None:
            self.audio.close(max(end - time.monotonic(), 0.0))

    # -- the source's own thread ------------------------------------------

    def _run(self, stop: threading.Event) -> None:
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
            if stop.is_set():
                return
            self.read_path, self.duration, self.fps = read, duration, fps
            if (self.cache is not None and read == self.path
                    and duration <= PROXY_MAX_S):
                proxy.submit(self.path, self.cache)
            self._play(container, stream, stop)
        except Exception as e:  # noqa: BLE001 — a bad file must not kill the app
            if not stop.is_set():
                self.status = error(f"{type(e).__name__}: {e}")
        finally:
            if container is not None:
                try:
                    container.close()
                except Exception:  # noqa: BLE001, S110
                    pass

    def _play(self, container, stream, stop: threading.Event) -> None:
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
        while not stop.is_set():
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
                if stop.is_set():
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
                if stop.is_set():
                    return
                rgba = cur.reformat(width=size[0], height=size[1],
                                    format="rgba").to_ndarray()
                ft = max(when(cur), 0.0)
                self._latest.put(MediaFrame(to_rgba(rgba), ft, round(ft * fps)))
                self.status = READY

