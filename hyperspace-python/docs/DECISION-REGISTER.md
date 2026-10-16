# Decision register — the open decisions

Rows 34–88 were each decided during an unattended build on 2026-10-04,
rows 89–108 during plan 22's run on 2026-10-06, rows 110–139 during
plan 24's run, rows 140–168 during plan 27's run and rows 169–209
during plan 26's run on 2026-10-14, rows 210–213 during plan 27's B6
(several gamepads at once) on 2026-10-15: the build took its own
recommendation and built it. Every one is in the app now (rows 110–213
on `plan-24-26-27-integration`, until the owner merges it) and waits
for the
owner to say **keep** or **overturn**. Row 109 is the owner's own (plan
25). Each row
says what was built (what you will see or feel), the other option(s), what
it costs to reverse, the known rough edge, and the hand check that lets you
judge it. The checks are numbered in
[`plans/11-hand-checks.md`](plans/11-hand-checks.md); the same checks in
plain words, by hardware, are in [`TESTING-GUIDE.md`](TESTING-GUIDE.md)
(each entry ends with its check numbers). None has been run by a person.

Decisions already settled, and these rows once kept, are in
[`DECISIONS.md`](DECISIONS.md); a row there marked "row N" points here.
When you answer a row: keep → mark it "owner" in DECISIONS and delete it
here; overturn → the change, then the same.

## Answer sheet

