import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'

type Meta = { modules: number; quiet: number; cols: number; rows: number
              verified: number; total: number }

const SENS = 0.006, FRICTION = 0.94, Q = Math.PI / 2
const deg = (r: number) => (((r * 180) / Math.PI % 360) + 360) % 360

const loadImage = (src: string) => new Promise<HTMLImageElement>((res, rej) => {
  const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src
})

/** The precomputed fallback: 216 frames on one sheet, no solver on the client.
 *  Dragging picks the nearest generated frame, so the motion is quantised to
 *  what was verified rather than interpolated into something that was not. */
export function Sprite() {
  const canvas = useRef<HTMLCanvasElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const read = useRef<HTMLDivElement>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [ghost, setGhost] = useState(false)
  const [kb, setKb] = useState(0)
  const ghostRef = useRef(false)
  ghostRef.current = ghost

  // everything the loop mutates lives here, so React never re-renders per frame
  const st = useRef({ xw: 0, yw: 0, vx: 0, vy: 0, down: false, px: 0, py: 0 })

  useEffect(() => {
    let alive = true, raf = 0
    ;(async () => {
      const m: Meta = await (await fetch('/data/sweep-2ax.json')).json()
      const [sheet, gh] = await Promise.all([
        loadImage('/data/sweep-2ax.png'),
        loadImage('/data/sweep-2ax-ghost.png').catch(() => null as never),
      ])
      if (!alive) return
      setMeta(m)
      fetch('/data/sweep-2ax.png', { method: 'HEAD' })
        .then(r => setKb(+(r.headers.get('content-length') ?? 0) / 1024)).catch(() => {})

      const c = canvas.current!, ctx = c.getContext('2d')!
      const n = m.modules, quiet = m.quiet, side = n + 2 * quiet
      c.width = c.height = side
      ctx.imageSmoothingEnabled = false

      const draw = () => {
        const s = st.current
        const i = (((Math.round((s.xw / Q) * m.cols) % m.cols) + m.cols) % m.cols)
        const j = Math.max(0, Math.min(m.rows - 1,
          Math.round(((((s.yw / Q) % 1) + 1) % 1) * m.rows) % m.rows))
        ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, side, side)
        ctx.drawImage(ghostRef.current && gh ? gh : sheet, i * n, j * n, n, n, quiet, quiet, n, n)
        if (read.current)
          read.current.textContent = `XW ${deg(s.xw).toFixed(1)}°   YW ${deg(s.yw).toFixed(1)}°`
      }

      const frame = () => {
        const s = st.current
        if (!s.down && (Math.abs(s.vx) > 1e-5 || Math.abs(s.vy) > 1e-5)) {
          s.xw += s.vx; s.yw += s.vy; s.vx *= FRICTION; s.vy *= FRICTION; draw()
        }
        raf = requestAnimationFrame(frame)
      }
      draw(); raf = requestAnimationFrame(frame)
      ;(c as HTMLCanvasElement & { _draw?: () => void })._draw = draw
    })()
    return () => { alive = false; cancelAnimationFrame(raf) }
  }, [])

  // redraw on a ghost flip without restarting the loop
  useEffect(() => {
    const c = canvas.current as (HTMLCanvasElement & { _draw?: () => void }) | null
    c?._draw?.()
  }, [ghost])

  const onDown = (e: React.PointerEvent) => {
    const s = st.current
    s.down = true; s.px = e.clientX; s.py = e.clientY; s.vx = s.vy = 0
    stage.current?.setPointerCapture(e.pointerId)
  }
  const onMove = (e: React.PointerEvent) => {
    const s = st.current
    if (!s.down) return
    const dx = (e.clientX - s.px) * SENS, dy = (e.clientY - s.py) * SENS
    s.px = e.clientX; s.py = e.clientY
    s.xw += dx; s.yw += dy; s.vx = dx; s.vy = dy
    ;(canvas.current as HTMLCanvasElement & { _draw?: () => void })?._draw?.()
  }
  const onUp = () => { st.current.down = false }

  return (
    <div className="flex flex-col items-center gap-5 py-8">
      <div ref={stage} onPointerDown={onDown} onPointerMove={onMove}
           onPointerUp={onUp} onPointerCancel={onUp}
           className="cursor-grab touch-none rounded-lg bg-white leading-none active:cursor-grabbing">
        <canvas ref={canvas}
                className="block size-[min(86vw,430px)] rounded-lg [image-rendering:pixelated]" />
      </div>
      <div ref={read} className="font-mono text-[11px] tabular-nums text-muted-foreground" />
      <div className="flex items-center gap-3">
        <Button variant={ghost ? 'default' : 'outline'} size="sm"
                className="text-[11px]" onClick={() => setGhost(g => !g)}>ghost</Button>
        <Button variant="outline" size="sm" className="text-[11px]"
                onClick={() => { st.current = { xw: 0, yw: 0, vx: 0, vy: 0, down: false, px: 0, py: 0 }
                                 ;(canvas.current as HTMLCanvasElement & { _draw?: () => void })?._draw?.() }}>
          reset
        </Button>
      </div>
      <p className="max-w-[56ch] text-center text-[11px] leading-relaxed text-muted-foreground">
        The precomputed fallback — grab and drag it.{' '}
        {meta && <>Every one of <b className="text-foreground">{meta.verified}/{meta.total}</b> frames
        was decoded before you ever touched it{kb ? <>, {kb.toFixed(0)} KB for the whole set</> : null}.</>}
      </p>
    </div>
  )
}
