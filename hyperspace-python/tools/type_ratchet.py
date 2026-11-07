"""The type ratchet (row 788): a new pyright complaint fails, an old one doesn't.

`tools/type_baseline.json` counts today's complaints by file and rule. A count over its
baseline is a new complaint; a file the baseline doesn't name has a baseline of none. Lines
aren't in it, so moving code inside a file changes nothing. Pyright only reads the source,
and this tool imports nothing of the app, so nothing here opens GL or needs a display.

    uv run python tools/type_ratchet.py            # check, and lower the baseline where errors went
    uv run python tools/type_ratchet.py --check    # check only, writes nothing: CI and the test
    uv run python tools/type_ratchet.py --accept   # a split: files move, no rule's total rises
    uv run python tools/type_ratchet.py --raise-baseline   # a real raise: a pyright bump, say

Exit 0: nothing new. Exit 1: something new. Exit 2: couldn't judge. A split moves old complaints
to a new file, which reads as new: `--accept` takes that, and refuses if any rule's total over
the app rose, so a split can't sweep a new complaint in. `--raise-baseline` is the only way a
total rises: it shows in the PR's diff, and the PR says why. Settings are `[tool.pyright]` in
pyproject.toml.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "type_baseline.json"

# The baseline is the Mac's full sync. CI has none of these, and pyright sees other types there:
# only a full sync writes the baseline, or lowering to CI's counts would fail the Mac afterwards.
FULL_SYNC = ("torch", "leap", "objc")
# What CI's sync sees against the baseline, exactly (measured with those packages gone, row 788):
# judged against this, CI's limit is what it really counts, so it has no spare room. Fixing or
# moving one of these complaints makes CI fail on that pair: change its number here.
CI_SYNC = {
    "hyperspace/dream.py": {"reportOptionalMemberAccess": +1},
    "hyperspace/hands/core.py": {"reportAttributeAccessIssue": -1},
    "hyperspace/overlay.py": {"reportAttributeAccessIssue": -1},
    "hyperspace/pinch.py": {"reportAttributeAccessIssue": -2},
    "hyperspace/segment.py": {"reportAttributeAccessIssue": -1},
}
# Packages a machine may lack, whose missing import is no complaint. Any other missing import is,
# a stale `from .routing_old import x` above all: the failure a split makes, only at runtime.
OPTIONAL = {"AppKit", "AVFoundation", "CoreML", "Foundation", "Metal", "Quartz", "Vision",
            "leap", "leapc_cffi", "mlx", "objc", "syphon", "torch", "torchvision"}

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


def _optional(d: dict) -> bool:
    """A missing import of a package a machine may lack."""
    if d.get("rule") != "reportMissingImports":
        return False
    head = d["message"].split('"')[1].split(".")[0]    # `Import "torch.nn" could not be resolved`
    return head in OPTIONAL


def parse(doc: dict, root: Path = ROOT) -> Report:
    """Pyright's --outputjson as a report: errors and warnings, by path from `root`."""
    try:
        if not doc["summary"]["filesAnalyzed"]:
            raise Unjudged(f"pyright analysed no files: {doc['summary']}")
        out = []
        for d in doc["generalDiagnostics"]:
            if d["severity"] not in ("error", "warning") or _optional(d):
                continue
            # pyright leaves `range` out when it's empty
            line = d["range"]["start"]["line"] + 1 if "range" in d else 0
            out.append(Complaint(Path(d["file"]).relative_to(root).as_posix(),
                                 d.get("rule", "(no rule)"), line,
                                 d["message"].split("\n")[0]))
        return Report(doc["version"], tuple(out))
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as e:
        raise Unjudged(f"pyright's output isn't what this reads: {e!r}") from e


def _run(cmd: list[str], timeout: float) -> tuple[int, str, str]:
    """(exit, stdout, stderr), and nothing left running if it doesn't finish. Pyright's wrapper
    runs node as a child, about 1 GB, and killing only the wrapper would orphan it: so its own
    session, and the whole group goes."""
    with subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          start_new_session=True,
                          env={**os.environ, "PYRIGHT_PYTHON_IGNORE_WARNINGS": "1"}) as proc:
        try:
            out, err = proc.communicate(timeout=timeout)
        except BaseException:
            with suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.pid, signal.SIGKILL)
            raise
        return proc.returncode, out, err


