"""The playlist (plan 44 D6): for installations. Leave the cart running, a new look
every five minutes.

A playlist is the meta controller's and an operator's verb, not a look's: its file
names loadable patches and holds none of their state, it sits in the library's
``playlists/`` folder (`library.PLAYLISTS`, schema ``hyperspace.playlist/1``), and no
patch's row can press it (`routing.meta_refusal`). It is used with nobody editing, so it
has no guards against the operator (the owner, 2026-11-04): it does not wait for
unsaved edits, an open undo step or the panel, and a look on the deck off air is
written over. There is no pausing at all: it plays or it is stopped.

**One advance.** `Playing.tick`, once a frame:

1. `LEAD_S` before the fade is due, the next entry loads into the deck off air, by that
   deck's own `LoadedPatch.load`, the road a bank pad's load takes. A patch that is
   missing or will not read is skipped, said in words, and the next is tried at once.
2. The load asks `Fade.warm` for one small draw in the same frame, so its shaders compile
   there and not in the fade's first frame. A look that will not draw is skipped too.
3. When the fade is due and the warm draw is done, `MetaController.crossfade` runs the
   fader across, over the entry's ``fade_s``, else `output.xfade_s`. That is the one fade
   in the app, the same as a press of the panel's fade; this module draws nothing, and
   the dream worker is lent as for any fade (`Fade.lend`). No second one (DQ8).

An advance waits while the crossfader is between its ends or a fade is running
(`MetaController.mixing`), since then the deck off air is in the picture. That is a
fact of the mixer rather than a guard: a press of a bank pad is refused there too.

**Dwell** is the seconds from one fade's start to the next's, so 300 is a new look every
five minutes whatever the fades take. It is the entry's that has just gone on air.

**The file** is read again before each load (`Library.read` keeps the parse until the
mtime moves), so an edit or the other Mac's save lands at the next advance, with no
restart. A file that has gone keeps the last list playing, and says so.

**Its controls** (`register`): `playlist.play`, `.next` and `.prev`, one object on both
decks (a shared meta group), never saved and not modulatable, so no patch's row can press
one (`routing.meta_refusal`); a key or a pad button may, those being the meta controller's.

**Undo** (row 709). Each load is a step on that deck's stack, the most that stack keeps
is `undo.LIMIT`, and each load and each fade latches the panel's stack (row 753), so ⌘Z on
a cart left running refuses and takes nothing back until someone changes something there.

Imports only `library`; the meta controller, the decks and the fade arrive as arguments
and are used duck-typed, so `tests/test_playlist.py` runs `tick` over stand-ins.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .library import LOADABLE, PLAYLIST_KIND, PLAYLIST_VERSION, PLAYLISTS, LibraryError

SCHEMA = f"{PLAYLIST_KIND}/{PLAYLIST_VERSION}"
DEFAULT_DWELL_S = 300.0   # the owner's "a new look every five minutes"
MIN_DWELL_S = 1.0         # below this a look would not be seen, and a typo would strobe
LEAD_S = 2.0              # how long before its fade the next look loads and warms
SOON = -math.inf          # a time already past: due at the next tick


def _seconds(value: Any, what: str, least: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not value >= least:
        raise ValueError(f"{what} must be a number of seconds, at least {least:g}: got {value!r}")
    return float(value)


@dataclass(frozen=True)
class Entry:
    """One line of a playlist. `loadable` is a loadable patch's name in the library
    (its folders too: ``party/trip``). `fade_s` None: `output.xfade_s`, read at the fade."""

    loadable: str
    dwell_s: float = DEFAULT_DWELL_S
    fade_s: float | None = None

    def to_doc(self) -> dict:
        doc: dict[str, Any] = {"loadable": self.loadable, "dwell_s": self.dwell_s}
        if self.fade_s is not None:
            doc["fade_s"] = self.fade_s
        return doc


@dataclass
class Playlist:
    """A playlist's file as it reads: its name and its entries, in order."""

    name: str
    entries: list[Entry] = field(default_factory=list)

    def to_doc(self) -> dict:
        return {"schema": SCHEMA, "name": self.name,
                "entries": [e.to_doc() for e in self.entries]}

    @classmethod
    def from_doc(cls, doc: dict) -> Playlist:
        """The file's words. ValueError, in words, for what cannot be played."""
        if not isinstance(doc, dict) or not isinstance(doc.get("entries"), list):
            raise ValueError("a playlist's file holds a list of entries")  # noqa: TRY004
        out = []
        for i, row in enumerate(doc["entries"], 1):
            name = row.get("loadable") if isinstance(row, dict) else None
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"entry {i} names no loadable patch")
            fade = row.get("fade_s")
            out.append(Entry(name,
                             _seconds(row.get("dwell_s", DEFAULT_DWELL_S), f"entry {i}'s dwell_s",
                                      MIN_DWELL_S),
                             None if fade is None else _seconds(fade, f"entry {i}'s fade_s", 0.0)))
        return cls(str(doc.get("name") or ""), out)


