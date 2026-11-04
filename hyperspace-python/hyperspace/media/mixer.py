"""The media mixer (plan 45 V2, V4): the channels' video sound, summed into
one output stream, its read heads the transport's slaves.

**The transport is the one clock** (plan 45, "no second time base"). The
frame thread hands the mixer, once a frame (`MediaState.poll`, after the
transports are stepped), a tuple of `Voice`s: for each channel whose
play-audio toggle is on and whose source has a soundtrack, the `Soundtrack`,
the playhead in seconds the transport was just stepped to, the channel's
gain, the transport's `velocity` (signed), its `wrap` (the loop's length) and
a key saying whose it is.

**The callback reads sequentially from a head of its own, slewed toward the
transport** (V4). The audio and display clocks are never locked, so reading
each block at the last playhead (V2) repeated or skipped a block now and
then. Each voice now has a `_Head`, written only by the callback, that moves
`speed × frames` source samples a block and is resampled (linear) by that
speed, which glides from last block's to this block's inside the block: at
rate 1 the samples come out one after another, whatever the phase of the two
clocks, and any other rate, reverse and a drag of `pos` sound like tape.

**The head is a slave, not a second time base.** Nothing reads it but the
callback: the picture, the window, the analyzer and the transport never ask
where it is, and it has no way to run on alone. Against the playhead,
carried forward by the velocity for the blocks since that playhead came
(`since`, zeroed by every feed), it does one of these a block:

- within `DEAD` samples: nothing. That is the jitter of the two clocks. At
  rate ±1 it also comes back to whole samples, so the output is the track's
  own samples again and not an interpolation after a slew;
- beyond that and up to `CUT`: slews, the speed trimmed by the excess over
  `TAU_S`, so a small error is a small bend of pitch and never a jump (the
  trim at most `TRIM_MAX` of the speed, so it never stops the tape or turns it);
- beyond `CUT` (a scrub, a far jog): cuts, the block a crossfade from where
  the head was to where the transport is;

(`DEAD` and `CUT` scale with the speed above 1: the clocks' jitter is a
time, so in samples of source it grows with the rate);
- the transport at rest, or no feed for `STALE_S` (the frame thread stuck):
  it stops and fades, and once silent sits on the playhead. It never creeps
  toward a stopped transport, and it never free-runs.

**The level glides too**, one block at a time, so no start or stop clicks: it
goes to the gain × `fade(speed)`, which is 1 from `FADE_SPEED` up, falling to
0 at `HOLD_SPEED` — **rate 0 is silence**, not one sample held as DC — and to
0 when this block or the next is not wholly held in memory
(`Soundtrack.holds`): **a block outside the window is zeros**, the fade runs
while there are still samples to fade, and the window arriving fades back in.
A voice with nothing to hear yet reads nothing. A silent voice's head sits on
the transport, so it starts exactly there, at speed at once (no glide up from
a stop, which would leave it late for good). A voice gone from the tuple (its
toggle off, its gain 0, its slot changed) gets one more block, fading out
(`_bind`).

**The loop wrap** (`wrap`): the head counts modulo the loop and reads straight
through the seam, sample after sample in either direction, the error measured
the short way round. So the wrap is neither a jump nor a gap, and a clip cut
to loop is seamless; a clip that was not has the click of its own two ends
(no splice fade: heard first, plan 45). The loop's length is the picture's, so
a track ending up to `SEAM_SLACK` before it (a mux mismatch) has that gap
bridged, a line from its last sample to its first, at full level; a track
ending further before it fades out and back; one running past it is cut at
the picture's end. **No head is prefetched**: a clip up
to `AUDIO_WINDOW_S` is held whole, and a longer one's wrap is a fade out and
back in, one window decode later (plan 45, "What changed in the build (V4)").

The callback allocates nothing once warm: its buffers are kept (`_warm`,
remade only if PortAudio asks for another size), a voice is read through
`Soundtrack.read(..., out=)` into `_src` and resampled into `_one` with
`out=`. A `_Head` is made on the frame thread (`_bind`), never here.

The stream is opened lazily — never until a channel's sound is first
turned on (nothing until something asks, as V1's soundtrack; a hold or a
gain at off still asks) — on a thread of its own (``media-mixer-open``),
so a slow CoreAudio open never holds the frame thread. Once open it stays
open, playing silence while no channel plays, until `close` (app exit,
`MediaState.close`); a failed open, or a stream that stops under us (its
`active` false: a device unplugged), is tried again `RETRY_S` after the
failure while a channel still asks. The callback never blocks and
never raises: a voice whose `read` raises or hands back the wrong shape is
skipped (`errors` counts them) and anything else wrong is silence.

**The analyzer can listen to the mix** (plan 45 V3). `listen(ring)` hands
the mixer the analyzer's input ring (`audio._Ring`, `AudioEngine.start_mix`);
each callback then pushes the block it just wrote to the output — after the
gains and after the clip, what the room hears — as mono, the mean of L and
R, into that ring, and a callback with no voice pushes a block of zeros so
the bands decay as they do on a paused track. The push is one more copy into
a buffer kept for it (`_mono`); it counts nothing and moves nothing: the
analyzer drains the ring once a frame exactly as it drains the mic's.
`listen(None)` stops it. The ring is one reference, read once a callback.

`sounddevice` is imported only when the stream is first opened (the
package's rule: importing the app pulls no adapter library)."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from typing import Any, NamedTuple

import numpy as np

from . import pool
from .video import AUDIO_CHANNELS, AUDIO_RATE

BLOCK = AUDIO_RATE // 60      # 800 samples: one 60 Hz frame a callback
RETRY_S = 5.0                 # a failed open is tried again this long after, while asked
CLOSE_BUDGET_S = 0.5          # how long `close` waits for an open still under way
CEILING = 1.0                 # the sum is clipped here: gain is the performer's to set

# -- the read head (V4; the numbers are judged by ear: hand checks 510-513)
HOLD_SPEED = 1e-3             # slower than this (a hold, a jog's coast dying out) is silent
FADE_SPEED = 0.05             # slower than this the level falls with the speed
MAX_SPEED = 16.0              # the most source a block reads: × BLOCK bounds `_src`
DEAD = 1.25 * BLOCK           # samples × max(1, |speed|): the clocks' phase (a block) + frame jitter
TAU_S = 0.25                  # the slew: the error beyond `DEAD` is closed at this time constant
TRIM_MAX = 0.5                # the slew: at most this share of the speed; never stops the tape
CUT = 0.25 * AUDIO_RATE       # samples × max(1, |speed|): beyond this the head cuts
SEAM_SLACK = AUDIO_RATE // 20 # a track this much shorter than its loop still loops seamlessly
STALE_S = 1.0                 # no feed for this long and the head stops: never free-runs
MIN_WRAP = AUDIO_RATE // 1000 # a loop shorter than this is no loop: bounds `_fetch`'s reads


class Voice(NamedTuple):
    """One channel heard, this frame (the frame thread's, read by the
    callback). `speed` is the transport's signed velocity, `wrap` the length
    it loops on in seconds (0: no loop), `key` whose voice it is across
    frames — the head follows the key — and the track when None."""

    track: Any
    at: float                 # the playhead just stepped, in seconds
    gain: float
    speed: float = 1.0
    wrap: float = 0.0
    key: Any = None


class _Head:
    """A voice's read position, made on the frame thread and from then on
    written only by the callback (module docstring). `seen` is the feed it
    last read, `since` the samples it has moved since that feed."""

    __slots__ = ("at", "level", "seen", "since", "speed")

    def __init__(self):
        self.at: float | None = None      # None: the first block starts at the transport
        self.speed = 0.0
        self.level = 0.0
        self.seen = None
        self.since = 0


def _default_stream(**kw):
    import sounddevice as sd
    return sd.OutputStream(**kw)


class Mixer:
    """One output stream for every channel's video sound (module docstring).

    The frame thread calls `feed(voices, asked)` once a frame and `close` at
    exit; the stream's thread calls `_callback`. `state` is "off" (never
    asked), "opening", "open", "closed" or "error: …"; `playing` the voices
    in the last feed that are moving, `underruns` the callbacks PortAudio flagged as an
    output underflow, `errors` the voice reads that raised."""

    def __init__(self, make: Callable | None = None):
        self._make = make if make is not None else _default_stream
        self._lock = threading.Lock()
        self._stream = None
        self._opener: threading.Thread | None = None
        self._failed_at = -1e9
        self._closed = False
        self.voices: tuple[Voice, ...] = ()
        self._heads: dict = {}       # the frame thread's: key → (head, its last voice)
        self._live: tuple = ()       # (voice, head) for the callback: one swap, one read
        self.state = "off"
        self.underruns = 0
        self.errors = 0
        self._warm(BLOCK)            # the callback's own buffers
        self.tap = None       # plan 45 V3: the analyzer's ring, or None (`listen`)
        self.tap_errors = 0   # pushes into that ring that raised (not voice reads)
        self._mono = np.zeros(BLOCK, np.float32)

    # -- the frame thread ---------------------------------------------------

    @property
    def playing(self) -> int:
        return sum(abs(v.speed) >= HOLD_SPEED for v in self.voices)

    @property
    def failed(self) -> bool:
        """The stream could not be opened, or stopped under us: SYSTEM warns."""
        return self.state.startswith("error")

    def feed(self, voices: tuple[Voice, ...], asked: bool | None = None) -> None:
        """This frame's voices (one swap). `asked` — some channel's sound is
        on, heard or not yet (a hold, gain off): the stream is opened then,
        so it is up before the sound is; it defaults to any voice. A stream
        that has stopped under us (a device unplugged, CoreAudio gone) is
        dropped and opened again `RETRY_S` later. Returns at once: the open
        and the drop run on threads of their own."""
        self.voices = tuple(Voice(*v) for v in voices)
        self._live = self._bind(self.voices)
        if self._closed:
            return
        s = self._stream
        if s is not None:
            try:
                alive = bool(getattr(s, "active", True))   # a PortAudio call: may raise
            except Exception:  # noqa: BLE001 — a stream that cannot say is a stopped one
                alive = False
            if alive:
                return
            with self._lock:                   # stopped under us: back to the retry
                if self._stream is not s:
                    return
                self._stream = None
                self._failed_at = time.monotonic()
                self.state = "error: the output stream stopped"
            threading.Thread(target=_shut, args=(s,), name="media-mixer-shut",
                             daemon=True).start()
            return
        if not (bool(self.voices) if asked is None else asked) or self._opener is not None:
            return
        if time.monotonic() - self._failed_at < RETRY_S:
            return
        self.state = "opening"
        t = self._opener = threading.Thread(target=self._open, name="media-mixer-open",
                                            daemon=True)
        t.start()

    def _bind(self, voices: tuple[Voice, ...]) -> tuple:
        """Each voice with its head, a new one made here and not in the
        callback; a voice gone from the tuple stays one more block at gain 0
        while it still sounds and a stream is there to play it, so it fades
        instead of stopping dead, and is let go after."""
        heads, live, seen = self._heads, [], set()
        for v in voices:
            key = v.track if v.key is None else v.key
            seen.add(key)
            held = heads.get(key)
            head = held[0] if held is not None else _Head()
            heads[key] = (head, v)
            live.append((v, head))
        for key in [k for k in heads if k not in seen]:
            head, v = heads[key]
            if head.level > 0.0 and self._stream is not None:     # else no callback will come
                live.append((v._replace(gain=0.0), head))
            else:
                del heads[key]
        return tuple(live)

    def _open(self) -> None:
        try:
            s = self._make(samplerate=AUDIO_RATE, channels=AUDIO_CHANNELS, dtype="float32",
                           blocksize=BLOCK,
                           # through the class, so a hot reload's callback is the new one
                           callback=lambda *a: type(self)._callback(self, *a))
            s.start()
        except Exception as e:  # noqa: BLE001 — no device is silence, said on SYSTEM
            with self._lock:
                self._failed_at = time.monotonic()     # when it failed, not when it began
                self._opener = None
                if not self._closed:
                    self.state = f"error: {type(e).__name__}: {e}"[:160]
            return
        with self._lock:
            self._opener = None
            if not self._closed:
                self._stream = s
                self.state = "open"
                return
        _shut(s)            # closed while it opened: never left playing

    def close(self, budget: float = CLOSE_BUDGET_S) -> bool:
        """App exit: no voice from here on; an open under way waited for and
        the stream aborted and closed (on ``media-mixer-shut``), the two
        together within `budget` s (and the exit's deadline, `pool.left`).
        True when nothing is left running (an open still stuck closes its
        stream itself when it returns; a stuck abort dies with the
        process)."""
        end = time.monotonic() + pool.left(budget)
        with self._lock:
            self._closed = True
            self.voices = ()
            self._live = ()
            self._heads = {}
            t = self._opener
        if t is not None:
            t.join(max(end - time.monotonic(), 0.0))
        with self._lock:
            s, self._stream = self._stream, None
            self.state = "closed"
        shut = None
        if s is not None:          # abort + close off this thread, waited for in the budget
            shut = threading.Thread(target=_shut, args=(s,), name="media-mixer-shut",
                                    daemon=True)
            shut.start()
            shut.join(max(end - time.monotonic(), 0.0))
        return ((t is None or not t.is_alive())
                and (shut is None or not shut.is_alive()))

    def listen(self, ring) -> None:
        """The analyzer's input ring (anything with `push(mono)`), or None
        to stop. From the frame thread; the callback reads it once a block.
        Opens nothing: the stream still opens when a channel first asks."""
        self.tap = ring

    def _push(self, mix, frames: int) -> None:
        """The block just written, as mono (the mean over its channels: L
        and R), into the analyzer's ring. Called from the callback only; a
        failure here costs the analyzer one block, never the sound already
        written. `_mono` is (re)made here, the one place: another block
        size, or a Mixer from before V3 that has none."""
        ring = getattr(self, "tap", None)
        if ring is None:
            return
        try:
            mono = getattr(self, "_mono", None)
            if mono is None or len(mono) != frames:      # another size: once
                mono = self._mono = np.zeros(frames, np.float32)
            if mix is None:
                mono.fill(0.0)
            else:
                np.mean(mix, axis=1, out=mono)
            ring.push(mono)
        except Exception:  # noqa: BLE001 — the analyzer's loss, not the room's
            self.tap_errors = getattr(self, "tap_errors", 0) + 1

    def line(self) -> str:
        """SYSTEM's one line: '' until a channel has asked for the stream
        (`failed` says whether to warn)."""
        if self.state == "off":
            return ""
        return (f"media sound: {self.state} · {self.playing} playing"
                f" · {self.underruns} underruns"
                + (f" · {self.errors} read errors" if self.errors else "")
                + (f" · {tap} analyzer push errors"
                   if (tap := getattr(self, "tap_errors", 0)) else ""))

    # -- the stream's thread ------------------------------------------------

    def _warm(self, frames: int) -> None:
        """Every buffer the callback uses, for a block of `frames`: at the
        start and when PortAudio asks for another size, never otherwise."""
        i = np.arange(frames, dtype=np.float64)
        self._mix = np.zeros((frames, AUDIO_CHANNELS), np.float32)
        self._one = np.zeros((frames, AUDIO_CHANNELS), np.float32)
        self._two = np.zeros((frames, AUDIO_CHANNELS), np.float32)
        self._src = np.zeros((int(MAX_SPEED * frames) + 4, AUDIO_CHANNELS), np.float32)
        self._i = i                                 # the speed's share of a sample's place
        self._ease = i * i / (2.0 * frames)         # its glide's share
        self._pos = np.zeros(frames, np.float64)
        self._pos1 = self._pos.reshape(-1, 1)       # the same memory, by the channels
        self._tmp = np.zeros(frames, np.float64)
        self._idx = np.zeros(frames, np.intp)
        # (frames, channels), not broadcast from (frames, 1): a broadcasting ufunc
        # with `out=` makes an iterator on the heap every call
        self._frac = np.zeros((frames, AUDIO_CHANNELS), np.float32)
        self._ramp = np.repeat(((i + 1.0) / frames).astype(np.float32).reshape(-1, 1),
                               AUDIO_CHANNELS, axis=1)
        self._env = np.zeros((frames, AUDIO_CHANNELS), np.float32)
        self._edge = np.zeros((2, AUDIO_CHANNELS), np.float32)      # a bridged seam's two sides
        self._count = np.arange(SEAM_SLACK + 2, dtype=np.float32)
        self._line = np.zeros(SEAM_SLACK + 2, np.float32)
        self._line2 = np.zeros(SEAM_SLACK + 2, np.float32)

    def _fetch(self, st, at: int, n: int, wrap: int, end: int) -> None:
        """`n` source samples from `at` into `_src`, round the loop when it
        wraps (each piece one `read`), a track's gap before the seam bridged."""
        src, k = self._src, 0
        at = at % wrap if wrap else at
        while k < n:
            c = min(n - k, wrap - at) if wrap else n
            view = src[k:k + c]
            block = st.read(at, c, out=view)
            if block.shape != view.shape:
                raise ValueError(f"read gave {block.shape}")
            if wrap and at + c > end:
                self._bridge(st, view, at, c, end, wrap)
            k += c
            at = 0

    def _bridge(self, st, view, at: int, c: int, end: int, wrap: int) -> None:
        """Places `end`..`wrap` of the piece in `view`: a line from the track's
        last sample to its first, so a few ms short of the loop is no click."""
        edge = self._edge
        st.read(end - 1, 1, out=edge[:1])
        st.read(0, 1, out=edge[1:])
        lo = max(at, end)
        m, x = at + c - lo, lo - end + 1
        line, line2 = self._line[:m], self._line2[:m]
        np.multiply(self._count[x:x + m], 1.0 / (wrap - end + 1), out=line)
        for ch in range(AUDIO_CHANNELS):
            a = float(edge[0, ch])
            np.multiply(line, float(edge[1, ch]) - a, out=line2)
            np.add(line2, a, out=view[lo - at:, ch])

    @staticmethod
    def _held(st, lo: int, n: int, wrap: int, end: int) -> bool:
        """Whether the `n` source samples from `lo` are in memory, round the
        loop when it wraps; a bridged gap counts as held."""
        if not wrap:
            return st.holds(lo, n)
        at = lo % wrap
        while n > 0:
            c = min(n, wrap - at)
            if at < end and not st.holds(at, min(c, end - at)):
                return False
            n -= c
            at = 0
        return True

    def _span_held(self, st, at: float, speed: float, frames: int, wrap: int, end: int) -> bool:
        """Whether a block from `at` at a steady `speed` would be wholly held."""
        last = at + speed * (frames - 1)
        lo = math.floor(min(at, last))
        return self._held(st, lo, math.ceil(max(at, last)) - lo + 1, wrap, end)

    def _tape(self, st, at: float, v0: float, v1: float, wrap: int, end: int) -> bool:
        """The block from head place `at`, the speed gliding v0 → v1, linearly
        resampled into `_one`; whether its source is all held."""
        pos, tmp, idx, one, two = self._pos, self._tmp, self._idx, self._one, self._two
        np.multiply(self._i, v0, out=pos)
        np.multiply(self._ease, v1 - v0, out=tmp)
        np.add(pos, tmp, out=pos)
        np.add(pos, at, out=pos)
        lo = math.floor(pos.min())
        n = math.ceil(pos.max()) - lo + 1
        self._fetch(st, lo, n, wrap, end)
        np.floor(pos, out=tmp)
        np.subtract(pos, tmp, out=pos)              # `pos` is now each sample's fraction
        np.copyto(self._frac, self._pos1, casting="unsafe")
        np.subtract(tmp, lo, out=tmp)
        np.copyto(idx, tmp, casting="unsafe")
        np.take(self._src, idx, axis=0, out=one, mode="clip")
        np.add(idx, 1, out=idx)
        np.minimum(idx, n - 1, out=idx)
        np.take(self._src, idx, axis=0, out=two, mode="clip")
        np.subtract(two, one, out=two)
        np.multiply(two, self._frac, out=two)
        np.add(one, two, out=one)
        return self._held(st, lo, n, wrap, end)

    def _lay(self, mix, l0: float, l1: float) -> None:
        """`_one` into the mix, its level gliding l0 → l1 across the block."""
        one = self._one
        if l0 == l1:
            np.multiply(one, l0, out=one, casting="unsafe")
        else:
            env = self._env
            np.multiply(self._ramp, l1 - l0, out=env, casting="unsafe")
            np.add(env, l0, out=env, casting="unsafe")
            np.multiply(one, env, out=one)
        np.add(mix, one, out=mix)

    def _voice(self, v: Voice, head: _Head, frames: int, mix) -> None:
        """One voice's block into the mix, and its head moved on (module
        docstring: the head against the transport)."""
        st = v.track
        if head.seen is not v:
            head.seen, head.since = v, 0
        speed = max(-MAX_SPEED, min(v.speed, MAX_SPEED))
        wrap = round(v.wrap * AUDIO_RATE)
        if wrap < MIN_WRAP:
            wrap = 0
        end = st.ends_at if wrap else 0
        if not 0 < wrap - end <= SEAM_SLACK:
            end = wrap                                    # no gap to bridge
        target = round(v.at * AUDIO_RATE) + speed * head.since
        if wrap:
            target %= wrap
        was = head.level
        silent = was == 0.0 or head.at is None    # it sits on the transport, at speed at once
        at, was_speed = (target, speed) if silent else (head.at, head.speed)
        err = target - at
        if wrap:
            err = (err + wrap / 2) % wrap - wrap / 2      # the short way round the loop
        scale = max(1.0, abs(speed))                      # the clocks' jitter, in source samples
        if head.since >= STALE_S * AUDIO_RATE or abs(speed) < HOLD_SPEED:
            speed = 0.0     # the master has stopped saying, or stopped: no creeping to it
        elif abs(err) > CUT * scale:
            if was > 0.0:                                 # the crossfade's way out
                self._tape(st, at, was_speed, was_speed, wrap, end)
                self._lay(mix, was, 0.0)
            at, was, was_speed = target, 0.0, speed
        elif abs(err) > DEAD * scale + 1.0:       # (+ 1: a slew's tail ends, it is not forever)
            trim = min((abs(err) - DEAD * scale) / (TAU_S * AUDIO_RATE), TRIM_MAX * abs(speed))
            speed = max(-MAX_SPEED, min(speed + math.copysign(trim, err), MAX_SPEED))
        elif abs(speed) == 1.0 and was_speed == speed:
            at = round(at)                                # the track's own samples again
        amount = abs(speed)
        want = (v.gain * min(amount / FADE_SPEED, 1.0)) if amount >= HOLD_SPEED else 0.0
        level = 0.0
        audible = want > 0.0 and self._span_held(st, at, speed, frames, wrap, end)
        if audible or not silent:                         # (silent with nothing to hear: no read)
            held = self._tape(st, at, was_speed, speed, wrap, end)
            at += (was_speed + speed) / 2.0 * frames
            if want > 0.0 and held and self._span_held(st, at, speed, frames, wrap, end):
                level = want                              # (the next block is there too)
            if level > 0.0 or was > 0.0:
                self._lay(mix, was, level)
        if wrap:
            at %= wrap
        head.at, head.speed, head.level = at, speed, level
        head.since += frames

    def _callback(self, outdata, frames, _time, status) -> None:
        """Sum each voice's block from its read head × its level. Never
        blocks, never raises, never moves the transport."""
        try:
            if status is not None and getattr(status, "output_underflow", False):
                self.underruns += 1
            live = self._live             # one read: this frame's or the last
            if not live:
                outdata.fill(0.0)
                self._push(None, frames)        # silence: the bands decay
                return
            if len(self._mix) != frames:    # PortAudio asked for another size: once
                self._warm(frames)
            mix = self._mix
            mix.fill(0.0)
            for v, head in live:
                try:
                    self._voice(v, head, frames, mix)
                except Exception:  # noqa: BLE001 — one bad voice is silence, not a dead stream
                    self.errors += 1
                    head.level = 0.0            # not sounding: `_bind` may let it go
            np.clip(mix, -CEILING, CEILING, out=mix)
            outdata[:] = mix
            self._push(mix, frames)           # V3: what is heard, to the analyzer
        except Exception:  # noqa: BLE001 — PortAudio must never see a raise
            try:
                outdata.fill(0.0)
            except Exception:  # noqa: BLE001, S110
                pass


def _shut(s) -> None:
    for name in ("abort", "close"):
        try:
            getattr(s, name)()
        except Exception:  # noqa: BLE001, S110 — a stream that will not stop dies with the process
            pass
