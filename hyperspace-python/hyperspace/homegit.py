"""The library home as a git repository: a commit on each save, opt-in.

With ``[library] git = true`` in config.toml (plan 19 WP6) app.main builds
one `Committer` over the home and sets it as ``library.committer``; the
library asks for a commit at the end of each of its saves
(`Library._commit`: a preset or module preset saved, one sent to the
trash, a show written). With the key off — the default — this module is
never imported, no thread starts and nothing is written.

What a commit is: ``git add -A`` then ``git commit``, everything the
``.gitignore`` lets through, so a hand edit of config.toml or a launch's
migration rides in the next save's commit. Nothing staged, no commit.
The words are taken once ``add -A`` has run: every request made by then is
one commit, the first message its subject and the rest its body, so a save
that lands while the worker is busy is never committed under another's
words alone.

The first request (never the launch) looks at the home:

- not a repository: ``git init``, ``.gitignore`` (`IGNORE`) if there is
  none, and everything committed as `FIRST`, the save that asked included;
- a repository whose top level is the home: used as it is (the owner's
  own ``.gitignore`` and branch kept; ours written only if there is none);
- inside another repository (a dotfiles repository, a home folder under
  git): never initialised, never committed — one note, and the key does
  nothing for the run (`refused`).

Git never blocks, fails or slows a save: `request` appends to a list and
returns; one daemon thread runs the commands, each with a timeout,
``GIT_TERMINAL_PROMPT=0``, no hooks of the machine's and no signing. A
missing binary, a locked index, a timeout or anything else is said once
through `notes()` — "git: not committed (<reason>); saves are not
affected" — and not again until a commit has gone through; the next
request's ``add -A`` takes up whatever a failed one left. The worker
never touches the library: `Library.poll` drains `notes()` on the frame
thread.

Local only: the module runs init, rev-parse, config, add, diff and commit,
nothing else; nothing leaves this machine. Sharing presets between people
is ``shared/`` and ``tools/shared_presets.py``, not this.

Imports nothing from the package (a leaf, like placement.py).
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

IGNORE = """\
# Written by Hyperspace when [library] git was switched on. Yours to edit.
weights/
trash/
*.log
last_show
windows.json
*.bak-*
.DS_Store
"""

FIRST = "Hyperspace: the home as it was when git was switched on"
NAME, EMAIL = "Hyperspace", "hyperspace@localhost"   # only when the machine has no identity

# every command: no hook of the machine's runs, and no signing prompt can hang it
SAFE = ("-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false")
# variables that would aim a command at some other repository than the home's
LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
            "GIT_PREFIX")


class GitFailed(Exception):
    """One command that did not do its job; the message is the reason."""


def is_real_home(home: Path) -> bool:
    """Is `home` the owner's ~/Hyperspace? Read from the path's text and
    the test home's own links only: nothing under ~/Hyperspace is looked at."""
    real = os.path.abspath(os.path.expanduser(os.path.join("~", "Hyperspace")))
    return os.path.abspath(home) == real or os.path.realpath(home) == real


