/** Turning a sheet into a file a printer or a cutter will accept.
 *
 *  Codes are re-rendered from the module grid in the manifest at the exact
 *  physical size, never by scaling the published SVG. Scaling goes through a
 *  rasteriser's idea of rounding; emitting the grid directly means a module
 *  edge lands exactly where the arithmetic says, which is the whole reason the
 *  grid is in the manifest.
 *
 *  The grid is geometry; the look is `lib/style.ts`, the TypeScript twin of
 *  gen/style.py. A code's style comes off its manifest item, so a sheet of
 *  `pal-red` or `sty-dots` exports as the thing the gallery shows rather than
 *  as plain black squares. Styling cannot change what a code says and very
 *  much can change whether a camera reads it, so gen/sheets.py rasterises
 *  every sheet these writers produce and decodes it.
 *
 *  Both writers take the same geometry from lib/sheet.ts, so the preview, the
 *  SVG and the PDF cannot disagree about where a cut goes.
 */
import { across, unpack } from './manifest'
import {
  bbox, isWhite, pdfPath, pieces, plainStyle, rgb, svgPath,
  type Piece, type Style, type Xf,
} from './style'
import type { Layout, Placed } from './sheet'

const MM_TO_PT = 72 / 25.4
const f = (v: number) => (Math.round(v * 1000) / 1000).toString()

export type Code = {
  id: string
  modules: number
  matrix: string
  dark: boolean
  /** from manifest.styleOf(); absent means plain black-on-white geometry */
  style?: Style
}

/** How far an inverted sticker's black plate may spread past its cut.
 *
 *  Never more than half the gutter, or the plate crosses into the next
 *  sticker: at a zero gutter a 3 mm plate reaches 3 mm into a neighbour whose
 *  quiet zone is only 2.41 mm, covering part of its outermost data column and
 *  making a perfectly good code unreadable. And never at all in print-then-cut,
 *  where the cutter takes its line from registration marks and bleed buys
 *  nothing. The sheet's own warning tells you when this is clamping. */
function plateInset(lay: Layout): number {
  if (lay.mode !== 'vendor') return 0
  return Math.max(0, Math.min(lay.bleed, lay.gutter / 2))
}

const grow = (r: { x: number; y: number; w: number; h: number }, by: number) =>
  ({ x: r.x - by, y: r.y - by, w: r.w + 2 * by, h: r.h + 2 * by })

/** One code's style and its fill elements, placed at (x, y) over `size` mm.
 *
 *  `size` covers the whole symbol, quiet zone included, so one module is
 *  size / across(n) millimetres — the same arithmetic lib/sheet.ts's pitch()
 *  reports and lib/media.ts judges against a floor.
 */
function art(code: Code, x: number, y: number, size: number) {
  const n = code.modules
  const st = code.style ?? plainStyle(code.dark)
  const m = size / across(n)
  const xf: Xf = { p: (u, v) => [x + u * m, y + v * m], s: m }
  return { st, m, xf, ps: pieces(unpack(code.matrix, n), n, st) }
}

/** The plate under the modules: a sticker's own paper colour.
 *
 *  Only painted when it differs from the sheet, so a white-backed code stays
 *  as it was — ink straight onto paper, no 44 mm white rectangle per sticker.
 *  That also means `pal-plate`'s rounded white plate is invisible here: it is
 *  for dropping on a dark page, and a sheet is already white. */
const plateOf = (st: Style) => (st.bg && !isWhite(st.bg) ? st.bg : null)

export type SheetExport = {
  layout: Layout
  placed: Placed[]
  codes: Record<string, Code>
  /** draw the cut lines into the artwork; vendors want them, cutters do not */
  cutline: boolean
}

