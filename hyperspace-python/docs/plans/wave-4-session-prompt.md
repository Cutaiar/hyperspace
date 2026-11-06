# Wave 4 of the post-show plan: the opening prompt for the orchestrating session

Paste everything below the line into a fresh Claude Code session opened in
`/Users/dallman/antigrav_repos/hyperspace`. It is written for the session
that orchestrates, not for a builder: the orchestrator reads, briefs, reviews
and merges; builders build. It was planned by three independent read-through
agents on 2026-11-04 and reconciled by the wave 3 orchestrator.

---

You are orchestrating **wave 4** of the Hyperspace post-show plan: the last
wave of `hyperspace-python/docs/plans/tier-2-3-build-order.md`, rows 4.1–4.7,
corrected below. Waves 0–3 are merged to `main`. The owner (Dan) wants it run
as wave 3 was: one builder per item in its own worktree on Opus, one PR per
item to `main`, an independent review and fix round on every PR, and a union
branch proving the PRs together before anything merges.

## Read first

1. `docs/plans/wave-3-session-prompt.md` "How to run it" and "Rules", and the
   lessons below.
2. `docs/plans/44-decks.md` §3 D5, D6, §4–§8, then
   **`docs/plans/44-decks-d5-d6-reading.md`**, where it is wrong against the
   code: seventeen rows, the split, the proofs, decisions DQ1–DQ8.
3. **`docs/plans/53-node-mode.md`**: the outline for N1–N3 and B2, decisions
   NQ1–NQ9.
4. **`docs/plans/wave-4-inherited.md`**: open PRs, pending rows, rough edges,
   CI health, hand-check priorities.
5. `REVIEW.md`, `docs/ENGINEERING.md` §15 and §16, `docs/ARCHITECTURE.md`
   §3–§4, and plans 49, 51, 52.

## The owner's answers, 2026-11-04 to 06 (these overrule anything below)

**The preset is the authority; a deck is a device.** A deck is the mechanism for
swapping quickly between presets and choosing which graph renders, holding only
what must be shared to keep decks in step, such as the clock. Any work in this
wave is judged against that line.

**The session count.** The owner asked why 256 of the 548 params undo watches
are session params. Counted at 0ab49d7 (`boot`, no effect files loaded, so `fx.*`
effect knobs are not in the 548):

| Session group | Params | What they are |
| --- | --- | --- |
| `hands` | 165 | 9 global + 13 shaping knobs × 12 axes |
| `band` | 78 | 6 audio bands × 13 knobs |
| `desk`, `master`, `output`, `scene`, `ghost.mirror` | 13 | the rig's feel and master levels |

A session param is **not** held by a deck: it is one object both decks share, and
none is in a preset. 243 of the 256 are those two tables of shaping knobs. Plan 43
ruled both "the rig" (`43-preset-contract.md`, the `hands.*` and `band.*` rows:
"the picture is the same with the music off"). Whether `band.*` stays there under
the line above is **Q7**, open. The undo problem is not a size problem: one shared
param has it as much as 256, so DQ2 stands whatever Q7 answers.

**Node mode** (overrules NQ1, NQ3, NQ9, and N3 as written; `53-node-mode.md` is
updated):
- **You choose the deck, per controller.** A controller can enter node mode on a
  preset being built off air, while someone else plays the on-air preset with a
  different controller. From the on-air graph, an operator can attach a controller
  a performer is holding to a node ("you're on the wobble node for a while"). So
  the panel must be able to look at either deck's graph, not only the one HOLD
  gives it, which D5a and D5d have to allow.
- **The cables are not temporary.** A node mode cable is its own cable kind, a
  colour other than the white control cables, drawn and labelled, and **saved in the
  preset**. Whether a controller is in node mode and which node it points at are
  preset state. Open the preset and they are back; choose another node and it
  switches. So **N3, "keep this one", is gone**, NQ9 with it, and NQ3 is answered.
- The consequences to build: a preset format move (see NM0), and re-pointing a
  controller is an edit of the preset.

