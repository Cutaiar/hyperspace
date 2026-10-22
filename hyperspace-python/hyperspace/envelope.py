"""Envelope generators — event-driven AHDSR voices (plan 31 §E, decisions 2–3).

An envelope is a source like an LFO: something fires it, it rises to a
peak, falls to a sustain and lets go on release, and the router reads its
level as an ``env`` lane that rests at 0.0 (REST), like the modifiers and
the analyzer lanes, so a push row from it only ever pushes one way and a
negative row depth pushes down. This module is the leaf voice and its
params, and `Envelopes`, the `modbank.Bank` that holds voices by stable
id, publishes them as the ``env`` scheme and saves membership in the
preset (``"envs"``), calling `declare` once per voice.

Per envelope (every knob a registry param ``env.<n>.<knob>``, so it is
modulatable, Learnable and saved in the preset like an LFO's):

  mode      gate · one-shot — one-shot closes its own gate at the end of
            decay (a drum hit: a release does nothing); gate sustains
            until a release
  attack    seconds (or beats), log 1 ms – 8 s
  hold      the same, defaulting to 0 so out of the box it reads as ADSR;
            the knob's bottom (1 ms) *is* 0, since a log range cannot
            reach 0
  decay     the same
  sustain   0–1, a fraction of the peak
  release   the same as attack (the voice's attribute is `rel`: `release`
            is the method that closes the gate)
  curve     −1…1, one curve shared by every stage: a stage x ∈ [0, 1] of
            the way through has travelled ``x ** CURVE_POW ** curve`` of
            its distance — the modifiers' curve — so −1 is the snappy
            analog shape (fast out of every corner) and +1 the slow start
  sync      s · beats — in beats the times are beats, ``× 60 / bpm``,
            the bpm read every step, so a tempo change mid-stage changes
            the stage's rate from there, never its place
  retrig    legato · reset — legato re-attacks from the level it is at,
            reset snaps to 0 first
  amount    0–1, the peak at full velocity
  velocity  0–1, the sensitivity: peak = ``amount · (1 − vs + vs · vel)``
  fire      a trigger: one note, gate open (a performer's rising edge, a key)
  gate      a toggle, modulatable: high fires with an open gate, low
            releases — a held pad, a hand closing

**Event-driven, so exact.** The state is a stage, how far into it the
voice is (`p`, a fraction) as of a reference time, and the level the stage
started from. `fire` and `release` only queue an event stamped with its
time; `step(t)` walks the stage boundaries and the queued events up to t
in time order, and the level is a closed form of the progress — with the
knobs still, ``p = (t − stage start) / duration`` — so a fire the
sequencer stamps between two frames renders exactly where it would have
had a frame landed on it. Progress is kept as a fraction rather than as
time elapsed so a modulated stage time, or a bpm change, changes the rate
from where the stage is and never jumps the level. Beats are counted from
the bpm, not read off `clock.beat`, so the global trigger or a nudge
(which move the downbeat) never jerk an envelope mid-stage.

**The LFO rule for late fires.** A fire with no `at` (the panel's chip, a
key, `Registry.apply`'s rising edge, which run after the frame's step) is
held and lands at the next step's own t, so the first frame that sees it
shows level 0 at the very start of the attack, never dt into it. A
stamped `at` is clamped to no earlier than the last step: that frame is
already on screen. An event stamped past this step's t waits for the step
that reaches it — which is how `gate=` releases on its own.

The level is in note units (0 → 1 is rest → peak) and the output is that
times the note's peak, read live, so `amount` moved mid-note scales the
envelope the way an LFO's depth does instead of waiting for the next fire.

**The bank** (plan 31 W1, decision 3): `Envelopes` always holds the five
lane envelopes, 1–5 — the sequencer's lanes fire them, so every lane works
the moment a pad is pressed — and `remove` refuses them. Extras, 6 up to
the cap of 16, come and go by stable id like the LFOs. Its preset key,
``"envs"``, is written only when there are extras (`preset.Presets.document`
compares with `DEFAULT`), so a file saved without any is the file it was.

Nothing here imports from the host but the leaf `modbank`: the clock and
the registry are duck-typed arguments (tests/test_envelope_boundary.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .modbank import Bank

MODES = ["gate", "one-shot"]
SYNCS = ["s", "beats"]
RETRIGS = ["legato", "reset"]
GATE, ONE_SHOT = 0, 1
SECONDS, BEATS = 0, 1
LEGATO, RESET = 0, 1
STAGES = ("idle", "attack", "hold", "decay", "sustain", "release")
IDLE, ATTACK, HOLD, DECAY, SUSTAIN, RELEASE = range(6)
T_LO, T_HI = 0.001, 8.0      # every stage time's log range, s (or beats)
# the modifiers' curve exponent (modifiers.CURVE_POW) — copied, not
# imported: a leaf imports nothing from the host
CURVE_POW = 4.0
REST = 0.0
GROUP = "env"                # the registry group and the id prefix ``env.<n>``
KNOBS = ("mode", "attack", "hold", "decay", "sustain", "release", "curve", "sync",
         "retrig", "amount", "velocity")
# a knob's attribute on the voice, where it differs from its param key
ATTR = {"release": "rel"}
_FIRE, _RELEASE = 0, 1
_RUNNING = (ATTACK, HOLD, DECAY, RELEASE)   # the stages that end on their own


def shape(x: float, curve: float) -> float:
    """How far a stage x ∈ [0, 1] of the way through has travelled."""
    x = 0.0 if x < 0.0 else min(x, 1.0)
    c = -1.0 if curve < -1.0 else min(curve, 1.0)
    return x ** (CURVE_POW ** c)


@dataclass
class Envelope:
    """One AHDSR voice: its knobs (the params) and its running state."""

    mode: int = GATE
    attack: float = 0.01
    hold: float = 0.0
    decay: float = 0.2
    sustain: float = 0.6
    rel: float = 0.3             # the release time (`release` is the method)
    curve: float = 0.0
    sync: int = SECONDS
    retrig: int = LEGATO
    amount: float = 1.0
    velocity: float = 0.0        # the sensitivity; the note's own velocity is `vel`
    # runtime, never saved
    stage: int = field(default=IDLE, repr=False)
    p: float = field(default=0.0, repr=False)            # progress through the stage, 0–1
    ref: float | None = field(default=None, repr=False)  # the t `p` holds at
    y0: float = field(default=0.0, repr=False)           # the level the stage started from
    vel: float = field(default=1.0, repr=False)          # this note's velocity
    note: int = field(default=0, repr=False)             # counts fires: an auto-release's token
    at: float | None = field(default=None, repr=False)   # the t this voice last stepped at
    out: float = field(default=REST, repr=False)         # this step's output
    held: bool = field(default=False, repr=False)        # the `gate` param's state
    events: list = field(default_factory=list, repr=False)  # (t | None, seq, kind, args)
    seq: int = field(default=0, repr=False)              # queue order, for ties in t

    # ---- events ----

    def _queue(self, at: float | None, kind: int, args) -> None:
        # None stays None: the next step's t. A stamp before the last step
        # is clamped to it — that frame is already on screen
        if at is not None and self.at is not None:
            at = max(float(at), self.at)
        self.seq += 1
        self.events.append((at, self.seq, kind, args))

    def fire(self, at: float | None = None, velocity: float = 1.0,
             gate: float | None = None) -> None:
        """A note at time `at` (None: the next step's t). `gate`, in seconds,
        releases it on its own that long after; None leaves the gate open
        until `release`. A one-shot ignores `gate`: decay's end closes it."""
        self._queue(at, _FIRE, (float(velocity), gate))

    def release(self, at: float | None = None) -> None:
        """The gate closes at `at` (None: the next step's t). A one-shot
        ignores it, and so does a voice already releasing or at rest."""
        self._queue(at, _RELEASE, None)

    # ---- the level ----

    def peak(self, vel: float | None = None) -> float:
        """The peak for velocity `vel` (default: this note's)."""
        vs = self.velocity
        v = self.vel if vel is None else vel
        return self.amount * (1.0 - vs + vs * v)

    def level(self) -> float:
        """The level in note units (1 is the peak) at the current progress."""
        s, g = self.stage, shape(self.p, self.curve)
        if s == ATTACK:
            return self.y0 + (1.0 - self.y0) * g
        if s == HOLD:
            return 1.0
        if s == DECAY:
            return self.y0 + (self.sustain - self.y0) * g
        if s == SUSTAIN:
            return self.sustain
        if s == RELEASE:
            return self.y0 * (1.0 - g)
        return 0.0

    def _duration(self, stage: int) -> float:
        k = STAGES[stage]
        d = float(getattr(self, ATTR.get(k, k)))
        if stage == HOLD and d <= T_LO:
            return 0.0                    # hold's knob bottom is 0: an ADSR
        return max(d, 0.0)

    def _next(self) -> int:
        s = self.stage
        if s == ATTACK:
            return HOLD
        if s == HOLD:
            return DECAY
        if s == DECAY:
            # one-shot: the gate closes at decay's end
            return RELEASE if self.mode == ONE_SHOT else SUSTAIN
        return IDLE

    def _enter(self, stage: int, t: float, y0: float) -> None:
        self.stage, self.p, self.ref, self.y0 = stage, 0.0, t, y0

    def _advance(self, to: float, per_s: float) -> None:
        """Walk the stage boundaries from `ref` up to `to`. `per_s` is the
        stage times' units per second: 1 in seconds, bpm / 60 in beats."""
        if self.ref is None:
            self.ref = to
        while self.stage in _RUNNING:
            d = self._duration(self.stage)
            rate = per_s / d if d > 0.0 else 0.0           # progress per second
            end = self.ref + (1.0 - self.p) / rate if rate else self.ref
            if end > to:
                self.p += (to - self.ref) * rate
                break
            self.p = 1.0                                   # lands exactly on its target
            self._enter(self._next(), end, self.level())
        self.ref = to

    def _apply(self, t: float, kind: int, args) -> None:
        if kind == _FIRE:
            vel, gate = args
            new = self.peak(vel)
            if self.retrig == RESET or new <= 0.0:
                y0 = 0.0
            else:
                # legato: re-attack from the level showing, in the new note's units
                y0 = self.level() * self.peak() / new
            self.vel = vel
            self.note += 1
            self._enter(ATTACK, t, y0)
            if gate is not None and self.mode == GATE:
                # tokened with this note, so a later fire's note isn't cut short
                self.seq += 1
                self.events.append((t + max(float(gate), 0.0), self.seq, _RELEASE, self.note))
            return
        if args is not None and args != self.note:
            return                                         # an earlier note's auto-release
        if self.mode == ONE_SHOT or self.stage in (IDLE, RELEASE):
            return
        self._enter(RELEASE, t, self.level())

    def step(self, t: float, clock=None) -> float:
        """The output at time t: every queued event up to t in time order,
        the stage boundaries between them, then the level at t. `clock` is
        read only in beats mode, for its bpm."""
        if self.at is not None and t < self.at:
            t = self.at                                    # time never runs back
        per_s = getattr(clock, "bpm", 120.0) / 60.0 if self.sync == BEATS else 1.0
        # an unstamped event lands at this step's t
        self.events = [(t if e[0] is None else e[0],) + e[1:] for e in self.events]
        while self.events:
            # re-sorted each time: a fire may queue its own auto-release,
            # due within this same step
            self.events.sort(key=lambda e: (e[0], e[1]))
            if self.events[0][0] > t:
                break
            te, _, kind, args = self.events.pop(0)
            self._advance(te, per_s)
            self._apply(te, kind, args)
        self._advance(t, per_s)
        self.at = t
        self.out = self.level() * self.peak()
        return self.out

    # ---- the gate param ----

    def set_gate(self, on) -> None:
        """The `gate` toggle's write. Only an edge acts: a modulated toggle
        is written every frame (params.Param.apply)."""
        on = bool(on)
        if on and not self.held:
            self.held = True
            self.fire()
        elif not on and self.held:
            self.held = False
            self.release()


def label(n: int) -> str:
    """Envelope n's name, the LFOs' scheme ("LFO 1")."""
    return f"env {n}"


def _fmt_time(env: Envelope, zero: bool = False):
    def fmt(v: float) -> str:
        if zero and v <= T_LO:
            return "0"
        if env.sync == BEATS:
            return f"{v:.3g} beat"
        return f"{v * 1000:.0f} ms" if v < 1.0 else f"{v:.2f} s"
    return fmt


def declare(reg, n: int, env: Envelope) -> None:
    """Envelope n's params, ``env.<n>.<knob>`` in the ``env`` group: every
    knob modulatable and persistent (an LFO can own a decay, a preset
    carries the shape), `fire` a trigger and `gate` a modulatable toggle.
    `gate` is not persisted: a preset that loaded a held gate would fire a
    note and leave it hanging. The bank calls this once per voice; a
    second call is a no-op."""
    p, name = f"{GROUP}.{n}", label(n)
    if f"{p}.fire" in reg:
        return

    def put(attr, cast):
        return lambda v: setattr(env, attr, cast(v))

    def time(k, tip, zero=False):
        a = ATTR.get(k, k)
        reg.continuous(f"{p}.{k}", f"{name} {k}", lambda: getattr(env, a), put(a, float),
                       lo=T_LO, hi=T_HI, log=True, fmt=_fmt_time(env, zero), group=GROUP,
                       tip=tip + " Seconds, or beats when Sync is beats.")

    reg.enum(f"{p}.mode", f"{name} mode", lambda: env.mode, put("mode", int), MODES,
             group=GROUP,
             tip="Gate holds the sustain until the gate closes; one-shot runs attack, "
                 "hold and decay, then releases on its own.")
    time("attack", "The rise to the peak.")
    time("hold", "How long it stays at the peak; at the bottom it is 0, an ADSR.", zero=True)
    time("decay", "The fall from the peak to the sustain.")
    reg.continuous(f"{p}.sustain", f"{name} sustain", lambda: env.sustain,
                   put("sustain", float), lo=0.0, hi=1.0,
                   fmt=lambda v: f"sustain {v:.2f}", group=GROUP,
                   tip="The level held while the gate is open, a fraction of the peak.")
    time("release", "The fall to rest once the gate closes.")
    reg.continuous(f"{p}.curve", f"{name} curve", lambda: env.curve, put("curve", float),
                   lo=-1.0, hi=1.0, fmt=lambda v: f"curve {v:+.2f}", group=GROUP,
                   tip="One shape for every stage: below 0 snaps out of each corner, "
                       "above 0 starts slow; 0 is straight.")
    reg.enum(f"{p}.sync", f"{name} sync", lambda: env.sync, put("sync", int), SYNCS,
             group=GROUP,
             tip="The times in seconds, or in beats of the clock — a tempo change "
                 "mid-stage changes its rate from there.")
    reg.enum(f"{p}.retrig", f"{name} retrig", lambda: env.retrig, put("retrig", int),
             RETRIGS, group=GROUP,
             tip="A fire while it sounds: legato re-attacks from where it is, reset "
                 "starts again from 0.")
    reg.continuous(f"{p}.amount", f"{name} amount", lambda: env.amount,
                   put("amount", float), lo=0.0, hi=1.0,
                   fmt=lambda v: f"amount {v:.2f}", group=GROUP,
                   tip="The peak at full velocity; 0 is silent.")
    reg.continuous(f"{p}.velocity", f"{name} velocity", lambda: env.velocity,
                   put("velocity", float), lo=0.0, hi=1.0,
                   fmt=lambda v: f"vel {v:.2f}", group=GROUP,
                   tip="How much a fire's velocity scales the peak; 0 ignores it.")
    reg.trigger(f"{p}.fire", f"{name} fire", lambda: env.fire(), group=GROUP,
                tip="One note, gate open: it releases when the gate goes low, or on "
                    "its own in one-shot.")
    reg.toggle(f"{p}.gate", f"{name} gate", lambda: env.held, env.set_gate,
               group=GROUP, persist=False,
               tip="High fires with the gate open, low releases: hold a pad, or let "
                   "a performer own it.")


LANE_ENVS = (1, 2, 3, 4, 5)   # the sequencer's lane envelopes: always there (decision 3)


class Envelopes(Bank):
    """The envelope bank (modbank.Bank), published as the ``env`` source:
    the five lane envelopes, always, plus extras up to the cap."""

    SCHEME, LABEL, KEY = GROUP, "env", "envs"
    DEFAULT = LANE_ENVS
    REST = REST
    # what feeds a voice's node in the modulation patch: every knob, and
    # `fire` and `gate` too — a route onto ``env.2.fire`` (from ``seq:0``,
    # say) then lands before envelope 2 steps, so the note starts on this
    # frame's step rather than being held to the next one
    KNOBS = (*KNOBS, "fire", "gate")
    SHARED: ClassVar[dict[str, str]] = {}

    def __init__(self, ids=None):
        # the lane envelopes whatever `ids` says: a bank without them would
        # leave a lane firing nothing
        super().__init__(sorted({*LANE_ENVS, *(LANE_ENVS if ids is None else ids)}))

    def make(self) -> Envelope:
        return Envelope()

    def step_voice(self, env: Envelope, dt: float, t: float, clock) -> float:
        # an envelope is event-driven: its level is a closed form of t, so
        # it takes no dt (Envelope.step)
        return env.step(t, clock)

    def remove(self, n: int) -> bool:
        """An extra envelope goes (`Bank.remove`); a lane envelope, 1–5,
        never does — False, as for no such voice."""
        if n in LANE_ENVS:
            return False
        return super().remove(n)

    @classmethod
    def parse(cls, value) -> tuple[list[int], list[str]]:
        """A file's membership (`Bank.parse`), with the lane envelopes in
        it whatever the file says — a hand-edited ``[6]`` is 1–6."""
        ids, notes = super().parse(value)
        return sorted({*LANE_ENVS, *ids})[:cls.MAX], notes

    def fire(self, n: int, *, at: float | None = None, velocity: float = 1.0,
             gate: float | None = None) -> bool:
        """Envelope `n` (1-based) fires at `at` (Envelope.fire). False: no
        such envelope — a lane pointed at a removed extra fires nothing."""
        env = self.voice(n)
        if env is None:
            return False
        env.fire(at=at, velocity=velocity, gate=gate)
        return True

    def release(self, n: int, *, at: float | None = None) -> bool:
        """Envelope `n`'s gate closes at `at` (Envelope.release). False: no
        such envelope."""
        env = self.voice(n)
        if env is None:
            return False
        env.release(at=at)
        return True


def register(reg, envs: Envelopes, clock=None) -> None:
    """Every envelope's knobs as params in the ``env`` group (`declare`),
    the bank bound to `reg` so an extra added later declares the same way
    and one removed drops them. `clock` is unused (the voices read it at
    their step) and taken for the shape of lfo.register."""
    envs.bind(reg, declare)
