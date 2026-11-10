"""`tools/wait_green.py` only waits. Its logic runs over a stub `gh` on PATH, a real child process
each read, so the arguments it sends are the ones a real `gh` would get; only the clock is fake."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "wait_green.py"
HEAD = "abc1234def"
OTHER = "fff0000aaa"

# Answers one call from a script of answers, the last repeating, and logs its arguments.
STUB = """#!{python}
import json, sys
from pathlib import Path
here = Path({here!r})
with (here / "calls.jsonl").open("a") as f:
    f.write(json.dumps(sys.argv[1:]) + chr(10))
name = "head" if sys.argv[1:3] == ["pr", "view"] else "runs"
script = json.loads((here / (name + ".json")).read_text())
turn = here / (name + ".turn")
n = int(turn.read_text()) if turn.exists() else 0
turn.write_text(str(n + 1))
step = script[min(n, len(script) - 1)]
if step.get("fail"):
    sys.stderr.write(step.get("err", ""))
    sys.exit(1)
sys.stdout.write(step["out"])
"""


def _tool():
    spec = importlib.util.spec_from_file_location("wait_green", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wait_green"] = mod
    spec.loader.exec_module(mod)
    return mod


def _out(doc) -> dict:
    return {"out": json.dumps(doc)}


def _head(sha=HEAD) -> dict:
    return _out({"headRefOid": sha})


def _run(status="completed", conclusion="success", workflow="tests", run_id=100, attempt=1) -> dict:
    return {"workflowName": workflow, "status": status, "conclusion": conclusion,
            "databaseId": run_id, "attempt": attempt, "url": f"https://ci/{workflow}/{run_id}"}


GOING = _run(status="in_progress", conclusion="")


class Rig:
    def __init__(self, tool, here: Path):
        self.tool, self.here, self.slept, self.now = tool, here, [], 0.0
        self.script(runs=[_out([_run()])], head=[_head()])

    def script(self, runs=None, head=None):
        """One answer per call, the last repeating; the count starts again."""
        for name, answers in (("runs", runs), ("head", head)):
            if answers is not None:
                (self.here / f"{name}.json").write_text(json.dumps(answers))
                (self.here / f"{name}.turn").unlink(missing_ok=True)

    def _sleep(self, s):
        self.slept.append(s)
        self.now += s

    def wait(self, want=HEAD):
        self.slept = []
        return self.tool.wait("7", want, sleep=self._sleep, clock=lambda: self.now)

    def calls(self) -> list[list[str]]:
        log = self.here / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


@pytest.fixture
def gh(tmp_path, monkeypatch):
    tool = _tool()
    exe = tmp_path / "gh"
    exe.write_text(STUB.format(python=sys.executable, here=str(tmp_path)))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", str(tmp_path), prepend=":")
    # the real waits are held by their own tests: four polls here, not hundreds of child processes
    monkeypatch.setattr(tool, "APPEAR_S", 40)
    monkeypatch.setattr(tool, "FINISH_S", 80)
    monkeypatch.setattr(tool, "SILENT_S", 30)
    return Rig(tool, tmp_path)


# --- the verdict


def test_a_finished_green_run_is_0(gh, capsys):
    assert gh.wait() == 0
    assert gh.slept == []
    assert capsys.readouterr().out == f"CI green on {HEAD}\n"


def test_a_prefix_will_do_and_ci_is_asked_about_the_whole_head(gh):
    assert gh.wait(want=HEAD[:7]) == 0
    assert gh.calls()[1][2:4] == ["--commit", HEAD]


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "neutral", "skipped",
                                        "", None])
def test_anything_but_a_success_is_2_and_names_the_run(gh, capsys, conclusion):
    """Skipped too: a `tests` that was skipped checked nothing, where the script passed it."""
    gh.script(runs=[_out([_run(conclusion=conclusion)])])
    assert gh.wait() == 2
    out = capsys.readouterr().out
    assert f"CI NOT green on {HEAD}" in out
    assert f"tests {conclusion} https://ci/tests/100" in out


def test_a_superseded_cancelled_run_does_not_red_the_head(gh):
    gh.script(runs=[_out([_run(conclusion="cancelled", run_id=99), _run(run_id=100)])])
    assert gh.wait() == 0


def test_a_newer_failure_beats_an_older_success_in_either_order(gh):
    a, b = _run(run_id=99), _run(conclusion="failure", run_id=100)
    gh.script(runs=[_out([a, b])])
    assert gh.wait() == 2
    gh.script(runs=[_out([b, a])])
    assert gh.wait() == 2


def test_the_newest_attempt_of_one_run_speaks(gh):
    gh.script(runs=[_out([_run(conclusion="failure", attempt=1), _run(attempt=2)])])
    assert gh.wait() == 0


def test_an_older_finished_run_does_not_answer_for_a_newer_one_still_going(gh):
    going = _run(status="queued", conclusion="", run_id=100)
    gh.script(runs=[_out([_run(run_id=99), going]), _out([_run(run_id=99), going]),
                    _out([_run(run_id=99), _run(run_id=100)])])
    assert gh.wait() == 0
    assert gh.slept == [20, 20]


def test_another_workflows_run_says_nothing_either_way(gh):
    gh.script(runs=[_out([_run(), _run(conclusion="failure", workflow="docs", run_id=200)])])
    assert gh.wait() == 0
    gh.script(runs=[_out([_run(conclusion="failure"), _run(workflow="docs", run_id=200)])])
    assert gh.wait() == 2


def test_only_other_workflows_is_no_run_4_even_all_green(gh):
    gh.script(runs=[_out([_run(workflow="docs"), _run(conclusion="skipped", workflow="pages")])])
    assert gh.wait() == 4


def test_the_workflow_it_asks_for_is_the_one_ci_runs():
    workflow = (ROOT.parent / ".github" / "workflows" / "tests.yml").read_text()
    assert re.search(r"^name: (\S+)$", workflow, re.MULTILINE)[1] == _tool().WORKFLOW


# --- the head


def test_another_head_at_the_start_is_3_and_never_reads_ci(gh, capsys):
    gh.script(head=[_head(OTHER)])
    assert gh.wait() == 3
    assert f"head {OTHER} is not {HEAD}" in capsys.readouterr().out
    assert len(gh.calls()) == 1


def test_a_push_while_waiting_is_3_not_a_stale_green(gh, capsys):
    """The runs on the old head finish green; the head has moved by the read after them."""
    gh.script(head=[_head(), _head(OTHER)])
    assert gh.wait() == 3
    assert f"head moved from {HEAD} to {OTHER}" in capsys.readouterr().out


def test_a_run_cancelled_by_the_next_push_is_3_not_2(gh):
    gh.script(head=[_head(), _head(), _head(OTHER)],
              runs=[_out([GOING]), _out([_run(conclusion="cancelled")])])
    assert gh.wait() == 3


def test_no_verdict_comes_from_a_read_whose_head_could_not_be_checked(gh):
    gh.script(head=[_head(), {"fail": True}, _head(OTHER)])
    assert gh.wait() == 3


def test_the_head_is_read_after_the_runs_on_every_poll(gh):
    gh.script(runs=[_out([GOING]), _out([GOING]), _out([_run()])])
    assert gh.wait() == 0
    verbs = [c[0] for c in gh.calls()]
    assert verbs == ["pr", "run", "pr", "run", "pr", "run", "pr"]


# --- no answer


@pytest.mark.parametrize("answer", [{"fail": True}, {"out": "not json"}, _out([]), _out({}),
                                    _out({"headRefOid": None}), _out({"headRefOid": ""})])
def test_no_answer_about_the_head_is_6_not_a_moved_head(gh, capsys, answer):
    gh.script(head=[answer])
    assert gh.wait() == 6
    assert "gh did not answer about PR 7" in capsys.readouterr().out


def test_gh_s_own_stderr_comes_through(gh, capfd):
    gh.script(head=[{"fail": True, "err": "gh auth login: you are logged out\n"}])
    assert gh.wait() == 6
    assert "you are logged out" in capfd.readouterr().err


@pytest.mark.parametrize("answer", [{"fail": True}, {"out": "not json"}, _out({}), _out(["x"])])
def test_a_gh_that_stops_answering_about_runs_is_6_after_the_silence(gh, capsys, answer):
    gh.script(runs=[answer])
    assert gh.wait() == 6
    assert gh.now >= 30
    assert f"gh stopped answering about {HEAD}" in capsys.readouterr().out


def test_a_rate_limit_that_ends_is_only_a_pause(gh, capfd):
    gh.script(runs=[{"fail": True, "err": "HTTP 403: rate limit\n"}, {"fail": True}, _out([_run()])])
    assert gh.wait() == 0
    assert "rate limit" in capfd.readouterr().err


def test_runs_that_vanish_while_waiting_are_never_green(gh):
    """The script read an empty list here as nothing pending, and then as nothing bad: exit 0."""
    gh.script(runs=[_out([GOING]), _out([])])
    assert gh.wait() == 5
    gh.script(runs=[_out([GOING]), {"fail": True}])
    assert gh.wait() == 6


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("gh", 60), FileNotFoundError("gh")])
def test_a_hung_or_missing_gh_is_no_answer(gh, monkeypatch, capfd, error):
    def run(*a, **k):
        raise error

    monkeypatch.setattr(gh.tool.subprocess, "run", run)
    assert gh.wait() == 6
    assert capfd.readouterr().err.startswith("gh: ")


# --- the waits


def test_no_run_ever_is_4_at_the_deadline(gh, capsys):
    gh.script(runs=[_out([])])
    assert gh.wait() == 4
    assert gh.slept == [10] * 4
    assert f"no CI run appeared for {HEAD}" in capsys.readouterr().out


def test_a_run_that_appears_late_is_waited_for(gh):
    gh.script(runs=[_out([]), {"fail": True}, _out([_run()])])
    assert gh.wait() == 0
    assert gh.slept == [10, 10]


def test_a_run_that_never_finishes_is_5_at_the_deadline(gh, capsys):
    gh.script(runs=[_out([GOING])])
    assert gh.wait() == 5
    assert gh.slept == [20] * 4
    assert f"CI still running after 30 min on {HEAD}" in capsys.readouterr().out


def test_the_finish_wait_starts_when_the_run_appears(gh):
    gh.script(runs=[_out([]), _out([]), _out([GOING])])
    assert gh.wait() == 5
    assert gh.slept == [10, 10] + [20] * 4


def test_the_real_waits_are_the_scripts_and_on_a_monotonic_clock():
    tool = _tool()
    assert (tool.APPEAR_S, tool.FINISH_S, tool.SILENT_S) == (10 * 60, 30 * 60, 5 * 60)
    assert inspect.signature(tool.wait).parameters["clock"].default is time.monotonic


def _slow_gh(tool, monkeypatch, runs):
    """Every `gh` takes the whole timeout. The real waits, on a fake clock."""
    now = [0.0]

    def fake(*args):
        now[0] += tool.GH_TIMEOUT_S
        return {"headRefOid": HEAD} if args[0] == "pr" else runs

    monkeypatch.setattr(tool, "_gh", fake)

    def sleep(s):
        assert s >= 0   # `time.sleep` raises on less, and a clock going back would hide an overrun
        now[0] += s

    return now, sleep


def test_a_slow_gh_cant_stretch_the_thirty_minutes():
    """Counting tries, 90 polls of two 60 s reads and a 20 s sleep would be 3.5 hours saying 30 min."""
    tool = _tool()
    with pytest.MonkeyPatch.context() as mp:
        now, sleep = _slow_gh(tool, mp, [GOING])
        assert tool.wait("7", HEAD, sleep=sleep, clock=lambda: now[0]) == 5
    first_poll_done = 3 * tool.GH_TIMEOUT_S
    assert tool.FINISH_S <= now[0] - first_poll_done <= tool.FINISH_S + 20 + 2 * tool.GH_TIMEOUT_S


def test_a_slow_gh_cant_stretch_the_ten_minutes():
    tool = _tool()
    with pytest.MonkeyPatch.context() as mp:
        now, sleep = _slow_gh(tool, mp, [])
        assert tool.wait("7", HEAD, sleep=sleep, clock=lambda: now[0]) == 4
    assert tool.APPEAR_S <= now[0] - tool.GH_TIMEOUT_S <= tool.APPEAR_S + 10 + 2 * tool.GH_TIMEOUT_S


def test_a_last_sleep_stops_at_the_deadline(gh):
    gh.tool.APPEAR_S = 25
    gh.script(runs=[_out([])])
    assert gh.wait() == 4
    assert gh.slept == [10, 10, 5]


# --- the arguments: argparse's own usage code is 2, which here would say "red"


@pytest.mark.parametrize("argv", [[], ["7"], ["7", ""], ["7", "a"], ["7", HEAD[:6]], ["", HEAD],
                                  ["7", HEAD, "extra"], ["--help"], ["-h"], ["7", HEAD, "--help"]])
def test_bad_arguments_are_1_and_ask_gh_nothing(gh, argv):
    """`["7", ""]`: an empty head is a prefix of every commit, and the script waved it through."""
    with pytest.raises(SystemExit) as e:
        gh.tool.main(argv)
    assert e.value.code == 1
    assert gh.calls() == []


def test_help_prints_the_help_and_still_is_not_0(gh, capfd):
    with pytest.raises(SystemExit) as e:
        gh.tool.main(["--help"])
    assert e.value.code == 1
    assert "the head commit you expect" in capfd.readouterr().err


def test_seven_characters_are_enough(gh):
    assert gh.tool.main(["7", HEAD[:7]]) == 0


def test_a_child_process_exits_with_the_code(gh):
    gh.script(head=[_head(OTHER)])
    done = subprocess.run([sys.executable, str(TOOL), "7", HEAD], capture_output=True, text=True,
                          check=False)
    assert done.returncode == 3, done.stderr
    assert len(gh.calls()) == 1


def test_it_runs_on_a_bare_python_with_no_project(gh):
    """The documented road is `python3 tools/wait_green.py`: `-I -S` sees no project and no packages."""
    gh.script(head=[_head(OTHER)])
    done = subprocess.run([sys.executable, "-I", "-S", str(TOOL), "7", HEAD], capture_output=True,
                          text=True, check=False, cwd="/")
    assert done.returncode == 3, done.stderr
    assert "uv run" not in _tool().__doc__.split("Standard library")[0]


# --- it can't merge


def test_every_gh_call_on_every_road_is_one_of_two_reads(gh):
    roads = ([_out([_run()])], [_out([_run(conclusion="failure")])], [_out([])], [_out([GOING])],
             [{"fail": True}])
    for runs in roads:
        gh.script(runs=runs)
        gh.now = 0.0
        gh.wait()
    gh.script(head=[_head(OTHER)])
    gh.wait()
    gh.script(head=[{"fail": True}])
    gh.wait()
    calls = gh.calls()
    assert len(calls) > 7
    for call in calls:
        assert call[:2] in (["pr", "view"], ["run", "list"]), call


def test_nothing_in_the_tool_can_merge():
    """The source starts one child process, on two literal reads, and holds no other road to one."""
    tree = ast.parse(TOOL.read_text())
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    words = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            words |= set(re.findall(r"[-a-z]+", n.value.lower()))
    assert not words & {"merge", "--auto", "ready", "api", "push", "close", "git", "edit", "comment"}

    gh_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and getattr(n.func, "id", "") == "_gh"]
    assert sorted((c.args[0].value, c.args[1].value) for c in gh_calls) == [("pr", "view"), ("run", "list")]

    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not attrs & {"Popen", "popen", "system", "call", "check_call", "check_output", "getoutput"}
    runs = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
    assert len(runs) == 1
    assert not any(k.arg == "shell" for k in runs[0].keywords)

    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imports |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imports.add(n.module.split(".")[0])
    assert imports == {"__future__", "argparse", "collections", "json", "pathlib", "subprocess",
                       "sys", "time"}
