import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { QArtSolver, rasterise, maxSpan } from '@/lib/solver.js'
import { drawStyled, DOT_TYPES, EYE_TYPES } from '@/lib/render.js'

// Six planes, named as hyperspace names them. W rotations apply first so the
// shape folds in its own space; the 3D turn then orients that for viewing,
// which is what makes a grab feel like turning the whole folding object.
const PLANES: [string, [number, number]][] = [
  ['XW', [0, 3]], ['YW', [1, 3]], ['ZW', [2, 3]],
  ['XY', [0, 1]], ['XZ', [0, 2]], ['YZ', [1, 2]],
]
const BLOB: Record<string, string> = {
  gothic: 'solver-gothic', streak: 'solver-streak', clump: 'solver-clump',
  even: 'solver', centre: 'solver-centre',
}
const TEXNOTE: Record<string, string> = {
  gothic: 'Low-frequency noise stretched vertically — heavy strokes with blob and line artefacts. Closest to the stills.',
  streak: 'Strongly vertical noise cells: the leftovers arrive as streaks down the grid.',
  clump:  'Isotropic blobs, a touch calmer than gothic.',
  even:   'A low-discrepancy sequence: leftovers scatter one module at a time, which reads as sparkle.',
  centre: 'Every degree of freedom spent on the middle; the noise piles into a ring at the rim.',
}
const MODENOTE: Record<string, string> = {
  '4d': 'Drag turns XW and YW directly, the way hyperspace maps x and y into W.',
  '3d': 'Drag turns the shape as a rigid 3D body (x → XZ, y → YZ) while the W planes keep folding it — the inverse of hyperspace’s 3D toggle, which holds W instead.',
}
// Update rate is deliberately separate from the angles: the shape keeps turning
// at the same speed, we just re-solve less often. At low rates each redraw is a
// visibly different code, which reads as stepping rather than churn.
const RATES = [1, 2, 3, 4, 6, 8, 12, 15, 20, 24, 30, 60, 0]   // 0 == uncapped
const SENS = 0.006, FRICTION = 0.9

type Engine = {
  ang: Record<string, number>
  rate: Record<string, number>
  opt: { stroke: number; wDist: number; zDist: number; margin: number }
  sty: Record<string, unknown>
  mode: '4d' | '3d'
  paused: boolean; ghost: boolean
  dirty: boolean; pending: boolean
  vx: number; vy: number; down: boolean; px: number; py: number
}

