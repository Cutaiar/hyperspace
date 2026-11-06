# dkit

Can Dear ImGui, on this project's own stack, be made to look like shadcn/ui?

This is the measuring rig for that question, plus the primitive kit it measures.
Nothing here is imported by the app — it lives in `tools/` on purpose.

## The bar

**Chrome matches within ~1px; glyph rasterization may differ.** Two text
rasterizers never agree (ImGui's stb_truetype applies no OpenType features and
snaps glyphs to integer positions; browsers use subpixel advances), so text is
out of scope and the diff runs with it hidden. The box is the thing.

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

## Results — Badge and Card, 14 chrome cells

```
flat: edges+fills   max 0-1 levels, 0 pixels over threshold, all 14 cells
corners             worst displacement 0.776 px   (bar 1.0)
background          0 pixels differ
```

Straight edges, borders, radii, fills, gradients, rings, shadows and colours
are **pixel-exact to within a level**. The whole residual is corner-arc
antialiasing at roughly a third of a pixel (mean +0.28px at r=10, -0.15px at
r=26 — ImGui's small-radius arcs sit a touch outside Chromium's). Lowering
`circle_tessellation_max_error` does not help and slightly hurts, so this is
the two rasterizers differing, not geometry to be fixed.

### Text (advisory)

Geist ships only as a variable woff2, which stb_truetype can read neither of,
so `fonts/` holds six faces cut from that exact file by `build_fonts.py`:
wght 400/500/600, each with and without tabular figures frozen in. With
those, ink extents land within a few px on a 110-170px string:

```
text.body14    113x11  vs  113x10   (exact)
text.title30   144x29  vs  146x29
text.num14     138x12  vs  132x12   <- advance rounding, not tnum
```

Two findings worth carrying forward:

* **ImGui's font size is not a CSS px.** stb_truetype scales so that
  `ascent - descent` equals the requested size; CSS maps the em square to
  `font-size`. Geist is upem 1000 with ascent 1005 / descent -295, so its span
  is 1.30em and ImGui renders 14px CSS text at 77% unless asked for 14 x 1.30.
  The ratio is a property of the font, so the kit keeps it per face
  (`draw.FONT_SPAN_EM`).
* **No OpenType features at runtime** — so `tnum` is frozen into the cmap at
  build time instead (`build_fonts.py`), producing a parallel `-tnum` face.
  Proportional Geist digits are 384-663 units wide; frozen they are all 600.
  A live readout cycling 1.36 / 0.50 / 2.08 **jitters by 9px** proportional
  and is **stable at 23px** tabular. That is the reason to do it — not width
  parity with the browser, which it does not buy.
* **ImGui rounds every glyph advance to a whole pixel** (9.0, 5.0, 8.0 at
  14px; still 66.0, 38.0 at 100px). Browsers use fractional advances, so a
  long string drifts by a few px either way. This is the irreducible text
  difference, and it is why `text.num14` sits -6px against the oracle.

## The demo

`dashboard.py` composes the primitives into the Hyperspace dashboard — the
same surface as `prototypes/dashboard/`, drawn with nothing but `draw.py`, on
real catalog and band data, headless, in both themes.

Layout follows the house pattern (`ui_players.lay_out`,
`ui_players.py:122-176`): a pure function of size returning every rectangle,
no imgui in it, drawn in a second pass.

Primitives now in the kit: Badge, Card, Button, Tabs, SidebarItem, Table,
meter, sparkline, trend arrow, plus `label`/`fit_text` for type. Three were
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
