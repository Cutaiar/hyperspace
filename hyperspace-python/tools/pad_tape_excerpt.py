"""A slice of a probe's pad tape for the tests (plans 42, 46).

    uv run python tools/pad_tape_excerpt.py joycon-check.jsonl tests/fixtures/pads/joycon-bt-excerpt.jsonl

The probe's ``--record`` tape (`pads.hid.Recorder`) is every report the pad
sent, with a note line at the start of each guided step. A test wants the
steps, not the minutes: this keeps the header, every note, and the first
`--seconds` (0.5) of reports after each note — the Edge's excerpt was cut
this way by hand (`tests/fixtures/pads/edge-bt-excerpt.jsonl`). The
Bluetooth address is not in a tape; a findings JSON beside it carries one
in ``info.serial_number`` and ``path`` — ``--findings`` copies that file
with both taken out.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def excerpt(src: Path, dst: Path, seconds: float = 0.5) -> tuple[int, int]:
    """Write the slice; (notes kept, reports kept)."""
    rows = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    out, notes, kept = [], 0, 0
    since = None
    for d in rows:
        if "tape" in d and not out:
            out.append(d)
        elif "note" in d:
            out.append(d)
            notes += 1
            since = float(d["t"])
        elif "r" in d and since is not None and float(d["t"]) - since <= seconds:
            out.append(d)
            kept += 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("".join(json.dumps(d) + "\n" for d in out))
    return notes, kept


def scrub_findings(src: Path, dst: Path) -> None:
    """The findings with the pad's Bluetooth address and device path out."""
    d = json.loads(src.read_text())
    d.pop("path", None)
    info = d.get("info")
    if isinstance(info, dict):
        info.pop("serial_number", None)
        info.pop("path", None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(d, indent=1) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("tape", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--seconds", type=float, default=0.5, help="kept after each note")
    ap.add_argument("--findings", type=Path, nargs=2, metavar=("SRC", "DST"),
                    help="also copy a findings JSON with the address taken out")
    args = ap.parse_args()
    notes, kept = excerpt(args.tape, args.out, args.seconds)
    print(f"{args.out}: {notes} steps, {kept} reports")
    if args.findings:
        scrub_findings(*args.findings)
        print(f"{args.findings[1]}: findings, address out")


if __name__ == "__main__":
    main()
