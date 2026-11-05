"""Players and duties (plan 55): who is on which `Deck`, on this Mac.

Controllers are generic; the actors are named: player 1, 2, 3, 4. A player
holds any number of controllers (`devices` roles) and a duty, on air or off
air, and it stays until someone moves the player: `deck.MetaController` turns
a duty into a `Deck` and moves the pointers of what the player holds.

**A patch names a player, never a device.** A row's qualifier is the player's:
bare (``pad:A``, ``axis:LX``) is player 1, ``axis@p2:LX`` is player 2, with no
file change (plan 27's roles were the seam). A player's first controller of a
repeatable kind publishes under that name (`devices.qualifiers_of`); a second
of the same kind keeps its role as its address, so no two feed one lane. A
player with no such controller has rows that are dormant and drawn.

**Who holds what, unless told otherwise:** a role ``p2``, ``p3``, ``p4`` is
that player's, every other role player 1's, and a repeatable kind's primary
(`primaries`, told by the device registry) is player 1's whatever its role, so
a rig whose first pad is called ``p2`` reads the bare rows as it always did.

**Persistence.** The meta controller's, on this Mac: ``<home>/players.json``
beside ``bindings.json`` (`library_home()`, never the shared library, never a
patch, never a show). Only what differs from the defaults is written, and only
when someone moves or registers a player; no file means everyone on air and
the rule above. A file that cannot be read is said, set aside as
``players.json.bad``, and the defaults stand.

A leaf: it imports nothing of the package.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

FILE = "players.json"
SCHEMA = "players/1"
NUMBERS = (1, 2, 3, 4)
_ROLE = re.compile(r"p([1-4])")


class Duty(StrEnum):
    """What a player is on. A `StrEnum`, so one from before a hot reload is
    still equal to the reloaded class's."""

    ON_AIR = "on_air"
    OFF_AIR = "off_air"


def qualifier_of(number: int) -> str:
    """The name a row gives player `number`: "" for player 1, whose rows are
    the bare ones, else ``p<number>``."""
    return "" if number == 1 else f"p{number}"


@dataclass
class Player:
    """One named actor. What it holds is `Players.controllers_of`'s to say."""

    number: int
    duty: Duty = Duty.ON_AIR

    @property
    def qualifier(self) -> str:
        return qualifier_of(self.number)


class Players:
    """The four players, who holds what, and the file that remembers it.
    `path` None: nothing is written (the tests', and a rig with no home)."""

    def __init__(self, path: Path | None = None, notes: list[str] | None = None):
        self.path = Path(path) if path is not None else None
        self.notes = notes if notes is not None else []
        self.players = {n: Player(n) for n in NUMBERS}
        self.held: dict[str, int] = {}          # role → player, as registered
        self.known: tuple[str, ...] = ()        # the controllers listed (`tell`)
        self.primaries: frozenset[str] = frozenset()
        self.error = ""
        self._read()

    @classmethod
    def load(cls, home: Path | str | None, notes: list[str] | None = None) -> Players:
        """This Mac's: ``<home>/players.json``."""
        return cls(Path(home) / FILE if home is not None else None, notes)

    # ---- asking ----

    def __iter__(self):
        return iter(self.players.values())

    def get(self, number: int) -> Player:
        """Player `number`; a number outside 1–4 is a ValueError."""
        got = self.players.get(number)
        if got is None:
            raise ValueError(f"players: no player {number!r} (1 to 4)")
        return got

    def player_of(self, role: str) -> Player:
        """Who holds the controller `role` (the module's rule)."""
        number = self.held.get(role)
        if number is None and role not in self.primaries and (m := _ROLE.fullmatch(role)):
            number = int(m.group(1))
        return self.players[number if number is not None else 1]

    def controllers_of(self, number: int) -> tuple[str, ...]:
        """The roles player `number` holds, of the controllers listed
        (`tell`), then those registered and not listed now, in order."""
        self.get(number)
        return tuple(r for r in dict.fromkeys((*self.known, *self.held))
                     if self.player_of(r).number == number)

    def active(self) -> list[Player]:
        """The players holding a listed controller: who a select screen shows."""
        return [p for p in self if any(self.player_of(r) is p for r in self.known)]

    # ---- told ----

    def tell(self, known, primaries=()) -> None:
        """The device registry: the controllers listed, and which are their
        kind's primaries (the module's rule). Not saved: the list is the config's."""
        self.known = tuple(known)
        self.primaries = frozenset(primaries)

    # ---- moved ----

    def move(self, number: int, duty: Duty | str) -> Player:
        """Player `number` to `duty`, remembered. `MetaController.move_player`
        also moves its pointers: call that."""
        player, duty = self.get(number), Duty(duty)
        if player.duty != duty:
            player.duty = duty
            self.save()
        return player

    def hold(self, role: str, number: int) -> None:
        """Player `number` holds the controller `role` from now on, remembered.
        `MetaController.register` also moves its pointer: call that."""
        self.get(number)
        if self.held.get(role) != number:
            self.held[role] = number
            self.save()

    # ---- the file ----

    def to_json(self) -> dict:
        """What differs from the defaults."""
        return {"schema": SCHEMA,
                "duties": {str(p.number): p.duty.value for p in self if p.duty != Duty.ON_AIR},
                "controllers": dict(self.held)}

    def save(self) -> None:
        """Written whole, through a temporary file; a failure is `error` and
        a note, and the move stands for this run."""
        if self.path is None:
            return
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            tmp.write_text(json.dumps(self.to_json(), indent=2) + "\n")
            tmp.replace(self.path)
            self.error = ""
        except OSError as e:
            self._say(f"players: not remembered after this run: {e}")

    def _read(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            doc = json.loads(self.path.read_text())
            if doc.get("schema") != SCHEMA:
                raise ValueError(f"schema {doc.get('schema')!r}")
            duties = {int(n): Duty(d) for n, d in doc.get("duties", {}).items()}
            held = {str(r): int(n) for r, n in doc.get("controllers", {}).items()}
            if not {*duties, *held.values()} <= set(NUMBERS):
                raise ValueError("a player outside 1 to 4")
        except (OSError, ValueError, AttributeError, TypeError) as e:
            self._set_aside(e)
            return
        self.held = held
        for number, duty in duties.items():
            self.players[number].duty = duty
        away = [p.number for p in self if p.duty == Duty.OFF_AIR]
        if away:
            who = ", ".join(str(n) for n in away)
            self.notes.append(f"players: {'player' if len(away) == 1 else 'players'} {who} "
                              f"off air, as left ({FILE})")

    def _set_aside(self, why) -> None:
        bad = self.path.with_name(self.path.name + ".bad")
        try:
            self.path.replace(bad)
            self._say(f"players: {self.path.name} could not be read ({why}) — kept as "
                      f"{bad.name}, everyone on air")
        except OSError as e:
            self._say(f"players: {self.path.name} could not be read ({why}; {e}) — "
                      "everyone on air")

    def _say(self, note: str) -> None:
        self.error = note[:200]
        self.notes.append(self.error)
