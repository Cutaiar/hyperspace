# dkit — session handoff

Written at the end of the session that built ScrollArea, intrinsic sizing,
Button, ButtonGroup, ContextMenu and Combobox. `README.md` and `FINDINGS.md`
are accurate as the **Tier 1** record and still worth reading for the
calibration findings; this file is what changed after them, plus the
pitfalls and the process revisions, so a fresh session does not relearn any
of it.

Branch: `claude/magical-ritchie-fkh5e0`. Tree clean at `2df969b`.

---

## Read in this order

1. **`ROADMAP.md`** — what to build next and the constraints each component
   has to respect. The four rules at the end are the important part.
2. **This file** — current state, the traps, and how the work is organised.
3. **`README.md`** — how the rig works, and the calibration findings that
   cost a day each to discover (ImGui's stroke is not centred on the path;
   its font size is not a CSS px; three bindings reverse the C++ argument
   order; the browser snaps what it paints to whole pixels).
4. **`FINDINGS.md`** — the Tier 1 verdict.

A reasonable opening message for a new session:

> Read `hyperspace-python/tools/dkit/ROADMAP.md` and `HANDOFF.md`. Branch
> `claude/magical-ritchie-fkh5e0`. Build <component> with the oracle-first
> method: add the real shadcn component to `prototypes/dashboard` on the
> `?probe` route, measure it with `probe_react.js`, then match it in the kit
> and diff it on `?gallery`. Do not implement from a reading of the spec.

---

## Where it stands

```
629 tests in tools/dkit, 664 with tests/test_ui_shell.py.  16 skipped.
chrome diff: flat 0-2 levels across 33 cells, worst corner 0.776 px, both themes.
```

| | state |
|---|---|
| tokens, draw primitives, box model, flex, interaction, popover placement, rounded clipping, pixel snapping | done |
| **Tier 1** Slider, Switch, Input, Select, Tooltip | done, diffed |
| **ScrollArea** | done — and the page scrolls, not just the table |
| **intrinsic sizing** | done — `box.Node` + `measure_tree` + `place_tree` |
| **Button, ButtonGroup** | done — 6 variants x 8 sizes, 116 tests |
| **ContextMenu** | done — 171 tests; found six wrong numbers in `menu.py` |
| **Combobox** | done — Base UI shape, the trigger IS the input |
| focus-visible | modelled: `Ui.focus_visible` tracks keyboard-vs-mouse |
| variant resolver (cva) | **still missing**, and now eight ad-hoc tables deep |
| text wrapping / multi-line measure | still missing |
| density / `Ui.scale` | still unused |
| **adoption** | **still nothing.** The kit is imported by no app code. |

### Still to build, in the order I would take

1. **Dialog** and **Sheet** — both need a modal layer and a scrim, which
   nothing in the kit has yet. Do Dialog first; Sheet is Dialog with a side.
2. **Toast** — needs a timed queue, which is the first thing in the kit with
   a lifetime longer than a frame and no widget to hang state on.
3. **Kbd**, **Breadcrumb**, **Checkbox** — small, and Checkbox is 47 toggle
   params.
4. **A variant resolver**, before a ninth table is written.
5. **Port one real `ui_pane.py` section.** This is the untested hypothesis
   and has been since the beginning. Everything else is rehearsal.

### Loose ends left deliberately

- No gallery cells for Button, ButtonGroup, ContextMenu or Combobox, so
  their chrome is **not** in the pixel diff — only in unit tests and by eye.
  That is the single biggest gap in coverage right now.
- Old `draw.button` / `interact.button` stubs still exist; callers have not
  been migrated to `comp_button`.
- `interact.select` draws its label 1px left of where it should
  (`x + pad_l`, should be `x + 1 + pad_l`; the chevron is already right).

---

## Pitfalls — every one of these was paid for

### ImGui's shape, not the browser's

- **`imgui_bundle` reverses the C++ argument order** on `add_rect`,
  `add_polyline` and `path_stroke`. Pass those by keyword, always. A
  positional call silently puts the thickness where the rounding goes.
- **`channels_split` must be matched by `channels_merge` in the same
  frame.** ImGui asserts on a nested split rather than tolerating it, which
  takes the window down — so a primitive that forgets the merge breaks every
  control drawn *after* it, and the traceback points at the innocent one.
  `_sandwich_begin`/`_sandwich_end` pair correctly; a hand-rolled split does
  not.
- **A popup window takes the keyboard the instant it appears.** An input
  left behind in the parent window stops receiving characters exactly when
  the list opens — so you can click a combobox, watch the panel appear, and
  type into nothing. Fix: the popup spans the **trigger** as well as the
  panel, so the field is inside the focused window.
