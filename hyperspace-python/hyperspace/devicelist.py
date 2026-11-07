"""The device list both Macs share (wave 5 CT1): `<library>/devices.json`.

The meta controller's: what controllers there are, each with the role that rows name.
No loadable patch reaches this file, and nothing here reaches a patch. Who holds which
controller stays on each Mac (`players.json`), and so does whether it is on
(`devices.here.json`, below). A root file is safe in the library: `Library.groups` and
`tools/migrate_library.py` walk folders only, and this is kept out of `library.py`.

**A new controller waits.** Plugging one in adopts nothing: the player board's tray shows
it (`ui_players.loose`), and dragging it to a player calls `adopt`.

**A role never renumbers.** Roles are row addresses, so:

- A role, once in the list, is never rewritten, and a new entry goes at the end, so no
  controller's place among its kind (which names its rows) moves.
- A new role comes from what the controller *is*, never from when it arrived: an APC40 is
  ``apc40``, a pad is its model's id, any other MIDI port the slug of its name. Both Macs
  get the same name for the same controller, in any order.
- The second pad of a model is ``xbox-2``. A pad entry takes any pad of its model
  (`pads.models.matches`), and two of one model are alike to a row, so these are seats,
  not units, and it doesn't matter which was plugged in first.
- **Two MIDI desks with one name are one, to us.** mido lists a name once and opens the
  first port of that name (`mido.backends.rtmidi`: `get_devices`, `_open_port`), and only
  `midiports` and `midi.Ports` may reach it, so no ordinal could open the second. A desk
  with a name of its own (``APC40 mkII`` beside ``Akai APC40``, ``Launch Control XL 2``)
  is its own controller, with a ``port`` naming it exactly. The tray's tip says so.

**What's in charge.** `[[devices]]` in config.toml is a seed, read once per Mac: the Mac
that finds no list writes one from it; a Mac that finds a list adds what its config names
and the list lacks, the first time, and the shared entry stands where a role is in both.
From then on the file is not read for the list, and a note says so. RT1 retires it. With
no `[[devices]]`, the old tables are the seed (`DEFAULTS` is that seed for a file that says
nothing, and what CL3 needs when `config._translate` goes). **A config.toml that didn't
read seeds nothing and spends nothing:** the read waits for a launch that can do it, and
the board says so.

**On or off is each Mac's.** One Mac may have no Leap, so `enabled` in the file is only
what a Mac that has never said goes by. `<home>/devices.here.json` holds what this Mac
said: seeded once from its config.toml, and set from the player board.

**The library not there.** The Drive may be unmounted at launch: the show still starts, on
`<home>/devices.last.json`, the list as this Mac last saw it, else this Mac's seed. `said`
says so on the board and a note on the SYSTEM page. Nothing is created in a folder that
isn't there. An adopt then stands for this run and waits in that copy, and reaches the
shared file when it's back, with no restart.

**The other Mac.** Drive moves the file's mtime and can land an older copy over ours, so
every write is read, merge, write, and an adopt is held for `HOLD_S` after its write: if a
file arrives without it, it is written back in. Both Macs converge on the union, and
neither writes when the file already says it, so they don't take turns. A list that
can't be read (half synced, a newer build's) is never written over: the old list stands, the
devices keep running, and it is read again. A role adopted on both Macs as two different
controllers keeps the file's, and ours takes the next free name (`renames`, which the meta
controller's holders follow).

**No disk on the frame thread.** A File Provider folder can block for seconds, which is a
frozen projector. Every touch of the shared folder runs in `_cycle` on a worker of its own,
and `look`, `adopt` and `role_for` only read memory: a stalled mount stalls that thread and
nothing else, and after `STALL_S` the board says so. It stats once per `LOOK_S`; what fails
is tried again at most every `RETRY_MAX_S`, backing off. This Mac's own files go on another
worker, so a stalled Drive never holds them up. The launch waits for the first read for
`LAUNCH_S`, then goes on with what it has, and the file lands when it answers.

Call everything from the main thread.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import apc40, config
from .pads.models import Model
from .players import NAMES

FILE = "devices.json"
COPY = "devices.last.json"      # in the home, beside players.json
HERE = "devices.here.json"      # …and what's on, on this Mac
SCHEMA = "devices/1"
HERE_SCHEMA = "devices.here/1"
HOLD_S = 600.0                  # how long a written adopt is put back if a file lacks it
LOOK_S = 1.0                    # the worker stats the file this often
RETRY_S = 2.0                   # what failed is tried again after this, doubling…
RETRY_MAX_S = 30.0              # …up to this
STALL_S = 5.0                   # a look unanswered this long is said on the board
LAUNCH_S = 3.0                  # how long a launch waits for the first read
CLOSE_S = 0.5                   # how long a quit waits for this Mac's own files
# nothing listed and nothing in config.toml: the devices that are there with no config
DEFAULTS: tuple[dict, ...] = (
    {"role": "pad", "kind": "gamepad"},
    {"role": "apc40", "kind": "midi"},
    {"role": "leap", "kind": "hands", "enabled": False},
    {"role": "bridge", "kind": "bridge", "enabled": False},
)

_OK, _ABSENT, _GONE, _BAD, _SAME = "ok", "absent", "gone", "bad", "same"


def _gone_words(what: str) -> str:
    return (f"The shared library isn't there: controllers from {what}. A new one is kept on "
            "this Mac until it's back.")


# ---------------------------------------------------------------- what a controller is called

def slug(name: str) -> str:
    """`name` as a role: lower case, a dash for anything else. No ':' (a role can't
    hold one) and no '@' (rows use it to name a role)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "controller"


