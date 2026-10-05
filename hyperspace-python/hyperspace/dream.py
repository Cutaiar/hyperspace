"""The dream worker — temporal Deep Dream on the GPU behind the look-back
slot (plan 07, WP6b; the spike is docs/plans/assets/06-lookback-perf.md).

Off by default; ``[dream] enabled = true`` in config.toml opens it and
app.py hangs it on ``renderer.lookback.source``. Nothing in the core
imports this module — like midi.py and bridge.py it depends on the core,
never the reverse — and without torch it is never touched: the look-back
stays the plain tracer lookback.py draws on its own.

One running buffer ``D`` on the device, the spike's recipe:

    D ← D·(1 − k) + frame·k                  blend the newest echo in
    M ← max(M·mask_decay, blur(lum(frame))·4)  the content-history mask
    s times:  x = roll(D, ±jitter)           the net sees a moved grid,
              g = ∂ mean(layer(x)) / ∂x      so texture coheres instead
              g = roll⁻¹(g) / std(g) · M     of locking to pixel noise
              D = clamp(D + step·g, 0, 1)
    out = D·M                                 premultiplied: black where
                                              content never was

Persistent content accumulates steps and dreams deep; content that moved
fades at ``k``, which *is* the age-proportional wake. Octaves run one
scale a frame in rotation ("2 alt", "3 alt") with the reference engine's
lost-detail reinjection — the same cost as one octave. The stability
rule from the spike, ``step × steps / k`` under a ceiling (STABLE_RATIO),
is a guard here: a larger push is clamped to it and the status line says
so; a buffer that still goes non-finite is reset to the frame and counted.

Threading. ``submit`` never blocks the frame loop: it hands the frame to
the worker thread and returns; a frame that arrives while the worker is
busy replaces the one waiting (latest wins — a queue would only add
lag). The worker sleeps on a condition, runs the step inside torch
kernels (which release the GIL; a Python spin here is what hurts the
renderer, spike C) and publishes into a ring of output buffers;
``latest`` is a lock-free read of the newest one. A result lands a
frame or two after its submit by design.

Copy path. ``buffer(shape)`` hands lookback.py a numpy view over the
MPS tensor's own host-visible MTLBuffer (``torch.mps._host_alias_storage``,
private API present in torch 2.14), so glReadPixels lands the pixels in
the tensor and the result comes back the same way — the spike's 0.9 ms
round trip. Three input slots rotate so the reader never fills a slot
the worker is still converting. Without the alias (another device, an
older torch) a plain staging array and ``.to(device)`` in the worker
take over; the path in use is printed at startup and shown in the
status line. The IOSurface/DLPack zero-copy path the spike prototyped
is documented there as the fallback if the alias API disappears; it is
not built.

Models. torchvision's pretrained VGG16 (every conv, conv1_1 … conv5_3,
through its ReLU) and GoogLeNet (conv1 … conv3 and every inception block,
3a … 5b) — lookback.LAYERS, TRUNKS below. A net's feature stack is read
once and kept (``DreamWorker.stacks``): a layer is a cut of it, so a
change between layers of one net reads no file and builds nothing (a
first read builds the whole net, ~1.5 s for VGG16). Weights are
looked for in ``weights_dir`` (default ``<library home>/weights``), then
in torch's own hub cache, and otherwise downloaded on first use — 528 MB
for VGG16, 50 MB for GoogLeNet, announced on stderr. A net that cannot
be had means no dream and the plain tracer, with the reason in the
status line; never a crash. The trunk loads lazily in the worker on the
first submit, so an app that never turns look-back on never reads it.

    [dream]
    enabled = false         # true opens the worker; off, it is never imported
    device = "auto"         # "auto" (MPS when there, else CPU), "mps", "cpu"
    precision = "fp32"      # or "fp16": 10 % faster on VGG, p99 outliers (spike C)
    weights_dir = ""        # where pretrained weights go; "" = <library home>/weights
"""

from __future__ import annotations

