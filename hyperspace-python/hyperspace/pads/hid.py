"""The hidapi road (plan 42): Sony pads over USB and Bluetooth, and tapes.

**One reader thread per pad** (`HidPad`), as `gamepad.UsbPad` reads a
wired 360 pad: it opens the device by path, reads feature report 0x05
(the motion calibration — and, over Bluetooth, what makes the pad switch
from its 10-byte simple report to the full one with the touchpad, the
sensors and the Edge's buttons), then reads reports as they come
(`sony.decode`), keeping the latest. Outputs go out from the same
thread — hidapi is not promised to be safe across threads on one device
— when the wanted `Effects` differ from the last sent, at most
`OUT_HZ` a second. A read that fails ends the thread; the hub notices
and the pad is found again when it comes back.

**The hub** (`HidHub`, one per device registry, on `gamepad.Claims`)
enumerates every `SCAN_S` on a thread of its own — enumerating on the
frame would cost a frame now and then — starts a reader for each Sony
pad it finds and stops the readers of pads that left. A pad entry asks
`take` each poll: it keeps the reader it holds while that one lives,
else is lent the first free one its ``controller =`` matches
(models.matches). Entries poll in list order, so the first listed has
first pick, as with GLFW joysticks.

**A tape** (`TapePad`) is a recorded session — the raw reports with their
times, one JSON object a line — read back as if it were the pad: the
tests, the cloud and a demo without the controller. `Recorder` writes
one; ``tools/hid_probe.py --record`` and the browser lab both do.

``import hid`` (the hidapi wheel) happens only inside `available`, a
scan and an open: importing this module costs nothing.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from . import models, nintendo, sony

SCAN_S = 1.0               # how often the hub looks for pads coming and going
READ_TIMEOUT_MS = 100      # a read waits at most this, so close() is quick
OUT_HZ = 60.0              # the most output reports a second
STALE_S = 0.5              # no report for this long: `latest` gives nothing (the pad reads lost)
DRAIN_MAX = 64             # reports read in one go before the outputs get a turn
TAPE_SCHEMA = "hyperspace.padtape/1"


def available() -> bool:
    """Can hidapi be imported here? (No: the GLFW road reads a Sony pad
    over USB with its own map, and Bluetooth waits for hidapi.)"""
    try:
        import hid  # noqa: F401
    except Exception:  # noqa: BLE001 — a wheel that will not load is no hidapi
        return False
    return True


def pad_devices(enumerate_=None) -> list[dict]:
    """hidapi's records for every pad the road reads (`models.HID_IDS`: the
    Sony pads, the Joy-Cons) plugged in or paired, one per path — the
    gamepad interface only (usage page 1, usage 5, where the platform
    says)."""
    if enumerate_ is None:
        import hid
        enumerate_ = hid.enumerate
    out, seen = [], set()
    for vid, pids in models.HID_IDS.items():
        for d in enumerate_(vid, 0):
            if d.get("product_id") not in pids:
                continue
            page, usage = d.get("usage_page"), d.get("usage")
            if page and usage and (page, usage) != (1, 5):
                continue
            if vid == models.NINTENDO_VID and _on_usb(d):
                # over USB a Joy-Con (in a grip) or a Pro Controller first wants the
                # 0x80 handshake the codec does not send: left to GLFW until a hand
                # has checked one (plan 46 "To revisit")
                continue
            path = d.get("path")
            if path in seen:
                continue
            seen.add(path)
            out.append(d)
    return out


sony_devices = pad_devices     # plan 42's name


def codec_for(model):
    """The module that speaks a model's reports: `nintendo` for a Joy-Con
    or Pro Controller, `sony` for everything else the road opens."""
    return nintendo if getattr(model, "family", "") == "nintendo" else sony


def _bt_hint(info: dict) -> bool | None:
    """What hidapi says about the link, where it says (0.14's bus_type:
    2 is Bluetooth); None when it does not."""
    bus = info.get("bus_type")
    if bus is None:
        return None
    return int(bus) == 2


def _on_usb(info: dict) -> bool:
    """Is this device on a USB bus? hidapi's bus_type where it says (1);
    before 0.14 the interface number tells: a USB device has one (0 or
    more), a Bluetooth device reports −1 (a Joy-Con over Bluetooth on
    macOS, 2026-11-02). Unknown both ways reads as USB — a Nintendo pad
    is never seized on a guess."""
    hint = _bt_hint(info)
    if hint is not None:
        return not hint
    iface = info.get("interface_number")
    if iface is None:
        return True
    return int(iface) >= 0


class Recorder:
    """A tape being written: a header line, then {"t", "r"} per report."""

    def __init__(self, path: str | Path, model: str, transport: str = ""):
        self.path = Path(path)
        self.f = self.path.open("w", encoding="utf-8")
        self.t0 = time.monotonic()
        self.f.write(json.dumps({"tape": TAPE_SCHEMA, "model": model,
                                 "transport": transport}) + "\n")
        self.lock = threading.Lock()

    def write(self, report: bytes, t: float | None = None) -> None:
        t = time.monotonic() - self.t0 if t is None else t
        with self.lock:
            if not self.f.closed:
                self.f.write(json.dumps({"t": round(t, 4), "r": bytes(report).hex()}) + "\n")

    def note(self, text: str) -> None:
        """A line a reader skips: what the probe asked for at this point."""
        with self.lock:
            if not self.f.closed:
                self.f.write(json.dumps({"t": round(time.monotonic() - self.t0, 4),
                                         "note": text}) + "\n")

    def close(self) -> None:
        with self.lock:
            if not self.f.closed:
                self.f.close()


class HidPad:
    """One pad read over hidapi on a thread of its own — a Sony pad, or a
    Joy-Con (plan 43), each through its codec (`codec_for`). `latest()`
    is the newest `sony.Frame` (None before the first, or once stale);
    `send(effects)` asks for an output; `close()` stops the thread.
    `opener` makes the device (tests hand in a fake)."""

    road = "hid"

    def __init__(self, info: dict, start: bool = True, opener=None, recorder=None):
        self.info = dict(info)
        self.path = info.get("path")
        self.vid = int(info.get("vendor_id") or 0)
        self.pid = int(info.get("product_id") or 0)
        self.serial = str(info.get("serial_number") or "")
        self.model = models.by_ids(self.vid, self.pid)
        self.name = self.model.name
        self.codec = codec_for(self.model)
        self.nintendo = self.codec is nintendo
        self.kind = nintendo.kind_of(self.model.id) if self.nintendo else ""
        self.bt_hint = _bt_hint(self.info)    # what hidapi said of the link, if it did
        self.transport = ""          # "usb" / "bluetooth", once a report says
        self.calibration = self.codec.Calibration()
        # the sensors' axes, this pad's own (a Joy-Con's per side; a Sony pad's the default)
        self.axis_map = nintendo.axis_map_for(self.kind) if self.nintendo else None
        self.flash: dict = {}        # a Joy-Con's SPI records read at connect (the probe asks)
        self.recentred = False       # …and whether its stick's rest became its centre
        self.note = ""
        self.recorder = recorder
        self.opener = opener
        self._lock = threading.Lock()
        self._raw: bytes | None = None       # the newest report, decoded on `latest`
        self._raw_t = 0.0
        self._frame: sony.Frame | None = None
        self._frame_of: bytes | None = None
        self.update_version = 0
        self.usb_len: int | None = None      # the USB output length macOS took
        self.tags: set[int] = set()          # BT byte 1's low nibbles seen (the probe asks)
        self._want: sony.Effects | None = None
        self._sent_key = None
        self._sent_t = 0.0
        self._sent_leds: int | None = None   # a Joy-Con's player lights as last sent
        self._seq = 0
        self._alive = True
        self._started_full = False
        self.reports = 0
        self._thread = None
        if start:
            self._thread = threading.Thread(target=self._run, name="hyperspace-hidpad",
                                            daemon=True)
            self._thread.start()

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def bluetooth(self) -> bool:
        return self.transport == "bluetooth"

    def latest(self) -> sony.Frame | None:
        """The newest report, decoded here — once a frame, on the caller's
        thread, not once per report (a pad sends 250–1000 a second)."""
        with self._lock:
            raw, t = self._raw, self._raw_t
        if raw is None or time.monotonic() - t > STALE_S:
            return None
        if raw is not self._frame_of:
            f = self._decode(raw)
            if f is not None:          # a refused report (a mic report, a bad CRC, a reply):
                self._frame = f        # the last good one stands, so nothing re-fires
            self._frame_of = raw
        return self._frame

    def _decode(self, raw: bytes):
        return self.codec.decode_frame(raw, self)

    @property
    def rumble_v2(self) -> bool:
        """The Edge always takes rumble v2; a DualSense from update 0x0215
        (Linux's threshold; spec §4.3)."""
        return self.model.id == "edge" or self.update_version >= sony.RUMBLE_V2_VERSION

    def send(self, effects: sony.Effects) -> None:
        with self._lock:
            self._want = effects

    def close(self) -> None:
        self._alive = False

    # ---- the thread ----

    def _open(self):
        if self.opener is not None:
            return self.opener(self.info)
        import hid
        dev = hid.device()
        dev.open_path(self.path)
        return dev

    def _run(self) -> None:
        dev = None
        try:
            dev = self._open()
            hint = _bt_hint(self.info)
            if hint is not None:
                self.transport = "bluetooth" if hint else "usb"
            self._calibrate(dev)
            in_len = self.codec.IN_LEN
            while self._alive:
                data = dev.read(in_len, READ_TIMEOUT_MS)
                n = 0
                while data:            # drain what queued (hidapi keeps 30): the newest wins
                    self._take(bytes(data))
                    n += 1
                    data = dev.read(in_len, 1) if n < DRAIN_MAX else None
                self._write(dev)
            self._neutral(dev)
        except Exception as e:  # noqa: BLE001 — unplugged, refused, a Bluetooth drop
            self.note = f"{type(e).__name__}: {e}"[:120]
        finally:
            self._alive = False
            if dev is not None:
                try:
                    dev.close()
                except Exception:  # noqa: BLE001, S110 — closing a gone device is best-effort
                    pass

    def _calibrate(self, dev) -> None:
        """The codec's connect sequence (`setup`): a Sony pad's feature
        reads (the motion calibration, and over Bluetooth the switch to
        the full report; the firmware's update version), a Joy-Con's
        subcommands (the full report mode, sensors and rumble on, each
        acknowledged), its flash reads and its stick's rest."""
        try:
            self.codec.setup(dev, self)
        except Exception as e:  # noqa: BLE001 — a pad that will not answer still reads
            self.note = f"setup: {type(e).__name__}: {e}"[:120]

    def _take(self, r: bytes) -> None:
        if self.recorder is not None:
            self.recorder.write(r)
        if not r:
            return
        link = self.codec.accepts(r, self)
        if link is None:
            return
        if link == "bluetooth" or not self.transport:   # a BT report settles it; USB only if unsaid
            self.transport = link
        with self._lock:
            self._raw, self._raw_t = r, time.monotonic()
            self.reports += 1

    def _write(self, dev) -> None:
        with self._lock:
            want = self._want
        if want is None or not self.transport:
            return
        now = time.monotonic()
        if now - self._sent_t < 1.0 / OUT_HZ:
            return
        # the codec sends what changed (a Sony pad's take-over first; a
        # Joy-Con's rumble again while it is on), or nothing
        if self.codec.write(dev, self, want, now):
            self._sent_key, self._sent_t = want.key(), now

    def _neutral(self, dev) -> None:
        """On the way out, after outputs were sent: rumble stopped and the
        triggers freed (the light keeps its colour), so nothing goes on
        shaking or pushing back after the app lets go."""
        with self._lock:
            want = self._want
        if self._sent_key is None or want is None:
            return
        try:
            self.codec.calm(dev, self, want)
        except Exception:  # noqa: BLE001, S110 — a pad already gone needs no calming
            pass

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0x0F
        return self._seq

    def _usb_len(self) -> int:
        if self.usb_len is not None:
            return self.usb_len
        return sony.USB_OUT_LENS.get(self.model.id, (sony.USB_OUT_LEN,))[0]

    def _send(self, dev, report: bytes, first: bool = False) -> None:
        """Write one report. Over USB the length macOS takes is learned:
        the descriptor's first, then the others SDL and Linux send
        (`sony.USB_OUT_LENS`; spec §9 1) — a refusal is tried once each."""
        if self.bluetooth or self.usb_len is not None:
            dev.write(report)
            return
        last = None
        for n in sony.USB_OUT_LENS.get(self.model.id, (sony.USB_OUT_LEN,)):
            r = (bytes(report) + bytes(n))[:n]
            try:
                if dev.write(r) > 0:
                    self.usb_len = n
                    return
            except Exception as e:  # noqa: BLE001 — the next length is tried
                last = e
        if last is not None:
            raise last


class TapePad:
    """A recorded session read back as a pad: each `latest()` the report
    the tape holds for the time since it started, looping. Its model and
    transport are the header's."""

    road = "tape"

    def __init__(self, path: str | Path, loop: bool = True, clock=time.monotonic):
        self.path = Path(path)
        self.loop, self.clock = loop, clock
        self.reports: list[tuple[float, bytes]] = []
        head: dict = {}
        with self.path.open(encoding="utf-8") as f:
            for n, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue           # a line cut short (a recording stopped mid-write)
                if not isinstance(d, dict):
                    continue
                if n == 0 and "tape" in d:
                    head = d
                    continue
                if "r" in d:
                    try:
                        self.reports.append((float(d["t"]), bytes.fromhex(d["r"])))
                    except (KeyError, TypeError, ValueError):
                        continue
        if head.get("tape", TAPE_SCHEMA) != TAPE_SCHEMA:
            raise ValueError(f"{self.path.name}: not a pad tape ({head.get('tape')!r})")
        self.model = models.MODELS.get(str(head.get("model", "")), models.MODELS["dualsense"])
        self.name = f"tape: {self.path.name}"
        self.transport = str(head.get("transport") or "usb")
        self.codec = codec_for(self.model)
        self.nintendo = self.codec is nintendo
        self.kind = nintendo.kind_of(self.model.id) if self.nintendo else ""
        self.bt_hint = self.transport == "bluetooth"
        self.calibration = self.codec.Calibration()
        self.axis_map = nintendo.axis_map_for(self.kind) if self.nintendo else None
        self.note = "" if self.reports else "the tape holds no reports"
        self.alive = True
        self.t0 = clock()
        self.sent: list[sony.Effects] = []
        self._frame: sony.Frame | None = None    # the last decoded frame (a reply leaves it)
        self._i = 0

    @property
    def length(self) -> float:
        return self.reports[-1][0] if self.reports else 0.0

    def latest(self) -> sony.Frame | None:
        if not self.reports:
            return None
        t = self.clock() - self.t0
        if self.loop and self.length > 0:
            # the last report holds as long as the one before it did, then round again
            gap = self.length - self.reports[-2][0] if len(self.reports) > 1 else 0.0
            t %= self.length + max(1e-3, gap)
        if t < self.reports[min(self._i, len(self.reports) - 1)][0]:
            self._i = 0
        while self._i + 1 < len(self.reports) and self.reports[self._i + 1][0] <= t:
            self._i += 1
        raw = self.reports[self._i][1]
        f = self.codec.decode_frame(raw, self)
        if f is not None:              # a reply on the tape: the last frame stands, as live
            self._frame = f
        return self._frame

    def send(self, effects: sony.Effects) -> None:
        """A tape has no light to set: what was asked is kept, for a test."""
        self.sent = [*self.sent[-15:], effects]

    def close(self) -> None:
        self.alive = False


class HidHub:
    """Every Sony pad hidapi can see, each with its reader, lent to the
    pad entries (`take`). `scan` runs on the hub's thread every `SCAN_S`;
    a test calls it directly with `start=False`."""

    def __init__(self, start: bool = True, enumerate_=None, opener=None,
                 start_readers: bool = True):
        self.enumerate_ = enumerate_
        self.opener = opener
        self.start_readers = start_readers   # False: a test steps the readers itself
        self.readers: dict = {}          # path → HidPad, in the order found
        self.held: dict = {}             # path → the pad entry (gamepad.Pad) holding it
        self.note = ""
        self._lock = threading.Lock()
        self._alive = True
        self._thread = None
        if start:
            self.start()

    def start(self) -> None:
        """The scanning thread (a first `scan` can run before it, so the
        pads plugged in now are there on the first poll)."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="hyperspace-hidhub",
                                            daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while self._alive:
            time.sleep(SCAN_S)
            if self._alive:
                self.scan()

    def scan(self) -> None:
        try:
            found = sony_devices(self.enumerate_)
            self.note = ""
        except Exception as e:  # noqa: BLE001 — a scan that fails is said, the next one runs
            self.note = f"hid: {type(e).__name__}: {e}"[:120]
            return
        paths = {d.get("path") for d in found}
        with self._lock:
            for path, r in list(self.readers.items()):
                if not r.alive or path not in paths:
                    if not r.alive and r.note:
                        # why it died (a refused open: Input Monitoring, another
                        # app holding the pad) — kept for the SYSTEM line
                        self.note = f"{r.name}: {r.note}"[:120]
                    r.close()
                    del self.readers[path]
                    self.held.pop(path, None)
            for d in found:
                path = d.get("path")
                if path not in self.readers and self._alive:
                    self.readers[path] = HidPad(d, start=self.start_readers,
                                                opener=self.opener)

    def take(self, pad, spec: str | None):
        """The reader `pad` reads this poll: the one it holds while it
        lives, else the first free one `spec` matches; None for none."""
        with self._lock:
            for path, holder in list(self.held.items()):
                r = self.readers.get(path)
                if holder is pad:
                    if r is not None and r.alive:
                        return r
                    del self.held[path]
            for path, r in self.readers.items():
                if path in self.held or not r.alive:
                    continue
                if models.matches(spec, r.model, r.vid, r.pid):
                    self.held[path] = pad
                    return r
        return None

    def release(self, pad) -> None:
        with self._lock:
            for path in [p for p, h in self.held.items() if h is pad]:
                del self.held[path]

    def holds(self, vid: int, pid: int) -> bool:
        """Does the hub read a pad with these ids — so the GLFW road leaves
        the same pad's joystick alone?"""
        with self._lock:
            return any(r.alive and r.vid == vid and r.pid == pid for r in self.readers.values())

    def close(self, join: float = 0.5) -> None:
        """Stop the scan and every reader — each sends its neutral report
        on the way out — and wait up to `join` seconds for the threads, so
        a restart's new image finds the pads free (as `gamepad.UsbPad`)."""
        self._alive = False
        with self._lock:
            readers = list(self.readers.values())
            self.readers.clear()
            self.held.clear()
        for r in readers:
            r.close()
        for r in readers:
            t = getattr(r, "_thread", None)
            if t is not None and t.is_alive() and join:
                t.join(join)
