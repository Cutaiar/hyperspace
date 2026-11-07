"""SC3a through real GL: the real `app._draw_render`, real looks and real windows
(hidden ones) on the root's context. Goldens never run `_draw_render`, so what they
can't see is here: the frame's MSAA, overlay's alpha on the window, no display live,
and a hot reload's hooks in the right context (audit V8)."""

from __future__ import annotations

import gc
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

glfw = pytest.importorskip("glfw")

from hyperspace import app
from hyperspace.outputs import Offscreen, Root, Slot, Switches, View
from hyperspace.pacing import Pacer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


SIZE = (320, 200)


def _hints(transparent=False, visible=False):
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 0)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, transparent)
    glfw.window_hint(glfw.VISIBLE, visible)


class _Stage:
    """The root and its windows as `app.main` makes them, every one hidden."""

    def __init__(self, moderngl):
        self.moderngl = moderngl
        self.root_win = app._root_window()
        if not self.root_win:
            pytest.skip("no window")
        glfw.make_context_current(self.root_win)
        self.ctx = moderngl.create_context()
        self.ctx.gc_mode = "auto"
        self.root = Root(self.root_win, Offscreen(self.ctx), Pacer(glfw))
        self.wins = []

    def output(self, n=1, transparent=False, **kw) -> Slot:
        _hints(transparent)
        win = glfw.create_window(*SIZE, f"output {n}", None, self.root_win)
        self.wins.append(win)
        glfw.make_context_current(win)
        glfw.swap_interval(0)
        slot = Slot(n, win=win, presenter=app.Presenter(self.moderngl.create_context()), **kw)
        glfw.make_context_current(self.root_win)
        return slot

    def close_output(self, slot: Slot) -> None:
        """SC3b's order (the spike's trap): the window current, its objects let go,
        then destroyed. With the root current, a release deleted the root's VAO of
        the same name."""
        win = slot.win
        glfw.make_context_current(win)
        slot.presenter.release()
        glfw.destroy_window(win)
        self.wins.remove(win)
        slot.win, slot.presenter = None, None
        glfw.make_context_current(self.root_win)


@pytest.fixture
def stage(gl_window_ok):
    moderngl = pytest.importorskip("moderngl")
    if not glfw.init():
        pytest.skip("glfw.init failed")
    st = _Stage(moderngl)
    try:
        yield st
    finally:
        gc.collect()         # this context's objects, while it lives: left for the next
        #                      test's, their release is that context's GL_INVALID_VALUE
        for w in st.wins:
            glfw.destroy_window(w)
        glfw.destroy_window(st.root_win)
        glfw.default_window_hints()
        glfw.terminate()     # (not left up for the worker's later tests: row 606)


def _rig(stage, slug="party-tumble", hands="absent"):
    """A corpus look through the golden rig's frame, which pins the clock."""
    import golden_frames as gf

    rig = gf.Rig(slug, hands, stage.ctx)
    rig.renderer.max_frame = None
    return rig


def _proxy(rig):
    """`rig.frame` as `_draw_render` calls a renderer: the same draw, clock pinned."""
    return SimpleNamespace(bg_alpha=rig.renderer.bg_alpha, max_frame=rig.renderer.max_frame,
                           draw_outputs=lambda _s, w, h, dpr, views: rig.frame(views, (w, h), dpr))


def _frame_px(stage):
    fbo = stage.root.frame.fbo
    size = fbo.size
    return np.frombuffer(fbo.read(viewport=(0, 0, *size), components=4),
                         dtype=np.uint8).reshape(size[1], size[0], 4).copy()


def test_the_frame_keeps_its_msaa_with_no_multisampled_window(stage, monkeypatch):
    """The trap: `_samples_of` says 0 of an `Offscreen`, so a first view that does not
    say `FRAME_SAMPLES` loses MSAA silently. Measured on the renderer's scene target
    and on the picture: the same look with the number forced to 0 has a
    single-sampled scene and other pixels on its edges."""
    def draw(samples):
        monkeypatch.setattr(app, "FRAME_SAMPLES", samples)
        rig = _rig(stage)
        slot = stage.output()
        for _ in range(2):
            app._draw_render(_proxy(rig), stage.ctx, rig.view, [slot], stage.root)
        out = _frame_px(stage), rig.renderer.scene.samples
        rig.close()
        return out

    px4, samples4 = draw(4)
    px0, samples0 = draw(0)
    assert (samples4, samples0) == (4, 0)
    # the same look, the same clock: only the edges MSAA softens differ, and they do
    differ = (np.abs(px4[..., :3].astype(int) - px0[..., :3].astype(int)).max(axis=2) > 0).sum()
    assert differ > 100


def _read_window(slot, into):
    """The window's back buffer straight after its presenter ran."""
    real = slot.presenter.present

    def present(ho, size, target=None):
        real(ho, size, target)
        ctx = slot.presenter.ctx
        raw = ctx.screen.read(viewport=(0, 0, *size), components=4)
        into.append(np.frombuffer(raw, dtype=np.uint8).reshape(size[1], size[0], 4).copy())
    slot.presenter.present = present