**The meta controller, second round.** "The meta controller" is the owner's name
for what the code calls the session (`SessionRegistry`, `SessionTable`): what is
tuned to facilitate a performance and should not be actively modified during one.
- **The analyzer's tuning and the hands' shaping are the meta controller's.** The
  music in a room has low variance across a show, so no preset retunes the analyzer.
  **Q7 is answered: `band.*` stays.** What plugs into the analyzer is the preset's:
  it is a fixture on the graph every preset may wire from. The code already has this
  shape (`graphview` draws one `analyzer` node; routes are the preset's).
- **"Band" is a bad name.** It becomes the analyzer, in words first (AZ). The ids
  are a format move and ride with NM0 and NSEW, or stay.
- **Undo: one stack per deck slot, scoped to its preset, and one for the meta
  controller.** Replaces DQ2. `Undo` already takes one registry and one table, so the
  fifth is an `Undo` over the `SessionRegistry` and `SessionTable`, and a deck's stack
  watches `part_of == "performance"` only. Two things to settle in D5b: U1 and U2 below.

**Players.** Controllers are generic; the actors are named: player 1, 2, 3, 4.
- People hold a controller for a long time across presets. The performer on air stays
  the performer when another preset goes on air; a second controller is assumed to be
  for an off-air deck, and may point at a node or param on air by choice.
- **One controller points at one preset at a time.** Mapping on another deck moves it
  there. So **NM3 is answered**: the decks cannot both hold it.
- **NM1 is answered:** editing a controller's mapping is an edit to the preset.
- **NM2 is answered:** a pad remapped between presets is how it is supposed to work.
- A preset names a **player**, not a device. Plan 27's roles (`axis@p2`, "roles, not
  serials") are the seam. Today's bare `pad:` and `axis:` rows read as player 1, with
  no file change. See PL.

**Third round, 2026-11-04.**
- **Two slots only: on air and off air.** Not four yet. Row 556's "N free" waits.
- **Q8 answered, players and duties.** A player registers any number of controllers
  and holds a duty: on air or off air. It stays until someone moves it. An off-air
  player stays with the off-air preset. The workflow to serve: explore a new preset on
  the graph, promote it, then join Dylan exploring it on air.
- **PS, the player select screen.** Like a console party game's team screen: every
  active player, the controllers they hold, and two lanes, On Air and Off Air. Move a
  player across by stick or mouse. It must be effortless. Built on PL.
- **Q9 answered: a hard rule.** No route from a preset onto a meta param. Tuning like
  `master.gain` happens before the show, and the refusal shows quickly which meta params
  belong in the preset. Item MR. Read-only count of the Drive library, 2026-11-04: **49
  rows in 48 of 110 presets are one row, `hand:left.y → master.gain`, push 0.375**,
  copied down from `party-tumble`; 2 more are `axis:RX → master.dyn`. So the rule's first
  visible result is that the left hand stops driving audio in those looks.
- **U1, U2 as recommended:** ⌘Z by where you are; a load is a step on the slot's stack.
- **Q1, Q2 as recommended:** merge on green for wave 4; checks 489–492 before D5d, and
  506–509 before N1.
- **The names (SEM).** The code's concepts must come to follow the owner's words, once.
  See "The semantic migration" below.

**Fourth round, 2026-11-04: two layers, and they do not leak.**
- **The concept:** there are two layers of granularity and no others.
  - **The meta controller:** everything set for a performance, tuned for a performance
    or an install.
  - **The preset:** where anything can change anything, a complete visual look you can
    play.
- **`rig`, `session` and lowercase "deck" all become the meta controller.** That is what
  "the rig goes away" means: the rig was a leaky, non-isolated abstraction, and the word
  goes with it. **Capital `Deck` stays:** it lives inside the meta controller and just
  represents a loaded preset.
- **Misplaced params present themselves later.** Nothing moves between the layers now. A
  param in the wrong layer is found in use and moved then. To trust that, the two layers
  must be completely consolidated and orthogonal, so that neither can leak into the other.
- **PS1 answered:** the party-game lanes are how it is drawn, not how it is driven. **The
  mouse moves players.** No stick input on the select screen.
- **MR1 answered:** drop the row with a note; a later save removes it. The owner: the
  `hand:left.y → master.gain` row is "quite annoying", and `axis:RX → master.dyn` is not
  wanted either, so nothing is lost. A desk row on `master.gain` (the APC's MASTER fader) is
  the meta controller's own control and stays.

**Fifth round, 2026-11-04.**
- **The absolute rule: no preset can affect another preset.** Not a question to ask. Any
  path by which one can is a bug, or a sign the thing belongs in the preset. D5d's leak
  test runs both ways. A row acts only on the `Deck` its player is on, which answers DQ4.
  The one accepted exception is the shared dream worker (DQ8), a known limitation.
- **The dim and the crossfade are separate controls.** The master dim is the meta
  controller's. Overturns row 559 and plan 44 §5. **A crossfade may fade into an empty
  `Deck`, which renders black,** as a DJ mixer fades into silence. The refusal in DQ3 is
  gone.
- **Changing what is on air is intentional, never from the desk.** Bank pads, the D-pad's
  preset list and `preset.next` load only into the off-air `Deck`. Answers DQ6.
- **The playlist is for installations:** leave the cart running, a new look every five
  minutes. It is not used alongside live editing, so it needs no guards against the
  operator. D6 gets smaller; DQ5 is answered: seconds, `playlists/`, no pausing.
- **No second dream worker.** DQ8: a known limitation. DQ7 as recommended.
- **Node mode:** no latch button and no paging. A node's params fill the controller's
  degrees of freedom, faders and knobs both. A node that does not fit is a node with too
  many params: list them, as the meta routes rule lists its rows; do not page. You enter
  from the panel, with a node already selected; a node with no params cannot be entered
  (NQ4). A mapping already on that node's params stays, and the rest fill what is left
  (NQ6). NQ5 and NQ7 as recommended.

**Sixth round, 2026-11-04: nothing is pending.**
- **HOLD, TAKE and DROP go away entirely.** The owner never asked for them. With an on-air
  and an off-air `Deck` there is nothing to hold. Two verbs remain: the crossfade, and "copy
  on air to off air". `hold.py` goes, and so do `output.hold`, `.take` and `.drop`. DQ1 is
  gone. Where `44-decks.md` and its reading say TAKE, read "the crossfade"; a timed
  fade is a control on the crossfade, which the playlist also uses.
- **The crossfader is a DJ mixer's.** The APC crossfader is the deck crossfade, the MASTER
  fader is the dim, and `master.gain` moves to the panel: it is pre-show tuning. Two fixed
  `Deck`s and **no swapping**. On air is whichever the fader is closer to; on-air players
  move across as it passes the middle. So D5c has no `swap`. DQ3 is gone.
- **No swapping presets from a controller or a pad.** The D-pad's preset list rows go. See
  the assumption below on bank pads.
- **Base chase is Back** (`pad:VIEW`). NQ8 is answered.
- **Tap tempo is not a default on every controller.** It is an extremely sensitive control.
  `pad:VIEW → tempo.tap` leaves the factory rows. It lives on the APC, and possibly on one
  specific Edge button (not by default: Learn it if wanted).
- **PA, new: toggles pair into a polarised axis.** A long-standing gap. D-pad up and down
  are one degree of freedom with two poles, left and right another. Today each is a discrete
  toggle. Pressing one moves along one pole, the other along the other pole. Whether a press
  steps or nudges a spring is a separate, later choice: the point is the pairing, for any two
  discrete controls. Node mode counts such a pair as one degree of freedom. Goes with NSEW.

**An assumption, on the owner's word to change:** "swapping presets on a controller or a
pad" is read as removing the gamepads' preset rows. The APC's bank pads and `preset.next`
stay, and load only into the off-air `Deck`. If they should go too, it is a one-row change.


**Seventh round, 2026-11-04.**
- **Timing:** the show is in the near future, not today. Every wave lands before it (the
  owner, final: see the eighth round and the schedule's note). The first draft of this bullet
  split small items from the spine on a recommendation, which the owner overruled.
- **A controller is generic, with extensions.** The APC is not a separate kind of thing: it
  inherits the generic physical control system and has extensions, the way the DualSense Edge
  does, by which it may talk to the meta controller. Some of its controls are reserved: not
  learnable or bindable by a preset, and mapped exclusively onto meta params, such as the
  crossfade. Another MIDI desk like it gets the same. So no new Learn road is needed for now:
  a preset's Learn desk on a meta param stays refused.
- **Hold-to-save is the Edge's only.** It is Dylan's controller for VJ-style setups. For
  controllers held by anyone else, a press-and-hold save should not be mapped at all. So
  `pad:MENU → preset.save_new` leaves the generic factory rows and becomes an Edge extension.
  Not on the Joy-Con.
- **`preset.*` and `deck.chase` become meta params,** decided with SEM after a sweep of which
  desk rows are factory ones. Preset loading must be very intentional.
- **"Band" is right for one bin:** EQ uses the word. "6 bands", SUB to AIR, as AZ built it.
- **Base chase on a Joy-Con:** − or capture if free, else a trigger or bumper. #365 gives both
  to the totem, so: **L on the left, R on the right.** That row belongs to #365's layout, so
  it is that session's to add.

**Eighth round, 2026-11-04.**
- **Every wave lands before the next show.** Final, and it replaces any split into "before
  the show" and "after it". Nothing is held back until after one.
- **Patch and loadable patch replace "preset" as the words.** A patch is the concept; a
  loadable patch, a preset today, is a patch with no wires coming out. New text uses them; old
  names in code stay until SEM. `docs/GLOSSARY.md` waits for the owner and is not edited.
- **Shows and sessions go.** Tuning moves to one meta controller file per install, with the
  bank beside it. **Open:** where the bank belongs.
- **Venues probably go.** Composing displays and peripherals in the app is new work, not
  scheduled in this wave.

**Ninth round, 2026-11-06.**
- **The gate on D5d is dropped:** "we can drop the gate". Checks 489–492 no longer hold #380; try
  #380 on the rig before SEM starts, if that can be done.
- **Bank pads and F-keys load off air** (row 700, on #380, option (b)): always into the off-air `Deck`, never
  touching the room, and refused while the crossfader is between its ends. A load is a meta
  controller verb. The panel's own load still goes to the `Deck` the panel is looking at.
- **The glossary is signed**, reviewed with Dillon. `docs/GLOSSARY.md` now says patch and loadable
  patch. SEM follows it.
- **FQ3–FQ7 as recommended, and one migration:** see `57-format-lane.md` §6.
- **Wave 5 is to be planned now,** with its launch prompt. It runs after this wave lands.

## Joy-Con version 0 (#365), from another session, 2026-11-04

The Joy-Con integration was scaled back to a workable control surface for an upcoming
show. Draft PR #365 (`origin/worktree-joycon-v0`) belongs to that session: do not change
it. The owner holds it until the Joy-Con is hand-checked.

- **Where it lands:** before N2a and the NSEW build. If hand checks slip past those, ask
  the owner; do not build against a `main` without it.
- **Its layout** lives in `models.Model.layout` and `routing.layout_of`, and replaces table
  rows on those controls: SL / SR previous and next shape in both modes, stick click view
  reset, − (+ on R) totem reset, capture (HOME on R) totem on and off. L and ZL are free.
  Stick routes act only with the totem on. `Router.pad(skip=)` holds layout rows off too.
- **Numbers:** rows 686–687, checks 520–521, group BW stay #365's.
- **The rule for wave 4:** a PR touching `routing.py`, `devices.py`, `gamepad.py`,
  `totem.py`, `pads/models.py` or `ui_pad.py` merges `origin/worktree-joycon-v0` into a
  scratch branch and runs `tests/test_joycon_v0.py`. The keeper holds the combined proof on
  `origin/scratch/wave4-joycon`. B2 has a real code conflict with it in `routing.py`.
- **N2a must** make `PadDevice._quiet_stick` and `steer` stand down on the axes a node mode
  holds, or that stick is dead and the view orbits under it.
- **What the owner's later answers changed in the note:** N2 has no page key, so the clash
  on SR is gone. A Joy-Con enters node mode by the panel chip (NQ7). Base chase moved to
  Back, which #365's layout gives to totem reset on the (L), and the (R) has none. B2's
  row 724 suggested SL, which #365 holds, and Learn cannot arm the chase from the panel.
  **Answered:** L on the left, R on the right, in #365's layout.
- **The order, all of it before the next show:** AZ, MR, B2, PA and #365: small, wanted, and
  each one hand-checkable. Then the rest of the spine, which touches every controller's path.
  AZ, MR, B2, PA, D5a and D5b are merged; #365 waits for its hand check. On #365's merge, add the one `control_free` line in #372's body and take the keeper's
  `routing.py` shape from `origin/scratch/wave4-joycon`.

## The semantic migration (SEM)

**Slot it right after D5d, as stage 4.5.** D5d deletes `hold.py` and settles the deck
model; before it, the names are still moving, and from stage 5 four parallel lanes write
new code against them. It is a rename and nothing else, so it needs a quiet moment rather
than a long one: no other PR open, one builder, goldens unmoved. The rename is mechanical;
the wall it adds (below) is not, so it is sized M–L, and it may be two PRs.

| The owner's word | The code today | Note |
| --- | --- | --- |
| meta controller | `session` (486 uses; `SessionRegistry`, `SessionTable`, `part_of == "session"`), `rig` (517 uses; `RigWires`, `RigMade`), lowercase "deck" in prose | **One concept, settled 2026-11-04.** The word `rig` goes |
| `Deck` | `Deck` | **Stays:** a loaded preset, living inside the meta controller. "Slot" is not a type: on air and off air say which `Deck` |
| analyzer | `band` (336 uses) | Words in AZ; ids stay (FQ3) |
| player, duty | none yet | New: named right from PL |
| patch, loadable patch | preset, and "performance" (`part_of`) | The eighth round's words, replacing "one word: preset". Old names stay until SEM |

**SEM must also make the line hold mechanically,** not only rename it: every param is in
exactly one layer, a test fails on anything in neither or both, and an import wall keeps
the preset layer from reaching into the meta controller except through its named surface.
D3 made `part_of` mechanical; this finishes the job. **#223 venues** and `config.toml.rig`
are the meta controller's install side, to be folded in at SEM or just after: ask then, and
Dillon owns that PR.

Three rules, starting now:
1. **A glossary first.** D5a's PR adds `docs/GLOSSARY.md`, one row per concept, and the
   owner signs it. It saves arguing in every PR.
2. **New code uses the new words from today.** D5a is about to add a `Decks` class: it
   must not. Name it from the glossary, and PL's `Player` and `Duty` likewise. Old names
   stay until SEM, so no PR renames in passing.
3. **Code in SEM; files in the format lane.** A saved key or id (`session` in a show,
   and so on) is a format move and rides the one migration. SEM touches only names in code.
   If a saved name cannot change cheaply, it stays and the glossary says so.

Merge order is unchanged by it. It holds the lanes between D5d and stage 5.

## The schedule

A wave is a dependency level. Width is limited by what freezes, not by builders. Wave
3's run shows about a day for nine PRs at this review depth, so the limit is the
owner's hand checks and show dates, not build time.

| Stage | Serial spine | In parallel | Merges when |
| --- | --- | --- | --- |
| 0 | Owner: sign the glossary (**signed 2026-11-06**) | #363; #365 when its pad charges | now |
| 1 | **D5a** pointers, with one deck pointer per player; `docs/GLOSSARY.md` (**merged**, #370) | B2, PA, AZ, MR, PC, NSEW design | green |
| 2 | **D5b** per-slot and meta undo (**merged**, #373) → **PL** players and duties | NSEW build | green |
| 3 | **D5c** copy, swap, take | **PS** the select screen; NM0 (needs PL); the format lane | green |
| 4 | **D5d** controls, `hold.py` gone | none on `ui_graph.py`, `preset.py`, chase lines | checks 489–492, between shows |
| 4.5 | **SEM**, the rename, alone | nothing open | green, goldens unmoved |
| 5 | **N1a + N1b**, stacked | D5e; D6a; #287 | N1: checks 506–509 |
| 6 | **N2a + N2b** | D6b | green |
| 7 | | PC words pass, row 668 if wanted | green |

- **Every wave lands before the next show (the owner, final).** No stage waits until after
  one. "Between shows" below means not during one, and the show is the deadline for all of it.
  D5a and D5b are merged; PL is next on the spine.
- **The spine is serial on purpose.** D5a–D5d freeze `deck.py`, `app.frame` and the
  handles, then `ui_graph.py` and `preset.py`. Everything else stays off them.
- **One format lane, one migration.** NSEW, the patch words and shows going all touch saved
  files. Build them apart, land them as one bump with one backup, between shows, both
  Macs together. Two bumps in a week is what the rule warns against.
- **Players go before node mode and after undo:** NM0 saves player names, and D5a's
  pointer is built for them, so nothing is written twice.
- **Peak width is about four builders** (stage 5), against eight in wave 3. Stage 1's
  side lane can start the moment the answers land; it depends on no deck work.

## What changed against the build order

- **D5 is five PRs, D6 two.** Pointers, undo, copy-and-swap, the controls, the
  words. No schema moves in either.
- **N1 and N2 split in two**, drawing apart from behaviour; NM0 is new and N3 is
  gone. N1a must not reach a show without N1b: rows that act and are not drawn
  are hidden edges. Stack them and merge together.
- **Row 4.7 is smaller.** #314 merged on 2026-11-02 (cf96377), so nothing
  rebases. Its "pad rows ride in patches" is not true of the code:
  `patches.check` refuses them, and riding needs app code and a ruling on row
  554. Not this wave, unless Dillon has vetted ideas on a real Edge. #287 is a
  rewrite on main **after D5** (its one dial dict meets per-deck registries).
- **North / south / east / west gates nothing.** Row 545 renames only the
  four-button cluster and the D-pad; "the extras from 32 stand". B2's `pad:LP`
  and N2's LB / RB page keys are untouched. It is still worth this wave, after
  #365, because every wave adds `pad:A/B/X/Y` rows (119 uses in 22 files), and
  it ships a migration.
- **`pad:LP` / `RP` are not Edge-only:** a Joy-Con's SL and SR read as them.

## The items

| Id | Item | Lane | Size | After | Neutral? |
| --- | --- | --- | --- | --- | --- |
| D5a | `Decks`, read-through pointers, both on deck 1 | Core | M–L | P3 merged | yes |
| D5b | Each deck's undo and dot; the session rule (256 of 548 watched params are session) | Core | M | D5a | yes while panel = on air |
| D5c | `copy`, the timed fade, on air by the fader's side, the preview road, no caller but tests | Core | M | D5b | yes |
| D5d | The crossfader and MASTER fader rows; **`hold.py` and its three controls deleted**; the leak test, both ways | Core | M–L | D5c; **merge gate: checks 489–492** | no: the first thing the owner sees |
| D5e | Deck indicator, ROUTING's dormant words, desk diagram, SYSTEM | UI | S | D5d, DQ7 | UI only |
| D6a | `playlist.py`, its file kind, `tick` over stand-ins | Library | M | D5d, DQ5 | no behaviour yet |
| D6b | Triggers, the frame hook, a pane section, the warm draw | Library | S–M | D6a | |
| PL | Players 1–4: a player registers controllers on this Mac and holds a duty, on air or off air; bare rows read as player 1; plan 55 | Core | M | D5b | yes while one slot is pointed at |
| PS | The player select screen: active players, their controllers, the On Air and Off Air lanes drawn like a party game; moved by mouse | UI | S–M | PL | no |
| MR | The hard rule: no preset row onto a meta param; refused at Learn, in the picker, at load with a note; a report of what dropped | Core | S | nothing | no: the left hand stops driving audio in 48 presets, as wanted |
| SEM | `rig`, `session` and lowercase deck become the meta controller in code; the two layers held apart by test and import wall | All | M–L | D5d; no other PR open | yes |
| AZ | "Band" becomes the analyzer in the panel's words | UI | S | nothing | words only |
| NM0 | The saved node mode: player, node, page in the preset, the cable kind and its colour; in the format lane | Format | M | PL | format |
| N1a, N1b | APC: the rows from the saved state, per player and per deck; then the drawing | Core + UI | M + M | NM0, D5d, NQ2, NQ4; **merge gate: checks 506–509** | no |
| N2a, N2b | Pad: rows in the Router, steer off; pad page keys, pad window, drawing | Core + UI | M + M | N1a, #365, NQ5–NQ7 | no |
| B2 | Factory `pad:VIEW` row for `deck.chase`; `tempo.tap` and the D-pad's preset rows leave the pad's factory rows; existing `bindings.json` follows | Core | S | can go first | no |
| PA | Pair two discrete controls into a polarised axis; the D-pad as two degrees of freedom | Core | M | B2 | no |
| NSEW | North / south / east / west, with its migration | Controllers | M | #365, rows 546 and 552 | format move |
| #287 | Dial readings rewritten on main, beside N2 | UI | S–M | D5d; who does it, Q4 | no |
| PC | Pane paper cuts: T2 fine on ROUTING's sliders and GRAPH's backdrop (row 608); the save-as-patch row at `SIDE_MIN`; SEND B drawn free (row 609) moves into N1 | UI | S | U3; last | no |

N1 could branch after D5a, but it conflicts with D5d in `ui_graph.py` and its
deck question is only testable once D5d exists, so it waits. While D5d is open,
`ui_graph.py`, `preset.py` and `params.py`'s chase lines are frozen. While
D5a–D5c are open, `deck.py`, `app.frame` and the `Host` / `Panel` handles are.

**Land D5d between shows**, with HOLD, TAKE and DROP exercised at the rig before
one: it replaces a mechanism a show relies on. Until D5d, raising `output.xfade`
fades to black, so learn no fader on it for a show.

## Decisions for the owner

Ask at the start, with the recommendations, and proceed with what is not gated.
Details are in the two plan documents.

**Asked once, wave-wide:**
- **Q1.** Merge authority for the wave. **Answered, 2026-11-04:** merge on green.
- **Q2.** The merge gates. **Answered:** 506–509 before N1 (the gate of 489–492 before D5d was dropped 2026-11-06);
  build freely, gate merges only.
- **Q3.** NSEW in this wave, after #365? Rec yes. And row 546 (`controller =`'s
  form), row 552 (the pad draws its own face), which it touches.
- **Q4.** #287: Dillon or us? Rec ask Dillon; it must follow D5d either way.
- **Q5.** A bulk nod on about 80 "(rec)" rows, by group (`wave-4-inherited.md`
  §2), calling out 669, 668, 641. Rec ask once. Only 653 and 609 gate this wave.
- **Q6.** Merge #363 (the CI flags, green, one file). Close #342 once #365 lands,
  keeping `tools/poi_probe.py`.
- **Q7.** ~~Do the `band.*` knobs move into the preset?~~ **Answered:** no; the
  analyzer's tuning and the hands' shaping are the meta controller's.

**D5 and D6** (`44-decks-d5-d6-reading.md` §6):
| | Question | Rec |
| --- | --- | --- |
| DQ1 | What does DROP leave? | Panel back on the on-air deck, hold off, B parked |
| DQ2 | ~~Whose undo holds a session param?~~ **Answered:** the meta controller's own stack | |
| DQ3 | `output.xfade` moved by hand; with nothing armed | A fader to 1 completes the take; un-held it reads 0 and says why |
| DQ4 | A `turn` row off air | Dormant; row 684 reverses |
| DQ5 | The playlist under hold; on unsaved edits; dwell; where it lives | Pauses and says so; pauses on the dot; seconds; `playlists/`, two decks |
| DQ6 | Library verbs under hold | The panel's deck: library follows the panel, performance the room |
| DQ7 | How the panel says which deck it is on | Always-on head chip, title, red canvas frame while they differ |
| DQ8 | Second dream worker (row 653) | No now; measure at the rig after D5d |

**Node mode and B2** (`53-node-mode.md` §6):
| | Question | Rec |
| --- | --- | --- |
| NQ1 | ~~Which deck?~~ **Answered:** you choose, per controller | |
| NQ2 | APC keys (the desk is Dillon's; he signs) | SEND C latches, ◀ ▶ flip, sixteen knobs |
| NQ3 | ~~Temporary cables?~~ **Answered:** a saved cable kind of its own colour | |
| NQ4 | In node mode with nothing to point at | The desk returns to its layers |
| NM1 | ~~Re-pointing lights the dot?~~ **Answered:** yes, it is an edit of the preset | |
| NM2 | ~~A preset takes a pad?~~ **Answered:** remapping between presets is how it works | |
| NM3 | ~~Both decks claim one?~~ **Answered:** one preset at a time; mapping elsewhere moves it. A cable naming a player who is on another deck is drawn dormant | |
| NQ5 | A stick on the page | Push: the look comes back on release; chase keeps it |
| NQ6 | Axes a saved route already reads | Free axes only |
| NQ7 | The pad's latch, with no free button | A chip per controller, learnable; factory `pad:RP` only |
| NQ8 | B2's button | Factory `pad:LP`; the 360's GUIDE by one Learn |
| NQ9 | ~~Keep on a taken knob~~ **Gone** with N3 | |

B2 meets NQ1: a chase on the controllers' deck misses what a node mode on another
deck pushes, so a press from a controller in node mode targets that controller's
deck.

## Numbers

Plans through 53; 54 is free for NSEW, 55 for players. Register rows through 685 plus #365's
686–687; hand checks through 519 plus #365's 520–521; groups through BV plus
BW. Pre-assign (unused ones are fine; do not reuse 602–604 or 633–635):

| Id | Rows | Checks | Group |
| --- | --- | --- | --- |
| D5a | 688–690 | 522–523 | BX |
| D5b | 691–693 | 524–525 | BY |
| D5c | 694–696 | 526–528 | BZ |
| D5d | 697–702 | 529–534 | CA |
| D5e | 703–704 | 535–536 | CB |
| D6a | 705–707 | 537–538 | CC |
| D6b | 708–709 | 539–540 | CD |
| N1 | 710–714 | 541–545 | CE |
| NM0 | 715–717 | 546–548 | CF |
| N2 | 718–722 | 549–553 | CG |
| B2 | 723–724 | 554–555 | CH |
| NSEW | 725–728 | 556–558 | CI |
| #287 | 729–730 | 559–560 | CJ |
| PC | 731–732 | 561–562 | CK |
| PL | 733–736 | 563–565 | CL |
| AZ | 737–738 | 566–567 | CM |
| PS | 739–742 | 568–571 | CN |
| MR | 743–745 | 572–573 | CO |
| SEM | 746–747 | 574 | CP |
| PA | 748–751 | 575–577 | CQ |

## Lessons from wave 3

- **`gh pr merge --auto` merges at once here:** `main` has no required checks.
  Wait for this head's CI, then merge. `merge-on-green`, as a small script
  taking the PR and the expected head: confirm the head, wait for its runs, stop
  on anything but success.
- **A red run twice on one head is not a flake, and a green run is not a fix.**
  #361 failed twice on a test it does not touch. The cause was on `main`, a stray
  GL free from `tools/golden_frames.py`, intermittent (4 of 9 runs), fixed in #366.
  Diagnose with logged CI runs from a separate agent.
- **Stacked PRs after a squash.** Merge the parent's final head into the child,
  record the squash with `git merge -s ours <squash>` after confirming the two
  trees are equal (stop if not), then merge `main`. The diff over main is then the
  child's own. It took the keeper four clean rounds; no code was lost.
- **Reviewers repeat themselves and are sometimes wrong.** Two of four findings
  on one pass did not hold up against the code. Builders verify; a disproved
  finding gets a test, not a change.
- **A worktree-isolated session cannot run git elsewhere.** The keeper runs
  union work; run `--all` in the keeper's worktree through the slot wrapper. A
  two-slot `mkdir` wrapper kept the Mac out of trouble with eight builders.
- **Reviews from the orchestrator's scratch worktree, one at a time.** Never the
  owner's checkout, which may be on a test branch for the owner's hand checks.
- **Keep the union where the owner is testing it.** The owner hand-tested a local
  branch tracking `origin/wave3-union`; the union stayed put through the merges.
- **Goldens:** `--all` on the union before the first merge, again on the step that
  moves the renderer. Wave 3's D4 moved none.

## Rules

As in wave 3: branch from `main`; a PR on an unmerged one stacks and retargets;
behaviour-neutral steps are tested as such; a schema move ships a migration and a
backup, and lands between shows with both Macs together; restart, not hot reload,
for a new module or a field on a long-lived object; docs land with the code; report
failing tests with their output, a skipped step as skipped.

After the last merge, both Macs pull, `uv sync` and restart; hand checks for the
wave; write up what wave 5 inherits (the grand cleanup pass first, and which params
have shown themselves misplaced between the two layers) and stop.
