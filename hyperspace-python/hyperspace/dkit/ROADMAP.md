# dkit roadmap

What to build next, and why — ordered by how much of Hyperspace's actual
surface each one unblocks, not by how interesting it is.

> **Current state, the traps, and the process this has settled into are in
> [`HANDOFF.md`](HANDOFF.md).** Read that second. This file is the plan;
> that one is where the work actually got to.

## Is any of this already out there?

Asked properly, because building what exists is the worst outcome.

**A shadcn-equivalent for Dear ImGui: no.** The whole field is
`shyalice/imgui_shadcn` (1 star), `lukaasm/ImFluent` (12 stars, Fluent
Design), and two Yoga+ImGui experiments at 0–1 stars. Nothing established,
nothing in Python.

**A layout engine: yes, and it does not fit.** Taffy has Python bindings
(`stretchable`, abi3 wheels, works on 3.14 — verified, flexbox *and* grid),
as does Yoga (`yogalayout`). Measured here:

```
build a 211-node tree from scratch   198 ms      <- per frame, impossible
reuse the tree, restyle + recompute  2.3 ms/frame
recompute + read 180 boxes back      1.4 ms/frame
901-node tree, layout only           6.0 ms
```

The Python↔Rust boundary dominates. 1.4 ms is ~9% of a 16.7 ms frame for
*180 boxes*, and the panel is far richer than that. An immediate-mode UI
wants to describe its layout every frame; this engine can only be used by
building once and mutating, which is the opposite shape — and the project's
own pattern (`ui_players.lay_out`: a pure width→rects function, cached on
resize) is both faster and dependency-free.

**So: write the flex subset, do not adopt the engine.** But take the user's
suggestion and validate it against a browser — a flex page in the existing
gallery harness, diffed the same way the chrome is. That turns "did I
implement flex right" from taste into a measurement, which is the trick
that has worked all the way through this.

## The layer stack

| layer | state |
|---|---|
| tokens (colour, radius, type scale) | done |
| draw primitives (fill, border, shadow, gradient, icon, text) | done |
| box model (`Rect`, padding, cuts, align) | done |
| layout (flex: direction, grow/shrink, justify, align, gap) | done — 27 cases vs Chromium |
| interaction (hit, eased state, the `_track` sandwich) | done |
| popover placement (side/align/offset, flip, shift) | done |
| rounded clipping (`overflow-hidden`) | done — both the rect-child and corner-cover cases |
| pixel snapping (the browser paints on whole pixels) | done — and it was worth 91 levels |
| intrinsic sizing (`box.Node`, `measure_tree`, `place_tree`) | done — 0.38 ms for 955 nodes |
| components | Tier 1 + ScrollArea, Button, ButtonGroup, ContextMenu, Combobox |

## Still missing, after flex

Primitives the browser gives free that ImGui does not, which components
will keep running into:

| missing | why it matters | hit yet? |
|---|---|---|
| ~~**rounded clipping**~~ | **done.** The Slider needed it at once: its track is `overflow-hidden rounded-full` and the range is a plain rect | yes — built |
| **text wrapping / multi-line measure** | descriptions, tooltips, node summaries. `push_text_wrap_pos` exists but `label()` is single-line | a tooltip truncates rather than wraps |
| ~~**intrinsic sizing**~~ | **done.** `box.Node` + `measure_tree` (bottom-up) + `place_tree` (top-down) | yes — built |
| ~~**scroll container**~~ | **done.** `interact.scroll_area`, and the dashboard page scrolls | yes — built |
| **focus ring + tab order** | `focus-visible:ring-[3px]` | mostly: `Ui.focus_visible` tracks keyboard-vs-mouse and every control rings correctly, but nothing orders a tab sequence |
| **variant resolver** (cva) | variants are ad-hoc dicts (`tokens.BADGE`, now `SWITCH`, `INPUT`, `SELECT` too); each component invents its own | yes, and getting worse |
| **transform transitions** | shadcn menus `zoom-in-95`; the ease store does colour only | no — the Switch's thumb slides by hand off an eased scalar |
| ~~**density / scale**~~ | **not a thing we need, and `Ui.scale` is deleted.** Three things were conflated here. DPI is already handled - `_boot` rasterises the atlas at the display's density and ImGui draws in logical points. shadcn's own density mechanism is SIZE VARIANTS, measured per size (a `sm` Select is 28 tall with radius 8, not a scaled 32/10), and the kit has those for Button, Select and Switch. A global zoom multiplier would make the pixel diff meaningless, because there is no oracle for "shadcn at 125%". | the real gap is `sm` on **Input and Combobox**, and the 240px pane is a LAYOUT problem that intrinsic sizing and flex already answer |

The **variant resolver** is now the one that will bite hardest — there are
eight ad-hoc tables, and `comp_button` alone added three. **Text wrapping**
is next after it: Dialog and Toast both want a multi-line measure.

## Components, against Hyperspace's real control inventory

The counts are measured from `params.build_registry`, not guessed: **427
params in a bare registry, realistically 600–900 live** once bands, LFOs,
modifiers and graph instances declare theirs.

