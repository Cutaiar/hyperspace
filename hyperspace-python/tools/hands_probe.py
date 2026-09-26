"""Watch the Ultraleap axes in a terminal, calibrate the box, map a DAW.

    uv run python tools/hands_probe.py                    # live table
    uv run python tools/hands_probe.py --calibrate 20     # sweep, write hands.json
    uv run python tools/hands_probe.py --solo right.pitch # only that axis to the DAW

The same thing the HANDS page shows, without the app: per axis the native
reading (mm / degrees / 0–1), the output y after shaping and dynamics,
and the value on its MIDI out. Uses [hands] in config.toml and the
default setup (the app's saved setups live in its library).

--calibrate N runs the page's sweep: for N seconds move each hand through
everything it should reach; each axis's range becomes what it covered
(2nd–98th percentile) and is written to the calibration file.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from hyperspace import config
from hyperspace.hands import FEATURES, SIDES, HandSettings, HandsIO

FPS = 60


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
    try:
        io = HandsIO(HandSettings.from_config(hc), hc, cal_path=cal)
    except ImportError as e:
        raise SystemExit(f"{e} — the Ultraleap bindings aren't installed; "
                         "see Install in docs/plans/08-hands.md") from e
    if args.solo:
        io.solo = io.axis(args.solo)
    if args.calibrate:
        io.start_calibration(args.calibrate)
    t0 = time.monotonic()
    try:
        while True:
            io.poll(1 / FPS)
            t = time.monotonic() - t0
            _draw(io, t)
            if args.calibrate and not io.calibrating:
                break
            if args.seconds and t >= args.seconds:
                break
            time.sleep(1 / FPS)
    except KeyboardInterrupt:
        pass
    print(f"\n{io.cal_note}" if io.cal_note else "")
    if args.calibrate:
        for a, st in zip(io.axes, io.state):
            print(f"  {a.name:14s} {st.lo:9.2f} … {st.hi:9.2f} {FEATURES[a.feature][0]}")
        print(f"wrote {cal}")
    io.close()


def _draw(io: HandsIO, t: float) -> None:
    head = f"{io.status} · {t:5.1f}s · out {io.out_name or 'none'}"
    if io.calibrating:
        head += f" · CALIBRATING {io.calibrating:4.1f}s — sweep every axis end to end"
    rows = [f"\x1b[H\x1b[2J{head}"]
    for side in SIDES:
        rows.append(f"{side:5s} {'IN' if io.present[side] else '--'}")
        for a, st in zip(io.axes, io.state):
            if a.side != side:
                continue
            unit = FEATURES[a.feature][0]
            raw = "      —     " if st.raw is None else f"{st.raw:8.2f} {unit:4s}"
            y = "  —  " if st.y is None else f"{st.y:5.3f}"
            bar = "" if st.y is None else "█" * round(st.y * 30)
            q = "" if st.q is None else f"{a.out} {st.q}"
            rows.append(f"   {a.feature:10s} {raw}  y {y}  {q:12s} {bar}")
    rows.append(f"last: {io.last}")
    sys.stdout.write("\n".join(rows) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
