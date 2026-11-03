"""The UV-field continuity harness: does a knob step move the picture a
little, or somewhere else?

An effect is run over a *UV-encoded* source — a texture whose red and
green are each pixel's own (u, v) — so its output says, per pixel, where
in the source that pixel came from: the effect's sampling field, exact,
no flow estimation needed (an "optical flow" whose ground truth is the
picture). Run for consecutive frames at the frame rate with the effect's
clocks moving (`FxChain.run_one` → `FxState.advance_to`), the field moves
a little each frame: `displacement` is the mean distance, in pixels, each
pixel's source moved between two frames. Step a param on one frame and
compare that frame's displacement with the still frames': a rate-like
param that is integrated (the effect's speed, a `@clock`) changes how fast
the field moves — the step frame's displacement is bounded by the frames
around it; one the shader multiplies into the phase (`u_phase * u_drift`)
moves the field by `phase × Δ` — whole screens, hours in — and the step
frame's displacement is far off the rest's.

`tests/test_fx_clock.py` uses it; K2–K4 prove each port with it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

import numpy as np

from hyperspace.fx import FxChain, FxState

W, H = 320, 200
DT = 1 / 60


def uv_source(w: int = W, h: int = H) -> np.ndarray:
    """The UV map as the pool's half-float RGBA: red u, green v (pixel
    centres), blue 0, alpha 1 — premultiplied and opaque, as a frame is."""
    u = (np.arange(w, dtype=np.float32) + 0.5) / w
    v = (np.arange(h, dtype=np.float32) + 0.5) / h
    img = np.zeros((h, w, 4), dtype=np.float32)
    img[..., 0] = u[None, :]
    img[..., 1] = v[:, None]
    img[..., 3] = 1.0
    return img.astype(np.float16)


def decode(raw: bytes, w: int = W, h: int = H) -> np.ndarray:
    """A pass's output over the UV source → the field (h, w, 2): where each
    pixel sampled, in source pixels."""
    px = np.frombuffer(raw, dtype=np.float16).reshape(h, w, 4).astype(np.float32)
    return np.stack([px[..., 0] * w, px[..., 1] * h], axis=-1)


def displacement(a: np.ndarray, b: np.ndarray) -> float:
    """The mean distance, px, between two fields' samples."""
    return float(np.hypot(*(b - a).transpose(2, 0, 1)).mean())


@dataclass
class Run:
    """One continuity run: the per-frame displacements of the frames before
    the step (`rest`), of the step frame (`step`) and after it (`after`)."""

    rest: list[float]
    step: float
    after: list[float]

    def bound(self, factor: float = 2.0, floor_px: float = 1.0) -> float:
        """What a continuous step may move: the largest still frame's
        displacement × `factor` (a rate that doubles doubles the drift), and
        never less than `floor_px` (the half-float field is good to a
        fraction of a pixel)."""
        return max(factor * max([*self.rest, *self.after], default=0.0), floor_px)

    def continuous(self, factor: float = 2.0, floor_px: float = 1.0) -> bool:
        return self.step <= self.bound(factor, floor_px)


def run(ctx, state: FxState, name: str, param: str, before: float, after: float, *,
        values: dict | None = None, phase: float = 3613.7, t0: float = 100.0, frames: int = 6,
        settle: int = 3, w: int = W, h: int = H) -> Run:
    """Effect `name` over the UV source for `frames` still frames, then
    `param` stepped `before` → `after` on the next, then `settle` more.
    `values` sets the effect's other params first (an amount big enough to
    see). `phase` is where the effect's clock stands first (an hour at
    speed 1 — the show's fourth hour at a quarter; not a round number, so a
    jump of whole mirrored screens cannot land back on itself), since the
    jump grows with it; each `@clock` of the effect stands where that hour
    at these knobs left it (phase × its rate). Every frame is DT apart; the clocks move through
    `run_one`."""
    v = state.values[name]
    v.update(on=True, mix=1.0)
    v.update(values or {})
    v[param] = before
    state.phase[name] = phase
    # its `@clock`s where an hour at these knobs left them: phase × rate
    # (u_phase is already speed × seconds), wrapped to a period if any
    clocks = state.clocks.setdefault(name, {})
    for c in state.specs[name].clocks:
        x = phase * math.prod(float(v[k]) for k in c.factors)
        clocks[c.uniform] = x % c.period if c.period else x
    chain = FxChain(ctx, state)
    try:
        (src, _), (_, dst) = chain.pool((w, h))
        src.write(uv_source(w, h).tobytes())
        fields: list[np.ndarray] = []
        for k in range(frames + 1 + settle):
            if k == frames:
                v[param] = after
            chain.run_one(name, src, dst, t0 + k * DT)
            fields.append(decode(dst.read(components=4, dtype="f2"), w, h))
        assert not chain.errors, chain.errors
        d = [displacement(a, b) for a, b in pairwise(fields)]
        # d[k] is the move from frame k to k+1: the step lands between
        # frames `frames - 1` and `frames`
        return Run(rest=d[:frames - 1], step=d[frames - 1], after=d[frames:])
    finally:
        chain.release()
