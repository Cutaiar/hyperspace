# dkit

> **This file is accurate as the Tier 1 record.** What was built after
> it — ScrollArea, intrinsic sizing, Button, ButtonGroup, ContextMenu,
> Combobox — plus every trap and process revision, is in
> [`HANDOFF.md`](HANDOFF.md).

Can Dear ImGui, on this project's own stack, be made to look like shadcn/ui?

**Picking this up fresh?** Start with [`ROADMAP.md`](ROADMAP.md) — what to
build next, in what order, why, and the constraints each component has to
respect. [`FINDINGS.md`](FINDINGS.md) has the verdict and the honest list of
what is not built.

This is the measuring rig for that question, plus the primitive kit it measures.
Nothing here is imported by the app — it lives in `tools/` on purpose.

## The bar

**Chrome matches within ~1px; glyph rasterization may differ.** Two text
rasterizers never agree on the ink itself, so the diff runs with text hidden
and the box is the thing. Text METRICS are another matter: since RETRO row
61 the kit's advances, kerning, ligatures and baselines are Chromium's to
within a few hundredths of a pixel, checked in `test_text.py`.

## How it works

`spec.json` is the shared contract: it pins every cell's rect in CSS pixels.
Both sides draw to the *same* rects, so a font-metric difference can never
change a box width and the diff only ever measures chrome.

- **React oracle** — `prototypes/dashboard/src/Gallery.tsx` renders the *real*
  shadcn components, pinned to the spec rects. `?gallery` is the chrome pass,
  `?gallery&text` adds text (advisory only).
- **ImGui side** — `gallery.py` draws the kit through `draw.py` + `tokens.py`,
  into a hidden GLFW window (the pattern from `tools/sheet_shots.py:40-85`).
- **Diff** — `diff.py` reports two things, because one is not enough.

## Two metrics, and why

| region | metric | why |
|---|---|---|
| straight edges, fills, flat areas | per-pixel value delta, must be **0** | catches a systematic sub-pixel or whole-pixel misalignment |
| rounded corners | radial contour displacement in **pixels** (`contour.py`) | the bar is geometric; a value delta is not |
| icon strokes, the tooltip arrow | the feature's own shape — ink **area**, in px² | a round line cap and a 45° edge are not axis-aligned either |

The third row is `vector_mask`, and it earns its place the same way the
second does. The Select's chevron lands on the right pixels and its body
matches to 2 levels, but the outermost pixel of each round line cap differs
by up to 59 — a cap a third of a pixel longer in one renderer. Nothing is
dropped silently: each masked region says what measures it instead.

That split is load-bearing. A 0.3px geometric difference across a
black-on-white corner is a ~115-level value delta, while the identical 0.3px on
a `#e5e5e5` border is ~7. Judging corners photometrically reports a failure
that is really sub-pixel agreement. Judging straight edges with a 1px-tolerant
metric hides a real 1px offset — which is exactly the bug the strict metric
caught during Phase 0.

## Calibration, not assumption

`probe_stroke.py` measures where ImGui actually puts a stroke, because the
intuition is wrong. An `add_rect` stroke of thickness 1 is **not** centred on
the path: the top/left edges cover `[p_min, p_min+1]` and the bottom/right
cover `[p_max-1, p_max]`. So the stroke already falls wholly inside the rect
bounds — which is exactly CSS `border-box`, and the correct inset is **none**.
Filled (unrounded) rect edges snap by pixel centre; rounded fills are
antialiased and land exactly.

## Results — 33 chrome cells, both themes

```
flat: edges+fills   max 0-2 levels, 0 pixels over threshold, all 33 cells
corners             worst displacement 0.776 px   (bar 1.0)
background          0 pixels differ
```

Badge, Card, Slider, Switch, Input, Select and the Tooltip panel. The worst
corner figure is the same 0.776 px the first fourteen cells gave, so Tier 1
is no looser than the chrome that came before it.

Straight edges, borders, radii, fills, gradients, rings, shadows and colours
are **pixel-exact to within a level**. The whole residual is corner-arc
antialiasing at roughly a third of a pixel (mean +0.28px at r=10, -0.15px at
r=26 — ImGui's small-radius arcs sit a touch outside Chromium's). Lowering
`circle_tessellation_max_error` does not help and slightly hurts, so this is
the two rasterizers differing, not geometry to be fixed.

