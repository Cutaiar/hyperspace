"""Live feeds as media sources (plan 32 T8): what NDI, Syphon and the
cameras share.

A *kind* (`LiveKind`) is a device-registry entry — ``kind = "ndi"``,
``"syphon"`` or ``"camera"`` in ``[[devices]]`` — that finds the feeds of
its kind and publishes them as sources, `media_sources()`: source id →
`LiveSource`, which the registry gathers (`DeviceRegistry.media_feeds`)
and the app's media resolver answers `live(sid)` from. It feeds the
Router nothing (`feeds` stays ``()``: that is the Router's tuple of fed
schemes, not this) and makes no rows. Finding feeds can block — an NDI
finder, Syphon's directory spinning a run loop for a second, AVFoundation
listing cameras — so `poll` never does it: every `SCAN_S` it hands the
scan to the media pool, and the frame thread only reads the dict the last
scan published (one reference swap, as `source.Latest`). A kind whose scan
needs a thread of its own (Syphon's run loop belongs to the thread that
spins it) says `own_thread` and scans on ``media-discover-<role>``.

A `LiveSource` is shared: every channel that puts the id on reads the one
object, so `open` and `close` count holders rather than connect and
disconnect. The first `open` starts the source's thread
(``media-live-<sid>``), which opens its *reader* and keeps the newest
frame; the last `close` only notes the time, and the kind's `poll` lets
the thread go once nobody has held the source for `RELEASE_S` — a slot
flicking away and back (the sequencer at 16ths) never reconnects. The
join runs on the pool, never on the frame thread.

A feed that stops (the sender quit, the Wi-Fi dropped) keeps its last
frame for `HOLD_S`, then reads None (black) and says `lost`; the reader
stays connected, so frames that resume are `ready` again with no reopen
(review focus 5). A reader that raises is said as the source's
``error: …`` and opened again after `RETRY_S`.

Each adapter library is imported inside the scan or the reader's `open`
(`need`), so importing `hyperspace.app` imports none of them; a library
that is not installed is the kind's ``error: <lib> not installed``."""

from __future__ import annotations

import importlib
import threading
import time

import numpy as np

from .. import devices
from . import pool
from .frame import CAP_LIVE, MediaFrame, fit_within, to_rgba
from .source import FETCHING, LOST, READY, Latest, error

HOLD_S = 1.0       # a feed that stops shows its last frame this long, then black
SCAN_S = 2.0       # how often a kind looks for feeds again
RELEASE_S = 5.0    # a source nobody holds lets its connection go after this long
RETRY_S = 2.0      # a reader that failed is opened again after this long
IDLE_S = 1 / 120   # a reader with nothing new is asked again after this long
JOIN_S = 1.0       # app exit: how long a kind waits for its sources' threads, together


class Fault(Exception):
    """A failure said as it is on the status line (no exception type in
    front): a library not installed, the camera permission."""


def need(lib: str):
    """Import the adapter library `lib`, or raise `Fault("<lib> not installed")`."""
    try:
        return importlib.import_module(lib)
    except ImportError as e:
        raise Fault(f"{lib} not installed") from e


def _said(e: Exception) -> str:
    return str(e) if isinstance(e, Fault) else f"{type(e).__name__}: {e}"


