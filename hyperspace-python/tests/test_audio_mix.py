"""Plan 45 V3 — the analyzer listens to the mix: the media mixer's summed
block, pushed by its callback into the analyzer's ring as mono at 48 kHz
(`Mixer.listen`, `AudioEngine.start_mix`, the ``audio.mix`` toggle).

No audio device: the mixer gets test_media_mixer's fake stream factory
(the test pulls blocks through the callback) and the engine's
`sounddevice` is test_audio's fake, so a test can prove no input stream
is opened for ``mix``. The soundtrack is synthetic: a sine read at the
sample the transport says."""

import numpy as np
import pytest
from test_audio import FakeStream, fake_sd  # noqa: F401 — the fixture
from test_media_mixer import DT, opened, rig

from hyperspace.analysis import FFT_SIZE
from hyperspace.audio import MIX_IDLE_FRAMES, AudioEngine
from hyperspace.control import Control
from hyperspace.media import mixer as M
from hyperspace.media.video import AUDIO_RATE
from hyperspace.params import build_registry
from hyperspace.view import ViewState

HZ = 1500.0

pytestmark = pytest.mark.usefixtures("fake_sd")    # no PortAudio: test_audio's fake


class Sine:
    """A soundtrack: `amp`·sin(2π·HZ·t) on the left, `amp_r`· the same on
    the right, t counted from the sample asked for (the transport's)."""

    def __init__(self, amp=0.5, amp_r=None):
        self.amp, self.amp_r = amp, amp if amp_r is None else amp_r
        self.reads: list[tuple[int, int]] = []

    def enable(self):
        pass

    def disable(self):
        pass

    def read(self, at, n, out=None):
        self.reads.append((at, n))
        s = np.sin(2 * np.pi * HZ * (at + np.arange(n)) / AUDIO_RATE)
        block = np.stack([s * self.amp, s * self.amp_r], axis=1).astype(np.float32)
        if out is None:
            return block
        out = out[:n]
        out[:] = block
        return out


def heard(n=1, amp=0.5, amp_r=None):
    """`n` channels heard, each a `Sine`."""
    m, _, f = rig(*(f"shared:{c}.mp4" for c in "ab"[:n]))
    m.poll(DT, -DT)                           # the sources open (nothing heard yet)
    for c in "ab"[:n]:
        m.channels[c].source.audio = Sine(amp, amp_r)
        m.channels[c].play_audio = True
    return m, f


def test_the_engines_mix_rate_is_the_mixers():
    assert AudioEngine.MIX_RATE == AUDIO_RATE


def test_the_mix_lands_in_the_analyzers_ring_as_mono_with_the_gains_applied():
    m, f = heard(1, amp=0.4, amp_r=0.2)
    m.channels["a"].gain = 0.5
    a = AudioEngine()
    assert a.start_mix(m.mixer)
    assert a.on and a.mode == "mix" and a.rate == AUDIO_RATE
    assert FakeStream.opened == [], "no input device is grabbed for the mix"
    m.poll(DT, 0.0)
    s = opened(m, f)
    out = s.pull()
    got = a._ring.drain()
    assert len(got) == M.BLOCK
    np.testing.assert_allclose(got, out.mean(axis=1), atol=1e-6)    # what is heard, mono
    at = round(m.channels["a"].transport.playhead * AUDIO_RATE)
    want = 0.5 * (0.4 + 0.2) / 2 * np.sin(2 * np.pi * HZ * (at + np.arange(M.BLOCK)) / AUDIO_RATE)
    np.testing.assert_allclose(got, want, atol=1e-5)


