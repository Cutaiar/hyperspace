"""Keep project history out of the code, and keep fixtures from growing unseen.

Code, tests and tools describe what the code is. Where a change came from
(plan numbers, register rows, PR numbers) belongs in git history and
`docs/plans/`; a shortcut taken on purpose belongs in `docs/DEBT.md`. See
the root `CLAUDE.md`.

    python3 tools/prose_audit.py check       # CI: fail if any file got worse
    python3 tools/prose_audit.py baseline    # rewrite the baseline (only ever lower it)
    python3 tools/prose_audit.py inventory OUT.jsonl   # every comment/docstring block, tagged

The comment audit (docs/COMMENT-AUDIT.md) also uses:

    python3 tools/prose_audit.py shards OUT.json [--target N]  # the audit's work units
    python3 tools/prose_audit.py verify [--base REF] [FILE...] # did an edit touch only prose?
    python3 tools/prose_audit.py renames RENAMES.json...       # apply test renames repo-wide
    python3 tools/prose_audit.py count FILE...                 # markers left in these files
    python3 tools/prose_audit.py promotions AUDIT_DIR          # ledgers -> batches to check

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
SKIP_PREFIXES = ("hyperspace-python/docs/", "prototypes/", "hyperspace-python/vendor/")
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


# ---------------------------------------------------------------- shards

AUDIT_AREAS = ("hyperspace-python/hyperspace/", "hyperspace-python/tests/", "hyperspace-python/tools/")


def _prose_lines(path: str) -> int:
    return sum(b["end"] - b["line"] + 1 for b in py_blocks(path))


def _chunks(path: str, target: int) -> list[list[int]]:
    """Split a large file at top-level statements into ranges of about
    `target` prose lines each. Returns [[first_line, last_line], ...]."""
    import ast
    src = (REPO / path).read_text(encoding="utf-8", errors="replace")
    n_lines = src.count("\n") + 1
    try:
        starts = [node.lineno for node in ast.parse(src).body]
    except SyntaxError:
        return [[1, n_lines]]
    # a decorator or comment above a def belongs with it
    starts = sorted({1, *[max(1, s) for s in starts]})
    prose_at = Counter()
    for b in py_blocks(path):
        prose_at[b["line"]] += b["end"] - b["line"] + 1
    bounds, acc, first = [], 0, 1
    for i, s in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else n_lines + 1
        acc += sum(v for k, v in prose_at.items() if s <= k < nxt)
        if acc >= target and nxt <= n_lines:
            bounds.append([first, nxt - 1])
            first, acc = nxt, 0
    bounds.append([first, n_lines])
    return bounds


def shards(out: str, target: int) -> int:
    """Work units for the comment audit. Python files in the audit areas are
    packed by directory into shards of about `target` prose lines; a file
    over 1.5 x target is its own shard, cut into ordered chunks. Other code
    files with markers form one more shard."""
    files = [p for p in tracked_files()
             if p.endswith(".py") and p.startswith(AUDIT_AREAS) and scanned(p)
             and (REPO / p).is_file()]
    files.sort()
    units, cur, cur_n, cur_dir = [], [], 0, None

    def close():
        nonlocal cur, cur_n
        if cur:
            units.append({"files": [{"path": f, "chunks": None} for f in cur], "prose_lines": cur_n})
        cur, cur_n = [], 0

    for f in files:
        n = _prose_lines(f)
        d = f.rsplit("/", 1)[0]
        if n > 1.5 * target:
            units.append({"files": [{"path": f, "chunks": _chunks(f, target)}], "prose_lines": n})
            continue
        if d != cur_dir or cur_n + n > target:
            close()
            cur_dir = d
        cur.append(f)
        cur_n += n
    close()
    base = json.loads(BASELINE.read_text())["markers"]
    shaders = [p for p in tracked_files()
               if p.startswith("hyperspace-python/hyperspace/") and p.endswith(".glsl")]
    other = sorted({*shaders, *(p for p in base
                                if not (p.endswith(".py") and p.startswith(AUDIT_AREAS)))}
                   - SKIP_FILES)
    for i in range(0, len(other), 15):
        units.append({"files": [{"path": p, "chunks": None} for p in other[i:i + 15]],
                      "prose_lines": 0})
    for i, u in enumerate(units):
        first = u["files"][0]["path"].replace("hyperspace-python/", "")
        u["id"] = f"s{i:03d}"
        u["label"] = first if len(u["files"]) == 1 else f"{first} +{len(u['files']) - 1}"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(units, indent=1) + "\n")
    agents = sum(len(u["files"][0]["chunks"] or [0]) for u in units)
    print(f"shards: {len(units)} units, {agents} worker agents, "
          f"{sum(u['prose_lines'] for u in units)} prose lines -> {out}")
    return 0


# ---------------------------------------------------------------- verify

def _strip_docstrings(tree):
    import ast
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _test_names(tree) -> list[str]:
    import ast
    return [n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")]


def _normalise(tree, names: bool, strings: bool):
    import ast
    for n in ast.walk(tree):
        if names and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_"):
            n.name = "test_"
        if strings and isinstance(n, ast.Constant) and isinstance(n.value, str):
            n.value = ""
    return ast.dump(tree, include_attributes=False)


def _strs(tree) -> list[str]:
    import ast
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _verify_py(old: str, new: str) -> dict:
    import ast
    try:
        a, b = _strip_docstrings(ast.parse(old)), _strip_docstrings(ast.parse(new))
    except SyntaxError as e:
        return {"status": "code", "detail": f"does not parse: {e}"}
    if ast.dump(a) == ast.dump(b):
        return {"status": "ok"}
    renames = {x: y for x, y in zip(_test_names(a), _test_names(b)) if x != y}
    if len(_test_names(a)) != len(_test_names(b)):
        return {"status": "code", "detail": "a test was added or removed"}
    if _normalise(a, True, False) == _normalise(b, True, False):
        return {"status": "renames", "renames": renames}
    a, b = _strip_docstrings(ast.parse(old)), _strip_docstrings(ast.parse(new))
    sa, sb = _strs(a), _strs(b)
    if _normalise(a, True, True) == _normalise(b, True, True) and len(sa) == len(sb):
        def bare(t: str) -> str:
            return " ".join(_C_LIKE.sub(" ", t).split())
        # a shader held in a Python string: an edit to its comments is prose
        changed = [[x, y] for x, y in zip(sa, sb) if x != y and bare(x) != bare(y)]
        if not changed:
            return {"status": "renames", "renames": renames} if renames else {"status": "ok"}
        return {"status": "strings", "renames": renames, "strings": changed}
    return {"status": "code", "detail": "the code changed, not only its prose"}


_C_LIKE = re.compile(r"/\*.*?\*/|//[^\n]*|<!--.*?-->", re.DOTALL)
_HASH = re.compile(r"(?m)(^|\s)#[^\n]*")


def _verify_text(path: str, old: str, new: str) -> dict:
    strip = _HASH if Path(path).suffix in {".sh", ".yml", ".yaml", ".toml"} else _C_LIKE
    norm = lambda t: " ".join(strip.sub(" ", t).split())
    return {"status": "ok"} if norm(old) == norm(new) else \
        {"status": "code", "detail": "changed outside comments"}


def verify(base: str, files: list[str]) -> int:
    """Each file's change from `base` must be prose only: comments and
    docstrings, plus (reported, for review) test renames and string edits."""
    if not files:
        out = subprocess.check_output(["git", "diff", "--name-only", base, "--"], cwd=REPO).decode()
        files = [f for f in out.split() if f and Path(f).suffix in CODE_SUFFIXES]
    report, bad = {}, 0
    for f in files:
        local = (Path.cwd() / f).resolve()
        rel = str(local.relative_to(REPO)) if local.exists() and local.is_relative_to(REPO) else f
        try:
            old = subprocess.check_output(["git", "show", f"{base}:{rel}"], cwd=REPO,
                                          stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            report[rel] = {"status": "code", "detail": "new file"}
            bad += 1
            continue
        path = REPO / rel
        new = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        if not path.exists():
            r = {"status": "code", "detail": "file deleted"}
        elif rel.endswith(".py"):
            r = _verify_py(old, new)
        elif Path(rel).suffix in CODE_SUFFIXES:
            r = _verify_text(rel, old, new)
        else:
            r = {"status": "code", "detail": "not a code file the audit may edit"}
        report[rel] = r
        bad += r["status"] == "code"
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 1 if bad else 0


# ---------------------------------------------------------------- renames

def renames(paths: list[str]) -> int:
    """Apply {old_test_name: new_test_name}, merged from every file given,
    to every tracked text file, as whole words. Refuses two new names for
    one old name, and a new name that already exists anywhere."""
    mapping: dict[str, str] = {}
    for path in paths:
        for old, new in json.loads(Path(path).read_text()).items():
            if mapping.get(old, new) != new:
                print(f"refusing: {old} renamed to both {mapping[old]} and {new}")
                return 1
            mapping[old] = new
    if not mapping:
        print("renames: none")
        return 0
    text_suffixes = {".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".txt", ".html"}
    files = [p for p in tracked_files() if Path(p).suffix in text_suffixes and (REPO / p).is_file()]
    blob = {p: (REPO / p).read_text(encoding="utf-8", errors="replace") for p in files}
    # Run after the renames were made in place: each new name is defined
    # once; an old name still defined somewhere is another test of the same
    # name, so its references are ambiguous and are left for a person.
    defs = Counter(m for p, t in blob.items() if p.endswith(".py")
                   for m in re.findall(r"(?m)^\s*(?:async\s+)?def\s+(\w+)\s*\(", t))
    skipped = {o: n for o, n in mapping.items() if defs[n] > 1 or defs[o] > 0}
    for o, n in skipped.items():
        print(f"skipped {o} -> {n}: " + ("new name defined twice" if defs[n] > 1
                                         else "old name still defined elsewhere"))
    mapping = {o: n for o, n in mapping.items() if o not in skipped}
    if not mapping:
        return 1 if skipped else 0
    pat = re.compile(r"\b(" + "|".join(map(re.escape, sorted(mapping, key=len, reverse=True))) + r")\b")
    touched = 0
    for p, t in blob.items():
        new = pat.sub(lambda m: mapping[m.group(1)], t)
        if new != t:
            (REPO / p).write_text(new, encoding="utf-8")
            touched += 1
    print(f"renames: {len(mapping)} names across {touched} files, {len(skipped)} skipped")
    return 1 if skipped else 0


# ---------------------------------------------------------------- promotions

def promotions(audit_dir: str, size: int = 40) -> int:
    """Gather every promotion from the audit ledgers (worker and verifier),
    by kind, into batches of at most `size` that keep one module's
    promotions together: <audit_dir>/promotions/<kind>-<k>.json. Prints the
    batches as JSON."""
    root = Path(audit_dir)
    by_kind: dict[str, list[dict]] = {}
    for f in sorted((root / "ledger").glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError:
            print(f"unreadable ledger: {f}", file=sys.stderr)
            continue
        items = data.get("promotions", []) + data.get("extra_promotions", [])
        for item in items:
            item = dict(item, ledger=f.name)
            by_kind.setdefault(item.get("kind", "unknown"), []).append(item)
    out = root / "promotions"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    batches = []
    for kind, items in sorted(by_kind.items()):
        items.sort(key=lambda i: (i.get("path", ""), i.get("line", 0)))
        groups: list[list[dict]] = [[]]
        for item in items:
            same_file = groups[-1] and groups[-1][-1].get("path") == item.get("path")
            if len(groups[-1]) >= size and not (same_file and len(groups[-1]) < 2 * size):
                groups.append([])
            groups[-1].append(item)
        for k, g in enumerate(x for x in groups if x):
            name = f"{kind}-{k:02d}"
            (out / f"{name}.json").write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n")
            batches.append({"batch": name, "kind": kind, "count": len(g)})
    print(json.dumps(batches))
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) >= 2 else ""
    if cmd == "check":
        return check()
    if cmd == "baseline":
        return baseline()
    if cmd == "inventory" and len(argv) >= 3:
        return inventory(argv[2])
    if cmd == "shards" and len(argv) >= 3:
        target = int(argv[argv.index("--target") + 1]) if "--target" in argv else 500
        return shards(argv[2], target)
    if cmd == "verify":
        rest = argv[2:]
        base = "HEAD"
        if "--base" in rest:
            i = rest.index("--base")
            base = rest[i + 1]
            rest = rest[:i] + rest[i + 2:]
        return verify(base, rest)
    if cmd == "promotions" and len(argv) >= 3:
        return promotions(argv[2])
    if cmd == "renames" and len(argv) >= 3:
        return renames(argv[2:])
    if cmd == "count" and len(argv) >= 3:
        counts = {p: dict(count_markers(p)) for p in argv[2:]}
        print(json.dumps({"total": sum(sum(c.values()) for c in counts.values()),
                          "files": {p: c for p, c in counts.items() if c}}, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
