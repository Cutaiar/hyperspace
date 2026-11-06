import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Download } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Slider } from '@/components/ui/slider'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { download, sheetPdf, sheetSvg, type Code } from '@/lib/export'
import type { Item, Manifest } from '@/lib/manifest'
import {
  DEFAULTS, PAPERS, assign, layout, minSticker, pitch,
  type CutMode, type Pick,
} from '@/lib/sheet'

const MM = (v: number) => `${v.toFixed(1)} mm`

export function Builder() {
  const [man, setMan] = useState<Manifest | null>(null)
  const [paperId, setPaperId] = useState('letter')
  const [mode, setMode] = useState<CutMode>('print-then-cut')
  const [sticker, setSticker] = useState(44)
  const [gutter, setGutter] = useState(DEFAULTS.gutter)
  const [bleed, setBleed] = useState(DEFAULTS.bleed)
  const [floorMm, setFloorMm] = useState(0.6)
  const [chosen, setChosen] = useState<string[]>([])
  const [cutline, setCutline] = useState(true)

  useEffect(() => {
    fetch('/data/gallery/manifest.json').then(r => r.json()).then((m: Manifest) => {
      setMan(m)
      setChosen([m.items[0].id])
    })
  }, [])

  const lay = useMemo(() => layout({
    paper: PAPERS[paperId], mode, sticker, gutter, bleed, edge: DEFAULTS.edge,
  }), [paperId, mode, sticker, gutter, bleed])

  const items = useMemo(
    () => (man?.items ?? []).filter(i => chosen.includes(i.id)), [man, chosen])

  const placed = useMemo(() => {
    const picks: Pick[] = items.map(i => ({ id: i.id, modules: i.modules }))
    return assign(lay, picks)
  }, [lay, items])

  const byId = useMemo(
    () => Object.fromEntries((man?.items ?? []).map(i => [i.id, i])) as Record<string, Item>,
    [man])

  // the worst case among the chosen codes decides whether this sheet is sane
  const worst = useMemo(() => {
    if (!items.length) return null
    return items.reduce((a, b) => (a.modules >= b.modules ? a : b))
  }, [items])
  const p = worst ? pitch(worst.modules, sticker) : 0
  const need = worst ? minSticker(worst.modules, floorMm) : 0
  const under = worst ? p < floorMm : false

  // the exporters re-render from the module grid, so they need the codes, not the files
  const codes = useMemo(() => Object.fromEntries(items.map(i =>
    [i.id, { id: i.id, modules: i.modules, matrix: i.matrix, dark: i.dark } as Code])), [items])
  const bundle = { layout: lay, placed, codes, cutline }
  const stem = `qr-dither-${paperId}-${sticker}mm-${placed.length}up`

  if (!man) return <div className="py-10 text-sm text-muted-foreground">loading…</div>
  const paper = PAPERS[paperId]

  return (
    <div className="grid gap-x-12 gap-y-8 pb-24 lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
        <p className="m-0 text-[11.5px] leading-[1.75] text-muted-foreground">
          Lay the codes out on a sheet. Geometry comes from <code>lib/sheet.ts</code>, the same
          model the exporter will use, so what is drawn here is what gets cut.
        </p>

        <div className="space-y-3">
          <Select value={paperId} onValueChange={setPaperId}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              {Object.values(PAPERS).map(x => (
                <SelectItem key={x.id} value={x.id}>
                  {x.label} · {x.w}×{x.h} mm
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <ToggleGroup type="single" value={mode} variant="outline" size="sm" className="w-full"
                       onValueChange={v => v && setMode(v as CutMode)}>
            <ToggleGroupItem value="print-then-cut" className="flex-1 text-[10.5px]">
              print-then-cut
            </ToggleGroupItem>
            <ToggleGroupItem value="vendor" className="flex-1 text-[10.5px]">
              vendor kiss-cut
            </ToggleGroupItem>
          </ToggleGroup>

          <Knob label="sticker" value={MM(sticker)}>
            <Slider value={[sticker]} min={10} max={90} step={1}
                    onValueChange={v => setSticker(v[0])} />
          </Knob>
          <Knob label="gutter" value={MM(gutter)}>
            <Slider value={[gutter]} min={0} max={15} step={0.25}
                    onValueChange={v => setGutter(v[0])} />
          </Knob>
          <Knob label="bleed" value={MM(bleed)}>
            <Slider value={[bleed]} min={0} max={6} step={0.25}
                    onValueChange={v => setBleed(v[0])} />
          </Knob>
          <Knob label="floor" value={`${floorMm.toFixed(2)} mm/mod`}>
            <Slider value={[floorMm]} min={0.3} max={1.5} step={0.05}
                    onValueChange={v => setFloorMm(v[0])} />
          </Knob>
        </div>

        <Separator />

        <div className="space-y-2 font-mono text-[11px]">
          <div className="text-muted-foreground">
            {lay.cols}×{lay.rows} = <b className="text-foreground text-[13px]">{lay.cells.length}</b> per sheet
          </div>
          <div className="text-muted-foreground/70">
            usable {MM(lay.usable.w)} × {MM(lay.usable.h)} · {(lay.coverage * 100).toFixed(0)}% covered
          </div>
          {worst && (
            <div className={under ? 'text-primary' : 'text-muted-foreground/70'}>
              {p.toFixed(3)} mm/module at {worst.modules}×{worst.modules}
              {under && <> — wants {MM(need)}</>}
            </div>
          )}
        </div>

        {(under || lay.warnings.length > 0) && (
          <div className="space-y-2 rounded-md border border-primary/30 bg-primary/5 p-3">
            {under && (
              <Warn>
                At {MM(sticker)} the densest chosen code runs {p.toFixed(3)} mm per module, under
                your {floorMm.toFixed(2)} floor. It needs {MM(need)}, which is{' '}
                {layout({ paper, mode, sticker: need, gutter, bleed, edge: DEFAULTS.edge })
                  .cells.length} per sheet instead of {lay.cells.length}.
              </Warn>
            )}
            {lay.warnings.map(w => <Warn key={w}>{w}</Warn>)}
          </div>
        )}

        <Separator />

        <div className="space-y-2">
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="flex-1 gap-1.5 text-[11px]"
                    disabled={!placed.length}
                    onClick={() => download(`${stem}.svg`, sheetSvg(bundle), 'image/svg+xml')}>
              <Download className="size-3" /> SVG
            </Button>
            <Button size="sm" variant="outline" className="flex-1 gap-1.5 text-[11px]"
                    disabled={!placed.length}
                    onClick={() => download(`${stem}.pdf`, sheetPdf(bundle), 'application/pdf')}>
              <Download className="size-3" /> PDF
            </Button>
          </div>
          <label className="flex cursor-pointer items-center gap-2 font-mono text-[10px] text-muted-foreground">
            <input type="checkbox" checked={cutline} onChange={e => setCutline(e.target.checked)}
                   className="accent-primary" />
            include the cut layer
          </label>
          <p className="text-[10px] leading-relaxed text-muted-foreground/70">
            Codes are re-rendered from the module grid at the exact size, never by scaling the
            published SVG. The SVG carries the cuts in a <code>#cutline</code> group; the PDF
            draws them as magenta strokes — it has no spot plate or true layers, so a vendor who
            needs those wants the SVG.
          </p>
        </div>

        <Separator />

        <div>
          <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-primary">
            codes ({chosen.length})
          </div>
          <div className="grid max-h-[320px] grid-cols-5 gap-1.5 overflow-y-auto pr-1">
            {man.items.map(i => {
              const on = chosen.includes(i.id)
              return (
                <button key={i.id} title={`${i.title} · ${i.modules}×${i.modules}`}
                  onClick={() => setChosen(c =>
                    c.includes(i.id) ? (c.length > 1 ? c.filter(x => x !== i.id) : c)
                                     : [...c, i.id])}
                  className={`aspect-square overflow-hidden rounded transition-opacity ${
                    on ? 'opacity-100 ring-2 ring-primary' : 'opacity-35 hover:opacity-70'} ${
                    i.dark ? 'bg-black' : 'bg-white'}`}>
                  <img src={`/data/${i.file}`} alt={i.title} className="size-full" />
                </button>
              )
            })}
          </div>
        </div>
      </aside>

      {/* the sheet, drawn in millimetres */}
      <main className="min-w-0">
        <div className="mx-auto max-w-[760px]">
          <svg viewBox={`0 0 ${paper.w} ${paper.h}`}
               className="h-auto w-full rounded-lg shadow-[0_0_0_1px_rgba(255,255,255,0.12)]"
               style={{ background: '#fff' }}>
            {/* the area cut lines may occupy */}
            <rect x={lay.usable.x} y={lay.usable.y} width={lay.usable.w} height={lay.usable.h}
                  fill="none" stroke="#c8c8c8" strokeWidth={0.3} strokeDasharray="2 2" />
            {placed.map((c, i) => {
              const it = byId[c.id]
              return (
                <g key={i}>
                  {bleed > 0 && mode === 'vendor' && (
                    <rect x={c.art.x} y={c.art.y} width={c.art.w} height={c.art.h}
                          fill="#ff2b2b" opacity={0.07} />
                  )}
                  <image href={`/data/${it.file}`} x={c.cut.x} y={c.cut.y}
                         width={c.cut.w} height={c.cut.h} preserveAspectRatio="none" />
                  <rect x={c.cut.x} y={c.cut.y} width={c.cut.w} height={c.cut.h}
                        fill="none" stroke="#ff2b2b" strokeWidth={0.25} opacity={0.75} />
                </g>
              )
            })}
            {mode === 'print-then-cut' && (
              // Cricut reads four corner marks; this is where they live, not art
              <g fill="#111">
                {[[lay.usable.x - 6, lay.usable.y - 6], [lay.usable.x + lay.usable.w + 2, lay.usable.y - 6],
                  [lay.usable.x - 6, lay.usable.y + lay.usable.h + 2]].map(([x, y], i) => (
                  <rect key={i} x={x} y={y} width={4} height={4} />
                ))}
              </g>
            )}
          </svg>
          <p className="mt-3 text-center font-mono text-[10px] text-muted-foreground/60">
            {paper.label} · {paper.w}×{paper.h} mm · drawn to scale ·{' '}
            {mode === 'print-then-cut'
              ? 'corner marks indicative, Cricut places its own'
              : 'red is the cutline, pink is bleed'}
          </p>
        </div>
      </main>
    </div>
  )
}

function Knob({ label, value, children }: {
  label: string; value: string; children: React.ReactNode
}) {
  return (
    <div className="grid grid-cols-[48px_1fr_84px] items-center gap-2">
      <span className="font-mono text-[10px] text-muted-foreground">{label}</span>
      {children}
      <span className="text-right font-mono text-[10px] tabular-nums text-muted-foreground">{value}</span>
    </div>
  )
}
function Warn({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex gap-2 text-[10.5px] leading-relaxed text-muted-foreground">
      <AlertTriangle className="mt-px size-3 shrink-0 text-primary" />
      <span>{children}</span>
    </p>
  )
}
