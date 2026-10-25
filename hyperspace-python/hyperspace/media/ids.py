"""Source ids: `<kind>:<ref>`, the one name a channel slot, a preset and the
resolver share. `shared:` and `local:` are folder-relative, `file:` is an
absolute path, the rest name a live feed. `phone:` is reserved (V2): it
parses but is never opened."""

from __future__ import annotations

from typing import NamedTuple

KINDS = ("shared", "local", "file", "camera", "syphon", "ndi", "phone")
FILE_KINDS = ("shared", "local", "file")


class SourceId(NamedTuple):
    kind: str
    ref: str


def parse(sid: str) -> SourceId:
    """Split `sid` at the first colon; the ref keeps everything after it."""
    kind, sep, ref = str(sid).partition(":")
    if not sep or kind not in KINDS:
        raise ValueError(f"not a source id: {sid!r}")
    return SourceId(kind, ref)
