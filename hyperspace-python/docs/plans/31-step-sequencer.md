# Plan 31 — the step sequencer: envelopes on a grid, N LFOs, the APC40 clip grid as the pattern

**Status: design, not built (2026-10-22).** Consolidated from four
design passes (modulator bank, sequencer engine, APC40 surface,
integration) read against `plan-28-30-integration` at 3c171a9. The
target base is the main commit that merges upstream main and PR #212
into that branch. Line references are to 3c171a9 and will drift a little
after that merge. Rows and hand-check numbers are provisional until it
lands.

## What the owner wants (2026-10-22)

- **Envelope generators.** None exist today. They go beside the LFOs,
  and each one can be routed to any automatable parameter.
- **An arbitrary number of LFOs.** Today there are four fixed ones
  (`lfo.N = 4`, DECISIONS row 140).
- **A step sequencer that triggers the envelopes.**
- **The APC40's clip-launch section is the grid**: 8 columns × 5 rows
  is 5 lanes (one envelope each) × 8 steps over a chosen span ("bar").
- **The clip-stop row is the playhead**: it lights across in time with
  the tempo.

## The shape in one paragraph

A new **modulator bank** (`modbank.py`) holds voices with stable ids.
It follows the plan 28 N1 modifier precedent: params are declared at
runtime, ids are one past the highest, and the bank is undoable and
saved in the preset. The LFOs become one bank, of any size up to 16.
**Envelopes** (`envelope.py`, AHDSR) are a second bank, `env:<n>`.
They are event-driven, so a fire stamped with a sub-frame time renders
exactly. A **sequencer** (`sequencer.py`, `seq`) reads its position
straight off the tempo clock. Its steps are registry params. It steps
inside `Router.modulate` right after `lfos.begin`, fires each lane's
envelope with the step's exact time, and publishes `seq:<lane>`
trigger lanes so a lane can fire anything else too. On the APC40 a
**sequencer page** (SEND A) shadows the clip grid, clip stop and scene
launch while it is up, and everything else stays live.

## Design

### B — the modulator bank (N LFOs)

- **`modbank.Bank`** owns:
  - stable 1-based ids, with add/remove/`next_id`/cap 16;
  - params declared from a `modifiers.Spec`-style table: `remove_prefix`
    then re-declare, which bumps `reg.serial`, which rebuilds the patch
    (routing.py:1520, params.py:697-733);
  - preset/undo doc;
  - publish, where a gap publishes NaN so a route from a deleted voice
    goes dormant (routing.py ~3238);
  - the late-trigger hold from lfo.py:233-261.
- **Voices.** `LFO` and `Envelope` implement only `step` and their
  `restart`/`fire`.
- **Addresses do not change.** They are `lfo:<n-1>`, params `lfo.<n>.*`.
  Ids never compact: removing LFO 2 leaves LFO 3 as `lfo:2`. Every
  factory preset and route keeps working.
- **Router and patch.** `use_lfos` becomes `use_banks`. The hard-coded
  `("lfo", i)` paths become `("bank", scheme, i)`: routing.py:2876-2960,
  3035-3053, 3204-3224, and patch.py:56-66.
- **In the preset**, a new key: `"lfos": [1,2,3,4]`. A file without it
  gets `[1,2,3,4]`. Knob values stay in `values`.
- **Undo.** Bank membership is added to `undo.State` beside the
  modifiers (undo.py:71, 239, 504).
- **Hot reload.** The reload target at app.py:1208 becomes a callable.
  The first launch after B needs a restart.

### E — envelopes (`env:<n>`, params `env.<n>.*`)

- **Shape: AHDSR**, with hold defaulting to 0 so it reads as ADSR.
  - `mode` is `gate | one-shot`. One-shot closes its own gate at the end
    of decay.
- **Knobs**, all of them registry params, so they are modulatable,
  Learnable and saved in the preset:
  - `attack hold decay sustain release`: log, 1 ms – 8 s.
  - `curve`: −1…1, using the modifiers' `CURVE_POW`.
  - `sync`: `s | beats`. In beats mode the times are read as beats and
    follow tempo changes mid-stage.
  - `retrig`: `legato | reset`.
  - `amount`.
  - `velocity` (sensitivity).
  - `fire`: a trigger.
  - `gate`: a momentary-able toggle.
- **Output** rests at **0.0**, published through `router.rests["env"]`,
  like the modifiers and the analyzer lanes. A negative row depth pushes
  down. Peak = `amount·(1−vs+vs·vel)`.
