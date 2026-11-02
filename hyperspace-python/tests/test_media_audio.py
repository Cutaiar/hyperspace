"""Plan 45 V1: a video's audio track decoded to memory, under the
transport's clock. The clips are synthesized here with PyAV (no committed
fixture): a known tone in each channel, so the decode is checked by the
frequency it recovers."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import av
import numpy as np
import pytest

from hyperspace.media import adapters, video
from hyperspace.media.source import FETCHING, READY

RATE = video.AUDIO_RATE


def _write_clip(path: Path, *, seconds=3.0, arate=44100, acodec="pcm_s16le",
                tones=(440.0, 880.0), tone_at=None, video_too=True):
    """A clip with `tones` (Hz, one per channel; one tone = mono) in its
    audio and, unless `video_too` is False, a grey ramp of video. With
    `tone_at` = (t_s, hz) every channel switches to `hz` from `t_s` on."""
    fmt = "fltp" if acodec == "aac" else "s16"
    n = int(seconds * arate)
    t = np.arange(n) / arate
    planes = []
    for hz in tones:
        f = np.full(n, hz)
        if tone_at is not None:
            f[t >= tone_at[0]] = tone_at[1]
        planes.append(0.5 * np.sin(2 * np.pi * np.cumsum(f) / arate))
    with av.open(str(path), "w") as out:
        a = out.add_stream(acodec, rate=arate)
        a.layout = "stereo" if len(tones) == 2 else "mono"
        a.format = fmt
        if video_too:          # every stream before the first mux
            v = out.add_stream("libx264", rate=30)
            v.width, v.height, v.pix_fmt = 64, 48, "yuv420p"
            v.options = {"crf": "30", "preset": "ultrafast"}
        chunk = a.codec_context.frame_size or 1024
        for i in range(0, n, chunk):
            part = [p[i:i + chunk] for p in planes]
            if fmt == "fltp":
                arr = np.stack(part).astype(np.float32)
            else:
                arr = (np.stack(part, 1).reshape(1, -1) * 32767).astype(np.int16)
            fr = av.AudioFrame.from_ndarray(arr, format=fmt, layout=a.layout.name)
            fr.sample_rate = arate
            fr.pts = i
            for p in a.encode(fr):
                out.mux(p)
        for p in a.encode():
            out.mux(p)
        if video_too:
            for i in range(int(seconds * 30)):
                vf = av.VideoFrame.from_ndarray(np.full((48, 64, 3), (i * 2) % 256, np.uint8),
                                                format="rgb24")
                for p in v.encode(vf):
                    out.mux(p)
            for p in v.encode():
                out.mux(p)
    return path


@pytest.fixture(scope="module")
def pcm_clip(tmp_path_factory):
    """3 s, 44.1 kHz PCM stereo in a .mov: 440 Hz left, 880 Hz right."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "tones.mov")


@pytest.fixture(scope="module")
def aac_clip(tmp_path_factory):
    """The same tones through AAC in an mp4: what a show video carries."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "tones.mp4", acodec="aac")


@pytest.fixture(scope="module")
def long_clip(tmp_path_factory):
    """30 s of 8 kHz mono PCM: 300 Hz for 15 s, then 600 Hz. Small enough to
    write in a blink; long enough for a (patched) window to move in."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "long.mov", seconds=30.0,
                       arate=8000, tones=(300.0,), tone_at=(15.0, 600.0), video_too=False)


@pytest.fixture
def opened():
    made = []

    def make(path, cache=None):
        s = video.VideoSource("file:" + str(path), path, cache=cache)
        made.append(s)
        s.open()
        return s

    yield make
    for s in made:
        s.close()


def _until(fn, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.01)
    return None


def _peak_hz(samples: np.ndarray) -> float:
    """The loudest frequency in one channel of samples at RATE."""
    spec = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return float(np.fft.rfftfreq(len(samples), 1.0 / RATE)[int(spec.argmax())])


def _audio_threads():
    return [t for t in threading.enumerate() if t.name.startswith("media-audio-")]


# -- the buffer ---------------------------------------------------------------

