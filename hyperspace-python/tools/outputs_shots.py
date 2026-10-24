#!/usr/bin/env python3
"""Plan 21's compose path, offscreen: one frame shown on several outputs.

Every picture is drawn by `Renderer.draw_outputs` (render.py) onto
offscreen framebuffers standing in for the windows, with two synthetic
ghost hands (tests/test_ghost.py's open hand and fist — no tracker) over
a 24-cell with face patterns and effects on. No window, screen, glass or
projector is involved: the sheets show what the renderer writes into
each output's framebuffer, not how it looks on the rig.

    uv run python tools/outputs_shots.py compose   # WP1: outputs-compose.png
    uv run python tools/outputs_shots.py eight     # WP2: eight-states.png
    uv run python tools/outputs_shots.py through   # WP2: through-two-outputs.png
    uv run python tools/outputs_shots.py timing    # WP2: compose-timing.txt
    uv run python tools/outputs_shots.py style     # WP6: style-through.png

writes into docs/plans/assets/21-outputs-and-the-hands/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import moderngl
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fake_hands import hand  # tests/fake_hands.py

from hyperspace import outputs as O
from hyperspace.fx import FxState
from hyperspace.ghost import _font
from hyperspace.graphmigrate import wiring_of
from hyperspace.hands import skeleton
from hyperspace.render import Renderer
from hyperspace.view import ViewState

OUT = ROOT / "docs" / "plans" / "assets" / "21-outputs-and-the-hands"
FW, FH = 640, 400            # the frame: the first output's size
BG = (18, 18, 22)
INK = (225, 225, 230)
DIM_INK = (150, 150, 160)


def hands(guide: bool = False) -> NS:
    """Two synthetic hands, as tests/test_ghost.py feeds the ghost; with
    `guide`, the axes a guide reads (a HandsIO with no camera)."""
    sk = {"left": skeleton(hand("left", "open", (-90.0, 210.0, 0.0))),
          "right": skeleton(hand("right", "fist", (90.0, 200.0, 10.0)))}
    if not guide:
        return NS(skeleton=sk, cfg={"mode": "desktop"})
    from hyperspace.hands import HandSettings, HandsIO

    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=lambda m: None))
    for st in io.state:
        st.follow.y = 0.7
    return NS(skeleton=sk, cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
              gates=io.gates)


def renderer(ctx, effects=("warp",), guide=0, **values) -> Renderer:
    fx = FxState()
    for n in effects:
        fx.values[n]["on"] = True
        fx.values[n].update(values.get(n, {}))
    r = Renderer(ctx, fx=fx)
    r.wiring = wiring_of(fx)  # plan 33 R23: its run as a load lands it
    r.ghost.state.on, r.ghost.state.alpha, r.ghost.state.guide = True, 1.0, guide
    r.ghost.source = hands(guide=bool(guide))
    return r


def view_state() -> ViewState:
    return ViewState(shape=10, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25,
                     faces=True, pattern=2)


def target(ctx, size):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer(size, 4)])


def pixels(f) -> Image.Image:
    w, h = f.size
    a = np.frombuffer(f.read(components=3), dtype=np.uint8).reshape(h, w, 3)[::-1]
    return Image.fromarray(a.copy())


def frames(ctx, r, views, n=12, t0=2.0):
    """`n` frames at 30 fps (the hands fade in, the effects move)."""
    s = view_state()
    for k in range(n):
        s.ang = [a + 0.01 for a in s.ang]
        r.draw_outputs(s, FW, FH, 1.0, views, t_now=t0 + k / 30)


def stats_line(r) -> str:
    st = r.stats
    names = ", ".join(O.NAMES[k] for k in st["pipelines"]) or "none"
    return (f"Renderer.stats: pipelines [{names}] · chain runs {st['chain_runs']} · "
            f"direct {st['direct']} · captures {st['captures']} · hands' layer {st['layer']}")


def compose(ctx) -> Path:
    """Three switch combinations, each on two outputs at once: the glass
    (the frame's size) and a square projector, letterboxed and at 60%."""
    S = O.Switches
    rows = [("scene + hands", S()), ("scene only", S(hands=False)),
            ("hands only", S(scene=False))]
    side = 400
    pad, head, foot = 16, 30, 26
    title = _font(18)
    small = _font(14)
    width = pad + FW + pad + side + pad
    height = pad + 34 + len(rows) * (head + max(FH, side) + foot + pad)
    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, pad), "Plan 21 WP1 — one frame, two outputs, three switch states "
           "(offscreen, synthetic hands, warp on)", fill=INK, font=title)
    y = pad + 34
    for label, sw in rows:
        r = renderer(ctx)
        glass = O.View(sw, (FW, FH), target=target(ctx, (FW, FH)))
        proj = O.View(O.Switches(scene=sw.scene, hands=sw.hands, dim=0.6), (side, side),
                      target=target(ctx, (side, side)))
        frames(ctx, r, [glass, proj])
        d.text((pad, y), f"{label}:  output 1 'glass' {FW}×{FH}", fill=INK, font=small)
        _, y0, w0, h0 = O.fit((FW, FH), (side, side))
        d.text((pad + FW + pad, y), f"output 2 {side}×{side} · frame in {w0}×{h0} at y {y0}"
               f" · own dim 60%", fill=INK, font=small)
        y += head
        sheet.paste(pixels(glass.target), (pad, y))
        sheet.paste(pixels(proj.target), (pad + FW + pad, y))
        d.rectangle((pad + FW + pad - 1, y - 1, pad + FW + pad + side, y + side),
                    outline=(70, 70, 80))
        y += max(FH, side) + 4
        d.text((pad, y), stats_line(r), fill=DIM_INK, font=small)
        y += foot + pad
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "outputs-compose.png"
    sheet.save(path)
    return path


