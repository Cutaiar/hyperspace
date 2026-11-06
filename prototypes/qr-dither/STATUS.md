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
cd app && npm run check                  # layout model + a real export, no browser needed
```

Regenerating artefacts needs `uv` and a Chromium (`QRD_CHROME` overrides the
lookup). Nothing else is machine-specific; verified by cloning the branch
clean and running the whole thing.

## Four views

| view | what it is |
| --- | --- |
| **gallery** | 29 stills. Pick a destination (screen px, sticker mm, etched, projected) and every code gets a verdict against it. |
| **live solver** | Re-derives the code per update, 0.2 ms a solve. Grab it and fold it. |
| **sprite** | 216 precomputed frames, 94 KB, no solver on the client. |
| **stickers** | Lay codes on a sheet, see the cut lines, export SVG or PDF. |

## State: done

- **The trick.** `gen/basis.py` reduces QArt to an affine map, so a browser
  solves in 0.2 ms instead of 2 s. The URL is baked into the factorisation —
  point it elsewhere and every artefact must be rebuilt.
- **29 stills** across eight subjects, seven dot styles, six palettes.
- **Measurement.** `gen/robust.py` measures the *rendered* file, not the
  matrix: min px/module, blur tolerance, flash tolerance. The manifest carries
  those plus the module grid as base64.
- **One app.** Vite + React + shadcn. `web/` is deleted; `tiles` folded into
  the gallery as a medium.
- **Sticker builder.** `lib/sheet.ts` (pure mm geometry), the preview, and
  `lib/export.ts` (SVG + a hand-written vector PDF).

## Everything is verified against an independent path

Nothing here is trusted on looks.

| what | how | result |
| --- | --- | --- |
| the 29 stills | Chrome rasterises each SVG, zxing decodes it | 29/29 |
| the sprite | every frame decoded before shipping | 216/216 |
| the live solver | frame pulled off the React canvas, decoded in Python | lands on the URL |
| the exports | PDF via macOS Quartz, SVG via Chrome, both decoded | 15/15 each |
| the layout model | every figure in STICKERS.md asserted in code | 28 checks |

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

- **Exports carry geometry, not style.** A sheet of `pal-red` or `sty-dots`
  previews styled and downloads as plain black squares, because the exporters
  re-render from the module grid and the grid has no palette in it. The UI says
  so. A real fix means porting `gen/style.py`'s renderer to TypeScript so the
  exporters can draw dots, eyes and colours at a physical size.

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
