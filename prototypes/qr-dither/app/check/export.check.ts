import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { QUIET, across, styleOf, unpack, type Item } from '../src/lib/manifest'
import { PAPERS, DEFAULTS, layout, assign, pitch, type CutMode, type Placed } from '../src/lib/sheet'
import { sheetSvg, sheetPdf, type Code } from '../src/lib/export'
import { DOTS, bbox, pieces } from '../src/lib/style'

let fails = 0
const ok = (name: string, cond: boolean, detail = '') => {
  if (cond) console.log(`  ok   ${name}${detail && ' — ' + detail}`)
  else { fails++; console.log(`  FAIL ${name}${detail && ' — ' + detail}`) }
}
const near = (a: number, b: number, eps = 0.002) => Math.abs(a - b) < eps

const man = JSON.parse(readFileSync('public/data/gallery/manifest.json', 'utf8'))
const item = (id: string): Item => {
  const hit = (man.items as Item[]).find(i => i.id === id)
  if (!hit) throw new Error(`no manifest item ${id}`)
  return hit
}
const light = item('c16-tilt')
const dark = (man.items as Item[]).find(i => i.dark)!

/** A code with its style, the way Builder.tsx hands them over. */
const styled = (it: Item): Code =>
  ({ id: it.id, modules: it.modules, matrix: it.matrix, dark: it.dark, style: styleOf(it) })
/** A code without one: the geometry-only path the exporters had before. */
const bare = (it: Item): Code =>
  ({ id: it.id, modules: it.modules, matrix: it.matrix, dark: it.dark })

const OUT = '../work/sheets'
mkdirSync(OUT, { recursive: true })

type Sheet = {
  name: string
  lay: ReturnType<typeof layout>
  placed: Placed[]
  svg: string
  pdf: string
  codes: Record<string, Code>
}

function sheet(name: string, mode: CutMode, gutter: number, bleed: number,
               picks: Code[], sticker = 44): Sheet {
  const lay = layout({ paper: PAPERS.letter, mode, sticker, gutter, bleed, edge: DEFAULTS.edge })
  const placed = assign(lay, picks.map(c => ({ id: c.id, modules: c.modules })))
  const codes = Object.fromEntries(picks.map(c => [c.id, c]))
  const bundle = { layout: lay, placed, codes, cutline: mode === 'vendor' }
  return {
    name, lay, placed, codes,
    svg: sheetSvg(bundle),
    pdf: Buffer.from(sheetPdf(bundle)).toString('latin1'),
  }
}

// ---------------------------------------------------------------- geometry

console.log('\nstyling never changes which modules are ink')
// The whole safety argument for styling an export: the renderer may reshape a
// module but may not move, add or drop one. Measured as inked area in module
// units against the grid's own population count, which is exact for squares
// and within the shape's area ratio for everything else.
for (const id of ['sty-square', 'sty-rounded', 'sty-extra-rounded', 'sty-dots',
                  'sty-dots-tight', 'sty-classy', 'sty-classy-rounded',
                  'pal-grad', 'pal-invert']) {
  const it = item(id)
  const n = it.modules
  const bits = unpack(it.matrix, n)
  const ps = pieces(bits, n, styleOf(it))
  // every piece sits inside the symbol, quiet zone and all
  const b = ps.map(bbox).reduce((a, c) => ({
    x0: Math.min(a.x0, c.x0), y0: Math.min(a.y0, c.y0),
    x1: Math.max(a.x1, c.x1), y1: Math.max(a.y1, c.y1),
  }))
  const inside = b.x0 >= QUIET - 0.1 && b.y0 >= QUIET - 0.1 &&
                 b.x1 <= QUIET + n + 0.1 && b.y1 <= QUIET + n + 0.1
  // the ink's bounding box is the grid itself: the finders touch all four
  // corners of every QR, so anything else means the symbol moved
  const exact = near(b.x0, QUIET, 0.1) && near(b.x1, QUIET + n, 0.1)
  ok(`${id} ink stays on the grid`, inside && exact,
     `[${b.x0.toFixed(2)}, ${b.x1.toFixed(2)}] of [${QUIET}, ${QUIET + n}]`)
}

