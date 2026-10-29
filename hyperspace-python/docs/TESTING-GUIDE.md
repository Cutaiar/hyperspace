# Testing guide — what a person still has to check

This is everything about Hyperspace that only a person at the machine can
test, written so that someone who has never seen the project can follow
it. **None of it has been run by a person yet.** Part 1 is everything you
can do with the laptop alone. Part 2 is everything that needs a device
plugged in, grouped by device so that each one is set up once.

Each entry says what it **needs**, what to **do**, what you should see if
it is **right**, what **wrong** looks like, and, where the test changes a
file, what **changes** and how to put it back. The numbers in brackets at
the end of each entry, such as *(check 57, 84)*, are the check numbers in
[`plans/11-hand-checks.md`](plans/11-hand-checks.md), which has the longer
version of each test: an automated test you can run first to see what
"right" looks like, and where in the code a failure points. If something
is wrong, write down the check number and what you saw.

Terms a newcomer may not know (APC40, preset, route, the glass…) are
explained in the [glossary](#glossary) at the end.

## Before you start

1. **Back up the home folder before anything else:**
   `cp -R ~/Hyperspace ~/Hyperspace-backup-<today's date>`, then make a
   second copy to experiment on: `cp -R ~/Hyperspace ~/Hyperspace-try`.
2. **Launch the app:** on branch `main` (`git checkout main`, `git pull`),
   run `cd hyperspace-python && uv sync && uv run hyperspace`. The shape
   entries (L48–L54, A19, D14) and the pattern entries (L55–L68, A20–A23,
   D15) are plan 22's, which is on `main`. The party-fix entries (L69–L71,
   A24–A32, B30–B36, C5) need plan 24, and the device entries (L72–L81,
   A33, B37, B38, F5, G1–G6) plan 27, and the render-graph entries
   (L82–L94, B39, B40, C6, C7, D16–D18) plan 26: until they are merged,
   use branch `plan-24-26-27-integration`. The shader-node entries
   (L95–L102, L129, L130, C9–C11, D19–D23) are plan 30's, and the node-editor entries
   (L103–L128, L131–L135, A34–A36, B41–B45, C8, D24, D25) plan 28's: until they are
   merged, use branch `plan-28-30-integration`. The instanced-field entries
   (L136–L138: thousands of copies, the 3D lattices, Fit) are on `main`.
   The step-sequencer entries (L139–L144) are plan 31's: use branch
   `plan-31-integration` until it is merged. Its APC40 entries (A37–A46) need branch
   `plan-31-a1`, which waits for Dylan's sign-off: run them with him.
   The media entries (L145–L151) are plan 32's, and L152 is the two
   plans together: use branch `plan-31-32-integration`, where they land
   together, until it is merged. The free-graph entries (L153–L157, A47)
   are plan 33's: use branch `plan-33-free-graph` (PR #235) until it is
   merged. A free graph saves as `hyperspace.preset/5`, which an older
   build refuses, so both Macs must run that build before L157.
   The free-frame entries (L158–L162) are plan 35's: use branch
   `plan-34-feedback` (PR #236) until it is merged. A frame that needs the
   new vocabulary saves as `hyperspace.preset/6`, which an older build
   refuses, so both Macs must run that build before L162.
   The feedback entries (L163–L167) are plan 34's, on the same branch:
   run them on the same build as L158–L162, after L158 (a new preset).
   A graph with a delay, resize, echo or dream saves `/5` where its frame
   round-trips, which a plan 33 build reads with a note, so both Macs must
   run that build before L167.
   The hold entries (L179–L181, A48) are plan 38's: use branch
   `plan-38-hold`, then `plan-37-38-39-integration`, until it is merged.
   Two windows open: the picture (the *render window*) and the *control
   window*. **Esc** quits.
3. **Use the copy instead of the real home folder:** in the terminal,
   `export HYPERSPACE_HOME=~/Hyperspace-try` before launching. The app
   then reads and writes only the copy, its config file included. Open a
   new terminal to go back to the real home folder.
4. **The config file** is `config.toml` in the home folder
   (`~/Hyperspace/config.toml`, or `~/Hyperspace-try/config.toml` on the
   copy). Every setting is explained in
   `hyperspace-python/hyperspace/config.py`. Edit it with the app closed,
   then launch again — except the device list (`[[devices]]`), which the
   app re-reads while it runs; the entries that say so edit it live.
5. **The control window's pages** are the column of names down its left
   edge — OUTPUT, VIEW, FACES, BITMAP, CAMERA, LOOKBACK, FX, AUDIO,
   ANALYZER, ROUTING, GRAPH, LFO, SEQ, HANDS, PRESETS, SYSTEM. Click a name to open
   that page. Messages appear in the *footer*, the line along the bottom.

Below, `<home>` means whichever home folder the app is using. ⌘ is the
Command key, ⇧ is Shift; "right-click" is a two-finger click on the
trackpad. F1–F8 are the function keys (hold **fn** if your Mac's top row
changes brightness or volume instead).

> **Known risks while testing**
>
> 1. **For a long session with no APC40, switch MIDI off.** When the
>    APC40 is not plugged in, the app keeps looking for it: every two
>    seconds for the first ten seconds, then every ten seconds (it was
>    every two seconds all night until a fix on 2026-10-05). In rare
>    cases macOS can kill the app while it looks (seen once during
>    automated testing, never yet in the app). The risk is now smaller,
>    not gone; putting `enabled = false` under `[midi]` in the config
>    file (or on the `apc40` entry of a device list) removes it (put it
>    back before testing the desk). A desk plugged in while the app runs
>    is found within ten seconds.
> 2. **Plug every screen in before launching.** A screen plugged in after
>    the app starts is not used until you restart it (⌘R or quit and
>    launch again).

### The order to run things

1. Back up and make the copy (above).
2. **On the copy**, the first launch of this build: L1, then L2 and L3.
   Do not launch on the real home folder before this: the first launch
   rewrites a file there (with a backup).
3. The rest of Part 1, in any order — but L55 and L56 first: L39–L42,
   L53, L55 and L59 on the copy, the others on the real home folder. L43
   (the shared library folder) needs a second Mac and a cloud folder;
   do it whenever both are to hand.
4. Part 2 (a), the APC40. Its entries marked "on the copy" run with
   `HYPERSPACE_HOME` set to the copy. A1 before A4. A20–A23 are the
   listening session for the macro candidates: do them together. A28
   before A29.
5. (L43, if not done yet: two Macs and a shared cloud folder.)
6. Part 2 (b), the hand camera: **B1 (calibration) first**, with nobody
   else in the camera's view. Leave the APC40 plugged in for the entries
   that need both.
7. Part 2 (c), the projector.
8. Part 2 (d), the glass and the projector: D1 first (it sets up two
   outputs in the config file), D14 any time, D12 and D13 last.
9. Part 2 (e), a mouse, and (f), the gamepad — any time.
10. Plan 27's device entries, on the copy: L72 first (it puts the
    device list in the config file), then L73–L76; the FL Studio ones
    (L77–L81) with L46; A33 with the APC40; B37, B38 with the hand
    camera; F5 with the pad; (g) when a second controller or a phone is
    to hand.
11. Plan 26's render-graph entries: L82 and L83 first, on the Mac the
    automated tests run on; then L85–L88; on the copy L89–L91, then
    L92–L94 with the hand camera or recorded hands, and L84 after L76;
    B39 and B40 with the hand camera; C6 and C7 on the projector; D16
    after D2, then D17 and D18.
12. Plan 30's shader-node entries: L95–L97 on the laptop; on the copy
    L98 (with the hand camera or recorded hands), then L99–L102; D19–D23
    with the glass and the projector, after D1.
13. Plan 28's node-editor entries: L103–L116 on the laptop (L113, the
    drag, early: everything else on the GRAPH page builds on it); on the
    copy L117–L121; L122 with two Macs on this build (with L43); the
    legible graph L123–L126 and L128 (the APC40 plugged in), L127 with the
    hand camera and music on the copy; the graph by concern L131–L135 on
    the laptop; A34–A36
    with the APC40; B41–B45 with the hand camera (B43 before B44); C8 on
    the projector; D24 and D25 with the glass and the projector, after
    D1.
14. Plan 31's step-sequencer entries: L139–L143 on the laptop (L141
    with music), L144 with two Macs on the copy; then, on branch
    `plan-31-a1` and with Dylan, A37 first and A38–A46 with the APC40.
15. Plan 32's media entries: L145–L148 on the laptop (L147 with the cloud
    and a second Mac), L149–L150 with Resolume or TouchDesigner, L151 with
    a phone on the copy; then L152, the two plans together, with two Macs.
16. Plan 33's free-graph entries: L153–L156 on the laptop (L156 with a
    live source), L157 with two Macs on the copy, then A47 with the APC40.
17. Plan 35's free-frame entries: L158, L159 and L161 on the laptop (L159
    with a clip), L160 at the rig, L162 with two Macs on the copy.
18. Plan 34's feedback entries, in the same sitting: L163, L164 and L165
    on the laptop (L165 with a clip, L164 with the dream worker), L166
    with L161 (the frame cost, the laptop and then the rig), L167 with two
    Macs on the copy (with L162).
19. Row 394, last: L168 — the shared library migrated to `/6` with both
    Macs on this build (after L162 and L167, which need an older Mac).
20. Plan 36, the WYSIWYG graph: L169-L172 on the laptop (L171 with the
    dream worker, L169 with the TV for two windows), then L173 with both
    Macs on `plan-36-build` last of all, since a `/7` file is refused by
    an older build (it supersedes L168's `/6`).
21. Plan 37, nodes as pictures and the faces, on `plan-37-pictures`:
    L174, L176 and L178 on the laptop, and L175 on the show Mac. L177's
    first half, naming the face patterns to keep, is the owner's and can
    happen any time. Its second half waits for the build that drops the
    others.
22. Plan 38, hold the projector: L179 and L180 on the laptop with a
    second screen as the projector, L181 on the show Mac with music,
    and A48 with the APC40 (Part 2).
23. Plan 39, vision, after `uv sync` on `plan-39-vision`: L185 and L186
    on the laptop first (a still and the camera, no person needed), then
    L182 with the camera, L183 with a dancer on the projector, L184 with
    the camera on a tripod and the party light, L187 on the show Mac with
    two cameras, and L188 on the projector.
24. Plan 40, patches, on `plan-40-build`, on the copy with its `[library]
    path` commented out: L189 (group), then L190 (save and spawn), L191
    (splice, with the TV or projector as a second window) and L193 (the fx
    module presets gone) on the laptop; A49 then A50 with the APC40 (Part
    2); then L192 (the laptop config, no Leap: it uses A49's patch) and
    L194 (twice) last.

## Running the automated tests (tiers)

`uv run pytest` is the inner loop: it runs the fast tier (about 3,940
tests) on every core, in about 17 s on the owner's Mac. It leaves out three
tiers that `tests/conftest.py` marks by name:

- `golden`: the golden-frame draws (`tests/test_golden_frames.py`: 128
  tests, one per rig job, comparing hashes, the shader programs pooled;
  about 12 s and 0.33 GB). Run them after touching rendering, shaders, a preset or
  the graph's evaluation, and once before a merge.
- `slow`: about 1 s or more each (torch dream, undo, plan 12 presets,
  whole-library sweeps).
- `live`: Syphon, NDI and file loopbacks with timeouts; they share global
  names, so they run on one worker and can fail under heavy load. Plan
  39's two real-model tests are here too (Apple Vision and torchvision,
  once each on a made-up frame: `uv run pytest -q --all tests/test_segment.py`).

`uv run pytest --all` runs every tier (about 50 s). Pick a tier with
`-m golden`, `-m slow` or `-m live` (add `--all` or name the file), and
use `-n0` to run serially (for a debugger). A test named by node id is
still skipped by the default `-m`: add `--all`. A new test that takes a
second or more goes in the tables at the top of `tests/conftest.py`.

## Summary

| Entry | What it tests | Part | Needs | Checks |
|---|---|---|---|---|
| L1 | First launch updates the control-mapping file, with a backup | 1 | laptop, the copy | 57, 84, 81 |
| L2 | Presets saved before load without a fuss | 1 | laptop, the copy | 83, 57 |
| L3 | The page holds twenty-four presets (superseded 2026-10-28) | 1 | laptop, the copy | 81 |
| L4 | The app starts, runs and quits; the keys (superseded 2026-10-28) | 1 | laptop | 1 |
| L5 | A config mistake is shown, not a crash | 1 | laptop | 2 |
| L6 | Sound from the microphone | 1 | laptop, music or clapping | 3 |
| L7 | Every page fits and reads from a distance | 1 | laptop | 4 |
| L8 | The stall log | 1 | laptop | 44 |
| L9 | A backup before an old mapping file is converted | 1 | laptop | 30 |
| L10 | The older home-folder conversion lost nothing | 1 | laptop | 33 |
| L11 | Windows reopen where you left them | 1 | laptop | 61 |
| L12 | The effects by eye | 1 | laptop | 5 |
| L13 | Clicking an effect's name opens it without switching it | 1 | laptop | 59 |
| L14 | An effect that is not running says why | 1 | laptop | 60 |
| L15 | An effect aimed at the faces | 1 | laptop | 91 |
| L16 | Nothing aimed at the faces changes nothing | 1 | laptop | 92 |
| L17 | The trail carries the faces' effects | 1 | laptop | 93 |
| L18 | Drag an effect to reorder (trackpad) | 1 | laptop | 94 |
| L19 | No see-through picture | 1 | laptop | 6 |
| L20 | Tap tempo and the LFO's downbeat | 1 | laptop, music or metronome | 7 |
| L21 | Code edits take effect while running | 1 | laptop | 8 |
| L22 | Tuning the dream, and the rare stall | 1 | laptop, music | 9 |
| L23 | The LOOKBACK page reads | 1 | laptop | 95 |
| L24 | Dream speed | 1 | laptop | 96 |
| L25 | The dream's layer cannot be performed | 1 | laptop | 63 |
| L26 | WAKE without the dream still draws | 1 | laptop | 46 |
| L27 | Instances down to zero | 1 | laptop | 62 |
| L28 | Instance layouts | 1 | laptop | 97 |
| L29 | Loading a preset resets everything it should | 1 | laptop | 38 |
| L30 | What the show starts on (superseded 2026-10-28) | 1 | laptop | 40 |
| L31 | Undo a slider drag | 1 | laptop | 48 |
| L32 | Undo a preset load | 1 | laptop | 50 |
| L33 | The Home key (superseded 2026-10-28) | 1 | laptop | 54 |
| L34 | The key legend is off at launch | 1 | laptop | 58 |
| L35 | One Unbind | 1 | laptop | 64 |
| L36 | The right-click menu from labels and meters | 1 | laptop | 68 |
| L37 | The big desk drawing | 1 | laptop | 69 |
| L38 | The ROUTING filter | 1 | laptop | 71 |
| L39 | Hide presets from the list (superseded 2026-10-28) | 1 | laptop, the copy | 86 |
| L40 | Rename a preset (superseded 2026-10-28) | 1 | laptop, the copy | 87 |
| L41 | The trash | 1 | laptop, the copy | 53, 88 |
| L42 | The unsaved dot from a step back (superseded 2026-10-28) | 1 | laptop, the copy | 89 |
| L43 | The shared library folder | 1 | laptop, a second Mac, a shared cloud folder | 139–143 |
| L44 | One output is as it was | 1 | laptop (recorded hands) | 99 |
| L45 | The HANDS page explains a bad setting | 1 | laptop | 100 |
| L46 | Sending to FL Studio | 1 | laptop, FL Studio | 27 |
| L47 | Receiving from FL Studio | 1 | laptop, FL Studio | 28 |
| L48 | The shapes turn through 4D and never go flat | 1 | laptop | 113 |
| L49 | The Heart turns with the music, in 3D | 1 | laptop, music | 114 |
| L50 | The Star, Starfruit, Rose and Möbius strip by eye | 1 | laptop | 115 |
| L51 | The Klein bottle | 1 | laptop | 116 |
| L52 | Stepping to the Klein bottle (keys) | 1 | laptop, the copy | 117 |
| L53 | Presets that show a changed shape | 1 | laptop, the copy, music | 118 |
| L54 | The turntable pictures | 1 | laptop, no app | 119 |
| L55 | The FACES page fits on the Mac | 1 | laptop, the copy | 120 |
| L56 | Every pattern draws on the Mac | 1 | laptop | 121 |
| L57 | Find a look, as a first-time user | 1 | laptop, music, a newcomer | 125 |
| L58 | The little pictures on the pattern buttons | 1 | laptop, music | 126 |
| L59 | "+ SUB": route a band from the page | 1 | laptop, the copy | 127 |
| L60 | "all neutral" in one step | 1 | laptop | 128 |
| L61 | One set of routes on every pattern | 1 | laptop, music | 122 |
| L62 | No jumps over a long set | 1 | laptop, music | 123 |
| L63 | Colour turning, faces apart, on the 120-cell | 1 | laptop | 124 |
| L64 | MARBLE's frame rate | 1 | laptop | 130 |
| L65 | KALEIDO and TRUCHET as art | 1 | laptop, music | 131 |
| L66 | The factory presets with music (superseded 2026-10-28) | 1 | laptop, music | 132 |
| L67 | `legacy6` in silence | 1 | laptop, music | 137 |
| L68 | WARP at full on HEX | 1 | laptop | 138 |
| L69 | The palette fold | 1 | laptop (APC40 for the fader) | 166 |
| L70 | A saved palette, and the palette's controls | 1 | laptop, the copy | 167 |
| L71 | Lines and points opacity | 1 | laptop | 154 |
| L72 | Every device on the SYSTEM page | 1 | laptop, the copy | 168 |
| L73 | Change the device list while the app runs | 1 | laptop, the copy | 173, 174 |
| L74 | A broken device does not stop the show | 1 | laptop, the copy | 170 |
| L75 | The pages offer what the rig lists | 1 | laptop, the copy | 178 |
| L76 | A recorded point cloud plays | 1 | laptop, the copy | 190 |
| L77 | A setting sent to FL Studio | 1 | laptop, FL Studio, the copy | 181 |
| L78 | The bridge's old "send" list becomes rows, once | 1 | laptop, FL Studio, the copy | 182 |
| L79 | Sending a setting never asks a question | 1 | laptop, FL Studio, the copy | 183 |
| L80 | The hands' own port, now a device | 1 | FL Studio, hand camera or a tape, the copy | 184 |
| L81 | The hands' port in the device list | 1 | laptop, the copy | 185 |
| L82 | The golden pictures match (the gate Mac) | 1 | the gate Mac | 191 |
| L83 | Every preset beside its golden picture | 1 | the gate Mac | 192 |
| L84 | A recorded point cloud in the picture | 1 | laptop, the copy | 216, 217, 218 |
| L85 | The time each part of the picture takes | 1 | laptop | 194, 210 |
| L86 | The shape where it always was; the eye | 1 | laptop | 196 |
| L87 | Zoom grows the shape; Screen strokes | 1 | laptop (recorded hands) | 197, 198 |
| L88 | The naming rule | 1 | reading, L90 | 193 |
| L89 | A preset that says how its picture is wired | 1 | laptop, the copy, recorded hands | 211, 209 |
| L90 | Two acids | 1 | laptop, the copy | 212 |
| L91 | The wiring in words | 1 | laptop, the copy | 215 |
| L92 | Hands inside the shape | 1 | laptop, the copy, recorded hands (hand camera for the last part) | 204, 205 |
| L93 | A hands layer that goes behind the shape | 1 | laptop, the copy, recorded hands | 207 |
| L94 | Hands as lines | 1 | laptop, the copy, recorded hands | 214 |
| L95 | A time for each effect on the SYSTEM page | 1 | laptop | 220 |
| L96 | Switching effects changes only the picture | 1 | laptop | 221 |
| L97 | An effect on the faces still bends only the faces | 1 | laptop | 230 |
| L98 | The palette on the hands only | 1 | laptop, the copy, recorded hands | 223 |
| L99 | A placement the app cannot follow is a note | 1 | laptop, the copy | 225 |
| L100 | A placement with nothing to sit on says so | 1 | laptop, the copy | 226 |
| L101 | The placements in words | 1 | laptop, the copy | 228 |
| L102 | The FX page's placed chip | 1 | laptop, the copy | 229 |
| L103 | An LFO on another LFO's depth, the same frame | 1 | laptop | 232 |
| L104 | A loop is refused in words | 1 | laptop | 233 |
| L105 | A delay lets a loop run | 1 | laptop | 234 |
| L106 | Every LFO still runs | 1 | laptop | 235 |
| L107 | Each modifier with music | 1 | laptop, music | 236 |
| L108 | Modifier edits are undo steps | 1 | laptop | 240 |
| L109 | The GRAPH page shows what ROUTING shows | 1 | laptop | 242 |
| L110 | Settings sit on the part of the picture they belong to | 1 | laptop | 243 |
| L111 | Hover and select | 1 | laptop | 245 |
| L112 | Quit, restart and a code edit with GRAPH open | 1 | laptop, a terminal | 246 |
| L113 | Drag a cable on the laptop's screen | 1 | laptop | 247 |
| L114 | Delete on the canvas | 1 | laptop | 250 |
| L115 | A wrong picture cable is refused in words | 1 | laptop, the copy | 253 |
| L116 | Add and delete an effect on the canvas | 1 | laptop | 255 |
| L117 | A preset holds its modifiers | 1 | laptop, the copy | 238 |
| L118 | A desk template's modifiers | 1 | laptop, the copy | 239 |
| L119 | Boxes stay where you put them | 1 | laptop, the copy | 244 |
| L120 | A desk template as one box | 1 | laptop, the copy | 257 |
| L121 | A preset from before this build loads with no note | 1 | laptop, the copy | 260 |
| L122 | A patch shared between two Macs | 1 | two Macs on this build, a shared folder | 259 |
| L123 | The closed graph reads at a glance | 1 | laptop (the APC40 helps) | 261 |
| L124 | Open two boxes: the real cables | 1 | laptop | 262 |
| L125 | Drop a cable on a closed box | 1 | laptop | 263 |
| L126 | Tidy says what it did; the details button | 1 | laptop | 264 |
| L127 | The energy patch from GRAPH alone | 1 | laptop, hand camera, music, the copy | 265 |
| L128 | ROUTING points to GRAPH; the desk lines as before | 1 | laptop, APC40 | 266 |
| L129 | The palette's Mode is a picker; its rows read as the slice | 1 | laptop | 270 |
| L130 | An old palette preset (centre and width) loads as the same look | 1 | laptop, the copy | 271 |
| L131 | The three areas at a glance | 1 | laptop (the APC40 helps) | 272 |
| L132 | A macro shows up when you patch it | 1 | laptop | 273 |
| L133 | Tidy puts everything back in its area | 1 | laptop | 274 |
| L134 | The off effects are one line | 1 | laptop | 275 |
| L135 | Five buttons frame the areas | 1 | laptop | 276 |
| L136 | Four thousand copies hold the frame rate | 1 | laptop | 277 |
| L137 | Fit leaves no copy cut by the edge | 1 | laptop, a second screen helps | 278 |
| L138 | The lattices read as 3D | 1 | laptop, a mouse helps | 279 |
| L139 | Seven LFOs, then sixteen | 1 | laptop, the copy | 280 |
| L140 | The SEQ page from across the room | 1 | laptop | 281 |
| L141 | The drum pattern against music | 1 | laptop, music | 282 |
| L142 | The trigger lines the pattern up | 1 | laptop | 283 |
| L143 | The lanes on the GRAPH page | 1 | laptop | 284 |
| L144 | A pattern preset on an older build | 1 | two Macs, the copy | 285 |
| L145 | A still as the backdrop; the faces and `aux` (plan 32) | 1 | laptop, a picture | 296, 297 |
| L146 | A video: speed, scrub, loop; the cue knob as a jog wheel | 1 | laptop; APC40 for the jog | 298, 299 |
| L147 | A file dropped in the media folder appears; a missing-local banner | 1 | laptop; the cloud and a second Mac | 300, 301 |
| L148 | Junk files, a renamed clip, rapid switching; the MEDIA page at distance | 1 | laptop | 302, 303 |
| L149 | Syphon and NDI in from Resolume and TouchDesigner; `extra_ips` | 1 | laptop, Resolume or TouchDesigner, a second Mac | 304–307, 313, 315 |
| L150 | Syphon and NDI out; a publish-only output | 1 | laptop, Resolume or TouchDesigner, a second screen | 308–310 |
| L151 | A webcam; a phone through an NDI camera app; an old bitmap preset | 1 | laptop, a phone, the copy | 311, 312, 314, 316 |
| L152 | A preset with a pattern and a bin, saved and reloaded (plans 31 + 32) | 1 | laptop, a picture, the copy; a second Mac | 317 |
| L153 | The headline graph; reordering the run by dragging; the FX page on a branch (plan 33) | 1 | laptop, a clip, a camera, the copy | 318, 320, 321 |
| L154 | A drop beside a cable; a shader back into the faces on the layout | 1 | laptop, the copy | 325, 326 |
| L155 | The FX page with a big graph, from across the room | 1 | laptop | 327 |
| L156 | A channel lost on the faces mid-show; the frame cost of branches and a switch | 1 | laptop, a live source | 323, 324 |
| L157 | An old party preset looks the same; a free graph on an older build | 1 | two Macs, the copy | 322, 328 |
| L158 | A new preset; the owner's delete sequence on GRAPH (plan 35) | 1 | laptop, the copy | 342, 343 |
| L159 | A channel alone on All outputs; the OUTPUT page; LOOKBACK's records | 1 | laptop, a clip, the copy | 344, 346, 349 |
| L160 | The glass's mutes; hands through the effects on output 2 | 1 | the rig, hands | 347, 348 |
| L161 | The canvas at distance; SYSTEM before and after | 1 | laptop, the older build | 350, 351 |
| L162 | A library preset looks the same; a `/6` file on an older build | 1 | two Macs, the copy | 345, 352 |
| L163 | The infinite mirror, an empty delay, trails (plan 34) | 1 | laptop, the copy | 332, 333 |
| L164 | A loop refused in words; an echo on the faces and at the hands; the dream | 1 | laptop, the copy, the dream worker | 334, 335, 336 |
| L165 | A resize into a delay with an LFO on the crop; a resize before an effect; a window resize mid-feedback | 1 | laptop, a clip, the copy | 337, 338, 339 |
| L166 | The frame cost of a delay, a resize and echoes | 1 | laptop, then the rig | 340 |
| L167 | A delay saved on this build, opened on a plan 33 build | 1 | two Macs, the copy | 341 |
| L168 | The library migrated to `/6`; both Macs on this build (row 394) | 1 | two Macs, the shared library | 353 |
| L169 | The quick wins on GRAPH; rewire output 1; cut a bus cable; All outputs stays put (plan 36) | 1 | laptop, the TV, the copy | 354-361 |
| L170 | A new preset shows a shape; each starter (plan 36) | 1 | laptop, a clip, the copy | 362, 363 |
| L171 | Tracers without the dream; the dream alone; `party-wake` live (plan 36) | 1 | laptop, the copy, the dream worker | 364-366 |
| L172 | Preset only; the nine re-recorded goldens (plan 36) | 1 | laptop, the gate Mac | 367, 369 |
| L173 | The libraries migrated to `/7`; both Macs on this build (plan 36) | 1 | two Macs, the shared library | 368 |
| L174 | Every node shows its picture; the tint switch (plan 37) | 1 | laptop, the copy | 370 |
| L175 | What the pictures cost; a hidden node stops being made (plan 37) | 1 | the show Mac, the copy | 371, 374 |
| L176 | Expand and collapse; hover a picture (plan 37) | 1 | laptop, the copy | 372, 373 |
| L177 | Pick the face patterns to keep; the FACES page after (plan 37) | 1 | laptop, then the show Mac, music | 375 |
| L178 | `acid-scene` draws forward (plan 37) | 1 | laptop, a scratch home | 376 |
| L179 | Hold, then build a new look behind GRAPH (plan 38) | 1 | laptop, a second screen, the copy, music | 377, 378 |
| L180 | Take and drop (plan 38) | 1 | laptop, a second screen, the copy | 379, 380 |
| L181 | What a hold costs; a band on a held setting (plan 38) | 1 | the show Mac, music, a Syphon or NDI source | 382, 383 |
| L182 | A webcam cut by person; the cut-out starter; the quality levels (plan 39) | 1 | show Mac, a camera, the copy | 384, 385 |
| L183 | The edge and the flicker, with a dancer (plan 39) | 1 | the projector, a camera, a dancer | 386 |
| L184 | Motion on a still camera, and the party light (plan 39) | 1 | a camera on a tripod, a party light | 387 |
| L185 | A still as a mask; a mask on a window (plan 39) | 1 | laptop, a still, the copy | 388, 389 |
| L186 | Edges on the shape, on the camera, into a cut (plan 39) | 1 | laptop or the projector, a camera | 390 |
| L187 | Two cameras, two segments; unplug a camera (plan 39) | 1 | show Mac, two cameras | 391, 392 |
| L188 | A half-transparent face over a bright picture, cut-through on and off (plan 39) | 1 | the projector, a still, the gate Mac | 393 |
| L189 | Group some nodes, open them, ungroup them (plan 40) | 1 | laptop, the copy | 394 |
| L190 | Save a group as a patch; spawn it into a new preset; wire as saved (plan 40) | 1 | laptop, the copy | 395 |
| L191 | Drop a patch on a cable (plan 40) | 1 | laptop, a second screen, the copy | 396 |
| L192 | A preset that wants a Leap on a rig without one (plan 40) | 1 | laptop (no Leap listed), the copy | 399 |
| L193 | The fx module presets are gone; the FX page is not (plan 40) | 1 | laptop | 400 |
| L194 | The same patch twice in one preset (plan 40) | 1 | laptop, the copy | 401 |
| L195 | A macro wired from the param menu moves the param (row 537) | 1 | laptop | 402 |
| L196 | The PRESETS page is the library (plan 41) | 1 | laptop, the copy | 403 |
| L197 | Drop a node on a cable: the drag shows what will happen, ⌘ for a wired effect | 1 | laptop | 404 |
| A1 | Knobs follow the app when it changes a value | 2a | APC40 | 31 |
| A2 | The desk wakes up; knobs, rings, faders | 2a | APC40 | 10 |
| A3 | SHIFT latches and lights | 2a | APC40 | 34 |
| A4 | Switching layer: knobs jump, faders wait | 2a | APC40 | 35 |
| A5 | Rings show the setting, lights show the state | 2a | APC40, music | 11 |
| A6 | Tempo buttons and the pad grid | 2a | APC40, music or metronome | 12 |
| A7 | The on-screen desk matches the real one | 2a | APC40 | 45, 69, 58 |
| A8 | Device knobs on each preset | 2a | APC40, the copy | 36, 85 |
| A9 | One knob, two directions | 2a | APC40 | 39 |
| A10 | Undo a knob turn, and a load from the desk | 2a | APC40 | 49, 50 |
| A11 | Undo a Learn and an Unbind | 2a | APC40 | 51 |
| A12 | OVERDUB is Home (superseded 2026-10-28) | 2a | APC40 | 54 |
| A13 | The crossfader is the master dimmer | 2a | APC40 | 55 |
| A14 | Hold an empty pad to save a new preset into it | 2a | APC40, the copy | 56, 83 |
| A15 | Pad rows 4 and 5 are presets | 2a | APC40, the copy | 82 |
| A16 | Click a control, then a setting | 2a | APC40 | 70 |
| A17 | Knob smoothing | 2a | APC40 | 78 |
| A18 | The instances knob at the bottom | 2a | APC40 | 62 |
| A19 | The cue knob reaches the Klein bottle | 2a | APC40 | 117 |
| A20 | Macro candidates: MACRO PERFORMANCE | 2a | APC40, music, the copy | 133 |
| A21 | Macro candidates: MACRO STREAMS | 2a | APC40, music, the copy | 134 |
| A22 | Macro candidates: MACRO INTENSITY | 2a | APC40, music, the copy | 135 |
| A23 | Macro candidates: MACRO BREAKDOWN DROP | 2a | APC40, music, the copy | 136 |
| A24 | Hold SAVE, tap a pad: ten saves in a row | 2a | APC40, the copy | 148 |
| A25 | Points, lines, faces and rotate on both layers | 2a | APC40 | 149 |
| A26 | A load relights the whole desk | 2a | APC40 | 150 |
| A27 | The desk log | 2a | APC40 | 151 |
| A28 | The track faders belong to the preset | 2a | APC40, the copy | 152 |
| A29 | The sound faders are under SHIFT | 2a | APC40, the copy | 153 |
| A30 | The desk coverage report against what you see | 2a | laptop (APC40 helps) | 155 |
| A31 | A desk template | 2a | laptop, the copy | 156 |
| A32 | Click a control: this preset's settings first | 2a | laptop (APC40 helps) | 157 |
| A33 | The desk plugged in after the app started | 2a | APC40 | 175 |
| A34 | Learn from a pin, with the desk | 2a | APC40 | 248 |
| A35 | The APC40 as two boxes, SHIFT latched and released | 2a | APC40, hand camera | 256 |
| A36 | Whose cable is it; a missing device | 2a | APC40, the copy | 258 |
| A37 | SEND A turns the pads into the pattern, and back | 2a | APC40, the copy, `plan-31-a1` | 286 |
| A38 | Yellow over green | 2a | APC40, `plan-31-a1` | 287 |
| A39 | No flicker at speed | 2a | APC40, `plan-31-a1` | 288 |
| A40 | The bottom row is the playhead and the length | 2a | APC40, `plan-31-a1` | 289 |
| A41 | Scene buttons pick and mute a lane | 2a | APC40, `plan-31-a1` | 290 |
| A42 | A held bank pad across SEND A saves nothing | 2a | APC40, the copy, `plan-31-a1` | 291 |
| A43 | SHIFT with the pattern up | 2a | APC40, `plan-31-a1` | 292 |
| A44 | QUANT with the pattern up | 2a | APC40, `plan-31-a1` | 293 |
| A45 | Switch the desk off and on with the pattern up | 2a | APC40, `plan-31-a1` | 294 |
| A46 | SEND A after the desk fell back to Generic mode | 2a | APC40, `plan-31-a1` | 295 |
| A47 | A switch over three channels on a knob, into the faces | 2a | APC40, the copy | 319 |
| A48 | Hold and take on two desk buttons (plan 38) | 2a | APC40, the copy | 381 |
| A49 | A patch brings its knob, and a sheet asks when the knob is taken (plan 40) | 2a | APC40, the copy | 397 |
| A50 | The desk unplugged, said; plugged in, said (plan 40) | 2a | APC40, the copy | 398 |
| B1 | Calibrate, and the box it draws | 2b | hand camera | 72, 15 |
| B2 | The probe sees both hands | 2b | hand camera | 13 |
| B3 | The HANDS page and which way is up | 2b | hand camera | 14, 4 |
| B4 | A hand outside the box | 2b | hand camera | 73 |
| B5 | The default feel | 2b | hand camera | 16 |
| B6 | Tilt and turn without moving height | 2b | hand camera | 17 |
| B7 | The thumb-to-ring-finger pinch | 2b | hand camera | 18 |
| B8 | Learn onto a setting a hand already drives | 2b | hand camera | 19 |
| B9 | Pinch zoom while scrolling | 2b | hand camera, scroll | 20 |
| B10 | The right hand deepens the breathing | 2b | hand camera | 21 |
| B11 | A second pinch at another height | 2b | hand camera | 23 |
| B12 | A hand leaving, and "hold" | 2b | hand camera | 24 |
| B13 | A hand moving makes no undo step | 2b | hand camera | 52 |
| B14 | A hand Learn listens to one hand | 2b | hand camera | 66 |
| B15 | A tilt learned is gentle | 2b | hand camera | 75 |
| B16 | Height is still a fader where it should be | 2b | hand camera | 76 |
| B17 | A Learn moves the axis | 2b | hand camera | 77 |
| B18 | Two hands steer the camera | 2b | hand camera | 80 |
| B19 | Hand routes follow the axis by name | 2b | hand camera | 42 |
| B20 | The "screentop" warning | 2b | hand camera | 100 |
| B21 | Zero instances with hands in | 2b | hand camera | 62 |
| B22 | The hands' own port in FL Studio | 2b | hand camera, FL Studio | 29 |
| B23 | A knob on a setting a hand drives | 2b | hand camera, APC40 | 22 |
| B24 | A hand on the desk does not perform; reset | 2b | hand camera, APC40 | 74 |
| B25 | A desk Learn ignores the hands | 2b | hand camera, APC40 | 65 |
| B26 | A knob bumped during a hand Learn | 2b | hand camera, APC40 | 67 |
| B27 | A smoothed knob with everything else | 2b | hand camera, APC40 | 79 |
| B28 | A hand cannot learn a ghost-hand setting | 2b | hand camera, APC40 | 110 |
| B29 | Hand-to-picture delay | 2b | hand camera, 120 fps phone camera | 25 |
| B30 | The new hand sources on the HANDS page and in ROUTING | 2b | hand camera | 158 |
| B31 | Curl and energy | 2b | hand camera | 159 |
| B32 | Spread | 2b | hand camera | 160 |
| B33 | Flick | 2b | hand camera | 161 |
| B34 | Gap and twist | 2b | hand camera | 162 |
| B35 | The grab | 2b | hand camera | 163 |
| B36 | Grab to steer the shape | 2b | hand camera, the copy | 164 |
| B37 | The hands in the device list | 2b | hand camera, the copy | 169, 180 |
| B38 | A tracker that would not start comes up later | 2b | hand camera, a tape, the copy | 172 |
| B39 | The hands where you are, through the shape's camera | 2b | hand camera, the copy (projector helps) | 202, 203 |
| B40 | `hands-orbit` turns only the shape | 2b | hand camera | 200 |
| B41 | A hand on an LFO's depth acts the same frame | 2b | hand camera | 232 |
| B42 | A modifier whose hand goes away lets go | 2b | hand camera | 237 |
| B43 | Hand energy, smoothed, times the kick, into the acid — on ROUTING | 2b | hand camera, music | 241 |
| B44 | The same patch, dragged on the GRAPH page | 2b | hand camera, music, the copy | 249 |
| B45 | Learn from a pin, with a hand | 2b | hand camera | 248 |
| C1 | Choosing the screen; the see-through mode locked | 2c | projector | 26 |
| C2 | A black ground, never see-through | 2c | projector | 43 |
| C3 | Windows reopen on the right screen | 2c | projector | 61 |
| C4 | Dream speed on the rig | 2c | projector | 96 |
| C5 | The hands on the projector | 2c | projector, hand camera | 165 |
| C6 | A hand across the box pans as far as it did | 2c | projector, hand camera | 199 |
| C7 | A preset saved before this build keeps its place | 2c | projector, the copy | 201 |
| C8 | Hands as lines, through the acid, with tracers — by dragging | 2c | projector, hand camera, the copy | 251 |
| C9 | The whole picture as shades of one red | 2c | projector | 267 |
| C10 | A yellow slice and its derivations | 2c | projector | 268 |
| C11 | A slice through red; dark turned bright | 2c | projector | 269 |
| D1 | Two outputs open where the config says | 2d | glass, projector | 101 |
| D2 | The eight output states | 2d | glass, projector, camera | 102 |
| D3 | Hands over or through the effects | 2d | glass, projector, camera | 103, 47 |
| D4 | The dims | 2d | glass, projector, APC40 | 104, 55, 43 |
| D5 | Black is never a mystery | 2d | glass, projector | 105 |
| D6 | An output of another shape | 2d | glass, projector, camera | 106 |
| D7 | Frame rate and tearing with two screens | 2d | glass, projector, camera | 107 |
| D8 | The ghost hands follow the real ones | 2d | glass, camera | 108, 47 |
| D9 | The five hand styles from the audience | 2d | glass, camera | 109 |
| D10 | Effects on the faces, on the rig | 2d | glass, projector | 98 |
| D11 | The party presets on the rig | 2d | glass, projector, camera, APC40 | 41, 32 |
| D12 | A screen not plugged in at launch | 2d | glass, projector | 111 |
| D13 | Unplug the projector mid-run | 2d | glass, projector | 112 |
| D14 | The shapes in 4D from the audience | 2d | glass | 113, 115 |
| D15 | METER and PULSE from the audience | 2d | glass, music | 129 |
| D16 | Every picture as on earlier builds, on the rig | 2d | glass, projector, camera, APC40 | 195, 208 |
| D17 | The hands in the shape on the projector, clean on the glass | 2d | glass, projector, camera, the copy | 206 |
| D18 | Two hands, one in the shape, one on the glass | 2d | glass, projector, camera, the copy | 213 |
| D19 | Each output still gets its own effects | 2d | glass, projector, camera | 222 |
| D20 | The palette on the hands, on both screens | 2d | glass, projector, camera, the copy | 223 |
| D21 | One screen recoloured | 2d | glass, projector, the copy | 224 |
| D22 | The trail holds the bent shape | 2d | glass, projector, the copy | 227 |
| D23 | Two palettes, a different colour on each screen | 2d | glass, projector, the copy | 231 |
| D24 | A second pair of hands on the glass alone | 2d | glass, projector, hand camera, the copy | 252 |
| D25 | Two outputs, two pictures, by wires | 2d | glass, projector, the copy | 254 |
| E1 | Drag an effect with a mouse | 2e | mouse | 94 |
| F1 | A wired Xbox 360 pad is found | 2f | gamepad | 144 |
| F2 | Learn pad — a button | 2f | gamepad | 145 |
| F3 | Learn pad — a stick and a trigger | 2f | gamepad | 146 |
| F4 | Momentary and hold on a pad button | 2f | gamepad | 147 |
| F5 | The pad after a restart, and its sticks | 2f | gamepad | 171, 179 |
| F6 | Two pads at once | 2f | the Xbox pad (Bluetooth), the wired pad, the copy | 219 |
| G1 | A second MIDI controller learned onto a knob | 2g | APC40, a second MIDI controller, the copy | 176 |
| G2 | SHIFT is the APC40's | 2g | APC40, a second MIDI controller, the copy | 177 |
| G3 | A phone's fader moves a setting | 2g | a phone on the same Wi-Fi, the copy | 186 |
| G4 | A phone's button | 2g | a phone, the copy | 187 |
| G5 | The phone goes quiet | 2g | a phone, the copy | 188 |
| G6 | Port 9000 already taken | 2g | a phone, a terminal, the copy | 189 |

Covered by other entries: check 32 is part of D11; check 37 is replaced
by B25; check 47 is finished by D8 (with D3, D9 and B28).

---

# Part 1 — the laptop alone

Keyboard, trackpad, the laptop's screen and its microphone. Nothing
plugged in. (See the known risks box about the APC40 being unplugged.)

## On the copy: the first launch of this build

Run L1–L3 in a terminal where `HYPERSPACE_HOME` points at the copy
(Before you start, step 3).

#### L1. The first launch updates the control-mapping file, with a backup

**Needs:** the copy, never launched on this build.

**Do:**
1. `ls -la $HYPERSPACE_HOME $HYPERSPACE_HOME/projects` and keep what it
   prints.
2. Launch, saving what the app prints:
   `uv run hyperspace 2>&1 | tee ~/first-launch.txt`.
3. PRESETS page → **show ▾** → open your own show; press F1 to F8 in
   turn; quit.
4. Read `~/first-launch.txt`, and run the `ls -la` again.
5. Launch again and quit.

**Right if:**
- The first launch printed one backup line, "backup: bindings.json kept
  as bindings.json.bak-v3" (or a name with a date if that name was
  taken), and one line per change: the crossfader moved to the master
  dimmer (`remapped cc:0:15: overlay.bg → output.dim`), OVERDUB added as
  Home (`added note:0:64 → preset.home`), `added key:…` lines for
  ⌘Z, ⌘⇧Z, Ctrl+Z, Ctrl+⇧Z and Home, and sixteen `added note:…:56` /
  `…:57 → preset.select` lines (pad rows 4 and 5; "remapped …
  view.shape → preset.select" where your file still had the old shape
  pads), then "updated … (N rows changed)". Lines for changes an earlier launch already made do not
  appear.
- On the first launch of a build with plan 24 (the party fixes), also:
  `added note:7:52 → desk.save` (SAVE, unless that button is already
  yours — then a "SAVE not added …" line on every launch), four `added`
  lines for points, lines, faces and rotate on the scene-launch column,
  and eight "moved cc:k:7 → … to the SHIFT layer" lines (the track
  faders' audio strip). This is check 153's first step.
- The SYSTEM page shows the same as one line: "bindings.json updated (N
  rows changed), the old file kept as bindings.json.bak-v3 — each change
  is on stderr".
- `grep -c preset.select $HYPERSPACE_HOME/bindings.json` prints 24.
- The ROUTING page's session section lists X → `output.dim`, B11 →
  `preset.home`, G6·8 → `desk.save` and scene launch 1–4 → points,
  lines, faces and rotate, under "invariant · both layers". The
  clip-stop SAVE AS bar of plan 15 is gone (since 2026-10-09): an old
  file's eight `preset.save_new` hold rows are dropped with a note.
- Your show files have the same size and time as before.
- A crossfader, OVERDUB, clip-stop or pad mapping you had changed by hand
  is left as you had it.
- The second launch prints nothing about the mapping file (except
  "SAVE not added …" when track 8's clip stop was already yours), the
  SYSTEM page has no other such line, and no file's time moves.

**Wrong if:** the file changed with no backup; one of your own mappings
was replaced; the same lines appear on every launch.

**Changes:** `bindings.json` is rewritten, the old one kept beside it as
`bindings.json.bak-v3`. To put it back, copy that file over
`bindings.json`.

**Later:** the first time you launch on the real home folder, the same
lines and its own backup appear there: read them the same way. If your
mapping file was itself just made from a very old `midi_map.json`, the
OVERDUB and SAVE lines arrive on the second launch instead, and it
says so. If you later delete the OVERDUB or the SAVE line from
`bindings.json`, it comes back on the next launch; to switch a button
off, keep its line and add `"enabled": false`.

*(check 57, 84, 81)*

#### L2. Presets saved before load without a fuss

**Needs:** the copy; presets of your own saved on an earlier build.

**Do:** `ls -l $HYPERSPACE_HOME/presets/`. Load three of your presets
from the preset list (PRESETS page → click the preset's name). Run the
`ls -l` again.

**Right if:** no warning, no unsaved dot, and no preset file's time
moved. Exception: if one of them had a control learned onto OVERDUB, a
clip-stop button or a pad in rows 4–5, a warning names it ("dropped … —
that control is invariant …"): that mapping is gone from the live desk
and stays in the file until you save the preset; saving then moves the
old file to the trash.

**Wrong if:** a warning on every load; a file's time moving on a load.

*(check 83, 57)*

#### L3. The page holds twenty-four presets

**Superseded (2026-10-28):** the PRESETS page has no bank pills or `more`; the pads are set on the desk only (check 403, L196).

**Needs:** the copy.

**Do:**
1. PRESETS page. Under the F1–F8 buttons are sixteen smaller buttons,
   four a row, "9" to "24", each "—" when empty (on the factory party
   show, 9 reads TRACER). Open **more** as well.
2. Right-click button 12 → **put preset here…** → pick one of yours.
3. Put another preset on button 20.

**Right if:** no scrollbar on the page, even with "more" open; button 12
reads "12" and the name; the footer says "slot 12: <name>"; the
`projects` folder now holds `<show>.hyp.json.bak-v2-bank8` (the show
file as it was — a factory show opened as shipped has none: its first
change makes your copy); no second backup after button 20.

**Known, not a fail:** with "more" open, a warning line (press an empty
far slot: "slot 13: an empty slot") pushes the page down 11 pixels. Say
whether that is a nuisance.

**Changes:** the show file now has 24 slots; the 8-slot version is kept
as `.bak-v2-bank8`.

*(check 81)*

## Starting, keys and settings

#### L4. The app starts, runs and quits; the keys

**Superseded (2026-10-28):** no party show ships or opens: a fresh library opens an unsaved show called `untitled` on a blank preset, and F1–F8 load the pads of your own library. The R, T, ⌘R and `/` steps still hold (check 403, L196).

**Needs:** laptop.

**Do:**
1. `HYPERSPACE_FRAMES=3 uv run hyperspace`: it should open both windows,
   draw three frames and quit by itself.
2. `uv run hyperspace`. Then: **R**; **F1**; **⇧F1**; **T**; **⌘R**;
   **/**.

**Right if:** step 1 exits cleanly with nothing in the terminal but
one-line notes. In step 2 the *party show* opens (PRESETS page: SHOW
`party`) on its first *preset*, TUMBLE; R resets the view; F1 loads
TUMBLE; ⇧F1 saves the current look as your own TUMBLE; T does nothing
(the see-through *overlay* mode is off unless the config has `[output]`
`overlay = true`); ⌘R restarts the app without resetting the view first;
`/` shows the key legend (the *cheat sheet*), its rows including R
("reset view + camera"), F1–F8 ("load preset · ⇧ saves"), a "Cmd+Z" row
reading "undo · ⇧ redo (or Ctrl+Z)" and a "Home" row reading "home
preset (fn ←)".

**Wrong if:** an error printed, the app not quitting, or a missing row.

**Changes:** ⇧F1 writes your own copy of TUMBLE,
`<home>/presets/tumble.json`, which then takes the factory one's place,
and rewrites the show file, `<home>/projects/party.hyp.json`; remove the
preset with × in the preset list (it goes to the trash) if you do not
want it.

*(check 1)*

#### L5. A config mistake is shown, not a crash

**Needs:** laptop; a config file that still has an `[overlay]` section
(if it already says `[output]`, skip step 1).

**Do:**
1. Launch, SYSTEM page.
2. Quit; add a line `output = 3` as the very first line of the config
   file (above every `[section]` line); launch; SYSTEM page.
3. Remove that line. Move the keys under `[overlay]` to `[output]` and
   delete `[overlay]`; launch.

**Right if:** (1) one note asks for `[overlay]` to be renamed `[output]`.
(2) the SYSTEM page shows the error in the warning colour ("config:
[output] must be a table, not 3") and the app runs. (3) the note is
gone.

**Wrong if:** no note, or the app crashes on the bad line.

**Changes:** the config file; the end state (the section renamed) is the
intended one.

*(check 2)*

#### L6. Sound from the microphone

**Needs:** laptop microphone; clapping or music.

**Do:**
1. AUDIO page: open the input list.
2. Press **M**. Clap.
3. PRESETS page → show ▾ → `house`, then F1 (BIG BLUE WAVE, where sound
   drives the spin). Clap.
4. Plug in or switch on another sound input and press **rescan** beside
   the list.

**Right if:** the list shows the MacBook microphone (and BlackHole, if
installed, already chosen, shown as "● BlackHole…"); macOS asks for
microphone permission once; on the ANALYZER page the six bars' white
input columns jump on a clap and settle, and their red output columns
follow; on BIG BLUE WAVE the spin
changes with the clap; after rescan the new input is listed and your
choice is kept.

**Wrong if:** no permission prompt and flat meters; meters stuck at the
top with a blinking warning in a quiet room; rescan losing the choice.

*(check 3)*

#### L7. Every page fits and reads from a distance

**Needs:** laptop.

**Do:** click through all fifteen pages. Stand about two metres back.

**Right if:** every label and number is readable from there; no page
shows a scrollbar of its own (the ROUTING page's list of rows scrolls
inside its own box, which is intended). The HANDS page with the camera
running is checked in B3.

**Wrong if:** a page scrollbar; a value you cannot read.

*(check 4)*

#### L8. The stall log

**Needs:** laptop; a second terminal.

**Do:** launch. In the second terminal:
`kill -USR1 $(pgrep -f "bin/hyperspace")`.

**Right if:** `<home>/stall.log` gains a block of text (the program's
current state, ending in `app.py` `main` for the main thread); the app
keeps running; the SYSTEM page shows "stall log: …/stall.log (1 raw
dump)".

**Wrong if:** no file, an empty one, or the app quits.

**From now on:** if the picture ever freezes, or a red banner at the
bottom of the control window mentions a render error or a render stall,
keep `stall.log`.

*(check 44)*

#### L9. A backup before an old mapping file is converted

**Needs:** laptop; the old file `~/Hyperspace/bindings.json.bak-plan09`
(made by hand some weeks ago). If you do not have it, skip this.

**Do:**
1. `mkdir -p /tmp/h && cp ~/Hyperspace/bindings.json.bak-plan09 /tmp/h/bindings.json`
2. `HYPERSPACE_HOME=/tmp/h HYPERSPACE_FRAMES=3 uv run hyperspace`
3. Run step 2 again.

**Right if:** the first run prints what it sorted and changed,
`backup: bindings.json kept as bindings.json.bak-v1`, and three
`migrate:` lines; `/tmp/h/` then holds a new `bindings.json`, the old
one as `bindings.json.bak-v1`, `presets/migrated.json` (a preset called
MIGRATED holding the old file's routes, knobs and *macros*) and
`projects/mine.hyp.json` (a show that starts on it). The second run makes
no new backup and rewrites nothing. Your real home folder's hand-made
backups are untouched.

**Wrong if:** no `.bak-v1`; an existing backup overwritten.

**Changes:** only `/tmp/h`; delete it afterwards.

*(check 30)*

#### L10. The older home-folder conversion lost nothing

**Needs:** laptop; the backup from "Before you start".

**Context:** a build from late September converted the home folder to
its current layout the first time it ran. Your home folder has probably
been converted already; then the app prints no `migrate:` lines and you
can only check the result.

**Do:** launch and read what it prints. Compare `ls -la ~/Hyperspace`
with the backup.

**Right if** (if it converts now): one `migrate:` line per rewritten
file naming its backup (`projects/<name>.hyp.json.bak-v1`,
`bindings.json.bak-v2`) and one per preset written. **Right if** (either
way): `<home>/presets/` holds a preset for each filled F-key of each of
your shows; opening a show brings back the look it had; `bindings.json`
holds only your keys, pad and MIDI rows; your hand-learned rows and
knobs are inside the presets (ROUTING page: the routes and the DESK
section); the old `<home>/bindings/` folder is as it was, with a
`NOT-READ.txt` in it; every backup file you made by hand is untouched. A
second launch prints nothing and changes no file.

**Wrong if:** a slot missing; a learned row gone; a backup overwritten.

*(check 33)*

#### L11. Windows reopen where you left them (laptop part)

**Needs:** laptop. The projector part is C3.

**Do:** drag and resize both windows; Esc; launch again. Then ⌘R with a
window moved. Then delete `<home>/windows.json` and launch.

**Right if:** both windows come back where and as large as they were;
`<home>/windows.json` has one `control` entry and one `render` entry;
after ⌘R the moved window stays where you put it; with the file deleted,
the old default placement returns (render window top-left, control
window flush right, both full size — on a small screen they may overlap).

**Wrong if:** a window off every screen or not where it was; no file
after Esc. If a window ever opens out of reach, delete `windows.json`.

*(check 61)*

## The effects

#### L12. The effects by eye

**Needs:** laptop.

**Do:**
1. FX page: from its preset strip load `acid`, then `noita-tripping`,
   then `noita-heavily-tripping`. Untick and tick **Effects** at the top.
   Pull **FX mix** to 0.
2. While the app runs, edit any file in `hyperspace-python/hyperspace/shaders/fx/`
   (change a number) and save; then add a deliberate typo and save; then
   undo your edit (`git checkout` the file).
3. Party show: press F6 (ACID), F7 (MANDALA), F8 (NOITA). Then switch on
   one more effect by hand and press the same F-key.

**Right if:** Effects off is the plain picture; each preset is clearly
its own look; FX mix at 0 is the same as off; a saved edit changes the
picture within a second; the typo keeps the last good picture and shows
the error on the page. F6 lights exactly acid, wobble, deconverge and hue
cycle; F7 plasma, kaleidoscope, fractals and glimmer; F8 trip warp, trip
colour, fractals and double vision; pressing the F-key again switches off
the extra one. A one-line note on the page says a preset load resets the
stack.

**Wrong if:** two presets looking alike; a typo blanking the picture (a
broken shared file falls back to the shipped one and says so on the
LOOKBACK page); a chip left dark or a stray one lit.

**Changes:** your shader edit — put it back with `git checkout`.

*(check 5)*

#### L13. Clicking an effect's name opens it without switching it

**Needs:** laptop.

**Do:**
1. F5 (TRIP), FX page. The effect *chips* are three to a row, each with a
   dot (on) or ring (off) at its left end. Click the **name** of an
   effect that is off.
2. Click the ring at the left end of that chip. Hover the dot.
3. Open Kaleidoscope and drag its **order** slider end to end.
4. Press F6, then F5.

**Right if:** (1) its settings strip opens, the chip gets a white
outline, and it stays off (no red, the picture unchanged). (2) it
switches on: the chip goes red, the ring becomes a filled dot, the open
strip does not change; the hover says "on — click to switch off". (3)
the strip stays Kaleidoscope's while its chip moves along the rows. (4)
the same effect is still open. Only the two longest names are cut short.

**Wrong if:** clicking a name switches the effect; the strip jumps to
another effect.

*(check 59)*

#### L14. An effect that is not running says why

**Needs:** laptop.

**Do:** FX page, open an effect that is off. Then: click **turn on**;
untick **Effects** at the top; tick it back and pull **FX mix** to 0;
put it back and pull the effect's own mix to 0. Also right-click one of
its dimmed sliders.

**Right if:** the strip reads "off — nothing below shows until it is on"
with a **turn on** chip; the sliders under it are dimmed but still move;
the right-click menu opens at full brightness; **turn on** switches it on
and the line and dimming go. With Effects unticked: "the whole stack is
bypassed" with **effects on**. FX mix at 0: "FX mix is at 0". Its own mix
at 0: "its mix is at 0", and that slider is not dimmed. No page
scrolls. Say whether the dimming is too faint or too strong from a step
back.

**Wrong if:** no line, the wrong reason, or the dimmed sliders dead.

*(check 60)*

#### L15. An effect aimed at the faces

**Needs:** laptop; any picture file.

**Do:**
1. F2 (FACES). BITMAP page: load a picture.
2. FX page: click Kaleidoscope's name to open its strip and switch it
   on; at the right end of the strip's title line, after **ONTO**, click
   **faces** (lit: **frame**).
3. Click **screen**, then **per face**.
4. Unload the picture, set the FACES page's pattern to FLAT, aim Plasma
   at the faces too.
5. VIEW page: switch Faces off. Then set Instances to 0.
6. ⌘Z after the **faces** click and after a screen / per face click.

**Right if:** (2) **faces** lights; the outline shape is no longer folded
but the picture inside each face is; the strip reads "faint on the
translucent faces — Brightness lifts them"; the status at the top of the FX page becomes two
rows, `frame …` and `faces Kaleidoscope`, the second ending in two chips
**per face** (lit) and **screen**; Kaleidoscope's chip shows a filled
diamond (an outlined one when off) and its hover says "on the faces".
(3) **screen**: the faces become windows onto one still, upright picture
while the shape turns across it; **per face**: the picture turns with
the shape again. (4) the faces glow and the space between them stays
black. (5) the faces row reads `faces (Faces is off)` in the warning
colour and the strip reads "aimed at the faces, and Faces is off" with a
**faces on** chip; at 0 instances: `faces (no copies to show them)`. (6)
each is one undo step.

**Judge:** whether the diamond can be told from the dot from a step
back. Per face, a subtle effect (Double vision, Deconverge, Trip colour,
Wobble) may be hard to see; strong ones (Hue cycle, Kaleidoscope) should
show. Every face showing the same picture is expected; say if it matters.

**Wrong if:** nothing changes in the faces; the whole frame still folds;
the picture upside down or mirrored.

*(check 91)*

#### L16. Nothing aimed at the faces changes nothing

**Needs:** laptop.

**Do:** press F1 to F8 in turn. Then F5 (TRIP): aim its four effects
(Plasma, Kaleidoscope, Zoom burst, Hue cycle) at the faces; watch the
frame rate in the footer. Press F5 again.

**Right if:** every preset looks as it did before this build; the FX
status is one line with no `frame` prefix; the frame rate does not
visibly drop with the four on the faces; F5 again puts them back on the
frame.

**Wrong if:** any preset looks different; a visible frame-rate drop (say
on which machine).

*(check 92)*

#### L17. The trail carries the faces' effects

**Needs:** laptop; the dream running (LOOKBACK page's status names a
device).

**Do:** F4 (WAKE). Aim Hue cycle at the faces and switch it on.

**Right if:** the trail behind the shape has the faces' cycling colours
and the dream grows out of them; an effect left on `frame` still never
appears in the trail.

**Wrong if:** the trail stays in the old colours.

*(check 93)*

#### L18. Drag an effect to reorder (trackpad)

**Needs:** laptop. The same with a mouse is E1.

**Do:**
1. F5 (TRIP), FX page. Drag the Hue cycle chip **by its name** onto the
   Plasma chip and let go. ⌘Z.
2. Drag a chip onto the right half of the last chip's name.
3. Click a name; press on a name, slip a little and let go on it; click a
   dot. Use the order slider in the strip.

**Right if:** while dragging, the name follows the pointer and a white
bar marks the left edge of the chip underneath; after the drop Hue cycle
is first, the status line starts with it, the picture changes, and its
strip is open; ⌘Z puts the order back in one press ("undid reorder
effects"). (2) the bar shows on that chip's right edge and the effect
lands last. (3) a click or a slipped press only opens; a dot only
switches; the slider still reorders. A drag never changes an effect's
target or switch.

**Known, not a fail:** a 2-pixel gap between a chip's dot and its name
takes no drop; the floating name can be cut at the window's edge.

**Wrong if:** a click starts a drag, or a drag cannot be started (use the
order slider and say so); the wrong effect moved; ⌘Z needed twice.

*(check 94)*

#### L19. No see-through picture

**Needs:** laptop; a white web page full screen behind the render
window.

**Do:**
1. Press **F** (faces on). FACES page: pick a pattern. VIEW page: tick
   and untick **Cut-through**. Do this in a window, then with the OUTPUT
   page's **Fullscreen** on.
2. Quit, add `overlay = true` under `[output]` in the config, launch.
   Press **T**, then tick and untick Cut-through again. Press **T** again.

**Right if:** (1) in a window and fullscreen the picture is solid with
Cut-through on and off: black ground, faces lit, nothing of the desktop
anywhere. (2) after T the window floats over the desktop: with
Cut-through on, the desktop shows through where faces overlap; off, the
faces hide it and only the empty ground is see-through. T again returns
the window. Cut-through only makes a difference in this floating mode.

**Wrong if:** the desktop shows through the faces in window or
fullscreen; no difference at all in the floating mode.

**Changes:** remove the `overlay = true` line afterwards.

*(check 6)*

#### L69. The palette fold

**Needs:** laptop; the APC40 for the last step (leave it out without
one). Plan 24 (the party fixes).

**Do:**
1. Any preset. FX page: the **Palette** chip is the last one. Switch it
   on.
2. Raise its **Mix** slowly to the top.
3. Set the **hue** row to 170 → 230, then both ends to 200. (Since plan
   30 N8 the palette is a slice — hue, sat and val each `from → to` —
   not Centre and Width: C9–C11, L129.)
4. Set **Mode** to gradient.
5. With the APC40: right-click Mix → **Learn desk**, move track fader 2
   (S2), then sweep S2.

**Right if:** (1) nothing changes: the palette starts at mix 0. (2)
still nothing changes: its slice starts as the whole colour wheel.
(3) at 170 → 230 the colours are pulled onto a blue-cyan slice with no
jump anywhere; at 200 → 200 the picture is one colour, its brightness
kept. (4) the picture becomes a greyscale
ramp (the default anchors are greys). (5) the footer says the learn
landed into the preset; S2 then fades the palette in and out once it
reaches the mix.

**Wrong if:** a jump (a seam) in the colours; the picture changes
in step 1 or 2; S2 refused as "invariant" (the track faders are still the
session's: see A28).

*(check 166)*

#### L70. A saved palette, and the palette's controls (on the copy)

**Needs:** laptop; the copy.

**Do:**
1. Copy `tests/fixtures/palettes/fx/sunset.json` into the copy's `fx/`
   folder (`<home>/fx/`, or the shared library's).
2. FX page, open Palette. Look at its controls with Mode on compress, then gradient.
3. From the FX page's preset strip (under its title) load **sunset**.
   Change one anchor colour, save it as your own (**as…**), load another
   effect preset, then yours again.

**Right if:** (2) the page never scrolls; on compress you see Mode, a
"compress into" line, then Hue, Sat and Val (each from → to on one
row); on gradient, Mode, Anchors and one row per anchor colour (hue,
sat, val on one row). (3)
sunset paints dark violet → magenta → orange → cream; yours comes back
with your anchor.

**Wrong if:** a row cut off or the page scrolling; the rows of the other
mode showing; anchors lost after a load.

**Changes:** a palette preset in `fx/`; delete it to undo.

*(check 167)*

## Tempo, the dream and the look-back

#### L20. Tap tempo and the LFO's downbeat

**Needs:** laptop; music (press **K** to play a file chosen on the AUDIO
page) or a metronome app at 140 beats a minute.

**Do:**
1. PRESETS page: load `lfo-breathe` from the preset list. LFO page.
2. Tap **B** four times on the beat; press **⇧B** on the "one".
3. Tap B again a few times. Click the page's trigger chip.

**Right if:** the BPM reads 140 ± 1; the beat light blinks on the beat;
*LFO* 1's little graph shows one smooth wave per bar and the brightness
swells with it, starting from your ⇧B; tapping B again changes the BPM
reading but never makes the swell jump (not even before the first ⇧B);
the trigger chip does the same as ⇧B.

**Wrong if:** the swell jumps on a tap; the BPM more than 1 off; no
swell at all (look at the ROUTING page: is the LFO's row onto Brightness
switched on?).

*(check 7)*

#### L21. Code edits take effect while running

**Needs:** laptop.

**Do:** with the app running, edit `hyperspace-python/hyperspace/lfo.py`:
make the sine wave twice as fast (in `wave()`, change
`return math.sin(2 * math.pi * x)` to `4 * math.pi * x`), save. Then undo the edit. Then save
`hyperspace/params.py` without changing it (`touch` it), and press
**F**, **P**, **L**.

**Right if:** LFO 1's graph doubles its speed within a second; the
SYSTEM page shows "hot reload: watching"; after the touch, F, P and L
still switch faces, points and lines, and SYSTEM shows no error or
"restart" line.

**Wrong if:** no change on save; a switch that stops working.

**Changes:** put `lfo.py` back (`git checkout hyperspace/lfo.py`).

*(check 8)*

#### L22. Tuning the dream, and the rare stall

**Needs:** laptop; music; `[dream] enabled = true` in the config (the
usual setting).

**Do:**
1. Launch normally. LOOKBACK page: the DREAM section's status names a
   device (not "no worker").
2. From the page's preset strip load `default`, then `tracer-only`. Turn
   on the page's **Look-back** switch. Play music.
3. Try layers from the layer menu, **passes**, **strength**, **speed**
   and the colour settings (hue, saturation, tint, tint from). Save two
   or three looks you like as presets in `<home>/dream/` — candidates to
   ship.
4. Watch the frame rate in the footer for ten minutes.
5. Load TRACER from the PRESETS list, then press F4 (WAKE). Hover
   **fade time**, **time apart** and **count** in the ECHOES section.
6. If the screen runs at 120 Hz, switch it to 60 Hz (System Settings →
   Displays → refresh rate) and compare TRACER's trail.

**Right if:** the dream is in its own colours and re-tinted by the
colour settings; the *echoes* are not; **shape hides** keeps the dream
off the shape; the rare stall (about one frame in 300) is one dropped
frame, not more. Each hover says what it does in seconds; on TRACER the
ECHOES note reads "24 × 67 MS · THE TRAIL REACHES 1.60 S", and its trail
is a clear fan of copies behind the turning shape; WAKE's trail reaches
past the faces with the dream painted into it; the trail is the same
length at 60 and 120 Hz.

**Wrong if:** a stall longer than a frame, or every few seconds; no
dream; a trail half as long at 120 Hz; a saved look-back preset of yours
looking different (the old file is kept as `<file>.bak-v2-frames`).

**Judge:** the dream's look (see the last section).

*(check 9)*

#### L23. The LOOKBACK page reads

**Needs:** laptop; the dream running.

**Do:** F4 (WAKE), LOOKBACK page. Read every label aloud. Open the layer
menu under the DREAM status: read it, hover a few lines, and choose
layers from both nets — several shallow, several deep — waiting each
time for the status line to name the layer. Right-click the menu.

**Right if:** three sections — **ECHOES** (brightness, fade time, count,
time apart, then thumbnails; the note reads "24 × 50 MS · THE TRAIL
REACHES 1.20 S"; time apart `50 ms`, fade time `0.60 s`), **DREAM**
(status, at most three lines; the layer menu, closed it reads "conv3_3 ·
small loops, the classic"; brightness, speed, strength, passes, linger,
jitter, scales, hue, saturation, tint, tint from, tint hue, tint sat, and
the tint swatch) and **BOTH** (darken, contrast, shape hides, detail).
The page does not scroll. Each label says what it does without the
hover. The menu lists VGG16's 13 layers, then GoogLeNet's 12, each with a
few words, readable at a pace; a hover says more. Within one net a new
layer shows at once; the first layer of the other net takes a moment.
On the ROUTING page the longer names read "Echo time apart", "Dream
brightness", "Shape hides wake". Right-click on the menu: "not
modulatable".

**Judge:** the words beside each layer were written from offscreen
pictures (`plans/assets/20-fx-dream-looks/dream-layers*.jpg`) and from
how deep the layer is, not from the rig: say which ones do not match
what you see, whether 25 layers is too many to choose from, and whether
the ones marked "slower" are too slow to keep.

**Wrong if:** the page scrolls; a layer does not load; a label is cut.

*(check 95)*

#### L24. Dream speed

**Needs:** laptop; the dream running. (Comparing on the rig is C4.)

**Do:** F4 (WAKE), DREAM section, **speed**. Drag it end to end while
the shape moves.

**Right if:** right is faster: at the fast end the dream keeps up with
the shape, lets go almost at once and is shallower; at the slow end it
trails well behind and grows deeper. The reading is in dream frames:
"≈23 frames" at the slow end, "≈14 frames" at the default, one decimal
under ten ("1.9 frames" at the fast end); slower than about 17 frames
the status says "step clamped".

**Judge:** whether this is the "speed" you meant, and whether one knob
is enough (faster is also shallower, by design).

*(check 96)*

#### L25. The dream's layer cannot be performed

**Needs:** laptop.

**Do:** LOOKBACK page, right-click the layer menu. ROUTING page: add a
route and open its target list. Change the layer from the menu.

**Right if:** the right-click menu says "not modulatable" where other
controls offer "Route a lane here…"; "Dream layer" is not in the target
list; the layer menu, a preset and a learned knob still change it. If a preset of yours
had a route onto the layer: load it — the route is dropped and the footer
says "preset <NAME>: dropped <source> → dream.layer: not modulatable";
the file is not rewritten.

**Wrong if:** a route onto the layer is offered.

*(check 63)*

#### L26. WAKE without the dream still draws

**Needs:** laptop.

**Do:** set `[dream]` `enabled = false` in the config, launch. Party
show, F4 (WAKE). Leave it a minute; press F1–F5 and back to F4.

**Right if:** the picture keeps moving the whole time — the shape turns,
the echoes trail it; a red banner says "WAKE turns the dream on, but
there is no dream worker (…)" until you click **dismiss**; `stall.log`
has that warning and no "stranded target" entry.

**Wrong if:** the picture freezes while the control window carries on.

**Changes:** put `[dream] enabled = true` back.

*(check 46)*

## The shape, the copies and presets

#### L27. Instances down to zero

**Needs:** laptop. (The APC40 and hand parts are A18 and B21.)

**Do:**
1. F1 (TUMBLE), VIEW page: drag **Instances** to the left end. ⌘Z. Set
   it to 1 by hand.
2. F4 (WAKE): take Instances to 0. F5 (TRIP) with Plasma's level up:
   Instances 0.

**Right if:** it reads "0 · nothing drawn" and the picture is black; ⌘Z
brings the count back; at 1 the shape is there. On WAKE the trail fades
out over black rather than cutting off. On TRIP, effects that make their
own picture (Plasma) still show.

**Know:** a route of your own that pushes Instances both ways now blanks
the picture half the time.

**Wrong if:** one copy still drawn at 0; an error or frozen picture.

*(check 62)*

#### L28. Instance layouts

**Needs:** laptop.

**Do:** F3 (FIELD), VIEW page. Under Instances: set **layout** to HEX with
7, then 19 copies, raising the count slowly; RING with 12, then
**motion** ORBIT and RIPPLE; in each layout take the count to 1 and 0;
⌘Z after a layout change. Then HEX + ORBIT with **amp** about 0.35.
Right-click the layout list and a rate cell. Then the house show's F1
and look at a rate cell.

**Right if:** FIELD looks as before; the page does not scroll; one row
under Instances holds layout, motion, and (unless motion is STILL) amp
and rate; the six rotation rates are three rows of two labelled "XY"
etc. HEX 7 is one in the middle and six round it, 19 two rings, and
copies already there do not move as the count rises; RING 12 is one
circle; ORBIT sends a wave round it, RIPPLE makes it breathe; 1 is one
copy in the centre and 0 nothing, in every layout; ⌘Z puts the layout
back; each right-click opens its own menu. On the house show a rate
reads `base → effective` in full. ROUTING and Learn say "Field motion",
"Field amp", "Field rate".

**Judge:** on HEX + ORBIT neighbours overlap — a look or a fault?

**Wrong if:** the grid different from before; copies jumping in HEX.

*(check 97)*

#### L29. Loading a preset resets everything it should

**Needs:** laptop.

**Do:** party show, F5 (TRIP). Tap **B** eight times at about 100 a
minute. F1 (TUMBLE). Then F6 (ACID) → F1, and F8 (NOITA) → F4 (WAKE).

**Right if:** after F1 every effect is off (FX page), the look-back is
back to its default, the ROUTING page shows TUMBLE's rows and none for
effects, the BPM still reads about 100, the sound-band settings have not
changed. F6 → F1 the same; F8 → F4: every effect off and WAKE's
look-back on (24 echoes, fade 0.60 s) with the dream, no extra step.

**Wrong if:** an effect still on; the BPM reset.

*(check 38)*

#### L30. What the show starts on

**Superseded (2026-10-28):** the PRESETS page has no "starts on" picker, no show "factory" tag and no shipped party or house show; the startup preset is read from the file and Home still loads it, but nothing on the panel sets it (L196).

**Needs:** laptop.

**Do:**
1. Launch. PRESETS page: the **STARTS ON / HOME** list → WAKE (no save needed).
2. Quit, launch.
3. **show ▾** → `house`; quit; launch.
4. Open `party` again and set its "starts on" back to TUMBLE.

**Right if:** (1) the party show opened with its name in full, "factory"
beside it, no unsaved dot, on TUMBLE. (2) it comes up on WAKE, with the
desk lit for WAKE and the status line saying so. (3) the house show
opens (the last show opened is remembered).

**Wrong if:** the wrong look or show at launch; the choice not kept.

**Changes:** picking "starts on" writes your own copy of the party show
(`<home>/projects/party.hyp.json`); step 4 puts the choice back.

*(check 40)*

#### L31. Undo a slider drag

**Needs:** laptop.

**Do:**
1. VIEW page: note Brightness, drag it in one move, let go, wait a
   second, ⌘Z (or Ctrl+Z). Then ⌘⇧Z.
2. Drag Brightness, wait, drag Speed, wait, ⌘Z twice.
3. ROUTING page: change a route's depth, ⌘Z.
4. Click in a text field (a macro's label) and press ⌘Z there.
5. Press ⌘Z until nothing is left.
6. Drag a slider, hold still with the button down for a full second,
   drag on.

**Right if:** (1) Brightness returns, nothing else moves, the footer
says "undid Brightness … → …" for about four seconds; ⌘⇧Z redoes it
("redid …"). (2) Speed returns first, then Brightness. (3) the depth
returns. (4) only the text changes. (5) the footer says "nothing to
undo" on every press. (6) this counts as **two** steps — say if it
should be one.

**Wrong if:** nothing returns; two presses needed for one drag; ⌘⇧Z
undoes instead of redoing.

*(check 48)*

#### L32. Undo a preset load

**Needs:** laptop. (Undo of a load from the desk is in A10.)

**Do:** F1 (TUMBLE). Change three things (brightness, the shape, faces
on) so the unsaved dot lights. F5 (TRIP). ⌘Z once. ⌘⇧Z. ⌘Z, then press
F5 by hand and try ⌘⇧Z. Then load a preset from the PRESETS list and ⌘Z.

**Right if:** after the first ⌘Z the look is TUMBLE with your three
changes, the PRESETS page says TUMBLE with its dot lit, F1's button is
lit, ROUTING shows TUMBLE's routes and desk, the footer says "undid load
TRIP"; ⌘⇧Z gives TRIP again, clean; after pressing F5 by hand there is
nothing to redo; a load from the list is one ⌘Z.

**Wrong if:** the look returns but the name still says TRIP; two
presses for one load; routes not back.

*(check 50)*

#### L33. The Home key (laptop part)

**Superseded (2026-10-28):** the "set starts on to — (none)" steps are gone: nothing on the panel sets "starts on" any more, and no show ships with one. Home loads the show's startup preset when its file names one (L196).

**Needs:** laptop. The APC40 part is A12.

**Do:** party show; the PRESETS page's STARTS ON / HOME list reads TUMBLE. F3,
then **fn+←** (Home). ⌘Z. Then set "starts on" to — (none) and press
fn+← twice. Set it back to TUMBLE.

**Right if:** fn+← loads TUMBLE; ⌘Z brings back the earlier look ("undid
home → TUMBLE"); with no "starts on", nothing loads and each press puts "home: this
show names no 'starts on' preset — pick one on the PRESETS page" in the
footer; that line goes when you set it back.

**Wrong if:** fn+← does nothing (say so: the laptop may not send Home
for fn+←, and the key can be changed).

*(check 54)*

#### L71. Lines and points opacity

**Needs:** laptop. Plan 24 (the party fixes).

**Do:** F5 (TRIP); VIEW page: tick **Points** on (TRIP has them off).
Under the Points / Lines / Rotate / Faces ticks, move **Points opacity** from 1 to
0 and back, then **Lines opacity**. Then ROUTING → `+ route`: LFO 1 →
Lines opacity.

**Right if:** at 1 the picture is exactly as before; going down, that
layer fades evenly (the far edges stay fainter than the near ones) and
is gone at 0; the LFO makes the lines pulse.

**Wrong if:** a faint layer left at 0; the other layer fading too.

*(check 154)*

## The control window

#### L34. The key legend is off at launch

**Needs:** laptop. (The APC40's DETAIL button is in A7.)

**Do:** launch. Press **/**, then **/** again. Look at the SYSTEM page's
**Cheat sheet** box. Quit with the legend showing and launch again.

**Right if:** no key legend at launch; the desk drawing sits in the
bottom-left corner; `/` shows the legend with the drawing above it,
already in place on the first frame (no flicker); `/` again hides it and
the drawing drops back; the SYSTEM box follows and its hover says `/`
toggles; after relaunch it is off again.

**Wrong if:** the legend at launch; the drawing missing, jumping or
floating with a gap.

*(check 58)*

#### L35. One Unbind

**Needs:** laptop, APC40 unplugged, `[midi] enabled = true`.

**Do:**
1. F1 (TUMBLE), VIEW page, right-click **Speed**. Choose **Unbind** →
   **both**. Right-click Speed again. ⌘Z.
2. Right-click **Brightness**.
3. Set `[midi] enabled = false`, launch, repeat 1–2.
4. AUDIO page, right-click **Input trim**.

**Right if:** (1) under the setting's name the menu lists "K2 (track knob
2)" and the right hand's height route (if hands are on, "R height pushes
…"), then **Learn desk**, **Learn hand** (left / right, only with hand
tracking on), one **Unbind** with a submenu "desk — K2", "route — R
height", "both", then (hand tracking on) "Gate: none", and "Route a lane
here…". After "both" the two lines and Unbind are gone, the preset's
unsaved dot is lit, and the footer said "unbound view.speed from K2
(track knob 2) and R height …"; ⌘Z brings both back ("undid unbind
view.speed"). (2) lines "K1 (track knob 1)", "B16 (▲) · step +3", "B17 (▼)
· step -3", and Unbind is a single item. (3) the same with MIDI off. (4)
"S8 (track fader 8) · global layer", dim, and no Unbind.

**Wrong if:** no desk line with MIDI off; ⌘Z bringing back only half.

**Changes:** put `[midi] enabled = true` back.

*(check 64)*

#### L36. The right-click menu from labels and meters

**Needs:** laptop, with hand tracking off for one step.

**Do:** CAMERA page: right-click the word ZOOM. VIEW page: right-click
the word BRIGHTNESS above its slider. ANALYZER page: right-click the
fourth meter, choose **Learn desk**, cancel it by clicking the footer's
line. BITMAP page: right-click the file name. HANDS page: right-click
Steadiness.

**Right if:** a label opens the same menu as its slider, at the pointer,
without moving the value; the meter opens the band-select menu without
selecting the band (a left click still selects), and while the Learn is
armed every meter is framed red; the file name offers no Learn, over a
dim "not modulatable"; with hand tracking off there is no "Learn hand"
anywhere; on HANDS settings there is "Learn desk" but never "Learn
hand".

**Known, not a fail:** some labels a page draws itself open nothing (FX
"blend", LOOKBACK's "from", "scene", "path"); on the LFO page the two
nudge chips' menu lists its items twice.

**Wrong if:** nothing opens on a label; a two-finger click not counting
as a right-click (say on which page).

*(check 68)*

#### L37. The big desk drawing (laptop part)

**Needs:** laptop. Holding the real APC40 beside it is A7.

**Do:** F5 (TRIP). Press **H** (or the `big` chip on the desk's header).
Step back two paces. Hover a control. Press `/`. Press H to bring the
panel back.

**Right if:** the panel goes and the desk drawing fills the window; every
lit control carries a name, its short code small in the corner, and dark
controls only the code; the top pad row reads TUMBLE … NOITA with TRIP
green; the track knobs read Brightness, Speed, Instances, Pattern mix,
Field amp, Field rate, Bitmap alpha, Zoom; the device knobs FX mix, Plasma
level, Kaleidoscope segments, Kaleidoscope zoom, Zoom burst amount, Zoom
burst glow, Hue cycle paint, Hue cycle spread; the track faders S1–S8
are dark (TRIP binds none); in the clip-stop row only G6·8 is mapped, to
Save (it lights only while held); names the desk keeps on every preset are
grey, the preset's white. Pad rows 4–5: a filled slot amber at half
strength with its name (on the factory party show G4·1 reads TRACER), an
empty one dark with no label. Nothing overlaps, no scrollbar. The hover
reads like "D3 · fx.kaleido.segments · Kaleidoscope segments · preset
layer", the device's own name, and what a click would do. With `/` the
desk moves beside the legend.

**Expect:** at the standard size most names are 13 px, about a dozen 11
px, and a few cut with "…". Labels beside the open panel need a window about 1200
px wide (drag the panel to the right edge after widening).

**Judge:** which names you can read from two paces.

*(check 69)*

#### L38. The ROUTING filter

**Needs:** laptop. Nobody has typed in this field yet.

**Do:**
1. F7 (MANDALA), ROUTING page. Click the field marked "filter" (left of
   `+ route`) and type `kaleido`. Try B, F, R and number keys while
   typing.
2. Clear it; type `d3`; then `r roll`. On F5 (TRIP), type `lfo 1`.
3. With `kaleido` typed, press F5.
4. With a filter set, press `+ route`. Drag a filtered route's depth.
5. Click the ×. Type a filter again and press Esc, backspace and ⌘Z
   inside the field.

**Right if:** (1) only the kaleidoscope's lines remain (two right-hand
routes, R depth and R roll, and desk lines D3 and D4); MACROS and
SESSION say "no row matches"; the count reads "n of m rows" in red; a ×
appears; typed keys do nothing else. (2) one desk line; that route;
LFO 1's route (a route from LFO 2 would also show — say if that
matters). (3) the filter stays, now over TRIP's rows. (4) the new route
may not show — the red count is the only sign (say if that is a trap); a
line you are dragging stays put until you let go. (5) every row returns;
say what Esc, backspace and ⌘Z did.

**Wrong if:** the × deletes a different row than the one shown; the page
scrolls; a typed key also fires its shortcut.

*(check 71)*

## On the copy: tidying presets

Run L39–L42 in a terminal where `HYPERSPACE_HOME` points at the copy.

#### L39. Hide presets from the list

**Superseded (2026-10-28):** there is no hidden list, no `hidden.json` and no "show hidden": × puts any preset in the trash (L196).

**Needs:** the copy.

**Do:** PRESETS page → click the preset name → the list. Click × on
`legacy6`, on `hands-*` presets you do not want, and on one house mood.
Click **show hidden**. Then × one of **your own** presets that sits on a
slot, and press that slot.

**Right if:** every row has ×, your own (white) also **rename**; each
goes; the footer says "hidden legacy6 — show hidden in the list brings
it back" (or "… — F3 still loads it" for one on a slot); the list ends
"show hidden (n)"; `<home>/hidden.json` lists them; "show hidden" shows
them struck through with **unhide**; an F-key or pad naming a hidden
preset still loads it. Your own preset goes to the trash: the footer
says in the warning colour "<name> is in the trash — F6 still names it
…", its slot button turns the warning colour, and pressing it says "F6:
no preset '<name>'".

**Wrong if:** a hidden preset will not load from its slot.

**Changes:** `<home>/hidden.json`; the trashed preset is restored in L41.

*(check 86)*

#### L40. Rename a preset

**Superseded (2026-10-28):** there are no factory presets: rename works on every preset, and the list has no dim rows (L196).

**Needs:** the copy; one of your presets on a slot in two of your shows.

**Do:** in the list: **rename** → type a name → Enter. Open the other
show. Rename it to a name another preset has. Look for rename on a
factory preset. Rename the loaded preset while it has an unsaved
change. Press ⌘Z.

**Right if:** the footer says "renamed TRIP 3 → SUNRISE (2 shows
updated)" (your names); the list, slot and "starts on" show the new
name at once, in both shows; `<home>/trash/presets` and
`<home>/trash/projects` hold the old files; a taken name is refused
("… that name is taken — pick another"); factory presets have no rename;
the unsaved dot stays lit; ⌘Z does not undo a rename (rename it back by
hand).

**Wrong if:** a slot saying "no preset" after a rename.

*(check 87)*

#### L41. The trash

**Needs:** the copy.

**Do:**
1. Load a preset of yours (or make one with **as…**: "CHECK 53"). Change
   the brightness, press **save**. Press save again with no change. Then
   open the list and × it. `ls <home>/trash/presets/`.
2. The list → **trash (n) ▸**. Restore the preset from L39.
3. Save over one preset twice, then restore the older copy.
4. Click **empty trash…** once and wait 4 seconds. Click it, then
   something else. Click it twice.

**Right if:** (1) two files `check-53.<date>-<time>.json` — the look
before the save and the one deleted; no third file for the save with no
change; "more" lists no "trash" strip. (2) a second list, "trash · n
files", newest first, each with folder, name, time and **restore**,
scrolling past twelve rows; restoring says "restored <name>", it is back
in the list and its slot loads. (3) "restored as TRIP 4 — TRIP 3 is
taken" (the next free name), the newer one untouched. (4) one click
reads "delete n files for good? — click again" in the warning colour and
after 4 s goes back with nothing deleted; clicking elsewhere disarms it;
two clicks: "trash: n files deleted for good", the trash line gone,
`<home>/trash` empty.

**Know:** emptying the trash is the only action in the app that deletes
with no copy kept.

**Wrong if:** a restore replacing a preset (the backup has it); one
click emptying the trash.

*(check 53, 88)*

#### L42. The unsaved dot from a step back

**Superseded (2026-10-28):** there is no factory preset to load and no dim row or "save copy": use one of your own presets; the dot and the save chip are as described (L196).

**Needs:** the copy.

**Do:** load a factory preset on a slot that you have no copy of (dim in
the list). Stand at arm's length, move a slider. Press the save chip.

**Right if:** you can see it is unsaved without leaning in: the save
chip solid red, a red disc by the name, a small white disc on the slot
button; the chip reads **save copy** and there is no reset; pressing it
makes it read "save", the dot goes, the list shows the preset once,
white (yours). ROUTING's header shows the same disc. A preset of yours
reads "save".

**Known, not a fail:** under "more", a module strip's save chip overlaps
the end of its name.

*(check 89)*

#### L43. The shared library folder (two Macs)

**Needs:** this Mac and a second one, both running this build, and a
folder in a cloud drive shared between you (set up as in
[`SETUP.md`](SETUP.md), "Share presets with someone"). Try the missing
folder (step 4) on a copy: `HYPERSPACE_HOME` pointed at a scratch
folder. **Both Macs must be on the same build** — since plans 28 and 30
a preset can carry modifiers, box positions and picture wiring that an
older build ignores or refuses, and an older build that saves it throws
them away (L122).

**Do:**
1. Both Macs pointed at the same folder (`[library] path`). On Mac A,
   save a new preset (**as…**). Watch Mac B's PRESETS list.
2. On Mac B, load that preset. On Mac A, change it and save it again.
3. Check `config.toml`, `bindings.json` and `windows.json` in each home:
   their dates do not change on a save, and none of them is in the
   shared folder.
4. On the scratch home, set `path` to a folder that does not exist and
   launch. Look at the footer and the SYSTEM page, then try a save.
5. Take Mac B offline. Save the same preset on both Macs. Bring B back
   online and wait for the sync.

**Right if:** (1) the preset appears on B within a couple of seconds of
the sync, no restart. (2) B re-applies it, as a hand edit of the file
does. (3) untouched and not shared. (4) a warning says the shared library
was not found; the SYSTEM page's library line is red and says "NOT
FOUND, saves are off"; the save says "not saved"; no folder is created.
(5) both entries show in the list (one under a name like
"hi-frek (… conflicted copy …)"); load both, keep one, delete the other.

**Wrong if:** a preset that never arrives (check the cloud client:
iCloud "Keep Downloaded", Dropbox "Available offline"); a machine file in
the shared folder; a folder created at step 4; only one entry at step 5.

**Changes:** the shared folder gets your test presets; delete them after.

*(checks 139–143)*

## Outputs and hands without the camera

#### L44. One output is as it was

**Needs:** laptop; the config with no `[[output.screens]]` list. Run
before any config change for Part 2 (d). Without the camera, use
recorded fake hands: `uv run python tools/hands_tape.py synth
/tmp/hands.json`, then in the config under `[hands]` set `enabled =
true` and `tape = "/tmp/hands.json"`.

**Do:** launch. OUTPUT page. HANDS page: tick **Ghost hands**; press F5
(TRIP).

**Right if:** two windows as before, the render window where it was; the
OUTPUT page shows under **Master dim** one block "1" with **scene** and
**hands** ticked and **through effects** unticked, no dim of its own,
and a "shows: scene" line ("shows: scene + hands over the effects" with
a ghost hand showing); Screen, Fullscreen and the overlay rows follow as
before; the picture is as on earlier builds; on TRIP the ghost hands are
clean over a warped shape.

**Wrong if:** any difference in the picture; a dim row of its own.

**Changes:** remove the `tape` line afterwards.

*(check 99)*

#### L45. The HANDS page explains a bad setting

**Needs:** laptop. (The camera part is B20.)

**Do:** in the config under `[hands]` set `tape = "/tmp/no-such-tape.json"`;
launch.

**Right if:** the SYSTEM page lists a note starting `hands: `, and the
HANDS page shows it in the warning colour where it used to say "tracker
off".

**Changes:** remove the `tape` line.

*(check 100)*

## The device list (on the copy)

Plan 27 (the device registry). Every device — the desk, the pad, the
hands, the bridge, a phone — is one entry in the config file's device
list, and one line on the SYSTEM page. These entries change the config
file **while the app runs**: the app reads the device list again about
half a second after you save it. The blocks to paste are in
`hyperspace-python/docs/plans/27-device-registry.md`, "The block to
paste".

#### L72. Every device on the SYSTEM page

**Needs:** laptop; the copy; the APC40 and the pad plugged in if you
have them.

**Do:**
1. Launch on the copy as it is. SYSTEM page → **devices**.
2. Quit. In `<home>/config.toml` replace the `[midi]`, `[gamepad]`,
   `[hands]` and `[bridge]` sections with the "today's rig" block
   (if the hands are on, write `enabled = true` on the `leap` entry and
   move the `[hands]` lines under it). Launch again.

**Right if:** (1) one line per device: `pad · gamepad …`, `apc40 · midi
· connected · 137 sources …` (or `lost` with no desk), `leap · hands …`,
`bridge · bridge · off …`; one grey note per old section the file has
("config: [midi] is now a [[devices]] entry …"); everything works as
before. (2) the same lines and no note.

**Wrong if:** a device missing; a note for a section the file does not
have; a note after the paste (an old section left in the file).

**Changes:** the config file; keep the copy of it you started from.

*(check 168)*

#### L73. Change the device list while the app runs

**Needs:** laptop; the copy, with the list from L72.

**Do:**
1. With the app running, set the `bridge` entry's `enabled = true`;
   save.
2. Write `role = "a:b"` on any entry; save. Then put it back; save.
3. Add a second hands device: `[[devices]]`, `role = "leap2"`, `kind =
   "hands"`; save. Then add a second pad: `role = "pad2"`, `kind =
   "gamepad"`; save. Then set the `leap` entry's `enabled = false`; save.

**Right if:** (1) within a second "devices: bridge changed — reopened"
on SYSTEM and the bridge line no longer says `off`. (2) one note
"config: [[devices]] not applied — … — the old list stands" and nothing
else changes; put back, the list is followed again. (3) `leap2 · hands ·
error: feeds 'hand', which leap already feeds — not opened`, the hands
unchanged; `pad2 · gamepad · lost` (or `connected · … · glfw 1` with a
second pad in), no error — two pads may run at once since plan 27 B6
(F6); with `leap` off, `leap2` takes over.

**Wrong if:** nothing happens after a save; a window moves or the app
restarts; both hands devices `connected` at once; `pad2` an `error:` line.

**Changes:** put the list back as it was.

*(checks 173, 174)*

#### L74. A broken device does not stop the show

**Needs:** laptop; the copy; a text editor on the code. The APC40
helps.

**Do:** with the app running, open `hyperspace-python/hyperspace/midi.py`
and add `raise RuntimeError("x")` as the first line inside `def
poll(self)` of `MidiIO`; save. Watch for a few seconds. Remove the line;
save.

**Right if:** a message `midi: RuntimeError: x` appears and the apc40
line reads `error: RuntimeError: x` in the warning colour, while the
picture and everything else go on; once the line is removed the message
clears and the line reads `connected` (or `lost`) again.

**Wrong if:** the window freezes; the other devices stop.

**Changes:** none once the line is removed (check `git diff`).

*(check 170)*

#### L75. The pages offer what the rig lists

**Needs:** laptop; the copy.

**Do:** ROUTING page: open a row's source list. Right-click any slider
(Brightness) and read its menu.

**Right if:** the source list has the sound bands, then LFO 1–4, then
the pad's sticks, the hands and `ext` lanes, in the order the device
list gives them. The menu has Learn desk, Learn hand (with a tracker on)
and Learn pad (with a pad connected), as before.

**Wrong if:** a device's sources missing from the list.

*(check 178)*

#### L76. A recorded point cloud plays

**Needs:** laptop; the copy.

**Do:** copy `hyperspace-python/tests/fixtures/clouds/knot.npz` into
`<home>/clouds/` and add the recorded-cloud block to the device list;
save. Watch the SYSTEM page. Then rename the file, add `loop = false`
to the entry and save; rename the file back.

**Right if:** `scan · cloud · connected · 1 source · knot.npz · frame
n/16 · … points · 12 fps`, the frame counting through 16 at 12 frames a
second (one loop about every 1⅓ seconds) and starting over; the picture
shows the knot as dots threaded through the shape (L84 is the drawing's
own entry).
Renamed: `error: FileNotFoundError …`; back: `connected` within about
10 seconds, the frame stopping at 16/16.

**Wrong if:** the frame number races with the app's frame rate.

**Changes:** remove the entry and the file.

*(check 190)*

## With FL Studio (no hardware)

These need FL Studio installed and the Mac's built-in virtual MIDI
cable: open Audio MIDI Setup → MIDI Studio → IAC Driver, tick "Device is
online", with one bus.

#### L46. Sending to FL Studio

**Needs:** FL Studio; the *IAC bus*; music playing in the app.

**Do:** in the config set `[bridge]` `enabled = true` and `out = "IAC"`.
Launch, SYSTEM page. In FL Studio, take IAC as input and put a Fruity
Formula Controller or Peak Controller on pitch bend, channel 1.

**Right if:** SYSTEM's bridge line (under **devices**) reads `bridge ·
bridge · connected · 16 sources · 1 sink ·` the port, `pitch, 16 lanes`
and a rising `sent` count; the FL controller moves with the lowest sound
band. With plan 27, the first launch with the bridge on also says
"bindings: [bridge] send is now sink rows in bindings.json …" (L78).

**Wrong if:** the bridge line says `lost` or `error` (check the IAC
name); no bridge line.

**Changes:** set `[bridge] enabled = false` afterwards.

*(check 27)*

#### L47. Receiving from FL Studio

**Needs:** as L46, plus `[bridge]` `in = "IAC"` (a second IAC bus, or
FL's own MIDI out).

**Do:** ROUTING page: add a route from `ext:0` to Brightness, **push**,
depth 0.5. Send pitch bend on channel 1 from FL. Then stop FL.

**Right if:** brightness follows the pitch wheel; when FL stops,
brightness returns to its setting within a frame.

**Wrong if:** nothing moves (check the encoding on both ends, and that the
row is switched on).

**Changes:** delete the route; undo the `[bridge]` lines.

*(check 28)*

#### L77. A setting sent to FL Studio

**Needs:** as L46 (FL Studio, or MIDI Monitor, listening to the IAC
bus); the copy.

**Do:** right-click Brightness → **Learn sink** → `bridge:6 · pitch
ch7`. Make brightness move by itself: ROUTING → `+ route`, LFO 1 →
Brightness. Watch channel 7 in FL. Load another preset.

**Right if:** the footer says "sent view.bright → bridge:6 (into
bindings.json)"; channel 7's pitch bend follows the brightness as it
moves with the LFO — not just the slider — and nothing is sent while it
holds still; the other preset leaves the sending in place.

**Wrong if:** FL follows only the slider; nothing on channel 7.

**Changes:** ROUTING → sinks: × the row.

*(check 181)*

#### L78. The bridge's old "send" list becomes rows, once

**Needs:** as L46; a copy whose bridge has never been switched on.

**Do:**
1. In the config set the bridge on with `send = ["lane:*",
   "param:view.bright"]` (on `[bridge]`, or on the bridge entry); launch.
2. Quit and launch again.
3. ROUTING → **sinks**: × every row. Change anything in the config file,
   save; quit and launch again.

**Right if:** (1) one note "bindings: [bridge] send is now sink rows in
bindings.json (lane:* → bridge:0, param:view.bright → bridge:6) …"; the
sinks section lists "every lane → bridge:0" and "param view.bright →
bridge:6"; SYSTEM: `bridge · bridge · connected · 16 sources · 2 sinks
…`; FL gets the lanes as before and brightness on channel 7; the source
list on ROUTING has `ext ext 0` … `ext ext 15`. (2) no note. (3) no row
comes back.

**Judge:** an entry after `lane:*` always lands on channel 7 (six sound
bands), whatever your band count: if a mapping in FL used another
channel, move it once.

**Wrong if:** the note on every launch; the rows come back.

*(check 182)*

#### L79. Sending a setting never asks a question

**Needs:** as L77.

**Do:** put an LFO on Brightness (ROUTING → `+ route`). Right-click
Brightness → **Learn sink** → any port. Then right-click Speed →
**Learn sink** → the same port. Right-click Speed → **Unbind**.

**Right if:** no Replace / Keep question either time; the LFO still
moves brightness; the second time the footer adds "…; param:view.bright
let go"; Speed's menu lists the sending dimmed, and Unbind leaves it;
the preset's unsaved dot stays off.

**Wrong if:** a Replace / Keep question; the unsaved dot lights.

**Changes:** × the row on ROUTING → sinks.

*(check 183)*

#### L80. The hands' own port, now a device

**Needs:** FL Studio; the IAC bus; the copy; the hand camera, or a
recorded hand tape (`[hands] tape`).

**Do:** hands on with `out = "IAC"`. Launch, raise the right hand. Take
the IAC bus offline in Audio MIDI Setup for a few seconds, then back.

**Right if:** SYSTEM shows the leap line and under it `hands-daw ·
midi-out · connected · 0 sources · 0 sinks · IAC …  · leap's DAW out ·
cc …`; FL's knobs follow the hands; offline the line says `lost`, and
within about 2 seconds of the bus coming back it says `connected` and
FL's knobs jump to where the hands are. FL lists no second "Hyperspace
Hands" port.

**Wrong if:** no messages; no jump after the reconnect; a second
"Hyperspace Hands".

**Changes:** put `out` back.

*(check 184)*

#### L81. The hands' port in the device list

**Needs:** the copy, with a device list and the hands on.

**Do:** put `out = "IAC"` on the `leap` entry; launch. Then remove it
and add an entry `role = "daw"`, `kind = "midi-out"`, `port = "IAC"`,
`carries = "leap"`; launch.

**Right if:** first: one note "config: [hands] out is now a [[devices]]
entry (role = 'hands-daw', …)" and a `hands-daw` line naming the bus.
Second: no `hands-daw` line; the `daw` line carries the hands.

**Wrong if:** two lines both carrying the hands.

**Changes:** put the entries back.

*(check 185)*

## The shapes in four dimensions

Seven shapes — Heart, Star, Rose, Torus, Trefoil knot, Starfruit, Möbius
strip — used to go flat, like a sheet of paper seen edge-on, whenever the
bass turned them "through the fourth dimension". Now six of them have real
4D depth, and the Heart stays an ordinary 3D shape that the bass turns in
3D. There is a new 26th shape, the Klein bottle. Pick a shape in the
VIEW page's **Shape** list (or with ← / →). The six round keys on the
VIEW page (XY, XZ, YZ, XW, YW, ZW) switch each turning direction on and
off; XW, YW and ZW are the "fourth dimension" ones, driven by the bass.

#### L48. A 3D shape ignores the W planes; a 4D shape turns through them

**Needs:** laptop.

**Do:** F1 (TUMBLE). On the VIEW page switch off every round key but
**XW**. Step through Star, Rose, Torus, Trefoil knot, Starfruit, Möbius
strip and Klein bottle (all 3D since plan 28). Then look at the Clifford
torus (shape 18) and the Tesseract. Do the same with only **YW** on,
then only **ZW**, then all six with music.

**Right if:** with only W keys on, every 3D shape holds still and its W
keys are dimmed (hover one: "does nothing now: a 3D shape has no w"); the
header line reads "3D · …"; the 4D shapes turn through w. With all six
on, a 3D shape turns in XY, XZ and YZ only. The Klein bottle crosses
itself where the neck passes through the body, as it must in 3D.

**Judge:** whether the 3D shapes are lively enough on the upper bands
alone.

**Wrong if:** a 3D shape moves with only W keys on; a seam opens up.

*(check 113)*

#### L49. The Heart turns with the music, in 3D

**Needs:** laptop, music with deep bass.

**Do:** pick the Heart. With only XW on, then only YW, then only ZW,
watch it. Then all keys on, music playing. Switch to the Tesseract and
back.

**Right if:** with only W keys on it holds still (plan 28: a 3D shape has
no w); with all keys on it turns with the upper bands; its lines are as
bright, and its near edges as thick and bright, as the Tesseract's.

**Judge:** whether the Heart still reads as moved by the music.

**Wrong if:** it moves with only W keys on; it looks dim and flat next
to the Tesseract.

*(check 114)*

#### L50. The Star, Starfruit, Rose and Möbius strip by eye

**Needs:** laptop.

**Do:** FACES on with a pattern. Star, Starfruit, Rose, Möbius strip:
all keys off, then turning (XY, XZ, YZ — they are 3D since plan 28).

**Right if:** the Star's two star-shaped ends show the pattern whole,
with no hole or tear; the Starfruit's five ridges are recognisable; the Rose is
still a delicate flower (it is a little deeper than before); the Möbius
strip is a little wider than before and not too wide; the Rose's centre
and the Möbius strip's join stay closed.

**Judge:** each of these four looks: keep, or say what to change.

**Wrong if:** a torn or folded star end; a gap at the Rose's centre or
the Möbius strip's join.

*(check 115)*

#### L51. The Klein bottle

**Needs:** laptop.

**Do:** pick the Klein bottle (shape 26, after the Möbius strip). All
keys off, then XY, XZ and YZ one at a time, slowly (Speed down). Faces
on and off.

**Right if:** at rest it looks like a bottle whose neck curls over and
comes back into its body, passing through its side (a Klein bottle in
3D must cross itself; plan 28 took out the lift that kept them apart in
w); no gap where the surface joins itself; the neck has enough lines.

**Judge:** whether it reads as a bottle — the build's own look said it
reads more like a curled horn or a loop. Say what you see.

**Wrong if:** a gap or a sliver at the join.

*(check 116)*

#### L52. Stepping to the Klein bottle (keys)

**Needs:** laptop; the copy for the save. (The desk part is A19.)

**Do:** VIEW page, Möbius strip (25). Press →, → again, then ←. If you have
the gamepad, RB and LB do the same. On the copy: save a preset on the Klein bottle, load
another, load it back.

**Right if:** → reaches the Klein bottle and stays there; the page
reads "KLEIN BOTTLE" and "576V 1152E · χ=0 · one side", with the χ drawn
as a letter, not a box; the saved preset comes back on the Klein bottle.

**Wrong if:** it stops at the Möbius strip; it jumps back to the 5-cell;
a box instead of χ.

*(check 117)*

#### L53. Presets that show a changed shape

**Needs:** laptop, the copy, music.

**Do:** load the factory presets `plasma-heart` (the Heart),
`spiral-silk` (the Trefoil knot) and `inverse-halo` (the Starfruit), then
your own `hi-frek-variation-1` and `light-realm-variation-1` (the Möbius
strip), from your library.

**Right if:** each still does what it was made for.

**Judge:** any that now looks wrong: re-tune the preset, or change that
shape back.

*(check 118)*

#### L54. The turntable pictures

**Needs:** laptop; no app.

**Do:** open the folder `hyperspace-python/docs/plans/assets/22-flat-shapes/`.
Each picture is one shape turning a full circle in XW, YW and ZW (three
rows of twelve), with a number under each frame: how much depth it
keeps, red when too little. Look at `before-18-heart.png` to
`before-24-mobius-strip.png`, then `after-18-heart.png` to
`after-25-klein-bottle.png`.

**Right if:** every "before" picture of those seven has red numbers at
the quarter turns; no "after" picture has any red; the after pictures
look like the shapes you know.

**Judge:** which shape looks worst.

*(check 119)*

## The face patterns

The *faces* of a shape can be filled with a moving *pattern*. There are
seventeen, and each reads eight *inputs* — SCALE, GLOW, WARP, SPEED,
COLOUR, SHARP, HUE, SPREAD — that mean the same on every pattern: 1 is
the pattern as designed, 0 and 2.6 the two extremes. The music moves
the first six (the low bands the first ones); HUE and SPREAD are left
for a slow oscillator (an *LFO*) or a knob. The **FACES** page shows
every pattern as a small moving picture and says, for each input, what
it does on the pattern on show and what is moving it. Run L55 and L56
first: they are the two things the automated tests cannot check on your
Mac.

#### L55. The FACES page fits on the Mac

**Needs:** laptop, the copy.

**Do:** open FACES. Click KALEIDO, then FLAT, then EMBER. Then the worst
case: on each of the eight inputs click its **+ …** offer (+ SUB … + LFO
2) so every input is driven; on ROUTING, give a macro a long name such
as "a long macro name" and set it to scale one of those routes; untick
**Faces**. Then tick Faces again and click FLAT and CAUSTIC: a
pattern's own description running long is the tallest case.

**Right if:** the page never needs scrolling; all seventeen pattern
buttons fit, with their names inside them; every input's two lines are
on screen, long text cut short with "…" rather than running off the
edge.

**Know:** the automated test for this ran on another computer whose
letters are a different size, so it proves nothing here. The small red
dot on the preset row's ▶ button overlaps it; that is known.

**Wrong if:** a scroll bar; an input's row off the bottom; a name
sticking out of its button. Say how much is missing.

**Changes:** ⌘Z (or reload the preset) takes the routes back.

*(check 120)*

#### L56. Every pattern draws on the Mac

**Needs:** laptop.

**Do:** faces on, FACES page: click each of the seventeen pattern
buttons in turn. Then press F5 (TRIP).

**Right if:** every pattern draws; no line starting "GLSL:" appears on
FACES or on the SYSTEM page; every button's little picture shows
something.

**Know:** the patterns were only ever compiled by Linux graphics
software, never by the Mac's own.

**Wrong if:** a "GLSL:" line — copy it exactly (it says which line of
`patterns.glsl` the Mac refused).

*(check 121)*

#### L57. Find a look, as a first-time user

**Needs:** laptop, music, and someone who has never seen the app.

**Do:** ask them to open FACES and find a look they like, then to say
what each of the eight inputs does on that pattern and what moves it.
Don't help. Note where they get stuck.

**Right if:** they get there without opening a code file, and can
explain the inputs and what drives them.

**Judge:** which words on the page confused them.

*(check 125)*

#### L58. The little pictures on the pattern buttons

**Needs:** laptop, music.

**Do:** shape 600-cell, faces on. Note the frame rate in the footer with
FACES open, then on VIEW. Back on FACES, drag SCALE and COLOUR. Then,
with FACES still open, break `patterns.glsl` (type a made-up word into a
line), save, wait, undo the change and save again.

**Right if:** each button shows a small moving picture of its pattern,
and the pictures change as you drag the inputs; the frame rate is about
the same on both pages; while the file is broken nothing stutters and
the pictures keep their last good look, and the fix comes back.

**Judge:** whether the pictures are big enough to tell apart.

**Wrong if:** blank buttons; the frame rate drops only while FACES is
open.

*(check 126)*

#### L59. "+ SUB": route a band from the page

**Needs:** laptop, the copy.

**Do:** load a house preset (PRESETS, show `house`). On FACES, the HUE
input says **+ LFO 1** at its right: click it. Then ⌘Z. Then click the
words "SUB pushes +0.35" on the SCALE input.

**Right if:** **+ LFO 1** turns into "LFO 1 pushes +0.35" and you stay on
FACES; ⌘Z takes it back; clicking the SUB words opens ROUTING showing
just that input's routes.

**Wrong if:** the page jumps to ROUTING when you click "+ LFO 1"; ⌘Z
does nothing.

*(check 127)*

#### L60. "all neutral" in one step

**Needs:** laptop.

**Do:** drag four inputs away from 1, pausing a second between each.
Click **all neutral**, then ⌘Z once. Then click the **1** beside one
input.

**Right if:** all neutral puts every input at 1.00 at once; one ⌘Z
brings all four back; **1** resets only its own input.

**Wrong if:** ⌘Z brings back one input at a time.

*(check 128)*

#### L61. One set of routes on every pattern

**Needs:** laptop, music with a clear kick, snare and hi-hats.

**Do:** load a house preset. On FACES click › to step through every
pattern, a few bars on each.

**Right if:** on every pattern the deep bass makes it bigger, the kick
makes it flash, the low mids bend it, the mids keep it moving, the snare
brings colour and the hi-hats sharpen it; quiet passages still move
it and loud ones never turn it solid white or black.

**Judge:** which pattern answers the music worst.

**Wrong if:** an input does something different on one pattern.

*(check 122)*

#### L62. No jumps over a long set

**Needs:** laptop, music, ten minutes or more.

**Do:** house preset, RINGS, then PLASMA; let it run and watch when the
music changes. If the app has been running an hour or more, also look
at PULSE and EMBER.

**Right if:** the pattern speeds up and slows down with the music, but
never snaps to a different place; after an hour PULSE's small dots still
twinkle and EMBER still drifts (EMBER is known to stop after about
12 hours).

**Wrong if:** a sudden snap.

*(check 123)*

#### L63. Colour turning, faces apart, on the 120-cell

**Needs:** laptop.

**Do:** shape 120-cell, faces on, CELLS. On the LFO page give LFO 1 a
slow rate and some depth; on FACES click **+ LFO 1** on HUE. Drag SPREAD
from 0 to 2.6.

**Right if:** the colours turn slowly round the colour wheel while the
pattern's shapes stay the same; SPREAD at 0 makes every face play the
same, at 2.6 each face its own way.

**Wrong if:** the shapes change as the colour turns; faces differ at
SPREAD 0.

*(check 124)*

#### L64. MARBLE's frame rate

**Needs:** laptop.

**Do:** shape 600-cell, faces on. Note the footer's frame rate on FLAT,
CELLS and MARBLE; then MARBLE with Instances at 7.

**Right if:** MARBLE keeps the screen's frame rate (or say by how much it
drops, against CELLS).

**Know:** MARBLE is the most expensive pattern — about four times FLAT on
the build's computer, a third more than CELLS.

*(check 130)*

#### L65. KALEIDO and TRUCHET as art

**Needs:** laptop, music.

**Do:** KALEIDO and TRUCHET on the tesseract, the 24-cell and the
Clifford torus, faces' mix full.

**Judge:** keep, change or drop each — KALEIDO's flat bright colours in
six mirrored wedges, TRUCHET's maze with a current along it. KALEIDO is
always six-sided, whatever shape a face is.

*(check 131)*

#### L66. The factory presets with music

**Superseded (2026-10-28):** no preset ships: the house and party presets live in `tests/corpus/` only. Run this with your own presets with faces on.

**Needs:** laptop, music with quiet and loud passages.

**Do:** house presets hex-engine, ember-orbit and spiral-silk; the party
show's FACES (F2) and TRIP (F5); then one of your own presets with faces
on.

**Right if:** quiet music visibly moves the faces; loud music stays
readable, nothing stuck all white or all black (EMBER not black, SPIRAL
not washed out).

**Judge:** whether to re-save your own presets: sixteen of yours still
push the patterns three times harder, as all presets used to.

*(check 132)*

#### L67. `legacy6` in silence

**Needs:** laptop, music.

**Do:** PRESETS: load `legacy6`; faces on, pick RINGS. Listen to
nothing, then play music.

**Right if:** in silence the shape stands still and the pattern looks
as designed; with music the shape turns and the pattern moves.

**Judge:** whether a still shape in silence is right for this preset (it
copies the original web app's behaviour).

**Wrong if:** a small, dim, grey, frozen pattern in silence.

*(check 137)*

#### L68. WARP at full on HEX

**Needs:** laptop.

**Do:** HEX, then PLAID and KALEIDO: drag WARP from 0 to 2.6.

**Right if:** from 0 to 1 the lines stay straight; above 1 they bend;
at 2.6 HEX is still a honeycomb.

**Judge:** whether 2.6 is too strong.

*(check 138)*

---

## The render graph (on the copy)

Plan 26 (the render graph). The picture is now built from parts — the
shape, the hands, a point cloud, the effects, the trail — wired
together, and the shape and the ghost hands share one camera, so the
hands can be drawn inside the shape. A preset can say how its picture
is wired, in its file. **No factory preset uses any of it**: these
entries copy a test preset into the copy's library. Before any of them,
open `~/Hyperspace-try/config.toml` and, if it has a `[library] path`
line, delete that line (on the copy only), so the presets you copy in
go to the copy's own `presets` folder and never to the shared Drive
folder. A preset file in `<home>/presets/` shows in the PRESETS list by
its file name.

The test preset is `hyperspace-python/tests/fixtures/presets/hands-lines.json`.
Some entries use a variant: copy that file into `<home>/presets/` under
the new name, open the copy in a text editor and replace the part that
starts `"graph": {"nodes": [` and ends `]},` with the line given:

- `hands-solid.json`: `"graph": {"nodes": [{"kind": "hands", "into":
  "scene"}, {"kind": "history", "holds": "scene+hands"}]},`
- `hands-depth.json`: `"graph": {"nodes": [{"kind": "hands", "laid":
  "depth"}]},`
- `two-acids.json`: `"graph": {"nodes": [{"kind": "effect", "file":
  "acid", "instance": 2}]},` — and after `"fx.acid.on": true,` add
  `"fx.acid.2.on": true, "fx.acid.2.twist": 0.3,`
- `two-hands.json`: `"graph": {"nodes": [{"kind": "hands", "into":
  "scene"}, {"kind": "hands", "instance": 2}]},`

Entries marked "(tape)" need hands: the hand camera, or recorded fake
hands as in L44 (`uv run python tools/hands_tape.py synth
/tmp/hands.json`, then `enabled = true` and `tape = "/tmp/hands.json"`
on the hands entry), with **Ghost hands** ticked on the HANDS page.

#### L82. The golden pictures match (the gate Mac)

**Needs:** the Mac the automated tests run on (its graphics chip is
"Apple M3 Max"); a terminal.

**Do:** in `hyperspace-python/`, run `uv run python tools/golden_frames.py`
(it takes under a minute; it uses a throwaway home folder, never yours). Then
open a few pictures in `tests/golden/frames/png/`.

**Right if:** it ends "all 757 frames match their goldens (Apple M3 Max,
4.1 Metal - 90.5)" (after a macOS update it may add a note naming two
versions); the pictures show the presets, some with two made-up hands
(the left open, the right a fist).

**Wrong if:** a list of `MOVED …` lines and a picture sheet under
`docs/plans/assets/26-render-graph/`: write down the names, then delete
the sheet.

*(check 191)*

#### L83. Every preset beside its golden picture

**Needs:** the gate Mac; no music playing.

**Do:** in `hyperspace-python/`, list each preset's golden picture:
`uv run python -c "import json; [print(g['preset'], 'tests/golden/frames/' + g['png']) for g in json.load(open('tests/golden/frames/frames.json'))['goldens'] if g['hands'] == 'absent' and g['state'] == 'solo']"`.
Launch the app. Load each of the 23 presets in the PRESETS list in turn,
its picture open beside the render window.

**Right if:** each looks like its picture — the shape's size and place,
how thick its lines are, its dots, its faces and colours, its effects.
(The shape keeps turning, so its angle differs; the picture is taken in
silence.)

**Wrong if:** a preset blank, black or plainly different from its
picture (note which; the SYSTEM page or `<home>/stall.log` may name a
drawing error); lines thicker or thinner than the picture (check **Screen
strokes** on the VIEW page is unticked).

*(check 192)*

#### L84. A recorded point cloud in the picture (on the copy)

**Needs:** laptop; the copy, with the device list from L72.

**Do:**
1. Add the recorded-cloud block to the device list (as L76), but do not
   copy the file in yet; save. Watch SYSTEM's last lines.
2. Copy `hyperspace-python/tests/fixtures/clouds/knot.npz` into
   `<home>/clouds/`. Load LEGACY 6.
3. Roll the mouse wheel and drag to pan; CAMERA page → **eye** → move
   Eye field of view, then put it back.
4. ROUTING page: find Cloud point size, Cloud scale, Cloud brightness
   and Cloud colours (they have no page of their own); right-click each →
   **Learn desk** (APC40) or drag its slider on ROUTING; then load another
   preset.
5. Remove the entry; save.

**Right if:** (1) the picture is unchanged, the `scan` line says
`error: …`, and the GPU lines include `cloud 0.00` above `scene`.
(2) within about 10 seconds, with no restart, a knot of dots (blue low,
warm high) turning slowly, about the shape's size, threaded through it:
where a dot is in front of an edge it hides the edge, where it is
behind, the edge is drawn over it; the `cloud` line shows a small time.
(3) the knot does not grow or move with the zoom and pan, and does not
tumble with the shape; the field of view changes both together. (4) size
grows the dots in whole pixels; scale grows the knot (very large, the
near dots vanish); brightness 0 makes the dots black; colours off makes
them white; a preset load leaves all four as you set them. (5) no
`cloud` line.

**Wrong if:** dots always on top of the shape; dots tumbling with the
shape; nothing drawn while the `scan` line says `connected`; an error
message or a freeze while the file is missing.

**Changes:** remove the entry and the file.

*(checks 216, 217, 218)*

#### L85. The time each part of the picture takes

**Needs:** laptop.

**Do:** load TRIP (F5); SYSTEM page. On the FX page untick **Effects**,
wait two seconds, tick it again. On LOOKBACK switch **Look-back** on
and off. On OUTPUT tick **through effects**, then untick it.

**Right if:** under the stall status, "gpu per node, ms (median of the
last frames):" and one line each for `scene`, `cover`, `hands`,
`history`, `fx`, `capture`, `output.1`, a few milliseconds or less and
steady, and a line for each effect that is running just above `fx`
(`fx` itself always reads 0.00 now: see L95); the effects' lines go
with the effects off and come back within a second; `history` changes with the look-back; ticking **through effects**
adds `composite(scene+hands)` and `fx(scene+hands)`, which go again a
moment after unticking. No `ghost` line.

**Wrong if:** no lines; "gpu: no GPU timer queries …"; a line that stays
after its switch is off.

*(checks 194, 210)*

#### L86. The shape where it always was; the eye

**Needs:** laptop.

**Do:** load LEGACY 6, then PLASMA HEART; CAMERA page.

**Right if:** both look exactly as on earlier builds (size, place,
dots); CAMERA has an **eye** section ("the room's camera, not the
preset's") showing Eye field of view 47.6° and Eye distance 3.78, which
loading a preset never changes.

**Wrong if:** the shape off-centre or another size; dots bigger.

*(check 196)*

#### L87. Zoom grows the shape; Screen strokes

**Needs:** laptop (the hands part: tape).

**Do:**
1. Load PARTY FIELD, then HEX ENGINE, and look at the middle column of
   `hyperspace-python/docs/plans/assets/26-render-graph/a2b-moved.png`.
   VIEW page: **Screen strokes** is unticked.
2. Roll the zoom from small (about 0.3×) to big (about 5×).
3. Tick **Screen strokes** and roll again.
4. Load LEGACY 6 and flip **Screen strokes** on and off.

**Right if:** (1) fine edges and small red dots, as on earlier builds.
(2) the shape grows with its own perspective (the near side grows
faster), past about 4× the view passes inside it with no streak across
the screen, and the edges and dots grow and shrink with the shape; the
ghost hands never move or change size. (3) the edges and dots keep one
size whatever the zoom. (4) nothing changes at all.

**Wrong if:** the hands growing with the zoom; a streak across the
screen; lines that do not change with the zoom while the box is
unticked; anything changing in step 4.

*(checks 197, 198)*

#### L88. The naming rule

**Needs:** reading; then L90's preset.

**Do:** read `hyperspace-python/docs/ENGINEERING.md` §2, "Node
instances: the naming rule". With TWO-ACIDS loaded (L90), look at the
ROUTING page's setting names.

**Right if:** the rule is clear, and "Acid 2 mix" (`fx.acid.2.mix`)
reads right as the second acid's mix.

**Judge:** whether you would rather another form — say so before you
save a preset that uses one.

*(check 193)*

#### L89. A preset that says how its picture is wired (on the copy, tape)

**Needs:** laptop; the copy; hands (tape).

**Do:**
1. Copy `hands-lines.json` into `<home>/presets/`. Load PARTY WAKE and
   watch the hands for a few seconds. Load HANDS-LINES. Then load TRIP,
   then press ⌘Z.
2. LOOKBACK page with PARTY WAKE, then with HANDS-LINES.
3. Edit the copy's `hands-lines.json`: change the first `"hands"` (after
   `"kind":`) to `"teapot"`. Load it, save it (the preset strip's save),
   and open the file again.

**Right if:** (1) on PARTY WAKE the hands leave no trail; HANDS-LINES
shows the hands *inside* the shape as wire hands, bent with it by the
acid, trailing echoes, with no warning on the preset strip; TRIP is as
always; ⌘Z brings HANDS-LINES back as it was. (2) "history: the scene",
then "history: the scene · with the hands". (3) the strip's warning
reads "graph: unknown node kind 'teapot' (this build knows effect,
hands, history); the default graph", the preset still loads (the hands
drawn over the shape, not in it), and after the save the file still says
`teapot`.

**Wrong if:** the hands drawn over the shape on HANDS-LINES; a crash or a
refused load on the teapot; the teapot gone after saving.

**Changes:** delete the preset files you copied in.

*(checks 211, 209)*

#### L90. Two acids (on the copy)

**Needs:** laptop; the copy.

**Do:** make `two-acids.json` (above); load TWO-ACIDS; FX page, then
ROUTING. Then load TRIP.

**Right if:** two chips, "Acid" and "Acid 2", each with its own controls
(twist 0.9 and 0.3); moving one moves only it; ROUTING lists "Acid 2 …"
settings; on TRIP there is one acid and no "Acid 2".

**Wrong if:** one chip; both moving together; the second acid's settings
landing on the first.

*(check 212)*

#### L91. The wiring in words (on the copy)

**Needs:** laptop; the copy; L89's preset.

**Do:** OUTPUT and LOOKBACK pages with TRIP, then HANDS-LINES; hold the
pointer over the "shows:" line.

**Right if:** TRIP: the "shows:" line as before and "history: the
scene"; HANDS-LINES: "scene + hands: in the scene as lines" and
"history: the scene · with the hands"; the pop-up names the graph
("graph: hands 1 in the scene as lines · history with the hands"). No
page scrolls.

**Wrong if:** words that disagree with the picture.

*(check 215)*

#### L92. Hands inside the shape (on the copy, tape)

**Needs:** laptop; the copy; hands; the hand camera for the last part.

**Do:** make `hands-solid.json` (above); load HANDS-SOLID; HANDS page
→ ghost guide BESIDE. FX page: untick **Effects**. Watch the hands pass
through the shape (with the camera: push one hand slowly into the shape
from the front). Then drag **Ghost opacity** to 0.3, then to 0. Tick
**Effects** again.

**Right if:** the hands are solid inside the shape: near edges are drawn
over a hand, far edges are hidden behind it, and faint far edges never
cut a hole in it; at opacity 0.3 they are still solid, at 0 gone; with
**Effects** on the hands bend with the shape and leave a trail (a hand
held still turns whitish: expected); the guide stays sharp and unbent.

**Wrong if:** the hands always on top of the shape; holes in a hand where
faint edges are; the guide bent by the effect.

*(checks 204, 205)*

#### L93. A hands layer that goes behind the shape (on the copy, tape)

**Needs:** laptop; the copy; hands.

**Do:** make `hands-depth.json` (above); load HANDS-DEPTH; watch a hand
pass through the shape.

**Right if:** the hand, see-through at its Ghost opacity, disappears
behind near edges and bright faces and reappears in front of them; the
edges of the hiding flicker by a pixel at most; the OUTPUT page's line
ends "· depth-aware".

**Wrong if:** the hand cut where nothing is in front of it; never hidden.

*(check 207)*

#### L94. Hands as lines (on the copy, tape)

**Needs:** laptop (the 1080p projector too, if to hand); the copy;
hands.

**Do:** load HANDS-LINES; HANDS page → step **Ghost style** through all
five; then on OUTPUT untick **scene**.

**Right if:** the hands are drawn as wires, in every style; with the
scene off, wire hands alone on black; the guide stays solid; the shape's
own lines are unchanged.

**Judge:** whether the dense mesh of wires reads as "hands as lines", or
whether you want a skeleton of bone lines instead.

**Wrong if:** the shape drawn as wires too; hands invisible on a sharp
(Retina) screen.

**Changes:** tick **scene** again.

*(check 214)*

## Shader nodes (L95–L97 on the laptop; L98–L102 on the copy)

Plan 30 (shader nodes). Each effect on the FX page is now its own part
of the picture's wiring, and a preset can put one somewhere other than
the end of the chain: the colour palette on the hands only, on one
screen only, or a second acid before the trail. **No factory preset
does it**: these entries copy test presets into the copy's library, as
for the render graph above (delete any `[library] path` line on the
copy first). The test presets are in
`hyperspace-python/tests/fixtures/presets/`:

- `palette-hands.json` — PARTY TRACER's look with the palette on the
  hands only;
- `palette-glass.json` — PARTY ACID with the palette on output 2 only;
- `acid-scene.json` — PARTY MANDALA with a second acid before the trail
  (the look-back on).

Two variants of `palette-hands.json`, made as above (copy it under the
new name and replace the `"graph": {"nodes": [` … `]},` part):

- `palette-teapot.json`: `"graph": {"nodes": [{"kind": "effect",
  "file": "palette", "after": "teapot"}]},`
- `palette-both.json`: `"graph": {"nodes": [{"kind": "effect", "file":
  "palette", "after": "hands", "into": "output.2"}]},`

The screens-together entries are D19–D23 in Part 2 (d).

#### L95. A time for each effect on the SYSTEM page

**Needs:** laptop.

**Do:** SYSTEM page; load ACID (F6). On the FX page switch Kaleido on
and Acid off.

**Right if:** under "gpu per node, ms", lines `acid`, `wobble`,
`deconverge` and `huecycle` just above `fx`. The `fx` line itself reads
0.00 — that is by design (it only hands the picture on); the effects'
cost is on their own lines. After the switch, `kaleido` appears and
`acid` goes within a few frames. No line for an effect that is off.
(The split between the lines jumps about on the Mac's graphics chip:
look for the lines, not their exact share.)

**Wrong if:** one `fx` line carrying everything; a line for every
effect, on or off.

*(check 220)*

#### L96. Switching effects changes only the picture

**Needs:** laptop.

**Do:** ACID; on the FX page click effects on and off quickly; drag one
chip to another place; then untick **Effects**.

**Right if:** each click changes the picture as on earlier builds, with
no flash, no black frame and no stall line on SYSTEM; the drag reorders
as before; with **Effects** off the picture is the plain shape and
SYSTEM shows no effect lines.

**Wrong if:** a black or frozen frame on a click; a stall on every
click.

*(check 221)*

#### L97. An effect on the faces still bends only the faces

**Needs:** laptop.

**Do:** load FACES (F2). FX page: open Warp, click ONTO **faces**,
switch it on. Hold the pointer over the ONTO **faces** chip.

**Right if:** the pictures inside the faces warp and the rest of the
frame does not; the pop-up ends "On the faces it runs inside the
shape's face drawing: the one shader run the render graph does not
show, and a placement in the preset's graph does not move it."; the
faces row lists Warp; SYSTEM has no `warp` line.

**Wrong if:** the whole frame warps.

**Changes:** click ONTO **frame** and switch Warp off again.

*(check 230)*

#### L98. The palette on the hands only (on the copy, tape)

**Needs:** laptop; the copy; hands (the hand camera, or the recorded
hands of L44), **Ghost hands** ticked.

**Do:** copy `palette-hands.json` into `<home>/presets/` and load
PALETTE-HANDS; SYSTEM page; move the hands; then take them out of view.

**Right if:** the hands turn a slice of blue-cyan (they are pale, so it
may read grey-teal) while the shape and its trail keep their colours;
the guide and labels are not recoloured; SYSTEM shows a `palette` line
under `hands` while the hands show, and none without them.

**Judge:** whether the blue-cyan reads as you meant at a distance.

**Wrong if:** the whole picture turns blue; a dark rim around the hands.

*(check 223)*

#### L99. A placement the app cannot follow is a note (on the copy)

**Needs:** laptop; the copy.

**Do:** make `palette-teapot.json` and `palette-both.json` (above). Load
each; save it (the preset strip's save); open the file again.

**Right if:** the preset strip says, for the teapot, "graph: palette
after 'teapot' — this build places after scene, hands, hands.2 …,
history, output.1 …, or an effect; the default placement", and for the
other "graph: palette after 'hands' and into 'output.2' at once — one
of the two; the default placement"; the palette then recolours the whole
picture (it went back to the end of the chain); the preset loads with
no red dot; after saving, the file still says what you wrote.

**Wrong if:** the load refused; the file changed by the save.

**Changes:** delete the two files.

*(check 225)*

#### L100. A placement with nothing to sit on says so (on the copy)

**Needs:** laptop; the copy; L98's preset.

**Do:** PALETTE-HANDS; OUTPUT page: untick **hands** on every output;
then tick it again.

**Right if:** OUTPUT lists "dormant: palette after hands — no hands
layer this frame"; nothing is recoloured and SYSTEM has no palette
line; ticking **hands** brings the recolouring back.

**Wrong if:** the shape turns blue (the palette fell back into the
chain).

*(check 226)*

#### L101. The placements in words (on the copy)

**Needs:** laptop; the copy; the three test presets copied in.

**Do:** load each in turn; OUTPUT page: hold the pointer over the
"shows:" line.

**Right if:** the pop-up's last line reads "graph: palette on the
hands", "graph: palette on output 2 only", "graph: acid ×2 · acid 2
before the history"; no page scrolls.

**Wrong if:** words that disagree with the picture.

*(check 228)*

#### L102. The FX page's placed chip (on the copy)

**Needs:** laptop; the copy; L98's preset.

**Do:** PALETTE-HANDS; FX page. Drag the Palette chip; drop another chip
onto it. Click its name and hold the pointer over the open strip's
title. Untick every output's **hands** and hold the pointer over the
chip's name. Load TRIP.

**Right if:** the Palette chip sits in a second row of chips under the
others, reading "Palette · after hands", readable from where you stand;
the line under **Effects** reads "nothing in the chain · 1 placed"; the
drag and the drop do nothing; its dot switches it and its name opens
its controls, whose title pop-up reads "palette.glsl · after hands";
with the hands off the "1 placed" goes and the pop-up says "dormant: …";
on TRIP the Palette chip is back in the main grid, last.

**Wrong if:** the Palette chip in the main grid on PALETTE-HANDS; a
drag moving it; the page scrolling.

*(check 229)*

## The node editor (L103–L116 on the laptop; L117–L121 on the copy; L122 with two Macs; L123–L128 the legible graph; L129–L130 the palette as compression, plan 30 N8; L131–L135 the graph by concern; L136–L138 the instanced field, from `main`)

Plan 28 (the node editor). Three things changed. **The modulation has no
one-frame lag any more**: a setting that drives another (an LFO on
another LFO's depth, a macro scaling a route) acts in the same frame.
**Modifiers**: small boxes between a source and a route — curve, scale,
smooth, combine two sources, threshold to a trigger, a one-frame delay —
built on GRAPH (right-click the canvas → modifier; click one for its
settings; ROUTING's MODIFIERS strip did this before the legible graph)
and saved in the preset. And
a new page, **GRAPH** (after ROUTING): everything wired to everything,
drawn as boxes and cables, which you can rewire by dragging. **No
automated test can drag the mouse on that page**, so every drag below is
new to anyone. No factory preset has modifiers or wires: build your own,
on the copy when you save. Two pins on a setting's box: the round one
(**mod**) takes one performer (a hand, a band, an LFO); the square one
(**base**) takes the desk's knobs and the pad.

**Since the legible graph (L123–L128), ROUTING has no routes and no
MODIFIERS strip any more.** Wherever an entry below says "on ROUTING add
a route" or "the MODIFIERS strip", do it on GRAPH: drag from the source's
dot onto the setting's round dot (or onto a closed box's small left dot
and pick the setting), right-click the empty canvas → modifier, click a
modifier's box to set its inputs and knobs, click a wire to see its rows.
Right-click a slider → Route a lane here… also works and opens GRAPH.

#### L103. An LFO on another LFO's depth, the same frame

**Needs:** laptop.

**Do:** load TRIP (F5); open the LFO page; set LFO 2's depth to 0.5. On
GRAPH drag from *LFO 1*'s right-hand dot onto *LFO 2*'s left-hand dot and
pick **depth · mod**; click the new wire and set the row to push. Watch
LFO 2's scope.

**Right if:** LFO 2's swing breathes in and out with LFO 1's wave,
smoothly, both ways; the frame rate on SYSTEM is as before.

**Wrong if:** the scope stutters, doubles or freezes.

**Changes:** remove the route (or load TRIP again).

*(check 232; the hand part is B41)*

#### L104. A loop is refused in words

**Needs:** laptop.

**Do:** on GRAPH drag *LFO 1*'s right-hand dot onto *LFO 2*'s left-hand
dot and pick **rate · mod**, then *LFO 2*'s onto *LFO 1*'s and pick
**depth · mod** (both rows push, from their wires). Look under the
preset's name at the top of ROUTING. Then delete the first route on
GRAPH (open both LFO boxes, click its cable, Delete).

**Right if:** a warning line: "loop: lfo:0 → lfo.2.rate → lfo:1 →
lfo.1.depth → lfo:0 needs a delay — lfo:1 → lfo.1.depth is off until it
has one"; LFO 1's depth does not move; everything else runs; with the
first route gone the warning goes and LFO 2 moves LFO 1's depth.

**Wrong if:** no warning; the app stutters; a route disappears.

*(check 233)*

#### L105. A delay lets a loop run

**Needs:** laptop.

**Do:** on GRAPH right-click the canvas → **modifier ▸ delay**; click it
and set its input to **LFO 1**. Drag its right-hand dot onto *LFO 1*'s
left-hand dot and pick **depth · mod** (push, from the wire's row).

**Right if:** no warning; LFO 1's scope swells and shrinks with itself,
smoothly.

**Wrong if:** the loop warning; a scope that flickers between two shapes.

*(check 234)*

#### L106. Every LFO still runs

**Needs:** laptop.

**Do:** load TUMBLE (no LFO routes); LFO page; tap a tempo, then ⇧B.

**Right if:** all four scopes move at their own rates; ⇧B puts every
synced LFO on its downbeat.

**Wrong if:** a scope frozen or racing.

*(check 235)*

#### L107. Each modifier with music

**Needs:** laptop; music.

**Do:** on GRAPH add one modifier at a time (right-click the canvas →
modifier), drag band 0 (the kick) onto its left-hand dot, drag its
right-hand dot onto *shape*'s and pick **Brightness · mod**; click it to
try its settings; remove it (× remove) before the next. Curve: move **shape**, tick
**invert**. Scale: **mul** 2, then **clamp**. Smooth: a long **release**;
then **spring** on with attack 0.2. Combine: inputs band 0 and band 3,
**how** mul, then cross and move **balance**. Threshold. Delay.

**Right if:** curve bends how the brightness answers, invert flips it;
scale doubles it, clamp holds it at full; smooth makes it fall slowly
after each kick, the spring overshoots and settles; combine mul is darker
than either band, cross fades between them; threshold flashes once per
kick; delay looks like the plain route. Each modifier's bar (click it)
and its box's "out" line move with the music.

**Wrong if:** a bar that does not move (its input not set); a threshold
lit all the time.

*(check 236)*

#### L108. Modifier edits are undo steps

**Needs:** laptop.

**Do:** add a modifier, drag its release, pick another input; ⌘Z three
times, then ⇧⌘Z three times.

**Right if:** each ⌘Z takes back one change, the last one removes the
modifier; redo puts them back.

**Wrong if:** the add cannot be undone; one ⌘Z takes two changes.

*(check 240)*

#### L109. The GRAPH page shows what ROUTING shows

**Needs:** laptop.

**Do:** load TRIP; open GRAPH; click **expand all**. Then right-click a
slider on another page → Route a lane here…. Click **collapse all**.
Look at SYSTEM.

**Right if:** with everything open every route is one solid cable into a
setting's round pin, the desk's and keys' rows faint cables into square
pins; the new route is selected on GRAPH, its row first in the details;
with everything closed two boxes are one wire, whose hover counts its
cables; SYSTEM has a line "graph page: … ms median (N nodes, M
cables)", about 1.3 ms closed.

**Wrong if:** a cable missing or doubled; the app slows down with the
page open.

*(check 242)*

#### L110. Settings sit on the part of the picture they belong to

**Needs:** laptop.

**Do:** load ACID; GRAPH; click **expand all**, untick **patched only**.

**Right if:** the view settings are on the `shape` box, the acid's on
`acid`, the trail's on `history`, the camera's on `eye`; tempo and the
master faders have boxes of their own.

**Wrong if:** everything in loose boxes by group.

*(check 243)*

#### L111. Hover and select

**Needs:** laptop.

**Do:** load lfo-breathe; GRAPH; open (**+**) the two boxes a route
joins. Hold the pointer over its cable; click it; click **details
beside**, then **details below**; click an effect's box.

**Right if:** the pop-up says from → to, the reading and the depth; the
click shows that route's ROUTING row under the canvas; **details beside**
(only there while something is selected) moves it to a column at the
side and **details below** back; changing the depth there changes the
cable's thickness; an effect's box shows its FX controls.

**Wrong if:** the pop-up somewhere else on the screen.

*(check 245)*

#### L112. Quit, restart and a code edit with GRAPH open

**Needs:** laptop; a terminal.

**Do:** GRAPH open, zoomed in; `touch hyperspace-python/hyperspace/ui_graph.py`;
then ⌘R; then quit.

**Right if:** the page keeps drawing at its zoom; ⌘R and quit close
cleanly.

**Wrong if:** a crash when quitting; two canvases.

*(check 246)*

#### L113. Drag a cable on the laptop's screen

**Needs:** laptop alone, the control window at its normal size.

**Do:** load TRIP; GRAPH; open (**+**) the analyzer and `shape` and untick
**patched only**. 1. Drag from band 2's pin to `view.bright`'s round pin. 2. Drag
that cable's end, from the round pin, onto `view.speed`'s round pin. 3.
Drag a band onto a setting a route already drives: answer **Keep**, then
again and **Replace**. 4. Right-click the empty canvas → **modifier ▸
smooth**; drag the new box over the band 2 cable and let go. 5. ⌘Z four
times.

**Right if:** the cable appears when you let go and clicking it shows the
route's row; it then ends on `view.speed`; Replace / Keep comes up; the smooth
sits between band 2 and `view.speed`; each ⌘Z takes one step back; a
drop on a wrong pin turns red with words and makes nothing.

**Wrong if:** a drag that never makes a cable; pins too small to hit;
the drop on the cable doing nothing.

*(check 247)*

#### L114. Delete on the canvas

**Needs:** laptop.

**Do:** load lfo-breathe; GRAPH. 1. Click the route a macro's depth cable
scales; press Delete; ⌘Z. 2. Click a key's faint cable; Delete. 3.
Right-click a macro's box → **delete**; ⌘Z. 4. Add a modifier with a
route on it; select its box; Delete.

**Right if:** 1: the route and the macro's cable go together and ⌘Z
brings both back; 2: the cable stays and the top line says it is the
session's (bindings.json); 3: the macro's label and every cable from it
go, the knob stays, ⌘Z puts them back; 4: the box goes, its route stays
and does nothing.

**Wrong if:** deleting a modifier deletes its routes.

*(check 250)*

#### L115. A wrong picture cable is refused in words

**Needs:** laptop; the copy for step 3.

**Do:** GRAPH. 1. Drag `ghost` (the hands) onto `output.1`'s image pin.
2. Drag `acid` onto `palette`'s image pin, then `palette` onto `acid`'s.
3. On the copy, in a saved preset's `"graph": {…}` add `, "wires":
[{"from": "teapot", "to": "output.1.image"}]` and load it.

**Right if:** 1: red, "wire ghost → output.1.image — ghost makes
geometry, output.1.image takes a picture"; 2: the second turns red with
"that makes a loop (…)"; 3: a note "graph: wire teapot → … ; the default
wiring", the rest of the look loads, no red dot.

**Wrong if:** a refused cable lands; one bad wire costs the whole look.

*(check 253)*

#### L116. Add and delete an effect on the canvas

**Needs:** laptop.

**Do:** GRAPH; right-click the empty canvas → **effect ▸ acid**; select
the new `acid.2` box → Delete; ⌘Z. Try Delete on `output.1`, on `acid`
and on a cable nobody wired.

**Right if:** "Acid 2" settings appear on FX and ROUTING, off; Delete
removes them, ⌘Z brings them back; the last three are refused in words.

**Wrong if:** the settings stay after the delete.

*(check 255)*

#### L117. A preset holds its modifiers (on the copy)

**Needs:** laptop; the copy.

**Do:** build two modifiers on GRAPH; save as a new preset; load
another, then this one; open `<home>/bindings.json` and the preset's
file in a text editor.

**Right if:** the modifiers come back as they were; the preset file has
a `"modifiers"` list after `"routes"`; `bindings.json` says nothing of
modifiers; a factory preset loads with no note and no modifiers.

**Wrong if:** modifiers in `bindings.json`; a red dot on a factory
preset just loaded.

*(check 238)*

#### L118. A desk template's modifiers (on the copy)

**Needs:** laptop; the copy.

**Do:** copy `tests/fixtures/modifiers/desk/mod-rig.json` into
`<home>/desk/` and `tests/fixtures/modifiers/presets/mod-templated.json`
into `<home>/presets/`; load MOD-TEMPLATED; save a copy and give the
copy's first modifier a longer release; save. Change the release in the
template file and load each preset again.

**Right if:** both show the template's modifiers; the copy keeps its own
release; the template's change reaches the other.

**Wrong if:** the saved copy holds every template modifier.

*(check 239)*

#### L119. Boxes stay where you put them (on the copy)

**Needs:** laptop; the copy.

**Do:** load TRIP and save it as a new preset; GRAPH. Drag the `shape`
box; save; load another preset and this one again. Drag an LFO's box.
Press **tidy**, then ⌘Z and ⇧⌘Z.

**Right if:** dragging `shape` puts a red dot on the preset and it comes
back where you dropped it; the preset file ends with a `"layout"`;
dragging the LFO marks the show instead; **tidy** lines everything up
left to right (controllers, LFOs, modifiers, macros, settings, the
picture, the outputs) and is one undo step each way.

**Wrong if:** a box jumps back while you drag it; a red dot on a factory
preset just loaded.

*(check 244)*

#### L120. A desk template as one box (on the copy)

**Needs:** laptop; the copy. The APC40 not needed.

**Do:** copy `tests/fixtures/desk-templates/desk/fixture-shape.json`
into `<home>/desk/` and `tests/fixtures/desk-templates/presets/templated.json`
into `<home>/presets/`; load TEMPLATED; GRAPH. Find the box *template
fixture shape* and click its **+**. Delete D1's cable. Drag D3's pin on
the template box onto `view.speed`'s square pin. Save as a new preset
and open its file.

**Right if:** closed, the box lists 7 controls and no cables; opened, 5
cables; the saved file says `"desk_template": "fixture shape"` and its
`"desk"` has D1 dark and D3 on `view.speed`; the template file is
unchanged.

**Wrong if:** no template box; the template file changed.

*(check 257)*

#### L121. A preset from before this build loads with no note (on the copy)

**Needs:** laptop; the copy and its own presets saved before this build.

**Do:** load each of your own presets; open ROUTING and GRAPH; save one.

**Right if:** no note and no red dot on any load; ROUTING's desk lines as before;
GRAPH draws every route; the saved file gains no `"modifiers"`,
`"layout"` or `"wires"` unless you added one.

**Wrong if:** a note or a red dot from a load.

*(check 260)*

#### L122. A patch shared between two Macs

**Needs:** two Macs **both on this build** (the branch above, or `main`
once merged), sharing a library folder as in L43.

**Do:** on Mac A build B43's patch (or any two modifiers and a route),
drag its boxes about, and save it as a new preset. Load it on Mac B;
change a modifier's release there and save; load it again on A.

**Right if:** B shows the same modifiers, routes and box positions, no
note; A gets B's change after the sync.

**Wrong if:** a note on B; the modifiers or positions missing.

**Important:** a Mac on an **older build** opens such a preset with the
default picture wiring and a note, silently ignores its modifiers and
box positions, and **throws them away if it saves the preset**. Update
both Macs before you share patches, and never save one on an older build.

*(check 259)*

**A legible graph (L123–L128, plan 28 N7).** After the owner's first look the GRAPH page was too busy, so now **every
box starts closed**: its name and at most five short lines (how many
ports it has, how many are wired, what is loudest right now), and **one
wire between two boxes** however many settings are mapped between them.
Click a box's **+** to open it (its ports, as before) — the real cables
appear only when both boxes are open. The routes and the modifiers are
edited on GRAPH now; ROUTING keeps the desk, the macros, the session's
rows and the sinks, with a line at the top pointing to GRAPH.

#### L123. The closed graph reads at a glance

**Needs:** laptop; the APC40 plugged in helps (its box says "off"
without it).

**Do:** load party-trip; open GRAPH; stand back at your usual distance.
Then open SYSTEM and read the `graph page:` line.

**Right if:** a handful of boxes, each a name and one to four short
lines; one wire from *apc40* to *shape*, one to *fx*, one to *eye* (and
one to each other box the desk maps into — the two APC40 boxes have 19
wires between them, most into the small setting boxes on the right); the
top line says about "55 nodes · 64 wires · 238 cables"; SYSTEM says
about 1.3 ms (it was 2.3–2.8 ms before).

**Wrong if:** a box lists its ports before you open it; two wires
between the same two boxes; SYSTEM over 2.3 ms.

*(check 261)*

#### L124. Open two boxes: the real cables

**Needs:** laptop.

**Do:** hover the *apc40* → *shape* wire; click it. Click *apc40*'s
**+**, then *shape*'s **+**. Then **collapse all**.

**Right if:** the hover says "24 cables: …", ten of them and "+ 14
more"; the click lists those rows under the canvas; with only *apc40*
open it is still one wire; with both open each control has its own
cable; **collapse all** brings the boxes back. (A wire of desk rows
lists them as plain lines in the details: the desk's own lines on
ROUTING edit them.) Pressing Delete on a
wire says "expand a node to edit its cables" and deletes nothing.

**Wrong if:** cables while one box is closed; a wire ending in mid-air.

*(check 262)*

#### L125. Drop a cable on a closed box

**Needs:** laptop.

**Do:** open *analyzer* only. Drag from band 3's dot onto the small dot
left of *shape*'s name; let go; pick **Brightness · mod**. Press ⌘Z. Then
right-click *shape* → **learn** → a group → a setting → Learn hand →
right, and move your hand (or skip without the camera).

**Right if:** while dragging: "let go: pick one of shape's ports"; the
list offers only what a band can drive; the pick makes the route
(the wire's pop-up counts one cable more; Brightness pulses with band 3), ⌘Z removes it; the Learn works without
opening *shape*.

**Wrong if:** no list; a square **base** entry offered for a band.

*(check 263)*

#### L126. Tidy says what it did; the details button

**Needs:** laptop.

**Do:** click **tidy** on a fresh page. Open two boxes, drag one far
away, click **tidy** again. Click a wire; click **details beside**, then
**details below**.

**Right if:** first "already tidy"; then every box closed and back in
its area, the view framed on them, "laid out 31 nodes in 6 areas, every
one collapsed · 22 idle off the canvas"; ⌘Z puts the dragged box back; the details button only
appears once something is selected, and moves the details beside the
canvas and back.

**Wrong if:** tidy says nothing or leaves a box open; the details button
with nothing selected.

*(check 264)*

#### L127. The energy patch from GRAPH alone

**Needs:** laptop, the hand camera, music; the copy.

**Do:** on GRAPH only (never ROUTING): right-click the canvas → modifier
→ smooth, then → combine. Open *leap*; drag **right energy** onto the
smooth's small left dot, pick its input. Drag the smooth's right dot onto
the combine's left dot, pick **in 1**; open *analyzer*, drag band 0 onto
the combine, pick **in 2**. Click the combine and set **how** to mul in
the details. Drag the combine's right dot onto *acid*'s left dot, pick
**acid mix mod** (acid on in the chain). Dance with the right hand.

**Right if:** every step works on GRAPH; the acid's mix swells with your
energy, smoothly, and pumps with the bass; it settles when the hand
leaves.

**Wrong if:** a step needs ROUTING; the combine's details are cut off.

*(check 265)*

#### L128. ROUTING points to GRAPH; the desk lines as before

**Needs:** laptop, the APC40.

**Do:** open ROUTING. Click a control on the desk diagram; right-click a
desk line → Learn, move a knob. Click "routes and modifiers: the GRAPH
page". Then right-click any slider → Route a lane here….

**Right if:** no route rows and no MODIFIERS strip on ROUTING; the desk,
macros, session and sinks exactly as before; the line opens GRAPH;
"Route a lane here…" opens GRAPH too.

**Wrong if:** anything in the desk section changed.

*(check 266)*

#### L129. The palette's Mode is a picker; its rows read as the slice

**Needs:** laptop. Plan 30 N8.

**Do:** FX page, open **Palette**. Click **Mode**: pick **gradient**,
then **compress**.

**Right if:** Mode is a drop-down with two words, compress and
gradient — not a slider. On compress the strip shows a faint line
"compress into: hue 0° → 360° · sat 0.00 → 1.00 · val 0.00 → 1.00",
then three rows, **hue**, **sat** and **val**, each two sliders with an
arrow between them (the hue row ends in a small **turn** slider that
moves the whole slice round), and a thin coloured bar under the hue row;
right-clicking MODE opens its menu; on gradient the anchor rows instead.
The page never scrolls.

**Wrong if:** Mode is a slider; the from/to sliders on separate rows.

*(check 270)*

#### L130. An old palette preset (centre and width) loads as the same look (on the copy)

**Needs:** laptop; the copy.

**Do:** copy `palette-glass.json` into `<home>/presets/` as
`old-glass.json`; in it replace `"fx.palette.hue_from": 170.0,
"fx.palette.hue_to": 230.0` with `"fx.palette.centre": 200.0,
"fx.palette.width": 60.0` (the way a preset saved before this build
reads). Load PALETTE-GLASS, then OLD-GLASS; open the palette. Save
OLD-GLASS and open its file.

**Right if:** both look the same; no note on the preset strip; the hue
row reads 170 → 230; the saved file has `hue_from` and `hue_to`, no
`centre` or `width`. A preset you saved before this build loads with no
note either.

**Wrong if:** the old one shows the full rainbow, or a note about
unknown ids.

**Changes:** delete the files.

*(check 271)*

#### L131. The three areas at a glance

**Needs:** laptop (the APC40 helps).

**Do:** launch on party-trip, open GRAPH. Read it; drag the canvas to
the left to see the rest; zoom out a few clicks with the wheel.

**Right if:** faint titles over the columns: CONTROLLERS, AUDIO (OTHER
under it), MODULATION, GEOMETRY, SHADERS. The sound boxes (analyzer,
band, tempo, master, audio, scene) are all under AUDIO; the shape, the
camera's *eye* and the hands under GEOMETRY; the history, the effects
and the outputs under SHADERS, four across, row under row. Every wire
runs from left to right, but the one that takes the shaders' chain from
the end of a row to the start of the next.

**Wrong if:** a sound box among the shapes or shaders; a wire that runs
back to the left.

*(check 272)*

#### L132. A macro shows up when you patch it

**Needs:** laptop.

**Do:** under MODULATION find the small box "8 idle macros · 3 idle
LFOs"; click its **+**. Drag *Macro 3*'s right dot onto *shape*'s left
dot and pick **Brightness · base**; click the small box's **−**. Then
open *Macro 3* and *shape*, click the new cable, press Delete.

**Right if:** **+** shows the eight macros and three LFOs under the small
box; once patched, *Macro 3* stays on the canvas with one wire into
*shape* and the box says "7 idle macros · 3 idle LFOs"; after the Delete it goes back
into the box. Right-clicking the canvas → **macro** still lists all
eight.

**Wrong if:** a macro with no wire on the canvas; a patched one hidden.

*(check 273)*

#### L133. Tidy puts everything back in its area

**Needs:** laptop.

**Do:** drag *shape* far away, open the idle box, open *apc40*; click
**tidy**; press ⌘Z.

**Right if:** everything closed and back under its title, the idle box
shut, the view framed; the line under the buttons says "laid out 31
nodes in 6 areas, every one collapsed · 22 idle off the canvas"; ⌘Z puts
*shape* back where you dropped it.

**Wrong if:** idle macros left on the canvas; a box outside its area.

*(check 274)*

#### L134. The off effects are one line

**Needs:** laptop.

**Do:** on party-trip open GRAPH, click the **SHADERS** button. Hover the
faint red wire leaving *history*; press Delete on it. On the FX page
switch *warp* on, come back; switch it off again. Then click the small
"9 off effects" box's **+**.

**Right if:** only the effects that are on are boxes (plasma, kaleido,
zoomblur, huecycle); the faint wire names the effects it runs over and
Delete only says what it is; *warp* on is a box in the chain, off it is
back in the small box; **+** shows every effect in its place.

**Wrong if:** the chain has a gap with no faint wire; *warp* does not
come back when switched on.

*(check 275)*

#### L135. Five buttons frame the areas

**Needs:** laptop.

**Do:** on party-trip, GRAPH: click **tidy**; then the buttons
**CONTROLLERS**, **AUDIO**, **MODULATION**, **GEOMETRY**, **SHADERS** one
after another; then click the faint GEOMETRY title on the canvas.

**Right if:** after tidy everything fits with the titles readable; each
button fills the canvas with that area's boxes, close enough to read
them; the title click does the same; the shaders sit four across, row
under row.

**Wrong if:** a button frames nothing; the shaders in one long row.

*(check 276)*

#### L136. Four thousand copies hold the frame rate

**Needs:** laptop.

**Do:** VIEW: shape the 120-cell, faces on. Drag Instances to the top
(4096), Layout GRID, then CUBIC. Scroll out until the whole field
shows. Turn faces off, then on. Scroll back in.

**Right if:** the frame rate on the SYSTEM page stays near 60 with faces
off and stays usable with faces on; zoomed in it is back at full speed.

**Wrong if:** the picture stutters more and more as the count rises at
the same zoom.

*(check 277)*

#### L137. Fit leaves no copy cut by the edge

**Needs:** laptop; the projector or a second screen if you have one.

**Do:** VIEW: Instances 12, Layout GRID, tick **Fit**. Then 7 and 19
on HEX, and 200 on FCC. Scroll in and out; right-drag.

**Right if:** 12 copies sit four across and three down, evenly spaced,
none touching an edge. Zooming in jumps between whole copies — never
half a shape at the screen's edge — and dragging moves one copy at a
time. A 3D lattice stays whole and centred.

**Wrong if:** any copy is cut by the edge of the screen.

*(check 278)*

#### L138. The lattices read as 3D

**Needs:** laptop; a mouse helps.

**Do:** VIEW: 300 copies of the tesseract. Try each of CUBIC, BCC, FCC,
HCP, HEX PRISM and DIAMOND; orbit with the mouse. Set Field depth to 0,
then 0.5, then 1. Turn a field motion on.

**Right if:** the field turns as one solid; nearer copies are larger,
brighter and drawn over farther ones; at depth 0 every copy is one size.

**Judge:** whether the default depth (0.5) and how far the far copies
fade are right.

**Wrong if:** a far copy is drawn over a near one.

*(check 279)*

## The step sequencer (L139–L144; plan 31)

The LFOs can now number up to sixteen; there are **envelopes** (a shape
that rises and falls once each time something fires it) and a **step
sequencer**: a grid of five lanes by eight steps that fires the lanes'
envelopes in time with the tapped tempo. The new **SEQ** page, after LFO,
draws the grid. The factory preset **seq-demo** has a drum pattern: the
kick brightens the picture, the snare punches the zoom, the hats split
the colours. It loads stopped: press **run** on the SEQ page.

#### L139. Seven LFOs, then sixteen (on the copy)

**Needs:** laptop; the copy.

**Do:** load LFO BREATHE; open LFO. Click **+ lfo** three times. Click a
one-line strip's arrow. Click **×** on LFO 2, then ⌘Z. Click **+ lfo**
until it greys out, hover it, and scroll the page.

**Right if:** with four LFOs the page looks as it always did; from five,
all but one strip are a single line with a small picture and a moving
bar, and the arrow opens that strip and closes the other; after ×, LFO 3
is still called LFO 3; ⌘Z brings LFO 2 back; at sixteen the button is
grey and says why; the page scrolls and stays smooth.

**Wrong if:** the LFOs renumber after a ×; two strips open at once; the
app stutters with sixteen.

*(check 280)*

#### L140. The SEQ page from across the room

**Needs:** laptop.

**Do:** load **seq-demo**, open SEQ, press **run**. Step back two
metres. Then click the number **6** above the grid; click lane 2's **M**;
click lane 3's number; click any square; ⌘Z.

**Right if:** the green squares (the kick, the snare and the hats) stand
out from the dark ones; a red-framed column walks across in time, and a
green square under it turns yellow — still easy to tell from green;
after **6**, columns 7 and 8 go dim and ignore clicks; lane 2's squares
turn red; clicking lane 3's number opens envelope 3's strip below; a
click toggles a square and ⌘Z puts it back. Nothing scrolls.

**Wrong if:** yellow and green hard to tell apart from a distance; a dim
column that still toggles.

*(check 281)*

#### L141. The drum pattern against music

**Needs:** laptop; music at about 120 BPM, then about 175.

**Do:** tap the tempo in with the music; press ⇧B on a downbeat; load
**seq-demo**, press **run**. Then the faster track: tap again, ⇧B. On
envelope 1's strip set **mode** to gate.

**Right if:** the picture flashes on the kick, the zoom punches on the
snare and the colours split on every hat, all on the music; nothing
drifts over a minute; at 175 the hats are still separate hits; in gate
mode the kick still lets go quickly.

**Wrong if:** hits early or late against a good tap; a hit doubled or
missed when the app stutters; a gate-mode kick that stays lit.

*(check 282)*

#### L142. The trigger lines the pattern up

**Needs:** laptop.

**Do:** on seq-demo, running, set LFO 1's sync to **1 bar** and route it
onto something you can see. Press ⇧B off the beat a few times; then the
SEQ page's **restart**; then ⇧B again.

**Right if:** each ⇧B puts the grid on step 1 and LFO 1 at the start of
its cycle at the same moment, with a kick there; **restart** puts only
the grid on step 1, LFO 1 carrying on; the next ⇧B lines both up again.

**Wrong if:** the grid ignores ⇧B; a burst of hits on a press; restart
moves the LFO.

*(check 283)*

#### L143. The lanes on the GRAPH page

**Needs:** laptop.

**Do:** on seq-demo, stopped, open GRAPH, click **MODULATION**; open the
*sequencer* box and *env 1*–*env 3* (open the idle line's **+** to see
*env 4*). Press run on SEQ and come back; mute lane 2 there. Drag lane
1's dot onto *env 4*'s **fire** dot; ⌘Z. Click a lane cable and press
Delete. Right-click *env 1*; right-click the canvas and add an
**envelope**, then delete it.

**Right if:** three cables, "lane 1 fires env 1" to "lane 3 fires env 3",
faint and marked "(stopped)" until run is on, lane 2's faint "(muted)";
lanes 4 and 5 (no steps) have none; the drag moves lane 1 onto env 4 (the
SEQ page's picker says env 4) and ⌘Z moves it back; Delete only explains
how to rebind; env 1 cannot be deleted and says why; the new envelope is
env 6 and can be deleted.

**Wrong if:** a lane cable deleted; the drag making a route instead.

*(check 284)*

#### L144. A pattern preset on an older build (two Macs, on the copy)

**Needs:** two Macs sharing one library folder, one on this build and one
on a build from before plan 31; the copy.

**Do:** on this build save TRIP unchanged under a new name; then turn one
step on in the SEQ grid and save under another name. Open both files in
a text editor. Load each on the older build.

**Right if:** the unchanged one says `hyperspace.preset/2` and has no
`env.` or `seq.` lines; the other says `/3`; the older build loads the
first and refuses the second with a message about the schema, leaving
the file as it was.

**Wrong if:** the older build opens the `/3` file and, saved there, it
loses its pattern.

*(check 285)*

## Media (plan 32: L145–L151)

Plan 32 gives the app eight media channels (pictures, video, a webcam,
Syphon, NDI) and the MEDIA page. Run on the copy, after `uv sync`
(four new libraries). Put a still, a `.heic`, a 30 s `.mp4` and a `.gif`
in `~/Hyperspace-try/media/`. A preset that uses media is saved in a new
file format (`/4`, which is `/3` plus media): a build from before plan 32
will not open it, so both Macs need this build first.

#### L145. A still as the backdrop; the faces and `aux`

**Needs:** laptop; a picture.

**Do:** MEDIA page: pick the picture (This Mac), click cell 1 of channel
A; set Backdrop to A, alpha 1; turn the look-back on and flip its
"history" switch; then set Faces to A and try the four paths. On the
GRAPH page wire `media.a` to the `aux` port of Displace, then Blend.

**Right if:** the picture sits under the shape, bent by effects with
history on; on the faces it keeps its shape and follows the pattern;
Displace bends the frame by the picture's brightness and Blend keys its
bright parts; unwired, each effect does nothing.

**Wrong if:** the picture is upside down, stretched, or vanishes when an
effect is placed after the scene.

*(checks 296, 297)*

#### L146. A video: speed, scrub, loop; the cue knob as a jog wheel

**Needs:** laptop; an APC40 for the jog.

**Do:** put the `.mp4` on channel A (backdrop A). Set rate 2, −1, 0;
loops; drag Position while it plays and let go. Learn the cue knob onto
Jog and spin it.

**Right if:** the clip plays at the rate, scrubs where you drag and plays
on when you let go; a jog spin speeds it and coasts back like a platter;
nothing stalls.

**Judge:** whether the jog's gain and coast feel right.

**Wrong if:** the picture hitches while scrubbing or the jog never
settles.

*(checks 298, 299)*

#### L147. A dropped file; a missing-local banner

**Needs:** laptop; for the second half the shared cloud folder and a
second Mac.

**Do:** with the MEDIA page open, drop a picture into the media folder in
Finder; delete one that is on a channel. On Mac 1 save a preset whose
bins hold a `local:` file; load it on Mac 2.

**Right if:** the new file is listed within about two seconds; the deleted
one's channel goes black and reads `missing`; Mac 2 shows a banner naming
the source it lacks and the channel is black.

**Wrong if:** the app stalls, or no banner.

*(checks 300, 301)*

#### L148. Junk files, a renamed clip, rapid switching; the page at distance

**Needs:** laptop.

**Do:** put a `.txt`, a truncated `.mp4`, a 0-byte `.png` in the media
folder; rename a playing clip; sweep a channel's slot with an LFO over
eight clips for a minute; quit. Stand two metres back from the MEDIA page
with 30 files in the library.

**Right if:** the junk is listed with an error and nothing else stops; the
sweep never hitches; the app quits in about two seconds; the page reads
from there.

**Wrong if:** a hitch at a switch, a slow quit, or a page too small to
read.

*(checks 302, 303)*

#### L149. Syphon and NDI in

**Needs:** laptop; Resolume or TouchDesigner; a second Mac for the
network case. `kind = "syphon"` and `kind = "ndi"` in `[[devices]]`.

**Do:** on the Live tab put a Syphon server, then a Resolume NDI sender,
then a TouchDesigner sender from the second Mac, on the backdrop. Quit and
restart each sender. Where mDNS is blocked, add `extra_ips`.

**Right if:** each appears in a few seconds, upright; a quit sender holds
its last frame a second, goes black and returns by itself.

**Wrong if:** nothing is found, the picture is flipped, or it needs a
relaunch to return.

*(checks 304–307, 313, 315)*

#### L150. Syphon and NDI out; a publish-only output

**Needs:** laptop; Resolume or TouchDesigner; a second screen.

**Do:** set `syphon = "hs"` and `ndi = "hs"` on `[output]`; receive in
Resolume and TouchDesigner. Give output 2 `window = false`. Resize and
move output 1's window.

**Right if:** the picture arrives upright at the render size (not 4K);
SYSTEM shows both publishers at about 60 fps, NDI's readback near 4 ms;
output 2 opens no window and still sends.

**Wrong if:** it is flipped, black, or the sent size follows the window.

*(checks 308–310)*

#### L151. A webcam; a phone through an NDI app; an old bitmap preset

**Needs:** laptop; a phone with an NDI camera app; the copy.

**Do:** `kind = "camera"`; put the camera on a channel and accept the
macOS prompt. Start the phone app's NDI sender; put it on a channel. Load
a preset saved before plan 32 with a picture on the faces.

**Right if:** the camera runs at about 30 fps; the phone appears as an NDI
source; the old preset loads with a note that the bitmap is no longer read.
The APC40's knob 7 still moves the faces' media opacity.

**Wrong if:** a stalled camera, or a crash on the old preset.

*(checks 311, 312, 314, 316)*

## Plans 31 and 32 together (L152)

#### L152. A preset with a pattern and a bin, saved and reloaded

**Needs:** the laptop on branch `plan-31-32-integration` (or later), a
picture in `~/Hyperspace-try/media/`, the copy; a second Mac on a build
from before plan 31 or on `plan-32-media` alone, sharing the library.

**Do:** load TRIP. In the SEQ grid turn two steps on; on the MEDIA page
put the picture in channel a's bin and pick it as the backdrop. Save under
a new name. Open the file in a text editor. Load another preset, then
load the new one again. On the second Mac, try to load it.

**Right if:** the file says `hyperspace.preset/4`, has `seq.` lines, the
`media` section with the picture's id, and the backdrop values; reloaded,
both steps are on and the picture is behind the scene again; the second
Mac refuses the file with a message about the schema and leaves it as it
was.

**Wrong if:** the file says `/3` or `/2`; either the pattern or the
picture is gone after the reload; the second Mac opens it.

*(check 317)*

## Plan 33: the free graph (L153–L157)

#### L153. The headline graph; reordering by dragging; the FX page on a branch

**Superseded in part (2026-10-29):** dragging an effect that is already in the run onto another cable moves it only with ⌘ held (check 404, L197).

**Needs:** laptop; a clip and a camera; the copy; branch
`plan-33-free-graph`.

**Do:** put the clip on channel A and the camera on B. On GRAPH,
right-click the canvas and add `acid`, `tripcolour` and `kaleido`; they
appear faint, "reaches nothing". Wire `media.a` → `acid.2` →
`tripcolour.2` → `shape.faces`, and `media.b` → `kaleido.2` →
`backdrop.image`; set the backdrop alpha to 1. Save under a new name.
Then load `party-trip`, drag its first effect onto another cable, undo,
and right-click a cable to insert an effect. Open the FX page: click
`acid.2`, move a slider, press **Show on GRAPH**.

**Right if:** each node stops being faint as it is wired; the clip plays
on the faces through the two effects and the camera is a kaleidoscope
behind the shape; the saved file says `hyperspace.preset/5`; a drag moves
the effect and the run closes over the gap, one undo puts it back, a
drop on empty canvas does nothing, the insert adds an instance; the FX
page lists `acid.2` under **→ faces** and `kaleido.2` under **→
backdrop**, the slider changes the picture, and **Show on GRAPH** centres
the node.

**Wrong if:** a wire is refused that should land, the faces go black, a
node duplicates, or the two pages disagree about which effect is open.

*(checks 318, 320, 321)*

#### L154. A drop beside a cable; a shader back into the faces on the layout

**Superseded in part (2026-10-29):** a cable lights while a node is dragged over it and the drop lands only on a lit one; an effect already wired moves to another cable only with ⌘ held (check 404, L197).

**Needs:** laptop; the copy; L153's graph.

**Do:** drag an effect node and let go a few pixels beside a cable, then
beside a modulation cable. Press tidy on L153's graph and look at the
cables.

**Right if:** a drop within reach of a cable lands on it, a drop away
from one does nothing, and a refusal note ("x is no picture cable") is
rare and makes sense; the cables run left to right (MEDIA, then GEOMETRY),
none doubling back, and the two effects on the faces sit in MEDIA.

**Wrong if:** a node moves for a drop nowhere near a cable, or a cable
runs back across the canvas.

*(checks 325, 326)*

#### L155. The FX page with a big graph, from across the room

**Needs:** laptop.

**Do:** build a graph with about twelve effects, two branches, the faces,
the backdrop and three unreached nodes. Open the FX page and stand a
metre and a half back.

**Right if:** the group headers and state words are legible, a name is
easy to hit, nothing is clipped, and **reaches nothing** stands out.

**Wrong if:** a row is hidden or a strip is pushed off the page.

*(check 327)*

#### L156. A channel lost on the faces; the frame cost of branches and a switch

**Needs:** laptop; a camera or an NDI sender.

**Do:** with a live source on the faces through two effects, unplug it for
five seconds and plug it back. Then note SYSTEM's frame time on
`party-trip`, build two branches, the faces branch and an eight-way
switch driven by an LFO, and write down SYSTEM's frame rate and each
branch's ms each time, with none wired first.

**Right if:** the faces show the pattern, not black or frozen, while the
source is gone, and the picture comes back by itself; the frame rate
stays where it was with no branches and the eight-way switch costs about
one branch, only its picked path showing on SYSTEM.

**Wrong if:** black faces, a freeze, a switch whose cost grows with its
inputs (the frame rate drops visibly), or a branch's line that keeps
growing.

*(checks 323, 324)*

#### L157. An old party preset looks the same; a free graph on an older build

**Needs:** two Macs sharing a library, one on this build and one on the
build from before plan 33; the copy.

**Do:** on the new build, load each `party-*` preset and `dial`; save one
untouched under its own name and diff it against the original. Open the
library on the old Mac. Then save L153's graph, try it on the old Mac,
strip its branches on the new build and save again.

**Right if:** no load note, the pictures look as before, the untouched
save is byte-identical and the old Mac opens it; the free graph's file
says `/5` and the old Mac refuses it, leaving it as it was; the run-only
file is a lower schema and the old Mac opens it.

**Wrong if:** a load note, a changed picture, a diff, or the old Mac
opening a `/5` file.

*(checks 322, 328)*

## Plan 35: the free frame (L158–L162)

Plan 35's tests: the frame is wired, so **three `/6` fixtures**
(`blank-frame`, `channel-out-only`, `through-one-output`) and **24 new
goldens** (741; the 717 before it did not move) are in
`tests/golden/frames/`; each golden output state (scene off, hands
through, …) is written as that output's own wires, with the window mutes
on; and a **signature test** (`graph.signature`, 125 cases in
`tests/fixtures/frame-signatures.json`) proves the wired frame builds the
node-for-node frame the deleted `default_graph` built. L82 now ends "all
757 frames match their goldens".

#### L158. A new preset, and the owner's delete sequence

**Needs:** laptop; the copy; branch `plan-34-feedback` (PR #236).

**Do:** load `party-trip`, change a knob and a route, then press **new**
on the PRESET strip. Right-click GRAPH and pick the scene starter; undo
twice. Load `party-trip` again and, on GRAPH, delete the cable from the
scene to the backdrop, then the look-back's cable into the first effect,
then each effect's cable, then the last effect's cable into All outputs.

**Right if:** the new preset is black on both windows with the factory's
values and desk; the starter shows the shape on both; every delete lands
with no refusal and the picture changes as it goes, black at the last.

**Wrong if:** a value left over, a refusal about "the default graph", or a
cable that cannot be deleted.

*(checks 342, 343)*

#### L159. A channel alone; the OUTPUT page and LOOKBACK

**Needs:** laptop; a clip; the copy; the TV for two windows.

**Do:** on a new preset wire the clip's channel into All outputs. On
OUTPUT pick a different picture for output 2, then "as All outputs",
then undo. On LOOKBACK set **records** to the backdrop, the scene and
nothing.

**Right if:** the clip fills both windows with no scene pass on SYSTEM;
a pick changes output 2 only and is one undo step; the echoes follow what
is recorded.

**Wrong if:** a scene pass on SYSTEM, a pick that moves output 1, or an
undo that takes two steps.

*(checks 344, 346, 349)*

#### L160. The glass's mutes, and hands through the effects

**Needs:** the rig (or the TV as a second window); hands in view.

**Do:** turn the glass output's picture mute off, then on; on OUTPUT tick
**hands through the effects** for output 2 and untick it; try the mute on
a migrated preset with hands through and on a preset with the hands in
the scene.

**Right if:** the muted glass shows the hands only; output 2 shows the
hands bent by the effects when ticked and looks like output 1 when not.
The two owner notes are for you to judge: a picture mute hides the
through picture, and on an in-scene preset it shows the ground and the
guide, not the hands layer.

**Wrong if:** a hitch when a mute flicks, a toggle that does nothing, or
hands left on a muted window.

*(checks 347, 348)*

#### L161. The canvas at distance; SYSTEM before and after

**Needs:** laptop; a build from before plan 35 for the comparison.

**Do:** press tidy on `party-trip` and read the canvas from a metre and a
half away; then note SYSTEM's frame time and rate on this build and the
older one.

**Right if:** the labels and hovers read without the ids, the areas run
MEDIA, SCENE, LOOK-BACK, EFFECTS, OUTPUTS left to right with no cable
running back but the capture's and a delay's, and the frame time is no
worse.

**Wrong if:** an id where a name should be, a cable doubling back, or a
slower frame.

*(checks 350, 351)*

#### L162. A library preset looks the same; a `/6` file on an older build

**Needs:** two Macs sharing a library, one on this build and one on a
plan 33/34 build; the copy.

**Do:** compare `party-trip`, `dial`, `displace-moo`, `glimmer-bug` and
`moo` on both builds; save `party-trip` untouched and diff it; save a
preset that needs the new vocabulary (a window set to "nothing") and try
it on the older Mac; then put both Macs on this build.

**Right if:** the pictures look as before; the new file says
`hyperspace.preset/6` and the older Mac refuses it, leaving it as it was.
(Row 394, 2026-10-25: every re-save is `/6` now — the untouched one and the
three `/5` presets too — so the older Mac refuses those as well; L168.)

**Wrong if:** a look that moved, a changed file, or the older Mac opening
the `/6` file.

*(checks 345, 352)*

## Plan 34: feedback (L163–L167)

Plan 34's tests: **five fixtures** (`delay-faces`, `delay-trails`,
`echo-faces`, `resize-faces`, `resize-crop`) and **40 goldens** in
`tests/golden/frames/` (24 of them in plan 35's 741, the other 16 make
757); a delay, an echo or the dream is a `/5` word and the resize's
fixtures are `/6` wired frames. Run L163–L167 on the same build as
L158–L162, starting from a new preset (L158).

#### L163. The infinite mirror, an empty delay, trails

**Needs:** laptop; the copy; branch `plan-34-feedback` (PR #236).

**Do:** on a new preset, pick the scene starter; add a `delay` and wire
`scene → delay.image`, `delay → shape.faces`. Watch the faces, then delete
the cable into the delay and wait a second, then wire it back. Then build
the trails graph: `delay → zoomblur.2 → palette.2` (val slice to 0.6),
`scene` and `palette.2` into a `composite.2` set to add, and `composite.2`
into both `delay.image` and `output.all.image`.

**Right if:** the faces show the shape within the shape; with the cable
deleted they show their pattern, not black, and the mirror comes back when
it is wired; the trails stream toward the centre, fade within a few frames
and stop when the shape stops, with nothing sticking or burning to white.

**Wrong if:** a refusal, black faces after the delete, a frozen picture,
a trail that never fades, or no trail at all.

*(checks 332, 333)*

#### L164. A loop refused in words; an echo on the faces and at the hands; the dream

**Needs:** laptop; the copy; the dream worker for the last step; the TV
for a second window.

**Do:** drag `scene` onto `shape.faces`; then through a `delay`; then
`wobble` onto `acid`'s `aux` after `acid → wobble`. Add `echo.4` and wire it
to `shape.faces` with the look-back off; change `dream.gap` and
`dream.res`. Put the look-back on and wire `echo.1` to an output's
`hands`. Add `dream` and wire it to `shape.faces`, with and without the
worker.

**Right if:** each loop drag goes red with words that say to wire it
through a delay and changes nothing; through a delay it lands; the echo
shows the shape from four captures back with no wake, moves with
`dream.gap`, goes back to the pattern for a few commits after `dream.res`
changes, and at the hands is one capture old; the dream says "no dream
worker: reads nothing" without its worker.

**Wrong if:** a loop that lands green and then sits dormant, an echo that
freezes, an echo that shows the frame being drawn, or black faces for the
dream.

*(checks 334, 335, 336)*

#### L165. A resize into a delay; a resize before an effect; a window resize mid-feedback

**Needs:** laptop; a clip on channel A; the copy.

**Do:** wire `scene → resize → delay → shape.faces` with the resize at
size 64, square, nearest; route an LFO to `resize.crop_w`, `crop_h` and
`crop_x`. Then wire `channel.a → acid.2 → shape.faces`, read `acid.2` on
SYSTEM, and put a resize (256) before it. Last, drag the windows' edges and
change the render cap during the mirror, and route an LFO to
`resize.size` for a minute.

**Right if:** the faces show pixelated feedback that zooms and pans
smoothly under the LFO with no hitch; `acid.2`'s line drops with the resize
before it; a window resize or a cap change shows no black flash and no
error; with `resize.size` stepping, the picture changes size at each step
and SYSTEM stays steady.

**Wrong if:** a flash or hitch as the crop moves, soft pixels with
nearest, no drop in `acid.2`'s line, or a frame time that keeps climbing.

*(checks 337, 338, 339)*

#### L166. The frame cost of a delay, a resize and echoes

**Needs:** laptop, then the rig; take L161's numbers in the same sitting.

**Do:** note SYSTEM's frame time and rate, then run the mirror at the
render cap and again with a resize (256) before the delay, then four
echoes on the faces; write down `delay(write)`, the resize's line and the
frame time each time.

**Right if:** the delay costs less at 256 than at the cap, the resize has a
line of its own, the four echoes' cost can be read off SYSTEM, and the
laptop's rate holds. Write the numbers down.

**Wrong if:** a delay at 256 that costs as much as one at the cap, or a
hitch from a wired but unread node.

*(check 340)*

#### L167. A delay saved on this build, opened on a plan 33 build

**Needs:** two Macs sharing a library, one on a plan 33 build; the copy.

**Do:** on this build load the factory frame, wire a delay in a loop (L163)
and save it under a new name; read its `schema`; open the library on the
plan 33 Mac; then put both Macs on this build.

**Right if:** the file says `hyperspace.preset/6` (row 394: every save
is) and the plan 33 build refuses it, leaving it as it was; with both Macs
on this build it opens on both.

**Wrong if:** the file says `/6` for a frame that needs nothing of plan
35's, or the plan 33 build crashes or refuses it.

*(check 341)*

## Row 394: the library on the newest schema (L168)

The owner, 2026-10-25: old schemas get no long-term support — both Macs
always run the newest build — so every save is `hyperspace.preset/6`, and
the library is moved there once with `tools/migrate_library.py`. On
`preset-schema-6`.

#### L168. The library migrated to `/6`; both Macs on this build

**Needs:** both Macs on this build, sharing the library (`[library] path`).

**Do:** on one Mac, `uv run python tools/migrate_library.py` (a dry run:
it writes nothing) and read the report; then add `--apply` and note the
backup folder it prints. Let the cloud sync. Open `glimmer-bug`, `moo`,
`reeeeeeeel`, a macro preset and a few others on both Macs; save one
untouched; run the dry run again.

**Right if:** every preset is listed `→ 6`, `picture: same`, `fixed point:
yes`; after `--apply` every preset file says `hyperspace.preset/6` under
its own name, each looks as before on both Macs, the untouched save leaves
the file's bytes as they were, and the second dry run leaves every preset
untouched.

**Wrong if:** a preset in the "not written" list, a look that moved, a
renamed or missing file, or a `/6` that changes on an untouched save.

*(check 353)*

## Plan 36: the WYSIWYG graph (L169-L173)

Plan 36's tests: the fast tier is 3,941 passed (2 skipped) and the goldens
128 passed over 757 pictures, nine of them re-recorded (hand check 369 and
register rows 405, 406, 408, 414); `tests/test_plan36_bus.py`,
`tests/test_plan36_lookback_dream.py`, `tests/test_graph_starters.py` and
`tests/test_graph_preset_only.py` are its own. A new preset is no longer
black: L158 above (check 342) describes the plan 35 build, and L170 is its
replacement. The checks are 354-369 (group AG); a `/7` file is refused by an
older build, so L173 is last.

#### L169. The quick wins; rewire output 1; cut a bus cable; All outputs stays put

**Needs:** laptop; the TV for two windows; the copy; a trackpad for the pan.

**Do:** on GRAPH, add nodes from the right-click menu, drag nodes about,
turn **output behind** on, scroll with two fingers and with ⌘. Then load
`party-trip`, drag another picture onto `output.1.image`, and mute the hands
on one window. Delete the `output.all.image` to `output.2.image` cable, save,
reopen, undo, and drag it back from All outputs' pin. Press **new** and drag
All outputs somewhere else.

**Right if:** nodes appear where you click and stay where you drop them;
the output shows behind at the canvas scale; two fingers pan and ⌘ zooms;
rewiring output 1 changes only output 1's image; a cut bus cable empties
that port and survives a reopen; undo and the pin bring it back; All
outputs stays where you dragged it.

**Wrong if:** output 1's hands or guide stay laid over the new picture
without a cable, a cut returns by itself, or All outputs snaps back.

*(checks 354-361)*

#### L170. A new preset shows a shape; each starter

**Needs:** laptop; the copy; a clip for the backdrop starter.

**Do:** press **new**; undo. Then pick each starter from the canvas menu:
scene chain, tracers, tracers + dream, dream on a picture, a channel to the
backdrop, undoing after each; right-click a picture cable for the tracers
and dream ones.

**Right if:** the new preset shows the shape on both windows with the
factory's values; each starter is one undo step, put at the pointer, every
node and cable visible.

**Wrong if:** a black window, a value left over, or a starter that wires
something you cannot see.

*(checks 362, 363)*

#### L171. Tracers without the dream; the dream alone; `party-wake` live

**Needs:** laptop; the copy; the dream worker on (`[dream] enabled`); a
clip.

**Do:** with the tracers starter, watch the dream worker; add a dream and
switch `dream.on` off and on; then put a dream on a channel with no
look-back and try a second dream; load `party-wake` and compare its look
with how it looked on `/6`.

**Right if:** the worker is idle with no dream on; the dream refreshes on a
channel alone; the second dream is refused in words; `party-wake` is
recognisably the party look (it is known to differ: register row 412).

**Wrong if:** the worker busy with no dream on, or a dream that never
refreshes.

*(checks 364-366)*

#### L172. Preset only; the nine re-recorded goldens

**Needs:** laptop, the copy; the gate Mac for the pictures.

**Do:** load `party-trip`, open GRAPH, read `· N hidden`, turn **preset
only** off and on; note group nodes and the camera. Open the nine
re-recorded goldens (check 369 lists them).

**Right if:** only the preset's nodes, what is cabled to them and the
windows are drawn, nothing moves on toggle; each golden is what its wiring
draws.

**Wrong if:** a node you need is hidden, or a golden shows hands where the
mute is on.

*(checks 367, 369)*

#### L173. The libraries migrated to `/7`; both Macs on this build

**Needs:** both Macs on this build, sharing the library.

**Do:** as L168 with `/7`: the dry run, `--apply` (note the backup folder),
let the cloud sync, open a handful of presets on both Macs, save one
untouched, run the dry run again.

**Right if:** every preset is listed `→ 7`, `picture: same`, `fixed point:
yes`; every file then says `hyperspace.preset/7` under its own name; the
untouched save changes nothing; the second dry run leaves all untouched.

**Wrong if:** a preset skipped, a look moved, a file lost, or a `/7` that
changes when saved untouched.

*(check 368)*

## Plan 37: nodes as pictures, and the faces (L174-L178)

On GRAPH, a node that makes a picture is now drawn as that picture: a
small, live image under its title. The app only makes these images for
the nodes you can see, so panning or hiding nodes makes them cheaper.

Plan 37's tests: the fast tier is 4,035 passed (2 skipped) and the
goldens 128 passed, with none of the 757 pictures moved.
`tests/test_thumbnails.py`, `tests/test_graph_hover.py`,
`tests/test_graph_areas.py` (the backward-wire sweep) and
`tests/test_faces_map.py` are its own.

The face patterns are not cut yet. The owner picks which stay (L177),
and a later build drops the rest. The checks are 370–376 (group AH);
register rows 417–429 and 460.

#### L174. Every node shows its picture; the tint switch

**Needs:** laptop; the copy.

**Do:**
1. Load `party-trip` and open GRAPH.
2. Look at each node: the clip or camera, the pattern, the scene, the
   effects, the composites, the look-back and the outputs.
3. On FX, move an effect's mix up and down.
4. Turn on **pictures · tint cables** at the right end of the GRAPH head
   and wait a second or two. Then turn it off.

**Right if:**
- Every one of those nodes shows a small moving picture, and an effect's
  picture changes as you move its mix.
- The shape node shows the scene, faintly. Output 1 shows the window, and
  output 2 shows its window without the hands.
- With the switch on, the red cables lean slightly orange out of
  yellow-green pictures and slightly pink out of blue-violet ones. They
  stay plain red out of red, cyan or grey pictures, and every one still
  reads as red.
- With the switch off, every picture cable is plain red again.

**Wrong if:** a black box on a node that is clearly drawing, an upside-down
or frozen picture, or a cable that looks amber (a trigger's colour) or
purple (a mask's).

*(check 370)*

#### L175. What the pictures cost; a hidden node stops being made

**Needs:** the show Mac; the copy.

**Do:**
1. With GRAPH closed, note the frame time on SYSTEM.
2. Open GRAPH and pan until about twenty picture nodes are on screen.
   Read SYSTEM again: the frame time and the line `thumbnails · N copied ·
   K repainted · M kept`.
3. Turn on the tint and read the frame time once more.
4. Turn **preset only** on (or pan nodes off screen) and read the line
   again after a second.
5. On a switch node, pick another input.

**Right if:**
- The show's frame rate holds with GRAPH open, with the tint on and off.
- N is about the number of picture nodes you can see, and it falls when
  nodes are hidden or off screen. M follows within a second.
- The node behind the input you left greys at once, goes black a second
  later, and comes back when you pick it again.

**Wrong if:** dropped frames with GRAPH open; a count that does not fall
when nodes go out of sight; a stutter only while the tint is on.

*(checks 371, 374)*

#### L176. Expand and collapse; hover a picture

**Needs:** laptop; the copy.

**Do:**
1. On GRAPH, expand an effect node with **+**, then collapse it.
2. Rest the pointer on the scene node's picture, then on an effect's, then
   on output 2's.
3. Rest it on a node's title.

**Right if:**
- Expanded, the picture sits above the ports. Collapsed, the node is just
  its title and its picture. Nothing overlaps.
- On a picture, a tooltip gives the node's lines, its size (such as
  `1920×1080 picture`) and `gpu … ms`, the same time SYSTEM shows for
  that node.
- On the title, the hover is as it was before.

**Wrong if:** the picture vanishes when expanded, nodes overlap, or no
tooltip appears on the picture.

*(checks 372, 373)*

#### L177. Pick the face patterns to keep; the FACES page after

**Needs:** laptop, then the show Mac; music (for METER, PULSE and SPEED).

**Do:**
1. Open `docs/plans/assets/37-faces/sheet.png` and `heart-sheet.png`.
   Each shows all 17 patterns on a shape, as a show draws them.
2. Play music on the FACES page to see the ones that move.
3. Name the patterns to keep. Then read `migration-map.md`'s "nearest
   kept" for the ones you drop, and say whether to renumber the patterns
   or keep the retired numbers (register row 417).
4. After the build that drops the others, open FACES, load each preset
   the map says used a dropped pattern, and turn the desk's pattern knob
   from end to end.

**Right if:**
- Before the build: you have a list, and the map's replacements read
  right to you.
- After it: FACES shows only the kept patterns, each preset that lost its
  pattern shows the nearest one and says so in its card, and the knob
  walks only the kept patterns.

**Wrong if:** a dropped pattern still on FACES, a preset on the wrong
pattern, or white faces.

*(check 375)*

#### L178. `acid-scene` draws forward

**Needs:** laptop; a scratch home with no `[library]` and no devices.

**Do:**
1. Copy `tests/fixtures/presets/acid-scene.json` into the scratch home's
   `presets/`, load it, and open GRAPH.
2. Follow the effect acid.2 from the scene into the look-back and on to
   the composite.
3. Drag acid.2 elsewhere and reload.

**Right if:** acid.2 sits in LOOK-BACK, left of the look-back, and every
cable out of it runs left to right. After the drag it stays where you put
it.

**Wrong if:** a cable curls back into the look-back, or a node jumps back
by itself.

*(check 376)*

## Plan 38: hold the projector (L179-L181)

Plan 38 lets the person at the laptop build the next look without the
room watching it being built. **hold** (the first chip on GRAPH's head)
freezes what every screen shows: the projector keeps the look it had,
still moving with the music, while everything you do afterwards appears
only behind GRAPH's nodes (the *preview*). A small red-framed **PROJECTOR**
picture in the canvas's corner shows what the room sees. **take** puts the
preview on the projector; **drop** throws it away. Its tests are in
`tests/test_hold.py` (32; the fast tier 3,990 passed, 2 skipped; no golden
moved). The checks are 377-383 (group AI); the desk buttons are A48 in
Part 2. These are best run with the projector or the TV as a second
screen, so you can see the room's picture and the laptop's at once.

#### L179. Hold, then build a new look behind GRAPH

**Needs:** laptop; the TV or the projector as a second window; the copy;
music.

**Do:** load `party-trip`, open GRAPH, press **hold**, then press **new**
on the PRESET strip. Wire shape → scene → All outputs, add an effect,
delete one of the old look's effects, and cut the cable from All outputs
into window 2. Open the node picker near the top-right corner. Save the
preview as a new preset.

**Right if:** the second screen keeps the `party-trip` look, effects and
all, moving with the music, the whole time; behind GRAPH's nodes you see
only your new look; the PROJECTOR inset shows the old look; the red
`HELD 0:0x …` line counts your changes and says "the graph changed".
(The inset covers the picker in its corner: that is known, say whether it
is in the way.)

**Wrong if:** the second screen changes at any step, goes black at
**new**, or loses an effect when you delete one on GRAPH.

*(checks 377, 378)*

#### L180. Take and drop

**Needs:** as L179, with the look-back on (trails).

**Do:** after L179 press **take**. Then note the preset's name and dot,
press **hold**, turn some knobs, rewire, load another preset and turn a
knob on it, dim the room, and press **drop**; then ⌘Z once. Last, hold a
look with an echo, load another preset, and press **take**.

**Right if:** **take** cuts the second screen to the new look in one
frame, with the trails carrying on. After **drop** the knobs, the canvas
and the preset's name and dot are back to what the projector shows, the
projector never changed, and the dim stayed; one ⌘Z brings the dropped
work back. The echo keeps trailing through the load and starts empty at
**take**. Say whether the cut feels harsh.

**Wrong if:** a black frame or a flash at **take**, a knob that stays
moved after **drop**, the dim undone by **drop**, ⌘Z needing two presses,
or the echo cut at the load.

*(checks 379, 380)*

#### L181. What a hold costs; a band on a held setting

**Needs:** the show Mac; music; a Syphon or NDI source if you have one.

**Do:** route a band to the brightness (`view.bright`). Press **hold**,
move the brightness on the panel, and turn the speed. Read the frame rate
on the SYSTEM page with GRAPH open and with it closed. Wire a Syphon or
NDI input into the preview.

**Right if:** the projector keeps its brightness and still pumps with the
band, the preview shows the new brightness pumping too; the speed turns
both (that is by design) and is not counted on the red line. The frame
rate drops a little with GRAPH open and not at all with it closed. The
live input shows in the preview (a stutter is fine) and stays smooth on
the projector.

**Wrong if:** the projector stops pumping or jumps to the new
brightness, the frame rate falls with GRAPH closed, or the projector's
live input stutters.

*(checks 382, 383)*

## Plan 39: vision (L182-L188)

Plan 39 lets a picture be cut into its foreground and its background:
a **segment** node takes any picture (a camera above all) and puts out the
person (`segment.fg`), the room without them (`segment.bg`) and the
person's shape as a mask (`segment.mask`). A **matte** turns any picture
into a mask (its bright parts, its coverage, or a colour), a **cut** cuts a
picture by a mask, and **edges** is a new effect that draws a picture's
outlines. A mask is a purple cable; wired straight into a window it shows
white where it passes and black elsewhere. On `plan-39-vision`; run
`uv sync` first (it adds Apple Vision's Python wrapper). The first time a
camera opens, macOS asks whether the terminal may use it: allow it. A
preset with a segment, matte or cut shows black on an older build, so
**both Macs run this build before such a preset is shared**.

Its tests: the fast tier is 4,105 passed (2 skipped) and the goldens 136
passed over 789 pictures, 32 of them new and 8 re-recorded (the two
backdrop fixtures, for the honest cut-through: L188). Its own files are
`tests/test_fx_edges.py`, `tests/test_graph_masks.py`,
`tests/test_graph_cut.py`, `tests/test_segment.py`,
`tests/test_graph_segment.py` and `tests/test_plan39_graph.py`. Two tests
run the real models once each on a made-up frame; they are in the `live`
tier, so `uv run pytest -q` leaves them out: run them with
`uv run pytest -q --all tests/test_segment.py` (Vision only on a Mac). The
checks are 384-393 (group AJ). Find the new nodes on GRAPH's right-click
menu: **media ▸** segment, **masks ▸** matte and cut, and starters ▸
**cut-out**.

#### L182. A webcam cut by person: you over the shape, then the room with your hole

**Needs:** the show Mac (or the laptop) with a camera; the copy.

**Do:** put the camera on channel a (MEDIA). On GRAPH right-click empty
canvas → starters ▸ cut-out. Stand in front of the camera. Then rewire the
segment's `bg` pin into the composite's `over` instead of `fg`; then wire
the segment's `mask` pin to output 2. Step `segment.quality` through fast,
balanced and accurate, watching the edge, the node's rate and the SYSTEM
page's frame time. Turn `segment.on` off and on. Use the starter a second
time, then undo. If plan 38's hold is on this build: HOLD, New, turn a knob
on the segment, DROP.

**Right if:** you stand over the turning shape with the room gone, the cut
on you (not upside down, not beside you) a frame or two behind; the node
says `256×144 · Vision fast · a frame or two late · ~30 fps`; `bg` shows
the room with a person-shaped hole and the shape through it; output 2
shows your white silhouette; each quality level gives a finer edge and the
frame time does not move; off shows the picture unchanged; the second
starter's nodes and cables are all drawn and one undo removes them; while
held the projector does not change.

**Wrong if:** the cut is upside down, squashed or beside you; the node
waits for ever or shows an error (check `uv sync` and the camera
permission); the frame time rises with the quality; a knob moves the
projector while held.

*(checks 384, 385)*

#### L183. The edge and the flicker, with a dancer

**Needs:** L182's set-up on the projector; a dancer.

**Do:** with the dancer moving, raise `segment.feather` from 0 to 8, then
`segment.smooth` from 0 to 0.6; then smooth to 0.95, have the dancer step
out, and wait.

**Right if:** the feather softens the edge and hides its steps; smooth
calms the flicker along the edge, at the cost of a trail on fast moves; at
0.95 the dancer still fades out completely after some seconds.

**Wrong if:** the feather does nothing, or smooth leaves a frozen ghost
where the dancer stood.

*(check 386)*

#### L184. Motion on a still camera, and the party light

**Needs:** a camera on a tripod pointed at the room; L182's wiring; a party
light.

**Do:** set `segment.mode` to motion. Walk through the frame; stand still
for three seconds (`segment.learn`); move again; raise `segment.sense` a
little. Then sweep the party light across the room.

**Right if:** the walker is cut out and the still room is gone; standing
still you fade into the room over about three seconds and come back at
once when you move; more sense ignores small flickers; the swept light
counts as movement until it has been still for a moment (expected: motion
cannot tell light from a person).

**Wrong if:** everything stays cut out, or nothing ever is.

*(check 387)*

#### L185. A still as a mask; a mask on a window

**Needs:** the laptop; the copy; a still with a clear bright shape in the
media folder.

**Do:** load the `cut-out` fixture through a scratch library
(`tests/fixtures/presets/cut-out.json`), or build it: the still on channel
a, from masks ▸ a matte and a cut, and a composite; wire `channel.a →
matte.image`, `matte → cut.mask`, `scene → kaleido.image`, `kaleido →
cut.image`, `cut → composite.over`, `scene → composite.under`, `composite →
All outputs`. Turn `matte.key`, `matte.soft`, `matte.feather`; set
`matte.from` to chroma and turn `matte.hue` onto a colour in the still.
Turn `cut.amount` to 0.5; turn on `cut.invert`; unwire the mask. Then wire
the matte straight into All outputs, look at its cable, and try to wire
the still straight into the cut's mask.

**Right if:** the kaleidoscope shows only where the still is bright (or
the keyed colour), the right way up, with the shape showing through its
empty parts; half amount brings it back at half strength elsewhere;
invert swaps the two; no mask shows the kaleidoscope everywhere. The
matte on a window is a soft white shape on black filling the window, its
cable purple into the red pin; the picture into the mask is refused with
"put a matte between".

**Wrong if:** the cut area is upside down, mirrored or stretched against
the still, black inside the bright shape, or a knob does nothing.

*(checks 388, 389)*

#### L186. Edges on the shape, on the camera, and into a cut

**Needs:** the laptop or the projector; a camera for the second part.

**Do:** wire `scene → edges → All outputs` and switch edges on. Sweep its
threshold, raise its glow to 4, try its three colours. Then feed it the
camera instead. Last, wire `edges → matte → cut.mask` with the pattern
into the cut's picture.

**Right if:** the shape's lines draw as thin white outlines on black; the
threshold thins them to only the strong lines; the glow adds a halo; the
direction colour turns as the shape turns; the room's door frames and
people's outlines draw steadily from the camera; the pattern shows only
along the lines.

**Wrong if:** flat areas are not black, the frame's border draws as a
line, or the camera's picture sparkles everywhere at the default
threshold.

*(check 390)*

#### L187. Two cameras, two segments; unplug a camera

**Needs:** the show Mac; two cameras.

**Do:** camera 1 on channel a, camera 2 on channel b; add two segments
(media ▸ twice), one fed by each, each `fg` over the shape on its own
output; watch the SYSTEM page's frame time. Then unplug camera 1, plug it
back, delete a segment, and quit.

**Right if:** both cut their own person, each node shows its own rate,
the frame time stays within the show's budget; unplugged, the node says
`no frame on channel a: its picture through, whole` and nothing stalls;
plugged back, the cut returns within a second or two; deleting a node and
quitting do not hitch.

**Wrong if:** one segment starves, the frame time spikes, the app stalls
or the last cut stays frozen over a black channel.

*(checks 391, 392)*

#### L188. A half-transparent face over a bright picture, cut-through on and off

**Needs:** the projector (an opaque window); a bright still; the gate Mac
for the eight re-recorded goldens.

**Do:** put the still on channel a; wire `channel.a → composite.under`,
`scene → composite.over`, `composite → All outputs`; faces on, lines and
points off, a pattern with see-through fills. Flip `view.cut_through` a
few times. Again with the still on the backdrop and `scene →
backdrop.scene` wired. Open the eight re-recorded goldens
(`backdrop-still` and `media-chain-backdrop`, the `present` states).

**Right if:** nothing changes when you flip it: the faces sit over the
white at their own strength, their colour readable; the goldens show the
same.

**Wrong if:** the faces wash out toward white, or brighten with the switch
on.

*(check 393)*

## Plan 40: patches (L189-L194)

Plan 40 lets you keep a little machine you built on GRAPH and drop it into
any other preset. Select some nodes and **Group** them: they fold into one
box whose plugs are the cables that cross its edge (`+` opens it again).
**Save as patch…** writes that group, with its knobs and hand moves, to its
own file (`patches/` in the library). The **patches** chip on GRAPH's head,
or right-click → **spawn ▸**, puts a copy into whatever preset is loaded,
under new names so nothing clashes; its plugs start unplugged unless you
drop it on a cable, which splices it in. If its knob is already used by the
preset, a sheet asks which one wins. The app also says which devices a
preset wants that are not plugged in, and says so again when one arrives.
The old fx "module presets" are gone; the FX page stays.

Run these on the copy (`export HYPERSPACE_HOME=~/Hyperspace-try`) with the
`[library] path` line in the copy's `config.toml` commented out, so a
saved patch stays on the copy and never reaches the shared Drive folder. A
preset with a group is a new file version (`/8`) that an older build will
not open, so **both Macs run this build before such a preset is shared**.
Its tests: the fast tier is 4,320 passed (2 skipped), the goldens 144
passed with none moved; its own files are `tests/test_patches.py`,
`tests/test_graph_groups.py` and `tests/test_device_wants.py`. The checks
are 394-401 (group AK); the two with the APC40 are A49 and A50 in Part 2.

#### L189. Group some nodes, open them, ungroup them

**Needs:** laptop; the copy.

**Do:** load `party-noita`, open GRAPH, drag a box around `scene`, `warp`,
`doublevision` and `fractals`, right-click one → **group 4 nodes**. Press
the group's `+`, drag its title bar, drag one member far out of the tinted
box, press ⌘Z; press `−`, drag the folded box, ⌘Z. Drop a cable on the
folded box's plain `in` stub. Right-click it → **ungroup**. Save the preset
as a copy and open the file in a text editor.

**Right if:** `scene` is left out ("scene is the frame's; left out") and
one box "group 1" appears with a picture in, a picture out and a row for
each knob or hand that drives one of the three; nothing changes on the
projector at any step; `+` shows the three where they were inside a tinted
box; the members follow the title live; the dragged-out one leaves and one
⌘Z brings it back; the stub drop goes red with "group 1 is folded: drop it
on one of its pins, or open it (+)"; ungroup changes nothing but the box.
The saved file says `hyperspace.preset/8` and has a `groups` line.

**Wrong if:** `scene` joins the group, the picture changes, members jump
only when you let go, one ⌘Z undoes two things, or an empty menu opens on
the stub.

*(check 394)*

#### L190. Save a group as a patch; spawn it into a new preset; wire as saved

**Needs:** laptop; the copy.

**Do:** group `warp`, `doublevision` and `fractals` in `party-noita`,
select the group and press **save as patch…** on its side panel; name it
"noita core" and save. Look in `~/Hyperspace-try/patches/`. Press **new**,
press **patches** on GRAPH's head and read the list, then right-click the
canvas → **spawn ▸ noita core**. Drag `scene` onto the box's `in` plug and
its `out` plug onto All outputs; then ⌘Z three times. Press **new** again,
spawn it, and press **wire as saved**. Try to save another group under the
same name. On PRESETS, open **patches**, rename it, then × it.

**Right if:** only `noita-core.json` is new in the folder; the list shows
its note and "in: picture · out: picture · wants: …"; the spawn is one
folded box at the click with two plugs reading "open (was scene)" and
"open (was tripcolour.image)", and nothing changes on screen until you
plug it; plugged, the picture is noita's middle; three ⌘Z remove the two
cables and then everything the spawn brought. **wire as saved** plugs the
scene and says "no node tripcolour" for the other. The second save is
refused ("a patch named noita core exists …"). A click on a name in the
PRESETS fold does nothing; rename and × work.

**Wrong if:** a preset or `bindings.json` changes when you spawn; the
spawn takes more than one ⌘Z; wire as saved plugs into a socket that
was already in use; the second save overwrites the first.

*(check 395)*

#### L191. Drop a patch on a cable

**Needs:** laptop; the TV or the projector as a second window; the copy;
the "noita core" patch from L190.

**Do:** load `party-trip`, open **patches** on GRAPH's head and drag
"noita core" out of the list over the canvas, then let go on the cable
from `scene` into `plasma`. Watch the second screen. Press ⌘Z.

**Right if:** while you drag, the cable under the pointer lights; on
release the three effects sit between `scene` and `plasma` and the second
screen shows them; one ⌘Z puts the cable back.

**Wrong if:** the list closes as soon as you drag, no cable lights, or the
splice takes two ⌘Z.

*(check 396)*

#### L192. A preset that wants a Leap on a rig without one

**Needs:** laptop with no hands device in its `config.toml`; the copy; the
acid wash patch (A49 copies it in).

**Do:** load a preset with acid wash in it (A49), read the group's box and
GRAPH's head. Press **new** and spawn acid wash; read the head's line.
Then spawn it into `party-acid` and answer **keep all existing**, Spawn.

**Right if:** the box says "waits for leap (not in this rig): right hand
y" and the grey Leap placeholder is drawn as before; both spawns end their
line "waits for leap (not in this rig): right hand y", and the second
does not mention K1.

**Wrong if:** a spawn says nothing about the Leap, or names K1 after you
kept it for the preset.

*(check 399)*

#### L193. The fx module presets are gone; the FX page is not

**Needs:** laptop.

**Do:** PRESETS → **more · module presets**. Open the FX tab. Load every
factory preset. Load one of your own presets from before this build that
named an fx module, and save it.

**Right if:** no fx entry under module presets; the FX page is as before
except the small strip under its "effects" title (name, arrows, save,
as…, reset) is gone; no preset puts a note in the footer; your old preset
loads quietly and saves without the fx label.

**Wrong if:** an fx strip or fx entry is still there, or a load says
anything about fx.

*(check 400)*

#### L194. The same patch twice in one preset

**Needs:** laptop; the copy; "noita core" from L190.

**Do:** load `party-noita` and spawn "noita core" twice: Spawn at the
first sheet, **keep all existing** at the second. Hover both groups. Save,
load another preset, load it back. Then press **new** and spawn it twice.

**Right if:** two boxes, "group 1" and "group 2"; their hovers say `warp →
warp.2 …` and `warp → warp.3 …`; the second says "n rows kept by the
preset", still after the reload. In the new preset the first copy keeps
the plain names and the second gets `.2`.

**Wrong if:** two copies share a name, or the kept rows are gone after
the reload.

*(check 401)*

#### L195. A macro wired from the param menu moves the param

**Needs:** laptop.

**Do:** load any preset, open GRAPH and the shape's panel. Right-click the
4D depth slider → **Route from ▸**, look under **LFO ▸**, **envelope ▸**
and **macro ▸**, pick **macro 2**. Open the macro 2 node and turn its knob
0 → 1 → 0. Right-click the slider → Route from ▸ macro ▸ again, then ⌘Z.
Right-click the look-back's **gap** slider, then the BPM on the audio page.

**Right if:** Route from holds just the three submenus; macro ▸ names the
eight knobs (a labelled one by its label). The slider follows the knob —
where it sat at 0, the top of its fader at 1 — and ROUTING's subscriber
line reads `from <where it sat> to 1.00`. Macro 2 is checked the second
time and a click does nothing; one ⌘Z takes the cable and the "macro 2"
label back together. The gap slider (no lane may drive it) offers only
macro ▸; the BPM has no Route from.

**Wrong if:** a flat list of LFOs and envelopes; `from` equal to `to` on
the new line; the knob moves nothing; macro ▸ on the BPM.

*(check 402)*

## One tier: the PRESETS page (L196; plan 41)

#### L196. The PRESETS page is the library

**Needs:** laptop, the copy (on the Drive library).

**Do:**
1. Open PRESETS. Read it top to bottom: the strip, the list, the patches
   fold, the show line.
2. Click a preset in the list. Click **rename** on another, type a name,
   press Enter. Click **×** on a third.
3. Open **trash (n) ▸** at the foot of the list and take the third back.
4. Open the **patches** fold; rename one, × one.
5. Open **open ▾** on the show line, then **as…**, name a show, and
   **new**.
6. On the desk press F1–F8 and a clip-row pad; hold an empty pad.

**Right if:** (1) the strip reads ◀ name ● ▶ · new · save · as…; the list
fills the page with every preset in the library and no others; the show
line reads "show · the desk's pads, the session, the rig's wires", then
the show's name, a red dot while unsaved, **open ▾**, **save**, **as…**,
**new**. Nothing reads "starts on", "F1–F8", "show hidden", "factory" or
"save copy", and no row is dim. (2) the click loads it and the strip
names it; the rename sticks and the shows that name it follow; the × puts
the file in the trash. (3) it is back in the list. (4) the same chips, no
pick. (5) a new show is called `untitled` with an empty bank. (6) the
pads still load and save; holding an empty pad saves into it.

**Wrong if:** a pill row, a "starts on" picker, a preset drop-down or a
module-preset fold on the page; a row that cannot be renamed or deleted;
a pad that loads nothing.

**Changes:** presets in your copy (renamed, trashed and restored), a new
show file; remove them with × if you do not want them.

*(check 403)*

## Dropping a node on a cable (L197)

#### L197. Drop a node on a cable

**Needs:** laptop; a preset with two effects in a row (for example
`lookback → acid → wobble → All outputs`).

**Do:**
1. Right-click the canvas and add an effect. Drag it slowly over the
   cables, including the shape's geometry cable, and let go with
   `acid → wobble` the bright one.
2. Drag `wobble` over `lookback → acid` and let go without any key.
3. Drag `wobble` again, hold ⌘, and let go over `lookback → acid`. Press
   ⌘Z.
4. Wire an LFO through a Smooth modifier into a param, select the Smooth
   and press Delete.
5. Hold Option and drag a box across three cables; press Delete, then
   ⌘Z.

**Right if:** (1) while dragging, every cable the node covers is faint
gold and the one nearest its middle thick gold, the geometry cable red, and
words beside the pointer say what letting go will do; let go, the effect
is in the run; all the while its border is faint gold, solid gold when a
cable is lit. (2) from the first movement the words say "hold ⌘ …",
nothing lights, the border stays as it was, and the node just moves.
(3) with ⌘ the node's border goes gold, its own cables fade
and a thin gold line shows how the run will close up; let go, `wobble`
moves before `acid`; one ⌘Z undoes it. (4) the LFO drives the param
directly. (5) the box picks cables, Delete removes them, ⌘Z restores them.

**Wrong if:** a drop does something the drag did not show, or the drag
shows something and the drop does nothing; ⌘ does not lift the node; the
param stops moving after (4).

*(check 404)*

# Part 2 — tests that need hardware

## (a) The APC40

Plug the APC40 in by USB before launching. On the desk: the 8 × 5 grid
of *pads* is top-left, with a column of scene buttons on its right; under
it the *clip-stop row*; along the bottom nine faders (*track faders* and
the master) and, bottom right, the *crossfader*. On the right are the
eight *track knobs* (top) and the eight *device knobs* (bottom), the
*SHIFT* button, TAP TEMPO, NUDGE − / +, and the small buttons
QUANT, OVERDUB, METRONOME and DETAIL. The *on-screen desk* in the
control window's bottom-left corner names each control with a short code
(K1–K8 track knobs, D1–D8 device knobs, S1–S8 faders; see *glyph*).

#### A1. Knobs follow the app when it changes a value — run first

**Needs:** APC40.

**Do:** house show (PRESETS → show ▾ → `house`), F1 (BIG BLUE WAVE,
brightness 1.25×). Turn track knob 1 (Brightness, K1) to about a quarter.
Press F2 (EMBER ORBIT, brightness 1.5×). Turn K1 a little.

**Right if:** the knob's light ring jumps to the new brightness at once,
and the next turn carries on from there — no jump back toward a quarter.

**Wrong if:** the first turn snaps brightness to where the knob was. Then
the desk's knobs keep their own position and ignore the app; note it and
skip A4's knob half.

*(check 31)*

#### A2. The desk wakes up; knobs, rings, faders

**Needs:** APC40.

**Do:**
1. `uv run python tools/midi_probe.py`: move controls (it prints each
   message and lights the desk); Ctrl-C.
2. Launch, ANALYZER page. Turn the track knobs; turn the device knobs;
   latch SHIFT and turn them again; move a track fader; pick another band
   with the track-select buttons and turn a device knob (SHIFT latched).
3. Move a fader while the app's value is elsewhere (drag it on screen
   first).

**Right if:** at launch the desk's lights come on in their layout and
the knob rings light; track knobs move the VIEW page's settings; without
SHIFT the device knobs do the preset's job (on TUMBLE D1–D4: 4D depth,
camera yaw, camera pitch, face pattern; D5–D8 dark and dead); with SHIFT
latched they move the open band's settings; with SHIFT latched a track
fader moves that band's drive (without SHIFT the track faders are the
preset's, and dark on every factory preset); after changing band the ring redraws and
the knob carries on from it; a fader whose value moved does nothing
until it passes that value, then follows. The on-screen desk lights each
control as you use it.

**Wrong if:** no lights (check `[midi] port`); a knob moving the wrong
setting; a fader jumping instead of catching.

*(check 10)*

#### A3. SHIFT latches and lights

**Needs:** APC40.

**Do:** press SHIFT once and let go; try the knobs; press SHIFT again.
Then hold a filled pad in row 4, press and release SHIFT while holding
it, let go of the pad.

**Right if:** SHIFT's light stays lit; the device knobs move the open
band (ANALYZER page); track knobs 1–5 move the hands' Steadiness,
Response, Catch, the selected axis's Return (HANDS page) and the BPM;
6–8 are dark and do nothing. SHIFT again: light off, the preset's
meanings back. Holding the pad: one preset load, nothing else.

**Wrong if:** lit only while held; a knob keeping its preset job under
SHIFT; a second action on release.

*(check 34)*

#### A4. Switching layer: knobs jump, faders wait

**Needs:** APC40; A1 done (if A1 was wrong, note it and skip the knob
half).

**Do:** turn K1 (Brightness) to a quarter; latch SHIFT (K1 is now
Steadiness); turn it a little; SHIFT back. Then ANALYZER page: drag SUB's
drive to the top with the trackpad, latch SHIFT, and move track fader 1
up from the bottom.

**Right if:** each switch moves the ring at once to that layer's value,
and the next turn carries on from the ring. The fader does nothing until
it passes the new value, then follows.

**Wrong if:** a knob snapping back to where it physically was; a fader
jumping.

*(check 35)*

#### A5. Rings show the setting, lights show the state

**Needs:** APC40; music playing.

**Do:** house show, F1 (BIG BLUE WAVE). Watch the track-knob rings.
Press the scene buttons for points, lines, faces and rotate. Then on the
ROUTING page add a route from `lane:0` to Faces, **push**.

**Right if:** the rings sit at the setting and do not flicker with the
sound; the scene-button lights match the switches and flip at once when
pressed; with the route, the FACES light follows the sound while the
control window's tick box shows the setting underneath.

**Wrong if:** a ring chasing the sound.

**Changes:** delete the route.

*(check 11)*

#### A6. Tempo buttons and the pad grid

**Needs:** APC40; music or a metronome.

**Do:** load `lfo-breathe`. Tap TAP TEMPO four times on the beat and
press METRONOME on the "one". Press NUDGE + and NUDGE −. Press QUANT a
few times. Press pads in row 1; latch SHIFT and press pads in rows 2–3;
press a filled pad in rows 4–5; turn the cue knob; press STOP ALL.

**Right if:** as L20 (BPM right, a tap never jumps the swell); the
METRONOME light blinks on the beat; NUDGE moves the tempo nudge by 0.01
and the swell with it; QUANT steps to the next filled slot (empty ones are skipped); row 1 picks
presets 1–8; rows 2–3 with SHIFT pick a sound-band scene; rows 4–5 load
presets 9–24 (on both layers); the cue knob changes the shape; STOP ALL
resets every band to the selected scene, and a second press within 8 s
undoes that reset (the ANALYZER page's button says so meanwhile).

**Wrong if:** METRONOME's light steady; a button doing an older job (your
`bindings.json` kept an old line: it shows on the ROUTING page's session
section; delete it from the file by hand).

*(check 12)*

#### A7. The on-screen desk matches the real one

**Needs:** APC40.

**Do:** party show, F5 (TRIP), ROUTING page. Press H (or the APC40's
DEVICE ON/OFF) for the big drawing. Hold the APC40 beside the screen and
walk every control with the pointer. Turn D1. Latch SHIFT. Pick a row in
ROUTING's DESK section, read its code (say D4), find it on the drawing,
then on the desk, and turn it. Press DETAIL twice.

**Right if:** the drawing is the desk's face, every control in the same
place; each hover names the control the maker's way; every control lit
on screen is lit on the desk and every dark one dark, pads in the same
colours; D1's arc moves with its ring; with SHIFT, the ⇧ turns red, the
header says GLOBAL LAYER · SHIFT, D1–D8 and K1–K5 stay lit and K6–K8 go
dark — on the desk too; the row's setting moves. DETAIL shows and hides
the key legend like `/`, and its light is dark at launch. A click on a
drawn control picks it (A16); click again to let go.

**Wrong if:** a control drawn in the wrong place (note its code); lit on
one and dark on the other.

*(check 45, 69, 58)*

#### A8. Device knobs on each preset (on the copy)

**Needs:** APC40; the copy.

**Do:** F1 (TUMBLE): turn D1–D8. Then a house mood, TRIP, WAKE, ACID,
and from the list `hands-fx`, `hands-pinch`, `lfo-breathe`. Look at the
ROUTING page's DESK section on TUMBLE.

**Right if:** on TUMBLE, D1 is 4D depth, D2 camera yaw, D3 camera pitch,
D4 the face pattern (one pattern a step), each ring following; D5–D8
dark and dead, listed on ROUTING as "D5 unmapped — dark" … "D8", drawn
dark on screen; latching SHIFT lights them for the band settings and the
ROUTING header reads DESK LAYER: GLOBAL. A house mood has the same four; TRIP,
WAKE and ACID their eight; `hands-fx`: D1 FX mix, D2–D6 the Acid effect
(bend, twist, reach, breathe, speed), D7 4D depth, D8 yaw;
`hands-pinch`: D1 FX mix, D2–D3 hue cycle paint and spread, then depth,
yaw, pitch, pattern, D8 dark; `lfo-breathe`: D1 still "Breathe", then FX
mix, Plasma level, LFO 1 depth, depth, yaw, pitch, D8 dark. If TUMBLE is
white in the list (your own, saved earlier) its knobs stay as you saved
them — dark — and that is right. D4 changes nothing visible with faces
off.

**Judge:** which knobs you reached for and found dark or useless (K7,
Bitmap alpha, does nothing on a factory preset).

**Wrong if:** a lit knob moving nothing; one knob doing two things; D4
skipping patterns; an unmapped knob moving the band settings without
SHIFT.

*(check 36, 85)*

#### A9. One knob, two directions

**Needs:** APC40.

**Do:** load `lfo-breathe` (it starts with brightness 1×, speed 0.25×).
Turn device knob 1 ("Breathe") from bottom to top and back. ROUTING
page, MACROS section.

**Right if:** the picture brightens from 1× to 2× while the spin slows
from 0.25× to a crawl (about 0.06×), together, smoothly, and the LFO's
breathing of the effect mix deepens from nothing; MACROS shows knob 1
"Breathe" with three lines — two `base` lines (one runs the other way)
and one `depth` line naming the LFO's route.

**Wrong if:** both move the same way; nothing moves.

*(check 39)*

#### A10. Undo a knob turn, and a load from the desk

**Needs:** APC40.

**Do:** F5 (TRIP). Sweep D1 (FX mix) to the other end, wait, ⌘Z, turn D1
again. Latch SHIFT, move S1 a little, wait, ⌘Z. Unlatch, then press QUANT
and ⌘Z.

**Right if:** the mix and D1's ring return; the next turn carries on
from the ring; after the fader ⌘Z the drive is back, SHIFT still lit, and
S1 does nothing until it passes the value again; the QUANT load is one
⌘Z.

**Wrong if:** SHIFT dropping or every fader losing its hold; the ring
not following.

*(check 49, 50)*

#### A11. Undo a Learn and an Unbind

**Needs:** APC40.

**Do:** F5 (TRIP), ROUTING page. `ls -l <home>/presets`. Right-click
Brightness → **Learn desk**, turn D3. ⌘Z. Right-click a setting a desk
knob drives → **Unbind** (choose **both** if it has a route too); ⌘Z.
Delete a route with its ×; ⌘Z. `ls -l` again.

**Right if:** after the Learn the DESK section shows "D3 view.bright",
D3's old job is gone, and the footer line ends "; K1 let go"; ⌘Z gives
D3 its old job, K1 its row and the footer says "undid learn
view.bright", the unsaved dot as it was; after Unbind the ring goes dark
and ⌘Z brings row and ring back ("both" is one ⌘Z); the route returns
with its depth and gate; no preset file's time moved.

**Wrong if:** a row not back; a ring staying dark.

*(check 51)*

#### A12. OVERDUB is Home

**Superseded (2026-10-28):** the "set starts on to none" steps are gone: nothing on the panel sets "starts on", and no show ships with one (L196).

**Needs:** APC40. The laptop part is L33.

**Do:** party show (home TUMBLE). F5 (TRIP), change a few things, press
OVERDUB. ⌘Z. F7, latch SHIFT, press OVERDUB. Set "starts on" to none,
press OVERDUB; set it back. Right-click any setting → **Learn desk**,
press OVERDUB, then cancel the Learn from the footer.

**Right if:** OVERDUB is lit; it loads TUMBLE with its desk lit; ⌘Z
brings TRIP back with your changes ("undid home → TUMBLE"); under SHIFT
it loads TUMBLE too and SHIFT drops; with no "starts on" its light goes
dark and pressing it loads nothing; during a Learn it still loads the
start preset, says nothing, and the Learn stays armed.

**Wrong if:** OVERDUB dark or dead; something else under SHIFT.

*(check 54)*

#### A13. The crossfader is the master dimmer

**Needs:** APC40. The ghost-hand part of step 4 needs the hand camera
(leave it out without one); the glass part is D4.

**Do:**
1. Quit. Push the crossfader hard left. Launch.
2. Nudge it a little from the left.
3. Slide it all the way right, then back to the left.
4. F5 (TRIP), then F4 for the look-back, with the ghost hands on: set
   the crossfader half way.
5. Leave it at half; press F1, F5, OVERDUB; then move it.
6. Latch SHIFT and move it.
7. Quit at half and launch.

**Right if:** (1) full brightness; the OUTPUT page's first row, **Master
dim**, reads 100%. (2) nothing happens. (3) from the right end it takes
hold and dims smoothly to black at the left, the footer reading "dim
…%" in the warning colour and "dim black" at the end; back right, full,
and the reading goes. (4) the shape, effects, trail and ghost hands are
all half as bright. (5) it stays at half through each load and the next
move carries on from half. (6) it still dims. (7) full again.

**Wrong if:** dark at launch; black at the right end (the direction was
read from the maker's notes, never from the device — say so); a jump
when first touched; dead after a load; something not dimming; a line
under Master dim on the OUTPUT page (the graphics driver refused it).

*(check 55)*

#### A14. Hold an empty pad to save a new preset into it (on the copy)

**Needs:** APC40; the copy.

**Do:**
1. Party show. PRESETS page: right-click F8 → **free this pad (keeps the
   preset)**.
2. F5 (TRIP); change the look. Tap pad 8 of clip row 1 quickly.
3. Hold pad 8 of row 1; let go after the blinking.
4. Press pad 1, then pad 8.
5. Hold a filled pad (pad 2) for two seconds.
6. Free slot 10 the same way; change the look; hold row 4's second pad.
7. Latch SHIFT, free another slot and hold its pad.
8. Right-click F8 → **put preset here…** → NOITA.
9. Press one of the first seven clip-stop buttons (the row under the
   grid; the eighth is SAVE, A24).

**Right if:** (1) F8 reads "—" and the footer says "F8: cleared — NOITA
is still in the preset list". (2) the footer says F8 is an empty slot and
to hold its pad; nothing is saved. (3) after a little over half a second
pad 8 blinks for about 1.5 s and stays green; F8 reads **TRIP 2**, lit,
the PRESETS strip says TRIP 2 with no dot, the footer "saved TRIP 2 → F8",
and `<home>/presets/trip-2.json` exists. (4) your look is back. (5) pad
2's preset loads and nothing else happens: no new file, no blink. (6)
slot 10 gets the new preset ("→ slot 10"). (7) it saves the same way on
the SHIFT layer. (8) F8 is NOITA again and TRIP 2 etc. stay in the list;
**free this pad** is greyed on an empty slot. (9) nothing happens: the
row is dark and free for Learn.

**Not fails:** the on-screen desk does not blink the pad. If the desk's
lights never blink, note what they do; the footer line is the real sign.

**Wrong if:** a tap saving; a save over a filled slot or a file; a
clip-stop button saving.

*(check 56, 83)*

#### A15. Pad rows 4 and 5 are presets (on the copy)

**Needs:** APC40; the copy, with a preset on slot 12 (L3).

**Do:** look at the pad grid. Press row 4's fourth pad. Press an empty
pad in rows 4–5. Latch SHIFT and press another filled far pad. Turn the
cue knob. Right-click a setting → **Learn desk**, press a far pad.

**Right if:** row 1 has one green pad (the loaded preset) and amber on
the other filled slots; row 4's fourth pad is amber; empty ones dark;
the on-screen desk shows the same, amber at half strength with names.
The pressed pad turns green, the old one amber, the picture changes and
slot 12's button is lit. An empty pad: nothing loads, "slot 16: an empty
slot". Under SHIFT: same lights, it loads, SHIFT drops. The cue knob
steps through all 26 shapes (no pad shows the shape any more). During a
Learn the pad loads and the Learn stays armed.

**Judge:** whether amber can be told from green on the real desk — say
what you see.

**Wrong if:** no amber; a pad changing the shape (an old line in
`bindings.json`); nothing under SHIFT.

*(check 82)*

#### A16. Click a control, then a setting

**Needs:** APC40. The first real clicks this feature gets.

**Do:**
1. F1, ROUTING page. Click D6 on the drawn desk.
2. Open VIEW. Point at Speed, click. Turn D6. ⌘Z.
3. Click D6 again, open VIEW, wait 20 seconds without touching anything.
4. Pick D6 and click it again; pick it and click empty ground between
   controls; pick it and click the footer's line.
5. Press H, click D6. Click again without moving the pointer. Then move
   to Speed and click. ⌘Z.
6. Click SM (the master fader). Latch SHIFT, click K1.
7. SHIFT off: right-click Brightness → **Learn desk**, then click D7 on
   the drawing. ⌘Z.
8. Pull the APC40's cable and map D8 both ways (steps 1–2 and 7).

**Right if:** (1) D6 framed red; ROUTING's row list (not the page)
scrolls to D6's line, framed red; ROUTING not dimmed; the footer counts
down "D6 picked (20 s): click a param on any other page". (2) VIEW is
dimmed and takes no input except the click — page list and footer still
work; Speed is framed red with "click: put D6 on Speed"; the click says
"learned view.speed ← D6 (device knob 6) (into the preset); K2 let go",
Speed does not move, the page brightens; D6's ring lights and moves
Speed; K2 goes dark; ⌘Z undoes it. (3) the page comes back by itself:
"D6 let go — no click for 20 s"; any click restarts the count. (4) each
lets go at once. (5) the panel returns with VIEW dimmed; the second
click without moving maps nothing; after moving, the click maps. (6) S2:
"… is invariant (the session's): Audio drive", VIEW
not dimmed, ROUTING scrolls to it; K1 under SHIFT: "… on the global
layer … latch SHIFT off to map into the preset: Steadiness". (7)
"learned view.bright ← D7 (device knob 7) (into the preset); K1 let go",
K1 dark (▲ ▼ keep Brightness). (8) the same lines, the dot lit.

**Judge:** whether the dimming reads as "waiting for a click", whether
20 s is long enough, and whether you would rather the click opened
ROUTING.

**Wrong if:** the click moves the slider; nothing maps; the page never
returns; ROUTING's whole page scrolls; a map lands on SM or under
SHIFT.

*(check 70)*

#### A17. Knob smoothing

**Needs:** APC40.

**Do:** F3 (FIELD). SYSTEM page, under "midi": **Knob smoothing**. Turn
K8 (Zoom) slowly, then fast. Set smoothing to "off" and turn K8 slowly.
Try 50 ms and 200 ms. Latch SHIFT and move S1 (a band's drive), then
the crossfader; unlatch. Turn the cue knob,
press a pad.

**Right if:** it reads "80 ms" and the show's dot is clean; the zoom
glides, settles within a blink when you stop, the ring sits where your
fingers left it; a fast spin neither lags noticeably nor overshoots; the
ring never crawls backwards and the next turn carries on from it. Off:
the picture steps, as before, and the show's dot lights (the number is
saved with the show). Faders and the crossfader glide too, and an
uncaught fader still waits. Cue knob and pads: one step per click.

**Judge:** whether 80 ms feels right — leave it where it feels right.

**Wrong if:** the knob fights you; a value that never settles; "off" at
launch on a show that never saved the number.

**Changes:** the number is saved with the show.

*(check 78)*

#### A18. The instances knob at the bottom

**Needs:** APC40.

**Do:** F1 (TUMBLE). Turn track knob 3 (K3) fully left.

**Right if:** the bottom of that knob is now "nothing drawn", not one
copy.

**Judge:** whether that is too easy to land on.

*(check 62)*

#### A19. The cue knob reaches the Klein bottle

**Needs:** APC40.

**Do:** turn the cue knob right until the shape stops changing, one
click more, then left.

**Right if:** it stops on the Klein bottle (26), one shape per click,
and never jumps back to the 5-cell.

*(check 117)*

#### A20. Macro candidates: MACRO PERFORMANCE (on the copy)

**Needs:** APC40, music with a clear kick and hi-hats, the copy, and
[`plans/22-macro-candidates.md`](plans/22-macro-candidates.md) open.

**Do:** PRESETS: load MACRO PERFORMANCE from your library. The
macros are the device knobs D1–D8 (without the desk: the macro sliders
on ROUTING). Turn each end to end, with music and with none, then back
to rest (noon; D7 and D8 to zero). Then a breakdown: D7 up over 8–16
bars, then at the drop D7 down and D8 up together.

**Judge:** for each knob, does it do what its line in the sheet says?
INTENSITY (D1) and DROP (D8) together are about four times the music's
push: too much? Which to keep, and as what.

*(check 133)*

#### A21. Macro candidates: MACRO STREAMS (on the copy)

**Needs:** as A20.

**Do:** load MACRO STREAMS. With music, take D1–D6 to zero and back,
one at a time; then D7 and D8.

**Right if:** each of D1–D6 at zero stills only its band's turning and
its pattern input, and at full doubles them; D7 swings the colours, D8
takes the faces from together to scattered.

**Judge:** which to keep.

*(check 134)*

#### A22. Macro candidates: MACRO INTENSITY (on the copy)

**Needs:** as A20.

**Do:** load MACRO INTENSITY. D1, D2 and D3 one at a time, each back to
noon, with music and in silence.

**Judge:** which "intensity" is right: D1 (both), D2 (only how hard the
music pushes; nothing in silence) or D3 (only the resting look)? D1 and
D3 share two settings, so the last one turned wins.

*(check 135)*

#### A23. Macro candidates: MACRO BREAKDOWN DROP (on the copy)

**Needs:** as A20.

**Do:** load MACRO BREAKDOWN DROP. D1 alone through a breakdown and a
drop; then D2 and D3 as a pair (not with D1).

**Judge:** one knob or two? Is D1's top too bright? Do the breakdown and
the drop still feel like their names?

*(check 136)*

The entries from A24 on test plan 24, the party fixes. No preset was
changed for it: where an entry needs a preset with faders, a template or
a palette, it copies a small test file from `tests/fixtures/` into the
copy. A30–A32 work with the on-screen desk alone too.

#### A24. Hold SAVE, tap a pad: ten saves in a row (on the copy)

**Needs:** APC40; the copy.

**Do:**
1. F5 (TRIP). Hold track 8's clip-stop button — the eighth button of the
   row under the grid, now **SAVE** — and, while holding it, tap an
   empty pad in row 4 or 5. Let go of both.
2. Hold SAVE and tap a filled pad in row 1.
3. Repeat, alternating empty and filled pads, until you have saved ten
   times; latch SHIFT for every other save.
4. Press SAVE alone and let go.
5. Look at the PRESETS list and `<home>/trash`.

**Right if:** SAVE lights while held. Each save makes a new preset
(TRIP 2, TRIP 3 … TRIP 11), the tapped pad blinks and then stays green,
and the footer names the new preset and its slot. On a filled pad the
footer adds that the old preset "is still in the preset list" — and it
is, with no pad pointing at it. Nothing is ever loaded by the tap. (4)
nothing happens. (5) every old preset is in the list; the trash is as it
was. SHIFT does not change any of it.

**Wrong if:** the pad loads instead of saving (SAVE did not light: read
the SYSTEM page for "SAVE not added …", which means that button was
already yours in `bindings.json`); a preset written over or moved to
the trash; no blink.

**Changes:** ten new presets; delete them from the list afterwards.

*(check 148)*

#### A25. Points, lines, faces and rotate on both layers

**Needs:** APC40.

**Do:** press scene launch 1–4 (the top four buttons of the column right
of the grid: points, lines, faces, rotate), then latch SHIFT and press
them again. Unlatch. Tick Points on the VIEW page. Load TUMBLE (F1) from
its pad, then latch SHIFT and load it again from the pad.

**Right if:** each button switches its layer whether SHIFT is latched or
not, and its light always shows whether that layer is on — it follows
the VIEW page's tick too. Right after each load the four lights show
TUMBLE's: points dark, the other three lit. No "dropped" line in the
footer on a factory preset's load.

**Wrong if:** a button dark or dead under SHIFT; a light that disagrees
with the picture after a load; a "dropped" note on load.

*(check 149)*

#### A26. A load relights the whole desk

**Needs:** APC40.

**Do:** run `uv run python tools/midi_probe.py`, press a few buttons the
app leaves dark (so they light), Ctrl-C. Launch the app and load a
preset from a pad. Then move the crossfader half way and load three
presets in a row, moving it after each.

**Right if:** after the load every light on the desk is either a
mapped control's state or off: nothing the probe lit is left on. The
crossfader keeps its place through every load and the next move carries
on from it (MASTER too).

**Wrong if:** a light left on from before; the crossfader dead after a
load.

*(check 150)*

#### A27. The desk log

**Needs:** APC40.

**Do:** SYSTEM page, under **midi**: open **desk log**. Press a bank
pad, a points/lines button, a button that does nothing, SHIFT, a band
scene (row 2, SHIFT latched), SAVE with a pad (on the copy), and hold a
filled pad for a second.

**Right if:** one line per press, newest at the top: the time, the
control ("G1·5 (clip 1·5)"), what it did ("Preset → TRIP", "nothing (no
row on the preset layer)", "saved into slot …", "held: nothing saved (a
filled pad only loads)") and the layer in brackets ([preset], [global],
[both]). Never more than twenty lines. Moving a knob or a fader adds no
line.

**Wrong if:** no **desk log** fold; a press missing; the wrong layer.

*(check 151)*

#### A28. The track faders belong to the preset (on the copy)

**Needs:** APC40; the copy.

**Do:**
1. Copy `tests/fixtures/desk-faders/faders.json` into the copy's
   `presets/` folder. Load FADERS from the PRESETS list.
2. Move each of the eight track faders up and down.
3. Save it as FADERS 2 and load it again.
4. Load TRIP (F5) and move the track faders.
5. On TRIP, VIEW page: right-click **Lines opacity** → **Learn desk**,
   then move track fader 1 (S1). Move it again slowly.

**Right if:** (1) the on-screen desk names S1–S8: points opacity, lines
opacity, pattern mix, bitmap alpha, brightness, speed, field amp, dream
mix. (2) each fader does nothing until it reaches its setting's value,
then moves it. (3) the same eight. (4) on TRIP they are dark and do
nothing. (5) the footer says "learned view.lines_alpha ← S1 … (into the
preset)", TRIP's unsaved dot lights, and S1 then fades the lines once it
catches them.

**Wrong if:** FADERS' faders dark, or the learn refused as "invariant"
(the first launch did not move the old fader rows: see L1 and A29);
TRIP's faders doing something.

**Changes:** FADERS, FADERS 2 and TRIP's unsaved learn; delete or revert
them.

*(check 152)*

#### A29. The sound faders are under SHIFT (on the copy)

**Needs:** APC40; the copy; A28 done.

**Do:**
1. On the copy's first launch of this build, read the SYSTEM page's
   bindings line (or L1's terminal output).
2. Load FADERS. Push S1 to the top (points fully opaque).
3. Latch SHIFT. Pull S1 down a little; then sweep it through SUB's
   Post-drive (watch the ANALYZER page).
4. Unlatch SHIFT and move S1 a little.
5. Move MASTER and the crossfader, with SHIFT up and latched.

**Right if:** (1) it says `bindings.json` was updated, with
`bindings.json.bak-v3` kept. (3) under SHIFT S1 does nothing until it
reaches SUB's value, then drives it; S7 and S8 are dynamics and trim.
(4) the points opacity does not jump: S1 waits until it comes back to
the opacity's value. (5) MASTER is the audio drive and the crossfader the
master dim, the same on both layers.

**Wrong if:** a setting jumps on the first move after a SHIFT press; no
sound faders under SHIFT.

*(check 153)*

#### A30. The desk coverage report against what you see

**Needs:** laptop (the on-screen desk); the APC40 helps.

**Do:** open `hyperspace-python/docs/plans/assets/24-party-fixes/desk-coverage.md`.
Load TRIP, then hands-orbit; press **H** for the big desk, and compare
each with its row under "Preset × control".

**Right if:** every lit control is ● in the row and every dark one ·
(S1–S8 are dark on every preset); K7 (Bitmap alpha) is ✕ on TRIP and
turning it changes nothing; on hands-orbit K4 and D4 (pattern mix,
pattern) are ✕ while the faces are off and come alive when Faces is
pressed.

**Judge:** whether "dead" (✕) matches what you would call dark, and
which presets to give a better desk first. The report says no preset
meets the bar of at most four dark or dead yet: that is for the
authoring pass.

**Wrong if:** a lit control marked dark; a control that visibly works
marked ✕.

*(check 155)*

#### A31. A desk template (on the copy)

**Needs:** laptop; the copy. The APC40 shows the same lights.

**Do:**
1. Copy `tests/fixtures/desk-templates/desk/fixture-shape.json` into
   `<home>/desk/` and `tests/fixtures/desk-templates/presets/templated.json`
   into `<home>/presets/`. Load TEMPLATED.
2. Save it as TEMPLATED 2 and open `<home>/presets/templated-2.json`.
3. In the template file add a row for D5 (copy D4's line, change `19` to
   `20` and the target); load TEMPLATED 2 again.
4. Load TEMPLATED. In the template file change D3's target to
   `camera.zoom`; without reloading, save as TEMPLATED 3, open its file,
   then load it.
5. Move the template file out of `desk/` and load TEMPLATED.

**Right if:** (1) D1 4D depth, D2 dream mix, D3 pitch, D4 pattern, K1
brightness, K2 dark, K3 pattern mix, S1 lines opacity. (2) the file
says `"desk_template": "fixture shape"` and holds three desk rows, not
the seven the desk shows. (3) D5 lights. (4) TEMPLATED 3 holds the same three rows as
TEMPLATED (none for D3); loaded, D3 is camera zoom. (5) the footer says
"desk template 'fixture shape' not loaded …" and only D2 and K3 are lit.

**Wrong if:** the saved file holds every row; D5 never appears;
TEMPLATED 3 holds a D3 row.

**Changes:** the template and three presets; delete them afterwards.

*(check 156)*

#### A32. Click a control: this preset's settings first

**Needs:** laptop (the on-screen desk); the APC40 helps.

**Do:**
1. F5 (TRIP). Click D5 on the on-screen desk; read the short list under
   the transport buttons. Open its chip ("all ▾", or "all params ▾" on
   the big desk).
2. Click a setting in the list.
3. Click SM; latch SHIFT and click D5.
4. Pick D5 again, open the chip's list and wait more than 20 seconds.
5. Press **H** and repeat step 1 on the big desk.

**Right if:** (1) the list starts with the settings TRIP's routes move,
then the ones TRIP has changed, then its effects' settings — no
look-back setting (TRIP's look-back is off); the chip shows the same,
then a menu per group of everything else. (2) D5 is put on it: "learned
… ← D5" in the footer, D5 labelled, one ⌘Z undoes it. Clicking a
setting on a page still maps too. (3) no list. (4) the pick lets go and
the panel answers clicks again. (5) the list is bigger and easier to
read.

**Judge:** whether an effect's blend, order and target belong in the
list, and whether the list is readable at the small size.

**Wrong if:** no list; a setting that does nothing on TRIP near the top;
the list covering a control.

*(check 157)*

#### A33. The desk plugged in after the app started

**Needs:** APC40. Plan 27 (the device registry).

**Do:** unplug the APC40 and launch. Look at SYSTEM → **devices**;
click a bank pad on the on-screen desk. Plug the APC40 in and wait ten
seconds. Move the crossfader and a knob; tap a bank pad.

**Right if:** before: the apc40 line says `lost` (not an error) and the
on-screen desk works. Within about ten seconds of plugging in, the line
says `connected`, the desk wakes up and every light shows the loaded
preset (points, lines, faces and rotate their live state), and the
crossfader, the knobs and the pads work at once, with no restart.

**Wrong if:** the line says `error`; the desk stays dark after it says
`connected`.

*(check 175)*

#### A34. Learn from a pin, with the desk

**Needs:** the APC40.

**Do:** GRAPH; right-click `view.bright`'s round pin → **Learn desk**;
turn a track knob. Then drag a macro's box output onto a round pin.

**Right if:** a faint cable from the knob lands on `view.bright`'s
square pin (a desk learn always sets the setting itself); the macro drag
is refused: "a macro sets a base or scales a depth; aim at base or a
depth stub".

**Wrong if:** nothing lands; the cable only after reopening the page.

*(check 248; the hand part is B45)*

#### A35. The APC40 as two boxes, SHIFT latched and released

**Needs:** the APC40; the hand camera for the last step.

**Do:** load TRIP; GRAPH; untick **patched only** on both desk boxes.
Press SHIFT (it latches), then again. Drag a pin of *apc40 (SHIFT)* onto
a square pin. With the hand camera on, open the hands box's folds.

**Right if:** two boxes, *apc40* (its first fold `invariant`: SHIFT, the
bank pads, transport, TAP, the crossfader, MASTER; then knobs, faders,
the clip grid, buttons) and *apc40 (SHIFT)* (no invariant control); the
band strip's cables leave the SHIFT box, the preset's knobs *apc40*;
latched, the SHIFT box is bright and *apc40*'s preset pins faint, its
invariant pins unchanged; released, back; the drag is refused ("… on the
SHIFT node is the session's (bindings.json): map it on ROUTING"); the
desk's own rings and lights behave as before; the hands fold as axes,
pinches, grab, presence, dance.

**Wrong if:** nothing changes on SHIFT; a control on both boxes that
should be on the first only.

*(check 256)*

#### A36. Whose cable is it; a missing device (on the copy)

**Needs:** the APC40; the copy.

**Do:** GRAPH. 1. Select a `band.sel.*` cable on *apc40 (SHIFT)*; press
Delete. 2. Select a preset knob's cable on *apc40*; Delete; ⌘Z. 3.
Unplug the pad (or add a route from `axis@p2:LX` with no second pad).

**Right if:** 1 is refused ("… is the session's (bindings.json): edit it
on ROUTING") and `bindings.json` is untouched; 2 removes the row from
the preset (red dot) and ⌘Z puts it back; 3: the row hangs off a grey
box named by its role (`pad`, `p2`), faint; plugging the device in
lights it where it is.

**Wrong if:** a grey box named `axis@p2`.

*(check 258)*

#### The step sequencer on the desk (A37–A46; branch `plan-31-a1`, with Dylan)

These need branch **`plan-31-a1`**, which holds the APC40 page and waits
for Dylan's sign-off. **SEND A** (in the track section's top-right
group) turns the clip-launch pads into the step grid: rows 1–5 are the
five lanes, the clip-stop row the playhead and the length, scene launch
1–5 pick a lane. Press SEND A again to get the bank back. Load
**seq-demo** and press **run** on the SEQ page first, unless the entry
says otherwise. Run them on the copy.

#### A37. SEND A turns the pads into the pattern, and back (on the copy)

**Needs:** the APC40; the copy; `plan-31-a1`.

**Do:** with the party show loaded, note the colours of the 24 bank pads,
SAVE (track 8's clip stop) and scene 1–4. Press SEND A; press a few grid
pads; press SEND A again.

**Right if:** SEND A lights; the grid shows the drum pattern in green
(lanes 4 and 5 dark), scene 1 lit; a pad turns its step on or off (the
screen agrees) and loads no preset; SEND A again goes dark and every bank
pad, SAVE and the scene buttons come back exactly as they were.

**Wrong if:** a bank pad left dark or a step left lit; a pad loading a
preset while the grid is up.

*(check 286)*

#### A38. Yellow over green

**Needs:** the APC40; `plan-31-a1`.

**Do:** SEND A up, seq-demo running; look from a metre or two.

**Right if:** the moving yellow on a lit pad is easy to tell from green,
and red (mute lane 2 on screen) from both.

**Wrong if:** yellow and green look the same on the desk.

*(check 287)*

#### A39. No flicker at speed

**Needs:** the APC40; `plan-31-a1`.

**Do:** turn every step of all five lanes on (on screen); SEND A; tempo
about 175 with span ½ bar; then span 4 bars.

**Right if:** the yellow column steps cleanly across five lit pads; no
pad flashes dark between steps.

**Wrong if:** flicker or stutter on the grid.

*(check 288)*

#### A40. The bottom row is the playhead and the length

**Needs:** the APC40; `plan-31-a1`.

**Do:** SEND A, running. Watch the clip-stop row; press clip stop 5, then
clip stop 8; then stop the transport on screen.

**Right if:** one clip stop is lit, walking along with the playhead;
after clip stop 5 the pattern repeats after step 5 and columns 6–8 go
dark and do nothing; clip stop 8 brings back all eight and **does not
save a preset** (off the grid it is SAVE); stopped, the row is dark.

**Wrong if:** clip stop 8 saves; a dark column still toggles.

*(check 289)*

#### A41. Scene buttons pick and mute a lane

**Needs:** the APC40; `plan-31-a1`.

**Do:** SEND A. Press scene 2; scene 2 again; scene 3; scene 2 again.

**Right if:** scene 2 lights (the on-screen desk's header says "SEQ ·
lane 2 · L=8"); the second press mutes lane 2 — its scene button blinks,
its pads turn red, the snare stops; scene 3 picks lane 3 while scene 2
keeps blinking; pressing scene 2 then picks it again (it stays muted);
points, lines, faces and rotate never change.

**Wrong if:** no blink; a scene press switching points or lines.

*(check 290)*

#### A42. A held bank pad across SEND A saves nothing (on the copy)

**Needs:** the APC40; the copy; `plan-31-a1`.

**Do:** grid down. Hold an **empty** bank pad (row 4); while holding,
press SEND A; keep holding for two seconds; let go.

**Right if:** nothing is saved (the PRESETS page and the slot unchanged),
no pad blinks, the grid is up.

**Wrong if:** a new preset in that slot.

*(check 291)*

#### A43. SHIFT with the pattern up

**Needs:** the APC40; `plan-31-a1`.

**Do:** SEND A; press SHIFT (it stays lit); press grid pads, scene
buttons and clip stops; turn a track knob; press SHIFT again.

**Right if:** the grid, the scene buttons and the clip stops still edit
the pattern with SHIFT lit; the knobs and faders do their SHIFT jobs;
with SHIFT off the knobs are the preset's again and the grid still up.

**Wrong if:** a SHIFT-layer action fires from a grid pad or scene button.

*(check 292)*

#### A44. QUANT with the pattern up

**Needs:** the APC40; `plan-31-a1`.

**Do:** SEND A on seq-demo; press QUANT (next preset) a few times; then
load seq-demo again from the screen.

**Right if:** the grid stays up through every load and shows each
preset's pattern (most are empty: dark), the drums again on seq-demo.

**Wrong if:** a load takes the grid down, or the old pattern stays lit.

*(check 293)*

#### A45. Switch the desk off and on with the pattern up

**Needs:** the APC40; `plan-31-a1`.

**Do:** SEND A up and running; switch the APC40 off and on (or unplug
it and plug it back in).

**Right if:** within a second or two the desk shows the grid again as it
was: SEND A lit, the pattern, the lane's scene button, the walking clip
stop.

**Wrong if:** the bank's lights come back while the screen says the grid
is up, or the grid stays dark.

*(check 294)*

#### A46. SEND A after the desk fell back to Generic mode

**Needs:** the APC40; `plan-31-a1`.

**Do:** with the grid **down**, switch the desk off and on while the app
runs (it may come back in Akai's Generic mode — see SETUP); press SEND A;
press it again. Then the same with the grid **up** before switching off.

**Right if:** within a press or two the desk is back in the app's mode
(the desk log says so); from then on SEND A turns the grid on and off
once per press, its light matching the screen; at worst the first press
is lost — press again.

**Wrong if:** SEND A's light and the screen disagree, or SEND A stays
latched on the desk by itself.

*(check 295)*

#### A47. A switch over three channels on a knob, into the faces

**Needs:** the APC40; the copy; three channels with pictures; branch
`plan-33-free-graph`.

**Do:** on GRAPH add a switch, wire `media.a`, `media.b` and `media.c`
into its `in1`–`in3` and the switch into `pattern.media`. Learn
`switch.select` onto an APC40 knob and sweep it; put the param on `off`
and on `4`.

**Right if:** the faces show A, B and C as the knob passes each third, as
a cut; `off` and the unwired `4` show the faces' own pattern; only the
picked channel uploads on SYSTEM. Say whether three positions on a
continuous knob are easy to land on.

**Wrong if:** a blended picture, a stall when the pick changes, or an
unpicked channel still uploading.

*(check 319)*

#### A48. Hold and take on two desk buttons

**Needs:** the APC40; the copy; branch `plan-38-hold` (plan 38).

**Do:** with no hold on, learn `output.hold` and `output.take` onto two
free buttons. Press the hold button, then the take button. Hold again and
press **drop** on GRAPH.

**Right if:** both buttons light while held and go dark after take and
after drop; the press that learns a button does not start a hold. Learn
the buttons *before* holding: a button learned during a hold is unlearned
by **drop** (register row 438).

**Wrong if:** the take button stays dark while held, or a learning press
starts a hold.

*(check 381)*

#### A49. A patch brings its knob, and a sheet asks when the knob is taken

**Needs:** the APC40; the copy (with `[library] path` commented out);
branch `plan-40-build` (plan 40).

**Do:** copy `tests/fixtures/patches/acid-wash.json` from the repo into
`~/Hyperspace-try/patches/` (acid, wobble and a delay; K1 on acid's speed;
the right hand's height, smoothed, on wobble's amount). Load `party-acid`
(where K1 is the brightness) and spawn acid wash from **patches** on
GRAPH's head. Read the sheet; press **Spawn**; turn K1; ⌘Z; turn K1. Spawn
again; while the sheet is up, arm a learn and move a hand or a knob. Press
**keep all existing**, then **Spawn**; turn K1; hover the new box. Spawn
once more and press **Cancel**. Then load `party-noita` and spawn it
there.

**Right if:** the sheet says "K1: fx.acid.2.speed (the patch) or
view.bright (the preset)" with the patch chosen; after Spawn K1 turns the
new acid's speed and its ring agrees; one ⌘Z takes the whole spawn back
and K1 is the brightness again; nothing learns while the sheet is up;
after **keep all existing** K1 stays the brightness and the box says "K1
kept by the preset"; Cancel adds nothing. In `party-noita` the sheet
lists only K1, even though the right hand's height already drives warp
there: the patch reads the hand through its smoothing node, which counts
as no clash today — say whether it should (register row 514).

**Wrong if:** K1 does the wrong thing after Spawn, a learn completes
under the sheet, undo takes more than one press, or "kept by the preset"
is missing.

*(check 397)*

#### A50. The desk unplugged, said; plugged in, said

**Needs:** the APC40; the copy; the preset saved in A49 with acid wash in
it.

**Do:** quit, unplug the APC40, start the app and load that preset. Read
the group's box, GRAPH's head, the PRESET strip and the SYSTEM page; hover
**1 device missing**. Plug the desk in and press nothing. Turn K1.

**Right if:** the box says "waits for apc40 (lost): K1"; the head and the
strip show **1 device missing**, whose hover lists the desk's controls by
their names (K1, K2 …); SYSTEM says "wanted by the preset: apc40 — lost;
n controls wait". When you plug it in the footer says "apc40 connected —
n controls live" once, the rings light, the warning goes, and K1 turns
the patch's knob. (With the desk unplugged every party preset shows **1
device missing**: say whether that is useful or noise.)

**Wrong if:** nothing is said when the desk comes back, it is said twice,
or the hover reads "CC 48 ch1" instead of K1.

*(check 398)*

## (b) The hand camera

Plug in the hand camera (Ultraleap Leap Motion Controller 2) by USB
before launching; the Ultraleap Hand Tracking service must be running.
The config has `[hands]` `enabled = true` and `mode = "desktop"`.
**B1 first**, with nobody else in the camera's view. Leave the APC40
plugged in for B23–B28.

#### B1. Calibrate, and the box it draws — run first

**Needs:** hand camera; nobody but you in its view.

**Do:**
1. Launch, HANDS page. Before touching anything, look at the box view.
2. Open **feel & calibration**, press **calibrate 20 s**, and move both
   hands through everything they should reach: side to side, low to
   high, near to far, and each tilt end to end. Each hand must travel
   more than 12 cm in a direction for it to count.

**Right if:** (1) if `<home>/hands.json` existed, the ranges are its
ones, there is no inner rectangle, and the line under the axis's range
reads "box open". (2) the note reads "calibrated 12 axes · box W × H × D
mm · the old file kept as hands.json.bak-v1" (the last part only if the
file existed); the box view now has an inner rectangle and the height
gauge a bracket; both hands' dots stay inside it wherever you played;
`hands.json` holds `"schema": "hyperspace.hands/2"` and a `box`; every
axis still reaches both ends of its row.

**Wrong if:** "x open (not swept)" — sweep wider on that direction and
run it again; "box left as it was (too few palm samples)" — the camera
barely saw a hand; no rectangle; no `.bak-v1`. A rectangle pressed
against the view's edge is not a fail: say whether it reads.

**Changes:** `<home>/hands.json` rewritten, the old one kept as
`hands.json.bak-v1`.

*(check 72, 15)*

#### B2. The probe sees both hands

**Needs:** hand camera; app closed.

**Do:** `uv run python tools/hands_probe.py`; move both hands; pinch;
Ctrl-C.

**Right if:** both hands appear within a second of entering; every
axis's readings change as you move; the pinch gaps print live; Ctrl-C
exits cleanly.

**Wrong if:** "no service" or nothing (the Ultraleap service is not
running or not found); a hand seen only very high (the `mode` setting).

*(check 13)*

#### B3. The HANDS page and which way is up

**Needs:** hand camera.

**Do:** HANDS page. Both hands in the box. Roll thumb-up, tilt fingers
up, turn fingers outward. Pinch each finger to the thumb.

**Right if:** two dots (left white, right red) follow the palms; on both
hands, thumb-up roll reads up, fingers-up reads up, fingers-outward reads
up; the eight pinch switches close on a pinch and show the gap. The page
fits with no scrollbar with the tracker on: switches beside the box, the
feel knobs two to a row.

**Wrong if:** a direction the wrong way (flip it for now with that axis's
invert setting and note it); a scrollbar.

*(check 14, 4)*

#### B4. A hand outside the box

**Needs:** hand camera.

**Do:** load `hands-play` (right hand height = brightness). Right hand
mid-height in the box; move it slowly out through the right side. Wobble
it a centimetre at the edge. Bring it back. Repeat upward past the
bracket and toward yourself.

**Right if:** a centimetre or two past the rectangle the dot becomes a
hollow dim ring, the status line shows `R◌` (hover: "tracked, but outside
the box"), its rows dim, and brightness returns to its setting at once;
at the edge it does not flicker; coming back the value glides onto the
hand, no jump.

**Judge:** whether `◌` can be told from `●` and `○` at arm's length.

**Wrong if:** still performing far outside; flicker at the edge; a jump
on re-entry.

*(check 73)*

#### B5. The default feel

**Needs:** hand camera.

**Do:** load `hands-play`. Raise and lower the right hand; watch
brightness. On the HANDS page the defaults are Steadiness 1 Hz, Response
4, Catch 150 ms, Return 500 ms, bounce 0.15, dead zone 0.04. Tune them
until it feels right, then save from the HANDS page's strip as
`factory`.

**Right if:** a still hand does not shimmer, a fast one does not lag, a
returning hand glides on rather than jumping.

**Wrong if:** shimmer at rest (Steadiness too high); lag (Response too
low).

**Changes:** writes `<home>/hands/factory.json`; tell the developers so
it can be shipped.

*(check 16)*

#### B6. Tilt and turn without moving height

**Needs:** hand camera.

**Do:** load `hands-fx`. Hold the right hand still; tilt it (fingers up
and down), then turn it (fingers left and right).

**Right if:** the Acid effect's twist (tilt) and bend (turn) move while
FX mix (height) stays within a few percent.

**Wrong if:** height moving with a tilt (widen the right hand's height
dead zone, or note it as a feel finding).

*(check 17)*

#### B7. The thumb-to-ring-finger pinch

**Needs:** hand camera.

**Do:** HANDS page; watch the ring finger's gap. Pinch thumb to ring
finger deliberately; open.

**Right if:** the gap drops below 0.34 (of the palm's size) and the
switch closes; opening past 0.46 lets go.

**Wrong if:** never below 0.34 on a deliberate pinch — note the gap you
read (the thresholds are the same for every finger).

*(check 18)*

#### B8. Learn onto a setting a hand already drives

**Needs:** hand camera. (Optionally a relaunch with `[midi] enabled =
false`.)

**Do:** load `hands-play`. VIEW page: right-click Brightness → **Learn
hand ▸ left**; move the left hand up and down. Choose **Keep**. Repeat
and choose **Replace**. Optionally set `[midi] enabled = false`, launch
and repeat, then put it back.

**Right if:** while armed, the footer reads "learning view.bright — move
the left hand…" on every page and only the left hand can complete it; a
prompt appears whichever page you are on — "ONE PERFORMER PER
PARAMETER", "Brightness is already performed by R height positions.",
"L height positions asks for it.", **Replace** / **Keep**; moving hands while it is up
learns nothing more; Keep changes nothing (the route's row, on GRAPH);
Replace makes the row read "L height positions", the line ends "moved from view.speed"
(the preset's own left-height row on Speed is gone), the unsaved dot
lights, and `<home>/bindings.json` is not written. (Had a tilt moved
most, the row would read "pushes +0.25" — also fine.) With MIDI off it
still works.

**Wrong if:** it lands with no prompt; the wrong axis learned.

*(check 19)*

#### B9. Pinch zoom while scrolling

**Needs:** hand camera; a scroll wheel or trackpad.

**Do:** load `hands-pinch`. Pinch left thumb to middle finger and move
the left hand: zoom follows. Keep pinching and scroll a few notches in
the render window. Open the pinch.

**Right if:** zoom does not run away while scrolling; when the pinch
opens, zoom lands on the value the scroll set, not where the hand left
it.

**Wrong if:** drift while scrolling; a jump to the hand's last value.

*(check 20)*

#### B10. The right hand deepens the breathing

**Needs:** hand camera.

**Do:** load `lfo-breathe`; LFO page. Raise the right hand, then lower
it, then take it out.

**Right if:** LFO 1's depth slider's ghost bar rises with the hand and
the brightness swell deepens; nothing else moves (speed, zoom, effects);
lowered or gone, depth returns to 0.6.

**Wrong if:** something else moving (a route on the ROUTING page); depth
not returning when the hand leaves.

*(check 21)*

#### B11. A second pinch at another height

**Needs:** hand camera.

**Do:** `hands-pinch`: pinch right index low (dark), open, raise the
hand, pinch again, open.

**Right if:** brightness takes the hand's new height at once and returns
to its setting on open.

**Judge:** whether that jump should glide (the 150 ms catch) instead.

*(check 23)*

#### B12. A hand leaving, and "hold"

**Needs:** hand camera.

**Do:** `hands-play`, HANDS page. Take the right hand out. Set the right
hand height's **rest** to *hold*; take it out again. Bring it back.

**Right if:** its rows dim and say "DAW only; lane —"; brightness is
back at its setting the same frame; with *hold* the value sent to
outside music software holds but the picture still returns; on re-entry
the row glides onto the hand.

**Wrong if:** the setting parked at the rest value.

*(check 24)*

#### B13. A hand moving makes no undo step

**Needs:** hand camera; music.

**Do:** F1 (TUMBLE). VIEW page: drag Brightness, wait a second. Play for
half a minute with both hands, in and out several times. ⌘Z once.

**Right if:** Brightness goes back — the one thing you did by hand.

**Wrong if:** the footer says "undid Speed …" (or another setting a hand
drives), or names a rotation or the BPM.

*(check 52)*

#### B14. A hand Learn listens to one hand

**Needs:** hand camera; B1 done.

**Do:** F1. Left hand still in the box. With the right hand on the
trackpad, CAMERA page: right-click Zoom → **Learn hand ▸ left**. Move the
right hand freely over the box for five seconds. Raise the left hand
slowly. ⌘Z. Repeat with **right** and the hands swapped. Then arm **left**,
click the footer's line to cancel, arm again at once and keep both hands
still.

**Right if:** nothing is learned from the right hand; the footer reads
"learning camera.zoom — move the left hand… (click to cancel)"; raising
the left hand gives "learned camera.zoom ← hand left.y positions (into
the preset; moved from master.gain)" — any left-hand axis is a pass —
ROUTING lists "L height" and Zoom follows the left hand only; TUMBLE's
own left-height row on the sound drive goes with it (⌘Z brings it back).
After re-arming, nothing is learned until the left hand moves.

**Wrong if:** the right hand took it; learned the moment it was armed.

*(check 66)*

#### B15. A tilt learned is gentle

**Needs:** hand camera.

**Do:** `hands-play`. VIEW page: right-click Speed → **Learn hand ▸
right**, roll the right hand, choose **Replace**. Then learn the right
hand's turn onto the XY rotation rate. Then lower **Learn depth** (HANDS
page, feel & calibration) and learn the right hand's tilt onto the XZ
rate.

**Right if:** the row reads "R roll pushes +0.25"; with the hand level
the speed is the preset's; a full roll takes it to about half or double,
not to stop or flat out; the XY rate turns as set with the hand level,
and a small turn nudges it; the XZ row carries the new depth, the others
keep 0.25, and the line ends "moved from view.depth4". Learning the same
axis onto the same setting again changes only its gate.

**Wrong if:** "positions" on a tilt; the setting jumping when the hand
enters.

*(check 75)*

#### B16. Height is still a fader where it should be

**Needs:** hand camera; after B15.

**Do:** learn the left hand's height onto Pattern mix; then onto the YZ
rate; then a tilt onto Faces; then a tilt onto Instances. Then load
`hands-play`, `hands-pinch` and F1–F8 and look at ROUTING each time.

**Right if:** Pattern mix: "L height positions" (low none, high full);
YZ rate: "L height pushes +0.25", the Pattern mix row gone, the plane
turns as set with the hand low and faster as it rises, never backwards
and never stopped; Faces: "positions", flipping past the middle;
Instances: "positions". Every factory preset's rows read as before.

**Wrong if:** a factory row changed.

*(check 76)*

#### B17. A Learn moves the axis

**Needs:** hand camera.

**Do:** F1 (TUMBLE): right roll turns the XW plane. Learn right roll
onto Brightness (**Learn hand ▸ right**, roll). ⌘Z.

**Right if:** the line says "learned view.bright ← … pushes +0.25 (into
the preset; moved from rot.phase.XW)", ROUTING no longer has the XW row,
roll moves brightness only; ⌘Z brings the XW row back and removes the
new one.

**Judge:** whether a Learn should instead add a row and keep the old one.

*(check 77)*

#### B18. Two hands steer the camera

**Needs:** hand camera.

**Do:** load `hands-orbit` from the list. Right hand in, level, mid box;
slide it left and right; tip fingers up. Left hand: side to side,
reaching in, raising. Take both out. Press R with a hand in.

**Right if:** a still level hand moves nothing; right hand side to side
orbits about a quarter turn each way; fingers up looks down onto the
shape; left hand pans and raising it zooms to about 2.2×; with both out
the camera is back where the mouse left it.

R with a hand in snaps the view to its reset at once. **Know:** the
reset is made under the hand's push, so when the hand then leaves the
camera lands past the reset view by what the hand was adding — say
whether that matters.

**Judge:** the directions, the zoom depth, and whether this is the
"orbit" you meant.

*(check 80)*

#### B19. Hand routes follow the axis by name

**Needs:** hand camera.

**Do:** in the config under `[hands]` set
`dofs = ["yaw", "pitch", "roll", "y", "x", "z"]`; launch; load
`hands-play`, then `hands-pinch`. Then set `dofs = ["x", "y", "z"]`;
launch; `hands-play`.

**Right if:** first: right height still drives brightness, left height
speed, right tilt 4D depth; ROUTING reads "R y positions", "L y
positions", "R pitch positions" and the source lists show `hand R y`
etc.; a right index pinch still picks brightness. Second: the right tilt
row does nothing while both heights work.

**Wrong if:** a row moving with the wrong axis; raw `hand:<n>` in the
lists.

**Changes:** remove the `dofs` line.

*(check 42)*

#### B20. The "screentop" warning

**Needs:** hand camera.

**Do:** set `[hands]` `mode = "screentop"`; launch; tick **Ghost hands**.

**Right if:** the ghost's **more ▸** chip reads **! more ▸** in the
warning colour, and clicking it shows "ghost axes for screentop are
unmeasured: left/right and up may be wrong — Mirror flips left for
right" (in desktop mode the chip reads **more ▸** and says nothing); the
page does not scroll with every ghost control showing, and no control
is drawn over another or over the **Ghost hands** label.

**Changes:** put `mode = "desktop"` back.

*(check 100)*

#### B21. Zero instances with hands in

**Needs:** hand camera.

**Do:** F3 (FIELD): right hand at the bottom of the box, then the top.
Then ghost hands on and Instances 0.

**Right if:** at the bottom nine copies, never none; at the top the room
fills (69 copies); the ghost hands still draw at 0.

**Wrong if:** FIELD blanks with a low hand.

*(check 62)*

#### B22. The hands' own port in FL Studio

**Needs:** hand camera; FL Studio; the IAC bus (see Part 1, FL Studio).

**Do:** hands on, launch. In FL Studio look for a "Hyperspace Hands"
input; raise the right hand. Then set `[hands] out = "IAC"` (the app's
own virtual port never goes away, so only a named bus tests the
rejoin), launch, take the IAC bus offline in Audio MIDI Setup while
running, then bring it back. Put `out` back afterwards.

**Right if:** FL sees "Hyperspace Hands"; right-hand height shows on CC
109, channel 16; the port is rejoined within 2 s if the bus was back
within about ten seconds, otherwise within 10 s.

**Wrong if:** no rejoin.

*(check 29)*

#### B23. A knob on a setting a hand drives

**Needs:** hand camera, APC40.

**Do:** `hands-play`; right hand in the box (it drives brightness). Turn
K1 (Brightness). Take the hand out of the box.

**Right if:** the setting moves (the ring follows), the picture does not;
with smoothing on (80 ms) it glides; when the hand leaves, brightness
lands on the knob's value at once — no fade to minimum.

**Wrong if:** brightness dropping when the hand leaves; the knob dead
while the hand is in.

*(check 22)*

#### B24. A hand on the desk does not perform; reset

**Needs:** hand camera, APC40 where it will stand for the show.

**Do:** `hands-play`. Reach for the APC40 with the right hand and turn a
knob (left hand away). Tick Ghost hands; move a hand out of the box. Then
press **reset ranges**; afterwards run B1 again.

**Right if:** brightness moves only by the knob; the right hand's mark is
a hollow ring (or gone) the whole time; the ghost hand fades out at the
frame's edge, and the frame shows the whole box; reset removes the
rectangle and bracket, the note reads "ranges back to the defaults, box
open", and a hand is present wherever the camera sees it.

**Wrong if:** the dot filled while your hand is on the desk — the desk is
inside the box: move it, or calibrate again keeping clear of it; the
ghost drawn outside.

**Changes:** reset clears the box; B1 puts it back.

*(check 74)*

#### B25. A desk Learn ignores the hands

**Needs:** hand camera, APC40.

**Do:**
1. F1. VIEW page: right-click 4D depth → **Learn desk**.
2. Wave both hands through the box for five seconds.
3. Move S3 a little. Tap TAP TEMPO. Press SHIFT; turn K2.
4. Press SHIFT again; turn D5.
5. Arm **Learn desk** again and press a pad in row 1; cancel by clicking
   the footer's line.

**Right if:** (1) its control framed red, the footer in red "learning
view.depth4 — turn a knob or press a button on th…" on every page (the
full line in its hover). (2) still armed; no new route (TUMBLE's own
hand route still moves depth). (3) S3 moves the third band's drive and
TAP taps, nothing said, still armed; SHIFT lights and the desk header
says GLOBAL LAYER; K2 shows for four seconds in the warning colour "K2
(track knob 2) is on the global layer (the session's) — latch SHIFT off
to learn into the preset", then the red line returns — still armed —
and K2 did not move Response. (4) "learned view.depth4 ← D5 (device
knob 5) (into the preset); D1 let go" (D1 had 4D depth), D5's ring
lights, the frame and red line go.
(5) the preset loads and the Learn stays armed.

**Judge:** whether swallowing every control under SHIFT during a desk
Learn is a trap.

**Wrong if:** the hands took it; a fader or TAP ended it; SHIFT did not
latch.

*(check 65; replaces check 37)*

#### B26. A knob bumped during a hand Learn

**Needs:** hand camera, APC40.

**Do:** F5 (TRIP), hands out. VIEW page: right-click Speed → **Learn hand
▸ right**. Turn D1, turn the cue knob, press a filled pad in row 4 and
an empty one. Click a control on the drawn desk. Click the footer's red
line.

**Right if:** FX mix moves with D1, the cue knob changes the shape; a
filled row-4 pad loads its preset (Learn still armed), an empty one says
"slot N: an empty slot"; the footer still reads "learning view.speed —
move the right hand…"; no new desk line, K2 still has Speed; the click
on the drawing does nothing; the footer click cancels.

**Wrong if:** D1 now drives Speed; the drawing click mapped something.

*(check 67)*

#### B27. A smoothed knob with everything else

**Needs:** hand camera, APC40.

**Do:** Knob smoothing at 250 ms (SYSTEM page). Spin K1 and press F5 at
the same moment; then the same with F5's pad. Spin K1 and latch SHIFT.
Sweep K1, wait, ⌘Z; sweep and ⌘Z while it moves. `hands-play`, hand in:
turn K1; take the hand out. Slide the crossfader and press F2 mid-slide.

**Right if:** the look is TRIP's with TRIP's brightness, not the knob's;
under SHIFT brightness still arrives and K1's ring shows the SHIFT
layer's value; one ⌘Z undoes a whole sweep (the footer names where it
landed); ⌘Z mid-glide goes back and stays; with the hand in the picture
does not move, and when the hand leaves brightness is where the knob put
it; the dim finishes arriving after F2.

**Changes:** put Knob smoothing back where A17 left it.

*(check 79)*

#### B28. A hand cannot learn a ghost-hand setting

**Needs:** hand camera, APC40.

**Do:** HANDS page, Ghost hands on: right-click **Guide** and **Style**,
and in **more ▸** right-click **Mirror** and **Tethers**; then Ghost
hands and Opacity. Learn desk on Mirror, then press a pad. OUTPUT page: right-click its ticks.

**Right if:** the four have **Learn desk** but no **Learn hand ▸**; Ghost
hands and Ghost opacity still have Learn hand; the pad flips the mirror;
the OUTPUT ticks: Learn desk, no Learn hand. A preset of yours with a
route onto mirror, guide or tethers (if any) loads with the note
"dropped … → ghost.mirror: not modulatable" and its file is not
rewritten.

**Wrong if:** a Learn hand item on one of the four; a row made.

*(check 110)*

#### B29. Hand-to-picture delay

**Needs:** hand camera; a phone that films at 120 frames a second.

**Do:** `hands-play`. Film the hand and the render window together; flick
the right hand up. Count video frames between the hand moving and
brightness changing.

**Right if:** under about 4 frames at 60 per second (this is a target
nobody has measured).

*(check 25)*

The entries from B30 on test plan 24's new hand sources: how bent each
finger is (*curl*), how far the fingers fan (*spread*), how fast the hand
moves (*energy*), a sharp *flick*, the distance between the palms
(*gap*), the two hands turning against each other (*twist*), and the
*grab* (a closed fist). No preset uses them yet. A hand Learn offers
only the twelve axes, so these are put on a setting by hand on the
ROUTING page: `+ route`, then pick the source and the setting. Do it on
a preset you do not mind changing, and do not save it over one of yours.

#### B30. The new hand sources on the HANDS page and in ROUTING

**Needs:** hand camera.

**Do:** HANDS page: find the column right of the axis rows. Keep your
hands out of the box, then put one in, then both. ROUTING page: open a
route's source list.

**Right if:** with no hand the bars are hollow; the hand in view fills
its five curl bars and its spread, energy and flick bars; gap and twist
fill only with both hands in. Hovering a bar shows its name and value
(`hand:right.curl.index: 0.42`). The source list offers `hand L curl
thu` … `hand R flick`, `hands gap` and `hands twist`. The twelve axis
rows read as before.

**Wrong if:** bars that never move (the camera gives no finger
skeleton: curl and spread need it, energy and flick do not); the page
scrolls.

*(check 158)*

#### B31. Curl and energy

**Needs:** hand camera.

**Do:** route `hand R curl ind` → Brightness (positions) and `hand R
energy` → Speed. Hold the right hand open and still; slowly bend the
index finger alone; make a fist; shake the hand; hold still.

**Right if:** an open, relaxed hand gives a dim picture (curl near 0) and
a fist a bright one (near 1); bending the index alone moves it first
(the others follow a little — that is anatomy); energy is near 0 still,
high while shaking, and falls away over about a second.

**Wrong if:** an open hand already well up; a fist that never gets
near the top; energy that moves while the hand is still. Say how far
off, so the ranges can be tuned.

*(check 159)*

#### B32. Spread

**Needs:** hand camera.

**Do:** route `hand R spread` → Brightness. Palm down, fingers together;
then fanned as wide as they go; then a fist.

**Right if:** together is dark (≈ 0), wide is full (≈ 1), a fist is
dark.

**Wrong if:** wide never reaches full; together already a fifth of the
way up.

*(check 160)*

#### B33. Flick

**Needs:** hand camera.

**Do:** route `hand R flick` → Brightness (pushes, depth 1). Flick the
fingers sharply; then softly; then move the hand slowly across the box.

**Right if:** a sharp flick flashes and fades in a few tenths of a
second, a harder one brighter; a slow move does nothing; one flick, one
flash.

**Wrong if:** nothing on a real flick; flashes on ordinary moves; two
flashes for one flick.

*(check 161)*

#### B34. Gap and twist

**Needs:** hand camera.

**Do:** route `hands gap` → Zoom and `hands twist` → Yaw (CAMERA page).
Both hands in: bring them together and apart; hold an imaginary steering
wheel and turn it clockwise and back; hold them palm to palm (a clap).
Take one hand out.

**Right if:** the zoom follows the distance smoothly, at one end with the
palms nearly touching and the other at arm's width; the yaw is level
with the hands mirror-image and in the clap, turns one way clockwise and
the other way anticlockwise; with one hand out both let go.

**Wrong if:** twist running backwards; the zoom at its end long before
arm's width.

*(check 162)*

#### B35. The grab

**Needs:** hand camera.

**Do:** HANDS page: each hand's curl row ends in "grab ○". Open your
hand; close it slowly into a fist; hold; loosen it half way; open it.
Flash a fist for a split second. Take the hand out of the box while it
is a fist. ROUTING: open a route's gate list.

**Right if:** "grab ●" lights red once the fist is made (hovering it
shows the fist level, about 0.65 or more), stays lit when loosened half
way, goes out when the hand opens; a split-second fist does nothing; a
fist leaving the box goes out at once; the gate list has "L grab" and
"R grab" after the eight pinches.

**Wrong if:** it never lights on a real fist (hover it and say what
level a fist reaches); it lights on a relaxed open hand; it flickers
half-closed.

*(check 163)*

#### B36. Grab to steer the shape (on the copy)

**Needs:** hand camera; the copy.

**Do:** copy `tests/fixtures/grab-follow/grab-follow.json` into the
copy's `presets/` and load GRAB FOLLOW. (It holds three routes: the
right hand's yaw, pitch and roll onto the camera's yaw and pitch and one
rotation plane, each only while "R grab".) Turn your open right hand
about. Then make a fist and turn it; open it mid-turn.

**Right if:** the open hand moves nothing; with a fist the shape turns
with the hand; opening lets go and the shape goes back to where it was.

**Judge:** the shape jumps to the hand's angle when the fist closes,
because these routes set the angle outright. Say whether you want it to
be caught where it is instead (that needs a later plan), and whether one
turn of the hand should be one turn of the shape.

*(check 164)*

#### B37. The hands in the device list (on the copy)

**Needs:** hand camera; the copy. Plan 27.

**Do:** in the config's device list put the `[hands]` lines on the
`leap` entry with `enabled = true` and delete the `[hands]` section.
Launch. Look at SYSTEM and the HANDS page; move both hands; try a hand
Learn; press ⌘R.

**Right if:** SYSTEM: `leap · hands · connected · 42 sources · …`; the
HANDS page shows the same axes and calibration as before; routes, a hand
Learn and the ghost hands work as before; after ⌘R the hands come back.

**Wrong if:** the HANDS page shows the default axes; `error: no hands
setup`; the ghost hands gone.

*(checks 169, 180)*

#### B38. A tracker that would not start comes up later (on the copy)

**Needs:** hand camera; the copy; a recorded tape
(`uv run python tools/hands_tape.py record <file>`).

**Do:**
1. On the `leap` entry set `enabled = true` and `tape = "missing.json"`
   (no such file), and launch.
2. After a few seconds copy your tape to `<home>/missing.json`.
3. Remove the `tape` line and save; once the camera's hands show,
   unplug the camera; plug it back.

**Right if:** (1) the leap line says `error: …No such file…`, with one
"hands: …" note and no more. (2) within about ten seconds it says
`connected` and the HANDS page plays the tape, with no restart. (3)
unplugged, the line says `error: no camera` (the tracker's own words)
and no new note appears; plugged back, `connected` on its own.

**Wrong if:** it stays `error` after the file appears; a new note every
two seconds; the hands never come back after the replug.

**Changes:** remove the tape file.

*(check 172)*

#### B39. The hands where you are, through the shape's camera (on the copy)

**Needs:** hand camera; the copy, whose `hands.json` was written by an
earlier build; the 1080p projector helps.

**Do:** launch; HANDS page → **calibrate 20 s** and sweep. Then, ghost
hands on, reach to each corner of the box, on the laptop and on the
projector; compare with
`hyperspace-python/docs/plans/assets/26-render-graph/a3-hands-moved.png`
(before | after).

**Right if:** `<home>/hands.json.bak-v2` appears, the same as the old
file, and the new `hands.json` says `hyperspace.hands/3` with a
`"units"` line; the ghost hands are the size and in the place they were
on earlier builds, the perspective a little stronger (fingers nearer
the camera a touch bigger); reaching to the box's edges reaches the
picture's edges on the projector.

**Wrong if:** no backup; hands a third smaller than before; a hand
leaving a landscape picture. (On a portrait or square screen leaving at
the sides is expected.)

**Changes:** none to put back (the old file is the `.bak-v2`).

*(checks 202, 203)*

#### B40. `hands-orbit` turns only the shape

**Needs:** hand camera; the ghost hands on.

**Do:** load HANDS ORBIT. With both hands in the box: move the right
hand sideways (orbit), raise its fingers (tip), move the left hand
sideways, reach in, and raise it (pan and zoom).

**Right if:** the shape orbits, tips, pans and grows; the ghost hands
stay exactly over where your hands are — they never turn, move or grow
with the shape.

**Wrong if:** the ghost hands swing, move or grow with the shape.

*(check 200)*

#### B41. A hand on an LFO's depth acts the same frame

**Needs:** the hand camera.

**Do:** load TRIP (the left hand's height owns LFO 1's depth, and LFO 1
drives the zoom); raise and drop the left hand quickly.

**Right if:** the zoom's pulse grows and dies with the hand, with the
same feel and range as before.

**Wrong if:** the zoom stutters, doubles or sticks after the hand
leaves.

*(check 232)*

#### B42. A modifier whose hand goes away lets go

**Needs:** the hand camera.

**Do:** load ACID; on GRAPH right-click → **modifier ▸ smooth**, drag
**right energy** onto its left-hand dot (pick its input), and its
right-hand dot onto *acid*'s, picking **acid mix · mod**. Move the right
hand, then take it out of the box. Then add a second modifier, route
something from it, click it and **× remove**, and ⌘Z.

**Right if:** with the hand out the smooth's box says "out not live" (its
details "dormant") and the acid mix goes back to its setting at once;
the removed modifier's route stays (a faint wire) and does nothing until
⌘Z brings the modifier back.

**Wrong if:** the mix sticks or drops to zero; the route vanishes with
the modifier.

*(check 237)*

#### B43. Hand energy, smoothed, times the kick, into the acid — from the modifiers' details

**Needs:** the hand camera; music.

**Do:** load ACID and set the acid's mix to 0.2. On GRAPH: right-click →
**modifier ▸ smooth**; click it and set input **hand R energy**, release
0.6; **modifier ▸ combine**, inputs **mod 1 smooth** and **0 sub**, how
mul; drag the combine's right-hand dot onto *acid*'s left-hand dot and
pick **acid mix · mod** (click the wire: op pos, depth 1).

**Right if:** the acid comes in as the right hand moves fast and pulses
with the kick, and fades over about half a second when the hand stops;
both modifiers' bars move.

**Wrong if:** the combine reads 0; **mod 1** missing from the combine's
input list a moment after adding it.

*(check 241)*

#### B44. The same patch, dragged on the GRAPH page (on the copy)

**Needs:** the hand camera; music; the copy.

**Do:** load ACID (mix 0.2) and save it as a new preset; GRAPH.
Right-click the canvas: add a **smooth** and a **combine**. Drag
**right energy** onto the smooth's input; the smooth's output onto the
combine's first input, band 0 onto its second; set the combine's **how**
to mul (click it: its details); drag the combine's output onto
`fx.acid.mix`'s round pin (or *acid*'s left-hand dot). Save; load another
preset; load this one again.

**Right if:** it feels as B43; the same modifiers and route come back
(click the wire for its row); the boxes come back where you put them.

**Wrong if:** the combine reads 0; the route missing.

*(check 249)*

#### B45. Learn from a pin, with a hand

**Needs:** the hand camera.

**Do:** GRAPH; right-click `camera.zoom`'s round pin → **Learn hand ▸
right**; lift the right hand. Then drag a hand's pin onto a square pin.

**Right if:** the menu is the same as a slider's right-click menu; a
cable from the right hand lands on `camera.zoom` at once; the drag onto
the square pin is refused: "a hand sets no base; aim at mod".

**Wrong if:** an empty menu; the cable only after reopening the page.

*(check 248; the desk part is A34)*

## (c) One projector, or any second screen

Plug it in before launching. For C1–C4 the config has no
`[[output.screens]]` list.

#### C1. Choosing the screen; the see-through mode locked

**Needs:** projector.

**Do:**
1. OUTPUT page: open **Screen**; pick the projector; tick
   **Fullscreen**. Press T and the APC40's MASTER button if plugged in.
   Back to "follow window", Fullscreen off.
2. In the config, `[output]` `monitor = 1` and `fullscreen = true`;
   launch.

**Right if:** the list shows "follow window" first, then each screen by
name; the picture fills the projector at its own sharpness (edges as
fine as on the laptop); the control window stays on the laptop; with no
`overlay` line in the config the Overlay switch is greyed with "overlay
off in the config: set [output] overlay = true in config.toml", and T
and MASTER change nothing; "follow window" with fullscreen off returns a
normal window. (2) it opens straight on the projector. (Screen and
Fullscreen are output 1's only; with an output list they come from the
list — see D1.)

**Wrong if:** the wrong screen; blurry edges; the desktop showing through
or T floating the window.

**Changes:** take out `monitor` and `fullscreen` (or leave them for C2).

*(check 26)*

#### C2. A black ground, never see-through

**Needs:** projector; a white web page full screen on the projector,
behind the render window.

**Do:** fullscreen the render window on the projector (OUTPUT page).
Press F for faces. Press F1–F5 in turn, ticking and unticking
**Cut-through** on each.

**Right if:** no desktop anywhere, ever: black ground, faces and lines lit
on black, on every preset, Cut-through on or off, with effects on (TRIP)
and the look-back on (WAKE).

**Wrong if:** the desktop through the faces or faint lines; through the
whole ground (check the OUTPUT page: is it in overlay mode?).

*(check 43; with two outputs, D4 runs it on each)*

#### C3. Windows reopen on the right screen

**Needs:** projector (and unplugging it once).

**Do:**
1. Drag the render window onto the projector; Esc; launch.
2. Set `[output] fullscreen = true` (no `monitor`); launch. Esc; look at
   `<home>/windows.json`.
3. Unplug the projector; launch. Put `fullscreen` back to false.
4. Projector in. Set `monitor = 0`, `control_monitor = 1`; launch. Then
   `monitor = 7`; launch. Then `monitor = "left"`; launch. Remove both
   lines.

**Right if:** (1) it opens on the projector, the control window on the
laptop. (2) fullscreen on the projector with no drag; the file still
holds the windowed size. (3) the render window opens on the laptop at
its default spot, and the terminal and SYSTEM page name the screen it
was last on. (4) the windows swap (render on screen 0, controls on
screen 1); with 7, the note "monitor = 7, but 2 screens are connected
(0–1) — using the last position"; with "left", the app still launches
with "monitor = 'left' is not a screen index — using the last position".

**Know:** a screen number that is not there at launch is ignored for the
whole run — plug in first.

**Wrong if:** a window off every screen; the wrong screen for a number;
the app not launching with "left". If a window cannot be reached, delete
`windows.json`.

*(check 61)*

#### C4. Dream speed on the rig

**Needs:** projector; the dream running.

**Do:** with the render window on the projector, repeat L24 at the same
speed setting.

**Right if:** the dream feels the same speed as on the laptop screen at
the same number (it counts the dream's own frames, not seconds).

**Judge:** if it feels different, say so.

*(check 96)*

#### C5. The hands on the projector

**Needs:** projector; the hand camera; the ghost hands on (HANDS page).

**Do:** in the config, give the projector an `[[output.screens]]` entry
with `hands = true` (as in SETUP.md's example; on the party rig this is
the owner's `config.toml.rig`). Launch, hands in the box.

**Right if:** the ghost hands show on the projector, and the OUTPUT
page's **hands** tick for that output is on.

**Wrong if:** no hands on the projector: that entry says `hands =
false`, the ghost hands are off, or the output is not the screen you
think (screen numbers can move after the HDMI reconnects).

**Changes:** remove the entry afterwards if this is not the rig.

*(check 165)*

#### C6. A hand across the box pans as far as it did

**Needs:** the projector at 1920×1080; the hand camera.

**Do:** load HANDS ORBIT; left hand in the box; move it from the box's
left edge to its right, then from near to far. Then the same on PARTY
FIELD.

**Right if:** the shape's centre (on PARTY FIELD the whole field)
travels about a fifth of the projector's width each way (about 390
pixels), as far as on earlier builds — sideways for side to side, up
and down for reach; with the hand level and centred the shape is where
the mouse left it.

**Wrong if:** the shape barely moves, flies off the screen, or moves the
wrong way up and down.

*(check 199)*

#### C7. A preset saved before this build keeps its place (on the copy)

**Needs:** the projector at 1080p; the copy.

**Do:** load PARTY MANDALA; CAMERA page. Save it as your own preset,
load another, and load it back. Then load any preset of yours saved
before this build with the shape off-centre.

**Right if:** the mandala sits where it did on the projector, a little
right of centre; CAMERA shows Pan X `+0.59`; the saved file has a line
`"units": {"camera.pan": "world"}` and loads to the same place with no
red dot; your older preset sits where it did on the projector. (On the
laptop's smaller window an off-centre shape sits nearer the centre than
it used to: expected.)

**Wrong if:** the shape far from its old place on the projector; a
re-loaded save drifting.

**Changes:** delete the preset you saved.

*(check 201)*

#### C8. Hands as lines, through the acid, with tracers — by dragging (on the copy)

**Needs:** the projector as output 1; the hand camera; the copy.

**Do:** load ACID with the look-back on (LOOKBACK: **Dream** or echoes
on); GRAPH. Drag from the `ghost` box's geometry pin onto `scene`'s
geometry pin. Right-click `ghost` → **draw lines**. Save as a new
preset; open its file.

**Right if:** after the drag the hands are inside the shape, bent by
the acid, trailing tracers; then they are lines; each step puts a red
dot on the preset and ⌘Z takes it back; the file's `"graph"` is
`{"nodes": [{"kind": "hands", "into": "scene", "draw": "lines"}]}`.

**Wrong if:** the drag does nothing; solid hands; no tracers.

*(check 251)*

#### C9. The whole picture as shades of one red

**Needs:** the projector. Plan 30 N8.

**Do:** load TRIP (F3). FX page, open **Palette**, switch it on, raise
its **Mix** to the top (nothing changes yet). Set **hue** 350 → 10,
**sat** 0.6 → 1, **val** 0.3 → 1.

**Right if:** the whole picture is reds — dark red where it was dark,
bright red where it was bright — and no other colour anywhere, no hard
edges between colours. Judge: does it read as "shades of one red"?

**Wrong if:** greens, blues or yellows left; black still black (the
range cut off rather than squeezed in); the picture changing before you
set the slice.

*(check 267)*

#### C10. A yellow slice and its derivations

**Needs:** the projector.

**Do:** as C9, then **hue** 45 → 75, **sat** 0.4 → 1, **val** 0.5 → 1;
then widen the hue to 30 → 90, then 0 → 300.

**Right if:** ambers through yellows to lime-yellows, different parts of
the picture different yellows (not one flat yellow); widening brings in
oranges and greens smoothly; at 0 → 300 most colours are back. Judge
the wide slices.

**Wrong if:** one flat yellow; a seam; a rainbow streak inside red
areas wider than a thin sliver.

*(check 268)*

#### C11. A slice through red; dark turned bright

**Needs:** the projector.

**Do:** as C9, then **hue** 300 → 60. Then hue back to 0 → 360 and
**val** 1 → 0.2.

**Right if:** 300 → 60 gives magentas, reds and oranges only (it goes
up through 0, not the long way); val 1 → 0.2 turns the dark ground
bright and the bright shape dim.

**Wrong if:** greens and blues at 300 → 60; the val change ignored.

*(check 269)*

## (d) The glass and the projector together

*The glass* is the Pepper's Ghost screen. Plug both screens in before
launching; read their numbers off the OUTPUT page's **Screen** list
first (they can change when a display is plugged in). D1 sets up the
config the rest use. Most entries also need the hand camera (calibrated,
B1) and some the APC40. **D12 and D13 last.**

#### D1. Two outputs open where the config says

**Needs:** glass, projector.

**Do:** in the config, under `[output]`, set `control_monitor` to the
laptop's number and remove `monitor` and `fullscreen`. Below that
section paste, with your numbers:

```toml
[[output.screens]]         # output 1: the glass — sets the frame size and pace
name = "glass"
monitor = 1
fullscreen = true

[[output.screens]]         # output 2: the projector
name = "projector"
monitor = 2
fullscreen = true
dim = 0.6                  # optional: its own dim at launch (never under 0.1)
```

Launch. Quit and launch again.

**Right if:** the glass and the projector each go fullscreen with the
same picture; the control window is on the laptop; SYSTEM has no config
note; the OUTPUT page shows two blocks, "1 glass" and "2 projector",
each with three ticks and a **dim** row (100% and 60%), and under them
"paced by output 1 · frame W×H · below: output 1's window"; the same
after relaunch; `<home>/windows.json` has two `render` entries in this
order.

**Wrong if:** one window; outputs swapped (output 1 is the first entry);
an output on the laptop. If the screens differ in size, list the larger
first.

**Changes:** the config; take the `[[output.screens]]` entries out to go
back to one output.

*(check 101)*

#### D2. The eight output states

**Needs:** glass, projector, hand camera.

**Do:** Ghost hands on (HANDS page), a hand in the box, F5 (TRIP). On the
OUTPUT page, walk output 1 through the eight combinations of its
**scene**, **hands** and **through effects** ticks, then output 2:

| scene | hands | through effects | What it shows |
|---|---|---|---|
| on | on | off | the scene with its effects, hands clean on top (the default) |
| on | on | on | scene and hands, both bent by the effects |
| on | off | off | the scene with its effects |
| on | off | on | the same as the row above |
| off | on | off | the hands alone on black |
| off | on | on | the hands alone through the effects; an effect that makes its own light lights the ground |
| off | off | off | black |
| off | off | on | black |

Then switch every effect off; then untick Ghost hands.

**Right if:** each state shows its row on that output only, the other
does not change, and the "shows:" line says what you see; with every
effect off, "through" changes nothing; with Ghost hands off, the hands
leave every output.

**Wrong if:** a change on the other output; echoes showing in the "hands
alone through the effects" state.

*(check 102)*

#### D3. Hands over or through the effects; the guide never bent

**Needs:** glass, projector, hand camera.

**Do:** glass: through effects **on**; projector: **off**. F5 (TRIP),
then F4 (WAKE). Switch every effect off. Then HANDS page: Guide
BESIDE, then ON HAND, Tethers (in **more ▸**) on.

**Right if:** on the glass the hands bend and recolour with the shape; on
the projector they are clean; on neither do the hands leave echoes or
feed the dream, and the echoes are the same on both; with effects off
the two look alike and the glass's block says "through: no effect on";
the guide gauges and tether labels are sharp and identical on both,
never folded or warped.

**Wrong if:** hand echoes; warped labels; different echoes on the two.

*(check 103, 47)*

#### D4. The dims

**Needs:** glass, projector, APC40.

**Do:**
1. Crossfader to the middle. Output 2's dim to half. Crossfader left.
2. Untick and tick an output switch, ⌘Z. Press F1, and load a show.
3. Quit, launch.
4. With a white page behind each output, repeat C2 (faces, F1–F5,
   Cut-through on and off) on both.

**Right if:** (1) both dim together; only the projector dims further and
its "shows:" line ends in the product ("· 30%" at master 60%); left:
both black, the footer "dim black". On the glass the ground stays solid
black at every dim, never grey or see-through. (2) ⌘Z does not take a
switch back; loads leave switches and dims alone. (3) master full, the
projector's dim back to the config's 60%, switches as the config says.
(4) no desktop on either (every output after the first is always
solid).

**Wrong if:** the wrong product; a switch moved by ⌘Z or a preset; the
desktop through the glass.

*(check 104, 55, 43)*

#### D5. Black is never a mystery

**Needs:** glass, projector.

**Do:** on the OUTPUT page, one output at a time: untick scene and
hands; then scene off and hands on with no hand in the box; then scene
on and its own dim to 0; then the crossfader left. Then Ghost hands off
with an output's hands ticked; then through effects ticked with no
effect on.

**Right if:** its "shows:" line, in the warning colour, reads in turn
"black — nothing switched on", "black — the scene is off and no hand
shows", "black — dim 0", "black — master dim"; for the first three the
footer on every page adds "· output 2 black" ("· outputs 1, 2 black" for
both); for the master only "dim black". With Ghost hands off: "hands:
ghost hands are off (HANDS page)" (with no camera: "hands: no
tracker"); with nothing to go through: "through: no effect on".

*(check 105)*

#### D6. An output of another shape

**Needs:** glass, projector, hand camera.

**Do:** if the two screens differ in shape, look at output 2. If not, set
its `fullscreen = false`, launch, and drag its window tall and narrow.

**Right if:** output 2 shows the whole frame centred with black bars,
circles round, nothing cropped, the hands on the same part of the shape
as on the glass.

**Wrong if:** stretched or cropped; the hands off their place.

**Changes:** put `fullscreen = true` back.

*(check 106)*

#### D7. Frame rate and tearing with two screens

**Needs:** glass, projector, hand camera. Nobody has seen this hold: in
scripted runs on one screen the app ran unlimited, at about 270–380
frames a second, and the one-window path did the same.

**Do:** both fullscreen, F5, a hand in the box, output 1 through effects
on and output 2 off. Note both screens' refresh rates (System Settings →
Displays). Watch the footer's FPS; watch the projector during fast
rotation; after five minutes look at `stall.log`.

**Right if:** FPS holds at the glass's refresh rate; no tearing (a
horizontal split in the picture) on the projector; no new stall log
entry.

**Wrong if:** half the refresh rate; tearing on the projector; far above
the refresh rate (the screen is not pacing the app at all). Note what
you see either way.

*(check 107)*

#### D8. The ghost hands follow the real ones

**Needs:** glass, hand camera.

**Do:** HANDS page: tick **Ghost hands**, opacity about 60%. Sit where
you perform, both hands in the box. Check:
- **Left and right not swapped:** raise only the left hand — the
  near-white hand on the left of the picture moves; the light red one is
  on the right.
- **Fingers:** spread, fist, pinch thumb to each finger, point: every
  finger follows, thumb on the correct side, nothing bending backwards.
- **Directions from the performer's side:** right is right, up is up,
  toward the screen goes away; palm down shows the back of the hand.
  Then tick **Mirror** (in **more ▸**) and look in the glass as the
  audience will.
- **No lag:** shake a hand — the ghost stays on it; hold still — no
  shimmer.
- **The box fills the frame:** reach each calibrated corner — the hand
  stays in frame, near the edge.
- **Leaving:** pull a hand out — it fades where it was in about a third
  of a second and fades back in on return; nothing freezes or jumps.
- **Off is off:** untick Ghost hands — the picture is as before.
- **The guide:** Guide BESIDE. Move the right hand straight right,
  then up, then toward the screen: each time one ball moves (red, green,
  blue) and the others stay. Tilt fingers up, turn them outward, roll
  thumb-up: the red arc's dot rises, the green's goes out, the blue's
  turns; no dot leaves its arc. Pinch each finger: its bead lights. Fist:
  the grab ring shrinks round a full ball. Route a few left-hand axes and
  none on the right (ROUTING): the routed left ones keep their colour,
  everything on the right is grey and smaller but still moves. ON HAND:
  the gauge rides the palm. Tick **Tethers** (in **more ▸**): each routed left axis
  gets a line in its colour to a label at the left edge naming its
  setting; the lines hold still while the balls move; untick and the
  gauges stay.
- If the rig ever uses `screentop`, repeat the directions there.

Then record the hand tape others will test against: `uv run python
tools/hands_tape.py record tests/fixtures/hands/rig.json --seconds 6` —
both hands, open, fist, pinches, in and out of the box — and commit it.

**Right if:** every point above holds. Note which Ghost mirror setting
the rig wants and save it in the show.

**Wrong if:** swapped or mirrored hands; a finger on the wrong digit or
bending wrongly; lag.

**Changes:** the tape file, a new file in the repository.

*(check 108, 47)*

#### D9. The five hand styles from the audience

**Needs:** glass, hand camera.

**Do:** HANDS page, Ghost hands on: the **Style** list. With both hands in
the box, step through from where the audience stands: HANDS (capsule
hands), JOINTS (a bead per joint, largest at the fingertips), PALMS (an
orb that swells as the hand opens, a ring, a spoke where the fingers
point), CAGE (a wire diamond shape that turns with the palm and breathes
with the grip), MARIONETTE (fingertip beads on strings from a bar above).
Try the guide ON HAND with each. Quit and launch.

**Right if:** each follows with no lag; the orb and cage open and close
with your grip; a leaving hand fades in every style; ON HAND, the guide
is on top in the four new styles and partly behind the palm in HANDS;
the frame rate does not change; the style is kept after relaunch.

**Judge:** which styles to keep; whether a real fist or open hand reads
wrong (the grip was tuned on fake hands only).

*(check 109)*

#### D10. Effects on the faces, on the rig

**Needs:** projector, then glass.

**Do:** repeat L15's looks on the projector and then on the glass:
Kaleidoscope on the faces with a picture loaded, per face and screen;
Plasma on the faces over FLAT. Stand where the audience will.

**Right if:** in screen mode the picture is sharp enough at room size and
not stretched (cropped top and bottom on a wide output); per face, a
face near the camera shows no blocks; on the glass, no desktop or grey
through the faces.

**Judge:** whether the faces' effects read at all at the faces'
brightness, per face especially, or need the pattern mix or brightness
up (say which preset).

**Wrong if:** soft or blocky; squashed; see-through faces on the glass.

*(check 98)*

#### D11. The party presets on the rig

**Needs:** glass, projector, hand camera, APC40.

**Do:** party show. F1 TUMBLE, F2 FACES, F3 FIELD, F4 WAKE, F5 TRIP, F6
ACID, F7 MANDALA, F8 NOITA, then TRACER from the list. The performer
cards in `docs/plans/assets/12-presets/party-*.md` say what each hand
does. For TRIP, first tap TAP TEMPO eight times and press METRONOME once.
Turn the device knobs on each.

**Right if:**
- faces at 2.5× (FACES) and 2.0× (TUMBLE, WAKE) read in the room, and the
  left hand's headroom up to 4× is usable, not a white-out;
- a tilt's ±45° feels like holding the object, and the half-second
  spring back when you let go reads as "let go", not a slip;
- thumb up is up, fingers out is out, reaching in is away, on every row
  (the cards' words);
- FIELD at the right hand's top (69 copies, faces on) holds its frame
  rate and the swing looks deliberate, not messy;
- WAKE with the dream: right roll turns the dream's colour round the
  wheel, fingers up brings the dream in; the wake reaches past the faces;
- TRIP: the left hand's height opens a pump on the beat and the burst at
  the right hand's top is light, not glare;
- ACID, MANDALA, NOITA and TRACER keep a black ground with no hand in the
  box (MANDALA's plasma comes in only with right fingers up);
- the device knobs D1–D8, each ring showing its value — WAKE: echo
  brightness, echo fade time, darken, contrast, shape hides, dream
  brightness, dream saturation, dream speed; TRIP: FX mix, plasma level,
  kaleidoscope segments, kaleidoscope zoom, zoom burst amount, zoom burst
  glow, hue cycle paint, hue cycle spread; ACID: FX mix, acid bend, twist,
  reach, breathe, wobble amount, deconverge amount, hue cycle spread;
  MANDALA: FX mix, plasma level, kaleidoscope segments, kaleidoscope zoom,
  fractals amount, fractals ground, glimmer amount, glimmer ground; NOITA:
  FX mix, trip warp amount, trip warp scale, trip colour amount, fractals
  amount, fractals size, double vision amount, double vision ghost;
  TRACER: echo brightness, echo fade time, echo count, echo time apart,
  darken, contrast, shape hides, 4D depth; on TUMBLE, FACES and FIELD
  D1–D4 are 4D depth, yaw, pitch and pattern and D5–D8 dark; TUMBLE's
  left height still pushes the sound drive, marked "session" in its row
  (click the leap → master wire on GRAPH).

**Wrong if:** a look off (a number in the preset); a knob on the wrong
setting; an axis flipped on every preset (then flip it on the HANDS page
and save the hands setup).

*(check 41, 32)*

#### D12. A screen not plugged in at launch

**Needs:** glass, projector; D1's config.

**Do:** quit, unplug the projector, launch. Plug it in while running.
Then ⌘R.

**Right if:** only the glass opens; the OUTPUT page shows output 1's
block and one greyed line "2 projector — screen 2 is not connected";
SYSTEM and the terminal say "config: output 2 (projector): monitor = 2,
but 2 screens are connected (0–1) — not opened" (your numbers); plugging
in while running does nothing; ⌘R opens it.

**Wrong if:** a third window on the laptop; output 2's settings present.

*(check 111)*

#### D13. Unplug the projector mid-run — last

**Needs:** glass, projector; D1's config. Last, since it may leave a
window somewhere odd.

**Do:** both outputs running, pull the projector's cable; wait ten
seconds; plug it back.

**Right if:** the glass never stops or freezes; the app keeps running;
the control window names output 2 if its picture failed ("output 2
(projector): its picture failed — …" or "… no picture for 2 s — …");
after replugging the projector shows the picture again (or say what it
does — it may need ⌘R). Nobody knows yet what macOS does with a
fullscreen window whose screen disappears: note it.

**Wrong if:** the app dies; the glass freezes; a projector window ends
up over the laptop's controls.

*(check 112)*

#### D14. The shapes in 4D from the audience

**Needs:** glass (the projector too, if you like).

**Do:** repeat L48 and L50 on the glass, from where the audience stands,
with music.

**Right if:** as in L48 and L50: no shape goes flat; they read as solid
shapes turning through themselves.

**Judge:** which shapes to use in a show.

*(checks 113, 115)*

#### D15. METER and PULSE from the audience

**Needs:** glass (or projector), music through the microphone or the
Mac's own sound.

**Do:** faces on, METER; then PULSE; then stop the music.

**Right if:** METER shows a wedge of lights per band, the deepest band's
at twelve o'clock and the rest clockwise, each lit outward as loud as
its band; the kick lights the first wedges, the hi-hats the last. PULSE:
the kick swells a magenta disc and throws a ring, the snare shoots
yellow rays, the hi-hats sparkle. In silence METER shows dim tracks and
PULSE a slow heartbeat.

**Judge:** whether each reads from where the audience stands.

**Wrong if:** nothing moves with music (is the sound on? AUDIO page);
the wrong wedge lights.

*(check 129)*

#### D16. Every picture as on earlier builds, on the rig

**Needs:** glass and projector (D1); the hand camera; the APC40 for the
crossfader.

**Do:** the glass with hands over, the projector with **through
effects** ticked; load TRIP; LOOKBACK's **Look-back** on; crossfader
half down. Move a hand in and out of the box; untick **Effects** (FX
page) and tick it again; close the projector's output (untick its
**scene** and **hands**) and back. Then step one output through the
eight states as in D2.

**Right if:** nothing looks different from the last build: the hands
clean over the effects on the glass, bent through them on the
projector, echoes behind the shape, both outputs dimmed alike; through
with no effect on is hands over; each state as D2 lists.

**Wrong if:** any change from before; the hands twice or missing on one
output; an output on black with a note on the OUTPUT page.

*(checks 195, 208)*

#### D17. The hands in the shape on the projector, clean on the glass (on the copy)

**Needs:** glass and projector; the hand camera; the copy with
`hands-solid.json` (Part 1, "The render graph").

**Do:** OUTPUT page: the projector with **scene** and **hands** ticked,
the glass with **scene** unticked and **hands** ticked. Load
HANDS-SOLID; move both hands through the shape.

**Right if:** on the projector the hands are inside the shape — in front
of some edges, behind others, bent with it by the acid; on the glass the
same hands alone, clean and unbent, on black; the projector's "shows:"
line reads "scene + hands: in the scene".

**Wrong if:** the glass blank; the hands twice on the projector.

*(check 206)*

#### D18. Two hands, one in the shape, one on the glass (on the copy)

**Needs:** glass and projector; the hand camera; the copy with
`two-hands.json` (Part 1, "The render graph"); the SYSTEM page.

**Do:** D17's switches. Load TWO-HANDS. On ROUTING find **Ghost 2
hands** and switch it on (it starts off, like every new switch); set
**Ghost 2 mirror** on and **Ghost 2 style** to CAGE. Load TRIP, then
TWO-HANDS again. Save the show (PRESETS page), quit, launch again and
load TWO-HANDS.

**Right if:** the projector shows solid hands inside the shape; the
glass shows mirrored cage hands alone; SYSTEM lists `ghost`, `scene`,
`hands.2` and `readout`; on TRIP the glass shows the usual hands and
`hands.2` leaves SYSTEM; back on TWO-HANDS the mirror and the cage are
back; after the restart, on TWO-HANDS, they are still there and the
show has no red dot.

**Wrong if:** the same hands on both screens; the projector's hands
mirrored too; the cage lost after the restart.

*(check 213)*

#### D19. Each output still gets its own effects (shader nodes)

**Needs:** glass and projector (D1); the hand camera; the SYSTEM page.

**Do:** OUTPUT page: the projector with **scene**, **hands** and
**through effects** ticked; the glass with **scene** unticked and
**hands** and **through effects** ticked. Load ACID; a hand in the box.
Then tick **Flip X** on the glass.

**Right if:** the projector bends the hands with the shape, the glass
bends the hands alone, both as on earlier builds; SYSTEM shows
`acid(scene+hands)` and `acid(hands)` lines; the flip mirrors the glass
only.

**Wrong if:** the glass showing the projector's picture; an effect
applied twice; the flip on both.

**Changes:** untick **Flip X** and the two **through effects**.

*(check 222)*

#### D20. The palette on the hands, on both screens (on the copy)

**Needs:** glass and projector (D1: the glass is output 1, the projector
output 2); the hand camera; the copy with `palette-hands.json` (Part 1,
"Shader nodes").

**Do:** OUTPUT page: **hands** ticked on both outputs. Load
PALETTE-HANDS; move your hands in front of the shape on both screens.

**Right if:** on both screens the hands are recoloured blue-cyan and the
shape is not, at the hands' usual see-through look; the guide is not
recoloured.

**Wrong if:** the hands recoloured on the glass but plain on the
projector (the second screen did not get the recoloured hands); a dark
rim round the hands.

*(check 223)*

#### D21. One screen recoloured (on the copy)

**Needs:** glass and projector (D1); the copy with `palette-glass.json`
copied in (Part 1, "Shader nodes").

**Do:** load PALETTE-GLASS. OUTPUT page: untick output 2's **scene**
and **hands**, then tick them again. Then edit the copy's
`palette-glass.json`: change `"output.2"` to `"output.1"`; load it
again.

**Right if:** the projector (output 2) shows the acid recoloured to
blue-cyan while the glass keeps the rainbow; output 2's "shows:" line
ends "· palette on this output only"; with its scene and hands unticked,
OUTPUT lists "dormant: palette into output.2 — output 2 shows no picture
this frame", and ticking them brings the colour back; after the edit,
the glass is recoloured and the projector is not.

**Wrong if:** both screens recoloured; output 2 black; the projector
plain where it should be recoloured.

**Changes:** delete the file.

*(check 224)*

#### D22. The trail holds the bent shape (on the copy)

**Needs:** glass and projector; the copy with `acid-scene.json` copied
in (Part 1, "Shader nodes").

**Do:** load ACID-SCENE; LOOKBACK page.

**Right if:** the mandala heaves with the second acid on both screens;
its trail follows the heaved shape, not a straight one; LOOKBACK reads
"history: the scene · acid 2 before the history".

**Wrong if:** the trail straight while the shape heaves.

*(check 227)*

#### D23. Two palettes, a different colour on each screen (on the copy)

**Needs:** glass and projector (D1); the copy.

**Do:** copy `palette-glass.json` into `<home>/presets/` as
`two-palettes.json` and replace its `"graph": {"nodes": [` … `]},` part
with `"graph": {"nodes": [{"kind": "effect", "file": "palette", "into":
"output.1"}, {"kind": "effect", "file": "palette", "instance": 2,
"into": "output.2"}]},`; after `"fx.palette.hue_to": 230.0` add `,
"fx.palette.2.on": true, "fx.palette.2.mix": 1.0,
"fx.palette.2.hue_from": 0.0, "fx.palette.2.hue_to": 60.0`. Load
TWO-PALETTES; FX page; then ROUTING, and drag Palette 2's hue turn.

**Right if:** the glass is blue-cyan and the projector orange-red; FX
shows two placed chips, "Palette · into output 1" and "Palette 2 · into
output 2", each with its own controls; dragging Palette 2's hue turn
changes only the projector; ROUTING lists "Palette 2 …" settings; each
output's "shows:" line ends "· palette on this output only" or "·
palette 2 on this output only".

**Wrong if:** both screens one colour; the colours on the wrong
screens; one chip.

**Changes:** delete the file.

*(check 231)*

#### D24. A second pair of hands on the glass alone (on the copy)

**Needs:** glass and projector (D1: the glass is output 1); the hand
camera; the copy.

**Do:** copy `tests/fixtures/presets/hands-glass-only.json` into
`<home>/presets/` as `hands-glass-1.json` and change its wire's
`"output.2.hands"` to `"output.1.hands"`. Both outputs on scene + hands.
Load HANDS-GLASS-1; on HANDS tick **Ghost hands 2**. Then untick the
projector's hands; then put the glass on **through**.

**Right if:** the projector shows the hands as lines inside the shape and
no solid hands; the glass shows the same plus a solid pair laid over;
OUTPUT's line for output 1 ends "· hands 2 over output 1"; the
projector's hands switch changes nothing on the glass; on through the
glass still shows the solid pair once.

**Wrong if:** solid hands on the projector while it shows the shape; no
solid hands on the glass (Ghost hands 2 off); the hands doubled or gone
on through.

*(check 252)*

#### D25. Two outputs, two pictures, by wires (on the copy)

**Needs:** glass and projector (D1); the copy.

**Do:** the projector (output 2) on **through**. Copy
`tests/fixtures/presets/wired-outputs.json` into `<home>/presets/` and
load WIRED-OUTPUTS; look at SYSTEM and FX.

**Right if:** the glass shows the acid look folded to blue-cyan; the
projector shows the shape through a second acid only — no wobble, no
colour cycling, no hands; output 2's "shows:" line reads "acid 2 by a
wire"; SYSTEM lists `wire(output.2)`.

**Wrong if:** both screens blue; the projector showing the whole chain.

*(check 254)*

## (e) A mouse

#### E1. Drag an effect with a mouse

**Needs:** a mouse. The trackpad version is L18.

**Do:** repeat L18 with the mouse.

**Right if:** the same as L18.

*(check 94)*

## (f) A gamepad

#### F1. A wired Xbox 360 pad is found

**Needs:** a wired Xbox 360 pad (the Afterglow AX.1) on USB, no other
pad connected.

**Do:** launch from a terminal.

**Right if:** the terminal says `gamepad: Afterglow Gamepad for Xbox 360
over USB`; the pad's ring lights one quarter (player 1) instead of
blinking; B / X step to the next / previous preset of the PRESETS page's
list (its drop-down, by name, wrapping; a preset saved a moment ago is
in it — not the desk's bank), A flips faces and Y lines, LB / RB step the shape, the D-pad steps brightness (up / down)
and speed (left / right), START and BACK do nothing, the left stick
orbits (up tilts the camera up; held, it tumbles over the top and keeps
going round, as the sideways orbit does) and its click resets the
camera, the right stick's up / down zooms and its right / left speeds
up / slows (through zero into reverse) the spin in the XW, YW and ZW
planes, and its click stops those three and turns them back to 0°, RT
pushes the 4D depth in and LT out.

**Wrong if:** no line; a button does another one's job; a stick runs
backwards.

*(check 144)*

#### F2. Learn pad — a button

**Needs:** a pad.

**Do:** VIEW page: right-click Points → **Learn pad**. Press Y on the
pad. Then right-click Brightness → **Learn pad** and press the D-pad's
down. Afterwards put Y back: right-click Lines → **Learn pad**, press Y.

**Right if:** the footer says `learned view.points ← …(into
bindings.json); view.lines let go`; Y now flips points; the D-pad's
down still dims (one detent a press); `bindings.json` holds `pad:Y` →
`view.points`. Pressing Y during the learn did not also flip the lines.

**Wrong if:** the press does nothing; Y does two things; a desk knob
turned during the learn completes it.

*(check 145)*

#### F3. Learn pad — a stick and a trigger

**Needs:** a pad.

**Do:** CAMERA page: right-click Pan X (or any centred setting) →
**Learn pad**, push the right stick left. Then right-click
Field amp (VIEW page) → **Learn pad**, squeeze RT.

**Right if:** the ROUTING page shows `right stick X pushes` on the first
and `right trigger positions` on the second; the first swings about its
value and comes back when the stick is let go; the second follows the
trigger and RT no longer rides the 4D depth, while LT still does. Save
the preset, reload it: both routes are still there.

**Wrong if:** the stick still orbits after its route is made; letting
go leaves the setting moved.

*(check 146)*

#### F4. Momentary and hold on a pad button

**Needs:** a pad; `bindings.json` open in an editor.

**Do:** change the `pad:Y` row's op to `"momentary"` and, for a button
with a trigger on it (`pad:B` → `preset.list.next`), to `"hold"`. ⌘R.

**Right if:** lines show only while Y is held; B steps the preset only
after about 0.6 s held, once per press; a tap does nothing.

**Wrong if:** lines stay on after Y is let go; B fires on a tap or
repeats while held.

*(check 147)*

#### F5. The pad after a restart, and its sticks

**Needs:** the wired pad. Plan 27.

**Do:** press ⌘R three times, a few seconds apart. Then repeat F1's
sticks and triggers, with SYSTEM → gamepad → feel on follow and on
spring; then F3.

**Right if:** after each restart the pad is found within a few seconds
(ring lit, sticks orbiting) and its SYSTEM line says `connected`; the
sticks and triggers do exactly what F1 says; a stick learned onto a
setting drives it and stops orbiting.

**Wrong if:** a dead pad after a restart (the ring blinks); nothing
moves; a learned stick still orbits.

*(checks 171, 179)*

#### F6. Two pads at once (on the copy)

**Needs:** the Xbox pad paired over Bluetooth and the wired pad (the
Afterglow) on USB. Plan 27 B6.

**Do:** in the copy's `config.toml`, put the two-pads block from
`docs/plans/27-device-registry.md` ("The block to paste") in place of
the `pad` entry: `pad`, then `p2` (both keep `usb = true`). Save. Look at
SYSTEM → devices. Right-click Points → **Learn pad**, press A on the
wired pad; right-click Field amp → **Learn pad**, squeeze the wired
pad's RT. Use both pads together. Unplug the wired pad; plug it back.
Turn the Xbox pad off and on.

**Right if:** two lines, `pad · gamepad · connected · … · glfw 0 · usb:
lent to p2` and `p2 · gamepad · connected · … · usb: Afterglow …`; the learns say "pad A
on p2" and "right trigger on p2"; the Xbox pad does everything it did
(A flips faces, the sticks steer); the wired pad's A flips points, its
RT rides Field amp and its sticks do nothing else; both at once.
Unplugged, `p2` reads `lost` and the Xbox pad keeps working; plugged
back, `connected` again. The Xbox pad off: `pad` reads `lost · usb:
lent to p2`, the wired pad keeps working, and **Learn p2** on a setting
completes from the wired pad.

**Wrong if:** `p2` reads `lost` while the Xbox pad is connected; with
the Xbox pad off, `pad` takes the wired pad; one press does both pads' jobs; the
wired pad's stick turns the camera.

*(check 219)*

## (g) A second controller, a phone (OSC)

Plan 27. Each of these adds an entry to the config file's device list
while the app runs (on the copy); the blocks are in
`hyperspace-python/docs/plans/27-device-registry.md`.

#### G1. A second MIDI controller learned onto a knob

**Needs:** the APC40 and any second USB MIDI controller with knobs; the
copy.

**Do:**
1. Plug in the second controller. Add an entry: `role = "launch"`,
   `kind = "midi"`, `profile = "generic"`, `port = "<part of its
   name>"`; save.
2. Right-click Field amp (VIEW page) → **Learn desk**, turn a knob on the
   second controller, and sweep it through the slider's value.
3. Turn the APC40 knob with the same number. Save the preset as a copy,
   load another, load it back.

**Right if:** (1) `launch · midi · connected · 0 sources · <its port> ·
0 bindings`; its lights do nothing new (the app sends it nothing). (2)
the footer says "learned view.inst_amp ← MIDI CC n ch1 on launch (into
the preset)"; the knob takes hold once it passes the value, then drives
it. (3) the APC40's knob does not move it; any APC40 knob already on
Field amp still works; after the reload the second knob still works.

**Wrong if:** "error: … matches no port" (give the entry a `port`); the
APC40's same knob moves it; the controller's lights flicker.

**Changes:** remove the entry; unbind the knob.

*(check 176)*

#### G2. SHIFT is the APC40's

**Needs:** G1's set-up.

**Do:** latch SHIFT on the APC40. Turn the second controller's learned
knob; right-click another setting → **Learn desk** → turn another knob on
the second controller; then try **Learn desk** with an APC40 knob.
Unlatch. Latch SHIFT again and load a preset.

**Right if:** under SHIFT the second controller's knob still works and
its learn lands; the APC40 learn is refused ("… on the global layer …
latch SHIFT off …") and stays armed; the load drops the APC40 back to
the preset layer.

**Wrong if:** the second controller goes dead under SHIFT; its learn is
refused.

*(check 177)*

#### G3. A phone's fader moves a setting

**Needs:** a phone with an OSC app (TouchOSC, or any) on the same Wi-Fi
as the Mac; the copy.

**Do:**
1. In the app set the host to the Mac's address (System Settings →
   Wi-Fi → Details) and the port to 9000; note its first two faders'
   addresses (TouchOSC's simple layout: `/1/fader1`, `/1/fader2`).
2. Add the phone block with `axes = ["/1/fader1", "/1/fader2"]`; save.
3. Move fader 1. Right-click Yaw (CAMERA page) → **Learn phone**, move
   fader 1 a good way; move it again.

**Right if:** (2) `phone · osc · lost · 2 sources · UDP 0.0.0.0:9000`;
macOS may ask whether Python may accept incoming connections — allow.
(3) the line says `connected` and shows the last message; the learn
lands and the yaw then moves with the fader; ROUTING's source list has
`phone`.

**Wrong if:** the line stays `lost` (the app's address or port, or the
firewall question was denied: System Settings → Network → Firewall); no
"Learn phone" item; `error: … in use` (another program has port 9000).

*(check 186)*

#### G4. A phone's button

**Needs:** G3's set-up.

**Do:** add the app's first button's address to `hits` (TouchOSC:
`/1/push1`); save. Right-click **Faces** (VIEW page) → **Learn phone** →
press the button; then press it a few times.

**Right if:** the learn lands (a row in `bindings.json`); each press
flips the faces once; letting go does nothing.

**Wrong if:** each press flips twice (set the button's off value to 0
in the app); nothing (the address is not in `hits`).

*(check 187)*

#### G5. The phone goes quiet

**Needs:** G3's set-up, with the learned yaw.

**Do:** leave the phone alone ten seconds, then move the fader. Add
`hold = false` to the entry, save, and repeat.

**Right if:** about five seconds after the last message the line says
`lost` and the yaw stays where the fader left it; the next move brings
`connected` back and the yaw follows. With `hold = false`, after five
seconds the yaw goes back to its setting.

**Wrong if:** the yaw snaps back without `hold = false`; the line never
says `lost` (fine if the app sends all the time, like a tilt sensor
page).

*(check 188)*

#### G6. Port 9000 already taken

**Needs:** G3's set-up; a terminal.

**Do:** quit the app. In a terminal run `python3 -c "import socket; s =
socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('0.0.0.0',
9000)); input()"` and leave it waiting. Launch. Then press Return in
that terminal.

**Right if:** `phone · osc · error: OSError: … Address already in use`
and one note, everything else running; within about ten seconds of
Return it says `lost`, then `connected` at the phone's next message.

**Wrong if:** the app stalls; the line stays `error`.

*(check 189)*

---

## What a person has to judge

These are opinions, not pass or fail. Each has a sensible default; say
what you want changed.

- **Knob smoothing at 80 ms** — does a knob feel late or right? Try 50
  and 200 ms. (A17, B27; checks 78, 79)
- **The palette as compression** — does a red slice read as shades of
  one red, a yellow slice as yellows and their derivations, and how do
  slices wider than 180° look (they slide from the fold towards the
  whole wheel)? (C9–C11; checks 267–269)
- **The GRAPH page at a distance** — can you hit a pin and read a box on
  the laptop at the control window's normal size? Is the selected route's
  row better under the canvas or beside it? (L111, L113; checks 245, 247)
- **Pictures on GRAPH** — are the thumbnails big enough to read across
  the room? Is the tint's ±20° lean too subtle, or should it stay off?
  (L174, L176; checks 370, 373)
- **The modifiers' defaults** — a smooth's 0.35 s release, a threshold
  at 0.6 / 0.4, a curve's shape range: do they feel right on music?
  (L107, B43; checks 236, 241)
- **The dream-layer menu's words** — each of the 25 layers has a few
  words on what it draws, written from offscreen pictures and depth;
  which are wrong, and are 25 too many? (L23; check 95)
- **Which hand styles to keep** — HANDS, JOINTS, PALMS, CAGE, MARIONETTE.
  (D9; check 109)
- **The dream's look** — save two or three dream presets you like as
  candidates to ship; and whether "speed" is the speed you meant. (L22,
  L24, C4; checks 9, 96)
- **The default hand feel** — Steadiness, Response, Catch, Return;
  saved as `factory`. (B5; check 16)
- **The shapes, 4D and 3D** — whether the 3D shapes are lively enough
  without the W planes (plan 28), the 3D switch, and the Klein bottle's
  look. (L48–L51, D14; checks 113–116)
- **The face patterns** — whether one set of routes reads on every
  pattern, the new patterns as art, METER and PULSE from the audience,
  and whether the factory presets answer quiet and loud music. (L61,
  L65, L66, D15; checks 122, 131, 132, 129)
- **The macro candidates** — which to keep, and as what. (A20–A23;
  checks 133–136)
- **The party fixes' feel** — the two-handed save on the real desk, the
  sound faders one SHIFT away, whether "dead" in the coverage report is
  what you call dark, the click-to-map list, every new hand source's
  range and the grab's thresholds on real hands, and the palette fold
  on the projector. (A24–A32, B30–B36, L69; checks 148–167)
- **The device registry's choices** — whether a second desk's rows
  should carry its name (`cc@launch:…`) and have no SHIFT of their own;
  whether five seconds of silence is the right moment for a phone to
  read `lost`, and whether its faders should hold their place then;
  whether sending a setting out should land at once, as it does, or wait
  like the other learns. (G1–G5, L77–L79; checks 176–188)
- **The render graph's looks** — every factory preset against its
  golden picture; whether strokes should grow with the zoom (the
  default) or keep their size (Screen strokes); the hands' size and
  perspective through the shape's camera; solid hands inside the shape;
  whether the wire hands read as "hands as lines"; the point cloud's
  dots. (L83, L87, L92, L94, L84, B39; checks 192, 197, 198, 203, 204,
  214, 216–218)
- **The shader nodes' looks** — whether the palette on the hands reads
  as the colour you meant from a distance (the ghost hands are pale), a
  palette per screen, and whether the FX page's placed chip reads
  clearly. (L98, L102, D20, D21, D23; checks 223, 224, 229, 231)
- **The step sequencer's feel** — whether the drum pattern feels tight
  against music at 120–175 BPM, and whether the SEQ grid and the yellow
  playhead read from across the room, on screen and on the desk. (L140,
  L141, A38, A39; checks 281, 282, 287, 288)

Smaller calls along the way: the Ghost mirror setting for the glass (D8;
108); `hands-orbit`'s directions and zoom (B18; 80); whether faces'
effects read from the audience (D10; 98); whether amber pads can be told
from green on the real desk (A15; 82); whether a Learn should add rather
than move a row (B17; 77); whether a second pinch should glide (B11; 23);
the click-a-control dimming and its 20 seconds (A16; 70); the Star's
lantern, the Starfruit's ridges, the Rose's depth and the Möbius strip's
width (L50; 115); presets that show a changed shape (L53; 118); whether a
pause mid-drag should be one undo step or two (L31; 48); HEX with ORBIT
overlapping (L28; 97); the bottom of the instances knob being nothing
(A18; 62); the dimmed sliders of an idle effect (L14; 60); readable desk
labels and the `◌` mark from a distance (L37, B4; 69, 73); the 11-pixel
page shift (L3; 81); the filter's hidden new route (L38; 71).

## Unclear in the source

Places where the check text did not say exactly what to do; the entries
above follow the most likely reading, flagged here.

- **L10 (check 33):** written for the first launch of a build from late
  September; whether your home folder still needs that conversion is not
  known.
- **L6 (check 3):** "plug in or switch on another sound input" — which second sound input
  is not said; any will do.

## Glossary

**4D depth** — how strongly the four-dimensional shape is projected into
three dimensions; a VIEW page setting.

**ANALYZER page** — the page showing the sound split into frequency
*bands*, with each band's settings.

**APC40** — the Akai APC40 (first model), a USB MIDI control desk with
pads, knobs and faders; the app's main hardware controller.

**APC40 buttons** — TAP TEMPO (tap the beat), NUDGE − / + (shift the
beat slightly), METRONOME (marks the "one"), QUANT (next preset), OVERDUB
(Home), DETAIL (key legend), SHIFT (the second layer), DEVICE ON/OFF
(the big desk drawing), MASTER (overlay mode), STOP ALL (reset the
scene). The labels printed on the desk are the maker's; these are the
jobs the app gives them.

**AUDIO page** — the page for the sound input (microphone or music file)
and its master levels.

**Axis (hand)** — one measured movement of a hand: side to side (x),
height (y), reach (z), roll, tilt (pitch) and turn (yaw). Twelve for two
hands.

**Band** — one slice of the sound's frequency range (SUB, BASS…). Each
band produces a *lane*.

**Band scene** — a saved set of all the sound bands' settings, picked
from pad rows 2–3 with SHIFT latched.

**Bank / slot (pads)** — a show's list of 24 numbered places for presets,
the desk's pads: slots 1–8 are F1–F8 and pad row 1, slots 9–24 are pad
rows 4–5. Set on the desk only (hold a pad, or SAVE + a pad); the PRESETS
page shows none of them since 2026-10-28.

**Bindings file** — `bindings.json` in the home folder: the control
mapping that belongs to the setup rather than to any preset (keys, the
desk's fixed buttons, faders).

**Bitmap** — a picture file shown inside the faces.

**BITMAP page** — the page for loading a picture to show inside the
faces.

**Box view** — the HANDS page's drawing of the camera's view, with a dot
for each palm.

**BPM** — beats per minute, the tempo.

**Cage, joints, marionette, palms** — ghost-hand *styles*; see D9.

**CAMERA page** — the shape's camera settings (zoom, yaw, pitch, pan),
and under **eye** the fixed camera everything is seen through.

**Catch** — how quickly a value glides onto a hand that has just come
back into the box, instead of jumping.

**Cheat sheet** — the key legend in the control window, shown and hidden
with `/`.

**Chip** — a small clickable label, such as one effect on the FX page.

**Click-through** — an OUTPUT page switch that lets mouse clicks pass
through the render window to whatever is behind it.

**Clip-stop row** — the row of eight buttons under the APC40's pad grid;
the eighth is SAVE (hold it and tap a pad to save into that pad's slot),
the other seven are free for Learn.

**Control window** — the window with the pages and settings, as opposed
to the render window.

**Crossfader** — the APC40's horizontal slider at the bottom right; it is
the *master dimmer*.

**Cue knob** — the single knob in the APC40's master column; here it
steps through the 26 shapes.

**Cut-through** — a VIEW page switch; it only matters in *overlay* mode,
where it lets the desktop show through overlapping faces.

**DAW** — music software such as FL Studio.

**Dead zone** — a small range around the middle of a hand axis that
counts as no movement.

**Desk** — the APC40. "The on-screen desk" is its drawing in the control
window's bottom-left corner.

**DESK section** — the part of the ROUTING page listing which desk
control does what in the loaded preset.

**Desktop / screentop mode** — how the hand camera is mounted: face-up
on a table (desktop, the usual) or on top of a screen facing the
performer (screentop).

**Device knobs** — the eight lower-right knobs on the APC40 (D1–D8).

**Device list** — the `[[devices]]` entries in the config file: one per
desk, pad, hand camera, bridge, phone or recording, each with a `role`
(its name) and a `kind`. Each has one line on the SYSTEM page:
`connected`, `lost` (not there; it keeps looking), `off` or `error`.

**Dirty dot / unsaved dot** — the red disc that shows the loaded preset
has changes not yet saved.

**Dream (the)** — a neural-network effect that "dreams" patterns into
the trail behind the shape; it needs the *dream worker*.

**Dream worker** — the background process that computes the dream; the
LOOKBACK page's status names its device when it runs.

**Drive** — how strongly a sound band pushes what it moves.

**Echoes** — the fading copies of earlier frames that trail behind the
moving shape.

**Effect chain / stack** — the list of picture effects (kaleidoscope,
plasma, hue cycle…) applied in order; managed on the FX page.

**Eye** — the fixed camera the shape and the ghost hands are both seen
through; its field of view and distance are on the CAMERA page, and no
preset changes them.

**FACES page** — the page for the faces' pattern and colours.

**Factory** — *superseded 2026-10-28*: nothing ships with the app any
more. Every preset in the library is yours, listed alike, and the
twenty-five the build once shipped live on only as test data
(`tests/corpus/`).

**FL Studio** — music software (a DAW) that the app can exchange MIDI
with.

**Footer** — the message line at the bottom of the control window.

**Frame rate (FPS)** — pictures drawn per second; shown in the footer.

**FX page** — the page for the picture effects.

**Gate** — a condition on a route, such as "only while pinching".

**Ghost hands** — drawn copies of the performer's hands in the picture,
switched on on the HANDS page.

**Ghost mirror** — flips the ghost hands left to right, for viewing in
the glass (HANDS page, **Mirror** in the ghost's **more ▸**).

**Glass (the) / Pepper's Ghost** — the stage rig: a screen reflected in
angled glass so the picture seems to float in the air. Any see-through
or grey ground spoils the illusion, hence the many "solid black" checks.

**Glyph** — the short code naming each desk control: K1–K8 track knobs,
D1–D8 device knobs, S1–S8 track faders, X the crossfader, G row·column
the pad grid (G6 is the clip-stop row), B-numbers the single buttons
(B11 OVERDUB, B20 TAP TEMPO…).

**Golden picture (golden frame)** — a picture of a factory preset the
automated tests draw and compare to the last byte; 596 of them, kept in
`hyperspace-python/tests/golden/frames/`.

**GRAPH page** — the page (after ROUTING) that draws every control,
route, modifier and part of the picture as boxes joined by cables, and
lets you rewire them by dragging.

**Ground** — the empty background of the picture. The OUTPUT page's
Ground setting is how see-through it is in overlay mode.

**Group** — several GRAPH boxes folded into one, its plugs the cables
that cross its edge; `+` opens it in place (plan 40).

**Guide and tethers** — the guide is a gauge drawn beside or on a ghost
hand showing each axis as a ball or arc; tethers are lines from the
routed axes to labels naming what they drive.

**Hand camera / Leap** — the Ultraleap Leap Motion Controller 2, a small
USB camera that tracks hands above it.

**Hand presets** — `hands-play`, `hands-pinch`, `hands-fx`,
`hands-orbit` and `lfo-breathe`: factory presets for trying the hands
and the LFO, found in the preset list (on no F-key).

**HANDS page** — the page for hand tracking: the box view, the feel
settings, calibration and the ghost hands.

**Home** — loading the show's startup preset (fn+← or OVERDUB), the one
its file names; nothing on the panel sets it since 2026-10-28.

**Home folder** — `~/Hyperspace`, where the app keeps your config,
presets, shows, mapping file and logs; another folder can be used with
`HYPERSPACE_HOME`. Written `<home>` in this guide.

**Hot reload** — the app picking up a saved code or effect file while it
runs.

**House mood** — one of the eight presets of the old `house` show
(BIG BLUE WAVE…); test corpus only since 2026-10-28.

**IAC bus** — the Mac's built-in virtual MIDI cable (Audio MIDI Setup →
IAC Driver), used to connect the app to FL Studio with no hardware.

**Instances** — how many copies of the shape are drawn (0 is none).

**Interaction box** — the region above the hand camera set by
calibration; a hand outside it counts as absent.

**Invariant** — a desk control whose job is fixed by the setup and is
the same on every preset and both layers (the master fader, the
crossfader, OVERDUB, SAVE, the bank pads, the points / lines / faces /
rotate buttons, TAP TEMPO); it cannot be learned.

**Lane** — a moving value that can drive a setting: a sound band
(written `lane:0` for the first), an LFO (`lfo:0`), a hand axis (`hand R
y`, "R height"), or an outside source such as FL Studio (`ext:0`).

**Layer (preset / global)** — the desk has two layers: normally its
knobs do the loaded preset's jobs; with SHIFT latched (the global layer)
they do the setup's jobs (band settings, hand feel, BPM).

**Learn / Unbind** — Learn assigns a desk control (**Learn desk**) or a
hand axis (**Learn hand ▸ left / right**) to a setting by moving it;
Unbind removes what drives a setting. Both are on a setting's
right-click menu.

**Learn depth** — how strongly the next tilt learned with Learn hand
moves its setting; on the HANDS page.

**LFO** — "low-frequency oscillator": a slow repeating wave, synced to
the tempo, that can move a setting (for example make brightness
"breathe"). The LFO page shows four.

**Look-back** — the LOOKBACK page's own switch, which turns the echoes
and the dream on.

**LOOKBACK page** — the page for the echoes and the dream (sections
ECHOES, DREAM, BOTH).

**Macro** — one knob that moves several settings at once, each over its
own range.

**Master dimmer (master dim)** — the overall brightness of everything
shown, set by the crossfader; the first row of the OUTPUT page.

**MIDI** — the standard way music hardware and software send control
messages.

**Modulatable** — able to be moved by a lane; "not modulatable" settings
can be set but not performed.

**Modifier** — a small box between a source (a hand, a band, an LFO) and
a route: curve, scale, smooth, combine two sources, threshold (turns a
level into a trigger), delay (one frame). Built on the GRAPH page
(ROUTING's MODIFIERS strip before the legible graph); saved in the preset.

**OSC** — Open Sound Control: messages a phone app or a music program
sends over the network (Wi-Fi); a phone app can be a device.

**Output** — a screen the picture is drawn on (the glass, the
projector); each can show different layers and has its own dim.

**OUTPUT page** — the page for screens, fullscreen, the master dimmer and
each output's switches.

**Overlay** — a mode where the render window floats see-through over the
desktop; only possible when the config has `[output] overlay = true`.

**Pad** — one of the 40 square buttons in the APC40's grid. Pad row 1
loads presets 1–8; rows 2–3 with SHIFT pick band scenes; rows 4–5 load
presets 9–24.

**Party show** — the show the app used to open with (F1 TUMBLE, F2
FACES, F3 FIELD, F4 WAKE, F5 TRIP, F6 ACID, F7 MANDALA, F8 NOITA, slot 9
TRACER); test corpus only since 2026-10-28, with the **house show**. A
fresh library opens an unsaved show called `untitled`; the owner's own
shows are in the Drive library.

**Patch** — a group of GRAPH boxes saved with the cables that cross its
edge, in `patches/` in the library, to drop into any preset (plan 40).

**Pattern** — the texture drawn on the faces (FLAT is plain); chosen on
the FACES page.

**Pickup** — a fader whose value moved elsewhere does nothing until you
move it past the current value, so the picture never jumps.

**Pinch switch** — a switch that closes when thumb and a finger touch.

**Point cloud** — a cloud of 3D dots from a recording (later, a depth
sensor), listed in the device list and drawn inside the shape's world.

**Preset** — a saved look: every performance setting, its routes and
what the desk's knobs do.

**PRESETS page** — the preset strip over a list of every preset (click
loads; rename, ×), the trash at its foot, the patches fold and one line
for the show (open ▾ · save · as… · new).

**Projector** — here, any second screen.

**Refresh rate** — how many times a second a screen redraws (60 or 120
Hz); System Settings → Displays.

**Render graph** — how the picture is built: parts (the shape, the
hands, a point cloud, the effects, the trail, each output) wired
together; a preset may say its own wiring in its file. The SYSTEM page
times each part.

**Render window** — the window that shows the picture.

**Rest / hold** — what a hand axis does when the hand leaves: go back to
rest, or hold its last value (hold only affects what is sent to outside
music software; the picture always returns).

**Ring** — the circle of lights around an APC40 knob, showing its value.

**Rotation planes (XY, XZ, YZ, XW…)** — the four-dimensional shape spins
in six planes, each with its own rate on the VIEW page.

**Route / routing** — a connection from a lane to a setting: **push**
moves the setting up and down around its own value; **positions** sets
it directly from the lane. The ROUTING page lists them all.

**ROUTING page** — the page listing every route, what the desk's
controls do on the loaded preset (DESK section), the macros (MACROS) and
the setup's own controls (SESSION).

**Scene buttons** — the column of buttons right of the APC40's pad grid;
here they switch points, lines, faces and rotation.

**Screen strokes** — a VIEW page switch: off (the default), the shape's
lines and dots grow and shrink with the zoom; on, they keep one size.

**Session** — the setup's own controls and settings, kept in the
bindings file and config rather than in a preset.

**Shape** — the four-dimensional object being drawn; there are 25.

**SHIFT layer** — the desk's second layer, latched by pressing SHIFT once
(its light stays on); see *Layer*.

**Show (project file)** — a file in `<library>/projects/` holding the
session, the desk's pads (a bank of preset names), the rig's wires and a
startup preset.

**Stall log** — `<home>/stall.log`, where the app writes what it was
doing when it froze or hit a drawing error.

**Starts on (startup)** — the preset a show's file names for Home and a
launch; no longer picked on the panel (2026-10-28).

**Stderr** — what the app prints in the terminal it was launched from.

**Steadiness, Response, Return** — hand feel settings on the HANDS page:
steadiness smooths jitter, response sets how quickly a value follows the
hand, return how quickly it goes back when the hand leaves (see also
*Catch*).

**Synthetic tape** — a recording of made-up hand movements, played in
place of the hand camera (`tools/hands_tape.py synth`).

**Sink** — a device that sends values out of the app (to FL Studio): the
bridge, the hands' own port. A setting goes out on one by **Learn
sink**.

**SYSTEM page** — the page for notes, errors, one line per device, the
library status, and app-wide settings.

**Tape (hand recording)** — a file of recorded hand movements that can
be played back instead of the hand camera; a *synthetic tape* is made
up, a real one is recorded at the rig (D8).

**Tearing** — a horizontal break across the picture where its top and
bottom come from different frames.

**Through effects** — an output switch: on, the ghost hands are bent by
the effects with the shape; off, they are drawn clean on top.

**Track faders** — the eight vertical faders along the APC40's bottom
(S1–S8); they belong to the loaded preset (dark when it binds none),
and with SHIFT latched they set the sound bands' drive, dynamics and
trim.

**Track knobs** — the eight upper-right knobs on the APC40 (K1–K8).

**Track-select buttons** — the row of eight buttons just under the
APC40's clip-stop row; here they choose which sound band the device
knobs edit (with SHIFT latched).

**Trash** — `<home>/trash/`, where replaced or deleted presets and shows
are kept; viewable from the preset list.

**Undo step** — one action that ⌘Z takes back as a whole.

**Unmapped** — a desk control with no job on the loaded preset; its
light is off and it does nothing.

**VIEW page** — the page for the shape's look: brightness, speed,
points, lines, faces, instances, rotation rates.

**Weights** — the dream's neural-network data files.
