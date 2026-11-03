"""Tesseract projections rendered at QR-module resolution.

A QArt code can only control the data-region modules, so the target image has to
survive being sampled on a coarse square grid: thin diagonals alias into dotted
staggers.  Everything here is therefore drawn with an explicit stroke width in
*modules*, not pixels, and rendered 1 px per module.
"""
import itertools
import math

from PIL import Image, ImageDraw

VERTICES = list(itertools.product((-1, 1), repeat=4))
EDGES = [
    (i, j)
    for i, a in enumerate(VERTICES)
    for j, b in enumerate(VERTICES)
    if i < j and sum(x != y for x, y in zip(a, b)) == 1
]


def _rot(p, i, j, theta):
    p = list(p)
    c, s = math.cos(theta), math.sin(theta)
    p[i], p[j] = p[i] * c - p[j] * s, p[i] * s + p[j] * c
    return p


def _project(v, angles, w_dist=2.6, z_dist=3.4):
    p = list(v)
    for (i, j), theta in angles.items():
        p = _rot(p, i, j, theta)
    k = w_dist / (w_dist - p[3])          # 4D -> 3D
    p = [p[0] * k, p[1] * k, p[2] * k]
    k = z_dist / (z_dist - p[2])          # 3D -> 2D
    return p[0] * k, p[1] * k


def render(n, angles=None, stroke=3, margin=0.14, supersample=8,
           w_dist=2.6, z_dist=3.4, span=None):
    """One projection at n x n modules, stroke given in modules."""
    angles = angles or {}
    pts = [_project(v, angles, w_dist, z_dist) for v in VERTICES]
    # a span fixed across the whole sweep, or the shape snaps to refill
    # the frame every time its bounding box changes
    if span is None:
        span = max(max(abs(x), abs(y)) for x, y in pts)
    scale = (n * (1 - 2 * margin)) / (2 * (span or 1.0))

    s = supersample
    img = Image.new("L", (n * s, n * s), 255)
    d = ImageDraw.Draw(img)
    xy = [((x * scale + n / 2) * s, (y * scale + n / 2) * s) for x, y in pts]
    w = max(1, int(round(stroke * s)))
    for a, b in EDGES:
        d.line([xy[a], xy[b]], fill=0, width=w)
    # round the joints so edges meet cleanly instead of notching
    r = w / 2
    for x, y in xy:
        d.ellipse([x - r, y - r, x + r, y + r], fill=0)

    return img.resize((n, n), Image.LANCZOS).point(lambda p: 0 if p < 150 else 255)


# A straight-on tesseract is four nested squares: the w- and z-divisions compose.
# Each division shrinks by (d-1)/(d+1), so picking the two distances sets how the
# four squares are spaced.  w_dist 7 -> 0.75, z_dist 3 -> 0.50, giving relative
# sizes 1.00 / 0.75 / 0.50 / 0.375 -- evenly separated instead of the inner pair
# collapsing into each other.
PRESETS = {
    "nested":      {"angles": {}},
    "tilted":      {"angles": {(0, 3): 0.62, (1, 2): 0.30}},
    "unfolding":   {"angles": {(0, 3): 1.05, (2, 3): 0.42, (0, 1): 0.22}},
    "edge_on":     {"angles": {(0, 3): math.pi / 4, (1, 3): 0.35}},
    "nested_open": {"angles": {}, "w_dist": 7.0, "z_dist": 3.0, "margin": 0.10},
    "nested_wide": {"angles": {}, "w_dist": 9.0, "z_dist": 2.6, "margin": 0.08},
    "nested_tilt": {"angles": {(0, 1): 0.7854}, "w_dist": 7.0, "z_dist": 3.0, "margin": 0.06},
}


def max_span(w_dist=2.6, z_dist=3.4, samples=3000, seed=0):
    """Widest the shape gets over all orientations, for a fixed scale."""
    import random
    rng = random.Random(seed)
    planes = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3)]
    best = 0.0
    for _ in range(samples):
        a = {p: rng.uniform(0, 2 * math.pi) for p in planes}
        for x, y in (_project(v, a, w_dist, z_dist) for v in VERTICES):
            best = max(best, abs(x), abs(y))
    return best
