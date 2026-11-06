/** The generators' output contract. gen/gallery.py writes this file. */
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
  dot: string
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

export type Manifest = {
  url: string
  items: Item[]
  baselines: Baseline[]
  matrix_encoding: string
}

/** Modules across the whole symbol, quiet zone included — the SVG's viewBox. */
export const across = (modules: number) => modules + 2 * QUIET

export function unpack(matrix: string, n: number): Uint8Array {
  const bin = atob(matrix)
  const out = new Uint8Array(n * n)
  for (let i = 0; i < n * n; i++)
    out[i] = (bin.charCodeAt(i >> 3) >> (7 - (i & 7))) & 1
  return out
}
