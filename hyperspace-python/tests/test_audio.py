"""audio.py's streams and analysis.py's FFT, headless (audit A9).

`sounddevice` is replaced by a fake whose streams hand their callback to
the test, so a capture and a file can be driven sample by sample without
hardware; the transport semantics are ENGINEERING §4b's.
"""

from types import SimpleNamespace
from typing import ClassVar

import numpy as np
import pytest
import soundfile as sf

from hyperspace import audio as A
from hyperspace.analysis import FFT_SIZE, SMOOTHING, Analyser
from hyperspace.audio import AudioEngine, preselect

DEVICES = [
    {"name": "MacBook Pro Microphone", "max_input_channels": 1},
    {"name": "Speakers", "max_input_channels": 0},
    {"name": "BlackHole 2ch", "max_input_channels": 2},
]


class FakeStream:
    """One PortAudio stream: remembers its arguments, exposes its callback."""

    opened: ClassVar[list["FakeStream"]] = []

    def __init__(self, *, callback, samplerate, channels, device=None, fail=False):
        if fail:
            raise RuntimeError("no such device")
        self.callback, self.samplerate, self.channels, self.device = callback, samplerate, channels, device
        self.running = False
        self.closed = False
        FakeStream.opened.append(self)

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def close(self):
        self.closed = True

    # ---- the test drives the callback ----

    def push(self, samples):
        """Capture: hand `samples` in as if PortAudio had recorded them."""
        block = np.asarray(samples, dtype=np.float64).reshape(-1, 1)
        self.callback(block, len(block), None, None)

    def pull(self, frames):
        """Playback: ask for `frames`; return what the engine wrote."""
        out = np.zeros((frames, 1))
        self.callback(out, frames, None, None)
        return out[:, 0]


@pytest.fixture
def fake_sd(monkeypatch):
    FakeStream.opened = []
    devices = [dict(d) for d in DEVICES]

    def query_devices(device=None):
        return devices if device is None else devices[device]

    sd = SimpleNamespace(
        query_devices=query_devices,
        InputStream=FakeStream,
        OutputStream=lambda **kw: FakeStream(**kw),
        devices=devices,
    )
    monkeypatch.setattr(A, "sd", sd)
    return sd


# ------------------------------------------------------------ devices (A3)

def test_preselect_picks_the_first_loopback_else_the_first_device():
    assert preselect([{"loopback": False}, {"loopback": True}, {"loopback": True}]) == 1
    assert preselect([{"loopback": False}, {"loopback": False}]) == 0
    assert preselect([]) == 0


def test_the_engine_lists_input_capable_devices_once_and_preselects_the_loopback(fake_sd):
    a = AudioEngine()
    assert a._devices is None                 # nothing scanned at construction
    assert [d["name"] for d in a.devices] == ["MacBook Pro Microphone", "BlackHole 2ch"]
    assert a.devices[1]["loopback"] and a.devices[1]["index"] == 2
    assert a.device_sel == 1                  # the loopback, by position in `devices`
    fake_sd.devices.append({"name": "USB Interface", "max_input_channels": 2})
    assert len(a.devices) == 2, "the list is read once"


def test_rescan_reads_the_list_again_and_keeps_the_selection_by_name(fake_sd):
    a = AudioEngine()
    assert a.devices
    a.device_sel = 0                          # the built-in mic
    fake_sd.devices.insert(0, {"name": "USB Interface", "max_input_channels": 2})
    new = a.rescan()
    assert [d["name"] for d in new] == ["USB Interface", "MacBook Pro Microphone", "BlackHole 2ch"]
    assert new[a.device_sel]["name"] == "MacBook Pro Microphone"
    fake_sd.devices[:] = [{"name": "Something else", "max_input_channels": 1}]
    a.rescan()
    assert a.device_sel == 0, "a vanished device falls back to the heuristic"


def test_a_failed_scan_is_an_error_not_a_crash_and_a_rescan_clears_it(monkeypatch):
    def boom():
        raise OSError("PortAudio not initialised")

    monkeypatch.setattr(A, "input_devices", boom)
    a = AudioEngine()
    assert a.devices == [] and "PortAudio" in a.error and a.device_sel == 0
    monkeypatch.setattr(A, "input_devices", lambda: [{"index": 3, "name": "USB", "loopback": False}])
    assert [d["name"] for d in a.rescan()] == ["USB"] and a.error == ""


