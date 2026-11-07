"""Watch the poi's hand on a real Joy-Con, and replay a tape through it
(plan 47, the poi: hyperspace/poi.py).

    uv run python tools/poi_probe.py                        # live: the poi's numbers, ten lines a second
    uv run python tools/poi_probe.py --record poi.jsonl     # …and keep the tape (and the calibration)
    uv run python tools/poi_probe.py --replay poi.jsonl     # a tape through the poi: a table, a row a note
    uv run python tools/poi_probe.py --replay poi.jsonl --series 16 22    # every frame between two times
    uv run python tools/poi_probe.py --replay poi.jsonl --hand 2 --weight 1  # …with the dials set
    uv run python tools/poi_probe.py --replay tests/fixtures/pads/joycon-poi-excerpt.jsonl \
        --findings docs/plans/assets/46-joycon/joycon-findings.json        # the owner's own tape

The pad is read by the app's own code: a real `gamepad.Pad` polls the
reader (`pads.hid.HidPad` live, `pads.hid.TapePad` on a replay), and
`poi.step` runs on the real camera params (`params.build_patch`), so what
prints here is what the poi's code does. The app itself doesn't run it on a
Joy-Con (`poi.no_position`, register row 686); this tool does. Close
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
end / farthest) and speed, the pan's farthest reach and the frames at a wall — the numbers the
2026-11-02 tape was diagnosed with — and with ``--series`` every frame
between two times. ``--findings`` names the calibration file when it is
not beside the tape (the probe's ``joycon-findings.json`` does). A replay
runs a frame at least every 1/60 s, so a pause in the tape is what the app
would have seen: after `hid.STALE_S` the pad is lost and reads afresh.

The tool reads `hyperspace/poi.py` as it stands and shows what that does;
the tape is a recording, not a verdict. Salvaged from #342 (closed), whose
changes to `poi.py` are not in the tree (register row 786).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
import threading
import time
from pathlib import Path

from hyperspace import gamepad, poi
from hyperspace.pads import gesture, hid, models, nintendo
from hyperspace.params import PAN_RANGE, build_patch
from hyperspace.view import ViewState

FRAME_S = 1 / 60          # the longest a replay goes between frames

# ---------------------------------------------------------------- the poi on a reading

class ProbePad(gamepad.Pad):
    """The app's pad, polling the reader it is handed (None: nothing lent
    this frame). A tape entry never looks for a joystick or the libusb road."""

    def __init__(self):
        super().__init__(tape="probe")
        self.reader = None

    def _hid_reader(self):
        return self.reader

    @property
    def model(self):
        """The reader's, of no family: the app's poi reads no Nintendo pad (`poi.no_position`,
        register row 686), and this tool exists to run that same code on one's tape."""
        m = self.__dict__.get("_model")
        return dataclasses.replace(m, family="probe") if m is not None else None

    @model.setter
    def model(self, m) -> None:
        self.__dict__["_model"] = m


class Rig:
    """The real camera params, the poi registered on them and on, and the
    app's pad for it to read."""

    def __init__(self, **dials):
        self.view = ViewState()
        self.reg = build_patch(self.view)
        self.state = poi.PoiState()
        poi.register(self.reg, self.state, dials)
        self.reg["poi.on"].set(True)
        self.pad = ProbePad()

    @property
    def motion(self) -> gesture.Motion:
        return self.pad.motion           # a lost pad comes back with a new one

    def frame(self, reader, dt: float) -> None:
        """One frame as the app makes it: `Pad.poll` on `reader`, `poi.step`."""
        self.pad.reader = reader
        self.pad.poll(dt)
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
        rec = hid.Recorder(record, model.id, "usb" if hid._on_usb(info) else "bluetooth")
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
            dt, last = min(0.25, now - last), now
            rig.frame(reader, dt)
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
            if not rig.pad.on:
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

def calibration_for(tape: Path, findings: Path | None, reader: hid.TapePad):
    """The calibration the live run read: from `findings` if named (it must
    be there), else from beside the tape, else nominal, and said."""
    side = findings or tape.with_suffix(tape.suffix + ".findings.json")
    if not side.exists():
        if findings is not None:
            raise SystemExit(f"no such findings file: {side}")
        print(f"no calibration beside the tape ({side.name}): nominal", file=sys.stderr)
        return reader.codec.Calibration()
    try:
        found = json.loads(side.read_text())
    except ValueError as e:
        raise SystemExit(f"{side}: not JSON ({e})") from None
    if not reader.nintendo:
        print(f"{side.name}: a {reader.model.id} tape's calibration is not read from it: nominal",
              file=sys.stderr)
        return reader.codec.Calibration()
    flash = found.get("flash") if isinstance(found, dict) else None
    if not isinstance(flash, dict):
        raise SystemExit(f"{side}: no flash records")
    try:
        records = {int(a, 16): bytes.fromhex(h) for a, h in flash.items()}
    except (TypeError, ValueError) as e:
        raise SystemExit(f"{side}: bad flash records ({e})") from None
    return nintendo.calibration(records, reader.kind)


