"""Question A — the GL -> compute -> GL copy path and how it scales.

    uv run --extra dream python tools/dream_bench/a_copy_path.py [--res 128,256,...]

For each square resolution it times, one part at a time (each bracketed by
its own device sync so the number is the part, not the pipeline):

  read_sync      fbo.read()  — glReadPixels straight into a Python bytes
  pbo_enqueue    fbo.read_into(pbo) — glReadPixels into a PIXEL_PACK buffer
  pbo_collect    pbo.read() one frame later (map + memcpy)
  up_u8          numpy RGBA8 -> torch MPS (pageable)
  up_u8_pinned   same, from a pinned host tensor, non_blocking
  up_f32         numpy float32 (1,3,H,W) -> MPS (the naive path)
  up_alias       memcpy into torch.mps._host_alias_storage of a resident MPS
                 tensor (no staging copy: the MTLBuffer *is* the host buffer)
  cvt            u8 RGBA (H,W,4) -> float (1,3,H,W) [0,1] on the GPU
  down_f32       (1,3,H,W) float MPS -> CPU numpy
  down_u8        (H,W,4) u8 MPS -> CPU (convert on GPU first)
  down_alias     torch.mps.synchronize + read through the host alias
  tex_write_u8   moderngl texture.write() RGBA8
  tex_write_f32  texture.write() RGB32F

Then the whole round trip at 256 px, the way the feature would do it, so the
3.4 ms measured earlier decomposes into its parts.
"""

from __future__ import annotations

import argparse
import sys
import time

import moderngl
import numpy as np
import torch
from common import Scene, bench, fmt, machine_info, make_ctx, md_table, mps_sync

RES = [128, 192, 256, 384, 512, 768]


def alias_view(t: torch.Tensor) -> np.ndarray:
    """numpy view over the host-visible MTLBuffer of an MPS tensor."""
    st = torch.mps._host_alias_storage(t.untyped_storage())
    cpu = torch.empty(0, dtype=t.dtype, device="cpu").set_(st, t.storage_offset(), t.shape,
                                                         t.stride())
    return cpu.numpy()


