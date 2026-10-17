#!/usr/bin/env python3
"""Plan 28 — the sticks as dials, played by a scripted pad and recorded.

SYNTHETIC PAD, REAL APP: the whole app runs in-process (`app.main`, as
tools/control_shots.py does) with the DIAL preset loaded, and the gamepad
is a `gamepad.Pad` whose sticks follow a script instead of hardware —
every other piece is the app's own: `Pad.lanes` → `Router.pad` → the
claims → `Router.modulate` → the registry → the renderer and the fx
stack → the SYSTEM page's dial faces. The clock is simulated (1/FPS a
frame), so effect speeds in the video are true to time however slowly
the frames render; the wall time each frame took is recorded beside it.

    HYPERSPACE_HOME=$(mktemp -d) xvfb-run -a -s "-screen 0 2400x1200x24" \\
        uv run python tools/dial_demo.py [--out DIR] [--scale 0.5]

Writes, under --out (default docs/plans/assets/28-gamepad-dial/):
  dial-trace.csv     a row per frame: phase, both sticks, each stick's
                     reading and sector, the camera and W-rate params the
                     sticks drive when free (WATCH), the 16 dial lanes and
                     the 16 routed params' effective values (0..1 of
                     their throw)
  dial-traces.png    the lanes and their params over the whole script
  dial-borders.png   petal against blend with the stick shaking on a border
  dial-sheet.png     a contact sheet: scene + both faces at the script's beats
  dial-timing.txt    what the dial costs per frame (micro-benchmark) and
                     how long the app's frames took here (software GL)
  dial.mp4           every frame composited (scene | faces) at FPS, if
                     ffmpeg is on the path (--frames DIR keeps the PNGs)

What it shows: the dial's numbers and what they do to a frame. What it
cannot show: how a real stick feels in the hand (plan 28's "to try").
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import glfw
import numpy as np
from OpenGL import GL
from PIL import Image, ImageDraw, ImageFont

from hyperspace import app, gamepad, render, ui
from hyperspace.ui import PAGE_KEYS

FPS = 30
R_SWEEP = 0.95
# what the sticks drive while no route claims them (app.py): none may move
WATCH = ("camera.yaw", "camera.pitch", "camera.zoom", "rot.rate.XW", "rot.rate.YW",
         "rot.rate.ZW")


# ---- the script: (seconds, phase name, stick fn of local t in [0, 1], swap at start) ----

def _polar(deg: float, r: float) -> tuple[float, float]:
    t = math.radians(deg)
    return r * math.sin(t), r * math.cos(t)


def _rest(_):
    return (0.0, 0.0), (0.0, 0.0)


def _push_up(u):         # out to the rim over 60 %, hold, back over the last 20 %
    r = min(u / 0.6, 1.0) if u < 0.8 else max(0.0, (1.0 - u) / 0.2)
    return _polar(0, r), (0.0, 0.0)


def _sweep(stick):
    def fn(u):
        p = _polar(360 * u, R_SWEEP)
        return (p, (0.0, 0.0)) if stick == "L" else ((0.0, 0.0), p)
    return fn


def _border(stick):      # shaking ±4° about the N | NE border, 3 Hz
    def fn(u):
        p = _polar(22.5 + 4 * math.sin(2 * math.pi * 3 * u * 2.0), 0.9)
        return (p, (0.0, 0.0)) if stick == "L" else ((0.0, 0.0), p)
    return fn


def _release(_):
    return (0.0, 0.0), (0.0, 0.0)


SCRIPT = [
    (1.0, "rest", _rest, False),
    (2.5, "left: push up and let go", _push_up, False),
    (8.0, "left petal: round the rim", _sweep("L"), False),
    (0.5, "release", _release, False),
    (2.0, "left petal: shaking on a border", _border("L"), False),
    (0.5, "release", _release, False),
    (8.0, "right blend: round the rim", _sweep("R"), False),
    (2.0, "right blend: shaking on a border", _border("R"), False),
    (0.5, "release", _release, False),
    (8.0, "swapped — left blend: round the rim", _sweep("L"), True),
    (2.0, "left blend: shaking on a border", _border("L"), False),
    (1.0, "rest", _rest, False),
]
STARTS = np.cumsum([0.0] + [s for s, *_ in SCRIPT])
TOTAL = int(STARTS[-1] * FPS)
WARM = 20                # frames before the script: the preset lands, imgui settles


def at_frame(n: int):
    """(phase index, phase name, (left xy, right xy), swap now) at frame n."""
    t = max(0, n - WARM) / FPS
    k = min(int(np.searchsorted(STARTS, t, side="right")) - 1, len(SCRIPT) - 1)
    secs, name, fn, swap = SCRIPT[k]
    u = min(max((t - STARTS[k]) / secs, 0.0), 1.0)
    first = n >= WARM and round(STARTS[k] * FPS) == n - WARM
    return k, name, fn(u), swap and first


# ---- the pad, the clock and the capture ----

state = SimpleNamespace(n=0, rows=[], panel=None, router=None, phase="", grab={},
                        wall=time.perf_counter(), walls=[], loaded=False)


class ScriptedPad(gamepad.Pad):
    """A connected pad whose sticks follow SCRIPT, no button ever down."""

    def poll(self) -> None:
        _, _, (left, right), _ = at_frame(state.n)
        self.source, self.jid = "glfw", 0
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons, self.hat = [0] * gamepad.N_BUTTONS, 0
        self.axes = [left[0], -left[1], right[0], -right[1], -1.0, -1.0]


class SimClock:
    """`time` for app.py and render.py: perf_counter is frame n / FPS."""

    def __getattr__(self, name):
        return getattr(time, name)

    @staticmethod
    def perf_counter() -> float:
        return state.n / FPS


_draw = ui.Panel.draw
_swap = glfw.swap_buffers


def draw(self, dt, fps):
    state.panel = self
    self.reg["ui.page"].set(PAGE_KEYS.index("system"))
    if not state.loaded and self.library is not None:
        self.library.presets.load("DIAL")
        state.loaded = True
    k, name, _, swap = at_frame(state.n)
    if swap:
        self.reg["desk.pad.dial.swap"].fire()
    state.phase = name
    try:
        _draw(self, dt, fps)
    except Exception:  # noqa: BLE001 — surface it; the loop would swallow it
        traceback.print_exc()
        raise SystemExit(1) from None
    if state.n >= WARM:
        record(self, k, name)


def record(panel, k: int, name: str) -> None:
    pad, router = panel.pad, panel.router
    routes = {b.source: b.target for b in router.table.mods()
              if b.enabled and b.scheme == "axis"}
    lanes = pad.dials()
    row = {"frame": state.n - WARM, "t": round((state.n - WARM) / FPS, 4), "phase": name,
           "lx": pad.axes[0], "ly": -pad.axes[1], "rx": pad.axes[2], "ry": -pad.axes[3],
           "mode_L": pad.dial_modes["L"], "mode_R": pad.dial_modes["R"],
           "sector_L": pad.dial_sectors["L"], "sector_R": pad.dial_sectors["R"]}
    for pid in WATCH:                   # the camera job: a dialed stick must not move it
        row[pid] = round(float(panel.reg[pid].value), 6)
    for lane_name, v in zip(gamepad.DIAL_LANES, lanes, strict=True):
        row[f"lane {lane_name}"] = round(v, 5)
        pid = routes.get(f"axis:{lane_name}")
        row[f"param {lane_name}"] = (round(panel.reg[pid].eff_norm, 5)
                                     if pid in panel.reg else "")
    state.rows.append(row)
    state.targets = {n: routes.get(f"axis:{n}") for n in gamepad.DIAL_LANES}
    state.labels = {n: panel.reg[p].label if p in panel.reg else "" for n, p in state.targets.items()}


def swap_buffers(win):
    """Read the back buffer of the window about to swap: the render window
    gives the scene, the control window the panel."""
    if state.n >= WARM and state.n < WARM + TOTAL:
        cur = glfw.get_current_context()
        glfw.make_context_current(win)
        w, h = glfw.get_framebuffer_size(win)
        GL.glReadBuffer(GL.GL_BACK)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        state.grab[glfw.get_window_title(win) or str(id(win))] = (
            np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1].copy())
        if cur is not None:
            glfw.make_context_current(cur)
    _swap(win)
    if state.panel is not None and win == getattr(state, "ctrl_win", None):
        end_frame()


def end_frame():
    now = time.perf_counter()
    if state.n >= WARM:
        state.walls.append(now - state.wall)
        if state.n < WARM + TOTAL:
            compose(state.n - WARM)
    state.wall = now
    state.n += 1


# ---- the pictures ----

def _font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def compose(i: int) -> None:
    grabs = state.grab
    scene = grabs.get(state.render_title)
    panel = grabs.get(state.ctrl_title)
    if scene is None or panel is None:
        return
    x0, y0, x1, y1 = state.face_box
    faces = Image.fromarray(panel[y0:y1, x0:x1])
    sc = Image.fromarray(scene)
    hh = 540
    sc = sc.resize((int(sc.width * hh / sc.height), hh), Image.LANCZOS)
    fw = int(faces.width * (hh - 60) / faces.height)
    faces = faces.resize((fw, hh - 60), Image.LANCZOS)
    out = Image.new("RGB", (sc.width + fw, hh), (0, 0, 0))
    out.paste(sc, (0, 0))
    out.paste(faces, (sc.width, 60))
    d = ImageDraw.Draw(out)
    d.text((sc.width + 12, 10), state.phase, fill=(240, 240, 240), font=_font(20))
    d.text((sc.width + 12, 36), f"t {i / FPS:5.2f} s", fill=(150, 150, 155), font=_font(15))
    state.frames_dir.mkdir(parents=True, exist_ok=True)
    out.save(state.frames_dir / f"{i:05d}.png")


def find_face_box(panel_px: np.ndarray, ui_scale: float) -> tuple[int, int, int, int]:
    """Where `Panel._dials` drew: its canvas's top-left is caught on the
    first draw (`state.dial_origin`), in imgui units scaled to pixels."""
    ox, oy, w, h = state.dial_rect
    s = ui_scale
    return (max(0, int(ox * s) - 4), max(0, int(oy * s) - 4),
            min(panel_px.shape[1], int((ox + w) * s) + 4),
            min(panel_px.shape[0], int((oy + h) * s) + 12))


def plots(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = state.rows
    t = np.array([r["t"] for r in rows])
    colors = plt.cm.tab10(np.arange(8))
    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True)
    for ax, stick, kind in ((axes[0], "L", "lane"), (axes[1], "L", "param"),
                            (axes[2], "R", "lane"), (axes[3], "R", "param")):
        for j, c in enumerate(gamepad.COMPASS):
            col = f"{kind} {stick}.{c}"
            ys = [r[col] if r[col] != "" else np.nan for r in rows]
            lab = f"{c} · {state.labels[f'{stick}.{c}']}"
            ax.plot(t, ys, color=colors[j], lw=1.4, label=lab)
        side = "left" if stick == "L" else "right"
        ax.set_ylabel(f"{side}\n{'dial lane' if kind == 'lane' else 'param (0..1 of throw)'}")
        ax.set_ylim(-0.03, 1.03)
        if kind == "lane":
            ax.legend(loc="upper left", ncol=4, fontsize=8, framealpha=0.85)
    for ax in axes:
        for s0, (secs, name, *_) in zip(STARTS[:-1], SCRIPT, strict=True):
            ax.axvline(s0, color="0.85", lw=0.8, zorder=0)
    named = [(s0, name) for s0, (secs, name, *_) in zip(STARTS[:-1], SCRIPT, strict=True)
             if secs >= 2.0]
    for j, (s0, name) in enumerate(named):
        axes[0].text(s0 + 0.1, 1.04 + 0.09 * (j % 2), name, fontsize=7.5, va="bottom",
                     transform=axes[0].get_xaxis_transform())
    axes[-1].set_xlabel("seconds")
    fig.suptitle("DIAL preset, scripted sticks: each lane and the param it pushes", y=0.998)
    fig.tight_layout()
    fig.savefig(out / "dial-traces.png", dpi=110)
    plt.close(fig)

    # the border shake: petal (left) against blend (right, then left swapped)
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.6), sharey=True)
    picks = [("left petal: shaking on a border", "L"), ("right blend: shaking on a border", "R"),
             ("left blend: shaking on a border", "L")]
    for ax, (phase, stick) in zip(axes, picks, strict=True):
        sub = [r for r in rows if r["phase"] == phase]
        tt = np.array([r["t"] for r in sub]) - sub[0]["t"]
        for j, c in ((0, "N"), (1, "NE")):
            ax.plot(tt, [r[f"lane {stick}.{c}"] for r in sub], color=colors[j], lw=1.6,
                    label=f"{c} lane")
        ang = [math.degrees(math.atan2(r[f"{stick.lower()}x"], r[f"{stick.lower()}y"]))
               for r in sub]
        a2 = ax.twinx()
        a2.plot(tt, ang, color="0.6", lw=0.8, ls="--")
        a2.axhline(22.5, color="0.8", lw=0.6)
        a2.set_ylim(10, 35)
        a2.set_ylabel("stick angle °", fontsize=8)
        flips = sum(1 for a, b in itertools.pairwise(sub)
                    if a[f"sector_{stick}"] != b[f"sector_{stick}"])
        ax.set_title(f"{phase}\n(sector changes: {flips})", fontsize=9)
        ax.set_xlabel("seconds")
        ax.legend(fontsize=8, loc="lower left")
    axes[0].set_ylabel("lane")
    fig.tight_layout()
    fig.savefig(out / "dial-borders.png", dpi=110)
    plt.close(fig)


def sheet(out: Path) -> None:
    """Every phase's middle frame, two to a row."""
    picks = []
    for s0, (secs, name, *_) in zip(STARTS[:-1], SCRIPT, strict=True):
        if name in ("release", "rest"):
            continue
        for frac in ((0.125, 0.375, 0.625, 0.875) if "rim" in name else (0.5,)):
            picks.append((int((s0 + secs * frac) * FPS), name))
    ims = [(Image.open(state.frames_dir / f"{i:05d}.png"), name) for i, name in picks
           if (state.frames_dir / f"{i:05d}.png").exists()]
    if not ims:
        return
    w, h = ims[0][0].size
    w2, h2 = w // 2, h // 2
    cols = 2
    rows = (len(ims) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * w2, rows * h2), (0, 0, 0))
    for k, (im, _) in enumerate(ims):
        canvas.paste(im.resize((w2, h2), Image.LANCZOS), ((k % cols) * w2, (k // cols) * h2))
    canvas.save(out / "dial-sheet.png", optimize=True)


def timing(out: Path) -> None:
    pad = gamepad.Pad()
    pad.source = "glfw"
    n = 20000
    t0 = time.perf_counter()
    for i in range(n):
        a = 2 * math.pi * i / 997
        pad.axes = [math.sin(a), -math.cos(a), math.cos(a), math.sin(a), -1.0, -1.0]
        pad.lanes()
    per = (time.perf_counter() - t0) / n
    walls = np.array(state.walls[1:]) * 1000
    lines = [
        "the dial's own cost (Pad.lanes with both sticks moving, every call recomputes):",
        (f"  {per * 1e6:.1f} µs per frame on this machine — "
         f"{per * 1e3 / (1000 / 60) * 100:.2f} % of a 60 Hz frame"),
        "",
        "the app's frames during the recording (Xvfb + llvmpipe software GL, so this",
        "is the CPU rasterizer, not the Mac's GPU — the dial's share is the line above):",
        (f"  {len(walls)} frames, median {np.median(walls):.0f} ms, p95 "
         f"{np.percentile(walls, 95):.0f} ms"),
    ]
    moved = {pid: max(abs(r[pid] - state.rows[0][pid]) for r in state.rows) for pid in WATCH}
    lines += ["", "the sticks' camera job while both sticks are dials (largest move from the",
              "first frame; 0 means the routes claimed the sticks):"]
    lines += [f"  {pid:<14} {d:.6f}" for pid, d in moved.items()]
    (out / "dial-timing.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---- the app ----

_dials = ui.Panel._dials


def dials(self):
    """The faces' canvas, caught where `Panel._dials` puts it."""
    from imgui_bundle import imgui
    p = imgui.get_cursor_screen_pos()
    w = imgui.get_content_region_avail().x
    h = 2 * max(2 * self.DIAL_R + 8, (gamepad.DIAL + 1) * self.DIAL_ROW + 4)
    state.dial_rect = (p.x, p.y, w, h)
    _dials(self)


_open_pad = app._open_pad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "plans" / "assets" / "28-gamepad-dial")
    ap.add_argument("--frames", default="", help="keep the composited frames here")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many frames (a probe)")
    a = ap.parse_args()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    import tempfile
    state.frames_dir = Path(a.frames) if a.frames else Path(tempfile.mkdtemp(prefix="dial-"))
    if state.frames_dir.exists():
        shutil.rmtree(state.frames_dir)

    home = Path(os.environ.get("HYPERSPACE_HOME", ""))
    if not home or not home.is_dir():
        raise SystemExit("set HYPERSPACE_HOME to a throwaway folder")
    (home / "config.toml").write_text(
        '[output]\nrender = "720p"\n[dream]\nenabled = false\n[hands]\nenabled = false\n'
        '[midi]\nenabled = false\n[gamepad]\nusb = false\n')

    ui.Panel.draw = draw
    ui.Panel._dials = dials
    app.time = SimClock()
    render.time = SimClock()
    app._open_pad = lambda cfg: _swap_in(_open_pad(cfg))

    _windows = app._windows

    def windows(*args, **kw):
        slots, ctrl = _windows(*args, **kw)
        state.ctrl_win, state.render_win = ctrl, slots[0].win
        state.ctrl_title = glfw.get_window_title(ctrl) or str(id(ctrl))
        state.render_title = glfw.get_window_title(slots[0].win) or str(id(slots[0].win))
        return slots, ctrl
    app._windows = windows
    glfw.swap_buffers = swap_buffers

    _compose = compose

    def compose_first(i):
        if not hasattr(state, "face_box"):
            panel = state.grab.get(state.ctrl_title)
            fb_w = panel.shape[1]
            win_w, _ = glfw.get_window_size(state.ctrl_win)
            state.face_box = find_face_box(panel, fb_w / win_w)
        _compose(i)
    globals()["compose"] = compose_first

    os.environ["HYPERSPACE_FRAMES"] = str(WARM + (a.limit or TOTAL) + 2)
    app.main()
    if a.limit:
        for name, px in state.grab.items():
            Image.fromarray(px).save(out / f"probe-{name.replace('/', '_')}.png")
        print(f"probe: {len(state.rows)} rows, grabs {list(state.grab)}, faces {state.face_box}")
        return

    with open(out / "dial-trace.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(state.rows[0]))
        wr.writeheader()
        wr.writerows(state.rows)
    plots(out)
    sheet(out)
    timing(out)
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", str(state.frames_dir / "%05d.png"), "-vf",
                        "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt",
                        "yuv420p", "-crf", "26", str(out / "dial.mp4")], check=True)
    if not a.frames:
        shutil.rmtree(state.frames_dir, ignore_errors=True)
    print(f"wrote {out}")


def _swap_in(pad):
    """The app's pad, made a ScriptedPad with the modes the config gave it."""
    if pad is None:
        return None
    sp = ScriptedPad()
    sp.dial_modes = dict(pad.dial_modes)
    return sp


if __name__ == "__main__":
    main()
