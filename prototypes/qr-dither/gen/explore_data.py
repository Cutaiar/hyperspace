# -*- coding: utf-8 -*-
"""Data for the editions explorer: target bitmaps and constants.

The browser has no polytope geometry -- solver.js knows the tesseract and
nothing else -- so rather than port polytopes.py, the generator ships what the
explorer actually needs: the target bitmap for each pose, packed the same way
the manifest packs a module grid. A 65x65 target is 529 bytes, so all of them
together are smaller than one SVG.

Each pose ships twice: as the gallery has it, and repositioned to keep its ink
off the QR's own furniture. 497 modules are finders, timing, alignment and
format, fixed by the standard and controllable by nothing; ink landing on one
that shows paper is lost before any budget is spent, which caps stroke
fidelity. Margin and the camera distances are swept to dodge them. Rotation is
not swept: only edges quantising to 0, 45 or 90 degrees survive a square grid,
so the angles stay put.

    uv run --with pyqart --with pillow --with numpy --with mpmath \\
      python3 gen/explore_data.py --url https://hyperspace.cutaiar.io
"""
import argparse
import base64
import json

import numpy as np

import polytopes
import robust
from basis import Affine
from paths import WEB

OUT = WEB / "editions"
STROKE = {"c16_star": 5, "tess_shallow": 3}

CONSTANTS = [
    ("pi",       "π",    "Pi",                  lambda mp: mp.pi,
     "circle constant; transcendental (Lindemann 1882)"),
    ("tau",      "τ",    "Tau",                 lambda mp: 2 * mp.pi,
     "2π — one full turn"),
    ("e",        "ℯ",    "Euler's number",      lambda mp: mp.e,
     "base of the natural log"),
    ("phi",      "φ",    "Golden ratio",        lambda mp: mp.phi,
     "(1+√5)/2; all 1s in its continued fraction"),
    ("sqrt2",    "√2",   "Pythagoras' constant", lambda mp: mp.sqrt(2),
     "the first number proved irrational"),
    ("sqrt3",    "√3",   "Theodorus' constant", lambda mp: mp.sqrt(3),
     "the measure of the fish"),
    ("gamma",    "γ",    "Euler–Mascheroni",    lambda mp: mp.euler,
     "nobody knows if it is even irrational"),
    ("apery",    "ζ(3)", "Apéry's constant",    lambda mp: mp.apery,
     "proved irrational in 1978, to general astonishment"),
    ("catalan",  "G",         "Catalan's constant",  lambda mp: mp.catalan,
     "irrationality still unproven"),
    ("khinchin", "K₀",   "Khinchin's constant", lambda mp: mp.khinchin,
     "almost every real shares this continued-fraction mean"),
    ("glaisher", "A",         "Glaisher–Kinkelin",   lambda mp: mp.glaisher,
     "the hyperfactorial's Stirling constant"),
    ("gelfond",  "e^π",  "Gelfond's constant",  lambda mp: mp.exp(mp.pi),
     "transcendental; e^π − π is 19.999099979…"),
    ("omega",    "Ω",    "Omega constant",      lambda mp: mp.lambertw(1),
     "Ωe^Ω = 1, the Lambert W fixed point"),
    ("silver",   "δₛ", "Silver ratio",     lambda mp: 1 + mp.sqrt(2),
     "the golden ratio's next of kin"),
    ("lemnis",   "ϖ",    "Lemniscate constant",
     lambda mp: mp.gamma(mp.mpf(1) / 4) ** 2 / (2 * mp.sqrt(2 * mp.pi)),
     "π's twin for the lemniscate, Gauss's obsession"),
]
DIGITS = 48


