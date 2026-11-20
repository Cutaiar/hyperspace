"""Idle lights: a controller's LEDs animate while nobody is using it.

A `[[devices]]` MIDI entry opts in with an ``idle`` table (or just the name
of a light set)::

    [[devices]]
    role = "ddj-flx4"
    kind = "midi"
    profile = "generic"
    port = "DDJ-FLX4"
    idle = { lights = "ddj-flx4", after = 30, yield_to = ["rekordbox"] }

Nothing is toggled by hand. The animation starts on its own once nobody has
touched the device for ``after`` seconds and ends on the frame someone does
(`IdleLights.is_touch`: a fader twitching on its own is not a touch).
It never runs while an app named in ``yield_to`` is running, and it ends when
one starts. ``never`` lists lights it must leave alone
(``["note:0:11", "cc:0:2"]``: kind, 0-based channel, number).

**Sharing a controller with another app (Rekordbox).** CoreMIDI does not open
a port exclusively: both apps send to the device and both hear it. The LEDs
are what they share. A light shows whichever message reached it last, and
neither app can see what the other sent, so this module cannot save Rekordbox's
lights and put them back. So it keeps out of the way instead:

  1. It runs only while no ``yield_to`` app runs (a background look at the
     process list every `LOOK_S`), or with ``yield_to = []`` alongside it,
     on the lights ``never`` leaves it.
  2. A touch on the device ends it on that frame.
  3. When it ends it sends every light it drew dark (`IdleLights.tick`), so no
     stale frame is left. Rekordbox lights its own as its state changes; on the
     FLX4 a pad-mode press makes it repaint the pads at once. A desk whose
     profile owns its lights (the APC40) redraws its own state after the dark.

What `tools/flx4_led_probe.py` found on the owner's FLX4 (2026-11-19):

  * **The addresses** (Mixxx's community mapping, Pioneer-DDJ-FLX4.midi.xml)
    light what they name, but for reloop (0x4D): the FLX4 has no such button,
    so it is not in the set. Deck 1's level meter did not light the first time,
    sent while the FLX4 was still coming out of its own demo show; a re-run
    (`--lights "level meter"`) lit both meters. Every light in `flx4()` is confirmed.
  * **Pads** show only the hot-cue block (notes 0-7) in hot-cue mode.
  * **Left alone**, the FLX4 plays a demo show of its own and its crossfader
    twitches (546 messages in 120 s): hence `is_touch`.
  * **Rekordbox starting**: its process showed 8 s after launch, the device
    first heard from 22 s, and its lights taken over at 29.5 s. Yielding (a look
    every `LOOK_S`) darkens about 20 s before Rekordbox writes anything, so the
    dark never lands on its lights.
  * **Rekordbox running** lets the device stay silent: no keepalive answers come
    back, so only `yield_to` keeps the animation off while it runs.
    It repaints its full last state when it connects, and after that only what
    changes (play, cue, a meter, a pad, the SHIFT layer while SHIFT is held),
    plus a blinking play. Sent dark, it relit play, the hot cues and release FX
    within seconds; anything else written over stays that way until its own
    state changes. That is why the animation yields to it by default and darkens
    what it drew.

**Patterns.** ``pattern`` is one name, a list played in turn (each for
``each`` seconds, and the next idle spell starts on the one after), or
``"all"``. ``wave`` and ``breathe`` are a brightness per light; the rest are
`idle_effects`: whole-desk animations (wash, ripple, wobble, heat, fireworks,
hearts, heartbeat, zoom; ``shape`` names zoom's polytope) that colour the
APC40's clip grid and run as shapes on a one-colour device. ``dither = true``
spreads each light's threshold over frames, so a level between reads as a
duty cycle (software dimming; whether it reads dim or flickers is a check by
eye at the desk).

Imports nothing from the package but `idle_effects` (which imports only
`geometry`, and that only for a zoom).
"""

from __future__ import annotations

import math
import os
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from . import idle_effects

__all__ = ["AFTER_S", "BURST_N", "BURST_S", "EACH_S", "FLX4_NAMES", "FPS", "JITTER", "LOOK_S", "PAIR_S", "PATTERNS", "SETS",
           "AppWatch", "IdleLights", "Light", "flx4", "from_entry", "parse_never", "pattern_names"]

