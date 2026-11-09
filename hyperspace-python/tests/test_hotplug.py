"""SC3b: displays coming and going, over a stand-in monitor list through the real launch
(`app._windows`), the real rows and the real `Pacer`; then through real GL, the real close order
and `_draw_render`, on hidden windows. A real cable is hand check 629, and nothing here is one."""

from __future__ import annotations

import gc
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import app, config, hotplug, placement, ui, ui_displays
from hyperspace.displays import CONTROL, DisplayList, Running, row, wanted
from hyperspace.hotplug import HOLD_S, LOOK_S, REOPEN_S, SETTLE_S, Hotplug
from hyperspace.outputs import Offscreen, Root, Slot
from hyperspace.overlay import GlfwBackend, Output
from hyperspace.pacing import Pacer
from hyperspace.ui import PAGE_KEYS
from hyperspace.watchdog import RenderWatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


@dataclass(eq=False)
class Mon:
    """A display: `uid` is what the Mac calls it this boot."""

    name: str
    rect: tuple[int, int, int, int]
    uid: int


def _laptop():
    return Mon("Built-in", (0, 0, 1728, 1117), 1)


def _tv(x=1728, uid=2, name="TV"):
    return Mon(name, (x, 0, 1920, 1080), uid)


def _projector(x=3648, uid=3):
    return Mon("Projector", (x, 0, 1920, 1080), uid)


class Glfw:
    """The window system, for the rows' sake. Its callback fires inside `poll_events`, and when
    a display goes, its windows move to one still there and stay open, as macOS's did."""

    def __init__(self, mons):
        self.mons = list(mons)
        self.windows: dict = {}
        self.destroyed: list = []
        self.hints: dict = {}
        self.callback = None
        self.queue: list = []
        self.current = None
        self.log: list = []
        self.intervals: dict = {}
        self.in_poll = False
        self.fail_create = False

    def __getattr__(self, name):
        if name.isupper():
            return name
        raise AttributeError(name)

    # ---- monitors
    def get_monitors(self):
        return list(self.mons)

    def get_monitor_workarea(self, m):
        return m.rect

    def get_monitor_pos(self, m):
        return m.rect[:2]

    def get_monitor_name(self, m):
        return m.name.encode()

    def get_cocoa_monitor(self, m):
        return m.uid

    def get_video_mode(self, m):
        return SimpleNamespace(size=SimpleNamespace(width=m.rect[2], height=m.rect[3]))

    def set_monitor_callback(self, fn):
        self.callback = fn

    def unplug(self, *mons):
        for m in mons:
            self.mons.remove(m)
        self.queue.append(())
        left = self.mons[0].rect if self.mons else (0, 0, 0, 0)
        for win in self.windows.values():       # macOS moves them, and they stay open
            if any(self._on(win, m) for m in mons):
                win["pos"] = (left[0] + 40, left[1] + 40)

    def plug(self, *mons):
        self.mons.extend(mons)
        self.queue.append(())

    @staticmethod
    def _on(win, m):
        x, y = win["pos"]
        w, h = win["size"]
        cx, cy = x + w / 2, y + h / 2
        return m.rect[0] <= cx < m.rect[0] + m.rect[2] and m.rect[1] <= cy < m.rect[1] + m.rect[3]

    def poll_events(self):
        self.in_poll = True
        for _ in self.queue:
            if self.callback is not None:
                self.callback(None, 0)
        self.queue = []
        self.in_poll = False

    # ---- windows
    def window_hint(self, k, v):
        self.hints[k] = v

    def create_window(self, w, h, title, mon, share):
        assert not self.in_poll, "never inside the poll"
        if self.fail_create:
            return None
        win = f"win{len(self.windows) + len(self.destroyed) + 1}:{title}"
        self.windows[win] = {"pos": (0, 0), "size": (w, h), "title": title, "shown": True,
                             "hints": dict(self.hints), "attrs": {}}
        self.log.append(("create", win))
        return win

    def _w(self, win):
        assert win in self.windows, f"{win} has been destroyed"
        return self.windows[win]

    def destroy_window(self, win):
        self._w(win)
        del self.windows[win]
        self.destroyed.append(win)
        self.log.append(("destroy", win))

    def hide_window(self, win):
        self._w(win)["shown"] = False
        self.log.append(("hide", win))

    def show_window(self, win):
        self._w(win)["shown"] = True
        self.log.append(("show", win))

    def set_window_pos(self, win, x, y):
        self._w(win)["pos"] = (x, y)

    def get_window_pos(self, win):
        return self._w(win)["pos"]

    def set_window_size(self, win, w, h):
        self._w(win)["size"] = (w, h)

    def get_window_size(self, win):
        return self._w(win)["size"]

    def get_framebuffer_size(self, win):
        return self._w(win)["size"]

    def set_window_attrib(self, win, attr, v):
        self._w(win)["attrs"][attr] = v

    def get_window_attrib(self, win, attr):
        return self._w(win)["attrs"].get(attr, 0)

    def set_window_opacity(self, win, a):
        self._w(win)

    def make_context_current(self, win):
        if win is not None:
            self._w(win)
        self.current = win

    def get_current_context(self):
        return self.current

    def swap_interval(self, n):
        self.intervals[self.current] = n


class Rig:
    """A launch as `app.main` makes one, with a `Hotplug` over it, and a clock."""

    def __init__(self, monkeypatch, tmp_path, mons, rows, **kw):
        self.g = g = Glfw(mons)
        monkeypatch.setattr(app, "glfw", g)
        self.released: list = []
        real = app.Presenter.release

        def release(p):
            self.released.append(g.current)
            g.log.append(("release", g.current))
            real(p)
        monkeypatch.setattr(app.Presenter, "release", release)
        (tmp_path / "Drive").mkdir(exist_ok=True)
        (tmp_path / "home").mkdir(exist_ok=True)
        self.store = DisplayList(tmp_path / "Drive", tmp_path / "home", seed=rows)
        self.store.sync()
        scr = placement.screens(g)
        cfg = {"output": dict(config.DEFAULTS["output"])}
        self.root_win = g.create_window(64, 64, "root", None, None)
        self.slots, self.ctrl = app._windows(False, cfg, tmp_path / "home", self.root_win,
                                             wanted(self.store.current, scr))
        self.contexts = []
        app._open_presenters(self.slots, self.root_win, make_context=self._context)
        self.main = Output(self.slots[0].win, GlfwBackend(g), allowed=False)
        self.main.monitor = self.slots[0].monitor
        self.main.fullscreen = self.slots[0].fullscreen
        self.slots[0].output = self.main
        for sl in self.slots[1:]:
            if sl.opened:
                sl.output = app._later_output(sl)
        for sl in self.slots:
            for a in sl.also:
                a.output = app._also_output(a)
        self.root = Root(self.root_win, SimpleNamespace(ctx=None), Pacer(g))
        self.root.pacer.choose(app._slot_windows(self.slots), self.root_win)
        self.run = Running(self.store, lambda: self.plug.screens, self.slots)
        self.t = 100.0
        self.wired = 0
        self.heard = app._slot_windows(self.slots)
        self.strict = True
        self.notes: list = []
        self.said: list = []
        self.warned: list = []
        self.plug = Hotplug(g, self.run, self.root, self.ctrl, self.main, make_context=self._context,
                            notes=self.notes, say=self.said.append, warn=self.warned.append,
                            wired=self._wired, clock=lambda: self.t, **kw)
        self.plug.start()
        g.make_context_current(self.ctrl)

    def _context(self):
        ctx = SimpleNamespace(release=lambda: None)
        self.contexts.append(ctx)
        return ctx

    def _wired(self):
        self.wired += 1
        self.heard = app._slot_windows(self.slots)

    def tick(self, dt=0.016):
        """A frame's start, and what the frame would touch: every window it holds must be alive."""
        self.t += dt
        self.g.poll_events()
        self.plug.between_frames()
        for w in app._slot_windows(self.slots):
            self.g._w(w)
        if self.strict:
            for w in self.heard:
                self.g._w(w)        # (`Keys.more`, `Mouse.win`: `glfw.get_key` on a dead window ends a show)
            assert self.g.current == self.ctrl, "what the loop has current here"
        for o in app._outputs_now(self.slots):
            o.apply()

    def run_for(self, secs):
        for _ in range(int(secs / 0.05) + 2):
            self.tick(0.05)

    def shown(self):
        """{display: output n} of what's open, by label."""
        return {(a.display if a else sl.display): sl.n
                for sl in self.slots if sl.opened for a in (None, *sl.also)}

    def live_window(self, display):
        return next((a or sl).win for sl in self.slots if sl.opened for a in (None, *sl.also)
                    if (a or sl).display == display)

    def on(self, win, m):
        return self.g._on(self.g._w(win), m)


