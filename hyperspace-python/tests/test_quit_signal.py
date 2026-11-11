"""Ctrl-C quits the app; it never dumps a traceback (2026-11-11).

What happened, and must not again: with no SIGINT handler installed,
Ctrl-C at the terminal raised `KeyboardInterrupt` wherever the signal
landed — three calls deep inside a panel draw — and `app.main` died with
a traceback through everyone's frames. None of the teardown after the
loop ran: the windows were left for the OS to reap, the audio stream and
every device were left open, the window placement was not saved, and the
shell was left printing `uv: Failed to get PID of child process`.

`app._install_quit_signals` is the fix: a handler asks the loop to quit
and the frame finishes, so the exit is the one a window close takes
(`close_all`, audit P1). The test below is the rule, and it is deliberately
end to end — the real `main` in a process of its own, a real SIGINT, and
then the three things a traceback would have cost: the exit code, a clean
stderr, and the `windows.json` only the teardown writes. A unit test of
the handler could not have caught the original bug; this one fails on the
build before the fix, every time.

The other half of the rule is what the app must *not* handle. SIGTERM is
the kernel's: a Python handler runs only where the interpreter reaches a
check point, so a main thread wedged in a driver call can take no signal
at all, and handling SIGTERM would have turned a launcher's one kill — the
thing that always worked on a hung show — into a wait with nothing behind
it. `test_one_sigterm_ends_an_app_wedged_in_a_native_call` is that rule,
and it is the reason the handler below is SIGINT alone.

It is in the fast tier, CI's merge gate, and not in `live`: the loop that
Ctrl-C has to leave is the app's, and nothing stubbed stands in for it.
On a Mac the app's windows take the focus for the few seconds it runs, so
there it waits for `--all`; CI is Linux under Xvfb and runs it on every
push.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hyperspace import app

ROOT = Path(__file__).resolve().parents[1]
# what `[project.scripts]` runs: `hyperspace = "hyperspace.app:main"`
LAUNCH = [sys.executable, "-c", "from hyperspace.app import main; main()"]
# no [[devices]] entry at all, and no dream: no hardware of the machine running
# the tests is opened (the same config tools/app_driver.py launches with)
CONFIG = """[[devices]]
role = "none"
kind = "midi"
enabled = false

[dream]
enabled = false
"""
UP_S = 90.0        # startup, as slow as a loaded runner's software GL makes it
QUIT_S = 20.0      # the signal to the exit: `close_all` shares a 2 s deadline
SETTLE_S = 0.5     # frames drawn before the signal, so it lands mid-frame


def _launch(home: Path) -> subprocess.Popen:
    """The real app, headless-ish, in a home of its own, running until something
    stops it (`HYPERSPACE_FRAMES` high enough to be no exit of its own)."""
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(CONFIG)
    env = dict(os.environ, HYPERSPACE_HOME=str(home), HYPERSPACE_FRAMES="100000000")
    return subprocess.Popen(LAUNCH, cwd=str(ROOT), env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _in_the_loop(p: subprocess.Popen, home: Path) -> None:
    """Wait until the app is drawing frames. `watchdog.start()` opens
    `stall.log` as the last thing before the loop, so the file appearing is
    startup done; `SETTLE_S` more and the signal lands inside a frame, where
    the traceback came from."""
    log = home / "stall.log"
    until = time.monotonic() + UP_S
    while time.monotonic() < until:
        if log.exists():
            time.sleep(SETTLE_S)
            return
        if p.poll() is not None:
            _, err = p.communicate()
            pytest.fail(f"the app exited during startup ({p.returncode}):\n{err[-3000:]}")
        time.sleep(0.05)
    p.kill()
    _, err = p.communicate()
    pytest.fail(f"the app never reached its frame loop:\n{err[-3000:]}")


@pytest.fixture
def quiet_on_a_mac(request):
    """The real app's windows take the focus on a Mac: there this waits for
    `--all`, as the other real-app tests do. CI is Linux and always runs it."""
    if sys.platform == "darwin" and not request.config.getoption("--all"):
        pytest.skip("the real app takes the focus on a Mac: `pytest --all`")


def test_ctrl_c_quits_the_real_app_without_a_traceback(quiet_on_a_mac, gl_window_ok, tmp_path):
    """A Ctrl-C into the running app leaves it the way quitting does:
    nothing on stderr, 0, and the teardown's own files written."""
    home = tmp_path / "home"
    p = _launch(home)
    _in_the_loop(p, home)

    sent = time.monotonic()
    p.send_signal(signal.SIGINT)
    try:
        _, err = p.communicate(timeout=QUIT_S)
    except subprocess.TimeoutExpired:
        p.kill()
        _, err = p.communicate()
        pytest.fail(f"Ctrl-C left the app running:\n{err[-3000:]}")

    tail = err[-3000:]
    assert "Traceback" not in err, f"Ctrl-C dumped a traceback:\n{tail}"
    assert "KeyboardInterrupt" not in err, f"Ctrl-C unwound the stack:\n{tail}"
    assert p.returncode == 0, f"Ctrl-C exited {p.returncode}:\n{tail}"
    # the teardown ran: `_quiet(save_windows)` is its first line, and nothing
    # else in a launch writes this file (placement.py)
    assert (home / "windows.json").exists(), f"Ctrl-C skipped the teardown:\n{tail}"
    assert time.monotonic() - sent < QUIT_S