import collections
import statistics
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from . import library
from .lookback import LAYERS, OCTAVES

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# lookback.LAYERS name → (torchvision arch, where to cut). VGG cuts index
# .features and include the ReLU after the named conv, as Deep Dream
# conventionally hooks (cut = that ReLU's index + 1); GoogLeNet cuts after
# the named child (its convs are conv + batch norm + ReLU already).
TRUNKS: dict[str, tuple[str, Any]] = {
    "conv1_1": ("vgg16", 2),
    "conv1_2": ("vgg16", 4),
    "conv2_1": ("vgg16", 7),
    "conv2_2": ("vgg16", 9),
    "conv3_1": ("vgg16", 12),
    "conv3_2": ("vgg16", 14),
    "conv3_3": ("vgg16", 16),
    "conv4_1": ("vgg16", 19),
    "conv4_2": ("vgg16", 21),
    "conv4_3": ("vgg16", 23),
    "conv5_1": ("vgg16", 26),
    "conv5_2": ("vgg16", 28),
    "conv5_3": ("vgg16", 30),
    **{name: ("googlenet", name) for name in (
        "conv1", "conv2", "conv3", "inception3a", "inception3b", "inception4a",
        "inception4b", "inception4c", "inception4d", "inception4e", "inception5a",
        "inception5b")},
}
# GoogLeNet's children through the deepest one a layer names: the pools
# between them ride along in a cut, the aux heads and classifier never do
GOOGLENET_LAST = "inception5b"
WEIGHTS = {"vgg16": "VGG16_Weights", "googlenet": "GoogLeNet_Weights"}

# step × steps / k at most. The spike's unmasked rule is 0.5; with the
# content mask on (always, here) the ground cannot fill and the ceiling is
# saturation, ~0.06 at k 0.08 and 2 steps (spike, UI ranges) — 1.5. The
# recommended default (0.03 × 2 / 0.08 = 0.75) sits inside it.
STABLE_RATIO = 1.5
OCTAVE_SCALE = 1.5
MASK_GAIN = 4.0
MASK_BLUR = 9
SLOTS = 3               # input slots: consuming, pending, being written
OUTPUTS = 3             # output ring: published, handed out, being written
HISTORY = 1.0           # seconds of step times the status p50 covers


def guard_step(step: float, steps: int, k: float) -> tuple[float, bool]:
    """The effective step size under the stability rule, and whether it bit."""
    steps = max(1, int(steps))
    limit = STABLE_RATIO * max(float(k), 1e-6) / steps
    if step > limit:
        return limit, True
    return float(step), False


# ------------------------------------------------------------------ weights

def weights_file(arch: str) -> tuple[str, str, float]:
    """(file name, url, size in MB) of the pretrained weights for `arch`."""
    import torchvision.models as tvm

    w = getattr(tvm, WEIGHTS[arch]).DEFAULT
    return w.url.rsplit("/", 1)[-1], w.url, float(w.meta.get("_file_size", 0.0))


def find_weights(arch: str, weights_dir: Path) -> Path | None:
    """Where the weights already are: our dir, then torch's hub cache."""
    name, _, _ = weights_file(arch)
    for d in (weights_dir, Path(torch.hub.get_dir()) / "checkpoints"):
        if (d / name).exists():
            return d / name
    return None


def load_state(arch: str, weights_dir: Path) -> dict:
    """The pretrained state dict, downloading into `weights_dir` if it is nowhere."""
    have = find_weights(arch, weights_dir)
    if have is None:
        name, _, mb = weights_file(arch)
        print(f"dream: downloading {name} ({mb:.0f} MB) to {weights_dir} …", file=sys.stderr)
        weights_dir.mkdir(parents=True, exist_ok=True)
        model_dir = weights_dir
    else:
        model_dir = have.parent
    import torchvision.models as tvm

    w = getattr(tvm, WEIGHTS[arch]).DEFAULT
    return w.get_state_dict(progress=True, check_hash=True, model_dir=str(model_dir))


def net_stack(arch: str, state: dict | None) -> list[tuple[str, Any]]:
    """The net's feature stack as (name, module) in order: VGG16's
    .features (named by index), GoogLeNet's children through inception5b.
    `state` None leaves the weights random (tests)."""
    import torchvision.models as tvm

    if arch == "vgg16":
        net = tvm.vgg16(weights=None)
        if state is not None:
            net.load_state_dict(state)
        return [(str(k), m) for k, m in enumerate(net.features.children())]
    # the pretrained dict carries the aux heads; build with them, cut before
    net = tvm.googlenet(weights=None, aux_logits=True, init_weights=False,
                        transform_input=False)
    if state is not None:
        net.load_state_dict(state)
    stack = []
    for name, child in net.named_children():
        stack.append((name, child))
        if name == GOOGLENET_LAST:
            break
    return stack


