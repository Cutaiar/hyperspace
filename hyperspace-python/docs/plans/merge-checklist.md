# Before merging the open PRs: the checklist (2026-10-23)

Everything that stands between Dan's open PRs and `main`, in order. The hand
checks below are the titles from [`11-hand-checks.md`](11-hand-checks.md);
open that file for each check's steps and its *Pass:* line. No person has
run any of them yet. Every PR's automated suite and golden frames are green
(#233: 3308 passed, 661 goldens; #235: 3516 passed, 693 goldens, the 661 unmoved).

## Which branch to run them on

**`plan-31-32-integration` (#233) for everything** — it sits on top of the
whole stack (main → #195 → #224 → plans 31 + 32), so groups U, W, V, X, Y,
Z, AA and AB all run on it (`uv sync` first). The guide's "Before you
start" names each plan's own branch; that was for running them before the
stack existed. Exceptions:

- **286–295** (the APC40 sequencer page) need `plan-31-a1` (#231, with Dillon).
- **285, 301, 317** each have a last step on an *older* build (to see it refuse a `/3` or `/4` preset): use the other Mac on `main`, or a second checkout.

## The PRs and what each needs

| PR | Into | What it needs before merging |
|---|---|---|
| **#235** plan 33, the free graph | `plan-31-32-integration` | hand checks AC (318–328) on `plan-33-free-graph`; **merge it into #233's branch before #233 merges**, so the stack grows by one PR |
| **#233** plans 31 + 32 together | `plan-28-30-integration` | hand checks Z (280–285; 286–295 are #231's), AA (296–316), AB (317) on this build |
| **#236** plan 34 (T1–T3) + plan 35, the free frame | `main` (retargeted 2026-10-25, after plan 33's stack merged) | hand checks AE (342–352) on `plan-34-feedback`; plan 34 resumes on it after; **both Macs on the build before a `/6` save** |
| **#224** plans 28 + 30 | `plan-24-26-27-integration` | hand checks X (220–231, 267–271), Y (232–276), Z's 277–279 (the instanced field from `main`) |
| **#195** plans 24, 26, 27 | `main` | hand checks U (148–167), W (168–190, 219), V (191–218) |
| #231 plan 31 A1 (APC40 sequencer page) | `plan-31-integration` | **Dillon's sign-off** (the desk is his, decision 10); checks 286–295 with him. Not needed for #233 |
| #230 plan 31, #232 plan 32 | — | nothing: **close after #233 merges** (records; #233 carries both) |
| #205 leapc-cffi any version | `merge-main-20261016` | nothing: **close** — its head is already in `plan-28-30-integration` |
| #204 plans 28/30 prompt | `plan-24-26-27-integration` | nothing: **close** — its head is already in `plan-28-30-integration` |

**Merge order (no retargeting):** #235 (plan 33) into `plan-31-32-integration`, then #233 into `plan-28-30-integration` → #224
into `plan-24-26-27-integration` → #195 into `main`. Each merge just grows
the next PR. `main` takes one merge. Then close #230, #232, #204, #205.

## Things that are not hand checks

- [ ] **Both Macs on the merged build** before anyone saves a preset from it: `/3` (sequencer) and `/4` (media) presets are refused by older builds, and a plan-32-only build would drop a sequencer pattern from a `/4` file.
- [ ] **Plan 33 (#235): both Macs on the build with the free graph** before anyone saves a branch, a switch or an unwired node: that saves `hyperspace.preset/5`, which an older build refuses. Presets that need nothing new save as before, byte for byte. The 661 goldens before the plan are unmoved (693 now); the gate Mac re-runs them.
- [ ] **Plan 35 (#236): both Macs on the build with the wired frame** before anyone saves a preset that needs the new vocabulary (a window set to "nothing", hands through the effects, an edit off the migrated shape): that saves `hyperspace.preset/6`, which a plan 33/34 build refuses. Untouched `/4` presets save byte for byte and `/5` ones where they round-trip. The 717 goldens before the plan are unmoved (741 now); the gate Mac re-runs them. Plan 34 T4–T6 resume on this model.
- [ ] `uv sync` on each Mac (new deps: `av`, `pillow-heif`, `syphon-python[opengl]`, `cyndilib`, `pyobjc-framework-avfoundation`).
- [ ] **Dillon: #223 venues vs `[[devices]]`** — decide whether a venue may set devices (proposal: no; the overlay drops them with a note). Resolution notes for #223 and #214 against this stack: [`assets/32-media/merge-dillon-214-223.md`](assets/32-media/merge-dillon-214-223.md). #223 also needs its register rows 110/111, check 144 and guide L69 renumbered (taken on the stack).
- [ ] Dillon's #214 and #223 are into `main`; after #195 lands they rebase onto it (one superficial hunk for #214; superficial hunks + the devices question for #223).
- [ ] Optional: the compositing-order reconciliation session — the backdrop's place in the look-back is a stopgap until then (plan 33 made changing it a graph edit, and kept plan 32's order, row 351).

## Without the hand camera

The synthetic hands tape stands in for the camera:
`uv run python tools/hands_tape.py synth ~/Hyperspace-try/hands-synth.json`,
then in the copy's `config.toml` `[hands]` set `enabled = true` and
`tape = "hands-synth.json"` (relative to the config's folder; remove `tape`
when the camera is back). No real recorded tape is committed yet.

- **On the tape (the guide says so):** 184; 200, 203–207, 209, 210, 213, 214; 223.
- **On the tape, judged (the guide names the camera, but nothing in the check needs a real hand):** 169, 180, 237, 251, 252, 256. Re-run them with the camera if anything looks off.
- **Need the real camera, so wait for it:** 158–165 (the dance sources, grab, hands on the projector), 172 (the tracker reconnecting), 241, 248, 249, 265 (a hand felt, or learned, live). Thirteen in all: eight in #195 (U), one in #195 (W), four in #224 (Y).

## Hand checks

### U. Plan 24: the party fixes
- [ ] **148** The two-handed save, ten times in a row — _copy, APC40_
- [ ] **149** Points, lines, faces and rotate on both layers — _APC40_
- [ ] **150** A load relights the whole desk — _APC40_
- [ ] **151** The desk log says what a press did — _APC40_
- [ ] **152** Faders on the preset layer: a preset's rows and a learned one — _copy, APC40_
- [ ] **153** The audio strip under SHIFT; faders pick up across the latch — _copy, APC40_
- [ ] **154** Lines and points opacity
- [ ] **155** The coverage report against what you see as dark
- [ ] **156** A desk template and a preset that names it — _copy_
- [ ] **157** Click a control: this preset's params first
- [ ] **158** The dance sources on the HANDS page and in ROUTING — _hand camera_
- [ ] **159** Curl and energy, learned onto params — _copy, hand camera_
- [ ] **160** Spread — _hand camera_
- [ ] **161** Flick — _hand camera_
- [ ] **162** Gap and twist — _hand camera_
- [ ] **163** The grab switch — _hand camera_
- [ ] **164** Grab to steer the shape — _copy, hand camera_
- [ ] **165** Hands on the projector at the rig — _projector, hand camera_
- [ ] **166** The palette fold on a fader — _APC40 for the fader; the rest on the laptop_
- [ ] **167** A saved palette, and the palette's strip — _copy_

### W. Plan 27: the device registry
- [ ] **168** The SYSTEM page lists every device, and an un-renamed config says so — _copy_
- [ ] **169** A hands entry carries the hands setup — _copy, hand camera_
- [ ] **170** A device that raises does not take the frame down — _copy_
- [ ] **171** ⌘R with the USB pad — _pad_
- [ ] **172** A device whose open failed is retried; a tracker comes back on its own — _copy, hand camera_
- [ ] **173** Editing `[[devices]]` lands without a relaunch; a bad edit does not — _copy_
- [ ] **174** A second hands device is refused, and comes up when the first leaves; a second pad opens — _copy_
- [ ] **175** The APC40 plugged in after launch lights up — _APC40_
- [ ] **176** A second controller maps on Learn desk with no code — _copy, APC40, a second USB MIDI controller_
- [ ] **177** SHIFT is the APC40's; the second desk keeps its layer — _copy, APC40, the second controller_
- [ ] **178** The pages offer what the rig lists — _copy_
- [ ] **179** The sticks still steer; a routed stick does not — _pad_
- [ ] **180** The hands on the registry — _copy, hand camera_
- [ ] **181** A param's effective value goes out on the bridge — _copy, FL Studio or MIDI Monitor, IAC_
- [ ] **182** The bridge's `send` list becomes rows once, seen in the DAW — _copy, FL Studio, IAC_
- [ ] **183** Learn sink never asks Replace / Keep — _copy_
- [ ] **184** The hands' DAW out works as before, from the `hands-daw` sink — _copy, hand camera or a tape, FL Studio_
- [ ] **185** `[hands] out` on a list, and an explicit `midi-out` — _copy_
- [ ] **186** A phone's fader drives a param, with no code — _copy, a phone on the same Wi-Fi_
- [ ] **187** A phone's button fires a row — _copy, the phone_
- [ ] **188** A silence reads `lost`; the faders keep their place — _copy, the phone_
- [ ] **189** A busy port is a line, not a crash, and comes up when it frees — _copy, the phone_
- [ ] **190** The recorded cloud plays at its own rate — _copy_
- [ ] **219** Two pads at once: the Xbox pad over Bluetooth and the wired Afterglow over USB — _copy, both pads_

### V. Plan 26: the render graph
- [ ] **191** The golden frames match on the gate Mac
- [ ] **192** Every factory preset against its golden, by eye, on the Mac
- [ ] **193** The naming rule
- [ ] **194** The per-node times on SYSTEM while an effect is toggled
- [ ] **195** Every picture is what it was before the graph
- [ ] **196** The shape sits where it always did; the eye on CAMERA
- [ ] **197** Zoom grows the shape in the world; the hands stay
- [ ] **198** Screen strokes: world space by default, the switch holds the weight
- [ ] **199** A hand across the box pans as far as it did (`hands-orbit`)
- [ ] **200** `hands-orbit` turns only the shape; the hands stay put
- [ ] **201** A preset saved before plan 26 with a pan looks the same on the projector — _copy_
- [ ] **202** `hands.json` gains the calibration and keeps the old file — _copy_
- [ ] **203** The hands are where the performer is (the calibration)
- [ ] **204** Hands inside the scene are solid — _copy_
- [ ] **205** A hand passes between the shape's edges — _copy_
- [ ] **206** The hands in the scene on the projector and a clean layer on the glass, at once — _copy, glass and projector_
- [ ] **207** A separate hands layer goes behind the shape (depth-aware) — _copy_
- [ ] **208** The OUTPUT switches still mean what they meant
- [ ] **209** The history can hold the hands — _copy_
- [ ] **210** The hands' own line on SYSTEM — _copy_
- [ ] **211** A preset says its graph in data — _copy_
- [ ] **212** Two acids in one chain — _copy_
- [ ] **213** Two hands nodes: one in the scene, one over the glass — _copy, glass and projector_
- [ ] **214** Hands as lines — _copy_
- [ ] **215** The wiring in words — _copy_
- [ ] **216** The recorded cloud in the scene, in the shape's world — _copy_
- [ ] **217** The cloud's look — _copy_
- [ ] **218** No cloud, no change; the cloud's cost on SYSTEM — _copy_

### X. Plan 30: shader nodes
- [ ] **220** SYSTEM times each effect that ran
- [ ] **221** Switching effects on and off changes nothing but the picture
- [ ] **222** Two outputs and the hands through still get their own chains
- [ ] **223** The palette folds the hands and not the shape (palette-hands) — _copy_
- [ ] **224** One output folds (palette-glass) — _copy, glass and projector_
- [ ] **225** A placement this build cannot honour is a note — _copy_
- [ ] **226** A dormant placement says so — _copy_
- [ ] **227** The echoes hold the bent scene (acid-scene) — _copy, projector_
- [ ] **228** The placements in words — _copy_
- [ ] **229** The FX page's placed chip — _copy_
- [ ] **230** The faces target still bends the faces
- [ ] **231** Two palettes with different slices on two outputs — _copy, glass and projector_
- [ ] **267** The whole picture as shades of one red — _projector_
- [ ] **268** A yellow slice and its derivations — _projector_
- [ ] **269** A slice through red, and an inverted brightness — _projector_
- [ ] **270** The mode is a picker; the strip reads as the slice — _laptop_
- [ ] **271** An old preset with centre and width loads as the same look — _copy_

### Y. Plan 28: the node editor
- [ ] **232** The lag is gone on a real LFO-on-LFO patch
- [ ] **233** A loop is refused in words; the rest of the preset runs
- [ ] **234** A delay closes a loop
- [ ] **235** Every LFO still runs with nothing routed
- [ ] **236** Each modifier kind does what its name says
- [ ] **237** A modifier whose input goes away lets its routes go; a removed one leaves them dormant — _hand camera_
- [ ] **238** A preset holds its modifiers; `bindings.json` never does — _copy_
- [ ] **239** A template's modifier reaches every preset that uses it — _copy_
- [ ] **240** Modifier edits are undo steps
- [ ] **241** "Right hand energy, smoothed, times band 0, into acid mix" from the modifiers' editors — _hand camera, music_
- [ ] **242** The GRAPH page shows one table
- [ ] **243** Params sit under their render nodes
- [ ] **244** Layout and tidy — _copy_
- [ ] **245** Hover and selection
- [ ] **246** Quit, ⌘R and a hot reload with GRAPH open
- [ ] **247** A cable dragged on the laptop screen at the control window's size
- [ ] **248** Learn from a port, with the APC40 and with a hand — _APC40, hand camera_
- [ ] **249** The hand-energy patch built on the canvas, felt with a real hand — _hand camera, music_
- [ ] **250** Deleting on the canvas
- [ ] **251** "Hands as lines through the acid with tracers", by dragging, on the projector — _projector, hand camera, copy_
- [ ] **252** A hands node wired to the glass alone — _glass, projector, hand camera, copy_
- [ ] **253** A wrong cable is refused in words — _copy for step 3_
- [ ] **254** Two outputs, two pictures (wired-outputs) — _glass, projector, copy_
- [ ] **255** The picker and delete for render nodes
- [ ] **256** The APC40 as two nodes, SHIFT latched and released — _APC40, hand camera_
- [ ] **257** A templated desk on the canvas — _copy_
- [ ] **258** A SHIFT-layer cable is the session's; a preset-layer one the preset's; a missing role — _APC40, copy_
- [ ] **259** A patch saved on one Mac loads on the other through the shared library — _two Macs, a shared folder_
- [ ] **260** A preset from before this run loads with no note — _copy_
- [ ] **261** The collapsed graph on party-trip reads at a glance — _laptop, APC40_
- [ ] **262** Expand the APC40 and the shape: the real cables — _laptop, APC40_
- [ ] **263** A drag onto a collapsed node lands a route — _laptop_
- [ ] **264** Tidy says what it did; the details chip — _laptop_
- [ ] **265** Energy → smooth → combine → acid mix, from GRAPH alone, with a hand — _hand camera, laptop; copy_
- [ ] **266** ROUTING points to GRAPH; its desk section as before — _APC40_
- [ ] **272** The three concern areas at a glance on party-trip — _laptop, APC40_
- [ ] **273** An idle macro appears when patched and goes when unpatched — _laptop_
- [ ] **274** Tidy lays out into the areas — _laptop_
- [ ] **275** The off effects are one line; the chain reads through them — _laptop_
- [ ] **276** Five chips frame the areas; the shaders in rows of four — _laptop_

### Z. The instanced field (from `main`); plan 31: the step sequencer
- [ ] **277** Four thousand copies hold the frame rate
- [ ] **278** Fit leaves no copy cut by the edge
- [ ] **279** The lattices read as 3D
- [ ] **280** The LFO page at 7 and at 16 LFOs — _laptop_
- [ ] **281** The SEQ page reads from a distance — _laptop_
- [ ] **282** `seq-demo` feels tight at 120–175 BPM — _laptop, music, a projector helps_
- [ ] **283** The global trigger re-aligns the grid; restart does not move the LFOs — _laptop_
- [ ] **284** GRAPH's lane cables — _laptop_
- [ ] **285** A `/3` preset between two Macs — _two Macs, the copy_
- [ ] **286** SEND A enters and redraws; leaving restores the bank, SAVE and the toggles — _APC40, the copy_
- [ ] **287** Yellow over green is legible — _APC40_
- [ ] **288** No flicker as the playhead runs — _APC40_
- [ ] **289** Clip stop is the playhead and the length — _APC40_
- [ ] **290** Scene select and the mute blink — _APC40_
- [ ] **291** A bank pad held across SEND A does not save — _APC40, the copy_
- [ ] **292** SHIFT inside the page — _APC40_
- [ ] **293** QUANT loads a preset with the page up — _APC40_
- [ ] **294** A power cycle re-sends the page — _APC40_
- [ ] **295** SEND A in a desk fallen back to Generic mode — _APC40_

### AA. Plan 32: media (channels, the media folder, live feeds, publishing out)
- [ ] **296** A still as a backdrop — _laptop_
- [ ] **297** The faces and `aux` — _laptop_
- [ ] **298** A video: rate, scrub, loop, the proxy — _laptop_
- [ ] **299** Jog with the cue knob — _APC40_
- [ ] **300** A dropped file appears — _laptop; the cloud for the second half_
- [ ] **301** The missing-local banner; both Macs on `/4` — _two Macs_
- [ ] **302** Junk, mid-show deletes and rapid switching — _laptop_
- [ ] **303** The MEDIA page at distance, and a big library — _laptop_
- [ ] **304** Syphon in — _laptop, a Syphon app_
- [ ] **305** NDI in from Resolume — _laptop, Resolume, same router_
- [ ] **306** NDI in from TouchDesigner on a second Mac — _two Macs_
- [ ] **307** `extra_ips` — _two networks_
- [ ] **308** Syphon out into Resolume — _laptop, Resolume_
- [ ] **309** NDI out into Resolume and TouchDesigner — _laptop, both_
- [ ] **310** A publish-only output; a window resized — _projector or a second screen_
- [ ] **311** A webcam; the dependencies — _laptop_
- [ ] **312** The phone, through an NDI camera app — _a phone, same Wi-Fi_
- [ ] **313** A feed vanishes and comes back — _laptop, any live source_
- [ ] **314** An old bitmap preset; knob 7 — _laptop, the copy; APC40 for the knob_
- [ ] **315** A frozen Syphon channel
- [ ] **316** A camera without a 1280×720 mode

### AB. Plans 31 and 32 together
- [ ] **317** A preset with a pattern and a bin, saved and reloaded on the merged build — _laptop, the copy, a picture; a second Mac for the last step_

### AC. Plan 33: the free graph
- [ ] **318** The headline graph: a clip through two effects onto the faces, the camera through `kaleido` behind the scene — _laptop, the copy, a clip, a camera_
- [ ] **319** A switch over three channels on an APC40 knob, into the faces — _APC40, the copy_
- [ ] **320** Reordering the run by dragging — _laptop, the copy_
- [ ] **321** The FX page finds and plays an effect on a branch — _laptop, the copy_
- [ ] **322** An old party preset loads and looks the same; saved untouched it opens on the second Mac — _laptop, the copy, a second Mac_
- [ ] **323** A channel on the faces is lost mid-show — _laptop, any live source_
- [ ] **324** The frame cost of two branches, the faces branch and an eight-way switch — _laptop_
- [ ] **325** The near-miss drag — _laptop, the copy_
- [ ] **326** A shader back into the faces on the GRAPH layout — _laptop, the copy_
- [ ] **327** The FX page with a big graph, at arm's length — _laptop_
- [ ] **328** A free graph is refused by an older build — _two Macs, the copy_

### AE. Plan 35: the free frame
- [ ] **342** A new preset: black, the factory's values and desk, a scene starter — _laptop, the copy_
- [ ] **343** The owner's delete sequence on a party preset — _laptop, the copy_
- [ ] **344** A channel alone on All outputs — _laptop, the copy, a clip_
- [ ] **345** A library preset by eye on both Macs, before and after — _laptop, the copy, the other Mac_
- [ ] **346** The OUTPUT page: pick a picture, as All outputs, undo; four outputs at distance — _laptop, the copy; the TV_
- [ ] **347** The glass's picture mute, and the two owner notes (a picture mute hides the through picture; on an in-scene preset it shows the ground and the guide) — _the rig_
- [ ] **348** Hands through the effects on output 2 — _the rig, or the TV_
- [ ] **349** LOOKBACK's records: the backdrop, the scene, nothing — _laptop, the copy_
- [ ] **350** The canvas at distance — _laptop, the copy_
- [ ] **351** SYSTEM before and after on the party preset — _laptop, then the rig_
- [ ] **352** A `/6` preset on a plan 33/34 build; both Macs on this build — _two Macs, the copy_
