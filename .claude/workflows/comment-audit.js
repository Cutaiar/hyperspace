export const meta = {
  name: 'comment-audit',
  description: 'Strip history and justified shortcuts from code, tests, tools and shaders; promote what is still true to DEBT, ARCHITECTURE and DECISIONS',
  whenToUse: 'Only when the owner says to dispatch the comment audit. Procedure and runbook: hyperspace-python/docs/COMMENT-AUDIT.md. args.shards comes from `python3 tools/prose_audit.py shards ../.audit/shards.json`.',
  phases: [
    { title: 'Prepare', detail: 'clean tree, audit branch, BASE' },
    { title: 'Audit', detail: 'one worker per shard (chunks of a big file in order)' },
    { title: 'Verify', detail: 'an independent verifier per shard' },
    { title: 'Sweep', detail: 'a second pass where markers or non-prose edits remain' },
    { title: 'Synthesize', detail: 'renames, promotions checked, DEBT / ARCHITECTURE / DECISIONS' },
    { title: 'Gate', detail: 'verify, ruff, fast tier, baseline, commit, push' },
    { title: 'Strings', detail: 'a separate pass on string literals that hold history, its own commits' },
    { title: 'Report' },
  ],
}

// ---------------------------------------------------------------- args

const A = args || {}
if (!Array.isArray(A.shards) || A.shards.length === 0) {
  throw new Error('args.shards is required: run `python3 tools/prose_audit.py shards ../.audit/shards.json` in hyperspace-python/ and pass the array it wrote')
}
const MODEL = A.model || 'sonnet'
const SYNTH = A.synthModel || 'sonnet'
const BRANCH = A.branch || 'audit/comments'
const EFFORT = A.effort  // undefined: inherit
const SWEEP = A.sweep !== false
const GATE = A.gate !== false
const STRINGS = A.strings !== false
// The comment-auditor type (.claude/agents/) carries only the tools the
// audit needs, so each agent starts with less context. A session that
// started before that file existed can't see it; the probe falls back.
let TYPE = A.agentType === undefined ? 'comment-auditor' : A.agentType
const run = (prompt, opts = {}) => agent(prompt, TYPE ? { ...opts, agentType: TYPE } : opts)

const matches = s => !A.only || A.only.some(o =>
  o === s.id || o === s.label || s.files.some(f => f.path === o || f.path.endsWith('/' + o)))
const SHARDS = A.shards.filter(matches)
if (SHARDS.length === 0) throw new Error(`args.only matched no shard: ${JSON.stringify(A.only)}`)
const dropped = A.shards.length - SHARDS.length
log(`${SHARDS.length} shards${dropped ? ` (pilot: ${dropped} not run)` : ''}, workers on ${MODEL}, synthesis on ${SYNTH}`)

const PROC = 'The procedure is hyperspace-python/docs/COMMENT-AUDIT.md. Read it in full before anything else and follow it exactly; where this prompt and it differ, it wins.'
const fileList = s => s.files.map(f => f.path)
const quoted = paths => paths.map(p => `  ${p}`).join('\n')

// ---------------------------------------------------------------- schemas

