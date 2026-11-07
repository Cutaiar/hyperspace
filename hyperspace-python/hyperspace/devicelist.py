"""The device list both Macs share (wave 5 CT1): `<library>/devices.json`.

The meta controller's: what controllers there are, each with the role that rows name.
No loadable patch reaches this file, and nothing here reaches a patch. Who holds which
controller stays on each Mac (`players.json`). A root file is safe in the library:
`Library.groups` and `tools/migrate_library.py` walk folders only, and this is kept out
of `library.py` on purpose.

**A new controller waits.** Plugging one in adopts nothing: the player board's tray shows
it (`ui_players.loose`), and dragging it to a player calls `adopt`.

**A role never renumbers.** Roles are row addresses, so:

- A role, once in the list, is never rewritten, and a new entry goes at the end, so no
  controller's place among its kind (which names its rows) moves.
- A new role comes from what the controller *is*, never from when it arrived: an APC40 is
  ``apc40``, a pad is its model's id, any other MIDI port the slug of its name. Both Macs
  get the same name for the same controller, in any order.
- The second of the same is ``xbox-2``. A pad entry takes any pad of its model
  (`pads.models.matches`), and two of one model are alike to a row, so these are seats,
  not units, and it doesn't matter which was plugged in first.

**What's in charge.** `[[devices]]` in config.toml is a seed, read once per Mac: the Mac
that finds no list writes one from it; a Mac that finds a list adds what its own
`[[devices]]` names and the list lacks, the first time, and the shared entry stands where a
role is in both. From then on the file is not read for the list; a note says so. RT1
retires it. With no `[[devices]]`, the old tables are the seed (`DEFAULTS` is that seed for
a file that says nothing, and what CL3 needs when `config._translate` goes), and a table's
`enabled = false` stays this Mac's (`off`), as it isn't the other Mac's to say.

**The library not there.** The Drive may be unmounted at launch: the show still starts, on
`<home>/devices.last.json`, the list as this Mac last saw it, else this Mac's seed. `said`
says so on the board and a note on the SYSTEM page. Nothing is created in a folder that
isn't there. An adopt then stands for this run and waits in that copy (`unwritten`), and
reaches the shared file when it's back, with no restart. The copy existing is also how a
Mac knows it has read its seed.

**The other Mac.** Drive moves the file's mtime and can land an older copy over ours, so
every write is read, merge, write, and an adopt is held for `HOLD_S` after its write: if a
file arrives without it, it is written back in. Both Macs converge on the union, and
neither writes when the file already says it, so they don't take turns. A list that
can't be read (half synced, a newer build's) is never written over: the old list stands, the
devices keep running, and it is read again. A role adopted on both Macs as two different
controllers keeps the file's, and ours takes the next free name.

Main thread only. A stat of the file twice a second, as the library's own scan of the same
folder; a read only when it moved.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import apc40, config
from .pads.models import Model
from .players import NAMES

FILE = "devices.json"
COPY = "devices.last.json"      # in the home, beside players.json
SCHEMA = "devices/1"
HOLD_S = 600.0                  # how long a written adopt is put back if a file lacks it
# nothing listed and nothing in config.toml: the devices that are there with no config
DEFAULTS: tuple[dict, ...] = (
    {"role": "pad", "kind": "gamepad"},
    {"role": "apc40", "kind": "midi"},
    {"role": "leap", "kind": "hands", "enabled": False},
    {"role": "bridge", "kind": "bridge", "enabled": False},
)

_OK, _ABSENT, _GONE, _BAD = "ok", "absent", "gone", "bad"


def _gone_words(what: str) -> str:
    return (f"The shared library isn't there: controllers from {what}. A new one is kept on "
            "this Mac until it's back.")


# ---------------------------------------------------------------- what a controller is called

def slug(name: str) -> str:
    """`name` as a role: lower case, a dash for anything else. No ':' (a role can't
    hold one) and no '@' (rows use it to name a role)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "controller"


def midi_entry(port: str) -> dict:
    """The entry for a MIDI port the Mac sees."""
    if apc40.PORT_MATCH.lower() in port.lower():
        return {"role": "apc40", "kind": "midi", "profile": "apc40"}
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


def _same(a: dict, b: dict) -> bool:
    """The same controller, whatever each is called? What it answers to."""
    if a.get("kind") != b.get("kind"):
        return False
    if a.get("kind") == "midi":
        return (a.get("profile") or "apc40", a.get("port")) == (b.get("profile") or "apc40", b.get("port"))
    if a.get("kind") == "gamepad":
        return a.get("controller", "any") == b.get("controller", "any")
    return {k: v for k, v in a.items() if k != "role"} == {k: v for k, v in b.items() if k != "role"}


# ---------------------------------------------------------------- the file