def load_stack(arch: str, weights_dir: Path, device, dtype) -> list[tuple[str, Any]]:
    """`net_stack` with the pretrained weights, frozen, in eval, on the
    device. One read of the weights file serves every layer of the net."""
    stack = net_stack(arch, load_state(arch, weights_dir))
    for _, m in stack:
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        m.to(device=device, dtype=dtype)
    return stack


def cut_stack(arch: str, stack: list[tuple[str, Any]], cut) -> torch.nn.Module:
    """The stack up to and including `cut` (TRUNKS's second half) as one
    module. It shares the stack's own modules: a cut copies nothing."""
    from torch import nn

    n = cut if arch == "vgg16" else [name for name, _ in stack].index(cut) + 1
    return nn.Sequential(*(m for _, m in stack[:n])).eval()


def build_trunk(layer: str, weights_dir: Path, device, dtype,
                stacks: dict[str, list] | None = None) -> torch.nn.Module:
    """The pretrained net cut at `layer`, frozen, in eval, on the device.
    `stacks` (arch → load_stack's list) keeps each net once it is read, so
    a change to another layer of the same net reads no file."""
    arch, cut = TRUNKS[layer]
    stack = None if stacks is None else stacks.get(arch)
    if stack is None:
        stack = load_stack(arch, weights_dir, device, dtype)
        if stacks is not None:
            stacks[arch] = stack
    return cut_stack(arch, stack, cut)


# ------------------------------------------------------------------ the step

