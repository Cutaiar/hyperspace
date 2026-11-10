"""Build dkit's font files from Geist's variable woff2.

    uv run --with fonttools --with brotli python hyperspace/dkit/dev/build_fonts.py

Two things have to happen ahead of time, because Dear ImGui cannot do either
at runtime:

1. **Instance the variable axis.** stb_truetype reads neither a woff2
   container nor a variation instance, so each weight is cut to a static TTF.

2. **Freeze `tnum`.** stb_truetype applies no OpenType features at all, which
   is why a digit-heavy string measured 4% narrow against the browser. The
   tabular-figures substitution is baked into the cmap instead, producing a
   parallel `-tnum` face used wherever numbers are set.

3. **Freeze `liga` the same way.** Chromium applies Geist's ligatures by
   default and some change the width - `tt` and `ff` are 0.05em narrower
   than their two letters, so "Settings" is 0.6px narrower at 12px. Each
   ligature glyph is given a Private Use codepoint, and `fonts/metrics.json`
   lists which letter sequences become which, for `draw.py` to substitute
   before it measures or draws.

4. **Give the line box a span of one em.** Dear ImGui's FreeType loader
   sizes a face by `FT_SIZE_REQUEST_TYPE_REAL_DIM` - ascender minus
   descender - and ImGui 1.92 ROUNDS every font size to a whole pixel. With
   Geist's own 1005 / -295 the kit had to ask for `css_px * 1.30`, which
   rounds (12px -> 15.6 -> 16), so 12px text drew 2.6% large. With a span
   of exactly upem the size the kit pushes IS the CSS px, and needs no
   rounding. The split, 800 / -200, only places ImGui's own line box (which
   stock widgets such as InputText use); see `ONE_EM` below.

5. **Write what the TTFs no longer say** to `fonts/metrics.json`: Geist's
   real ascender and descender, which `draw.py` places a baseline with the
   way Blink does, and the `kern` feature as a table of character pairs,
   because ImGui applies no OpenType positioning and Chromium kerns by
   default ("Ctrl" is 21.588 unkerned and 21.192 kerned at 12px medium).
   And every glyph's advance from `hmtx`, exactly: FreeType reports one in
   1/64ths of a pixel, which drifts a long string by 0.05px or more.

Freezing is deliberately kept to a separate face rather than applied to the
default one. shadcn turns `tabular-nums` on selectively (card values, table
cells), not everywhere, and this project already works the same way — a mono
face for readouts, a proportional one for words (`ui.py:126-129`).
"""

from __future__ import annotations

import json
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "fonts"   # the package's
SRC = (HERE / "../../../../prototypes/dashboard/node_modules/"
       "@fontsource-variable/geist/files/geist-latin-wght-normal.woff2")

WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600}

# The line box written into the TTFs. Its SUM is what matters - one em, so
# ImGui's size is the CSS px. The split is chosen so ImGui's own line box,
# ceil(0.8 * px) above the baseline, puts a stock widget's baseline where
# Blink's centring does at 12, 13 and 14px; draw.py corrects what is left
# (`draw.stock_text_y`) rather than relying on it.
ONE_EM = (800, -200)


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


PUA = 0xE000


def freeze_liga(font: TTFont) -> list:
    """Map every `liga` output glyph into the cmap; return the rules.

    The rules come back as [letters, codepoint] in the order HarfBuzz tries
    them - lookup by lookup, and within a lookup the ligature set of the
    first letter in the font's own order, which puts the longest first.
    Codepoints are assigned from U+E000 by sorted glyph name, so every face
    agrees on them."""
    gsub = font["GSUB"].table
    cmap = font.getBestCmap()
    rev = {}
    for cp, g in sorted(cmap.items()):
        rev.setdefault(g, cp)
    lookups = []
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag == "liga":
            lookups += [i for i in fr.Feature.LookupListIndex if i not in lookups]
    rules, outs = [], set()
    for li in lookups:
        lk = gsub.LookupList.Lookup[li]
        for st in lk.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if lk.LookupType not in (4, 7) or not hasattr(st, "ligatures"):
                raise SystemExit(f"liga lookup {li} is type {lk.LookupType}")
            for first, ligs in st.ligatures.items():
                for lig in ligs:
                    seq = [first] + list(lig.Component)
                    if all(g in rev for g in seq):
                        rules.append(("".join(chr(rev[g]) for g in seq),
                                      lig.LigGlyph))
                        outs.add(lig.LigGlyph)
    code = {g: rev.get(g) or PUA + i
            for i, g in enumerate(sorted(o for o in outs if o not in rev))}
    code.update({g: rev[g] for g in outs if g in rev})
    for table in font["cmap"].tables:
        if table.isUnicode():
            for g, cp in code.items():
                table.cmap[cp] = g
    return [[letters, code[g]] for letters, g in rules]