const PREP = {
  type: 'object',
  properties: {
    base: { type: 'string' }, branch: { type: 'string' },
    ok: { type: 'boolean' }, notes: { type: 'string' },
  },
  required: ['base', 'branch', 'ok', 'notes'],
}
const WORK = {
  type: 'object',
  properties: {
    keep: { type: 'integer' }, rewrite: { type: 'integer' }, delete: { type: 'integer' },
    promote: { type: 'integer' }, flag: { type: 'integer' }, renames: { type: 'integer' },
    verify_ok: { type: 'boolean', description: 'every file in scope reports ok or renames' },
    remaining: { type: 'integer', description: 'the `prose` figure from `prose_audit.py count` on your files (string-literal markers are the string pass\'s)' },
    notes: { type: 'string' },
  },
  required: ['keep', 'rewrite', 'delete', 'promote', 'flag', 'verify_ok', 'remaining', 'notes'],
}
const CHECKED = {
  type: 'object',
  properties: {
    restored: { type: 'integer' }, fixed: { type: 'integer' }, extra_promotions: { type: 'integer' },
    verify_ok: { type: 'boolean' }, remaining: { type: 'integer', description: 'the `prose` figure from `count`' }, notes: { type: 'string' },
  },
  required: ['restored', 'fixed', 'extra_promotions', 'verify_ok', 'remaining', 'notes'],
}
const BATCHES = {
  type: 'object',
  properties: {
    renamed: { type: 'integer' }, renames_skipped: { type: 'array', items: { type: 'string' } },
    batches: {
      type: 'array',
      items: {
        type: 'object',
        properties: { batch: { type: 'string' }, kind: { type: 'string' }, count: { type: 'integer' } },
        required: ['batch', 'kind', 'count'],
      },
    },
  },
  required: ['renamed', 'renames_skipped', 'batches'],
}
const PROPOSED = {
  type: 'object',
  properties: {
    accepted: { type: 'integer' }, already_covered: { type: 'integer' },
    dropped: { type: 'integer' }, contradicted: { type: 'integer' }, notes: { type: 'string' },
  },
  required: ['accepted', 'already_covered', 'dropped', 'contradicted', 'notes'],
}
const APPLIED = {
  type: 'object',
  properties: { added: { type: 'integer' }, changed: { type: 'integer' }, notes: { type: 'string' } },
  required: ['added', 'changed', 'notes'],
}
const GATED = {
  type: 'object',
  properties: {
    verify_ok: { type: 'boolean' }, ruff_ok: { type: 'boolean' },
    tests: { type: 'string', description: 'passed/failed/skipped, and failures vs BASE' },
    audit_caused_failures_fixed: { type: 'integer' },
    markers_before: { type: 'integer' }, markers_after: { type: 'integer' },
    commits: { type: 'array', items: { type: 'string' } },
    pushed: { type: 'boolean' }, notes: { type: 'string' },
  },
  required: ['verify_ok', 'ruff_ok', 'tests', 'markers_before', 'markers_after', 'commits', 'pushed', 'notes'],
}

// ---------------------------------------------------------------- prepare

phase('Prepare')
if (TYPE) {
  const probe = await agent('Return ok=true.', {
    phase: 'Prepare', label: `probe ${TYPE}`, agentType: TYPE, effort: 'low',
    schema: { type: 'object', properties: { ok: { type: 'boolean' } }, required: ['ok'] },
  })
  if (!probe) { log(`agent type ${TYPE} unavailable here: using the default workflow agent`); TYPE = null }
}
const prep = await run(`Prepare the working tree for the comment audit. Work from the repository root.

1. \`git status --porcelain\` must show nothing outside \`.audit/\`. If it shows anything else, set ok=false, list it in notes, and stop.
2. Add the line \`.audit/\` to \`.git/info/exclude\` if it isn't there. Run \`mkdir -p .audit/ledger .audit/renames .audit/promotions .audit/proposals\`.
3. ${A.base ? `BASE is ${A.base}: confirm it with \`git rev-parse ${A.base}\`.` : 'BASE is `git rev-parse HEAD`, taken before any checkout.'}
4. Branch: if \`${BRANCH}\` doesn't exist, run \`git checkout -b ${BRANCH}\`. If it exists, check it out. It must contain BASE (\`git merge-base --is-ancestor BASE HEAD\`).
5. From hyperspace-python/, run \`python3 tools/prose_audit.py check\`. It must pass.

Return the full BASE sha, the branch, ok, and short notes.`,
  { phase: 'Prepare', label: 'prepare', schema: PREP, model: SYNTH, effort: 'low' })
if (!prep || !prep.ok) throw new Error(`prepare failed: ${prep ? prep.notes : 'no result'}`)
const BASE = prep.base
log(`BASE ${BASE.slice(0, 10)} on ${prep.branch}`)

