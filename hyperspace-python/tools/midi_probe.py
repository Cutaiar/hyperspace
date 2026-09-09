"""Print what a MIDI controller sends, and light it up — a protocol check.

    uv run python tools/midi_probe.py [port-substring] [seconds]

Opens the first port matching the substring (default "APC40"), puts an
APC40 in host-controlled mode, walks a value up every knob ring and lights
a few buttons so the feedback path is visible, then echoes every incoming
message with its channel, number and value until the time is up. Use it
to confirm the numbers in hyperspace/apc40.py against the hardware, or to
find the numbers for a new device profile.
"""

from __future__ import annotations

import sys
import time

import mido

from hyperspace import apc40


def main() -> None:
    match = sys.argv[1] if len(sys.argv) > 1 else "APC40"
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
    ins, outs = mido.get_input_names(), mido.get_output_names()
    print("inputs :", ins)
    print("outputs:", outs)
    iname = next((n for n in ins if match.lower() in n.lower()), None)
    oname = next((n for n in outs if match.lower() in n.lower()), None)
    if iname is None:
        raise SystemExit(f"no input port matching {match!r}")
    inp = mido.open_input(iname)
    out = mido.open_output(oname) if oname else None
    print(f"listening on {iname!r} for {secs:g}s — move things")
    if out is not None and "apc40" in iname.lower():
        for m in apc40.enter():
            out.send(m)
        for k, ccn in enumerate((*apc40.DEVICE_KNOBS, *apc40.TRACK_KNOBS)):
            out.send(mido.Message("control_change", control=ccn + 8, value=apc40.RING_VOLUME))
            out.send(mido.Message("control_change", control=ccn, value=min(8 * (k + 1), 127)))
        for ch in range(8):
            out.send(mido.Message("note_on", channel=ch, note=apc40.N_CLIP[0], velocity=ch % 6 + 1))
        out.send(mido.Message("note_on", note=apc40.N_PLAY, velocity=1))
        print("sent: mode 0x42, ring values 8..128 step 8, clip row 1 colours 1–6, PLAY lit")
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < secs:
            for msg in inp.iter_pending():
                print(f"{time.monotonic() - t0:6.2f}  {msg}")
            time.sleep(0.005)
    finally:
        if out is not None and "apc40" in iname.lower():
            for m in apc40.leave():
                out.send(m)
        inp.close()
        if out is not None:
            out.close()


if __name__ == "__main__":
    main()
