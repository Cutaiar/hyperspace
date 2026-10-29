# Plans 37, 38 and 39 — pictures and the faces, the hold, vision (orchestrator prompt)

You are the top-level orchestrator for three plans in `Cutaiar/hyperspace`
(the Python app under `hyperspace-python/`), run **in parallel**, each on
its own branch, merged through one integration branch:

- **Plan 37 — nodes as pictures, and the faces**
  ([`37-pictures-and-faces.md`](37-pictures-and-faces.md), a draft spec with
  five open decisions, the recommendation taken for each unless the owner
  says otherwise during the run). The GRAPH page draws every picture node
  as the picture it makes; the face patterns are cut to the ones the owner
  names; the `acid-scene` backward wire.
- **Plan 38 — hold the projector** ([`38-hold.md`](38-hold.md) on branch
  `output-hold`, **a first cut already built** on 2026-10-27 from
  `graph-quick-wins` @ b914064, with D1–D5 answered by recommendation).
  It needs rebasing onto `main` (two conflicts: `docs/plans/README.md` and
  `ui_graph.py`, where plan 36 moved the head), its 16 tests green there, a
  review pass, and its docs (register rows, hand checks) written.
- **Plan 39 — vision** ([`39-vision.md`](39-vision.md), every decision
  answered by the owner; build plan [`39-vision-build.md`](39-vision-build.md)).
  `segment` (any picture → foreground, background, mask), `matte` and `cut`,
  the mask as its own wire, `edges` as an effect file.

Work the way plans 24/26/27 and 28/30 were worked: one sub-agent per task
in its own git worktree off a verified base, numbered tasks, one branch per
plan, an integration branch, a review pass per plan, a docs task per plan.
The owner merges the final PR.

**Read first, in full:** the three plan files above and plan 39's spike
([`assets/39-vision/findings.md`](assets/39-vision/findings.md)), then
`docs/CHECKPOINT.md`, `ARCHITECTURE.md` (§2 the render graph, the Media
and Graph rows of §1's table, the thread table), `DECISIONS.md`,
`docs/plans/README.md`, `36-wysiwyg-graph.md` (the WYSIWYG rule and its
"Known follow-ups"), and `28-30-orchestrator-prompt.md` as the model for
this prompt's ledger and briefs (`assets/28-30-run/`).

## The rules every stream keeps

- **The graph on GRAPH is the whole truth** (plan 36, the owner's rule for
  the last time): no default graph, no hidden edge, no auto layout, nothing
  filled in at load.
- **Alpha is not a mask** (the owner, 2026-10-27; plan 39): a mask is a
  pattern, a pixel passes or it does not, on its own wire.
- **Pictures don't move**: no golden under `tests/golden/` changes except
  where a plan says so with the reason in the commit (plan 37 P2 re-records
  the presets whose pattern is dropped; nothing else).
- **Both Macs on this build** before any preset saved with the new kinds is
  shared (a `/7` section with `segment`/`matte`/`cut` reads as black on an
  older build).
- Sub-agents never push to `main`, never merge, never rebase a branch
  another stream is on, never dispatch their own sub-agents; commits end
  with the attribution lines the session gives.

## The base

`main` @ **f2351a0** or later (plan 36 merged as #245, #246 before it, #247
after). Verify it before cutting anything; re-check it before each
worktree. Integration branch **`plan-37-38-39-integration`** cut from
there; each plan's branch cut from the integration branch:
`plan-37-pictures`, `plan-38-hold` (made by rebasing `output-hold`'s one
commit, 3959f57, onto the integration branch — the owner's words in that
commit's message are kept), `plan-39-vision`.

Numbers, assigned now so the three docs tasks never collide:

| plan | register rows | hand checks | group |
|---|---|---|---|
| 37 | 417–429 | 370–376 | AH |
| 38 | 430–439 | 377–383 | AI |
| 39 | 440–459 | 384–393 | AJ |

(Row 416 and check 369 are the last used, by plan 36. A plan that needs
more rows takes them after 459 and says so in the ledger.)

## Who owns which files (the parallel contract)

The three streams touch the same app. Each owns files; a stream that must
touch another's file does so in the smallest way the table allows and says
so in its report, and the integration merge is where the controller
reconciles.

| file | 37 | 38 | 39 |
|---|---|---|---|
| `graph.py` | read `picture()` only; no new kind, no port | nothing | **owns**: the promotion, `matte`, `cut`, `segment`, pins, tables |
| `render.py` | `PreviewTextures` and the `_for_the_panel` hook | nothing (the program/preview draw lives in `hold.py` and `app.py`) | `segmenter()`, `motion_pair()`, the `masks.py` hand-off only |
| `masks.py`, `segment.py`, `shaders/fx/edges.glsl` | — | — | **new, owns** |
| `hold.py`, `undo.py`, `hotreload.py` | — | **owns** | — |
| `app.py` | nothing | **owns** `_draw_render`, the hold's construction | `renderer.segment_cfg`, the workers on the close list (two lines, beside the dream's) |
| `ui_graph.py` | **owns** `_node`, the thumbnail draw, the hover | **owns** the head (`_head`, `head_line`, chips), the backdrop-forced-on, the PROJECTOR inset | `COLOURS` only if a promoted cable needs a style |
| `graphview.py` | **owns** `summary` and whatever the thumbnail needs on `VNode` | nothing | table entries only (`LABELS`, `HOVERS`, `OWNERS`, `PICKER_GROUP`, `picker`, `FRAME_CLASS`, `_stand_in`, `STARTERS`) |
| `patterns.glsl`, `patterns.py`, `ui_patterns.py`, the presets whose pattern is dropped | **owns** | — | — |
| `params.py` | nothing | nothing (`output.hold`/`take`/`drop` register from `hold.py`) | `declare_mattes`, `declare_cuts`, `declare_segments` |
| `preset.py` | nothing | nothing | the landing of the three declares, beside the resizes |
| `outputs.py` | `Preview` reused as is; a `PreviewTextures` may live here or in `render.py` | `Preview` reused as is (the monitor) | nothing |
| `pyproject.toml`, `uv.lock` | — | — | `pyobjc-framework-vision` |
| `ARCHITECTURE.md`, `DECISIONS.md`, `DECISION-REGISTER.md`, `11-hand-checks.md`, `CHECKPOINT.md`, `README.md` | its own rows, checks and lines, in its own docs task, **rebased last** | same | same |

The one shared seam: **plan 37's thumbnails show plan 39's nodes without
either knowing the other.** 37 asks any node whose `OUTPUT` is `IMAGE` for
`picture()`; 39's `segment.fg`/`.bg` pins and `cut` are such nodes, and a
mask node is one through 39's promotion. Neither stream writes code for the
other. If 37 lands first, 39's nodes get thumbnails on merge; if 39 lands
first, 37's generic path covers them.

## Streams and their tasks

### Stream A — plan 39 (vision), six tasks

T0 `edges.glsl` → T1 alpha is honest → T2 the mask wire and `matte` →
T3 `cut` → T4 `segment` and the worker → T5 GRAPH and the pages → T6 docs,
as [`39-vision-build.md`](39-vision-build.md) writes them. T0 and T1 are
independent and may run as two worktrees at once; T2 → T3 → T4 are a chain;
T5 after T4; T6 last. T0 may be offered to the owner as its own PR ahead of
everything (decision 7).

### Stream B — plan 38 (hold), four tasks

- B1 **rebase**: `output-hold`'s commit onto the integration branch; resolve
  `ui_graph.py` against plan 36's head (the hold chips go first on the head
  as the spec says, before plan 36's chips) and `README.md`; the hold reads
  `Renderer.wiring` as plan 36 left it (the spec says it "works the same once
  plan 36 makes the graph explicit" — prove it: a held graph with a rig bus
  cut stays held). Its 16 tests green; the fast tier green.
- B2 **hand-check readiness**: the spec's seven checks become group AI
  377–383; the two the controller can run headless (the program draws from
  the held wiring while the live wiring changes; drop reverts as one undo
  step) get tests if they lack them.
- B3 **review**: a reviewer sub-agent reads the diff against the spec's D1–D5
  and the plan 36 rule (a hold must never fill in a wire); its findings
  fixed in place.
- B4 **docs**: rows 430–439 (D1–D5 and the rulings), checks 377–383,
  `ARCHITECTURE.md`'s host paragraph (the program and the preview in the
  frame loop; `hold.py` in the module table), `README.md`'s line.

