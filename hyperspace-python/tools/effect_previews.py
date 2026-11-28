#!/usr/bin/env python3
"""Every effect file's preview, written out — for docs, and for a
future skill that needs to see what an effect does without running the app.

For each file in ``hyperspace/shaders/fx/`` (or ``--fx``), the test card
put through the effect at the file's defaults, made exactly as GRAPH's
effect picker makes it (`previews.EffectPreviews`, on a standalone GL
context): ``<name>.png``, the still, and ``<name>.gif``, the loop
(`previews.LOOP_FRAMES` frames over `previews.LOOP_S` seconds of the
effect's clock at its default speed, looping). ``--sheet`` also writes
``sheet.png``: every still on one page, grouped by family as the picker
groups them, each labelled.

    uv run python tools/effect_previews.py --out /tmp/effects
    uv run python tools/effect_previews.py --out docs/plans/assets/65-effect-previews/sheet --sheet --no-gif

Writes only under ``--out``, which it refuses to be the library home
(``~/Hyperspace``) or anything under it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from hyperspace import previews as pv
from hyperspace.fx import FX_DIR, FxState


def _refuse(out: Path) -> None:
    home = (Path.home() / "Hyperspace").resolve()
    o = out.resolve()
    if o == home or home in o.parents:
        raise SystemExit(f"refusing to write under the library home {home}")


def made(fx_dir: Path) -> tuple[pv.EffectPreviews, FxState]:
    """Every file's still and loop, made on a context of the tool's own."""
    ctx = moderngl.create_context(standalone=True)
    st = FxState(fx_dir)
    cache = pv.EffectPreviews(st, ctx, budget=10_000)
    names = sorted(st.files)
    for name in names:                  # one file at a time: all its cells
        cache.want([name], loop=name)
        cache.make()
    if cache.error:
        raise SystemExit(f"previews: {cache.error}")
    return cache, st


def cell(cache: pv.EffectPreviews, name: str, k: int) -> Image.Image:
    """Cell `k` of file `name`'s atlas as an image, the right way up."""
    tex = cache.atlas[name][0]
    a = np.frombuffer(tex.read(), np.uint8).reshape(pv.ATLAS_H, pv.ATLAS_W, 4)
    x, y, w, h = pv.cell_rect(k)
    return Image.fromarray(a[y:y + h, x:x + w, :3][::-1].copy())


def sheet(cache: pv.EffectPreviews, st: FxState, scale: int = 1) -> Image.Image:
    """Every still, grouped by family (`previews.families`), labelled."""
    groups = pv.families(st.files.values())
    cols, pad, label_h, head_h = 5, 12, 22, 28
    w, h = pv.PREVIEW_W * scale, pv.PREVIEW_H * scale
    rows = sum(-(-len(g) // cols) for _, g in groups)
    W = cols * w + (cols + 1) * pad
    H = rows * (h + label_h + pad) + len(groups) * head_h + pad
    img = Image.new("RGB", (W, H), (23, 23, 23))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 15)
    except OSError:
        font = bold = ImageFont.load_default()
    y = pad
    for family, group in groups:
        d.text((pad, y + 4), family, fill=(161, 161, 161), font=bold)
        y += head_h
        for i, spec in enumerate(group):
            if i and i % cols == 0:
                y += h + label_h + pad
            x = pad + (i % cols) * (w + pad)
            img.paste(cell(cache, spec.name, 0).resize((w, h)), (x, y))
            d.text((x + 2, y + h + 3), spec.label, fill=(230, 230, 230), font=font)
        y += h + label_h + pad
    return img


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True, help="the folder to write into")
    ap.add_argument("--fx", type=Path, default=FX_DIR, help="the effect files' folder")
    ap.add_argument("--sheet", action="store_true", help="also every still on one page")
    ap.add_argument("--no-gif", action="store_true", help="the stills only")
    ap.add_argument("--only", nargs="*", help="these files only")
    a = ap.parse_args(argv)
    _refuse(a.out)
    a.out.mkdir(parents=True, exist_ok=True)
    cache, st = made(a.fx)
    names = sorted(st.files) if not a.only else [n for n in a.only if n in st.files]
    for name in names:
        cell(cache, name, 0).save(a.out / f"{name}.png")
        if not a.no_gif:
            frames = [cell(cache, name, k) for k in range(1, pv.LOOP_FRAMES + 1)]
            frames[0].save(a.out / f"{name}.gif", save_all=True, append_images=frames[1:],
                           duration=round(1000 * pv.LOOP_S / pv.LOOP_FRAMES), loop=0)
        why = cache.failed(name)
        print(f"{name}: {'plain card — ' + why.splitlines()[0] if why else 'ok'}")
    if a.sheet:
        sheet(cache, st).save(a.out / "sheet.png")
    print(f"{len(names)} effects → {a.out} ({cache.bytes_kept / 1e6:.1f} MB of textures)")
    cache.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
