# Plan 37A — build plan

Spec: [`37a-nodes-as-pictures.md`](37a-nodes-as-pictures.md), the
authority. Read its "What is there today" map before any task; its
file:line references are to `main` @ f2351a0 and may have drifted.
Decisions D1–D5 are the owner's; build on the recommendations until he
says otherwise, and say in the report which ones you built on.

Branch `plan-37a-build`, cut from `main`. Work in `hyperspace-python/`.
Run tests with `uv run pytest -q …` from there (the fast tier; `--all`
for everything, `--all -m golden` for the goldens). This workstream does
not depend on plan 37B and must not wait for it; if 37B has merged first,
cut from that `main` and keep its face passes as they are.

## Global constraints

- **The rule.** The graph on GRAPH is the whole truth (plan 36). This plan
  adds no node, wire, placement or layout; it only draws what is there
  better. A thumbnail is a read of a node's result, never a write into it.
- **Pictures don't move.** No golden PNG under `tests/golden/` may change,
  and `tests/fixtures/frame-signatures.json` is not re-recorded. T1 proves
  it with every node wanted.
- **Layouts don't move.** No saved node position changes, and a collapsed
  node is never taller than it was (`graphview.height` for a render node
  ≤ `HEAD_H + SUMMARY_LINES × ROW_H`).
- **Cost.** Thumbnails are captured only while the GRAPH page is shown,
  only for nodes on the visible canvas, at most `THUMBS_PER_FRAME` a
  frame. A page that is not GRAPH pays nothing: a test counts the
  captures at zero.
- **Dylan's files.** `apc40.py`, `midi.py`, `bindings.default.json`, the
  desk diagram and `ui_desk*.py` are untouched.
- **Style.** Match the surrounding code: docstrings in the repo's voice,
  comments that cite the plan (`# plan 37A T<n>: …`), no new
  dependencies.
- **Before reporting DONE:** `uv run ruff check` clean on the files you
  touched; the fast tier passing; `uv run pytest -q --all -m golden`
  passing with nothing re-recorded. Report the numbers. The controller
  runs the full suite once before the final review.
- **Commits.** One or more per task, each message ending with the
  attribution lines the session gives you. Never push, merge or rebase.
  Never dispatch subagents.

## Task 1: the thumbnail service (spec P1, D2, D4)

Goal: the renderer can hand the panel a small, current picture of any
picture node by name, for a budgeted cost, and only when asked.

1. `render.Thumbs` (a class in `render.py`, next to the swatches): holds
   `want: set[str]` (set by the panel each frame; cleared when no page
   sets it), `tex: dict[str, moderngl.Texture]` (`THUMB_W = 240`,
   `THUMB_H = 135`, RGBA8), a round-robin cursor, `kept: dict[str, int]`
   for release after `THUMB_KEEP_FRAMES = 120` unwanted frames, and a
   `made(name, src)` entry that blits `src` (a `Texture`, or an
   `Framebuffer` whose colour attachment is read) cover-fitted into the
   name's thumbnail, at most `THUMBS_PER_FRAME = 4` times a frame. One
   FBO per thumbnail, made lazily, on the render context. The blit is the
   existing `_refit` cover path or a two-triangle copy — reuse, don't
   write a third.
