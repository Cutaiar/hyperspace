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
(`channels._freeze`); a frozen channel stops polling, and a tap nobody
polled is not drawn, so the texture it holds stays as it was.

`gl_poll` runs only on the frame thread (the renderer's `MediaTextures`
reads a channel): it asks the tap to draw the canvas at the end of this
frame (`want`) and hands back the texture the tap wrote last — one frame
of latency, which round a loop (the channel on the backdrop behind the
canvas it pictures) is the intended echo. Off the GRAPH page nothing is
drawn: the last frame holds `live.HOLD_S`, then the source reads None
(black) and says `lost` — the owner's default — and is `ready` again on
the first frame the page is back."""

from __future__ import annotations

import time

from .frame import TEX_2D, MediaFrame
from .live import HOLD_S
from .source import FETCHING, LOST, READY

GRAPH = "panel:graph"


class PanelSource:
    """`panel:graph` as a `media.source.Source`, untimed. `tap` is the
    `outputs.CanvasTap` (duck-typed: `want()`, `tex` with a `glo`, `size`,
    `frame_no`, `at` on `clock`'s scale). Holders are counted, as a live
    source's are, so the one object serves every channel that lists it."""

    sid = GRAPH
    kind = "panel"
    timed = False
    duration = 0.0

    def __init__(self, tap, *, clock=time.monotonic):
        self.tap = tap
        self.clock = clock
        self._frame: MediaFrame | None = None
        self._holders = 0
        self._opened_at: float | None = None
        self._fault = ""

    # -- what a channel calls ---------------------------------------------

    def open(self) -> None:
        self._holders += 1
        if self._opened_at is None:
            self._opened_at = self.clock()

    def close(self) -> None:
        self._holders = max(self._holders - 1, 0)
        if not self._holders:
            self._opened_at = None

    def want(self, t: float) -> None:
        pass

    def latest(self) -> MediaFrame | None:
        """The newest frame while it is under `HOLD_S` old, else None."""
        f = self._frame
        if f is None or self.clock() - f.t > HOLD_S:
            return None
        return f

    def gl_poll(self) -> MediaFrame | None:
        """The frame thread: ask for the canvas at this frame's end, and
        read what the tap wrote last (a frame per grab, by `frame_no`)."""
        tap = self.tap
        if tap is None:
            return None
        tap.want()
        tex = getattr(tap, "tex", None)
        n = int(getattr(tap, "frame_no", 0))
        if tex is not None and (self._frame is None or self._frame.frame != n):
            size = tuple(int(v) for v in tap.size)
            self._frame = MediaFrame(None, float(tap.at), n, texture=int(tex.glo),
                                     tex_size=(size[0], size[1]), tex_target=TEX_2D)
            self._fault = ""
        return self.latest()

    @property
    def status(self) -> str:
        if self._fault:
            return "error: " + self._fault
        f, now = self._frame, self.clock()
        if f is not None and now - f.t <= HOLD_S:
            return READY
        at = self._opened_at
        if f is None and at is not None and now - at <= HOLD_S:
            return FETCHING
        return LOST

    @status.setter
    def status(self, value: str) -> None:
        """What the channels say when reading the source raised."""
        self._fault = str(value).removeprefix("error: ")

    @property
    def held(self) -> int:
        return self._holders

    def __repr__(self) -> str:
        return f"<PanelSource {self.sid} {self.status}>"
