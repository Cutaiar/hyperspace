"""The segment worker — a person matte off the frame thread (plan 39 T4,
W4; decisions 3, 4, 5; the spike is docs/plans/assets/39-vision/).

The `segment` node (graph.SegmentNode) cuts any picture into its
foreground and its background by a matte. In `person` mode the matte is a
model's, and a model is too slow for the frame thread, so it runs here: one
`SegmentWorker` per node, on the dream worker's pattern (dream.py) —

- `submit(frame, index)` never blocks: the frame (H×W×4 uint8 RGBA, rows
  top first — what a model expects to see upright) is copied into one of
  three rotating slots and handed over; a frame that arrives while one is
  still waiting replaces it (latest wins — a queue would only add lag) and
  is counted (`drops`);
- the thread sleeps on a condition while nothing is submitted, runs the
  backend on the newest frame, and publishes the matte by one reference
  swap; `latest()` is a lock-free read of it: `(mask, index, size)`, the
  mask H×W uint8 (rows top first, as the frame's) at the model's size in
  the frame's aspect, `index` the submit it answers;
- an error is caught into `.error` (and said on the node), never past the
  thread; `close()` joins within a second.

Backends are classes with `open()`, `run(frame, quality) -> mask` and
`close()`; `open` runs inside the worker's first job, so the libraries are
imported there and never on `import hyperspace.app` (tests/test_app_boundary.py):

- `VisionBackend`: Apple Vision's `VNGeneratePersonSegmentationRequest`
  through pyobjc, on the Neural Engine — the request built once per
  quality level (`alloc().initWithCompletionHandler_(None)`; `init` and
  `new` are unavailable), a `CGImage` from the frame's bytes, the result's
  `CVPixelBuffer` (`L008`, one byte a pixel) locked, read into numpy and
  unlocked. Vision's mask has a fixed size per level (256×192, 512×384,
  2016×1512) stretched over the whole image, so it is resampled here to
  the frame's aspect at its own width: a consumer fits it by cover, as it
  fits every mask.
- `TorchBackend`: torchvision's LR-ASPP MobileNetV3 (21 classes, 15 is a
  person), fp16 on MPS when there, the spike's ImageNet normalise and
  softmax, the person class's probability as the matte. Several workers
  share one model (`_shared_model`). Weights are looked for in
  `<library home>/weights`, then torch's own hub cache, and otherwise
  downloaded on first use with a line on stderr, as the dream's are.

`pick_backend(cfg)` reads `[segment] backend` — "auto" (Vision on macOS,
else torch), "vision" or "torch" — and returns the backend, or a reason
string when its library is missing (said on the node; never an
exception).

    [segment]
    backend = "auto"        # "auto" (Vision on macOS, else torch), "vision", "torch"
    weights_dir = ""        # the torch backend's weights; "" = <library home>/weights
"""

from __future__ import annotations

import collections
import importlib.util
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

# the model's own levels (`segment.quality`, view.SEGMENT_QUALITY's order)
QUALITIES = ("fast", "balanced", "accurate")
SLOTS = 3               # input slots: consuming, pending, being written
RATE_SPAN = 2.0         # seconds of results the said rate covers
CLOSE_S = 1.0           # close() joins within this
# Vision's quality levels (VNGeneratePersonSegmentationRequestQualityLevel)
VISION_LEVEL = {"fast": 2, "balanced": 1, "accurate": 0}
# the long side of what the readback hands Vision per level (the spike:
# 2.7 ms at 640×360 in, 3.6 at 1280×720 for fast; balanced and accurate
# gain from a finer input)
VISION_INPUT = {"fast": 640, "balanced": 960, "accurate": 1280}
# the short side the torch model runs at per level (the spike's sizes:
# 6.6 ms at 320×240 … 7.6 at 640×480 on MPS)
TORCH_INPUT = {"fast": 240, "balanced": 360, "accurate": 480}
PERSON = 15             # the person class of torchvision's VOC labels
L008 = 0x4C303038       # kCVPixelFormatType_OneComponent8: 'L008'
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def quality_of(q: Any) -> str:
    """`q` as one of `QUALITIES`: a name, or an index into them (a
    `segment.quality` param's value) — "fast" for anything else."""
    if isinstance(q, str) and q in QUALITIES:
        return q
    try:
        i = int(q)
    except (TypeError, ValueError):
        return QUALITIES[0]
    return QUALITIES[i] if 0 <= i < len(QUALITIES) else QUALITIES[0]


