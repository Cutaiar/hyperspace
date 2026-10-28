#!/usr/bin/env python3
"""Plan 37 C4 (the dry run of P2): the 17 face patterns on the faces of a
shape, for the owner to judge by eye (D1), and the migration map
`dropped → nearest kept` that P2 executes once he names the list.

Not plan 22's `tools/pattern_sheet.py` (one face's pattern alone, a tile per
input value): here each pattern is drawn **on the faces of a shape, as a
show draws it** — a factory preset loaded through the real `Presets` over a
scratch library home (`tools/golden_frames.py`'s `Rig`: HYPERSPACE_HOME is
a temporary folder before anything is imported, the library home another;
nothing reads or writes ~/Hyperspace or the Drive library), its own
`pattern → shape.faces` wire drawn, the hands absent, then the mode set on
`view.pattern` and drawn through `Renderer.draw_outputs` for `FRAMES`
frames on the pinned clock, so an animated pattern is past its first frame.

What a tile shows, the same for every mode (only `view.pattern` differs):
- `view.pattern_mix` 1.0 — the pattern alone on the faces, not the
  preset's blend with the plain fill;
- the eight inputs where the factory routes leave them on a **medium
  passage** (plan 22 B3's MEDIUM bands: lane i pushes input i at
  `routing.PATTERN_DEPTH` on a base of 1; HUE and SPREAD at 1.0) — the
  factory pattern depth, set as the inputs' bases since the rig's analyzer
  is never fed;
- the analyzer's lanes as the renderer reads them (`Renderer.bands`) at
  the same passage, which only METER and PULSE draw.

Two sheets, because one shape does not show every mode's character:
`party-faces` (a tesseract turning in 4D, many small faces seen through
each other: how a pattern reads as a texture across a solid) and
`plasma-heart` (the Heart, one big flat face: the pattern's own design,
large). Each writes one PNG per mode and a labelled sheet in
`patterns.NAMES` order.

The migration map (`docs/plans/assets/37-faces/migration-map.md`) is
generated, never hand-edited: what each mode draws and its ranked nearest
neighbours are data here (`DRAWS`, `NEAREST`); which presets use each mode
— with the faces wire drawn, with the faces off, or carried unwired — is
read off every factory preset and every fixture as the real loader lands
them (`usage`). `--check` regenerates it and fails when the file differs
(tests/test_faces_map.py runs it), so the map cannot rot silently.

    uv run python tools/faces_sheets.py            # sheets + map
    uv run python tools/faces_sheets.py --map      # the map only (no GL)
    uv run python tools/faces_sheets.py --check    # exit 1 if the map is stale
    uv run python tools/faces_sheets.py --frames 3 --only RINGS,HEX

Writes, under docs/plans/assets/37-faces/:
  <NAME>.png            one per mode on party-faces, 480×300 (the frame's
                        middle at full resolution, where the shape sits)
  sheet.png             all 17 on party-faces, labelled
  heart-sheet.png       all 17 on plasma-heart's Heart, labelled
  migration-map.md      the map
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "tools", ROOT / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# golden_frames points HYPERSPACE_HOME at a temporary folder on import,
# before anything of hyperspace's is imported (unless the tests' conftest
# already chose one that is not the owner's real home)
import golden_frames as gf

from hyperspace import graph as G
from hyperspace.bands import CEIL
from hyperspace.patterns import MODES, N_INPUTS, NAMES
from hyperspace.routing import PATTERN_DEPTH

OUT = ROOT / "docs" / "plans" / "assets" / "37-faces"
MAP = OUT / "migration-map.md"
FACTORY = ROOT / "hyperspace" / "library" / "presets"
FIXTURES = ROOT / "tests" / "fixtures" / "presets"

FRAMES = 3                    # frames drawn before the read: past the first
TILE = (480, 300)             # a mode's PNG and a sheet's tile, half the rig's 960×600
LABEL_H = 22
# (sheet file, the preset it is drawn on, what it shows, values set over
# the preset's own for every mode). The Heart is lit at party-faces'
# brightness (plasma-heart's own 1.2 leaves the face too dim to judge)
SHEETS = (("sheet.png", "party-faces",
           "a tesseract turning in 4D: many small faces, seen through each other", {}),
          ("heart-sheet.png", "plasma-heart",
           "the Heart: one big flat face, the pattern's design large (lit at bright 2.5)",
           {"view.bright": 2.5}))
# plan 22 B3's medium passage (tools/pattern_sheet.py MEDIUM): every band
# near nominal, in fader units (out); SUB BASS MIDB MID UPR AIR
MEDIUM = (1.00, 1.00, 0.70, 0.90, 0.60, 0.60)


def factory_inputs(out=MEDIUM, depth: float = PATTERN_DEPTH) -> list[float]:
    """The eight inputs as the factory routes leave them for lanes `out`
    (tools/pattern_sheet.py's rule): lane i pushes input i at `depth` of
    the 0–2.6 range on a base of 1, held to the range; HUE and SPREAD 1."""
    mods = [1.0] * N_INPUTS
    for i, o in enumerate(out):
        mods[i] = min(max(1.0 + depth * o / CEIL * 2.6, 0.0), 2.6)
    return mods


# ---- the map's data: what each mode draws, and its nearest neighbours ----

# one line per mode: what it draws on a face (patterns.glsl's design())
DRAWS: dict[str, str] = {
    "FLAT": "No pattern: a plain white fill, tinted by the shape's own colour; reads no input.",
    "RINGS": "Concentric rings from the face centre, beaten by a second ring set into "
             "travelling bands; the hue cycles along the ring phase.",
    "PLAID": "Two crossing straight-stripe wave systems, warm red on one axis and cool "
             "blue on the other, adding where they agree and going dark where they cancel.",
    "MOIRE": "Two near-equal straight stripe fields at a slight angle, beating into broad "
             "moiré bands; a teal–magenta duotone.",
    "BLOOM": "A single ring of seven petals round the centre, turning, the hue round the "
             "wheel; the middle and the corners dark.",
    "CAUSTIC": "Deep water: dark-blue troughs and bright cyan-white filaments where three "
               "sine swells cross.",
    "HEX": "A honeycomb of round cells, each flashing on its own phase in its own hue.",
    "SPIRAL": "Five galaxy arms winding out of a hot white core, the colour running out "
              "along the arms.",
    "CELLS": "Voronoi cells: drifting nuclei, each cell a flat hue, bright white "
             "membranes between them.",
    "PLASMA": "The classic folded sine field: soft rainbow contour bands flowing over "
              "the whole face.",
    "WEAVE": "Orange warp and blue weft ribbons interlaced over and under on a checker, "
             "breathing.",
    "EMBER": "Rising fractal noise: dark coals under ash, glowing orange, white-hot "
             "where it peaks.",
    "METER": "The bands themselves: a radial LED equaliser, a spectrum-coloured wedge "
             "per band lit out from the hub as far as it reads (dark tracks in silence).",
    "PULSE": "The beat as shapes: a magenta kick disc throwing a ring, yellow snare "
             "rays, cyan hat sparkle; an idle heartbeat in silence.",
    "MARBLE": "Domain-warped noise folded through itself: lapis ink, teal currents and "
              "fine gold veins, flowing.",
    "TRUCHET": "A maze of quarter-circle arcs on a navy checker, tiles flipping, a "
               "neon cyan-to-magenta current running along the paths.",
    "KALEIDO": "Six mirrored wedges of flat pop colour — magenta, yellow, cyan, black "
               "bands and dots — turning, hard-edged.",
}

# For each mode, its neighbours by look, nearest first, with one line on
# why. The ranking rule (register-row draft in the C4 decisions): (1) the
# same structure on the face — radial about the centre, a straight-line
# lattice, a cell lattice, a flowing field, a band reader — then (2) the
# same palette and light (dark ground with bright lines, or a full fill),
# then (3) the same motion. FLAT has no neighbour by look but RINGS is the
# plainest fill-the-face pattern; any mode's list names three so that
# whichever subset is kept, the first kept name in the list is the answer
# (and `nearest_kept` falls back to the first kept mode in NAMES order).
NEAREST: dict[str, tuple[tuple[str, str], ...]] = {
    "FLAT": (("PLASMA", "a full, soft fill of the face, the least 'pattern' of the rest"),
             ("CAUSTIC", "a full fill of one cool hue family"),
             ("EMBER", "a full fill, dark to bright, no hard lines")),
    "RINGS": (("BLOOM", "radial about the face centre, the hue riding round it"),
              ("SPIRAL", "radial, lines leaving the centre, the colour running outward"),
              ("MOIRE", "beating line fields into travelling bands")),
    "PLAID": (("WEAVE", "a straight warm/cool lattice crossing at right angles"),
              ("MOIRE", "straight stripe fields interfering into dark and bright"),
              ("TRUCHET", "a square tile lattice of lines on a dark ground")),
    "MOIRE": (("PLAID", "straight stripe fields interfering"),
              ("RINGS", "two line systems beating into bands"),
              ("CAUSTIC", "interfering sine fields, a two-tone cool palette")),
    "BLOOM": (("KALEIDO", "radial symmetry about the centre, turning, round the wheel"),
              ("SPIRAL", "radial arms about a centre, turning"),
              ("RINGS", "radial about the centre, hue round the phase")),
    "CAUSTIC": (("MARBLE", "flowing liquid lines on deep blue, bright filaments"),
                ("PLASMA", "summed sine fields flowing over the whole face"),
                ("MOIRE", "interfering sine stripes, a cool duotone")),
    "HEX": (("CELLS", "a lattice of cells each in its own hue"),
            ("TRUCHET", "a regular tile lattice that flips and flows"),
            ("METER", "discrete segments each lit on its own")),
    "SPIRAL": (("BLOOM", "radial about a centre, turning, hue round the wheel"),
               ("RINGS", "radial lines out from the centre"),
               ("KALEIDO", "radial symmetry, turning")),
    "CELLS": (("HEX", "a lattice of cells each in its own hue"),
              ("MARBLE", "organic, drifting, bright veins between darker regions"),
              ("TRUCHET", "a tiling with bright paths along its edges")),
    "PLASMA": (("MARBLE", "a flowing noise/sine field over the whole face"),
               ("CAUSTIC", "summed sine fields flowing"),
               ("EMBER", "a soft flowing field, no hard edges")),
    "WEAVE": (("PLAID", "a straight warm/cool lattice crossing at right angles"),
              ("TRUCHET", "a square tile lattice of ribbons and paths"),
              ("HEX", "a regular lattice of discrete elements")),
    "EMBER": (("MARBLE", "fractal noise flowing, bright veins out of dark"),
              ("PLASMA", "a soft flowing field over the whole face"),
              ("CAUSTIC", "bright where it peaks out of a dark ground")),
    "METER": (("PULSE", "the other mode that draws the bands themselves"),
              ("BLOOM", "radial wedges round the centre, hue round the wheel"),
              ("KALEIDO", "radial wedges of flat colour, turning")),
    "PULSE": (("METER", "the other mode that draws the bands themselves"),
              ("RINGS", "rings thrown out from the centre"),
              ("BLOOM", "a radial shape about the centre, on black")),
    "MARBLE": (("CAUSTIC", "flowing liquid lines on deep blue"),
               ("EMBER", "fractal noise flowing, bright veins out of dark"),
               ("PLASMA", "a flowing field over the whole face")),
    "TRUCHET": (("WEAVE", "a square lattice of ribbons crossing"),
                ("HEX", "a regular tile lattice"),
                ("PLAID", "a straight lattice of lines on dark")),
    "KALEIDO": (("BLOOM", "radial symmetry about the centre, turning, saturated"),
                ("SPIRAL", "radial, turning"),
                ("METER", "radial wedges of flat colour")),
}


def nearest_kept(mode: str, kept) -> str:
    """The mode a preset on `mode` migrates to when only `kept` stay: the
    first kept name in `mode`'s ranked list, else the first kept mode in
    NAMES order (FLAT, when kept, is never chosen for a patterned mode
    unless nothing else is)."""
    kept = [k for k in NAMES if k in set(kept)]
    if not kept:
        raise ValueError("no mode kept")
    if mode in kept:
        return mode
    for name, _ in NEAREST[mode]:
        if name in kept:
            return name
    rest = [k for k in kept if k != "FLAT"]
    return (rest or kept)[0]


# ---- the usage table, read by code ----

@dataclass(frozen=True)
class Use:
    """One preset's pattern, as the real loader lands it."""

    slug: str
    where: str            # "factory" or "fixture"
    schema: str           # the file's schema ("/7")
    mode: int             # view.pattern after the load
    faces_on: bool        # view.faces after the load
    path: tuple[str, ...]  # pattern → … → shape.faces as drawn; () unwired
    elsewhere: tuple[str, ...]   # other ports the pattern's picture goes into
    driven: tuple[str, ...]      # route/desk/macro rows that set view.pattern

    @property
    def name(self) -> str:
        return NAMES[self.mode] if 0 <= self.mode < len(NAMES) else f"#{self.mode}"

    @property
    def state(self) -> str:
        """"on screen", "faces off" (wired, faces hidden) or "unwired"."""
        if not self.path:
            return "unwired"
        return "on screen" if self.faces_on else "faces off"


def _path_to_faces(wires) -> tuple[str, ...]:
    """The nodes from `pattern` to `shape.faces` along drawn wires (any
    input port, a pin read as its node), `pattern` first; () if the
    pattern's picture does not reach the faces."""
    into: dict[str, list[str]] = {}
    for w in wires:
        into.setdefault(w.node, []).append(w.src)
        if G.pin_node(w.src) is not None:
            into.setdefault(w.src, []).append(G.pin_node(w.src))
    start = [w.src for w in wires if w.dst == "shape.faces"]
    parent: dict[str, str | None] = {s: None for s in start}
    todo = list(start)
    while todo:
        name = todo.pop(0)
        if name == "pattern":
            out = [name]
            while parent[out[-1]] is not None:
                out.append(parent[out[-1]])
            return (*out, "shape.faces")
        for src in into.get(name, ()):
            if src not in parent:
                parent[src] = name
                todo.append(src)
    return ()


def _driven(doc: dict) -> tuple[str, ...]:
    """The rows in a preset file that set `view.pattern`: its routes, desk
    and macros (`source op`)."""
    rows = []
    for key in ("routes", "desk"):
        for r in doc.get(key) or []:
            if isinstance(r, dict) and r.get("target") == "view.pattern":
                rows.append(f"{key}: {r.get('source')} {r.get('op')}")
    for m in doc.get("macros") or []:
        for s in (m.get("subs") or m.get("targets") or []) if isinstance(m, dict) else []:
            if isinstance(s, dict) and s.get("target") == "view.pattern":
                rows.append(f"macro {m.get('name', '?')}")
    return tuple(rows)


def usage() -> list[Use]:
    """Every factory preset and every fixture under tests/fixtures/presets/,
    each loaded through the real `Presets` over a scratch library (the
    golden rig's headless `Loader`, every fixture copied in), read for its
    landed mode, faces switch and wires."""
    loader = gf.Loader()
    own = Path(loader._home.name) / "presets"
    for f in sorted(FIXTURES.glob("*.json")):          # every one, not just the goldens'
        (own / f.name).write_text(f.read_text())
    out = []
    try:
        for where, folder in (("factory", FACTORY), ("fixture", FIXTURES)):
            for f in sorted(folder.glob("*.json")):
                doc = json.loads(f.read_text())
                _, _, effects, free = loader.load(f.stem)
                spec = G.read_graph(free or {}, effects={e.partition(".")[0] for e in effects})
                wires = list(spec.all_wires())
                path = _path_to_faces(wires)
                elsewhere = tuple(sorted(w.dst for w in wires if w.src == "pattern"
                                         and w.dst != "shape.faces"
                                         and (not path or w.node != path[1])))
                out.append(Use(f.stem, where, str(doc.get("schema", "")).rpartition("/")[2],
                               int(loader.view.pattern), bool(loader.view.faces), path,
                               elsewhere, _driven(doc)))
    finally:
        loader.close()
    return out


# ---- the map ----

def render_map(uses: list[Use]) -> str:
    by_mode: dict[str, list[Use]] = {n: [] for n in NAMES}
    for u in uses:
        by_mode.setdefault(u.name, []).append(u)

    def names(us, state):
        got = [f"`{u.slug}`" + (f" (via {' → '.join(u.path[1:-1])})" if len(u.path) > 2 else "")
               for u in us if u.state == state]
        return ", ".join(got) or "—"

    lines = [
        "# The face patterns: the migration map (plan 37 P2, dry run)",
        "",
        "Generated by `tools/faces_sheets.py --map`; **do not edit by hand** —",
        "`tests/test_faces_map.py` fails when this file and the presets disagree.",
        "The sheets beside it (`sheet.png` on `party-faces`' tesseract,",
        "`heart-sheet.png` on `plasma-heart`'s Heart, one `<NAME>.png` per mode) are",
        "what the owner judges D1 from; nothing has been removed.",
        "",
        "**How to read it.** For each mode: what it draws; the presets that show",
        "it — *on screen* (a `pattern → … → shape.faces` wire drawn and the faces",
        "on), *faces off* (the wire drawn, `view.faces` off: nothing shows until a",
        "performer turns the faces on) and *unwired* (the mode is carried, the",
        "faces read nothing from the pattern: dropping it changes nothing on",
        "screen); and its nearest neighbours by look, nearest first. Whichever",
        "subset the owner keeps, a dropped mode's presets move to the **first kept",
        "name in its list** (`faces_sheets.nearest_kept`).",
        "",
        "**The ranking rule**: the same structure on the face first (radial about",
        "the centre; a straight-line lattice; a cell lattice; a flowing field; a",
        "reader of the bands), then the same palette and light (bright lines on a",
        "dark ground, or a full fill), then the same motion.",
        "",
        "**Beyond the presets.** The desk rows in the *driven* column below put",
        "`view.pattern` on a knob (`abs`), so a performer sweeps every mode there;",
        "after P2 the knob's throw is the kept list. Presets in the owner's Drive",
        "library are not read here (never touched by a build); P2 migrates them",
        "with the same table, on the owner's say, the way plan 36's",
        "`tools/migrate_library.py` moved it to `/7` (backup first).",
        "",
        f"Inputs on the sheets: the factory pattern depth ({PATTERN_DEPTH}) on a medium",
        "passage (plan 22 B3's MEDIUM bands), `view.pattern_mix` 1.0,",
        f"{FRAMES} frames in, hands absent; each tile is the frame's middle at full",
        "resolution; the Heart sheet is lit at `view.bright` 2.5.",
        "",
        "## Summary",
        "",
        "| # | mode | on screen | faces off | unwired | nearest (ranked) |",
        "|---|---|---|---|---|---|",
    ]
    for k, n in enumerate(NAMES):
        us = by_mode[n]
        c = {s: sum(u.state == s for u in us) for s in ("on screen", "faces off", "unwired")}
        near = " · ".join(x for x, _ in NEAREST[n])
        lines.append(f"| {k} | {n} | {c['on screen']} | {c['faces off']} | {c['unwired']} "
                     f"| {near} |")
    lines += ["", "## Per mode", ""]
    for k, n in enumerate(NAMES):
        us = by_mode[n]
        lines += [f"### {k} {n}", "", DRAWS[n], ""]
        if n != "FLAT":
            lines += [f"![{n}]({n}.png)", ""]
        for state in ("on screen", "faces off", "unwired"):
            for where in ("factory", "fixture"):
                lines.append(f"- {state}, {where}: "
                             + names([u for u in us if u.where == where], state))
        lines += ["- nearest kept, in order:"]
        lines += [f"  {i}. **{x}** — {why}" for i, (x, why) in enumerate(NEAREST[n], 1)]
        lines.append("")
    lines += [
        "## Every preset",
        "",
        "As the real loader lands each file (schema as on disk; a fixture of an",
        "older schema is migrated on load). *path* is the drawn run from the",
        "pattern to the faces; *also* any other port the pattern's picture goes",
        "into; *driven* the file's own rows that set `view.pattern`.",
        "",
        "| preset | where | schema | mode | faces | state | path | also | driven |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for u in uses:
        lines.append(
            f"| `{u.slug}` | {u.where} | /{u.schema} | {u.mode} {u.name} "
            f"| {'on' if u.faces_on else 'off'} | {u.state} "
            f"| {' → '.join(u.path) or '—'} | {', '.join(u.elsewhere) or '—'} "
            f"| {'; '.join(u.driven) or '—'} |")
    return "\n".join(lines) + "\n"


def check() -> list[str]:
    """What is stale: the map against the presets, and the data against NAMES."""
    errs = []
    for n in NAMES:
        if n not in DRAWS:
            errs.append(f"DRAWS has no line for {n}")
        near = [x for x, _ in NEAREST.get(n, ())]
        if len(near) < 2 or n in near or any(x not in NAMES for x in near):
            errs.append(f"NEAREST[{n}] must rank two or more other modes: {near}")
    if set(DRAWS) != set(NAMES) or set(NEAREST) != set(NAMES):
        errs.append("DRAWS / NEAREST name a mode NAMES does not")
    want = render_map(usage())
    have = MAP.read_text() if MAP.is_file() else ""
    if have != want:
        errs.append(f"{MAP.relative_to(ROOT)} is stale: run tools/faces_sheets.py --map")
    return errs


# ---- the sheets ----

def shoot(slug: str, modes: list[int], frames: int, over: dict | None = None):
    """{mode: (H, W, 3) uint8, top row first} — preset `slug` on the golden
    rig, hands absent, one fresh rig per mode (so every mode starts on the
    same clock), the mode set, the inputs at the factory depth on a medium
    passage, the mix at 1, then `over`'s values."""
    import numpy as np

    ctx = gf.context()
    states = gf.STATES[:1]                         # scene + hands, as the rig ships
    shots = {}
    with gf.shared_programs(ctx):
        for mode in modes:
            rig = gf.Rig(slug, "absent", ctx)
            try:
                section = gf.rig_section(rig, slug, states, None)
                rig.renderer.wiring = G.read_graph(
                    section, effects={n.partition(".")[0] for n in rig.fx.specs}).wiring()
                rig.reg["view.pattern"].set(mode)
                rig.reg["view.pattern_mix"].set(1.0)
                for k, v in enumerate(factory_inputs()):
                    rig.reg[f"pattern.mod.{k}"].set(v)
                for pid, v in (over or {}).items():
                    rig.reg[pid].set(v)
                rig.renderer.bands = tuple(o / CEIL for o in MEDIUM)
                target = gf._target(ctx, (gf.W, gf.H), gf.SAMPLES)
                views = gf.state_views(slug, states, (gf.W, gf.H), [target])
                for _ in range(frames):
                    rig.frame(views, (gf.W, gf.H), gf.DPR)
                if views[0].error:
                    raise RuntimeError(f"{slug} {NAMES[mode]}: {views[0].error}")
                px = gf._read(ctx, target, (gf.W, gf.H))[::-1, :, :3]
                # the middle TILE of the frame at full resolution: the shape
                # sits in it, twice the size a downscaled frame would give
                y0, x0 = (gf.H - TILE[1]) // 2, (gf.W - TILE[0]) // 2
                shots[mode] = np.ascontiguousarray(px[y0:y0 + TILE[1], x0:x0 + TILE[0]])
                target.release()
            finally:
                rig.close()
                gf._PARK.use()
                gc.collect()
    return shots


def _save(img, path: Path) -> None:
    from PIL import Image

    img = img.convert("RGB").quantize(256, method=Image.Quantize.MEDIANCUT,
                                      dither=Image.Dither.FLOYDSTEINBERG)
    img.save(path, optimize=True)
    print(f"wrote {path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


def sheet(shots: dict, slug: str, about: str, path: Path, cols: int = 5) -> None:
    from PIL import Image, ImageDraw, ImageFont

    tw, th = TILE
    head = 40
    rows = (len(shots) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, head + rows * (th + LABEL_H)), (12, 12, 14))
    d = ImageDraw.Draw(im)
    big, font = ImageFont.load_default(size=20), ImageFont.load_default(size=15)
    d.text((10, 10), f"the face patterns on {slug}: {about}", fill=(232, 232, 232), font=big)
    for i, mode in enumerate(sorted(shots)):
        x, y = (i % cols) * tw, head + (i // cols) * (th + LABEL_H)
        tile = Image.fromarray(shots[mode])
        im.paste(tile, (x, y + LABEL_H))
        d.text((x + 6, y + 3), f"{mode}  {NAMES[mode]}", fill=(232, 232, 232), font=font)
    _save(im, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--map", action="store_true", help="write the migration map only (no GL)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the map is stale")
    ap.add_argument("--frames", type=int, default=FRAMES)
    ap.add_argument("--only", default="", help="modes by name, comma-separated (sheets only)")
    a = ap.parse_args()
    if a.check:
        errs = check()
        for e in errs:
            print(e, file=sys.stderr)
        return 1 if errs else 0
    OUT.mkdir(parents=True, exist_ok=True)
    MAP.write_text(render_map(usage()))
    print(f"wrote {MAP.relative_to(ROOT)}")
    if a.map:
        return 0
    from PIL import Image

    only = [x.strip().upper() for x in a.only.split(",") if x.strip()]
    if bad := [x for x in only if x not in NAMES]:
        ap.error(f"no such mode: {', '.join(bad)} (one of {', '.join(NAMES)})")
    modes = [NAMES.index(x) for x in only] if only else list(range(len(MODES)))
    for k, (name, slug, about, over) in enumerate(SHEETS):
        shots = shoot(slug, modes, a.frames, over)
        if k == 0:
            for mode, px in shots.items():
                _save(Image.fromarray(px), OUT / f"{NAMES[mode]}.png")
        if not only:
            sheet(shots, slug, about, OUT / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
