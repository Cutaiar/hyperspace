# Roadmap — plans 15 to 21: from the Oct 3–4 session to the finish line

**Written 2026-10-04 on main fa9b3a1 (1003 tests); revised the same day
with the owner's answers (§7).** Source: the review of the Oct 3–4 session
at the machine (Dan and Dillon, 1h44m transcript, read against main), a
code sweep of the twelve areas it names, and the owner's answers. This
file orders the work and scopes each plan. It is not the plans: each plan
document (`15-…md` to `21-…md`) is written against the code as it stands
when that plan starts, by the session that runs
[`docs/prompts/plans-15-21-orchestrator.md`](../prompts/plans-15-21-orchestrator.md).

## 1. The constraints on everything below

- **"We don't want to drown in the number of parameters."** Said in the
  session; it bounds the whole list. A work package that adds a param, a
  menu item or a page says which one it replaces, or why none. Prefer a
  better default, a label, or an existing concept (a macro, a route's
  depth, the show's "starts on") over a new knob.
- **Undo was called "absolutely the most important thing."** It is first,
  and it reaches single parameter edits: that is how good presets get
  found.
- **No timetable.** The owner, 2026-10-04: the software is needed by
  Friday 2026-10-09, and the work is not to be planned around dates. The
  order below is by what matters, and it holds if time runs out.
- **The run is unattended and never touches main.** Everything lands on
  one branch, `finish-line`, plan by plan. The owner runs that branch at
  the machine and merges it when happy.
- **The control model stands** (ARCHITECTURE §3) and so does every
  DECISIONS row the owner has not changed in §7.
- **Never touch the owner's real `~/Hyperspace`.** The presets saved that
  night live there. Every agent runs with `HYPERSPACE_HOME` pointed at a
  temp folder.

## 2. What the session got wrong about the system (do not build these)

| Asked for | What is true on main | So |
|---|---|---|
| Un-hard-code the F1–F8 presets | They are eight pointers in the show file; ⇧F1–F8 or ⇧click overwrites one | Nothing to un-hard-code. The gaps are a save-as on the desk (plan 15 WP4) and more than eight slots (plan 19) |
| Decide how module presets compose | Decided: a preset stores each module preset's name as a label and never loads it (D3) | Nothing to build |
| Add dream layer selection | `dream.layer` exists, four layers | Surface it better (plan 20) |
| Rename echo "Spacing" to "complexity" | It is the time between echoes (`dream.gap`) | Rename only to something that says so (plan 20) |
| Git-diffable preset files | Already one plain JSON per preset, one row per line | The gap is that `~/Hyperspace` is not in git (plan 19) |
| Lower hand "sensitivity", tame rotation | There is no sensitivity param. A hand learn writes a full-range `position` row at depth 1; on a rotation or speed param that is a lot. Rate-type params under a hand are fine (the owner, 2026-10-04) | Fix the default a learn lands with, and the box (plan 18) |
| Dimming on the crossfader "in shift mode" | Faders mean one thing on both layers (D6). The crossfader's job today, the overlay ground, is inert since decision 21 | The crossfader is master dim on both layers (plan 15 WP3, decision 28) |

## 3. Sequence

| Order | Plan | What | Size |
|---|---|---|---|
| 0 | **PR #78 into `finish-line`** | Dillon's ghost hands (off by default) merged first, because it touches `render.py`, `params.py`, `hands/core.py` and the document tables every later plan edits | one merge, suite green |
| 1 | **15 — Safety net and the bank** | Undo down to single edits, home, master dim, save-as from the APC40 | 4 WPs; undo M–L, the rest S–M |
| 2 | **16 — Paper cuts** | Small fixes with no design fork: cheat sheet off, FX chip and stack selection, window placement, instances to zero | 5 WPs, S each |
| 3 | **17 — Learn, unbind and seeing the desk** | One Unbind, a hand learn and a desk learn that cannot be confused, Learn on the controls that lack it, a bigger diagram you can click, a ROUTING filter | 5 WPs, S–M |
| 3 | **18 — Hand and knob feel** | An interaction box, a learn's default depth and op, knob smoothing | 4 WPs, S–M; beside 17 |
| 4 | **19 — Presets and the desk layout** | Twenty-four presets on the desk, hiding the presets nobody wants, rename, the trash, the home in git, the factory preset layer re-cut toward knobs | 6 WPs, S–M, one L |
| 4 | **20 — FX, dream and looks** | The faces as their own effect target, a chain view with safe reorder, the look-back page split into echoes and dream, instance layouts | 5 WPs, S–M, one L; beside 19 |
| 5 | **21 — Outputs and the hands** | Two render outputs (Pepper's Ghost, projector), each with its own dim and its own switches for the scene and the hands; the ghost hands polished; other things to draw in place of hands | 3 WPs, M–L |

Why this order: 15 is what makes a mistake recoverable and a preset
findable. 16 is fixes that were each hit that night and need no decision.
17 comes before 19 because mapping was where the session lost the most
time and because 19's desk re-cut is easier to get right once the diagram
is clickable. 18 runs beside 17 because its code is `hands/` and
`midi.py`, not `learn.py` and the UI. 21 is last because it is the only
new architecture.

**PR shape** (decision 30): one PR per work package, small, each with a
demo (a screenshot or a headless script and its output) in the PR body;
the WP PRs of one plan stack on a `plan-NN-integration` branch, which is
merged into `finish-line` when it is green and reviewed. One draft PR,
`finish-line` → main, is the owner's single thing to merge; its body is
the run's status. Each of plan 15's four features is its own merge commit,
so one `git revert -m 1` takes exactly one feature out.

## 4. The plans

Sizes: S = under half a day of agent time, M = a day, L = more. "Owns" is
the file set a work package may edit; the plan document tightens it.

### Plan 15 — Safety net and the bank

*As built:* [`15-safety-net.md`](15-safety-net.md) §8 (PRs #81–#83 and
after); where it differs from the rows below, that section is the code.

| WP | What | Scope | Owns | Size |
|---|---|---|---|---|
| 1 | **Undo** | One bounded in-memory stack; **a step is one gesture**: a slider drag, a knob turn on the desk, a typed value, a toggle, a ROUTING field edit, or one replacing action (a preset or show load from any road, a Learn landing, an Unbind, a route or macro delete, Replace in the Replace / Keep prompt, a module-preset load or reset, an FX reorder). It needs no write hook: once a frame the undo compares a cheap fingerprint of every param's **base** and of the routes, desk layer and macros. A performer writes an offset, never the base, so a hand, a band or an LFO moving makes no step. When the fingerprint changes, the last settled state is pushed; changes that keep arriving within about 0.4 s are the same step. Params that are integrated state (rotation angles, clocks, anything `ViewState.integrate` writes) are left out of the fingerprint; the plan lists them from the code. Ctrl+Z puts back only what differs between the step and now (bases through `Param.set`, changed rows through the table's own calls), so undoing one slider does not re-run a load: the desk layer, fader pickup and LFO phases stay put. Ctrl+Shift+Z redoes; a new edit clears the redo side. Session params are registry params and are covered; band add / remove / move keeps the existing 8-second undo unless folding it in is cheap. One status line names what was undone. A restore writes no file and leaves the dirty dot honest. Files get their own net: a preset file about to be overwritten or deleted goes to `<home>/trash/` first. (Decision 26.) | new `undo.py`; one call in the frame loop (`app.py`); explicit pushes in `preset.py`, `library.py`, `learn.py`, `midi.py`, `ui_routing.py`, `hands/panel.py`; key rows in `routing.LOOP_KEY_ROWS`; the cheat sheet | M–L |
| 2 | **Home** | `preset.home`, a trigger that loads the show's "starts on" preset (no new noun: decision 27). The Home key, and the APC40's OVERDUB button as an invariant control, lit. Undoable through WP1. The PRESETS page reads "starts on / home". | `params.py` (one trigger), `library.py`, `apc40.py`, `routing.py`, `ui_presets.py` | S |
| 3 | **Master dim on the crossfader** | `output.dim`, 0–1, a session param (a preset load never moves it), not persisted (a launch is always full brightness), multiplied into the frame as the very last thing before the window: after the FX chain and after the ghost hands' composite. The crossfader's invariant row moves from `overlay.bg` to `output.dim`, left is black, with soft pickup, so a crossfader left at black cannot dim the rig until it crosses the value (decision 28). The overlay ground stays on the OUTPUT page. No blackout button. | `render.py` (final pass), `overlay.py`, `apc40.py`, `routing.remap_factory` for existing `bindings.json` | S |
| 4 | **Save-as on the desk** | The desk never overwrites: a hold of about 0.6 s on the clip-stop row (all eight buttons act as one wide SAVE AS bar under the grid; a tap does nothing) saves the live state as a **new** preset and puts it in the next empty bank slot, whose pad blinks. The name is made from where the look came from: the loaded preset's name and the next free number ("TRIP 2", "TRIP 3"; a preset that already ends in a number counts on from it). A full bank saves to the list and says so. Plain Save on the panel still overwrites your own preset and copies a factory one, as today. On the PRESETS page a slot's context menu gains "put preset here…" and "clear slot". (Decision 29, as changed by the owner.) | `apc40.py`, `midi.py` (press duration), `routing.py`, `library.py` (naming, next empty slot), `ui_presets.py` | S–M |

Contracts: WP1 publishes `undo.push(label)` and the trash helper; WP2 and
WP4 call them. WP3 touches nothing the others do.

Exit: named tests for each row above; hand checks added to
`11-hand-checks.md` as group K (checks 48–57: undo of one slider drag, of one knob turn,
after an F-key load, after a Learn, after an Unbind; a hand moving makes
no step; home from any preset on either layer; the crossfader dims to
black and back, survives a preset load, starts bright; a hold saves a new
preset into the next empty slot and a tap does not; the new slot loads
from the desk).

### Plan 16 — Paper cuts (no design forks)

*As built:* [`16-paper-cuts.md`](16-paper-cuts.md) §7 (PRs #84–#86, #89, #90, and #92 for four follow-ups); where it differs from the rows below, that section is the code — three chips to a row, the idle strip dimmed by a veil, a first launch's window size not clipped. Its forks are decision register rows 45–49.

| WP | What | Finding it fixes | Size |
|---|---|---|---|
| 1 | The cheat sheet is off at launch (`Panel.cheatsheet = False`); the desk diagram stays on; `/` still toggles | "cheat sheet off by default" | S |
| 2 | An FX chip click selects; the toggle is its own target on the chip (a lit corner or the strip's "on"). Selection is tracked by effect name, not by index into the order-sorted list, so a reorder or a preset load never changes which effect is open | select without toggling; each reorder click changed which effect was being edited | S |
| 3 | With an effect off, its strip says so and offers "turn on" beside the greyed controls | effect controls doing nothing while the effect is off | S |
| 4 | Window placement at launch: `[output]` config for which monitor each window opens on, and the last positions remembered in the home folder | window placement at startup | S |
| 5 | `view.instances` floor 0 (nothing drawn at 0); `dream.layer` not modulatable (plan 12 §2 says never routed); the `ui_presets.py` docstring that contradicts the code; the `preset.py` comment that says `party-noita` follows a no-rate-params rule it does not follow (the comment goes, the rows stay) | "instances to zero"; three drifts the sweep found | S |

### Plan 17 — Learn, unbind and seeing the desk

*As built:* [`17-learn-and-the-desk.md`](17-learn-and-the-desk.md) §7 (PRs #93, #96, #99, #91 and #102); where it differs from the rows below, that section is the code — no DESK page (the desk window grows, and fills the control window with the panel hidden), Unbind covers every route and not only the hand's, an invariant control works through a learn, and a picked control lets go by itself after 20 s. Decision register rows 57–64; hand checks 64–71.

- **One Unbind.** One menu item that removes whatever performs the param
  (desk row, hand rows); a submenu only when there are two kinds. Shown
  whether or not a MIDI port is open. Undoable.
- **Learn that cannot pick the wrong source.** "Learn desk" and "Learn
  hand ▸ left / right" as the menu items, so a hand learn listens to one
  hand and a knob bump during a hand learn is ignored. This is the fix for
  "the Leap assigned a learn to the wrong hand".
- **Learn where it is missing**: the controls the sweep lists as lacking
  the menu, where a Learn means something. Not every widget: the plan
  lists which and why.
- **The desk, big and clickable.** A DESK view at a size you can read from
  a step back: every mapped control labelled with its param. Click a
  control: the ROUTING page scrolls to its row. Click a control, then a
  param: mapped (the session's "drag to map" at a fraction of the cost).
- **A ROUTING filter**: one text field that filters rows by glyph, param
  or source.

Forks the orchestrator settles when the plan is written: where the big
diagram lives (its own page, or the existing one enlarged; "no page
scrolls" stands).

### Plan 18 — Hand and knob feel

*As built:* [`18-hand-and-knob-feel.md`](18-hand-and-knob-feel.md) §7
(PRs #94, #97, #98, #100 on `plan-18-integration`; decision register
rows 50–56; hand checks 72–80). Two things differ from the lines below:
knob smoothing is on at 80 ms in the running app, and `hands-orbit`'s
zoom depth is 0.12.

- **An interaction box.** Explicit bounds in `hands.json`, drawn on the
  HANDS page's box; a hand outside them reads absent, so its rows let go
  as B1 already does. Today "in the box" is only the tracker's confidence.
- **A learn's default.** A hand learn today lands as a full-range
  `position` row at depth 1, on any param; on a rotation or speed param
  that is what read as "too sensitive". Centred axes learn as `push`
  about the base ("bipolar targets"), and the default depth is a session
  setting, one number, not a per-route extra. **Rate-type params under a
  hand are allowed** (the owner, 2026-10-04): nothing flags, warns about
  or refuses them, and `party-noita` keeps its two.
- **Knob smoothing.** One session param: a short slew on values arriving
  from the desk's knobs and faders, off at 0. No per-control settings.
  The undo's settle time must outlast it (plan 15 WP1).
- **Two-hand orbit camera**: a preset (routes onto the camera params that
  exist), not a new mode; built only if it needs no new axis (DECISIONS:
  "no gesture vocabularies, no more DOFs").

Whether the rig was calibrated that night is unknown (Q3). The plan is
built either way; the hand checks start with calibration.

### Plan 19 — Presets and the desk layout

*As built:* [`19-presets-and-the-desk.md`](19-presets-and-the-desk.md)
§7 (PRs #104, #110, #115, #114, #117 and #119 on `plan-19-integration`;
decision register rows 72–78; hand checks 81–90). Where it differs from
the lines below, that section is the code — a preset's old shape pads
drop at load **without** a note (a note only for a row the owner mapped
there), and rename repoints every show of the owner's, not only the
open bank.

- **Twenty-four presets on the desk.** The bank grows from 8 slots to 24:
  clip row 1 is slots 1–8 as today, clip rows 4–5 become slots 9–24, all
  invariant (the same on both layers). Shape selection leaves those two
  rows for the cue knob, which already has it. F1–F8 stay the first
  eight. `SLOTS = 8` is wired into the keys, the clip row, the PRESETS
  page and the params loop: this is the L item. A preset whose desk layer
  maps rows 4–5 has those rows dropped at load with a note, as any row on
  an invariant control is today. The plan carries a drawing of the desk.
- **The factory preset layer re-cut** toward knobs and faders: the device
  knobs, dark on most presets today, get the params the session reached
  for. A data change.
- **Hide what nobody wants.** A × on any preset in the list: a user preset
  goes to the trash (plan 15), a factory preset is hidden (a list in the
  home folder; "show hidden" brings them back). Factory files stay
  read-only on disk. The owner culls at the machine in a minute; nobody
  has to say in advance which presets are the bad ones.
- **Rename** a preset from the list (the file, and every bank slot that
  points at it), so a "TRIP 3" can get a real name.
- **A dirty dot that reads at arm's length**, and "save" labelled for what
  it does ("save" on yours, "save copy" on a factory one).
- **The trash**: a view of it, restore, empty.
- **The home in git**: `~/Hyperspace` as a repository with a commit on
  each save, opt-in from config; a `.gitignore` for weights and logs.
- **Not built**: folders (hiding and the filter first; the owner did not
  ask again).

### Plan 20 — FX, dream and looks

*As built:* [`20-fx-dream-looks.md`](20-fx-dream-looks.md) §7 (PRs #101,
#106, #108, #105, #107 and #111 on `plan-20-integration`; decision
register rows 65–71; hand checks 91–98); where it differs from the lines
below, that section is the code — the picture starts from what a face
shows (pattern and bitmap), the chain view is the FX page's chip grid,
**`dream.layer` has six layers, so it is a row of six chips, not four**,
and "speed" is `dream.k`.

- **The faces as their own effect target** (the owner's ask, 2026-10-04:
  "shaders that run against the screen space … that render target should
  just be the bitmaps in the faces on the geometry"). Each effect gets a
  target, `frame` (today) or `faces`. Effects aimed at the faces run as a
  second pass of the same chain into a texture of fixed size, starting
  from the face bitmap (or the flat face pattern when no bitmap is
  loaded); the face shader then shows that texture where it shows the
  bitmap today. One more switch, for the whole face target, says how the
  texture sits on the geometry: **per face** (each face carries the whole
  picture, as the bitmap does now, and it turns with the shape) or
  **screen** (the faces are windows onto one picture that stays still
  while the shape moves across it). What the code already gives: faces
  carry face-local UVs and sample `pattern()` and `u_bitmap`
  (`render.py`), a face coverage pass exists, and `FxChain` is a
  self-contained ping-pong that can be instanced at another size. What
  the plan must settle from the code: effects that read the previous
  frame or assume the window's aspect, the texture size, and that the
  echoes (captured before the frame's effects) will carry the faces'
  effects. Cost in params: one enum per effect, generated like `order`,
  and one mapping switch.
- **A chain view**: the effects that are on, per target, in order, as a
  list you drag to reorder (the `order` integers stay the stored form).
- **The look-back page as two sections**, ECHOES and DREAM, with labels
  that say what each knob does ("Spacing" becomes a name that means time
  between echoes); `dream.layer` shown as a row of four. Labels and layout
  only: no param id changes, so no migration.
- **Dream "speed"**: the plan first says which of `gap`, `fade`, the
  worker's `k` and `steps` the session meant, then exposes one control.
- **Instance layouts**: `view.inst_layout` — grid, hex, ring.

### Plan 21 — Outputs and the hands

The owner, 2026-10-04: the Pepper's Ghost glass and the projector are each
a render target; the laptop screen is the control view. Each target shows
the same frame, has its own dim, and has two switches of its own: the
polytope pipeline on or off, the hands on or off (four states per output).

- **Outputs.** A list of render outputs in the config (two on the rig),
  each a fullscreen window on its monitor sharing the one GL context. The
  scene with its effects is rendered once into a texture; the hands are
  rendered once into their own layer (as PR #78 already does); each output
  composes its picture from the two according to its switches, times its
  own dim, times the master dim. Six session params in all (scene, hands
  and dim per output), on the OUTPUT page as a small grid. The plan
  settles: outputs of different size or aspect, swap timing with two
  fullscreen windows, what a rig with one monitor does (one output, as
  today). This replaces the standing "two windows" decision with "one
  control window and a list of render outputs".
- **The ghost hands, finished.** PR #78 is merged into `finish-line` at
  the start of the run (§3 row 0). Here it is reviewed as any work
  package, its findings fixed, and its hand checks written.
- **Things to draw in place of hands.** #78 draws through one call,
  `draw(poses, view_proj, eye)`, with the capsule hands behind it. One
  enum, `ghost.style`, picks what is drawn from the same poses: the
  capsule hands, simple shapes (a primitive per joint or per palm), and
  one or two fun objects the plan proposes with pictures.

## 5. Contracts between plans

- Plan 15's `undo.push(label)` is called by every later plan's replacing
  action (17's Unbind and click-to-map, 19's hide, rename and trash, 20's
  reorder).
- Plan 15 WP4's "next empty slot" reads the bank's size from one place,
  so plan 19's twenty-four slots need no change to it.
- Plan 16 WP2's selection-by-name is what plan 20's chain view drives
  (as built: `FxState.select(name)` / `selected()`, `fx.py`).
- Plan 16 WP4's `<home>/windows.json` is machine-specific: plan 19's
  `.gitignore` for the home should list `windows.json` beside
  `last_show`. Its `render` entry is a list, shaped for plan 21's second
  output.
- Plan 17 and plan 18 both touch a hand learn: 17 owns `learn.py` and the
  menu; 18 owns what a learned row looks like (`_place`'s op and depth) and
  `hands/`. 17 merges first.
- Plan 15 WP3's `output.dim` is the master over plan 21's per-output dims.
- Plan 20's face target renders before the scene pass; plan 21 composes
  after everything. They meet only in `render.py`'s frame order; 20 merges
  first.

## 6. Deferred or parked, with the reason

- **Auto BPM**: deferred by the owner, 2026-10-04 ("something we need to
  put a little bit of thought into"). Tap-only stands for this run.
- **A blackout switch**: the session turned it into dimming.
- **Preset folders**: hiding and the filter first.
- **Drag-to-map**: click-then-click first (plan 17).
- **Hands fixed to one set of properties**: conceded in the session;
  hands stay mapped per preset.
- **Hardware** (a Leap mount, a plywood APC40 mount, a second screen or
  iPad): the owner's list, not software.

## 7. The owner's answers, 2026-10-04

Also in `docs/DECISION-REGISTER.md` Part A4.

| What | Answer |
|---|---|
| Dates | Needed by Friday 2026-10-09; do not plan around dates |
| Undo depth (26) | Single parameter edits are in |
| Rate-type params under a hand | Allowed; no restriction |
| Who merges | The run never touches main; everything on `finish-line`; the owner merges that |
| A fork mid-run | The orchestrator takes its recommendation, builds it, and logs it in the register to confirm or overturn |
| Home (27), crossfader (28) | As recommended |
| Save on the desk (29) | Save-as: always a new preset with a made-up meaningful name; the desk never overwrites. Plain Save on the panel overwrites |
| Outputs (32) | Two render targets, the same frame, each with its own dim and its own switches for the scene and the hands; the laptop is the control view |
| The hand HUD (33) | Finish and merge PR #78, and make what is drawn swappable for other objects |
| "Faces through FX" | The faces as their own effect target (plan 20) |
| Presets | More than eight on the desk; clean out the unwanted ones; no always-ask on save |
| Auto BPM (31) | Deferred |
| Scope | All of plans 15–21, in order |

Still unknown, and not blocking: where the presets from that night are
and whether they are backed up (`cp -R ~/Hyperspace ~/Hyperspace-2026-10-04`
before launching any new build); whether the hands were calibrated; which
build ran.
