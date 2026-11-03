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
AUDIO_CHANNELS = 2      # stereo, by the resampler: mono on both sides at −3 dB (its centre mix), surround downmixed
AUDIO_WINDOW_S = 120.0  # the memory bound: a longer track is held as this much around the position
AUDIO_RECENTRE_S = AUDIO_WINDOW_S / 4   # the window follows once the position is this far off its centre
AUDIO_WINDOW_BYTES = int(AUDIO_WINDOW_S * AUDIO_RATE) * AUDIO_CHANNELS * 4   # 46 MB, float32
AUDIO_RETRY_S = 1.0     # a window that failed or came back empty is tried again once the position moved this far
_GROW_S = 2.0           # a track of unknown length starts with this much buffer and doubles
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


def _start_of(stream) -> float:
    """Where a stream's timeline begins, in container seconds: its
    `start_time`, 0 when the container gives none. The video's is the
    transport's zero (`_play`'s `start`) and the soundtrack's `origin` —
    the one expression for both, so the two can never disagree."""
    return float((stream.start_time or 0) * stream.time_base)


def _audio_end(container, stream, origin: float) -> float:
    """Where the audio track ends, in transport seconds (the video's first
    frame is 0): the stream's own start less `origin`, plus its length —
    a track whose first pts is after the video's (AAC priming, an edit
    list, a screen recording) ends that much later than its length. The
    container's end stands in when the stream gives no length. 0 when
    neither says."""
    tb = stream.time_base
    if stream.duration is not None and tb is not None:
        return max(_start_of(stream) - origin + float(stream.duration * tb), 0.0)
    if container.duration:
        return max(((container.start_time or 0) + container.duration) / 1_000_000.0 - origin, 0.0)
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
        if self._thread is not None:
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
        t, self._thread = self._thread, None
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
    enabled, `status` is FETCHING until the file is probed and whenever the
    wanted position is outside what is held (a reader there hears silence
    until the window arrives), READY while it is inside, NO_AUDIO (no
    track, or none decodable: `read` is silence) or `error(...)` (the
    window that failed; an older one stays readable, and the next move of
    `AUDIO_RETRY_S` tries again). `duration` is where the track ends in
    transport seconds, `rate` and `channels` what `read` returns in.
    `want(t)` is the transport's position in seconds, as the video's.
    `read(at, n)` is the n samples from sample `at` as an (n, channels)
    float32 array, zeros wherever nothing is held; it never blocks and
    never raises. `held` is the span of seconds in memory, `nbytes` what
    that costs. A track held whole ends its thread and closes its file
    once it is in."""

    rate = AUDIO_RATE
    channels = AUDIO_CHANNELS

    def __init__(self, path: Path):
        super().__init__(f"media-audio-{Path(path).name}")
        self.path = Path(path)
        self._status = OFF
        self.enabled = False        # something asks for sound
        self.duration = 0.0
        self.whole = False          # the whole track is held, never re-decoded
        self._opened = False
        self._win: _Window | None = None

    @property
    def status(self) -> str:
        st = self._status
        if st != READY:
            return st
        w, at = self._win, round(self._want * self.rate)
        return READY if w is not None and w.start <= at <= w.end else FETCHING

    @status.setter
    def status(self, value: str) -> None:
        self._status = value

    # -- called from the frame thread (through the VideoSource) -----------

    def open(self) -> None:
        """The source opened; the thread starts only once sound is asked for."""
        self._opened = True
        if self.enabled:
            self._start()

    def close(self, timeout: float = CLOSE_JOIN_S) -> None:
        """The source closed for good: the thread ends, and an `enable`
        from here on starts nothing."""
        self._opened = False
        super().close(timeout)

    def enable(self) -> None:
        """Something asks for sound: decode from here on (and from `open`)."""
        self.enabled = True
        if self._opened:
            self._start()

    def disable(self) -> None:
        """Nothing asks any more: the thread ends, the samples are let go;
        the source stays open, so `enable` brings them back."""
        self.enabled = False
        _Follower.close(self)
        self._win = None
        self.whole = False
        self.status = OFF

    def want(self, t: float) -> None:
        self._want = float(t)
        if self._thread is not None and not (self.whole and self._win is not None):
            self._wake.set()        # a whole track held has nothing left to follow

    # -- what V2 reads ----------------------------------------------------

    def read(self, at: int, n: int, out: np.ndarray | None = None) -> np.ndarray:
        """`n` samples from sample `at` (counted at `rate` from the start of
        the clip) as (n, channels) float32: the track where it is held,
        zeros everywhere else. The reader's own array, safe to write —
        `out[:n]` when the reader hands one in (plan 45 V2: the mixer's
        callback allocates nothing), a new one otherwise."""
        n = max(int(n), 0)
        if out is None:
            out = np.zeros((n, self.channels), np.float32)
        else:
            out = out[:n]
            out.fill(0.0)
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
            # the transport's zero is the video's first frame (as `_play`'s
            # `start`); audio pts are on the same container timeline
            origin = _start_of(container.streams.video[0]) if container.streams.video else 0.0
            self.duration = _audio_end(container, stream, origin)
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
        old one readable; once the position has moved `AUDIO_RETRY_S` it is
        tried again. Nothing is published once `stop` is set: the samples
        were let go, or are another thread's by now."""
        centre = None        # of the window held
        failed_at = None     # the position when the last window failed or came back empty
        while not stop.is_set():
            self._wake.clear()
            want = self._want
            a, b = audio_window(want, self.duration)
            c = (a + b) / 2.0
            if failed_at is not None:
                due = abs(want - failed_at) >= AUDIO_RETRY_S
            else:
                due = centre is None or (not self.whole and abs(c - centre) > AUDIO_RECENTRE_S)
            if not due:
                self._wake.wait(_IDLE_S)
                continue
            try:
                win = self._decode(container, stream, origin, a, b, stop)
            except Exception as e:  # noqa: BLE001 — this window's failure, not the track's
                if stop.is_set():
                    return
                self.status = error(f"{type(e).__name__}: {e}")
                failed_at = want
                continue
            if win is None or stop.is_set():   # stopped, or the transport moved on: start over
                if stop.is_set():
                    return
                continue
            if len(win.data) == 0:
                failed_at = want
                if self.whole:                  # says it has sound, and has none to decode
                    self.status = NO_AUDIO
                continue
            self._win = win
            self.status = READY
            centre, failed_at = c, None
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
        decoded straight into one buffer (`_Buffer`) — no other copy is
        held. Each resampled frame is laid by its own time, the pts the
        resampler gives it, so a gap or a dropped frame in the file is
        silence there and moves nothing after it. None when stopped, or
        when the transport left for another window before this one was
        done (`_left`)."""
        import av
        tb = float(stream.time_base)
        container.seek(max(int((a + origin) / tb), 0), stream=stream, backward=True)
        resampler = av.AudioResampler(format="flt", layout="stereo", rate=self.rate)
        cap = round((b - a) * self.rate)
        known = self.duration > 0.0
        buf = _Buffer(cap if known else min(cap, round(_GROW_S * self.rate)), cap, self.channels)
        base = (a + origin) * self.rate     # the window's first row, in output samples
        nxt = 0                             # the row after the last laid, for a frame with no pts

        def lay(o) -> None:
            nonlocal nxt
            if o.pts is not None and o.time_base is not None:
                row = round(o.pts * float(o.time_base) * self.rate - base)
            else:
                row = nxt
            nxt = buf.lay(row, _packed(o))

        for fr in container.decode(stream):
            if stop.is_set() or (not self.whole and self._left(a, b)):
                return None
            if fr.pts is None:
                continue
            if fr.pts * tb - origin > b:
                break
            for o in resampler.resample(fr):
                lay(o)
        for o in resampler.resample(None):
            lay(o)
        data = buf.done()
        data.flags.writeable = False
        return _Window(round(a * self.rate), data)


class _Buffer:
    """A window's rows, laid by position into one float32 array: of the
    window's size when the track's length is known, else `size` rows that
    double (to `cap`) as rows land, so a short clip of unknown length never
    allocates the whole window. `done` is the rows filled — the array
    itself when it is already that size, else one trim."""

    def __init__(self, size: int, cap: int, channels: int):
        self.cap = cap
        self.data = np.zeros((max(size, 0), channels), np.float32)
        self.filled = 0

    def lay(self, at: int, chunk: np.ndarray) -> int:
        """`chunk` from row `at`, clipped to 0..cap; returns the row after it."""
        end = min(at + len(chunk), self.cap)
        if end > len(self.data):
            grown = np.zeros((min(self.cap, max(end, 2 * len(self.data))), self.data.shape[1]),
                             np.float32)
            grown[:len(self.data)] = self.data
            self.data = grown
        lo, hi = max(at, 0), min(end, len(self.data))
        if hi > lo:
            self.data[lo:hi] = chunk[lo - at:hi - at]
            self.filled = max(self.filled, hi)
        return at + len(chunk)

    def done(self) -> np.ndarray:
        if self.filled == len(self.data):
            return self.data
        return self.data[:self.filled].copy()


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
        start = _start_of(stream)
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

