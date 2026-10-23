"""One frame of a media source, and the pixel helpers every source shares.

`MediaFrame` follows `devices.PointCloud`: frozen, with read-only
C-contiguous pixels, so the frame thread can upload it as it is while a
source thread publishes the next. A frame is either CPU pixels (H×W×4
uint8 RGBA) or a GL texture name in the renderer's share group (Syphon) —
exactly one of the two."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

CAP_FILE = (1920, 1080)   # files are decoded no larger than this
CAP_LIVE = (1280, 720)    # live feeds likewise


def to_rgba(arr: np.ndarray) -> np.ndarray:
    """`arr` (H×W×3 or H×W×4, uint8 or float 0–1) as a C-contiguous H×W×4
    uint8 array; alpha is 255 when the input has none."""
    a = np.asarray(arr)
    if a.ndim != 3 or a.shape[2] not in (3, 4):
        raise ValueError(f"pixels must be H×W×3 or H×W×4, not {a.shape}")
    if a.dtype != np.uint8:
        a = (np.clip(a.astype(np.float32), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    if a.shape[2] == 3:
        out = np.empty((a.shape[0], a.shape[1], 4), np.uint8)
        out[..., :3] = a
        out[..., 3] = 255
        return out
    return np.ascontiguousarray(a)


def fit_within(arr: np.ndarray, cap: tuple[int, int]) -> np.ndarray:
    """`arr` scaled down to fit inside `cap` (w, h), aspect kept, Lanczos.
    Never scales up: a smaller image comes back as it is."""
    h, w = arr.shape[:2]
    k = min(cap[0] / w, cap[1] / h)
    if k >= 1.0:
        return arr
    size = (max(1, round(w * k)), max(1, round(h * k)))
    return np.asarray(Image.fromarray(arr).resize(size, Image.LANCZOS))


@dataclass(frozen=True, eq=False)
class MediaFrame:
    """`pixels` is H×W×4 uint8, C-contiguous and read-only. `t` is the
    source's time for the frame (seconds into a clip; the wall clock for a
    live feed); `frame` its id, counting up, so a reader uploads only when
    it moved. A GPU frame carries `texture` (a GL texture name in the
    renderer's share group) and `tex_size` instead of `pixels`."""

    pixels: np.ndarray | None
    t: float
    frame: int
    texture: int | None = None
    tex_size: tuple[int, int] | None = None

    def __post_init__(self):
        if (self.pixels is None) == (self.texture is None):
            raise ValueError("a MediaFrame carries pixels or a texture, exactly one")
        if self.pixels is not None:
            p = self.pixels
            if p.dtype != np.uint8 or p.ndim != 3 or p.shape[2] != 4:
                raise ValueError(f"pixels must be H×W×4 uint8, not {p.dtype} {p.shape}")
            if not p.flags.c_contiguous:
                p = np.ascontiguousarray(p)
            elif p.flags.writeable:
                p = p.view()   # freeze a view; the caller's array stays writable
            p.flags.writeable = False
            object.__setattr__(self, "pixels", p)
        elif self.tex_size is None:
            raise ValueError("a texture frame needs tex_size")

    @property
    def size(self) -> tuple[int, int]:
        """(width, height)."""
        if self.pixels is None:
            return self.tex_size
        return (self.pixels.shape[1], self.pixels.shape[0])