// ---------------------------------------------------------------- per shard

function workerPrompt(shard, part) {
  const lid = part ? `${shard.id}-c${part.k}` : shard.id
  const f0 = shard.files[0].path
  const scope = part
    ? `Your scope is part ${part.k + 1} of ${part.n} of ${f0}: the top-level statements that were at lines ${part.a}–${part.b} in BASE. See them with \`git show ${BASE}:${f0} | sed -n '${part.a},${part.b}p'\`, then find the same definitions in the current file. Earlier parts may already be edited, so line numbers shift. Don't touch anything outside your part. Parts run one after another, never at the same time.`
    : `Your scope is these files, in full:\n${quoted(fileList(shard))}`
  return `You are a worker in the comment audit, shard ${shard.id} (${shard.label}). ${PROC}

BASE = ${BASE}
${scope}

Do this:
1. Go through every comment block, docstring, test function name, and shader comment (in .glsl files, or GLSL inside a Python string) in your scope. Give each one exactly one action from the procedure's table and carry it out. Edit prose only.
2. Write your ledger to \`.audit/ledger/${lid}.json\` and your renames to \`.audit/renames/${lid}.json\` (\`{}\` if none), both at the repository root, in the procedure's format. Every promotion needs \`original\` copied verbatim and honest \`evidence\`.
3. From hyperspace-python/, run \`python3 tools/prose_audit.py verify --base ${BASE} ${fileList(shard).join(' ')}\`. Undo whatever makes a file report \`strings\` or \`code\`, then run it again.
4. Run \`python3 tools/prose_audit.py count ${fileList(shard).join(' ')}\`. Every marker its \`prose\` figure still counts in your scope is either removed or listed as a flag with a reason. Markers \`in_strings\` are left for the string pass; don't flag them.

Don't edit other files, don't commit, and don't run \`baseline\`. Return the counts.`
}

function verifierPrompt(shard) {
  return `You are the independent verifier for comment-audit shard ${shard.id} (${shard.label}). ${PROC} Follow its "Verification" section. You didn't write these edits; judge them from the diff and the code, not from anyone's explanation.

BASE = ${BASE}
Files:
${quoted(fileList(shard))}
Worker ledgers: \`.audit/ledger/${shard.id}.json\` and \`.audit/ledger/${shard.id}-c*.json\` (whichever exist).

1. Read \`git diff ${BASE} -- <files>\` in full.
2. Run checks 1–4 from the procedure. Fix problems in place, prose only: restore any invariant, unit, trap or non-obvious reason that was lost (in present tense, with no history); finish what was left behind; correct promotions that misstate their original. Add promotions the worker missed as \`extra_promotions\`.
3. Run \`verify\` and \`count\` again on the files, from hyperspace-python/.
4. Write \`.audit/ledger/${shard.id}.verify.json\` in the procedure's format.

Don't edit files outside this shard, and don't commit. Return the counts.`
}

function sweepPrompt(shard, v) {
  return `Second pass on comment-audit shard ${shard.id} (${shard.label}). ${PROC}

BASE = ${BASE}
Files:
${quoted(fileList(shard))}
After the verifier: verify_ok=${v ? v.verify_ok : 'unknown'}, remaining markers=${v ? v.remaining : 'unknown'}. Verifier notes: ${v ? v.notes : '(verifier did not return)'}

Get every file to report \`ok\` or \`renames\` under \`verify --base ${BASE}\`, undoing any non-prose edit. Then remove each marker \`count\`'s \`prose\` figure still reports, or record it as a flag with a reason (\`in_strings\` markers belong to the string pass). Add anything new to \`.audit/ledger/${shard.id}.sweep.json\` (same format, with \`promotions\`, \`renames\` and \`flags\`), and add new renames to \`.audit/renames/${shard.id}-sweep.json\`. Prose only, these files only, no commit. Return the counts as the verifier does.`
}

