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

   Not implemented, and not to be implied: PDF optional content groups (true
   layers) and spot colours. The PDF's cuts are ordinary magenta strokes. A
   vendor who needs a named spot plate wants the SVG.

5. ~~**Style**~~ — done: `src/lib/style.ts`, the TypeScript twin of
   `gen/style.py`. The exporters carry the dot, eye and colour treatment, not
   just the geometry, so a sheet of `pal-red` or `sty-dots` downloads as the
   thing the gallery shows. Still re-rendered from the grid: a rounded module
   is arcs in the SVG and the matching cubics in the PDF, and a gradient is an
   axial shading clipped to the module path, so the PDF stays dependency-free
   and unrasterised.

   The manifest carries the style because it already carries the grid.
   `gen/gallery.py` writes every argument it handed `style.to_svg` —
   `eye_frame`, `eye_core`, `fg`, `fg2`, `bg`, `plate_radius`, `style_eyes` —
   next to the `dot` it already wrote. A table of the same facts in the app
   would be a second place for them to drift.

   "Twin" is a claim, so it is tested rather than asserted. `npm run twins`
   draws all 29 gallery stills again through `lib/style.ts`, and `gen/twins.py`
   shoots both versions with the same Chrome and compares them: **26 of 29 are
   bit identical**, and the three circular ones differ only within one pixel of
   an edge, because `style.py` emits a `<circle>` where the port emits the same
   circle as four arcs. The test is *where* pixels differ, not how many — a
   0.1-module offset is caught, a 0.02-module one is under a pixel and is not,
   so the two renderers agree to about 0.015 mm on a 44 mm sticker.

Codes come from `manifest.json`. Re-render from `matrix` rather than scaling the
SVG when a code needs an exact physical size — the grid is in the manifest
precisely so this does not go through a rasteriser.

## What a styled sheet actually costs

Measured, not assumed. `cd app && npm run check` writes eight sheets to
`work/sheets/`; `gen/sheets.py` rasterises each one with a renderer that had
nothing to do with writing it — headless Chrome for the SVG, poppler for the
PDF (`brew install poppler`; `mutool` or `pypdfium2` if you would rather, and
`QRD_PDFRAST` to pick), both at 384 dpi so the two columns compare the files
and not the settings — decodes every sticker, then crops one sticker of each
code and runs it through `gen/robust.py`.

**276/276 stickers decoded** across those sixteen files, styled and plain,
including 24/24 on the hostile sheet (vendor, zero gutter, `pal-red` and
`pal-invert` alternating). Per code, at 44 mm:

| sheet | code | min px/module (SVG / PDF) | blur | flash |
| --- | --- | --- | --- | --- |
| ordinary | `c16-tilt`, no style | 1 / 1 | 0.45 | 1.2 |
| ordinary | `pal-red` | 1 / 1 | 0.45 | **0.6** |
| ordinary | `pal-grad` | 1 / 1 | 0.45 | 1.2 |
| ordinary | `sty-classy-rounded` | 1 / 1 | 0.45 | 1.2 |
| ordinary | `sty-dots` | **3 / 3** | 0.45 | 1.2 |
| ordinary | `sty-dots-tight` | **2 / 3** | 0.45 | 1.2 |
| hostile | `pal-red` | 3 / 3 | 0.40 | 0.6 |
| hostile | `pal-invert` | 3 / 3 | 0.40 | 1.0 |

Three things worth reading off that:

- **Circular modules cost resolution on a sheet too**, the same way they do on
  a still, and a little more of it: `dots` measures 3 px a module here against
  the 2 the gallery measures on the isolated still, because a sticker cropped
  out of a page raster carries its surroundings with it. At 0.603 mm a module,
  3 px is a camera resolving 0.2 mm — so a dots sheet wants more millimetres
  per sticker, not fewer. The two writers agree within one step everywhere,
  `dots-tight` included, which is the point of measuring both.
- **Red keeps its glare penalty**: flash 0.6 against 1.2 for ink, exactly the
  figure the gallery measures on the still. Styling the export did not invent
  a new weakness or hide an old one.
- **A zero gutter costs every code a step**, styled or not — at no gutter the
  crop around one sticker contains its neighbours' ink, and a camera pointed at
  one sticker sees the same thing. That is an argument for the gutter, not
  against the style.

These are synthetic rasterisations of a file, like every other number here.
They say the exporter is sound; they do not say what a printer will do with it.


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
