"""Still images as sources: decoded once on the pool, capped, held."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import pool
from .frame import CAP_FILE, MediaFrame, fit_within, to_rgba
from .source import FETCHING, READY, Latest, error

STILL_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}


def _load(path: Path, cap: tuple[int, int]) -> np.ndarray:
    """Decode `path` to capped RGBA. Runs on the pool, never the frame thread."""
    from PIL import Image, ImageOps
    if Path(path).suffix.lower() in (".heic", ".heif"):
        import pillow_heif
        pillow_heif.register_heif_opener()
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        arr = to_rgba(np.asarray(im.convert("RGBA")))
    return fit_within(arr, cap)


class StillSource:
    kind = "still"
    timed = False
    duration = 0.0

    def __init__(self, sid: str, path: Path, cap: tuple[int, int] = CAP_FILE):
        self.sid = sid
        self.path = Path(path)
        self.cap = cap
        self.status = FETCHING
        self._latest = Latest()
        self._future = None

    def _decode(self) -> None:
        try:
            arr = _load(self.path, self.cap)
            self._latest.put(MediaFrame(arr, time.monotonic(), 0))
            self.status = READY
        except Exception as e:  # noqa: BLE001 — a bad file must not kill the app
            self.status = error(f"{type(e).__name__}: {e}")

    def open(self) -> None:
        self.status = FETCHING
        self._future = pool.submit(self._decode)

    def latest(self) -> MediaFrame | None:
        return self._latest.get()

    def want(self, t: float) -> None:
        pass

    def close(self) -> None:
        f = getattr(self, "_future", None)
        if f is not None:
            f.cancel()
