"""Shared helpers for the WP6-0 look-back (temporal Deep Dream) spike.

Nothing here is imported by the `hyperspace` package. Every script in this
directory is standalone:

    uv run python tools/dream_bench/<name>.py

The helpers cover three things the benchmarks all need:

  * a real Hyperspace frame source (`Scene`) — the moderngl Renderer drawing
    into an FBO, rotating a little each frame like ViewState.integrate;
  * pretrained torchvision trunks cut at a named layer (`trunk()`), so the
    step cost of "VGG16 conv3_3" is the cost of the real thing;
  * the temporal dream step itself (`dream_step`, `TemporalDream`) —
    gradient ascent on the mean activation of the hooked layer, gradient
    std-normalised, warm-started from the running buffer D.

Timing on MPS always brackets with torch.mps.synchronize(); the numbers are
wall-clock for the whole step, launch overhead included, which is what the
frame budget sees.
"""

from __future__ import annotations

import platform
import statistics
import sys
import time
from pathlib import Path

import moderngl
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperspace.render import Renderer
from hyperspace.view import ViewState

ASSETS = ROOT / "docs" / "plans" / "assets" / "06-lookback"

# Judge scenes for the spike: a 24-cell and a 600-cell, faces + pattern on.
# Shape indices follow hyperspace.geometry.SHAPES.
SCENE_24CELL = {"shape": 10, "faces": True, "pattern": 2, "bright": 1.0}
SCENE_600CELL = {"shape": 16, "faces": True, "pattern": 3, "bright": 1.0}


def machine_info() -> dict[str, str]:
    import torch

    info = {
        "machine": platform.machine(),
        "macos": platform.mac_ver()[0],
        "python": platform.python_version(),
        "torch": torch.__version__,
        "moderngl": moderngl.__version__,
    }
    try:
        import torchvision

        info["torchvision"] = torchvision.__version__
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        import mlx.core as mx

        info["mlx"] = mx.__version__
    except Exception:  # noqa: BLE001, S110
        pass
    return info


# --------------------------------------------------------------------------
# timing


def stats_ms(samples: list[float]) -> dict[str, float]:
    s = sorted(samples)
    n = len(s)
    return {
        "p50": statistics.median(s) * 1e3,
        "p90": s[min(n - 1, int(0.9 * n))] * 1e3,
        "p99": s[min(n - 1, int(0.99 * n))] * 1e3,
        "mean": statistics.fmean(s) * 1e3,
        "min": s[0] * 1e3,
        "max": s[-1] * 1e3,
    }


def fmt(st: dict[str, float]) -> str:
    return f"p50 {st['p50']:.2f}  p99 {st['p99']:.2f}  max {st['max']:.2f} ms"


def bench(fn, n: int = 50, warm: int = 5, sync=None) -> dict[str, float]:
    """Time fn() n times (after `warm` warm-ups); `sync` drains the device."""
    for _ in range(warm):
        fn()
        if sync:
            sync()
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        if sync:
            sync()
        out.append(time.perf_counter() - t0)
    return stats_ms(out)


def mps_sync():
    import torch

    torch.mps.synchronize()


