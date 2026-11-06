import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useMirror } from '@/lib/useMirror'
import { QArtSolver, rasterise, maxSpan, minZDist } from '@/lib/solver.js'
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

type Cfg = {
  rate: Record<string, number>
  opt: { stroke: number; wDist: number; zDist: number; margin: number }
  sty: Record<string, unknown>
  mode: '4d' | '3d'
  paused: boolean
  ghost: boolean
  rateIdx: number
}

export function LiveSolver() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const stats = useRef<HTMLDivElement>(null)
  const angles = useRef<HTMLDivElement>(null)

  const [ready, setReady] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [texture, setTexture] = useState('gothic')

  // What the loop owns and React never touches: the pose and the throw.
  const eng = useRef({
    ang: Object.fromEntries(PLANES.map(([k]) => [k, 0])) as Record<string, number>,
    dirty: true, pending: true, vx: 0, vy: 0, down: false, px: 0, py: 0,
  })

  // Everything a control can change lives in ONE mirrored object, so the loop
  // sees a new field the moment it exists. See useMirror for why that matters.
  const { value: cfg, ref: cfgRef, patch } = useMirror<Cfg>(
    {
      rate: { ...Object.fromEntries(PLANES.map(([k]) => [k, 0])), XW: 0.35 },
      opt: { stroke: 3, wDist: 7.0, zDist: 3.0, margin: -0.04 },
      sty: { dotType: 'square', eyeFrame: 'square', eyeCore: 'square', styleEyes: true,
             fg: '#000000', fg2: '#ff2b2b', bg: '#ffffff', gradient: false, px: 10 },
      mode: '4d', paused: false, ghost: false, rateIdx: RATES.indexOf(12),
    },
    () => { eng.current.dirty = true },        // any change at all repaints
  )

  const solvers = useRef<Record<string, InstanceType<typeof QArtSolver>>>({})
  const active = useRef<string>('gothic')

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

  function applyDrag(dx: number, dy: number) {
    const a = eng.current.ang
    if (cfgRef.current.mode === '4d') { a.XW += dx; a.YW += dy }
    else { a.XZ += dx; a.YZ += dy }            // trackball: about Y, about X
  }

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
      const hz = RATES[cfgRef.current.rateIdx]
      if (!hz) { raf = requestAnimationFrame(step); return }
      // wait for the next deadline rather than a flat interval, so time spent
      // solving does not get added on top of the requested period
      timer = setTimeout(() => step(performance.now()),
                         Math.max(0, lastStep + 1000 / hz - performance.now()))
    }

    const step = (t: number) => {
      const e = eng.current, k = cfgRef.current
      // angles advance by real elapsed time, so turn speed is independent of
      // update rate: a lower rate samples the motion, it does not slow it
      const dt = Math.min((t - last) / 1000, 0.25); last = t; lastStep = t
      if (!k.paused)
        for (const [p] of PLANES) if (k.rate[p]) { e.ang[p] += k.rate[p] * dt; e.pending = true }
      if (!e.down && (Math.abs(e.vx) > 1e-5 || Math.abs(e.vy) > 1e-5)) {
        applyDrag(e.vx, e.vy); e.vx *= FRICTION; e.vy *= FRICTION; e.pending = true
      }
      if (e.pending || e.dirty) {
        drawnAt.push(t)
        while (drawnAt.length && t - drawnAt[0] > 1000) drawnAt.shift()
        const t0 = performance.now()
        const want = rasterise(tctx, n, PLANES.map(([p, pl]) => [pl, e.ang[p]]),
          k.opt.stroke, k.opt.margin,
          { wDist: k.opt.wDist, zDist: k.opt.zDist, span: maxSpan(k.opt.wDist, k.opt.zDist) })
        const mods = solvers.current[active.current].solve(want)
        const ms = performance.now() - t0
        drawStyled(ctx, mods, n, quiet, k.sty)
        if (k.ghost) {
          // The source drawing, tinted over the code. This used to ask for
          // destination-over -- "under the modules" -- which can never show:
          // drawStyled fills the whole canvas with opaque paper first, so
          // anything composited behind it is hidden. The button was dead from
          // the day it was written. A translucent pass on top is the version
          // that can actually be seen, and the modules still read through it.
          const px = k.sty.px as number
          ctx.fillStyle = 'rgba(255,64,64,.34)'
          for (let y = 0; y < n; y++) for (let x = 0; x < n; x++)
            if (want[y * n + x]) ctx.fillRect((x + quiet) * px, (y + quiet) * px, px, px)
        }
        let hit = 0, tot = 0
        for (let i = 0; i < n * n; i++) if (want[i]) { tot++; if (mods[i]) hit++ }
        if (stats.current)
          stats.current.textContent =
            `${ms.toFixed(2)} ms · ${((tot ? hit / tot : 1) * 100).toFixed(0)}% of the drawing held · ${drawnAt.length} /s`
        if (angles.current)
          angles.current.textContent = PLANES.map(([p]) => `${p} ${deg(e.ang[p]).toFixed(0)}°`).join('   ')
        e.dirty = false; e.pending = false
      }
      schedule()
    }
    schedule()
    return () => { stop = true; clearTimeout(timer); cancelAnimationFrame(raf) }
  }, [ready])

  const reset = () => {
    const e = eng.current
    for (const [p] of PLANES) e.ang[p] = 0
    e.vx = e.vy = 0; e.dirty = true
  }

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const k = ev.key.toLowerCase()
      if (k === 'g') patch(c => ({ ghost: !c.ghost }))
      if (k === 'r') reset()
      if (k === ' ') { ev.preventDefault(); patch(c => ({ paused: !c.paused })) }
    }
    addEventListener('keydown', onKey)
    return () => removeEventListener('keydown', onKey)
  }, [patch])

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

  // Keep both cameras outside the solid. minZDist is the pole; a little margin
  // past it keeps the span finite rather than merely defined.
  const zFloorFor = (w: number) => Math.ceil(minZDist(w) * 1.06 * 10) / 10
  const zFloor = zFloorFor(cfg.opt.wDist)

  const num = (v: number, d = 2) => v.toFixed(d)
  const setOpt = (p: Partial<Cfg['opt']>) => patch(c => ({ opt: { ...c.opt, ...p } }))
  const setSty = (p: Record<string, unknown>) => patch(c => ({ sty: { ...c.sty, ...p } }))

  return (
    <div className="flex flex-wrap items-start gap-10 pb-24">
      <div className="flex flex-col items-center gap-3">
        <div ref={stage} onPointerDown={onDown} onPointerMove={onMove}
             onPointerUp={onUp} onPointerCancel={onUp}
             className="cursor-grab touch-none rounded-lg bg-white leading-none active:cursor-grabbing">
          <canvas ref={canvas} className="block size-[min(86vw,520px)] rounded-lg" />
        </div>
        <div ref={stats} className="font-mono text-[11px] tabular-nums text-muted-foreground" />
        <div ref={angles} className="font-mono text-[10px] tabular-nums text-muted-foreground/60" />
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="text-[11px]"
                  onClick={() => patch(c => ({ paused: !c.paused }))}>
            {cfg.paused ? 'play' : 'pause'}
          </Button>
          <Button size="sm" variant={cfg.ghost ? 'default' : 'outline'} className="text-[11px]"
                  onClick={() => patch(c => ({ ghost: !c.ghost }))}>ghost</Button>
          <Button size="sm" variant="outline" className="text-[11px]" onClick={reset}>reset</Button>
        </div>
      </div>

      <div className="grid min-w-[280px] flex-1 gap-x-10 gap-y-7 self-start
                      [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]">
        <div className="space-y-6">
          <Field label="grab">
            <ToggleGroup type="single" value={cfg.mode} variant="outline" size="sm"
                         onValueChange={v => v && patch({ mode: v as '4d' | '3d' })}>
              <ToggleGroupItem value="4d" className="text-[11px]">fold (4D)</ToggleGroupItem>
              <ToggleGroupItem value="3d" className="text-[11px]">turn (3D)</ToggleGroupItem>
            </ToggleGroup>
            <Note>{MODENOTE[cfg.mode]}</Note>
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
            {PLANES.map(([p]) => (
              <Row key={p} name={p} value={num(cfg.rate[p])}>
                <Slider value={[cfg.rate[p]]} min={-1.5} max={1.5} step={0.01}
                        onValueChange={v => patch(c => ({ rate: { ...c.rate, [p]: v[0] } }))} />
              </Row>
            ))}
          </Field>
        </div>

        <div className="space-y-6">
          <Field label="drawing">
            <Row name="edge" value={`${cfg.opt.stroke} mod`}>
              <Slider value={[cfg.opt.stroke]} min={1} max={6} step={1}
                      onValueChange={v => setOpt({ stroke: v[0] })} />
            </Row>
            <Row name="w-dist" value={num(cfg.opt.wDist, 1)}>
              <Slider value={[cfg.opt.wDist]} min={2.6} max={14} step={0.1}
                      onValueChange={v => {
                        const w = v[0]
                        // moving the w camera moves the z floor with it
                        setOpt({ wDist: w, zDist: Math.max(cfg.opt.zDist, zFloorFor(w)) })
                      }} />
            </Row>
            <Row name="z-dist" value={num(cfg.opt.zDist, 1)}>
              {/* the z camera has to clear the solid after the w-projection has
                  stretched it, or the span blows up and the drawing vanishes */}
              <Slider value={[cfg.opt.zDist]} min={zFloor} max={14} step={0.1}
                      onValueChange={v => setOpt({ zDist: v[0] })} />
            </Row>
            <Row name="margin" value={num(cfg.opt.margin)}>
              <Slider value={[cfg.opt.margin]} min={-0.1} max={0.3} step={0.01}
                      onValueChange={v => setOpt({ margin: v[0] })} />
            </Row>
            <Row name="update" value={RATES[cfg.rateIdx] ? `${RATES[cfg.rateIdx]} /s` : 'every frame'}>
              <Slider value={[cfg.rateIdx]} min={0} max={RATES.length - 1} step={1}
                      onValueChange={v => patch({ rateIdx: v[0] })} />
            </Row>
          </Field>

          <Field label="style">
            {([['dots', 'dotType', DOT_TYPES], ['eye', 'eyeFrame', EYE_TYPES],
               ['core', 'eyeCore', EYE_TYPES]] as const).map(([lbl, key, vals]) => (
              <Row key={key} name={lbl}>
                <Select value={cfg.sty[key] as string} onValueChange={v => setSty({ [key]: v })}>
                  <SelectTrigger className="h-7 w-full text-[10.5px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {(vals as readonly string[]).map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Row>
            ))}
            <div className="flex items-center gap-3 pt-1">
              {([['ink', 'fg'], ['ink 2', 'fg2'], ['paper', 'bg']] as const).map(([lbl, key]) => (
                <label key={key} className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                  <input type="color" value={cfg.sty[key] as string}
                         onChange={ev => setSty({ [key]: ev.target.value })}
                         className="size-6 cursor-pointer rounded border border-border bg-transparent p-0.5" />
                  {lbl}
                </label>
              ))}
              <Button size="sm" variant={cfg.sty.gradient ? 'default' : 'outline'}
                      className="ml-auto h-6 px-2 text-[10px]"
                      onClick={() => setSty({ gradient: !cfg.sty.gradient })}>grad</Button>
            </div>
            <Row name="detail" value={`${cfg.sty.px} px`}>
              <Slider value={[cfg.sty.px as number]} min={4} max={16} step={1}
                      onValueChange={v => setSty({ px: v[0] })} />
            </Row>
          </Field>
        </div>
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
