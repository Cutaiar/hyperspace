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
import spec from "../../../hyperspace-python/tools/shadkit/spec.json"

type Cell = {
  id: string
  kind: string
  variant: string
  x: number
  y: number
  w: number
  h: number
  text: string
}

export default function Gallery({ withText }: { withText: boolean }) {
  const cells = spec.cells as Cell[]
  return (
    <div
      id="shadkit-canvas"
      style={{
        position: "relative",
        width: spec.canvas.w,
        height: spec.canvas.h,
        background: spec.canvas.bg,
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
          <Badge
            variant={c.variant as never}
            // Pin to the spec rect: override the component's intrinsic
            // h-5/w-fit sizing without touching its chrome.
            className="h-full w-full"
            style={{ color: withText ? undefined : "transparent" }}
          >
            {withText ? c.text : ""}
          </Badge>
        </div>
      ))}
    </div>
  )
}
