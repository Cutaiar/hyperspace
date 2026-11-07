"""The type ratchet (tools/type_ratchet.py, row 788) and the import walls' glob (tests/walls.py).

A new pyright complaint fails, an old one doesn't, and the baseline only falls unless someone
says `--accept`. The one test that runs pyright runs it for real, here in the fast tier, so CI
holds the rule without a step of its own: see ENGINEERING §16, CI, for what it costs.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from walls import family, inside, module_of, shown

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


def test_accept_is_the_one_way_up(tmp_path):
    """A split moves old complaints to a new file; the raise shows in the PR's diff."""
    p = base(tmp_path, {A: {"r": 1}})
    assert run(["--accept"], p, diag(B, "r")) == 0
    assert ratchet.read(p) == (VERSION, {B: {"r": 1}})
    assert run(["--check"], p, diag(B, "r")) == 0


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
    assert run(["--accept"], p, diag(A, "r")) == 0
    assert ratchet.read(p)[0] == VERSION


# ---- a machine without the full sync (CI) ----

def _no_torch(module: str) -> bool:
    return module != "torch"


def test_a_file_that_needs_a_missing_module_isnt_judged():
    """CI has no torch: dream.py complains once more there, and that isn't a new complaint."""
    dream = "hyperspace/dream.py"
    assert ratchet.NEEDS[dream] == "torch"
    p_counts = {dream: {"r": 1}, A: {"r": 1}}
    assert ratchet.judged(p_counts, _no_torch) == {A: {"r": 1}}
    assert ratchet.judged(p_counts, lambda m: True) == p_counts


def test_it_is_judged_again_where_the_module_is(tmp_path):
    dream = "hyperspace/dream.py"
    p = base(tmp_path, {dream: {"r": 1}})
    assert run(["--check"], p, diag(dream, "r"), diag(dream, "r"), found=_no_torch) == 0
    assert run(["--check"], p, diag(dream, "r"), diag(dream, "r")) == 1


def test_only_a_full_sync_writes_the_baseline(tmp_path, capsys):
    """Fewer types means fewer complaints: lowering to CI's count would fail the Mac after."""
    p = base(tmp_path, {A: {"r": 2}})
    before = p.read_text()
    assert run([], p, diag(A, "r"), found=_no_torch) == 2
    assert run(["--accept"], p, diag(A, "r"), found=_no_torch) == 2
    assert p.read_text() == before
    assert "--check" in capsys.readouterr().out
    assert run(["--check"], p, diag(A, "r"), found=_no_torch) == 0


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
    try:
        report = ratchet.run_pyright()
    except ratchet.Unjudged as e:
        if os.environ.get("CI"):        # CI is where the rule holds: never skip it away there
            raise
        pytest.skip(f"pyright can't run here: {e}")
    pin, baseline = ratchet.read(ratchet.BASELINE)
    assert report.version == pin, "the pin and the baseline disagree: see the tool's docstring"
    grown, _ = ratchet.compare(ratchet.judged(baseline), ratchet.judged(report.counts()))
    assert not grown, "new type complaints:\n" + "\n".join(ratchet.describe_new(grown, report))


def test_the_settings_the_baseline_was_made_under_are_there():
    """The ratchet counts what these settings say, so moving one moves every count."""
    import tomllib

    py = tomllib.loads((ROOT / "pyproject.toml").read_text())
    got = py["tool"]["pyright"]
    assert got["include"] == ["hyperspace"]
    assert got["typeCheckingMode"] == "basic" and got["pythonPlatform"] == "Darwin"
    assert any(d.startswith("pyright[nodejs]==") for d in py["dependency-groups"]["dev"])


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


def test_a_wall_on_nothing_fails(pkg):
    with pytest.raises(AssertionError, match="no such module"):
        family("gone", pkg)


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
    assert family(stem)
