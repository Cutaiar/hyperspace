# Plan 31 — the step sequencer: envelopes on a grid, N LFOs, the APC40 clip grid as the pattern

**Status: built (2026-10-22)** on `plan-31-integration` (c81a9d9, 2582
tests passed, 2 skipped), all but the APC40 page. **A1, the APC40
sequencer page, is built on its own branch, `plan-31-a1`, and waits for
Dylan's sign-off** (he owns the desk, decision 10); nothing on
`plan-31-integration` depends on it. A2 (D5–D8 as the selected lane's
AHDSR) is not built. The owner accepted all ten recommended decisions
on 2026-10-22.

The LFOs are now a **modulator bank** of any size up to 16, each voice
added or removed by a stable id. **Envelopes** are a second bank: AHDSR
voices that rest at 0, fired by an event stamped to the sub-frame, so a
note that fell between two frames renders where it would have had a
frame landed on it. A **step sequencer**, five lanes of eight steps, reads
its position straight off the tempo clock, fires each lane's envelope at
each step's exact time and publishes five trigger lanes, `seq:0`–`seq:4`,
that any route can take. Every step is a registry param, so the panel's
grid, Learn, undo, the preset and (on `plan-31-a1`) the APC40's clip grid
all edit the same thing. A new **SEQ page** draws the grid in the APC40's
LED colours and the envelopes as strips; GRAPH draws the envelopes and
the sequencer as nodes, with each lane's envelope as a cable. A preset
that uses any of it is saved as `hyperspace.preset/3`; every other
preset is still `/2`, byte for byte. One factory preset was added,
`seq-demo`. **No golden moved**: 25 new ones are `seq-demo`'s (621 in
all).

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group Z, checks
280–295 (286–295 are the APC40 page's, on `plan-31-a1`). Decisions: the
ten are rows 311–320 of [`DECISION-REGISTER.md`](../DECISION-REGISTER.md),
each answered "(rec) — accepted 2026-10-22", and their rows in
[`DECISIONS.md`](../DECISIONS.md) "Tempo, LFOs and the sequencer".

Branch `plan-31-integration`, in merge order: the design (b361992), S1
(e833983), E1 (a3dc6b6), B1 (4822e97), U1 (f26ea8d), W1 (d1a71c2), P1's
gate (99731e4), U2 (006911a), G1 (23df7fb), P1 (0356320), D1 (this
file). A1 is 9e2e4f0 and 0d6c00a on `plan-31-a1`.

## What the owner wants (2026-10-22)

- **Envelope generators.** None existed. They go beside the LFOs,
  and each one can be routed to any automatable parameter.
- **An arbitrary number of LFOs.** There were four fixed ones
  (`lfo.N = 4`, DECISIONS "Four LFOs").
- **A step sequencer that triggers the envelopes.**
- **The APC40's clip-launch section is the grid**: 8 columns × 5 rows
  is 5 lanes (one envelope each) × 8 steps over a chosen span ("bar").
- **The clip-stop row is the playhead**: it lights across in time with
  the tempo.

## What was built

### B1 — the modulator bank (`modbank.py`); the LFOs as a bank of N

- **At the machine.** The LFO page has a `+ lfo` chip on the first
  strip's head and a `×` on every strip (U1, below). Four LFOs look and
  behave as before; every route, factory preset and Learn row still
  names the same LFO.
- **`modbank.Bank`**, a leaf (imports nothing from the package;
  `tests/test_modbank.py::test_modbank_imports_nothing_from_the_host`).
  A kind subclasses it and sets `SCHEME`, `LABEL`, `KEY`, `DEFAULT`,
  `REST`, `KNOBS`, `SHARED` and `make`. It owns:
  - **membership by stable 1-based id**: `ids`, `add(n=None)`,
    `remove(n)`, `set(ids)`, `doc`, `parse`, `next_id` (one past the
    highest), `can_add`. **Ids never compact**: removing LFO 2 leaves
    LFO 3 on `lfo:2` and `lfo.3.*`. `MAX = 16` voices; `MAX_ID = 64` is
    the highest id a file may name (a hand-edited 10⁹ is refused with a
    note, not a feed vector that long). `parse` drops a non-id or a
    repeat with a note and keeps the lowest 16.
  - **the params**: `bind(reg, declare)` hands the bank the kind's
    `declare(reg, n, voice)`; an add drops `<scheme>.<n>.` and declares
    it afresh, a remove drops it. Each moves `reg.serial`, which is what
    rebuilds the patch: there is no other hook.
  - **the frame**: `begin(t, clock)`, then `step_one(i, dt, t, clock)`
    at each voice's patch node; `step` for a caller with no router.
  - **publishing**: `outputs` is as wide as the highest id with **NaN in
    a gap**, so a route left on a removed voice reads NaN and goes
    dormant (`Router.modulate` skips a NaN lane, as for a hand out of
    view); a gap's label is "", which the source combo reads as no lane.
  - **late gestures**: `late` / `late_one` (lfo.py's old `_late`, moved
    here) — a trigger after the bank or its voice stepped at this frame's
    t is held to the next step.
- **`lfo.LFOs(Bank)`**: `SCHEME = "lfo"`, `KEY = "lfos"`, `DEFAULT =
  (1, 2, 3, 4)`, `SHARED = {"lfo.trigger": "trigger"}`. `lfo.declare(reg,
  lfos, clock, n, lf)` is LFO n's six knobs as before. `LFOs.lfos` is now
  a property (the voices in id order).
- **The router.** `Router.use_bank(bank, clock)` keeps each bank by
  scheme; `use_lfos` is a wrapper that also sets `Router.lfos` (the
  design's `use_banks` became one call per bank). `routing.BANKS` maps a
  scheme to its class (`lfo`, `env`), so a bare router still draws an
  LFO route's source as an LFO. The patch adds a node per voice id
  (`<scheme>:<n-1>`, its kind the scheme), links `<scheme>.<n>.<knob>`
  for the class's `KNOBS` and its `SHARED` params, and the plan step is
  `("bank", scheme, i)`, emitted only for an id the bank holds.
  `_patch_key` holds each bank's ids. `patch.KINDS` gains `env`.
- **The preset.** `"lfos": [ids]` is written **only when it is not
  `[1, 2, 3, 4]`**, so a preset of four LFOs is the file it always was.
  A file without it gets four. On load each bank's membership is parsed
  and set before the values land; a value for a voice the registry does
  not hold yet waits (`later`) until its voice is declared.
- **Undo.** `undo.Undo(…, banks=)` takes the banks by scheme, or a
  callable (app.py passes `lambda: router._banks()`). Each state holds
  every bank's ids; a restore puts the membership back (step 4¾) before
  the bases, so a voice that returns is declared, then its knobs land.
  Adding or removing an LFO is one step.
- **Hot reload.** `modbank` is watched before `lfo`. The reload target
  list in app.py was already a lambda re-read at each swap, so it lists
  the voices as they are then (`*[(lf, "lfo", "LFO") for lf in
  lfos.lfos]`); no change to make it a callable was needed.
- **Tests.** `tests/test_modbank.py`, notably
  `::test_removing_lfo_2_keeps_lfo_3_on_lfo_2`,
  `::test_a_route_from_a_removed_lfo_goes_dormant`,
  `::test_a_membership_change_rebuilds_the_patch`,
  `::test_an_lfo_owning_another_with_gaps_lands_the_same_frame`,
  `::test_undo_of_add_and_remove_restores_the_params_and_their_bases`,
  `::test_a_preset_without_the_key_loads_four_lfos`,
  `::test_a_preset_round_trips_with_gaps`. The existing LFO tests pass
  unchanged; `tests/test_lfo_boundary.py` allows `lfo` its one leaf
  import, `modbank`.

### E1 — envelopes (`envelope.py`)

- **The voice, `Envelope`**: AHDSR. Its knobs are `mode` (`gate` ·
  `one-shot`), `attack`, `hold`, `decay`, `sustain`, **`rel`** (the
  release time: `release` is the method that closes the gate; the param
  is still `env.<n>.release`, `envelope.ATTR` maps it), `curve`, `sync`
  (`s` · `beats`), `retrig` (`legato` · `reset`), `amount`, `velocity`.
  - Stage times are log 1 ms – 8 s (`T_LO`, `T_HI`). **Hold's knob bottom
    (1 ms) is 0**, since a log range cannot reach 0, so out of the box
    hold is off and the shape is an ADSR. The defaults: attack 10 ms,
    hold 0, decay 200 ms, sustain 0.6, release 300 ms, curve 0, gate,
    seconds, legato, amount 1, velocity 0.
  - `curve` −1…1 is one shape for every stage, the modifiers'
    `x ** CURVE_POW ** curve` (`CURVE_POW = 4`, copied, not imported).
  - One-shot runs attack, hold and decay, then releases on its own and
    ignores `release` and a gate length.
  - In beats mode the times are beats × 60 / bpm, the bpm read every
    step, so a tempo change mid-stage changes the stage's rate from
    where it is. Beats are counted from the bpm, never read off
    `clock.beat`, so a trigger or a nudge never jerks a stage.
  - Peak = `amount · (1 − vs + vs · vel)`; the output is the level times
    the peak **read live**, so `amount` moved mid-note scales the note.
- **Event-driven, so exact.** `fire(at=None, velocity=1.0, gate=None)`
  and `release(at=None)` only queue an event stamped with its time;
  `step(t, clock)` walks the stage boundaries and the queued events up to
  t in time order. Progress is kept as a fraction of the stage, so a
  modulated stage time changes the rate from where it is and never jumps
  the level.
  - A fire with no `at` (the panel, a key, `Registry.apply`'s rising
    edge) lands at the next step's own t, so the first frame that sees it
    shows level 0 at the start of the attack (the LFO rule).
  - A stamp before the last step is clamped to it: that frame is on
    screen already. Time never runs back.
  - `gate=` (seconds) queues the note's own release, tokened with the
    note, so a later fire's note is never cut short by an earlier note's
    release.
  - Legato re-attacks from the level showing, in the new note's units;
    reset snaps to 0.
- **The params**, `env.<n>.<knob>` in group `env`: every knob
  modulatable and persistent; `fire` a trigger; **`gate` a modulatable
  toggle that is not persisted** (`persist=False`: a preset that loaded a
  held gate would leave a note hanging). Only an edge of `gate` acts.
- **Tests.** `tests/test_envelope.py`, notably
  `::test_the_stages_land_on_time`,
  `::test_stepping_frame_by_frame_agrees_with_one_jump`,
  `::test_beats_follow_a_bpm_change_mid_stage`,
  `::test_beats_ignore_the_downbeat`,
  `::test_a_sub_frame_fire_is_the_closed_form`,
  `::test_several_fires_in_one_step_apply_in_time_order`,
  `::test_a_late_fire_is_held_and_starts_at_zero`,
  `::test_a_later_fire_outlives_the_earlier_notes_gate`;
  `tests/test_envelope_boundary.py` (a leaf but for `modbank`).

### W1 — envelopes as a bank, the sequencer in the pass, wired into the app

- **`envelope.Envelopes(Bank)`**: `SCHEME = "env"`, `LABEL = "env"`,
  `KEY = "envs"`, `REST = 0.0`. **Envelopes 1–5 always exist**
  (decision 3, `LANE_ENVS`): the constructor adds them whatever `ids`
  says, `remove` refuses them (returns False), and **`parse` re-adds them**
  — a hand-edited `"envs": [6]` loads as 1–6. Extras are 6 up to the cap
  of 16 voices. `"envs"` is written only when there are extras.
  - `Envelopes.fire(n, *, at, velocity, gate)` and `release(n, *, at)`
    return False for an id the bank lacks: a lane pointed at a removed
    extra fires nothing.
  - **`KNOBS` includes `fire` and `gate`**, so a route onto
    `env.2.fire` (from `seq:0`, say) lands before envelope 2 steps and
    the note starts this frame, not the next.
- **`Router.use_sequencer(seq, envs, clock=None)`** and
  **`Router._step_sequencer`**: in `modulate`, **every bank's `begin`
  first** (a held global trigger lands and moves the clock's epoch),
  **then the sequencer steps** — its fires go to `envs.fire(env,
  at=t_k, velocity=v, gate=seq.gate_seconds(clock))`, its stop releases
  to `envs.release` — and it publishes; **then the plan** walks the
  patch, where each envelope steps at its node and sees this frame's
  fires.
- **The `seq:` lanes** are 0-based like every router address: `seq:0`
  is lane 1, whose params are the 1-based `seq.1.*`. Each pulses the
  step's velocity on the frame its lane fires and rests at 0; their kind
  is `trigger` in `Router.lane_kinds` (decision 10's lane kind), so a
  route takes one to a trigger param on its rising edge.
- **Schemes.** `routing.BUILTIN_LANES = ("lane", "lfo", "env", "seq")`
  (a bare router's offer order) and `devices.BUILTIN_SCHEMES` the same,
  held equal by `tests/test_plan31_wiring.py`. `env` and `seq` are in
  `params.PERFORMANCE_GROUPS`, so they are the look's and a preset
  carries them; module presets of the `seq` group are the pattern slots
  (decision 8).
- **app.py** builds `envelope.Envelopes()` and `sequencer.Sequencer()`,
  registers both before `library.attach` (so "default" holds their
  knobs and an empty pattern), calls `router.use_bank(envs, clock)` after
  `use_lfos` and `router.use_sequencer(seq, envs)`, hands both to the
  panel (`panel.envs`, `panel.seq`) and lists the bank, each envelope,
  the sequencer and each lane as reload targets
  (`tests/test_app_boundary.py::test_main_hands_the_router_its_envelopes_and_sequencer`).
- **Tests.** `tests/test_plan31_wiring.py` end to end, notably
  `::test_a_step_fires_its_envelope_at_the_steps_exact_time_and_it_comes_back`,
  `::test_seq_lane_fires_a_trigger_param_on_each_step`,
  `::test_the_global_trigger_fires_step_0_the_same_frame`,
  `::test_a_route_onto_an_envelopes_fire_starts_it_this_frame`,
  `::test_an_extra_envelope_routes_and_goes_dormant_when_removed`,
  `::test_a_lane_on_a_missing_envelope_fires_nothing`,
  `::test_stopping_releases_gate_mode_envelopes`,
  `::test_nan_never_reaches_a_param_from_an_idle_bank`.

### S1 — the sequencer engine (`sequencer.py`) and `tempo.Clock.epoch`

- **The model.** 5 `Lane`s × 8 steps. A step is stored as a float (0
  off, > 0 its velocity) and is a toggle param in v1: on keeps a
  velocity it already has (decision 5). Per lane: `mute` and `env`, the
  envelope id it fires (1–16, default lane l → envelope l).
- **Globals**: `span` (`1/2 bar` · `1 bar` · `2 bars` · `4 bars`,
  default 1 bar; `steps_per_beat = 8 / (bars · 4)`), `length` 1–8,
  `swing` 0–0.5 of a step (how late every odd step lands), **`gate`
  0.05–1 of a step, default 0.5** (P1, below), `run`.
- **Position** is the clock's, never integrated: `s(t) = (clock.beat(t)
  + shift) · steps_per_beat`. Each `step(t, clock, fire, release=None)`
  fires every step k in (k_last, K], each at `time_of(k)`, tempo.py's
  `beat` inverted, so t_k is exact. Not crossings, and firing nothing
  extra:
  - **a stall** of more than `length` steps fires only the current step;
  - **a step backwards** (a nudge, swing turned up) holds `k_last`, so
    nothing fires twice; a jump back of more than 8 steps is a
    re-anchored clock and starts afresh;
  - **a span change** re-anchors and starts at the next boundary.
- **Re-align.** `tempo.Clock.epoch` (class-level 0) increments in
  `Clock.trigger`. A new epoch fires step 0 that call, at the trigger
  time, and clears the sequencer's own offset — the global `lfo.trigger`
  puts the grid on the one with the LFOs.
- **`seq.trigger`** ("Seq restart", not in the design): the sequencer
  alone restarts at step 0, keeping an offset `shift` (beats) from a
  clock that stays where it is. It is always held to the next `step` and
  lands at that step's t. Its light is lit while the playhead is on step 1.
- **Transport.** `run` gates firing only; `k_last` keeps following the
  clock while stopped, so starting fires at the first boundary after the
  last stepped frame — never a catch-up. `playhead` is None while
  stopped; the frame that sees `run` go off calls `release(lane, env, t)`
  for every lane.
- **Params**, group `seq` (`register`): `seq.<l>.<s>` toggles,
  `seq.<l>.mute`, `seq.<l>.env` (integer 1–16, **not modulatable**:
  retargeting a lane mid-gate would strand the envelope it opened),
  `seq.span`, `seq.length`, `seq.swing`, `seq.gate`; `seq.run` and the
  read-only **`seq.step`** (0 stopped, else the 1-based step) are
  `persist=False`; `seq.trigger`.
- **Hot reload.** The runtime state is class-level, so a swapped instance
  keeps `k_last` and fires nothing twice
  (`tests/test_sequencer.py::test_a_hot_reload_swap_keeps_k_last_and_fires_nothing_twice`).
- **Tests.** `tests/test_sequencer.py` on a deterministic clock, notably
  `::test_each_step_fires_exactly_once_at_its_exact_time_at_60fps`,
  `::test_each_step_fires_exactly_once_at_irregular_dt`,
  `::test_a_two_second_stall_fires_the_current_step_not_a_burst`,
  `::test_set_bpm_mid_step_neither_skips_nor_doubles`,
  `::test_a_backward_nudge_never_fires_a_step_twice`,
  `::test_the_clock_trigger_fires_step_zero_that_call_at_the_trigger_time`,
  `::test_swing_offsets_the_odd_steps`,
  `::test_seq_trigger_keeps_its_offset_until_the_clock_trigger_clears_it`.

### P1 (first part) — the gate (`seq.gate`)

Not in the design (decision 5 put gate length "later"): without it a
gate-mode envelope fired by the sequencer would hold its sustain until
the transport stopped. Each fire passes `gate = seq.gate × one step's
seconds` at the clock's bpm and span (`Sequencer.gate_seconds`, unswung),
so a gate-mode envelope releases on its own half a step later by default.
One-shots ignore it. It is one global value, not per step
(`tests/test_plan31_wiring.py::test_a_step_releases_a_gate_mode_envelope_after_half_a_step`,
`::test_the_gate_follows_the_bpm_and_the_gate_param`,
`::test_a_one_shot_ignores_the_gate`).

### U1 — the LFO page for N strips (`ui_lfo.py`)

- Four LFOs draw as before (`tests/test_ui_lfo.py::test_four_lfos_do_not_fold_and_still_fit`).
- **Above four**, every strip but the selected one folds to one line: a
  one-cycle thumbnail (17 points), the name, the live output as a bar, a
  chevron that opens it. Exactly one strip is open, the full 129-point
  scope drawn only there. The selection is the Panel's (`_lfo_open`),
  for the session, never saved; a new LFO is selected as it is added.
  The page child scrolls when the strips overflow
  (`::test_sixteen_lfos_scroll_and_one_is_open`).
- `+ lfo` is disabled at the cap with a tooltip; add and remove are one
  undo step each (`::test_add_and_remove_through_the_chips_are_undoable`).

### U2 — the SEQ page (`ui_seq.py`)

After LFO in `ui.PAGES` (`("seq", "seq", ("seq", "env"))`), so the
control window has sixteen pages. A function over the Panel, like
ui_lfo. Top to bottom:

- **The transport**: `run` (lit while running), the span picker,
  `restart` (`seq.trigger`), then flush right the beat light and
  "step 3/8" (or "stopped"); `length` and `swing` as two half faders.
  `seq.gate` is not on the page (a rough edge, below).
- **The grid**: 5 × 8 cells, **48 px tall and as wide as the page
  allows up to 48** (`min(48, fit)`: 36 px at the control window's
  960 × 900), 4 px apart, in the APC40's LED palette: off dark, **on
  green**, on in a muted lane **red**, a lit step under the playhead
  **yellow**. The playhead's column is tinted and framed in the one red
  (`ui.RED`), and only while running. **Columns past `length` are dimmed
  to 30 % and take no click.** The step numbers over the grid set the
  length (the APC's clip stop k). Each row's label: the lane number (a
  click selects the lane and opens its envelope), **M** (mute), and an
  envelope picker over the bank's ids (`seq.<l>.env`), in the warning
  colour when it names a removed extra. A click is an ordinary param
  write (undo sees it); right-click on a cell gives the usual menu, Learn
  included.
- **The envelopes**: a strip per envelope id. One is open — the selected
  lane's envelope unless another was opened since — with the AHDSR shape
  drawn from the knobs and a dot at the live level, mode · sync · retrig,
  and A/H, D/S, R/curve, amount/velocity as half faders; its head says
  which lanes fire it, the stage and the output, with `+ env`, `gate`
  and (extras only) `×`. The rest fold two to a line (thumbnail, name,
  level bar). `+ env` and `×` are one undo step; envelopes 1–5 are
  refused.
- The default page fits the control window without a scroll
  (`tests/test_ui_seq.py::test_the_default_page_fits_the_control_window`);
  no conflicting ids with 0, 3 or 11 extras (`::test_no_conflicting_ids`).
  Without a sequencer the page says so.

### G1 — GRAPH (`graphview.py`, `ui_graph.py`)

- **Kinds** `env` and `seq` in `graphview.KINDS`, both in the MODULATION
  area (`AREA`, with `group:env` and `group:seq`), both idle while
  unrouted (`IDLE_KINDS`), no placeholder device (`NO_DEVICE`).
- **Bank nodes by id**: `bank_ids(router, reg, scheme)` is a list, so
  ids keep their gaps (`_lfo_count` is gone). A voice's node is
  `lfo.<n>` / `env.<n>`, its params as inputs, its lane as its output.
- **The sequencer is one node**, "sequencer", its params as inputs and
  five trigger outputs `lane 1`–`lane 5` (group "lanes").
- **The lane cable** (a new cable kind, `lane`): each lane's envelope
  binding drawn from its pin to that envelope's `fire`, labelled "lane 1
  fires env 1", **only for a lane that can fire** (a step on, or the
  sequencer running), faint with "(muted)" or "(stopped)". It is no row:
  **dragging a lane's pin onto another envelope's `fire` base stub
  rebinds the lane** (`Edit.bind_lane`, a write of `seq.<l>.env`); a drop
  onto the envelope it already fires is refused ("lane 1 fires env 1
  already"); **Delete on it is refused** ("a lane always fires an
  envelope: drag its pin onto another envelope's fire to rebind it").
  A lane bound to a removed envelope draws no cable. A route *from* a
  lane (onto `mod`) is an ordinary route.
- **Add and delete**: the canvas picker gains "LFO" and "envelope"
  (`ui_graph.add_voice`, through the bank, one undo step, greyed with the
  reason at the cap); the node menu's delete and the Delete key on an
  LFO or an extra envelope go through the bank (the routes on its lane
  stay, dormant); a lane envelope 1–5 is refused before any undo step
  ("… is a sequencer lane's envelope: it stays").
- **Positions** of the LFO, envelope and sequencer nodes are the
  preset's (`OWNERS`), since a bank's membership is preset content.
- **Tests.** `tests/test_graph_seq.py`, notably
  `::test_a_lane_with_a_step_on_is_a_binding_cable_to_its_envelope`,
  `::test_a_lane_rebinds_by_a_drag_onto_an_envelopes_fire_and_cannot_be_deleted`,
  `::test_bank_ids_keep_their_gaps`,
  `::test_a_lane_envelope_is_refused_an_extra_one_goes`,
  `::test_the_picker_adds_an_lfo_up_to_the_cap`.

### P1 — the conditional `hyperspace.preset/3`, `seq-demo`, the goldens

- **`preset.schema_of(doc)`** writes `/3` only when the document carries
  what a build from before plan 31 would silently lose on a re-save: a
  bank membership key (`lfos` other than the four, `envs` with extras),
  an `env.*` / `seq.*` value, or a route, modifier input or macro
  subscriber naming an `env`/`seq` lane or param. **Otherwise it is `/2`
  and carries no `env.*` / `seq.*` value at all** — they are left out
  when every one is at what a load would land for it missing
  (`Presets._uses_v3`, floats compared to 1e-9) — so it is byte for byte
  the file an older registry writes. A `/3` file carries every envelope
  and sequencer value, as every other group's.
- **Load** takes `VERSIONS = (2, 3)`; `/2 → /3` is the identity. An
  older build refuses a `/3` file through `Library.read`'s versions
  ("schema … is not a hyperspace.preset") rather than strip it.
  ENGINEERING's shared-library section says both Macs must be on this
  build.
- **`seq-demo`**, a factory preset (`FACTORY_PRESETS`, `desk=None`):
  half a bar (16ths), kick on lane 1 steps 1 and 5, snare on lane 2
  steps 3 and 7, hats on lane 3 every step; envelopes 1–3 one-shot with
  sustain 0 (kick 5 ms / 300 ms, snare 5 ms / 180 ms, hat 2 ms / 70 ms).
  Routes: `env:0 → view.bright` push 0.5, `env:1 → camera.zoom` push
  0.06, **`env:2 → fx.deconverge.amount`** push 0.5 (the design said
  fx.mix; the deconverge's base amount is 0, so it shows only on a hat),
  over a dimmed `view.bright` 0.6. It is a `/3` file. **`seq.run` is
  not in it**: the pattern plays once the performer presses run.
  It is in no show's bank.
- **Tests.** `tests/test_plan31_wiring.py`,
  `::test_an_untouched_preset_saves_as_2_without_an_envelope_or_a_step`,
  `::test_anything_an_older_build_would_lose_saves_as_3`,
  `::test_a_3_round_trips_and_a_2_after_it_puts_the_defaults_back`,
  `::test_this_build_reads_both_and_an_older_build_refuses_a_3`,
  `::test_2_to_3_is_the_identity`,
  `::test_seq_demo_is_the_pattern_and_plays_once_play_is_pressed`.
  The desk coverage report gains seq-demo's row (15 dark or dead, 0 of
  24 presets meet the bar).

### A1 — the APC40 sequencer page (`seq_page.py`) — on `plan-31-a1`, pending Dylan

Built and tested on `plan-31-a1` (9e2e4f0, then 0d6c00a after merging
`plan-31-integration`), **not merged** into `plan-31-integration`: the
desk is Dylan's (DECISIONS "the APC40 map … Dylan's"), and decision 10
waits for his sign-off. What it is, read from `git diff
plan-31-integration...plan-31-a1`:

- **A surface page, not a layer.** `Bindings.page` (an object with
  `rows()`), `page_rows`, `page_serial`, `set_page`. While a page is up
  on the first MIDI role's desk, its rows **shadow every row on their
  controls on both layers, invariant ones included** (`dispatch` and
  `active` check the page first; a disabled page row does nothing). They
  are in memory only — never in `table.bindings`, never saved — and
  `is_invariant` says a page control is taken while up, so no Learn
  takes one (`ui_desk.click` / `mappable` refuse it: "the sequencer page
  owns this").
- **Entering and leaving.** `seq.page`, a session toggle (group `desk`,
  not saved, not modulatable), on **SEND A (note 0x58), latched**, an
  invariant row of `apc40.DEFAULT_MAP` (`bindings.default.json`
  regenerated). An older `bindings.json` gets it through
  `routing.APC_NEW_ROWS`; one whose own row holds SEND A gets a note at
  every launch (`seq_missing`, beside `save_missing`). Until the
  sequencer's params exist SEND A does nothing. **A preset load does not
  leave the page**; the grid redraws to the loaded pattern.
- **What the page owns**: clip rows 1–5 × 8 (lane l's steps, `toggle`
  on `seq.<l>.<s>`; a column past `length` disabled), clip stop 1–8
  (`set seq.length = k`), scene launch 1–5 (`set seq.select = l` for
  another lane, `toggle seq.<l>.mute` for the lane already selected).
  `seq.select` is a session enum in group `desk`. Everything else —
  faders, knobs, SHIFT and its layers, the transport, TAP/NUDGE, QUANT,
  OVERDUB, the track strips, STOP ALL, MASTER — is as it was.
- **Lights**, one rule, `routing.led_shade(b, p)` → `off · on · hit ·
  muted · held`, read by both `MidiIO.feedback` and `ui_desk`; the
  profile turns a page shade into a velocity (`apc40.SHADE`,
  `shade_of`): a step on GREEN; in a muted lane RED; under the playhead
  on an unmuted lane YELLOW; clip stop k lit while the playhead is in
  column k (dark while stopped); scene k lit for the selected lane,
  **blinking (velocity 2) for a muted lane**; columns past `length`
  dark. The rows are rebuilt only when the lane selected or the length
  changes, each control keeping its last sent light, so the playhead
  sends only what changed (the existing `last_out` gate).
- **midi.py**: `page_serial` is the fourth of `_serials`, so a flip
  redraws the whole desk from the params with nothing cached; going up
  **drops the hold timers and blinks on page controls** (`_drop_page_holds`),
  so a bank pad held across SEND A cannot save; a power cycle and a hot
  reload re-send the page's rows too.
- **On-screen desk** (`ui_desk`): `page_serial` and the rows in `_key`, a
  header line **"SEQ · lane 2 · L=8"** (the design's span is not in it),
  each page control's words ("L1·3", "lane 2", "mute 2", "L=5").
- **Tests** on `plan-31-a1`: `tests/test_seq_page.py` (14), e.g.
  `::test_send_a_enters_and_the_grid_redraws_from_the_steps`,
  `::test_a_pad_toggles_a_step_and_loads_no_preset`,
  `::test_clip_stop_sets_the_length_and_clip_stop_8_does_not_save`,
  `::test_scene_1_selects_then_mutes_and_leaves_the_render_toggles`,
  `::test_an_advancing_playhead_sends_only_the_diff`,
  `::test_leaving_restores_the_bank_the_toggles_and_save`,
  `::test_a_bank_pad_held_across_send_a_never_saves`,
  `::test_shift_inside_the_page_moves_the_knobs_not_the_grid`,
  `::test_learn_never_takes_a_page_control`,
  `::test_a_power_cycle_with_the_page_up_resends_the_page`,
  `::test_older_files_get_send_a_unless_it_is_taken`.

Not built: **A2**, D5–D8 as the selected lane's A/D/S/R through
`seq.sel.*` proxies.

## The goldens

**621 goldens, 147 distinct pictures**, on "Apple M3 Max" (GL_VERSION
"4.1 Metal - 90.5"). **The 596 recorded before this plan match byte for
byte** (the design's golden rule: four LFOs, envelopes
resting at 0 and unrouted, the sequencer stopped). The 25 new ones are
`seq-demo`'s: a 24th factory preset in the nine states with hands absent
and present, the two `solo` states and the five depth / in-scene states
(`24 × 2 × 9 + 7 × 2 + 1 + 24 × 5 + …` in
`tests/test_golden_frames.py`); 9 distinct pictures, 7 of them new PNGs.

The golden rig (`tools/golden_frames.py`) now registers and steps the
envelopes and the sequencer through the router as the app does — at
rest and stopped, so no other preset sees them — except for the presets
in `RUNNING` (`seq-demo`), drawn with run pressed and the pattern
restarted as the rig starts: step 1 fires on the first frame, and the
hashed frame, about 117 ms later at 120 BPM, is mid-envelope on the kick
(the hat that fired with it is over, the snare still to come). The
manifest records `"sequencer_running": ["seq-demo"]`. How to diff and
re-record is in [`26-render-graph.md`](26-render-graph.md), "How to
re-record".

## What no person has verified

Everything. Every proof is headless: the tests on a deterministic
clock, the goldens at one pinned moment, the panel drawn on a headless
imgui context. In particular:

- **The LFO page at 7 and at 16 LFOs** (280): the folding, the open
  strip, the scroll and the cost of sixteen scopes in the live app.
- **The SEQ page at distance** (281): 36 px cells, the yellow playhead
  against green, the dimmed columns past `length`, the folded
  envelope strips' micro text.
- **`seq-demo` against real music** (282): whether 16ths fired at the
  exact step time *feel* tight at 120–175 BPM — the tests prove the
  time, not the feel — and whether the kick on brightness reads at all
  on a projector.
- **The global trigger re-aligning the grid** on a running pattern with
  synced LFOs (283), and the per-sequencer restart leaving the LFOs.
- **The GRAPH lane cables** (284): the drag onto a `fire` stub, the
  refusals, the faint stopped and muted cables — the tests call the
  functions, never a mouse.
- **Two Macs on one library** with a `/3` preset (285): no test runs an
  older build.
- **The APC40 page, all of it** (286–295, on `plan-31-a1`): the fake-port
  rig proves the messages, never an mk1 — yellow over green, the mute
  blink on a scene button, no flicker at 180 BPM 16ths, the 24 bank pads
  relit, a power cycle, a desk fallen back to Generic mode (where SEND A
  is a toggle the device keeps).
- **Frame time** with 16 LFOs and 16 envelopes: S0's baseline was never
  run as its own WP; nothing has measured the patch rebuild or the
  frame at the caps.

## Known rough edges

- **`seq.gate` is not on the SEQ page.** It is reachable from ROUTING,
  GRAPH, Learn or a preset; the transport line has length and swing only.
- **A lane can point at a removed extra.** The lane then fires nothing;
  the SEQ page's picker shows it in the warning colour and GRAPH draws no
  cable, but nothing else says so.
- **Removing an LFO or an envelope leaves its routes dormant**, by design
  (ids never compact). A later add takes one past the highest, so a
  removed top voice's id *is* reused by the next add, and a route left on
  it comes back to life on the new voice (the rule protects only ids
  below a standing voice).
- **Several notes on one envelope** within a gate share one voice
  (legato by default): two lanes pointed at one envelope re-attack it
  rather than layering.
- **Swing moves odd steps only**, by one global amount; per-step velocity,
  gate length and probability, per-lane length and 16/32-step pages are
  not built (decisions 5, 6).
- **Stopping releases every lane's envelope**, even one a route or the
  panel is holding open through `env.<n>.gate`.
- **A `/3` preset is refused by an older build** with a message about the
  schema, not about the sequencer; a person sees only that the preset will
  not load there.
- **The first launch after B needs a restart** (the design's warning): a
  hot reload would re-class an `LFOs` object from before the bank, whose
  voices were a plain list (`lfos` is a property now); not tried at the
  machine.
- **The A1 header drops the span** ("SEQ · lane 2 · L=8"), and the page
  is the first MIDI role's only: a second APC40 has no sequencer page.
- **The registry grows**: six params an LFO, thirteen an envelope, 57 for
  the sequencer (40 steps, five mutes, five envs, span, length, swing,
  gate, run, step, trigger); Learn menus and target combos are longer.
- **`seq-demo` carries no desk** (`desk=None`), so loaded at the machine
  its APC40 preset layer is dark (the desk is Dylan's).

## The design, as agreed (2026-10-22), corrected where the build differs

### The shape in one paragraph

A **modulator bank** (`modbank.py`) holds voices with stable ids. It
follows the plan 28 N1 modifier precedent: params are declared at
runtime, ids are one past the highest, and the bank is undoable and
saved in the preset. The LFOs became one bank, of any size up to 16.
**Envelopes** (`envelope.py`, AHDSR) are a second bank, `env:<n>`.
They are event-driven, so a fire stamped with a sub-frame time renders
exactly. A **sequencer** (`sequencer.py`, `seq`) reads its position
straight off the tempo clock. Its steps are registry params. It steps
inside `Router.modulate` after every bank's `begin`, fires each lane's
envelope with the step's exact time, and publishes `seq:<lane>`
trigger lanes so a lane can fire anything else too. On the APC40 a
**sequencer page** (SEND A) shadows the clip grid, clip stop and scene
launch while it is up, and everything else stays live (on `plan-31-a1`).

### B — the modulator bank (N LFOs)

- **`modbank.Bank`** owns stable 1-based ids (add / remove / `next_id` /
  cap 16), params declared through the kind's `declare` (remove the
  prefix, re-declare: `reg.serial` moves and the patch rebuilds), the
  preset/undo doc, publishing with NaN in a gap, and the late-trigger
  hold.
- **Voices.** `LFO` and `Envelope` implement only their `step` and their
  `restart` / `fire`.
- **Addresses do not change**: `lfo:<n-1>`, params `lfo.<n>.*`; ids never
  compact.
- **Router and patch.** *Built as* `Router.use_bank` per bank (`use_lfos`
  kept as a wrapper), `routing.BANKS`, plan steps `("bank", scheme, i)`.
- **In the preset**, `"lfos": [ids]`, written only off `[1, 2, 3, 4]`.
- **Undo** holds bank membership beside the modifiers.
- **Hot reload.** *Built as* nothing to change: the reload targets were
  already a lambda.

### E — envelopes (`env:<n>`, params `env.<n>.*`)

- **AHDSR**, hold defaulting to 0 (its knob bottom), `mode` gate |
  one-shot; knobs as in E1 above, all registry params.
- **Output** rests at 0.0 (`rests["env"]`); a negative row depth pushes
  down. Peak = `amount · (1 − vs + vs · vel)`.
- **API** as designed: `Envelopes.fire(n, *, at=None, velocity=1.0,
  gate=None)`, `Envelopes.release(n, *, at=None)`. *Built with* `fire`
  and `gate` as patch inputs too, and `gate=` a length in seconds.
- **The bank holds 5 lane envelopes (1–5) plus extras** up to 16 voices
  (decision 3), the five re-added by `parse`.

### S — the sequencer engine (`sequencer.py`)

- **Naming.** "patterns" is the face shader's; the module is `seq` /
  "Sequencer".
- **Model.** 5 lanes × 8 steps, `seq.<l>.<s>` toggles stored as
  velocities; `seq.<l>.mute`; *built with* `seq.<l>.env` (a lane can
  fire any envelope, default its own); `seq.span`, `seq.length`,
  `seq.swing`, *and* `seq.gate`; `seq.run` and `seq.step` never saved;
  *and* `seq.trigger`.
- **Why steps are params**: the pad is a plain `toggle` row with LED
  feedback, and Learn, undo, the preset and ownership come with it.
- **Position** `s(t) = (clock.beat(t) + shift) · steps_per_beat`.
- **Firing** every crossed step at its exact t_k; odd steps swung; a stall
  fires only the current step; `set_bpm` needs nothing; a backward nudge
  never double-fires.
- **Re-align** on `Clock.epoch`.
- **Transport**: `run` gates firing only; start waits for the next
  boundary; stop releases.
- **Output**: `envs.fire(lane.env, at=t_k, velocity=v, gate=…)`, and the
  `seq:<l>` trigger lanes resting at 0.
- **In the preset**: `seq` and `env` in `PERFORMANCE_GROUPS`; pattern
  slots are `seq` module presets; undo watches the steps (taps inside
  undo's 0.4 s settle merge into one step).

### A — the APC40 sequencer page

As designed — a page, not a third layer (invariant rows win `dispatch`
and `active`; layers spread into Learn, desks and GRAPH); in-memory rows
that shadow every row on their controls; SEND A latched; hold timers
cleared on entering; clip rows 1–5, clip stop and scene 1–5 owned; the
rest live — with these as built (above): the LED table is `led_shade` +
`apc40.SHADE`; `seq.select` is the lane's param; the header has no span.
**Phase 2** (D5–D8 as the selected lane's A/D/S/R) is not built.

| State | LED |
|---|---|
| Step on | GREEN |
| Step on, lane muted | RED |
| Playhead on a lit step | YELLOW |
| Playhead | the lit clip stop in its column |
| Scene k | lit = selected lane, blink = muted |
| Columns past `length` | dark, and inert |

### U — panel and GRAPH

- **LFO page**: N strips, `+ lfo`, `×`; above 4 strips each folds to one
  line.
- **SEQ page** (`ui_seq.py`, after `lfo` in `PAGES`): *built with* cells
  48 px tall and up to 48 wide (36 at the control window; the design said
  52 px), the LED palette, the playhead column in `ui.RED`, click to
  toggle, right-click for Learn, one envelope strip open and the rest
  folded, `+ env`.
- **GRAPH**: kinds `env` and `seq` in MODULATION, idle rules, id lists,
  delete and picker entries, positions in the preset's layout, the
  sequencer one node with five trigger outputs, the lane → envelope
  binding a cable — *built* editable by a drag, never deleted.

### P — presets, schema, library

- **Conditional `hyperspace.preset/3`**, written only when needed; load
  accepts `(2, 3)`; `/2 → /3` the identity; an older build refuses.
- **Factory `seq-demo`**: kick, snare, hats at ½ bar; *built* onto
  brightness, zoom and the deconverge (not fx.mix); goldens at a fixed
  clock t, play pressed.
- **Docs**: both Macs on one library on this build (ENGINEERING).

## Work packages

| WP | Size | What | Status |
|---|---|---|---|
| S0 | S | Baseline: golden count, frame time with 4/16 LFOs + 16 envs, patch rebuild cost | not run as its own WP (the golden count is above; no frame-time measure) |
| B1 | M | `modbank.py`; LFOs as a bank of N; router/patch generalised to banks; preset `lfos`; undo; hot reload | built (4822e97) |
| E1 | M | `envelope.py`: AHDSR, exact `at=`, gate/one-shot, beats sync, legato/reset | built (a3dc6b6) |
| S1 | L | `sequencer.py`: clock-locked stepping, swing, epoch re-align, run, `seq:<l>` lanes; `Clock.epoch` | built (e833983) |
| W1 | M | the `env` bank, `use_sequencer`, the app's wiring (split out of E1/S1) | built (d1a71c2) |
| P1 | M | `seq.gate`; conditional preset/3; `seq-demo` + goldens | built (99731e4, 0356320) |
| U1 | M | LFO page with N strips | built (f26ea8d) |
| U2 | M | SEQ page | built (006911a) |
| G1 | M | GRAPH: `env`/`seq` kinds, picker/delete, id lists, layout keys, lane cables | built (23df7fb) |
| A1 | L | APC40 sequencer page | built on `plan-31-a1` (9e2e4f0, 0d6c00a), **pending Dylan** |
| A2 | S | D5–D8 selected-lane AHDSR | not built |
| D1 | M | the docs | this commit |

### Tests (the headline ones, as built)

- **Bank**: `tests/test_modbank.py` (add / remove / next_id / cap; a NaN
  gap; LFO 3 keeps `lfo:2`; undo; an old preset loads four).
- **Envelope**: `tests/test_envelope.py`, `tests/test_envelope_boundary.py`.
- **Sequencer**: `tests/test_sequencer.py`, on `Clock(now=…)`.
- **Wiring, presets, `seq-demo`**: `tests/test_plan31_wiring.py`.
- **Pages**: `tests/test_ui_lfo.py`, `tests/test_ui_seq.py`.
- **GRAPH**: `tests/test_graph_seq.py`.
- **APC page** (on `plan-31-a1`): `tests/test_seq_page.py` on the
  fake-port rig.

## Risks (as they stand)

- **Dylan's area.** A1 touches `apc40.DEFAULT_MAP`, `dispatch`, `active`,
  `feedback` and `ui_desk`: it stays on its branch until he agrees.
- **Registry growth** and **frame time**: see the rough edges; nothing
  has measured the caps.
- **Numbering.** Register rows 311–320 and hand checks 277–292 were
  assigned on `plan-31-integration`, after plan 28/30's 310 and 276; when
  `plan-28-30-integration` brought in `main`'s instanced field (its checks
  renumbered to 277–279, its guide entries to L136–L138), plan 31's
  checks moved up to 280–295 and its guide entries from L136–L141 to
  L139–L144. The register rows did not move.

## Decisions for the owner — all accepted 2026-10-22

Each was accepted as recommended; register rows 311–320 record each with
what was built against it.

1. **Replace "Four LFOs" with "N LFOs, cap 16", removable by stable id.**
   Accepted (row 311).
2. **Envelope type: AHDSR, with gate and one-shot modes**; hold 0,
   legato, seconds (beats one enum away), one shared curve. Accepted
   (row 312).
3. **Lane envelopes 1–5 always exist, each bound to its lane, plus up to
   11 extras.** Accepted (row 313).
4. **Steps as registry params.** Accepted (row 314).
5. **Per-step data in v1: on/off only**, stored so it can become
   velocity; swing one global value. Accepted (row 315); a global gate
   length (`seq.gate`) was built beside it.
6. **One global span and a global length 1–8.** Accepted (row 316).
7. **APC entry: SEND A, latched.** Accepted (row 317); scene 1–4's render
   toggles are shadowed while the page is up, amending D6; a preset load
   does not leave the page.
8. **The pattern is in the preset; `run` is not.** Accepted (row 318).
9. **Conditional preset/3.** Accepted (row 319).
10. **A1 only after Dylan agrees.** Accepted (row 320): A1 is built on
    `plan-31-a1` and waits there.
