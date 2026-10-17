# Hyperspace custom-colour anaglyph: engineering handoff files

These are the supporting engineering files for the anaglyph research package for the Hyperspace projection-cart installation. Everything here was generated on 2026-10-17 from the notes in `research_notes/Custom anaglyph 3D projection plan/`. No new research was done to produce them.

**Data rule.** Every number traces to those notes, or is computed from them with the method stated. Values that have not been measured are `null` and marked **PLACEHOLDER**. Nothing in this folder has been measured on the Hyperspace projector.

## Decisions these files implement

1. **Test order.**
   1. **Red/cyan baseline.** Premade: Rainbow Symphony paper 03201 and ProView plastic 03401. DIY gels: LEE 106 Primary Red with LEE 172 Lagoon Blue, 183 Moonlight Blue or 115 Peacock Blue.
   2. **Magenta/green.** Premade: Rainbow Symphony ProView 03410, GEMS and the 03412 clip-on; American Paper Optics TrioScopics paper; 3Dstereo TriOviz. Note that TriOviz is not TrioScopics. DIY gels: LEE 795 Magical Magenta or 128 Bright Pink with LEE 139 Primary Green or 124 Dark Green.
   3. **Amber/blue, DIY gels only.** LEE 010 Medium Yellow or 101 Yellow with LEE 363 Special Medium Blue or 119 Dark Blue. There is no verified premade US source.
   4. **Pale pinks leak green.** LEE 035, 036 and 002 are shown in plot C4 for this reason.
2. **Algorithm.** Use a pair of 3×3 matrices, `M_left` and `M_right`, applied in linear light. The two terms are summed and clipped, then re-encoded. Dubois 2009 clips each term before summing. The presets come in this order:
   1. Pure channel mask.
   2. Dubois presets: red-cyan 2009, and green-magenta and amber-blue 2010 "LCD".
   3. Matrices recomputed from measured spectra with Dubois least squares.
3. **Calibration.**
   - **Path A:** through-filter visual tests, a Weissman-style crosstalk chart, and phone RAW captures at locked exposure. Path A gives relative comparisons only.
   - **Path B:** rent a Sekonic C-800 from Lensrentals. Use it to measure the projector SPD, and filter transmission on a halogen source, then apply the Woods & Rourke integration.
   - **Crosstalk formula:** `(ghost − black) / (white − black)`.
4. **Hyperspace context.** These facts were observed in `rendering_algorithms.md` Q9:
   - The active app is `hyperspace-python`, built on moderngl with OpenGL 3.3 core, GLFW and imgui-bundle.
   - Projection is mono and runs on the CPU, in `geometry.project_h()` at `geometry.py:1009`.
   - There is no stereo or colour-space code yet. All anaglyph rendering blocks in the diagrams are **proposed**, not built.

## File list

### `diagrams/`: Mermaid sources, rendered to SVG and PNG with `@mermaid-js/mermaid-cli`

| File | Purpose | Provenance |
|---|---|---|
| `A_system_architecture.mmd` / `.svg` / `.png` | Existing hyperspace-python modules (app, `project_h`, `render.py`, `outputs.py`), the proposed anaglyph blocks (profile, per-eye offset, eye passes, compositor), the physical chain (projector, screen, filters, eyes) and the calibration loop | rendering_algorithms.md Q4, Q5, Q9; calibration_equipment.md |
| `B_optical_separation.mmd` / … | **Conceptual** red/cyan separation: which primaries reach which eye, and where the leaks are | rendering_algorithms.md Q1, Q4; color_pairs.md §1 |
| `C_spectral_plots_map.mmd` / … | Data flow for Diagram C: `gel_spectra.csv` → `make_plots.py` → C1–C5 plus `band_summary.csv`. The plots themselves are in `plots/` | this folder |
| `D_rendering_pipeline.mmd` / … | Stage-by-stage inputs and outputs, from 4D state through the per-eye CPU projection, eye passes and compositor (decode, gains, `u_ML`/`u_MR`, clip, optional cancellation, encode) to the outputs. Shows where matrices, masks, gains and `k` are applied | rendering_algorithms.md Q2, Q4, Q5, Q9 |
| `E_prototyping_process.mmd` / … | The 10 prototyping steps in the decided test order, with Path A and Path B | all notes; the decided recommendations |
| `F_calibration_decision_tree.mmd` / … | Seven symptoms: excessive ghosting, one eye darker, lack of depth, reversed depth, distorted colours, monitor and projector disagreeing, and variation between viewers. For each: likely causes, the diagnostic, and the next adjustment | rendering_algorithms.md, color_pairs.md, calibration_equipment.md, theatrical_gels.md |