def md_table(headers: list[str], rows: list[list]) -> str:
    def cell(v):
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)

    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        lines.append("| " + " | ".join(cell(v) for v in r) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# the real renderer, offscreen


class Scene:
    """A Hyperspace scene rendered by the real moderngl pipeline into an FBO.

    `step()` advances the rotation by a fixed dt (mirrors ViewState.integrate
    at 60 fps) and draws one frame. The FBO stays bound; readers pull pixels
    with `read_rgba()` / `fbo.read_into()`.
    """

    def __init__(self, ctx: moderngl.Context, w: int, h: int, dt: float = 1 / 60,
                 shape: int = 10, faces: bool = True, pattern: int = 2, bright: float = 1.0,
                 speed: float = 0.30, alpha: bool = False, **view):
        self.ctx, self.w, self.h, self.dt = ctx, w, h, dt
        self.state = ViewState(shape=shape, faces=faces, pattern=pattern, bright=bright,
                               speed=speed, **view)
        self.state.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
        self.state.yaw, self.state.pitch = 0.4, 0.25
        self.tex = ctx.texture((w, h), 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.renderer = Renderer(ctx)
        if alpha:
            self.renderer.bg_alpha = 0.0  # overlay mode: transparent ground
        self.t = 0.0
        self.frame = 0

    def step(self) -> None:
        self.state.integrate(self.dt)
        self.t += self.dt
        self.frame += 1
        self.fbo.use()
        self.ctx.viewport = (0, 0, self.w, self.h)
        self.renderer.draw(self.state, self.w, self.h, t_now=self.t)

    def read_rgba(self) -> np.ndarray:
        """Sync glReadPixels; (h, w, 4) uint8, bottom-up (GL order)."""
        return np.frombuffer(self.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4)

    def read_rgb_topdown(self) -> np.ndarray:
        return self.read_rgba()[::-1, :, :3].copy()


def make_ctx() -> moderngl.Context:
    return moderngl.create_context(standalone=True)


# --------------------------------------------------------------------------
# nets


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# name -> (torchvision ctor, how to cut). VGG indices are into .features and
# include the ReLU after the named conv, as Deep Dream conventionally hooks.
TRUNKS = {
    "vgg16_conv2_2": ("vgg16", ("features", 9)),
    "vgg16_conv3_3": ("vgg16", ("features", 16)),
    "vgg16_conv4_3": ("vgg16", ("features", 23)),
    "vgg16_conv5_3": ("vgg16", ("features", 30)),
    "googlenet_3b": ("googlenet", ("children", "inception3b")),
    "googlenet_4c": ("googlenet", ("children", "inception4c")),
    "googlenet_4e": ("googlenet", ("children", "inception4e")),
    "mobilenet_v2_b7": ("mobilenet_v2", ("features", 8)),
    "mobilenet_v2_b11": ("mobilenet_v2", ("features", 12)),
    "resnet18_layer2": ("resnet18", ("children", "layer2")),
    "resnet18_layer3": ("resnet18", ("children", "layer3")),
}


def trunk(name: str, device="mps", dtype=None, channels_last: bool = False):
    """Pretrained torchvision net cut at the named layer, frozen, eval."""
    import torch
    import torchvision.models as tvm
    from torch import nn

    arch, (how, where) = TRUNKS[name]
    kw = {"weights": "DEFAULT"}
    if arch == "googlenet":
        kw.update(transform_input=False, init_weights=False)  # aux heads are not in the trunk
    net = getattr(tvm, arch)(**kw)
    if how == "features":
        seq = nn.Sequential(*list(net.features.children())[:where])
    else:
        mods = []
        for cname, child in net.named_children():
            mods.append(child)
            if cname == where:
                break
        seq = nn.Sequential(*mods)
    seq.eval()
    for p in seq.parameters():
        p.requires_grad_(False)
    seq = seq.to(device)
    if dtype is not None:
        seq = seq.to(dtype)
    if channels_last:
        seq = seq.to(memory_format=torch.channels_last)
    return seq


class SmallTrunk:
    """A random-weight VGG-ish trunk (conv1_1..conv3_3 shape) for framework
    comparisons where the pretrained weights are irrelevant to timing."""

    CFG = (64, 64, "M", 128, 128, "M", 256, 256, 256)

    @classmethod
    def torch(cls, device="mps", dtype=None):
        from torch import nn

        layers, c = [], 3
        for v in cls.CFG:
            if v == "M":
                layers.append(nn.MaxPool2d(2))
            else:
                layers += [nn.Conv2d(c, v, 3, padding=1), nn.ReLU(inplace=True)]
                c = v
        seq = nn.Sequential(*layers).eval().to(device)
        for p in seq.parameters():
            p.requires_grad_(False)
        if dtype is not None:
            seq = seq.to(dtype)
        return seq


# --------------------------------------------------------------------------
# the dream step


def normalize_in(x):
    """[0,1] RGB NCHW -> ImageNet-normalised (in place is fine on a copy)."""
    import torch

    mean = torch.tensor(IMAGENET_MEAN, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    std = torch.tensor(IMAGENET_STD, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    return (x - mean) / std


def dream_step(D, net, step: float = 0.02, norm: str = "std", clamp=(0.0, 1.0),
               loss_kind: str = "mean", jitter: int = 0, mask=None):
    """One gradient-ascent step on the [0,1]-range buffer D (1,3,H,W).

    `jitter` > 0 rolls the image by a random offset in [-jitter, jitter]
    before the forward pass and rolls the gradient back (the classic Deep
    Dream trick: the net sees a different pixel grid each step, so the
    textures cohere instead of locking to pixel noise). `mask` (1,1,H,W)
    scales the step per pixel — the content-history mask that keeps the
    dream a wake behind the content rather than a fill of the black ground.

    Returns (D_new, stats) where stats has the raw loss, the fractions of
    pixels the clamp caught above 1 / below 0, and the mean |delta|. D is
    treated as data: the returned tensor is detached.
    """
    import torch

    x0 = D.detach()
    if jitter:
        ox, oy = torch.randint(-jitter, jitter + 1, (2,)).tolist()
        x = torch.roll(x0, shifts=(oy, ox), dims=(2, 3)).requires_grad_(True)
    else:
        ox = oy = 0
        x = x0.requires_grad_(True)
    act = net(normalize_in(x))
    if loss_kind == "mean":
        loss = act.mean()
    else:  # l2, the other classic
        loss = act.pow(2).mean()
    (g,) = torch.autograd.grad(loss, x)
    if jitter:
        g = torch.roll(g, shifts=(-oy, -ox), dims=(2, 3))
    if norm == "std":
        g = g / (g.std() + 1e-8)
    elif norm == "absmean":
        g = g / (g.abs().mean() + 1e-8)
    elif norm == "l2":
        g = g / (g.norm() / g.numel() ** 0.5 + 1e-8)
    elif norm == "none":
        pass
    if mask is not None:
        g = g * mask
    out = x0 + step * g
    lo, hi = clamp
    clip_hi = (out > hi).float().mean()   # saturating to white: the runaway signal
    clip_lo = (out < lo).float().mean()   # black background pushed below zero: benign
    out = out.clamp_(lo, hi)
    return out, {"loss": loss.detach(), "clip_hi": clip_hi, "clip_lo": clip_lo,
                 "delta": (out - x0).abs().mean()}


class TemporalDream:
    """D <- blend(D, frame, k); s steps on D; D goes back to the compositor.

    `frame` and D are (1,3,H,W) float in [0,1] on the device. `octaves`
    > 1 runs the steps additionally at 1/1.5 and 1/2.25 scale with the
    lost-detail reinjection of the reference engine (temporal version:
    one octave per call when `alternate` is set, all otherwise).

    `mask_decay` > 0 keeps a content-history mask M: each frame
    M <- max(M * decay, blur(luminance(frame)) * gain), and the gradient
    step is scaled by M, so the dream deepens where content is or recently
    was and never grows on ground the content has not touched. The mask is
    one avg-pool and a max per frame — free next to the net.
    """

    def __init__(self, net, k: float = 0.08, steps: int = 2, step_size: float = 0.02,
                 octaves: int = 1, octave_scale: float = 1.5, alternate: bool = False,
                 norm: str = "std", loss_kind: str = "mean", jitter: int = 0,
                 mask_decay: float = 0.0, mask_gain: float = 4.0, mask_blur: int = 9):
        self.net, self.k, self.steps, self.step_size = net, k, steps, step_size
        self.octaves, self.octave_scale, self.alternate = octaves, octave_scale, alternate
        self.norm, self.loss_kind, self.jitter = norm, loss_kind, jitter
        self.mask_decay, self.mask_gain, self.mask_blur = mask_decay, mask_gain, mask_blur
        self.D = None
        self.M = None
        self.calls = 0
        self.last = {}

    def _run(self, x, steps, mask=None):
        st = {}
        for _ in range(steps):
            x, st = dream_step(x, self.net, self.step_size, self.norm, loss_kind=self.loss_kind,
                               jitter=self.jitter, mask=mask)
        return x, st

    def _update_mask(self, frame):
        import torch
        import torch.nn.functional as F

        lum = frame.float().mean(1, keepdim=True)
        if self.mask_blur > 1:
            lum = F.avg_pool2d(lum, self.mask_blur, stride=1, padding=self.mask_blur // 2)
        lum = (lum * self.mask_gain).clamp_(0, 1)
        self.M = lum if self.M is None else torch.maximum(self.M * self.mask_decay, lum)
        return self.M.to(frame.dtype)

    def __call__(self, frame):
        import torch.nn.functional as F

        if self.D is None:
            self.D = frame.clone()
        D = self.D * (1.0 - self.k) + frame * self.k
        mask = self._update_mask(frame) if self.mask_decay > 0 else None
        H, W = D.shape[-2:]
        if self.octaves == 1:
            D, st = self._run(D, self.steps, mask)
        else:
            scales = [self.octave_scale ** i for i in range(self.octaves - 1, -1, -1)]
            if self.alternate:
                scales = [scales[self.calls % self.octaves]]
            base = D
            st = {}
            for sc in scales:
                h, w = round(H / sc), round(W / sc)
                if (h, w) != (H, W):
                    small = F.interpolate(base, size=(h, w), mode="bilinear", align_corners=False)
                    m_small = None if mask is None else F.interpolate(
                        mask, size=(h, w), mode="bilinear", align_corners=False)
                    small, st = self._run(small, self.steps, m_small)
                    up = F.interpolate(small, size=(H, W), mode="bilinear", align_corners=False)
                    down_up = F.interpolate(
                        F.interpolate(base, size=(h, w), mode="bilinear", align_corners=False),
                        size=(H, W), mode="bilinear", align_corners=False)
                    base = (up + (base - down_up)).clamp_(0, 1)  # reinject lost detail
                else:
                    base, st = self._run(base, self.steps, mask)
            D = base
        self.D = D.detach()
        self.calls += 1
        self.last = st
        return self.D


def frame_to_tensor(rgba_u8: np.ndarray, device="mps", dtype=None):
    """(h,w,4) uint8 bottom-up GL pixels -> (1,3,h,w) float [0,1] top-down."""
    import torch

    t = torch.from_numpy(np.ascontiguousarray(rgba_u8[::-1, :, :3])).to(device)
    t = t.permute(2, 0, 1).unsqueeze(0).float().div_(255.0)
    if dtype is not None:
        t = t.to(dtype)
    return t.contiguous()


def tensor_to_u8(t) -> np.ndarray:
    """(1,3,h,w) float [0,1] -> (h,w,3) uint8 top-down numpy."""
    return (t.detach().float().clamp(0, 1)[0].permute(1, 2, 0) * 255.0).round().to(
        "cpu").numpy().astype(np.uint8)


def composite(scene_rgb: np.ndarray, dream_rgb: np.ndarray, alpha: float = 0.4,
              darken: float = 0.6) -> np.ndarray:
    """The intended effect: dream, darkened, under/over the scene at alpha."""
    s = scene_rgb.astype(np.float32) / 255.0
    d = dream_rgb.astype(np.float32) / 255.0 * darken
    if d.shape[:2] != s.shape[:2]:
        from PIL import Image

        d = np.asarray(Image.fromarray((d * 255).astype(np.uint8)).resize(
            (s.shape[1], s.shape[0]), Image.BILINEAR)).astype(np.float32) / 255.0
    # scene over dream: dream is the wake; scene keeps its full brightness
    out = d * alpha + s  # additive-ish so the wireframe stays white-hot
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