ROWS = {"Built-in": row(CONTROL), "TV": row("output.1"), "Projector": row("output.2")}


@pytest.fixture
def rig(monkeypatch, tmp_path):
    made = []

    def make(mons=None, rows=None, **kw):
        r = Rig(monkeypatch, tmp_path, mons if mons is not None else [_laptop(), _tv(), _projector()],
                rows if rows is not None else ROWS, **kw)
        made.append(r)
        return r
    yield make


def test_with_nothing_unplugged_nothing_happens(rig):
    r = rig()
    before = list(r.g.windows)
    r.g.log.clear()
    r.run_for(5.0)
    assert list(r.g.windows) == before and r.g.log == []
    assert r.shown() == {"TV": 1, "Projector": 2}
    assert r.root.pacer.owner == r.slots[0].win


def test_the_callback_only_raises_a_flag(rig):
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    r.g.log.clear()
    r.g.poll_events()           # (`create_window` asserts it's never inside the poll)
    assert r.plug.changed is True and r.g.log == [] and r.g.windows


def test_output_1_unplugged_hides_at_once_then_closes_in_order_and_comes_back(rig):
    r = rig()
    laptop, tv, _ = r.g.mons
    win = r.slots[0].win
    r.g.unplug(tv)
    assert r.on(win, laptop), "macOS moved it onto a display still here, and it's open"
    r.tick()
    # the same step, before anything is drawn: out of sight and out of the slot
    assert r.g.windows[win]["shown"] is False
    assert not r.slots[0].opened and r.main.win is None
    assert r.root.pacer.owner == r.slots[1].win, "the next display paces"
    assert r.g.intervals[r.slots[1].win] == 1
    assert r.root.hold_size, "output 1's frame keeps its size for now"
    assert any("TV has gone" in s for s in r.plug.lines())
    # the hold runs out: the close order, always
    r.g.log.clear()
    r.run_for(HOLD_S)
    assert win not in r.g.windows
    assert [e for e in r.g.log if e[0] in ("release", "destroy")] == [("release", win), ("destroy", win)]
    assert r.released == [win], "with its own context current"
    assert not r.root.hold_size and not r.plug.held
    assert r.slots[0].missing == "its display is not connected (TV)"
    assert any("TV has gone" in s for s in r.warned)
    # it comes back: the same job
    r.g.log.clear()
    r.g.plug(tv)
    r.tick()
    assert not r.slots[0].opened, "the list holds still first"
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV": 1, "Projector": 2}
    assert r.slots[0].missing == "" and r.main.win == r.slots[0].win != win
    assert r.on(r.slots[0].win, tv)
    assert r.g.windows[r.slots[0].win]["title"] == "Hyperspace"
    assert r.root.pacer.owner == r.slots[0].win, "output 1 paces again"
    assert r.g.intervals[r.slots[1].win] == 0, "and only one window waits"
    assert any(s == "TV shows output 1" for s in r.said)
    assert r.plug.times and r.plug.times[-1][0] == "TV shows output 1"


def test_a_later_output_unplugged_and_back(rig):
    r = rig()
    _, _, pr = r.g.mons
    one, two = r.slots[0].win, r.slots[1].win
    r.g.unplug(pr)
    r.tick()
    assert not r.slots[1].opened and r.slots[1].output is None and r.g.windows[two]["shown"] is False
    assert r.root.pacer.owner == one and r.slots[0].win == one
    r.run_for(HOLD_S)
    assert two not in r.g.windows
    r.g.plug(pr)
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV": 1, "Projector": 2} and r.on(r.slots[1].win, pr)
    assert r.root.pacer.owner == one, "the first still paces"


def test_a_further_display_unplugged_and_its_first_promoted(rig):
    rows = {"Built-in": row(CONTROL), "TV": row("output.1", flip_x=True), "Projector": row("output.1", flip_y=True)}
    r = rig(rows=rows)
    _, tv, pr = r.g.mons
    sl = r.slots[0]
    first, also = sl.win, sl.also[0].win
    assert (sl.switches.flip_x, sl.switches.flip_y) == (True, False)
    # the further display goes: the first is untouched
    r.g.unplug(pr)
    r.tick()
    assert sl.win == first and sl.also == [] and r.g.windows[also]["shown"] is False
    r.g.plug(pr)
    r.run_for(SETTLE_S)
    assert sl.also[0].win == also and r.g.windows[also]["shown"] is True, "the same window"
    # the first goes: the next is the first, with its flips what the frame is drawn with
    r.g.unplug(tv)
    r.tick()
    assert sl.win == also and sl.display == "Projector" and sl.also == []
    assert (sl.switches.flip_x, sl.switches.flip_y) == (False, True)
    assert r.main.win == also, "output 1's params have whichever window is its first"
    assert r.root.hold_size, "its first is away a moment: the frame keeps its size"
    assert r.root.pacer.owner == also
    r.run_for(HOLD_S)
    assert not r.root.hold_size, "gone: the next has the size, as SC2 has it"
    assert first not in r.g.windows and sl.win == also
    # it comes back as the further display, and nothing moves that needn't
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert sl.win == also and [a.display for a in sl.also] == ["TV"] and sl.also[0].flip_x is True
    assert r.on(sl.also[0].win, tv)


def test_the_control_window_moves_to_one_still_there_and_comes_back(rig):
    r = rig(mons=[_laptop(), _tv(), _projector()],
            rows={"Built-in": row(CONTROL), "TV": row("output.1")})
    laptop, _, pr = r.g.mons
    r.g.set_window_pos(r.ctrl, 100, 100)
    r.plug._note_where()
    assert r.plug._ctrl_on == "Built-in"
    r.g.unplug(laptop)
    r.tick()
    assert r.plug._ctrl_gone_at is not None, "it can't be hidden, and it waits out the hold"
    r.run_for(HOLD_S)
    assert r.on(r.ctrl, pr), "the display no render is on"
    assert r.plug.floating is False
    assert r.plug.lines() == ["The control window is on Projector while Built-in is away."]
    r.g.plug(laptop)
    r.run_for(SETTLE_S)
    assert r.on(r.ctrl, laptop) and r.g.get_window_pos(r.ctrl) == (100, 100), "where it was"
    assert r.plug.lines() == []


def test_the_display_it_left_coming_and_going_before_settling_raises_nothing(rig):
    """It left a display with no row saying, which comes back and goes again inside `SETTLE_S`."""
    r = rig(mons=[_laptop(), _tv(), _projector()], rows={"TV": row("output.1")})
    laptop, _, pr = r.g.mons
    r.g.set_window_pos(r.ctrl, 100, 100)
    r.plug._note_where()
    r.g.unplug(laptop)
    r.run_for(HOLD_S + 0.1)
    assert r.on(r.ctrl, pr) and r.plug._ctrl_left == "Built-in"
    r.g.plug(laptop)
    r.tick()
    r.g.unplug(laptop)
    r.run_for(SETTLE_S + 1.0)
    assert not r.plug.failed and not any("failed" in s for s in r.warned), r.warned
    assert r.on(r.ctrl, pr) and not r.plug._arrived
    r.g.plug(laptop)
    r.run_for(SETTLE_S)
    assert r.on(r.ctrl, laptop) and r.plug._ctrl_left == ""


