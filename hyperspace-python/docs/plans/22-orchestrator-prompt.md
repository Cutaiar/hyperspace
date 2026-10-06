# Plan 22 — orchestrator launch prompt

You are the top-level orchestrator for Plan 22 in `Cutaiar/hyperspace`.
You manage two independent streams of work through sub-agents, integrate
them, review them, and open one PR to `main`. Work the way Plan 21 / PR #80
was worked: numbered work packages, one branch and PR each, an integration
branch, a review pass, and a docs work package that records what was built.

Start by reading `hyperspace-python/docs/CHECKPOINT.md`,
`ARCHITECTURE.md`, `DECISIONS.md`, `DECISION-REGISTER.md` and
`docs/plans/README.md`. Then read `docs/plans/21-outputs-and-the-hands.md`
as the model for what your final docs WP must look like.

Base everything on `main` at `eb3d72e` or later. `main` is current as of
2026-10-06; there are no open PRs.

---

## The two streams

### Stream A — the flat shapes get real 4D extent

Six shapes collapse to a plane at some viewing angles: **Heart, Star,
Torus, Trefoil knot, Starfruit, Möbius strip**. They are built through
`geometry.param_surface` (line 315), whose sample function returns three
coordinates, and indexed by `_mesh3` (line 263), which at
**`geometry.py:280`** pads every vertex as `[p[0], p[1], p[2], 0.0]`.
Every vertex has `w = 0`. Their `Shape.cells` field is `0`, the code's own
marker for "not a polytope".

Because `w = 0`, a 90° rotation in XW moves the whole x-extent into w and
brings zeros back as x; projecting to 3D drops w, so a dimension is lost.
The three W-involving planes (XW, YW, ZW) are driven by SUB, BASS and MIDB
— the bass bands — so this happens continuously, not occasionally.

**The reference implementation already exists in the repo.** Shape 17,
`Clifford torus`, is `duoprism(32, 16, True)` — a flat torus with genuine
4D coordinates that does not collapse. It is the destination for shape 21,
the 3D donut. Compare against it.

- **A1 — the four-coordinate surface path.** Give `param_surface` and
  `spherical_surface` a way to return a `w` component, and `_mesh3` a way
  to carry it. Prefer a *lift* (`w` as a function of the existing `u, v`)
  over sweeping into a 3-manifold: a lift keeps the face count and is what
  the standard 4D Klein bottle embedding does. Add a per-shape way to
  declare that a shape is 3D and should have the W planes masked instead
  (see the per-shape rule below).
- **A2 — the six shapes.** Give each a `w(u, v)`. Judge each one, and for
  any that reads badly, fall back to masking the W rotation planes for that
  shape and remapping the bass bands. Produce turntable renders — a full
  360° sweep of each of XW, YW and ZW independently, per shape — as the
  evidence, saved under `tools/` output or `docs/plans/assets/`.
- **A3 — the Klein bottle.** New shape, built with genuine w-extent from
  the start. It only embeds without self-intersection in 4D, so it is both
  the best proof A1 works and the shape that most wants it. The Möbius
  strip is its neighbour and shares the seam-merging behaviour.
- **A5 — the new-family shortlist (document only, no implementation).**
  While A1 has this code loaded, assess which further 4-polytope families
  are cheap to add now. All six regular convex 4-polytopes already exist
  (5-cell, tesseract, 16-cell, 24-cell, 120-cell, 600-cell), so the open
  territory is the second tier: the rectified / truncated / cantellated
  series, the grand antiprism, the snub 24-cell, the 4D Catalan duals, and
  the Schläfli–Hess star polytopes. Rank them by effort against the
  machinery as it stands after A1, and say which would stress `_mesh3`'s
  simple-planar-polygon assumption — the stars especially, which is the same
  risk area A2 is already probing. **Produce a ranked list with difficulty
  notes and build none of them.** The owner picks.
- **A4 — docs.** As described under "What the docs WP must produce".

**Acceptance for Stream A:** each of the six shapes, plus the Klein bottle,
keeps visible volume through a full 360° sweep of each W plane
independently. No viewing angle reduces any of them to a plane or a line.

**Known risk, check it early:** `_mesh3` drops any cycle that revisits a
vertex non-consecutively and any quad with fewer than three distinct
vertices, because face UVs need simple planar polygons. A non-planar 4D
quad may break face framing or silently shed faces. Separately, the Möbius
seam closes by `kkey` coincidence-merging — adding a w component changes
which points coincide. Check face counts before and after, per shape.

**Golden traces:** the parity bar is exact geometry (1e-12, vertex order
kept). Changing these six shapes' vertices will move any golden data that
covers them. Re-record **only** the six 3D surfaces, state in the commit
that you did and why. The 19 polytopes' geometry must not change at all —
if a polytope's golden trace moves, you have broken something.

### Stream B — the face patterns become usable

Two problems, and the second is the important one.

