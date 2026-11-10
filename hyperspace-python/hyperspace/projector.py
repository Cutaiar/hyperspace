"""The projector's battery, read over the network through ADB.

The party projector is an XGIMI Halo+ (Android TV). With its developer
options on and network debugging enabled (the steps are in
docs/SETUP.md, "The projector's battery"), the Mac reaches it with::

    adb connect <HALO_IP>:5555
    adb -s <HALO_IP>:5555 shell dumpsys battery

and `dumpsys battery` prints the state of charge as ``level`` over
``scale``, the charger as ``AC powered`` / ``USB powered``, and the status
as a number (2 charging, 3 discharging, 4 not charging, 5 full).

Two pieces:

- `parse` turns that text into a `Battery`, or None when the text holds no
  level. Pure, so the tests feed it captured output.
- `Watch` asks on a worker thread of its own, every `EVERY_S`, and keeps
  the last `Reading`. `latest()` never blocks and never raises: the frame
  and the panel read it as they read a pad's battery. A projector that is
  off, asleep or unauthorised is a `Reading` with `error` said and the
  last good `battery` kept, so a readout can show "85 %, 2 min ago".

`words` is the one line a readout shows ("projector 85 % · charging").

A leaf: the standard library only, nothing from the package
(`tests/test_projector.py::test_projector_is_a_leaf`). Cold for hot
reload, as `segment` is: its thread outlives a reload.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable

PORT = 5555
EVERY_S = 30.0        # a battery moves a percent in minutes; no need to ask often
TIMEOUT_S = 8.0       # one adb call; a projector gone from the network hangs a connect
STALE_S = 180.0       # a reading older than this is said as old

# `BatteryManager.BATTERY_STATUS_*`
STATUS = {1: "unknown", 2: "charging", 3: "discharging", 4: "not charging", 5: "full"}

Runner = Callable[[list[str], float], tuple[int, str]]


@dataclass(frozen=True)
class Battery:
    """One `dumpsys battery`. `percent` is 0–100; the rest is None when the
    projector didn't say."""

    percent: int
    status: str = "unknown"
    plugged: tuple[str, ...] = ()        # "ac", "usb", "wireless", "dock"
    present: bool = True                 # False: the build reports a battery it hasn't got
    temp_c: float | None = None
    volts: float | None = None

    @property
    def charging(self) -> bool:
        return self.status in ("charging", "full")


@dataclass(frozen=True)
class Reading:
    """What `Watch` last knows. `at` is the `time.monotonic()` of the last
    good battery (None until one); `error` the last ask's failure, cleared
    by the next success."""

    battery: Battery | None = None
    at: float | None = None
    error: str | None = None


def _flag(v: str) -> bool:
    return v.strip().lower() == "true"


def parse(text: str) -> Battery | None:
    """`dumpsys battery`'s output → a `Battery`; None without a level.

    Reads only the indented ``key: value`` lines of the "Current Battery
    Service state" block; anything else (a header, an ADB warning) is
    skipped. A ``scale`` of 0 or missing is taken as 100."""
    kv: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip().lower()
        if k and k not in kv:           # the first of a key: later blocks repeat some
            kv[k] = v.strip()
    try:
        level = int(kv["level"])
    except (KeyError, ValueError):
        return None
    try:
        scale = int(kv.get("scale", "100")) or 100
    except ValueError:
        scale = 100
    pct = max(0, min(100, round(level * 100 / scale)))
    try:
        status = STATUS.get(int(kv.get("status", "1")), "unknown")
    except ValueError:
        status = "unknown"
    plugged = tuple(name for key, name in (("ac powered", "ac"), ("usb powered", "usb"),
                                           ("wireless powered", "wireless"),
                                           ("dock powered", "dock"))
                    if _flag(kv.get(key, "")))

    def num(key: str, div: float) -> float | None:
        try:
            return int(kv[key]) / div
        except (KeyError, ValueError):
            return None

    return Battery(percent=pct, status=status, plugged=plugged,
                   present=_flag(kv.get("present", "true")),
                   temp_c=num("temperature", 10.0),     # tenths of a degree
                   volts=num("voltage", 1000.0))        # millivolts


