# Wave 4: what it inherits (everything but D5, D6, N1–N3, B2)

> **Corrected by the orchestrator, 2026-11-04:** §0 item 3 and §4 below say
> north / south / east / west must come before N2 and B2. It need not: row 545
> renames only the four-button cluster and the D-pad, and "the extras from 32
> stand", so B2's `pad:LP` and N2's LB / RB page keys are untouched by it. It
> is still worth this wave, after #365; it gates nothing. Numbers in §6 are
> pre-assigned in `wave-4-session-prompt.md`.

Read 2026-11-04 against origin/main ff58ee2; #366 merged after that (7be8136). No code, PR, `~/Hyperspace` or Drive touched.
**[V]** = verified (`gh`, read-only `git merge-tree`, the tree). **[I]** = my inference or recommendation.

## 0. What would change wave 4's plan

1. **Row 4.7 is wrong on both halves.** #314 has nothing to rebase [V], and "pad rows ride in patches" is not true of the code [V, §1]. 4.7 shrinks to #287 alone.
2. **#287 should land after D5, not before** [I]: one shared dial dict meets per-deck registries (§1).
3. **North/south/east/west should come before N2 and B2** [I], or those two add rows a rename then has to migrate (§4). This is the one unscheduled item that moves the order.
4. **Merge gate:** D5's merge waits on 489–492, and N1's on 506–509 (§5). Building need not wait.
5. **Numbers:** #365 (not in the brief) already claims rows 686–687, checks 520–521, group BW (§6).

## 1. Open and held PRs

| PR | State [V] | Conflict with main [V] | Wave 4 [I] |
|---|---|---|---|
| #314 Plan 42 lab | **Merged** 2026-11-02, cf96377, on main; no branch to rebase | none | Strike from 4.7; see below |
| #287 dial readings | Draft, Dillon, untouched since 10-29; 122 behind | 8 files: register, ENGINEERING, hand checks, app, devices, params, ui, ui_graph. One hunk in each of the 5 code files | Rewrite on main **after D5**; see below |
| #223 venues | Draft, Dillon, last commit 10-17; 709 behind | 9 of 12 files, incl. config, app, test_config, test_ui_shell | Not wave 4. Pairs with rig removal. Do not port or close without asking (owner, 10-25) |
| #273 structure audit | Draft, docs only; 65 behind | Clean | Do not merge as it stands: its figures predate D1–D4 and U1–U3. Re-measure, then merge. Phase 0 (pyright baseline, size ratchet) touches no app code and could run beside wave 4 if the owner wants it |
| #342 poi hand fix | Draft; 7 behind | Clean | **Superseded by #365** (its body says #342 stays a record). Close once #365 lands. `tools/poi_probe.py` is not on #365, so the branch must be kept or the tool salvaged. Its check number 444 is also taken on main |
| #340 edge lab bench | Ready, Dillon; 10 behind | `docs/plans/README.md` only | Merge whenever its owner says. No `hyperspace/` change, no gate. Outside wave 4 |
| #365 Joy-Con v0 (not in brief) | Draft, 2026-11-04, on ff58ee2; pad flat, tape-tested only | Clean by merge-tree; GitHub says CONFLICTING (stale, I assume) | Land before NSEW, which must rename its rows too |
| #363 CI flags | Ready, CI green, one file | Clean | Merge now (§5) |

**#314, the rest of it.**
- [V] Its "before this can merge" list never got done: vet on a real Edge, decide limitation 1.
- [V] All eight patches in `assets/42-controllers/patches/` are still `patch/1`, with no `desk` rows.
- [V] Plan 50 line 21 says "pad rows can ride in a patch: a patch's `desk` rows are any desk control's". The code does not allow that:
  - `patches.check` refuses a `desk` row that is not MIDI ("not a desk control").
  - It refuses a `routes` row that is not a performer row.
  - The rows these ideas need are sink rows (`param:rot.phase.XW` to a pad channel) and one `pad:RP`. All are session rows by `routing.is_session_row`.
- [I] So riding needs app code **and** a contract ruling: row 554 says hardware is the rig's, "and requested". Likely shape: the patch requests rows, and the spawn adds them to the session after asking, which is #314's own proposal. Size M.
- [I] Not wave 4 unless Dillon has vetted ideas on a real Edge. Row 549: "the Edge is not the priority". Correct plan 50's sentence in whichever PR next touches it.

