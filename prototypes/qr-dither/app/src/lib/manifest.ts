/** The generators' output contract. gen/gallery.py writes this file. */
import type { EyeStyle, Style } from './style'

export const QUIET = 4

export type Item = {
  id: string
  file: string
  title: string
  note: string
  section: 'shapes' | 'styles' | 'palettes'
  modules: number
  bytes: number
  decodes: boolean
  dark: boolean
  pose: string
  stroke: number
  version: number
  /** which solid, and which family it belongs to — gen/polytopes.py's taxonomy */
  subject?: string
  family?: string
  dot: string
  /** The rest of what gen/gallery.py handed style.to_svg. Optional only
   *  because a manifest generated before the exporters could carry a style
   *  has none; styleOf() falls back to style.to_svg's own defaults. */
  eye_frame?: EyeStyle
  eye_core?: EyeStyle
  fg?: string
  fg2?: string | null
  bg?: string
  /** corner radius of the background plate, in modules */
  plate_radius?: number
  style_eyes?: boolean
  /** measured: fewest camera pixels per module that still decoded */
  min_ppm: number | null
  /** measured: Gaussian sigma in MODULES at which it stopped decoding */
  blur: number
  /** measured: peak added brightness, as a fraction of full white, survived */
  flash: number
  /** base64, row-major, MSB first, bit i = y * n + x */
  matrix: string
}

export type Baseline = {
  ecc: string
  version: number
  modules: number
  min_ppm: number | null
  blur: number
  flash: number
}

/** One solid: what it is, and what was tried and rejected.
 *
 *  `vertices` and `edges` are counted off the real geometry in
 *  gen/polytopes.py rather than declared, so they cannot describe a shape that
 *  is not there. `dim` is declared, because a 3-cube sits in the w = 0
 *  hyperplane and its vertices are 4-tuples like everything else. */
export type Subject = {
  id: string
  label: string
  dim: number
  vertices: number
  edges: number
  /** pose ids in POSES; empty means nothing about this solid survived */
  poses: string[]
  /** rendered and rejected by eye at 65 modules, and why */
  rejected: { pose: string; why: string }[]
}

export type Family = {
  id: string
  label: string
  note: string
  subjects: Subject[]
}

export type Manifest = {
  url: string
  items: Item[]
  baselines: Baseline[]
  /** the whole taxonomy, members with no still included */
  families?: Family[]
  matrix_encoding: string
}

/** Modules across the whole symbol, quiet zone included — the SVG's viewBox. */
export const across = (modules: number) => modules + 2 * QUIET

/** A manifest item's style, as lib/style.ts wants it.
 *
 *  The manifest is the single source of truth for what exists, so the
 *  renderer's arguments belong in it next to the grid they apply to — a
 *  lookup table in the app would be a second place for the same facts to
 *  drift from. The defaults mirror style.to_svg's signature.
 */
export function styleOf(it: Item): Style {
  return {
    dot: it.dot ?? 'square',
    eyeFrame: it.eye_frame ?? 'square',
    eyeCore: it.eye_core ?? 'square',
    fg: it.fg ?? '#000000',
    fg2: it.fg2 ?? null,
    bg: it.bg ?? '#ffffff',
    plateRadius: it.plate_radius ?? 0,
    styleEyes: it.style_eyes ?? true,
  }
}

export function unpack(matrix: string, n: number): Uint8Array {
  const bin = atob(matrix)
  const out = new Uint8Array(n * n)
  for (let i = 0; i < n * n; i++)
    out[i] = (bin.charCodeAt(i >> 3) >> (7 - (i & 7))) & 1
  return out
}
