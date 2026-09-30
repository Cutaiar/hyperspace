"""Question C — GPU contention: the real renderer against a dream worker.

    uv run python tools/dream_bench/c_contention.py [--secs 3] [--fps 60|0]

Main thread: the moderngl Renderer draws the 600-cell (faces + pattern on)
at 1280x820 into an FBO in a tight loop, ctx.finish() per frame, and records
the frame time. Worker thread: torch MPS temporal-dream steps at a cadence
of one call per N rendered frames (N=1: every frame — if it cannot keep up
it just runs flat out). Each configuration runs for --secs seconds.

Controls first: no worker; a worker that only spins Python (GIL cost with
no GPU work). Then the size sweep (res x steps x trunk), then the levers
one at a time from the base config (vgg16 conv3_3, 256 px, 2 steps).

Frame time here is CPU (numpy projection + GL calls) + GPU (finish), the
same work the app does between swaps. With --fps 60 (default) the loop is
paced like a vsynced window: it sleeps out the rest of each 16.7 ms tick,
which is when the worker gets the GIL and the GPU — the realistic case.
--fps 0 runs the renderer flat out (~900 fps), the pathological case where
the renderer hogs the GIL; "missed" counts frames whose work exceeded the
16.7 ms tick.
"""

from __future__ import annotations

import argparse
import threading
import time

import numpy as np
import torch
from common import (
    SCENE_600CELL,
    Scene,
    TemporalDream,
    machine_info,
    make_ctx,
    md_table,
    stats_ms,
    trunk,
)

W, H = 1280, 820


class Worker(threading.Thread):
    def __init__(self, fn, every: int, frame_counter: list[int], stop: threading.Event):
        super().__init__(daemon=True)
        self.fn, self.every, self.fc, self.stop = fn, every, frame_counter, stop
        self.times: list[float] = []
        self.calls = 0

    def run(self):
        due = 0
        while not self.stop.is_set():
            if self.fc[0] < due:
                time.sleep(0.0005)
                continue
            t0 = time.perf_counter()
            self.fn()
            torch.mps.synchronize()
            self.times.append(time.perf_counter() - t0)
            self.calls += 1
            due = self.fc[0] + self.every


def run_config(ctx, scene, worker_fn, every: int, secs: float, fps: float = 60.0) -> dict:
    fc = [0]
    stop = threading.Event()
    w = Worker(worker_fn, every, fc, stop) if worker_fn else None
    frames = []
    if w:
        w.start()
    t_end = time.perf_counter() + secs
    # warm-up: first frames pay for shader/kernel compiles
    for _ in range(20):
        scene.step()
        ctx.finish()
        fc[0] += 1
    n0 = fc[0]
    tick = 1.0 / fps if fps else 0.0
    next_tick = time.perf_counter()
    while time.perf_counter() < t_end:
        t0 = time.perf_counter()
        scene.step()
        ctx.finish()
        frames.append(time.perf_counter() - t0)
        fc[0] += 1
        if tick:
            next_tick += tick
            rem = next_tick - time.perf_counter()
            if rem > 0:
                time.sleep(rem)
            else:
                next_tick = time.perf_counter()  # dropped: resync like a swap would
    stop.set()
    if w:
        w.join()
    st = stats_ms(frames)
    out = {"frame_p50": st["p50"], "frame_p99": st["p99"], "frame_max": st["max"],
           "fps": len(frames) / secs, "missed": sum(f > 1 / 60 for f in frames)}
    if w and w.times:
        ds = stats_ms(w.times[3:] if len(w.times) > 6 else w.times)
        out.update(dream_p50=ds["p50"], dream_p99=ds["p99"],
                   dream_per_frame=w.calls / max(fc[0] - n0, 1))
    else:
        out.update(dream_p50=0.0, dream_p99=0.0, dream_per_frame=0.0)
    return out


