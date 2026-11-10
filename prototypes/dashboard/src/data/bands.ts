// The six frequency bands and the rotation plane each one drives.
// Mirrors BANDS in hyperspace-python/hyperspace/bands.py.
export type Band = {
  name: string
  plane: string
  lo: number
  hi: number
  dir: 1 | -1
}

export const BANDS: Band[] = [
  { name: "SUB", plane: "ZW", lo: 20, hi: 60, dir: 1 },
  { name: "BASS", plane: "XW", lo: 60, hi: 160, dir: 1 },
  { name: "MIDB", plane: "YW", lo: 160, hi: 400, dir: -1 },
  { name: "MID", plane: "XY", lo: 400, hi: 1200, dir: -1 },
  { name: "UPR", plane: "XZ", lo: 1200, hi: 4000, dir: 1 },
  { name: "AIR", plane: "YZ", lo: 4000, hi: 14000, dir: -1 },
]

// A deterministic stand-in for a live analyzer frame: 180 ticks of
// per-band level. Seeded so the page renders the same every time.
function mulberry32(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export type Tick = { t: number } & Record<string, number>

export function makeTicks(count = 180): Tick[] {
  const rand = mulberry32(0x4d21)
  const state = BANDS.map(() => 0.4)
  const ticks: Tick[] = []
  for (let i = 0; i < count; i++) {
    const row: Tick = { t: i }
    BANDS.forEach((b, k) => {
      // lower bands move slower and sit higher, like real program material
      const inertia = 0.82 - k * 0.07
      const drive = rand() * (1 - k * 0.09)
      state[k] = state[k] * inertia + drive * (1 - inertia)
      row[b.name] = Number((state[k] * 2.6).toFixed(3)) // CEIL = 2.6
    })
    ticks.push(row)
  }
  return ticks
}
