/** Render every gallery still a second time, through lib/style.ts.
 *
 *  lib/style.ts claims to be the TypeScript twin of gen/style.py. The way to
 *  find out is not to read both: it is to draw the same 29 codes with each and
 *  rasterise the pair. This writes the TypeScript half to work/twins/, in the
 *  same viewBox style.py uses — one unit to a module — so gen/twins.py can
 *  shoot both with the same Chrome and diff them pixel for pixel.
 *
 *      cd app && npm run twins
 *      uv run --with pillow --with numpy python3 gen/twins.py
 *
 *  Not part of `npm run check`, which stays browser-free.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { QUIET, across, styleOf, unpack, type Item } from '../src/lib/manifest'
import { pieces, svgPath, type Xf } from '../src/lib/style'

const man = JSON.parse(readFileSync('public/data/gallery/manifest.json', 'utf8'))
const OUT = '../work/twins'
mkdirSync(OUT, { recursive: true })

const f = (v: number) => (Math.round(v * 1000) / 1000).toString()
const identity: Xf = { p: (x, y) => [x, y], s: 1 }

for (const it of man.items as Item[]) {
  const n = it.modules, side = across(n)
  const st = styleOf(it)
  const body = pieces(unpack(it.matrix, n), n, st, QUIET).map(p =>
    p.kind === 'rects'
      ? p.rects.map(([x, y, w, h]) =>
          `<rect x="${f(x)}" y="${f(y)}" width="${f(w)}" height="${f(h)}"/>`).join('')
      : `<path${p.evenOdd ? ' fill-rule="evenodd"' : ''} d="${svgPath(p.segs, identity)}"/>`
  ).join('')
  const defs = st.fg2
    ? `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">` +
      `<stop offset="0" stop-color="${st.fg}"/>` +
      `<stop offset="1" stop-color="${st.fg2}"/></linearGradient></defs>`
    : ''
  const rx = st.plateRadius ? ` rx="${f(st.plateRadius)}"` : ''
  writeFileSync(`${OUT}/${it.id}.svg`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${side} ${side}">` +
    `<rect width="${side}" height="${side}" fill="${st.bg}"${rx}/>${defs}` +
    `<g fill="${st.fg2 ? 'url(#g)' : st.fg}">${body}</g></svg>`)
}
console.log(`wrote ${man.items.length} twins to work/twins/`)
console.log('diff them:  uv run --with pillow --with numpy python3 gen/twins.py')
