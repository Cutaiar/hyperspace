"""Source ids: `<kind>:<ref>`, the one name a channel slot, a preset and the
resolver share. `shared:` and `local:` are folder-relative, `file:` is an
absolute path, the rest name a live feed. `phone:` is reserved (V2): it
parses but is never opened. `panel:` names a picture of the control
window's own (2026-11-02): `panel:graph`, the GRAPH canvas, a built-in
the app's resolver answers without a `[[devices]]` entry."""

from __future__ import annotations

from typing import NamedTuple

KINDS = ("shared", "local", "file", "camera", "syphon", "ndi", "phone", "panel")
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