def kern_pairs(font: TTFont) -> dict:
    """Every character pair the `kern` feature moves, in font units.

    The way HarfBuzz applies GPOS pair positioning to two glyphs with no
    mark between them: each lookup of the feature in turn, and within a
    lookup the FIRST subtable that covers the left glyph wins - for a
    class-based subtable that holds even when its value is zero. Values
    from separate lookups add. Only the left glyph's XAdvance is read; the
    build refuses a font that positions anything else.
    """
    gpos = font["GPOS"].table
    cmap = font.getBestCmap()
    lookups = []
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == "kern":
            lookups += [i for i in fr.Feature.LookupListIndex if i not in lookups]

    def adv(v):
        return getattr(v, "XAdvance", 0) or 0 if v is not None else 0

    def one(st, left, right):
        """(applies, value) for one PairPos subtable."""
        if left not in st.Coverage.glyphs:
            return False, 0
        if st.Format == 1:
            ps = st.PairSet[st.Coverage.glyphs.index(left)]
            for rec in ps.PairValueRecord:
                if rec.SecondGlyph == right:
                    if getattr(rec, "Value2", None) is not None and any(
                            getattr(rec.Value2, a, 0) for a in rec.Value2.__dict__):
                        raise SystemExit("kern moves a second glyph")
                    return True, adv(rec.Value1)
            return False, 0
        c1 = st.ClassDef1.classDefs.get(left, 0)
        c2 = st.ClassDef2.classDefs.get(right, 0)
        rec = st.Class1Record[c1].Class2Record[c2]
        return True, adv(rec.Value1)

    glyphs = {cp: g for cp, g in cmap.items() if cp >= 0x20}
    out = {}
    for lc, lg in glyphs.items():
        for rc, rg in glyphs.items():
            total = 0
            for li in lookups:
                lk = gpos.LookupList.Lookup[li]
                if lk.LookupType != 2:
                    raise SystemExit(f"kern lookup {li} is type {lk.LookupType}")
                for st in lk.SubTable:
                    hit, v = one(st, lg, rg)
                    if hit:
                        total += v
                        break
            if total:
                out[chr(lc) + chr(rc)] = total
    return out


def classes(pairs: dict) -> dict:
    """The pair table, losslessly regrouped: characters that kern
    identically on the left share a class, likewise on the right, and the
    matrix between the classes is stored sparse - [right class, value, ...]
    per left class. Thirteen thousand pairs come out at ~55 x 50 classes,
    which is the shape of the font's own class-based subtable."""
    lefts = sorted({p[0] for p in pairs})
    rights = sorted({p[1] for p in pairs})
    row = {a: tuple(sorted((p[1], v) for p, v in pairs.items() if p[0] == a))
           for a in lefts}
    col = {b: tuple(sorted((p[0], v) for p, v in pairs.items() if p[1] == b))
           for b in rights}
    lsig = sorted(set(row.values()))
    rsig = sorted(set(col.values()))
    left = ["".join(a for a in lefts if row[a] == sig) for sig in lsig]
    right = ["".join(b for b in rights if col[b] == sig) for sig in rsig]
    rc = {b: i for i, cls in enumerate(right) for b in cls}
    m = []
    for cls in left:
        a = cls[0]
        seen = {}
        for (_, b), v in ((p, v) for p, v in pairs.items() if p[0] == a):
            seen[rc[b]] = v
        m.append([x for k in sorted(seen) for x in (k, seen[k])])
    out = {"left": left, "right": right, "kern": m}
    back = {}
    for li, cls in enumerate(left):
        for a in cls:
            flat = m[li]
            for k, v in zip(flat[::2], flat[1::2]):
                for b in right[k]:
                    back[a + b] = v
    if back != pairs:
        raise SystemExit("kern classes do not round-trip")
    return out


def one_em(font: TTFont) -> None:
    """hhea and the typo metrics both: the font sets USE_TYPO_METRICS, and
    FreeType honours it."""
    font["hhea"].ascent, font["hhea"].descent = ONE_EM
    font["hhea"].lineGap = 0
    os2 = font["OS/2"]
    os2.sTypoAscender, os2.sTypoDescender = ONE_EM
    os2.sTypoLineGap = 0


def cut(weight: int, tnum: bool) -> TTFont:
    # recalcTimestamp off, so a rebuild changes only what the build changes
    f = TTFont(SRC, recalcTimestamp=False)
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
    meta = {"faces": {}}
    for name, wght in WEIGHTS.items():
        for tnum in (False, True):
            dest = OUT / f"Geist-{name}{'-tnum' if tnum else ''}.ttf"
            f = cut(wght, tnum)
            # read BEFORE one_em overwrites them
            meta.update(upem=f["head"].unitsPerEm,
                        ascender=f["hhea"].ascent, descender=f["hhea"].descent)
            liga = freeze_liga(f)
            kern = kern_pairs(f)
            hmtx = f["hmtx"]
            adv = {chr(cp): hmtx[g][0] for cp, g in f.getBestCmap().items()
                   if cp >= 0x20}
            meta["faces"][dest.name] = dict(classes(kern), liga=liga, adv=adv)
            one_em(f)
            f.save(dest)
            print(f"{dest.name:28} wght {wght}  {len(kern)} kern pairs, "
                  f"{len(liga)} ligatures"
                  f"{'  tabular figures frozen' if tnum else ''}")
    (OUT / "metrics.json").write_text(
        json.dumps(meta, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
