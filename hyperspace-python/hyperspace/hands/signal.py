"""The hand axes as analog signals — shaping, dynamics, MIDI encoding.

Pure functions and small state machines, no SDK and no registry, so
core.py composes them and the tests drive them directly. One axis, per
frame:

    raw ──norm──▶ u ──One Euro──▶ ──shape──▶ target ──Follower──▶ y ──encode──▶ MIDI
                (calibrated lo/hi)   (dead zone, curve)   (attack/decay,     (cc, cc14,
                                                          spring to rest)    pitch, pressure)

`shape` — the static transfer. A *bipolar* axis (a tilt, a sideways
position) is shaped about its middle: the dead zone is a flat band
around 0.5 so a neutral hand reads exactly neutral, and the curve bends
both halves the same way. A *unipolar* axis (height) has its dead zone
at the bottom, so "off" is easy to hit. The dead zone never shortens the
throw: what is left of the range is stretched to reach 0 and 1 again.
curve c ∈ [−1, 1] is the exponent 4^c on the magnitude: 0 linear, +1
fine control near the centre (or bottom) and fast at the ends, −1 the
reverse.

`Follower` — the dynamics, run every render frame. While the hand is in
view the output follows the shaped target through a one-pole slew with
separate *attack* (rising) and *decay* (falling) times — the envelope an
analog synth would put on a control voltage. When the hand leaves, a
`return` axis springs to its rest value (a damped spring: `return_s` is
how long it takes to settle, `bounce` how much it overshoots on the way)
and a `hold` axis stays where it was. When a hand comes back the output
does not jump to it: it glides there over `catch_s` on a critically
damped spring, then follows again.

`quantize` / `encode` — y ∈ [0, 1] to MIDI. 7-bit CC and channel
pressure use 0–127; 14-bit CC (MSB on n, LSB on n + 32, so n ≤ 31) and
pitch bend use 0–16383. Every encoding holds its last value until y is
clearly past the next step (hysteresis), so a still hand sends nothing.
"""

from __future__ import annotations

import math

import mido

OUTS = ["off", "cc", "cc14", "pitch", "pressure"]
RESTS = ["hold", "return"]
FULL = {"cc": 127, "pressure": 127, "cc14": 16383, "pitch": 16383}
HYST_14 = 3.0            # 14-bit hysteresis in steps: a few LSB of tracker noise
SPRING_H = 0.002         # spring integration substep, s


# ------------------------------------------------------------------ shape

def curve(m: float, c: float) -> float:
    """m ∈ [0, 1] bent by c ∈ [−1, 1] (exponent 4^c)."""
    return m ** (4.0 ** c) if m > 0.0 else 0.0


def shape(u: float, *, bipolar: bool, deadzone: float, c: float) -> float:
    """The static transfer of a normalized reading (see the module doc)."""
    u = min(1.0, max(0.0, u))
    dz = min(max(deadzone, 0.0), 0.95)
    if bipolar:
        d = (u - 0.5) * 2.0
        m = max(0.0, (abs(d) - dz) / (1.0 - dz))
        return 0.5 + math.copysign(curve(m, c), d) / 2.0
    return curve(max(0.0, (u - dz) / (1.0 - dz)), c)


# --------------------------------------------------------------- dynamics

def slew(y: float, target: float, dt: float, attack: float, decay: float) -> float:
    """One-pole follow: `attack` seconds rising, `decay` falling (0 = instant)."""
    tau = attack if target > y else decay
    if tau <= 0.0 or dt <= 0.0:
        return target if tau <= 0.0 else y
    return y + (target - y) * (1.0 - math.exp(-dt / tau))


def spring(y: float, v: float, target: float, dt: float, settle: float,
           bounce: float = 0.0) -> tuple[float, float]:
    """A damped spring toward target: settles in about `settle` seconds;
    bounce 0 is critically damped, toward 1 it rings. Returns (y, v)."""
    if settle <= 0.0:
        return target, 0.0
    zeta = 1.0 - 0.85 * min(max(bounce, 0.0), 1.0)
    # within ~2 % by `settle`: critically damped, (1 + ωt)·e^(−ωt) = 0.02 at
    # ωt ≈ 5.8; underdamped, the envelope e^(−ζωt) is well inside that
    w = 5.8 / (zeta * settle)
    n = max(1, math.ceil(dt / min(SPRING_H, 0.5 / w)))   # keep ωh small: stable
    h = dt / n
    for _ in range(n):                    # semi-implicit Euler: stable at this h
        v += (w * w * (target - y) - 2.0 * zeta * w * v) * h
        y += v * h
    return y, v


