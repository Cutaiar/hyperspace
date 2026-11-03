"""tests/gl_probe.py: glfw.init() is probed in a child process with a hard
timeout and the answer cached. The child is stubbed (no window opens),
except in the last tests, whose real children never touch glfw."""

import subprocess
import sys
import time

import gl_probe
import pytest


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(gl_probe, "_cache", [])


def _child_returning(code, err=""):
    calls = []

    def run(cmd, timeout):
        calls.append((cmd, timeout))
        return code, err
    return run, calls


def test_a_probe_that_exits_zero_is_available(monkeypatch):
    run, calls = _child_returning(0)
    monkeypatch.setattr(gl_probe, "_run_child", run)
    assert gl_probe.reason() is None
    cmd, timeout = calls[0]
    assert cmd[:3] == [sys.executable, "-c", gl_probe.PROBE_CODE]
    assert "glfw.init()" in cmd[2]
    assert tuple(cmd[3:]) == gl_probe.APPKIT_ARGS == ("-ApplePersistenceIgnoreState", "YES")
    assert timeout == gl_probe.TIMEOUT_S


def test_init_saying_no_is_no_display_with_its_stderr(monkeypatch):
    run, _ = _child_returning(gl_probe.INIT_FALSE, "GLFWError: no display\n")
    monkeypatch.setattr(gl_probe, "_run_child", run)
    assert gl_probe.reason() == f"{gl_probe.NO_DISPLAY}: GLFWError: no display"


def test_any_other_exit_is_a_failed_probe_with_its_stderr(monkeypatch):
    run, _ = _child_returning(1, "Traceback ...\nModuleNotFoundError: No module named 'glfw'\n")
    monkeypatch.setattr(gl_probe, "_run_child", run)
    why = gl_probe.reason()
    assert why.startswith("the glfw probe failed (exit 1): ")
    assert "No module named 'glfw'" in why


def test_a_probe_that_times_out_names_the_alert_and_the_guide(monkeypatch):
    def run(cmd, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)
    monkeypatch.setattr(gl_probe, "_run_child", run)
    why = gl_probe.reason()
    assert why == gl_probe.STUCK
    assert f"in {gl_probe.TIMEOUT_S:g} s" in why and "ENGINEERING §16" in why


def test_the_answer_is_cached(monkeypatch):
    run, calls = _child_returning(0)
    monkeypatch.setattr(gl_probe, "_run_child", run)
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


def test_a_child_that_ignores_sigterm_is_killed_after_a_second():
    """SIGTERM first (a clean exit where the child allows it), SIGKILL a
    second later."""
    code = ("import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "time.sleep(60)")
    t = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        gl_probe._run_child([sys.executable, "-c", code], 0.5)
    assert 1.3 < time.monotonic() - t < 5