const results = await pipeline(
  SHARDS,
  async (shard) => {
    const f0 = shard.files[0]
    const opts = { phase: 'Audit', schema: WORK, model: MODEL, effort: EFFORT }
    if (shard.files.length === 1 && f0.chunks && f0.chunks.length > 1) {
      const parts = []
      for (let k = 0; k < f0.chunks.length; k++) {
        const [a, b] = f0.chunks[k]
        parts.push(await run(workerPrompt(shard, { k, n: f0.chunks.length, a, b }),
          { ...opts, label: `audit ${shard.label} ${k + 1}/${f0.chunks.length}` }))
      }
      return parts
    }
    return [await run(workerPrompt(shard), { ...opts, label: `audit ${shard.label}` })]
  },
  async (work, shard) => {
    const v = await run(verifierPrompt(shard),
      { phase: 'Verify', label: `verify ${shard.label}`, schema: CHECKED, model: MODEL, effort: EFFORT })
    return { work, v }
  },
  async ({ work, v }, shard) => {
    let sweep = null
    if (SWEEP && (!v || !v.verify_ok || v.remaining > 0)) {
      sweep = await run(sweepPrompt(shard, v),
        { phase: 'Sweep', label: `sweep ${shard.label}`, schema: CHECKED, model: MODEL, effort: EFFORT })
    }
    return { id: shard.id, label: shard.label, work, v, sweep }
  },
)

// ---------------------------------------------------------------- tallies

const done = results.filter(Boolean)
const failed = SHARDS.filter(s => !done.some(r => r.id === s.id)).map(s => s.label)
const sum = (rows, k) => rows.reduce((n, r) => n + ((r && r[k]) || 0), 0)
const works = done.flatMap(r => r.work || []).filter(Boolean)
const final = r => r.sweep || r.v
const unresolved = done.filter(r => { const f = final(r); return !f || !f.verify_ok }).map(r => r.label)
const tallies = {
  shards: SHARDS.length, shards_failed: failed, shards_not_verify_ok: unresolved,
  keep: sum(works, 'keep'), rewrite: sum(works, 'rewrite'), delete: sum(works, 'delete'),
  promote: sum(works, 'promote'), flag: sum(works, 'flag'),
  restored_by_verifiers: sum(done.map(r => r.v), 'restored'),
  extra_promotions: sum(done.map(r => r.v), 'extra_promotions') + sum(done.map(r => r.sweep), 'extra_promotions'),
  swept: done.filter(r => r.sweep).length,
  markers_left_in_shards: done.reduce((n, r) => n + ((final(r) && final(r).remaining) || 0), 0),
}
log(`audited: ${JSON.stringify(tallies)}`)
if (failed.length) log(`not finished (agent died or skipped): ${failed.join(', ')}`)
if (unresolved.length) log(`still reporting non-prose edits: ${unresolved.join(', ')}; the gate must clear them`)

// ---------------------------------------------------------------- synthesize

phase('Synthesize')
const gathered = await run(`Comment audit, synthesis step 1. ${PROC} Follow its "Synthesis" section. Work from hyperspace-python/.

1. Run \`python3 tools/prose_audit.py renames ../.audit/renames/*.json\` (if there are no files, nothing was renamed). Report how many names were renamed. List each skipped one as "old -> new: reason".
2. Run \`python3 tools/prose_audit.py promotions ../.audit\` and return its JSON batch list unchanged.`,
  { phase: 'Synthesize', label: 'renames + gather', schema: BATCHES, model: SYNTH, effort: 'low' })
const batches = (gathered && gathered.batches) || []
log(`${batches.length} promotion batches: ${batches.map(b => `${b.batch}(${b.count})`).join(' ')}`)

const DOC = {
  debt: 'hyperspace-python/docs/DEBT.md',
  architecture: 'hyperspace-python/docs/ARCHITECTURE.md',
  decision: 'hyperspace-python/docs/DECISIONS.md',
}