def words(r: Reading, now: float | None = None) -> str:
    """The one line a readout shows: "projector 85 % · charging",
    "projector 85 % · 4 min ago · unreachable", "projector —"."""
    now = time.monotonic() if now is None else now
    b = r.battery
    if b is None:
        return f"projector — · {r.error}" if r.error else "projector —"
    parts = [f"projector {b.percent} %"]
    if b.charging:
        parts.append(b.status)
    elif b.plugged:
        parts.append("plugged in")
    if not b.present:
        parts.append("no battery reported")
    if r.at is not None and now - r.at >= STALE_S:
        parts.append(f"{int((now - r.at) // 60)} min ago")
    if r.error:
        parts.append(r.error)
    return " · ".join(parts)


def run_adb(argv: list[str], timeout: float) -> tuple[int, str]:
    """One adb call → (exit code, stdout + stderr). Never raises: a missing
    adb or a timeout is a nonzero code with the reason as its text."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "adb not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as e:
        return 1, str(e)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _reason(out: str) -> str:
    low = out.lower()
    if "unauthorized" in low:
        return "unauthorised: accept the debugging prompt on the projector"
    if "adb not found" in low:
        return "adb not found"
    if "timed out" in low or "failed to connect" in low or "cannot connect" in low \
            or "no route" in low or "refused" in low or "offline" in low:
        return "unreachable"
    return out.strip().splitlines()[-1][:80] if out.strip() else "no answer"


def ask(serial: str, adb: str = "adb", runner: Runner = run_adb,
        timeout: float = TIMEOUT_S) -> tuple[Battery | None, str | None]:
    """One connect and one `dumpsys battery` → (battery, error). Blocks up
    to two timeouts; `Watch` calls it off the frame."""
    code, out = runner([adb, "connect", serial], timeout)
    if code != 0 or "connected to" not in out.lower():
        return None, _reason(out)
    code, out = runner([adb, "-s", serial, "shell", "dumpsys", "battery"], timeout)
    if code != 0:
        return None, _reason(out)
    b = parse(out)
    return (b, None) if b is not None else (None, _reason(out) if out.strip() else "no battery in the answer")


class Watch:
    """Asks the projector on a thread of its own every `every` seconds.

    ``Watch("192.168.1.40").start()``; ``latest()`` from anywhere;
    ``close()`` at quit (joins within a timeout's length). `runner` and
    `clock` are for the tests."""

    def __init__(self, host: str, port: int = PORT, every: float = EVERY_S,
                 adb: str | None = None, runner: Runner = run_adb,
                 clock: Callable[[], float] = time.monotonic):
        self.serial = host if ":" in host else f"{host}:{port}"
        self.every = every
        self.adb = adb or shutil.which("adb") or "adb"
        self._runner = runner
        self._clock = clock
        self._lock = threading.Lock()
        self._reading = Reading()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def latest(self) -> Reading:
        with self._lock:
            return self._reading

    def poll(self) -> Reading:
        """One ask, now, on the caller's thread; the reading is kept."""
        b, err = ask(self.serial, self.adb, self._runner)
        with self._lock:
            old = self._reading
            if b is not None:
                self._reading = Reading(battery=b, at=self._clock(), error=None)
            else:
                self._reading = Reading(battery=old.battery, at=old.at, error=err)
            return self._reading

    def start(self) -> "Watch":
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="projector-battery",
                                            daemon=True)
            self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll()
            except Exception as e:           # a worker never dies of one bad answer
                with self._lock:
                    old = self._reading
                    self._reading = Reading(old.battery, old.at, f"error: {e}")
            self._stop.wait(self.every)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=TIMEOUT_S * 2 + 1)
            self._thread = None
