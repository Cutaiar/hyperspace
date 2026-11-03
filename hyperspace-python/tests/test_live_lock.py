"""The live-device lock (tests/live_lock.py, conftest's
`pytest_runtest_protocol` and `pytest_runtest_setup`): live tests of two
pytest processes take turns, and so do two workers of one `--dist load`
run (row 605); a waiter skips, saying why, after a bounded wait behind
another run or a holder that names none, and waits on behind its own
run; the wait is outside the per-test timeout; the lock comes free when
a test raises. A live test's fixture wider than the test is an error by
name before it is set up."""

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


def test_a_waiter_of_the_holders_own_run_waits_until_it_lets_go(tmp_path):
    """The holder wrote its run's id into the file: a waiter of another run
    gives up at `wait_s`, saying whose run; one of the same run waits on
    past both bounds until the holder lets go (2 s here)."""
    path = tmp_path / "live.lock"
    p, release = _holder(path, run="xdist-R")
    let_go = threading.Timer(2.0, release.set)
    try:
        fd, why = live_lock.wait_for(path, wait_s=0.2, poll_s=0.05, run="xdist-S",
                                     run_wait_s=0.2)
        assert fd is None and live_lock.SKIP_REASON in why and "xdist-R" in why, why
        t = time.monotonic()
        let_go.start()
        fd, why = live_lock.wait_for(path, wait_s=0.2, poll_s=0.05, run="xdist-R",
                                     run_wait_s=0.2)
        assert fd is not None and why == ""
        assert time.monotonic() - t >= 1.9
        assert live_lock.holder(fd) == f"xdist-R:{os.getpid()}"
        live_lock.release(fd)
    finally:
        let_go.cancel()
        release.set()
        p.join(10)


def test_an_own_run_id_whose_pid_is_gone_is_a_holder_that_names_none(tmp_path):
    """A killed worker's id left under an older build's lock (which writes
    none): this run's id with a dead pid is waited for `run_wait_s`, not
    for ever."""
    path = tmp_path / "live.lock"
    p, release = _holder(path)                  # an older build: writes no id
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    fd = os.open(path, os.O_RDWR)
    os.pwrite(fd, f"xdist-R:{dead.pid}".encode(), 0)
    os.close(fd)
    try:
        fd, why = live_lock.wait_for(path, wait_s=0.1, poll_s=0.05, run="xdist-R",
                                     run_wait_s=0.5)
        assert fd is None and why.startswith(live_lock.UNKNOWN_REASON), why
    finally:
        release.set()
        p.join(10)


def test_each_holder_is_counted_on_its_own(tmp_path, monkeypatch):
    """Time behind a holder that names no run does not count toward
    another run's bound, and the reason names the holder whose bound ran
    out (the file is read through `holder`, scripted here)."""
    path = tmp_path / "live.lock"
    p, release = _holder(path)
    seen = iter([""] * 6 + ["xdist-S:1"] * 1000)
    monkeypatch.setattr(live_lock, "holder", lambda fd: next(seen))
    try:
        fd, why = live_lock.wait_for(path, wait_s=0.5, poll_s=0.1, run="xdist-R",
                                     run_wait_s=5.0)
    finally:
        release.set()
        p.join(10)
    # ~0.6 s behind "no id" (under its 5 s), then 0.5 s behind xdist-S: its bound
    assert fd is None and live_lock.SKIP_REASON in why and "(xdist-S)" in why, why


def test_a_holder_that_names_no_run_is_waited_for_run_wait_s_and_said(tmp_path):
    """An older build's holder writes no id: a waiter with a run waits the
    longer `run_wait_s` for it, not `wait_s`, and says so when it gives up."""
    path = tmp_path / "live.lock"
    p, release = _holder(path)                  # (no id: the file stays empty)
    try:
        t = time.monotonic()
        fd, why = live_lock.wait_for(path, wait_s=0.1, poll_s=0.05, run="xdist-R",
                                     run_wait_s=1.0)
        assert fd is None and why.startswith(live_lock.UNKNOWN_REASON), why
        assert time.monotonic() - t >= 0.95
    finally:
        release.set()
        p.join(10)


