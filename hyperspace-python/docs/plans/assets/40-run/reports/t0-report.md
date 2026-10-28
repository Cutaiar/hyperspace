# T0 report — plan 40 D1: `patch.py` is `modgraph.py`

**Status:** DONE
**Base:** f10f281 (confirmed after `git reset --hard FETCH_HEAD`). Branch `plan-40-t0`.
**PR:** https://github.com/Cutaiar/hyperspace/pull/269 (into `plan-40-build`, not merged)

## Commits
- 3884d64 Plan 40 T0 (D1): patch.py is modgraph.py, the word patch freed
- 2e54b4d Plan 40 T0 (D1): the docs name modgraph.py's symbols
- fa4da2d Plan 40 T0 (D1): the symbols in backtick spans that cross a line

## What was built
- Two `git mv`s: hyperspace/patch.py → modgraph.py and tests/test_patch.py → test_modgraph.py.
- The imports: `from . import patch as patchmod` → `from . import modgraph`, with no alias, in routing.py and graphview.py. Ruff's isort merged it into the existing `from . import …` lines.
- The Router: `build_patch` → `build_modgraph`, `patch` → `modgraph`, `patch_notes` → `modgraph_notes`, `patch_cut` → `modgraph_cut`. The private names `_patch_key` and `_rebuild_patch` and the cache keys were renamed with them.
- The readers: ui_routing.py (`modgraph_notes`) and graphview.py (`modgraph_cut`, in 3 places).
- The module's types: `Patch` / `PatchNode` / `PatchEdge` → `ModGraph` / `ModNode` / `ModEdge`.
- The docstring's first line is kept, and a note says the module was named `patch` until plan 40.
- `hotreload.MODULES`: `"patch"` → `"modgraph"`, in the same slot.
- Comments that name the symbols, in lfo.py, params.py, graph.py and modbank.py.
- Tests: test_modgraph.py, test_routing.py, test_modbank.py, test_plan31_wiring.py and test_graph_effects.py, plus the renames of two test functions.
- Docs: a sed inside backtick spans only, with every line read by eye. Lines touched per file: ARCHITECTURE.md 17, DECISION-REGISTER.md 14, DECISIONS.md 3, ENGINEERING.md 4, plans/28-node-editor.md 14, plans/28-30-orchestrator-prompt.md 17. ARCHITECTURE.html is untouched: it names none of the symbols, only the prose "the patch". `docs/plans/assets/28-30-run/` is untouched.
- These keep the word: "k patched", `PATCHED_TIP`, prose like "the modulation patch", and `mock.patch` / `monkeypatch`.

## Where the build differs from the spec, and why
- **The rename is wider than the list (47a).** The class `Patch` and its kin, `patch_cut` and the private names were renamed too. The task's goal is that "patch" means the owner's thing only. A `Patch` class would collide with T1's patches.
- **The docstring note avoids the literal "patch.py" (47b).** Writing it would break step 4's proof grep.

## Tests (from hyperspace-python/)
- `uv run pytest -q`: `1 failed, 4121 passed, 2 skipped`. That is the base's count (4124). The base log also shows 1 failure, in a different load-flaky media test. Mine was `test_media_folder.py::test_a_file_still_downloading_is_not_opened_until_it_is_ready`. Run serially with `-n 0`, it and the base's flaky test both pass (`2 passed`).
- `uv run ruff check .`: `Found 25 errors.` These are the same 25 as the base, in docs/plans/assets/39-vision, media/* and tools/ingest.py, and none is in a touched file. Ruff on the touched files: `All checks passed!`.
- `uv run pytest -q tests/test_golden_frames.py`: `no tests ran` (the goldens are only in the full tier). `uv run pytest -q --all tests/test_golden_frames.py`: `136 passed`. Nothing was re-recorded.
- `uv run pytest -q --all`: `2 failed, 4342 passed, 2 skipped`. The failures were `test_media_core.py::test_bad_file_is_an_error`, a known flaky test, and `test_migrate_library.py::test_the_real_picture_check_passes_an_old_preset`. Both pass serially with `-n 0` (`2 passed`). Neither touches the modulation graph.
- `grep -rn "patch\.py\|patchmod\|build_patch\|patch_notes" hyperspace/ tests/`: empty.
- `git diff --stat f10f281`: 20 files. These are the 14 code/test files above plus the 6 docs. Of the code files, graph.py, params.py, modbank.py and lfo.py are outside the dispatch's named list, but the grep found them, and each change is a one-line comment or docstring.

## Self-review
- In routing.py the property `Router.modgraph` has the same name as the module. Method bodies see the global module, the annotations are deferred by the `__future__` import, and the property's own annotation is evaluated lazily. The tests confirm it.
- graphview and ui_routing read through `getattr(router, "modgraph_cut"/"modgraph_notes", ())`. A missed rename there would fail silently, so I grepped for every string `"patch*"` in hyperspace/ and tests/: none is left.
- No behaviour changed. The code diff is names only.

## Concerns / for T6
- `docs/plans/11-hand-checks.md` (forbidden to me) still cites `tests/test_patch.py::…` at lines 3362, 3376 and 3391. They should become `tests/test_modgraph.py`.
- `docs/plans/30-shader-nodes.md` (not in my list) names `patch.py` at lines 340 and 349.
- My commits carry the session's mandated `Co-Authored-By: Claude Opus 5.5` trailer, not the brief's "Fable 5.1". The harness's attribution instruction for this session takes precedence.

## Files changed
hyperspace/{modgraph.py (renamed), routing.py, graphview.py, ui_routing.py, hotreload.py, lfo.py, params.py, graph.py, modbank.py};
tests/{test_modgraph.py (renamed), test_routing.py, test_modbank.py, test_plan31_wiring.py, test_graph_effects.py};
docs/{ARCHITECTURE.md, ENGINEERING.md, DECISIONS.md, DECISION-REGISTER.md, plans/28-node-editor.md, plans/28-30-orchestrator-prompt.md}.

Decisions file: /Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t0.md
