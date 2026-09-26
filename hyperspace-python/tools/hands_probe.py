"""Watch the Ultraleap axes live, calibrate their ranges, map them in a DAW.

    uv run python tools/hands_probe.py                    # live table
    uv run python tools/hands_probe.py --calibrate 30     # sweep, write hands.json
    uv run python tools/hands_probe.py --out "Hyperspace Hands" --solo right.pitch

The live table shows, per axis, the native reading (mm / degrees / 0–1),
the normalized u, and the 7-bit value that goes out on its CC — the check
that the box, the tracking mode and the ranges agree. Reads the [hands]
section of config.toml for everything not given on the command line.

--calibrate N: for N seconds, sweep each hand through everything it
should reach — every axis, both ends — and the range each axis covered
(2nd–98th percentile, so a tracking glitch doesn't stretch it) is written
to the calibration file, keeping each axis's `invert`. Axes a hand never
reached keep their old range.

--solo AXIS: only that axis sends (e.g. to click MIDI-learn in a DAW
while both hands are in the box); --out opens or creates a MIDI port.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from hyperspace import config
from hyperspace.hands import FEATURES, HandsIO, save_calibration


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--calibrate", type=float, metavar="SECONDS")
    ap.add_argument("--mode", help="desktop | screentop | hmd")
    ap.add_argument("--out", help="MIDI out port (substring, else created virtual)")
    ap.add_argument("--solo", metavar="AXIS", help="e.g. left.x — only this axis sends")
    ap.add_argument("--seconds", type=float, default=0.0, help="stop after (0 = Ctrl-C)")
    args = ap.parse_args()

    hc = dict(config.load()["hands"])
    for k in ("mode", "out"):
        if getattr(args, k):
            hc[k] = getattr(args, k)
    cal = Path(hc["calibration"])
    io = HandsIO(hc, cal_path=cal)
    if args.solo:
        io.solo = io.axis(args.solo)
    print(f"leap: {io.status} · calibration {cal}{'' if cal.exists() else ' (none yet)'}")

    seen: dict[str, list[float]] = {a.name: [] for a in io.axes}
    t0 = time.monotonic()
    end = args.calibrate or args.seconds
    try:
        while not end or time.monotonic() - t0 < end:
            io.poll()
            for a in io.axes:
                if a.u is not None and a.raw is not None:
                    seen[a.name].append(a.raw)
            _draw(io, time.monotonic() - t0, end, bool(args.calibrate))
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
    print()
    if args.calibrate:
        changed = 0
        for a in io.axes:
            v = seen[a.name]
            if len(v) < 30:
                print(f"  {a.name:14s} not reached — keeps {a.lo:g} … {a.hi:g}")
                continue
            lo, hi = np.percentile(v, [2, 98])
            if hi - lo < 1e-6:
                continue
            a.lo, a.hi = float(lo), float(hi)
            changed += 1
            print(f"  {a.name:14s} {a.lo:9.2f} … {a.hi:9.2f} {FEATURES[a.feature][0]}")
        cal.parent.mkdir(parents=True, exist_ok=True)
        save_calibration(cal, io.axes)
        print(f"wrote {cal} ({changed} axes calibrated)")
    io.close()


def _draw(io: HandsIO, t: float, end: float, calibrating: bool) -> None:
    rows = [f"\x1b[H\x1b[2J{io.status} · {t:5.1f}s" + (f" / {end:g}s" if end else "")
            + ("  (calibrating: sweep every axis end to end)" if calibrating else "")]
    for side in ("left", "right"):
        rows.append(f"{side:5s} {'IN' if io.present[side] else '--'}")
        for a in io.axes:
            if a.side != side:
                continue
            unit = FEATURES[a.feature][0]
            if a.u is None:
                rows.append(f"   {a.feature:10s} cc{a.cc:<3d}      —")
                continue
            bar = "█" * round(a.u * 30)
            rows.append(f"   {a.feature:10s} cc{a.cc:<3d} {a.raw:9.2f} {unit:4s} "
                        f"u {a.u:4.2f} → {a.sent:3d} {bar}")
    rows.append(f"last: {io.last}")
    sys.stdout.write("\n".join(rows) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
