"""Choosing a source for an id: by extension for the file kinds, through
the resolver for live ones. The resolver (the app's media folder and live
registry) is a Protocol so tests can hand in a fake."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from . import ids
from .source import MISSING, Source, error
from .still import STILL_EXT, StillSource

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".gif", ".avi"}   # = video.VIDEO_EXT


class Resolver(Protocol):
    def path(self, sid: str) -> Path | None: ...
    def live(self, sid: str) -> Source | None: ...


class MissingSource:
    """A slot whose file or feed is not there: black, status `missing`."""

    kind = "missing"
    timed = False
    duration = 0.0

    def __init__(self, sid: str, status: str = MISSING):
        self.sid = sid
        self.status = status

    def latest(self):
        return None

    def want(self, t: float) -> None:
        pass

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass


def open_source(sid: str, resolver: Resolver) -> Source:
    """A source for `sid`, not yet opened. Never raises."""
    try:
        parsed = ids.parse(sid)
    except ValueError as e:
        return MissingSource(sid, error(str(e)))
    if parsed.kind in ids.FILE_KINDS:
        path = resolver.path(sid)
        if path is None:
            return MissingSource(sid)
        if Path(path).suffix.lower() in STILL_EXT:
            return StillSource(sid, path)
        if Path(path).suffix.lower() in VIDEO_EXT:
            from .video import VideoSource   # lazily: pulls in nothing heavy itself
            return VideoSource(sid, path, cache=getattr(resolver, "proxy_cache", None))
        return MissingSource(sid, error("unsupported"))
    if parsed.kind == "phone":   # reserved (V2): parsed, never opened
        return MissingSource(sid, error("unsupported"))
    live = resolver.live(sid)
    return live if live is not None else MissingSource(sid)
