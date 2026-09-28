"""Audio sources — live capture and file playback (plan 03 task 0).

Both feed the same Analyser+Analyzer pair (`chain` — the N-band analyzer,
plan 07), mirroring the reference's single attach() hub. Transport
semantics are the reference's (ENGINEERING.md, transport section):
position is ``_offset + _played``, where ``_played`` counts the frames
the output callback has handed PortAudio — not the frame loop's dt;
pause freezes position and keeps the same stream open, emitting silence
so the chain keeps stepping and the bands decay on their own time
constants; restart is return-to-zero
preserving transport state; playback loops.

Callback discipline (plan 04 note, honoured here): stream callbacks only
copy samples into a ring buffer. FFT + chain run on the frame loop.
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from .analysis import Analyser
from .analyzer import Analyzer

LOOPBACK_NAMES = ("blackhole", "loopback", "soundflower")


def is_loopback(name: str) -> bool:
    n = name.lower()
    return any(key in n for key in LOOPBACK_NAMES)


def input_devices() -> list[dict]:
    """Input-capable devices: [{index, name, loopback}], in device order."""
    out = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            out.append({"index": i, "name": d["name"], "loopback": is_loopback(d["name"])})
    return out


def preselect_device() -> int | None:
    """The reference's heuristic: a loopback device wins if present."""
    devs = input_devices()
    for d in devs:
        if d["loopback"]:
            return d["index"]
    return devs[0]["index"] if devs else None


class _Ring:
    """Single-producer single-consumer sample ring for callback → frame loop."""

    def __init__(self, capacity: int):
        self.buf = np.zeros(capacity)
        self.cap = capacity
        self.w = 0
        self.avail = 0
        self.lock = threading.Lock()

    def push(self, x: np.ndarray) -> None:
        n = len(x)
        with self.lock:
            i = self.w % self.cap
            first = min(n, self.cap - i)
            self.buf[i : i + first] = x[:first]
            if n > first:
                self.buf[: n - first] = x[first:]
            self.w += n
            self.avail = min(self.avail + n, self.cap)

    def drain(self) -> np.ndarray:
        with self.lock:
            n = self.avail
            self.avail = 0
            if n == 0:
                return np.empty(0)
            i = (self.w - n) % self.cap
            first = min(n, self.cap - i)
            out = np.concatenate([self.buf[i : i + first], self.buf[: n - first]])
        return out