**The mod inputs have no convention.** `shaders/patterns.glsl` exposes
`u_mod[8]`, registered as `pattern.mod.0`–`.7`, range 0–2.6, with **1.0 as
the un-driven neutral**. The factory `legacy6` routes put analyzer lane *i*
on `u_mod[i]`. But each of the 12 modes uses the indices for different
things: index 1 is phase speed in one mode, a falloff exponent in another,
a width wobble in a third; index 3 is arm count in one and petal count in
another. No route is portable between patterns. **No existing preset has
meaningful custom mod routing, so you may redesign this freely with no
migration path to preserve** (owner's decision, 2026-10-06).

**The subsystem is not explorable.** Effects have `ui_fx.py` — 561 lines,
chips, a browsable list, controls you can read and get a feel for. The
`faces` page has no module of its own; it is drawn inline in `ui.py` as one
dropdown plus eight anonymous sliders. The owner's requirement, verbatim in
spirit: *none of the visual ambition matters if the system does not lend
itself to first-time usability and efficient exploration of the state space
once you know what you're doing.*

- **B1 — the mod convention.** Decide what each of the eight inputs *means*
  across every pattern — density, speed, scale, count, and so on — name
  them, and make every mode honour it. A routing set that feels good on one
  pattern must be meaningful on the next. Keep the 1.0-neutral convention
  and the `vec4 pattern(int mode, vec2 uv, float fid)` contract.
- **B2 — the FACES page.** Bring it to parity with the FX page's
  discoverability. A first-time user should be able to open it, see what
  modes exist, see what the eight inputs do *for the mode they are on*
  (named, not numbered), see what is currently driving each, and find a
  good look without reading shader source. Follow `ui_fx.py`'s patterns;
  a `ui_patterns.py` module alongside it is the natural shape. Add it to
  `ui.PAGES` properly.
- **B3 — the patterns themselves.** Rework the 12 modes onto the
  convention, then add new ones. The owner wants expressiveness, and
  expressiveness here is plural: sometimes bold and maximalist colour,
  sometimes technically interesting generative depth, sometimes plainly
  seeing the audio drive the bands. Pursue all three — but **gated on B2**:
  an expressive mode nobody can find or steer is not a win. Art direction
  matters; deliberate palettes and composition, not just more modes.
  `patterns.glsl` hot-reloads on save and keeps the last good version on a
  compile error, so iterate live with the app running.
- **B4 — docs.** As described below, including the per-index documentation
  of the new convention.
- **B5 — candidate macro presets (preparation only).** Build a set of macro
  configurations worth auditioning and save them as loadable presets —
  base subscribers (`a + m · (b − a)`) and depth subscribers across the
  destinations that matter: plane drives, per-band gain, the new pattern
  inputs, FX amounts. Aim for configurations where one knob re-scales a
  whole scene coherently. **Judging them is a listening session with the
  owner and is not your call** — your job is to leave good candidates ready
  to try, named so their intent is obvious, with a line each on what the
  macro is supposed to do.

**Acceptance for Stream B:** a person who has never seen the page can open
FACES, understand what the eight inputs control for the current mode, and
reach a look they like without opening a `.glsl` file. And one routing set
produces a coherent, legible response on every pattern without re-aiming.

---

## Decisions already made — do not relitigate

1. **Per-shape choice on w-extent.** Keep w-extent where it reads well;
   fall back to masking the W planes for shapes where it does not. A
   per-shape flag is expected. Do not force all six down one path, and do
   not revert all six because one looks wrong.
2. **The mod convention is free to change.** No legacy mod routing to
   preserve.
3. **Expressiveness is gated on usability.** B2 before B3 lands.
4. **The polytope audit is deferred, and will probably delete nothing.**
   The six "bad" shapes are bad *because of* this bug. Do not remove any
   shape. Re-judge after A2.

## Out of scope for this run

**Implementing** any new polytope family. A5 assesses and ranks them; the
owner decides what gets built, in a later plan. Do not add a new family to
`SHAPES`, however cheap A1 makes it look — the one new shape in this plan is
the Klein bottle (A3).

**Judging the macro candidates.** B5 prepares them; the owner auditions
them. Do not tune a macro set by eye and declare it good.

Also out: removing any existing shape (see decision 4 below), and anything
touching the hands package, the desk, presets or outputs — those subsystems
are settled and nothing here needs them.

## Decisions you may make yourself

Anything not settled above. When you take your own recommendation and build
it, append a row to `docs/DECISION-REGISTER.md` starting at **row 89**
(rows 1–88 exist), in that file's format: what was built and what the owner
will see or feel, the other option(s), the cost to reverse, the known rough
edge, and the hand check that lets the owner judge it. Mark the
corresponding `DECISIONS.md` row's **Who** column as `row N`, not `owner`.
Never mark a row `owner` yourself.

---

## How to orchestrate

- One sub-agent per work package, each in **its own git worktree**.
- **Branch every worktree off the same fresh base**, and re-verify that base
  immediately before you spawn. The failure mode that silently ruins this
  workflow is an agent branching off a stale base and producing a diff that
  conflicts or quietly reverts a sibling's work. Check it, don't assume it.
- Branch names `plan-22-a1-<slug>`, `plan-22-b2-<slug>`, and so on. One PR
  per work package, titled as Plan 21's were.
- Merge each WP into `plan-22-integration`. The streams are independent —
  A touches `geometry.py` and the shape list, B touches `shaders/`,
  `ui_*.py` and `params.py`. If they collide, you have mis-scoped a WP.
- Sequencing: A1 → A2 → A3 within Stream A; B1 → B2 → B3 within Stream B.
  The two streams run in parallel. A5 may start once A1 has settled the
  surface path; B5 once B1 has named the mod inputs. A4 and B4 last, since
  they record what the others built.
- **Run a review pass over the integration branch** before the final PR, and
  commit its fixes as `Review: <what was fixed>`, the way Plan 21 did.
- **Re-measure everything on the merged branch.** A sub-agent's measurement
  taken inside its own worktree does not survive integration. Before you
  claim any acceptance criterion is met, re-run the check on
  `plan-22-integration` itself. This applies to the turntable renders, the
  face counts, the test suite, all of it.
- Finally, one PR from `plan-22-integration` to `main`, titled
  `Plan 22: the flat shapes in 4D, the face patterns made usable`.

## Gates — all green before any PR

```
uv run pytest -q
uv run ruff check .
HYPERSPACE_FRAMES=120 uv run hyperspace     # windowed smoke run
```

These boundary tests must keep passing untouched. They are the architecture,
asserted:

- `tests/test_hands_boundary.py` — `hands/core.py`, `signal.py`, `tape.py`
  import nothing from the package.
- `tests/test_routing_boundary.py` — routing imports nothing above it, and
  `Param.modulate` has exactly one call site.
- `tests/test_render.py::test_the_render_stack_imports_no_registry`.
- `tests/test_app_boundary.py::test_importing_app_leaves_every_gated_adapter_unimported`
  and `::test_the_frame_runs_in_the_documented_order`.

Also hold these invariants: modulation is non-destructive and never writes
into `PARAMS`; the render stack reads parameters and never writes one; no
new module may import `torch` outside `dream.py`.

## What the docs WP must produce

Match Plan 21's docs WP exactly:

- `docs/plans/22-<slug>.md` — the plan **as built**: what was built, what is
  not verified by a person, known rough edges.
- `docs/ARCHITECTURE.md` — updated in the same PR if a boundary, the frame
  order or the control model changed. Add the 3D-versus-4D shape
  distinction: that `cells == 0` marks a surface rather than a polytope, and
  which shapes now carry real w-extent.
- **`docs/ARCHITECTURE.html`** — the diagrammed companion to the Markdown,
  and maintained with it in the same PR. It is a self-contained page: inline
  CSS, inline SVG, Google Fonts by link, no build step and no other assets.
  Two things in it that this plan will certainly move: the **band-to-plane
  map** figure, if any band's plane or direction changes, and the **counts**
  in the masthead and the closing stat row (modules, lines of app, lines of
  tests, test files, shapes, effects — shapes goes to 26 with the Klein
  bottle, and patterns changes if B3 adds modes). Diagram colours come from
  CSS classes, never `var()` inside SVG presentation attributes — browsers do
  not resolve those, and the figures will render black if you change this.
  Keep the light and dark token blocks in step.
- `docs/ENGINEERING.md` — the new behaviour: the mod convention per index,
  the FACES page, how a shape declares w-extent or masking.
- `docs/DECISIONS.md` and `docs/DECISION-REGISTER.md` — rows from 89.
- `docs/plans/11-hand-checks.md` — a new group **R** (A–Q exist), checks
  numbered from **113** (1–112 exist). Follow the existing format: bold
  number and title, the headless tests behind it, the setup, then *Pass:*
  and *Fail:* with the failure pointing at the likely cause.
- `docs/TESTING-GUIDE.md` — the same checks in plain words, by hardware,
  each entry ending with its check numbers.
- `docs/CHECKPOINT.md` — kept short and current.

## Report back

When the PR is open, report:

- What landed per stream.
- **Which of the six shapes kept w-extent and which fell back to masking**,
  and why for each. Link the turntable renders.
- The A5 shortlist: the ranked families, the cheap ones, and the ones that
  would fight `_mesh3`.
- The B5 candidates: what each macro set is meant to do, so the owner can
  audition them without reverse-engineering them.
- The register rows you opened (89–N), each with what it needs from the
  owner.
- The new hand check numbers and their group letter.
- Anything you deliberately left undone, and anything you found that
  contradicts this prompt — including in the docs. If a document says
  something the code does not do, say so rather than quietly matching it.
