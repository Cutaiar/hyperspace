"""Plan 45 V1: a video's audio track decoded to memory, under the
transport's clock. The clips are synthesized here with PyAV (no committed
fixture): a known tone in each channel, so the decode is checked by the
frequency it recovers."""

from __future__ import annotations

import threading
import time
import tracemalloc
from pathlib import Path

import av
import numpy as np
import pytest

from hyperspace.media import adapters, video
from hyperspace.media.source import FETCHING, READY

RATE = video.AUDIO_RATE


def _write_clip(path: Path, *, seconds=3.0, arate=44100, acodec="pcm_s16le",
                tones=(440.0, 880.0), tone_at=None, video_too=True, offset_s=0.0,
                audio_offset_s=None, drop=None):
    """A clip with `tones` (Hz, one per channel; one tone = mono) in its
    audio and, unless `video_too` is False, a grey ramp of video. With
    `tone_at` = (t_s, hz) every channel switches to `hz` from `t_s` on.
    `offset_s` puts both streams' first pts that far after zero (a file
    whose timeline does not start at 0); `audio_offset_s` the audio's alone.
    `drop` = (from_s, to_s) leaves the audio frames starting in that span
    out of the file (a pts gap; only a .mkv keeps one)."""
    if audio_offset_s is None:
        audio_offset_s = offset_s
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
        aoff = round(audio_offset_s * arate)
        for i in range(0, n, chunk):
            if drop is not None and drop[0] <= i / arate < drop[1]:
                continue
            part = [p[i:i + chunk] for p in planes]
            if fmt == "fltp":
                arr = np.stack(part).astype(np.float32)
            else:
                arr = (np.stack(part, 1).reshape(1, -1) * 32767).astype(np.int16)
            fr = av.AudioFrame.from_ndarray(arr, format=fmt, layout=a.layout.name)
            fr.sample_rate = arate
            fr.pts = aoff + i
            fr.time_base = a.codec_context.time_base
            for p in a.encode(fr):
                out.mux(p)
        for p in a.encode():
            out.mux(p)
        if video_too:
            voff = round(offset_s * 30)
            for i in range(int(seconds * 30)):
                vf = av.VideoFrame.from_ndarray(np.full((48, 64, 3), (i * 2) % 256, np.uint8),
                                                format="rgb24")
                if offset_s or audio_offset_s:
                    vf.pts = voff + i
                    vf.time_base = v.codec_context.time_base
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
def late_clip(tmp_path_factory):
    """The tones again, both streams' first pts at 2 s: `start_time` is 2 s
    on the audio and the video, the audio's duration 3 s."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "late.mov", offset_s=2.0)


@pytest.fixture(scope="module")
def aoff_clip(tmp_path_factory):
    """The video from 0, the audio's first pts at 0.5 s (AAC priming, an
    edit list, a screen recording): the track ends at 3.5 s of the clip."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "aoff.mov", audio_offset_s=0.5)