def run(res: int, ctx: moderngl.Context) -> dict[str, dict]:
    out = {}
    sc = Scene(ctx, res, res)
    sc.step()
    ctx.finish()
    nbytes = res * res * 4

    # -- GL -> host
    out["read_sync"] = bench(lambda: sc.fbo.read(components=4), sync=ctx.finish)

    pbo = [ctx.buffer(reserve=nbytes), ctx.buffer(reserve=nbytes)]
    i = [0]

    def enqueue():
        sc.fbo.read_into(pbo[i[0] % 2], components=4)
        i[0] += 1

    out["pbo_enqueue"] = bench(enqueue, sync=None)  # cost to issue, no wait
    ctx.finish()

    def collect():
        return pbo[(i[0] + 1) % 2].read()  # the buffer written a frame ago

    out["pbo_collect"] = bench(collect, sync=None)

    # the realistic pairing: enqueue this frame, collect last frame's
    def pair():
        sc.step()
        sc.fbo.read_into(pbo[i[0] % 2], components=4)
        i[0] += 1
        return pbo[i[0] % 2].read()

    out["pbo_pair+render"] = bench(pair, sync=ctx.finish)
    out["render_only"] = bench(sc.step, sync=ctx.finish)

    # -- host -> MPS
    raw = np.frombuffer(sc.fbo.read(components=4), dtype=np.uint8).reshape(res, res, 4).copy()
    out["up_u8"] = bench(lambda: torch.from_numpy(raw).to("mps"), sync=mps_sync)
    pinned = torch.empty((res, res, 4), dtype=torch.uint8, pin_memory=True)
    raw_t = torch.from_numpy(raw)

    def up_pinned():
        pinned.copy_(raw_t)
        return pinned.to("mps", non_blocking=True)

    out["up_u8_pinned"] = bench(up_pinned, sync=mps_sync)
    f32 = np.ascontiguousarray(raw[None, :, :, :3].transpose(0, 3, 1, 2)).astype(np.float32)
    out["up_f32"] = bench(lambda: torch.from_numpy(f32).to("mps"), sync=mps_sync)

    resident = torch.zeros((res, res, 4), dtype=torch.uint8, device="mps")
    mps_sync()
    view = alias_view(resident)

    def up_alias():
        torch.mps.synchronize()
        view[...] = raw

    out["up_alias"] = bench(up_alias, sync=None)
    assert (resident.cpu().numpy() == raw).all()

    # -- GPU-side conversion
    g8 = torch.from_numpy(raw).to("mps")

    def cvt():
        return g8[:, :, :3].permute(2, 0, 1).unsqueeze(0).float().div_(255.0).contiguous()

    out["cvt"] = bench(cvt, sync=mps_sync)
    gf = cvt()

    # -- MPS -> host
    out["down_f32"] = bench(lambda: gf.cpu().numpy(), sync=None)
    out["down_u8"] = bench(
        lambda: (gf[0].permute(1, 2, 0) * 255).to(torch.uint8).cpu().numpy(), sync=None)
    gu8 = (gf[0].permute(1, 2, 0) * 255).to(torch.uint8).contiguous()
    mps_sync()
    v2 = alias_view(gu8)

    def down_alias():
        torch.mps.synchronize()
        return v2.copy()

    out["down_alias"] = bench(down_alias, sync=None)

    # -- host -> GL texture
    tex8 = ctx.texture((res, res), 3)
    rgb8 = np.ascontiguousarray(raw[:, :, :3])
    out["tex_write_u8"] = bench(lambda: tex8.write(rgb8.tobytes()), sync=ctx.finish)
    out["tex_write_u8_view"] = bench(lambda: tex8.write(rgb8), sync=ctx.finish)
    texf = ctx.texture((res, res), 3, dtype="f4")
    rgbf = np.ascontiguousarray(f32[0].transpose(1, 2, 0))
    out["tex_write_f32"] = bench(lambda: texf.write(rgbf), sync=ctx.finish)

    for b in pbo:
        b.release()
    tex8.release()
    texf.release()
    sc.fbo.release()
    sc.tex.release()
    return out


def round_trip(ctx: moderngl.Context, res: int = 256) -> list[list]:
    """The whole thing, timed part by part with the sync points a real
    pipeline would have (one sync at the end of each leg)."""
    sc = Scene(ctx, res, res)
    net = None
    rows = []
    t_read, t_up, t_cvt, t_down, t_tex = [], [], [], [], []
    tex = ctx.texture((res, res), 3)
    for k in range(60):
        sc.step()
        t0 = time.perf_counter()
        raw = np.frombuffer(sc.fbo.read(components=4), dtype=np.uint8).reshape(res, res, 4)
        t1 = time.perf_counter()
        g = torch.from_numpy(raw).to("mps")
        mps_sync()
        t2 = time.perf_counter()
        f = g[:, :, :3].permute(2, 0, 1).unsqueeze(0).float().div_(255.0).contiguous()
        mps_sync()
        t3 = time.perf_counter()
        back = (f[0].permute(1, 2, 0) * 255).to(torch.uint8).contiguous().cpu().numpy()
        t4 = time.perf_counter()
        tex.write(back)
        ctx.finish()
        t5 = time.perf_counter()
        if k >= 10:
            t_read.append(t1 - t0)
            t_up.append(t2 - t1)
            t_cvt.append(t3 - t2)
            t_down.append(t4 - t3)
            t_tex.append(t5 - t4)
    del net
    from common import stats_ms

    for name, s in [("glReadPixels sync", t_read), ("np->MPS u8", t_up), ("u8->f32 on GPU", t_cvt),
                    ("f32->u8->CPU", t_down), ("texture.write + finish", t_tex)]:
        st = stats_ms(s)
        rows.append([name, st["p50"], st["p99"]])
    tot = [a + b + c + d + e for a, b, c, d, e in zip(t_read, t_up, t_cvt, t_down, t_tex)]
    st = stats_ms(tot)
    rows.append(["**total round trip**", st["p50"], st["p99"]])
    return rows


