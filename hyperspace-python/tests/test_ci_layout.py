"""CI's layout (row 870): the fast tier split over runners, the sweep tier on its own.

tools/ci_shard.py splits the test files by CI time; .github/workflows/tests.yml runs
the shards and the type ratchet side by side; .github/workflows/sweeps.yml runs
conftest's sweep tier when a PR touches what it walks. These hold the pieces to
each other, so none can drift from the rest without a failing test.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

import conftest
import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT.parent / ".github" / "workflows"
RATCHET = "tests/test_type_ratchet.py::test_no_new_complaint_in_the_app"


def _tool():
    spec = importlib.util.spec_from_file_location("ci_shard", ROOT / "tools" / "ci_shard.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ci_shard"] = mod
    spec.loader.exec_module(mod)
    return mod


tool = _tool()


# ---- the split


@pytest.mark.parametrize("count", [1, 2, 3, 4, 6])
def test_every_test_file_lands_in_exactly_one_shard(count):
    files = tool.test_files()
    split = [tool.shard(i, count) for i in range(count)]
    flat = [f for s in split for f in s]
    assert sorted(flat) == files and len(flat) == len(set(flat))
    assert all(split), "an empty shard would be a runner with nothing to run"


def test_the_same_files_and_timings_give_the_same_shards():
    files, costs = tool.test_files(), tool.read_durations().get("files", {})
    assert tool.shards(files, costs, 4) == tool.shards(list(reversed(files)), dict(costs), 4)


def test_a_file_the_timings_dont_name_counts_as_their_median():
    costs = {"a.py": 1.0, "b.py": 3.0, "c.py": 9.0}
    assert tool.shards(["a.py", "b.py", "c.py", "new.py"], costs, 2) == [["c.py"], ["a.py", "b.py", "new.py"]]


def test_the_committed_timings_split_four_ways_within_a_tenth():
    files, costs = tool.test_files(), tool.read_durations()["files"]
    loads = [sum(costs.get(f, 0.0) for f in s) for s in tool.shards(files, costs, 4)]
    assert max(loads) <= 1.1 * min(loads), loads


def test_an_index_outside_the_count_is_refused():
    with pytest.raises(ValueError):
        tool.shard(4, 4)


# ---- the workflows


def test_tests_yml_runs_every_shard_and_the_ratchet_once():
    text = (WORKFLOWS / "tests.yml").read_text()
    shards = int(re.search(r"^  SHARDS: (\d+)$", text, re.MULTILINE)[1])
    matrix = json.loads(re.search(r"^        shard: (\[[\d, ]+\])", text, re.MULTILINE)[1])
    assert matrix == list(range(shards))
    assert f"--deselect {RATCHET}" in text, "the shards would run pyright four more times"
    assert f"pytest -q -n0 -p no:cacheprovider {RATCHET}" in text, "nothing would run the ratchet"


def test_the_required_check_tests_waits_for_every_job_and_passes_only_with_them():
    """A ruleset on main can require a check named `tests`: the one job that keeps that name
    must need every other job, run even when one fails, and fail unless all passed."""
    text = (WORKFLOWS / "tests.yml").read_text()
    jobs = re.findall(r"^  (\w+):$", text.split("\njobs:\n", 1)[1], re.MULTILINE)
    gate = text.split("\n  tests:\n", 1)[1]
    assert "    name: tests\n" in gate and "    if: always()\n" in gate
    assert re.search(r"needs: \[(.*)\]", gate)[1].split(", ") == [j for j in jobs if j != "tests"]
    for job in jobs:
        if job != "tests":
            assert f'test "${{{{ needs.{job}.result }}}}" = success' in gate, job


def _sweep_keys() -> set[str]:
    return set(conftest._SWEEP_TESTS)


def test_every_sweep_names_a_test_that_exists():
    """A renamed sweep would slip back into the fast tier with its old name left here."""
    for key in sorted(_sweep_keys()):
        path, name = key.split("::")
        tree = ast.parse((ROOT / "tests" / path).read_text())
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert name in names, key


def test_sweeps_yml_is_triggered_by_every_file_with_a_sweep_in_it():
    paths = set(re.findall(r"^      - (hyperspace-python/tests/test_\S+\.py)$",
                           (WORKFLOWS / "sweeps.yml").read_text(), re.MULTILINE))
    want = {f"hyperspace-python/tests/{k.split('::')[0]}" for k in _sweep_keys()}
    assert paths == want


def test_no_sweep_is_in_the_fast_tier():
    assert "not sweep" in conftest._FAST
    assert conftest._FAST in (ROOT / "pyproject.toml").read_text()


# ---- the order


class _Item:
    def __init__(self, nodeid):
        self.nodeid, self.markers = nodeid, []
        path, self.name = nodeid.split("::")
        self.path, self.originalname = Path(path), self.name

    def add_marker(self, mark):
        self.markers.append(mark.name)


def test_the_longest_tests_go_first_and_the_rest_keep_their_order(monkeypatch):
    timings = {"tests": {"tests/test_b.py::test_slow": 9.0, "tests/test_c.py::test_slower": 20.0}}
    monkeypatch.setattr(conftest, "_ci_durations", lambda: timings)
    items = [_Item(n) for n in ("tests/test_a.py::test_one", "tests/test_b.py::test_slow",
                                "tests/test_a.py::test_two", "tests/test_c.py::test_slower")]
    conftest.pytest_collection_modifyitems(None, items)
    assert [i.nodeid for i in items] == ["tests/test_c.py::test_slower", "tests/test_b.py::test_slow",
                                         "tests/test_a.py::test_one", "tests/test_a.py::test_two"]


def test_a_sweep_is_marked_sweep(monkeypatch):
    monkeypatch.setattr(conftest, "_ci_durations", dict)
    key = min(_sweep_keys())
    item = _Item(f"tests/{key}")
    conftest.pytest_collection_modifyitems(None, [item])
    assert item.markers == ["sweep"]


def test_the_committed_timings_load():
    timings = conftest._ci_durations()
    assert timings["files"] and timings["tests"]
    assert all(t >= tool.SLOW_S for t in timings["tests"].values())


# ---- the timings


def test_durations_reads_junit_into_files_and_slow_tests(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="tests.test_ci_layout" name="test_x[a]" time="2.5"/>'
        '<testcase classname="tests.test_ci_layout" name="test_y" time="0.25"/>'
        '<testcase classname="tests.test_ci_layout._Item" name="test_z" time="1.0"/>'
        '</testsuite></testsuites>')
    out = tool.durations([report])
    assert out["files"] == {"tests/test_ci_layout.py": 3.8}
    assert out["tests"] == {"tests/test_ci_layout.py::test_x[a]": 2.5,
                            "tests/test_ci_layout.py::_Item::test_z": 1.0}