def midi_entry(port: str, *, another: bool = False) -> dict:
    """The entry for a MIDI port the Mac sees. `another`: an APC40 already listed reads a
    different port, so this one names its own."""
    if apc40.PORT_MATCH.lower() in port.lower():
        own = {"port": port} if another else {}
        return {"role": "apc40", "kind": "midi", "profile": "apc40", **own}
    return {"role": slug(port), "kind": "midi", "profile": "generic", "port": port}


def pad_entry(model: Model | None, vid: int | None = None, pid: int | None = None) -> dict:
    """The entry for a pad the Mac sees: by its model; one the model table doesn't know,
    by its USB id."""
    if model is not None and model.id != "generic":
        return {"role": model.id, "kind": "gamepad", "controller": model.id}
    if vid is not None and pid is not None:
        return {"role": f"pad-{vid:04x}-{pid:04x}", "kind": "gamepad",
                "controller": f"{vid:04x}:{pid:04x}"}
    return {"role": "pad-generic", "kind": "gamepad", "controller": "generic"}


def free_role(entry: dict, raw: list[dict]) -> str:
    """The entry's role, or its first free ``-2``, ``-3``: not one in `raw`, nor a
    player's name (`@p2` always means player 2), nor the hands' DAW sink's."""
    taken = {str(e.get("role", "")) for e in raw} | NAMES | {config.DAW_ROLE}
    base, n = str(entry["role"]), 1
    role = base
    while role in taken:
        n += 1
        role = f"{base}-{n}"
    return role


def _midi_id(e: dict) -> tuple[str, str]:
    """A MIDI entry's profile and the port it asks for: an APC40's own, with none named."""
    profile = str(e.get("profile") or "apc40")
    port = e.get("port") or (apc40.PORT_MATCH if profile == "apc40" else "")
    return profile, str(port).lower()


def _same(a: dict, b: dict) -> bool:
    """The same controller, whatever each is called? What it answers to."""
    if a.get("kind") != b.get("kind"):
        return False
    if a.get("kind") == "midi":
        return _midi_id(a) == _midi_id(b)
    if a.get("kind") == "gamepad":
        return a.get("controller", "any") == b.get("controller", "any")
    return {k: v for k, v in a.items() if k != "role"} == {k: v for k, v in b.items() if k != "role"}


# ---------------------------------------------------------------- the file

def _parse(data: bytes) -> tuple[list[dict], dict]:
    """(the list, the whole document). Whatever is in the file, a ValueError at the worst."""
    try:
        doc = json.loads(data.decode("utf-8"))
    except RecursionError as e:
        raise ValueError("nested too deep") from e
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"schema {doc.get('schema')!r}" if isinstance(doc, dict) else "not a table")
    raw = doc.get("devices")
    if not isinstance(raw, list) or not all(isinstance(e, dict) for e in raw):
        raise ValueError("devices is not a list of tables")
    return raw, doc


def _text(raw: list[dict], **more) -> str:
    return json.dumps({"schema": SCHEMA, "devices": raw, **more}, indent=2, default=str) + "\n"


