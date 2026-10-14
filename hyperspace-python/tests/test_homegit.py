"""Plan 19 WP6: the home in git — a commit on each save, opt-in.

Every test builds its `Committer` on a home under its own tmp_path (the
autouse fixture already points ``HYPERSPACE_HOME`` there); the ones that
need a real ``git`` skip when there is none on the PATH. The test file
runs git itself (``_git``) only to read what the committer made."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest
from conftest import OWNER_PRESETS, boot_home, tree

from hyperspace import config, homegit, library

GIT = shutil.which("git")
needs_git = pytest.mark.skipif(GIT is None, reason="no git on the PATH")
LOCATORS = homegit.LOCATORS


def _git(home: Path, *args: str, check: bool = True) -> str:
    env = {k: v for k, v in os.environ.items() if k not in LOCATORS}
    r = subprocess.run(["git", *args], cwd=home, env=env, capture_output=True, text=True,
                       check=False, timeout=30)
    if check:
        assert r.returncode == 0, r.stderr
    return r.stdout


def _subjects(home: Path) -> list[str]:
    """The log's subjects, newest first."""
    return _git(home, "log", "--format=%s").splitlines()


def _tracked(home: Path) -> set[str]:
    return set(_git(home, "ls-files").splitlines())


def _boot(home: Path, committer=None):
    r = boot_home(home)
    r.lib.committer = committer
    return r


def _settle(r, c) -> None:
    """Let the worker finish, then the frame thread's poll drain its notes."""
    assert c.wait(15.0)
    r.lib.poll()


def _homegit_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "homegit" and t.is_alive()]


def _script(path: Path, body: str) -> str:
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return str(path)


# ---------------------------------------------------------------- off by default

def test_off_by_default_and_nothing_is_written(tmp_path, monkeypatch):
    """No key, or ``git = false``: the library has no committer (app.py's
    gate builds none: `test_app_boundary.py::test_the_homegit_gate`), no
    thread starts, no subprocess runs on a save, and the home gains no
    `.git` or `.gitignore`."""
    home = tmp_path / "home"
    home.mkdir()
    cfg = config.load(home / "config.toml")              # no file: the defaults
    assert "git" not in cfg["library"]
    (home / "config.toml").write_text("[library]\ngit = false\n")
    assert "git" not in config.load(home / "config.toml")["library"]
    before = len(_homegit_threads())
    r = _boot(home)
    assert r.lib.committer is None
    ran: list = []
    with monkeypatch.context() as m:
        m.setattr(subprocess, "Popen", lambda *a, **k: ran.append(a) or _boom())
        r.presets.save_as("OFF ONE")
        r.lib.project.put_slot(10, "OFF ONE")
        r.lib.delete(library.PRESETS, "OFF ONE")
        r.lib.poll()
    assert ran == []
    assert not (home / ".git").exists() and not (home / ".gitignore").exists()
    assert len(_homegit_threads()) == before


def _boom():
    raise AssertionError("a subprocess ran with git off")


# ---------------------------------------------------------------- the first save

@needs_git
def test_git_init_waits_for_the_first_save(tmp_path):
    """Building the committer and attaching it runs nothing: no thread, no
    `.git`, no `.gitignore`, whatever the frames poll — until a save."""
    home = tmp_path / "home"
    before = len(_homegit_threads())
    c = homegit.Committer(home)
    r = _boot(home, c)
    for _ in range(5):
        r.lib.poll()
    assert not (home / ".git").exists() and not (home / ".gitignore").exists()
    assert len(_homegit_threads()) == before and c.commits == 0
    r.presets.save_as("FIRST ONE")
    _settle(r, c)
    assert (home / ".git").is_dir() and c.commits == 1


