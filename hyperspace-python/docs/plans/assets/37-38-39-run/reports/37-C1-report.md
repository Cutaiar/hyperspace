# 37-C1 report — thumbnails: nodes are pictures

**Status:** DONE_WITH_CONCERNS (concerns below are visual/hand-check items and one spec deviation, nothing failing)
**PR:** https://github.com/Cutaiar/hyperspace/pull/255 (`plan-37-c1-thumbnails` → `plan-37-pictures`)
**Base:** cb78963. The brief's `git reset --hard FETCH_HEAD` was refused by the harness's permission classifier; the worktree was clean and the base a descendant, so `git merge --ff-only FETCH_HEAD` brought HEAD to cb78963, same result. Branch renamed to `plan-37-c1-thumbnails`.

## Commits
- 4d684e7 Plan 37 C1: PreviewTextures, a small texture per wanted node, made at the frame's end
- e47c50d Plan 37 C1: GRAPH draws every picture node as its picture; SYSTEM says the copies

## What was built
- `hyperspace/outputs.py`: `THUMB_PX = 192`, `THUMB_DROP_S = 1.0`, `THUMB_BLACK_S = 1.0`, `THUMB_FS` (a 16-tap bilinear downsample pass, opaque output), `thumb_size`, `PreviewTextures` (want/take/begin_frame/put/end_frame/shade/get/size_of/count/kept/drop/close). Imports: `time` (stdlib) added; still moderngl + glsl only from the package (the boundary test passes).
- `hyperspace/render.py`: `thumb_source(frame, name, how, pulled)` resolves the four hows (picture via `graph.picture`; scene; layer; window via `Handoff.frame` or a publish-only target). `Renderer.thumbs` (made in `__init__`, closed + None on `on_reload`, made again lazily), `_thumb_frame` held from `_draw_frame` (after a successful `evaluate`) to `_for_the_panel`, `_thumbnails()` called last in `_for_the_panel`: takes the wish, mutes `PassTimer` (`_active`), asks each wanted node, restores the frame's `stats` dict in place, drops unwanted names. Never raises.
- `hyperspace/graphview.py`: `THUMBS` (the one table), `thumb_of`, `THUMB_FAINT`, `THUMB_H = 134`, the four how words; `VNode.thumb` (set in `build`), `VNode.picture` (the size hook for C2); `height` counts the box collapsed (title + box, no lines) and expanded (title + box + ports).
- `hyperspace/ui_graph.py`: `FAINT_PIC`, `THUMB_GROUND`, `thumb_name`, `by_preview`, `on_screen`, `thumb_wants`, `_where`, `_want_thumbs`, `thumb_of`, `_thumb`, `thumbnail_line`; `_canvas` records `seen_rect` (the editor's visible canvas rect via `screen_to_canvas`), `thumbs`, `preview`, and calls `_want_thumbs` after the nodes are drawn; `_node` draws the box after the title line for a picture node, collapsed or expanded, and leaves out a picture node's summary lines.
- `hyperspace/ui.py`: one SYSTEM line (`thumbnails · N copied · M kept`) under the GRAPH page's timing line.
- Tests: new `tests/test_thumbnails.py` (14 tests); `tests/test_graph_legible.py` height assertion updated (deliberate: picture nodes now take their thumbnail's room).

## Cost per kind (also row 4xe)
- One blit (192-texel pass): scene, hands layer, channel (fit already made), pattern, a look-back trail / dream already bound by a consumer, an effect held for two readers or folded after a made texture, a composite made into a texture, an output's handoff.
- Full-size repaint + blit: an effect painting directly into its single consumer, a switch, delay/echo laid by cover, resize, a composite or look-back painted direct. Each holds a full-size frame target (or one more effects-pool texture) while wanted.
- Only drawn, on-screen nodes are wanted; nothing behind an unpicked switch input; nothing that reads nothing.

## How it was tested
- `uv run pytest -q` → `3972 passed, 2 skipped in 94.30s` (base 3958 + 14)
- `uv run ruff check .` → `Found 25 errors.`. All are pre-existing in files this task does not touch (`docs/plans/assets/39-vision/bench_*.py` 13, `hyperspace/media/{adapters,folder,proxy,video}.py` 5, `tools/ingest.py` 3, `tests/test_{media_folder,sequencer,ui_desk,ui_pad}.py` 4; ruff 0.16.4 in the fresh venv). On the touched files: `All checks passed!`
- `uv run pytest -q --all tests/test_golden_frames.py` → `128 passed in 9.99s` (no golden file changed; `git status` shows none). Note: without `--all` this file reports `no tests ran` (the fast tier skips it), so the gate line in common.md needs `--all`.
- `uv run pytest -q --all` → `4184 passed, 2 skipped in 47.86s` (base 4170 + 14)

What the new tests cover: want → made next frame; unwanted for a second → dropped; wanted again → remade; dimmed then black ages; the count; thumbnail size/aspect; the table covers every IMAGE kind of `WIRED_MAKES` plus the generic fallback; **outputs byte-identical over three frames with every node wanted vs none** (two outputs, an effect, a composite), the stats and GPU timer untouched; `graph.picture` asked only for wanted nodes (a counter on `render.picture`); a thumbnail shows its picture (output 2's thumbnail mean ≈ output 2's mean, opaque); unbuilt/undrawn nodes make nothing; hot reload drops and remakes; the page wants exactly the drawn, on-screen picture nodes, nothing off screen, nothing hidden by preset only, never output 1; a headless draw of the page asks every drawn picture node for its body collapsed and expanded and sets `VNode.picture`; the SYSTEM line is drawn.

## Self-review findings
- Painting after `evaluate`: nodes' `paint`/`image` checked for side effects — effects' clocks advance once per frame time (idempotent), `Lookback.trail` and the dream's lay read only, frame data caches prevent repaints of anything the frame already made, held pool textures (incl. the ones a presenter's handoff may reference) are never handed out by `_spare`. The one visible effect: a look-back asked after the frame's capture includes this frame's commit; an echo whose slot was just rewritten reads nothing (dim).
- `Frame` is not copied; `stats` is snapshotted and restored in place so sub-frames (`Frame.at`) sharing the dict are covered too.
- The page's `_where` falls back to `NODE_W × (HEAD_H + THUMB_H)` before the editor has sized a node.

## Concerns
1. **Spec deviation**: no mipmaps (P1 says "mipmapped"); a 16-tap pass instead, because `build_mipmaps` changes a frame-owned texture's filter (golden risk). Reversible in one shader.
2. **Collapsed picture nodes lose their N7 lines** (switch pick, "reaches nothing", `said`) until C2's hover lands — as the brief says, but the canvas says less in the meantime.
3. Auto-laid positions of picture nodes shift once (their height changed); stored positions do not.
4. Outputs 2–4 show their handoff frame without the hands; output 1 shows the full window via `Preview` — an inconsistency the owner may notice.
5. No explicit `glFlush` for the thumbnails: they rely on output 1's swap (after `draw_outputs`) flushing before the control window samples them. Unverified at the machine.
6. Everything visual and the cost on the show Mac are hand checks (AH.1–AH.3, AH.5 drafted).

## Files
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/hyperspace/outputs.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/hyperspace/render.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/hyperspace/graphview.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/hyperspace/ui_graph.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/hyperspace/ui.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/tests/test_thumbnails.py
- /Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/agent-a8c7a09eb93a62ce3/hyperspace-python/tests/test_graph_legible.py
- Decisions: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/37-C1.md

---

## Fix report (review round 1) — commit f0cfaf7, pushed to PR #255

1. **IMPORTANT, fixed**: `render.thumb_source` now returns None for any node not in `Graph.pulled` (every kind), checked before `Node.reads` (which reads a channel). New test `test_a_node_behind_an_unpicked_switch_input_is_not_made`: a composite (channel a under, scene over) behind the switch's unpicked input is not copied, only channel b is read (`_media_now` raw keys == {b}), it dims then blacks after a second, and it's copied again once it's picked. I checked that the test fails with the old gate (`count == 1`).
2. `PreviewTextures.kept` now counts the thumbnails held (`len(tex)`; with no context, the names copied and not dropped). The docstring says so. `test_the_count_is_this_frames_copies` now expects 2 kept, not 3.
3. Flush: `Renderer._thumbnails` calls `render._flush()` (`OpenGL.GL.glFlush`, the same call as app.py's `_gl_flush`; it's best-effort) whenever it copied something that frame. Both the docstring and the decisions row say so. app.py is untouched.
4. The byte-identity fixture now has a delay (kaleido a frame late), the look-back's trail, and a switch (select 1) feeding the composite into output 2. `EVERY` includes delay, lookback and switch; it checks that all 8 are copied and that `0 < repainted < 8`. Outputs are byte-identical over 3 frames.
5. SYSTEM line: `thumbnails · N copied · K repainted · M kept`. The repainted count is how many copies left a new entry in the frame's data, i.e. pictures the frame hadn't made itself. The decisions row now gives the held target cost: about 8 MB per 1080p RGBA8 node, twice that for a half-float one.
6. Output 1 not dimming: I recorded it as a rough edge in the row and the `_body_of` docstring rather than building an age for `Preview`.
7. Renamed `ui_graph.thumb_of` to `_body_of`, along with the test's monkeypatch.

Gates:
- `uv run pytest -q`: 3973 passed, 2 skipped (+1)
- `uv run ruff check .`: 25 errors, the same ones that are already on the base; the touched files are clean
- `uv run pytest -q --all tests/test_golden_frames.py`: 128 passed, no golden moved
- `uv run pytest -q -n0 tests/test_thumbnails.py`: 15 passed