def test_the_track_is_decoded_whole_as_stereo_float32_at_48k(pcm_clip, opened):
    s = opened(pcm_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.rate == 48_000 and a.channels == 2
    assert a.duration == pytest.approx(3.0, abs=0.01)
    assert a.whole
    assert a.held == pytest.approx((0.0, 3.0), abs=0.002)
    assert abs(a.nbytes // 8 - 3 * RATE) <= 64        # 8 bytes a stereo sample
    out = a.read(0, 3 * RATE)
    assert out.dtype == np.float32 and out.shape == (3 * RATE, 2)
    assert out.flags.writeable


def test_a_sines_frequency_is_recovered_in_each_channel(pcm_clip, opened):
    s = opened(pcm_clip)
    assert _until(lambda: s.audio.status == READY)
    out = s.audio.read(RATE, RATE)          # the second second
    assert _peak_hz(out[:, 0]) == pytest.approx(440.0, abs=1.0)
    assert _peak_hz(out[:, 1]) == pytest.approx(880.0, abs=1.0)
    assert np.abs(out).max() == pytest.approx(0.5, abs=0.02)


def test_an_aac_track_in_an_mp4_decodes_the_same(aac_clip, opened):
    s = opened(aac_clip)
    assert _until(lambda: s.audio.status == READY)
    assert abs(s.audio.nbytes // 8 - 3 * RATE) <= 2048   # the codec's priming
    out = s.audio.read(RATE, RATE)
    assert _peak_hz(out[:, 0]) == pytest.approx(440.0, abs=2.0)
    assert _peak_hz(out[:, 1]) == pytest.approx(880.0, abs=2.0)


def test_read_is_zeros_outside_what_is_held_and_never_raises(pcm_clip, opened):
    s = opened(pcm_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert not a.read(-RATE, RATE).any()                 # before the start
    assert not a.read(10 * RATE, RATE).any()             # past the end
    tail = a.read(3 * RATE - 100, 200)                   # straddling the end
    assert tail.shape == (200, 2) and tail[:100].any() and not tail[100:].any()
    assert a.read(0, 0).shape == (0, 2)
    assert a.read(5, -3).shape == (0, 2)


def test_a_file_without_audio_is_silence_with_no_note(tmp_path, opened, capsys):
    p = tmp_path / "mute.mp4"
    with av.open(str(p), "w") as out:
        v = out.add_stream("libx264", rate=30)
        v.width, v.height, v.pix_fmt = 64, 48, "yuv420p"
        for i in range(30):
            for pk in v.encode(av.VideoFrame.from_ndarray(
                    np.full((48, 64, 3), i, np.uint8), format="rgb24")):
                out.mux(pk)
        for pk in v.encode():
            out.mux(pk)
    s = opened(p)
    assert _until(lambda: s.audio.status == video.NO_AUDIO)
    assert _until(lambda: s.status == READY)              # the picture is unaffected
    assert s.audio.held is None and s.audio.nbytes == 0
    assert not s.audio.read(0, 1024).any()
    assert _until(lambda: not _audio_threads())           # its thread is done
    assert capsys.readouterr() == ("", "")


def test_the_transport_is_the_one_clock(pcm_clip, opened):
    """`want` on the source is the position both threads follow: the
    soundtrack has no clock of its own."""
    s = opened(pcm_clip)
    s.want(1.25)
    assert s.audio._want == 1.25 and s._want == 1.25
    assert not any(n.startswith(("play", "clock")) for n in vars(s.audio))


# -- the memory policy ----------------------------------------------------------

def test_the_window_policy():
    w = video.AUDIO_WINDOW_S
    assert video.AUDIO_WINDOW_BYTES == int(w * RATE) * 2 * 4
    assert video.AUDIO_WINDOW_BYTES < 64 * 2**20                   # 46 MB a track
    assert video.audio_window(0.0, 30.0) == (0.0, 30.0)            # short: whole
    assert video.audio_window(29.0, w) == (0.0, w)                 # exactly the bound: whole
    assert video.audio_window(3600.0, 7200.0) == (3600.0 - w / 2, 3600.0 + w / 2)
    assert video.audio_window(0.0, 7200.0) == (0.0, w)             # pinned to the head
    assert video.audio_window(7200.0, 7200.0) == (7200.0 - w, 7200.0)   # and the tail
    assert video.audio_window(-5.0, 7200.0) == (0.0, w)
    assert video.audio_window(500.0, 0.0) == (500.0 - w / 2, 500.0 + w / 2)   # length unknown
    assert video.audio_window(0.0, 0.0) == (0.0, w)


def test_a_two_hour_file_holds_one_window_not_the_film(pcm_clip, opened, monkeypatch):
    """The probe is made to say two hours; what is held is the window."""
    monkeypatch.setattr(video, "_audio_duration", lambda c, st: 7200.0)
    s = opened(pcm_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.duration == 7200.0 and not a.whole
    assert a.nbytes <= video.AUDIO_WINDOW_BYTES
    assert a.held[0] == 0.0 and a.held[1] <= video.AUDIO_WINDOW_S


def test_the_window_follows_the_transport(long_clip, opened, monkeypatch):
    monkeypatch.setattr(video, "AUDIO_WINDOW_S", 4.0)
    monkeypatch.setattr(video, "AUDIO_RECENTRE_S", 1.0)
    s = opened(long_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.duration == pytest.approx(30.0, abs=0.01) and not a.whole
    assert a.held == pytest.approx((0.0, 4.0), abs=0.05)
    assert a.nbytes <= int(4.0 * RATE) * 8
    one = a.read(RATE, RATE)
    assert _peak_hz(one[:, 0]) == pytest.approx(300.0, abs=1.0)
    assert np.array_equal(one[:, 0], one[:, 1])              # mono, doubled
    s.want(20.0)                                             # a scrub far ahead
    assert _until(lambda: a.held is not None and a.held[0] > 17.0)
    assert a.held == pytest.approx((18.0, 22.0), abs=0.05)
    assert a.nbytes <= int(4.0 * RATE) * 8
    later = a.read(20 * RATE, RATE)
    assert _peak_hz(later[:, 0]) == pytest.approx(600.0, abs=1.0)
    assert not a.read(RATE, RATE).any()                      # the head is let go
    s.want(20.5)                                             # inside the window: no move
    time.sleep(0.15)
    assert a.held == pytest.approx((18.0, 22.0), abs=0.05)


# -- never on the frame thread ----------------------------------------------------

def test_opening_never_blocks_the_caller(pcm_clip, opened, monkeypatch):
    real = av.open
    gate = threading.Event()

    def slow(*a, **kw):
        gate.wait(2.0)
        return real(*a, **kw)

    monkeypatch.setattr(av, "open", slow)
    t0 = time.monotonic()
    s = opened(pcm_clip)
    s.want(1.0)
    out = s.audio.read(RATE, 512)
    assert time.monotonic() - t0 < 0.1
    assert s.audio.status == FETCHING and not out.any()
    gate.set()
    assert _until(lambda: s.audio.status == READY)


def test_close_joins_the_audio_thread_too(pcm_clip, opened):
    s = opened(pcm_clip)
    assert _until(lambda: s.audio.status == READY)
    assert _audio_threads()
    s.close()
    assert not _audio_threads()
    assert s.audio._thread is None
    s.close()                                                # twice is fine


def test_close_is_quick_mid_decode(long_clip, opened, monkeypatch):
    """A window decode checks the stop flag every frame."""
    monkeypatch.setattr(video, "AUDIO_WINDOW_S", 4.0)
    real = video.Soundtrack._decode

    def crawl(self, *a):
        time.sleep(0.02)
        return real(self, *a)

    monkeypatch.setattr(video.Soundtrack, "_decode", crawl)
    s = opened(long_clip)
    t0 = time.monotonic()
    s.close()
    assert time.monotonic() - t0 < 0.5
    assert not _audio_threads()


def test_the_adapter_hands_out_a_source_with_a_soundtrack(pcm_clip):
    class R:
        def path(self, sid):
            return pcm_clip

        def live(self, sid):
            return None

    s = adapters.open_source("file:" + str(pcm_clip), R())
    assert isinstance(s.audio, video.Soundtrack)
    assert s.audio.status == FETCHING and s.audio.read(0, 4).shape == (4, 2)
    assert not hasattr(adapters.MissingSource("file:/x"), "audio")


def test_the_soundtrack_reads_the_original_not_the_proxy(pcm_clip, tmp_path, opened):
    """A proxy is MJPEG with no audio; the track always comes from the file."""
    cache = tmp_path / "proxies"
    a = opened(pcm_clip, cache)
    assert _until(lambda: a.status == READY and a.audio.status == READY)
    from hyperspace.media import proxy
    assert _until(lambda: proxy.proxy_for(pcm_clip, cache))
    a.close()
    b = opened(pcm_clip, cache)
    assert _until(lambda: b.status == READY and b.audio.status == READY)
    assert b.read_path != pcm_clip and b.audio.path == pcm_clip
    assert _peak_hz(b.audio.read(RATE, RATE)[:, 0]) == pytest.approx(440.0, abs=1.0)
