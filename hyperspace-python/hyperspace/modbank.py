"""A modulator bank — voices with stable ids, declared at runtime (plan 31 B).

A bank is a row of like voices (the LFOs; the envelopes next) that the
router steps inside its modulation pass and publishes as one source
scheme. Voice `n` (1-based, its params ``<scheme>.<n>.<key>``) is the
lane ``<scheme>:<n-1>`` — the address every route, Learn row and factory
preset already names (``lfo:0`` is LFO 1). Membership is preset content
and undoable, the rule plan 28 N1 set for the modifiers: ids are **one
past the highest** (`next_id`) and **never compact**, so removing LFO 2
leaves LFO 3 on ``lfo:2`` and a route left on a removed voice's lane is
never silently picked up by the next one added while a higher one
stands. The count is capped at `MAX` (decision 1: 16).

What the bank owns, and what a kind supplies:

  membership   `ids` / `add` / `remove` / `set` / `doc` — the preset's
               ``"<KEY>": [ids]`` and undo's part; `parse` reads a file's
  params       through the kind's `declare(reg, n, voice)` (bound with
               `bind`): a voice added drops ``<scheme>.<n>.`` and
               declares it afresh, one removed drops it. Every add and
               remove moves `reg.serial`, which is what rebuilds the
               router's patch (`Router._patch_key`) — no other hook
  the frame    `begin` (a held global gesture lands, the frame's output
               list made), `step_one` per voice at its patch node,
               `step` for a caller with no router
  publishing   `outputs` is as wide as the highest id, NaN in a gap, so
               a route from a deleted voice reads NaN and goes dormant —
               `Router.modulate` skips a NaN lane, as for a hand out of
               view. A gap's label is "", which the source combo reads
               as no lane (the `mod` scheme's rule)
  late gestures  `late` / `late_one`: a trigger arriving after the bank
               (or that voice) already stepped at this frame's t — the
               panel's chip, `Registry.apply` — is the kind's to hold for
               the next step, so it lands at that step's own time (the
               LFO rule, lfo.py; the envelopes' fire with no `at`)

A kind subclasses `Bank` and sets the class attributes — `SCHEME`,
`LABEL`, `KEY`, `DEFAULT`, `REST`, `KNOBS`, `SHARED` — and `make`; the
router learns its scheme from `routing.BANKS` and steps an instance
handed to `Router.use_bank`.

A leaf: nothing here imports from the package — the registry and the
router are duck-typed arguments (tests/test_modbank.py holds the rule).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import Any

MAX = 16          # voices a bank holds at most (plan 31 decision 1)
MAX_ID = 64       # the highest id a file may name: a hand-edited 10⁹ is no feed vector
NAN = float("nan")


class Bank:
    """Voices by stable 1-based id, stepped once a frame, published as one
    source scheme. A subclass is one kind (lfo.LFOs)."""

    # the kind's table — class-level, so a subclass is a few lines
    SCHEME = ""                    # the lanes' scheme and the params' group: ``lfo``
    LABEL = ""                     # a voice's name: "LFO" → "LFO 3"
    KEY = ""                       # the preset's membership key: ``"lfos": [1, 2, 3, 4]``
    DEFAULT: tuple[int, ...] = ()  # the membership a file without `KEY` gets
    REST = 0.0                     # where a lane rests (`Router.rests`)
    KNOBS: tuple[str, ...] = ()    # ``<scheme>.<n>.<knob>`` params that feed the voice's node
    SHARED: dict[str, str] = {}    # bank-wide param id → the port it feeds on every voice
    MAX = MAX

    # class-level so an instance from before a hot reload has them
    stepped_at: float | None = None   # the t of the bank's last step
    serial = 0                        # moves on every membership change
    reg = None                        # the registry `bind` gave, or None
    declare: Callable[[Any, int, Any], None] | None = None

    def __init__(self, ids: Iterable[int] | None = None):
        self._voices: dict[int, Any] = {}
        self.outputs: list[float] = []
        for n in sorted(set(self.DEFAULT if ids is None else ids)):
            self._voices[int(n)] = self.make()
        self._resize()

    # ---- the kind ----

    def make(self):
        """A fresh voice, at its defaults."""
        raise NotImplementedError

    def step_voice(self, voice, dt: float, t: float, clock) -> float:
        """One voice's step for time t: its output, in [0, 1]."""
        return voice.step(dt, t, clock)

    # ---- membership ----

    def ids(self) -> list[int]:
        """The voices' ids, ascending."""
        return sorted(self._voices)

    @property
    def voices(self) -> list:
        """The voices in id order."""
        return [self._voices[n] for n in self.ids()]

    def voice(self, n: int):
        """Voice `n` (1-based), or None for a gap."""
        return self._voices.get(n)

    def __len__(self) -> int:
        return len(self._voices)

    def __getitem__(self, i: int):
        """The voice on lane `i` (0-based: ``lfo:i`` is id i + 1)."""
        v = self._voices.get(i + 1) if isinstance(i, int) and i >= 0 else None
        if v is None:
            raise IndexError(f"no {self.LABEL or 'voice'} on lane {i}")
        return v

    def __contains__(self, n: int) -> bool:
        return n in self._voices

    @property
    def width(self) -> int:
        """The feed vector's length: the highest id (0 for an empty bank)."""
        return max(self._voices, default=0)

    def next_id(self) -> int:
        """One past the highest: never a removed voice's id while a higher one stands."""
        return self.width + 1

    def can_add(self) -> bool:
        return len(self._voices) < self.MAX and self.next_id() <= MAX_ID

    def add(self, n: int | None = None) -> int:
        """A fresh voice, `n` or `next_id`, its params declared. Its id."""
        n = self.next_id() if n is None else int(n)
        if n in self._voices:
            raise ValueError(f"{self.LABEL} {n} is there already")
        if not 1 <= n <= MAX_ID:
            raise ValueError(f"a {self.LABEL} id is 1–{MAX_ID}, not {n}")
        if len(self._voices) >= self.MAX:
            raise ValueError(f"{self.MAX} {self.LABEL}s at most")
        v = self._voices[n] = self.make()
        self._declare(n, v)
        self._changed()
        return n

    def remove(self, n: int) -> bool:
        """Voice `n` and its params go; the ids above it stay where they
        are, and a route on its lane goes dormant. False: no such voice."""
        if self._voices.pop(n, None) is None:
            return False
        if self.reg is not None:
            self.reg.remove_prefix(self.prefix(n))
        self._changed()
        return True

    def doc(self) -> list[int]:
        """The membership as a preset holds it."""
        return self.ids()

    def set(self, ids: Iterable[int]) -> list[str]:
        """The membership becomes `ids` (a preset load, an undo): voices not
        in it go, missing ones come fresh at their defaults, the ones in
        both keep their state. Touches only what differs. Notes for what
        `parse` would refuse."""
        want, notes = self.parse(list(ids))
        for n in sorted(set(self._voices) - set(want), reverse=True):
            self.remove(n)
        for n in want:
            if n not in self._voices:
                self.add(n)
        return notes

    @classmethod
    def parse(cls, value) -> tuple[list[int], list[str]]:
        """A file's membership: (ids ascending, notes). Not a list: the
        default. An entry that is no id, or a second one, is dropped with a
        note; past `MAX` the lowest `MAX` stand."""
        if value is None:
            return list(cls.DEFAULT), []
        if not isinstance(value, list | tuple):
            return list(cls.DEFAULT), [f"{cls.KEY}: not a list of ids, {len(cls.DEFAULT)} "
                                       f"{cls.LABEL}s"]
        out: list[int] = []
        notes: list[str] = []
        for v in value:
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= MAX_ID:
                notes.append(f"{cls.KEY}: {v!r} is no {cls.LABEL} id, dropped")
            elif v in out:
                notes.append(f"{cls.KEY}: a second {v}, dropped")
            else:
                out.append(v)
        out.sort()
        if len(out) > cls.MAX:
            notes.append(f"{cls.KEY}: {cls.MAX} {cls.LABEL}s at most, "
                         f"{', '.join(map(str, out[cls.MAX:]))} dropped")
            out = out[:cls.MAX]
        return out, notes

    # ---- the params ----

    def prefix(self, n: int) -> str:
        """Voice `n`'s param prefix: ``lfo.3.``."""
        return f"{self.SCHEME}.{n}."

    def bind(self, reg, declare: Callable[[Any, int, Any], None]) -> None:
        """The registry voices declare onto, and the kind's `declare(reg, n,
        voice)`: from now on an add declares, a remove drops. Every voice
        there now is declared (afresh, if it was)."""
        self.reg, self.declare = reg, declare
        for n in self.ids():
            self._declare(n, self._voices[n])

    def _declare(self, n: int, voice) -> None:
        if self.reg is None or self.declare is None:
            return
        self.reg.remove_prefix(self.prefix(n))
        self.declare(self.reg, n, voice)

    def _changed(self) -> None:
        self.serial += 1
        self._resize()

    # ---- the frame ----

    def _resize(self) -> None:
        """`outputs` as wide as the highest id: a voice's last output, NaN
        in a gap."""
        old = list(getattr(self, "outputs", ()))
        self.outputs = [(old[k] if k < len(old) and not math.isnan(old[k])
                         else float(getattr(self._voices[k + 1], "out", self.REST)))
                        if k + 1 in self._voices else NAN for k in range(self.width)]

    def begin(self, t: float, clock) -> None:
        """The frame's start for the bank, before any voice steps:
        `outputs` becomes this frame's list (last frame's values until each
        voice steps). A kind with a held gesture lands it here, then calls this."""
        if len(self.outputs) != self.width:
            self._resize()
        self.outputs = list(self.outputs)

    def step_one(self, i: int, dt: float, t: float, clock) -> float:
        """The voice on lane `i`'s step for time t — what the modulation
        pass runs at its node, after the knob params it reads have landed
        this frame. Into `outputs[i]` and returned."""
        v = self[i]
        self.stepped_at = t
        v.at = t
        out = self.outputs[i] = self.step_voice(v, dt, t, clock)
        return out

    def step(self, dt: float, t: float, clock) -> list[float]:
        """One frame of the whole bank in id order — for a caller with no router."""
        self.begin(t, clock)
        for n in self.ids():
            self.step_one(n - 1, dt, t, clock)
        return self.outputs

    def late(self, clock, t: float | None) -> bool:
        """Did this arrive after the bank already stepped at this frame's t?
        (t None: the clock's.) The kind then holds it for the next step."""
        if t is None:
            t = getattr(clock, "t", None)
        return t is not None and t == self.stepped_at

    def late_one(self, i: int, clock, t: float | None) -> bool:
        """`late`, for the voice on lane `i` alone: a gesture the pass lands
        before that voice's node reads at once that same step."""
        if t is None:
            t = getattr(clock, "t", None)
        return t is not None and t == getattr(self[i], "at", self.stepped_at)

    # ---- publishing ----

    @property
    def labels(self) -> list[str]:
        """One per lane: "LFO 3", and "" for a gap (no lane to offer)."""
        return [f"{self.LABEL} {k}" if k in self._voices else ""
                for k in range(1, self.width + 1)]

    def publish(self, router) -> None:
        """This frame's outputs to the router under `SCHEME`, with the
        lanes' names and the rest a push row on a voice is centred on."""
        router.feed(self.SCHEME, self.outputs)
        router.labels[self.SCHEME] = self.labels
        router.rests[self.SCHEME] = [self.REST] * self.width
