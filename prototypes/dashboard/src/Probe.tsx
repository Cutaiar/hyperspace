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
  ComboboxList, ComboboxGroup, ComboboxLabel, ComboboxSeparator,
} from "@/components/ui/combobox"
import { ButtonGroup } from "@/components/ui/button-group"
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel,
  ContextMenuSeparator, ContextMenuShortcut, ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  SidebarProvider, Sidebar, SidebarContent, SidebarMenu, SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
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

      {/* ---- Checkbox: both states, enabled and disabled ----
           One size only: the registry ships no size variant. `checkbox.row`
           is the shadcn demo's own composition (flex gap-3 + Label htmlFor),
           which is what a toggle param row would be; `checkbox.hit` is
           uncontrolled so probe_react.js can CLICK it at the edges of the
           `after:-inset-x-3 -inset-y-2` hit area and read whether it toggled. */}
      <P id="checkbox.off" w={80}>
        <Checkbox checked={false} />
      </P>
      <P id="checkbox.on" w={80}>
        <Checkbox checked />
      </P>
      <P id="checkbox.disabled.off" w={80}>
        <Checkbox checked={false} disabled />
      </P>
      <P id="checkbox.disabled.on" w={80}>
        <Checkbox checked disabled />
      </P>
      <P id="checkbox.row">
        <div className="flex items-center gap-3">
          <Checkbox id="probe-cb-row" checked />
          <Label htmlFor="probe-cb-row">Accept terms</Label>
        </div>
      </P>
      <P id="checkbox.row.disabled">
        <div className="flex items-center gap-3">
          <Checkbox id="probe-cb-row-d" checked={false} disabled />
          <Label htmlFor="probe-cb-row-d">Accept terms</Label>
        </div>
      </P>
      <P id="checkbox.hit" w={120}>
        <div style={{ padding: "20px 40px" }}>
          <Checkbox data-probe-cbhit="" defaultChecked={false} />
        </div>
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
      {/* ---- The modal LAYER, which is what layer.py has to be: a scrim,
           a centred panel, and a close affordance. Behind ?probe&open with
           the other modal layers, because an open Dialog puts
           pointer-events:none on the body and `aria-hidden` on everything
           outside it - exactly the thing that makes every hover below it
           unmeasurable. Measuring the scrim's own colour is the point: it is
           the one piece of chrome in the kit with nothing underneath it to
           compare against. ---- */}
      {open ? (
        <>
          <P id="dialog.open" w={420}>
            <Dialog defaultOpen modal>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete preset</DialogTitle>
                  <DialogDescription>
                    This cannot be undone.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline">Cancel</Button>
                  <Button variant="destructive">Delete</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </P>
          <P id="sheet.open" w={420}>
            <Sheet defaultOpen modal>
              <SheetContent side="right">
                <SheetHeader>
                  <SheetTitle>Node</SheetTitle>
                  <SheetDescription>A side panel.</SheetDescription>
                </SheetHeader>
              </SheetContent>
            </Sheet>
          </P>
        </>
      ) : null}

      {/* ---- The four controls interact.py draws with NO focus ring. The
           point of measuring rather than porting Button's: a TabsTrigger
           carries an OUTLINE as well as a ring, and a SidebarMenuButton's
           ring is 2px in `sidebar-ring` with no border change at all. A
           TableRow is here to answer whether it is focusable in the first
           place - a <tr> is not a control. ---- */}
      <P id="tabs.list" w={420}>
        <Tabs defaultValue="a">
          <TabsList>
            <TabsTrigger value="a" data-probe-tab>Overview</TabsTrigger>
            <TabsTrigger value="b">Bands</TabsTrigger>
          </TabsList>
        </Tabs>
      </P>
      <P id="sidebar.menubutton" w={300}>
        <SidebarProvider>
          <Sidebar collapsible="none">
            <SidebarContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton data-probe-sidebtn>Catalog</SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton isActive>Bands</SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarContent>
          </Sidebar>
        </SidebarProvider>
      </P>
      <P id="table.row" w={420}>
        <Table>
          <TableBody>
            <TableRow data-probe-row>
              <TableCell>Tesseract</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </P>

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

      {/* ---- A combobox that is NOT forced open, which is the only way to
           ask what the KEYBOARD does: whether focus opens it, whether an
           arrow opens it, whether Escape closes it, and where Tab goes.
           Every other combobox block on this route carries `open`, so
           `aria-expanded` is true in them whatever you press. ---- */}
      <P id="combobox.kb" w={320}>
        <Combobox items={["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]}>
          <ComboboxInput placeholder="Keyboard" />
          <ComboboxContent>
            <ComboboxEmpty>None.</ComboboxEmpty>
            <ComboboxList>
              {(item: string) => (
                <ComboboxItem key={item} value={item}>{item}</ComboboxItem>
              )}
            </ComboboxList>
          </ComboboxContent>
        </Combobox>
      </P>

      {/* ---- Sixteen items, NOT forced open, with a committed value.
           This is the ERGONOMICS block, and it is the only one that can
           answer: does the keyboard highlight SCROLL the list to follow
           itself past the 252px clamp; does opening the list select the
           field's text; where does the caret land on a click into the
           middle of the value; does a parked mouse over another row steal
           the highlight from the arrows; and does blur / Escape / Tab /
           click-away each revert the query to the committed value.

           Every one of those questions needs the component to be driven,
           so a forced-open block cannot answer any of them. ---- */}
      <P id="combobox.many" w={320}>
        <Combobox
          items={["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta",
                  "Iota","Kappa","Lambda","Mu","Nu","Xi","Omicron","Pi"]}
          defaultValue="Gamma"
        >
          <ComboboxInput placeholder="Sixteen" />
          <ComboboxContent>
            <ComboboxEmpty>None.</ComboboxEmpty>
            <ComboboxList>
              {(item: string) => (
                <ComboboxItem key={item} value={item}>{item}</ComboboxItem>
              )}
            </ComboboxList>
          </ComboboxContent>
        </Combobox>
      </P>

      {/* ---- Disabled, not forced open. The kit derives the disabled state
           from `opacity-50` on the class list and has never measured it. ---- */}
      <P id="combobox.dis" w={320}>
        <Combobox items={["Alpha", "Beta", "Gamma"]} defaultValue="Beta" disabled>
          <ComboboxInput placeholder="Disabled" disabled />
          <ComboboxContent>
            <ComboboxEmpty>None.</ComboboxEmpty>
            <ComboboxList>
              {(item: string) => (
                <ComboboxItem key={item} value={item}>{item}</ComboboxItem>
              )}
            </ComboboxList>
          </ComboboxContent>
        </Combobox>
      </P>

      {/* ---- A group label and a separator, forced open so both are in the
           dump. `combobox.tsx`'s separator is `-mx-1 my-1 h-px bg-border` —
           it DOES carry a margin block, where `command.tsx`'s (the old
           recipe's, which is what the kit's table recorded) does not. ---- */}
      <div data-probe-grp style={{ position: "fixed", left: 1000, top: 40, width: 320, zIndex: 1 }}>
       <div data-probe="combobox.grp" style={{ width: 320 }}>
        <Combobox items={["Alpha", "Beta", "Gamma"]} open>
          <ComboboxInput placeholder="Grouped" />
          <ComboboxContent>
            <ComboboxEmpty>None.</ComboboxEmpty>
            <ComboboxList>
              <ComboboxGroup>
                <ComboboxLabel>Planes</ComboboxLabel>
                <ComboboxItem value="Alpha">Alpha</ComboboxItem>
                <ComboboxSeparator />
                <ComboboxItem value="Beta">Beta</ComboboxItem>
              </ComboboxGroup>
            </ComboboxList>
          </ComboboxContent>
        </Combobox>
       </div>
      </div>

      {/* ---- THE KEYBOARD BLOCKS. ----------------------------------------

           Every menu block that existed before these carried `defaultOpen`,
           and a forced-open component cannot answer a keyboard question:
           `data-state` reads "open" whatever you press, so "did this key
           open it" and "did this key close it" both come back yes. That is
           exactly how the Combobox's first keyboard model came out wrong
           (RETRO row 17), and `combobox.kb` exists for the same reason.

           So: a DropdownMenu with a REAL trigger and a Select with no
           `defaultOpen`, driven with playwright.

           `menu.kb` carries one of everything the arrows have to step over
           or skip: a label (not focusable), a separator, a DISABLED item,
           a destructive item, and six enabled items whose initials are all
           different so typeahead has something unambiguous to jump to. ---- */}
      <P id="menu.kb" w={320}>
        <DropdownMenu>
          <DropdownMenuTrigger data-probe-menu-trigger>Open menu</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel>Node</DropdownMenuLabel>
            <DropdownMenuItem>
              Alpha<DropdownMenuShortcut>⌘O</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem>Beta</DropdownMenuItem>
            <DropdownMenuItem disabled>Gamma</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Delta</DropdownMenuItem>
            <DropdownMenuItem>Epsilon</DropdownMenuItem>
            <DropdownMenuItem variant="destructive">Zeta</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </P>

      {/* ---- Sixteen items, so PageUp / PageDown have somewhere to go and
           the list is taller than its clamp. The Combobox needed exactly
           this block (`combobox.many`) to find that its highlight never
           scrolled the list (RETRO row 30). ---- */}
      <P id="menu.long" w={320}>
        <DropdownMenu>
          <DropdownMenuTrigger data-probe-menu-trigger>Open long</DropdownMenuTrigger>
          <DropdownMenuContent>
            {["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta",
              "Iota","Kappa","Lambda","Mu","Nu","Xi","Omicron","Pi"].map(n => (
              <DropdownMenuItem key={n}>{n}</DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </P>

      {/* ---- A Select with a REAL trigger and a committed value. The one
           question `select.open` cannot be asked: when it opens, is the
           SELECTED item highlighted, or the first? The Combobox's answer
           was the selected one and the kit had it wrong (RETRO row 26), so
           this is the column that has to be probed with the state AND
           without — hence the valueless twin below. ---- */}
      <P id="select.kb">
        <Select defaultValue="c">
          <SelectTrigger data-probe-select-trigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="a">Alpha</SelectItem>
            <SelectItem value="b">Beta</SelectItem>
            <SelectItem value="c">Gamma</SelectItem>
            <SelectItem value="d">Delta</SelectItem>
            <SelectItem value="e">Epsilon</SelectItem>
            <SelectItem value="f">Zeta</SelectItem>
          </SelectContent>
        </Select>
      </P>

      {/* ---- The same Select holding NOTHING. One probe block answers one
           COLUMN of the table. ---- */}
      <P id="select.kbnone">
        <Select>
          <SelectTrigger data-probe-select-trigger>
            <SelectValue placeholder="Select" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="a">Alpha</SelectItem>
            <SelectItem value="b">Beta</SelectItem>
            <SelectItem value="c">Gamma</SelectItem>
            <SelectItem value="d">Delta</SelectItem>
            <SelectItem value="e">Epsilon</SelectItem>
            <SelectItem value="f">Zeta</SelectItem>
          </SelectContent>
        </Select>
      </P>

      {/* ---- Something to Tab ONTO, so "where does focus land" has an
           answer that is not "the body". ---- */}
      <P id="menu.after" w={320}>
        <Button data-probe-after>after</Button>
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