def _same(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.realpath(a) == os.path.realpath(b)


class Committer:
    """A commit of the home on request, on a thread of its own.

    `refused` is true once the home has proved to be inside another
    repository; `commits` counts the commits this run made."""

    def __init__(self, home: Path, *, git: str = "git", timeout: float = 10.0):
        home = Path(home).expanduser()
        if os.environ.get("PYTEST_CURRENT_TEST") and is_real_home(home):
            raise RuntimeError(f"homegit: {home} is the owner's home — never under pytest")
        self.home = home
        self.git = git
        self.timeout = float(timeout)
        self.refused = False
        self.commits = 0
        self._ready = False          # the home looked at, `.gitignore` in place
        self._head = False           # the repository has a commit
        self._ident: tuple[str, ...] | None = None
        self._failed = False         # a failure said, and no commit since
        self._pending: list[str] = []
        self._notes: list[str] = []
        self._busy = False
        self._closing = False
        self._cond = threading.Condition()
        self._thread: threading.Thread | None = None

    # ---- the frame thread's side ----

    def request(self, message: str) -> None:
        """Ask for a commit of the home as it now is. Returns at once."""
        with self._cond:
            if self.refused:
                return
            self._pending.append(str(message))
            self._closing = False
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="homegit", daemon=True)
                self._thread.start()
            self._cond.notify_all()

    def notes(self) -> list[str]:
        """What the worker has to say since the last call (drained)."""
        with self._cond:
            out, self._notes = self._notes, []
        return out

    def wait(self, timeout: float = 10.0) -> bool:
        """Block until nothing is waiting or running (tests, tools/homegit_demo.py);
        False if `timeout` ran out first. The app never calls it."""
        with self._cond:
            return self._cond.wait_for(lambda: not self._pending and not self._busy, timeout)

    def close(self, timeout: float = 2.0) -> None:
        """At quit and ⌘R: let the worker finish what is waiting, for up to
        `timeout` seconds. What is left is committed by the next run's
        first save (its ``add -A``)."""
        with self._cond:
            self._closing = True
            self._cond.notify_all()
            t = self._thread
        if t is not None:
            t.join(timeout)

    # ---- the worker ----

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._pending:
                    if self._closing:
                        return
                    self._cond.wait()
                self._busy = True
            try:
                self._commit()
            except Exception as e:  # noqa: BLE001 — anything at all is a note, never a raise
                # a failure drops the words waiting; the next request's add -A has the files
                self._take()
                self._fail(str(e) if isinstance(e, GitFailed) else f"{type(e).__name__}: {e}")
            finally:
                with self._cond:
                    self._busy = False
                    self._cond.notify_all()

    def _take(self) -> list[str]:
        """Every message waiting — taken once ``add -A`` has staged the home,
        so a save that landed while this commit was being prepared is in it
        under its own words, not in it silently with its words left for an
        empty commit that is never made."""
        with self._cond:
            batch, self._pending = self._pending, []
        return batch

    def _say(self, note: str) -> None:
        with self._cond:
            self._notes.append(note)

    def _fail(self, reason: str) -> None:
        if not self._failed:
            self._failed = True
            self._say(f"git: not committed ({reason}); saves are not affected")

    def _env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in LOCATORS}
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["LC_ALL"] = "C"          # git's own words, so "not a git repository" reads as such
        return env

    def _git(self, *args: str, pre: tuple[str, ...] = (), ok: tuple[int, ...] | None = (0,)):
        verb = args[0]
        try:
            r = subprocess.run([self.git, *SAFE, *pre, *args], cwd=self.home, env=self._env(),
                               stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=self.timeout,
                               check=False)
        except FileNotFoundError as e:
            raise GitFailed("git is not on the PATH" if os.sep not in self.git
                            else f"no git at {self.git}") from e
        except subprocess.TimeoutExpired as e:
            raise GitFailed(f"git {verb} took longer than {self.timeout:g} s") from e
        except OSError as e:
            raise GitFailed(f"git {verb}: {e}") from e
        if ok is not None and r.returncode not in ok:
            said = next((ln.strip() for ln in r.stderr.splitlines() if ln.strip()), "")
            raise GitFailed(f"git {verb} exited {r.returncode}" + (f": {said}" if said else ""))
        return r

    def _prepare(self) -> None:
        """The first request's look at the home: init, refuse or take it as it is."""
        if not self.home.is_dir():
            raise GitFailed(f"{self.home} is not a folder")
        r = self._git("rev-parse", "--show-toplevel", ok=None)
        if r.returncode == 0:
            top = Path(r.stdout.strip())
            if not _same(top, self.home):
                with self._cond:
                    self.refused = True
                    self._pending.clear()
                self._say(f"git: {self.home} is inside another repository ({top}): "
                          "not committing")
                return
        elif "not a git repository" in r.stderr.lower():
            self._git("init", "-q")
        else:
            said = next((ln.strip() for ln in r.stderr.splitlines() if ln.strip()), "")
            raise GitFailed(f"git rev-parse exited {r.returncode}" + (f": {said}" if said else ""))
        try:
            with open(self.home / ".gitignore", "x", encoding="utf-8") as f:
                f.write(IGNORE)
        except FileExistsError:
            pass                                        # the owner's, or ours from before: kept
        except OSError as e:
            raise GitFailed(f".gitignore: {e}") from e
        self._ready = True

    def _identity(self) -> tuple[str, ...]:
        """``-c user.name=… -c user.email=…`` for what the machine lacks."""
        if self._ident is None:
            pre: list[str] = []
            for key, value in (("user.name", NAME), ("user.email", EMAIL)):
                if not self._git("config", key, ok=None).stdout.strip():
                    pre += ["-c", f"{key}={value}"]
            self._ident = tuple(pre)
        return self._ident

    def _commit(self) -> None:
        if not self._ready:
            self._prepare()
            if self.refused:
                return
        if not self._head:
            self._head = self._git("rev-parse", "--verify", "-q", "HEAD",
                                   ok=None).returncode == 0
        self._git("add", "-A")
        batch = self._take() or ["save"]
        if self._git("diff", "--cached", "--quiet", ok=(0, 1)).returncode == 0:
            return                                      # nothing staged: no commit
        if self._head:
            subject, body = batch[0], batch[1:]
        else:                                           # the first: everything as it was
            subject, body = FIRST, batch
        args = ["commit", "-q", "-m", subject]
        if body:
            args += ["-m", "\n".join(body)]
        self._git(*args, pre=self._identity())
        self._head = True
        self.commits += 1
        self._failed = False
