# Plan 23 — session launch prompt

You are running Plan 23 in `Cutaiar/hyperspace`: three small work packages
the owner needs before the event, then a review pass and a docs WP. Work
the way Plans 21 and 22 were worked: numbered work packages, one branch
and PR each, an integration branch, a review pass, and a docs WP that
records what was built.

**The plan is [`23-flip-windows-tabs.md`](23-flip-windows-tabs.md).**
Read it first and in full: it holds the problem, the owner's decisions,
the code sites (file and line, checked against `1d7a293`) and the
acceptance criteria for each WP. This prompt does not repeat them.

Then read `hyperspace-python/docs/CHECKPOINT.md`, `ARCHITECTURE.md`,
`DECISIONS.md`, `DECISION-REGISTER.md` and `docs/plans/README.md`, and
`docs/plans/21-outputs-and-the-hands.md` as the model for the as-built
docs.

## The base

Plan 22 is on `plan-22-integration`, PR #151, which may not be merged
yet. Plan 23 builds on it: it touches `ui.py`, `ui_desk.py` and tests
that plan 22 changed.

- **If #151 is merged:** base on `main`, and the final PR targets `main`.
- **If it is not:** base on `plan-22-integration` (at `1d7a293` or later),
  and the final PR targets `plan-22-integration`, so its diff is plan 23
  alone. Say so in the PR body.

Check which applies before anything else, and re-check it immediately
before each branch is cut.

---

## The work packages

| WP | What | Mostly touches |
| --- | --- | --- |
| **WP1** | Flip X / Flip Y per output, at the output stage | `outputs.py`, `render.py` (`SHOW_FS`, `_show`, `_compose`), `ghost.py` (`COMPOSITE_FS`, `_lay`), `overlay.py`, `config.py`, `app.py` (`_slots`, `Mouse`), `ui.py` (OUTPUT page) |
| **WP2** | Windows that come back: screen-relative rects by name, fullscreen remembered, control window fills the MacBook, `imgui.ini` in the home | `placement.py`, `app.py` (window opening, `save_windows`), `config.py` (absent vs. set) |
| **WP3** | The page tabs across the top; the panel pinned to the right half | `ui.py` (`_draw`, `_rail` → a top bar, `PANEL_W`), `ui_desk.py` (`_room`), the UI tests |

Branches `plan-23-wp1-flip`, `plan-23-wp2-windows`, `plan-23-wp3-tabs`,
then `plan-23-wp4-docs`. Integration branch `plan-23-integration`.

**Sequencing.** WP1 is independent. WP2 and WP3 both shape the control
window: WP2 decides its size, WP3 what is inside it. Run WP1 and WP2 in
parallel, and WP3 after WP2 merges into integration, so WP3 lays out against
the real default size. Expect small `app.py` and `config.py` overlaps
between WP1 and WP2 (both add config keys and touch the launch path).
Resolve them at integration, never by one WP reverting the other's lines.
WP4 (docs) last.

You may run the WPs with sub-agents (one per WP, each in its own git
worktree off the verified base) or do them yourself in sequence. They are
small, and either is fine. If you use sub-agents, the failure that silently
ruins this workflow is an agent on a stale base whose diff quietly reverts
a sibling's work. Verify the base, don't assume it.

---

## Decisions already made — do not relitigate

All the owner's, 2026-10-07:

1. **The flip is at the output, not on the hands.** Per output,
   `output.N.flip_x` / `flip_y`, launch values from the config's
   `[[output.screens]]` / `[output]` entry, toggles on the OUTPUT page.
   Rig settings: never in a preset, show or undo step. `ghost.mirror`
   stays as it is (its tooltip changes).
2. **Fullscreen is remembered.** This overturns register row 48. A key
   the config sets still wins; a key it leaves out defers to
   `windows.json`.
3. **The control panel is pinned to the right half**, not draggable, with
   a floor width. The desk takes the left.
4. **The tabs go across the top** and may wrap to a second row.

When the docs WP records these, they go into `DECISIONS.md` with **Who**
= `owner`. Row 48 is answered: per `DECISION-REGISTER.md`'s own rule
("overturn → the change, then the same"), delete row 48 from the
register and its answer sheet, and rewrite the `placement.py` row of
`DECISIONS.md` (currently "Fullscreen is never remembered … row 48") to
say what is now true, Who `owner`.

## Decisions you may make yourself