def test_sigterm_is_left_to_the_kernel_and_ends_the_real_app(quiet_on_a_mac, gl_window_ok,
                                                             tmp_path):
    """Nothing of ours handles SIGTERM, so a launcher's kill is the kernel's
    business and always lands. It costs the teardown — no `windows.json` —
    and that is the trade: see the wedged case below for what handling it
    would have cost instead."""
    home = tmp_path / "home"
    p = _launch(home)
    _in_the_loop(p, home)

    p.send_signal(signal.SIGTERM)
    try:
        _, err = p.communicate(timeout=QUIT_S)
    except subprocess.TimeoutExpired:
        p.kill()
        pytest.fail("SIGTERM left the app running")
    assert p.returncode == -signal.SIGTERM, f"{p.returncode}: {err[-2000:]}"


# A frame that never comes back to the loop's condition *and* never returns to
# the interpreter: two locks of a non-recursive mutex on one thread, which is a
# driver's deadlock without a driver. `pthread_mutex_lock` returns for no signal,
# so no Python handler of ours — and none of CPython's — runs again in this
# process. It is the case nothing in-process can answer, which is why it decides
# what the app may handle rather than how it handles it.
WEDGED = """
import ctypes

from hyperspace import app

app._install_quit_signals()
lib = ctypes.CDLL(None)
m = ctypes.create_string_buffer(128)      # pthread_mutex_t: 40 bytes on glibc, 64 on macOS
lib.pthread_mutex_init(m, None)
lib.pthread_mutex_lock(m)
print("wedging", flush=True)
lib.pthread_mutex_lock(m)
print("impossible", flush=True)
"""


def test_one_sigterm_ends_an_app_wedged_in_a_native_call():
    """The rule that keeps `_install_quit_signals` to SIGINT.

    A show whose driver has deadlocked is exactly when a kill has to work,
    and it is exactly when no Python can run to notice one. The kernel's
    default disposition is the only thing that ends this process, so nothing
    may take SIGTERM away from it — not a handler, however graceful, and not
    a handler that arms a deadline, because the arming cannot happen either.

    Measured 2026-11-11: with SIGTERM handled, this process sat through the
    signal and outlived a one-second hard deadline that was never armed.
    """
    p = subprocess.Popen([sys.executable, "-c", WEDGED], cwd=str(ROOT), text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.stdout is not None
    assert p.stdout.readline().strip() == "wedging", "the app never reached the deadlock"

    p.send_signal(signal.SIGTERM)
    try:
        out, err = p.communicate(timeout=QUIT_S)
    except subprocess.TimeoutExpired:
        p.kill()
        pytest.fail("one SIGTERM left a wedged app running: something is handling it")
    assert "impossible" not in out, "the mutex was not a deadlock; the test proves nothing"
    assert p.returncode == -signal.SIGTERM, f"{p.returncode}: {err[-2000:]}"


def test_the_handlers_are_installed_before_the_windows_and_again_before_the_loop():
    """Where the two calls are is the whole of what they cover: the first
    before `glfw.init`, so a Ctrl-C through the seconds of startup is a quit
    too; the second after everything is open, in case a driver installed a
    SIGINT handler of its own over ours. Moved below either line, Ctrl-C is
    a traceback again for as long as it takes to get there."""
    src = (ROOT / "hyperspace" / "app.py").read_text()
    assert src.index("quitting = _install_quit_signals()") < src.index("if not glfw.init():")
    assert src.index("_install_quit_signals(quitting)\n") < src.index("while not (quitting.asked")
    # and what main does on the way out, after the last window is gone
    assert src.index("_restore_quit_signals(quitting)\n") > src.index("glfw.terminate()")


def test_the_loop_leaves_by_the_same_door_a_window_close_does():
    """No `sys.exit`, no `os._exit`, no `raise` on the way out: the quit
    joins the loop's own condition, so the teardown below it runs."""
    src = (ROOT / "hyperspace" / "app.py").read_text()
    loop = src[src.index("    try:\n        while not (quitting.asked"):src.index("    _quiet(save_windows)")]
    assert "sys.exit" not in loop and "os._exit" not in loop


# ---- the handler itself


@pytest.fixture
def handler():
    """`_install_quit_signals` on a clock of the test's own, with this
    process's own handlers — and its alarm — put back after it. The teardown
    matters: a signal here arms a real SIGALRM, and the default action for
    one is to kill this worker."""
    before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM)}
    clock, forced = [0.0], []
    quitting = app._install_quit_signals(clock=lambda: clock[0], hard=lambda: forced.append(1))
    try:
        yield signal.getsignal(signal.SIGINT), quitting, clock, forced
    finally:
        signal.alarm(0)
        for s, was in before.items():
            signal.signal(s, was)