console.log('\nsquare modules with square eyes still reduce to merged runs')
// Square eyes draw the 7x7 ring and 3x3 core that are already in the grid, so
// this case must stay on the rect fast path — it is most of a sheet, and the
// old geometry-only output is the regression baseline.
{
  const it = item('sty-square')
  const n = it.modules
  const bits = unpack(it.matrix, n)
  const ps = pieces(bits, n, styleOf(it))
  const dark0 = bits.reduce((a, v) => a + v, 0)
  ok('one rects piece', ps.length === 1 && ps[0].kind === 'rects')
  const area = ps[0].kind === 'rects' ? ps[0].rects.reduce((a, [, , w, h]) => a + w * h, 0) : -1
  ok('inked area equals the module count', area === dark0, `${area} of ${dark0}`)
  ok('bare code takes the same path',
     JSON.stringify(pieces(bits, n, styleOf({ ...it, dot: 'square' }))) === JSON.stringify(ps))
}

console.log('\nevery dot style emits the shapes it claims')
for (const [id, want] of [['sty-rounded', 'cell'], ['sty-dots', 'dot'],
                          ['sty-classy', 'classy']] as const) {
  const it = item(id)
  const n = it.modules
  const ps = pieces(unpack(it.matrix, n), n, styleOf(it))
  const body = ps[0]
  const arcs = body.kind === 'path' ? body.segs.filter(s => s.t === 'A').length : 0
  ok(`${id} is ${want} and curved`, DOTS[it.dot].kind === want && arcs > 0,
     `${arcs} arcs, ${ps.length} pieces`)
  ok(`${id} punches its finder rings with even-odd`,
     ps.some(p => p.kind === 'path' && p.evenOdd))
}

console.log('\na module lands at the physical size the arithmetic says')
// 65 modules + two 4-module quiet zones is 73 across; at 44 mm that is
// 0.60274 mm a module, which is the figure STICKERS.md quotes and the one
// lib/media.ts judges against a floor.
{
  const n = 65, size = 44
  const m = size / across(n)
  ok('pitch at 44 mm', near(m, 0.6027, 0.0001), `${m.toFixed(5)} mm/module`)
  ok('sheet.ts agrees', near(pitch(n, size), m, 1e-12))
  const s = sheet('probe', 'print-then-cut', DEFAULTS.gutter, 0, [styled(item('sty-dots'))])
  // a `dots` module is a circle of radius half a module
  const radii = [...s.svg.matchAll(/A([\d.]+) /g)].map(x => +x[1])
  ok('dots radius is half a module', near(radii[0], m / 2, 0.0005),
     `${radii[0]} mm, want ${(m / 2).toFixed(4)}`)
  const tight = sheet('probe', 'print-then-cut', DEFAULTS.gutter, 0,
                      [styled(item('sty-dots-tight'))])
  const tr = [...tight.svg.matchAll(/A([\d.]+) /g)].map(x => +x[1])[0]
  ok('dots-tight radius is 1.08 of that', near(tr, m * 0.54, 0.0005),
     `${tr} mm, want ${(m * 0.54).toFixed(4)}`)
  // The symbol's ink spans each cut inset by its quiet zone — the finder
  // patterns reach all four corners of the grid, so the outermost drawn
  // coordinate on the sheet is the leftmost cut plus four modules, and the
  // rightmost cut plus sixty-nine. Checked in both writers' own units, since
  // getting the unit wrong is exactly the bug that turns a 44 mm sticker into
  // a 15 mm one.
  const x0 = Math.min(...s.placed.map(p => p.cut.x))
  const x1 = Math.max(...s.placed.map(p => p.cut.x))
  const svgXs = [...s.svg.matchAll(/[ML]([\d.]+) /g)].map(v => +v[1])
  ok('SVG ink spans the cuts less their quiet zones',
     near(Math.min(...svgXs), x0 + QUIET * m, 0.01) &&
     near(Math.max(...svgXs), x1 + (QUIET + n) * m, 0.01),
     `${Math.min(...svgXs).toFixed(3)}..${Math.max(...svgXs).toFixed(3)} mm, ` +
     `cuts at ${x0.toFixed(3)}..${x1.toFixed(3)}`)
  const MM_TO_PT = 72 / 25.4
  const pdfXs = [...s.pdf.matchAll(/^([\d.]+) [\d.]+ [ml]$/gm)].map(v => +v[1])
  ok('PDF ink spans the same cuts, in points',
     near(Math.min(...pdfXs), (x0 + QUIET * m) * MM_TO_PT, 0.02) &&
     near(Math.max(...pdfXs), (x1 + (QUIET + n) * m) * MM_TO_PT, 0.02),
     `${Math.min(...pdfXs).toFixed(3)}..${Math.max(...pdfXs).toFixed(3)} pt`)
}

