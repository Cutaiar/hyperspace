"""Four-dimensional subjects to draw into QR data.

`tesseract.py` does one shape; this generalises it to a family. The projection
and rendering maths is the same code -- imported, not copied -- so a subject
here lands on the module grid exactly the way the tesseract already does.

Only edges that quantise to 0, 45 or 90 degrees survive sampling on a coarse
square grid; everything else staircases into a blob. So the orientations below
are not arbitrary pretty rotations, they are the ones that keep a subject's
edge set on those angles. Each subject's vertices are normalised to
circumradius 1, which keeps one set of camera distances usable for all of them.
"""
import itertools
import math

from PIL import Image, ImageDraw

from tesseract import _project

TAU = 2 * math.pi


def _norm(verts):
    """Scale to circumradius 1 so one camera distance suits every subject."""
    r = max(math.sqrt(sum(c * c for c in v)) for v in verts)
    return [tuple(c / r for c in v) for v in verts]


def _by_length(verts, want=None, eps=1e-6):
    """Edges = the vertex pairs at the shortest distance (or a chosen one)."""
    d2 = {}
    for i, j in itertools.combinations(range(len(verts)), 2):
        s = sum((a - b) ** 2 for a, b in zip(verts[i], verts[j]))
        d2[(i, j)] = s
    target = want if want is not None else min(d2.values())
    return [ij for ij, s in d2.items() if abs(s - target) < eps]


def _tesseract():
    v = _norm(list(itertools.product((-1, 1), repeat=4)))
    e = [(i, j) for i, j in itertools.combinations(range(16), 2)
         if sum(a != b for a, b in zip(v[i], v[j])) == 1]
    return v, e