| # | Decision | Check | Keep / overturn |
|---|---|---|---|
| 34 | Undo on ⌘Z and Ctrl+Z; exact chords | 48 | |
| 35 | Band add / remove / move not undoable | — | |
| 36 | Taps and BPM are not undo steps | — | |
| 37 | Trash only when the file changes | 53, 88 | |
| 38 | Home is the Home key only | 54 | |
| 39 | Camera moves are undo steps | — | |
| 40 | Home may be fired by a performer; dim may not | 54, 55 | |
| 41 | The dim in overlay fades alpha too | — | |
| 42 | Save-as hold: how it fires and lights — the clip-stop bar **superseded** (#158; clip stop 8 is SAVE, row 110) | 56 | superseded in part |
| 43 | A paused drag is two undo steps | 48 | |
| 44 | A load releases only faders it moved — for the preset's faders **superseded by row 112** | 55 | superseded in part |
| 45 | FX chip: dot switches, name opens; three a row | 59 | |
| 46 | An idle effect's faders dimmed but live | 60 | |
| 47 | Instances reach zero from slider and K3 | 62 | |
| 48 | Where the windows open | 61 | |
| 49 | The dream's layer cannot be performed | 63 | |
| 50 | The interaction box: set by the sweep | 72–74 | |
| 51 | A hand outside the box is absent everywhere | 73, 74 | |
| 52 | A hand Learn lands as a gentle push | 75, 76 | |
| 53 | A hand Learn moves the axis's other rows | 77 | |
| 54 | Knob smoothing on at 80 ms | 78, 79 | |
| 55 | Where knob smoothing and Learn depth live | 75, 78 | |
| 56 | `hands-orbit`: two hands on the camera | 80 | |
| 57 | The big on-screen desk and its names | 69 | |
| 58 | Click a desk control, then a param | 70 | |
| 59 | One Unbind removes desk rows and routes | 64 | |
| 60 | "Learn desk" and "Learn hand ▸ left / right" (what it waits for comes from the device registry since plan 27: rows 151, 158) | 66–68 | |
| 61 | Session controls work through a desk learn (its list changed in plan 24: S1–S8 left it; SAVE and the four toggles joined) | 65 | |
| 62 | One road onto the desk, no APC40 needed | 70 | |
| 63 | The ROUTING filter: only you clear it | 71 | |
| 64 | Two hand-Learn details left alone | 66 | |
| 65 | The faces' effect picture: what, size, fit | 91–93, 98 | |
| 66 | Performers on effect target and face mapping | 91 | |
| 67 | The chip grid is the chain; drag to reorder | 94 | |
| 68 | Re-aim an effect by the strip's combo | 91, 94 | |
| 69 | LOOKBACK as ECHOES / DREAM / BOTH; every layer in one menu | 95 | |
| 70 | Dream "speed" is `dream.k`, in frames | 96 | |
| 71 | Instance layouts: grid, honeycomb, ring | 97 | |
| 72 | The bank of twenty-four | 81, 83 | |
| 73 | Clip rows 4–5 are the bank; their lights (its diagram's clip-stop row and toggle column are out of date: rows 110, 113) | 82–84 | |
| 74 | No backup, no rewrite of `bindings.json` | 84, 57 | |
| 75 | Device knobs only where they do something | 85 | |
| 76 | Hide, rename and the trash | 86–88 | |
| 77 | The red dot and "save copy" | 89 | |
| 78 | The home in git — **superseded by row 109** (removed in plan 25) | 90 | superseded |
| 79 | Where "hands through effects" puts the hands — **superseded in part by rows 193, 194** (plan 26: the switches are the default graph's wiring; the history is wiring) | 102, 103 | superseded in part |
| 80 | The guide and labels are never bent | 103 | |
| 81 | Output switches are rig settings | 101, 104 | |
| 82 | Another shape is letterboxed | 106 | |
| 83 | One window renders, others copy | 107 | |
| 84 | Ghost hands and each output's hands tick | 102, 105 | |
| 85 | The OUTPUT page says it in words | 102, 105 | |
| 86 | A screen not connected at launch | 101, 111, 112 | |
| 87 | `ghost.style`: five drawn objects | 109 | |
| 88 | Ghost mirror / guide / tethers not performable | 110 | |
| 89 | The Heart masked; the other shapes lifted | 113, 114 | |
| 90 | The W fold at draw time: XW → XZ, YW → YZ, ZW → XY | 114 | |
| 91 | A masked shape cues depth on z | 114 | |
| 92 | `VOLUME_FLOOR` 0.15, from all 18 4D shapes | 113, 119 | |
| 93 | How a shape is lifted: the lift rules | 113, 115 | |
| 94 | The Möbius strip widened and lifted | 115, 118 | |
| 95 | The Rose deepened and lifted (the orchestrator's call) | 115 | |
| 96 | The Klein bottle: the bottle, lifted, shape 26 | 116, 117 | |
| 97 | A bent cap framed by its least-squares plane | 115 | |
| 98 | The eight pattern inputs: their meanings and order | 122, 124, 125 | |
| 99 | SPEED is an integrated clock | 123 | |
| 100 | WARP / SPREAD inert from 0 to 1; GLOW's 30% floor | 122, 137, 138 | |
| 101 | Fixed counts: seven petals, five arms, six wedges | 122, 131 | |
| 102 | The FACES page as a browser of swatch chips | 120, 125, 126, 128 | |
| 103 | "+ SUB": the convention's source offered on an idle input | 127 | |
| 104 | METER and PULSE read the bands (`u_levels`) | 129 | |
| 105 | Five new patterns; the old twelve's art unchanged | 129–131 | |
| 106 | Pattern routes at depth 0.35; `legacy6` drops pattern parity (the orchestrator's call) | 132, 137 | |
| 107 | The house presets' routes generated from code | 132 | |
| 108 | Macro candidates in `shared/` (folder **superseded by row 109**); per-band gain as depth | 133–136 | |
| 109 | Plan 25: presets shared through a cloud-synced folder (`[library] path`), D1–D8 | 139–143 | **owner, 2026-10-14** |
| 110 | SAVE is track 8's clip stop, held, on `desk.save` | 148 | |
| 111 | The two-handed save names from the loaded preset; the pad blinks | 148 | |
| 112 | A load lets go of every preset fader and darkens the whole desk (row 44 changed) | 150, 153 | |
| 113 | Factory files keep the toggle rows; a load drops them quietly | 149 | |
| 114 | The desk log: the last twenty presses on SYSTEM | 151 | |
| 115 | The band audio strip on the SHIFT-layer faders (amends D6) | 153 | |
| 116 | A layer switch re-arms every layered fader from where it is | 153 | |
| 117 | `view.lines_alpha` and `view.points_alpha` | 154 | |
| 118 | Fader rows in a preset's desk: `track_fader`, `knob_desk(faders=)` | 152 | |
| 119 | An older `bindings.json` moves the fader rows to SHIFT once | 153 | |
| 120 | What makes a desk control "dead" (`learn.cannot_show`) | 155 | |
| 121 | The coverage counts 38 preset-layer controls | 155 | |
| 122 | Desk templates: the file format, overrides and dark rows | 156 | |
| 123 | Click a control: this preset's params first, in four tiers | 157 | |
| 124 | The dance lanes after the switches; `hands:` its own scheme | 158, 162 | |
| 125 | Curl and spread: what they measure | 159, 160 | |
| 126 | Energy: mean speed, fast up, slow down | 159 | |
| 127 | Flick: a spike past 1500 mm/s that decays | 161 | |
| 128 | Gap and twist | 162 | |
| 129 | The dance sources and the grab: no settings, no DAW, no hand Learn | 158, 164 | |
| 130 | The dance column and the grab glyph on the HANDS page | 158, 163 | |
| 131 | The grab: mean curl, closes past 0.65, opens under 0.45 | 163, 164 | |
| 132 | The grab lanes after the dance lanes; gates after the pinches | 163 | |
| 133 | Hands on the projector: the SETUP.md line, not the home's file | 165 | |
| 134 | The palette's ids are `fx.palette.*` | 166 | |
| 135 | The `@mix` directive; the palette starts at mix 0 | 166 | |
| 136 | The palette's params: mode, anchors, twelve anchor values | 166, 167 | |
| 137 | The palette at `@order 95` | — | |
| 138 | The fold over the absolute hue wheel; linear sat and val | 166 | |
| 139 | The FX page repacked; strip rows packed by name | 167 | |
| 140 | `[[devices]]`; the old tables translated with a note each | 168, 169 | |
| 141 | Today's devices keep their schemes; two never feed one Router key (since B6: a second pad opens under its role, rows 210–213; a second hands device is still refused) | 174, 219 | |
| 142 | The `Device` protocol, one `Port`, four status words | 170 | |
| 143 | The devices own today's adapters; the hands read in the feed slot | 168, 180 | |
| 144 | Open behind the entry, retry a failed open, close last-listed-first | 170–172, 175 | |
| 145 | `config.toml` watched every 30 frames; a bad edit keeps the old list | 173 | |
| 146 | The SYSTEM page: one line per device | 168 | |
| 147 | A second desk's rows are `cc@<role>:…`; who owns the unqualified rows | 176, 177 | |
| 148 | SHIFT is the first desk's; other desks have their own layer, no SHIFT | 177 | |
| 149 | The `generic` MIDI profile | 176 | |
| 150 | Continuous = not a row kind; schemes and their order from the registry | 178 | |
| 151 | What a Learn waits for is each device's `wants` | 178, 186 | |
| 152 | The pad is a device; it runs the sticks' camera job | 179 | |
| 153 | The hands' device in `hands/device.py` | 180 | |
| 154 | One knob per param per desk | 176 | |
| 155 | The sink row: `param:<id>` / `lane:<i>` → `<role>:<channel>`, the session's | 181, 183 | |
| 156 | `[bridge] send` becomes sink rows once (`sinks_seeded`) | 182 | |
| 157 | The hands' DAW out is the `hands-daw` sink | 184, 185 | |
| 158 | Learn sink ▸ lands at once, in the session | 183 | |
| 159 | The bridge in two halves; `ext` labels and rests | 181, 182 | |
| 160 | A sink's line says `n sinks` | 182, 184 | |
| 161 | An OSC role is its scheme; hits are rows under it | 186, 187 | |
| 162 | OSC values: first number, range, NaN until heard, held while lost | 188 | |
| 163 | OSC hits: velocity is the first number | 187 | |
| 164 | The OSC socket read in `poll`; UDP 0.0.0.0:9000 | 186, 189 | |
| 165 | `devices.PointCloud` | 190, 216 | |
| 166 | Clouds on the registry, not the Router (drawn by plan 26's `cloud` node, rows 204–209) | 190, 216 | |
| 167 | The cloud file: version-1 `.npz` | 190 | |
| 168 | The cloud device plays at its own rate | 190 | |
| 169 | The instance marker: a number after the prefix (`fx.acid.2.mix`) | 193 | |
| 170 | Goldens: eight output states as eight outputs of one frame, and output 1 alone | 191, 192 | |
| 171 | LFOs and analyzer at rest in the goldens | 191 | |
| 172 | "Hands present" in the goldens: one fixed pose, the ghost on | 191 | |
| 173 | The 1080p-cap golden: party-trip at 2× HiDPI | 191 | |
| 174 | GPU time per node: read 3 frames late, a median of 60 | 194 | |
| 175 | The golden tool's one GL context | 191 | |
| 176 | The FX node is the chain, one per pipeline, the pipeline's end | 194 | |
| 177 | The history as two nodes, `history` and `capture` | 194 | |
| 178 | The Output node is `_compose` | 194, 195 | |
| 179 | Nodes and ports: made images pulled, painted images drawn into the consumer | 194 | |
| 180 | The default graph keyed by switches, wiring and clouds; reused | 194, 195 | |
| 181 | The cover mask as a Layer node | 194 | |
| 182 | The eye: `eye.fov`, `eye.distance`, session, the old divide | 196 | |
| 183 | `camera.pan` in world units (±12), marked by `units`, through 1080p | 199, 201 | |
| 184 | `camera.zoom` the shape's world scale; copies in the world (its stroke sentence superseded by row 189) | 197 | |
| 185 | The shape's depth: never against itself; alpha > 0.25 written after | 205 | |
| 186 | Point quads a whole number of pixels | 196 | |
| 187 | The Leap calibration: `units` in `hands.json` /3, a 16:9 fit | 202, 203 | |
| 188 | A stroke end behind the eye is slid in front | 197 | |
| 189 | Strokes in world space by default; screen space the switch (the toggle is the owner's) | 198 | |
| 190 | `view.screen_strokes`: a performance toggle, modulatable | 198 | |
| 191 | Hands inside the scene are solid (`ghost.alpha` not applied) | 204, 205 | |
| 192 | The depth-aware composite: a 0.05-radius bias | 207 | |
| 193 | The OUTPUT switches are wiring; through stands down per frame | 195, 208 | |
| 194 | `Wiring`: hands, blend, history — renderer-wide | 206, 209 | |
| 195 | The hands node `ghost` and its layer `hands`; time by the consumer edge | 210, 213 | |
| 196 | The preset's `graph` section: the nodes that differ, one object each | 211 | |
| 197 | An unreadable section: a note, the default graph, kept as written; `cloud` unknown | 211 | |
| 198 | Instances as built: `fx.<file>.<n>`, `ghost.<n>`, `hands.<n>` | 212, 213 | |
| 199 | A second hands node is its own `Ghost` over its own state | 213 | |
| 200 | Where two hands nodes go | 213 | |
| 201 | Hands as lines: the meshes' edges | 214 | |
| 202 | The OUTPUT and LOOKBACK pages say the wiring in words | 215 | |
| 203 | Undoing a load puts the graph back first | 211 | |
| 204 | A point cloud is solid geometry in the scene | 216 | |
| 205 | The cloud's transform: one scale, `cloud.scale` 0.3 | 216 | |
| 206 | `cloud.*` a session group | 217 | |
| 207 | A listed `cloud` device adds its node to the scene | 216, 218 | |
| 208 | The cloud buffer uploaded on a new (frame, time) | 218 | |
| 209 | The cloud's draw is its own SYSTEM line | 218 | |
| 210 | The device qualifier is general: any scheme takes `@<role>`; an unqualified row is the primary device's | 219 | |
| 211 | A joystick per pad device (next free, or pinned); one USB reader, the first `usb = true` entry's | 219 | |
| 212 | The camera job and the factory pad rows are the primary pad's; a second pad starts with no rows; one feel | 219 | |
| 213 | The hands stay single: a second hands entry is refused | 174 | |

"—": no hand check shows it; tests only.

---

## Undo, home, the dim, save-as

### 34. Undo on ⌘Z and Ctrl+Z; a key fires only its exact chord

- **Built.** ⌘Z and Ctrl+Z undo; adding ⇧ redoes. A key press fires only
  the row whose modifiers are exactly the ones held, so ⌘⇧Z redoes and
  does not also undo.
- **Other options.** ⌘Z only (Ctrl+Z does nothing); Ctrl+Z only (wrong for
  Mac hands).
- **To reverse.** Delete two rows in `routing.LOOP_KEY_ROWS`: minutes. The
  exact-chord rule is needed by redo under any option.
- **Rough edge.** A row you made by hand on a bare key (`key:Z`) no longer
  fires while ⇧, ⌘ or Ctrl is held. No factory row is affected.
- **Judge it.** Check 48.

### 35. Adding, removing or moving a band is not an undo step

- **Built.** ⌘Z after adding a band does not remove it. Each undo step
  remembers the band layout it was made on; strip values go back only onto
  that same layout. When a step's strip values are skipped, the footer
  says "the bands have changed: their strips were left". A band preset
  load, a show load and a scene pick undo whole. The 8-second "Reset all"
  undo is unchanged.
- **Other options.** Make add / remove / move undo steps (about a day,
  builds on this); clear the whole history on a layout change.
- **To reverse.** About a day for full undo of layout changes.
- **Judge it.** No check; tests only.

### 36. A tap, a nudge or a typed BPM is not an undo step

- **Built.** The tempo group is not watched by undo, so tapping never fills
  the history, and undoing a show load leaves the tempo where it is.
- **Other option.** Watch the BPM: each tap of a burst becomes a step.
- **To reverse.** One line (`undo.EXCLUDED_GROUPS`).
- **Judge it.** No check; tests only.

### 37. A preset goes to the trash only when the file would change

- **Built.** Saving or deleting a preset first copies the old file to
  `~/Hyperspace/trash/presets/<name>.<date>-<time>.json` (a module preset
  to its own folder there), but only when the text would actually change.
  If the copy fails (a full disk), a save warns and goes on; a delete is
  refused.
- **Other options.** Trash on every save (identical copies pile up); a
  failed copy also refuses the save.
- **To reverse.** One condition in `library.to_trash`'s callers.
- **Judge it.** Checks 53 and 88.

### 38. Home is the Home key only (fn ← on a MacBook)

- **Built.** `key:HOME` fires home; the desk's OVERDUB is the other road.
  The row is in `bindings.json` and can be moved to another key there.
- **Other option.** A second key as well (say ⇧H).
- **To reverse.** One row.
- **Rough edge.** Whether fn+← reaches the app as Home has not been tried.
- **Judge it.** Check 54.

### 39. Camera moves are undo steps

- **Built.** R (reset view), a mouse orbit, the sticks, the wheel and ↑ / ↓
  each undo like any setting; one continuous orbit is one step. The
  history holds 100 steps.
- **Other option.** Leave the camera out, so ⌘Z always reaches a "real"
  edit.
- **To reverse.** Add `"camera"` to `undo.EXCLUDED_GROUPS`.
- **Judge it.** No check of its own; any undo check after an orbit.

### 40. A performer may fire home; nothing may drive the master dim

- **Built.** A pinch, band or LFO routed onto `preset.home` fires it, like
  "next preset". The master dim (`output.dim`) cannot be a route's target,
  is never saved and is never moved by a preset or a show. No factory
  preset routes onto home.
- **Other options.** Home not performable; the dim performable (a band
  could strobe the room, a hand leaving the box could black it out).
- **To reverse.** One flag each.
- **Judge it.** Checks 54 and 55.

### 41. In overlay mode the dim fades colour and transparency together

- **Built.** On the normal opaque window the dim scales the colour toward
  black. In overlay mode (only when `config.toml` sets `[output] overlay =
  true`) it also fades the alpha, so the render fades away over the
  desktop.
- **Other option.** Colour only: a dark veil stays over the desktop.
- **To reverse.** One line in `Renderer.dim_pass`.
- **Judge it.** No check: the rig runs with overlay off.

### 42. The save-as hold on the clip-stop row

- **Superseded in part.** The clip-stop SAVE AS bar was retired on
  2026-10-09 (#158: an empty bank pad held saves into it), and since plan
  24 track 8's clip stop is the desk's SAVE (row 110). The `hold` op, its
  bar of lit buttons and the blink stay for a row you learn. Kept here as
  history.
- **Built.** Holding any of the eight clip-stop buttons for 0.6 s saves the
  live look as a new preset ("TRIP" → "TRIP 2") into the next empty bank
  slot, while you are still holding. The eight act as one bar: two fingers
  save once. The bar is dark at rest, lit while held, and blinks for
  1.5 s with the new slot's pad when it saves. A new name never matches a
  file, a listed name or a bank entry. The new preset becomes the loaded
  one, so panel Save then writes it. With the bank full the preset still
  saves, to the list, and the footer says so. A save that fails blinks
  nothing.
- **Other options.** Fire on release; the bar lit at rest; stay on the old
  preset after saving; a per-row hold time.
- **To reverse.** Each is a line or a constant (`midi.HOLD_S`, the rows'
  "off" velocity).
- **Rough edge.** The on-screen desk lights the bar while held but does not
  blink. The hold, lights and blink have never been on the APC40.
- **Judge it.** Check 56.

```
 clip row 1     [ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ]   bank slots 1–8
 clip rows 4–5  slots 9–16 and 17–24 (row 73)
 clip stop      [========== SAVE AS: hold 0.6 s ==========]  [STOP ALL: reset all]
                a NEW preset → the next empty slot, whose pad blinks; a tap: nothing
```

### 43. A slider drag that pauses is two undo steps

- **Built.** An undo step ends after 0.4 s in which nothing you set has
  changed. A drag held still longer than that, then moved again, is two
  steps. One rule for the panel, the desk, keys and typed values.
- **Other option.** Hold the step open while a panel widget is dragged
  (the desk's knobs gain nothing).
- **To reverse.** One flag the panel sets; the quiet time is one constant
  (`undo.SETTLE_S`; knob smoothing must stay under it).
- **Judge it.** Check 48 (does 0.4 s feel right).

### 44. A preset load releases only the faders whose parameter it moved

- **Superseded in part by row 112** (plan 24): a fader the new preset
  binds now always lets go on a load. The session's faders — the
  crossfader, MASTER, and the band strip under SHIFT — keep this rule.
- **Built.** A fader "has" its parameter once moved onto its value (soft
  pickup). A preset load makes a fader let go only if the load moved its
  parameter, the parameter is gone, the fader has never been moved, or
  another control moved the parameter since. So the crossfader's dim, the
  band faders and the master fader carry straight on through a load. A
  fader moved while its row is switched off, or while a Learn took its
  message, picks up again from where it is.
- **Other options.** Every fader lets go on every load (the crossfader
  sometimes dead after a load); the crossfader with no pickup (one parked
  at the left blacks the rig out).
- **To reverse.** One condition in `MidiIO.redraw`.
- **Judge it.** Check 55 (e).

## Effects, windows, instances

### 45. An effect chip: the dot switches, the name opens; three chips a row

- **Built.** On the FX page each chip has a dot at its left end that
  switches the effect on or off (● on, ○ off; a diamond when the effect is
  aimed at the faces), and a name that opens its faders without switching
  it. The open chip has a white outline. Chips sit three to a row so every
  name fits. The open effect is remembered by name, so a reorder or a load
  never opens a different one.
- **Other options.** No switch on the chip, only the strip's "on" box;
  click opens and ⇧click switches.
- **To reverse.** Remove the dot (about a dozen lines in `ui_fx._chip`);
  four a row is one constant (`ui_fx.CHIPS_PER_ROW`).
- **Rough edge.** The dot is small; nobody has tried it with a trackpad.
- **Judge it.** Check 59.

### 46. An effect that is not running: its faders dimmed but live

- **Built.** The open effect says why it is idle ("off" with a **turn on**
  button, the stack bypassed with **effects on**, FX mix at 0, its own mix
  at 0). Its faders sit under a veil but still move and still offer
  right-click → Learn. The "on" box, and the mix fader when the mix is the
  reason, are not dimmed.
- **Other option.** Disabled: greyed and dead, no Learn on an off effect.
- **To reverse.** A few lines in `ui_fx.page`; the strength is
  `ui_fx.IDLE_ALPHA`.
- **Judge it.** Check 60.

### 47. The instance count reaches zero from the slider and K3

- **Built.** `view.instances` runs 0–100. At 0 the readout says "0 ·
  nothing drawn"; the ground, the echoes, the effects, the ghost hands and
  the dim carry on. The slider's left end and the bottom of track knob K3
  are zero. ⌘Z brings the count back. No factory preset, desk value or
  hand route lands on zero.
- **Other options.** Stop the slider and knob at 1 (zero only by preset or
  typing); a separate "blank" switch.
- **To reverse.** Two lines (the range's floor and the renderer's clamp);
  a preset saved at 0 would then load as 1.
- **Rough edge.** A route of yours that pushes both ways on the count (an
  LFO) can now blank the scene for half its cycle.
- **Judge it.** Check 62.

### 48. Where the windows open

- **Built.** The app remembers both windows' places in
  `~/Hyperspace/windows.json`, written on quit and on ⌘R only. A screen
  number in `config.toml` (`[output] monitor`, `control_monitor`) wins over
  the file. Fullscreen is never remembered (`[output] fullscreen` says).
  A first launch opens at full size: render top-left, controls flush
  right. A remembered spot that is not on a connected screen falls back to
  the default spot with a note. Delete `windows.json` to forget.
- **Other options.** The file beats the config; write the file while
  running (survives a crash); remember fullscreen; fit a first launch to a
  small screen.
- **To reverse.** Each is a branch or a line in `placement.place`,
  `placement.default_rect` or the frame loop.
- **Rough edge.** A configured screen number with no screen at launch is
  ignored for the whole run (audit P6). Never run with a second screen.
- **Judge it.** Check 61.

### 49. The dream's layer cannot be performed

- **Built.** `dream.layer` (which net layer the dream works on) is not a
  route target, like "Echo time apart" and "Look-back detail": changing it
  reloads part of the net. A preset, a key, the page's menu and a learned
  knob or button still set it. A saved preset's route onto it is dropped
  at load with a note.
- **Other option.** Leave it performable: a band on it reloads the net on
  every swing.
- **To reverse.** One flag in `params.py`.
- **Judge it.** Check 63.

## The hands and the knobs

### 50. The interaction box, set by the calibration sweep

- **Built.** A hand counts only while its palm is inside one box, the same
  for both hands, symmetric left and right of the camera. The 20-second
  calibration sweep on the HANDS page sets it: where the palms went plus
  40 mm all round (`BOX_MARGIN`). A direction gets a bound only if one hand
  travelled over 12 cm along it. At the edge a hand that is in stays in
  until it is 15 mm past a face (`BOX_EDGE`). There is no on/off switch:
  "reset ranges" opens the box (and resets the ranges). The box is saved in
  `hands.json` (format 2); an older file is read unchanged and backed up
  as `hands.json.bak-v1` the first time it is rewritten.
- **Other options.** Drag the box on the drawing, or six sliders; a box
  per hand; a "use box" checkbox.
- **To reverse.** Widgets over the same ranges (`HandsIO.box`); the three
  sizes are constants in `hands/core.py`.
- **Rough edge.** The box is off during the sweep, so anyone the camera
  sees is counted into it: calibrate with nobody else in view. No camera
  has seen any of this.
- **Judge it.** Checks 72–74 (72 first).

### 51. A hand outside the box is absent everywhere, its ghost included

- **Built.** Outside the box a hand's rows let go and their params return
  to their base that frame, its pinches drop, its "present" light goes
  off, and its ghost fades out. The ghost hands' frame is the box. Only
  the HANDS page still shows it, hollow and as `◌`. A hand coming back is
  caught and glided onto, no jump.
- **Other options.** Still draw it as a dimmed ghost; frame the ghost by
  the axis ranges.
- **To reverse.** One line in `HandsIO._skeletons`; one branch in
  `ghost.box_of`.
- **Judge it.** Checks 73 and 74.

### 52. A hand Learn lands as a gentle push

- **Built.** A new hand Learn now adds to where you set the control,
  instead of the hand becoming the fader:

  | Learned onto | A tilt, sideways or reach (rests in the middle) | Height (rests at the bottom) |
  |---|---|---|
  | a range centred on zero (a rotation rate, an angle, a pan, the hue) | push at the Learn depth | push at the Learn depth |
  | any other fader (speed, brightness, a mix) | push at the Learn depth | the fader, as before |
  | a switch, a list, a button or a whole-number count | the fader | the fader |

  The Learn depth is 0.25 (a quarter of the travel over the hand's whole
  range), on the HANDS page as "Learn depth". A level or low hand leaves
  the preset's value showing. Existing rows and factory presets are not
  changed.
- **Other options.** Height a push everywhere, or the fader everywhere;
  depth 0.5 or 0.1; the depth in `config.toml`.
- **To reverse.** One condition each in `Learn._row`; the depth is
  `learn.PUSH_DEPTH` and `HandSettings.learn_depth`.
- **Rough edge.** Learning the same axis onto the same control again does
  not tame an old row: it only refreshes the pinch gate. No real hand has
  felt 0.25.
- **Judge it.** Checks 75 and 76.

### 53. A hand Learn takes the axis's other rows with it

- **Built.** Learning a hand axis onto a control removes that axis's other
  push and position rows in the loaded preset, switched off or on: a
  learned axis drives one control. The footer names what moved
  ("…; moved from rot.phase.XW"); one ⌘Z brings it back. The file is not
  touched until you save.
- **Other options.** Only position rows move (an axis can end up on three
  controls); only rows of the new row's kind move.
- **To reverse.** One condition in `Learn._place`.
- **Rough edge.** On a factory preset this removes the preset's own row on
  that axis.
- **Judge it.** Check 77 (would you rather a Learn added?).

### 54. Knob smoothing, on at 80 ms

- **Built — against the plan's recommendation.** A value from a desk knob
  or fader now arrives in a straight line over 80 ms and rests exactly on
  the step it always did; the ring shows where the knob is sending it.
  "Knob smoothing" on the SYSTEM page sets it, off to 250 ms; it is saved
  with the show, and a show that saved a number (off included) keeps it.
  Not smoothed: buttons, the cue knob, and a knob on a list, switch or
  whole-number count. One knob turn is still one undo step.
- **Other option.** The plan's recommendation: off until you turn it up.
  Its worry: smoothing leans on the APC40 accepting a ring message
  mid-turn (check 31, never seen on the device).
- **To reverse.** One constant (`routing.SLEW_DEFAULT_S` to 0).
- **Rough edge.** Never on an APC40. If knobs feel late or fight you, turn
  it off on SYSTEM.
- **Judge it.** Checks 78 and 79.

### 55. Where knob smoothing and Learn depth live

- **Built.** Knob smoothing (`desk.slew`) is on SYSTEM; Learn depth
  (`hands.learn_depth`) is on HANDS with the hand feel. Both are saved with
  the show, never by a preset. Neither is on a global-layer knob (K6–K8
  stay free); either can be put on a control by Learn.
- **Other options.** Learn depth or smoothing on K6.
- **To reverse.** One factory row each (and a `bindings.json` rewrite,
  with its backup).
- **Rough edge.** "Knob smoothing" also shows in the ROUTING page's list
  of things a route's depth can be scaled by; scaling by it is not useful.
- **Judge it.** Checks 75 and 78.

### 56. Two hands on the camera: the `hands-orbit` preset

- **Built.** A factory preset in the list, on no F-key. Right hand:
  sideways orbits up to a quarter turn each way; fingers up tip the camera
  to look down (±44°). Left hand: sideways and reaching in pan; raising it
  zooms in, to 2.2× at the top (depth 0.12). A level, low or absent hand
  adds nothing. The two-hand "steering wheel" (the hands measured against
  each other) is not built.
- **Other options.** No preset; the steering wheel (two new axes, against
  the rule of twelve).
- **To reverse.** Hide it from the list, or delete its entry; the depths
  are the five numbers in `preset.hands_orbit_routes`.
- **Rough edge.** Nobody has played it; directions and depths are a first
  cut. Since plan 26 the pan and the zoom move only the shape, in the
  world (rows 183, 184; check 200); the ghost hands stay put.
- **Judge it.** Check 80.

## Learn, Unbind and the on-screen desk

### 57. The big on-screen desk, and what a control says

- **Built.** The APC40 drawing takes the room it has. With the panel hidden
  (H, DEVICE ON/OFF, or the desk's `big` chip) it fills the control window
  and every lit control carries a name once a layout unit is at least
  44 × 32 px. A control says the panel's name for what it does (a bank pad
  its preset's name, ▲ "Brightness +3"). White names are the loaded
  preset's (or the global layer's under SHIFT); grey names are the
  session's. A dark control shows only its glyph. There is no DESK page.
- **Other options.** A DESK page (no room for names); a page that widens
  the panel; a separate "big desk" switch.
- **To reverse.** A page is one function calling `ui_desk._body`; ids
  instead of names is `ui_desk.text`; the sizes are `ui_desk.LABEL_UNIT`,
  `LABEL_UNIT_H`, `LABEL_PX`.
- **Rough edge.** Names that do not fit drop to 11 px on two lines, and a
  few are still cut with "…". Nobody has looked at it on the control
  window.
- **Judge it.** Check 69 (readable from two paces?).

### 58. Click a desk control, then click the param it should drive

- **Built.** A click on the on-screen desk picks a control (framed red;
  ROUTING scrolls to its line). The next click on a param's control maps
  it. While a control is picked every page but ROUTING is dimmed and takes
  no other input. A pick lets go after 20 s with no click, when its footer
  line is clicked, or when the control is clicked again. No click maps
  until the mouse has moved 12 px from the picking click. If the param
  already had a knob, that knob lets go; one ⌘Z undoes both. The session's
  controls cannot be picked to map.
- **Other options.** A click opens ROUTING at the control's line; map via
  a "put D3 here" menu item instead of the dimmed page.
- **To reverse.** One line in `ui_desk.click`; the 20 s and 12 px are
  `ui_desk.PICK_S`, `PICK_MOVE`.
- **Rough edge.** A stray click on the dimmed page maps (one ⌘Z). No real
  mouse has clicked any of it.
- **Judge it.** Check 70.

### 59. One Unbind removes the preset's desk rows and every route

- **Built.** The param's menu lists everything bound to it (a knob, a hand,
  an LFO, a band). **Unbind** removes the loaded preset's desk rows on the
  param and every route on it, whatever drives it; with both kinds bound
  it becomes **Unbind ▸ desk / route / both**. It is offered only when it
  would remove something, never touches a session control, works with no
  APC40 or MIDI off, and is one ⌘Z.
- **Other option.** Desk rows and hand rows only (an LFO or band route
  could not be unbound from its control).
- **To reverse.** A filter on the source's kind in `Learn.unbind`.
- **Judge it.** Check 64.

### 60. "Learn desk" and "Learn hand ▸ left / right"

- **Changed in plan 27.** What a Learn can wait for is no longer the
  fixed `learn.WANTS`: it is "desk" plus each listed device's `wants`
  (row 151), so the menu also offers "Learn <role>" for a new device and
  **Learn sink ▸** (row 158). Learn desk completes from any listed MIDI
  desk. The rule itself stands.
- **Built.** A Learn says what it waits for. **Learn desk** completes only
  from a knob, button or a click on the on-screen desk; **Learn hand ▸
  left** only from the left hand. Anything else does its own job meanwhile.
  The footer shows what is armed on every page; click it to cancel. An
  armed learn never times out. The menu also opens from a row's label and
  from every meter.
- **Other options.** Three flat items (desk, left hand, right hand); one
  `Learn ▸` submenu.
- **To reverse.** The item list in `Panel._ctx_learn`.
- **Rough edge.** Within the chosen hand the axis that travelled furthest
  still wins (row 64). No real hand has completed one.
- **Judge it.** Checks 66–68.

### 61. The session's controls work through an armed desk learn

- **Changed in plan 24.** The diagram below is from before it: S1–S8 are
  now the preset's (learnable; under SHIFT the band strip, row 115), clip
  stops 1–7 are free and clip stop 8 is SAVE (row 110), and scene launch
  1–4 (points, lines, faces, rotate) are invariant (decision 18). The
  rule itself stands.
- **Built.** With "Learn desk" armed, a session control (below) is not a
  candidate: it does its own job and the learn stays armed. A refusal
  also leaves the learn armed.
- **Other options.** As before (the first touch of anything ends the
  learn); refuse and swallow the touch but stay armed.
- **To reverse.** One branch in `MidiIO._handle`, one line in
  `Learn.learn_control`.
- **Rough edge.** A bank pad pressed mid-learn loads its preset, and the
  learn then lands in that preset. With SHIFT latched every non-session
  control is refused until SHIFT is off. Never on an APC40.
- **Judge it.** Check 65.

```
 the session's controls: the same on both layers; never learned, mapped by a click, or unbound

   S1–S8, SM     the faders                    G1·1–G1·8      bank slots 1–8 (clip row 1)
   X             the crossfader (master dim)   G4·1–G5·8      bank slots 9–24 (clip rows 4–5)
   ⇧             SHIFT                         G6·1–G6·8      the clip-stop row (hold: save as)
   B20           TAP TEMPO                     G6·9           STOP ALL CLIPS (reset all)
   B21, B22      NUDGE − / +                   G7·1–G7·6      track select (pick a band)
   B19, B18      ◀ ▶ (band −1 / +1)            G7·9           MASTER select (overlay)
   B10           QUANT (next preset)           G9·1–G9·6      the solo row (a band's transfer)
   B11           OVERDUB (home)                G10·1–G10·6    the rec-arm row (a band's reset)
   B12           METRONOME (LFO trigger)       B13–B15        PLAY, STOP, REC (the mic)
   B5, B6, B9    CLIP/TRACK, DEVICE ON/OFF,    B1             PAN (click-through)
                 DETAIL (cheat sheet)

 the preset's to map: the 16 knobs, the cue knob, clip rows 2–3, the scene-launch
 column, the activator row (G8), ▲ ▼, and the dark buttons
```

### 62. One road onto the desk, with or without the APC40

- **Built.** Putting a param on a desk control lives in the Learn object,
  not the MIDI adapter. A knob bump, a click on the on-screen desk with
  Learn desk armed, and pick-then-click all make the same row, refuse in
  the same words and cost one ⌘Z. With no APC40 plugged in you can still
  lay out a preset's desk by clicking.
- **Other option.** Keep it in the MIDI adapter (no adapter, no mapping).
- **To reverse.** Move the body back.
- **Rough edge.** The device's ring lighting for a row made by a click is
  unseen.
- **Judge it.** Check 70.

### 63. The ROUTING filter: only you clear it

- **Built.** One text field on ROUTING keeps only the lines that contain
  every word typed (a glyph `d3`, a param, a source `r roll`). Only you
  clear it (empty it or its ×), or a click on a desk control; it holds
  across preset loads. The count turns red ("4 of 176 rows") while
  something is hidden. It is never saved and is empty at every launch.
- **Other option.** Also clear it on a preset load.
- **To reverse.** One line where a load is called.
- **Rough edge.** A route, Learn or undo added while it is set can be
  hidden by it (the red count is the only sign). "lfo 1" also matches
  LFO 2, whose address is `lfo:1`. Nobody has typed in it.
- **Judge it.** Check 71.

### 64. Two hand-Learn details left as they were

- **Built (nothing changed).** If a finger is pinched when a hand learn
  lands, that pinch becomes the row's gate: the learning hand's thumb
  first, then the other hand's. Within the wanted hand, the axis that
  travelled furthest wins; there is no "click an axis, then a param".
- **Other options.** Only the learning hand's pinch may gate; build the
  axis-first learn (about twenty lines on the desk pick).
- **To reverse.** One line in `HandsIO.held_gate`; a click handler on the
  HANDS page's axis rows.
- **Judge it.** Check 66: if the wrong axis keeps winning, the axis-first
  learn is the fix.

## Effects on the faces, the look-back, layouts

### 65. The faces' effect picture: what it holds, its size, its fit

- **Built.** An effect aimed at the faces runs over one square picture of
  the whole face as face 0 shows it (the pattern with the bitmap over it),
  1024 × 1024 (`render.FACE_PIC`, not a setting). The faces show it per
  face or in screen space; in screen space it is cover-fit (scaled to the
  longer side, about a fifth cropped top and bottom at 16:9). It is made
  before the scene pass, so the echoes and the dream carry it. With
  nothing aimed at the faces nothing runs and the frame is unchanged.
- **Other options.** The bitmap only (keeps the per-face pattern phase);
  one picture per face; 512 or 2048; stretch or contain.
- **To reverse.** About thirty lines (bitmap only); one number (size); one
  line of GLSL (fit).
- **Rough edge.** While any effect is on the faces, every face shows face
  0's pattern phase. Per face, a subtle effect can read faint. Never seen
  on a projector or the glass.
- **Judge it.** Checks 91–93 and 98.

### 66. Performers on an effect's target and on the face mapping

- **Built.** An effect's target (`fx.<name>.target`, frame or faces)
  cannot be driven by a hand, band or LFO, like its order; a knob, key,
  the page or a preset sets it. The face mapping (`fx.face_map`, per face
  or screen) can be driven by any performer.
- **Other options.** The target performable (an effect flickering between
  chains); the mapping not performable.
- **To reverse.** One flag each (`fx.declare`).
- **Judge it.** Check 91.

### 67. The chip grid is the chain view; drag a chip to reorder

- **Built.** The FX page's chips are in stack order. Dragging a chip by
  its name onto another puts it before that one (the right half of the
  last chip's name is "to the end"). A drop opens the dragged effect and
  is one undo step. Two status lines read what runs on the frame and on
  the faces, in order. The order slider stays.
- **Other options.** Two lists of rows, one per target (the chip grid
  would have to go); the grid split into frame and faces groups.
- **To reverse.** The grouping is one loop in `ui_fx.page`; the drag is
  two blocks in `ui_fx._chip`.
- **Rough edge.** No real mouse or trackpad has dragged a chip.
- **Judge it.** Check 94.

### 68. An effect is re-aimed by the open strip's ONTO chips

- **Built.** The open strip's title line ends in **ONTO** and two chips,
  frame and faces, the lit one where it runs. A drag only reorders; it
  never changes a target or a switch. A target change is one undo step.
- **Other option.** Drop a chip on a status line to re-aim it.
- **To reverse.** A dozen lines in `ui_fx._faces_row` and the frame line.
- **Judge it.** Checks 91 and 94.

### 69. The LOOKBACK page as ECHOES, DREAM and BOTH, and every dream layer in one menu

- **Built.** The page has three sections named for what a knob acts on.
  The dream's layer is one menu offering every layer of both nets — the
  13 conv layers of VGG16 and GoogLeNet's conv1–conv3 and nine inception
  blocks, 25 in all — under a heading per net, shallow to deep, each
  with its own name and a few words on what it draws; a hover says more.
  The deepest six say "slower" (over 25 ms a frame at 256 px). The new
  labels are used everywhere: ROUTING, a Learn's line and the desk say
  "Echo time apart" (was Spacing), "Shape hides wake" (was Occlude),
  "Look-back detail" (was Resolution), "Dream speed", and so on. A saved
  look keeps its layer: the stored index of the six older layers is
  unchanged.
- **Other option.** Offer only a few hand-picked layers, under nicknames.
- **To reverse.** The words are one table, `lookback.LAYER_INFO`; a layer
  left out is a line there and in `dream.TRUNKS` (append-only `LAYERS`
  keeps saved indices).
- **Rough edge.** The descriptions come from one to two seconds of
  dreaming a still 24-cell and a colour field at the defaults
  (`assets/20-fx-dream-looks/dream-layers*.jpg`), and from depth; nobody
  has watched the new layers on the rig. A key or desk row that *steps*
  the layer walks the stored order (the six older layers first), not the
  menu's.
- **Judge it.** Check 95: are the words right, and are 25 too many?

### 70. The dream's "speed" is `dream.k`, read in frames

- **Built.** `dream.k` (the share of each frame blended into the dream) is
  labelled "speed" and reads as the dream frames it takes a frame's share
  to halve: "≈23 frames" slow, "≈14 frames" at the default, one decimal
  under ten ("1.9 frames" fastest).
- **Other options.** A new `dream.speed` that also scales the strength;
  make `k` per second (a migration).
- **To reverse.** Three strings and `params.dream_speed_text`.
- **Rough edge.** Faster is also shallower. It counts the worker's frames,
  so a slower worker is a slower dream. Nobody has judged the dream at any
  speed.
- **Judge it.** Check 96.

### 71. Instance layouts: grid, honeycomb, ring

- **Built.** `view.inst_layout` (VIEW page, under the count) is GRID (the
  old layout, bit for bit), HEX (a honeycomb spiral from the centre, whole
  hexagons at 7, 19, 37, 61, 91; a copy never moves as the count grows) or
  RING (one circle, copy 0 at the top). The three motions are unchanged.
- **Other options.** HEX as offset rows; RING as concentric rings.
- **To reverse.** One branch of `render.inst_positions`.
- **Rough edge.** HEX with ORBIT at amp 0.35 overlaps neighbours visibly.
- **Judge it.** Check 97.

## Presets and the desk

### 72. The bank of twenty-four

- **Built.** A show's bank is 24 slots: 1–8 are F1–F8 and clip row 1;
  9–24 are clip rows 4–5 and the PRESETS page's sixteen smaller buttons
  (four a row). Slots 9–24 have no triggers of their own; they are
  reached through `preset.select`. The show file stays
  `hyperspace.project/2`, is never rewritten by a load, and holds the bank
  only up to its last filled slot; the first write past slot 8 keeps the
  old file as `<show>.hyp.json.bak-v2-bank8`. A fresh home's factory party
  show has TRACER on slot 9.
- **Other options.** Load/save triggers for every slot (32 more params);
  a new `project/3` format (older builds refuse your show); far slots
  eight a row.
- **To reverse.** One line each (`params.build_registry`,
  `library/projects/party.hyp.json`, `ui_presets.FAR_COLS`); a new format
  needs a migration.
- **Rough edge.** An absolute knob learned onto `preset.select` spreads
  over all 24 and can rest on an empty slot (audit R14). With "more" open,
  a warning line scrolls the PRESETS page a little.
- **Judge it.** Checks 81 and 83.

### 73. Clip rows 4–5 are the bank, and how the bank lights

- **Note (plan 24).** In the diagram below, column 9's Points, Lines,
  Faces and Rotate are now invariant (the same under SHIFT), and the G6
  row is no longer a SAVE AS bar: clip stops 1–7 are free and clip stop
  8 is SAVE (rows 110, 113). The bank itself is unchanged.
- **Built.** Rows 4–5 load slots 9–24 on both layers (invariant). A bank
  pad is green when its preset is loaded, amber (Akai velocity 5) when its
  slot is filled, dark when empty. The sixteen shape pads older presets
  carry on those rows are dropped quietly at load; any other row of yours
  on them is dropped with a note. Shapes are on the cue knob (all 26).
- **Other options.** Only the loaded pad lit; a note per dropped row.
- **To reverse.** `apc40.filled_of` returns None (lights); empty
  `routing.RETIRED_DESK_ROWS` (quiet drop); rows 4–5 back to shapes needs
  the map and a remap with a backup.
- **Rough edge.** No pad shows which shape is up. Amber beside green is
  unseen on the mk1.
- **Judge it.** Checks 82–84.

```
 the desk's clip grid      preset layer                             under SHIFT (global layer)
        1     2     3     4     5     6     7     8      9         1 … 8                  9
 G1   [ 1]  [ 2]  [ 3]  [ 4]  [ 5]  [ 6]  [ 7]  [ 8]   Points      [ 1] … [ 8]            ·
 G2     ·     ·     ·     ·     ·     ·     ·     ·    Lines       scene 1 … scene 8      ·
 G3     ·     ·     ·     ·   STILL ORBIT WAVE RIPPLE  Faces       scene 9, 10, 11        ·
 G4   [ 9]  [10]  [11]  [12]  [13]  [14]  [15]  [16]   Rotate      [ 9] … [16]            ·
 G5   [17]  [18]  [19]  [20]  [21]  [22]  [23]  [24]   Reset view  [17] … [24]            ·
 G6   [============ SAVE AS (hold) ============]      [Reset all]  [==== SAVE AS ====]   [Reset all]
 C    cue knob: Shape (all 26)                                     ·

 [ ] invariant (the same on both layers)   · dark   [n] bank slot n
 a bank pad: green = loaded · amber = a preset is here · dark = empty
```

### 74. No backup, no rewrite of `bindings.json`

- **Built.** When a launch brings `bindings.json` up to date it backs the
  file up first; if the copy fails, the file is not rewritten for the rest
  of the session (the table in memory is updated; the next launch tries
  again). One line on the SYSTEM page says what the launch did, e.g.
  "bindings.json updated (16 rows changed), the old file kept as
  bindings.json.bak-v3"; each change is also on stderr.
- **Other option.** Rewrite anyway, with nothing to go back to.
- **To reverse.** The three `backup(…) is None` branches.
- **Judge it.** Checks 84 and 57.

### 75. The device knobs, only where they do something

- **Built.** A fresh preset, and every factory preset with no knobs of its
  own, gets D1–D4 = 4D depth, yaw, pitch, face pattern; D5–D8 dark.
  `hands-fx`, `hands-pinch` and `lfo-breathe` have their own sets. WAKE,
  TRACER, TRIP, ACID, MANDALA and NOITA keep their eight. A preset you
  saved before keeps its own desk.
- **Other option.** Make every scene preset "echo-ready" (look-back on,
  echo mix and fade on D5–D6): every party preset pays for a dream nobody
  sees.
- **To reverse.** One tuple in `preset.py` or `apc40.SCENE`, then
  `python -m hyperspace.preset`.
- **Rough edge.** D4 (pattern) changes nothing visible on a preset with
  faces off. Never turned on an APC40.
- **Judge it.** Check 85.

### 76. Hide, rename and the trash, in the preset list

- **Built.** In the preset list: × on every preset (yours go to the
  trash; a factory one is hidden via `<home>/hidden.json`), **rename** on
  yours, and at the foot "show hidden (n)" and "trash (n) ▸" with
  **restore** and **empty trash…**. Renaming a factory preset is refused
  ("save copy, then rename the copy"). Rename repoints every show of yours
  that names it, each copied to the trash first; it is not an undo step.
  Restore never writes over a file (a taken name restores as the next
  free one). Empty asks for a second click within 4 s.
- **Other options.** Rename a factory preset by copying and hiding it;
  put the trash under "more" on PRESETS, or a TRASH page.
- **To reverse.** A branch in `Library.rename`; two lines moved out of
  `ui_presets._list_popup`.
- **Rough edge.** **Empty trash is the one delete with no copy kept.** ×
  on yours leaves slots naming it in the warning colour until restored.
  No person has clicked these popups.
- **Judge it.** Checks 86–88.

### 77. The red dot and "save copy"

- **Built.** The dirty dot is a 12 px red disc on every strip and on
  ROUTING's head, and the save chip is solid red while there is something
  to save. On a factory preset the chip reads "save copy" (your copy takes
  its place in the list). The preset strip has no reset. Nothing prompts.
- **Other option.** "save copy" on every strip (a module strip would not
  fit).
- **To reverse.** `ui.DOT_R`; `ui_presets.save_label`; one condition in
  `ui_presets.strip`.
- **Rough edge.** On a module strip under "more" the save chip overlaps
  the name button (audit U10).
- **Judge it.** Check 89.

### 78. The home in git

- **Superseded by row 109** (plan 25, 2026-10-14): the home-as-git module and
  its config switch were removed; presets are shared through a cloud-synced
  folder, which keeps its own file versions. Kept here as history.
- **Built.** With `[library] git = true` (off by default) the home folder
  is a local git repository: no remote, nothing pushed. The first save
  after launch makes it; every save, trash, rename, hide, unhide, restore
  and show write is a commit. The trash, `weights/`, logs, `last_show`,
  `windows.json` and the `*.bak-*` backups are ignored. A home inside
  another repository is never touched. Git runs on its own thread and
  never blocks or fails a save; a failed commit is said once and the next
  one picks up its files.
- **Other option.** Track the trash ("empty" recoverable; every overwrite
  stored twice).
- **To reverse.** One line of `homegit.IGNORE`; off is the config key.
- **Rough edge.** Emptying the trash makes no commit, and the app never
  restores from git (use git yourself).
- **Judge it.** Check 90.

## The outputs and the ghost hands

### 79. Where "hands through effects" puts the hands

- **Superseded in part by rows 193 and 194** (plan 26, 2026-10-14): the
  frame is a render graph, `Renderer._pipeline` is gone, and the
  switches below are the default graph's wiring (`graph.default_graph`);
  the history is wiring — it holds the scene by default, as below, and
  the scene with the hands when a preset's `graph` section says so; and
  the hands can also be drawn inside the scene (row 191). With the
  default graph every picture below is as it was. Kept here as history.
- **Built.** With an output's "through effects" tick on, its hands go in
  after the look-back composite and before the first effect, so the
  effects bend them. The echoes and the dream are captured from the scene
  alone and never hold the hands. With the scene off and through on, the
  output shows the hands alone through the effects, on black.
- **Other options.** Hands onto the scene before the look-back (they
  trail and feed the dream, but then every output shows hand echoes); the
  scene off + through the same as "hands over".
- **To reverse.** A few lines in `Renderer._pipeline` (every output at
  once); per output needs a second history and dream worker (days).
- **Rough edge.** Two outputs that disagree run the effects twice a frame.
- **Judge it.** Checks 102 and 103.

```
   scene  hands  through   what the output shows (an effect on, a hand in the box)
    on     on     off      the scene with its effects, the hands clean on top   (default)
    on     on     on       the scene and the hands, both bent by the effects
    on     off    —        the scene with its effects
    off    on     off      the hands alone, clean, on black
    off    on     on       the hands alone, bent by the effects, on black
    off    off    —        black
   With no effect on, or no hand shown, "through" changes nothing.
```

### 80. The guide and the tethers' labels are never bent

- **Built.** When hands go through effects, the guide (balls, rings,
  pinch beads) and the tethers' text labels are drawn in a second layer
  laid on after the effects, so they stay legible. The second layer exists
  only while it is needed; otherwise the hands are one layer as before.
- **Other option.** Let them bend with the hands.
- **To reverse.** Delete the readout layer (`Ghost.readout`,
  `Ghost.composite_readout`), a few hours.
- **Judge it.** Check 103.

### 81. Each output's switches are rig settings

- **Built.** `output.N.scene`, `.hands`, `.through` and `.dim` are never
  saved, not performable, and untouched by presets, shows and undo. Every
  launch and ⌘R takes them from the `[[output.screens]]` entries in
  `config.toml`; a config `dim` under 0.1 is raised to 0.1 so the config
  cannot launch an output black (the fader still goes to 0). An output's
  own dim fader exists when two or more outputs are listed, or when a lone
  output's entry sets `dim` under 1. Each switch can be learned onto a
  desk button.
- **Other option.** Session params saved in the show (a show made on the
  rig would carry `output.2.*` to a laptop).
- **To reverse.** Flip `persist` in `overlay.register_switches`, an hour.
- **Judge it.** Checks 101 and 104.

### 82. An output of another shape is letterboxed

- **Built.** The frame is drawn once, at output 1's size. An output of
  another shape shows the whole frame, centred, with black bars; the hands
  sit on the same part of the shape on every output. List the larger
  screen first in the config.
- **Other options.** Cover (crop); stretch; render per output size (days).
- **To reverse.** `outputs.fit`, a few lines.
- **Judge it.** Check 106.

### 83. One window renders, the others copy; only output 1 waits

- **Built.** Output 1's GL context renders every distinct picture once;
  each later output copies it in its own context and adds its hands,
  guide and dim. Only output 1's swap waits for its screen; the others
  swap at once. The hands' layer has no size cap.
- **Other options.** Every output waits (no tearing anywhere); a hidden
  window renders and every output copies.
- **To reverse.** One `glfw.swap_interval` call per output
  (`app._open_presenters`); the hidden renderer is days.
- **Rough edge.** **The reason is unconfirmed**: the plan measured two
  waiting swaps halving the frame rate, but the build's launches ran
  unpaced. Never run with two screens or mixed refresh rates.
- **Judge it.** Check 107.

### 84. Ghost hands and each output's hands tick

- **Built.** Both stay. Ghost hands (`ghost.on`, HANDS page) says whether
  hands are drawn at all; each output's tick says where they show. The
  OUTPUT page names Ghost hands when it is the reason an output has none.
- **Other option.** The ticks replace Ghost hands (breaks saved shows and
  learned rows, no single off).
- **To reverse.** A migration of shows and rows on `ghost.on`, a day or
  two.
- **Judge it.** Checks 102 and 105.

### 85. The OUTPUT page says in words what each output shows

- **Built.** Each output has a "shows: …" line ("scene + hands over the
  effects", "black — dim 0", …), and the footer names a black output on
  every page ("output 2 black"). There is no picture of the render in the
  control window. With one output there is one block and no dim row of
  its own (the master dim is its dim).
- **Other option.** A small live picture per output (about 0.5 ms each).
- **To reverse.** About a day for the pictures.
- **Judge it.** Checks 102 and 105.

### 86. A screen not connected at launch; later outputs' screens

- **Built.** A later output whose screen is not connected at launch is not
  opened, with a note ("screen 2 is not connected" on the OUTPUT page).
  Output 1 always opens. Later outputs take their screen and fullscreen
  from `config.toml` only; the OUTPUT page's screen and fullscreen
  controls are output 1's.
- **Other options.** Open it anyway, where it was last or on the first
  screen (it would cover the controls); a screen and fullscreen control
  per output.
- **To reverse.** One branch in `app._later_rect`; per-output controls
  half a day.
- **Rough edge.** A screen plugged in after launch is not used until ⌘R or
  a relaunch (audit P6). What macOS does when a cable is pulled mid-run is
  unknown.
- **Judge it.** Checks 101, 111 and 112.

### 87. `ghost.style`: five drawn objects for the hands

- **Built.** One choice on the HANDS page, saved with the show, never
  performable (a desk button or knob can be learned onto it):

  | Style | What is drawn |
  |---|---|
  | HANDS | the capsule hands (the default, unchanged) |
  | JOINTS | a bead per joint, the fingertips largest |
  | PALMS | an orb that swells as the hand opens, a ring in the palm's plane, a spoke where the fingers point |
  | CAGE | a wire octahedron round each hand that turns with the palm, a small solid inside |
  | MARIONETTE | a bead per fingertip on strings from a bar above the hand |

  In the four new styles the guide is drawn on top.
- **Other option.** Five separate on/off switches.
- **To reverse.** One function in `ghost.PARTS` per style.
- **Judge it.** Check 109 — and say which styles to keep.

### 88. Ghost mirror, guide and tethers cannot follow a hand

- **Built.** `ghost.mirror`, `ghost.guide` and `ghost.tethers` (with
  `ghost.style`) are not performable. A hand Learn onto one is refused in
  words ("… can't follow a hand (not modulatable) — not learned; Learn
  desk puts it on a button"). A saved route onto one is dropped at load
  with a note; the file is not rewritten. `ghost.on` and `ghost.alpha`
  stay performable.
- **Other options.** Leave them performable (a route could flip the hands
  mid-set); not performable with no refusal (a Learn writes a dead row).
- **To reverse.** Three flags.
- **Judge it.** Check 110.

## The shapes in four dimensions (plan 22)

Seven shapes (Heart, Star, Rose, Torus, Trefoil knot, Starfruit, Möbius
strip) used to sit at w = 0 and went flat whenever the bass bands turned a
W plane. That each one either gets real 4D extent or stays 3D, chosen per
shape, is the owner's; how each was chosen is below. The sheets are in
[`plans/assets/22-flat-shapes/`](plans/assets/22-flat-shapes/); the plan
as built is [`plans/22-flat-shapes-and-face-patterns.md`](plans/22-flat-shapes-and-face-patterns.md).

### 89. The Heart is masked; the other shapes are lifted

- **Built.** The Star, Rose, Torus, Trefoil knot, Starfruit and Möbius
  strip are lifted into the fourth dimension: as XW, YW and ZW turn they
  bend, saddle and swap sides like the Clifford torus, and none goes
  flat. The Heart stays a 3D heart prism; the bass bands turn it in 3D
  (row 90). On the VIEW page a lifted shape's alias reads "4D lift · …";
  the Heart keeps "3D · …".
- **Other options.** Lift the Heart too (the best lift tried,
  z·(sin t + 2 sin 2t + 2 sin 3t), read as a twisted ribbon or bow-tie
  at XW / YW 60–120° and 240–300°, although it passed both gates: ratio
  0.376, at most 0.11 of its face area edge-on);
  mask all seven (the shapes stay 3D and never turn through W); mask any
  of the others.
- **To reverse.** One word per shape in `geometry.SHAPES` (`w="mask"` or
  `"lift"`), plus removing the lift from its builder, which re-records
  that shape's digest: minutes per shape.
- **Rough edge.** The Star becomes a box, a lantern of its walls, at XW
  90° and 270°; the Starfruit's five ridges are softened at rest by the
  lift's perspective (row 93). Factory presets `plasma-heart`,
  `spiral-silk` and `inverse-halo` show the Heart, the Trefoil knot and
  the Starfruit, and now move differently.
- **Judge it.** Checks 113 and 114.

### 90. The W fold happens where the shape is drawn: XW → XZ, YW → YZ, ZW → XY

- **Built.** A masked shape cannot turn through W, so each W plane's
  angle is added onto a 3D plane as the frame is drawn
  (`geometry.view_angles`, `Renderer.draw_scene`): SUB (ZW) rolls the
  Heart in the screen plane, BASS (XW) spins it about the vertical, MIDB
  (YW) tumbles it about the horizontal. No param changes, the integrator
  is untouched, and a rate or a phase route on a W plane both reach the
  Heart. `Shape.w` says how each shape fills W in one of four words
  (`native`, `flat`, `lift`, `mask`).
- **Other options.** Fold in the integrator (it would ignore a phase
  route on a W plane, and a shape's pose would depend on which shapes
  were shown before it); the Hodge-dual remap XW → YZ, YW → XZ, ZW → XY
  (each W plane onto the 3D plane it leaves alone); a yes/no "3D" flag
  instead of four words.
- **To reverse.** `W_REMAP` is three numbers (minutes); folding
  elsewhere is a day.
- **Rough edge.** The VIEW page's XW / YW / ZW keys, `rot.phase.*` and
  ROUTING go on showing the W planes turning while the Heart turns in
  XZ, YZ and XY; nothing on the page says the planes are folded. BASS
  onto XZ is a spin about the vertical: on the Heart it turns the heart
  side-on, but on a shape round about the vertical (the Torus, the
  Starfruit), were one masked, it would barely show. 4D depth (↑ / ↓,
  TUMBLE's D1) does nothing on the Heart: with w at 0 the 4D divide
  leaves it as it is.
- **Judge it.** Check 114 — and whether BASS's spin reads as BASS.

### 91. A masked shape cues depth on z

- **Built.** Lines and faces fade, thin and sort by depth. A 4D shape
  cues on w; a masked shape's w is 0 at every angle, so it cues on its
  depth toward the 3D camera instead (z after the camera's yaw and
  pitch, `geometry.view_depth`), and is as bright and as deep-looking as
  a polytope. The near side is the bright one, drawn on top, however
  the camera is turned.
- **Other option.** Leave it on w: the Heart would draw at the cue's
  dimmest, flat and faint, at every angle.
- **To reverse.** Three lines in `Renderer.draw_scene`.
- **Judge it.** Check 114.

### 92. `VOLUME_FLOOR` is 0.15, calibrated across all 18 4D shapes

- **Built.** "Keeps its volume" is measured, not judged: the shape's 3D
  cloud's smallest singular value over its largest (1 a ball, 0 a
  plane). Each lifted or masked shape must stay at or over 0.15 through
  a full turn of each W plane, from rest and from a generic pose, and
  turn at most 0.15 of its face area edge-on. 0.15 is half the worst
  any of the 18 4D shapes reaches (the cubic pyramid, 0.30; then the
  4,8-duoprism 0.53, the dodecahedral prism 0.64, the 5-cell 0.65, the
  tesseract 0.94, the Clifford torus 0.97, the 24-cell, 120-cell and
  600-cell 1.00), so no surface is held rounder than a polytope already
  is. You asked for it calibrated from what already works, not picked.
  Every shape's geometry is also pinned by a digest, with floats rounded
  to 1e-9 so a last-bit difference between machines is not a change.
- **Other options.** Calibrate on the tesseract, 24-cell and Clifford
  torus only (about 0.47: no masked Heart, Star, Torus or Möbius strip
  could meet it, since a mask leaves a shape its own 3D proportions,
  0.16–0.43); judge by eye alone; volume only, no edge-on gate.
- **To reverse.** One constant; the tests re-gate every shape on it.
- **Rough edge.** A sweep turns one W plane at a time; the music turns
  all six at once. 500 random poses of all six planes (the docs pass,
  seed 0) left every lifted or masked shape over the floor, the Rose
  lowest at 0.156, but random poses are a sample, not a proof. The
  edge-on gate, 0.15, sits just under the 4D shapes' own worst (the
  cubic pyramid 0.155, the 3,3-duoprism 0.167), so a polytope would not
  pass it; the Star, at 0.139, is the gated shape closest to it.
- **Judge it.** Checks 113 and 119.

### 93. How a shape is lifted: a function of its own parameters, by four rules

- **Built.** Every builder takes a lift of its own parameters — w(u, v)
  on a patch, w(θ, φ) on a sphere, w(t, z) on an extruded outline, w(t,
  a) on a tube — and keeps its vertices, edges and faces. Each lift has
  no linear part of x, y or z (that only tilts the shape into another
  flat space), is odd under each single-axis mirror (an even one folds
  the halves onto each other into a sheet: the torus read as a bowl, the
  starfruit as a sombrero), depends on z on an extruded outline (else
  every wall goes edge-on at once), and agrees wherever the surface
  welds. The lifts: Star 0.6·(z/h)·sin t, Rose z·(3 sin 4θ + sin 8θ),
  Torus 0.7·sin v·sin 2u, Trefoil 1.5·cos 3t, Starfruit 0.6·sin 2φ·sin 2θ,
  Möbius 0.5·sin 2u.
- **Other options.** A lift as a point function w(x, y, z) (it cannot
  separate the sheets where a surface crosses itself, which the Klein
  bottle needs); sweeping each surface into a 3-manifold (more faces);
  other formulas per shape.
- **To reverse.** One lambda per shape.
- **Rough edge.** The shapes change look at rest as well as in a turn:
  the perspective divide shows a lifted shape slightly bent even with
  every plane at 0 (the Starfruit's ridges soften).
- **Judge it.** Checks 113 and 115.

### 94. The Möbius strip is widened (0.45 → 0.55) and lifted

- **Built.** The band is a little wider and lifted by 0.5·sin 2u (0 at
  the seam, which still welds). Through the W planes it keeps
  0.163 / 0.179 / 0.179. A band that thin limits any lift (at 0.45 wide
  the same lift keeps only 0.134), hence the width.
- **Other option.** Mask it at its old width (0.158, no geometry change),
  so it would stay 3D beside the Klein bottle.
- **To reverse.** The width and the lift in `_build_mobius`, or `w="mask"`
  with the old width: minutes, plus the digest.
- **Rough edge.** It clears the floor by little. Your shared presets
  `hi-frek-variation-1` and `light-realm-variation-1` show the Möbius
  strip and now look different.
- **Judge it.** Checks 115 and 118.

### 95. The Rose is made a seventh shape, deepened (0.12 → 0.16) and lifted

- **Built.** The brief named six flat shapes; the Rose was a seventh,
  built at w = 0 like them. **The orchestrator added it to the plan — it
  is the orchestrator's call, not yours.** Its own 3D proportions at
  depth 0.12 (0.118) were under the floor, and no lift can fatten a shape
  at rest, so it is 0.16 deep (the smallest change that clears: 0.157)
  and lifted by z·(3 sin 4θ + sin 8θ), each petal's wall twisting
  through w, front against back. The pinch still welds.
- **Other options.** Leave the Rose flat (it goes flat at 90° of each W
  plane, as before); mask it (it would still read 0.118, under the
  floor, unless deepened anyway); deepen more.
- **To reverse.** The depth and the lift in `_build_rose`: minutes, plus
  the digest.
- **Rough edge.** It clears the floor by 5%, and it may read less
  delicate at 0.16.
- **Judge it.** Check 115.

### 96. The Klein bottle: the classic bottle, lifted, shape 26

- **Built.** A new shape after the Möbius strip: the textbook "bottle"
  immersion, which in 3D must pass through itself where the neck enters
  the body, lifted by w = sin 2u + ½·sin v·cos 2u so that in 4D the neck
  passes beside the body and never through it. 36 × 16 vertices (576 V,
  1152 E, 576 faces), centred on its bounding box; `Shape.w` "lift";
  the VIEW page reads "KLEIN BOTTLE", "4D · one-sided bottle, no
  self-crossing", "χ=0 · one side". The cue knob, ← / → and the pad's
  LB / RB reach it and stop there.
- **Other options.** The torus-style ("figure-8") immersion (at rest it
  reads as a pinched torus); `Shape.w` "native" (it is built with w from
  the start, but its lift is of a 3D immersion, as the others'); a denser
  grid; a "∞"-style glyph in the sym text (the font may lack it).
- **To reverse.** It is the last shape, so it can be dropped with its V/E
  row and digest (a preset saved on shape 26 would then point past the
  end); the grid is two numbers.
- **Rough edge.** To the orchestrator it reads at rest more like a
  curled horn or a loop than the textbook bottle. The neck is sparse at
  some angles (16 round).
- **Judge it.** Checks 116 and 117.

### 97. A bent cap is framed by its least-squares plane

- **Built.** The Star's lift bends its two pentagram caps through w. A
  face of more than four corners that is not planar is now framed (for
  the pattern's UVs and the triangulation) by its least-squares plane,
  where its outline stays simple and its triangles tile it exactly.
  Every planar face, every polytope's included, keeps the basis it had,
  so nothing else changed.
- **Other option.** Split each bent cap into triangles or quads (more
  faces, and the pattern would no longer span the cap as one face).
- **To reverse.** Four lines in `geometry._face_xy` — but the Star's caps
  would then fold over themselves.
- **Rough edge.** Only the Star has such caps. The star polytopes on the
  shortlist would bring pentagram faces of their own
  ([`plans/22-polytope-shortlist.md`](plans/22-polytope-shortlist.md)).
- **Judge it.** Check 115.

## The face patterns (plan 22)

That the eight pattern inputs could be redesigned with nothing to
migrate, and that a page nobody can steer is not a win, were yours; what
was built on them is below. The plan as built is
[`plans/22-flat-shapes-and-face-patterns.md`](plans/22-flat-shapes-and-face-patterns.md),
Stream B; the pictures are in
[`plans/assets/22-face-patterns/`](plans/assets/22-face-patterns/).

### 98. The eight pattern inputs: what each means, and in what order

- **Built.** Every pattern reads its inputs the same way: 0 SCALE (small
  and many → big and few), 1 GLOW (dim → white-hot), 2 WARP (straight →
  heavily bent), 3 SPEED (frozen → 2.6×), 4 COLOUR (grey → more hues), 5
  SHARP (soft → crisp), 6 HUE (turns the palette, half a turn per unit),
  7 SPREAD (every face in unison → each its own). 1.0 is always the
  pattern as designed. The order puts the factory's lanes where they
  read best: SUB swells the scale, the kick flashes the glow, the low
  mids bend, the mids drive the speed, the snare flares the colour, the
  hats sharpen. HUE and SPREAD are left free for an LFO, a macro or a
  knob. ROUTING, Learn and the desk call them "Pattern scale" and so on;
  the FACES page "SCALE". `patterns.py` holds the table and the shader
  is held to it by tests.
- **Other options.** A COUNT or DENSITY input instead of SPREAD (on the
  grid patterns it does what SCALE does); HUE or SPREAD on a band (a hue
  that follows a band flickers); another order (any order changes what
  each band does by default).
- **To reverse.** A reorder is the accessors in `patterns.glsl` and the
  table in `patterns.py`, an hour; a different meaning is that input's
  helper in every mode, a day.
- **Rough edge.** SHARP at 0 and GLOW at 2.6 both brighten, differently.
- **Judge it.** Checks 122, 124 and 125.

### 99. SPEED is an integrated clock

- **Built.** The renderer folds SPEED into the patterns' clock: each
  frame it moves on by the time since the last frame times SPEED
  (`Renderer._pattern_clock`, `u_ptime`). A band on SPEED changes how
  fast a pattern goes, never where it is.
- **Other option.** Time × SPEED, as before (every change of SPEED jumps
  the phase by time × the change — minutes into a set, a big jump).
- **To reverse.** One function, minutes.
- **Rough edge.** `u_time` is still uploaded and no pattern reads it.
- **Judge it.** Check 123.

### 100. WARP and SPREAD do nothing from 0 to 1 on straight and unison designs; GLOW keeps 30%

- **Built.** A pattern that is straight as designed (PLAID, MOIRE,
  BLOOM's ring, HEX, METER, PULSE, TRUCHET, KALEIDO) stays straight from
  WARP 0 to 1 and bends only above 1; one whose faces play in unison
  (PLAID, WEAVE) stays in step from SPREAD 0 to 1 and parts only above.
  GLOW at 0 keeps 30% of the design's light, so a route on a base of 0
  does not make the faces vanish. GLOW, HUE and COLOUR's grey end are one
  pass over every pattern alike.
- **Other options.** Make 0 "less than designed" on every pattern (a
  straight design has nothing to take away); GLOW to black at 0.
- **To reverse.** A constant in `warp()`, `face_k1()` and `finish()`,
  minutes each.
- **Rough edge.** A route on a base of 0 moves WARP or SPREAD on those
  designs only once it passes 1. WARP at 2.6 on HEX may be too strong.
- **Judge it.** Checks 122, 137 and 138.

### 101. Fixed counts: seven petals, five arms, six wedges

- **Built.** BLOOM always has seven petals, SPIRAL five arms and KALEIDO
  six mirrored wedges. No input changes a count.
- **Other option.** A count on an input (driven by audio, a count
  flickers as it steps); KALEIDO by the face's sides (the shader does not
  know them).
- **To reverse.** A few lines per pattern.
- **Judge it.** Checks 122 and 131.

### 102. The FACES page as a browser of swatch chips

- **Built.** FACES has a module of its own (`ui_patterns.py`), as FX
  does. Every pattern is a chip with a small live swatch of it on the
  inputs as they are now, four to a row, the one on show red, its one
  line on hover; under them the mode's name and line with ‹ ›; then the
  eight inputs by name, each saying what it does on this pattern and
  what drives it, with a slider and a **1** chip back to neutral; **all
  neutral** is one undo step. A GLSL error or "Faces is off" takes the
  line's place. The renderer draws one swatch a frame only while the page
  is open.
- **Other options.** The old dropdown with named sliders; still
  thumbnails (they would not show the current inputs); every swatch
  every frame.
- **To reverse.** The page is one module; the dropdown is an hour.
- **Rough edge.** Its fit on the Mac is **unverified** (18 px spare in
  the container's font metrics, which are not the Mac's; the tallest
  case is a mode's own about line wrapping). The pattern
  group's preset strip draws its dirty dot over its ▶ chip at this
  width.
- **Judge it.** Checks 120, 125, 126 and 128.

### 103. "+ SUB": an idle input offers the convention's source

- **Built.** An input nothing drives offers, at the end of its line, the
  source the convention puts on it: "+ SUB" … "+ AIR" for the first six,
  "+ LFO 1" for HUE, "+ LFO 2" for SPREAD. A click adds a push route at
  the factory depth (0.35) into the loaded preset and stays on FACES;
  undo takes it back. A driven input names its driver instead ("SUB
  pushes +0.35", "K3 sets it", "macro.4 sets its base"), a link that
  opens ROUTING filtered to that input.
- **Other option.** The existing menu item "Route a lane here…", which
  uses the band selected on the analyzer and jumps to ROUTING.
- **To reverse.** A few lines in `ui_patterns`.
- **Rough edge.** "+ LFO 1" looks inert while LFO 1's depth is 0.
- **Judge it.** Check 127.

### 104. METER and PULSE read the bands directly

- **Built.** Two patterns draw the music itself: METER a wedge of LEDs
  per band, PULSE the kick, the snare and the hats as shapes. For them
  the app hands the renderer the analyzer's lanes each frame, as it hands
  over the dim (`app._bands`, `u_levels`): read only, never a param, and
  no other pattern reads it. What they show ignores the routes by
  design; the inputs style them as on any pattern.
- **Other option.** Draw them through the routed inputs only (a band
  could not have a wedge of its own); a param per band (more for
  presets to save and undo to watch).
- **To reverse.** Drop the two patterns and the uniform, an hour.
- **Rough edge.** The hand-over happens just before the frame is drawn,
  outside the guarded step, and no test pins its place in the frame.
- **Judge it.** Check 129.

### 105. Five new patterns; the old twelve's art unchanged

- **Built.** METER and PULSE (the audio, seen), MARBLE and TRUCHET
  (generative depth), KALEIDO (bold colour), appended after EMBER so
  every preset's pattern stays where it was. The twelve old patterns
  were moved onto the convention but their look at 1.0 is unchanged, so
  no preset changes look from art.
- **Other options.** More patterns; rework the old twelve's art too.
- **To reverse.** A pattern can be dropped only from the end (presets
  hold the index).
- **Rough edge.** MARBLE is the dearest pattern: 4.19× FLAT on the
  600-cell in software GL (CELLS, the dearest before, 3.13×). KALEIDO is
  always six-fold.
- **Judge it.** Checks 129, 130 and 131.

### 106. The factory pattern routes at depth 0.35; `legacy6` drops the pattern parity

- **Built.** **This is the orchestrator's call, not yours.** The six
  factory lane → pattern routes push at 0.35 instead of 1, on a base of
  1. A quiet band lifts its input to about 1.1, a band at nominal to
  1.35, a kick to about 1.86, so the pattern answers quiet music and
  stays legible loud. At depth 1 a band reading 0.6 or more pinned its
  input at 2.6, and loud music held every input at its extreme on every
  pattern (EMBER black; SPIRAL, CELLS and KALEIDO blown out). The rate
  routes are unchanged. `legacy6` keeps the reference's rotation parity
  but no longer reproduces its pattern drive: its pattern inputs sit at
  1 and are pushed at 0.35.
- **Other options.** 0.3 (quiet music barely differs from silence); 0.4
  (EMBER and SPIRAL blow out on kicks); 1, as the reference.
- **To reverse.** One constant (`routing.PATTERN_DEPTH`), then
  `uv run python -m hyperspace.preset` to regenerate the factory files:
  minutes.
- **Rough edge.** Your own presets were not touched: sixteen of the
  seventeen in Dan's snapshot (then `shared/dan-2026-10-04/presets/`,
  now in his library) still push at depth 1;
  with faces on, three would change visibly if re-saved (one SPIRAL, two
  PLASMA). Tuned on synthetic band levels.
- **Judge it.** Checks 132 and 137 — and whether to re-save yours at
  0.35.

### 107. The house presets' routes are generated from code

- **Built.** The eight house moods (big-blue-wave, ember-orbit,
  hex-engine, inverse-halo, plasma-heart, spiral-silk, strobe-cage,
  woven-lattice) get their routes from the generator, as the party
  presets do; their values and notes are still data. Before, their lane
  rows were data a test held equal to the code, so a change of depth
  would not have reached them. **Presets were a subsystem the brief
  called settled**; this changes how eight factory files are made, not
  what a preset is or how one loads.
- **Other option.** Leave them as data and edit the eight files' six
  rows by hand.
- **To reverse.** Take the eight out of `FACTORY_PRESETS`, an hour.
- **Judge it.** Check 132.

### 108. Macro candidates in `shared/`; per-band gain as depth subscribers

- **Superseded in part by row 109** (plan 25): the repo's `shared/`
  folder and its install tool are gone. The four candidates are in the
  owner's library, and `tests/fixtures/macro-candidates/` keeps a copy
  for the tests; the macros themselves still wait for checks 133–136.
- **Built.** Four presets of macros to audition — MACRO PERFORMANCE,
  MACRO STREAMS, MACRO INTENSITY, MACRO BREAKDOWN DROP — in
  `shared/plan-22-macro-candidates/`, installed with
  `uv run python tools/shared_presets.py install shared/plan-22-macro-candidates`.
  Each shares one scene, puts its macros on device knobs D1–D8, and rests
  them at noon (BREAKDOWN and DROP at zero) on the file's own values. A
  band's gain in a macro is a depth subscriber on that band's routes.
  [`plans/22-macro-candidates.md`](plans/22-macro-candidates.md) says
  what each macro is meant to do. None was judged by the build. After
  B3 their pattern routes sit at 0.35 with the multipliers unchanged.
- **Other options.** Factory presets (the factory list and its bank
  are pinned at 23); base subscribers on the analyzer's band gains,
  attack and gate (session params: dropped at load, D9 — so TIGHT cannot
  reach attack or gate); a separate scene per file.
- **To reverse.** Delete the folder; keep the ones you like by saving
  them as your own.
- **Rough edge.** The PRESETS page does not show a preset's note, so
  the intents live in the files and the sheet. MACRO INTENSITY's 1 and
  3, and MACRO BREAKDOWN DROP's 1 and 2/3, share bases: the last turned
  wins. INTENSITY × DROP stacks to about ×4 on the lane routes. Ranges
  that mirror round noon give odd ends (speed 0.12 → 0.75, 4D depth 6 →
  1.51, zoom 0.7 → 2.41).
- **Judge it.** Checks 133–136: say which macros to keep, and as what.

## The shared library (plan 25)

### 109. Presets shared through a cloud-synced folder (D1–D8)

- **Decided by the owner on 2026-10-14** (plan 25's kickoff,
  [`plans/25-shared-library.md`](plans/25-shared-library.md)), and built:
  - D1: presets are shared through a cloud-synced folder (Dropbox, iCloud
    Drive, Google Drive, Syncthing — the code does not care which), not
    git.
  - D2: `[library] path` points the library — `presets/`, `projects/`,
    every module-preset group folder, `hidden.json`, `trash/` — at it.
  - D3: machine files stay in the home: `config.toml`, `bindings.json`
    and its `.bak-*`, `hands.json`, `windows.json`, `imgui.ini`,
    `last_show`, logs, `weights/`.
  - D4: `path` unset or `""` is exactly the old behaviour.
  - D5: a folder named but missing at launch is never created and never
    silently replaced: a loud warning, every write refused, only the
    factory listed; fix it and restart.
  - D6: the home-as-git module and its config switch, and the repo's `shared/` folder
    with its install tool are removed (row 78 and row 108's folder are
    superseded). Both stay in git history at `6473fda`.
  - D7: factory presets and `hidden.json` behave as before.
  - D8: `tools/move_library.py` copies an existing library into the
    shared folder once and never overwrites.
- **Also built.** Library writes are atomic (temp file, then replace),
  and a cloud client's conflict copy is listed under its own file stem.
- **Judge it.** Checks 139–143.

## The party fixes (plan 24)

Built in plan 24's run on 2026-10-14
([`plans/24-party-fixes.md`](plans/24-party-fixes.md)), on
`plan-24-26-27-integration` until the owner merges it. The owner's own
decisions for this plan (17–21, 23 and 24 of the launch prompt) are in
[`DECISIONS.md`](DECISIONS.md) with Who "owner"; these rows are what the
build chose where those left a choice open. No preset was edited or
added: every proof is a fixture under `tests/fixtures/`.

### 110. SAVE is track 8's clip stop, a held button on `desk.save`

- **Built.** Track 8's clip stop (G6·8) is the desk's **SAVE**: hold it
  and tap a bank pad (clip rows 1, 4, 5) to save the live state into that
  pad's slot. It is one invariant row (`apc40.SAVE`), the same on both
  layers, lit while held: a `momentary` row on a session param,
  `desk.save` ("Save", never saved, not modulatable). So the on-screen
  desk draws it, and a device that takes the adapter over carries it as
  a port. A reconnect lets go of it, so a note-off lost to a pulled cable
  cannot turn the next pad press into a save. It can never be latched:
  it is no desk target on ROUTING, "Learn desk" and "Learn pad" refuse it
  in words, and any row on it that is not `momentary` is refused (a
  hand-edited `bindings.json` loses such a row with a note and is written
  back once). A `bindings.json` gains the row once, only where nothing
  already uses clip stop 8; where the owner's row holds it, every launch
  says "SAVE not added: note:7:52 is yours (…)" on stderr and the SYSTEM
  page, and the file is not touched. Clip stops 1–7 stay free for Learn.
- **Other options.** Another free button (the working plan's open
  question): a clip stop is the nearest free button to the pads, and
  track 8's is at the end of the row. SAVE as a modifier read inside the
  adapter, with no param: the panel could not show it.
- **To reverse.** One row in `apc40.DEFAULT_MAP` and one in
  `routing.APC_NEW_ROWS` (move it to another note), or drop both.
- **Rough edge.** An owner's row on clip stop 8 in a preset's desk is
  dropped at load with D6's note. Never on the APC40.
- **Judge it.** Check 148.

### 111. The two-handed save names the new preset from the loaded one, and blinks the pad

- **Built.** On a filled pad the new preset is named from the **loaded**
  preset, as `save_new` names them (TRIP → TRIP 2, counted against every
  file, listed name and bank name), not from the preset the slot held.
  The footer says "saved TRIP 3 → slot 11 (TRIP 2 is still in the preset
  list)". The tapped pad blinks for 1.5 s (`midi.BLINK_S`) and then
  shows green as the loaded slot. A save the show file could not take
  blinks nothing and the desk log says "did not land there"; the preset
  is still saved and in the list. A tap under SAVE never loads the pad
  and never starts its hold.
- **Other options.** Name it from the slot's old preset (FIELD → FIELD 2
  on F3): reads well when that preset was loaded, but differs from every
  other save on the desk.
- **To reverse.** One line in `library.Project._save_new` (the name
  passed to `next_name`).
- **Rough edge.** The blink velocity (`apc40.blink_of`) has never been
  seen on the mk1.
- **Judge it.** Check 148.

### 112. Every load lets go of every fader the preset binds, and darkens the whole desk (row 44 changed)

- **Built.** A load re-arms soft pickup on **every fader the new preset's
  desk binds** (a preset-layer row), whether or not the load moved its
  param, so each picks up from the new preset the same way every time. A
  fresh row starts from where its fader physically is (the last value it
  sent, `MidiIO._hw`), so a fader already on the value catches on its
  first move. The session's faders (the crossfader's dim, MASTER, and the
  audio strip under SHIFT) keep row 44's rule, since a preset never moves
  their params (D9). On every load and at power-up, every control of the
  APC40's layout that no active row draws is sent dark
  (`MidiIO._dark_desk`), not only the controls a row once named.
- **Other options.** Row 44 as it was. The dark pass on SHIFT as well
  (about a hundred more messages per press).
- **To reverse.** One condition (`b.layer == "preset"`) and one call
  (`_dark_desk`) in `MidiIO.redraw`.
- **Rough edge.** A fader nobody has moved since launch or a reconnect
  has no position: its first move after a load must land within the
  pickup tolerance, or wait to cross the value. Whether the mk1 keeps up
  with the dark pass (about 100 messages a load) is unknown.
- **Judge it.** Checks 150 and 153 (and 55 (e) for the session faders).

### 113. The factory files keep the four toggle rows; a load drops them quietly

- **Built.** No file under `hyperspace/library/` changed in this run
  (decision 23), so the factory presets still carry the four render
  toggle rows on scene launch 1–4. The generator keeps writing them
  (`preset.file_desk` is the fresh desk plus those rows). A load drops
  those four exact rows **without a note** (`routing.TOGGLE_DESK_ROWS`,
  part of `RETIRED_DESK_ROWS`), as plan 19 did with the shape pads,
  because the session's invariant rows do the job; an owner's other row
  on scene launch 1–4 drops **with** D6's note. The preset is not dirty
  after the load.
- **Other options.** Regenerate the factory files without the rows
  (forbidden this run). Drop them with a note (twenty-three factory
  presets would each say so on every load).
- **To reverse.** After the creative pass, point `Factory.desk` and
  `write_factory` at `fresh_desk` and run `python -m hyperspace.preset`.
- **Rough edge.** Until then the factory files and the loaded desk differ
  by four rows.
- **Judge it.** Check 149.

### 114. The desk log: the last twenty presses on the SYSTEM page

- **Built.** The SYSTEM page, under **midi**, has a fold "desk log — the
  last N presses". Each line has the time, the control in the desk's
  words ("G1·5 (clip 1·5)"), what the press did ("Preset → TRIP",
  "saved into slot 15: TRIP 2", "nothing (no row on the preset layer)",
  "held: nothing saved (a filled pad only loads)") and the layer it was
  read on (preset, global, or both for an invariant control). Newest
  first, twenty kept (`midi.DESK_LOG_SIZE`). Button presses, holds that
  fired and two-handed saves are logged; knob and fader moves and
  releases are not.
- **Other options.** Log knob moves too, collapsed per control; show it
  on ROUTING; write it to a file.
- **To reverse.** `midi.DeskLog` and `Panel._desk_log`.
- **Rough edge.** In memory only, lost at a restart. With no APC40 there
  is no log.
- **Judge it.** Check 151.

### 115. The band audio strip is on the SHIFT-layer faders, not the knobs (amends D6)

- **Built.** With SHIFT latched, track faders S1–S6 are the six bands'
  post-drive, S7 `master.dyn` and S8 `master.trim` (`apc40.SHIFT_FADERS`,
  global-layer rows). With SHIFT up, S1–S8 are the loaded preset's.
  MASTER and the crossfader stay invariant.
- **Other options.** The SHIFT-layer track knobs 6–8 and the device
  knobs: endless, so no pickup, but eight audio params do not fit on the
  free knobs.
- **To reverse.** Drop `layer=G` from the eight rows, invert
  `routing.FADER_SHIFT_ROWS`, regenerate `bindings.default.json`.
- **Rough edge.** Under SHIFT a fader rarely sits where its band is, so
  the first pull after a latch does nothing until it reaches the value.
- **Judge it.** Check 153.

### 116. A layer switch re-arms every layered fader from where it physically is

- **Built.** One fader now serves two params. On every SHIFT latch or
  unlatch, each layered fader row takes the fader's last physical
  position and is caught only when its param already sits within the
  pickup tolerance (1.5/127); otherwise it waits to cross the value. A
  fader moved on one layer never jumps the other layer's param. On a
  load, row 112's rule decides.
- **Other options.** Keep each row's catch across the switch (the fader
  then jumps the other layer's param on its first move); uncatch with no
  position (a fader already on the value would need a crossing).
- **To reverse.** The `switch` block in `MidiIO.redraw`.
- **Rough edge.** A fader not moved since launch or a reconnect has no
  position and catches only on a move that lands on the value; a stale
  position is never taken for a crossing.
- **Judge it.** Check 153.

### 117. Lines and points opacity: `view.lines_alpha`, `view.points_alpha`

- **Built.** Two 0–1 params in the `view` group (performance, saved in
  presets, modulatable), both 1 by default. Each multiplies the alpha
  `draw_scene` already gives an edge or a point, after the existing
  floor, so 1 is the picture as it was and 0 takes the layer away. A pair
  of sliders on the VIEW page ("Points opacity", "Lines opacity"). No
  desk row and no preset value; a preset that lacks them loads them at 1.
- **Other options.** Ids `view.lines.opacity`; an opacity uniform in the
  shaders; the factor before the floor (0 would leave a faint layer).
- **To reverse.** The two params, the two `ViewState` fields, the two
  factors in `render.py`, the slider row.
- **Rough edge.** The render graph's rewrite of `draw_scene` must keep
  the two factors.
- **Judge it.** Check 154.

### 118. Fader rows in a preset's desk: `preset.track_fader` and `knob_desk(…, faders=)`

- **Built.** `track_fader(k, target)` is track fader k on the preset
  layer (absolute, soft pickup, no light). `knob_desk(targets,
  faders=())` puts `faders[k]` on fader k + 1, None leaving it dark. The
  default adds nothing, so every factory desk is as it was; `fresh_desk`
  and `file_desk` bind no fader. Fader rows load, save and redraw like
  knob rows: nothing new in the file format. A fader on the preset layer
  is learnable like a knob.
- **Other options.** A separate `fader_desk(...)` beside `knob_desk`.
- **To reverse.** The helper and the parameter.
- **Rough edge.** No factory preset uses it (decision 23): every one
  leaves S1–S8 dark until the owner authors fader sets.
- **Judge it.** Check 152.

### 119. An older `bindings.json` moves its eight fader rows to SHIFT once, with a backup

- **Built.** On load, `routing.remap_factory` gives each exact old
  invariant fader row (`FADER_SHIFT_ROWS`) the global layer, with the
  note "moved cc:k:7 → band.k.post to the SHIFT layer (…)". The file is
  backed up (`bindings.json.bak-v3`) and written back once; the next
  load is quiet. A fader row the owner changed stays invariant, so that
  fader stays the owner's on both layers, and a preset row on it drops
  with D6's note.
- **Other options.** Drop the old rows and add new ones (two changes in
  the note, and an owner's flags lost).
- **To reverse.** `FADER_SHIFT_ROWS` and its branch in `remap_factory`.
- **Rough edge.** The first remap that changes only a row's layer, so
  its note says "moved", not "remapped".
- **Judge it.** Check 153 (the first launch's SYSTEM line).

### 120. What makes a desk control "dead": `learn.cannot_show`

- **Built.** A control is **dead** when the loaded preset has a row on it
  but cannot show that row's param, read from the preset's bases (not
  the live frame): the pattern params and `view.pattern_mix` with the
  faces off; `view.bmp_*` with the faces off or no bitmap file; points or
  lines opacity with that layer off; `fx.mix` with the effects off; an
  effect's param with the effects or that effect off; `dream.*` with the
  look-back off; `rot.rate.*` and `view.plane.*` with rotation off; a
  param the registry lacks. Today this makes K7 (`view.bmp_alpha`) dead
  on every factory preset, and K4 / D4 dead where the faces are off.
- **Other options.** Judge the live frame (could not be committed); more
  groups (zero instances, a dream knob at mix 0, an unread LFO); no
  bitmap rule (K7 would read as mapped).
- **To reverse.** Edit `learn.cannot_show` and rerun
  `tools/desk_coverage.py`.
- **Rough edge.** The render toggles are invariant, so Faces is one
  button away: a pattern knob on a faces-off preset is "dead" until it
  is pressed.
- **Judge it.** Check 155.

### 121. The preset layer the coverage counts: 38 controls

- **Built.** D1–D8, K1–K8 and S1–S8, plus every other control the
  factory map gives a preset-layer row (grid motion G3·5–8, the planes
  G8·1–6, the view reset G5·9, the cue knob, ▲ ▼), less any control the
  session holds on both layers. A preset row on another control is
  listed apart.
- **Other options.** Every control the preset layer could take (about
  70: the bar out of reach); only the three strips (24).
- **To reverse.** `layer_controls` in `tools/desk_coverage.py`.
- **Rough edge.** The set comes from the factory session, not the
  owner's `bindings.json`.
- **Judge it.** Check 155.

### 122. Desk templates: `hyperspace.desk/1` files in the `desk` group; a preset names one and keeps its overrides

- **Built.** A template is `<library>/desk/<slug>.json`:
  `{"schema": "hyperspace.desk/1", "name", "note"?, "desk": [rows]}`.
  The factory has no templates (the folder `hyperspace/library/desk/`
  need not exist: the group lists none without it); the owner's live in the library, so a shared
  `[library] path` shares them. A preset names one with `"desk_template":
  "<name>"`, and its `"desk"` then holds only overrides: an override row
  replaces every template row on the same control, and a dark row
  (`{"source": …, "dark": true}`) leaves a template control unmapped. A
  load expands it (template rows not overridden, then the overrides); a
  save writes the name plus the live rows that differ from the template
  **as the load read it**, so a template edited on disk never turns into
  overrides that undo it. A missing template is a note and the overrides
  alone. A preset with no `desk_template` takes exactly the old path.
  Templates are never applied as module presets of the `desk` param
  group.
- **Other options.** A folder named apart (`desk-templates/`); a
  `Library.kind`; overrides keyed by glyph; the whole expanded desk
  saved (a template fix would then not reach its presets).
- **To reverse.** The template branch in `Presets.load_doc` and
  `_desk_part`, the helpers in `preset.py`, `Library.desk_template`. A
  preset naming a template would need its desk expanded first.
- **Rough edge.** No UI writes or edits a template. Editing one on disk
  does not re-apply a loaded preset: reload it. Two spellings of one
  knob (`cc:*:16`, `cc:0:16`) lose the any-channel one on a round trip.
  An older build ignores `desk_template` and refuses a dark row.
- **Judge it.** Check 156.

### 123. Click a control: this preset's params first, ranked

- **Built.** While a mappable control is picked, the desk lists this
  preset's params on its empty ground under the transport row
  (`ui_desk.OFFER`; a test proves it covers no control). `learn.ranked`
  orders them in four tiers: **routed** (a route or macro moves it),
  **moved** (its base is off the group default), **on** (its effect,
  the look-back, the faces, the points or the lines are on), **on the
  desk**. A dead param is never offered as one of the preset's own. A
  chip, "all params ▾" ("all ▾" on the small desk), opens a popup with
  the same list and a menu per group of the rest. A click maps the
  control there through `Learn.map_picked`, as a click on the page does.
- **Other options.** A popup that opens on the pick (it would block the
  second click plan 17 relies on); a block on the page; other tier
  orders.
- **To reverse.** Drop `_offer` from `ui_desk._body`.
- **Rough edge.** At the default window size the list is about
  107 × 79 px, five items at a time. The "on" tier includes an effect's
  `.blend`, `.order` and `.target`. The list is ranked at the moment of
  the pick.
- **Judge it.** Check 157.

### 124. The dance lanes go after the switches; `hands:` is a scheme of its own

- **Built.** Each hand gets eight `hand:` lanes — `curl.thumb` …
  `curl.pinky`, `spread`, `energy`, `flick` — after the eight pinch
  switches, so every older lane keeps its index (a saved `hand:9` still
  reads the same roll). `hands:gap` and `hands:twist` are a second
  scheme, `hands`, with its own vector, labels, rests (0, 0.5) and no
  gates. Only the pinches and the grab (row 132) are gates; a flick
  spikes and decays and is not one. The ROUTING page offers them by name
  ("hand R curl ind", "hands gap").
- **Other options.** The pair in the `hand` vector (`hand:both.gap`);
  the new lanes before the switches (every numeric `hand:<i>` past the
  axes would move).
- **To reverse.** The lane order is `addresses` and `Layout`; presets
  name lanes by name, so a reorder costs only numeric addresses.
- **Rough edge.** The hand tests that pinned 22 lanes now read 40 (with
  the grab).
- **Judge it.** Checks 158 and 162.

### 125. Curl is the summed bend of a finger's joints; spread is the index–pinky fan

- **Built.** `curl.<digit>`: the angles between each bone and the next,
  summed, 20° → 0 … 220° → 1 for a finger, 10° → 0 … 80° → 1 for the
  thumb. `spread`: the angle between the index's and the pinky's first
  bones in the palm's plane, 10° → 0 … 60° → 1; a finger bent down at the
  knuckle makes it 0 (a fist does not fan). Both slewed 0.05 s; both
  need the skeleton, and read nothing without one.
- **Other options.** The SDK's one grab number per hand; fingertip to
  palm distance (mixes curl with spread); tip-to-tip distance for spread.
- **To reverse.** Constants in `hands/core.py` (`CURL_RANGE`,
  `CURL_RANGE_FINGER`, `SPREAD_RANGE`, `SPREAD_MIN_FLAT`, `CURL_S`).
- **Rough edge.** Tuned on synthetic hands: a relaxed real hand may idle
  above 0 and a real fist may stop short of 1. A middle finger crossing
  is invisible to spread.
- **Judge it.** Checks 159 and 160.

### 126. Energy is the mean speed of the palm and the five tips, fast up, slow down

- **Built.** On each tracking frame the speed of the palm and each
  fingertip, averaged: 60 mm/s → 0 (above a still hand's jitter) …
  1000 mm/s → 1, then a slew with 0.06 s attack and 0.5 s decay, so a
  burst of dancing lingers. With no skeleton, the palm alone. A frame
  that measures no speed lets it fall.
- **Other options.** The peak speed (one finger dominates); the palm
  only; a longer window.
- **To reverse.** `ENERGY_RANGE`, `ENERGY_ATTACK_S`, `ENERGY_DECAY_S`,
  `SPEED_GAP_S`.
- **Rough edge.** The floor is a guess at the camera's jitter.
- **Judge it.** Check 159.

### 127. A flick is the fastest tip passing 1500 mm/s; it spikes and decays

- **Built.** Until a trigger kind exists, `hand:<side>.flick` is a lane:
  0 at rest; when the fastest fingertip (the palm with no skeleton)
  reaches 1500 mm/s it jumps to speed / 3000 mm/s (at most 1), holds the
  peak while the move lasts, then decays with τ = 0.15 s. No new hit
  until the speed falls under 700 mm/s; over 10000 mm/s is a tracking
  jump and ignored; a hand entering the box never flicks on its first
  frame.
- **Other options.** Acceleration (noisier); fingertips relative to the
  palm (a whole-hand snap would not count); a hold-then-drop shape.
- **To reverse.** `FLICK_ON`, `FLICK_OFF`, `FLICK_FULL`, `FLICK_CEILING`,
  `FLICK_DECAY_S`.
- **Rough edge.** Any fast move is a flick, so energy and flick fire
  together on big moves (closing a fist fast included).
- **Judge it.** Check 161.

### 128. Gap is the palms' distance; twist is the right hand's roll less the left's

- **Built.** `hands:gap`: 60 mm → 0 … 600 mm → 1. `hands:twist`: right
  roll − left roll, wrapped, ±90° → 0 … 1, so mirror-image hands (both
  palms down, a clap) read 0.5 and turning a wheel clockwise reads up.
  Both slewed 0.05 s; both read nothing unless both hands are in.
- **Other options.** The full relative rotation (loses direction); the
  roll difference in room terms (a clap would read ±180°).
- **To reverse.** `GAP_RANGE`, `TWIST_FULL`, `PAIR_S`, `PAIR_RESTS`.
- **Rough edge.** Twist reads roll only; past a quarter turn each way it
  wraps.
- **Judge it.** Check 162.

### 129. The dance sources and the grab have no settings, no DAW output and no hand Learn

- **Built.** None of the new hand sources is a registry param (no dead
  zone, curve, attack or rest of its own), none sends to the DAW port,
  and a hand Learn still lands only an axis: a dance source is picked on
  the ROUTING page (source combo), the grab as a row's gate there or
  from a param's "Gate: … ▸". A Learn made while holding a fist writes no
  grab gate (`held_gate` offers only a held pinch).
- **Other options.** Each as a full axis with settings, MIDI out and
  Learn; grab thresholds as `hands.*` params; a held grab offered by
  `held_gate`, so a fist and a turn would write a grab mapping in one
  gesture.
- **To reverse.** Additive each.
- **Rough edge.** Their feel is fixed in code; a route's own motion
  (route motion, PR #162) can still shape one per row. A grab mapping
  takes three ROUTING-page edits per row.
- **Judge it.** Checks 158 and 164.

### 130. The HANDS page shows the dance sources in a column beside the axes, the grab on each curl row

- **Built.** A 220 px column right of the axis rows (which are that much
  shorter): per hand five curl bars ending in "grab ●" / "grab ○", then
  spread, energy and flick; then gap and twist (with a middle tick).
  Hollow while a source reads nothing; hover for the address and value,
  and on the grab the live fist level against its two thresholds. Beside
  the rows, not under them: the page is already the window's height.
- **Other options.** A folded header (still one line too many); the grab
  beside the pinch switches (hidden when they are off, and taller than
  the box).
- **To reverse.** `panel._dance`, `panel._grab`, two lines in `_axes`.
- **Rough edge.** The bars are small (16 px).
- **Judge it.** Checks 158 and 163.

### 131. The grab: the four fingers' mean curl, closing past 0.65, letting go under 0.45

- **Built.** `hand:<side>.grab` is 1 while the hand is a fist: the mean
  of the index, middle, ring and pinky raw curls (the thumb left out, so
  a fist with the thumb out or tucked both count), through the pinches'
  `Gate`: it closes once the fist passes 0.65, opens only under 0.45,
  and an edge must hold 0.05 s. A hand leaving the box drops it at once.
  With no skeleton it never closes.
- **Other options.** The SDK's grab number; the minimum of the four
  curls (one badly tracked finger would stop a fist); the smoothed
  curls (more lag).
- **To reverse.** `GRAB_FINGERS`, `GRAB_CLOSE`, `GRAB_OPEN`,
  `GRAB_HOLD_S`, `fist`.
- **Rough edge.** Tuned on synthetic hands; 0.65 is low on purpose
  because a real fist may not read 1. Closing fast also fires flick and
  energy.
- **Judge it.** Checks 163 and 164.

### 132. The grab lanes go after the dance lanes; the grab gates after the pinches

- **Built.** `hand:left.grab` and `hand:right.grab` ("L grab", "R grab")
  come after the sixteen dance lanes, so the `hand` vector is 40 lanes
  and no older lane moves. The published gates are the eight pinches,
  then the two grabs, so the ROUTING gate combo and "Gate: … ▸" offer
  them and a row reads "… positions while R grab". The grab lives in
  `HandsIO.grab`, not the pinches' dict, so the ghost hands and the probe
  read what they did.
- **Other options.** The grab beside the pinches (moves every dance lane).
- **To reverse.** `grab_name`, the `grab` map in `Layout`, `HandsIO.grab`.
- **Rough edge.** None known.
- **Judge it.** Check 163.

### 133. "Hands on the main projection" is the SETUP.md example, not a file in the home

- **Built.** Each output's `hands` switch already defaults on, so the
  projector shows the hands with no edit. SETUP.md's projector entry
  says `hands = true` outright, with a sentence. The rig's own
  `~/Hyperspace/config.toml.rig` is the owner's file, outside the repo,
  and this run never touches the home: the owner adds the line there.
- **Other options.** A `config.toml.rig` example in the repo.
- **To reverse.** Delete the line and the sentence.
- **Rough edge.** It changes nothing until something says
  `hands = false`.
- **Judge it.** Check 165.

### 134. The palette's ids are `fx.palette.*`, not `palette.*`

- **Built.** The palette fold is an effect file,
  `shaders/fx/palette.glsl`, so its params are `fx.palette.*`, it is a
  chip on the FX page, and the desk, hands, LFOs and bands reach it as
  any effect.
- **Other options.** A core `palette.*` group (the working plan's ids).
- **To reverse.** Rename the ids (cheap while no preset uses them).
- **Rough edge.** The ids differ from the working plan's.
- **Judge it.** Check 166.

### 135. A new `// @mix` directive: the palette starts at mix 0

- **Built.** `fx.py` reads `// @mix <value>` as an effect's default
  wet/dry (1 when absent, so every other effect is as it was). The
  palette says `@mix 0`: switching it on changes nothing until its mix is
  raised.
- **Other options.** Mix 1 and neutral fold defaults: the fold at width
  360 is not the identity, so none exists.
- **To reverse.** Delete the directive; "on" would then fold the picture.
- **Rough edge.** "On" with no change can look broken; the tip says "Mix
  0 leaves the picture alone".
- **Judge it.** Check 166.

### 136. The palette's params: `mode` 0 / 1, an `anchors` count, twelve anchor values

- **Built.** `mode` is a whole number, 0 (fold) or 1 (gradient map),
  because the `@param` form has no list. The ramp is up to four anchor
  colours, each `a<n>_hue` (degrees, wraps), `_sat` and `_val`, and
  `anchors` (2–4) says how many are used, dark to light, evenly spaced
  on brightness. The default is a grey ramp (values 0, 0.333, 0.667, 1).
- **Other options.** RGB triples; one saturation for all (8 params); a
  list form added to `fx.py`.
- **To reverse.** Rename the params (breaks saved palettes).
- **Rough edge.** Twenty params of its own.
- **Judge it.** Checks 166 and 167.

### 137. The palette is `@order 95`, last but with room after it

- **Built.** The palette sits after every other effect (the next highest
  factory order is 85), and a chip dragged to the end needs only one
  order rewritten.
- **Other options.** 99.
- **To reverse.** The header line.
- **Judge it.** — (tests only).

### 138. The fold is a triangle over the absolute hue wheel; saturation and value are linear

- **Built.** Red folds to one end of the slice and cyan to the other,
  centred on `centre`, `width` wide: neighbouring hues stay neighbours,
  no seam. Saturation and value are rescaled linearly into `sat_lo`–
  `sat_hi` and `val_lo`–`val_hi`, so a raised `val_lo` lifts black to
  grey, and a grey pixel (hue 0) lands on the slice's edge once `sat_lo`
  is above 0. On a see-through ground (overlay, faces) the result is
  scaled by the pixel's alpha, so a raised floor never lights what was
  clear.
- **Other options.** A fold relative to the picture's mean hue; a gamma
  on value.
- **To reverse.** A few lines of `palette.glsl`.
- **Rough edge.** Never seen on a projector.
- **Judge it.** Check 166.

### 139. The FX page is repacked to fit a thirteenth chip and the palette's strip

- **Built.** Three chips a row as before (row 45); the gaps around the
  chips and under the strip header are gone, which wins back the room a
  fifth row of chips needs. The strip packs `_lo`/`_hi` and
  `_hue`/`_sat`/`_val` params onto one row by name (`ui_fx.strip_rows`),
  and the palette shows only the open mode's rows
  (`ui_fx.HIDDEN_BY_MODE`); the hidden params stay declared and routable.
- **Other options.** Four chips a row (names cut); an `@group` tag in
  `fx.py`.
- **To reverse.** Restore the spacing; delete `strip_rows`.
- **Rough edge.** The page fits with 7 px to spare at worst; the chips
  sit closer to the status lines; a route on a hidden row cannot be seen
  on the strip until the mode flips.
- **Judge it.** Check 167.

## The device registry (plan 27)

Built in plan 27's run on 2026-10-14
([`plans/27-device-registry.md`](plans/27-device-registry.md)), on
`plan-24-26-27-integration` until the owner merges it. The owner's own
decisions for this plan (10–14 and 16 of the launch prompt: the
registry's shape, roles not serials, two input ports per param, values
and triggers, a device's layers, the processes) are in
[`DECISIONS.md`](DECISIONS.md) with Who "owner"; these rows are what the
build chose where those left a choice open — the `[[devices]]` keys, the
MIDI qualifier, the sink row, the OSC addresses and the cloud file among
them. No preset was edited or added.

### 140. `[[devices]]`: the rig's devices as a list of tables; the old tables translated

- **Built.** `config.toml` may list the rig's devices as `[[devices]]`
  tables, each with `role` (a name without `:`, unique), `kind` (`midi`,
  `gamepad`, `hands`, `bridge`, `midi-out`, `osc`, `cloud`), `enabled`
  (default true) and the kind's own keys — the keys the old `[midi]`,
  `[gamepad]`, `[hands]` and `[bridge]` tables hold, with the same
  defaults. **A config with no list keeps working unedited**: the four old
  tables become the equivalent entries at load, in today's poll order —
  `pad` (gamepad), `apc40` (midi; the profile's name), `leap` (hands),
  `bridge` — with one note per table the file holds ("config: [midi] is
  now a [[devices]] entry (role = 'apc40', kind = 'midi') — see
  config.py"), on stderr and the SYSTEM page. With a list, the list says
  and each old table is ignored with a note. The first entry of each old
  kind is folded back into its table, so `cfg["midi"]` (the binding
  file's profile) and `cfg["hands"]` (the hands setup) say what the entry
  says. An entry with a bad or duplicate role, or no kind, is dropped
  with a note; an `enabled` that is not true or false is true; an unknown
  kind is kept as an `error: unknown kind` line. `[dream]` stays a table:
  the worker has no sources and no sinks.
- **Other options.** A list only, the old tables an error (breaks every
  rig config, `config.toml.rig` included); translate silently (the file
  never catches up); roles `midi` / `gamepad` / `hands` instead of
  `apc40` / `pad` / `leap`.
- **To reverse.** `config._translate` and `config.DEVICE_TABLES`; the
  notes are strings.
- **Rough edge.** An un-renamed rig config prints a note per old table on
  every launch, by design. A list with no `hands` entry leaves the hands
  settings registered from the defaults, so the HANDS page says "tracker
  off".
- **Judge it.** Checks 168 and 169.

### 141. Today's devices keep their schemes behind their roles; two devices never feed one scheme

- **Changed in B6.** The registry claims (scheme, role), not scheme
  (row 210): a second **pad** is no longer refused — it opens and
  publishes under its role (`axis@p2`, `pad@p2:A`), so it still never
  feeds the first pad's key. The refusal stands for a kind that cannot
  qualify: a second **hands** device is `error: feeds 'hand', which leap
  already feeds — not opened` (row 213). A role listed twice is refused
  by the registry too. The rest of the row stands.
- **Built.** "The role is the scheme" holds for a *new* device (an OSC
  phone publishes `phone:x`). Today's four keep the schemes their rows
  already name: an entry's `role` names the device (the SYSTEM line, the
  notes, a MIDI row's qualifier) and the device class's `schemes` say
  which Router keys it publishes — `axis` / `pad` / `hat` (the pad),
  `hand` / `hands` (the hands), `ext` (the bridge), `cc` / `note` /
  `pitch` (MIDI) — so a preset names a scheme and every existing row is
  unchanged whatever the entry is called. `feeds` is the subset fed as
  continuous vectors. Every `Port` carries its `scheme` and `address`
  (`axis:LX`, `hand:right.roll`, `cc:0:48`), so plan 28 can build a cable
  from a port. A second **enabled** entry whose kind would feed a scheme
  an earlier enabled entry already feeds is refused — `error: feeds
  'axis', which pad already feeds — not opened`, one note naming both
  roles — and comes up when the first leaves the list. A kind that feeds
  nothing (MIDI: its messages are rows) is never refused, so two desks
  both open.
- **Other options.** The role as the scheme for today's devices too
  (every preset and `bindings.json` rewritten to `leap:right.roll`); let
  the last entry win silently (the Router's feed overwrites); refuse in
  `config` (which does not know a kind's schemes).
- **To reverse.** `Device.schemes` / `feeds` are class tuples;
  `RefusedDevice` and the `claimed` map in `devices.make` are twenty
  lines.
- **Rough edge.** A refused entry is an `error:` line, not `off`, so the
  reason shows.
- **Judge it.** Check 174.

### 142. The `Device` protocol: open, poll, learn, act, feed, send, close; one `Port`; four status words

- **Built.** `devices.Device` (a runtime-checkable protocol): `role`,
  `kind`, `schemes`, `feeds`, `layers`, `wants`, `status`, `last`,
  `sources`, `sinks`, `open()`, `poll(dt, now)`, `learn(learn) -> bool`,
  `act(router)`, `feed(router)`, `send(reg, analyzer)`, `close()`,
  `targets()`. One `Port` type — name, label, kind (`value`, `trigger`,
  or `cloud`), rest, bipolar, velocity, group, layer, scheme — is the
  node editor's description of a device (plan 28), with no second one.
  The registry's frame slots: the **scene-setter slot** runs each open
  device's `poll` (the hardware read; MIDI applies its rows here), then
  `learn` (an armed Learn is offered a moved axis or a pressed button),
  then `act` (the rest of the frame's rows: the pad's, an OSC device's
  hits); the **feed slot** runs `feed`; the **sink slot**, after
  `reg.apply`, runs `send`. Status is `connected`, `lost` (the hardware is
  not there; the device looks for it itself), `off` or `error: <why>`.
  The registry retries only an `open` that raised; a `lost` device
  reconnects on its own schedule and is never closed or reopened by the
  registry. A `poll` that raises skips that device's `learn` and `act`
  for the frame; its error stands until the next clean poll and the
  first error of the frame goes to the hot-reload toast.
- **Other options.** One `poll(dt, now, router, learn)` call (what
  `HandsIO.poll` is); a status enum.
- **To reverse.** The protocol is one class; the slots are three
  registry methods.
- **Rough edge.** `learn` and `act` are steps a device's user never sees;
  the hands complete a hand Learn inside their feed-slot call, MIDI
  inside its `poll`.
- **Judge it.** Check 170.

### 143. The devices own today's adapters; the hands' one call runs in the feed slot

- **Built.** `MidiDevice`, `PadDevice`, `hands.device.HandsDevice` and
  `BridgeDevice` own a `MidiIO`, `Pad`, `HandsIO` and `Bridge`, built in
  `open()` (each adapter module imported there, so `import
  hyperspace.app` imports none of `midi`, `bridge`, `dream`, `osc`,
  `leap`, `torch`, `pythonosc`). Those objects are still what the panel
  holds and the ghost renderer reads: a registry listener in `app.main`
  re-points `panel.midi`, `panel.pad`, `panel.hands` and
  `renderer.ghost.source` whenever the list changes. The hands device
  makes the instrument's one call, `HandsIO.poll(dt, learn, router)`, from
  the **feed** slot, so the hands' tracker read now runs after
  `output.apply`, the mouse and the audio step rather than before them;
  nothing in between reads the `hand` feed.
- **Other options.** Split `HandsIO.poll` so the read is in the
  scene-setter slot (a change to the liftable `hands/core.py`).
- **To reverse.** Call the hands from `poll`; a few lines.
- **Rough edge.** The hands device's status passes the tracker's own
  words through: an unplugged camera reads `error: no camera` and a
  stopped service `error: service lost` — though the Leap thread
  reconnects by itself — and only "connecting" or a tape not yet started
  reads `lost`.
- **Judge it.** Checks 168 and 180.

### 144. The registry: open behind the entry, retry a failed open on the Ports schedule, close last-listed-first

- **Built.** `DeviceRegistry` makes one device per checked entry (`off`
  for `enabled = false`: listed, never opened, its adapter never
  imported).
  `open_all` opens each; one whose `open` raises is `error: …`, said once
  on stderr and in the config notes in the old gates' words (`"hands:
  …"`), and tried again on the MIDI desk's schedule — every 2 s for five
  misses, then every 10 s (`devices.retry_after`, held equal to
  `midi.retry_after` by a test); the frame it opens it is polled and the
  listeners run. `close()` closes every device last listed first,
  best-effort; `Host.adapters == (devices, dream_io)` is the one close
  list for a quit and ⌘R, and the pad is on it now (`Pad.close` stops and
  joins its USB reader, at most 0.5 s).
- **Other options.** Each device retries itself (every device a clock of
  its own); close in list order.
- **To reverse.** The schedule is three constants; the close order one
  `reversed`.
- **Rough edge.** A device whose `poll` raises every frame (a hot-reload
  bug) is never closed and reopened: it stays red on its line and the
  toast until the file is fixed.
- **Judge it.** Checks 170, 171, 172 and 175.

### 145. `config.toml` is watched every 30 frames; only the device list is re-read; a bad edit keeps the old list

- **Built.** Every 30 frames (`devices.WATCH_FRAMES`, the shaders'
  cadence) the registry stats `<home>/config.toml`; when its mtime moved
  it re-reads the `[[devices]]` list only (`config.read_devices`). Any
  problem — a parse error, an entry that would be dropped — is one note
  ("config: [[devices]] not applied — … — the old list stands") and
  nothing changes. Otherwise an unchanged entry keeps its device, a
  changed one is closed and opened again ("devices: apc40 changed —
  reopened"), a new role opens ("added"), a role that left closes
  ("removed"), and the order becomes the list's. A file with no list
  re-reads as the old tables translated.
- **Other options.** Reload the whole config (the outputs, the library
  path and the windows are not hot-pluggable); apply the good entries of
  a partly bad edit.
- **To reverse.** `watch` / `apply`; `WATCH_FRAMES`.
- **Rough edge.** A changed entry is reopened whole: an edit to the
  `apc40` entry re-sends the power-up and redraws the desk. An editor
  that saves in two steps may land a parse error (a note) and then the
  good list.
- **Judge it.** Check 173.

### 146. The SYSTEM page: one line per device

- **Built.** A **devices** section above **midi**, one line per listed
  device in list order: `role · kind · status · n sources · last` —
  MIDI's `last` is the port, the binding count and the last message; the
  pad's road and USB name; the hands' last DAW message or tracker status;
  the bridge's port, encoding, lanes and sent count; a sink's starts with
  `n sinks` (row 160). `error: …` lines are in the warning colour, `lost`
  in the dimmed colour of a normal line. "no devices — [[devices]] in
  config.toml" for an empty list. The old MIDI and bridge lines are gone;
  the HANDS page keeps its own status.
- **Other options.** Keep the old lines beside the new ones.
- **To reverse.** `ui.device_lines` and `Panel._device_lines`.
- **Rough edge.** A bridge's line is long; `lost` is not a warning, so an
  unplugged desk does not stand out.
- **Judge it.** Check 168.

### 147. A second desk's rows are `cc@<role>:<ch>:<n>`; the unqualified rows are the desk the table was written for

- **Built.** Every `[[devices]]` MIDI entry is its own desk. One MIDI role
  reads the unqualified rows — every row in `bindings.json` and every
  preset written before plan 27 (`cc:0:48`, `note:0:98`, `pitch:0`), so
  nothing moves: the first MIDI entry whose `profile` is the binding
  table's (`bindings.json`'s `"profile"`, `apc40` by default), else the
  first MIDI entry listed (`DeviceRegistry.midi_roles`). Any other desk's
  rows carry its role after `@` on the kind: `cc@launch:0:21`,
  `note@launch:0:40`, `pitch@launch:3`. The qualifier adds no `:`, so
  everything that splits a source at its first `:` is untouched. Learn
  desk on the second desk writes the qualified form; ROUTING and the
  footer say "MIDI CC 21 ch1 on launch".
- **Other options.** `<role>:cc:<ch>:<n>` (adds a `:`); the role inside
  the channel field; every row qualified (rewrites every preset and
  `bindings.json`); "the first MIDI entry listed" without the profile
  test (a generic box listed above the APC40 would take its rows and
  SHIFT).
- **To reverse.** `routing.QUALIFIER`, `base_scheme`, `Binding.device` /
  `bare`, the table's `serves`: an hour; nothing on disk uses the form
  until a learn on a second desk.
- **Rough edge.** A hand-written `cc@apc40:…` (the owning role named)
  acts as that desk's but is a different control from its unqualified
  twin to `overlaps` and the invariant check. Two APC40-profile desks:
  the first listed owns the unqualified rows.
- **Judge it.** Checks 176 and 177.

### 148. SHIFT is the first desk's latch; every other desk has a layer of its own and no SHIFT

- **Built.** `Bindings.layer` stays the owning desk's layer, the one
  `desk.shift` reads and SHIFT toggles; every other MIDI role has its own
  in `Bindings.layers` (`layer_of(role)`, `set_layer(layer, role)`,
  `toggle_layer(role)`), the preset layer until something latches it.
  Learn's refusal on the global layer (D5) is per desk: with the APC40 on
  SHIFT a knob on the second desk still learns into the preset and its
  rows still act. A preset load drops **every** desk to the preset layer
  (D4); D12 holds per desk; each desk's latch changes are counted on
  their own (`layer_serial_of`), so the APC40's SHIFT re-arms the APC40's
  faders only (D7). `MidiDevice.layers` says what a desk exposes for plan
  28: `("preset", "global")` for the owning APC40, `("preset",)` for any
  other.
- **Other options.** One layer for every desk (the APC40's SHIFT would
  blank the second desk's preset rows); a latch param and a SHIFT row per
  APC40-profile desk (deferred: "a second desk has its own, or none").
- **To reverse.** `layers` / `layer_of` and the `role` argument on four
  methods.
- **Rough edge.** A second APC40 gets its power-up and the lights of its
  own rows but no SHIFT: its SHIFT button is an ordinary unmapped note.
- **Judge it.** Check 177.

### 149. The `generic` MIDI profile: plain CC, note and pitch, nothing sent back, a `port` required

- **Built.** `hyperspace/generic.py`, a profile beside `apc40.py`:
  `PORT_MATCH = None` (the entry must name its `port`; without one the
  line reads `error: ValueError: the generic profile matches no port by
  itself …`, never the first port that happens to be there), `FEEDBACK =
  False` (the device is sent nothing: no power-up, ring, LED or leave),
  every CC absolute with soft pickup, a note a toggle, pitch an absolute
  14-bit fader, no layout (its line counts 0 sources; the on-screen desk
  stays the APC40's), no factory rows. A `profile` the registry does not
  know is an error line ("no MIDI profile 'akai'; one of apc40,
  generic"). The entry's profile is the desk's: `bindings.json`'s
  `"profile"` only says which profile the file's unqualified rows were
  written for.
- **Other options.** Echo values back as CC (a box that echoes would
  loop); take the first port when none is named (would grab the APC40);
  separate "generic pads" and "generic CC" profiles.
- **To reverse.** One module, one `midi.PROFILES` entry, one gate in
  `MidiIO._send`.
- **Rough edge.** A relative encoder on a generic box learns as `abs`;
  change its op on ROUTING.
- **Judge it.** Check 176.

### 150. A continuous source is "not a row kind"; the registry says which schemes there are and in what order

- **Built.** `routing.LANE_SCHEMES`, `ui_routing.SOURCE_ORDER` and
  `learn.WANTS` are gone. A row's shape is judged by
  `routing.is_continuous(scheme)`: anything but the kinds the table
  dispatches itself (`ROW_SCHEMES`: `key`, `pad`, `hat`, `cc`, `note`,
  `pitch`). So a preset route on a device this rig lacks (`phone:x`,
  `wand1:tilt`) is a dormant performer, never dropped (decision 11).
  *Which* schemes exist and in what order a page offers them is the
  registry's, handed to the Router as an argument (`Router.use`):
  `continuous_schemes()` is `lane`, `lfo`, then each listed device's
  `feeds` in list order (an `off` device's too). The referee's row
  schemes are extended the same way (`DeviceRegistry.row_schemes`). With
  no registry (a bare router), `lane` and `lfo` then whatever has been
  fed.
- **Other options.** A module-level tuple the registry appends to;
  `is_performer` asking the registry (a `Binding` has no table); keep
  `SOURCE_ORDER`'s order (`hand` before `lfo`).
- **To reverse.** `is_continuous` back to a tuple test; `Router.schemes`
  back to a tuple: minutes each.
- **Rough edge.** A typo'd scheme in a preset route (`hnad:right.roll`)
  is kept as a dormant performer, not dropped with a note. The ROUTING
  combo now lists the LFOs before the hands and the pad.
- **Judge it.** Check 178.

### 151. What a Learn can wait for is each device's `wants`; "desk" is always there

- **Built.** `Device.wants`: a MIDI desk `("desk",)` (one want; whichever
  desk moves first completes it, and the row says which), the pad
  `("pad",)`, the hands `("hand:left", "hand:right")`, and by default a
  device that feeds, its role. `Learn.wants()` is `desk` (the on-screen
  desk completes it with no MIDI device at all) then the registry's, in
  list order, `off` devices included (the learn completes once the device
  is on); `Learn.arm` refuses a want not in it. The param menu keeps
  Learn desk, Learn hand ▸ and Learn pad on their old conditions and adds
  "Learn <role>" on a modulatable param for any other want (an OSC phone:
  "Learn phone"). With no registry, today's four (`learn.BARE_WANTS`).
- **Other options.** One want per MIDI role (`desk@launch`: you would
  have to say which desk before touching it); only open devices' wants.
- **To reverse.** One property per class, `DeviceRegistry.wants`,
  `Learn.wants`.
- **Rough edge.** The bridge feeds `ext` but has `wants = ()` (it has no
  `learn`), so no "Learn bridge" item is offered, on or off; fixed in the
  review pass. A new device's item completes only through that device's
  own `learn`.
- **Judge it.** Checks 178 and 186.

### 152. The pad is a device: it publishes its axes and runs the sticks' camera job itself

- **Built.** `gamepad.Pad` has `open()`, a `status` (`connected` /
  `lost`, never an error) and `publish(router)` (the `axis` names, labels
  and rests; `Router._publish_axes` is gone). The sticks' default camera
  job moved from `app.frame` to `gamepad.steer(pad, router, reg, dt)`,
  run by `PadDevice.act` right after the pad's rows: the same constants,
  the same `router.claimed("axis")` and the pad's feel through
  `router.felt` (`desk.pad.*`, unchanged on purpose). It now runs before
  the MIDI desk's rows in the scene-setter slot; both write the bases of
  independent params by relative moves.
- **Other options.** Keep the job in `app.frame`; run it in the device's
  `poll` (which is handed no router).
- **To reverse.** Move `steer`'s body back into `frame`; restore
  `_publish_axes`.
- **Rough edge.** A route on `axis:LX` added before the pad ever
  published is not "claimed" for that one frame (no pad, no job anyway).
- **Judge it.** Check 179.

### 153. The hands' device is `hands/device.py`; the kinds table looks it up lazily

- **Built.** `HandsDevice` lives in `hands/device.py`, a `devices.Base`
  subclass beside `hands/panel.py`, so `hands/core.py`, `signal.py` and
  `tape.py` still import nothing from the host and
  `tests/test_hands_boundary.py`'s host-reaching list is `["device.py",
  "panel.py"]`. Its `schemes` and `feeds` are `hand` and `hands`; its
  ports read every count from `Layout` (axes, switches, presence, dance
  under `hand`; gap and twist under `hands`), so plan 24's new lanes
  needed no edit. Because it imports `devices`, `devices.kinds()` imports
  it when asked (`devices.KINDS` and `devices.HandsDevice` read through a
  module `__getattr__`). `hotreload.MODULES` gains `hands.device` after
  `devices`.
- **Other options.** Duck-type the protocol without `Base`; import
  `hands.device` at the bottom of `devices.py` (a circular import).
- **To reverse.** Move the class back; `KINDS` a dict again.
- **Rough edge.** `devices.KINDS` is built on each access (cheap).
- **Judge it.** Check 180.

### 154. One knob per param per desk

- **Built.** A desk learn still replaces the param's previous knob on
  the same layer, but only on the **same desk**: learning
  `view.inst_amp` on the second desk leaves the APC40's knob on it alone.
- **Other options.** One knob per param across every desk (a learn on
  the second desk would silently unmap the APC40's).
- **To reverse.** One condition in `Bindings.bind`.
- **Rough edge.** Two knobs on two desks drive one param, last touch wins
  (scene-setters, as two rows always could).
- **Judge it.** Check 176.

### 155. The sink row: a param or a lane, sent to `<role>:<channel>`, in the session

- **Built.** A param routed *out* is one more row in the one table:
  `{"source": "param:view.bright", "target": "bridge:3", "op": "send"}`
  (`routing.SINK_OP`). Its source is `param:<id>` (the **effective**
  norm, base plus this frame's modulation, read after `reg.apply`),
  `lane:<i>` (as a route reads it, `lane / CEIL`) or `lane:*` (every
  analyzer lane from the row's channel on); its target is a device's sink
  port, `<role>:<channel>`. It is a **session** row (`bindings.json`:
  sinks are rig, D1 / D9), never a performer (no `Owned`, no Replace /
  Keep, the modulation pass never reads it) and never in a preset; the
  referee checks only its form (`sink_refusal`). What a sink sends is
  `routing.sink_values(rows, reg, analyzer)` over the enabled rows on its
  role; an explicit row wins its channel over a `lane:*`. A trigger, or
  an id the registry lacks, reads 0.
- **Other options.** A separate `sinks` list in `bindings.json`; the op
  named `sink` or `out`; the sink port as the source and the param as
  the target; sink rows in the preset.
- **To reverse.** `SINK_OP`, `Binding.is_sink`, `sink_refusal`,
  `sink_values`, `Bindings.sinks`, the referee's branch: an hour.
- **Rough edge.** A `lane:*` row's width is the live band layout's; a
  later explicit row hides the star's lane on its channel. A param's
  alias (`band.sel.*`) can be sent and follows the selection.
- **Judge it.** Checks 181 and 183.

### 156. `[bridge] send` becomes sink rows once, marked in `bindings.json`

- **Built.** When the registry is built, and whenever the list is
  re-applied, every **enabled** entry with a `send` list — the bridge's
  default `["lane:*"]` included — whose role has no sink row at all gets
  the list as rows (slot k → `<role>:<k>`; `lane:*` one row taking the
  default layout's 6 channels before the next entry), written to
  `bindings.json` with one note: "bindings: [bridge] send is now sink
  rows in bindings.json (lane:* → bridge:0, param:view.bright → bridge:6)
  — the rows say from here on; edit them on ROUTING (sinks)". The
  translation is marked done in `bindings.json` itself, `"sinks_seeded":
  ["bridge"]` (written only when non-empty, so a file with none is
  byte-identical): a role in it is never seeded again, so rows deleted on
  ROUTING never come back. An entry it cannot translate (`ext:3`) is its
  own note; an off bridge seeds nothing. A `Bridge` made on its own
  (tests, tools) still sends its `send` list.
- **Other options.** Translate on every launch (the key would beat the
  owner's ROUTING edits for ever); keep `send` as the truth and show it
  read-only; mark it done by consuming the config key.
- **To reverse.** `DeviceRegistry._seed_sinks` and
  `routing.sink_rows_from_send`.
- **Rough edge.** Editing `[bridge] send` after the first launch does
  nothing (remove the role from `"sinks_seeded"` to translate again). An
  entry after `lane:*` lands at channel 6 whatever the rig's band count,
  so a DAW mapping may need one move.
- **Judge it.** Check 182.

### 157. The hands' DAW out is a `midi-out` sink, `hands-daw`; `HandsIO` makes the messages and opens no port

- **Built.** `hands/core.py` no longer opens a MIDI port: `HandsIO.poll`
  makes the frame's DAW messages exactly as before (per-axis CC, 14-bit,
  pitch or pressure, presence and pinch notes, rate-limited, solo) and
  leaves them in `HandsIO.outbox` for a carrier (`HandsIO.carry`);
  `HandsIO.resync()` gives the notes that are on for a port that came
  back. The port moved to `bridge.OutPort`. The device is
  `devices.MidiOutDevice` (`kind = "midi-out"`): its `poll` looks for a
  lost port again and, on a reconnect, queues the resync before the
  hands' frame; its `send` (after `reg.apply`) sends the resync, the
  carried messages, then any sink rows on its role (encoded as the
  bridge's lanes). **`[hands] out` keeps working**: at load the first
  enabled hands entry whose `out` names a port gets an entry right after
  it — `role = "hands-daw"`, `kind = "midi-out"`, `port = <out>`,
  `carries = <hands role>` — unless the list already has a `midi-out`
  carrying that role; one note when the file wrote `out` itself, none for
  the default.
- **Other options.** Keep the port in `HandsIO` with the sink only owning
  it; move the whole DAW encoding out of `hands/` (it reads the axes'
  settings; a liftable instrument that makes its MIDI is more useful);
  send from the feed slot.
- **To reverse.** Put `_open` / `_send` and the reconnect fields back in
  `HandsIO`; drop `config._daw` and the kind.
- **Rough edge.** The messages leave a millisecond or so later than
  before, in the sink slot. A rig with the hands off gets no `hands-daw`
  entry until a live edit turns them on. Tools that build a `HandsIO`
  with no `out` no longer make a "Hyperspace Hands" port.
- **Judge it.** Checks 184 and 185.

### 158. "Learn sink ▸ <role>:<channel>" lands at once, in the session

- **Built.** A param's right-click menu has **Learn sink ▸**, listing
  every sink port the rig's devices offer (`bridge:3 · pitch ch4`), on
  any param but a trigger. A pick lands immediately — nothing on a sink
  moves to complete it — through `Learn.learn_sink`: the row `param:<id>
  → <port>` is added and `bindings.json` written now, with no undo step
  and no preset dirt (like Learn pad). It takes the port from whatever
  sent on it ("…; param:view.bright let go"); a param may go out on
  several ports. Never a Replace / Keep question. The menu's bound lines
  list the param's sink rows dim, and Unbind never removes them. ROUTING
  has a **sinks** section after the session's (a checkbox and a ×, both
  writing the file).
- **Other options.** Arm and wait like the other learns; a sink picker
  page; an undo step.
- **To reverse.** `Learn.learn_sink` / `sinks`, `ui.sink_items`, the menu
  block, `ui_routing.sinks`.
- **Rough edge.** An `off` sink offers no ports, so nothing can be
  learned onto it until it is on. A pitch-encoded sink lists sixteen
  ports.
- **Judge it.** Check 183.

### 159. The bridge is one device with two halves; `ext` publishes its labels and rests

- **Built.** `BridgeDevice.poll` looks for its ports again (scene-setter
  slot); `feed` receives the inbound lanes as `ext` and publishes their
  labels ("ext 0" …) and rests (0); `send`, after `reg.apply`, sends the
  sink rows on its role through `bridge.Sender` (per channel: quantise,
  change-gate, rate-limit, encode), shared with `midi-out`. So a sent
  param is this frame's effective value, no longer a frame behind, and
  `ui_routing.N_EXT` is gone: the ROUTING combo offers the lanes the
  bridge publishes (and, for a scheme nobody publishes, up to the highest
  lane a row names).
- **Other options.** Labels as the wire ("pitch ch4"), which would change
  every `ext` route's words.
- **To reverse.** `Bridge.publish` and one line in the ROUTING combo.
- **Rough edge.** The combo reads "ext ext 0" (scheme, then label), as
  the LFOs read "lfo LFO 1".
- **Judge it.** Checks 181 and 182.

### 160. A sink's SYSTEM line starts its last part with `n sinks`

- **Built.** A device with sink ports shows the number of **enabled**
  sink rows on its role first: `bridge · bridge · connected · 16 sources
  · 2 sinks · IAC Driver Bus 1 · pitch, 16 lanes · 41 sent`; `hands-daw ·
  midi-out · connected · 0 sources · 0 sinks · Hyperspace Hands · leap's
  DAW out · cc 102 = 64 ch16`.
- **Other options.** A sixth field on every line; counting sink ports
  (sixteen on any pitch bridge, saying nothing).
- **To reverse.** Four lines in `DeviceRegistry.lines`.
- **Rough edge.** `hands-daw` reads `0 sinks` while it carries the hands
  (the words after it say so).
- **Judge it.** Checks 182 and 184.

### 161. An OSC device's role is its scheme; an address is a source name; its hits are rows under the same scheme

- **Built.** `kind = "osc"` with `role = "phone"` feeds the scheme
  `phone`: `axes = ["/x", "/y"]` are `phone:x`, `phone:y` (the address
  without its leading `/`; a deeper path kept, `/1/fader3` →
  `phone:1/fader3`), published with names, labels and rests, so a route
  names them like `hand:right.roll` and ROUTING and "Learn phone" offer
  them. `hits = ["/hit"]` are triggers under the **same** scheme
  (`phone:hit`), delivered as rows like a pad button's. A device says
  which schemes it delivers rows under (`Base.rows`) and what an entry
  would publish before it is made (`Base.publishes`), so a second feeder
  of `phone` is refused and an `off` OSC entry still lists its scheme (a
  row on it waits). A role that is a row kind or a built-in scheme
  (`key`, `pad`, `hat`, `cc`, `note`, `pitch`, `lane`, `lfo`, `cloud`) is
  an error line on open.
- **Other options.** `osc:<role>.<name>` (the launch prompt's text: one
  `osc` scheme for every OSC device, so two phones would share one
  vector); hits under a scheme of their own (`hit@phone:…`: a Learn armed
  for `phone` could not take a hit); hits as a fed 0/1 lane (no velocity,
  against decision 13).
- **To reverse.** `OscDevice.publishes` / `rows` and the read in
  `DeviceRegistry.row_schemes`: an hour.
- **Rough edge.** Because `phone` is fed and a row scheme, the referee
  accepts any op on a `phone:` row. A hit row in `bindings.json` waits
  while its device is not listed; re-enabling it on ROUTING then is
  refused ("'fire' is not an op for a phone source") until the phone is
  listed (even off).
- **Judge it.** Checks 186 and 187.

### 162. OSC values: the first number, the entry's range onto 0–1; nothing until heard; held while lost

- **Built.** An axis's value is the message's first number (a bool, a
  string or a NaN is skipped) — only the first: an XY pad's second value
  is not read — mapped from `range` (default `[0, 1]`) onto 0–1 and
  clamped. An axis no message has reached reads NaN, so its routes stay
  dormant and nothing moves at launch. The device is `connected` while
  any message arrived within `timeout` (5 s), `lost` before the first and
  after a silence; while lost the axes **hold** their last values (`hold
  = true`: a phone app sends only on change, so a fader left alone must
  not snap back), and `hold = false` lets the routes go. Closing the
  device takes its scheme off the router (vector, labels, names, rests).
  A `timeout`, `range` or `rest` of the wrong kind is an error line.
- **Other options.** Let routes go when lost, always; a 2 s timeout (the
  line would flicker between touches); the rest instead of NaN before the
  first message (a `position` route would move its param at launch).
- **To reverse.** `TIMEOUT_S`, `hold`, the NaN fill: minutes.
- **Rough edge.** With `hold = true` a phone that leaves the network
  leaves its routes where they were (the line says `lost`). An app that
  streams continuously is never `lost`.
- **Judge it.** Check 188.

### 163. An OSC hit: its velocity is the first number; a press is a velocity above 0

- **Built.** A hit's velocity is the message's first number clamped to
  0–1 (`range` is the axes' only), 1 when the message has none. Its rows
  act as a pad button's when the velocity is above 0 (`fire`, `toggle`,
  `step`, `set`); `abs` lands the velocity itself; `momentary` holds a
  toggle while the velocity is above 0 and lets go at 0; `hold` does
  nothing (a hit has no duration). A Learn armed for the role takes the
  next hit above 0 as a button row in `bindings.json`
  (`Learn.learn_pad_button`, as a pad button) and holds that frame's rows
  back; else the first axis moved 0.25 from its rest as a route.
- **Other options.** Velocity on 0–127 like MIDI; hit rows in the
  preset; a timed `hold`.
- **To reverse.** `osc.fire`.
- **Rough edge.** A velocity above 1 clamps; a learned step on a fader
  always steps up.
- **Judge it.** Check 187.

### 164. The OSC socket is read in `poll`, non-blocking, with no thread; UDP `0.0.0.0:9000` by default

- **Built.** `osc.Server` binds a UDP socket on the entry's `host:port`
  (every interface by default, so a phone on the LAN reaches it, port
  9000) and the device's `poll` reads every datagram waiting, at most 512
  a frame; `pythonosc` parses each (a bundle's messages in order), and a
  datagram that is not OSC is counted on the line ("… · 3 not OSC"). A
  port another program holds is an error line and one note, retried on
  the registry's schedule. `pythonosc` is imported only in `Server`;
  `hyperspace.osc` itself is imported whenever the registry looks a kind
  up, so an `off` OSC entry still lists its scheme.
- **Other options.** `pythonosc`'s threading server and a dispatcher (a
  thread, a lock and a queue per device, and tests that race it); import
  `osc.py` only when an entry names the kind.
- **To reverse.** `Server` is forty lines.
- **Rough edge.** macOS asks once whether Python may accept incoming
  connections the first time it binds `0.0.0.0`; denied, nothing ever
  arrives and the line stays `lost`.
- **Judge it.** Checks 186 and 189.

### 165. `devices.PointCloud`: a read-only N×3 float32 buffer, the frame clock's time, a counting frame id, bounds, optional colours

- **Built.** `PointCloud(points, t, frame, colors=None)`, frozen:
  `points` N×3 float32, C-contiguous and read-only (`ctx.buffer(points)`
  uploads it as it is; a caller's writeable array is copied), `t` the
  frame clock's `now` when it was published, `frame` an id counting up
  from 0 while the device is open (a reader uploads only when it moved),
  `bounds` a read-only 2×3 box (zeros for an empty cloud), `colors` None
  or N×3 RGB 0–1. Units are the publisher's.
- **Other options.** `t` as the recording's own time; `frame` as the
  index into the file (repeats on a loop); N×4 points.
- **To reverse.** One dataclass.
- **Rough edge.** Points are expected finite: a NaN point gives NaN
  bounds (plan 29's sensors must filter, or `bounds` moves to
  `nanmin` / `nanmax`).
- **Judge it.** Check 190; check 216 for plan 26's `cloud` node, which
  draws it.

### 166. Clouds are on the registry, not the Router: `DeviceRegistry.clouds` as `cloud:<role>`

- **Built.** A device that publishes a cloud holds its latest frame;
  `DeviceRegistry.clouds` maps `cloud:<role>` to it for every **open**
  device that has one, in list order — what plan 26's point-cloud node
  (`graph.PointCloud`, rows 204–209) reads (`cloud:scan`). No `cloud`
  scheme reaches the Router, the referee
  or a Learn. The cloud device's one `Port` has `kind = "cloud"`. A
  closed or removed device's cloud is gone from the map at once.
- **Other options.** `Router.feed("cloud", …)` (the Router holds float
  vectors per scheme); a stored map filled in the feed slot.
- **To reverse.** One property.
- **Rough edge.** The map is rebuilt on each read (cheap).
- **Judge it.** Checks 190, 216.

### 167. The cloud file: a version-1 `.npz` — rate, ragged offsets, concatenated points, optional colours

- **Built.** `devices.write_clouds(path, frames, rate, colors=None)`
  writes `version` (1), `rate` (frames per second), `offsets` (F + 1:
  frame i is `points[offsets[i]:offsets[i+1]]`, so frames may differ in
  size) and `points` (M×3 float32), plus `colors` when given;
  `read_clouds` checks every key and shape and refuses another version,
  offsets that do not walk the points or a rate that is not positive, as
  an error the device's line shows. The fixture
  `tests/fixtures/clouds/knot.npz` is a (2, 3) torus knot turning about
  its vertical axis, 16 frames at 12 fps, 96 + 8i points on frame i,
  coloured by height, written by `tools/cloud_fixture.py` with no random
  numbers and no clock.
- **Other options.** A fixed N per frame; PLY or PCD; one `.npy` per
  frame in a folder.
- **To reverse.** Two functions; nothing outside the tests reads the
  format yet.
- **Rough edge.** No per-frame timestamps: a recording plays at one rate
  (a later version may add `times`; version-1 readers ignore unknown
  keys).
- **Judge it.** Check 190.

### 168. The `cloud` device plays at its own rate against the frame clock; `file` is the home's

- **Built.** `kind = "cloud"` with `file` (required; relative to the
  home), `rate` (default the file's) and `loop` (default true; false
  holds the last frame). Polled at `now` it shows recorded frame
  `floor((now − start) · rate)`, so it plays at 12 fps whatever the app's
  frame rate. `connected` while the file is loaded; a missing or bad
  file, or a bad `rate`, is `error: …` with one note and retried, so a
  file copied in later comes up with no relaunch. The line: `scan · cloud
  · connected · 1 source · knot.npz · frame 7/16 · 144 points · 12 fps`.
- **Other options.** One recorded frame per app frame; resolve `file` in
  `config.py`.
- **To reverse.** One class.
- **Rough edge.** The file is read whole at open; a recording changed on
  disk is not re-read until its entry changes or the app restarts.
- **Judge it.** Check 190.

### 210. The device qualifier is general: any scheme takes `@<role>`; an unqualified row is the primary device's

- **Built.** A row's source may carry `@<role>` on any scheme, not only
  MIDI's (`pad@p2:A`, `hat@p2:UP`, `axis@p2:LX`): `routing.base_scheme`,
  `Binding.device`, `Binding.bare`, `is_continuous` read it the same way
  for every scheme, and the qualified head (`axis@p2`) is its own Router
  key — its own feed, labels, rests and names — so two pads never
  overwrite each other. An unqualified row means the scheme's primary
  device: MIDI's by B2's rule, unchanged to the byte (`midi_roles`: the
  desk whose profile wrote the table, else the first listed); every
  other scheme's by list order, the first enabled entry of its kind
  (`devices.primaries_of`, `DeviceRegistry.primaries`, told to the table
  as `Bindings.primaries`). No file migrates: every `pad:A`, `axis:LX`,
  `hat:UP` written before means the first pad. A qualified row's line
  says whose it is ("left stick X on p2 pushes +0.25"; "pad A on p2").
- **Other options.** A role-named scheme per pad (`p2:A`, as an OSC
  device's — but then a second pad's rows look nothing like the first's
  and Learn, the remap and the camera job would each need a branch); the
  primary chosen by a key (`primary = true`) rather than list order;
  migrating old rows to `pad@pad:A`.
- **To reverse.** `base_scheme` back to its MIDI-only test and
  `Binding.device` with it; the pad's role then has no way into a row.
- **Rough edge.** A row qualified with the primary's own role
  (`pad@pad:A`) means nothing — the primary reads bare rows only (a
  desk's `cc@apc40:…` does act). Swapping the two pad entries swaps
  which pad the bare rows mean; the second pad's qualified rows go
  dormant when it becomes the primary. A role containing `@` would read
  as a qualifier (config does not refuse one).
- **Judge it.** Check 219.

### 211. A joystick per pad device, the next free one or pinned; one USB reader, the first `usb = true` entry's

- **Built.** Each pad device reads its own controller. The pads share
  one `gamepad.Claims` on the registry's context (`Context.pads`): a pad
  takes the next present GLFW joystick no other pad has taken, in list
  order (the devices poll in list order, so the first pad takes the
  first). An entry's `joystick = n` (0–15, checked in `config.py`; a bad
  value is a note and dropped) pins it: it reads only that index, waits
  for it (`lost · waiting for joystick 1`), and no unpinned pad takes it.
  An unpinned pad whose joystick leaves reads `lost`, lets the index go,
  and takes the next free one that appears. The SYSTEM line names the
  joystick read (`glfw 1`). **The libusb reader stays one**: the first
  pad entry with `usb = true` owns it; a later `usb = true` entry reads
  GLFW only and says `usb: pad has the wired pad` on its line. A pad no
  device attached (a tool, a test) reads the first present joystick, as
  before.
- **Other options.** Match a pad to its entry by GUID or name (GLFW
  reports both; a re-paired Bluetooth pad keeps its GUID) — plan 28/29's
  device identity; hand the USB reader to whichever pad has no GLFW
  joystick (works with the defaults, but the owner's ruling is "the
  first `usb = true` entry"); one USB reader per entry (two wired pads —
  `UsbPad` takes the first 360 pad it finds, so two readers would fight
  for one).
- **To reverse.** `Pad._find` back to "the first present joystick" and
  `Pad.attach` out of `PadDevice.open`: about forty lines.
- **Rough edge.** With the defaults (`usb = true` on both entries) the
  first pad owns the USB reader even while it reads a Bluetooth pad over
  GLFW, so a wired pad on the second entry is never read: the
  Bluetooth pad's entry needs `usb = false`. Only one wired 360 pad is
  ever read. GLFW's index for a pad can change across a reconnect, so a
  pinned pad may wait for an index its controller no longer has.
- **Judge it.** Check 219.

### 212. The camera job and the factory pad rows are the primary pad's; a second pad starts with no rows; one feel

- **Built.** Defaults author no look (decision 24): the sticks' default
  camera job (`gamepad.steer`) runs for the primary pad only — a second
  pad's unrouted sticks and triggers do nothing until a route names
  them. The factory pad rows (`bindings.default.json`) and `PAD_REMAP` /
  `PAD_NEW_ROWS` are unqualified, so the primary's; a second pad starts
  with no rows and gets them from Learn pad (one item: it completes on
  whichever pad moves first) or ROUTING. The pad's feel, the five
  `desk.pad.*` session params, is one set applied to every pad
  (`Router.source_feel` reads any `axis@<role>` as `axis`).
- **Other options.** Copy the factory rows for each pad (two pads would
  both flip faces on A); run the camera job on every pad (two sticks on
  one camera); a feel per pad (`desk.pad.<role>.*` — more session params
  on SYSTEM for a case not yet played).
- **To reverse.** The `if q:` branch in `PadDevice.act`; per-pad feel is
  a new set of params and a role key in `Router.source_feel`.
- **Rough edge.** Per-pad feel is plan 28/29's. "Learn pad" on a
  param's menu shows while the *first open* pad is connected
  (`rig.adapter("gamepad")`), so with only the second pad plugged in the
  item is missing.
- **Judge it.** Check 219.

### 213. The hands stay single: a second hands entry is refused

- **Built.** The hands kind is not `repeatable`: a second enabled hands
  entry is refused as in B1 (`error: feeds 'hand', which leap already
  feeds — not opened`, one note) and comes up when the first leaves the
  list. Their forty named lanes, the pair scheme `hands`, the HANDS page,
  the ghost and the calibration are all one tracker's; two Leaps are
  plan 29's.
- **Other options.** Qualify the hands too (`hand@leap2:right.roll`):
  the Router would take it, the HANDS page, the ghost and the
  calibration would not.
- **To reverse.** `repeatable = True` on `HandsDevice`, then a page, a
  ghost and a calibration per tracker.
- **Rough edge.** None new: the refusal is B1's.
- **Judge it.** Check 174.

## The render graph (plan 26)

Built in plan 26's run on 2026-10-14
([`plans/26-render-graph.md`](plans/26-render-graph.md)), on
`plan-24-26-27-integration` until the owner merges it. The owner's own
decisions for this plan (1–9, 15, the render parts of 16, and 22–24 of
the launch prompt: the four node kinds, the hands in the scene or as a
layer, the shape's transform and the fixed eye, real depth for lines and
points, the history as wiring, step 0 first, no GLSL in the graph; and
the stroke-space toggle of 2026-10-14) are in
[`DECISIONS.md`](DECISIONS.md) with Who "owner"; these rows are what the
build chose where those left a choice open — the golden rig, the timer,
the instance marker, the node and port design, the eye's ids and
defaults, how the pan migrates, the in-scene alpha rule, the
depth-aware threshold, the graph JSON's shape, the cloud's transform
among them. No preset was edited or added: no factory preset carries a
`graph` section, and every proof is a fixture under `tests/fixtures/`.

### 169. The instance marker for an extra render node is its number right after the node's prefix (`fx.acid.2.mix`)

- **Built.** `params.instance_id(node, key, n)` and
  `params.instance_of(pid, node)`. Instance 1 keeps today's id
  (`fx.acid.mix`, `ghost.alpha`, `dream.mix`); instance n ≥ 2 is
  `<node>.<n>.<key>` (`fx.acid.2.mix`, `ghost.2.alpha`). The first
  segment — the group, which decides whether a param is in a preset —
  never changes, so an extra instance lands in the same part of a preset
  as its first, and no preset or binding migrates for a single-instance
  graph. The rule is written in ENGINEERING §2. The owner sees these ids
  in ROUTING, learn lines and preset files once a preset's graph adds a
  second instance (row 198).
- **Other options.** `fx.acid#2.mix` / `fx.acid@2.mix` (a new character
  every OSC address, file name and binding would have to accept);
  `fx.acid_2.mix` (collides with an effect file named `acid_2`);
  `fx2.acid.mix` (a new first segment: changes the group).
- **To reverse.** Two functions and a paragraph — but now a migration of
  every saved id that carries a marker.
- **Rough edge.** A purely decimal segment after the prefix is the
  marker, so no effect file and no `@param` key may be digits alone
  (refused at the source since row 198). It looks like the collection
  indices `band.2.trim` / `pattern.mod.3`, which are not node instances:
  `instance_of` is asked only about node prefixes.
- **Judge it.** Check 193.

### 170. Golden frames: the eight output states as eight outputs of one frame, and output 1 alone

- **Built.** Per preset and hand state, one rig draws all eight
  `Switches` states as eight views of one `draw_outputs` call — output 1
  4× MSAA like the window, the other seven plain targets — at 960×600,
  dpr 1, after 8 frames at 1/60 s on a pinned clock. Because a pipeline
  shared by two views goes through a frame texture, `solo` adds output 1
  alone (drawn direct) for every preset × hands, and
  `solo-scene+hands+through` the same for the six presets with an
  effect on. The full-resolution frame's SHA-256 is compared exactly; a
  quarter-size PNG is for a person. 427 goldens at A0, 556 today (row
  list in the plan file).
- **Other options.** One rig per state (368 rigs, about 45 s, every
  frame direct); single-sample output 1 (unlike the window).
- **To reverse.** `_shoot`'s view list and one re-record: every golden
  moves.
- **Rough edge.** The direct MSAA path and the texture path are not
  bit-identical in general (three hands-absent solo frames differ from
  their eight-output twin by 1 LSB in one pixel); both are pinned. The
  goldens prove pixels only on "Apple M3 Max": anywhere else the test
  skips.
- **Judge it.** Checks 191, 192.

### 171. "LFOs and analyzer at rest" in the goldens means never stepped and never fed

- **Built.** The golden rigs declare `lfo.*` / `tempo.*` (so presets
  load them) but never step the LFOs and never feed an analyzer or LFO
  lane: every param sits at its base plus the hand rows.
- **Other options.** Step the LFOs at a pinned phase 0 (the LFO maths and
  a random LFO's seed in every golden); publish rest values explicitly.
- **To reverse.** `lfos.step/publish` in `Rig.frame` and a re-record.
- **Rough edge.** lfo-breathe's golden is its bases, not its breathing.
- **Judge it.** Check 191.

### 172. "Hands present" in the goldens is one fixed two-hand pose with the ghost on

- **Built.** `tests/fake_hands.py` at test_ghost's pose (left open at
  (−90, 210, 0) mm, right fist at (90, 200, 10)), polled fresh each frame
  through the real `HandsIO` (One Euro, dead zone, follower), full frames
  with skeletons, so the preset's hand rows move and the hands draw.
  `ghost.on` is set in every rig (a session param no preset carries);
  "present with the ghost off" is the hands-absent picture.
- **Other options.** Several poses per preset (multiplies the count); the
  ghost at its session default, off (the hands' states never reached).
- **To reverse.** Extend `FakeHands` / `HANDS` and re-record.
- **Rough edge.** One pose: a hand row's full throw is not covered by a
  golden (`tools/preset_shots.py`'s sweeps cover it numerically).
- **Judge it.** Check 191.

### 173. The 1080p-cap golden is party-trip on a 2× HiDPI 1080p screen

- **Built.** One golden: party-trip, hands present, `scene+hands`, a
  3840×2160 output at dpr 2 (1920×1080 logical) under `max_frame =
  (1920, 1080)`: the frame is drawn at 1920×1080 and shown scaled. Every
  other golden also runs under the 1080p cap (the app's default), which
  does nothing at 960×600.
- **Other options.** An output of exactly 1920×1080 (the cap does
  nothing there); a preset without effects.
- **To reverse.** `CAP` in the tool and a re-record.
- **Rough edge.** One preset and one state at the cap; hashing one 33 MB frame.
- **Judge it.** Check 191.

### 174. GPU time per node: one query each, read 3 frames late, a median over 60 frames

- **Built.** `render.PassTimer`: one `GL_TIME_ELAPSED` query per node a
  frame (queries never nest; a node that runs several times a frame is
  summed, one that did not run counts 0), read `LAG` = 3 frames later so
  the CPU never waits on the GPU, kept as a rolling median over `WINDOW`
  = 60 frames in `stats["gpu_ms"]`; `stats["gpu_note"]` says why there
  are none ("no GPU timer queries on this context …"). The SYSTEM page:
  "gpu per node, ms (median of the last frames):" and one line per node,
  in the graph's order. A0 built six fixed passes (scene, cover, hands,
  lookback, fx, compose); A1 made it one line per node, named by the
  graph, a node that leaves the graph leaving the list.
- **Other options.** One dot-separated line (the prompt's example text);
  nested queries per pipeline (GL forbids nesting); reading each query
  at once (stalls the CPU every frame).
- **To reverse.** Local to `PassTimer` and `Panel.gpu_lines`.
- **Rough edge.** Apple's driver reports some tiny nodes as 0.00 ms; the
  figures are GPU time only, not the CPU's time to issue the work; the
  lines show the medians, no history.
- **Judge it.** Check 194.

### 175. The golden tool keeps one standalone GL context for the process

- **Built.** `tools/golden_frames.context()` makes one standalone context
  with `gc_mode = "auto"` and collects each rig's objects after it;
  `tests/test_golden_frames.py` uses the same context.
- **Other options.** A fresh context per rig (cleanest, but `release()`
  left no context current and broke the GL tests after it).
- **To reverse.** Local to the tool.
- **Rough edge.** None seen: the hashes are identical to a per-rig
  recording.
- **Judge it.** Check 191.

### 176. The FX node is the chain, one per pipeline, and the end of its pipeline

- **Built.** `graph.Fx` wraps `fx.FxChain`: it paints its input into the
  chain's first half-float texture and the last effect writes the
  destination; with no effect on it paints its input straight through.
  The default pipelines are three `Fx` nodes over the one chain (`fx`,
  `fx(scene+hands)`, `fx(hands)`), the effects' order inside each as
  before. As a pipeline's end it decides where the picture lands:
  straight into the one output that takes it when that output is at the
  frame's size, unflipped and on this context; otherwise once into a
  frame texture every output of it shows. The owner sees one SYSTEM line
  per chain node, 0.00 when its pipeline did not run.
- **Other options.** One FX node shared by the pipelines (the chain's
  ping-pong textures are shared state: two pipelines cannot interleave
  through one node); an FX node only while an effect is on (a rebuild on
  every `fx.on`, a line that comes and goes); the direct-or-texture
  choice on the Output node (two outputs would each need to know the
  other).
- **To reverse.** Local to `graph.Fx` and `default_graph`.
- **Rough edge.** A `fx(scene+hands)` or `fx(hands)` node is in the
  graph (and on SYSTEM at 0.00) whenever an output has hands-through on,
  with no effect on or no hand showing. These three are one chain, not
  instances, so their names are not param prefixes (`fx(…)`, never
  `fx.<x>`).
- **Judge it.** Check 194.

### 177. The history is two nodes: `history` (the echoes and the dream over its input) and `capture` (the ring)

- **Built.** `graph.History` lays its input over the echoes and the
  dream, occluded by its `cover` port (a copy with the look-back off),
  and moves the echoes' clock and pulls a finished dream once a frame.
  `graph.Capture` puts its `image` port — what the wiring says (row 194)
  — into the ring exactly once a frame, after every pipeline end. Two
  nodes, because the composite must read the ring before the frame's
  capture changes it, and runs once per pipeline.
- **Other options.** One node with a two-phase contract (a second
  evaluator phase for one node); the capture inside the history's run
  (the composite would see the current frame as an echo: every echo
  golden moves); the capture by the Output node (several outputs would
  capture several times).
- **To reverse.** Merge the classes and add a second phase to
  `Graph.evaluate`; no pixel changes.
- **Rough edge.** `history`'s GPU line sums its composites for every
  pipeline of the frame.
- **Judge it.** Check 194.

### 178. The Output node is `Renderer._compose`, one per view, after the capture

- **Built.** `graph.Output` calls `_compose` for its view: its picture
  (1:1, scaled into `outputs.fit`'s rect, or already there when drawn
  direct), the hands over it, the readout, the flips, the dim (master ×
  its own), or the five-step `outputs.Handoff` for a presenter. Named
  `output.N` after the `output.N.*` params; one SYSTEM line each.
- **Other options.** `_compose` moved into graph.py (it needs `Handoff`,
  `fit`, `_show`, `dim_pass`, still the renderer's); one Output node for
  all views (no per-output timing).
- **To reverse.** Trivial: the node is a wrapper.
- **Rough edge.** Which pipeline end feeds it is settled per frame
  (`Output.settle`, row 193).
- **Judge it.** Checks 194, 195.

### 179. Nodes and ports: made images are pulled by their consumers; painted images draw into the consumer's framebuffer

- **Built.** `graph.Node` has a unique `name` (the SYSTEM line, the
  timer's key), typed input ports (`INPUTS`: `image`, `mask`,
  `geometry`), one `OUTPUT` type, `after` dependencies, and `run(frame)`.
  A Scene or Layer *makes* a texture (`image`, and `depth` beside it); a
  History, Composite or FX *paints* (`paint(frame, dst)`) into the
  framebuffer its consumer hands it — so the look-back composites
  straight into the chain's half-float input and the chain into the
  window, as before. Any image feeds any image port (the default `paint`
  shows a made texture 1:1); a consumer that needs a painted node as a
  texture gets it materialised once a frame (`Composite.image`).
  Geometries are drawn by their scene or layer. The graph refuses a
  wrong port type, an unknown port, a dependency outside it and a
  duplicate name when it is built. Method names: `run`, `paint`, `draw`,
  `image`, `depth` — never `apply`, `modulate`, `snapshot`, `set_value`
  (pinned by `tests/test_graph.py`).
- **Other options.** Every node materialises a texture (an RGBA8 texture
  between the look-back and the half-float chain quantises the picture:
  goldens move); a `Port` object per connection (more machinery than the
  nodes need; plan 28's editor can add it).
- **To reverse.** The pull is inside three `paint` methods; a
  materialising design replaces them and re-records goldens.
- **Rough edge.** A painted node can run more than once a frame (the
  history for two pipelines), by design; its GPU line sums them.
- **Judge it.** Check 194.

### 180. The default graph is keyed by the views' switches, the wiring and the listed clouds; the last one is reused

- **Built.** `graph.graph_key(views)` is each view's (scene, hands,
  through); `Renderer._graph_for` keeps the last graph and builds a new
  one only when that key, `Renderer.wiring` (row 194) or the listed
  `cloud` roles (row 207) change — a switch toggled, an output opened or
  closed, a preset with another graph, a cloud listed. Size, flips, dim,
  a presenter and the cap are read when the nodes run; which pipelines
  run is settled per frame after the hands' layer drew. `on_reload`
  drops the graph so a saved graph.py rebuilds it from the new classes.
- **Other options.** Key on `fx.active()` and hand visibility too (a
  rebuild on every hand that enters the box and every effect toggle; the
  SYSTEM lines would flicker); a cache of every graph seen.
- **To reverse.** Local to `_graph_for` and `graph_key`.
- **Rough edge.** `FxChain.tick` (the effect folder's 30-frame watch)
  runs at the top of the frame, before the scene: an effect file saved to
  disk lands on the faces' picture on the poll frame itself rather than
  the next.
- **Judge it.** Checks 194, 195.

### 181. The cover mask is a Layer node of the scene's faces, wired to the history

- **Built.** `graph.Cover` draws the faces' coverage mask
  (`Renderer._draw_cover`) only while the look-back occludes, from the
  face buffer the scene pass left, into the history's `cover` port
  (type `mask`). Its SYSTEM line stays `cover`.
- **Other options.** The cover inside the Scene node (its line merged
  into `scene`); drawn by the History node (a history that draws
  geometry).
- **To reverse.** Local.
- **Rough edge.** It depends on the scene node (the face buffer), not on
  the shape geometry in the shared camera.
- **Judge it.** Check 194.

### 182. The eye: `eye.fov` and `eye.distance`, session params whose defaults are the old 3D divide

- **Built.** A fixed perspective camera on the world's +z axis looking at
  the origin, y up (`geometry.eye_matrix`). `eye.fov` = 47.6°
  (`geometry.EYE_FOV`) across the picture's **shorter** side (the longer
  side sees more, as `project_h`'s `min(w, h)·0.30` did); `eye.distance`
  = 3.78 shape radii (`EYE_DISTANCE` = CAM3 / 0.9). Ranges 10–120° and
  1.5–40 (log). Group `eye`, a session group: no preset moves it, the
  show saves it. Not modulatable (the camera is the rig; the shape is
  what moves). Clip planes 0.05 / 1000 (`EYE_NEAR` / `EYE_FAR`: depth
  only). On the CAMERA page under "eye" ("the room's camera, not the
  preset's"). With the defaults, zoom 1 and pan 0, the largest vertex
  error against `project_h` is 2.3e-13 px in float64 and 1.1e-4 px in
  float32, against a bar of 0.5 px.
- **Other options.** The fov on the vertical (would not reproduce
  `project_h` on a portrait output); an eye position / target / up set
  (more knobs than a fixed camera needs); modulatable (a lane would swing
  the whole room).
- **To reverse.** Local: two params, `eye_matrix`'s arguments.
- **Rough edge.** Moving the eye off its defaults moves the whole
  picture (no golden covers it). Past zoom ≈ 3.8 the eye is inside the
  shape (row 188).
- **Judge it.** Check 196.

### 183. `camera.pan` is in world units (±12 shape radii), marked by a `units` key, converted through the 1080p screen

- **Built.** `camera.pan.x/y` are the shape's world position in shape
  radii (`geometry.model_matrix`), y positive **down** the screen as it
  always was (stored and routed pans keep their direction). Range
  ±`params.PAN_RANGE` = ±12, shown `+0.00`. A document **without**
  `"units": {"camera.pan": "world"}` stored logical px and is divided by
  `geometry.PAN_REF_PX` = 324 px a unit (the default eye's px per unit at
  1080p, the render cap and the party projector) at load, silently —
  presets (`preset.load_doc` step 0), camera module presets and
  `camera/default.json` alike (`params.pan_world`); every save writes the
  key. The schema stays `hyperspace.preset/2`. Only `values` convert
  (route and desk depths are fractions of the range); ±12 keeps a routed
  pan as far as ±4000 px went at 1080p — `hands-orbit`'s push of 0.1
  moves the shape ±1.2 radii (≈ ±390 px at 1080p; ±400 before). The
  mouse drag pans by cursor px / px-per-unit and the wheel zooms about
  the point under the cursor (`app._px_per_unit`).
- **Other options.** A schema bump to preset/3 (an older build would
  refuse every new file); the reference screen = the window at load (a
  preset would land differently per screen); the golden size 960×600;
  pan.y positive up (every stored pan.y flips); converting route depths.
- **To reverse.** `pan_world` and the range; a world-unit file needs the
  opposite conversion (the key says which it is).
- **Rough edge.** **A converted pan is exact only on 1080p**: on the
  laptop window an old preset's shape sits proportionally nearer the
  centre (party-mandala's 190 px is 0.59 radii: 105 px at 960×600). A
  pan is exact at depth 0; off-centre the shape is seen a little from
  the side.
- **Judge it.** Checks 199, 201.

### 184. `camera.zoom` is the shape's world scale; copies live in the world

- **Built.** `model_matrix` scales the shape about the world origin
  (the whole-frame 2D zoom is gone). Copies are in the world: a cell is
  `render.CELL` = 2.4 radii (the old `0.72·min(w, h)` px through the
  default eye), offsets before the zoom, so a field is scaled and moved
  as one and at zoom 1 is spaced exactly as before at depth 0. A scaled
  shape has its own perspective (a small zoom is flatter, a big one
  deeper); off-centre copies are seen slightly from the side. **The
  strokes' weight is row 189's**: A2 built "strokes and dots keep their
  pixel weight", which since A2b is true only with Screen strokes on;
  by default they scale with the zoom as before plan 26.
- **Other options.** Copies as screen-space tiles after the projection
  (the old picture exactly, but not in the world the hands join); the
  cell fixed in the world with the zoom only on each copy (zooming out
  would spread a field apart).
- **To reverse.** The cell offsets inside `u_model` vs outside.
- **Rough edge.** A zoom route (hands-orbit, party-trip's LFO) changes
  the shape's perspective as well as its size.
- **Judge it.** Check 197.

### 185. The shape's depth: never tested against itself; its visible surface (alpha > 0.25) written after its colour

- **Built.** `SceneTarget` has a depth attachment. `draw_scene` draws
  faces, edges and points painter-sorted as before, depth-tested against
  whatever solid geometry is already there (the hands, a cloud) with
  depth writes off; then `Renderer._depth_pass` draws them again writing
  depth only (colour untouched) for fragments whose alpha is over
  `render.DEPTH_ALPHA` = **0.25**. A draw that cannot reach it is
  skipped. The colour is byte-identical with or without the attachment.
- **Other options.** Depth writes in the colour pass (edges crossing in
  the painter sort's wrong order would cut each other); threshold 0.1
  (bright fills would hide a hand behind a barely visible face) or 0.5
  (only the nearest edges would count).
- **To reverse.** One constant; the pass is one method.
- **Rough edge.** The depth pass re-draws edges, points and bright fills
  on almost every frame (measured within run-to-run noise on the M3
  Max). Bright fills (alpha up to ~0.36 at bright 2) do write depth.
- **Judge it.** Check 205.

### 186. Point quads are a whole number of pixels across

- **Built.** `draw_scene` rounds each point's diameter to whole
  framebuffer pixels (`floor(2r + 0.5) / 2`): Apple's driver rounded
  `gl_PointSize`, and with the rounding the quads draw the old sprites'
  frames byte for byte.
- **Other options.** The true fractional size (every points-on golden
  moves; dots a little bigger).
- **To reverse.** One line.
- **Rough edge.** Dots change size in one-pixel steps with depth, as
  they did.
- **Judge it.** Check 196.

### 187. The Leap calibration: `units` in `hands.json` /3, "from the box" by default, fitted into a 16:9 picture of the eye

- **Built.** `hands.core.Units(mm, origin, tilt)` in `hands.json` beside
  the ranges and the box: `"units": {"mm": null, "origin": null, "tilt":
  32.0}`. A Leap point lands at `world = R_x(tilt) · (stage(p) − c) / mm`
  (`ghost.calibration`). `mm` null → the scale at which the padded palm
  box fits, every corner, into the eye's frame of a **16:9** reference
  picture (`ghost.CAL_ASPECT`, the party projector, as `PAN_REF_PX` and
  the 1080p cap), as tightly as the old ghost camera framed it there;
  `origin` null → the padded box's centre; `tilt` 32° (the old ghost
  camera's elevation). Measured with the goldens' hands: within 4 px of
  the old camera at 960×600 and 9 px at 1080p. `CAL_SCHEMA` =
  `hyperspace.hands/3`: an older file is read as it is and kept as
  `hands.json.bak-v2` (or `-v1`) by the first save. A bad entry is "from
  the box" with one stderr line. Not editable in the UI. (A2 built the
  entry and a fit to the shorter side's square; A3 changed the fit to
  16:9 when it drew the hands through it — the square had drawn them two
  thirds the size.)
- **Other options.** The fit to each output's aspect (as the old camera
  did: the hands' size relative to the shape would then change with the
  window, which the shared world forbids); the square on the shorter
  side; a full 4×4 in the file (opaque to edit); an anisotropic map that
  reproduces the old camera exactly (it would squash the hands' depth in
  the world).
- **To reverse.** One constant (and the fit's two tangents); local to
  `Units`, `calibration`, `save_calibration`.
- **Rough edge.** On a portrait or square output the box is wider than
  the frame: a hand at its left or right edge leaves the picture. The
  perspective is the eye's 47.6° across the shorter side, not the old
  camera's 38° vertical: fingers nearer the eye are a touch bigger. This
  is why A3's 122 hands goldens moved.
- **Judge it.** Checks 202, 203.

### 188. A stroke end behind the eye is slid to just in front of it

- **Built.** In `LINE_VS` an edge end with clip w below `EYE_W` (1.2 ×
  `EYE_NEAR`) is moved along the edge to w = `EYE_W`; an edge wholly
  behind is dropped; a point behind the eye is dropped. Faces are clipped
  by the GPU.
- **Other options.** Let the GPU clip the expanded quad (an end behind the
  eye projects to the wrong side and the quad sweeps the screen).
- **To reverse.** Local to the shader.
- **Rough edge.** Reachable only past zoom ≈ 3.8 (the eye inside the
  shape).
- **Judge it.** Check 197.

### 189. Strokes in world space by default; screen space is the switch

- **Built.** The owner asked for the toggle on 2026-10-14 (DECISIONS,
  owner); the default is the build's. With `view.screen_strokes` off (the
  default) the edges' width and the dots' radius are × `camera.zoom`
  again — the pre-A2 formula and nothing else: the width × zoom before
  the 1 px floor (the sub-pixel part folded into alpha, so a zoomed-out
  field's far edges fade as they did on `main`), the radius × zoom before
  the whole-pixel rounding. Strokes grow and shrink with the shape; the
  zoomed-out factory looks (ember-orbit 0.5, hex-engine 0.4, party-field
  0.42) are back to their pre-A2 weight. On, they are A2's: the same
  pixel weight whatever the zoom. At `camera.zoom = 1` both draw the
  same frame byte for byte. The shape's strokes only: the hands' tubes
  are world-sized (`ghost.WIRE_R`, `BONE_R`) and never follow the zoom,
  and hand lines (row 201) are always one pixel. **This row supersedes
  the sentence "strokes and dots keep their pixel weight" of A2's zoom
  row (row 184).**
- **Other options.** Screen space as the default (A2's goldens kept; the
  zoomed-out looks 2–2.5× heavier than on `main`, the rough edge the
  owner did not want by default); true perspective width (a stroke a
  world size, thicker at its near end: every frame with strokes moves,
  zoom 1 included, and it is a shader change); a 0–1 blend between the
  two.
- **To reverse.** One default (`ViewState.screen_strokes`) and 218 frames
  re-recorded; or the switch removed (one line, one param, one checkbox).
- **Rough edge.** A2's goldens at zoom ≠ 1 moved a second time (218 of
  556). At a big zoom (party-tumble 1.3, party-acid 1.1) edges are
  fatter, and zoomed far out the far edges fold into alpha and a field
  looks fainter — as on `main`. A preset saved before A2b has no key and
  loads world space. At zoom 1 the switch shows nothing (a routed zoom
  makes it live, so it is not a learn "cannot show" rule).
- **Judge it.** Check 198.

### 190. The stroke switch's form: `view.screen_strokes`, a performance toggle, routable and modulatable

- **Built.** `view.screen_strokes` ("Screen strokes"), a toggle in group
  `view`: in every saved preset's `values`; a file without it loads off
  (world space), so the new switch is off by default (decision 24).
  Routable and modulatable like `view.lines` and `view.cut_through`. On
  the VIEW page under the points and lines opacity sliders, one checkbox
  with a tip; no desk or pad default. `learn.cannot_show` calls it dead
  ("points and lines off") while both are off.
- **Other options.** An enum `view.stroke_space` (world / screen: its
  default would be index 0 of an enum, not a switch off); a session param
  (it would not travel with a look); not modulatable.
- **To reverse.** Local (the id lives in `params.py`, `view.py`, `ui.py`,
  `render.py`, the tests).
- **Rough edge.** A modulated flip mid-zoom jumps the stroke weight in one
  frame (as flipping `view.lines` does).
- **Judge it.** Check 198.

### 191. Hands inside the scene are solid: `ghost.alpha` is not applied there

- **Built.** With the hands in the scene the scene draws them first
  (`Ghost.draw_solid`: the style's parts, depth test and write on,
  premultiplied over the cleared ground), then the see-through shape
  painter-sorted and depth-tested against them. A hand in front of the
  shape hides it; behind it, the shape's strokes and fills lie over it.
  `ghost.alpha` still sets the hands' *layer*; inside the scene they are
  at full opacity, each still premultiplied by its fade (see-through for
  its 0.1 s fade-in and 0.3 s fade-out). The guide and the tethers never
  go into the scene: they are the readout, laid on at the outputs.
- **Other options.** The hands sorted as one see-through object among the
  shape's faces (the shape's draws split around each hand, a pass per
  hand); order-independent transparency (deferred by decision 3).
- **To reverse.** Local to `Ghost.draw_solid` and `graph.Scene.run`.
- **Rough edge.** A fading hand writes depth at any fade, so for its
  fade-out it cuts the shape behind it while already faint. `ghost.alpha`
  does nothing to in-scene hands **except at exactly 0**, which removes
  them from the scene too (0 = "no hands anywhere"); 0.01 shows them
  fully solid. With the look-back on (party-wake, party-tracer) in-scene
  hands are in the history: their echoes stack and a held hand saturates
  towards white.
- **Judge it.** Checks 204, 205.

### 192. The depth-aware composite hides a layer texel where the scene's visible surface is nearer by more than 0.05 shape radii

- **Built.** `render.LAYER_FS` / `Renderer.lay(blend="depth")`: both
  depths linearised through the eye's clip planes; a layer texel is
  dropped (the picture under it shows) where the scene wrote depth (its
  visible surface, row 185) nearer than the layer's by more than
  `render.LAYER_DEPTH_BIAS` = 0.05 world units (about 8–10 mm of hand at
  the default calibration). Where the scene wrote no depth, or the
  layer's resolved depth is the far plane, the layer shows. Used by the
  through composites, the history's composite and an output's
  hands-over when the layer is laid `depth`. The scene's depth is
  resolved out of its MSAA target on the first ask of a frame
  (`SceneTarget.depth_texture`, made lazily: nothing is allocated unless
  a depth-aware node exists).
- **Other options.** Compare raw window depths (a bias not in world
  units); a soft fade over a depth range (wider halos); hide on the
  far-plane silhouette too (measured: 29–48 rim pixels hidden with the
  hands wholly in front).
- **To reverse.** One constant; two lines of shader.
- **Rough edge.** Silhouette pixels use one depth sample of four: where a
  hand passes behind an edge the boundary is a 1 px stair-step, and a
  hand behind the shape keeps a 1 px rim. A presenter output lays a
  depth-aware layer plain over (the depths stay in output 1's context);
  "add" does reach a presenter (`Handoff.blend`).
- **Judge it.** Check 207.

### 193. The OUTPUT switches are the default graph's wiring; a through pipeline "stands down" per frame

- **Built.** `graph.default_graph(views, wiring)` wires each output from
  its switches: `image` = the SCENE chain (scene on), `fx(scene+hands)`
  (scene, hands and through: the hands' layer composited onto the
  history before the effects), `fx(hands)` (scene off, hands and
  through), or nothing (the ground); `hands` = the layer laid over at the
  output (hands on, through off); `readout` = the layer's readout while
  hands is on. `outputs.route`'s per-frame collapse — no effect on, or no
  hand drawn: through is hands over — is wiring too: a through `Fx` node
  carries a `fallback` and is `bent` only while an effect is on and its
  layer drew; otherwise its outputs take the fallback with the layer over
  (`Output.settle`). `outputs.route` stays the pure table, and the golden
  tool asserts the graph's settled route equals it for every default
  state.
- **Other options.** Through as a static wire that always runs the
  composite (pixels move for letterboxed, flipped and overlay outputs,
  and two outputs differing only by through would run the chain twice);
  a new per-output "hands in the scene" switch (output params and a
  session decision; a preset's graph does it instead).
- **To reverse.** Local to `default_graph`, `Fx.bent`, `Output.settle`.
- **Rough edge.** The collapse is still a per-frame decision; a node
  editor (plan 28) will have to show a through wire that is sometimes not
  taken.
- **Judge it.** Checks 195, 208.

### 194. `Wiring`: where the hands are drawn, how their layer is laid on, what the history holds — renderer-wide, the default today's

- **Built.** `graph.Wiring(hands="layer"|"scene", blend="over"|"add"|"depth",
  history="scene"|"scene+hands")` (plus `draw` and `extra`, row 200),
  held by `Renderer.wiring`; the default `Wiring()` is today's frame and
  the graph is rebuilt when it changes. Only a preset's `graph` section
  sets it (row 196); the golden tool and the tests set it directly.
  `hands="scene"`: an output showing the scene shows the hands in it (no
  layer over it, no SCENE+HANDS pipeline); an output with the scene off
  still gets the hands' layer, over or through — decision 3's projector
  and glass with one `Wiring`. `history="scene+hands"`: the capture takes
  the layer laid on the scene (`composite(history)`, materialised once a
  frame); with the hands in the scene the scene already holds them, so no
  such composite is built.
- **Other options.** Per-output wiring (the history and the scene are
  shared: only the blend could be per output); a `render.*` param per
  choice (the wiring in the registry and presets before the graph JSON
  existed).
- **To reverse.** Local; the dataclass is the seam the graph JSON fills.
- **Rough edge.** With the hands in the scene an output's **hands** switch
  no longer removes them from that output's scene (it wires only the
  readout and, scene off, the layer); there is no "scene without hands"
  for the history in that wiring.
- **Judge it.** Checks 206, 209.

### 195. The hands node is `ghost` (geometry) feeding the `hands` layer; its time is decided by the consumer edge

- **Built.** The default graph has a geometry node `ghost` (the `ghost.*`
  params' node; a second is `ghost.2`) before the scene, settled once a
  frame (`Ghost.settle`); the hands' layer keeps its name and SYSTEM line
  `hands`. A hands node is never timed itself (`Hands.TIMED` is False):
  `Graph.timed` lists every node that times itself plus every solid
  geometry a scene draws, timed under its own name inside the scene's
  draw. So the default SYSTEM lines are unchanged (`scene cover hands
  history fx capture output.1`); with the hands in the scene `ghost`
  comes before `scene` (and `readout` when the readout is drawn alone);
  one hands node feeding a scene and a layer has its own line (its
  in-scene draws) beside the layer's. (A3 set the timing on the node
  from the scene that held it; A4 moved it to the consumer edge, so the
  same node object in two graphs is never changed by either.)
- **Other options.** Name the geometry `hands` and the layer
  `layer(hands)` (renames today's line); always time `ghost` (a dead
  0.00 line in the default graph); a line per consumer edge (`ghost→hands`
  as well as `ghost→scene`).
- **To reverse.** Names, and two lines in `Graph.timed`.
- **Rough edge.** The layer's draw of a node that is also in the scene is
  counted in the layer's line, not the node's.
- **Judge it.** Checks 210, 213.

### 196. The preset's `graph` section lists the nodes that differ from the default graph, one JSON object per node

- **Built.** A preset may carry `"graph": {"nodes": [...]}`
  (`graph.GraphSpec`, `graph.read_graph`, `preset.GraphSection`). Each
  entry names its `kind` and, for a second or later node, its
  `instance`; the rest is its wiring — `hands`: `into` (`layer` |
  `scene`), `draw` (`solid` | `lines`), `laid` (`over` | `add` |
  `depth`, only on the node that makes the layer); `effect`: `file` and
  `instance` ≥ 2 (instance 1 is the file itself); `history`: `holds`
  (`scene` | `scene+hands`). A node that is the default is left out, so
  `{"nodes": []}` and no section both mean the default graph. A save
  writes the section in a fixed order (hands by instance, effects by
  file and instance, the history, later kinds), one node per line,
  before `values`. Nothing that is a param goes in it. The owner sees a
  `graph` block only in a preset that has one — none in any factory
  file. Example: `tests/fixtures/presets/hands-lines.json`.
- **Other options.** A full node-and-edge list (`{"nodes": {...},
  "wires": [...]}`): what plan 28's editor will want, but today only the
  default graph's builder exists, so most of it would be re-derived and
  every file long; a flat object of the `Wiring`'s fields (shorter, but
  it cannot name instances or a later kind).
- **To reverse.** Local to `read_graph` / `GraphSpec.to_json` and
  `GraphSection`; no factory file carries a section.
- **Rough edge.** The section is wiring choices for the default graph,
  not a graph: the outputs still come from the OUTPUT page's switches,
  so a preset cannot say which output gets which hands node; at most one
  hands node makes the layer. Keys are strict: a key this build does not
  know makes the section unreadable (row 197).
- **Judge it.** Check 211.

### 197. A section this build cannot read is a note and the default graph, kept as the file had it

- **Built.** An unknown node kind, a value out of its choices, a key a
  node does not take, two nodes of one instance, two layers, `laid` on a
  node that makes no layer: one note on the preset strip ("graph:
  unknown node kind 'teapot' (this build knows effect, hands, history);
  the default graph"), and the values, routes and desk land as ever. The
  section is kept verbatim and written back on save, so a preset written
  by a later build survives a save in this one. **A `cloud` kind is such
  an unknown kind in this run**: point clouds follow the device list
  (row 207), not the preset's graph, until plan 28 (the orchestrator's
  ruling; no `cloud` entry in `graph.NODE_KINDS`). The whole section
  falls back, never part of it. A load sorts instance ids against the
  graph it lands, and any raise between landing the graph and the values
  puts the old graph back with its instances' values.
- **Other options.** Drop only the bad node (a partial graph the author
  never wrote); drop the section on save (loses a newer build's work).
- **To reverse.** One branch in `GraphSection.read`.
- **Rough edge.** A preset whose section fell back is not marked dirty
  and saves it back unread; the note is the only sign. A refused load
  still pushes a no-op undo step.
- **Judge it.** Check 211.

### 198. Instances as built: `fx.<file>.<n>.*` for an effect, `ghost.<n>.*` for a hands node, its layer `hands.<n>`

- **Built.** Row 169's rule, used. A second acid is the effect named
  `acid.2` in `FxState` (`set_instances`; the acid file's spec, labelled
  "Acid 2"), so its params are `fx.acid.2.on/mix/speed/blend/order/target/…`
  ("Acid 2 mix" on ROUTING and in learn lines), performance params in a
  preset's `values`, with its own clock and order, run on the file's one
  compiled program. A second hands node is `ghost.2` with
  `ghost.2.on/alpha/mirror/guide/tethers/style` ("Ghost 2 opacity"),
  session params like `ghost.*`; its layer is `hands.2` and its lone
  readout `readout.2` on SYSTEM. Re-declaring an effect file drops only
  its own ids, never an instance's; `fx.parse` refuses a purely decimal
  `@param` key and `FxState.load` an effect file whose stem has a dot or
  is digits alone (`acid.2.glsl`).
- **Other options.** An instance as its own effect file (a copy to keep
  in step); a per-instance prefix group (`fx2.acid.mix`: rejected,
  row 169).
- **To reverse.** `FxState.set_instances` and `ghost.prefix`; cheap
  before an owner preset uses `fx.acid.2`.
- **Rough edge.** An `fx` module preset saved while a second acid exists
  holds `fx.acid.2.*`; loaded where the graph has one acid it says
  "unknown id(s)". A second instance of an effect not on disk waits for
  the file. `ghost.2.*` are session params, and a show opens before its
  startup preset declares the node: the show holds them back
  (`Project._held_back`, neither reported unknown nor counted dirty) and
  `GraphSection` seeds the node from the open show once per show
  opened, so the glass comes up as saved.
- **Judge it.** Checks 212, 213.

### 199. A second hands node is its own `Ghost` over its own `GhostState`, kept while the app runs

- **Built.** `preset.GraphSection` declares `ghost.2.*` on a `GhostState`
  it keeps for the run and hands to the renderer
  (`Renderer.ghost_states`); `Renderer.ghost_of("ghost.2")` makes a
  `Ghost` over it on first use, following the first ghost's tracker and
  routing table. The graph's `Hands`, `HandsLayer` and `Readout` nodes
  draw through their own node's Ghost, and each Output lays its own
  layer's and readout's. A graph that no longer holds `ghost.2` releases
  its Ghost (`Renderer.drop_ghosts`, also on a hot reload); a preset that
  brings the node back finds its settings as they were.
- **Other options.** The state owned by the renderer (the registry would
  need the render stack to declare `ghost.2.*`, which it must not); a
  fresh state per load (the glass's mirror and style lost at every
  preset change).
- **To reverse.** Local to `GraphSection.land`, `Renderer.ghost_of`.
- **Rough edge.** `ghost.2.on` starts off (decision 24): a preset that
  adds the node shows nothing on the glass until the show switches it
  on. The HANDS page shows `ghost.*` only; `ghost.2.*` are reached from
  ROUTING, Learn and the desk (plan 28).
- **Judge it.** Check 213.

### 200. Where two hands nodes go: every `into: "scene"` node in the scene; the `into: "layer"` node (else the first) on the outputs without the hands in their scene

- **Built.** `graph.default_graph` with `Wiring.extra`: the scene draws
  every in-scene hands node (solid first); the layer is drawn from the
  node `into` "layer", else from the first (`Wiring.layer_node`), laid
  over or through on every output whose hands switch is on and whose
  scene does not hold hands. An output showing the scene with hands in it
  takes the first in-scene node's readout; one taking the layer, the
  layer's. So `ghost` in the scene and `ghost.2` the layer: the projector
  (scene + hands) shows `ghost` in its scene; the glass (scene off, hands
  on) shows `ghost.2`'s own picture — its style, opacity, mirror and
  guide.
- **Other options.** Both nodes on every output (the projector would show
  the hands twice); a per-output choice of node (output params, a session
  decision: plan 28).
- **To reverse.** Local to `default_graph`.
- **Rough edge.** A glass that shows the scene too gets the scene's hands,
  not the second node: its scene switch must be off.
- **Judge it.** Check 213.

### 201. "Hands as lines" is a hands node's `draw: "lines"`: the style's own meshes drawn as edges

- **Built.** A hands node drawn `lines` (`HandsAt.draw`, the JSON's
  `draw`): `Ghost.draw_solid(…, lines=True)` and `Ghost.layer(…,
  lines=True)` draw the style's spheres, capsules and palm as their
  triangles' edges (`ghost.Geometry.draw(lines=)` sets `ctx.wireframe`
  and puts it back), one pixel wide, depth-tested and depth-writing as
  ever; the guide stays solid. A node setting in the preset's graph, not
  a param (`ghost.style` is the session's, so a preset could not say
  "lines" through it). Default `solid`.
- **Other options.** A sixth `ghost.style`, LINES (a session param: a
  preset could not choose it); quads for the bones like the shape's
  edges (a real line width; a new draw path).
- **To reverse.** Remove `draw` from `HandsAt` and the `lines` keyword.
- **Rough edge.** Wireframe lines are one pixel whatever the dpr (core GL
  has no wide lines): thin on a 2× screen. The capsules' tessellation
  shows as a dense hatching, not a skeleton of bone lines — the owner
  judges whether this is "lines" (plan 28 / H3).
- **Judge it.** Check 214.

### 202. The OUTPUT and LOOKBACK pages say the wiring in words, on lines they already had

- **Built.** The OUTPUT page's "shows:" line says the wiring under a
  preset's graph (`ui.output_shows(…, wiring)`): an output whose scene
  holds the hands "scene + hands: in the scene as lines" (whatever its
  hands switch: the scene holds them anyway), a layer on its node when
  there are two ("hands through the effects (2)"), "as lines", "·
  depth-aware" / "· added". With the default graph the words are
  unchanged. Its hover gives `hands: in the scene · …`
  (`graph.hands_words`) and the loaded graph in one line (`graph: hands
  1 in the scene as lines · history with the hands`,
  `graph.graph_words`). The LOOKBACK page says `history: the scene` or
  `history: the scene · with the hands` under its switch
  (`ui_lookback.history_line`). No editor (plan 28); the existing
  switches still set the default graph's wiring.
- **Other options.** A line per output of its own (four outputs overflow
  the control window); the whole graph as a line on the page (the same).
- **To reverse.** Local to `output_shows` and the two pages.
- **Rough edge.** After a hot reload of graph.py the held `Wiring` is the
  old module's class until the next preset load (harmless today). The
  full graph line is on a hover only; a hidden layer node is named by
  number ("hands 2").
- **Judge it.** Check 215.

### 203. Undoing a load puts the loaded preset's graph back first

- **Built.** `library.Marks.take` carries `GraphSection.mark()` (the spec
  and the section as read); `Marks.before` lands it again before the
  values, so undoing the load of a preset with a second acid removes
  `fx.acid.2.*` and redo brings them back with their values. A load
  refused for a value puts the graph that was there back, with its
  instances' values.
- **Other options.** None worth it: without it an undo would put values
  on params that no longer exist.
- **To reverse.** Two lines in `Marks`.
- **Rough edge.** None known.
- **Judge it.** Check 211.

### 204. A point cloud is solid geometry in the scene: opaque round dots, depth written, before the see-through shape

- **Built.** `graph.PointCloud` draws the latest frame of `cloud:<role>`
  (`DeviceRegistry.clouds`, row 166) through the eye as one instanced
  quad per point (`CLOUD_VS` is A2's point-quad arithmetic), a hard round
  dot, alpha 1, depth tested and written. It is `SOLID`, so the scene
  draws it with the hands, before the shape: the shape's strokes in front
  of a point lie over it, and a point in front hides the strokes behind
  it. A dot is a whole number of framebuffer pixels across (row 186); a
  point behind the eye is dropped.
- **Other options.** See-through points sorted with the shape (a per-frame
  CPU sort of N points; plan 29's sensors publish 10⁵); soft-edged
  blended dots (the rim either cuts the shape or is hidden by it); GL
  point sprites (no real depth size control).
- **To reverse.** Local to `PointCloud.draw` / `CLOUD_FS`.
- **Rough edge.** Hard edges (MSAA smooths them on output 1; plain outputs
  show stair-steps). A point is the same size in pixels at any depth.
- **Judge it.** Check 216.

### 205. The cloud's world transform is one uniform scale about the world origin (`cloud.scale`, default 0.3), not the shape's camera

- **Built.** `u_model = diag(k, k, k, 1)` with `k = cloud.scale` (0.01–10,
  log, default 0.3: the fixture knot's ±3 units land at ±0.9 shape radii,
  the shape's size; a Kinect's metres at 0.3 would make a 2 m person 0.6
  radii). The shape's `camera.zoom/pan` and `rot.*` do not move the cloud
  (they are the shape's transform, decision 4); the eye does.
- **Other options.** Fit the cloud's `bounds` into the unit sphere each
  frame (the scale would breathe with a live sensor's noise); the shape's
  model matrix (the cloud would tumble with the shape); a full position
  and rotation (`cloud.pan.*`, `cloud.yaw`: plan 29's sensor calibration).
- **To reverse.** One param and one matrix.
- **Rough edge.** No offset or rotation: a sensor's cloud centred away
  from its origin sits off-centre until plan 29 calibrates it.
- **Judge it.** Check 216.

### 206. `cloud.*` is a session group: size, scale, brightness, the cloud's own colours

- **Built.** `cloud.size` ("Cloud point size": radius in logical px,
  0.5–12, default 2), `cloud.scale` (row 205), `cloud.bright` (× the
  colour, 0–2, default 1), `cloud.colors` (toggle, default on: the
  source's colours; off, or a source with none, white). In
  `params.SESSION_GROUPS` (the cloud is the room's sensor; a preset load
  never changes how it is shown), on `ViewState.cloud_*`. Size, scale and
  brightness are modulatable; the colours toggle is not. Every cloud node
  reads them.
- **Other options.** Performance params (a preset would carry the look
  of a sensor it may not have); a hue or tint param (a look: the creative
  pass).
- **To reverse.** Local to `params.build_registry`'s block and four
  `ViewState` fields.
- **Rough edge.** No panel row: Learn and ROUTING reach them. A second
  cloud node (`cloud.2`) shares them.
- **Judge it.** Check 217.

### 207. The renderer is handed the device registry; a *listed* `cloud` device adds its node to the default scene

- **Built.** `Renderer.cloud_source` (one line in `app.main`:
  `renderer.cloud_source = rig`). `graph.cloud_roles(source)` reads the
  roles of the devices whose `kind` is `cloud` (duck-typed: `graph.py`
  never imports `devices`), `Renderer._graph_for` keys the graph on them
  (row 180), and `default_graph(views, wiring, clouds)` adds one
  `PointCloud` per role (`cloud`, `cloud.2`, …) as the scene's first
  geometries. A listed device whose file is missing, not yet polled or
  closed keeps its node, which draws nothing — so a recording copied in
  later shows with no graph change. With no `cloud` entry the graph is
  the one before, node for node.
- **Other options.** Key on the clouds *present* (a rebuild whenever a
  device drops or returns); any device with a `Port(kind="cloud")` (plan
  29's sensor kinds would add themselves, but every device is asked for
  its ports each frame); a `cloud` kind in the preset's graph (ruled out
  for this run, row 197).
- **To reverse.** Local to `cloud_roles` and `_graph_for`.
- **Rough edge.** Only devices of kind `cloud` are found: plan 29's sensor
  kinds must be added to `cloud_roles` (one line) or move it to the ports.
- **Judge it.** Checks 216, 218.

### 208. The cloud's buffer is uploaded on a new (frame id, publish time); its GL objects live on the renderer

- **Built.** `graph._CloudGL` (on `Renderer._cloud_gl`, made on the first
  cloud drawn) holds the program, the quad's corners and, per node, a
  points buffer, a colours buffer and a vertex array. It writes the
  read-only float32 points only when `(cloud.frame, cloud.t)` moved — the
  publish time too, because a re-opened device counts its frames from 0
  again. A graph rebuilt for new switches re-uploads nothing;
  `Renderer.on_reload` releases them.
- **Other options.** Key on `frame` alone (a re-opened device's frame 0
  taken for the old one); buffers on the node (released or leaked on
  every rebuild).
- **To reverse.** Local.
- **Rough edge.** A node removed from the graph (its device unlisted)
  keeps its buffers until the next reload.
- **Judge it.** Check 218.

### 209. The cloud's draw is its own SYSTEM line, named after the node

- **Built.** The scene times each solid geometry under its node's name
  (row 195), so the SYSTEM page reads `cloud` (then `ghost` when the
  hands are in the scene) before `scene`. `stats["clouds"]` holds each
  cloud node's drawn point count this frame; a draw that raises is
  `stats["cloud_error"]` and the scene goes on.
- **Other options.** The cloud's time inside `scene`'s line (no way to
  see its cost).
- **To reverse.** Local to `Scene.run` and `Graph.timed`.
- **Rough edge.** `cloud_error` is on no page (the device's own SYSTEM
  line says whether it is `connected`).
- **Judge it.** Check 218.
