"""Out (plan 32 T9): a render output published to Resolume or
TouchDesigner — over Syphon on this Mac, over NDI to another machine.

An output's ``syphon = "<name>"`` / ``ndi = "<name>"`` (config.py) give it
a publisher each. The renderer hands every publisher its output's picture
once the frame is drawn — a texture of the renderer's context, rows GL's
way up (`Renderer._publish`) — and the SYSTEM page shows one line per
publisher: ``<kind> out <name> — <fps> fps, readback <ms> ms``.

- **Syphon** (`SyphonOut`): the texture itself is handed to a Syphon
  server made once with the render context current; Syphon shares it
  with the client app on the GPU — no readback, ~0.3 ms at 1080p
  (m0-findings §1). It runs on the frame thread, which owns the context.
- **NDI** (`NdiOut`): NDI takes host memory, so the picture is read back
  — asynchronously, through two pixel-pack buffers taken in turn: this
  frame's texture is read into one (a GPU command, no wait) and the
  other, filled a frame ago and long finished, is copied out for the
  sender. The send runs on the publisher's own thread,
  ``media-ndi-out-<name>``: cyndilib's `write_video` releases the GIL
  (the spike), so the frame thread never waits on the network. While the
  sender is still busy with the last frame, this one is dropped, never
  queued.

Neither library is imported until a publisher of its kind is made (the
app's boundary, tests/test_app_boundary.py). A publisher never raises
into the frame: what goes wrong — on the frame thread, on the sender's,
or in the renderer's copy for it (`fail`) — is its `status` (``error:
…``, `media.source.error`), said once on stderr and in its `notes` (the
config's, which the SYSTEM page lists). Its fps falls to 0 once nothing
was sent for `RATE_S`, so a stalled publisher never reads as live."""

from __future__ import annotations

import sys
import threading
import time
from fractions import Fraction
from typing import Protocol

import numpy as np

from . import live, pool
from .source import error

NDI_RATE = Fraction(60, 1)    # the frame rate an NDI sender announces (the loop's)
RATE_S = 1.0                  # fps is counted over this long


class Publisher(Protocol):
    """One output published under one name."""

    kind: str          # "syphon" or "ndi"
    name: str
    status: str        # "waiting" (no frame yet), "sending", or "error: …"
    fps: float         # pictures published per second, of the last second or so
    readback_ms: float  # the frame thread's cost of the readback (0 with none)

    def publish(self, tex, t: float) -> None: ...

    def fail(self, why: str) -> None: ...

    def close(self) -> None: ...


