"""Build dkit's font files from Geist's variable woff2.

    uv run --with fonttools --with brotli python tools/dkit/build_fonts.py

Two things have to happen ahead of time, because Dear ImGui cannot do either
at runtime:

1. **Instance the variable axis.** stb_truetype reads neither a woff2
   container nor a variation instance, so each weight is cut to a static TTF.

2. **Freeze `tnum`.** stb_truetype applies no OpenType features at all, which
   is why a digit-heavy string measured 4% narrow against the browser. The
   tabular-figures substitution is baked into the cmap instead, producing a
   parallel `-tnum` face used wherever numbers are set.

Freezing is deliberately kept to a separate face rather than applied to the
default one. shadcn turns `tabular-nums` on selectively (card values, table
cells), not everywhere, and this project already works the same way — a mono
face for readouts, a proportional one for words (`ui.py:126-129`).
"""

from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent
OUT = HERE / "fonts"
SRC = (HERE / "../../../prototypes/dashboard/node_modules/"
       "@fontsource-variable/geist/files/geist-latin-wght-normal.woff2")

WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600}


def single_subs(font: TTFont, tag: str) -> dict:
    """glyph -> replacement, for every single substitution a feature runs."""
    gsub = font.get("GSUB")
    if gsub is None:
        return {}
    idx = [fr.Feature for fr in gsub.table.FeatureList.FeatureRecord
           if fr.FeatureTag == tag]
    out: dict[str, str] = {}
    for feat in idx:
        for li in feat.LookupListIndex:
            lk = gsub.table.LookupList.Lookup[li]
            for st in lk.SubTable:
                # LookupType 1 is a one-for-one swap, which is all tnum needs
                mapping = getattr(st, "mapping", None)
                if mapping:
                    out.update(mapping)
    return out


def freeze(font: TTFont, tag: str) -> int:
    """Point the cmap at a feature's outputs, so it applies with no shaper."""
    subs = single_subs(font, tag)
    if not subs:
        return 0
    n = 0
    for table in font["cmap"].tables:
        for cp, name in list(table.cmap.items()):
            if name in subs:
                table.cmap[cp] = subs[name]
                n += 1
    return n


def cut(weight: int, tnum: bool) -> TTFont:
    f = TTFont(SRC)
    instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True,
                                      updateFontNames=False)
    if tnum:
        n = freeze(f, "tnum")
        if not n:
            raise SystemExit("tnum produced no substitutions — wrong source?")
    f.flavor = None                       # woff2 container off; plain TTF out
    return f


def main() -> None:
    if not SRC.exists():
        raise SystemExit(
            f"missing {SRC}\n"
            "run `npm install` in prototypes/dashboard first — the source is "
            "the same woff2 the React oracle renders with, so the comparison "
            "is the same typeface")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, wght in WEIGHTS.items():
        for tnum in (False, True):
            dest = OUT / f"Geist-{name}{'-tnum' if tnum else ''}.ttf"
            cut(wght, tnum).save(dest)
            print(f"{dest.name:28} wght {wght}"
                  f"{'  tabular figures frozen' if tnum else ''}")


if __name__ == "__main__":
    main()
