"""The media mixer (plan 45 V2): the channels' video sound, summed into one
output stream, read at the transport's position.

**The transport is the one clock** (plan 45, "no second time base"). The
frame thread hands the mixer, once a frame (`MediaState.poll`, after the
transports are stepped), a tuple of *voices*: for each channel whose
play-audio toggle is on and whose source has a soundtrack, the
`Soundtrack`, the playhead in seconds the transport was just stepped to,
and the channel's gain. The stream's callback reads that tuple — one
reference, swapped whole, so the callback sees last frame's voices or
this frame's, never a mix — and for each voice asks
`read(round(playhead × AUDIO_RATE), frames)`, multiplies by the gain and
sums into one float32 stereo block, clipped at ±1. **The callback
integrates nothing**: no sample counter, no stream time, no position of
its own (`audio.py`'s `_played` is the model it must not copy). The
glitch that buys is structural, not a matter of rate: the audio clock and
the display clock are never locked, so even at rate 1 a callback now and
then lands twice between two steps (a block repeated) or a step passes
with no callback (a block skipped) — an occasional click, expected until
V4 reads sequentially and slews toward the transport. The block is one
60 Hz frame long (`BLOCK`), so at the rig's frame rate a callback and a
step roughly alternate; any rate ≠ 1 stutters or skips outright. A voice
not moving forward (`MediaState._voices`: a hold, a jog's coast dying
out, a `once` clip parked at its end, reverse, pingpong's way back) is
left out — silence, not one block buzzing; reverse is V4's.

The callback allocates nothing once warm: one mix buffer and one voice
buffer of the block's size are kept (`_mix`, `_one`, remade only if
PortAudio asks for another size), each voice is read into `_one` through
`Soundtrack.read(..., out=)` and scaled and summed in place.

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

import threading
import time
from collections.abc import Callable

import numpy as np

from . import pool
from .video import AUDIO_CHANNELS, AUDIO_RATE

BLOCK = AUDIO_RATE // 60      # 800 samples: one 60 Hz frame a callback
RETRY_S = 5.0                 # a failed open is tried again this long after, while asked
CLOSE_BUDGET_S = 0.5          # how long `close` waits for an open still under way
CEILING = 1.0                 # the sum is clipped here: gain is the performer's to set

Voice = tuple   # (soundtrack, playhead seconds, gain)


def _default_stream(**kw):
    import sounddevice as sd
    return sd.OutputStream(**kw)


class Mixer:
    """One output stream for every channel's video sound (module docstring).

    The frame thread calls `feed(voices, asked)` once a frame and `close` at
    exit; the stream's thread calls `_callback`. `state` is "off" (never
    asked), "opening", "open", "closed" or "error: …"; `playing` the voices
    in the last feed, `underruns` the callbacks PortAudio flagged as an
    output underflow, `errors` the voice reads that raised."""

    def __init__(self, make: Callable | None = None):
        self._make = make if make is not None else _default_stream
        self._lock = threading.Lock()
        self._stream = None
        self._opener: threading.Thread | None = None
        self._failed_at = -1e9
        self._closed = False
        self.voices: tuple[Voice, ...] = ()
        self.state = "off"
        self.underruns = 0
        self.errors = 0
        self._mix = np.zeros((BLOCK, AUDIO_CHANNELS), np.float32)   # the callback's own
        self._one = np.zeros((BLOCK, AUDIO_CHANNELS), np.float32)
        self.tap = None       # plan 45 V3: the analyzer's ring, or None (`listen`)
        self.tap_errors = 0   # pushes into that ring that raised (not voice reads)
        self._mono = np.zeros(BLOCK, np.float32)

    # -- the frame thread ---------------------------------------------------

    @property
    def playing(self) -> int:
        return len(self.voices)

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
        self.voices = tuple(voices)
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

    def _callback(self, outdata, frames, _time, status) -> None:
        """Sum each voice's `read(round(playhead × rate), frames)` × gain.
        Never blocks, never raises, never moves a position."""
        try:
            if status is not None and getattr(status, "output_underflow", False):
                self.underruns += 1
            voices = self.voices          # one read: this frame's or the last
            if not voices:
                outdata.fill(0.0)
                self._push(None, frames)        # silence: the bands decay
                return
            mix, one = self._mix, self._one
            if len(mix) != frames:          # PortAudio asked for another size: once
                mix = self._mix = np.zeros((frames, AUDIO_CHANNELS), np.float32)
                one = self._one = np.zeros((frames, AUDIO_CHANNELS), np.float32)
            mix.fill(0.0)
            for st, at, gain in voices:
                try:
                    block = st.read(round(at * AUDIO_RATE), frames, out=one)
                    if block.shape != mix.shape:
                        raise ValueError(f"read gave {block.shape}")
                    np.multiply(block, gain, out=one, casting="unsafe")
                    np.add(mix, one, out=mix)
                except Exception:  # noqa: BLE001 — one bad voice is silence, not a dead stream
                    self.errors += 1
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
