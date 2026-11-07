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
   missing or will not read is skipped, said in words, and the next is tried at once. If
   none will play (Drive offline), it says so once, what is on air stays, and it tries
   again a dwell later: an install runs on.
2. The load asks `Fade.warm` for one small draw in the same frame, so its shaders compile
   there and not in the fade's first frame. A look that will not draw is skipped too.
3. When the fade is due and the warm draw is done, `MetaController.crossfade` runs the
   fader across, over the entry's ``fade_s``, else `output.xfade_s`. That is the one fade
   in the app, the same as a press of the panel's fade; this module draws nothing, and
   the dream worker is lent as for any fade (`Fade.lend`). No second one (DQ8).

An advance waits while the crossfader is between its ends or a fade is running
(`MetaController.mixing`), since then the deck off air is in the picture. That is a
fact of the mixer rather than a guard: a press of a bank pad is refused there too. A hand
that takes the fader across to the look armed has played it: its dwell starts there.

**Dwell** is the seconds from one fade's start to the next's, so 300 is a new look every
five minutes whatever the fades take. It is the entry's that has just gone on air.

**The file** is read again before each load, by the name it was chosen by (`Library.read`
keeps the parse until the mtime moves), so an edit or the other Mac's save lands at the
next advance, with no restart. A file that has gone keeps the last list playing, and says
so. A bad row is left out and said; the rest of the file plays, as with a missing patch.

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

from .library import PLAYLIST_KIND, PLAYLIST_VERSION, PLAYLISTS, LibraryError

SCHEMA = f"{PLAYLIST_KIND}/{PLAYLIST_VERSION}"
DEFAULT_DWELL_S = 300.0   # the owner's "a new look every five minutes"
MIN_DWELL_S = 1.0         # below this a look would not be seen, and a typo would strobe
MAX_DWELL_S = 7 * 86400.0  # a week: past this a number is a typo, and an install looks hung
FADE_MAX_S = 30.0         # `output.xfade_s`'s own top (`deck.register_xfade`, a test holds them)
LEAD_S = 2.0              # how long before its fade the next look loads and warms
SOON = -math.inf          # a time already past: due at the next tick