EIGHT = [O.Switches(scene=a, hands=b, through=c)
         for a in (True, False) for b in (True, False) for c in (False, True)]


def _state_label(k: int, sw: O.Switches) -> str:
    return (f"{k}  scene {'on' if sw.scene else 'off'} · hands {'on' if sw.hands else 'off'}"
            f" · {'through' if sw.through else 'over'} effects")


def eight(ctx) -> Path:
    """One output's eight switch states, drawn as eight outputs of one
    frame by draw_outputs (warp + kaleido on)."""
    tw, th = FW * 3 // 4, FH * 3 // 4
    pad, head = 10, 24
    small, title = _font(14), _font(17)
    r = renderer(ctx, effects=("warp", "kaleido"))
    views = [O.View(sw, (FW, FH), target=target(ctx, (FW, FH))) for sw in EIGHT]
    frames(ctx, r, views)
    sheet = Image.new("RGB", (pad + 4 * (tw + pad), 34 + 2 * (head + th + pad) + 28), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), "Plan 21 WP2 — one output's eight switch states, from the merged "
           "draw_outputs (offscreen, synthetic hands, warp + kaleido)", fill=INK, font=title)
    for k, v in enumerate(views):
        x, y = pad + (k % 4) * (tw + pad), 34 + (k // 4) * (head + th + pad)
        d.text((x, y), _state_label(k + 1, v.switches), fill=(240, 200, 120), font=small)
        sheet.paste(pixels(v.target).resize((tw, th), Image.LANCZOS), (x, y + head))
    d.text((pad, sheet.height - 24), stats_line(r) + " · 3 = 4 and 7 = 8 byte for byte",
           fill=DIM_INK, font=small)
    path = OUT / "eight-states.png"
    sheet.save(path)
    return path


def through(ctx) -> Path:
    """The glass with the hands over the effects beside the projector with
    them through, guide on (beside each hand: never bent, fork F3)."""
    pad, head = 14, 26
    small, title = _font(14), _font(17)
    r = renderer(ctx, effects=("warp", "kaleido"), guide=1)
    glass = O.View(O.Switches(), (FW, FH), target=target(ctx, (FW, FH)))
    proj = O.View(O.Switches(through=True), (FW, FH), target=target(ctx, (FW, FH)))
    frames(ctx, r, [glass, proj])
    sheet = Image.new("RGB", (pad + 2 * (FW + pad), 34 + head + FH + 40), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), "Plan 21 WP2 — glass: hands over the effects · projector: hands through "
           "them (offscreen, synthetic hands, warp + kaleido, guide beside)", fill=INK,
           font=title)
    for k, (v, lab) in enumerate(((glass, "output 1 'glass' — hands over the effects"),
                                  (proj, "output 2 'projector' — hands through the effects"))):
        x = pad + k * (FW + pad)
        d.text((x, 34), lab, fill=(240, 200, 120), font=small)
        sheet.paste(pixels(v.target), (x, 34 + head))
    d.text((pad, 34 + head + FH + 10), stats_line(r) + f" · readout layer {r.stats['readout']}",
           fill=DIM_INK, font=small)
    path = OUT / "through-two-outputs.png"
    sheet.save(path)
    return path


