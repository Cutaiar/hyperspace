"""Draw-list replay (2026-11-02): the GRAPH canvas as `panel:graph`. The
filter rule over fake draw lists, the scissor and projection maths, the
tap's leased texture pool, and — on a GL context — a real imgui frame
replayed into the tap: the canvas's own window kept, its child (the side
pane), a tooltip and the foreground list left out; a frame held at rate 0
beside a live reader, across a canvas resize; a draw that fails
publishing nothing; an empty framebuffer drawing nothing; the viewport
put back."""

from __future__ import annotations

from types import SimpleNamespace as NS

import numpy as np
import pytest
from imgui_bundle import imgui

from hyperspace import outputs, replay

PAGE = "CONTROLS/##page_1F84F328"


def dl(name: str, *cmds):
    return NS(_owner_name=name, cmd_buffer=list(cmds))


# ---------------------------------------------------------------- the rule

def test_only_the_page_windows_own_list_is_kept():
    """The page window's list carries the backdrop, the editor's ground and
    grid, the nodes and the cables; everything laid over the canvas is
    another window's list — or the viewport's — and is dropped."""
    lists = [
        dl("##desk"), dl("CONTROLS"), dl("CONTROLS/##rail_2C8A99EF"),
        dl(PAGE),
        dl(PAGE + "/##graph.side_4C22007E"),      # the details side pane (a child)
        dl("##Popup_0a"), dl("##Menu_00"), dl("##Tooltip_00"),
        dl(replay.FOREGROUND), dl(replay.BACKGROUND),
    ]
    kept = replay.canvas_lists(lists, PAGE)
    assert [x._owner_name for x in kept] == [PAGE]
    assert replay.keep(PAGE, PAGE)
    for other in ("CONTROLS", PAGE + "/##graph.side_4C22007E", "##Tooltip_00",
                  replay.FOREGROUND, replay.BACKGROUND, ""):
        assert not replay.keep(other, PAGE)
    assert not replay.keep(PAGE, "") and replay.canvas_lists(lists, "") == []


def test_the_rule_costs_one_pass_over_the_lists():
    lists = [dl(f"w{i}") for i in range(50)] + [dl(PAGE)]
    seen: list[str] = []
    orig = replay.keep
    try:
        replay.keep = lambda o, p: seen.append(o) or orig(o, p)
        assert len(replay.canvas_lists(lists, PAGE)) == 1
    finally:
        replay.keep = orig
    assert len(seen) == len(lists)


# ---------------------------------------------------------------- the maths

def test_fit_size_caps_the_long_side_and_never_scales_up():
    assert outputs.fit_size((392.0, 565.0), (1.0, 1.0)) == (392, 565)
    assert outputs.fit_size((392.0, 565.0), (2.0, 2.0)) == (784, 1130)
    w, h = outputs.fit_size((1000.0, 700.0), (2.0, 2.0))
    assert w == 1280 and h == 896
    assert outputs.fit_size((0.0, 0.0), (2.0, 2.0)) == (1, 1)
    assert outputs.fit_size((5000.0, 10.0), (1.0, 1.0), cap=100) == (100, 1)


def test_scissor_moves_scales_and_clips_to_the_canvas():
    """A clip rect in the control window's framebuffer pixels becomes the
    tap's box: moved to the canvas's origin, scaled with the tap, rows
    counted from the bottom; a rect outside the canvas is None."""
    origin, scale, target = (100.0, 50.0), (2.0, 2.0), (400, 300)   # canvas 200×150 pt → 400×300
    k = (1.0, 1.0)
    # the whole page window's clip, wider than the canvas: the canvas itself
    assert replay.scissor((0, 0, 1000, 1000), origin, scale, k, target) == (0, 0, 400, 300)
    # a node's clip inside it: 20 pt in from the origin, 40×30 pt
    assert replay.scissor((240, 140, 320, 200), origin, scale, k, target) == (40, 200, 80, 60)
    # above the canvas (the head chips): nothing
    assert replay.scissor((200, 0, 600, 100), origin, scale, k, target) is None
    # the tap scaled by half: the box with it
    assert replay.scissor((240, 140, 320, 200), origin, scale, (0.5, 0.5), (200, 150)) == (20, 100, 40, 30)


