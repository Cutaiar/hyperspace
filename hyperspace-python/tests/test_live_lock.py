"""The live-device lock (tests/live_lock.py, conftest's
`_live_devices_take_turns`): live tests of two pytest processes take
turns, and so do two workers of one `--dist load` run (row 605); a waiter
skips after a bounded wait — longer while its own run holds it — and the
lock comes free when a test raises. A live test's fixture wider than the
test is refused at collection."""

import multiprocessing as mp
import os
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import live_lock
import pytest

TESTS = Path(__file__).resolve().parent


def _hold(path, held, release, run=""):
    """In another process: take the lock (as `run`), say so, hold it until told."""
    import live_lock

    fd = live_lock.acquire(Path(path), wait_s=5, run=run)
    assert fd is not None
    held.set()
    release.wait(120)       # (set once the caller is done; a safety cap)
    live_lock.release(fd)


def _holder(path, run=""):
    ctx = mp.get_context("spawn")
    held, release = ctx.Event(), ctx.Event()
    p = ctx.Process(target=_hold, args=(str(path), held, release, run))
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


def test_a_waiter_of_the_holders_own_run_waits_longer(tmp_path):
    """The holder wrote its run's id into the file: a waiter of the same run
    waits up to `run_wait_s`, one of another run gives up at `wait_s`."""
    path = tmp_path / "live.lock"
    p, release = _holder(path, run="xdist-R")
    let_go = threading.Timer(0.8, release.set)
    try:
        t = time.monotonic()
        assert live_lock.acquire(path, wait_s=0.2, poll_s=0.05, run="xdist-S",
                                 run_wait_s=10) is None
        assert time.monotonic() - t < 0.7
        let_go.start()
        fd = live_lock.acquire(path, wait_s=0.2, poll_s=0.05, run="xdist-R", run_wait_s=10)
        assert fd is not None and time.monotonic() - t >= 0.75
        assert live_lock.holder(fd) == "xdist-R"
        live_lock.release(fd)
    finally:
        let_go.cancel()
        release.set()
        p.join(10)
    fd = os.open(path, os.O_RDONLY)
    try:
        assert live_lock.holder(fd) == ""       # released: no id left behind
    finally:
        os.close(fd)


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
pytest_collection_modifyitems = _mod.pytest_collection_modifyitems


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


def _inner_pytest(tmp_path, temp, tests=_TESTS, args=("-p", "no:xdist")):
    """Run `tests` in a pytest of their own, with this conftest's fixture
    and collection hook and TMPDIR (where the lock file lives) at `temp`."""
    run = tmp_path / "run"
    run.mkdir()
    (run / "conftest.py").write_text(_CONFTEST.format(
        tests=str(TESTS), conftest=str(TESTS / "conftest.py")))
    (run / "test_inner.py").write_text(textwrap.dedent(tests))
    (run / "pytest.ini").write_text("[pytest]\n")
    env = dict(os.environ, TMPDIR=str(temp), INNER_LOG=str(tmp_path / "log"))
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider",
         *args, "-c", str(run / "pytest.ini"), "--rootdir", str(run),
         str(run / "test_inner.py")],
        cwd=run, env=env, capture_output=True, text=True, timeout=60, check=False)


_TWO_WORKERS = """
import os
import time

import pytest
import live_lock


def _turn(name):
    fd = os.open(live_lock.lock_path(), os.O_RDONLY)
    try:
        held_by = live_lock.holder(fd)
    finally:
        os.close(fd)
    start = time.time()
    time.sleep(0.8)
    with open(os.environ["INNER_LOG"], "a") as f:
        f.write(f"{name} {os.environ.get('PYTEST_XDIST_WORKER')} {held_by} {start} {time.time()}\\n")


@pytest.mark.live
def test_one():
    _turn("one")


@pytest.mark.live
def test_two():
    _turn("two")
"""


def test_two_workers_of_one_load_run_take_turns_and_neither_skips(tmp_path):
    """`--dist load` (row 605) hands the two live tests to two workers at
    once: the lock runs them one after the other, and the second, waiting
    past `WAIT_S` (0.3 s in the inner run) on its own run's holder, is not
    skipped."""
    temp = tmp_path / "temp"
    temp.mkdir()
    out = _inner_pytest(tmp_path, temp, _TWO_WORKERS, ("-n", "2", "--dist", "load"))
    assert "2 passed" in out.stdout, out.stdout + out.stderr
    rows = [line.split() for line in (tmp_path / "log").read_text().splitlines()]
    assert sorted(r[0] for r in rows) == ["one", "two"]
    assert {r[1] for r in rows} == {"gw0", "gw1"}               # two workers
    assert len({r[2] for r in rows}) == 1 and rows[0][2].startswith("xdist-")  # one run's id
    (_, first_ends), (second_starts, _) = sorted((float(r[3]), float(r[4])) for r in rows)
    assert first_ends <= second_starts, f"the two live tests overlapped: {rows}"


_WIDE = """
import pytest


@pytest.fixture(scope="module")
def device():
    yield "opened"


@pytest.mark.live
def test_a_live_test_on_a_module_fixture(device):
    pass
"""


def test_a_live_test_on_a_module_scoped_fixture_is_refused_at_collection(tmp_path):
    """Row 589's caveat: the lock is per test, so a module- or
    session-scoped fixture would open its device outside it."""
    temp = tmp_path / "temp"
    temp.mkdir()
    out = _inner_pytest(tmp_path, temp, _WIDE)
    assert out.returncode != 0
    text = out.stdout + out.stderr
    assert "outside the live lock" in text and "uses device (module-scoped)" in text, text


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


def test_a_lock_file_that_cannot_be_opened_is_a_skip_reason(tmp_path, monkeypatch):
    def refused(*a, **k):
        raise PermissionError(13, "Permission denied")     # (another account's file)
    monkeypatch.setattr(live_lock, "_open", refused)
    with live_lock.held(tmp_path / "live.lock", wait_s=0) as why_not:
        assert why_not and "cannot be taken" in why_not and "Permission denied" in why_not


def test_a_flock_error_closes_the_file_and_is_a_skip_reason(tmp_path, monkeypatch):
    opened, closed = [], []

    def opening(*a, **k):
        opened.append(os.open(*a, **k))
        return opened[-1]

    def closing(fd):
        closed.append(fd)
        os.close(fd)

    def no_locks(fd, op):
        raise OSError(77, "No locks available")
    monkeypatch.setattr(live_lock, "_open", opening)
    monkeypatch.setattr(live_lock, "_close", closing)
    monkeypatch.setattr(live_lock, "_flock", no_locks)
    with live_lock.held(tmp_path / "live.lock", wait_s=0) as why_not:
        assert "No locks available" in why_not
    assert len(opened) == 1 and closed == opened


def test_a_skip_inside_the_block_chains_no_lock_error(tmp_path, monkeypatch):
    def refused(*a, **k):
        raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(live_lock, "_open", refused)
    with (pytest.raises(pytest.skip.Exception) as e,
          live_lock.held(tmp_path / "live.lock", wait_s=0) as why_not):
        pytest.skip(why_not)
    assert e.value.__context__ is None


def test_the_lock_file_is_the_accounts_own():
    assert str(os.getuid()) in live_lock.lock_path().name
