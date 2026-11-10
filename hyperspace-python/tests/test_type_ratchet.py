"""The type ratchet (tools/type_ratchet.py, row 788) and the import walls' glob (tests/walls.py).

A new pyright complaint fails, an old one doesn't, and no rule's total rises unless someone
says `--raise-baseline`. The one test that runs pyright runs it for real. In the fast tier on a Mac; on
CI in tests.yml's `lint and types` job, beside the fast tier's shards rather than on one of their workers,
where it was the longest test (row 870; ENGINEERING §16, CI).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

import pytest
from walls import family, inside, module_of, reaches, shown

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("type_ratchet", ROOT / "tools" / "type_ratchet.py")
assert _spec and _spec.loader
ratchet = importlib.util.module_from_spec(_spec)
sys.modules["type_ratchet"] = ratchet      # a dataclass looks its module up while it's built
_spec.loader.exec_module(ratchet)

A, B = "hyperspace/a.py", "hyperspace/b.py"
VERSION = "1.1.414"


def diag(file: str, rule: str | None, line: int = 0, severity: str = "error") -> dict:
    d = {"file": str(ROOT / file), "severity": severity, "message": "bad\nmore",
         "range": {"start": {"line": line, "character": 0}}}
    return d if rule is None else {**d, "rule": rule}


def doc(*diags: dict, version: str = VERSION, files: int = 2) -> dict:
    return {"version": version, "generalDiagnostics": list(diags),
            "summary": {"filesAnalyzed": files}}


def base(tmp_path: Path, files: dict, version: str = VERSION) -> Path:
    p = tmp_path / "baseline.json"
    p.write_text(json.dumps({"pyright": version, "files": files}))
    return p


def run(args: list[str], path: Path, *diags: dict, found=lambda m: True, version: str = VERSION):
    return ratchet.main(args, pyright=lambda: ratchet.parse(doc(*diags, version=version)),
                        baseline=path, found=found)


# ---- what fails and what doesn't ----

def test_an_old_complaint_passes(tmp_path):
    p = base(tmp_path, {A: {"r": 2}})
    assert run(["--check"], p, diag(A, "r"), diag(A, "r", 9)) == 0


def test_moving_inside_a_file_is_nothing(tmp_path):
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--check"], p, diag(A, "r", 500)) == 0


def test_one_more_in_a_file_and_rule_fails_and_names_them(tmp_path, capsys):
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--check"], p, diag(A, "r", 4), diag(A, "r", 7)) == 1
    out = capsys.readouterr().out
    assert f"{A}: r: 2, baseline 1" in out
    assert f"{A}:5: bad" in out and f"{A}:8: bad" in out and "more" not in out


def test_a_new_rule_in_an_old_file_fails(tmp_path):
    assert run(["--check"], base(tmp_path, {A: {"r": 5}}), diag(A, "s")) == 1


def test_a_complaint_in_a_new_file_fails(tmp_path):
    assert run(["--check"], base(tmp_path, {A: {"r": 1}}), diag(A, "r"), diag(B, "r")) == 1


def test_fewer_in_one_file_doesnt_buy_more_in_another(tmp_path):
    p = base(tmp_path, {A: {"r": 3}, B: {"r": 1}})
    assert run(["--check"], p, diag(A, "r"), diag(B, "r"), diag(B, "r")) == 1


def test_a_warning_counts_and_a_note_doesnt(tmp_path):
    p = base(tmp_path, {})
    assert run(["--check"], p, diag(A, "r", severity="information")) == 0
    assert run(["--check"], p, diag(A, "r", severity="warning")) == 1


def test_a_complaint_with_no_rule_counts(tmp_path):
    assert run(["--check"], base(tmp_path, {}), diag(A, None)) == 1
    assert run(["--check"], base(tmp_path, {A: {"(no rule)": 1}}), diag(A, None)) == 0


# ---- the baseline only falls ----

def test_the_tool_lowers_where_errors_went(tmp_path, capsys):
    p = base(tmp_path, {A: {"r": 3, "s": 1}, B: {"r": 1}})
    assert run([], p, diag(A, "r")) == 0
    assert ratchet.read(p)[1] == {A: {"r": 1}}
    assert "4 gone, baseline lowered" in capsys.readouterr().out


def test_a_lowered_count_then_holds(tmp_path):
    p = base(tmp_path, {A: {"r": 2}})
    assert run([], p, diag(A, "r")) == 0
    assert run(["--check"], p, diag(A, "r"), diag(A, "r")) == 1


def test_lowering_never_lets_a_new_complaint_in(tmp_path):
    p = base(tmp_path, {A: {"r": 3}})
    assert run([], p, diag(A, "r"), diag(B, "r")) == 1
    assert ratchet.read(p)[1] == {A: {"r": 1}}


def test_check_says_what_went_and_writes_nothing(tmp_path, capsys):
    p = base(tmp_path, {A: {"r": 3}})
    before = p.read_text()
    assert run(["--check"], p, diag(A, "r")) == 0
    assert p.read_text() == before
    assert "2 gone" in capsys.readouterr().out


def test_nothing_gone_writes_nothing(tmp_path):
    p = base(tmp_path, {A: {"r": 1}})
    before = p.read_text()
    assert run([], p, diag(A, "r")) == 0
    assert p.read_text() == before


def test_accept_takes_a_split_that_moved_old_complaints(tmp_path):
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--check"], p, diag(B, "r")) == 1
    assert run(["--accept"], p, diag(B, "r")) == 0
    assert ratchet.read(p) == (VERSION, {B: {"r": 1}})
    assert run(["--check"], p, diag(B, "r")) == 0


def test_accept_refuses_a_split_that_swept_a_new_complaint_in(tmp_path, capsys):
    p = base(tmp_path, {A: {"r": 1}})
    before = p.read_text()
    assert run(["--accept"], p, diag(B, "r"), diag(B, "r")) == 1
    assert p.read_text() == before
    assert "r: 2 over the app, baseline 1" in capsys.readouterr().out


def test_accept_refuses_a_rule_that_is_new_to_the_app(tmp_path):
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--accept"], p, diag(B, "s")) == 1


def test_raise_is_the_one_way_up(tmp_path):
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--raise-baseline"], p, diag(B, "r"), diag(B, "r")) == 0
    assert ratchet.read(p) == (VERSION, {B: {"r": 2}})


def test_the_file_is_one_rule_a_line_and_sorted(tmp_path):
    p = tmp_path / "b.json"
    ratchet.write(p, VERSION, {B: {"s": 1, "r": 2}, A: {"r": 1}})
    lines = p.read_text().splitlines()
    assert lines[lines.index(f'    "{A}": {{') + 1] == '      "r": 1'
    assert lines.index(f'    "{A}": {{') < lines.index(f'    "{B}": {{')
    assert p.read_text().endswith("}\n")


# ---- never read "couldn't run" as "no complaints" ----

def test_no_files_analysed_cant_be_judged(tmp_path, capsys):
    p = base(tmp_path, {})
    code = ratchet.main(["--check"], pyright=lambda: ratchet.parse(doc(files=0)), baseline=p)
    assert code == 2 and "no files" in capsys.readouterr().out


def test_pyright_not_running_cant_be_judged(tmp_path):
    def broken():
        raise ratchet.Unjudged("no node")
    assert ratchet.main(["--check"], pyright=broken, baseline=base(tmp_path, {})) == 2


def test_another_pyright_cant_be_judged_until_the_pin_moves(tmp_path, capsys):
    p = base(tmp_path, {A: {"r": 1}}, version="1.1.1")
    assert run(["--check"], p, diag(A, "r")) == 2
    assert "1.1.1" in capsys.readouterr().out
    assert run(["--accept"], p, diag(A, "r")) == 2
    assert run(["--raise-baseline"], p, diag(A, "r")) == 0
    assert ratchet.read(p)[0] == VERSION


def test_an_empty_range_has_no_range_and_is_still_a_complaint(tmp_path, capsys):
    """Pyright leaves `range` out when it's empty."""
    d = diag(A, "r")
    del d["range"]
    assert run(["--check"], base(tmp_path, {}), d) == 1
    assert f"{A}:0: bad" in capsys.readouterr().out


