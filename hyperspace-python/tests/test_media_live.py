"""Live media feeds (plan 32 T8): the shared `LiveSource` / `LiveKind`
over a fake reader and a fake clock — a feed that stops holds 1 s then
goes black, comes back with no reopen, is let go 5 s after the last
channel, and is found off the frame thread — then NDI, Syphon and the
cameras on the device registry, and loopbacks through the real
libraries where they import."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import app, config, devices
from hyperspace.media import live, ndi
from hyperspace.media.camera import PERMISSION, CameraKind
from hyperspace.media.channels import MediaState
from hyperspace.media.ndi import NdiKind
from hyperspace.media.source import LOST, READY
from hyperspace.media.syphon import SyphonKind


class Clock:
    def __init__(self, t: float = 100.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


class FakeReader:
    """Frames while `on`; counts opens and closes."""

    def __init__(self):
        self.on = True
        self.opens = self.closes = self.reads = 0

    def open(self):
        self.opens += 1

    def read(self):
        self.reads += 1
        return np.full((4, 6, 3), 200, np.uint8) if self.on else None

    def close(self):
        self.closes += 1


def until(cond, timeout: float = 3.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.005)
    return cond()


def quiet_reads(reader: FakeReader) -> None:
    """Wait until the source thread is past any read that made a frame."""
    n = reader.reads
    until(lambda: reader.reads > n + 2)


# ---- the source ----

def test_live_holds_then_black():
    clk, r = Clock(), FakeReader()
    src = live.LiveSource("ndi:X", r, kind="ndi", clock=clk)
    src.open()
    try:
        assert until(lambda: src.latest() is not None)
        f = src.latest()
        assert f.size == (6, 4) and f.pixels[0, 0, 3] == 255 and src.status == READY
        r.on = False                      # the sender stops
        quiet_reads(r)
        last = src.latest()
        clk.t = last.t + 0.5
        assert src.latest() is last and src.status == READY      # held
        clk.t = last.t + live.HOLD_S
        assert src.latest() is last
        clk.t = last.t + live.HOLD_S + 0.01
        assert src.latest() is None and src.status == LOST       # then black
        assert not src.timed and src.duration == 0.0
    finally:
        src.shut()


def test_sender_returns():
    clk, r = Clock(), FakeReader()
    src = live.LiveSource("ndi:X", r, kind="ndi", clock=clk)
    src.open()
    try:
        assert until(lambda: src.latest() is not None)
        r.on = False
        quiet_reads(r)
        clk.t += 5.0
        assert src.status == LOST and src.latest() is None
        n = src._n
        r.on = True                       # back on the network
        assert until(lambda: src.latest() is not None and src._n > n)
        assert src.status == READY
        assert r.opens == 1 and r.closes == 0     # never reconnected
    finally:
        src.shut()
    assert r.closes == 1


def test_a_reader_that_raises_is_an_error_and_is_opened_again(monkeypatch):
    monkeypatch.setattr(live, "RETRY_S", 0.01)
    clk = Clock()

    class Flaky(FakeReader):
        def read(self):
            if self.opens == 1:
                raise OSError("wire pulled")
            return super().read()

    r = Flaky()
    src = live.LiveSource("camera:C", r, kind="camera", clock=clk)
    src.open()
    try:
        assert until(lambda: r.opens >= 2 and src.latest() is not None)
        assert src.status == READY and r.closes >= 1
    finally:
        src.shut()


class FakeKind(live.LiveKind):
    kind = "fake"
    lib = "fake"

    def __init__(self, *a, found=None, sleep=0.0, **kw):
        super().__init__(*a, **kw)
        self.found = dict(found if found is not None else {"ndi:X": "X"})
        self.sleep = sleep
        self.readers: dict[str, FakeReader] = {}
        self.threads: list[str] = []

    def discover(self):
        self.threads.append(threading.current_thread().name)
        time.sleep(self.sleep)
        return self.found

    def source(self, sid):
        r = self.readers[sid] = FakeReader()
        return live.LiveSource(sid, r, kind="ndi", clock=self.clock)


def test_discovery_off_the_frame_thread():
    k = FakeKind("ndi", {}, sleep=0.5)
    k.open()
    try:
        t = time.perf_counter()
        k.poll(0.016, 0.0)
        assert time.perf_counter() - t < 0.010
        assert k.media_sources() == {} and k.status == "lost"
        assert until(lambda: "ndi:X" in k.media_sources())
        assert k.threads and all(n.startswith("media-pool") for n in k.threads)
        assert k.status == "connected — 1 feed" and k.last == "ndi:X"
        k.poll(0.016, 1.0)                # under SCAN_S: no second scan
        k.poll(0.016, 2.5)
        assert until(lambda: len(k.threads) == 2)
    finally:
        k.close()


def test_feed_closed_when_unheld():
    clk = Clock()
    k = FakeKind("ndi", {}, clock=clk)
    k.open()
    try:
        k._scan()
        src = k.media_sources()["ndi:X"]
        r = k.readers["ndi:X"]
        src.open()                        # a channel puts it on…
        assert until(lambda: src.latest() is not None)
        src.close()                       # …and takes it off
        clk.t += live.RELEASE_S - 0.1
        k.poll(0.016, 0.0)
        assert src.running and r.closes == 0
        src.open()                        # back within 5 s: the same connection
        src.close()
        clk.t += live.RELEASE_S - 0.1
        k.poll(0.016, 0.0)
        assert src.running and r.opens == 1
        clk.t += 0.2
        k.poll(0.016, 0.0)                # nobody for 5 s: let go, joined on the pool
        assert not src.running
        assert until(lambda: r.closes == 1)
        assert not any(t.name == "media-live-ndi:X" for t in threading.enumerate()
                       if t.is_alive())
        src.open()                        # asked for again: a fresh connection
        assert until(lambda: r.opens == 2 and src.latest() is not None)
    finally:
        k.close()
    assert r.closes == 2


def test_a_held_feed_that_vanishes_is_kept_and_found_again():
    clk = Clock()
    k = FakeKind("ndi", {}, clock=clk)
    k.open()
    try:
        k._scan()
        src = k.media_sources()["ndi:X"]
        src.open()
        k.found = {}                      # the sender quit
        k._scan()
        assert k.media_sources() == {} and k.status == "lost"
        k.poll(0.016, 0.0)
        k.found = {"ndi:X": "X"}          # and came back
        k._scan()
        assert k.media_sources()["ndi:X"] is src
    finally:
        k.close()


def test_missing_library_is_an_error_status(monkeypatch):
    for name, cls in (("cyndilib", NdiKind), ("syphon", SyphonKind),
                      ("AVFoundation", CameraKind)):
        monkeypatch.setitem(sys.modules, name, None)       # import raises ImportError
        k = cls(cls.kind, {})
        k.open()
        try:
            k._scan()
            assert k.status == f"error: {name} not installed", name
            assert k.media_sources() == {}
        finally:
            k.close()


def test_a_refused_camera_says_where_to_allow_it(monkeypatch):
    dev = SimpleNamespace(authorizationStatusForMediaType_=lambda t: 2,
                          devicesWithMediaType_=lambda t: [])
    monkeypatch.setitem(sys.modules, "AVFoundation",
                        SimpleNamespace(AVCaptureDevice=dev, AVMediaTypeVideo="vide"))
    k = CameraKind("camera", {})
    k.open()
    try:
        k._scan()
        assert k.status == f"error: {PERMISSION}"
        assert PERMISSION.startswith("camera permission (System Settings ▸ Privacy")
    finally:
        k.close()


def test_cameras_are_listed_by_name(monkeypatch):
    names = [SimpleNamespace(localizedName=lambda n=n: n) for n in ("FaceTime HD", "Cam Link")]
    dev = SimpleNamespace(authorizationStatusForMediaType_=lambda t: 3,
                          devicesWithMediaType_=lambda t: names)
    monkeypatch.setitem(sys.modules, "AVFoundation",
                        SimpleNamespace(AVCaptureDevice=dev, AVMediaTypeVideo="vide"))
    k = CameraKind("camera", {})
    k.open()
    try:
        k._scan()
        assert sorted(k.media_sources()) == ["camera:Cam Link", "camera:FaceTime HD"]
        assert k.media_sources()["camera:Cam Link"].reader.name == "Cam Link"
    finally:
        k.close()


def _fake_av(monkeypatch, takes):
    """AVFoundation allowing the camera, and an `av` whose avfoundation
    input opens only with the options in `takes` (EINVAL otherwise, as
    FFmpeg says for a mode the device does not list); the tries in order."""
    from hyperspace.media import camera

    dev = SimpleNamespace(authorizationStatusForMediaType_=lambda t: 3)
    monkeypatch.setitem(sys.modules, "AVFoundation",
                        SimpleNamespace(AVCaptureDevice=dev, AVMediaTypeVideo="vide"))
    tried = []

    def open_(name, format=None, options=None):
        tried.append(dict(options or {}))
        if dict(options or {}) not in takes:
            raise OSError(22, "Invalid argument")
        return SimpleNamespace(demux=lambda video=0: iter(()), close=lambda: None)
    monkeypatch.setitem(sys.modules, "av", SimpleNamespace(open=open_))
    return camera, tried


def test_a_camera_without_720p_opens_in_a_mode_it_has(monkeypatch):
    """Final review A-I2: a capture card offering only 1080p opens at it —
    the modes are tried in order, and the one that opened is kept for the
    next open."""
    camera, tried = _fake_av(monkeypatch, [{"framerate": "30", "video_size": "1920x1080"}])
    r = camera.CameraReader("Cam Link")
    r.open()
    assert [t.get("video_size") for t in tried] == ["1280x720", "1920x1080"]
    r.close()
    tried.clear()
    r.open()
    assert [t.get("video_size") for t in tried] == ["1920x1080"]


def test_a_camera_with_no_mode_says_what_was_tried(monkeypatch):
    """A-I2: when every mode is refused the status says so, not EINVAL;
    the device's default (no options) is the last try."""
    camera, tried = _fake_av(monkeypatch, [])
    r = camera.CameraReader("Odd Cam")
    with pytest.raises(live.Fault) as e:
        r.open()
    assert str(e.value).startswith("no supported mode (tried 1280x720@30")
    assert "default" in str(e.value) and tried[-1] == {}
    assert len(tried) == len(camera.MODES)