def test_rescan_on_a_never_read_list_scans_once(monkeypatch):
    scans = []
    monkeypatch.setattr(A, "input_devices", lambda: scans.append(1) or [])
    a = AudioEngine()
    a.rescan()                                # app.main's startup call
    assert scans == [1]


# ------------------------------------------------------------- capture (A9)

def test_start_mic_opens_the_device_and_samples_reach_the_chain_on_step(fake_sd):
    a = AudioEngine(48_000.0)
    assert a.start_mic(2)
    stream = FakeStream.opened[-1]
    assert stream.running and stream.device == 2 and stream.samplerate == 48_000.0 and stream.channels == 1
    assert a.on and a.mode == "mic" and a.label == "System · BlackHole 2ch" and a.rate == 48_000.0
    n = 4800
    tone = np.sin(2 * np.pi * 1000 * np.arange(n) / 48_000.0)
    stream.push(tone)                         # the callback only copies into the ring
    assert a._ring.avail == n
    fed = []
    a.analyser.feed = lambda x: fed.append(x)   # the frame loop drains the ring…
    stepped = []
    a.chain.step = lambda dt: stepped.append(dt)
    a.step(1 / 60)
    assert len(fed) == 1 and len(fed[0]) == n and a._ring.avail == 0
    assert stepped == [1 / 60]                # …and runs the chain, once per frame
    a.step(1 / 60)
    assert len(fed) == 1 and stepped == [1 / 60] * 2, "an empty ring still steps the chain"


def test_start_mic_failure_is_reported_and_leaves_the_engine_off(fake_sd):
    a = AudioEngine()
    fake_sd.InputStream = lambda **kw: FakeStream(fail=True, **kw)
    assert not a.start_mic(0)
    assert "could not open input" in a.error and not a.on and a._stream is None


def test_stop_closes_the_stream_and_the_chain_freezes(fake_sd):
    a = AudioEngine()
    a.start_mic(0)
    stream = FakeStream.opened[-1]
    a.stop()
    assert stream.closed and not stream.running and not a.on and a.mode is None
    stepped = []
    a.chain.step = lambda dt: stepped.append(dt)
    a.step(1 / 60)
    assert stepped == [], "off: nothing steps, every lane row lets go (ENGINEERING §4b)"


def test_a_source_switch_keeps_the_bands_and_the_faders(fake_sd):
    a = AudioEngine()
    a.chain.gain, a.chain.dyn, a.chain.trim = 1.7, 0.4, -6.0
    a.chain.params[2].atk = 0.111
    a.start_mic(0)
    assert (a.chain.gain, a.chain.dyn, a.chain.trim) == (1.7, 0.4, -6.0)
    assert a.chain.params[2].atk == 0.111 and a.chain.warm == 0


# ---------------------------------------------------- file transport (A6, A9)

@pytest.fixture
def track(tmp_path):
    sr = 44_100
    t = np.arange(sr * 2) / sr                # two seconds
    data = np.stack([np.sin(2 * np.pi * 220 * t), np.sin(2 * np.pi * 220 * t)], axis=1) * 0.5
    path = tmp_path / "tone.wav"
    sf.write(path, data, sr)
    return path, sr


def test_start_file_attaches_once_at_the_tracks_rate(fake_sd, track, monkeypatch):
    path, sr = track
    a = AudioEngine(48_000.0)                # its own idle analyser, at the capture rate
    built = []
    real = A.Analyser
    monkeypatch.setattr(A, "Analyser", lambda rate: built.append(rate) or real(rate))
    assert a.start_file(path)
    assert built == [float(sr)], "one analyser, at the track's rate — not one at 48 kHz first"
    assert a.rate == sr and a.sr == 48_000.0 and a.analyser.sample_rate == sr
    assert a.chain.an is a.analyser
    stream = FakeStream.opened[-1]
    assert stream.samplerate == sr and stream.running
    assert a.on and a.mode == "file" and a.playing and a.label == "tone.wav"
    assert a.duration() == pytest.approx(2.0)


