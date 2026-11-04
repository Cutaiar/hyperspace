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

## The owner's answers, 2026-11-04 (these overrule anything below)

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

**Last questions, pending:** HT (HOLD, TAKE, DROP), XF (the crossfader), B2's button.


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
| analyzer | `band` (336 uses) | Words in AZ; ids in the format lane or never |
| player, duty | none yet | New: named right from PL |
| preset | preset, and "performance" (`part_of`) | One word: preset |

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
   `band.*`) is a format move and rides the one migration. SEM touches only names in code.
   If a saved name cannot change cheaply, it stays and the glossary says so.

Merge order is unchanged by it. It holds the lanes between D5d and stage 5.

## The schedule

A wave is a dependency level. Width is limited by what freezes, not by builders. Wave
3's run shows about a day for nine PRs at this review depth, so the limit is the
owner's hand checks and show dates, not build time.

| Stage | Serial spine | In parallel | Merges when |
| --- | --- | --- | --- |
| 0 | Owner: PS1, MR1, DQ1, DQ3–DQ8, NQ2, NQ4–NQ8; sign the glossary at D5a | #363; #365 when its pad charges | now |
| 1 | **D5a** pointers, with one deck pointer per player; `docs/GLOSSARY.md` | B2, AZ, MR, PC, NSEW design | green |
| 2 | **D5b** per-slot and meta undo → **PL** players and duties | NSEW build | green |
| 3 | **D5c** copy, swap, take | **PS** the select screen; NM0 (needs PL); the format lane | green |
| 4 | **D5d** controls, `hold.py` gone | none on `ui_graph.py`, `preset.py`, chase lines | checks 489–492, between shows |
| 4.5 | **SEM**, the rename, alone | nothing open | green, goldens unmoved |
| 5 | **N1a + N1b**, stacked | D5e; D6a; #287 | N1: checks 506–509 |
| 6 | **N2a + N2b** | D6b | green |
| 7 | | PC words pass, row 668 if wanted | green |

- **The spine is serial on purpose.** D5a–D5d freeze `deck.py`, `app.frame` and the
  handles, then `ui_graph.py` and `preset.py`. Everything else stays off them.
- **One format lane, one migration.** NSEW, NM0 and any `band` id rename all touch saved
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
| D5c | `copy`, `swap`, `take`, the preview road, no caller but tests | Core | M | D5b | yes |
| D5d | The controls on `Decks`; **`hold.py` deleted**; plan 38's leak test | Core | L | D5c, DQ1–DQ4; **merge gate: checks 489–492** | no: the first thing the owner sees |
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
| B2 | Factory `pad:LP` row for `deck.chase` | Core | XS | NQ8; can go first | no |
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
- **Q2.** The merge gates. **Answered:** 489–492 before D5d, 506–509 before N1;
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
