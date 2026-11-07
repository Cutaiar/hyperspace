"""One row per display, and the file both Macs share (wave 5 SC2): `<library>/displays.json`.

The meta controller's: which display shows what. No loadable patch reaches this file, and
nothing here reaches a patch. A root file is safe in the library: `Library.groups` and
`tools/migrate_library.py` walk folders only, and this is kept out of `library.py`.

**A row.** A display, by its label (`placement.labels`: its exact name, or its name and an
ordinal across the desk when two share one), remembers its job: what targets it, whether
it's fullscreen, and its flips. ::

    {"schema": "displays/1",
     "displays": {"TV #2": {"target": "output.2", "fullscreen": true,
                            "flip_x": false, "flip_y": false, "at": 1730000000.25}}}

`target` is `output.N`, `control`, or "" for nothing. **A display has one target; a target
may go to several displays; the control window goes to one.** The first is the file's shape,
the second is `wanted`'s, and the third is `set_target`'s, on this Mac's displays, with
`wanted` holding it for what two Macs may have written. `output.N` is the saved name wires
and bus cuts use, so a row names an output and N never renumbers.

**`wanted(rows, screens)` is the seam.** It takes the rows and the connected list and gives
what should be open, and it opens nothing. A launch (`app._windows`) acts on it; SC3b's
monitor callback will too, which is when a change of target stops waiting for ⌘R.

**What's in charge.** `[output] monitor`, `control_monitor`, `fullscreen` and
`[[output.screens]]` are a seed, read once per Mac (`seed_rows`): where each window would
have opened goes on that display's row. From then on config.toml is not read for this, and
a note says so; RT1 retires it. Two outputs asking for one display: the first has it, and a
note says the other has none. A control window on a display a render has gets no row of its
own, and floats there as it always did. **A config.toml that didn't read seeds nothing and
spends nothing:** this launch runs on a default in memory, never written.

**`--laptop` leaves all this alone:** no read, no write, no seed. One plain output on the
primary display, by `config.laptop`, as ever.

**The library not there.** The Drive may be unmounted at launch: the show still starts, on
`<home>/displays.last.json`, the rows as this Mac last saw them, and `said` says so on the
panel. Nothing is created in a folder that isn't there. A change stands, waits in that copy,
and reaches the shared file when it's back, with no restart.

**The other Mac.** Each row carries `at`, when it was last chosen, and the merge takes the
later of each row, on both Macs: the same answer in any order, so they converge, and neither
writes when the file already says it, so they don't take turns. No timer is needed: an older
copy Drive lands over ours just loses, and is written back over once. Two rows with one `at`
keep the file's, so the file settles it. A seed's `at` is 0, so what's in the file stands.
Rows are never removed. A file that can't be read (half synced, a newer build's) is never
written over: the rows in memory stand, and it's read again.

**No disk on the frame thread.** `_cycle` runs on a worker of its own (`sharedfile.Worker`),
and `look` and `set` only touch memory. The launch waits `LAUNCH_S` for the first read at
most, then goes on with what it has.

Call everything from the main thread.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config, placement, sharedfile
from .outputs import MAX_OUTPUTS
from .placement import Screen
from .sharedfile import Worker

FILE = "displays.json"
COPY = "displays.last.json"     # in the home, beside devices.last.json
SCHEMA = "displays/1"
CONTROL = "control"
NOTHING = ""
TICKS = ("fullscreen", "flip_x", "flip_y")
LOOK_S = 1.0                    # the worker stats the file this often
RETRY_S = 2.0                   # what failed is tried again after this, doubling…
RETRY_MAX_S = 30.0              # …up to this
STALL_S = 5.0                   # a look unanswered this long is said on the panel
LAUNCH_S = 3.0                  # how long a launch waits for the first read
CLOSE_S = 0.5                   # how long a quit waits for this Mac's own copy

_OUTPUT = re.compile(r"output\.([1-9][0-9]*)")

Rows = dict[str, dict]


def row(target: str = NOTHING, *, fullscreen: bool = False, flip_x: bool = False,
        flip_y: bool = False, at: float = 0.0) -> dict:
    return {"target": target, "fullscreen": fullscreen, "flip_x": flip_x, "flip_y": flip_y, "at": at}


def output_of(target) -> int | None:
    """N of `output.N`, as far as there are outputs; None for anything else."""
    m = _OUTPUT.fullmatch(target) if isinstance(target, str) else None
    return int(m.group(1)) if m and int(m.group(1)) <= MAX_OUTPUTS else None


def _at(entry: dict) -> float:
    at = config.number(entry.get("at"))
    return 0.0 if at is None else at


def find(rows: Rows, tag: str) -> dict | None:
    """The row of the display labelled `tag`. A pair's first and a lone one are the same
    memory: with one "TV" on the desk, and then two, the row carries on as "TV #1"."""
    if tag in rows:
        return rows[tag]
    base, hash_, n = tag.rpartition(" #")
    if hash_ and n == "1":
        return rows.get(base)
    return rows.get(f"{tag} #1")


def read_row(entry: dict | None) -> dict:
    """A row as it may be used, whatever the file held."""
    e = entry if isinstance(entry, dict) else {}
    target = e.get("target")
    return {"target": target if isinstance(target, str) else NOTHING,
            **{k: e.get(k) is True for k in TICKS}, "at": _at(e)}


# ---------------------------------------------------------------- what should be open

@dataclass(frozen=True)
class Opening:
    """One display's window: `display` its label, `index` in the connected list."""

    display: str
    index: int
    fullscreen: bool = False
    flip_x: bool = False
    flip_y: bool = False


