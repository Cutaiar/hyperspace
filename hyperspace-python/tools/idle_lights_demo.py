"""Idle lights on a real desk, without the app: the same `IdleLights` the app
runs for a `[[devices]]` entry's ``idle`` (hyperspace/idle_lights.py), so
what plays here is what the app plays.

    uv run python tools/idle_lights_demo.py                # every pattern; a touch skips
    uv run python tools/idle_lights_demo.py ripple hearts  # just these
    uv run python tools/idle_lights_demo.py --each 20 --dither
    uv run python tools/idle_lights_demo.py --after 10     # the app's idle / wake loop
    uv run python tools/idle_lights_demo.py --lights ddj-flx4 --port DDJ-FLX4
    uv run python tools/idle_lights_demo.py --lamp         # APC40: each row lit in turn

Without --after, any touch (`IdleLights.is_touch`) skips to the next
pattern. With --after N it runs as the app does: dark until N seconds pass
untouched, then the patterns, one each idle spell; a touch ends it.
--shape names the zoom's polytope. Ctrl-C leaves the desk dark (the APC40
back in generic mode). The app must not be running: both would draw.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

import mido

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hyperspace import apc40, idle_lights

PORTS = {"apc40": "Akai APC40", "ddj-flx4": "DDJ-FLX4"}


def lamp(out) -> None:
    """Each APC40 row lit in turn, so its colour can be told."""
    rows = [("clip rows 1-5 green", apc40.N_CLIP, range(8), apc40.GREEN),
            ("clip rows 1-5 yellow", apc40.N_CLIP, range(8), apc40.YELLOW),
            ("clip rows 1-5 red", apc40.N_CLIP, range(8), apc40.RED),
            ("clip rows blink (2/4/6)", apc40.N_CLIP, range(8), None),
            ("scene launch 1-5", apc40.N_SCENE, [0], 1),
            ("clip stop", [apc40.N_CLIPSTOP], range(8), 1),
            ("track select + MASTER", [apc40.N_SELECT], range(8), 1),
            ("activator", [apc40.N_ACTIVATOR], range(8), 1),
            ("solo", [apc40.N_SOLO], range(8), 1),
            ("rec-arm", [apc40.N_ARM], range(8), 1),
            ("STOP ALL CLIPS", [apc40.N_STOP_ALL], [0], 1),
            ("right-hand buttons", apc40.OTHER_BUTTONS, [0], 1)]
    for name, notes, chans, v in rows:
        input(f"  {name} — Enter to light")
        for r, n in enumerate(notes):
            for ch in chans:
                vel = v if v is not None else (2, 4, 6)[(r + ch) % 3]
                out.send(mido.Message("note_on", channel=ch, note=n, velocity=vel))
        if name.startswith("track select"):
            out.send(mido.Message("note_on", channel=0, note=apc40.N_MASTER_SEL, velocity=1))
        input("    what colour? (Enter to clear)")
        for n in [*notes, apc40.N_MASTER_SEL]:
            for ch in range(8):
                out.send(mido.Message("note_on", channel=ch, note=n, velocity=0))


def send(out, msgs) -> None:
    for kind, ch, number, value in msgs:
        if kind == "cc":
            out.send(mido.Message("control_change", channel=ch, control=number, value=value))
        else:
            out.send(mido.Message("note_on", channel=ch, note=number, velocity=value))


def is_touch(idle: idle_lights.IdleLights, m) -> bool:
    """`MidiIO._is_touch`, for a port of our own."""
    if m.type in ("clock", "active_sensing"):
        return False
    if m.type == "control_change":
        return idle.is_touch("cc", m.channel, m.control, m.value)
    if m.type == "pitchwheel":
        return idle.is_touch("pitch", m.channel, 0, (m.pitch + 8192) >> 7)
    return m.type != "note_off" and not (m.type == "note_on" and m.velocity == 0)


def main() -> None:
    names = idle_lights.pattern_names()
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help=f"patterns to play (of {', '.join(names)})")
    ap.add_argument("--lights", default="apc40", choices=sorted(idle_lights.SETS))
    ap.add_argument("--port", help="the MIDI port (default: the set's usual one)")
    ap.add_argument("--each", type=float, default=15.0, help="seconds a pattern plays")
    ap.add_argument("--after", type=float, default=None,
                    help="run the app's idle / wake loop with this timeout (seconds)")
    ap.add_argument("--dither", action="store_true", help="software dimming")
    ap.add_argument("--shape", default="Tesseract", help="the zoom's polytope")
    ap.add_argument("--lamp", action="store_true", help="APC40: light each row in turn")
    a = ap.parse_args()
    pattern = [n for n in names if not a.only or any(n.startswith(o) for o in a.only)]
    idle = idle_lights.from_entry(
        {"lights": a.lights, "pattern": pattern, "each": a.each, "shape": a.shape,
         "dither": a.dither, "after": a.after or 0.0, "yield_to": []}, start_watch=False)
    assert idle is not None
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))

    port = a.port or PORTS[a.lights]
    out, inp = mido.open_output(port), mido.open_input(port)
    apc = a.lights == "apc40"
    if apc:
        for m in apc40.enter():
            out.send(m)
        time.sleep(0.3)
    try:
        if a.lamp:
            lamp(out)
            return
        for _ in inp.iter_pending():
            pass
        print(f"idle after {a.after:g} s" if a.after else "a touch skips to the next pattern")
        playing = None
        while True:
            now = time.perf_counter()
            for m in inp.iter_pending():
                if is_touch(idle, m):
                    idle.touched()
            send(out, idle.tick())
            if idle.running:
                n = idle.names[idle._at] if idle.names else idle.pattern_name
                if n != playing:
                    playing = n
                    print(f"▶ {n}")
            elif idle.ended:
                playing = None
                print("  touched")
            time.sleep(max(0.0, 1 / idle_lights.FPS - (time.perf_counter() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        send(out, idle.end_now())
        if apc:
            for m in apc40.leave():
                out.send(m)


if __name__ == "__main__":
    main()
