"""Slots for hot classes, in a module no reload re-executes (row 802).

A hot class can't add to its object's layout over another hot class: once the base
has reloaded, Python refuses the re-class (`hotreload.py`'s contract). A class that
needs slots there takes them from a base here, so its layout's base is one class on
both sides of every reload. A leaf: it imports nothing. Cold, so changing it needs a
restart.
"""

from __future__ import annotations


class DeckProjectSlots:
    """`library.DeckProject`'s own fields. The view shares its show's `__dict__`, so
    nothing of its own can live there."""

    __slots__ = ("lib", "meta")


class DeckLibrarySlots:
    """`library.DeckLibrary`'s own fields, for the same reason."""

    __slots__ = ("_project", "base", "own")
