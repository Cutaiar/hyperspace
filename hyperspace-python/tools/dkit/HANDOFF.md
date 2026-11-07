# dkit — session handoff

Written at the end of the session that built ScrollArea, intrinsic sizing,
Button, ButtonGroup, ContextMenu and Combobox. `README.md` and `FINDINGS.md`
are accurate as the **Tier 1** record and still worth reading for the
calibration findings; this file is what changed after them, plus the
pitfalls and the process revisions, so a fresh session does not relearn any
of it.

Branch: `claude/magical-ritchie-fkh5e0`.

---

## Before anything else: fetch

```bash
git fetch origin && git status -sb
```

Not boilerplate. A cloud session's container clones the repo when it starts,
and its remote-tracking refs are frozen at that moment — so `git log --all`
means "every ref this clone happens to hold", not "every commit that
exists". The session that wrote rows 42-56 of `RETRO.md` opened by telling
the user that four of the files named in this very document did not exist,
with a table and a `git log --all` to prove it. The branch was
thirty-eight commits ahead. See RETRO row 54.

And while you are checking things that look settled: **every figure in this
file is a claim with a date on it.** Re-run the suite and the diff before
building on either. The line that said "733 passed, flat 0-2 levels" was
sitting above three cells failing at 26.

## Read in this order

> **[`RETRO.md`](RETRO.md) is the shortest useful thing here.** Fifty-six
> defects, each with what would have caught it. Read it before writing any
> code: the right-hand column is a list of checks, not a list of regrets.
>
> Rows 1-41 were nearly all found by a person looking at the running app
> while the pixel diff, the browser oracle and 700-odd tests all said it was
> fine. Rows 42-56 are the other shape, and worth reading as a pair with
> them: they were found by putting four finished components INTO the pixel
> diff, and most of them are faults in the measuring rig rather than in the
> kit — including a region excluded from the diff whose own geometry came
> from the code under test, so the hole followed the bug.


1. **`ROADMAP.md`** — what to build next and the constraints each component
   has to respect. The four rules at the end are the important part.
2. **This file** — current state, the traps, and how the work is organised.
3. **`README.md`** — how the rig works, and the calibration findings that
   cost a day each to discover (ImGui's stroke is not centred on the path;
   its font size is not a CSS px; three bindings reverse the C++ argument
   order; the browser snaps what it paints to whole pixels).
4. **`FINDINGS.md`** — the Tier 1 verdict.

A reasonable opening message for a new session:

> `git fetch` first — RETRO row 54, and it is why this sentence is here.
>
> Then read `hyperspace-python/tools/dkit/RETRO.md`, `ROADMAP.md` and
> `HANDOFF.md`. Branch `claude/magical-ritchie-fkh5e0`. Items 1 and 2 of the
> "Pick up here" list are done and `layer.py` exists; **start at item 3, the
> modularisation**, and do it in the order 3a → 3b → 3c written there. Run
> `test_module_surface.py` after every move — it is what lets the split be a
> move rather than a rewrite of 188 call sites. **Stop before 3d**: the
> 492-line `combobox()` is a behaviour refactor, not a move, and three RETRO
> rows describe bugs that live inside it.
>
> A pure move cannot change a pixel, so finish on the diff and expect "all
> cells within the bar". Re-run the suite and the diff before trusting any
> figure in these docs — the last session found three cells failing at 26
> levels under a line that said 0-2, and a skip is not a pass (row 56).

---

## Where it stands

```
815 passed, 51 skipped.   chrome diff: 64 cells, flat 0-2 levels, worst
corner 0.776 px, "all cells within the bar" in BOTH themes.
```

The skips are mostly `test_module_surface.py`, which parametrizes over every
file in the kit and skips the ones with no cross-module references. That is
the intended shape, but see RETRO row 56 before reading a skip as a pass.

One standing flake, not a failure: `test_gallery.py` crashes an xdist worker
(`node down: Not properly terminated`) on most runs — usually
`test_every_specimen_can_be_clicked`, sometimes
`test_every_specimen_survives_a_right_click` as well, which is what a shared
GL context looks like rather than two separate bugs. All ten pass with `-n0`:

