# Plan 58 — wave 5: the cleanup, the rig's last piece, and cheaper changes

**Status: running since 2026-11-06; state per item is in [`tier-2-3-build-order.md`](tier-2-3-build-order.md), "Where we are". §9 corrects §2 and §4 against `main`: read it with your item.** Planned 2026-11-06. Read against `main` at 34caf3c, before #380 merged (463b154), by three independent
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

## 2. What waits, and for what

**The owner, 2026-11-06: getting wave 5 running matters most.** After the rename, only the cleanup needs the migration. So screens, hot-plug, controllers, leak fixes, words and types start now, beside the end of wave 4. See the prompt's three tracks; where §5 disagrees, the prompt is right.

**The cleanup (CL1–CL4) waits for one thing:** the owner says the migration ran and both Macs have opened the new library. The `/11` run's own hand check is the same fact checked. In §4, **After** is a hard dependency.

### 2a. Dylan's Mac

The library is one shared Drive folder, so there's no separate library to fetch. Dylan needs **the new code**, and needs to **open the app once**.

1. **Before the migration:** quit Hyperspace when told, and leave it closed while it runs. A save from the old build during it could put old files back.
2. **After it:** let Google Drive finish syncing. Then, in the repo: `git checkout main`, `git pull`, `uv sync`, in `hyperspace-python/`.
3. **Launch once.** Each Mac moves its own `bindings.json` at that launch, with a backup. Load a few patches. Tell the owner it worked.

**If Dylan doesn't, before wave 5's cleanup:**
- **Old code on the migrated library:** that Mac refuses every file until it updates. Nothing is lost; it just can't open looks.
- **Updated code but never launched, then the cleanup lands (CL3):** the reader for the old `bindings.json` is gone, so Dylan's mappings wouldn't move. That is what the gate prevents. The backup and `git` can recover it, but it's a bad day before a show.
- **Saving from the old build after the migration:** old-format files reappear in the Drive, in the old folder. CL1's dry run would catch them.

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
12. A display's target may go to several displays; the control window goes to one.
13. The panel says patches; session, rig and preset leave its words, preset with the migration.
14. A cart starts by itself after launch: **SM6**, one key in the install file, after the migration.

Assumed unless the owner objects: patches may read `master.gain` (457 saved rows do), since reading is not
writing; a tapped BPM comes back at launch and a nudge does not; totem and poi are meta, following the player's
`Deck`; a new type-checker complaint fails a PR, old ones don't, from TY1 on; no trial split of `graph.py`; #223 closes
with a note to Dillon once RT1 lands; the control window goes to one display at a time, and floats over a render if no display
is free; controllers' setup is shared between the Macs in the Drive, as displays' is, and who's which player stays on each Mac.

## 9. Corrections, read against `main` at cddc4eb, 2026-11-06

SEM moved most of §4's references, and building from them would be wrong in places. **Where this section disagrees with §1–§7, this section is right;** the owner's answers still overrule it. Read by one independent agent, tags as above. A builder verifies what it relies on.

### What changes scope

