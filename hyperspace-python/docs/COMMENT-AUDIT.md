# Comment audit

The procedure for removing history and justified shortcuts from code,
tests, tools and shaders, so that the code plus ARCHITECTURE, DECISIONS and
DEBT form one source of truth. The rules being enforced are in the root
[`CLAUDE.md`](../../CLAUDE.md) ("What code, tests and fixtures may
contain"). This file says how to apply them. The run is the
`comment-audit` workflow (`.claude/workflows/comment-audit.js`); the
runbook is at the end.

## What you are looking for

Every comment block, docstring, test name, and comment inside a shader
(in a `.glsl` file or a GLSL string in Python) gets exactly one action:

| Action | When | What you do |
|---|---|---|
| **keep** | It states an invariant, a unit, a contract, a non-obvious reason, or a trap, in the present tense, with no history. | Nothing. |
| **rewrite** | It has useful content mixed with provenance or narration. | Keep the content and cut the history. Write it in the present tense, about the code as it is. |
| **delete** | It's pure history ("before plan 87 this was…", "plan 40 D3 asked for…"), restates the code, or narrates to a later reader. | Remove it. |
| **promote: debt** | It admits or argues for a shortcut: "for now", "the proper fix would be", "it was more work to…", "beware…", a paragraph defending why this is allowed. | Record a debt promotion (below). Replace the block with one line, `# DEBT: <slug>` (`// DEBT: <slug>` in GLSL), and leave a short present-tense comment only if the code still needs one to be read. |
| **promote: architecture** | It states how parts relate: who owns what, who may write what, a frame-order or import rule, a cross-module invariant. | Record an architecture promotion. Keep at most a one-line present-tense comment at the site if a reader of this code needs it there. |
| **promote: decision** | It records a choice that is still in force and could have gone another way: "X, not Y, because…". | Record a decision promotion. Keep the present-tense "why" at the site if a reader of this code needs it. |
| **flag** | You can't tell, or acting on it needs more than a prose edit (a test that asserts on a docstring, a user-visible string with a plan number, a fixture holding prose). | Leave the text as it is and record a flag. |

How to tell a real "why" from a justification: a real "why" stays true and
useful if every plan, PR and person named in it is removed, and it doesn't
apologise. A justification only makes sense as an argument with a past
decision or a future reader.

Examples from this codebase:

- `"""The mask passes (plan 39 T2, W1–W3): a mask as its own wire.` →
  rewrite: `"""The mask passes: a mask as its own wire.`
- `It never rides in a picture's alpha (the owner, 2026-10-27: "alpha is
  not a mask").` → rewrite: `It never rides in a picture's alpha.` If the
  choice isn't already in DECISIONS, promote it as a decision.
- `Is pad one whose sensors move no position? The Nintendo pads, for now
  (the owner, 2026-11-04: …)` → keep the contract in the docstring, cut the
  quote and the date. If "for now" hides a real limitation, promote it as
  debt.
- `# ---- plan 16 WP4: the windows open where placement says ----` →
  rewrite: `# ---- windows open where placement says ----`
- `def test_the_smooth_ramp_is_plan_87s_and_the_default` → rename to
  `test_the_smooth_ramp_is_the_default`.

## Hard limits

- **Edit prose only.** That means comments, docstrings, test function names,
  and comments inside GLSL (in `.glsl` files or inside a Python string
  that holds a shader). Never change code, values, ordinary strings,
  fixtures or data.
- **Prove it before you finish:**
  `python3 tools/prose_audit.py verify --base <BASE> <your files>` (run
  from `hyperspace-python/`; paths are relative to it or to the repository
  root). Every file must report `ok` or `renames`. On `strings` or `code`,
  undo that part of your edit.
- **Your files only.** Don't edit files outside your shard, don't edit
  docs, don't run `baseline`, don't commit. Several workers share this
  working tree.
- **Test renames.** Rename a test only to remove provenance from its name.
  The new name says what behaviour is checked and doesn't already exist in
  that file. Record each rename; the integrator applies it to references
  elsewhere. Don't edit other files yourself.
- **Don't invent.** A promotion carries what the text says plus what you
  checked in the code. If you can't confirm it from the code, say so in
  `evidence` and the synthesis step decides.

## The ledger

Each shard writes `.audit/ledger/<shard-id>.json` at the repository root
(the `.audit/` folder is excluded from git):

```json
{
  "shard": "s042",
  "files": ["hyperspace-python/hyperspace/masks.py"],
  "counts": {"keep": 0, "rewrite": 0, "delete": 0, "promote": 0, "flag": 0},
  "promotions": [
    {
      "kind": "debt | architecture | decision",
      "slug": "kebab-case-name (debt: the slug in the `# DEBT:` pointer)",
      "path": "hyperspace-python/hyperspace/masks.py",
      "line": 123,
      "title": "one line",
      "text": "self-contained, present tense: what is true now / the shortcut, the proper fix, its cost",
      "original": "the block as it was, verbatim",
      "evidence": "what in the code confirms it (function names, lines), or 'unconfirmed: …'"
    }
  ],
  "renames": {"test_old_name": "test_new_name"},
  "flags": [{"path": "…", "line": 1, "issue": "…"}]
}
```

Renames also go in `.audit/renames/<shard-id>.json`, as a flat
`{old: new}` object.

## Verification (a second agent per shard)

The verifier gets the shard's files, `BASE`, and the worker's ledger, but
not the worker's reasoning. It reads `git diff <BASE> -- <files>` and
checks:

1. `verify` reports only `ok` or `renames`.
2. **Nothing needed was lost.** Every deleted or shortened block that held
   an invariant, unit, trap or non-obvious reason is either still at the
   site in present tense or in a promotion. The verifier restores anything
   missing, rewritten without history.
3. **Nothing was left behind.** `python3 tools/prose_audit.py count <files>`
   is zero, or each remaining marker is legitimate (for example, a date
   that is data) and listed as a flag. Unmarked justification paragraphs
   are gone too.
4. **The promotions match.** Each promotion says what the original said,
   and a `# DEBT:` pointer exists for every debt promotion.

