"""The live-device lock (tests/live_lock.py, conftest's
`_live_devices_take_turns`): live tests of two pytest processes take
turns, a waiter skips after a bounded wait, and the lock comes free when
a test raises."""

import multiprocessing as mp
import os
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import live_lock

TESTS = Path(__file__).resolve().parent


def _hold(path, held, release):
    """In another process: take the lock, say so, hold it until told."""
    import live_lock

    fd = live_lock.acquire(Path(path), wait_s=5)
    assert fd is not None
    held.set()
    release.wait(120)       # (set once the caller is done; a safety cap)
    live_lock.release(fd)


def _holder(path):
    ctx = mp.get_context("spawn")
    held, release = ctx.Event(), ctx.Event()
    p = ctx.Process(target=_hold, args=(str(path), held, release))
    p.start()
    assert held.wait(30), "the holder never took the lock"
    return p, release


def test_a_second_process_cannot_have_it_and_gives_up_in_bounded_time(tmp_path):
    path = tmp_path / "live.lock"
    p, release = _holder(path)
    try:
        t = time.monotonic()
        assert live_lock.acquire(path, wait_s=0.3, poll_s=0.05) is None
        assert 0.25 < time.monotonic() - t < 5
    finally:
        release.set()
        p.join(10)
    fd = live_lock.acquire(path, wait_s=1)        # free once the holder let go
    assert fd is not None
    live_lock.release(fd)


def test_a_waiter_gets_it_when_the_holder_lets_go(tmp_path):
    path = tmp_path / "live.lock"
    p, release = _holder(path)
    let_go = threading.Timer(0.4, release.set)
    t = time.monotonic()
    let_go.start()
    try:
        with live_lock.held(path, wait_s=10, poll_s=0.05) as why_not:
            assert why_not is None
            assert time.monotonic() - t >= 0.35
    finally:
        let_go.cancel()
        release.set()
        p.join(10)


def test_a_dead_holder_leaves_it_free(tmp_path):
    path = tmp_path / "live.lock"
    p, _release = _holder(path)
    p.kill()
    p.join(10)
    fd = live_lock.acquire(path, wait_s=2, poll_s=0.05)
    assert fd is not None
    live_lock.release(fd)


def test_held_releases_when_the_block_raises(tmp_path):
    path = tmp_path / "live.lock"
    try:
        with live_lock.held(path, wait_s=1) as why_not:
            assert why_not is None
            raise RuntimeError("the test failed")
    except RuntimeError:
        pass
    fd = live_lock.acquire(path, wait_s=0)
    assert fd is not None
    live_lock.release(fd)


# ---------------------------------------- the conftest fixture, in a pytest of its own

_CONFTEST = """
import importlib.util
import sys

sys.path.insert(0, {tests!r})
import live_lock

live_lock.WAIT_S = 0.3
_spec = importlib.util.spec_from_file_location("hs_conftest", {conftest!r})
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_live_devices_take_turns = _mod._live_devices_take_turns


def pytest_configure(config):
    config.addinivalue_line("markers", "live: live devices")
"""

_TESTS = """
import os
import fcntl

import pytest
import live_lock


def _free():
    fd = os.open(live_lock.lock_path(), os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    except BlockingIOError:
        return False
    finally:
        os.close(fd)


@pytest.mark.live
def test_a_live_test_holds_it_and_raises():
    assert not _free()
    raise RuntimeError("a live test failed")


def test_b_after_it_the_lock_is_free():
    assert _free()


def test_c_a_plain_test_never_takes_it():
    assert _free()
"""


def _inner_pytest(tmp_path, temp):
    """Run _TESTS in a pytest of their own, with this conftest's fixture
    and TMPDIR (where the lock file lives) at `temp`."""
    run = tmp_path / "run"
    run.mkdir()
    (run / "conftest.py").write_text(_CONFTEST.format(
        tests=str(TESTS), conftest=str(TESTS / "conftest.py")))
    (run / "test_inner.py").write_text(textwrap.dedent(_TESTS))
    (run / "pytest.ini").write_text("[pytest]\n")
    env = dict(os.environ, TMPDIR=str(temp))
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider",
         "-p", "no:xdist", "-c", str(run / "pytest.ini"), "--rootdir", str(run),
         str(run / "test_inner.py")],
        cwd=run, env=env, capture_output=True, text=True, timeout=60, check=False)


def test_the_fixture_holds_it_for_a_live_test_and_lets_go_when_it_raises(tmp_path):
    temp = tmp_path / "temp"
    temp.mkdir()
    out = _inner_pytest(tmp_path, temp)
    assert "1 failed, 2 passed" in out.stdout, out.stdout + out.stderr
    assert "a live test failed" in out.stdout


def test_the_fixture_skips_a_live_test_another_run_holds_it_for(tmp_path):
    temp = tmp_path / "temp"
    temp.mkdir()
    p, release = _holder(temp / live_lock.lock_path().name)
    try:
        out = _inner_pytest(tmp_path, temp)
    finally:
        release.set()
        p.join(10)
    assert "1 skipped" in out.stdout, out.stdout + out.stderr
    assert live_lock.SKIP_REASON in out.stdout
    # (the plain tests ran, and found it held by the other process)
    assert "2 failed" in out.stdout


def test_a_lock_file_that_cannot_be_opened_is_a_skip_reason(tmp_path):
    path = tmp_path / "live.lock"
    path.write_text("")
    path.chmod(0o400)                   # (as if another account owned it)
    with live_lock.held(path, wait_s=0) as why_not:
        assert why_not and "cannot be taken" in why_not


def test_a_flock_error_closes_the_file_and_is_a_skip_reason(tmp_path, monkeypatch):
    opened, closed = [], []
    real_open, real_close = os.open, os.close
    monkeypatch.setattr(live_lock.os, "open", lambda *a: opened.append(real_open(*a)) or opened[-1])
    monkeypatch.setattr(live_lock.os, "close", lambda fd: closed.append(fd) or real_close(fd))

    def no_locks(fd, op):
        raise OSError(77, "No locks available")
    monkeypatch.setattr(live_lock.fcntl, "flock", no_locks)
    with live_lock.held(tmp_path / "live.lock", wait_s=0) as why_not:
        assert "No locks available" in why_not
    assert opened and closed == opened


def test_the_lock_file_is_the_accounts_own():
    assert str(os.getuid()) in live_lock.lock_path().name
