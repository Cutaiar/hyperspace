import { readFileSync, writeFileSync } from 'node:fs'
import { PAPERS, DEFAULTS, layout, assign, type CutMode } from '../src/lib/sheet'
import { sheetSvg, sheetPdf, type Code } from '../src/lib/export'

let fails = 0
const ok = (name: string, cond: boolean, detail = '') => {
  if (cond) console.log(`  ok   ${name}${detail && ' — ' + detail}`)
  else { fails++; console.log(`  FAIL ${name}${detail && ' — ' + detail}`) }
}

const man = JSON.parse(readFileSync('public/data/gallery/manifest.json', 'utf8'))
const light = man.items.find((i: { id: string }) => i.id === 'c16-tilt')
const dark = man.items.find((i: { dark: boolean }) => i.dark)
const codes: Record<string, Code> = {}
for (const i of [light, dark])
  codes[i.id] = { id: i.id, modules: i.modules, matrix: i.matrix, dark: i.dark }

function sheet(mode: CutMode, gutter: number, bleed: number, sticker = 44) {
  const lay = layout({ paper: PAPERS.letter, mode, sticker, gutter, bleed, edge: DEFAULTS.edge })
  const placed = assign(lay, [
    { id: light.id, modules: light.modules },
    { id: dark.id, modules: dark.modules },
  ])
  return { lay, placed, svg: sheetSvg({ layout: lay, placed, codes, cutline: mode === 'vendor' }) }
}

/** the black plate drawn for the first inverted sticker, as width in mm */
function plateWidth(svg: string, cutW: number) {
  const widths = [...svg.matchAll(/<rect x="[-\d.]+" y="[-\d.]+" width="([\d.]+)" height="[\d.]+" fill="#000"\/>/g)]
    .map(m => +m[1])
  return widths.length ? widths[0] : cutW
}

console.log('\nthe inverted plate never reaches the next sticker')
// a 65-module code at 44 mm has a 2.41 mm quiet zone; a 3 mm plate at zero
// gutter would eat 0.59 mm of the neighbour's data
for (const [mode, gutter, bleed, want, why] of [
  ['vendor', 0, 3, 44, 'zero gutter: no spread at all'],
  ['vendor', DEFAULTS.gutter, 3, 44 + 2 * (DEFAULTS.gutter / 2), 'clamped to half the gutter'],
  ['vendor', 12, 3, 50, 'wide gutter: the full 3 mm bleed'],
  ['print-then-cut', DEFAULTS.gutter, 3, 44, 'cutter reads marks, bleed buys nothing'],
] as const) {
  const { lay, svg } = sheet(mode as CutMode, gutter, bleed)
  const w = plateWidth(svg, 44)
  ok(`${mode} gutter ${(+gutter).toFixed(2)}`, Math.abs(w - want) < 0.01, `${w} mm — ${why}`)
  void lay
}

console.log('\nplates never overlap a neighbouring cut, at any gutter')
for (const g of [0, 1, 2, DEFAULTS.gutter, 12]) {
  const { lay, svg } = sheet('vendor', g, 3)
  const w = plateWidth(svg, 44)
  const spread = (w - 44) / 2
  // the file rounds coordinates to 3 decimals, so allow half a micron of it
  ok(`gutter ${g.toFixed(2)}`, spread <= g / 2 + 0.001,
     `plate spreads ${spread.toFixed(3)} mm into a ${(g / 2).toFixed(3)} mm half-gutter`)
  void lay
}

// a real sheet for the decode harness: the hostile case, mixed and zero gutter
const hostile = sheet('vendor', 0, 3)
writeFileSync('/tmp/sheet-hostile.svg', hostile.svg)
writeFileSync('/tmp/sheet-hostile.pdf',
  sheetPdf({ layout: hostile.lay, placed: hostile.placed, codes, cutline: true }))
const normal = sheet('print-then-cut', DEFAULTS.gutter, 3)
writeFileSync('/tmp/sheet.svg', normal.svg)
writeFileSync('/tmp/sheet.pdf',
  sheetPdf({ layout: normal.lay, placed: normal.placed, codes, cutline: false }))
console.log(`\nwrote /tmp/sheet.{svg,pdf} (${normal.placed.length} up) and ` +
            `/tmp/sheet-hostile.{svg,pdf} (${hostile.placed.length} up, zero gutter, mixed)`)

console.log(fails ? `\n${fails} FAILED` : '\nall checks passed')
process.exit(fails ? 1 : 0)
