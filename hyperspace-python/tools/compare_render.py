#!/usr/bin/env python3
"""Side-by-side comparison shots: HTML reference vs Python renderer (plan 02).

For each judge shape, renders the same view state through both pipelines at
1200×800 and writes a labelled side-by-side PNG into docs/plans/assets/.
The user judges these by eye — that is the plan-02 exit bar.

  uv run python tools/compare_render.py
"""

from __future__ import annotations

import functools
import http.server
import io
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

from hyperspace.render import render_offscreen
from hyperspace.view import ViewState

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = ROOT.parent / "hyperspace-web"
ASSETS = ROOT / "docs" / "plans" / "assets"
GOLDEN = ROOT / "tests" / "golden" / "geometry"
W, H = 1200, 800

# The four judge shapes from the plan, by slug.
JUDGES = ["00-5-cell", "03-tesseract", "15-120-cell", "17-clifford-torus"]
VIEW_INDEX = 1  # the generic pose


def serve(root: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    quiet = type("H", (handler.func,), {"log_message": lambda *a, **k: None})
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(quiet, directory=str(root))
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def html_shot(page, index: int, view: dict) -> Image.Image:
    page.evaluate(
        """([i, view]) => {
          S.playing = false; S.shape = i;
          for (let p = 0; p < 6; p++) S.ang[p] = view.ang[p];
          S.yaw = view.yaw; S.pitch = view.pitch;
          draw();
        }""",
        [index, view],
    )
    return Image.open(io.BytesIO(page.locator("#c").screenshot()))


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    srv, port = serve(WEB_ROOT)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": W, "height": H})
            page.goto(f"http://127.0.0.1:{port}/hyperspace.html")
            page.wait_for_function("typeof draw === 'function'")
            # hide every DOM overlay so the shot is the canvas alone
            page.evaluate(
                """for (const id of ['readout', 'console', 'keys'])
                     document.getElementById(id).style.display = 'none';"""
            )

            for slug in JUDGES:
                ref = json.loads((GOLDEN / f"{slug}.json").read_text())
                view = ref["views"][VIEW_INDEX]
                left = html_shot(page, ref["index"], view).convert("RGB").resize((W, H))
                right = Image.fromarray(
                    render_offscreen(
                        ViewState(
                            shape=ref["index"],
                            ang=list(view["ang"]),
                            yaw=view["yaw"],
                            pitch=view["pitch"],
                        ),
                        W,
                        H,
                    )
                )
                combo = Image.new("RGB", (W * 2 + 4, H + 28), (16, 16, 16))
                combo.paste(left, (0, 28))
                combo.paste(right, (W + 4, 28))
                d = ImageDraw.Draw(combo)
                d.text((8, 7), f"{ref['name']} — HTML reference", fill=(220, 220, 220))
                d.text((W + 12, 7), "Python / moderngl", fill=(220, 220, 220))
                out = ASSETS / f"02-{slug}.png"
                combo.save(out)
                diff = np.asarray(left, dtype=np.int16) - render_offscreen(
                    ViewState(shape=ref["index"], ang=list(view["ang"]),
                              yaw=view["yaw"], pitch=view["pitch"]), W, H
                ).astype(np.int16)
                print(f"{slug}: wrote {out.name}  (mean abs pixel delta {np.abs(diff).mean():.2f})")
            browser.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
