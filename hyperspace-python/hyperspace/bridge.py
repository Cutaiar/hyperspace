"""DAW bridge — the analyzer's lanes out as MIDI, external MIDI lanes in.

Plan 05 task 1, plan 07 WP4c, BLUEPRINT §3.6: the pluggable edge that
keeps FL Studio (or another Hyperspace, a lighting rig) connectable
without the core knowing. Off by default; ``[bridge] enabled = true`` in
config.toml opens it. Nothing in the core imports this module — app.py
attaches it the way it attaches midi.py — and absent it costs nothing.

Out. Every frame the lanes go to a virtual MIDI port (IAC on macOS,
loopMIDI on Windows; the OS makes the port, the bridge opens it by a
substring of its name — `out`). One encoding per bridge:

  pitch   lane i → pitch bend on channel `channel + i`. Natively 14-bit,
          16 channels for the 16-lane cap, and a DAW links to it with no
          script. The default.
  cc14    lane i → CC `cc + i` (MSB) then CC `cc + i + 32` (LSB), both
          on `channel` — the MIDI 1.0 14-bit pair, 32 − cc lanes at most.
          A receiver that reads the MSB alone gets 7-bit motion (FL's
          Link to controller does); the LSB is for one that fuses pairs
          (another Hyperspace, plan 05's FL script).

Value mapping, exactly: an analyzer lane is normalized as routing.py
does, ``u = lane / CEIL``, then clamped to [0, 1] and quantized
``v = round(u · 16383)`` — a lane at the asymptote is 16383, nominal
(1.0) is round(16383 / CEIL), and the analyzer's lanes are in [0, CEIL)
so the clamp never bites. A param lane sends the param's effective norm
(`eff_norm`: base + modulation, already in [0, 1]) through the same
quantizer, one frame behind the registry (the bridge runs before
`reg.apply()`). Pitch bend carries v − 8192.

`send` says what goes out, in lane order: "lane:*" (every analyzer lane,
band order), "lane:3", "param:view.bright". Slot k is the k-th entry
once the stars expand, so the default ["lane:*"] puts the analyzer's
lane i on the bridge's lane i. With no analyzer running (audio off) the
lane slots send 0 once and fall silent. Slots past the encoding's room
(16 − channel, or 32 − cc) are dropped.

Rate-limited and change-gated: a slot sends at most `rate` times a
second and only when its 14-bit value changed, so idle lanes go quiet
and a change inside the window goes out at the window's end — always
the latest value, never a stale one. A reconnect resends everything.

In. The same message forms on `in` become the ``ext`` source vector
handed to ``Router.feed("ext", …)`` each frame, so ``ext:<i>`` routes
(routing.py) modulate any param — FL automation or another Hyperspace
drives this one. Both forms are always decoded: pitch bend on channel
`channel + i` and the CC pair `cc + i` / `cc + i + 32` on `channel` both
land in ext lane i as ``u = v / 16383``, so the sender's ``lane:i`` and
this end's ``ext:i`` read the same u and a route keeps its depth when
it moves across. Pairs: each half is latched and the lane reads
``(msb << 7) | lsb`` after either — a pair in either order, or an MSB
alone from a 7-bit sender, lands the same (MIDI 1.0's "MSB zeroes the
LSB" is deliberately not applied). A poll drains the whole pending queue
before the router reads the vector, so it never sees half a pair unless
the halves straddle a frame; then for one frame, off by < 1/128. The
vector is `in_lanes` long, not a source until the first message arrives,
and let go (``feed("ext", None)``) when the port vanishes.

Don't open `in` on the bus `out` sends to: IAC echoes, and the lanes
would come straight back as ext lanes. Use two buses.

MIDI clock out (plan 05: 24 ppqn from the DJ Link BPM, start/stop with
beat-grid lock) waits for a beat source; nothing here derives ticks yet.

**Sinks (plan 27 B3).** On the device registry the bridge is one device
with two halves (devices.BridgeDevice): its `receive` stays a source (the
``ext`` vector, with its labels and rests published, `publish`) and its out
half is a *sink*: what goes out is the session's sink rows on the
bridge's role (routing.py, ``param:view.bright → bridge:3``, `sink_values`),
read after ``reg.apply()`` — so a param lane carries this frame's effective
value, no longer one frame behind — and sent through `send_values`. The
`send` list above is what the rows are translated from, once
(`routing.sink_rows_from_send`); a `Bridge` made on its own (the tests, a
tool) still sends it through `step` / `transmit`.

The outbound gate (`Sender`: quantise, change-gate, rate-limit, encode, per
channel) and a named output port that is made virtual when absent and
looked for again when it goes (`OutPort`) are this module's, shared with
the `midi-out` sink (devices.MidiOutDevice) — the port the hands' DAW
messages go out on (the `hands-daw` entry), which hands/core.py no longer
opens itself.
"""