def aspect_size(width: int, src: tuple[int, int]) -> tuple[int, int]:
    """(w, h) at `width` in `src`'s (w, h) aspect, at least 1×1."""
    sw, sh = max(int(src[0]), 1), max(int(src[1]), 1)
    w = max(int(width), 1)
    return w, max(1, round(w * sh / sw))


def resample(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """One-channel `mask` resampled bilinearly to `size` (w, h)."""
    h, w = mask.shape[:2]
    if (w, h) == tuple(size):
        return np.ascontiguousarray(mask)
    from PIL import Image

    return np.asarray(Image.fromarray(np.ascontiguousarray(mask)).resize(
        tuple(int(v) for v in size), Image.BILINEAR))


# ------------------------------------------------------------------ backends

class Backend:
    """What a worker runs (subclassed; tests pass any object with these):
    `name` for the said line, `open()` once in the worker's first job,
    `run(frame, quality)` → the matte, `close()` when the worker goes."""

    name = "backend"

    def open(self) -> None:
        pass

    def run(self, frame: np.ndarray, quality: str = "fast") -> np.ndarray:
        raise NotImplementedError

    def close(self) -> None:
        pass

    def input_size(self, quality: str, src: tuple[int, int]) -> tuple[int, int]:
        """The size the readback hands this backend for a picture of `src`
        (w, h): the picture's aspect, never larger than it."""
        return tuple(int(v) for v in src)


class VisionBackend(Backend):
    """Apple Vision's person segmentation (see the module): the request
    per quality level built once, on the Neural Engine, the GPU left free."""

    name = "Vision"

    def __init__(self) -> None:
        self._requests: dict[str, Any] = {}
        self._vision = self._quartz = self._nsdata = None

    def open(self) -> None:
        import Quartz
        import Vision
        from Foundation import NSData

        self._vision, self._quartz, self._nsdata = Vision, Quartz, NSData

    def _request(self, quality: str):
        req = self._requests.get(quality)
        if req is None:
            req = self._vision.VNGeneratePersonSegmentationRequest.alloc() \
                .initWithCompletionHandler_(None)
            req.setQualityLevel_(VISION_LEVEL[quality])
            req.setOutputPixelFormat_(L008)
            self._requests[quality] = req
        return req

    def _cgimage(self, frame: np.ndarray):
        """A `CGImage` over the frame's bytes (one copy, into the NSData: the
        spike's call, safe while the slot is rewritten after)."""
        q = self._quartz
        h, w = frame.shape[:2]
        data = self._nsdata.dataWithBytes_length_(frame.tobytes(), frame.nbytes)
        prov = q.CGDataProviderCreateWithCFData(data)
        cs = q.CGColorSpaceCreateDeviceRGB()
        return q.CGImageCreate(w, h, 8, 32, w * 4, cs, q.kCGImageAlphaNoneSkipLast, prov,
                               None, False, q.kCGRenderingIntentDefault)

    def _pixels(self, pb) -> np.ndarray:
        """The result's pixel buffer read into an H×W uint8 array: locked,
        read row by row past its padding, unlocked."""
        q = self._quartz
        q.CVPixelBufferLockBaseAddress(pb, 1)
        try:
            w = q.CVPixelBufferGetWidth(pb)
            h = q.CVPixelBufferGetHeight(pb)
            bpr = q.CVPixelBufferGetBytesPerRow(pb)
            buf = q.CVPixelBufferGetBaseAddress(pb).as_buffer(bpr * h)
            return np.frombuffer(buf, np.uint8).reshape(h, bpr)[:, :w].copy()
        finally:
            q.CVPixelBufferUnlockBaseAddress(pb, 1)

    def run(self, frame: np.ndarray, quality: str = "fast") -> np.ndarray:
        quality = quality_of(quality)
        req = self._request(quality)
        handler = self._vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
            self._cgimage(frame), {})
        ok, err = handler.performRequests_error_([req], None)
        if not ok:
            raise RuntimeError(f"Vision: {err}")
        res = req.results()
        if not res:
            raise RuntimeError("Vision returned no matte")
        mask = self._pixels(res[0].pixelBuffer())
        # (stretched over the whole image: back to the frame's aspect)
        fh, fw = frame.shape[:2]
        return resample(mask, aspect_size(mask.shape[1], (fw, fh)))

    def input_size(self, quality: str, src: tuple[int, int]) -> tuple[int, int]:
        long = VISION_INPUT[quality_of(quality)]
        w, h = max(int(src[0]), 1), max(int(src[1]), 1)
        k = min(1.0, long / max(w, h))
        return max(1, round(w * k)), max(1, round(h * k))

    def close(self) -> None:
        self._requests = {}


