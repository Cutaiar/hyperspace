"""Question B.2 — MLX versus torch MPS for the gradient-ascent step.

    uv run python tools/dream_bench/b_mlx.py [--res 128,256,512]

Two trunks, identical weights in both frameworks:

  small     conv1_1..conv3_3 of a VGG-16 shape, random weights (12 GMAC fwd
            at 256 px) — the framework comparison proper
  vgg16_3_3 the pretrained torchvision VGG16 cut at conv3_3, weights
            converted OIHW -> OHWI for MLX — the real thing

For each: one gradient-ascent step (forward, mean activation, grad wrt the
input, std-normalise, add, clamp) timed with the device drained
(torch.mps.synchronize / mx.eval). MLX is measured eager and under
mx.compile. Then the host <-> device conversions MLX makes cheap on unified
memory, and the DLPack bridge to torch MPS (zero copy, see b_iosurface.py).
"""

from __future__ import annotations

import argparse
import time

import mlx.core as mx
import numpy as np
import torch
from common import IMAGENET_MEAN, IMAGENET_STD, SmallTrunk, bench, machine_info, md_table, mps_sync
from common import trunk as torch_trunk
from mlx import nn


class MLXTrunk(nn.Module):
    """nn.Sequential-alike of Conv2d/ReLU/MaxPool built from a torch Sequential."""

    def __init__(self, torch_seq):
        super().__init__()
        self.layers = []
        for m in torch_seq:
            name = type(m).__name__
            if name == "Conv2d":
                w = m.weight.detach().cpu().numpy().transpose(0, 2, 3, 1)  # OIHW -> OHWI
                b = m.bias.detach().cpu().numpy()
                c = nn.Conv2d(w.shape[3], w.shape[0], w.shape[1], padding=m.padding[0])
                c.weight = mx.array(w)
                c.bias = mx.array(b)
                self.layers.append(c)
            elif name == "ReLU":
                self.layers.append(nn.ReLU())
            elif name == "MaxPool2d":
                self.layers.append(nn.MaxPool2d(2))
            else:
                raise ValueError(name)

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        return x


def mlx_step_fn(net, step: float):
    mean = mx.array(IMAGENET_MEAN).reshape(1, 1, 1, 3)
    std = mx.array(IMAGENET_STD).reshape(1, 1, 1, 3)

    def loss(x):
        return net((x - mean) / std).mean()

    g = mx.grad(loss)

    def step_fn(x):
        gr = g(x)
        gr = gr / (mx.std(gr) + 1e-8)
        return mx.clip(x + step * gr, 0.0, 1.0)

    return step_fn


def torch_step_fn(net, step: float):
    from common import dream_step

    def step_fn(x):
        out, _ = dream_step(x, net, step)
        return out

    return step_fn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="128,256,512")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()
    res_list = [int(r) for r in args.res.split(",")]
    print(machine_info())
    mx.set_default_device(mx.gpu)

    rows = []
    for tname in ["small", "vgg16_conv3_3"]:
        if tname == "small":
            tnet = SmallTrunk.torch()
        else:
            tnet = torch_trunk(tname)
        mnet = MLXTrunk(tnet)
        mx.eval(mnet.parameters())
        tnet16 = None
        for dt_name, dt in [("fp32", torch.float32), ("fp16", torch.float16)]:
            for res in res_list:
                # torch
                if dt_name == "fp16" and tnet16 is None:
                    tnet16 = (SmallTrunk.torch(dtype=dt) if tname == "small"
                              else torch_trunk(tname, dtype=dt))
                net_t = tnet if dt_name == "fp32" else tnet16
                x = torch.rand((1, 3, res, res), device="mps", dtype=dt)
                sf = torch_step_fn(net_t, 0.02)
                st = bench(lambda sf=sf, x=x: sf(x), n=args.n, warm=3, sync=mps_sync)
                rows.append([tname, dt_name, res, "torch MPS", st["p50"], st["p99"]])

                # mlx eager
                mdt = mx.float32 if dt_name == "fp32" else mx.float16
                if dt_name == "fp16":
                    mnet16 = MLXTrunk(tnet)
                    mnet16.set_dtype(mx.float16)
                    mx.eval(mnet16.parameters())
                    net_m = mnet16
                else:
                    net_m = mnet
                xm = mx.random.uniform(shape=(1, res, res, 3)).astype(mdt)
                mx.eval(xm)
                msf = mlx_step_fn(net_m, 0.02)

                def run_m(msf=msf, xm=xm):
                    y = msf(xm)
                    mx.eval(y)
                    return y

                try:
                    st = bench(run_m, n=args.n, warm=3)
                    rows.append([tname, dt_name, res, "MLX eager", st["p50"], st["p99"]])
                    csf = mx.compile(msf)

                    def run_c(csf=csf, xm=xm):
                        y = csf(xm)
                        mx.eval(y)
                        return y

                    st = bench(run_c, n=args.n, warm=3)
                    rows.append([tname, dt_name, res, "MLX compiled", st["p50"], st["p99"]])
                except Exception as e:  # noqa: BLE001
                    rows.append([tname, dt_name, res, "MLX", f"ERR {type(e).__name__}", ""])
                print(rows[-3:][0], rows[-1])
        del tnet, tnet16, mnet
        torch.mps.empty_cache()

    print("\n### B.2 gradient-ascent step, ms (p50 / p99)\n")
    print(md_table(["trunk", "dtype", "res", "framework", "p50", "p99"], rows))

    # ---- conversions -------------------------------------------------------
    print("\n### B.2 host <-> device conversions at 256/512 px (ms, p50)\n")
    crow = []
    for res in (256, 512):
        a = np.random.rand(res, res, 4).astype(np.float32)
        u8 = (a * 255).astype(np.uint8)

        def np_to_mlx(u8=u8):
            m = mx.array(u8)
            mx.eval(m)
            return m

        st = bench(np_to_mlx)
        crow.append([res, "np u8 -> mx.array (+eval)", st["p50"]])
        m = mx.array(u8)
        mx.eval(m)
        st = bench(lambda m=m: np.asarray(m))
        crow.append([res, "mx.array -> np.asarray", st["p50"]])
        mf = mx.array(a)
        mx.eval(mf)
        st = bench(lambda mf=mf: np.array(mf))
        crow.append([res, "mx.array f32 -> np.array (copy)", st["p50"]])
        t = torch.from_numpy(u8).to("mps")
        mps_sync()

        def t2m(t=t):
            mm = mx.from_dlpack(t)
            mx.eval(mm)
            return mm

        st = bench(t2m)
        crow.append([res, "torch MPS -> mx.from_dlpack", st["p50"]])

        def m2t(m=m):
            tt = torch.from_dlpack(m)
            torch.mps.synchronize()
            return tt

        st = bench(m2t)
        crow.append([res, "mlx -> torch.from_dlpack (+sync)", st["p50"]])

        # the round trip a torch dream would need: mlx sees torch's result
        st = bench(lambda t=t: (t.float(), mps_sync())[0])
        crow.append([res, "(ref) one torch elementwise op + sync", st["p50"]])
    print(md_table(["res", "conversion", "p50 ms"], crow))
    _ = time


if __name__ == "__main__":
    main()