def _put(path: Path, text: str, tmp_name: str | None = None) -> None:
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


@dataclass
class _Waiting:
    """An entry the shared file may not say yet."""

    entry: dict
    until: float | None = None      # None: not written
    adopted: bool = True            # a seed's gives way to the file; an adopt takes a free name


class _Worker:
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


# ---------------------------------------------------------------- the worker's half

@dataclass
class _Job:
    """What a cycle needs, copied: nothing here is shared with the main thread."""

    fallback: list[dict]
    waiting: list[tuple[str, dict, bool]]
    seen: tuple
    force: bool
    may_make: bool


@dataclass
class _Seen:
    """What a cycle found."""

    state: str
    why: str = ""
    stat: tuple = ()
    merged: list[dict] | None = None
    wrote: bool = False
    write_error: str = ""
    moved: list[tuple[str, dict]] = field(default_factory=list)
    differs: list[str] = field(default_factory=list)
    asked: tuple[str, ...] = ()


def _stat(path: Path, root: Path) -> tuple:
    try:
        st = path.stat()
    except OSError:
        return (_ABSENT if root.is_dir() else _GONE,)
    return st.st_mtime_ns, st.st_size


def _read(path: Path, root: Path) -> tuple[list[dict] | None, str, str]:
    """(the list or None, `_OK` / `_ABSENT` / `_GONE` / `_BAD`, why)."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None, _ABSENT if root.is_dir() else _GONE, ""
    except OSError as e:
        return None, _BAD if root.is_dir() else _GONE, str(e)
    try:
        return _parse(data)[0], _OK, ""
    except (ValueError, TypeError) as e:     # (UnicodeDecodeError is a ValueError)
        return None, _BAD, str(e)[:120]


def _without_enabled(e: dict) -> dict:
    return {k: v for k, v in e.items() if k != "enabled"}


def _union(doc: list[dict], waiting: list[tuple[str, dict, bool]]
           ) -> tuple[list[dict], list[tuple[str, dict]], list[str]]:
    """`doc` and what waits: (the list, the adopts that had to move, the seeds that gave
    way). The file's stands on a role in both; an adopt of a different controller under a
    role the file gave away takes a free name."""
    out = [dict(e) for e in doc]
    moved: list[tuple[str, dict]] = []
    differs: list[str] = []
    for role, entry, adopted in waiting:
        have = next((e for e in out if str(e.get("role", "")) == role), None)
        if have is None:
            out.append(dict(entry))
        elif adopted and have != entry and not _same(have, entry):
            made = {**entry, "role": free_role(entry, out)}
            moved.append((role, made))
            out.append(dict(made))
        elif not adopted and _without_enabled(have) != _without_enabled(entry):
            differs.append(role)
    return out, moved, differs


def _cycle(path: Path, root: Path, job: _Job, tmp_name: str) -> _Seen:
    """One look at the shared file: a stat; if it moved, or something must be written, a
    read, a merge and, only if the file doesn't say it, a write. On the worker. Whatever the
    disk does and whatever the file holds, a `_Seen`."""
    asked = tuple(r for r, _, _ in job.waiting)
    try:
        stat = _stat(path, root)
        if stat == job.seen and not job.force:
            return _Seen(_SAME, stat=stat)
        doc, state, why = _read(path, root)
        if doc is None and state != _ABSENT:
            return _Seen(state, why=why, stat=_stat(path, root))
        if state == _ABSENT and not job.may_make and not job.waiting:
            return _Seen(state, stat=stat)
        merged, moved, differs = _union(doc if doc is not None else job.fallback, job.waiting)
        seen = _Seen(state, merged=merged, moved=moved, differs=differs, asked=asked)
        if merged == doc:
            seen.wrote = True
        else:
            try:
                _put(path, _text(merged), tmp_name)
                seen.wrote = True
            except OSError as e:
                seen.write_error = str(e)[:120]
        seen.stat = _stat(path, root)
        return seen
    except Exception as e:  # noqa: BLE001 — nothing a disk does reaches the app
        return _Seen(_BAD, why=f"{type(e).__name__}: {e}"[:120])


# ---------------------------------------------------------------- the list

class DeviceList:
    """The list, on this Mac. `raw` is as the file holds it; `checked` is what the
    registry opens. `root` the library, `home` this Mac's folder (None: tests, no files of
    its own). `said` is what the board shows, "" when all's well. `hold_seed`: this launch
    could not read its config.toml. `here` is what this Mac has said of on and off;
    `said_here`, what its config.toml says of it now."""

    def __init__(self, root: Path, home: Path | None = None, *, seed=DEFAULTS, listed: bool = False,
                 said_here: dict[str, bool] | None = None, no_midi_look: bool = False,
                 hold_seed: bool = False, notes: list[str] | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self.root = Path(root)
        self.path = self.root / FILE
        self.base = Path(home) if home is not None else self.root
        self.has_home = home is not None
        self.copy = self.base / COPY if home is not None and self.base != self.root else None
        self.here_path = self.base / HERE if home is not None else None
        self.no_midi_look = no_midi_look
        self.notes = notes if notes is not None else []
        self.clock = clock
        self.held = ""                          # what stands all run: the seed not read
        self.raw: list[dict] = []
        self.waiting: dict[str, _Waiting] = {}
        self.here: dict[str, bool] = {}
        self.renames: list[tuple[str, str]] = []     # roles a rename moved: the holders follow
        self._said = ""
        self._unread = False
        self._dirty = False
        self._copy_text: str | None = None
        self._seen: tuple = ()
        self._from = ""
        self._tmp = f"{FILE}.{os.getpid()}.tmp"
        self._shared = _Worker("device list: library")
        self._local = _Worker("device list: this Mac")
        self._done: deque[_Seen] = deque()
        self._asked = False
        self._asked_at = 0.0
        self._next = float("-inf")
        self._delay = RETRY_S
        self._may_make = not hold_seed
        self._told: set[str] = set()
        self._open([dict(e) for e in seed], listed, said_here or {}, hold_seed)

    @classmethod
    def open(cls, cfg: dict, home: Path) -> DeviceList:
        """This launch's list, and `cfg`'s device list taken from it. Called before the
        windows and before a `Library`: it reads the configured path itself, and waits for
        that `LAUNCH_S` at the most."""
        lp = cfg.get("library", {}).get("path", "")
        notes = cfg.setdefault("notes", [])
        hold = "device_seed" not in cfg
        out = cls(Path(lp) if lp else home, home, seed=cfg.get("device_seed", DEFAULTS),
                  listed=bool(cfg.get("device_seed_listed")), said_here=cfg.get("device_here"),
                  no_midi_look=bool(cfg.get("no_midi_look")), hold_seed=hold, notes=notes)
        entries, problems, said = out.checked()
        notes += [*problems, *said]
        config.take_devices(cfg, entries)
        return out

    def checked(self) -> tuple[list[dict], list[str], list[str]]:
        """(entries, problems, notes): `config.listed_devices` over the list, and on or off
        as this Mac says. Whatever the list holds, it doesn't raise."""
        try:
            return config.listed_devices(self.raw, self.base, self.here)
        except Exception as e:  # noqa: BLE001 — a shared file never stops the show
            return [], [f"devices: {FILE} would not check: {type(e).__name__}: {e}"[:200]], []

    @property
    def said(self) -> str:
        return self._said or self.held

    # ---- the launch ----

    def _read_local(self, path: Path | None) -> dict | None:
        """One of this Mac's own files: its document, or None."""
        if path is None:
            return None
        try:
            doc = json.loads(path.read_bytes().decode("utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("not a table")
            return doc
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, RecursionError) as e:
            self._note(f"devices: {path.name} could not be read ({e}): not used")
            return None

    def _read_copy(self) -> tuple[list[dict], list[tuple[dict, bool]]] | None:
        doc = self._read_local(self.copy)
        if doc is None:
            return None
        raw = doc.get("devices")
        if doc.get("schema") != SCHEMA or not isinstance(raw, list):
            self._note(f"devices: {COPY} is not a list: not used")
            return None
        kept = [(w["entry"], w.get("adopted") is not False) for w in doc.get("unwritten", ())
                if isinstance(w, dict) and isinstance(w.get("entry"), dict) and "role" in w["entry"]]
        return [e for e in raw if isinstance(e, dict)], kept

    def _read_here(self) -> dict[str, bool] | None:
        """What this Mac has said of on and off; None: it has never been read from config.toml."""
        doc = self._read_local(self.here_path)
        if doc is None or doc.get("schema") != HERE_SCHEMA or not isinstance(doc.get("on"), dict):
            return None
        return {str(r): v for r, v in doc["on"].items() if isinstance(v, bool)}

    def _open(self, seed: list[dict], listed: bool, said_here: dict[str, bool], hold: bool) -> None:
        last = self._read_copy()
        here = self._read_here()
        self._from = "this Mac's last list" if last is not None else "this Mac's config.toml"
        for e, adopted in last[1] if last is not None else ():
            self.waiting[str(e["role"])] = _Waiting(e, adopted=adopted)
        self.raw = [dict(e) for e in (last[0] if last is not None else seed)]
        if hold:
            # no seed to read: a later launch reads it, so nothing here counts as that
            self.held = ("config.toml didn't read, so the controllers it lists weren't either: "
                         "fix it and relaunch.")
            self._note(f"devices: {self.held}")
            self.here = here or {}
        elif here is None and self.has_home:
            # this Mac's one read of its config.toml: what it says of on and off, and what
            # it adds. A role the list has keeps the list's. (The old tables' defaults add
            # nothing: a Mac that said nothing has nothing to add.)
            self.here = dict(said_here)
            self._save_here()
            for e in seed:
                if listed or e not in DEFAULTS:
                    self.waiting.setdefault(str(e.get("role", "")), _Waiting(e, adopted=False))
        else:
            self.here = here or {}
            if listed and self.has_home:
                self._note(f"devices: config.toml's [[devices]] is not read: {FILE} in the "
                           "library says, and it's set from the player board")
            for role, on in said_here.items():
                if self.here.get(role, on) != on:
                    self._note(f"devices: config.toml says {role} is {'on' if on else 'off'}, and this "
                               "Mac has it otherwise: it's set from the player board")
        self._give()
        if self._shared.wait(LAUNCH_S):
            self._take()
            self._dirty = False
        else:
            self._say(f"The shared library isn't answering: controllers from {self._from}.")

    # ---- keeping up ----

    def _give(self) -> None:
        """A cycle, on the worker. At most one is out."""
        unwritten = any(w.until is None for w in self.waiting.values())
        job = _Job([dict(e) for e in self.raw],
                   [(r, dict(w.entry), w.adopted) for r, w in self.waiting.items()],
                   self._seen, bool(unwritten or self._unread or self._said), self._may_make)
        self._asked, self._asked_at = True, self.clock()
        path, root, tmp = self.path, self.root, self._tmp
        self._shared.give(lambda: self._done.append(_cycle(path, root, job, tmp)))

    def _take(self) -> None:
        while self._done:
            self._landed(self._done.popleft())

    def _backoff(self, now: float) -> None:
        self._next = now + self._delay
        self._delay = min(self._delay * 2, RETRY_MAX_S)

    def _landed(self, r: _Seen) -> None:
        """A cycle's answer, on the main thread."""
        now = self.clock()
        self._asked = False
        self._seen = r.stat
        if r.state == _SAME or (r.state == _ABSENT and r.merged is None):
            self._next, self._delay = now + LOOK_S, RETRY_S
            if self._said:
                self._said = ""
            return
        self._unread = r.state == _BAD
        if r.merged is None:
            words = (_gone_words(self._from) if r.state == _GONE else
                     f"{FILE} could not be read ({r.why}): controllers as they were, "
                     "and nothing is written over it.")
            self._say(words)
            self._keep_copy()
            self._backoff(now)
            return
        for old, made in r.moved:
            new = str(made["role"])
            self.waiting.pop(old, None)
            self.waiting[new] = _Waiting(made)
            self.renames.append((old, new))
            self._note(f"devices: the other Mac named another controller {old}: this one is {new}")
        merged = [dict(e) for e in r.merged]
        have = {str(e.get("role", "")) for e in merged}
        merged += [dict(w.entry) for role, w in self.waiting.items() if role not in have]   # since
        if merged != self.raw:
            self.raw, self._dirty = merged, True
        for role in r.differs:
            if role not in self._told:
                self._told.add(role)
                self._note(f"devices: config.toml says otherwise of {role}: {FILE} in the library stands")
        if r.state == _ABSENT:
            # just made here. The other Mac's may land on it, so held
            for e in r.merged:
                self.waiting.setdefault(str(e.get("role", "")), _Waiting(e, adopted=False))
            self._note(f"devices: {self.path} made from {self._from}: from now on it says "
                       "what controllers there are, on both Macs")
        if r.wrote:
            if self._said:
                self._note(f"devices: {FILE} is back")
            self._said, self._from = "", "this Mac's last list"
            until = now + HOLD_S
            for role in (*r.asked, *(str(e.get("role", "")) for e in r.merged)):
                w = self.waiting.get(role)
                if w is not None and w.until is None and any(
                        str(e.get("role", "")) == role for e in r.merged):
                    w.until = until
            self._next, self._delay = now + LOOK_S, RETRY_S
        else:
            self._say(f"{FILE} not written ({r.write_error}): kept on this Mac, and tried again.")
            self._backoff(now)
        self._keep_copy()

    def _keep_copy(self) -> None:
        if self.copy is None:
            return
        unwritten = [{"entry": w.entry, "adopted": w.adopted}
                     for w in self.waiting.values() if w.until is None]
        text = _text(self.raw, unwritten=unwritten)
        if text == self._copy_text:
            return
        self._copy_text = text
        self._local.give(lambda path=self.copy, text=text: self._put_local(path, text))

    def _save_here(self) -> None:
        if self.here_path is not None:
            text = json.dumps({"schema": HERE_SCHEMA, "on": self.here}, indent=2) + "\n"
            self._local.give(lambda path=self.here_path, text=text: self._put_local(path, text))

    def _put_local(self, path: Path, text: str) -> None:
        try:
            _put(path, text)
        except OSError as e:
            self._note(f"devices: {path.name} not written: {e}")

    def look(self) -> bool:
        """Has the list changed? Called every `devices.WATCH_FRAMES`, and it reads memory:
        what the worker found, and it gives the worker its next cycle when one is due."""
        self._take()
        now = self.clock()
        for role, w in list(self.waiting.items()):
            if w.until is not None and now >= w.until:
                del self.waiting[role]
        if self._asked:
            if now - self._asked_at >= STALL_S:
                self._say("The shared library isn't answering: controllers as they are, and a "
                          "new one is kept on this Mac until it does.")
        elif now >= self._next:
            self._give()
        dirty, self._dirty = self._dirty, False
        return dirty

    def sync(self, timeout: float | None = 10.0) -> None:
        """Wait for a whole cycle, for what isn't the frame: the tests, and tools."""
        self._shared.wait(timeout)
        self._take()
        self._give()
        self._shared.wait(timeout)
        self._take()
        self._local.wait(timeout)

    def close(self) -> None:
        """A quit: this Mac's own files get a moment. A stalled Drive holds up nothing."""
        self._take()
        self._local.wait(CLOSE_S)

    # ---- adopting, and on or off ----

    def adopt(self, entry: dict) -> str:
        """The controller of `entry` (`midi_entry`, `pad_entry`) into the list, at its
        end; its role. A MIDI port already listed, adopted a moment ago on the other Mac,
        keeps that entry. The caller applies the list. Memory only: the worker writes it,
        and if the file gave its name away meanwhile, `renames` says what it became."""
        self._take()
        role = self.role_for(entry)
        if any(str(e.get("role", "")) == role for e in self.raw):
            return role
        made = {**entry, "role": role}
        self.raw = [*self.raw, made]
        self.waiting[role] = _Waiting(made)
        self._keep_copy()
        self._next = float("-inf")          # (the next look gives it, if one is out now)
        if not self._asked:
            self._give()
        return role

    def role_for(self, entry: dict) -> str:
        """What adopting `entry` now would call it (the tray's tooltip)."""
        if entry.get("kind") == "midi":
            same = next((e for e in self.raw if _same(e, entry)), None)
            if same is not None:
                return str(same["role"])
        return free_role(entry, self.raw)

    def is_on(self, role: str) -> bool:
        """Is `role` on, on this Mac?"""
        if role in self.here:
            return self.here[role]
        entry = next((e for e in self.raw if e.get("role") == role), None)
        return entry is None or entry.get("enabled", True) is True

    def set_here(self, role: str, on: bool) -> None:
        """`role` on or off, on this Mac alone, from now on. The caller applies the list."""
        self.here[role] = bool(on)
        self._save_here()

    def take_renames(self) -> list[tuple[str, str]]:
        out, self.renames = self.renames, []
        return out

    # ---- saying ----

    def _note(self, note: str) -> None:
        self.notes.append(note[:200])

    def _say(self, words: str) -> None:
        if words != self._said:
            self._said = words
            self._note(f"devices: {words}")