const checked = await parallel(batches.map(b => () => run(
  `Comment audit, synthesis: check one batch of ${b.kind} promotions against the code. ${PROC} Follow its "Synthesis" section.

Batch: \`.audit/promotions/${b.batch}.json\` (${b.count} items). Target doc: ${DOC[b.kind] || '(unknown kind: report each item as a flag)'}.

For each item:
- Read the code at \`path\`/\`line\`, and wherever the evidence points.
- Read what the target doc already says on the subject. For decisions, also look for the row in DECISIONS.md.
- Classify it as accepted (new and true now), already_covered, dropped (not true of the code now, e.g. a shortcut later fixed), or contradicted (the doc says otherwise and the code agrees with the item).

Write \`.audit/proposals/${b.batch}.md\`:
- For each accepted item, the exact text to add, in the target doc's style and format (DEBT entries in DEBT.md's format, with every site under **Where**), plus the heading it belongs under.
- For each contradicted item, the doc correction.
- For each dropped debt item, the \`# DEBT: <slug>\` pointer sites to remove.
- A one-line reason for every item.

Edit nothing else. Return the counts.`,
  { phase: 'Synthesize', label: `check ${b.batch}`, schema: PROPOSED, model: SYNTH, effort: EFFORT })))
const checkedOk = checked.filter(Boolean)

