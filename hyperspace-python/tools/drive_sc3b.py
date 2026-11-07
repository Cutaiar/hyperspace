"""tools/app_driver.py's script for SC3b: the real app, and a real display coming and going.

The display is `tools/sc3a_spike.py vdisplay`, a private `CGVirtualDisplay` in a helper process:
the window server's real thing, added and removed, with no cable. **It opens windows on this
Mac's real displays and may leave an arrangement entry, so run it as few times as you need, and
check the monitor list before and after.** It proves the app's half. Only a real cable proves the
rest (hand check 629). Run from `hyperspace-python/`, checking `tools/sc3a_spike.py state` first:

    uv run python tools/app_driver.py tools/drive_sc3b.py --out <scratch>/run --every 30 --home <scratch>/home

Each step's words go to stderr, a step that doesn't do what it should stops the run, and the numbers
go to `<cwd>/sc3b.json`, or `SC3B_JSON`. Touches no `~/Hyperspace`: `--home` is its library.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import glfw
import numpy as np

from hyperspace.displays import CONTROL, NOTHING
from hyperspace.placement import memory
from hyperspace.ui import PAGE_KEYS

NAME = "sc3a spike"
SPIKE = str(Path(__file__).resolve().parent / "sc3a_spike.py")
HOLD_SECS = "600"


def say(*a):
    print("sc3b:", *a, file=sys.stderr, flush=True)


def _helper():
    return subprocess.Popen([sys.executable, SPIKE, "vdisplay", "--secs", HOLD_SECS, "--hz", "60"],
                            stdout=subprocess.DEVNULL)


def _gone(p):
    p.kill()
    p.wait()


def _screen_of(win):
    """Which display the window server says the window is on."""
    import objc

    ns = objc.objc_object(c_void_p=glfw.get_cocoa_window(win))
    return str(ns.screen().localizedName()) if ns.screen() is not None else None


def _watched(d, panel, until, secs, times, what):
    """Frames until `until()` holds, each frame's length kept. A stop at `secs`."""
    end = time.perf_counter() + secs
    last = time.perf_counter()
    swaps = panel.outputs[0].presenter.presented if panel.outputs[0].presenter else 0
    while not until():
        if time.perf_counter() > end:
            raise AssertionError(f"{what}: not within {secs} s; {panel.displays.plug.lines()}")
        yield
        now = time.perf_counter()
        times.append((now - last) * 1000.0)
        last = now
    return swaps


def _stats(times):
    t = np.array(times or [0.0])
    return {"frames": len(times), "p50": round(float(np.median(t)), 2), "max": round(float(t.max()), 2),
            "over_50ms": int((t > 50).sum())}


def _tag(run):
    tags = run.labels(run.plug.screens)
    return next((t for t in tags if memory(t) == NAME), None)


def _all_real(run):
    return [t for t in run.labels(run.plug.screens) if memory(t) != NAME]


