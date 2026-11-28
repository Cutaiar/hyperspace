"""Keep project history out of the code, and keep fixtures from growing unseen.

Code, tests and tools describe what the code is. Where a change came from
(plan numbers, register rows, PR numbers) belongs in git history and
`docs/plans/`; a shortcut taken on purpose belongs in `docs/DEBT.md`. See
the root `CLAUDE.md`.

    python3 tools/prose_audit.py check       # CI: fail if any file got worse
    python3 tools/prose_audit.py baseline    # rewrite the baseline (only ever lower it)
    python3 tools/prose_audit.py inventory OUT.jsonl   # every comment/docstring block, tagged

`check` is a ratchet. The baseline holds today's counts per file, so
existing debt does not fail CI, but no file may gain a marker, a new file
starts at zero, and a large fixture may not grow or appear without an entry.
Cleaning a file lowers its count; run `baseline` to lock the gain in.

Run from `hyperspace-python/`. Stdlib only, so CI needs no sync to run it.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).resolve().parent / "prose_baseline.json"

# Code files scanned for markers, by suffix. Docs (.md) are not scanned:
# they may cite history; code may not.
CODE_SUFFIXES = {".py", ".glsl", ".ts", ".tsx", ".js", ".mjs", ".swift",
                 ".sh", ".yml", ".yaml", ".toml", ".css", ".html", ".h"}
SKIP_PREFIXES = ("hyperspace-python/docs/", "prototypes/")
SKIP_FILES = {"hyperspace-python/tools/prose_audit.py"}

# Provenance: a pointer into the project's history.
PROVENANCE = re.compile(
    r"""(?ix)
      \bplans?[\s_-]*\#?\d{1,3}[a-z]?s?\b       # plan 90, plan_87s, plans 24
    | \bplans/\d                                 # docs/plans/40-patches.md
    | \brows?\s+\d{2,4}\b                        # row 870 (the decision register)
    | \bPR\s*\#?\d{2,4}\b                        # PR #289
    | (?<![\w/&])\#\d{3,4}\b(?!\s*[0-9a-f]{3})   # (#524) — not a colour
    | \b(?:WP|wave\s)\d+\b                       # WP4, wave 3
    | \baudit\s+[A-Z]\d+\b                       # audit A10
    | \b[DHNT]\d{1,2}\b(?=[^\n]{0,40}\bplan\b)   # D2 … plan 44
    | \b20\d\d-[01]\d-[0-3]\d\b                 # 2026-10-27 (who said what, when)
    """
)

# Narration: notes to the next author, or a shortcut excused in place.
NARRATION = re.compile(
    r"""(?ix)
      \b(?:future|next|later|other)\s+(?:agents?|sessions?|runs?|readers?)\b
    | \bbeware\b
    | \bfor\s+now\b
    | \bhack(?:y|ed|s)?\b
    | \bworkaround\b
    | \bkludge\b
    | \bcompromise[sd]?\b
    | \b(?:TODO|FIXME|XXX)\b
    """
)

FIXTURE_DIRS = ("hyperspace-python/tests/fixtures/", "hyperspace-python/tests/golden/")
FIXTURE_LIMIT = 256 * 1024  # bytes; a fixture above this needs a baseline entry


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO)
    return [p for p in out.decode().split("\0") if p]


def scanned(path: str) -> bool:
    return (Path(path).suffix in CODE_SUFFIXES
            and not path.startswith(SKIP_PREFIXES)
            and path not in SKIP_FILES)


def py_text_segments(src: str):
    """(kind, start_line, text) for each comment, string and identifier."""
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            yield "comment", tok.start[0], tok.string
        elif tok.type == tokenize.STRING or tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            yield "string", tok.start[0], tok.string
        elif tok.type == tokenize.NAME:
            yield "name", tok.start[0], tok.string


def count_markers(path: str) -> Counter:
    src = (REPO / path).read_text(encoding="utf-8", errors="replace")
    c: Counter = Counter()
    if path.endswith(".py"):
        try:
            segs = list(py_text_segments(src))
        except (tokenize.TokenError, SyntaxError, IndentationError):
            segs = [("comment", 1, src)]
        for kind, _, text in segs:
            if kind == "name":
                # identifiers: only plan numbers (test_..._plan_87s_...)
                c["provenance"] += len(re.findall(r"(?i)(?:^|_)plans?_?\d{1,3}", text))
            else:
                c["provenance"] += len(PROVENANCE.findall(text))
                c["narration"] += len(NARRATION.findall(text))
    else:
        c["provenance"] += len(PROVENANCE.findall(src))
        c["narration"] += len(NARRATION.findall(src))
    return +c


def measure() -> dict:
    files = tracked_files()
    markers = {}
    for p in files:
        if scanned(p) and (REPO / p).is_file():
            c = count_markers(p)
            if c:
                markers[p] = dict(sorted(c.items()))
    fixtures = {}
    for p in files:
        if p.startswith(FIXTURE_DIRS) and (REPO / p).is_file():
            size = (REPO / p).stat().st_size
            if size > FIXTURE_LIMIT:
                fixtures[p] = size
    return {"markers": dict(sorted(markers.items())),
            "fixtures": dict(sorted(fixtures.items()))}


def check() -> int:
    base = json.loads(BASELINE.read_text())
    now = measure()
    problems = []
    for path, counts in now["markers"].items():
        was = base["markers"].get(path, {})
        for kind, n in counts.items():
            if n > was.get(kind, 0):
                problems.append(f"{path}: {kind} {was.get(kind, 0)} -> {n}")
    for path, size in now["fixtures"].items():
        was = base["fixtures"].get(path)
        if was is None:
            problems.append(f"{path}: new fixture of {size // 1024} KB (limit {FIXTURE_LIMIT // 1024} KB)")
        elif size > was:
            problems.append(f"{path}: fixture grew {was // 1024} KB -> {size // 1024} KB")
    if problems:
        print("prose audit: these files got worse than the baseline:\n")
        print("\n".join("  " + p for p in problems))
        print(
            "\nCode, tests and tools say what the code is, not where it came from."
            "\n- provenance (plan N, row N, PR #N): drop it; git log and docs/plans/ hold history."
            "\n- narration (for now, workaround, future agents, TODO): if a shortcut is real,"
            "\n  add an entry to hyperspace-python/docs/DEBT.md and leave at most a one-line"
            "\n  `# DEBT: <slug>` pointer in the code. (The pointer is not counted.)"
            "\n- large fixture: generate it from a tool in a test, or shrink it."
            "\nSee CLAUDE.md at the repository root."
        )
        return 1
    lowered = sum(
        1 for p, c in base["markers"].items()
        if any(n < c.get(k, 0) for k, n in now["markers"].get(p, {}).items())
        or p not in now["markers"]
    )
    print(f"prose audit: ok ({len(now['markers'])} files with markers"
          + (f"; {lowered} cleaner than the baseline, run `baseline` to lock in" if lowered else "") + ")")
    return 0


def baseline() -> int:
    now = measure()
    if BASELINE.exists():
        base = json.loads(BASELINE.read_text())
        raised = [p for p, c in now["markers"].items()
                  if any(n > base["markers"].get(p, {}).get(k, 0) for k, n in c.items())]
        if raised and "--allow-raise" not in sys.argv:
            print("refusing to raise the baseline for:\n  " + "\n  ".join(raised)
                  + "\n(pass --allow-raise only with the owner's agreement)")
            return 1
    BASELINE.write_text(json.dumps(now, indent=1) + "\n")
    total = sum(sum(c.values()) for c in now["markers"].values())
    print(f"baseline: {total} markers in {len(now['markers'])} files, {len(now['fixtures'])} large fixtures")
    return 0


def py_blocks(path: str):
    """Comment runs and docstrings of a Python file, as audit ledger rows."""
    src = (REPO / path).read_text(encoding="utf-8", errors="replace")
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return
    run: list[tuple[int, str]] = []
    prev_sig = None  # previous significant token type
    code_lines = {t.start[0] for t in toks if t.type not in (
        tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
        tokenize.DEDENT, tokenize.ENDMARKER)}

    def flush():
        if run:
            yield {"kind": "comment", "line": run[0][0], "end": run[-1][0],
                   "text": "\n".join(t for _, t in run)}
            run.clear()

    for t in toks:
        if t.type == tokenize.COMMENT:
            if run and t.start[0] != run[-1][0] + 1:
                yield from flush()
            trailing = t.start[0] in code_lines
            if trailing:
                yield from flush()
                yield {"kind": "trailing", "line": t.start[0], "end": t.start[0], "text": t.string}
            else:
                run.append((t.start[0], t.string))
        elif t.type == tokenize.STRING and prev_sig in (None, tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT):
            yield from flush()
            yield {"kind": "docstring", "line": t.start[0], "end": t.end[0], "text": t.string}
        elif t.type not in (tokenize.NL,):
            if t.type not in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                yield from flush()
        if t.type not in (tokenize.NL, tokenize.COMMENT):
            prev_sig = t.type
    yield from flush()


def inventory(out: str) -> int:
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for p in tracked_files():
            if not (p.endswith(".py") and scanned(p)):
                continue
            for b in py_blocks(p):
                text = b["text"]
                b["file"] = p
                b["lines"] = b["end"] - b["line"] + 1
                b["provenance"] = len(PROVENANCE.findall(text))
                b["narration"] = len(NARRATION.findall(text))
                b["tag"] = ("narration" if b["narration"] else
                            "provenance" if b["provenance"] else "plain")
                f.write(json.dumps(b, ensure_ascii=False) + "\n")
                n += 1
    print(f"inventory: {n} blocks -> {out}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "check":
        return check()
    if len(argv) >= 2 and argv[1] == "baseline":
        return baseline()
    if len(argv) >= 3 and argv[1] == "inventory":
        return inventory(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
