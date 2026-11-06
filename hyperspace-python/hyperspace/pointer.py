"""Which `Deck` a holder is on (plan 44 D5a, `deck.MetaController` owns them).

A holder is whatever acts on a look: one controller (a device by its role), the
keys, the mouse, the panel. Each has its own `Pointer`, so each can be moved on
its own, and it reads what it needs through it each time, never keeping a
deck's object: a kept `Param` or table is how a loadable patch comes to affect another.

`Through` is that read as a descriptor, for a holder whose handles tests and
the app assign before there is anything to point at (`panel.reg = …`,
`Host(reg=…)`). With no pointer it is a plain attribute; once the holder has
one it reads the deck's field, and assigning raises, since the value would
be ignored. It keeps its value in the instance's `__dict__` under its own name,
so an instance from before a hot reload brings it, and `hasattr` still answers.

A leaf: it imports nothing of the package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# every move of any pointer counts here (kept across a hot reload of this file): what
# a reader that caches what the pointers say compares (`Sources.away_from`)
moves: int = globals().get("moves", 0)


def deck_number(decks, deck) -> int:
    """Which of the two `decks` this is, as a person reads it: 1 or 2."""
    return 1 if deck is decks[0] else 2


@dataclass
class Pointer:
    """One holder's place: the `Deck` it is on now. A plain attribute to read."""

    deck: Any

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        if name == "deck":
            global moves
            moves += 1


class Through:
    """`field` of the deck the holder's pointer (its attribute `via`) is on;
    `field` None: the deck itself."""

    def __init__(self, field: str | None, via: str = "pointer"):
        self.field, self.via = field, via
        self.name = field or ""            # `__set_name__`'s, or by hand after a dataclass

    def __set_name__(self, owner, name: str) -> None:
        self.name = name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        vars_ = obj.__dict__
        pointer = vars_.get(self.via)
        if pointer is not None:
            return pointer.deck if self.field is None else getattr(pointer.deck, self.field)
        try:
            return vars_[self.name]
        except KeyError:
            raise AttributeError(self.name) from None

    def __set__(self, obj, value) -> None:
        if obj.__dict__.get(self.via) is not None:
            raise AttributeError(f"{self.name} reads through {self.via}: move the pointer "
                                 "(MetaController.point), do not assign the handle")
        obj.__dict__[self.name] = value
