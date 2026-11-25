import { useEffect, useMemo, useState } from 'react'
import { Ban, ChevronRight } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import {
  Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle,
} from '@/components/ui/drawer'
import {
  Select, SelectContent, SelectGroup, SelectItem,
  SelectLabel, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { CodeCard } from '@/components/CodeCard'
import { across, type Family, type Item, type Manifest, type Subject } from '@/lib/manifest'
import { MEDIA, type Medium } from '@/lib/media'

/** The gallery sorted by what a thing *is* rather than by what it shows.
 *
 *  Which orientations survive module quantisation is a property of a family's
 *  edge set, not of any one solid: hypercubes keep their edges on the axes,
 *  duoprisms inherit their polygons' angles, a simplex has neither. Grouping
 *  that way puts the stills next to the reason there are that many of them.
 *
 *  The taxonomy comes from the manifest, which gen/polytopes.py fills, so this
 *  view cannot show a family the generator does not have — and it shows the
 *  members with no still at all, because a subject that was rendered and
 *  rejected is part of the answer and the reason is the part worth keeping.
 */
export function Families() {
  const [man, setMan] = useState<Manifest | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)
  const [mediumId, setMediumId] = useState(MEDIA[0].id)
  const [zoom, setZoom] = useState<Item | null>(null)

  useEffect(() => {
    fetch('/data/gallery/manifest.json').then(r => r.json()).then((m: Manifest) => {
      setMan(m)
      setOpenId(m.families?.[0]?.id ?? null)
    })
  }, [])

  const medium: Medium = useMemo(
    () => MEDIA.find(m => m.id === mediumId) ?? MEDIA[0], [mediumId])

  // A subject's stills are its *shape* stills. The styles and palettes
  // sections are one solved matrix — c16_tilt — shown through every treatment,
  // so counting them here would say the 16-cell has eleven orientations when
  // it has two. They are counted separately and named, because "this is the
  // matrix the whole styles section is built on" is worth knowing.
  const bySubject = useMemo(() => {
    const out: Record<string, { shapes: Item[]; reused: Item[] }> = {}
    for (const i of man?.items ?? []) {
      if (!i.subject) continue
      const e = (out[i.subject] ??= { shapes: [], reused: [] })
      ;(i.section === 'shapes' ? e.shapes : e.reused).push(i)
    }
    return out
  }, [man])

  if (!man) return <div className="py-10 text-sm text-muted-foreground">loading…</div>
  const families = man.families ?? []
  if (!families.length)
    return (
      <div className="py-10 text-[11.5px] leading-relaxed text-muted-foreground">
        This manifest has no <code>families</code> block. Rebuild it:{' '}
        <code>python3 gen/gallery.py --url {man.url}</code>
      </div>
    )

  const open = families.find(f => f.id === openId) ?? families[0]
  const count = (f: Family) =>
    f.subjects.reduce((n, s) => n + (bySubject[s.id]?.shapes.length ?? 0), 0)

  return (
    <div className="grid gap-x-12 gap-y-8 pb-24 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
        <p className="m-0 text-[11.5px] leading-[1.75] text-muted-foreground">
          The same codes as the gallery, grouped by what the solid <b className="font-medium
          text-foreground">is</b>. What survives a square module grid is a property of a
          family’s edge set, so the family is the unit that explains why one subject has six
          stills and another has none.
        </p>

        <Select value={mediumId} onValueChange={setMediumId}>
          <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
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

        <Separator />

        <nav className="space-y-1">
          {families.map(f => {
            const on = f.id === open.id
            const n = count(f)
            return (
              <div key={f.id}>
                <button onClick={() => setOpenId(f.id)}
                  className={`flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left
                              text-[11.5px] transition-colors ${
                    on ? 'bg-primary/10 text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
                  <ChevronRight className={`size-3 shrink-0 transition-transform ${on ? 'rotate-90' : ''}`} />
                  <span className="flex-1">{f.label}</span>
                  <span className="font-mono text-[10px] text-muted-foreground/60">{n}</span>
                </button>
                {on && (
                  <ul className="m-0 mb-1 list-none space-y-0.5 py-0.5 pl-7 pr-2">
                    {f.subjects.map(s => {
                      const n2 = bySubject[s.id]?.shapes.length ?? 0
                      return (
                        <li key={s.id}
                            className="flex items-baseline gap-2 font-mono text-[10px]">
                          <a href={`#families`} onClick={e => {
                               e.preventDefault()
                               document.getElementById(`subj-${s.id}`)
                                 ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                             }}
                             className={`flex-1 truncate no-underline transition-colors ${
                               n2 ? 'text-muted-foreground hover:text-foreground'
                                  : 'text-muted-foreground/40 hover:text-muted-foreground'}`}>
                            {s.label}
                          </a>
                          <span className={n2 ? 'text-muted-foreground/60' : 'text-muted-foreground/30'}>
                            {n2 || '—'}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            )
          })}
        </nav>

        <Separator />

        <p className="text-[10px] leading-relaxed text-muted-foreground/70">
          A dash means nothing about that solid survived quantisation. The reason is on the
          subject, not in a comment — see <code>REJECTED</code> in{' '}
          <code>gen/polytopes.py</code>.
        </p>
      </aside>

      <main className="min-w-0">
        <header className="mb-8">
          <h2 className="m-0 text-[11px] font-medium uppercase tracking-[0.24em]">{open.label}</h2>
          <p className="mb-0 mt-1 max-w-[80ch] text-[11.5px] leading-relaxed text-muted-foreground">
            {open.note}
          </p>
        </header>

        <div className="space-y-12">
          {open.subjects.map(s => (
            <SubjectBlock key={s.id} subject={s}
                          stills={bySubject[s.id]?.shapes ?? []}
                          reused={bySubject[s.id]?.reused ?? []}
                          medium={medium} onZoom={setZoom} />
          ))}
        </div>
      </main>

      <Drawer open={!!zoom} onOpenChange={o => !o && setZoom(null)}>
        <DrawerContent>
          {zoom && (
            <div className="mx-auto flex w-full max-w-lg flex-col items-center gap-4 px-4 pb-8 pt-2">
              <DrawerHeader className="pb-0 text-center">
                <DrawerTitle className="text-sm">{zoom.title}</DrawerTitle>
                <DrawerDescription className="font-mono text-[11px]">
                  {zoom.pose} · {zoom.modules}×{zoom.modules} · {across(zoom.modules)} across
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

function SubjectBlock({ subject: s, stills, reused, medium, onZoom }: {
  subject: Subject
  /** the shape stills: one per orientation that survived */
  stills: Item[]
  /** style and palette stills built on this subject's matrix */
  reused: Item[]
  medium: Medium
  onZoom: (i: Item) => void
}) {
  const preview = medium.unit === 'px' ? medium.size : 230
  const cell = Math.max(preview, 215)
  return (
    <section id={`subj-${s.id}`} className="scroll-mt-6">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="m-0 text-[13px] font-medium text-foreground">{s.label}</h3>
        <Badge variant="secondary" className="text-[10px]">{s.dim}D</Badge>
        <span className="font-mono text-[10px] text-muted-foreground/60">
          {s.vertices} vertices · {s.edges} edges · {stills.length || 'no'}{' '}
          {stills.length === 1 ? 'orientation' : 'orientations'}
        </span>
      </div>

      {reused.length > 0 && (
        <p className="m-0 mt-1.5 text-[10.5px] leading-relaxed text-muted-foreground/70">
          Also the solved matrix behind {reused.length} of the gallery's
          {reused.length === 1 ? ' style and palette still' : ' style and palette stills'} —
          same code, different treatment, so they say nothing about this solid's shape.
        </p>
      )}

      {stills.length > 0 && (
        <div className="mt-5 grid gap-x-6 gap-y-9"
             style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${cell}px, 1fr))` }}>
          {stills.map(i => (
            <CodeCard key={i.id} item={i} medium={medium}
                      preview={preview} cell={cell} onZoom={onZoom} />
          ))}
        </div>
      )}

      {s.rejected.length > 0 && (
        <ul className="m-0 mt-5 list-none space-y-2 rounded-md border border-border/60 p-3">
          {s.rejected.map(r => (
            <li key={r.pose} className="flex gap-2">
              <Ban className="mt-px size-3 shrink-0 text-muted-foreground/50" />
              <span className="text-[10.5px] leading-relaxed text-muted-foreground">
                <b className="font-medium text-muted-foreground/90">{r.pose}</b> — {r.why}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