// ------------------------------------------------------------------ colour

console.log('\ncolour and shape reach both writers')
{
  const red = sheet('probe', 'print-then-cut', DEFAULTS.gutter, 0, [styled(item('pal-red'))])
  ok('SVG fills pal-red red', red.svg.includes('fill="#ff2b2b"'))
  ok('PDF fills pal-red red', red.pdf.includes('1 0.169 0.169 rg'))
  ok('PDF draws curves, not just rects', (red.pdf.match(/ c$/gm) ?? []).length > 100,
     `${(red.pdf.match(/ c$/gm) ?? []).length} cubics`)
  ok('PDF still fills with even-odd where the rings need it', red.pdf.includes('f*'))

  const plain = sheet('probe', 'print-then-cut', DEFAULTS.gutter, 0, [bare(item('pal-red'))])
  ok('a bare code is still black', plain.svg.includes('fill="#000000"') &&
     !plain.svg.includes('#ff2b2b'))
  ok('a bare code is still rects only', !plain.svg.includes('<path'))

  const grad = sheet('probe', 'print-then-cut', DEFAULTS.gutter, 0, [styled(item('pal-grad'))])
  ok('SVG carries the gradient', grad.svg.includes('<linearGradient id="grad-pal-grad"') &&
     grad.svg.includes('fill="url(#grad-pal-grad)"'))
  ok('PDF carries an axial shading', grad.pdf.includes('/ShadingType 2') &&
     grad.pdf.includes('/Sh0 sh') && grad.pdf.includes('/Shading<<'))
  // one shading per fill element, so each gets the ramp SVG's bounding box
  // would give it: body, the three rings as one even-odd path, three cores
  const shCount = (grad.pdf.match(/\/ShadingType 2/g) ?? []).length
  const pieceCount = pieces(unpack(item('pal-grad').matrix, 65), 65,
                            styleOf(item('pal-grad'))).length
  ok('one shading per piece per sticker', shCount === pieceCount * grad.placed.length,
     `${shCount} for ${grad.placed.length} stickers of ${pieceCount} pieces`)

  const inv = sheet('probe', 'vendor', 0, 3, [styled(dark)])
  ok('an inverted code keeps its plate and inverts its ink',
     inv.svg.includes('fill="#000000"') && inv.svg.includes('fill="#ffffff"'))
}

// ------------------------------------------------------------- the plate

/** the background plate drawn for the first sticker, as width in mm */
function plateWidth(svg: string, cutW: number) {
  const widths = [...svg.matchAll(
    /<rect x="[-\d.]+" y="[-\d.]+" width="([\d.]+)" height="[\d.]+" fill="#[0-9a-f]{3,6}"\/>/g)]
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
  const s = sheet('probe', mode as CutMode, gutter, bleed, [styled(light), styled(dark)])
  const w = plateWidth(s.svg, 44)
  ok(`${mode} gutter ${(+gutter).toFixed(2)}`, Math.abs(w - want) < 0.01, `${w} mm — ${why}`)
}

