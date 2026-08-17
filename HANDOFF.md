# Hyperspace — handoff

Single-file 4D polytope viewer with audio-reactive rotation. Built over one
session. This document is written for another agent picking the work up cold.

**Artifact:** `hyperspace.html` — one self-contained file, ~52 KB, no build step,
no dependencies, no network calls. Open it in a browser and it runs.

---

## 1. What the user asked for, in order

1. A rotating hypercube artifact — black background, white edges, red vertices,
   a toggle for the points, and a slider to move between "hyper platonic
   solids." Explicitly asked for a plan before execution.
2. A brightness control (the depth-fade was blowing out on dense shapes and
   burying far edges on sparse ones), a collapsible control drawer, and sliders
   that actually drag on touch instead of only responding to taps.
3. An FFT module on microphone audio. Six frequency bands, each mapped to one
   rotation plane, with per-band rolling-window RMS. Low end and high end should
   pull the shape in different directions. Bands go to zero → their plane stops.
4. Bug reports: audio section invisible, mic never prompting.
5. Pasted a browser console log revealing the real sandbox constraints.
6. Decouple the input meter from the fader it drives — an FL Studio Fruity Peak
   Controller, with a dropdown of transfer functions per band.
7. Tooltips, per-band pre/post drive, per-band window size, per-band threshold /
   attack / decay, and a scene preset dropdown across all bands.
8. Commit to a new private git repo (blocked — see §8).

**User's register:** technical, hands-on maker, comfortable with DSP and audio
production vocabulary. Speaks in FL Studio / Ableton terms and expects those
concepts to map directly. Prefers being told plainly when something can't be
done over being given a workaround dressed up as a solution.

---

## 2. Geometry

Vertices come from exact standard constructions; edges are recovered by
connecting every pair at the minimum vertex distance (`edgesByMinDist`). This is
valid for regular and uniform polytopes where all edges are the same length.
Duoprisms and prisms build their edge lists explicitly instead.

Helpers: `expand(base, mode)` applies all-or-even index permutations × all sign
changes with dedup; `cyc3` does the 3D cyclic equivalent for the seed solids;
`prism(V3)` extrudes a 3D solid along w; `duoprism(n, m)` spins two polygons in
orthogonal planes.

All 18 shapes, ordered by cell count (the slider index — cells are the 4D
analogue of faces, which is how the "number of faces" request was honoured):

| # | Shape | Cells | V | E |
|---|---|---|---|---|
| 1 | 5-cell (hypertetrahedron) | 5 | 5 | 10 |
| 2 | 3,3-duoprism | 6 | 9 | 18 |
| 3 | Cubic pyramid | 7 | 9 | 20 |
| 4 | Tesseract (hypercube) | 8 | 16 | 32 |
| 5 | Rectified 5-cell | 10 | 10 | 30 |
| 6 | 4,8-duoprism | 12 | 32 | 64 |
| 7 | 6,6-duoprism | 12 | 36 | 72 |
| 8 | 16-cell (hyperoctahedron) | 16 | 8 | 24 |
| 9 | 10,10-duoprism | 20 | 100 | 200 |
| 10 | Icosahedral prism | 22 | 24 | 72 |
| 11 | 24-cell | 24 | 24 | 96 |
| 12 | Truncated tesseract | 24 | 64 | 128 |
| 13 | 12,12-duoprism | 24 | 144 | 288 |
| 14 | Dodecahedral prism | 32 | 40 | 80 |
| 15 | 20,20-duoprism | 40 | 400 | 800 |
| 16 | 120-cell (hyperdodecahedron) | 120 | 600 | 1200 |
| 17 | 600-cell (hypericosahedron) | 600 | 120 | 720 |
| 18 | Clifford torus (32×16) | — | 512 | 1024 |

Geometry is built lazily on first selection and cached in `cache[]`, normalised
to unit circumradius, stored as flat `Float64Array` / `Int32Array`.

