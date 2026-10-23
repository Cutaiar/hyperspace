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
    new = f.copy_to_shared(sid)
    assert new == "shared:pic.png"
    f.copy_jobs[new].result(5)
    assert (f.shared / "pic.png").is_file()
    assert not list(f.shared.glob("*.part"))
    f.scan()
    assert f.status(new) == "ready"
    assert f.copy_to_shared(sid) == "shared:pic (1).png"


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
