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
so `fonts/` holds static instances cut from that exact file at wght 400/500/600.
With those, ink extents land within a few px on a 110-170px string:

```
text.title30   144x29  vs  144x29   (exact)
text.body14    113x11  vs  115x10
text.num14     138x12  vs  132x12   <- tabular-nums, -4%
```

Two findings worth carrying forward:

* **ImGui's font size is not a CSS px.** stb_truetype scales so that
  `ascent - descent` equals the requested size; CSS maps the em square to
  `font-size`. Geist is upem 1000 with ascent 1005 / descent -295, so its span
  is 1.30em and ImGui renders 14px CSS text at 77% unless asked for 14 x 1.30.
  The ratio is a property of the font, so the kit keeps it per face
  (`draw.FONT_SPAN_EM`).
* **No OpenType features.** `tabular-nums` is the one shadcn leans on, and
  stb_truetype cannot apply it — hence -6px on a digit-heavy string. The
  project already solves this the other way, with a mono face for readouts
  (`ui.py:126-129`).

## The demo

`dashboard.py` composes the primitives into the Hyperspace dashboard — the
same surface as `prototypes/dashboard/`, drawn with nothing but `draw.py`, on
real catalog and band data, headless, in both themes.

```bash
HYPERSPACE_HOME=$(mktemp -d) uv run python tools/dkit/dashboard.py \
    --out /tmp/dkit --theme dark
```

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

## Running it

```bash
cd hyperspace-python
export UV_NO_GROUP="hands dream"

# oracle (needs the dashboard built and previewing on :4173)
( cd ../prototypes/dashboard && npm run build && npx vite preview --port 4173 & )
node tools/dkit/capture_react.js "http://localhost:4173/?gallery" /tmp/dkit

# the kit, and the verdict
HYPERSPACE_HOME=$(mktemp -d) uv run python tools/dkit/gallery.py --out /tmp/dkit
uv run python tools/dkit/diff.py /tmp/dkit
```

`/tmp/dkit/contact.png` is `react | imgui | diff x4`.

## Known limits

- **Baselines are machine-class specific.** GL here is Mesa/llvmpipe under
  Xvfb; the Mac is Metal. The project already gates its render goldens on
  `GL_RENDERER` (`tests/test_golden_frames.py:336`) for the same reason —
  expect to re-baseline on the Mac rather than to match this container's.
- The diff is a tool, not a CI gate, until the kit stabilizes.
- `--tess` on `gallery.py` exists only to document that tessellation is not the
  lever it looks like.