def pack(arr):
    """Same convention as the manifest's matrix: row-major, MSB first."""
    return robust.pack([[bool(v) for v in row] for row in arr])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--version", type=int, default=12)
    ap.add_argument("--mask", type=int, default=0)
    args = ap.parse_args()
    n = 4 * args.version + 17
    OUT.mkdir(parents=True, exist_ok=True)

    from mpmath import mp
    mp.dps = DIGITS + 30
    consts = []
    for key, glyph, name, fn, note in CONSTANTS:
        v = mp.nstr(fn(mp), DIGITS + 12, strip_zeros=False)
        consts.append({"id": key, "glyph": glyph, "name": name, "note": note,
                       "digits": "".join(c for c in v if c.isdigit())[:DIGITS]})
    (OUT / "constants.json").write_text(
        json.dumps({"digits": DIGITS, "constants": consts}, indent=1), encoding="utf-8")

    # the furniture: modules nothing can control, and what they already show
    aff = Affine(args.url, version=args.version, mask=args.mask, level=0, order="even")
    data = np.zeros((n, n), bool)
    for off, (x, y, inv) in aff.pos_of.items():
        data[y][x] = True
    dead = ~data & ~np.array(aff.fixed)      # furniture showing paper: ink here is lost

    def measure(pose, stroke, **over):
        px = np.array(polytopes.pose(n, pose, stroke=stroke, **over)) < 128
        ink = int(px.sum())
        lost = int((px & dead).sum())
        return px, ink, lost, (100 * (ink - lost) / ink if ink else 0.0)

    fam_of = {s["id"]: (f["id"], f["label"])
              for f in polytopes.taxonomy() for s in f["subjects"]}
    label_of = {s["id"]: s["label"]
                for f in polytopes.taxonomy() for s in f["subjects"]}

    targets = []
    for pose in polytopes.POSES:
        subject, _, w0, z0, m0 = polytopes.POSES[pose]
        stroke = STROKE.get(pose, 2)
        bpx, bink, blost, bceil = measure(pose, stroke, w_dist=w0, z_dist=z0, margin=m0)
        zmin = 1.0 * w0 / (w0 - 1.0) * 1.3
        best = None
        for m in [round(0.04 + 0.01 * i, 3) for i in range(15)]:
            for wf in (0.80, 0.90, 1.0, 1.10, 1.25):
                for zf in (0.85, 1.0, 1.2):
                    w, z = round(w0 * wf, 3), round(z0 * zf, 3)
                    if z <= zmin or w <= 1.6:
                        continue
                    px, ink, lost, ceil = measure(pose, stroke, w_dist=w, z_dist=z, margin=m)
                    if not (bink * 0.85 <= ink <= bink * 1.15):
                        continue
                    if best is None or ceil > best[3]:
                        best = (px, ink, lost, ceil, {"w_dist": w, "z_dist": z, "margin": m})
        fid, flabel = fam_of[subject]
        for variant, (px, ink, lost, ceil, over) in (
                ("original", (bpx, bink, blost, bceil,
                              {"w_dist": w0, "z_dist": z0, "margin": m0})),
                ("repositioned", best[:5] if best else
                 (bpx, bink, blost, bceil, {"w_dist": w0, "z_dist": z0, "margin": m0}))):
            targets.append({
                "id": f"{pose}:{variant}", "pose": pose, "variant": variant,
                "subject": subject, "subject_label": label_of[subject],
                "family": fid, "family_label": flabel, "stroke": stroke,
                "ink": ink, "lost": lost, "ceiling": round(ceil, 1),
                "settings": over, "bits": pack(px),
            })
        print(f"  {pose:14} {bceil:5.1f}% → {best[3] if best else bceil:5.1f}%  "
              f"ink {bink} → {best[1] if best else bink}")

    (OUT / "targets.json").write_text(
        json.dumps({"url": args.url.rstrip('#'), "modules": n, "quiet": 4,
                    "mask": args.mask, "version": args.version,
                    "furniture": int((~data).sum()), "dead": int(dead.sum()),
                    "targets": targets}, indent=1), encoding="utf-8")
    kb = sum((OUT / f).stat().st_size for f in ("targets.json", "constants.json")) / 1024
    print(f"\n{len(targets)} targets, {len(consts)} constants, {kb:.0f} KB total")
    print(f"editions data: {OUT}")


if __name__ == "__main__":
    raise SystemExit(main())
