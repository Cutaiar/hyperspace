"""Reduce QArt to an affine map, so a browser can solve it per frame.

pyqart redoes Gaussian elimination for every image.  But the generator basis of
the code depends only on the block geometry, and the image only supplies target
values -- so if the pivot ORDER is pinned instead of being sorted by image
contrast, the whole thing collapses to

    result = base XOR  SUM over pivots p of  (base_p XOR desired_p) * u_p

with the reduced basis {u_p} computed once.  Each u_p is 1 at p and 0 at every
other pivot, so the terms are independent and a frame costs only XORs.

The numeric filler is the one non-linear part: pyqart encodes it in numeric
mode, where each 10-bit group must read below 1000, and it retries when one
does not.  Pinning each group's top bit to zero caps it at 511 and removes the
retry, making validity structural.  It costs one bit of drawing freedom in ten.
"""
import math

from pyqart.qr.args import QrArgs
from pyqart.qr.data import QrData
from pyqart.qr.data.numbers import Numbers
from pyqart.qr.ec import RSEncoder
from pyqart.qr.painter import QrPainter
from pyqart.qr.painter.point import QrPointType
from pyqart.common import BIT_PER_CW


def _hash01(i, j, seed):
    v = (i * 374761393 + j * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF) / 0xFFFF


def _value_noise(x, y, seed=0):
    """Smooth lattice noise.  Thresholding it gives connected blobs rather than
    isolated points, which is the whole difference between clumps and sparkles."""
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    a = _hash01(x0, y0, seed) * (1 - sx) + _hash01(x0 + 1, y0, seed) * sx
    b = _hash01(x0, y0 + 1, seed) * (1 - sx) + _hash01(x0 + 1, y0 + 1, seed) * sx
    return a * (1 - sy) + b * sy


# How the leftover noise is shaped.  sx/sy are the noise cell size in modules;
# making sy larger than sx stretches the blobs into vertical streaks, which is
# what reads as a line artifact against the QR grid.
TEXTURES = {
    "even":   None,
    "centre": None,
    "clump":  dict(sx=5.0, sy=5.0, oct2=0.45, seed=7),
    "streak": dict(sx=2.2, sy=9.0, oct2=0.35, seed=3),
    "gothic": dict(sx=3.0, sy=7.0, oct2=0.60, seed=11),
}


