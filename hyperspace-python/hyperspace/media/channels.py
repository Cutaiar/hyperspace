"""The eight media channels (plan 32 C, rows 321–326): `a`–`h`, each a bin
of up to sixteen source ids with one of them on the channel (`slot`), and
a transport for a timed source.

`Channels` (plan 44 D3; `MediaState` is its old name) is the one object a deck reads, over
the rig's `MediaSources` (the resolver, the opener, the closer, the mixer —
shared by every deck: one decode for every reader): the registry's `media.*`
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
`missing`); one still downloading is one too (black, `fetching`: a read
of it would block until it lands). Every `RECHECK_S` the channel asks
the resolver again: a file that has arrived or finished downloading opens, one that has gone goes black, and one replaced on
disk (the resolver's optional `stamp(sid)` moved) opens afresh. The
resolver answers from the folder's last scan, so none of this touches the
disk on the frame thread.

Sound (plan 45 V2): a channel's `play_audio` toggle enables its source's
soundtrack (`VideoSource.audio`) the frame it turns on or a new slot comes
under it, and disables it `OFF_FRAMES` after it turns off — on the
closer, since a disable joins the soundtrack's thread, and never at once
with an enable (`_Sound`); a slot change leaves the old track to its
source's `close`. Each poll ends by handing the mixer
(`media/mixer.py`) the channels heard, with the playhead each transport
was just stepped to, how it is moving, and the channel's `gain`: the
transport is the one clock, and the mixer's read head is its slave (V4)."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from . import adapters, ids, mixer, pool
from .adapters import MissingSource
from .frame import MediaFrame
from .source import FETCHING, MISSING, Source, error
from .transport import LOOPS, Transport

CHANNELS = "abcdefgh"
BIN = 16
FITS = ("cover", "contain", "stretch")
EMPTY = "empty"          # a bin entry with nothing in it: black
FROZEN = "frozen"        # a live feed held at rate 0 (row 324)
RECHECK_S = 1.0          # how often a channel asks the resolver about its id again
STILL_KINDS = ("still", "missing")   # untimed and not live: rate means nothing
CLOSE_BUDGET_S = 1.5     # app exit: how long `MediaState.close` waits for the closes
CLOSER_IDLE_S = 2.0      # the closer thread ends after this long with nothing to close
OFF_FRAMES = 30          # a channel's sound turned off lets its soundtrack go this many frames later


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
    play_audio: bool = False   # plan 45 V2: the source's soundtrack into the mixer
    gain: float = 1.0          # …at this gain (linear; 1 is unity)
    # runtime, never saved
    source: Source | None = field(default=None, repr=False, compare=False)
    transport: Transport | None = field(default=None, repr=False, compare=False)
    sid: str | None = field(default=None, repr=False, compare=False)   # what `source` is for
    stamp: Any = field(default=None, repr=False, compare=False)
    checked: float = field(default=0.0, repr=False, compare=False)
    frozen: bool = field(default=False, repr=False, compare=False)
    held: MediaFrame | None = field(default=None, repr=False, compare=False)
    heard: Any = field(default=None, repr=False, compare=False)   # the Soundtrack enabled for it
    quiet: int = field(default=0, repr=False, compare=False)      # frames its sound has been off

    def index(self) -> int:
        return min(max(round(self.slot), 0), BIN - 1)


class _Sound:
    """Who calls a soundtrack's `enable` and `disable`, so the two never
    run at once on one track (plan 45 V2, review): the frame thread enables
    (`on`, non-blocking), the closer disables (`off` queues a `_Silence`:
    `disable` joins the soundtrack's thread). While a disable is queued or
    running the frame thread only notes that it wants the track again, and
    the closer enables it once its disable is done (`done`), under the
    lock `on` takes — so an enable never lands inside a disable."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pending: dict[int, list] = {}     # id(track) → [track, wanted again]

    def on(self, track) -> None:
        with self._lock:
            p = self._pending.get(id(track))
            if p is not None:
                p[1] = True
                return
            track.enable()

    def off(self, track, closer: Closer) -> None:
        with self._lock:
            p = self._pending.get(id(track))
            if p is not None:
                p[1] = False
                return
            self._pending[id(track)] = [track, False]
        closer.put(_Silence(self, track))

    def forget(self, track) -> None:
        """The track's source is being dropped: a queued disable is not
        followed by an enable."""
        with self._lock:
            p = self._pending.get(id(track))
            if p is not None:
                p[1] = False

    def done(self, track) -> None:
        with self._lock:
            p = self._pending.pop(id(track), None)
            if p is not None and p[1]:
                track.enable()

    def busy(self, track) -> bool:
        with self._lock:
            return id(track) in self._pending


class _Silence:
    """A soundtrack's `disable` as a job for the closer: it joins the
    soundtrack's thread, which can sit in `av.open` on a cloud file, so it
    never runs on the frame thread (plan 45 V2)."""

    def __init__(self, sound: _Sound, track):
        self.sound, self.track = sound, track

    def close(self) -> None:
        try:
            self.track.disable()
        finally:
            self.sound.done(self.track)


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


class MediaSources:
    """What the channels read their pictures and sound through — the rig's,
    one for every deck (plan 44 D3, §2 "the media sources"): the resolver
    (an id → a file or a live feed), the opener, the closer thread a dropped
    source goes to, the soundtracks' bookkeeping and the mixer (plan 45
    V2–V3: `live_mixer`, the analyzer's `mix` source). A decode is one for
    every reader; the channels' state (bins, slots, transports) is a deck's
    (`Channels`)."""

    def __init__(self, resolver=None, opener=adapters.open_source):
        self.resolver = resolver if resolver is not None else NoResolver()
        self.opener = opener
        self.closer = Closer()
        self.mixer = mixer.Mixer()
        self.sound = _Sound()

    def _closer(self) -> Closer:
        """The closer; made here for an object from before it (a hot reload
        re-classes, never re-inits)."""
        c = self.__dict__.get("closer")
        if c is None:
            c = self.closer = Closer()
        return c

    def _mixer(self) -> mixer.Mixer:
        """The mixer (plan 45 V2); made here for an object from before it,
        and re-classed to the module's `Mixer` after a hot reload of
        `media.mixer` (its stream, and the callback reached through the
        class, live on)."""
        m = self.__dict__.get("mixer")
        if m is None:
            m = self.mixer = mixer.Mixer()
        elif (type(m) is not mixer.Mixer and type(m).__qualname__ == "Mixer"
              and type(m).__module__ == mixer.__name__):     # the module's own, reloaded
            m.__class__ = mixer.Mixer
            for k, v in vars(mixer.Mixer()).items():  # fields added since: their defaults
                m.__dict__.setdefault(k, v)
        return m

    def begin_frame(self) -> None:
        """A new frame's reads (plan 44 D4, §8): from here to the next call,
        each source is read once (`read`) whichever deck asks."""
        self.__dict__["_read_now"] = {}

    def read(self, src) -> MediaFrame | None:
        """`src`'s picture this frame: asked once a frame, its `gl_poll` (a
        Syphon feed's, which may have no new frame for a second asker) or
        `latest` — every renderer, on any deck, handed the same `MediaFrame`.
        Before any `begin_frame` (a tool, a test), a fresh read each time."""
        now = self.__dict__.get("_read_now")
        if now is None:
            return _read(src)
        hit = now.get(id(src))
        if hit is None:
            hit = now[id(src)] = (src, _read(src))     # (src held: its id stays its own)
        return hit[1]

    def live_mixer(self) -> mixer.Mixer:
        """The mixer the channels feed — the public door (the analyzer's
        `mix` source, plan 45 V3); `_mixer` is the hot-reload accessor
        behind it."""
        return self._mixer()

    def _sound(self) -> _Sound:
        s = self.__dict__.get("sound")
        if s is None:
            s = self.sound = _Sound()
        return s

    def drain(self, timeout: float = CLOSE_BUDGET_S) -> bool:
        """Wait up to `timeout` s for the dropped sources' closes to finish."""
        return self._closer().drain(timeout)


def _through(name: str) -> property:
    """A deck's channels' view of their sources' `name` (plan 44 D3)."""
    return property(lambda self: getattr(self._sources(), name),
                    lambda self, v: setattr(self._sources(), name, v),
                    doc=f"The media sources' `{name}` (`MediaSources`).")


class Channels:
    """A deck's eight media channels (plan 44 D3): each `Channel`'s bin,
    slot, fit and transport — what the deck's `media.*` params write
    (`params.build_performance`), the preset's `media` section (`to_json`
    / `from_json`), what the deck's renderer reads (`frame`) — over the
    rig's `MediaSources` (`sources`: one for every deck; made here when
    none is given, from `resolver` and `opener`). `resolver`, `opener`,
    `closer`, `mixer` and `sound` read and write the sources'."""

    resolver = _through("resolver")
    opener = _through("opener")
    closer = _through("closer")
    mixer = _through("mixer")
    sound = _through("sound")

    def __init__(self, resolver=None, opener=adapters.open_source, *,
                 sources: MediaSources | None = None):
        self.__dict__["_media_sources"] = (sources if sources is not None
                                           else MediaSources(resolver, opener))
        self.channels: dict[str, Channel] = {c: Channel(c) for c in CHANNELS}
        self._closed = False

    @property
    def sources(self) -> MediaSources:
        """The rig's media sources these channels read through."""
        return self._sources()

    def _sources(self) -> MediaSources:
        """The sources — made here, from what the object held itself, for a
        `MediaState` from before plan 44 D3 (a hot reload re-classes it)."""
        src = self.__dict__.get("_media_sources")
        if src is None:
            src = MediaSources.__new__(MediaSources)
            for name in ("resolver", "opener", "closer", "mixer", "sound"):
                if name in self.__dict__:
                    src.__dict__[name] = self.__dict__.pop(name)
            src.__dict__.setdefault("resolver", NoResolver())
            src.__dict__.setdefault("opener", adapters.open_source)
            self.__dict__["_media_sources"] = src
        return src

    def _closer(self) -> Closer:
        return self._sources()._closer()

    def _mixer(self) -> mixer.Mixer:
        return self._sources()._mixer()

    def live_mixer(self) -> mixer.Mixer:
        """The sources' mixer (plan 45 V3: the analyzer's `mix` source)."""
        return self._sources().live_mixer()

    def _sound(self) -> _Sound:
        return self._sources()._sound()

    # -- the frame thread ---------------------------------------------------

    def poll(self, dt: float, now: float, *, heard: bool = True) -> None:
        """Once a frame: each channel's source follows its slot, a missing or
        replaced file is looked at again, and a timed source's transport is
        stepped and handed to it. Never raises for a source's sake. `heard`
        False (plan 44 D4, a deck off air): its channels leave the one mixer
        alone — the on-air deck's are what it plays."""
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
        if heard:
            voices, asked = self._voices()
            self._mixer().feed(voices, asked)

    # -- the sound (plan 45 V2) ---------------------------------------------

    def _voices(self) -> tuple[tuple, bool]:
        """Each channel's soundtrack follows its play-audio toggle: enabled
        the frame the toggle (or a new slot under it) asks, let go
        `OFF_FRAMES` frames after it stops asking (a lane flicking the
        toggle never queues a disable and a fresh decode a flick), through
        `_Sound`. Returns, for every channel heard, a `mixer.Voice` — a hold
        or a parked clip included, at velocity 0: the mixer's read head
        follows it and the mixer is what makes that silence (plan 45 V4) —
        and whether any channel asks for sound at all (the mixer opens its
        stream on that, before a hold ends)."""
        sound, out, asked = self._sound(), [], False
        for ch in self.channels.values():
            src = ch.source
            track = getattr(src, "audio", None)
            want = track if ch.play_audio else None
            try:
                if want is not None:
                    ch.quiet = 0
                    if ch.heard is None:
                        sound.on(want)          # (raises: not heard, tried again next frame)
                        ch.heard = want
                elif ch.heard is not None:
                    ch.quiet += 1
                    if ch.quiet >= OFF_FRAMES:
                        sound.off(ch.heard, self._closer())
                        ch.heard, ch.quiet = None, 0
            except Exception as e:  # noqa: BLE001 — a soundtrack must not kill the frame
                if src is not None:
                    src.status = error(f"{type(e).__name__}: {e}")
                continue
            if want is None:
                continue
            asked = True
            tr = ch.transport
            if tr is None:
                continue
            g = float(ch.gain)
            if g > 0.0:             # (NaN too: not > 0)
                out.append(mixer.Voice(want, float(tr.playhead), g, float(tr.velocity),
                                       float(tr.wrap), tr))
        return tuple(out), asked

    def _switch(self, ch: Channel, sid: str | None, now: float) -> None:
        old, ch.source, ch.transport = ch.source, None, None
        ch.frozen, ch.held = False, None
        if ch.heard is not None:        # the leaving source's `close` ends its sound
            self._sound().forget(ch.heard)
            ch.heard, ch.quiet = None, 0
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
        missing = isinstance(src, MissingSource) and src.status in (MISSING, FETCHING)
        if kind in ids.FILE_KINDS:
            here = r.path(sid) is not None
            if missing:       # arrived, or `fetching` and `missing` swapped
                return here or src.status != adapters.file_status(r, sid)
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

    def _freeze(self, ch: Channel, src) -> None:
        """A live feed at rate 0 holds the frame it showed (row 324)."""
        if ch.rate == 0.0:
            if not ch.frozen:
                ch.frozen, ch.held = True, self._sources().read(src)
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
            return self._sources().read(ch.source)
        except Exception:  # noqa: BLE001
            return None

    def status(self, c: str) -> str:
        """The source's status; `frozen` while a live feed is held at rate
        0 — nobody reads the source then, so its own would drift to
        `lost` (final review A-m3)."""
        ch = self.channels.get(c)
        if ch is None or ch.source is None:
            return EMPTY
        if ch.frozen:
            return FROZEN
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
        if kind in ids.FILE_KINDS:   # one still downloading is on its way, not missing
            return (self.resolver.path(sid) is not None
                    or adapters.file_status(self.resolver, sid) == FETCHING)
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
        return self._sources().drain(timeout)

    def drop_sources(self) -> None:
        """Every source this deck holds handed to the closer, and none opened
        again: all a deck off air has to do at exit (plan 44 D4) — the mixer
        and the closer's budget are the rig's, spent by the on-air deck."""
        self._closed = True
        for ch in self.channels.values():
            self._switch(ch, None, 0.0)

    def close(self, budget: float = CLOSE_BUDGET_S) -> bool:
        """App exit: every source dropped and closed, waiting at most
        `budget` s for all the closes together, then returning whatever is
        left (the closer is a daemon: a close still stuck dies with the
        process). A poll after this opens nothing. True when all closed.
        Within what is left of the app's exit (`pool.left`)."""
        self.drop_sources()
        t0 = time.monotonic()
        quiet = self._mixer().close(min(mixer.CLOSE_BUDGET_S, budget))
        left = max(budget - (time.monotonic() - t0), 0.0)
        return self.drain(pool.left(left)) and quiet


# plan 44 D3: the one object before the split, by its old name — a deck's
# channels over the rig's sources (`MediaState(resolver, opener)` makes both)
MediaState = Channels


def _read(src) -> MediaFrame | None:
    poll = getattr(src, "gl_poll", None)
    return poll() if poll is not None else src.latest()