@pytest.fixture(scope="module")
def gap_clip(tmp_path_factory):
    """3 s of 8 kHz mono in a .mkv, 440 Hz then 880 Hz from 1.5 s, with the
    audio frames of 1.0..1.5 s left out: a pts gap the container keeps."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "gap.mkv", arate=8000,
                       tones=(440.0,), tone_at=(1.5, 880.0), drop=(1.0, 1.5))


@pytest.fixture(scope="module")
def long_clip(tmp_path_factory):
    """30 s of 8 kHz mono PCM: 300 Hz for 15 s, then 600 Hz. Small enough to
    write in a blink; long enough for a (patched) window to move in."""
    return _write_clip(tmp_path_factory.mktemp("audio") / "long.mov", seconds=30.0,
                       arate=8000, tones=(300.0,), tone_at=(15.0, 600.0), video_too=False)


@pytest.fixture
def opened():
    made = []

    def make(path, cache=None, sound=True):
        s = video.VideoSource("file:" + str(path), path, cache=cache)
        made.append(s)
        s.open()
        if sound:
            s.audio.enable()
        return s

    yield make
    for s in made:
        s.close()


@pytest.fixture
def small_window(monkeypatch):
    """A 4 s window that moves after 1 s, so the 30 s clip is a long film."""
    monkeypatch.setattr(video, "AUDIO_WINDOW_S", 4.0)
    monkeypatch.setattr(video, "AUDIO_RECENTRE_S", 1.0)


WAIT_S = 10.0   # every gate and poll waits this long at most: headroom for a loaded machine


class _Gate:
    """`av.AudioResampler` with a gate in `resample`: the first call sets
    `inside` and waits for `release`, so a test can act while a window
    decode is provably mid-loop. `calls` counts every `resample`, so a
    test can say how far the loop went after the gate — state, not
    wall time."""

    def __init__(self, monkeypatch):
        self.inside = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        real = av.AudioResampler
        gate = self

        class Gated:
            def __init__(self, *a, **kw):
                self._r = real(*a, **kw)

            def resample(self, fr):
                gate.calls += 1
                if not gate.inside.is_set():
                    gate.inside.set()
                    gate.release.wait(WAIT_S)
                return self._r.resample(fr)

        monkeypatch.setattr(av, "AudioResampler", Gated)


def _until(fn, timeout=WAIT_S):
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


def _video_threads():
    return [t for t in threading.enumerate() if t.name.startswith("media-video-")]


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


def test_a_file_whose_timeline_starts_late_is_held_from_its_first_sample(late_clip, opened):
    """Review 1: pts are the container's, the window is transport time. A
    file whose streams start at 2 s (MPEG-TS, a MOV with an edit list) is
    the whole 3 s from sample 0, not one second and then silence."""
    s = opened(late_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.duration == pytest.approx(3.0, abs=0.01)
    assert a.held == pytest.approx((0.0, 3.0), abs=0.002)
    out = a.read(2 * RATE, RATE)                         # the last second, in transport time
    assert _peak_hz(out[:, 0]) == pytest.approx(440.0, abs=1.0)
    assert _peak_hz(out[:, 1]) == pytest.approx(880.0, abs=1.0)


def test_a_window_into_a_late_file_is_cut_in_transport_time(late_clip, opened, small_window,
                                                            monkeypatch):
    """Review 1, the window: a 4 s window from 0.5 s of a file whose pts
    start at 2 s holds transport seconds 0.5..3 (all the sound there is),
    not 0.5..2.5 cut by the file's offset. The position is set before the
    sound is asked for: a `want` after `enable` races the thread's first
    window (made at position 0, and 2.5 is inside it, so it stays), which
    is what a loaded CI runner saw."""
    monkeypatch.setattr(video, "_audio_end", lambda c, st, o: 7200.0)   # a long film
    s = opened(late_clip, sound=False)
    s.want(2.5)                                           # the window is 0.5..4.5
    s.audio.enable()
    a = s.audio
    assert _until(lambda: a.held is not None)
    assert a.held == pytest.approx((0.5, 3.0), abs=0.05)
    assert a.status == READY
    out = a.read(2 * RATE, RATE)                          # 2..3: the tail is there, in time
    assert _peak_hz(out[:, 0]) == pytest.approx(440.0, abs=1.0)
    assert _peak_hz(out[:, 1]) == pytest.approx(880.0, abs=1.0)
    assert not a.read(0, RATE // 4).any()                 # before the window: silence
    assert not a.read(3 * RATE + 48, RATE // 4).any()     # past the track (a ms on): silence


def test_a_track_that_starts_after_the_video_keeps_its_tail(aoff_clip, opened):
    """Review B1: the track's end is its own start (less the video's) plus
    its length. Audio from 0.5 s under video from 0 ends at 3.5 s, and the
    last half second is held, not cut by the offset."""
    s = opened(aoff_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.duration == pytest.approx(3.5, abs=0.01)
    assert a.held == pytest.approx((0.0, 3.5), abs=0.002)
    assert not a.read(0, RATE // 4).any()                 # before the track: silence
    tail = a.read(3 * RATE, RATE // 2)                    # 3.0..3.5: the tail is there
    assert np.abs(tail).max() == pytest.approx(0.5, abs=0.02)
    assert _peak_hz(a.read(2 * RATE, RATE)[:, 1]) == pytest.approx(880.0, abs=1.0)


def test_a_pts_gap_is_silence_and_the_rest_keeps_its_time(gap_clip, opened):
    """Review B5: each resampled frame is laid by its own time. Frames
    missing from 1.0 to 1.5 s read as silence there, and the 880 Hz that
    starts at 1.5 s is at 1.5 s — not pulled back to 1.0 with the file's
    end gone quiet."""
    s = opened(gap_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.duration == pytest.approx(3.0, abs=0.01)
    assert _peak_hz(a.read(0, RATE)[:, 0]) == pytest.approx(440.0, abs=1.0)
    hole = a.read(RATE + RATE // 20, RATE // 2 - RATE // 10)   # 1.05..1.45
    assert not hole.any()
    body = a.read(2 * RATE, RATE)
    assert _peak_hz(body[:, 0]) == pytest.approx(880.0, abs=1.0)
    level = np.abs(body).max()                                 # mono sits on both sides at −3 dB
    assert level == pytest.approx(0.5 / np.sqrt(2), abs=0.02)
    last = a.read(3 * RATE - RATE // 4, RATE // 4)             # 2.75..3.0 is still there
    assert np.abs(last).max() == pytest.approx(level, rel=0.05)


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


def test_read_into_the_readers_own_buffer(pcm_clip, opened):
    """Plan 45 V2 (second review): `read(at, n, out=)` writes into the
    reader's buffer — zeros where nothing is held, every stale sample
    overwritten — and returns its first n rows; the same samples as
    without `out`."""
    s = opened(pcm_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    buf = np.full((400, 2), 7.0, np.float32)
    got = a.read(3 * RATE - 100, 200, out=buf)
    assert got.base is buf and got.shape == (200, 2)
    assert np.array_equal(got, a.read(3 * RATE - 100, 200))
    assert not got[100:].any() and (buf[200:] == 7.0).all()
    assert not a.read(10 * RATE, 300, out=buf).any() and (buf[300:] == 7.0).all()


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


# -- nothing until asked (review 9) ----------------------------------------------

def test_nothing_is_read_until_something_asks_for_sound(pcm_clip, opened, monkeypatch):
    opens = []
    real = av.open

    def spy(*a, **kw):
        opens.append(a[0])
        return real(*a, **kw)

    monkeypatch.setattr(av, "open", spy)
    s = opened(pcm_clip, sound=False)
    assert _until(lambda: s.status == READY)
    time.sleep(0.05)
    assert s.audio.status == video.OFF and not s.audio.enabled
    assert not _audio_threads()
    assert opens == [str(pcm_clip)]                      # the picture's open, no other
    assert not s.audio.read(0, 512).any() and s.audio.nbytes == 0
    s.audio.enable()                                     # V2's play-audio toggle
    assert _until(lambda: s.audio.status == READY)
    assert opens == [str(pcm_clip)] * 2
    s.audio.disable()
    assert s.audio.status == video.OFF and s.audio.nbytes == 0 and s.audio.held is None
    assert not _audio_threads()
    s.audio.enable()
    assert _until(lambda: s.audio.status == READY)
    assert s.audio.held == pytest.approx((0.0, 3.0), abs=0.002)


def test_enable_on_a_closed_source_starts_nothing(pcm_clip, opened):
    """Review B3: `close` is for good — an `enable` after it starts no
    thread nobody would close. `disable` is not: `enable` after it works."""
    s = opened(pcm_clip)
    assert _until(lambda: s.audio.status == READY)
    s.close()
    s.audio.enable()
    time.sleep(0.05)
    assert not _audio_threads() and s.audio._thread is None
    s.audio.disable()
    s.audio.enable()
    time.sleep(0.05)
    assert not _audio_threads()


def test_enable_before_open_decodes_at_open(pcm_clip):
    s = video.VideoSource("file:" + str(pcm_clip), pcm_clip)
    s.audio.enable()
    assert not _audio_threads() and s.audio.status == video.OFF
    try:
        s.open()
        assert _until(lambda: s.audio.status == READY)
    finally:
        s.close()


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
    monkeypatch.setattr(video, "_audio_end", lambda c, st, o: 7200.0)
    s = opened(pcm_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert a.duration == 7200.0 and not a.whole
    assert a.nbytes <= video.AUDIO_WINDOW_BYTES
    assert a.held[0] == 0.0 and a.held[1] <= video.AUDIO_WINDOW_S


def test_a_window_is_decoded_into_one_buffer(pcm_clip, opened):
    """Review 3: no chunk list and no concatenate — the peak while a window
    is made is the window, not three of it."""
    tracemalloc.start()
    try:
        s = opened(pcm_clip)
        a = s.audio
        assert _until(lambda: a.status == READY)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert a.nbytes == 3 * RATE * 8
    assert a._win.data.base is None                     # owns its memory: no view of a bigger one
    # the old way held the chunks and their concatenation at once: 2× and more.
    # 1.75 leaves room for the resampler's frames and whatever else the
    # process allocates meanwhile (tracemalloc counts every thread)
    assert peak < a.nbytes * 1.75


def test_a_clip_of_unknown_length_holds_only_what_is_there(pcm_clip, opened, monkeypatch):
    """Review B6: with no length from the probe the window is 120 s, but a
    3 s clip must not allocate 46 MB for it: the buffer starts small and
    doubles, and what is held is the 3 s."""
    monkeypatch.setattr(video, "_audio_end", lambda c, st, o: 0.0)
    tracemalloc.start()
    try:
        s = opened(pcm_clip)
        a = s.audio
        assert _until(lambda: a.status == READY)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert not a.whole and a.held == pytest.approx((0.0, 3.0), abs=0.002)
    assert a.nbytes == 3 * RATE * 8
    # 2 s → 4 s doubling (2 + 4) and the trim to 3 s: 2.33× the clip; 4× is
    # headroom for the process's other allocations. The window would be 40×
    assert peak < 4 * a.nbytes
    assert peak < 8 * 2**20
    assert _peak_hz(a.read(RATE, RATE)[:, 0]) == pytest.approx(440.0, abs=1.0)


def test_a_right_sized_buffer_is_handed_over_without_a_copy():
    b = video._Buffer(8, 8, 2)
    assert b.lay(0, np.ones((8, 2), np.float32)) == 8
    assert b.done() is b.data
    g = video._Buffer(2, 10, 2)                          # unknown length: grows to what lands
    assert g.lay(0, np.ones((3, 2), np.float32)) == 3
    assert len(g.data) == 4 and g.filled == 3
    assert g.lay(6, np.full((6, 2), 2.0, np.float32)) == 12   # clipped at cap
    assert len(g.data) == 10 and g.filled == 10
    out = g.done()
    assert out.shape == (10, 2) and not out[3:6].any() and out[6:].all()
    assert video._Buffer(5, 5, 2).lay(-2, np.ones((3, 2), np.float32)) == 1   # before the window


def test_status_is_fetching_while_the_transport_is_outside_the_window(
        long_clip, opened, small_window, monkeypatch):
    """Review B7: READY means the wanted position is in what is held. A
    far scrub reads FETCHING until the window arrives, with the old
    window still held."""
    gate = threading.Event()
    calls = []
    real = video.Soundtrack._decode

    def slow_second(self, *args):
        calls.append(args[3])
        if len(calls) == 2:
            gate.wait(WAIT_S)
        return real(self, *args)

    monkeypatch.setattr(video.Soundtrack, "_decode", slow_second)
    s = opened(long_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    s.want(20.0)
    assert _until(lambda: len(calls) == 2)
    assert a.status == FETCHING and a.held == pytest.approx((0.0, 4.0), abs=0.05)
    gate.set()
    assert _until(lambda: a.status == READY)
    assert a.held == pytest.approx((18.0, 22.0), abs=0.05)
    s.want(30.0)                                          # inside: the window's own end
    assert a.status == FETCHING                           # 30 is past 22 until it moves
    s.want(22.0)
    assert a.status == READY                              # the end is in


def test_a_whole_track_at_its_end_is_ready(pcm_clip, opened):
    s = opened(pcm_clip)
    assert _until(lambda: s.audio.status == READY)
    s.want(3.0)
    assert s.audio.status == READY
    s.want(3.5)
    assert s.audio.status == FETCHING


@pytest.mark.parametrize("how", ["fails", "empty"])
def test_a_whole_track_that_fails_or_is_empty_retries_on_the_next_move(pcm_clip, opened,
                                                                       monkeypatch, how):
    """Review B4: a whole track's failed or empty first window keeps the
    thread alive and `want` waking it, so a move of a second tries again."""
    calls = []
    real = video.Soundtrack._decode

    def once_bad(self, container, stream, origin, a, b, stop):
        calls.append(a)
        if len(calls) == 1:
            if how == "fails":
                raise RuntimeError("a bad packet")
            return video._Window(0, np.zeros((0, 2), np.float32))
        return real(self, container, stream, origin, a, b, stop)

    monkeypatch.setattr(video.Soundtrack, "_decode", once_bad)
    s = opened(pcm_clip)
    a = s.audio
    want_status = "error:" if how == "fails" else video.NO_AUDIO
    assert _until(lambda: a.status.startswith(want_status))
    assert a.whole and a.held is None and _audio_threads()
    s.want(0.5)                                           # under a second: not yet
    time.sleep(0.1)
    assert len(calls) == 1
    s.want(1.5)                                           # the next move: retried
    assert _until(lambda: a.status == READY)
    assert a.held == pytest.approx((0.0, 3.0), abs=0.002)
    assert _until(lambda: not _audio_threads())           # and then, whole, the thread ends


def test_an_abandoned_decode_publishes_nothing(pcm_clip, opened, monkeypatch):
    """Review B2: a thread `close` gave up on while its window was being
    made must not write that window back once the samples were let go."""
    inside, release = threading.Event(), threading.Event()
    real = video.Soundtrack._decode

    def held_up(self, *args):
        win = real(self, *args)
        inside.set()
        release.wait(WAIT_S)
        return win

    monkeypatch.setattr(video.Soundtrack, "_decode", held_up)
    s = opened(pcm_clip)
    old = _audio_threads()
    assert inside.wait(WAIT_S) and len(old) == 1
    s.audio.close(0.05)                                   # gives up on the thread mid-publish
    assert s.audio.held is None
    release.set()
    assert _until(lambda: not old[0].is_alive())
    assert s.audio.held is None and s.audio.status != READY


def test_the_window_follows_the_transport(long_clip, opened, small_window):
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


def test_a_whole_track_lets_its_thread_and_file_go(pcm_clip, opened):
    """Review 4: once a whole track is in there is nothing to follow — the
    thread ends, the container closes, and `want` wakes nobody."""
    s = opened(pcm_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    assert _until(lambda: not _audio_threads())
    assert _video_threads()                                  # the picture goes on
    a._wake.clear()
    s.want(2.0)
    assert not a._wake.is_set()
    assert _peak_hz(a.read(2 * RATE, RATE)[:, 0]) == pytest.approx(440.0, abs=1.0)


def test_a_far_scrub_abandons_the_window_being_decoded(long_clip, opened, small_window,
                                                        monkeypatch):
    """Review 5: a decode checks where the transport is now, not only the
    stop flag, so a scrub across a long film never finishes a stale window
    first."""
    gate = _Gate(monkeypatch)
    results = []
    real = video.Soundtrack._decode

    def spy(self, *a):
        r = real(self, *a)
        results.append(None if r is None else (r.start / RATE, r.end / RATE))
        return r

    monkeypatch.setattr(video.Soundtrack, "_decode", spy)
    s = opened(long_clip)
    assert gate.inside.wait(WAIT_S)                          # mid-decode of 0..4
    s.want(25.0)
    gate.release.set()
    assert _until(lambda: s.audio.held is not None and s.audio.held[0] > 22.0)
    assert results[0] is None                                # the stale window was dropped
    assert s.audio.held == pytest.approx((23.0, 27.0), abs=0.05)
    assert all(r is None or r[0] > 22.0 for r in results)    # 0..4 was never published


def test_a_window_that_fails_keeps_the_old_one_and_the_next_move_retries(
        long_clip, opened, small_window, monkeypatch):
    """Review 2: one window's error is that window's, not the track's."""
    calls = []
    real = video.Soundtrack._decode

    def flaky(self, container, stream, origin, a, b, stop):
        calls.append(a)
        if len(calls) == 2:
            raise RuntimeError("a bad packet")
        return real(self, container, stream, origin, a, b, stop)

    monkeypatch.setattr(video.Soundtrack, "_decode", flaky)
    s = opened(long_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    s.want(20.0)
    assert _until(lambda: a.status.startswith("error:"))
    assert "a bad packet" in a.status
    assert a.held == pytest.approx((0.0, 4.0), abs=0.05)     # the old window stays
    assert _audio_threads()                                  # the thread goes on
    time.sleep(0.1)
    assert len(calls) == 2                                   # no retry while it sits
    s.want(20.5)                                             # under AUDIO_RETRY_S: not yet
    time.sleep(0.1)
    assert len(calls) == 2
    s.want(10.0)                                             # the next move retries
    assert _until(lambda: a.status == READY and a.held[0] > 7.0)
    assert a.held == pytest.approx((8.0, 12.0), abs=0.05)


def test_an_empty_window_is_not_held(long_clip, opened, small_window, monkeypatch):
    """Review 6: a decode with nothing in it leaves the old window and the
    status; the next move tries again."""
    calls = []
    real = video.Soundtrack._decode

    def hollow(self, container, stream, origin, a, b, stop):
        calls.append(a)
        if len(calls) == 2:
            return video._Window(round(a * RATE), np.zeros((0, 2), np.float32))
        return real(self, container, stream, origin, a, b, stop)

    monkeypatch.setattr(video.Soundtrack, "_decode", hollow)
    s = opened(long_clip)
    a = s.audio
    assert _until(lambda: a.status == READY)
    s.want(20.0)
    assert _until(lambda: len(calls) == 2)
    time.sleep(0.1)
    assert a.held == pytest.approx((0.0, 4.0), abs=0.05)   # the old window stays
    assert a.status == FETCHING                              # 20 is outside it (review B7)
    s.want(10.0)
    assert _until(lambda: a.held is not None and a.held[0] > 7.0)
    assert a.held == pytest.approx((8.0, 12.0), abs=0.05)


# -- never on the frame thread ----------------------------------------------------

def test_opening_never_blocks_the_caller(pcm_clip, opened, monkeypatch):
    """`open`, `want` and `read` return while `av.open` is still held shut:
    the state says so (nothing probed, nothing held), and the clock only
    has to beat the gate's own wait, which a blocked caller would sit out."""
    real = av.open
    gate = threading.Event()

    def slow(*a, **kw):
        gate.wait(WAIT_S)
        return real(*a, **kw)

    monkeypatch.setattr(av, "open", slow)
    t0 = time.monotonic()
    s = opened(pcm_clip)
    s.want(1.0)
    out = s.audio.read(RATE, 512)
    elapsed = time.monotonic() - t0
    assert not gate.is_set() and s.audio.status == FETCHING and not out.any()
    assert elapsed < WAIT_S / 2          # a caller that blocked on the open would wait WAIT_S
    gate.set()
    assert _until(lambda: s.audio.status == READY)


def test_close_joins_the_audio_thread_too(long_clip, opened, small_window):
    s = opened(long_clip)
    assert _until(lambda: s.audio.status == READY)
    assert _audio_threads()                                  # a long clip keeps following
    s.close()
    assert not _audio_threads()
    assert s.audio._thread is None
    s.close()                                                # twice is fine


def test_close_is_quick_mid_decode(long_clip, opened, small_window, monkeypatch):
    """Review 10: `close` while a window decode is provably inside its
    loop. Quick means the loop stops at its next check instead of
    finishing the window: the gated `resample` is the only one that ran,
    and the join found the thread gone — state, not a stopwatch."""
    gate = _Gate(monkeypatch)
    s = opened(long_clip)
    assert gate.inside.wait(WAIT_S)
    assert _audio_threads() and s.audio.status == FETCHING   # inside, nothing published yet
    threading.Timer(0.05, gate.release.set).start()          # let the loop turn once more
    s.close(timeout=WAIT_S)
    assert not _audio_threads()                              # the join returned with it gone
    assert gate.calls == 1                                   # no frame decoded past the stop
    assert s.audio.held is None                              # the window was never published


def test_an_abandoned_thread_never_resumes_beside_a_new_one(pcm_clip, opened, monkeypatch):
    """Review 8: each start has a stop event of its own. A thread stuck in
    `av.open` when `close` gave up on it ends when the open returns, and
    the source opened again runs one thread a kind."""
    real = av.open
    gate = threading.Event()
    opens = []

    def slow(*a, **kw):
        opens.append(a[0])
        if len(opens) <= 2:                                  # the first video and audio opens hang
            gate.wait(WAIT_S)
        return real(*a, **kw)

    monkeypatch.setattr(av, "open", slow)
    s = opened(pcm_clip)
    assert _until(lambda: len(opens) == 2)
    old = _video_threads() + _audio_threads()
    s.close(0.05)                                            # gives up on both
    assert all(t.is_alive() for t in old)
    s.open()
    s.audio.enable()
    assert _until(lambda: len(opens) == 4)
    gate.set()                                               # the old opens return
    assert _until(lambda: not any(t.is_alive() for t in old))
    assert _until(lambda: s.status == READY and s.audio.status == READY)
    assert len(_video_threads()) == 1
    assert len(_audio_threads()) <= 1                        # whole: the new one may be done
    s.want(1.0)
    time.sleep(0.1)
    assert s.status == READY and s.audio.status == READY     # nothing stale wrote over them


def test_the_adapter_hands_out_a_source_with_a_soundtrack(pcm_clip):
    class R:
        def path(self, sid):
            return pcm_clip

        def live(self, sid):
            return None

    s = adapters.open_source("file:" + str(pcm_clip), R())
    assert isinstance(s.audio, video.Soundtrack)
    assert video.VideoSource.audio is None                   # a source from before plan 45
    assert s.audio.status == video.OFF and s.audio.read(0, 4).shape == (4, 2)
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