@needs_git
def test_the_first_save_inits_ignores_and_commits(owner_home):
    home = owner_home
    (home / "hidden.json").write_text('{"schema": "hyperspace.hidden/1", "presets": []}\n')
    (home / "config.toml").write_text("[library]\ngit = true\n")
    (home / "bindings.json.bak-v3").write_text("{}\n")
    (home / ".DS_Store").write_bytes(b"\0")
    c = homegit.Committer(home)
    r = _boot(home, c)
    r.presets.save_as("NIGHT FOUR")
    _settle(r, c)
    assert (home / ".gitignore").read_text() == homegit.IGNORE
    log = _git(home, "log", "--format=%s%n%b%n--")
    assert _subjects(home) == [homegit.FIRST]
    assert "save preset NIGHT FOUR" in log                 # the save that asked is in it
    t = _tracked(home)
    for name in OWNER_PRESETS + ("NIGHT FOUR",):
        assert f"presets/{library.slug(name)}.json" in t, name
    assert {"projects/mine.hyp.json", "projects/party.hyp.json", "bindings.json",
            "hidden.json", "config.toml", ".gitignore"} <= t
    for path in t:
        assert not path.startswith(("weights/", "trash/")), path
        assert path not in ("stall.log", "last_show", "windows.json", ".DS_Store"), path
        assert ".bak-" not in path, path
    assert _git(home, "status", "--porcelain") == ""
    assert _git(home, "remote") == ""                      # nothing added: local only
    assert r.lib.warning == ""


@needs_git
def test_each_save_is_one_commit_with_its_message(tmp_path):
    """A preset saved, a module preset saved, × on a preset, a bank change,
    "starts on" and a show saved: one commit each, in the library's words.
    (Rename, hide and restore are WP4's; their one-line hooks are listed
    in the PR.)"""
    home = tmp_path / "home"
    c = homegit.Committer(home)
    r = _boot(home, c)
    lib, pr = r.lib, r.lib.project

    def step(fn) -> str:
        fn()
        _settle(r, c)
        return _subjects(home)[0]

    assert step(lambda: r.presets.save_as("TRIP 2")) == homegit.FIRST
    r.reg["view.speed"].set(r.reg["view.speed"].value * 0.5)
    assert step(lambda: r.presets.save_as("TRIP 2")) == "save preset TRIP 2"
    assert step(lambda: lib.save_as("fx", "acid")) == "save fx acid"
    assert step(lambda: r.presets.save_as("TRIP 3")) == "save preset TRIP 3"
    assert step(lambda: lib.delete(library.PRESETS, "TRIP 3")) == "trash preset TRIP 3"
    assert step(lambda: pr.put_slot(11, "TRIP 2")) == f"show {pr.name}: bank"

    def starts_on():
        pr.startup = "TRIP 2"
        pr.write()
    assert step(starts_on) == f"show {pr.name}: starts on TRIP 2"
    r.reg["master.gain"].set(r.reg["master.gain"].value * 0.5)
    assert step(lambda: pr.save()) == f"save show {pr.name}"
    n = len(_subjects(home))
    assert n == 8 and c.commits == 8
    assert _git(home, "status", "--porcelain") == ""
    assert not any(p.startswith("trash/") for p in _tracked(home))   # fork 11: ignored


@needs_git
def test_several_waiting_requests_are_one_commit_and_nothing_staged_none(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "a.json").write_text("{}\n")
    c = homegit.Committer(home)
    c.request("first")
    assert c.wait(15.0) and c.commits == 1
    (home / "b.json").write_text("{}\n")
    (home / "c.json").write_text("{}\n")
    with c._cond:                         # the worker cannot take the list until all three wait
        c.request("save preset B")
        c.request("save preset C")
        c.request("save show mine")
    assert c.wait(15.0) and c.commits == 2
    assert _git(home, "log", "-1", "--format=%s|%b").strip() == \
        "save preset B|save preset C\nsave show mine"
    c.request("nothing changed")
    assert c.wait(15.0) and c.commits == 2                 # nothing staged: no commit
    assert len(_subjects(home)) == 2 and c.notes() == []


@needs_git
def test_a_save_landing_while_the_worker_is_busy_keeps_its_own_words(tmp_path):
    """Found at the real launch: a first commit (init and all) can take a
    second while the frames run on, and a save made meanwhile is staged by
    that commit's ``add -A``. Its words are taken after the add, so they
    are in that commit's body — not left for a commit that finds nothing
    staged and is never made."""
    home = tmp_path / "home"
    home.mkdir()
    (home / "a.json").write_text("{}\n")
    c = homegit.Committer(home)
    real = c._git

    def slow_frames(*args, **kw):
        if args[0] == "add" and not (home / "late.json").exists():
            (home / "late.json").write_text("{}\n")       # a save on the frame thread…
            c.request("save preset LATE")                  # …and its request, mid-commit
        return real(*args, **kw)
    c._git = slow_frames
    c.request("save preset A")
    assert c.wait(15.0) and c.commits == 1
    assert _git(home, "log", "-1", "--format=%b").strip() == "save preset A\nsave preset LATE"
    assert "late.json" in _tracked(home)