The verifier fixes in place and writes `.audit/ledger/<shard-id>.verify.json`:
`{"restored": n, "fixed": n, "extra_promotions": [...], "remaining": n, "notes": "…"}`.

## Synthesis

When every shard is done:

- **Renames.** `python3 tools/prose_audit.py renames .audit/renames/*.json`.
  It reports any it skipped as ambiguous; those become flags.
- **DEBT.** Every debt promotion is checked against the code. Duplicates
  (one shortcut seen from several files) merge into one entry, with every
  site listed under **Where**. Entries go into `docs/DEBT.md` in its
  format, and pointer slugs are updated to the merged slug. A "shortcut"
  the code shows is not one (it was fixed later) is dropped, and its
  pointer removed.
- **ARCHITECTURE and DECISIONS.** Each promotion is checked against the
  code and against what the doc already says. It is either already
  covered (drop it), new and true (add it in the doc's own style, in
  present tense, with no plan numbers), or contradicted by the code (the
  code wins: correct the doc and note it in the report). Doc edits stay
  small and are placed where a reader would look.
- **Flags** go to the report for the owner.

## The gate

Run from `hyperspace-python/`:

1. `python3 tools/prose_audit.py verify --base <BASE>` reports no `code`.
2. `uv run ruff check .`
3. The fast tier as CI runs it: `xvfb-run -a -s "-screen 0 1920x1080x24"
   uv run pytest -q --timeout 120`. Any failure is compared against
   `BASE`. A failure the audit caused (usually a test that asserts on a
   docstring's wording) is fixed by restoring the prose, never by
   changing a test's logic, and listed in the report.
4. `python3 tools/prose_audit.py baseline`, then `check`. The baseline may
   only go down.
5. Commit by area (app, tests, tools, shaders, docs), then push the audit
   branch. Don't open a PR unless the owner asked.

## Runbook

**Before the run:**

- The guardrail tools (`tools/prose_audit.py`, `CLAUDE.md`, this file)
  are on the branch you start from.
- The working tree is clean.

**Launch.** Tell Claude, at the repository root, "run the comment audit"
(add "pilot on graph.py" for a pilot). Claude then:

1. runs `cd hyperspace-python && python3 tools/prose_audit.py shards ../.audit/shards.json`;
2. reads that file and calls the `comment-audit` workflow, passing the
   array as `args.shards`. The workflow can't read files itself.

Optional args:

- `branch` (default `audit/comments`)
- `base`: an explicit BASE ref (default: HEAD at launch)
- `model` (default `sonnet`, for workers and verifiers)
- `synthModel` (default `sonnet`)
- `effort`
- `only`: shard ids, labels or file paths, for a pilot
- `sweep` (default `true`): a second pass on shards with markers left
- `gate` (default `true`)

**Size.** About 154 shards. The full run is at most about 490 agents: 175
workers (big files are cut into chunks that run in order), 154 verifiers,
up to 154 sweeps, and a handful for synthesis and the gate. A pilot on
`graph.py` is 15.

**Pilot first.** Run with `only: ["hyperspace/graph.py"]` and read its
ledger and diff before releasing the full run.

**Resume.** If the run stops, relaunch with the same script and args and
`resumeFromRunId`. Finished shards come back from cache.

**Output.**

- The audit branch, committed and pushed.
- `.audit/ledger/` with every decision.
- `.audit/REPORT.md`: counts, the DEBT entries added, the doc changes,
  every flag, and gate results. It is also the workflow's return value.