### Text (advisory)

Geist ships only as a variable woff2, which ImGui's loader can read neither
of, so `fonts/` holds six faces cut from that exact file by `build_fonts.py`:
wght 400/500/600, each with and without tabular figures frozen in. Ink
extents against the oracle, both themes, before and after the font loader
was fixed (RETRO row 61):

```
                 before        after
text.num14       -6 px          0
text.small12     +6 / +5       +1 / -1
text.title30     +2             0
text.mixed       +2             0
```

What it took, each measured - read `draw.py`'s "faces and metrics":

* **ImGui's loader is FreeType, not stb_truetype**, in imgui_bundle 1.92.
  It sizes a face by `ascent - descent` (REAL_DIM) where CSS maps the em,
  and Geist's span is 1.30em. The old answer was to push `css x 1.30` - but
  **ImGui 1.92 rounds every font size to a whole pixel**, so 12px became
  15.6 and then 16: text 2.6% large. `build_fonts.py` now writes a
  one-em line box (800 / -200) into the TTFs, so the kit pushes the CSS px
  itself. Geist's real 1005 / -295 live in `fonts/metrics.json`.
* **FreeType hints by default, and a hinted advance is a whole pixel**
  ("K" 8 against 7.872). The faces load with `NoHinting`.
* **No OpenType features at runtime.** `tnum` is frozen into a parallel
  `-tnum` face at build time; `kern` and `liga` are frozen into
  `fonts/metrics.json` (every pair checked against HarfBuzz, 50,586 per
  face, zero mismatches) and applied by `draw.shape`. Ligatures matter to
  width: Geist's `tt` and `ff` are 0.05em narrower than their letters. The
  advances come from `hmtx` too - FreeType's are in 1/64ths of a pixel.
* **Layout is exact; glyph placement is close, for speed.** Widths,
  alignment and baselines come from the frozen metrics. The glyphs are
  drawn by `add_text` in runs that restart at the kerned pen whenever
  ImGui's unkerned one drifts 0.25px (`draw.DRIFT_PX`), so a glyph lands
  within ~0.7px of Chromium's position. One quad per glyph was exact and
  cost ~3ms of a dashboard frame; runs cost ~0.6ms over the pre-fix
  loader. The baseline stays a whole pixel (`draw.baseline_y`, measured on
  252 cells - see its docstring for the two roundings).
* Tabular figures: proportional Geist digits are 384-663 units wide; frozen
  they are all 600. A live readout cycling 1.36 / 0.50 / 2.08 **jitters by
  9px** proportional and is **stable at 23px** tabular.

## Measuring a component before building it

`spec.json` + the `?gallery` route is the pixel diff. `?probe` is the step
*before* that: it renders the real shadcn components at their own intrinsic
sizes and `probe_react.js` dumps every `data-slot`'s rect and chrome styles,
including the hover and focus states that do not exist in a computed style
until the pseudo-class matches.

```bash
node tools/dkit/probe_react.js "http://localhost:4173/?probe" --json /tmp/p.json
node tools/dkit/probe_react.js "http://localhost:4173/?probe&dark"   # theme traps
node tools/dkit/probe_react.js "http://localhost:4173/?probe&open"   # open popovers
```

It is worth the detour because reading the Tailwind classes is how you get
it wrong. Everything below came out of the dump and none of it is guessable:

* **a Slider's range and its thumb use different mappings.** The range runs
  edge to edge (`f·W`); the thumb is inset by its own width (`f·(W−12)`), so
  it can never overhang the track. They agree only at 50% — at 25% on a
  240px track the range ends at 60 while the thumb's centre is at 63, and at
  100% the range reaches 240 while the thumb's centre stops at 234. One
  mapping for both puts the thumb half its own width from the end of its own
  fill, and looks right until you check it anywhere but the middle.
* **a Switch is 18.390625 px tall.** The class says `h-[18.4px]`; Chromium
  lays out on a 1/64 px grid.
* **the Slider thumb's `bg-white` is a literal, not a token.** It stays pure
  white on Hyperspace's `#0a0a0a` ground while every other fill swaps.