Two naming notes settled with the user: "hyper hexahedron" and "hypercube" are
the same object (the tesseract); "hyper dodecagon" was read as the 120-cell, and
a 12,12-duoprism was added so the literal dodecagon reading is covered too.

## 3. Rendering

Rotate in 4D across six planes → perspective project 4D→3D (`D4 / (D4 - w)`) →
apply drag orientation (yaw/pitch) → perspective project 3D→2D → draw.

- Canvas 2D, `alpha:false`, DPR-capped at 2.
- Edges are painter-sorted on w-depth, alpha `(0.10 + 0.90·t²)·B` where `t` is
  normalised w-depth. The near half glows, the far half recedes.
- `B = brightness · density compensation`, where `dens = clamp(340/edges, .42, 1)`.
  Without that term the 120-cell's 1200 edges clip to a solid white blob at the
  same slider position that leaves the 5-cell invisible.
- Points are red, radius and alpha both depth-cued.

## 3b. Audio sources

Three, all feeding the same `attach(ctx, node, label)` hub:

- **Mic** (`m`, `startMic`) — `getUserMedia`, with `echoCancellation`,
  `noiseSuppression` and `autoGainControl` all off. Those are voice-call DSP;
  they gate and duck exactly the dynamics the band analysis exists to find.
  **Do not turn them on.**
- **System audio** (`s`, `startSys`) — `getDisplayMedia`. Chrome refuses
  audio-only capture, so it asks for video and immediately stops and removes
  the video track. On macOS only *tab* shares carry audio; screen and window
  shares come back silent, hence the "no audio track" branch. The track's
  `ended` event fires when the user hits Chrome's own "Stop sharing" bar, and
  tears the graph down.
- **File** (`startFile`) — see the CSP note in §5.

**The BlackHole route is the one that actually covers everything**, and it is
the same trick `samples` (~/Dev/samples) uses: a virtual loopback driver
installs as an ordinary *input* device, so with the Mac's output routed through
a Multi-Output Device, all system audio arrives through the plain mic path — any
app, any browser, no `getDisplayMedia` needed. That is what `#inputRow` /
`refreshInputs()` exist for; `LOOPBACK`/`isLoopback()` recognise such a device
by name, preselect it and label the readout `System · …`. Device *labels* are
blank until some capture has been granted, so `refreshInputs()` runs at startup
(useful on a site already granted), again after every successful open, and on
`devicechange`. README has the user-facing setup.

## 4. Audio chain

Per band, in order:

```
FFT bins → power-sum RMS → dB → u (0..2.5; 1.0 is nominal, 56 dB window)
  ├─ LEVEL:     rolling window (asymmetric one-pole, per-band attack/decay)
  │               → peak/valley window + confidence + gate
  │               → upward expansion about the band's running mean
  └─ TRANSIENT: fast env − slow env → relative flux, peak-normalised
  → blend(level, transient) per band          ← the `trn` knob
  → harmonic coupling             ← this is the INPUT meter (white)
  → pre-drive → transfer function → post-drive
                                  ← this is the OUTPUT meter (red)
  → PLANEDRIVE[plane] = dir · out · 3.2 · masterGain
```

**Headroom.** Nothing clamps anywhere. Four landmarks: `NOM = 1.0` (a band
working normally), `KNEE = 1.25` (where the soft ceiling starts to bend),
`HEAD = CEIL = 2.6` (asymptotes the signal approaches and never reaches).
`softCeil(x, knee, ceil)` is the identity below the knee and
`knee + r·t/√(1+t²)` above it — slope 1 at the knee with no curvature step,
and a t⁻³ tail, so even a cubed signal driven ten times past nominal comes
out strictly increasing. That property is the point: the old
`clamp(x, 0, HEAD)` flat-topped four bands at once, and a flat top is not
"loud", it is zero dynamics.

