"""Plan 32 T3: video files on their own thread, and the scrub proxies."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import av
import numpy as np
import pytest
from PIL import Image

from hyperspace.media import adapters, proxy, video
from hyperspace.media.source import READY


def _write_clip(path: Path, seconds=3, w=320, h=240, fps=30):
    with av.open(str(path), "w") as out:
        s = out.add_stream("libx264", rate=fps)
        s.width, s.height, s.pix_fmt = w, h, "yuv420p"
        s.options = {"crf": "10", "g": "30"}
        for i in range(seconds * fps):
            arr = np.full((h, w, 3), min(255, i * 2), np.uint8)
            for p in s.encode(av.VideoFrame.from_ndarray(arr, format="rgb24")):
                out.mux(p)
        for p in s.encode():
            out.mux(p)


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    p = tmp_path_factory.mktemp("clips") / "ramp.mp4"
    _write_clip(p)
    return p


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


def _gray(s):
    f = s.latest()
    return None if f is None else int(f.pixels[f.pixels.shape[0] // 2, f.pixels.shape[1] // 2, 0])


def _wants_gray(s, t, gray, tol=4):
    s.want(t)
    return _until(lambda: _gray(s) is not None and abs(_gray(s) - gray) <= tol, 2.0)


def test_duration_and_fps(clip, opened):
    s = opened(clip)
    assert _until(lambda: s.status == READY)
    assert s.timed
    assert s.duration == pytest.approx(3.0, abs=0.1)
    assert s.fps == pytest.approx(30.0, abs=0.01)


def test_want_decodes_that_frame(clip, opened):
    s = opened(clip)
    assert _wants_gray(s, 1.5, 90)
    assert s.latest().frame == 45


def test_backward_seek(clip, opened):
    s = opened(clip)
    assert _wants_gray(s, 2.5, 150)
    assert _wants_gray(s, 0.2, 12)


def test_sequential_forward(clip, opened):
    s = opened(clip)
    assert _wants_gray(s, 1.0, 60)
    assert _wants_gray(s, 1.5, 90)
    assert _wants_gray(s, 1.5 + 0.7, 132)


def test_gif_is_timed(tmp_path, opened):
    p = tmp_path / "x.gif"
    ims = [Image.new("RGB", (32, 24), (i * 40, 0, 0)) for i in range(5)]
    ims[0].save(p, save_all=True, append_images=ims[1:], duration=100, loop=0)
    s = opened(p)
    assert _until(lambda: s.status == READY)
    assert s.timed and s.duration > 0
    assert _until(lambda: s.latest() is not None)


def test_proxy_made_once_and_used(clip, tmp_path, monkeypatch, opened):
    calls = []
    real = proxy.make_proxy

    def spy(path, cache):
        calls.append(path)
        return real(path, cache)

    monkeypatch.setattr(proxy, "make_proxy", spy)
    cache = tmp_path / "proxies"
    a = opened(clip, cache)
    assert _until(lambda: proxy.proxy_for(clip, cache))
    a.close()
    b = opened(clip, cache)
    assert _until(lambda: b.status == READY)
    assert len(calls) == 1
    assert b.read_path == proxy.proxy_for(clip, cache)
    assert b.read_path.suffix == ".mov"
    assert _wants_gray(b, 1.5, 90, tol=6)


def test_proxy_shape(clip, tmp_path):
    out = proxy.make_proxy(clip, tmp_path)
    assert out == proxy.proxy_for(clip, tmp_path)
    assert not list(tmp_path.glob("*.tmp*"))
    with av.open(str(out)) as c:
        st = c.streams.video[0]
        assert st.codec_context.name == "mjpeg"
        assert st.average_rate == 30
        assert st.width <= 1280 and st.height <= 720


def test_long_clip_gets_no_proxy(clip, tmp_path, monkeypatch, opened):
    real = video._probe
    monkeypatch.setattr(video, "_probe", lambda c, st: (601.0, real(c, st)[1]))
    s = opened(clip, tmp_path / "proxies")
    assert _until(lambda: s.status == READY)
    time.sleep(0.3)
    assert proxy.proxy_for(clip, tmp_path / "proxies") is None
    assert s.duration == 601.0


def test_close_joins_thread(clip, opened):
    s = opened(clip)
    assert _until(lambda: s.status == READY)
    assert any(t.name.startswith("media-video-") for t in threading.enumerate())
    s.close()
    assert not any(t.name.startswith("media-video-") for t in threading.enumerate())


def test_open_is_idempotent(clip, opened):
    s = opened(clip)
    s.open()
    assert len([t for t in threading.enumerate() if t.name.startswith("media-video-")]) == 1


def test_status_frozen_after_close(clip, opened):
    s = opened(clip)
    s.close()
    st = s.status
    time.sleep(0.2)
    assert s.status == st


def test_truncated_file_is_error(clip, tmp_path, opened):
    p = tmp_path / "cut.mp4"
    p.write_bytes(clip.read_bytes()[: clip.stat().st_size // 2])
    s = opened(p)
    assert _until(lambda: s.status.startswith("error:"))
    assert s.latest() is None


def test_adapter_routes_video(clip):
    class R:
        def path(self, sid):
            return clip

        def live(self, sid):
            return None

    s = adapters.open_source("file:" + str(clip), R())
    assert isinstance(s, video.VideoSource)
