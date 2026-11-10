#!/usr/bin/env python3
"""Split the fast tier across CI's runners, and keep the timings that split it (row 870).

    python3 tools/ci_shard.py files <index> <count>     one shard's test files, a line each
    uv run python tools/ci_shard.py prewarm <index> <count>
                                                    pytest's assert rewriting of those files,
                                                    four processes at once, before the run
    python3 tools/ci_shard.py durations <junit.xml>...  tests/ci_durations.json from CI's reports

`files`: every `tests/test_*.py` lands in exactly one of `count` shards, the
longest first onto the shard with the least time so far, by the seconds CI took
on each file (`tests/ci_durations.json`). A file the timings don't name counts as
their median. The same files and timings always give the same shards.

`prewarm`: on a fresh checkout pytest rewrites the asserts of every test module it
imports and caches the result in `tests/__pycache__`, and each xdist worker does all
of it for itself: about 20 s of the fast tier's start (132,000 lines). Collecting a
quarter of the shard's files in each of four processes first leaves the cache warm,
so the workers start at once. It never fails a run: a module that doesn't import
fails in the real run, by name.

`durations`: the JUnit reports of the `tests` workflow's fast-tier jobs (uploaded on
each push to main), summed per file, with every test of `SLOW_S` or more named so
conftest can hand it out first. Run it when a shard runs long; the order and the split
only get worse as the timings age, never wrong.

Standard library only, so `files` and `durations` run on plain `python3`.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DURATIONS = ROOT / "tests" / "ci_durations.json"
SLOW_S = 1.0        # a test this slow is named in the timings, to be handed out first
PREWARM_PROCS = 4   # a runner's cores


def test_files(root: Path = ROOT) -> list[str]:
    """Every test module pytest collects (`testpaths = ["tests"]`, `test_*.py`)."""
    return sorted(p.relative_to(root).as_posix() for p in (root / "tests").glob("test_*.py"))


def read_durations(path: Path = DURATIONS) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def shards(files: list[str], costs: dict[str, float], count: int) -> list[list[str]]:
    """`files` in `count` groups of about equal time: the longest file first onto the
    group with the least so far, ties to the lower index and then by name."""
    if count < 1:
        raise ValueError("count must be at least 1")
    known = [costs[f] for f in files if f in costs]
    default = statistics.median(known) if known else 1.0
    loads, out = [0.0] * count, [[] for _ in range(count)]
    for f in sorted(files, key=lambda f: (-costs.get(f, default), f)):
        i = min(range(count), key=lambda j: (loads[j], j))
        out[i].append(f)
        loads[i] += costs.get(f, default)
    return [sorted(s) for s in out]


def shard(index: int, count: int, root: Path = ROOT, durations: Path = DURATIONS) -> list[str]:
    if not 0 <= index < count:
        raise ValueError(f"index {index} is not in 0..{count - 1}")
    return shards(test_files(root), read_durations(durations).get("files", {}), count)[index]


def prewarm(files: list[str], procs: int = PREWARM_PROCS, root: Path = ROOT) -> int:
    """Collect `files` in `procs` processes at once; every exit is fine."""
    groups = [files[i::procs] for i in range(procs)]
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", "-n0", "-p", "no:cacheprovider"]
    running = [subprocess.Popen(cmd + g, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
               for g in groups if g]
    for p in running:
        p.wait()
    return 0


def nodeid(classname: str, name: str, root: Path = ROOT) -> str:
    """A JUnit testcase's pytest node id: `tests.test_x.TestC` + `test_y[a]` is
    `tests/test_x.py::TestC::test_y[a]` (the longest dotted prefix that is a file)."""
    parts = classname.split(".")
    for cut in range(len(parts), 0, -1):
        path = "/".join(parts[:cut]) + ".py"
        if (root / path).exists() or cut == 1:
            return "::".join([path, *parts[cut:], name])
    raise AssertionError("unreachable")


def durations(reports: list[Path], root: Path = ROOT) -> dict:
    files: dict[str, float] = {}
    tests: dict[str, float] = {}
    for report in reports:
        for case in ET.parse(report).iter("testcase"):
            nid = nodeid(case.get("classname", ""), case.get("name", ""), root)
            t = float(case.get("time", 0.0))
            path = nid.split("::", 1)[0]
            files[path] = files.get(path, 0.0) + t
            if t >= SLOW_S:
                tests[nid] = t
    return {"_": "CI seconds per test file and per test of 1 s or more, from the fast tier's "
                 "JUnit reports: python3 tools/ci_shard.py durations <junit.xml>... (row 870)",
            "files": {k: round(v, 1) for k, v in sorted(files.items())},
            "tests": {k: round(v, 1) for k, v in sorted(tests.items())}}


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] in ("files", "prewarm"):
        files = shard(int(argv[1]), int(argv[2]))
        if argv[0] == "files":
            print("\n".join(files))
            return 0
        return prewarm(files)
    if len(argv) >= 2 and argv[0] == "durations":
        DURATIONS.write_text(json.dumps(durations([Path(a) for a in argv[1:]]), indent=1) + "\n")
        return 0
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