def test_playback_callback_feeds_the_ring_and_position_counts_played_frames(fake_sd, track):
    path, sr = track
    a = AudioEngine()
    a.start_file(path)
    stream = FakeStream.opened[-1]
    out = stream.pull(4410)
    assert np.allclose(out, a.track[:4410]) and a._ring.avail == 4410
    assert a.position() == pytest.approx(0.1)
    stream.pull(sr * 2)                       # past the end: the loop folds
    assert a.position() == pytest.approx(0.1)
    assert a._ring.avail == a._ring.cap, "the ring holds its last two seconds"


def test_pause_emits_silence_keeps_the_ring_filling_and_freezes_position(fake_sd, track):
    path, _ = track
    a = AudioEngine()
    a.start_file(path)
    stream = FakeStream.opened[-1]
    stream.pull(4410)
    a.toggle_play()
    assert not a.playing and stream.running and not stream.closed, "pause tears nothing down"
    assert a.position() == pytest.approx(0.1)
    a._ring.drain()
    silence = stream.pull(1000)
    assert not silence.any() and a._ring.avail == 1000, "silence still reaches the chain — the bands decay"
    assert a.position() == pytest.approx(0.1)
    a.toggle_play()
    stream.pull(4410)
    assert a.position() == pytest.approx(0.2), "resumes where it paused"


def test_restart_returns_to_zero_and_keeps_the_transport_state(fake_sd, track):
    path, _ = track
    a = AudioEngine()
    a.start_file(path)
    stream = FakeStream.opened[-1]
    stream.pull(4410)
    a.restart()
    assert a.position() == 0.0 and a.playing
    a.toggle_play()
    stream.pull(4410)
    a.restart()
    assert a.position() == 0.0 and not a.playing


def test_a_bad_file_is_an_error_and_nothing_opens(fake_sd, tmp_path):
    bad = tmp_path / "notes.wav"
    bad.write_bytes(b"not audio")
    a = AudioEngine()
    assert not a.start_file(bad)
    assert "could not decode notes.wav" in a.error and not a.on and FakeStream.opened == []


def test_an_output_that_will_not_open_leaves_no_track(fake_sd, track):
    path, _ = track
    fake_sd.OutputStream = lambda **kw: FakeStream(fail=True, **kw)
    a = AudioEngine()
    assert not a.start_file(path)
    assert "could not open output" in a.error and a.track is None and not a.on


# ------------------------------------------------------------ analysis (A9)

def test_a_tone_peaks_in_its_bin_and_the_spectrum_is_smoothed_by_the_constant():
    an = Analyser(48_000.0)
    tone = np.sin(2 * np.pi * 1000 * np.arange(FFT_SIZE) / 48_000.0)
    an.feed(tone)
    first = an.float_frequency_data()
    assert first.shape == (FFT_SIZE // 2,)
    assert int(np.argmax(first)) == round(1000 * FFT_SIZE / 48_000)   # bin 85
    assert first[1000] < first.max() - 60, "a Blackman window: the far bins sit far below"
    second = an.float_frequency_data()
    # s1 = (1 − τ)·|X|, s2 = τ·s1 + (1 − τ)·|X| — the ratio is the smoothing constant's
    assert second.max() - first.max() == pytest.approx(20 * np.log10(1 + SMOOTHING), abs=1e-9)
    assert SMOOTHING == 0.15


def test_feed_keeps_the_most_recent_fft_size_samples():
    an = Analyser()
    an.feed(np.ones(100))
    assert an._buf[-100:].all() and not an._buf[:-100].any()
    an.feed(np.full(FFT_SIZE + 10, 2.0))
    assert an._buf.shape == (FFT_SIZE,) and (an._buf == 2.0).all()


def test_band_bins_round_like_the_reference():
    an = Analyser(48_000.0)                   # nyquist 24 kHz over 2048 bins: 11.72 Hz a bin
    assert an.band_bins(60, 160) == (5, 14)   # floor(5.12), ceil(13.65)
    assert an.band_bins(0, 5) == (1, 2)       # never bin 0, never fewer than two
    assert an.band_bins(20_000, 30_000) == (1706, 2047)