def run_pyright() -> Report:
    """Pyright over `[tool.pyright]`'s include, resolving imports in this interpreter."""
    cmd = [sys.executable, "-m", "pyright", "--outputjson", "--pythonpath", sys.executable]
    try:
        code, out, err = _run(cmd, 240)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Unjudged(f"pyright didn't finish: {e}") from e
    if code not in (0, 1):                      # 0 and 1: no complaints, complaints
        raise Unjudged(f"pyright exited {code}: {err[-2000:]}")
    try:
        return parse(json.loads(out))
    except json.JSONDecodeError as e:
        raise Unjudged(f"pyright's output isn't JSON: {out[:500]!r}") from e


def sync_of(found: Callable[[str], bool] = _found) -> str:
    """"full", "ci", or "mixed", which neither table describes."""
    have = [found(m) for m in FULL_SYNC]
    return "full" if all(have) else "mixed" if any(have) else "ci"


def limits(baseline: Counts, sync: str) -> Counts:
    """What this machine may count: the baseline, moved by CI_SYNC on CI's sync."""
    if sync != "ci":
        return baseline
    out = {f: dict(rules) for f, rules in baseline.items()}
    for f, rules in CI_SYNC.items():
        for rule, delta in rules.items():
            mine = out.setdefault(f, {})
            mine[rule] = max(0, mine.get(rule, 0) + delta)
    return out


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
    try:
        doc = json.loads(path.read_text())
        pin, files = doc["pyright"], doc["files"]
        fine = isinstance(pin, str) and all(
            isinstance(n, int) for rules in files.values() for n in rules.values())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise Unjudged(f"can't read the baseline {path}: {e!r}") from e
    if not fine:
        raise Unjudged(f"the baseline {path} isn't counts by file and rule")
    return pin, files


def write(path: Path, version: str, counts: Counts) -> None:
    """One rule a line, sorted: PRs touching different files merge without a conflict."""
    doc = {"pyright": version, "files": counts}
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


def total(counts: Counts) -> int:
    return sum(n for rules in counts.values() for n in rules.values())


def rule_totals(counts: Counts) -> dict[str, int]:
    out: dict[str, int] = {}
    for rules in counts.values():
        for rule, n in rules.items():
            out[rule] = out.get(rule, 0) + n
    return out


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
    mode.add_argument("--accept", action="store_true",
                      help="write today's counts if no rule's total over the app rose")
    mode.add_argument("--raise-baseline", action="store_true", help="write today's counts, whatever they are")
    args = ap.parse_args(argv)

    sync = sync_of(found)
    if not args.check and sync != "full":
        print(f"writing the baseline needs a full `uv sync`, with {', '.join(FULL_SYNC)}: "
              "use --check here")
        return 2
    if sync == "mixed":
        print(f"this sync has some of {', '.join(FULL_SYNC)}: neither the baseline nor CI_SYNC "
              "describes it, so it can't be judged")
        return 2
    try:
        report = pyright()
        if args.raise_baseline:
            write(baseline, report.version, report.counts())
            print(f"raised to {total(report.counts())} complaints; say why in the PR")
            return 0
        pin, whole = read(baseline)
    except Unjudged as e:
        print(e)
        return 2
    if pin != report.version:
        print(f"the baseline is pyright {pin}, this is {report.version}: "
              "`uv sync`, or move the pin with --raise-baseline")
        return 2
    if args.accept:
        was, is_ = rule_totals(whole), rule_totals(report.counts())
        risen = {r: (was.get(r, 0), n) for r, n in is_.items() if n > was.get(r, 0)}
        if risen:
            for r, (a, b) in sorted(risen.items()):
                print(f"{r}: {b} over the app, baseline {a}")
            print("a move leaves every rule's total level: fix what's new, or --raise-baseline "
                  "and say why in the PR")
            return 1
        write(baseline, pin, report.counts())
        print(f"accepted {total(report.counts())} complaints; say why in the PR")
        return 0

    now = report.counts()
    grown, gone = compare(limits(whole, sync), now)
    if gone and not args.check:
        write(baseline, pin, lowered(whole, now))
    for line in describe_new(grown, report):
        print(line)
    went = sum(a - b for _, _, a, b in gone)
    if not gone:
        note = ""
    elif not args.check:
        note = f"; {went} gone, baseline lowered: commit it"
    elif sync == "full":
        note = f"; {went} gone: run this without --check and commit the baseline"
    else:
        note = f"; {went} gone: a full sync without --check lowers the baseline"
    print(f"{total(now)} complaints, {sum(b - a for _, _, a, b in grown)} over the baseline{note}")
    return 1 if grown else 0


if __name__ == "__main__":
    sys.exit(main())