| Hyperspace need | how much | component |
|---|---|---|
| continuous param | **292** | **Slider** — taper-aware, detents, shift-fine |
| enum param | **73** | **Select**; Combobox for long lists; ToggleGroup for short |
| toggle param | **47** | **Switch**, Checkbox |
| text param / node rename / numeric entry | — | **Input** |
| trigger param | 15 | Button ✓ |
| every param has a tip | all | **Tooltip** |
| 17 folding sections (`ui_pane.SECTIONS`) | 17 | **Collapsible / Accordion** |
| "a section may scroll down" (REVIEW.md) | — | **ScrollArea** |
| canvas ↔ side-pane split (`ui_graph.band_height`) | 1 | **Resizable** |
| right-click a node | — | **ContextMenu** (reuses `menu.py`) |
| finding one of 600–900 params | — | **Command** palette |
| MIDI-learn, key bindings | — | **Kbd** |
| footer message slot (`_footer`, `MESSAGE_S`) | — | **Toast** |
| destructive confirms (delete node/preset) | — | **AlertDialog** |
| node summary without opening it | — | **HoverCard** |
| band/level meters | 6+ | Progress ✓ (as `meter`) |
| graph location | — | Breadcrumb |

### Order

**Tier 1 — DONE.** Slider, Input, Select, Switch, Tooltip — 412 of the 427
measured params plus every tooltip. All five are diffed against the real
component in both themes and driven by real imgui widgets underneath, so
`tests/ui_driver.py` can still find and drive them.

**Tier 2 — partly done.** ScrollArea ✓, ContextMenu ✓, Button ✓,
ButtonGroup ✓, Combobox ✓. Still open: **Collapsible**, **Resizable**,
**Command** (the cmdk ranking is already ported and verified as
`comp_combobox.rank_items_cmdk`, waiting for this).

**Tier 3 — polish, and the next wave.** Dialog, Sheet, Toast, Kbd,
Breadcrumb, Checkbox — then AlertDialog, HoverCard, RadioGroup, Pagination.
Dialog first: it brings the modal layer and the scrim that Sheet and
AlertDialog both need, and nothing in the kit has either yet.

### Two the requested list left out, which are the biggest wins

**Slider** and **Select** were not on the list of interest, but 292
continuous and 73 enum params are 85% of the registry. Nothing else comes
close. A Hyperspace panel is mostly sliders.

### One that is cheap and underrated

**Command** palette. With 600–900 addressable params and a stated rule that
"everything settable has a stable id", a fuzzy finder over the registry is
nearly free to build and changes how the app is used.

## Constraints every component has to respect

- **Keep an `invisible_button` with the same `##id`** — `tests/ui_driver.py`
  finds controls that way and 22 `test_ui_*.py` files depend on it.
- **Fit the narrowest width.** GRAPH's side pane is 240–320px
  (`REVIEW.md`), and `Ui.scale` exists but is still unused.
- **No per-frame cache rebuilds** (`REVIEW.md`). Layout is cached on size.
- **Popups never reach the canvas tap** — `replay.keep` drops every popup,
  menu and tooltip from `panel:graph`.
- **A persisted param id is a file format** (`REVIEW.md`), so a component
  that renames anything needs the migration rules.

## Picking this up in a fresh session

Everything needed to resume is in the repo, not in a chat log. Read, in
this order:

1. **`ROADMAP.md`** (this file) — what to build, why that order, and the
   constraints each component has to respect.
2. **`HANDOFF.md`** — where the work actually got to, every trap that cost
   a round of rework, and the process revisions each of them forced. Also
   the Gallery tab, which is where you look at all of this running.
3. **`README.md`** — how the kit works, how to run it, how to test it, and
   the calibration findings that are easy to rediscover the hard way
   (ImGui's stroke is not centred on the path; its font size is not a CSS
   px; three bindings reverse the C++ argument order).
4. **`FINDINGS.md`** — the Tier 1 verdict, and what every number was
   measured on.

A reasonable opening message:

> Read `hyperspace-python/hyperspace/dkit/ROADMAP.md` and `HANDOFF.md`. Branch
> `claude/magical-ritchie-fkh5e0`. Build Dialog, which brings the modal
> layer Sheet and AlertDialog also need. Use the browser-oracle pattern:
> add the real component to `prototypes/dashboard`, measure it on the
> `?probe` route, then match it in the kit and diff it on `?gallery`. Do
> not implement from a reading of the spec — `?probe` exists because
> reading the Tailwind classes is how the Slider, the Switch and the Select
> each came out wrong the first time, and because briefing an agent from a
> *recollection* of which primitives a component is built on sent a whole
> Combobox the wrong way.

### The order I would take from here

1. **Dialog**, then **Sheet** — the modal layer and the scrim are the new
   primitives; Sheet is Dialog with a side.
2. **Toast** — the first thing in the kit with a lifetime longer than a
   frame and no widget to hang its state on.
3. ~~**Kbd**~~, **Breadcrumb**, ~~**Checkbox**~~ (Kbd and Checkbox done — see `HANDOFF.md` item 4) — small, and Checkbox is 47 toggle
   params.