# ---------------------------------------------------------------- the three cases

@needs_git
def test_a_home_inside_another_repository_is_never_committed(tmp_path):
    outer = tmp_path / "dotfiles"
    outer.mkdir()
    _git(outer, "init", "-q")
    home = outer / "Hyperspace"
    c = homegit.Committer(home)
    r = _boot(home, c)
    r.presets.save_as("INSIDE")
    _settle(r, c)
    assert c.refused
    assert "is inside another repository" in r.lib.warning
    assert not (home / ".git").exists() and not (home / ".gitignore").exists()
    said = r.lib.said.get("warning", 0)
    r.presets.save_as("INSIDE 2")                          # the key does nothing for the run
    _settle(r, c)
    assert r.lib.said.get("warning", 0) == said and c.notes() == []
    assert _git(outer, "rev-parse", "--verify", "-q", "HEAD", check=False) == ""   # no commit


@needs_git
def test_an_existing_repository_and_gitignore_are_kept(tmp_path):
    home = tmp_path / "home"
    r = _boot(home)
    _git(home, "init", "-q", "-b", "owners")
    (home / ".gitignore").write_text("# mine\ntrash/\n")
    _git(home, "add", "-A")
    _git(home, "-c", "user.name=Owner", "-c", "user.email=o@example.invalid",
         "commit", "-q", "-m", "the owner's own first commit")
    c = homegit.Committer(home)
    r.lib.committer = c
    r.presets.save_as("KEPT")
    _settle(r, c)
    assert (home / ".gitignore").read_text() == "# mine\ntrash/\n"
    assert _git(home, "rev-parse", "--abbrev-ref", "HEAD").strip() == "owners"
    assert _subjects(home) == ["save preset KEPT", "the owner's own first commit"]