**What F1, P1, U3 (and D3, D4) change for #287.**
- **Params [V]:** the one conflict hunk is `PERFORMANCE_GROUPS`, which D3 rewrote. Re-add `pad` by hand.
- **F1 [I]:** no format obstacle. Unknown ids get a note, so the "both Macs" rule covers it, and its "no schema bump" probably survives. Its "after the 10/30 show" banner is expired.
- **P1 [I]:** `pad` is a new performance group, and a registry-wide test holds `patches._param_rows` equal to `graphview.OWNERS`. It may need an owner entry; a pad's readings should stay refused in a patch.
- **U3 [V/I]:** the move still makes sense and now helps. Row 671 lists SYSTEM with the dials as long at 320 px; moving them to the pad node fixes that. `DIAL_WIDE` suits the 240–320 px pane. The `ui_graph` hunk is at the pad node's details.
- **D3/D4, the real one [I]:** #287 has one dict every pad reads (`Context.dial_modes`) in a performance group. Performance params are now per deck, and D4's deck 2 has its own registry and can load. A load on deck 2 would change the live pad's readings, breaking "deck 2 moves nothing on air". The dict has to become "the pad reads the deck it drives", and D5 is what defines that. Build it after D5, beside N2 (same pad surfaces). Ask D5's planner to confirm.
- **Numbers [V]:** its row 542 and check 404 are both taken on main; renumber.
- **Who does it:** the build order says Dillon rebases his own, and also that the fold became ours. Owner to say (§7).

## 2. Rows pending the owner

[V] Counted from the register's index table (639 rows, 34–685). **61** say "pending"; **25** more are bare "(rec)" with no acceptance. That is **86**. The 250 blank-status rows are the older build-time keep-or-overturn rows, not counted.

| Group | Rows | n | State |
|---|---|---:|---|
| Plan 49 fold U1–U3 | 597–601, 626–632, 668–672 | 17 | nod; 669 and 668 carry questions |
| Plan 50 F1 | 639–647 | 9 | nod; 641 is a stated deviation |
| Plan 51 O1, O2 | 678–685 | 8 | judge after sensors |
| Plan 45 V4 | 673–677 | 5 | judge by ear |
| Plan 44 D4 | 648, 649, 651–653 | 5 | **653 is a question** |
| Plan 42 | 546, 550–552 | 4 | **552, 546 go with NSEW** |
| P1 | 657–660 | 4 | nod |
| Plan 52 B1 | 654–656 | 3 | judge with B2 |
| Plan 48 L2 | 636–638 | 3 | nod |
| I1 | 605, 606 | 2 | nod |
| Row 524 | 524 | 1 | P3 closes it (owner: "yes, the take-over chip") |
| Bare (rec): D3 | 611–619, 622–625 | 13 | nod; 625 is D5's list |
| Bare (rec): V2, V3, L1 | 582–584, 594–596 | 6 | nod |
| Bare (rec): T2, T3 | 607–610 | 4 | **609 before N1** |
| Bare (rec): other | 334, 542 | 2 | nod |

P2 and P3 add rows 661–667 on merge. Their state is unconfirmed until they land.