class Follower:
    """One axis's output over time: follow, catch on entry, rest on exit."""

    FOLLOW, CATCH, REST, HOLD = "follow", "catch", "rest", "hold"

    def __init__(self):
        self.y: float | None = None     # None until a hand has ever been seen
        self.v = 0.0
        self.mode = self.HOLD
        self.t = 0.0                    # time in the current mode

    @property
    def live(self) -> bool:
        """True while a hand is driving `y` — following, or being caught on
        its return. False before the first sight and while the hand is
        away, when the spring or the hold shape only the DAW output: the
        routing lane reads NaN then, so a row lets go of its param the
        frame the hand leaves (plan 11, audit B1). The catch stays live so
        a one-frame tracking dropout costs one frame, not a catch-long
        hole, and a push row keeps its glide onto a returning hand."""
        return self.mode in (self.FOLLOW, self.CATCH)

    def step(self, dt: float, target: float | None, *, attack: float, decay: float,
             catch_s: float, rest: str, rest_value: float, return_s: float,
             bounce: float) -> float | None:
        """target: the shaped hand value, None while the hand is away."""
        if target is not None:
            if self.y is None:            # first sight: start where the hand is
                self.y, self.v, self.mode, self.t = target, 0.0, self.FOLLOW, 0.0
                return self.y
            if self.mode in (self.REST, self.HOLD):
                self.mode, self.t = self.CATCH, 0.0
            if self.mode == self.CATCH:
                self.t += dt
                self.y, self.v = spring(self.y, self.v, target, dt, catch_s)
                if self.t >= catch_s or abs(self.y - target) < 1e-4:
                    self.mode, self.v = self.FOLLOW, 0.0
            else:
                self.y = slew(self.y, target, dt, attack, decay)
        elif self.y is not None:
            if rest == "return":
                if self.mode != self.REST:
                    self.mode, self.t = self.REST, 0.0
                self.t += dt
                self.y, self.v = spring(self.y, self.v, rest_value, dt, return_s, bounce)
            else:
                self.mode, self.v = self.HOLD, 0.0
        if self.y is not None:
            self.y = min(1.0, max(0.0, self.y))
        return self.y


# ------------------------------------------------------------------- MIDI

def quantize(u: float, last: int | None, hysteresis: float, full: int = 127) -> int:
    """u ∈ [0, 1] → 0…full, holding `last` until u is clearly past the step."""
    v = min(1.0, max(0.0, u)) * full
    q = round(v)
    if last is None or q == last:
        return q
    return q if abs(v - last) >= 0.5 + hysteresis else last


def valid(out: str, number: int) -> str:
    """Why an output can't be sent as configured; "" when it can."""
    if out == "cc14" and not 0 <= number <= 31:
        return "14-bit CC needs a number 0–31 (the LSB goes on number + 32)"
    if out in ("cc", "cc14") and not 0 <= number <= 127:
        return "CC number out of range"
    return ""


def encode(out: str, channel: int, number: int, q: int) -> list[mido.Message]:
    """A quantized value as messages; channel 0-based."""
    if out == "cc":
        return [mido.Message("control_change", channel=channel, control=number, value=q)]
    if out == "cc14":
        return [mido.Message("control_change", channel=channel, control=number, value=q >> 7),
                mido.Message("control_change", channel=channel, control=number + 32,
                             value=q & 0x7F)]
    if out == "pitch":
        return [mido.Message("pitchwheel", channel=channel, pitch=q - 8192)]
    if out == "pressure":
        return [mido.Message("aftertouch", channel=channel, value=q)]
    return []


def describe(m: mido.Message) -> str:
    """A sent message the way the page shows it: "16·cc105 = 64"."""
    ch = f"{m.channel + 1}·"
    if m.type == "control_change":
        return f"{ch}cc{m.control} = {m.value}"
    if m.type == "pitchwheel":
        return f"{ch}bend = {m.pitch:+d}"
    if m.type == "aftertouch":
        return f"{ch}press = {m.value}"
    if m.type in ("note_on", "note_off"):
        return f"{ch}note {m.note} {'on' if m.type == 'note_on' and m.velocity else 'off'}"
    return str(m)
