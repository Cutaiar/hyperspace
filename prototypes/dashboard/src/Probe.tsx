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
