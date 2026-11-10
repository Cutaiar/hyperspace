# Status — read this first

A tesseract (and seven other 4D solids) drawn **in the data** of a QR code, a
live solver that re-derives one per frame, and a sticker-sheet builder that
exports print-ready files. Branch `qr-dither/bench`.

## Run it

```sh
cd app && npm install && npm run dev     # http://localhost:5181
```

Vite 8 binds IPv6 only — `127.0.0.1` will not answer, use `localhost`.

```sh
cd app && npm run check                  # layout model + real exports, no browser needed
```

`npm run check` also writes eight sheets to `work/sheets/`. Decoding them is a
separate step, because it needs Chrome and a Python stack the app does not:

```sh
uv run --with pillow --with numpy --with segno --with zxing-cpp \
  python3 gen/sheets.py --url https://www.instagram.com/hyperspace.av/
```

That one also wants **poppler** — the only system package this prototype needs
beyond Chromium, and the one thing here that is not satisfied by a fresh macOS:
`brew install poppler`, or `apt-get install poppler-utils`. It rasterises the
PDFs, and it is poppler rather than Chrome on purpose, so the renderer that
checks a file is not the renderer that checks the other one. `mutool` works
too, `QRD_PDFRAST` overrides the lookup, and adding `--with pypdfium2` to the
command above needs no system package at all — at the cost of being Chrome's
PDF engine, which makes the two halves less independent.

Regenerating artefacts needs `uv` and a Chromium (`QRD_CHROME` overrides the
lookup). Nothing else is machine-specific; verified by cloning the branch
clean and running the whole thing.

## Six views

| view | what it is |
| --- | --- |
| **gallery** | 29 stills. Pick a destination (screen px, sticker mm, etched, projected) and every code gets a verdict against it. |
| **families** | The same stills grouped by what the solid *is* — hypercubes, cross-polytopes, duoprisms, simplexes, the 24-cell — including the members that have no still, and why. |
| **live solver** | Re-derives the code per update, 0.2 ms a solve. Grab it and fold it. |
| **sprite** | 216 precomputed frames, 94 KB, no solver on the client. |
| **stickers** | Lay codes on a sheet, see the cut lines, export SVG or PDF. |
| **editions** | Browse the one-of-one space live: a pose, a constant pinned into the fragment, a treatment. Swapping the number is free; the panel hands you the command that bakes the real thing. |

## State: done

- **The trick.** `gen/basis.py` reduces QArt to an affine map, so a browser
  solves in 0.2 ms instead of 2 s. The URL is baked into the factorisation —
  point it elsewhere and every artefact must be rebuilt.
- **29 stills** across eight subjects, seven dot styles, six palettes.
- **The editions explorer.** A tab that re-derives a code per control change.
  The trick that makes it possible: the factorisation does **not** depend on
  which constant is pinned — `_build` picks pivots by position and only
  `solve()` reads their values — so one blob per digit count serves all fifteen
  numbers, and swapping π for φ is a 0.2 ms re-solve. Poses ship as target
  bitmaps (529 bytes each) rather than porting `polytopes.py` to JS.
  `gen/explore_data.py` writes both, and also does the furniture search below.
- **Editions.** `gen/editions.py` pairs one pose with one irrational constant,
  pinned into the leading digits of the numeric filler, so the fragment opens
  with the number: a code is a one-of-one in both its shape and its payload.
  `basis.py` grew `pin_digits` for it, extending the `forced` map that already
  held the URL. Costs **3 modules a digit**, linear to the end of the filler.
  5/5 rasterised, decoded, and checked that the fragment really begins with the
  digits asked for.
- **The family tree.** `gen/polytopes.py` carries the taxonomy and the reject
  log as data rather than a comment, `gallery.py` writes both into the
  manifest, and the families view reads it. A subject that was rendered and
  rejected is part of the answer, so it is shown with its reason instead of
  being absent.
- **Measurement.** `gen/robust.py` measures the *rendered* file, not the
  matrix: min px/module, blur tolerance, flash tolerance. The manifest carries
  those plus the module grid as base64.
- **One app.** Vite + React + shadcn. `web/` is deleted; `tiles` folded into
  the gallery as a medium.
- **Sticker builder.** `lib/sheet.ts` (pure mm geometry), the preview, and
  `lib/export.ts` (SVG + a hand-written vector PDF).
- **Styled exports.** `lib/style.ts` is the TypeScript twin of `gen/style.py`,
  so a sheet exports with the dot, eye and colour treatment it previews with —
  arcs in the SVG, the matching cubics and an axial shading in the PDF, still
  no dependency and still no raster.

## Everything is verified against an independent path

Nothing here is trusted on looks.

| what | how | result |
| --- | --- | --- |
| the 29 stills | Chrome rasterises each SVG, zxing decodes it | 29/29 |
| the sprite | every frame decoded before shipping | 216/216 |
| the live solver | frame pulled off the React canvas, decoded in Python | lands on the URL |
| the exports | 8 sheets rasterised by Chrome (SVG) and poppler (PDF), every sticker decoded, one of each code measured | 276/276 |
| the style port | all 29 stills drawn again by `lib/style.ts` and diffed against `gen/style.py`'s own render | 26 bit identical, 3 within a pixel |
| the layout model | every figure in STICKERS.md asserted in code | 85 checks |

## Open — all four are physical, none are code

See STICKERS.md for the detail. In short, each needs one cheap real-world test:

1. **Etch floor.** `media.ts` says 1.0 mm/module. A guess — kerf and undercut
   are specific to your machine and material. Etch one test plate at several
   sizes, scan each, keep the smallest that reads.