The clipping the user reported was manufactured inside the chain, not
delivered by the input — envelopes sat at 0.6–1.0 while the post-expander
signal came out at 1.7–2.0. Two causes, both fixed: the expander had no
gain-staging discipline on its makeup (see `DEV_AIM`), and harmonic coupling
multiplied a value that had *already* been clamped and then clamped it again.
Coupling is unchanged in depth but now sits immediately before the one and
only saturation in the chain. Measured on a brickwalled WAV in the browser,
steady state: time within 2% of the ceiling 0.3% → **0.0%**, input sd
0.273 → **0.382**, fader-out sd 0.176 → **0.230**.

`WARM_F` fades the expander in over the first second. It needs a settled mean
to expand about and for that first second it has a seed instead; expanding
against a stale mean is what threw every bar at the ceiling for the opening
half second of every track (4.5% of warm-up frames flat against the clamp,
peaking at 11% on MIDB — now 0.0%).

Meters read 0..`CEIL` with the nominal line at 38.5% and the knee line at
48.1%, two stacked tints so working / headroom / knee read as three shades.
The bar top is an asymptote, so a column that sits against it for 0.5 s
(`PIN_HOLD`) is genuinely over-driven and lights a blinking annunciator —
"full" and "wrong" are now different-looking things.

**Dynamics recovery** — the point of all this is that a brickwalled master
carries almost no level variation, so the old fixed-floor peak normaliser
mapped it to a flat 1.0 and the rotation became a constant rate. Three parts
undo that: a **valley tracker** (window has a moving floor as well as a moving
ceiling), **upward expansion** about the band's running mean scaled by how
squashed the band already is, and a **transient path** (fast minus slow
envelope) — a limiter flattens level but cannot flatten change. Global
`Dynamics` slider (`AUDIO.dyn`) scales the lot; per-band `Contrast` (`exp`) and
`Transient` (`trn`) knobs sit at the top of the strip.

Measured on a synthetic brickwalled WAV, `AUDIO.out` for BASS moved from
sd 0.018 (dyn 0) to sd 0.181 (dyn 1); MIDB from 0.080 to 0.697 with a full
0→2.0 swing. Against the *old* chain on a limited signal: sd 0.000, pinned at
1.000. A band with genuinely no dynamics (a static pad) correctly stays flat —
this recovers what a limiter took, it does not invent motion.

**Input trim** (`PARAMS[i].trim`, `AUDIO.trim`, both dB) is the mixer-style
input stage: off, then −60 dB to +12 dB at 1 dB/step with a detent at 0, tagged
LIN because dB is already a logarithm. It is applied twice — added to `db`
before `u` is formed (so it moves the band against the references that do *not*
adapt: the gate `thr`, `CONF_LO`, `PK_MIN`) and again as `tDb / U_SPAN` offset
onto the fader signal after the trackers. The second application exists because
the window normaliser is a two-point auto-calibration and by construction
removes any static gain placed in front of it: pre-envelope trim alone is a
**placebo**, measured converging to the identical output within 30 s whether
cut by 0 dB or 40 dB.

> ⚠️ **Known limitation, measured on the merged build — do not trust the
> per-agent numbers here.** Both the trim and the soft-ceiling work were
> verified in isolation, but the trim's calibration depends on harmonic
> coupling, which the ceiling work moved. On real material from a *fully
> settled* state, BASS trim is non-monotonic through the range you would
> actually reach for: 0 dB → `inp` 0.606 / `out` 0.867; −6 dB → 0.701 / **1.03**;
> −12 dB → 0.649 / **1.01**; −20 dB → 0.463 / 0.748. Cutting 6–12 dB makes the
> band drive *harder*, and it only starts attenuating around −20 dB. A hard off
> (−60 dB) does correctly produce exactly 0 on `inp`, `out` and `PLANEDRIVE`.
> The earlier clean monotonic table was produced against a *constant* band
> level, where the trackers cannot re-calibrate the way they do on music.
> The structural fix is one of: bias the adaptive window in proportion to trim,
> apply trim as a post-normaliser multiplier on the band's contribution, or add
> a per-band manual mode that bypasses adaptive normalisation entirely.

