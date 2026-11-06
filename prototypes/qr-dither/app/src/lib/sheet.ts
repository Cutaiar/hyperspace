/** Laying codes out on a physical sheet. Pure geometry in millimetres — no
 *  React, no DOM, no SVG. The preview and the exporter both read from this, so
 *  what you see on screen and what lands in the file cannot disagree.
 *
 *  The numbers and their sources are in STICKERS.md. The short version: vendor
 *  conventions disagree, so the defaults here are the conservative end, and a
 *  chosen printer's own template overrides all of it.
 */
import { across } from './manifest'

export type Paper = { id: string; label: string; w: number; h: number }

export const PAPERS: Record<string, Paper> = {
  letter: { id: 'letter', label: 'US Letter', w: 215.9, h: 279.4 },
  a4:     { id: 'a4',     label: 'A4',        w: 210.0, h: 297.0 },
}

/** Cricut publishes 7.44" x 9.94" on Letter, the corners being reserved for
 *  registration marks. That is a uniform 13.45 mm inset, which is what gets
 *  applied to A4 as well — a derivation, not a published figure, so treat the
 *  A4 case as unverified until a real cut says otherwise. */
export const PTC_INSET = 13.45

export type CutMode = 'vendor' | 'print-then-cut'

export type SheetOpts = {
  paper: Paper
  mode: CutMode
  /** the cut size of one sticker, mm (square: these codes are square) */
  sticker: number
  /** gap between adjacent cut lines, mm */
  gutter: number
  /** art carried past the cut, mm. Printed, then trimmed away. */
  bleed: number
  /** keep-out from the sheet edge to any cut line, mm (vendor mode) */
  edge: number
}

export const DEFAULTS: Omit<SheetOpts, 'paper' | 'mode' | 'sticker'> = {
  gutter: (3 / 16) * 25.4,     // 4.76 mm — the conservative vendor figure
  bleed: 3,                    // 1/8"
  edge: 3,                     // 1/8"
}

export type Rect = { x: number; y: number; w: number; h: number }
export type Cell = { row: number; col: number; cut: Rect; art: Rect }

export type Layout = {
  paper: Paper
  mode: CutMode
  /** carried so an exporter can tell how far art may safely spread */
  gutter: number
  bleed: number
  usable: Rect
  cols: number
  rows: number
  cells: Cell[]
  /** fraction of the usable area the cuts cover */
  coverage: number
  warnings: string[]
}

/** The area cut lines may occupy. */
export function usableArea(opts: SheetOpts): Rect {
  const { paper, mode, edge } = opts
  if (mode === 'print-then-cut')
    return { x: PTC_INSET, y: PTC_INSET,
             w: paper.w - 2 * PTC_INSET, h: paper.h - 2 * PTC_INSET }
  return { x: edge, y: edge, w: paper.w - 2 * edge, h: paper.h - 2 * edge }
}

/** How many fit along a run of `span` mm.
 *  n stickers need n*sticker + (n-1)*gutter, so the trailing gutter is not
 *  charged — floor(span / pitch) would quietly lose a column. */
export function fitAlong(span: number, sticker: number, gutter: number): number {
  if (sticker <= 0) return 0
  return Math.max(0, Math.floor((span + gutter) / (sticker + gutter)))
}

export function layout(opts: SheetOpts): Layout {
  const { sticker, gutter, bleed } = opts
  const usable = usableArea(opts)
  const cols = fitAlong(usable.w, sticker, gutter)
  const rows = fitAlong(usable.h, sticker, gutter)

  // centre the block in the usable area rather than hugging one corner, so a
  // misfed sheet loses margin evenly instead of clipping one edge
  const blockW = cols * sticker + Math.max(0, cols - 1) * gutter
  const blockH = rows * sticker + Math.max(0, rows - 1) * gutter
  const x0 = usable.x + (usable.w - blockW) / 2
  const y0 = usable.y + (usable.h - blockH) / 2

  const cells: Cell[] = []
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const x = x0 + c * (sticker + gutter), y = y0 + r * (sticker + gutter)
    cells.push({
      row: r, col: c,
      cut: { x, y, w: sticker, h: sticker },
      art: { x: x - bleed, y: y - bleed, w: sticker + 2 * bleed, h: sticker + 2 * bleed },
    })
  }

  const warnings: string[] = []
  if (!cells.length)
    warnings.push(`A ${sticker.toFixed(1)} mm sticker does not fit on ${opts.paper.label} at this gutter.`)
  if (sticker < 6)
    warnings.push('Under the 6 mm minimum sticker size most vendors will accept.')
  if (opts.mode === 'vendor' && gutter < 2 * bleed)
    warnings.push(
      `Gutter ${gutter.toFixed(2)} mm is less than twice the ${bleed} mm bleed, so neighbouring ` +
      'bleeds overlap. Fine if the art is one continuous design, wrong if the stickers are distinct.')
  if (opts.mode === 'print-then-cut' && bleed > 0)
    warnings.push('Print-then-cut reads a cut line from registration marks, not from a bleed. Bleed is wasted here.')
  if (opts.paper.id === 'a4' && opts.mode === 'print-then-cut')
    warnings.push('The A4 print-then-cut area is derived from the Letter inset, not published. Verify before a real cut.')

  const area = usable.w * usable.h
  return { paper: opts.paper, mode: opts.mode, gutter, bleed, usable, cols, rows, cells,
           coverage: area > 0 ? (cells.length * sticker * sticker) / area : 0,
           warnings }
}

/** mm per module when a code of `modules` fills a sticker of `sticker` mm,
 *  quiet zone included — the quiet zone is part of the symbol, not margin. */
export function pitch(modules: number, sticker: number): number {
  return sticker / across(modules)
}

/** The smallest sticker at which `modules` clears `floorMm` per module. */
export function minSticker(modules: number, floorMm: number): number {
  return across(modules) * floorMm
}

export type Pick = { id: string; modules: number; count?: number }
export type Placed = Cell & { id: string; modules: number }

/** Fill the sheet from `picks`. Entries with a `count` get exactly that many;
 *  whatever is left over is dealt round-robin from the picks that did not ask
 *  for a specific number. An empty cell is simply absent from the result. */
export function assign(lay: Layout, picks: Pick[]): Placed[] {
  if (!picks.length) return []
  const queue: Pick[] = []
  for (const p of picks)
    for (let i = 0; i < (p.count ?? 0); i++) queue.push(p)
  const fillers = picks.filter(p => p.count == null)
  let f = 0
  while (queue.length < lay.cells.length && fillers.length)
    queue.push(fillers[f++ % fillers.length])

  return lay.cells.slice(0, queue.length).map((cell, i) => ({
    ...cell, id: queue[i].id, modules: queue[i].modules,
  }))
}