```bash
xvfb-run -a uv run python -m pytest tools/dkit/test_gallery.py -q -n0
```

RETRO row 19 is the last time this bit, and it bit by being attributed to
someone else's work. Run it serially before believing it.

| | state |
|---|---|
| tokens, draw, box model, flex, interaction, popover placement, rounded clipping, pixel snapping, intrinsic sizing | done |
| **Tier 1** Slider, Switch, Input, Select, Tooltip + ScrollArea | done, in the pixel diff |
| **Button, ButtonGroup, ContextMenu, Combobox** | done, **in the pixel diff** — except the Combobox panel's ROWS |
| icons measured by mass + centroid, not only excluded | done (`contour.icon_ink`) |
| focus rings on every ringed control, measured per control | done |
| focus model (`:focus-visible`, one ring, no ImGui nav cursor) | done |
| `spec.json` checked against its three consumers | done (`test_spec.py`) |
| keyboard model (Combobox, menus, ContextMenu, Select) | done, measured per component |
| scroll (rate, momentum, whole pixels, monotone rounding) | done — see the decision record in `interact.py` |
| `comp_command.py` (cmdk scorer, verified, no UI yet) | parked for the Command palette |
| Toast, Kbd, Breadcrumb, Checkbox, Collapsible, Resizable | **not started** |
| `layer.py` (scrim, panels, focus trap, z-order) | done, measured, 20 tests |
| Dialog, Sheet on top of it | **not started — but no longer blocked** |
| variant resolver (cva) | not started, eight ad-hoc tables |
| text wrapping / multi-line measure | not started |
| **adoption** | **nothing imports the kit.** Unchanged since day one. |

## Pick up here — the list, verified rather than remembered

Each line was re-checked against the tree, not recalled. The command that
proves it is next to it.

**Items 1 and 2 are DONE** — see the five commits ending
`dkit: the focus-ring audit`, and rows 42-56 of `RETRO.md` for what doing
them found. Both are left here in summary because what they turned up
changes how to read the rest of this list.

### Done, and what it cost

**1. ~~Four components are outside the pixel diff.~~** All four are in it
now: 16 Button cells, 2 ButtonGroup, 1 ContextMenu panel, 2 Combobox
triggers, light and dark.

```bash
python3 -c "import json,collections;s=json.load(open('tools/dkit/spec.json'));print(collections.Counter(c['kind'] for c in s['cells']))"
```

It found two real bugs in the Combobox trigger inside ten minutes — a
chevron at half the browser's ink strength and 3px out of place — plus the
fact that **`icon_boxes` dropped every icon out of every metric** while
promising the opposite, so neither bug could have been caught by the cell
that found them until `contour.icon_ink` existed. Read RETRO row 44 before
excluding anything else from the diff.