Analyser: `fftSize 4096`, `smoothingTimeConstant 0.15` (deliberately low — the
per-band envelopes do the smoothing, and the analyser's own smoothing would
fight the attack/decay knobs).

**Harmonic coupling** boosts a band by the geometric-mean coherence with the
band above it, so overtone-rich sources drive harder than pure tones. It's a
proxy, not real integer-multiple peak detection — this was stated plainly to
the user. It sits on the input side because it characterises the signal rather
than shaping it; the user was told it could move downstream if preferred.

**Band → plane map.** The three w-planes are the true 4D rotations that evert
the shape, so the low end drives those; upper harmonics drive the ordinary 3D
spins, with opposed signs so lows and highs pull in different directions.

| Band | Range | Default window | Plane | Dir |
|---|---|---|---|---|
| SUB | 20–60 Hz | 250 / 850 ms | ZW | + |
| BASS | 60–160 Hz | 15 / 130 ms | XW | + |
| MIDB | 160–400 Hz | 6 / 70 ms | YW | − |
| MID | 400–1200 Hz | 50 / 300 ms | XY | − |
| UPR | 1.2–4 kHz | 90 / 500 ms | XZ | + |
| AIR | 4–14 kHz | 180 / 900 ms | YZ | − |

**13 transfer functions** (`SHAPERS`), each with per-band scratch state so
envelopes and LFOs hold between frames: `LIN` `SQRT` `SQ` `CUBE` `CURV`
(smoothstep) `GATE` `INV` `HOLD` (peak hold, 0.7 s fall) `STAC` (4 ms / 75 ms)
`CHOP` (5 Hz square) `TREM` (6 Hz sine, 70% depth) `S&H` (180 ms) `SLEW`
(800 ms). Changing a band's function resets that band's scratch state.

**11 scenes** (`PRESETS`) snapshot the whole chain — function, both drives,
attack, decay, threshold for all six bands: Balanced, Kick & Sizzle, Glacial
Drift, Strobe Cage, Bass Engine, Air & Lace, Inverse World, Percussive, Tremolo
Web, Harmonic Bloom, Slow Bass / Fast Air.

**Per-band knobs** (`PARAMS[i]`, edited via the strip): contrast 1:1–1:5,
transient 0–100%, pre-drive off/0.06–8×, post-drive off/0.06–8×, attack
0.5 ms–2.05 s, decay 5 ms–20.5 s, threshold 0–0.6.

**Fader tapers.** Every fader is an integer position; a taper object owns
both directions of the mapping (`map` / `unmap`) and `unmap(map(p)) === p`
exactly over the whole throw, which is what keeps `selectBand` and
`applyPreset` from walking a fader sideways. `expZero(u, n)` is exponential
with a hard zero at position 0 and unity at `u`; `expPure` has no zero;
`expTime(v0, n)` is an exponential time constant in ms stored as seconds;
`linT(d, n)` is `p/d`. LOG is used for every gain and every time constant
(equal travel, equal ratio); LIN only where the quantity is already
perceptually even — a percent blend, an expansion ratio, and threshold,
whose units are already dB. Each caption carries a `LOG`/`LIN` tag and the
gain faders draw a unity detent notch. `KNOBS[].scale` is gone; specs carry
`t` (the taper) and `fmt` now takes the real value, not the position, so a
scene value that lands between two notches still reads truthfully.

`PRESETS` rows are now `[fn, pre, post, atkMs, decMs, thr, exp, trn]`, but
`applyPreset` still accepts six-element rows and falls back to `DEF_EXP` /
`DEF_TRN`, so older scene definitions keep loading.

**Reset** resolves to the *currently selected scene* (`curScene()` reads
`#scene`), not to the hard-coded `PARAMS` defaults — scenes are the unit of
intent, and on Balanced the two coincide anyway. `resetBand(i)` and `resetAll()`
write into `PARAMS` and repaint via `refreshChain()`; they deliberately know
nothing about the taper mapping, which is what let tapers and reset be built in
parallel without colliding. Reset-all is guarded by an 8 s **undo** (the button
relabels itself) rather than a confirm, and the undo snapshot is discarded on a
scene change because it belongs to the old scene.