- **Having focus is not being active.** The popup can hold the keyboard
  while nothing inside it is the active item, and characters still go
  nowhere. `set_keyboard_focus_here()` on the frame it opens — and *only*
  that frame, or it fights the user every frame after.
- **ImGui draws a blue nav-cursor rectangle** around a keyboard-focused
  item. No shadcn component has one. Push `Col_.nav_cursor` transparent
  wherever the kit asks for focus itself.
- **A stock slider draws its format string across the track.** Push
  `Col_.text` transparent except during Ctrl+click entry.
- **imgui's `Col_.text` defaults to white**, so an `input_text` is invisible
  on the light theme until the theme's ink is pushed. The regression test for
  this was written against the broken code first, which is the only way to
  know it would have caught it.
- **Screen-space vs window-space cursor inside a child window.**
  `set_cursor_screen_pos` inside a scroll child inflates the scroll range
  without bound (3238 → 5638 → 51238 px over three frames). Use
  `set_cursor_pos`.
- **A child window has its own draw list.** Content drawn into the parent's
  list paints *over* the header that should occlude it. Swap `ui.dl` to the
  child's list for the duration.
- **Per-widget state cannot live on a per-frame object.** `Ui` is rebuilt
  each frame, so anything stored on it is discarded before it can be read —
  a tooltip could never reach its own delay. State goes in `anim.store`.

### Measuring

- **Chromium lays out on a 1/64 px grid and snaps what it PAINTS to whole
  device pixels.** Unsnapped, a switch disagreed by 91 levels — the largest
  single residual the diff ever reported. Layout keeps the fraction; only
  paint snaps.
- **Radix's default `step` is 1**, which silently snapped a spec fraction of
  0.375 to 0.38. Pass `step={0.0001}` in the oracle.
- **The arc metric has to be told where the arcs are.** It walked *cell*
  corners, which is nowhere near a slider thumb's. `contour.sub_boxes()`
  takes per-box corner lists; a switch reported a phantom 0.996 px until
  occluded corners were excluded.
- **A portalled component defeats pinning** — pin the *trigger* instead, and
  the dump then tells you Radix reserves the arrow's full 10px between
  tooltip and anchor while drawing only 5.071 of it.
- **`capture_react.js` runs a 1600px viewport now.** At 700 floating-ui
  flipped the panel against the live viewport rather than the 1300px canvas,
  which looks exactly like a placement bug in the kit.
- **`_blur_layers` reach must scale with sigma.** Hardcoded 3 truncated
  shadow-md's blur 6 (1345px of shadow became 312). Half-step layers made it
  *worse*, because Skia uses a triple box blur, not a Gaussian — so the
  soft-shadow edge is reported as an advisory rather than fitted.
- **Group opacity is not per-element opacity.** A disabled field folds the
  two with Porter-Duff OVER (`ease.over`) — but **only where the fill and
  border share a box.** Button is `bg-clip-padding`, so its fill and border
  are disjoint and folding predicts 33 where Chromium paints border 28 /
  fill 14. I stated that rule too generally and an agent correctly overrode
  it.
- **An interaction test must dwell past the animation period.** shadcn's
  transition is 150ms ≈ 9 frames; a six-frame check passed on a kebab menu
  that flickered and was unclickable in practice. Every interaction test in
  `test_interaction.py` dwells 40 frames.

### Mine, not the tools'

- **A local constant shadowed a module one.** `lay_out`'s `ROW_H = 24.0`
  shadowed the module's `ROW_H = 34.0`, so the table was laid out at a 24px
  pitch while paint drew 34 and the kebab menu opened 2px above the pointer.
  Renamed to `CTL_ROW_H`. Nothing in the diff could see this.
- **A widget outside any window makes ImGui invent a "Debug" window.** The
  gallery's menu cell needed `chrome_only=True`.
- **A blanket find-and-replace gave a test a variable it does not have**, and
  a stability window averaged pre-scroll frames. Read what a test asserts
  after editing it mechanically.

---

## Process revisions

These are changes to **how** the work is done, and each replaced something
that had already failed once.

### 1. The oracle comes before the implementation, without exception

Not "usually". Every part of this that came out right came out of measuring;
every part that came out wrong came out of reasoning from the Tailwind
classes. `?probe` takes a minute to use.

### 2. Verifying an implementation against its spec is worthless if the
premise picked the wrong spec

