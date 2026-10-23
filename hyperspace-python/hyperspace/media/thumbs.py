"""Thumbnails for the media browser: a small PNG per file, made on the pool.
Stills go through Pillow, videos through PyAV's first frame. Imports of both
are inside the functions, so nothing heavy loads with the app."""

from __future__ import annotations

import os
from pathlib import Path

from .still import STILL_EXT


def _first_frame(path: Path):
    """The first decoded frame of a video as a PIL image."""
    import av
    with av.open(str(path)) as c:
        for frame in c.decode(video=0):
            return frame.to_image()
    raise ValueError("no video frames")


def make(path: Path, out: Path, px: int = 160) -> Path:
    """Write a thumbnail of `path` to `out`, fitting inside `px` x `px`,
    aspect kept. Written beside `out` then renamed, so a reader never sees a
    half-written file. Raises on a file it cannot read."""
    from PIL import Image, ImageOps
    path, out = Path(path), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in STILL_EXT:
        if path.suffix.lower() in (".heic", ".heif"):
            import pillow_heif
            pillow_heif.register_heif_opener()
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((px, px))
            im = im.convert("RGBA")
    else:
        im = _first_frame(path)
        im.thumbnail((px, px))
        im = im.convert("RGBA")
    tmp = out.with_name(out.name + ".part")
    im.save(tmp, format="PNG")
    os.replace(tmp, out)
    return out
