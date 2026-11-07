/** Styled geometry for a solved module matrix — the TypeScript twin of
 *  `gen/style.py`, which is itself the vector twin of `lib/render.js`.
 *
 *  Same dot shapes, the same neighbour-aware corner rounding, the same
 *  even-odd finder rings, the same gradient. Styling is presentation only: it
 *  never changes which modules are ink, so it cannot change what a reader
 *  decodes. It absolutely changes whether a reader manages to read it —
 *  `dots-tight` needs 3 camera pixels per module where `square` needs 1 — so
 *  every styled artefact gets rasterised and decoded rather than eyeballed
 *  (`gen/sheets.py` for the sheets, `gen/gallery.py` for the stills).
 *
 *  Everything here is in MODULE units with the origin at the top-left of the
 *  whole symbol, quiet zone included, exactly like style.py's viewBox. One
 *  unit is one module, radii are fractions of one, and a writer's only job is
 *  to scale. That is what lets a sheet exporter put a module edge exactly
 *  where the arithmetic says instead of asking a rasteriser to scale a
 *  finished SVG.
 */
import { QUIET } from './manifest'

export const FINDER = 7

export type DotSpec =
  | { kind: 'cell'; r: number }
  | { kind: 'dot'; shrink: number }
  | { kind: 'classy'; r: number; round: boolean }

/** The same table as style.py's DOTS, and the ids the manifest's `dot` uses. */
export const DOTS: Record<string, DotSpec> = {
  'square':         { kind: 'cell',   r: 0 },
  'rounded':        { kind: 'cell',   r: 0.25 },
  'extra-rounded':  { kind: 'cell',   r: 0.5 },
  'dots':           { kind: 'dot',    shrink: 0 },
  'dots-tight':     { kind: 'dot',    shrink: -0.08 },
  'classy':         { kind: 'classy', r: 0.5, round: false },
  'classy-rounded': { kind: 'classy', r: 0.5, round: true },
}

export type EyeStyle = 'square' | 'rounded' | 'extra-rounded' | 'dot'

/** Every argument gen/gallery.py hands to style.to_svg, which is why the
 *  manifest carries exactly these fields per item. */
export type Style = {
  dot: string
  eyeFrame: EyeStyle
  eyeCore: EyeStyle
  fg: string
  fg2: string | null
  bg: string
  /** corner radius of the background plate, in modules */
  plateRadius: number
  styleEyes: boolean
}

/** Black squares on white, or white on black — what the exporters drew before
 *  they could carry a style, and the fallback for a code with none. */
export const plainStyle = (dark: boolean): Style => ({
  dot: 'square', eyeFrame: 'square', eyeCore: 'square',
  fg: dark ? '#ffffff' : '#000000', fg2: null, bg: dark ? '#000000' : '#ffffff',
  plateRadius: 0, styleEyes: false,
})

// ---------------------------------------------------------------- geometry

/** A path segment. Every curve in this renderer is a quarter circle — the
 *  corner of a rounded module, or one of the four arcs of a dot — so `A` is
 *  radius plus endpoint and nothing else. SVG writes it as an arc; PDF has no
 *  arc operator and writes the matching cubic. */
export type Seg =
  | { t: 'M'; x: number; y: number }
  | { t: 'L'; x: number; y: number }
  | { t: 'A'; r: number; x: number; y: number }
  | { t: 'Z' }

/** One fill element, in the order and the grouping style.py emits.
 *
 *  The grouping is not cosmetic: a gradient is resolved against the bounding
 *  box of the element it fills, so "one piece" is also "one gradient ramp".
 *  Keeping the pieces aligned with style.py's elements is what makes an
 *  exported sheet of `pal-grad` look like the still it came from. */
export type Piece =
  | { kind: 'rects'; rects: [number, number, number, number][] }
  | { kind: 'path'; evenOdd: boolean; segs: Seg[] }