def test_the_bands_see_the_videos_tone_as_they_would_the_mics():
    m, f = heard(1, amp=0.5)
    a = AudioEngine()
    a.start_mix(m.mixer)
    m.poll(DT, 0.0)
    s = opened(m, f)
    for _ in range(FFT_SIZE // M.BLOCK + 2):
        s.pull()
    a.step(DT)
    spec = a.analyser.float_frequency_data()
    want = round(HZ / (AUDIO_RATE / 2) * a.analyser.bins)
    assert abs(int(np.argmax(spec)) - want) <= 1


def test_the_mix_is_taken_after_the_clip():
    m, f = heard(2, amp=0.9)                  # two channels at 0.9: the peaks clip at 1
    a = AudioEngine()
    a.start_mix(m.mixer)
    m.poll(DT, 0.0)
    out = opened(m, f).pull()
    got = a._ring.drain()
    assert np.abs(got).max() <= M.CEILING + 1e-6
    np.testing.assert_allclose(got, out.mean(axis=1), atol=1e-6)


def test_mix_with_nothing_heard_is_silence_not_an_error():
    m, _, f = rig("shared:a.mp4")
    a = AudioEngine()
    assert a.start_mix(m.mixer) and a.error == ""
    m.poll(DT, 0.0)                           # no channel asks: no stream at all
    assert f.made == [] and m.mixer.state == "off"
    a.step(DT)
    assert not np.any(a.analyser._buf)
    m.channels["a"].play_audio = True         # a channel asks, then stops
    m.poll(DT, 0.1)
    s = opened(m, f)
    m.channels["a"].play_audio = False
    m.poll(DT, 0.2)
    s.pull()
    got = a._ring.drain()
    assert len(got) == M.BLOCK and not got.any(), "no voice pushes zeros: the bands decay"


def test_a_stream_that_stops_or_stalls_is_silence_not_the_last_block_held():
    m, f = heard(1, amp=0.5)
    a = AudioEngine()
    a.start_mix(m.mixer)
    m.poll(DT, 0.0)
    s = opened(m, f)
    for _ in range(6):
        s.pull()
    a.step(DT)
    assert a.analyser._buf.any()
    assert m.mixer.state == "open"           # still "open": PortAudio stalled, no callback
    for _ in range(MIX_IDLE_FRAMES - 1):
        a.step(DT)
    assert a.analyser._buf.any(), "a frame or two with no block is jitter, not silence"
    a.step(DT)
    assert not a.analyser._buf.any()
    s.pull()                                 # the callback comes back: the sound does too
    a.step(DT)
    assert a.analyser._buf.any() and a._mix_idle == 0


def test_switching_sources_mid_run_detaches_the_mix_and_keeps_the_bands():
    m, f = heard(1)
    a = AudioEngine()
    a.chain.gain = 1.6
    a.start_mix(m.mixer)
    assert m.mixer.tap is a._ring
    a.start_mic(0)                            # mix → mic
    assert m.mixer.tap is None and a.mode == "mic" and a.chain.gain == 1.6
    m.poll(DT, 0.0)
    opened(m, f).pull()
    assert a._ring.avail == 0, "the mix no longer reaches the analyzer"
    mic = FakeStream.opened[-1]
    a.start_mix(m.mixer)                      # mic → mix: the mic's stream closes
    assert mic.closed and m.mixer.tap is a._ring and a.chain.gain == 1.6
    a.stop()
    assert m.mixer.tap is None and not a.on


def test_the_mixer_without_a_listener_is_v2_unchanged():
    m, f = heard(1, amp=0.4)
    m.poll(DT, 0.0)
    s = opened(m, f)
    assert m.mixer.tap is None
    out = s.pull()
    assert out.shape == (M.BLOCK, 2) and out.any() and m.mixer.errors == 0


def test_a_ring_that_raises_costs_the_analyzer_not_the_sound():
    class Bad:
        def push(self, x):
            raise RuntimeError("full")

    m, f = heard(1, amp=0.4)
    m.mixer.listen(Bad())
    m.poll(DT, 0.0)
    out = opened(m, f).pull()
    assert out.any() and m.mixer.tap_errors == 1 and m.mixer.errors == 0
    assert "1 analyzer push errors" in m.mixer.line() and "read errors" not in m.mixer.line()


def test_the_mono_is_the_mean_over_however_many_channels():
    mx = M.Mixer(make=lambda **kw: None)
    a = AudioEngine()
    a.start_mix(mx)
    mx._push(np.array([[0.3, 0.6, 0.9]] * 4, np.float32), 4)
    np.testing.assert_allclose(a._ring.drain(), 0.6, atol=1e-6)
    assert mx.tap_errors == 0


def test_a_mixer_from_before_v3_learns_to_listen_after_a_hot_reload():
    mx = M.Mixer(make=lambda **kw: None)
    del mx.__dict__["tap"], mx.__dict__["_mono"]
    out = np.ones((M.BLOCK, 2), np.float32)
    mx._callback(out, M.BLOCK, None, None)     # no tap: V2's callback, untouched
    assert not out.any()
    a = AudioEngine()
    assert a.start_mix(mx) and mx.tap is a._ring
    mx._callback(out, M.BLOCK, None, None)
    assert a._ring.avail == M.BLOCK


def test_the_audio_mix_toggle_picks_the_source_and_lets_it_go():
    m, _, _ = rig("shared:a.mp4")
    a = AudioEngine()
    reg = build_registry(ViewState(), Control(a.chain), a, media=m)
    mix, mic = reg["audio.mix"], reg["audio.mic"]
    assert mix.value is False and not mix.persist
    mix.set(True)
    assert a.mode == "mix" and m.mixer.tap is a._ring and FakeStream.opened == []
    assert mix.value is True and mic.value is False
    mic.set(True)
    assert a.mode == "mic" and m.mixer.tap is None and mix.value is False
    mix.set(True)
    mix.set(False)
    assert not a.on and m.mixer.tap is None


def test_the_toggle_is_declared_only_with_the_hosts_media():
    a = AudioEngine()
    reg = build_registry(ViewState(), Control(a.chain), a)    # no media: no fed mixer
    assert "audio.mix" not in reg and "audio.mic" in reg
