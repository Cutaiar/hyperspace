#!/usr/bin/env python3
"""Does an Xbox 360 Kinect see closer with Kinect-for-Windows near mode's registers?

    uv run python tools/kinect_near.py [--rounds 3] [--seconds 16] [--out DIR]

libfreenect refuses near mode on this sensor by its USB product id alone; the
mode itself is two register writes (src/flags.c: 0x15 0x1e→0x07, 0x2ef
0x190→0). This writes them anyway, each alone and both, in turn for several
rounds over a scene held still, and says what depth came back. A register is
read back after each write: a write that did not stick tests nothing. Depth
that goes blank on its own cycle is counted (``blank``) and left out of the
rest. The registers are put back at the end. Quit Hyperspace first.

Put something flat and matte at 30–40 cm, filling part of the view, and
another thing at 1–2 m, and leave both alone. ``<45cm`` and ``45-80cm`` are the
shares of the picture read there: near mode works if they grow.
"""

from __future__ import annotations

import argparse
import ctypes as C
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hyperspace import kinect

IR, FAR = 0x15, 0x2EF
MODES = {"off": (0x1E, 0x190), "ir": (0x07, 0x190), "2ef": (0x1E, 0x000), "both": (0x07, 0x000)}
SETTLE_S = 2.0
BLANK = 0.005        # under this share of the picture read is a blank frame


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--seconds", type=float, default=16.0, help="per mode: longer than one 14 s blank cycle")
    ap.add_argument("--out", type=Path, help="save each mode's median depth picture here")
    a = ap.parse_args()
    s = kinect.Sensor(kinect.Options())
    frames: dict[str, list[np.ndarray]] = {m: [] for m in MODES}
    blanks = dict.fromkeys(MODES, 0)
    before = None
    try:
        s.open()
        lib, dev = s._lib, s._dev
        lib.read_register.restype, lib.read_register.argtypes = C.c_uint16, [C.c_void_p, C.c_uint16]
        lib.write_register.restype = C.c_int
        lib.write_register.argtypes = [C.c_void_p, C.c_uint16, C.c_uint16]

        def put(reg: int, v: int) -> int:
            lib.write_register(dev, reg, v)
            time.sleep(0.1)
            return lib.read_register(dev, reg)

        def pump(seconds: float, keep: str | None = None) -> None:
            end = time.monotonic() + seconds
            k = 0
            while time.monotonic() < end:
                got = s.read()
                if got is None or keep is None:
                    continue
                k += 1
                if (got[0] > 0).mean() < BLANK:
                    blanks[keep] += 1
                elif k % 10 == 0:
                    frames[keep].append(got[0])

        pump(2.0)
        before = (lib.read_register(dev, IR), lib.read_register(dev, FAR))
        print(f"as found: 0x15 = {before[0]:#x}, 0x2ef = {before[1]:#x}")
        for r in range(a.rounds):
            for m, (ir, far) in MODES.items():
                back = put(IR, ir), put(FAR, far)
                pump(SETTLE_S)
                pump(a.seconds, m)
                print(f"round {r + 1} {m:5s} wrote {ir:#x} {far:#x}  read back {back[0]:#x} {back[1]:#x}"
                      f"{'' if back == (ir, far) else '  (NOT what was written)'}", flush=True)
    finally:
        if before is not None:
            s._lib.write_register(s._dev, IR, before[0])
            s._lib.write_register(s._dev, FAR, before[1])
        s.close()
    print(f"\n{'mode':6s}{'frames':>7s}{'blank':>7s}{'read %':>8s}{'<45cm %':>9s}{'45-80cm %':>11s}"
          f"{'>80cm %':>9s}{'nearest mm':>12s}")
    for m, fs in frames.items():
        if not fs:
            print(f"{m:6s}{0:7d}{blanks[m]:7d}   no depth")
            continue
        d = np.stack(fs)
        n = d.size
        print(f"{m:6s}{len(fs):7d}{blanks[m]:7d}{100 * (d > 0).sum() / n:8.1f}"
              f"{100 * ((d > 0) & (d < 450)).sum() / n:9.2f}{100 * ((d >= 450) & (d < 800)).sum() / n:11.2f}"
              f"{100 * (d >= 800).sum() / n:9.2f}{np.percentile(d[d > 0], 0.5):12.0f}")
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            px = kinect.depth_picture(np.median(d, axis=0).astype(np.uint16), kinect.Options(near=0.2))
            Image.fromarray(px).save(a.out / f"{m}.png")


if __name__ == "__main__":
    main()
