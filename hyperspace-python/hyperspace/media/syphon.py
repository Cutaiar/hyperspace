"""Syphon in (plan 32 T8): another app on this Mac — Resolume, VDMX, a
TouchDesigner window — as `syphon:<app>/<server>` sources, zero-copy.

Syphon hands over a GL texture in our own context, so a frame here is a
texture `MediaFrame` (no pixels) and never touches the CPU (m0-findings
§1). That puts the work on two threads:

- **The scan** (`SyphonKind`, ``media-discover-<role>``): each ask of
  syphon-python's server directory spins the asking thread's run loop
  (`RUN_LOOP_S`), so it lives on a thread of its own — not the pool, whose
  workers it would hold, and never the frame thread. Syphon's shared
  directory hears servers come and go through the *main* thread's run
  loop (tested: a scan thread alone never sees a server), which the app's
  GLFW event poll spins every frame; the scan only reads its list.
- **The client** (`SyphonSource.gl_poll`, the frame thread only, with the
  render context current — the renderer's `MediaTextures` calls it): the
  client is made there on the first call, and `new_frame_image` /
  `textureName()` are read there, as Syphon requires. The client's
  new-frame callback runs on a Syphon thread and only sets a flag. The
  image object is kept while its texture may be sampled. Letting the
  client go (`release`, `inline`) runs on the frame thread too, in the
  kind's `poll`, so the context is never used from two threads.

A server that restarts comes back under a new uuid: the next `gl_poll`
sees the scan's new description and makes a new client. The texture is
the size the server publishes; `CAP_LIVE` caps the CPU feeds only."""

from __future__ import annotations

import time

from . import live
from .frame import MediaFrame

RUN_LOOP_S = 0.05     # how long one directory ask spins the scan thread's run loop


class SyphonSource(live.LiveSource):
    """One Syphon server, read by `gl_poll` on the frame thread. `lookup()`
    is the server's description from the last scan (None while gone)."""

    inline = True

    def __init__(self, sid: str, lookup, *, clock=time.monotonic):
        super().__init__(sid, None, kind="syphon", clock=clock)
        self.lookup = lookup
        self._client = None
        self._uuid = ""
        self._img = None
        self._new = False
        self._retry_at = 0.0

    def _start(self) -> None:
        self._thread = self       # no thread: the client is made by the next gl_poll

    def _detach(self):
        self._thread, self._opened_at = None, None
        return self._drop

    def _drop(self, timeout: float = 0.0) -> None:
        cl, self._client, self._img, self._uuid = self._client, None, None, ""
        self._new = False
        if cl is not None:
            live._quiet(cl.stop)

    def _flag(self, _client) -> None:
        """Syphon's thread: a new frame is there. A flag, nothing else."""
        self._new = True

    def gl_poll(self) -> MediaFrame | None:
        """The frame thread, the render context current: the newest frame
        as a texture, held `HOLD_S` once the server stops sending."""
        if self._thread is None:
            return None
        desc = self.lookup()
        if desc is not None and (self._client is None or desc.uuid != self._uuid):
            now = self.clock()
            if now >= self._retry_at:
                self._drop()
                try:
                    syphon = live.need("syphon")   # imported already: the scan found this id
                    self._client = syphon.SyphonOpenGLClient(desc, new_frame_handler=self._flag)
                    self._uuid = desc.uuid
                    self._new = True               # whatever the server holds now
                except Exception as e:  # noqa: BLE001 — said, and tried again
                    self._fault = live._said(e)
                    self._retry_at = now + live.RETRY_S
        cl = self._client
        if cl is not None and self._new:
            self._new = False
            img = cl.new_frame_image
            if img is not None:
                sz = img.textureSize()
                self._img = img
                self._n += 1
                self._latest.put(MediaFrame(None, self.clock(), self._n,
                                            texture=int(img.textureName()),
                                            tex_size=(int(sz.width), int(sz.height))))
                self._fault = ""
        return self.latest()


class SyphonKind(live.LiveKind):
    """The Syphon servers on this Mac as sources (see the module docstring)."""

    kind = "syphon"
    lib = "syphon"
    own_thread = True

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._dir = None

    def discover(self) -> dict[str, object]:
        syphon = live.need(self.lib)
        d = self._dir
        if d is None:                 # made on the scan thread, whose run loop it needs
            d = self._dir = syphon.SyphonServerDirectory()
            d.run_loop_interval = RUN_LOOP_S
        out: dict[str, object] = {}
        for desc in d.servers:
            out.setdefault(f"syphon:{desc.app_name}/{desc.name}", desc)
        return out

    def source(self, sid: str) -> SyphonSource:
        return SyphonSource(sid, lambda: self.handle(sid), clock=self.clock)

    def forget(self) -> None:
        d, self._dir = self._dir, None
        if d is not None:
            d.close()