@pytest.mark.parametrize("bad", [
    {"version": VERSION, "summary": {"filesAnalyzed": 2}},                     # no diagnostics
    {"generalDiagnostics": [], "summary": {"filesAnalyzed": 2}},               # no version
    doc({"file": str(ROOT / A), "severity": "error"}),                         # no message
    doc({**diag(A, "r"), "file": "/elsewhere/a.py"}),                          # outside the root
    doc({**diag(A, "reportMissingImports"), "message": "no quotes"}),
])
def test_output_it_cant_read_cant_be_judged_not_a_new_complaint(tmp_path, bad):
    code = ratchet.main(["--check"], pyright=lambda: ratchet.parse(bad),
                        baseline=base(tmp_path, {}), found=lambda m: True)
    assert code == 2


@pytest.mark.parametrize("text", ["not json", "[]", '{"pyright": "1"}', '{"files": {}}',
                                  '{"pyright": "1", "files": []}',
                                  '{"pyright": "1", "files": {"a": {"r": "x"}}}',
                                  '{"pyright": 1, "files": {}}'])
def test_a_bad_baseline_cant_be_judged(tmp_path, text):
    p = tmp_path / "b.json"
    p.write_text(text)
    assert run(["--check"], p) == 2
    assert run(["--accept"], p) == 2


