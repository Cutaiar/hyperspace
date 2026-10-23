"""Scrub proxies: an intra-frame copy of a clip, so a jog wheel or a macro
sweeping `pos` can land on any frame without decoding from the last
keyframe. MJPEG in a .mov, no larger than 1280×720, the same frame rate.
They live in the app's own cache (`<home>/media-cache/proxies/`), never in
the shared folder, and are keyed by name, size and mtime so a replaced
clip makes a new proxy rather than reading a stale one."""

from __future__ import annotations

import os
from pathlib import Path

MAX_SIZE = (1280, 720)


def _key(path: Path) -> str:
    st = Path(path).stat()
    return f"{Path(path).stem}-{st.st_size}-{st.st_mtime_ns}.mov"


def proxy_for(path: Path, cache: Path) -> Path | None:
    """The finished proxy for `path` in `cache`, or None. Never raises."""
    try:
        p = Path(cache) / _key(path)
        return p if p.is_file() else None
    except OSError:
        return None


def make_proxy(path: Path, cache: Path) -> Path:
    """Write the proxy for `path` into `cache` and return its path. It is
    written to a temporary name and renamed, so `proxy_for` never sees a
    half-written file. Runs on the media pool; raises if the clip will not
    decode."""
    import av

    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    final = cache / _key(path)
    tmp = final.with_name(final.stem + ".tmp.mov")
    try:
        with av.open(str(path)) as src:
            vs = src.streams.video[0]
            vs.thread_type = "AUTO"
            rate = vs.average_rate or vs.guessed_rate or 25
            w, h = vs.codec_context.width, vs.codec_context.height
            k = min(MAX_SIZE[0] / w, MAX_SIZE[1] / h, 1.0)
            w, h = max(2, round(w * k) // 2 * 2), max(2, round(h * k) // 2 * 2)
            with av.open(str(tmp), "w", format="mov") as dst:
                out = dst.add_stream("mjpeg", rate=rate)
                out.width, out.height, out.pix_fmt = w, h, "yuvj420p"
                out.options = {"qmin": "2", "qmax": "5"}
                n = 0
                for fr in src.decode(vs):
                    f = fr.reformat(width=w, height=h, format="yuvj420p")
                    f.pts = n
                    f.time_base = out.codec_context.time_base
                    n += 1
                    for pkt in out.encode(f):
                        dst.mux(pkt)
                for pkt in out.encode():
                    dst.mux(pkt)
            if n == 0:
                raise ValueError("no frames")
        os.replace(tmp, final)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return final
