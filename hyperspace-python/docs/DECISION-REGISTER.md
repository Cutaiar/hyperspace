# Decision register — the open decisions

Rows 34–88 were each decided during an unattended build on 2026-10-04,
rows 89–108 during plan 22's run on 2026-10-06, rows 110–139 during
plan 24's run, rows 140–168 during plan 27's run and rows 169–209
during plan 26's run on 2026-10-14, rows 210–213 during plan 27's B6
(several gamepads at once) on 2026-10-15, rows 214–232 during plan 30's
run (shader nodes) and rows 233–277 during plan 28's run (the node
editor) on 2026-10-17, rows 278–290 in plan 28's N7 (a legible graph)
and rows 291–298 in plan 30's N8 (the palette as compression)
and rows 299–310 in plan 28's N9 (the graph by concern)
on 2026-10-20 (rows 321–339, plan 32's media, were answered by the owner
on 2026-10-22 before the build, so each is "(rec) — accepted" or
"owner"; they are at the end, after plan 31's 311–320 on its own branch):
the build took its own
recommendation and built it. Every one is in the app now (rows 110–213
on `plan-24-26-27-integration`, rows from 214 on `plan-28-30-integration`,
until the owner merges them) and waits
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
| 89 | The Heart masked; the other shapes lifted | 113, 114 | **overturned, owner 2026-10-17** (plan 28: a shape is 4D or 3D) |
| 90 | The W fold at draw time: XW → XZ, YW → YZ, ZW → XY | 114 | **overturned, owner 2026-10-17** (plan 28: a shape is 4D or 3D) |
| 91 | A masked shape cues depth on z | 114 | |
| 92 | `VOLUME_FLOOR` 0.15, from all 18 4D shapes | 113, 119 | now for the 4D shapes only (owner, 2026-10-17) |
| 93 | How a shape is lifted: the lift rules | 113, 115 | **overturned, owner 2026-10-17** (plan 28: a shape is 4D or 3D) |
| 94 | The Möbius strip widened and lifted | 115, 118 | lift **overturned, owner 2026-10-17**; the size stays |
| 95 | The Rose deepened and lifted (the orchestrator's call) | 115 | lift **overturned, owner 2026-10-17**; the size stays |
| 96 | The Klein bottle: the bottle, lifted, shape 26 | 116, 117 | **overturned, owner 2026-10-17** (plan 28: a shape is 4D or 3D) |
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
| 135 | The `@mix` directive; the palette starts at mix 0 — "no identity exists" **superseded in part** (row 291) | 166 | superseded in part |
| 136 | The palette's params: mode, anchors, twelve anchor values — `mode` as a number **superseded in part** (row 296) | 166, 167 | superseded in part |
| 137 | The palette at `@order 95` | — | |
| 138 | The fold over the absolute hue wheel; linear sat and val — `centre`/`width` and `_lo`/`_hi` **superseded** (rows 291–294) | 166 | superseded in part |
| 139 | The FX page repacked; strip rows packed by name — the palette's rows **superseded in part** (row 297) | 167 | superseded in part |
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
| 176 | The FX node is the chain, one per pipeline, the pipeline's end — **superseded by rows 214, 215** (plan 30: each effect is its own node; `Fx` is the end only) | 194 | superseded |
| 177 | The history as two nodes, `history` and `capture` | 194 | |
| 178 | The Output node is `_compose` | 194, 195 | |
| 179 | Nodes and ports: made images pulled, painted images drawn into the consumer | 194 | |
| 180 | The default graph keyed by switches, wiring and clouds; reused (plan 30 adds the effect list and the placements to the key: rows 215, 219) | 194, 195 | |
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
| 196 | The preset's `graph` section: the nodes that differ, one object each (an effect's `after` / `into` and a placed instance 1: row 219) — "wiring choices, not a graph" **superseded in part by rows 263, 266** (plan 28: a wire list, outputs as nodes) | 211 | superseded in part |
| 197 | An unreadable section: a note, the default graph, kept as written; `cloud` unknown — "the whole section falls back" **superseded in part by row 221** (a refused placement costs only that effect its place) | 211 | |
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
| 211 | A joystick per pad device (next free, or pinned); one USB reader, lent to the first `usb = true` pad with no GLFW joystick, sticky | 219 | |
| 212 | The camera job and the factory pad rows are the primary pad's; a second pad starts with no rows; one feel | 219 | |
| 213 | The hands stay single: a second hands entry is refused | 174 | |
| 214 | The pipeline end keeps the name `Fx`; its own line reads 0.00 | 220 | |
| 215 | An off effect is read through: no pass, no texture, no rebuild | 221 | |
| 216 | The effects' pool: two half-float textures plus one per held picture | 222 | |
| 217 | An effect node's name: `acid` in the scene's pipeline, `acid(scene+hands)` in the others | 220, 222 | |
| 218 | SYSTEM: a line only for an effect that ran | 220 | |
| 219 | The placement keys `after` and `into`; a placed instance 1 | 223, 224 | |
| 220 | The placeable names and which key each takes | 225 | |
| 221 | A refused placement costs only that effect its place; loops refused twice (two drafts folded) | 225 | |
| 222 | A placement on a missing node is dormant, said in words | 226 | |
| 223 | How an effect sits on an edge; the presenter gets the folded picture | 223, 224, 227 | |
| 224 | The words: "on the hands", "before the history", "on output 2 only" | 228 | |
| 225 | The three proof fixtures' extra values | 223, 224, 227 | |
| 226 | A placed chip in a grid of its own, its place after its name | 229 | |
| 227 | The FX status line adds "· N placed" | 229 | |
| 228 | Two vocabularies: the chip's and OUTPUT's | 228, 229 | |
| 229 | A dormant placement still shows as placed | 229 | |
| 230 | A placed effect aimed at the faces says "on the faces" | 230 | |
| 231 | The `VALUE` port: a fourth type, used by no node | — | |
| 232 | The faces target stays an inner chain (the lift as the other option) | 230 | |
| 233 | `patch.py`'s types: nodes by address or param id, an edge per port | — | |
| 234 | Only the params a later node reads land in the pass; the frame's mark | 232 | |
| 235 | The patch cached on a key built once a frame (about 5 µs a frame dearer) | — | |
| 236 | A loop through no delay: its last cable off, a note, the row kept (two drafts folded) | 233 | |
| 237 | A delay closing a loop runs first, one frame late (two drafts folded) | 234 | |
| 238 | The LFOs step inside the pass, every one a node | 232, 235 | |
| 239 | The equivalence oracle: the base's `modulate`, verbatim, in the test | — | |
| 240 | The six modifier kinds and their params | 236 | |
| 241 | The lane `mod:<n>`; a modifier whose input is not live reads NaN | 237 | |
| 242 | Modifier ids one past the highest; a removal leaves its routes dormant | 237 | |
| 243 | A modifier's params in its entry only, never in `values` | 238, 260 | |
| 244 | A template's modifiers: overridden by id, a save writes what differs | 239 | |
| 245 | The modifiers one undo part of the table | 240 | |
| 246 | Learn takes a `mod:` lane only when armed for anything | — | |
| 247 | The MODIFIERS strip between the routes and the desk — not drawn on ROUTING since N7: **superseded in part** (rows 288, 289) | 241 | superseded in part |
| 248 | Node and pin ids: strings with a kind prefix (the `layout` keys) | 244 | |
| 249 | Params on the render node that owns them (`OWNERS`) | 243 | |
| 250 | What the canvas draws: modulatable params and row targets; no sinks — its timing **superseded in part** (row 290) | 242, 245 | superseded in part |
| 251 | Positions: the preset's map and the show's; a drop dirties; tidy one undo step — tidy's behaviour **superseded in part** (row 285) | 244 | superseded in part |
| 252 | The tidy columns — a collapsed node's height **superseded in part** (row 278); the columns by kind **superseded** by the areas (row 299) | 244 | superseded in part |
| 253 | The editor context on the panel, closed before imgui | 246 | |
| 254 | The selection pane below the canvas; **beside** for a column — the chip **superseded** (row 286) | 245 | superseded in part |
| 255 | A cable into `mod` is the row a Learn would make | 247, 248 | |
| 256 | A cable into `base`: desk or pad setters only; the refusal words | 248 | |
| 257 | A cable's end moved input pin to input pin | 247 | |
| 258 | A free modifier dropped on a cable is inserted | 247, 249 | |
| 259 | The node picker: modifiers by kind, idle macros | 249, 250 | |
| 260 | A macro onto `mod` is refused | 248 | |
| 261 | A macro node's delete clears its label and subscribers | 250 | |
| 262 | Cable deletes: the preset's go, the session's refused | 250, 258 | |
| 263 | The wire list: `{"from", "to"}` in `wires` | 251, 252 | |
| 264 | A preset wires image ports only; a hands node's place is its `into` | 253 | |
| 265 | D1's `after` / `into` are wires written short | 251 | |
| 266 | Outputs as nodes: a wire overrides that port alone (a through output's hands folded in) | 252, 254 | |
| 267 | A refused wire: a note and that port's default | 253 | |
| 268 | The render picker; every edit read back before it lands (N3's seam folded in) | 251, 255 | |
| 269 | The two wire fixtures' look | 252 | |
| 270 | The APC40 as two nodes; a SHIFT-node drag into `base` refused | 256 | |
| 271 | The desk's port groups | 256 | |
| 272 | The SHIFT latch read from the table each frame | 256 | |
| 273 | A layered row on an invariant control drawn off on *apc40* | — | |
| 274 | A desk template as a subgraph node; an edit inside an override (two drafts folded) — its collapsed port list **superseded in part** (row 278) | 257 | superseded in part |
| 275 | A missing role is a grey placeholder | 258 | |
| 276 | The hands node's groups: axes, pinches, grab, presence, dance | 256 | |
| 277 | An older build and this run's keys: both Macs on this build before sharing | 259 | |
| 278 | A collapsed node's lines: what it holds, how much is patched, its live reading | 261 | |
| 279 | One in and one out stub a node; a render cable to a collapsed node's stub | 261 | |
| 280 | A bundle per node pair, as thick as it is many (capped), its hover the first ten | 261, 262 | |
| 281 | A bundle selected lists its rows; its Delete refused in words | 262 | |
| 282 | The collapse state is the page's, saved nowhere | 261 | |
| 283 | A drag onto a collapsed node's stub opens a picker of its ports | 263 | |
| 284 | Learn from a node's right-click, per param | 263 | |
| 285 | Tidy collapses everything, lays it out again and says what it did — into the areas, its words **superseded in part** (row 304) | 264, 274 | superseded in part |
| 286 | The details chip only with a selection on a narrow page | 264 | |
| 287 | Expand all / collapse all; "patched only" within an expanded node | 262 | |
| 288 | ROUTING's pointer line; "Route a lane here…" opens GRAPH | 266 | |
| 289 | A modifier node's side pane: the MODIFIERS strip's block, stacked | 265 | |
| 290 | A collapsed node reads only what its lines show; wiring and columns kept (the areas' layout since N9, row 299) | 261 | |
| 291 | The slice: `hue_from` → `hue_to` up the wheel, turned by a wrapping `hue_turn`; from = to one hue, 0 → 360 the whole wheel | 267, 269 | |
| 292 | The hue map: the old fold up to 180°, sliding to the identity at 360° | 267, 268 | |
| 293 | Saturation and value mapped linearly, never clamped | 267, 268 | |
| 294 | `from` above `to` inverts (sat or val) | 269 | |
| 295 | `centre`/`width` and `_lo`/`_hi` read as the slice on load (values, routes, desk rows, macros); a note only when the palette shows | 271 | |
| 296 | `// @param choice [a\|b] n "Label"`: a discrete param, drawn as a picker | 270 | |
| 297 | The strip: mode picker, "compress into" line, hue / sat / val rows `from → to` (the hue row's turn beside), a hue bar | 270 | |
| 298 | The gradient map kept as the second mode | 270 | |
| 299 | Five areas left to right: controllers → audio → modulation → geometry → shaders | 272 | |
| 300 | The audio before the modulation; the LFOs are modulation | 272 | |
| 301 | Each area's title: faint words on the canvas, no node | 272 | |
| 302 | The idle rule by kind: macros, LFOs, group nodes, lost devices | 273 | |
| 303 | The small "other" area under the audio | 272 | |
| 304 | One idle line an area; its + shows them; tidy closes it | 273, 274 | |
| 305 | An off effect with no cable is idle; a through wire spans the hidden run | 275 | |
| 306 | The shaders' chain wraps in rows of four (Z order) | 276 | |
| 307 | Frame an area: five chips on the head, or a click on its title | 276 | |
| 308 | The modulation and the audio laid out by their own depth | 272 | |
| 309 | Titles never under 12 px on screen; a short word when needed | 272 | |
| 310 | Open question: GRAPH asking for the whole control window (not built) | — | owner's call |
| 321 | Eight fixed channels `a`–`h` | 303 | (rec) — accepted 2026-10-22 |
| 322 | A bin of ≤ 16 sources plus a `slot` param | 296, 298 | (rec) — accepted 2026-10-22 |
| 323 | Bins live in the preset | 301 | (rec) — accepted 2026-10-22 |
| 324 | Source ids and places; a missing source is black plus the banner | 300–302 | (rec) — accepted 2026-10-22 |
| 325 | Live kinds are device-registry kinds that discover feeds | 304, 305, 311, 313 | (rec) — accepted 2026-10-22 |
| 326 | The transport: pos latch, rate −4…+4, jog with coast, three loop modes | 298, 299 | (rec) — accepted 2026-10-22 |
| 327 | Scrub proxies for clips ≤ 10 minutes (own worker) | 298 | (rec) — accepted 2026-10-22 |
| 328 | Threads: a pool, a thread per blocking source, the render thread only uploads | 302, 303 | (rec) — accepted 2026-10-22 |
| 329 | Caps 1080p files / 720p live; upload only consumed, new frames | 303 | (rec) — accepted 2026-10-22 |
| 330 | Backdrop under the scene, before history and effects; history off | 296 | (rec) — accepted 2026-10-22 |
| 331 | Faces read a channel; `view.bmp_*` dropped with a note; K7 kept by an alias | 297, 314 | (rec) — accepted 2026-10-22 |
| 332 | Every effect gets an `aux` input; `displace` and `blend` | 297 | (rec) — accepted 2026-10-22 |
| 333 | The phone's own page is V2; an NDI camera app in V1 | 312 | owner — 2026-10-22 |
| 334 | Phone join (V2): a token in the QR, ≤ 4, approved on the host | — | (rec), not built — 2026-10-22 |
| 335 | Resolume / TouchDesigner both ways in V1; publishers are SYSTEM lines | 304–310 | owner — 2026-10-22 |
| 336 | Dependencies: `av`, `pillow-heif`, `syphon-python`, `cyndilib` (+ avfoundation) | 311 | (rec) — accepted 2026-10-22 |
| 337 | Conditional preset `/4` (a media value, bin, or route / modifier / macro / wire naming a media id); both Macs on this build | 301 | (rec) — accepted 2026-10-22 |
| 338 | Base `plan-28-30-integration` | — | (rec) — accepted 2026-10-22 |
| 339 | No desk or APC40 default bindings; Learn for all | 299 | (rec) — accepted 2026-10-22 |

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
  zooms in, to 2.2× at the top (depth 0.0757, the 0.12 of before zoom's
  range widened on 2026-10-21 — the same 2.2×). A level, low or absent hand
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

> **Overturned by the owner, 2026-10-17 (plan 28).** A shape is honestly
> 4D or 3D (`Shape.dims`): a 3D shape sits at w = 0 and the W planes do
> nothing to it — no lift, no fold. See DECISIONS, Shapes.

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

> **Overturned by the owner, 2026-10-17 (plan 28).** A shape is honestly
> 4D or 3D (`Shape.dims`): a 3D shape sits at w = 0 and the W planes do
> nothing to it — no lift, no fold. See DECISIONS, Shapes.

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

> **Overturned by the owner, 2026-10-17 (plan 28).** A shape is honestly
> 4D or 3D (`Shape.dims`): a 3D shape sits at w = 0 and the W planes do
> nothing to it — no lift, no fold. See DECISIONS, Shapes.

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

> **Overturned by the owner, 2026-10-17 (plan 28).** A shape is honestly
> 4D or 3D (`Shape.dims`): a 3D shape sits at w = 0 and the W planes do
> nothing to it — no lift, no fold. See DECISIONS, Shapes.

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

> **Overturned by the owner, 2026-10-17 (plan 28).** A shape is honestly
> 4D or 3D (`Shape.dims`): a 3D shape sits at w = 0 and the W planes do
> nothing to it — no lift, no fold. See DECISIONS, Shapes.

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

> **Overturned by the owner, 2026-10-17 (plan 28).** A shape is honestly
> 4D or 3D (`Shape.dims`): a 3D shape sits at w = 0 and the W planes do
> nothing to it — no lift, no fold. See DECISIONS, Shapes.

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

- **Superseded in part by row 291** (plan 30 N8, 2026-10-20): the slice's
  defaults (the whole cylinder) are the identity now, so "none exists"
  below no longer holds; the palette still starts at mix 0.

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

- **Superseded in part by row 296** (plan 30 N8, 2026-10-20): `mode` is a
  `@param choice` (compress / gradient) drawn as a picker; its values are
  still 0 and 1, so a saved `mode` loads as it was. The anchors are
  unchanged.

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

- **Superseded in part by rows 291–294** (plan 30 N8, 2026-10-20):
  `centre`/`width` became the slice's ends `hue_from`/`hue_to` (and the
  turn `hue_turn`), and `sat_lo`/`_hi`, `val_lo`/`_hi` became
  `_from`/`_to`. The triangle is kept for arcs up to 180° (bit for bit:
  the D1 frames did not move), and the linear sat and val and the alpha
  scaling stand.

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

- **Superseded in part by row 297** (plan 30 N8, 2026-10-20): the palette's
  rows are mode (a picker), hue, sat and val, each `from → to`; the packing
  by name gained `_from`/`_to`.

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
- **Rough edge.** Swapping the two pad entries swaps
  which pad the bare rows mean; the second pad's qualified rows go
  dormant when it becomes the primary. A role containing `@` would read
  as a qualifier (config does not refuse one).
- **Judge it.** Check 219.

### 211. A joystick per pad device, the next free one or pinned; one USB reader, lent to the first `usb = true` pad with no GLFW joystick

- **Built.** Each pad device reads its own controller. The pads share
  one `gamepad.Claims` on the registry's context (`Context.pads`): a pad
  takes the next present GLFW joystick no other pad has taken, in list
  order (the devices poll in list order, so the first pad takes the
  first). An entry's `joystick = n` (0–15, checked in `config.py`; a bad
  value is a note and dropped) pins it: it reads only that index, waits
  for it (`lost · waiting for joystick 1`), and no unpinned pad takes it.
  An unpinned pad whose joystick leaves reads `lost`, lets the index go,
  and takes the next free one that appears. The SYSTEM line names the
  joystick read (`glfw 1`); two entries pinned to one index: the second
  is dropped with a note. **The libusb reader is one, lent, not owned**
  (the owner's amendment): one `UsbPad` (`Claims.reader`), lent each
  poll to the pad that holds it while that pad still has `usb` on and no
  GLFW joystick (**sticky**), else to the first `usb = true` pad in list
  order with no GLFW joystick; a pad that finds a GLFW joystick hands it
  back that poll. With both entries at the default `usb = true` the
  Bluetooth pad reads GLFW and the Afterglow on `p2` reads USB; the
  first pad's line says `usb: lent to p2` (no note while the reader is
  idle). It closes when the last pad that could borrow it closes. A pad
  no device attached (a tool, a test) reads the first present joystick
  and its own reader, as before.
- **Other options.** Match a pad to its entry by GUID or name (GLFW
  reports both; a re-paired Bluetooth pad keeps its GUID) — plan 28/29's
  device identity; the reader owned by the first `usb = true` entry (as
  first built: the defaults then never read a wired pad on the second
  entry); re-deciding the lend from list order every poll (not sticky: a
  pad listed earlier that loses its Bluetooth pad would take the wired
  pad from the second); one USB reader per entry (two wired pads —
  `UsbPad` takes the first 360 pad it finds, so two readers would fight
  for one).
- **To reverse.** `Pad._find` back to "the first present joystick" and
  `Pad.attach` out of `PadDevice.open`: about forty lines.
- **Rough edge.** Only one wired 360 pad is ever read; sticky means a
  pad listed earlier that loses its GLFW joystick reads `lost · usb:
  lent to p2` rather than taking the wired pad. GLFW's index for a pad can change across a reconnect, so a
  pinned pad may wait for an index its controller no longer has.
- **Judge it.** Check 219.

### 212. The camera job and the factory pad rows are the primary pad's; a second pad starts with no rows; one feel

- **Built.** Defaults author no look (decision 24): the sticks' default
  camera job (`gamepad.steer`) runs for the primary pad only — a second
  pad's unrouted sticks and triggers do nothing until a route names
  them. The factory pad rows (`bindings.default.json`) and `PAD_REMAP` /
  `PAD_NEW_ROWS` are unqualified, so the primary's; a second pad starts
  with no rows and gets them from Learn pad (it completes on whichever
  pad moves first), **Learn p2** (the second pad's own want: only it
  completes it, so it can be learned onto with the first unplugged) or
  ROUTING. The pad's feel, the five
  `desk.pad.*` session params, is one set applied to every pad
  (`Router.source_feel` reads any `axis@<role>` as `axis`).
- **Other options.** Copy the factory rows for each pad (two pads would
  both flip faces on A); run the camera job on every pad (two sticks on
  one camera); a feel per pad (`desk.pad.<role>.*` — more session params
  on SYSTEM for a case not yet played).
- **To reverse.** The `if q:` branch in `PadDevice.act`; per-pad feel is
  a new set of params and a role key in `Router.source_feel`.
- **Rough edge.** Per-pad feel is plan 28/29's. "Learn p2" is offered
  only on a param a lane can drive (`p.modulatable`), as every "Learn
  <role>" item.
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

- **Superseded by rows 214 and 215** (plan 30, 2026-10-17): every effect
  instance is now its own `Effect` node, the chain a run of them in each
  pipeline, and `Fx` the thin pipeline end that keeps the jobs below
  (where the picture lands, the stand-down, the error path). Kept here
  as history.
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

- **Amended by plan 30** (rows 215, 219): the key also holds the effect
  stack's list in order (`FxState.names()`: an order, an instance or a
  file changed rebuilds, a toggle does not) and the preset's placements
  (`Wiring.placed`).
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

- **Amended by row 219** (plan 30): an `effect` entry may also carry
  `after` or `into` (a placement), and a placed entry may name instance
  1; an unplaced one still needs `instance` ≥ 2.
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
- **Superseded in part by rows 263 and 266** (plan 28, 2026-10-17): the
  section may now carry a wire list beside its nodes, and the outputs are
  nodes a wire may feed, so a preset can say which output gets which
  hands node and which effects it alone takes; an output no wire names
  keeps the session's switches. The rough edge below is closed for the
  outputs; at most one hands node still makes the layer.
- **Rough edge.** The section is wiring choices for the default graph,
  not a graph: the outputs still come from the OUTPUT page's switches,
  so a preset cannot say which output gets which hands node; at most one
  hands node makes the layer. Keys are strict: a key this build does not
  know makes the section unreadable (row 197).
- **Judge it.** Check 211.

### 197. A section this build cannot read is a note and the default graph, kept as the file had it

- **Superseded in part by row 221** (plan 30): a placement this build
  cannot honour — both keys, a non-string, an unknown name, a loop — is
  a note ending "; the default placement" and costs only that effect its
  place; the rest of the section lands. Every other unreadable section
  still falls back whole, as below.
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

## Shader nodes (plan 30)

Built in plan 30's run on 2026-10-17
([`plans/30-shader-nodes.md`](plans/30-shader-nodes.md)), on
`plan-28-30-integration` until the owner merges it. The owner's own
decisions for this plan (1–5 and the render parts of 16 of the launch
prompt: shaders are nodes, the palette moved first, the auxiliary ports
designed and not built, no preset edited, the default graph
pixel-identical) are in [`DECISIONS.md`](DECISIONS.md) with Who
"owner"; these rows are what the build chose where those left a choice
open — the end node's name, how an off effect is skipped, the texture
pool, the placement keys and their vocabulary, refusals and dormancy,
the words, the FX page's placed chips, the `VALUE` port's shape and the
faces target. No preset was edited or added: every proof is a fixture
under `tests/fixtures/presets/`.

### 214. The pipeline end keeps the class name `Fx`, its node names and its SYSTEM lines

- **Built.** `graph.Fx` is now the thin end of a pipeline: its input is
  the last effect of its run, its `paint` paints that input (moving the
  clocks once and counting `chain_runs`), and its `run` keeps every job
  it had — straight into the one output at the frame's size, unflipped
  and on this context, else the pipeline's frame texture; `bent` /
  `fallback` through `Fx.source` / `Fx.layer`; a raise marking the
  views. The nodes are still `fx`, `fx(scene+hands)`, `fx(hands)`, and
  SYSTEM keeps their lines. The owner sees the `fx` line at **0.00**:
  the end runs no pass of its own, and the effects' time moved to their
  own lines just above it.
- **Other options.** A new class (`End`, `Pipeline`) with `Fx` gone or an
  alias: every test, tool and document naming `fx` / `Fx` changes, and
  the golden manifest's recorded `nodes` lists would move.
- **To reverse.** Rename the class and `FX_NAMES`; re-record the
  manifest's `nodes` lists (no pixel moves).
- **Rough edge.** 0.00 on `fx` does not mean the effects cost nothing:
  their cost is on their own lines (`acid`, `huecycle` …).
- **Judge it.** Check 220.

### 215. An off effect is read through by its consumer: no pass, no texture, no change to the graph

- **Built.** An `Effect` not in `FxState.chain(FRAME)` this frame
  (switched off, mix 0, the stack bypassed, aimed at the faces) or whose
  file never compiled paints its input straight into its consumer's
  framebuffer, and its `image` is its input's. Every instance is in
  every run, on or off (the run is `FxState.names()`), so switching a
  chip on or off rebuilds nothing: `Renderer._graph_for` rebuilds only
  when the list in order changes (an order, an instance, a file).
  Retargeting an effect to the faces rebuilds nothing either. Measured
  on party-acid: four passes a frame for the four on effects, none for
  the nine off.
- **Other options.** Rewire the edge around an off node each frame (the
  graph's shape follows the chips); a run holding only the on effects (a
  rebuild on every toggle).
- **To reverse.** `Effect.paint` / `image` and `_graph_for`'s key.
- **Rough edge.** Thirteen effect nodes per pipeline whatever is on (up
  to 39 with the three pipelines), seen only in `repr(graph)` and on the
  GRAPH page. A file that fails to compile reads through instead of the
  old block's copy through a half-float texture (the same picture
  within half-float rounding).
- **Judge it.** Check 221.

### 216. The effects' pool is the chain's half-float textures: two, plus one per held picture, sized by the graph

- **Built.** `FxChain.pool(size, n)` hands out the chain's `f2` textures
  (the faces' chain's `begin` hands out the pool's first framebuffer, asking for at least the textures it already holds, two at the least). `Graph.pool` is 0
  with no effect node, else 2 plus one per effect read by more than one
  node — and, since D1, one per placed effect that folds a made texture
  or an output's frame. A straight run alternates the two however long
  it is. A held picture is made once (`Effect._make(frame, avoid=dst)`,
  `graph._spare`: never the consumer's target, never a texture already
  held) and shown 1:1 into each reader. A graph that needs fewer
  textures releases the pool (`FxChain.fit_pool`); a size change makes
  all of them again; the pool grows by one if none is free.
- **Other options.** A pool owned by the graph object (the renderer's
  release paths and the hot-reload hooks would need it too); a texture
  per effect (13 × 3 half-float frames).
- **To reverse.** Local to `FxChain.pool`, `graph._spare`, `Graph.pool`.
- **Rough edge.** A held picture costs one copy more than a direct pass,
  and its second reader sees the half-float texture. The `avoid` rule is
  load-bearing: a held texture shown into itself is a GL feedback loop
  (pinned by
  `tests/test_graph_effects.py::test_a_held_effect_read_through_the_pool_is_never_its_consumers_target`).
- **Judge it.** Check 222.

### 217. An effect's node is named by the effect in the scene's pipeline and with the pipeline's suffix in the others

- **Built.** `graph.effect_node_name`: `acid`, `acid.2`, `palette` in the
  scene's pipeline — the SYSTEM line and the word a placement names —
  and `acid(scene+hands)`, `acid(hands)` in the others, as the ends are
  named. An effect whose name another node has (a `scene.glsl`, a
  `capture.glsl`, `output.2`, or `fx` against the ends) takes the
  params' prefix: `fx.scene`, `fx.fx(scene+hands)`.
- **Other options.** `fx.<name>` for every effect node (unambiguous, but
  not the word the design and the placements use); one node shared by
  the pipelines (the passes differ per pipeline).
- **To reverse.** `effect_node_name` and the collision rule in
  `default_graph`.
- **Rough edge.** With the hands through and two pipelines running,
  SYSTEM shows `acid` and `acid(scene+hands)`: correct, but two lines for
  one chip.
- **Judge it.** Checks 220, 222.

### 218. SYSTEM shows a line only for an effect that ran a pass that frame

- **Built.** `Effect.TIMED` is False, so `Graph.timed` (and the golden
  manifest's recorded `nodes`) are as before; `Graph.timed_in(frame)`
  adds the effects that ran (`frame.stats["effects"]`) in their places,
  and the renderer hands that to the timer. An effect switched off drops
  its line once its last timed frame is read back (`PassTimer.LAG`, a
  few frames).
- **Other options.** A line for every effect node, 0.00 when off (13 to
  39 dead lines).
- **To reverse.** `Effect.TIMED = True` and `end_frame(graph.timed)`.
- **Rough edge.** On Apple's tile GPU a timer query is charged when a
  render pass is flushed, so a line can carry its input's work or read
  0.00: the lines are indicative, not an exact split (party-acid: the
  old `fx` line 0.225 ms, the new lines summing to 0.089 ms, wall time
  the same within noise; the review pass measured 0.225 against 0.078
  ms, and the frame's wall time 1.34 → 1.44 ms median, about +0.1 ms,
  inside the base's spread but higher in two rounds of three). Each on
  effect's `FxChain._program` is assembled twice a frame (`ready`, then
  `run_one`): string work and a compare, never a compile — a per-frame
  cache would need a frame counter the tests' direct calls never tick.
- **Judge it.** Check 220.

### 219. The placement keys are `after` and `into`, both kept

- **Built.** An effect entry in a preset's `graph` section may carry
  `"after": "<node>"` — on that node's picture, every consumer of it
  reading the effect — or `"into": "<node>"` — on that node's `image`
  input alone — never both. A placed effect may name instance 1
  (`{"kind": "effect", "file": "palette", "after": "hands"}`), which
  takes the file itself out of the chain; an unplaced instance 1 is
  still refused ("2 or more"). The section writes instance 1 by its file
  alone and an extra instance with `instance`. The owner sees nothing in
  a factory preset; the three fixtures use one key each.
- **Other options.** One key with a port suffix (`"at":
  "output.2.image"`): it reads less plainly and needs a port vocabulary
  plan 28's wires bring anyway; `after` alone, `into: output.2` written
  `after: output.2`.
- **To reverse.** `EffectAt`, `_effect_entry`, `GraphSpec.to_json`, the
  three fixtures; plan 28's wires read both keys.
- **Rough edge.** `after: "output.<n>"` is accepted and means the same
  as `into` (an output has no picture of its own to come after); both
  are written back as the file had them. A build from before plans 28 and 30
  refuses either key and opens the preset as the default graph with a
  note (row 277).
- **Judge it.** Checks 223, 224.

### 220. The placeable names, and which key each takes

- **Built.** `scene`, `hands`, `hands.<n>` (n ≥ 2), `history`,
  `output.<n>` (n ≥ 1) and an effect instance this build has (a file on
  disk, or an extra instance the same section declares). `into` takes
  only the history, an output or an effect: the scene's and a layer's
  inputs are geometry, so `into: "scene"` is refused with "its inputs
  are geometry, not a picture: after 'scene' folds its picture". An
  effect cannot sit after or into itself. The note: `graph: palette after
  'teapot' — this build places after scene, hands, hands.2 …, history,
  output.1 …, or an effect; the default placement` (for `into`:
  "history, output.1 …, or an effect").
- **Other options.** One list for both keys, `into: scene` meaning
  `after: scene` (hides a mistake).
- **To reverse.** `placement_error`, `_PLACE_NODE` / `_PLACE_EFFECT`,
  `PLACE_WORDS`.
- **Rough edge.** `hands.<n>` is honoured only on the node that makes
  the layer (one layer per graph); otherwise the effect is dormant ("no
  hands.2 layer this frame"). Read with no list of files
  (`read_graph(section)` alone) any well-formed effect name passes and a
  missing file is dormant at build.
- **Judge it.** Check 225.

### 221. A refused placement costs only that effect its place; a loop is refused at read and again at build

Folds two of D1's drafts: the refusals, and the loops.

- **Built.** Both keys at once, a non-string (an explicit `null`
  included), a name outside the vocabulary, or a placement that makes a
  loop each give one note on the preset strip ending "; the default
  placement", and that effect goes back to the chain: an extra instance
  at its order, instance 1 as the file. The rest of the graph lands,
  and the section is kept as the file had it. A loop is found by
  following each placed effect's target through the others
  (`graph.placement_loops`): every effect on it gets `palette after
  'acid.2' — that makes a loop (palette after acid.2 into palette)`.
  `default_graph` checks again (`Graph.notes`) and `Graph.insert` refuses
  an edge whose consumer is upstream, so a hand-built `Wiring` cannot
  loop either. `read_graph` returns the notes in `GraphSpec.notes`;
  `GraphSection.read` passes it the effect files on disk. Anything else
  unreadable is still row 197's note and the default graph.
- **Other options.** Treat a bad placement like any unreadable section
  (the whole section dropped, the hands' wiring lost for one typo);
  detect loops only at build, through the sort.
- **To reverse.** `_effect_entry`'s return, `read_graph`'s notes,
  `GraphSection.read`, `placement_loops` and its two callers.
- **Rough edge.** A save writes the refused placement back unchanged (by
  design: fix it in the JSON or on plan 28's GRAPH page). Every member of
  a loop is refused, not only the last named. An explicit `null` is
  refused in Python's words: the note reads `palette after None — …`
  where the file says `null` (cosmetic).
- **Judge it.** Check 225.

### 222. A placement on a node the built graph lacks is dormant: no node, said in words

- **Built.** `default_graph` builds no node for a placed effect whose
  target is absent this frame and says why in `Graph.dormant`: `palette
  after hands — no hands layer this frame`, `palette.2 into output.3 —
  no output 3 this frame`, `… — output 2 shows no picture this frame`,
  `… — no kaleido effect in this build`, `warp after palette — palette
  is dormant this frame`. It does not fall back into the chain. The
  OUTPUT page lists `dormant: …` under the output blocks
  (`ui.dormant_lines`) and the "shows:" hover uses `graph_words(spec,
  graph.dormant)`. The graph is rebuilt when the switches change, so the
  node comes back as soon as its target exists.
- **Other options.** Put a dormant effect back in the chain (it would
  bend the whole picture where the preset said the hands only); keep a
  node with no input.
- **To reverse.** `_place_one`'s returns and `Graph.dormant`.
- **Rough edge.** Dormancy follows the switches, not "a hand is in the
  box": with the hands switch on and no hand, the node exists and has
  nothing to fold (no pass). A build from before plans 28 and 30 refuses the placement keys and opens such a preset as the default graph with a note (row 277).
- **Judge it.** Check 226.

### 223. How an effect sits on an edge: folded once in `run` after a texture, folded by the output into an output, the presenter given the folded picture

- **Built.**
  - After the scene or a hands layer, or after such an effect, the
    effect folds that texture once in its own `run`, before any pipeline
    paints, into a held pool texture (`Effect.makes`, `_made`); every
    consumer reads that picture, and a source with no picture this frame
    leaves it none.
  - On a layer (`Effect.see_through`, walked back to the source, so no
    edge carries it) the pass runs with `u_opaque = 0`, so a see-through
    pixel stays see-through, and it is laid on at the layer's
    `ghost.alpha` with the layer's depth (`Renderer.lay`). The layer's
    readout is split always: the guide and labels are never folded.
  - Into an output: `Output.folds` folds the frame texture the output
    settled on into a held pool texture and shows it; that pipeline is
    never painted direct.
  - After or into a painted node (the history, an effect of the run):
    D0's paint path, held with two readers. `after` rewires every image
    port but those that read something else of the node (`Node.REFS`:
    the face buffer, a depth, the readout). After an effect of the run,
    one placed node per pipeline. A placed node is listed after its
    source, so SYSTEM shows it under it.
  - **Presenters** (every output after the first): an output laying a
    folded layer hands `_compose` the folded texture, so `Handoff.hands`
    is folded, at its own Ghost's opacity (`Effect.ghost`: ghost 2's for
    `hands.2`); an output folded by `into` hands its presenter the folded
    frame.
  - **`fx_on`** is "an effect of a chain run is on" (`chain(FRAME)` less
    `Graph.placed_names`): with only placed effects on, a through output
    stands down as with none.
- **Other options.** Paint the layer through the effect on demand at
  each consumer (a pass per consumer, or D0's aliasing risk from a
  `lay`); an output-fold node that re-runs the pipeline (two chain runs).
- **To reverse.** `Effect.run` / `_made` / `fold` / `_one`,
  `Output.folds` / `run`, `Fx.run`'s direct test, `Graph.pool`,
  `Graph.insert`, `Renderer._compose`'s `hands_tex`.
- **Rough edge.** A presenter's `Handoff.frame` / `hands` may be a
  half-float pool texture wrapped "f1" (plan 26's contract widened, the
  docstring says so): proven by texture identity in the tests, never on
  a real second window. `into: output.<n>` on a **through** output that
  stands down this frame (no effect of its run on, or no hand drawn):
  when the output falls back to its ground, the fold has nothing to fold
  and is skipped, and the review pass's fixes (#221) say so as a dormant
  word for that frame — `palette into output 2 — output 2 stands down
  this frame` (`Graph.stood`), on OUTPUT's dormant lines and the FX
  page's chip; when it falls back to the scene pipeline, the fold does
  run, on the scene alone — the hands laid over at the output are not
  folded — and nothing says so. A glass on `hands+through` with the chain
  switched off live is the reachable case: the palette stops folding the
  hands there.
- **Judge it.** Checks 223, 224, 227.

### 224. The words: "on the hands", "before the history", "on output 2 only"

- **Built.** `graph.placement_words`: after the hands `palette on the
  hands` (`on hands 2`); after the scene `acid 2 before the history`
  (the history and the capture both read it); into the history `acid 2
  into the history only`; after it `palette after the history`; an
  output `palette 2 on output 2 only`; after an effect `palette after
  acid 2`; into one `palette before warp`. `graph_words` appends them,
  or the dormant words. The OUTPUT "shows:" line adds the placements on
  what that output shows (`· palette 2 on this output only` for its own
  fold); LOOKBACK's history line adds those on the history's way in or
  after it.
- **Other options.** The node words as written (`after scene`, `into
  output.2`): less readable at distance.
- **To reverse.** `placement_words`, `output_placement_words`,
  `history_words`.
- **Rough edge.** LOOKBACK reads `history: the scene · acid 2 before the
  history` (a little redundant); a placed extra instance still counts in
  `palette ×2` on the graph line.
- **Judge it.** Check 228.

### 225. The three proof fixtures and their extra values

- **Built.** Each fixture is a factory preset's `values`, `routes` and
  `macros`, with no `desk` or `modules` (like `hands-lines`), plus:
  `palette-hands.json` — party-tracer, the palette `after: "hands"`, on,
  mix 1, centre 200, width 60 (hue 170 → 230 since N8, row 295), and `fx.on: true` (party-tracer bypasses
  the stack, so the palette would never run); `palette-glass.json` —
  party-acid, the palette `into: "output.2"` with the same values, so
  the output visibly folds; `acid-scene.json` — party-mandala, a second
  acid `after: "scene"` with party-acid's acid (bend 0.04, twist 0.9,
  reach 10, breathe 0.35), on, mix 1, and `dream.on: true`
  (party-mandala has the look-back off, and "the echoes hold the bent
  scene" needs echoes). 24 goldens, recorded once.
- **Other options.** The default palette (width 360, which barely shows);
  the look-back left off in acid-scene (nothing of the capture shown).
- **To reverse.** Edit the fixtures and re-record their goldens
  (`--only`).
- **Rough edge.** No desk, so a fixture loaded at the machine has no
  APC40 rows (the desk is Dylan's). No fixture places two instances of one file (check 231 uses a hand-made variant; no test loads that configuration). `palette-glass` folds output 2,
  which on the testing guide's rig (D1: the glass output 1) is the
  projector.
- **Judge it.** Checks 223, 224, 227.

### 226. A placed effect's chip sits in a grid of its own, its place after its name

- **Built.** The FX page still edits the default chain. An effect the
  loaded preset places leaves the chain's grid for a second grid under
  it, three to a row: `Warp · after hands`, `Palette · into output 2`,
  `Acid 2 · after scene`, cut with an ellipsis to fit
  (`ui_fx.placed_label`). The name's hover has the place whole, "placed
  by the preset's graph, not in the chain: moved in the preset's JSON,
  not by a drag", and `dormant: …` when the built graph has it dormant.
  It is no drag source and no drop target, and a drop among the chain's
  chips never rewrites a placed effect's order (`_drop` works over the
  chain). Its LED switches it; its name opens its strip, whose title
  hover reads `warp.glsl · after hands` in place of `#20`. The words
  come from `graph.placed_chips(spec)`. Two grids of a and b chips take
  at most one row more than one of a + b: the page never scrolls at the
  control size.
- **Other options.** One chip to a row with the words beside it (the
  first build: it scrolled with three placed effects); the chip in its
  grid place with a mark and the place on hover only (unreadable at
  distance, and it looks reorderable).
- **To reverse.** `ui_fx.page`'s second grid, `_chip(place=, dormant=)`,
  `placed_label`, `_drop(placed=)`.
- **Rough edge.** A long label and place is cut (`Kaleidoscope ·
  aft…`). The page reads the preset's spec (`Panel.graph_now`), not the
  built graph: a placement refused only at build would still show as
  placed (none reaches it: `read_graph` refuses loops first).
- **Judge it.** Check 229.

### 227. The FX status line keeps the chain's labels and adds the count of placed effects that run

- **Built.** Under the bypass, the running chain's labels without the
  placed effects, then ` · N placed`: `Acid → Palette · 1 placed`, or
  `nothing in the chain · 1 placed`. N counts placed effects that are on
  (mix above 0), aimed at the frame and not dormant in the built graph.
  With nothing placed the line is byte-identical to before.
- **Other options.** The prompt's literal `3 in the chain · 1 placed`
  (drops the labels the line has always shown and the FX tests assert).
- **To reverse.** `ui_fx._status`.
- **Rough edge.** The count says how many, not which (the placed grid
  says which).
- **Judge it.** Check 229.

### 228. The chip's place words and OUTPUT's placement words are two vocabularies

- **Built.** The FX chip (`graph.placed_chips`) uses the key and the
  node — `after hands`, `into output 2`, `after scene`, `into history`,
  `after acid 2` — the edit view, worded like the JSON. OUTPUT's
  "shows:" line and LOOKBACK (`graph.placement_words`, row 224) say
  what the picture gets — `palette on the hands`, `acid 2 before the
  history`, `palette 2 on output 2 only` — the show view. Plan 28's N4
  extends `placed_chips` for wires.
- **Other options.** One vocabulary (`palette on the hands` is too long
  for a chip; `after hands` reads poorly on the output line).
- **To reverse.** Have `placed_chips` call `placement_words`.
- **Rough edge.** One placement reads two ways on two pages.
- **Judge it.** Checks 228, 229.

### 229. A dormant placement still shows as placed, said only in the hover and the count

- **Built.** A placed effect whose node the built graph lacks this frame
  keeps its chip in the placed grid with the same words; its LED and
  strip still work. Its hover adds `dormant: palette after hands — no
  hands layer this frame`, and the status count leaves it out. OUTPUT's
  `dormant:` lines (row 222) say it in full.
- **Other options.** Dim the chip or add `(dormant)` to its label (the
  label is already cut at three to a row); hide the chip (then it
  cannot be switched or edited until its node comes back).
- **To reverse.** Pass `dormant` into the label in `_chip`.
- **Rough edge.** A lit chip can run nothing, with only the count and
  the hover saying so.
- **Judge it.** Check 229 (with every output's hands switch off).

### 230. A placed effect aimed at the faces says "on the faces" and is not counted as placed

- **Built.** An effect both placed and aimed at the faces runs in the
  faces' chain, not on its edge (row 232). Its chip reads `Warp · on the
  faces`, its hover "placed after hands, aimed at the faces: it runs in
  the faces' chain", the status count leaves it out and the faces row
  lists it.
- **Other options.** Refuse the placement at load when the effect is
  aimed at the faces (but `target` is a param a person can change at any
  time: a load-time check on a live value).
- **To reverse.** `_chip`'s words and `_status`'s count filter.
- **Rough edge.** The preset says `after hands`; the chip does not.
- **Judge it.** Check 230.

### 231. The `VALUE` port: a fourth type, named, used by no node

- **Built.** `graph.VALUE = "value"` beside `IMAGE`, `MASK` and
  `GEOMETRY` (`graph.PORT_TYPES` holds the four): a scalar or a small
  float vector a node publishes once a frame. Its docstring names its
  two uses — the palette's `palette` value out (centre, width, the sat
  and val ranges, the ramp's anchors; its slice's ends since N8, row
  291) for a lights sink (plan 29), and
  an image-in `sample` port on the palette that would set its params
  from a bitmap. No node publishes or reads one (a test walks every
  `Node` class and the built default graph). `patch.RENDER_VALUE =
  "value"` names it on the modulation side, as a future source whose id
  is the node's port (`palette:palette`); `patch.py` stays a leaf.
  `Node.__init__` already type-checks a wired port, so the first node to
  declare one wires like any other. Nothing to see.
- **Other options.** A typed shape (a `ValuePort(n, names)` naming the
  vector's fields); deferring the type to plan 29. Both rejected for
  now: built with nothing to read them.
- **To reverse.** Delete `VALUE`, `PORT_TYPES` and `RENDER_VALUE`
  (nothing reads them).
- **Rough edge.** The vector's layout (which float is the centre) is
  undecided until a node publishes one.
- **Judge it.** None at the machine: nothing is drawn.

### 232. The faces target stays an inner chain

- **Built.** `target = faces` still runs inside the shape's face drawing
  (`render.face_fx`, `FxChain.run`), not on a graph edge. The
  `fx.<name>.target` tip (an ONTO chip's hover) ends: "On the faces it
  runs inside the shape's face drawing: the one shader run the render
  graph does not show, and a placement in the preset's graph does not
  move it." An effect both placed and aimed at the faces runs there
  (row 230).
- **Other options.** The lift, "faces as a layer": the shape's faces
  drawn to a texture of their own, an image edge where any effect can
  be placed — a change to the scene's drawing that puts the face pass's
  translucency and depth at stake.
- **To reverse.** Build the lift (a plan of its own).
- **Rough edge.** The graph and the GRAPH page do not show this one
  shader run; SYSTEM times it inside `scene`. Placement is not checked
  against `target`.
- **Judge it.** Check 230.

## The node editor (plan 28)

Rows 278–290, plan 28's N7 (2026-10-20), are under "A legible graph"
below.

Built in plan 28's run on 2026-10-17
([`plans/28-node-editor.md`](plans/28-node-editor.md)), on
`plan-28-30-integration` until the owner merges it. The owner's own
decisions for this plan (6–16 of the launch prompt: one editor for both
graphs, dependency order removing the lag, modifiers in the preset, two
ports per param, values and triggers, roles not serials, the APC40 as
two nodes, both graphs as plain JSON, no GLSL in the graph,
`imgui_node_editor`, the processes) are in [`DECISIONS.md`](DECISIONS.md)
with Who "owner"; these rows are what the build chose where those left a
choice open — the patch's types and order, the frame's mark, loops and
the delay, each modifier kind's params, the `mod` lane, where positions
live, what the canvas draws and how a drag lands, the wire list, outputs
as nodes, the APC40's two nodes, placeholders — and one compatibility
fact the review pass found (277). No preset was edited or added: every
proof is a fixture under `tests/fixtures/`. Folds: N0's "a delay's
place" and "a delay closing a loop" are row 237; N0's "a loop of
modifiers alone" is in row 236; N3's "the seam with N4" is in row 268;
N4's "a hands wire on a through output" is in row 266; N5's "an edit
inside a template" is in row 274.

### 233. `patch.py`'s types: nodes by address or param id, an edge per port

- **Built.** `PatchNode(id, kind, delay=False)`, kinds `source lfo
  modifier macro param`; a source's, an LFO's or a modifier's id is the
  address a row names (`lane:0`, `lfo:0`, `mod:3`, `hand:right.y`), a
  param's or a macro's its param id — an address has a `:`, an id never
  does. `PatchEdge(src, dst, port, cable, enabled)`, ports `mod`, `when`
  (a row's gate orders before the row: a gate on an `lfo:` lane needs
  it), `depth`, `base`, `in`, and every LFO knob `shape rate sync depth
  phase reset` plus `trigger` (`lfo.trigger` → every LFO); a modifier's
  own param edge is named by its param. `cable` is the route's `(source,
  target)`. `order` is a stable DFS post-order (dependencies first, ties
  in insertion order); `cycles` lists every elementary loop once (capped
  at 256).
- **Other options.** Nodes as a list; a gate folded into the `mod`
  edge; only `depth / rate / phase` as LFO ports (the prompt's list).
- **To reverse.** Small: `patch.py` is data; the GRAPH page draws from
  the table, not from it.
- **Rough edge.** A switched-off row is in the patch as disabled edges
  (not run); a cable cut by a loop looks the same in the patch.
- **Judge it.** Tests only.

### 234. Only the params a later node reads land in the pass; `Param.apply` is idempotent by a frame mark

- **Built.** `Router.modulate` lands (`Param.apply`) only a param that a
  later node of the pass reads — a `scale`, a macro behind a depth
  subscriber, an LFO knob, a modifier's own param. Every other param
  lands in `reg.apply()` exactly as before, in registry order.
  `Registry.begin_frame()` opens a mark (`Registry.frame`,
  `Registry.landed`); `Param.apply(mark)` returns at once under a mark
  it has seen; `Registry.apply()` passes the mark and closes it, so an
  `apply()` with no pass before it (tests, `Registry.remove`) lands
  everything. `Registry.nonfinite` also names a param that dropped a NaN
  inside the pass. The owner feels it as "a frame earlier" where a value
  was read stale, nothing else.
- **Other options.** Land every param node in the pass (a leaf trigger —
  a band-layout change, `preset.select` — would fire mid-pass, in patch
  order); a per-param flag cleared by `Registry.apply`.
- **To reverse.** One condition in `_rebuild_patch` (land always).
- **Rough edge.** A read param lands in patch order, not registry order:
  the same value at another moment in the frame. A test that calls
  `p.apply()` by hand between `modulate` and `reg.apply()` on such a
  param lets it go.
- **Judge it.** Check 232.

### 235. The patch is cached on a key built once a frame

- **Built.** `Router.patch` is rebuilt when `_patch_key` moves: every
  performer row by identity and its `source target op enabled scale
  when`, `macros_serial`, every macro subscriber (identity, `depth`,
  `base`), the modifiers' `(id, kind, inputs)`, the LFO count and
  `Registry.serial` (new: moves on every `add` / `remove`). A row's
  `value`, `rest`, `motion` and a subscriber's range are read live.
- **Other options.** A serial bumped by every table edit door (the table
  is also mutated in place, by ROUTING and by tests: a missed door would
  run a stale patch).
- **To reverse.** `_patch_key`.
- **Rough edge.** `Router.modulate` costs about 5 µs a frame more:
  31.4 / 30.5 µs on the base, 37.2 / 35.0 µs now (party-trip, 21 routes,
  the hand tape, 2000 frames × 5 rounds, twice), mostly this tuple and
  undo's fingerprint of the modifiers — 0.2% of a 60 Hz frame. A table
  replaced by an identical one at the same `id` would not rebuild
  (vanishingly unlikely).
- **Judge it.** Tests only.

### 236. A loop through no delay keeps its last cable off, with a note; the row stays

Folds N0's "a loop of modifiers alone".

- **Built.** A loop that passes through no `delay` modifier is broken at
  its **last cable in table order** among those on it: that cable's
  edges are disabled in the patch, the row stays in the table, enabled,
  and saves as written. One note per cut under ROUTING's head, in the
  warning colour, while the loop stands: `loop: lfo:0 → lfo.2.rate →
  lfo:1 → lfo.1.depth → lfo:0 needs a delay — lfo:1 → lfo.1.depth is off
  until it has one`. A loop of modifiers alone (no cable on it) keeps the
  last modifier's input on the loop off, in id order — that modifier is
  dormant — with `loop: mod:1 → mod:2 → mod:1 needs a delay — mod.2's
  input mod:1 is off until it has one`. Loops are cut one at a time and
  listed again after each cut. A macro's base subscriber never closes a
  loop (a scene-setter at step 3). GRAPH's hover on the cut cable says
  "off: a loop needs a delay".
- **Other options.** Switch the row off in the table (the preset dirty,
  `enabled: false` saved); the note in `table.notes` (cleared by any
  edit while the loop stands); labels in the note; cut the loop's first
  input.
- **To reverse.** `_rebuild_patch`'s loop; two lines in `ui_routing.head`.
- **Rough edge.** The row's checkbox still reads on; the modifier's input
  combo still shows the cut input. The note uses node ids, not labels.
  An LFO owning its own depth, which ran before with a frame of lag, is
  refused until a delay sits in it.
- **Judge it.** Check 233.

### 237. A delay orders like any node unless it closes a loop; then it runs first, one frame late

Folds N0's two delay drafts.

- **Built.** An edge into a delay orders like any other (a plain delay
  runs after its input and uses N1's stateful step: its rest first, then
  one frame late), unless the delay reaches that edge's source again
  (`patch.ordering`): then the edge does not order, the delay runs
  first and emits its input's lane as it stood — last frame's — so a
  loop through it is exactly one frame late; on the loop's first frame
  it emits its rest (0). `cycles` lists no loop through a delay.
- **Other options.** Every edge into a delay non-ordering (a delay on a
  computed lane, stepped statefully, would be two frames late); a
  loop-closing delay that reads NaN when its other source goes (the
  loop could never restart).
- **To reverse.** `patch.ordering` and `_step_modifier`'s `early`.
- **Rough edge.** If the loop's other source goes away the early delay
  emits its rest, not NaN; it passes ±inf through (harmless:
  `Param.modulate` drops non-finite, and a modifier reading it drops its
  memory).
- **Judge it.** Check 234.

### 238. The LFOs step inside the pass, every one a node

- **Built.** `Router.use_lfos(lfos, clock)` (`app.main`, once);
  `Router.modulate(analyzer, dt, now)` calls `LFOs.begin` (a held
  trigger lands) and `LFOs.publish`, then `LFOs.step_one` at each LFO's
  node. Every LFO is a node whether or not a cable touches it, so each
  steps once a frame, in index order unless a dependency says otherwise
  (a random LFO's draws follow that order). A per-LFO reset is held for
  the next step only if that LFO has already stepped at this time
  (`LFO.at`), so a reset fired earlier in the pass lands at phase 0 the
  same frame. `LFOs.step` is `begin` + every `step_one`, for a caller
  with no router; a bare `Router` steps no LFO. `app.frame` no longer
  steps or publishes them (`ORDER` lost its two entries).
- **Other options.** The bank passed to every `modulate` call.
- **To reverse.** `app.frame` back to `lfos.step` / `publish` before
  `router.modulate`; `use_lfos` dropped.
- **Rough edge.** `tools/preset_shots.py`, `tools/undo_demo.py` and
  `tools/faces_page_shots.py` keep the old frame shape (the LFOs stepped
  outside, no `use_lfos`): they lag a frame on an LFO-on-LFO patch,
  harmless for stills, never a double step. A hot reload of `routing`
  into an `app.py` from before this run keeps the old order.
- **Judge it.** Checks 232, 235.

### 239. The equivalence proof's oracle is the base build's `modulate`, verbatim, in the test file

- **Built.** `tests/test_routing.py::_lagged_modulate` is the base
  build's `Router.modulate` (5d18192) copied verbatim, checked bit for
  bit against the real base over all 23 factory presets before the
  change. `test_every_factory_preset_lands_the_same_values_one_frame_earlier`
  plays every factory preset with the synthetic hand tape on both and
  asserts every modulatable param and every LFO output identical, or
  shifted exactly by the base's computed lag (`_lag_of`). The lanes are
  held and LFO 1 is a held square wave, so a lagged term times a moving
  one cannot blur the shift. Three named pairs keep it from being
  vacuous: party-trip's `camera.zoom`, lfo-breathe's `view.bright`,
  party-tumble's `rot.rate.ZW` (the `scale` path).
- **Other options.** A test-only flag in `Router.modulate` (a second
  `p.modulate` call site, which the boundary walk forbids); a committed
  recording (large, and it could not follow a helper's change).
- **To reverse.** Delete the function and the test.
- **Rough edge.** It shares the Router's helpers (`_resolve_lane`,
  `gated`, `rest_of`, `feel_of`, `_move`), so it proves timing and
  order, not the helpers. No factory preset carries a modifier or a
  delay: those are proven by `test_patch` and `test_modifiers` only.
- **Judge it.** Tests only.

### 240. The six modifier kinds and their params

- **Built.** Each param a registry param `mod.<n>.<p>` (group `mod`,
  performance, modulatable). `curve`: `shape` −1…1 (y = x^(4^shape):
  0 straight, +1 x⁴, −1 x^¼; input clamped 0…1), `invert`. `scale`:
  `mul` −4…4 (1), `offset` −1…1 (0), `clamp` (on by default: held in
  0…1). `smooth`: `attack` 0…2 s (0.05), `release` 0…4 s (0.35),
  `spring` (off) — `motion.follow` about 0; spring on is a
  `motion.spring` with ω = 1/attack, damping 0.6; the first reading is
  taken as it is. `combine`: `how` add · mul · min · max · cross (add),
  `balance` 0…1 (0.5, the crossfade only). `threshold`: `on` 0.6, `off`
  0.4 (an off above on reads as on), `hold` 0…2 s (0.1): 1 on the rising
  edge and while the hold lasts, again only after falling under `off`.
  `delay`: no params, last frame's input, 0 on its first frame.
- **Other options.** An S-shaped curve as well as the exponent; a spring
  with its own Hz and damping; add clamped to 0…1.
- **To reverse.** Small: `modifiers.PARAMS` and the kind functions; a
  preset holding a param that goes away keeps loading.
- **Rough edge.** A spring smooth has no release; a combine `add` can
  exceed 1 (a `position` route clamps it, a `push` does not).
- **Judge it.** Check 236.

### 241. A modifier's lane is `mod:<n>`; a modifier whose input is not live reads NaN

- **Built.** Modifier `mod.<n>` publishes lane `mod:<n>` (the lane index
  is n; index 0 unused, never offered), labelled `<n> <kind>` ("mod 2
  combine" on ROUTING), rest 0, its signal kind in
  `Router.lane_kinds["mod"]` ("trigger" for a threshold, whose lane is
  also a gate a route's `when` may wait on). A modifier whose input is
  not live this frame — a scheme never fed, a name the rig lacks, an
  input not chosen, a hand out of the box — is dormant: its lane reads
  NaN, so a route on it lets go and the base returns, as on that source;
  its memory starts afresh when the input comes back. A non-finite
  output counts as dormant for that frame.
- **Other options.** A dormant lane at its rest 0 (the prompt's words: a
  `position` route would pin its target at 0); a names map
  (`mod:smooth1`).
- **To reverse.** One line in `Router._step_modifier`.
- **Rough edge.** A combine with one dormant input is wholly dormant. On
  its input's return a threshold already above `on` fires at once (a
  hand re-entering the box hot is a rising edge), and a smooth takes its
  first reading as it is, with no glide in.
- **Judge it.** Check 237.

### 242. Ids are one past the highest; a removal leaves its routes dormant

- **Built.** `modifiers.next_id` is one past the highest id held, so a
  removed modifier's number is not reused while a higher one stands.
  Removing a modifier drops its params; a route on its lane stays,
  dormant (a load drops such a route with a note instead).
- **Other options.** The lowest free number; removing the routes on its
  lane with it.
- **To reverse.** `next_id` / `Bindings.remove_modifier`.
- **Rough edge.** Removing the highest and adding again reuses its
  number, and a dormant route left on that lane wakes on the new node.
- **Judge it.** Check 237.

### 243. A modifier's params live in its entry only, at their bases

- **Built.** `{"id", "kind", "in", <params>}` (an enum by name, a toggle
  as a bool), at their bases (a performer riding one never reaches the
  file). `values` leaves out every `mod.*` id, and a `mod.*` id written
  into `values` by hand is ignored with a note. The `modifiers` key is
  written only when there is one, so an older preset saves byte for byte
  as before. `mod` is a performance group with no module presets
  (`preset.NO_MODULE`, beside `macro`; the PRESETS overview leaves it
  out).
- **Other options.** The params in `values` too.
- **To reverse.** `Presets._values`.
- **Rough edge.** None known.
- **Judge it.** Checks 238, 260.

### 244. A desk template's modifiers: the preset's override by id; a save writes only what differs

- **Built.** A preset that names a template lands the template's
  modifiers with its own overriding by id (the merged set held and drawn
  in id order), and a save writes only the entries that differ from the
  template's as the load read them (the desk's `compact_desk` rule), so
  a fix to the template reaches every preset that uses it at the next
  load.
- **Other options.** A save writing the whole list (a template fix would
  never reach a preset saved once).
- **To reverse.** `Presets._modifiers_part`.
- **Rough edge.** A template's modifier the preset removed comes back at
  the next load: there is no "none" entry.
- **Judge it.** Check 239.

### 245. The modifiers and their params are one undo part of the table

- **Built.** `undo.TABLE_GROUPS = ("mod",)`: the modifiers are watched as
  one table part, their params not as bases, so adding, removing, an
  input picked and a param's drag are each a step, and a restore puts
  the node and its params back together (`Bindings.set_modifiers`). The
  strip's +, × and input combos push named steps ("add modifier
  smooth", "delete modifier mod.2", "modifier input mod.2"); an input
  pick replaces the modifier whole, and picking the input it already
  reads is no step.
- **Other options.** The params watched as bases (adding a modifier, a
  new id, would be no step).
- **To reverse.** `undo.TABLE_GROUPS`.
- **Rough edge.** A restore re-declares every `mod.*` param (a performer
  riding one picks it up again next frame).
- **Judge it.** Check 240.

### 246. Learn takes a `mod:` lane only when armed for anything or for "mod"

- **Built.** `Learn.accepts` takes a `mod:` lane for a learn armed with
  no `want` or for "mod", never a desk, pad, hand or role learn;
  `learn_source("mod:1")` lands a push or position route like a hand
  axis. No "Learn modifier" menu entry: nothing physical moves a
  modifier. (On GRAPH a modifier's lane is dragged onto a `mod` stub
  instead.)
- **Other options.** A "Learn modifier" entry that waits for a
  modifier's output to move.
- **To reverse.** Two lines in `Learn.accepts`.
- **Rough edge.** None known.
- **Judge it.** Tests only (`tests/test_modifiers.py::test_learn_takes_a_mod_lane_as_a_continuous_source`).

### 247. The MODIFIERS strip sits between the routes and the desk, a line and a params line each

- **Built.** A title with a kind combo and **+ modifier** flush right;
  per modifier `MOD n`, its kind, an input combo per input (the route
  sources plus the other modifiers' lanes, never its own), the live
  output bar and number ("dormant" while not live), ×; a second line of
  its params as the panel's own widgets (slider, checkbox, combo), so
  Learn, "Route a lane here…" and base → effective come with them. The
  kind is fixed once added. The page filter matches a modifier by id,
  "mod n", kind and inputs.
- **Other options.** A kind combo per modifier (changed in place); the
  strip under the macros.
- **To reverse.** `ui_routing.modifiers`.
- **Rough edge.** Three params on the narrow panel make short sliders;
  no live bar of the inputs.
- **Judge it.** Check 241.
- **Superseded in part by rows 288 and 289** (plan 28 N7, 2026-10-20):
  the strip is no longer drawn on ROUTING (its pointer line to GRAPH is
  there); its per-modifier block (`ui_routing.modifier_block`) is the
  editor of a selected modifier node in GRAPH's side pane, stacked, and
  a modifier is added from GRAPH's right-click picker. `ui_routing.modifiers`
  itself is unchanged.

### 248. Node and pin ids are strings with a kind prefix; the widget's integers are a per-panel map

- **Built.** Nodes `device:<role>` (`device:<role>/global` for the SHIFT
  node), `template:<name>`, `source:<scheme>`, `analyzer`, `lfo.<n>`,
  `mod.<n>`, `macro.<n>`, `render:<node>` (`render:eye`,
  `render:output.<n>`), `group:<group>`. Pins `out:<address>`,
  `base:` / `mod:` / `depth:<pid>`, `in:<mod id>.<k>`, `bus:<macro id>`,
  `rin:<node>/<port>`, `rout:<node>`. The node ids are the `layout` keys
  the owner sees in a preset or show file. `ui_graph` maps each string to
  a stable int for the editor.
- **Other options.** Strings hashed to ints (collisions); bare names
  (`shape`, which clashes with the band `scene` group).
- **To reverse.** The layout keys change: a saved `layout` would need
  migrating.
- **Rough edge.** A render node a later plan renames loses its saved
  position.
- **Judge it.** Check 244.

### 249. Params sit on the render node that owns them by one table; the rest a node per group

- **Built.** `graphview.OWNERS`: `view` / `rot` / `pattern` → `shape`;
  `ghost[.<n>]` → that hands node; `cloud` → the first point cloud;
  `dream` → `history`; `fx.<effect>.*` → that effect's node in the
  scene's pipeline (else its first), `fx.on` / `mix` / `select` → `fx`;
  `camera` / `eye` → `render:eye` (the shared camera, no image port);
  `output.<n>.*` → that output. Every other group, and a mapped one
  whose node is not in this frame's graph, is `group:<group>`. `lfo.<n>.*`
  sit on their LFO, `mod.<n>.*` on their modifier, `macro.<n>` on its
  bus node.
- **Other options.** One "misc" node; the camera on `shape`.
- **To reverse.** One dict.
- **Rough edge.** With no render graph yet (before the first frame, or
  headless) everything falls to group nodes. Effects in the other
  pipelines (`acid(hands)`) carry no params.
- **Judge it.** Check 243.

### 250. The canvas draws every modulatable param and every row's target; setters into `base`; no sinks

- **Built.** Param ports are every modulatable non-alias param plus any
  param a route, a desk / pad / key row or a macro sub names. Desk, pad
  and key rows are `setter` cables into `base` (keys from a grey
  `source:key` node). A route's `scale` and `when` are said on its
  hover, not drawn (a param has no output pin). Sink rows are not drawn.
  Only macros with subs, a label or a cable get a node.
- **Other options.** Every param (~700 ports); only the routes.
- **To reverse.** The filters in `graphview.build`.
- **Rough edge.** The APC40's ~100 desk rows make many base cables,
  faint while idle. Setters are faint, not dashed (`ed.link` draws no
  dash): only the square `base` stub tells one from a route. The page
  costs 2.78 ms median at 960 × 900 on party-trip (55 nodes, 239
  cables, patched only; about 3.8 ms with every node expanded,
  headless); `route_said` runs per route per frame and `key` builds a
  tuple over every binding each frame.
- **Judge it.** Checks 242, 245.
- **Superseded in part by row 290** (plan 28 N7, 2026-10-20): every node
  now starts collapsed, a value / trigger cable with a collapsed end is
  folded into one wire a node pair (row 280), and the page draws in
  1.27 ms median on party-trip at 960 × 900 (64 wires for 238 cables);
  "patched only" is the view inside an expanded node (row 287).

### 251. Positions: the preset's map for the look's nodes, the show's for the rig's; a drop dirties; tidy forgets

- **Built.** `preset["layout"]` holds the modifiers, macros, every render
  node but the outputs (`render:eye` among them: its ports are
  performance params) and performance-group nodes; the show's `layout`
  the devices, sources, the analyzer, the LFOs, the outputs and
  session-group nodes (`graphview.home`). Whole canvas units, written
  sorted, one node a line, only for a node the owner dropped (on mouse
  release); auto-placed nodes are never written. The preset's map is in
  its `signature()` and the show's in `Project.is_dirty`, so a drop
  dirties. **Tidy** deletes the canvas's nodes from both maps and lays
  everything out again, with no confirmation and as one undo step ("tidy
  the graph"; redo puts the tidy back). The library's marks carry both
  maps, so undoing a load puts the earlier positions back. An unreadable
  entry is dropped with a note; no key, no note and no dirt.
- **Superseded in part by row 285** (plan 28 N7, 2026-10-20): tidy also
  collapses every node, frames the canvas and says what it did ("laid
  out 55 nodes, every one collapsed", or "already tidy").
- **Other options.** Everything in the preset; auto positions written
  too (noisy diffs).
- **To reverse.** `graphview.home`, `Presets.layout`, `Project.layout`.
- **Rough edge.** A drag on its own is not an undo step: positions come
  back only with the undo of a load or a tidy. Undoing an earlier load in
  the same show also puts the show's positions back as they were then,
  losing a later drag of a rig node.
- **Judge it.** Check 244.

### 252. The tidy columns: sources, LFOs, modifiers, macros, groups, the render graph by depth, outputs

- **Built.** Left to right: sources (devices, the template, keys, the
  analyzer) 0, LFOs 1, modifiers 2, macros 3, param-group nodes 4, render
  nodes from 5 by their depth in the render graph, outputs last; stacked
  down each column by estimated height (a node's own expand and folds
  counted, so expanding one pushes the unplaced nodes under it down).
  Placed nodes take no room; dropping a node re-stacks the rest of its
  column.
- **Superseded in part by row 278** (plan 28 N7, 2026-10-20): a collapsed
  node (the default) takes its title and its lines' room, an expanded
  one its ports' and its chip line's.
- **Superseded by row 299** (plan 28 N9, 2026-10-20): the columns are the
  concern areas' (controllers → audio → modulation → geometry →
  shaders), not the kinds'; `graphview.COLUMN` is gone.
- **Other options.** One render column.
- **To reverse.** `graphview.COLUMN` / `_columns`.
- **Rough edge.** Thirteen effects a pipeline make a wide canvas; port
  positions are estimated, not measured.
- **Judge it.** Check 244.

### 253. The editor context lives on the panel; `Panel.close` destroys it

- **Built.** `panel._graph["editor"]` is made on the page's first draw
  (`Config.settings_file = ""`: no `NodeEditor.json` anywhere). A hot
  reload of `ui_graph` keeps it, so no second context is made.
  `Panel.close()` → `ui_graph.close` runs at quit and in ⌘R's close list
  (`close_all(…, panel, …)`) before imgui shuts down; twice is safe.
- **Other options.** Destroy and recreate on reload (selection and zoom
  lost).
- **To reverse.** `ui_graph._state` / `close`.
- **Rough edge.** A reload of `ui.py` re-classes the Panel and the state
  survives it too. The test rig closes the panel in its teardown.
- **Judge it.** Check 246.

### 254. The selection pane goes below the canvas; **beside** or a wide page puts it in a side column

- **Built.** CONTROLS is `ui.PANEL_W` 540 px wide, so the page is about
  420 px: the ROUTING row or effect strip of the selection shows in a
  240 px pane under the canvas by default. The head's **beside** chip,
  or a page at least 720 px wide (CONTROLS widened by hand), puts it in a
  320 px column beside. The effect strip is `ui_fx.strip(panel, name)`,
  factored out of the FX page unchanged.
- **Other options.** Always beside (a canvas about 100 px wide at the
  default size); a lower threshold (the same).
- **Superseded by row 286** (plan 28 N7, 2026-10-20): the **beside** chip
  is gone; **details beside / below** shows only while something is
  selected on a page narrower than 720 px.
- **To reverse.** `ui_graph.page`'s `wide`.
- **Rough edge.** The selection is read a frame late (last frame's
  canvas).
- **Judge it.** Check 245.

### 255. A cable into `mod` makes the row a Learn would make (`learn.row_for`)

- **Built.** A source dropped on a param's round `mod` stub is
  `Bindings.add` of the row `learn.row_for` returns (`Learn._row`'s
  table moved to module level, unchanged): a **push** when the source is
  centred (the device port's `bipolar`: a hand's roll, a stick) or the
  param is centred on zero — a hand's at `hands.learn_depth`, any other
  at `PUSH_DEPTH` — otherwise the **position** fader at depth 1. A taken
  param is `Ask`: ROUTING's Replace / Keep (`ui_routing.ask`), Replace
  calling `replace_owner`. A desk knob, a pad button or a key on `mod` is
  refused: "a desk knob sets a base, not a performer; aim at base".
- **Other options.** The prompt's rule: push only for a hand axis, else
  position at 1 (a band would land on a centred `rot.rate.*` as a fader
  pinned at one end).
- **To reverse.** `Edit.route_for` builds its own row.
- **Rough edge.** A source the device registry does not list (no tracker
  connected) is never read as centred: its cable lands as position
  unless the param is centred.
- **Judge it.** Checks 247, 248.

### 256. A cable into `base` is a desk or pad setter through the learns' own roads; the rest refused in words

- **Built.** A desk control (`cc` / `note` / `pitch`, any qualifier) on a
  `base` stub goes through a private `Learn(...).learn_control`: a
  preset-layer `abs` row (a `toggle` for a note or a trigger param),
  `bind(write=False)`, the same refusals (an invariant control, the
  global layer, SAVE). A pad button or the D-pad goes through
  `Learn.learn_pad_button`: the session's row, `bindings.json` written,
  no undo step — as the pad learn. A hand: "a hand sets no base; aim at
  mod" (and "a band", "an LFO", "a modifier", "a stick" with their own
  noun). A key: "keys are the session's rows: map them on ROUTING".
- **Other options.** The prompt's row for a pad, `Binding(src, pid,
  "abs", layer="preset")`: an `abs` on a button does nothing useful, and
  `is_session_row` would class it as the session's anyway.
- **To reverse.** `Edit._setter`.
- **Rough edge.** A pad setter is written at once and not undoable. The
  private Learn's "learned …" words are not shown; only refusals reach
  the head.
- **Judge it.** Check 248.

### 257. A cable's end is moved by a drag from where it lands, input pin to input pin

- **Built.** The widget cannot pick up a link, so a drag that starts on a
  **patched input pin** (a route's `mod` stub, a modifier's `in`) and
  ends on another input pin moves that cable: a route by
  `move_route(target=…)` (same op and depth, its macro depth
  subscribers follow; a taken param asks, Replace being
  `replace_owner(row, target=…)`), a modifier input to the other
  modifier's input. Between two input pins with no cable: "join an output
  to an input". The move picks up the performer, never a sleeping row.
- **Other options.** Ctrl-drag; a "move to…" item on the cable's menu.
- **To reverse.** `Edit.move`.
- **Rough edge.** The source end cannot be moved by a drag: delete and
  draw again, or insert a modifier.
- **Judge it.** Check 247.

### 258. A free modifier let go over a cable is inserted into it

- **Built.** When a **modifier node with no cables** is dropped, its
  centre is tested against every route and modifier-input cable on the
  cubic the widget draws (handles at `link_strength` 100 canvas units,
  sampled 16 times: `graphview.bezier`, `cable_near`). Within 14 canvas
  units it is inserted (`Edit.insert_modifier`): the cable's source
  becomes its first input, its lane the cable's new source
  (`move_route`, op and depth kept), and a push keeps its old source's
  rest (`Router.rest_of`), so a centred hand stays centred through a
  smooth. A cable's right-click **insert ▸ <kind>** does the same with a
  new modifier; either is one undo step.
- **Other options.** The mouse position rather than the node's centre;
  the widget's own hovered link (the dragged node covers the cable).
- **To reverse.** `ui_graph.dropped` and `_moved`'s two lines.
- **Rough edge.** Pin positions are last frame's pin centres. A modifier
  already patched is never inserted by a drop: unpatch it, or use
  **insert**.
- **Judge it.** Checks 247, 249.

### 259. The node picker: modifiers by kind, idle macros; delete for a modifier or macro node

- **Built.** Right-click the empty canvas: **modifier ▸ curve · scale ·
  smooth · combine · threshold · delay** (`Bindings.add_modifier`) and
  **macro ▸** the idle macros (every macro is already a node — its knob
  is modulatable — so picking one labels it "macro N", and ROUTING's
  strip names it too). The node lands where the menu opened, saved in
  the preset's layout. A modifier or macro node goes by its right-click
  **delete** or the Delete key; the rig's nodes are refused ("<label>:
  the rig's, not the preset's").
- **Other options.** Hide idle macros; the picker on a drag into empty
  space (`query_new_node`).
- **To reverse.** `ui_graph.picker` / `macros_free`, `Edit.show_macro`.
- **Rough edge.** The "macro N" label dirties the preset.
- **Judge it.** Checks 249, 250.

### 260. A macro dragged onto `mod` is refused in words

- **Built.** A cable from a macro's `bus` onto a param's `mod` stub is
  refused: "a macro sets a base or scales a depth; aim at base or a
  depth stub". A macro lands only on a `base` stub (a base subscriber)
  or a route's `depth` stub (a depth subscriber).
- **Why.** No Router scheme publishes a macro's knob, so a route sourced
  from a macro would sit dormant for ever; the design's own "drag from a
  macro → a `Sub`" is what is built.
- **Other options.** A route sourced from a macro, through a new `macro`
  lane fed by `follow_macros`.
- **To reverse.** Moderate: publish the macros as a lane, then drop the
  `MACRO_NO_MOD` branch in `Edit._macro_refusal`.
- **Rough edge.** One knob that both sets a base and drives a
  modulation needs two subscribers, or the desk knob routed itself.
- **Judge it.** Check 248.

### 261. Deleting a macro node clears its label and every subscriber; the knob stays

- **Built.** A macro node's delete (the key, or its right-click
  **delete**) rewrites the table's macros without it
  (`set_macros(macros_doc() minus it)`): its label and every subscriber
  go; the knob, one of the rig's eight `macro.*` params, stays. One undo
  step ("delete node macro.N"). ROUTING's macro strip then shows the
  knob with no label and no subscribers.
- **Other options.** Refuse it, as for the rig's other nodes; remove only
  the subscribers and keep the label.
- **To reverse.** One branch in `Edit.remove_value_node`.
- **Rough edge.** A label the owner typed is lost with it (⌘Z brings it
  back).
- **Judge it.** Check 250 (its third step: the node delete).

### 262. Deleting a cable: the preset's go, the session's are refused

- **Built.** The Delete key on a selected cable, or the cable's
  **delete**: a route is `remove`d (its depth subscribers with it); a
  preset-layer desk row is removed and the desk redrawn; a macro
  subscriber leaves its macro; a modifier input is unset. A session
  row's cable (keys, the pad, an invariant or global-layer desk row:
  `is_session_row`) is refused: "<source> is the session's
  (bindings.json): edit it on ROUTING". Each edit is one named undo step
  ("delete cable …", "connect … → …", "insert smooth into …"). In a
  delete of several things at once, the first refusal's words stay on the
  head.
- **Other options.** Let the canvas edit `bindings.json` too.
- **To reverse.** `Edit.disconnect_value`, `ui_graph._value_cut`.
- **Rough edge.** None known.
- **Judge it.** Checks 250, 258.

### 263. The wire list: `{"from": "<node>", "to": "<node>.<port>"}` in a `wires` list beside `nodes`

- **Built.** The preset's `graph` section takes `wires` beside `nodes`.
  `from` is a node's name, meaning its one output (`scene`, `hands`,
  `hands.2`, `history`, an effect instance `palette` / `acid.2`, a
  composite); `to` is `<node>.<port>` (`output.2.hands`, `acid.2.image`,
  `history.image`, `composite.over`). Kept in the file's order and
  written back so, one wire a line (`preset.dumps`); a section with no
  wires writes no key. `GraphSpec.wires` holds the list as read.
- **Other options.** Wires nested on each node (`"inputs": {"image":
  "history"}`: shorter for effects, but outputs are not in `nodes`);
  `to` as two keys.
- **To reverse.** `Wire`, `_read_wires`, `GraphSpec.to_json`,
  `preset.dumps`, the two fixtures.
- **Rough edge.** A list's order has no meaning, but two specs differing
  only in order compare unequal (a rebuild, nothing more). An older
  build refuses the key (row 277).
- **Judge it.** Checks 251, 252.

### 264. A preset may wire image ports only; a hands node's place stays its `into`

- **Built.** Wireable: `output.<n>.image`, `.hands` and `.readout`;
  `history.image`; an effect's `image`; a composite's `under` and `over`.
  Geometry and mask ports are typed, so a wrong drag can say why, but
  are not wireable: `ghost → scene.geometry` gives "a hands node's place
  is its into (ghost into scene or layer), not a wire"; `cover → …`
  "the cover is the history's own". On the canvas a geometry cable from a
  hands node into the scene or the layer **does** land: it sets that
  node's `into` (A4's JSON). `output.<n>.readout` takes only a hands
  layer; a composite cannot take the history `over` (it paints into what
  reads it); an output's `depth` follows the blend.
- **Other options.** Geometry wires in the JSON (two spellings of A4's
  `into`); a wireable depth port.
- **To reverse.** `WIRE_TAKES` / `WIRE_MAKES` in `graph.py`.
- **Rough edge.** Two spellings of "hands in the scene": a geometry drag
  on the canvas and `into` in the JSON (the canvas writes the JSON's).
- **Judge it.** Check 253.

### 265. D1's `after` / `into` are wires written short; a D1-only section stays short

- **Built.** `after X` is the wire `X → E.image`, `into Y` is `E →
  Y.image` (`GraphSpec.all_wires`, `d1_wires`). Back the other way
  (`split_wires`): an effect fed by one wire and wired into nothing is
  `after` its source; fed by none and wired into one output's or the
  history's `image`, `into` it; anything else is an explicit edge (it
  reads exactly its source, only the named ports read it). A D1-only
  section is written short, byte for byte; a section read as wires is
  written as wires; an edit on the canvas writes wires, dropping a D1
  placement it replaces (an extra instance stays in the chain).
- **Other options.** Normalise every section to one form on save (a
  hand-written file re-spelled; D1's three fixtures would change).
- **To reverse.** `split_wires`, `d1_wires`, `graphview._unplace`.
- **Rough edge.** D1's `into: <effect>` has no wire spelling (`palette →
  warp.image` reads as "warp after palette") and stays short. A wire into
  an effect's image and D1's `after` on that effect are two wires into
  one port, refused.
- **Judge it.** Check 251.

### 266. Outputs as nodes: a wire overrides that port alone; the guide goes with the hands shown

Folds N4's "a hands wire on a through output".

- **Built.** `output.<n>.image` ← S: the output shows S through an end of
  its own (`graph.Wired`, `wire(output.<n>)`, painted straight into the
  output when it can), ignoring its scene and through switches; if its
  `hands` port was empty, its readout goes too unless the readout is
  wired. `.hands` ← S: S laid over, depth-aware when the blend is depth,
  the layer's guide with it if the output had none; on a **through**
  output the output's picture moves to the end the hands were laid onto
  (the scene's end, or the ground) and only the wired node is laid
  over, so the hands are never drawn twice; a non-layer on `.hands` (the
  scene, a composite, an effect) is laid as its own picture, never
  through hands 1's ghost; `history → *.hands` is refused.
  `.readout` ← layer: that layer's guide. An output no wire names is
  node for node the default graph's, following the session's switches; a
  load never writes a switch. The wires ride in `Wiring`, so
  `Renderer._graph_for` rebuilds when they change.
- **Other options.** Keep an image-wired output's switch-derived hands
  and readout (a guide on a picture with no hands); let the image wire
  take `hands` too; lay a wired layer through the chain (a pipeline per
  wired layer); refuse a hands wire on a through output.
- **To reverse.** `_Wiring._put`, `Wired`, `Output.run`'s `laid_node`.
- **Rough edge.** On a through output the effects no longer bend the
  hands while a hands wire is on it (the wire wins). A wired output's
  golden route reads `none` (with a `"wired"` key naming its source);
  `stats["routes"]` keys it `"wire(output.2)"`.
- **Judge it.** Checks 252, 254.

### 267. A refused wire is a note and that port's default; a malformed one the default graph

- **Built.** `graph: wire <from> → <to> — <why>; the default wiring`,
  that wire left out, its port at its default (or D1's placement), the
  rest standing, the section kept as written. The reasons: no such node
  ("a wire leaves scene, hands …, history, an effect or a composite"),
  no such effect in this build, an output as a source ("it makes nothing
  to wire on"), no such port ("it takes image, hands, readout"), a type
  mismatch ("ghost makes geometry, output.1.image takes a picture"), no
  such layer, a readout from a non-layer, a D1 placement already there
  ("one place"), two wires into one port ("it keeps its default"), an
  effect with no wire in and several out, a loop ("that makes a loop
  (palette → acid.2 → palette)"). A malformed wire (not two strings, or
  the same twice) is a `GraphError`: the default graph, as A4 does. A
  wire on a node this frame lacks is dormant
  (`Graph.dormant`: "wire hands → output.3.hands — no output 3 this
  frame"), on OUTPUT's dormant lines and in the graph words.
- **Other options.** Drop the whole graph on any refused wire.
- **To reverse.** `wire_error`, `_read_wires`, `GraphSection.read`'s
  suffix.
- **Rough edge.** Every wire into a doubly wired port is refused, not
  only the later one; every wire on a loop.
- **Judge it.** Check 253.

### 268. The render picker; every render edit read back through `read_graph` before it lands

Folds N3's "the seam with N4".

- **Built.** Right-click the canvas: **effect ▸** one item per effect
  file (`EffectAt(file, n + 1)`, its `fx.<file>.<n+1>.*` at their
  defaults, the instance in the chain at its order), **hands**
  (`HandsAt(n + 1)`), **composite** (`CompositeAt(n + 1)`, blend over,
  built once a wire feeds it). A render node's menu: delete; `draw
  solid` / `draw lines`; `laid over` / `add` / `depth`. Delete on a wire
  unwires it; on a default cable: "… is the default graph's: no wire
  says it (wire something else into … to replace it)". A node delete
  removes an extra effect instance, hands node or composite with every
  wire on it; instance 1 of an effect, hands 1, the scene, the history
  and the outputs stay, each with words. Every edit is a new section
  read back through `read_graph` with the build's files: a note is the
  refusal and nothing changes; else one undo step (`undo.push(label,
  load=True)`), then `GraphSection.land` (the preset dirty, the renderer
  handed the wiring); an edit that empties the section lands none. The
  page dispatches a drag by its pins' type (`ui_graph.CREATE`) and a
  delete by the cable's or node's kind (`DELETE`, `DELETE_NODE`); value
  and trigger edits go through `_act`, render edits through
  `render_edit`, whose step is pushed only once an edit is accepted. The
  head says the last edit's words until the next edit or refusal.
- **Other options.** A picker of instances already declared; edits that
  write the spec directly (two paths for refusals).
- **To reverse.** `graphview`'s render edits and `ui_graph`'s.
- **Rough edge.** A loaded section that carried a refused wire or
  placement is kept, but the first canvas edit writes the accepted spec
  and drops the refused part. A drag's red words are a tooltip, not a
  note.
- **Judge it.** Checks 251, 255.

### 269. The two wire fixtures' look

- **Built.** `hands-glass-only.json`: hands-lines' values, `ghost` drawn
  in the scene **as lines** so the solid `ghost.2` layer reads apart;
  `ghost.2` is the layer, wired to `output.2.hands`. `wired-outputs.json`:
  palette-glass's values (party-acid, the palette at centre 200, width
  60 — hue 170 → 230 since N8, row 295) plus `fx.acid.2.*` (on, mix 1, bend 0.06, twist 1.6, reach 6,
  breathe 0.5); the palette wired into `output.1.image`, acid 2 after the
  history into `output.2.image`. `tools/golden_frames.py` switches on any
  `ghost.<n>.on` a fixture's graph declares (session state no preset
  carries).
- **Other options.** Ghost 1 solid in the scene (the two hands alike in
  the golden).
- **To reverse.** Re-record the two fixtures (`--only`).
- **Rough edge.** At the machine `ghost.2.on` starts off: switch it on on
  HANDS. Hands 2 is also on any output whose switches lay a layer with
  the scene off (A4's one-layer rule). The name assumes the glass is
  output 2; on the hand checks' two-screen rig (101) the glass is output
  1.
- **Judge it.** Check 252.

### 270. The APC40 is two nodes: `device:apc40` with every control, `device:apc40/global` without the invariant ones

- **Built.** A device whose `layers` has two or more entries (today the
  first MIDI role's APC40: `("preset", "global")`) is one node per layer
  (`graphview.device_nodes`). *apc40* keeps N2's id and name, carries
  every control of the layout, the invariant ones included, and draws the
  preset layer's rows and the invariant rows; *apc40 (SHIFT)*
  (`device:apc40/global`) carries every control but the invariant ones
  and draws the global layer's (`bindings.json`). "Invariant" is the
  table's own `Bindings.is_invariant(Binding(control, ""))`: SHIFT plus
  the control of any enabled layer-None row; nothing is listed by hand.
  The first node's pins stay `out:<address>`, the SHIFT node's
  `out:<address>|global`. Both ids are the show's layout keys. A drag
  from a SHIFT-node port into `base` is refused whatever the latch
  ("<addr> on the SHIFT node is the session's (bindings.json): map it on
  ROUTING"): the global layer is never a Learn target (D5).
- **Other options.** One node with a layer toggle (decision 12 rejects a
  layer view); ids `device:apc40.shift`.
- **To reverse.** `device_nodes` returns one node; the SHIFT node's
  saved position is dropped as an unknown id.
- **Rough edge.** The global layer's rows are edited on ROUTING only.
- **Judge it.** Check 256.

### 271. The desk's port groups

- **Built.** On each desk node, in this order: `invariant` (first node
  only), `track knobs`, `device knobs`, `knobs` (the cue level),
  `faders` (track faders, MASTER, the crossfader when not invariant),
  `clip grid` (the field and the scene column), `buttons`, from the
  profile's control kind (`Port.group`) with knobs split by Akai's name;
  inside a group, the layout's order. A generic desk (one layer, no
  layout) has no ports, as before.
- **Other options.** The raw kinds (N2's `knob`, `fader`, `grid`,
  `button`); the glyph rows.
- **To reverse.** `graphview.desk_group` / `DESK_GROUPS`.
- **Rough edge.** An invariant fader (the crossfader) sits in
  `invariant`, not `faders`.
- **Judge it.** Check 256.

### 272. The SHIFT latch is read from the table (`Bindings.layer_of`) each frame

- **Built.** `MidiIO` reads `Bindings.layer_of(role)`, which `desk.shift`
  sets, and the page reads the same value: each frame `graphview.refresh`
  sets each layered node's `up` and each port's (an invariant port is
  always up). A cable from a port whose layer is down is dormant
  (faint); the down node's title and ports are faint, an up layer's
  ports bright, invariant ports dim as ever. A flip rebuilds nothing.
- **Other options.** `desk.shift` from the registry (the first role
  only); an `up_layer` on `MidiDevice` (`devices.py` was not needed).
- **To reverse.** The block at the top of `refresh`.
- **Rough edge.** A second MIDI desk with no latch is one node and never
  faint.
- **Judge it.** Check 256.

### 273. A layered row on an invariant control is drawn off, on *apc40*'s invariant port

- **Built.** A preset- or global-layer row whose control is invariant
  never acts and never lights (D6). Its cable is `off` (dormant), its
  hover says "(under an invariant control)", and it leaves that
  control's port on *apc40*, in `invariant` — never a port on the SHIFT
  node — so "invariant controls on *APC40* only" holds even for it.
- **Other options.** Hide it.
- **To reverse.** The `shadowed` line in `build`.
- **Rough edge.** None known (no factory row is shadowed today).
- **Judge it.** Tests only
  (`tests/test_graphview_devices.py::test_a_shadowed_layered_row_leaves_the_invariant_port_on_the_first_node`).

### 274. A desk template is a subgraph node; an edit inside is an override

Folds N5's "an edit inside a template is an override".

- **Built.** When the loaded preset names a `desk_template`, the page
  passes the template's rows as the load expanded them
  (`Presets.template_at_load()`, what a save compacts against). `build`
  draws one node, `template:<name>` (column 0, saved in the **preset's**
  layout), a port per template row ("<control> → <target>"). A live
  preset-layer row still the template's (same control, target, op and
  value) is a cable from it (`VCable.inside`); an override, or a row on a
  control the template does not map, hangs off *apc40*; an overridden or
  darkened template control is a port with no cable. Every template
  node starts collapsed (its ports listed, none of its cables drawn); its
  **+** opens it, **−** closes it. **Superseded in part by row 278**
  (plan 28 N7, 2026-10-20): collapsed, it lists no port either — "<n>
  mapped controls" — like every node; its open state is every node's
  expanded set (row 282). Deleting a template row's cable is
  `table.remove` (the save writes a dark row); dragging a template port
  onto a `base` stub is the desk learn (the save writes an override).
  The template file is never written.
- **Other options.** Collapsed, one bundled cable per target node; the
  overrides inside the subgraph too; template-level edits rewriting the
  file (shared by every preset that names it).
- **To reverse.** The template block in `build`, `template_of`,
  `drawn_cable`.
- **Rough edge.** While collapsed, the params its rows set show a
  patched `base` stub with no visible cable (the stub's hover: "set by
  desk template <name> (collapsed: + shows it)"). After an edit the cable
  jumps from the template node to *apc40* — honest (it is an override
  now), but it can surprise.
- **Judge it.** Check 257.

### 275. A role this rig lists no device for is a grey placeholder `device:<role>`

- **Built.** A row from a role with no listed device draws from a grey
  node `device:<role>` (`placeholder`, status "not in this rig: its
  cables wait for it"), its cables dormant. The role: the row's
  qualifier (`axis@p2` → `p2`); for an unqualified MIDI row the desk's
  first role; else the kind's usual role from `config.py`'s example list
  (`hand` / `hands` → `leap`, `axis` / `pad` / `hat` → `pad`, `cc` /
  `note` / `pitch` → `apc40`); else the scheme. The id is the real
  device's, so a device of that role arriving takes the placeholder's
  saved position. Keys stay their own `source:key` node. Fixed on the
  way: N2 drew a qualified MIDI row with no such device from the first
  desk's node.
- **Other options.** N2's `source:<scheme>` nodes.
- **To reverse.** The placeholder branch in `source_pin`, `SCHEME_ROLE`
  / `NO_DEVICE`.
- **Rough edge.** With no desk listed there is one placeholder, not two:
  its preset- and global-layer rows on one control share one pin.
  `SCHEME_ROLE` guesses from `config.py`'s example names: a rig that
  names its hands role otherwise gets a placeholder `leap`, and the real
  device takes its own id.
- **Judge it.** Check 258.

### 276. The hands node's groups: axes, pinches, grab, presence, dance

- **Built.** `hands/device.py`'s own groups, except that its `switches`
  are told apart by address: a `.grab` port in `grab`, every other
  switch in `pinches`; the device's order. Nothing in the hands package
  changed (`tests/test_hands_boundary.py` untouched).
- **Other options.** The two groups added in `hands/device.py` itself.
- **To reverse.** `graphview.hand_group`.
- **Rough edge.** `presence` is a fifth group the design did not name.
- **Judge it.** Check 256.

### 277. A build from before this run reads this run's presets only in part: placements and wires are a note, modifiers and positions are lost on its save

- **Found by the review pass**, not chosen: no code can fix it, because
  the old build is what reads the file.
- **Built.** Nothing in this build: the keys are additive and no schema
  was bumped (`hyperspace.preset/2`). What an older build (the base,
  5d18192, or the other Mac if it is behind) does with a preset saved
  here: a `graph` section with a placement (`after` / `into`, plan 30)
  or a `wires` list is refused whole by its strict reader — the preset
  opens as the default graph with one note (`graph: effect node: no key
  'after' (it takes instance, file); the default graph`, `graph: no key
  'wires' (it takes nodes); the default graph`), plus an unknown-id note
  for each extra instance's params; the section survives a save there.
  `modifiers` and `layout` are ignored **with no note**, and a save on
  that build **drops** both; a route on `mod:<n>` is a dormant row
  there. Everything else (values, routes, desk, macros) lands as before.
- **Other options.** A schema bump to `hyperspace.preset/3` (an older
  build would then refuse the whole file); writing the old short form
  where it can (it cannot for wires or modifiers).
- **To reverse.** n/a: it is how the base build reads.
- **Rough edge.** The shared library (plan 25) syncs presets between two
  Macs: **update both Macs to this build before sharing patches**, and
  never save a preset with modifiers or positions on an older one. Rows
  219 and 222 (the placement keys) carry the same caveat.
- **Judge it.** Check 259.

## A legible graph (plan 28, N7)

Built on 2026-10-20 after the owner's first look at the GRAPH page
("very messy … borderline illegible with the APC40 alone … I clicked
the tidy button, and nothing happened … I clicked the beside toggle,
and I don't know if it did anything"). The owner's three decisions —
every node collapsed by default, one wire between two nodes while either
end is collapsed, GRAPH takes the routes and the modifiers from ROUTING
now (ROUTING keeps its desk, macros, session and sinks until it is
retired) — are in [`DECISIONS.md`](DECISIONS.md) "UI" with Who "owner
(2026-10-20)"; these rows are what the build chose where those left a
choice open. It supersedes parts of rows 250, 251, 252, 254 and 274
(marked there). Measured on party-trip at the control window's
960 × 900 (55 nodes, 238 cables): the page draws in **1.27 ms** median
collapsed (64 wires), 2.66 ms with every node expanded, against N2's
2.32–2.78 ms. No preset was edited or added; `apc40.py`, `midi.py` and
ROUTING's desk, macros, session and sinks sections are untouched.

### 278. A collapsed node's lines: what it holds, how much is patched, its live reading

- **Built.** Under the title, at most five lines (`graphview.summary`),
  the same count every frame: a device "137 ports · 97 patched", its
  loudest patched port ("> right y 0.83", else "nothing live"), its
  layer and whether it is up (*apc40*: "preset layer · up"), "not in this
  rig" for a placeholder or the device's status while it is grey; the
  analyzer "6 bands · 6 patched" and its loudest; an LFO "out 0.42" and
  its knobs; a modifier its kind and output ("smooth · out 0.42"), its
  inputs, its params; a macro its knob and its subscribers; a render,
  output or group node "51 params · 32 patched", its picture ports, its
  loudest patched param; a desk template its mapped controls. No row
  per port.
- **Other options.** Only the title (nothing to read at a glance); the
  first five patched ports (as long as the APC40's list, cut).
- **To reverse.** `graphview.summary`.
- **Rough edge.** "Loudest" is by |reading| of a patched port, so a knob
  parked at 1.0 wins over a moving one. A line longer than the node is
  cut with "…".
- **Judge it.** Check 261.

### 279. One in and one out stub a node; a render cable to a collapsed node's stub

- **Built.** Every node with an input port has an ``in`` stub
  (`nin:<node>`) at the left of its title line, every node with an output
  port an ``out`` stub (`nout:<node>`) at the right, expanded or not; a
  stub is lit while any cable touches the node. Bundles end on stubs.
  A render cable (image / geometry / mask) stays one wire each, its end
  on a collapsed node moved to that node's stub.
- **Other options.** Stubs only while collapsed (a bundle from a
  collapsed node into an expanded one would then have no end on the
  expanded side).
- **To reverse.** `ui_graph._node`, `graphview.wiring`.
- **Rough edge.** Two render cables between the same two collapsed nodes
  draw on top of each other.
- **Judge it.** Check 261.

### 280. A bundle: one per (source node, target node), as thick as it is many, its hover the first ten

- **Built.** `graphview.wiring` folds every value and trigger cable with
  a collapsed end into one `VBundle` per (source node, target node):
  trigger-coloured when every cable is a trigger, else value-coloured;
  its reading the largest live |reading|; faint while every cable is
  dormant. Its line is 2.5 px for one cable plus 0.5 px a cable, capped
  at 7 px (ten cables or more). Hover: "<source> → <target>", "<n>
  cables: <source port> → <param>, …" — the first ten, then "+ k more" —
  and the reading.
- **Other options.** One bundle per pair and type (two wires where a
  desk sets triggers and values on one node); thickness by the reading
  (a bundle's many readings in one number).
- **To reverse.** `graphview.wiring`, `ui_graph.bundle_thickness`.
- **Rough edge.** The APC40 is still two nodes (owner decision 12), so
  the desk reaches a node over two wires when both layers map into it,
  and the two fan out one wire per node they map into: 19 bundles on
  party-trip (*apc40* 14, *apc40 (SHIFT)* 5), most into group nodes
  (`band`, `preset`, `master`, `tempo` …), three into render nodes
  (`shape`, `fx`, `eye`). The key node fans out to about ten group
  nodes. A bundle at the cap does not thicken with one more cable: its
  hover's count does.
- **Judge it.** Checks 261, 262.

### 281. A bundle selected lists its rows; its Delete is refused in words

- **Built.** A selected bundle's side pane lists every route in it as
  ROUTING's own row (`ui_routing._row`, the one table: its widgets, its
  ×), and the other cables (desk rows, subscribers) as a line each.
  Delete on a bundle keeps it and says "expand a node to edit its
  cables"; its right-click offers "expand both ends".
- **Other options.** Delete removes every cable in it (one keystroke for
  two dozen rows).
- **To reverse.** `ui_graph._side`, `ui_graph.delete_bundle`.
- **Rough edge.** A desk row in a bundle has no editor in the pane
  (ROUTING's desk section edits it): a bundle of setters (the APC40's,
  the keys') lists its cables as text lines ("<control> → <param>
  <op>"), only its routes as rows.
- **Judge it.** Check 262.

### 282. The collapse state is the page's, saved nowhere

- **Built.** Which nodes are expanded is UI state on the panel
  (`ui_graph._state(panel)["open"]`): not in the preset, not in the
  show's `layout`, not an undo step; every node is collapsed at launch,
  a hot reload keeps the set, and so does a preset load (a node of the
  same id stays expanded); a tidy clears it. A desk template's "open" is
  the same set.
- **Other options.** In the show's `layout` beside the rig's positions
  (a show that opens half-expanded is the mess the owner described).
- **To reverse.** Carry the set in the show's map (`Project.layout`,
  `graphview.split`).
- **Rough edge.** Expanding a node pushes the unplaced nodes under it
  down; a node the owner placed stays and may be overlapped.
- **Judge it.** Check 261.

### 283. A drag onto a collapsed node's stub opens a picker of its ports

- **Built.** A cable dragged from a port onto a collapsed node's ``in``
  stub (or from an input onto an ``out`` stub) says "let go: pick one of
  <node>'s ports" while held; let go, a menu lists that node's pins it
  can land on — each param's `mod` / `base` / `depth` stub, a modifier's
  inputs, a render port — by port group when there are more than twelve,
  only the ones `Edit.refusal` lets through ("nothing on <node> takes it:
  <first refusal>" when none), each "<port> · <stub>" ("Brightness ·
  mod"). A collapsed node with exactly one output pin (a modifier, an
  LFO, a macro) has an ``out`` stub that stands for that pin
  (`graphview.stub_pin`), so a collapsed modifier's out dropped on
  another collapsed node's in opens that node's picker. The pin picked goes through
  `Edit.connect` unchanged (one undo step; Replace / Keep when taken), a
  render one through `Edit.wire`. A drag between two stubs neither of
  which stands for one output (a device's out onto a render node's in),
  or onto the wrong side, is refused red in words.
- **Other options.** A two-level menu for stub to stub (every source
  port × every target pin: hundreds of refusal checks); expand on drop.
- **To reverse.** `ui_graph._stub_drag`, `open_land`, `land`,
  `graphview.land_choices`.
- **Rough edge.** A render node lists its picture ports among its params'
  stubs; the menu is long on the shape (about fifty params).
- **Judge it.** Check 263.

### 284. Learn from a node's right-click, per param

- **Built.** Right-click any node: expand / collapse, then **learn ▸**
  its params by port group, each opening N3's pin menu (the param menu's
  own Learn items, `Panel._ctx_learn_block`), so a collapsed render node
  is learned without expanding.
- **Other options.** Only on an expanded node's `mod` pin (N3's).
- **To reverse.** `ui_graph._node_menu`, `learn_params`.
- **Rough edge.** Three menu levels on the shape.
- **Judge it.** Check 263.

### 285. Tidy collapses everything, lays it out again and says what it did

- **Built.** **tidy** collapses every node, forgets every position in
  both maps (one undo step, as before), lays every node out again by
  column, frames the canvas on them, and the head says "laid out 55
  nodes, every one collapsed" — or "already tidy" when no node moved
  and none was expanded.
- **Other options.** Keep the expanded nodes expanded (the owner's
  "nothing happened" came from a tidy that changed nothing visible).
- **To reverse.** `ui_graph.tidy`.
- **Rough edge.** The undo puts the positions back, not the expanded
  nodes.
- **Superseded in part by row 304** (plan 28 N9): tidy lays every node
  out in its area, closes the idle lines, and says "laid out 31 nodes in
  6 areas, every one collapsed · 22 idle off the canvas".
- **Judge it.** Checks 264, 274.

### 286. The details chip: only with a selection on a narrow page, named by what it does

- **Built.** The **beside** chip is gone. While something is selected
  and the page is narrower than 720 px, the head has **details beside**
  (the details are under the canvas) or **details below** (they are
  beside); with nothing selected there is no chip; at 720 px or more the
  details sit beside with no chip.
- **Other options.** Always beside (a canvas about 100 px wide at the
  panel's size).
- **To reverse.** `ui_graph.beside_chip`.
- **Rough edge.** The choice is kept while nothing is selected.
- **Judge it.** Check 264.

### 287. Expand all / collapse all; "patched only" within an expanded node

- **Built.** The head's first chip is **expand all** (every node
  collapsed or some) or **collapse all** (any expanded). Inside an
  expanded node N2's view holds: the page's **patched only** chip
  (default on) and the node's own **all ports / patched only** chip,
  and its port groups fold.
- **Other options.** "patched only" as the collapsed view (N2's).
- **To reverse.** `ui_graph._head`, `_node`.
- **Rough edge.** Expand all draws every patched port of every node
  (2.66 ms on party-trip).
- **Judge it.** Check 262.

### 288. ROUTING's pointer line; "Route a lane here…" opens GRAPH

- **Built.** Where ROUTING's counts line, its route rows, its "+ route"
  and its MODIFIERS strip were, one dim line: "routes and modifiers: the
  GRAPH page" (a click opens GRAPH), with the filter field beside it; the
  filter now counts and filters the desk, the macros, the session and
  the sinks only. The routes' and the modifiers' functions stay in
  `ui_routing` (`add_route`, `_row`, `_sources`, `_targets`,
  `add_modifier`, `set_modifier_input`, `remove_modifier`,
  `modifiers`). The param menu's "Route a lane here…" adds the route as
  before and opens GRAPH instead of ROUTING.
- **Other options.** A route list on GRAPH's side pane while nothing is
  selected (a second route page); leave ROUTING's rows until it is
  retired (two pages editing the routes).
- **To reverse.** The pointer block in `ui_routing.page` (the two
  sections were a few lines there).
- **Rough edge.** "+ route" is gone: a new route is a drag on the
  canvas, a Learn, or "Route a lane here…" (which selects the new route
  on GRAPH, its row first in the pane). While the filter holds text its
  red "n of m rows" takes the pointer's place.
- **Judge it.** Check 266.

### 289. A modifier node's side pane is the MODIFIERS strip's block, stacked

- **Built.** Selecting a modifier node shows its editor in the side
  pane: `ui_routing.modifier_block` (the strip's own per-modifier block,
  factored out of `modifiers` unchanged for the strip) drawn stacked for
  the 320 px column: its output bar, each input's source combo on a line,
  each param under it, "× remove".
- **Other options.** The strip's one-line layout (cut at 320 px).
- **To reverse.** `modifier_block(stacked=…)`.
- **Rough edge.** None known.
- **Judge it.** Check 265.

### 290. A collapsed node reads only what its lines show; the wiring and the columns are kept

- **Built.** `graphview.refresh` skips the unpatched input ports of a
  collapsed node (its lines never show them); the page keeps
  `graphview.wiring`'s answer while the view and the expanded set hold
  (only the bundles' readings move a frame) and the column layout while
  the view, the expanded set, the folds and the stored positions hold;
  `View.node` is a dict lookup.
- **Other options.** Recompute every frame (2.2 ms collapsed).
- **To reverse.** `ui_graph._wiring`, `_place`'s cache, `refresh`'s
  `collapsed`.
- **Rough edge.** A port's hover on a collapsed node is not reachable,
  so its stale reading is never seen.
- **Since N9** the cached layout is the areas' (`ui_graph.areas_of`),
  its key the open idle lines too (row 299).
- **Judge it.** Check 261.

## The palette as compression (plan 30, N8)

Built on 2026-10-20 after the owner's second look at the palette: "What I
want this to be is a color compression transform. It is definitionally
mapping the space of the HSV cylinder onto a bounded subspace of that
cylinder" — a start and a stop angle, a start and a stop saturation, a
start and a stop value — and "one of the mode controls is like a slider,
but it's really a discrete picker". The owner's decision is in
[`DECISIONS.md`](DECISIONS.md) "Effects and the look-back" with Who
"owner (2026-10-20)"; these rows are what the build chose where it left
a choice open. They supersede rows 138 and parts of 135, 136 and 139
(marked there). No factory preset turns the palette on, so no factory
golden moved; the three fixtures that do (`palette-hands`,
`palette-glass`, `wired-outputs`) were converted to the slice's keys and
their frames match as recorded.

### 291. The slice: `hue_from` → `hue_to` up the wheel; from = to is one hue, 0 → 360 the whole wheel

- **Built.** Seven params name the slice: `hue_from`, `hue_to` (degrees,
  0–360), `hue_turn` (degrees, wraps), `sat_from`, `sat_to`, `val_from`,
  `val_to` (0–1). The arc runs from `hue_from` *up* the wheel to
  `hue_to`, through 360 when `to` is below `from` (350 → 10 is the 20° of
  reds either side of 0); `from = to` is one hue; 0 → 360 is the whole
  wheel. `hue_turn` is added to both ends: it turns the whole slice round
  the wheel and keeps its width, wrapping as the old `centre` did, so a
  hand or a lane sweeping the hue rides it (a converted centre route
  lands there). The defaults are the whole cylinder (0 → 360, turn 0,
  0 → 1, 0 → 1), so switched on at mix 1 the picture is as it was on an
  opaque ground (a test; on a see-through ground — the overlay, the
  faces — the colour is premultiplied and the pass scales it by alpha
  once more, so a part-clear pixel darkens). The ends do not wrap: 360
  must stay 360, or the whole wheel would read as one hue.
- **Other options.** The short way round (350 → 10 and 10 → 350 the same
  arc; no arc over 180° could be set); wrapping hue params with `from = to`
  as the whole wheel (a single hue then needs two different numbers).
- **To reverse.** The arc line in `palette.glsl`, the params' header.
- **Rough edge.** A route on one end alone clamps at 0 / 360 (the ends do
  not wrap): to move the slice round, route the turn, not an end.
- **Judge it.** Checks 267, 269.

### 292. The hue map: the old fold up to 180°, sliding to the identity at 360°

- **Built.** A seamless map from the whole wheel onto an arc must fold
  (a map that went once round the wheel onto a partial arc would tear at
  red), and a map that is the identity at 360° cannot fold — so the
  palette keeps the triangle fold for arcs up to 180° (red lands on
  `from`, cyan on `to`, every hue between; "derivations on yellow"), and
  above 180° the fold's peak slides from cyan towards the far side of red
  (`smoothstep(180, 360, arc)`) until at 360° the climb is the whole
  wheel and the map the identity. Up to 180° the expression is the old
  one to the bit: the palette fixtures' frames did not move.
- **Other options.** A linear map (`from + hue × arc`): the identity at
  360°, but a seam through every red in the picture for any narrower arc;
  the fold at every width (no identity: the defaults would change the
  picture).
- **To reverse.** The `if (arc > 180.0)` block in `palette.glsl`.
- **Rough edge.** Near 360° the return from the far red runs through a
  narrow band of input hues just below 360 (at 350° wide, the last few
  degrees of magenta-red carry a short rainbow back to `from`); never
  seen on a projector.
- **Judge it.** Checks 267, 268.

### 293. Saturation and value are mapped linearly, never clamped

- **Built.** Saturation 0–1 lands linearly on `sat_from` → `sat_to`,
  value 0–1 on `val_from` → `val_to` (`mix(from, to, x)`): the whole
  input range lands inside the slice and uses all of it, so a red slice
  with val 0.3 → 1 lifts black to a dark red and keeps white white. On a
  see-through ground the result is still scaled by the pixel's alpha.
- **Other options.** A clamp (cuts detail off at both ends; the owner
  asked for a map); a curve (gamma) on value.
- **To reverse.** The `mix` calls in `palette.glsl`.
- **Rough edge.** A grey pixel has no hue (it reads as red), so once
  `sat_from` is above 0 a grey wireframe takes the slice's `from` colour.
- **Judge it.** Checks 267, 268.

### 294. `from` above `to` inverts

- **Built.** `sat_from > sat_to` or `val_from > val_to` is legal and
  inverts that axis: `val 1 → 0.2` turns the darkest pixel the brightest
  and the brightest a dim one (a test). Nothing refuses it.
- **Other options.** Sort the two ends (no inversion; one less knob's
  meaning).
- **To reverse.** Swap the ends in `palette.glsl` when from > to.
- **Rough edge.** On the overlay a black ground inverted to bright stays
  clear (alpha scales it), so the inversion shows on the shape only.
- **Judge it.** Check 269.

### 295. Old documents are read as the slice on load

- **Built.** `palettecompat.palette_slice` (a leaf module: plain dicts)
  reads a document carrying the fold's ids (any instance,
  `fx.palette.2.*` too) in the slice's: `hue_from` = centre − width/2 and
  `hue_to` = centre + width/2, wrapped into 0–360 (centre 200 width 60 →
  170 → 230; width 360 → 0 → 360), turn 0, a missing one at its old
  default (centre 0, width 360); `sat_lo/_hi`, `val_lo/_hi` renamed
  `_from/_to`; an id already in the new form wins. When something sets
  the centre outright (a `position` route or a macro's base subscriber on
  it) the arc is laid about 0 and `hue_turn` holds the centre (centre 200
  width 60 → 330 → 30 turned 200), so those rows move to the turn as they
  are. Routes and desk rows: a rename moves the row; any row on the
  centre goes to `hue_turn` (it wraps, so a push through a full turn
  keeps the arc's width — a test); a push on the width becomes half of it
  apart on each end (it widens). Macros: base and depth subscribers on
  the renamed ids follow; a depth subscriber on the centre's route
  follows it to the turn; one on the width's push is split into one per
  end (its from/to scale each half alike); a base subscriber on the width
  is converted about the document's centre when both ends stay inside
  0–360 over its travel, else dropped with a note. It runs on every
  whole-preset load (`Presets.load_doc`, beside plan 26's `pan_world`)
  and every `fx` module load (`library._module_values`), silently; the
  next save writes the new keys. A note only when the palette would show
  the change — on with mix above 0 in compress mode, or a row naming it —
  and the fold was wider than 180°: at 360° "the old fold doubled the
  whole wheel; its slice 0 → 360 now leaves the colours as they are".
  Every preset saved before carries the palette's ids at their defaults
  with it off (a save writes every base): those load with no note and
  no dot (a test on a full snapshot).
- **Other options.** A `units`-style marker (no need: the old ids are
  unambiguous); rewrite the files at launch (`migrate_home`).
- **To reverse.** The two call sites and the function.
- **Rough edge.** A non-push row on the width is kept dormant with a
  note (no single slice param takes it whole), and a width base
  subscriber crossing 0 / 360 is dropped with a note. A wide old fold
  (over 180°) looks different; the note says so. Nothing in the library
  carried the old ids (no factory preset turns the palette on).
- **Judge it.** Check 271.

### 296. `// @param choice [a|b] n "Label"`: a discrete param, drawn as a picker

- **Built.** An effect file may declare `uniform int u_mode; // @param
  choice [compress|gradient] 0 "Mode" tip`: the names in brackets, `|`
  between them, the default's index. `fx.declare` makes it an enum
  (`Kind.ENUM`), so the strip draws a combo, a desk knob steps through
  its choices, a route can switch it, and its readout is the choice's
  name; the uniform gets the index. A float uniform, fewer than two
  choices or a repeated name is refused with the line. The palette's
  `mode` is the only one; every other effect file is unchanged.
- **Other options.** A combo for any integer param of two or three
  values (guessing); chips instead of a combo.
- **To reverse.** The `_CHOICE` form in `fx.parse` and the enum branch
  of `declare`; the palette's header back to `@param 0 1 0`.
- **Rough edge.** A choice name with `|` or `]` in it cannot be written.
- **Judge it.** Check 270.

### 297. The strip: mode picker, "compress into" line, hue / sat / val rows `from → to`

- **Built.** The palette's strip in compress mode reads: **mode** (a
  combo, its label opening the param menu as a row's does), a faint line
  in the owner's words — `compress into: hue 170° → 230° · sat 0.00 →
  1.00 · val 0.00 → 1.00` (`turned 90°` after the hue when turned) — then
  **hue**, **sat** and **val**, each one row of two sliders with `→`
  between them, the hue row with the small turn slider at its end and a
  thin bar of the slice's colours (as turned) under it. The packing by
  name (row 139) gained `_from`/`_to`, which is why `sat_lo`/`_hi` and
  `val_lo`/`_hi` were renamed (every row of the slice reads the same
  way). Gradient mode shows mode, anchors and the four anchor rows as
  before (`HIDDEN_BY_MODE`).
- **Other options.** Keep `_lo`/`_hi` for sat and val (two words for one
  idea on one strip); a hue wheel instead of the bar (more drawing for
  the same information).
- **To reverse.** `ui_fx.strip`'s choice and pair branches,
  `compress_line`, `_hue_bar`.
- **Rough edge.** The bar shows the arc's hues at full saturation and
  brightness, not the slice's sat and val.
- **Judge it.** Check 270.

### 298. The gradient map is kept as the second mode

- **Built.** The owner's words describe the compression; the gradient
  map (brightness through two to four anchor colours) is a different
  transform — it throws the picture's hues away and paints by
  brightness — so it stays, as the picker's second choice, unchanged.
- **Other options.** Remove it (sunset-style ramps lost; `fx` presets
  that use it would load as compression).
- **To reverse.** Delete the mode and its fourteen params.
- **Rough edge.** None known.
- **Judge it.** Check 270.

## The graph by concern (plan 28, N9)

Built on 2026-10-20 after the owner's second look at the GRAPH page
("The graph looks better. The graph needs to be organized better in
terms of the concerns: all things audio need to live in one area; all
things geometry should be grouped in another area; all things shader
should be grouped in another area. Currently, they all sit clustered
together in some pattern that I don't really understand. Also, there
are macros sitting there that don't connect to anything."). The owner's
decision — the canvas organised by concern, a macro with nothing in and
nothing out not drawn by default — is in [`DECISIONS.md`](DECISIONS.md)
"UI" with Who "owner (2026-10-20)"; these rows are what the build chose
where it left a choice open. It supersedes parts of rows 252, 285 and
290 (marked there). Review round 1 added the off effects to the idle rule
(row 305), the shaders' wrap (306), the area chips (307), the depths
inside the modulation and the audio (308) and the titles' floor (309),
and asks the owner one question (310). Measured on party-trip in the
real app at the control window's 960 × 900 after round 1 (53 nodes, 31
drawn, 22 idle; 50 wires, 233 cables; the canvas 10 columns, the
shaders 4 in 2 rows): the page draws in **1.42 ms** median collapsed,
1.71 ms with the whole canvas framed (6.7×), 1.59 ms on SHADERS framed,
1.61 ms after a tidy (N7: 1.27 ms). On every factory preset, and on
party-trip with the whole effect chain wired as each graph fixture says,
no drawn wire runs back or within a column but the shaders' row
returns. No preset was edited or added; `apc40.py`, `midi.py` and
ROUTING's desk section are untouched.

### 299. Five areas, left to right: controllers → audio → modulation → geometry → shaders

- **Built.** `graphview.auto_layout` (now `layout`) lays the canvas in
  areas, each its own columns: **controllers** (the devices, the keys, a
  placeholder, a desk template) one column; **audio** (the analyzer, the
  band, tempo, master, audio and scene params' nodes) one; **modulation**
  (the LFOs, the modifiers, the macros, the `lfo.trigger` group) one;
  **geometry** (the shape, the hands, a cloud, the camera's *eye*, and
  the scene, its cover and the hands' layer that draw them) and
  **shaders** (the capture, the history, the effects, the composites,
  the outputs last) each as many columns as their render nodes are deep
  in the render graph, counted from the area's shallowest. A node's area
  is one table, `graphview.AREA` (by kind, by `group:<g>`, by render
  class — `area_of`). Saved positions still win (the `layout` keys, the
  undo marks); a placed node takes no room. On party-trip: controllers
  column 0, audio 1, modulation 2, geometry 3–5, shaders 6–12 (headless
  graph; the real app's 14-effect chain runs to column 22).
- **Other options.** Top to bottom bands (the page is tall and narrow,
  but the widget draws every wire from a node's right to the next node's
  left, so a band below its source reads as a loop back); N2's columns
  by kind (the "pattern I don't really understand").
- **To reverse.** `graphview.AREA`, `AREAS`, `_columns`, `layout`.
- **Rough edge.** ~~The shaders area is as wide as the scene pipeline is
  long~~ — built in review round 1: the chain wraps in rows of four and
  the off effects are idle (rows 305, 306); the canvas is 10 columns.
- **Judge it.** Check 272.

### 300. The audio before the modulation; the LFOs are modulation

- **Built.** The audio is the second area, before the modulation: the
  analyzer is a source the modulation reads (a band into a modifier, a
  band onto an LFO's rate) as well as the look, so its wires run right;
  the audio's params (bands, tempo, master, the band scenes) are set
  only by the controllers, from its left. The LFOs sit with the
  modifiers and the macros in **modulation**: each is a source like a
  modifier, and its tempo sync is a knob, not a cable from the audio.
- **Other options.** The brief's sketch, modulation before the audio (a
  band into a modifier would then run back); the LFOs in the audio as
  tempo-synced sources.
- **To reverse.** `AREAS`' order; `AREA["lfo"]`.
- **Rough edge.** A route from an LFO or a macro onto a band's param
  would run back (none in a factory preset).
- **Judge it.** Check 272.

### 301. Each area's title: faint words on the canvas, no node

- **Built.** **CONTROLLERS**, **AUDIO**, **OTHER**, **MODULATION**,
  **GEOMETRY**, **SHADERS** drawn on the canvas's own draw list over each
  area's first column, in a title row above its nodes (`TITLE_H`), at
  30 % of the text colour, before the nodes (behind them); 30 canvas
  units tall at full zoom, kept 18 px on screen while zoomed out
  (`ui_graph.title_size`), never wider than its area's columns. Nothing
  to select, drag or delete.
- **Other options.** A node-editor group node (selectable and draggable,
  and a drag would move it off its area).
- **To reverse.** `ui_graph._titles`, `titles`, `title_size`.
- **Rough edge.** The titles stay at the auto layout's place when you
  drag boxes away. (A long title's shrinking is row 309's: a floor and
  a short word.)
- **Judge it.** Check 272.

### 302. The idle rule, by kind: macros, LFOs, group nodes and lost devices

- **Built.** A node is idle (`graphview.is_idle`, `VNode.idle`) when no
  cable starts or ends on it and no route names one of its params as a
  `scale` or one of its sources as a `when`; and then: a **macro** only
  while it has no label and no subscriber; an **LFO** and a **group
  node** on that alone; a **device** only while lost (grey, not a
  placeholder — a connected device is drawn even unmapped, it says the
  rig has it). Never idle: a modifier (one just picked waits to be
  dropped on a cable), the analyzer, a render node, an output, the keys,
  a desk template, a placeholder (it has rows). An idle node is not
  drawn and takes no room. On the factory presets: 8 idle macros on
  every preset but lfo-breathe (7), 4 idle LFOs (party-trip 3,
  lfo-breathe 2), the *cloud* group (no point cloud in the default
  graph); in the real app also the disabled bridge.
- **Other options.** Macros only (the owner's words; but the unpatched
  LFOs and the cloud group sat there the same way).
- **To reverse.** `graphview.IDLE_KINDS`, `is_idle`.
- **Rough edge.** An unpatched LFO still runs; hidden, its knobs are
  out of sight (the LFO page keeps them). An effect switched off is idle
  by row 305's rule. The idle words name an off device ("1 off device":
  its status says off) apart from a lost one.
- **Judge it.** Check 273.

### 303. The small "other" area under the audio

- **Built.** A group no area claims — `preset`, `ui`, `desk` and the
  *missing params* node — goes to **other**, titled under the audio's
  last box in the audio's column, so the keys' and the desk's wires into
  it run right from the controllers.
- **Other options.** A column of its own after the controllers (between
  them and the audio); the far right (its wires across the canvas).
- **To reverse.** `graphview.SHARES`, `AREA`'s default.
- **Rough edge.** The *missing params* node holds `audio.play` /
  `stop` / `restart` (no param in this build) under OTHER, not AUDIO.
- **Judge it.** Check 272.

### 304. One idle line an area; its + shows them; tidy closes it

- **Built.** An area with idle nodes draws one small box under its
  nodes in its first column, saying what it holds ("8 idle macros · 3
  idle LFOs" under MODULATION, "1 idle param group" under GEOMETRY,
  "1 lost device" under CONTROLLERS); its **+** draws them under it,
  stacked, so one can be patched; **−** takes them off. A macro patched
  leaves the line and is drawn as any node; unpatched, it goes back. The
  open lines are UI state (`st["idle_open"]`), saved nowhere. The
  picker's **macro ▸** still offers every idle macro; one picked gets a
  label, so it is drawn with the line shut. The head counts "31 nodes
  (22 idle)" (party-trip in the app, after round 1). **tidy** also closes
  the lines and says "laid out 31 nodes in 6 areas, every one collapsed
  · 22 idle off the canvas". An idle node is given no place on the
  canvas while it is not drawn.
- **Other options.** One collapsed "macros" node holding the idle ones
  as ports; a line drawn as text with no box.
- **To reverse.** `ui_graph._idle_line`, `drawn_node`, `toggle_idle`,
  `tidied`.
- **Rough edge.** The line is a box of the editor: it can be dragged,
  but its place is not saved and it goes back on the next layout change.
- **Judge it.** Checks 273, 274.

### 305. An effect switched off with no cable is idle; a through wire spans the hidden run

- **Built.** (Review round 1.) An effect node is idle while its
  `fx.<effect>.on` is false when the view is built and no value cable
  (a route, a desk / pad / key row, a macro subscriber) reaches any node
  of that effect — so a pad that toggles an effect keeps it drawn. Its
  render cables do not count. Not `Effect.on(frame)`: a mix at 0 or the
  stack bypassed would reshape the chain mid-show. `graphview.key` holds
  every effect's on switch, so turning one on from the FX page draws it
  next frame. The chain gets a **through wire** (`graphview.throughs`,
  kind `through`, half-faint, image-coloured) from the node before each
  hidden run to the next drawn node; its hover names the effects it
  passes; it is no render edge — Delete on it is refused in words ("a
  through wire stands for off effects: turn one on (FX) or open the off
  effects line to edit its cables"), a modifier dropped on it does
  nothing. SHADERS' idle line says "9 off effects" (party-trip in the
  app: plasma, kaleido, zoomblur and huecycle on, the other nine off);
  its **+** lays the whole chain out again with no through wire.
- **Other options.** `Effect.on(frame)` (moves with the mix and the
  bypass); keep every effect drawn (the 23-column canvas).
- **To reverse.** `graphview.effect_off`, `effect_switches`, `throughs`;
  `build`'s `cabled` set.
- **Rough edge.** An effect switched on from the FX page moves the chain
  under the owner's eyes (the layout re-stacks): the price of a canvas
  that shows only what runs.
- **Judge it.** Check 275.

### 306. The shaders' chain wraps in rows of four (Z order)

- **Built.** (Review round 1.) Inside SHADERS the chain's depths wrap
  into rows of `SHADER_ROW` = 4 columns, every row left to right, each
  row starting under the tallest column of the one before. The only
  wires that run back are the row returns — a cable from one row to a
  later one (`graphview.returns`), which the no-back-wire test excuses
  and nothing else. On party-trip in the app the canvas is 10 columns
  (was 23), the shaders 4 columns in 2 rows, the whole canvas framed at
  about 6.7× (was 16×).
- **Other options.** Snake rows (every other row right to left: half the
  wires loop back over their own nodes); no wrap.
- **To reverse.** `graphview.SHADER_ROW`, `_grid`.
- **Rough edge.** A row return crosses its row from right to left; with
  two pipelines (the scene's and the scene + hands') two of them do.
- **Judge it.** Check 276.

### 307. Frame an area: five chips on the head, or a click on its title

- **Built.** (Review round 1.) Under the head's first line,
  **CONTROLLERS · AUDIO · MODULATION · GEOMETRY · SHADERS** as chips
  (wrapped to the page); a click frames the canvas on that area's drawn
  boxes and its idle line (`ui_graph.frame_area`: they are selected, the
  view brought to them, the selection cleared). A click on the canvas
  background inside an area's title does the same (`_title_click`). This
  is how "at a glance" holds on a page about 390 px wide.
- **Other options.** A minimap; the editor's own "frame selection" key
  (F) only.
- **To reverse.** `ui_graph._area_chips`, `frame_area`, `_title_click`.
- **Rough edge.** Framing clears whatever was selected.
- **Judge it.** Check 276.

### 308. The modulation and the audio laid out by their own depth

- **Built.** (Review round 1.) Every area is laid out by depth over its
  own cables, as the render nodes always were (`graphview._depths`: the
  longest path over the cables between the area's drawn nodes, a loop's
  closing cable left out). In MODULATION an LFO or a macro fed by
  nothing is at 0, a modifier one past what feeds it, an LFO whose depth
  another LFO drives one past it, an LFO whose rate a macro sets one
  past the macro; in AUDIO a band group fed by the analyzer one past it.
  So an LFO → modifier, a smooth → combine (check 265) and a macro → LFO
  knob cable run right instead of looping within one column.
- **Other options.** One column per kind inside the modulation (LFOs,
  modifiers, macros: a macro into an LFO would still run back).
- **To reverse.** `graphview._depths`, `_grid`.
- **Rough edge.** A loop (two LFOs on each other's depth) draws its
  closing cable back.
- **Judge it.** Check 272.

### 309. Titles: never under 12 px on screen; a short word when the long one will not fit

- **Built.** (Review round 1.) A title may be as wide as the distance to
  the next title on its row (`ui_graph.title_room`); its size is 30
  canvas units, kept 18 px on screen zoomed out, held to that room — and
  never under 12 px on screen: when the word will not fit at that it
  falls back to a short one (CTRL, AUD, OTH, MOD, GEO, SHD;
  `graphview.SHORT_TITLES`). On the whole canvas framed (6.7×) the head
  reads CTRL · AUDIO · MOD · GEOMETRY · SHADERS.
- **Other options.** Two-line titles; staggered rows.
- **To reverse.** `ui_graph.title_fit`, `title_room`, `TITLE_FLOOR`.
- **Rough edge.** OTHER, on its own row under AUDIO, is held to one
  column.
- **Judge it.** Check 272.

### 310. Open question for the owner (not built): GRAPH asking for the whole control window

- **The question.** With the areas, the wrap and the chips, the whole
  canvas framed still sits at about 6.7× on CONTROLS' 540 px panel (a
  canvas about 390 px wide): the titles read, the boxes' words do not.
  The only way the whole canvas reads at the zoom a box's title needs
  is for GRAPH to take the control window's full width (960 px, about
  2.5× more canvas) — the desk and the cheat sheet would give way while
  GRAPH is open.
- **Built.** Nothing: the panel's width is `ui.PANEL_W`, shared by every
  page; widening CONTROLS by hand works today.
- **Other options.** Keep the panel; a GRAPH window of its own.
- **Judge it.** The owner's call.

## Plan 32 — media (rows 321–339)

Rows 321–339 were answered by the owner on 2026-10-22, in the session that
designed plan 32, before the build: "(rec)" is the recommendation accepted,
"(owner)" the owner's own. Each row says what the build did; "Rough edge"
and "Judge it" are for the hand checks of group AA (checks 296–316).
These rows follow plan 31's rows 311–320, which are on
`plan-31-integration`; the gap closes when that lands.

### 321. Eight fixed channels, `a`–`h`

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `media.channels.CHANNELS = "abcdefgh"`; each channel has six
  params in the `media` group (`media.<c>.slot / fit / rate / pos / jog /
  loop`, 48 in all), all routable, all Learn targets, none with a desk
  default. The group is a performance group, so the presets page's module
  overview leaves it out (a channel's values mean nothing without its bin).
- **Other options.** Channels added and removed like LFOs (plan 31's
  bank); sixteen channels.
- **To reverse.** `channels.CHANNELS`, `params.build_registry`, the MEDIA
  page's eight columns, `graph.MEDIA_CHANNELS` (a test holds the two
  constants equal).
- **Rough edge.** Unused empty channels sit on GRAPH's idle line ("8 empty
  channels"); eight 45 px columns are tight on the panel.
- **Judge it.** Check 303.

### 322. A channel's choice is a bin of ≤ 16 sources plus a `slot` param

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `media.<c>.slot` is a discrete 0–15 param; the bin is
  `BIN = 16` ids, an empty entry or a missing source reads black. Switching
  is a param, so Learn, the pad, the APC40, the sequencer, a macro, an LFO
  and undo all switch it. The MEDIA page assigns (library pick, then a
  cell), cues (a cell with no pick writes the slot) and empties (right
  click); a bin edit is one undo step.
- **Other options.** A channel holding one source with no bin; a longer
  bin.
- **To reverse.** `channels.BIN`, the slot param's range, the page's bin
  cells.
- **Rough edge.** A bin edit made any way but the MEDIA page (a script) is
  not an undo step.
- **Judge it.** Checks 296, 298.

### 323. Bins live in the preset

- **Answer.** (rec) — accepted 2026-10-22. "Source lists in the preset are
  fine."
- **Built.** A `media` section, `{"channels": {"a": [id | null, …≤16],
  …}}`, one channel to a line. The bins are part of the dirty dot's
  signature and of `Presets.same`, and `library.Marks` carries them, so an
  undo of a load puts them back. A bad id in a file is a note and the entry
  is dropped; the bins land after the values.
- **Other options.** Bins in the show or the session (the rig), not the
  preset.
- **To reverse.** `preset.document`, `MediaState.to_json / from_json`,
  `library.Marks`.
- **Rough edge.** A preset names a place (`local:`, `camera:`) another Mac
  may lack: the banner says so, the channel shows black.
- **Judge it.** Check 301.

### 324. Source ids and places

- **Answer.** (rec) — accepted 2026-10-22: `shared:`, `local:`, `file:`,
  the live kinds; a missing source is black plus the banner.
- **Built.** `shared:<rel>` (`<library>/media/`), `local:<rel>`
  (`<home>/media/`), `file:<abs>`, `camera:<name>`, `syphon:<app>/<server>`,
  `ndi:<stream>` (`ndi:HOST (stream)` when two hosts send one name);
  `phone:` is parsed and never opened. The MEDIA page's banner lists the
  ids the loaded preset names that this Mac lacks, three lines and "and n
  more". A file that is deleted, renamed or replaced mid-show turns its
  channel black and `missing` (a new mtime reloads it); a placeholder is
  `fetching` — black, never opened (a read would block until the download
  lands), out of the banner, opened within a second of the scan that says
  `ready` (final review A-I1); a junk file is `error: …`; none of it
  reaches the frame thread. **Copy to shared** turns a `local:` or `file:` pick into a
  `shared:` one.
- **Other options.** Content hashes instead of paths; a manifest.
- **To reverse.** `media.ids`, `MediaFolder`, the banner in `ui_media`.
- **Rough edge.** A renamed file is a new id (the old bin entry goes
  missing); `file:` ids are absolute and so never portable.
- **Judge it.** Checks 300, 301, 302.

### 325. Live kinds are device-registry kinds that discover feeds

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `ndi`, `syphon` and `camera` are `devices.kinds()` entries on
  `media.live.LiveKind`; an entry in `[[devices]]` turns one on (the
  factory template lists all three, commented, `enabled = true`). A kind's
  `media_sources()` is the dict its last scan published, and
  `DeviceRegistry.media_feeds()` merges the open devices'. Status
  `connected — n feeds`, `lost`, or `error: …`; the registry's retry and
  config watch come free. The kind's name for its feed map is
  `media_sources`, not the design's `feeds`, which `devices.Base` already
  uses for the Router schemes a device feeds (ruling during the build).
  A feed that vanishes is held `lost` and found again with no relaunch; a
  channel follows a device remade by a `config.toml` edit.
- **Other options.** A separate "media sources" registry beside devices.
- **To reverse.** `media.live`, `devices.kinds`, `DeviceRegistry.media_feeds`.
- **Rough edge.** A GRAPH device node is grey unless its status starts with
  `connected` (changed from "connected"); the camera kind lists Continuity
  Camera.
- **Judge it.** Checks 304, 305, 311, 313, 316.

### 326. The transport: `pos` latch scrub, `rate` −4…+4, `jog` a push with coast, `loop` three modes, rate 0 freezes a live feed

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `media.transport.Transport`: speed = `rate + coast`, where only
  `coast` (target 8 × `jog`) springs (`motion.spring`, 2 Hz); a `rate`
  change acts at once (ruling: "× native speed" and "jog coasts back to
  rate" together). While `pos` moves, the playhead is put there; at rest it
  runs on. `loop` / `pingpong` / `once` (the last holds its last frame).
  On a live feed `rate` 0 freezes the frame. The playhead is a readout on
  the MEDIA page and GRAPH, never a param. A channel with no consumer still
  plays but is not uploaded.
- **Other options.** `pos` as an absolute param only; jog as a speed
  multiplier; a rate that springs too.
- **To reverse.** `Transport.step`, `JOG_GAIN`, `JOG_HZ` in `transport.py`.
- **Rough edge.** Rate 0 freezes an NDI or camera feed exactly, and a Syphon
  channel holds too — its copy of the held frame is made only when the
  frame moves — except across a renderer hot reload, which copies the held
  texture name again (check 315). A frozen live channel says `frozen`. `once` never re-arms by itself (a new scrub moves it);
  a proxy retimes VFR clips; scrubbing a clip without a proxy is coarse
  (keyframes).
- **Judge it.** Checks 298, 299, 315.

### 327. Scrub proxies for clips ≤ 10 minutes

- **Answer.** (rec) — accepted 2026-10-22. "I can't imagine we'd have
  longer clips than that."
- **Built.** A clip of ≤ 600 s gets an MJPEG proxy (≤ 1280×720) in
  `<home>/media-cache/proxies/`, never the shared folder, made the first
  time the clip is opened. The build gave it a single cancellable worker of
  its own (`media-proxy`) instead of the pool: a transcode cannot be
  cancelled on the pool and would hold a worker through an app exit. Until
  it exists the original plays forward only; the proxy is picked up at the
  next open.
- **Other options.** Transcode at add time; HAP/ProRes proxies; no proxy.
- **To reverse.** `media.proxy`, `video.VideoSource` (`read_path`).
- **Rough edge.** A failed proxy is retried at every open; clips over 10
  minutes scrub by keyframe, always.
- **Judge it.** Check 298.

### 328. Threads: a pool for jobs that end, a thread per blocking source, the render thread only uploads

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `media.pool` (3 workers) for still decode, folder scans, live
  discovery and joins, and `media-thumb` (1 worker, at most 16 jobs
  waiting, the oldest dropped) for thumbnails; all daemon threads
  (`pool.DaemonExecutor`: `concurrent.futures` joins its own at
  interpreter exit, so one stuck read held Quit — final review A-I1); a
  thread of its own per video
  (`media-video-<name>`), live feed (`media-live-<id>`), NDI out
  (`media-ndi-out-<name>`), plus `media-proxy`, `media-closer` (a dropped
  source is closed there, so a close stuck in a cloud download cannot
  freeze the frame), `media-discover-syphon` and the folder's probe
  threads. `MediaState.poll` steps transports and opens/queues closes;
  `MediaTextures` uploads. Tests: a fake adapter sleeping 200 ms leaves the
  frame untouched; 500 rapid switches balance opens and closes and leave one
  thread; app exit joins everything within 2 s — one deadline shared by
  every close (`pool.begin_exit` / `left`), proved in a subprocess with
  every pool worker stuck in a read, a transcode running and a video stuck
  opening; a huge image reads None until ready.
- **Other options.** One pool for all (a blocking read starves it);
  asyncio.
- **To reverse.** The adapters' thread starts, `Closer`.
- **Rough edge.** Syphon's client release runs on the frame thread. A
  video's close waits 1 s at most and abandons a thread stuck opening; a
  close of another kind hung for good still blocks later closes (leak, not
  stall).
- **Judge it.** Checks 302, 303.

### 329. Caps: 1080p files, 720p live; upload only consumed channels with a new frame

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `CAP_FILE` 1920×1080, `CAP_LIVE` 1280×720, aspect kept, on the
  decoding thread. `MediaTextures.texture` writes only for a channel a
  consumer reads this frame whose `(frame, t)` moved. Syphon textures
  arrive at the server's size and are sampled scaled (a cap would need a
  GPU pass). The MEDIA page's preview of a channel nothing reads is a copy
  at most 320 px wide, each at most 10 a second and two a frame, round
  robin (final review B-I2); a channel the frame reads shows its own
  texture.
- **Other options.** Resize on the GPU; a lower file cap.
- **To reverse.** `frame.CAP_FILE`, `CAP_LIVE`.
- **Rough edge.** Eight consumed 1080p channels at 30 fps is ~2 GB/s of
  texture writes; never measured in a show.
- **Judge it.** Check 303.

### 330. Backdrop under the scene, before the history and the effects; `backdrop.history` off by default; plan 33 settles the order

- **Answer.** (rec) — accepted 2026-10-22. "Stopgap is fine."
- **Built.** `backdrop.channel` (off / a–h), `backdrop.alpha`,
  `backdrop.history`. The scene clears to alpha 0 and is laid over the
  channel (`grounded`); echoes and the dream are drawn over the backdrop.
  With `history` off they are held back by the scene alone (the history's
  `occluder` port — not by the backdrop's brightness, which hid them;
  final review B-I1). With `history` on the capture takes the composite,
  so the echoes hold the backdrop too and the history occludes from its own
  picture as before: occluded by the scene alone, a still backdrop added
  onto itself and washed to white (re-review). So with `history` on, the
  shape's echoes show over the backdrop's dark areas only. An effect placed
  `after scene` is retargeted to the backdrop's composite. The hands-only
  pipeline has none. With no backdrop the graph is unchanged node for node.
- **Other options.** The backdrop inside the history by default; a
  backdrop per output.
- **To reverse.** `graph.default_graph`'s `grounded`, `Renderer.scene_ground`.
- **Rough edge.** With `history` off, echoes are not bent by an effect
  placed after the scene; with `cut_through` on and a backdrop, faint fills
  let the backdrop show through (never eyeballed).
- **Judge it.** Check 296.

### 331. Faces read a channel (`view.media`); `view.bmp_*` dropped on load with a note

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `view.media` (off / a–h) and `view.media_alpha / scale / mode /
  amp / rate` with the old meaning; the faces read the channel's raw
  texture, aspect kept. An old preset's non-empty `view.bmp_file` is
  dropped with `bitmap file <path> is no longer read: put it on a media
  channel`. Ruling: the APC40's factory knob 7 (`cc:0:54 → view.bmp_alpha`)
  keeps working because `view.bmp_alpha` is a hidden alias of
  `view.media_alpha`: an old preset's value lands on `media_alpha`
  (the file's own `view.media_alpha` wins); row 339 forbids new defaults,
  not the keeping of existing ones.
- **Other options.** Retire the knob (free K7); keep a bitmap page beside.
- **To reverse.** `params` (the alias rule), `preset` (the load note).
- **Rough edge.** The alias shows as its own port on GRAPH's shape node,
  like the `band.sel.*` aliases.
- **Judge it.** Checks 297, 314.

### 332. Every effect gets an optional `aux` input; `displace` and `blend`

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** `Effect.INPUTS = {"image", "aux"}`; `_lib.glsl` has `u_aux`,
  `u_aux_on`, `u_aux_size`, `aux(uv)`, `aux_luma(uv)`; unwired is
  transparent black. Any `IMAGE` node may feed it (a channel, the scene,
  the history, another effect), by a wire `{"from": "media.a", "to":
  "acid.2.aux"}`; a loop or a missing end is dormant with words. `displace`
  (luma or red/green moves the picture; amount, mode, angle) and `blend`
  (over, multiply, screen, difference, luma key; key, soft; mix = amount).
  No factory preset uses them. Goldens `displace-luma`, `blend-luma-key`.
- **Other options.** Effects named per input; N aux ports.
- **To reverse.** `graph.Effect.INPUTS`, `fx.py` uniforms, the two shader
  files.
- **Rough edge.** Adding two effect files adds `fx.displace.*` / `fx.blend.*`
  lines to every saved preset (see row 337); an aux from an in-run effect
  reads the scene pipeline's node.
- **Judge it.** Check 297.

### 333. The phone's own HTTPS page is V2; V1 leaves the door open for an NDI camera app

- **Answer.** (owner) — 2026-10-22. Its check with a real phone comes after
  the sprint.
- **Built.** Nothing for phones but the `phone:` id, parsed and never
  opened, and never listed missing. A phone running an NDI camera app is an
  `ndi:` source.
- **Other options.** The HTTPS/WebRTC page (the design in the plan file, §P).
- **To reverse.** n/a (V2 adds the adapter and a kind).
- **Rough edge.** The NDI-camera-app road has never been tried with a real
  phone.
- **Judge it.** Check 312.

### 334. Phone join (V2): a per-rig token in the QR, at most 4, each approved on the host

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** Not built (V2).
- **Other options.** Open join; a PIN per session.
- **To reverse.** n/a.
- **Rough edge.** n/a.
- **Judge it.** No check; V2.

### 335. Resolume / TouchDesigner both ways in V1: NDI in, Syphon in, Syphon out, NDI out; publish-only outputs

- **Answer.** (owner) — 2026-10-22.
- **Built.** In: `ndi` (with `extra_ips`) and `syphon` kinds (row 325). Out:
  `[output]` / `[[output.screens]]` take `syphon = "<name>"`, `ndi =
  "<name>"` and `window = false`. Syphon out hands the texture over on the
  frame thread (0 ms); NDI out reads back through two pixel-pack buffers
  and sends on its own thread (~4 ms of frame time at 1080p), dropping a
  frame when the sender is busy. A window publishes at the render cap, so
  a retina window is not a 4K stream. Rulings: publishers are SYSTEM lines
  (`<kind> out <name> — <fps> fps, readback <ms> ms`), not registry sinks;
  output 1 cannot be publish-only (it holds the GL context and paces the
  loop): `window = false` there is a note. `extra_ips` goes through an
  app-owned `<home>/ndi/ndi-config.v1.json` (`NDI_CONFIG_DIR` set before
  `cyndilib` loads), because `cyndilib` hard-codes the finder's extra IPs.
  Syphon in is a `GL_TEXTURE_RECTANGLE`, copied on the GPU into a 2D
  texture.
- **Other options.** A registry sink per publisher; NDI|HX; a Syphon
  Metal server; clocking the NDI sender.
- **To reverse.** `media.publish`, `config` (the three keys),
  `render._publish`.
- **Rough edge.** `extra_ips` is unverified (the status says so); a change
  after `cyndilib` loaded needs a restart; the NDI copy is 4 ms of a 16 ms
  frame; a hand-edited `window = false` on output 1 is refused.
- **Judge it.** Checks 304–310.

### 336. Dependencies: `av`, `pillow-heif`, `syphon-python`, `cyndilib` in the default install, each imported only when used

- **Answer.** (rec) — accepted 2026-10-22; the phone's (`aiohttp`,
  `aiortc`, `segno`) come with V2.
- **Built.** `pyproject.toml`: `av>=19`, `pillow-heif>=1.8`,
  `syphon-python[opengl]>=0.2` (macOS only; the extra is PyOpenGL, already a
  dependency, which Syphon's GL server needs), `cyndilib>=0.1.3` (its macOS
  wheel carries `libndi`; check the NDI SDK's licence before shipping a
  build), and, beyond the row, `pyobjc-framework-avfoundation` (macOS only,
  for the camera list). `import hyperspace.app` imports none of `av`,
  `pillow_heif`, `syphon`, `cyndilib`, `AVFoundation` (a boundary test).
- **Other options.** Optional extras; a separate install step.
- **To reverse.** `pyproject.toml`, `uv lock`.
- **Rough edge.** `uv sync` pulls four more wheels (a heavier first launch).
- **Judge it.** Check 311 (a fresh `uv sync` on the other Mac).

### 337. Conditional preset `hyperspace.preset/4`, after plan 31's `/3`

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** A preset is saved `/4` only when its document has a `media`
  section with an id, or any `media.*`, `backdrop.*` or `view.media*` value
  away from its default; every other preset is `/2` (`/3` once plan 31
  lands). Load accepts the kind's versions both. **Both Macs sharing a
  library must run this build** to load a `/4` file; an older build refuses
  it.
- **Other options.** Always write `/4`.
- **To reverse.** `preset.uses_media`, `MEDIA_SCHEMA`.
- **Rough edge.** "Every other preset is byte for byte the file it was"
  holds except for the added `fx.displace.*` / `fx.blend.*` value lines
  (two new effect files; plan 30's palette did the same): the test ignores
  them. A `/4` file read by an older build is the cross-build question
  hand check 301 asks.
- **Judge it.** Check 301.

### 338. Base `plan-28-30-integration`, taking it in as it moves

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** Built on `plan-28-30-integration` @ 1a5cc2e. Nothing taken in
  during the build.
- **Other options.** Wait for #224 to merge.
- **To reverse.** n/a.
- **Rough edge.** It lands after #224 and plan 31; preset schema, register
  rows and check numbers renumber at merge if plan 31 does not land first.
- **Judge it.** n/a.

### 339. No desk or APC40 default bindings; Learn for all

- **Answer.** (rec) — accepted 2026-10-22.
- **Built.** No factory row, desk template or APC40 mapping was added;
  `apc40.py` and `midi.py` are untouched. Every channel param is a Learn
  target; the MEDIA page suggests Learning the cue knob to
  `media.<c>.jog`. K7's existing row survives through an alias (row 331).
- **Other options.** Defaults on the clip grid; the cue knob bound to the
  selected channel's jog.
- **To reverse.** n/a (add rows to a profile).
- **Rough edge.** Nothing moves a channel until a performer Learns it.
- **Judge it.** Check 299.