_SHARED: dict[tuple[str, str], Any] = {}
_SHARED_LOCK = threading.Lock()


def _weights_name() -> tuple[str, Any]:
    from torchvision.models.segmentation import LRASPP_MobileNet_V3_Large_Weights

    w = LRASPP_MobileNet_V3_Large_Weights.DEFAULT
    return w.url.rsplit("/", 1)[-1], w


def find_weights(weights_dir: Path) -> Path | None:
    """Where LR-ASPP's weights already are: our dir, then torch's hub cache."""
    import torch

    name, _ = _weights_name()
    for d in (weights_dir, Path(torch.hub.get_dir()) / "checkpoints"):
        if (d / name).exists():
            return d / name
    return None


def _shared_model(device, dtype, weights_dir: Path):
    """The one LR-ASPP model per device and precision, every worker's
    (decision 4's "the torch backend shares one model"): built on the first
    ask, weights found or downloaded (announced on stderr), frozen, in eval."""
    key = (str(device), str(dtype))
    with _SHARED_LOCK:
        got = _SHARED.get(key)
        if got is not None:
            return got
        from torchvision.models.segmentation import lraspp_mobilenet_v3_large

        name, w = _weights_name()
        have = find_weights(weights_dir)
        if have is None:
            mb = float(w.meta.get("_file_size", 0.0))
            print(f"segment: downloading {name} ({mb:.0f} MB) to {weights_dir} …",
                  file=sys.stderr)
            weights_dir.mkdir(parents=True, exist_ok=True)
            model_dir = weights_dir
        else:
            model_dir = have.parent
        state = w.get_state_dict(progress=False, check_hash=True, model_dir=str(model_dir))
        net = lraspp_mobilenet_v3_large(weights=None, weights_backbone=None,
                                        num_classes=len(w.meta["categories"]))
        net.load_state_dict(state)
        net = net.eval().to(device=device, dtype=dtype)
        for p in net.parameters():
            p.requires_grad_(False)
        got = _SHARED[key] = (net, threading.Lock())
        return got


class TorchBackend(Backend):
    """torchvision's LR-ASPP person matte (see the module): one model
    shared by every worker, its forward pass serialised between them."""

    name = "torch"

    def __init__(self, cfg: dict | None = None):
        c = cfg or {}
        wd = str(c.get("weights_dir") or "")
        self._weights_dir = Path(wd).expanduser() if wd else None
        self._device_name = str(c.get("device", "auto"))
        self.net = self._lock = self.device = self.dtype = None

    @property
    def weights_dir(self) -> Path:
        if self._weights_dir is not None:
            return self._weights_dir
        from . import library

        return library.home() / "weights"

    def open(self) -> None:
        import torch

        if self._device_name == "auto":
            self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        else:
            self.device = torch.device(self._device_name)
        self.dtype = torch.float16 if self.device.type == "mps" else torch.float32
        self.net, self._lock = _shared_model(self.device, self.dtype, self.weights_dir)

    def input_size(self, quality: str, src: tuple[int, int]) -> tuple[int, int]:
        short = TORCH_INPUT[quality_of(quality)]
        w, h = max(int(src[0]), 1), max(int(src[1]), 1)
        k = min(1.0, short / min(w, h))
        return max(1, round(w * k)), max(1, round(h * k))

    def run(self, frame: np.ndarray, quality: str = "fast") -> np.ndarray:
        import torch
        import torch.nn.functional as F

        fh, fw = frame.shape[:2]
        w, h = self.input_size(quality, (fw, fh))
        dev, dt = self.device, self.dtype
        x = torch.from_numpy(np.ascontiguousarray(frame[..., :3])).to(dev)
        x = x.permute(2, 0, 1).unsqueeze(0).to(dt) / 255.0
        if (w, h) != (fw, fh):
            x = F.interpolate(x, size=(h, w), mode="bilinear", align_corners=False)
        mean = torch.tensor(IMAGENET_MEAN, device=dev, dtype=dt).view(1, 3, 1, 1)
        std = torch.tensor(IMAGENET_STD, device=dev, dtype=dt).view(1, 3, 1, 1)
        x = (x - mean) / std
        with self._lock, torch.no_grad():
            out = self.net(x)["out"]
        person = out.float().softmax(1)[:, PERSON]
        return (person * 255.0).round().clamp_(0, 255).to(torch.uint8)[0].cpu().numpy()