* **the Switch thumb inverts in dark** — `foreground` off,
  `primary-foreground` on. In light both states are white.
* **the Select trigger has no hover tint in light at all**, and does have one
  in dark (`input/30` → `input/50`).
* **the Select trigger's radius is not constant across sizes** — default is
  `rounded-lg` (10), `sm` is `rounded-md` (8).
* **Radix reserves the arrow's full declared size** between a tooltip and its
  anchor, so `panel bottom = anchor top − 10`, while the rendered diamond
  only uses 5.071 px of it.

Two of the numbers chased in this round turned out to be the *harness*, and
both were fixed rather than tolerated: Radix's default `step` is 1, which
silently snapped a spec fraction of 0.375 to 0.38; and the arc metric walked
cell corners, which is nowhere near where a slider thumb's arcs actually are.

## Pixel snapping — the browser paints on whole pixels

The one finding that reaches past the gallery. **Chromium lays out on
fractions but snaps what it PAINTS to whole device pixels.** ImGui
antialiases instead, which is the more faithful rendering of the stated
geometry and the wrong answer if the bar is "match the browser".

Measured on the two shapes that have fractional edges:

* the Switch's box runs `y 790 .. 808.390625`; the background is painted into
  rows 790–807 and row 808 is left completely empty. Unsnapped that was **91
  levels** on a dark switch — the largest single disagreement the diff has
  ever reported.
* a Slider thumb at 33.3% lands at `x 102.604 .. 114.604`. The browser paints
  it at 103 .. 115 — snapped at both edges, width preserved at 12 — and puts
  no ink at all in column 102, where ImGui put 133.

This matters in the app, not just here: 292 of the registry's 427 params are
continuous, so a thumb sits on a fraction almost always. So **layout keeps
the fraction and only paint snaps** — `box.slider_geom` and
`box.switch_geom` stay exact, because the thumb's placement depends on them.
Snapping an integer size is exact under translation, so a dragged thumb
never breathes a pixel.

One related trap: a slider's *range* has fractional edges too, but they are
never visible — the 12px thumb always covers the 4px track at the range's
end.

## Rounded clipping

ImGui clips to rectangles only, and a draw list cannot erase, so CSS
`overflow: hidden` on a rounded box has exactly two honest techniques. Both
are in `draw.py`:

* **`fill_clipped`** — for an axis-aligned rect child, round the child's own
  corners by the container's radius, but only the corners it actually
  reaches. That is not an approximation of the clip, it **is** the clip: the
  intersection of a rect with a rounded rect is a rect whose touched corners
  carry the container's arc. It covers what `overflow-hidden` actually meets
  most of the time — a slider range, a progress fill, a selected row inside a
  rounded card.
* **`cover_corners`** — for arbitrary content (text, icons, a scrolling
  subtree), clip to the rect and then paint the four corner notches back in
  the colour *behind* the container. Exact whenever that backdrop is a known
  flat colour, which inside a panel it is.

This was pulled ahead of ScrollArea because the Slider needed it at once:
the track is `overflow-hidden rounded-full` and the range is a plain rect, so
the range's ends are shaped entirely by the track.

## Rings, and where ImGui puts a stroke

shadcn's `ring-3` is a box-shadow, and CSS never paints an outer shadow under
its own element — so on an Input with a transparent background a filled
expanded rect would show through the middle. It has to be a true annulus,
which means a stroke, which means knowing where ImGui puts one:

```
thickness 1   covers [p, p + 1)        <- wholly inside, the finding above
thickness 3   covers [p - 1, p + 2)
```

**ImGui centres a rect stroke on `p + 0.5`, not on `p`.** So a band of
`width` px landing wholly outside the box needs the path expanded by
`0.5 + width/2` — 2.0 for the 3px ring, which is neither 3 nor 1.5. The same
formula gives 1.0 at width 1, which is the expansion the Card's ring was
already measured to need.

## The demo

`dashboard.py` composes the primitives into the Hyperspace dashboard — the
same surface as `prototypes/dashboard/`, drawn with nothing but `draw.py`, on
real catalog and band data, headless, in both themes.