def read(lib, name: str) -> Playlist:
    """Playlist `name` from the library; LibraryError, in words, for a bad file."""
    doc = lib.read(PLAYLISTS, name)
    try:
        playlist = Playlist.from_doc(doc)
    except ValueError as e:
        raise LibraryError(f"playlist {name}: {e}") from e
    playlist.name = playlist.name or name
    return playlist


def save(lib, playlist: Playlist) -> None:
    lib.save_playlist(playlist.to_doc())


class Playing:
    """One playlist being played, or none: what the meta controller ticks.

    `meta` is the `MetaController` (`off_air`, `mixing`, `crossfade`), `lib` the library,
    for the file and the words, and `fade` the `deck.Fade`, for the warm draw; None has
    none to wait for."""

    def __init__(self, meta, lib, fade=None):
        self.meta, self.lib, self.fade = meta, lib, fade
        self.playlist: Playlist | None = None
        self.on = False
        self.at: int | None = None      # the entry last faded to
        self.next = 0                   # the entry to load next
        self.armed: int | None = None   # the entry loaded and not yet faded to…
        self.armed_on = None            # …on this deck
        self.fails = 0                  # entries in a row that would not load or draw
        self.fade_at = self.load_at = SOON
        self.waited = False             # has this wait been said?
        self.last = 0.0                 # the frame's clock, as `tick` last saw it

    # ---- what a person does ----

    def select(self, name: str) -> bool:
        """Open playlist `name` at its top; it plays from there if playing. True when
        it read."""
        try:
            self.playlist = read(self.lib, name)
        except LibraryError as e:
            self.lib.say(warning=str(e))
            return False
        self.at, self.next, self.armed, self.fails = None, 0, None, 0
        if self.on:
            self.load_at = self.fade_at = SOON
        return True

    def play(self) -> None:
        """Start: the next entry loads and fades at once, and on from there."""
        if self.on:
            return
        if self.playlist is None or not self.playlist.entries:
            self.lib.say(warning="playlist: choose one with something in it first")
            return
        self.on, self.fails, self.waited = True, 0, False
        self.load_at = self.fade_at = SOON

    def stop(self, why: str | None = None) -> None:
        """Stop where it is: a fade running finishes, and what is on air stays. A look
        loaded for the next fade stays on the deck off air."""
        self.on, self.armed = False, None
        if why is not None:
            self.lib.say(warning=why)

    def step(self, by: int = 1) -> None:
        """Go on (+1) or back (-1) now, whatever is left of the dwell. Stopped, nothing
        fades: back moves the place it will play from, and on leaves it, as play goes on
        from there anyway."""
        entries = self.playlist.entries if self.playlist is not None else ()
        if not entries:
            return
        if by < 0:                      # the one before what is on air
            self.next, self.armed = ((self.at or 0) + by) % len(entries), None
        if self.on:
            self.fails = 0
            self.load_at = self.fade_at = SOON

    # ---- once a frame ----

    def tick(self, now: float) -> None:
        """One compare a frame while a look dwells (`load_at`); the rest runs only
        around an advance."""
        self.last = now
        if self.on and now >= self.load_at:
            self._due(now)

    def _due(self, now: float) -> None:
        meta = self.meta
        if meta.mixing:                 # the deck off air is in the picture
            if not self.waited:
                self.waited = True
                self.lib.say("playlist: waiting for the crossfader to reach an end")
            return
        self.waited = False
        if self.armed is None or self.armed_on is not meta.off_air:
            self._arm()                 # (on air moved by hand since: load again)
            return
        fade = self.fade
        if fade is not None:
            if fade.warm_deck is not None:
                return                  # its warm draw is still to come
            if fade.warm_error:
                self._failed(self.armed, fade.warm_error)
                return
        if now >= self.fade_at:
            self._go(now)

    def _fresh(self) -> list[Entry]:
        """The entries as the file says now; a file that will not read keeps the last."""
        pl = self.playlist
        try:
            self.playlist = pl = read(self.lib, pl.name)
        except LibraryError as e:
            self.lib.say(warning=f"{e}: playing the list as it last read")
        return pl.entries

    def _arm(self) -> None:
        """Load the next loadable entry into the deck off air, skipping what cannot."""
        entries = self._fresh()
        while self.on:
            if not entries:
                self.stop(f"playlist {self.playlist.name}: it has nothing in it. Stopped")
                return
            k = self.next = self.next % len(entries)
            why = self._load(entries[k].loadable)
            if why is None:
                self.armed, self.armed_on = k, self.meta.off_air
                return
            self._failed(k, why)

    def _load(self, name: str) -> str | None:
        """`name` on the deck off air; why not, in words, or None. A raise of any kind
        is one look lost: an install runs on."""
        loaded_patch = self.meta.off_air.loaded_patch
        if self.fade is not None:
            self.fade.warm_error = ""   # (the last warm draw's words: this load's own next)
        try:
            if self.lib.path_of(LOADABLE, name, loose=True) is None:
                return "there is no such patch"
            loaded_patch.load(name)
        except Exception as e:  # noqa: BLE001 — one bad file must not end an install
            return str(e) if isinstance(e, LibraryError) else f"{type(e).__name__}: {e}"[:160]
        return None

    def _failed(self, k: int, why: str) -> None:
        """Entry `k` is skipped and said, the next is next; every entry in a row and it
        stops rather than try for ever."""
        pl = self.playlist
        name = pl.entries[k].loadable if k < len(pl.entries) else f"entry {k + 1}"
        self.lib.say(warning=f"playlist {pl.name}: skipped {name}: {why}")
        self.armed, self.next = None, (k + 1) % max(1, len(pl.entries))
        self.fails += 1
        if self.fails >= len(pl.entries):
            self.stop(f"playlist {pl.name}: none of its {len(pl.entries)} entries will play. "
                      "Stopped, and what is on air stays")

    def _go(self, now: float) -> None:
        """The fade, and the clock for the next: this entry's dwell runs from now."""
        k, entries = self.armed, self.playlist.entries
        if k >= len(entries):           # (the file shrank under it)
            self.armed, self.next = None, 0
            return
        entry = entries[k]
        self.meta.crossfade(seconds=entry.fade_s)
        self.at, self.armed, self.next, self.fails = k, None, (k + 1) % len(entries), 0
        self.fade_at = now + entry.dwell_s
        self.load_at = self.fade_at - LEAD_S
        self.lib.say(f"playlist {self.playlist.name}: {entry.loadable}, "
                     f"{k + 1} of {len(entries)}, for {entry.dwell_s:g} s")

    def left(self) -> float | None:
        """Seconds until the next fade is due, or None: stopped or due now."""
        return self.fade_at - self.last if self.on and self.fade_at > self.last else None


PLAY_TIP = ("Play the playlist: each look loads off air, then the crossfader runs across. For "
            "an install: it does not wait for anyone's edits, and it writes over the deck off air.")


def register(reg, playing: Playing) -> list[str]:
    """`playlist.play`, `.next`, `.prev`: the meta controller's (`params.SHARED_META_GROUPS`),
    an operator's verbs. Declared once, on both decks, from lambdas so a hot reload lands."""
    settings = {"group": "playlist", "modulatable": False}
    reg.toggle("playlist.play", "Playlist", lambda: playing.on,
               lambda v: playing.play() if v else playing.stop(), persist=False, tip=PLAY_TIP,
               **settings)
    reg.trigger("playlist.next", "Playlist on", lambda: playing.step(1),
                tip="The next look now, whatever is left of this one's dwell.", **settings)
    reg.trigger("playlist.prev", "Playlist back", lambda: playing.step(-1),
                tip="The look before this one, now.", **settings)
    return ["playlist.play", "playlist.next", "playlist.prev"]
