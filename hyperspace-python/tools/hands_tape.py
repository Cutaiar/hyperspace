"""Record real hand frames to a tape once; replay them anywhere.

    uv run python tools/hands_tape.py record tests/fixtures/hands/rig.json --seconds 5
    uv run python tools/hands_tape.py info tests/fixtures/hands/rig.json
    uv run python tools/hands_tape.py shots tests/fixtures/hands/rig.json --out shots/
    uv run python tools/hands_tape.py synth tests/fixtures/hands/synthetic.json
    uv run python tools/hands_tape.py styles tests/fixtures/hands/synthetic.json

`record` needs the camera: it opens the tracker in `[hands] mode` (or
--mode) and keeps every frame for --seconds — features, confidence and
the full skeleton of each hand — as JSON (hyperspace/hands/tape.py).
Move both hands through the box, open and closed, in and out of it.
Everyone else replays it: `[hands] tape = "<path>"` in config.toml plays
it in the app instead of the camera (with `enabled = true`), and the
tests replay every tape under tests/fixtures/hands/.

`info` prints what a tape holds; `shots` renders it offscreen through
the ghost hands over a running scene, a PNG every --every frames;
`synth` writes a tape of the synthetic hands the tests use (no camera);
`styles` renders the five `ghost.style`s side by side from a tape, the
ghost alone on black, at two moments (--at, seconds into the tape).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
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
    rec.add_argument("--cues", help="pose names, comma-separated: each is called in turn, "
                                    "held --hold seconds, and its span kept in the tape")
    rec.add_argument("--hold", type=float, default=3.0, help="seconds a cue is held")
    rec.add_argument("--ready", type=float, default=1.5, help="seconds to get into a pose")
    rec.add_argument("--fps", type=float, help="thin the frames to about this rate "
                                               "(the camera's own is ~120: a fixture that "
                                               "replays in the tests wants ~30)")
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
    st = sub.add_parser("styles", help="the ghost styles side by side, from a tape")
    st.add_argument("path", type=Path)
    st.add_argument("--out", type=Path, default=ROOT / "docs" / "plans" / "assets"
                    / "21-outputs-and-the-hands" / "ghost-styles.png")
    st.add_argument("--at", default="0.3,0.9", help="moments, seconds, comma-separated")
    st.add_argument("--size", default="400x300", help="one cell, px")
    args = ap.parse_args()
    {"record": _record, "info": _info, "shots": _shots, "synth": _synth,
     "styles": _styles}[args.cmd](args)


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
    if args.cues:
        t = _cued(src, [c.strip() for c in args.cues.split(",") if c.strip()], args, mode)
    else:
        print(f"{src.status} — recording {args.seconds:.1f} s in {mode} mode; move both hands",
              file=sys.stderr)
        t = tape.record(src, args.seconds, mode=mode)
    src.close()
    if args.fps:
        t["frames"] = _thinned(t["frames"], args.fps,
                               [c["t0"] for c in t.get("cues", [])])
    tape.save(t, args.path)
    print(f"wrote {args.path}: {_summary(t)}")
    for c in t.get("cues", []):
        print(f"  {c['t0']:6.2f}–{c['t1']:5.2f} s  {c['label']}")


def _thinned(frames: list[dict], fps: float, starts: Iterable[float] = ()) -> list[dict]:
    """Every frame whose time has moved on by 1/`fps` — the camera runs at
    about 120, which no replay needs and a committed fixture should not
    carry.

    `starts` are times that must survive whatever the spacing says: a
    cue's first frame. Thinning across the whole tape could drop it, and
    a tape is replayed by taking the last frame at or before a time
    (`hands.tape.TapeSource`), so a cue's own `t0` then landed on the
    pose before it (review of #449). A kept start also restarts the
    spacing, so no cue is thinned against its neighbour.
    """
    keep = {round(t, 6) for t in starts}
    out: list[dict] = []
    step, last = 1.0 / fps, None
    for f in frames:
        if round(f["t"], 6) in keep or last is None or f["t"] - last >= step - 1e-9:
            out.append(f)
            last = f["t"]
    return out


def _cued(src, cues: list[str], args, mode: str) -> dict:
    """One take a cue, called in turn and spliced into a single tape, each
    cue's span kept in `cues` so a screenshot can find the pose by name."""
    import time

    frames: list[dict] = []
    spans: list[dict] = []
    at = 0.0
    print(f"{src.status} — {len(cues)} poses, {args.hold:.0f} s each; "
          f"hold each one still until the next is called\n", file=sys.stderr)
    for n, label in enumerate(cues, 1):
        for k in range(int(args.ready), 0, -1):
            print(f"\r  next ({n}/{len(cues)}): {label} … {k}  ", end="", file=sys.stderr)
            time.sleep(1.0)
        print(f"\r  NOW ({n}/{len(cues)}): {label}{' ' * 24}", file=sys.stderr)
        one = tape.record(src, args.hold, mode=mode)
        if not one["frames"]:
            print(f"    no frames for {label} — hands in the box?", file=sys.stderr)
            continue
        for f in one["frames"]:
            frames.append({**f, "t": round(at + f["t"], 6)})
        spans.append({"label": label, "t0": round(at, 6), "t1": round(frames[-1]["t"], 6)})
        at = frames[-1]["t"] + 1.0 / 60.0
    print(file=sys.stderr)
    return {"schema": tape.TAPE_SCHEMA, "mode": mode, "frames": frames, "cues": spans}


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
    from hyperspace.graphmigrate import wiring_of
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
    r.wiring = wiring_of(fx)  # plan 33 R23: its run as a load lands it
    r.ghost.state.on, r.ghost.source = True, io
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h))])
    s = ViewState(ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25, faces=True)
    args.out.mkdir(parents=True, exist_ok=True)
    n = int(io.source.length * 60)
    for k in range(n):
        clock.t = k / 60
        io.poll(1 / 60)
        s.integrate(1 / 60)
        s.seed_phases(clock.t)  # K3: the field's and media path's phases at the pinned clock
        fbo.use()
        ctx.viewport = (0, 0, w, h)
        r.draw(s, w, h, t_now=clock.t)
        if k % args.every == 0:
            img = np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1]
            Image.fromarray(img).save(args.out / f"ghost-{k:04d}.png")
    print(f"{n} frames, a shot every {args.every} → {args.out}/")