@needs_git
def test_a_repository_with_no_gitignore_gets_ours(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    _git(home, "init", "-q")
    (home / "x.json").write_text("{}\n")
    c = homegit.Committer(home)
    c.request("save preset X")
    assert c.wait(15.0)
    assert (home / ".gitignore").read_text() == homegit.IGNORE
    assert _subjects(home) == [homegit.FIRST]               # no commit yet: the first is ours


# ---------------------------------------------------------------- never blocks, never fails

@needs_git
def test_git_never_blocks_or_fails_a_save(tmp_path):
    """A missing binary, a locked index and a git that sleeps past its
    timeout: the save returns at once with its file written, one note each
    (not repeated), and the next good commit holds everything."""
    home = tmp_path / "home"
    r = _boot(home)
    lib = r.lib

    def save(name: str) -> float:
        t = time.perf_counter()
        r.presets.save_as(name)
        took = time.perf_counter() - t
        assert (home / library.PRESETS / f"{library.slug(name)}.json").is_file()
        return took

    # a missing binary
    c = lib.committer = homegit.Committer(home, git=str(tmp_path / "no-git"))
    assert save("MISSING 1") < 0.5
    _settle(r, c)
    assert lib.warning == f"git: not committed (no git at {tmp_path / 'no-git'}); " \
                          "saves are not affected"
    said = lib.said["warning"]
    save("MISSING 2")
    _settle(r, c)
    assert lib.said["warning"] == said                     # said once
    # a git that sleeps five seconds, against a one-second timeout
    c = lib.committer = homegit.Committer(home, git=_script(tmp_path / "slow-git", "sleep 5"),
                                          timeout=1.0)
    assert save("SLOW") < 0.5
    _settle(r, c)
    assert "took longer than 1 s" in lib.warning
    # a locked index: the real git, after a first good commit
    c = lib.committer = homegit.Committer(home)
    save("GOOD")
    _settle(r, c)
    assert c.commits == 1
    lock = home / ".git" / "index.lock"
    lock.write_text("")
    assert save("LOCKED 1") < 0.5
    _settle(r, c)
    assert lib.warning.startswith("git: not committed (git add exited 128")
    said = lib.said["warning"]
    save("LOCKED 2")
    _settle(r, c)
    assert lib.said["warning"] == said and c.commits == 1
    lock.unlink()
    save("AFTER")
    _settle(r, c)
    assert c.commits == 2 and lib.said["warning"] == said
    t = _tracked(home)
    for name in ("MISSING 1", "MISSING 2", "SLOW", "LOCKED 1", "LOCKED 2", "AFTER"):
        assert f"presets/{library.slug(name)}.json" in t, name   # the catch-up
    assert _git(home, "status", "--porcelain") == ""
    # after a commit has gone through, a new failure is said again
    lock.write_text("")
    save("LOCKED 3")
    _settle(r, c)
    assert lib.said["warning"] == said + 1
    lock.unlink()


@needs_git
def test_an_exception_in_the_worker_or_the_request_never_reaches_the_save(tmp_path):
    home = tmp_path / "home"
    c = homegit.Committer(home)
    r = _boot(home, c)

    def broken():
        raise ValueError("a bug in the worker")
    c._commit = broken
    r.presets.save_as("BUGGED")
    _settle(r, c)
    assert r.lib.warning == ("git: not committed (ValueError: a bug in the worker); "
                             "saves are not affected")

    class Raising:
        def request(self, message):
            raise RuntimeError("request broke")

        def notes(self):
            raise RuntimeError("notes broke")
    r.lib.committer = Raising()
    path = r.presets.save_as("STILL SAVED")
    assert path.is_file()
    r.lib.poll()                                          # the watcher goes on


def test_the_file_is_on_disk_before_the_commit_is_asked_for(tmp_path):
    seen: list = []
    home = tmp_path / "home"
    r = _boot(home)

    class Looking:
        def request(self, message):
            seen.append((message, sorted(p.name for p in (home / "presets").glob("*.json"))))

        def notes(self):
            return []
    r.lib.committer = Looking()
    r.presets.save_as("ON DISK")
    assert seen == [("save preset ON DISK", ["on-disk.json"])]


def test_request_returns_at_once_and_the_worker_never_touches_the_library(tmp_path):
    """The note sits in the committer until the frame thread's poll takes it."""
    home = tmp_path / "home"
    c = homegit.Committer(home, git=str(tmp_path / "no-git"))
    r = _boot(home, c)
    t = time.perf_counter()
    c.request("save preset X")
    assert time.perf_counter() - t < 0.05
    assert c.wait(15.0)
    assert r.lib.warning == ""                             # not until the frame thread polls
    r.lib.poll()
    assert r.lib.warning.startswith("git: not committed (no git at")
    assert c.notes() == []                                 # drained, once


@needs_git
def test_commands_run_with_no_prompt_no_hooks_no_signing_and_a_timeout(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / "x.json").write_text("{}\n")
    calls: list = []
    waits: list = []

    class Recording(subprocess.Popen):
        def __init__(self, cmd, **kw):
            calls.append((cmd, kw))
            super().__init__(cmd, **kw)

        def communicate(self, input=None, timeout=None):
            waits.append(timeout)
            return super().communicate(input, timeout)
    c = homegit.Committer(home, timeout=7.0)
    with monkeypatch.context() as m:
        m.setattr(homegit.subprocess, "Popen", Recording)
        m.setenv("GIT_DIR", str(tmp_path / "elsewhere"))   # never aims it elsewhere
        c.request("save preset X")
        assert c.wait(15.0)
    assert c.commits == 1 and calls and waits == [7.0] * len(calls)
    for cmd, kw in calls:
        assert cmd[1:5] == ["-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
        assert kw["env"]["GIT_TERMINAL_PROMPT"] == "0" and kw["stdin"] == subprocess.DEVNULL
        assert "GIT_DIR" not in kw["env"] and kw["cwd"] == home
    verbs = {next(a for a in cmd[5:] if not a.startswith("-") and "=" not in a)
             for cmd, _ in calls}
    assert verbs <= {"rev-parse", "init", "config", "add", "diff", "commit"}
    # a hook of the machine's would refuse the commit; it never runs
    hook = home / ".git" / "hooks" / "pre-commit"
    _script(hook, f"touch {tmp_path / 'hook-ran'}; exit 1")
    (home / "y.json").write_text("{}\n")
    c.request("save preset Y")
    assert c.wait(15.0) and c.commits == 2
    assert not (tmp_path / "hook-ran").exists()


def test_a_git_past_its_timeout_is_asked_to_stop_and_clean_up_first(tmp_path):
    """Review of PR #119: a SIGKILLed `git add` leaves `.git/index.lock`,
    and every later commit fails until it is deleted by hand. Past its
    timeout a command gets SIGTERM — on which git removes its own lock
    files — and SIGKILL only if it is still there `KILL_AFTER` later. The
    stand-in holds a lock file and removes it on SIGTERM, as git does."""
    home = tmp_path / "home"
    home.mkdir()
    lock = tmp_path / "index.lock"
    slow = _script(tmp_path / "git-with-a-lock",
                   f"trap 'rm -f {lock}; exit 143' TERM\ntouch {lock}\n"
                   "sleep 30 >/dev/null 2>&1 </dev/null & wait")
    c = homegit.Committer(home, git=slow, timeout=0.5)
    t = time.perf_counter()
    c.request("save preset X")
    assert c.wait(15.0)
    assert time.perf_counter() - t < 0.5 + homegit.KILL_AFTER + 1.0
    assert not lock.exists()                               # cleaned up, not killed mid-write
    assert c.notes() == [("git: not committed (git rev-parse took longer than 0.5 s); "
                          "saves are not affected")]


@needs_git
def test_a_machine_with_no_identity_commits_as_hyperspace(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / "x.json").write_text("{}\n")
    with monkeypatch.context() as m:
        m.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
        m.setenv("GIT_CONFIG_NOSYSTEM", "1")
        for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                  "GIT_COMMITTER_EMAIL", "EMAIL"):
            m.delenv(k, raising=False)
        c = homegit.Committer(home)
        c.request("save preset X")
        assert c.wait(15.0) and c.commits == 1, c.notes()
        assert _git(home, "log", "-1", "--format=%an <%ae>").strip() == \
            "Hyperspace <hyperspace@localhost>"
        # a machine with one: used as it is
        _git(home, "config", "user.name", "Owner")
        _git(home, "config", "user.email", "owner@example.invalid")
        c2 = homegit.Committer(home)
        (home / "y.json").write_text("{}\n")
        c2.request("save preset Y")
        assert c2.wait(15.0) and c2.commits == 1
        assert _git(home, "log", "-1", "--format=%an <%ae>").strip() == \
            "Owner <owner@example.invalid>"


def test_no_network_commands():
    src = Path(homegit.__file__).read_text().lower()
    for word in ("push", "fetch", "pull", "clone", "remote"):
        assert word not in src, word


def test_it_refuses_the_real_home_under_pytest():
    assert os.environ.get("PYTEST_CURRENT_TEST")
    for home in (Path.home() / "Hyperspace", Path("~/Hyperspace"),
                 Path.home() / "Hyperspace" / ".." / "Hyperspace"):
        with pytest.raises(RuntimeError, match="never under pytest"):
            homegit.Committer(home)


# ---------------------------------------------------------------- quit

@needs_git
def test_close_waits_two_seconds_and_the_next_run_commits_what_was_left(tmp_path):
    home = tmp_path / "home"
    r = _boot(home)
    stuck = homegit.Committer(home, git=_script(tmp_path / "stuck-git", "sleep 3; exit 1"))
    r.lib.committer = stuck
    r.presets.save_as("LEFT OVER")
    t = time.perf_counter()
    stuck.close(2.0)
    took = time.perf_counter() - t
    assert 1.5 < took < 2.6
    # the next run: its first save takes up the file the last one never committed
    nxt = homegit.Committer(home)
    r.lib.committer = nxt
    r.presets.save_as("NEXT RUN")
    _settle(r, nxt)
    t = _tracked(home)
    assert {"presets/left-over.json", "presets/next-run.json"} <= t
    # a committer with nothing waiting closes at once
    t0 = time.perf_counter()
    nxt.close()
    assert time.perf_counter() - t0 < 0.5


# ---------------------------------------------------------------- the owner's files

@needs_git
def test_it_rewrites_no_file_of_the_owners(owner_home):
    """On a copy of a home like the owner's, with the key on: a save
    commits, and every other file — each preset, show, bindings.json, the
    trash, the weights — is byte for byte (and mtime) what it was. Git
    writes `.git/` and `.gitignore` only."""
    home = owner_home
    r = _boot(home)                     # the launch (its one rewrite of bindings.json) first
    before = tree(home)
    c = homegit.Committer(home)
    r.lib.committer = c
    r.presets.save_as("NIGHT FOUR")
    _settle(r, c)
    assert c.commits == 1 and r.lib.warning == ""
    after = tree(home, but=(".git/", ".gitignore", "presets/night-four.json"))
    assert after == before
    assert _git(home, "status", "--porcelain") == ""