def test_a_holder_writes_run_and_pid_and_a_release_clears_them(tmp_path):
    path = tmp_path / "live.lock"
    fd = live_lock.acquire(path, wait_s=0, run="xdist-a-long-run-id")
    live_lock.release(fd)
    fd = live_lock.acquire(path, wait_s=0, run="pid-7")
    assert live_lock.holder(fd) == f"pid-7:{os.getpid()}"       # (no long id's tail)
    assert live_lock.run_of(live_lock.holder(fd)) == ("pid-7", os.getpid())
    live_lock.release(fd)
    fd = os.open(path, os.O_RDONLY)
    try:
        assert live_lock.holder(fd) == ""
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
import os
import sys

sys.path.insert(0, {tests!r})
import live_lock

live_lock.WAIT_S = float(os.environ.get("INNER_WAIT_S", "0.3"))
live_lock.RUN_WAIT_S = 0.6
_spec = importlib.util.spec_from_file_location("hs_conftest", {conftest!r})
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
pytest_runtest_protocol = _mod.pytest_runtest_protocol
pytest_runtest_setup = _mod.pytest_runtest_setup

if os.environ.get("INNER_SIGNAL"):          # say when the wait starts, whom it saw, how long
    import time

    _real_wait_for = live_lock.wait_for

    def _signalled_wait_for(path=None, *a, **k):
        sig = os.environ["INNER_SIGNAL"]
        fd = os.open(path or live_lock.lock_path(), os.O_RDWR | os.O_CREAT, 0o600)
        who = live_lock.holder(fd)
        os.close(fd)
        with open(sig + ".tmp", "w") as f:
            f.write(who)
        os.replace(sig + ".tmp", sig)
        t = time.monotonic()
        out = _real_wait_for(path, *a, **k)
        with open(sig + ".waited", "w") as f:
            f.write(str(time.monotonic() - t))
        return out

    live_lock.wait_for = _signalled_wait_for


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


def _inner_pytest(tmp_path, temp, tests=_TESTS, args=("-p", "no:xdist"), env=None):
    """Run `tests` in a pytest of their own, with this conftest's fixture
    and collection hook and TMPDIR (where the lock file lives) at `temp`."""
    run = tmp_path / "run"
    run.mkdir()
    (run / "conftest.py").write_text(_CONFTEST.format(
        tests=str(TESTS), conftest=str(TESTS / "conftest.py")))
    (run / "test_inner.py").write_text(textwrap.dedent(tests))
    (run / "pytest.ini").write_text("[pytest]\n")
    env = dict(os.environ, TMPDIR=str(temp), INNER_LOG=str(tmp_path / "log"), **(env or {}))
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
    runs = {live_lock.run_of(r[2])[0] for r in rows}
    assert len(runs) == 1 and runs.pop().startswith("xdist-")    # one run's id
    (_, first_ends), (second_starts, _) = sorted((float(r[3]), float(r[4])) for r in rows)
    assert first_ends <= second_starts, f"the two live tests overlapped: {rows}"


_WIDE = """
import os

import pytest


@pytest.fixture(scope="module")
def device():
    open(os.environ["INNER_LOG"], "a").write("opened\\n")
    yield "opened"


@pytest.mark.live
def test_a_live_test_on_a_module_fixture(device):
    pass


def test_a_plain_test_beside_it():
    pass
"""


@pytest.mark.parametrize("args", [("-p", "no:xdist"), ("-n", "2", "--dist", "load")],
                         ids=["serial", "xdist"])
def test_a_live_test_on_a_module_scoped_fixture_is_an_error_by_name(tmp_path, args):
    """Row 589's caveat: the lock is per test, so a module- or
    session-scoped fixture would open its device outside it. The test is
    an error by name before the fixture is set up — under xdist too — and
    the rest of the run goes on."""
    temp = tmp_path / "temp"
    temp.mkdir()
    out = _inner_pytest(tmp_path, temp, _WIDE, args)
    text = out.stdout + out.stderr
    assert "1 passed, 1 error" in out.stdout, text
    assert "test_a_live_test_on_a_module_fixture" in text and "INTERNALERROR" not in text
    assert "outside the live lock" in text and "device (module-scoped)" in text, text
    assert not (tmp_path / "log").exists()          # the fixture never ran


