"""Modifiers — the modulation graph's curated value nodes (plan 28 N1).

A modifier reads one or two source lanes, has a few params of its own,
and publishes one output lane under the scheme ``mod`` (``mod:<n>`` for
``mod.<n>``), so a route may say ``"source": "mod:2"`` and the Router,
Learn, the referee and ROUTING's source combo need no new path. They
live in the preset beside its routes (decision 8, `preset.MODIFIERS_KEY`)
and never in `bindings.json`.

  kind       inputs  params                            out
  curve      1       shape −1…1 (0 linear), invert     value
  scale      1       mul, offset, clamp                value
  smooth     1       attack, release, spring           value
  combine    2       how (add mul min max cross),      value
                     balance
  threshold  1       on, off (hysteresis), hold        trigger
  delay      1       —                                 value (last frame's input)

`step(m, inputs, state, dt)` is pure but for `state` (the smoother's
follower, the threshold's gate and hold, the delay's held value); the
Router steps each modifier once a frame and feeds the output into its
``mod`` lane (`routing.Router._step_modifier`). The registry params
``mod.<n>.<p>`` are the router module's to declare — this module is a
leaf and imports nothing from the package but `motion` and `tapers`: it
says what each kind's params are (`PARAMS`), the declaration is
`routing.declare_modifiers`.

Ids follow the naming rule: ``mod.1``, ``mod.2``… (`next_id`: one past
the highest, so a route left on a removed modifier's lane is never
silently picked up by the next one added while a higher one stands).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from .motion import Follower, Motion
from .tapers import clamp

SCHEME = "mod"              # the output lanes' scheme: ``mod:<n>``
PREFIX = "mod."             # the ids, and the registry group's params: ``mod.<n>.<p>``
GROUP = "mod"               # the registry group (params.PERFORMANCE_GROUPS)
KINDS = ("curve", "scale", "smooth", "combine", "threshold", "delay")
HOW = ("add", "mul", "min", "max", "cross")
# how many inputs each kind reads
INPUTS = {"curve": 1, "scale": 1, "smooth": 1, "combine": 2, "threshold": 1, "delay": 1}
VALUE, TRIGGER = "value", "trigger"     # the two signal kinds (decision 10)
OUT = {"threshold": TRIGGER}            # every other kind's output is a value
REST = 0.0                  # where every modifier's lane rests (`Router.rests`)
CURVE_POW = 4.0             # `curve`'s shape ±1 is an exponent of 4^±1
SPRING_BOUNCE = 0.4         # `smooth` with spring on: motion.Motion's bounce (ζ 0.6)


@dataclass(frozen=True)
class Spec:
    """One param of a kind: its key (``mod.<n>.<key>``), label, range,
    default, and what it is — "continuous", "toggle" or "enum" (`choices`)."""

    key: str
    label: str
    default: float
    lo: float = 0.0
    hi: float = 1.0
    kind: str = "continuous"
    choices: tuple[str, ...] = ()
    tip: str = ""


PARAMS: dict[str, tuple[Spec, ...]] = {
    "curve": (
        Spec("shape", "shape", 0.0, -1.0, 1.0,
             tip="Bends the input: 0 straight, up to 1 slow to start (x⁴), down to −1 "
                 "fast to start (x^¼)"),
        Spec("invert", "invert", 0.0, kind="toggle", tip="Turn it upside down: 1 − y"),
    ),
    "scale": (
        Spec("mul", "×", 1.0, -4.0, 4.0, tip="Multiplies the input"),
        Spec("offset", "+", 0.0, -1.0, 1.0, tip="Added after the multiply"),
        Spec("clamp", "clamp", 1.0, kind="toggle", tip="Hold the result inside 0…1"),
    ),
    "smooth": (
        Spec("attack", "attack", 0.05, 0.0, 2.0,
             tip="Seconds to rise (a one-pole's time constant); with spring on, the "
                 "spring's speed"),
        Spec("release", "release", 0.35, 0.0, 4.0, tip="Seconds to fall back"),
        Spec("spring", "spring", 0.0, kind="toggle",
             tip="A spring instead of the follower: it overshoots a little and rings"),
    ),
    "combine": (
        Spec("how", "how", 0.0, 0.0, len(HOW) - 1, kind="enum", choices=HOW,
             tip="add, multiply, the lower, the higher, or a crossfade by balance"),
        Spec("balance", "balance", 0.5, tip="The crossfade: 0 the first input, 1 the second"),
    ),
    "threshold": (
        Spec("on", "on", 0.6, tip="The input crossing up through this fires"),
        Spec("off", "off", 0.4, tip="…and must fall under this before it can fire again"),
        Spec("hold", "hold", 0.1, 0.0, 2.0, tip="Seconds the output stays at 1 after a fire"),
    ),
    "delay": (),
}


def spec(kind: str, key: str) -> Spec | None:
    return next((s for s in PARAMS.get(kind, ()) if s.key == key), None)


def defaults(kind: str) -> dict[str, float]:
    return {s.key: float(s.default) for s in PARAMS[kind]}


# ---------------------------------------------------------------- the node

@dataclass(eq=False)
class Modifier:
    """One node: its id (``mod.<n>``), kind, the source addresses it reads
    ("" for an input not chosen yet: the modifier is dormant), and its
    params by key — the live (effective) values the registry's
    ``mod.<n>.<p>`` params read and write."""

    id: str
    kind: str
    inputs: tuple[str, ...] = ()
    params: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"no modifier kind {self.kind!r}; one of {', '.join(KINDS)}")
        if number(self.id) is None:
            raise ValueError(f"a modifier id is mod.<n>, not {self.id!r}")
        n = INPUTS[self.kind]
        ins = tuple("" if a is None else str(a) for a in self.inputs)
        self.inputs = (ins + ("",) * n)[:n]
        self.params = {**defaults(self.kind), **{k: float(v) for k, v in self.params.items()
                                                 if spec(self.kind, k) is not None}}

    @property
    def n(self) -> int:
        return number(self.id) or 0

    @property
    def address(self) -> str:
        """The output lane, as a route names it: ``mod:<n>``."""
        return f"{SCHEME}:{self.n}"

    @property
    def out(self) -> str:
        return OUT.get(self.kind, VALUE)

    def to_json(self, params: dict[str, float] | None = None) -> dict:
        """The preset's entry: id, kind, ``in``, then each param — an enum
        by its name, a toggle as a bool. `params` (the registry's bases)
        stands in for the live values when given."""
        vals = self.params if params is None else {**self.params, **params}
        d: dict = {"id": self.id, "kind": self.kind,
                   "in": [a or None for a in self.inputs]}
        for s in PARAMS[self.kind]:
            v = float(vals.get(s.key, s.default))
            if s.kind == "enum":
                d[s.key] = s.choices[int(clamp(round(v), 0, len(s.choices) - 1))]
            elif s.kind == "toggle":
                d[s.key] = v >= 0.5
            else:
                d[s.key] = v
        return d

    @classmethod
    def from_json(cls, d) -> Modifier:
        """A preset's entry; ValueError for one that names no kind or id
        this build knows. A missing param takes its default, an unknown
        key is ignored, an enum may be its name or its index."""
        if not isinstance(d, dict):
            raise TypeError(f"a modifier is an object, not {type(d).__name__}")
        kind, mid = d.get("kind"), d.get("id")
        if kind not in KINDS:
            raise ValueError(f"no modifier kind {kind!r}")
        ins = d.get("in") or []
        if isinstance(ins, str):
            ins = [ins]
        params: dict[str, float] = {}
        for s in PARAMS[kind]:
            if s.key not in d:
                continue
            v = d[s.key]
            if s.kind == "enum" and isinstance(v, str):
                if v not in s.choices:
                    raise ValueError(f"{mid}: {s.key} is one of {', '.join(s.choices)}, "
                                     f"not {v!r}")
                v = s.choices.index(v)
            params[s.key] = float(v)
        return cls(str(mid), str(kind), tuple(ins), params)


def number(mid: str | None) -> int | None:
    """``mod.3`` → 3; None for anything else."""
    if not isinstance(mid, str) or not mid.startswith(PREFIX):
        return None
    tail = mid[len(PREFIX):]
    return int(tail) if tail.isdecimal() and str(int(tail)) == tail and int(tail) >= 1 else None


def id_of(address: str) -> str | None:
    """``mod:3`` → ``mod.3``; None for an address of any other scheme."""
    scheme, _, tail = address.partition(":")
    if scheme != SCHEME or not tail.isdecimal():
        return None
    mid = f"{PREFIX}{int(tail)}"
    return mid if number(mid) is not None else None


def next_id(ids: Iterable[str]) -> str:
    """The id a new modifier gets: one past the highest held."""
    return f"{PREFIX}{max((number(i) or 0 for i in ids), default=0) + 1}"


def param_id(mid: str, key: str) -> str:
    return f"{mid}.{key}"


# ---------------------------------------------------------------- stepping

@dataclass
class ModState:
    """A modifier's memory between frames: the smoother's follower, the
    threshold's gate and the time its fire has left, the delay's held
    input. Fresh when the modifier is made, or when its input goes away."""

    follower: Follower | None = None
    gate: bool = False
    left: float = 0.0
    held: float | None = None


def _curve(x: float, p: dict) -> float:
    x = clamp(x, 0.0, 1.0)
    y = x ** (CURVE_POW ** clamp(p.get("shape", 0.0), -1.0, 1.0))
    return 1.0 - y if p.get("invert", 0.0) >= 0.5 else y


def _scale(x: float, p: dict) -> float:
    y = x * p.get("mul", 1.0) + p.get("offset", 0.0)
    return clamp(y, 0.0, 1.0) if p.get("clamp", 1.0) >= 0.5 else y


def smooth_motion(p: dict) -> Motion:
    """`smooth`'s feel from its params: the follower on attack / release,
    or with spring on a spring whose speed is attack's (ω = 1 / attack,
    its time feel: a perceptual duration of 2π·attack) at SPRING_BOUNCE.
    What it steps, and what the panel plots (ui_feel)."""
    atk, rel = max(0.0, p.get("attack", 0.0)), max(0.0, p.get("release", 0.0))
    if p.get("spring", 0.0) >= 0.5:
        return Motion("spring", dur=2 * math.pi * atk, bounce=SPRING_BOUNCE)
    return Motion("follow", atk=atk, rel=rel)


def _smooth(x: float, p: dict, state: ModState, dt: float) -> float:
    if state.follower is None:            # first sight: start on the reading
        state.follower = Follower(x)
        return x
    return state.follower.step(x, dt, smooth_motion(p), REST)


def _combine(a: float, b: float, p: dict) -> float:
    how = HOW[int(clamp(round(p.get("how", 0.0)), 0, len(HOW) - 1))]
    if how == "add":
        return a + b
    if how == "mul":
        return a * b
    if how == "min":
        return min(a, b)
    if how == "max":
        return max(a, b)
    bal = clamp(p.get("balance", 0.5), 0.0, 1.0)
    return a * (1.0 - bal) + b * bal


def _threshold(x: float, p: dict, state: ModState, dt: float) -> float:
    on = p.get("on", 0.6)
    off = min(p.get("off", 0.4), on)          # an off above on is on: no hysteresis
    if not state.gate and x >= on:
        state.gate, state.left = True, max(0.0, p.get("hold", 0.0))
        return 1.0                            # the rising edge: always one frame
    if state.gate and x < off:
        state.gate = False
    if state.left > 0.0:
        state.left -= dt
        if state.left > 1e-9:
            return 1.0
        state.left = 0.0
    return 0.0


def step(m: Modifier, inputs: tuple[float, ...], state: ModState, dt: float) -> float:
    """One frame of `m` on its inputs' readings (every one live: the
    caller makes the node dormant otherwise), reading its params as they
    are now (`m.params`). Pure but for `state`."""
    p, x = m.params, float(inputs[0])
    k = m.kind
    if k == "curve":
        return _curve(x, p)
    if k == "scale":
        return _scale(x, p)
    if k == "smooth":
        return _smooth(x, p, state, dt)
    if k == "combine":
        return _combine(x, float(inputs[1]), p)
    if k == "threshold":
        return _threshold(x, p, state, dt)
    # delay: last frame's input — at its rest on the first frame
    out = REST if state.held is None else state.held
    state.held = x
    return out