def test_the_control_window_fits_a_smaller_display_and_the_pinned_panel_with_it(rig):
    """`Panel.panel_rect` follows the OS window every frame (row 808), so the move has to leave a
    window that fits: its full 2372 × 900 on a 1280 × 720 display, and the panel is off the edge."""
    small = Mon("Small", (1728, 0, 1280, 720), 5)
    r = rig(mons=[_laptop(), small], rows={"Built-in": row(CONTROL)})
    laptop = r.g.mons[0]
    r.g.set_window_pos(r.ctrl, 10, 10)
    r.g.set_window_size(r.ctrl, 1700, 1000)
    r.run_for(1.2)
    r.g.unplug(laptop)
    r.run_for(HOLD_S + 0.1)
    x, y = r.g.get_window_pos(r.ctrl)
    w, h = r.g.get_window_size(r.ctrl)
    assert r.on(r.ctrl, small) and x >= small.rect[0] and x + w <= small.rect[0] + 1280 and y + h <= 720
    for desk, pad in ((False, False), (True, False), (False, True), (True, True)):
        px, py, pw, ph = ui.panel_rect((w, h), desk, pad)
        assert 0 <= px and px + pw <= w and 0 <= py and py + ph <= h and pw > 0 and ph > 0
    r.g.plug(laptop)
    r.run_for(SETTLE_S)
    assert r.g.get_window_size(r.ctrl) == (1700, 1000), "and its own size, back on its own"


def test_the_control_window_floats_over_a_render_with_nowhere_free(rig, monkeypatch):
    floated = []
    monkeypatch.setattr(GlfwBackend, "float_over_renders", lambda self, win, on: floated.append((win, on)))
    r = rig(mons=[_laptop(), _tv()], rows={"Built-in": row(CONTROL), "TV": row("output.1", fullscreen=True)})
    laptop, tv = r.g.mons
    r.g.set_window_pos(r.ctrl, 100, 100)
    r.plug._note_where()
    r.g.unplug(laptop)
    r.run_for(HOLD_S + 0.1)
    assert r.on(r.ctrl, tv) and r.plug.floating and floated == [(r.ctrl, True)]
    assert r.shown() == {"TV": 1}, "and the render isn't touched"
    # a free display arrives, unknown: it goes there
    new = Mon("Dell", (-1920, 0, 1920, 1080), 9)
    r.g.plug(new)
    r.run_for(SETTLE_S)
    assert r.on(r.ctrl, new) and not r.plug.floating and floated[-1] == (r.ctrl, False)
    assert "Dell" not in r.shown()


def test_a_render_chosen_on_the_control_windows_display_moves_it_or_floats_it(rig, monkeypatch):
    monkeypatch.setattr(GlfwBackend, "float_over_renders", lambda self, win, on: None)
    r = rig(mons=[_laptop(), _tv()], rows={"Built-in": row(CONTROL), "TV": row("output.1")})
    laptop, _ = r.g.mons
    r.g.set_window_pos(r.ctrl, 100, 100)
    r.plug._note_where()
    r.store.set_target("Built-in", "output.2", ["Built-in", "TV"])
    r.tick()
    assert r.shown() == {"Built-in": 2, "TV": 1}, "at once"
    assert r.on(r.ctrl, laptop) and r.plug.floating, "both displays have a render"


def test_every_display_gone_and_back_in_another_order(rig):
    r = rig()
    laptop, tv, pr = r.g.mons
    one, two = r.slots[0].win, r.slots[1].win
    r.g.unplug(laptop, tv, pr)
    r.tick()
    assert r.plug.screens == [] and r.root.pacer.owner is None
    assert not any(sl.opened for sl in r.slots)
    assert r.ctrl in r.g.windows, "the panel's window stays"
    r.run_for(HOLD_S + 1.0)
    assert one not in r.g.windows and two not in r.g.windows
    assert r.root.pacer.owner is None
    # back, the projector first and listed first
    r.g.plug(pr)
    r.run_for(SETTLE_S)
    assert r.shown() == {"Projector": 2}
    assert r.slots[1].monitor == 0 and r.slots[1].output.monitor == 0
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    r.g.plug(laptop)
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV": 1, "Projector": 2}
    assert r.on(r.slots[0].win, tv) and r.on(r.slots[1].win, pr)
    assert (r.slots[1].monitor, r.slots[0].monitor) == (0, 1), "indices are the list's as it is"
    assert r.on(r.ctrl, laptop), "its row's display"
    assert r.root.pacer.owner == r.slots[0].win


def test_a_flap_tears_nothing_down(rig):
    """A TV's HDMI re-sync: off and on within the hold. Hidden at once, the same window after."""
    r = rig(rows={"Built-in": row(CONTROL), "TV": row("output.1", fullscreen=True), "Projector": row("output.2")})
    _, tv, _ = r.g.mons
    win, presenter = r.slots[0].win, r.slots[0].presenter
    for _ in range(4):
        r.tick()
    assert r.g.get_window_pos(win) == tv.rect[:2] and r.main.mode == "fullscreen"
    r.g.log.clear()
    for _ in range(3):
        r.g.unplug(tv)
        r.run_for(1.0)
        assert r.g.windows[win]["shown"] is False and not r.slots[0].opened
        assert r.main.fullscreen is False, "the window took it with it"
        r.g.plug(tv)
        r.run_for(SETTLE_S)
        assert r.slots[0].win == win and r.slots[0].presenter is presenter
        assert r.main.win == win and r.main.fullscreen is True and r.main.mode == "fullscreen"
        assert r.g.windows[win]["shown"] is True
        assert r.g.windows[win]["attrs"]["FOCUS_ON_SHOW"] is False, "the operator keeps the focus"
        assert r.g.get_window_pos(win) == tv.rect[:2], "it covers its display again"
        assert r.root.pacer.owner == win and r.g.intervals[win] == 1
        assert not r.root.hold_size
    kinds = {e[0] for e in r.g.log}
    assert "destroy" not in kinds and "create" not in kinds and "release" not in kinds


def test_a_flap_past_the_hold_closes_at_most_once_a_hold(rig):
    r = rig()
    tv = r.g.mons[1]
    r.g.log.clear()
    for _ in range(20):         # off for a second, on for an instant, for twenty seconds
        r.g.unplug(tv)
        r.run_for(1.0)
        r.g.plug(tv)
        r.tick()
    assert not [e for e in r.g.log if e[0] in ("create", "destroy")], "the hold restarts only by coming back"


def test_a_plain_window_returns_where_it_was(rig):
    r = rig()
    tv = r.g.mons[1]
    win = r.slots[0].win
    r.g.set_window_pos(win, 1800, 50)
    r.run_for(1.1)
    r.g.unplug(tv)
    r.tick()
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert r.g.get_window_pos(win) == (1800, 50)
    # and after a close, a new window takes the spot its display had
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert r.slots[0].win != win and r.g.get_window_pos(r.slots[0].win) == (1800, 50)


def test_every_index_follows_when_the_list_shifts(rig):
    """`Output.monitor` is an index: with the primary gone, a fullscreen window's own display is
    a different number at once, or the next `apply` covers the wrong one."""
    r = rig(rows={"Built-in": row("output.2", fullscreen=True), "TV": row("output.1", fullscreen=True),
                  "Projector": row(CONTROL)})
    laptop, tv, _ = r.g.mons
    for _ in range(3):
        r.tick()
    assert r.g.get_window_pos(r.slots[0].win) == tv.rect[:2]
    r.g.unplug(laptop)
    r.tick()
    assert (r.main.monitor, r.slots[0].monitor) == (0, 0)
    r.tick()
    assert r.g.get_window_pos(r.slots[0].win) == tv.rect[:2], "still its own"


