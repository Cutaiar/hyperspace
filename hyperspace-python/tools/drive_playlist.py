"""tools/app_driver.py script: the playlist in the real app, by mouse, with what it costs
(plan 44 D6b). Writes a list (one entry a missing patch), opens the pane's section, plays
it twice round on a short dwell, and measures: each load, each warm draw, the frame times
in a dwell against a fade's, and its first frame. Then a soak of quick advances, watching
the resident size, the params and the undo stacks. Says it all on stderr.

    uv run python tools/app_driver.py tools/drive_playlist.py --out <scratch>/run --every 200
"""

import ctypes
import os
import statistics
import sys
import threading
import time
import traceback

from hyperspace import playlist
from hyperspace.playlist import Entry, Playlist
from hyperspace.ui import PAGE_KEYS

LOOKS = ("party-trip", "party-acid", "party-wake", "party-noita", "party-tracer", "party-field",
         "party-mandala", "party-faces")
SOAK = int(os.environ.get("PLAYLIST_SOAK", "80"))      # advances
ROUNDS = int(os.environ.get("PLAYLIST_ROUNDS", "2"))
SLOW_MS = 40.0
QUIET_S = 20.0     # no step of the script for this long is a wedge
STUCK_S = 30.0     # the script stepping, and no advance for this long, is one too


def footprint() -> str:
    """The physical footprint the kernel keeps for this process (GL's memory too), by
    `proc_pid_rusage`: no tool attaches, so nothing stalls the frame it is read in. `vmmap`
    suspends the process, reads in 0.1 GB steps and does not repeat itself."""
    info = (ctypes.c_uint64 * 32)()
    libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
    if libproc.proc_pid_rusage(os.getpid(), 0, info):       # RUSAGE_INFO_V0
        return "?"
    return f"footprint {info[9] / (1 << 20):.0f} MB"        # after the uuid and seven counters


def ms(values) -> str:
    v = sorted(values)
    return (f"n {len(v)}, median {statistics.median(v):.1f} ms, worst {v[-1]:.1f} ms"
            if v else "n 0")


def timed(obj, name, into):
    """`obj.name` with its calls timed into `into`."""
    real = getattr(obj, name)

    def call(*a, **k):
        t = time.perf_counter()
        got = real(*a, **k)
        into.append((time.perf_counter() - t) * 1000)
        return got
    setattr(obj, name, call)


def state(panel) -> str:
    p, meta, fade, lib = panel.playing, panel.meta, panel.fade, panel.library
    return (f"on {p.on}, at {p.at}, lost {p.lost}, armed {p.armed}, mixing {meta.mixing}, timed "
            f"{meta.timed}, fader {meta.mix.xfade:.3f}, warm_deck {fade.warm_deck}, warm_error "
            f"{fade.warm_error!r}, load_at in {p.load_at - p.last:.1f} s; warning {lib.warning!r}; "
            f"status {lib.status!r}")


def watch(panel, seen: dict) -> None:
    """No step of the script for `QUIET_S`: the script runs from `Panel.draw`, so one that raises
    each frame leaves the app looping under the frame guard, the room playing and the script
    dead, and no deadline in the script can see it. Says what it can, and ends the run."""
    while True:
        time.sleep(1.0)
        if time.perf_counter() - seen["at"] > QUIET_S:
            print(f"WEDGED: no step for {QUIET_S} s: {state(panel)}; draw raised {seen['raised']}",
                  file=sys.stderr, flush=True)
            os._exit(3)


