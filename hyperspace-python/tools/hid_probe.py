"""Watch, record and check a DualSense or DualSense Edge over hidapi (plan 42).

    uv run python tools/hid_probe.py --list            # every Sony pad hidapi sees
    uv run python tools/hid_probe.py                   # live: buttons, sticks, touch, motion
    uv run python tools/hid_probe.py --record edge.jsonl   # …and keep a tape of it
    uv run python tools/hid_probe.py --check           # the guided hardware checks
    uv run python tools/hid_probe.py --check --record edge-check.jsonl --out findings.json

The pad is read exactly as the app reads it (`pads.hid.HidPad`, decoded by
`pads.sony`, the lanes by `pads.gesture`), over USB or Bluetooth — pair it
first: hold Create and PS until the light bar flashes, then System
Settings ▸ Bluetooth. Close anything else holding the pad (the app, the
browser lab's tab): hidapi opens it exclusively.

``--check`` walks through what only a controller can answer
(docs/plans/assets/42-controllers/sony-hid.md §9 and plan 42's list):
the link, the back buttons with and without a profile, whether Fn hides
the face, the sensors' axes and signs, the touchpad's reach, whether the
light bar, rumble, a trigger and the player lights obey, and how still
the sticks rest. Each step says what to do, waits for Enter, and records
what the pad sent; the answers go to ``--out`` (default
``edge-findings.json``) and, with ``--record``, into the tape as notes.
Hand both back: they are what the next build is corrected against.

``--shared`` asks hidapi not to open the pad exclusively (a ctypes call
into the wheel; untested on a Mac — spec §3), so GLFW can see it too.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from hyperspace.pads import gesture, hid, models, sony

NAMES = {i: n for n, i in models.CANON.items()}
HATS = {1: "↑", 2: "→", 4: "↓", 8: "←"}


def shared() -> str:
    """Ask hidapi for non-exclusive opens (spec §3); what happened, in words."""
    try:
        import ctypes

        import hid as _hid
        lib = ctypes.CDLL(_hid.__file__)
        lib.hid_darwin_set_open_exclusive(0)
        return "hidapi: shared opens"
    except Exception as e:  # noqa: BLE001 — the probe says it and carries on
        return f"hidapi: could not ask for shared opens ({type(e).__name__}: {e})"


def pick(controller: str) -> dict:
    found = [d for d in hid.sony_devices()
             if models.matches(controller, models.by_ids(d["vendor_id"], d["product_id"]),
                               d["vendor_id"], d["product_id"])]
    if not found:
        raise SystemExit(f"no Sony pad for controller = {controller!r} — plugged in or paired?")
    return found[0]


def describe(d: dict) -> str:
    m = models.by_ids(d.get("vendor_id"), d.get("product_id"))
    bus = {1: "usb", 2: "bluetooth"}.get(d.get("bus_type"), "?")
    return (f"{m.name}  {d.get('vendor_id', 0):04x}:{d.get('product_id', 0):04x}  {bus}  "
            f"serial {d.get('serial_number') or '-'}  path {d.get('path')!r}")


class Live:
    """A reader and the app's lanes over it, stepped by the probe's clock."""

    def __init__(self, info: dict, recorder=None):
        self.reader = hid.HidPad(info, recorder=recorder)
        self.touchpad, self.motion = gesture.Touchpad(), gesture.Motion()
        self.t = time.monotonic()
        self.count0, self.t0 = 0, self.t
        self.rate = 0.0

    def step(self) -> sony.Frame | None:
        now = time.monotonic()
        dt, self.t = now - self.t, now
        f = self.reader.latest()
        if now - self.t0 >= 1.0:
            self.rate = (self.reader.reports - self.count0) / (now - self.t0)
            self.count0, self.t0 = self.reader.reports, now
        if f is not None and f.full:
            w, h = sony.TOUCH_W - 1, sony.TOUCH_H - 1
            self.touchpad.step([(t.down, t.id, t.x / w, t.y / h) for t in f.touches], dt)
            cal = self.reader.calibration
            self.motion.step(cal.gyro_dps(f.gyro), cal.accel_g(f.accel), dt)
        return f

    def wait(self, seconds: float, each=None) -> list[sony.Frame]:
        frames, end = [], time.monotonic() + seconds
        while time.monotonic() < end:
            f = self.step()
            if f is not None:
                frames.append(f)
                if each is not None:
                    each(f)
            time.sleep(1 / 120)
        return frames


def line(live: Live, f: sony.Frame | None) -> str:
    r = live.reader
    if f is None:
        return f"waiting… {r.note}"
    down = [NAMES[i] for i, v in enumerate(f.buttons) if v and i in NAMES]
    hat = "".join(g for b, g in HATS.items() if f.hat & b)
    axes = " ".join(f"{v:+.2f}" for v in f.axes)
    touch = " ".join(f"{t.id}:{t.x},{t.y}" for t in f.touches if t.down) or "-"
    mo = dict(zip(gesture.MOTION_LANES, live.motion.lanes(), strict=True))
    return (f"{r.transport or '?':9} {live.rate:5.0f} Hz  {f.kind:9}  bat {f.battery * 10:3d}%  "
            f"[{' '.join(down) or '-'}] {hat or '·'}  axes {axes}  touch {touch}  "
            f"roll {mo['roll']:.2f} pitch {mo['pitch']:.2f} shake {mo['shake']:.0f}")


def watch(live: Live) -> None:
    try:
        while True:
            f = live.step()
            sys.stdout.write("\r" + line(live, f)[:200].ljust(200))
            sys.stdout.flush()
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        print()


# ---- the guided checks ----

def ask(text: str) -> str:
    try:
        return input(f"\n{text}\n  [Enter when ready] ").strip()
    except EOFError:
        return ""


def yes(text: str) -> bool:
    try:
        return input(f"{text} [y/n] ").strip().lower().startswith("y")
    except EOFError:
        return False


def held(frames: list[sony.Frame]) -> list[str]:
    """The canonical buttons down through most of `frames`."""
    if not frames:
        return []
    n = len(frames)
    counts = [sum(f.buttons[i] for f in frames) for i in range(models.N_CANON)]
    return [NAMES[i] for i, c in enumerate(counts) if c > n / 2 and i in NAMES]


def mean(rows) -> list[float]:
    rows = list(rows)
    return [sum(c) / len(rows) for c in zip(*rows, strict=True)] if rows else []


def axis_of(delta: list[float]) -> tuple[int, int]:
    """The raw axis that moved most, and its sign."""
    i = max(range(len(delta)), key=lambda k: abs(delta[k]))
    return i, (1 if delta[i] >= 0 else -1)


def check(live: Live, rec, out: Path) -> None:
    r = live.reader
    found: dict = {"model": r.model.id, "path": repr(r.path), "info": {
        k: (v if isinstance(v, (int, str)) else repr(v)) for k, v in r.info.items()}}

    def note(step: str) -> None:
        if rec is not None:
            rec.note(step)

    note("settle")
    frames = live.wait(1.5)
    raw = r._raw or b""
    found["link"] = {"transport": r.transport, "kinds": sorted({f.kind for f in frames}),
                     "report_id": raw[:1].hex(), "report_len": len(raw),
                     "bt_tags": sorted(r.tags), "rate_hz": round(live.rate),
                     "update_version": f"0x{r.update_version:04x}",
                     "calibration": {"nominal": r.calibration.nominal,
                                     "gyro": r.calibration.gyro, "accel": r.calibration.accel}}
    print(f"\nlink: {found['link']['transport']} {found['link']['kinds']} "
          f"{found['link']['rate_hz']} Hz, update {found['link']['update_version']}")

    def hold(step: str, key: str, text: str) -> None:
        ask(text)
        note(step)
        fr = live.wait(1.0)
        found[key] = {"down": held(fr), "raw_buttons": [f.raw_buttons.hex() for f in fr[-1:]]}
        print(f"  → {found[key]['down']}  raw p7–p10 {found[key]['raw_buttons']}")

    hold("still", "nothing_held", "Put the pad down, touch nothing.")
    hold("left back", "left_back", "Hold the LEFT back button (default profile: Fn + △ first).")
    hold("right back", "right_back", "Hold the RIGHT back button.")
    hold("fn left", "fn_left", "Hold the LEFT Fn button (under the left stick).")
    hold("fn cross", "fn_and_cross", "Hold the LEFT Fn button AND ✕ together.")
    hold("profile back", "profile_back",
         "Switch to a profile that maps a back button to a face button (Fn + ○/✕/□), "
         "then hold that back button.")
    hold("default again", "default_profile", "Back to the default profile (Fn + △), hold ✕.")

    # the sensors: the gravity reading flat, tipped right, far edge up; a turn right
    ask("Lay the pad flat on the table, face up.")
    note("flat")
    flat = mean(f.accel for f in live.wait(1.0))
    ask("Tip the RIGHT side down about 45° and hold it.")
    note("right down")
    right = mean(f.accel for f in live.wait(1.0))
    ask("Lay it flat again, then lift the FAR edge (the triggers' side) about 45°.")
    note("far up")
    far = mean(f.accel for f in live.wait(1.0))
    ask("Hold it flat and, after Enter, turn it to the RIGHT (clockwise from above) for 2 s.")
    note("turn right")
    turn = mean(f.gyro for f in live.wait(2.0))
    up = axis_of(flat)
    x = axis_of([a - b for a, b in zip(right, flat, strict=True)])
    z = axis_of([a - b for a, b in zip(far, flat, strict=True)])
    yaw = axis_of(turn)
    # right side down moves the reading toward −x, the far edge up toward −z (gesture.Motion)
    found["sensors"] = {"flat_accel": flat, "right_down_accel": right, "far_up_accel": far,
                        "turn_right_gyro": turn,
                        "proposed_axis_map": {
                            "accel": [[x[0], -x[1]], [up[0], up[1]], [z[0], -z[1]]],
                            "gyro_yaw": [yaw[0], -yaw[1]]},
                        "default_holds": x == (0, -1) and up == (1, 1) and z == (2, -1)}
    print(f"  → accel axes: x raw {x}, up raw {up}, z raw {z}; yaw raw {yaw}; "
          f"SDL's default holds: {found['sensors']['default_holds']}")

    ask("After Enter, drag one finger slowly round every edge and corner of the touchpad (5 s).")
    note("touch reach")
    reach = {"x": 0, "y": 0, "x_min": 10 ** 6, "y_min": 10 ** 6}

    def edges(f):
        for t in f.touches:
            if t.down:
                reach["x"], reach["y"] = max(reach["x"], t.x), max(reach["y"], t.y)
                reach["x_min"], reach["y_min"] = min(reach["x_min"], t.x), min(reach["y_min"], t.y)
    live.wait(5.0, edges)
    found["touch_reach"] = reach
    print(f"  → x {reach['x_min']}–{reach['x']}, y {reach['y_min']}–{reach['y']}")

    # outputs: each asks a person, since only eyes and hands can tell
    def show(key: str, effects: sony.Effects, question: str) -> None:
        r.send(effects)
        live.wait(0.6)
        found[key] = {"seen": yes(question), "usb_len": r.usb_len, "note": r.note}
    show("light_red", sony.Effects(light=(255, 0, 0)), "Is the light bar RED?")
    show("players_3", sony.Effects(light=(255, 0, 0), players=sony.player_bits(3)),
         "Are three player lights on (centre and both ends)?")
    show("rumble", sony.Effects(light=(0, 255, 0), rumble_low=0.8, rumble_high=0.4),
         "Is it rumbling (and the light green)?")
    r.send(sony.Effects(light=(0, 255, 0)))
    show("trigger_right", sony.Effects(light=(0, 0, 255),
                                       right=sony.Trigger("resist", 0.15, 1.0)),
         "Press R2: does it push back hard (and the light is blue)?")
    show("mic_led", sony.Effects(light=(0, 0, 255), mic=1), "Is the mic button's light on?")
    r.send(sony.Effects(light=(0, 0, 64)))

    ask("Hands off the sticks; after Enter hold still for 3 s.")
    note("rest")
    rest = live.wait(3.0)
    names = ("LX", "LY", "RX", "RY", "LT", "RT")
    found["stick_rest"] = ({name: [min(f.axes[k] for f in rest), max(f.axes[k] for f in rest)]
                            for k, name in enumerate(names)} if rest else {})
    print(f"  → {found['stick_rest']}")
    out.write_text(json.dumps(found, indent=1, default=lambda v: list(v) if isinstance(v, tuple)
                              else repr(v)) + "\n")
    print(f"\nfindings written to {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--list", action="store_true", help="list the Sony pads hidapi sees")
    ap.add_argument("--controller", default="any", help='which pad: "edge", "dualsense", any…')
    ap.add_argument("--record", type=Path, help="keep a tape of every report (.jsonl)")
    ap.add_argument("--check", action="store_true", help="the guided hardware checks")
    ap.add_argument("--out", type=Path, default=Path("edge-findings.json"),
                    help="where --check writes its answers")
    ap.add_argument("--shared", action="store_true", help="open the pad non-exclusively")
    args = ap.parse_args()
    if not hid.available():
        raise SystemExit("hidapi is not installed here: uv sync")
    if args.shared:
        print(shared())
    if args.list:
        for d in hid.sony_devices():
            print(describe(d))
        return
    info = pick(args.controller)
    print(describe(info))
    model = models.by_ids(info["vendor_id"], info["product_id"])
    rec = None
    if args.record:
        bus = {1: "usb", 2: "bluetooth"}.get(info.get("bus_type"), "")
        rec = hid.Recorder(args.record, model.id, bus)
    live = Live(info, recorder=rec)
    try:
        if args.check:
            check(live, rec, args.out)
        else:
            watch(live)
    finally:
        live.reader.close()
        if rec is not None:
            rec.close()
            print(f"tape written to {args.record}")


if __name__ == "__main__":
    main()
