"""The DDJ-FLX4's lights next to Rekordbox: what tunes idle_lights.py, asked of the hardware.

    uv run python tools/flx4_led_probe.py [port-substring] [--out report.json]

Run it on the Mac with the FLX4 plugged in. It opens the FLX4's ports the way
Hyperspace does (shared, never exclusive), walks you through five steps, asks
you what you see after each, and writes every answer and the input it heard to
a JSON report (default ``flx4-probe-<time>.json`` here). Send that file back
and the light set, the defaults and the yield rules in idle_lights.py get tuned
from it.

  1. **Addresses** (Rekordbox closed). Each light of idle_lights.flx4() lights on
     its own; you say whether the light you expect came on.
  2. **Pad modes** (Rekordbox closed). Every pad-mode note block lights in turn;
     you say which show in the pad mode the deck is in.
  3. **Left alone** (Rekordbox closed). Nothing is sent and nothing is asked of
     the device for a while; you say whether it starts a light show of its own
     (Pioneer's demo mode), and the input it sends unasked is counted.
  4. **Launch race**. Every light on, then you start Rekordbox. It times when the
     process appears (what idle_lights' app watch sees) against when the device
     first speaks and when you see Rekordbox's lights take over. That gap is
     how long a dark sent on yielding can still land on Rekordbox's lights.
  5. **Side by side** (Rekordbox open, a track on deck 1). Every light on, then
     you do ordinary things (play, a pad, a pad-mode switch, a deck load,
     clicking Rekordbox's window) and say each time whether Rekordbox took its
     lights back. Input is counted throughout, to see whether Rekordbox keeps
     the device talking (a SysEx answer every 200 ms would keep a running
     animation from ever starting while Rekordbox runs, by itself).

Ctrl-C skips the rest; the report still holds what was done. Nothing here
writes to Hyperspace's files.
"""

from __future__ import annotations

import argparse
import json
import select
import sys
import time
from collections import Counter
from pathlib import Path

import mido

from hyperspace.idle_lights import FLX4_NAMES, AppWatch, Light, flx4

PAD_BLOCKS = {           # Mixxx's mapping: one note block a pad mode, first note
    "hot cue": 0x00, "pad fx 1": 0x10, "beat jump": 0x20, "sampler": 0x30,
    "keyboard": 0x40, "pad fx 2": 0x50, "beat loop": 0x60, "key shift": 0x70,
}
PAD_CH = (7, 9)          # deck 1, deck 2