def test_a_new_unknown_display_waits_with_no_target(rig):
    r = rig()
    new = Mon("Dell", (-1920, 0, 1920, 1080), 9)
    before = set(r.g.windows)
    r.g.plug(new)
    r.run_for(1.0)
    assert set(r.g.windows) == before
    assert r.run.labels(r.plug.screens)[-1] == "Dell"
    assert wanted(r.plug.acting, r.plug.screens).shown["Dell"] == ""
    # chosen, it acts at once
    r.store.set_target("Dell", "output.3", ["Dell"])
    r.tick()
    assert r.shown()["Dell"] == 3 and r.on(r.slots[2].win, new)
    assert r.run.opened["Dell"] == "output.3"


def test_a_row_acts_at_once(rig):
    r = rig()
    tv = r.g.mons[1]
    old = r.slots[0].win
    r.store.set_target("TV", "output.3", ["Built-in", "TV", "Projector"])
    r.tick()                    # the next frame: no settling for a choice
    assert r.shown() == {"TV": 3, "Projector": 2} and old not in r.g.windows
    assert not r.slots[0].opened and r.main.win is None
    assert r.on(r.slots[2].win, tv)
    assert r.run.opened["TV"] == "output.3" and r.root.pacer.owner == r.slots[1].win
    # nothing on it: it closes, and the row is remembered
    r.store.set_target("TV", "", ["Built-in", "TV", "Projector"])
    r.tick()
    assert r.shown() == {"Projector": 2}
    # the control window goes to one
    r.store.set_target("TV", CONTROL, ["Built-in", "TV", "Projector"])
    r.tick()
    assert r.on(r.ctrl, tv) and r.run.opened["TV"] == CONTROL


def test_a_row_chosen_while_its_display_is_away_acts_when_it_returns(rig):
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    r.store.set("TV", target="output.4", fullscreen=True, flip_x=True)
    r.tick()
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert r.shown()["TV"] == 4
    assert r.slots[3].switches.flip_x is True and r.slots[3].output.fullscreen is True


def test_what_the_other_mac_chose_waits_on_a_display_here_and_not_on_one_away(rig, tmp_path):
    """Both have a "Built-in Retina Display", so a shared row mustn't move a window in a show."""
    r = rig()
    r.store.rows["TV"] = row("output.2", at=2e9)        # as the merge lands it
    r.g.log.clear()
    r.run_for(1.0)
    assert r.shown() == {"TV": 1, "Projector": 2} and r.g.log == [], "nothing moved"
    assert r.plug.others_chose() == [("TV", "output.2")]
    # a display that isn't here takes its row as it comes, and acts on it when it arrives
    r.store.rows["Dell"] = row("output.3", at=2e9)
    new = Mon("Dell", (-1920, 0, 1920, 1080), 9)
    r.g.plug(new)
    r.run_for(SETTLE_S)
    assert r.shown()["Dell"] == 3, "not here to move"
    assert r.shown()["TV"] == 1, "still waiting"
    # the panel's button
    r.plug.take_others()
    r.tick()
    assert r.shown()["TV"] == 2 and r.plug.others_chose() == []


def test_a_twin_plugged_in_on_the_left_leaves_the_window_on_its_display(rig):
    r = rig(mons=[_laptop(), _tv(x=3648, uid=2)], rows={"Built-in": row(CONTROL), "TV": row("output.1")})
    _, right = r.g.mons
    win = r.slots[0].win
    twin = _tv(x=1728, uid=7)
    r.g.plug(twin)
    r.run_for(SETTLE_S)
    assert r.slots[0].win == win and win in r.g.windows, "the same window"
    assert r.on(win, right)
    tags = r.run.labels(r.plug.screens)
    assert tags == ["Built-in", "TV #1", "TV #2"], "numbered by arrival, for the run"
    assert placement.labels(r.plug.screens)[1] == "TV #2", "where a restart would number it"
    assert r.slots[0].display == "TV #1"
    assert r.shown() == {"TV #1": 1}, "the new one waits: it has no row"
    assert any("A restart numbers them" in s for s in r.plug.lines())


def test_either_twin_going_leaves_the_other_its_job(rig):
    rows = {"Built-in": row(CONTROL), "TV #1": row("output.1"), "TV #2": row("output.2")}
    r = rig(mons=[_laptop(), _tv(x=1728, uid=2), _tv(x=3648, uid=7)], rows=rows)
    _, left, right = r.g.mons
    one, two = r.slots[0].win, r.slots[1].win
    # the left goes: by place the right would be "TV", the left's row
    r.g.unplug(left)
    r.run_for(HOLD_S + 0.1)
    assert r.slots[1].win == two and r.slots[1].display == "TV #2" and not r.slots[0].opened
    assert r.run.labels(r.plug.screens) == ["Built-in", "TV #2"]
    r.g.plug(left)
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV #1": 1, "TV #2": 2} and r.slots[1].win == two
    assert r.on(r.slots[0].win, left)
    # the right goes
    one = r.slots[0].win
    r.g.unplug(right)
    r.run_for(HOLD_S + 0.1)
    assert r.shown() == {"TV": 1} and r.slots[0].win == one
    r.g.plug(right)
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV #1": 1, "TV #2": 2} and r.on(r.slots[1].win, right)


def test_twins_both_out_and_back_in_turn_keep_their_jobs_by_the_macs_id(rig):
    rows = {"TV #1": row("output.1"), "TV #2": row("output.2"), "Built-in": row(CONTROL)}
    r = rig(mons=[_laptop(), _tv(x=1728, uid=2), _tv(x=3648, uid=7)], rows=rows)
    _, left, right = r.g.mons
    r.g.unplug(left, right)
    r.run_for(HOLD_S + 0.1)
    r.g.plug(right)         # the right first: lone, by name it would be the first's
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV #2": 2} and r.on(r.slots[1].win, right)
    r.g.plug(left)
    r.run_for(SETTLE_S)
    assert r.shown() == {"TV #1": 1, "TV #2": 2}


def test_a_window_that_wont_open_is_said_and_the_rest_go_on(rig):
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    r.g.fail_create = True
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert not r.slots[0].opened and r.slots[1].opened
    assert "could not be created" in r.slots[0].missing and any("could not be created" in s for s in r.warned)
    r.g.fail_create = False
    new = Mon("Dell", (-1920, 0, 1920, 1080), 9)
    r.g.plug(new)               # the next change tries again
    r.run_for(SETTLE_S)
    assert r.slots[0].opened and r.slots[0].missing == ""


@pytest.mark.parametrize("how", ["its display goes", "its row changes"])
def test_a_refused_window_no_row_wants_is_forgotten(rig, how):
    """Its words don't stay on the slot, and nothing is re-armed for the rest of the run."""
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    r.g.fail_create = True
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert "could not be created" in r.slots[0].missing and r.plug._wont
    if how == "its display goes":
        r.g.unplug(tv)
        r.run_for(SETTLE_S)
        assert r.slots[0].missing == "its display is not connected (TV)"
    else:
        r.store.set_target("TV", "", ["Built-in", "TV", "Projector"])
        r.tick()
        assert r.slots[0].missing == ""
    assert not r.plug._wont and r.plug._settle_at is None
    tries = []
    real = r.g.create_window
    r.g.create_window = lambda *a: (tries.append(1), real(*a))[1]
    r.run_for(REOPEN_S * 2 + 1.0)
    assert tries == [] and r.plug._settle_at is None