@dataclass
class Wanted:
    """What should be open. `renders`: each output's displays across the desk; `control`:
    the control window's, None for no row of its own; `away`: outputs with a row on a display
    that isn't connected; `notes`: what the rows asked that can't be; `shown`: each connected
    label's target, as it takes effect."""

    renders: dict[int, list[Opening]] = field(default_factory=dict)
    control: Opening | None = None
    away: dict[int, list[str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    shown: dict[str, str] = field(default_factory=dict)


def wanted(rows: Rows, scr: list[Screen]) -> Wanted:
    """The rows and the connected list, and what should be open (SC3b's seam)."""
    out = Wanted()
    tags = placement.labels(scr)
    used: set[int] = set()
    for i in placement.arranged(scr):
        tag = tags[i]
        entry = find(rows, tag)
        if entry is None:
            out.shown[tag] = NOTHING
            continue
        used.add(id(entry))
        r = read_row(entry)
        target, n = r["target"], output_of(r["target"])
        here = Opening(tag, i, r["fullscreen"], r["flip_x"], r["flip_y"])
        if target == CONTROL:
            if out.control is None:
                out.control = here
            else:
                out.notes.append(f"displays: {tag} and {out.control.display} both say the control window, "
                                 f"which goes to one: it opens on {out.control.display}")
                target = NOTHING
        elif n is not None:
            out.renders.setdefault(n, []).append(here)
        elif target != NOTHING:
            out.notes.append(f"displays: {tag} says {target!r}, which isn't an output here: nothing on it")
            target = NOTHING
        out.shown[tag] = target
    for tag, entry in rows.items():
        n = output_of(read_row(entry)["target"])
        if n is not None and id(entry) not in used:
            out.away.setdefault(n, []).append(tag)
    return out


def pending(rows: Rows, scr: list[Screen], opened: dict[str, str]) -> list[tuple[str, str]]:
    """(label, target) for each connected display that a launch would open differently from
    what's open, across the desk."""
    now = wanted(rows, scr).shown
    return [(tag, target) for tag, target in now.items() if opened.get(tag, NOTHING) != target]


# ---------------------------------------------------------------- the seed

def seed_rows(cfg: dict, scr: list[Screen], seen: dict, notes: list[str],
              render_size: tuple[int, int] = (1280, 820),
              control_size: tuple[int, int] = (960, 900)) -> Rows:
    """The rows `cfg`'s `[output]` says, once: where each window would have opened, by
    `placement`, as that display's row. An output asking for a display another has gets
    none, and a note. `seen`: `placement.load`'s. The sizes are the windows' defaults."""
    if not scr:
        return {}
    tags = placement.labels(scr)
    oc = cfg.get("output", {}) if isinstance(cfg, dict) else {}
    oc = oc if isinstance(oc, dict) else {}
    out: Rows = {}

    def where(monitor, key: str, remembered, kind: str, size) -> str | None:
        """The label `monitor` asks for, by name even if that display is away; None for an
        index no display has."""
        name = placement.named(monitor)
        if name:
            i, said = placement.resolve(name, scr)
            if said:
                notes.append(f"config: {key} = {name!r} {said}")
            return tags[i] if i >= 0 else name
        wish, _ = placement.read(key, monitor)
        if wish >= len(scr):
            notes.append(f"config: {key} = {wish}, but {len(scr)} connected: no display remembers it")
            return None
        rect, _ = placement.place(kind, size, scr, wish, remembered)
        return tags[scr.index(placement.on_screen(rect, scr) or scr[0])]

    for k, e in enumerate(config.screens(cfg)):
        n = k + 1
        if not e.get("window", True) and k:
            continue                # publish-only: it asks for no display
        tag = where(e.get("monitor", -1), f"output {n} monitor", placement.spot(seen, "", n),
                    "render", render_size)
        if tag is None:
            continue
        if tag in out:
            notes.append(f"displays: output {n} and {out[tag]['target']} both ask for {tag}, and a "
                         f"display has one target: output {n} has none, so choose it one")
            continue
        out[tag] = row(f"output.{n}", fullscreen=bool(e.get("fullscreen")),
                       flip_x=e.get("flip_x") is True, flip_y=e.get("flip_y") is True)
    tag = where(oc.get("control_monitor", -1), "[output] control_monitor", seen.get("control"),
                "control", control_size)
    if tag is not None and tag not in out:
        out[tag] = row(CONTROL)
    return out


def _config_says(cfg: dict) -> list[str]:
    """What config.toml says of this that it no longer decides."""
    oc = cfg.get("output", {}) if isinstance(cfg, dict) else {}
    oc = oc if isinstance(oc, dict) else {}
    says = [k for k in ("monitor", "control_monitor") if oc.get(k, -1) != -1]
    says += ["fullscreen"] if oc.get("fullscreen") else []
    says += ["[[output.screens]]"] if isinstance(oc.get("screens"), list) else []
    return says


# ---------------------------------------------------------------- the worker's half

def _parse(data: bytes) -> Rows:
    """The rows in a file. Whatever is in it, a ValueError at the worst."""
    try:
        doc = json.loads(data.decode("utf-8"))
    except RecursionError as e:
        raise ValueError("nested too deep") from e
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"schema {doc.get('schema')!r}" if isinstance(doc, dict) else "not a table")
    raw = doc.get("displays")
    if not isinstance(raw, dict) or not all(isinstance(e, dict) for e in raw.values()):
        raise ValueError("displays is not a table of tables")
    return raw


def _text(rows: Rows, **more) -> str:
    return json.dumps({"schema": SCHEMA, "displays": rows, **more}, indent=2, sort_keys=True,
                      default=str) + "\n"


def merged(doc: Rows, mine: Rows) -> Rows:
    """The later of each row; the file's on a tie."""
    out = {tag: dict(e) for tag, e in doc.items()}
    for tag, e in mine.items():
        if tag not in out or _at(e) > _at(out[tag]):
            out[tag] = dict(e)
    return out


def _read(path: Path, root: Path) -> tuple[Rows | None, str, str]:
    """(the rows or None, the state, why)."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None, sharedfile.ABSENT if root.is_dir() else sharedfile.GONE, ""
    except OSError as e:
        return None, sharedfile.BAD if root.is_dir() else sharedfile.GONE, str(e)
    try:
        return _parse(data), sharedfile.OK, ""
    except (ValueError, TypeError) as e:     # (UnicodeDecodeError is a ValueError)
        return None, sharedfile.BAD, str(e)[:120]


@dataclass
class _Seen:
    """What a cycle found."""

    state: str
    why: str = ""
    stat: tuple = ()
    rows: Rows | None = None
    wrote: bool = False
    write_error: str = ""


def _cycle(path: Path, root: Path, mine: Rows, seen: tuple, force: bool, tmp_name: str) -> _Seen:
    """One look at the shared file: a stat; if it moved, or something must be written, a read,
    a merge and, only if the file doesn't say it, a write. On the worker. Whatever the disk
    does and whatever the file holds, a `_Seen`."""
    try:
        stat = sharedfile.stat(path, root)
        if stat == seen and not force:
            return _Seen(sharedfile.SAME, stat=stat)
        doc, state, why = _read(path, root)
        if doc is None and state != sharedfile.ABSENT:
            return _Seen(state, why=why, stat=sharedfile.stat(path, root))
        rows = merged(doc or {}, mine)
        out = _Seen(state, rows=rows)
        if rows == (doc or {}):
            out.wrote = True        # (nothing to say yet makes no file)
        else:
            try:
                sharedfile.put(path, _text(rows), tmp_name)
                out.wrote = True
            except OSError as e:
                out.write_error = str(e)[:120]
        out.stat = sharedfile.stat(path, root)
        return out
    except Exception as e:  # noqa: BLE001 — nothing a disk does reaches the app
        return _Seen(sharedfile.BAD, why=f"{type(e).__name__}: {e}"[:120])


# ---------------------------------------------------------------- the rows

class DisplayList:
    """The rows, on this Mac. `root` the library, `home` this Mac's folder (None: tests, no
    copy). `said` is what the panel shows, "" when all's well. `seed` is what this Mac's
    config.toml says, spent once; `hold_seed`: this launch could not read it, and `seed` is
    only a default to run on."""

    def __init__(self, root: Path, home: Path | None = None, *, seed: Rows | None = None,
                 hold_seed: bool = False, notes: list[str] | None = None,
                 config_says: list[str] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 wall: Callable[[], float] = time.time):
        self.root = Path(root)
        self.path = self.root / FILE
        base = Path(home) if home is not None else self.root
        self.copy = base / COPY if home is not None and base != self.root else None
        self.notes = notes if notes is not None else []
        self.clock, self.wall = clock, wall
        self.rows: Rows = {}
        self.fallback: Rows = {}        # a default nobody chose: run on, never written
        self.seeded = False
        self.held = ""                  # what stands all run: the seed not read
        self._said = ""
        self._force = False
        self._copy_text: str | None = None
        self._seen: tuple = ()
        self._from = "this Mac's config.toml"
        self._tmp = f"{FILE}.{os.getpid()}.{id(self):x}.tmp"
        self._shared = Worker("display rows: library")
        self._local = Worker("display rows: this Mac")
        self._done: deque[_Seen] = deque()
        self._asked = False
        self._asked_at = 0.0
        self._next = float("-inf")
        self._delay = RETRY_S
        self._open(seed or {}, hold_seed, config_says or [])

    @classmethod
    def open(cls, cfg: dict, home: Path, scr: list[Screen],
             sizes: tuple[tuple[int, int], tuple[int, int]] = ((1280, 820), (960, 900))) -> DisplayList:
        """This launch's rows. Called before the windows and before a `Library`: it reads the
        configured path itself, and waits for that `LAUNCH_S` at the most."""
        lp = cfg.get("library", {}).get("path", "")
        notes = cfg.setdefault("notes", [])
        hold = bool(cfg.get("error"))
        seed = seed_rows(cfg, scr, placement.load(home), [] if hold else notes, *sizes)
        return cls(Path(lp) if lp else home, home, seed=seed, hold_seed=hold, notes=notes,
                   config_says=_config_says(cfg))

    @property
    def said(self) -> str:
        return self._said or self.held

    @property
    def current(self) -> Rows:
        """What to act on: the rows, or with none at all, a launch's default."""
        return self.rows or self.fallback

    # ---- the launch ----

    def _read_copy(self) -> None:
        if self.copy is None:
            return
        try:
            doc = json.loads(self.copy.read_bytes().decode("utf-8"))
            raw = doc.get("displays") if isinstance(doc, dict) and doc.get("schema") == SCHEMA else None
            if not isinstance(raw, dict):
                raise TypeError("not rows")
        except FileNotFoundError:
            return
        except (OSError, ValueError, TypeError, RecursionError) as e:
            self._note(f"displays: {COPY} could not be read ({e}): not used")
            return
        self.rows = {str(t): e for t, e in raw.items() if isinstance(e, dict)}
        self.seeded = doc.get("seeded") is True
        self._from = "this Mac's last rows"

    def _open(self, seed: Rows, hold: bool, config_says: list[str]) -> None:
        self._read_copy()
        if hold:
            self.held = ("config.toml didn't read, so the displays it names weren't either: fix it "
                         "and relaunch. A display you choose here is kept.")
            self._note(f"displays: {self.held}")
            self.fallback = {t: dict(e) for t, e in seed.items()}
        elif not self.seeded:
            # this Mac's one read of its config.toml: what's in the file stands
            self.seeded = True
            self.rows = merged(seed, self.rows)
            self._force = True
        elif config_says:
            self._note(f"displays: config.toml's {', '.join(config_says)} isn't read: {FILE} in the "
                       "library says, and it's set on the output section")
        self._give()
        if self._shared.wait(LAUNCH_S):
            self._take()
        else:
            self._say(f"The shared library isn't answering: displays from {self._from}.")
        self._keep_copy()

    # ---- keeping up ----

    def _give(self) -> None:
        """A cycle, on the worker. At most one is out."""
        force = bool(self._force or self._said)
        mine = {t: dict(e) for t, e in self.rows.items()}
        self._asked, self._asked_at = True, self.clock()
        self._force = False
        path, root, seen, tmp = self.path, self.root, self._seen, self._tmp
        self._shared.give(lambda: self._done.append(_cycle(path, root, mine, seen, force, tmp)))

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
        if r.state == sharedfile.SAME:
            self._next, self._delay = now + LOOK_S, RETRY_S
            return
        if r.rows is None:
            self._force = True
            self._say((f"The shared library isn't there: displays from {self._from}. A change is kept "
                       "on this Mac until it's back.") if r.state == sharedfile.GONE else
                      f"{FILE} could not be read ({r.why}): displays as they were, and nothing is "
                      "written over it.")
            self._keep_copy()
            self._backoff(now)
            return
        self.rows = merged(r.rows, self.rows)     # (and what was chosen since this cycle went)
        self._force = self._force or self.rows != r.rows
        if r.state == sharedfile.ABSENT and r.wrote and r.rows:
            self._note(f"displays: {self.path} made from {self._from}: from now on it says which "
                       "display shows what, on both Macs")
        if r.wrote:
            if self._said:
                self._note(f"displays: {FILE} is back")
            self._said, self._from = "", "this Mac's last rows"
            self._next, self._delay = now + LOOK_S, RETRY_S
        else:
            self._force = True
            self._say(f"{FILE} not written ({r.write_error}): kept on this Mac, and tried again.")
            self._backoff(now)
        self._keep_copy()

    def _keep_copy(self) -> None:
        if self.copy is None:
            return
        text = _text(self.rows, seeded=self.seeded)
        if text != self._copy_text:
            self._copy_text = text
            self._local.give(lambda path=self.copy, text=text: self._put_local(path, text))

    def _put_local(self, path: Path, text: str) -> None:
        try:
            sharedfile.put(path, text)
        except OSError as e:
            self._note(f"displays: {path.name} not written: {e}")

    def look(self) -> None:
        """Each frame, and it reads memory: what the worker found, and it gives the worker its
        next cycle when one is due."""
        self._take()
        now = self.clock()
        if self._asked:
            if now - self._asked_at >= STALL_S:
                self._say("The shared library isn't answering: displays as they are, and a change "
                          "is kept on this Mac until it does.")
        elif now >= self._next:
            self._give()

    def sync(self, timeout: float | None = 10.0) -> None:
        """Wait for a whole cycle, for what isn't the frame: the tests, and tools."""
        self._shared.wait(timeout)
        self._take()
        self._give()
        self._shared.wait(timeout)
        self._take()
        self._local.wait(timeout)

    def close(self) -> None:
        """A quit, or ⌘R: this Mac's copy gets a moment, and carries a change the shared file
        hasn't had yet into the next launch. A stalled Drive holds up nothing."""
        self._take()
        self._keep_copy()
        self._local.wait(CLOSE_S)

    # ---- choosing ----

    def set(self, tag: str, **changes: Any) -> None:
        """A row's fields, chosen now. Memory only: the worker writes it. Always later than
        the row it replaces, whatever this Mac's clock says."""
        old = read_row(find(self.current, tag))
        at = round(max(self.wall(), old["at"] + 0.001), 3)
        self.rows[tag] = {**old, **changes, "at": at}
        self._force = True
        self._next = float("-inf")          # (the next look gives it, if one is out now)
        self._keep_copy()

    def set_target(self, tag: str, target: str, connected: list[str]) -> None:
        """`target` on the display `tag`. The control window goes to one, so another of this
        Mac's displays that has it gives it up. A display away keeps its memory: it may be the
        other Mac's."""
        if target == CONTROL:
            for other in connected:
                if other != tag and read_row(find(self.current, other))["target"] == CONTROL:
                    self.set(other, target=NOTHING)
        self.set(tag, target=target)

    # ---- saying ----

    def _note(self, note: str) -> None:
        self.notes.append(note[:200])

    def _say(self, words: str) -> None:
        if words != self._said:
            self._said = words
            self._note(f"displays: {words}")


# ---------------------------------------------------------------- the running app's side

@dataclass
class Running:
    """What the panel's rows act on: the rows, the connected list (`screens`, a call), the
    slots, and `opened`, each display's target as this run opened them."""

    store: DisplayList
    screens: Callable[[], list[Screen]]
    slots: list
    opened: dict[str, str] = field(default_factory=dict)

    def window_on(self, tag: str) -> tuple[Any, Any] | None:
        """(slot, its `Also` or None for its first display) of the window open on `tag`."""
        for sl in self.slots:
            if sl.opened and sl.display == tag:
                return sl, None
            for also in sl.also:
                if also.display == tag:
                    return sl, also
        return None


def opened_of(slots: list, control: Opening | None) -> dict[str, str]:
    """Each display's target, as these slots have them."""
    out = {sl.display: f"output.{sl.n}" for sl in slots if sl.opened and sl.display}
    out.update({a.display: f"output.{sl.n}" for sl in slots for a in sl.also})
    if control is not None:
        out[control.display] = CONTROL
    return out
