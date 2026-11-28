#!/usr/bin/env python3
"""Every repository file holding a dream, drawn through the old
code (the dream node, `lookback.Dreamer`) and through the current migrated
patch (the folded chain: Resize → Dream → … → Fade → Composite over), with a
synchronous numpy worker in place of torch — the same run of frames at a pinned
clock (`golden_frames`' rig, as `tools/lookback_proof.py`) — and how far apart
they are.

    # on the old code (a worktree of the base); --root is the package drawn:
    PYTHONPATH=<wt>/hyperspace-python uv run python tools/dream_proof.py \\
        --root <wt>/hyperspace-python save old.npz
    # on the current code:
    uv run python tools/dream_proof.py check old.npz

`--root` is put first on the path and the run asserts `hyperspace` was imported
from it. The worker is each version's own recipe with one fixed "dream" in
place of the net's gradient — every gated pixel pushed a quarter of the way to
white each job (`G`):

- old (`OldFake`): ``D ← D·(1 − k) + f·k`` on rgb; ``M ← max(M·mask_decay,
  clamp(4·blur₉(mean f)))``; ``D ← G(D, M)``; out ``(D·M, M)``;
- new (`NewFake`): ``D ← D·(1 − k) + f·k`` on rgba (Hold); ``D.rgb ← G(D.rgb,
  D.a)``; out ``D``.

Frame-perfect sameness is not the aim; the numbers say how close a migrated look stays: the largest
difference, the mean, the share of pixels off by more than 2 and by more than
16 levels, and the lit share of each.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
# every repository file whose dream the ladder keeps (`graphmigrate.forward`
# finds a dream in it; party-wake's look and its saves, acid-scene's old "dream"
# look, the desk template's fixture)
FILES = ("tests/corpus/loadable/party-wake.json",
         "tests/fixtures/desk-templates/presets/templated.json",
         "tests/fixtures/factory-sources/presets/party-wake.json",
         "tests/fixtures/plan33-v4-saves/factory--party-wake.json",
         "tests/fixtures/plan33-v4-saves/presets--acid-scene.json",
         "tests/fixtures/presets/acid-scene.json")
FRAMES = (6, 24, 48)           # the frames kept: the dream arriving, then held
SIZE = (480, 300)
PUSH = 0.25                    # `G`: a quarter of the way to white, where gated


def _blur9(x: np.ndarray) -> np.ndarray:
    """A 9 × 9 box mean, edges padded by zeros (the old mask's avg_pool2d)."""
    p = np.pad(x, 4)
    c = p.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = x.shape
    return (c[9:9 + h, 9:9 + w] - c[:h, 9:9 + w] - c[9:9 + h, :w] + c[:h, :w]) / 81.0


class OldFake:
    """The old worker's recipe, synchronous (a `lookback.LookbackSource`)."""

    def __init__(self, reg):
        self.reg = reg
        self.D = self.M = None
        self._latest = None

    def _v(self, k, default):
        p = self.reg.get(f"dream.{k}") if self.reg is not None else None
        return default if p is None else float(p.value)

    def submit(self, frame, frame_index):
        f = frame[..., :3].astype(np.float32) / 255.0
        k, decay = self._v("k", 0.05), self._v("mask_decay", 0.99)
        if self.D is None or self.D.shape != f.shape:
            self.D, self.M = f.copy(), None
        D = self.D * (1 - k) + f * k
        lum = np.clip(4.0 * _blur9(f.mean(axis=2)), 0.0, 1.0)
        self.M = lum if self.M is None or self.M.shape != lum.shape else np.maximum(
            self.M * decay, lum)
        D = np.clip(D + PUSH * (1.0 - D) * self.M[..., None], 0.0, 1.0)
        self.D = D
        out = np.concatenate([D * self.M[..., None], self.M[..., None]], axis=2)
        self._latest = (np.round(out * 255).astype(np.uint8), frame_index)

    def latest(self):
        return self._latest


class NewFake:
    """The new worker's recipe, synchronous (a `dreamhook.Source`)."""

    def __init__(self):
        self.D = None
        self._latest = None

    def ready(self):
        return True

    def submit(self, frame, frame_index, params=None):
        f = frame.astype(np.float32) / 255.0
        k = float((params or {}).get("k", 1.0))
        if k >= 1.0 or self.D is None or self.D.shape != f.shape:
            D = f.copy()
        else:
            D = self.D * (1 - k) + f * k
        D[..., :3] = np.clip(D[..., :3] + PUSH * (1.0 - D[..., :3]) * D[..., 3:4], 0.0, 1.0)
        self.D = D
        self._latest = (np.round(D * 255).astype(np.uint8), frame_index)

    def latest(self):
        return self._latest


def _paths(root: Path) -> None:
    for p in (root / "tests", root / "tools", root):
        sys.path.insert(0, str(p))


def _key(rel: str) -> str:
    p = Path(rel)
    return f"{p.parent.name}/{p.stem}"


def render(root: Path) -> dict:
    import hyperspace
    got = Path(hyperspace.__file__).resolve()
    assert str(got).startswith(str(root.resolve())), f"imported {got}, not under {root}"
    import golden_frames as gf
    out: dict = {"_imported": str(got)}
    ctx = gf.context()
    states = (("scene", {"scene": True, "hands": False, "through": False}),)
    with gf.shared_programs(ctx):
        for rel in FILES:
            rig = gf.Rig("proof", "absent", ctx, source=HERE / rel)
            try:
                section = gf.rig_section(rig, "proof", states, None)
                r = rig.renderer
                r.wiring = gf.read_graph(
                    section, effects={n.partition(".")[0] for n in rig.fx.specs}).wiring()
                if hasattr(r, "dreamer"):          # the old code
                    r.dreamer.source = OldFake(rig.reg)
                    out["_code"] = np.array("old")
                else:
                    r.fx.dream_source = NewFake()
                    out["_code"] = np.array("new")
                target = gf._target(ctx, SIZE)
                views = gf.state_views("proof", states, SIZE, [target])
                for k in range(1, max(FRAMES) + 1):
                    rig.frame(views, SIZE, 1.0)
                    if k in FRAMES:
                        out[f"{_key(rel)}@{k}"] = gf._read(ctx, target, SIZE).copy()
                errors = [v.error for v in views if v.error]
                assert not errors, errors
                out[f"{_key(rel)}#notes"] = np.array(json.dumps(rig.notes))
            finally:
                rig.close()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=HERE)
    ap.add_argument("mode", choices=("save", "check"))
    ap.add_argument("npz", type=Path)
    a = ap.parse_args()
    _paths(a.root)
    pics = render(a.root)
    print("drawn by", pics.pop("_imported"), "—", str(pics.pop("_code", "?")), "code")
    if a.mode == "save":
        np.savez_compressed(a.npz, **pics)
        print(f"saved {len([k for k in pics if '@' in k])} pictures to {a.npz}")
        return 0
    old = np.load(a.npz)
    worst = 0
    for key in sorted(k for k in pics if "@" in k):
        x, y = old[key].astype(int), pics[key].astype(int)
        d = np.abs(x - y)
        px = d.max(axis=2)
        worst = max(worst, int(d.max()))
        print(f"{key:48s} max {int(d.max()):3d}  mean {d.mean():6.3f}  "
              f">2 {(px > 2).mean():7.3%}  >16 {(px > 16).mean():7.3%}  "
              f"old lit {(x[..., :3].max(axis=2) > 8).mean():6.2%} "
              f"new lit {(y[..., :3].max(axis=2) > 8).mean():6.2%}")
    for key in sorted(k for k in pics if "#notes" in k):
        print(key, json.loads(str(pics[key]))[:4])
    print("largest difference", worst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
