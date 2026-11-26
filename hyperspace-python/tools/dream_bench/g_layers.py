"""Question G — every dream layer × resolution, eager and compiled.

    uv run python tools/dream_bench/g_layers.py                       # everything
    uv run python tools/dream_bench/g_layers.py --quick               # ~1 min look
    uv run python tools/dream_bench/g_layers.py --layers googlenet \\
        --modes eager,fold,inductor,fold+inductor,step --res 256,540,1080
    uv run python tools/dream_bench/g_layers.py --label show --out bench-show.json

Times one gradient-ascent step of the app's own dream path (dream.TRUNKS,
dream.net_stack / cut_stack, dream.dream_step — not the spike's trunks in
common.py) for every layer the layer menu offers, at each resolution, in
each execution mode, and fits each net's cost to

    ms per step ≈ o × (convs up to the layer) + c × (multiply-adds per pixel) × pixels

so `o` is the fixed cost per conv (launches, dispatch, the BN and ReLU
riding with it) and `c` the cost of the arithmetic. Eager GoogLeNet is
mostly `o` (plan 20: inception5b's ~3 ms of arithmetic measured 29 ms at
256 px); the modes below are the ways to take it out.

Modes (--modes, comma-separated; each is '+'-joined tokens):

    eager       the app as it runs today: the cut stack, torch eager
    fold        fold each eval BatchNorm into its conv first (GoogLeNet's
                57 BNs; VGG has none, so it is eager there) — no compiler
    cl          channels-last memory layout for the net and its input
    aot         torch.compile(backend="aot_eager"): one traced graph, eager
                kernels — what tracing alone saves (Python and dispatch)
    inductor    torch.compile(net): the default inductor backend, which
                fuses the elementwise work around the convs, forward and
                backward (AOTAutograd builds the input-gradient graph)
    max         torch.compile(net, mode="max-autotune-no-cudagraphs")
    step        torch.compile of the whole gradient: normalise → net →
                mean → torch.func.grad → std-normalise in one graph (the
                jitter roll, mask, add and clamp stay outside, as cheap)

e.g. `fold+inductor`, `fold+cl+step`. A mode that fails to build or compile
(an older torch, a missing MPS lowering) is a row that says why; the run
goes on. The first call of a compiled mode is its compile and is reported
apart (`compile s`), never in the timings.

Passes (--pass): `step` (the dream: forward to the layer, gradient to the
input) and `forward` (the activations alone, no gradient — a field from
the net's features, the page's group 6). Precision (--precision): fp32
and/or fp16, the `[dream] precision` choice.

Resolutions are the short side, at --aspect (16:9 by default), sized as
the app sizes an echo (lookback.echo_size): 540 is 960×540. A layer whose
p50 passes --max-ms at one resolution skips the larger ones (said, not
silently dropped).

Load. This times the step alone. The frame budget is shared with the
renderer, so run it twice: once with nothing else open (`--label alone`)
and once with the app on a show patch (`--label show`), and compare.

Weights. Pretrained torchvision weights from --weights (default
<library home>/weights, as the app) or torch's hub cache, downloaded if
neither has them (VGG16 528 MB, GoogLeNet 50 MB). --random-weights skips
them: the timing of a conv does not depend on its weights.

--out writes every row, the fits and the machine as JSON, for the
"Dreaming at 540p" calculator and for comparing two runs.
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from common import md_table, stats_ms
from torch import nn

from hyperspace import dream, library
from hyperspace.lookback import LAYER_INFO, echo_size

RES = [256, 384, 540, 720, 1080]
BACKENDS = ("eager", "aot", "inductor", "max", "step")
FLAGS = ("fold", "cl")
DEFAULT_MODES = "eager,fold,aot,inductor,fold+inductor,step"
# the layers that could run live at 540p by the page's estimate, and the
# ones either side of them, for --quick and --layers shallow
SHALLOW = ["conv1_1", "conv1_2", "conv2_2", "conv3_3",
           "conv1", "conv2", "conv3", "inception3a", "inception3b", "inception4c"]


# ------------------------------------------------------------------ modes

@dataclass(frozen=True)
class Mode:
    backend: str
    fold: bool = False
    cl: bool = False

    @property
    def name(self) -> str:
        return "+".join([t for t, on in (("fold", self.fold), ("cl", self.cl)) if on]
                        + ([] if self.backend == "eager" and (self.fold or self.cl)
                           else [self.backend]))

    @property
    def compiled(self) -> bool:
        return self.backend != "eager"


def parse_mode(text: str) -> Mode:
    """'fold+inductor' → Mode('inductor', fold=True). One backend at most;
    none means eager."""
    toks = [t.strip() for t in text.split("+") if t.strip()]
    bad = [t for t in toks if t not in BACKENDS + FLAGS]
    if bad:
        raise ValueError(f"unknown mode token(s) {bad}: backends {BACKENDS}, flags {FLAGS}")
    backends = [t for t in toks if t in BACKENDS]
    if len(backends) > 1:
        raise ValueError(f"{text!r}: one backend per mode, got {backends}")
    return Mode(backends[0] if backends else "eager", "fold" in toks, "cl" in toks)


def pick_layers(text: str) -> list[str]:
    order = list(dream.TRUNKS)
    out: list[str] = []
    for tok in (t.strip() for t in text.split(",") if t.strip()):
        if tok == "all":
            out += order
        elif tok == "shallow":
            out += SHALLOW
        elif tok in ("vgg", "vgg16"):
            out += [n for n in order if dream.TRUNKS[n][0] == "vgg16"]
        elif tok == "googlenet":
            out += [n for n in order if dream.TRUNKS[n][0] == "googlenet"]
        elif tok in dream.TRUNKS:
            out.append(tok)
        else:
            raise ValueError(f"unknown layer {tok!r} (see --list)")
    seen: set[str] = set()
    return [n for n in out if not (n in seen or seen.add(n))]


# ------------------------------------------------------------------ device

def pick_device(name: str) -> torch.device:
    if name == "auto":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    return torch.device(name)


def syncer(device: torch.device):
    if device.type == "mps":
        return torch.mps.synchronize
    if device.type == "cuda":
        return torch.cuda.synchronize
    return lambda: None


def free(device: torch.device) -> None:
    gc.collect()
    if device.type == "mps":
        torch.mps.empty_cache()
    elif device.type == "cuda":
        torch.cuda.empty_cache()


def machine() -> dict[str, str]:
    info = {"machine": platform.machine(), "system": platform.system(),
            "macos": platform.mac_ver()[0], "python": platform.python_version(),
            "torch": torch.__version__}
    try:
        import torchvision

        info["torchvision"] = torchvision.__version__
    except Exception:  # noqa: BLE001, S110
        pass
    if sys.platform == "darwin":
        for key, name in (("chip", "machdep.cpu.brand_string"), ("memory", "hw.memsize")):
            try:
                info[key] = subprocess.run(["sysctl", "-n", name], capture_output=True,
                                           text=True, timeout=2, check=False).stdout.strip()
            except Exception:  # noqa: BLE001, S110
                pass
        if info.get("memory", "").isdigit():
            info["memory"] = f"{int(info['memory']) / 2**30:.0f} GB"
    return info


# ------------------------------------------------------------------ nets

def fold_bn(stack: list[tuple[str, nn.Module]]) -> int:
    """Fold every eval BatchNorm into the conv before it (torchvision's
    BasicConv2d: conv → bn → relu), in place. Returns how many it folded."""
    from torch.nn.utils.fusion import fuse_conv_bn_eval

    n = 0
    for _, top in stack:
        for m in top.modules():
            conv, bn = getattr(m, "conv", None), getattr(m, "bn", None)
            if isinstance(conv, nn.Conv2d) and isinstance(bn, nn.BatchNorm2d):
                m.conv = fuse_conv_bn_eval(conv.eval(), bn.eval())
                m.bn = nn.Identity()
                n += 1
    return n


class Stacks:
    """Each net's feature stack once per (arch, dtype, fold, cl): the app's
    `net_stack`, pretrained or random, frozen, on the device."""

    def __init__(self, device: torch.device, weights: Path | None):
        self.device, self.weights = device, weights
        self._states: dict[str, dict] = {}
        self._stacks: dict[tuple, list] = {}

    def state(self, arch: str) -> dict | None:
        if self.weights is None:
            return None
        if arch not in self._states:
            self._states[arch] = dream.load_state(arch, self.weights)
        return self._states[arch]

    def get(self, arch: str, dtype: torch.dtype, mode: Mode) -> list:
        key = (arch, dtype, mode.fold, mode.cl)
        if key not in self._stacks:
            stack = dream.net_stack(arch, self.state(arch))
            for _, m in stack:
                m.eval()
                for p in m.parameters():
                    p.requires_grad_(False)
            if mode.fold:
                fold_bn(stack)
            for _, m in stack:
                m.to(device=self.device, dtype=dtype)
                if mode.cl:
                    m.to(memory_format=torch.channels_last)
            self._stacks[key] = stack
        return self._stacks[key]

    def drop(self) -> None:
        self._stacks.clear()


class ChannelsLast(nn.Module):
    def __init__(self, net: nn.Module):
        super().__init__()
        self.net = net

    def forward(self, x):
        return self.net(x.contiguous(memory_format=torch.channels_last))


def conv_cost(net: nn.Module, x: torch.Tensor) -> tuple[int, float]:
    """(convs run, multiply-adds per input pixel) of one forward of `net` on
    `x`, counted by hooks on its Conv2d modules."""
    count = [0, 0]

    def hook(m: nn.Conv2d, _inp, out):
        kh, kw = m.kernel_size
        count[0] += 1
        count[1] += out.shape[-2] * out.shape[-1] * (m.in_channels // m.groups) * m.out_channels * kh * kw

    hooks = [m.register_forward_hook(hook) for m in net.modules() if isinstance(m, nn.Conv2d)]
    try:
        with torch.no_grad():
            net(dream.normalize_in(x))
    finally:
        for h in hooks:
            h.remove()
    return count[0], count[1] / (x.shape[-2] * x.shape[-1])


# ------------------------------------------------------------------ the timed call

STEP, JITTER = 0.03, 8          # the app's defaults; the timing does not depend on them


def make_call(net: nn.Module, mode: Mode, pass_: str, x0: torch.Tensor, mask: torch.Tensor):
    """The function one timing calls: one dream step (or one forward) on `x0`,
    the way `mode` runs it."""
    if mode.cl:
        net = ChannelsLast(net)
    if pass_ == "forward":
        fwd = net if mode.backend == "eager" else compiled(net, mode)

        def call():
            with torch.no_grad():
                return fwd(dream.normalize_in(x0))
        return call
    if mode.backend == "step":
        def grad_of(x):
            return torch.func.grad(lambda y: net(dream.normalize_in(y)).mean())(x)

        def normed(x):
            g = grad_of(x)
            return g / (g.std() + 1e-8)

        gfn = torch.compile(normed, dynamic=False)

        def call():
            oy, ox = torch.randint(-JITTER, JITTER + 1, (2,)).tolist()
            x = torch.roll(x0, shifts=(oy, ox), dims=(2, 3))
            g = torch.roll(gfn(x), shifts=(-oy, -ox), dims=(2, 3))
            return (x0 + STEP * g * mask).clamp_(0.0, 1.0)
        return call
    run = net if mode.backend == "eager" else compiled(net, mode)
    return lambda: dream.dream_step(x0, run, STEP, JITTER, mask)


def compiled(net: nn.Module, mode: Mode) -> nn.Module:
    if mode.backend == "aot":
        return torch.compile(net, backend="aot_eager", dynamic=False)
    if mode.backend == "max":
        return torch.compile(net, mode="max-autotune-no-cudagraphs", dynamic=False)
    return torch.compile(net, dynamic=False)


@dataclass
class Row:
    arch: str
    layer: str
    mode: str
    precision: str
    pass_: str
    res: int
    w: int
    h: int
    convs: int = 0
    macs_px: float = 0.0
    compile_s: float | None = None
    p50: float | None = None
    p90: float | None = None
    p99: float | None = None
    mean: float | None = None
    max: float | None = None
    n: int = 0
    note: str = ""

    @property
    def px(self) -> int:
        return self.w * self.h


def time_call(call, sync, n: int, warm: int) -> tuple[float, dict[str, float]]:
    """(first call s — the compile, for a compiled mode — , stats of n calls
    after `warm` more)."""
    t0 = time.perf_counter()
    call()
    sync()
    first = time.perf_counter() - t0
    for _ in range(max(0, warm - 1)):
        call()
        sync()
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        call()
        sync()
        out.append(time.perf_counter() - t0)
    return first, stats_ms(out)


# ------------------------------------------------------------------ the fit

def fit(rows: list[Row]) -> dict[str, Any] | None:
    """Least squares of ms = o·convs + c·macs_px·px over `rows` (one net,
    mode, precision and pass), neither term below zero. None unless the rows
    hold at least two layers (two conv counts): with one, any fixed cost
    passes for `o` and the split means nothing."""
    pts = [r for r in rows if r.p50 is not None and r.convs]
    if len({r.convs for r in pts}) < 2:
        return None
    A = np.array([[r.convs, r.macs_px * r.px] for r in pts], dtype=float)
    y = np.array([r.p50 for r in pts], dtype=float)
    (o, c), *_ = np.linalg.lstsq(A, y, rcond=None)
    if o < 0 or c < 0:                    # the better one-term fit, the other held at 0
        col = [(0, float(A[:, 0] @ y / (A[:, 0] @ A[:, 0]))),
               (1, float(A[:, 1] @ y / (A[:, 1] @ A[:, 1])))]
        best = min(col, key=lambda kc: float(np.sum((A[:, kc[0]] * kc[1] - y) ** 2)))
        o, c = (best[1], 0.0) if best[0] == 0 else (0.0, best[1])
    resid = A @ np.array([o, c]) - y
    return {"o_ms_per_conv": float(o), "c_ms_per_gmac": float(c * 1e9),
            "gmac_per_s": float(1e3 / (c * 1e9)) if c > 0 else None,
            "max_resid_ms": float(np.abs(resid).max()), "points": len(pts)}


# ------------------------------------------------------------------ main

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layers", default="all",
                    help="comma list: layer names, 'vgg', 'googlenet', 'shallow', 'all'")
    ap.add_argument("--res", default=",".join(map(str, RES)), help="short sides, px")
    ap.add_argument("--aspect", default="16:9", help="W:H of the frame the echo is cut from")
    ap.add_argument("--modes", default=DEFAULT_MODES, help="see above")
    ap.add_argument("--precision", default="fp32", help="fp32, fp16 or both")
    ap.add_argument("--pass", dest="passes", default="step", help="step, forward or both")
    ap.add_argument("--n", type=int, default=30, help="timed calls per row")
    ap.add_argument("--warm", type=int, default=5, help="untimed calls first (the compile is the first)")
    ap.add_argument("--max-ms", type=float, default=250.0,
                    help="a layer slower than this skips its larger resolutions")
    ap.add_argument("--device", default="auto", help="auto (mps, cuda, cpu), mps, cuda, cpu")
    ap.add_argument("--weights", default="", help="weights dir; '' = <library home>/weights")
    ap.add_argument("--random-weights", action="store_true", help="no weights read or downloaded")
    ap.add_argument("--label", default="", help="a name for this run, e.g. alone / show")
    ap.add_argument("--out", default="", help="write the rows, fits and machine as JSON")
    ap.add_argument("--quick", action="store_true",
                    help="--layers shallow --res 256,540 --n 10 --warm 3")
    ap.add_argument("--list", action="store_true", help="list the layers and exit")
    return ap


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.quick:
        args.layers, args.res, args.n, args.warm = "shallow", "256,540", 10, 3
    layers = pick_layers(args.layers)
    modes = [parse_mode(m) for m in args.modes.split(",") if m.strip()]
    res_list = sorted(int(r) for r in args.res.split(",") if r.strip())
    aw, ah = (int(v) for v in args.aspect.split(":"))
    precisions = [p.strip() for p in args.precision.split(",") if p.strip()]
    passes = [p.strip() for p in args.passes.split(",") if p.strip()]
    for p in precisions:
        if p not in ("fp32", "fp16"):
            raise ValueError(f"precision {p!r}: fp32 or fp16")
    for p in passes:
        if p not in ("step", "forward"):
            raise ValueError(f"pass {p!r}: step or forward")
    device = pick_device(args.device)
    sync = syncer(device)
    weights = None if args.random_weights else (
        Path(args.weights).expanduser() if args.weights else library.home() / "weights")
    info = machine()
    print(" · ".join(f"{k} {v}" for k, v in info.items()), f"· device {device.type}",
          f"· weights {'random' if weights is None else weights}", file=sys.stderr)
    try:
        import torch._dynamo

        torch._dynamo.config.cache_size_limit = max(64, torch._dynamo.config.cache_size_limit)
    except Exception:  # noqa: BLE001, S110
        pass

    stacks = Stacks(device, weights)
    rows: list[Row] = []
    costs: dict[tuple[str, int], tuple[int, float]] = {}
    by_arch: dict[str, list[str]] = {}
    for name in layers:
        by_arch.setdefault(dream.TRUNKS[name][0], []).append(name)

    for arch, names in by_arch.items():
        for prec in precisions:
            dtype = torch.float16 if prec == "fp16" else torch.float32
            for mode in modes:
                for pass_ in passes:
                    for name in names:
                        cut = dream.TRUNKS[name][1]
                        too_slow = False
                        for res in res_list:
                            w, h = echo_size(res, aw * 1000, ah * 1000)
                            row = Row(arch, name, mode.name, prec, pass_, res, w, h)
                            rows.append(row)
                            if too_slow:
                                row.note = f"skipped: over {args.max_ms:g} ms at a smaller size"
                                continue
                            try:
                                stack = stacks.get(arch, dtype, mode)
                                net = dream.cut_stack(arch, stack, cut)
                                x0 = torch.rand((1, 3, h, w), device=device, dtype=dtype)
                                mask = torch.ones((1, 1, h, w), device=device, dtype=dtype)
                                if (name, res) not in costs:
                                    costs[(name, res)] = conv_cost(net, x0)
                                row.convs, row.macs_px = costs[(name, res)]
                                if mode.compiled:
                                    torch._dynamo.reset()
                                call = make_call(net, mode, pass_, x0, mask)
                                first, st = time_call(call, sync, args.n, args.warm)
                                if mode.compiled:
                                    row.compile_s = round(first, 2)
                                row.p50, row.p90, row.p99 = st["p50"], st["p90"], st["p99"]
                                row.mean, row.max, row.n = st["mean"], st["max"], args.n
                                too_slow = st["p50"] > args.max_ms
                            except Exception as e:  # noqa: BLE001 — a row that says why
                                row.note = f"{type(e).__name__}: {e}".splitlines()[0][:160]
                            finally:
                                free(device)
                            print(f"{arch:9} {name:12} {mode.name:16} {prec} {pass_:7} "
                                  f"{w}×{h}: " + (f"p50 {row.p50:7.2f}  p99 {row.p99:7.2f} ms"
                                                  if row.p50 is not None else row.note)
                                  + (f"  (compile {row.compile_s} s)" if row.compile_s else ""),
                                  file=sys.stderr, flush=True)
            stacks.drop()
            free(device)

    fits = []
    for key in sorted({(r.arch, r.mode, r.precision, r.pass_) for r in rows}):
        f = fit([r for r in rows if (r.arch, r.mode, r.precision, r.pass_) == key])
        if f is not None:
            fits.append({"arch": key[0], "mode": key[1], "precision": key[2], "pass": key[3], **f})
    return {"label": args.label, "device": device.type, "machine": info,
            "args": {k: v for k, v in vars(args).items() if k != "list"},
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rows": [{**asdict(r), "px": r.px} for r in rows], "fits": fits}


def report(result: dict[str, Any]) -> str:
    rows = result["rows"]
    out = [(f"# Dream layers{(' · ' + result['label']) if result['label'] else ''} · "
            f"{result['machine'].get('chip', result['machine']['machine'])} · {result['device']} · "
            f"torch {result['machine']['torch']}")]
    sizes = sorted({(r["res"], r["w"], r["h"]) for r in rows})
    groups = sorted({(r["arch"], r["precision"], r["pass_"]) for r in rows})
    for arch, prec, pass_ in groups:
        out.append(f"\n## {arch} · {prec} · {pass_}: ms p50 (p99) per {'step' if pass_ == 'step' else 'forward'}\n")
        table = []
        sel = [r for r in rows if (r["arch"], r["precision"], r["pass_"]) == (arch, prec, pass_)]
        for layer in dict.fromkeys(r["layer"] for r in sel):
            for mode in dict.fromkeys(r["mode"] for r in sel):
                cells = []
                comp = None
                for res, _, _ in sizes:
                    r = next((r for r in sel if (r["layer"], r["mode"], r["res"]) == (layer, mode, res)), None)
                    if r is None:
                        cells.append("")
                    elif r["p50"] is not None:
                        cells.append(f"{r['p50']:.1f} ({r['p99']:.1f})")
                        comp = comp if r["compile_s"] is None else max(comp or 0, r["compile_s"])
                    else:
                        cells.append("skipped" if r["note"].startswith("skipped") else "error")
                table.append([layer, mode, *cells, "" if comp is None else f"{comp:.1f}"])
        out.append(md_table(["layer", "mode", *[f"{w}×{h}" for _, w, h in sizes], "compile s"], table))
    errors = sorted({(r["mode"], r["note"]) for r in rows if r["note"] and not r["note"].startswith("skipped")})
    if errors:
        out.append("\n## Errors\n")
        out.append("\n".join(f"- `{m}`: {n}" for m, n in errors))
    if result["fits"]:
        out.append("\n## The fit: ms ≈ o × convs + c × multiply-adds\n")
        out.append("o is the fixed cost per conv (what compiling should remove); c is the "
                   "arithmetic, shown as ms per billion multiply-adds and its rate.\n")
        out.append(md_table(
            ["net", "mode", "precision", "pass", "o ms/conv", "c ms/GMAC", "GMAC/s", "worst miss ms", "points"],
            [[f["arch"], f["mode"], f["precision"], f["pass"], f"{f['o_ms_per_conv']:.3f}",
              f"{f['c_ms_per_gmac']:.3f}", "" if f["gmac_per_s"] is None else f"{f['gmac_per_s']:.0f}",
              f"{f['max_resid_ms']:.2f}", f["points"]] for f in result["fits"]]))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        for name, (arch, _) in dream.TRUNKS.items():
            info = LAYER_INFO.get(name)
            print(f"{name:12} {arch:9} {info[1] if info else ''}")
        return 0
    result = run(args)
    print(report(result))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1))
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
