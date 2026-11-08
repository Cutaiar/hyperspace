"""Time the dashboard's per-frame CPU work - `dashboard.paint()` - offscreen.

    xvfb-run -a uv run python tools/dkit/bench_paint.py [frames]

`paint` is where the kit spends Python: layout, every widget, every label.
GPU time and the backend's render are not in it. Prints the median and p90
over the frames after five warm-up ones, and how many labels and characters
a frame draws. Run it twice: it is noisy at the 0.3ms level on a shared
machine, and a change smaller than that is not shown by one run.

Figures (Mesa, 1440x1100, RETRO row 70): 4.8ms before the font-loader fix,
7.8ms with a quad per glyph, 5.2ms with `add_text` runs (paired runs, same machine: 4.6 pre-fix).
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dashboard as DB   # noqa: E402
import draw as D         # noqa: E402


def main() -> None:
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    times, calls = [], {"n": 0, "chars": 0}
    real_paint, real_label = DB.paint, D.label

    def paint(*a, **k):
        calls["n"] = calls["chars"] = 0
        t0 = time.perf_counter()
        real_paint(*a, **k)
        times.append(time.perf_counter() - t0)

    def label(dl, x, y, s, *a, **k):
        calls["n"] += 1
        calls["chars"] += len(s)
        return real_label(dl, x, y, s, *a, **k)

    DB.paint, D.label = paint, label
    DB.render("light", 1440, 1100, script=[None] * frames, keep="last")
    ss = sorted(times[5:])
    print(f"paint() median {statistics.median(ss) * 1e3:.2f} ms  "
          f"p90 {ss[int(len(ss) * 0.9)] * 1e3:.2f} ms  "
          f"labels/frame {calls['n']}  chars/frame {calls['chars']}")


if __name__ == "__main__":
    main()
