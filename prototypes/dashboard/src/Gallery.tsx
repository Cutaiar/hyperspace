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
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Combobox, ComboboxInput } from "@/components/ui/combobox"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel,
  ContextMenuSeparator, ContextMenuShortcut, ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { Card } from "@/components/ui/card"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
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
  size?: number | string
  weight?: number
  fracs?: number[]
  on?: boolean
  content?: number
  frac?: number
  disabled?: boolean
  members?: number[]
  orientation?: string
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
          ) : c.kind === "menu" ? (
            // The panel is portalled, so the TRIGGER is pinned instead and
            // Radix places the content below it at sideOffset 4 - the same
            // way the tooltip cell works. The cell rect IS the panel.
            <DropdownMenu defaultOpen modal={false}>
              <DropdownMenuTrigger
                style={{
                  position: "absolute", left: 0, top: -4,
                  width: c.w, height: 0, padding: 0, border: 0,
                }}
              />
              <DropdownMenuContent
                align="start"
                sideOffset={4}
                // The ContextMenu cell is opened with a real right-click, and
                // this panel is a DismissableLayer with modal={false}: an
                // outside pointerdown closed it, so the menu cell rendered
                // nothing and the diff reported 34 levels over 1364 px with
                // NaN corners. The gallery is a static contact sheet - no
                // cell here should ever be dismissed by another cell's setup.
                onInteractOutside={(e) => e.preventDefault()}
                onEscapeKeyDown={(e) => e.preventDefault()}
                // every descendant, not just the content: the destructive
                // item and the shortcut carry colours of their OWN
                // (`text-destructive`, `text-muted-foreground`) and ignore
                // an inherited transparent, so they painted 255-level text
                // against an ImGui side drawing none.
                className="[&_*]:text-transparent!"
                style={{ width: c.w, animation: "none", opacity: 1,
                         color: "transparent" }}
              >
                <DropdownMenuLabel>Node</DropdownMenuLabel>
                <DropdownMenuItem>
                  Open<DropdownMenuShortcut>K</DropdownMenuShortcut>
                </DropdownMenuItem>
                <DropdownMenuItem>Duplicate</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive">Delete</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : c.kind === "button" ? (
            // Pinned to the spec rect by inline style, which beats the
            // size variant's own h-8/size-8 classes without touching any
            // other chrome. Text transparent: the chrome pass never
            // measures glyphs, and a Button's intrinsic WIDTH comes from
            // its label, which is the one thing the spec exists to pin.
            <Button
              variant={c.variant as never}
              size={c.size as never}
              disabled={c.disabled}
              style={{ width: "100%", height: "100%", color: "transparent" }}
            >
              {c.text}
            </Button>
          ) : c.kind === "buttongroup" ? (
            // The member widths are pinned too, for the same reason: the
            // browser's 48.6875 / 47.8125 / 57.5625 are text metrics. What
            // is being diffed is the JOINS - which corners stay round and
            // which shared border is dropped.
            <ButtonGroup
              orientation={c.orientation as "horizontal" | "vertical"}
              style={{ width: "100%", height: "100%" }}
            >
              {(c.members ?? []).map((m, i) => (
                <Button
                  key={i}
                  variant={c.variant as never}
                  style={
                    c.orientation === "vertical"
                      ? { width: "100%", height: m, color: "transparent" }
                      : { width: m, height: "100%", color: "transparent" }
                  }
                >
                  {""}
                </Button>
              ))}
            </ButtonGroup>
          ) : c.kind === "combobox" ? (
            // The CLOSED trigger. No `open`: the panel's chrome is already
            // measured by the menu cells (the kit draws it with literally
            // menu.panel_chrome), and an open Base UI popover on this route
            // would put its portal over the ContextMenu anchor that
            // capture_react.js right-clicks.
            //
            // The trigger IS the input - Base UI's ComboboxInput is an
            // InputGroup wrapping a real <input>, not a Button that opens a
            // panel with a search box in it. That was the old
            // Popover+Command recipe and it is the wrong component.
            <Combobox items={["Alpha", "Beta", "Gamma"]}
                      disabled={c.variant === "disabled"}>
              <ComboboxInput
                placeholder=""
                className="h-full w-full"
                style={{ color: "transparent" }}
              />
            </Combobox>
          ) : c.kind === "contextmenu" ? (
            // Radix's ContextMenu has no `open` or `defaultOpen` - it is
            // driven by a real contextmenu gesture and nothing else - so the
            // trigger is a 0x0 point at the cell's top-left and
            // capture_react.js right-clicks it. The panel then lands wherever
            // RADIX puts it relative to that pointer, and the spec cell's
            // rect is set to the measured result rather than to an offset
            // copied out of the Python.
            <ContextMenu modal={false}>
              {/* Pinned by Radix's own measured offset, the same way the
                  tooltip cell pins its trigger by the arrow allowance. A
                  ContextMenu's panel goes at the POINTER + (2, 0): measured
                  on ?probe, where a contextmenu event at client (0, 0) put
                  the content at (2, 0). So the trigger's top-left - which is
                  where capture_react.js right-clicks - sits 2px LEFT of the
                  cell, and the panel lands exactly on the cell rect.

                  20x20 rather than 0x0 because a real right-click needs a
                  hit area; only its top-left corner is ever clicked. */}
              <ContextMenuTrigger
                data-ctx-anchor
                style={{
                  position: "absolute", left: -2, top: 0,
                  width: 20, height: 20, padding: 0, border: 0,
                }}
              />
              <ContextMenuContent
                // same reasoning as the menu cell: the destructive item and
                // the shortcut carry colours of their own and ignore an
                // inherited transparent
                className="[&_*]:text-transparent!"
                style={{ width: c.w, animation: "none", opacity: 1,
                         color: "transparent" }}
              >
                <ContextMenuLabel>Node</ContextMenuLabel>
                <ContextMenuItem>
                  Open<ContextMenuShortcut>K</ContextMenuShortcut>
                </ContextMenuItem>
                <ContextMenuItem>Duplicate</ContextMenuItem>
                <ContextMenuSeparator />
                <ContextMenuItem variant="destructive">Delete</ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
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
