# Plan 58 — wave 5: the cleanup, the rig's last piece, and cheaper changes

**Status: planned 2026-11-06, none of it built.** Read against `main` at 34caf3c, before #380 merged (463b154), by three independent
planners, reconciled by the wave 4 orchestrator. Its launch prompt is
[`wave-5-session-prompt.md`](wave-5-session-prompt.md). Tags: **[V]** read or run, **[I]** inferred.

Wave 5 was not in the build order, which stops at wave 4. Its content comes from what wave 4 said it
would hand on, what the owner said about venues on 2026-11-05, and a sweep of everything deferred.

## 1. What this wave is for

Three things, in this order of importance:

1. **Make the two layers true everywhere,** and delete what kept the old shape alive. After wave 4 the
   words are right and the library is on one format. What remains is code that still reads files nobody
   has, and a few places where one look can still reach another.
2. **Finish "the rig goes away".** After the rename, the rig is mostly config files. Screens and
   controllers should be set up in the app, and remembered without planning.
3. **Make the next change cheaper.** The owner asked for this on 2026-10-26. The measurements below
   change what that means.

It adds no new looks or controllers. That is a choice, and the owner may overrule it (§8, question 8).

## 2. Before it can start

Wave 5's runs depend on wave 4 being finished, because the cleanup must follow the last change to saved
files or it runs twice.

| Must be true | Why |
| --- | --- |
| Wave 4 merged: SEM, D5e, N1, N2, D6, #287, #365, NSEW, the migration | Every item here is built on the renamed code and the `/11` library |
| **The owner ran the migration, and both Macs have opened the new library** | Stage 1 removes the code that reads the old files. Only the owner can say this |
| Hand check 467–468 passed (the other Mac) | The same fact, checked |

Items H1, H2 and SM1 need none of this and can land at any time, including during wave 4.

### What wave 4's remainder must carry, found by this planning

These belong in wave 4, and are also written into its documents.

**SEM:**
- **`preset.*`, `deck.chase`, `totem.*` and `poi.*` are in neither layer, and they can't simply be added to
  the meta list [V].** `Registry.add` makes a session param one object shared by both `Deck`s
  (`params.py:930–936`), and these close over one `Deck`. They need a class of "meta, one per `Deck`":
  counted as meta for the refusal and for the one-layer test. SEM's own test forces this.
- A patch's row can no longer press a load or a save: #380 refuses both (row 752), so the class above
  replaces that refusal rather than adding to it.

**The format lane (plan 57):**
- **`modules` in a show is not cruft [V].** It holds the analyzer scene in 5 of the 6 shows, and must
  reach the install file. `layout`, `startup`, `scene.select` and `last_show` need homes too. `mine` has no
  tuning and `startup: "MIGRATED"`.
- **`trash/presets` moves as well** (`TRASH`, `restore_trash`), and a reader must accept the old word for
  the run.
- **The run should also tidy:** delete `fx/`, empty folders and `.bak-v2-*`, and report bank slots that
  point at nothing. Five shows have 10 of 24 such slots [V].
- **`scenes/band` files say `hyperspace.preset/1` and are analyzer tunings [V].** After the rename they
  are the last "preset" files. Rename their kind in the run, or rung `/1` must stay.
- **Size:** the show-file move is an L, the largest thing left in wave 4 [V]. With one migration it can't
  split off, so wave 5 waits on it.

## 3. What was measured

| | 2026-10-27 audit's commit | `main` now |
| --- | --- | --- |
| `hyperspace/` files / lines | 91 / 70,082 | 120 / 98,522 |
| Largest: `graph`, `graphview`, `ui_graph` | 6,276, 4,776, 2,791 | 7,322, 6,929, 5,156 |
| `getattr`/`hasattr` per 1,000 lines | 13.7 | 15.7 |
| Functions fully annotated | 67.2% | 64.7% |
| Modules in one import cycle | 14 | 18 |
| pyright basic errors | 933 (audit) | 1,511 |

Measured by the same script on both commits, except the pyright row [V].

