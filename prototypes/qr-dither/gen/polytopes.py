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

# --- the taxonomy ---------------------------------------------------------
#
# The subjects above are not a flat list: they are members of families, and a
# family is the useful unit for exploring them, because what survives module
# quantisation is a property of the family's edge set rather than of any one
# solid. Hypercubes have edges on the axes, so they survive; duoprisms built
# from octagons put every edge on an axis or a 45, so they survive; a simplex
# has neither and never will.
#
# `dim` is declared rather than measured: a 3-cube lives in the w = 0
# hyperplane, so its vertices are still 4-tuples. Vertex and edge counts are
# NOT declared -- they come off SUBJECTS, so they cannot drift from the shape.

FAMILIES = [
    ("hypercube", "Hypercubes",
     "The measure polytopes. Every edge runs along an axis, which is exactly "
     "what a square module grid samples cleanly, and is why this family is the "
     "one the prototype is built around.",
     ["cube", "tesseract"]),
    ("orthoplex", "Cross-polytopes",
     "The duals of the hypercubes: vertices on the axes, every non-opposite "
     "pair joined. Several vertices project to the same point, so they read as "
     "a figure inside a diamond rather than as nested cells.",
     ["cell16"]),
    ("duoprism", "Duoprisms",
     "An m-gon times a k-gon. The angles available are the polygons' own, so "
     "octagons work (every edge on an axis or a 45) and triangles do not.",
     ["duo38", "duo48", "duo88"]),
    ("simplex", "Simplexes",
     "The minimum solid in each dimension. No two edges are parallel and none "
     "aligns to an axis, which is the one thing this grid cannot draw.",
     ["cell5"]),
    ("exceptional", "The 24-cell",
     "Self-dual, 96 edges, and no analogue in any other dimension \u2014 it is its "
     "own family. The densest subject here that still reads.",
     ["cell24"]),
]

SUBJECT_LABELS = {
    "cube":      ("3-cube", 3),
    "tesseract": ("Tesseract (4-cube)", 4),
    "cell16":    ("16-cell", 4),
    "cell24":    ("24-cell", 4),
    "cell5":     ("5-cell", 4),
    "duo38":     ("3-8 duoprism", 4),
    "duo48":     ("4-8 duoprism", 4),
    "duo88":     ("8-8 duoprism", 4),
}

# Subjects and orientations with no pose above are not oversights. Each was
# rendered and rejected by eye at 65 modules, and the reason is the useful
# part: an absence with no reason written down gets re-explored by whoever
# comes next. Two kinds live here -- a subject that has no viable orientation
# at all, and an orientation of a subject that does.
REJECTED = {
    "cell5":     [("any orientation",
                   "No axis to align to, so its edges staircase at every angle.")],
    "duo38":     [("any orientation",
                   "The triangular ring's edges never land on 0, 45 or 90; they "
                   "staircase the way the octagonal ones do not.")],
    "cell24":    [("cell first",
                   "Fills solid. 96 edges with no gaps left for a reader.")],
    "tesseract": [("folded part-way through XW",
                   "An angle that is neither 0 nor 45, so every edge becomes a "
                   "dotted stagger.")],
}


def taxonomy():
    """Families, their members, and what each member is -- for the manifest.

    Counts come off SUBJECTS and the pose list comes off POSES, so this cannot
    describe a shape that is not there or miss one that is.
    """
    out = []
    for fid, label, note, members in FAMILIES:
        subjects = []
        for sid in members:
            verts, edges = SUBJECTS[sid]
            name, dim = SUBJECT_LABELS[sid]
            subjects.append({
                "id": sid, "label": name, "dim": dim,
                "vertices": len(verts), "edges": len(edges),
                "poses": [p for p, (s, *_) in POSES.items() if s == sid],
                "rejected": [{"pose": p, "why": w} for p, w in REJECTED.get(sid, [])],
            })
        out.append({"id": fid, "label": label, "note": note, "subjects": subjects})
    return out


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