from __future__ import annotations

import sys
import time

import mido
import numpy as np

from .bands import CEIL
from .config import DEFAULTS
from .midi import RECONNECT_S, Ports, retry_after
from .params import Kind, Registry

FULL = 16383                    # 14 bits
ENCODINGS = ("pitch", "cc14")
LSB_OFFSET = 32                 # MIDI 1.0: CC n's LSB is CC n + 32, n in 0–31


# ------------------------------------------------------------ the wire

def quantize(u: float) -> int:
    """A normalized reading → its 14-bit value."""
    return round(min(max(float(u), 0.0), 1.0) * FULL)


def encode(v: int, lane: int, encoding: str, channel: int, cc: int) -> list[mido.Message]:
    """The message(s) that carry 14-bit `v` on bridge lane `lane`."""
    if encoding == "pitch":
        return [mido.Message("pitchwheel", channel=channel + lane, pitch=v - 8192)]
    n = cc + lane
    return [mido.Message("control_change", channel=channel, control=n, value=v >> 7),
            mido.Message("control_change", channel=channel, control=n + LSB_OFFSET,
                         value=v & 0x7F)]


def capacity(encoding: str, channel: int, cc: int) -> int:
    """How many lanes an encoding has room for from its first channel / CC."""
    return 16 - channel if encoding == "pitch" else LSB_OFFSET - cc


class Sender:
    """The outbound gate, per channel: a reading in [0, 1] is quantised to
    14 bits and goes out only when its value changed, at most `rate` times
    a second — a change inside the window goes out at the window's end,
    always the latest value. `reset` makes every channel send again (a
    reconnect: the far end starts blank). Channels past the encoding's
    room are dropped."""

    def __init__(self, encoding: str = "pitch", channel: int = 0, cc: int = 16,
                 rate: float = 100.0, clock=time.monotonic, *, who: str = "bridge"):
        self.encoding = str(encoding)
        if self.encoding not in ENCODINGS:
            raise ValueError(f"{who}: encoding {self.encoding!r} is not one of {ENCODINGS}")
        self.channel, self.cc = int(channel), int(cc)
        if not 0 <= self.channel < 16 or not 0 <= self.cc < LSB_OFFSET:
            raise ValueError(f"{who}: channel {self.channel} / cc {self.cc} out of range")
        self.rate = float(rate)
        self.clock = clock
        self._last_v: dict[int, int] = {}       # per channel: the value on the wire
        self._last_t: dict[int, float] = {}     # per channel: when it went out

    @classmethod
    def of(cls, cfg: dict | None, clock=time.monotonic, *, who: str = "bridge") -> Sender:
        """One from a config table's encoding / channel / cc / rate (the
        `[bridge]` defaults fill what it leaves out)."""
        c = {**DEFAULTS["bridge"], **(cfg or {})}
        return cls(c["encoding"], c["channel"], c["cc"], c["rate"], clock, who=who)

    @property
    def room(self) -> int:
        return capacity(self.encoding, self.channel, self.cc)

    def reset(self) -> None:
        self._last_v.clear()

    def messages(self, values) -> list[mido.Message]:
        """What goes out now for `values` — a list (channel k = index k) or
        a dict channel → reading — in channel order."""
        items = values.items() if isinstance(values, dict) else enumerate(values)
        now = self.clock()
        period = 1.0 / self.rate if self.rate > 0 else 0.0
        out: list[mido.Message] = []
        for k, u in sorted(items):
            if not 0 <= k < self.room:
                continue
            v = quantize(u)
            if v == self._last_v.get(k) or now - self._last_t.get(k, float("-inf")) < period:
                continue
            out += encode(v, k, self.encoding, self.channel, self.cc)
            self._last_v[k], self._last_t[k] = v, now
        return out


def _open_out(name: str, *, virtual: bool = True) -> tuple:
    """(port, error, made_virtual): an existing output port whose name
    holds `name` (any case), else — when `virtual` — a new virtual one
    called `name`. (None, why, False) when there is no such port or the
    backend refuses. (Moved here from hands/core.py, plan 27 B3.)"""
    if not name:
        return None, "", False
    try:
        hit = next((n for n in mido.get_output_names() if name.lower() in n.lower()), None)
        if hit:
            return mido.open_output(hit), "", False
        if not virtual:
            return None, f"out {name!r}: no such port", False
        return mido.open_output(name, virtual=True), "", True
    except Exception as e:  # noqa: BLE001 — no backend / virtual ports unsupported
        return None, f"out {name!r}: {e}"[:120], False


