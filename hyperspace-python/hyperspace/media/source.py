"""The source contract: what a channel reads, whatever made the frame."""

from __future__ import annotations

from typing import Protocol

from .frame import MediaFrame

READY, FETCHING, MISSING, LOST = "ready", "fetching", "missing", "lost"


def error(why: str) -> str:
    """A status for a source that failed, kept short enough for a label."""
    return "error: " + why[:160]


class Latest:
    """The newest frame a source thread has made, for the frame thread to
    read. One attribute swap: assigning a reference is atomic in CPython and
    a frame is immutable, so a reader sees the old frame or the new one,
    never a mix, and no lock is needed."""

    def __init__(self):
        self._f: MediaFrame | None = None

    def put(self, f: MediaFrame) -> None:
        self._f = f

    def get(self) -> MediaFrame | None:
        return self._f


class Source(Protocol):
    """`status` is READY, FETCHING, MISSING, LOST or `error(...)`. `want`
    is the transport's time in seconds (a no-op when untimed); `close`
    joins the source's thread. A source may also define `gl_poll() ->
    MediaFrame | None`, called only on the frame thread by the renderer
    (Syphon's `textureName()` needs the GL thread); sources without it are
    read with `latest()`."""

    sid: str
    kind: str
    status: str
    timed: bool
    duration: float   # seconds; 0.0 when untimed

    def latest(self) -> MediaFrame | None: ...
    def want(self, t: float) -> None: ...
    def open(self) -> None: ...
    def close(self) -> None: ...
