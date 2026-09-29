"""Plan 14 WP1 — the stall log (watchdog.py), headless.

A fake clock drives the stall rules without sleeping; one test runs the
real thread over a frame that blocks, one sends the process SIGUSR1, and
the render watch is driven through `app.frame` over the host's stubs — a
`renderer.draw` that raises while the panel goes on drawing, and a render
window that stops presenting. Every log is on tmp_path, never ~/Hyperspace.
"""

import os
import signal
import threading
import time
from types import SimpleNamespace

import pytest

from hyperspace.watchdog import LIMIT, RenderWatch, Watchdog


class Clock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture()
def fake(tmp_path):
    clock = Clock()
    wd = Watchdog(tmp_path / "stall.log", clock=clock, wall=lambda: 1_790_000_000.0,
                  preset=lambda: "TUMBLE")
    assert wd.open()           # the file, without the thread: check() is driven by hand
    yield wd, clock
    wd.close()


def test_the_default_limit_is_two_seconds():
    assert LIMIT == 2.0


def test_a_stall_is_logged_once_with_every_thread(fake):
    wd, clock = fake
    wd.pet(clock.t)
    clock.t += 1.9
    assert not wd.check(), "under the limit is not a stall"
    clock.t += 0.2
    assert wd.check()
    clock.t += 5.0
    assert not wd.check() and not wd.check(), "one dump per stall, not one per tick"
    text = wd.path.read_text()
    assert text.count("=== stall ") == 1 and wd.stalls == 1
    assert "preset TUMBLE" in text
    assert "no frame for 2.1 s" in text and "last completed frame at" in text
    assert "Current thread" in text and "test_a_stall_is_logged_once" in text
    # a frame completes, then the loop stalls again: a second dump
    wd.pet(clock.t)
    clock.t += 3.0
    assert wd.check()
    assert wd.path.read_text().count("=== stall ") == 2
    assert wd.status() == f"stall log: {wd.path} (2 stalls)"


def test_no_line_until_the_log_has_entries(fake):
    wd, _ = fake
    assert wd.path.exists() and wd.status() == ""
    assert wd.counts() == {}


def test_a_frame_that_blocks_is_caught_by_the_thread(tmp_path):
    """The real thread over a loop whose frame blocks: the dump names the
    blocking frame, the loop goes on, and the next frame pets it again."""
    wd = Watchdog(tmp_path / "stall.log", limit=0.15, period=0.02).start()
    try:
        release = threading.Event()

        def a_frame_that_blocks():
            release.wait(2.0)

        def loop():
            for _ in range(3):
                wd.pet(time.perf_counter())
                time.sleep(0.01)
            a_frame_that_blocks()
            wd.pet(time.perf_counter())

        t = threading.Thread(target=loop, name="frame-loop")
        t.start()
        deadline = time.monotonic() + 2.0
        while wd.stalls == 0 and time.monotonic() < deadline:
            time.sleep(0.02)
        release.set()
        t.join(2.0)
        time.sleep(0.1)
        assert wd.stalls == 1, wd.error
        assert "a_frame_that_blocks" in wd.path.read_text()
        assert wd.error == ""
    finally:
        wd.close()
    assert wd._thread is None


@pytest.mark.skipif(not hasattr(signal, "SIGUSR1"), reason="no SIGUSR1 on this platform")
def test_sigusr1_dumps_on_demand(tmp_path):
    wd = Watchdog(tmp_path / "stall.log", limit=60.0).start()
    try:
        os.kill(os.getpid(), signal.SIGUSR1)
        deadline = time.monotonic() + 2.0
        while "Current thread" not in wd.path.read_text() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert "test_sigusr1_dumps_on_demand" in wd.path.read_text()
        assert wd.counts() == {"on demand": 1}
        assert wd.status() == f"stall log: {wd.path} (1 on demand)"
    finally:
        wd.close()


def test_it_never_stops_the_show(tmp_path, monkeypatch):
    """A log that will not open leaves the watchdog off with the reason; a
    check that raises inside the thread is kept on `error`, not raised."""
    blocker = tmp_path / "file"
    blocker.write_text("")
    wd = Watchdog(blocker / "stall.log").start()     # a file, not a directory
    assert wd.error.startswith("stall log:") and wd._thread is None
    wd.pet(0.0)
    assert not wd.check() and wd.status() == "" and not wd.log("stall", "x")
    rw = RenderWatch(wd, info=lambda: 1 / 0)          # an info that raises, a dead log
    rw.failed(RuntimeError("boom"), 0.0)
    rw.tick(0.0)
    rw.tick(5.0)
    assert rw.alerts()                                # still said on the panel
    wd.close()

    ok = Watchdog(tmp_path / "stall.log", limit=0.01, period=0.01)
    monkeypatch.setattr(ok, "check", lambda: 1 / 0)
    ok.start()
    try:
        deadline = time.monotonic() + 1.0
        while not ok.error and time.monotonic() < deadline:
            time.sleep(0.01)
        assert "ZeroDivisionError" in ok.error
        assert ok._thread.is_alive(), "the thread goes on"
    finally:
        ok.close()