def notes_of(tape: Path) -> list[tuple[float, str]]:
    """The tape's notes and their times. `TapePad` reads the reports and
    leaves these; as it does, a line cut short or not a row is skipped."""
    out = []
    for text in tape.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(text)
            if isinstance(d, dict) and "note" in d:
                out.append((float(d["t"]), str(d["note"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def frames(tape: Path, findings: Path | None, dials: dict):
    """The tape through the app's path, on the tape's own time: (which note
    this is since the tape began, the note, the time, the rig, `Rig.numbers`)
    for each report's frame that has sensors. Between reports further apart
    than `FRAME_S` the app's frames run too, on the last report, and past
    `hid.STALE_S` on none: the reader says the pad is lost."""
    now = [0.0]
    try:
        reader = hid.TapePad(tape, loop=False, clock=lambda: now[0])
    except (OSError, ValueError) as e:
        raise SystemExit(f"{tape}: {e}") from None
    reader.calibration = calibration_for(tape, findings, reader)
    rig = Rig(**dials)
    notes = notes_of(tape)
    window, note, read = 0, "(start)", None
    for t, _raw in reader.reports:
        while notes and notes[0][0] <= t:
            window, note = window + 1, notes.pop(0)[1]
        if read is not None:
            while t - now[0] > FRAME_S:
                now[0] += FRAME_S
                rig.frame(None if now[0] - read > hid.STALE_S else reader, FRAME_S)
        dt, now[0], read = (0.0 if read is None else t - now[0]), t, t
        rig.frame(reader, dt)
        if rig.pad.motion_lanes() is not None:
            yield window, note, t, rig, rig.numbers()


def replay(tape: Path, findings: Path | None, dials: dict, series: tuple[float, float] | None,
           every: float) -> list[dict]:
    """The table, a row a note, and each row's numbers behind it. A tape
    with nothing in it that reads as a pad's sensors is an error."""
    rows: dict[int, dict] = {}
    shown = -1e9
    for window, note, t, _rig, num in frames(tape, findings, dials):
        s = rows.setdefault(window, {"note": note, "n": 0, "still": 0, "err": [], "lin": [],
                                     "travel": [], "speed": [], "pan": [], "walls": 0, "t0": t})
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
    if not rows:
        raise SystemExit(f"{tape}: no report here decoded with sensors, so there is nothing to show")

    def med(v):
        v = sorted(x for x in v if math.isfinite(x))
        return v[len(v) // 2] if v else float("nan")

    def worst(v):                       # (max alone keeps a NaN that comes first: a zero reading's)
        return max((x for x in v if math.isfinite(x)), default=float("nan"))
    print(f"\n{'window':16} {'secs':>5} {'still':>5}  {'err° med/max':>13}  {'lin g med/max':>14}  "
          f"{'travel end/max':>15}  {'v max':>5}  {'pan max':>7}  {'walled':>6}")
    for s in rows.values():
        print(f"{s['note'][:16]:16} {s['t1'] - s['t0']:5.1f} {100 * s['still'] / s['n']:4.0f}%  "
              f"{med(s['err']):5.1f}/{worst(s['err']):5.1f}  {med(s['lin']):6.3f}/{worst(s['lin']):6.3f}  "
              f"{s['travel'][-1]:6.2f}/{worst(s['travel']):6.2f}  {worst(s['speed']):5.2f}  "
              f"{worst(s['pan']):7.2f}  {100 * s['walls'] / s['n']:5.0f}%")
    print(f"\nthe walls: the hand at {poi.HAND_LIMIT:.1f} world units from home, the pan at "
          f"±{PAN_RANGE:.1f}; a 16:9 output through the default eye shows about ±3 across, "
          "±1.7 down")
    return list(rows.values())


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
    for key, (lo, hi) in poi.RANGES.items():
        ap.add_argument(f"--{key}", type=float, default=None, help=f"poi.{key} ({lo}–{hi})")
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
