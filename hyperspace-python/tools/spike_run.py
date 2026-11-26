#!/usr/bin/env python3
"""Run the real app on a patch for a few minutes and find where the slow
frames come from (`tools/spike_recorder.py` says what is recorded).

    uv run python tools/spike_run.py PATCH.json --out ~/hyperspace-spikes

PATCH is read, never written: it is copied into the driver's scratch home
(a fresh temp folder, the corpus library, no devices) and loaded from the
copy. Nothing is written beside the patch or into any Drive folder; the
recording goes to `--out` and a report is printed.

The run: a warm-up, then `--rounds` rounds; in each, every condition once in
a shuffled order, `--block` frames each (the first 40 of a block are the
switch settling and are not counted). The warm-up is 45 s: on every run
here a burst of 350-650 ms frames came ~23 s after the start, and a short
warm-up handed it to whichever block ran first. Conditions: base, thumbs_off,
readback_off, gc_frozen, additive_flip. `--set view.shape=108` sets a param
after the load (a stand-in patch).

Nothing here is captured: the driver's screenshots are off. Leave the Mac
alone while it runs (a second app, a screensaver, a hot lap of the fan and
the shuffle will not cancel it). Expect rounds x 5 x block frames: the
default is 5 x 5 x 400 = 10,000 frames, about three minutes at 60 fps.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import app_driver
import spike_recorder as sr


def make_script(a, rec: sr.Recorder, saved: dict):
    def script(d, panel):
        reg = panel.reg
        home = Path(os.environ["HYPERSPACE_HOME"])
        scratch = home / "spike-patch.json"
        shutil.copyfile(a.patch, scratch)                 # read the patch, write only the copy
        doc = json.loads(scratch.read_text())
        panel.library.loaded_patch.load_doc(doc)
        for item in a.set:
            pid, _, v = item.partition("=")
            p = reg[pid]
            p.set(type(p.get())(float(v)) if not isinstance(p.get(), bool) else v in ("1", "true"))
        yield from d.wait(30)
        saved["patch"] = doc.get("name", Path(a.patch).stem)
        saved["additive"] = bool(reg["view.frac_additive"].base)
        saved["shape"] = reg["view.shape"].base
        rec.install()
        if a.gil:
            rec.start_gil_probe()
        rec.meta.update(patch=saved["patch"], additive_at_start=saved["additive"],
                        shape=saved["shape"], block=a.block, rounds=a.rounds, seed=a.seed)
        rng = random.Random(a.seed)

        t_warm = time.perf_counter()
        n_warm = 0
        # warm-up by frames *and* seconds: a first thumbnail, a shader, a texture made
        # lazily is a one-off that a short warm-up hands to the first block
        while n_warm < a.warmup or time.perf_counter() - t_warm < a.warmup_s:
            n_warm += 1
            yield
        for rnd in range(a.rounds):
            order = list(sr.CONDITIONS)
            rng.shuffle(order)
            for cond in order:
                rec.start_block(cond, rnd)
                import gc
                gc.collect()                              # every block starts with the same heap
                rec.flags["thumbs_off"] = cond == "thumbs_off"
                rec.flags["readback_off"] = cond == "readback_off"
                if cond == "gc_frozen":
                    gc.disable()
                if cond == "additive_flip":
                    reg["view.frac_additive"].set(not saved["additive"])
                for _ in range(a.block):
                            yield
                gc.enable()
                rec.flags["thumbs_off"] = rec.flags["readback_off"] = False
                reg["view.frac_additive"].set(saved["additive"])
            print(f"round {rnd + 1}/{a.rounds}: {len(rec.rows)} frames", flush=True)
        rec.uninstall()

    return script


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("patch", type=Path, help="a loadable patch (.json), read only")
    ap.add_argument("--out", type=Path, default=Path.home() / "hyperspace-spikes")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--block", type=int, default=400, help="frames a block")
    ap.add_argument("--warmup", type=int, default=240, help="frames, and at least --warmup-s")
    ap.add_argument("--warmup-s", type=float, default=45.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--gil", action="store_true",
                    help="also run a thread that measures how late a 1 ms sleep wakes (a run of its own)")
    ap.add_argument("--set", action="append", default=[], metavar="ID=VALUE")
    a = ap.parse_args()
    if not a.patch.is_file():
        sys.exit(f"no such patch: {a.patch}")
    need = a.warmup + a.rounds * len(sr.CONDITIONS) * a.block + 200
    os.environ["HYPERSPACE_FRAMES"] = str(need + 1000)
    a.out.mkdir(parents=True, exist_ok=True)
    rec, saved = sr.Recorder(), {}
    scratch = a.out / "scratch"                           # the driver's capture folder: left empty
    app_driver.run(make_script(a, rec, saved), scratch, every=10**9, corpus=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = a.out / f"spikes-{stamp}.json"
    rec.save(path)
    doc = json.loads(path.read_text())
    print()
    sr.report(doc)
    print(f"\nrecording: {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
