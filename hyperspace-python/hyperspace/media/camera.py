"""Cameras (plan 32 T8): this Mac's webcams and capture cards as
`camera:<name>` sources.

`CameraKind` is a ``kind = "camera"`` device entry. Its scan (on the media
pool) lists AVFoundation's video devices by name (pyobjc's
`AVCaptureDevice`) and checks the camera permission; a source's thread
opens its device with PyAV's ``avfoundation`` input in the first of
`MODES` it takes — FFmpeg refuses a size or rate the device does not list
(EINVAL), and a capture card often offers only its input's 1080p — and
decodes each frame as it comes (between frames the input says it has
none, and the thread waits `live.IDLE_S`).
A camera the user has refused is ``error: camera permission (System
Settings ▸ Privacy & Security ▸ Camera)`` on the kind and on the source;
one never asked about is asked by macOS the first time a source opens."""

from __future__ import annotations

import numpy as np

from . import live

FPS = 30
SIZE = "1280x720"
# what an open tries, in order: 720p, 1080p, 480p at FPS, then the
# device's own default (no options). The one that opened is tried first
# next time (final review A-I2)
MODES: tuple[dict[str, str], ...] = (
    {"framerate": str(FPS), "video_size": SIZE},
    {"framerate": str(FPS), "video_size": "1920x1080"},
    {"framerate": str(FPS), "video_size": "640x480"},
    {},
)


def _mode_name(opts: dict[str, str]) -> str:
    return f"{opts['video_size']}@{opts['framerate']}" if opts else "default"
PERMISSION = "camera permission (System Settings ▸ Privacy & Security ▸ Camera)"
_DENIED = (1, 2)     # AVAuthorizationStatusRestricted, AVAuthorizationStatusDenied


def _check_permission(avf) -> None:
    st = avf.AVCaptureDevice.authorizationStatusForMediaType_(avf.AVMediaTypeVideo)
    if int(st) in _DENIED:
        raise live.Fault(PERMISSION)


class CameraReader:
    """One camera through PyAV, used only on its source's thread."""

    def __init__(self, name: str):
        self.name = name
        self._c = None
        self._packets = None
        self.mode: dict[str, str] | None = None    # the one that opened

    def open(self) -> None:
        """Open the device in the first mode it takes (`MODES`, the last
        one that worked first); `Fault("no supported mode (tried …)")`
        when it takes none."""
        _check_permission(live.need("AVFoundation"))
        av = live.need("av")
        mode = getattr(self, "mode", None)
        order = ([mode] if mode is not None else []) + [m for m in MODES if m != mode]
        for opts in order:
            try:
                self._c = av.open(self.name, format="avfoundation", options=dict(opts))
            except Exception:  # noqa: BLE001, S112 — a mode it lacks: the next
                continue
            self.mode = opts
            self._packets = self._c.demux(video=0)
            return
        raise live.Fault("no supported mode (tried "
                         + ", ".join(_mode_name(m) for m in MODES) + ")")

    def read(self) -> np.ndarray | None:
        """The next frame, or None when the camera has none ready: the
        ``avfoundation`` input says EAGAIN (`BlockingIOError`) between
        frames, which ends PyAV's demux generator, so a fresh one is made."""
        try:
            packet = next(self._packets)
        except BlockingIOError:
            self._packets = self._c.demux(video=0)
            return None
        except StopIteration:
            raise EOFError("the camera stopped sending") from None
        frames = packet.decode()
        return frames[-1].to_ndarray(format="rgba") if frames else None

    def close(self) -> None:
        c, self._c, self._packets = self._c, None, None
        if c is not None:
            c.close()


class CameraKind(live.LiveKind):
    """The video capture devices on this Mac as sources."""

    kind = "camera"
    lib = "AVFoundation"

    def discover(self) -> dict[str, str]:
        avf = live.need(self.lib)
        live.need("av")                  # what a source opens with: said here, not on open
        _check_permission(avf)
        out: dict[str, str] = {}
        for d in avf.AVCaptureDevice.devicesWithMediaType_(avf.AVMediaTypeVideo) or ():
            name = str(d.localizedName())
            out.setdefault(f"camera:{name}", name)
        return out

    def source(self, sid: str) -> live.LiveSource:
        return live.LiveSource(sid, CameraReader(sid.removeprefix("camera:")), kind="camera",
                               clock=self.clock)