def script(d, panel):
    p, meta, fade, lib = panel.playing, panel.meta, panel.fade, panel.library
    panel.render_watch = None
    assert meta.playing is p
    seen = {"at": time.perf_counter(), "raised": 0}
    draw = type(panel).draw

    def drawn(self, dt, fps):
        try:
            draw(self, dt, fps)
        except Exception:
            if not seen["raised"]:
                print("WEDGED: Panel.draw raised:", file=sys.stderr)
                traceback.print_exc()
            seen["raised"] += 1
            raise
        seen["at"] = time.perf_counter()
    type(panel).draw = drawn
    threading.Thread(target=watch, args=(panel, seen), daemon=True).start()
    loads, warms = [], []
    timed(p, "_load", loads)
    real_warm = fade.warm

    def warm(*a, **k):
        t = time.perf_counter()
        drew = real_warm(*a, **k)
        if drew:
            warms.append((time.perf_counter() - t) * 1000)
        return drew
    fade.warm = warm

    playlist.save(lib, Playlist("cart", [Entry("party-trip", 3.0, 1.0),
                                         Entry("not-a-patch", 3.0),
                                         *[Entry(n, 3.0, 1.0) for n in LOOKS[1:]]]))
    yield from d.wait(5)
    assert p.select("cart")
    panel.reg["ui.page"].set(PAGE_KEYS.index("playlist"))     # the pane's view
    yield from d.wait(30)         # the section, for the shot
    yield from d.click("chip.playlist.play", frames=3)
    assert p.on

    dwell, fading, first = [], [], []
    last = time.perf_counter()
    was_fading = False
    went = []
    at = None
    rounds = ROUNDS * len(LOOKS)
    moved = time.perf_counter()
    while len(went) < rounds:
        yield
        if time.perf_counter() - moved > STUCK_S:
            print(f"WEDGED: no advance for {STUCK_S} s: {state(panel)}", file=sys.stderr, flush=True)
            os._exit(4)
        now = time.perf_counter()
        step = (now - last) * 1000
        last = now
        running = meta.mixing
        if step > SLOW_MS:
            look = p.playlist.entries[p.at].loadable if p.at is not None else "-"
            print(f"slow frame {step:.0f} ms: {look}, fader {meta.mix.xfade:.3f}, "
                  f"round {len(went) // len(LOOKS) + 1}, fade {'on' if running else 'off'}", file=sys.stderr)
        if running and not was_fading:
            first.append(step)
        elif running:
            fading.append(step)
        elif not was_fading:
            dwell.append(step)
        was_fading = running
        if p.at != at:
            at, moved = p.at, time.perf_counter()
            print(f"advance {len(went) + 1}, {time.perf_counter():.1f} s: {footprint()}", file=sys.stderr)
            went.append((p.playlist.entries[at].loadable, meta.deck_name(meta.off_air),
                         meta.off_air.loaded_patch.current))
    print("the looks, as each fade began (name, deck coming in, its current):", file=sys.stderr)
    for row in went:
        print("  ", row, file=sys.stderr)
    print(f"warnings: {lib.warning}", file=sys.stderr)
    print(f"load (each):             {ms(loads)}", file=sys.stderr)
    print(f"warm draw (each):        {ms(warms)}", file=sys.stderr)
    print(f"frame in a dwell:        {ms(dwell)}", file=sys.stderr)
    print(f"frame in a fade:         {ms(fading)}", file=sys.stderr)
    print(f"a fade's first frame:    {ms(first)}", file=sys.stderr)
    print(f"on air {meta.deck_name(meta.on_air)}; panel {meta.deck_name(meta.panel)}", file=sys.stderr)
    print(f"fade errors: {fade.error!r}; warm: {fade.warm_error!r}", file=sys.stderr)

    # the soak: quick advances, what grows
    p.stop()
    yield from d.wait(120)
    playlist.save(lib, Playlist("soak", [Entry(n, 2.2, 0.2) for n in LOOKS]))
    assert p.select("soak")
    p.play()
    done = 0
    at = None
    print(f"soak start: {footprint()}, params {len(meta.decks[0].reg)}+{len(meta.decks[1].reg)}, "
          f"stacks {[len(s.stack) for s in meta.stacks]}", file=sys.stderr)
    moved = time.perf_counter()
    while done < SOAK:
        yield
        if time.perf_counter() - moved > STUCK_S:
            print(f"WEDGED: no advance for {STUCK_S} s: {state(panel)}", file=sys.stderr, flush=True)
            os._exit(4)
        if p.at != at:
            at, moved = p.at, time.perf_counter()
            done += 1
            if done % 20 == 0:
                print(f"soak {done}: {footprint()}, params {len(meta.decks[0].reg)}+"
                      f"{len(meta.decks[1].reg)}, stacks {[len(s.stack) for s in meta.stacks]}",
                      file=sys.stderr)
    p.stop()
    print(f"end of the soak: {footprint()}", file=sys.stderr)
    for k in range(int(os.environ.get("PLAYLIST_IDLE", "3"))):   # the control: nothing happening
        yield from d.wait(1200)
        print(f"idle, {(k + 1) * 1200} frames on: {footprint()}", file=sys.stderr)