### Stream C — plan 37 (pictures and the faces), five tasks

- C1 **thumbnails** (P1's how): `PreviewTextures`, the page's want list,
  the end-of-frame copies, `_node` drawing the thumbnail, the dimmed-then-
  black rule; tests on the want/drop lifetime and that a hidden node is not
  copied; a SYSTEM line with the count.
- C2 **hover and the head switch** (P1, D2, D3): the hover text; the
  `pictures · tint cables` switch off by default.
- C3 **the backward wire** (P3, D5): the area rule, the test over every
  factory preset.
- C4 **the faces** (P2, D1): **waits for the owner's list**; until it
  arrives the task is a dry run (`tools/preset_shots.py` sheets of the 17
  for the owner to judge, the migration map `dropped → nearest kept`
  prepared, no shader removed). If the list never arrives in the run, C4
  ships the sheets and the map and the spec says so.
- C5 **review and docs**: a reviewer on C1–C3; rows 417–429, checks
  370–376, `ARCHITECTURE.md`'s GRAPH page paragraph, `README.md`'s line.

## Merge order and the final PR

1. **Plan 38 first** (smallest, already built): `plan-38-hold` →
   `plan-37-38-39-integration` once B1–B4 are done.
2. **Plan 39 second**: `plan-39-vision` rebased on the integration branch
   (38's `ui_graph.py` head changes and 39's `COLOURS` line do not overlap;
   `app.py`'s two lines sit beside the dream's, away from `_draw_render`).
3. **Plan 37 last**: `plan-37-pictures` rebased on the integration branch
   (its `ui_graph._node` and `graphview.summary` sit away from 38's head
   and 39's tables; its `render.py` hook away from 39's `segmenter`).
4. After each merge: the fast tier, then the full suite with goldens, then
   `graph.signature` fixtures unchanged except where a plan recorded new
   cases. The ledger records the counts.
5. The final PR `plan-37-38-39-integration → main`, titled for the three
   plans, its body the three README lines and the test counts; the owner
   merges. Both Macs then update together (plan 39's new kinds).

If a stream finishes early and clean, it may be offered to the owner as its
own PR to `main` ahead of the rest (plan 38 and plan 39 T0 are the likely
candidates); the integration branch then rebases onto `main`.

## The ledger

`assets/37-38-39-run/`: `ledger.md` (every task: branch, worktree base,
status, test counts, review findings, the rows and checks it took), the
briefs as sent (`briefs/<plan>-<task>.md`), the decisions the controller
made in the owner's absence (`decisions.md`, each with what the owner can
reverse), and the sub-agents' reports as received (`reports/`).