def test_spans_cut_the_pane_decorations_out_of_a_command():
    """`omit` = (i0, i1), the indices the pane's decorations took on the
    page's list: a command before or after them is drawn whole, one
    around them in two parts, one inside them not at all."""
    assert replay.spans(0, 300, None) == [(0, 300)]
    assert replay.spans(0, 300, (0, 0)) == [(0, 300)]
    assert replay.spans(0, 300, (300, 420)) == [(0, 300)]        # before them
    assert replay.spans(420, 60, (300, 420)) == [(420, 60)]      # after them
    assert replay.spans(0, 480, (300, 420)) == [(0, 300), (420, 60)]
    assert replay.spans(300, 120, (300, 420)) == []              # the decorations alone
    assert replay.spans(240, 120, (300, 420)) == [(240, 60)]     # the part before
    assert replay.spans(360, 120, (300, 420)) == [(420, 60)]     # the part after
    assert replay.spans(0, 0, None) == []


def test_the_projection_maps_the_canvas_rect_onto_clip_space():
    m = list(replay.projection((100.0, 50.0), (200.0, 150.0)))
    def to_clip(x, y):
        return (m[0] * x + m[12], m[5] * y + m[13])
    assert to_clip(100.0, 50.0) == pytest.approx((-1.0, 1.0), abs=1e-6)      # top-left
    assert to_clip(300.0, 200.0) == pytest.approx((1.0, -1.0), abs=1e-6)     # bottom-right
    assert to_clip(200.0, 125.0) == pytest.approx((0.0, 0.0), abs=1e-6)


# ---------------------------------------------------------------- the tap

def test_grab_takes_the_wish_and_draws_nothing_without_the_page():
    """A wish never outlives its frame: `take` is read whether or not GRAPH
    drew, so a page left mid-frame leaves no stale draw next frame."""
    tap = outputs.CanvasTap()
    tap.want()
    assert replay.grab(tap, None, None, None) is False
    assert tap.wanted is False and tap.tex is None and tap.frame_no == 0
    assert replay.grab(tap, None, None, ((0, 0), (1, 1), (1, 1), PAGE)) is False   # not wanted
    assert replay.grab(None, None, None, ((0, 0), (1, 1), (1, 1), PAGE)) is False


def test_the_backend_still_has_what_draw_lists_reaches_for():
    """`draw_lists` uses the programmable renderer's private GL handles and
    a command's `tex_ref.get_tex_id()`; the module checks them on import
    and raises naming the missing ones, so a backend rename fails loudly
    here and not as every grab's `tap.error`."""
    assert replay.missing_backend_names() == []
    replay.check_backend()

    class Renamed:
        def __init__(self):
            self._shader_handle = self._vao_handle = self._vbo_handle = 0
            self._elements_handle = self._attrib_proj_mtx = 0     # `_attrib_location_tex` gone

    assert replay.missing_backend_names(Renamed) == ["Renamed._attrib_location_tex"]


def test_fit_makes_the_new_texture_before_letting_the_old_one_go():
    """`Offscreen.fit` at a new size: a make that fails leaves the old
    texture and framebuffer in place (a frame naming them stays whole)."""
    made = []

    class Ctx:
        fbo = None

        def texture(self, size, n):
            if size == (8, 8):
                raise RuntimeError("out of memory")
            t = NS(size=size, released=False)
            t.release = lambda t=t: setattr(t, "released", True)
            made.append(t)
            return t

        def framebuffer(self, color_attachments):
            f = NS(tex=color_attachments[0], released=False)
            f.release = lambda f=f: setattr(f, "released", True)
            return f

    off = outputs.Offscreen(Ctx())
    fbo = off.fit((4, 4))
    assert off.tex.size == (4, 4) and off.fit((4, 4)) is fbo
    with pytest.raises(RuntimeError):
        off.fit((8, 8))
    assert off.tex is made[0] and off.fbo is fbo and not made[0].released
    off.fit((2, 2))
    assert made[0].released and fbo.released and off.tex.size == (2, 2)