The one piece left: **the Combobox panel's ROWS**. Its panel CHROME is
covered — `comp_combobox._panel_chrome` delegates to `menu.panel_chrome`
now, so `menu.panel` and `contextmenu.panel` measure it as the same code
rather than as a claim — but the rows (the highlight fill, the check
indicator's inset, the group heading, the separator) are not. Doing it needs
a `chrome_only` path through `_row` and the row loop, the way `menu.rows`
has one; the loop currently runs inside `I.scroll_area`, which needs a
window, so that is the knot to untie.

**2. ~~The cross-library audit is HALF DONE.~~** Done, and the list was
wrong in three places, each worth knowing:

* `gallery.py` holds `interact.chrome()` now, but the symptom it was listed
  for cannot occur there: the gallery submits no widgets, and the capture is
  byte-identical with it in place. It is defence for a future cell.
* **The six ringless controls are not one model.** Measured per control:
  a TabsTrigger has Button's band PLUS a 1px solid outline at full `ring`; a
  SidebarMenuButton rings at **2px, full opacity**, with no border change; a
  TableRow **is not focusable at all** and correctly keeps no ring;
  `interact.button` had no callers and is deleted. Porting Button's ring
  would have been wrong three different ways.
* The "three hand-eased focus values" are **one**. `comp_button` duplicated
  `focus_f`'s predicate and now calls it; `interact.text_input` and the
  Combobox field are the measured Input exception — a text field rings from
  a POINTER click too — and routing them through `focus_f` would have been a
  regression. `focus_f`'s own docstring says so.

And it uncovered the biggest thing in the batch: **`is_item_hovered()` is
True for a merely nav-focused `invisible_button`**, so every control reading
`State.hot` was lighting its hover tint off the keyboard. RETRO row 49.

### Still to do

**3. Modularisation.** Mostly mechanical, with one part that is not, and
the two are worth keeping apart — see 3d.

```bash
wc -l tools/dkit/*.py | sort -rn | head -8
```

### Before you touch any of it

There are **~190 `B.x` / `I.x` / `C.x` references across seventeen files**, so
every module that gets split has to stay behind as a FACADE that re-exports.
Rewriting the call sites is not the task; it is churn with a risk of its own,
and it would make the diff unreviewable.

```bash
grep -rhoE "\bB\.[a-zA-Z_]+|\bI\.[a-zA-Z_]+" --include=*.py tools/dkit/ | wc -l
```

`test_module_surface.py` is the guardrail, and it is the thing to run after
every move:

```bash
xvfb-run -a uv run python -m pytest tools/dkit/test_module_surface.py -q -n0
```

It reads every `alias.attr` and every `from <kit module> import name` in the
tree and asserts each resolves, so an incomplete facade fails naming the
attribute, the file and the line. That is the one failure mode a
move-and-re-export does NOT get for free: `import` succeeds, the module
loads, and the AttributeError waits for whichever code path uses the name.
It is derived from the call sites rather than being a snapshot, so it cannot
go stale and there is no list to maintain.

Two things it already tells you:

* `comp_command.py` does `from comp_combobox import Item, _is_row, _k,
  heading, sep` — **two PRIVATE names cross a module boundary.** They are
  pinned in `test_the_private_names_that_cross_a_module_boundary_are_known`
  as a ledger, not a prohibition: move one and update the list and the
  importer together.
* a module-level alias can be SHADOWED locally — `test_components.py` has
  `import draw as D` at the top and `D = _dashboard()` inside a test — so the
  scanner is scope-aware. If you extend it, keep that; the first version
  reported two dangling references on a module that was fine.

### 3a. `box.py` (616) → three layers. No cycles, so this is the easy one.

Measured with an AST walk of who references whom, not by reading it:

| group | names | lines |
|---|---|---|
| **rect** — nothing depends on anything | `Rect`, `place_popover`, `card_body`, `slider_geom`, `switch_geom`, `scroll_thumb` | ~220 |
| **flex** — needs `Rect` | `_Cell`, `Flow`, `Item`, `_dist`, `flex`, `stack` | ~150 |
| **tree** — needs `Rect`, `Item`, `flex` | `AUTO`, `Node`, `_pad_wh`, `measure_tree`, `place_tree`, `lay`, `lay_auto`, `wants` | ~130 |

So `rect.py` ← `flex.py` ← `tree.py`, strictly one direction, and `box.py`
becomes `from rect import *` etc. with an explicit `__all__`.

```bash
xvfb-run -a uv run python -m pytest tools/dkit/test_box.py tools/dkit/test_flex.py tools/dkit/test_nest.py -q -n0
```

### 3b. `interact.py` (1130) → pull two pieces out, keep the primitives.

**`wheel.py` first — it is the safest extraction in the kit.** Seven names
with **zero** references to anything else in the module:

`_PRECISE`, `_WHEEL`, `wheel_px_per_unit`, `snap_scroll`, `note_wheel_step`,
`scale_wheel`, `install_wheel` (L518–620, ~105 lines).

It is also the part with the most measurement behind it per line — the 10 px
per unit, the 0.1 scale factor, the monotone rounding — so having it in a
file of its own is worth more than the line count suggests. `scroll_area` is
its only in-module caller (`snap_scroll`).

**Then `ui.py`:** `State` (8), `Ui` (182), `chrome` (24), `_sandwich_begin`
(22), `_sandwich_end` (3) — ~240 lines, and everything else in the module
depends on it.

What is left in `interact.py` is the primitives, which is a coherent file:
`sidebar_item`, `tabs`, `row`, `_ghost_ring`, `icon_button`, `row_action`,
`slider`, `switch`, `text_input`, `select`, `tooltip`, `range_slider`,
`scroll_area`, `scrolled`. Do not split it further on line count alone —
they share `_sandwich_*` and the measured focus model, and there is no second
seam as clean as the first two.

```bash
grep -rn "install_wheel\|snap_scroll\|wheel_px_per_unit" --include=*.py tools/dkit/ | grep -v "^tools/dkit/interact.py"
```

### 3c. `comp_combobox.py` (1703) → extract the PURE parts.

Four groups that are already pure functions with their own tests, and that
nothing about the widget's lifecycle touches:

| group | names | lines |
|---|---|---|
| tokens | `COMBOBOX` (216 lines of table on its own), `COMBOBOX_DARK`, `combobox_table` | ~230 |
| the selection model | `SEL_FIRST/LAST/NONE`, `SENTINELS`, `_Cleared`, `CLEARED`, `_MISSING`, `_committed_row`, `resolve_open` | ~100 |
| items and filtering | `Item`, `heading`, `sep`, `_k`, `_is_row`, `_SPACE`, `_fold`, `filter_items` | ~110 |
| measure | `_rows_node`, `combobox_size`, `list_content_h` | ~95 |

That is ~535 lines out, all of it covered by `test_combobox.py` and
`test_combobox_keys.py` already, and it takes the file under 1200 without
touching a line of behaviour. **Mind the ledger**: `_is_row` and `_k` go
with the items group and `comp_command.py` imports both.

### 3d. The part that is NOT mechanical, and should not be done in the same sitting

**`combobox()` is 492 lines in one function** and references 24 other
top-level names. That — not the file length — is the real problem, and it is
a behaviour refactor, not a move:

```bash
uv run python -c "import ast;t=ast.parse(open('tools/dkit/comp_combobox.py').read());f=[n for n in t.body if getattr(n,'name','')=='combobox'][0];print(f.end_lineno-f.lineno+1,'lines')"
```

Three traps are recorded in `RETRO.md` and all three live inside that
function, so splitting it badly reintroduces them:

* **row 40** — `armed` gates the MOVEMENT keys and not the activation keys,
  and the activation handler must run LAST in the frame. An extraction that
  reorders the key phases will reopen it.
* **row 26** — `resolve_open`: the committed value beats the gesture, and the
  gesture is only the fallback. It is the valued half of the table that was
  missed the first time.
* **rows 17/18/25** — the field is drawn TWICE, once in the parent window for
  the chrome and once in the popup for the caret, and exactly one of them may
  paint the glyphs. The `ink` flag is the whole of that; a split that gives
  each copy its own code path will double the ink again, measurably (255
  against a `foreground` of 250).

If you do take it on: extract by PHASE, not by line count — resolve the open
gesture, filter, place the panel, run the keyboard, draw the rows, commit —
and make each phase take and return explicit state rather than closing over
it. Then re-run the driven keyboard tests, which are the only thing that can
tell you whether the order survived:

```bash
xvfb-run -a uv run python -m pytest tools/dkit/test_combobox_keys.py tools/dkit/test_menu_keys.py -q -n0
```

### The tests that will break on a pure move, and should

Five assertions in the suite grep SOURCE TEXT rather than call anything, and
they will fail on a move that changes nothing about behaviour. They are not
mistakes — each exists because a unit test passed while the wiring was a
no-op (RETRO row 32: the wheel's px-per-unit was being read at a point in the
frame where it is always zero, and its unit test passed because it was handed
a fake `io`). So they assert that a call site EXISTS.

```bash
grep -rn "in src\b" --include=test_*.py tools/dkit/ | grep -v command_score
```

| where | asserts | breaks if |
|---|---|---|
| `test_components.py:809` | `"I.install_wheel("` appears in `dashboard.py` | `wheel.py` is introduced and the dashboard calls it under a different alias |
| `test_components.py:811` | `io.mouse_wheel` does NOT appear in `dashboard.py` | — (a guard, keep it) |
|  `test_components.py:814` | `I.note_wheel_step()` appears at least twice | the frame loops are touched |
| `test_components.py:917` | `interact.scroll_area`'s own source contains `snap_scroll(imgui.get_scroll_y())` | `scroll_area` reaches `snap_scroll` through a new module alias |
| `test_combobox.py:860-862` | `menu.panel_chrome`'s source draws `popover`, `foreground/10`, `RADII["lg"]` | that function moves or is rewritten |

**Update them as part of the move, not afterwards.** The temptation is to
loosen them to something alias-agnostic; do not, without replacing the thing
they protect. What they are really checking is that the knob is connected,
and the cheapest honest version of that is still a grep.

### One thing to fold in while moving code

The scrollbar's TRACK geometry is worked out twice over, from different
arguments. `draw.scroll_bar` takes a region's root rect and insets by its
border; `contour.icon_boxes` rebuilds the same track by hand from a cell.
They agreed by luck, which is the only reason the icon boxes sat over the
browser's thumb while `gallery.py`'s own call to `scroll_bar` was passing it
the wrong rect (RETRO row 45). One function should answer "where is the
thumb" from one set of inputs.

```bash
grep -rn "scroll_thumb(" --include=*.py tools/dkit/ | grep -v "def \|test_"
```

### How to know you have not broken anything

In this order, because the cheap ones fail faster:

```bash
xvfb-run -a uv run python -m pytest tools/dkit/test_module_surface.py -q -n0
```

```bash
xvfb-run -a uv run python -m pytest tools/dkit -q
```

```bash
cd ../prototypes/dashboard && npm run build && npx vite preview --port 4173 &
```

```bash
node tools/dkit/capture_react.js "http://localhost:4173/?gallery" /tmp/d &&   HYPERSPACE_HOME=$(mktemp -d) xvfb-run -a uv run python tools/dkit/gallery.py --out /tmp/d &&   xvfb-run -a uv run python tools/dkit/diff.py /tmp/d
```

The diff should still say **"all cells within the bar"** with a worst
flat-region delta of 2 levels. A pure move cannot change a pixel, so if it
does, something was not a move.

**4. Then coverage**: Dialog, Sheet, Toast, Kbd, Breadcrumb, Checkbox.
Checkbox is 47 toggle params and the cheapest of them.

**5. And the one that decides it all**: port one real `ui_pane.py` section.
Nothing imports the kit. Until that happens the hypothesis is untested in
the only place that matters.

```bash
grep -rn "tools.dkit\|from dkit\|import dkit" --include=*.py hyperspace/ tests/ | head
```

### Two smaller things, both recorded in code

`menu.popup` has no scroll area or height clamp, so a long menu cannot
scroll to follow its keyboard highlight — measured on the real one, noted in
`menu.py`. And a Select's closed typeahead (a letter sets the value without
opening) has nowhere to live until `interact.select` reads characters.