def test_a_deselected_live_test_on_a_module_fixture_costs_nothing(tmp_path):
    """The fast tier deselects live tests: one with a wide fixture is not looked at."""
    temp = tmp_path / "temp"
    temp.mkdir()
    out = _inner_pytest(tmp_path, temp, _WIDE, ("-p", "no:xdist", "-m", "not live"))
    assert out.returncode == 0 and "1 passed, 1 deselected" in out.stdout, out.stdout + out.stderr


_NO_TURN = """
import pytest


@pytest.fixture(scope="module")
def device():
    yield "opened"


@pytest.mark.live
@pytest.mark.skipif(True, reason="not on this machine")
def test_a_live_test_its_marks_skip():
    pass


@pytest.mark.live
@pytest.mark.skipif(True, reason="not on this machine")
def test_a_skipped_live_test_on_a_module_fixture(device):
    pass


@pytest.mark.live
def test_a_live_test_on_a_module_fixture(device):
    pass
"""


def test_a_live_test_that_will_not_run_takes_no_turn(tmp_path):
    """While another run holds the lock (and the inner run would wait 30 s
    for it): a live test its skipif skips skips at once — a wide fixture
    beside the skip is a skip, not an error — and a wide-fixture test is
    its error at once; none of them waited for a turn."""
    temp = tmp_path / "temp"
    temp.mkdir()
    p, release = _holder(temp / live_lock.lock_path().name, run="xdist-other")
    try:
        t = time.monotonic()
        out = _inner_pytest(tmp_path, temp, _NO_TURN, env={"INNER_WAIT_S": "30"})
        took = time.monotonic() - t
    finally:
        release.set()
        p.join(10)
    text = out.stdout + out.stderr
    assert "2 skipped, 1 error" in out.stdout, text
    assert text.count("not on this machine") == 2 and "outside the live lock" in text, text
    assert took < 20, f"a test waited for a turn it would not use ({took:.1f} s)"


_ONE_LIVE = """
import pytest


@pytest.mark.live
def test_a_live_test():
    pass
"""


def test_the_wait_for_the_lock_is_not_timed(tmp_path):
    """The lock is taken outside pytest-timeout's window (conftest's
    `pytest_runtest_protocol`, the outer wrapper): a test that waits 2 s
    for its turn under `--timeout=1` still runs and passes. The holder
    lets go 2 s after the inner run says it has started waiting (a file
    it writes, with the holder it saw), not on a clock of the outer's."""
    temp = tmp_path / "temp"
    temp.mkdir()
    sig = tmp_path / "waiting"
    p, release = _holder(temp / live_lock.lock_path().name, run="xdist-other")
    got = []
    inner = threading.Thread(target=lambda: got.append(_inner_pytest(
        tmp_path, temp, _ONE_LIVE, ("-p", "no:xdist", "--timeout=1"),
        env={"INNER_WAIT_S": "30", "INNER_SIGNAL": str(sig)})))
    inner.start()
    try:
        deadline = time.monotonic() + 50
        while not sig.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert sig.exists(), "the inner run never started waiting"
        time.sleep(2.0)
    finally:
        release.set()
        inner.join(60)
        p.join(10)
    assert live_lock.run_of(sig.read_text())[0] == "xdist-other"     # it saw the holder
    assert float((tmp_path / "waiting.waited").read_text()) >= 1.9
    out = got[0]
    assert "1 passed" in out.stdout, out.stdout + out.stderr


def test_the_fixture_holds_it_for_a_live_test_and_lets_go_when_it_raises(tmp_path):
    temp = tmp_path / "temp"
    temp.mkdir()
    out = _inner_pytest(tmp_path, temp)
    assert "1 failed, 2 passed" in out.stdout, out.stdout + out.stderr
    assert "a live test failed" in out.stdout


def test_the_fixture_skips_a_live_test_another_run_holds_it_for(tmp_path):
    temp = tmp_path / "temp"
    temp.mkdir()
    p, release = _holder(temp / live_lock.lock_path().name, run="xdist-other")
    try:
        out = _inner_pytest(tmp_path, temp)
    finally:
        release.set()
        p.join(10)
    assert "1 skipped" in out.stdout, out.stdout + out.stderr
    assert live_lock.SKIP_REASON in out.stdout and "xdist-other" in out.stdout


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