def test_a_failing_grab_is_the_taps_error_never_a_raise():
    tap = outputs.CanvasTap()
    tap.want()
    bad = NS(cmd_lists=[dl(PAGE)], display_size=(400, 300), framebuffer_scale=(2, 2))
    assert replay.grab(tap, None, bad, ((0, 0), (10, 10), (1, 1), PAGE)) is False
    assert tap.error and tap.wanted is False and tap.frame_no == 0


def test_an_empty_framebuffer_draws_nothing_and_publishes_nothing():
    """The window minimised: the backend's `render` returns before
    `scale_clip_rects` when the framebuffer is 0 wide or high, so the
    clip rects are still in points; `grab` bails out the same way — the
    wish taken, no error, no frame."""
    assert replay.framebuffer_size(NS(display_size=(400, 300), framebuffer_scale=(2, 2))) == (800, 600)
    assert replay.framebuffer_size(NS(display_size=(0, 300), framebuffer_scale=(2, 2))) == (0, 600)
    assert replay.framebuffer_size(NS(display_size=(400, 0.4), framebuffer_scale=(1, 1))) == (400, 0)
    tap = outputs.CanvasTap()
    for ds in ((0, 300), (400, 0)):
        tap.want()
        dd = NS(cmd_lists=[dl(PAGE)], display_size=ds, framebuffer_scale=(2, 2))
        assert replay.grab(tap, None, dd, ((0, 0), (10, 10), (2, 2), PAGE)) is False
        assert tap.error == "" and tap.wanted is False and tap.frame_no == 0 and tap.tex is None


# ---------------------------------------------------------------- on GL

def _gl():
    moderngl = pytest.importorskip("moderngl")
    try:
        return moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")


def _rgba(tex) -> np.ndarray:
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)[::-1]   # rows top first


RED, GREEN, BLUE, WHITE = (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 255, 255)
CYAN = (0, 255, 255, 255)
ORIGIN, SIZE = (60.0, 100.0), (200.0, 120.0)        # the canvas, points
SCALE = (2.0, 2.0)


class Scene:
    """A control window of 400×300 points at 2× on a standalone context:
    the backend, a screen texture and a tap. `shoot(colour)` runs one imgui
    frame — a page window with the canvas in `colour` and a green head
    above it, the side pane (a bordered child, cyan ground, blue content)
    over the canvas, a tooltip and a white foreground rect — renders it to
    the screen as the app's loop does and grabs it into the tap; `canvas`
    is the rect it draws the canvas in (points), changed to test a
    resize."""

    def __init__(self):
        from imgui_bundle.python_backends.opengl_backend_programmable import (
            ProgrammablePipelineRenderer,
        )

        self.gl = _gl()
        self.ictx = imgui.create_context()
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(400, 300)
        io.display_framebuffer_scale = imgui.ImVec2(*SCALE)
        io.fonts.add_font_default()
        self.screen = self.gl.framebuffer(color_attachments=[self.gl.texture((800, 600), 4)])
        self.screen.use()
        self.impl = ProgrammablePipelineRenderer()
        self.tap = outputs.CanvasTap(self.gl)
        self.canvas = (ORIGIN, SIZE)
        self.page = ""
        self.omit = (0, 0)

    def shoot(self, colour=(1, 0, 0, 1), *, want: bool = True, grab=None, display=None) -> bool:
        origin, size = self.canvas
        if display is not None:                   # the window minimised: a 0×0 display
            imgui.get_io().display_size = imgui.ImVec2(*display)
        imgui.new_frame()
        imgui.set_next_window_pos(imgui.ImVec2(50, 40))
        imgui.set_next_window_size(imgui.ImVec2(300, 220))
        imgui.begin("PAGE", None, imgui.WindowFlags_.no_decoration)
        self.page = imgui.internal.get_current_window().name
        d = imgui.get_window_draw_list()
        d.add_rect_filled(imgui.ImVec2(60, 50), imgui.ImVec2(260, 90), imgui.get_color_u32(imgui.ImVec4(0, 1, 0, 1)))
        d.add_rect_filled(imgui.ImVec2(*origin), imgui.ImVec2(origin[0] + size[0], origin[1] + size[1]),
                          imgui.get_color_u32(imgui.ImVec4(*colour)))
        imgui.set_cursor_screen_pos(imgui.ImVec2(160, 120))
        # the side pane as the GRAPH page draws it: a bordered child with a
        # ground — decorations imgui puts on the page's list — noted
        imgui.push_style_color(imgui.Col_.child_bg, imgui.ImVec4(0, 1, 1, 1))
        i0 = d.idx_buffer.size()
        imgui.begin_child("##side", imgui.ImVec2(80, 80), imgui.ChildFlags_.borders)
        self.omit = (i0, d.idx_buffer.size())
        imgui.get_window_draw_list().add_rect_filled(imgui.ImVec2(170, 130), imgui.ImVec2(230, 190),
                                                     imgui.get_color_u32(imgui.ImVec4(0, 0, 1, 1)))
        imgui.end_child()
        imgui.pop_style_color()
        imgui.begin_tooltip()
        imgui.text("a tooltip over the canvas")
        imgui.end_tooltip()
        imgui.end()
        imgui.get_foreground_draw_list().add_rect_filled(
            imgui.ImVec2(70, 110), imgui.ImVec2(100, 130), imgui.get_color_u32(imgui.ImVec4(1, 1, 1, 1)))
        imgui.render()
        dd = imgui.get_draw_data()
        self.screen.use()
        self.screen.clear(0, 0, 0, 1)
        self.impl.render(dd)                 # the screen, every list — as the app's loop does
        if want:
            self.tap.want()
        try:
            return (grab or replay.grab)(self.tap, self.impl, dd, (origin, size, SCALE, self.page, self.omit))
        finally:
            if display is not None:
                imgui.get_io().display_size = imgui.ImVec2(400, 300)

    def close(self) -> None:
        self.tap.close()
        self.impl.shutdown()
        imgui.destroy_context(self.ictx)
        self.screen.release()
        self.gl.release()