**Actually gate wave 4 work: 4 rows, plus 1 non-row** [I]:
- **653**, second lower-resolution dream worker for the panel's deck: D4 measured it, "the owner's to decide". Shapes D5's preview. For D5's planner.
- **609**, SEND B as FINE, "for the owner and Dillon to keep": N1 gives the APC knobs a new mode, so settle it before N1.
- **552** (pad draws its model's face) and **546** (the form of `controller =`): only if NSEW is scheduled.
- **The B2 button** (a build-order gate, no row): see §4; the Edge's `pad:LP` / `RP` sidestep the rename.

**The other ~80 just await a nod.** Ask once by group, with 669, 668 and 641 called out, and do not walk rows.

## 3. Rough edges recorded, not scheduled

**Worth a PR in wave 4** [I]; all UI-lane, S, could be one "pane paper cuts" PR:
| Item | Source [V] | Why |
|---|---|---|
| T2 fine mode misses ROUTING's raw sliders and GRAPH's backdrop | row 608 | Route depth is where fine matters most; U3 keeps ROUTING on screen with the canvas |
| Save-as-patch / update-patch row spills 19 px at `SIDE_MIN` | #364 body | Breaks plan 49's "nothing past the pane's edge"; a `ui.beside` fix and a test |
| "page" words in the panel (a tip's "HANDS page", "open on VIEW") | row 668, an owner question on #360 | Land last so it catches N1–N3's words; many tests name them. Only if he says yes |
| On-screen desk draws SEND B as free | row 609 | Ship with or before N1 (`desk.fine` beside `desk.save`), not in the paper cuts, because the desk is N1's |

**Hand to D5's planner** [V]: ROUTING not saying a deck-off-air row is dormant (row 650); row 625's list (`hold._preset_part` and the mirror, the presets kind's owner); xfade fading to black until D5; the giving-up deck holding its last dream (653).

**Stay** [I]:
| Item | Source [V] | Why it stays |
|---|---|---|
| ROUTING combos cut at 320 px | row 671 | Row's own answer: the pane's width (the grip) |
| Load is not a spawn | row 660, 641 | Proven equal over the corpus; no change a user sees. Close with a nod |
| Two decodes when both decks open a file | row 652 | No evidence it costs yet; revisit if D5 or D6 shows it |
| Chase: source going home under a held verb; two surviving stale-trim cases | row 654, plan 52 | Judge with B2 on the rig first |
| Orbit: fist may tip the palm reading; the flip-back loses a hand-picked gate; not a trackball | #362, plan 51 §6 | No sensor has run any of it; 514–519 first |
| V4 loop seams and window-fade on long clips | rows 675–676 | Nobody has heard it; 510–513 first |
| Hand-dragged pin stays open; chips below the fold at 900 px | #364 | The first is a question for the owner; it needs a record of "answered" |
| `_param_rows` restates `graphview.OWNERS` | #355 | Import direction; a test holds them equal |
| Shot scripts setting `ui.page` not re-run | #360 | They still land; fix when next used |

## 4. The owner's unscheduled items

| Item | When [I] | Why |
|---|---|---|
| **North / south / east / west** (row 545: "not Xbox names"; "a work item, not built") | **Wave 4, before N2 and B2, after #365** | [V] `pad:A/B/X/Y` appears 119 times in 22 files across code, tests, tools. N2, B2 and #365 all add such rows; every one added first is one more to migrate, and it reaches `bindings.json`, shows and any preset row. Needs a migration by the repo's rule. Size M. Gamepad and adapter files, so it can run beside D5 if the two agree on `routing.py`. Check the names against existing `pad:` tokens. **If he defers it,** B2 should take a button the rename will not touch, and N2 lands knowing it will be migrated |
| **Grand cleanup pass** (row 585) | **After wave 4; first thing in wave 5** | Must follow the last format-touching work (NSEW, #287, N-mode rows) or it runs twice. Schema normalising is largely done already (the library is on `/10`, `patch/2`), so what is left is cruft: the `modules` key and `RETIRED_MODULES` (row 646), a leftover `desk/` folder (rough edge in the D3 rows), perhaps the ladder's old rungs under "no old-schema support". Run it between shows, backup first. A read-only "what would change" report could come earlier, by the owner, no agent on the Drive |
| **The rig concept goes away** | **After D5 and D6, wave 5 or later, with #223** | Wave 4 stands on the seam: `RigMade`, `RIG_KINDS`, `RigWires` are in 10 modules [V]. Owner leans to Dillon's venues as the one concept (10-25). Needs a decision first: since D3 the session/performance line is mechanical, so does "goes away" mean a rename, or venues replacing `config.toml.rig`? Write it as its own plan |
| **Plan 40 follow-ups** (`40-patches.md:544`: nested groups; exposed knobs; patches in a bank, only if D8 turns; a patch's media source list) | **Later; backlog** | P1–P3 were the sequel that mattered. Exposed knobs is the only one near wave 4: see whether N1's "selected node's params" covers the need first |

## 5. Test and CI health

**CI [V]**
- Main's last 12 runs are all green.
- `tests.yml:67` still has `--timeout 120 --max-worker-restart=0`.
- **The brief is out of date here:** `ci/dist-load` is pushed as **#363**: ready, one file, green, merges clean. It only needs someone able to merge a workflow change. pyproject has had these flags since row 605. Merge first.
- #366 merged (7be8136). Its own evidence: 4 of 9 failures before, 0 of 5 after, "0 of 5 alone is weak".
- #361's status check shows a FAILURE from before #366. Rebase and re-run before reading anything into it; if it recurs, the cause is not closed.

**Skips**
- [V] Mac fast tier: 2. `ENGINEERING.md:3300` names one, the no-real-hand-tape test; the second I did not identify.
- [V] #366 reports 4 on Linux CI. #362's extra two were chase tests lifted by B1 (`test_hands_orbit.py` no longer skips).
- I could **not** read CI logs (the API returned nothing), so skip names on Linux are unverified.

**Flakes on record [V]**
- `test_shape_renders` and the segment crashes: "stay unexplained" (row 606); next time rerun `-n0 -k` at once.
- `test_media_folder`'s still-downloading test: load-flaky, 5 of 8 standalone per #287 (old data; may have moved).
- The GL free: now #366.
- `test_a_channel_dropped_on_a_cable…`: fixed in U3 (glide race).
- The `live` tier: flaky under load by its own marker, serialised by the lock.

**Goldens:** run on the Mac by the orchestrator, not builders (wave 3 prompt). Builders' PRs all say "not run; none should move". Confirm wave 3's union run is recorded before D5 builds on D4; I did not see the record.

**Hand checks [V]**
- Main holds 509 checks numbered up to 519. The doc's line 3 still says "none has been run yet", and 425 did run (CHECKPOINT:185).
- Since wave 0 (419+): **94 on main, 100 with P2/P3's 500–505**, 102 with #365. No record of any but 425. Top matter also still says "1–404".

| Priority | Groups | Why |
|---|---|---|
| **Stage, first** | BN 489–493 (D4), BS 506–509 (U3) | Going on stage first |
| **Stage, before any show** | BJ 461–470, esp. 467–468 (`/10` on the other Mac), BM 485, BK 471–479 | The library everything loads |
| **Before D5** | 494 (chase under hold) | Plan 52's hold interplay; D5 retires the hold |
| **Before N1** | BI 459, BH 457 | Fine vs node mode on the same knobs |
| **Can wait** | BT 510–513, BU/BV 514–519, BE, BB, AV | Sound and sensors; nothing in wave 4 builds on them |

**Should wave 3's checks gate wave 4? Recommend [I]: gate merges, not builds, and only two of them.**
- **D5 does not merge until 489–492 pass on the rig.** D5 puts real content on the fade and retires `hold.py`; a D4 fault found later has two layers to dig through. Nothing has run with Syphon, NDI or MSAA hardware, or with pretrained dream weights through a fade (#359).
- **N1 does not merge until 506–509 pass.** It draws into the pane U3 just made permanent.
- Builders start regardless; the rest of wave 4 stays independent.
- Roughly an hour at the rig [I], and the same pass readies him for stage.
- **Stage warning [V]:** in this build raising `output.xfade` **fades to black** (deck 2 empty until D5, #359). Learn no fader on it for a show before D5.

## 6. Next free numbers

[V] From main, P2/P3 and #365. No `plan 5[3-9]` found in any branch's log or in `docs/plans`.

| Thing | On main ends | Claimed by open PRs | **Next free** |
|---|---|---|---|
| Plan | 52 | none | **53** |
| Register row | 685 | P2 661–664, P3 665–667, **#365 686–687** | **688** |
| Hand check | 519 | P2 500–502, P3 503–505, **#365 520–521** | **522** |
| Group | BV | BQ, BR, **BW** | **BX** |

- If #365 is dropped: 686, 520, BW. Assign from 688/522/BX either way.
- Index gaps 602–604 and 633–635 have no row on main. Do not reuse them.
- Pre-assign the wave's blocks at launch, as parallel builders collide. `tools/sort_register.py` sorts only.
- #287's 542 and 404 and #342's 444 are all taken, so each needs new numbers.

## 7. The owner's decisions

1. **NSEW in wave 4, before N2 and B2?** Rec yes. This is the one that reorders.
2. **Merge gate:** 489–492 before D5, 506–509 before N1? Rec yes.
3. **Row 653:** second dream worker (D5's scope). **Row 609:** keep SEND B as FINE (before N1).
4. **#287:** after D5, and who rewrites it, Dillon or us?
5. **Pad rows in patches:** drop from 4.7 until Dillon vets ideas on a real Edge? Rec yes.
6. **Merge #363.** Close #342 once #365 lands (keep the probe?).
7. **Bulk nod** on ~80 rows by group; his answers to 669, 668 (words PR), 641.
8. **Later:** what "the rig goes away" means, with #223; cleanup pass at wave 5's start.
