import { readFileSync, writeFileSync } from 'node:fs'
import { PAPERS, DEFAULTS, layout, assign } from '../src/lib/sheet'
import { sheetSvg, sheetPdf, type Code } from '../src/lib/export'

const man = JSON.parse(readFileSync('public/data/gallery/manifest.json', 'utf8'))
const pick = man.items.find((i: { id: string }) => i.id === 'c16-tilt')
const dark = man.items.find((i: { dark: boolean }) => i.dark)        // the inverted one
const sticker = 44

const lay = layout({ paper: PAPERS.letter, mode: 'print-then-cut', sticker, ...DEFAULTS })
const placed = assign(lay, [
  { id: pick.id, modules: pick.modules },
  { id: dark.id, modules: dark.modules },
])
const codes: Record<string, Code> = {}
for (const i of [pick, dark])
  codes[i.id] = { id: i.id, modules: i.modules, matrix: i.matrix, dark: i.dark }

const svg = sheetSvg({ layout: lay, placed, codes, cutline: true })
const pdf = sheetPdf({ layout: lay, placed, codes, cutline: true })
writeFileSync('/tmp/sheet.svg', svg)
writeFileSync('/tmp/sheet.pdf', pdf)

const first = placed[0]
console.log(JSON.stringify({
  cells: lay.cells.length,
  placed: placed.length,
  firstId: first.id,
  firstCutMm: [first.cut.x, first.cut.y, first.cut.w, first.cut.h].map(v => +v.toFixed(3)),
  modulesAcross: pick.modules + 8,
  moduleMm: +(sticker / (pick.modules + 8)).toFixed(4),
  svgBytes: svg.length,
  pdfBytes: pdf.length,
  hasCutLayer: svg.includes('id="cutline"'),
  darkPlaced: placed.filter(p => p.id === dark.id).length,
}, null, 1))
