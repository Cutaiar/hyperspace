#!/usr/bin/env python3
"""Record golden traces from hyperspace.html (plan 00).

This is the only context in which hyperspace.html is ever executed. It drives
the page in headless Chromium via Playwright and records:

  geometry — for all 18 shapes: the exact constructed vertices/edges and the
             projected screen positions at 3 fixed view configurations.
             Deterministic; recorded twice and required byte-identical.

  audio    — for each test WAV: per-frame {t, AUDIO.inp, AUDIO.out,
             PLANEDRIVE} through the file-playback path. Time-series with
             rAF jitter; recorded twice, the run-to-run delta becomes the
             noise floor written to the manifest (plan 01 tolerances derive
             from it).

  uv run python tools/record_golden.py            # both modes
  uv run python tools/record_golden.py geometry
  uv run python tools/record_golden.py audio
"""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import sys
import threading
import wave
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"
VIEWPORT = {"width": 1200, "height": 800}

# Three view configurations per shape: identity, a generic pose, a second
# generic pose with negative angles. Chosen once, never changed — plan 01
# and plan 02 replay these exact numbers.
VIEWS = [
    {"ang": [0, 0, 0, 0, 0, 0], "yaw": 0.0, "pitch": 0.0},
    {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25},
    {"ang": [2.1, -0.6, 0.9, 3.3, -1.2, 0.4], "yaw": -0.8, "pitch": 0.6},
]

# Audio runs: (clip, run-label, page settings applied after load)
AUDIO_RUNS = [
    ("gate-prover.wav", "default", {}),
    ("brickwalled.wav", "default", {}),
    ("brickwalled.wav", "dyn0", {"dyn": 0.0}),
    ("sweep.wav", "default", {}),
    # user-supplied commercial master; window capped so the trace stays small
    ("real.mp3", "default", {"maxS": 120.0}),
]

RAF_HOOK = """
(() => {
  const orig = window.requestAnimationFrame;
  window.__samples = [];
  window.__tick = null;
  window.requestAnimationFrame = cb => orig(t => {
    cb(t);
    if (window.__tick) window.__tick(t);
  });
})();
"""


def serve(root: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler_quiet = type("H", (handler.func,), {"log_message": lambda *a, **k: None})
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(handler_quiet, directory=str(root))
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, sort_keys=True, separators=(",", ":"))
        f.write("\n")


def new_page(pw, url: str):
    browser = pw.chromium.launch(
        headless=True,
        args=["--autoplay-policy=no-user-gesture-required"],
    )
    page = browser.new_page(viewport=VIEWPORT)
    page.add_init_script(RAF_HOOK)
    page.goto(url)
    page.wait_for_function("typeof SHAPES !== 'undefined' && typeof draw === 'function'")
    return browser, page


# ---------------------------------------------------------------- geometry

def record_geometry(pw, url: str) -> dict:
    browser, page = new_page(pw, url)
    n_shapes = page.evaluate("SHAPES.length")
    shapes = {}
    for i in range(n_shapes):
        views = []
        base = None
        for view in VIEWS:
            data = page.evaluate(
                """([i, view]) => {
                  S.playing = false; S.shape = i;
                  const g = geom(i);
                  for (let p = 0; p < 6; p++) S.ang[p] = view.ang[p];
                  S.yaw = view.yaw; S.pitch = view.pitch;
                  draw();
                  return {
                    name: SHAPES[i].name, cells: SHAPES[i].cells,
                    n: g.n, m: g.m,
                    V: Array.from(g.V), E: Array.from(g.E),
                    px: Array.from(px.subarray(0, g.n)),
                    py: Array.from(py.subarray(0, g.n)),
                    pd: Array.from(pd.subarray(0, g.n)),
                  };
                }""",
                [i, view],
            )
            if base is None:
                base = {k: data[k] for k in ("name", "cells", "n", "m", "V", "E")}
            views.append({**view, "px": data["px"], "py": data["py"], "pd": data["pd"]})
        slug = f"{i:02d}-" + "".join(
            c if c.isalnum() else "-" for c in base["name"].lower()
        ).strip("-")
        shapes[slug] = {"index": i, **base, "viewport": VIEWPORT, "views": views}
    browser.close()
    return shapes


def run_geometry(pw, url: str) -> None:
    a = record_geometry(pw, url)
    b = record_geometry(pw, url)
    if a != b:
        sys.exit("geometry traces differ between runs — determinism bug in the harness")
    for slug, data in a.items():
        dump_json(GOLDEN / "geometry" / f"{slug}.json", data)
    print(f"geometry: {len(a)} shapes, byte-stable across two runs")


