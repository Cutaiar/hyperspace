// The React side of the shadkit diff harness.
//
// It renders the REAL shadcn components, but pinned to the rects in
// tools/shadkit/spec.json so the ImGui side can draw the same boxes. That
// isolates chrome fidelity from text metrics: the two rasterizers will never
// agree on glyphs, so the box must not depend on them.
//
// ?gallery         the chrome pass (text hidden) — this is what gets diffed
// ?gallery&text    the same grid with text, advisory only
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import spec from "../../../hyperspace-python/tools/shadkit/spec.json"

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
      id="shadkit-canvas"
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