def _seconds(value: Any, what: str, least: float, most: float) -> float:
    """`value` as seconds in the range; ValueError, in words. Compared before any `float`, so
    infinity, not-a-number and an integer too long for a float are all refused here."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not least <= value <= most:
        raise ValueError(f"{what} must be seconds from {least:g} to {most:g}: got {value!r}")
    return float(value)


@dataclass(frozen=True)
class Entry:
    """One line of a playlist. `loadable` is a loadable patch's name in the library
    (its folders too: ``party/trip``). `fade_s` None: `output.xfade_s`, read at the fade.
    Refuses, in words, what could not be played, so nothing can write what would not read."""

    loadable: str
    dwell_s: float = DEFAULT_DWELL_S
    fade_s: float | None = None

    def __post_init__(self):
        if not isinstance(self.loadable, str) or not self.loadable.strip():
            raise ValueError("it names no loadable patch")
        object.__setattr__(self, "dwell_s", _seconds(self.dwell_s, "dwell_s", MIN_DWELL_S, MAX_DWELL_S))
        if self.fade_s is not None:
            object.__setattr__(self, "fade_s", _seconds(self.fade_s, "fade_s", 0.0, FADE_MAX_S))

    def to_doc(self) -> dict:
        doc: dict[str, Any] = {"loadable": self.loadable, "dwell_s": self.dwell_s}
        if self.fade_s is not None:
            doc["fade_s"] = self.fade_s
        return doc


@dataclass
class Playlist:
    """A playlist's file as it reads: its name, its entries in order, and in words the rows
    left out for being unplayable."""

    name: str
    entries: list[Entry] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list, compare=False)

    def to_doc(self) -> dict:
        return {"schema": SCHEMA, "name": self.name,
                "entries": [e.to_doc() for e in self.entries]}

    @classmethod
    def from_doc(cls, doc: dict) -> Playlist:
        """The file's words. A bad row is left out and said in `skipped`, as a missing patch
        is only skipped; ValueError, in words, for a file that holds no list at all."""
        if not isinstance(doc, dict) or not isinstance(doc.get("entries"), list):
            raise ValueError("a playlist's file holds a list of entries")  # noqa: TRY004
        out, skipped = [], []
        for i, row in enumerate(doc["entries"], 1):
            try:
                if not isinstance(row, dict):
                    raise ValueError("it is not an entry")  # noqa: TRY004
                out.append(Entry(row.get("loadable"), row.get("dwell_s", DEFAULT_DWELL_S),
                                 row.get("fade_s")))
            except ValueError as e:
                skipped.append(f"entry {i}: {e}")
        return cls(str(doc.get("name") or ""), out, skipped)


def _nearest(entries: list[Entry], name: str, i: int) -> int | None:
    """The place of the entry `name` nearest `i`, for a list with one look twice; or None."""
    hits = [k for k, e in enumerate(entries) if e.loadable == name]
    return min(hits, key=lambda k: abs(k - i)) if hits else None


def read(lib, name: str) -> Playlist:
    """Playlist `name` from the library; LibraryError, in words, for a bad file."""
    doc = lib.read(PLAYLISTS, name)
    try:
        playlist = Playlist.from_doc(doc)
    except ValueError as e:
        raise LibraryError(f"playlist {name}: {e}") from e
    playlist.name = playlist.name or name
    return playlist


def save(lib, playlist: Playlist, key: str | None = None) -> None:
    """Over the file `key` (what it was chosen by; else its own name) resolves to."""
    lib.save_playlist(playlist.to_doc(), key)


class Playing:
    """One playlist being played, or none: what the meta controller ticks.

    `meta` is the `MetaController` (`on_air`, `off_air`, `mixing`, `crossfade`), `lib` the
    library, for the file and the words, and `fade` the `deck.Fade`, for the warm draw;
    None has none to wait for."""

    def __init__(self, meta, lib, fade=None):
        self.meta, self.lib, self.fade = meta, lib, fade
        self.playlist: Playlist | None = None
        self.key: str | None = None     # the name it was chosen by: its file's, always
        self.on = False
        self.at: int | None = None      # the entry last on air
        self.next = 0                   # the entry to load next (`_arm` wraps it)
        self.armed: Entry | None = None  # the entry loaded and not yet on air…
        self.armed_at = 0               # …its place…
        self.armed_on = None            # …and its deck
        self.fails = 0                  # entries in a row that would not load or draw
        self.lost = False               # a whole pass would not play: said once, tried again
        self.stepping = False           # a step asked for and not yet on air
        self.fade_at = self.load_at = SOON
        self.waited = False             # has this wait been said?
        self.last = 0.0                 # the frame's clock, as `tick` last saw it
        self.rows_said: list[str] = []  # the file's bad rows, as last said

    # ---- what a person does ----

    def select(self, name: str) -> bool:
        """Open playlist `name` at its top; it plays from there if playing. True when
        it read."""
        try:
            self.playlist = read(self.lib, name)
        except LibraryError as e:
            self.lib.say(warning=str(e))
            return False
        self.key = name
        self.at, self.next, self.armed, self.fails = None, 0, None, 0
        self.lost, self.stepping, self.rows_said = False, False, []
        self._say_rows()
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
        self.on, self.fails, self.waited, self.lost = True, 0, False, False
        self.load_at = self.fade_at = SOON

    def edit(self, change) -> bool:
        """`change(entries)` over the file as it is now, so another Mac's save is kept, and
        into memory only once the save has landed. It returns the new entries, or None
        with its reason said. True when it landed; the place stays (`_keep_place`)."""
        try:
            pl = read(self.lib, self.key)
            entries = change(list(pl.entries))
            if entries is None:
                return False
            done = Playlist(pl.name, entries)
            save(self.lib, done, self.key)
        except (LibraryError, ValueError) as e:
            self.lib.say(warning=f"playlist not changed: {e}")
            return False
        self._keep_place(entries)
        self.playlist, self.rows_said = done, []
        return True

    def _row(self, entries: list[Entry], i: int, name: str) -> int | None:
        """The file's row for what the panel showed at `i`, by entry: the file may have moved
        under the panel."""
        k = _nearest(entries, name, i)
        if k is None:
            self.lib.say(warning=f"playlist: {name} is no longer in the file")
        return k

    def remove(self, i: int, name: str) -> bool:
        def change(entries):
            k = self._row(entries, i, name)
            return None if k is None else entries[:k] + entries[k + 1:]
        return self.edit(change)

    def set_dwell(self, i: int, name: str, dwell: float) -> bool:
        """A typed dwell, brought into range: the field can hold infinity."""
        dwell = float(dwell)
        dwell = MIN_DWELL_S if math.isnan(dwell) else min(MAX_DWELL_S, max(MIN_DWELL_S, dwell))

        def change(entries):
            k = self._row(entries, i, name)
            if k is None:
                return None
            entries[k] = Entry(entries[k].loadable, dwell, entries[k].fade_s)
            return entries
        return self.edit(change)

    def add(self, name: str) -> bool:
        return self.edit(lambda entries: [*entries, Entry(name)])

    def stop(self) -> None:
        """Stop where it is: a fade running finishes, and what is on air stays. A look
        loaded for the next fade stays on the deck off air."""
        self.on, self.armed, self.stepping = False, None, False

    def step(self, by: int = 1) -> None:
        """Go on (+1) or back (-1) one entry, and presses add up. Playing, it goes now,
        whatever is left of the dwell: the first press on is the entry already next, and
        the first back the one before what is on air. Stopped, nothing fades: it moves
        the place play goes on from."""
        entries = self.playlist.entries if self.playlist is not None else ()
        if not entries:
            return
        if not self.on:
            self.next += by
            return
        if self.stepping or by < 0:
            base = self.next if self.stepping or self.at is None else self.at
            self.next, self.armed = base + by, None
        self.stepping, self.fails, self.lost = True, 0, False
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
        if self.armed is not None and self.armed_on is meta.on_air:
            self._played(now)           # a hand took the fader across to it
            return
        if self.armed is None:
            self._arm(now)
            return
        fade = self.fade
        if fade is not None:
            if fade.warm_deck is not None:
                return                  # its warm draw is still to come
            if fade.warm_error:
                entry, self.armed = self.armed, None
                self._failed(self.armed_at, entry.loadable, fade.warm_error, now)
                return
        if now >= self.fade_at:
            self.meta.crossfade(seconds=self.armed.fade_s)
            self._played(now)

    def _say(self, words: str) -> None:
        """A line about one entry or the file: not while a whole pass is lost, already said."""
        if not self.lost:
            self.lib.say(warning=words)

    def _say_rows(self) -> None:
        pl = self.playlist
        if pl.skipped != self.rows_said:
            self.rows_said = pl.skipped
            for words in pl.skipped:
                self._say(f"playlist {pl.name}: left out {words}")

    def _keep_place(self, new: list[Entry]) -> None:
        """The list is changing to `new`: what is on air, what is armed and what is next
        stay the entries they are, wherever those now sit. An entry that has gone: nothing
        on air, nothing armed, and next is whatever took its place."""
        old = self.playlist.entries if self.playlist is not None else []
        if self.at is not None:
            self.at = _nearest(new, old[self.at].loadable, self.at) if self.at < len(old) else None
        if self.armed is not None:
            k = _nearest(new, self.armed.loadable, self.armed_at)
            if k is None:
                self.armed = None
            else:
                self.armed, self.armed_at = new[k], k
        if old:
            n = self.next % len(old)
            k = _nearest(new, old[n].loadable, n)
            self.next = n if k is None else k

    def _fresh(self) -> list[Entry]:
        """The entries as the file says now; a file that will not read keeps the last."""
        try:
            pl = read(self.lib, self.key)
            self._keep_place(pl.entries)
            self.playlist = pl
        except LibraryError as e:
            self._say(f"{e}: playing the list as it last read")
        self._say_rows()
        return self.playlist.entries

    def _arm(self, now: float) -> None:
        """Load the next loadable entry into the deck off air, skipping what cannot."""
        entries = self._fresh()
        if not entries:
            self._retry(now, "it has nothing in it", DEFAULT_DWELL_S)
            return
        while True:
            k = self.next = self.next % len(entries)
            why = self._load(entries[k].loadable)
            if why is None:
                self.armed, self.armed_at, self.armed_on = entries[k], k, self.meta.off_air
                return
            if self._failed(k, entries[k].loadable, why, now):
                return

    def _load(self, name: str) -> str | None:
        """`name` on the deck off air; why not, in words, or None. A raise of any kind
        is one look lost: an install runs on."""
        if self.fade is not None:
            self.fade.warm_error = ""   # (the last warm draw's words: this load's own next)
        try:
            self.meta.off_air.loaded_patch.load(name)
        except Exception as e:  # noqa: BLE001 — one bad file must not end an install
            return str(e) if isinstance(e, LibraryError) else f"{type(e).__name__}: {e}"[:160]
        return None

    def _failed(self, k: int, name: str, why: str, now: float) -> bool:
        """Entry `k` is skipped and said, the next is next. True when that is every entry
        in a row: then it waits a dwell before trying again."""
        pl = self.playlist
        self._say(f"playlist {pl.name}: skipped {name}: {why}")
        self.next = k + 1
        self.fails += 1
        if self.fails < len(pl.entries):
            return False
        dwell = pl.entries[k].dwell_s if k < len(pl.entries) else DEFAULT_DWELL_S
        self._retry(now, f"none of its {len(pl.entries)} entries will play", dwell)
        return True

    def _retry(self, now: float, why: str, dwell: float) -> None:
        """Nothing to play now. It stays on, what is on air stays, and it tries again a
        dwell later; said once, however long it lasts."""
        pl = self.playlist
        if not self.lost:
            self.lib.say(warning=f"playlist {pl.name}: {why}. What is on air stays; "
                                 "trying again each dwell")
        self.lost, self.fails, self.armed = True, 0, None
        self.load_at = self.fade_at = now + dwell

    def _played(self, now: float) -> None:
        """The armed entry is on air, or on its way: its dwell runs from now."""
        entry, k, total = self.armed, self.armed_at, len(self.playlist.entries)
        self.at, self.armed, self.next, self.fails = k, None, k + 1, 0
        self.lost, self.stepping = False, False
        self.fade_at = now + entry.dwell_s
        self.load_at = self.fade_at - LEAD_S
        self.lib.say(f"playlist {self.playlist.name}: {entry.loadable}, "
                     f"{k + 1} of {total}, for {entry.dwell_s:g} s")

    def left(self) -> float | None:
        """Seconds until the next fade is due, or None: stopped or due now."""
        return self.fade_at - self.last if self.on and self.fade_at > self.last else None


PLAY_TIP = ("Play the playlist: each look loads off air, then the crossfader runs across. For "
            "an install: it does not wait for anyone's edits, and it writes over the deck off air.")


def register(reg, playing: Playing) -> list[str]:
    """`playlist.play`, `.next`, `.prev`: the meta controller's (`params.SHARED_META_GROUPS`),
    an operator's verbs. Declared once, on both decks, from lambdas so a hot reload lands."""
    settings = {"group": "playlist"}
    reg.toggle("playlist.play", "Playlist", lambda: playing.on,
               lambda v: playing.play() if v else playing.stop(), persist=False, tip=PLAY_TIP,
               **settings)
    reg.trigger("playlist.next", "Playlist on", lambda: playing.step(1),
                tip="The next look now, whatever is left of this one's dwell.", **settings)
    reg.trigger("playlist.prev", "Playlist back", lambda: playing.step(-1),
                tip="The look before this one, now.", **settings)
    return ["playlist.play", "playlist.next", "playlist.prev"]
