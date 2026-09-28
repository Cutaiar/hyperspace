# Plan 10 — Architecture and documentation pass

**After plan 09.** The system grew through four plan-sized pushes in a
month (07 overhaul, 08 hands, 09 one performer, plus the FX / dream / restyle
PRs between them). Nobody — owner, maintainer or agent — can hold it in one
head any more, and the documents that exist say what each push *intended*,
not what the whole *is*. This plan writes the documents that keep one-shot
fixes possible: a component map, the frame-order data flow, the control
model as the one canonical statement, a shape sheet per module, a decisions
log, a refreshed ENGINEERING.md, and the findings of the audit that produced
them. It changes no behaviour. Docstrings are the only code it touches.

Docs: `docs/ARCHITECTURE.md` (new), `docs/DECISIONS.md` (new),
`docs/AUDIT-2026-09.md` (new), `docs/ENGINEERING.md` (refreshed),
`docs/assets/10-architecture/` (SVGs where a picture earns its place),
`docs/plans/README.md` row 10, `docs/CHECKPOINT.md`.

## Why

The plan 09 audit found two write paths for continuous sources —
`Router.drive` and `Router.modulate` — that had coexisted for weeks without
anyone noticing. Not because the code was hidden, but because no document
stated the control model in one place: plan 07 introduced modulation, plan
08 introduced Learn, and each was correct on its own page. The second path
was visible only to someone who read both pages and the code between them.

That is the failure this plan prevents. The test of every document here is
the one-shot fix: a maintainer or an agent who has never seen the repo
opens `ARCHITECTURE.md`, and from it alone can say **where a given
controller's value goes each frame** and **who may write a given
parameter** — then makes a change in the right place, first time.

The audience is the owner, other maintainers, and Claude sessions. All of
them know MIDI, DAWs and the codebase's vocabulary. Simple and conceptually
accurate beats exhaustive; the code remains the reference for the rest.

## Decisions (scope, settled before writing)

1. **The code is the ground truth, not the plans.** Plans 07–09 say what
   was intended; several "as built" sections already record where the code
   went its own way. Every architectural claim is verified against the code
   at `main` ef299ef and carries a `file:line` (pinned to that commit) or a
   test name. Where a plan and the code disagree, the document describes
   the code and the disagreement becomes an audit finding.
2. **ENGINEERING.md stays the behaviour reference; ARCHITECTURE.md is the
   structure reference.** ENGINEERING answers "how does this behave and why
   is it built that way"; ARCHITECTURE answers "what are the parts, how do
   they connect, who may write what". Neither duplicates the other; each
   links.
3. **The Python app is the only subject.** `hyperspace-web/` is frozen and
   out of scope; no document here describes it beyond the one sentence that
   says it is the golden-trace oracle. ENGINEERING.md §5 (browser sandbox
   constraints), §6 (puppeteer testing), §8 (Vercel deploy) and the
   `getUserMedia` / `getDisplayMedia` parts of §3b are true only of the
   HTML and are removed; the commit history keeps them.
4. **Describe the system as built now.** Plan 09's hand checks at the
   machine are still owed and may yield small fixes; the documents describe
   `main` at ef299ef and say so in their header. A later fix updates the
   line it changes, the way `CHECKPOINT.md` is kept.
5. **Findings are filed, not fixed.** The audit lists every place code and
   docs disagree, every duplicated concept, boundary leak, piece of dead
   code and test that asserts the old model — each with a one-line fix and
   a size — and this plan applies none of them, except to docstrings.
   Fixing while documenting is how the documentation stops matching the
   code again before the PR merges.
6. **Diagrams are Mermaid in the markdown**, so they render on GitHub and
   diff as text. An SVG under `docs/assets/10-architecture/` is drawn only
   where Mermaid cannot carry the picture (the control model's value
   spaces is the one candidate). Every SVG has its Mermaid or text twin so
   the markdown is never the poorer copy.
7. **Decisions are recorded with their date and their why**, gathered from
   the "Decisions" sections of plans 07, 08 and 09, the "as built" notes,
   and the session memory where it holds a decision the plans do not.
   A decision that the code no longer honours is listed as *superseded*,
   with what replaced it — not silently dropped.

## The document set