Layout follows the house pattern (`ui_players.lay_out`,
`ui_players.py:122-176`): a pure function of size returning every rectangle,
no imgui in it, drawn in a second pass.

Primitives now in the kit: Badge, Card, Button, Tabs, SidebarItem, Table,
meter, sparkline, trend arrow, Slider, Switch, Input, Select and Tooltip,
plus `label`/`fit_text` for type. Three were
added by the demo rather than by the diff, because composing is what exposes
them:

* **truncation** — shadcn leans on `truncate`/`line-clamp`; ImGui clips
  nothing, so long text ran out of its card. `fit_text` is the same binary
  search `ui.py:317-329` uses.
* **drawn trend marks** — Geist's latin subset has no arrows, so ↗/↘ came out
  as missing glyphs. They are triangles now, the way `ui_players.py:421-539`
  draws device glyphs.
* **per-segment area fill** — `add_concave_poly_filled` triangulates a whole
  outline and leaves visible streaks across an area chart. One convex
  trapezoid per segment is exact.

## Interaction and easing

`interact.py` is `Panel._track` (`hyperspace/ui.py:1311-1357`) generalized —
the one place in 20,800 lines of UI code that already runs a real widget for
behaviour and paints its own chrome. Two rules it keeps:

* **Every interactive primitive carries an `invisible_button` with its
  `##id`.** `tests/ui_driver.py:43-46` finds controls that way and
  twenty-two `test_ui_*.py` files depend on it. `Ui.hit` also refuses a
  duplicate id, because two widgets sharing one is a silent bug in both
  ImGui and the driver.
* **Chrome is drawn from eased state.** ImGui keeps nothing between frames,
  so shadcn's `150ms cubic-bezier(.4,0,.2,1)` lives in `ease.Anim`, keyed by
  widget id and stepped once a frame. Per `REVIEW.md` the step is O(live
  widgets) and drops anything that stopped drawing.

`ease.cubic_bezier` is pinned to Chromium's own Web Animations output to
1e-5 (`test_ease.py`), because this curve is what everything in the kit
moves on.

### Tier 1, over stock widgets

Slider, Switch, Input, Select and Tooltip each run a **real imgui widget**
for behaviour and paint dkit chrome under it. That is not a shortcut, it is
the constraint: `tests/ui_driver.py:43-46` finds controls by wrapping stock
widgets, and its `enter()` action drives a slider by Ctrl+clicking it into a
text field — behaviour only `imgui.slider_float` has. Twenty-two test files
depend on it.

Three things that fell out of wiring them up, none of which the diff could
have caught:

* **the stock slider draws its format string across the middle of the
  track.** shadcn's has no inline text — a readout is a separate label — so
  `Col_.text` is pushed transparent, except while Ctrl+click entry is up,
  which is the one time those glyphs are the thing being typed into.
* **a `Ui` is rebuilt every frame**, so per-widget state kept on it is thrown
  away before it can be read. The Shift-fine value, the text-entry flag and
  the tooltip's hover clock live on `Anim` instead — the one object the kit
  already threads across frames. The tooltip could never reach its delay
  until this was fixed.
* **a tooltip must not have a hit target of its own.** It takes `hovered`
  from the control's own `State`, because one that took the hover would
  steal it from the thing it describes and blink at the easing's period —
  exactly the trap `row_action` exists to close.

**Taper is deliberately not in the kit.** `_track` takes a `norm` in 0..1
along the throw and lets the caller own the mapping, because a taper belongs
to the param model rather than to the chrome; `interact.slider` follows that.
Detents and Shift-fine *are* here, since both are about the drag rather than
about the param.

`ease.mix` interpolates **premultiplied**, and that is not a detail: a
straight RGBA lerp from `transparent` goes through transparent *black*, so a
sidebar item measurably darkened to 20 on its way from 23 to 38 before this
was fixed. Browsers premultiply; so does the kit.

The demo now draws into a real window's draw list rather than the background
list — `replay.keep` (`hyperspace/replay.py:91`) only carries the page
window's own list into the canvas tap, so background-list chrome would be
missing from `panel:graph`.

## Icons

