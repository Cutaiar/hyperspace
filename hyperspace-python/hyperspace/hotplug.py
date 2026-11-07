"""A display can come and go while the app runs (wave 5 SC3b, audit fault P6). The owner,
2026-11-06: if a display "gets accidentally unplugged and then plugged back in, we cannot restart
the app in order to pick up that change. It has to be hot-pluggable."

The picture rests on the root window (SC3a), so no display can take it. This keeps the windows
in step with `displays.wanted(rows, screens)`, between frames. `Hotplug.between_frames` runs
right after `glfw.poll_events`; the monitor callback, inside that poll, only raises a flag.

**A display goes.** At once, in the same step, before anything draws: its window is hidden,
whole, and taken out of its `Slot`, so nothing presents to it or paces on it. It has to be hidden
because macOS has already moved it onto a display that's still here, where it would sit on another
window's picture, and it never sets `should_close`. Every other window's `monitor` follows, since
those are indices into a list that just changed. A slot whose first display went promotes its next
(`Slot.win` and `switches` are the first display's).

**It comes back within `HOLD_S`** (`[output] unplug_hold_s`): the same window, shown again where
it was, and everything as it was: a promoted display steps back, so the slot's first, its flips,
`output.fullscreen`, the mouse and who paces are all what they were, and output 1's frame keeps
its size meanwhile (`Root.hold_size`). A TV's HDMI re-sync costs a blank TV and no window. **It doesn't:** the window closes, in
the one order: that window current, `Presenter.release`, destroy, `Pacer.choose`. GL makes a
vertex array's number per context, so let go with the root current it can take the root's. (Apple's
driver numbers them across the share group, so it can't here, as `test_hotplug` shows: the order
is for what GL says, not for what was measured.)
**Later,** the job is on its row, by `placement.memory`: a new window, 35–38 ms on the main thread
on this Mac, which is the hitch a display change costs. Nothing else here takes time.

Arrivals and returns wait `SETTLE_S` for the list to hold still; going hides at once, and closing
waits `HOLD_S` from its last going, so a display flapping for ever costs no window at all.

**A display dropping and returning within one poll** looks like no change to the list, but macOS
has moved its windows. So any change looks for a window off its display, and puts it back.

**A step that raises costs the rest nothing.** Each step is guarded, whatever was done is wired
up in a `finally`, so nothing holds a destroyed window, and it's tried again a second later.

**A display off but still listed,** a projector asleep that keeps its link, is no change here.
One that drops its link is a display gone, after the hold. A window is never closed for being
covered or on a sleeping display.

**A row's target acts at once when it's chosen on this Mac** (`DisplayList.chosen`). **What the
other Mac chose waits** on a display showing something here, with a line and a button on the
panel: a shared row must not move a window in a show because someone is setting up elsewhere and
both have a "Built-in Retina Display". A row for a display that isn't here is taken as it comes.

**The control window** goes to one display and can't be hidden: it's the operator's only panel.
Its display gone, it stays where macOS put it for the hold, then moves to a display with no render
on it, or floats over a render if none is free (`GlfwBackend.float_over_renders`, above a fullscreen
render's level). It comes back when its row's display does. A window dragged by hand is left alone
until something else moves it, and rows are never written from here.

**Two of one name.** Labels go by place across the desk, so a second "TV" plugged in on the left
would take the first's label, its row and its job. So displays keep their numbers for the run, by
`Screen.uid` (`placement.labels`' `held`): the window stays on the display it's on, and the panel
says when a restart would number them otherwise. What's left: `Screen.uid` is the Mac's own
display id, and if two twins with no serial number change places or ports with both away, it can't
tell them apart, nor can anything else here. Nor can a restart: it numbers them across the desk.

Call everything from the main thread, between frames. Nothing here reads or writes a file: spots
are `seen`, read at launch, and kept up in memory. `--laptop` has no `Hotplug`.

Render stack's edge, as `pacing.py`: `glfw` is handed in, so a test can stand in for it.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import moderngl

from . import placement
from .displays import Opening, Running, Wanted, find, opened_of, read_row, wanted
from .outputs import Also, Offscreen, Presenter, Root, Slot
from .overlay import GlfwBackend, Output
from .placement import memory

HOLD_S = 3.0        # a window waits this long for its display: a re-sync is a second or two
SETTLE_S = 0.25     # the list must hold still this long before a window opens or comes back
LOOK_S = 1.0        # how often where the windows are is noted, for when they come back
REOPEN_S = 5.0      # a window that wouldn't open is tried again after this: each try is a hitch

TWINS = ("{} numbered by what each showed this run, not by where it sits. A restart numbers them "
         "left to right, and their jobs can swap.")
OTHER_MAC = "The other Mac chose: "


@dataclass
class Held:
    """A window whose display has just gone: hidden, whole, out of its slot. `since`: when."""

    slot: Slot
    display: str
    win: Any
    presenter: Any
    output: Any
    flip_x: bool
    flip_y: bool
    since: float
    asked: tuple[bool, bool, bool] | None = None    # the row's fullscreen and flips as it went


class Hotplug:
    """The windows, kept in step with the rows and the connected list. `run`: the panel's
    `displays.Running`, whose slots and `opened` this keeps. `main_output`: output 1's `Output`,
    which has the params and so stays output 1's, whichever window it has. `wired`: called when
    the windows change, for what holds one (`Keys`, `Mouse`, the frame's list). `say` and `warn`
    go to the footer. `seen`: `placement.load`'s, windows' spots; kept up here."""

    changed = False     # the monitor callback's flag

    def __init__(self, glfw: Any, run: Running, root: Root, ctrl_win: Any, main_output: Output, *,
                 seen: dict | None = None, hold_s: float = HOLD_S,
                 sizes: tuple[tuple[int, int], tuple[int, int]] = ((1280, 820), (2372, 900)),
                 title: str = "Hyperspace", overlay: bool = False,
                 make_context: Callable[[], Any] | None = None, notes: list[str] | None = None,
                 say: Callable[[str], None] | None = None, warn: Callable[[str], None] | None = None,
                 wired: Callable[[], None] | None = None,
                 clock: Callable[[], float] = time.perf_counter):
        self.glfw, self.run, self.root, self.ctrl_win, self.main = glfw, run, root, ctrl_win, main_output
        self.seen = seen if seen is not None else {}
        self.hold_s = float(hold_s)
        self.render_size, self.control_size = sizes
        self.title, self.overlay = title, bool(overlay)
        self.make_context = make_context or moderngl.create_context
        self.notes = notes if notes is not None else []
        self.say, self.warn = say, warn
        self.wired = wired
        self.clock = clock
        self.backend = GlfwBackend(glfw)        # the control window's
        self.screens = placement.screens(glfw)
        self.held: list[Held] = []
        self.acting = dict(run.store.current)   # the rows the windows follow
        self.floating = False                   # the control window, over a render
        self.times: list[tuple[str, float]] = []    # each change's words and milliseconds
        self.failed = ""                        # the last step that raised
        self._settle_at: float | None = None
        self._arrived: set[str] = set()
        self._here = set(self._keys())          # the displays the rows were last acted on with
        self._wont: dict[int, str] = {}         # output → why its window wouldn't open
        self._rects: dict[int, tuple] = {}      # id(window) → its windowed rect, as last noted
        self._looked = -1e9
        self._ctrl_on: str | None = None        # the display it's on
        self._ctrl_row: str | None = None       # the display its row says
        self._ctrl_gone_at: float | None = None
        self._ctrl_left = ""                    # the display it had to leave
        self._ctrl_spots: dict[str, tuple] = {}     # its rect on each display it's been on
        self._touched = False                   # something changed that holders must hear
        self._fault = False                     # a step raised this time
        self._retry_at = float("-inf")
        self._ranks: dict[int, int] = {}        # id(window) → its place in its slot, oldest first
        self._next_rank = 0
        self.gone_spots: dict[str, tuple] = {}  # where closed windows were, for `away_spots`
        for sl, also in self._open_now():
            self._ranked(also.win if also is not None else sl.win)
        want = wanted(self.acting, self.screens, run.labels(self.screens))
        self._ctrl_row = memory(want.control.display) if want.control else None
        self._note_where()

    def start(self) -> None:
        """The callback, once. It fires inside `poll_events`: a flag, and nothing else."""
        self.glfw.set_monitor_callback(lambda *_: setattr(self, "changed", True))
        self.changed = True     # a first look: a change since the windows opened went unheard

    # ---- what's there ----

    def _keys(self) -> dict[str, int]:
        """Each connected display's memory → its index in `screens`."""
        return {memory(t): i for i, t in enumerate(self.run.labels(self.screens))}

    def _open_now(self) -> list[tuple[Slot, Also | None]]:
        return [(sl, a) for sl in self.run.slots if sl.opened for a in (None, *sl.also)]

    def windows(self) -> list:
        """The windows only this holds: both exits destroy them too."""
        return [g.win for g in self.held]

    def away_spots(self) -> dict[str, tuple]:
        """Where each window with none open now was, by its display's memory: for windows.json,
        as a display unplugged at a quit keeps its spot."""
        out = dict(self.gone_spots)
        for g in self.held:
            was = self._rects.get(id(g.win))
            if was is not None:
                out[memory(g.display)] = was
        return out

    def _ranked(self, win) -> int:
        """`win`'s place among its slot's windows: the order they took their jobs in, whichever
        has been promoted since."""
        if id(win) not in self._ranks:
            self._ranks[id(win)] = self._next_rank
            self._next_rank += 1
        return self._ranks[id(win)]

    def _live(self) -> list:
        """What may pace, in slot order, as `app._slot_windows`."""
        return [w for sl in self.run.slots if sl.opened and sl.presenter is not None
                for w in (sl.win, *(a.win for a in sl.also))]

    # ---- each frame ----

    def between_frames(self, now: float | None = None) -> None:
        """Whatever a change asks, between frames. Costs a flag and two compares when there's none,
        and never raises: the frame goes on, and what failed is said."""
        now = self.clock() if now is None else now
        ran = now >= self._retry_at
        try:
            if ran:
                self._fault = False
                self._step(now)
        except Exception as e:  # noqa: BLE001 — a window system's hiccup must not stop the show
            self._raised("a change of display", e)
        finally:
            if self._touched:
                self._wire()
            if ran and self._fault:
                self._retry_at = now + LOOK_S   # tried again, not every frame
                if self._settle_at is None:
                    self._settle_at = self._retry_at

    def _raised(self, what: str, e: Exception) -> None:
        """Said once, and tried again in a moment."""
        self._fault = True
        why = f"displays: {what} failed: {type(e).__name__}: {e}"[:200]
        if why != self.failed:
            self.failed = why
            self.notes.append(why)
            print(why, file=sys.stderr)
            if self.warn is not None:
                self.warn(why)

    def _try(self, what: str, fn: Callable, *args) -> Any:
        """One step of a change: its raising costs the others nothing."""
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001 — as `between_frames`
            self._raised(what, e)
            return None

    def _wire(self) -> None:
        """Every holder of a window hears what's open, whatever happened: the frame must not reach a
        destroyed window. Each by itself, and a holder that couldn't hear is told again next frame."""
        self._touched = False
        self._try("who paces", self.root.pacer.choose, self._live(), self.root.win)
        self._keep_size()
        if self.wired is not None:
            try:
                self.wired()
            except Exception as e:  # noqa: BLE001
                self._raised("pointing the keys and the mouse", e)
                self._touched = True
        self._try("the context", self.glfw.make_context_current, self.ctrl_win)  # what the loop has current

    def _keep_size(self) -> None:
        """A window of output 1's that outranks what it has now was its first a moment ago."""
        first = self.run.slots[0] if self.run.slots else None
        rank = self._ranked(first.win) if first is not None and first.opened else float("inf")
        self.root.hold_size = first is not None and any(
            g.slot is first and self._ranked(g.win) < rank for g in self.held)

    def _step(self, now: float) -> None:
        if self.changed:
            self.changed = False
            self._touched = True
            try:
                self._list_moved(now)
            except Exception:
                self.changed = True     # (the list unread: it's looked at again, not lost)
                raise
        chose = self.run.store.chosen
        due = self._settle_at is not None and now >= self._settle_at
        if chose or due or self._ran_out(now):
            self._touched = True
            self._act(now, chose)
        elif now - self._looked >= LOOK_S:
            self._looked = now
            self._note_where()

    def _ran_out(self, now: float) -> bool:
        if any(now - g.since >= self.hold_s for g in self.held):
            return True
        at = self._ctrl_gone_at
        return at is not None and now - at >= self.hold_s and bool(self.screens)

    def _note_where(self) -> None:
        """Where each window is, for its return: afterwards macOS has moved it."""
        for sl, also in self._open_now():
            out = also.output if also is not None else sl.output
            rect = None if out is None else out.windowed_rect()
            if out is not None and rect is not None:
                self._rects[id(out.win)] = tuple(rect)
        if self._ctrl_gone_at is not None or not self.screens:
            return
        g = self.glfw
        rect = (*g.get_window_pos(self.ctrl_win), *g.get_window_size(self.ctrl_win))
        on = placement.on_screen(rect, self.screens)
        if on is not None:
            tags = self.run.labels(self.screens)
            self._ctrl_on = memory(tags[self.screens.index(on)])
            self._ctrl_spots[self._ctrl_on] = rect

    # ---- a display went or came: what can't wait ----

    def _list_moved(self, now: float) -> None:
        g = self.glfw
        scr = placement.screens(g)
        if not scr and g.get_monitors():
            self.changed = True         # (a monitor that can't say yet: the next frame's)
            return
        was = set(self._keys())
        self.screens = scr
        keys = self._keys()
        self._arrived |= set(keys) - was
        for sl, also in reversed(self._open_now()):     # (a slot's first last: its next takes over)
            where = also.display if also is not None else sl.display
            if memory(where) not in keys:
                self._try("hiding a window", self._hold, sl, also, now)
        for held in self.held:
            if memory(held.display) in keys:
                held.since = now        # a flap: its hold starts again from its last going
        self._follow()
        if self._ctrl_on in keys:
            self._ctrl_gone_at = None
        elif self._ctrl_gone_at is None:
            self._ctrl_gone_at = now
        self._settle_at = now + SETTLE_S
        self._try("putting a window back", self._strays, keys)
        self._after(wanted(self.acting, scr, self.run.labels(scr)))

    def _strays(self, keys: dict[str, int]) -> None:
        """A window off its display, though its display is here: macOS moved it when a display
        dropped and came back within one poll, which the list can't show."""
        scr = self.screens
        for sl, also in self._open_now():
            holder = also if also is not None else sl
            out = holder.output
            i = keys.get(memory(holder.display))
            if out is None or i is None or out.backend is None:
                continue
            on = placement.on_screen(tuple(out.backend.window_rect(out.win)), scr)
            if on is not None and on == scr[i]:
                continue
            was = self._rects.get(id(out.win))
            spot = dict(zip("xywh", was, strict=True)) if was else placement.spot(self.seen, holder.display, sl.n)
            out.back_at(self._where("render", self.render_size, i, spot, sl.label))
        on_key = self._ctrl_on
        if on_key in keys and self._ctrl_gone_at is None and on_key in self._ctrl_spots:
            g = self.glfw
            rect = (*g.get_window_pos(self.ctrl_win), *g.get_window_size(self.ctrl_win))
            on = placement.on_screen(rect, scr)
            if on is None or on != scr[keys[on_key]]:
                self._move_control(on_key, keys)

    def _hold(self, sl: Slot, also: Also | None, now: float) -> None:
        """Out of its slot and out of sight, whole."""
        where = also.display if also is not None else sl.display
        asked = read_row(find(self.acting, where))
        held = self._take(sl, also, now)
        held.asked = (asked["fullscreen"], asked["flip_x"], asked["flip_y"])
        self.held.append(held)
        try:
            self.glfw.hide_window(held.win)
        except Exception as e:  # noqa: BLE001 — it's on its way to being closed anyway
            self.notes.append(f"displays: {held.display}'s window wouldn't hide: {e}"[:200])

    def _follow(self) -> None:
        """Each window's label and index, as the list has it now. `Output.monitor` is an index,
        and the next `apply` would cover the wrong display."""
        tags = self.run.labels(self.screens)
        keys = {memory(t): i for i, t in enumerate(tags)}
        for sl, also in self._open_now():
            holder = also if also is not None else sl
            i = keys.get(memory(holder.display))
            if i is None:
                continue
            holder.display, holder.monitor = tags[i], i
            if holder.output is not None:
                holder.output.monitor = i

    # ---- out of a slot, and into one ----

    def _take(self, sl: Slot, also: Also | None, now: float) -> Held:
        """A window out of its slot. A slot's first display going, its next is the first."""
        if also is not None:
            sl.also.remove(also)
            return Held(sl, also.display, also.win, also.presenter, also.output, also.flip_x, also.flip_y, now)
        if sl.n == 1 and sl.output is self.main:
            out = Output(None, GlfwBackend(self.glfw), allowed=False)
            self.main.swap_window(out)      # the params stay; the window and all it was go
        else:
            out, sl.output = sl.output, None
        held = Held(sl, sl.display, sl.win, sl.presenter, out, bool(sl.switches.flip_x),
                    bool(sl.switches.flip_y), now)
        sl.win, sl.presenter, sl.display, sl.monitor, sl.fullscreen = None, None, "", -1, False
        if sl.also:
            a = sl.also.pop(0)
            self._seat_first(sl, a.display, a.win, a.presenter, a.output, a.flip_x, a.flip_y)
        return held

    def _seat_first(self, sl: Slot, display: str, win, presenter, out, flip_x: bool, flip_y: bool) -> None:
        """`win` is `sl`'s first display now. (With overlay allowed, a further display opened at
        launch isn't transparent: promoted, it's opaque until its display comes round again.)"""
        sl.win, sl.presenter, sl.display, sl.missing = win, presenter, display, ""
        sl.monitor, sl.fullscreen = out.monitor, bool(out.fullscreen)
        sl.switches.flip_x, sl.switches.flip_y = flip_x, flip_y
        if sl.n == 1:
            self.main.swap_window(out)
            sl.output = self.main
        else:
            sl.output = out

    def _seat(self, sl: Slot, display: str, win, presenter, out, flip_x: bool, flip_y: bool) -> None:
        self._ranked(win)
        if sl.opened:
            sl.also.append(Also(display, out.monitor, bool(out.fullscreen), win, presenter, out,
                                flip_x=flip_x, flip_y=flip_y))
        else:
            self._seat_first(sl, display, win, presenter, out, flip_x, flip_y)

    def _in_order(self, sl: Slot) -> None:
        """A window back from a moment away goes back in its place: a first steps in again, and
        the display promoted for it steps back, flips, fullscreen and all."""
        sl.also.sort(key=lambda a: self._ranked(a.win))
        if not sl.opened or not sl.also or self._ranked(sl.also[0].win) > self._ranked(sl.win):
            return
        top = sl.also.pop(0)
        if sl.n == 1 and sl.output is self.main:
            out = Output(None, GlfwBackend(self.glfw), allowed=False)
            self.main.swap_window(out)
        else:
            out = sl.output
        down = Also(sl.display, sl.monitor, bool(out.fullscreen), sl.win, sl.presenter, out,
                    flip_x=bool(sl.switches.flip_x), flip_y=bool(sl.switches.flip_y))
        self._seat_first(sl, top.display, top.win, top.presenter, top.output, top.flip_x, top.flip_y)
        sl.also.append(down)
        sl.also.sort(key=lambda a: self._ranked(a.win))

    # ---- acting on the rows ----

    def _act(self, now: float, chose: tuple[str, ...]) -> None:
        t0 = self.clock()
        store = self.run.store
        self._settle_at = None
        if chose:
            store.chosen = ()
        rows = store.current
        for key, entry in rows.items():     # what this Mac chose, and any display not here to move
            if key in chose or key not in self._here:
                self.acting[key] = entry
        scr = self.screens
        tags = self.run.labels(scr)
        want = wanted(self.acting, scr, tags)
        keys = {memory(t): i for i, t in enumerate(tags)}
        shows = {memory(o.display): (n, o) for n, os in want.renders.items() for o in os}
        closed, opened, back = [], [], []
        for g in list(self.held):
            k = memory(g.display)
            if k in keys:
                if shows.get(k, (0,))[0] == g.slot.n:
                    self._try("bringing a window back", self._back, g, shows[k][1])
                    if g not in self.held:
                        back.append(g)
                else:
                    self._close(g)
            elif now - g.since >= self.hold_s:
                self._close(g)
                closed.append(g)
        for sl, also in reversed(self._open_now()):
            where = memory(also.display if also is not None else sl.display)
            if shows.get(where, (0,))[0] != sl.n:
                self._close(self._take(sl, also, now))      # (`_close` never raises)
        on = {memory(a.display if a is not None else sl.display): sl for sl, a in self._open_now()}
        for key, (n, o) in shows.items():
            if (key not in on and 0 < n <= len(self.run.slots)
                    and self._try("opening a window", self._open, self.run.slots[n - 1], o)):
                opened.append(key)
        self._try("following the list", self._follow)
        self._try("putting a window back", self._strays, keys)
        self._here = set(keys)
        self._try("moving the control window", self._control, want, keys, now, set(opened))
        self._arrived = set()
        self._try("the slots' words", self._after, want)
        if self._wont and self._settle_at is None:
            self._settle_at = now + REOPEN_S
        ms = (self.clock() - t0) * 1000.0
        for g in closed:
            self._tell(f"{g.display} has gone: {g.slot.label} has no window there, and the other pictures go on",
                       ms, warning=True)
        for key in opened:
            self._tell(f"{tags[keys[key]]} shows {self.run.slots[shows[key][0] - 1].label}", ms)
        for g in back:
            self.notes.append(f"displays: {g.display} dropped and came back: the same window")

    def _tell(self, words: str, ms: float, warning: bool = False) -> None:
        """A change, in the footer and on the SYSTEM page, with what it cost the frame."""
        self.times.append((words, ms))
        del self.times[:-32]
        self.notes.append(f"displays: {words} ({ms:.0f} ms)"[:200])
        fn = self.warn if warning else self.say
        if fn is not None:
            fn(words)

    def _after(self, want: Wanted) -> None:
        """What follows from what's open: the slots' words, what they publish through, and the
        panel's `opened`. Who paces, the keys and the mouse are `_wire`'s."""
        for sl in self.run.slots:
            if sl.opened:
                sl.window, sl.missing = True, ""
            else:
                sl.window = not (sl.syphon or sl.ndi)
                away = want.away.get(sl.n)
                sl.missing = (self._wont.get(sl.n, "") or
                              (f"its display is not connected ({', '.join(away)})" if sl.window and away else ""))
            self._try("what an output publishes through", self._publish_follows, sl)
        slots = self.run.slots
        control = want.control if want.control is not None and memory(want.control.display) == self._ctrl_on else None
        self.run.opened = opened_of(slots, control)

    def _publish_follows(self, sl: Slot) -> None:
        """A later output that's published draws to a window's `tap`, or with none its own
        `offscreen` (`app._open_publishers`, `_draw_render`). Output 1's always has the frame."""
        if sl.n == 1 or not sl.publishers:
            return
        ctx = self.root.frame.ctx
        if sl.opened and sl.tap is None:
            sl.tap = Offscreen(ctx)
            old, sl.offscreen = sl.offscreen, None
        elif not sl.opened and sl.offscreen is None:
            sl.offscreen = Offscreen(ctx)
            old, sl.tap = sl.tap, None
        else:
            return
        if old is not None:
            self.glfw.make_context_current(self.root.win)
            old.release()

    def _where(self, kind: str, size, i: int, spot, what: str = "") -> tuple:
        """Where a window goes on display `i`: `spot` if that's on it, else the default there."""
        rect, _ = placement.place(kind, size, self.screens, i, spot, what=what)
        return rect

    def _open(self, sl: Slot, o: Opening) -> bool:
        """`sl`'s window on the display `o`. One that won't open is said, and tried again at
        the next change."""
        g = self.glfw
        first = not sl.opened
        rect = self._where("render", self.render_size, o.index,
                           placement.spot(self.seen, o.display, sl.n), sl.label)
        # (a first display's only, as a launch: a further one with alpha would show the desktop)
        self._hints(transparent=self.overlay and first and sl.n == 1)
        title = (f"{self.title} — {o.display}" if not first else self.title if sl.n == 1
                 else f"{self.title} — {sl.name or f'output {sl.n}'}")
        win = g.create_window(int(rect[2]), int(rect[3]), title, None, self.root.win)
        g.window_hint(g.TRANSPARENT_FRAMEBUFFER, False)
        if not win:
            self._refused(sl, f"its window on {o.display} could not be created")
            return False
        try:
            g.set_window_pos(win, int(rect[0]), int(rect[1]))
            g.make_context_current(win)
            g.swap_interval(0)
            presenter = Presenter(self.make_context())
        except Exception as e:  # noqa: BLE001 — as at a launch: the others go on
            g.make_context_current(self.root.win)
            g.destroy_window(win)
            self._refused(sl, f"its GL context on {o.display} would not open: {type(e).__name__}: {e}"[:160])
            return False
        out = Output(win, GlfwBackend(g), allowed=False)
        out.monitor, out.fullscreen = o.index, bool(o.fullscreen)
        self._seat(sl, o.display, win, presenter, out, o.flip_x, o.flip_y)
        self.gone_spots.pop(memory(o.display), None)
        self._wont.pop(sl.n, None)
        g.make_context_current(self.root.win)
        return True

    def _hints(self, transparent: bool) -> None:
        """The one kind of window an output has (`app._windows`), never taking focus from the
        control window as it opens."""
        g = self.glfw
        g.window_hint(g.CONTEXT_VERSION_MAJOR, 3)
        g.window_hint(g.CONTEXT_VERSION_MINOR, 3)
        g.window_hint(g.OPENGL_PROFILE, g.OPENGL_CORE_PROFILE)
        g.window_hint(g.OPENGL_FORWARD_COMPAT, True)
        g.window_hint(g.SAMPLES, 0)
        g.window_hint(g.TRANSPARENT_FRAMEBUFFER, transparent)
        g.window_hint(g.AUTO_ICONIFY, False)
        g.window_hint(g.FOCUSED, False)
        g.window_hint(g.FOCUS_ON_SHOW, False)

    def _refused(self, sl: Slot, why: str) -> None:
        said = self._wont.get(sl.n) == why
        self._wont[sl.n] = why
        if said:
            return
        self.notes.append(f"output: {sl.label}: {why}"[:200])
        if self.warn is not None:
            self.warn(f"{sl.label}: {why}")

    def _back(self, g: Held, o: Opening) -> None:
        """Its display came back in time: the same window, where it was, in its place in its
        slot. What it had stands, as a desk may have set it, but for what its row has changed since."""
        gl = self.glfw
        gl.make_context_current(g.win)
        gl.swap_interval(0)         # (it may have been pacing as it went: `choose` says who does)
        gl.make_context_current(self.root.win)
        was = self._rects.get(id(g.win))
        spot = dict(zip("xywh", was, strict=True)) if was else placement.spot(self.seen, o.display, g.slot.n)
        rect = self._where("render", self.render_size, o.index, spot, g.slot.label)
        if g.asked is not None:
            if o.fullscreen != g.asked[0]:
                g.output.fullscreen = bool(o.fullscreen)
            if o.flip_x != g.asked[1]:
                g.flip_x = bool(o.flip_x)
            if o.flip_y != g.asked[2]:
                g.flip_y = bool(o.flip_y)
        g.output.monitor = o.index
        g.output.back_at(rect)
        gl.set_window_attrib(g.win, gl.FOCUS_ON_SHOW, False)
        gl.show_window(g.win)
        self.held.remove(g)
        self._seat(g.slot, o.display, g.win, g.presenter, g.output, g.flip_x, g.flip_y)
        self._in_order(g.slot)

    def _close(self, g: Held) -> None:
        """Gone for good, or its row changed. **The order:** that window current, its
        `Presenter` let go, destroyed, then who paces (the module's docstring says why). Never raises: a window is out of its
        slot by now, and whatever fails, it goes and the next window's step is taken."""
        gl = self.glfw
        if g in self.held:
            self.held.remove(g)
        self._touched = True
        was = self._rects.pop(id(g.win), None)
        self._ranks.pop(id(g.win), None)
        if was is not None:
            self.gone_spots[memory(g.display)] = tuple(was)
            if not isinstance(self.seen.get("displays"), dict):
                self.seen["displays"] = {}
            self.seen["displays"][memory(g.display)] = dict(zip("xywh", was, strict=True))

        def release() -> None:
            gl.make_context_current(g.win)
            if g.presenter is not None:
                g.presenter.release()
                g.presenter.ctx.release()

        self._try("letting a window's objects go", release)
        self._try("the root's context", gl.make_context_current, self.root.win)
        self._try("closing a window", gl.destroy_window, g.win)
        self._try("who paces", self.root.pacer.choose, self._live(), self.root.win)

    # ---- the control window ----

    def _control(self, want: Wanted, keys: dict[str, int], now: float, opened: set[str]) -> None:
        """Where it goes, if anywhere, and whether it has to float there."""
        rendered = {memory(a.display if a is not None else sl.display) for sl, a in self._open_now()}
        free = [k for k in self._across(keys) if k not in rendered]
        row = memory(want.control.display) if want.control else None
        to = None
        if row is not None and (row != self._ctrl_row or row in self._arrived):
            to = row
        self._ctrl_row = row
        on = self._ctrl_on
        if to is None and on not in keys:
            if self._ctrl_gone_at is None:
                self._ctrl_gone_at = now
            if now - self._ctrl_gone_at >= self.hold_s and keys:
                floats = memory(want.floats.display) if want.floats else None
                to = floats if floats in free else free[0] if free else floats or self._across(keys)[0]
                self._ctrl_left = self._ctrl_left or (on or "")
        elif to is None and on in self._arrived:
            to = on                     # back from a flap: macOS may have moved it
        elif to is None and self._ctrl_left in self._arrived:
            to = self._ctrl_left        # the display it had to leave, with no row saying
        elif to is None and (on in opened or self.floating) and free:
            to = free[0]                # a render opened on it, or a display came free
        if to is not None:
            self._move_control(to, keys)
            if to in (row, self._ctrl_left):
                self._ctrl_left = ""
            self._ctrl_gone_at = None
        floats_now = (self._ctrl_on in rendered
                      and (self.floating or to is not None or self._ctrl_on in opened))
        if floats_now != self.floating:
            self.floating = floats_now
            self.backend.float_over_renders(self.ctrl_win, floats_now)

    def _across(self, keys: dict[str, int]) -> list[str]:
        """The connected displays' memories, left to right."""
        at = {i: k for k, i in keys.items()}
        return [at[i] for i in placement.arranged(self.screens) if i in at]

    def _move_control(self, key: str, keys: dict[str, int]) -> None:
        was = self._ctrl_spots.get(key)
        spot = dict(zip("xywh", was, strict=True)) if was else None
        rect = self._where("control", self.control_size, keys[key], spot)
        g = self.glfw
        g.set_window_pos(self.ctrl_win, int(rect[0]), int(rect[1]))
        g.set_window_size(self.ctrl_win, int(rect[2]), int(rect[3]))
        if key != self._ctrl_on:
            self.notes.append(f"displays: the control window goes to {key}"[:200])
        self._ctrl_on = key
        self._ctrl_spots[key] = tuple(rect)

    # ---- the panel's ----

    def lines(self) -> list[str]:
        """What the output section says of what's going on."""
        out = [f"{g.display} has gone: {g.slot.label} waits for it, and the other pictures go on."
               for g in self.held]
        if self._ctrl_left and self._ctrl_on and self._ctrl_left != self._ctrl_on:
            out.append(f"The control window is on {self._ctrl_on} while {self._ctrl_left} is away.")
        twins = placement.differs(self.screens, self.run.held)
        if twins:
            out.append(TWINS.format(" and ".join(twins) + (" is" if len(twins) == 1 else " are")))
        return out

    def others_chose(self) -> list[tuple[str, str]]:
        """(label, target) of each connected display the other Mac has chosen another target for,
        which waits for `take_others`. Read while the output section is drawn."""
        tags = self.run.labels(self.screens)
        rows = dict(self.run.store.current)
        for key in self.run.store.chosen:       # this Mac's own, a frame from being acted on
            if key in self.acting:
                rows[key] = self.acting[key]
            else:
                rows.pop(key, None)
        now = wanted(rows, self.screens, tags).shown
        was = wanted(self.acting, self.screens, tags).shown
        return [(t, v) for t, v in now.items() if was.get(t, "") != v]

    def take_others(self) -> None:
        """The panel's button: what the other Mac chose, acted on now."""
        self.run.store.chosen = (*self.run.store.chosen, *self.run.store.current)
