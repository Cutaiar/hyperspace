"""What a file both Macs share needs, whatever it holds (wave 5 CT1, SC2): the worker no
stalled Drive can hold up, a whole write, and a stat that says a folder has gone. `devicelist`
and `displays` each keep their own merge and their own words. No GL, no imgui, nothing of the
package.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from collections.abc import Callable
from pathlib import Path

OK, ABSENT, GONE, BAD, SAME = "ok", "absent", "gone", "bad", "same"


def put(path: Path, text: str, tmp_name: str | None = None) -> None:
    """Whole, through a temporary file beside it; an OSError if not."""
    tmp = path.with_name(tmp_name or f"{path.name}.tmp")
    try:
        tmp.write_text(text)
        tmp.replace(path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def stat(path: Path, root: Path) -> tuple:
    """(mtime, size), or (`ABSENT`,) in a folder that is there, or (`GONE`,) with none."""
    try:
        st = path.stat()
    except OSError:
        return (ABSENT if root.is_dir() else GONE,)
    return st.st_mtime_ns, st.st_size


def library_root(path: str, hold: bool, copy: Path, home: Path, file: str) -> tuple[Path, bool]:
    """(the library, whether to stay off it). `path` is config.toml's; `hold`: config.toml
    didn't read, so a "" there says nothing. Then it's where this Mac's copy says it last
    was. With no copy that says, and no `file` (the shared file's name) in the home to show
    that the library is the home, this launch doesn't know: the home is no stand-in, as what's
    written there is lost on the next good launch, so it stays on the copy alone."""
    if path:
        return Path(path), False
    if not hold:
        return home, False
    try:
        doc = json.loads(copy.read_bytes().decode("utf-8"))
        known = doc.get("library") if isinstance(doc, dict) else None
    except (OSError, ValueError, RecursionError):
        known = None
    if isinstance(known, str) and known:
        return Path(known), False
    return home, not (home / file).exists()


class Worker:
    """Runs what it's given, in order, on a daemon thread that lasts as long as there is
    work. A thread stuck on a stalled disk holds up its own queue and nothing else."""

    def __init__(self, name: str):
        self.name = name
        self.queue: deque[Callable[[], None]] = deque()
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None

    def give(self, fn: Callable[[], None]) -> None:
        with self.lock:
            self.queue.append(fn)
            if self.thread is None:
                self.thread = threading.Thread(target=self._run, name=self.name, daemon=True)
                self.thread.start()

    def _run(self) -> None:
        while True:
            with self.lock:
                if not self.queue:
                    self.thread = None
                    return
                fn = self.queue.popleft()
            try:
                fn()
            except Exception:  # noqa: BLE001, S110 — each job says its own failures
                pass

    def wait(self, timeout: float | None) -> bool:
        """True when it has finished everything given, within `timeout`."""
        thread = self.thread
        if thread is not None:
            thread.join(timeout)
        return self.thread is None or not self.thread.is_alive()