def round_trip_alias(ctx: moderngl.Context, res: int = 256) -> list[list]:
    """Same trip through torch.mps._host_alias_storage: glReadPixels lands in
    the MPS tensor's own MTLBuffer, and texture.write reads the result's."""
    from common import stats_ms

    sc = Scene(ctx, res, res)
    tex = ctx.texture((res, res), 4)
    inbuf = torch.zeros((res, res, 4), dtype=torch.uint8, device="mps")
    outbuf = torch.zeros((res, res, 4), dtype=torch.uint8, device="mps")
    mps_sync()
    in_view, out_view = alias_view(inbuf), alias_view(outbuf)
    t_read, t_cvt, t_back, t_tex = [], [], [], []
    for k in range(60):
        sc.step()
        t0 = time.perf_counter()
        torch.mps.synchronize()             # nothing may still read inbuf
        sc.fbo.read_into(in_view, components=4)
        t1 = time.perf_counter()
        f = inbuf[:, :, :3].permute(2, 0, 1).unsqueeze(0).float().div_(255.0).contiguous()
        mps_sync()
        t2 = time.perf_counter()
        outbuf[:, :, :3] = (f[0].permute(1, 2, 0) * 255).to(torch.uint8)
        torch.mps.synchronize()
        t3 = time.perf_counter()
        tex.write(out_view)
        ctx.finish()
        t4 = time.perf_counter()
        if k >= 10:
            t_read.append(t1 - t0)
            t_cvt.append(t2 - t1)
            t_back.append(t3 - t2)
            t_tex.append(t4 - t3)
    rows = []
    for name, s in [("glReadPixels into alias", t_read), ("u8->f32 on GPU", t_cvt),
                    ("f32->u8 on GPU + sync", t_back), ("texture.write(alias) + finish", t_tex)]:
        st = stats_ms(s)
        rows.append([name, st["p50"], st["p99"]])
    tot = [a + b + c + d for a, b, c, d in zip(t_read, t_cvt, t_back, t_tex)]
    st = stats_ms(tot)
    rows.append(["**total round trip (alias)**", st["p50"], st["p99"]])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default=",".join(map(str, RES)))
    args = ap.parse_args()
    res_list = [int(r) for r in args.res.split(",")]
    print(machine_info())
    ctx = make_ctx()
    results = {}
    for r in res_list:
        results[r] = run(r, ctx)
        print(f"-- {r} px")
        for k, v in results[r].items():
            print(f"   {k:20s} {fmt(v)}")
        sys.stdout.flush()

    keys = list(next(iter(results.values())).keys())
    print("\n### A. copy path, p50 ms (p99 in parentheses)\n")
    rows = []
    for k in keys:
        rows.append([k] + [f"{results[r][k]['p50']:.2f} ({results[r][k]['p99']:.2f})"
                           for r in res_list])
    print(md_table(["part"] + [f"{r} px" for r in res_list], rows))
    print("\n### A. round trip at 256 px, part by part (ms)\n")
    print(md_table(["part", "p50", "p99"], round_trip(ctx, 256)))
    print("\n### A. round trip at 256 px through the MPS host alias (ms)\n")
    print(md_table(["part", "p50", "p99"], round_trip_alias(ctx, 256)))
    print("\n### A. round trip at 512 px through the MPS host alias (ms)\n")
    print(md_table(["part", "p50", "p99"], round_trip_alias(ctx, 512)))
    # bandwidth reference: the bytes moved per leg
    print("\nbytes per frame (RGBA8 / RGB32F):",
          ", ".join(f"{r}px {r*r*4/1e6:.2f}/{r*r*12/1e6:.2f} MB" for r in res_list))


if __name__ == "__main__":
    main()
