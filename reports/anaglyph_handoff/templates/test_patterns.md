# Anaglyph test patterns: specification

Pattern IDs (TP1 to TP9) are what `experiment_log.csv` (`test_scene`) and `experiment_example.yaml` (`test_patterns`) refer to.

**Provenance.** Each value is tagged with where it comes from:

- **[notes]**: taken from the research notes in `research_notes/Custom anaglyph 3D projection plan/`. Most come from `calibration_equipment.md` Q3/Q4 and `rendering_algorithms.md` Q7.
- **[spec]**: a layout choice made in this document so the patterns can be reproduced exactly. These are not measurements; change them if needed and record the change in the log.
- **[derived]**: computed from a [notes] value with the formula shown.

## 0. Common conventions

| Item | Value | Source |
|---|---|---|
| Reference raster | W × H = 1920 × 1080 px. For another raster, scale every pixel size by W/1920, but keep disparities in px and re-derive them from the parallax budget | [spec]; the 1920 px width matches the worked example in rendering_algorithms.md Q7 |
| Coordinates | Origin top-left, x to the right, y down. Rectangles are written `[x0, y0, x1, y1)` (end-exclusive) | [spec] |
| Code values | 8-bit **encoded** values in each eye's *source* image, i.e. before the compositor | [spec] |
| Linear ↔ code conversion | The sRGB OETF/EOTF from Dubois 2009 is used until the projector's EOTF has been measured. Once it has, recompute every "linear %" patch with the measured curve | [notes] rendering_algorithms.md Q2 |
| Two delivery modes | **E (eye-source):** L and R images go through the compositor with the profile under test, which tests the whole pipeline. **D (direct-output):** the RGB frame is sent straight to the projector with the compositor bypassed, which tests only the projector and filters | [spec] |
| "White" for one eye | That eye's own primary set. Red/cyan: L = (255,0,0), R = (0,255,255). Green/magenta: L = (0,255,0), R = (255,0,255). Amber/blue: L = (255,255,0), R = (0,0,255) | [notes] calibration_equipment.md Q3, Path A step 2. Eye roles follow the profiles; Blender's channel encoding gives the same RC/GM/YB split |
| Disparity sign | d = x_R − x_L in px. **d > 0 is uncrossed** (appears behind the screen). **d < 0 is crossed** (appears in front) | [notes] rendering_algorithms.md Q7 (p > 0 behind, p < 0 in front) |
| Applying d | Shift left-eye content by −⌊d/2⌋ px and right-eye content by +⌈d/2⌉ px. Leave y unchanged, because vertical parallax is not allowed | [spec] |
| Background | Black (0,0,0) in both eyes unless stated otherwise | [spec] |
| Projector state | Lock the settings first: BrilliantColor/white boost, dynamic contrast, eco and auto keystone all OFF; fixed colour mode | [notes] calibration_equipment.md Q5 |
| Repeats | Take at least 5 readings per frame and report mean ± SD | [notes] calibration_equipment.md Q3 |

Crosstalk for each eye, measured through that eye's filter, is the black-level-corrected observed crosstalk [notes]:

```
crosstalk_eye = (ghost − black) / (white − black)
  white = reading with this eye's view at "white" and the other view black
  ghost = reading with this eye's view black and the other view at "white"
  black = reading with both views black
```

---

## TP1. Leakage, full field (L-only / R-only)

Purpose: measure per-eye crosstalk (Path A or Path B) and the 3×2 per-primary leakage matrix.

| Frame | Left view | Right view | Mode | Read through |
|---|---|---|---|---|
| TP1-LW | eye "white" (see §0) | black | E and D | left filter (= white_L), right filter (= ghost_R) |
| TP1-RW | black | eye "white" | E and D | right filter (= white_R), left filter (= ghost_L) |
| TP1-K | black | black | E and D | both filters (= black_L, black_R) |
| TP1-PR / PG / PB | — | — | D only: full-field (255,0,0), (0,255,0), (0,0,255) | both filters, giving the per-primary leakage table |
| TP1-W / TP1-K0 | — | — | D only: full-field (255,255,255) and (0,0,0) | both filters, plus no filter (for the additivity check: W compared with R+G+B) |
| TP1-RAMP (optional) | the leaking view driven at 32 levels, code = round(i·255/31), i = 0..31; the other view black | | E | regression slope instead of single-point ratios ([notes] Baker et al. 2016 used 32 levels) |