The hardest lesson of the session. I briefed an agent that shadcn's Combobox
is Popover + Command, so it ported cmdk's `commandScore` and **verified it
exactly against the shipped JavaScript over 382 input pairs**. Flawless
work, and the wrong rule — shadcn ships `combobox.tsx` built on Base UI,
whose filter is a plain case-insensitive substring match, and whose trigger
*is* the input. The verification could never have caught that, because it
was measuring the right answer to the wrong question.

So: **verify the premise against the real component before verifying
anything against the premise.** For a component, that means reading the
actual registry file, not recalling its recipe. The cmdk port survives as
`rank_items_cmdk()` for a future Command palette, where it is correct.

### 3. The demo is the dashboard, and "visible" means visible

Three separate times I fixed a component's internals and left the thing on
screen untouched — most recently shipping a Combobox whose table and filter
were right while the *drawn* trigger was still the old Popover shape. The
user had to ask twice. A component is not done until the state is reachable
in `dashboard.py --live` and has been looked at.

The gallery is a contact sheet: it proves chrome to a pixel and tells you
nothing about how a control feels under the pointer. Three real bugs — the
stray format string, the discarded per-frame state, the invisible light-theme
input text — were invisible to the diff by construction.

### 4. Spacing is a scale, not a pitch

Prompted by "you're missing the concept of a gap". There was no space scale
at all; containers were hand-sized and gaps were arithmetic at the draw
site. Now `tokens.SPACE` (Tailwind's 4px scale with half-steps), tokenized
component paddings, and `box.stack` / `box.card_body` rather than
`i * pitch`. The failure mode is quiet — nothing looks broken, it just reads
wrong, and no number in the file says which one is at fault.

### 5. Precalculating bounding boxes is the antipattern it sounds like

Prompted directly. Replaced by intrinsic sizing: `box.Node` with a bottom-up
`measure_tree` and a top-down `place_tree`. Measured at **0.38 ms for 955
nodes**, which is affordable per frame precisely because it never crosses an
FFI boundary — the reason Taffy's Python bindings were rejected at 1.4 ms for
180 boxes. Note `flex-basis: 0` (CSS `flex-1`) is not `flex-grow: 1` on an
auto basis: grow distributes only leftover space.

### 6. A test asks the source; it never copies a number

Two tests held a literal `92.0` for a label column and went stale the moment
the spacing moved. Where a pixel probe cannot distinguish two things — a
tooltip floating over the card description behind it — count the thing
instead of sampling it.

### 7. Subagents work, on disjoint files, with the premise stated

Three agents in parallel, each owning one `comp_*.py` + one `test_*.py` and
nothing else, each independently verified against its own oracle pass. All
three came back accurate and one correctly overrode an instruction of mine.
What makes it work: disjoint file ownership, the measure-first method
restated in the brief, and the reviewer re-measuring rather than reading.
What broke it: a wrong premise in the brief propagates straight through
everything downstream, and the agent's verification cannot see it (see 2).

### 8. Hyperspace is not the authority on UI

"hyperspace shouldn't be taken as gospel... don't be too corrupted by it."
I had been arguing "the app does X, so dkit should". The only binding
constraint from the app is the **test harness contract**:
`tests/ui_driver.py:43-46` finds controls by the text after `##`, and 22
`test_ui_*.py` files depend on it — so every interactive primitive keeps an
`invisible_button` with the same id. Everything else about the app's current
UI is a thing to improve, not a specification.

And the standing caution: **do not restyle Hyperspace to look like shadcn.**
What transfers is the method — scales, named tokens, measuring rather than
reasoning. The palette does not: the app is one red and three greys on
black, which is its own language and a deliberate one.

---

## Running it

```bash
cd hyperspace-python && uv sync
```

```bash
xvfb-run -a uv run python -m pytest tools/dkit tests/test_ui_shell.py -q
```

```bash
uv run python tools/dkit/dashboard.py --live
```

The oracle needs the React app built and served:

```bash
cd prototypes/dashboard && npm i && npm run build && npm run preview
```

```bash
node tools/dkit/probe_react.js "http://localhost:4173/?probe" --json /tmp/p.json
```

```bash
node tools/dkit/capture_react.js && xvfb-run -a uv run python tools/dkit/diff.py
```

Routes: `?probe`, `?probe&dark`, `?probe&open` (modal layers — a Radix
Select puts `pointer-events:none` on the body, so no hover is reachable in
that pass), `?gallery`, `?gallery&text`.

---

## One standing caveat

**Every number in these docs was measured on Mesa/llvmpipe under Xvfb.** On
a Mac (Metal) the 0.776 px corner figure will move; straight edges and fills
should hold. Re-baseline on the Mac rather than treating a change as a
regression — `tests/test_golden_frames.py:336` gates the render goldens on
`GL_RENDERER` for exactly this reason.
