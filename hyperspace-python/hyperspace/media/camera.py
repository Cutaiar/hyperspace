"""Cameras (plan 32 T8): this Mac's webcams and capture cards as
`camera:<name>` sources.

`CameraKind` is a ``kind = "camera"`` device entry. Its scan (on the media
pool) lists AVFoundation's video devices by name (pyobjc's
`AVCaptureDevice`) and checks the camera permission; a source's thread
opens its device with PyAV's ``avfoundation`` input at `FPS` and `SIZE`
and decodes each frame as it comes (between frames the input says it has
none, and the thread waits `live.IDLE_S`).
A camera the user has refused is ``error: camera permission (System
Settings ▸ Privacy & Security ▸ Camera)`` on the kind and on the source;
one never asked about is asked by macOS the first time a source opens."""

from __future__ import annotations

import numpy as np

from . import live

FPS = 30
SIZE = "1280x720"
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

    def open(self) -> None:
        _check_permission(live.need("AVFoundation"))
        av = live.need("av")
        self._c = av.open(self.name, format="avfoundation",
                          options={"framerate": str(FPS), "video_size": SIZE})
        self._packets = self._c.demux(video=0)

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