def style(ctx, name: str = "CAGE") -> Path:
    """WP6: one style with the guide beside each hand and the tethers on,
    over the effects on one output and through them on the other — the
    style bends with the shape, the guide and its labels do not."""
    import tempfile

    from test_ghost import _routed_rig

    from hyperspace import ghost as G

    pad, head = 14, 26
    small, title = _font(14), _font(17)
    router, io = _routed_rig(Path(tempfile.mkdtemp()),
                             ["hand:left.x", "hand:left.roll", "hand:right.y", "hand:right.pitch"])
    for st in io.state:
        st.follow.y = 0.65
    r = renderer(ctx, effects=("warp", "kaleido"), guide=1)
    sk = r.ghost.source.skeleton
    r.ghost.source = NS(skeleton=sk, cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
                        gates=io.gates, layout=io.layout, frame=io.frame)
    r.ghost.router = router
    r.ghost.state.tethers = True
    r.ghost.state.style = G.STYLES.index(name)
    glass = O.View(O.Switches(), (FW, FH), target=target(ctx, (FW, FH)))
    proj = O.View(O.Switches(through=True), (FW, FH), target=target(ctx, (FW, FH)))
    frames(ctx, r, [glass, proj])
    sheet = Image.new("RGB", (pad + 2 * (FW + pad), 34 + head + FH + 40), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), f"Plan 21 WP6 — ghost.style {name}, guide beside each hand, tethers on "
           "(offscreen, synthetic hands, warp + kaleido)", fill=INK, font=title)
    for k, (v, lab) in enumerate(((glass, f"{name} over the effects"),
                                  (proj, f"{name} through the effects — guide and labels unbent"))):
        x = pad + k * (FW + pad)
        d.text((x, 34), lab, fill=(240, 200, 120), font=small)
        sheet.paste(pixels(v.target), (x, 34 + head))
    d.text((pad, 34 + head + FH + 10), stats_line(r) + f" · readout layer {r.stats['readout']}"
           + f" · ghost.error {r.ghost.error!r}", fill=DIM_INK, font=small)
    path = OUT / "style-through.png"
    sheet.save(path)
    return path


def timing(ctx, n: int = 120) -> Path:
    """Frame time at 1920×1080 (the first output 4× MSAA, as the window
    is): one default view, two that agree, two that disagree (hands over
    vs through). Median and 90th percentile of `n` frames, each ended by
    ctx.finish(), after 20 warm-up frames."""
    import platform
    import statistics
    import subprocess
    import time

    size = (1920, 1080)

    def fb(samples):
        return ctx.framebuffer(color_attachments=[ctx.renderbuffer(size, 4, samples=samples)])

    cases = [
        ("one view, default (Renderer.draw's path)", [O.Switches()]),
        ("two views agreeing (scene + hands over)", [O.Switches(), O.Switches()]),
        ("two views disagreeing (hands over | hands through)",
         [O.Switches(), O.Switches(through=True)]),
    ]
    try:
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                              text=True, check=False).stdout.strip()
    except OSError:
        chip = platform.processor()
    lines = [f"Plan 21 WP2 — compose timing, {size[0]}×{size[1]}, {chip}, GL renderer "
             + ctx.info["GL_RENDERER"],
             ("standalone context, offscreen targets (first 4x MSAA, others single-sampled), "
              "warp + kaleido on, two synthetic hands; ms per frame, each frame ended by "
              f"glFinish; {n} frames after 20 warm-up"), ""]
    for label, sws in cases:
        r = renderer(ctx, effects=("warp", "kaleido"))
        views = [O.View(sw, size, target=fb(4 if k == 0 else 0)) for k, sw in enumerate(sws)]
        s = view_state()
        times = []
        for k in range(n + 20):
            s.ang = [a + 0.01 for a in s.ang]
            t0 = time.perf_counter()
            r.draw_outputs(s, 1920, 1080, 1.0, views, t_now=2.0 + k / 60)
            ctx.finish()
            if k >= 20:
                times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        lines.append(f"{label:52s} median {statistics.median(times):6.2f} ms · "
                     f"p90 {times[int(0.9 * len(times))]:6.2f} ms · chain runs "
                     f"{r.stats['chain_runs']} · pipelines {[O.NAMES[p] for p in r.stats['pipelines']]}")
    path = OUT / "compose-timing.txt"
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=["compose", "eight", "through", "timing", "style", "all"])
    args = ap.parse_args()
    ctx = moderngl.create_context(standalone=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("compose", compose), ("eight", eight), ("through", through),
                     ("timing", timing), ("style", style)):
        if args.what in (name, "all"):
            print(fn(ctx))


if __name__ == "__main__":
    main()