## 4b. Transport

The file source is a `AudioBufferSourceNode`, which cannot be restarted, so
playback runs through a fixed `GainNode` hub (`hub → destination`, `hub →
analyser`). Pause stores `trPos()` and tears the node down; resume builds a
fresh source and `start(0, offset)`. Position is measured against
`ac.currentTime`, not counted per frame, so it survives rAF throttling, and the
modulo folds loop wraps back in. Restart is return-to-zero preserving transport
state. Keys: `K` play/pause, `0` restart. Pausing lets the bands decay on their
own time constants — the shape coasts to rest over ~4 s rather than freezing.

---

## 5. Sandbox constraints — hard-won, do not re-litigate

These were each discovered from a real failure. Re-introducing any of them
breaks the artifact in the Claude preview.

- **No `blob:` URLs for media.** The artifact iframe serves
  `default-src https://www.claudeusercontent.com` with no `media-src`, so an
  `<audio>` element fed `URL.createObjectURL(file)` is refused outright. The
  file path therefore reads to an `ArrayBuffer` via `FileReader` and uses
  `decodeAudioData` + `AudioBufferSourceNode`. Nothing is *loaded*, so CSP has
  nothing to block. **Do not reintroduce an `<audio>` element.**
- **Microphone is blocked in every preview frame, and no amount of clicking
  "allow" fixes it.** An iframe only receives the microphone if the *parent*
  wrote `allow="microphone"` on it; artifact, cloud and doc embeds do not, so
  Permissions Policy rejects `getUserMedia` with `NotAllowedError` before a
  prompt is ever reachable. (The artifact sandbox additionally emits an
  unrecognised `webrtc` CSP directive.) `file://` in Chrome is separately
  hopeless — opaque origin, no prompt.
  The page therefore checks `document.featurePolicy.allowsFeature(…)`
  (`policyAllows()`, for `"microphone"` and equally for `"display-capture"`) up
  front and on click, skips the pointless request, and offers the one thing that
  actually works: `escapeFrame()` reopens the same URL as a
  top-level tab, where the browser prompts normally. If the frame also blocks
  `window.open` (no `allow-popups`), it falls back to copying the address.
  Non-`http(s)` frames (`srcdoc`, `blob:`) have no reopenable address and get
  told to open `hyperspace.html` in a browser instead.
- **`vh` is wrong on iOS.** It measures the *large* viewport, so a panel capped
  at `88vh` grew taller than the visible area and pushed the collapse handle off
  the top edge. Use `dvh` with a `vh` fallback.
- **Programmatic `input.click()` on a file input is blocked** in sandboxed
  frames. The file input is instead layered invisibly over its button
  (`.fbtn input{position:absolute;inset:0;opacity:0}`) so the tap lands on the
  real input with genuine user activation.
- **Native range drag is unreliable on touch.** Sliders are custom: a 30 px
  pointer-capture hit strip drives the value, with the `<input type=range>` kept
  underneath for keyboard and focus only (its thumb is zero-sized). See
  `bindSlider`.
- **Sliders claim horizontal gestures only.** `#body` scrolls, so a fader that
  swallowed vertical gestures made the panel unscrollable wherever a fader sat
  under the cursor. The wheel handler ignores (and does not `preventDefault`)
  anything that is not horizontally dominant by **2.5:1** — trackpads emit
  off-axis noise, and at 2.0 an ordinary scroll still grabbed the fader. The
  pointer path is an axis lock: `pointerdown` claims nothing, the first move
  past 6 px decides, and a gesture that goes vertical is abandoned for good.
  Two consequences that look like bugs but are load-bearing: `input.focus()`
  happens where the gesture *resolves*, not on pointerdown (without the
  pointerdown `preventDefault`, native mousedown handling clears focus right
  after you set it), and `.slider input[type=range]` is `pointer-events:none`
  (otherwise the native range widget handles its own drags and bypasses the
  axis lock entirely). `touch-action` is `pan-y`, not `none`.