def dream_fn(net, res: int, steps: int, dtype=torch.float32, channels_last=False,
             octaves=1, alternate=False):
    frame = torch.rand((1, 3, res, res), device="mps", dtype=dtype)
    if channels_last:
        frame = frame.contiguous(memory_format=torch.channels_last)
    td = TemporalDream(net, k=0.1, steps=steps, step_size=0.02, octaves=octaves,
                       alternate=alternate)

    def fn():
        td(frame)

    return fn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=float, default=3.0)
    ap.add_argument("--fps", type=float, default=60.0, help="0 = renderer flat out")
    args = ap.parse_args()
    print(machine_info())
    ctx = make_ctx()
    scene = Scene(ctx, W, H, **SCENE_600CELL)
    rows = []

    def add(label, cfg):
        r = run_config(ctx, scene, cfg[0], cfg[1], args.secs, args.fps)
        rows.append([label, r["frame_p50"], r["frame_p99"], r["frame_max"], r["missed"],
                     round(r["fps"]), r["dream_p50"], r["dream_p99"],
                     f"{r['dream_per_frame']:.2f}"])
        print(rows[-1], flush=True)

    # ---- controls
    add("no worker", (None, 1))

    def spin():
        x = 1
        for _ in range(200000):
            x = (x * 31 + 7) % 1000003  # pure-Python work holding the GIL

    add("python-spin worker (GIL only)", (spin, 1))

    # ---- size sweep
    nets = {}

    def get(name, **kw):
        key = (name, tuple(sorted(kw.items())))
        if key not in nets:
            nets[key] = trunk(name, **kw)
        return nets[key]

    for tname in ("vgg16_conv2_2", "vgg16_conv3_3", "vgg16_conv4_3", "googlenet_4c"):
        for res in (128, 256, 384):
            for steps in (1, 2):
                if res == 384 and steps == 2:
                    continue
                add(f"{tname} {res}px x{steps} every 1",
                    (dream_fn(get(tname), res, steps), 1))
    print(f"\n### C. renderer frame time vs dream work (ms), renderer paced at {args.fps} fps\n")
    hdr = ["config", "frame p50", "frame p99", "frame max", "missed", "fps",
           "dream p50", "dream p99", "dream calls/frame"]
    print(md_table(hdr, rows))

    # ---- levers, from the base config
    rows.clear()
    base = "vgg16_conv3_3"
    add("base: conv3_3 256px x2 every 1", (dream_fn(get(base), 256, 2), 1))
    add("lever: res 192", (dream_fn(get(base), 192, 2), 1))
    add("lever: res 128", (dream_fn(get(base), 128, 2), 1))
    add("lever: layer conv2_2", (dream_fn(get("vgg16_conv2_2"), 256, 2), 1))
    add("lever: steps 1", (dream_fn(get(base), 256, 1), 1))
    add("lever: every 2 frames", (dream_fn(get(base), 256, 2), 2))
    add("lever: every 4 frames", (dream_fn(get(base), 256, 2), 4))
    add("lever: fp16", (dream_fn(get(base, dtype=torch.float16), 256, 2, torch.float16), 1))
    add("lever: channels_last", (dream_fn(get(base, channels_last=True), 256, 2,
                                          channels_last=True), 1))
    add("lever: fp16 + channels_last",
        (dream_fn(get(base, dtype=torch.float16, channels_last=True), 256, 2, torch.float16,
                  channels_last=True), 1))
    add("2 octaves both per call", (dream_fn(get(base), 256, 2, octaves=2), 1))
    add("2 octaves alternating (temporal octaves)",
        (dream_fn(get(base), 256, 2, octaves=2, alternate=True), 1))
    add("combo: 192px x1 fp16 every 2",
        (dream_fn(get(base, dtype=torch.float16), 192, 1, torch.float16), 2))
    print("\n### C. levers from the base config (ms)\n")
    print(md_table(hdr, rows))
    _ = np


if __name__ == "__main__":
    main()
