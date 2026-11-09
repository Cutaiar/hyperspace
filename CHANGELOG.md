# Changelog

## v1.3 — 2026-11-08

### Panel

- GRAPH is always on screen: the rail is gone and every other page (presets, look-back, faces, analyzer, media, fx, LFO, sequencer, audio, camera, output, view, routing, hands, system) is a section of GRAPH's side pane, and the FX page is retired (#345, #350, #360)
- The side pane shows one view at a time at full height — the selection or one section — picked from a row of chips (SELECTION, PATCHES, AUDIO, ROUTING, PLAYLIST, PLAYERS, SYSTEM, and **SECTIONS ▾** for the rest); ⌘[ / ⌘] step back and forward through every view and every node you selected, and each section keeps its own scroll (#439)
- The pane's chips hold still: each is as wide as its name, with a dirty dot in its corner, and what's selected, where the playlist is and who's on air move into their tooltips (#439, #440)
- LOOKBACK is drawn as its two picture nodes, LOOK-BACK and DREAM, with `dream.on` on the dream's head (#350)
- Hold Shift while dragging a panel slider or fader and it moves a tenth as far, with no jump when Shift goes down or up, one undo step a drag (#348)
- The panel says "analyzer", not "band", for the audio analyzer and its tuning; nothing saved changes (#368)
- `--laptop` (or `--single`) launches for one screen with no projector: the render window opens as a plain window, extra outputs and saved window spots are left alone, and the control panel comes to the front (#299)
- Shift-drag fine control now reaches a route's depth, rest and feel knobs, a macro's from / to and GRAPH's backdrop too; those sliders draw filled with their value, like a param's (#375)
- The side pane fits at its narrowest, 240 px: the analyzer section, its meter tags and the patch buttons no longer run into each other (#375)
- ⌘Z takes back the last edit of the preset you're on, or, with the mouse over a rig-tuning section (the analyzer, hands …), that section's last edit, so a ⌘Z mid-set never undoes a tuning tweak from an hour ago; undoing a whole show load is now two ⌘Zs (#373)
- After you move to another deck or section, ⌘Z takes nothing back until you make a change there ("nothing to undo here yet: make a change on deck 2 first"), so a stray ⌘Z can't undo something from ten minutes ago; hovering alone no longer changes what ⌘Z reaches (#386)
- A cursor left in a text field (a find box, a name) no longer counts as working the panel, so a controller move while it sits there can't steal ⌘Z's target (#398)
- GRAPH opens, and refits with a glide whenever another patch loads, with every node in view beside the side pane; **Tidy** frames the same way, keeping the selection; the fit zooms in no further than 1.3× on a 1080p show display or a Retina screen, 1.5× on a large one; resizing the window no longer zooms or moves the canvas, and the panel's stray scrollbar is gone (#411, #429, #439)
- CONTROLS is the control window itself, not a window inside it: no title bar, nothing to drag or close by accident, and it follows the window's size; H still shows and hides it, and the floating pad diagram gets an × (#426)
- Plainer words: "session" and "rig" are gone (now "meta controller", "this Mac", "bus cable"), "preset" becomes "patch" (the **PATCHES** section, "patch: saved TRIP 2") and "show" becomes "install" ("install: saved party"); saved ids and files are unchanged (#407, #436, #437)
- Nudge chips each open their own popup, and a patch strip's save chip no longer covers ▶ in a narrow pane (#414)

### Displays

- Each connected display has its own row in the output section: choose what it shows (the control window, an output, or nothing), fullscreen and flips — no more monitor dropdown; the choices live in `<library>/displays.json`, shared by both Macs (#424)
- A display can be unplugged and plugged back in with no restart: back within `[output] unplug_hold_s` (3 s) its window returns where it was, and the control window moves to another display meanwhile; not yet tried with a real cable (#425)
- `config.toml` can name a screen: `monitor = "MStar"`, exact, with `"MStar #2"` for the second of two counted left to right, so a replug can't swap outputs at the next launch (#404)
- The picture no longer depends on output 1's window: a failed draw holds the last frame instead of flickering, and a locked Mac or sleeping display can't run the loop past 240 fps (#420)

### Decks

- HOLD, TAKE and DROP are gone: there are two decks, one on air and one off air; the APC40's crossfader fades between them (`output.xfade`) and MASTER dims the room (`output.dim`); GRAPH's head shows which deck you're looking at (click it for the other), **copy** on air to off air, the crossfade slider and a timed fade (#380)
- F1–F8, Home, next / prev and the preset list, from keys or pads, always load into the off-air deck, and are refused in words while the fader is between its ends or a timed fade runs; the panel's own load still lands on the deck it shows (#380)
- You can always tell the decks apart: the deck off air is framed in red with an ON AIR inset; the loaded look's strip ("deck 2 · off air"), the desk diagram's header ("the desk plays deck 1"), ROUTING's desk section, the window title and SYSTEM's GPU line all say which is which (#380, #393)
- Playlists for installs: a new playlist section in the side pane plays a list of looks, each for its own dwell in seconds, fading between them — choose or make a list, play / stop, back / on, fade seconds, add a look; lists live in `<library>/playlists/` (#392, #400)
- A fade between decks or a window resize no longer leaks about 16 MB each, which would have ended a long-running install within days (#400)

### Players

- A player select screen: the footer chip reads who is on air and off air ("on air 1 4 · off air 2 3"); click it or press O for the board, then drag a player between ON AIR and OFF AIR, or a controller onto a player, with the mouse; it is also the last section of the side pane (#379)
- A player's place and controllers are kept on this Mac in `players.json`, beside `bindings.json`; a pad's lights follow its player, and a patch row can name a player (`axis@p2`), drawn on GRAPH as its own placeholder when that player has no controller (#376, #379)
- Add a controller from the app: the player board's tray lists pads and MIDI devices not yet set up — drag one to a player to adopt it; the list lives in `<library>/devices.json`, shared by both Macs, with a per-Mac on/off chip, and a quit saves this Mac's copy (#418, #423)
- ⌘Z over the player board takes back moving a controller or a player ("player 2 to off air") (#417)
- Looking for MIDI devices can no longer crash the app when macOS refuses MIDI access; it says so instead (#414)

### Node mode

- Point a controller at a node: from the chip in GRAPH's selection section, the APC40's K1–K8, D1–D8 and S1–S8 fill with that node's params, saved in the patch, per player and per deck; drawn as their own green cables, outlined on the desk, left from the chip or the cable's menu (#396, #397)
- Node mode on pads: a pad's sticks and axes push the node's params and the look comes back on release; buttons that already do something are never taken, and the camera orbit stands down only on the filled axes; not yet tried on a real pad (#433)

### Presets

- The presets list is a tree of folding folders: right-click a preset → move to ▸, or drag it onto a folder; make, rename and remove folders from the panel (#349)
- A preset now holds the hands' look, the clouds' look and the bus cuts; presets move to `/10` and shows to `/3`, migrated with a backup (#351)
- One saved format: module presets are patches of one group (`patches/<group>/`, `hyperspace.patch/2`), and a group holds any node the preset saves; run `tools/migrate_library.py --apply` once, both Macs on this build, between shows (#352)
- A patch can hold the scene, shape, backdrop, pattern, look-back and dream, so a dream + fx + composite patch can be saved; spawning one where the host already has that node is refused in words (#355)
- Spawning a patch with a dream into a preset that has one offers **Replace and spawn** on the sheet, one press and one undo step (#361)
- A new **wire as saved, replacing …** chip lands a patch's outlets even on taken ports and names each cable it cuts; the plain chip still never cuts (#364)
- The one library migration (`/11`): `presets/` becomes `loadable/`, shows become `installs/<name>.json`, and old trash and backups are cleared after one backup; quit both Macs and run `tools/migrate_library.py --apply` once (#434)

### Routes

- Base chase: while `deck.chase` is held, the performer's motion goes into the base, so on release the look stays where you left it; one undo step per hold (#356)
- A preset can no longer route onto a meta param (rig tuning such as `master.gain`): Learn, ROUTING and GRAPH don't offer one, a saved row drops at load with a note, and `tools/meta_routes.py` lists what a library would lose (#371)
- `deck.chase`, `totem.*` and `poi.*` join the preset keys as controls no preset can route to; your own key, pad and desk rows on them still work (#388)

### Gamepad

- BACK holds the base chase; by default the pad no longer taps tempo or swaps presets, and an existing `bindings.json` follows once, with a backup (#369)
- Paired axes: two buttons of one pad (`pair:UP/DOWN`, `pair:A/UP`) act as one two-way lane, through **Learn pair** / **Learn pair (spring)** on the param menu or a **pairs** port group on GRAPH's pad node (#372)
- Experiment: the Joy-Con as a poi's handle — the shape is the weight on a spring string and swings and flies out as you swing the pad; switch it on with "poi off" in the pad window's header or `[poi]`, tune it in its own **Poi** window, with a handle / string / weight guide over the output (#336, #338, #339)
- A sleeping Joy-Con wakes without a restart, the pad window follows a controller connected after launch, and a hard swing no longer loses the pad's attitude (#338, #339)
- Making a pair over a button that is already mapped now asks first: **Keep both**, **Let the pair take over** or **Cancel** (#387)
- The dial readings (petal / blend) are saved in the preset (`pad.dial.left` / `.right`) and picked in the pad node's details on GRAPH instead of SYSTEM; a pad reads the deck it drives, a dialed stick shows its eight sectors, and `dial_left` / `dial_right` in `config.toml` now only set what a preset naming no reading gets (#395)
- Joy-Con version 0: SL / SR change shape, stick click resets the view, − resets the totem, Capture toggles it, L holds the base chase, and the gyro learns its own rest; not yet tried on a live pad (#431)
- The DualSense Edge's hold-MENU save works again, in any role (#431)
- Buttons are named by compass on every pad: `pad:N` / `S` / `E` / `W`, `hat:N` …, pairs `pair:N/S` and `pair:hat.N/hat.S`; the panel says "south button", "d-pad up"; each Mac's `bindings.json` moves once at first launch, kept as `.bak-v3` (#435)
- The poi stays on the screen: its hand and shape are held to the frame, and a still pad stops it in 0.35 s instead of 1.5 (#430)

### Desk

- APC40: hold SEND B and every knob moves its param a tenth as far (`desk.fine`); let go and the next detent carries on with no jump (#344)
- The on-screen APC40 draws SEND B as FINE, lit while held, rather than as a free button (#375)
- A generic MIDI desk such as the DDJ-FLX4 learns at full resolution: Learn listens for a moment, then a 14-bit fader becomes an `abs14` row, a jog a `rel64` / `rel` row, anything else `abs` as before; notes and the APC40 still learn at once; not yet tried on a real FLX4 (#438)
- Learn ▸ Learn Player 1–4 ▸ a controller learns from that one controller, named by model or port ("DDJ-FLX4"); **Any desk** is the old Learn desk, and a plugged-in controller nobody holds is listed greyed (#438)

### Graph

- Matte and segment nodes show their mask as a thumbnail on GRAPH, a segment's `fg` and `bg` pins show their own pictures, and a mask that can't be shown says why (#405)

### Effects

- New **Grow** effect: grass, sprouts, blobs, noodles, mould, coral or cells grow out of the picture and push its pixels (a lens-like bulge, or a lift along Angle); ride `fx.grow.grow` with an LFO to grow it in and out — at 0 the frame is untouched (#381)
- New **Wave Table** effect: a disc of the picture at each root is dragged along grass, noodle or curl paths into an extruded tube; scrub or LFO `fx.wavetable.pos` — at 0 the frame is untouched (#406)

### Media

- The analyzer can listen to the video sound: AUDIO → **Listen to video sound** drives the bands and the beat from the media mix, as the mic does (#343)
- A video's sound now follows its picture: no clicks at rate 1, any rate plays at that speed, reverse and scrubs are heard, and rate 0 is silent (#357)
- Launching with a camera, NDI or Syphon source listed no longer crashes at start-up with a `RecursionError` (#381)
- A patch's media opens on both Macs: a clip missing from this Mac's own folder falls back to the same file in the shared Drive `media/` folder, and assigning a clip that is in both now saves the `shared:` id (#419)
- **Listen to video sound** says on its hover and under the toggle that the off-air look reacts to the on-air video's sound too (#416)

### Hands

- Ultraleap room-frame palm lanes, `hand:<side>.room.roll` / `pitch` / `yaw`, read the same on both hands, with HANDS → feel & calibration → **level room** (#358)
- The orbit: close a hand and turn it, and the camera turns with it, staying put when you open it — a new `turn` route op, clutched by the same hand's grab; not yet tried on a real sensor (#358, #362)
- A deck dropping its hands node no longer takes the other deck's mirror with it: every hands node now follows the one `ghost.mirror` (#408)

### For developers

- Decks: the router's shared `Sources` (`routing_sources.py`) split from its per-deck evaluator, the rig's `SessionRegistry` beside each deck's `Registry`, and deck 2 drawn offscreen with `output.xfade` as the one mix pass — deck 2 runs empty until D5, so leave the fade at 0 (#346, #351, #359)
- Tests run `--dist load --max-worker-restart=4` locally and in CI, so a crash costs one test; the live lock keeps live tests apart within a run; `tools/sort_register.py` sorts the register (#347, #363)
- The golden tool frees its rig on its own GL context, so a stray free no longer fails a later test with `GL_INVALID_OPERATION` (#366)
- Decks D5: `deck.MetaController` with a `Pointer` per holder (`pointer.py`) and `docs/GLOSSARY.md`; three undo stacks, one per `Deck` and `MetaController.undo`, with `library.MetaMarks`; `MetaController.follow_fader` (on air by the crossfader's side), timed fades via `output.xfade_s` and `copy_on_air` — live in the app since D5d (#370, #373, #378, #380)
- `players.py` (`Players`, `Player`, `Duty`), and `Router.feeds` keeps a row quiet while its controller's pointer is on the other deck (#376)
- Node mode's saved form: an optional `node_mode` key on presets (`nodemode.py`, `Presets.node_mode`), no schema bump and no caller yet; `docs/plans/57-format-lane.md` lays out the format lane (#377)
- D5d: `hold.py` is deleted (`output.hold` / `.take` / `.drop`, `Deck.hold`, `Undo.checkpoint`), `meta.tick` runs first in `app.frame`, and `apc40.META_CONTROLS` reserves the meta controls on the first desk; `tools/drive_decks.py` drives the verbs in the real app (#380)
- The two layers made mechanical: `params.PER_DECK_META`, a third `part_of`, with `is_meta_id` / `is_session_id` / `is_per_deck_meta_id`, and `tests/test_layer_boundary.py` puts every param in one layer and every module on one side of the wall (#388); identifiers renamed to the signed glossary (`MetaRegistry`, `MetaTable`, preset → patch), with saved ids, files and panel words unchanged (#389)
- `playlist.py` (`Playlist`, `Entry`, `Playing.tick`), ticked last by `MetaController.tick`; `MetaController.crossfade(to, seconds=None)`; `tools/drive_playlist.py` (#392, #400)
- `.gitattributes` merges the four doc tails by union and `tests/test_doc_numbers.py` catches a number taken twice (#391); tests leave no `undo._hand` / `_loading` behind and a stuck undo stack fails fast (#394)
- Node mode: `node_desk.NodeDesk` derives rows from `LoadedPatch.node_mode` by `nodemode.fill` for desks and pads, ahead of saved rows, with a `NODE_MODE` cable kind and its own `…|node` bundle (#396, #397, #433)
- New shared-file stores beside `library.py`: `sharedfile.py`, `devicelist.py` (`devices/1`), `displays.py` (`displays/1`); `midiports.port_names()` never raises; `hotplug.py` and `pacing.py` with a hidden root window holding the GL context (#414, #418, #420, #424, #425)
- Saving `outputs.py`, `render.py` or `ghost.py` hot reloads again (slots moved to the cold `hot_slots.py`), and the slots rule imports in list order (#421, #427)
- `Param.__post_init__` makes every meta param non-modulatable (#409); `Project` is `Install` in code (`Library.install`, `DeckInstall`) (#436); `routing.layout_of` gives rows by pad model (#431)
- `tools/type_ratchet.py` fails a PR on a new pyright complaint against `tools/type_baseline.json` (#412); `docs/AUDIT-STRUCTURE-2026-10.md` records the structure audit (#413); `tools/wait_green.py`, re-measured test times (#403); `tools/poi_probe.py` replays a real Joy-Con tape (#410); the doc tails were restored and `tests/test_doc_numbers.py` checks more (#432)
- The `abs14` route op reads CC n + 32 as the LSB and rests between detents; `midi.heard_as` and `midi.LISTEN_S` drive the listening Learn, and `players.controllers_of` feeds its menu (#438); `Panel.graph_fit` switches GRAPH's fit off, as the canvas tests' rig does — restart after pulling (#439)

## v1.2 — 2026-11-02

### Graph

- Any picture node can be dropped on a cable to splice it in — composite, switch, delay, resize, dream, look-back, cut, segment, backdrop, the faces pattern, a media channel — not just effects (#307)
- Dropping a composite or switch on a cable asks which inlet takes it (under / over, in1 … in8); the others stay open (#307)
- A channel dropped on a cable feeds that port instead; the old source keeps its other cables and the line says if it now feeds nothing (#307)
- ⌘-drag lifts a wired node of any kind out of its chain and onto a cable, closing the gap behind it (#307)
- Right-click a cable → "insert ▸" offers every picture kind, not just effects (#307)
- A node that can't go on a cable says why, and only the cables that could take it dim while you drag (#307)
- Cable drag targets stay finger-sized at any zoom — at least 22 px on screen — and the drop onto a cable reaches as far zoomed out as zoomed in (#300)
- Media channels a–h are in the add menu (media ▸ channel), and the preset-only view always shows all eight, wired or not (#303)
- A node you just added is never hidden by the preset-only view, and an LFO feeding a modifier feeding a param is drawn too (#303)
- Right-click a picture cable → starters ▸ feedback splices in a trail loop (composite laid over, a one-frame delay, the new `fade` effect at 0.75); a picture node's menu has "add feedback after" too — one undo step, as many loops as you like (#319)
- Groups behave: ungrouping no longer hands the old number to the next group, a deleted node leaves its group at once, and undoing the delete puts it back in (#321)

### Media

- The GRAPH canvas is a live source: MEDIA → Live → `panel:graph`, put it in a channel and wire it anywhere a picture goes — the projector, or the backdrop behind the canvas for a loop; off the page it holds 1 s, then reads black (#313)
- Videos can play their sound: each channel has an `audio` toggle and a gain slider (off, then −30 … +6 dB) on MEDIA, mixed into one output that follows the transport; SYSTEM shows a `media sound` line; an occasional click at rate 1 is expected for now (#316, #324, #329)
- The segment node no longer leaks memory — two segment nodes over a long set had grown the app to 140 GB and frozen the Mac (#310)

### Gamepad

- The DualSense Edge works over USB and Bluetooth: touchpad, back and Fn buttons, motion, light bar, rumble, trigger resistance, player lights — new `touch:` and `motion:` sources and `<role>:0`–`8` output ports, all in Learn pad (#306)
- Any controller can fill any role: a gamepad entry's `controller =` takes `any`, a model (`edge`, `dualsense`, `xbox`, `x360`), a family (`sony`, `xbox`) or a USB id (#306)
- The Joy-Con (L or R) connects over Bluetooth, one per role, with its six-axis sensor, stick drift calibrated, HD rumble and player lights (`controller = "joycon-l"`) (#315)
- The pad window has four views — Map, Faithful, Lanes, Cockpit — picked with Pad view on SYSTEM or by clicking the view's name in the pad window's header (#312, #315)
- Experiment: the Joy-Con as a 4D totem — its gyro turns the shape's rotation planes, X / Y / B swing one into W, A resets, tilt pans; switch it on with "totem off" in the pad window's header or `[totem] on = true` (#330, #335)

### Routes

- Every new route lands with the `smooth` spring feel (0.5 s, no bounce) instead of raw; envelope routes keep auto, and saved routes are unchanged (#301)
- A band routed to a param now lands as a gentle push about its base (`LANE_DEPTH` 0.12) instead of taking the param over; an LFO lands as a push (0.25) too; toggles and menus still follow the source (#305)

### Effects

- Calmer shipped defaults — effect speeds about a quarter, amounts about a third, LFO depth 1.0 → 0.5 — so turning an effect on is no longer jarring; presets that set their own values look the same (#304)
- Fine control at the low end: every effect's `speed` and fourteen amounts are on new tapers, so 0.05× and 5 % are a few knob steps instead of under one; saved routes onto them are converted at load and reach the same values (#322)
- A knob turned an hour into a set no longer throws the picture somewhere else — warp's drift and scale, tripcolour's pulse, RINGS' colour and the field's and media path's rates now change speed without a jump (#325, #326, #328)

### For developers

- The panel publishes the GRAPH page's selected node (`Panel.graph_selected`, `select_graph_node`, `graph_selected_params`) — groundwork for a controller node mode; restart, don't hot reload (#302)
- `tools/calm_lanes.py` holds every preset's band routes to the new depth, as springs; `tools/retaper_routes.py --write` rewrites a library for the new tapers — run it before the next show (#311, #322)
- One `Deck` bundle built by `Deck.build` (`Host.deck`, `Panel.deck`), no behaviour change — the first step of plan 44's decks; restart, don't hot reload (#327)
- A hung test fails by name instead of stalling the run, and live-device tests take turns across processes (#331)
- The panel driver's Ctrl is the key imgui reads as Ctrl, so it types on a Mac (#309)

## v1.1 — 2026-10-30

### Panel

- The panel's fonts ship inside the app — Inter for words, JetBrains Mono for numbers — so every machine draws the same text (#297)

### Renderer

- Effects and the cut read their own pixel exactly — a 1:1 read that landed a step off on ~0.7% of pixels now copies byte for byte (#296)

### For developers

- CI on every PR and push to `main`: ruff + the fast test tier on Linux, ~3.5 min, green off the Mac (#286)
- Vercel deploys `main` only — PR previews are gone; a manual `vercel deploy` still makes one (#294)
- Cloud sessions set themselves up like CI, and a script can drive the app's panel by control id with no person at the rig (#295)

## v1 — 2026-10-29

### Graph

- Drop a node onto a wire to splice it into the chain — the wire it will land on glows gold while you drag, everything else dims, and the pointer says what letting go will do (#292)
- ⌘-drag moves an effect that's already wired; its old chain closes over the gap, one undo step (#292)
- Deleting a modifier now bridges the chain — `LFO → Smooth → size` becomes `LFO → size` instead of a dead cable (#292)
- Delete / ⌫ removes the selected node or cable whenever the canvas is focused — a Mac's delete key finally works (#285)
- Option-drag box-selects cables — now said on the page (#292)
- Selecting the Shape node shows a live white wireframe of just the shape at the top of its side panel; it costs nothing when not shown (#283)

### Gamepad

- Preset walk moved to a 0.6 s hold on d-pad ◀/▶ — brushing past them no longer throws away the live look (#284)
- B now toggles points, X toggles screen strokes, BACK taps tempo (#284)
- Existing bindings files migrate themselves with a backup; anything you remapped by hand is left alone (#284)

### Feel

- Springs are set by duration and bounce (Apple's model) instead of frequency and damping — named feels: snappy, smooth, bouncy, wobbly, lazy (#289)
- Every feel now shows two plots: the curve of what the setting does, plus the last few seconds of the live signal (#289)
- The spring preset picker draws each option's curve on one shared axis so you can compare before picking (#289)
- Old shows convert on open and back themselves up first — restart, don't hot reload, to pick this up (#289)

### For developers

- The screenshot tools render the real frame again instead of black (#288)
- Vercel skips a deploy when the project's folder didn't change — Python-only PRs stop burning the daily quota (#290)
- New `REVIEW.md` + `/deep-review` skill: the checklist that caught a saved-show data-loss bug before merge, now runnable on every PR (#291)
