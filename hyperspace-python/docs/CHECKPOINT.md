# Checkpoint — 2026-10-04

Where the Python re-platform stands and what to pick up next. This
revision describes the **`finish-line`** branch with plans 15 and 16 on
it (`plan-15-integration`, then `plan-16-integration`, each merged into
it when its last PR is in), and **`plan-18-integration`** on top of it:
plan 18 whole (the interaction box, knob smoothing, what a hand Learn
lands with, `hands-orbit`) together with plan 17's three merged code
packages (One Unbind, Learn desk / hand, the ROUTING filter), whose own
documents are still to be written by plan 17's docs package. It merges
into `finish-line` when both are documented; `main` is at plan 14 (fa9b3a1) and nothing from
plans 15–21 touches it until the owner merges `finish-line` (decision
30). What the
system *is* — the parts, the frame, who may write a parameter — is
[`ARCHITECTURE.md`](ARCHITECTURE.md); how it behaves is
[`ENGINEERING.md`](ENGINEERING.md); why it is that way, dated, is
[`DECISIONS.md`](DECISIONS.md); what drifted and how each item was closed
is [`AUDIT-2026-09.md`](AUDIT-2026-09.md); the stages it was built in are
[`plans/`](plans/README.md). This file keeps only the pick-up list.

## How to pick this up

```bash
git clone github.com/Cutaiar/hyperspace && cd hyperspace/hyperspace-python
uv sync                 # whole environment, from the committed lockfile
git checkout finish-line      # plans 15–21 land here, never on main
uv run pytest           # 1178 pass, 1 skipped (the hands tape) with plans 15 and 16;
                        # 1259 pass, 1 skipped on plan-18-integration (plan 18, and plan 17's code)
uv run hyperspace       # the app: ? shows the controls cheat sheet (off at launch)
```

Machine prerequisites: [`SETUP.md`](SETUP.md). Rig-specific values live in
`~/Hyperspace/config.toml` (documented in `hyperspace/config.py`).

## Where it stands

Plans 00–10 are done and described in the documents above, not here. Plan
11 (2026-09-27/28, [`plans/11-remediation.md`](plans/11-remediation.md))
closed the September audit register: a hand leaving the box releases its
rows (B1), hot reload watches every module and keeps `Kind` identity
(H1–H4), one scene store and layouts on saved band presets (A1, A2), one
Learn object shared by MIDI and hands (B3, B4), one preset system with
routing presets in the library (L1–L3, L5, L6, L8), exact trigger phase on
every path (B6–B8), and one tidy-up sweep per component with the missing
boundary and loop-order tests (R, N, V, A, L, U, P) — PRs #40–#54, one
per work package, each code-reviewed, integrated on
`plan-11-integration` (which is what the owner merges). Seven
decisions are the owner's and pending (plan 11 §2, rows 1–7: B2, B5, R1,
R6, A7, A10, R2+L2); the trim fix (A10) and the keys-into-the-table change
(R2+L2) wait on them. (Those seven were answered on 2026-09-28 and built;
plans 11 and 12 are merged, main 4bffa9d.)

