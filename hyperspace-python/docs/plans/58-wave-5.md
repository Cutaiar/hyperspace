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

It adds no new looks or controllers: the owner confirmed that scope on 2026-11-06.

## 2. Before it can start

Wave 5's runs depend on wave 4 being finished, because the cleanup must follow the last change to saved
files or it runs twice.

| Must be true | Why |
| --- | --- |
| Wave 4 merged: SEM, D5e, N1, N2, D6, #287, #365, NSEW, the migration | Every item here is built on the renamed code and the `/11` library |
| **The owner ran the migration, and both Macs have opened the new library** | Stage 1 removes the code that reads the old files. Only the owner can say this, and they coordinate the other Mac. The `/11` run's own hand check, which plan 57 §7a tells the format lane to add, is the same fact checked |

Items H1, H2 and SM1 need none of this and can land at any time, including during wave 4.

In §4, **After** is a hard dependency. **Stage** in §5 is when to start.

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
- **The Drive's trash is deleted in the run, not converted** (owner, 2026-11-06), after the backup.
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
With `merge=union` on those four files, 31 falls to 11 **for local merges only**. **So splitting big files
would not buy merge relief; one line of git config does, for a merge made locally.** GitHub's server doesn't
honour the attribute: retested 2026-11-06 with it on `main`, its merge API said 409 and a PR's mergeable
state said conflict on a pair that merges clean locally. A PR showing doc conflicts needs main merged
locally and pushed, which union then resolves with no hand work. Replay reconstructs conflicts rather than
counting real ones.

**Tests [V].** Fast tier on `main`: 6199 passed, 3 skipped, 458 s under contention; recent PR bodies show
about 76 s alone. CI: 6197 passed, 5 skipped, 3.9 min median. 49 CI runs in a row are green since 11-05.
`--all` was not run: 6,425 tests, 789 goldens over 195 distinct pictures. No recent timing exists, and
`ENGINEERING.md` §16's are stale.

## 4. The items

Numbers are in §7. "Saved?" says whether files on disk change.