export function sheetSvg({ layout: lay, placed, codes, cutline }: SheetExport): string {
  const { w, h } = lay.paper
  const defs: string[] = []
  const graded = new Set<string>()
  const art$: string[] = []
  const cuts: string[] = []

  for (const p of placed) {
    const code = codes[p.id]
    if (!code) continue
    const { st, m, xf, ps } = art(code, p.cut.x, p.cut.y, p.cut.w)

    const plate = plateOf(st)
    if (plate) {
      // bleed exists so a cut landing a millimetre out still hits printed
      // ink, but never so far that it reaches the next sticker
      const r = grow(p.cut, plateInset(lay))
      const rx = st.plateRadius ? ` rx="${f(st.plateRadius * m)}"` : ''
      art$.push(`<rect x="${f(r.x)}" y="${f(r.y)}" width="${f(r.w)}" ` +
                `height="${f(r.h)}" fill="${plate}"${rx}/>`)
    }

    // A gradient is resolved against the bounding box of the element it fills,
    // so one gradient def per code id is placement-independent and gives each
    // piece the same ramp style.py's objectBoundingBox gives it.
    let fill = st.fg
    if (st.fg2) {
      fill = `url(#grad-${code.id})`
      if (!graded.has(code.id)) {
        graded.add(code.id)
        defs.push(`<linearGradient id="grad-${code.id}" x1="0" y1="0" x2="1" y2="1">` +
                  `<stop offset="0" stop-color="${st.fg}"/>` +
                  `<stop offset="1" stop-color="${st.fg2}"/></linearGradient>`)
      }
    }
    art$.push(`<g fill="${fill}">${ps.map(pc => svgPiece(pc, xf)).join('')}</g>`)
    cuts.push(`<rect x="${f(p.cut.x)}" y="${f(p.cut.y)}" width="${f(p.cut.w)}" height="${f(p.cut.h)}"/>`)
  }

  // The cut layer is its own group with a predictable id, which is what every
  // vendor template asks for. Spot-colour naming is per-printer; set it there.
  const cutLayer = cutline
    ? `<g id="cutline" fill="none" stroke="#ff00ff" stroke-width="0.25">${cuts.join('')}</g>`
    : ''

  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${f(w)}mm" height="${f(h)}mm" ` +
      `viewBox="0 0 ${f(w)} ${f(h)}">`,
    `<rect width="${f(w)}" height="${f(h)}" fill="#fff"/>`,
    defs.length ? `<defs>${defs.join('')}</defs>` : '',
    `<g id="artwork">${art$.join('')}</g>`,
    cutLayer,
    '</svg>',
  ].filter(Boolean).join('\n')
}

function svgPiece(pc: Piece, xf: Xf): string {
  if (pc.kind === 'rects')
    return pc.rects.map(([x, y, rw, rh]) => {
      // both corners through the transform, so neither writer has to know
      // which units it is in or which way its y points
      const [x0, y0] = xf.p(x, y)
      const [x1, y1] = xf.p(x + rw, y + rh)
      return `<rect x="${f(Math.min(x0, x1))}" y="${f(Math.min(y0, y1))}" ` +
             `width="${f(Math.abs(x1 - x0))}" height="${f(Math.abs(y1 - y0))}"/>`
    }).join('')
  const rule = pc.evenOdd ? ' fill-rule="evenodd"' : ''
  return `<path${rule} d="${svgPath(pc.segs, xf)}"/>`
}

/** A single-page vector PDF, written by hand so there is no dependency and no
 *  rasterisation. Geometry is in points, origin bottom-left, so y is flipped.
 *
 *  Rounded and circular modules are real path operators: `re f` can only draw
 *  a rectangle, so every arc becomes the cubic that matches it (lib/style.ts),
 *  and a gradient becomes an axial shading painted through the module path as
 *  a clip. Still no dependency and still no raster.
 *
 *  Not implemented: optional content groups (true PDF layers) and spot
 *  colours. The cut lines are ordinary magenta strokes. A vendor who needs a
 *  named spot plate wants the SVG, or this file plus a one-line swatch change
 *  in their prepress — say so rather than implying this is press-ready.
 */