const kinds = [...new Set(batches.map(b => b.kind))].filter(k => DOC[k])
const applied = await parallel(kinds.map(kind => () => run(
  `Comment audit, synthesis: apply the checked ${kind} proposals to ${DOC[kind]}. ${PROC}

Proposals: \`.audit/proposals/${kind}-*.md\`. You are the only agent editing ${DOC[kind]}.
- Merge duplicates across batches: one shortcut or one rule seen from several files is one entry.
- Keep the doc's existing structure, voice and numbering. ${kind === 'decision' ? 'DECISIONS rows are numbered; `tests/test_doc_numbers.py` checks that numbers are unique, so take the next free numbers.' : ''}${kind === 'architecture' ? 'ARCHITECTURE.html is maintained alongside the Markdown: mirror each change into it where it covers the same section.' : ''}${kind === 'debt' ? 'Where entries merge, update every `# DEBT: <slug>` pointer in the code to the merged slug, and remove pointers for dropped items. Pointers are comments, so `verify` stays ok.' : ''}
- No plan numbers, rows, PRs, dates or people in what you add. Write in the present tense.
Return the counts.`,
  { phase: 'Synthesize', label: `apply ${kind}`, schema: APPLIED, model: SYNTH, effort: EFFORT })))

// ---------------------------------------------------------------- gate

phase('Gate')
let gate = null
if (GATE) {
  gate = await run(`Comment audit: the gate. ${PROC} Follow its "The gate" section exactly. BASE = ${BASE}, branch ${prep.branch}.

These shards still reported non-prose edits after their sweep, and must be cleared first: ${unresolved.length ? unresolved.join(', ') : 'none'}.

1. From hyperspace-python/, run \`python3 tools/prose_audit.py verify --base ${BASE}\`. Undo any edit it reports as \`code\` or \`strings\` (keep the prose part where you can).
2. Run \`uv run ruff check .\`.
3. Run the fast tier as CI does. Compare failures against BASE: \`git stash\` won't work cleanly here, so use \`git worktree add ../../hyperspace-audit-base ${BASE}\` (outside the repository, so ruff and pytest here don't see it) and run the failing tests there with this checkout's interpreter (\`../../hyperspace/hyperspace-python/.venv/bin/python -m pytest\` from its hyperspace-python/, adjusting the path to where the repository really is). Fix every audit-caused failure by restoring prose. Never change a test's logic. List each one.
4. Record markers_before as the total in \`git show ${BASE}:hyperspace-python/tools/prose_baseline.json\` (the sum of all marker counts). Run \`python3 tools/prose_audit.py baseline\` and \`check\`, and record markers_after.
5. Commit by area, in separate commits: app (hyperspace/), tests (tests/), tools (tools/), shaders (*.glsl), other code files, docs (DEBT, ARCHITECTURE, DECISIONS, renamed references) plus the baseline. Message style: an imperative summary line, then a short body. End each message with the repository's attribution lines from the session's system reminder, if there are any. Then run \`git push -u origin ${prep.branch}\`, retrying network errors up to 4 times. Don't open a PR.
Remove the base worktree when done (\`git worktree remove ../../hyperspace-audit-base --force\`). Return the results.`,
    { phase: 'Gate', label: 'gate', schema: GATED, model: SYNTH, effort: EFFORT })
}

// ---------------------------------------------------------------- strings

const SLIST = {
  type: 'object',
  properties: {
    strbase: { type: 'string' },
    files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, markers: { type: 'integer' } }, required: ['path', 'markers'] } },
  },
  required: ['strbase', 'files'],
}
const SWORK = {
  type: 'object',
  properties: {
    strings_changed: { type: 'integer' }, left_as_is: { type: 'integer' },
    verify_ok: { type: 'boolean', description: 'every file reports ok or strings, never code' },
    remaining: { type: 'integer', description: 'the `in_strings` figure from `count`' }, notes: { type: 'string' },
  },
  required: ['strings_changed', 'left_as_is', 'verify_ok', 'remaining', 'notes'],
}
let strings = null
if (STRINGS && GATE && gate && gate.pushed) {
  phase('Strings')
  const listed = await run(`Comment audit, string pass: list the work. ${PROC} Its "The string pass" section.
From hyperspace-python/: return \`git rev-parse HEAD\` as strbase, and the JSON that \`python3 tools/prose_audit.py string-markers\` prints, unchanged, as files.`,
    { phase: 'Strings', label: 'strings list', schema: SLIST, model: SYNTH, effort: 'low' })
  const STRBASE = listed && listed.strbase
  // a partial run (args.only) changes strings only in the files whose prose it audited
  const inRun = new Set(SHARDS.flatMap(sh => sh.files.map(f => f.path)))
  const sfiles = ((listed && listed.files) || []).filter(f => !A.only || inRun.has(f.path))
  // shards of up to 6 files or about 30 markers; a file is never split
  const sshards = []
  for (const f of sfiles) {
    const last = sshards[sshards.length - 1]
    if (!last || last.files.length >= 6 || last.markers + f.markers > 30) sshards.push({ files: [], markers: 0 })
    sshards[sshards.length - 1].files.push(f.path)
    sshards[sshards.length - 1].markers += f.markers
  }
  sshards.forEach((x, i) => { x.id = `str${String(i).padStart(2, '0')}`; x.label = `${x.files[0].replace('hyperspace-python/', '')}${x.files.length > 1 ? ` +${x.files.length - 1}` : ''}` })
  log(`string pass: ${sfiles.length} files, ${sfiles.reduce((n, f) => n + f.markers, 0)} markers, ${sshards.length} shards, from ${STRBASE ? STRBASE.slice(0, 10) : '?'}`)

  const sres = STRBASE ? await pipeline(
    sshards,
    sh => run(`Comment audit, string pass, shard ${sh.id}. ${PROC} Follow its "The string pass" section.

STRBASE = ${STRBASE}
Files:
${quoted(sh.files)}

Edit only string literals that hold provenance or narration, and only to remove it, keeping every message's meaning. Leave a string as it is when the history is part of what it means, and say why in your notes. Prove it: \`python3 tools/prose_audit.py verify --base ${STRBASE} <files>\` must report \`ok\` or \`strings\` for every file, never \`code\`. Then run \`count\`. Write \`.audit/ledger/${sh.id}.json\` with each changed string as [path, line, before, after]. Don't commit.`,
      { phase: 'Strings', label: `strings ${sh.label}`, schema: SWORK, model: MODEL, effort: EFFORT }),
    (w, sh) => run(`Independent verifier, comment-audit string pass, shard ${sh.id}. ${PROC} Its "The string pass" section. Judge from the diff, not from anyone's account.

STRBASE = ${STRBASE}
Files:
${quoted(sh.files)}

Read \`git diff ${STRBASE} -- <files>\` and \`verify --base ${STRBASE}\`'s list of string pairs. Each change must remove only provenance or narration and keep the message's meaning. Revert anything else. Search tests/ for any test that matches a changed message's old text (\`grep -rn\` on a distinctive fragment) and list each in notes: the gate updates its expected string. Write \`.audit/ledger/${sh.id}.verify.json\`. Don't commit.`,
      { phase: 'Strings', label: `verify strings ${sh.label}`, schema: SWORK, model: MODEL, effort: EFFORT }),
  ) : []

  const sgate = STRBASE ? await run(`Comment audit, string pass: the gate. ${PROC} "The string pass" and "The gate" sections. STRBASE = ${STRBASE} (the prose commits), branch ${prep.branch}.

Verifier notes, including tests that match changed messages: ${JSON.stringify(sres.filter(Boolean).map(r => r.notes))}

1. From hyperspace-python/, run \`python3 tools/prose_audit.py verify --base ${STRBASE}\`. No file may report \`code\`.
2. Run \`uv run ruff check .\`, then the fast tier as CI does. A failure caused by a changed message is fixed in the test: update its expected string to the new text, or, when the test keys on the history itself (filters or recognises messages by a plan number), change the test to recognise them another way, such as a predicate or constant the module exports. Don't put the history back in the message to satisfy a test. Change app code only in its strings, plus any such small exported predicate or constant. List every test you changed beyond an expected string. Revert a message only when its test can't be fixed either way.
3. Run \`python3 tools/prose_audit.py baseline\` and \`check\`.
4. Commit by area (app, tests, tools), with summary lines that begin "Strings:", so the string edits are reviewable on their own. Then run \`git push -u origin ${prep.branch}\`, retrying network errors up to 4 times. Don't open a PR.
Return the gate results.`, { phase: 'Strings', label: 'strings gate', schema: GATED, model: SYNTH, effort: EFFORT }) : null
  const sdone = sres.filter(Boolean)
  strings = {
    files: sfiles.length, shards: sshards.length,
    changed: sdone.reduce((n, r) => n + (r.strings_changed || 0), 0),
    left_as_is: sdone.reduce((n, r) => n + (r.left_as_is || 0), 0),
    gate: sgate,
  }
} else if (STRINGS) {
  log('string pass skipped: it runs only after the prose gate has committed and pushed')
}