AFTER_S = 30.0      # untouched this long, it starts
FPS = 30.0          # frames sent a second, at most (only lights that changed)
LOOK_S = 1.0        # the process list is read this often, off the frame thread
JITTER = 3          # a continuous control this many steps (of 127) from its last value moved
BURST_N, BURST_S = 6, 0.5   # this many messages from one control this fast: it moved
PAIR_S = 0.05       # a 14-bit LSB follows its MSB at once, within this
EACH_S = 20.0       # a list of patterns: each plays this long
_BAYER = (0.125, 0.625, 0.375, 0.875)   # `dither`'s threshold offsets, a light's phase a frame


@dataclass(frozen=True)
class Light:
    """One LED: the message that sets it, where it sits on the device (for a
    pattern that sweeps), and the values it takes, darkest first. A ``cc``
    light with ``levels`` None takes any value 0..127 (a level meter).
    ``colours`` names the values of a light that shows colour (the APC40's
    clip pads), for an `idle_effects` effect that says which."""

    kind: str                   # "note" (velocity) or "cc" (value)
    channel: int                # 0-based
    number: int
    x: float = 0.0
    y: float = 0.0
    levels: tuple[int, ...] | None = (0, 127)
    colours: tuple[tuple[str, int], ...] = ()

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.kind, self.channel, self.number)

    def value(self, b: float, dither: float | None = None) -> int:
        """The value that shows brightness `b` (0..1) on this light; `dither`
        (0..1, this frame's phase) moves where each step falls."""
        b = 0.0 if not b > 0.0 else min(1.0, b)     # NaN reads dark
        if self.levels is None:
            return round(b * 127)
        n = len(self.levels)
        i = int(b * n) if dither is None else int(b * (n - 1) + dither)
        return self.levels[min(n - 1, i)]

    def show(self, level: float, colour: str | None = None, dither: float | None = None) -> int:
        """The value for an effect's (level, colour): a colour light lit in
        that colour above `idle_effects.THRESHOLD`, any other the level."""
        if colour is not None and self.colours:
            thr = idle_effects.THRESHOLD if dither is None else 1.0 - dither
            return dict(self.colours).get(colour, 0) if level > thr else 0
        return self.value(level, dither)


# ---- the light sets ----