| Document | Answers | Written from | Kept current by |
|---|---|---|---|
| `ARCHITECTURE.md` | What are the parts; where does a value go each frame; who may write a param; the shape of each module | the code, this plan's audit | whoever changes a boundary or the frame order |
| `DECISIONS.md` | Why is it this way; what was rejected | plans 07–09, memory | whoever settles a new decision with the owner |
| `ENGINEERING.md` | How does the existing chain behave; what has been tried and failed | today's file, verified against the code | whoever changes behaviour |
| `AUDIT-2026-09.md` | What is wrong or drifting right now, and what it would cost to fix | this plan's audit | consumed by the follow-up plan; not maintained after |

### ARCHITECTURE.md, section by section

1. **Component map.** One Mermaid diagram of the major components and a
   table: what each owns, what it reads, what it writes, its boundary rule
   and the test that holds the rule where one exists
   (`test_hands_boundary.py`, `test_lfo_boundary.py`). Components, as the
   code groups them: the registry (`params.py`, `tapers.py`), the routing
   table (`routing.py`), the input adapters (`midi.py` + `apc40.py`,
   `hands/`, `gamepad.py`, keys and mouse in `app.py`, `bridge.py`), the
   sources that are not inputs (`analyzer.py` + `analysis.py` + `bands.py`
   + `audio.py`, `lfo.py` + `tempo.py`), the render stack (`geometry.py`,
   `render.py`, `fx.py`, `lookback.py`, `dream.py`, `overlay.py`,
   `shaders/`), the library (`library.py`, `presets.py`, `config.py`), the
   panel (`control.py`, `ui*.py`, `hands/panel.py`), and the host
   (`app.py`, `hotreload.py`).
2. **The frame.** A sequence diagram of one frame in `app.run`'s order —
   poll events / keys / gamepad / MIDI → `hands.poll` → `output.apply` →
   `mouse.poll` → `audio.step` → `bridge.step` → `lfos.step` +
   `publish` → `router.modulate` → `reg.apply` → `integrate` → `draw` →
   `panel.draw` — with the one-frame-lag rule stated once: a source that
   owns another source's parameter lands one frame before that source's
   output does, and every modulated value the panel shows is last frame's.
3. **The control model** — the canonical statement, correct above all
   else. Parameter registry; base vs effective; scene-setters vs the one
   performer; `push` / `position` and the rest; chaining through macros and
   LFO params; the referee and the Replace / Keep prompt; binding file
   schema 2 and the v1 migration and the factory remap; the tempo clock and
   the global LFO trigger. Every statement carries `file:line` at ef299ef
   or a test name. One table lists every writer of a `Param` in the code
   and which of base / offset / object it writes.
4. **Module shapes.** One screen per module (or package): purpose in a
   sentence, public surface (the names other modules use), what it must
   never do, where its tests are. Ordered as the component map.

### DECISIONS.md

A dated table, one row per decision: date · decision · why · source
(plan / PR / memory) · status (standing / superseded by …). Grouped by
theme rather than by plan, because the reader arrives with a question, not
a plan number: platform, control model, inputs, audio, render, library and
persistence, UI, process.

### ENGINEERING.md, refreshed

Kept: §2 geometry (verified against `geometry.py`; the shape table checked
against `SHAPES`), §3 rendering (rewritten for `render.py`: the two-window
host, the look-back and FX stages), §4 audio chain (verified against
`bands.py` / `analyzer.py`; the N-band analyzer stated; the trim note kept
only if the code still has the behaviour), §4b transport (verified against
`audio.py`), §7 visual conventions (already current), §10's worktree traps
(moved to a process section). Marked as changed by plan 09: anything that
says a source drives a param outside `Router.modulate`. Removed: §5, §6,
§8 (HTML-only, decision 3), §1 and the HTML-artifact preamble (history, now
in `DECISIONS.md` and the commit log), §9 threads that are closed or
restated in `CHECKPOINT.md`. Every surviving sentence is checked against the code.

### AUDIT-2026-09.md

Findings from the reading, one line each with a size (S ≤ ½ day, M ≈ 1–2
days, L ≈ 3–4 days): code–docs disagreements, duplicated concepts,
boundary leaks, dead code, tests asserting the old model, docstrings that
lie. Grouped by component, ordered by cost of leaving it. Ends with the
suggested shape of the follow-up plan.

## Work packages

Sizes: S ≤ ½ day, M ≈ 1–2 days, L ≈ 3–4 days. WP1 first and in parallel
across eight readers; WP2–WP5 on WP1's reports; WP6 last.