export function sheetPdf({ layout: lay, placed, codes, cutline }: SheetExport): Uint8Array {
  const W = lay.paper.w * MM_TO_PT, H = lay.paper.h * MM_TO_PT
  const pt = (xMm: number, yMm: number): [number, number] =>
    [xMm * MM_TO_PT, (lay.paper.h - yMm) * MM_TO_PT]
  const up = (yMm: number, hMm: number) => (lay.paper.h - yMm - hMm) * MM_TO_PT

  const s: string[] = ['1 1 1 rg', `0 0 ${f(W)} ${f(H)} re f`]
  const shadings: string[] = []

  for (const p of placed) {
    const code = codes[p.id]
    if (!code) continue
    const { st, m, ps } = art(code, p.cut.x, p.cut.y, p.cut.w)
    // the writers share one segment list; only the final mapping differs
    const xf: Xf = { p: (u, v) => pt(p.cut.x + u * m, p.cut.y + v * m), s: m }

    const plate = plateOf(st)
    if (plate) {
      const r = grow(p.cut, plateInset(lay))   // same clamp as the SVG
      s.push(`${rgb(plate).map(f).join(' ')} rg`)
      if (st.plateRadius) {
        // a rounded plate is a path like any other; reuse the module writer
        const rr = roundedRect(r, st.plateRadius * m)
        s.push(pdfPath(rr, { p: pt, s: 1 }), 'f')
      } else {
        s.push(`${f(r.x * MM_TO_PT)} ${f(up(r.y, r.h))} ` +
               `${f(r.w * MM_TO_PT)} ${f(r.h * MM_TO_PT)} re f`)
      }
    }

    if (st.fg2) {
      const [c0, c1] = [rgb(st.fg), rgb(st.fg2)]
      for (const pc of ps) {
        // One shading per piece, spanning that piece's bounding box — the same
        // ramp SVG's objectBoundingBox hands the matching element.
        const b = bbox(pc)
        const [ax, ay] = xf.p(b.x0, b.y0)
        const [bx, by] = xf.p(b.x1, b.y1)
        const name = `Sh${shadings.length}`
        shadings.push(
          `/${name}<</ShadingType 2/ColorSpace/DeviceRGB/Extend[true true]` +
          `/Coords[${f(ax)} ${f(ay)} ${f(bx)} ${f(by)}]` +
          `/Function<</FunctionType 2/Domain[0 1]/N 1` +
          `/C0[${c0.map(f).join(' ')}]/C1[${c1.map(f).join(' ')}]>>>>`)
        s.push('q', pdfPiece(pc, xf), pc.kind === 'path' && pc.evenOdd ? 'W* n' : 'W n',
               `/${name} sh`, 'Q')
      }
    } else {
      s.push(`${rgb(st.fg).map(f).join(' ')} rg`)
      for (const pc of ps)
        s.push(pdfPiece(pc, xf), pc.kind === 'path' && pc.evenOdd ? 'f*' : 'f')
    }
  }

  if (cutline) {
    s.push('1 0 1 RG', '0.25 w')
    for (const p of placed)
      s.push(`${f(p.cut.x * MM_TO_PT)} ${f(up(p.cut.y, p.cut.h))} ` +
             `${f(p.cut.w * MM_TO_PT)} ${f(p.cut.h * MM_TO_PT)} re S`)
  }
  const content = s.join('\n')

  const resources = shadings.length ? `<</Shading<<${shadings.join('')}>>>>` : '<<>>'
  const objs = [
    '<</Type/Catalog/Pages 2 0 R>>',
    '<</Type/Pages/Kids[3 0 R]/Count 1>>',
    `<</Type/Page/Parent 2 0 R/MediaBox[0 0 ${f(W)} ${f(H)}]/Contents 4 0 R` +
      `/Resources ${resources}>>`,
    `<</Length ${content.length}>>\nstream\n${content}\nendstream`,
  ]
  let pdf = '%PDF-1.4\n'
  const offsets: number[] = []
  objs.forEach((o, i) => { offsets.push(pdf.length); pdf += `${i + 1} 0 obj\n${o}\nendobj\n` })
  const xref = pdf.length
  pdf += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`
  for (const o of offsets) pdf += `${String(o).padStart(10, '0')} 00000 n \n`
  pdf += `trailer\n<</Size ${objs.length + 1}/Root 1 0 R>>\nstartxref\n${xref}\n%%EOF\n`

  const out = new Uint8Array(pdf.length)
  for (let i = 0; i < pdf.length; i++) out[i] = pdf.charCodeAt(i) & 0xff
  return out
}

/** Rects stay `re`: it is shorter and exact, and a run of plain squares is
 *  most of a sheet. Everything else is a path. */
function pdfPiece(pc: Piece, xf: Xf): string {
  if (pc.kind === 'rects')
    return pc.rects.map(([x, y, rw, rh]) => {
      const [x0, y0] = xf.p(x, y)
      const [x1, y1] = xf.p(x + rw, y + rh)
      return `${f(Math.min(x0, x1))} ${f(Math.min(y0, y1))} ` +
             `${f(Math.abs(x1 - x0))} ${f(Math.abs(y1 - y0))} re`
    }).join('\n')
  return pdfPath(pc.segs, xf)
}

/** A rounded rectangle in mm, as segments the path writers understand. */
function roundedRect(r: { x: number; y: number; w: number; h: number }, rad: number) {
  const k = Math.min(rad, Math.min(r.w, r.h) / 2)
  const { x, y, w, h } = r
  return [
    { t: 'M' as const, x: x + k, y },
    { t: 'L' as const, x: x + w - k, y },
    { t: 'A' as const, r: k, x: x + w, y: y + k },
    { t: 'L' as const, x: x + w, y: y + h - k },
    { t: 'A' as const, r: k, x: x + w - k, y: y + h },
    { t: 'L' as const, x: x + k, y: y + h },
    { t: 'A' as const, r: k, x, y: y + h - k },
    { t: 'L' as const, x, y: y + k },
    { t: 'A' as const, r: k, x: x + k, y },
    { t: 'Z' as const },
  ]
}

export function download(name: string, data: string | Uint8Array, type: string) {
  const blob = new Blob([data as BlobPart], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name
  document.body.append(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