# ---- NDI's names and its config ----

def test_ndi_ids_are_the_stream_names():
    assert ndi.ids_for(["STUDIO (RIG)", "LAPTOP (Arena)"]) == {
        "ndi:RIG": "STUDIO (RIG)", "ndi:Arena": "LAPTOP (Arena)"}
    # one stream name on two hosts: each by its full name
    assert ndi.ids_for(["A (Out)", "B (Out)"]) == {"ndi:A (Out)": "A (Out)",
                                                   "ndi:B (Out)": "B (Out)"}


def test_extra_ips_go_in_the_apps_ndi_config_before_cyndilib(monkeypatch, tmp_path):
    seen = {}

    class Finder:
        def __init__(self):
            seen["dir"] = os.environ.get("NDI_CONFIG_DIR")

        def set_change_callback(self, cb):
            pass

        def open(self):
            pass

        def get_source_names(self):
            return ["FAR (Resolume)"]

        def close(self):
            seen["closed"] = True

    monkeypatch.setitem(sys.modules, "cyndilib", SimpleNamespace(Finder=Finder))
    monkeypatch.delenv("NDI_CONFIG_DIR", raising=False)
    k = NdiKind("ndi", {"extra_ips": ["192.168.1.50", "10.0.0.7"]},
                devices.Context(home=tmp_path))
    k.open()
    try:
        k._scan()
        folder = tmp_path / "ndi"
        assert seen["dir"] == str(folder)
        doc = json.loads((folder / ndi.CONFIG_NAME).read_text())
        assert doc == {"ndi": {"networks": {"ips": "192.168.1.50,10.0.0.7"}}}
        assert k.status == "connected — 1 feed; extra_ips via NDI config (unverified)"
        assert list(k.media_sources()) == ["ndi:Resolume"]
    finally:
        k.close()
    assert seen["closed"]
    # no extra_ips: no file, the user's own NDI config left alone
    monkeypatch.delenv("NDI_CONFIG_DIR", raising=False)
    k = NdiKind("ndi", {}, devices.Context(home=tmp_path / "other"))
    k.open()
    k._scan()
    k.close()
    assert "NDI_CONFIG_DIR" not in os.environ and not (tmp_path / "other").exists()


