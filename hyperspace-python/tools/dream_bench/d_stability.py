"""Question D (part 2) — step size / gradient normalisation stability.

    uv run python tools/dream_bench/d_stability.py [--frames 300]

Runs the temporal dream (D <- blend(D, frame, k); s steps on D) on real
Hyperspace frames — the 24-cell, faces + pattern, rotating at 60 fps — for
--frames frames at 256 px with VGG16 conv3_3, over a grid of step size x
gradient normalisation x blend k, and reports per configuration:

  delta 10-40 / last30   mean |D_t - D_{t-1}| per pixel (0-1 units) over
                         frames 10-40 and the last 30: a healthy buffer
                         settles to a steady, small delta; a runaway keeps
                         growing; flicker is a large delta that never settles
  sat                    fraction of pixels the step pushed above 1 (last 30
                         frames): saturation to white is the runaway signal.
                         (Pixels pushed below 0 are the black ground and are
                         benign — 20% of the frame sits at 0.)
  bg leak                mean brightness of D over pixels that are black in
                         every scene frame (the corners): how far the dream
                         hallucinates into empty space instead of staying a
                         wake behind the content
  mean / std             brightness and contrast of D at the end (scene ~0.06)
  sign flip              fraction of pixels whose frame-to-frame delta flipped
                         sign between the last two frames — flicker reads as
                         a value well above 0.5 with a large delta

Verdict: runaway if sat > 0.02 or bg leak > 0.15; flicker if delta last30
> 0.01 and sign flip > 0.55; growing if delta last30 > 1.5 x delta 10-40 and
> 0.01; else stable. The thresholds came from looking at the images
(e_samples.py); they are a guide, not a law.
"""

from __future__ import annotations

import argparse

import torch
from common import (
    SCENE_24CELL,
    Scene,
    TemporalDream,
    frame_to_tensor,
    machine_info,
    make_ctx,
    md_table,
    trunk,
)


def run(scene_frames, bg_mask, net, step_size, norm, k, steps=2, loss_kind="mean"):
    td = TemporalDream(net, k=k, steps=steps, step_size=step_size, norm=norm,
                       loss_kind=loss_kind)
    deltas, sats, flips = [], [], []
    prev, prev_delta = None, None
    for f in scene_frames:
        D = td(f)
        if prev is not None:
            d = D - prev
            deltas.append(d.abs().mean().item())
            if prev_delta is not None:
                flips.append(((d * prev_delta) < 0).float().mean().item())
            prev_delta = d
        sats.append(td.last["clip_hi"].item())
        prev = D
    early = sum(deltas[10:40]) / max(len(deltas[10:40]), 1)
    late = sum(deltas[-30:]) / 30
    sat = sum(sats[-30:]) / 30
    bg = D[0].mean(0)[bg_mask].mean().item()
    mean_late = D.mean().item()
    std_late = D.std().item()
    flip_late = sum(flips[-10:]) / 10
    if sat > 0.02 or bg > 0.15:
        verdict = "runaway"
    elif late > 0.01 and flip_late > 0.55:
        verdict = "flicker"
    elif late > early * 1.5 and late > 0.01:
        verdict = "growing"
    else:
        verdict = "stable"
    return [f"{early:.4f}", f"{late:.4f}", f"{sat:.3f}", f"{bg:.3f}", f"{mean_late:.2f}",
            f"{std_late:.2f}", f"{flip_late:.2f}", verdict]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--res", type=int, default=256)
    args = ap.parse_args()
    print(machine_info())
    ctx = make_ctx()
    sc = Scene(ctx, args.res, args.res, **SCENE_24CELL)
    frames = []
    for _ in range(args.frames):
        sc.step()
        frames.append(frame_to_tensor(sc.read_rgba()))
    stack = torch.cat(frames)  # (N,3,H,W)
    bg_mask = stack.amax(dim=(0, 1)) < 0.02  # never lit in any frame
    print(f"{len(frames)} real frames at {args.res} px; scene mean brightness "
          f"{stack.mean().item():.3f}; always-dark background {bg_mask.float().mean().item():.2f} "
          "of the frame")
    net = trunk("vgg16_conv3_3")

    hdr = ["step", "norm", "k", "delta 10-40", "delta last30", "sat", "bg leak", "mean", "std",
           "sign flip", "verdict"]
    rows = []
    for norm in ("std", "absmean", "l2"):
        for step in (0.005, 0.01, 0.02, 0.04, 0.08):
            r = run(frames, bg_mask, net, step, norm, 0.08)
            rows.append([f"{step:.3f}", norm, "0.08"] + r)
            print(rows[-1], flush=True)
    rows.append(["1.000", "none (raw grad)", "0.08"] + run(frames, bg_mask, net, 1.0, "none", 0.08))
    print(rows[-1])
    print("\n### D. stability over 300 frames, conv3_3 256 px, 2 steps, k = 0.08\n")
    print(md_table(hdr, rows))

    rows = []
    for k in (0.02, 0.05, 0.08, 0.15, 0.3):
        for step in (0.01, 0.02, 0.04):
            r = run(frames, bg_mask, net, step, "std", k)
            rows.append([f"{step:.3f}", "std", f"{k:.2f}"] + r)
            print(rows[-1], flush=True)
    print("\n### D. blend k versus step size (std norm)\n")
    print(md_table(hdr, rows))

    rows = []
    for steps in (1, 2, 4):
        for step in (0.01, 0.02, 0.04):
            r = run(frames, bg_mask, net, step, "std", 0.08, steps=steps)
            rows.append([f"{step:.3f} x{steps}", "std", "0.08"] + r)
            print(rows[-1], flush=True)
    r = run(frames, bg_mask, net, 0.02, "std", 0.08, loss_kind="l2")
    rows.append(["0.020 x2 (L2 loss)", "std", "0.08"] + r)
    print("\n### D. steps per frame versus step size (std norm, k = 0.08)\n")
    print(md_table(hdr, rows))


if __name__ == "__main__":
    main()