class LiveSource:
    """One live feed as a `media.source.Source`, untimed. `reader` is
    what connects to it, used only on the source's own thread:
    `open()` connects (may raise), `read()` returns a new frame's pixels
    (H×W×3 or ×4) or None when there is nothing new — it may wait a little
    for one, as a camera does — and `close()` lets go. Frames are kept
    within `cap` (`CAP_LIVE`), aspect kept, and stamped with `clock`, so
    `latest` can tell a feed that stopped."""

    timed = False
    duration = 0.0
    inline = False     # True: `release`'s work runs on the frame thread (Syphon's GL client)

    def __init__(self, sid: str, reader=None, *, kind: str = "live", clock=time.monotonic,
                 cap: tuple[int, int] = CAP_LIVE):
        self.sid = sid
        self.kind = kind
        self.reader = reader
        self.clock = clock
        self.cap = cap
        self._latest = Latest()
        self._n = 0
        self._fault = ""
        self._lock = threading.Lock()
        self._holders = 0
        self._released = 0.0
        self._opened_at: float | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # -- what a channel calls (the frame thread; `close` from the closer) --

    def open(self) -> None:
        """A channel holds the feed: the first holder starts its thread."""
        with self._lock:
            self._holders += 1
            if self._opened_at is None:
                self._opened_at = self.clock()
            if self._thread is None:
                self._start()

    def close(self) -> None:
        """A channel let go. The connection stays until nobody has held
        the feed for `RELEASE_S` (the kind's `poll`)."""
        with self._lock:
            self._holders = max(self._holders - 1, 0)
            if not self._holders:
                self._released = self.clock()

    def want(self, t: float) -> None:
        pass

    def latest(self) -> MediaFrame | None:
        """The newest frame while it is under `HOLD_S` old, else None."""
        f = self._latest.get()
        if f is None or self.clock() - f.t > HOLD_S:
            return None
        return f

    @property
    def status(self) -> str:
        if self._fault:
            return error(self._fault)
        f = self._latest.get()
        now = self.clock()
        if f is not None and now - f.t <= HOLD_S:
            return READY
        at = self._opened_at
        if f is None and at is not None and now - at <= HOLD_S:
            return FETCHING
        return LOST

    @status.setter
    def status(self, value: str) -> None:
        """What the channels say when reading the source raised; the next
        good frame clears it."""
        self._fault = str(value).removeprefix("error: ")

    @property
    def held(self) -> int:
        return self._holders

    @property
    def running(self) -> bool:
        return self._thread is not None

    # -- the kind's housekeeping --------------------------------------------

    def release(self, now: float):
        """The work that lets the connection go, when nobody has held the
        feed for `RELEASE_S`, else None. Decided here, under the lock an
        `open` takes, so a holder arriving now keeps it; the work itself
        (joining the thread) is the caller's to run off the frame thread."""
        with self._lock:
            if self._holders or self._thread is None or now - self._released < RELEASE_S:
                return None
            return self._detach()

    def shut(self, timeout: float = JOIN_S) -> None:
        """Let go now, held or not (the kind closing: app exit)."""
        with self._lock:
            work = self._detach() if self._thread is not None else None
            self._holders = 0
        if work is not None:
            work(timeout)

    def _detach(self):
        t, self._thread = self._thread, None
        self._stop.set()
        self._opened_at = None
        return lambda timeout=JOIN_S: t.join(timeout)

    # -- the source's own thread ----------------------------------------------

    def _start(self) -> None:
        prev = getattr(self, "_last_thread", None)
        self._stop = stop = threading.Event()
        self._thread = self._last_thread = threading.Thread(
            target=self._run, args=(stop, prev), name=f"media-live-{self.sid}", daemon=True)
        self._thread.start()

    def _run(self, stop: threading.Event, prev: threading.Thread | None) -> None:
        if prev is not None:
            prev.join()          # the last connection closes before this one opens
        opened = False
        try:
            while not stop.is_set():
                if not opened:
                    try:
                        self.reader.open()
                        opened = True
                    except Exception as e:  # noqa: BLE001 — said, and tried again
                        self._fault = _said(e)
                        stop.wait(RETRY_S)
                        continue
                try:
                    arr = self.reader.read()
                except Exception as e:  # noqa: BLE001 — said, and opened again
                    self._fault = _said(e)
                    opened = False
                    _quiet(self.reader.close)
                    stop.wait(RETRY_S)
                    continue
                if arr is None:
                    stop.wait(IDLE_S)
                    continue
                self._publish(fit_within(to_rgba(arr), self.cap))
        finally:
            if opened:
                _quiet(self.reader.close)

    def _publish(self, px: np.ndarray) -> None:
        self._n += 1
        self._latest.put(MediaFrame(px, self.clock(), self._n))
        self._fault = ""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.sid} {self.status}>"


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001, S110 — letting go is best-effort
        pass