Lucide — the set shadcn uses — is a good fit for a draw list: every icon is a
24x24 box of *stroked* paths, 2px wide, round caps and joins, which is
`path_line_to` / `path_bezier_cubic_curve_to` + `path_stroke` almost exactly.
So they are vector at any size, take their colour from a token, and need no
atlas, no texture and no new runtime dependency.

`dump_icons.js` reads lucide-react's own node data (better than parsing SVG
files: no markup, and the same geometry the React oracle renders),
`build_icons.py` resolves everything awkward ahead of time, and `icons.py` is
the generated table — 38 icons, 553 ops, 16 KB. `icon_sheet.py` renders them
all, which is how three bugs were caught that no amount of staring at the
code would have found:

* **a circle written as two 180-degree arcs** hits the one case where SVG's
  large-arc flag is ambiguous. It put a notch in `circle` and mangled the
  dots in `ellipsis`, `grip-vertical` and `info`. Circles are built from four
  cubics now.
* **a path that already ends where it began** must not also be given ImGui's
  `Closed` flag — that adds a zero-length segment which, under round joins,
  draws a visible tick. Every circle had one.
* **quadratics.** My first survey of the path commands said there were none;
  it had been run before alias-following was added, and four of the aliased
  icons use them.

Lucide dropped brand icons, so there is no `github`; the header button is
text. ISC licence in `Lucide-LICENSE.txt`.

## Menus and popovers

The hard parts of a popup are focus, dismissal on click-away or Escape,
nesting and z-order — all of which ImGui already does. `menu.py` borrows its
popup window and paints shadcn's chrome into it rather than reimplementing
any of it. Open with `imgui.open_popup(key)` from an
`interact.icon_button(..., "ellipsis-vertical")`; draw with
`menu.popup(ui, key, items)`, which returns the chosen id.

Items carry an icon, a shortcut, a `destructive` variant, a `checked` state
and an `enabled` flag; `menu.sep()` and `menu.heading()` are the other two
row kinds.

Two things worth knowing:

* **The shadow and ring fall outside the popup window**, which imgui clips
  to, so the chrome widens the clip rect while it draws.
* **`replay.keep` drops every popup, menu and tooltip** from the GRAPH canvas
  tap (`hyperspace/replay.py:91`). A menu opened over that canvas will not
  appear in the `panel:graph` texture that feeds the render graph. Fine on
  the panel; it cannot be part of anything projected.

## The box model

`box.py` is the layer that stops the kit degenerating into typed offsets.
Without it the trend badge ended up carrying `+26`, `+6` and `+19` — three
constants that did not agree with each other, so the label sat a pixel
inside the icon and the icon a pixel above centre. Nobody reads that and
sees it. The answer is not better constants; it is not writing constants.

* **`Rect`** — `pad()` in CSS shorthand order, `expand`, `cut_left/right/
  top/bottom`, `align`. Padding a box is a thing you can now say.
* **`Flow`** — a measured single-line row. Items are collected, then placed,
  so the row knows its own width *before* deciding where anything goes.
  That is what lets a pill size itself to its contents, or a row centre
  itself in a box it did not choose.
* **`place_popover`** — Radix's placement model, which shadcn uses: the
  panel sits on a `side` of the **anchor**, offset by `sideOffset`, aligned
  on the cross axis, then **flipped** if it will not fit and **shifted** to
  stay on screen. ImGui's default is to place a popup at the mouse, which
  reads wrong for a row action — the menu should land in the same place
  however you arrived at the button.

All three are pure geometry with no imgui in them, so they are unit-tested
the way `ui_players.lay_out` (`ui_players.py:122-176`) is — including a
sweep that asserts a popover never leaves the viewport from any trigger
position.

## Testing it

`test_interaction.py` drives synthetic input and reads the result back, so
the kit's behaviour is checked without a person at the window.

It exists because of a bug it would have caught and a manual check did not:
the row kebab flickered and could never be clicked, and the screenshot I
took looked fine because **the script hovered for six frames — shorter than
the 150ms transition**, so the oscillation had not started. Every test here
dwells well past the easing period and asserts stability over time rather
than the state of one frame. A bug that needs time to appear needs a test
that spends time.

```bash
uv run python -m pytest tools/dkit/ -q          # 277 with tests/test_ui_shell.py
```