def _parse(text: str) -> list[dict]:
    doc = json.loads(text)
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"schema {doc.get('schema')!r}" if isinstance(doc, dict) else "not a table")
    raw = doc.get("devices")
    if not isinstance(raw, list) or not all(isinstance(e, dict) for e in raw):
        raise ValueError("devices is not a list of tables")
    return raw


def _text(raw: list[dict], **more) -> str:
    return json.dumps({"schema": SCHEMA, "devices": raw, **more}, indent=2, default=str) + "\n"


@dataclass
class _Waiting:
    """An entry the shared file may not say yet."""

    entry: dict
    until: float | None = None      # None: not written
    adopted: bool = True            # a seed's gives way to the file; an adopt takes a free name


class DeviceList:
    """The list, on this Mac. `raw` is as the file holds it; `checked` is what the
    registry opens. `root` the library, `home` this Mac's folder (None: tests, no copy).
    `said` is what the board shows, "" when all's well."""

    def __init__(self, root: Path, home: Path | None = None, *, seed=DEFAULTS, listed: bool = False,
                 off=(), no_midi_look: bool = False, notes: list[str] | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self.root = Path(root)
        self.path = self.root / FILE
        self.base = Path(home) if home is not None else self.root
        self.copy = self.base / COPY if home is not None and self.base != self.root else None
        self.off = tuple(off)
        self.no_midi_look = no_midi_look
        self.notes = notes if notes is not None else []
        self.clock = clock
        self.said = ""
        self.raw: list[dict] = []
        self.waiting: dict[str, _Waiting] = {}
        self._unread = False
        self._copy_text: str | None = None
        self._seen: tuple = ()
        self._from = ""
        self._open([dict(e) for e in seed], listed)

    @classmethod
    def open(cls, cfg: dict, home: Path) -> DeviceList:
        """This launch's list, and `cfg`'s device list taken from it. Called before the
        windows and before a `Library`: it reads the configured path itself."""
        lp = cfg.get("library", {}).get("path", "")
        notes = cfg.setdefault("notes", [])
        out = cls(Path(lp) if lp else home, home, seed=cfg.get("device_seed", DEFAULTS),
                  listed=bool(cfg.get("device_seed_listed")), off=cfg.get("devices_off", ()),
                  no_midi_look=bool(cfg.get("no_midi_look")), notes=notes)
        entries, problems, said = out.checked()
        notes += [*problems, *said]
        config.take_devices(cfg, entries)
        return out

    def checked(self) -> tuple[list[dict], list[str], list[str]]:
        """(entries, problems, notes): `config.listed_devices` over the list."""
        return config.listed_devices(self.raw, self.base, self.off)

    # ---- asking the disk ----

    def _stat(self) -> tuple:
        try:
            st = self.path.stat()
        except OSError:
            return (_ABSENT if self.root.is_dir() else _GONE,)
        return st.st_mtime_ns, st.st_size

    def _read(self) -> tuple[list[dict] | None, str, str]:
        """(the list or None, `_OK` / `_ABSENT` / `_GONE` / `_BAD`, why)."""
        try:
            text = self.path.read_text()
        except FileNotFoundError:
            return None, _ABSENT if self.root.is_dir() else _GONE, ""
        except OSError as e:
            return None, _BAD if self.root.is_dir() else _GONE, str(e)
        try:
            return _parse(text), _OK, ""
        except (ValueError, TypeError) as e:
            return None, _BAD, str(e)

    def _read_copy(self) -> tuple[list[dict], list[dict]] | None:
        if self.copy is None:
            return None
        try:
            text = self.copy.read_text()
            doc = json.loads(text)
            raw = _parse(text)
            return raw, [e for e in doc.get("unwritten", ()) if isinstance(e, dict)]
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, AttributeError) as e:
            self._note(f"devices: {COPY} could not be read ({e}): not used")
            return None

    # ---- the launch ----

    def _open(self, seed: list[dict], listed: bool) -> None:
        last = self._read_copy()
        doc, state, _why = self._read()
        self._from = "this Mac's last list" if last is not None else "this Mac's config.toml"
        for e in last[1] if last is not None else ():
            if "role" in e:
                self.waiting[str(e["role"])] = _Waiting(e)
        self.raw = [dict(e) for e in (doc if doc is not None else last[0] if last is not None else seed)]
        first_sight = self.copy is not None and last is None
        if state == _ABSENT:
            # nothing here yet: written now. The other Mac's may land on it, so held
            for e in self.raw:
                self.waiting.setdefault(str(e.get("role", "")), _Waiting(e, adopted=False))
            self._note(f"devices: {self.path} made from {self._from}: from now on it says "
                       "what controllers there are, on both Macs")
        elif listed and first_sight:
            # this Mac's one read of its [[devices]], as soon as the file is there to read
            have = {str(e.get("role", "")): e for e in doc or ()}
            for e in seed:
                if str(e.get("role", "")) not in have:
                    self.waiting[str(e.get("role", ""))] = _Waiting(e, adopted=False)
            kept = [r for r, e in have.items() if any(s.get("role") == r and s != e for s in seed)]
            if kept:
                self._note(f"devices: config.toml says otherwise of {', '.join(kept)}: "
                           f"{FILE} in the library stands")
        elif listed and state == _OK:
            self._note(f"devices: config.toml's [[devices]] is not read: {FILE} in the "
                       "library says, and it's set from the player board")
        self._flush()

    # ---- keeping up ----

    def _union(self, doc: list[dict]) -> list[dict]:
        """`doc` and what waits. The file's stands on a role in both; an adopt of a
        different controller under a role the file gave away takes a free name."""
        out = [dict(e) for e in doc]
        for role, w in list(self.waiting.items()):
            have = next((e for e in out if str(e.get("role", "")) == role), None)
            if have is None:
                out.append(dict(w.entry))
            elif w.adopted and have != w.entry and not _same(have, w.entry):
                new = free_role(w.entry, out)
                del self.waiting[role]
                moved = {**w.entry, "role": new}
                self.waiting[new] = _Waiting(moved)
                out.append(dict(moved))
                self._note(f"devices: the other Mac named another controller {role}: "
                           f"this one is {new}")
        return out

    def _flush(self) -> bool:
        """Read, merge, write if the file doesn't say it. True when the list changed."""
        doc, state, why = self._read()
        self._unread = state == _BAD
        if state == _GONE:
            self._say(_gone_words(self._from))
            self._keep_copy()
            self._seen = self._stat()
            return False
        if state == _BAD:
            self._say(f"{FILE} could not be read ({why}): controllers as they were, "
                      "and nothing is written over it.")
            self._seen = self._stat()
            return False
        merged = self._union(doc if doc is not None else self.raw)
        changed = merged != self.raw
        self.raw = merged
        wrote = merged == doc or self._write(merged)
        if wrote:
            if self.said:
                self._note(f"devices: {FILE} is back")
            self.said, self._from = "", "this Mac's last list"
            until = self.clock() + HOLD_S
            for w in self.waiting.values():
                if w.until is None:
                    w.until = until
        self._keep_copy()
        self._seen = self._stat()
        return changed

    def _write(self, raw: list[dict]) -> bool:
        tmp = self.path.with_name(f"{FILE}.{os.getpid()}.tmp")
        try:
            tmp.write_text(_text(raw))
            tmp.replace(self.path)
            return True
        except OSError as e:
            self._say(f"{FILE} not written ({e}): kept on this Mac, and tried again.")
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _keep_copy(self) -> None:
        if self.copy is None:
            return
        unwritten = [w.entry for w in self.waiting.values() if w.until is None]
        text = _text(self.raw, unwritten=unwritten)
        if text == self._copy_text:
            return
        tmp = self.copy.with_name(self.copy.name + ".tmp")
        try:
            tmp.write_text(text)
            tmp.replace(self.copy)
            self._copy_text = text
        except OSError as e:
            self._note(f"devices: {COPY} not written: {e}")

    def look(self) -> bool:
        """Has the list changed? Called every `devices.WATCH_FRAMES`, and cheap: a stat
        unless the file moved, or something is still to be written."""
        now = self.clock()
        for role, w in list(self.waiting.items()):
            if w.until is not None and now >= w.until:
                del self.waiting[role]
        stat = self._stat()
        unwritten = any(w.until is None for w in self.waiting.values())
        if stat == self._seen and not self._unread and not unwritten:
            return False
        return self._flush()

    # ---- adopting ----

    def adopt(self, entry: dict) -> str:
        """The controller of `entry` (`midi_entry`, `pad_entry`) into the list, at its
        end; its role. A MIDI port already listed, adopted a moment ago on the other Mac,
        keeps that entry. The caller applies the list."""
        self._flush()               # what the file says now, so a name isn't taken twice
        if entry.get("kind") == "midi":
            same = next((e for e in self.raw if _same(e, entry)), None)
            if same is not None:
                return str(same["role"])
        role = free_role(entry, self.raw)
        made = {**entry, "role": role}
        self.raw = [*self.raw, made]
        self.waiting[role] = _Waiting(made)
        self._flush()
        return role

    def role_for(self, entry: dict) -> str:
        """What adopting `entry` now would call it (the tray's tooltip)."""
        if entry.get("kind") == "midi":
            same = next((e for e in self.raw if _same(e, entry)), None)
            if same is not None:
                return str(same["role"])
        return free_role(entry, self.raw)

    # ---- saying ----

    def _note(self, note: str) -> None:
        self.notes.append(note[:200])

    def _say(self, words: str) -> None:
        if words != self.said:
            self.said = words
            self._note(f"devices: {words}")
