import { useEffect, useMemo, useState } from 'react'
import { SlidersHorizontal } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Drawer, DrawerClose, DrawerContent, DrawerDescription,
  DrawerFooter, DrawerHeader, DrawerTitle, DrawerTrigger,
} from '@/components/ui/drawer'
import {
  Select, SelectContent, SelectGroup, SelectItem,
  SelectLabel, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { CodeCard } from '@/components/CodeCard'
import { across, type Item, type Manifest } from '@/lib/manifest'
import { MEDIA, perSheet, verdict, type Medium } from '@/lib/media'

const SECTIONS = [
  ['shapes', 'The shapes',
   'One still per subject and pose. Only edges that quantise to 0, 45 or 90 degrees survive sampling on a square grid, so these orientations are chosen, not arbitrary.'],
  ['styles', 'The styles',
   'One solved matrix — the 16-cell turned 45° — through every dot and eye treatment. Styling never changes what the code says, only whether a camera can read it, and the measured floors below show it doing exactly that.'],
  ['palettes', 'Colour and plate',
   'The same trick in the page’s own palette. Contrast in the luminance channel is what a reader binarises on, which is why red keeps half the glare headroom of ink.'],
] as const

export default function App() {
  const [man, setMan] = useState<Manifest | null>(null)
  const [mediumId, setMediumId] = useState(MEDIA[0].id)
  const [safety, setSafety] = useState(3)
  const [floorMm, setFloorMm] = useState(0.6)
  const [zoom, setZoom] = useState<Item | null>(null)

  useEffect(() => {
    fetch('/data/gallery/manifest.json').then(r => r.json()).then(setMan)
  }, [])

  // the selected medium, with the thresholds the user can overrule
  const medium: Medium = useMemo(() => {
    const base = MEDIA.find(m => m.id === mediumId) ?? MEDIA[0]
    return base.unit === 'px' ? { ...base, safety }
         : base.distanceM ? base : { ...base, floorMm }
  }, [mediumId, safety, floorMm])

  const preview = medium.unit === 'px' ? medium.size : 260
  const sheet = perSheet(medium)

  // the control: a boring QR for the same destination, judged identically
  const control = useMemo<Item | null>(() => {
    const b = man?.baselines.find(x => x.ecc === 'M')
    if (!b) return null
    return {
      id: 'control', file: 'current-plain.svg', title: 'Plain QR (control)',
      note: `ECC ${b.ecc}, version ${b.version} — the boring code for the same URL. Everything else is judged against this.`,
      section: 'shapes', modules: b.modules, bytes: 0, decodes: true, dark: false,
      pose: '—', stroke: 0, version: b.version, dot: 'square',
      min_ppm: b.min_ppm, blur: b.blur, flash: b.flash, matrix: '',
    }
  }, [man])

  const tally = useMemo(() => {
    if (!man) return null
    const all = [...man.items]
    const ok = all.filter(i => verdict(i, medium).status === 'ok').length
    return { ok, total: all.length }
  }, [man, medium])

  if (!man) return <div className="p-10 text-sm text-muted-foreground">loading…</div>

  return (
    <div className="mx-auto max-w-[1500px] px-6 pb-32 pt-10">
      <h1 className="m-0 text-[13px] font-medium uppercase tracking-[0.35em] text-primary">
        QR Dither
      </h1>
      <p className="mt-2 max-w-[74ch] text-[12px] leading-[1.8] text-muted-foreground">
        Four-dimensional solids drawn <b className="font-medium text-foreground">in the data</b> of
        a QR code, not overlaid on one. Every file here was rasterised and decoded before it was
        written, so the question is never whether it is a valid code — it is whether the thing you
        print it on leaves a camera enough to work with. Pick a destination and every code gets a
        verdict against it.
      </p>

      {/* ---- the bar that replaced the old tiles page ---- */}
      <div className="mt-7 flex flex-wrap items-center gap-4 border-y border-border py-3">
        <Select value={mediumId} onValueChange={setMediumId}>
          <SelectTrigger className="w-[260px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {['Screen', 'Print', 'Projected'].map(g => (
              <SelectGroup key={g}>
                <SelectLabel>{g}</SelectLabel>
                {MEDIA.filter(m => m.group === g).map(m => (
                  <SelectItem key={m.id} value={m.id}>{m.label}</SelectItem>
                ))}
              </SelectGroup>
            ))}
          </SelectContent>
        </Select>

        <Badge variant={medium.measured ? 'outline' : 'secondary'} className="text-[10px]">
          {medium.measured ? 'floor measured × safety' : 'floor is a rule of thumb'}
        </Badge>

        {tally && (
          <span className="font-mono text-[11px] text-muted-foreground">
            {tally.ok}/{tally.total} read here
          </span>
        )}
        {sheet && (
          <span className="font-mono text-[11px] text-muted-foreground">
            {sheet.cols}×{sheet.rows} = <b className="text-foreground">{sheet.total}</b> per Letter sheet
          </span>
        )}

        <span className="flex-1" />

        <Drawer>
          <DrawerTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2 text-[11px]">
              <SlidersHorizontal className="size-3.5" /> Thresholds
            </Button>
          </DrawerTrigger>
          <DrawerContent>
            <div className="mx-auto w-full max-w-md">
              <DrawerHeader>
                <DrawerTitle className="text-sm">Thresholds</DrawerTitle>
                <DrawerDescription className="text-[11px] leading-relaxed">
                  These are judgements, not measurements, so they are yours to move.
                  gen/robust.py measured each code’s floor against a patient decoder on a clean
                  image; a phone in a dim room is neither.
                </DrawerDescription>
              </DrawerHeader>
              <div className="space-y-7 px-4 pb-2">
                <div>
                  <div className="mb-2 flex justify-between font-mono text-[11px]">
                    <span className="text-muted-foreground">screen safety factor</span>
                    <span>×{safety.toFixed(1)}</span>
                  </div>
                  <Slider value={[safety]} min={1} max={6} step={0.5}
                          onValueChange={v => setSafety(v[0])} />
                  <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                    Multiplies the measured min px/module. ×1 trusts the lab number outright.
                  </p>
                </div>
                <div>
                  <div className="mb-2 flex justify-between font-mono text-[11px]">
                    <span className="text-muted-foreground">print floor</span>
                    <span>{floorMm.toFixed(2)} mm/module</span>
                  </div>
                  <Slider value={[floorMm]} min={0.3} max={1.5} step={0.05}
                          onValueChange={v => setFloorMm(v[0])} />
                  <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                    0.6 mm is the usual comfortable minimum for phone scanning. Etching wants more
                    — how much more is a question for a test plate, not for this slider.
                  </p>
                </div>
              </div>
              <DrawerFooter>
                <DrawerClose asChild><Button variant="outline" size="sm">Done</Button></DrawerClose>
              </DrawerFooter>
            </div>
          </DrawerContent>
        </Drawer>
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">{medium.blurb}</p>

      {/* ---- the control, pinned ---- */}
      {control && (
        <section className="mt-9">
          <h2 className="m-0 text-[11px] font-medium uppercase tracking-[0.24em]">The control</h2>
          <p className="mb-5 mt-1 max-w-[68ch] text-[11.5px] leading-relaxed text-muted-foreground">
            Judged by the same rule as everything below. If this fails too, the medium is the
            problem and no amount of art will fix it.
          </p>
          <CodeCard item={control} medium={medium} preview={preview} onZoom={setZoom} />
        </section>
      )}

      {SECTIONS.map(([key, title, note]) => {
        const mine = man.items.filter(i => i.section === key)
        if (!mine.length) return null
        return (
          <section key={key} className="mt-12">
            <h2 className="m-0 text-[11px] font-medium uppercase tracking-[0.24em]">{title}</h2>
            <p className="mb-6 mt-1 max-w-[68ch] text-[11.5px] leading-relaxed text-muted-foreground">
              {note}
            </p>
            <div className="flex flex-wrap gap-x-6 gap-y-9">
              {mine.map(i => (
                <CodeCard key={i.id} item={i} medium={medium} preview={preview} onZoom={setZoom} />
              ))}
            </div>
          </section>
        )
      })}

      {/* ---- scan it for real ---- */}
      <Drawer open={!!zoom} onOpenChange={o => !o && setZoom(null)}>
        <DrawerContent>
          {zoom && (
            <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-4 px-4 pb-8 pt-2">
              <DrawerHeader className="pb-0 text-center">
                <DrawerTitle className="text-sm">{zoom.title}</DrawerTitle>
                <DrawerDescription className="font-mono text-[11px]">
                  {zoom.modules}×{zoom.modules} · {across(zoom.modules)} across · ECC L
                </DrawerDescription>
              </DrawerHeader>
              <img src={`/data/${zoom.file}`} alt={zoom.title}
                   className={`size-[min(70vw,46vh)] rounded-xl ${zoom.dark ? 'bg-black' : 'bg-white'}`} />
              <p className="text-center text-[11px] text-muted-foreground">
                Scan it. That is the only test that counts.
              </p>
            </div>
          )}
        </DrawerContent>
      </Drawer>
    </div>
  )
}
