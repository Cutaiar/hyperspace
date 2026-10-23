"""Outputs published out (plan 32 T9): the config's `syphon` / `ndi` /
`window` keys, a publish-only output drawn offscreen with no window, each
published output's picture handed to its publishers after it is drawn,
an NDI out that never makes the frame wait, the SYSTEM lines — then
loopbacks through the real libraries (our sender read back by T8's
receivers) where they import."""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import app, config
from hyperspace.media import publish
from hyperspace.outputs import Offscreen, Presenter, Slot, Switches, View

# ---------------------------------------------------------------- the config


def test_config_reads_publish_keys(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('[[output.screens]]\nsyphon = "RIG"\n'
                 '[[output.screens]]\nwindow = false\nndi = "RIG"\nsyphon = "TD"\n')
    cfg = config.load(p)
    a, b = config.screens(cfg)
    assert (a["syphon"], a["ndi"], a["window"]) == ("RIG", "", True)
    assert (b["syphon"], b["ndi"], b["window"]) == ("TD", "RIG", False)
    assert not cfg.get("notes")
    s1, s2 = app._slots(cfg)
    assert (s1.syphon, s1.ndi, s1.window) == ("RIG", "", True)
    assert (s2.syphon, s2.ndi, s2.window) == ("TD", "RIG", False)

    # a bad type is a config note and the default — never a dead launch
    p.write_text('[[output.screens]]\n[[output.screens]]\nndi = 5\nwindow = "no"\nsyphon = true\n')
    cfg = config.load(p)
    b = config.screens(cfg)[1]
    assert (b["syphon"], b["ndi"], b["window"]) == ("", "", True)
    notes = " | ".join(cfg["notes"])
    assert "ndi = 5 is not a name" in notes and "syphon = True is not a name" in notes
    assert "window = 'no' is not true or false" in notes

    # output 1 holds the GL context and paces the loop: it always opens a window
    p.write_text('[[output.screens]]\nwindow = false\nsyphon = "RIG"\n')
    cfg = config.load(p)
    assert config.screens(cfg)[0]["window"] is True
    assert any("output 1" in n and "always opens a window" in n for n in cfg["notes"])

    # the one-output form: [output] says for output 1
    p.write_text('[output]\nsyphon = "RIG"\nndi = "RIG"\n')
    cfg = config.load(p)
    (one,) = config.screens(cfg)
    assert (one["syphon"], one["ndi"], one["window"]) == ("RIG", "RIG", True)
    p.write_text('[output]\nndi = 3\nwindow = false\n')
    cfg = config.load(p)
    (one,) = config.screens(cfg)
    assert (one["ndi"], one["window"]) == ("", True)
    notes = " | ".join(cfg["notes"])
    assert "[output] ndi = 3 is not a name" in notes and "always opens a window" in notes
    # with a list, the list says: [output] syphon is ignored, with the note
    p.write_text('[output]\nsyphon = "X"\n[[output.screens]]\nname = "a"\n')
    cfg = config.load(p)
    assert config.screens(cfg)[0]["syphon"] == ""
    assert any("syphon" in n and "ignored" in n for n in cfg["notes"])


# ---------------------------------------------------------------- no window


def test_publish_only_output_has_no_window(monkeypatch, tmp_path):
    """`window = false`: no GLFW window is made for it — not even on a
    screen that is not connected, which would leave a windowed output
    closed — and it is drawn all the same (its switches are registered,
    the OUTPUT page lists it). One with nothing to publish is not drawn,
    said once."""
    from test_app_boundary import _PlaceGlfw

    from hyperspace.overlay import register_switches
    from hyperspace.params import Registry

    p = tmp_path / "config.toml"
    p.write_text('[[output.screens]]\n'
                 '[[output.screens]]\nname = "td"\nwindow = false\nsyphon = "RIG"\nmonitor = 5\n'
                 '[[output.screens]]\nwindow = false\n')
    cfg = config.load(p)
    g = _PlaceGlfw()
    monkeypatch.setattr(app, "glfw", g)
    slots, ctrl = app._windows(False, cfg, tmp_path)
    assert len(g.size) == 2 and set(g.size) == {slots[0].win, ctrl}   # render + controls only
    _, td, idle = slots
    assert td.win is None and not td.opened and td.missing == "" and td.drawn
    assert td.publish_only and td.syphon == "RIG"
    assert idle.win is None and not idle.drawn
    assert idle.missing == "window = false and nothing to publish (no syphon or ndi)"
    assert sum("nothing to publish" in n for n in cfg["notes"]) == 1
    reg = Registry()
    register_switches(reg, slots)
    assert "output.2.scene" in reg and "output.3.scene" not in reg


class _Off:
    """An `Offscreen` stand-in: the size it was last fitted to."""

    def __init__(self):
        self.size = None
        self.fbo = SimpleNamespace(name="offscreen fbo")

    def fit(self, size):
        self.size = tuple(size)
        return self.fbo


def test_draw_render_draws_a_publish_only_output_offscreen_at_the_render_cap():
    """`_draw_render`: a publish-only output is a `View` on its offscreen
    target (the renderer's context) at the render cap's size, in its
    place among the outputs; a published output carries its publishers;
    nothing is presented or swapped for it."""
    from test_app_boundary import _Ctx, _Pres, _Renderer, _rig_slots, _SwapGlfw

    log: list[str] = []
    g = _SwapGlfw(log, {"w1": (800, 500), "w3": (640, 400)})
    app_glfw, app.glfw = app.glfw, g
    try:
        slots = _rig_slots("one", "td", "proj", presenter=lambda sl: _Pres(log, sl.name))
        slots[1].win, slots[1].presenter, slots[1].window = None, None, False
        slots[1].syphon = "RIG"
        slots[1].offscreen = off = _Off()
        pubs = [object()]
        slots[1].publishers = pubs
        r = _Renderer(log)
        r.max_frame = (1920, 1080)
        app._draw_render(r, _Ctx(log), object(), slots, flush=lambda: log.append("flush"))
        vs = r.calls[0]
        assert [v.size for v in vs] == [(800, 500), (1920, 1080), (640, 400)]
        assert vs[1].target is off.fbo and vs[1].presenter is None and off.size == (1920, 1080)
        assert vs[1].publish is pubs and vs[0].publish == [] and vs[1].switches is slots[1].switches
        assert log == ["current w1", "bind screen", "draw 3", "flush",
                       "current w3", "present proj", "swap w3", "current w1", "swap w1"]
        # "full" (no cap): output 1's framebuffer
        r.max_frame = None
        app._draw_render(r, _Ctx(log), object(), slots, flush=lambda: None)
        assert r.calls[1][1].size == (800, 500)
    finally:
        app.glfw = app_glfw


# ---------------------------------------------------------------- the picture handed over

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


class Grab:
    """A publisher that keeps a copy of each picture it is handed (rows
    GL's way: row 0 the bottom)."""

    kind, status, fps, readback_ms = "test", "sending", 0.0, 0.0

    def __init__(self, name="grab"):
        self.name, self.got, self.sizes, self.ts = name, None, [], []

    def publish(self, tex, t):
        self.sizes.append(tuple(tex.size))
        self.ts.append(t)
        self.got = np.frombuffer(tex.read(), np.uint8).reshape(tex.size[1], tex.size[0], 4)

    def close(self):
        pass


def _flat(ctx, f):
    w, h = f.size
    data = f.read(components=4)
    return np.frombuffer(data, np.uint8).reshape(h, w, 4)


def test_each_published_output_hands_its_picture_to_its_publishers(ctx):
    """After the frame, each published view's picture goes to its
    publishers as a texture of the renderer's: a publish-only view's own
    offscreen texture; a window's (here a multisampled framebuffer
    standing in for output 1's) resolved into its tap; a presenter's
    hand-off presented into its tap on this context — each the picture
    that output shows, byte for byte."""
    from test_outputs import H, W, fbo, px, rig, scene_view

    r = rig(ctx, effects=("warp",), dim=0.8)
    win = fbo(ctx, W, H, samples=4)                    # output 1's window, multisampled
    ref = fbo(ctx, W, H)                               # what a plain target of output 2 shows
    a, b, c, d = Grab("one"), Grab("pres"), Grab("off"), Grab("off2")
    off, tap1, tap2 = Offscreen(ctx), Offscreen(ctx), Offscreen(ctx)
    pres = Presenter(ctx)
    sw2 = Switches(dim=0.5)
    vs = [View(Switches(), (W, H), target=win, publish=[a], tap=tap1),
          View(sw2, (W, H), presenter=pres, publish=[b], tap=tap2),
          View(sw2, (W, H), target=off.fit((W, H)), publish=[c, d]),
          View(sw2, (W, H), target=ref)]
    s = scene_view()
    r.draw_outputs(s, W, H, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    assert ctx.fbo is win and ctx.viewport == vs[0].rect          # output 1 bound again
    want1 = px(ctx, win)[::-1]                                    # GL rows: bottom first
    want2 = _flat(ctx, ref)
    assert a.sizes == [(W, H)] and np.array_equal(a.got, want1)
    assert np.array_equal(b.got, want2) and np.array_equal(c.got, want2)
    assert np.array_equal(d.got, want2) and a.ts == [2.0]
    assert want2[..., :3].max() > 50                              # something was drawn
    # a publisher that raises is said on itself, never the frame's
    bad = Grab("bad")
    bad.publish = lambda tex, t: (_ for _ in ()).throw(RuntimeError("gone"))
    vs[2].publish = [bad, c]
    r.draw_outputs(s, W, H, 1.0, vs, t_now=2.1)
    assert vs[2].error == "" and c.ts[-1] == 2.1
    assert r.stats["publish_errors"] == {"test out bad": "RuntimeError: gone"}
    for o in (off, tap1, tap2):
        o.release()
    pres.release()


# ---------------------------------------------------------------- NDI out never blocks


class SlowSender:
    """A fake NDI sender: each frame takes 100 ms to send."""

    def __init__(self):
        self.sent: list[np.ndarray] = []
        self.threads: set[str] = set()
        self.closed = False

    def write_video(self, data):
        self.threads.add(threading.current_thread().name)
        time.sleep(0.1)
        self.sent.append(np.array(data, copy=True))

    def close(self):
        self.closed = True


def test_ndi_out_never_blocks(ctx):
    w, h = 64, 36
    tex = ctx.texture((w, h), 4)
    fb = ctx.framebuffer([tex])
    fb.use()
    ctx.clear(1.0, 0.0, 0.0, 1.0, viewport=(0, h // 2, w, h - h // 2))   # the top: red
    ctx.clear(0.0, 0.0, 1.0, 1.0, viewport=(0, 0, w, h // 2))            # the bottom: blue
    made: list = []

    def make(name, size):
        made.append((name, size))
        return snd

    snd = SlowSender()
    out = publish.NdiOut("RIG", ctx, make_sender=make)
    assert out.kind == "ndi" and out.status == "waiting"
    t0 = time.perf_counter()
    for k in range(30):
        out.publish(tex, k / 60)
    took = time.perf_counter() - t0
    assert took < 0.05, took
    assert out.dropped > 0 and out.readback_ms >= 0.0
    deadline = time.monotonic() + 2.0
    while not snd.sent and time.monotonic() < deadline:
        time.sleep(0.01)
    assert snd.sent and made == [("RIG", (w, h))]
    assert snd.threads == {"media-ndi-out-RIG"}
    # a frame behind, and the rows NDI's way: top first
    px = snd.sent[0].reshape(h, w, 4)
    assert tuple(px[0, 0]) == (255, 0, 0, 255) and tuple(px[-1, 0]) == (0, 0, 255, 255)
    assert out.status == "sending"
    assert publish.line(out).startswith("ndi out RIG — ") and "fps, readback" in publish.line(out)
    t = time.monotonic()
    out.close()
    assert time.monotonic() - t < 2.0 and snd.closed
    assert not any(th.name == "media-ndi-out-RIG" for th in threading.enumerate())
    fb.release()
    tex.release()


def test_publish_lines_and_a_missing_library_is_an_error_status(ctx, monkeypatch):
    from hyperspace.media import live

    def need(lib):
        raise live.Fault(f"{lib} not installed")

    monkeypatch.setattr(live, "need", need)
    s = publish.SyphonOut("RIG", ctx)
    n = publish.NdiOut("RIG", ctx)
    assert s.status == "error: syphon not installed" and n.status == "error: cyndilib not installed"
    s.publish(None, 0.0)                     # nothing to publish to: nothing happens
    n.publish(None, 0.0)
    assert publish.line(s) == "syphon out RIG — error: syphon not installed"
    g = Grab("x")
    g.kind, g.fps, g.readback_ms = "ndi", 59.6, 1.234
    assert publish.line(g) == "ndi out x — 60 fps, readback 1.2 ms"
    sl = Slot(2, publishers=[s, g])
    assert publish.lines([Slot(1), sl]) == [publish.line(s), publish.line(g)]
    s.close()
    n.close()


# ---------------------------------------------------------------- fix round 1


def test_a_windowed_output_publishes_at_the_capped_size(ctx):
    """A window whose framebuffer is 2× the render cap — output 1's,
    multisampled, and a presenter's — publishes the frame at the capped
    size, not an upscale at the window's: the picture a publish-only view
    of that size shows, byte for byte."""
    from test_outputs import H, W, fbo, rig, scene_view

    r = rig(ctx, effects=("warp",), dim=0.8)
    r.max_frame = (W // 2, H // 2)
    win = fbo(ctx, W, H, samples=4)
    a, b, c = Grab("one"), Grab("pres"), Grab("ref")
    off, tap1, tap2 = Offscreen(ctx), Offscreen(ctx), Offscreen(ctx)
    pres = Presenter(ctx)
    sw = Switches()
    vs = [View(sw, (W, H), target=win, publish=[a], tap=tap1),
          View(sw, (W, H), presenter=pres, publish=[b], tap=tap2),
          View(sw, (W // 2, H // 2), target=off.fit((W // 2, H // 2)), publish=[c])]
    r.draw_outputs(scene_view(), W, H, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    assert a.sizes == b.sizes == c.sizes == [(W // 2, H // 2)]
    assert np.array_equal(a.got, c.got) and np.array_equal(b.got, c.got)
    assert c.got[..., :3].max() > 50
    for o in (off, tap1, tap2):
        o.release()
    pres.release()


class _GlLost:
    """A texture whose read back fails, as a lost buffer's does."""

    size = (64, 36)
    glo = 1

    def read_into(self, *a, **k):
        raise RuntimeError("GL_INVALID_OPERATION")


class _BadTap(Offscreen):
    def fit(self, size):
        raise RuntimeError("out of memory")


def test_a_frame_half_failure_is_the_publishers_error_said_once(ctx, capsys):
    """A failure on the frame thread — NdiOut's own read back, or the
    renderer's copy for it — is the publisher's status, its SYSTEM line
    says so, and it is said once on stderr and in the notes, however many
    frames it fails."""
    from test_outputs import H, W, fbo, rig, scene_view

    notes: list[str] = []
    out = publish.NdiOut("RIG", ctx, make_sender=lambda name, size: SlowSender())
    out.notes = notes
    for k in range(3):
        out.publish(_GlLost(), k / 60)
    assert out.status == "error: RuntimeError: GL_INVALID_OPERATION"
    assert publish.line(out) == "ndi out RIG — error: RuntimeError: GL_INVALID_OPERATION"
    assert notes == ["publish: ndi out RIG: RuntimeError: GL_INVALID_OPERATION"]
    assert capsys.readouterr().err.count("GL_INVALID_OPERATION") == 1
    out.close()

    # the renderer's copy for a published window fails: the publisher is told
    r = rig(ctx, effects=())
    out = publish.NdiOut("TAP", ctx, make_sender=lambda name, size: SlowSender())
    out.notes = notes
    tap = _BadTap(ctx)
    vs = [View(Switches(), (W, H), target=fbo(ctx, W, H), publish=[out], tap=tap)]
    for k in range(3):
        r.draw_outputs(scene_view(), W, H, 1.0, vs, t_now=2.0 + k / 60)
    assert vs[0].error == "" and out.status == "error: RuntimeError: out of memory"
    assert "error: RuntimeError: out of memory" in publish.line(out)
    assert notes[-1] == "publish: ndi out TAP: RuntimeError: out of memory" and len(notes) == 2
    assert r.stats["publish_errors"] == {"ndi out TAP": "RuntimeError: out of memory"}
    out.close()


def test_fps_falls_to_zero_when_nothing_was_sent_for_a_second(ctx, monkeypatch):
    from hyperspace.media import live

    class Server:
        def __init__(self, name):
            self.n = 0

        def publish_frame_texture(self, glo, size=None):
            self.n += 1

        def stop(self):
            pass

    monkeypatch.setattr(live, "need", lambda lib: SimpleNamespace(SyphonOpenGLServer=Server))
    now = [100.0]
    out = publish.SyphonOut("RIG", ctx, clock=lambda: now[0])
    tex = SimpleNamespace(glo=1, size=(64, 36))
    for _ in range(90):
        out.publish(tex, now[0])
        now[0] += 1 / 60
    assert 55 < out.fps < 65 and publish.line(out).startswith("syphon out RIG — 60 fps")
    now[0] += 1.1                                       # nothing sent for over a second
    assert out.fps == 0.0 and publish.line(out) == "syphon out RIG — 0 fps, readback 0.0 ms"
    out.publish(tex, now[0])                            # sending again: counted afresh
    assert out.status == "sending"
    out.close()


# ---------------------------------------------------------------- loopbacks


def test_ndi_out_loopback(ctx):
    """Our NDI out, read back by T8's receiver: the mean colour matches
    and the picture is the right way up."""
    pytest.importorskip("cyndilib")
    from hyperspace.media.ndi import NdiKind
    from hyperspace.media.source import READY

    w, h = 160, 90
    tex = ctx.texture((w, h), 4)
    fb = ctx.framebuffer([tex])
    fb.use()
    ctx.clear(0.9, 0.1, 0.1, 1.0, viewport=(0, h // 2, w, h - h // 2))   # the top: red
    ctx.clear(0.1, 0.1, 0.9, 1.0, viewport=(0, 0, w, h // 2))            # the bottom: blue
    want = np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)[::-1]   # top first
    out = publish.NdiOut("RIG-T9", ctx)
    k = NdiKind("ndi", {})
    k.open()
    src = None
    try:
        t0 = time.monotonic()
        n = 0
        while src is None and time.monotonic() - t0 < 6.0:
            out.publish(tex, n / 30)
            n += 1
            k.poll(0.016, time.monotonic())
            src = next((s for sid, s in k.media_sources().items() if "RIG-T9" in sid), None)
            time.sleep(0.03)
        assert src is not None, k.media_sources()
        src.open()
        t0 = time.monotonic()
        while src.latest() is None and time.monotonic() - t0 < 4.0:
            out.publish(tex, n / 30)
            n += 1
            time.sleep(0.03)
        f = src.latest()
        assert f is not None and f.size == (w, h) and src.status == READY, src.status
        got = f.pixels.astype(float)
        # NDI's codec is lossy (a YUV round trip): the means within 16 of 255
        assert np.abs(got[..., :3].mean(axis=(0, 1)) - want[..., :3].mean(axis=(0, 1))).max() < 16
        assert got[2, w // 2, 0] > 180 and got[-3, w // 2, 2] > 180     # red on top
        t0 = time.monotonic()                     # fps is counted over a second
        while out.fps == 0 and time.monotonic() - t0 < 3.0:
            out.publish(tex, n / 30)
            n += 1
            time.sleep(0.03)
        assert out.fps > 0 and out.status == "sending"
        src.close()
    finally:
        k.close()
        t = time.monotonic()
        out.close()
        assert time.monotonic() - t < 2.0
        fb.release()
        tex.release()


# (last in the file: it makes a window's context current; the module's
# standalone context is made current again at its end)
def test_syphon_out_loopback(ctx):
    """Our Syphon out, read back by T8's Syphon source: the texture handed
    over (no readback), its colours and its way up intact."""
    import gc

    pytest.importorskip("syphon")
    from test_media_live import _gl_context

    from hyperspace.media.frame import TEX_RECT
    from hyperspace.media.source import READY
    from hyperspace.media.syphon import SyphonKind
    from hyperspace.media_tex import MediaTextures

    made = _gl_context()
    if made is None:
        pytest.skip("no GL context")
    glfw, win, gctx = made
    w, h = 64, 32
    tex = gctx.texture((w, h), 4)
    fbo = gctx.framebuffer([tex])
    fbo.use()
    gctx.clear(1.0, 0.0, 0.0, 1.0, viewport=(0, h // 2, w, h // 2))   # the top: red
    gctx.clear(0.0, 0.0, 1.0, 1.0, viewport=(0, 0, w, h // 2))        # the bottom: blue
    gctx.finish()
    out = publish.SyphonOut("hs-t9-loop", gctx)
    k = SyphonKind("syphon", {})
    k.open()
    src = f = mt = None
    try:
        assert out.status == "waiting", out.status
        t0 = time.monotonic()
        while src is None and time.monotonic() - t0 < 6.0:
            out.publish(tex, time.monotonic())
            glfw.poll_events()
            k.poll(0.016, time.monotonic())
            src = next((s for sid, s in k.media_sources().items()
                        if sid.endswith("/hs-t9-loop")), None)
            time.sleep(0.016)
        assert src is not None, k.media_sources()
        assert out.status == "sending" and out.readback_ms == 0.0
        src.open()
        t0 = time.monotonic()
        while f is None and time.monotonic() - t0 < 3.0:
            out.publish(tex, time.monotonic())
            f = src.gl_poll()
            time.sleep(0.016)
        assert f is not None and src.status == READY and f.size == (w, h)
        assert f.tex_target == TEX_RECT
        _ = gctx.error
        mt = MediaTextures(gctx)
        got = mt.texture("a", f)
        assert got is not None and mt.error == ""
        px = np.frombuffer(got.read(), np.uint8).reshape(h, w, 4)     # GL rows: row 0 the bottom
        assert tuple(px[h - 2, w // 2]) == (255, 0, 0, 255)         # the top: red
        assert tuple(px[1, w // 2]) == (0, 0, 255, 255)             # the bottom: blue
        src.close()
        src.shut()
    finally:
        k.close()
        out.close()
        # everything holding the window's GL freed while its context is
        # current (T6's lesson), then the module's context current again
        if mt is not None:
            mt.release()
        src = f = mt = out = k = None
        gc.collect()
        gctx.release()
        glfw.destroy_window(win)
        ctx.__enter__()