Anything the plan leaves open, for example the uniform's shape, the floor
width, the pill padding, the duplicate-screen-name rule, and how a `/1`
`windows.json` migrates. When you take your own recommendation and build
it, append a row to `docs/DECISION-REGISTER.md` starting at **row 109**
(rows 34–108 exist), in that file's format: what was built and what the
owner will see or feel, the other option(s), the cost to reverse, the
known rough edge, and the hand check that lets the owner judge it. Mark
the matching `DECISIONS.md` row's **Who** as `row N`. Never mark a row
`owner` yourself, except the four above.

## Out of scope

Everything under "Not in this plan" in the plan file. Also: anything in
the hands package, routing, presets, the shapes or the patterns. If a WP
needs to change one of those, stop and say why in the report rather than
doing it.

---

## Gates — all green before any PR

```
uv run pytest -q
uv run ruff check .
HYPERSPACE_FRAMES=120 uv run hyperspace     # windowed smoke run
```

Run the smoke run once with a flip on (set `flip_y = true` in a scratch
config) and once with no `windows.json` in a scratch home, so the new
paths actually run. **Never touch the owner's real `~/Hyperspace`.** Point
the home at a temporary folder the way the tests do.

These boundary tests must keep passing untouched:

- `tests/test_hands_boundary.py`
- `tests/test_routing_boundary.py`
- `tests/test_render.py::test_the_render_stack_imports_no_registry`. The
  flip reaches the renderer as `Switches` fields in a `View`, never as a
  param.
- `tests/test_app_boundary.py::test_importing_app_leaves_every_gated_adapter_unimported`
  and `::test_the_frame_runs_in_the_documented_order`.

Also hold these invariants: the render stack reads parameters and never
writes one; with both flips off every output is bit-identical to today;
nothing in placement can open a window off every screen.

## Review pass

Before the final PR, review `plan-23-integration` as a whole and commit
fixes as `Review: <what was fixed>`, as Plans 21 and 22 did. Look hard at
three things:

- **Hands flipped twice.** Check hands-through with an effect on, and an
  output flip together with `ghost.mirror`.
- **The flip on output 2+.** The `Presenter` path has its own shader and
  its own handoff. Make sure it isn't only output 1 that flips.
- **A launch that strands a window.** Check a renamed screen, an unplugged
  screen, a `/1` file, a config `monitor` index that no longer exists, and
  fullscreen remembered on a screen that is now gone.

**Re-measure on the merged branch.** A sub-agent's green run inside its own
worktree does not survive integration. Re-run the gates on
`plan-23-integration` itself before claiming anything.

## What the docs WP must produce

- `docs/plans/23-flip-windows-tabs.md`: rewritten **as built** (what was
  built, what no person has verified, known rough edges), in the shape of
  `21-outputs-and-the-hands.md`. Keep this prompt file.
- `docs/plans/README.md`: both entries updated, this prompt's to "the
  launch prompt plan 23 was run from", as 22's is.
- `docs/ARCHITECTURE.md` and **`docs/ARCHITECTURE.html`** together, if
  the output stage's passes, the control window's layout or placement's
  rules are drawn or described there (they are: check the outputs figure
  and the windows text). Update the counts in the HTML's masthead and
  closing stat row. Keep SVG colours in CSS classes, never `var()` in
  presentation attributes, and keep the light and dark tokens in step.
- `docs/ENGINEERING.md`: the flip (where it applies, where it must not),
  `windows.json` `/2`, the config/file precedence, the panel layout.
- `docs/DECISIONS.md` and `docs/DECISION-REGISTER.md`: as above (row 48
  removed, rows from 109).
- `docs/plans/11-hand-checks.md`: a new group **S** (A–R exist), checks
  numbered from **139** (1–138 exist), in the existing format: bold number
  and title, the headless tests behind it, the setup, then *Pass:* and
  *Fail:*, with the failure pointing at the likely cause. At least:
  - flip at the glass, each axis
  - flip on the projector output alone
  - the mouse on a flipped render window
  - relaunch with nothing dragged
  - relaunch after changing the primary display
  - remembered fullscreen
  - the first-launch half-and-half layout
  - every page at half width on the MacBook
  - `imgui.ini` no longer depending on the launch folder
- `docs/TESTING-GUIDE.md`: the same checks in plain words, by hardware,
  each ending with its check numbers. These are pre-event checks, so put
  them where the owner will find them first.
- `docs/CHECKPOINT.md`: kept short and current.

## Report back

When the PR is open, report:

- What landed per WP, with the PR links.
- **Which axis to flip for the glass.** You cannot know this. Say that
  it is hand check 139 and the one thing to do first at the rig.
- The register rows you opened (109–N), each with what it needs from the
  owner.
- The new hand check numbers (group S).
- Anything you deliberately left undone, and anything you found that
  contradicts this prompt or the plan, including in the docs. If a
  document says something the code does not do, say so rather than
  quietly matching it.
