"""Watch the poi's hand on a real Joy-Con, and replay a tape through it
(plan 47, the poi: hyperspace/poi.py).

    uv run python tools/poi_probe.py                        # live: the poi's numbers, ten lines a second
    uv run python tools/poi_probe.py --record poi.jsonl     # …and keep the tape (and the calibration)
    uv run python tools/poi_probe.py --replay poi.jsonl     # a tape through the poi: a table, a row a note
    uv run python tools/poi_probe.py --replay poi.jsonl --series 16 22    # every frame between two times
    uv run python tools/poi_probe.py --replay poi.jsonl --hand 2 --weight 1  # …with the dials set
    uv run python tools/poi_probe.py --replay tests/fixtures/pads/joycon-poi-excerpt.jsonl \
        --findings docs/plans/assets/46-joycon/joycon-findings.json        # the owner's own tape

The pad is read exactly as the app reads it (`pads.hid.HidPad`, its
per-report turn on the report clock, the frame's newest sample through
the calibration and the axis map, `poi.step` on a registry with the
camera's pan and zoom), so what prints here is what the shape does. Close
the app first: hidapi opens the pad exclusively.

**Live**, each line is the poi's state now: the reading (|accel| in g,
the turn in deg/s), the attitude's error against gravity (the degrees
between the accel through the attitude and straight up — this is what
leaks gravity into the hand), the push left after gravity (lin, g), how
long the pad has read still, the hand's speed and place, the weight, the
pan and zoom the shape would get, and the walls it is held at: `hand` at
`poi.HAND_LIMIT` world units from home, `pan` at the pan's reach. Type a word and Enter to put a note in the tape ("carry right",
"swing") — a bare Enter notes "mark"; A on the pad resets, as in the app;
Ctrl-C ends it. The calibration the reader found goes beside the tape
(``<tape>.findings.json``: the flash records, as the probe's --check
writes them), so a replay reads the sensors exactly as live did.

**Replay** prints, for each note's window, how still the pad read, the
attitude error and the push (median / worst), the hand's travel (at the
end / farthest) and speed, and the pan's farthest reach — the numbers the
2026-11-02 tape was diagnosed with — and with ``--series`` every frame
between two times. ``--findings`` names the calibration file when it is
not beside the tape (the probe's ``joycon-findings.json`` does).

The tool reads `hyperspace/poi.py` as it stands and shows what that does;
the tape is a recording, not a verdict. Salvaged from #342 (closed), whose
changes to `poi.py` are not in the tree (register row 786).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from hyperspace import poi
from hyperspace.pads import gesture, hid, models, nintendo
from hyperspace.params import PAN_RANGE, Registry

# ---------------------------------------------------------------- the poi on a reading

class Rig:
    """A registry with the camera's pan and zoom, the poi registered on it
    and on, and a pad the poi reads (duck-typed as gamepad.Pad)."""

    def __init__(self, **dials):
        self.view = SimpleNamespace(zoom=1.0, pan=[0.0, 0.0])
        reg = self.reg = Registry()
        for i, axis in enumerate("xy"):
            reg.continuous(f"camera.pan.{axis}", f"Pan {axis.upper()}",
                           lambda i=i: self.view.pan[i],
                           lambda v, i=i: self.view.pan.__setitem__(i, v),
                           lo=-PAN_RANGE, hi=PAN_RANGE)
        reg.continuous("camera.zoom", "Zoom", lambda: self.view.zoom,
                       lambda v: setattr(self.view, "zoom", v), lo=0.005, hi=200.0, log=True)
        self.state = poi.PoiState()
        poi.register(reg, self.state, dials)
        reg["poi.on"].set(True)
        self.motion = gesture.Motion()
        self.buttons: list[int] = []
        self.was: list[int] = []
        self.pad = SimpleNamespace(on=True, has=lambda cap: cap == "motion",
                                   motion_lanes=lambda: self.motion.lanes(), motion=self.motion,
                                   buttons_named={"A": models.CANON["A"]},
                                   pressed=self._pressed, hat_pressed=lambda h: False,
                                   hat=0, prev_hat=0)

    def _pressed(self, code: int) -> bool:
        down = code < len(self.buttons) and bool(self.buttons[code])
        before = code < len(self.was) and bool(self.was[code])
        return down and not before

    def frame(self, f, turned, n: int, cal, amap, dt: float) -> None:
        """One frame as `gamepad.Pad._extras` makes it: the reader's summed
        turn (degrees, the sensor's axes), the frame's newest sample."""
        self.was, self.buttons = self.buttons, list(f.buttons) if f is not None else []
        self.motion.add_turn(amap.pick(turned, amap.gyro))
        if f is not None and n:
            self.motion.step(amap.pick(cal.gyro_dps(f.gyro), amap.gyro),
                             amap.pick(cal.accel_g(f.accel), amap.accel), dt, integrate=False)
        else:
            self.motion.decay(dt)
        poi.step(self.state, self.pad, self.reg, dt, "probe")

    def numbers(self) -> dict:
        st, m = self.state, self.motion
        accel = list(m.accel)
        up = poi._apply(st.att, accel)
        a = poi._norm(accel)
        err = math.degrees(math.acos(max(-1.0, min(1.0, up[1] / a)))) if a > 1e-6 else float("nan")
        lin = poi._norm(poi._sub(up, [0.0, 1.0, 0.0]))
        walls = " ".join(name for name, held in (
            ("hand", poi._norm(st.wrist) >= poi.HAND_LIMIT - 1e-9),
            ("pan", max(abs(v) for v in self.view.pan) >= PAN_RANGE - 1e-9)) if held)
        return {"a": a, "rate": poi._norm(list(m.gyro)), "err": err, "lin": lin,
                "still": st.still, "speed": poi._norm(st.wrist_v), "wrist": list(st.wrist),
                "ball": list(st.ball), "pan": list(self.view.pan), "zoom": self.view.zoom,
                "walls": walls, "settled": st.settled}


def line(t: float, n: dict, rate_hz: float | None = None, note: str = "") -> str:
    w, b = n["wrist"], n["ball"]
    hz = f"{rate_hz:3.0f}/s " if rate_hz is not None else ""
    return (f"{t:7.2f}s {hz}|a| {n['a']:.3f}  turn {n['rate']:5.1f}°/s  err {n['err']:4.1f}°  "
            f"lin {n['lin']:.3f}g  still {n['still']:4.2f}  v {n['speed']:4.2f}  "
            f"wrist {w[0]:+.2f} {w[1]:+.2f} {w[2]:+.2f}  weight {b[0]:+.2f} {b[1]:+.2f} {b[2]:+.2f}  "
            f"pan {n['pan'][0]:+.2f} {n['pan'][1]:+.2f}  zoom {n['zoom']:.2f}"
            + (f"  wall {n['walls']}" if n["walls"] else "")
            + ("" if n["settled"] else "  (no gravity yet)") + (f"  {note}" if note else ""))


# ---------------------------------------------------------------- live

def flash_of(reader) -> dict:
    return {f"{addr:#06x}": bytes(data).hex() for addr, data in reader.flash.items()}


def live(info: dict, record: Path | None, dials: dict) -> None:
    model = models.by_ids(info["vendor_id"], info["product_id"])
    rec = None
    if record is not None:
        bus = {1: "usb", 2: "bluetooth"}.get(info.get("bus_type"), "")
        rec = hid.Recorder(record, model.id, bus)
    reader = hid.HidPad(info, recorder=rec)
    rig = Rig(**dials)
    notes: list[str] = []

    def keys() -> None:
        while True:
            try:
                text = input()
            except EOFError:
                return
            notes.append(text.strip() or "mark")
    threading.Thread(target=keys, daemon=True).start()
    print("reading… (type a word and Enter to note it in the tape; A resets; Ctrl-C ends)")
    t0 = last = time.monotonic()
    shown = 0.0
    wrote_findings = False
    count0, c_t0, rate = 0, t0, 0.0
    try:
        while True:
            now = time.monotonic()
            dt, last = now - last, now
            f = reader.latest()
            turned, n = reader.take_turn()
            cal = reader.calibration
            amap = gesture.axis_map_of(None, reader)
            rig.frame(f, turned, n, cal, amap, dt)
            if not wrote_findings and reader.flash and record is not None:
                side = record.with_suffix(record.suffix + ".findings.json")
                side.write_text(json.dumps({"model": model.id, "flash": flash_of(reader),
                                            "note": reader.note}, indent=1))
                wrote_findings = True
                print(f"calibration written to {side}")
            if now - c_t0 >= 1.0:
                rate = (reader.reports - count0) / (now - c_t0)
                count0, c_t0 = reader.reports, now
            note = ""
            while notes:
                note = notes.pop(0)
                if rec is not None:
                    rec.note(note)
                print(f"--- {note}")
            if f is None:
                if now - shown >= 0.5:
                    print(f"{now - t0:7.2f}s waiting for the pad… {reader.note}")
                    shown = now
            elif now - shown >= 0.1 or note:
                print(line(now - t0, rig.numbers(), rate, note))
                shown = now
            time.sleep(1 / 120)
    except KeyboardInterrupt:
        print()
    finally:
        reader.close()
        if rec is not None:
            rec.close()
            print(f"tape written to {record}")


# ---------------------------------------------------------------- replay

def calibration_for(tape: Path, findings: Path | None, kind: str) -> nintendo.Calibration:
    side = findings or tape.with_suffix(tape.suffix + ".findings.json")
    if not side.exists():
        print(f"no calibration beside the tape ({side.name}): nominal", file=sys.stderr)
        return nintendo.Calibration()
    found = json.loads(side.read_text())
    records = {int(a, 16): bytes.fromhex(h) for a, h in found["flash"].items()}
    return nintendo.calibration(records, kind)


def frames(tape: Path, findings: Path | None, dials: dict):
    """The tape through the app's path, a frame a report: (the note it is
    under, the tape's time, the rig, `Rig.numbers`)."""
    rows = [json.loads(ln) for ln in tape.read_text().splitlines() if ln.strip()]
    head = rows[0] if rows and "tape" in rows[0] else {}
    model = str(head.get("model", "joycon-l"))
    kind = nintendo.kind_of(model)
    cal = calibration_for(tape, findings, kind)
    amap = nintendo.axis_map_for(kind)
    rig = Rig(**dials)
    turn = hid.Turn()
    note, last = "(start)", None
    for d in rows[1:]:
        if "note" in d:
            note = str(d["note"])
            continue
        if "r" not in d:
            continue
        t, r = float(d["t"]), bytes.fromhex(d["r"])
        samples = nintendo.gyro_of(r, None)
        if samples is not None:
            turn.add(samples, t, cal, nintendo.report_clock(r))
        f = nintendo.decode(r, kind, cal)
        if f is None or not f.full:
            continue
        dt = 0.0 if last is None else min(0.25, t - last)
        last = t
        turned, n = turn.take()
        rig.frame(f, turned, n, cal, amap, dt)
        yield note, t, rig, rig.numbers()


def replay(tape: Path, findings: Path | None, dials: dict, series: tuple[float, float] | None,
           every: float) -> dict[str, dict]:
    """The table, and each window's numbers behind it."""
    stats: dict[str, dict] = {}
    shown = -1e9
    for note, t, _rig, num in frames(tape, findings, dials):
        s = stats.setdefault(note, {"n": 0, "still": 0, "err": [], "lin": [], "travel": [],
                                    "speed": [], "pan": [], "walls": 0, "t0": t})
        s["n"] += 1
        s["still"] += num["still"] >= poi.STILL_S
        s["err"].append(num["err"])
        s["lin"].append(num["lin"])
        s["travel"].append(poi._norm(num["wrist"]))
        s["speed"].append(num["speed"])
        s["pan"].append(max(abs(num["pan"][0]), abs(num["pan"][1])))
        s["walls"] += bool(num["walls"])
        s["t1"] = t
        if series is not None and series[0] <= t <= series[1] and t - shown >= every:
            print(line(t, num, None, note))
            shown = t

    def med(v):
        v = sorted(x for x in v if math.isfinite(x))
        return v[len(v) // 2] if v else float("nan")
    print(f"\n{'window':16} {'secs':>5} {'still':>5}  {'err° med/max':>13}  {'lin g med/max':>14}  "
          f"{'travel end/max':>15}  {'v max':>5}  {'pan max':>7}  {'walled':>6}")
    for name, s in stats.items():
        if not s["n"]:
            continue
        print(f"{name[:16]:16} {s['t1'] - s['t0']:5.1f} {100 * s['still'] / s['n']:4.0f}%  "
              f"{med(s['err']):5.1f}/{max(s['err']):5.1f}  {med(s['lin']):6.3f}/{max(s['lin']):6.3f}  "
              f"{s['travel'][-1]:6.2f}/{max(s['travel']):6.2f}  {max(s['speed']):5.2f}  "
              f"{max(s['pan']):7.2f}  {100 * s['walls'] / s['n']:5.0f}%")
    print(f"\nthe walls: the hand at {poi.HAND_LIMIT:.1f} world units from home, the pan at "
          f"±{PAN_RANGE:.1f}; a 16:9 output through the default eye shows about ±3 across, "
          "±1.7 down")
    return stats


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--controller", default="nintendo", help='which pad: "nintendo" (any Joy-Con), '
                    '"joycon-l", "edge"…')
    ap.add_argument("--record", type=Path, help="keep a tape of every report (.jsonl)")
    ap.add_argument("--replay", type=Path, help="a tape through the poi instead of a pad")
    ap.add_argument("--findings", type=Path, help="the calibration for --replay (a findings JSON)")
    ap.add_argument("--series", nargs=2, type=float, metavar=("FROM", "TO"),
                    help="--replay: every frame between two tape times (seconds)")
    ap.add_argument("--every", type=float, default=0.0, help="--series: at most a line this often")
    dial = ap.add_argument             # a flag per dial, named by the loop, read by getattr below
    for key, (lo, hi) in poi.RANGES.items():
        dial(f"--{key}", type=float, default=None, help=f"poi.{key} ({lo}–{hi})")
    args = ap.parse_args(argv)
    dials = {k: getattr(args, k) for k in poi.RANGES if getattr(args, k) is not None}
    if args.replay is not None:
        replay(args.replay, args.findings, dials, tuple(args.series) if args.series else None,
               args.every)
        return
    if not hid.available():
        raise SystemExit("hidapi is not installed here: uv sync")
    found = [d for d in hid.pad_devices()
             if models.matches(args.controller, models.by_ids(d["vendor_id"], d["product_id"]),
                               d["vendor_id"], d["product_id"])]
    if not found:
        raise SystemExit(f"no pad for controller = {args.controller!r} — paired and awake? "
                         "(a sleeping Joy-Con wakes when a button is pressed)")
    info = found[0]
    m = models.by_ids(info["vendor_id"], info["product_id"])
    print(f"{m.name}  {info.get('vendor_id', 0):04x}:{info.get('product_id', 0):04x}")
    live(info, args.record, dials)


if __name__ == "__main__":
    main()
