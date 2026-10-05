"""The stall log — a frozen show leaves a stack dump behind (plan 14 WP1).

Everything below writes ``<home>/stall.log``, each entry a ``=== <kind>``
header (the wall time, the loaded preset) and every thread's stack
(``faulthandler.dump_traceback(all_threads=True)``):

**The whole loop stalls** (`Watchdog`). A daemon thread watches the frame
loop; the loop *pets* it once a frame (`pet(now)`, a float write, off the
render path's cost). When no frame has completed for 2 s the thread logs
a ``stall`` with how long the loop has been stuck and when the last frame
completed. Once per stall: the next dump needs a frame to complete and
the loop to stall again.

**The render window stops while the panel goes on** (`RenderWatch`) —
the owner's freeze (2026-09-29): the control window kept working while
the render window showed one frame. Two roads to it, both logged from the
main thread:

- ``render error`` — `renderer.draw` raised. `app.frame` guards the draw
  so the loop lives on, which is exactly why the render window just
  holds its last frame. The entry has the full traceback, once per
  distinct error; the error is live (`RenderWatch.alerts`, the control
  window's red banner) until a draw succeeds.
- ``render stall`` — no render frame has been *presented* for 2 s while
  the loop's frames advance: the draw did not complete, or the window
  was invisible, minimised, occluded or had no framebuffer (vsync on a
  second display, a fullscreen Space). The entry has the window's
  attributes (visible, iconified, focused, monitor, framebuffer size,
  macOS occlusion) as `info()` reads them. With several render outputs
  (plan 21 WP3, `outputs`) it is "no output presented"; one output dark
  for 2 s while another presents, or whose present raised
  (`output_failed`), is a ``warning`` naming it ("output 2 (projector):
  …"), once per message, with its window state or traceback.
- ``stranded target`` — a render frame started with an offscreen
  framebuffer still bound (`app.draw_render` checks before it binds the
  window). That was the freeze itself: `Renderer.draw` draws into
  whatever is bound, and a frame that left the look-back's atlas bound
  made every later frame draw there while the window swapped a stale
  picture, with no error anywhere. `Renderer.draw` and `Lookback.capture`
  now put their target back on every exit; the check stays as the alarm.
- ``non-finite`` — a param dropped a NaN / inf offset or value
  (`Registry.nonfinite`), once per param.
- ``warning`` — a show problem worth a banner, once per message (a
  preset that asks for the dream — `dream.on` with `dream.mix` above 0 —
  with no worker to dream; dismissed, it does not come back).

The banner keeps a render error after the render recovers — its last
message, time and count — and the warnings, until the performer
dismisses them: a freeze that fixed itself is still worth knowing about.

**Raw dumps** (no header; the SYSTEM page counts them): ``kill -USR1
<pid>`` dumps every thread into the same file (``faulthandler.register``),
and a stall that holds the GIL — which the thread cannot see, since it
cannot run — is caught by faulthandler's own C timer, which the thread
re-arms every look (`Watchdog._arm`).

It must never stop the show: every failure — the file will not open, the
platform has no SIGUSR1, a write fails — is kept on `error` and the show
goes on. This module is cold, like app.py (hotreload.MODULES leaves it
out): it has to outlive whatever a reload does.
"""

from __future__ import annotations

import faulthandler
import signal
import threading
import time
import traceback
from collections.abc import Callable
from pathlib import Path

LIMIT = 2.0          # seconds without a completed frame before it counts as a stall
PERIOD = 0.25        # how often the thread looks
POLL = 0.5           # how often RenderWatch reads the render window's attributes
LOG_NAME = "stall.log"
KINDS = ("stall", "render error", "render stall", "stranded target", "non-finite",
         "warning")                                   # the headers' kinds, in status order