**Why a PR is slow [V, by replay].** The last 79 pairs of merges were replayed as if they were siblings:
31 would conflict, and **23 of those 31 are in documentation only** (`DECISION-REGISTER` 21,
`11-hand-checks` 18, `DECISIONS` 7, `plans/README` 5). Code conflicts are rare: `app.py` 3, `deck.py` 3.
With `merge=union` on those four files, 31 falls to 11. **So splitting big files would not buy merge
relief; one line of git config does.** Replay reconstructs conflicts rather than counting real ones.

**Tests [V].** Fast tier on `main`: 6199 passed, 3 skipped, 458 s under contention; recent PR bodies show
about 76 s alone. CI: 6197 passed, 5 skipped, 3.9 min median. 49 CI runs in a row are green since 11-05.
`--all` was not run: 6,425 tests, 789 goldens over 195 distinct pictures. No recent timing exists, and
`ENGINEERING.md` §16's are stale.

## 4. The items

Numbers are in §7. "Saved?" says whether files on disk change.

### Housekeeping (can land any time)

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **H1** | Doc conflicts stop: `merge=union` on the four doc tails, plus a test that row numbers and hand-check groups are unique | `.gitattributes`, one test | S | nothing | no | Replay above; one clean replayed merge produced a duplicate row, which the test exists to catch |
| **H2** | Test truth: fix `ENGINEERING.md` §16's counts and times; `wait-green` moves to `tools/merge_on_green.py`; a builder's last check is CI, not a machine slot; the next `--all` records its durations | docs, one tool | S | nothing | no | No `hyperspace/` diff |
| **SM1** | Salvage `tools/poi_probe.py` from `origin/worktree-poi-hand-fix`, then close #342 once #365 has landed | one tool | S | nothing | no | Runs on its own tape |

### Layers: no look reaches another

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **LY1** | One mirror: `ghost.N.mirror` follows `ghost.mirror`, so an extra hands node no longer adds a param to what's shared and leaves it behind (`params.py:935`) | ghost, params, deck | S | wave 4 | drops an id no file holds (0 in Drive [V]) | Leak test both ways |
| **LY2** | Honest flags: 87 meta params say `modulatable=True` and are refused anyway; `tempo.nudge` stops being saved; `output.bg` and `.alpha` move with SC2 | params, library | S | wave 4 | install file changes slightly | `test_meta_rule` |
| **LY3** | The video-sound path, per question 5: as a named limit in words, or closed | media, ui | S | question 5 | no | A test that names the path |

### The grand cleanup (row 585)

Normalising is done by the one migration, so what is left is deletion [V]. No `desk/` folder exists, so that
item is empty.

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **CL1** | Refuse old files in words: `forward` refuses anything below `/11`, and the silent load steps go (`palettecompat.py`, `pan_world`, `retaper_depths`, the old-show readers) | preset, library, graphmigrate, palettecompat, params | M | §2's gate, question 7 | no | Goldens unmoved; a dry run of the loader over the Drive, read-only, by the owner |
| **CL2** | **Harder than it reads [V]:** `graphmigrate` is also what the tests are built with (50 test files; `tools/golden_frames.py`; `render.py:3718`, `graphview.py`, `graph.py:1996` at runtime), so its 1,778 lines can't just go. Surviving builders move to `tests/wiredframe.py` and the golden tool; the 118 fixtures below `/10` are deleted or converted | graphmigrate, tests, tools | L | CL1 | no | Goldens unmoved; `frame-signatures.json` holds |
| **CL3** | Readers of each Mac's old files: `MIGRATED_FILES`, `LEGACY_MIDI_FILE`, bindings V1/V2, `Carried`, `LEGACY_OUTPUT`, `DEVICE_TABLES`, `_seed_sinks`, `overlay.*` aliases | library, routing, config, devices, overlay | S–M | §2's gate | no | Home-file tests |
| **CL4** | `RETIRED_MODULES`, and tools whose job is finished: `retaper_routes`, `meta_routes`, `calm_lanes`, most of `migrate_library` (763 lines). Keep its backup and check, and keep `move_library` | library, preset, ui_presets, tools | S | §2's gate, and `fx/` deleted | no | `groups()` test |

### Screens and controllers, composed in the app

