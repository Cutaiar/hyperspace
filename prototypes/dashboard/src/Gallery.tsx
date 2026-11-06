// The React side of the dkit diff harness.
//
// It renders the REAL shadcn components, but pinned to the rects in
// tools/dkit/spec.json so the ImGui side can draw the same boxes. That
// isolates chrome fidelity from text metrics: the two rasterizers will never
// agree on glyphs, so the box must not depend on them.
//
// ?gallery         the chrome pass (text hidden) — this is what gets diffed
// ?gallery&text    the same grid with text, advisory only
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { SelectTrigger, SelectValue, Select } from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import spec from "../../../hyperspace-python/tools/dkit/spec.json"

// The dashboard decorates its stat cards on top of the base Card; that
// combination (gradient + shadow-xs + ring) is the hard case for ImGui, so
// the gallery carries both.
const CARD_DECOR =
  "bg-gradient-to-t from-primary/5 to-card shadow-xs dark:bg-card"

type Cell = {
  id: string
  kind: string
  variant: string
  x: number
  y: number
  w: number
  h: number
  text: string
  size?: number
  weight?: number
  fracs?: number[]
  on?: boolean
  content?: number
  frac?: number
}

export default function Gallery({
  withText,
  dark,
}: {
  withText: boolean
  dark: boolean
}) {
  const cells = spec.cells as Cell[]
  // Hyperspace is a black-ground app, so dark is the theme that matters; it
  // should be nothing but a token swap on both sides.
  if (dark) document.documentElement.classList.add("dark")
  else document.documentElement.classList.remove("dark")
  return (
    <div
      id="dkit-canvas"
      style={{
        position: "relative",
        width: spec.canvas.w,
        height: spec.canvas.h,
        background: dark ? "#0a0a0a" : spec.canvas.bg,
        overflow: "hidden",
      }}
    >
      {cells.map((c) => (
        <div
          key={c.id}
          style={{
            position: "absolute",
            left: c.x,
            top: c.y,
            width: c.w,
            height: c.h,
            // Badge is an inline span: in a block wrapper it sits on the text
            // baseline, so a cell shorter than the line box pushes it down a
            // pixel. flex + lineHeight 0 makes it fill the rect exactly.
            display: "flex",
            lineHeight: 0,
          }}
        >
          {c.kind === "text" ? (
            // Text cells always draw: they are the advisory pass, measured by
            // ink extent rather than by pixel diff. line-height = cell height
            // pins the baseline deterministically.
            <span
              style={{
                fontFamily: '"Geist Variable", sans-serif',
                fontSize: c.size,
                fontWeight: c.weight,
                lineHeight: `${c.h}px`,
                color: dark ? "#fafafa" : "#0a0a0a",
                whiteSpace: "pre",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {c.text}
            </span>
          ) : c.kind === "slider" ? (
            // Pinned by width only: the root takes the cell's height and
            // `items-center` does the vertical placement, which is the law
            // box.slider_geom reproduces. The values are fractions in the
            // spec, so the component's own 0..100 domain is used.
            <Slider
              className="h-full w-full"
              value={(c.fracs ?? [0]).map((f) => f * 100)}
              min={0}
              max={100}
              // Radix's default step is 1, which SNAPS the value: a spec
              // fraction of 0.375 came back drawn at 0.38 and showed up as
              // the worst corner figure in the set. The spec pins a
              // fraction, so the oracle must honour it exactly - step is a
              // behaviour knob, not chrome.
              step={0.0001}
            />
          ) : c.kind === "switch" ? (
            // NOT stretched: a Switch has an intrinsic size (32 x 18.390625
            // for default), and reproducing that size is half of what is
            // being checked. The spec rect is that intrinsic size.
            <Switch checked={c.on} size={c.variant as "sm" | "default"} />
          ) : c.kind === "input" ? (
            <Input
              className="h-full w-full"
              aria-invalid={c.variant === "invalid" || undefined}
              disabled={c.variant === "disabled"}
              style={{ color: "transparent" }}
            />
          ) : c.kind === "select" ? (
            <Select>
              <SelectTrigger
                size={c.variant as "sm" | "default"}
                className="h-full w-full"
                style={{ color: "transparent" }}
              >
                <SelectValue placeholder="" />
              </SelectTrigger>
            </Select>
          ) : c.kind === "tooltip" ? (
            // TooltipContent is PORTALLED to the body, so inline left/top on
            // it resolve against the viewport and pinning it that way does
            // nothing. Instead the TRIGGER is pinned - a zero-size point at
            // the bottom centre of the cell - and Radix is left to place the
            // panel itself, at sideOffset 0 and centred on that point. With
            // the panel sized to the cell, it lands exactly on the cell
            // rect, and the arrow comes with it in the right place.
            <TooltipProvider>
              <Tooltip open>
                <TooltipTrigger
                  style={{
                    position: "absolute",
                    left: "50%",
                    // + the arrow allowance: Radix reserves the arrow's full
                    // declared size (10px) between the panel and the anchor,
                    // so panel bottom = anchor top - 10. Putting the anchor
                    // 10 below the cell lands the panel ON the cell.
                    top: "calc(100% + 10px)",
                    width: 0,
                    height: 0,
                    padding: 0,
                  }}
                />
                <TooltipContent
                  side="top"
                  sideOffset={0}
                  style={{
                    width: c.w,
                    height: c.h,
                    maxWidth: "none",
                    // `animation: none` alone leaves tw-animate-css's
                    // --tw-enter-opacity in place, so the panel renders at
                    // ~0.99 and the arrow's overlap composites 2 levels
                    // darker than the token. Pinning opacity removes the
                    // artifact rather than tolerating it.
                    animation: "none",
                    opacity: 1,
                    color: "transparent",
                  }}
                >
                  .
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : c.kind === "scroll" ? (
            // type="always" so the scrollbar is up without a hover, and the
            // viewport scrolled by a ref so the thumb sits at a known
            // fraction. The kit draws the same box and the same thumb.
            <ScrollArea
              type="always"
              className="h-full w-full rounded-lg border"
              ref={(el: HTMLDivElement | null) => {
                const vp = el?.querySelector<HTMLDivElement>(
                  '[data-slot="scroll-area-viewport"]')
                if (vp) vp.scrollTop = (c.frac ?? 0) * ((c.content ?? 0) - (c.h - 2))
              }}
            >
              <div style={{ height: c.content }} />
            </ScrollArea>
          ) : c.kind === "card" ? (
            <Card
              className={
                "h-full w-full p-0 " +
                (c.variant === "gradient" ? CARD_DECOR : "")
              }
            />
          ) : (
            <Badge
              variant={c.variant as never}
              // Pin to the spec rect: override the component's intrinsic
              // h-5/w-fit sizing without touching its chrome.
              className="h-full w-full"
              style={{ color: withText ? undefined : "transparent" }}
            >
              {withText ? c.text : ""}
            </Badge>
          )}
        </div>
      ))}
    </div>
  )
}