- **API**:
  ```python
  Envelopes.fire(n, *, at=None, velocity=1.0, gate=None)
  Envelopes.release(n, *, at=None)
  ```
  - The state is (stage, stage start, start level). The value at frame
    t is a closed form of t − onset, so a step that fell between two
    frames is exact.
  - Several fires in one frame apply in order.
  - A fire with no `at` that arrives after the step (the panel,
    `Registry.apply`) is held to the next step, which shows level 0 at
    the start of the attack. That is the LFO rule.
- **The bank holds 5 lane envelopes (1–5) plus any extras** up to 16
  (decision 3).

### S — the sequencer engine (`sequencer.py`, a leaf like lfo.py)

- **Naming.** The name "patterns" is taken (the face shader's
  `patterns.py`). The new module is `seq` / "Sequencer".
- **Model.** 5 lanes × 8 steps. The step params are `seq.<l>.<s>`:
  toggles in v1, stored so they can become velocity later. Also:
  - `seq.<l>.mute`;
  - `seq.span` ∈ ½ bar · 1 bar · 2 bars · 4 bars, the time the 8 steps
    cover: 16ths, 8ths, quarters, halves;
  - `seq.length` 1–8;
  - `seq.swing` 0–0.5;
  - `seq.run` (session, never saved);
  - `seq.step` (read-only playhead, never saved).
- **Why steps are params** rather than a data blob: the pad becomes a
  plain `toggle` row with LED feedback, and Learn, undo, the preset and
  "a performer owns a step" all come with it. 40 params is small next
  to the registry. Pages later add more of the same.
- **Position.** `s(t) = clock.beat(t) · steps_per_beat`.
- **Firing.**
  - Each frame fires every step k in (k_last, ⌊s⌋], in order, each with
    its exact time t_k, which inverts tempo.py:123.
  - Odd steps are offset by swing.
  - A stall longer than a pattern fires only the current step, never a
    burst.
  - `set_bpm` keeps beat continuous, so tempo changes need nothing.
  - A backward nudge never double-fires.
- **Re-align.** `Clock.epoch` increments on `trigger()`. A new epoch
  fires step 0 that frame at the trigger time, so the global LFO
  trigger realigns the grid too.
- **Transport.** `run` only gates firing; the position is always the
  clock's, so the grid never drifts from the LFOs. Start waits for the
  next step boundary. Stop releases open gates.
- **Output.**
  - It calls `envs.fire(lane.env, at=t_k, velocity=v)` directly, with
    lane l bound to envelope l in v1.
  - It publishes `seq:<l>`, a trigger-kind lane (decision 10) that
    pulses on the frame a step fires, with `rests["seq"] = 0`. A lane
    can then fire `preset.next`, a strobe, anything.
- **Wiring.** `Router.use_sequencer`; app.py:1077-1106; reloader
  targets at app.py:1206.
- **In the preset.** `seq` is added to `PERFORMANCE_GROUPS`
  (params.py:111), and `env` with it. Pattern slots come free as module
  presets of the `seq` group (D3). Undo watches the steps; taps within
  0.4 s merge into one step.

### A — the APC40 sequencer page

- **A page, not a third layer.** A third layer doesn't work for two
  reasons:
  - Invariant rows win `dispatch` (routing.py:2071) and `active`
    (2088), so the bank pads would beat it.
  - Layers spread into Learn, preset desks and the GRAPH device nodes.
- **What a page is.** In-memory rows (`Bindings.page`, `page_rows`,
  `page_serial`) that shadow every row on their controls while up. They
  are never saved, never Learnable, and never in `table.bindings`. It is
  about 15 lines in `dispatch`/`active`/`is_invariant`. Everything else
  lives in a new `seq_page.py`.
- **Entering and leaving.**
  - **SEND A** (note 0x58), latched, LED lit while up. No map or
    factory preset uses it.
  - Older `bindings.json` files get it through `APC_NEW_ROWS`, or a
    `seq_missing` note if SEND A is taken.
  - Leaving bumps `page_serial`, so `MidiIO.redraw()` relights the bank,
    SAVE and the toggles from their params with nothing cached.
  - Entering clears hold timers, so a bank pad held across the switch
    can't save.
- **What the page owns**: clip rows 1–5 × 8, clip stop × 8, scene
  launch 1–5.
- **What stays live**: faders, knobs, SHIFT and its layers, the
  transport, TAP/NUDGE, QUANT (`preset.next`), OVERDUB, the track
  strips, STOP ALL and MASTER.