@pytest.fixture
def scene():
    sc = Scene()
    try:
        yield sc
    finally:
        sc.close()


def _hold(src_tap):
    """A channel at rate 0 in shape: a frame naming the tap's texture with
    the lease a `PanelSource` would put on it (`MediaFrame.lease`)."""
    from hyperspace.media.frame import MediaFrame

    lease = src_tap.lease()
    return MediaFrame(None, src_tap.at, src_tap.frame_no, texture=lease.texture,
                      tex_size=lease.size, tex_gen=lease.generation, lease=lease)


def test_the_canvas_is_replayed_into_the_tap_without_what_lies_over_it(scene):
    """A real imgui frame on a GL context: a page window with a red canvas
    and a green head above it, a child window (the side pane) blue over
    the canvas, a tooltip and a white foreground rect over it too. The
    screen shows all of them; the tap shows the red canvas alone, opaque,
    at the canvas's framebuffer size, and its red matches the screen's."""
    for _ in range(2):                                # a frame to settle, one to shoot
        assert scene.shoot() is True, scene.tap.error
    tap, omit = scene.tap, scene.omit
    assert scene.page == "PAGE" and tap.error == "" and tap.frame_no == 2 and omit[1] > omit[0]
    assert tap.size == (400, 240)
    pic, shown = _rgba(tap.tex), _rgba(scene.screen.color_attachments[0])
    # the screen has everything: red canvas, the side pane (cyan ground, blue
    # content), white inset, green head
    assert tuple(shown[2 * 120, 2 * 85]) == WHITE and tuple(shown[2 * 160, 2 * 200]) == BLUE
    assert tuple(shown[2 * 125, 2 * 165]) == CYAN and tuple(shown[2 * 70, 2 * 100]) == GREEN
    # the tap: the canvas's red where the side pane and the inset lay, nothing else
    canvas_px = (2 * (200 - 60), 2 * (160 - 100))                # the side pane's spot, tap px
    assert tuple(pic[canvas_px[1], canvas_px[0]]) == RED
    assert tuple(pic[2 * (125 - 100), 2 * (165 - 60)]) == RED  # under the pane's ground
    assert tuple(pic[2 * 20, 2 * 25]) == RED                       # under the white inset
    assert tuple(pic[120, 200]) == RED and tuple(pic[0, 0]) == RED and tuple(pic[239, 399]) == RED
    colours = {tuple(c) for c in np.unique(pic.reshape(-1, 4), axis=0)}
    assert colours == {RED}, colours                                # no green, blue or white
    assert pic[..., 3].min() == 255
    # with every reader live the pool is two textures written in turn
    held = tap.tex
    assert scene.shoot() is True and tap.tex is not held and tap.frame_no == 3
    assert tap.textures == 2 and tap.ctx.fbo is scene.screen       # the screen bound again


