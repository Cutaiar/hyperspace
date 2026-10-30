"""The media folder (plan 32 T4): scan, watch, status, thumbnails, copies."""

import os
import threading
import time

import pytest
from PIL import Image

from hyperspace.media import folder as mf
from hyperspace.media import pool
from hyperspace.media.folder import MediaFolder


def png(path, color=(200, 30, 30), size=(40, 20)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


@pytest.fixture
def mk(tmp_path):
    made = []

    def make(shared=True):
        f = MediaFolder(tmp_path / "lib" / "media" if shared else None,
                        tmp_path / "home" / "media", tmp_path / "home" / "media-cache")
        made.append(f)
        return f
    yield make
    for f in made:
        f.stop()


def wait_for(cond, t=3.0):
    end = time.monotonic() + t
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


def test_scan_lists_shared_and_local(mk):
    f = mk()
    png(f.shared / "a" / "b.png")
    (f.local / "c.mp4").write_bytes(b"x" * 100)
    es = {e.sid: e for e in f.scan()}
    assert set(es) == {"shared:a/b.png", "local:c.mp4"}
    assert es["shared:a/b.png"].group == "a" and es["shared:a/b.png"].kind == "still"
    assert es["local:c.mp4"].group == "" and es["local:c.mp4"].kind == "video"
    assert es["shared:a/b.png"].status == "ready"
    assert f.path("shared:a/b.png") == f.shared / "a" / "b.png"
    assert f.live("camera:x") is None and f.proxy_cache == f.cache / "proxies"


def test_dropped_file_appears_within_a_scan(mk):
    f = mk()
    f.start(every=0.1)
    c0 = f.changed
    png(f.local / "new.png")
    assert wait_for(lambda: any(e.sid == "local:new.png" for e in f.entries), 1.0)
    assert f.changed > c0


def test_removed_file_is_missing(mk):
    f = mk()
    p = png(f.local / "a.png")
    f.scan()
    assert f.status("local:a.png") == "ready"
    p.unlink()
    f.scan()
    assert f.status("local:a.png") == "missing"
    assert f.path("local:a.png") is None


def test_junk_does_not_stop_the_scan(mk):
    f = mk()
    png(f.local / "good.png")
    (f.local / "note.txt").write_text("hi")
    (f.local / "empty.mp4").write_bytes(b"")
    (f.local / "x.png").mkdir()
    es = {e.sid: e for e in f.scan()}
    assert es["local:good.png"].status == "ready"
    assert es["local:empty.mp4"].status != "ready"
    assert "local:note.txt" not in es and "local:x.png" not in es
    allv = {e.sid: e for e in f.scan(all=True)}
    assert allv["local:note.txt"].status == "error: unsupported"


def test_slow_read_is_fetching(mk, monkeypatch):
    f = mk()
    png(f.local / "a.png")
    monkeypatch.setattr(mf, "_probe", lambda p: 0.6)
    f.scan()
    assert f.status("local:a.png") == "fetching"
    monkeypatch.undo()
    f.scan()
    assert f.status("local:a.png") == "ready"


def test_dataless_flag_is_fetching(mk, monkeypatch):
    f = mk()
    (f.local / "a.mp4").write_bytes(b"")
    real = os.stat

    class St:
        def __init__(self, st):
            self._st = st
            self.st_flags = mf.SF_DATALESS

        def __getattr__(self, k):
            return getattr(self._st, k)
    monkeypatch.setattr(mf.os, "stat", lambda p, *a, **k: St(real(p, *a, **k)))
    f.scan()
    assert f.status("local:a.mp4") == "fetching"


def test_conflict_copies_are_listed(mk):
    f = mk()
    png(f.local / "a.png")
    png(f.local / "a (1).png")
    assert {e.sid for e in f.scan()} == {"local:a.png", "local:a (1).png"}


def test_thumb_keyed_by_mtime(mk):
    f = mk()
    p = png(f.local / "a.png")
    f.scan()
    assert f.thumb("local:a.png") is None
    assert wait_for(lambda: f.thumb("local:a.png") is not None)
    t1 = f.thumb("local:a.png")
    assert t1.parent == f.cache / "thumbs"
    with Image.open(t1) as im:
        assert max(im.size) <= 160
    st = p.stat()
    os.utime(p, (st.st_atime, st.st_mtime + 10))
    f.scan()
    assert f.thumb("local:a.png") is None
    assert wait_for(lambda: f.thumb("local:a.png") is not None)
    assert f.thumb("local:a.png") != t1


def test_add_file_and_copy_to_shared(mk, tmp_path):
    f = mk()
    src = png(tmp_path / "elsewhere" / "pic.png")
    sid = f.add_file(src)
    assert sid == f"file:{src.resolve()}"
    f.scan()
    assert f.status(sid) == "ready" and f.path(sid) == src.resolve()
    new = f.copy_to_shared(sid).result(5)
    assert new == "shared:pic.png"
    assert (f.shared / "pic.png").is_file()
    assert not list(f.shared.glob("*.part"))
    f.scan()
    assert f.status(new) == "ready"
    assert f.copy_to_shared(sid).result(5) == "shared:pic (1).png"
    assert {e.sid: e.group for e in f.entries}[sid] == "added"


def test_no_library_means_no_shared(mk):
    f = mk(shared=False)
    assert f.shared is None and f.local.is_dir()
    png(f.local / "a.png")
    assert [e.sid for e in f.scan()] == ["local:a.png"]
    with pytest.raises(ValueError):
        f.copy_to_shared("local:a.png")
    assert f.path("shared:a.png") is None


def test_stop_joins_the_timer_promptly(mk):
    f = mk()
    f.start(every=5.0)
    t = time.monotonic()
    f.stop()
    assert time.monotonic() - t < 1.0
    assert not any(th.name == "media-folder-watch" for th in threading.enumerate())
    pool.shutdown()


def test_blocked_read_does_not_stall_the_scan(mk, monkeypatch):
    f = mk()
    png(f.local / "a.png")
    png(f.local / "b.png")
    gate, calls = threading.Event(), []

    def stuck(p):
        calls.append(p)
        if p.name == "a.png":
            gate.wait(10)
        return 0.0
    monkeypatch.setattr(mf, "_probe", stuck)
    t = time.monotonic()
    f.scan()
    assert time.monotonic() - t < 1.0
    assert f.status("local:a.png") == "fetching" and f.status("local:b.png") == "ready"
    n = len([c for c in calls if c.name == "a.png"])
    f.scan()
    assert len([c for c in calls if c.name == "a.png"]) == n   # no second probe
    assert f.status("local:a.png") == "fetching"
    gate.set()
    assert wait_for(lambda: (f.scan(), f.status("local:a.png"))[1] == "ready")


def test_dataless_file_wakes_once(mk, monkeypatch):
    f = mk()
    (f.local / "a.mp4").write_bytes(b"")
    gate, calls = threading.Event(), []
    monkeypatch.setattr(mf, "_probe", lambda p: (calls.append(p), gate.wait(10), 0.0)[2])
    real = os.stat

    class St:
        def __init__(self, st):
            self._st = st
            self.st_flags = mf.SF_DATALESS

        def __getattr__(self, k):
            return getattr(self._st, k)
    monkeypatch.setattr(mf.os, "stat", lambda p, *a, **k: St(real(p, *a, **k)))
    for _ in range(4):
        f.scan()
    assert wait_for(lambda: len(calls) >= 1)
    assert len(calls) == 1
    gate.set()


def test_added_file_is_listed_and_goes_missing(mk, tmp_path):
    f = mk()
    src = png(tmp_path / "away" / "p.png")
    sid = f.add_file(src)
    f.scan()
    e = next(e for e in f.entries if e.sid == sid)
    assert e.group == "added" and e.status == "ready"
    src.unlink()
    f.scan()
    assert f.status(sid) == "missing" and f.path(sid) is None


def test_replaced_file_gets_a_new_mtime(mk):
    f = mk()
    p = png(f.local / "a.png")
    f.scan()
    m0 = f.entries[0].mtime
    png(p, color=(0, 255, 0))
    st = p.stat()
    os.utime(p, (st.st_atime, st.st_mtime + 5))
    f.scan()
    assert f.entries[0].mtime != m0


def test_unseen_id_makes_no_disk_access(mk, monkeypatch):
    f = mk()
    png(f.local / "a.png")

    def boom(*a, **k):
        raise AssertionError("disk touched")
    monkeypatch.setattr(mf.Path, "is_file", boom)
    monkeypatch.setattr(mf.Path, "exists", boom)
    monkeypatch.setattr(mf.os, "stat", boom)
    assert f.path("local:a.png") is None
    assert f.status("local:a.png") == "missing"
    assert f.thumb("local:a.png") is None


def test_video_thumb(mk):
    av = pytest.importorskip("av")
    import numpy as np
    f = mk()
    p = f.local / "c.mp4"
    with av.open(str(p), "w") as c:
        s = c.add_stream("mpeg4", rate=10)
        s.width, s.height, s.pix_fmt = 64, 48, "yuv420p"
        for _ in range(3):
            fr = av.VideoFrame.from_ndarray(np.full((48, 64, 3), 128, np.uint8), format="rgb24")
            for pk in s.encode(fr):
                c.mux(pk)
        for pk in s.encode():
            c.mux(pk)
    f.scan()
    assert f.status("local:c.mp4") == "ready"
    f.thumb("local:c.mp4")
    assert wait_for(lambda: f.thumb("local:c.mp4") is not None)


def test_a_file_still_downloading_is_not_opened_until_it_is_ready(mk, monkeypatch):
    """Final review A-I1: a `fetching` (cloud-dataless) file has no path,
    so no channel opens it (a read would block until the download lands);
    once it is downloaded the next scan says `ready`, gives the path, and
    moves `changed` — the status is part of what a scan compares."""
    f = mk()
    (f.local / "a.png").write_bytes(b"x" * 1000)
    real = os.stat
    dataless = {"on": True}

    class St:
        def __init__(self, st):
            self._st = st
            self.st_flags = mf.SF_DATALESS if dataless["on"] else 0

        def __getattr__(self, k):
            return getattr(self._st, k)
    monkeypatch.setattr(mf.os, "stat", lambda p, *a, **k: St(real(p, *a, **k)))
    f.scan()
    assert f.status("local:a.png") == "fetching" and f.path("local:a.png") is None
    was = f.changed
    dataless["on"] = False                     # the download landed
    # the read the first scan started (the one that asks for the download)
    # is done before the next looks: one still in flight reads `fetching`
    assert wait_for(lambda: not f._inflight)
    f.scan()
    assert f.status("local:a.png") == "ready" and f.path("local:a.png") == f.local / "a.png"
    assert f.changed == was + 1


def test_thumbnails_have_their_own_worker_and_a_short_queue():
    """A-m2: thumbnail jobs never queue on the pool a still a channel wants
    decodes on, and at most `THUMB_QUEUE` wait — the oldest past that are
    dropped (their rows scrolled past)."""
    gate = threading.Event()
    jobs = [pool.submit_thumb(gate.wait)]
    try:
        assert wait_for(lambda: jobs[0].running(), 1.0)
        jobs += [pool.submit_thumb(gate.wait) for _ in range(pool.THUMB_QUEUE + 5)]
        # a still's decode on the pool runs at once, behind no thumbnail
        name = pool.submit(lambda: threading.current_thread().name).result(1.0)
        assert name.startswith("media-pool-")
        waiting = [j for j in jobs if not j.running() and not j.cancelled()]
        assert len(waiting) == pool.THUMB_QUEUE
        assert all(j.cancelled() for j in jobs[1:6])         # the oldest dropped
    finally:
        gate.set()
    assert jobs[-1].result(2.0) is True


def test_thumbnail_makes_go_on_the_thumbnail_worker(mk, monkeypatch):
    """The folder's thumbnail jobs are the thumbnail worker's (A-m2)."""
    f = mk()
    png(f.local / "a.png")
    f.scan()
    names = []
    monkeypatch.setattr(mf.thumbs, "make",
                        lambda p, out: names.append(threading.current_thread().name))
    f.thumb("local:a.png")
    assert wait_for(lambda: names) and names[0].startswith("media-thumb-")
