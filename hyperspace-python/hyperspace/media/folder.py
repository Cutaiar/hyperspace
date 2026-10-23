"""The media folder: the shared cloud folder (`<library>/media/`) and this
Mac's own (`<home>/media/`), scanned off the frame thread into a listing the
UI and the resolver read. It is the `adapters.Resolver` for the file kinds.

Everything slow lives in `scan()`, which runs on the media pool: stat, the
cloud-placeholder flags, a timed read of each file's first 64 KiB. `status()`
and `path()` only read what the last scan found, so the frame thread never
touches the disk for them. A file that is mid-sync reads `fetching`, one that
has gone reads `missing`, junk reads `error: ...`; none of it stops a scan."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from . import ids, pool, thumbs
from .adapters import VIDEO_EXT
from .source import FETCHING, MISSING, READY, error
from .still import STILL_EXT

PROBE_BYTES = 64 * 1024
SLOW_READ = 0.5          # a first-64-KiB read slower than this is a file still arriving
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
UF_DATAVAULT = getattr(stat, "UF_DATAVAULT", 0x00000080)


@dataclass(frozen=True)
class Entry:
    sid: str
    path: Path
    kind: str          # "still" | "video" (| "other" in a scan(all=True) listing)
    size: int
    mtime: float
    group: str         # the first folder under the root, "" at the top
    status: str


def _probe(path: Path) -> float:
    """Seconds taken to read the first 64 KiB of `path`. Raises OSError."""
    t = time.monotonic()
    with open(path, "rb") as f:
        f.read(PROBE_BYTES)
    return time.monotonic() - t


def _kind(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    if ext in STILL_EXT:
        return "still"
    if ext in VIDEO_EXT:
        return "video"
    return "other"


class MediaFolder:
    def __init__(self, shared: Path | None, local: Path, cache: Path):
        self.shared = Path(shared) if shared else None
        self.local = Path(local)
        self.cache = Path(cache)
        self.proxy_cache = self.cache / "proxies"
        self.thumb_dir = self.cache / "thumbs"
        for d in (self.shared, self.local):
            if d is not None:
                try:
                    d.mkdir(parents=True, exist_ok=True)
                except OSError:
                    pass
        self.entries: tuple[Entry, ...] = ()
        self.changed = 0
        self._info: dict[str, Entry] = {}     # every known id, incl. added file: ones
        self._files: dict[str, Path] = {}     # file: ids from add_file
        self._probed: dict[tuple, str] = {}   # (path, mtime_ns, size, dataless) -> status
        self._lock = threading.Lock()
        self._scan_lock = threading.Lock()
        self._scan_job: Future | None = None
        self._thumb_jobs: dict[str, Future] = {}
        self._thumb_bad: set[str] = set()
        self.copy_jobs: dict[str, Future] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- the Resolver ------------------------------------------------------
    def path(self, sid: str) -> Path | None:
        e = self._info.get(sid)
        if e is not None:
            return e.path
        try:
            p = self._locate(sid)
        except ValueError:
            return None
        return p if p is not None and p.is_file() else None

    def live(self, sid: str):
        return None   # live feeds come from the app's resolver (plan 32 T8)

    def _locate(self, sid: str) -> Path | None:
        k = ids.parse(sid)
        if k.kind == "file":
            return Path(k.ref)
        root = self.shared if k.kind == "shared" else self.local if k.kind == "local" else None
        if root is None or ".." in Path(k.ref).parts or Path(k.ref).is_absolute():
            return None
        return root / k.ref

    # -- scanning ----------------------------------------------------------
    def add_file(self, path) -> str:
        """Put an absolute path on the books (checked by each scan, not listed)."""
        sid = f"file:{Path(path).expanduser().resolve()}"
        self._files[sid] = Path(sid[5:])
        return sid

    def _walk(self, root: Path):
        """Yield (relative dir with trailing slash, real name, path on disk,
        is an iCloud `.name.icloud` placeholder) for every visible file."""
        stack = [(root, "")]
        while stack:
            d, rel = stack.pop()
            try:
                items = list(os.scandir(d))
            except OSError:
                continue
            for de in items:
                try:
                    name = de.name
                    placeholder = name.startswith(".") and name.endswith(".icloud") and len(name) > 8
                    if name.startswith(".") and not placeholder:
                        continue
                    if de.is_dir(follow_symlinks=False):
                        stack.append((Path(de.path), f"{rel}{name}/"))
                    elif de.is_file():
                        yield rel, (name[1:-7] if placeholder else name), Path(de.path), placeholder
                except OSError:
                    continue

    def _status_of(self, path: Path, st: os.stat_result | None, placeholder: bool) -> tuple[str, int, float]:
        if st is None:
            return MISSING, 0, 0.0
        flags = getattr(st, "st_flags", 0)
        dataless = placeholder or bool(flags & SF_DATALESS) or (st.st_size == 0 and bool(flags & UF_DATAVAULT))
        key = (str(path), st.st_mtime_ns, st.st_size, dataless)
        if self._probed.get(key) == READY:
            return READY, st.st_size, st.st_mtime
        if dataless:
            pool.submit(self._wake, path)   # reading it asks the cloud client to download it
            return FETCHING, st.st_size, st.st_mtime
        if st.st_size == 0:
            return error("empty file"), 0, st.st_mtime
        try:
            slow = _probe(path) > SLOW_READ
        except OSError as e:
            return error(e.strerror or "unreadable"), st.st_size, st.st_mtime
        if slow:
            return FETCHING, st.st_size, st.st_mtime
        self._probed[key] = READY
        return READY, st.st_size, st.st_mtime

    @staticmethod
    def _wake(path: Path) -> None:
        try:
            _probe(path)
        except OSError:
            pass

    def scan(self, all: bool = False) -> list[Entry]:
        """Walk both folders. Updates `entries`, `changed` and the status
        cache; `all=True` also returns unsupported files (`entries` never
        lists them)."""
        with self._scan_lock:
            found: list[Entry] = []
            roots = [(self.local, "local")]
            if self.shared is not None:
                roots.insert(0, (self.shared, "shared"))
            for root, label in roots:
                for rel, name, p, placeholder in self._walk(root):
                    kind = _kind(name)
                    try:
                        st = os.stat(p)
                    except OSError:
                        st = None
                    if kind == "other":
                        status = error("unsupported")
                        size, mt = (st.st_size, st.st_mtime) if st else (0, 0.0)
                    else:
                        status, size, mt = self._status_of(p, st, placeholder)
                    group = rel.split("/", 1)[0]
                    found.append(Entry(f"{label}:{rel}{name}", root / rel / name, kind, size, mt, group, status))
            found.sort(key=lambda e: e.sid)
            listed = tuple(e for e in found if e.kind != "other")
            info = {e.sid: e for e in listed}
            for sid, p in list(self._files.items()):
                try:
                    st = os.stat(p)
                except OSError:
                    st = None
                kind = _kind(p.name)
                if kind == "other" and st is not None:
                    status, size, mt = error("unsupported"), st.st_size, st.st_mtime
                else:
                    status, size, mt = self._status_of(p, st, False)
                info[sid] = Entry(sid, p, kind, size, mt, "", status)
            def sig(d):
                return {s: (e.size, e.mtime, e.status) for s, e in d.items()}
            if sig(info) != sig(self._info):
                self.changed += 1
            self.entries = listed
            self._info = info
            if len(self._probed) > 20000:
                self._probed.clear()
            return found if all else list(listed)

    def status(self, sid: str) -> str:
        """The last scan's word on `sid`; `missing` for anything it did not see."""
        e = self._info.get(sid)
        return e.status if e is not None else MISSING

    # -- the watch timer ---------------------------------------------------
    def start(self, every: float = 2.0) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._watch, args=(every,),
                                        name="media-folder-watch", daemon=True)
        self._thread.start()

    def _watch(self, every: float) -> None:
        while not self._stop.is_set():
            job = self._scan_job
            if job is None or job.done():
                try:
                    self._scan_job = pool.submit(self._safe_scan)
                except RuntimeError:
                    pass
            self._stop.wait(every)

    def _safe_scan(self) -> None:
        try:
            self.scan()
        except Exception:  # noqa: BLE001 — a bad folder must not kill the watch
            pass

    def stop(self) -> None:
        """Stop the timer thread; a scan already running finishes on its own."""
        self._stop.set()
        t, self._thread = self._thread, None
        if t is not None:
            t.join()

    # -- thumbnails and copies --------------------------------------------
    def thumb(self, sid: str) -> Path | None:
        """The thumbnail if it is made; otherwise queue it and return None.
        The name carries the file's mtime and size, so a changed file gets a
        new thumbnail."""
        e = self._info.get(sid)
        if e is None or e.status != READY:
            return None
        key = hashlib.sha1(f"{sid}|{e.mtime}|{e.size}".encode()).hexdigest()[:20]
        out = self.thumb_dir / f"{key}.png"
        if out.exists():
            return out
        with self._lock:
            job = self._thumb_jobs.get(key)
            if key not in self._thumb_bad and (job is None or job.done()):
                self._thumb_jobs[key] = pool.submit(self._make_thumb, e.path, out, key)
        return None

    def _make_thumb(self, path: Path, out: Path, key: str) -> None:
        try:
            thumbs.make(path, out)
        except Exception:  # noqa: BLE001 — a bad file just gets no thumbnail
            self._thumb_bad.add(key)

    def copy_to_shared(self, sid: str) -> str:
        """Copy a file into the shared folder on the pool and return the new
        `shared:` id at once; the entry appears in a scan after the job
        (kept in `copy_jobs[new_id]`) finishes. The copy lands under a
        `.part` name and is renamed, so a scan never lists half a file. A
        name clash gets a ` (n)` suffix."""
        if self.shared is None:
            raise ValueError("no shared folder: set [library] path")
        src = self.path(sid)
        if src is None:
            raise FileNotFoundError(sid)
        self.shared.mkdir(parents=True, exist_ok=True)
        stem, ext = os.path.splitext(src.name)
        dest, n = self.shared / src.name, 1
        with self._lock:
            while dest.exists() or f"shared:{dest.name}" in self.copy_jobs:
                dest = self.shared / f"{stem} ({n}){ext}"
                n += 1
            new = f"shared:{dest.name}"
            self.copy_jobs[new] = pool.submit(self._copy, src, dest)
        return new

    @staticmethod
    def _copy(src: Path, dest: Path) -> None:
        tmp = dest.with_name(dest.name + ".part")
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)