const finders = (n: number): [number, number][] =>
  [[0, 0], [n - FINDER, 0], [0, n - FINDER]]

const inFinder = (x: number, y: number, n: number) =>
  finders(n).some(([fx, fy]) =>
    fx <= x && x < fx + FINDER && fy <= y && y < fy + FINDER)

/** One module, corners rounded only where it has no orthogonal neighbour on
 *  both adjacent sides — what makes runs read as one connected stroke. */
function cell(out: Seg[], x: number, y: number, r: number,
              up: boolean, right: boolean, down: boolean, left: boolean) {
  const tl = !up && !left ? r : 0
  const tr = !up && !right ? r : 0
  const br = !down && !right ? r : 0
  const bl = !down && !left ? r : 0
  out.push({ t: 'M', x: x + tl, y })
  out.push({ t: 'L', x: x + 1 - tr, y })
  if (tr) out.push({ t: 'A', r: tr, x: x + 1, y: y + tr })
  out.push({ t: 'L', x: x + 1, y: y + 1 - br })
  if (br) out.push({ t: 'A', r: br, x: x + 1 - br, y: y + 1 })
  out.push({ t: 'L', x: x + bl, y: y + 1 })
  if (bl) out.push({ t: 'A', r: bl, x, y: y + 1 - bl })
  out.push({ t: 'L', x, y: y + tl })
  if (tl) out.push({ t: 'A', r: tl, x: x + tl, y })
  out.push({ t: 'Z' })
}

/** Two opposite corners cut: the leaf. */
function classy(out: Seg[], x: number, y: number, r: number, roundFar: boolean) {
  out.push({ t: 'M', x: x + r, y })
  out.push({ t: 'L', x: x + 1, y })
  out.push({ t: 'L', x: x + 1, y: y + 1 - (roundFar ? r : 0) })
  if (roundFar) out.push({ t: 'A', r, x: x + 1 - r, y: y + 1 })
  out.push({ t: 'L', x, y: y + 1 })
  out.push({ t: 'L', x, y: y + r })
  out.push({ t: 'A', r, x: x + r, y })
  out.push({ t: 'Z' })
}

function rrect(out: Seg[], x: number, y: number, s: number, r0: number) {
  const r = Math.min(r0, s / 2)
  if (r <= 0) {
    out.push({ t: 'M', x, y }, { t: 'L', x: x + s, y },
             { t: 'L', x: x + s, y: y + s }, { t: 'L', x, y: y + s }, { t: 'Z' })
    return
  }
  out.push({ t: 'M', x: x + r, y })
  out.push({ t: 'L', x: x + s - r, y })
  out.push({ t: 'A', r, x: x + s, y: y + r })
  out.push({ t: 'L', x: x + s, y: y + s - r })
  out.push({ t: 'A', r, x: x + s - r, y: y + s })
  out.push({ t: 'L', x: x + r, y: y + s })
  out.push({ t: 'A', r, x, y: y + s - r })
  out.push({ t: 'L', x, y: y + r })
  out.push({ t: 'A', r, x: x + r, y })
  out.push({ t: 'Z' })
}

/** A circle as four quarter arcs, clockwise from the top. style.py emits a
 *  `<circle>`; one path for every dot in a code is smaller than one element
 *  each, and it means arcs are the only curve either writer has to know. */
function circle(out: Seg[], cx: number, cy: number, r: number) {
  out.push({ t: 'M', x: cx, y: cy - r })
  out.push({ t: 'A', r, x: cx + r, y: cy })
  out.push({ t: 'A', r, x: cx, y: cy + r })
  out.push({ t: 'A', r, x: cx - r, y: cy })
  out.push({ t: 'A', r, x: cx, y: cy - r })
  out.push({ t: 'Z' })
}

