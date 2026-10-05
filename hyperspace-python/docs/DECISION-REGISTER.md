# Decision register — everything that is yours to decide

As of 2026-10-04. **Rows 1–33 are answered** (26–33, from the Oct 3–4 session, on 2026-10-04; Part A4). Rows the unattended run of plans 15–21 adds after 33 are built on its recommendation and wait for you to confirm or overturn (the answer sheet at the end). **Plan 15 added rows 34–44** (Part A4, after row 33).
implementing and settling the open work is here, whichever plan or session
raised it. Each entry stands on its own: what the thing is, what the software
does today, the options, a recommendation with its reasons, the trade-off you
accept, and what changes once you answer. The answer sheet at the end takes
one letter per row.

Sources folded in: plan 11 §2 rows 1–11, the plan 13 ledger (PR #56, rows
12–18), plan 12 §7, plan 13 §8, DECISIONS.md's pending row. Once you answer,
DECISIONS.md gets a dated row per decision and this file records the answer.

## Vocabulary, once

- **Parameter**: any setting with an id (brightness, an LFO's depth, tap
  tempo). Its **base** is what you set with a knob, key or panel. A
  **performer** (a hand axis, an audio band, an LFO, a DAW lane) adds an
  offset on top through one routing row per parameter.
- **Trigger**: a parameter that fires once (tap tempo, LFO reset).
- **Routing preset**: a saved set of performer rows, optionally with the
  bases they assume. **Theme**: a saved snapshot of every base. (Both are
  gone since plan 13, built on `plan-13-integration`: a preset holds both,
  and the questions below that use the words are kept as they were asked.)
