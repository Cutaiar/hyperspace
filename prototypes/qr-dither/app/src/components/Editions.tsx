import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectGroup, SelectItem,
  SelectLabel, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { unpack } from '@/lib/manifest'
import { QArtSolver } from '@/lib/solver.js'
import { drawStyled, DOT_TYPES, EYE_TYPES } from '@/lib/render.js'

/** Browse the edition space: a pose, a constant, a treatment.
 *
 *  The factorisation does not depend on WHICH constant is pinned — pivots are
 *  chosen by position and only their values are read when solving — so one
 *  blob per digit count serves all fifteen numbers and swapping π for φ is a
 *  0.2 ms re-solve. The pose is a target bitmap, 529 bytes, shipped by
 *  gen/explore_data.py rather than ported: solver.js knows the tesseract and
 *  nothing else, and that is not worth fixing for a picker.
 *
 *  What you see here is the live approximation. The blobs use a fixed pivot
 *  order, because an order that ranks by the drawing needs one blob per pose.
 *  The baked version spends its budget on the ink first and comes out 11 to 15
 *  points better. The panel says so rather than letting it surprise you.
 */
type Target = {
  id: string; pose: string; variant: 'original' | 'repositioned'
  subject: string; subject_label: string
  family: string; family_label: string
  stroke: number; ink: number; lost: number; ceiling: number
  settings: { w_dist: number; z_dist: number; margin: number }
  bits: string
}
type Const = { id: string; glyph: string; name: string; note: string; digits: string }

const BLOB: Record<number, string> = {
  0: 'solver-gothic', 24: 'solver-gothic-d24', 48: 'solver-gothic-d48',
}

