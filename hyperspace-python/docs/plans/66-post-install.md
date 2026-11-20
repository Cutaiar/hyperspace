# Plan 66: the post-install wave

Written 2026-11-20 from the install debrief, the Claude Doc "Install debrief — November 2026". It collects every open item in that doc except the shader roundup and consolidation, which have their own track. Each item is one cloud agent, one draft PR to `main`.

## 1. The items

| Plan | Item | Wave | Owns (files it may change) | Rows | Checks | Group |
| --- | --- | --- | --- | --- | --- | --- |
| 67 | **Mandelbrot fixes**: input-less render, coloured interior under perturbation, off-screen term sensitivity, perturbation and skip cost | 1 | `mandel.py`, `shaders/fx/mandel.glsl`, `tools/mandel_*`, `tests/test_mandel.py` | 902–909 | 699–706 | EB |
| 68 | **An endless, centred fractal dive** | 1 | `fractal.py`, `view.py` (`reroot`), `tests/test_fractal*.py` | 910–917 | 707–712 | EC |
| 69 | **Control widgets**: tick marks, unipolar/bipolar drawing, XY pads and XYZ volumes | 1 | `ui_fields.py`, the fader drawing in `ui.py`, `fx.py` (directive parse), `@pair` lines in four effect files | 918–927 | 713–722 | ED |
| 70 | **Save and load live**: Save as on the meta controller, a scrolling playlist | 1 | `deck.py`, `ui_loadable.py`, `ui_playlist.py`, `playlist.py` | 928–933 | 723–728 | EE |
| 71 | **GRAPH: GPU cost at a glance** | 1 | `ui_graph.py` (a toggle and node tint), the pass timer's read side in `render.py` | 934–939 | 729–734 | EF |
| 72 | **Hands default: BONES, PLAIN, 50%** (update PR #459) | 1 | `ghost.py`, `app.py`'s show-look call, a library tool | 940–943 | 735–737 | EG |
| 73 | **Loader and node-mode fixes**: a note for a missing `units` marker; node mode and dropdowns | 1 | `loadable.py` (the units read), `nodemode.py` | 944–949 | 738–741 | EH |
| 74 | **Audio reactivity that survives a load** | 2 | the meta controller's routes (`routing.py` layer, `deck.py` where 70 left it), its panel | 950–957 | 742–749 | EI |
| 75 | **Install mode**: plays on its own when nobody touches anything | 2 | a new `install_mode.py`, `config.py` keys, a read of `idle_lights.IdleLights.touched` | 958–965 | 750–757 | EJ |
| 76 | **The VIEW page, reviewed and fixed** (§5) | 2 | `ui_view.py`, `Panel._view_stock` and `_view_hero` in `ui.py`, VIEW params' labels and tips in `params.py`, the media-path rows on `ui_media.py` | 966–975 | 758–765 | EK |

Wave 1 runs at once: no two items own the same file. Wave 2 waits for the owner's decisions below and for 70 to merge, since 74 and 75 touch the meta controller and the playlist after it. 76 waits for 69 to merge, because both draw VIEW's controls.

## 2. Decisions the owner makes before dispatch

| # | For | Question | Recommendation |
| --- | --- | --- | --- |
| D1 | 74 | Where does audio reactivity live? | **A:** band-to-fader routes on the meta controller, laid over whatever patch loads, with one toggle and a depth knob; a patch can opt out with a flag |
| D2 | 75 | What plays when nobody is touching anything, and after how long? | A named playlist from `config.toml` (`[install] playlist`), after 300 s with no desk, pad or hand input. Any touch returns to the patch that was loaded, at the point it was left |
| D3 | 69 | Which X/Y pairs become pads now? | Prism, Wave and Zoom burst `cx`/`cy`, and Wave Table `offset_x`/`offset_y`, declared with a `@pair` line and **no param renamed** (the roundup may rename later). Zoom burst's centre plus amount as the first XYZ volume |
| D4 | 68 | The fractal dive drifts toward an edge. By design? | No: zoom about the screen centre, so the point under it stays put through every re-root |
| D5 | 76 | VIEW's new layout | One page in three sections, Shape, Spin and Copies (§5), with the rarely used controls in a fold under each |
| D6 | 76 | The four media-path params drawn nowhere | Draw them on MEDIA beside Media alpha |
| D7 | 76 | Rename the `view.*` ids that belong to faces and media? | No: labels, tips and grouping only. A rename is a format change for 158 patches |

Wave 1 needs only D3 and D4, and both recommendations are written into the prompts. Change them there if you decide otherwise.

## 3. Not for cloud agents (on the rig, by the owner or a local session)

- **Rugged Doctor at the 60 FPS floor.** Time its passes with the GPU timer on the rig. The roundup found the Blocks shader cheap, so the cost is elsewhere.
- **The benches:** `tools/mandel_bench.py` and `tools/fractal_bench.py`, and again after 67 lands.
- **Re-set the library's hands look** with 72's tool, once 72 merges.
- **Look at sorted vs. additive** (`docs/plans/assets/64-recursive-geometry/`).
- **The hand checks** for groups DY, DZ, EA and every group below.
- **Out of scope:** Dillon's interface redesign; the APC40 idle effects (#465, open); the shader roundup, face shaders and preview showcase values; Invisible City.

## 5. The VIEW review (2026-11-20)

VIEW (`ui_view.page` on dkit, `Panel._view_stock` without it) has collected controls one plan at a time, and nobody has rethought it as a page. What it holds, and how the 158 patches in the Drive library use each control:

| Control | Patches not at the default | Notes |
| --- | --- | --- |
| Shape menu (`view.shape`) | 141 | The most-used control on the page, drawn by the panel's own combo |
| Brightness, Speed, 4D depth | 151, 115, 86 | No tips |
| Six plane toggles (`view.plane.*`) | 2–82 each | Spin is split three ways: the plane toggles and Speed here, a Rotate switch, and each plane's rate under a separate ROTATION strip |
| Rotate (`view.rotate`) | 13 | Overlaps the plane toggles: a pause for every plane at once |
| Points, Lines, Faces switches | 104, 37, 127 | Faces is also on FACES |
| 3D hold (`view.three_d`) | **0** | |
| Points and lines opacity | 2, 3 | |
| Screen strokes | 5 | |
| Fractal line order (`view.frac_additive`) | not saved | Labelled only "Additive" |
| The copies: count, Fit, layout, motion, amp, rate, spacing, depth | 83 use copies | A self-contained group of eight; Fit is set in only 8 |
| Six rates (`rot.rate.*`) | 135 carry them, 120 route them | The heaviest-routed controls on the page, under their own strip |

**Under `view.*` but not on VIEW:**
- **Faces:** `view.pattern`, `pattern_mix` and `cut_through` are drawn on FACES.
- **Media:** `view.media_alpha` is on MEDIA. `view.media_scale`, `media_mode`, `media_amp` and `media_rate` (the faces' media path) are **drawn nowhere**, though 20 patches set two of them.
- **The legacy alias:** `view.bmp_alpha`, an alias of media alpha, is still the default APC40 layer's knob 7 (`apc40.py:547`), and so in 104 patches' desk layers. It works; leave it.

**What 76 builds** (D5–D7 as recommended):

1. **One page, three sections:**
   - **Shape:** the menu, Brightness, 4D depth, Points, Lines and Faces.
   - **Spin:** Speed, the Rotate pause, and **each plane as one row**: its toggle beside its rate. This replaces the separate ROTATION strip.
   - **Copies:** the eight instance controls.
2. **A fold in each section, closed by default,** for the rarely used: 3D hold, both opacities, screen strokes, Fit and the fractal line order. Nothing is deleted.
3. **Labels and tips** for every VIEW control that has none: Brightness, Speed, 4D depth, Points, Lines, Rotate, the copies' amp and rate. "Additive" becomes "Fractal lines: additive".
4. **The media path's four controls drawn on MEDIA,** beside Media alpha.
5. **No id renamed or re-keyed** (D7). The cell-count head stays: it is the panel's identity.

## 6. The builder brief (every item)

You build one item as one draft PR to `main`. The owner reviews and merges; you never merge.

**Read first:** `REVIEW.md` (repo root), `hyperspace-python/docs/CHECKPOINT.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` §3–§4, `docs/GLOSSARY.md` (use its words), `docs/ENGINEERING.md` §15 (hot reload) and §16 (testing). For pictures and driving the panel: `.claude/skills/drive-the-app/SKILL.md`.

**Rules:**
- **Two layers.** The meta controller holds everything set for a performance; a loadable patch is a complete look, and no patch may affect another.
- **The graph is WYSIWYG:** no default graph, no hidden edges, no auto layout.
- **Change only the files your row owns.** Needing another one: say so in the PR and keep the change minimal.
- **Goldens must not move**, except where your prompt says. `tests/fixtures/` needs `git add -f`.
- **Files on disk are a format** (REVIEW.md). New keys follow the no-old-schema rule: saves write the newest schema, both Macs update together. A rename or removal of a saved id: stop and report.
- Never run anything against `~/Hyperspace` or a Google Drive path. A tool meant for the owner's library goes in the PR body as a command.
- Don't modify `.github/workflows/`.
- The panel must stay legible at a distance: big targets, little text, no all caps.
- Report faithfully: failures with their output, a skipped step as skipped.

**Your numbers** are your row of the table in §1. Use only those: register rows in `docs/DECISION-REGISTER.md` (a table row plus a `### <n>.` section each), hand checks in `docs/plans/11-hand-checks.md` under your group, and a plan doc `docs/plans/<plan>-<slug>.md` with a line in `docs/plans/README.md`. Where the owner hasn't answered something, build the recommendation and mark the row "(rec) — pending the owner".

**Testing:** cloud setup is `.claude/hooks/session-start.sh`, or drive-the-app §0. Run `uv run pytest -q` from `hyperspace-python/`; it must be green. Cloud machines render in software, so frame times there mean nothing: anything about speed gets a tool the owner runs on the rig, with the command in the PR body.

**PR:** branch `plan-<n>-<slug>` from `origin/main`, opened as a draft with `gh pr create --draft`. Body headings:
- **Why**
- **What**
- **Testing** (counts verbatim)
- **On the rig** (if any)
- **Restart or hot reload**
- **Owner decisions pending** (each with your recommendation)

When you finish, reply with: the PR URL, the head commit, what's done and not, test counts, the rows and checks used, and the open questions.