def _stamp(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + f".{int(t % 1 * 1000):03d}"


def _quiet_call(fn: Callable | None, default=None):
    try:
        return fn() if fn is not None else default
    except Exception:  # noqa: BLE001 — a log line must not raise
        return default


class Watchdog:
    """The log file and the whole-loop stall thread. One per process.
    `clock` is the loop's own (the `now` it pets with); `wall` stamps the
    log; `preset` names what is loaded. All injectable, so a test drives a
    stall with a fake clock and `check()` and never sleeps."""

    def __init__(self, path: Path | str, *, limit: float = LIMIT, period: float = PERIOD,
                 clock: Callable[[], float] = time.perf_counter,
                 wall: Callable[[], float] = time.time,
                 preset: Callable[[], str | None] | None = None):
        self.path = Path(path)
        self.limit, self.period = float(limit), float(period)
        self.clock, self.wall, self.preset = clock, wall, preset
        self.last = clock()          # the last completed frame, on `clock`
        self.stalls = 0              # stalls this process has logged
        self.error = ""
        self._dumped_for: float | None = None   # the `last` a dump already answered
        self._file = None            # held open: faulthandler writes to its fd
        self._lock = threading.Lock()   # the thread and the main thread both write
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen: tuple[int, int] | None = None    # (size, mtime_ns) the counts are from
        self._counts: dict[str, int] = {}

    # ---- the loop's side ----

    def pet(self, now: float) -> None:
        """A frame completed at `now` (the loop's clock)."""
        self.last = now

    # ---- the file ----

    def open(self) -> bool:
        """Open the log (append) once; False, with the reason on `error`, if it will not."""
        if self._file is not None:
            return True
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.path, "a", encoding="utf-8")  # noqa: SIM115 — held for faulthandler
        except OSError as e:
            self.error = f"stall log: {e}"[:160]
            return False
        return True

    def log(self, kind: str, headline: str, body: str = "") -> bool:
        """One entry: the header (kind, wall time, preset, `headline`), then
        `body`, then every thread's stack. Never raises."""
        if self._file is None:
            return False
        try:
            name = _quiet_call(self.preset)
            with self._lock:
                f = self._file
                f.write(f"\n=== {kind} {_stamp(self.wall())} · preset "
                        f"{name or '(none)'}: {headline} ===\n")
                if body:
                    f.write(body if body.endswith("\n") else body + "\n")
                f.flush()
                faulthandler.dump_traceback(file=f, all_threads=True)
                f.flush()
            return True
        except Exception as e:  # noqa: BLE001 — the log must never stop the show
            self.error = f"stall log: {type(e).__name__}: {e}"[:160]
            return False

    # ---- the thread ----

    def start(self) -> Watchdog:
        """Open the log, register SIGUSR1 and start the thread; a failure
        is kept on `error` and the show goes on."""
        if not self.open():
            return self
        if hasattr(signal, "SIGUSR1"):
            try:
                faulthandler.register(signal.SIGUSR1, file=self._file, all_threads=True)
            except (RuntimeError, ValueError, OSError) as e:   # not the main thread, no signals
                self.error = f"stall log: SIGUSR1: {e}"[:160]
        self.last = self.clock()
        self._thread = threading.Thread(target=self._run, name="stall-watchdog", daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.wait(self.period):
            try:
                self._arm()
                self.check()
            except Exception as e:  # noqa: BLE001 — the watchdog must never stop the show
                self.error = f"stall log: {type(e).__name__}: {e}"[:160]

    def _arm(self) -> None:
        """The backstop for a stall that holds the GIL (a C call that never
        returns): this thread could not run then, so faulthandler's own C
        timer — which needs no GIL — dumps every thread if the thread has
        not re-armed it within the limit and a little. Re-armed every look,
        so while this thread runs the timer never fires; its dump has no
        header (a "raw dump", like SIGUSR1's)."""
        f = self._file
        if f is not None:
            faulthandler.dump_traceback_later(self.limit + 2 * self.period, repeat=False,
                                              file=f)

    def check(self) -> bool:
        """One look: log a stall if the loop has stalled and this stall has
        no entry yet. Returns whether it wrote one."""
        last = self.last
        stuck = self.clock() - last
        if stuck < self.limit or self._dumped_for == last or self._file is None:
            return False
        self._dumped_for = last
        now = self.wall()
        if self.log("stall", f"no frame for {stuck:.1f} s; last completed frame at "
                             f"{_stamp(now - stuck)}"):
            self.stalls += 1
            return True
        return False

    def close(self) -> None:
        """Stop the thread before a quit or restart tears the loop down (a
        slow teardown is not a stall), and let SIGUSR1 go."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        faulthandler.cancel_dump_traceback_later()
        if self._file is not None:
            if hasattr(signal, "SIGUSR1"):
                try:
                    faulthandler.unregister(signal.SIGUSR1)
                except (RuntimeError, ValueError):
                    pass
            with self._lock:
                self._file.close()
                self._file = None

    # ---- what the SYSTEM page shows ----

    def counts(self) -> dict[str, int]:
        """Entries in the log by kind, every process's, plus "raw dump" (a
        stack with no header: kill -USR1, or the GIL-held backstop, `_arm`)
        — re-read only when the file changed."""
        try:
            st = self.path.stat()
        except OSError:
            return {}
        key = (st.st_size, st.st_mtime_ns)
        if key != self._seen:
            try:
                text = self.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return self._counts
            self._seen = key
            lines = text.splitlines()
            out = {k: sum(1 for ln in lines if ln.startswith(f"=== {k} ")) for k in KINDS}
            # a dump from a Python thread marks its caller "Current thread";
            # the C timer's has none and opens with "Timeout (…)!" instead
            dumps = sum(1 for ln in lines if ln.startswith("Current thread"))
            timeouts = sum(1 for ln in lines if ln.startswith("Timeout ("))
            out["raw dump"] = max(dumps - sum(out.values()), 0) + timeouts
            self._counts = {k: v for k, v in out.items() if v}
        return self._counts

    def status(self) -> str:
        """"stall log: <path> (N stalls, …)" once the file has entries, else ""."""
        c = self.counts()
        if not c:
            return ""
        parts = []
        for k, n in c.items():
            plural = "s" if n != 1 else ""
            parts.append(f"{n} {k}{plural}")
        return f"stall log: {self.path} ({', '.join(parts)})"


class RenderWatch:
    """The render window's health, from the main thread: `drew` after a
    render frame completed, `failed` when the draw raised, `tick` once per
    loop frame after both windows drew, `stranded` when a frame starts on
    an offscreen framebuffer. `info` reads the render window's attributes
    (app.py: GLFW, and the NSWindow's occlusion on macOS); its
    "presentable" key says whether a completed frame reaches the screen.
    Everything here is guarded: a watch that raises would be the thing
    that stopped the show."""

    def __init__(self, log: Watchdog | None, *, limit: float = LIMIT, poll: float = POLL,
                 info: Callable[[], dict] | None = None,
                 wall: Callable[[], float] = time.time,
                 outputs: Callable[[], list[tuple[str, dict]]] | None = None):
        self.watchdog = log
        self.limit, self.poll = float(limit), float(poll)
        self.info, self.wall = info, wall
        # plan 21 WP3: with two or more render outputs, (label, window state)
        # for each opened one, the first included. The stall is then "no
        # output presented"; one output dark for `limit` while another
        # presents is a warning that names it. None, or one entry: today's
        self.outputs = outputs
        self._others: list[tuple[str, dict]] = []
        self._dark: dict[str, float] = {}     # label → since when it is not presentable
        self.error = ""               # the live render error: the last draw raised
        self.stalled = ""             # the live render stall
        self.frames = 0               # render frames completed
        # sticky: the last render error, kept after the render recovers
        # until dismissed (the banner's "dismiss")
        self.last_error = ""
        self.last_error_at = 0.0      # wall time
        self.error_count = 0          # draws that raised, this process
        self.warnings: list[str] = []
        self._waved: set[str] = set()   # warnings the performer dismissed: not shown again
        self.dismissed = True         # nothing sticky to show yet
        self.errors_logged = 0
        self.stalls_logged = 0
        self._logged: set[str] = set()   # distinct errors / warnings / ids already written
        self._drew = False               # a frame completed since the last tick
        self._last_ok: float | None = None   # the last tick a completed frame was presentable
        self._polled: float | None = None
        self._state: dict = {}
        self._stall_open = False

    def _once(self, key: str, kind: str, headline: str, body: str = "") -> bool:
        if key in self._logged or self.watchdog is None:
            return False
        self._logged.add(key)
        return self.watchdog.log(kind, headline, body)

    def drew(self, now: float) -> None:
        self.frames += 1
        self._drew = True
        self.error = ""

    def failed(self, exc: BaseException, now: float) -> None:
        """`renderer.draw` raised: the render window holds its last frame."""
        try:
            msg = f"{type(exc).__name__}: {exc}"
            self.error = f"render window stopped — {msg}"[:200]
            self.last_error, self.last_error_at = msg[:200], self.wall()
            self.error_count += 1
            self.dismissed = False
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            key = "".join(traceback.format_exception_only(type(exc), exc))
            last = traceback.extract_tb(exc.__traceback__)[-1:] if exc.__traceback__ else []
            key += "".join(f"{fr.filename}:{fr.lineno}" for fr in last)
            if self._once("error:" + key, "render error",
                          f"renderer.draw raised {msg}"[:300], tb):
                self.errors_logged += 1
        except Exception:  # noqa: BLE001, S110 — never stop the show
            pass

    def stranded(self, glo: int) -> None:
        """A render frame started with framebuffer `glo` bound, not the window."""
        try:
            last = self.last_error or "none"
            self.warn(f"render target stranded: framebuffer {glo} was still bound at the "
                      f"start of a render frame (last render error: {last})",
                      kind="stranded target", key=f"glo:{glo}")
        except Exception:  # noqa: BLE001, S110
            pass

    def nonfinite(self, ids) -> None:
        """Params that dropped a NaN / inf this frame (`Registry.nonfinite`)."""
        try:
            if not isinstance(ids, (list, tuple)):
                return
            for pid in ids:
                self._once(f"nonfinite:{pid}", "non-finite",
                           f"{pid}: a NaN / inf offset or value was dropped; the base holds")
        except Exception:  # noqa: BLE001, S110
            pass

    def warn(self, msg: str, *, kind: str = "warning", key: str | None = None,
             body: str = "") -> None:
        """A show problem: on the banner until dismissed, in the log once."""
        try:
            if msg not in self.warnings and msg not in self._waved:
                self.warnings.append(msg)
                self.dismissed = False
            self._once(f"{kind}:{key or msg}", kind, msg[:300], body)
        except Exception:  # noqa: BLE001, S110
            pass

    def output_failed(self, label: str, exc: BaseException) -> None:
        """A render output after the first raised in its present (plan 21
        WP3): the frame went on; a warning naming it, once per message,
        with the traceback in the log."""
        try:
            msg = f"{label}: its picture failed — {type(exc).__name__}: {exc}"[:240]
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self.warn(msg, body=tb)
        except Exception:  # noqa: BLE001, S110
            pass

    def _outputs(self, now: float, first: bool) -> bool:
        """Whether any render output can present (`first`: the first
        output's own answer); each one dark for `limit` while another
        presents is a warning naming it, with its window state."""
        others = self._others
        if len(others) < 2:
            return first
        live = [bool(st.get("presentable", True)) for _, st in others]
        for (label, st), ok in zip(others, live, strict=True):
            if ok:
                self._dark.pop(label, None)
                continue
            since = self._dark.setdefault(label, now)
            if now - since >= self.limit and any(live):
                self.warn(f"{label}: no picture for {self.limit:.0f} s — {_why(st)}",
                          body=f"{label}: " + ", ".join(f"{k}={v}" for k, v in st.items()))
        return any(live)

    def dismiss(self) -> None:
        """The banner's button: forget the sticky error and the warnings
        (the live ones stay until the render recovers)."""
        self.dismissed = True
        self._waved.update(self.warnings)
        self.warnings = []

    def tick(self, now: float) -> None:
        try:
            if self._polled is None or now - self._polled >= self.poll:
                self._polled = now
                self._state = _quiet_call(self.info, {}) or {}
                self._others = _quiet_call(getattr(self, "outputs", None), []) or []
            # with several outputs: "no output presented" is the stall
            presentable = self._outputs(now, bool(self._state.get("presentable", True)))
            if self._last_ok is None:
                self._last_ok = now
            if self._drew and presentable:
                self._last_ok = now
                if self._stall_open:
                    self._stall_open, self.stalled = False, ""
            self._drew = False
            stuck = now - self._last_ok
            if stuck >= self.limit and not self._stall_open:
                self._stall_open = True
                state = _quiet_call(self.info, {}) or {}   # fresh, for the entry
                self._state = state
                why = "the draw did not complete" if self.error else _why(state)
                self.stalled = f"render window: no new frame for {stuck:.1f} s — {why}"[:200]
                body = "render window: " + ", ".join(f"{k}={v}" for k, v in state.items())
                if self.watchdog is not None and self.watchdog.log(
                        "render stall", f"no render frame presented for {stuck:.1f} s while "
                                        f"the control window runs ({why})", body):
                    self.stalls_logged += 1
        except Exception:  # noqa: BLE001, S110 — never stop the show
            pass

    @property
    def dismissible(self) -> bool:
        return not self.dismissed and (bool(self.warnings) or self._sticky() != "")

    def _sticky(self) -> str:
        if self.dismissed or not self.error_count or self.error:
            return ""
        at = time.strftime("%H:%M:%S", time.localtime(self.last_error_at))
        times = f"{self.error_count} times" if self.error_count != 1 else "once"
        return (f"the render window stopped {times}, last at {at}: {self.last_error} "
                f"(it recovered; the traceback is in the stall log)")[:240]

    def alerts(self) -> list[str]:
        """What the control window's red banner says right now: the live
        render error and stall, then what stays until dismissed."""
        out = [a for a in (self.error, self.stalled, self._sticky()) if a]
        if not self.dismissed:
            out += self.warnings
        return out


def _why(state: dict) -> str:
    """The render window's attributes, as the reason nothing is on screen."""
    if not state:
        return "window state unknown"
    for key, bad, say in (("visible", False, "the window is hidden"),
                          ("iconified", True, "the window is minimised"),
                          ("occluded", True, "the window is covered or on another Space")):
        if state.get(key) is bad:
            return say
    fb = state.get("framebuffer")
    if fb is not None and (not fb[0] or not fb[1]):
        return "the window has no framebuffer"
    return "no completed frame"