class LiveKind(devices.Base):
    """A device whose sources are live feeds (see the module docstring).
    A subclass names its `kind`, its library `lib`, and gives `discover()`
    — run off the frame thread, returning source id → handle (whatever
    `source` needs to connect) — and `source(sid)`, a new `LiveSource`
    for an id. `status` is ``connected — <n> feeds``, `lost` (none found)
    or ``error: …``; `last` names the feed found most recently."""

    lib = ""
    own_thread = False    # scan on a thread of its own, not the pool

    def __init__(self, role: str, entry: dict | None = None, ctx: devices.Context | None = None,
                 *, io=None, clock=time.monotonic):
        super().__init__(role, entry, ctx, io=io)
        self.clock = clock
        self._lock = threading.Lock()
        self._handles: dict[str, object] = {}       # the last scan: sid → handle
        self._sources: dict[str, LiveSource] = {}   # every source made and still kept
        self._feeds: dict[str, LiveSource] = {}     # what the last scan found (one swap)
        self._fault = ""
        self._newest = ""
        self._on = False
        self._scanned: float | None = None
        self._job = None
        self._scanner: threading.Thread | None = None
        self._scan_stop = threading.Event()

    # -- what a subclass gives -------------------------------------------------

    def discover(self) -> dict[str, object]:
        raise NotImplementedError

    def source(self, sid: str) -> LiveSource:
        raise NotImplementedError

    def handle(self, sid: str):
        """The last scan's handle for `sid` (None: not found now) — what a
        reader asks to connect, from its own thread."""
        return self._handles.get(sid)

    def forget(self) -> None:
        """Let the library's own objects go (the kind closing); after
        every source has shut."""

    # -- the device --------------------------------------------------------------

    def open(self) -> None:
        """Nothing that can block: the first scan is the next `poll`'s job
        (or the scanner thread's)."""
        self._on, self.io = True, self
        self._fault = ""
        if self.own_thread and self._scanner is None:
            self._scan_stop = stop = threading.Event()
            self._scanner = threading.Thread(target=self._scan_loop, args=(stop,),
                                             name=f"media-discover-{self.role}", daemon=True)
            self._scanner.start()

    @property
    def status(self) -> str:
        if self.error:
            return f"error: {self.error}"
        if getattr(self, "_fault", ""):
            return f"error: {self._fault}"
        n = len(getattr(self, "_feeds", {}))
        if not getattr(self, "_on", False) or not n:
            return "lost"
        return f"connected — {n} feed{'' if n == 1 else 's'}"

    @property
    def last(self) -> str:
        return getattr(self, "_newest", "")

    def media_sources(self) -> dict[str, LiveSource]:
        """Source id → `LiveSource` for every feed the last scan found:
        a dict already made, so asking is a lookup, never a scan."""
        return self._feeds if getattr(self, "_on", False) else {}

    def poll(self, dt: float, now: float) -> None:
        """The frame thread: a scan handed to the pool every `SCAN_S`, and
        each source nobody holds let go after `RELEASE_S`. Nothing here
        waits."""
        if not self._on:
            return
        if not self.own_thread and (self._job is None or self._job.done()) and (
                self._scanned is None or now - self._scanned >= SCAN_S):
            self._scanned = now
            self._job = pool.submit(self._scan)
        t = self.clock()
        with self._lock:
            kept = list(self._sources.items())
        for sid, src in kept:
            work = src.release(t)
            if work is not None:
                if src.inline:
                    _quiet(work)
                else:
                    pool.submit(work)
            if sid not in self._handles and not src.held and not src.running:
                with self._lock:
                    if self._sources.get(sid) is src:
                        del self._sources[sid]

    def close(self) -> None:
        """Every source shut, their threads joined within `JOIN_S`
        together; the scanner stopped; the library's objects let go."""
        self._on, self.io = False, None
        self._scan_stop.set()
        scanner, self._scanner = self._scanner, None
        with self._lock:
            srcs = list(self._sources.values())
            self._sources, self._feeds, self._handles = {}, {}, {}
        end = time.monotonic() + JOIN_S
        for s in srcs:
            _quiet(lambda s=s: s.shut(max(end - time.monotonic(), 0.0)))
        if scanner is not None:
            scanner.join(max(end - time.monotonic(), 0.0))
        _quiet(self.forget)

    # -- off the frame thread ------------------------------------------------------

    def _scan_loop(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self._scan()
            stop.wait(SCAN_S)

    def _scan(self) -> None:
        """One look for feeds; its failure is the kind's status."""
        try:
            found = dict(self.discover())
        except Exception as e:  # noqa: BLE001 — said on the SYSTEM page, tried again
            self._fault = _said(e)
            return
        self._fault = ""
        if not self._on:
            return
        with self._lock:
            for sid in found:
                if sid not in self._sources:
                    self._sources[sid] = self.source(sid)
                if sid not in self._handles:
                    self._newest = sid
            self._handles = found
            self._feeds = {sid: self._sources[sid] for sid in sorted(found)}