All six sources rendered without errors in mermaid-cli, to both SVG and PNG. The brief asked for six sources but named five (A, B, D, E, F). `C_spectral_plots_map.mmd` is the sixth; it documents Diagram C, which is a set of matplotlib plots.

### `plots/`: Diagram C, spectral transmission plots

| File | Purpose |
|---|---|
| `make_plots.py` | Script that regenerates everything below. Run it with a venv that has matplotlib and numpy |
| `C1_red_cyan.svg/.png` | LEE 106 (left) against 172, 183 and 115 (right) |
| `C2_magenta_green.svg/.png` | LEE 139 and 124 (left, green) against 795 and 128 (right, magenta) |
| `C3_amber_blue.svg/.png` | LEE 010 and 101 (left, amber) against 363 and 119 (right, blue). DIY only |
| `C4_pale_pink_leakage.svg/.png` | LEE 035, 036 and 002 against 139: the pale pinks transmit the green band |
| `C5_crosstalk_conceptual.svg/.png` | **Conceptual** illustration of signal area against ghost area. It uses synthetic curves, not data |
| `band_summary.csv` | Mean %T of each plotted gel in the three illustrative bands, computed from the CSV |

How to read the plots:

- Every pair plot uses the same axes: 400–700 nm, with %T shown linear (top) and log (bottom).
- The shaded bands are **illustrative band markers only**: blue 445–465, green 530–560 and red 610–640 nm. They are the B455/G545/R625 proxies used in theatrical_gels.md, not measured projector primaries.
- The footer of every plot gives the data source: URL pattern `https://leefilters.com/colour/<code>-<name>/`, *"manufacturer-published (LEE Filters website), not measured by us"*. LEE's floor value is 0.01 %.
- Each line has a unique colour, line style and legend entry. The colours were checked with the dataviz palette validator across all pairs in light mode.

**Data source.** All curves come from `research_notes/Custom anaglyph 3D projection plan/gel_spectra.csv`, which has 5 nm steps and was scraped from LEE colour pages on 2026-10-17. The band means match the key-band table in theatrical_gels.md Q2; for example, LEE 106 gives 0.14 / 0.03 / 57.16.

**band_summary.csv values** (mean %T, arithmetic mean of the 5 nm samples, band edges inclusive):

| LEE gel | Role | Blue 445–465 | Green 530–560 | Red 610–640 |
|---|---|---|---|---|
| 106 Primary Red | left (red) | 0.143 | 0.032 | 57.156 |
| 172 Lagoon Blue | right (cyan) | 58.956 | 24.500 | 0.118 |
| 183 Moonlight Blue | right (cyan) | 69.136 | 21.647 | 0.149 |
| 115 Peacock Blue | right (cyan) | 61.458 | 49.927 | 1.049 |
| 139 Primary Green | left (green) | 0.029 | 23.647 | 0.017 |
| 124 Dark Green | left (green) | 4.344 | 44.940 | 0.512 |
| 795 Magical Magenta | right (magenta) | 47.529 | 0.493 | 62.381 |
| 128 Bright Pink | right (magenta) | 35.284 | 0.538 | 75.766 |
| 010 Medium Yellow | left (amber) | 0.049 | 88.724 | 89.903 |
| 101 Yellow | left (amber) | 0.089 | 81.658 | 88.153 |
| 363 Special Medium Blue | right (blue) | 44.881 | 0.975 | 0.049 |
| 119 Dark Blue | right (blue) | 45.745 | 1.101 | 0.011 |
| 035 Light Pink | pale pink | 67.094 | **48.575** | 88.395 |
| 036 Medium Pink | pale pink | 51.987 | **27.378** | 85.137 |
| 002 Rose Pink | pale pink | 67.148 | **10.089** | 86.551 |