- **Clock**: the tap-tempo clock the synced LFOs read. The **trigger
  button** (⇧B, the APC40's METRONOME) says "the one is now".
- Plan 13's two nouns, already decided by you on 2026-09-28: a **preset** is
  one file holding everything a performance moment is (every base, the
  performer rows, the APC40's preset layer, a label per module); a
  **session** is the rig boilerplate (the analyzer, the desk's fixed global
  layer, the startup preset). The APC40 gets two layers under a latched
  SHIFT: the **preset layer** the loaded preset maps, and the **global
  layer** the session fixes. **Invariant controls** (faders, preset-select
  row, SHIFT, TAP TEMPO, METRONOME, NUDGE ±, transport) mean one thing on
  both layers.

---

## Part A — the thirteen open decisions

### 1. B2 — does a tap ever move the downbeat?

**Recommendation: (a), a tap never moves the downbeat.**

**What it is.** You tap B or TAP TEMPO to set the tempo. You press the
trigger button to say "the one is now", which restarts every synced LFO
together. The question is whether a tap may also move the one.

**Today.** Until the first trigger press of the session, every tap moves
the downbeat to the burst's first tap. After the first trigger, a tap changes
only the tempo. Two rules depending on history; the decision log states only
the second.

| Option | What a performer feels | Trade-off |
|---|---|---|
| (a) A tap never moves the downbeat | Tapping is always safe; the picture never jolts until you press the trigger. On a fresh launch the swells are unaligned until the first ⇧B. | One extra press at the start of a set. |
| (b) Keep today's two rules, document them | No change on the desk. | The first burst after launch moves the picture; a later tap does not. Two behaviours for one button. |
| (c) The first tap of every burst moves the downbeat | Re-tapping re-aligns without the trigger. | Every re-tap mid-set jolts running LFOs, which the trigger button exists to prevent. |

**Why (a).** One rule, matching the decision already recorded; the trigger
button keeps its one job. Plan 12's `party-trip` preset is the first that
feels this: its quarter-note pump hiccups on every tap until the first
METRONOME press under (b).

**What changes.** A small edit in the clock, two tests flip, one sentence in
three documents. Lands on PR #42. Reversible in an hour.

### 2. B5 — which triggers may a performer fire?

**Recommendation: (a), keep all three modulatable.**

**What it is.** Any parameter can be owned by a performer unless flagged
otherwise. A performer on a trigger fires it each time its signal rises past
the on threshold. Three triggers are in question: tap tempo, the global LFO
trigger, and each LFO's own reset.

**Today.** All three are ownable. A pinch switch or an audio band can be
routed to any of them. Nothing ships routed that way.

| Option | What it allows | Trade-off |
|---|---|---|
| (a) Keep all three ownable | A pinch drops the LFOs on the one; a kick band re-triggers them; a pinch restarts one LFO. | A band routed to tap tempo would tap on every transient. Nobody has to route it. |
| (b) None ownable | Only keys, the APC40 and the panel can fire them. | The pinch switches lose their most natural use; the per-LFO reset stops being the gesture hook its docstring promises. |
| (c) LFO triggers ownable, tap tempo not | Everything in (a) except tapping from a hand or a band. | Tapping tempo with a pinch is gone. |

**Why (a).** The pinch switches exist so a pinch can be a button, and the
rising-edge trigger mechanism was built for exactly this. The one footgun in
(a) needs a deliberate routing to arm.

**What changes.** Nothing in code. One sentence moves from "not promised" to
"intended" in ARCHITECTURE; one decision row.

### 3. R1 — where are LFO knob settings saved?

**Recommendation: (c), theme state, and a routing preset may set the bases
it assumes.** Note: plan 13 dissolves this question, because a preset then
carries every base and every route in one file. Answer it anyway; it governs
the code until plan 13 lands.

**What it is.** Each LFO has five knobs. A theme snapshots every base. A
routing preset carries performer rows and may carry values, the bases its
rows assume. Today only the eight macro knobs are routing-layer state.

**Today.** LFO knobs are theme state. The factory routing preset that
demonstrates chaining writes four LFO values so its demo works; the factory
hands preset writes one effect value the same way; plan 12's `party-trip` and
`party-wake` do the same with LFO and dream values. That leaves the LFO
group's "unsaved changes" dot lit after loading the routing preset.

| Option | What it means | Trade-off |
|---|---|---|
| (a) LFO and tempo become routing-layer state | LFO settings travel with routing presets, never with themes. | A theme stops carrying "breathe at one bar"; the LFO page's own save/load strip becomes meaningless. |
| (b) Theme state; routing presets may only set macros | The routing file owns only its own layer. | The factory and party presets that assume LFO or effect settings silently depend on what you have set; their demos break. |
| (c) Theme state; a routing preset may set any base its rows assume | Every preset stays honest about what it needs; the lit dot is truthful. | A routing preset load can change a look. A test pins that every such value is a real, saved parameter. |

**Why (c).** An LFO arrangement is part of a look. A preset that assumes a
setting should say so. It matches how the hands preset already works and is
the shape plan 13 generalises.

**What changes.** One test and two document sentences. (a) instead is a
one-line code change plus moving the LFO strip, half a day.

### 4. R6 — what does an APC40 LED show under a performer?

**Recommendation: (a), keep it: rings show the base, LEDs show the state.**

**What it is.** A knob's LED ring shows a position; a button's LED shows on
or off. When a performer owns the parameter behind a control, the base (what
you set) and the effective value (what the show does) differ.

**Today.** Rings show the base, which is necessary: the knob uses soft pickup
and a ring that chased the performer would mean the knob could never catch
its own value. A button's LED on a toggle, or on an enum "set to X" row,
shows the effective value.

| Option | What the desk shows | Trade-off |
|---|---|---|
| (a) Keep the split, document it as intended | Ring = where the knob is. LED = what the show is doing. | Pressing a button on a performer-owned toggle changes the base and the LED may not change. Same as the panel, which shows base and effective side by side. |
| (b) LEDs show the base too | One rule for all feedback. | A lit button while the show does the opposite. |

**Why (a).** A ring is a pickup readback; an LED is a state light. The
asymmetry follows from what each light is for.

**What changes.** Prose only: one ARCHITECTURE sentence, the adapter's
docstring, one decision row.

### 5. A7 — the Dynamics fader's range past 1×

**Recommendation: (b), keep the range and document the split.**

**What it is.** The master Dynamics fader (0.06× to 4×, off at the bottom)
controls how much of the range a limiter took is put back. Inside the audio
chain it does two jobs: it blends between an absolute and a windowed
normaliser, and it scales the expansion ratio.

**Today.** The blend clamps the fader at 1, so from 1× to 4× only the
expansion keeps growing. The parity oracle that guards the chain is frozen at
0 and 1, where the two jobs agree.

| Option | Effect | Trade-off |
|---|---|---|
| (a) Cap the fader at 1× | The knob means one thing. | Every saved preset's fader position moves (positions are integer detents); presets need a re-map; the extra expansion above 1× is lost. |
| (b) Keep 4×, say what happens past 1× | Nothing moves; the tooltip says "past 1× only the expansion grows". | One knob still has two meanings, now written down. |
| (c) Two knobs, blend and expansion | Full control. | A new parameter on the audio page, every preset gains a field, the oracle must be re-frozen. |

**Why (b).** A tooltip and one sentence; nothing moves; the oracle stays
frozen. (c) is the honest fix if the double meaning ever bothers you at the
desk.

**What changes.** A tooltip, one ENGINEERING sentence, one decision row.

### 6. A10 — fixing the input trim

**Recommendation: (3), a per-band auto/manual normalisation switch.**

**What it is.** Each audio band has an input trim in dB, plus a master
trim. The chain then normalises each band adaptively, tracking a moving floor
and ceiling, so a static gain in front of it is mostly cancelled. To make
trim do anything the reference design applied it twice: before the envelope
and again after the trackers.

**Today.** On real material, cutting the bass band by 6 to 12 dB makes it
drive harder, and it only attenuates from about 20 dB down. Measured on the
reference: 0 dB gives 0.87 out, −6 gives 1.03, −12 gives 1.01, −20 gives
0.75. Fully off gives exactly 0. Ported on purpose for parity and frozen by a
bit-exact test. Open since plan 06.

| Option | How it works | Trade-off |
|---|---|---|
| (1) Bias the adaptive window in proportion to trim | The floor and ceiling shift with the trim so the gain is not cancelled. | Changes the reference path for everyone; the parity oracle must be re-recorded; no reference to check the new behaviour against. |
| (2) Trim as a multiplier after the normaliser | Trim becomes a plain output gain per band. | Same re-freeze; and a post-normaliser gain no longer moves the band against the gate and confidence thresholds, half of what trim is for. |
| (3) A per-band auto/manual switch | Auto keeps today's chain bit for bit. Manual bypasses the adaptive window for that band; trim becomes a plain gain, monotonic. | One new saved parameter per band and a chip on each strip. Manual bands lose the limiter-undoing dynamics recovery, which is the point of choosing manual. |

**Why (3).** What a mix engineer expects; the auto path and its oracle stay
untouched; the monotonicity test runs on the manual path. Plan 06 proposed it
first.

**What changes.** About two days (plan 11 WP15): the switch, the strip chip,
a monotonicity test on real material, one scene-file field defaulting to auto
so every saved scene loads unchanged, the ENGINEERING warning rewritten.

### 7. R2 + L2 — the loop keys into the binding table

**Recommendation: (a), make them table rows.**

**What it is.** Almost every key, pad button and APC40 control is a row in
one binding table, saved in your home folder, editable on the ROUTING page,
shown on the cheat sheet. Three things are still hard-coded in the frame
loop: R (camera reset), F1–F8 (load slot) and ⇧F1–F8 (save slot). Cmd+R and
Esc/Q are also in the loop and would stay there.

**Today.** The loop keys work but cannot be rebound, do not appear on the
ROUTING page, and need a duplicate "act" code path the audit wants gone. A
decision from 2026-09-26 kept them in the loop, with scope as the reason.

| Option | Result | Trade-off |
|---|---|---|
| (a) Rows for R, F1–F8 and ⇧F1–F8; delete the duplicate path | Every performance key rebinds like any other; the cheat-sheet test covers them; only restart and quit stay outside the table. | Your binding file gains up to seventeen rows on next launch, added only where those keys are free. Supersedes the earlier decision. |
| (b) Keep them in the loop; delete only the duplicate setter | No change to the file. | The duplicate path stays; F-keys and R remain the one thing the ROUTING page cannot show or change. |

**Why (a).** The earlier decision was about scope, not design; the table was
built for this; it closes two audit rows. Under plan 13 the F-key rows load
*preset slots* rather than theme slots; the recommendation is unchanged, only
the target ids differ.

**What changes.** Half a day (plan 11 WP7): three factory rows, the migration
that adds them to older files, the cheat sheet, tests, one superseded row.

### 8. Merge one integration PR, or fifteen PRs

**Recommendation: merge PR #55, then #47.**

**What it is.** Plan 11 is fifteen pull requests (#39–#54), one per work
package, each code-reviewed on its own. They were built in parallel and
several edit the same document tables and the same few source lines, so they
were stacked. PR #55 is all fifteen merged in stacking order with the seams
fixed and tested as one build: 778 tests pass. PR #56 (the plan 13 ledger)
targets #55's branch and rides with it. PR #47 (plan 12's five party
presets) merges after #55 as is, which you settled on 2026-09-28.

| Option | What you do | Trade-off |
|---|---|---|
| Merge #55 | One merge; GitHub marks the fifteen as merged. | Main receives one large merge; a later bisect lands on the integration commit rather than a work package. |
| Merge the fifteen in order | Fifteen merges, in the order #55's description lists. | Each after the first few conflicts on the ARCHITECTURE, ENGINEERING and AUDIT tables, the hot-reload module list and the frame loop; the same resolutions as #55, redone by hand. |

**Why #55.** The conflicts are already resolved and the merged result is
what was tested. Each PR keeps its review and diff.

### 9. P13-a — what the global layer's track knobs carry

**Recommendation: (a) as a first cut.**

**What it is.** Under plan 13 the APC40's eight track knobs have two
meanings: the loaded preset's on the preset layer, and a fixed set on the
global layer (reached by latched SHIFT). The global set is defined by the
session and can never be Learned over. The question is what those eight
global knobs should do.

**Today.** No layer exists; the track knobs are the view faders on every
preset.

| Option | The global track knobs | Trade-off |
|---|---|---|
| (a) Four hand-feel settings (smoothing, response, catch time, the selected axis's return time) plus BPM; three knobs free | The desk person adjusts the hand feel while someone else is in the box. | Thin: five of eight used. If the box is calibrated once and left, these knobs are rarely touched. |
| (b) Only the band strip on the device knobs; track knobs dark under SHIFT | Nothing to learn; the global layer is the analyzer only. | Hand feel is panel-only mid-set. |
| (c) Your own list | Whatever you reach for. | You write it. |

**Why (a).** The hand feel is the one thing that changes with who is in the
box, and it must not cost every preset a knob. If the box is calibrated once
and left alone, choose (b).

**What changes.** A session file's global map, one factory table, the LED
rule for the dark knobs. Part of plan 13 WP2.

### 10. P13-b — partial presets under "a load replaces everything"

**Recommendation: (a), no exception.**

**What it is.** You decided that loading a preset replaces everything: every
performance parameter lands (the file's value or the app default), every
performer row is replaced, the desk's preset layer is replaced, no merging.
Today's routing presets (`legacy6`, `lfo-breathe`, the `hands-*` files) are
routes-only files with no values. Loaded as presets under that rule they
would reset the whole picture.

| Option | What a routes-only file does | Trade-off |
|---|---|---|
| (a) No exception: the one-time migration turns routes-only files into full presets; "partial" means only a module preset (one group's values from that group's strip) | Every preset load is total and predictable. | Routes-only files stop existing; anyone who liked "load the routes, keep my look" uses module presets and a full preset instead. |
| (b) A preset may omit values and then leaves the picture alone | Today's routes-only files keep working as they are. | One exception to the no-merge rule, and the place the next exception comes from. Two kinds of load to explain. |

**Why (a).** You chose the rule for having no merge cases. Plan 13 §8 calls
(a) the clean answer.

**What changes.** The migration writes full presets from the routes-only
files, with today's theme values filled in. Part of plan 13 WP1.

### 11. P13-c — bank slots by name or inline

**Recommendation: (a), a slot names a preset file.**

**What it is.** F1–F8 and the APC40's preset-select row pick one of eight
slots. Today a slot (a theme slot) holds its values inline in the project
file.

| Option | What a slot is | Trade-off |
|---|---|---|
| (a) A slot names a preset file; F-key and the preset row load it; ⇧F-key saves the live state *as* that preset into the user folder | A preset is the one unit that is saved, loaded, shared and versioned; a slot is a pointer. | Deleting or renaming a preset file empties a slot; the slot then loads nothing and says so. |
| (b) Slots keep inline copies, as themes do today | A project is self-contained. | The same performance moment exists twice, in the bank and as a file, and drifts. |

**Why (a).** One unit, one place. Plan 13's design assumes it.

**What changes.** The session's slot list, the save-slot path, the project
migration. Part of plan 13 WP1.

### 12. P13-d — what a macro is

**Recommendation: (a). This one is waiting for your yes.**

**What it is.** Today a macro is one of eight knobs that scales the *depth*
of every performer row naming it; it never sets a value itself. Separately,
no desk row today can set more than one target. You asked on 2026-09-28 what
a macro is, describing "one knob, multiple bound controls that all change
simultaneously".

| Option | Meaning | Trade-off |
|---|---|---|
| (a) Keep macros as depth attenuators, saved in the preset with their routes, and add multi-target desk rows: one knob sets several bases, each with its own range | Two small jobs, each with one name. The thing you described is the second half. | Two concepts to explain: "macro" (attenuator) and "multi-target row" (fan-out setter). |
| (b) Macros become the fan-out setter; the attenuator role goes | One word. | Chaining loses its attenuator: a hand can no longer scale how hard an LFO pushes without owning the LFO's depth directly. |
| (c) Both jobs under one word | One knob can attenuate routes and set bases. | The row format grows two shapes; the ROUTING page has to show both. |

**Why (a).** The two jobs do not compete and each is small.

**What changes.** A `targets` list on a desk row with a range per target;
the ROUTING page shows it. Part of plan 13 WP3.

### 13. P13-e — the ROUTING page once it edits the loaded preset

**Recommendation: (a), one page.**

**What it is.** Under plan 13 a Learn or an edit on the ROUTING page writes
into the loaded preset, not into a global file. The page has to show the
preset's performer rows, the preset's desk rows (the APC40 preset layer), and
the session's invariant and global rows.

**Today.** The page lists performer rows and a routing-preset strip. MIDI
rows are not shown at all.

| Option | Layout | Trade-off |
|---|---|---|
| (a) One page: the preset's routes table, its desk rows under it, the session's invariant and global rows read-only below | One place to see why a knob does nothing: unmapped, invariant, or on the other layer. | A longer page; the rows scroll in a child (already the case). |
| (b) Desk rows on their own page | Each page stays short. | Two pages to check when a knob is dead. |

**Why (a).** The question a performer asks at the desk is "why does this
knob do nothing", and one page answers it.

**What changes.** The ROUTING page layout and its no-scroll test. Part of
plan 13 WP3.

### 12b. P13-g — when a hand owns a macro, do its base settings follow?

**Recommendation: (a) for the first build.**

**What it is.** Your answer to 12 made a macro one knob with subscribers:
each either sets a parameter's base or scales a route's depth, with its own
direction. A macro is an ordinary parameter, so a performer (a hand, an
LFO) can own it. The question is what happens to the macro's *base*
subscribers while a performer is moving it.

**Why it is a question.** The control model has one hard rule: knobs,
keys, the panel and presets set bases; performers only ever add offsets,
through one path. A knob turned on the desk setting several bases is
fine. A hand setting several bases every frame is a performer writing
bases, which the model forbids.

| Option | What a hand riding a macro does | Trade-off |
|---|---|---|
| (a) Base subscribers follow the macro's base only | Moves the macro's depth subscribers (route attenuation), as `scale` does today. The base subscribers move only when the knob, panel or a preset moves the macro. | A hand cannot sweep several bases at once through a macro; it can still own each of those params directly. |
| (b) Yes, as offsets | The macro becomes the performer of every param it base-subscribes, counted by the referee as that param's one owner; the hand's movement lands as offsets. | A real extension of the model: a macro that is a performer, with referee rules for when a route and a macro both want one param. |
| (c) Yes, as base writes | The hand rewrites the bases every frame. | Breaks the rule that stops a hand and a knob fighting over one value; the knob could never catch. |

**Why (a).** It needs nothing new in the model and ships the concept.
(b) can follow if a hand on a macro turns out to be what you reach for.

---

## Part A2 — raised while building plan 13 (2026-09-28)

Both came out of checking plan 13 against the code (plan 13 §9). Both are
about the **MASTER fader**, which in this app is the audio *drive*: how
hard the music pushes everything the bands drive (`master.gain`, 1× to 8×).

```
 APC40 MASTER fader ──▶ master.gain (session: the room's drive)
                              │ today: every band → rotation route is "× master.gain"
 band lanes ──push──▶ rot.rate.XY … ZW        (the six planes spin with the music)
 left hand (party-tumble) ──push──▶ master.gain   (a hand leans on the drive)
```

### 18. P13-h — how the drive fader reaches the rotation, once routes lose `scale`

**Answered (a), 2026-09-28.** (Recommendation was (a), keep `scale` on a route, only for a session param.)

**What it is.** A route's depth can be multiplied by another parameter's
live value, its `scale`. You decided (row 12) that a macro's attenuation
becomes a *depth subscriber* of the macro, and that routes lose the
`scale` field. But the field has a second user that is not a macro: the
six band → rotation routes are each "× `master.gain`". That multiplication
is the only way the MASTER fader changes how hard the music spins the
shape, and it is how the reference design worked (the parity test checks
it).

**Today.** Every factory and party preset carries those six rows with
`scale: master.gain`. Move the MASTER fader and the music spins the shape
harder or softer; the band pattern inputs are not scaled.

| Option | What the MASTER fader does to the rotation | Trade-off |
|---|---|---|
| (a) Keep `scale` on a route, allowed only on a session param (the drive fader today); macros go to subscribers as decided | Exactly what it does now. | Two ways to scale a depth remain — a macro's subscriber (per preset) and a route's `scale` (the rig's) — each with one job; the ROUTING page shows both. |
| (b) Let the drive fader have depth subscribers, like a macro, listed in the preset | The same, described as a subscriber. | A session control's wiring lives in every preset; a subscriber's `from → to` runs over the fader's 0–1 position, not its 1×–8× value, so the six rows' numbers change and the parity test is re-derived. |
| (c) Drop it: routes lose `scale` everywhere | The MASTER fader no longer changes the rotation; only the pattern and whatever the analyzer's gain feeds. | The drive fader stops meaning "how hard the music drives the shape"; the legacy6 parity anchor is re-frozen without gain. |

**Why (a).** It keeps the one job the drive fader has in the room, costs
no numbers, and keeps your macro decision whole: every `scale` that named
a macro still becomes a subscriber.

**What changes.** (a): the migration converts only `scale: macro.N`; the
loader refuses a `scale` on a performance param with a note; one sentence
in ARCHITECTURE §3.4. Plan 13 WP3 builds it; until you answer, WP3 leaves
those six rows exactly as they are.

### 19. P13-i — may a preset's route *perform* a session param?

**Answered (a), 2026-09-28.** (Recommendation was (a), yes.)

**What it is.** You decided (plan 13 D9) that the analyzer is session: its
bands, dynamics, scene and the drive fader are never in a preset, so a
preset load never moves them. `party-tumble`'s left hand, though, *pushes*
the drive (`master.gain`) — lifting the hand makes the music grip the
shape harder; lowering it or leaving the box gives the fader's own value
back.

**Today.** The route works; nothing distinguishes a session target.

| Option | What `party-tumble`'s left hand does | Trade-off |
|---|---|---|
| (a) A route may target any param a performer may drive, session ones included; D9 governs the *values* a preset lands | Leans on the drive while the hand is up; the fader's setting is never changed and shows again when the hand leaves. | A preset can change how the room *feels* while a hand is in, never what it is *set* to. The ROUTING page marks such a route "session". |
| (b) A route onto a session param is dropped at load with a note | Nothing; `party-tumble`'s left height is re-cut onto a performance param (the spin speed, say). | The strict reading of D9; one party gesture changes. |

**Why (a).** D9's reason was that the analyzer is the room and every
preset assumes one lane layout; an offset that springs back touches
neither. It keeps plan 12's gesture as you approved it.

**What changes.** (a): nothing in the loader; the page's "session" mark;
one sentence in ARCHITECTURE §3.2. (b): a check in the preset loader and a
new left-height row in `party-tumble` (WP5).

### 20. P13-j — hand routes by name or by lane number

**Answered (a), 2026-09-29: by name, built in plan 13 WP5b (PR #70).** (Recommendation was (a).) Every factory preset now names its hand rows (`hand:right.roll`); the migration names yours by your rig's `[hands] dofs` (or the default list when `[hands]` is off) and says so in a note; a number still reads. Hand check 42 tries a reordered `dofs` at the machine.

**What it is.** A preset's hand route says which hand axis drives it. Today
it says so by a lane *number*: `hand:9` means "the 10th hand lane", which on
the shipped setup is the right hand's roll. The numbers follow the order of
the `[hands] dofs` list in your `config.toml`. If that list is ever
reordered or trimmed (say, dropping yaw because it is noisy in your box),
every hand row in every shipped and saved preset silently points at a
different axis: a tilt would start zooming. Nothing warns.

```
 [hands] dofs = x y z roll pitch yaw     hand:9  →  right roll     (as designed)
 [hands] dofs = x y z roll pitch         hand:9  →  right pitch?   (silently wrong)
 by name:                                hand:right.roll → right roll, whatever the list
```

**Today.** Every preset uses numbers; plan 12 noted the risk and the audit
filed it (N7). Plan 13 has just regenerated every factory preset and is
migrating your files once, so this is the cheapest moment the format will
ever have.

| Option | What a preset says | Trade-off |
|---|---|---|
| (a) Names now: `hand:right.roll`, `hand:left.y`, `hand:left.pinch.index`; the hands adapter publishes the name → lane map; a name the rig lacks makes the row dormant, never another axis. Factory presets regenerated with names; your migrated presets written with names; `hand:<i>` still read. | The axis it means, whatever `dofs` says. | About half a day more in plan 13 (a small follow-up PR before the integration merge). Learn writes names too. |
| (b) Later, as its own small plan | Numbers for now. | Every preset written until then (factory, migrated, yours) carries numbers and needs a second conversion; the silent scramble stays possible meanwhile. |
| (c) Never; a warning instead | Numbers; the app warns at start when your `dofs` differs from the shipped order. | Cheapest; you are told, but the presets are still wrong until re-authored. |

**Why (a).** The format is being set now and your files are being migrated
once; doing it now means no second migration, and a changed `dofs` can
never quietly break a party preset mid-set.

**What changes.** (a): a name map the hands adapter publishes, a resolver in
the router (routes, gates, rests, the page's labels), Learn writing names,
the generator and the migration writing names, tests; plan 13 builds it as
WP5b before the integration merge. (b)/(c): audit N7 stays open.

---

## Part A3 — raised by the first night at the machine (plan 14, 2026-09-29)

The rig is for a party: a render on a black window behind a Pepper's Ghost
glass, two hands in a box, an APC40. Plan 14 (`docs/plans/14-party-rig.md`)
has the findings; these five are yours.

### 21. P14-a — does overlay mode survive?

**Answered (a), 2026-09-29.** **Recommendation: (a), keep it behind a config key, off by default.**

**What it is.** Overlay mode floats the render window over the whole
desktop, see-through and click-through (a feature from an early commit).
The window is created with a transparent framebuffer for it in *every*
mode, and the APC40's MASTER select and the `T` key switch into it with one
press. For Pepper's Ghost the window must be opaque black, always.

**Today.** Plan 14 WP1 makes window and fullscreen opaque (the picture no
longer cuts the alpha); overlay still exists and one press still reaches it.

| Option | What the rig does | Trade-off |
|---|---|---|
| (a) Behind `[output] overlay = true` (default off): no transparent framebuffer, and MASTER select / `T` do nothing, unless the config asks | Can never show the desktop at a party; overlay still there for a laptop demo. | One config line to turn it on. |
| (b) Remove overlay mode | Simplest; nothing can go see-through. | Drops a feature and its code (pyobjc window raising, the crossfader's ground). |
| (c) Keep as today (after WP1) | Opaque unless someone presses MASTER select or `T`. | One wrong press mid-show floats the window over the desktop. |

**Why (a).** The show can never go see-through by accident, and nothing is
thrown away.

**What changes.** (a): the window hint and the two controls gated on the
config key, the overlay tests, check 26. Plan 14 WP2.

**Built** (plan 14 WP2): `[output] overlay` (default false) in
`config.DEFAULTS`; `app._windows(overlay)` sets `TRANSPARENT_FRAMEBUFFER`
only when it is true; `overlay.Output.allowed` gates `output.overlay`, the
one param the `T` row, the MASTER select row, the panel and a preset land
on, so each road is shut together; the OUTPUT page greys the toggle and
says why.

### 22. P14-b — how the rig becomes "the party device"

**Answered the recommendation, 2026-09-29.** **Recommendation: the party show opens by default; the house moods become a
`house` show; the last show opened is remembered.**

**What it is.** A "show" (today's "project") is a bank of eight presets and
the one it starts on. The rig always opens the show named `default` — the
eight house moods, and on your machine the `MIGRATED` preset in front of
them — and forgets `party` every launch.

**Today.** You open `party` by hand from load ▾ after every launch.

| Option | What a launch opens | Trade-off |
|---|---|---|
| (a) Party is the factory default show (the house moods move to a `house` show), the last show opened is remembered, your `MIGRATED` stays a preset in the list (not in the bank) | Party, on every launch; whatever you last opened thereafter. | Your current `default` file is renamed with a backup; its bank moves to `house`. |
| (b) A config key names the show to open (`[library] show = "party"`) | Party, as long as the key says so. | Explicit, but one more thing in the config. |
| (c) Only remember the last show | Party after you open it once. | The first launch is still the house moods. |

**Why (a).** The rig is a party device; the first thing it shows should be
the party.

**What changes.** The factory `default.hyp.json`, a `house` show, a
remembered last show, a one-off rename of your `default` (with backup).
Plan 14 WP3.

**Built** (plan 14 WP3): the factory `default.hyp.json` is removed rather
than re-filled — `party.hyp.json` already was the party show, and a user
file named `default` (yours, plan 13's) would have gone on shadowing a
factory `default`; `library.DEFAULT_PROJECT` is `party`. The house moods
are `house.hyp.json`. `<home>/last_show` holds the name of the show opened
last (a plain one-line file beside `config.toml`, written by a show load,
save as, or a "starts on" pick); a name that is gone falls back to the
party. On the first launch your `projects/default.hyp.json` becomes
`projects/mine.hyp.json` (named `mine`, bank and startup as they were),
kept first as `default.hyp.json.bak-v2`, noted on stderr and on the
PRESETS page; the second launch changes nothing.

### 23. P14-c — "the dream on by default"

**Answered (a): torch is part of the app, 2026-09-29.** **Recommendation: (b), keep torch optional, turn the worker on by default,
and say loudly when torch is missing.**

**What it is.** The dream worker (the neural "dream" over the look-back
echoes) needs torch — about 1 GB — installed as an optional extra with
`uv sync --extra dream`. Without it the look-back shows raw echoes and says
"no worker"; a plain `uv sync` removes the extra.

| Option | What you get | Trade-off |
|---|---|---|
| (a) torch always installed | The dream works on every install. | A ~1 GB install and a slower launch on every machine, dream or not. |
| (b) Optional extra, worker on by default, the panel says what to run when torch is missing | The dream works once you run the one command; the panel tells you. | You must use `--extra dream` for sync and run. |
| (c) As today | — | "No worker" with no explanation. |

**Why (b).** The rig gets the dream once, on purpose; a laptop without it
still starts fast and tells you why.

**What changes.** `[dream] enabled` default, the SYSTEM / LOOKBACK message
(WP1), the setup docs, the launch command in the hand checks. Plan 14 WP6.

**As built (plan 14 WP1 + WP6).** WP1 made torch an ordinary dependency
and the worker on by default. WP6 made the echoes it dreams over
readable: echo time is seconds (`dream.fade`, a half-life; `dream.gap`,
seconds between echoes — the old per-frame `dream.decay` / `dream.every`
read as 60 Hz frames, so every saved look is the same at 60 Hz and a
120 Hz screen no longer halves the trail); a TRACER preset with the
investigation's legible set (a ninth party preset, in the list, on no
F-key); WAKE re-tuned (24 echoes over 1.2 s, a 0.6 s half-life, occlude
0.3) and shot with the worker running
(`docs/plans/assets/12-presets/party-wake-dream-sheet.png`). No extra
step: `uv sync` and launch; hand checks 9 and 41 look at it.

### 24. P14-d — which effects go on the party show's F6–F8

**Answered (a), 2026-09-29.** **Recommendation: ACID, MANDALA and NOITA.**

**What it is.** The FX page has twelve effects; the party show uses four,
all in TRIP. Seven (warp, wobble, doublevision, deconverge, fractals,
glimmer, tripcolour) are in no preset at all. The party show has three
empty slots.

| Option | F6–F8 | Trade-off |
|---|---|---|
| (a) ACID, MANDALA, NOITA — built from the three module presets already tuned in `library/fx/`, each with hand routes and eight device knobs like TRIP | Three more looks, one effect family each; every effect reachable from the show. | Three presets to compose and judge by eye (check 41). |
| (b) Your own three | — | You name them. |
| (c) Leave F6–F8 empty; add the effects to the existing five | No new presets. | The five were composed to plan 12's brief; adding effects changes them. |

**Why (a).** The looks already exist as module presets; this puts them on a
key.

**What changes.** Three generated presets, the party bank, the FX-coverage
test. Plan 14 WP5.

**As built (plan 14 WP5).** `party-acid` (acid, wobble, deconverge, hue
cycle), `party-mandala` (plasma, kaleidoscope, fractals, glimmer) and
`party-noita` (trip warp, trip colour, fractals, double vision) on F6–F8,
each taking its effect values from its `library/fx` module preset, with
plan 12's hand rows and eight device knobs. The seven effects no preset
used are all on in one of the three. Two deviations from the module
presets, both for the glass: MANDALA's plasma level and its fractals and
glimmer grounds start at 0 (the module is a full-frame generator; on a
Pepper's Ghost the black must stay black — the right hand's pitch floods
the plasma in), and NOITA adds double vision, which no module preset has.
The dead `fx.mix` rows: `hands-pinch` fades the hue cycle in, `lfo-breathe`
breathes the plasma. Cards: `docs/plans/assets/12-presets/party-{acid,
mandala,noita}.md`; hand checks 5 and 41.

### 25. P14-e — the desk's glyphs and diagram

**Answered (a), 2026-09-29.** **Recommendation: the scheme below, the diagram above the cheat sheet,
showing the layer that is up.**

**What it is.** Akai's names ("track knob", "device knob", "clip 4·2")
mean nothing for this show. Each control gets a short glyph, printed on
every ROUTING row and Learn message, and drawn on an on-screen picture of
the APC40 with the mapped controls lit.

```
 K1 K2 … K8   track knobs (top row)         D1 … D8   device knobs (right)
 G1·1 … G5·8  clip grid, row·column          G1·9 … G5·9  scene launch
 G6 … G10     clip stop, select, activator, solo, rec-arm rows
 S1 … S8      track faders    SM  master fader    X  crossfader    C  cue
 B1 … B22     the other buttons (transport, arrows, TAP, NUDGE, …)    ⇧  SHIFT
```

| Option | Trade-off |
|---|---|
| (a) As above (S for faders, so F stays the F-keys; the diagram shows the up layer) | Short, unique (checked against every control and row shipped). |
| (b) Letters for the button rows instead of G6–G10 | Easier to say aloud, longer to learn. |
| (c) The diagram shows both layers at once | Everything visible; twice as dense. |

**Why (a).** One glance from a row to the desk, in four characters.

**What changes.** A layout table, the glyph on the page and in Learn, the
diagram window, hand check 45. Plan 14 WP7.

**Built (plan 14 WP7).** `apc40.LAYOUT` holds all 137 controls with the
glyphs above (B1–B4 PAN, SEND A–C; B5–B12 the eight device buttons,
CLIP/TRACK … METRONOME; B13–B15 PLAY, STOP, REC; B16–B19 ▲ ▼ ▶ ◀; B20
TAP TEMPO, B21 NUDGE −, B22 NUDGE +). The ROUTING desk and session rows
print the glyph first, Akai's name in the tooltip; Learn says "D3
(device knob 3)". The diagram (`ui_desk.py`, `ui.desk`) sits above the
cheat sheet in the control window and reads the table, not the port.
Where each control sits is hand check 45's to confirm on the device.

---

## Part A4 — raised by the Oct 3–4 session (plans 15–21, 2026-10-04)

Dan and Dillon ran the rig for a night and talked through everything it
still needs. `docs/plans/15-21-roadmap.md` orders that list into seven
plans. **You answered rows 26–33 on 2026-10-04**; each entry below keeps
the question as it was asked, with the answer on its first line. Rows 26–29
are built (plan 15, PRs #81–#83 and #87; the answer sheet's notes say
where). **Rows 34–44,
after row 33, are the forks plan 15's unattended run settled on its own
recommendation**: each is built and waits for you to confirm or overturn.

You also set how the work runs, since nobody will be watching it:

- **Nothing touches main.** Every plan lands on one branch,
  `finish-line`; you run that branch at the machine and merge it.
- **A fork met mid-run is decided by the run**: it takes its
  recommendation, builds it, and adds a row here after 33 marked "built
  on the recommendation; confirm or overturn", with the cost to reverse.
- **No timetable.** Needed by Friday 2026-10-09; not planned around dates.
- **Rate-type params under a hand are allowed**; nothing restricts them.
- **Presets**: more than eight on the desk (twenty-four: clip row 1 and
  clip rows 4–5); the unwanted ones hidden or trashed from the list;
  plain Save overwrites without asking for a name; no folders for now.
- **The faces as their own effect target**: your answer to "faces
  through FX". Each effect is aimed at the frame or at the faces; the
  faces' effects run into a texture the faces show, laid on per face or
  in screen space (plan 20).

**What is still unknown** (none of it blocks the work):

| # | Question | Assumed until you say |
|---|---|---|
| Q2 | Where are the roughly ten presets saved that night, and are they backed up? | On the rig in `~/Hyperspace/presets/`, not backed up. Run `cp -R ~/Hyperspace ~/Hyperspace-2026-10-04` before launching any new build |
| Q3 | Were the hands calibrated on that rig (HANDS page, the 20-second sweep)? | Unknown. Plan 18 is built either way; its hand checks start with calibration |
| Q4 | Which build ran that night? | Main at fa9b3a1 (2026-09-29) |

### 26. P15-a — how deep does undo go?

**Answered 2026-10-04: undo reaches single parameter edits** ("that's part of what we need in order to discover good presets"). Built as (b) with a short settle time, so one slider drag, knob turn or typed value is one step; no write hook is needed. The recommendation had been (a) first, then (b).

**What it is.** Ctrl+Z. The app has no undo except an 8-second one on
"reset all". A parameter write fires no event, and the ROUTING page edits
rows in place, so undo cannot record single edits cheaply; it can keep
whole snapshots of the loaded preset (values, routes, desk layer, macros).

| Option | What Ctrl+Z takes back | Trade-off |
|---|---|---|
| (a) Actions | A preset or show load, a Learn, an Unbind, a deleted route or macro, a module-preset load or reset; an overwritten or deleted preset file goes to a trash folder | A slider you dragged is not undone on its own; the last action before it is. Small. |
| (b) Actions and settled edits | The above, plus a snapshot whenever the preset has changed and then sat still for a couple of seconds | Slider moves undo in chunks. A day more; the stack fills faster. |
| (c) Every edit | Each slider move, each field | Needs a write hook through the registry and every in-place table edit. Large. |

**Why.** (a) covers every way the session lost work. (b) is what "undo"
means to most people and rides on the same stack.

**What changes.** A new `undo.py`, a call before each replacing action,
Ctrl+Z and Ctrl+Shift+Z as key rows. Plan 15 WP1.

### 27. P15-b — what "home" is, and where its button lives

**Answered (a), 2026-10-04**: the show's "starts on" preset, on the APC40's OVERDUB button (beside METRONOME) and the Home key.

**What it is.** One press back to a known-good look when a preset has gone
wrong mid-party.

| Option | What a press loads | Trade-off |
|---|---|---|
| (a) The show's "starts on" preset | The preset the show opens with | No new thing to set or explain. Home and the opening look are the same preset. |
| (b) A separate "home" pointer in the show | Whatever you marked as home | One more field and one more picker on the PRESETS page. |

**Why (a).** The show already names one preset as its known-good start.
The button is added to the invariant controls (the same on both desk
layers; no preset may remap it), which extends that list by one.

**What changes.** A `preset.home` trigger, one key row, one APC40 row, the
"starts on" line on the PRESETS page reads "starts on / home". Plan 15 WP2.

### 28. P15-c — the crossfader becomes master dim

**Answered (a), 2026-10-04**: master dim on both layers, left is black.

**What it is.** The session wanted to dim the whole picture from the desk
(a blackout switch was proposed and turned into dimming). The crossfader
today sets the overlay's background, which has done nothing since
decision 21 put overlay behind a config key. "Dimming on the crossfader in
shift mode" is not possible: faders mean one thing on both layers.

| Option | The crossfader | Trade-off |
|---|---|---|
| (a) Master dim on both layers; left is black, right is full | Dims the finished frame, after the effects. A preset load never moves it; a launch always starts at full; it picks up softly, so a crossfader left at black does nothing until you move it through the current value | The overlay background is set from the OUTPUT page only. |
| (b) Keep the overlay background; put dim on an unused knob | As today | A knob on one layer is not there on the other; dim wants to be always reachable. |

**What changes.** `output.dim` (a rig setting, not saved), one multiply at
the end of the frame, the crossfader's row in the factory desk and in an
existing `bindings.json` (backed up first). Plan 15 WP3.

### 29. P15-d — saving a preset from the APC40

**Answered 2026-10-04, changed**: the desk never overwrites. The gesture is a **save-as**: it always makes a new preset, with a name made from the preset the look grew from and the next free number ("TRIP 2"), and puts it in the next empty bank slot. Built as a hold of about 0.6 s anywhere on the clip-stop row (the eight buttons act as one wide bar); a tap does nothing. Plain Save on the panel still overwrites. The options below are the question as first asked, when the gesture saved into the slot above the button.

**What it is.** ⇧F1–F8 on the keyboard saves the live state into a bank
slot; the desk has no way to. The row of eight clip-stop buttons, directly
under the grid and in line with the eight slot buttons of clip row 1, is
unused.

```
 clip row 1   [ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ]   press: load slot k (today)
 clip rows 2–5  …
 clip stop    [ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ]   hold 0.6 s: save into slot k (new)
```

| Option | The gesture | Trade-off |
|---|---|---|
| (a) Hold clip-stop k for about 0.6 s; it blinks when saved; a tap does nothing | One hand, no modifier, lined up with the slot it writes | A long lean on the row saves. The preset it replaces goes to the trash first and Ctrl+Z still has the look. |
| (b) Hold a "save" button and press slot k on clip row 1 | Two-button chord, hard to do by accident | Needs a held modifier, which the desk does not have (SHIFT is a latch), and a second meaning for the preset row. |
| (c) No desk gesture; keyboard only | As today | The session asked for it. |

**What changes.** The eight clip-stop rows as invariant controls, press
duration in the MIDI adapter, a blink. Plan 15 WP4, which also adds "put
preset here…" to a slot on the PRESETS page, so a preset saved by name can
be put in the bank without loading it.

### 30. P15-e — the shape of the PRs

**Answered (a), 2026-10-04, with one change**: the per-plan integration branches merge into one branch, `finish-line`, not into main; you merge `finish-line`.

**What it is.** In the session Dan said Claude makes too many commits and
asked for one stacked PR per category; Dillon said the commits are too big
and asked for small PRs. The standing rule is one PR per work package,
merged through one integration branch per plan.

| Option | What you review and merge | Trade-off |
|---|---|---|
| (a) A small PR per work package, each with a demo in its body; they stack on `plan-NN-integration`; you merge that one PR per plan. In plan 15 each feature is its own merge commit, so one revert removes one feature | Small to read (Dillon), one merge per category (Dan), each feature revertable before Wednesday | Two levels of PR to look at. |
| (b) One PR per plan, no per-package PRs | One thing to look at | Large diffs; a revert takes the whole plan. |
| (c) Each small PR merged to main on its own | Simplest history | The document tables conflict on every merge; many merges for you. |

### 31. P16+ — automatic BPM

**Answered 2026-10-04: deferred.** "Something we need to put a little bit of thought into." Tap-only stands for this run.

DECISIONS: "One free-running clock, tapped into time … No DJ Link, no MIDI
clock, no drift correction: re-tap." Auto BPM reverses it. In the session
Dillon said it is not that important and Dan said it is real work.

| Option | Trade-off |
|---|---|
| (a) Stay tap-only | Nothing to build. |
| (b) Beat detection from the audio input, suggesting a BPM you accept with a press | Real work, tuned by ear; likely wrong on sparse music. |

### 32. P21-a — one output or two

**Answered 2026-10-04**: the Pepper's Ghost glass and the projector are each a render output; the laptop screen is the control view. Each output shows the same frame, has its own dim, and has its own on/off for the polytope pipeline and for the hands (four states per output). This replaces the "two windows" decision with one control window and a list of render outputs. Plan 21.

Plan 14 treats the render window as the Pepper's Ghost picture. That night
the Pepper's Ghost glass and the projector were separate outputs. The app
has two windows by decision (render, controls); a third is new
architecture. What does each surface show: the same frame, the same frame
with its own dimming, or different content (the shape on the glass, the
effects on the wall)? Plan 21 is not written until this is answered.

### 33. P21-b — the hand HUD

**Answered 2026-10-04: (a) and (c)**: finish and merge PR #78 as the hand HUD, and make what is drawn swappable, so other objects can stand in for the hands (`ghost.style`). Plan 21.

The session disagreed (ghost-hand meshes against abstract shapes for the
twelve axes) and settled on simple shapes first. On 2026-10-04 Dillon
opened draft PR #78: both hands drawn as capsule hands over the finished
frame, after the effects, off by default (about 2,600 lines, with tests).

| Option | Trade-off |
|---|---|
| (a) Review and finish PR #78 as the HUD; it is display only and off by default | It is built. It is the "mesh" side of the disagreement, in its simplest form. |
| (b) Close #78; draw simple shapes per axis instead | Matches what was settled; throws away working code. |
| (c) Both: #78 as one HUD style, shapes as another | Two things to maintain; more settings. |

**Rows 34–44 were decided for you while plan 15 was built.** Nobody was
watching the run, so each fork it met was settled the way
you set out above: the recommendation was taken and built, and the
entry is here for you to confirm or overturn. "What the code did" is the
behaviour before plan 15. Each was shown by tests and scripted launches
on a laptop, not at the rig; the hand check that would show it to you is
named. Plan 15 §7 has the same forks in the builder's words (its forks
2, 3, 11 and 18 are about how the code is put together and change
nothing you can see, so they are not here).

### 34. P15-f — which keys undo, and what a two-modifier chord fires

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** You asked for Ctrl+Z. The rig is a Mac, where undo is
⌘Z, and the cheat sheet already says "Cmd+R". Redo is the same key with
⇧, which is the first time one key has rows with two modifiers.

**What the code did.** There was no Control modifier for a key row at
all (only ⇧ and ⌘). And a row with modifiers fired whenever its
modifiers were *among* those held: with rows on ⌘Z and on ⌘⇧Z, pressing
⌘⇧Z would have fired undo and redo together.

| Option | Trade-off |
|---|---|
| (a) ⌘Z / ⌘⇧Z only | No new modifier. "Ctrl+Z", as written and as said, does nothing. |
| (b) Ctrl+Z / Ctrl+⇧Z only | What was said. Wrong for Mac hands. One new modifier. |
| **(c) Both** | Either hand finds it. One new modifier name and two more rows. |

**Chosen: (c)**, and with it one rule for every key: **a press fires
only its own chord**. A row fires when its modifiers are exactly the
held ones that some row on that key names. ⌘⇧Z redoes and nothing else;
`B` and ⇧B stay two controls, as before; a modifier that no row on the
key uses is ignored, as before. A missed undo mid-party costs more than
two rows. The rule is needed under every option.

One thing changes for a row you made by hand in `bindings.json`: a bare
`key:Z` row no longer fires while ⇧, ⌘ or Ctrl is held (the undo rows
now use all three on Z), and two one-modifier rows on one key no longer
both fire when both modifiers are down. No factory row is affected.

**Cost to reverse.** Delete two rows, or the modifier: minutes. Going
back to the old "among those held" rule would break redo. Plan 15 WP1
(PR #82); `Router.keys`, `routing.MODIFIERS`;
`test_routing.py::test_a_chord_fires_only_its_own_row`. Hand check 48.

### 35. P15-g — undo and the band layout

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** The roadmap said a band added, removed or moved "keeps
the existing 8-second undo". What happens to Ctrl+Z around such a
change, and to a strip you had edited before it?

**What the code did.** Those three never had an undo: each *clears* the
8-second one, which only "Reset all" arms. A layout change also
re-creates every band parameter, and moving a band shifts values between
the same ids, so a strip value saved before the change would land on a
different band after it.

| Option | Trade-off |
|---|---|
| (a) Fold it all in: add, remove and move become undo steps; the 8-second button retires | Not cheap: changes in the analyzer's control code, a layout in every saved state, and the reset undo's own snapshot redone. |
| (b) Clear the whole undo history on any layout change | Adding a band throws away the history of the look. |
| (c) Drop only the band values from the history on a layout change | Simple, but every factory band preset carries a layout: Ctrl+Z after loading one from the strip would find its own step emptied and undo the edit *before* it. |
| **(d) Remember which band layout each step was made on; put strip values back only onto that same layout; a load puts its layout back first** | A band preset load, a show load and a scene pick undo whole. Add, remove and move are not steps; a strip edited before one is left alone by an undo until the layout is the same again. |

**Chosen: (d).** Ctrl+Z after adding a band does not remove the band. If
a step holds strip edits made on another layout, the rest of the step
still comes back and the footer adds "(the bands have changed: their
strips were left)". The 8-second "Reset all" button works as before,
beside it.

**Cost to reverse.** (a) is a later plan's work, about a day, and builds
on (d). Plan 15 WP1 (PR #82);
`test_undo.py::test_a_band_add_remove_or_move_makes_no_step`,
`::test_strips_are_put_back_only_onto_the_layout_they_were_made_on`.

### 36. P15-h — is a tap an undo step?

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** The BPM is a saved setting of the show, so undo could
watch it like a slider.

**What the code did.** A tap burst rewrites the BPM on every tap, and
taps at 120 BPM are half a second apart: longer than the 0.4 s of quiet
that ends an undo step.

| Option | Trade-off |
|---|---|
| (a) Watch the BPM | Each tap of a burst is a step; Ctrl+Z after tapping walks back through tempos before it reaches the slider you meant. |
| **(b) Leave the clock out** | Tapping never touches the undo history. A typed BPM and a nudge are not undone either, and undoing a show load leaves the tempo where it is. |

**Chosen: (b).** "Clocks" were on the roadmap's own list of things to
leave out.

**Cost to reverse.** One line (`undo.EXCLUDED_GROUPS`). Plan 15 WP1
(PR #82); `test_undo.py::test_integrated_state_and_the_clock_are_not_watched`.

### 37. P15-i — when a preset file goes to the trash

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** You asked that a preset file about to be overwritten or
deleted go to a trash folder first (`~/Hyperspace/trash/`). Two details
were open: whether every Save trashes, and what happens when the copy
into the trash fails (a full disk).

**What the code did.** Save wrote over the file; the list's × deleted
it. Nothing was kept.

| Option | Trade-off |
|---|---|
| (a) Trash on every overwrite | Pressing Save with nothing changed fills the folder with identical copies. |
| **(b) Trash only when the file would actually change; a failed copy warns and lets the save go on, and refuses a delete** | Quiet. A full disk cannot make a delete unrecoverable, and cannot block a save. |
| (c) A failed copy refuses the save too | Safest for the old file, worst at a party: you cannot save at all. |

**Chosen: (b).** The trashed file is named
`<preset>.<date>-<time>.json` under `trash/presets/` (or the module's
folder); two in one second get `-2`, `-3`. Copy one back into
`presets/` under its plain name to restore it. Factory presets are never
written, so never trashed. Nothing empties the trash and no page shows
it yet (plan 19).

**Cost to reverse.** One condition. Plan 15 WP1 (PR #82);
`library.to_trash`, `Library.save_as`, `Library.delete`;
`test_library.py::test_a_save_that_changes_nothing_trashes_nothing`,
`::test_a_delete_keeps_the_file_in_the_trash_or_does_not_delete`. Hand
check 53.

### 38. P15-j — the Home key on a laptop

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** You put home on OVERDUB and "the Home key". A MacBook
has no Home key; fn+← sends it.

**What the code did.** Nothing: there was no home.

| Option | Trade-off |
|---|---|
| **(a) The Home key only; the cheat sheet says "fn ←"** | One row. The desk's OVERDUB is the party road. |
| (b) A second key as well (say ⇧H) | One more thing on the sheet for a road the desk already has. |

**Chosen: (a).** The row is in `bindings.json` like any key and can be
moved to another key there.

**Cost to reverse.** One row. Plan 15 WP2 (PR #83);
`routing.LOOP_KEY_ROWS`. Whether fn+← reaches the app as Home on your
laptop has not been tried: hand check 54.

### 39. P15-k — are camera moves undo steps?

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** Orbiting with the mouse, the sticks, the wheel, ↑ / ↓
and R (reset view) all change the camera, and the camera is saved in a
preset.

**What the code did.** No undo of anything.

| Option | Trade-off |
|---|---|
| **(a) Watch the camera like any setting** | R and an orbit undo. Someone who orbits a lot must press Ctrl+Z past the orbits to reach an earlier edit; the history holds 100 steps. |
| (b) Leave the camera out | Ctrl+Z always reaches a "real" edit. A wrecked camera is not undone, though it is saved in presets. |

**Chosen: (a).** One continuous orbit is one step; an orbit that pauses
for more than 0.4 s is two (row 43).

**Cost to reverse.** One word: add `"camera"` to
`undo.EXCLUDED_GROUPS`. Plan 15 WP1 (PR #82).

### 40. P15-l — what a hand or a band may do to home and to the dim

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** Two new parameters, and for each the question whether a
performer (a pinch, a hand axis, an audio band, an LFO) may be routed
onto it.

**What the code did.** Neither existed. The other preset triggers (load
slot k, next preset) may be fired by a performer; the four rig settings
of the output (screen, fullscreen, overlay, click-through) may not be
performed.

| Option | Trade-off |
|---|---|
| **Home: (a) a performer may fire it**, like load-slot and next-preset | No new rule. A pinch can send the show home if you route one there. |
| Home: (b) it may not | A second rule for one trigger of a family. |
| Dim: (a) a performer may drive it | A band or a hand could strobe the room, and a hand leaving the box could black it out. A preset could carry such a route. |
| **Dim: (b) it may not**, like the rig settings beside it | The dim is the operator's. A strobe is an effect's job. |

**Chosen: home (a), dim (b).** No factory preset routes anything onto
home. The dim is also never saved and never moved by a preset or a show.

**Cost to reverse.** One flag each. Plan 15 WP2 (PR #83, `preset.home`
in `params.build_registry`) and WP3 (PR #81, `Output.register`;
`test_overlay.py::test_dim_is_a_rig_setting_that_starts_bright`).

### 41. P15-m — what the dim does in overlay mode

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** In window and fullscreen the dim multiplies the picture
toward black and leaves the window opaque, which is what the Pepper's
Ghost glass needs. In overlay mode (only when `config.toml` asks:
decision 21) the ground is see-through, and "black" has no obvious
meaning.

**What the code did.** No dim.

| Option | Trade-off |
|---|---|
| (a) Colour only, as on an opaque ground | The ground's darkness stays over the desktop while the shape fades: neither black nor gone. |
| **(b) Colour and transparency together** | The render fades away and the desktop behind is left as the config asked for. |

**Chosen: (b).** Overlay is off unless the config asks, so the rig as
set up never sees this.

**Cost to reverse.** One line (the blend in `Renderer.dim_pass`). Plan
15 WP3 (PR #81); `test_render.py::test_dim_fades_a_see_through_ground`.
Seen offscreen only.

### 42. P15-n — the save-as gesture on the clip-stop row

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** You decided what the gesture does (row 29: a hold on the
clip-stop row saves a **new** preset into the next empty slot; the desk
never overwrites). Four details of how were left to the build.

```
 the button field (left of the desk)

 clip row 1   [G1·1][G1·2][G1·3][G1·4][G1·5][G1·6][G1·7][G1·8]  [G1·9]   press: load slot k
 clip rows 2–5   …                                                        (today, unchanged)
 clip stop    [=============== SAVE AS  ·  G6·1 … G6·8 ==============]  [G6·9]  STOP ALL: reset all,
               hold any of the eight 0.6 s: a NEW preset → the next               unchanged
               empty slot, whose pad on clip row 1 blinks; a tap: nothing

 the right-hand section

 device buttons   [B5 ][B6 ][B7 ][B8 ]
                  [B9 ][B10][B11][B12]      B9 DETAIL: cheat sheet    B10 QUANT: next preset
                                            B11 OVERDUB: home         B12 METRONOME: LFO trigger
 crossfader  X    [■■■■■■■■■──────────]     left: black … right: full
```

**What the code did.** The eight clip-stop buttons had no rows. The
MIDI adapter kept no press time, and nothing ever sent a blink.

| The detail | Option | Trade-off |
|---|---|---|
| How the table spells it | **(a) a new op, `hold`** | The ROUTING page's row says what it does (`G6·1 preset.save_new  hold`); the adapter times any row with it. One more op. |
| | (b) the adapter treats that one parameter specially | No new op, but the adapter then knows a parameter by name. |
| | (c) a per-row hold time | A setting per row nobody asked for. |
| When it fires | **(a) at 0.6 s, while you are still holding** | The blink is the feedback: you see it saved and let go. Something left lying on the row saves once, a new preset, and then nothing. |
| | (b) on release, after 0.6 s | No confirmation until the hand is gone; a long lean saves nothing, silently. |
| The bar's lights | (a) lit at rest | Says "mapped", but eight lights under the grid all night, and on this desk a lit button means a state that is on. |
| | **(b) dark at rest; lit while held; blinking, with the new slot's pad, for 1.5 s when it saves** | The light is the gesture's feedback. The on-screen desk and the hand-check card say what the row is. |
| What a new name counts against, and what is loaded afterwards | (a) the listed names only | A file whose name on disk matches another preset's would be overwritten, or would hide a factory preset. |
| | **(b) the files in both preset folders, the listed names and the bank; the new preset becomes the loaded one** | Never overwrites, never hides. A second hold counts on (TRIP 2 → TRIP 3), and Save on the panel then saves the new one. A factory "TRIP" yields your "TRIP 2". |
| | (c) as (b), but stay on the old preset | Every hold makes the next number from TRIP, but Save on the panel would still write TRIP, which you did not ask to change. |

**Chosen: the bold option of each.** The eight buttons are one bar: two
fingers save once, and a button still down saves nothing more until it
is pressed again. With the bank full the preset is still saved, goes to
the preset list, and the footer says so ("saved TRIP 3 — the bank is
full: it is in the preset list"); the bar blinks, no pad does, and no
slot is lit, because the loaded preset is in none. A preset whose name
ends in a number counts on from it (TRIP 2 → TRIP 3; with TRIP 3 taken,
TRIP 4).

Four things the build added that the question did not cover:

- **A save that fails blinks nothing.** If the preset cannot be written
  (a full disk), the bar just goes dark at 0.6 s; the desk never
  confirms a save that did not happen. The reason is on the PRESETS
  page.
- If the preset saves but the show cannot be written, the slot stays
  empty and the footer says the preset is in the list.
- The "bank is full" line goes away as soon as you make room (clear a
  slot, or put a preset somewhere).
- **A clip-stop button you delete from `bindings.json` comes back on the
  next launch**, like every factory button the migration adds. To switch
  one off, keep its row and add `"enabled": false`.

Not built, and not a fault: the on-screen desk lights the bar while it
is held but does not blink, and the cheat sheet does not mention the
bar.

**Cost to reverse.** Firing on release: move one call. The bar lit at
rest: the rows' "off" velocity. Staying on the old preset: one line. A
different hold time: one constant (`midi.HOLD_S`). Plan 15 WP4
(PR #87);
`test_midi.py::test_a_hold_fires_once_at_the_hold_time_while_held`,
`::test_the_bar_is_one_control`,
`::test_the_bar_lights_while_held_and_the_new_slots_pad_blinks`,
`test_presets.py::test_save_new_never_overwrites`. Hand check 56: the
gesture has been run by tests on a fake clock and fake ports, and the
save itself by a scripted launch of the app; the hold, the lights and
the blink have never been on the APC40, and the blink's velocities come
from Akai's table.

### 43. P15-o — a slider drag that pauses

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** Undo has no "mouse down / mouse up": a step ends after
0.4 s in which nothing you set has changed. So a slider held still for
longer than that with the mouse down, then moved again, is two steps,
and Ctrl+Z takes back the second part first.

**What the code did.** No undo.

| Option | Trade-off |
|---|---|
| **(a) The quiet time only** | One rule for the panel, the desk's knobs and faders, keys and typed values. A slow, hesitant drag can take two presses to undo. |
| (b) Also hold the step open while a panel widget is being dragged | One step per mouse press on the panel. The desk's knobs get nothing from it, and the undo would need the panel to tell it. |

**Chosen: (a)**, as the roadmap described it.

**Cost to reverse.** Small: one flag the panel sets. A different quiet
time is one constant (`undo.SETTLE_S`; plan 18's knob smoothing must
stay under it). Plan 15 WP1 (PR #82);
`test_undo.py::test_a_pause_longer_than_the_settle_time_makes_a_second_step`.
Whether 0.4 s feels right is hand check 48's.

### 44. P15-p — the faders after a preset load

**Built on the recommendation, 2026-10-04 (unattended run); confirm or overturn.**

**What it is.** A fader "has" its parameter once it has been moved to
the parameter's value (soft pickup); until then it does nothing, so a
fader never makes a value jump. You asked that the crossfader's dim
survive a preset load.

```
 a fader that has its parameter          the same fader after a preset load

   value ●━━━━━━━━━━┥ fader               before plan 15: every fader let go
   moving it moves the value               ●          ┥   dead until brought
                                                          back across the value

                                          now: let go only if the load
   S1 … S8   SM    X                      moved that fader's parameter
   ┃ ┃ ┃ ┃   ┃   ━━┥━━                    S1–S8, SM, X: a preset never moves
   drive     gain  dim                    theirs, so they carry straight on
```

**What the code did.** Every preset load made every fader let go,
whether or not the load had moved its parameter. A fader then took hold
again only if its next message landed on the value or crossed it. Worked
out from the MIDI step and the parameter's own steps (not measured),
that fails roughly one time in ten: the crossfader would be dead after
about one load in ten until it was brought back across, with the picture
half dimmed.

| Option | Trade-off |
|---|---|
| (a) Leave it | No change to the adapter. The crossfader sometimes dead after a load, mid-party. |
| **(b) A load makes a fader let go only when the load moved its parameter** | "Survives a preset load" is exact. The same fix reaches S1–S8 and the master fader, whose parameters a preset never moves. |
| (c) Give the crossfader no pickup at all | It would jump to the fader's position on first touch: a crossfader parked at the left blacks the rig out. Rejected. |

**Chosen: (b).** As built, a fader also lets go when its parameter no
longer exists, when it has never been moved since launch, and — added by
the review of PR #81 — when the parameter is not where *that fader* last
put it (two controls can share one parameter, and the other may have
moved it).

One gap is older than this and is not closed by it: a fader moved while
its row is switched off (or by the one message a Learn takes for itself)
does not notice, and jumps on its next touch. Before, any preset load happened to heal that;
now only a load that moves the parameter does. It is filed as audit row
R13.

**Cost to reverse.** One condition (`MidiIO.redraw`). Plan 15 WP3
(PR #81);
`test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load`.
Hand check 55 (e).

---

## Part B — built on the recommendation without asking; confirm or overturn

Four calls had a sensible default and waiting would have blocked the work.
Each is built, reviewed and on PR #55. Overturning any is a small follow-up.

| # | Call | What was built | The alternative | Cost to reverse |
|---|---|---|---|---|
| 14 | B1: a hand leaving the box | The moment a hand is out of the box its axes read "absent", so every row it drives lets go and the base returns, as a gate opening already did. The return spring and the "hold on exit" setting shape only the MIDI sent to a DAW. While a returning hand is being caught, the row stays live and glides onto it, so a one-frame tracker dropout does not snap the picture. | Keep "hold" latching a route: the hand leaves and the parameter stays. Latching is instead done by setting the base with a knob, which a performer never blocks. | Half a day; reopens the audit's first finding. |
| 15 | A1: which scene store survives | The eleven JSON files under the band library are the one source of scenes, with band names in each layout; the scene combo, the APC40 grid, Reset and the strip all read them; a user file of the same name shadows a factory scene. | Delete the JSON files and keep scenes in code; user-authored scenes would not exist. | A day. |
| 16 | L3: a project's own routing | A project never carries its own copy of the routing table; the live table stays one file in the home folder. The never-written field is gone. (Plan 13 replaces this: a preset carries its routes.) | Fill the field so a project restores its rows on load. | Moot once plan 13 lands. |
| 17 | B6: a trigger fired after the LFOs stepped | A trigger or LFO reset from the panel or a performer, which arrives after this frame's LFO step, is held to the start of the next step so the LFOs read exactly phase 0 the first frame they see it. Keys still land at once. | Document that those two paths are one frame off. | An hour. |

---

## Part C — already settled by you, listed so nothing is missing

- **Plan 13 D1–D12** (2026-09-28, in DECISIONS.md "Presets and the desk"):
  two nouns; a load replaces everything; module presets as labels; latched
  SHIFT with an LED; fixed global layer; invariant controls; knobs jump and
  faders pick up on a layer switch; an unmapped control does nothing and
  shows dark; the analyzer is session; a session names its startup preset; a
  modifier is read at the press. Built in plan 13 (WP1 #62, WP2 #64, WP3
  #63, WP4 #65, WP5 #66) on `plan-13-integration`; DECISIONS.md's rows say
  where and which test holds each.
- **Sequencing** (2026-09-28): merge #55, then #47 as is, then plan 13 from
  its WP1, re-cutting the five `party-*` presets in its WP5.
- **Plan 12's per-preset desk block**: superseded by plan 13's preset desk
  layer.

## Part D — not decisions, but gating "settled"

- `docs/plans/11-hand-checks.md`: 32 checks at the machine (41 since
  plan 13's group H). Checks 7 and 11
  read differently under each answer to decisions 1 and 4. Check 31 is the
  one hardware assumption plan 13 rests on (the APC40's endless knobs
  re-base from a host CC). Check 32 is plan 12's seven projector-and-box
  judgements.
- Two review notes from plan 12 that belong in the audit, not here: named
  hand addresses (`hand:left.roll`) so a custom `[hands] dofs` list cannot
  scramble shipped presets; an explicit groups-to-reset list on a theme or
  preset. Filed 2026-09-28 as `AUDIT-2026-09.md` rows N7 and L9. L9 is moot
  for presets since plan 13 (a load replaces every performance group, D2);
  N7 is row 20 here, answered (a) 2026-09-29, built in plan 13 WP5b (PR #70).
- Plan 13's machine checks: `docs/plans/11-hand-checks.md` group H
  (checks 33–42).
- The groups added since, in the same file: **I** (plan 14: the opaque
  window, the stall log, the on-screen desk; checks 43–46), **J** (the
  ghost hands; check 47) and **K** (plan 15: undo, the trash, home, the
  master dim, save-as on the desk; checks 48–57 — 57 first, because it
  is the launch that rewrites `bindings.json`; copy `~/Hyperspace`
  before it). Rows 34–44 above are each shown by one of group K's
  checks; nothing in plan 15 has been tried at the rig.

---

## Answer sheet

Write the letter, or "rec" for the recommendation. Rows 14–17 and 34–44
take "keep" or "overturn".

| # | Decision | Recommended | Your answer | Note |
|---|---|---|---|---|
| 1 | B2 tap and the downbeat | (a) never moves it | **(a)**, 2026-09-28 | |
| 2 | B5 performer-fired triggers | (a) keep all three | **(c)**, 2026-09-28 | LFO triggers ownable, tap tempo not |
| 3 | R1 LFO knobs | (c) theme state; presets may set assumed bases | **(c)**, 2026-09-28 | dissolved by plan 13 WP5 (PR #66): a preset carries every performance base, LFO knobs included, and the routing presets are full presets |
| 4 | R6 APC40 LEDs | (a) rings base, LEDs state | **(a)**, 2026-09-28 | |
| 5 | A7 Dynamics past 1× | (b) keep 4×, document | **(b)**, 2026-09-28 | |
| 6 | A10 input trim | (3) auto/manual switch | **(3)**, 2026-09-28 | built, WP15 |
| 7 | R2 + L2 loop keys | (a) table rows | **(a)**, 2026-09-28 | built, PR #58 |
| 8 | Merge path | PR #55, then #47 | **rec**, 2026-09-28 | #56 folded into #55 first |
| 9 | P13-a global track knobs | (a) hand feel + BPM | **(a)**, 2026-09-28 | a first cut; expect better globals with use. Built in plan 13 WP3 (PR #63): five global rows in `apc40.DEFAULT_MAP` (hand feel and `tempo.bpm` on track knobs 1–5, `hands.sel.return` the selected axis's alias), knobs 6–8 dark; learns kept off the global layer in WP4 (PR #65) |
| 10 | P13-b partial presets | (a) no exception | **(a)**, 2026-09-28 | built in plan 13 WP2 (PR #64): a load lands every performance base and replaces every route; and WP5 (PR #66): the routes-only files are full presets — `legacy6`, `lfo-breathe`, `hands-*` in `library/presets/`, a user's `bindings/*.json` by the first-launch migration (`preset.migrate_routing_presets`), each with the effects its routes drive switched on |
| 11 | P13-c bank slots | (a) a slot names a file | **(a)**, 2026-09-28 | built in plan 13 WP2 (PR #64): `Project.bank` is eight preset names, `load_slot` / `save_slot` / `cycle`; schema-1 inline slots become preset files in WP5 (PR #66) |
| 12 | P13-d what a macro is | (a) attenuator + multi-target rows | **one concept**, 2026-09-28 | subscribers set a base or a depth, each with its own polarity; see 12b. Built in plan 13 WP3 (PR #63): `routing.Macro` / `Sub`, `Router.follow_macros`, the depth term in `Router.modulate`, `scale: macro.N` migrated; the macros became the loaded preset's in WP4 (PR #65) and left `bindings.json` in WP5 (PR #66) |
| 13 | P13-e ROUTING page | (a) one page | **(a)**, 2026-09-28 | built in plan 13 WP4 (PR #65): `ui_routing.page` over the loaded preset — the head (name, dirty dot, save / as…, the layer, the last learn or refusal), routes, the desk with its dark controls, the macros and their subscribers, the session's MIDI rows read-only; the routing-preset strip left it there |
| 12b | P13-g a performer on a macro | (a) base subscribers follow the base only | **(a)**, 2026-09-28 | built in plan 13 WP3 (PR #63): base subscribers follow `p.base`, depth ones `p.value` (`test_a_performer_on_a_macro_moves_only_its_depth_subscribers`) |
| 14 | B1 as built | keep | **keep**, 2026-09-28 | |
| 15 | A1 as built | keep | **keep**, 2026-09-28 | |
| 16 | L3 as built | keep | **keep**, 2026-09-28 | |
| 17 | B6 as built | keep | **keep**, 2026-09-28 | |
| 18 | P13-h the drive fader and `scale` | (a) keep `scale`, session params only | **(a)**, 2026-09-28 | built in plan 13 WP5 (PR #66): `routing.migrate_scales` — a `scale` kept only on a session param, one on a macro a depth subscriber, one on a performance param dropped with a note |
| 19 | P13-i a route onto a session param | (a) yes; D9 is about values | **(a)**, 2026-09-28 | built in plan 13 WP5 (PR #66): the ROUTING page marks such a route "session" (`ui_routing.is_session_target`); the scale combo offers session params only |
| 20 | P13-j hand routes by name | (a) names now, in plan 13 | **(a)**, 2026-09-29 | built, plan 13 WP5b, PR #70: `hand:right.roll`, `hand:left.present`, `hand:left.pinch.index`, resolved through the hands adapter's published map (`router.names`); a name the rig lacks is dormant; `hand:<i>` still reads; the factory presets regenerated, the migration names what it carries by the rig's layout |
| 21 | P14-a overlay mode | (a) behind a config key, off | **(a)**, 2026-09-29 | built, plan 14 WP2 (PR #75): `[output] overlay = false` by default — the render window is created without a transparent framebuffer, `output.overlay` refuses to switch on (`T`, MASTER select, the panel's greyed toggle with the reason, a preset), the crossfader's ground does nothing; `true` is today's overlay |
| 22 | P14-b the party device | party opens; house moods a `house` show; last show remembered | **rec**, 2026-09-29 | built, plan 14 WP3 + WP4 (PR #75): the factory `default` show is gone — `party` opens, `house` holds the eight house moods; `<home>/last_show` remembers the show opened last; your `default` (MIGRATED + seven house moods) is renamed `mine` once, backed up as `default.hyp.json.bak-v2`, MIGRATED still its first preset; the PRESETS page speaks "show" |
| 23 | P14-c dream on by default | (b) optional torch, worker on, loud when missing | **(a)**, 2026-09-29 | torch is part of the app, not optional; built: plan 14 WP1 (the dependency, the worker on) and WP6 (echoes in seconds, TRACER, WAKE re-tuned and shot with the worker on) |
| 24 | P14-d F6–F8 effects | (a) ACID, MANDALA, NOITA | **(a)**, 2026-09-29 | built: plan 14 WP5 — `party-acid` / `party-mandala` / `party-noita` on F6–F8, every effect on in a factory preset, no factory route on an effect that is off |
| 25 | P14-e desk glyphs and diagram | (a) K/D/S/G/B glyphs, up layer, above the cheat sheet | **(a)**, 2026-09-29 | plan 14 WP7 — built (`apc40.LAYOUT`, `ui_desk.py`, hand check 45) |
| 26 | P15-a undo depth | (a) actions first, then (b) settled edits | **per-edit**, 2026-10-04 | one gesture (a drag, a knob turn, a typed value) is one step; built, plan 15 WP1 (PR #82): `undo.py` — `Undo.tick` once a frame in `app.frame` after `router.follow_macros`, a step closed by 0.4 s of quiet (`SETTLE_S`), `undo.push` before every load, Learn, Unbind, delete and Replace, a restore through `Registry.restore` and `Bindings.set_routes` / `set_desk(load=False)` / `set_macros`, `library.Marks` for what is loaded; ⌘Z / Ctrl+Z and ⇧ to redo (`edit.undo`, `edit.redo`); the footer's message line; the trash (`library.to_trash`). `tests/test_undo.py` (27 tests, `test_a_slider_drag_is_one_step_and_undo_sets_only_that_param`, `test_a_performer_moving_makes_no_step`, `test_an_idle_app_makes_no_step` among them), `test_library.py`'s five trash tests. Rows 34–37, 39 and 43 are its forks. Hand checks 48–53 |
| 27 | P15-b home | (a) the "starts on" preset, on OVERDUB and the Home key | **(a)**, 2026-10-04 | built, plan 15 WP2 (PR #83): `Project.home` (`library.py`), the `preset.home` trigger, `key:HOME` and the invariant OVERDUB row `note:0:64` (lit while the show names a "starts on"), added to an existing `bindings.json` where free; the PRESETS page reads "starts on / home"; one undo step. `test_presets.py::test_home_loads_what_the_show_starts_on`, `::test_home_is_one_undo_step`, `test_desk.py::test_overdub_is_home_on_both_layers_and_is_lit`. Rows 38 and 40 are its forks. Hand check 54 |
| 28 | P15-c crossfader | (a) master dim, both layers, left is black | **(a)**, 2026-10-04 | built, plan 15 WP3 (PR #81): `output.dim` (`Output.register`: never saved, not modulatable, 1 at launch), `Renderer.dim_pass` as the frame's last pass after the ghost hands, the crossfader's invariant row `cc:0:15 → output.dim` with soft pickup, your old factory row swapped with a backup (`routing.APC_REMAP`), first on the OUTPUT page, `dim 40%` in the footer. `test_render.py`'s seven `dim` tests, `test_midi.py::test_the_crossfader_dims_with_soft_pickup`, `test_desk.py::test_the_crossfader_keeps_its_hold_across_a_preset_load`. That the left end is CC 0 was read from a comment, not the device. Rows 40, 41 and 44 are its forks. Hand check 55 |
| 29 | P15-d save on the APC40 | (a) hold clip-stop k to save into slot k | **save-as**, 2026-10-04 | always a new preset with a made-up name, into the next empty slot; the desk never overwrites; built, plan 15 WP4 (PR #87): the eight invariant clip-stop rows as one `hold` bar (`midi.HOLD_S` = 0.6 s, `MidiIO._fire_holds`), `preset.save_new` → `Project.save_new`, `library.next_name`, "put preset here…" and "clear slot" on a slot's menu (`ui_presets._slot_menu`, `Project.put_slot` / `clear_slot`). `test_midi.py::test_a_hold_fires_once_at_the_hold_time_while_held`, `::test_a_tap_fires_nothing`, `test_presets.py::test_save_new_never_overwrites`, `::test_save_new_on_a_full_bank_saves_to_the_list_and_says_so`, `test_desk.py::test_the_clip_stop_row_is_invariant`. Row 42 is its forks. Never on the APC40 yet. Hand check 56 |
| 30 | P15-e PR shape | (a) a PR per work package, an integration PR per plan | **(a)**, 2026-10-04 | everything onto `finish-line`, never main; you merge that |
| 31 | Auto BPM | (a) stay tap-only | **deferred**, 2026-10-04 | not in this run |
| 32 | P21-a one output or two | none; describe the rig | **two render outputs**, 2026-10-04 | the same frame; per output a dim, scene on/off, hands on/off; the laptop is the control view; plan 21 |
| 33 | P21-b the hand HUD | (a) finish PR #78 | **(a) and (c)**, 2026-10-04 | #78 finished as the HUD, with what is drawn swappable; plan 21 |
| 34 | P15-f undo keys and chords | (c) both ⌘Z and Ctrl+Z; a press fires only its own chord | built on the recommendation; confirm or overturn | plan 15 WP1 (PR #82); a hand-made bare `key:Z` row no longer fires with ⇧, ⌘ or Ctrl held |
| 35 | P15-g undo and the band layout | (d) add / remove / move are not steps; strips go back only onto the same layout | built on the recommendation; confirm or overturn | plan 15 WP1 (PR #82); the 8-second "Reset all" undo unchanged |
| 36 | P15-h a tap as an undo step | (b) the clock is left out | built on the recommendation; confirm or overturn | plan 15 WP1 (PR #82); a typed BPM is not undone either |
| 37 | P15-i the trash on a save | (b) only when the file would change; a failed copy warns on save, refuses a delete | built on the recommendation; confirm or overturn | plan 15 WP1 (PR #82) |
| 38 | P15-j the Home key on a laptop | (a) the Home key only (fn ←) | built on the recommendation; confirm or overturn | plan 15 WP2 (PR #83) |
| 39 | P15-k camera moves as undo steps | (a) yes | built on the recommendation; confirm or overturn | plan 15 WP1 (PR #82) |
| 40 | P15-l performers on home and the dim | home: may be fired; dim: may not be driven | built on the recommendation; confirm or overturn | plan 15 WP2 (PR #83) and WP3 (PR #81) |
| 41 | P15-m the dim in overlay mode | (b) colour and transparency fade together | built on the recommendation; confirm or overturn | plan 15 WP3 (PR #81); overlay is off unless the config asks |
| 42 | P15-n the save-as gesture | a `hold` op; fires at 0.6 s while held; the bar dark at rest; names counted against files, list and bank; the new preset becomes the loaded one | built on the recommendation; confirm or overturn | plan 15 WP4 (PR #87); a failed save blinks nothing; a clip-stop row deleted from `bindings.json` comes back unless kept with `enabled: false` |
| 43 | P15-o a drag that pauses | (a) over 0.4 s still is two steps | built on the recommendation; confirm or overturn | plan 15 WP1 (PR #82) |
| 44 | P15-p the faders after a preset load | (b) a fader lets go only when the load moved its parameter | built on the recommendation; confirm or overturn | plan 15 WP3 (PR #81), with the per-fader condition its review added; audit R13 is the older gap it no longer hides |
