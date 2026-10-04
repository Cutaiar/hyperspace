"""Record real hand frames to a tape once; replay them anywhere.

    uv run python tools/hands_tape.py record tests/fixtures/hands/rig.json --seconds 5
    uv run python tools/hands_tape.py info tests/fixtures/hands/rig.json
    uv run python tools/hands_tape.py shots tests/fixtures/hands/rig.json --out shots/
    uv run python tools/hands_tape.py synth tests/fixtures/hands/synthetic.json

`record` needs the camera: it opens the tracker in `[hands] mode` (or
--mode) and keeps every frame for --seconds — features, confidence and
the full skeleton of each hand — as JSON (hyperspace/hands/tape.py).
Move both hands through the box, open and closed, in and out of it.
Everyone else replays it: `[hands] tape = "<path>"` in config.toml plays
it in the app instead of the camera (with `enabled = true`), and the
tests replay every tape under tests/fixtures/hands/.

`info` prints what a tape holds; `shots` renders it offscreen through
the ghost hands over a running scene, a PNG every --every frames;
`synth` writes a tape of the synthetic hands the tests use (no camera).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hyperspace.hands import tape

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record", help="record from the camera")
    rec.add_argument("path", type=Path)
    rec.add_argument("--seconds", type=float, default=5.0)
    rec.add_argument("--mode", help="desktop | screentop | hmd (default: [hands] mode)")
    inf = sub.add_parser("info", help="what a tape holds")
    inf.add_argument("path", type=Path)
    sh = sub.add_parser("shots", help="render a tape through the ghost hands")
    sh.add_argument("path", type=Path)
    sh.add_argument("--out", type=Path, default=Path("ghost-shots"))
    sh.add_argument("--every", type=int, default=30)
    sh.add_argument("--size", default="960x600")
    sh.add_argument("--fx", default="warp", help="effects on, comma-separated ('' none)")
    sy = sub.add_parser("synth", help="a tape of the tests' synthetic hands")
    sy.add_argument("path", type=Path)
    args = ap.parse_args()
    {"record": _record, "info": _info, "shots": _shots, "synth": _synth}[args.cmd](args)


def _record(args) -> None:
    from hyperspace import config
    from hyperspace.hands.core import LeapSource

    mode = args.mode or config.load()["hands"]["mode"]
    try:
        src = LeapSource(mode)
    except ImportError as e:
        raise SystemExit(f"{e} — the Ultraleap bindings aren't installed; "
                         "see Install in docs/plans/08-hands.md") from e
    src.connecting.join(5.0)
    print(f"{src.status} — recording {args.seconds:.1f} s in {mode} mode; move both hands",
          file=sys.stderr)
    t = tape.record(src, args.seconds, mode=mode)
    src.close()
    tape.save(t, args.path)
    print(f"wrote {args.path}: {_summary(t)}")


def _summary(t: dict) -> str:
    fr = t["frames"]
    if not fr:
        return "no frames — is the service running and the camera seen?"
    sides = {s: sum(1 for f in fr if s in f["hands"]) for s in ("left", "right")}
    digits = sum(1 for f in fr for h in f["hands"].values()
                 if h.get("skeleton") and h["skeleton"]["digits"])
    dur = fr[-1]["t"]
    return (f"{len(fr)} frames over {dur:.2f} s ({len(fr) / max(dur, 1e-6):.0f} fps), "
            f"mode {t['mode']}, left in {sides['left']}, right in {sides['right']}, "
            f"{digits} hand-frames with fingers")


def _info(args) -> None:
    print(f"{args.path}: {_summary(tape.load(args.path))}")


def _synth(args) -> None:
    """Two seconds: the hands come in, the right closes to a fist and
    opens again, the left leaves for the last half second."""
    sys.path.insert(0, str(ROOT / "tests"))
    from fake_hands import hand

    from hyperspace.hands import features, skeleton

    frames = []
    for k in range(60):
        t = k / 30.0
        hands = {}
        if t < 1.5:
            hands["left"] = hand("left", "open", (-90.0 + 20.0 * t, 200.0, 0.0))
        hands["right"] = hand("right", "fist" if 0.6 < t < 1.2 else "open",
                              (90.0, 190.0 + 30.0 * t, 10.0))
        frames.append({"t": round(t, 6), "hands": {
            s: {"features": features(h), "confidence": 1.0, "skeleton": skeleton(h)}
            for s, h in hands.items()}})
    t = {"schema": tape.TAPE_SCHEMA, "mode": "desktop", "synthetic": True, "frames": frames}
    tape.save(t, args.path)
    print(f"wrote {args.path}: {_summary(t)}")


def _shots(args) -> None:
    import moderngl
    import numpy as np
    from PIL import Image

    from hyperspace.fx import FxState
    from hyperspace.hands import HandSettings, HandsIO
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    w, h = (int(v) for v in args.size.split("x"))
    clock = _Clock()
    io = HandsIO(HandSettings.from_config({}), {"out": "", "tape": str(args.path)},
                 clock=clock)
    ctx = moderngl.create_context(standalone=True)
    fx = FxState()
    for name in filter(None, args.fx.split(",")):
        fx.values[name]["on"] = True
    r = Renderer(ctx, fx=fx)
    r.ghost.state.on, r.ghost.source = True, io
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h))])
    s = ViewState(ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25, faces=True)
    args.out.mkdir(parents=True, exist_ok=True)
    n = int(io.source.length * 60)
    for k in range(n):
        clock.t = k / 60
        io.poll(1 / 60)
        s.integrate(1 / 60)
        fbo.use()
        ctx.viewport = (0, 0, w, h)
        r.draw(s, w, h, t_now=clock.t)
        if k % args.every == 0:
            img = np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1]
            Image.fromarray(img).save(args.out / f"ghost-{k:04d}.png")
    print(f"{n} frames, a shot every {args.every} → {args.out}/")


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


if __name__ == "__main__":
    main()