def _close_port(port) -> None:
    """Best effort: a dropped or finished port is closed, so a virtual one
    is unregistered rather than left for the next open to find."""
    if port is not None and hasattr(port, "close"):
        try:
            port.close()
        except Exception:  # noqa: BLE001, S110
            pass


class OutPort:
    """One MIDI output found by name — an existing port by substring, else
    a virtual port of that name (`virtual`) — and looked for again on
    midi.Ports' schedule when it fails (`retry_after`: RECONNECT_S for
    RECONNECT_FAST looks, then RECONNECT_SLOW_S; back to the start once it
    opens). After a loss only a port that is back is joined — or, when the
    first open had to make a virtual one, a new virtual one. What the hands'
    DAW out did inside hands/core.py until plan 27 B3, now the `midi-out`
    sink's (devices.MidiOutDevice). An open that fails is said once on
    stderr, prefixed with `who`. `out` may be injected (a test's fake): it
    is the caller's, never closed and never reopened."""

    def __init__(self, name: str, *, virtual: bool = True, out=None, clock=time.monotonic,
                 who: str = "midi-out"):
        self.match = "" if out is not None else str(name or "")
        self.virtual_ok = bool(virtual)
        self.clock = clock
        self.who = who
        self.out = out
        self.error = ""
        self._virtual: bool | None = None       # what the first open made
        self._next = 0.0
        self.misses = 0
        self.lost = False                       # a port that worked went away

    @property
    def on(self) -> bool:
        return self.out is not None

    @property
    def name(self) -> str:
        return (getattr(self.out, "name", "") or "") if self.out is not None else ""

    def open(self) -> bool:
        """Look for the port now; True when one opened."""
        self.misses += 1
        self._next = self.clock() + retry_after(self.misses)
        self.out, err, virtual = _open_out(
            self.match, virtual=self.virtual_ok and self._virtual is not False)
        if err and err != self.error:
            print(f"{self.who}: {err}", file=sys.stderr)
        self.error = err
        if self.out is None:
            return False
        self.misses = 0
        if self._virtual is None:
            self._virtual = virtual
        self.lost = False
        return True

    def retry(self) -> bool:
        """Look again when due; True the frame the port comes (back)."""
        if self.out is not None or not self.match or self.clock() < self._next:
            return False
        return self.open()

    def send(self, msg) -> bool:
        """One message out; False when there is no port or it went away
        under the send (then it is let go of, `error` says why, and the
        next look is RECONNECT_S away)."""
        if self.out is None:
            return False
        try:
            self.out.send(msg)
            return True
        except Exception as e:  # noqa: BLE001 — port yanked mid-frame
            self.error = f"send: {e}"[:120]
            if self.match:
                _close_port(self.out)
            self.out = None
            self.lost = True
            self._next = self.clock() + RECONNECT_S
            return False

    def close(self) -> None:
        if self.match:
            _close_port(self.out)
        self.out = None


class Decoder:
    """The 14-bit registers behind the ext vector, fed one message at a time."""

    def __init__(self, n: int, channel: int, cc: int):
        self.n, self.channel, self.cc = n, channel, cc
        self.msb = [0] * n
        self.lsb = [0] * n
        self.values = np.zeros(n)
        self.live = False       # a message has arrived: the vector is a source

    def feed(self, msg) -> int | None:
        """Take one message; the lane it landed on, or None."""
        t = msg.type
        if t == "pitchwheel":
            i = msg.channel - self.channel
            if not 0 <= i < self.n:
                return None
            v = msg.pitch + 8192
            self.msb[i], self.lsb[i] = v >> 7, v & 0x7F
        elif t == "control_change" and msg.channel == self.channel:
            n = msg.control
            i = n - self.cc
            if 0 <= i < self.n and n < LSB_OFFSET:
                self.msb[i] = msg.value
            elif 0 <= i - LSB_OFFSET < self.n and n >= LSB_OFFSET:
                i -= LSB_OFFSET
                self.lsb[i] = msg.value
            else:
                return None
        else:
            return None
        self.values[i] = ((self.msb[i] << 7) | self.lsb[i]) / FULL
        self.live = True
        return i


# ---------------------------------------------------------------- bridge