### One more, new

`?probe` now carries `tabs.list`, `sidebar.menubutton` and `table.row`, and
`probe_react.js` focuses each with a real keyboard focus to measure its
ring. The Tabs and sidebar CHROME is still not in the pixel diff — only
their rings are driven, by `test_interaction.py`. Cells for them are cheap
now that the pattern is established, and the TabsList's `muted` ground plus
the active trigger's `shadow-sm` are the two things worth having measured.

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
that pass), `?gallery`, `?gallery&text`, `?gallery&dark`.

Two things `probe_react.js` now does that are easy to undo by accident: it
opens the ContextMenu (by dispatching `contextmenu`, because `?probe` also
carries an open Combobox whose portal intercepts a real right-click) and
closes it again straight after the static walk — an open Radix ContextMenu
is a modal layer and every hover measurement below it times out. And
`capture_react.js` sizes its viewport from `spec.canvas`, not a constant:
a portalled panel anchored to a POINTER does not reposition when Playwright
scrolls to shoot, so a canvas taller than the viewport put the ContextMenu
panel in the corner of the page.

---

## One standing caveat

**Every number in these docs was measured on Mesa/llvmpipe under Xvfb.** On
a Mac (Metal) the 0.776 px corner figure will move; straight edges and fills
should hold. Re-baseline on the Mac rather than treating a change as a
regression — `tests/test_golden_frames.py:336` gates the render goldens on
`GL_RENDERER` for exactly this reason.