# ---- on the device registry, through the app's resolver ----

def test_the_live_kinds_are_registry_kinds_that_feed_nothing():
    kinds = devices.kinds()
    assert (kinds["ndi"], kinds["syphon"], kinds["camera"]) == (NdiKind, SyphonKind, CameraKind)
    for cls in (NdiKind, SyphonKind, CameraKind):
        assert cls.feeds == () and cls.schemes == ()
    cfg_entries, problems = _read(
        '[[devices]]\nrole = "ndi"\nkind = "ndi"\n[[devices]]\nrole = "cam"\nkind = "camera"\n')
    assert problems == []
    assert cfg_entries == [{"role": "ndi", "kind": "ndi", "enabled": True, "extra_ips": []},
                           {"role": "cam", "kind": "camera", "enabled": True}]
    assert 'kind = "syphon"  enabled = true' in config.__doc__


def _read(text: str):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "config.toml"
        p.write_text(text)
        return config.read_devices(p)


def test_media_feeds_and_the_resolver(monkeypatch):
    clk = Clock()
    a = FakeKind("ndi", {}, clock=clk)
    b = FakeKind("ndi2", {}, found={"ndi:X": "X", "ndi:Y": "Y"}, clock=clk)
    off = FakeKind("ndi3", {}, found={"ndi:Z": "Z"}, clock=clk)
    reg = devices.DeviceRegistry(devices=[a, b, off])
    for d in (a, b):
        reg._open(d)
        d._scan()
    off.open()
    off._scan()                           # found, but the registry never opened it
    feeds = reg.media_feeds()
    assert list(feeds) == ["ndi:X", "ndi:Y"]
    assert feeds["ndi:X"] is a.media_sources()["ndi:X"]   # the first device's
    r = app.MediaResolver(SimpleNamespace(path=lambda sid: None), reg)
    assert r.live("ndi:Y") is b.media_sources()["ndi:Y"] and r.live("ndi:Z") is None
    assert app.MediaResolver(SimpleNamespace()).live("ndi:X") is None   # no registry yet

    # a channel puts ndi:X on: the shared source opens and shows frames
    ms = MediaState(r)
    ms.assign("a", 0, "ndi:X")
    ms.assign("b", 0, "ndi:W")            # not on the network
    ms.poll(0.016, 0.0)
    src = feeds["ndi:X"]
    assert ms.channels["a"].source is src and src.held == 1
    assert until(lambda: ms.frame("a") is not None)
    assert ms.status("a") == READY and ms.missing() == ["ndi:W"]
    ms.close()
    assert src.held == 0
    reg.close()
    off.close()
    assert not src.running and reg.media_feeds() == {}


