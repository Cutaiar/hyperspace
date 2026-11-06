/** Turning a sheet into a file a printer or a cutter will accept.
 *
 *  Codes are re-rendered from the module grid in the manifest at the exact
 *  physical size, never by scaling the published SVG. Scaling goes through a
 *  rasteriser's idea of rounding; emitting the grid directly means a module
 *  edge lands exactly where the arithmetic says, which is the whole reason the
 *  grid is in the manifest.
 *
 *  Both writers take the same geometry from lib/sheet.ts, so the preview, the
 *  SVG and the PDF cannot disagree about where a cut goes.
 */
import { across, unpack } from './manifest'
import type { Layout, Placed } from './sheet'

const MM_TO_PT = 72 / 25.4
const f = (v: number) => (Math.round(v * 1000) / 1000).toString()

export type Code = { id: string; modules: number; matrix: string; dark: boolean }

/** Dark-module rects for one code, in mm, placed at (x, y) over `size` mm. */
function moduleRects(code: Code, x: number, y: number, size: number) {
  const n = code.modules
  const bits = unpack(code.matrix, n)
  const quiet = (across(n) - n) / 2
  const m = size / across(n)
  const out: [number, number, number, number][] = []
  for (let r = 0; r < n; r++) {
    let c = 0
    while (c < n) {
      if (bits[r * n + c]) {
        let run = 1
        while (c + run < n && bits[r * n + c + run]) run++
        out.push([x + (c + quiet) * m, y + (r + quiet) * m, run * m, m])
        c += run
      } else c++
    }
  }
  return out
}

export type SheetExport = {
  layout: Layout
  placed: Placed[]
  codes: Record<string, Code>
  /** draw the cut lines into the artwork; vendors want them, cutters do not */
  cutline: boolean
}

export function sheetSvg({ layout: lay, placed, codes, cutline }: SheetExport): string {
  const { w, h } = lay.paper
  const art: string[] = []
  const cuts: string[] = []

  for (const p of placed) {
    const code = codes[p.id]
    if (!code) continue
    if (code.dark) {
      art.push(`<rect x="${f(p.cut.x)}" y="${f(p.cut.y)}" width="${f(p.cut.w)}" ` +
               `height="${f(p.cut.h)}" fill="#000"/>`)
    }
    const fill = code.dark ? '#fff' : '#000'
    const rects = moduleRects(code, p.cut.x, p.cut.y, p.cut.w)
      .map(([x, y, rw, rh]) => `<rect x="${f(x)}" y="${f(y)}" width="${f(rw)}" height="${f(rh)}"/>`)
      .join('')
    art.push(`<g fill="${fill}">${rects}</g>`)
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
    `<g id="artwork">${art.join('')}</g>`,
    cutLayer,
    '</svg>',
  ].join('\n')
}

/** A single-page vector PDF, written by hand so there is no dependency and no
 *  rasterisation. Geometry is in points, origin bottom-left, so y is flipped.
 *
 *  Not implemented: optional content groups (true PDF layers) and spot colours.
 *  The cut lines are ordinary magenta strokes. A vendor who needs a named spot
 *  plate wants the SVG, or this file plus a one-line swatch change in their
 *  prepress — say so rather than implying this is press-ready.
 */
export function sheetPdf({ layout: lay, placed, codes, cutline }: SheetExport): Uint8Array {
  const W = lay.paper.w * MM_TO_PT, H = lay.paper.h * MM_TO_PT
  const up = (yMm: number, hMm: number) => (lay.paper.h - yMm - hMm) * MM_TO_PT

  const s: string[] = ['1 1 1 rg', `0 0 ${f(W)} ${f(H)} re f`]
  for (const p of placed) {
    const code = codes[p.id]
    if (!code) continue
    if (code.dark) {
      s.push('0 0 0 rg',
        `${f(p.cut.x * MM_TO_PT)} ${f(up(p.cut.y, p.cut.h))} ` +
        `${f(p.cut.w * MM_TO_PT)} ${f(p.cut.h * MM_TO_PT)} re f`)
    }
    s.push(code.dark ? '1 1 1 rg' : '0 0 0 rg')
    for (const [x, y, rw, rh] of moduleRects(code, p.cut.x, p.cut.y, p.cut.w))
      s.push(`${f(x * MM_TO_PT)} ${f(up(y, rh))} ${f(rw * MM_TO_PT)} ${f(rh * MM_TO_PT)} re f`)
  }
  if (cutline) {
    s.push('1 0 1 RG', '0.25 w')
    for (const p of placed)
      s.push(`${f(p.cut.x * MM_TO_PT)} ${f(up(p.cut.y, p.cut.h))} ` +
             `${f(p.cut.w * MM_TO_PT)} ${f(p.cut.h * MM_TO_PT)} re S`)
  }
  const content = s.join('\n')

  const objs = [
    '<</Type/Catalog/Pages 2 0 R>>',
    '<</Type/Pages/Kids[3 0 R]/Count 1>>',
    `<</Type/Page/Parent 2 0 R/MediaBox[0 0 ${f(W)} ${f(H)}]/Contents 4 0 R/Resources<<>>>>`,
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

export function download(name: string, data: string | Uint8Array, type: string) {
  const blob = new Blob([data as BlobPart], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name
  document.body.append(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
