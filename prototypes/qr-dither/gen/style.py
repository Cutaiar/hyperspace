"""Styled SVG for a solved module matrix.

The vector twin of web/render.js: the same dot shapes, the same neighbour-aware
corner rounding, the same even-odd finder rings -- emitted as SVG so a still can
be printed at any size. Styling is presentation only. It never changes which
modules are ink, so it cannot change what a reader decodes; it can absolutely
change whether a reader manages to read it, which is why gen/gallery.py
rasterises and decodes every file it writes.

One unit in the viewBox is one module, so radii below are fractions of a module.
"""
FINDER = 7


def finders(n):
    return [(0, 0), (n - FINDER, 0), (0, n - FINDER)]


def in_finder(x, y, n):
    return any(fx <= x < fx + FINDER and fy <= y < fy + FINDER
               for fx, fy in finders(n))


DOTS = {
    "square":          {"kind": "cell",   "r": 0.0},
    "rounded":         {"kind": "cell",   "r": 0.25},
    "extra-rounded":   {"kind": "cell",   "r": 0.5},
    "dots":            {"kind": "dot",    "shrink": 0.0},
    "dots-tight":      {"kind": "dot",    "shrink": -0.08},
    "classy":          {"kind": "classy", "r": 0.5, "round": False},
    "classy-rounded":  {"kind": "classy", "r": 0.5, "round": True},
}
EYES = ["square", "rounded", "extra-rounded", "dot"]


