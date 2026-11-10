import { Badge } from '@/components/ui/badge'
import { across, type Item } from '@/lib/manifest'
import { verdict, type Medium } from '@/lib/media'

const STATUS = {
  ok:    { label: 'reads',  cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  tight: { label: 'tight',  cls: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  fail:  { label: 'too small', cls: 'bg-red-500/15 text-red-300 border-red-500/35' },
}

export function CodeCard({ item, medium, preview, cell, onZoom }: {
  item: Item
  medium: Medium
  /** the code's own rendered size — the medium's real pixels on a screen medium */
  preview: number
  /** the grid cell, which may be wider, so a 200px code gets a readable caption */
  cell: number
  onZoom: (i: Item) => void
}) {
  const v = verdict(item, medium)
  const s = STATUS[v.status]
  const dp = v.unit === 'mm' ? 2 : 1

  return (
    <figure className="m-0" style={{ maxWidth: Math.max(preview, cell) }}>
      <button
        onClick={() => onZoom(item)}
        // On a screen medium this renders at the medium's real pixel size, so
        // the card is the honest test rather than a thumbnail of one.
        style={{ width: preview, height: preview }}
        className={`block cursor-zoom-in overflow-hidden rounded-lg leading-none
                    ${item.dark ? 'bg-black ring-1 ring-white/12' : 'bg-white'}`}
      >
        <img src={`/data/${item.file}`} alt={item.title} loading="lazy"
             className="block h-full w-full" />
      </button>

      <figcaption className="mt-3">
        <div className="flex items-start justify-between gap-2">
          <b className="text-[12.5px] font-medium text-foreground">{item.title}</b>
          <Badge variant="outline" className={`shrink-0 text-[10px] ${s.cls}`}>{s.label}</Badge>
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{item.note}</p>
        <div className="mt-2 font-mono text-[10px] text-muted-foreground/70">
          {item.modules}×{item.modules} · {across(item.modules)} across ·{' '}
          <span className={v.status === 'fail' ? 'text-red-400' : 'text-foreground/70'}>
            {v.pitch.toFixed(dp)}{v.unit}/module
          </span>{' '}
          vs {v.floor.toFixed(dp)} floor
        </div>
        <div className="mt-0.5 font-mono text-[10px] text-muted-foreground/50">
          measured: min {item.min_ppm ?? '—'} px/mod · blur {item.blur.toFixed(2)} · flash {item.flash.toFixed(1)}
        </div>
      </figcaption>
    </figure>
  )
}
