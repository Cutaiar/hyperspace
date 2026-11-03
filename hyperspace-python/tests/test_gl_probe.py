"""tests/gl_probe.py: glfw.init() is probed in a child process with a hard
timeout and the answer cached. subprocess is stubbed: no window opens."""

import subprocess
import sys

import gl_probe
import pytest


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(gl_probe, "_cache", [])


def _run_returning(code):
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, code)
    return run, calls


def test_a_probe_that_exits_zero_is_available(monkeypatch):
    run, calls = _run_returning(0)
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    assert gl_probe.reason() is None
    cmd, kw = calls[0]
    assert cmd[0] == sys.executable and "glfw.init()" in cmd[-1]
    assert kw["timeout"] == 8.0


def test_a_probe_that_exits_nonzero_says_no_display(monkeypatch):
    run, _ = _run_returning(2)
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    assert gl_probe.reason() == "no display for GL"


def test_a_probe_that_times_out_names_the_alert_and_the_guide(monkeypatch):
    def run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    why = gl_probe.reason()
    assert why == ("glfw.init() did not complete in 8 s: a modal alert or no "
                   "window server; see TESTING-GUIDE")


def test_the_answer_is_cached(monkeypatch):
    run, calls = _run_returning(0)
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    gl_probe.reason()
    gl_probe.reason()
    assert len(calls) == 1


def test_require_skips_with_the_reason_and_passes_when_available(monkeypatch):
    monkeypatch.setattr(gl_probe, "_cache", [gl_probe.STUCK])
    with pytest.raises(pytest.skip.Exception, match="did not complete in 8 s"):
        gl_probe.require()
    monkeypatch.setattr(gl_probe, "_cache", [None])
    gl_probe.require()


def test_a_real_child_that_hangs_is_killed_at_the_timeout():
    """subprocess.run with a timeout really ends a child stuck in init."""
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run([sys.executable, "-c", "import time; time.sleep(60)"],
                       timeout=0.5, check=False)
