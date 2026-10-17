# Theatrical lighting gels (Rosco, LEE, GAM) as anaglyph viewing-filter material, with San Francisco procurement

Research date: 2026-10-17. All prices, stock and availability were checked on that date unless marked otherwise. Companion data file: `gel_spectra.csv` in this folder. It has 46 columns of numeric per-wavelength transmittance, 400–700 nm in 5 nm steps. A larger file with all 287 LEE colour spectra was also scraped and saved in the session scratchpad at `/tmp/claude-0/-home-user-hyperspace/09698ced-e93f-5a72-90ce-f7bfc3eb3edb/scratchpad/gels/lee_full_library_spectra.csv`. Copy it into the project if pair optimisation needs the full library.

## Q1. Which candidate gel codes are real and current?

### Takeaway
Every Roscolux and LEE code in the brief is a real product listed on the makers' sites in October 2026. One correction: Rosco CalColor is numbered 42xx–49xx, not "4800". The 48xx block is CalColor Pink. Red is 46xx, Cyan 43xx, Green 44xx, Blue 42xx, Yellow 45xx and Magenta 47xx.

### Cited Findings
- **Roscolux current list (us.rosco.com catalog, 265 entries scraped).** All of these have live product pages: R19 Fire, R26 Light Red, R27 Medium Red, R24 Scarlet, R324 Cherry Red, R10 Medium Yellow, R12 Straw, R15 Deep Straw, R21 Golden Amber, R312 Canary, R45 Rose, R46 Magenta, R48 Rose Purple, R49 Medium Purple, R339 Broadway Pink, R344 Follies Pink, R346 Tropical Magenta, R68 Parry Sky Blue (the name is now "Parry Sky Blue"), R70 Nile Blue, R71 Sea Blue, R72 Azure Blue, R73 Peacock Blue, R77 Green Blue, R80 Primary Blue, R93 Blue Green, R95 Medium Blue Green, R370 Italian Blue, R89 Moss Green, R90 Dark Yellow Green, R91 Primary Green, R94 Kelly Green, R389 Chroma Green and R393 Emerald Green — [Rosco Roscolux catalog](https://us.rosco.com/en/products/catalog/roscolux); example page [R27 Medium Red](https://us.rosco.com/en/products/filters/r27-medium-red)
- **CalColor (current, listed under "Roscolux, Cinegel").**
  - Blue: R4215, R4230, R4260, R4290.
  - Cyan: R4307 (7.5), R4315, R4330, R4360, R4390.
  - Green: R4415–R4490. Yellow: R4515–R4590. Red: R4615–R4690. Magenta: R4715–R4790. Pink: R4815–R4890. Lavender: R4915–R4990.
  - Source: [Rosco R4690 CalColor 90 Red](https://us.rosco.com/en/products/filters/r4690-calcolor-90-red), [R4390 CalColor 90 Cyan](https://us.rosco.com/en/products/filters/r4390-calcolor-90-cyan) and the catalog above.
- **Rosco's own Y-transmission figures, from each product page's description:**

| Code | Name | Published transmission |
|---|---|---|
| R19 | Fire | 20% |
| R26 | Light Red | 12% |
| R27 | Medium Red | 4% |
| R24 | Scarlet | 22% |
| R324 | Cherry Red | 31% |
| R12 | Straw | 88% |
| R15 | Deep Straw | 65% |
| R21 | Golden Amber | 43% |
| R10 | Medium Yellow | 92% |
| R312 | Canary | 85% |
| R45 | Rose | 8% |
| R46 | Magenta | 6% |
| R48 | Rose Purple | 16% |
| R49 | Medium Purple | 4% |
| R344 | Follies Pink | 21% |
| R339 | Broadway Pink | 15% |
| R346 | Tropical Magenta | 22% |
| R68 | Parry Sky Blue | 14% |
| R70 | Nile Blue | 45% |
| R71 | Sea Blue | 30% |
| R72 | Azure Blue | 44% |
| R73 | Peacock Blue | 28% |
| R77 | Green Blue | 9% |
| R80 | Primary Blue | 9% |
| R93 | Blue Green | 35% |
| R95 | Medium Blue Green | 15% |
| R370 | Italian Blue | 31% |
| R89 | Moss Green | 45% |
| R90 | Dark Yellow Green | 13% |
| R91 | Primary Green | 7% |
| R389 | Chroma Green | 40% |
| R94 | Kelly Green | 25% |
| R393 | Emerald Green | 14% |
| R4290 | CalColor 90 Blue | 15% |
| R4390 | CalColor 90 Cyan | 39% |
| R4360 | CalColor 60 Cyan | 50% |
| R4490 | CalColor 90 Green | 18% |
| R4590 | CalColor 90 Yellow | 66% |
| R4690 | CalColor 90 Red | 30% |
| R4660 | CalColor 60 Red | 39% |
| R4790 | CalColor 90 Magenta | 28% |
| R4760 | CalColor 60 Magenta | 37% |
| R4730 | CalColor 30 Magenta | 52% |

  Source: the individual us.rosco.com/en/products/filters/<slug> pages, e.g. [R26](https://us.rosco.com/en/products/filters/r26-light-red), [R80](https://us.rosco.com/en/products/filters/r80-primary-blue), [R4790](https://us.rosco.com/en/products/filters/r4790-calcolor-90-magenta).
- **CalColor densities.** 15/30/60/90 correspond to ½, 1, 2 and 3 stops of the colour's complement. The line was designed around the spectral sensitivity of colour film. CalColor 90 = 60 + 30 (for example 4690 = 4660 + 4630, per Rosco's description) — [Rosco CalColor kit PDF via castinfo.de](https://www.castinfo.de/downloaditem//r/o/rosco_photo_filter_kits_calcolor.pdf); [Rosco R4690 page](https://us.rosco.com/en/products/filters/r4690-calcolor-90-red)
- **LEE current colour pages (333 product slugs on the LEE colour-effect index).** All of these exist: 002 Rose Pink, 010 Medium Yellow, 019 Fire, 024 Scarlet, 026 Bright Red, 027 Medium Red, 029 Plasa Red, 035 Light Pink, 036 Medium Pink, 046 Dark Magenta, 089 Moss Green, 101 Yellow, 104 Deep Amber, 106 Primary Red, 113 Magenta, 115 Peacock Blue, 116 Medium Blue-Green, 118 Light Blue, 119 Dark Blue, 120 Deep Blue, 121 LEE Green, 124 Dark Green, 126 Mauve, 128 Bright Pink, 132 Medium Blue, 139 Primary Green, 172 Lagoon Blue, 182 Light Red, 183 Moonlight Blue, 195 Zenith Blue, 323 Jade, 328 Follies Pink, 363 Special Medium Blue, 738 JAS Green, 787 Marius Red and 795 Magical Magenta — [LEE colour effect filters index](https://leefilters.com/lighting/colour-effect-lighting-filters/); e.g. [LEE 106](https://leefilters.com/colour/106-primary-red/), [LEE 787](https://leefilters.com/colour/787-marius-red/)
- **Rosco E-Colour+** is Rosco's line that uses LEE-style numbering, e.g. "Rosco E-Colour 106 Primary Red – 21in. x 24in. Sheet" — [Stage Lighting Store item API / listing](https://www.stagelightingstore.com/Rosco-E-Colour-106-Primary-Red). Rosco also publishes a cross-reference — [Lee to Rosco Equivalents](https://us.rosco.com/en/lee-rosco-equivalents)
- **GAM (GAMColor) is now sold under Rosco.** Rosco's site has a GAMColor catalog, and a "Rosco GAM Swatchbook" is sold — [Rosco catalog nav (gamcolor)](https://us.rosco.com/en/products/catalog/gamcolor); [Stage Lighting Store GAM swatchbook](https://www.stagelightingstore.com/Rosco-GAM-Swatchbook)

### Inferences
- **CalColor is not the best-characterised option for anaglyph, contrary to the brief's hypothesis.** The "90" grade is defined as 3 stops of attenuation of the complementary band. 3 stops is a factor of 8, i.e. roughly 10–13% leakage. Anaglyph needs about 1% or less (20–40 dB). A single CalColor 90 Red or 90 Cyan would therefore ghost badly. Two stacked 90s would give about 6 stops (≈1.6%), which is still worse than LEE 106 or 172 alone (see Q2). This inference is based on Rosco's stop definition, not on measured spectra.
- E-Colour numbers match LEE numbers by name, but the material is Rosco's. Do not assume E-Colour 106 has the same spectrum as LEE 106.

### Gaps
- GAM and Apollo per-code data were not researched in depth. GAM appears to be absorbed into Rosco's catalog. Apollo's current gel line and status were not verified.
- Rosco's product pages do not say which Roscolux codes use the polycarbonate substrate and which use polyester.

## Q2. What spectral data does each manufacturer publish, and what are the numbers?

### Takeaway
LEE publishes numeric per-wavelength transmittance for every colour, 400–700 nm in 5 nm steps. The values sit in the hover tooltips of the inline SVG graph on each colour page. I scraped all 287 LEE colours. Rosco no longer shows SED curves or numeric data on its website. Its SED curves are only in the myColor mobile app and the printed swatchbook, so the only numeric Rosco spectra found are a few independent lab measurements. On LEE's own numbers, the best performers are:
- Red: 106 Primary Red, or 026/029 for even lower leakage.
- Cyan: 172 Lagoon Blue or 183 Moonlight Blue. They pass about 0.1–0.2% at 610–640 nm.
- Magenta: 795 Magical Magenta or 128 Bright Pink.
- Green: 139 Primary Green (very clean but dim) or 124 Dark Green.
- Yellow: 010 Medium Yellow or 101 Yellow. Both pass ≤0.1% at 455 nm.
- Blue: 119, 363, 120 or 195.

### Cited Findings
- **What a LEE colour page publishes:**
  - A graph titled "Light transmitted (Y%) for each colour wavelength".
  - Two blocks, "Daylight (Source C)" and "Tungsten", each with Transmission Y, x, y, Absorption and Colour Temperature. For 106 Primary Red: Daylight Y 9.3, x 0.699, y 0.285, Absorption 1.03; Tungsten Y 12.8, x 0.693, y 0.305, Absorption 0.89.
  - The graph is an inline SVG. Each point carries a tooltip such as `<span>405</span>Colour: <b>0.287</b>`, at 405, 410 … 700 nm. The 400 nm value is the SVG path's first point (y = 100 − T%).
  - Source: [LEE 106 Primary Red page](https://leefilters.com/colour/106-primary-red/), raw HTML retrieved 2026-10-17.
- LEE's "Absorption" equals −log10(Y): −log10(0.093) = 1.03 and −log10(0.128) = 0.89, so it is optical density — [LEE 106 page](https://leefilters.com/colour/106-primary-red/) (computed check)
- **LEE's colour data comes in two forms.** Transmission is given against Source C daylight and against 3200 K tungsten, and the two differ by a few percent. A developer who built a 498-gel library noted that Rosco gives a single "Transmission = X%" figure on the web, while fuller data is in the myColor app — [jerryjonas3/plotedit PR #42](https://github.com/jerryjonas3/plotedit/pull/42)
- **Rosco's US product pages give only a description with "(Transmission = X%)".** No SED image or data appears in the page HTML; R27 has only "Good red primary … (Transmission = 4%)" — [Rosco R27](https://us.rosco.com/en/products/filters/r27-medium-red). Rosco says that all its colour data, with larger SED graphics, is in myColor — [Rosco search result snippet / spectrum.rosco.com](https://spectrum.rosco.com/index.php/2016/04/how-to-properly-choose-a-color-filter). The current myColor landing page offers only iOS and Android apps — [Rosco myColor app](https://us.rosco.com/en/mycolor-app). Rosco's guide describes the R27 SED as passing wavelengths above about 620 nm — [Rosco Guide to Color Filters PDF](http://www.rosco.com/us/litreq/catalogs/guide_to_color_filters.pdf)
- **Independent numeric Rosco spectra.** The R package photobiologyFilters 0.6.1 contains a few theatrical gels:
  - Rosco measurements (Shimadzu UV-2501PC with integrating sphere): E-Colour #89 Moss Green, Supergel #312 Canary, Supergel #343 Neon Pink (used).
  - LEE spectra digitised from LEE catalogue plots: 101, 105, 119, 199 and NDs.
  - Source: [photobiologyFilters theatrical_gels index](https://search.r-project.org/CRAN/refmans/photobiologyFilters/html/theatrical_gels.html); [CRAN package](https://cran.r-project.org/package=photobiologyFilters)

**Key-band transmittance (%) computed from LEE's published per-wavelength data (source: each page at leefilters.com/colour/<slug>/, scraped 2026-10-17).**

How to read the table:
- Columns 2–4 are narrow-band means: B455 = 445–465 nm, G545 = 530–560 nm, R625 = 610–640 nm. These are a proxy for projector primaries.
- Columns 5–7 are wide-band means: Bw = 420–490, Gw = 500–570, Rw = 600–700.
- The last three columns are LEE's own Y and chromaticity figures.
- 0.01 is LEE's floor value.

| LEE code | B455 | G545 | R625 | Bw | Gw | Rw | Y daylight | Y tungsten | x,y (daylight) |
|---|---|---|---|---|---|---|---|---|---|
| 029 Plasa Red | 0.01 | 0.01 | 43.09 | 0.01 | 0.01 | 54.21 | 5.8 | 8.7 | 0.693,0.303 |
| 026 Bright Red | 0.06 | 0.01 | 46.59 | 0.09 | 0.01 | 57.01 | 8.6 | 9.1 | 0.712,0.281 |
| 027 Medium Red | 0.30 | 0.01 | 20.30 | 0.25 | 0.01 | 44.19 | 3.6 | 5.3 | 0.712,0.261 |
| 106 Primary Red | 0.14 | 0.03 | 57.16 | 0.17 | 0.04 | 64.95 | 9.3 | 12.8 | 0.699,0.285 |
| 182 Light Red | 0.23 | 0.12 | 58.81 | 0.24 | 0.15 | 64.62 | 11.0 | 15.0 | 0.67,0.313 |
| 787 Marius Red | 0.01 | 0.01 | 2.56 | 0.01 | 0.01 | 31.99 | 1.0 | 1.7 | 0.714,0.283 |
| 164 Flame Red | 1.40 | 1.50 | 80.34 | 1.42 | 1.54 | 82.28 | 18.0 | 23.2 | 0.659,0.302 |
| 019 Fire | 0.66 | 1.70 | 81.25 | 0.68 | 1.49 | 82.02 | 18.9 | 24.0 | 0.664,0.31 |
| 024 Scarlet | 6.69 | 2.17 | 73.11 | 7.49 | 1.97 | 76.16 | 18.7 | 25.5 | 0.561,0.296 |
| 135 Deep Golden Amber | 0.01 | 0.61 | 69.13 | 0.01 | 1.34 | 72.02 | 19.5 | 26.5 | 0.667,0.326 |
| 507 Madge | 0.01 | 0.02 | 63.02 | 0.01 | 0.11 | 67.20 | 13.6 | 19.4 | 0.662,0.337 |
| 116 Medium Blue-Green | 29.87 | 16.79 | 0.01 | 31.15 | 28.03 | 0.01 | 16.5 | 12.4 | 0.113,0.28 |
| 118 Light Blue | 77.26 | 28.53 | 0.91 | 73.45 | 37.40 | 2.37 | 22.2 | 19.2 | 0.149,0.113 |
| 115 Peacock Blue | 61.46 | 49.93 | 1.05 | 61.41 | 56.20 | 1.36 | 35.2 | 28.6 | 0.134,0.296 |
| 132 Medium Blue | 57.82 | 6.28 | 0.17 | 51.75 | 13.36 | 2.99 | 8.3 | 7.0 | 0.137,0.11 |
| 172 Lagoon Blue | 58.96 | 24.50 | 0.12 | 58.02 | 34.92 | 0.49 | 25.4 | 16.3 | 0.141,0.22 |
| 183 Moonlight Blue | 69.14 | 21.65 | 0.15 | 65.00 | 31.07 | 0.48 | 18.7 | 15.5 | 0.128,0.168 |
| 323 Jade | 29.22 | 42.99 | 0.75 | 35.92 | 49.95 | 1.42 | 32.0 | 25.8 | 0.165,0.367 |
| 354 Special Steel Blue | 68.88 | 50.10 | 1.82 | 68.25 | 56.06 | 2.60 | 39.2 | 31.1 | 0.173,0.265 |
| 139 Primary Green | 0.03 | 23.65 | 0.02 | 0.55 | 21.96 | 0.04 | 11.9 | 10.1 | 0.196,0.712 |
| 124 Dark Green | 4.34 | 44.94 | 0.51 | 12.52 | 50.19 | 0.67 | 29.7 | 25.6 | 0.123,0.586 |
| 121 LEE Green | 4.71 | 76.16 | 26.25 | 15.69 | 76.77 | 22.68 | 64.0 | 58.0 | 0.302,0.534 |
| 089 Moss Green | 3.90 | 45.29 | 4.89 | 8.98 | 45.42 | 6.20 | 29.8 | 28.0 | 0.259,0.547 |
| 738 JAS Green | 0.07 | 71.15 | 16.06 | 6.44 | 71.59 | 14.66 | 52.3 | 47.4 | 0.315,0.587 |
| 113 Magenta | 6.77 | 0.04 | 66.54 | 5.97 | 0.10 | 72.85 | 10.9 | 14.7 | 0.563,0.217 |
| 128 Bright Pink | 35.28 | 0.54 | 75.77 | 31.32 | 1.50 | 79.10 | 13.7 | 18.8 | 0.401,0.151 |
| 126 Mauve | 28.02 | 0.02 | 15.03 | 23.26 | 0.26 | 45.16 | 4.1 | 5.0 | 0.287,0.082 |
| 046 Dark Magenta | 4.64 | 0.07 | 30.60 | 4.66 | 0.32 | 53.69 | 6.0 | 8.2 | 0.572,0.223 |
| 795 Magical Magenta | 47.53 | 0.49 | 62.38 | 42.51 | 2.47 | 72.10 | 13.3 | 16.7 | 0.323,0.138 |
| 328 Follies Pink | 48.37 | 2.72 | 78.26 | 44.24 | 5.14 | 81.16 | 21.6 | 24.6 | 0.335,0.18 |
| 002 Rose Pink | 67.15 | 10.09 | 86.55 | 63.11 | 15.27 | 86.86 | 32.7 | 34.2 | 0.328,0.202 |
| 036 Medium Pink | 51.99 | 27.38 | 85.14 | 50.77 | 28.61 | 85.98 | 45.4 | 48.2 | 0.36,0.268 |
| 035 Light Pink | 67.09 | 48.57 | 88.39 | 66.21 | 50.39 | 88.68 | 61.3 | 64.0 | 0.335,0.289 |
| 120 Deep Blue | 36.65 | 0.08 | 0.01 | 28.21 | 1.36 | 2.09 | 2.1 | 1.1 | 0.149,0.051 |
| 119 Dark Blue | 45.75 | 1.10 | 0.01 | 38.53 | 4.90 | 1.31 | 3.1 | 2.3 | 0.142,0.054 |
| 363 Special Medium Blue | 44.88 | 0.97 | 0.05 | 38.40 | 3.35 | 0.13 | 4.2 | 2.1 | 0.141,0.07 |
| 195 Zenith Blue | 47.17 | 0.65 | 0.01 | 39.18 | 3.72 | 6.66 | 2.7 | 2.5 | 0.142,0.046 |
| 101 Yellow | 0.09 | 81.66 | 88.15 | 2.96 | 73.20 | 88.48 | 80.0 | 80.7 | 0.451,0.507 |
| 104 Deep Amber | 0.86 | 60.22 | 84.42 | 3.97 | 50.96 | 83.63 | 63.9 | 73.0 | 0.496,0.462 |
| 010 Medium Yellow | 0.05 | 88.72 | 89.90 | 6.28 | 85.93 | 90.07 | 86.5 | 88.1 | 0.426,0.509 |
| 015 Deep Straw | 0.06 | 55.58 | 87.36 | 1.23 | 44.35 | 88.38 | 60.8 | 67.5 | 0.517,0.46 |
| 767 Oklahoma Yellow | 0.03 | 73.75 | 87.56 | 0.86 | 61.02 | 88.36 | 67.3 | 72.9 | 0.48,0.501 |

**Selected per-wavelength values (T%) from LEE's published data.** The full 5 nm tables are in `gel_spectra.csv`.

| nm | 106 Primary Red | 026 Bright Red | 029 Plasa Red | 182 Light Red | 172 Lagoon Blue | 183 Moonlight Blue | 115 Peacock Blue | 139 Primary Green | 124 Dark Green | 128 Bright Pink | 113 Magenta | 101 Yellow |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 400 | 0.245 | 0.091 | 0.012 | 0.386 | 21.601 | 28.854 | 31.421 | 0.016 | 3.324 | 38.235 | 6.773 | 0.085 |
| 440 | 0.287 | 0.151 | 0.016 | 0.379 | 53.263 | 67.156 | 55.836 | 0.01 | 1.852 | 39.863 | 9.503 | 0.012 |
| 460 | 0.095 | 0.037 | 0.01 | 0.174 | 60.082 | 69.999 | 62.111 | 0.033 | 5.171 | 32.813 | 5.53 | 0.099 |
| 480 | 0.024 | 0.01 | 0.01 | 0.065 | 70.274 | 66.689 | 70.524 | 0.923 | 29.638 | 19.02 | 1.856 | 6.22 |
| 500 | 0.01 | 0.01 | 0.01 | 0.027 | 67.342 | 60.225 | 78.156 | 13.157 | 65.244 | 6.765 | 0.47 | 41.543 |
| 520 | 0.01 | 0.01 | 0.01 | 0.026 | 50.716 | 45.295 | 74.284 | 32.946 | 66.417 | 1.297 | 0.088 | 67.84 |
| 540 | 0.013 | 0.01 | 0.01 | 0.053 | 28.546 | 25.5 | 57.075 | 29.024 | 52.038 | 0.733 | 0.058 | 81.136 |
| 560 | 0.086 | 0.014 | 0.01 | 0.312 | 10.462 | 9.314 | 30.556 | 10.016 | 26.131 | 0.162 | 0.012 | 84.877 |
| 580 | 1.021 | 0.208 | 0.22 | 2.382 | 1.711 | 1.631 | 10.259 | 1.255 | 7.39 | 1.637 | 0.359 | 87.299 |
| 590 | 4.716 | 1.382 | 1.363 | 7.751 | 0.807 | 0.807 | 5.56 | 0.405 | 3.699 | 9.702 | 3.975 | 87.891 |
| 600 | 16.427 | 7.549 | 7.162 | 21.321 | 0.332 | 0.367 | 2.622 | 0.098 | 1.571 | 33.155 | 20.499 | 87.946 |
| 610 | 36.552 | 23.37 | 22.102 | 41.52 | 0.139 | 0.172 | 1.289 | 0.024 | 0.68 | 58.823 | 45.064 | 87.171 |
| 620 | 54.149 | 42.22 | 38.985 | 55.883 | 0.09 | 0.116 | 0.939 | 0.014 | 0.455 | 74.238 | 62.886 | 87.309 |
| 640 | 70.392 | 62.566 | 57.883 | 69.955 | 0.176 | 0.219 | 1.154 | 0.021 | 0.553 | 85.045 | 80.359 | 89.405 |
| 660 | 75.286 | 69.661 | 65.059 | 73.196 | 0.235 | 0.314 | 0.918 | 0.012 | 0.437 | 86.685 | 83.671 | 87.164 |
| 680 | 77.624 | 71.663 | 70.372 | 75.637 | 0.263 | 0.319 | 0.569 | 0.01 | 0.231 | 88.251 | 84.505 | 88.46 |
| 700 | 81.051 | 75.38 | 73.739 | 76.35 | 3.595 | 3.025 | 4.884 | 0.324 | 2.474 | 88.686 | 86.133 | 91.109 |

Source for both tables: LEE colour pages, e.g. [106](https://leefilters.com/colour/106-primary-red/), [172](https://leefilters.com/colour/172-lagoon-blue/), [183](https://leefilters.com/colour/183-moonlight-blue/), [139](https://leefilters.com/colour/139-primary-green/), [128](https://leefilters.com/colour/128-bright-pink/), [101](https://leefilters.com/colour/101-yellow/), [795](https://leefilters.com/colour/795-magical-magenta/), [010](https://leefilters.com/colour/010-medium-yellow/).

### Inferences
- **Red/cyan, best single-layer pick: LEE 106 Primary Red + LEE 172 Lagoon Blue or 183 Moonlight Blue.**
  - 106 passes about 57% at 610–640 nm and ≤0.15% in blue and green.
  - 172 and 183 pass about 0.1–0.2% at 610–640 nm, but only about 22–25% at 545 nm. The cyan eye is green-starved, so the image will look blue-heavy unless the renderer compensates.
  - 115 Peacock Blue doubles the green (≈50%) but leaks about 1% red, roughly 7–9x worse.
  - Blue-green leakage of the red gels is far below the cyan gels' red leakage. Ghosting will be dominated by the cyan eye seeing red.
- **Projectors with an orange-shifted red.** If the red primary has energy at 590–600 nm (common on lamp projectors), 106 still passes 4.7–16% there, and the cyans pass about 0.3–0.8%. 026 Bright Red and 029 Plasa Red cut harder below 600 nm (≈1.4% at 590), trading about 20–25% less red brightness for that. The final choice should come from measured projector primaries; another researcher covers that.
- **787 Marius Red and 027 Medium Red are poor choices.** They pass only about 2.6% and 20% at 625 nm, so they would make the red eye very dark.
- **Magenta/green.** For the green eye, 139 Primary Green is spectrally the cleanest (R and B ≤0.03%) but passes only about 24% peak. 124 Dark Green is about twice as bright but leaks 4% blue at 455 nm. For the magenta eye, 795 Magical Magenta (B 47.5%, G 0.49%, R 62%) or 128 Bright Pink (B 35%, G 0.54%, R 76%) work. 113 Magenta and 046 Dark Magenta pass too little blue (≈5–7%) to make a good magenta eye.
- **Yellow/blue (ColorCode-like).** 010 Medium Yellow and 101 Yellow block 455 nm to ≤0.1% with about 82–90% elsewhere, which is excellent. For the blue eye, 363 Special Medium Blue (B 45%, G 1%, R 0.05%) or 119 Dark Blue work.
- **Pale pinks (035, 036, 002)** leak 10–50% green. They are useful only as brightness-balancing or tinting layers, not as separating filters.
- **Stacking two identical layers** roughly squares the fractional transmittance. For example, two layers of 172 would cut 625 nm leakage to about 0.0001–0.0004 (near LEE's floor), but cut 545 nm to about 6%. This is an approximation that ignores inter-reflection gains.

### Gaps
- No numeric per-wavelength data exists on the web for any Roscolux code in the brief (R26, R27, R80, R89, R91, R93 and so on) or for CalColor. Numbers would need the Rosco myColor app (not accessed) or a spectrometer. I did not read approximate values off Rosco graphs, because no Rosco graph was reachable on the web.
- LEE does not state which illuminant or geometry its per-wavelength curve uses. Spectral transmittance is illuminant-independent, but the page's "Y%" heading is ambiguous. Values below 0.01 are reported as 0.01, so the true out-of-band blocking may be better than shown.
- The photobiologyFilters Rosco columns in the CSV are E-Colour #89 and Supergel #312. They are not the Roscolux codes in the brief, and are included only as independent measured references.

## Q3. Material, thickness, optics, heat, cutting and mounting, and stacking losses

### Takeaway
- Roscolux uses two substrates: deep-dyed PET polyester (35–64 µm) and body-coloured polycarbonate (75–100 µm).
- LEE colour effect filters are polyester, 0.08 mm thick.
- Both are non-diffusing colour films that are easy to cut. Reflection losses (≈5–6% per surface) are already included in single-sheet transmission data. Stacking multiplies the transmittances, each of which already includes its own reflection losses.

### Cited Findings
- **Roscolux substrates.**
  - Polyester (PET) is 1.4–2.5 mil (35–64 µm), softens at 257°F (125°C) and melts at 572°F (300°C).
  - Body-coloured polycarbonate with a fire-retardant additive is 3–4 mil (75–100 µm), softens at 320°F (160°C) and melts at 425°F (220°C). It "remains in a relaxed state in hot conditions without puckering".
  - Sizes: 20"×24" sheets and 24"×25' rolls. Polyester rolls also come 48" wide.
  - Source: [Rosco Roscolux product page](https://us.rosco.com/en/product/roscolux)
- **How the two Roscolux substrates are made.** The deep-dyed polyester starts as a clear PET film run through a heated dye bath, so "the dye is trapped below the surface". The polycarbonate is coloured by extruding resin and dye together — [Stage Lighting Store Roscolux description (manufacturer text)](https://www.stagelightingstore.com/06-No-Color-Straw). Adorama describes a "tri-extrusion" that seals the coloured layer between clear layers — [Adorama RO27](https://www.adorama.com/ro27.html). This is a retailer claim and was not verified against Rosco.
- **LEE thickness and heat.** "Most Polyester coloured effect filters are 0.08mm thick." LEE gives no specific heat rating, saying "It is a complex calculation" — [LEE Filters Direct FAQ](https://leefiltersdirect.com/apps/frequently-asked-questions). Retailers quote 356°F heat resistance for several LEE polyester filters — [search summary of retailer listings, e.g. Scheimpflug](https://www.scheimpflug.com/product-page/flag-4x4-frame-skinned-420-lifght-opal-rental) (secondary).
- **Rosco Supergel** is a Rosco filter range sold alongside Roscolux, and many Roscolux codes are listed as "Roscolux, Supergel" — [Rosco Supergel](https://us.rosco.com/en/product/supergel); [Rosco R27](https://us.rosco.com/en/products/filters/r27-medium-red)

### Inferences
- **Reflection loss.** The Fresnel loss per uncoated surface at normal incidence is about 6.0% for PET (n≈1.65) and about 5.1% for polycarbonate (n≈1.585). Two surfaces lose about 10–12%.
  - LEE's highest in-band values (≈88–91% for 010 and 101) are consistent with this, so the published transmittances already include the sheet's own reflection losses.
  - A two-layer stack with an air gap transmits about T1×T2 using the published single-sheet values (slightly better because of inter-reflections). Laminating the two layers optically, or index-matching them, would recover about 6–12%.
  - These are calculations, with n values from general polymer optics; I found no source specific to the gels.
- **Optical clarity.** Colour-effect gels are non-diffusing, unlike the diffusion and frost products. Neither maker publishes haze, wavefront or birefringence data.
  - Thin films (0.035–0.1 mm) will ripple if not held flat. Mounting between two clear rigid sheets (acrylic or CR-39 blanks), or tensioning in a frame, improves image quality.
  - PET is birefringent. It does not matter for anaglyph, but it would cause colour fringes if combined with polarised 3D.
  - Scratches are easy to make. Cut with a sharp blade on a clean surface and handle by the edges.
- **Body-dyed and deep-dyed filters** (Roscolux polycarbonate and deep-dyed polyester) should resist surface abrasion of the colour better than surface-coated films. Whether LEE coats or dyes its colour was not verified.

### Gaps
- No manufacturer haze or clarity specifications were found.
- LEE's base-film process (surface coating or body dye) was not confirmed from a LEE source.
- Which Roscolux codes are polycarbonate and which are polyester was not found.

## Q4. Are swatch books a fast, cheap experiment source?

### Takeaway
Yes, for a first test. The Rosco books (Roscolux, E-Colour, GAM, Cinegel) cost about $9.95, and the LEE Designer's Edition about $25–28. Both are in stock at US retailers. Each sample is about 1.5"×3.25" (38×83 mm), roughly enough for one eye of one pair of glasses per colour. A Roscolux book gives one each of R27/R26/R80/R89/R91 and so on. The catch is that Rosco has no numeric spectra, while the LEE book matches the LEE data above.

### Cited Findings
- Stage Lighting Store, 2026-10-17:
  - Rosco Cinegel Swatchbook $9.95 (qty 160); Rosco GAM Swatchbook $9.95 (qty 23); Rosco E-Colour Swatchbook $9.95 (qty 74).
  - Rosco Large Roscolux Swatchbook 3"×6" (950SBLUX0306) $29.99 (qty 7); Rosco Large Cinegel Swatchbook 3"×5" $29.99 (qty 0).
  - Source: [Stage Lighting Store](https://www.stagelightingstore.com/Rosco-Large-Roscolux-Swatchbook-3X6) (via the site's /api/items search)
- Production Advantage: "Rosco Gel Swatchbook" (SKU ROSCOSWATCHBOOK) $9.95; "Lee Gel Swatchbook" (SKU LEESWATCHBOOK) $25.00 — [Production Advantage swatchbooks](https://proadv.com/supplies/swatchbooks/)
- Studio Depot (Burbank, CA): LEE swatch book $28.00, "In Stock: Order now to ship the next business day" — [Studio Depot LEE swatchbook](https://www.studiodepot.com/leeswatchbook.html)
- **LEE's books.** The Designers Edition is "Pouched, with Numeric Lookup" and contains "a sample of every colour in our lighting gel collection". There is also a Zircon Edition for LEDs. Dealers may supply a swatch book on request — [LEE Filters Direct FAQ](https://leefiltersdirect.com/apps/frequently-asked-questions)
- **Rosco small swatchbook size and price.** It is usually listed as about 1.5"×3.25" (Adorama lists 1.75"×3.25"), for about $9.95–$28. Older reports say Rosco used to give them away free; this was not confirmed as current — [Adorama Rosco swatch book](https://www.adorama.com/rosb.html); [B&H Roscolux Swatchbook 950SBLUX0103](https://www.bhphotovideo.com/c/product/45189-REG/Rosco_950SBLUX0103_Roscolux_Swatchbook.html) (from search snippet; B&H blocked direct fetch)

### Inferences
- A single swatch (~38×83 mm, minus the bound end) can be cut into two pieces of about 38×38 mm. That is enough for one lens of a cardboard frame at a single layer, or both pieces stacked for a double layer.
- **Suggested plan.** Buy one LEE Designers Edition, which gives a sample of every candidate LEE code in Q2. Optionally add one Roscolux book for side-by-side visual checks. Then buy full sheets only of the winners. One 21"×24" sheet yields dozens of lens pairs.

### Gaps
- Exact usable swatch area (excluding binding and printed label) was not measured or published.
- Whether a free Rosco or LEE swatch book is currently available on request in the US was not confirmed.

## Q5. Where to buy fast to San Francisco (procurement records, 2026-10-17)

### Takeaway
- LEE sheets: Studio Depot (Burbank, CA) shows the candidate LEE codes in stock at $12.00 per 21"×24" sheet, shipping the next business day. California ground delivery is likely 1–2 days.
- Roscolux and CalColor sheets: Stage Lighting Store lists them at $11.50 per 20"×24" with live warehouse quantities.
- Second sources: Production Advantage (LEE $11, Rosco swatchbook), Glazer's ($12 LEE), Adorama and Full Compass (~$11–11.50).
- No dedicated walk-in gel counter in San Francisco was confirmed. Call Holzmueller (sells expendables, appointment only) and Samy's Camera SF (sells Rosco E-Colour sheets) before going.

### Cited Findings — procurement records

The LEE codes below were all checked on 2026-10-17 at Studio Depot, Burbank, CA ("Studio Depot, Burbank, CA 91504" appears in the page footer). Each is a LEE Filters 21"×24" sheet at $12.00, marked "In Stock: Order now to ship the next business day":

| LEE code | Studio Depot SKU |
|---|---|
| 106 | CL106 / 106S |
| 026 | 026S |
| 029 | 029S |
| 182 | 182S |
| 172 | 172S |
| 183 | 183S |
| 115 | 115S |
| 116 | 116S |
| 118 | 118S |
| 139 | 139S |
| 124 | 124S |
| 089 | 089S |
| 113 | 113S |
| 128 | 128S |
| 126 | 126S |
| 046 | 046S |
| 002 | 002S |
| 101 | 101S |
| 010 | 010S |
| 104 | 104S |
| 119 | 119S |
| 363 | 363S |
| 120 | 120S |

Example link: [Studio Depot LEE 106](https://www.studiodepot.com/31-lee-s106.html). Every other code uses the same URL pattern, e.g. [172](https://www.studiodepot.com/31-lee-s172.html), [183](https://www.studiodepot.com/31-lee-s183.html), [029](https://www.studiodepot.com/31-lee-s029.html), [139](https://www.studiodepot.com/31-lee-s139.html), [128](https://www.studiodepot.com/31-lee-s128.html), [101](https://www.studiodepot.com/31-lee-s101.html), [363](https://www.studiodepot.com/31-lee-s363.html). LEE 787, 738 and 795 are not listed at Studio Depot (404).

Other LEE sources:
- **Glazer's Camera:** "LEE Filters 106 Primary Red Lighting Gel Filter Sheet, 21"x 24"", $12.00, SKU 62749 — [Glazer's](https://www.glazerscamera.com/collections/all/products/primary-red-21-x24) (Glazer's is a Seattle retailer; location not verified on the page)
- **Production Advantage:** "Lee Gel 21"x24" Sheets", SKU LEE-GEL-SHT, $11.00 (all colours via an option selector) — [Production Advantage](https://proadv.com/lee-color-gel/). Per-colour stock was not shown in the static page.
- **Adorama:** LEE 172S Lagoon Blue 24×21" listed at $11.00, marked special order (the ship date shown was April 2026, so possibly stale) — [Adorama 172S](https://www.adorama.com/le172s.html) (from search snippet)
- **LEE Direct (official LEE webshop, UK):** 106 Half Sheet £5.25, Full Sheet £10.25, Compact 2ft Roll £72.75, Standard 4ft Roll £138.00. The store currency is GBP, so it ships from the UK and is not the fast option — [LEE Filters Direct 106](https://leefiltersdirect.com/products/106-primary-red)

Rosco Roscolux and CalColor at Stage Lighting Store (stagelightingstore.com), 20"×24" sheets at $11.50 each, all flagged "isinstock: True". Warehouse quantities on 2026-10-17:

| Code | Name | Qty |
|---|---|---|
| R27 | Medium Red | 1 |
| R26 | Light Red | 0 |
| R19 | Fire | 0 |
| R46 | Magenta | 17 |
| R45 | Rose | 7 |
| R48 | Rose Purple | 9 |
| R49 | Medium Purple | 12 |
| R344 | Follies Pink | 13 |
| R339 | Broadway Pink | 0 |
| R68 | Parry Sky Blue | 0 |
| R70 | Nile Blue | 1 |
| R71 | Sea Blue | 0 |
| R72 | Azure Blue | 8 |
| R73 | Peacock Blue | 1 |
| R77 | Green Blue | 0 |
| R80 | Primary Blue | 4 |
| R93 | Blue Green | 13 |
| R95 | Medium Blue Green (listed as "Medium Green") | 34 |
| R370 | Italian Blue | 4 |
| R89 | Moss Green | 0 |
| R90 | Dark Yellow Green | 0 |
| R91 | Primary Green | 13 |
| R389 | Chroma Green | 1 |
| R94 | Kelly Green | 18 |
| R393 | Emerald Green | 2 |
| R10 | Medium Yellow | 0 |
| R12 | Straw | 14 |
| R15 | Deep Straw | 10 |
| R21 | Golden Amber | 8 |
| R312 | Canary | 3 |
| R4390 | CalColor 90 Cyan | 2 |
| R4360 | CalColor 60 Cyan | 16 |
| R4290 | CalColor 90 Blue | 0 |
| R4490 | CalColor 90 Green | 2 |
| R4590 | CalColor 90 Yellow | 5 |
| R4690 | CalColor 90 Red | 4 |
| R4790 | CalColor 90 Magenta | 3 |
| R4760 | CalColor 60 Magenta | 5 |
| R4730 | CalColor 30 Magenta | 1 |
| E106 | Rosco E-Colour 106 Primary Red, 21"×24" | 2 |

- Free ground shipping over $249. Ship origin and transit time to SF were not stated — [Stage Lighting Store R27](https://www.stagelightingstore.com/27-Medium-Red), [R80](https://www.stagelightingstore.com/80-Primary-Blue), [R46](https://www.stagelightingstore.com/46-Magenta), [CalColor 4390](https://www.stagelightingstore.com/4390-CalColor-90-Cyan)
- **Roscolux second sources:**
  - Full Compass lists Roscolux 20"×24" sheets at $11.50 (some list $12.50) — [Full Compass Roscolux #26](https://www.fullcompass.com/prod/229138-rosco-roscolux-26-roscolux-sheet-20-x24-26-light-red) (from search snippet; direct fetch was blocked with 403).
  - Adorama lists R27 at $11.00 but on backorder (expected 06/2026 at time of indexing) — [Adorama RO27](https://www.adorama.com/ro27.html).
  - Markertek sells R27 20×24 — [Markertek RX27](https://www.markertek.com/product/rx27/rosco-r27-gel-sheet-medium-red-20-inch-x-24-inch-sheet).
  - B&H lists Rosco #27 (B&H 43959-REG, MFR 100000272425) — [B&H](https://www.bhphotovideo.com/c/product/43959-REG/Rosco_100000272425_27_Filter_Medium.html). Price and stock were not readable (403).
- **Local, San Francisco Bay Area:**
  - **Holzmueller Productions**, (415) 826-8383; address listed as 1050 25th St, San Francisco 94107. The site advertises "Selling Lighting Equipment & Expendable Supplies" and shows a "Lighting Gels" image. Rentals are by appointment, and orders go by email to rental@holzmueller.com — [Holzmueller](https://www.holzmueller.com/); [YellowPages SF listing](https://www.yellowpages.com/san-francisco-ca/theatrical-stage-lighting-equipment)
  - **Samy's Camera.** A San Francisco location was listed at 1090 Bryant St, San Francisco 94103, (415) 621-7400, in a 2017 rental catalog; current status was not verified. Samy's online listings include Rosco E-Colour 21"×24" sheets at $11.50 — [Samy's 2017 rental catalog PDF](https://www.samys.com/images/pdf/Rental_Catalog_June2017.pdf); [samys.com listing](https://www.samys.com/c/Camera-Accessories/1/null?start=8244)
  - **Other SF and Oakland theatrical firms listed under "Theatrical Equipment & Supplies"**, not confirmed to sell gel: Integrated Controls Inc (2851 21st St SF, 415-647-0480), Bay Area Lighting and Sound Rentals (2302 Market St), Arthur Freyer Lighting (Oakland, 510-835-5800), Cool Neon/Funhouse (Oakland) — [YellowPages SF](https://www.yellowpages.com/san-francisco-ca/theatrical-stage-lighting-equipment)

### Inferences
- **Fastest reliable path to SF:**
  - Order the LEE swatch book and full sheets of the LEE winners (106, 172/183, plus optional 026/029, 139, 795/128, 010/101, 363/119) from Studio Depot. Next-business-day shipping from Burbank should give 1–2 business-day ground delivery to SF (not stated by the retailer).
  - Second LEE source: Production Advantage or Glazer's. Rosco: Stage Lighting Store, with Full Compass as backup.
  - Same-day: call Holzmueller and Samy's SF to ask about LEE 106/172/183 or Roscolux 26/27/80 sheets and swatch books.
- **Rough cost** for a full experiment set: about 8 LEE sheets × $12 + a $28 swatch book ≈ $124 plus shipping and tax.

### Gaps
- Blick Art Materials SF was not checked for Rosco or LEE stock.
- No SF retailer's live gel stock was confirmed. Stage Lighting Store's ship-from location and transit time were not found.
- Full Compass and B&H live prices and stock could not be read (403).
- Studio Depot's "In Stock" may be a generic flag rather than a live count; the page shows the same message for every code.

## Q6. Safety cautions

### Takeaway
Theatrical gels are lighting filters, not eyewear. They carry no ophthalmic, impact or UV-protection rating, so use them only for viewing projected images indoors.

### Cited Findings
- Rosco markets Roscolux for use "in front of hot theatrical and film/TV fixtures" and gives softening and melting temperatures, not eyewear properties — [Rosco Roscolux](https://us.rosco.com/en/product/roscolux)
- LEE's FAQ covers heat and mounting near lamps but gives no eye-safety guidance — [LEE Filters Direct FAQ](https://leefiltersdirect.com/apps/frequently-asked-questions)
- Rosco publishes RoHS and IEC compliance documents for its colour filters. These are lighting-product compliance documents, not eyewear standards — [Rosco Roscolux page (documents list)](https://us.rosco.com/en/product/roscolux)

### Inferences
- **Gels are not tested to ANSI Z80.3 (sunglass) or Z87.1 (impact) eyewear standards.** No sources stating either standard were found. Never use them as sun filters or for eclipse or solar viewing.
- **Dark filters dilate the pupils.** Deep gels (LEE 106 Y≈9–13%, 139 Y≈12%, blues Y≈2–4%) dilate the pupils, while red gels still pass near-IR (106 is at about 81% at 700 nm, per LEE data). Do not use them with bright IR or UV sources.
- **Physical hazards:** cut edges can be sharp, and thin film can catch fire near hot lamps. Keep viewer filters away from projector exhaust.
- **Comfort:** a large luminance imbalance between the eyes (e.g. 106 at Y≈9% vs 172 at Y≈25%) can cause discomfort and rivalry. Consider balancing with a pale neutral or tint layer.

### Gaps
- No manufacturer statement on skin or eye-contact safety, or on chemical safety (dyes, fire retardant), for wearing gels close to the eyes was found.
