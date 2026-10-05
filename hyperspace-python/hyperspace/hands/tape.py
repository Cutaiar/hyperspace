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

import bisect
import json
import time
from pathlib import Path

# no tracking frame for this long: no hands. The one definition: a camera's
# frames go stale after it (hands/core.py imports it from here — tape is
# the leaf core imports, so the constant lives with it), and a tape that
# does not loop goes quiet this long after its last frame
STALE_S = 0.25

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
        if hasattr(source, "snapshot"):        # features and skeletons of one frame
            seq, t, hands, skel = source.snapshot()
        else:
            (seq, t, hands), skel = source.latest(), {}
        if seq != last and seq > 0:
            last = seq
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
        self._ts = [f["t"] for f in self.frames]
        self.clock = clock
        self.loop = loop
        self.t0 = clock()
        self.length = (self.frames[-1]["t"] if self.frames else 0.0) + 1.0 / 90.0
        self.status = "tape" if self.frames else "tape: empty"

    @property
    def on(self) -> bool:
        return bool(self.frames)

    def _at(self) -> tuple[int, dict | None]:
        """(seq, frame) playing now; (0, None) for an empty tape, and for
        a tape that does not loop once it has gone stale past its end."""
        if not self.frames:
            return 0, None
        el = self.clock() - self.t0
        if self.loop:
            lap, pos = divmod(el, self.length)
        elif el > self.length + STALE_S:
            return len(self.frames), None
        else:
            lap, pos = 0, el
        k = max(bisect.bisect_right(self._ts, pos) - 1, 0)
        return int(lap) * len(self.frames) + k + 1, self.frames[k]

    def snapshot(self) -> tuple[int, float, dict, dict]:
        """One frame's features and skeletons (`LeapSource.snapshot`)."""
        seq, f = self._at()
        if f is None:
            return seq, -1.0, {}, {}
        hands = f["hands"]
        return (seq, self.clock(),
                {s: (h["features"], float(h["confidence"])) for s, h in hands.items()},
                {s: h["skeleton"] for s, h in hands.items() if h.get("skeleton")})

    def latest(self) -> tuple[int, float, dict]:
        seq, t, hands, _ = self.snapshot()
        return seq, t, hands

    def skeletons(self) -> tuple[int, float, dict]:
        seq, t, _, skel = self.snapshot()
        return seq, t, skel

    def close(self) -> None:
        pass