### WP1 — The reading · M · eight subagents in parallel

One reader per component area, each against the same checklist and each
returning a structured report (kept in the session, not the repo):

| Reader | Area |
|---|---|
| A | `params.py`, `tapers.py`, `routing.py`, `midi.py`, `apc40.py`, `control.py` |
| B | `hands/` |
| C | `lfo.py`, `tempo.py` |
| D | `geometry.py`, `render.py`, `fx.py`, `lookback.py`, `dream.py`, `shaders/` |
| E | `audio.py`, `analysis.py`, `analyzer.py`, `bands.py`, `offline.py` |
| F | `ui.py`, `ui_*.py`, `hands/panel.py` |
| G | `library.py`, `presets.py`, `config.py`, `library/` |
| H | `app.py`, `overlay.py`, `gamepad.py`, `hotreload.py`, `bridge.py` |

Each report: (a) purpose in one sentence; (b) public surface — every name
another module imports, with `file:line`; (c) imports in and out, and the
boundary rule the module actually keeps; (d) every read and write of the
registry (`Param.set*`, `nudge`, `scale`, `modulate`, `value`, `base`,
`norm`, direct object writes), with the line; (e) where its tests are and
which tests assert behaviour plan 09 removed; (f) docstrings and comments
that disagree with the code; (g) dead code and duplicated concepts;
(h) three sentences a newcomer needs that no document says. Readers do
not edit anything.

### WP2 — ARCHITECTURE.md · L · after WP1

Written in the order that matters: the control model first (verified line
by line against reader A's report and the code, then re-verified by a
fresh subagent that reads only the section and the code and reports every
claim it cannot find), then the frame, then the component map, then the
module shapes. The writer-reads-checker pass is the exit criterion, not a
courtesy.

### WP3 — DECISIONS.md · S · parallel with WP2

Gathered from plans 07–09 and memory; each row checked against the code
for status. Superseded decisions kept with their successor.

### WP4 — ENGINEERING.md · M · parallel with WP2

Section by section against readers D and E and the code; §5 / §6 / §8
removed as HTML-only. A sentence that cannot be
verified against the code is removed, not kept on faith.

### WP5 — AUDIT-2026-09.md · S · after WP1–WP4

The readers' (e), (f), (g) items plus what WP2–WP4 turned up, deduplicated,
sized, with a one-line fix each. Docstring fixes applied in this PR are
listed as done; everything else is filed.

### WP6 — Closing · S · last

`docs/plans/README.md` row 10; `CHECKPOINT.md` entry; `ARCHITECTURE.md`
published as a shareable page for maintainers without the repo; the PR
opened (not merged) and `/code-review` run on it if the merge needs one.
`pytest` and `ruff` unchanged from ef299ef's 628 / clean, because nothing
but docstrings moved.

## Exit criteria (checked on the PR branch)

- [ ] 1. Someone who has never seen the repo can, from `ARCHITECTURE.md`
      alone, say where a given controller's value goes each frame and who
      may write a given parameter. Checked by a fresh subagent given the
      document and five questions of that form, no code access.
- [ ] 2. Every statement in the control-model section carries a
      `file:line` at ef299ef or a test name, and a second subagent that
      reads only that section and the code finds no claim it cannot
      locate.
- [ ] 3. `ENGINEERING.md` contains nothing the code contradicts: every
      surviving section has been read against its module, and no
      HTML-only section remains.
- [ ] 4. `AUDIT-2026-09.md` gives every finding a size and a one-line fix,
      and `git diff ef299ef -- hyperspace/` touches docstrings and comments
      only (no statement changes; `pytest` count and `ruff` unchanged).
- [ ] 5. Every Mermaid block renders (checked with `mmdc` where available,
      otherwise by GitHub's preview on the PR), and every SVG has a text
      twin in the markdown.
- [ ] 6. `DECISIONS.md` has a dated row, with a why, for every decision in
      plans 07–09's "Decisions" sections and the memory notes, and marks
      the superseded ones.
- [ ] 7. `docs/plans/README.md` row 10 and `CHECKPOINT.md` say what this
      plan delivered; the PR is open and reviewed; the shareable page
      exists.

## What comes after

The audit's follow-up plan (11), shaped by `AUDIT-2026-09.md`'s last
section: the fixes filed here, in cost order, plus plan 09's hand checks
if they surface anything. Not started in this plan.