export function LiveSolver() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const stats = useRef<HTMLDivElement>(null)
  const angles = useRef<HTMLDivElement>(null)

  const [ready, setReady] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [texture, setTexture] = useState('gothic')
  const [mode, setMode] = useState<'4d' | '3d'>('4d')
  const [paused, setPaused] = useState(false)
  const [ghost, setGhost] = useState(false)
  const [rateIdx, setRateIdx] = useState(RATES.indexOf(12))
  const [rate, setRate] = useState<Record<string, number>>(
    () => ({ ...Object.fromEntries(PLANES.map(([k]) => [k, 0])), XW: 0.35 }))
  const [opt, setOpt] = useState({ stroke: 3, wDist: 7.0, zDist: 3.0, margin: -0.04 })
  const [sty, setSty] = useState<Record<string, unknown>>({
    dotType: 'square', eyeFrame: 'square', eyeCore: 'square', styleEyes: true,
    fg: '#000000', fg2: '#ff2b2b', bg: '#ffffff', gradient: false, px: 10,
  })

  // The loop reads only this. React state is the source of truth for the
  // controls and is copied in below, so a slider drag re-renders but a frame
  // never does -- the readouts are written straight to the DOM.
  const eng = useRef<Engine>({
    ang: Object.fromEntries(PLANES.map(([k]) => [k, 0])),
    rate: {}, opt, sty, mode: '4d', paused: false, ghost: false,
    dirty: true, pending: true, vx: 0, vy: 0, down: false, px: 0, py: 0,
  })
  const solvers = useRef<Record<string, InstanceType<typeof QArtSolver>>>({})
  const active = useRef<string>('gothic')

  useEffect(() => {
    const e = eng.current
    e.rate = rate; e.opt = opt; e.sty = sty
    e.mode = mode; e.paused = paused; e.ghost = ghost
    e.dirty = true
  }, [rate, opt, sty, mode, paused, ghost])

  // load a texture blob on demand; only gothic is committed
  useEffect(() => {
    let alive = true
    ;(async () => {
      if (solvers.current[texture]) { active.current = texture; eng.current.dirty = true; return }
      try {
        const name = BLOB[texture]
        const [m, b] = await Promise.all([fetch(`/data/${name}.json`), fetch(`/data/${name}.bin`)])
        if (!m.ok || !b.ok) throw new Error('missing')
        const s = new QArtSolver(await m.json(), await b.arrayBuffer())
        if (!alive) return
        solvers.current[texture] = s; active.current = texture
        eng.current.dirty = true; setErr(null); setReady(true)
      } catch {
        if (alive) setErr(texture)
      }
    })()
    return () => { alive = false }
  }, [texture])

  // rateIdx is read inside the loop without restarting it
  const rateIdxRef = useRef(rateIdx)
  useEffect(() => { rateIdxRef.current = rateIdx; eng.current.dirty = true }, [rateIdx])

  // the engine: one effect for the lifetime of the component
  useEffect(() => {
    if (!ready) return
    const c = canvas.current!, ctx = c.getContext('2d')!
    const S0 = solvers.current[active.current]
    const n: number = S0.n, quiet: number = S0.meta.quiet
    const tmp = document.createElement('canvas'); tmp.width = tmp.height = n
    const tctx = tmp.getContext('2d', { willReadFrequently: true })!

    let timer: ReturnType<typeof setTimeout> | undefined
    let raf = 0, last = performance.now(), lastStep = 0, stop = false
    const drawnAt: number[] = []
    const deg = (r: number) => (((r * 180) / Math.PI % 360) + 360) % 360

    // A capped rate is driven by a timer, not requestAnimationFrame: rAF is
    // paced by the compositor and throttled hard in a background or embedded
    // view, so it cannot deliver "4 updates a second" on purpose.
    const schedule = () => {
      clearTimeout(timer)
      if (stop) return
      const hz = RATES[rateIdxRef.current]
      if (!hz) { raf = requestAnimationFrame(step); return }
      // wait for the next deadline rather than a flat interval, so time spent
      // solving does not get added on top of the requested period
      timer = setTimeout(() => step(performance.now()),
                         Math.max(0, lastStep + 1000 / hz - performance.now()))
    }

    const step = (t: number) => {
      const e = eng.current
      // angles advance by real elapsed time, so turn speed is independent of
      // update rate: a lower rate samples the motion, it does not slow it
      const dt = Math.min((t - last) / 1000, 0.25); last = t; lastStep = t
      if (!e.paused)
        for (const [k] of PLANES) if (e.rate[k]) { e.ang[k] += e.rate[k] * dt; e.pending = true }
      if (!e.down && (Math.abs(e.vx) > 1e-5 || Math.abs(e.vy) > 1e-5)) {
        applyDrag(e.vx, e.vy); e.vx *= FRICTION; e.vy *= FRICTION; e.pending = true
      }
      if (e.pending || e.dirty) {
        drawnAt.push(t)
        while (drawnAt.length && t - drawnAt[0] > 1000) drawnAt.shift()
        const t0 = performance.now()
        const want = rasterise(tctx, n, PLANES.map(([k, p]) => [p, e.ang[k]]),
          e.opt.stroke, e.opt.margin,
          { wDist: e.opt.wDist, zDist: e.opt.zDist, span: maxSpan(e.opt.wDist, e.opt.zDist) })
        const mods = solvers.current[active.current].solve(want)
        const ms = performance.now() - t0
        drawStyled(ctx, mods, n, quiet, e.sty)
        if (e.ghost) {                       // the source drawing, under the modules
          const px = e.sty.px as number
          ctx.globalCompositeOperation = 'destination-over'
          ctx.fillStyle = 'rgba(255,120,120,.40)'
          for (let y = 0; y < n; y++) for (let x = 0; x < n; x++)
            if (want[y * n + x]) ctx.fillRect((x + quiet) * px, (y + quiet) * px, px, px)
          ctx.globalCompositeOperation = 'source-over'
        }
        let hit = 0, tot = 0
        for (let i = 0; i < n * n; i++) if (want[i]) { tot++; if (mods[i]) hit++ }
        if (stats.current)
          stats.current.textContent =
            `${ms.toFixed(2)} ms · ${((tot ? hit / tot : 1) * 100).toFixed(0)}% of the drawing held · ${drawnAt.length} /s`
        if (angles.current)
          angles.current.textContent = PLANES.map(([k]) => `${k} ${deg(e.ang[k]).toFixed(0)}°`).join('   ')
        e.dirty = false; e.pending = false
      }
      schedule()
    }
    schedule()
    return () => { stop = true; clearTimeout(timer); cancelAnimationFrame(raf) }
  }, [ready])

  function applyDrag(dx: number, dy: number) {
    const e = eng.current
    if (e.mode === '4d') { e.ang.XW += dx; e.ang.YW += dy }
    else { e.ang.XZ += dx; e.ang.YZ += dy }      // trackball: about Y, about X
  }

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const k = ev.key.toLowerCase()
      if (k === 'g') setGhost(g => !g)
      if (k === 'r') { for (const [p] of PLANES) eng.current.ang[p] = 0
                       eng.current.vx = eng.current.vy = 0; eng.current.dirty = true }
      if (k === ' ') { ev.preventDefault(); setPaused(p => !p) }
    }
    addEventListener('keydown', onKey)
    return () => removeEventListener('keydown', onKey)
  }, [])

  const onDown = (ev: React.PointerEvent) => {
    const e = eng.current
    e.down = true; e.px = ev.clientX; e.py = ev.clientY; e.vx = e.vy = 0
    stage.current?.setPointerCapture(ev.pointerId)
  }
  const onMove = (ev: React.PointerEvent) => {
    const e = eng.current
    if (!e.down) return
    const dx = (ev.clientX - e.px) * SENS, dy = (ev.clientY - e.py) * SENS
    e.px = ev.clientX; e.py = ev.clientY; e.vx = dx; e.vy = dy
    applyDrag(dx, dy); e.pending = true
  }
  const onUp = () => { eng.current.down = false }

  const num = (v: number, d = 2) => v.toFixed(d)

  return (
    <div className="flex flex-wrap items-start gap-8 py-8">
      <div className="flex flex-col items-center gap-3">
        <div ref={stage} onPointerDown={onDown} onPointerMove={onMove}
             onPointerUp={onUp} onPointerCancel={onUp}
             className="cursor-grab touch-none rounded-lg bg-white leading-none active:cursor-grabbing">
          <canvas ref={canvas} className="block size-[min(86vw,460px)] rounded-lg" />
        </div>
        <div ref={stats} className="font-mono text-[11px] tabular-nums text-muted-foreground" />
        <div ref={angles} className="font-mono text-[10px] tabular-nums text-muted-foreground/60" />
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="text-[11px]"
                  onClick={() => setPaused(p => !p)}>{paused ? 'play' : 'pause'}</Button>
          <Button size="sm" variant={ghost ? 'default' : 'outline'} className="text-[11px]"
                  onClick={() => setGhost(g => !g)}>ghost</Button>
          <Button size="sm" variant="outline" className="text-[11px]"
                  onClick={() => { for (const [p] of PLANES) eng.current.ang[p] = 0
                                   eng.current.vx = eng.current.vy = 0; eng.current.dirty = true }}>
            reset
          </Button>
        </div>
      </div>

      <div className="w-[300px] shrink-0 space-y-6">
        <Field label="grab">
          <ToggleGroup type="single" value={mode} variant="outline" size="sm"
                       onValueChange={v => v && setMode(v as '4d' | '3d')}>
            <ToggleGroupItem value="4d" className="text-[11px]">fold (4D)</ToggleGroupItem>
            <ToggleGroupItem value="3d" className="text-[11px]">turn (3D)</ToggleGroupItem>
          </ToggleGroup>
          <Note>{MODENOTE[mode]}</Note>
        </Field>

        <Field label="texture">
          <Select value={texture} onValueChange={setTexture}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              {Object.keys(BLOB).map(k => <SelectItem key={k} value={k}>{k}</SelectItem>)}
            </SelectContent>
          </Select>
          <Note>
            {err === texture
              ? <span className="text-primary">Not built. Run gen/export_js.py --order {texture} --out {BLOB[texture]}</span>
              : TEXNOTE[texture]}
          </Note>
        </Field>

        <Field label="rotation (rad/s)">
          {PLANES.map(([k]) => (
            <Row key={k} name={k} value={num(rate[k])}>
              <Slider value={[rate[k]]} min={-1.5} max={1.5} step={0.01}
                      onValueChange={v => setRate(r => ({ ...r, [k]: v[0] }))} />
            </Row>
          ))}
        </Field>

        <Field label="drawing">
          <Row name="edge" value={`${opt.stroke} mod`}>
            <Slider value={[opt.stroke]} min={1} max={6} step={1}
                    onValueChange={v => setOpt(o => ({ ...o, stroke: v[0] }))} />
          </Row>
          <Row name="w-dist" value={num(opt.wDist, 1)}>
            <Slider value={[opt.wDist]} min={2} max={14} step={0.1}
                    onValueChange={v => setOpt(o => ({ ...o, wDist: v[0] }))} />
          </Row>
          <Row name="z-dist" value={num(opt.zDist, 1)}>
            <Slider value={[opt.zDist]} min={2} max={14} step={0.1}
                    onValueChange={v => setOpt(o => ({ ...o, zDist: v[0] }))} />
          </Row>
          <Row name="margin" value={num(opt.margin)}>
            <Slider value={[opt.margin]} min={-0.1} max={0.3} step={0.01}
                    onValueChange={v => setOpt(o => ({ ...o, margin: v[0] }))} />
          </Row>
          <Row name="update" value={RATES[rateIdx] ? `${RATES[rateIdx]} /s` : 'every frame'}>
            <Slider value={[rateIdx]} min={0} max={RATES.length - 1} step={1}
                    onValueChange={v => setRateIdx(v[0])} />
          </Row>
        </Field>

        <Field label="style">
          {([['dots', 'dotType', DOT_TYPES], ['eye', 'eyeFrame', EYE_TYPES],
             ['core', 'eyeCore', EYE_TYPES]] as const).map(([lbl, key, vals]) => (
            <Row key={key} name={lbl}>
              <Select value={sty[key] as string} onValueChange={v => setSty(s => ({ ...s, [key]: v }))}>
                <SelectTrigger className="h-7 w-full text-[10.5px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(vals as string[]).map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </Row>
          ))}
          <div className="flex items-center gap-3 pt-1">
            {([['ink', 'fg'], ['ink 2', 'fg2'], ['paper', 'bg']] as const).map(([lbl, key]) => (
              <label key={key} className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                <input type="color" value={sty[key] as string}
                       onChange={ev => setSty(s => ({ ...s, [key]: ev.target.value }))}
                       className="size-6 cursor-pointer rounded border border-border bg-transparent p-0.5" />
                {lbl}
              </label>
            ))}
            <Button size="sm" variant={sty.gradient ? 'default' : 'outline'}
                    className="ml-auto h-6 px-2 text-[10px]"
                    onClick={() => setSty(s => ({ ...s, gradient: !s.gradient }))}>grad</Button>
          </div>
          <Row name="detail" value={`${sty.px} px`}>
            <Slider value={[sty.px as number]} min={4} max={16} step={1}
                    onValueChange={v => setSty(s => ({ ...s, px: v[0] }))} />
          </Row>
        </Field>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="text-[10px] uppercase tracking-[0.2em] text-primary">{label}</div>
      {children}
    </div>
  )
}
function Row({ name, value, children }: { name: string; value?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[46px_1fr_64px] items-center gap-2">
      <span className="font-mono text-[10px] text-muted-foreground">{name}</span>
      {children}
      {value !== undefined
        ? <span className="text-right font-mono text-[10px] tabular-nums text-muted-foreground">{value}</span>
        : <span />}
    </div>
  )
}
function Note({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] leading-relaxed text-muted-foreground">{children}</p>
}
