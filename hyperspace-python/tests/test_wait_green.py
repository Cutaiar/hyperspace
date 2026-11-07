"""`tools/wait_green.py` only waits. Its logic runs over a stub `gh` on PATH, a real child process
each poll, so the arguments it sends are the ones a real `gh` would get; only the sleeps are fake."""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "wait_green.py"
HEAD = "abc1234def"

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


def _run(status="completed", conclusion="success", name="tests") -> dict:
    return {"name": name, "status": status, "conclusion": conclusion, "url": f"https://ci/{name}"}


class Rig:
    def __init__(self, tool, here: Path):
        self.tool, self.here, self.slept = tool, here, []
        self.script(runs=[_out([_run()])], head=[_out({"headRefOid": HEAD})])

    def script(self, runs=None, head=None):
        """One answer per call, the last repeating; the count starts again."""
        for name, answers in (("runs", runs), ("head", head)):
            if answers is not None:
                (self.here / f"{name}.json").write_text(json.dumps(answers))
                (self.here / f"{name}.turn").unlink(missing_ok=True)

    def wait(self, want=HEAD):
        self.slept = []
        return self.tool.wait("7", want, sleep=self.slept.append)

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
    # the caps are held by their own test: no hundred child processes each time one is reached
    monkeypatch.setattr(tool, "APPEAR_TRIES", 4)
    monkeypatch.setattr(tool, "FINISH_TRIES", 4)
    return Rig(tool, tmp_path)


def test_a_finished_green_run_is_0(gh, capsys):
    assert gh.wait() == 0
    assert gh.slept == []
    assert capsys.readouterr().out == f"CI green on {HEAD}\n"


def test_a_prefix_will_do_and_ci_is_asked_about_the_whole_head(gh):
    assert gh.wait(want=HEAD[:7]) == 0
    assert gh.calls()[1][2:4] == ["--commit", HEAD]


def test_a_skipped_run_passes_as_it_did_in_the_script(gh):
    gh.script(runs=[_out([_run(), _run(conclusion="skipped", name="other")])])
    assert gh.wait() == 0


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "neutral", "", None])
def test_any_other_conclusion_is_2_and_lists_every_run(gh, capsys, conclusion):
    gh.script(runs=[_out([_run(), _run(conclusion=conclusion, name="bad")])])
    assert gh.wait() == 2
    out = capsys.readouterr().out
    assert f"CI NOT green on {HEAD}" in out
    assert "tests success https://ci/tests" in out
    assert f"bad {conclusion} https://ci/bad" in out


def test_another_head_is_3_and_never_reads_ci(gh, capsys):
    gh.script(head=[_out({"headRefOid": "fff0000"})])
    assert gh.wait() == 3
    assert f"head fff0000 is not {HEAD}" in capsys.readouterr().out
    assert len(gh.calls()) == 1


@pytest.mark.parametrize("answer", [{"fail": True}, {"out": "not json"}, _out([]), _out({}),
                                    _out({"headRefOid": None})])
def test_no_answer_about_the_head_is_3(gh, answer):
    gh.script(head=[answer])
    assert gh.wait() == 3


def test_no_run_ever_is_4_after_every_try(gh, capsys):
    gh.script(runs=[_out([])])
    assert gh.wait() == 4
    assert gh.slept == [10] * 4
    assert f"no CI run appeared for {HEAD}" in capsys.readouterr().out


@pytest.mark.parametrize("answer", [{"fail": True}, {"out": "not json"}, _out({}), _out(["x"])])
def test_a_gh_with_no_answer_about_runs_is_4_not_green(gh, answer):
    gh.script(runs=[answer])
    assert gh.wait() == 4


def test_a_run_that_appears_late_is_waited_for(gh):
    gh.script(runs=[_out([]), {"fail": True}, _out([_run()])])
    assert gh.wait() == 0
    assert gh.slept == [10, 10]


def test_a_run_that_never_finishes_is_5(gh, capsys):
    gh.script(runs=[_out([_run(status="in_progress", conclusion="")])])
    assert gh.wait() == 5
    assert gh.slept == [20] * 4
    assert f"CI still running after 30 min on {HEAD}" in capsys.readouterr().out


def test_one_unfinished_run_among_finished_ones_is_still_waited_for(gh):
    done, going = _run(), _run(status="queued", conclusion="", name="later")
    # one answer goes on the read that saw a run appear, one on the first of the finish loop
    gh.script(runs=[_out([done, going]), _out([done, going]), _out([done, _run(name="later")])])
    assert gh.wait() == 0
    assert gh.slept == [20]


def test_the_conclusion_comes_from_the_read_that_saw_them_finish(gh):
    going = _run(status="in_progress", conclusion="")
    gh.script(runs=[_out([going]), _out([going]), _out([_run(conclusion="failure")])])
    assert gh.wait() == 2


@pytest.mark.parametrize("flaky", [{"fail": True}, _out([])])
def test_runs_that_vanish_while_waiting_are_never_green(gh, flaky):
    """The script read an empty list here as nothing pending, and then as nothing bad: exit 0."""
    gh.script(runs=[_out([_run(status="in_progress", conclusion="")]), flaky])
    assert gh.wait() == 5


def test_the_full_waits_are_the_scripts_ten_and_thirty_minutes():
    tool = _tool()
    assert tool.APPEAR_TRIES * tool.APPEAR_WAIT_S == 10 * 60
    assert tool.FINISH_TRIES * tool.FINISH_WAIT_S == 30 * 60


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("gh", 60), FileNotFoundError("gh")])
def test_a_hung_or_missing_gh_is_no_answer(gh, monkeypatch, error):
    def run(*a, **k):
        raise error

    monkeypatch.setattr(gh.tool.subprocess, "run", run)
    assert gh.wait() == 3


# --- the arguments: argparse's own usage code is 2, which here would say "red"


@pytest.mark.parametrize("argv", [[], ["7"], ["7", ""], ["", HEAD], ["7", HEAD, "extra"]])
def test_bad_arguments_are_1_and_ask_gh_nothing(gh, argv):
    """`["7", ""]`: an empty head is a prefix of every commit, and the script waved it through."""
    with pytest.raises(SystemExit) as e:
        gh.tool.main(argv)
    assert e.value.code == 1
    assert gh.calls() == []


def test_a_child_process_exits_with_the_code(gh):
    gh.script(head=[_out({"headRefOid": "fff0000"})])
    done = subprocess.run([sys.executable, str(TOOL), "7", HEAD], capture_output=True, text=True,
                          check=False)
    assert done.returncode == 3, done.stderr
    assert len(gh.calls()) == 1


# --- it can't merge


def test_every_gh_call_on_every_road_is_one_of_two_reads(gh):
    roads = ([_out([_run()])], [_out([_run(conclusion="failure")])], [_out([])],
             [_out([_run(status="queued", conclusion="")])])
    for runs in roads:
        gh.script(runs=runs)
        gh.wait()
    gh.script(head=[_out({"headRefOid": "fff"})])
    gh.wait()
    calls = gh.calls()
    assert len(calls) > 5
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
