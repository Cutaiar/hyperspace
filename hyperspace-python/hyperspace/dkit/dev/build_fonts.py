"""Build dkit's font files from Inter's variable woff2 - the same file the
React oracle renders with, so the comparison is the same typeface - and the
same family the panel sets its own words in (`hyperspace/fonts`, Inter 4.1).

    uv run --with fonttools --with brotli --with uharfbuzz \
        python hyperspace/dkit/dev/build_fonts.py

The last step checks `draw.shape` against HarfBuzz - Chromium's shaper - on
every string literal in the app plus 20000 generated ones, every face, and
fails the build on any difference in glyphs or advances.

Things that have to happen ahead of time, because Dear ImGui cannot do them
at runtime:

1. **Instance the variable axis.** ImGui's loader reads neither a woff2
   container nor a variation instance, so each weight is cut to a static TTF.

2. **Freeze `tnum`.** ImGui applies no OpenType features at all, so the
   tabular-figures substitution is baked into the cmap instead, producing a
   parallel `-tnum` face used wherever numbers are set.

3. **Export the substitutions Chromium applies by default** - `ccmp`,
   `liga`, `calt` and the rest of HarfBuzz's default set, whichever the font
   has - to `fonts/metrics.json`, for `draw.shape` to replay. Some change a
   width (Inter's `->` is one glyph, narrower than two; Geist's `tt` and
   `ff` were 0.05em narrower than their letters); others change only a
   shape (Inter raises a colon between digits and a hyphen between
   capitals). Every glyph a substitution can produce is given a Private Use
   codepoint in the cmap, so the kit can name it and ImGui can draw it.

4. **Give the line box a span of one em.** Dear ImGui's FreeType loader
   sizes a face by `FT_SIZE_REQUEST_TYPE_REAL_DIM` - ascender minus
   descender - and ImGui 1.92 ROUNDS every font size to a whole pixel. With
   the font's own metrics the kit had to ask for `css_px * span`, which
   rounds (Geist: 12px -> 15.6 -> 16, text 2.6% large). With a span of
   exactly upem the size the kit pushes IS the CSS px, and needs no
   rounding. The split only places ImGui's own line box (which stock
   widgets such as InputText use); see `ONE_EM` below.

5. **Write what the TTFs no longer say** to `fonts/metrics.json`: the real
   ascender and descender, which `draw.py` places a baseline with the way
   Blink does; the `kern` feature as a table of character pairs, because
   ImGui applies no OpenType positioning and Chromium kerns by default; and
   every glyph's advance from `hmtx`, exactly - FreeType reports one in
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
FAMILY = "Inter"
# fontsource's default `@fontsource-variable/inter` import: the wght axis
# only, at Inter's text optical size - the cut the panel's own Inter is.
SRC = (HERE / "../../../../prototypes/dashboard/node_modules/"
       "@fontsource-variable/inter/files/inter-latin-wght-normal.woff2")

WEIGHTS = {"Regular": 400, "Medium": 500, "SemiBold": 600}

# The line box written into the TTFs. Its SUM is what matters - one em, so
# ImGui's size is the CSS px. The split only places ImGui's own line box,
# ceil(ONE_EM[0] / upem * px) above the baseline, which stock widgets use;
# draw.py corrects what is left (`draw.stock_text_y`) rather than relying on
# it. In font units of a 2048-upem font: 0.8 em above, 0.2 below.
ONE_EM_FRAC = (0.8, -0.2)

# HarfBuzz's default substitution features for horizontal text, which
# Chromium leaves on (`locl` needs a language and the kit sets none).
GSUB_FEATURES = ("ccmp", "rlig", "liga", "clig", "calt", "rclt")


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


def _lookup(table, li):
    """(type, subtables) with Extension (GSUB 7 / GPOS 9) unwrapped."""
    lk = table.LookupList.Lookup[li]
    subs = [getattr(st, "ExtSubTable", st) for st in lk.SubTable]
    ty = lk.LookupType
    if ty in (7, 9) and lk.SubTable:
        ty = lk.SubTable[0].ExtensionLookupType
    return ty, subs


def _chain_records(st):
    """Every SubstLookupRecord in a chain subtable, of any format."""
    if st.Format == 3:
        return list(st.SubstLookupRecord)
    sets = st.ChainSubRuleSet if st.Format == 1 else st.ChainSubClassSet
    rule = "ChainSubRule" if st.Format == 1 else "ChainSubClassRule"
    return [r for rs in sets if rs for ru in getattr(rs, rule) for r in ru.SubstLookupRecord]


def _chain_rules(st, rev) -> list:
    """A chain subtable as coverage-form rules, in the order HarfBuzz tries
    them: [backtrack sets, input sets, lookahead sets, records]. Formats 1
    (glyph sequences) and 2 (class sequences) are rewritten into format 3's
    shape, which is lossless here because the build knows every character
    the buffer can hold (`rev`) - class 0, "every glyph in no class", is
    spelled out as exactly that."""
    alphabet = set(rev)

    def chars(glyphs):
        return "".join(sorted(chr(rev[g]) for g in glyphs if g in rev))

    def recs(ru):
        return [[r.SequenceIndex, r.LookupListIndex] for r in ru.SubstLookupRecord]

    if st.Format == 3:
        return [[[chars(c.glyphs) for c in st.BacktrackCoverage],
                 [chars(c.glyphs) for c in st.InputCoverage],
                 [chars(c.glyphs) for c in st.LookAheadCoverage],
                 recs(st)]]
    cov = set(st.Coverage.glyphs)
    out = []
    if st.Format == 1:
        for first, rs in zip(st.Coverage.glyphs, st.ChainSubRuleSet):
            for ru in (rs.ChainSubRule if rs else ()):
                out.append([[chars([g]) for g in ru.Backtrack],
                            [chars([first])] + [chars([g]) for g in ru.Input],
                            [chars([g]) for g in ru.LookAhead], recs(ru)])
        return out

    def members(cd):
        by = {}
        for g, k in cd.classDefs.items():
            by.setdefault(k, set()).add(g)
        by[0] = alphabet - set(cd.classDefs)
        return lambda k: chars(by.get(k, ()))

    bk, ik, ak = (members(st.BacktrackClassDef), members(st.InputClassDef),
                  members(st.LookAheadClassDef))
    for k1, rs in enumerate(st.ChainSubClassSet):
        if not rs:
            continue
        first = chars(cov & {g for g in alphabet
                             if st.InputClassDef.classDefs.get(g, 0) == k1})
        for ru in rs.ChainSubClassRule:
            out.append([[bk(k) for k in ru.Backtrack],
                        [first] + [ik(k) for k in ru.Input],
                        [ak(k) for k in ru.LookAhead], recs(ru)])
    return out


def export_gsub(font: TTFont, features=GSUB_FEATURES) -> list:
    """The default substitutions as data `draw.shape` can replay; maps every
    glyph they can produce into the cmap at a Private Use codepoint.

    Returned: [lookups, order, sets]. `order` is the top-level lookups in the
    order HarfBuzz applies them - every enabled feature's lookups together,
    by lookup index. `lookups[i]` is one of
      ["single", {char: char}]
      ["liga",   {first char: [[rest, out char], ...]}]   (font order)
      ["chain",  [[backtrack sets, input sets, lookahead sets,
                   [[sequence index, lookup index], ...]], ...]]
    with each set an index into `sets`, a list of strings of characters; chains of every format come out in
    coverage form (`_chain_rules`). Any other lookup type stops the build
    rather than being approximated. dev/test_text.py checks the replay
    against HarfBuzz."""
    gsub = font["GSUB"].table
    cmap = font.getBestCmap()
    rev = {}
    for cp, g in sorted(cmap.items()):
        rev.setdefault(g, cp)
    order = sorted({li for fr in gsub.FeatureList.FeatureRecord
                    if fr.FeatureTag in features
                    for li in fr.Feature.LookupListIndex})
    # every lookup reachable from the top level, and every glyph produced
    need, todo = set(), list(order)
    while todo:
        li = todo.pop()
        if li in need:
            continue
        need.add(li)
        ty, subs = _lookup(gsub, li)
        if ty == 6:
            for st in subs:
                todo += [r.LookupListIndex for r in _chain_records(st)]
        elif ty not in (1, 4):
            raise SystemExit(f"lookup {li}: GSUB type {ty} is not replayed")
    outs = set()
    for li in need:
        ty, subs = _lookup(gsub, li)
        for st in subs:
            if ty == 1:
                outs.update(st.mapping.values())
            elif ty == 4:
                outs.update(lig.LigGlyph for ligs in st.ligatures.values()
                            for lig in ligs)
    fresh = sorted(o for o in outs if o not in rev)
    for i, g in enumerate(fresh):
        rev[g] = PUA + i
    for table in font["cmap"].tables:
        if table.isUnicode():
            for g in fresh:
                table.cmap[rev[g]] = g

    def ch(g):
        return chr(rev[g]) if g in rev else None

    lookups = {}
    for li in sorted(need):
        ty, subs = _lookup(gsub, li)
        if ty == 1:
            m = {}
            for st in subs:
                for a, b in st.mapping.items():
                    if ch(a) and a not in m:
                        m[ch(a)] = ch(b)
            lookups[li] = ["single", m]
        elif ty == 4:
            m = {}
            for st in subs:
                for first, ligs in st.ligatures.items():
                    if not ch(first):
                        continue
                    for lig in ligs:
                        rest = [ch(g) for g in lig.Component]
                        if all(rest):
                            m.setdefault(ch(first), []).append(
                                ["".join(rest), ch(lig.LigGlyph)])
            lookups[li] = ["liga", m]
        else:
            rules = []
            for st in subs:
                rules += _chain_rules(st, rev)
            lookups[li] = ["chain", rules]
    # Each distinct character set once, rules naming it by index: the same
    # capitals or digits recur in dozens of rules, and spelled out each time
    # they made metrics.json ten times its size.
    sets, index = [], {}

    def ref(chars):
        if chars not in index:
            index[chars] = len(sets)
            sets.append(chars)
        return index[chars]

    for kind, data in lookups.values():
        if kind == "chain":
            for rule in data:
                for part in range(3):
                    rule[part] = [ref(x) for x in rule[part]]
    return [{str(k): v for k, v in lookups.items()}, order, sets]


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
                ty, subs = _lookup(gpos, li)
                if ty != 2:
                    raise SystemExit(f"kern lookup {li} is type {ty}")
                for st in subs:
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
    upem = font["head"].unitsPerEm
    asc = round(ONE_EM_FRAC[0] * upem)
    one = (asc, asc - upem)
    font["hhea"].ascent, font["hhea"].descent = one
    font["hhea"].lineGap = 0
    os2 = font["OS/2"]
    os2.sTypoAscender, os2.sTypoDescender = one
    os2.sTypoLineGap = 0


def cut(weight: int) -> TTFont:
    # recalcTimestamp off, so a rebuild changes only what the build changes
    f = TTFont(SRC, recalcTimestamp=False)
    instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True,
                                      updateFontNames=False)
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
    meta = {"family": FAMILY, "faces": {}}
    for name, wght in WEIGHTS.items():
        for tnum in (False, True):
            dest = OUT / f"{FAMILY}-{name}{'-tnum' if tnum else ''}.ttf"
            f = cut(wght)
            # read BEFORE one_em overwrites them
            meta.update(upem=f["head"].unitsPerEm,
                        ascender=f["hhea"].ascent, descender=f["hhea"].descent)
            # `tnum` is REPLAYED with the rest, in lookup order, not frozen
            # first: Inter's tabular figures cover punctuation too, and its
            # `calt` raises that punctuation between digits - frozen ahead
            # of `calt`, the raised forms were never chosen (9065 of 27k
            # strings differed from HarfBuzz).
            gsub = export_gsub(f, GSUB_FEATURES + (("tnum",) if tnum else ()))
            kern = kern_pairs(f)
            hmtx = f["hmtx"]
            adv = {chr(cp): hmtx[g][0] for cp, g in f.getBestCmap().items()
                   if cp >= 0x20}
            meta["faces"][dest.name] = dict(classes(kern), gsub=gsub, adv=adv)
            # ...and ALSO frozen into the cmap, after the tables are read,
            # for the one path that draws without `draw.shape`: a stock
            # widget (InputText) setting digits in the tabular face.
            if tnum and not freeze(f, "tnum"):
                raise SystemExit("tnum produced no substitutions - wrong source?")
            one_em(f)
            f.save(dest)
            print(f"{dest.name:28} wght {wght}  {len(kern)} kern pairs, "
                  f"{len(gsub[1])} substitution lookups"
                  f"{'  tabular figures frozen' if tnum else ''}")
    (OUT / "metrics.json").write_text(
        json.dumps(meta, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")) + "\n")


def check_shaping() -> None:
    """`draw.shape` against HarfBuzz on the SOURCE font, glyph for glyph and
    advance for advance, for every face. The corpus is every string literal
    in the app - its real labels - and 20000 generated strings over the
    characters the context rules turn on (digits, capitals, brackets,
    dashes, colons). Run on the files just written."""
    import ast
    import importlib
    import io
    import random

    import uharfbuzz as hb

    from hyperspace.dkit import draw as D
    importlib.reload(D)                  # the metrics.json just written
    src = TTFont(SRC)
    src.flavor = None
    raw = io.BytesIO()
    src.save(raw)
    face, order = hb.Face(raw.getvalue()), src.getGlyphOrder()
    upem, have = src["head"].unitsPerEm, set(src.getBestCmap())
    corpus = set()
    for py in (HERE.parent.parent).rglob("*.py"):
        for n in ast.walk(ast.parse(py.read_text())):
            v = getattr(n, "value", None)
            if isinstance(n, ast.Constant) and isinstance(v, str) and 0 < len(v) < 60:
                corpus.add(v)
    rnd = random.Random(1)
    alpha = "AXYZabcxyz0123456789:-\u2013\u2014()[]{}<>=+*/.,% xX\u00d7@#&!?'\"_|"
    for _ in range(20000):
        corpus.add("".join(rnd.choice(alpha) for _ in range(rnd.randint(2, 7))))
    corpus = sorted(t for t in corpus if all(ord(c) >= 0x20 and ord(c) in have for c in t))
    bad = []
    for variant, wght in (("regular", 400), ("medium", 500), ("semibold", 600)):
        for tnum in (False, True):
            font = hb.Font(face)
            font.set_variations({"wght": wght})
            built = TTFont(OUT / dict(D.FACE_FILES)[D.face_key(variant, tnum)])
            name_of = built.getBestCmap()
            for t in corpus:
                buf = hb.Buffer()
                buf.add_str(t)
                buf.guess_segment_properties()
                hb.shape(font, buf, {"tnum": True} if tnum else {})
                want = [order[i.codepoint] for i in buf.glyph_infos]
                adv = [p.x_advance for p in buf.glyph_positions]
                glyphs, pen = D.shape(t, variant, tnum)
                if [name_of.get(ord(c)) for c in glyphs] != want or None in pen or \
                        any(abs(a - b * upem) > 1.5 for a, b in zip(adv, pen)):
                    bad.append((variant, tnum, t))
    print(f"shaping checked against HarfBuzz: {len(corpus)} strings x 6 faces, "
          f"{len(bad)} different")
    if bad:
        raise SystemExit(f"draw.shape differs from HarfBuzz, e.g. {bad[:5]}")


if __name__ == "__main__":
    main()
    try:
        import uharfbuzz  # noqa: F401
    except ImportError:
        raise SystemExit("uharfbuzz missing: the files are written but NOT "
                         "checked - run with `--with uharfbuzz`") from None
    check_shaping()
