"""Question D (part 1) — what nets/layers/resolutions can we actually run.

    uv run --extra dream python tools/dream_bench/d_nets.py [--res 128,192,256,384,512]

One gradient-ascent step (forward to the hooked layer, mean activation,
grad wrt input, std-normalise, add, clamp) on torch MPS, isolated (no
renderer), fp32 and fp16, for every trunk in common.TRUNKS: VGG16 conv2_2 /
conv3_3 / conv4_3 / conv5_3, GoogLeNet inception 3b / 4c / 4e, MobileNetV2
block 7 / 11, ResNet18 layer2 / layer3. Pretrained torchvision weights.

Then octaves: 1 vs 2 vs 3 in the temporal scheme (all octaves per call, or
one octave per call alternating) at 256 px with conv3_3, 2 steps.

Then cadence: the same step issued back to back versus after 16 / 33 / 66 ms
of idling, because c_contention.py showed "dream every N frames" makes each
call slower (the GPU clocks down between bursts).
"""

from __future__ import annotations

import argparse
import time

import torch
from common import TRUNKS, TemporalDream, bench, dream_step, machine_info, md_table, mps_sync, trunk


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="128,192,256,384,512")
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()
    res_list = [int(r) for r in args.res.split(",")]
    print(machine_info())

    rows = []
    for name in TRUNKS:
        for dt_name, dt in (("fp32", torch.float32), ("fp16", torch.float16)):
            try:
                net = trunk(name, dtype=dt)
            except Exception as e:  # noqa: BLE001
                rows.append([name, dt_name] + [f"ERR {type(e).__name__}"] * len(res_list))
                continue
            row = [name, dt_name]
            for res in res_list:
                x = torch.rand((1, 3, res, res), device="mps", dtype=dt)
                try:
                    st = bench(lambda x=x, net=net: dream_step(x, net, 0.02)[0], n=args.n,
                               warm=3, sync=mps_sync)
                    row.append(f"{st['p50']:.1f} ({st['p99']:.1f})")
                except Exception as e:  # noqa: BLE001
                    row.append(f"ERR {type(e).__name__}")
                    print(name, dt_name, res, repr(e)[:200])
            rows.append(row)
            print(row, flush=True)
            del net
            torch.mps.empty_cache()
    print("\n### D. gradient-ascent step time, ms p50 (p99), isolated\n")
    print(md_table(["trunk", "dtype"] + [f"{r} px" for r in res_list], rows))

    # ---- octaves
    net = trunk("vgg16_conv3_3")
    frame = torch.rand((1, 3, 256, 256), device="mps")
    orow = []
    for octaves in (1, 2, 3):
        for alt in ((False,) if octaves == 1 else (False, True)):
            td = TemporalDream(net, k=0.1, steps=2, octaves=octaves, alternate=alt)
            st = bench(lambda td=td: td(frame), n=args.n, warm=3, sync=mps_sync)
            label = f"{octaves} octave(s)" + (" alternating" if alt else " all per call")
            orow.append([label, st["p50"], st["p99"]])
            print(orow[-1])
    print("\n### D. octaves, conv3_3 256 px, 2 steps per octave, ms per call\n")
    print(md_table(["scheme", "p50", "p99"], orow))

    # ---- cadence
    crow = []
    x = torch.rand((1, 3, 256, 256), device="mps")
    for idle_ms in (0, 8, 16, 33, 66):
        ts = []
        for k in range(args.n + 3):
            if idle_ms:
                time.sleep(idle_ms / 1e3)
            t0 = time.perf_counter()
            dream_step(x, net, 0.02)
            mps_sync()
            if k >= 3:
                ts.append(time.perf_counter() - t0)
        from common import stats_ms

        st = stats_ms(ts)
        crow.append([f"idle {idle_ms} ms between steps", st["p50"], st["p99"]])
        print(crow[-1])
    print("\n### D. cadence: conv3_3 256 px, one step after idling, ms\n")
    print(md_table(["cadence", "p50", "p99"], crow))


if __name__ == "__main__":
    main()
