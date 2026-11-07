# dkit — session handoff

Written at the end of the session that built ScrollArea, intrinsic sizing,
Button, ButtonGroup, ContextMenu and Combobox. `README.md` and `FINDINGS.md`
are accurate as the **Tier 1** record and still worth reading for the
calibration findings; this file is what changed after them, plus the
pitfalls and the process revisions, so a fresh session does not relearn any
of it.

Branch: `claude/magical-ritchie-fkh5e0`.

---

## Read in this order

> **[`RETRO.md`](RETRO.md) is the shortest useful thing here.** Fifty-three
> defects, each with what would have caught it. Read it before writing any
> code: the right-hand column is a list of checks, not a list of regrets.
>
> Rows 1-41 were nearly all found by a person looking at the running app
> while the pixel diff, the browser oracle and 700-odd tests all said it was
> fine. Rows 42-53 are the other shape, and worth reading as a pair with
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

> Read `hyperspace-python/tools/dkit/RETRO.md` first, then `ROADMAP.md` and
> `HANDOFF.md`. Branch `claude/magical-ritchie-fkh5e0`. Items 1 and 2 of the
> "Pick up here" list are done; start at 3, which is `layer.py` and the
> modularisation, because Dialog and Sheet are both blocked on it. Use the
> oracle-first method: `refresh_shadcn.sh`, then measure the real component
> on `?probe`, then match it, then diff on `?gallery`. Do not implement from
> a reading of the spec, and verify every new test against the broken code
> it covers. Re-run the suite and the diff before trusting any figure in
> these docs — the last session found three cells failing at 26 levels under
> a line that said 0-2.

---

## Where it stands

```
751 passed, 16 skipped.   chrome diff: 64 cells, flat 0-2 levels, worst
corner 0.776 px, "all cells within the bar" in BOTH themes.
```

One standing flake, not a failure: `test_gallery.py::test_every_specimen_can_be_clicked`
crashes its xdist worker (`node down: Not properly terminated`) roughly every
run and passes on its own with `-n0`. It boots a GL context per module; RETRO
row 19 is the last time that bit. Run `-n0` before believing it.

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
| Dialog, Sheet, Toast, Kbd, Breadcrumb, Checkbox, Collapsible, Resizable | **not started** |
| `layer.py` (scrim, focus trap, z-order) | **not started — blocks Dialog and Sheet** |
| variant resolver (cva) | not started, eight ad-hoc tables |
| text wrapping / multi-line measure | not started |
| **adoption** | **nothing imports the kit.** Unchanged since day one. |

## Pick up here — the list, verified rather than remembered

Each line was re-checked against the tree, not recalled. The command that
proves it is next to it.

**Items 1 and 2 are DONE** — see the five commits ending
`dkit: the focus-ring audit`, and rows 42-53 of `RETRO.md` for what doing
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

**3. Modularisation, which is mechanical and worth doing in one sitting.**

```bash
wc -l tools/dkit/box.py tools/dkit/interact.py tools/dkit/comp_combobox.py
```

`box.py` (616) holds three separable things: the `Rect` algebra and cuts,
the flex solver, and the intrinsic-sizing tree. `interact.py` (~1100) holds
both the `Ui` object and every primitive. `comp_combobox.py` (~1700) is the
largest file in the kit and holds the keyboard model, the filter, the panel
and the trigger.

`layer.py` does not exist and Dialog and Sheet both need it — a scrim, a
focus trap, z-order and click-outside. **Do `layer.py` BEFORE those two
components, not after.**

```bash
ls tools/dkit/layer.py          # -> No such file
```

One thing to fold in while moving code: the scrollbar's TRACK geometry is
worked out twice over, from different arguments. `draw.scroll_bar` takes a
region's root rect and insets by its border; `contour.icon_boxes` rebuilds
the same track by hand from a cell. They agreed by luck, which is the only
reason the icon boxes sat over the browser's thumb while `gallery.py`'s own
call to `scroll_bar` was passing it the wrong rect (RETRO row 45). One
function should answer "where is the thumb" from one set of inputs.

```bash
grep -rn "scroll_thumb(" --include=*.py tools/dkit/ | grep -v "def \|test_"
```

```bash
grep -rn "scroll_thumb(" --include=*.py tools/dkit/ | grep -v "def "
```

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
