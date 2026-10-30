"""Choosing a source for an id: by extension for the file kinds, through
the resolver for live ones. The resolver (the app's media folder and live
registry) is a Protocol so tests can hand in a fake."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from . import ids
from .source import FETCHING, MISSING, Source, error
from .still import STILL_EXT, StillSource

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".gif", ".avi"}   # = video.VIDEO_EXT


class Resolver(Protocol):
    """May also give `status(sid)` (the folder's word on a file) and
    `stamp(sid)` (what moves when the file is replaced)."""

    def path(self, sid: str) -> Path | None: ...
    def live(self, sid: str) -> Source | None: ...


def file_status(resolver, sid: str) -> str:
    """`fetching` when the resolver says the file is still downloading,
    else `missing` — the status of a file id with no path."""
    fn = getattr(resolver, "status", None)
    try:
        return FETCHING if fn is not None and fn(sid) == FETCHING else MISSING
    except Exception:  # noqa: BLE001 — asking is best-effort
        return MISSING


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
        if path is None:      # gone, or still downloading: never opened (A-I1)
            return MissingSource(sid, file_status(resolver, sid))
        if Path(path).suffix.lower() in STILL_EXT:
            return StillSource(sid, path)
        if Path(path).suffix.lower() in VIDEO_EXT:
            from .video import VideoSource  # lazily: pulls in nothing heavy itself
            return VideoSource(sid, path, cache=getattr(resolver, "proxy_cache", None))
        return MissingSource(sid, error("unsupported"))
    if parsed.kind == "phone":   # reserved (V2): parsed, never opened
        return MissingSource(sid, error("unsupported"))
    live = resolver.live(sid)
    return live if live is not None else MissingSource(sid)