2. **Projection floor.** Assumes a module must subtend ~1 mrad, i.e. a 2 m code
   at 20 m. Arithmetic, never tested. Put a still on the projector, walk to the
   back row.
3. **PDF cut layer.** The PDF draws cuts as magenta strokes. It has no optional
   content groups and no spot colours, so a vendor wanting a named cut plate
   should be given the **SVG**, which carries its cuts in a `#cutline` group.
4. **A4 print-then-cut area.** Derived from Cricut's Letter inset (13.45 mm all
   round), not published. One A4 test cut, or read it off Design Space.

## Smaller opens, in the code

- **Three renderers draw a styled module grid, and only two are held together
  by a test.** `lib/render.js` paints the canvas for the live solver,
  `gen/style.py` writes the stills, `lib/style.ts` feeds the exporters, and all
  three carry the same `FINDER`, the same `DOTS` table and the same eye ratios
  independently. `gen/twins.py` pins the last two — change one and a command
  tells you. Nothing pins `render.js`; the README calls it a twin and that is
  an assertion, not a measurement. Deliberate: its drift is cosmetic and shows
  up the moment you open the live view, where a divergent *export* would not,
  and a third harness would be friction on every style change. If a constant
  ever gets tuned in one file, this is the paragraph to remember.

- Four of five texture blobs are gitignored (358 KB each). Only `gothic` ships;
  the live solver's texture picker prints the command for the others.
- The builder preview draws codes with `preserveAspectRatio="none"`. Harmless
  for square codes, would distort anything non-square. The **exporters** do not
  have this issue — they re-render from the module grid.
- No tests on the React components. The pure modules (`sheet.ts`, `export.ts`)
  are covered by `npm run check`; the UI is covered by having been driven in a
  browser, which does not survive a refactor.

## Things not to rediscover

- **The ghost button was dead for months** — `drawStyled` fills opaque paper,
  and the overlay was composited behind it. Fixed; the fix is a tint on top,
  because "under the modules" is unreachable over opaque paper.
- **`destination-over` and Fast Refresh both produced false alarms.** Twice a
  change looked broken because the page was running a stale module. Reload
  before believing a negative result.
- **`gen/gallery.py` is not reproducible, and that is pyqart, not a bug here.**
  pyqart retries its elimination until the error count reaches zero, and the
  retry is not seeded, so re-running the generator rewrites every `matrix` with
  a different but equally valid code. Expect a 29-file diff for no change. The
  style fields added to the manifest were therefore written from gallery.py's
  own tables rather than by regenerating; `gallery.py` emits them from now on.
- **The pose's quarrel is with the QR's furniture, not with the number.** A
  search over which constant suits which pose is numerology: across 1680
  combinations the agreement between a pinned bit and the drawing had sd 2.9%
  where a fair coin gives 2.8%, and the best pairing at one mask correlates
  −0.009 with the best at another. What *is* real is that 497 modules are
  finders, timing, alignment and format, fixed by the standard; ink landing on
  one that shows paper is lost before any budget is spent. That sets a per-pose
  ceiling (90.3% for `c16_tilt`, 98.6% for `duo88_tilt`) and it predicts the
  measurements. Margin and the camera distances slide a pose off them —
  `gen/explore_data.py` does that sweep, nine of fourteen poses reach a 100%
  ceiling, and `c16_tilt` gains 8.3 points of measured stroke fidelity with its
  ink count *up* 1.6%. Rotation is never swept: the 0/45/90 rule is load-bearing.
- **Spend the budget on the ink first.** The committed pivot orders are
  image-independent because the live solver reuses one factorisation across
  every frame. A still has no such constraint. A drawing's ink is only a
  quarter of the symbol, so ranking ink modules first makes every stroke solid
  and leaves the rest to clump as halo: +11 to +15 points of stroke fidelity at
  equal digits. It is a redistribution, not a gain — background fidelity drops
  from 76.6% to 72.8% — and past about 48 pinned digits the background wins and
  the code goes muddy. 24 to 48 digits is the usable range, not 96.
- **The affine path's extra noise is the 511 cap, not the pivot order.** An
  affine still is ~3.5 points behind pyqart on drawing fidelity, and it is
  tempting to blame the fixed pivot order. It is not: ranking pivots by image
  contrast instead moved it 0.3 points, and the mask moved it 0.7 either way.
  The cap is the whole gap. 269 numeric groups, one bit pinned each to hold the
  group under 512, is 269 modules; an uncontrolled module is right by chance
  half the time, so that predicts 3.2 points against 3.5 measured. pyqart does
  not pay it because it retries instead, which is fatal in a loop and free for
  a still. **Open:** lift the cap for stills, check the solved groups for
  legality, re-solve the rare one over 999.
- **Only `export_js.py` takes the fast path** through `basis.py`. Everything
  else calls pyqart directly and pays ~2 s per image — fine for a still,
  impossible for a frame.
- **Live solver state**: every control lives in one object behind
  `lib/useMirror.ts`, synced on a single dependency. Add fields to that object,
  never a second mirrored ref — the point is that a new control cannot silently
  fail to reach the render loop.
- **Was Vite worth it?** It downloads 11x more than the old static pages
  (44 KB → 502 KB) for roughly the same features plus the medium selector. It
  was a bet on the sticker builder, and the builder now exists. Worth knowing
  the trade was deliberate rather than accidental.

## Next

The builder is feature-complete for a first pass. The useful next moves are
physical: print a sheet, scan it, and find out which of the four guesses above
were wrong.
