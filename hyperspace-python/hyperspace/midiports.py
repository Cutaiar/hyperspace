"""Looking for MIDI ports: the one road, on the frame thread (audit R15, row 791).

`port_names()` is what asks the machine which MIDI ports it has. Call it from the
main thread, as often as you like: it really looks at most every `LOOK_S`, and a
plugged-in port shows within that. An open passes `fresh=True`, on its own pace.

What R15 feared, and what is true of the python-rtmidi we ship (1.5.8, read
from its binary on 2026-11-06):

- **The abort is the process's first client, not every look.** RtMidi holds one
  CoreMIDI client for the process and asks for it only while it has none. Asked
  and refused, it throws from a `throw()` function: `std::terminate`, past any
  `except`. Once a client exists no later look or open can reach that line.
- `sandbox-exec` denying the MIDI server reproduces it: status -10833, then
  `mido.get_input_names()` dies with exit 134. Through here, a sentence
  (`test_midiports.py` runs it for real).

So the first look is the dangerous one, and we ask first in words that can be
told no: `_create_client` calls `MIDIClientCreate` itself, which returns a
status where RtMidi would abort. A refusal gives no names and a reason, and
RtMidi is not touched; it is asked again at most every `REFUSED_RETRY_S`, however
often it is called. The client we made is held for the life of the process, so
CoreMIDI's answer still stands a moment later, when RtMidi asks. A refusal in
exactly that gap is the one thing left, and no code here can reach it.

**What a look costs** (2026-11-06, one Mac, busy; virtual ports made by another
process, n inputs and n outputs, the first named as an APC40; 300 looks each):

    n     median    p99       worst
    0     0.05 ms   0.08 ms   1.2 ms
    1     0.29 ms   0.60 ms   0.6 ms
    12    3.2 ms    7.3 ms    19.9 ms
    32    7.7 ms    10.6 ms   15.2 ms
    64    14.6 ms   24.5 ms   33.0 ms

About 0.25 ms a pair, on the frame thread, and a real device's names were not
measured. That is why a plain call shares one look per `LOOK_S`. The first look in
a process, which makes the client and loads the backend, took 0.1 to 1.2 s.

A refused ask: 13 ms the first time (loading the frameworks), then a median of
0.017 ms, worst 0.073 ms, with the MIDI server denied. A server that hangs rather
than refuses wasn't measured; no one here can make one, and RtMidi's own ask would
hang the same.

Only this module may list ports, and an open (`midi.Ports`, `bridge._open_out`)
looks here first: `test_midiports.py` holds it to that.
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import NamedTuple

import mido

__all__ = ["LOOK_S", "REFUSED_RETRY_S", "PortNames", "port_names"]

LOOK_S = 2.0                # a plain `port_names()` really looks this often, at most
REFUSED_RETRY_S = 10.0      # a refused client is asked for again this often, at most
_COREMIDI = "/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI"
_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
_UTF8 = 0x0800_0100         # kCFStringEncodingUTF8


class PortNames(NamedTuple):
    """One look: the ports' names, and why a side has none when it could not ask.
    Each side stands alone, so a broken input list leaves the outputs good. Read-only:
    a plain call hands the same one to everyone until the next look."""

    inputs: list[str]
    outputs: list[str]
    in_why: str = ""
    out_why: str = ""

    @property
    def why(self) -> str:
        """Why it could not ask, on either side; empty when both are good."""
        return self.in_why or self.out_why


def _client_api() -> tuple:
    """`MIDIClientCreate` and our client's name, each made once: a refused client is
    asked for again all night, and a name made per ask would leak each time."""
    global _api
    if _api is None:
        foundation, coremidi = ctypes.CDLL(_FOUNDATION), ctypes.CDLL(_COREMIDI)
        make = foundation.CFStringCreateWithCString
        make.restype, make.argtypes = ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        create = coremidi.MIDIClientCreate
        create.restype = ctypes.c_int32
        create.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        _api = create, make(None, b"Hyperspace", _UTF8)
    return _api


def _create_client() -> int:
    """Ask CoreMIDI for a client ourselves; its status, 0 for yes. Not on a Mac, 0:
    no other backend has this abort. The tests' conftest replaces this, since a
    real client reaches the machine's MIDI."""
    if sys.platform != "darwin":
        return 0
    create, name = _client_api()
    client = ctypes.c_uint32(0)
    # (never disposed: holding it is the point, and a process makes one)
    return create(name, None, None, ctypes.byref(client))


class _Gate:
    """Has CoreMIDI said yes to this process? Yes is for good; no is asked again.
    It keeps the last look too, for everyone who doesn't need a fresh one."""

    def __init__(self) -> None:
        self.open = False
        self.why = ""
        self.next_ask = float("-inf")
        self.seen = PortNames([], [])
        self.next_look = float("-inf")

    def ask(self, now: float) -> str:
        """Empty once CoreMIDI has given a client; else why not."""
        if self.open:
            return ""
        if now < self.next_ask:
            return self.why
        self.next_ask = now + REFUSED_RETRY_S
        try:
            status = _create_client()
        except Exception as e:  # noqa: BLE001 — no framework, no ctypes: no MIDI, not a crash
            self.why = f"{type(e).__name__}: {e}"[:120]
            return self.why
        self.open = status == 0
        self.why = "" if self.open else f"CoreMIDI refused a client ({status})"
        return self.why


# both survive this module's reload (REVIEW.md): a new gate would make another client,
# and could read a refusal while RtMidi holds a working one
_api: tuple | None = globals().get("_api")
_gate: _Gate = globals().get("_gate") or _Gate()


def _side(names) -> tuple[list[str], str]:
    """One side's names, and why not. A port going away mid-look lists as None
    (seen on the Mac, unplugging)."""
    try:
        return [n for n in names() if n], ""
    except Exception as e:  # noqa: BLE001 — backend missing / broken
        return [], f"{type(e).__name__}: {e}"[:120]


def port_names(clock=time.monotonic, *, fresh: bool = False) -> PortNames:
    """The MIDI ports on this machine, as of the last `LOOK_S` (`fresh`: now). Never
    raises, and can't abort on a refusal it sees (the module's docstring has the gap
    left); with nothing to say, empty lists and `why`. Main thread only (RtMidi's list
    runs the calling thread's run loop). The first call in a process makes the client,
    so make it before the first frame if a panel will be the first to ask."""
    now = clock()
    why = _gate.ask(now)
    if why:
        return PortNames([], [], why, why)
    if fresh or now >= _gate.next_look:
        # (mido builds these two at import, so pyright can't see them)
        inputs, in_why = _side(lambda: mido.get_input_names())  # pyright: ignore[reportAttributeAccessIssue]
        outputs, out_why = _side(lambda: mido.get_output_names())  # pyright: ignore[reportAttributeAccessIssue]
        _gate.seen = PortNames(inputs, outputs, in_why, out_why)
        _gate.next_look = now + LOOK_S
    return _gate.seen
