# Sticker builder — spec and the numbers behind it

Everything here is either measured, cited, or flagged as a guess. The point of
writing it down is that the next session should not have to re-derive it, and
should not have to trust it either.

## What it does

Pick codes from the gallery, lay them out on a sheet, export something a
printer or a cutter will accept. Two destinations, and they want different
files:

| | vendor kiss-cut sheet | home print-then-cut |
| --- | --- | --- |
| who cuts | the printer, from your cutline | your Cricut/Silhouette |
| needs | bleed, a named spot-colour cutline layer | registration margin, no cutline |
| export | 300 DPI PDF or SVG, cutline on its own layer | PDF/PNG at 300 DPI |

## The numbers

Vendor conventions, from the sources at the bottom. They disagree, so these are
the conservative end:

- **bleed** 3 mm (1/8") of art past every cut
- **gutter** 4.76 mm (3/16") between adjacent cut lines — some vendors say 1/4",
  one says 1/2", StickerApp says 2 mm. Take the largest your printer allows.
- **sheet edge margin** 3 mm (1/8") from any cut line
- **safe zone** 1.6 mm (1/16") inside the cut for anything that must not be clipped
- **minimum sticker** 6 mm
- **cutline** 1 pt, solid, closed vector, spot colour

Home print-then-cut, Cricut on US Letter: usable area **7.44" × 9.94"**
(189.0 × 252.5 mm), corners reserved for registration marks. Older guides say
6.75" × 9.25" — that is the pre-update figure and will under-fill the sheet.

## What that costs you, which is the whole design problem

Module pitch sets a floor on sticker size, and sticker size sets the yield.
Computed in `gen/` terms at the 0.6 mm/module rule of thumb:

| code | modules + quiet | min sticker | grid | per Letter sheet |
| --- | --- | --- | --- | --- |
| art, version 12 | 73 | **43.8 mm** | 3×5 | **15** |
| art, version 15 | 85 | 51.0 mm | 3×4 | 12 |
| plain ECC M | 37 | 22.2 mm | 7×9 | **63** |

**The art code costs about 4× the sheet.** A builder that does not say this out
loud is hiding the only decision that matters. Fixing the size instead:

| sticker | grid | per sheet | pitch at 73 modules |
| --- | --- | --- | --- |
| 35 mm | 4×6 | 24 | 0.479 mm — under the floor |
| 40 mm | 4×5 | 20 | 0.548 mm — under the floor |
| 44 mm | 3×5 | 15 | 0.603 mm |
| 50 mm | 3×4 | 12 | 0.685 mm |

Every figure in both tables above is asserted in `app/check/sheet.check.ts`
against the layout model, so the document and the code cannot drift apart:

```sh
cd app && npm run check
```

## Build order

1. ~~**Sheet model**~~ — done: `src/lib/sheet.ts` — `src/lib/sheet.ts`: paper sizes, margins, gutter, bleed;
   papers, usable area per cut mode, `layout()` in millimetres, `assign()` to
   fill cells, `pitch()`/`minSticker()`, and warnings for the cases that bite
   (bleed wider than half the gutter, under the 6 mm minimum, nothing fits).
   Pure: no React, no DOM, no SVG, so the preview and the exporter read the
   same geometry and cannot disagree.
2. ~~**Preview**~~ — done: `src/components/Builder.tsx`. The sheet drawn to
   scale in millimetres, cut lines, bleed, Cricut's reserved corners, the
   per-sheet count, and the warning that says what a size costs you: at 44 mm
   a version-12 code is 15 to a Letter sheet, and dropping to 40 mm buys 20 at
   0.548 mm per module, under the floor.
3. ~~**Selection**~~ — done: pick codes from a thumbnail grid; the sheet fills
   round-robin from whatever is selected.
4. ~~**Export**~~ — done: `src/lib/export.ts`. SVG with the cuts in a
   `#cutline` group, and a single-page vector PDF written by hand — no
   dependency, no rasterisation. Both re-render from the manifest's `matrix` at
   the exact physical size rather than scaling the published SVG, which is what
   the grid is in the manifest for.

   Verified end to end, not by inspection: a real 15-up Letter sheet was
   exported, the PDF rasterised by macOS Quartz and the SVG by Chrome, and
   zxing read **15/15 codes out of each file**, the seven inverted ones
   included.

   Not implemented, and not to be implied: PDF optional content groups (true
   layers) and spot colours. The PDF's cuts are ordinary magenta strokes. A
   vendor who needs a named spot plate wants the SVG.

Codes come from `manifest.json`. Re-render from `matrix` rather than scaling the
SVG when a code needs an exact physical size — the grid is in the manifest
precisely so this does not go through a rasteriser.

## Open, and not to be guessed at

- **Etch floor.** `media.ts` uses 1.0 mm/module. That is a placeholder. Kerf and
  undercut are process-specific; one test plate answers it and nothing else will.
- **Projection floor.** 1 mrad per module, i.e. 2 m wide at 20 m. Untested.
  Project a still, walk to the back row, try to scan it.
- **Which vendor.** Bleed and gutter above are the conservative intersection.
  A chosen printer's own template overrides all of it.
- **Inverted codes on a sticker.** `pal-invert` needs 3 px/module where square
  needs 1, and loses blur headroom. It scans on a screen; on film under a flash
  is a different question, and the one we have no measurement for.

## Sources

- https://stickerapp.com/support/stickers/products/sticker-sheet/sticker-sheet-layout-requirements
- https://www.discountlabels.com/wp-content/uploads/2023/09/StickerSheet-SalesSheet-web.pdf
- https://www.4over4.com/.well-known/okf/guide/how-to-design-sticker-sheets-with-expert-tips.md
- https://support.stickergiant.com/hc/en-us/articles/24764931649172
- https://www.printedmint.com/kiss-cut-sticker-guide
- https://help.cricut.com/hc/en-us/articles/360009429814-How-large-can-I-Print-Then-Cut