console.log('\nplates never overlap a neighbouring cut, at any gutter')
for (const g of [0, 1, 2, DEFAULTS.gutter, 12]) {
  const s = sheet('probe', 'vendor', g, 3, [styled(light), styled(dark)])
  const w = plateWidth(s.svg, 44)
  const spread = (w - 44) / 2
  // the file rounds coordinates to 3 decimals, so allow half a micron of it
  ok(`gutter ${g.toFixed(2)}`, spread <= g / 2 + 0.001,
     `plate spreads ${spread.toFixed(3)} mm into a ${(g / 2).toFixed(3)} mm half-gutter`)
}

// -------------------------------------------------- artefacts to decode

// Nothing here ships on looks: gen/sheets.py rasterises each of these with an
// independent renderer (Chrome for the SVG, poppler for the PDF), decodes every
// sticker, and measures one of each code with gen/robust.py. The index tells it
// where each sticker is, so the mm geometry is single-sourced from lib/sheet.ts.
const sheets: Sheet[] = [
  // the geometry-only regression: the pair and the modes that were verified
  // 15/15 and 24/24 before the exporters carried a style
  sheet('plain', 'print-then-cut', DEFAULTS.gutter, 3, [bare(light), bare(dark)]),
  sheet('plain-hostile', 'vendor', 0, 3, [bare(light), bare(dark)]),
  // the two the brief names, each styled, on an ordinary sheet
  sheet('pal-red', 'print-then-cut', DEFAULTS.gutter, 3, [styled(item('pal-red'))]),
  sheet('sty-dots', 'print-then-cut', DEFAULTS.gutter, 3, [styled(item('sty-dots'))]),
  // the hardest shape and the hardest fill
  sheet('sty-dots-tight', 'print-then-cut', DEFAULTS.gutter, 3, [styled(item('sty-dots-tight'))]),
  sheet('pal-grad', 'print-then-cut', DEFAULTS.gutter, 3, [styled(item('pal-grad'))]),
  sheet('sty-classy-rounded', 'print-then-cut', DEFAULTS.gutter, 3,
        [styled(item('sty-classy-rounded'))]),
  // and the hostile one, styled: vendor, zero gutter, light and inverted
  // alternating, every plate pushing at its neighbour's quiet zone
  sheet('styled-hostile', 'vendor', 0, 3, [styled(item('pal-red')), styled(dark)]),
]

for (const s of sheets) {
  writeFileSync(`${OUT}/${s.name}.svg`, s.svg)
  writeFileSync(`${OUT}/${s.name}.pdf`, Buffer.from(s.pdf, 'latin1'))
}
writeFileSync(`${OUT}/index.json`, JSON.stringify({
  url: man.url,
  sheets: sheets.map(s => ({
    name: s.name,
    paper: { w: s.lay.paper.w, h: s.lay.paper.h },
    mode: s.lay.mode,
    expect: s.placed.length,
    styled: s.placed.some(p => !!s.codes[p.id].style),
    placed: s.placed.map(p => ({
      id: p.id, modules: p.modules,
      x: p.cut.x, y: p.cut.y, w: p.cut.w, h: p.cut.h,
    })),
  })),
}, null, 1))

console.log('\nwrote the decode harness to work/sheets/')
for (const s of sheets)
  console.log(`  ${s.name.padEnd(20)} ${String(s.placed.length).padStart(2)} up  ` +
              `${s.lay.mode.padEnd(15)} svg ${String(s.svg.length).padStart(7)}B  ` +
              `pdf ${String(s.pdf.length).padStart(7)}B`)
console.log('  decode and measure them:  uv run --with pillow --with numpy --with segno ' +
            '--with zxing-cpp python3 gen/sheets.py --url ' + man.url)

console.log(fails ? `\n${fails} FAILED` : '\nall checks passed')
process.exit(fails ? 1 : 0)
