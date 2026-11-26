#!/usr/bin/env python3
"""Plan 90 (H2): every repository file holding a look-back, drawn through the old
code and through this branch's migrated patch — the same run of frames at a
pinned clock (`golden_frames`' rig: the file copied into a scratch library,
loaded through the real `LoadedPatch`, drawn by `Renderer.draw_outputs`) — and
how far apart they are.

    # on the old code (a worktree of main); --root is the package drawn:
    PYTHONPATH=<wt>/hyperspace-python uv run python tools/lookback_proof.py \\
        --root <wt>/hyperspace-python save old.npz
    # on this branch:
    uv run python tools/lookback_proof.py check old.npz

`--root` is put first on the path and the run asserts `hyperspace` was imported
from it (a `tools/` script otherwise imports the venv's package — this
branch's — which proves nothing). The pictures are kept at `FRAMES`, so the
echoes have filled; each is compared per channel, 8-bit, and the numbers said:
the largest difference, the mean, and the share of pixels off by more than 2
and by more than 16 levels.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
# every repository file that holds a look-back once `main`'s ladder has read it
# (17; echo-faces reads an echo pin) — found by running `main`'s `graphmigrate.forward`
# over every loadable in the repository
FILES = ("loadable/kinetic/kinetic-clay.json",
         "tests/corpus/loadable/party-tracer.json",
         "tests/corpus/loadable/party-wake.json",
         "tests/fixtures/desk-templates/presets/templated.json",
         "tests/fixtures/factory-sources/presets/party-tracer.json",
         "tests/fixtures/factory-sources/presets/party-wake.json",
         "tests/fixtures/plan33-v4-saves/factory--party-tracer.json",
         "tests/fixtures/plan33-v4-saves/factory--party-wake.json",
         "tests/fixtures/plan33-v4-saves/presets--acid-scene.json",
         "tests/fixtures/plan33-v4-saves/presets--hands-glass-only.json",
         "tests/fixtures/plan33-v4-saves/presets--hands-lines.json",
         "tests/fixtures/plan33-v4-saves/presets--palette-hands.json",
         "tests/fixtures/presets/acid-scene.json",
         "tests/fixtures/presets/echo-faces.json",
         "tests/fixtures/presets/hands-glass-only.json",
         "tests/fixtures/presets/hands-lines.json",
         "tests/fixtures/presets/palette-hands.json")
FRAMES = (12, 24, 48)          # the frames kept: the trail filling, then full
SIZE = (480, 300)


def _paths(root: Path) -> None:
    for p in (root / "tests", root / "tools", root):
        sys.path.insert(0, str(p))


def _key(rel: str) -> str:
    """A short unique key for a file: its folder and stem."""
    p = Path(rel)
    return f"{p.parent.name}/{p.stem}"


def render(root: Path) -> dict:
    import numpy as np

    import hyperspace
    got = Path(hyperspace.__file__).resolve()
    assert str(got).startswith(str(root.resolve())), f"imported {got}, not under {root}"
    import golden_frames as gf
    out: dict = {"_imported": str(got)}
    ctx = gf.context()
    states = (("scene", {"scene": True, "hands": False, "through": False}),)
    with gf.shared_programs(ctx):
        for rel in FILES:
            src = HERE / rel
            rig = gf.Rig("proof", "absent", ctx, source=src)
            try:
                section = gf.rig_section(rig, "proof", states, None)
                rig.renderer.wiring = gf.read_graph(
                    section, effects={n.partition(".")[0] for n in rig.fx.specs}).wiring()
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
    import numpy as np
    pics = render(a.root)
    print("drawn by", pics.pop("_imported"))
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
        print(key, json.loads(str(pics[key]))[:3])
    print("largest difference", worst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