def test_a_frame_held_at_rate_0_keeps_its_pixels_beside_a_live_reader(scene):
    """Channel A at rate 0 holds the red frame; channel B reads on. Three
    more grabs (blue) later A's texture still reads red everywhere — no
    grab writes a leased texture — and the pool grew by one, no more; A
    letting go frees it, and the pool shrinks back to two."""
    assert scene.shoot() is True, scene.tap.error
    tap = scene.tap
    a = _hold(tap)                                        # channel A freezes on frame 1
    red = _rgba(tap.tex)
    assert tuple(red[120, 200]) == RED and a.texture == tap.tex.glo
    for _ in range(3):
        assert scene.shoot((0, 0, 1, 1)) is True, tap.error   # channel B's grabs
        assert tap.tex.glo != a.texture
        assert tuple(_rgba(tap.tex)[120, 200]) == BLUE
    assert tap.frame_no == 4 and tap.textures == 3
    held = [s for s in tap._slots if s.off.tex.glo == a.texture]
    assert len(held) == 1 and held[0].leases == 1
    assert np.array_equal(_rgba(held[0].off.tex), red)       # A's bytes unchanged
    del a                                                  # A's rate back up
    tap._reap()                                            # (the next begin's first step)
    assert held[0].leases == 0
    for _ in range(2):
        assert scene.shoot((0, 0, 1, 1)) is True, tap.error
    assert tap.textures == 2                               # the spare let go


def test_a_canvas_resize_leaves_a_held_frame_whole(scene):
    """A frame held at rate 0, then the canvas changes size: the two grabs
    after it go into textures of the new size, the held frame's texture is
    neither freed nor resized and still reads back its red at its size."""
    assert scene.shoot() is True, scene.tap.error
    tap = scene.tap
    a = _hold(tap)
    red = _rgba(tap.tex)
    assert a.tex_size == (400, 240)
    scene.canvas = ((60.0, 100.0), (100.0, 60.0))        # the pane dragged: a smaller canvas
    for _ in range(2):
        assert scene.shoot((0, 0, 1, 1)) is True, tap.error
        assert tap.size == (200, 120) and tap.tex.glo != a.texture
    [held] = [s for s in tap._slots if s.off.tex.glo == a.texture]
    assert held.off.tex.size == (400, 240) and np.array_equal(_rgba(held.off.tex), red)
    assert tap.textures == 3
    # the textures made anew carry a later generation than the held one,
    # whatever name GL gave them (a reused name is a different object)
    assert tap.lease().generation > a.tex_gen == a.lease.generation
    assert tap.allocations == 3                            # the first, then two at the new size (the second slot was never made before)


def test_a_frame_dropped_on_another_thread_frees_its_texture_on_the_next_grab(scene):
    """Leases are dropped wherever the frame is (the channels' closer, a
    GC run): `__del__` hands the slot back on a deque and the frame thread
    counts it off in the next `begin`. A frame let go on another thread
    while grabs run: its texture reads its colour until then, is free
    after, and the pool is back to two with every lease accounted for."""
    import threading

    assert scene.shoot() is True, scene.tap.error
    tap = scene.tap
    box = [_hold(tap)]
    name = box[0].texture
    red = _rgba(tap.tex)
    dropped = threading.Event()

    def drop():
        box.clear()                                        # the frame's last reference
        dropped.set()

    for _ in range(3):
        assert scene.shoot((0, 0, 1, 1)) is True, tap.error
    [held] = [s for s in tap._slots if s.off.tex.glo == name]
    assert np.array_equal(_rgba(held.off.tex), red) and held.leases == 1
    t = threading.Thread(target=drop)
    t.start()
    t.join()
    assert dropped.is_set() and held.leases == 1           # not counted off yet: the deque has it
    assert tap._returns and tap._returns[0] is held
    for _ in range(3):
        assert scene.shoot((0, 0, 1, 1)) is True, tap.error
    assert held.leases == 0 and not tap._returns
    assert tap.textures == 2
    assert sum(s.leases for s in tap._slots) == 0          # no frame in hand: nothing leased