4. ~~**Gallery cells for Button, ButtonGroup, ContextMenu and Combobox.**~~
   Done — all four are in the diff, and doing it found two bugs in the
   Combobox trigger plus a hole in the harness that had been hiding every
   icon's position and colour from every metric. See `HANDOFF.md` item 1 and
   `RETRO.md` rows 42-56. What is left of it is the Combobox panel's ROWS.
5. **A variant resolver**, before a ninth ad-hoc table is written.
6. **Collapsible / Accordion** — 17 folding sections in `ui_pane.SECTIONS`.

And the one thing none of this answers: **nothing is adopted yet.** The kit
now covers 412 of 427 params, which is the whole reason Tier 1 came first;
porting one real `ui_pane.py` section is the test that matters, and until
that happens the hypothesis is still untested where it counts.

### The method that has worked

Every part of this that came out right came out of measuring rather than
reasoning:

- the chrome, against a screenshot of the real component;
- the easing curve, against Chromium's Web Animations output;
- flex, against Chromium's own layout (which caught that CSS scales the
  shrink factor by base size but not the grow factor);
- the interaction bugs, against tests that **dwell past the animation
  period** — the kebab flicker survived a six-frame check because the
  transition is nine frames long;
- Tier 1, against the real components on `?probe`, which caught that a
  Slider's range and thumb use different mappings, that a Switch is
  18.390625 px tall, that the thumb's white is a literal rather than a
  token, and — the one that reaches past the gallery — that **the browser
  snaps what it paints to whole pixels** while laying out on fractions.

Composing them into the demo caught two more that no diff could: the stock
slider draws its format string across the track, and per-widget state kept
on the per-frame `Ui` was thrown away before it could be read, so the
tooltip could never reach its delay. Measure, then compose; they find
different bugs.

### The six rules this has settled into

Each one is here because breaking it cost a round of rework.

0. **Get the current shadcn first, then probe it.** Before any component:
   `hyperspace/dkit/dev/refresh_shadcn.sh`, read whatever it says moved, and re-probe.
   The registry is a moving target — inside this project's lifetime
   `radix-nova` has changed its menu treatment, its focus ring and the whole
   shape of its Combobox — so a kit measured against a vendored copy nobody
   has refreshed is measured against nothing, and every number downstream
   inherits the staleness silently. The script is thirty seconds and the
   answer you want from it is "no component changed". That is a measurement
   too, and worth having made.

   This is rule zero rather than rule six because it comes before rule one:
   an oracle built on a stale component is a confident wrong answer, which
   is worse than no answer. It is the same failure as the Combobox — an
   exact measurement of the wrong thing.

1. **Build the oracle first.** Never implement from a reading of the spec.
   The Tailwind classes say `h-[18.4px]`; the browser says 18.390625. They
   say one slider; the browser draws two mappings. `?probe` exists for this
   and takes a minute to use.
2. **A colour, a padding and a gap are tokens on a scale.** Not literals at
   the draw site. The failure is quiet - nothing looks broken, it just reads
   wrong, and no number in the file says which one is at fault. This is
   `box.py`'s own argument ("the answer is not better constants; it is not
   writing constants") and it applies to spacing exactly as it applies to
   the offsets that started it. `tokens.SPACE`, and `box.stack` /
   `box.card_body` rather than `i * pitch`.
3. **The React app is the rubric, and it has two pages.** Every component
   lands in the prototype twice before the ImGui version is judged: once on
   the **gallery page**, enumerated in every state it has, and once on the
   **dashboard page**, used the way something real would use it. The second
   is where the judgement is - a Combobox filtering 600 params is a
   different claim from a Combobox with three fruit in it - and it is what
   makes "does the kit look right" a question with an answer.

   The same split holds on the ImGui side: `dashboard.py --live` has a
   **Gallery** tab, which is the enumeration, and the dashboard page, which
   is the realistic use. Nothing belongs in both. A Buttons card showing six
   variants and eight sizes was on the dashboard page and had to come off:
   the Gallery already enumerates them, and a dashboard that enumerates its
   own controls is a gallery with worse framing.

4. **The demo is the dashboard.** Every state a component can be in has to
   be reachable there, not only in the gallery. The gallery is a contact
   sheet: it proves chrome to a pixel and tells you nothing about how a
   disabled control feels under the pointer. Three real bugs - the slider's
   stray format string, the discarded per-frame state, the invisible input
   text in light - were all invisible to the diff by construction.
5. **A test asks the source; it never copies a number.** Two tests held a
   `92.0` for a label column and went stale the moment the spacing moved.
   Where a pixel probe cannot tell two things apart - a tooltip floating
   over the card description behind it - count the thing instead of
   sampling it.

And the standing caution: **do not restyle Hyperspace to look like shadcn.**
What transfers is the method - scales, named tokens, measuring rather than
reasoning. The palette does not: the app is one red and three greys on
black, which is its own language and a deliberate one.

When something looks right but is not measured, it is usually wrong in a
way nobody will see until it ships. Build the oracle first.
