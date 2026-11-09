"""Contact sheet of the generated codes, for judging silhouette at a glance."""
import pathlib, re, sys
from PIL import Image, ImageDraw

from paths import WEB, WORK

OUT = WORK / "stills"
VERSIONS = [10, 12, 15]
COLS = ["nested_open", "nested_wide", "nested_tilt"]
STROKES = [2, 3]
TILE, PAD, LBL = 300, 8, 18

cols = COLS * 0  # placeholder
order = [(p, s) for p in COLS for s in STROKES]
W = len(order) * (TILE + PAD) + PAD
H = len(VERSIONS) * (TILE + PAD + LBL) + PAD
sheet = Image.new("RGB", (W, H), (18, 18, 22))
d = ImageDraw.Draw(sheet)

for r, v in enumerate(VERSIONS):
    for c, (p, s) in enumerate(order):
        f = OUT / f"qart_v{v}_{p}_s{s}.png"
        x = PAD + c * (TILE + PAD)
        y = PAD + r * (TILE + PAD + LBL)
        if f.exists():
            im = Image.open(f).convert("RGB").resize((TILE, TILE), Image.LANCZOS)
            sheet.paste(im, (x, y))
        d.text((x + 2, y + TILE + 3), f"v{v} {p} s{s}", fill=(170, 170, 180))

sheet.save(OUT / "_sheet2.png")
print(OUT / "_sheet2.png", sheet.size)