/** Horizontal runs as rects — the compact form for unrounded squares. */
function runs(bits: Uint8Array, n: number, quiet: number) {
  const out: [number, number, number, number][] = []
  for (let y = 0; y < n; y++) {
    let x = 0
    while (x < n) {
      if (bits[y * n + x]) {
        let run = 1
        while (x + run < n && bits[y * n + x + run]) run++
        out.push([x + quiet, y + quiet, run, 1])
        x += run
      } else x++
    }
  }
  return out
}

/** The fill elements for one styled symbol, in module units.
 *
 *  `bits` is the unpacked grid, `n` modules across. The returned pieces all
 *  take the same foreground: a style's two colours are one gradient, not two
 *  fills.
 */
export function pieces(bits: Uint8Array, n: number, st: Style,
                       quiet = QUIET): Piece[] {
  const spec = DOTS[st.dot] ?? DOTS.square
  const on = (x: number, y: number) =>
    x >= 0 && x < n && y >= 0 && y < n && !!bits[y * n + x]

  // Square eyes draw a 7x7 ring one module thick around a 3x3 core, which is
  // exactly the finder pattern already in the grid — so with square modules
  // the whole styled render reduces to the grid, and merged runs are both
  // smaller and pixel-identical.
  const plainEyes = !st.styleEyes ||
    (st.eyeFrame === 'square' && st.eyeCore === 'square')
  if (spec.kind === 'cell' && spec.r === 0 && plainEyes)
    return [{ kind: 'rects', rects: runs(bits, n, quiet) }]

  const out: Piece[] = []
  const body: Seg[] = []
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    if (!bits[y * n + x]) continue
    if (st.styleEyes && inFinder(x, y, n)) continue
    const X = x + quiet, Y = y + quiet
    if (spec.kind === 'dot') circle(body, X + 0.5, Y + 0.5, 0.5 * (1 - spec.shrink))
    else if (spec.kind === 'classy') classy(body, X, Y, spec.r, spec.round)
    else cell(body, X, Y, spec.r, on(x, y - 1), on(x + 1, y), on(x, y + 1), on(x - 1, y))
  }
  if (body.length) out.push({ kind: 'path', evenOdd: false, segs: body })

  if (st.styleEyes) {
    // All three rings in one even-odd path, each punched by its own inner
    // rect: one element, so one gradient ramp across all three.
    const ring: Seg[] = []
    const cores: Piece[] = []
    for (const [fx, fy] of finders(n)) {
      const X = fx + quiet, Y = fy + quiet, S = FINDER
      const ro = st.eyeFrame === 'extra-rounded' ? S * 0.32
                : st.eyeFrame === 'rounded' ? S * 0.18
                : st.eyeFrame === 'dot' ? S / 2 : 0
      rrect(ring, X, Y, S, ro)
      rrect(ring, X + 1, Y + 1, S - 2, Math.max(0, ro - 1))
      const core: Seg[] = []
      if (st.eyeCore === 'dot') circle(core, X + 3.5, Y + 3.5, 1.5)
      else rrect(core, X + 2, Y + 2, 3,
                 st.eyeCore === 'extra-rounded' ? 3 * 0.34
                 : st.eyeCore === 'rounded' ? 3 * 0.18 : 0)
      cores.push({ kind: 'path', evenOdd: false, segs: core })
    }
    out.push({ kind: 'path', evenOdd: true, segs: ring })
    out.push(...cores)   // style.py emits each core as its own element
  }
  return out
}

/** The bounding box of a piece, in module units.
 *
 *  Every curve here is a quarter arc, which is monotone in both axes, so its
 *  bounding box is exactly the box of its endpoints — no sampling needed. The
 *  gradient axis is this box's diagonal, which is what SVG's default
 *  `objectBoundingBox` gives for free and what a PDF shading has to be told.
 */
export function bbox(p: Piece): { x0: number; y0: number; x1: number; y1: number } {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
  const add = (x: number, y: number) => {
    if (x < x0) x0 = x; if (x > x1) x1 = x
    if (y < y0) y0 = y; if (y > y1) y1 = y
  }
  if (p.kind === 'rects') for (const [x, y, w, h] of p.rects) { add(x, y); add(x + w, y + h) }
  else for (const s of p.segs) if (s.t !== 'Z') add(s.x, s.y)
  return { x0, y0, x1, y1 }
}

