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

> **[`RETRO.md`](RETRO.md) is the shortest useful thing here.** Forty-one
> defects, each with what would have caught it. Nearly all were found by a
> person looking at the running app while the pixel diff, the browser oracle
> and 700-odd tests all said it was fine. Read it before writing any code:
> the right-hand column is a list of checks, not a list of regrets.


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
> `HANDOFF.md`. Branch `claude/magical-ritchie-fkh5e0`. Work the "Pick up
> here" list in HANDOFF in order — it is verified against the tree and each
> item carries the command that proves it. Use the oracle-first method:
> `refresh_shadcn.sh`, then measure the real component on `?probe`, then
> match it, then diff on `?gallery`. Do not implement from a reading of the
> spec, and verify every new test against the broken code it covers.

---

## Where it stands

```
733 passed, 16 skipped.   chrome diff: flat 0-2 levels, worst corner 0.776 px.
```

| | state |
|---|---|
| tokens, draw, box model, flex, interaction, popover placement, rounded clipping, pixel snapping, intrinsic sizing | done |
| **Tier 1** Slider, Switch, Input, Select, Tooltip + ScrollArea | done, in the pixel diff |
| **Button, ButtonGroup, ContextMenu, Combobox** | done, **NOT in the pixel diff** |
| focus model (`:focus-visible`, one ring, no ImGui nav cursor) | done |
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

**1. Four components are outside the pixel diff.** `spec.json` holds badge,
card, input, menu, scroll, select, slider, switch, text, tooltip. Button,
ButtonGroup, ContextMenu and Combobox are verified by unit tests and by eye
only — which is exactly the standard that produced most of `RETRO.md`. They
need `?gallery` cells, spec rects and a diff run.

**2. The cross-library audit is HALF DONE.** The menu keyboard slice landed;
these three did not:

```bash
grep -rln "I.chrome(" --include=*.py .     # -> dashboard.py, test_interaction.py only
```
`gallery.py` does not hold `interact.chrome()`, so anything drawn there
still gets ImGui's blue nav cursor and its pale text selection.

```bash
for fn in button sidebar_item tabs row icon_button row_action; do ... done
```
Six controls in `interact.py` draw **no focus ring at all**: `button` (the
old stub), `sidebar_item`, `tabs`, `row`, `icon_button`, `row_action`. The
model is settled and uniform — `draw.ring`, `ui.focus_f`, `:focus-visible`
only — so this is applying it, not deciding it. Measure the real Tabs
trigger and sidebar button first; do not assume they match Button.

```bash
grep -rn 'anim.to(f"{key}:focus"' --include=*.py .
```
`comp_button.py`, `comp_combobox.py` and `interact.py` ease focus by hand
instead of going through `ui.focus_f`, which exists for it.

**3. Modularisation, which is mechanical and worth doing in one sitting.**
`box.py` (616) holds three separable things: the `Rect` algebra and cuts,
the flex solver, and the intrinsic-sizing tree. `interact.py` (1036) holds
both the `Ui` object and every primitive. `layer.py` does not exist and
Dialog and Sheet both need it — a scrim, a focus trap, z-order and
click-outside. Do `layer.py` BEFORE those two components, not after.

**4. Then coverage**: Dialog, Sheet, Toast, Kbd, Breadcrumb, Checkbox.

**5. And the one that decides it all**: port one real `ui_pane.py` section.
Nothing imports the kit. Until that happens the hypothesis is untested in
the only place that matters.

### Two smaller things, both recorded in code

`menu.popup` has no scroll area or height clamp, so a long menu cannot
scroll to follow its keyboard highlight — measured on the real one, noted in
`menu.py`. And a Select's closed typeahead (a letter sets the value without
opening) has nowhere to live until `interact.select` reads characters.

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