class Affine:
    def __init__(self, url, version=12, mask=0, level=0, order="even"):
        """order: "centre" spends every degree of freedom on the middle and
        leaves a dense noise ring at the rim; "even" spreads the modules it
        cannot control uniformly, so the leftover noise reads as one texture
        across the whole code instead of a border."""
        self.url, self.version, self.mask, self.level = url, version, mask, level
        self.order = order

        data = QrData(url + "#", level)
        painter = QrPainter(data, version, mask, 0)
        args, available, used = painter.get_params()

        # mirror qart.py's numeric-filler sizing exactly
        cci = args.cci_length_of(Numbers)
        avail_num = available - 4 - cci
        used += 4 + cci
        count = avail_num // 10 * 3
        rem = avail_num % 10
        if rem >= 7:
            count += 2
            rem -= 7
        elif rem >= 4:
            count += 1
            rem -= 4
        data.put_numbers("0" * count)
        # the writable window: [num_start, upper).  Below it sit the mode
        # indicators and the URL itself; above it the trailing pad bits.  Both
        # must survive untouched or the payload stops being the URL.
        self.upper = args.dcwc * BIT_PER_CW - rem

        self.args, self.painter = args, painter
        self.numbers_count, self.num_start = count, used
        self.n = args.size if hasattr(args, "size") else 4 * version + 17

        self.base_bits = self._bits_to_list(painter.bits)
        self.canvas = painter.canvas
        self.canvas.load_data(painter.bits)

        self.dcwc_bits = args.dcwc * BIT_PER_CW
        self.ecbc = args.eccwcpb * BIT_PER_CW

        self._map_points()
        self._build()

    # ---------- plumbing ----------

    @staticmethod
    def _bits_to_list(bits):
        return [bool(bits[i]) for i in range(bits.length)]

    def _map_points(self):
        """offset -> (x, y, invert) for every data/correction module."""
        self.pos_of = {}
        self.fixed = [[False] * self.n for _ in range(self.n)]
        for y, row in enumerate(self.canvas.points):
            for x, pt in enumerate(row):
                self.fixed[y][x] = pt.fill if not pt.invert else not pt.fill
                if pt.type in (QrPointType.DATA, QrPointType.CORRECTION):
                    self.pos_of[pt.offset] = (x, y, bool(pt.invert))

    def _block_ranges(self):
        di, eci = 0, self.dcwc_bits
        for bi in range(self.args.bc):
            dbc = self.args.dcwcof(bi) * BIT_PER_CW
            yield bi, di, dbc, eci, self.ecbc
            di += dbc
            eci += self.ecbc

    @staticmethod
    def _gen_basis(dbc, ecbc):
        """vs[i] = e_i || RS(e_i), as an int, bit j counted from the left."""
        L = dbc + ecbc
        out = []
        for i in range(dbc):
            b = [0] * (i // 8) + [1 << (7 - i % 8)] + [0] * (dbc // 8 - i // 8 - 1)
            b = b + list(RSEncoder.encode(b, ecbc // BIT_PER_CW, False))
            out.append(int.from_bytes(bytes(b), "big"))
        return out, L

    # ---------- the one-time elimination ----------

    def _build(self):
        cx = cy = (self.n - 1) / 2
        self.blocks = []

        for bi, di, dbc, eci, ecbc in self._block_ranges():
            L = dbc + ecbc
            vs, _ = self._gen_basis(dbc, ecbc)

            def glob(j):
                return di + j if j < dbc else eci + (j - dbc)

            # Pinned first, each to a required value:
            #   - data bits outside the writable window keep their base value
            #     (they carry the mode indicators, the URL, and the padding)
            #   - the top bit of each numeric group is zeroed, capping the group
            #     at 511 so it is always legal numeric and never needs a retry
            forced = {}
            for j in range(dbc):
                g = di + j
                if g < self.num_start or g >= self.upper:
                    forced[j] = self.base_bits[g]
            for g in range(0, self.numbers_count, 3):
                width = 10 if g + 3 <= self.numbers_count else [0, 4, 7][self.numbers_count - g]
                off = self.num_start + g // 3 * 10
                if width and di <= off < di + dbc:
                    forced[off - di] = False

            # Then everything else.  Whichever positions fall past the end of the
            # pivot budget are the ones that go uncontrolled, so this order is
            # really a choice about WHERE the leftover noise lands.
            R2 = (0.7548776662466927, 0.5698402909980532)   # low-discrepancy
            tex = TEXTURES.get(self.order)

            def rank(j):
                p = self.pos_of.get(glob(j))
                if p is None:
                    return math.inf
                x, y = p[0], p[1]
                if self.order == "centre":
                    return math.hypot(x - cx, y - cy)
                if tex is None:
                    # a well-spread per-module value: any prefix of this order is a
                    # uniform scatter, so the remainder is a uniform scatter too
                    return (x * R2[0] + y * R2[1]) % 1.0
                v = _value_noise(x / tex["sx"], y / tex["sy"], tex["seed"])
                if tex["oct2"]:
                    v += tex["oct2"] * _value_noise(
                        x / (tex["sx"] / 2), y / (tex["sy"] / 2), tex["seed"] + 101)
                return v

            rest = sorted((j for j in range(L) if j not in forced), key=rank)
            order = list(forced) + rest

            pivots, us = [], []
            free = list(vs)
            for j in order:
                hit = next((k for k, v in enumerate(free) if (v >> (L - 1 - j)) & 1), None)
                if hit is None:
                    continue
                u = free.pop(hit)
                free = [v ^ u if (v >> (L - 1 - j)) & 1 else v for v in free]
                us = [w ^ u if (w >> (L - 1 - j)) & 1 else w for w in us]
                pivots.append(j)
                us.append(u)

            self.blocks.append({
                "bi": bi, "di": di, "dbc": dbc, "eci": eci, "ecbc": ecbc, "L": L,
                "pivots": pivots, "us": us, "forced": forced,
                "glob": [glob(j) for j in range(L)],
            })

    # ---------- per-frame solve ----------

    def solve(self, want):
        """want: dict module (x,y) -> bool ink. Returns the full bool matrix."""
        bits = list(self.base_bits)
        for blk in self.blocks:
            L, acc = blk["L"], 0
            cur = 0
            for j in range(L):
                if bits[blk["glob"][j]]:
                    cur |= 1 << (L - 1 - j)
            for j, u in zip(blk["pivots"], blk["us"]):
                if j in blk["forced"]:
                    d = blk["forced"][j]
                else:
                    g = blk["glob"][j]
                    p = self.pos_of.get(g)
                    if p is None:
                        continue
                    x, y, inv = p
                    v = want.get((x, y))
                    if v is None:
                        continue
                    d = (not v) if inv else v     # module ink -> stored bit
                have = bool((cur ^ acc) >> (L - 1 - j) & 1)
                if have != d:
                    acc ^= u
            cur ^= acc
            for j in range(L):
                bits[blk["glob"][j]] = bool((cur >> (L - 1 - j)) & 1)

        m = [row[:] for row in self.fixed]
        for off, (x, y, inv) in self.pos_of.items():
            b = bits[off]
            m[y][x] = (not b) if inv else b
        return m, bits
