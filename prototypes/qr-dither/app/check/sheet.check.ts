import { PAPERS, DEFAULTS, layout, usableArea, minSticker, pitch, assign, fitAlong } from '../src/lib/sheet'

let fails = 0
const eq = (name: string, got: unknown, want: unknown, tol = 0) => {
  const ok = typeof got === 'number' && typeof want === 'number'
    ? Math.abs(got - want) <= tol : got === want
  if (!ok) { fails++; console.log(`  FAIL ${name}: got ${got}, want ${want}`) }
  else console.log(`  ok   ${name} = ${typeof got === 'number' ? (got as number).toFixed(2) : got}`)
}

const ptc = (sticker: number) => layout({
  paper: PAPERS.letter, mode: 'print-then-cut' as const, sticker, ...DEFAULTS })

console.log('\nusable area, Letter print-then-cut (Cricut publishes 7.44 x 9.94 in)')
const u = usableArea({ paper: PAPERS.letter, mode: 'print-then-cut', sticker: 40, ...DEFAULTS })
eq('width mm', u.w, 7.44 * 25.4, 0.2)
eq('height mm', u.h, 9.94 * 25.4, 0.2)

console.log('\nminimum sticker at the 0.6 mm/module floor')
eq('art v12 (65 modules)', minSticker(65, 0.6), 43.8, 0.05)
eq('art v15 (77 modules)', minSticker(77, 0.6), 51.0, 0.05)
eq('plain ECC M (29)',     minSticker(29, 0.6), 22.2, 0.05)

console.log('\nper Letter sheet at those sizes')
eq('art v12 cols',  ptc(minSticker(65, 0.6)).cols, 3)
eq('art v12 rows',  ptc(minSticker(65, 0.6)).rows, 5)
eq('art v12 total', ptc(minSticker(65, 0.6)).cells.length, 15)
eq('art v15 total', ptc(minSticker(77, 0.6)).cells.length, 12)
eq('plain total',   ptc(minSticker(29, 0.6)).cells.length, 63)

console.log('\nfixed sticker sizes')
for (const [mm, want] of [[35, 24], [40, 20], [44, 15], [50, 12]] as const)
  eq(`${mm} mm`, ptc(mm).cells.length, want)

console.log('\npitch at 73 modules across')
for (const [mm, want] of [[35, 0.479], [40, 0.548], [44, 0.603], [50, 0.685]] as const)
  eq(`${mm} mm`, pitch(65, mm), want, 0.001)

console.log('\nthe trailing gutter is not charged')
eq('two 100mm at 10mm gutter in 210mm', fitAlong(210, 100, 10), 2)
eq('...but not in 209mm',               fitAlong(209, 100, 10), 1)

console.log('\ngeometry stays inside the usable area')
const L = ptc(44)
const last = L.cells[L.cells.length - 1]
eq('right edge within usable', last.cut.x + last.cut.w <= L.usable.x + L.usable.w + 1e-9, true)
eq('bottom edge within usable', last.cut.y + last.cut.h <= L.usable.y + L.usable.h + 1e-9, true)
eq('block is centred', (L.cells[0].cut.x - L.usable.x) -
   ((L.usable.x + L.usable.w) - (last.cut.x + last.cut.w)), 0, 1e-9)

console.log('\nassign fills the sheet')
const picks = [{ id: 'a', modules: 65 }, { id: 'b', modules: 65 }]
const placed = assign(L, picks)
eq('every cell filled', placed.length, L.cells.length)
eq('alternates a/b', placed.slice(0, 4).map(p => p.id).join(''), 'abab')
const counted = assign(L, [{ id: 'x', modules: 65, count: 4 }, { id: 'y', modules: 65 }])
eq('explicit count honoured', counted.filter(p => p.id === 'x').length, 4)

console.log('\nwarnings fire')
eq('vendor bleed overlap warns',
   layout({ paper: PAPERS.letter, mode: 'vendor', sticker: 44, ...DEFAULTS })
     .warnings.some(w => w.includes('bleed')), true)
eq('too small to fit warns', ptc(400).warnings.some(w => w.includes('does not fit')), true)

console.log(fails ? `\n${fails} FAILED` : '\nall checks passed')
process.exit(fails ? 1 : 0)