1. **SC3a is larger than moving the context, and goldens can't prove it.** Goldens draw on an offscreen target (`tools/golden_frames.py:533`) and never run `_draw_render` [V]. Output 1 is the only MSAA window (`app.py:469`, `SAMPLES 4`) and the only transparent one (`app.py:477`). `outputs.Offscreen` (`outputs.py:260`) has no samples [V], so moving output 1 onto it would silently drop 4× MSAA on the real picture. The overlay needs alpha through `Presenter` too. Frame size, dpr and the scene's sample count come from output 1 (`render.py:1562`, `:1717-1718`, `:1768`). "Goldens unmoved" is necessary, not the proof: **also require `drive-the-app`, a measured MSAA and overlay check, and pacing numbers.** Seams: 11 `_draw_render` uses in `tests/test_app_boundary.py`; 10 test files and `tools/dial_demo.py` name `slots[0]` or `render_win`.
2. **SC2 is bigger than M.** `Slot` holds one `win` (`outputs.py:226`) and flips live on the slot's `Switches` (`outputs.py:47-61`), read as the renderer's last step in a `View`. A render on several displays, each row with its own flips, needs a window list per slot and flips per window, so it reaches `View` and `Presenter`. `output.N` ids are a saved format: wires and bus cuts name them (`graph.py:658`, `window_ports` `graph.py:1323`). So displays map onto N, and N never renumbers.
3. **SC2 and CT1: launch order.** `_windows` runs at `app.py:1445`, `Library(...)` at `app.py:1492`. `displays.json` must be read from the configured library path before a `Library` exists, with an answer for an unmounted Drive. SC2 also leaves `windows.json` (`render[k]` indexed by output place, `placement.py:109`) meaning something unstable.
4. **SC3b must change the loop and some fixed lists.** Closing any window ends the app (`app.py:1833`). `later`, `Keys`, `opened` and `all_windows` are captured once (`app.py:1458`, `:1741`, `:1774`, `:1802`). `register_switches` declares no params for an undrawn slot, and `.dim` only with several outputs (`overlay.py:442`), so `output.N.*` appearing mid-run moves param ids and bindings. [Rec] Keep all slots drawn from launch.
5. **CT1 "also looks for MIDI" makes audit fault R15 worse.** Each look makes a CoreMIDI client (`midi.py:159`, `:280-286`), the tray looks every `LOOSE_S = 1.0` (`ui_players.py:67`), and a native rtmidi abort is what R15 names. CT1 needs a slow or shared look, or R15 fixed first. `watch` reads only `config.toml` (`devices.py:2269`, `config.read_devices`), so it must watch `devices.json`, and in a Drive-synced file the mtime also moves from the other Mac.
6. **CL3's `overlay.*` aliases are saved, not "Saved? no".** Factory rows name them (`bindings.default.json:20,21,160,161`, `apc40.py:617`, `routing.py:469,1157`, `ui_desk.py:645-646`), so each Mac's `bindings.json` holds them. Plan 57 doesn't mention them [V]. **Add them to the `bindings/4` road in the migration,** or keep the aliases. `DEVICE_TABLES`/`_translate` is also the default device set with no `[[devices]]` (`config.py:636`, `:729`), so it goes only after CT1's defaults.
7. **LY2 has side effects, and the count is 102, not 87.** On the test rig with 6 bands: 89 shared + 13 per `Deck`, by group band 79, preset 13, master 3, tempo 2, output 2, scene 2, audio 1. `modulatable=False` is more than a label: it changes `push` (`params.py:646`), position rows (`routing.py:4192`, `:4215`), Learn's words (`learn.py:1171`) and "Learn pair (spring)" (`ui.py:1136`). Check each door, and that meta desk rows on `master.*` and `band.*` still work.
8. **LY1 is worse than §4 says: it is a look-to-look leak.** `LoadedPatch`'s graph section `land` (`loadable.py:438-462`, `remove_prefix` `:456`) → `Registry.remove` → `MetaRegistry.remove` (`params.py:1361+`). So one `Deck` dropping its hands node removes `ghost.2.mirror` from the other `Deck`, which may still hold that node. Files: ghost, params, **loadable, library**; not `deck`.
9. **SM2 must not change `SCALE`.** It is an import-time constant behind canvas units (`graphview.py:2083-2088`, `ui_graph.py:248`, `:1631`), and saved layout positions are in those units. Only a read of zoom was found (`ed.get_current_zoom`, `ui_graph.py:1622`), with `navigate_to_*` at `:1686`: check the binding has a setter.
10. **Done or moot:** H1 (#391); SEM's "meta, one per `Deck`" class, so §2's SEM bullets are history; the `RigWires` rename, so `graph` leaves RT1's files and only `docs/GLOSSARY.md:20` still says it; R13, which left `docs/AUDIT-2026-09.md` in f673a37a though `docs/ENGINEERING.md:3545-3546` still names it; U10, likely, so measure once and delete.
11. **Order.** SM4, TY1 and TY2 need nothing from CL1, so the prompt's order stands. SC3a's "After: SC1" isn't a code dependency. CL1 and CL2 depend on `/11`, which doesn't exist yet: `LOOK_SCHEMA` is `/10` (`graphmigrate.py:87`). RT1's "After" adds the gate, as the prompt says.
12. **Row 740 and row 668.** Row 740 says ⌘Z over the board takes nothing back (`ui_players.py:898` agrees), so moving player moves onto the meta stack amends it. Row 668 is plan 49 U3; the wave 4 prompt says "PC words pass, row 668 if wanted".

### Saved formats before the migration

**Must wait:** `tempo.nudge` (`tempo.py:165`; `tests/test_tempo.py:212,223`), `output.bg` and `.alpha` (`overlay.py:256,261`). **LY1:** the next save drops `ghost.N.mirror` from a show's session (`library.py:1465`, `:1556`, `_held_back` `:1560`); keep tolerating the id on read. **New root files are safe:** `Library.groups` (`library.py:2096`) and `migrate_library.py:497` only walk directories [V]. Keep the new stores out of `library.py`, because the migration wins there.

### SC3a: where output 1 is [V]

- **Context:** `app._windows` (`app.py:390`) creates `render_win` at `:479`, the share root for `ctrl_win` (`:487`) and later outputs (`:509`); `slots[0].win` at `:498`. `app.main` (`app.py:1431`): `make_context_current` `:1452`, `moderngl.create_context` `:1454`. Deck 2's `renderer.sibling()` at `:1655-1656`. VAOs and FBOs don't share across contexts, so the whole renderer lives there.
- **Pacing:** `swap_interval(1)` on `render_win` at `:1453`; later outputs get 0 (`:585`), the control window 0 (`:1466`). The only blocking swap is in `_draw_render` (`app.py:650`), its `finally` at `:759-760`. The loop at `:1833-1866` has no other wait. `ui.py:2383` says "paced by output 1".
- **As a drawing target:** `_draw_render:687-697`, `:699-700`, `:715`, `:734`, `:740`. `Renderer.draw_outputs` (`render.py:1559`) raises without `views[0].target` (`:1587`); an offscreen first view works.
- **Also holding `render_win`:** `_save_windows:319-333`, `_make_output:529` via `:1525`, `_later_output:558`, `Keys:1741`, `Mouse:1742`, watchdog `:1776`, `_close_publishers:616`/`:1797`, `all_windows:1802`, `quit:1818`, smoke close `:1838`, `_samples_of` `render.py:660`. Also `Fade` (`deck.py:1095,1125`).
- **Likely shape [I]:** a hidden root window holds the context; output 1 becomes a `Presenter` slot. **For the spike to test:** Cocoa may not block a swap on a hidden window, so a pacer on the first live display's window, else a timer; whether a share group survives one member window being destroyed on NSGL (never destroying the root avoids it). Decide V8 here: `reloader.poll()` (`app.py:1229`) runs with the control context current.

### References by item [V]

| Item | Now |
| --- | --- |
| H2 | `ENGINEERING.md:3172-3173` say ~17 s and ~55 s; also `:3545-3546`. `--collect-only --all`: **6938** tests. `wait-green.sh` is outside the repo (`~/.claude/handoffs/wave4/`), so "moves" means copy |
| SM1 | `origin/worktree-poi-hand-fix:hyperspace-python/tools/poi_probe.py` (309 lines). Main's `poi.step` is `poi.py:416`. `st.box`, `box_for`, `_bound`, `_valid`, `_rotate`, `_hook_view_reset` are branch-only, so `numbers()`'s walls are rewritten. **The tape `tests/fixtures/pads/joycon-poi-excerpt.jsonl` and `tests/test_poi_real.py` are branch-only: salvage the tape with `git add -f`.** #342's poi fixes are not on main, so the probe shows main's drift, not #342's result |
| LY1 | `params.py:975-976`, keys `:179-183`; `ghost.py:178-199`, `RoomSetting` `:121`; `_seed` `loadable.py:517`; docs `loadable.py:348-350`; panel `hands/panel.py:305` |
| LY2 | `tests/test_meta_rule.py`; `learn.py:1127`, `ui_routing.py:963` already ask `meta_refusal` (`routing.py:1582`) |
| LY3 | `media/mixer.py:82-89`, `listen` `:307`, push `:534`; `media/channels.py:258,311,382`. The toggle's widget isn't located yet |
| SC1 | On `origin/venues` only: `named` :236, `match` :251 (first case-blind substring), `read(..., screens)` :263, `index(..., screens)` :293; its `tests/test_placement.py:304` pins first-match-wins, so invert it. Main: `read` `placement.py:241`, `index` `:256`, `screens` `:70`, `place` `:263`. **Also `app.py:350`, `:461`, `:462`, `:540`, `:564`; `config.py:386`, `:817`.** `Output.monitor` stays an index at runtime (`overlay.py:421-430`) until SC3b |
| SC2 | `overlay.py:456-462`; `outputs.py:204`; `MAX_OUTPUTS` `outputs.py:41`. Seeds: `config.screens` `:478`, `_screens` `:437`, `SCREEN` `:322`. `--laptop`: `config.laptop` `:502`, `app.py:1436,1447,1805`. Page line `ui.py:2381-2384` |
| SC3b | No `set_monitor_callback` anywhere. `_later_rect` `app.py:363`, `placement.index:256`, `GlfwBackend.monitors` `overlay.py:110` |
| CT1 | `DeviceRegistry` `devices.py:1715`, frame hook `:2167`, `apply` ~`:2300-2335`, `WATCH_FRAMES` `:111`; `_open_devices` `app.py:795`; `players.py:44,167`; tray `ui_players.py:28`, `loose` `:244`, `:287`. A loose pad is read-only until in config, so "adopt" is new |
| RT1 | Readers: `config.py:296`, `:322`, `:437-466`, `:478`, `:817`; `app.py:346-353`, `:461-462` |
| CL2 | `loadable.py:141` (was `preset.py`), `library.py:142`, `headless.py:109`, `graphview.py:126`, **`render.py:3719`**, `hotreload.py:59`, `patches.py:54,249`, `golden_frames.py:274`. 48 test files, 16 tools. 124 tracked fixture JSONs, 104 below `/10`. `tests/wiredframe.py` (345 lines, 14 test files) itself stands on graphmigrate. 134 `hyperspace.preset/N` lines in `tests/*.py` by this grep, not 74 |
| CL1 | `forward` `graphmigrate.py:1749`, called `loadable.py:1030`; `patches.forward:244`; `library.forward_group:794`. `palettecompat`: `library.py:144`, `loadable.py:173`, `hotreload.py:58`. `pan_world`: `params.py:1402`, `library.py:155,822`, `loadable.py:203,990`. `retaper_depths`: `params.py:1473`, `library.py:156,2465`, `loadable.py:205,1004`, **`routing.py:2493`**. `_legacy` `graph.py:1996`, `:2012,:2043`. Old-show readers `library.py:545`, `:874-881`, `:977`, `_KEPT_LOOKS :1620` |
| CL3 | `MIGRATED_FILES` `library.py:295,353`; `LEGACY_MIDI_FILE` `routing.py:334,2366`; V1/V2 `routing.py:330-332,427,1326`, ~`:2485`; `Carried` `:2017,2113,2316,2395,2433`; `LEGACY_OUTPUT` `config.py:287,782,790`; `DEVICE_TABLES` `config.py:341,530,636,707,719`; `_seed_sinks` `devices.py:1752,1897,2325`, `routing.py:2334`; aliases `overlay.py:274-282` |
| CL4 | `RETIRED_MODULES` `library.py:292,2114,2515`; **`ui_loadable.py:66,306`**; `loadable.py:161,609,1287`; `tools/migrate_library.py:486-505` |
| TY1 | No pyright config in `pyproject.toml`. 7 `tests/test_*_boundary.py`; `test_layer_boundary.py` already uses `PKG.rglob`, others unchecked. No size cap yet. `.github/workflows/tests.yml` |
| TY2 | #273 mergeable, draft: `docs/AUDIT-STRUCTURE-2026-10.md` (540 lines, at `7506f54`, pre-SEM words), `docs/ARCHITECTURE.md` (+3/−1). Needs a header on the re-measure and old names |
| TY3 | `Renderer` `render.py:1100`, `Registry` `params.py:883`, `Analyzer` `analyzer.py:240`, `Panel` `ui.py:731`, `Bindings` `routing.py:2218` |
| TY4 | `Frame` `graph.py:3138`, `self.r` `:3245`, `:3267`; `devices.Device` `:172`, `Base` `:257` |
| SM2 | `SCALE` `graphview.py:2083` |
| SM3 | Row 500 `DECISION-REGISTER.md:542`. `thumb_of` `graphview.py:967` draws only `OUTPUT == IMAGE`; `MatteNode` `graph.py:4694`, `SegmentNode` `:5050` are `MASK`, one-channel 8-bit, so `Renderer._thumbnails` (`render.py:1914`) and `outputs.PreviewTextures` need a grey read; `ui_graph.thumb_name:2911` |
| SM4 | **R14:** `set_norm` `params.py:501-508`, `preset.select` `:2863`, nothing in `learn.py` refuses. **R15:** `midi.py:159,240,245,280`; no `Ports` in `hands/core.py` (others: `bridge.py:346`, `midi.py:387`), so the audit text is stale. **U9:** `ui_lfo.py:182`, `_ctx` `ui.py:920`, `tests/test_ui_lfo.py:73`. **U10:** `ui_loadable.py:187,298,332`, `ui.py:1789`, `ui_patterns.py:233`, `tests/test_ui_loadable.py:394`. **V8:** `app.py:1229`, `render.py:1323`, `ghost.py:1295,1936`, `lookback.py:659,1004` unread; `Presenter` defers at `outputs.py:1094` |
| SM5 | `meta.undo` `app.py:1678`, `ui_players.over :896-899` |