def test_pet_is_a_float_write():
    wd = Watchdog("/nonexistent/never-opened.log")
    wd.pet(12.5)
    assert wd.last == 12.5


# ---------------------------------------------------------------- the render window

def _raise_in_draw():
    raise ValueError("the scene texture is gone")


def test_a_raising_draw_is_logged_once_with_its_traceback_and_bannered(fake):
    """The owner's freeze: `renderer.draw` raises every frame, `app.frame`
    swallows it so the panel goes on, and the render window holds its last
    frame. The render watch writes the full traceback once per distinct
    error, and the banner names it until a draw succeeds."""
    from test_app_boundary import _host

    from hyperspace import app

    wd, _ = fake
    log: list[str] = []
    h = _host(log)
    h.render_watch = RenderWatch(wd, info=lambda: {"presentable": True})

    def draw_render(dt):
        log.append("render.draw")
        _raise_in_draw()

    h.draw_render = draw_render
    for k in range(5):
        log.clear()
        assert app.frame(h, now=1.0 + k / 60, dt=1 / 60, fps=60.0) is False
        assert log[-2:] == ["render.draw", "panel.draw"], "the panel still draws"
    text = wd.path.read_text()
    assert text.count("=== render error ") == 1, "once per distinct error"
    assert "Traceback (most recent call last)" in text and "_raise_in_draw" in text
    assert "ValueError: the scene texture is gone" in text and "preset TUMBLE" in text
    assert h.render_watch.alerts() == [
        "render window stopped — ValueError: the scene texture is gone"]
    assert h.reloader.runtime_error.startswith("render.draw: ValueError")
    # another error is another entry; a good draw clears the banner
    h.draw_render = lambda dt: (_ for _ in ()).throw(KeyError("u_mix"))
    app.frame(h, now=2.0, dt=1 / 60, fps=60.0)
    assert wd.path.read_text().count("=== render error ") == 2
    h.draw_render = lambda dt: log.append("render.draw")
    assert app.frame(h, now=2.1, dt=1 / 60, fps=60.0) is True
    assert h.render_watch.alerts() == []
    assert h.render_watch.errors_logged == 2
    assert wd.status() == f"stall log: {wd.path} (2 render errors)"


def test_a_render_window_that_stops_presenting_is_logged(fake):
    """The frames go on, but the render window shows nothing new: hidden,
    minimised, occluded — a fullscreen Space or a second display. After
    2 s the watch logs the window's attributes, once, and the banner says
    why; a presented frame clears it and re-arms the log."""
    wd, _ = fake
    state = {"visible": True, "iconified": False, "focused": False,
             "monitor": "Projector", "framebuffer": (1920, 1080), "occluded": False,
             "presentable": True}
    rw = RenderWatch(wd, poll=0.0, info=lambda: dict(state))
    t = 0.0
    for _ in range(30):                 # healthy: presented frames
        rw.drew(t)
        rw.tick(t)
        t += 1 / 60
    assert rw.alerts() == [] and rw.stalls_logged == 0
    state.update(occluded=True, presentable=False)
    for _ in range(180):                # 3 s of frames that reach no screen
        rw.drew(t)
        rw.tick(t)
        t += 1 / 60
    assert rw.stalls_logged == 1, "once per stall"
    text = wd.path.read_text()
    assert text.count("=== render stall ") == 1
    assert "monitor=Projector" in text and "occluded=True" in text
    assert "visible=True" in text and "iconified=False" in text and "framebuffer=(1920, 1080)" in text
    assert rw.alerts() and "covered or on another Space" in rw.alerts()[0]
    state.update(occluded=False, presentable=True)
    rw.drew(t)
    rw.tick(t)
    assert rw.alerts() == []
    # the counter itself stopping (no completed draw) is a stall too
    for _ in range(150):
        rw.tick(t)
        t += 1 / 60
    assert rw.stalls_logged == 2
    assert wd.counts() == {"render stall": 2}


def test_the_backend_reads_the_window_state():
    """overlay.GlfwBackend.window_state over a fake GLFW: what the render
    stall entry records, and whether a frame reaches the screen."""
    from hyperspace.overlay import GlfwBackend

    attrs = {1: 1, 2: 0, 3: 1}
    g = SimpleNamespace(
        VISIBLE=1, ICONIFIED=2, FOCUSED=3,
        get_window_attrib=lambda w, a: attrs[a],
        get_framebuffer_size=lambda w: (2560, 1600),
        get_window_monitor=lambda w: None,
        get_window_pos=lambda w: (16, 16), get_window_size=lambda w: (1280, 800),
    )
    b = GlfwBackend(g)
    b._nswindow = lambda win: None
    st = b.window_state("win")
    assert st["presentable"] and st["monitor"] == "none (windowed)"
    assert st["framebuffer"] == (2560, 1600)
    attrs[2] = 1                          # minimised
    assert not b.window_state("win")["presentable"]