class Probe:
    def __init__(self, match: str):
        ins, outs = mido.get_input_names(), mido.get_output_names()  # pyright: ignore[reportAttributeAccessIssue]
        iname = next((n for n in ins if match.lower() in n.lower()), None)
        oname = next((n for n in outs if match.lower() in n.lower()), None)
        if iname is None or oname is None:
            raise SystemExit(f"no FLX4: nothing matches {match!r} in {ins} / {outs}")
        self.inp, self.out = mido.open_input(iname), mido.open_output(oname)  # pyright: ignore[reportAttributeAccessIssue]
        self.report: dict = {"ports": [iname, oname], "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                             "steps": {}}
        print(f"opened {iname!r} / {oname!r}")

    # ---- the wire ----

    def set(self, light: Light, value: int) -> None:
        if light.kind == "cc":
            self.out.send(mido.Message("control_change", channel=light.channel,
                                       control=light.number, value=value))
        else:
            self.out.send(mido.Message("note_on", channel=light.channel, note=light.number,
                                       velocity=value))

    def all(self, lights, on: bool) -> None:
        for lt in lights:
            self.set(lt, lt.value(1.0) if on else 0)

    def drain(self) -> list:
        return list(self.inp.iter_pending())

    def listen(self, seconds: float) -> dict:
        """What the device sent in `seconds`: counts by type, and the first few."""
        end, kinds, first = time.monotonic() + seconds, Counter(), []
        while time.monotonic() < end:
            for m in self.drain():
                kinds[m.type] += 1
                if len(first) < 12:
                    first.append(m.hex())
            time.sleep(0.01)
        return {"seconds": seconds, "by_type": dict(kinds), "first": first}

    @staticmethod
    def ask(q: str) -> str:
        return input(f"  {q} ").strip()

    def yes(self, q: str) -> bool:
        return self.ask(f"{q} [y/n]").lower().startswith("y")

    # ---- the steps ----

    def addresses(self) -> None:
        print("\n1. Addresses — close Rekordbox. Each light comes on alone.")
        lights, out = flx4(), []
        self.all(lights, False)
        for lt in lights:
            name = FLX4_NAMES.get(lt.key, "?")
            self.set(lt, lt.value(1.0))
            time.sleep(0.05)
            lit = self.ask(f"{name} ({lt.kind} ch{lt.channel} #{lt.number}) — lit? "
                           "[y / n / a note of what lit instead]")
            self.set(lt, 0)
            out.append({"light": list(lt.key), "name": name, "answer": lit})
        self.report["steps"]["addresses"] = out

    def pad_modes(self) -> None:
        print("\n2. Pad modes — leave both decks in HOT CUE mode.")
        out = {}
        for mode, first in PAD_BLOCKS.items():
            pads = [Light("note", ch, first + i) for ch in PAD_CH for i in range(8)]
            self.all(pads, True)
            out[mode] = self.ask(f"block {mode!r} (notes {first}-{first + 7}) lit: "
                                 "do the pads show it? [y/n]")
            self.all(pads, False)
        out["switched"] = self.ask("Now press PAD FX on deck 1 and back to HOT CUE. "
                                   "Did lit hot-cue pads stay lit through the switch? [y/n/none lit]")
        self.report["steps"]["pad_modes"] = out

    def left_alone(self, seconds: float) -> None:
        print(f"\n3. Left alone — Rekordbox closed, nothing sent for {seconds:g} s. Don't touch it.")
        self.all(flx4(), False)
        heard = self.listen(seconds)
        self.report["steps"]["left_alone"] = {
            "heard": heard,
            "own_show": self.ask("Did the FLX4 start a light show of its own? "
                                 "[n / y and after about how long]"),
        }

    def launch_race(self, timeout: float) -> None:
        print("\n4. Launch race — every light on. Start Rekordbox now; press Enter the moment "
              "Rekordbox's lights replace these (or type 'never').")
        lights = flx4()
        self.all(lights, True)
        self.drain()
        watch = AppWatch(["rekordbox"], start=False)
        t0, seen_proc, first_msg = time.monotonic(), None, None
        first_type = ""
        while time.monotonic() - t0 < timeout:
            if seen_proc is None and watch.check():
                seen_proc = time.monotonic() - t0
                print(f"  (Rekordbox's process seen at {seen_proc:.1f} s)")
            for m in self.drain():
                if first_msg is None:
                    first_msg, first_type = time.monotonic() - t0, m.type
                    print(f"  (the FLX4 first spoke at {first_msg:.1f} s: {m.type})")
            r, _, _ = select.select([sys.stdin], [], [], 0.2)
            if r:
                said = sys.stdin.readline().strip()
                took = time.monotonic() - t0
                break
        else:
            said, took = "timeout", None
        self.report["steps"]["launch_race"] = {
            "process_seen_s": seen_proc, "device_first_spoke_s": first_msg,
            "device_first_type": first_type, "lights_taken_s": took, "said": said,
            "which_taken": self.ask("Which lights did Rekordbox change? (all / some: which / none)"),
        }

    def side_by_side(self) -> None:
        print("\n5. Side by side — Rekordbox open, a track loaded on deck 1.")
        lights = flx4()
        self.all(lights, True)
        out = {"idle_traffic": self.listen(5.0)}
        print(f"  heard in 5 s, untouched: {out['idle_traffic']['by_type']}")
        for what in ("click Rekordbox's window (focus)",
                     "press PLAY on deck 1, then pause",
                     "set a hot cue on pad 1 of deck 1",
                     "switch deck 1 to BEAT LOOP and back to HOT CUE",
                     "load another track onto deck 1",
                     "do nothing for 10 s"):
            self.all(lights, True)
            input(f"  Every light is on. Now: {what}. Enter when done.")
            out[what] = self.ask("Which lights went back to Rekordbox's state? "
                                 "(all / none / which)")
        self.all(lights, False)
        out["after_dark"] = self.ask("Every light is now sent dark. Did Rekordbox relight its "
                                     "own on its own (within a few seconds)? [y/n/which]")
        self.report["steps"]["side_by_side"] = out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("port", nargs="?", default="DDJ-FLX4")
    ap.add_argument("--out", type=Path,
                    default=Path(f"flx4-probe-{time.strftime('%Y%m%d-%H%M%S')}.json"))
    ap.add_argument("--alone", type=float, default=120.0, help="step 3's wait, seconds")
    ap.add_argument("--steps", default="12345", help="which steps to run, e.g. 45")
    a = ap.parse_args()
    p = Probe(a.port)
    steps = {"1": p.addresses, "2": p.pad_modes, "3": lambda: p.left_alone(a.alone),
             "4": lambda: p.launch_race(180.0), "5": p.side_by_side}
    try:
        for k in a.steps:
            steps[k]()
    except KeyboardInterrupt:
        print("\n(stopped; writing what was done)")
        p.report["stopped"] = True
    finally:
        a.out.write_text(json.dumps(p.report, indent=2))
        print(f"\nreport: {a.out.resolve()}")


if __name__ == "__main__":
    main()