def test_a_channel_follows_its_device_remade_by_a_config_edit(monkeypatch):
    """Review I1: an edit to the entry (extra_ips added) closes the device
    and opens a new one with new source objects; a channel holding the old
    one picks up the new one at its next recheck, with no slot switch."""
    real = devices.kinds
    monkeypatch.setattr(devices, "kinds", lambda: {**real(), "fake": FakeKind})
    entry = {"role": "net", "kind": "fake", "enabled": True}
    reg = devices.DeviceRegistry([entry])
    reg.open_all()
    first = reg.get("net")
    first._scan()
    ms = MediaState(app.MediaResolver(SimpleNamespace(path=lambda sid: None), reg))
    ms.assign("a", 0, "ndi:X")
    ms.poll(0.016, 0.0)
    old = ms.channels["a"].source
    assert old is first.media_sources()["ndi:X"]
    assert until(lambda: ms.frame("a") is not None)

    assert reg.apply([{**entry, "extra_ips": ["10.0.0.7"]}])     # closed and made again
    second = reg.get("net")
    assert second is not first and not old.running
    second._scan()
    ms.poll(0.016, 0.5)                   # before the recheck: still the old one
    assert ms.channels["a"].source is old
    ms.poll(0.016, 0.5 + 1.0)             # channels.RECHECK_S later
    new = ms.channels["a"].source
    assert new is second.media_sources()["ndi:X"] and new is not old and new.held == 1
    assert until(lambda: ms.frame("a") is not None) and ms.status("a") == READY
    assert ms.drain(2.0) and old.held == 0       # the old one went through the closer

    # a feed that has only gone (not remade) stays held, to be found again
    second.found = {}
    second._scan()
    ms.poll(0.016, 3.0)
    assert ms.channels["a"].source is new
    ms.close()
    reg.close()


# ---- loopbacks through the real libraries ----

