# Roadmap — plans 15 to 21: from the Oct 3–4 session to the finish line

**Written 2026-10-04 on main fa9b3a1 (1003 tests).** Source: the review of
the Oct 3–4 session at the machine (Dan and Dillon, 1h44m transcript, read
against main), plus a code sweep of the twelve areas it names. This file
orders the work and scopes each plan. It is not the plans: each plan
document (`15-…md` to `21-…md`) is written against main as it stands when
that plan starts, by the session that runs
[`docs/prompts/plans-15-21-orchestrator.md`](../prompts/plans-15-21-orchestrator.md).

## 1. The constraints on everything below

- **"We don't want to drown in the number of parameters."** Said in the
  session; it bounds the whole list. A work package that adds a param, a
  menu item or a page says which one it replaces, or why none. Prefer a
  better default, a label, or an existing concept (a macro, a route's
  depth, the show's "starts on") over a new knob.
- **Undo was called "absolutely the most important thing."** It is first.
- **Wednesday 2026-10-07 is treated as the deadline** for plan 15 and
  nothing else (assumed; question Q1). Everything before it must be
  revertable on its own.
- **The control model stands** (ARCHITECTURE §3) and so does every
  DECISIONS row. Where the session asked for something a standing decision
  rules out, it is a register row, not a work package.
- **Never touch the owner's real `~/Hyperspace`.** The roughly ten presets
  saved that night live there and may not be backed up (Q2). Every agent
  runs with `HYPERSPACE_HOME` pointed at a temp folder.

## 2. What the session got wrong about the system (do not build these)

| Asked for | What is true on main | So |
|---|---|---|
| Un-hard-code the F1–F8 presets | They are eight pointers in the show file; ⇧F1–F8 or ⇧click overwrites one | Nothing to build. The gap is a save gesture on the desk and assigning an existing preset to a slot (plan 15 WP4) |
| Decide how module presets compose | Decided: a preset stores each module preset's name as a label and never loads it (D3) | Nothing to build |
| Add dream layer selection | `dream.layer` exists, four layers | Surface it better (plan 20) |
| Rename echo "Spacing" to "complexity" | It is the time between echoes (`dream.gap`) | Rename only to something that says so (plan 20) |
| Delete the factory presets | Read-only by decision; a user file shadows one | Hide, do not delete (plan 19) |
| Git-diffable preset files | Already one plain JSON per preset, one row per line | The gap is that `~/Hyperspace` is not in git (plan 19) |
| Lower hand "sensitivity", tame rotation | There is no sensitivity param. The complaints come from learning hands onto rate-type params, which plan 12 rules out for party presets; a learn writes a `position` row at depth 1 | Fix at the Learn and in the factory data (plan 16 WP5, plan 18) |
| Dimming on the crossfader "in shift mode" | Faders mean one thing on both layers (D6). The crossfader's job today, the overlay ground, is inert since decision 21 | Take the crossfader whole (plan 15 WP3, decision 28) |

## 3. Sequence

| Order | Plan | What | Size | Gate |
|---|---|---|---|---|
| 1 | **15 — Safety net and the bank** | Undo, home, master dim, a save gesture on the APC40 | 4 WPs, S–M each | before Wed 2026-10-07; decisions 26–29 built on the recommendation |
| 2 | **16 — Paper cuts** | Small fixes with no design fork: cheat sheet off, FX chip and stack selection, window placement, instances to zero, the NOITA rate rows | 6 WPs, S each | after 15 merges; may start in parallel on files 15 does not own |
| 3 | **17 — Learn, unbind and seeing the desk** | One Unbind, a hand learn and a desk learn that cannot be confused, Learn on the controls that lack it, a bigger diagram you can click, a ROUTING filter | 5 WPs, S–M | after 16 |
| 3 | **18 — Hand and knob feel** | An interaction box, rate-type params under a hand, a learn's default depth and op, knob smoothing | 4–5 WPs, S–M | parallel with 17 (different files, one contract: §5); Q3 calibration answered first |
| 4 | **19 — Presets and the desk layout** | Save-as and the dirty dot, hiding factory presets, a trash, the home in git, folders if still wanted, more slots on the desk, the factory preset layer re-cut toward knobs | 6 WPs, S–M, one L | after 17; decisions filed when the plan is written |
| 4 | **20 — FX, dream and looks** | A chain view with safe reorder, controls of an effect that is off, the look-back page split into echoes and dream, instance layouts | 5 WPs, S–M | parallel with 19 |
| 5 | **21 — Outputs** | The hand HUD, a projector output beside the Pepper's Ghost one, per-output dim | L, new architecture | last; blocked on decisions 32 and 33 |

Why this order: 15 is what makes a mistake at the party recoverable. 16 is
an afternoon of fixes that were each hit that night and need no decision.
17 comes before 19 because mapping was where the session lost the most
time and because 19's desk re-cut is easier to judge once the diagram is
clickable. 18 runs beside 17 because its code is `hands/` and `midi.py`,
not `learn.py` and the UI. 21 is last because it is the only new
architecture and the only one with an unanswered "what is it" (Q6).

**PR shape** (decision 30, reconciling the two positions in the session):
one PR per work package, small, each with a demo (a screenshot or a
headless script and its output) in the PR body; the WP PRs of one plan
stack on a `plan-NN-integration` branch; the owner merges one integration
PR per plan. For plan 15 each of the four features is also its own merge
commit on the integration branch, so one `git revert -m 1` takes exactly
one feature out before Wednesday.

## 4. The plans

Sizes: S = under half a day of agent time, M = a day, L = more. "Owns" is
the file set a work package may edit; the plan document tightens it.

### Plan 15 — Safety net and the bank (before Wednesday)

| WP | What | Scope | Owns | Size |
|---|---|---|---|---|
| 1 | **Undo** | A bounded in-memory stack of whole-preset snapshots (`Presets.document()`: values, routes, desk layer, macros). A snapshot is pushed before every action that replaces or removes: preset load (panel, F-key, APC40 row, `preset.next/prev`), show load / new, module-preset load / reset, Learn landing, Unbind, a ROUTING row or macro delete, Replace in the Replace / Keep prompt. Ctrl+Z restores the top through the load path (so D2 holds: a restore replaces everything); Ctrl+Shift+Z redoes. A restore writes no file and leaves the dirty dot honest. One status line names what was undone. File actions get a file-level net: a preset overwritten by a slot save or deleted from a strip goes to `<home>/trash/` first. The 8-second undo on reset-all stays as it is (it restores analyzer objects, which are session). Not in v1: undo of single slider moves (decision 26). | new `undo.py`; call sites in `preset.py`, `library.py`, `learn.py`, `midi.py`, `ui_routing.py`, `hands/panel.py`; a key row in `routing.LOOP_KEY_ROWS`; the cheat sheet | M |
| 2 | **Home** | `preset.home`, a trigger that loads the show's "starts on" preset (no new noun: decision 27). A key row, an invariant APC40 button, lit. Undoable through WP1. The PRESETS page labels the "starts on" preset as home. | `params.py` (one trigger), `library.py`, `apc40.py`, `routing.py`, `ui_presets.py` | S |
| 3 | **Master dim on the crossfader** | `output.dim`, 0–1, a session param (a preset load never moves it), not persisted (a launch is always full brightness), multiplied into the frame as the last thing before the window, after the FX chain. The crossfader's invariant row moves from `overlay.bg` to `output.dim` with soft pickup, so a crossfader left at black cannot dim the rig until it crosses the value (decision 28). The overlay ground stays on the OUTPUT page. No blackout button: the session settled on dimming. | `render.py` (final pass), `overlay.py`, `apc40.py`, `routing.remap_factory` for existing `bindings.json` | S |
| 4 | **Save on the desk, and the bank** | A long press (about 0.6 s) on the clip-stop button under column k fires `preset.save.k`; the button blinks to confirm; a short press does nothing (decision 29). The preset it overwrites goes to the trash first (WP1). On the PRESETS page a slot's context menu gains "put preset here…" so a preset saved with "as…" can be reached from the desk without loading it first. | `apc40.py`, `midi.py` (press duration), `routing.py`, `ui_presets.py` | S–M |

Contracts: WP1 publishes `undo.push(label)` and the trash helper; WP2 and
WP4 call them. WP3 touches nothing the others do. If PR #78 (ghost hands)
merges first, WP3's multiply goes after its composite.

Exit: named tests for each row above; hand checks added to
`11-hand-checks.md` as group I (undo after an F-key load, after a Learn,
after an Unbind; home from any preset on either layer; the crossfader dims
to black and back, survives a preset load, starts bright; a long press
saves and a short press does not; the saved slot loads from clip row 1).

### Plan 16 — Paper cuts (no design forks)

| WP | What | Finding it fixes | Size |
|---|---|---|---|
| 1 | The cheat sheet is off at launch (`Panel.cheatsheet = False`); the desk diagram stays on; `/` still toggles | "cheat sheet off by default" | S |
| 2 | An FX chip click selects; the toggle is its own target on the chip (a lit corner or the strip's "on"). Selection is tracked by effect name, not by index into the order-sorted list, so a reorder or a preset load never changes which effect is open | select without toggling; each reorder click changed which effect was being edited | S |
| 3 | With an effect off, its strip says so and offers "turn on" beside the greyed controls | effect controls doing nothing while the effect is off | S |
| 4 | Window placement at launch: `[output]` config for which monitor each window opens on, and the last positions remembered in the home folder | window placement at startup | S |
| 5 | `party-noita`'s two hand rows on rate params (`fx.tripcolour.pulse`, `fx.warp.drift`, `preset.py` L692–693) re-pointed at non-rate params; a `rate` flag on the registry params plan 12 §2 lists; a test that no factory route puts a hand on a flagged param | plan 12's rule is stated and not enforced; the factory show breaks it | S |
| 6 | `view.instances` floor 0 (nothing drawn at 0); `dream.layer` not modulatable (plan 12 §2 says never routed); the `ui_presets.py` docstring that contradicts the code | "instances to zero"; two drifts the sweep found | S |

### Plan 17 — Learn, unbind and seeing the desk

- **One Unbind.** One menu item that removes whatever performs the param
  (desk row, hand rows); a submenu only when there are two kinds. Shown
  whether or not a MIDI port is open. Undoable.
- **Learn that cannot pick the wrong source.** "Learn desk" and "Learn
  hand ▸ left / right" as the menu items, so a hand learn listens to one
  hand and a knob bump during a hand learn is ignored. This is the fix for
  "the Leap assigned a learn to the wrong hand".
- **Learn where it is missing**: the ROUTING row targets and the bank
  buttons' siblings the sweep lists as lacking the menu, where a Learn
  means something. Not every widget: the plan lists which and why.
- **The desk, big and clickable.** A DESK view at a size you can read from
  a step back (the diagram today is small and above the cheat sheet):
  every mapped control labelled with its param. Click a control: the
  ROUTING page scrolls to its row. Click a control, then a param: mapped
  (this is the session's "drag to map" at a fraction of the cost; drag
  itself only if the owner still wants it after using this).
- **A ROUTING filter**: one text field that filters rows by glyph, param
  or source.

Forks to file when the plan is written: where the big diagram lives (its
own page, or the existing overlay enlarged; "no page scrolls" stands);
whether click-then-click replaces drag.

### Plan 18 — Hand and knob feel

- **An interaction box.** Explicit bounds in `hands.json`, drawn on the
  HANDS page's box; a hand outside them reads absent, so its rows let go
  as B1 already does. Today "in the box" is only the tracker's confidence.
- **Rate-type params under a hand.** Using plan 16's `rate` flag: a Learn
  onto a flagged param says so and lands as a gentle `push` (a small depth
  about the base) instead of a full-range `position`. This is what "tamer
  rotation" and "lower sensitivity" were.
- **A learn's default.** Centred axes learn as `push` about the base
  ("bipolar targets"); the default depth is a session setting, one number,
  not a per-route extra.
- **Knob smoothing.** One session param: a short slew on values arriving
  from the desk's knobs and faders, off at 0. No per-control settings.
- **Two-hand orbit camera**: scoped in the plan as a preset (routes onto
  the camera params that exist), not a new mode; built only if it needs
  no new axis (DECISIONS: "no gesture vocabularies, no more DOFs").

Before it starts: Q3 (was the rig calibrated that night). If not, hand
checks 13–18 come first and some of this list may shrink.

### Plan 19 — Presets and the desk layout

- **Save.** "Save" on a factory preset already writes your copy; say so on
  the button. A dirty dot that reads at arm's length (size, colour, the
  name marked). Whether plain Save should always ask for a name is a fork.
- **Hide factory presets** per show (a list in the show file); nothing is
  deleted. **Trash** view and empty (plan 15 put files there).
- **The home in git**: `~/Hyperspace` as a repository with a commit on
  each save, opt-in from config; a `.gitignore` for weights and logs.
- **Folders** only if hiding and the filter are not enough: the library
  scans one level deep and shadows by slug, so folders are the one L item
  here. A fork.
- **More presets on the desk** and **the factory preset layer re-cut**:
  the shape rows (clip rows 4–5) and the cue knob are data in the factory
  layer. Shape moves to the cue knob alone; the freed pads and the unused
  device knobs go to what the session reached for. A grid of presets
  beyond eight needs `SLOTS = 8` lifted (keys, the clip row, the page, the
  params loop): a fork, with a drawing of the desk under each option.

### Plan 20 — FX, dream and looks

- **A chain view**: the effects that are on, in order, as a list you drag
  to reorder (the `order` integers stay the stored form).
- **The look-back page as two sections**, ECHOES and DREAM, with labels
  that say what each knob does ("Spacing" becomes a name that means time
  between echoes); `dream.layer` shown as a row of four. Labels and layout
  only: no param id changes, so no migration. Whether echoes get their own
  on switch is a fork (it is an id change).
- **Dream "speed"**: the plan first says which of `gap`, `fade`, the
  worker's `k` and `steps` the session meant, then exposes one control.
- **Instance layouts**: `view.inst_layout` — grid, hex, ring.
- **"Faces through FX"**: faces already pass through the chain. The plan
  asks what was seen (Q7) before building anything.

### Plan 21 — Outputs

Blocked on two answers. Decision 32: is the Pepper's Ghost picture the
render window (plan 14's assumption) or one of two outputs with a
projector beside it (what the session ran). Decision 33: is the hand HUD
Dillon's draft PR #78 (capsule ghost hands, drawn after the FX chain, off
by default) or the "simple shapes first" the session settled on. Scope
once answered: an output list in the config, each with its monitor, what
it shows and its own dim under the master; the HUD as a layer an output
may show or not.

## 5. Contracts between plans

- Plan 15's `undo.push(label)` is called by every later plan's replacing
  action (17's Unbind and click-to-map, 19's hide and trash, 20's reorder).
- Plan 16 WP5's `rate` flag is read by plan 18.
- Plan 16 WP2's selection-by-name is what plan 20's chain view drives.
- Plan 17 and plan 18 both touch a hand learn: 17 owns `learn.py` and the
  menu; 18 owns what a learned row looks like (`_place`'s op and depth) and
  `hands/`. 17 merges first.
- Plan 15 WP3's `output.dim` becomes the master over plan 21's per-output
  dims.

## 6. Parked, with the reason

- **Auto BPM**: reverses "tap sets BPM … no drift correction: re-tap".
  Dillon said it is not that important; Dan said it is real work.
  Decision 31, recommended: stay tap-only.
- **A blackout switch**: the session turned it into dimming.
- **Ghost-hand meshes**: decision 33.
- **Hands fixed to one set of properties**: conceded in the session;
  hands stay mapped per preset.
- **Hardware** (a Leap mount, a plywood APC40 mount, a second screen or
  iPad): the owner's list, not software.

## 7. Questions only the owner can answer

Mirrored in `docs/DECISION-REGISTER.md` Part A4.

| # | Question | Assumed until answered |
|---|---|---|
| Q1 | What is Wednesday, when is Rachel's party, and which is the deadline? | Wednesday 2026-10-07 is the deadline for plan 15 |
| Q2 | Where are the presets saved that night, and are they backed up? | In `~/Hyperspace/presets/` on the rig, not backed up. Do `cp -R ~/Hyperspace ~/Hyperspace-2026-10-04` before launching any new build |
| Q3 | Were the hands calibrated on that rig? | No. Plan 18 waits on hand checks 13–18 |
| Q4 | Which build ran that night? | Main at fa9b3a1 |
| Q5 | PR shape (decision 30) | One PR per work package, one integration PR per plan |
| Q6 | Two outputs or one (decision 32) | Unknown; plan 21 waits |
| Q7 | "Faces through FX": what was seen and what was wanted? | Unknown; plan 20 asks before building |
