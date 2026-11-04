# Plan 44, D5 and D6 read against the code (wave 4 planning, 2026-11-04)

Tags: **[V]** read in the code. **[P]** seen in a headless probe (`boot` over a temp home, `Deck.beside`; no GL, no library). **[I]** my inference, not run.
P2 (#361) and P3 (#364) grepped: their code never touches `hold`, `panel.deck` or `canvas_renderer`; both edit `ui_graph.py`, so they land first. Paths are under `hyperspace-python/hyperspace/`.

## 1. Where plan 44 is now wrong

| # | The plan says | The code says | Consequence |
|---|---|---|---|
| 1 | §3 D5 is one L PR | Pointers, undo, copy, swap, controls and UI each have their own proof | Five PRs (§2) |
| 2 | §4 Drop = `copy(on_air, panel)`; `output.hold` reads on while panel's deck differs; ⌘Z restores | After such a Drop the panel is still on B, so hold stays lit and only a TAKE releases it, which restarts the dream. Today's tip and `test_the_output_controls` say Drop lets go (`hold.py:206-212`) [V] | **DQ1** |
| 3 | §4 copy = `reg.restore(src.reg.snapshot(g))` and field by field | `Registry.restore` with no `trims` empties the chase ledger (`params.py:1108-1126`) [V]. B lands base + whole push where A lands base + push − trim: a jump after any chase with a push still out [I] | Copy carries the trims; test below |
| 4 | §4's copy list | Omits the pose, `inst_phase`, `media_phase` (per-deck `ViewState` now) and banks' running state; only the pose is in a preset doc (`preset.py:56`) [V] | Copy = doc road + an explicit list (§3 D5c) |
| 5 | §2/§3 "undo per deck" | **256 of 548 watched params are session** (hands 165, band 78, desk 6, master 3, output 2…) [P]. Each is one object in both registries, and `watched` does not ask the part (`undo.py:91`). Deck 2 is never ticked today (only `h.undo.tick`, `app.py:1284`) [V]. Tick both and one knob makes two steps; ⌘Z on B then restores a stale `master.gain` through `_differs` (`undo.py:525`): the room moves from the panel [I] | **DQ2** |
| 6 | §3 "Marks are the panel's deck's" | `Marks.take/put` read `self.lib.presets`, so deck 2's marks read deck 1 (`library.py:1642`, `:1722`) [V, P]. They also carry `lib.project.mark()`, the show's, on a per-deck stack [V] | `Marks(lib, presets)` in D5b |
| 7 | §3 lists midi, gamepad, hands, bridge, OSC as the retargets | Missed: `SeqPage.reg` kept at first registration (`seq_page.py:170`), and `table.page` is one object on both tables [P], so after a TAKE SEND A's page reads the old deck. `Library.reg` from `attach` (`library.py:1833`): `Library.restore`/`reset` (`:2451`, `:3410`) write it, and a `pattern` strip exists on the panel (`ui_patterns.py:233`), so a Reset under hold would hit the room [V road, I effect]. `dream_check` closes over deck 1's `reg` and listens on deck 1's presets only (`app.py:1725`, `:1729`). `Mouse` keeps five `Param`s (`app.py:1010-1011`). `draw_render` closes over `renderer, s, hold` (`app.py:1696`) [V] | All in D5a's list |
| 8 | §3 "MidiIO.reg is a property" | Also needed: `_writes` (`midi.py:1329`) and row catch state hold A's numbers; `layer_serial` is what re-arms pickup and redraws (`routing.py:2564`) [V]. Swap must bump it or LEDs and faders read the old deck [I] | Swap test over fake ports |
| 9 | §6 load the entry "into the deck not on air and not the panel's" | Un-held, the panel **is** the on-air deck (§1), so that rule picks B, and after the take the panel sits on the parked deck: an accidental hold [I]. Under hold with two decks there is no third | **DQ5**; panel follows when un-held |
| 10 | §6 implies `Presets.load` into any deck | `Presets.load` → `lib.load(GROUP, …)` → the kind's hooks, bound to one instance (`preset.py:878-886`, `:922-927`); `load_doc` pushes on the module's installed `Undo` (`preset.py:1165`), the panel's; `dream_check` and `Project.follow` hang off it [V] | D5a gives the kind a read-through and `Library.load(…, into=)`; push through `undo.watching(reg)` |
| 11 | §2 "renderer built up front avoids the stall"; §4 "trails carry on through the fade" | `FxChain._program` compiles lazily at draw (`fx.py:1096`) [V], so B's first draw after a copy or load compiles on the room's thread, the same stall row 648 warned of [I; not measured]. Off air B draws nothing unless GRAPH asks, so a copied feedback look has no trail at TAKE, and a delay drawn at preview size then at output size has no continuity I could confirm [I] | Warm draw in D5c/D6; wording on the head; check at the machine |
| 12 | §2 hands' turn "own deck's camera" (plan 51 §6) | After a copy B holds the `turn` row too. `_turn` has no off-air test; only session targets are dormant (`routing.py:3886`, `:3904`) [V]. An orbit at the room then writes B's camera, opens "orbit" on B's stack and lights B's dot while the operator edits it [I] | **DQ4** |
| 13 | §5 `xfade` "at 1 roles swap and xfade is 0" | Fits a timed take. A learned physical fader sits at the top while the value reads 0; `Binding.pickup` defaults on (`routing.py:649`), so it re-catches at the bottom [V field, I behaviour]. Un-held, B is empty or parked: the known fade to black or to a stale look | **DQ3** |
| 14 | `test_hold.py`: 37 tests, 7 kept | 40 `def test` today, 1121 lines [V]. By the names, about 15 are promises, not mechanism: all four `on_gl`, both bus-cut, Drop one step, Drop after a whole look, load resets delays, eye and turn under hold, the controls, lit buttons, head line, the two `_draw_render` ones, inset. Also `test_hold_thumbnails.py` (5), `test_base_chase.py` (4 sites), `test_hands_orbit.py:817-841`, `test_deck.py:474,499` [V] | Budget for 15+ rewritten, not 7 |
| 15 | Row 625: "kind is the deck built last" | Already settled: `claim=not beside` keeps deck 1 (`deck.py:253`, `preset.py:878`) [V] | D5a retires `claim`; `lib.presets` becomes the panel's pointer |
| 16 | §2 `preset.*` load into the panel's deck | True by accident: `preset.*` and `deck.chase` are per-deck objects of part None [P], yet the bank's triggers reach `Project._loader()` → `lib.presets` (`library.py:1078`) [V]. So a desk's bank pad under hold loads into B | **DQ6** confirms it; `deck.chase` goes to on air via the handle |
| 17 | Parked decks are not mentioned | After TAKE or Drop the other deck keeps running pass, integrate and media poll (`app.py:1327-1330`, `:1344`, `:246`), holding sources open [V]. Row 653's 118 µs was an *empty* deck | Skip the pass when parked (D5d), measure |

The leftovers you named:
- Deck 2 empty, fade to black: row 13, fixed in D5d.
- `xfade_s` has no reader: `Decks.take`, D5c.
- ROUTING dormant words: D5e (`ui_routing.py:896-931` asks nothing of `reg.lands`) [V].
- `draw_size`'s preview branch: D5c, called from the backdrop; it imports `preview_size` from `hold.py`, so that moves first (`deck.py:53`, `app.py:95`).
- `_preset_part` and the mirror: gone with the doc road, since `_values` uses `snapshot(part="performance")` (`preset.py:1406-1408`) [V]; a test pins it.

## 2. The split

| PR | Concern | Size | After | Neutral? |
|---|---|---|---|---|
| **D5a** | `Decks` and read-through pointers, both on deck 1 | M–L | P2, P3 | yes |
| **D5b** | Every deck's undo and dot; the session rule | M | D5a | yes while panel = on air |
| **D5c** | `copy` and `swap`, no caller but tests; preview road | M | D5b | yes |
| **D5d** | The three controls on `Decks`; `hold.py` deleted; head chips | L | D5c, DQ1–DQ4 | **no: the first thing the owner sees** |
| **D5e** | Words: deck indicator, ROUTING dormant, desk diagram, SYSTEM | S | D5d, DQ7 | UI only |
| **D6a** | `playlist.py`, the file kind, `tick` over stand-ins | M | D5d, DQ5 | no behaviour until D6b |
| **D6b** | Triggers, frame hook, pane section, warm draw | S–M | D6a | |

Total about 1.5 times the build order's "L + M". **Parallel opening:** N1–N3 need only "the published selection and the deck pointer", so N1 can branch after D5a rather than all of 4.1 [I]. It conflicts in `ui_graph.py` with D5d, so land N1 before or after, never overlapping. B2 and Dillon's #287, #314 are independent of all this.

## 3. Each PR

### D5a: pointers (restart)
**Owns:** `deck.py` (`Decks`: `decks`, `on_air`, `panel`, `point(on_air=, panel=)`), `devices.py` (`Context`), `midi.py` (`reg`, `table`, `learner` as properties), `seq_page.py`, `app.py` (`Host` flat fields as properties, `Mouse.use`, `draw_render`, `dream_check`), `ui.py` (the handles as properties with setters, since tests assign them), `library.py` (`presets`, `reg`, `load(into=)`), `preset.py` (retire `claim`; kind hooks read through), `undo.py` (`install` on panel move), `hotreload.py`.
**Freezes:** those files; `ui_*` reads stay as they are, through the properties.
- Learn: `h.learn` = panel's; `MidiIO.learner` the same.
- On air: `router=`, keys, sinks, `reg["view.depth4"]`, the mouse.
- Stick to: `devs.poll(router=)` already passes the router each frame, so the pad needs little (`devices.py:815`, `:837`) [V].
- Id parity check: boot shows nothing only on deck 1, while **deck 2 alone holds 142 `fx.*`** (an empty deck has every file) [P]. Boot skips the totem and poi hooks, so assert it on the app's hook list; `totem.state_of(reg)` params may be missing on deck 2 [I].

**Proof:** goldens unmoved; D1's and D2's same-state tests; `test_app_boundary` ORDER unchanged; all of `test_hold.py` still green (hold is still there, on deck 1); a new `test_pointing_the_handles_at_deck_2`: `Decks.point` in a test sends MIDI, the pad and the mouse to one deck and every `panel.*`, `lib.presets`, `undo.installed()` to the other, with no row or base crossing; `test_every_swap_target_lives_in_a_watched_module` over `Decks`.

### D5b: undo and dot (restart)
**Owns:** `undo.py`, `library.py` (`Marks(lib, presets)`), `app.py` (tick the decks), `deck.py`.
Implements DQ2. Proof: `tests/test_undo.py` as it stands; `test_session_params_are_covered` restated; `test_undo_is_per_deck`; `test_the_dot_is_per_deck`; `test_a_session_knob_is_one_step`; `test_undo_on_the_panels_deck_leaves_a_stale_session_value_alone`; a 2-tick cost note on SYSTEM (548 bases a frame twice) per REVIEW's per-frame rule.

### D5c: copy, swap, preview (restart)
**Owns:** `deck.py`, `render.py` only if the warm draw needs it, `app.py` (`_draw_preview` takes a deck), `dream.py` no change.
- `Decks.copy(src, dst)`: `dst.presets.load_doc(src.presets.document(name))` (plan 43's contract is the list; §4's hand list would drift). Then the landing (name, clean ref, unsaved), `Registry.restore(trims=)` from the source's ledger, `view.set_pose` + `forget_commits(POSE_IDS)`, `inst_phase`, `media_phase`, and the first copy onto an empty deck leaving no undo-back-to-black. No lock on LFO or sequencer phase unless the clock already gives it: check.
- `Decks.swap()`: `session.lead`, `Fade.on_air/off_air`, `Fade.lent_to` stays right by construction (`deck.py:494`) [V], `media.state` / `media.off_air` (heard), `Host`, `Mouse`, `MidiIO`, `layer_serial`, `SeqPage`. Lets a held chase go on the leaving deck, one step on its stack.
- `Decks.take(seconds)`, `tick(now, dt)` writing `output.xfade` through its `Param`; `xfade_s` 0 cuts. Frame slot before `_draw_render`, one row in ORDER.
- Backdrop: B at `draw_size(full, cap, False)`, and on frames `Fade.draw` already drew B at full size, reuse it rather than drawing B twice: delays turn "once a frame" (`render.py:95`) [V], so a second draw would double-turn them [I].
- Warm: after a copy or load, one small offscreen draw of the off-air deck, so a compile lands then, not in the fade. Measure on the corpus; REVIEW's stall log says.

**Proof, neutral:** no caller in `app`. **Copy:** over every corpus preset, HOLD-style copy then 120 frames with one lane vector: every performance param of A and B equal each frame (D2's pattern); `test_a_copy_after_a_chase_with_a_push_out_does_not_jump`; `test_copy_leaves_the_mirror`. **GL:** copy, then `xfade` 1 equals A at 0 byte for byte on non-feedback presets, within tolerance otherwise. **Swap:** `test_after_a_swap_only_the_new_deck_moves_a_session_param`; fake-port LEDs and pickup; lend not restarted at swap.

### D5d: the controls, `hold.py` goes (restart)
**Owns:** `deck.py` (`register`, tips, `Decks` operations), `hold.py` deleted, `hotreload.MODULES`, `preset.py` (`GraphSection.hold`, `keep`, `_values`/`parts` filters, `hold_pose`, reset seam at `:1183`, `:1236`), `params.py` (`chase_guard` at `:855`, `:1057`, row 656 superseded), `app.py` (`_draw_render`'s `hold=`, `monitor`), `routing.py` (DQ4), `ui.py:82`, `ui_graph.py` (`:473`, `:1187`, `:1251`, `:1273`, `:1371`, `:1405`, `:2885`, `:3070`, `:3521`, `:3859`), `Fade` gate.
**Freezes:** `ui_graph.py`, `preset.py`, `params.py` chase lines. Say so in the body; UI lane stays off during it.
- `output.hold/.take/.drop` ids unchanged; `lit` = held; `toggle(off)` = take.
- `Fade.k` reads 0 unless a deck is armed (DQ3).
- `Hold.engage`'s "let the verb go" goes; A's verb stays on air (plan 52 §hold). Row 684 reverses: an orbit moves the room while held. Say both.

**Proof:** `test_nothing_on_the_panel_reaches_the_on_air_deck` (route, LFO rate, modifier, macro, load, GRAPH edit, **a `pattern` strip reset, a ⌘Z**, leaving A's `snapshot`, `routes()`, modgraph key and GL frame unchanged); `test_a_controller_moves_the_on_air_deck_and_the_panel_moves_the_other`; `test_a_learn_armed_on_the_panels_deck_lands_in_its_table`; `test_the_output_controls` rewritten; `test_a_chase_stays_on_air_under_a_hold`; turn tests from `test_hands_orbit.py:817`; four `on_gl` rewrites; the fade to black gone. Goldens unmoved at `xfade` 0. Hand checks: a full HOLD, edit, TAKE, DROP at the rig with the desk; a dream look TAKE; a feedback look TAKE.

### D5e: the words
**Owns:** `ui.py`, `ui_graph.py` head, `ui_routing.py` (a row with `not reg.lands(p)`: "dormant off air: lands when this deck is on air"), `ui_desk.py`, `ui.py:2599` (block per deck by number, not "deck 2").
Proof: `tests/test_ui_pane.py` width test; REVIEW's "text matches the current model" sweep of "held", "program", "preview" (`deck.py` and plan-38 tooltips, DECISIONS row at line 379); check by eye with `drive-the-app`.

### D6a, D6b: the playlist
**Owns:** `playlist.py` (new; `hotreload.MODULES`), `library.py` (a kind that is never landed, as `_patch_kind` is, `library.py:753`, `:1790`), then `deck.py` (one hook), `app.py`, a new pane section (`ui.PAGE_KEYS` is append-only, per REVIEW).
**Freezes:** nothing but `Decks`' public surface.
- `Playlist.tick(now)`: load at `dwell − lead` into the off-air deck via `Library.load(into=)`, warm, then `Decks.take(fade_s)`. An advance waits for a running take. `playlist.*` rig controls, group `output`, `persist=False`.
- Un-held: panel follows on-air after the swap (row 9); never mid-gesture: an open undo step delays the swap.
- Preset names in entries take plan 48's folder paths through `path_of`; a missing one skips with a note.

**Proof (D6a):** over stand-in `Decks`: entry lands in the right deck and fades; a deck with an open step is never written; missing preset skipped; `test_an_advance_is_one_mix_pass` (AST: no second fade road); file round-trip; `fade_s` 0 cuts. **(D6b):** frame order; a dirty on-air deck obeys DQ5; `test_library_tool_ignores_playlists` for `migrate_library`.

## 4. Two Macs and schema

**No schema moves in D5 or D6.** No id, no `bindings.json` row and no preset key changes [V by §3's "must not", kept]. `Presets.document` is unchanged, so a preset saved on B is the same file.
- **New folder.** An older build's `Library.groups()` lists any directory under the root (`library.py:1966-1970`) [V], so `playlists/` shows as a group on a Mac not yet updated; harmless but visible. Under the one-build rule, pull both before the first playlist save.
- **Drive sync onto a loaded file.** `Library.poll` reapplies through `landed_groups` → the panel's owner (`library.py:3446+`) [V]. Today the other Mac's save re-lands on air. After D5: under hold A is protected and B re-lands; un-held it still cuts on air, as now. A playlist's off-air load could also be replaced mid-dwell [I]. Not changed here; one line in DECISIONS.
- **Learned rows.** A `playlist.*` or `output.xfade` row in `bindings.json` is dormant on a Mac without it [I from `Sources`' "a name the rig lacks"].
- **Restart** on both Macs for D5a–D5d, D6b (new fields, module gone). PR bodies say so.
- **Show timing.** D5d replaces the mechanism a show relies on. Land it between shows, with the hold exercised at the rig before one. No compat road, per the no-old-schema rule; reversal is a revert.

## 5. Risks

1. **Undo across the session line** (row 5): 256 shared params. Worst failure is silent: ⌘Z moves the room. D5b exists for this.
2. **A leak by a forgotten holder** (row 7): each one found by reading, so assume more. D5a's pointing test and D5d's leak test must drive real roads (strip Reset, bank pad, ⌘Z), not only the plan's six.
3. **A hitch at the fade's first frame** (row 11): not measured. If the warm draw cannot hide it, a TAKE stutters in front of the room where the old hold's cut did not stutter the same way.
4. **TAKE with no edits is not invisible:** the dream restarts (row 653) and feedback looks start empty. The owner will see this on the first press. Say it on the head; check it first.
5. **Session jump at the swap:** A's rows on `master.gain` stop and B's start in one frame; identical after a copy, a step after an edit [I]. No smoothing planned; check by ear.
6. **Video audio cuts at the swap:** only the on-air deck is heard (`Channels.poll(heard=)`, `media/channels.py:390`, `app.py:246`) [V], so a fade that is smooth to the eye has a hard audio edge. Not planned; note to owner, later S.
7. **GRAPH state across a panel move:** `panel._graph` selection, pins, `_wants_cache` (`ui_graph.py:231`, `:1207`) assume one look; treat a move like a load (`ui_graph.settle`) [I].
8. **Hot reload:** `Panel` properties shadow old instance attributes after a re-class [I]; restart covers it, and `test_hotreload` catches the module drop.

## 6. Decisions for the owner

**DQ1. What does DROP leave?**
- (a) Panel returns to the on-air deck, hold off, B parked with its edits. ⌘Z no longer brings them back at once; HOLD then ⌘Z does (HOLD's copy is one step on B's stack).
- (b) As §4: panel stays on B, a fresh copy, ⌘Z restores, hold stays lit until a TAKE, whose fade restarts the dream on an unchanged look.
- **Recommend (a):** it keeps "Drop lets go" and the desk light's meaning. It costs plan 38's one-key ⌘Z; a footer line says how.

**DQ2. Whose undo holds a session param?**
- (a) Only the panel's deck watches session params; a panel move strips them from the deck it left (empty steps already drop, `undo.py:493`). A controller's `master.gain` under hold lands on B's stack, and ⌘Z moves the room for that edit alone.
- (b) A separate rig stack, ⌘Z taking the newer of two; cleaner, more code.
- (c) Session params leave undo: 165 hand and 78 band params lose it.
- **Recommend (a):** one stack per ⌘Z. It loses ⌘Z for session edits made before the move.

**DQ3. `output.xfade` moved by hand, and with nothing armed?**
- (a) Held: a fader to 1 completes the take and swaps, then pickup re-catches at the bottom. Un-held: reads 0, moves nothing, says why.
- (b) No swap by hand: a DJ fader, A and B fixed until TAKE; controllers stay on the deck the room no longer sees at 1.
- **Recommend (a).** Row 559 stands; no default desk row.

**DQ4. A `turn` row on the deck off air.**
- (a) Dormant, as a session row is: base writes belong to the deck the controllers point at. B's camera stays where it was built; a crossfade covers the difference at TAKE.
- (b) Runs on both (plan 51's words): no camera jump at TAKE with no edits, but an orbit dirties B and adds steps to the stack the operator is using.
- **Recommend (a);** row 684 is rewritten either way.

**DQ5. The playlist against the operator.**
- *Under hold:* (a) pauses and says so; (b) a third deck, needing a third renderer: compile stall or idle cost. **Recommend (a),** and N stays 2 for now, narrowing row 556's "N free from D6".
- *Un-held with unsaved edits on air:* (a) pause on the dot, say so; (b) advance anyway: the edits sit on the parked deck and the next load overwrites them. **Recommend (a).**
- *Dwell:* seconds, as §6, or bars on the one clock. **Recommend seconds now, `bars` a later key.**
- *Where it lives:* `playlists/` kind, shared by both Macs, as §6; or in the show, one per rig. **Recommend §6.**

**DQ6. Library verbs under hold (bank pads, `preset.next`, F-keys, hold-to-save, START save).**
- (a) Panel's deck: the room is safe, as the code already leans. A pad cannot change the room while held.
- (b) On-air: a pad cuts the room as it does today, while the panel builds elsewhere.
- **Recommend (a):** "library verbs follow the panel, performance follows the room". Keys and arrows stay on-air per §2.

**DQ7. How the panel says which deck it is on (the rail is gone).** GRAPH is always drawn (`ui_pane.py:3`), and the pane scrolls, so the head is the one fixed place.
- (a) The red head line only, as `ui_graph.py:1187` today.
- (b) Always-on head chip ("deck 1 · on air", or red "deck 2 · not on air · 1:42"), the deck in the `CONTROLS` title and the preset strip's name, a red canvas frame while they differ.
- (c) A new persistent bar: rebuilds what U3 removed.
- **Recommend (b).** Desk diagram: shows the panel's rows, with a red "the desk plays deck 1" line while they differ. Its rows and the hardware then disagree on purpose; say which you want.

**DQ8. Row 558's second dream worker.** Measured: on-air +37 % beside a 128 preview, +67 % beside 192, shared Mac, random weights, renderers not drawing (row 653).
- (a) No: B's preview passes the dream through, the head says so.
- (b) Yes, 128 px, only while held with the backdrop up, behind config.
- (c) Measure at the rig first.
- **Recommend (a) now, (c) as a hand check after D5d;** (b) is an additive PR. Separately: **should a lend keep `D`** when the look is unchanged, rather than wiping (row 653)? Would soften risk 4; not designed. Recommend trying it only if the check bothers you.

**Rows pending and worth a word:** 648, 649, 651–656 are still "(rec), pending the owner"; D5d supersedes 656 and 684. Register and hand-check numbers: next free at build; P2 and P3 still add theirs.

## 7. Not verified

No GL ran and no frame was timed. The probe had no renderer, totem, poi or real devices. Copy's losslessness through `document`/`load_doc`, the compile stall, delay behaviour across sizes, pickup on a learned `xfade`, and LFO and sequencer phase agreement after a copy are all reasoned from reading; D5c's tests are where they get answered. The build's `.venv` was created in this worktree by the probe (gitignored); nothing else changed, and nothing touched `~/Hyperspace` or Drive.