### Housekeeping (can land any time)

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **H1** | Doc conflicts stop in local merges (GitHub's server doesn't honour it, retested 2026-11-06, §3): `merge=union` on the four doc tails, plus a test that row numbers and hand-check groups are unique | `.gitattributes`, one test | S | nothing | no | Replay above; one clean replayed merge produced a duplicate row, which the test exists to catch |
| **H2** | Test truth: fix `ENGINEERING.md` §16's counts and times; `wait-green` moves to `tools/wait_green.py`, which only waits and merges nothing; a builder's last check is CI, not a machine slot; the next `--all` records its durations | docs, one tool | S | nothing | no | No `hyperspace/` diff |
| **SM1** | Salvage `tools/poi_probe.py` from `origin/worktree-poi-hand-fix` (#342 is closed). It was written against that branch's `poi.py`, so port it to `main`'s `poi.step` | one tool | S | nothing | no | Runs on its own tape against `main` |

### Layers: no look reaches another

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **LY1** | One mirror: `ghost.N.mirror` follows `ghost.mirror`, so an extra hands node no longer adds a param to what's shared and leaves it behind (`params.py:935`) | ghost, params, deck | S | wave 4 | drops an id no file holds (0 in Drive [V]) | Leak test both ways |
| **LY2** | Honest flags: 87 meta params say `modulatable=True` and are refused anyway; `tempo.nudge` stops being saved. `output.bg` and `.alpha` are SC2's | params, library | S | wave 4 | install file changes slightly | `test_meta_rule` |
| **LY3** | Say it on the toggle: the analyzer hears what the room hears, so the on-air look's video sound reaches what the off-air look reads from it. The owner accepts this as not a breach (2026-11-06) | media, ui | S | wave 4 | no | A test that names the path |

### The grand cleanup (row 585)

Normalising is done by the one migration, so what is left is deletion [V]. No `desk/` folder exists, so that
item is empty.

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **CL2** | **First, because the tests stand on it [V]:** `tools/golden_frames.py` loads fixture presets through the ladder, `tests/fixtures` holds 118 presets at `/1`–`/7`, and 74 lines in `tests/*.py` name an old schema. `graphmigrate` is also a builder: 47 test files, about 17 tools, and at runtime `preset.py:141`, `library.py:142`, `headless.py:109`, `graphview.py:126` (`through_wires`, a live toggle) and `render.py:3717`. Its 1,778 lines can't just go. **The tests stop needing to load anything below `/11`:** fixtures converted or deleted (`git add -f`), test builders move to `tests/wiredframe.py` and the golden tool, runtime parts keep a home in the app. Re-save goldens guarding a migration that's going may be deleted, each named in the PR body | graphmigrate, tests, tools, preset, library | L, may run larger | §2's gate | no | Remaining goldens unmoved; `frame-signatures.json` holds |
| **CL1** | **The point of no return:** refuse old files in words. `forward` refuses anything below `/11`, and the silent load steps go (`palettecompat.py`, `pan_world`, `retaper_depths`, including `routing.py:2505`, the old-show readers, `graph.py:1996`'s `_legacy`). Ships a read-only dry-run tool, `tools/check_library.py`, for the owner to run. Its PR's first line says old files stop opening, and what to do if a Mac hasn't updated | preset, library, graphmigrate, palettecompat, params, routing, graph, one tool | M | CL2, §2's gate | no | Goldens unmoved; **merges only after the owner's dry run over the Drive is clean** |
| **CL3** | Readers of each Mac's old files: `MIGRATED_FILES`, `LEGACY_MIDI_FILE`, bindings V1/V2, `Carried`, `LEGACY_OUTPUT`, `DEVICE_TABLES`, `_seed_sinks`, `overlay.*` aliases | library, routing, config, devices, overlay | S–M | §2's gate | no | Home-file tests |
| **CL4** | `RETIRED_MODULES`, and tools whose job is finished: `retaper_routes`, `meta_routes`, `calm_lanes`, most of `migrate_library` (763 lines). Keep its backup and check, and keep `move_library` | library, preset, ui_presets, tools | S | §2's gate, and `fx/` deleted | no | `groups()` test |

### Screens and controllers, composed in the app

Today [V]: controllers mostly work (`DeviceRegistry.watch` swaps them live; `players.json` is written by the
app). Displays don't: there's no monitor callback, slots last the whole run, `output.N.*` are never saved,
and screens are numbers that shift when HDMI re-syncs. Nothing writes `config.toml`. The Drive already
holds a `venues/` folder with three files, using `monitor = "MStar"`, which `main` reads as "not a screen".

**The owner, 2026-11-06:** "It needs to be extremely easy for us to just quickly set up the screens for the
thing that we're doing. I don't think we need a whole configuration layer called venues." **Each connected display
gets its own row on the output section, not a dropdown, and you choose what targets it: the control window or any of
the renders.** Each display remembers its job by name, in the Drive, so both Macs share it. **And it must be
hot-pluggable:** a display accidentally unplugged and plugged back in can't need a restart.

| Id | What | Files | Size | After | Saved? | Proof |
| --- | --- | --- | --- | --- | --- | --- |
| **SC1** | Screens by name: port `placement.match` from #223, the one part of it worth keeping. Fixes swapped outputs on its own. **Exact name plus an ordinal among displays of the same name,** not its first-substring hit: two identical screens are two rows, and "TV" must not match a longer name | placement, config | S | nothing | config only | `test_placement`, with two same-named displays; replugging HDMI by hand |
| **SC2** | **One row per connected display** on the output section: its name, what targets it (the control window, a render, or nothing), fullscreen and flips. One target per display; **a target may go to several displays** (owner, 2026-11-06). Written to `<library>/displays.json`, shared by both Macs. A render may go to several displays; **the control window goes to one.** Includes fullscreen remembered (plan 23's last piece), `output.bg` and `.alpha`. Seeds once from `[output] monitor`, `control_monitor`, `fullscreen` and `[[output.screens]]`, and says what `--laptop` becomes. A change acts on ⌘R until SC3b, then at once | ui, app, config, new store | M | SC1, SC3a | new file `/1` | Headless panel test; `drive-the-app` |
| **SC3a** | **The picture stops depending on any one display.** Output 1 holds the GL context and paces the loop today [V], so it can't close while running. Both move to something no unplug can take away. No behaviour change. **The riskiest step in the wave: start with a short spike, and if it fails, stop and tell the owner, since hot-plug is required** | app, outputs, render | L | SC1 | no | Goldens unmoved; frame pacing measured before and after |
| **SC3b** | **Hot-plug (audit fault P6):** a monitor callback, outputs opened and closed while running, the same job back when the same display returns; pictures keep rendering meanwhile; a row's target acts at once; a control window whose display goes moves to one still there, floating over a render if none is free | app, outputs, overlay | M–L | SC2, SC3a | no | Tests over a stand-in monitor list; a hand check with a real unplug on the rig |
| **CT1** | Controllers composed: `<library>/devices.json`, shared by both Macs as displays are, with `[[devices]]` read once as a seed; `players.json` stays on each Mac; dragging from the tray adopts one; it also looks for MIDI; stable automatic roles, since roles are row addresses | devices, config, ui_players | M | wave 4 | new file `/1` | `test_players`; `tools/drive_players.py` |
| **RT1** | Retire: rename `RigWires` to bus cuts if SEM left it; stop reading `[[output.screens]]`, `[output] monitor`, `control_monitor`, `fullscreen`; close #223 with a note to Dillon. **Owner's steps, listed in the PR:** delete `~/Hyperspace/config.toml.rig` and the Drive's `venues/` | config, graph, app | S | SC2, CT1, **SC3b's hand check** | one-time seed | Launch from an empty home |

`[library]`, `[dream]` and `[totem]` stay in `config.toml`: the library's path must be known before the
library can be read. So "no planned config files" is true of displays and peripherals, not of everything.

**What dropping venues loses, accepted by the owner [V]:** overriding any setting per place (render cap, hands mode,
`keep_awake`); two arrangements of the same screens; `--venue` and the restart picker; the three venue files in the Drive.

### Types: stop the drift

The goal is a ratchet, not zero errors.

| Id | What | Size | After | Proof it changes nothing |
| --- | --- | --- | --- | --- |
| **TY1** | pyright baseline by file and rule; import-wall tests globbed so future splits are covered; a per-file size cap at the sizes after stage 4, added with TY3, so the display work doesn't trip it. The CI step needs the owner's token (`.github/workflows/`), as #363 did | S | wave 4 | No `hyperspace/` diff |
| **TY2** | Re-measure #273's audit and merge it as the record | S | TY1 | Docs only |
| **TY3** | Declare attributes, annotations only: `Renderer`, `Registry`, `Analyzer`, `Panel`, `Bindings`. The audit estimates about 500 errors fewer; not re-derived | M | TY1, after the cleanup | AST identical once annotation lines are stripped; goldens unmoved |
| **TY4** | `RenderHost` Protocol for `Frame.r`, `Device` used as a type; no renames | M | TY3 | Same AST check; `--all` |

### Small things already asked for

| Id | What | Size | After |
| --- | --- | --- | --- |
| **SM2** | GRAPH's zoom scaled to the display: the owner's install item 1, still `SCALE = 1.25` [V] | S | nothing |
| **SM3** | Matte and segment thumbnails (row 500) | S | nothing |
| **SM4** | Audit faults still open in `ENGINEERING.md` (R13, R14, R15, U9, U10, V8; P6 is SC3b), each verified first since some may be moot | S each | CL1 |
| **SM5** | Whatever wave 4 did not reach: the words pass (row 668), the player's moves on the undo stack (row 740) | S | wave 4 |

And one look, no code, the owner's, to be asked for in the session's first status message: the **per-face render check**, flipping the face map on a dragonfly preset and
unwiring the backdrop on logo-wobble. The build order calls it the only way the per-face question gets
answered. It decides whether "per-face through an effect chain" is a real item.

## 5. The schedule

| Stage | Items | Merges when |
| --- | --- | --- |
| Any time | H1, H2, SM1 | green |
| 1 | **CL2, alone among anything touching tests' builders**; beside it LY1, LY2, SC1, SM2, SM3 | §2's gate; green, goldens as named |
| 2 | **CL1**, then CL3 and CL4 together; TY1, TY2; SM4 | CL1: the owner's dry run clean; else green |
| 2b | **SC3a, alone** on the render loop, after CL2 and CL1 | green, goldens unmoved, pacing measured |
| 3 | SC2, CT1, LY3, SM5 | green |
| 4 | SC3b, then RT1 | SC3b green; RT1 after SC3b's hand check with a real unplug |
| 5 | TY3, then TY4: last, so they annotate what survived | green, `--all` |

Peak width is about six builders, at stage 1. CL2 before CL1, because a real refusal would otherwise turn the tests red on its own PR [I, by reading]. Why SC1, SM2 and SM3 wait for stage 1 though they depend on nothing: they'd otherwise land under the rename.
No migration in this wave: SC2 and CT1 add new files, seeded on first launch, and nothing old is rewritten.

## 6. What this plan does not do

**Not building, and why:**
- **Splitting the big files.** The conflict data says it isn't the problem. 73 `monkeypatch.setattr(module, …)`
  uses across 26 test files can silently miss after a façade split [I]. That rules out the audit's phase 3,
  and its phase 5.
- **Page-by-page UI work** (audit's phase 4): the owner says `dkit` is orthogonal, and no preparation is wanted.
- **Removing `render.py`'s 95 `getattr(self…`.** They guard hot reload, so removing them isn't neutral.
- **Cheaper goldens yet.** There's no current cost figure. H2's measurement decides. The likely candidate is
  sampling the 51 re-save redraws, but those guard the migrations, so it would be the owner's call.

**Later, recorded:** faces per instance, **a unifying primitive for face patterns and the general shaders** (the owner is thinking about it, 2026-11-06: patterns are "just kind of shaders" and useful as textures and displacement maps), "across" face map, dream fidelity, plan 40's
follow-ups, pad rows in patches, pad feedback and trigger effects, Joy-Con acceleration object, paired poles'
later choice, output warp, plan 29 (DMX, bulbs, Kinect, drums), touchscreen panel, Dante, tempo-synced
springs, audio delay compensation, creative pass.

**Dropped, as decided or overtaken:** DJ Link, MIDI clock, auto BPM (owner, DECISIONS); plan 23's top tabs
(the rail is gone); wands and Wiimotes as such; an IMU prop (the totem covers it [I]).

**Stale records to fix when next touched:** `CHECKPOINT.md` lists DJ Link as an idea; `11-hand-checks.md`
says "none run", and 425 ran; CHECKPOINT says a face list is awaited, and the owner closed it (row 417);
row 653 reads open on a second dream worker, and the fifth round said none.

**Hand checks.** Numbered to 580, and only 425 is recorded as run [V]. Most needed before a show: 489–492's
matters on the #380 build, 506–509, the `/11` run's check, the players screen (CL, CN), and 514–519.

**Rows.** Bulk accepted on 2026-11-06, marked so in the register; only 417, 609 and 751 went to the owner.

## 7. Numbers

Wave 4's remainder keeps rows from 755 and checks from 581. Wave 5 starts well clear: **plan 58, rows from
770, checks from 600, groups from DA.** Pre-assign per item at launch. `CHANGELOG` #374, the Edge lab #340 and
the QR sticker PR #383 are their authors', and outside this wave.

## 8. The owner's answers, 2026-11-06

They overrule anything above. The wording is in `wave-5-session-prompt.md`.

1. **Venues go.** One row per display on the output section, choosing what targets it (SC2).
2. **A display's memory is shared by both Macs,** in the Drive.
3. **Hot-plug is required,** not optional (SC3a, SC3b).
4. A new controller waits until it is dragged to a player.
5. Video sound reaching the analyzer is accepted (LY3).
6. Old-file reading goes only after the owner says both Macs have opened the new library; the owner coordinates that.
7. The 12 trashed looks are deleted in the migration, not converted.
8. **This scope is right:** no new looks or controllers.
9. `dkit` is orthogonal. No UI preparation in this wave.
10. Pending rows bulk accepted and marked so. Row 417: all 17 face patterns stay. Row 609: SEND B stays FINE. Row 751: pairs ask (wave 4 PC2).
11. Merge on green holds for this wave too.
12. A display's target may go to several displays.

Assumed unless the owner objects: patches may read `master.gain` (457 saved rows do), since reading is not
writing; a tapped BPM comes back at launch and a nudge does not; totem and poi are meta, following the player's
`Deck`; a new type-checker complaint fails a PR, old ones don't, from TY1 on; no trial split of `graph.py`; #223 closes
with a note to Dillon once RT1 lands; the control window goes to one display at a time, and floats over a render if no display
is free; controllers' setup is shared between the Macs in the Drive, as displays' is, and who's which player stays on each Mac.
