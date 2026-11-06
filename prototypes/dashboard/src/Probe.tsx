// The measuring route: ?probe
//
// Renders the real shadcn components in the configurations dkit needs to
// match, each in a labelled wrapper. tools/dkit/probe_react.js walks every
// [data-probe] and dumps the rect + computed style of each data-slot inside
// it, so the kit is built from measurements rather than from a reading of the
// Tailwind classes.
//
// Why a separate route from ?gallery: the gallery pins everything to
// spec.json rects for the pixel diff. This one lets the components size
// THEMSELVES, which is the question "how big is a switch, actually" — and
// the answer (h-[18.4px]) is not one I would have guessed.
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Combobox, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox"
import { ButtonGroup } from "@/components/ui/button-group"
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel,
  ContextMenuSeparator, ContextMenuShortcut, ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

function P({ id, w, children }: { id: string; w?: number; children: React.ReactNode }) {
  return (
    <div data-probe={id} style={{ width: w ?? 240, margin: "18px 0" }}>
      {children}
    </div>
  )
}

export default function Probe({ dark, open }: { dark: boolean; open: boolean }) {
  if (dark) document.documentElement.classList.add("dark")
  else document.documentElement.classList.remove("dark")
  return (
    <div
      id="dkit-probe"
      style={{
        padding: 24,
        width: 900,
        background: dark ? "#0a0a0a" : "#ffffff",
        fontFamily: '"Geist Variable", sans-serif',
      }}
    >
      {/* ---- Slider: the value->thumb-centre law is the thing to measure.
           Radix insets the thumb so it never overhangs the track, so the
           centre is NOT simply x + frac*w. Several values and several widths
           pin the law. ---- */}
      {[0, 25, 50, 75, 100].map((v) => (
        <P key={`s${v}`} id={`slider.w240.v${v}`}>
          <Slider value={[v]} min={0} max={100} />
        </P>
      ))}
      {[120, 200, 320].map((w) => (
        <P key={`sw${w}`} id={`slider.w${w}.v50`} w={w}>
          <Slider value={[50]} min={0} max={100} />
        </P>
      ))}
      {/* a non-0..100 domain, to check the law is in fraction space */}
      <P id="slider.domain.v3of8">
        <Slider value={[3]} min={0} max={8} />
      </P>
      {/* two thumbs: the range no longer starts at the left edge */}
      <P id="slider.range.v30-70">
        <Slider value={[30, 70]} min={0} max={100} />
      </P>
      <P id="slider.disabled.v40">
        <Slider value={[40]} min={0} max={100} disabled />
      </P>

      {/* ---- Switch: both sizes, both states ---- */}
      <P id="switch.default.off" w={80}>
        <Switch checked={false} />
      </P>
      <P id="switch.default.on" w={80}>
        <Switch checked />
      </P>
      <P id="switch.sm.off" w={80}>
        <Switch size="sm" checked={false} />
      </P>
      <P id="switch.sm.on" w={80}>
        <Switch size="sm" checked />
      </P>

      {/* ---- Input ---- */}
      <P id="input.empty">
        <Input placeholder="Placeholder" />
      </P>
      <P id="input.value">
        <Input defaultValue="600-cell" />
      </P>
      <P id="input.invalid">
        <Input defaultValue="bad" aria-invalid />
      </P>
      <P id="input.disabled">
        <Input defaultValue="off" disabled />
      </P>

      {/* ---- Select: trigger closed, and the content forced open ---- */}
      <P id="select.closed">
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="Pick one" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="a">Alpha</SelectItem>
          </SelectContent>
        </Select>
      </P>
      <P id="select.sm">
        <Select>
          <SelectTrigger size="sm">
            <SelectValue placeholder="Small" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="a">Alpha</SelectItem>
          </SelectContent>
        </Select>
      </P>
      {/* An open Select is a MODAL layer: Radix puts pointer-events:none on
          the body while it is up, so every hover measurement on the same
          page times out. It gets its own ?probe&open pass. */}
      {open ? (
        <P id="select.open">
          <Select defaultOpen value="b">
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="a">Alpha</SelectItem>
              <SelectItem value="b">Beta</SelectItem>
              <SelectItem value="c">Gamma</SelectItem>
            </SelectContent>
          </Select>
        </P>
      ) : null}

      {/* ---- Card + a stack of labelled fields: the SPACING, which is the
           thing the dashboard has been guessing. Card's own padding and
           header gap, and the rhythm between a label and its control. ---- */}
      <P id="card.header" w={360}>
        <Card>
          <CardHeader>
            <CardTitle>Controls</CardTitle>
            <CardDescription>Slider, Switch, Select, Input</CardDescription>
          </CardHeader>
          <CardContent>
            <div data-probe-field className="grid gap-2">
              <label data-slot="label">Cutoff</label>
              <Input defaultValue="2400" />
            </div>
          </CardContent>
        </Card>
      </P>

      {/* ---- ScrollArea: the thumb's size law is the thing to measure.
           Radix sizes the thumb by viewport/content, with a floor, and the
           scrollbar OVERLAYS rather than taking layout space - both of
           which decide whether a kit version can be drawn from
           scroll_y/scroll_max_y alone. Three content ratios pin the law.
           `type="always"` so it is up without a hover; the default is
           "hover", which is itself worth recording. ---- */}
      {[200, 400, 1200].map((ch) => (
        <P key={`sa${ch}`} id={`scroll.h200.content${ch}`} w={320}>
          <ScrollArea type="always" className="h-[200px] w-full rounded-lg border">
            <div style={{ height: ch }} data-probe-content />
          </ScrollArea>
        </P>
      ))}
      <P id="scroll.hover.default" w={320}>
        <ScrollArea className="h-[120px] w-full rounded-lg border">
          <div style={{ height: 600 }} />
        </ScrollArea>
      </P>

      {/* ---- Button: 6 variants x 8 sizes. The radius is size-dependent
           (`rounded-[min(var(--radius-md),10px)]` on the small ones), the
           hover is per-variant, and there is an `active:translate-y-px`
           press nudge. ---- */}
      {["default", "outline", "secondary", "ghost", "destructive", "link"].map((v) => (
        <P key={`bv${v}`} id={`button.${v}`} w={420}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Button variant={v as never}>Button</Button>
          </div>
        </P>
      ))}
      {["xs", "sm", "default", "lg", "icon-xs", "icon-sm", "icon", "icon-lg"].map((z) => (
        <P key={`bz${z}`} id={`button.size.${z}`} w={420}>
          <Button size={z as never}>{z.startsWith("icon") ? "✕" : "Button"}</Button>
        </P>
      ))}
      <P id="button.disabled" w={420}>
        <Button disabled>Button</Button>
      </P>

      {/* ---- ButtonGroup: the joins are the thing. Inner corners square,
           outer ones rounded, and the shared border is not doubled. ---- */}
      <P id="buttongroup.horizontal" w={420}>
        <ButtonGroup>
          <Button variant="outline">One</Button>
          <Button variant="outline">Two</Button>
          <Button variant="outline">Three</Button>
        </ButtonGroup>
      </P>
      <P id="buttongroup.vertical" w={420}>
        <ButtonGroup orientation="vertical">
          <Button variant="outline">One</Button>
          <Button variant="outline">Two</Button>
        </ButtonGroup>
      </P>

      {/* ---- Combobox = Popover + Command, which is how shadcn builds it:
           there is no `combobox` component. Behind ?probe&open because a
           Popover is a modal layer and swallows every hover. ---- */}
      {open ? (
        <P id="combobox.open" w={420}>
          <Popover defaultOpen>
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-[220px] justify-between">
                Pick a plane
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[220px] p-0">
              <Command>
                <CommandInput placeholder="Search..." />
                <CommandList>
                  <CommandEmpty>Nothing found.</CommandEmpty>
                  <CommandGroup heading="Planes">
                    <CommandItem value="xy">XY</CommandItem>
                    <CommandItem value="xz">XZ</CommandItem>
                    <CommandItem value="xw">XW</CommandItem>
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </P>
      ) : null}

      {/* ---- ContextMenu: no defaultOpen on Radix's, so it is opened with
           a real right-click from playwright. Its content is the same
           chrome DropdownMenu uses, which menu.py already draws. ---- */}
      <P id="contextmenu.target" w={420}>
        <ContextMenu>
          <ContextMenuTrigger asChild>
            <div
              data-probe-ctx
              style={{ height: 60, border: "1px dashed #999", borderRadius: 8 }}
            />
          </ContextMenuTrigger>
          <ContextMenuContent>
            <ContextMenuLabel>Node</ContextMenuLabel>
            <ContextMenuItem>
              Open<ContextMenuShortcut>⌘O</ContextMenuShortcut>
            </ContextMenuItem>
            <ContextMenuItem>Duplicate</ContextMenuItem>
            <ContextMenuSeparator />
            <ContextMenuItem variant="destructive">Delete</ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </P>

      {/* ---- The REAL Combobox: Base UI, and the trigger IS the input.
           Not the old Popover+Command recipe.

           `defaultValue` so an ItemIndicator is actually rendered - the
           check's inset is one of the numbers the kit got wrong, and with
           nothing selected there is no check to measure. ---- */}
      <P id="combobox.real" w={320}>
        <Combobox items={["Dodecahedron", "Great Dodecahedron", "Tesseract", "Grand antiprism"]} open defaultValue="Tesseract">
          <ComboboxInput placeholder="Filter planes" />
          <ComboboxContent>
            <ComboboxEmpty>No such plane.</ComboboxEmpty>
            <ComboboxList>
              {(item: string) => (
                <ComboboxItem key={item} value={item}>{item}</ComboboxItem>
              )}
            </ComboboxList>
          </ComboboxContent>
        </Combobox>
      </P>

      {/* ---- A combobox with more items than fit, pinned near the bottom of
           the viewport. The question this answers is what Base UI does when
           the list does not fit below: FLIP to the other side, or CAP to
           `--available-height` and scroll inside. The kit flips, and the
           panel jumps from above the field to below it the moment filtering
           shrinks it, which is the bug this block exists to settle. ---- */}
      <div data-probe-tight style={{ position: "fixed", left: 600, bottom: 90, width: 320, zIndex: 1 }}>
        <div data-probe="combobox.tight" style={{ width: 320 }}>
          <Combobox
            items={["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta",
                    "Iota","Kappa","Lambda","Mu","Nu","Xi","Omicron","Pi"]}
            open
          >
            <ComboboxInput placeholder="Many" />
            <ComboboxContent>
              <ComboboxEmpty>None.</ComboboxEmpty>
              <ComboboxList>
                {(item: string) => (
                  <ComboboxItem key={item} value={item}>{item}</ComboboxItem>
                )}
              </ComboboxList>
            </ComboboxContent>
          </Combobox>
        </div>
      </div>

      {/* ---- Tooltip, forced open ---- */}
      <P id="tooltip.open">
        <TooltipProvider>
          <Tooltip open>
            <TooltipTrigger>trigger</TooltipTrigger>
            <TooltipContent side="top">Cutoff frequency</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </P>
    </div>
  )
}
