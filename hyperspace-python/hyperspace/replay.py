"""Draw-list replay (2026-11-02): the GRAPH canvas drawn again, from its
own draw lists, into the control window's `outputs.CanvasTap` — what
`panel:graph` (`media.panel`) hands a channel.

The owner's ask: the node editor's view — output 1 behind it, the faded
ground, the grid, the nodes and the cables — as a picture a media channel
can pick, with what is laid over the canvas filtered out. The filter is
by draw list, not by pixel: imgui keeps one `ImDrawList` per window, each
named after its window (`ImDrawList._owner_name`), and on the GRAPH page
the backdrop, the editor's ground and grid and every node and cable all
land on the page window's own list (the node editor draws into the
current window's list; it opens no child). So:

- **kept**: the page window's list — `CONTROLS/##page_…`, the name the
  page records in `Panel.canvas_px` — projected so the canvas rect fills
  the tap, which leaves the head chips above the canvas outside the
  picture;
- **dropped**: everything else — the details side pane (a child window,
  `…/##graph.side_…`), every popup, menu and tooltip (their own windows),
  the desk and the rail, and the viewport's background and foreground
  lists (the held PROJECTOR inset is on the foreground list);
- **cut out**: the side pane's decorations — its ground, border and
  scrollbar — which imgui draws on the *parent's* list inside
  `begin_child` (one draw call fewer, since 1.71). The page notes the
  indices of its list they took (`omit`, the fifth of `Panel.canvas_px`)
  and `spans` leaves them out of each command's draw.

`keep` is that rule, pure; `canvas_lists` applies it, O(lists), once a
frame. `draw_lists` is the GL backend's own replay (the same program, VAO
and buffers, the same state save and restore) with the projection moved
to the canvas's origin and each command's scissor moved and scaled with
it; `grab` runs after `impl.render(draw_data)` — the clip rects are in
framebuffer pixels by then (`scale_clip_rects`), and the font atlas is
up — on a frame the tap was wanted and the GRAPH page drew."""

from __future__ import annotations

import ctypes
import time

import OpenGL.GL as gl
from imgui_bundle import imgui
from imgui_bundle.python_backends.opengl_base_backend import (
    get_common_gl_state,
    restore_common_gl_state,
)

from .outputs import fit_size

FOREGROUND, BACKGROUND = "##Foreground", "##Background"


def keep(owner: str, page: str) -> bool:
    """Whether the draw list a window `owner` owns is part of the canvas's
    picture: only the page window's own list (`page`, as the GRAPH page
    recorded it). A child of it (the side pane), a popup, a menu, a tooltip,
    any other window and the viewport's background and foreground lists
    are not."""
    return bool(page) and owner == page


def canvas_lists(cmd_lists, page: str) -> list:
    """The draw lists of `cmd_lists` (an `ImDrawData`'s) the picture keeps."""
    return [dl for dl in cmd_lists if keep(dl._owner_name, page)]


def scissor(clip, origin: tuple[float, float], scale: tuple[float, float],
            k: tuple[float, float], target: tuple[int, int]) -> tuple[int, int, int, int] | None:
    """A command's clip rect (x0, y0, x1, y1, framebuffer pixels of the
    control window) as the tap's `glScissor` box (x, y, w, h, GL's rows:
    y up from the bottom), or None when nothing of it lies in the canvas.
    `origin` is the canvas's top-left in points, `scale` the framebuffer
    scale, `k` tap pixels per framebuffer pixel, `target` the tap's size."""
    ox, oy = origin[0] * scale[0], origin[1] * scale[1]
    x0 = max((clip[0] - ox) * k[0], 0.0)
    y0 = max((clip[1] - oy) * k[1], 0.0)
    x1 = min((clip[2] - ox) * k[0], float(target[0]))
    y1 = min((clip[3] - oy) * k[1], float(target[1]))
    if x1 <= x0 or y1 <= y0:
        return None
    return (int(x0), int(target[1] - y1), int(x1 - x0), int(y1 - y0))


def spans(start: int, count: int, omit: tuple[int, int] | None) -> list[tuple[int, int]]:
    """A command's indices `[start, start + count)` as the (offset, count)
    spans to draw with `omit` = (i0, i1) — the pane's decorations — cut
    out: the whole command when they do not meet, else the part before
    and the part after (either may be empty and is left out)."""
    end = start + count
    if omit is None or omit[1] <= omit[0] or omit[1] <= start or omit[0] >= end:
        return [(start, count)] if count > 0 else []
    out = []
    if omit[0] > start:
        out.append((start, omit[0] - start))
    if omit[1] < end:
        out.append((omit[1], end - omit[1]))
    return out


def projection(origin: tuple[float, float], size: tuple[float, float]):
    """imgui's orthographic matrix (column-major, as the backend lays it
    out) with the canvas rect — `origin`, `size`, points — mapped onto the
    whole target: y down, as imgui draws."""
    ox, oy = float(origin[0]), float(origin[1])
    w, h = max(float(size[0]), 1e-6), max(float(size[1]), 1e-6)
    return (ctypes.c_float * 16)(
        2.0 / w, 0.0, 0.0, 0.0,
        0.0, -2.0 / h, 0.0, 0.0,
        0.0, 0.0, -1.0, 0.0,
        -(2.0 * ox / w + 1.0), 2.0 * oy / h + 1.0, 0.0, 1.0,
    )