- **LEDs (mk1).** One rule, `routing.led_shade(b, p)`, is read by both
  `MidiIO.feedback` and `ui_desk._led`:

  | State | LED |
  |---|---|
  | Step on | GREEN |
  | Step on, lane muted | RED |
  | Playhead on a lit step | YELLOW |
  | Playhead | the lit clip stop in its column |
  | Scene k | lit = selected lane, blink = muted |
  | Columns past `length` | dark, and inert |

  - Only diffs are sent, through the existing `last_out` gate. That is
    about 12 messages per step at 180 BPM 8ths.
- **Gestures**:
  - a pad toggles a step;
  - a scene button selects a lane, and tapping the selected lane again
    toggles its mute;
  - clip stop k sets length = k.
- **Phase 2**: D5–D8 become the selected lane's A/D/S/R through
  `seq.sel.*` proxy params (the `band.sel.*` pattern). D1–D4 keep SCENE.
- **On-screen desk.** `ui_desk` shows the page through `table.active()`
  for free. Add `page_serial` to `_key` and a header line, "SEQ ·
  lane 2 · 1 bar · L=8". `click()` and `mappable()` refuse page
  controls.

### U — panel and GRAPH

- **LFO page.**
  - Show N strips: `+ lfo` on the head, `×` per strip.
  - Above 4 strips, collapse each to one line (scope thumbnail, name,
    out).
- **New SEQ page** (`ui_seq.py`, after `lfo` in `PAGES`):
  - an 8×5 grid of 52 px cells in the same LED palette, with the
    playhead column in `ui.RED`;
  - click toggles a step; right-click gives Learn;
  - below the grid, one envelope strip per lane (AHDSR, curve, amount,
    and a scope);
  - `+ env` for extra envelopes.
- **GRAPH.**
  - Kinds `env` and `seq` go in `graphview.KINDS`/`patch.KINDS`, the
    MODULATION area, and the idle rules.
  - `_lfo_count` (graphview.py:392) becomes a list of ids, because ids
    can have gaps.
  - Delete and picker entries for `lfo`/`env` (ui_graph.py:1785-1788).
  - LFO node positions move to the preset's `LAYOUT_KEY`, because N is
    now preset content.
  - The sequencer is one node with five trigger outputs. The lane →
    envelope binding is drawn as a cable. The N7/N9 rules stand.

### P — presets, schema, library

- **Conditional `hyperspace.preset/3`.** Written only when a preset
  uses envelopes, the sequencer, or N ≠ 4. Load accepts
  `versions=(2,3)` (preset.py:579).
  - Without it, an older build re-saving from the shared library would
    silently drop the new keys (preset.py:830-845). With it, the older
    build refuses the file instead.
  - /2 → /3 is the identity.
- **Factory `seq-demo`.** Kick, snare and hat lanes at ½ bar, driving
  envelopes onto brightness, zoom and fx.mix. Its goldens are taken at a
  fixed clock t.
- **Docs.** "Both Macs on one library must be on this build"
  (ENGINEERING, plan 25).

## Work packages

| WP | Size | What | After |
|---|---|---|---|
| S0 | S | Baseline: golden count, frame time with 4/16 LFOs + 16 envs, patch rebuild cost | the merge to main |
| B1 | M | `modbank.py`; LFOs as a bank of N with stable ids; router/patch generalised to banks; preset `lfos`; undo; hot reload. Existing LFO tests unchanged | S0 |
| E1 | M | `envelope.py` + `env` bank: AHDSR, exact `at=`, gate/one-shot, beats sync, legato/reset; boundary test | B1 |
| S1 | L | `sequencer.py`: clock-locked stepping, swing, epoch re-align, run, `seq:<l>` lanes, lane → env fire; `Clock.epoch` | E1 |
| P1 | M | Conditional preset/3, migration, library versions, `seq-demo` + goldens | B1–S1 |
| U1 | M | LFO page with N strips, add/remove | B1 |
| U2 | M | SEQ page: grid editor + envelope strips | S1 |
| G1 | M | GRAPH: `env`/`seq` kinds, picker/delete, id lists, layout keys | B1–S1 |
| A1 | L | APC40 sequencer page: page mechanism, SEND A row, `led_shade`, playhead on clip stop, desk mirror | S1 + **Dylan's sign-off** |
| A2 | S | Phase 2: D5–D8 selected-lane AHDSR | A1 |
| D1 | M | ARCHITECTURE (module table, frame order), DECISIONS (row 140 re-decided), DECISION-REGISTER, ENGINEERING, TESTING-GUIDE, 11-hand-checks group Z, plans/README | throughout |

**Order.** B1 → E1 → S1 is the spine. U1 can run beside E1. U2, G1 and
P1 run in parallel after S1. A1 starts once Dylan agrees, and nothing
else waits on it: the panel's grid gives the full feature without the
hardware.

