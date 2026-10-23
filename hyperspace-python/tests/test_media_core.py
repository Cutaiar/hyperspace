"""Plan 32 T1: the media core — frames, ids, the latest-frame slot, the
worker pool and still images."""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest
from PIL import Image

from hyperspace.media import adapters, frame, ids, source, still
from hyperspace.media.frame import MediaFrame, fit_within, to_rgba


def test_frame_is_read_only_rgba():
    f = MediaFrame(to_rgba(np.zeros((4, 6, 3), np.uint8)), 0.0, 0)
    assert f.size == (6, 4)
    assert f.pixels.shape == (4, 6, 4)
    assert (f.pixels[..., 3] == 255).all()
    with pytest.raises(ValueError):
        f.pixels[0, 0, 0] = 1


def test_texture_frame():
    f = MediaFrame(None, 0.0, 1, texture=7, tex_size=(32, 16))
    assert f.size == (32, 16)
    with pytest.raises(ValueError):
        MediaFrame(None, 0.0, 1)
    with pytest.raises(ValueError):
        MediaFrame(np.zeros((2, 2, 4), np.uint8), 0.0, 1, texture=3, tex_size=(2, 2))


def test_to_rgba_float():
    out = to_rgba(np.full((2, 2, 3), 0.5, np.float32))
    assert out.dtype == np.uint8 and out.shape == (2, 2, 4)
    assert out.flags.c_contiguous


def test_fit_within_caps_and_keeps_aspect():
    big = np.zeros((6000, 8000, 4), np.uint8)
    assert fit_within(big, frame.CAP_FILE).shape[:2] == (1080, 1440)
    small = np.zeros((50, 100, 4), np.uint8)
    assert fit_within(small, frame.CAP_FILE).shape[:2] == (50, 100)


def test_latest_never_torn():
    slot = source.Latest()
    assert slot.get() is None
    stop = threading.Event()

    def write():
        for i in range(2000):
            slot.put(MediaFrame(to_rgba(np.full((8, 8, 3), i % 256, np.uint8)), 0.0, i))
        stop.set()

    t = threading.Thread(target=write)
    t.start()
    seen = 0
    while not stop.is_set():
        f = slot.get()
        if f is not None:
            seen += 1
            assert (f.pixels[..., :3] == f.pixels[0, 0, 0]).all()
    t.join()
    assert slot.get().frame == 1999


def test_parse_ids():
    assert ids.parse("shared:loops/a.mp4") == ids.SourceId("shared", "loops/a.mp4")
    assert ids.parse("ndi:RIG (Arena)").ref == "RIG (Arena)"
    for bad in ("nope", "bogus:x"):
        with pytest.raises(ValueError, match=bad):
            ids.parse(bad)


def test_error_text_is_bounded():
    assert source.error("x" * 500) == "error: " + "x" * 160


def test_still_decodes_on_the_pool(monkeypatch, tmp_path):
    def slow(path, cap):
        time.sleep(0.3)
        return to_rgba(np.zeros((4, 4, 3), np.uint8))

    monkeypatch.setattr(still, "_load", slow)
    s = still.StillSource("file:x.png", tmp_path / "x.png")
    t0 = time.monotonic()
    s.open()
    assert time.monotonic() - t0 < 0.02
    assert s.latest() is None and s.status == source.FETCHING
    deadline = time.monotonic() + 1.0
    while s.status == source.FETCHING and time.monotonic() < deadline:
        time.sleep(0.01)
    assert s.status == source.READY and s.latest().size == (4, 4)
    s.close()


def _wait(s):
    deadline = time.monotonic() + 5.0
    while s.status == source.FETCHING and time.monotonic() < deadline:
        time.sleep(0.01)


def test_huge_still_is_capped(tmp_path):
    p = tmp_path / "big.png"
    Image.new("RGB", (4000, 3000), (10, 20, 30)).save(p)
    s = still.StillSource("file:big.png", p)
    s.open()
    _wait(s)
    assert s.latest().size == (1440, 1080)
    s.close()


def test_heic_opens(tmp_path):
    pillow_heif = pytest.importorskip("pillow_heif")
    p = tmp_path / "a.heic"
    pillow_heif.from_pillow(Image.new("RGB", (32, 16), (200, 100, 50))).save(str(p))
    s = still.StillSource("file:a.heic", p)
    s.open()
    _wait(s)
    assert s.status == source.READY and s.latest().pixels.shape == (16, 32, 4)
    s.close()


def test_bad_file_is_an_error(tmp_path):
    p = tmp_path / "bad.png"
    p.write_text("not an image")
    s = still.StillSource("file:bad.png", p)
    s.open()
    _wait(s)
    assert s.status.startswith("error: ")
    assert s.latest() is None
    s.close()


class _Resolver:
    def __init__(self, path=None):
        self._path = path

    def path(self, sid):
        return self._path

    def live(self, sid):
        return None


def test_missing_path_is_missing_source():
    s = adapters.open_source("shared:gone.png", _Resolver(None))
    assert s.status == source.MISSING and s.latest() is None


def test_open_source_picks_still_and_unsupported(tmp_path):
    p = tmp_path / "a.png"
    Image.new("RGB", (4, 4)).save(p)
    assert isinstance(adapters.open_source("file:a", _Resolver(p)), still.StillSource)
    q = tmp_path / "a.xyz"
    q.write_text("x")
    assert adapters.open_source("file:b", _Resolver(q)).status == "error: unsupported"


def test_pool_threads_are_named():
    from hyperspace.media import pool
    assert pool.submit(lambda: threading.current_thread().name).result(2).startswith("media-pool-")
