"""The type ratchet (row 788): a new pyright complaint fails, an old one doesn't.

`tools/type_baseline.json` counts today's complaints by file and rule. A count over its
baseline is a new complaint; a file the baseline doesn't name has a baseline of none. Lines
aren't in it, so moving code inside a file changes nothing. Pyright only reads the source,
and this tool imports nothing of the app, so nothing here opens GL or needs a display.

    uv run python tools/type_ratchet.py            # check, and lower the baseline where errors went
    uv run python tools/type_ratchet.py --check    # check only, writes nothing: CI and the test
    uv run python tools/type_ratchet.py --accept   # write today's counts, raises included

Exit 0: nothing new. Exit 1: something new. Exit 2: couldn't judge. `--accept` is for a split,
which moves old complaints to a new file, and for moving the pyright pin: the raise shows in
the PR's diff, and the PR says why. Settings are `[tool.pyright]` in pyproject.toml.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "type_baseline.json"

# Files that can't be judged where a module is missing: without torch, dream.py's tensors are
# Unknown and pyright sees a different `None`, so CI (no `dream` group) complains once more.
NEEDS = {"hyperspace/dream.py": "torch"}
# What writing the baseline needs: it is the Mac's full sync. Without these pyright sees fewer
# types and so fewer complaints, and lowering to that count would fail the Mac afterwards.
FULL_SYNC = ("torch", "leap", "objc")

Counts = dict[str, dict[str, int]]
Change = tuple[str, str, int, int]      # file, rule, baseline, now


class Unjudged(RuntimeError):
    """Pyright didn't run, or read nothing: never read as "no complaints"."""


@dataclass(frozen=True)
class Complaint:
    file: str
    rule: str
    line: int
    message: str


@dataclass(frozen=True)
class Report:
    version: str
    complaints: tuple[Complaint, ...]

    def counts(self) -> Counts:
        out: Counts = {}
        for c in self.complaints:
            rules = out.setdefault(c.file, {})
            rules[c.rule] = rules.get(c.rule, 0) + 1
        return out


def _found(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def parse(doc: dict, root: Path = ROOT) -> Report:
    """Pyright's --outputjson as a report: errors and warnings, by path from `root`."""
    if not doc.get("summary", {}).get("filesAnalyzed"):
        raise Unjudged(f"pyright analysed no files: {doc.get('summary')}")
    out = []
    for d in doc.get("generalDiagnostics", ()):
        if d.get("severity") not in ("error", "warning"):
            continue
        out.append(Complaint(Path(d["file"]).relative_to(root).as_posix(),
                             d.get("rule", "(no rule)"),
                             d["range"]["start"]["line"] + 1,
                             d["message"].split("\n")[0]))
    return Report(doc["version"], tuple(out))


def run_pyright() -> Report:
    """Pyright over `[tool.pyright]`'s include, resolving imports in this interpreter."""
    cmd = [sys.executable, "-m", "pyright", "--outputjson", "--pythonpath", sys.executable]
    try:
        done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=240, check=False,
                              env={**os.environ, "PYRIGHT_PYTHON_IGNORE_WARNINGS": "1"})
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Unjudged(f"pyright didn't finish: {e}") from e
    if done.returncode not in (0, 1):           # 0 and 1: no complaints, complaints
        raise Unjudged(f"pyright exited {done.returncode}: {done.stderr[-2000:]}")
    try:
        return parse(json.loads(done.stdout))
    except json.JSONDecodeError as e:
        raise Unjudged(f"pyright's output isn't JSON: {done.stdout[:500]!r}") from e


def judged(counts: Counts, found: Callable[[str], bool] = _found) -> Counts:
    """`counts` without the files this machine can't judge (NEEDS)."""
    return {f: rules for f, rules in counts.items()
            if f not in NEEDS or found(NEEDS[f])}


def compare(baseline: Counts, now: Counts) -> tuple[list[Change], list[Change]]:
    """(new, gone): every (file, rule) over its baseline, and every one under it."""
    grown, gone = [], []
    for f in sorted({*baseline, *now}):
        was, is_ = baseline.get(f, {}), now.get(f, {})
        for rule in sorted({*was, *is_}):
            a, b = was.get(rule, 0), is_.get(rule, 0)
            if b > a:
                grown.append((f, rule, a, b))
            elif b < a:
                gone.append((f, rule, a, b))
    return grown, gone


def lowered(baseline: Counts, now: Counts) -> Counts:
    """The baseline with every count at or under where it was; none rises, none appears."""
    out: Counts = {}
    for f, rules in baseline.items():
        kept = {r: min(n, now.get(f, {}).get(r, 0)) for r, n in rules.items()}
        kept = {r: n for r, n in kept.items() if n}
        if kept:
            out[f] = kept
    return out


def read(path: Path) -> tuple[str, Counts]:
    doc = json.loads(path.read_text())
    return doc["pyright"], doc["files"]


def write(path: Path, version: str, counts: Counts) -> None:
    """One rule a line, sorted: PRs touching different files merge without a conflict."""
    doc = {"pyright": version, "files": counts}
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


def total(counts: Counts) -> int:
    return sum(n for rules in counts.values() for n in rules.values())


def describe_new(grown: Iterable[Change], report: Report) -> list[str]:
    """Each grown count and all its complaints: lines aren't kept, so which is new can't be told."""
    lines = []
    for f, rule, was, now in grown:
        lines.append(f"{f}: {rule}: {now}, baseline {was}")
        lines += [f"  {f}:{c.line}: {c.message}" for c in report.complaints
                  if c.file == f and c.rule == rule]
    return lines


def main(argv: list[str] | None = None, *, pyright: Callable[[], Report] = run_pyright,
         baseline: Path = BASELINE, found: Callable[[str], bool] = _found) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="write nothing")
    mode.add_argument("--accept", action="store_true", help="write today's counts, raises included")
    args = ap.parse_args(argv)

    if not args.check and not all(found(m) for m in FULL_SYNC):
        print(f"writing the baseline needs a full `uv sync`, with {', '.join(FULL_SYNC)}: "
              "use --check here")
        return 2
    try:
        report = pyright()
    except Unjudged as e:
        print(e)
        return 2
    if args.accept:
        now = report.counts()
        write(baseline, report.version, now)
        print(f"accepted {total(now)} complaints; say why in the PR")
        return 0

    pin, whole = read(baseline)
    if pin != report.version:
        print(f"the baseline is pyright {pin}, this is {report.version}: "
              "`uv sync`, or move the pin with --accept")
        return 2
    now = judged(report.counts(), found)
    grown, gone = compare(judged(whole, found), now)
    if gone and not args.check:
        write(baseline, pin, lowered(whole, report.counts()))
    for line in describe_new(grown, report):
        print(line)
    went = sum(a - b for _, _, a, b in gone)
    if not gone:
        note = ""
    elif not args.check:
        note = f"; {went} gone, baseline lowered: commit it"
    elif all(found(m) for m in FULL_SYNC):
        note = f"; {went} gone: run this without --check and commit the baseline"
    else:
        note = f"; {went} under the baseline, as a partial sync sees fewer types"
    print(f"{total(now)} complaints, {sum(b - a for _, _, a, b in grown)} over the baseline{note}")
    return 1 if grown else 0


if __name__ == "__main__":
    sys.exit(main())