export function Editions() {
  const [targets, setTargets] = useState<Target[] | null>(null)
  const [consts, setConsts] = useState<Const[]>([])
  const [meta, setMeta] = useState<{ modules: number; quiet: number } | null>(null)
  const [poseId, setPoseId] = useState('tess_tilt')
  const [variant, setVariant] = useState<'original' | 'repositioned'>('repositioned')
  const [constId, setConstId] = useState('pi')
  const [digits, setDigits] = useState(24)
  const [sty, setSty] = useState<Record<string, unknown>>({
    dotType: 'extra-rounded', eyeFrame: 'rounded', eyeCore: 'rounded',
    fg: '#000000', bg: '#ffffff', px: 11, styleEyes: true,
  })
  const [copied, setCopied] = useState(false)
  const solvers = useRef<Record<number, InstanceType<typeof QArtSolver>>>({})
  const [ready, setReady] = useState(0)
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    fetch('/data/editions/targets.json').then(r => r.json()).then(j => {
      setTargets(j.targets); setMeta({ modules: j.modules, quiet: j.quiet })
    })
    fetch('/data/editions/constants.json').then(r => r.json()).then(j => setConsts(j.constants))
  }, [])

  // one blob per digit count, fetched on demand and kept
  useEffect(() => {
    let alive = true
    if (solvers.current[digits]) { setReady(r => r + 1); return }
    const stem = BLOB[digits]
    Promise.all([
      fetch(`/data/${stem}.json`).then(r => r.json()),
      fetch(`/data/${stem}.bin`).then(r => r.arrayBuffer()),
    ]).then(([m, buf]) => {
      if (!alive) return
      solvers.current[digits] = new QArtSolver(m, buf)
      setReady(r => r + 1)
    }).catch(() => { /* a missing blob just leaves the canvas as it was */ })
    return () => { alive = false }
  }, [digits])

  const target = useMemo(
    () => targets?.find(t => t.pose === poseId && t.variant === variant) ?? null,
    [targets, poseId, variant])
  const konst = useMemo(() => consts.find(c => c.id === constId), [consts, constId])

  useEffect(() => {
    const s = solvers.current[digits]
    const ctx = canvas.current?.getContext('2d')
    if (!s || !ctx || !target || !meta) return
    if (digits && konst) s.setDigits(konst.digits)
    const n = meta.modules
    const bits = unpack(target.bits, n)
    const want = new Uint8Array(n * n)
    for (let i = 0; i < n * n; i++) want[i] = bits[i]
    drawStyled(ctx, s.solve(want), n, meta.quiet, sty)
  }, [ready, digits, target, konst, sty, meta])

  const budget = 2415 - digits * 3
  const cmd = target && konst
    ? `uv run --with pyqart --with pillow --with numpy --with mpmath \\\n` +
      `  --with segno --with zxing-cpp python3 gen/editions.py \\\n` +
      `  --url https://hyperspace.cutaiar.io --digits ${digits}\n` +
      `# pose ${target.pose}  stroke ${target.stroke}  constant ${konst.id}\n` +
      `# w_dist ${target.settings.w_dist}  z_dist ${target.settings.z_dist}` +
      `  margin ${target.settings.margin}`
    : ''

  if (!targets || !meta) return <div className="py-10 text-sm text-muted-foreground">loading…</div>

  const families = [...new Map(targets.map(t => [t.family, t.family_label])).entries()]

  return (
    <div className="grid gap-x-12 gap-y-8 pb-24 lg:grid-cols-[330px_minmax(0,1fr)]">
      <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
        <p className="m-0 text-[11.5px] leading-[1.75] text-muted-foreground">
          A pose and a number. The solver re-derives the whole code when you change either —
          swapping the constant costs nothing, because the factorisation picks its pivots by
          position and only reads their values when it solves.
        </p>

        <div className="space-y-3">
          <Select value={poseId} onValueChange={setPoseId}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              {families.map(([fid, flabel]) => (
                <SelectGroup key={fid}>
                  <SelectLabel>{flabel}</SelectLabel>
                  {targets.filter(t => t.family === fid && t.variant === 'original').map(t => (
                    <SelectItem key={t.pose} value={t.pose}>{t.pose}</SelectItem>
                  ))}
                </SelectGroup>
              ))}
            </SelectContent>
          </Select>

          <ToggleGroup type="single" value={variant} variant="outline" size="sm" className="w-full"
                       onValueChange={v => v && setVariant(v as typeof variant)}>
            <ToggleGroupItem value="original" className="flex-1 text-[10.5px]">as published</ToggleGroupItem>
            <ToggleGroupItem value="repositioned" className="flex-1 text-[10.5px]">repositioned</ToggleGroupItem>
          </ToggleGroup>

          <Select value={constId} onValueChange={setConstId}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              {consts.map(c => (
                <SelectItem key={c.id} value={c.id}>
                  <span className="font-mono">{c.glyph}</span>&nbsp; {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <ToggleGroup type="single" value={String(digits)} variant="outline" size="sm"
                       className="w-full" onValueChange={v => v && setDigits(+v)}>
            {[0, 24, 48].map(d => (
              <ToggleGroupItem key={d} value={String(d)} className="flex-1 text-[10.5px]">
                {d === 0 ? 'no digits' : `${d} digits`}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>

        <Separator />

        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-primary">treatment</div>
          <div className="grid grid-cols-3 gap-1.5">
            {(['dotType', 'eyeFrame', 'eyeCore'] as const).map(k => (
              <Select key={k} value={sty[k] as string}
                      onValueChange={v => setSty(s => ({ ...s, [k]: v }))}>
                <SelectTrigger className="h-7 text-[10px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(k === 'dotType' ? DOT_TYPES : EYE_TYPES).map((o: string) => (
                    <SelectItem key={o} value={o} className="text-[11px]">{o}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ))}
          </div>
          <div className="flex items-center gap-2">
            {(['fg', 'bg'] as const).map(k => (
              <label key={k} className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                {k}
                <input type="color" value={sty[k] as string} id={`ed-${k}`}
                       onChange={e => setSty(s => ({ ...s, [k]: e.target.value }))}
                       className="h-6 w-8 cursor-pointer rounded border border-border bg-transparent" />
              </label>
            ))}
            <Button size="sm" variant={sty.gradient ? 'default' : 'outline'}
                    className="h-6 px-2 text-[10px]"
                    onClick={() => setSty(s => ({ ...s, gradient: !s.gradient, fg2: '#ff2b2b' }))}>
              gradient
            </Button>
          </div>
        </div>

        <Separator />

        {target && (
          <div className="space-y-1 font-mono text-[11px] text-muted-foreground">
            <div>
              ink <b className="text-foreground">{target.ink}</b> modules ·
              {' '}budget <b className="text-foreground">{budget}</b>
            </div>
            <div className={target.lost ? 'text-primary' : 'text-emerald-400'}>
              {target.lost} lost to QR furniture · ceiling {target.ceiling}%
            </div>
            <div className="text-muted-foreground/70">
              {digits ? `${digits} digits cost ${digits * 3} modules` : 'no digits pinned'}
            </div>
          </div>
        )}

        {konst && digits > 0 && (
          <div className="rounded-md border border-border/60 bg-muted/30 p-3">
            <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.13em] text-muted-foreground/70">
              fragment
            </div>
            <code className="block break-all font-mono text-[11px] leading-[1.7]">
              #{konst.digits.slice(0, digits).replace(/(\d{3})/g, '$1 ').trim()}
            </code>
            <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground/70">
              {konst.note}
            </p>
          </div>
        )}

        <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
          <p className="m-0 text-[10px] leading-relaxed text-muted-foreground">
            This preview uses a fixed pivot order, the one the live solver ships. The baked
            version spends its budget on the ink first and runs <b className="text-foreground">11
            to 15 points</b> better on stroke fidelity — so the real thing looks better than this,
            not worse.
          </p>
        </div>

        <Button size="sm" variant="outline" className="w-full gap-1.5 text-[11px]"
                onClick={() => {
                  navigator.clipboard.writeText(cmd).then(
                    () => { setCopied(true); setTimeout(() => setCopied(false), 1600) },
                    () => {})
                }}>
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
          {copied ? 'copied' : 'copy the bake command'}
        </Button>
      </aside>

      <main className="min-w-0">
        <div className="mx-auto max-w-[620px]">
          <canvas ref={canvas} className="h-auto w-full rounded-lg"
                  style={{ background: sty.bg as string, imageRendering: 'auto' }} />
          <div className="mt-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-2">
            {target && <Badge variant="outline" className="text-[10px]">{target.family_label}</Badge>}
            {target && (
              <span className="font-mono text-[11px] text-muted-foreground">
                {target.subject_label} · {target.pose}
                {target.variant === 'repositioned' && ' · repositioned'}
              </span>
            )}
            {konst && digits > 0 && (
              <span className="font-mono text-[11px] text-primary">
                {konst.glyph} to {digits} digits
              </span>
            )}
          </div>
          <p className="mt-3 text-center font-mono text-[10px] text-muted-foreground/60">
            re-derived in the browser · {meta.modules}×{meta.modules} modules · scan it
          </p>
        </div>
      </main>
    </div>
  )
}
