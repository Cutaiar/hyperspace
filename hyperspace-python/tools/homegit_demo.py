#!/usr/bin/env python3
"""The home in git, shown headless (plan 19 WP6).

    uv run python tools/homegit_demo.py
        → docs/plans/assets/19-presets-and-the-desk/homegit-demo.txt

Runs on a fresh temp home built like the owner's
(`tests/conftest.py::build_owner_home`); ``HYPERSPACE_HOME`` points at a
temp folder before anything reads it, so this cannot touch ~/Hyperspace.
The steps go through the library as the app does (`boot_home`, the
committer `app._open_homegit` builds from the config), and the log is read
with git afterwards:

  the key off (nothing happens); the key on and the first save (init,
  `.gitignore`, the "as it was" commit); two more saves, a × and a bank
  change (the log after each); a save with git missing from the PATH and
  one with the index locked (the one note, the save standing, the next
  save catching up); a home inside another repository (refused, said
  once); and the timing of a request and of the commit it asks for.
"""

from __future__ import annotations

import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="hyperspace-homegit-demo-"))
HOME = ROOT / "home"
os.environ["HYPERSPACE_HOME"] = str(HOME)
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from conftest import boot_home, build_owner_home

from hyperspace import app, config, homegit, library

OUT = REPO / "docs" / "plans" / "assets" / "19-presets-and-the-desk" / "homegit-demo.txt"
lines: list[str] = []


def say(text: str = "") -> None:
    lines.append(text.replace(os.path.realpath(ROOT), "<tmp>").replace(str(ROOT), "<tmp>"))
    print(lines[-1])


def git(home: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in homegit.LOCATORS}
    return subprocess.run(["git", *args], cwd=home, env=env, capture_output=True, text=True,
                          check=False, timeout=30).stdout


def log(home: Path, indent: str = "      ") -> None:
    for ln in git(home, "log", "--format=%h %s").splitlines():
        say(f"{indent}{ln}")


def settle(r, c) -> None:
    c.wait(15.0)
    r.lib.poll()


