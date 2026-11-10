"""What drawing the panel on dkit costs, against the stock widgets: CPU time
per frame of the real `Panel.draw` with each side pane section shown, and
the vertices its draw lists hold.

    xvfb-run -a uv run python tools/profile_kit.py            # both, side by side
    xvfb-run -a uv run python tools/profile_kit.py --frames 400

Each run is its own process (``HYPERSPACE_KIT`` is read when the fonts
load), on the headless rig the panel's tests use (`tests/test_ui_shell.
build_rig`): the panel the whole window at 1600 × 900, the pane at its
default width, every section focused in turn. A frame is `new_frame`,
`Panel.draw`, `render` — `render` builds the draw data, which is where a
draw list's vertex count turns into work — and nothing is drawn to a GPU:
this measures the CPU side only (a GPU here is Mesa's llvmpipe, and the
panel's draw lists are tiny next to the render windows'). The median of
`--frames` frames, after `--warm` frames of warm-up.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def measure(frames: int, warm: int) -> dict:
    sys.path.insert(0, str(ROOT / "tests"))
    os.environ.setdefault("HYPERSPACE_HOME", tempfile.mkdtemp())
    from imgui_bundle import imgui
    from test_ui_shell import build_rig

    from hyperspace import ui_graph, ui_kit, ui_pane
    from hyperspace.ui import PAGE_KEYS

    out = {"kit": None, "sections": {}}
    with build_rig(Path(tempfile.mkdtemp())) as r:
        out["kit"] = ui_kit.ready()
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)

        def frame() -> tuple[float, int]:
            t0 = time.perf_counter()
            imgui.new_frame()
            r.panel.draw(1 / 60, 60.0)
            imgui.render()
            dt = time.perf_counter() - t0
            return dt, imgui.get_draw_data().total_vtx_count

        frame()
        ui_graph._state(r.panel)["side_w"] = ui_graph.SIDE_W
        for key, *_ in ui_pane.SECTIONS:
            r.reg["ui.page"].set(PAGE_KEYS.index("graph" if key == ui_pane.SELECTION else key))
            for _ in range(warm):
                frame()
            ms, vtx = [], []
            for _ in range(frames):
                dt, v = frame()
                ms.append(dt * 1000.0)
                vtx.append(v)
            out["sections"][key] = {"ms": statistics.median(ms), "p90": sorted(ms)[int(0.9 * len(ms))],
                                    "vtx": statistics.median(vtx)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--frames", type=int, default=200)
    ap.add_argument("--warm", type=int, default=30)
    ap.add_argument("--one", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--json", type=Path, help="write both runs here")
    a = ap.parse_args()
    if a.one:
        print(json.dumps(measure(a.frames, a.warm)))
        return
    runs = {}
    for kit in ("0", "1"):
        env = {**os.environ, "HYPERSPACE_KIT": kit}
        res = subprocess.run([sys.executable, __file__, "--one", "--frames", str(a.frames),
                              "--warm", str(a.warm)], env=env, capture_output=True, text=True, check=False,
                             cwd=ROOT)
        if res.returncode:
            sys.exit(res.stderr)
        runs[kit] = json.loads(res.stdout.strip().splitlines()[-1])
    stock, kit = runs["0"], runs["1"]
    assert stock["kit"] is False and kit["kit"] is True, (stock["kit"], kit["kit"])
    print(f"{'section':<10} {'stock ms':>9} {'kit ms':>8} {'Δ ms':>7} {'Δ %':>6}   "
          f"{'stock vtx':>9} {'kit vtx':>8}")
    tot = [0.0, 0.0]
    for key, s in stock["sections"].items():
        k = kit["sections"][key]
        d = k["ms"] - s["ms"]
        tot[0] += s["ms"]
        tot[1] += k["ms"]
        print(f"{key:<10} {s['ms']:9.3f} {k['ms']:8.3f} {d:+7.3f} {100 * d / s['ms']:+5.0f}%   "
              f"{s['vtx']:9.0f} {k['vtx']:8.0f}")
    print(f"{'mean':<10} {tot[0] / len(stock['sections']):9.3f} {tot[1] / len(stock['sections']):8.3f}"
          f" {(tot[1] - tot[0]) / len(stock['sections']):+7.3f}"
          f" {100 * (tot[1] - tot[0]) / tot[0]:+5.0f}%")
    if a.json:
        a.json.write_text(json.dumps(runs, indent=1))


if __name__ == "__main__":
    main()
