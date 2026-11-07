"""Looking for MIDI ports: the one road, safe and cheap (audit R15, row 791).

`port_names()` is what asks the machine which MIDI ports it has. Call it from
the main thread, as often as you like: a panel once a second is nothing.

What R15 feared, and what is true of the python-rtmidi we ship (1.5.8, read
from its binary on 2026-11-06):

- **The abort is the process's first client, not every look.** RtMidi holds one
  CoreMIDI client for the process and asks for it only while it has none. Asked
  and refused, it throws from a `throw()` function: `std::terminate`, past any
  `except`. Once a client exists no later look or open can reach that line.
- **A look after that is 0.05 ms** for both lists (300 looks on the owner's Mac);
  the first, which makes the client and loads the backend, 0.1 to 1.2 s.
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

Only this module may list ports, and an open (`midi.Ports`, `bridge._open_out`)
looks here first: `test_midiports.py` holds it to that.
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import NamedTuple

import mido

__all__ = ["REFUSED_RETRY_S", "PortNames", "port_names"]

REFUSED_RETRY_S = 10.0      # a refused client is asked for again this often, at most
_COREMIDI = "/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI"
_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
_UTF8 = 0x0800_0100         # kCFStringEncodingUTF8


class PortNames(NamedTuple):
    """One look: the ports' names, and `why` there are none when it could not ask."""

    inputs: list[str]
    outputs: list[str]
    why: str = ""


def _create_client() -> int:
    """Ask CoreMIDI for a client ourselves; its status, 0 for yes. Not on a Mac, 0:
    no other backend has this abort. The tests' conftest replaces this, since a
    real client reaches the machine's MIDI."""
    if sys.platform != "darwin":
        return 0
    foundation, coremidi = ctypes.CDLL(_FOUNDATION), ctypes.CDLL(_COREMIDI)
    make = foundation.CFStringCreateWithCString
    make.restype, make.argtypes = ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    create = coremidi.MIDIClientCreate
    create.restype = ctypes.c_int32
    create.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    client = ctypes.c_uint32(0)
    # (never disposed: holding it is the point, and a process makes one)
    return create(make(None, b"Hyperspace", _UTF8), None, None, ctypes.byref(client))


class _Gate:
    """Has CoreMIDI said yes to this process? Yes is for good; no is asked again."""

    def __init__(self) -> None:
        self.open = False
        self.why = ""
        self.next_ask = float("-inf")

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


_gate = _Gate()


def port_names(clock=time.monotonic) -> PortNames:
    """The MIDI ports on this machine now. Never raises and cannot abort; with
    nothing to say, empty lists and `why`. Main thread only (RtMidi's list runs
    the calling thread's run loop). The first call in a process makes the client
    and loads the backend, 0.1 to 1.2 s as measured, so make it before the first
    frame if a panel will be the first to ask."""
    why = _gate.ask(clock())
    if why:
        return PortNames([], [], why)
    try:
        # (a port going away mid-look lists as None: seen on the Mac, unplugging)
        return PortNames([n for n in mido.get_input_names() if n],
                         [n for n in mido.get_output_names() if n])
    except Exception as e:  # noqa: BLE001 — backend missing / broken
        return PortNames([], [], f"{type(e).__name__}: {e}"[:120])
