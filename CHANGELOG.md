# Changelog

## v1.3 — 2026-11-06

### Panel

- GRAPH is always on screen: the rail is gone and every other page (presets, look-back, faces, analyzer, media, fx, LFO, sequencer, audio, camera, output, view, routing, hands, system) is a folding section of GRAPH's side pane; ⌘[ / ⌘] and `ui.page` now pick the focus section, and the FX page is retired (#345, #350, #360)
- LOOKBACK is drawn as its two picture nodes, LOOK-BACK and DREAM, with `dream.on` on the dream's head (#350)
- Hold Shift while dragging a panel slider or fader and it moves a tenth as far, with no jump when Shift goes down or up, one undo step a drag (#348)
- The panel says "analyzer", not "band", for the audio analyzer and its tuning; nothing saved changes (#368)
- `--laptop` (or `--single`) launches for one screen with no projector: the render window opens as a plain window, extra outputs and saved window spots are left alone, and the control panel comes to the front (#299)
- Shift-drag fine control now reaches a route's depth, rest and feel knobs, a macro's from / to and GRAPH's backdrop too; those sliders draw filled with their value, like a param's (#375)
- The side pane fits at its narrowest, 240 px: the analyzer section, its meter tags and the patch buttons no longer run into each other (#375)
- ⌘Z takes back the last edit of the preset you're on, or, with the mouse over a rig-tuning section (the analyzer, hands …), that section's last edit, so a ⌘Z mid-set never undoes a tuning tweak from an hour ago; undoing a whole show load is now two ⌘Zs (#373)
- After you move to another deck or section, ⌘Z takes nothing back until you make a change there ("nothing to undo here yet: make a change on deck 2 first"), so a stray ⌘Z can't undo something from ten minutes ago; hovering alone no longer changes what ⌘Z reaches (#386)
- A cursor left in a text field (a find box, a name) no longer counts as working the panel, so a controller move while it sits there can't steal ⌘Z's target (#398)

### Decks

- HOLD, TAKE and DROP are gone: there are two decks, one on air and one off air; the APC40's crossfader fades between them (`output.xfade`) and MASTER dims the room (`output.dim`); GRAPH's head shows which deck you're looking at (click it for the other), **copy** on air to off air, the crossfade slider and a timed fade (#380)
- F1–F8, Home, next / prev and the preset list, from keys or pads, always load into the off-air deck, and are refused in words while the fader is between its ends or a timed fade runs; the panel's own load still lands on the deck it shows (#380)
- You can always tell the decks apart: the deck off air is framed in red with an ON AIR inset; the loaded look's strip ("deck 2 · off air"), the desk diagram's header ("the desk plays deck 1"), ROUTING's desk section, the window title and SYSTEM's GPU line all say which is which (#380, #393)
- Playlists for installs: a new playlist section in the side pane plays a list of looks, each for its own dwell in seconds, fading between them — choose or make a list, play / stop, back / on, fade seconds, add a look; lists live in `<library>/playlists/` (#392, #400)
- A fade between decks or a window resize no longer leaks about 16 MB each, which would have ended a long-running install within days (#400)

### Players

- A player select screen: the footer chip reads who is on air and off air ("on air 1 4 · off air 2 3"); click it or press O for the board, then drag a player between ON AIR and OFF AIR, or a controller onto a player, with the mouse; it is also the last section of the side pane (#379)
- A player's place and controllers are kept on this Mac in `players.json`, beside `bindings.json`; a pad's lights follow its player, and a patch row can name a player (`axis@p2`), drawn on GRAPH as its own placeholder when that player has no controller (#376, #379)

### Presets

- The presets list is a tree of folding folders: right-click a preset → move to ▸, or drag it onto a folder; make, rename and remove folders from the panel (#349)
- A preset now holds the hands' look, the clouds' look and the bus cuts; presets move to `/10` and shows to `/3`, migrated with a backup (#351)
- One saved format: module presets are patches of one group (`patches/<group>/`, `hyperspace.patch/2`), and a group holds any node the preset saves; run `tools/migrate_library.py --apply` once, both Macs on this build, between shows (#352)
- A patch can hold the scene, shape, backdrop, pattern, look-back and dream, so a dream + fx + composite patch can be saved; spawning one where the host already has that node is refused in words (#355)
- Spawning a patch with a dream into a preset that has one offers **Replace and spawn** on the sheet, one press and one undo step (#361)
- A new **wire as saved, replacing …** chip lands a patch's outlets even on taken ports and names each cable it cuts; the plain chip still never cuts (#364)

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

### Desk

- APC40: hold SEND B and every knob moves its param a tenth as far (`desk.fine`); let go and the next detent carries on with no jump (#344)
- The on-screen APC40 draws SEND B as FINE, lit while held, rather than as a free button (#375)

### Effects

- New **Grow** effect: grass, sprouts, blobs, noodles, mould, coral or cells grow out of the picture and push its pixels (a lens-like bulge, or a lift along Angle); ride `fx.grow.grow` with an LFO to grow it in and out — at 0 the frame is untouched (#381)

### Media

- The analyzer can listen to the video sound: AUDIO → **Listen to video sound** drives the bands and the beat from the media mix, as the mic does (#343)
- A video's sound now follows its picture: no clicks at rate 1, any rate plays at that speed, reverse and scrubs are heard, and rate 0 is silent (#357)
- Launching with a camera, NDI or Syphon source listed no longer crashes at start-up with a `RecursionError` (#381)

### Hands

- Ultraleap room-frame palm lanes, `hand:<side>.room.roll` / `pitch` / `yaw`, read the same on both hands, with HANDS → feel & calibration → **level room** (#358)
- The orbit: close a hand and turn it, and the camera turns with it, staying put when you open it — a new `turn` route op, clutched by the same hand's grab; not yet tried on a real sensor (#358, #362)

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