def script(d, panel):
    run = panel.displays
    plug = run.plug
    out = {"monitors_before": [s.name for s in plug.screens], "steps": {}, "locked": _locked()}
    say("monitors before", out["monitors_before"])
    panel.library.load("presets", "party-tumble")
    panel.reg["ui.page"].set(PAGE_KEYS.index("output"))     # (the section's words, in the captures)
    yield from d.wait(20)
    one = panel.outputs[0]
    two = panel.outputs[1]
    say("output 1 on", one.display, "control on", plug._ctrl_on, "pacing by output 1:", plug.root.pacer.owner is one.win)
    base = []
    for _ in range(240):
        t0 = time.perf_counter()
        yield
        base.append((time.perf_counter() - t0) * 1000.0)
    out["steps"]["nothing plugged"] = _stats(base)

    # ---- a display arrives, unknown: it waits, with no target
    helper = _helper()
    times = []
    yield from _watched(d, panel, lambda: _tag(run) is not None, 8.0, times, "the display arrives")
    uid_line = _uid(plug)
    say("arrived", uid_line, "after frames", len(times))
    wait_times = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 1.0:
        yield
        wait_times.append(0.0)
    assert not two.opened, "an unknown display waits"
    out["steps"]["arrives unknown"] = {**_stats(times), "uid": uid_line, "opened": False}

    # ---- chosen: it acts at once
    tag = _tag(run)
    before = len(plug.times)
    run.store.set_target(tag, "output.2", [tag])
    times = []
    yield from _watched(d, panel, lambda: two.opened, 2.0, times, "chosen, it opens")
    yield from d.wait(30)
    assert _screen_of(two.win) == NAME, _screen_of(two.win)
    assert two.presenter.presented > 10 and not two.error
    say("output 2 on it:", plug.times[before:], "frames", _stats(times))
    out["steps"]["chosen"] = {**_stats(times), "cost": plug.times[before:], "window_on": _screen_of(two.win)}
    win2 = two.win

    # ---- it goes: hidden at once, the hold, closed; the picture on the real display goes on
    drew = one.presenter.presented if one.presenter else 0
    t_off = time.perf_counter()
    _gone(helper)
    times = []
    yield from _watched(d, panel, lambda: _tag(run) is None, 8.0, times, "it goes")
    hidden_after = time.perf_counter() - t_off
    assert not two.opened and plug.held and not glfw.get_window_attrib(win2, glfw.VISIBLE), "hidden, whole"
    say("gone, hidden, after", round(hidden_after, 3), "s; pacer on output 1:", plug.root.pacer.owner is one.win)
    out["steps"]["goes"] = {**_stats(times), "hidden_after_s": round(hidden_after, 3),
                            "window_moved_to": _screen_of(win2)}
    times = []
    before = len(plug.times)
    yield from _watched(d, panel, lambda: not plug.held, plug.hold_s + 3.0, times, "the hold ends")
    assert not two.opened and two.missing, two.missing
    if one.presenter:
        assert one.presenter.presented > drew, "the picture on the real display went on"
    say("closed after the hold;", plug.times[before:], _stats(times), "banner:", panel.render_watch.alerts())
    out["steps"]["hold"] = {**_stats(times), "cost": plug.times[before:], "alerts": list(panel.render_watch.alerts())}
    # (locked, the window server calls every window covered, and one left is a "stall": the watch's
    # job, and true of a locked Mac. Unlocked, a display gone mustn't raise it)
    if not _locked():
        assert not panel.render_watch.stalled, panel.render_watch.stalled

    # ---- it returns: the same job
    helper = _helper()
    before = len(plug.times)
    times = []
    yield from _watched(d, panel, lambda: two.opened, 8.0, times, "it comes back")
    yield from d.wait(30)
    uid_back = _uid(plug)
    assert _screen_of(two.win) == NAME and two.win is not win2, "a new window, on it"
    assert two.presenter.presented > 10
    say("back:", uid_back, plug.times[before:], _stats(times))
    out["steps"]["returns"] = {**_stats(times), "uid": uid_back, "cost": plug.times[before:],
                               "same_id_as_before": uid_back == uid_line}

    # ---- a flap: gone and back inside the hold, the helper's start being the gap
    win2, presenter2 = two.win, two.presenter
    _gone(helper)
    helper = None
    times = []
    yield from _watched(d, panel, lambda: _tag(run) is None, 8.0, times, "the flap's going")
    helper = _helper()
    yield from _watched(d, panel, lambda: two.opened, 8.0, times, "the flap's return")
    yield from d.wait(30)
    assert two.win is win2 and two.presenter is presenter2, "the same window: nothing torn down"
    assert _screen_of(two.win) == NAME and glfw.get_window_attrib(win2, glfw.VISIBLE)
    say("flap: same window", _stats(times))
    out["steps"]["flap"] = {**_stats(times), "same_window": True}

    # ---- the control window on it, then gone: it moves, and comes back
    tag = _tag(run)
    run.store.set_target(tag, CONTROL, _all_real(run) + [tag])
    times = []
    yield from _watched(d, panel, lambda: not two.opened and plug._ctrl_on == memory(tag), 2.0, times, "control on it")
    ctrl = _ctrl_win(plug)
    yield from d.wait(10)
    assert _screen_of(ctrl) == NAME, _screen_of(ctrl)
    _gone(helper)
    helper = None
    times = []
    yield from _watched(d, panel, lambda: plug._ctrl_on != memory(tag), plug.hold_s + 4.0, times, "the control window moves")
    yield from d.wait(10)
    moved_to = _screen_of(ctrl)
    assert moved_to and moved_to != NAME
    say("control window moved to", moved_to, plug.lines(), "floating", plug.floating)
    out["steps"]["control goes"] = {**_stats(times), "to": moved_to, "floating": plug.floating}
    helper = _helper()
    times = []
    yield from _watched(d, panel, lambda: plug._ctrl_on == memory(tag), 8.0, times, "the control window back")
    yield from d.wait(10)
    assert _screen_of(ctrl) == NAME
    say("control window back", _stats(times))
    out["steps"]["control returns"] = _stats(times)
    # leave the shared memory as it found it, and the display gone
    run.store.set_target(_tag(run), NOTHING, [_tag(run)])
    yield from d.wait(10)
    _gone(helper)
    times = []
    yield from _watched(d, panel, lambda: plug._ctrl_on != memory(tag), plug.hold_s + 4.0, times, "the control window leaves")
    yield from d.wait(10)
    out["monitors_after"] = [s.name for s in plug.screens]
    say("monitors after", out["monitors_after"], "floating", plug.floating, "on", plug._ctrl_on)
    out["slots"] = [(sl.n, sl.display, sl.missing) for sl in panel.outputs]
    out["notes"] = [n for n in plug.notes if n.startswith("displays")][-12:]
    with open(os.environ.get("SC3B_JSON", "sc3b.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)


def _locked():
    import Quartz

    return bool((Quartz.CGSessionCopyCurrentDictionary() or {}).get("CGSSessionScreenIsLocked"))


def _uid(plug):
    return next(s.uid for s in plug.screens if s.name == NAME)


def _ctrl_win(plug):
    return plug.ctrl_win
