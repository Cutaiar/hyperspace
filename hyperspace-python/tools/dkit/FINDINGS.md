# Can Dear ImGui look like shadcn?

**Yes, to within a pixel — and the reason is narrower than it sounds.**

shadcn's chrome is a small, closed vocabulary: a rounded rect, a 1px border,
an outside ring, a vertical gradient, a soft shadow, and eight greys. Five
operations. Dear ImGui lacks a primitive for two of them, and both turned out
to be reconstructible to within a level. Nothing in the result depends on a new
dependency, a different renderer, or a fork of ImGui.

Measured across 14 chrome cells spanning four Badge variants, two Card
variants, six geometries and both themes:

| | light | dark |
|---|---|---|
| straight edges, borders, fills, gradients, rings, shadows | **0–1 levels**, 0 pixels over threshold | **0–1 levels**, 0 over |
| rounded corners (geometric displacement) | **0.776 px** worst, 0.28 mean | **0.776 px** worst |
| background | 0 pixels differ | 0 differ |

The bar was "chrome within ~1px, glyphs may differ". It is met with room.

---

## What the residual actually is

Corner arcs, and nothing else. Both rasterizers track the analytic circle;
ImGui's small-radius arcs sit about a third of a pixel outside Chromium's
(mean +0.28px at r=10, −0.15px at r=26). Lowering
`circle_tessellation_max_error` does not help and slightly hurts, so this is
the two rasterizers differing rather than geometry waiting to be fixed. It is
invisible at 1× and will not compound, because it is bounded by the arc, not
by accumulation.

## The four things that had to be got right

Each of these was wrong on the first attempt and found by measurement, not by
reading documentation.

1. **ImGui's 1px stroke is not centred on the path.** The top/left edges cover
   `[p_min, p_min+1]`, the bottom/right `[p_max-1, p_max]`. So it already falls
   wholly inside the rect bounds — which is exactly CSS `border-box` — and the
   correct inset is *none*. Two plausible insets (half a pixel, then a full
   pixel on `p_max`) were measured away before that landed.
   `probe_stroke.py` is the calibration.

2. **Tailwind v4 interpolates gradients in oklab with premultiplied alpha.** A
   straight sRGB lerp between the same endpoints is up to 2.6 levels off in the
   middle — over budget. Doing it properly reproduces Chromium to within 0.86
   levels, which is rounding. The ramp goes up as a 1×N texture through
   `add_image_rounded`, so the rounded clip comes free.

3. **ImGui's font size is not a CSS pixel.** stb_truetype scales so that
   `ascent − descent` equals the requested size; CSS maps the em square to
   `font-size`. Geist is upem 1000 with ascent 1005 / descent −295, so its span
   is 1.30em and ImGui draws 14px CSS text at **77%** of the right size. The
   ratio belongs to the font, so the kit carries it per face.

4. **A theme is not only a colour swap.** The card gradient's endpoints are
   `primary` and `card`, so in dark the wash runs *light*. And the destructive
   badge is `bg-destructive/10 dark:bg-destructive/20` — the alpha itself is
   themed. Both failed the diff until the tables learned about them.

## Where ImGui genuinely cannot follow

- **No OpenType features.** `tabular-nums` is the one shadcn leans on, and
  stb_truetype cannot apply it: a digit-heavy string comes out 4% narrow
  (138px → 132px). The project already answers this the other way round, with
  a mono face for readouts (`ui.py:126-129`), and that remains the answer.
- **No variable fonts, no woff2.** Static instances have to be cut ahead of
  time (`fonts/README.md`). Fine for a fixed set of weights; not fine if a
  design wants continuous weight.
- **Glyph rasterization differs** — ImGui's is slightly lighter. At 1× the two
  are hard to tell apart side by side; they will never be pixel-identical, and
  the bar deliberately did not ask them to be.
- **No shadow primitive.** Stacked rounded rects are within a level at the
  2px/5% shadows shadcn uses. They would get expensive and banded at the large,
  soft shadows a different design language might want. NanoVG is already wired
  into this project and *does* have real feathered shadows via `box_gradient`
  (`ui_pad_nvg.py:119-128`), but it is off headless with no fallback, so it
  cannot back a diff harness. Worth reaching for only if the shadows grow.

## What this does not yet prove

Honest scope. The kit covers **static chrome for two primitives**. It does not
cover:

- **Interaction states and transitions.** shadcn animates on a 150ms
  cubic-bezier; ImGui is stateless per frame, so this needs an `id → (value,
  target)` ease map stepped once a frame. That is the one piece of genuinely
  new machinery and it is not built. The project has no UI easing today —
  `motion.py`'s springs drive parameter values, not chrome.
- **Layout.** There is no flex or grid. The house pattern already exists
  (`ui_players.lay_out`, `ui_players.py:122-176` — a pure width→rects function,
  unit-tested without imgui), and it is the right one, but the shadcn layouts
  would have to be written out by hand.
- **The remaining primitives** — Button, Tabs, Table, SidebarItem. All are
  combinations of the five operations above, so the risk is low, but "low risk"
  is not "done".
- **The Mac.** Every number here is Mesa/llvmpipe under Xvfb. The Mac is Metal
  and will differ; the project already gates its render goldens on
  `GL_RENDERER` for exactly this reason (`tests/test_golden_frames.py:336`).
  Re-baseline there before trusting these figures on the rig.

## The constraint to design around

`tests/ui_driver.py:43-46` finds controls by wrapping **stock** imgui widgets
and reading the text after `##`. Twenty-two `test_ui_*.py` files drive the
panel that way. A primitive drawn purely into a draw list drops out of the
driver's reach and off those tests. So every interactive primitive in the kit
must keep an `invisible_button` carrying the same `##id` — which is what
`ui_players._button` (`ui_players.py:651-658`) already does, and what
`Panel._track` (`ui.py:1311-1357`) already does for sliders.

That technique — `channels_split(2)`, push the stock widget's colours to
transparent, run the real widget for behaviour, paint custom chrome on the
lower channel — is used exactly **once** in 20,800 lines of UI code today.
Generalizing it is the kit, and it is the single highest-leverage change
available: it buys shadcn's look without giving up either the behaviour or the
test harness.

## Recommendation

Carry on, in this order: generalize `_track` into the kit's widget sandwich,
build the ease map, then port Button / Tabs / Table / SidebarItem. Hold the
diff as a tool rather than a CI gate until the kit stops moving, then
re-baseline on the Mac and consider wiring it in beside the render goldens.

The React frontend alternative is closed, and not on aesthetics: a web app was
already tried and retired (`DECISIONS.md:33`), no IPC exists that could drive a
UI (OSC is input-only and lane-addressed; the bridge is 16 lanes of 14-bit
MIDI), the frame contract is zero-lag and the panel already spends the only
~16ms of slack, and the GRAPH canvas is itself a texture inside the render
graph. ImGui is the right target; it just needed to be measured rather than
assumed.