class _Rate:
    """Events per second, counted over `RATE_S` windows of `clock`; 0
    once the last event is more than `RATE_S` old."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._fps = 0.0
        self._n = 0
        self._t0: float | None = None
        self._last: float | None = None

    def tick(self) -> None:
        t = self._last = self.clock()
        if self._t0 is None:           # the window opens on this event: intervals from here
            self._t0 = t
            return
        self._n += 1
        dt = t - self._t0
        if dt >= RATE_S:
            self._fps, self._n, self._t0 = self._n / dt, 0, t

    @property
    def fps(self) -> float:
        last = self._last
        if last is None or self.clock() - last > RATE_S:
            return 0.0
        return self._fps


class _Out:
    """What both publishers share: the status, the fps, the failure said once."""

    kind = ""

    def __init__(self, name: str, ctx, clock=time.monotonic):
        self.name, self.ctx = name, ctx
        self.status, self.readback_ms = "waiting", 0.0
        self.notes: list | None = None    # the config's notes (app.py): where a failure is said
        self._rate = _Rate(clock)
        self._said: set[str] = set()

    @property
    def fps(self) -> float:
        return self._rate.fps

    def fail(self, why: str) -> None:
        """Something failed for this publisher: its status says so, and
        each distinct reason is said once (stderr, `notes`)."""
        self.status = error(why)
        if why not in self._said:
            self._said.add(why)
            note = f"publish: {self.kind} out {self.name}: {why}"
            print(note, file=sys.stderr)
            if self.notes is not None:
                self.notes.append(note)

    def _failed(self, e: Exception) -> None:
        self.fail(live._said(e))


class SyphonOut(_Out):
    """A Syphon server of `name` on the render context `ctx`, made here —
    so made with that context current (app.main does, as the renderer is
    made). `publish` hands the texture over; frame thread only."""

    kind = "syphon"

    def __init__(self, name: str, ctx, clock=time.monotonic):
        super().__init__(name, ctx, clock)
        self._srv = None
        try:
            syphon = live.need("syphon")
            self._srv = syphon.SyphonOpenGLServer(name)
        except Exception as e:  # noqa: BLE001 — a publisher must not stop the launch
            self._failed(e)

    def publish(self, tex, t: float) -> None:
        srv = self._srv
        if srv is None or tex is None:
            return
        try:
            srv.publish_frame_texture(int(tex.glo), size=tuple(int(v) for v in tex.size))
        except Exception as e:  # noqa: BLE001 — said, and tried again next frame
            self._failed(e)
            return
        self.status = "sending"
        self._rate.tick()

    def close(self) -> None:
        srv, self._srv = self._srv, None
        if srv is not None:
            live._quiet(srv.stop)


def _ndi_sender(name: str, size: tuple[int, int]):
    """A cyndilib sender of `name` for RGBA frames of `size`, open. Not
    clocked: the render loop is the clock, and a frame the sender is too
    busy for is dropped before it gets here."""
    cl = live.need("cyndilib")
    snd = cl.Sender(name, clock_video=False)
    vf = cl.VideoSendFrame()
    vf.set_resolution(int(size[0]), int(size[1]))
    vf.set_frame_rate(NDI_RATE)
    vf.set_fourcc(cl.FourCC.RGBA)
    snd.set_video_frame(vf)
    snd.open()
    return snd


class NdiOut(_Out):
    """An NDI sender of `name`, fed from textures of `ctx` (see the module
    docstring). `make_sender(name, (w, h))` makes the sender, on the
    publisher's thread — anything with `write_video(flat_uint8)` and
    `close()` (the tests' fake; cyndilib's by default). A size change
    makes the buffers and the sender again. `dropped` counts the frames
    the sender was too busy for."""

    kind = "ndi"

    def __init__(self, name: str, ctx, make_sender=None, clock=time.monotonic):
        super().__init__(name, ctx, clock)
        self.dropped = 0
        self._make = make_sender or _ndi_sender
        self._size: tuple[int, int] | None = None
        self._pbo: list = []
        self._filled = [False, False]
        self._k = 0
        self._stage: np.ndarray | None = None   # the bytes on their way to the sender
        self._shape = (0, 0, 4)                 # …as (h, w, 4)
        self._job = threading.Event()           # set: `_stage` holds a frame to send
        self._busy = False                      # the sender has a frame (set here, cleared there)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._fault = ""
        if make_sender is None:
            try:
                live.need("cyndilib")           # imported here, once: never on the frame thread
            except Exception as e:  # noqa: BLE001 — a publisher must not stop the launch
                self._fault = live._said(e)
                self._failed(e)

    # ---- the frame thread

    def _fit(self, size: tuple[int, int]) -> None:
        if size == self._size:
            return
        self._drop_buffers()
        n = size[0] * size[1] * 4
        self._pbo = [self.ctx.buffer(reserve=n), self.ctx.buffer(reserve=n)]
        self._filled = [False, False]
        self._size = size

    def publish(self, tex, t: float) -> None:
        if self._fault or tex is None:
            return
        try:
            self._read(tex)
        except Exception as e:  # noqa: BLE001 — a lost buffer, a GL error: said, tried again
            self._failed(e)
            self._drop_buffers()          # made again at the next frame

    def _read(self, tex) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name=f"media-ndi-out-{self.name}",
                                            daemon=True)
            self._thread.start()
        t0 = time.perf_counter()
        size = (int(tex.size[0]), int(tex.size[1]))
        self._fit(size)
        k, self._k = self._k, self._k ^ 1
        tex.read_into(self._pbo[k], alignment=1)        # into the buffer: the GPU's to finish
        other, ready = self._pbo[k ^ 1], self._filled[k ^ 1]
        self._filled[k] = True
        if ready:
            if self._busy:
                self.dropped += 1                       # dropped, never queued
            else:
                stage = self._stage
                if stage is None or stage.size != size[0] * size[1] * 4:
                    stage = self._stage = np.empty(size[0] * size[1] * 4, np.uint8)
                other.read_into(stage)                  # filled a frame ago: no wait
                self._shape = (size[1], size[0], 4)
                self._busy = True
                self._job.set()
        ms = (time.perf_counter() - t0) * 1000.0
        self.readback_ms = ms if self.readback_ms == 0.0 else self.readback_ms * 0.9 + ms * 0.1

    # ---- the publisher's thread

    def _run(self) -> None:
        snd, made_for = None, None
        try:
            while not self._stop.is_set():
                if not self._job.wait(0.1):
                    continue
                self._job.clear()
                if self._stop.is_set():
                    break
                h, w, _ = self._shape
                try:
                    if snd is None or made_for != (w, h):
                        if snd is not None:
                            live._quiet(snd.close)
                        snd, made_for = self._make(self.name, (w, h)), (w, h)
                    # GL's rows run bottom first, NDI's top first
                    flat = np.ascontiguousarray(self._stage.reshape(h, w, 4)[::-1]).ravel()
                    snd.write_video(flat)
                    self.status = "sending"
                    self._rate.tick()
                except Exception as e:  # noqa: BLE001 — said; the next frame tries again
                    self._failed(e)
                    if snd is not None:
                        live._quiet(snd.close)
                    snd = made_for = None
                finally:
                    self._busy = False
        finally:
            if snd is not None:
                live._quiet(snd.close)

    def _drop_buffers(self) -> None:
        for b in self._pbo:
            live._quiet(b.release)
        self._pbo, self._size = [], None

    def close(self) -> None:
        """Stop and join the thread (it closes the sender), free the
        buffers. Call with the render context current."""
        self._stop.set()
        self._job.set()
        th, self._thread = self._thread, None
        if th is not None:
            th.join(pool.left(1.5))       # within the app's exit (A-m1)
        self._drop_buffers()


def line(p) -> str:
    """One publisher's SYSTEM line."""
    head = f"{p.kind} out {p.name} — "
    if str(p.status).startswith("error"):
        return head + p.status
    return head + f"{p.fps:.0f} fps, readback {p.readback_ms:.1f} ms"


def lines(slots) -> list[str]:
    """The SYSTEM page's publisher lines, every output's in order."""
    return [line(p) for sl in slots or () for p in getattr(sl, "publishers", None) or ()]


def open_for(slot, ctx, makers=None, notes: list | None = None) -> list:
    """`slot`'s publishers, one per name its config gives (`syphon` then
    `ndi`), made with `ctx` current, saying their failures in `notes`.
    `makers` (the tests') maps a kind to a maker taking (name, ctx)."""
    made = {"syphon": SyphonOut, "ndi": NdiOut, **(makers or {})}
    out = []
    for kind in ("syphon", "ndi"):
        if getattr(slot, kind, ""):
            p = made[kind](getattr(slot, kind), ctx)
            if notes is not None and hasattr(p, "notes"):
                p.notes = notes
                for why in sorted(getattr(p, "_said", ())):   # what its making said already
                    notes.append(f"publish: {p.kind} out {p.name}: {why}")
            out.append(p)
    return out


def close_all(slots) -> None:
    """Every output's publishers closed — the app's two exits."""
    for sl in slots or ():
        for p in getattr(sl, "publishers", None) or ():
            live._quiet(p.close)