Today [V]: controllers mostly work (`DeviceRegistry.watch` swaps them live; `players.json` is written by the
app). Displays don't: there's no monitor callback, slots last the whole run, `output.N.*` are never saved,
and screens are numbers that shift when HDMI re-syncs. Nothing writes `config.toml`. The Drive already
holds a `venues/` folder with three files, using `monitor = "MStar"`, which `main` reads as "not a screen".

**The smallest version [I]: each display remembers its job, by its name.** There's no notion of a place.
The TV, the U28E590 (flip Y) and the LW551i each hold their output number, fullscreen and flips. Plug in
the same screens and the job comes back, so laptop-plus-TV and the rig coexist with no switching.

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **SC1** | Screens by name: port `placement.match` from #223. Fixes swapped outputs on its own | placement, config | S | nothing | config only | `test_placement`; replugging HDMI by hand |
| **SC2** | Displays composed on the OUTPUT section: connected screens listed and assigned, with fullscreen and flips; written to one app-owned file; "restart to apply" is the existing ⌘R. Includes fullscreen remembered (plan 23's last piece) | ui, app, config, new store | M | SC1, questions 1, 2 | new file `/1` | Headless panel test; `drive-the-app` |
| **SC3** | Live: a screen plugged in lights up with no restart. Output 1 holds the GL context and paces the loop, so **it can't close live** | app, outputs, overlay | L | SC2, question 3 | no | Hand check only, the rig needed |
| **CT1** | Controllers composed: `devices.json`, with `[[devices]]` read once as a seed; dragging from the tray adopts one; it also looks for MIDI; stable automatic roles, since roles are row addresses | devices, config, ui_players | M | question 4 | new file `/1` | `test_players`; `tools/drive_players.py` |
| **RT1** | Retire: rename `RigWires` to bus cuts if SEM left it; stop reading `[[output.screens]]`; delete `config.toml.rig`; close #223 with Dillon | config, graph | S | SC2, CT1, question 1 | one-time seed | Launch from an empty home |

`[library]`, `[dream]` and `[totem]` stay in `config.toml`: the library's path must be known before the
library can be read. So "no planned config files" is true of displays and peripherals, not of everything.

**What dropping venues loses [V]:** overriding any setting per place (render cap, hands mode, `keep_awake`);
two arrangements of the same screens; `--venue` and the restart picker; Dillon's three files.

### Types: stop the drift

The goal is a ratchet, not zero errors.

| Id | What | Size | After | Proof it changes nothing |
| --- | --- | --- | --- | --- |
| **TY1** | pyright baseline by file and rule; a per-file size cap at today's sizes; import-wall tests globbed so future splits are covered. The CI step needs the owner's token (`.github/workflows/`), as #363 did | S | wave 4 | No `hyperspace/` diff |
| **TY2** | Re-measure #273's audit and merge it as the record | S | TY1 | Docs only |
| **TY3** | Declare attributes, annotations only: `Renderer`, `Registry`, `Analyzer`, `Panel`, `Bindings`. The audit estimates about 500 errors fewer; not re-derived | M | TY1, after the cleanup | AST identical once annotation lines are stripped; goldens unmoved |
| **TY4** | `RenderHost` Protocol for `Frame.r`, `Device` used as a type; no renames | M | TY3 | Same AST check; `--all` |

### Small things already asked for

| Id | What | Size | After |
| --- | --- | --- | --- |
| **SM2** | GRAPH's zoom scaled to the display: the owner's install item 1, still `SCALE = 1.25` [V] | S | nothing |
| **SM3** | Matte and segment thumbnails (row 500) | S | nothing |
| **SM4** | Audit faults still open in `ENGINEERING.md` (R13, R14, R15, U9, U10, V8), each verified first since some may be moot | S each | CL1 |
| **SM5** | Whatever wave 4 did not reach: the words pass (row 668), the player's moves on the undo stack (row 740) | S | wave 4 |

And one look, no code: the **per-face render check**, flipping the face map on a dragonfly preset and
unwiring the backdrop on logo-wobble. The build order calls it the only way the per-face question gets
answered. It decides whether "per-face through an effect chain" is a real item.

## 5. The schedule

| Stage | Items | Merges when |
| --- | --- | --- |
| Any time | H1, H2, SM1 | green |
| 1 | **CL1**, then CL3 and CL4 together; LY1, LY2; SC1; SM2, SM3 | §2's gate; green |
| 2 | **CL2, alone among anything touching tests' builders**; TY1, TY2; SM4 | green, goldens unmoved |
| 3 | SC2, CT1, LY3, SM5 | green |
| 4 | RT1; SC3 if question 3 says so | green |
| 5 | TY3, then TY4: last, so they annotate what survived | green, `--all` |

Peak width is about five builders, at stage 1. CL1 first because it decides what CL3 and CL4 may assume.
No migration in this wave: SC2 and CT1 add new files, seeded on first launch, and nothing old is rewritten.

## 6. What this plan does not do

**Not building, and why:**
- **Splitting the big files.** The conflict data says it isn't the problem. 73 `monkeypatch.setattr(module, …)`
  uses across 26 test files can silently miss after a façade split [I]. That rules out the audit's phase 3,
  and its phase 5.
- **Page-by-page UI work** (audit's phase 4), unless Dylan's UI pass has a date (question 6).
- **Removing `render.py`'s 95 `getattr(self…`.** They guard hot reload, so removing them isn't neutral.
- **Cheaper goldens yet.** There's no current cost figure. H2's measurement decides. The likely candidate is
  sampling the 51 re-save redraws, but those guard the migrations, so it would be the owner's call.

**Later, recorded:** faces per instance, face list (row 417), "across" face map, dream fidelity, plan 40's
follow-ups, pad rows in patches, pad feedback and trigger effects, Joy-Con acceleration object, paired poles'
later choice, output warp, plan 29 (DMX, bulbs, Kinect, drums), touchscreen panel, Dante, tempo-synced
springs, audio delay compensation, creative pass.

**Dropped, as decided or overtaken:** DJ Link, MIDI clock, auto BPM (owner, DECISIONS); plan 23's top tabs
(the rail is gone); wands and Wiimotes as such; an IMU prop (the totem covers it [I]).

**Stale records to fix when next touched:** `CHECKPOINT.md` lists DJ Link as an idea; `11-hand-checks.md`
says "none run", and 425 ran; row 417 and CHECKPOINT say a face list is awaited, and the owner kept all 17;
row 653 is still pending, and the fifth round said no second dream worker.

**Hand checks.** Numbered to 577, and only 425 is recorded as run [V]. Most needed before a show: 489–492's
matters on the #380 build, 506–509, 467–468 and 485, the players screen (CL, CN), and 514–519.

**Rows.** 89 pending the owner by status text [V]. Question 9 asks for one nod rather than a walk.

## 7. Numbers

Wave 4's remainder keeps rows from 752 and checks from 578. Wave 5 starts well clear: **plan 58, rows from
770, checks from 600, groups from DA.** Pre-assign per item at launch. `CHANGELOG` #374, the Edge lab #340 and
the QR sticker PR #383 are their authors', and outside this wave.

## 8. Questions for the owner

The owner answers these in the launch prompt's "The owner's answers". Until then this plan assumes the
recommendations. Plain wording is in the session report of 2026-11-06.

1. Venues: each screen remembers its job, and no places (recommended), with Dillon's confirmation.
2. Does a screen's memory live in the Drive, shared by both Macs (recommended), or on each Mac?
3. Must a screen plugged in during a show light up with no restart? Recommended: restart first; SC3 optional.
4. Does a new controller act at once, or wait until dragged to a player (recommended)?
5. On-air video sound reaching the off-air look through the analyzer.
6. `dkit`, and whether Dylan's UI pass has a date.
7. When old-file reading goes, and what happens to the 12 trashed looks.
8. Is this wave's scope right, with no new looks or controllers?
9. One nod on the rows pending.
10. Whether a mis-pressed pad followed by ⌘Z, with the panel on air, is fine with #380's warning in words.

Assumed unless the owner objects: patches may read `master.gain` (457 saved rows do), since reading is not
writing; a tapped BPM comes back at launch and a nudge does not; totem and poi are meta, following the player's
`Deck`; a new type-checker complaint fails a PR, old ones don't, from TY1 on; no trial split of `graph.py`.