- Geometry: full frame `[0,0,1920,1080)`. [spec]
- Phone RAW (Path A): fix manual exposure, ISO, white balance and focus. Use a tripod and measure the same pixel region, the central `[760,340,1160,740)` px of the frame. Bracket exposures with known time ratios, because ghost and signal levels can be 50–100× apart. [notes for method; spec for region]

## TP2. Ghost edges (high-contrast bars) and SCT-style chart

**TP2a, ghost-edge bars (mode E).** Vertical white bars on black, all at **d = +20 px**. That is the largest rung in the [notes] disparity set, so it makes ghosts most visible.

- 5 bars of width 2, 4, 8, 16 and 32 px. [spec]
- Bar centres at x = 320, 640, 960, 1280, 1600. [spec]
- Each bar spans y ∈ [140, 940). [spec]
- Bar value is that eye's "white" (§0).

Look through each filter in turn and note the faint copy offset by d.

**TP2b, SCT-style chart (mode E).** After Weissman & Woods 2011, with patches scaled in percent of *linear* intensity [notes]:

- Eye A (the leaking view) is a horizontal bar at eye-A "white", spanning `[0, 450, 1920, 630)`. [spec]
- Eye B (the view being judged) has 8 gray patches in a row, each 240 × 180 px, spanning `[k·240, 630, (k+1)·240, 810)`, k = 0..7. [spec] Each patch is drawn in eye B's own primary set, at the level below. A label under each patch gives its %.
- Patch levels, in % linear [notes]: 0.5, 1, 2, 3, 5, 8, 12, 20.
- Matching sRGB code values [derived, sRGB OETF ×255, rounded]: **16, 25, 39, 48, 63, 80, 97, 124**. Recompute these with the measured projector EOTF once it is known.
- Run the chart twice: A = left / B = right, then A = right / B = left.
- Task: the viewer looks through eye B's filter only and names the patch that matches the ghost of the bar.

Background: the older Weissman and Bloos charts were scaled in gray level, not intensity, so they read wrong unless gamma is accounted for [notes].

## TP3. Black / white / black (and adjacent red | cyan)

**TP3a (mode E).** Three equal vertical bands in one eye only:

- `[0,0,640,1080)` black, `[640,0,1280,1080)` eye "white", `[1280,0,1920,1080)` black. [spec]
- The other eye is all black.
- Run it once per eye.
- Then run the inverse, white | black | white, to check for ghosting of dark-on-bright edges.

**TP3b (mode D), adjacent rectangles** [notes, Woods & Rourke 2004]:

- `[0,0,960,1080)` = (255,0,0) next to `[960,0,1920,1080)` = (0,255,255).
- Hold one filter over the boundary. The more completely the complementary half goes black, the lower the crosstalk.
- For other pairs, use the matching pair of eye colours: green (0,255,0) | magenta (255,0,255), and amber (255,255,0) | blue (0,0,255). [spec extension]

## TP4. Colour patches (mode E, zero disparity, identical in both eyes)

A 4 × 4 grid of 400 × 220 px patches. The grid origin is (160, 100) and patches are separated by 20 px gaps of mid-gray (128,128,128). The whole background is (128,128,128). [spec]

| Row | Patch 1 | Patch 2 | Patch 3 | Patch 4 |
|---|---|---|---|---|
| 1 | (255,0,0) | (0,255,0) | (0,0,255) | (255,255,255) |
| 2 | (0,255,255) | (255,0,255) | (255,255,0) | (0,0,0) |
| 3 | 25 % linear = (137,137,137) | 50 % linear = (188,188,188) | 75 % linear = (225,225,225) | Hyperspace point red (255,43,43) |
| 4 | (128,0,0) | (0,128,0) | (0,0,128) | (128,128,128) |