def test_a_missing_baseline_cant_be_judged(tmp_path):
    assert run(["--check"], tmp_path / "none.json") == 2


def test_nothing_is_left_running_when_pyright_times_out(tmp_path):
    """The wrapper's node child, about 1 GB, goes with it: a stand-in with a child of its own."""
    pid_file = tmp_path / "pid"
    stand_in = tmp_path / "stand_in.py"
    stand_in.write_text(
        "import pathlib, subprocess, sys, time\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(kid.pid))\n"
        "time.sleep(60)\n")
    with pytest.raises(subprocess.TimeoutExpired):
        ratchet._run([sys.executable, str(stand_in)], 3)
    kid = int(pid_file.read_text())
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(kid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(kid, 9)
    pytest.fail("the stand-in's child outlived the timeout")


# ---- missing imports ----

def missing(name: str) -> dict:
    return {**diag(A, "reportMissingImports"), "message": f'Import "{name}" could not be resolved'}


@pytest.mark.parametrize("name", [".routing_old", "hyperspace.routing_old", "nosuchpackage",
                                  "..routing.old"])
def test_a_stale_import_of_ours_or_a_typo_is_a_complaint(tmp_path, name):
    assert run(["--check"], base(tmp_path, {}), missing(name)) == 1


@pytest.mark.parametrize("name", ["torch", "torch.nn", "objc", "Vision", "leap"])
def test_a_known_optional_package_missing_is_not(tmp_path, name):
    assert run(["--check"], base(tmp_path, {}), missing(name)) == 0


# ---- a machine without the full sync (CI) ----

def _ci(module: str) -> bool:
    return module not in ratchet.FULL_SYNC


DREAM = "hyperspace/dream.py"


def test_the_syncs_are_told_apart():
    assert ratchet.sync_of(lambda m: True) == "full"
    assert ratchet.sync_of(_ci) == "ci"
    assert ratchet.sync_of(lambda m: m != "torch") == "mixed"


def test_ci_is_allowed_the_known_difference_and_no_more(tmp_path):
    """dream.py complains once more without torch: that one passes, and a second one is new."""
    p = base(tmp_path, {DREAM: {"reportOptionalMemberAccess": 1}})
    two = [diag(DREAM, "reportOptionalMemberAccess")] * 2
    assert run(["--check"], p, *two, found=_ci) == 0
    assert run(["--check"], p, *two) == 1
    assert run(["--check"], p, *two, diag(DREAM, "reportOptionalMemberAccess"), found=_ci) == 1


def test_ci_has_no_spare_room_where_it_sees_fewer(tmp_path):
    """pinch.py has two fewer there: the two freed places can't take a new complaint."""
    pinch = "hyperspace/pinch.py"
    rule = "reportAttributeAccessIssue"
    p = base(tmp_path, {pinch: {rule: 3}})
    assert ratchet.CI_SYNC[pinch] == {rule: -2}
    assert run(["--check"], p, diag(pinch, rule), found=_ci) == 0
    assert run(["--check"], p, diag(pinch, rule), diag(pinch, rule), found=_ci) == 1


def test_a_difference_never_makes_a_limit_negative():
    got = ratchet.limits({}, "ci")
    assert all(n >= 0 for rules in got.values() for n in rules.values())
    assert ratchet.limits({A: {"r": 1}}, "full") == {A: {"r": 1}}


def test_only_a_full_sync_writes_the_baseline(tmp_path, capsys):
    """Fewer types means fewer complaints: lowering to CI's count would fail the Mac after."""
    p = base(tmp_path, {A: {"r": 2}})
    before = p.read_text()
    assert run([], p, diag(A, "r"), found=_ci) == 2
    assert run(["--accept"], p, diag(A, "r"), found=_ci) == 2
    assert run(["--raise-baseline"], p, diag(A, "r"), found=_ci) == 2
    assert p.read_text() == before
    assert "--check" in capsys.readouterr().out
    assert run(["--check"], p, diag(A, "r"), found=_ci) == 0
    assert p.read_text() == before


def test_a_mixed_sync_cant_be_judged(tmp_path, capsys):
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--check"], p, diag(A, "r"), found=lambda m: m != "torch") == 2
    assert "can't be judged" in capsys.readouterr().out


# ---- the real thing ----

def test_the_tool_imports_nothing_of_the_app_and_no_gl():
    code = ("import runpy, sys; runpy.run_path(sys.argv[1], run_name='ratchet'); "
            "print([m for m in sys.modules if m.split('.')[0] in "
            "('hyperspace', 'moderngl', 'glfw', 'OpenGL', 'imgui_bundle', 'numpy')])")
    done = subprocess.run([sys.executable, "-c", code, str(ROOT / "tools" / "type_ratchet.py")],
                          capture_output=True, text=True, timeout=60, check=True)
    assert done.stdout.strip() == "[]"


@pytest.mark.timeout(300)
def test_no_new_complaint_in_the_app():
    """The rule itself. 12-22 s of one worker on the Mac, under the fast tier's other workers."""
    sync = ratchet.sync_of()
    if sync == "mixed":
        pytest.skip("a mixed sync can't be judged: see the tool's sync_of")
    try:
        report = ratchet.run_pyright()
    except ratchet.Unjudged as e:
        if os.environ.get("CI"):        # CI is where the rule holds: never skip it away there
            raise
        pytest.skip(f"pyright can't run here: {e}")
    pin, baseline = ratchet.read(ratchet.BASELINE)
    assert report.version == pin, "the pin and the baseline disagree: see the tool's docstring"
    grown, gone = ratchet.compare(ratchet.limits(baseline, sync), report.counts())
    assert not grown, "new type complaints:\n" + "\n".join(ratchet.describe_new(grown, report))
    if gone:                            # an old rule's fix isn't a failure: see row 788
        warnings.warn(f"{sync} sync, under the baseline: {gone}", stacklevel=1)


def test_the_settings_the_baseline_was_made_under_are_there():
    """The ratchet counts what these settings say, so moving one moves every count."""
    import tomllib

    py = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert py["tool"]["pyright"] == {
        "include": ["hyperspace"],
        "exclude": ["hyperspace/dkit/dev"],   # dkit's workbench: tooling, as tests/ is
        "typeCheckingMode": "basic",
        "pythonVersion": "3.12",
        "pythonPlatform": "Darwin",
        "reportMissingModuleSource": False,
    }
    assert any(d.startswith("pyright[nodejs]==") for d in py["dependency-groups"]["dev"])
    # either of these would take over from the table above
    assert not (ROOT / "pyrightconfig.json").exists()
    assert not (ROOT.parent / "pyrightconfig.json").exists()


# ---- the walls' glob: a split stays behind its wall ----

@pytest.fixture
def pkg(tmp_path):
    for name in ("audio.py", "audio_capture.py", "audiobook.py", "audio/__init__.py",
                 "audio/deep/x.py", "other.py"):
        f = tmp_path / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("")
    return tmp_path


def test_a_family_is_the_module_its_split_and_its_package(pkg):
    assert [shown(f, pkg) for f in family("audio", pkg)] == [
        "audio/__init__.py", "audio/deep/x.py", "audio.py", "audio_capture.py"]


def test_a_stem_with_no_file_is_the_file_it_should_be_and_collection_goes_on(pkg):
    """family runs while pytest collects, so it can't raise: the tests reading it fail by name."""
    assert family("gone", pkg) == [pkg / "gone.py"]
    assert not family("gone", pkg)[0].is_file()


def test_reaches_says_what_each_import_names(pkg):
    f = pkg / "audio/deep/x.py"
    f.write_text(
        "import os\nimport hyperspace.ui.x\nfrom hyperspace import tapers\nfrom .. import sib\n"
        "from ...ui_pane import y\nfrom hyperspace.deck import d\n"
        "def later():\n    import glfw\n    from . import near\n"
        "class C:\n    from .kid import z\n")
    assert [(r.ours, r.lazy) for r in reaches(f, pkg)] == [
        (None, False), (("ui", "x"), False), (("tapers",), False), (("audio", "sib"), False),
        (("ui_pane",), False), (("deck",), False), (None, True), (("audio", "deep", "near"), True),
        (("audio", "deep", "kid"), False)]


def test_a_relative_import_resolves_from_where_the_file_sits(pkg):
    assert inside(pkg / "audio.py", "tapers", 1, pkg) == ("tapers",)
    assert inside(pkg / "audio_capture.py", "ui.x", 1, pkg) == ("ui", "x")
    assert inside(pkg / "audio/deep/x.py", "y", 1, pkg) == ("audio", "deep", "y")
    assert inside(pkg / "audio/deep/x.py", "ui", 3, pkg) == ("ui",)
    assert inside(pkg / "audio/__init__.py", "y", 1, pkg) == ("audio", "y")
    assert inside(pkg / "audio.py", "ui", 2, pkg) is None
    assert module_of(pkg / "audio/__init__.py", pkg) == ("audio",)


@pytest.mark.parametrize("stem", ["audio", "analysis", "analyzer", "bands", "offline", "envelope",
                                  "tempo", "lfo", "routing", "routing_sources", "library", "hands"])
def test_every_module_a_wall_names_is_there(stem):
    """A rename takes its wall with it, or fails here by name."""
    assert all(f.is_file() for f in family(stem))