class Bridge:
    """Lanes out and ext lanes in over one pair of virtual ports.

    `cfg` is the ``[bridge]`` section (config.py's defaults fill what it
    leaves out). `inp`/`out` may be injected (tests: fakes with
    iter_pending() and send()); otherwise the ports are found by name and
    reopened on their own (midi.Ports).
    """

    def __init__(self, registry: Registry, cfg: dict | None = None, *,
                 inp=None, out=None, clock=time.monotonic):
        self.reg = registry
        c = {**DEFAULTS["bridge"], **(cfg or {})}
        self.sender = Sender.of(c, clock)        # the outbound gate (raises on a bad encoding)
        self.encoding, self.channel, self.cc = (self.sender.encoding, self.sender.channel,
                                                self.sender.cc)
        self.rate = self.sender.rate
        self.send_spec = [str(s) for s in c["send"]]
        self.clock = clock
        self.ports = Ports(c["in"] or None, c["out"] or None, inp=inp, out=out, clock=clock)
        self.decoder = Decoder(int(c["in_lanes"]), self.channel, self.cc)
        self._n = 0                              # the analyzer's lane count, last seen
        self._fed = False                        # the router holds our vector
        self.sent = 0                            # messages out — counted; no panel shows it yet
        if not self.ports.injected and self.ports.connect():
            self._connected()

    # ---- ports ----

    @property
    def on(self) -> bool:
        return self.ports.on

    @property
    def name(self) -> str:
        return self.ports.name

    @property
    def error(self) -> str:
        return self.ports.error

    @property
    def room(self) -> int:
        """How many lanes the encoding can carry."""
        return capacity(self.encoding, self.channel, self.cc)

    @property
    def labels(self) -> list[str]:
        """The ext lanes' names, as routes and the ROUTING page show them."""
        return [f"ext {i}" for i in range(self.decoder.n)]

    def _connected(self) -> None:
        self.sender.reset()                         # the far end starts blank: resend all
        sides = [f"{k} {n}" for k, n in (("out", self.ports.out_name), ("in", self.ports.in_name))
                 if n]
        print(f"bridge: {', '.join(sides)} ({self.encoding}, {self.room} lanes)",
              file=sys.stderr)

    def close(self) -> None:
        self.ports.close()

    # ---- per frame ----

    def step(self, analyzer, router=None) -> None:
        """Once a frame, a bridge on its own: drain the input into the
        router's ext vector, send the `send` list's lanes. `analyzer` is
        the live one or None while no audio source runs. (On the device
        registry the halves run apart: `reconnect` in the scene-setter
        slot, `receive` + `publish` in the feed slot, `send_values` from
        the sink rows after ``reg.apply()`` — devices.BridgeDevice.)"""
        self.reconnect()
        if router is not None:
            self.receive(router)
        self.transmit(analyzer)

    def reconnect(self) -> bool:
        """The ports looked for again when due; True the frame they come
        back (every lane then resends)."""
        if self.ports.retry():
            self._connected()
            return True
        return False

    def publish(self, router) -> None:
        """The ext lanes' labels and rests, like every source (plan 27 B3:
        the ROUTING page reads the count from here, not a constant). An
        ext lane rests at 0 — what a push row with no rest of its own has
        always been centred on."""
        if router.labels.get("ext") != self.labels:
            router.labels["ext"] = self.labels
        if len(router.rests.get("ext") or ()) != self.decoder.n:
            router.rests["ext"] = [0.0] * self.decoder.n

    def receive(self, router) -> None:
        """Inbound messages → the ext vector, held live between messages."""
        if self.ports.inp is None:
            if self._fed:
                router.feed("ext", None)
                self._fed = False
            return
        for msg in self.ports.recv():
            self.decoder.feed(msg)
        if self.decoder.live:
            router.feed("ext", self.decoder.values)
            self._fed = True

    def lanes(self, analyzer) -> list[float]:
        """This frame's outbound readings, one per slot, in [0, 1]."""
        if analyzer is not None:
            self._n = analyzer.n
        out: list[float] = []
        for spec in self.send_spec:
            scheme, _, addr = spec.partition(":")
            if scheme == "lane":
                idx = range(self._n) if addr == "*" else [int(addr)]
                for i in idx:
                    v = 0.0 if analyzer is None or not 0 <= i < analyzer.n else analyzer.lanes[i]
                    out.append(float(v) / CEIL)
            elif scheme == "param":
                p = self.reg.get(addr)
                out.append(0.0 if p is None or p.kind is Kind.TRIGGER else p.eff_norm)
        return out

    def transmit(self, analyzer) -> None:
        """The `send` list's lanes out: what changed, at most `rate` times
        a second per lane (a bridge on its own; `step`)."""
        if self.ports.out is None:
            return
        self.send_values(self.lanes(analyzer)[: self.room])

    def send_values(self, values) -> None:
        """This frame's readings out — a list (lane k = index k) or a dict
        lane → reading, what the sink rows give (routing.sink_values) —
        through the gate (`Sender`)."""
        if self.ports.out is None:
            return
        for msg in self.sender.messages(values):
            self.ports.send(msg)
            self.sent += 1