- **Anything in `#body`'s flow that changes height on hover causes jitter.** The
  hint readout used to sit in flow and shoved every control below it down. It is
  now `position:absolute; bottom:100%` inside `#console` — out of every flow,
  growing upward into empty canvas. Keep new transient UI out of the flow.
- **No `localStorage`/`sessionStorage`** in artifacts. All state is in memory.

## 6. Testing

The container has a real Chromium at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, drivable via the puppeteer
bundled inside mermaid-cli:

```js
const p = await import('/home/claude/.npm-global/lib/node_modules/@mermaid-js/mermaid-cli/node_modules/puppeteer/lib/esm/puppeteer/puppeteer.js');
const b = await p.default.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  headless: 'new',
  args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required']
});
```

Use it. Two rounds of bugs in this session were diagnosed by guessing and only
resolved once the page was actually run. Useful techniques already proven:

- Multi-viewport hit-testing with `document.elementFromPoint` to confirm a
  control is reachable, at 390×844, 390×560, 360×480 and 1200×800.
- Feed audio without a mic by `uploadFile`-ing a WAV into `#fileIn`. Generate a
  test tone with python `wave` — a 50 Hz + 3 kHz mix isolates SUB/BASS and UPR
  and leaves MIDB/MID/AIR at exactly zero, which proves the gate works.
- Reproduce the artifact sandbox with a `srcdoc` iframe under a restrictive CSP
  meta tag to catch CSP regressions before the user does.
- Syntax-check without a browser:
  `new Function(html.match(/<script>([\s\S]*)<\/script>/)[1])`.

## 7. Visual conventions

Instrument-panel aesthetic, deliberately not a generic dashboard. Monospace
throughout, `tabular-nums`, uppercase micro-labels with wide letter-spacing,
hairline 1 px rules, square corners everywhere (no border-radius), red `#ff2b2b`
as the only accent and it matches the vertex colour. The large cell-count
readout in the top-left is the signature element. Keep new UI consistent with
this — it is a considered look, not a default.

## 8. Git state

Now on the user's own machine at `~/Dev/hyperspace`, `main`, with `origin` set
to `github.com/Cutaiar/hyperspace.git` and the real commit author. The container
blockers described in earlier versions of this document are resolved.

The work above was built by four parallel agents in git worktrees under
`.claude/worktrees/` and merged; `.gitignore` covers `worktrees`.
`.claude/launch.json` (untracked) runs `python3 -m http.server 8123` — serving
over localhost is what makes the **microphone** testable, unlike `file://`.

## 9. Open threads

- Real harmonic detection (integer-multiple peak picking) to replace the
  octave-coherence proxy.
- Per-band LFO rate/depth as knobs rather than fixed inside the CHOP/TREM
  presets.
- Tempo sync — the user's background is flow props and beat-synced lighting, so
  a BPM-locked chop is a natural fit.
- User-saveable scenes (blocked on no storage in artifacts; would need export to
  a JSON string the user copies out).
- Mic path is still unexercised end-to-end. It is now *testable* — serve over
  localhost with the launch config in §8 and the prompt will appear — but no
  session has actually granted permission yet. Transport in mic mode is likewise
  only verified via the `stopAudio()` path.
- The dynamics chain has only been driven by synthetic brickwalled audio. It
  wants a real commercial MP3 next; the constants most likely to need tuning are
  `OPEN_SPAN` (what counts as a healthy natural range) and `CONF_LO/CONF_SPAN`
  (which stop the expander turning an empty band's hiss into full-scale motion).
- A scrub bar for the transport — the position math (`trPos`) already exists.

## 10. User context

Hands-on maker: electronics, optics, LED and flow props (flowtoys vision clubs),
Arduino strobes, interactive visual art. Has iterated on this viewer across
multiple sessions. Reads console output and pastes it when something breaks —
take those logs seriously, the CSP fix came directly from one. Wants to be told
when something is impossible rather than handed a workaround presented as a fix.
