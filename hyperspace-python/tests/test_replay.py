"""Draw-list replay (2026-11-02): the GRAPH canvas as `panel:graph`. The
filter rule over fake draw lists, the scissor and projection maths, the
tap's double buffer, and — on a GL context — a real imgui frame replayed
into the tap: the canvas's own window kept, its child (the side pane), a
tooltip and the foreground list left out."""

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


def test_a_failing_grab_is_the_taps_error_never_a_raise():
    tap = outputs.CanvasTap()
    tap.want()
    bad = NS(cmd_lists=[dl(PAGE)])
    assert replay.grab(tap, None, bad, ((0, 0), (10, 10), (1, 1), PAGE)) is False
    assert tap.error and tap.wanted is False


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


def test_the_canvas_is_replayed_into_the_tap_without_what_lies_over_it():
    """A real imgui frame on a GL context: a page window with a red canvas
    and a green head above it, a child window (the side pane) blue over
    the canvas, a tooltip and a white foreground rect over it too. The
    screen shows all of them; the tap shows the red canvas alone, opaque,
    at the canvas's framebuffer size, and its red matches the screen's."""
    from imgui_bundle.python_backends.opengl_backend_programmable import (
        ProgrammablePipelineRenderer,
    )

    gl = _gl()
    ictx = imgui.create_context()
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(400, 300)
    io.display_framebuffer_scale = imgui.ImVec2(2, 2)
    io.fonts.add_font_default()
    screen = gl.framebuffer(color_attachments=[gl.texture((800, 600), 4)])
    screen.use()
    impl = ProgrammablePipelineRenderer()
    tap = outputs.CanvasTap(gl)
    origin, size = (60.0, 100.0), (200.0, 120.0)        # the canvas, points
    try:
        page = ""
        for _ in range(2):                                # a frame to settle, one to shoot
            imgui.new_frame()
            imgui.set_next_window_pos(imgui.ImVec2(50, 40))
            imgui.set_next_window_size(imgui.ImVec2(300, 220))
            imgui.begin("PAGE", None, imgui.WindowFlags_.no_decoration)
            page = imgui.internal.get_current_window().name
            d = imgui.get_window_draw_list()
            d.add_rect_filled(imgui.ImVec2(60, 50), imgui.ImVec2(260, 90), imgui.get_color_u32(imgui.ImVec4(0, 1, 0, 1)))
            d.add_rect_filled(imgui.ImVec2(*origin), imgui.ImVec2(origin[0] + size[0], origin[1] + size[1]),
                              imgui.get_color_u32(imgui.ImVec4(1, 0, 0, 1)))
            imgui.set_cursor_screen_pos(imgui.ImVec2(160, 120))
            # the side pane as the GRAPH page draws it: a bordered child with
            # a ground — decorations imgui puts on the page's list — noted
            imgui.push_style_color(imgui.Col_.child_bg, imgui.ImVec4(0, 1, 1, 1))
            i0 = d.idx_buffer.size()
            imgui.begin_child("##side", imgui.ImVec2(80, 80), imgui.ChildFlags_.borders)
            omit = (i0, d.idx_buffer.size())
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
            screen.use()
            screen.clear(0, 0, 0, 1)
            impl.render(dd)                 # the screen, every list — as the app's loop does
            tap.want()
            assert replay.grab(tap, impl, dd, (origin, size, (2.0, 2.0), page, omit)) is True, tap.error
        assert page == "PAGE" and tap.error == "" and tap.frame_no == 2 and omit[1] > omit[0]
        assert tap.size == (400, 240)
        pic, shown = _rgba(tap.tex), _rgba(screen.color_attachments[0])
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
        # a channel at rate 0 holds the texture written before: the next grab
        # writes the other one
        held = tap.tex
        imgui.new_frame()
        imgui.render()
        tap.want()
        assert replay.grab(tap, impl, imgui.get_draw_data(), (origin, size, (2.0, 2.0), page, (0, 0))) is True
        assert tap.tex is not held and tap.frame_no == 3
        assert tuple(_rgba(held)[120, 200]) == RED
    finally:
        tap.close()
        impl.shutdown()
        imgui.destroy_context(ictx)
        screen.release()
        gl.release()