def _f(v):
    """Short decimals keep these files small; three places is sub-pixel at print size."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def _cell_path(x, y, r, nb):
    """One module, corners rounded only where it has no orthogonal neighbour on
    both adjacent sides -- what makes runs read as one connected stroke."""
    up, right, down, left = nb
    tl = r if (not up and not left) else 0
    tr = r if (not up and not right) else 0
    br = r if (not down and not right) else 0
    bl = r if (not down and not left) else 0
    p = [f"M{_f(x + tl)} {_f(y)}", f"H{_f(x + 1 - tr)}"]
    if tr:
        p.append(f"A{_f(tr)} {_f(tr)} 0 0 1 {_f(x + 1)} {_f(y + tr)}")
    p.append(f"V{_f(y + 1 - br)}")
    if br:
        p.append(f"A{_f(br)} {_f(br)} 0 0 1 {_f(x + 1 - br)} {_f(y + 1)}")
    p.append(f"H{_f(x + bl)}")
    if bl:
        p.append(f"A{_f(bl)} {_f(bl)} 0 0 1 {_f(x)} {_f(y + 1 - bl)}")
    p.append(f"V{_f(y + tl)}")
    if tl:
        p.append(f"A{_f(tl)} {_f(tl)} 0 0 1 {_f(x + tl)} {_f(y)}")
    return "".join(p) + "Z"


def _classy_path(x, y, r, round_far):
    """Two opposite corners cut: the leaf."""
    p = [f"M{_f(x + r)} {_f(y)}", f"H{_f(x + 1)}", f"V{_f(y + 1 - (r if round_far else 0))}"]
    if round_far:
        p.append(f"A{_f(r)} {_f(r)} 0 0 1 {_f(x + 1 - r)} {_f(y + 1)}")
    p += [f"H{_f(x)}", f"V{_f(y + r)}",
          f"A{_f(r)} {_f(r)} 0 0 1 {_f(x + r)} {_f(y)}"]
    return "".join(p) + "Z"


def _rrect_path(x, y, s, r):
    r = min(r, s / 2)
    if r <= 0:
        return f"M{_f(x)} {_f(y)}h{_f(s)}v{_f(s)}h{_f(-s)}Z"
    return (f"M{_f(x + r)} {_f(y)}H{_f(x + s - r)}"
            f"A{_f(r)} {_f(r)} 0 0 1 {_f(x + s)} {_f(y + r)}"
            f"V{_f(y + s - r)}"
            f"A{_f(r)} {_f(r)} 0 0 1 {_f(x + s - r)} {_f(y + s)}"
            f"H{_f(x + r)}"
            f"A{_f(r)} {_f(r)} 0 0 1 {_f(x)} {_f(y + s - r)}"
            f"V{_f(y + r)}"
            f"A{_f(r)} {_f(r)} 0 0 1 {_f(x + r)} {_f(y)}Z")


def _runs(m, n, quiet):
    """Horizontal runs as rects -- the compact form for unrounded squares."""
    out = []
    for y, row in enumerate(m):
        x = 0
        while x < n:
            if row[x]:
                run = 1
                while x + run < n and row[x + run]:
                    run += 1
                out.append(f'<rect x="{x + quiet}" y="{y + quiet}" width="{run}" height="1"/>')
                x += run
            else:
                x += 1
    return "".join(out)


def to_svg(m, quiet=4, dot="square", eye_frame="square", eye_core="square",
           fg="#000000", fg2=None, bg="#ffffff", plate_radius=0,
           style_eyes=True):
    """A solved matrix as a standalone SVG. `m` is a list of rows of bools."""
    n = len(m)
    side = n + 2 * quiet
    spec = DOTS[dot]
    at = lambda x, y: (0 <= x < n and 0 <= y < n and m[y][x])

    defs = ""
    fill = fg
    if fg2:
        defs = (f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="{fg}"/>'
                f'<stop offset="1" stop-color="{fg2}"/></linearGradient></defs>')
        fill = "url(#g)"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" role="img">']
    if bg:
        r = f' rx="{_f(plate_radius)}"' if plate_radius else ""
        out.append(f'<rect width="{side}" height="{side}" fill="{bg}"{r}/>')
    out.append(defs)

    # Unrounded squares with plain eyes is the one case that needs no paths at
    # all, and merged runs make that file a third the size.
    plain = spec["kind"] == "cell" and spec["r"] == 0 and not style_eyes
    if plain:
        out.append(f'<g fill="{fill}" shape-rendering="crispEdges">{_runs(m, n, quiet)}</g>')
        out.append("</svg>")
        return "\n".join(out)

    body, circles = [], []
    for y in range(n):
        for x in range(n):
            if not m[y][x]:
                continue
            if style_eyes and in_finder(x, y, n):
                continue
            X, Y = x + quiet, y + quiet
            if spec["kind"] == "dot":
                rad = 0.5 * (1 - spec["shrink"])
                circles.append(f'<circle cx="{_f(X + .5)}" cy="{_f(Y + .5)}" r="{_f(rad)}"/>')
            elif spec["kind"] == "classy":
                body.append(_classy_path(X, Y, spec["r"], spec["round"]))
            else:
                body.append(_cell_path(X, Y, spec["r"],
                                       (at(x, y - 1), at(x + 1, y), at(x, y + 1), at(x - 1, y))))

    out.append(f'<g fill="{fill}">')
    if body:
        out.append(f'<path d="{"".join(body)}"/>')
    out += circles

    if style_eyes:
        ring, core = [], []
        for fx, fy in finders(n):
            X, Y, S = fx + quiet, fy + quiet, float(FINDER)
            ro = (S * 0.32 if eye_frame == "extra-rounded" else
                  S * 0.18 if eye_frame == "rounded" else
                  S / 2 if eye_frame == "dot" else 0)
            # outer minus inner, punched with even-odd
            ring.append(_rrect_path(X, Y, S, ro))
            ring.append(_rrect_path(X + 1, Y + 1, S - 2, max(0.0, ro - 1)))
            if eye_core == "dot":
                core.append(f'<circle cx="{_f(X + 3.5)}" cy="{_f(Y + 3.5)}" r="1.5"/>')
            else:
                cr = (3 * 0.34 if eye_core == "extra-rounded" else
                      3 * 0.18 if eye_core == "rounded" else 0)
                core.append(f'<path d="{_rrect_path(X + 2, Y + 2, 3.0, cr)}"/>')
        out.append(f'<path fill-rule="evenodd" d="{"".join(ring)}"/>')
        out += core

    out += ["</g>", "</svg>"]
    return "\n".join(out)
