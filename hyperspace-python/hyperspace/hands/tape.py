"""A hand tape: real tracking frames recorded once, replayed anywhere.

The camera is on one machine; the ghost hands, the tests and anyone
tuning the look are everywhere else. `record` reads a tracking source
(`LeapSource`, or anything with ``latest()`` and ``skeletons()``) for a
few seconds and keeps every new frame — each hand's features, confidence
and skeleton, all plain floats — as JSON. `TapeSource` plays a tape back
as a source: the same ``latest()`` / ``skeletons()`` / ``status`` /
``on`` surface, on a loop, so `HandsIO` (and through it the ghost hands)
cannot tell it from the camera. `[hands] tape` in config.toml names one
for the app; tools/hands_tape.py records and inspects them.

Like core.py and signal.py, this imports nothing from the host.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

TAPE_SCHEMA = "hyperspace.hands.tape/1"


def record(source, seconds: float, *, mode: str = "desktop", clock=time.monotonic,
           sleep=time.sleep, poll_hz: float = 240.0) -> dict:
    """Every new frame `source` delivers over `seconds`, as a tape dict:
    ``{"schema", "mode", "frames": [{"t", "hands": {side: {"features",
    "confidence", "skeleton"}}}]}``, t from the first frame. Frames with no
    hand are kept too (empty ``hands``): leaving the box is data."""
    frames: list[dict] = []
    t0 = clock()
    last = -1
    first: float | None = None
    while clock() - t0 < seconds:
        seq, t, hands = source.latest()
        if seq != last and seq > 0:
            last = seq
            skel = source.skeletons()[2] if hasattr(source, "skeletons") else {}
            first = t if first is None else first
            frames.append({"t": round(t - first, 6), "hands": {
                side: {"features": feats, "confidence": conf, "skeleton": skel.get(side)}
                for side, (feats, conf) in hands.items()}})
        sleep(1.0 / poll_hz)
    return {"schema": TAPE_SCHEMA, "mode": mode, "frames": frames}


def save(tape: dict, path: Path) -> None:
    """Compact JSON, every float to 1e-4 (mm and unit vectors alike): a
    few seconds of two hands stays a fixture-sized file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_rounded(tape), separators=(",", ":")) + "\n")


def _rounded(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _rounded(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_rounded(v) for v in x]
    return x


def load(path: Path) -> dict:
    tape = json.loads(Path(path).read_text())
    if tape.get("schema") != TAPE_SCHEMA:
        raise ValueError(f"{path}: not a hand tape (schema {tape.get('schema')!r})")
    for f in tape["frames"]:            # JSON lists back to the tuples a live frame has
        for h in f["hands"].values():
            if h.get("skeleton"):
                h["skeleton"] = _tuples(h["skeleton"])
    return tape


def _tuples(sk: dict) -> dict:
    v = lambda p: tuple(float(x) for x in p)
    bone = lambda b: {"prev": v(b["prev"]), "next": v(b["next"]),
                      "width": float(b["width"]), "rot": v(b["rot"])}
    return {"palm": v(sk["palm"]), "normal": v(sk["normal"]),
            "direction": v(sk["direction"]), "width": float(sk["width"]),
            "digits": [[bone(b) for b in d] for d in sk["digits"]],
            "arm": bone(sk["arm"]) if sk.get("arm") else None}


class TapeSource:
    """A tape as a tracking source, looping. `tape` is a dict (`load`) or
    a path. Frame seq counts every frame played, so a loop is new frames."""

    def __init__(self, tape, clock=time.monotonic, loop: bool = True):
        self.tape = tape if isinstance(tape, dict) else load(Path(tape))
        self.mode = self.tape.get("mode", "desktop")
        self.frames = self.tape["frames"]
        self.clock = clock
        self.loop = loop
        self.t0 = clock()
        self.length = (self.frames[-1]["t"] if self.frames else 0.0) + 1.0 / 90.0
        self.status = "tape" if self.frames else "tape: empty"

    @property
    def on(self) -> bool:
        return bool(self.frames)

    def _at(self) -> tuple[int, dict]:
        """(seq, frame) playing now; (0, None) for an empty tape."""
        if not self.frames:
            return 0, None
        el = self.clock() - self.t0
        lap, pos = divmod(el, self.length) if self.loop else (0, min(el, self.length))
        k = 0
        while k + 1 < len(self.frames) and self.frames[k + 1]["t"] <= pos:
            k += 1
        return int(lap) * len(self.frames) + k + 1, self.frames[k]

    def latest(self) -> tuple[int, float, dict]:
        seq, f = self._at()
        if f is None:
            return 0, -1.0, {}
        return seq, self.clock(), {s: (h["features"], float(h["confidence"]))
                                   for s, h in f["hands"].items()}

    def skeletons(self) -> tuple[int, float, dict]:
        seq, f = self._at()
        if f is None:
            return 0, -1.0, {}
        return seq, self.clock(), {s: h["skeleton"] for s, h in f["hands"].items()
                                   if h.get("skeleton")}

    def close(self) -> None:
        pass
