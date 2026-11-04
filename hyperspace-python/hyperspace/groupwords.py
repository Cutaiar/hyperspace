"""What the panel calls a param group, where that is not its key (wave 4 AZ).

A group's key is saved: a show's `modules`, a library folder, `band.*` ids. So
it stays what it is, and everything a person reads goes through here. Group
`band` is the analyzer: the fixture on the graph and its tuning. One of its
parts is a band, the plain audio word (register row 737).

A leaf: it imports nothing from the package. `undo.py` must stay a leaf too, so
it asks through `Registry.group_word`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroupWords:
    word: str                # short, inside a line: "analyzer: Balanced"
    title: str               # full, the group's own head or node: "analyzer tuning"
    part: str                # one of its parts, for a small button: "band"


GROUPS = {"band": GroupWords("analyzer", "analyzer tuning", "band")}


def group_word(group: str) -> str:
    """The group inside a line; its key where it has no other word."""
    g = GROUPS.get(group)
    return g.word if g is not None else group


def group_title(group: str) -> str:
    """The group as a head or a node's title; its key where it has no other."""
    g = GROUPS.get(group)
    return g.title if g is not None else group


def group_part(group: str) -> str:
    """One part of the group, for a small button; its key where it has no other."""
    g = GROUPS.get(group)
    return g.part if g is not None else group