def _have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


VISION_MISSING = ("Vision is not installed (pyobjc-framework-vision): run `uv sync`, or set "
                  "[segment] backend = \"torch\"")
TORCH_MISSING = "torch is not installed: run `uv sync`"


def pick_backend(cfg: dict | None) -> Backend | str:
    """The backend `[segment] backend` names — auto (Vision on macOS, else
    torch), vision, torch — or, when its library is missing or the name is
    none of those, the reason in words (the node says it). Imports nothing:
    the libraries are found, not loaded (`open` loads them)."""
    c = cfg or {}
    name = str(c.get("backend", "auto") or "auto").lower()
    if name == "auto":
        name = "vision" if sys.platform == "darwin" and _have("Vision") else "torch"
    if name == "vision":
        return VisionBackend() if _have("Vision") and _have("Quartz") else VISION_MISSING
    if name == "torch":
        return (TorchBackend(c) if _have("torch") and _have("torchvision")
                else TORCH_MISSING)
    return f"[segment] backend = {name!r}: one of \"auto\", \"vision\", \"torch\""


# ------------------------------------------------------------------ the worker

class _Job:
    __slots__ = ("index", "quality", "slot")

    def __init__(self, slot: int, index: int, quality: str):
        self.slot, self.index, self.quality = slot, index, quality