def test_the_wheel_over_a_window_thats_no_longer_output_1s_moves_nothing(monkeypatch):
    """A return demotes the promoted window: alive, a further display, its callback still set."""
    calls: dict = {}
    monkeypatch.setattr(app, "glfw", SimpleNamespace(set_scroll_callback=lambda w, fn: calls.__setitem__(w, fn)))
    reg = dict.fromkeys(("camera.yaw", "camera.pitch", "camera.zoom", "camera.pan.x", "camera.pan.y"))
    m = app.Mouse("first", reg, SimpleNamespace())
    calls["first"]("first", 0.0, 1.0)
    assert m._wheel == 1.0
    m.aim("promoted")
    calls["first"]("first", 0.0, 1.0)
    assert m._wheel == 1.0, "not output 1's now"
    calls["promoted"]("promoted", 0.0, 1.0)
    assert m._wheel == 2.0
    m.aim("first")
    calls["promoted"]("promoted", 0.0, 1.0)
    assert m._wheel == 2.0, "demoted: it's a further display"
    calls["first"]("first", 0.0, 1.0)
    assert m._wheel == 3.0
    m.aim(None)
    calls["first"]("first", 0.0, 1.0)
    assert m._wheel == 3.0


def test_a_window_that_wont_open_is_tried_every_few_seconds_with_no_change(rig):
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    r.g.fail_create = True
    tries = []
    real = r.g.create_window
    r.g.create_window = lambda *a: (tries.append(1), real(*a))[1]
    r.g.plug(tv)
    r.run_for(SETTLE_S + 12.0)
    assert 2 <= len(tries) <= 4, "not every frame: each one is a hitch"
    assert len([s for s in r.warned if "could not be created" in s]) == 1, "said once"
    r.g.fail_create = False
    r.run_for(REOPEN_S + 0.1)
    assert r.slots[0].opened and r.slots[0].missing == ""


def test_a_context_that_wont_open_closes_its_window(rig):
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    r.plug.make_context = lambda: (_ for _ in ()).throw(RuntimeError("no"))
    made = set(r.g.windows)
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert not r.slots[0].opened and set(r.g.windows) == made and "GL context" in r.slots[0].missing


def test_a_step_that_raises_is_said_and_the_frame_goes_on(rig, monkeypatch):
    r = rig()
    tv = r.g.mons[1]
    r.g.unplug(tv)
    monkeypatch.setattr(placement, "screens", lambda g: 1 / 0)
    r.tick()
    r.tick()
    assert len([s for s in r.warned if "ZeroDivisionError" in s]) == 1, "once"


def test_a_list_that_cant_say_yet_isnt_every_display_gone(rig, monkeypatch):
    r = rig()
    win = r.slots[0].win
    monkeypatch.setattr(placement, "screens", lambda g: [])     # (all or nothing, mid-change)
    r.g.queue.append(())
    r.tick()
    assert r.slots[0].win == win and r.g.windows[win]["shown"] and r.plug.changed is True


def test_a_published_output_keeps_publishing(rig):
    r = rig()
    pr = r.g.mons[2]
    sl = r.slots[1]
    sl.ndi, sl.publishers = "show", [object()]
    sl.tap = Offscreen(None)
    tap = sl.tap
    r.g.unplug(pr)
    r.tick()
    assert sl.publish_only and sl.drawn and sl.tap is None and sl.offscreen is not None
    assert sl.missing == ""
    r.run_for(HOLD_S + 0.1)
    assert sl.drawn and sl.offscreen is not None and tap.tex is None
    r.g.plug(pr)
    r.run_for(SETTLE_S)
    assert sl.opened and sl.tap is not None and sl.offscreen is None and not sl.publish_only


def test_the_loop_reads_only_live_windows(rig):
    """Closing a window ends the app, but `Hotplug` closes none it has left in a slot; and a window
    it holds is in none (`app._slot_windows`), so the loop's `window_should_close` never sees it."""
    r = rig()
    win = r.slots[0].win
    r.g.unplug(r.g.mons[1])
    r.tick()
    assert win not in app._slot_windows(r.slots)
    assert win in r.plug.windows(), "both exits destroy it"


# ---- review of #425: an accident at a show doesn't cost the show


def _boom(*a, **k):
    raise RuntimeError("the window system says no")


@pytest.mark.parametrize("where", [
    "glfw.hide_window", "glfw.show_window", "glfw.destroy_window", "glfw.create_window", "glfw.set_window_pos",
    "glfw.swap_interval", "glfw.set_window_attrib", "glfw.window_hint",
    "plug._control", "plug._follow", "plug._strays", "plug._after", "plug._publish_follows", "plug._move_control",
    "pacer.choose", "release",
])
def test_a_raise_at_any_step_costs_the_frame_nothing(rig, monkeypatch, where):
    """Through a whole unplug, hold and return with a step raising throughout: every frame, nothing
    the frame holds is dead and the loop's context is current; then, with the fault gone, the
    same job is back by itself."""
    r = rig()
    tv = r.g.mons[1]
    r.run_for(0.5)
    who, name = where.split(".") if "." in where else ("presenter", where)
    owner = {"glfw": r.g, "plug": r.plug, "pacer": r.root.pacer}.get(who)
    if owner is not None:
        monkeypatch.setattr(owner, name, _boom)
    else:
        monkeypatch.setattr(app.Presenter, "release", _boom)
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.5)
    r.g.plug(tv)
    r.run_for(SETTLE_S + 0.5)
    monkeypatch.undo()
    r.run_for(LOOK_S + SETTLE_S + REOPEN_S + 1.0)
    assert r.shown() == {"TV": 1, "Projector": 2}, r.notes
    assert r.main.win == r.slots[0].win and r.root.pacer.owner == r.slots[0].win
    assert r.g.windows[r.slots[0].win]["shown"] is True
    assert not r.plug.held, "no hidden window left over"


def test_a_failing_step_is_tried_once_a_second_not_every_frame(rig, monkeypatch):
    r = rig()
    calls = []
    monkeypatch.setattr(r.plug, "_control", lambda *a: (calls.append(1), _boom())[1])
    r.g.unplug(r.g.mons[1])
    r.run_for(HOLD_S + 0.1)         # the hold has run out, which asks each frame
    n = len(calls)
    r.run_for(3.0)
    assert 1 <= len(calls) - n <= 4, "about one a second"


def test_a_wire_that_fails_is_told_again_next_frame(rig):
    r = rig()
    r.run_for(0.5)
    win = r.slots[0].win
    good, r.plug.wired = r.plug.wired, _boom
    r.strict = False
    r.g.unplug(r.g.mons[1])
    r.run_for(HOLD_S + 0.5)
    assert win not in r.g.windows and win in r.heard
    r.plug.wired = good
    r.tick()
    assert win not in r.heard


def test_a_broken_seen_costs_no_window(rig):
    r = rig()
    r.run_for(1.1)
    win = r.slots[0].win
    r.plug.seen["displays"] = "not a table"
    r.g.unplug(r.g.mons[1])
    r.run_for(HOLD_S + 0.1)
    assert win not in r.g.windows and not r.plug.held


def _pair(rig):
    rows = {"Built-in": row(CONTROL), "TV": row("output.1", fullscreen=True, flip_x=True),
            "Projector": row("output.1", flip_y=True)}
    return rig(mons=[_laptop(), _tv(), _projector()], rows=rows)