def draw_lists(impl, lists, origin: tuple[float, float], size: tuple[float, float],
               scale: tuple[float, float], target: tuple[int, int],
               omit: tuple[int, int] | None = None) -> int:
    """Replay `lists` (draw lists whose clip rects are already in the
    control window's framebuffer pixels) with the backend `impl`'s program
    into the bound framebuffer of `target` size, the canvas rect at
    `origin` / `size` points filling it; the indices `omit` (the pane's
    decorations, `spans`) left out. GL state is saved and restored as the
    backend's own `render` does. Returns the draws made."""
    tw, th = int(target[0]), int(target[1])
    if tw <= 0 or th <= 0:
        return 0
    k = (tw / max(size[0] * scale[0], 1e-6), th / max(size[1] * scale[1], 1e-6))
    common = get_common_gl_state()
    last_program = gl.glGetIntegerv(gl.GL_CURRENT_PROGRAM)
    last_active_texture = gl.glGetIntegerv(gl.GL_ACTIVE_TEXTURE)
    last_array_buffer = gl.glGetIntegerv(gl.GL_ARRAY_BUFFER_BINDING)
    last_element_array_buffer = gl.glGetIntegerv(gl.GL_ELEMENT_ARRAY_BUFFER_BINDING)
    last_vertex_array = gl.glGetIntegerv(gl.GL_VERTEX_ARRAY_BINDING)
    drawn = 0
    try:
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendEquation(gl.GL_FUNC_ADD)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        gl.glViewport(0, 0, tw, th)
        gl.glUseProgram(impl._shader_handle)
        gl.glUniform1i(impl._attrib_location_tex, 0)
        gl.glUniformMatrix4fv(impl._attrib_proj_mtx, 1, gl.GL_FALSE, projection(origin, size))
        gl.glBindVertexArray(impl._vao_handle)
        gltype = gl.GL_UNSIGNED_SHORT if imgui.INDEX_SIZE == 2 else gl.GL_UNSIGNED_INT
        for commands in lists:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, impl._vbo_handle)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, commands.vtx_buffer.size() * imgui.VERTEX_SIZE,
                            ctypes.c_void_p(commands.vtx_buffer.data_address()), gl.GL_STREAM_DRAW)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, impl._elements_handle)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, commands.idx_buffer.size() * imgui.INDEX_SIZE,
                            ctypes.c_void_p(commands.idx_buffer.data_address()), gl.GL_STREAM_DRAW)
            for command in commands.cmd_buffer:
                box = scissor(command.clip_rect, origin, scale, k, (tw, th))
                if box is None or not command.elem_count:
                    continue
                gl.glBindTexture(gl.GL_TEXTURE_2D, command.tex_ref.get_tex_id())
                gl.glScissor(*box)
                for off, cnt in spans(command.idx_offset, command.elem_count, omit):
                    gl.glDrawElements(gl.GL_TRIANGLES, cnt, gltype,
                                      ctypes.c_void_p(off * imgui.INDEX_SIZE))
                    drawn += 1
    finally:
        restore_common_gl_state(common)
        gl.glUseProgram(last_program)
        gl.glActiveTexture(last_active_texture)
        gl.glBindVertexArray(last_vertex_array)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, last_array_buffer)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, last_element_array_buffer)
    return drawn


def framebuffer_size(draw_data) -> tuple[int, int]:
    """The control window's framebuffer size as the backend computes it
    (`display_size` × `framebuffer_scale`, truncated): (0, 0) for a
    minimised or zero-sized window, on which `impl.render` returns before
    `scale_clip_rects`, so the lists' clip rects are still in points."""
    ds, fs = draw_data.display_size, draw_data.framebuffer_scale
    return (int(ds[0] * fs[0]), int(ds[1] * fs[1]))


def grab(tap, impl, draw_data, canvas_px, *, clock=time.monotonic) -> bool:
    """After `impl.render(draw_data)`, before the swap: when the tap was
    wanted this frame and the GRAPH page drew (`canvas_px` is its
    `(origin, size, scale, page[, omit])` — points, points, framebuffer
    scale, the page window's name, the pane's decorations' index range),
    draw the canvas's lists into the tap and flush, so the render context
    sees the texture next frame. True when drawn. The tap's `take` is read
    whether or not the page drew, so a wish never outlives its frame, and
    its `on_page` says whether the page drew (the source's `off page`).
    An empty framebuffer (the window minimised: the backend skipped the
    frame and its clip rects are unscaled) draws nothing. A draw that
    fails is `abort`ed — nothing published, the last frame stands — and
    is the tap's `error`, never the loop's. The viewport is put back as
    it was: `end` rebinds the screen through moderngl, which reapplies
    the viewport it noted at creation, not the window's size now."""
    if tap is None:
        return False
    tap.on_page = canvas_px is not None
    if not tap.take() or canvas_px is None:
        return False
    origin, size, scale, page = canvas_px[:4]
    omit = canvas_px[4] if len(canvas_px) > 4 else None
    try:
        fb = framebuffer_size(draw_data)
        if fb[0] <= 0 or fb[1] <= 0:
            return False
        lists = canvas_lists(draw_data.cmd_lists, page)
        target = fit_size(size, scale)
        if getattr(tap, "ctx", None) is None:
            raise RuntimeError("CanvasTap has no GL context")    # before any GL call: none is current
        viewport = [int(v) for v in gl.glGetIntegerv(gl.GL_VIEWPORT)]
        tap.begin(target)
        try:
            try:
                draw_lists(impl, lists, origin, size, scale, target, omit)
            except Exception:
                tap.abort()
                raise
            tap.end(clock())
        finally:
            gl.glViewport(*viewport)
        gl.glFlush()
        tap.error = ""
    except Exception as e:  # noqa: BLE001 — a picture must not cost the panel its frame
        tap.error = f"{type(e).__name__}: {e}"
        return False
    return True