phase('Report')
const report = await run(`Comment audit: write the report. ${PROC}

Write \`.audit/REPORT.md\` at the repository root for the owner, and return its full text. Base it on the ledgers in \`.audit/ledger/\`, the proposals, \`git log ${BASE}..HEAD\`, and these figures:

tallies: ${JSON.stringify(tallies)}
renames skipped: ${JSON.stringify((gathered && gathered.renames_skipped) || [])}
promotion checks: ${JSON.stringify(checkedOk)}
doc edits: ${JSON.stringify(applied.filter(Boolean))}
gate: ${JSON.stringify(gate)}${GATE ? '' : ' (gate skipped by args: nothing committed)'}
string pass: ${JSON.stringify(strings)}
${dropped ? `pilot: ${dropped} shards were not run` : ''}

Sections:
1. Outcome: markers before and after, lines of prose removed (\`git diff --shortstat\`), and test results.
2. New DEBT entries, one line each.
3. ARCHITECTURE and DECISIONS changes, including any corrections where the code contradicted the doc.
4. Every flag, grouped by kind, with path:line. These are the owner's decisions.
5. The string pass: strings changed, strings left as they are and why, and test expectations updated. List its commits separately.
6. Anything unfinished: failed shards, unresolved verify results, skipped renames.
Keep it plain and factual. Don't list plan numbers.`,
  { phase: 'Report', label: 'report', model: SYNTH, effort: 'low' })

return { base: BASE, branch: prep.branch, agentType: TYPE || 'default', tallies, gate, strings, report }