Plan 13 (2026-09-28, [`plans/13-preset-and-session.md`](plans/13-preset-and-session.md))
is built on `plan-13-integration` (PRs #61–#66, the WP6 docs PR to
come; 872 tests): the five nouns for saved state are two — a **preset**
(`library/presets/*.json`, `hyperspace.preset/2`: every performance
value, the routes, the APC40's preset layer, the macros) and the
**session** (`config.toml`, `hands.json`, `bindings.json` — now only
the session's controls — and the project, `hyperspace.project/2`: its
session values, a startup preset and F1–F8 as a bank of preset names).
Themes, routing presets and the routing strip are gone; the APC40 has
two layers under a latched SHIFT (the band strip behind it); a macro
acts through base and depth subscribers; Learn writes into the loaded
preset and never a file; the ROUTING page is one page over the loaded
preset; the first launch migrates an older home once, backing up every
file it rewrites. Pending: hand checks group H and decision 20 (hand
routes by name). (Since merged as PR #69; decision 20 answered and built,
PR #70.)

Plan 14 (2026-09-29, [`plans/14-party-rig.md`](plans/14-party-rig.md);
merged, PR #77, main fa9b3a1) made the rig a party device: an opaque
render window for the Pepper's Ghost glass, the stall log and red
banner, the `party` show as what opens, the PRESETS page, every effect
in a factory preset, echoes in seconds with the dream on, the desk drawn
with glyphs. Its §6 is the owner's to-do list at the machine. The ghost
hands (PR #78) are on `finish-line` ahead of plan 15.

Plan 15 (2026-10-04, [`plans/15-safety-net.md`](plans/15-safety-net.md),
its §8 "As built"; from the Oct 3–4 session, decisions 26–29) is the
safety net, on `plan-15-integration` → `finish-line`:

- **Undo** (WP1, PR #82): ⌘Z / Ctrl+Z, ⇧ to redo. One step per gesture
  (a drag, a knob turn, a typed value) or per replacing action (a load,
  a Learn, an Unbind, a delete, Replace), found by comparing the bases
  and the loaded preset's table once a frame; a hand, a band or an LFO
  makes no step; a restore sets only what differs. `undo.py`,
  ENGINEERING §5b.
- **The trash** (WP1): a user preset file a save or a delete would
  destroy is copied to `<home>/trash/` first.
- **Home** (WP2, PR #83): the Home key and the APC40's OVERDUB load the
  show's "starts on" preset.
- **The master dim** (WP3, PR #81): the crossfader dims the finished
  frame, left black, right full; never saved, 1 at launch; a preset load
  no longer loosens a fader whose param it did not move.
- **Save-as on the desk** (WP4, PR #87): a hold of 0.6 s on the
  clip-stop row saves a new preset ("TRIP 2") into the next empty slot;
  the desk never overwrites. A bank slot's right-click menu on the
  PRESETS page has "put preset here…" and "clear slot".

None of it has been tried by a person at the rig. It was shown by tests
(1121 pass), offscreen renders, headless demos under
`plans/assets/15-safety-net/`, and a scripted launch of the app on a
laptop. Eleven forks were settled by the unattended run on its own
recommendation and wait for the owner: `DECISION-REGISTER.md` rows
34–44.

Plan 16 (2026-10-04, [`plans/16-paper-cuts.md`](plans/16-paper-cuts.md),
its §7 "As built"; from the same session, no decision asked of the
owner) is the paper cuts, on `plan-16-integration` → `finish-line`. It
adds no param, page or menu item; one config key and one file in the
home:

- **The cheat sheet is off at launch** (WP1, PR #89); `/`, the pad's
  MENU and the APC40's DETAIL show it. The desk diagram stays, in the
  bottom-left corner.
- **An FX chip's name opens the effect; a dot at its left end switches
  it** (WP2, PR #84). Three chips to a row. The open effect is a name
  (`FxState.select` / `selected`), so a reorder or a preset load never
  changes it.
- **An effect that is not running says why** (WP3, PR #86): off,
  bypassed, FX mix 0, its mix 0, with "turn on" / "effects on"; its
  controls are dimmed by a veil and stay live.
- **The windows open where the config says, else where they were**
  (WP4, PR #85): `[output] monitor` and the new `control_monitor`, then
  `<home>/windows.json`, written on quit and ⌘R; fullscreen is never
  remembered. `placement.py`, ENGINEERING §2.5.
- **Instances to zero** (WP5, PR #90): `view.instances` 0–100, "0 ·
  nothing drawn", the echoes and effects carry on. `dream.layer` is not
  modulatable.
- **Four follow-ups** (WP7, PR #92): a footer line said twice shows
  twice; a performer's round-off lights no dirty dot; the desk diagram
  is in its place on the sheet's first frame; a config screen that is
  not a number is −1 and a note, not a dead launch.

None of plan 16 has been tried by a person at the rig either. It was
shown by tests (1178 pass with it), pictures from a hidden window or an
offscreen render and transcripts under `plans/assets/16-paper-cuts/`,
and a scripted launch on a one-screen laptop — so **window placement has
never met a second screen**. Five calls were built on the run's
recommendation and wait for the owner: `DECISION-REGISTER.md` rows
45–49. Plans 17–21 are ordered in
[`plans/15-21-roadmap.md`](plans/15-21-roadmap.md); each plan document
is written when it starts.

Plan 18 (2026-10-04, [`plans/18-hand-and-knob-feel.md`](plans/18-hand-and-knob-feel.md),
its §7 "As built"; from the same session's "lower hand sensitivity",
"tame rotation" and the desk's stepping knobs) is hand and knob feel, on
`plan-18-integration`. It adds two session params, one optional key in
`hands.json` and one factory preset:

- **An interaction box** (WP1, PR #94): bounds on the palm in
  `hands.json` (schema 2; an old file is never rewritten at launch and
  is kept as `hands.json.bak-v1` before the first rewrite). The
  calibration sweep sets it, "reset ranges" opens it, the HANDS page
  draws it. A hand outside it is absent everywhere, its ghost included.
  **The box is off for the whole sweep: calibrate with nobody else in
  view.**
- **Knob smoothing** (WP2, PR #98): `desk.slew`, on SYSTEM under
  "midi". A knob's or fader's value arrives in a straight line between
  detents and rests where it always did. **80 ms in the running app**,
  settled by the run's orchestrator against the plan's recommendation of
  off (register row 54); a show that saved the number keeps it.
- **What a hand Learn lands with** (WP3, PR #100): a tilt lands as a
  `push` about the base at `hands.learn_depth` (0.25, HANDS, "feel &
  calibration"); height is still the fader except onto a range centred
  on zero; a learn takes the axis's other rows with it, a factory
  preset's included (one ⌘Z back). Existing rows and every preset file
  are untouched.
- **`hands-orbit`** (WP4, PR #97): a factory preset, the right hand
  orbiting the camera and the left panning and zooming it; in the list,
  on no F-key. Its zoom depth is 0.12, not the plan's 0.3.

None of plan 18 has been tried by a person at the rig, **and none of it
has met a camera, a real hand, a real sweep or an APC40**: it was shown
by tests on synthetic hands and fake MIDI ports (1259 pass with it and
plan 17's code), pictures from a hidden window and offscreen renders
under `plans/assets/18-hand-and-knob-feel/`, and scripted launches on a
laptop. Seven calls wait for the owner: `DECISION-REGISTER.md` rows
50–56. Plan 17's code is on the same branch and its documents are not
written yet; ARCHITECTURE and ENGINEERING describe Learn and Unbind as
they were before plan 17 except where plan 18 changed a sentence.

**Everything only the machine can verify** — plan 09's five hand checks,
plan 08's unverified list, plan 07's WP6c dream tuning, the first real
capture, the APC40, the second monitor, IAC + FL Studio, and the
eyeballing owed for PRs #24, #25, #26, the LFO page and the re-laid-out
HANDS page — is one numbered list with commands, presets, pass and fail:
[`plans/11-hand-checks.md`](plans/11-hand-checks.md). Do it in that order;
file what fails as new audit rows dated with plan 11.

## Not done — in rough priority order

1. **The hand checks** above. Nothing in them has been run by a person
   since plan 09 landed; B1's fix and the HANDS page re-layout (plan 11
   WP13 found it overflowing the panel by 216 px on any rig with hands
   enabled) are the two things most likely to look different. Plan 13's
   group H (checks 33–42, check 31 first) starts with the first launch
   on the new code, which migrates `~/Hyperspace` — copy it first.
   Plan 15's **group K** (checks 48–57) is the newest: before launching
   `finish-line`, `cp -R ~/Hyperspace ~/Hyperspace-2026-10-04`; do check
   57 first (that launch rewrites `bindings.json` once, with a backup:
   the crossfader, OVERDUB, the clip-stop row, Home and the undo keys),
   then 48, 50, 53 on the laptop, 49, 51, 54–56 with the APC40, 52 with
   the camera. Check 55 settles the one thing read from a comment: that
   the crossfader's left end is CC 0. Plan 16's **group L** (checks
   58–63, about 20 minutes): 58–60, 62 and 63 on the laptop, 61 with the
   projector — the first time window placement meets a second screen; if
   a window ever opens out of reach, delete `~/Hyperspace/windows.json`.
   Plan 18's **group N** (checks 72–80, about 40 minutes, the camera for
   all of it and the APC40 for 74, 78 and 79; 64–71 are kept for plan
   17's group M): **72 first** — the calibration sweep, which now sets
   the interaction box, done with nobody else in the camera's view —
   then 73 and 74 (a hand outside the box, a hand on the desk), 75–77
   (what a Learn lands with), 78 and 79 (judge the 80 ms of knob
   smoothing; SYSTEM → Knob smoothing turns it down or off), 80
   (`hands-orbit`'s directions and its zoom). Since a hand outside the
   box is now absent, every older check that needs a hand in the box
   (group C's, and the hand parts of the later groups) is run after 72.
2. **First real audio capture.** Every live path is code-complete and now
   under test over a fake device, but no human has pressed `M` on real
   hardware with the macOS microphone prompt. One click plus a clap
   (hand check 3).
3. **The owner's remaining decisions** (`docs/DECISION-REGISTER.md`).
   Rows 1–6 are answered and built (the trim is the per-band AUTO /
   MANUAL switch, plan 11 WP15); `R` / F1–F8 as table rows (row 7) and
   plan 13's forks (rows 9–13, 12b, 18, 19) are answered and built. Row
   20 (hand routes by name, audit N7) is open. (As of 2026-10-04: rows
   1–33 are all answered. **Rows 34–44 are the open ones** — eleven
   calls plan 15's unattended run built on its own recommendation, each
   to confirm or overturn, each with its cost to reverse: the undo keys
   and the chord rule, the band layout, taps, the trash's rules, the
   Home key, camera moves, performers on home and the dim, the dim in
   overlay, the save-as gesture, a drag that pauses, the faders after a
   load. **Rows 45–49 are plan 16's**, open the same way: the switch on
   an FX chip and three chips to a row, an idle effect's faders dimmed
   but live, the instance count reaching zero from the knob, where the
   windows open, the dream's layer no longer performable. **Rows 50–56
   are plan 18's**: the interaction box, a hand outside it absent
   everywhere, what a hand Learn lands with, a Learn taking the axis's
   other rows, knob smoothing on at 80 ms — the one built against its
   plan's recommendation — where the two new numbers live, and
   `hands-orbit`. Plan 17's rows follow, from its own documents.)
4. **The rest of the finish line**: plans 17–21 in the roadmap's order,
   each onto `finish-line`. Plan 18 is built and documented; plan 17's
   three code packages are merged beside it and its documents (its "As
   built", its register rows after 56, hand checks 64–71) are owed, then
   `plan-18-integration` goes to `finish-line`. Plans 19–21 are not
   started. One code comment is stale since plan 18:
   `hands/core.py`'s module docstring still says Learn "writes a
   `position` route". Nothing of plan 15's desk side has been on
   the APC40: the hold's timing, the clip-stop LEDs and the blink are
   from Akai's protocol table (hand check 56). One audit row is open from plan 15: R13 (a fader moved
   while its row is disabled stays caught and jumps).
5. **Plan 04 — booth hardware.** Blocked on access: the pure-Python
   Pro DJ Link spike against the CDJ-3000/XDJ-AZ (BLT+OSC is the standing
   fallback), ESP32+BNO055 IMU ingest (packet format specced in BLUEPRINT
   §3.4), Δt delay compensation + metronome calibration. The tempo clock
   deliberately syncs to nothing until then (DECISIONS).
6. **Instanced GPU field.** For a *live* field: per-instance rotation
   phases and true instancing (agent prototype measured 621–845 fps at
   N=100; 1–2 days). The synchronized-grid mode is the v1.
7. **Plan 05's rest** — MIDI clock from deck BPM and the FL-side fuser
   script; the bridge itself is built, off by default, and now has a line
   on the SYSTEM page.
8. **Plan 06's non-trim items:** tempo-locked shapers once DJ Link exists,
   real harmonic detection, a scrub bar. (Saveable scenes and per-band
   LFO knobs are covered by the JSON scenes and the routable LFOs.)
9. **Ideas parked:** per-cell (3-cell) grouping for cell-wise
   colour/pattern assignment.

## Decisions that govern future work

The full, dated list is [`DECISIONS.md`](DECISIONS.md). The ones a new
session trips over first:

- Full Python re-platform; the HTML is a frozen reference, never executed
  at runtime (BLUEPRINT §5). FL Studio connects only via the optional
  bridge (§3.6).
- Parity bar: geometry exact; audio behavioural; visuals judged by the
  owner's eye.
- One performer per parameter; scene-setters write the base; every
  continuous source reaches a param only through `Router.modulate`;
  `hands/core.py`, `hands/signal.py`, `lfo.py`, `tempo.py` and `undo.py`
  import nothing from the package (ARCHITECTURE §3, held by tests).
- A replacing action calls `undo.push(label)` **before** it changes
  anything (`load=True` when it changes what is loaded); undo is a
  scene-setter and never writes an offset or a file. Every later plan's
  new action does the same.
- Nothing from plans 15–21 goes to `main`; everything lands on
  `finish-line` through one integration branch per plan (decision 30).
- Plans 03/04 swapped (hardware unavailable). The DJ Link spike is the
  first thing to do when deck access exists — it is the only genuine
  unknown in the stack.
