"""Question E — sample images for judging the look by eye.

    uv run python tools/dream_bench/e_samples.py [--frames 120]

Renders real Hyperspace frames at 1280x820 with the moderngl Renderer
(24-cell or 600-cell, faces + pattern, rotating at speed 1.0 with a fixed
1/60 s dt like ViewState.integrate), downsamples each to the dream
resolution on the GPU, runs the temporal dream (D <- blend(D, frame, k);
s steps on D) for --frames frames, and writes into
docs/plans/assets/06-lookback/:

  <setting>-f030.png / -f060.png / -f120.png   the dream buffer D
  <setting>-triptych.png                       raw frame | D | composite at
                                               frame 120 (composite = scene
                                               + darkened D at 40 %, the
                                               intended effect)

Two look-side options that the spike found necessary, both free at run
time (see common.TemporalDream): pixel jitter (roll by a random offset per
step, the classic Deep Dream trick that turns pixel noise into coherent
texture) and the content-history mask (the gradient step is scaled by a
decaying max of the frame's luminance, so the dream deepens where content
is or recently was and never fills the black ground). The first setting is
the unmasked, unjittered control so the difference is visible.

"res" is the short side; the buffer keeps the 1280:820 aspect, so 256 means
400x256 (1.5x the pixels of the 256x256 squares timed in d_nets.py). The
per-setting dream time printed at the end is for that real buffer. PNGs are
palette-quantised to keep the gallery small.
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import torch
import torch.nn.functional as F
from common import (
    ASSETS,
    SCENE_24CELL,
    SCENE_600CELL,
    Scene,
    TemporalDream,
    composite,
    frame_to_tensor,
    machine_info,
    make_ctx,
    md_table,
    tensor_to_u8,
    trunk,
)
from PIL import Image

W, H = 1280, 820

# name -> (trunk, short side, steps, step size, k, dtype, octaves, alternate,
#          jitter, mask decay, scene)
SETTINGS = {
    "conv3_3-256-x2-plain": ("vgg16_conv3_3", 256, 2, 0.02, 0.08, "fp32", 1, False, 0, 0.0,
                             "24cell"),
    "conv3_3-256-x2": ("vgg16_conv3_3", 256, 2, 0.03, 0.08, "fp32", 1, False, 8, 0.97, "24cell"),
    "conv4_3-256-x1": ("vgg16_conv4_3", 256, 1, 0.04, 0.08, "fp32", 1, False, 8, 0.97, "24cell"),
    "conv2_2-256-x2": ("vgg16_conv2_2", 256, 2, 0.03, 0.08, "fp32", 1, False, 8, 0.97, "24cell"),
    "inception4c-192-x2": ("googlenet_4c", 192, 2, 0.03, 0.08, "fp32", 1, False, 6, 0.97,
                           "24cell"),
    "conv3_3-384-x2-fp16": ("vgg16_conv3_3", 384, 2, 0.03, 0.08, "fp16", 1, False, 12, 0.97,
                            "600cell"),
    "conv3_3-256-x2-oct2alt": ("vgg16_conv3_3", 256, 2, 0.03, 0.08, "fp32", 2, True, 8, 0.97,
                               "600cell"),
}


def save(img: np.ndarray, path, quantize: bool = True, max_w: int | None = None) -> int:
    im = Image.fromarray(img)
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    if quantize:
        im = im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    im.save(path, optimize=True)
    return path.stat().st_size


def triptych(raw_rgb: np.ndarray, dream_rgb: np.ndarray, comp_rgb: np.ndarray,
             panel_w: int = 426) -> np.ndarray:
    panel_h = round(panel_w * H / W)
    out = Image.new("RGB", (panel_w * 3 + 8, panel_h), (24, 24, 24))
    for i, img in enumerate((raw_rgb, dream_rgb, comp_rgb)):
        out.paste(Image.fromarray(img).resize((panel_w, panel_h), Image.LANCZOS),
                  (i * (panel_w + 4), 0))
    return np.asarray(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--only", default="", help="comma-separated setting names")
    args = ap.parse_args()
    print(machine_info())
    ASSETS.mkdir(parents=True, exist_ok=True)
    ctx = make_ctx()
    scenes = {"24cell": Scene(ctx, W, H, speed=1.0, **{**SCENE_24CELL, "bright": 1.3}),
              "600cell": Scene(ctx, W, H, speed=1.0, **{**SCENE_600CELL, "bright": 1.3})}
    total = 0
    rows = []
    names = [n for n in args.only.split(",") if n] or list(SETTINGS)
    for name in names:
        tname, short, steps, step, k, dt_name, octaves, alt, jit, mdecay, sname = SETTINGS[name]
        dtype = torch.float16 if dt_name == "fp16" else torch.float32
        net = trunk(tname, dtype=dtype)
        td = TemporalDream(net, k=k, steps=steps, step_size=step, octaves=octaves, alternate=alt,
                           jitter=jit, mask_decay=mdecay)
        dh, dw = short, round(short * W / H / 8) * 8
        sc = scenes[sname]
        # restart the scene so every setting sees the same frames
        sc.state.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
        sc.frame, sc.t = 0, 0.0
        times = []
        for f in range(1, args.frames + 1):
            sc.step()
            raw = sc.read_rgba()
            full = frame_to_tensor(raw)
            small = F.interpolate(full, size=(dh, dw), mode="bilinear", antialias=True,
                                  align_corners=False).to(dtype)
            t0 = time.perf_counter()
            D = td(small)
            torch.mps.synchronize()
            times.append(time.perf_counter() - t0)
            if f in (30, 60, args.frames):
                total += save(tensor_to_u8(D), ASSETS / f"{name}-f{f:03d}.png")
            if f == args.frames:
                scene_rgb = np.ascontiguousarray(raw[::-1, :, :3])
                d8 = tensor_to_u8(D)
                comp = composite(scene_rgb, d8, alpha=0.4, darken=0.7)
                total += save(triptych(scene_rgb, d8, comp), ASSETS / f"{name}-triptych.png")
        ms = sorted(times[5:])
        rows.append([name, sname, f"{dw}x{dh}", steps, step, k, dt_name,
                     f"{octaves}{' alt' if alt else ''}", jit, mdecay, ms[len(ms) // 2] * 1e3,
                     ms[int(0.99 * (len(ms) - 1))] * 1e3])
        print(rows[-1], flush=True)
        del net, td
        torch.mps.empty_cache()
    print("\n### E. sample settings (dream time per frame on the real 1280:820 buffer, ms)\n")
    print(md_table(["setting", "scene", "buffer", "steps", "step", "k", "dtype", "octaves",
                    "jitter", "mask decay", "p50", "p99"], rows))
    print(f"\ngallery size: {total / 1e6:.2f} MB in {ASSETS}")


if __name__ == "__main__":
    main()