class SegmentWorker:
    """One segment node's matte on its own thread (see the module).
    `backend` is a `Backend` (or a reason string: the worker then makes
    nothing and says why); `quality` the level a submit without one runs
    at. `start` False leaves the thread unstarted (tests)."""

    def __init__(self, backend: Backend | str, quality: Any = "fast", *,
                 name: str = "segment", start: bool = True):
        self.name = name
        self.quality = quality_of(quality)
        self.reason = backend if isinstance(backend, str) else ""
        self.backend: Backend | None = None if isinstance(backend, str) else backend
        self.backend_name = getattr(self.backend, "name", "segment")
        self._slots: list[np.ndarray | None] = [None] * SLOTS
        self._cv = threading.Condition()
        self._pending: _Job | None = None
        self._busy: _Job | None = None
        self._stop = threading.Event()
        self._opened = False
        self._latest: tuple[np.ndarray, int, tuple[int, int]] | None = None
        self.submitted = -1
        self.answered = -1
        self.drops = 0
        self.results = 0
        self.errors = 0
        self.error = self.reason
        self.loading = False
        self.last_quality = self.quality
        self._times: collections.deque = collections.deque(maxlen=240)
        self._thread = threading.Thread(target=self._run, name=f"segment-{name}", daemon=True)
        if start and self.backend is not None:
            self._thread.start()

    # ---- the frame thread's side ----

    def wants(self) -> bool:
        """Whether a submit now would be run rather than replace one still
        waiting (the frame thread skips a readback when not)."""
        return self.backend is not None and self._pending is None and not self._stop.is_set()

    def input_size(self, src: tuple[int, int], quality: Any = None) -> tuple[int, int]:
        """What the readback should hand over for a picture of `src`."""
        if self.backend is None:
            return tuple(int(v) for v in src)
        return self.backend.input_size(quality_of(quality or self.quality), src)

    def submit(self, frame: np.ndarray, index: int, quality: Any = None) -> None:
        """Hand frame `frame` (H×W×4 uint8, rows top first; copied) over
        as submit `index`; never waits. One still waiting is dropped for it."""
        if self.backend is None or self._stop.is_set():
            return
        with self._cv:
            taken = {j.slot for j in (self._pending, self._busy) if j is not None}
        slot = next(i for i in range(SLOTS) if i not in taken)
        buf = self._slots[slot]
        if buf is None or buf.shape != frame.shape:
            buf = self._slots[slot] = np.empty(frame.shape, np.uint8)
        np.copyto(buf, frame)
        job = _Job(slot, int(index), quality_of(quality or self.quality))
        self.submitted = job.index
        with self._cv:
            if self._pending is not None:
                self.drops += 1
            self._pending = job
            self._cv.notify()

    def latest(self) -> tuple[np.ndarray, int, tuple[int, int]] | None:
        """The newest matte, `(mask, index, (w, h))`, or None before the
        first: a lock-free read of one reference."""
        return self._latest

    # ---- the worker's side ----

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._cv:
                while self._pending is None and not self._stop.is_set():
                    self._cv.wait()
                if self._stop.is_set():
                    return
                job, self._pending = self._pending, None
                self._busy = job
            try:
                self._process(job)
            except Exception as e:  # noqa: BLE001 — the worker outlives a bad frame
                self.errors += 1
                self.error = f"{type(e).__name__}: {e}"[:160]
            finally:
                with self._cv:
                    self._busy = None

    def _open(self) -> bool:
        if self._opened:
            return not self.reason
        self._opened = True
        self.loading = True
        try:
            self.backend.open()
        except Exception as e:  # noqa: BLE001 — no backend means no matte, never a crash
            self.reason = self.error = f"{self.backend_name} would not open: " \
                                       f"{type(e).__name__}: {e}"[:160]
            print(f"segment: {self.error}", file=sys.stderr)
            return False
        finally:
            self.loading = False
        return True

    def _process(self, job: _Job) -> None:
        if not self._open():
            return
        frame = self._slots[job.slot]
        mask = self.backend.run(frame, job.quality)
        mask = np.ascontiguousarray(np.asarray(mask, dtype=np.uint8))
        if mask.ndim != 2:
            raise ValueError(f"a matte is H×W, not {mask.shape}")
        self._latest = (mask, job.index, (mask.shape[1], mask.shape[0]))
        self.answered = job.index
        self.results += 1
        self.last_quality = job.quality
        self.error = ""
        self._times.append(time.perf_counter())

    # ---- what the node says ----

    def rate(self) -> float:
        """Results a second over the last `RATE_SPAN` seconds (0 with fewer
        than two)."""
        now = time.perf_counter()
        ts = [t for t in list(self._times) if now - t <= RATE_SPAN]
        if len(ts) < 2 or ts[-1] <= ts[0]:
            return 0.0
        return (len(ts) - 1) / (ts[-1] - ts[0])

    def said(self) -> str:
        """The node's line: the error or the reason in words, else the
        matte's size, the backend and level, the lag and the result rate
        (`256×192 · Vision fast · a frame or two late · 29 fps`)."""
        if self.error:
            return f"{self.backend_name}: {self.error}" if self.backend is not None \
                else self.error
        if self.loading:
            return f"loading {self.backend_name} …"
        got = self._latest
        if got is None:
            return f"waiting for {self.backend_name} {self.quality}"
        w, h = got[2]
        return (f"{w}×{h} · {self.backend_name} {self.last_quality} · a frame or two late · "
                f"{self.rate():.0f} fps")

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

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def close(self) -> None:
        """Stop the thread (within `CLOSE_S`), then the backend."""
        self._stop.set()
        with self._cv:
            self._pending = None
            self._cv.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=CLOSE_S)
        if self.backend is not None and self._opened:
            try:
                self.backend.close()
            except Exception:  # noqa: BLE001, S110 — teardown is best-effort
                pass


def make_worker(cfg: dict | None, name: str = "segment") -> SegmentWorker:
    """A worker for segment node `name` on the backend `cfg` picks (the
    renderer's `segmenter`): a missing library is a worker that makes
    nothing and says why."""
    return SegmentWorker(pick_backend(cfg), name=name)