### `config/`

| File | Purpose |
|---|---|
| `anaglyph_profile.schema.json` | JSON Schema (Draft 2020-12). `kind: anaglyph_profile` selects a filter-pair profile and `kind: anaglyph_experiment` selects an experiment run that embeds a profile (see below) |
| `profiles/red_cyan_channel_mask.yaml` | First preset. Identity-row channel mask (Wimmer "Color" anaglyph). Filters: RS ProView 03401; alternates RS 03201 and LEE 106/172/183/115. Overall status PLACEHOLDER (not calibrated) |
| `profiles/red_cyan_dubois_2009.yaml` | Dubois March 2009 red/cyan matrices, **copied exactly** from rendering_algorithms.md Q3, with citation (Dubois 2009 PDF). Labelled "red/cyan glasses and CRT/plasma display". Status placeholder for this projector and these gels |
| `profiles/magenta_green_lee795_lee139.yaml` | **Candidate** custom pair: LEE 139 (left, green) and LEE 795 (right, magenta). Matrices are the Dubois green-magenta 2010 "LCD + TrioScopics3D" preset, used as a **PLACEHOLDER starting point that is not calibrated for these gels**. The channel-mask fallback is given in the header comment |
| `experiment_example.yaml` | EXAMPLE experiment config (red/cyan baseline). Every observation is null. Its geometry uses the notes' worked-example assumption (V = 4 m, 4 m / 1920 px screen, divergence limit ≈ 63 mm ≈ 30 px), **not** the real cart |
| `validate_configs.py` | Validates the YAML against the schema, recomputes matrix row sums, and runs 6 negative self-tests |
| `compute_dubois_matrix.py` | numpy reference implementation of Dubois least squares from spectra; see below |

**What a profile contains:**

- name, version, overall status, and provenance with citations;
- left and right filter designations, with product codes, suppliers (SKU, URL, price, verified date) and material;
- a transmission data reference with `data_type` set to `measured`, `published` or `unknown`;
- `matrices`: `M_left` and `M_right` as 3×3 row-major output rows, `input_color_space`, `output_color_space`, `math_domain` (`linear` or `encoded`), decode and encode transfer, `clip_mode`, status, source and `row_sum_check`;
- `eye_gains`;
- `crosstalk_compensation` (k coefficients and black floor);
- `stereo`:
  - interaxial and zero-parallax distance, each with units;
  - maximum positive and negative parallax, each as a fraction of screen width, in mm and in px;
  - `off_axis`, viewer distance, interocular distance and eye assignment;
- `display`: projector and screen assumptions;
- `calibration`: date, method, operator, instrument, formula, measured crosstalk per eye, and status (`placeholder` or `measured`). If status is `measured`, the schema requires numeric crosstalk values and a date.

**GLSL note.** Matrices are row-major output rows. GLSL `mat3` is column-major, so upload the transpose.

**`compute_dubois_matrix.py`:**

