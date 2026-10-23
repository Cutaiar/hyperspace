"""The eight media channels (plan 32 C, rows 321–326): `a`–`h`, each a bin
of up to sixteen source ids with one of them on the channel (`slot`), and
a transport for a timed source.

`MediaState` is the one object the rest reads: the registry's `media.*`
params write its channels' fields (params.py), the preset's `media`
section is its bins (`to_json` / `from_json`), the renderer reads
`frame(c)` and `channels[c].fit`, the MEDIA page `status`, `playhead` and
`missing`. `poll` runs once a frame on the frame thread, right after the
devices (the scene-setter slot, app.frame): it opens and closes sources as
slots change and steps the transports. Opening a source starts its own
thread or a pool job, never a decode here. Closing one joins its thread,
which can take as long as the file it is stuck reading (a cloud file still
downloading holds `av.open`), so a dropped source goes to the `Closer`, a
thread of its own (``media-closer``), and the frame thread only queues it.
Once dropped a source is never read again, so a late decode finishing on a
closed source (still.py) reaches nothing.

A file the resolver could not find is a `MissingSource` (black,
`missing`). Every `RECHECK_S` the channel asks the resolver again: a file
that has arrived opens, one that has gone goes black, and one replaced on
disk (the resolver's optional `stamp(sid)` moved) opens afresh. The
resolver answers from the folder's last scan, so none of this touches the
disk on the frame thread."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Any

from . import adapters, ids
from .adapters import MissingSource
from .frame import MediaFrame
from .source import MISSING, Source, error
from .transport import LOOPS, Transport

CHANNELS = "abcdefgh"
BIN = 16
FITS = ("cover", "contain", "stretch")
EMPTY = "empty"          # a bin entry with nothing in it: black
RECHECK_S = 1.0          # how often a channel asks the resolver about its id again
STILL_KINDS = ("still", "missing")   # untimed and not live: rate means nothing
CLOSE_BUDGET_S = 1.5     # app exit: how long `MediaState.close` waits for the closes
CLOSER_IDLE_S = 2.0      # the closer thread ends after this long with nothing to close


class Closer:
    """Closes dropped sources on one daemon thread (``media-closer``), in
    the order they were dropped, so a close that waits on a stuck read
    never holds the frame thread. Not the media pool: a hung close would
    sit on one of its three workers. The thread starts with the first
    close and ends after `CLOSER_IDLE_S` with none. `done` counts the
    closes finished (raising or not), `pending` the ones queued or running."""

    def __init__(self):
        self._q: queue.SimpleQueue = queue.SimpleQueue()
        self._cv = threading.Condition()
        self._thread: threading.Thread | None = None
        self.pending = 0
        self.done = 0

    def put(self, src) -> None:
        """Queue `src` to be closed; returns at once."""
        with self._cv:
            self.pending += 1
            t = self._thread
            if t is None or not t.is_alive():
                t = self._thread = threading.Thread(target=self._run, name="media-closer",
                                                    daemon=True)
                t.start()
        self._q.put(src)

    def _run(self) -> None:
        while True:
            try:
                src = self._q.get(timeout=CLOSER_IDLE_S)
            except queue.Empty:
                with self._cv:            # decided under the lock `put` takes
                    if self.pending == 0:
                        self._thread = None
                        return
                continue
            try:
                src.close()
            except Exception:  # noqa: BLE001, S110 — a source that will not close is dropped anyway
                pass
            with self._cv:
                self.pending -= 1
                self.done += 1
                self._cv.notify_all()

    def drain(self, timeout: float) -> bool:
        """Wait up to `timeout` s for every queued close; True when none is left."""
        with self._cv:
            return self._cv.wait_for(lambda: self.pending == 0, timeout)


@dataclass
class Channel:
    name: str
    bin: list[str | None] = field(default_factory=lambda: [None] * BIN)
    slot: float = 0.0
    fit: int = 0
    rate: float = 1.0
    pos: float = 0.0
    jog: float = 0.0
    loop: int = 0
    # runtime, never saved
    source: Source | None = field(default=None, repr=False, compare=False)
    transport: Transport | None = field(default=None, repr=False, compare=False)
    sid: str | None = field(default=None, repr=False, compare=False)   # what `source` is for
    stamp: Any = field(default=None, repr=False, compare=False)
    checked: float = field(default=0.0, repr=False, compare=False)
    frozen: bool = field(default=False, repr=False, compare=False)
    held: MediaFrame | None = field(default=None, repr=False, compare=False)

    def index(self) -> int:
        return min(max(round(self.slot), 0), BIN - 1)


class NoResolver:
    """Nothing on this Mac: the stand-in when no app builds a resolver."""

    proxy_cache = None

    def path(self, sid):
        return None

    def live(self, sid):
        return None


def read_bins(doc) -> tuple[dict[str, list[str | None]], list[str]]:
    """The preset's `media` section as {channel: bin of BIN}, and a note for
    each thing dropped: an unknown channel, a bin that is not a list, an
    entry that is not a source id, entries past the sixteenth. A missing
    section is every bin empty."""
    bins: dict[str, list[str | None]] = {c: [None] * BIN for c in CHANNELS}
    notes: list[str] = []
    chans = (doc or {}).get("channels") if isinstance(doc, dict) else None
    if chans is None:
        return bins, notes
    if not isinstance(chans, dict):
        return bins, ["media: channels is not a table, ignored"]
    for c, entries in chans.items():
        if c not in bins:
            notes.append(f"media: no channel {c!r}, ignored")
            continue
        if not isinstance(entries, list):
            notes.append(f"media.{c}: the bin is not a list, ignored")
            continue
        if len(entries) > BIN:
            notes.append(f"media.{c}: {len(entries) - BIN} entr"
                         f"{'y' if len(entries) - BIN == 1 else 'ies'} past {BIN} dropped")
        for i, sid in enumerate(entries[:BIN]):
            if sid is None:
                continue
            try:
                ids.parse(sid if isinstance(sid, str) else "")
            except ValueError:
                notes.append(f"media.{c}[{i}]: not a source id {sid!r}, dropped")
                continue
            bins[c][i] = sid
    return bins, notes


class MediaState:
    def __init__(self, resolver=None, opener=adapters.open_source):
        self.resolver = resolver if resolver is not None else NoResolver()
        self.opener = opener
        self.channels: dict[str, Channel] = {c: Channel(c) for c in CHANNELS}
        self._closed = False
        self.closer = Closer()

    def _closer(self) -> Closer:
        """The closer; made here for a MediaState from before it (a hot
        reload re-classes, never re-inits)."""
        c = self.__dict__.get("closer")
        if c is None:
            c = self.closer = Closer()
        return c

    # -- the frame thread ---------------------------------------------------

    def poll(self, dt: float, now: float) -> None:
        """Once a frame: each channel's source follows its slot, a missing or
        replaced file is looked at again, and a timed source's transport is
        stepped and handed to it. Never raises for a source's sake."""
        if getattr(self, "_closed", False):
            return
        for ch in self.channels.values():
            sid = ch.bin[ch.index()]
            if sid != ch.sid:
                self._switch(ch, sid, now)
            elif ch.source is not None and now - ch.checked >= RECHECK_S:
                ch.checked = now
                if self._stale(ch):
                    self._switch(ch, sid, now)
            src = ch.source
            if src is None:
                continue
            try:
                if src.timed:
                    self._step(ch, src, dt)
                elif src.kind not in STILL_KINDS:
                    self._freeze(ch, src)
            except Exception as e:  # noqa: BLE001 — a source must not kill the frame
                src.status = error(f"{type(e).__name__}: {e}")

    def _switch(self, ch: Channel, sid: str | None, now: float) -> None:
        old, ch.source, ch.transport = ch.source, None, None
        ch.frozen, ch.held = False, None
        if old is not None:
            self._closer().put(old)     # never joined here: see the module docstring
        ch.sid, ch.checked, ch.stamp = sid, now, None
        if sid is None:
            return
        try:
            src = self.opener(sid, self.resolver)
            src.open()
        except Exception as e:  # noqa: BLE001 — a bad source is black, never a crash
            src = MissingSource(sid, error(f"{type(e).__name__}: {e}"))
        ch.source = src
        ch.stamp = self._stamp(sid)
        if src.timed:
            ch.transport = Transport(src.duration)
            ch.transport.reset(ch.pos)

    def _stamp(self, sid: str):
        fn = getattr(self.resolver, "stamp", None)
        if fn is None:
            return None
        try:
            return fn(sid)
        except Exception:  # noqa: BLE001
            return None

    def _stale(self, ch: Channel) -> bool:
        """Whether the channel's source no longer matches what the resolver
        says about its id: arrived, gone, or replaced."""
        src, sid = ch.source, ch.sid
        try:
            kind = ids.parse(sid).kind
        except ValueError:
            return False
        r = self.resolver
        missing = isinstance(src, MissingSource) and src.status == MISSING
        if kind in ids.FILE_KINDS:
            here = r.path(sid) is not None
            if missing:
                return here
            if not here:
                return True
            return self._stamp(sid) != ch.stamp
        if kind == "phone":
            return False
        # a live id: arrived, or now another object — its device was closed
        # and made again by a [[devices]] edit, so the held one is dead. A
        # feed that has only gone stays held (`lost`), to be found again
        live = r.live(sid)
        return live is not None and live is not src

    def _step(self, ch: Channel, src, dt: float) -> None:
        tr = ch.transport
        if tr is None:
            tr = ch.transport = Transport(src.duration)
            tr.reset(ch.pos)
        d = max(float(src.duration or 0.0), 0.0)
        if d != tr.duration:          # probed on the source's thread since it opened
            was = tr.duration
            tr.duration = d
            if was <= 0.0:
                tr.playhead = min(max(tr.last_pos, 0.0), 1.0) * d
        loop = LOOPS[min(max(int(ch.loop), 0), len(LOOPS) - 1)]
        src.want(tr.step(dt, ch.rate, ch.pos, ch.jog, loop))

    @staticmethod
    def _freeze(ch: Channel, src) -> None:
        """A live feed at rate 0 holds the frame it showed (row 324)."""
        if ch.rate == 0.0:
            if not ch.frozen:
                ch.frozen, ch.held = True, _read(src)
        elif ch.frozen:
            ch.frozen, ch.held = False, None

    # -- what the renderer and the page read --------------------------------

    def frame(self, c: str) -> MediaFrame | None:
        """The channel's picture now, or None (black). Read on the frame
        thread: a source with `gl_poll` (Syphon) is asked through it."""
        ch = self.channels.get(c)
        if ch is None or ch.source is None:
            return None
        if ch.frozen:
            return ch.held
        try:
            return _read(ch.source)
        except Exception:  # noqa: BLE001
            return None

    def status(self, c: str) -> str:
        ch = self.channels.get(c)
        if ch is None or ch.source is None:
            return EMPTY
        return str(ch.source.status)

    def playhead(self, c: str) -> tuple[float, float] | None:
        """(seconds, duration) for a timed source; None otherwise."""
        ch = self.channels.get(c)
        if ch is None or ch.transport is None:
            return None
        return (ch.transport.playhead, ch.transport.duration)

    def missing(self) -> list[str]:
        """The ids in any bin the resolver cannot find on this Mac, in bin
        order, once each — the MEDIA page's banner. Each is asked of the
        resolver (`_found`): a file by its path, a live feed by `live`,
        which the app's resolver answers None for until plan 32 T8 brings
        the feeds. A `phone:` id is reserved (V2) and never listed."""
        out: list[str] = []
        for ch in self.channels.values():
            for sid in ch.bin:
                if sid is None or sid in out:
                    continue
                if not self._found(sid):
                    out.append(sid)
        return out

    def _found(self, sid: str) -> bool:
        try:
            kind = ids.parse(sid).kind
        except ValueError:
            return True          # never in a bin: read_bins and assign refuse it
        if kind in ids.FILE_KINDS:
            return self.resolver.path(sid) is not None
        if kind == "phone":
            return True
        return self.resolver.live(sid) is not None

    # -- the bins -----------------------------------------------------------

    def assign(self, c: str, i: int, sid: str | None) -> None:
        """Put `sid` (None: empty) in channel `c`'s bin at `i`; the next
        poll opens it if it is the slot on the channel."""
        if sid is not None:
            ids.parse(sid)
        self.channels[c].bin[int(i)] = sid

    def to_json(self) -> dict:
        """The preset's `media` section: each bin holding anything, trailing
        empties trimmed."""
        out: dict[str, list[str | None]] = {}
        for c, ch in self.channels.items():
            b = list(ch.bin)
            while b and b[-1] is None:
                b.pop()
            if b:
                out[c] = b
        return {"channels": out}

    def from_json(self, d: dict | None) -> list[str]:
        """Every bin replaced by the section's (`read_bins`); the notes for
        what was dropped. The next poll opens what the slots now name."""
        bins, notes = read_bins(d)
        self.set_bins(bins)
        return notes

    def set_bins(self, bins: dict[str, list[str | None]]) -> None:
        for c, ch in self.channels.items():
            ch.bin = list(bins.get(c) or [None] * BIN)

    def drain(self, timeout: float = CLOSE_BUDGET_S) -> bool:
        """Wait up to `timeout` s for the dropped sources' closes to finish."""
        return self._closer().drain(timeout)

    def close(self, budget: float = CLOSE_BUDGET_S) -> bool:
        """App exit: every source dropped and closed, waiting at most
        `budget` s for all the closes together, then returning whatever is
        left (the closer is a daemon: a close still stuck dies with the
        process). A poll after this opens nothing. True when all closed."""
        self._closed = True
        for ch in self.channels.values():
            self._switch(ch, None, 0.0)
        return self.drain(budget)


def _read(src) -> MediaFrame | None:
    poll = getattr(src, "gl_poll", None)
    return poll() if poll is not None else src.latest()
