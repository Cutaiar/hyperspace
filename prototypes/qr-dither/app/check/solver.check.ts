import { maxSpan, minZDist, RADIUS } from '../src/lib/solver.js'

let fails = 0
const ok = (name: string, cond: boolean, detail = '') => {
  if (cond) console.log(`  ok   ${name}${detail && ' — ' + detail}`)
  else { fails++; console.log(`  FAIL ${name}${detail && ' — ' + detail}`) }
}

console.log('\ncircumradius and the camera floor it implies')
ok('RADIUS is 2', RADIUS === 2)
ok('minZDist(7) ≈ 2.80', Math.abs(minZDist(7) - 2.8) < 0.01, minZDist(7).toFixed(2))
ok('minZDist(4.2) ≈ 3.82', Math.abs(minZDist(4.2) - 3.818) < 0.01, minZDist(4.2).toFixed(2))
ok('minZDist(2) is unreachable', !Number.isFinite(minZDist(2)))

console.log('\nspan stays sane at the settings that used to explode')
// before the guard: (2,3) -> ~18895, (4.2,2.2) -> ~2831, (2.5,2.5) -> ~26631
for (const [w, z] of [[2, 3], [4.2, 2.2], [2.5, 2.5], [3, 2], [2, 2]] as const) {
  const s = maxSpan(w, z, 3000)
  ok(`maxSpan(${w}, ${z}) bounded`, Number.isFinite(s) && s > 0 && s <= 24, s.toFixed(2))
}

console.log('\nand the ordinary settings are unchanged')
for (const [w, z, want] of [[7, 3, 2.9], [9, 2.6, 3.34], [14, 4, 2.34]] as const) {
  const s = maxSpan(w, z, 4000)
  ok(`maxSpan(${w}, ${z}) ≈ ${want}`, Math.abs(s - want) < 0.35, s.toFixed(2))
}

console.log('\na drawing at these spans is still visible')
for (const [w, z] of [[7, 3], [4.2, 2.2]] as const) {
  const scale = (65 * (1 - 2 * -0.04)) / (2 * maxSpan(w, z, 3000))
  ok(`scale at (${w}, ${z}) keeps the solid on the grid`, scale > 1,
     `${scale.toFixed(2)} modules per unit`)
}

console.log(fails ? `\n${fails} FAILED` : '\nall checks passed')
process.exit(fails ? 1 : 0)