def _styles(args) -> None:
    """A sheet: a column per style, a row per moment, the ghost alone on
    black at full opacity — what the hands' layer holds, no scene."""
    import moderngl
    import numpy as np
    from PIL import Image, ImageDraw

    from hyperspace import ghost as G
    from hyperspace.hands import HandSettings, HandsIO

    w, h = (int(v) for v in args.size.split("x"))
    moments = [float(v) for v in args.at.split(",")]
    ctx = moderngl.create_context(standalone=True)
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4)])
    pad, head, top = 10, 24, 34
    sheet = Image.new("RGB", (pad + len(G.STYLES) * (w + pad), top + len(moments) * (head + h + pad)),
                      (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    title, small = G._font(17), G._font(14)
    d.text((pad, 8), f"ghost.style — the five styles from the same poses ({args.path.name}, "
           "offscreen, the ghost alone on black)", fill=(225, 225, 230), font=title)
    for row, at in enumerate(moments):
        clock = _Clock()
        io = HandsIO(HandSettings.from_config({}), {"out": "", "tape": str(args.path)},
                     clock=clock)
        gh = G.Ghost(ctx)
        gh.state.on, gh.state.alpha, gh.source = True, 1.0, io
        for k in range(int(at * 60) + 1):           # the tape played up to `at`: fades settle
            clock.t = k / 60
            io.poll(1 / 60)
            gh.layer((w, h), clock.t)
        open_ = {p.side: G.openness(p) for p in (gh.poses(clock.t, w / h) or ([],))[0]}
        for col, name in enumerate(G.STYLES):
            gh.state.style = col
            fbo.use()
            ctx.viewport = (0, 0, w, h)
            ctx.clear(0.0, 0.0, 0.0, 1.0)
            gh.draw(fbo, (0, 0, w, h), clock.t)
            img = np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1]
            x, y = pad + col * (w + pad), top + row * (head + h + pad)
            sides = " · ".join(f"{s} open {o:.2f}" for s, o in sorted(open_.items()))
            d.text((x, y), f"{name}   t {at:.1f} s · {sides}", fill=(240, 200, 120), font=small)
            sheet.paste(Image.fromarray(img.copy()), (x, y + head))
        if gh.error:
            print(f"ghost.error: {gh.error}", file=sys.stderr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"{len(G.STYLES)} styles × {len(moments)} moments → {args.out}")


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


if __name__ == "__main__":
    main()