def test_the_first_signal_asks_the_loop_to_quit_and_arms_the_backstop(handler):
    """It asks — and leaves nothing resting on the asking being heard."""
    fire, quitting, clock, forced = handler
    assert not quitting.asked and not quitting.armed
    clock[0] = 7.0
    fire(signal.SIGINT, None)
    assert quitting.asked and quitting.at == 7.0 and not forced
    assert quitting.armed
    assert signal.getsignal(signal.SIGALRM) is signal.SIG_DFL, "the kernel does this one"
    assert 0 < signal.alarm(0) <= app.QUIT_HARD_S       # (and disarms it again)


def test_the_restore_disarms_the_backstop_and_gives_the_signals_back(handler):
    """What `main` does on its way out: a tool that calls it goes on owning
    its own Ctrl-C, and the alarm set for a quit that finished is gone."""
    fire, quitting, _, _ = handler
    before = signal.getsignal(signal.SIGALRM)
    fire(signal.SIGINT, None)
    app._restore_quit_signals(quitting)
    assert not quitting.armed and signal.alarm(0) == 0
    assert signal.getsignal(signal.SIGINT) is not fire
    assert signal.getsignal(signal.SIGALRM) is before, "SIGALRM was left at SIG_DFL"


def test_a_handler_someone_else_meant_to_install_is_left_alone(handler):
    """Only ours is taken back: a restore never undoes a handler that
    something installed after us on purpose."""
    fire, quitting, _, _ = handler

    def mine(signum, frame):
        pass

    assert signal.signal(signal.SIGINT, mine) is fire       # installed over ours
    app._restore_quit_signals(quitting)
    assert signal.getsignal(signal.SIGINT) is mine, "a restore took back what wasn't ours"


def test_a_second_ctrl_c_inside_the_grace_window_is_a_double_tap(handler):
    """Mashing Ctrl-C must not take the teardown away from a quit that is
    already under way."""
    fire, quitting, clock, forced = handler
    fire(signal.SIGINT, None)
    clock[0] = app.QUIT_GRACE_S - 0.01
    fire(signal.SIGINT, None)
    assert quitting.at == 0.0 and not forced


def test_a_ctrl_c_after_the_grace_window_leaves_at_once(handler):
    """The escape hatch for a teardown that wedges — the only exit that
    skips it."""
    fire, _, clock, forced = handler
    fire(signal.SIGINT, None)
    clock[0] = app.QUIT_GRACE_S
    fire(signal.SIGINT, None)
    assert forced == [1]


def test_sigterm_is_nobody_of_ours(handler):
    """The unit-level half of the wedged test: installing leaves SIGTERM
    exactly as it was, so the kernel's default disposition still holds it."""
    fire, quitting, _, _ = handler
    assert signal.getsignal(signal.SIGTERM) is not fire
    assert signal.SIGTERM not in quitting.before
    again = app._install_quit_signals(quitting)
    assert again is quitting and signal.getsignal(signal.SIGINT) is not fire
    assert signal.getsignal(signal.SIGTERM) is not quitting.handler