def test_ndi_loopback():
    cl = pytest.importorskip("cyndilib")
    w, h = 160, 90
    snd = cl.Sender("RIG")
    vf = cl.VideoSendFrame()
    vf.set_resolution(w, h)
    vf.set_frame_rate(Fraction(30, 1))
    vf.set_fourcc(cl.FourCC.BGRA)
    snd.set_video_frame(vf)
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 2], img[..., 3] = 220, 255          # BGRA: red
    stop = threading.Event()

    def send():
        while not stop.is_set():
            snd.write_video(img.ravel())         # clocked to 30 fps

    snd.open()
    th = threading.Thread(target=send, daemon=True)
    th.start()
    k = NdiKind("ndi", {})
    k.open()
    try:
        t0 = time.monotonic()
        while "ndi:RIG" not in k.media_sources() and time.monotonic() - t0 < 5.0:
            k.poll(0.016, time.monotonic())
            time.sleep(0.016)
        src = k.media_sources().get("ndi:RIG")
        assert src is not None, k.media_sources()
        src.open()
        assert until(lambda: src.latest() is not None, 3.0), src.status
        f = src.latest()
        assert f.size == (w, h) and src.status == READY
        r, g, b, a = (int(v) for v in f.pixels[h // 2, w // 2])
        assert r > 180 and g < 40 and b < 40 and a == 255    # RGBA, no swizzle
        src.close()
    finally:
        stop.set()
        th.join(2.0)
        t = time.monotonic()
        k.close()
        assert time.monotonic() - t < 2.0
        snd.close()


def _gl_context():
    """A hidden GLFW window's GL 3.3 core context, current on this thread,
    as the spike made one; None where none can be made."""
    try:
        import glfw
        import moderngl
    except ImportError:
        return None
    if not glfw.init():
        return None
    glfw.window_hint(glfw.VISIBLE, False)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    win = glfw.create_window(64, 64, "t8", None, None)
    glfw.default_window_hints()
    if not win:
        return None
    glfw.make_context_current(win)
    try:
        return glfw, win, moderngl.create_context()
    except Exception:  # noqa: BLE001
        glfw.destroy_window(win)
        return None


def test_syphon_loopback():
    syphon = pytest.importorskip("syphon")
    made = _gl_context()
    if made is None:
        pytest.skip("no GL context")
    glfw, win, ctx = made
    w, h = 64, 32
    tex = ctx.texture((w, h), 4)
    fbo = ctx.framebuffer([tex])
    fbo.use()
    # not one colour: a read of the wrong texture must not pass (T6 fix
    # round: the bind as 2D failed and read the last 2D texture, this red)
    ctx.clear(1.0, 0.0, 0.0, 1.0, viewport=(0, 0, w // 2, h))          # left: red
    ctx.clear(0.0, 0.0, 1.0, 1.0, viewport=(w // 2, 0, w - w // 2, h))  # right: blue
    ctx.clear(0.0, 1.0, 0.0, 1.0, viewport=(0, 0, w, h // 4))           # the bottom: green
    ctx.finish()
    srv = syphon.SyphonOpenGLServer("hs-t8-loop")
    k = SyphonKind("syphon", {})
    k.open()
    try:
        assert k._scanner is not None and k._scanner.name == "media-discover-syphon"
        src = None
        t0 = time.monotonic()
        while src is None and time.monotonic() - t0 < 6.0:
            srv.publish_frame_texture(tex.glo, size=(w, h))
            glfw.poll_events()            # the app's event poll: Syphon hears servers here
            t = time.perf_counter()
            k.poll(0.016, time.monotonic())
            assert time.perf_counter() - t < 0.010      # the scan is not on this thread
            src = next((s for sid, s in k.media_sources().items()
                        if sid.endswith("/hs-t8-loop")), None)
            time.sleep(0.016)
        assert src is not None, k.media_sources()
        assert src.sid.startswith("syphon:") and k.status.startswith("connected")
        src.open()
        f = None
        t0 = time.monotonic()
        while f is None and time.monotonic() - t0 < 3.0:
            srv.publish_frame_texture(tex.glo, size=(w, h))
            f = src.gl_poll()             # the frame thread, the context current
            time.sleep(0.016)
        assert f is not None, src.status
        assert f.pixels is None and f.texture and f.size == (w, h) and src.status == READY
        # the real path (T6): an IOSurface's rectangle texture, copied on the
        # GPU into a 2D texture of our own — never uploaded — and read back
        from hyperspace.media.frame import TEX_RECT
        from hyperspace.media_tex import MediaTextures

        assert f.tex_target == TEX_RECT
        _ = ctx.error                          # (what Syphon's own calls left)
        mt = MediaTextures(ctx)
        got = mt.texture("a", f)
        assert ctx.error == "GL_NO_ERROR" and mt.error == ""
        assert got is not None and got.size == (w, h) and mt.blits == 1 and mt.uploads == 0
        px = np.frombuffer(got.read(), np.uint8).reshape(h, w, 4)     # GL rows: row 0 the bottom
        assert ctx.error == "GL_NO_ERROR"
        assert tuple(px[h // 2, w // 4]) == (255, 0, 0, 255)         # left: red
        assert tuple(px[h // 2, 3 * w // 4]) == (0, 0, 255, 255)     # right: blue
        # which way up: GL's bottom row (read first) green, its top row not
        assert tuple(px[0, w // 4]) == tuple(px[0, 3 * w // 4]) == (0, 255, 0, 255)
        assert tuple(px[h - 1, w // 4]) == (255, 0, 0, 255)
        assert tuple(px[h - 1, 3 * w // 4]) == (0, 0, 255, 255)
        mt.release()
        src.close()
        src.shut()
        assert src._client is None
    finally:
        k.close()
        srv.stop()
        ctx.release()
        glfw.destroy_window(win)
