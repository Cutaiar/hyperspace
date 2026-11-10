/** Where a code ends up, and whether it survives getting there.
 *
 *  This is what merged the old `tiles` page into the gallery. Tiles asked one
 *  question — is the art code readable at the size the contact page uses — by
 *  pinning two fixed pixel sizes. That question generalises: every destination
 *  is the same comparison in a different unit, so a medium supplies the size
 *  and the floor, and every code gets a verdict against it.
 *
 *  Two kinds of floor, and the difference matters:
 *
 *  MEASURED — screen media use the code's own `min_ppm` from the manifest,
 *  which gen/robust.py measured by degrading the real rendered file until
 *  zxing lost it. That is a floor for a clean synthetic image and a patient
 *  decoder, so it is multiplied by `safety` to stand in for a phone held at
 *  arm's length in bad light. The factor is visible and adjustable because it
 *  is a judgement, not a measurement.
 *
 *  RULE OF THUMB — print and projection floors are conventions, not things
 *  measured here. 0.6 mm per module is the usual comfortable minimum for phone
 *  scanning. The etch floor is a guess until a test plate says otherwise, and
 *  the projection floor assumes a module must subtend about a milliradian.
 *  Treat all three as a starting point to test, not an answer.
 */
import { across, type Item } from './manifest'

export type Medium = {
  id: string
  label: string
  group: 'Screen' | 'Print' | 'Projected'
  /** rendered size of the whole symbol, quiet zone included */
  size: number
  unit: 'px' | 'mm'
  /** screen only: multiplier on the measured min_ppm */
  safety?: number
  /** print only: floor in mm per module */
  floorMm?: number
  /** projected only: viewing distance in metres, floor derived from it */
  distanceM?: number
  /** print only: sheet to tile onto */
  sheet?: 'letter-ptc'
  measured: boolean
  blurb: string
}

/** Cricut's published Print Then Cut usable area on US Letter, in mm. */
export const SHEET = { w: 7.44 * 25.4, h: 9.94 * 25.4, gutter: (3 / 16) * 25.4 }

export const MEDIA: Medium[] = [
  { id: 'screen-200', label: 'Contact page, 200px', group: 'Screen', size: 200, unit: 'px',
    safety: 3, measured: true,
    blurb: 'What the linked page renders today.' },
  { id: 'screen-400', label: 'Contact page, 400px', group: 'Screen', size: 400, unit: 'px',
    safety: 3, measured: true,
    blurb: 'What the art codes have always wanted.' },
  { id: 'sticker-35', label: 'Sticker, 35mm', group: 'Print', size: 35, unit: 'mm',
    floorMm: 0.6, sheet: 'letter-ptc', measured: false,
    blurb: 'Small enough for a laptop lid, and the first size that gets tight.' },
  { id: 'sticker-44', label: 'Sticker, 44mm', group: 'Print', size: 44, unit: 'mm',
    floorMm: 0.6, sheet: 'letter-ptc', measured: false,
    blurb: 'The smallest a 65-module code clears 0.6 mm per module at.' },
  { id: 'sticker-50', label: 'Sticker, 50mm', group: 'Print', size: 50, unit: 'mm',
    floorMm: 0.6, sheet: 'letter-ptc', measured: false,
    blurb: 'Comfortable headroom, twelve to a Letter sheet.' },
  { id: 'etch-60', label: 'Etched plate, 60mm', group: 'Print', size: 60, unit: 'mm',
    floorMm: 1.0, measured: false,
    blurb: 'The 1.0 mm floor is a guess. Kerf and undercut are process-specific — one test plate settles it.' },
  { id: 'proj-20m', label: 'Projected, seen from 20m', group: 'Projected', size: 2000, unit: 'mm',
    distanceM: 20, measured: false,
    blurb: 'A 2 m code on the wall at the end of a set. Walk to the back row and try it before believing this.' },
]

export type Verdict = {
  pitch: number
  floor: number
  unit: 'px' | 'mm'
  ratio: number
  status: 'ok' | 'tight' | 'fail'
  measured: boolean
}

export function verdict(item: Item, m: Medium): Verdict {
  const pitch = m.size / across(item.modules)
  let floor: number
  if (m.unit === 'px') floor = (item.min_ppm ?? 99) * (m.safety ?? 1)
  else if (m.distanceM) floor = m.distanceM * 1000 * 0.001   // ~1 mrad per module
  else floor = m.floorMm ?? 0.6
  const ratio = pitch / floor
  return {
    pitch, floor, unit: m.unit, ratio, measured: m.measured,
    status: ratio >= 1 ? 'ok' : ratio >= 0.75 ? 'tight' : 'fail',
  }
}

/** How many of these tile onto one print-then-cut Letter sheet. */
export function perSheet(m: Medium) {
  if (!m.sheet || m.unit !== 'mm') return null
  const pitch = m.size + SHEET.gutter
  const cols = Math.floor(SHEET.w / pitch)
  const rows = Math.floor(SHEET.h / pitch)
  return { cols, rows, total: cols * rows }
}