def test_a_begin_that_fails_is_aborted_too(scene, monkeypatch):
    """`fit` raising inside `begin` (a texture that cannot be made): the
    grab is aborted — no slot half-begun, nothing published, the screen
    bound — and the next grab is whole."""
    assert scene.shoot() is True, scene.tap.error
    tap = scene.tap
    good, n = tap.tex, tap.frame_no
    free = [s for s in tap._slots if s is not tap._cur]
    monkeypatch.setattr(free[0].off, "fit", lambda size: (_ for _ in ()).throw(RuntimeError("no memory")))
    assert scene.shoot((0, 0, 1, 1)) is False
    assert tap.error == "RuntimeError: no memory"
    assert tap._next is None and tap._prev is None and tap.ctx.fbo is scene.screen
    assert tap.tex is good and tap.frame_no == n
    assert tap.lease().texture == good.glo                 # a frame named now is whole
    monkeypatch.undo()
    assert scene.shoot((0, 0, 1, 1)) is True and tap.frame_no == n + 1


def test_a_minimised_window_grabs_nothing_through_the_real_backend(scene):
    """`impl.render` returns before `scale_clip_rects` on a 0×0 display;
    `grab` bails the same way: the wish taken, no error, no frame."""
    assert scene.shoot() is True, scene.tap.error
    tap = scene.tap
    n = tap.frame_no
    assert scene.shoot((0, 0, 1, 1), display=(0, 0)) is False
    assert tap.error == "" and tap.wanted is False and tap.frame_no == n
    assert scene.shoot((0, 0, 1, 1)) is True and tap.frame_no == n + 1


def test_a_draw_that_fails_publishes_nothing(scene, monkeypatch):
    """A draw that raises after its first command: the half-drawn texture
    is not published — `tex`, `frame_no` and `at` stand as the last good
    grab left them, the error is the tap's — and the screen is bound
    again; the grab after it is whole."""
    assert scene.shoot() is True, scene.tap.error
    tap = scene.tap
    good, n, at = tap.tex, tap.frame_no, tap.at
    real = replay.scissor
    calls = []

    def torn(*args):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError("torn")
        return real(*args)

    monkeypatch.setattr(replay, "scissor", torn)
    assert scene.shoot((0, 0, 1, 1)) is False
    assert len(calls) == 2 and tap.error == "RuntimeError: torn"
    assert tap.tex is good and tap.frame_no == n and tap.at == at
    assert tuple(_rgba(tap.tex)[120, 200]) == RED
    assert tap.ctx.fbo is scene.screen and tap._next is None
    monkeypatch.setattr(replay, "scissor", real)
    assert scene.shoot((0, 0, 1, 1)) is True and tap.frame_no == n + 1 and tap.error == ""
    assert tuple(_rgba(tap.tex)[120, 200]) == BLUE


def test_the_viewport_is_put_back_after_a_grab(scene):
    """`end` rebinds the screen through moderngl, which reapplies the
    viewport it noted when the framebuffer was made — not the window's
    size now — so `grab` restores the viewport it found."""
    import OpenGL.GL as gl

    def resized_then_grab(*args):
        gl.glViewport(3, 5, 777, 555)             # the window since resized: what the loop has set
        return replay.grab(*args)

    assert scene.shoot() is True, scene.tap.error
    assert scene.shoot(grab=resized_then_grab) is True, scene.tap.error
    assert [int(v) for v in gl.glGetIntegerv(gl.GL_VIEWPORT)] == [3, 5, 777, 555]
    assert scene.tap.ctx.fbo is scene.screen