// ----------------------------------------------------------------- writers

/** Module units to the output's units. `p` places a point, `s` scales a
 *  length. PDF flips y, which is a mirror, and a mirror maps the arcs below
 *  onto arcs, so the writers can share one segment list. */
export type Xf = { p: (x: number, y: number) => [number, number]; s: number }

const fmt = (v: number) => (Math.round(v * 1000) / 1000).toString()

/** An SVG `d` attribute. */
export function svgPath(segs: Seg[], xf: Xf): string {
  const out: string[] = []
  for (const g of segs) {
    if (g.t === 'Z') { out.push('Z'); continue }
    const [x, y] = xf.p(g.x, g.y)
    if (g.t === 'M') out.push(`M${fmt(x)} ${fmt(y)}`)
    else if (g.t === 'L') out.push(`L${fmt(x)} ${fmt(y)}`)
    else {
      const r = fmt(g.r * xf.s)
      // every arc is a quarter turn, so large-arc is 0 and sweep is 1
      out.push(`A${r} ${r} 0 0 1 ${fmt(x)} ${fmt(y)}`)
    }
  }
  return out.join('')
}

/** Cubic control points for the quarter arc from (x0,y0) to (x1,y1).
 *
 *  A 90-degree arc is within a thousandth of a module of its Bezier match, and
 *  it is the only curve this renderer makes, so the 4/3·tan(θ/4) constant is a
 *  constant rather than a function. The centre comes from the chord: the two
 *  candidates are on either side of it, and style.py's arcs are all SVG
 *  sweep-1, which picks the one towards `(-dy, dx)`.
 */
const KAPPA = 0.5522847498307936

function cubic(x0: number, y0: number, r: number, x1: number, y1: number) {
  const dx = x1 - x0, dy = y1 - y0
  const len = Math.hypot(dx, dy)
  if (!len || r <= 0) return null
  const half = len / 2
  const h = Math.sqrt(Math.max(0, r * r - half * half))
  const cx = (x0 + x1) / 2 - (dy / len) * h
  const cy = (y0 + y1) / 2 + (dx / len) * h
  const k = KAPPA * r
  return [
    x0 + k * (-(y0 - cy) / r), y0 + k * ((x0 - cx) / r),
    x1 - k * (-(y1 - cy) / r), y1 - k * ((x1 - cx) / r),
  ] as const
}

/** A PDF content-stream path, with no paint operator — the caller decides
 *  between `f`, `f*` and a clip. */
export function pdfPath(segs: Seg[], xf: Xf): string {
  const out: string[] = []
  const at = (x: number, y: number) => { const [a, b] = xf.p(x, y); return `${fmt(a)} ${fmt(b)}` }
  let px = 0, py = 0
  for (const g of segs) {
    if (g.t === 'Z') { out.push('h'); continue }
    if (g.t === 'M') out.push(`${at(g.x, g.y)} m`)
    else if (g.t === 'L') out.push(`${at(g.x, g.y)} l`)
    else {
      const c = cubic(px, py, g.r, g.x, g.y)
      if (!c) out.push(`${at(g.x, g.y)} l`)
      else out.push(`${at(c[0], c[1])} ${at(c[2], c[3])} ${at(g.x, g.y)} c`)
    }
    px = g.x; py = g.y
  }
  return out.join('\n')
}

/** `#rgb` or `#rrggbb` to PDF's three 0..1 components. */
export function rgb(hex: string): [number, number, number] {
  let h = hex.replace('#', '').trim()
  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
  const v = parseInt(h || '000000', 16)
  return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255]
}

export const isWhite = (hex: string) =>
  ['#fff', '#ffffff', 'white'].includes(hex.trim().toLowerCase())
