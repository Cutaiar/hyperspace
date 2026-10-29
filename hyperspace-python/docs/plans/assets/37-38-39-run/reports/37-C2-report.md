# 37-C2 report: hover gives details; the "pictures · tint cables" switch

**Status:** DONE_WITH_CONCERNS (the concerns are about judging it by eye and at the machine; nothing is failing)
**PR:** https://github.com/Cutaiar/hyperspace/pull/258 (`plan-37-c2-hover` → `plan-37-pictures`)
**Base:** 761aef3. I used `git merge --ff-only FETCH_HEAD` from a clean tree, as the dispatch allows, then renamed the branch to `plan-37-c2-hover`.

## Commits
- 68335cf Plan 37 C2: PreviewTextures reads a thumbnail's dominant hue, one a frame, each once a second, only while asked
- e1a05e4 Plan 37 C2: hovering a thumbnail gives the summary, the size and the GPU time; the pictures · tint cables switch, off by default

## What was built
- **Hover:** `graphview.picture_hover(n, gpu_ms)` builds the text: the title, the `summary` lines, `W×H picture` (from `VNode.picture`) and `gpu N.NN ms`. `ui_graph.thumb_tip` adds the GPU time from `renderer.stats["gpu_ms"][thumb_name(n)]` and the status. `_thumb` records `st["thumb_hover"]` while the pointer is on the picture box, and `_hover` shows the tip in that case. Hovering the title behaves as before. `_want_thumbs` now gives output 1's node its `Preview` size.
- **Switch:** `_tint_chip(st)` is one call in `_head`, after the details chip, so it is last among today's chips. It is lit-chip `pictures · tint cables`, `st["tint"]` defaults to False, and the state is page-only. While it is lit, `_canvas` calls `thumbs.want_hues()` and computes `st["tints"] = cable_tints(st, view)` after `_wiring`. `_cable` uses the tinted colour for a picture cable whose maker has a hue. `COLOURS` is unchanged.
- **Tint:** `tint(hue, strength)` is a pure function. It leans red's hue toward the picture's hue along the shorter way round, compressing the whole circle onto ±20° and scaling by `strength / 0.25` (capped at 1). Saturation and value stay red's.
- **Hue read:** `outputs.dominant_hue` is a pure-Python, chroma-weighted circular mean over a 16×16 strided sample. `PreviewTextures._read_hue` runs from `begin_frame`, before the frame's copies, so it reads last frame's thumbnail. While the page asks, it reads at most one thumbnail a frame, and each one at most once a second. A read is one `tex.read()` of about 80 KB. With the switch off it costs nothing.

## Tests (`tests/test_graph_hover.py`, 11)
- The hover text contains the summary lines, the size and the time, and leaves out the size and time when there is none.
- The GPU time is looked up by the render node's name.
- The hover says a switch's pick and "reaches nothing".
- The chip is off by default and is the last `##graph` chip, after "output behind".
- The preset and show files are identical with the switch on and off.
- With the switch on, a picture cable takes `tint(hue)`; with it off, it is plain red again; `COLOURS` is untouched.
- The tint stays within ±20° of red for every hue, red stays the leading channel, it stays clear of amber and purple, and strength 0 gives exact red.
- `dominant_hue` on solid green and blue, on grey, on empty input, and on half-red/half-grey.
- The read schedule: one read a frame, each node once a second, nothing when not asked, and a dropped node forgets its hue.
- A real GL thumbnail's hue (standalone context).
- A headless draw with the switch lit and a thumbnail hovered gives the hover text as the tooltip.

## Gates
- `uv run pytest -q`: `4035 passed, 2 skipped in 53.42s`
- `uv run ruff check .`: `Found 25 errors.` These are the 25 already on the base, which C1 listed; the touched files show `All checks passed!`
- `uv run pytest -q --all tests/test_golden_frames.py`: `128 passed in 12.61s`; no golden file changed
- `uv run pytest -q --all`: `4248 passed, 2 skipped in 85.66s`

## Files changed
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a122bdecd675f250d/hyperspace-python/hyperspace/outputs.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a122bdecd675f250d/hyperspace-python/hyperspace/graphview.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a122bdecd675f250d/hyperspace-python/hyperspace/ui_graph.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a122bdecd675f250d/hyperspace-python/tests/test_graph_hover.py (new)

The head file is plan 38's. I touched it in the smallest way the ownership table allows: one `_tint_chip(st)` call in `_head`, placed last. Nothing changed in `graph.py`, `app.py`, `render.py`, `hold.py` or `patterns.*`.

## Self-review
- The tint uses ImVec4. `_cable` checks `is None` explicitly rather than relying on `or` with ImVec4's truthiness.
- `st["tints"]` is computed after `_wiring`, so the through wires of the current frame are included.
- The hue readback is a sync on a texture written the previous frame. It is cheap in theory but has not been measured on the show Mac.
- The headless hover test drives `thumb_hover` through a stand-in, because `imgui.is_item_hovered` inside the node editor cannot be pointed at headless.

## Concerns
1. Whether the hover shows up inside `imgui_node_editor` at the machine (`is_item_hovered` on a dummy inside a node) is not proven headless. The + button's tooltip uses the same pattern.
2. The ±20° lean is a guess at "red stays recognisable" and may read as too subtle. It is two constants.
3. Commits use the attribution lines from common.md (Claude Fable 5.1).

Decisions: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/37-C2.md

---

## Fix report (review round 1): commit a233deb, pushed to PR #258

1. **IMPORTANT, fixed. The hue read is now asynchronous.** `PreviewTextures._read_hue` no longer calls `tex.read()`. `_hue_start` runs C1's `THUMB_FS` pass (split out as `_pass`) from the chosen thumbnail into a 16×16 target and calls `fbo.read_into(buffer)`, a 1 KB PBO copy with no wait. Next frame, `_hue_collect` reads that buffer and weighs it. The schedule is the same as before: one node a frame, each once a second. The 16×16 target and buffer are made once and released in `close`. Tests: the schedule test uses fake textures whose `read()` counts and stays at 0, and the hue arrives one `begin_frame` later. The real-GL test patches `moderngl.Texture.read` with a counter, which stays empty; the hue is None after the first frame and present after the second. I rewrote row 4xh's cost text and added the AH.1 line "SYSTEM fps unchanged with the switch lit on a 20-node preset".
2. **Minor 1: a continuous mapping.** The lean is now `TINT_SPAN × sin(2π(hue − red))`. The yellow-green half leans orange, the blue-violet half leans rose, and red and cyan give no lean, so there is no flip at cyan. I updated `TINT_TIP`, the row and the test: the lean is at most ±20°, ±span at a quarter round, 0 at cyan, and adjacent steps of half a degree differ by less than 0.2°.
3. **Minor 2:** AH.4 now names the fallback: test the dummy's rect against `imgui.get_mouse_pos()` taken to canvas space.
4. **Minor 3:** the page calls `thumbs.stop_hues()` on any frame the switch is off, so no hue starts after that. A hue already in flight is still collected (tested). I updated row 4xi.

Gates:
- `uv run pytest -q`: 4035 passed, 2 skipped
- `uv run ruff check .`: Found 25 errors, the same ones that are already on the base; the touched files pass
- `uv run pytest -q --all tests/test_golden_frames.py`: 128 passed
- `uv run pytest -q tests/test_thumbnails.py tests/test_graph_hover.py`: 26 passed