def normalize_in(x: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor(IMAGENET_MEAN, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    std = torch.tensor(IMAGENET_STD, device=x.device, dtype=x.dtype).view(1, 3, 1, 1)
    return (x - mean) / std


def dream_step(D: torch.Tensor, net, step: float, jitter: int,
               mask: torch.Tensor | None) -> torch.Tensor:
    """One gradient-ascent step on the [0, 1] buffer (1, 3, h, w): std-
    normalised gradient of the layer's mean activation, jittered, masked."""
    x0 = D.detach()
    if jitter > 0:
        oy, ox = torch.randint(-jitter, jitter + 1, (2,)).tolist()
        x = torch.roll(x0, shifts=(oy, ox), dims=(2, 3)).requires_grad_(True)
    else:
        oy = ox = 0
        x = x0.requires_grad_(True)
    loss = net(normalize_in(x)).mean()
    (g,) = torch.autograd.grad(loss, x)
    if jitter > 0:
        g = torch.roll(g, shifts=(-oy, -ox), dims=(2, 3))
    g = g / (g.std() + 1e-8)
    if mask is not None:
        g = g * mask
    return (x0 + step * g).clamp_(0.0, 1.0)


def dream_steps(D: torch.Tensor, net, steps: int, step: float, jitter: int,
                mask: torch.Tensor | None) -> torch.Tensor:
    for _ in range(max(1, int(steps))):
        D = dream_step(D, net, step, jitter, mask)
    return D


def dream_octave(D: torch.Tensor, net, scale: float, steps: int, step: float, jitter: int,
                 mask: torch.Tensor | None) -> torch.Tensor:
    """The steps at 1/scale size with the lost-detail reinjection: the fine
    scale is not averaged away by the coarse one."""
    if scale <= 1.0:
        return dream_steps(D, net, steps, step, jitter, mask)
    H, W = D.shape[-2:]
    h, w = max(16, round(H / scale)), max(16, round(W / scale))
    small = F.interpolate(D, size=(h, w), mode="bilinear", align_corners=False)
    m_small = None if mask is None else F.interpolate(
        mask, size=(h, w), mode="bilinear", align_corners=False)
    down_up = F.interpolate(small, size=(H, W), mode="bilinear", align_corners=False)
    small = dream_steps(small, net, steps, step, max(0, round(jitter / scale)), m_small)
    up = F.interpolate(small, size=(H, W), mode="bilinear", align_corners=False)
    return (up + (D - down_up)).clamp_(0.0, 1.0)


# ------------------------------------------------------------------ buffers

def alias_view(t: torch.Tensor) -> np.ndarray:
    """A numpy view over the host-visible MTLBuffer of an MPS tensor."""
    st = torch.mps._host_alias_storage(t.untyped_storage())
    cpu = torch.empty(0, dtype=t.dtype, device="cpu").set_(st, t.storage_offset(), t.shape,
                                                         t.stride())
    return cpu.numpy()


def probe_alias(device) -> bool:
    """Whether the host-alias copy path works on this device and torch."""
    if getattr(device, "type", str(device)) != "mps":
        return False
    if not hasattr(torch.mps, "_host_alias_storage"):
        return False
    try:
        t = torch.empty((4, 4, 4), dtype=torch.uint8, device=device)
        v = alias_view(t)
        v[...] = 7
        return bool((t.cpu() == 7).all())
    except Exception:  # noqa: BLE001 — any failure means the staging path
        return False


@dataclass(eq=False)
class Slot:
    """One (h, w, 4) uint8 buffer: the device tensor and the host array
    glReadPixels writes — the same memory on the alias path."""

    dev: torch.Tensor | None
    host: np.ndarray


@dataclass(eq=False)
class Job:
    slot: Slot
    frame: int
    params: dict[str, Any]


class DreamWorker:
    """The look-back slot's dream: a LookbackSource on its own thread.

    `cfg` is the ``[dream]`` section. `step_fn(D, mask, params) → D`
    replaces the net for tests; `alias` forces the copy path (None =
    probe). Reads ``dream.*`` from the registry on every submit, so a
    lane riding ``dream.step`` lands on the next frame.
    """

    def __init__(self, reg, cfg: dict | None = None, *, step_fn: Callable | None = None,
                 alias: bool | None = None, start: bool = True):
        from .config import DEFAULTS

        self.reg = reg
        c = {**DEFAULTS["dream"], **(cfg or {})}
        self.device = self._pick_device(str(c.get("device", "auto")))
        self.dtype = torch.float16 if str(c.get("precision", "fp32")) == "fp16" else torch.float32
        wd = str(c.get("weights_dir") or "")
        self.weights_dir = Path(wd).expanduser() if wd else library.home() / "weights"
        self.step_fn = step_fn
        self.alias = probe_alias(self.device) if alias is None else (
            alias and probe_alias(self.device))
        self.path = "alias" if self.alias else "staging"
        # the buffers
        self.shape: tuple[int, int, int] | None = None
        self._slots: list[Slot] = []
        self._writing = -1                    # the slot buffer() handed out last
        self._outs: list[Slot] = []
        self._published = -1                  # output slot latest() answers with
        self._handed = -1                     # …and the one the reader last took
        self._latest: tuple[int, np.ndarray, int] | None = None   # (output, pixels, frame)
        # the dream
        self.net = None
        self.stacks: dict[str, list] = {}     # arch → its feature stack, read once
        self.layer = ""                       # the loaded trunk's layer name
        self._failed_layer = ""               # a layer that could not be had
        self.D: torch.Tensor | None = None
        self.M: torch.Tensor | None = None
        self.calls = 0
        # the hand-off
        self._cv = threading.Condition()
        self._pending: Job | None = None
        self._busy: Job | None = None
        self._stop = threading.Event()
        # the status line
        self.submitted = -1                   # newest frame index handed to us
        self.answered = -1                    # newest frame index published
        self.drops = 0
        self.nan_resets = 0
        self.errors = 0
        self.clamped = False
        self.error = ""
        self.loading = ""
        self._times: collections.deque = collections.deque(maxlen=240)   # (t_end, ms)
        self._thread = threading.Thread(target=self._run, name="dream", daemon=True)
        print(f"dream: {self.device.type} · {self.path} copy path · "
              f"{'fp16' if self.dtype is torch.float16 else 'fp32'} · weights {self.weights_dir}",
              file=sys.stderr)
        if start:
            self._thread.start()

    @staticmethod
    def _pick_device(name: str) -> torch.device:
        if name == "auto":
            return torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        if name == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("dream: MPS is not available on this machine")
        return torch.device(name)

    # ---- LookbackSource ----

    def buffer(self, shape) -> np.ndarray:
        """The array glReadPixels should fill next: a slot the worker is
        neither converting nor holding as pending."""
        shape = tuple(int(v) for v in shape)
        if shape != self.shape:
            self._resize(shape)
        with self._cv:
            taken = {id(j.slot) for j in (self._pending, self._busy) if j is not None}
        for i, s in enumerate(self._slots):
            if id(s) not in taken:
                self._writing = i
                return s.host
        self._writing = 0                     # unreachable with three slots
        return self._slots[0].host

    def submit(self, frame: np.ndarray, frame_index: int) -> None:
        """Hand the newest echo to the worker; never waits. A frame still
        waiting is dropped for this one."""
        shape = tuple(frame.shape)
        if shape != self.shape:
            self._resize(shape)
        slot = self._slots[self._writing] if 0 <= self._writing < len(self._slots) else None
        if slot is None or frame is not slot.host:
            # not our buffer (a staging array of lookback's): copy it in
            self.buffer(shape)
            slot = self._slots[self._writing]
            np.copyto(slot.host, frame)
        self._writing = -1
        job = Job(slot, int(frame_index), self._params())
        self.submitted = job.frame
        with self._cv:
            if self._pending is not None:
                self.drops += 1
            self._pending = job
            self._cv.notify()

    def latest(self) -> tuple[np.ndarray, int] | None:
        got = self._latest
        if got is None:
            return None
        self._handed = got[0]                 # the worker leaves this one alone now
        return got[1], got[2]

    # ---- params, from the registry each submit ----

    def _params(self) -> dict[str, Any]:
        reg = self.reg

        def val(name, default):
            p = reg.get(f"dream.{name}") if reg is not None else None
            return default if p is None else p.value

        return {
            "steps": int(val("steps", 2)),
            "step": float(val("step", 0.03)),
            "k": float(val("k", 0.05)),
            "jitter": int(val("jitter", 8)),
            "mask_decay": float(val("mask_decay", 0.99)),
            "octaves": int(val("octaves", 0)),
            "layer": LAYERS[max(0, min(int(val("layer", 1)), len(LAYERS) - 1))],
        }

    # ---- buffers ----

    def _make(self, shape) -> Slot:
        if self.alias:
            t = torch.empty(shape, dtype=torch.uint8, device=self.device)   # no fill kernel
            return Slot(t, alias_view(t))
        return Slot(None, np.empty(shape, dtype=np.uint8))

    def _resize(self, shape: tuple[int, int, int]) -> None:
        """New echo size: fresh slots and outputs; ``D`` is rebuilt by the
        worker when the next frame's size differs from its own."""
        self.shape = shape
        self._slots = [self._make(shape) for _ in range(SLOTS)]
        self._outs = [self._make(shape) for _ in range(OUTPUTS)]
        self._writing = -1
        self._latest = None
        self._published = self._handed = -1

    # ---- the worker ----

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._cv:
                while self._pending is None and not self._stop.is_set():
                    self._cv.wait()
                if self._stop.is_set():
                    return
                job, self._pending = self._pending, None
                self._busy = job
            t0 = time.perf_counter()
            try:
                self._process(job)
            except Exception as e:  # noqa: BLE001 — the worker must outlive a bad step
                self.errors += 1
                self.error = f"{type(e).__name__}: {e}"[:120]
            finally:
                with self._cv:
                    self._busy = None
            self._times.append((time.perf_counter(), (time.perf_counter() - t0) * 1e3))

    def _ensure_net(self, layer: str) -> bool:
        if self.step_fn is not None:
            return True
        if layer == self.layer and self.net is not None:
            return True
        if layer == self._failed_layer:
            return False
        self.loading = layer
        try:
            self.net = build_trunk(layer, self.weights_dir, self.device, self.dtype,
                                   self.stacks)
        except Exception as e:  # noqa: BLE001 — no net means no dream, not a crash
            self.net, self._failed_layer = None, layer
            self.error = f"no {layer}: {type(e).__name__}: {e}"[:120]
            print(f"dream: {self.error}", file=sys.stderr)
            return False
        finally:
            self.loading = ""
        self.layer, self.error = layer, ""
        return True

    def _frame_tensor(self, slot: Slot) -> torch.Tensor:
        """(h, w, 4) uint8 in the slot → (1, 3, h, w) [0, 1] on the device.
        Rows stay bottom-up throughout: the net does not mind, and the
        result goes back in the same layout."""
        t = slot.dev if slot.dev is not None else torch.from_numpy(slot.host).to(self.device)
        return t[:, :, :3].permute(2, 0, 1).unsqueeze(0).to(self.dtype).div(255.0).contiguous()

    def _update_mask(self, frame: torch.Tensor, decay: float) -> torch.Tensor:
        lum = frame.float().mean(1, keepdim=True)
        lum = F.avg_pool2d(lum, MASK_BLUR, stride=1, padding=MASK_BLUR // 2)
        lum = (lum * MASK_GAIN).clamp_(0.0, 1.0)
        self.M = lum if self.M is None else torch.maximum(self.M * decay, lum)
        return self.M.to(frame.dtype)

    def _process(self, job: Job) -> None:
        p = job.params
        if not self._ensure_net(p["layer"]):
            return
        frame = self._frame_tensor(job.slot)
        if self.D is None or self.D.shape != frame.shape:
            self.D, self.M = frame.clone(), None
        k = p["k"]
        D = self.D * (1.0 - k) + frame * k
        mask = self._update_mask(frame, p["mask_decay"])
        step, self.clamped = guard_step(p["step"], p["steps"], k)
        if self.step_fn is not None:
            D = self.step_fn(D, mask, {**p, "step": step})
        else:
            n_oct = max(1, min(int(p["octaves"]), len(OCTAVES) - 1) + 1)
            scale = OCTAVE_SCALE ** ((n_oct - 1) - self.calls % n_oct)
            D = dream_octave(D, self.net, scale, p["steps"], step, p["jitter"], mask)
        D = D.detach()
        bad = ~torch.isfinite(D).all()
        # the output: D premultiplied by the mask, alpha the mask, as uint8
        out = self._pick_output()
        rgba = torch.cat([D * mask, mask], dim=1)[0].permute(1, 2, 0).mul(255.0).round()
        rgba = rgba.clamp_(0.0, 255.0).to(torch.uint8)
        if out.dev is not None:
            out.dev.copy_(rgba)
            torch.mps.synchronize()
            pixels = out.host
        else:
            pixels = rgba.cpu().numpy()
            np.copyto(out.host, pixels)
            pixels = out.host
        if bool(bad.item()):
            self.D, self.M = frame.clone(), None
            self.nan_resets += 1
            return
        self.D = D
        self.calls += 1
        if pixels.shape != self.shape:        # resized under us: this one is stale
            return
        self._published = next(i for i, o in enumerate(self._outs) if o is out)
        self._latest = (self._published, pixels, job.frame)
        self.answered = job.frame

    def _pick_output(self) -> Slot:
        """An output buffer the reader is not looking at: neither the one
        published nor the one it last took."""
        for i, s in enumerate(self._outs):
            if i not in (self._published, self._handed):
                return s
        return self._outs[0]

    # ---- what the panel shows ----

    def stats(self) -> dict[str, Any]:
        now = time.perf_counter()
        recent = [ms for t, ms in list(self._times) if now - t <= HISTORY]
        if not recent:
            recent = [ms for _, ms in list(self._times)[-5:]]
        return {
            "device": self.device.type,
            "path": self.path,
            "precision": "fp16" if self.dtype is torch.float16 else "fp32",
            "layer": self.layer,
            "ms": statistics.median(recent) if recent else 0.0,
            "behind": max(0, self.submitted - self.answered) if self.answered >= 0 else 0,
            "drops": self.drops,
            "nan_resets": self.nan_resets,
            "clamped": self.clamped,
            "loading": self.loading,
            "error": self.error,
            "alive": self._thread.is_alive(),
        }

    def status(self) -> str:
        s = self.stats()
        if s["error"] and not s["layer"]:
            return f"{s['device']} · {s['error']}"
        if s["loading"]:
            return f"{s['device']} · loading {s['loading']} …"
        if not s["layer"] and self.step_fn is None:
            return f"{s['device']} · {s['path']} · idle"
        parts = [s["device"], s["path"], f"{s['layer'] or 'fake'} {s['precision']}",
                 f"{s['ms']:.1f} ms", f"{s['behind']} behind"]
        if s["drops"]:
            parts.append(f"{s['drops']} dropped")
        if s["nan_resets"]:
            parts.append(f"{s['nan_resets']} nan reset(s)")
        if s["clamped"]:
            parts.append("step clamped")
        if s["error"]:
            parts.append(s["error"])
        return " · ".join(parts)

    # ---- tests and tools ----

    def drain(self, timeout: float = 5.0) -> bool:
        """Wait until nothing is pending or running; True if it emptied."""
        end = time.perf_counter() + timeout
        while time.perf_counter() < end:
            with self._cv:
                if self._pending is None and self._busy is None:
                    return True
            time.sleep(0.001)
        return False

    def close(self) -> None:
        self._stop.set()
        with self._cv:
            self._cv.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)
        if self.calls:
            print(f"dream: closed after {self.calls} submit(s) · {self.status()}", file=sys.stderr)
