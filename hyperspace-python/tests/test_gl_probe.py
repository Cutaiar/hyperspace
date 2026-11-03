"""tests/gl_probe.py: glfw.init() is probed in a child process with a hard
timeout and the answer cached. subprocess is stubbed: no window opens."""

import subprocess
import sys
import time

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
    assert kw["timeout"] == gl_probe.TIMEOUT_S


def test_a_probe_that_exits_nonzero_says_no_display(monkeypatch):
    run, _ = _run_returning(2)
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    assert gl_probe.reason() == "no display for GL"


def test_a_probe_that_times_out_names_the_alert_and_the_guide(monkeypatch):
    def run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    why = gl_probe.reason()
    assert why == gl_probe.STUCK
    assert f"in {gl_probe.TIMEOUT_S:g} s" in why and "ENGINEERING §16" in why


def test_the_answer_is_cached(monkeypatch):
    run, calls = _run_returning(0)
    monkeypatch.setattr(gl_probe.subprocess, "run", run)
    gl_probe.reason()
    gl_probe.reason()
    assert len(calls) == 1


def test_require_skips_with_the_reason_and_passes_when_available(monkeypatch):
    monkeypatch.setattr(gl_probe, "_cache", [gl_probe.STUCK])
    with pytest.raises(pytest.skip.Exception, match="did not complete"):
        gl_probe.require()
    monkeypatch.setattr(gl_probe, "_cache", [None])
    gl_probe.require()


def test_a_child_stuck_in_init_is_a_skip_reason_not_a_hang(monkeypatch):
    """gl_probe's own road with a real child that never answers (a sleep
    standing in for the modal): the cap ends it and the reason is STUCK."""
    monkeypatch.setattr(gl_probe, "PROBE_CODE", "import time; time.sleep(60)")
    monkeypatch.setattr(gl_probe, "TIMEOUT_S", 0.3)
    t = time.monotonic()
    assert gl_probe.reason() == gl_probe.STUCK
    assert time.monotonic() - t < 5
