"""Export the factorisation as a binary blob the browser can solve against.

With --pin-digits N the blob reserves the first N digits of the numeric filler
for a constant, and carries a `pin` section saying which pivot belongs to which
digit group. That last part is what makes an explorer possible: _build picks
pivots by POSITION and only solve() reads their values, so one factorisation
serves every constant at a given digit count and the browser can swap the
number with no new blob. The digits baked in here are zeros; they are meant to
be overridden.
"""
import argparse, json, pathlib, struct
from basis import Affine

from paths import WEB, WORK


def pack_bits(vals, L):
    """L bits, index 0 at the top, into little-endian u32 words."""
    words = (L + 31) // 32
    out = bytearray(words * 4)
    for j, v in enumerate(vals):
        if v:
            out[(j >> 5) * 4 + ((j >> 3) & 3)] |= 1 << (7 - (j & 7))
    return bytes(out), words


def int_to_bits(v, L):
    return [(v >> (L - 1 - j)) & 1 for j in range(L)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--version", type=int, default=12)
    ap.add_argument("--mask", type=int, default=0)
    ap.add_argument("--out", default="solver")
    ap.add_argument("--order", default="even", choices=["even", "centre", "clump", "streak", "gothic"])
    ap.add_argument("--pin-digits", type=int, default=0,
                    help="reserve this many leading filler digits for a constant")
    a = ap.parse_args()

    aff = Affine(a.url, version=a.version, mask=a.mask, level=0, order=a.order,
                 pin_digits="0" * a.pin_digits)
    n = aff.n
    buf = bytearray()
    meta = {"url": a.url, "version": a.version, "mask": a.mask, "modules": n,
            "order": a.order, "pin_digits": len(aff.pin_digits),
            "quiet": 4, "sections": {}, "blocks": []}

    def add(name, data):
        meta["sections"][name] = {"offset": len(buf), "bytes": len(data)}
        buf.extend(data)

    # the fixed layer: function patterns plus whatever the data layer leaves
    base, _ = pack_bits([aff.fixed[y][x] for y in range(n) for x in range(n)], n * n)
    add("base", base)

    for blk in aff.blocks:
        L = blk["L"]
        # module index for each bit position, with the mask flag in bit 15
        mods = []
        for j in range(L):
            p = aff.pos_of.get(blk["glob"][j])
            if p is None:
                mods.append(0xFFFF)
            else:
                x, y, inv = p
                mods.append((y * n + x) | (0x8000 if inv else 0))
        cur_bits = [aff.base_bits[blk["glob"][j]] for j in range(L)]
        cur, words = pack_bits(cur_bits, L)

        piv_j = struct.pack(f"<{len(blk['pivots'])}H", *blk["pivots"])
        piv_f = bytes((255 if j not in blk["forced"] else int(blk["forced"][j]))
                      for j in blk["pivots"])

        # Which pivots carry a pinned digit, as (group << 4) | bit weight.
        # 0xFFFF means "not a digit": the URL's own bits and the 511 caps keep
        # the values baked above. A client rewrites only the digit ones.
        pins = []
        for j in blk["pivots"]:
            gb = blk["glob"][j]
            off = gb - aff.num_start
            gi, k = divmod(off, 10)
            if (j in blk["forced"] and off >= 0 and gb < aff.upper
                    and gi * 3 + 3 <= len(aff.pin_digits) and k < 10):
                pins.append((gi << 4) | (9 - k))
            else:
                pins.append(0xFFFF)
        piv_pin = struct.pack(f"<{len(pins)}H", *pins)
        us = bytearray()
        for u in blk["us"]:
            packed, _ = pack_bits(int_to_bits(u, L), L)
            us.extend(packed)

        i = blk["bi"]
        add(f"mods{i}", struct.pack(f"<{L}H", *mods))
        add(f"cur{i}", cur)
        add(f"pivj{i}", piv_j)
        add(f"pivf{i}", piv_f)
        add(f"pin{i}", piv_pin)
        add(f"us{i}", bytes(us))
        meta["blocks"].append({"L": L, "words": words, "pivots": len(blk["pivots"])})

    out = WEB / a.out
    out.with_suffix(".bin").write_bytes(bytes(buf))
    out.with_suffix(".json").write_text(json.dumps(meta))
    total = sum(b["pivots"] for b in meta["blocks"])
    pinned = sum(1 for i in range(len(meta["blocks"]))
                 for v in struct.unpack(
                     f"<{meta['sections'][f'pin{i}']['bytes']//2}H",
                     bytes(buf[meta["sections"][f"pin{i}"]["offset"]:
                               meta["sections"][f"pin{i}"]["offset"]
                               + meta["sections"][f"pin{i}"]["bytes"]]))
                 if v != 0xFFFF)
    print(f"{a.out}.bin  {len(buf)/1024:.0f} KB   "
          f"{len(meta['blocks'])} blocks, {total} pivots, {n}x{n} modules, "
          f"{len(aff.pin_digits)} digits reserved on {pinned} pivots")


if __name__ == "__main__":
    main()