def _cell16():
    """The tesseract's dual: 8 vertices on the axes, every non-opposite pair joined."""
    v = _norm([tuple(s if k == ax else 0 for k in range(4))
               for ax in range(4) for s in (1, -1)])
    e = [(i, j) for i, j in itertools.combinations(range(8), 2) if i // 2 != j // 2]
    return v, e


def _cell24():
    """All permutations of (+-1, +-1, 0, 0) -- self-dual, 96 edges, very dense."""
    v = []
    for i, j in itertools.combinations(range(4), 2):
        for si, sj in itertools.product((1, -1), repeat=2):
            p = [0, 0, 0, 0]
            p[i], p[j] = si, sj
            v.append(tuple(p))
    v = _norm(v)
    return v, _by_length(v)


def _cell5():
    """The 4-simplex: five vertices, ten edges, no axis to align to."""
    v = _norm([(1, 1, 1, -1 / math.sqrt(5)), (1, -1, -1, -1 / math.sqrt(5)),
               (-1, 1, -1, -1 / math.sqrt(5)), (-1, -1, 1, -1 / math.sqrt(5)),
               (0, 0, 0, 4 / math.sqrt(5))])
    return v, list(itertools.combinations(range(5), 2))


def _duoprism(m, k):
    """An m-gon times a k-gon. 4x4 is the tesseract; 8-gons bring 45 degree edges."""
    v, e = [], []
    for i in range(m):
        for j in range(k):
            a, b = TAU * i / m, TAU * j / k
            v.append((math.cos(a), math.sin(a), math.cos(b), math.sin(b)))
    idx = lambda i, j: (i % m) * k + (j % k)
    for i in range(m):
        for j in range(k):
            e.append(tuple(sorted((idx(i, j), idx(i + 1, j)))))
            e.append(tuple(sorted((idx(i, j), idx(i, j + 1)))))
    return _norm(v), sorted(set(e))


def _cube():
    """A plain 3-cube sitting in the w=0 hyperplane: square inside a square."""
    v = _norm([(x, y, z, 0) for x, y, z in itertools.product((-1, 1), repeat=3)])
    e = [(i, j) for i, j in itertools.combinations(range(8), 2)
         if sum(a != b for a, b in zip(v[i], v[j])) == 1]
    return v, e


SUBJECTS = {
    "tesseract": _tesseract(),
    "cell16":    _cell16(),
    "cell24":    _cell24(),
    "cell5":     _cell5(),
    "duo48":     _duoprism(4, 8),
    "duo88":     _duoprism(8, 8),
    "duo38":     _duoprism(3, 8),
    "cube":      _cube(),
}

R45 = math.pi / 4


# Each entry is the camera and pose for one still. `angles` keys are rotation
# planes over the axes (0,1,2,3) = (x,y,z,w); w_dist/z_dist set how far the
# nested copies separate, which is the whole look of a straight-on projection.
POSES = {
    # --- tesseract: the committed family, plus deeper and shallower nestings ---
    "tess_nested":    ("tesseract", {}, 7.0, 3.0, 0.10),
    "tess_tilt":      ("tesseract", {(0, 1): R45}, 7.0, 3.0, 0.06),
    "tess_wide":      ("tesseract", {}, 9.0, 2.6, 0.08),
    "tess_deep":      ("tesseract", {}, 4.2, 2.2, 0.10),
    "tess_tilt_deep": ("tesseract", {(0, 1): R45}, 4.2, 2.2, 0.06),
    "tess_shallow":   ("tesseract", {}, 14.0, 4.0, 0.12),

    # --- 16-cell: its z and w vertices project to the origin, so it reads as a
    #     cross inside a diamond, or square-with-an-X once turned ---
    "c16_star":       ("cell16", {}, 6.0, 3.0, 0.08),
    "c16_tilt":       ("cell16", {(0, 1): R45}, 6.0, 3.0, 0.08),

    # --- 24-cell: 96 edges, so it wants version 15 and a 2-module stroke ---
    "c24_tilt":       ("cell24", {(0, 1): R45}, 8.0, 3.4, 0.08),

    # --- duoprisms: octagonal rings, every edge on an axis or a 45 ---
    "duo48_flat":     ("duo48", {}, 7.0, 3.0, 0.08),
    "duo88_flat":     ("duo88", {}, 7.0, 3.0, 0.08),
    "duo88_tilt":     ("duo88", {(0, 1): math.pi / 8}, 7.0, 3.0, 0.08),

    # --- a 3-cube, for contrast with the genuinely four-dimensional ones ---
    "cube_flat":      ("cube", {}, 7.0, 3.0, 0.12),
    "cube_tilt":      ("cube", {(0, 1): R45}, 7.0, 3.0, 0.10),
}

# Subjects with no pose here are not oversights. The 5-cell has no axis to
# align to and its edges staircase at any angle; the 3-8 duoprism's triangles
# do the same; the 24-cell seen cell-first fills solid; and folding the
# tesseract in XW mid-way (an angle that is neither 0 nor 45) turns its edges
# into dotted staggers. Each was rendered and rejected by eye at 65 modules.


def render(n, subject="tesseract", angles=None, stroke=3, margin=0.10,
           supersample=8, w_dist=7.0, z_dist=3.0, span=None):
    """One projection of `subject` at n x n modules, stroke given in modules."""
    verts, edges = SUBJECTS[subject]
    angles = angles or {}
    pts = [_project(v, angles, w_dist, z_dist) for v in verts]
    if span is None:
        span = max(max(abs(x), abs(y)) for x, y in pts)
    scale = (n * (1 - 2 * margin)) / (2 * (span or 1.0))

    s = supersample
    img = Image.new("L", (n * s, n * s), 255)
    d = ImageDraw.Draw(img)
    xy = [((x * scale + n / 2) * s, (y * scale + n / 2) * s) for x, y in pts]
    w = max(1, int(round(stroke * s)))
    for a, b in edges:
        d.line([xy[a], xy[b]], fill=0, width=w)
    r = w / 2
    for x, y in xy:
        d.ellipse([x - r, y - r, x + r, y + r], fill=0)

    return img.resize((n, n), Image.LANCZOS).point(lambda p: 0 if p < 150 else 255)


def pose(n, name, stroke=3, **over):
    """Render a named pose from POSES."""
    subject, angles, w, z, margin = POSES[name]
    kw = dict(subject=subject, angles=angles, w_dist=w, z_dist=z,
              margin=margin, stroke=stroke)
    kw.update(over)
    return render(n, **kw)