def main() -> int:
    say("plan 19 WP6 — the home in git: a commit on each save, opt-in")
    say(f"git: {git(ROOT, '--version').strip()}")
    build_owner_home(HOME)
    say("home: a copy shaped like the owner's (conftest.build_owner_home) at <tmp>/home")
    say()

    # ---- the key off
    say("1. [library] git absent (the default)")
    cfg = config.load(HOME / "config.toml")
    r = boot_home(HOME)
    r.lib.committer = app._open_homegit(cfg, HOME)
    say(f"   cfg['library'] = {cfg['library']}   committer = {r.lib.committer}")
    r.presets.save_as("NIGHT FOUR")
    r.lib.poll()
    say(f"   saved NIGHT FOUR → .git: {(HOME / '.git').exists()}  "
        f".gitignore: {(HOME / '.gitignore').exists()}  homegit threads: "
        f"{sum(t.name == 'homegit' for t in threading.enumerate())}")
    say()

    # ---- the key on
    say("2. [library] git = true, and the first save")
    (HOME / "config.toml").write_text("[library]\ngit = true\n")
    cfg = config.load(HOME / "config.toml")
    c = app._open_homegit(cfg, HOME)
    r.lib.committer = c
    say(f"   cfg['library'] = {cfg['library']}   committer built; .git yet: "
        f"{(HOME / '.git').exists()} (nothing runs until a save)")
    r.reg["view.speed"].set(r.reg["view.speed"].value * 0.5)
    r.presets.save_as("NIGHT FIVE")
    settle(r, c)
    say("   saved NIGHT FIVE → git log --oneline:")
    log(HOME)
    say("   body of the first commit: "
        + repr(git(HOME, "log", "-1", "--format=%b").strip()))
    say("   .gitignore (written, there was none):")
    for ln in (HOME / ".gitignore").read_text().splitlines():
        say(f"      | {ln}")
    tracked = git(HOME, "ls-files").splitlines()
    say(f"   tracked ({len(tracked)}): " + ", ".join(tracked))
    ignored = git(HOME, "status", "--ignored", "--porcelain").splitlines()
    say("   ignored: " + ", ".join(sorted(ln[3:] for ln in ignored if ln.startswith("!!"))))
    say(f"   git status --porcelain: {git(HOME, 'status', '--porcelain')!r}")
    say()

    # ---- more saves
    say("3. two more saves, a ×, a bank change — the log after each")
    steps = [
        ("save NIGHT FIVE again, changed", lambda: (
            r.reg["view.bright"].set(r.reg["view.bright"].value * 0.9),
            r.presets.save_as("NIGHT FIVE"))),
        ("save fx acid (a module preset)", lambda: r.lib.save_as("fx", "acid")),
        ("× on NIGHT FOUR", lambda: r.lib.delete(library.PRESETS, "NIGHT FOUR")),
        ("put NIGHT FIVE on slot 12", lambda: r.lib.project.put_slot(11, "NIGHT FIVE")),
    ]
    for what, fn in steps:
        fn()
        settle(r, c)
        say(f"   {what}:")
        log(HOME)
    say(f"   git status --porcelain: {git(HOME, 'status', '--porcelain')!r}  "
        f"(trash/ holds {len(list((HOME / 'trash').rglob('*.json')))} files, none tracked)")
    say()

    # ---- git missing
    say("4. git missing from the PATH")
    path = os.environ["PATH"]
    os.environ["PATH"] = str(ROOT / "no-bin")
    try:
        c2 = homegit.Committer(HOME)                   # a fresh run, as after a relaunch
        r.lib.committer = c2
        r.reg["view.speed"].set(r.reg["view.speed"].value * 0.9)
        t = time.perf_counter()
        r.presets.save_as("NO GIT 1")
        took = (time.perf_counter() - t) * 1000
        settle(r, c2)
        on_disk = (HOME / "presets" / "no-git-1.json").is_file()
        say(f"   save NO GIT 1: returned in {took:.1f} ms, file on disk: {on_disk}")
        say(f"   warning line: {r.lib.warning!r}")
        said = r.lib.said["warning"]
        r.presets.save_as("NO GIT 2")
        settle(r, c2)
        say(f"   save NO GIT 2: said again? {r.lib.said['warning'] != said}")
    finally:
        os.environ["PATH"] = path
    r.presets.save_as("GIT BACK")
    settle(r, c2)
    say("   git back on the PATH, save GIT BACK — the catch-up:")
    log(HOME)
    say("   files in that commit: " + ", ".join(
        git(HOME, "show", "--name-only", "--format=", "HEAD").split()))
    say()

    # ---- a locked index
    say("5. the index locked (another git holding .git/index.lock)")
    lock = HOME / ".git" / "index.lock"
    lock.write_text("")
    t = time.perf_counter()
    r.presets.save_as("LOCKED")
    took = (time.perf_counter() - t) * 1000
    settle(r, c2)
    say(f"   save LOCKED: returned in {took:.1f} ms, file on disk: "
        f"{(HOME / 'presets' / 'locked.json').is_file()}")
    say(f"   warning line: {r.lib.warning!r}")
    said = r.lib.said["warning"]
    r.presets.save_as("LOCKED 2")
    settle(r, c2)
    say(f"   save LOCKED 2: said again? {r.lib.said['warning'] != said}")
    lock.unlink()
    r.presets.save_as("UNLOCKED")
    settle(r, c2)
    say("   lock gone, save UNLOCKED — the catch-up:")
    log(HOME)
    say("   files in that commit: " + ", ".join(
        git(HOME, "show", "--name-only", "--format=", "HEAD").split()))
    say(f"   git status --porcelain: {git(HOME, 'status', '--porcelain')!r}")
    say()

    # ---- inside another repository
    say("6. a home inside another repository (a dotfiles repository above it)")
    outer = ROOT / "dotfiles"
    outer.mkdir()
    git(outer, "init", "-q")
    inner = outer / "Hyperspace"
    shutil.copytree(HOME, inner, ignore=shutil.ignore_patterns(".git", ".gitignore"))
    os.environ["HYPERSPACE_HOME"] = str(inner)
    r2 = boot_home(inner)
    c3 = homegit.Committer(inner)
    r2.lib.committer = c3
    r2.presets.save_as("INSIDE 1")
    settle(r2, c3)
    say(f"   save INSIDE 1 → warning line: {r2.lib.warning!r}")
    said = r2.lib.said["warning"]
    r2.presets.save_as("INSIDE 2")
    settle(r2, c3)
    say(f"   save INSIDE 2 → said again? {r2.lib.said['warning'] != said}; refused: {c3.refused}")
    say(f"   <home>/.git: {(inner / '.git').exists()}  <home>/.gitignore: "
        f"{(inner / '.gitignore').exists()}  commits in the outer repository: "
        f"{len(git(outer, 'log', '--oneline').splitlines())}")
    os.environ["HYPERSPACE_HOME"] = str(HOME)
    say()

    # ---- timing
    say("7. timing: request() on the frame thread, and the commit it asks for")
    c4 = homegit.Committer(HOME)
    r.lib.committer = c4
    asks, lands = [], []
    for k in range(10):
        (HOME / "presets" / f"timing-{k}.json").write_text(f'{{"k": {k}}}\n')
        t = time.perf_counter()
        c4.request(f"timing {k}")
        asks.append((time.perf_counter() - t) * 1e6)
        c4.wait(15.0)
        lands.append((time.perf_counter() - t) * 1e3)
    say(f"   request() returned in {statistics.median(asks):.0f} µs median "
        f"(max {max(asks):.0f} µs) over 10")
    say(f"   the commit landed in {statistics.median(lands):.0f} ms median "
        f"(max {max(lands):.0f} ms) over 10 — add -A, diff --cached, commit on the worker")
    t = time.perf_counter()
    r.presets.save_as("TIMED SAVE")
    say(f"   a whole Presets.save_as with git on: {(time.perf_counter() - t) * 1000:.1f} ms "
        "(the file written; the commit follows on the worker)")
    settle(r, c4)
    c4.close()
    say(f"   commits in the home now: {len(git(HOME, 'log', '--oneline').splitlines())}")

    OUT.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