`test_components.py` pins the measured geometry laws — the slider's two
mappings, the switch's fractional height, the snapping rule and the rounded-
clip corner flags — as pure functions, no GL and no display, the way
`test_box.py` and `test_flex.py` are. `test_interaction.py` drives the real
thing: eighteen tests, every one dwelling 40 frames against a 9-frame
transition.

Two seams make it possible: `render(..., script=[(x, y[, down])],
keys=[(frame, key)])` drives the pointer and the keyboard a frame at a time,
and `menu.LAST_RECT` records where ImGui actually put each popup. Reading
the menu's position from pixels was tried first and is unreliable — a
hovered table row composites to within one level of the popover fill, so the
bounding box swallowed the row.

## Running it

Nothing here needs `HYPERSPACE_HOME` — dkit touches none of the app's state.
On a Mac, after the usual `uv sync`, that is the whole setup.

### Use it

```bash
cd hyperspace-python
uv run python tools/dkit/dashboard.py --live
```

Icons are generated; to rebuild them after changing the wanted list:

```bash
cd prototypes/dashboard
node ../../hyperspace-python/tools/dkit/dump_icons.js > /tmp/lucide.json
cd ../../hyperspace-python
uv run python tools/dkit/build_icons.py /tmp/lucide.json
uv run python tools/dkit/icon_sheet.py --out /tmp/dkit   # and look at it
```

Opens a window and runs until you close it. Hover the sidebar and the table
rows, click the nav items, click the tabs — they filter the catalog for real
(All 101, 4-polytopes 61, Regular 6, Stars 8, Solids 13). Resize it and the
layout follows; the table grows and shrinks with the window. `--theme light`
for the light palette.

Transitions run off the wall clock here, not off a fixed dt, so what you see
is the real 150ms.

### Stills, if you want them

```bash
uv run python tools/dkit/dashboard.py --out /tmp/dkit --theme dark
uv run python tools/dkit/dashboard.py --out /tmp/dkit --theme light
```

A hover easing in and out, as a frame sequence (30 PNGs):

```bash
uv run python tools/dkit/dashboard.py --out /tmp/dkit --theme dark --hover
```

### The unit tests, which need no GL and no display

```bash
uv run python -m pytest tools/dkit/test_ease.py -q
```

### The diff, which also needs the React oracle

Two halves: the oracle is a Vite build, the kit is Python.

```bash
# once
cd prototypes/dashboard && npm install && npm run build
npx vite preview --port 4173 &

# then, from hyperspace-python
node tools/dkit/capture_react.js "http://localhost:4173/?gallery" /tmp/dkit
uv run python tools/dkit/gallery.py --out /tmp/dkit
uv run python tools/dkit/diff.py /tmp/dkit
```

`/tmp/dkit/contact.png` is `react | imgui | diff x4`. Add `&dark` to the URL
and `--theme dark` to `gallery.py` for the dark pass.

`probe_stroke.py` prints where ImGui actually puts a stroke — run it if a
border ever lands a pixel off on a different machine.

### On a Mac, expect different numbers

Every figure in this file was measured on Mesa/llvmpipe under Xvfb. The Mac
rasterizes through Metal and **will not match them** — the project already
gates its render goldens on `GL_RENDERER` for the same reason
(`tests/test_golden_frames.py:336`). The straight edges and fills should
still be exact, because those are geometry; the corner displacement figure
is the one to expect to move. Record a Mac baseline and compare against that
rather than against this container's.

The windows are created with `COCOA_RETINA_FRAMEBUFFER` off, so the
framebuffer is 1:1 with the spec on a Retina display. Without it the readback
comes back at 2x and `gallery.py`'s size check trips.

## Known limits

- **Baselines are machine-class specific.** GL here is Mesa/llvmpipe under
  Xvfb; the Mac is Metal. The project already gates its render goldens on
  `GL_RENDERER` (`tests/test_golden_frames.py:336`) for the same reason —
  expect to re-baseline on the Mac rather than to match this container's.
- The diff is a tool, not a CI gate, until the kit stabilizes.
- `--tess` on `gallery.py` exists only to document that tessellation is not the
  lever it looks like.