# ------------------------------------------------------------------- audio

def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def record_audio_run(pw, url: str, clip: Path, settings: dict) -> tuple[list[list[float]], float]:
    browser, page = new_page(pw, url)
    page.set_input_files("#fileIn", str(clip))
    page.wait_for_function("AUDIO.on === true", timeout=30_000)
    # duration from the decoded buffer, so mp3/m4a work as well as wav
    dur = page.evaluate("TR.buf.duration")
    if "maxS" in settings:
        dur = min(dur, settings["maxS"])
    if "dyn" in settings:
        page.evaluate("d => { AUDIO.dyn = d; }", settings["dyn"])
    page.evaluate(
        """() => {
          window.__samples = [];
          window.__tick = t => {
            if (!AUDIO.on) return;
            window.__samples.push([t, trPos(), ...AUDIO.inp, ...AUDIO.out, ...PLANEDRIVE]);
          };
        }"""
    )
    page.wait_for_timeout(int(dur * 1000) + 500)
    samples = page.evaluate("window.__samples")
    browser.close()
    if len(samples) < dur * 30:
        sys.exit(f"only {len(samples)} frames for {clip.name} — page was not running at speed")
    cutoff = samples[0][0] + dur * 1000
    kept = []
    for row in samples:
        if row[0] > cutoff:
            break
        if kept and row[1] < kept[-1][1] - 0.5:
            break  # transport looped — keep the monotonic first pass only
        kept.append(row)
    return kept, dur


def resample(samples: list[list[float]], t_lo: float, t_hi: float, hz: float = 60.0) -> np.ndarray:
    """Interpolate the 18 channels onto a fixed music-time grid (trPos axis).

    Aligning on transport position rather than wall time is what lets two
    runs compare — the sampler starts a variable beat after playback does.
    """
    arr = np.asarray(samples)
    pos = arr[:, 1]
    grid = np.arange(t_lo, t_hi, 1.0 / hz)
    return np.stack([np.interp(grid, pos, arr[:, c]) for c in range(2, arr.shape[1])], axis=1)


def noise_floor(a: list[list[float]], b: list[list[float]]) -> float:
    """RMS delta of AUDIO.out between two runs on the shared music-time span.

    The first 2 s are excluded: the adaptive trackers spend ~1 s settling
    from seeds (ENGINEERING §4, WARM_F) and that transient differs between
    runs by construction. Plan-01 comparisons treat warm-up the same way.
    """
    lo = max(2.0, a[0][1], b[0][1])
    hi = min(a[-1][1], b[-1][1])
    ra, rb = resample(a, lo, hi), resample(b, lo, hi)
    return float(np.sqrt(np.mean((ra[:, 6:12] - rb[:, 6:12]) ** 2)))


def run_audio(pw, url: str) -> None:
    manifest = {"sampleChannels": "t, pos, inp[6], out[6], planedrive[6]", "clips": {}}
    for name, label, settings in AUDIO_RUNS:
        clip = FIXTURES / name
        if not clip.exists():
            print(f"audio: {name} not present — skipped (manifest notes it)")
            manifest["clips"][f"{name}:{label}"] = {"status": "missing"}
            continue
        a, dur = record_audio_run(pw, url, clip, settings)
        b, _ = record_audio_run(pw, url, clip, settings)
        nf = noise_floor(a, b)
        out = GOLDEN / "audio" / f"{Path(name).stem}-{label}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.writelines(json.dumps([round(x, 6) for x in row]) + "\n" for row in a)
        manifest["clips"][f"{name}:{label}"] = {
            "status": "recorded",
            "file": out.name,
            "sha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
            "durationS": round(dur, 3),
            "settings": settings,
            "frames": len(a),
            "noiseFloorRms": round(nf, 6),
        }
        status = "OK" if nf < 0.05 else "TOO NOISY"
        print(f"audio: {name} [{label}] {len(a)} frames, noise floor {nf:.4f} {status}")
        if nf >= 0.05:
            sys.exit("noise floor over 0.05 — fix harness timing before trusting traces")
    dump_json(GOLDEN / "audio" / "manifest.json", manifest)


def main() -> None:
    modes = sys.argv[1:] or ["geometry", "audio"]
    srv, port = serve(ROOT)
    url = f"http://127.0.0.1:{port}/hyperspace.html"
    try:
        with sync_playwright() as pw:
            if "geometry" in modes:
                run_geometry(pw, url)
            if "audio" in modes:
                run_audio(pw, url)
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