- **What it implements.** It computes `C`, `A_l` and `A_r` by trapezoid integration, then `P = N (RᵀWR)⁻¹ RᵀW C₂`, and splits the result into `M_L` and `M_R`. It also provides the sRGB EOTF and OETF and `apply_anaglyph()` (decode → gains → matrices → clip per term or after the sum → encode). It provides an example Y-weighted W, and a CLI that reads CSVs, including `gel_spectra.csv` with `--percent`.
- **CIE CMFs are not bundled.** Download the CIE 1931 2° XYZ CMFs, for example from cvrl.org, and pass them in.
- **Tests** (synthetic data only), run with `python compute_dubois_matrix.py --test`:
  1. The notes' row-sum test on all four published Dubois presets.
  2. The row-sum test on matrices recomputed from synthetic spectra, with W = I and with Y-weighting.
  3. A test that ideal non-overlapping spectra reduce exactly to the channel mask.
  4. A test that channel-mask profiles reproduce pure channels through the full decode/encode path. It covers red/cyan, green/magenta and amber/blue, and also checks the shipped YAML.
  5. An sRGB round trip and a check of both clip modes.

### `templates/`

| File | Purpose |
|---|---|
| `experiment_log.csv` | Log header with the 20 required columns and one row marked **EXAMPLE** |
| `test_patterns.md` | Exact specification of TP1–TP9 on a 1920 × 1080 reference raster: full-field leakage (L-only / R-only / black, per primary, 32-level ramp); ghost-edge bars plus an SCT-style chart; black / white / black plus adjacent red \| cyan; colour patches; disparity ladder; depth-reversal check; text at disparities; random-dot stereogram; registration. Each value is tagged [notes], [spec] or [derived]. The SCT chart's linear percentages (0.5–20 %) map to sRGB codes 16, 25, 39, 48, 63, 80, 97 and 124 |

## Validation results (2026-10-17)

| Check | Command | Result |
|---|---|---|
| Schema is valid Draft 2020-12 | `python config/validate_configs.py` | PASS |
| `red_cyan_channel_mask.yaml` | ″ | PASS; row sums [1, 1, 1] |
| `red_cyan_dubois_2009.yaml` | ″ | PASS; row sums [1.000, 0.999, 1.000] |
| `magenta_green_lee795_lee139.yaml` | ″ | PASS; row sums [0.999, 0.999, 1.000] |
| `experiment_example.yaml` | ″ | PASS |
| Negative tests (malformed matrix, bad `data_type`, "measured" without numbers, wrong eye, missing `off_axis`, bad `math_domain`) | ″ | 6/6 rejected as expected |
| Dubois implementation tests | `python config/compute_dubois_matrix.py --test` | 5/5 PASS |
| Mermaid syntax | `mmdc -i diagrams/X.mmd -o X.svg` and `-o X.png` | 6/6 rendered to SVG and PNG without error |

Environment used: Python 3.13 venv with matplotlib 3.11.2, numpy 2.5.4, PyYAML and jsonschema 4.26.0; Node 22 with @mermaid-js/mermaid-cli.

## Regenerating

```bash
python -m venv venv && venv/bin/pip install matplotlib numpy pyyaml jsonschema
venv/bin/python plots/make_plots.py                 # plots + band_summary.csv
venv/bin/python config/validate_configs.py          # schema validation
venv/bin/python config/compute_dubois_matrix.py --test
npx -y @mermaid-js/mermaid-cli -i diagrams/A_system_architecture.mmd -o diagrams/A_system_architecture.svg
```

## Known limits

- **Untested against hardware.** No projector, gel or glasses has been measured. All matrices, gains and stereo limits are presets or placeholders until Path A or Path B data exist.
- **Display and glasses mismatch.** The Dubois presets were fitted to CRT/plasma (2009) or LCD (2010) primaries and to commercial glasses, not to a projector or to LEE gels. Dubois does not say whether the 2010 matrices expect linear or sRGB input. Linear is used here, following the decided pipeline.
- **No vendor spectra for premade glasses.** No vendor publishes transmission data, so every premade lens is `data_type: unknown`.
- **Unverified stereo-injection maths.** The per-eye CPU projection formula and the z1 = 0 zero-parallax plane are inferences in the notes. Verify them against `tests/test_core.py` before relying on them.