**Golden rule.** No existing golden moves. The defaults are 4 LFOs,
envelopes unrouted and resting at 0, and the sequencer stopped. Only
`seq-demo`'s frames are new.

### Tests (the headline ones)

- **Bank**: add/remove/next_id/cap; a NaN gap leaves a route dormant;
  removing LFO 2 keeps `lfo:2` on LFO 3; undo restores membership and
  bases; an old preset loads 4 LFOs.
- **Envelope**: a table of stage timings; curves; beats with a bpm
  change mid-stage; legato vs reset; velocity; a sub-frame `at` equals
  the closed form; several fires in one frame; a late fire shows attack
  0 on the next frame.
- **Sequencer**, with a deterministic `Clock(now=…)`:
  - steps per span;
  - each step fires once with the exact t_k, at 60 fps and at irregular
    dt;
  - several steps in one frame fire in order;
  - a stall fires no burst;
  - `set_bpm` mid-step neither skips nor doubles;
  - a backward nudge doesn't double-fire;
  - `lfo.trigger` fires step 0 the same frame;
  - swing; mute; run on/off;
  - the `seq:` rising edge fires a trigger param;
  - a hot-reload swap keeps `k_last`.
- **APC page**, on the fake-port rig (tests/test_midi.py:21-81):
  - SEND A enters and the grid redraws;
  - a pad toggles a step and doesn't load a preset;
  - clip stop 8 doesn't save;
  - scene 1 selects, then mutes, and doesn't toggle `view.points`;
  - the playhead sends only diffs;
  - leaving restores the bank's LEDs;
  - Learn doesn't take a page control;
  - a file with SEND A taken gets a note, not a row.

### Hand checks at the machine (group Z, provisional)

- Yellow over green is legible while the playhead runs.
- No flicker when the playhead crosses five lit steps.
- The mk1's blink rates on the grid and clip stop, which no one has
  verified yet (plan 15 group K).
- Leaving the page relights all 24 bank pads correctly.
- A power cycle with the page up re-sends the page (midi.py:670).
- Envelopes on brightness feel tight against the music at 120–175 BPM.

## Risks

- **Dylan's area.** DECISIONS 12, :55 and :355 make the APC40 map, its
  feel, `dispatch`, `active`, `feedback` and `DEFAULT_MAP` Dylan's. A1's
  footprint is one row plus three small hooks, but it needs his
  agreement first. #212 also touches `ui.py` `PAGES` and the `app.py`
  wiring, so expect merge conflicts there.
- **Registry growth.** About 6 params per LFO, 13 per envelope and 50
  for the sequencer make Learn menus and target combos longer. The caps
  hold it.
- **Frame time.** Each LFO scope is a 129-point polyline. Collapsing the
  strips handles it. S0 measures.
- **Numbering.** Main's DECISION-REGISTER stops at row 109 and the
  integration branch reaches 310. Rows (from 311) and hand checks (from
  277) are assigned only after the merge lands.

## Decisions for the owner

Each has a recommended answer.

1. **Replace "Four LFOs" (row 140) with "N LFOs, cap 16", removable by
   stable id.** *Recommend yes.*
2. **Envelope type.** *Recommend AHDSR, with gate and one-shot modes.*
   Hold defaults to 0, retrigger to legato, time to seconds (beats one
   enum away), with one shared curve.
3. **Lane envelopes.** *Recommend envelopes 1–5 always exist, each
   bound to its lane, plus up to 11 extras.* The alternative is a fresh
   preset starting with 0 envelopes and a lane creating one on first
   use. The designs differed here. Always-there is simpler on the
   hardware: every lane works the moment you press a pad.
4. **Steps as registry params** (Learnable, ownable, undo for free)
   rather than a data blob. *Recommend params.*
5. **Per-step data in v1.** *Recommend on/off only*, stored so it can
   become velocity. Gate length and probability come later. Swing in v1
   is one global value.
6. **Span and length.** *Recommend one global span* (½/1/2/4 bars over
   the 8 steps) *and a global length 1–8 set by a clip-stop press.*
   Per-lane length (polymeter) and 16/32-step pages come later.
7. **APC entry: SEND A, latched.** *Recommend SEND A.* The alternative
   is holding CLIP/TRACK. While the page is up the scene 1–4 render
   toggles are shadowed, which amends D6. A preset load does not leave
   the page.
8. **The pattern is in the preset; `run` is not.** *Recommend yes.*
   Pattern slots come as `seq` module presets.
9. **Conditional preset/3**, so older builds refuse a new file rather
   than silently stripping it. *Recommend yes.*
10. **Go ahead with A1 only after Dylan agrees.** Meanwhile B1 → S1 and
    the panel grid proceed.
