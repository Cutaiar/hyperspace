"""The control window's GRAPH canvas as a media source (2026-11-02):
`panel:graph`.

The picture is the canvas the GRAPH page draws — output 1 behind it, the
editor's faded ground, the grid, the nodes and the cables — replayed from
the canvas's own draw lists into a texture of the control window's
context (`outputs.CanvasTap`, drawn by `replay.grab` at the end of the
frame). The control context shares the render context's share group, so
the texture is a GPU frame here (`MediaFrame` with `texture`, `TEX_2D`),
as a Syphon feed's is, and never touches the CPU.

The source is a built-in: the app's resolver answers `panel:graph` with
the one `PanelSource` it made (so `channels._stale` keeps it), and the
MEDIA page lists it among the live feeds without a `[[devices]]` entry.
It is untimed, so a channel at rate 0 holds the frame it showed
(`channels._freeze`). Each frame carries a lease on its texture
(`outputs.Lease`, `MediaFrame.lease`): while the channel holds the frame
no grab writes that texture and no resize frees it, so the hold is exact
however many other readers go on grabbing beside it, and the texture is
free again the moment the channel lets the frame go.

`gl_poll` runs only on the frame thread (the renderer's `MediaTextures`
reads a channel): it asks the tap to draw the canvas at the end of this
frame (`want`) and hands back the texture the tap wrote last — one frame
of latency, which round a loop (the channel on the backdrop behind the
canvas it pictures) is the intended echo. Off the GRAPH page nothing is
drawn: the last frame holds `live.HOLD_S`, then the source reads None
(black) and says `off page` (the page says it is not drawing: not
`lost`, which is for a page that draws and a tap that gets nothing — a
minimised window) — the owner's default — and is `ready` again on the
first frame the page is back."""

from __future__ import annotations

import time

from .frame import TEX_2D, MediaFrame
from .live import SharedSource

GRAPH = "panel:graph"
OFF_PAGE = "off page"    # the GRAPH page is not on screen: nothing to draw


class PanelSource(SharedSource):
    """`panel:graph` as a `media.source.Source`, untimed, shared as a live
    feed is (`SharedSource`: holders, the newest frame, the status). `tap`
    is the `outputs.CanvasTap` (duck-typed: `want()`, `lease()` with
    `texture`, `size` and `generation`, `frame_no`, `at` on `clock`'s
    scale); `on_page` answers whether the GRAPH page is drawing its
    canvas now — the panel's own fact (`Panel.canvas_px is not None`),
    read from it, so the status has one owner."""

    def __init__(self, tap, *, on_page=None, clock=time.monotonic):
        super().__init__(GRAPH, kind="panel", clock=clock)
        self.tap = tap
        self.on_page = on_page if on_page is not None else (lambda: True)

    def _idle(self) -> str:
        """`off page` while GRAPH is not on screen (no frame can come, so
        not `fetching`), else a live feed's words."""
        if self.tap is not None and not self.on_page():
            return OFF_PAGE
        return super()._idle()

    def gl_poll(self) -> MediaFrame | None:
        """The frame thread: ask for the canvas at this frame's end, and
        read what the tap wrote last (a frame per grab, by `frame_no`),
        holding its texture through the frame's lease."""
        tap = self.tap
        if tap is None:
            return None
        tap.want()
        n = int(getattr(tap, "frame_no", 0))
        f = self._latest.get()
        if n and (f is None or f.frame != n):
            lease = tap.lease()
            if lease is not None:
                size = tuple(int(v) for v in lease.size)
                self._publish(MediaFrame(None, float(tap.at), n, texture=int(lease.texture),
                                         tex_size=(size[0], size[1]), tex_target=TEX_2D,
                                         tex_gen=int(getattr(lease, "generation", 0)),
                                         lease=lease))
        return self.latest()