def test_a_flap_on_a_first_display_leaves_everything_as_it_was(rig):
    """Output 1 on a big TV and a small monitor, and the TV re-syncs for a second: the first, its
    flips, `output.fullscreen`, the mouse's window, who paces and the frame's size all come back."""
    r = _pair(rig)
    tv = r.g.mons[1]
    sl = r.slots[0]
    r.run_for(0.5)
    first, also = sl.win, sl.also[0].win
    r.root.size = (3840, 2160)
    r.g.unplug(tv)
    r.tick()
    assert sl.win == also, "the other display's picture goes on"
    assert r.root.hold_size, "the frame keeps its size, its first being away a moment"
    assert (sl.switches.flip_x, sl.switches.flip_y) == (False, True)
    r.run_for(1.0)
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert sl.win == first and sl.display == "TV" and [a.win for a in sl.also] == [also]
    assert (sl.switches.flip_x, sl.switches.flip_y) == (True, False)
    assert sl.also[0].flip_y is True and sl.also[0].flip_x is False
    assert r.main.win == first and r.main.fullscreen is True and r.main.mode == "fullscreen"
    assert sl.also[0].output.win == also and sl.also[0].output.fullscreen is False
    assert r.root.pacer.owner == first and r.g.intervals[also] == 0 and r.g.intervals[first] == 1
    assert not r.root.hold_size and first in r.heard
    r.tick()
    assert r.g.get_window_pos(first) == tv.rect[:2], "and covers its display"


def test_past_the_hold_the_promoted_display_stays_first(rig):
    r = _pair(rig)
    tv = r.g.mons[1]
    sl = r.slots[0]
    also = sl.also[0].win
    r.g.unplug(tv)
    r.run_for(HOLD_S + 0.1)
    assert sl.win == also and not r.root.hold_size, "its size now, as SC2 has it"
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert sl.win == also and [a.display for a in sl.also] == ["TV"]


def test_both_of_an_outputs_displays_flapping_come_back_in_order_whichever_returns_first(rig):
    r = _pair(rig)
    tv, pr = r.g.mons[1:]
    sl = r.slots[0]
    r.run_for(0.5)
    first, also = sl.win, sl.also[0].win
    r.g.unplug(tv)
    r.tick()
    r.g.unplug(pr)
    r.tick()
    assert not sl.opened and r.root.hold_size
    r.g.plug(pr)
    r.run_for(SETTLE_S)
    assert sl.win == also and r.root.hold_size
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert sl.win == first and [a.win for a in sl.also] == [also] and not r.root.hold_size


def test_the_control_window_falls_back_to_the_display_it_asked_to_float_on(rig, monkeypatch):
    monkeypatch.setattr(GlfwBackend, "float_over_renders", lambda self, win, on: None)
    # the leftmost is a render too: a projector in the room
    r = rig(mons=[_laptop(), _projector(x=1728), _tv(x=3648)],
            rows={"Built-in": row(CONTROL), "Projector": row("output.2"), "TV": row("output.1", floats_control=True)})
    laptop, _, tv = r.g.mons
    r.g.set_window_pos(r.ctrl, 100, 100)
    r.plug._note_where()
    r.g.unplug(laptop)
    r.run_for(HOLD_S + 0.1)
    assert r.on(r.ctrl, tv) and r.plug.floating


def test_only_output_1s_first_display_asks_for_alpha(rig):
    r = rig(rows={"Built-in": row(CONTROL), "TV": row("output.1"), "Projector": row("output.1")}, overlay=True)
    tv, pr = r.g.mons[1:]
    r.g.unplug(tv, pr)
    r.run_for(HOLD_S + 0.1)
    assert not r.slots[0].opened
    r.g.plug(pr)
    r.run_for(SETTLE_S)
    assert r.g.windows[r.slots[0].win]["hints"]["TRANSPARENT_FRAMEBUFFER"] is True
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert r.g.windows[r.slots[0].also[0].win]["hints"]["TRANSPARENT_FRAMEBUFFER"] is False
    assert r.g.hints["TRANSPARENT_FRAMEBUFFER"] is False


def test_a_change_before_the_callback_goes_in_isnt_missed(rig):
    r = rig()
    assert r.plug.changed is True, "a first look"
    r.g.mons.remove(r.g.mons[2])    # unplugged after `_windows`, before `start`
    two = r.slots[1].win
    r.tick()
    assert not r.slots[1].opened and r.g.windows[two]["shown"] is False


def test_a_row_changed_during_the_hold_is_honoured_and_a_desks_change_kept(rig):
    r = rig(rows={"Built-in": row(CONTROL), "TV": row("output.1"), "Projector": row("output.2")})
    tv = r.g.mons[1]
    sl = r.slots[0]
    win = sl.win
    r.run_for(0.5)
    sl.switches.flip_y = True       # a desk's, on the param: no row knows
    r.g.unplug(tv)
    r.tick()
    r.store.set("TV", flip_x=True, fullscreen=True)
    r.tick()
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert sl.win == win, "the same window"
    assert sl.switches.flip_x is True and r.main.fullscreen is True, "what the panel says"
    assert sl.switches.flip_y is True, "and what the row never touched stands"
    r.tick()
    assert r.main.mode == "fullscreen" and r.g.get_window_pos(win) == tv.rect[:2]


def test_a_drop_and_return_within_one_poll_is_put_right(rig):
    """The list reads the same, and macOS has moved the window onto another display's picture."""
    r = rig(rows={"Built-in": row(CONTROL), "TV": row("output.1"), "Projector": row("output.2")})
    laptop, tv, _ = r.g.mons
    win, two = r.slots[0].win, r.slots[1].win
    r.g.set_window_pos(r.ctrl, 100, 100)
    r.g.set_window_pos(win, 1800, 50)
    r.run_for(1.2)
    # the control window's display too: it's the same fault
    r.g.unplug(tv)
    r.g.plug(tv)
    r.g.windows[r.ctrl]["pos"] = (5000, 40)
    r.g.queue = [()]
    assert r.on(win, laptop)
    r.tick()
    assert r.slots[0].win == win, "no window was torn down, as nothing's gone"
    assert r.on(win, tv) and r.g.get_window_pos(win) == (1800, 50)
    assert two in r.g.windows and r.slots[1].win == two
    assert r.g.get_window_pos(r.ctrl) == (100, 100)


def test_ones_own_pick_isnt_the_other_macs(rig):
    r = rig()
    r.run_for(0.5)
    r.store.set_target("TV", "output.3", ["Built-in", "TV", "Projector"])
    assert r.plug.others_chose() == [], "a frame from being acted on, no warning flashes"
    r.tick()
    assert r.plug.others_chose() == []


def test_a_closed_windows_spot_outlives_a_quit(rig, tmp_path):
    r = rig()
    tv = r.g.mons[1]
    r.g.set_window_pos(r.slots[0].win, 1800, 50)
    r.run_for(1.2)
    r.g.unplug(tv)
    r.tick()
    assert r.plug.away_spots()["TV"][:2] == (1800, 50), "a quit during the hold"
    r.run_for(HOLD_S + 0.1)
    assert r.plug.away_spots()["TV"][:2] == (1800, 50), "and after it"
    scr = placement.screens(r.g)
    home = tmp_path / "saved"
    home.mkdir()
    placement.save(home, None, [None], scr, {}, r.plug.away_spots())
    seen = placement.load(home)
    assert placement.spot(seen, "TV", 1)["x"] == 1800, "though no display here can show it"
    r.g.plug(tv)
    r.run_for(SETTLE_S)
    assert "TV" not in r.plug.away_spots(), "its window has it again"


def test_the_stall_watch_with_windows_coming_and_going():
    """A display gone isn't a stall; a picture that stopped is, and the banner's the only warning."""
    open_now = [("output 1", {"presentable": True}), ("output 2", {"presentable": False})]
    w = RenderWatch(None, limit=2.0, poll=0.0,
                    info=lambda: open_now[0][1] if open_now else {}, outputs=lambda: list(open_now))
    for t in range(4):
        w.drew(float(t))
        w.tick(float(t))
    assert any("output 2" in a for a in w.alerts()), "dark beside another: named"
    # its window closed: it starts afresh when it's back
    open_now[1:] = []
    w.drew(5.0)
    w.tick(5.0)
    assert "output 2" not in w._dark
    w.dismiss()
    open_now.append(("output 2", {"presentable": False}))
    w.drew(6.0)
    w.tick(6.0)
    assert w._dark["output 2"] == 6.0
    # no window at all: drawn is drawn
    open_now.clear()
    for t in range(7, 12):
        w.drew(float(t))
        w.tick(float(t))
    assert not w.stalled
    # the draw stops, with no window: that's a stall, and it's said
    for t in range(12, 16):
        w.tick(float(t))
    assert w.stalled