@pytest.mark.parametrize("bg", [1.0, 0.0, 0.35])
def test_the_window_shows_the_frame_byte_for_byte_opaque_and_overlay(stage, bg):
    """Overlay's real path: the renderer's ground see-through (`Output.bg_alpha`), a
    transparent window, `Presenter`. The window's back buffer is the frame target, alpha
    included, so what the compositor gets is what the renderer drew."""
    rig = _rig(stage)
    rig.renderer.bg_alpha = bg
    slot = stage.output(transparent=bg < 1.0)
    shots: list = []
    _read_window(slot, shots)
    for _ in range(2):
        app._draw_render(_proxy(rig), stage.ctx, rig.view, [slot], stage.root)
    frame = _frame_px(stage)
    rig.close()
    window = shots[-1]
    assert np.array_equal(frame[..., :3], window[..., :3])
    if slot.presenter.ctx.screen.bits.get("a", 0) > 0:      # (a window system may not give one)
        assert np.array_equal(frame[..., 3], window[..., 3])
    if bg < 1.0:
        assert frame[..., 3].min() < 255        # see-through somewhere
    else:
        assert frame[..., 3].min() == 255       # opaque means opaque
    assert frame[..., :3].max() > 8             # a picture, not a blank


def test_a_raising_draw_leaves_the_window_on_its_last_frame(stage):
    """A real raising draw: nothing swapped or presented, the frame target rebound, the
    root current. The window's front buffer is whatever it last showed: the real app's
    `tools/drive_sc3a.py` run (`SC3A_RAISE`) sees it on screen."""
    rig = _rig(stage)
    slot = stage.output()
    proxy = _proxy(rig)
    app._draw_render(proxy, stage.ctx, rig.view, [slot], stage.root)
    swaps: list = []
    real = glfw.swap_buffers
    app.glfw.swap_buffers = lambda w: (swaps.append(w), real(w))[1]
    try:
        boom = SimpleNamespace(bg_alpha=1.0, max_frame=None,
                               draw_outputs=lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        stage.root.pacer.end_frame()
        with pytest.raises(RuntimeError, match="boom"):
            app._draw_render(boom, stage.ctx, rig.view, [slot], stage.root)
    finally:
        app.glfw.swap_buffers = real
    rig.close()
    assert swaps == [] and not stage.root.pacer._swapped


def test_a_flip_a_dim_and_a_later_output_all_come_through(stage):
    """Output 1's flip and dim are baked in its frame target; a later output gets its
    own `Handoff` and its own switches."""
    rig = _rig(stage)
    one = stage.output(1, switches=Switches(flip_x=True, dim=0.5))
    two = stage.output(2)
    shots: dict = {1: [], 2: []}
    _read_window(one, shots[1])
    _read_window(two, shots[2])
    app._draw_render(_proxy(rig), stage.ctx, rig.view, [one, two], stage.root)
    app._draw_render(_proxy(rig), stage.ctx, rig.view, [one, two], stage.root)
    rig.close()
    a, b = shots[1][-1][..., :3], shots[2][-1][..., :3]
    assert a.shape == b.shape and b.max() > 8
    assert one.error == "" and two.error == ""
    # undimmed and unflipped, the second is brighter and not the first's mirror
    assert b.astype(float).mean() > a.astype(float).mean() * 1.5
    assert stage.root.pacer.owner == one.win


def test_the_picture_goes_on_when_every_display_is_gone(stage):
    """The point of SC3a: with output 1's window closed, the frame still draws, on the
    root's context at the last known size, nothing swaps, and a timer paces. A later
    output takes the pacing over, and a new window picks the picture up again. No GL
    error on any of it. (`Slot.win` going None is SC3b's to arrange at run time.)"""
    rig = _rig(stage)
    one, two = stage.output(1), stage.output(2)
    slots = [one, two]
    proxy = _proxy(rig)

    def frame():
        app._draw_render(proxy, stage.ctx, rig.view, slots, stage.root)
        from OpenGL.raw.GL.VERSION.GL_1_1 import glGetError
        return glGetError()

    frame()
    size = stage.root.size
    assert stage.root.pacer.owner == one.win
    frame()
    stage.close_output(one)
    assert frame() == 0
    assert stage.root.pacer.owner == two.win                # the handover
    assert stage.root.size == size and two.error == ""
    stage.close_output(two)
    before = _frame_px(stage)
    assert frame() == 0
    assert stage.root.pacer.owner is None and stage.root.size == size
    after = _frame_px(stage)
    assert after.shape == before.shape and after[..., :3].max() > 8
    # back: a new window on the same root shows the picture
    three = stage.output(1)
    slots[0] = three
    shots: list = []
    _read_window(three, shots)
    assert frame() == 0
    assert stage.root.pacer.owner == three.win and shots[-1][..., :3].max() > 8
    rig.close()


def test_a_hot_reload_with_the_root_current_keeps_the_picture(stage):
    """Audit V8, decided in SC3a: `frame` makes the root current before
    `reloader.poll()`, so the hooks' vertex arrays and framebuffers are the context's
    that draws them (tools/sc3a_spike.py v8 measures the wrong context). Here: a reload's
    hooks, the next frame the same picture."""
    rig = _rig(stage)
    off = Offscreen(stage.ctx)

    def draw():
        v = View(Switches(), SIZE, target=off.fit(SIZE), viewport=(0, 0, *SIZE), samples=4)
        rig.frame([v], SIZE, 1.0)
        assert v.error == ""
        return np.frombuffer(off.fbo.read(components=3), dtype=np.uint8)

    lit = (draw().reshape(SIZE[1], SIZE[0], 3).max(axis=2) > 8).sum()
    glfw.make_context_current(stage.root_win)
    rig.renderer.on_reload()
    rig.renderer.ghost.on_reload()
    after = (draw().reshape(SIZE[1], SIZE[0], 3).max(axis=2) > 8).sum()
    off.release()
    rig.close()
    assert lit > 100 and after > 0.5 * lit