class AudioEngine:
    """One live source at a time (mic or file), driving one Analyser+Analyzer."""

    def __init__(self, sample_rate: float = 48_000.0):
        self.sr = sample_rate
        self.analyser = Analyser(sample_rate)
        self.chain = Analyzer(self.analyser)
        self.on = False
        self.mode: str | None = None     # "mic" | "file"
        self.label = ""
        self.error = ""
        self._devices: list[dict] | None = None   # see `devices`
        self._device_sel: int | None = None
        self._ring = _Ring(int(sample_rate * 2))
        self._stream: sd.InputStream | sd.OutputStream | None = None
        # transport (file mode)
        self.track: np.ndarray | None = None   # mono, at the file's own rate (_track_sr)
        self._track_sr = sample_rate
        self.playing = False
        self._offset = 0            # frames into the track at last start
        self._played = 0            # frames emitted since last start (callback-owned)

    # ---- the input devices `audio.device` chooses from ----

    @property
    def devices(self) -> list[dict]:
        """Read once, on first use (the panel's combo, a key row toggling the
        mic) — not at construction, so a headless engine never scans the
        hardware. A device plugged in later needs a restart (audit A3)."""
        if self._devices is None:
            try:
                self._devices = input_devices()
            except Exception as e:  # noqa: BLE001 — a failed scan is not fatal
                self._devices, self.error = [], f"audio devices: {e}"
        return self._devices

    @property
    def device_sel(self) -> int:
        """Index into `devices`; a loopback driver is pre-selected."""
        if self._device_sel is None:
            self._device_sel = next((k for k, d in enumerate(self.devices) if d["loopback"]), 0)
        return self._device_sel

    @device_sel.setter
    def device_sel(self, k: int) -> None:
        self._device_sel = int(k)

    # ---- shared teardown ----

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        self.on = False
        self.mode = None
        self.playing = False
        self.track = None
        self._offset = 0
        self._played = 0

    def _fresh_chain(self) -> Analyzer:
        """New trackers on the current analyser; the user's bands and tuning
        (layout, per-band params, master faders) carry across sources."""
        old = self.chain
        new = Analyzer(self.analyser, old.params, layout=old.layout())
        new.gain, new.dyn, new.trim = old.gain, old.dyn, old.trim
        return new

    def _attach(self, mode: str, label: str) -> None:
        # fresh trackers per source, like the reference's attach()
        self.analyser = Analyser(self.sr)
        self.chain = self._fresh_chain()
        self._ring = _Ring(int(self.sr * 2))
        self.mode = mode
        self.label = label
        self.error = ""
        self.on = True

    # ---- mic / loopback ----

    def start_mic(self, device: int | None = None) -> bool:
        self.stop()
        try:
            name = sd.query_devices(device)["name"] if device is not None else "default input"
            stream = sd.InputStream(
                device=device, channels=1, samplerate=self.sr,
                callback=self._on_input,
            )
            stream.start()
        except Exception as e:  # noqa: BLE001 — surface any device failure in the UI
            self.error = f"could not open input: {e}"
            return False
        self._stream = stream
        self._attach("mic", ("System · " if is_loopback(name) else "") + name)
        return True

    def _on_input(self, indata, _frames, _t, _status) -> None:
        self._ring.push(indata[:, 0].copy())

    # ---- file transport ----

    def start_file(self, path: str | Path) -> bool:
        self.stop()
        try:
            data, sr = sf.read(str(path), dtype="float64", always_2d=True)
        except Exception as e:  # noqa: BLE001 — any decode failure reads the same way
            self.error = f"could not decode {Path(path).name}: {e}"
            return False
        self.track = data.mean(axis=1)
        self._track_sr = float(sr)
        try:
            stream = sd.OutputStream(
                channels=1, samplerate=self._track_sr, callback=self._on_output
            )
            stream.start()
        except Exception as e:  # noqa: BLE001
            self.error = f"could not open output: {e}"
            self.track = None
            return False
        self._stream = stream
        self.analyser = None  # rebuilt at track rate below
        self._attach("file", Path(path).name[:20])
        self.analyser = Analyser(self._track_sr)
        self.chain = self._fresh_chain()
        self._offset = 0
        self._played = 0
        self.playing = True
        return True

    def _on_output(self, outdata, frames, _t, _status) -> None:
        if self.track is None or not self.playing:
            outdata.fill(0.0)
            # feed the analyser silence so envelopes decay (coast-to-rest)
            self._ring.push(np.zeros(frames))
            return
        n = len(self.track)
        idx = (self._offset + self._played + np.arange(frames)) % n  # loop fold
        chunk = self.track[idx]
        outdata[:, 0] = chunk
        self._ring.push(chunk)
        self._played += frames

    # position measured against frames the stream actually played
    def position(self) -> float:
        if self.track is None:
            return 0.0
        n = len(self.track)
        return ((self._offset + (self._played if self.playing else 0)) % n) / self._track_sr

    def duration(self) -> float:
        return 0.0 if self.track is None else len(self.track) / self._track_sr

    def toggle_play(self) -> None:
        if self.track is None:
            return
        if self.playing:
            self._offset = int((self._offset + self._played) % len(self.track))
            self._played = 0
            self.playing = False
        else:
            self.playing = True

    def restart(self) -> None:
        """Return to zero, preserving transport state."""
        if self.track is None:
            return
        self._offset = 0
        self._played = 0

    # ---- per-frame ----

    def step(self, dt: float) -> None:
        """Called once per render frame: drain captured samples, run the chain."""
        if not self.on:
            return
        pending = self._ring.drain()
        if len(pending):
            self.analyser.feed(pending)
        self.chain.step(dt)
