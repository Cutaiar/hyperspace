import { useEffect, useState } from 'react'
import { Builder } from '@/components/Builder'
import { Gallery } from '@/components/Gallery'
import { LiveSolver } from '@/components/LiveSolver'
import { Sprite } from '@/components/Sprite'

const VIEWS = {
  gallery: { label: 'gallery', el: <Gallery /> },
  live:    { label: 'live solver', el: <LiveSolver /> },
  sprite:  { label: 'sprite', el: <Sprite /> },
  builder: { label: 'stickers', el: <Builder /> },
} as const
type View = keyof typeof VIEWS

export default function App() {
  const [view, setView] = useState<View>(
    () => (location.hash.slice(1) in VIEWS ? location.hash.slice(1) as View : 'gallery'))

  // a hash change is same-document, so nothing re-runs without this
  useEffect(() => {
    const on = () => { const h = location.hash.slice(1); if (h in VIEWS) setView(h as View) }
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])

  const go = (v: View) => { setView(v); location.hash = v }

  return (
    <div className="mx-auto max-w-[1500px] px-6 pt-10">
      <header className="flex flex-wrap items-center gap-5">
        <h1 className="m-0 text-[13px] font-medium uppercase tracking-[0.35em] text-primary">
          QR Dither
        </h1>
        <nav className="flex overflow-hidden rounded-md border border-border">
          {(Object.keys(VIEWS) as View[]).map(k => (
            <button key={k} onClick={() => go(k)}
              className={`px-4 py-1.5 text-[11px] tracking-wide transition-colors ${
                view === k ? 'bg-primary font-semibold text-primary-foreground'
                           : 'text-muted-foreground hover:text-foreground'}`}>
              {VIEWS[k].label}
            </button>
          ))}
        </nav>
      </header>
      <main className="mt-6">{VIEWS[view].el}</main>
    </div>
  )
}
