# Decision register — everything that is yours to decide

As of 2026-09-29. **Every row is answered** (21–25, plan 14, on 2026-09-29) (the answer sheet at the end). This is the one list. Every decision that blocks
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

---

## Answer sheet

Write the letter, or "rec" for the recommendation. Rows 14–17 take "keep"
or "overturn".

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
| 21 | P14-a overlay mode | (a) behind a config key, off | **(a)**, 2026-09-29 | built, plan 14 WP2 (PR #PRNUM): `[output] overlay = false` by default — the render window is created without a transparent framebuffer, `output.overlay` refuses to switch on (`T`, MASTER select, the panel's greyed toggle with the reason, a preset), the crossfader's ground does nothing; `true` is today's overlay |
| 22 | P14-b the party device | party opens; house moods a `house` show; last show remembered | **rec**, 2026-09-29 | built, plan 14 WP3 + WP4 (PR #PRNUM): the factory `default` show is gone — `party` opens, `house` holds the eight house moods; `<home>/last_show` remembers the show opened last; your `default` (MIGRATED + seven house moods) is renamed `mine` once, backed up as `default.hyp.json.bak-v2`, MIGRATED still its first preset; the PRESETS page speaks "show" |
| 23 | P14-c dream on by default | (b) optional torch, worker on, loud when missing | **(a)**, 2026-09-29 | torch is part of the app, not optional; plan 14 WP1 |
| 24 | P14-d F6–F8 effects | (a) ACID, MANDALA, NOITA | **(a)**, 2026-09-29 | plan 14 WP5 |
| 25 | P14-e desk glyphs and diagram | (a) K/D/S/G/B glyphs, up layer, above the cheat sheet | **(a)**, 2026-09-29 | plan 14 WP7 |