def test_the_hold_comes_from_the_config(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    (home / "config.toml").write_text('[output]\nunplug_hold_s = 8\n')
    assert config.load()["output"]["unplug_hold_s"] == 8
    (home / "config.toml").write_text('[output]\nunplug_hold_s = "long"\n')
    cfg = config.load()
    assert cfg["output"]["unplug_hold_s"] == HOLD_S and any("unplug_hold_s" in n for n in cfg["notes"])


def test_the_hold_can_be_tuned(rig):
    r = rig(hold_s=0.5)
    win = r.slots[0].win
    r.g.unplug(r.g.mons[1])
    r.run_for(0.6)
    assert win not in r.g.windows


# ---- the labels


def test_labels_with_nothing_held_are_the_arrangements():
    from hyperspace.placement import Screen
    scr = [Screen("TV", 3648, 0, 1920, 1080, (3648, 0), 7), Screen("Built-in", 0, 0, 100, 100, (0, 0), 1),
           Screen("TV", 1728, 0, 1920, 1080, (1728, 0), 2)]
    held: dict = {}
    assert placement.labels(scr, held) == placement.labels(scr) == ["TV #2", "Built-in", "TV #1"]
    assert held == {7: "TV #2", 1: "Built-in", 2: "TV"}
    assert placement.differs(scr, held) == []


def test_a_number_given_away_isnt_claimed_back():
    """A goes, C arrives and takes its number, A returns: two connected twins must never claim one
    number, or a live window changes job by list order, with nobody choosing."""
    from hyperspace.placement import Screen
    a, b = Screen("TV", 0, 0, 10, 10, (0, 0), 1), Screen("TV", 10, 0, 10, 10, (10, 0), 2)
    c = Screen("TV", 20, 0, 10, 10, (20, 0), 3)
    held: dict = {}
    assert placement.labels([a, b], held) == ["TV #1", "TV #2"]
    assert placement.labels([b], held) == ["TV #2"]
    assert placement.labels([b, c], held) == ["TV #2", "TV #1"], "the lowest free"
    assert placement.labels([a, b, c], held) == ["TV #3", "TV #2", "TV #1"], "C keeps it, whatever the order"
    assert placement.labels([c, a, b], held) == ["TV #1", "TV #3", "TV #2"]
    assert len(set(held.values())) == len(held)
    # with its number still free, it takes it back
    held2: dict = {}
    placement.labels([a, b], held2)
    placement.labels([b], held2)
    assert placement.labels([a, b], held2) == ["TV #1", "TV #2"]


def test_a_stand_in_with_no_id_goes_by_place():
    from hyperspace.placement import Screen
    scr = [Screen("TV", 0, 0, 10, 10), Screen("TV", 10, 0, 10, 10)]
    held: dict = {}
    assert placement.labels(scr, held) == ["TV #1", "TV #2"] and held == {}


# ---- the panel


def _lines(r, d):
    said: list[str] = []
    real = imgui.text_colored
    imgui.text_colored = lambda c, t: (said.append(t), real(c, t))[1]
    try:
        d.run(d.wait(1))
    finally:
        imgui.text_colored = real
    return said


def test_the_panel_says_whats_going_on_and_takes_what_the_other_mac_chose(tmp_path, monkeypatch):
    root = tmp_path / "Drive"
    root.mkdir()
    (tmp_path / "home").mkdir()
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        store = DisplayList(root, tmp_path / "home", seed={"Built-in": row(CONTROL)})
        store.sync()
        taken = []
        plug = SimpleNamespace(lines=lambda: ["TV has gone: output 1 waits for it, and the other pictures go on."],
                               others_chose=lambda: [("Built-in", "output.1")], take_others=lambda: taken.append(1))
        scr = [placement.Screen("Built-in", 0, 0, 1728, 1117, (0, 0), 1)]
        run = Running(store, lambda: scr, r.panel.outputs, plug=plug)
        r.panel.displays = run
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        r.reg["ui.page"].set(PAGE_KEYS.index("output"))
        d.run(d.wait(3))
        said = _lines(r, d)
        assert any("TV has gone" in t for t in said)
        assert any(t.startswith(hotplug.OTHER_MAC) and "Built-in" in t for t in said)
        d.run(d.click("display.others"), d.park(), d.wait(2))
        assert taken == [1]
        assert ui_displays.TIP_TAKE


# ---- real GL: the close order on real windows, the real frame


class _RealWindows:
    """The real window system, every window hidden, over a stand-in monitor list."""

    def __init__(self, glfw, mons):
        self.real, self.mons = glfw, list(mons)
        self.callback = None

    def __getattr__(self, name):
        return getattr(self.real, name)

    def get_monitors(self):
        return list(self.mons)

    def get_monitor_workarea(self, m):
        return m.rect

    def get_monitor_pos(self, m):
        return m.rect[:2]

    def get_monitor_name(self, m):
        return m.name.encode()

    def get_cocoa_monitor(self, m):
        return m.uid

    def get_video_mode(self, m):
        return SimpleNamespace(size=SimpleNamespace(width=m.rect[2], height=m.rect[3]))

    def set_monitor_callback(self, fn):
        self.callback = fn

    def create_window(self, w, h, title, mon, share):
        self.real.window_hint(self.real.VISIBLE, False)
        return self.real.create_window(min(w, 320), min(h, 200), title, mon, share)

    def show_window(self, win):
        pass

    def set_window_size(self, win, w, h):
        pass

    def change(self, mons):
        self.mons = list(mons)
        self.callback(None, 0)


@pytest.fixture
def real(gl_window_ok):
    glfw = pytest.importorskip("glfw")
    moderngl = pytest.importorskip("moderngl")
    if not glfw.init():
        pytest.skip("glfw.init failed")
    laptop, tv, pr = _laptop(), _tv(), _projector()
    g = _RealWindows(glfw, [laptop, tv, pr])
    glfw.window_hint(glfw.VISIBLE, False)
    root_win = app._root_window()
    glfw.make_context_current(root_win)
    ctx = moderngl.create_context()
    ctx.gc_mode = "auto"
    root = Root(root_win, Offscreen(ctx), Pacer(glfw))
    ctrl = g.create_window(320, 200, "control", None, root_win)
    yield SimpleNamespace(glfw=glfw, g=g, ctx=ctx, root=root, root_win=root_win, ctrl=ctrl,
                          laptop=laptop, tv=tv, pr=pr)
    gc.collect()
    glfw.destroy_window(ctrl)
    glfw.destroy_window(root_win)
    glfw.default_window_hints()
    glfw.terminate()


def _real_plug(real, tmp_path, monkeypatch, slots, rows=ROWS):
    (tmp_path / "Drive").mkdir(exist_ok=True)
    store = DisplayList(tmp_path / "Drive", None, seed=rows)
    store.sync()
    run = Running(store, lambda: plug.screens, slots)
    main = Output(None, GlfwBackend(real.g), allowed=False)
    slots[0].output = main
    plug = Hotplug(real.g, run, real.root, real.ctrl, main, hold_s=0.0)
    plug.start()
    return plug


def _rig_look(ctx):
    import golden_frames as gf

    rig = gf.Rig("party-tumble", "absent", ctx)
    rig.renderer.max_frame = None
    rig.view.integrate = lambda dt: None    # the same picture every frame: a change is a fault
    rig.t0 = rig.t
    return rig


def _proxy(rig):
    def draw(_s, w, h, dpr, views):
        rig.t = rig.t0
        rig.frame(views, (w, h), dpr)

    return SimpleNamespace(bg_alpha=rig.renderer.bg_alpha, max_frame=rig.renderer.max_frame, draw_outputs=draw)


def _px(fbo):
    w, h = fbo.size
    return np.frombuffer(fbo.read(viewport=(0, 0, w, h), components=4), dtype=np.uint8).reshape(h, w, 4).copy()


def test_a_close_leaves_every_array_of_the_roots(real, tmp_path, monkeypatch):
    """The close order, on real GL. **This can't catch a wrong order on this Mac,** which was tried:
    Apple's driver numbers vertex arrays from one table across a share group (a root's are 1-4 and
    7-10 where a presenter's are 5, 6), so no root array shares a presenter's number, and the
    spike's `same_name_on_root_alive_after: false` was the presenter's own number going. GL's
    spec makes names per context, so another driver can have the fault: the order stays, and
    the stand-in's order test holds it. This holds what's true here: the numbers don't meet, and
    a close takes none of the root's."""
    from OpenGL import GL

    monkeypatch.setattr(app, "glfw", real.glfw)
    slots = [Slot(n) for n in (1, 2, 3, 4)]
    plug = _real_plug(real, tmp_path, monkeypatch, slots)
    prog = real.ctx.program(vertex_shader="#version 330\nvoid main(){gl_Position=vec4(0.0);}")
    keep = [real.ctx.vertex_array(prog, []) for _ in range(4)]
    plug.between_frames(1000.0)     # (the first look, then the list has held still)
    plug.between_frames(1000.5)
    two = slots[1]
    real.glfw.make_context_current(two.win)
    two.presenter._build()
    mine = {two.presenter._vao.glo, two.presenter._dim_vao.glo}
    real.glfw.make_context_current(real.root_win)
    keep += [real.ctx.vertex_array(prog, []) for _ in range(4)]
    names = {v.glo for v in keep}
    if sys.platform == "darwin":
        assert not names & mine, "if these ever meet, this test can catch the order: make it"
    real.g.change([real.laptop, real.tv])
    plug.between_frames(1001.0)
    plug.between_frames(1002.0)
    assert not two.opened and not plug.held
    real.glfw.make_context_current(real.root_win)
    assert all(GL.glIsVertexArray(n) for n in names)


def test_a_flap_on_a_first_display_holds_the_frame_and_shows_it_on_the_other(real, tmp_path, monkeypatch):
    """Output 1 on two displays of different shapes: while the first is away the other shows the
    frame in its own shape, at the size it was, and after, all is as it was."""
    monkeypatch.setattr(app, "glfw", real.glfw)
    rows = {"Built-in": row(CONTROL), "TV": row("output.1"), "Projector": row("output.1")}
    slots = [Slot(n) for n in (1, 2, 3, 4)]
    plug = _real_plug(real, tmp_path, monkeypatch, slots, rows)
    plug.hold_s = 100.0
    rig = _rig_look(real.ctx)
    plug.between_frames(1000.0)     # (the first look, then the list has held still)
    plug.between_frames(1000.5)
    sl = slots[0]
    first, other = sl.win, sl.also[0].win
    real.glfw.set_window_size(other, 160, 100)
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    big = tuple(real.root.size)
    want = _px(real.root.frame.fbo)
    real.g.change([real.laptop, real.pr])
    plug.between_frames(1001.0)
    assert sl.win == other and real.root.hold_size
    seen = []
    real_present = sl.presenter.present
    sl.presenter.present = lambda ho, size, target=None: (seen.append((ho.rect, tuple(size))), real_present(ho, size, target))[1]
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    assert tuple(real.root.size) == big and not sl.error
    small = tuple(real.glfw.get_framebuffer_size(other))
    assert seen and seen[0][1] == small and seen[0][0] == app.fit(big, small), "its own shape"
    assert np.array_equal(_px(real.root.frame.fbo), want)
    real.g.change([real.laptop, real.tv, real.pr])
    plug.between_frames(1002.0)
    plug.between_frames(1003.0)
    assert sl.win == first and sl.also[0].win == other and not real.root.hold_size
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    assert tuple(real.root.size) == big and np.array_equal(_px(real.root.frame.fbo), want)
    assert real.root.pacer.owner is first
    rig.close()


def test_a_flap_doesnt_resize_output_1s_frame(real, tmp_path, monkeypatch):
    """Output 1's display dropped: another's size doesn't take over during the hold, so no look's
    buffers resize for a re-sync. Past the hold, as SC2 has it, the first that shows anything's."""
    monkeypatch.setattr(app, "glfw", real.glfw)
    slots = [Slot(n) for n in (1, 2, 3, 4)]
    plug = _real_plug(real, tmp_path, monkeypatch, slots)
    plug.hold_s = 100.0
    rig = _rig_look(real.ctx)
    plug.between_frames(1000.0)     # (the first look, then the list has held still)
    plug.between_frames(1000.5)
    real.glfw.set_window_size(slots[1].win, 160, 100)
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    big = tuple(real.root.size)
    real.g.change([real.laptop, real.pr])
    plug.between_frames(1001.0)
    assert real.root.hold_size
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    assert tuple(real.root.size) == big and slots[1].presenter.presented == 2
    plug.between_frames(1200.0)
    assert not real.root.hold_size and plug.held == []
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    assert tuple(real.root.size) == tuple(real.glfw.get_framebuffer_size(slots[1].win)) != big
    rig.close()


def test_many_cycles_through_the_close_order_keep_the_picture(real, tmp_path, monkeypatch):
    """Output 1's and output 2's displays out and in, each cycle a real window and context made
    and let go, with the real `_draw_render` between: the root's objects survive (the trap: a
    release with the root current deleted its vertex array of the same name) and the picture on
    the root's frame is the same picture byte for byte."""
    monkeypatch.setattr(app, "glfw", real.glfw)
    slots = [Slot(n) for n in (1, 2, 3, 4)]
    plug = _real_plug(real, tmp_path, monkeypatch, slots)
    laptop, tv, pr = real.laptop, real.tv, real.pr
    rig = _rig_look(real.ctx)
    t = 1000.0

    def step():
        nonlocal t
        t += 1.0
        plug.between_frames(t)
        t += 1.0
        plug.between_frames(t)
        app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)

    real.g.change([laptop, tv, pr])
    plug._settle_at = t
    step()
    assert slots[0].opened and slots[1].opened and real.root.pacer.owner is slots[0].win
    size = tuple(real.root.size)
    assert slots[0].presenter.presented == 1
    want = _px(real.root.frame.fbo)
    assert want[..., :3].max() > 8
    for i in range(12):
        first = slots[0].win
        real.g.change([laptop, pr])
        step()
        assert not slots[0].opened and slots[1].opened and real.root.pacer.owner is slots[1].win
        assert slots[1].presenter.presented >= 1 and not slots[1].error
        assert tuple(real.root.size) != (0, 0)
        if tuple(real.root.size) == size:
            assert np.array_equal(_px(real.root.frame.fbo), want), i
        real.g.change([laptop, tv, pr])
        step()
        assert slots[0].opened and slots[0].win is not first, "a new window"
        assert not slots[0].error and slots[0].presenter.presented == 1
        assert real.root.pacer.owner is slots[0].win
        assert np.array_equal(_px(real.root.frame.fbo), want), i
    assert real.ctx.error == "GL_NO_ERROR"
    real.g.change([])
    t += 1.0
    plug.between_frames(t)
    plug.between_frames(t + 1.0)
    assert not any(sl.opened for sl in slots) and plug.held == []
    app._draw_render(_proxy(rig), real.ctx, rig.view, slots, real.root)
    assert np.array_equal(_px(real.root.frame.fbo), want), "and with no display at all"
    rig.close()