2. `Frame.made(node, src)` on `graph.Frame`: forwards to
   `r.thumbs.made(node.name, src)` when `node.name in r.thumbs.want`.
   Each picture node's pass calls it once at its end: scene (its target's
   texture), effect and composite (the framebuffer they painted or the
   texture they made), switch (its picked input, a pointer not a copy),
   delay (the pair's read side), echo and look-back (the trail texture),
   dream (the dreamer's texture or the through picture), resize, media
   channel (the channel's texture), backdrop, pattern (its 1024²
   picture, or the plain faces' pattern pass drawn small — see 4), and
   `Shown` (the output's presented frame via `Preview`). Masks (cover,
   depth) are captured as they are and drawn grey by the panel.
3. `outputs.Preview` becomes one per output: `Preview(k)`, published by
   output k's View the way output 1's is at `app.py:643–650`. The GRAPH
   backdrop keeps using output 1's. The thumbnail of output k is a blit
   of its preview.
4. Geometry nodes (D2 recommended): `Thumbs` draws the shape's edges —
   the existing edges program at the thumbnail's size, white on dark,
   the scene's camera, no faces — as one capture under the same budget.
   Hands and clouds: their points, the same way. If the owner picks "no
   picture", skip this step and the panel draws the kind word.
5. The GPU timer gets one `thumbs` name around all the frame's captures
   (`PassTimer`, one query, never nested inside a node's).
6. Tests (standalone GL, the precedent is `test_ui_shell.py:655`):
   - wanted names get a thumbnail whose mean colour matches a cover-fit
     downsample of the node's result (scene, one effect, a delay, an
     output);
   - with nothing wanted, zero captures and zero timer time;
   - a 40-node want refreshes each name within 10 frames;
   - an unwanted name is released after `THUMB_KEEP_FRAMES`;
   - **the proof**: `tools/golden_frames.py` with every node wanted
     draws every golden byte-identical, and `frame-signatures.json`
     holds.

## Task 2: the node is its picture (spec P2, D1)

Goal: a collapsed picture node on GRAPH is its title and its moving
picture; the words that left go to hover. Nothing moves.

1. `graphview.height`: a render node whose output is a picture or a mask
   is `HEAD_H + THUMB_ROWS × ROW_H + (ROW_H if n.said else 0)` collapsed,
   where `THUMB_ROWS` is the whole number of rows a 16:9 picture at
   `NODE_W` needs (5 at `SCALE` 1.25); assert in a test it is never more
   than `HEAD_H + SUMMARY_LINES × ROW_H`. Expanded, the same picture then
   the port rows.
2. `ui_graph._node`: after the title line, `add_image` of the node's
   thumbnail (`panel.renderer.thumbs.tex.get(n.ref.name)`) at `NODE_W ×
   NODE_W × 9/16`, uv flipped as `_backdrop` does it; at `DORMANT_ALPHA`
   when the node is dormant, off or read nothing this frame; a dark
   rectangle with the kind word when there is no texture yet. Then the
   `said` line if any. The summary's other lines are not drawn.
3. The want list: `ui_graph` sets `renderer.thumbs.want` each frame to
   the picture nodes whose rect intersects the editor's visible rect
   (`ed.get_screen_size` / the canvas rect `_canvas` already computes)
   and that **preset only** does not hide. On any other page the panel
   sets nothing, so the set clears.
4. Hover: `ui.tooltip_image(tex, size, lines)` in `ui.py` beside
   `ui.tooltip` (begin_tooltip, the image at `2 × THUMB_W`, then the
   lines wrapped at `TIP_CH`). `_hover` over a node shows the thumbnail
   big, then `graphview.summary(n)` in full, then the node's GPU time
   from `renderer.stats["gpu_ms"]`. The error / faint-tip / status
   lines stay first when present.
5. Tests (`tests/test_graph_legible.py`, `test_graphview.py`, headless):
   collapsed height rule; the summary lines absent from the node's text
   and present in the hover text; the want set equals the visible
   picture nodes minus the preset-only-hidden ones; the want set is empty
   on the FX page; `tools/control_shots.py` still shoots GRAPH.

## Task 3: the cable palette (spec P3, D3)

Goal: a cable's colour says what it carries; no cable is red.

1. `graphview.PICTURE_HUES`: a table from a source node's kind to a
   palette name (media / scene / effect / trail / dream / depth), and
   `VCable.hue` set at `graphview.build` for picture cables from
   `node_of(c.src_port).kind`; masks, geometry, values and triggers keep
   their type. A bundle's hue is its contents' as today.
2. `ui_graph.COLOURS` gains the six picture hues (amber, white-blue,
   teal, sand, magenta, the mask violet dashed for depth) and loses
   `IMAGE: RED`. `_pin` colours a patched pin by the cable's hue, not
   the port type. `_cable` and `_bundle` read `c.hue`.
3. A `?` chip on the GRAPH head (next to **preset only**) toggles a
   legend box in the canvas's corner: one line per hue in words. Off by
   default, remembered in the show like the other chips.
4. Tests: no drawn cable's colour equals `ui.RED` on any factory preset;
   a channel's cable and the scene's cable differ; the legend lists every
   hue in `COLOURS`; `test_graph_legible`'s alpha/thickness captures
   still hold.

## Task 4: legibility from the display (spec P4, D5)

Goal: GRAPH opens at a size that reads from the chair on whichever Mac,
and a user's zoom is kept.

1. Launch zoom: `ui_graph` reads the control window's content scale and
   height once per size change (`glfw.get_window_content_scale`, the
   panel's window; `app.py` already tracks the window size for the 4:3
   panes) and sets the editor's zoom to `clamp(scale × height / 900,
   1.0, 2.0)` **unless the show holds a zoom for this window**. A user
   zoom (wheel, ⌘-scroll, pinch) is written to the show beside #246's
   pan (`panned`), per window.
2. `PIN = 14`; the pin's hit rect is the row's height; the stubs the
   same. Check `pin_xy` consumers (cable ends, hover) still land.
3. `[ui] font` in `config.toml`: `auto` (default) or a pixel size;
   `auto` is `ui.FONT_BASE` scaled by the content scale the way imgui's
   DPI handling expects (no double scaling on a Retina window: check
   what `app.py` sets today). The canvas font follows `ui.FONT_BASE`.
   Document the key in `SETUP.md`.
4. Tests: the zoom formula at three sizes; a show with a zoom wins over
   the formula; `PIN` and the hit rect in `test_graph_legible`; the
   config key parsed and defaulted.

## Task 5: docs

- This spec's "What changed in the build" (as plan 36's), with any
  ruling the controller made and a register row for each (the next free
  rows in `DECISION-REGISTER.md`, after whatever plan 37B took if it
  landed first).
- `ARCHITECTURE.md`: `Thumbs`, `Frame.made`, the palette, the launch
  zoom; `ENGINEERING.md`'s GRAPH section; `plans/README.md`'s entry.
- Hand checks: the spec's six, written into `11-hand-checks.md` as the
  next group after the last one in the file.
- Test counts in the spec header.