def _flx4_named() -> list[tuple[str, Light]]:
    """The DDJ-FLX4's lights with their names (Mixxx's mapping, each confirmed on
    the owner's unit by tools/flx4_led_probe.py, 2026-11-19). Deck 1 is channel 0, deck 2 channel 1; the pads are on channel 7
    (deck 1) and 9 (deck 2), one note block per pad mode, SHIFT's on 8 and 10.
    Only the hot-cue block (notes 0-7, the mode it powers up in) is drawn:
    another mode's block would light pads that mode shows. x runs left to
    right across both decks, y top to bottom."""
    out: list[tuple[str, Light]] = []
    for deck, ch, pad_ch, x0 in ((1, 0, 7, 0.0), (2, 1, 9, 6.0)):
        d = f"deck {deck}"
        out.append((f"{d} level meter", Light("cc", ch, 0x02, x0 + 4.5, 0.0, None)))
        for i in range(8):                                   # pads 1-4 over 5-8
            out.append((f"{d} pad {i + 1}", Light("note", pad_ch, i, x0 + i % 4, 1.0 + i // 4)))
        for name, n, x, y in (("loop in", 0x10, 0.0, 3.0), ("loop out", 0x11, 1.0, 3.0),
                              ("headphone cue", 0x54, 4.5, 2.0),
                              ("sync", 0x58, 3.0, 4.0), ("cue", 0x0C, 0.0, 4.0),
                              ("play / pause", 0x0B, 1.0, 4.0)):
            out.append((f"{d} {name}", Light("note", ch, n, x0 + x, y)))
    return out


def flx4() -> tuple[Light, ...]:
    """The DDJ-FLX4's lights (`_flx4_named`)."""
    return tuple(lt for _name, lt in _flx4_named())


FLX4_NAMES: dict[tuple[str, int, int], str] = {lt.key: name for name, lt in _flx4_named()}


# the APC40's button field below its clip grid, top to bottom (apc40.py's
# N_CLIPSTOP, N_SELECT, N_ACTIVATOR, N_SOLO, N_ARM) and each row's centre in
# layout units (apc40.LAYOUT; tests/test_idle_lights.py holds the two together)
_APC40_ROWS = ((0x34, 5.8), (0x33, 6.9), (0x32, 8.1), (0x31, 9.1), (0x30, 10.1))
_APC40_GRID = (("green", 1), ("yellow", 5), ("red", 3))     # apc40.GREEN, YELLOW, RED


def _apc40() -> tuple[Light, ...]:
    """Every APC40 button with a light, at its centre on the face
    (apc40.LAYOUT, x right, y down): the clip grid (notes 0x35-0x39, a track
    a channel) in green, yellow, red as they brighten, and colours for an
    effect; the five button rows under it; the scene launch column, STOP ALL
    CLIPS and MASTER select, one colour each. Not the knob rings: a ring
    value re-bases its knob (`idle_effects`)."""
    grid = (0, *(v for _c, v in _APC40_GRID))
    out = [Light("note", track, 0x35 + row, track + 0.5, row + 0.5, grid, _APC40_GRID)
           for row in range(5) for track in range(8)]
    out += [Light("note", track, note, track + 0.5, y, (0, 1))
            for note, y in _APC40_ROWS for track in range(8)]
    out += [Light("note", 0, 0x52 + row, 8.7, row + 0.5, (0, 1)) for row in range(5)]
    out += [Light("note", 0, 0x51, 8.7, 5.8, (0, 1)), Light("note", 0, 0x50, 8.7, 6.9, (0, 1))]
    return tuple(out)


SETS: dict[str, Callable[[], tuple[Light, ...]]] = {"ddj-flx4": flx4, "apc40": _apc40}


# ---- the patterns: (light, seconds) → brightness 0..1 ----

def _wave(light: Light, t: float) -> float:
    """A band of light sweeping left to right, a lap every 2.4 s, a little
    late on each lower row."""
    phase = (t / 2.4 - light.x / 12.0 - light.y / 24.0) % 1.0
    return max(0.0, 1.0 - abs(phase - 0.5) * 5.0)


def _breathe(light: Light, t: float) -> float:
    """Every light swells and fades together, every 4 s."""
    del light
    return 0.5 - 0.5 * math.cos(2.0 * math.pi * t / 4.0)


PATTERNS: dict[str, Callable[[Light, float], float]] = {"wave": _wave, "breathe": _breathe}


def pattern_names() -> tuple[str, ...]:
    """Every pattern a config can name: the effects, then the per-light ones."""
    return (*idle_effects.EFFECTS, *PATTERNS)


# ---- is another app running ----

def _process_names() -> list[str]:
    """Every running process's executable name, lower case ("" on failure)."""
    try:
        out = subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True,
                             timeout=2.0, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [os.path.basename(line.strip()).lower() for line in out.splitlines()]


class AppWatch:
    """Whether any app named in `names` is running, read off the frame thread:
    a daemon thread looks at the process list every `LOOK_S`, and `running`
    is a plain read. A name matches a process whose name contains it, ignoring
    case ("rekordbox" matches "rekordbox" and "rekordboxAgent"). `look` is the
    process lister, for tests; `start=False` leaves the thread off (`check`
    then looks once, on the caller's thread)."""

    def __init__(self, names: Iterable[str], *, look: Callable[[], list[str]] = _process_names,
                 start: bool = True):
        self.names = tuple(n.lower() for n in names if n)
        self._look = look
        self.running = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if self.names and start:
            self._thread = threading.Thread(target=self._loop, name="idle-lights-watch",
                                            daemon=True)
            self._thread.start()

    def check(self) -> bool:
        procs = self._look()
        self.running = any(n in p for p in procs for n in self.names)
        return self.running

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.check()
            self._stop.wait(LOOK_S)

    def stop(self) -> None:
        self._stop.set()


# ---- the animator ----

Message = tuple[str, int, int, int]     # (kind, channel, number, value)


@dataclass
class IdleLights:
    """One desk's idle animation. The desk calls `touched` when the device
    sends anything and `tick` every frame, and sends what `tick` returns.
    `tick` says, on the frame it ends, so the desk can redraw its own lights."""

    lights: tuple[Light, ...]
    after: float = AFTER_S
    pattern: Callable[[Light, float], float] = _wave
    watch: AppWatch | None = None
    # the pattern by its PATTERNS name, looked up each frame, so a hot reload's edit
    # to it is drawn; `pattern` is used when this is None (a test's own function)
    pattern_name: str | None = None
    # several patterns played in turn, `each` seconds apiece (overrides `pattern_name`);
    # a name may be an `idle_effects` effect, made fresh each time it comes up
    names: tuple[str, ...] = ()
    each: float = EACH_S
    shape: str = "Tesseract"            # the zoom effect's polytope
    dither: bool = False
    clock: Callable[[], float] = time.monotonic
    running: bool = False
    ended: bool = False                 # `tick` just ended it: the desk redraws
    _last_touch: float = field(default=0.0, init=False)
    _started: float = field(default=0.0, init=False)
    _next_frame: float = field(default=0.0, init=False)
    _sent: dict[tuple[str, int, int], int] = field(default_factory=dict, init=False)
    # `is_touch`'s memory: each continuous control's last value, and its recent message times
    _cc_last: dict[tuple[str, int, int], int] = field(default_factory=dict, init=False)
    _bursts: dict[tuple[str, int, int], deque] = field(default_factory=dict, init=False)
    _prev: tuple[tuple[str, int, int], float] | None = field(default=None, init=False)
    _touch_due: bool = field(default=False, init=False)   # a touch `tick` has not seen
    _turn: int = field(default=0, init=False)             # where the list starts next spell
    _at: int = field(default=0, init=False)               # the list's entry playing now
    _effect: tuple[int, str, idle_effects.Effect] | None = field(default=None, init=False)
    _frames: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._last_touch = self.clock()

    @property
    def yielding(self) -> bool:
        """An app it gives way to is running."""
        return self.watch is not None and self.watch.running

    def touched(self) -> None:
        self._last_touch, self._touch_due = self.clock(), True

    def is_touch(self, kind: str, channel: int, number: int, value: int) -> bool:
        """Is a message from the device a person's touch? A note, a SysEx and anything
        else is. A continuous control (``cc``, ``pitch`` with its value in 0..127) is
        not when it is only twitching. The FLX4 probe (2026-11-19) heard its crossfader
        send 546 messages in 120 s with no hand on it, its 14-bit pair (CC 31 / 63
        on channel 6): the MSB wandering a step at a time, the LSB anywhere. So:

          * an LSB never is: CC 32-63 arriving straight after its MSB, CC n - 32,
            within `PAIR_S`. Not merely 32 apart: the APC40's track knobs
            (CC 48-55) are knobs of their own, 32 above its device knobs;
          * a value `JITTER` or more from the control's last one is;
          * so are `BURST_N` messages from one control inside `BURST_S`: a jog's
            relative ticks repeat one value, and a quick fader move is fast.

        A control's first message only sets where it is."""
        key, now = (kind, channel, number), self.clock()
        prev, self._prev = self._prev, (key, now)
        if kind not in ("cc", "pitch"):
            return True
        if (kind == "cc" and 32 <= number < 64 and prev is not None
                and prev[0] == ("cc", channel, number - 32) and now - prev[1] <= PAIR_S):
            return False
        last = self._cc_last.get(key)
        self._cc_last[key] = value
        times = self._bursts.setdefault(key, deque(maxlen=BURST_N))
        times.append(now)
        if len(times) == BURST_N and now - times[0] <= BURST_S:
            return True
        return last is not None and abs(value - last) >= JITTER

    def forget_sent(self) -> None:
        """The device came back (a reconnect): every light is sent again."""
        self._sent.clear()

    def tick(self) -> list[Message]:
        """This frame's messages: a frame of the pattern (only lights that
        changed, at most `FPS` a second) while it runs, every light it drew
        dark on the frame it ends, else nothing."""
        now = self.clock()
        self.ended = False
        # a touch since the last frame ends it, even with `after` 0
        touch, self._touch_due = self._touch_due, False
        want = not touch and not self.yielding and now - self._last_touch >= self.after
        if self.running and not want:
            return self._end()
        if not want:
            return []
        if not self.running:
            self.running, self._started, self._next_frame = True, now, now
            self._effect = None
        if now < self._next_frame:
            return []
        self._next_frame = now + 1.0 / FPS
        self._frames += 1
        t = now - self._started
        out: list[Message] = []
        for i, (light, (level, colour)) in enumerate(zip(self.lights, self._levels(t))):
            d = _BAYER[(self._frames + i) % 4] if self.dither else None
            v = light.show(level, colour, d)
            if self._sent.get(light.key) != v:
                self._sent[light.key] = v
                out.append((*light.key, v))
        return out

    def _levels(self, t: float) -> list[tuple[float, str | None]]:
        """This frame's (level, colour) per light, `t` seconds into the spell."""
        names = self.names or ((self.pattern_name,) if self.pattern_name else ())
        name, start = (names[0] if names else ""), 0.0
        if len(names) > 1:
            turn = int(t // self.each)
            self._at = (self._turn + turn) % len(names)
            name, start = names[self._at], turn * self.each
        if name in idle_effects.EFFECTS:
            if self._effect is None or self._effect[:2] != (self._at, name):
                self._effect = (self._at, name, idle_effects.make(name, self.lights, shape=self.shape))
            return self._effect[2].frame(t - start)
        self._effect = None
        pattern = PATTERNS.get(name, self.pattern)
        return [(pattern(light, t), None) for light in self.lights]

    def _end(self) -> list[Message]:
        self.running, self.ended = False, True
        self._turn, self._effect = self._at + 1, None    # the next spell plays the next one
        out = [(*key, 0) for key, v in self._sent.items() if v != 0]
        self._sent.clear()
        return out

    def end_now(self) -> list[Message]:
        """It ends regardless (the desk is closing): every light it drew, dark."""
        if not self.running:
            return []
        msgs = self._end()
        self.ended = False
        return msgs

    def close(self) -> None:
        if self.watch is not None:
            self.watch.stop()


def parse_never(items: Iterable[str]) -> set[tuple[str, int, int]]:
    """``"note:0:11"`` (or ``"note@ddj-flx4:0:11"``, as a row's source names it)
    → ("note", 0, 11). A malformed item raises ValueError naming it."""
    out = set()
    for item in items:
        parts = str(item).split(":")
        kind = parts[0].split("@", 1)[0]
        if len(parts) != 3 or kind not in ("note", "cc"):
            raise ValueError(f"idle.never: {item!r} is not kind:channel:number "
                             "(kind note or cc)")
        try:
            out.add((kind, int(parts[1]), int(parts[2])))
        except ValueError:
            raise ValueError(f"idle.never: {item!r} is not kind:channel:number") from None
    return out


def from_entry(idle, *, default_set: str | None = None, start_watch: bool = True,
               clock: Callable[[], float] = time.monotonic) -> IdleLights | None:
    """The animator a `[[devices]]` entry's ``idle`` asks for, or None.
    ``idle`` is absent / false (none), true (the profile's own set,
    `default_set`), a set's name, or a table: ``lights`` (a set's name),
    ``after`` (seconds), ``pattern`` (a name, a list, or ``"all"``),
    ``each`` (seconds a listed pattern plays), ``shape`` (zoom's polytope),
    ``dither``, ``yield_to`` (app names; default ``["rekordbox"]``) and
    ``never``. A bad value raises ValueError naming it."""
    if idle is None or idle is False:
        return None
    if idle is True:
        idle = {}
    if isinstance(idle, str):
        idle = {"lights": idle}
    if not isinstance(idle, dict):
        # a config.toml mistake, read as the entry's error line like every other
        raise ValueError(f"idle: {idle!r} is not a table, a light set's name or true")  # noqa: TRY004
    name = idle.get("lights", default_set)
    if name not in SETS:
        raise ValueError(f"idle.lights: {name!r} is not one of {', '.join(SETS)}")
    pattern = idle.get("pattern", "wave")
    names = pattern_names() if pattern == "all" else (pattern,) if isinstance(pattern, str) else pattern
    if not isinstance(names, (list, tuple)) or not names:
        raise ValueError(f"idle.pattern: {pattern!r} is not a pattern's name, a list of them or 'all'")
    for n in names:
        if n not in pattern_names():
            raise ValueError(f"idle.pattern: {n!r} is not one of {', '.join(pattern_names())}")
    each = float(idle.get("each", EACH_S))
    if not each > 0.0:
        raise ValueError(f"idle.each: {idle.get('each')!r} is not a number of seconds")
    shape = str(idle.get("shape", "Tesseract"))
    if "zoom" in names:
        try:
            idle_effects.shape_vertices(shape)
        except KeyError:
            raise ValueError(f"idle.shape: {shape!r} is not a shape's name") from None
    after = float(idle.get("after", AFTER_S))
    if not after >= 0.0:
        raise ValueError(f"idle.after: {idle.get('after')!r} is not a number of seconds")
    yield_to = idle.get("yield_to", ["rekordbox"])
    if isinstance(yield_to, str):
        yield_to = [yield_to]
    never = parse_never(idle.get("never", ()))
    lights = tuple(lt for lt in SETS[name]() if lt.key not in never)
    watch = AppWatch(yield_to, start=start_watch) if yield_to else None
    first = names[0]
    return IdleLights(lights, after=after, pattern=PATTERNS.get(first, _wave), watch=watch, clock=clock,
                      pattern_name=first, names=tuple(names) if len(names) > 1 else (),
                      each=each, shape=shape, dither=bool(idle.get("dither", False)))