- The row 3 code values are [derived] with the sRGB OETF.
- (255,43,43) is `RED = (1.0, 43/255, 43/255)` from `hyperspace/view.py` [notes]. It is included because saturated red can disappear from the cyan eye.
- Record, per patch: perceived hue and brightness through the glasses, and any rivalry (flicker or alternation between the two eyes' colours).

## TP5. Disparity ladder (mode E)

- 7 white squares, each 120 × 120 px, at the [notes] disparities **d = −20, −10, −5, 0, +5, +10, +20 px**. [notes: calibration_equipment.md Q4]
- Squares are centred on y = 540 at x = 240, 480, 720, 960, 1200, 1440, 1680, ordered from most crossed to most uncrossed. [spec]
- Square value: eye "white".
- Optional rung at the installation's parallax budget. The notes' worked example (V = 4 m, 4 m wide screen, 1920 px) gives about +30 px at the divergence limit. Only include it once the real screen width and seat distances are known, and compute it from `stereo.max_positive_parallax` in the profile. [notes; this is an example only, not the installation]
- Record, per rung: whether the square fuses, its depth order relative to its neighbours, and any visible ghost.

## TP6. Depth reversal check (mode E)

- Centre square `[860,440,1060,640)` at **d = −10 px**. This is crossed, so it must appear **in front of** the frame. [spec]
- Surrounding hollow frame: outer edge `[560,140,1360,940)`, 40 px thick, at **d = +10 px**. This is uncrossed, so it must appear **behind**. [spec]
- Eye identification markers at d = 0:
  - The letter "L" (200 px tall) at `[100,100,300,300)`, drawn **only in the left view**.
  - The letter "R" at `[1620,100,1820,300)`, drawn **only in the right view**. [spec]
- Pass condition: the square appears in front of the frame, and a viewer closing their right eye sees "L" clearly ("R" at most as a faint ghost).
- If the square appears behind the frame, depth is reversed. Check the glasses orientation, the M_left/M_right assignment and the sign of the per-eye offset ex. See decision tree F.

## TP7. Text at disparities (mode E)

- The string `HYPERSPACE 0123456789`, white on black, in a sans-serif font. [spec]
- 8 rows, centred at x = 960, with row baselines at y = 130, 250, …, 970 (120 px pitch). [spec]
- Rows alternate cap height 24 px and 48 px. [spec]
- Row disparities: d = 0, 0, −5, −5, +10, +10, +20, +20 px (each value used for one 24 px row and one 48 px row). These use the [notes] disparity set. [spec ordering]
- Record: legibility, any doubled-glyph ghosting, and the disparity at which reading becomes uncomfortable.

## TP8. Random-dot stereogram (mode E)

After Julesz [notes]. It contains no monocular depth cues, so it checks stereopsis and screens viewers. About 5 % of individuals cannot see depth in RDS [notes].

- Dot size: 4 × 4 px cells across the full frame, giving 480 × 270 cells. Each cell is black or eye "white" with p = 0.5, using a fixed PRNG seed (seed = 1, numpy `default_rng`). [spec] Dots must be large enough to resolve; dot size affects stereoacuity results [notes].
- Target: a central square of 240 × 240 px, `[840,420,1080,660)`. In the right view it is shifted by d = −12 px (3 cells, crossed, should appear in front). Fill the strip uncovered by the shift with fresh random cells. [spec]
- Variant TP8b: the same with d = +12 px (should appear behind). [spec]
- Record, per viewer: whether the square is seen, and whether it is in front or behind. A viewer who sees no square should be checked with Randot (graded circles 400 → 20 arcsec [notes]) and logged separately.

## TP9. Registration / alignment (optional, mode E)

- Nonius lines [notes: calibration_equipment.md Q4], 2 px wide:
  - Left view: vertical lines at x = 960 for y ∈ [300, 540), and at x = 480 and 1440 for the same y-range.
  - Right view: the same x positions for y ∈ [540, 780).
  - Any horizontal offset at y = 540 means misregistration (with disparity 0 intended). [spec geometry]
- Checkerboard: 60 × 60 px squares, identical in both views, for checking keystone and warp. Prefer physical alignment over digital keystone. [notes for the purpose; spec for the size]
