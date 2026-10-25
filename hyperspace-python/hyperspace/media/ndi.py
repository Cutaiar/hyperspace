"""NDI in (plan 32 T8): another rig's picture over the network — Resolume
or TouchDesigner on the next laptop — as `ndi:<sender>` sources.

`NdiKind` is a ``kind = "ndi"`` device entry. Its scan (on the media
pool) keeps one cyndilib `Finder` open, whose own thread follows the
network, and reads its source names: ``HOST (stream)`` becomes
``ndi:<stream>``, or ``ndi:HOST (stream)`` for each of two hosts sending
one stream name. A source's thread polls the receiver's frame sync
(`capture_video`, which never blocks) — never `Receiver.receive` with a
timeout, which holds the GIL for the whole wait and starves the frame
thread (the M0 spike, m0-findings §2) — and keeps the frame whenever its
timestamp moves. The receiver asks for RGBX/RGBA, so a frame uploads
with no swizzle; one without alpha is made opaque.

``extra_ips`` (a list of addresses, for a sender on another subnet):
cyndilib's finder cannot be given them, so the kind writes them to an NDI
config file of the app's own, ``<home>/ndi/ndi-config.v1.json``, and
points ``NDI_CONFIG_DIR`` at that folder before cyndilib is first
imported. The NDI SDK documents the file; this spike-era road is not yet
proven against a real second subnet, so the status says so."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from . import live

CONFIG_NAME = "ndi-config.v1.json"
UNVERIFIED = "extra_ips via NDI config (unverified)"


def stream_of(name: str) -> str:
    """``HOST (stream)`` → ``stream``; a name without the brackets is its own."""
    if name.endswith(")") and " (" in name:
        return name[name.index(" (") + 2:-1]
    return name


def ids_for(names) -> dict[str, str]:
    """``ndi:<stream>`` → the full NDI name, for each name; a stream name
    two hosts share gets the full name in its id instead, for each."""
    by_stream: dict[str, list[str]] = {}
    for n in sorted(names):
        by_stream.setdefault(stream_of(n), []).append(n)
    out: dict[str, str] = {}
    for stream, full in by_stream.items():
        if len(full) == 1:
            out[f"ndi:{stream}"] = full[0]
        else:
            out.update({f"ndi:{n}": n for n in full})
    return out


def write_config(folder: Path, ips: list[str]) -> Path:
    """The NDI config file listing `ips` (the SDK's ``networks.ips``,
    comma-separated), in `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / CONFIG_NAME
    p.write_text(json.dumps({"ndi": {"networks": {"ips": ",".join(ips)}}}, indent=2) + "\n")
    return p


class NdiReader:
    """One receiver, used only on its source's thread. `lookup()` is the
    sender's full NDI name from the last scan (None while it is not on the
    network), `finder()` the kind's finder; the receiver follows the name
    when it changes."""

    def __init__(self, lookup, finder):
        self.lookup, self.finder = lookup, finder
        self._rx = self._vfs = None
        self._name: str | None = None
        self._ts = None

    def open(self) -> None:
        cl = live.need("cyndilib")
        self._rx = cl.Receiver(color_format=cl.RecvColorFormat.RGBX_RGBA,
                               bandwidth=cl.RecvBandwidth.highest)
        self._vfs = cl.VideoFrameSync()
        self._rx.frame_sync.set_video_frame(self._vfs)
        self._name, self._ts = None, None

    def read(self) -> np.ndarray | None:
        rx, vfs = self._rx, self._vfs
        name = self.lookup()
        if name is not None and name != self._name:
            f = self.finder()
            src = f.get_source(name) if f is not None else None
            if src is not None:
                rx.set_source(src)
                self._name = name
        if self._name is None:
            return None
        rx.frame_sync.capture_video()      # never blocks: the latest frame, or none yet
        if vfs.xres <= 0:
            return None
        ts = vfs.get_timestamp_posix()
        if ts == self._ts:
            return None
        self._ts = ts
        w, h = int(vfs.xres), int(vfs.yres)
        stride = int(vfs.get_line_stride()) or w * 4
        flat = np.asarray(vfs.get_array(), np.uint8)
        px = flat[:h * stride].reshape(h, stride)[:, :w * 4].reshape(h, w, 4).copy()
        if str(vfs.get_fourcc()).rsplit(".", 1)[-1] in ("RGBX", "BGRX"):
            px[..., 3] = 255
        return px

    def close(self) -> None:
        rx, self._rx, self._vfs = self._rx, None, None
        if rx is not None:
            live._quiet(lambda: rx.set_source(None))


class NdiKind(live.LiveKind):
    """NDI senders on the network as sources (see the module docstring).
    Entry: ``extra_ips = ["192.168.1.50", …]`` (default none)."""

    kind = "ndi"
    lib = "cyndilib"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._finder = None

    @property
    def extra_ips(self) -> list[str]:
        ips = self.entry.get("extra_ips") or []
        if isinstance(ips, str):
            ips = [ips]
        return [str(i).strip() for i in ips if str(i).strip()]

    @property
    def status(self) -> str:
        s = super().status
        return f"{s}; {UNVERIFIED}" if self.extra_ips and not s.startswith("error") else s

    def _configure(self) -> None:
        """The app's NDI config, before cyndilib is first imported (the
        runtime reads it once, as it loads)."""
        ips, home = self.extra_ips, self.ctx.home
        if not ips or home is None:
            return
        folder = Path(home) / "ndi"
        write_config(folder, ips)
        os.environ["NDI_CONFIG_DIR"] = str(folder)

    def discover(self) -> dict[str, str]:
        f = self._finder
        if f is None:
            self._configure()
            cl = live.need("cyndilib")
            f = cl.Finder()
            f.set_change_callback(self._soon)
            f.open()                  # its own thread follows the network from here
            if not self._on:          # closed while this scan was importing
                f.close()
                return {}
            self._finder = f
        return ids_for(f.get_source_names())

    def _soon(self, *_) -> None:
        """The finder's thread: the list changed, so the next `poll` scans
        (a sender is a source within a frame of the finder seeing it, not
        up to `SCAN_S` later). One assignment; nothing else on that thread."""
        self._scanned = None

    def source(self, sid: str) -> live.LiveSource:
        reader = NdiReader(lambda: self.handle(sid), lambda: self._finder)
        return live.LiveSource(sid, reader, kind="ndi", clock=self.clock)

    def forget(self) -> None:
        f, self._finder = self._finder, None
        if f is not None:
            f.close()
