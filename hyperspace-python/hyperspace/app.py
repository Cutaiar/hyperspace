"""Hyperspace entry point — GLFW windows in one GL share group.

The *render* window is pure moderngl output, the thing on the projector or
TV: no imgui in it, ever. With ``[[output.screens]]`` in config.toml
(plan 21 WP3) there is one render window per listed output. A hidden *root*
window holds the context the frame is rendered on, which no unplugged display can
take (SC3a, plan 58); every output's window shows the frame through an
`outputs.Presenter` in its own context (`_draw_render`), and the first live one's
swap paces the loop (`pacing.py`). The *control* window holds every widget — the
CONTROLS panel, the cheat sheet, the hot-reload error toast — in its own
imgui context and GlfwRenderer. Keys are polled, not callback-driven, so
they work from whichever window is focused (the control window defers to
imgui while it is typing); the mouse orbits, pans and zooms in the render
window only. overlay.py owns where the render window goes (screen,
fullscreen, overlay) through the output.* params. ``hyperspace --laptop``
(or ``--single``) launches for one screen with no projector (config.laptop).

  ← / →  shape      space  pause      P  points     R  reset view
  [ / ]  brightness , / .  speed      1–6  planes   H  panel
  M  mic on/off     K  play/pause     0  restart    Q  quit
  Cmd+R  restart the whole process (same terminal, cold reload)
  ↑ / ↓  4D perspective — holding accelerates toward the range limit
  drag  orbit       ⇧drag / right-drag  pan   scroll  zoom about cursor
  L  lines          F  faces          ?  cheat sheet
  T  overlay: float the render over the screen    G  clicks through it
     (only with [output] overlay = true in config.toml — decision 21)
  F1–F8  load a loadable patch of the bank               ⇧F1–F8  save the live state as it
  B  tap tempo      ⇧B  LFO trigger: the downbeat is now, synced LFOs restart
  Cmd+Z / Ctrl+Z  undo the last gesture or load here  with ⇧  redo (undo.py)

Every input path — keys, the Xbox-layout gamepad, a MIDI controller, the
analyzer's lanes — is one binding table over the parameter registry
(params.py, routing.py): a row names a source, a param id and an
operation, nothing touches state directly. The table is bindings.json
(factory default in routing.py; MIDI rows editable from the panel by
right-click → Learn). The mouse, the sticks and ↑/↓ are the one thing
outside the table — relative writers — and they nudge a param's *base*
(Param.nudge / scale), so a performer's offset rides on the move rather
than folding into it.

The in-app cheat sheet (ui.CHEATSHEET) is the canonical human list;
tests/test_ui_shell.py checks it against the tables and LOOP_KEYS below.

The engine hot-reloads (hotreload.py): save a module on its watch list
(hotreload.MODULES) while the app runs and live objects pick the code up
in place; modules not listed need a restart; a broken
save keeps the last good version and shows the error in the control
window. This file is the one cold piece — its loop is on the stack — so
keep it thin: put anything you'll want to iterate on live in the modules
it calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

# pyGLFW and imgui_bundle each ship a libglfw; loading both trips ObjC class
# collisions on macOS. Point pyGLFW at imgui_bundle's copy before it loads.
if "PYGLFW_LIBRARY" not in os.environ:
    _spec = importlib.util.find_spec("imgui_bundle")
    if _spec and _spec.origin:
        _dylib = Path(_spec.origin).parent / "libglfw.3.dylib"
        if _dylib.exists():
            os.environ["PYGLFW_LIBRARY"] = str(_dylib)

import glfw
import moderngl
import numpy as np
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

from . import (
    config,
    devices,
    gamepad,
    grip,
    lfo,
    node_desk,
    placement,
    playlist,
    poi,
    replay,
    sharedfile,
    tempo,
    totem,
    ui_browse,
)
from . import ghost as ghosts
from . import undo as undos
from . import world as worlds
from .audio import AudioEngine
from .bands import CEIL
from .control import Control
from .deck import KEYS, MOUSE, Deck, DeckHooksMade, Fade, MetaController, Mix, register_xfade
from .devicelist import DeviceList
from .displays import COPY as DISPLAYS_COPY
from .displays import FILE as DISPLAYS_FILE
from .displays import DisplayList, Running, Wanted, opened_of, wanted
from .geometry import EYE_DISTANCE, EYE_FOV, px_per_unit
from .hotplug import Hotplug
from .hotreload import HotReloader
from .learn import Learn
from .library import Library
from .library import home as library_home
from .media import pool as media_pool
from .media import proxy as media_proxy
from .media import publish
from .media.channels import Channels, MediaState
from .media.folder import MediaFolder
from .media.panel import GRAPH as PANEL_GRAPH
from .media.panel import PanelSource
from .midiports import port_names
from .outputs import (
    FRAME_SAMPLES,
    MAX_OUTPUTS,
    Also,
    CanvasTap,
    Handoff,
    Offscreen,
    Presenter,
    Preview,
    Root,
    Slot,
    Switches,
    View,
    fit,
)
from .overlay import RENDER_DEFAULT, GlfwBackend, Output, register_switches, render_index
from .pacing import Pacer
from .params import Registry, build_meta
from .pinch import install as install_pinch
from .players import Players
from .pointer import Pointer, Through
from .render import Renderer
from .routing import SLEW_DEFAULT_S, Bindings, Router, bindings_path, register_desk
from .ui import Panel, apply_style, go_view, load_fonts, view_of
from .view import ViewState
from .watchdog import LOG_NAME, RenderWatch, Watchdog

TITLE = "Hyperspace"
# the library's name when config.toml didn't read and nothing says where it is: never a
# folder, so nothing is listed and every save is refused in words (`Library.missing`)
CONFIG_UNREAD = "(config.toml did not read)"
RENDER_SIZE = (1280, 820)
ROOT_SIZE = (64, 64)     # the hidden window that holds the render context: never drawn on
# two 4:3 panes side by side: the desk diagram on the left, the panel on
# the right, the same size (ui.panel_w splits it). 900 tall is what every
# page is laid out to fit; on a screen narrower than this the window opens
# as wide as the screen and the desk gives up the width (placement.default_rect)
CONTROL_SIZE = (2372, 900)

# 4D perspective hold keys move depth4 in the taper's own log space —
# octaves of (depth − 1) — so travel feels even across the whole throw.
# The rate eases in quadratically from a tap-sized nudge to full speed.
D4_RATE0 = 0.45   # octaves/s at the instant of the press
D4_RATE1 = 3.6    # octaves/s once the ramp completes
D4_RAMP = 1.8     # seconds of hold to reach full rate

# the key / pad / MIDI / lane binding tables live in routing.py (bindings.json);
# these are the keys the loop still handles itself (the cheat-sheet test reads
# it). R and F1–F8 / ⇧F1–F8 are table rows since plan 11 (routing.LOOP_KEY_ROWS).
LOOP_KEYS = ("SUPER+R", "SUPER+LEFT_BRACKET", "SUPER+RIGHT_BRACKET",
             "UP", "DOWN", "Q")


def _err(where: str, e: Exception) -> str:
    return f"{where}: {type(e).__name__}: {e}"[:160]


# ---- Ctrl-C (2026-11-11) ----

QUIT_GRACE_S = 2.0      # a second Ctrl-C this long after the first: out now, teardown or no


@dataclass
class Quit:
    """What a Ctrl-C asked for: `at` is when the first signal arrived."""

    at: float | None = None

    @property
    def asked(self) -> bool:
        return self.at is not None


def _exit_now() -> None:
    """The escape hatch: no teardown, no traceback, 130 — a shell's own code
    for a Ctrl-C."""
    print("quit: forced", file=sys.stderr, flush=True)
    os._exit(130)       # every exit hook skipped: that is the point


def _install_quit_signals(quitting: Quit | None = None, *, clock=time.perf_counter,
                          hard=_exit_now) -> Quit:
    """Ctrl-C asks the loop to quit; it never unwinds the stack.

    With no handler, SIGINT raises KeyboardInterrupt wherever the signal
    lands — mid-frame, inside a draw — and `main` dies with a traceback,
    every window, the audio stream and the devices still open and the
    window placement unsaved. A handler instead sets `Quit.at`, and the
    loop leaves by the door a window close uses, so the one teardown runs
    (`close_all`, audit P1). SIGTERM is the same: `uv run`, a launchd job
    or a terminal closing is a quit, not a kill.

    A further signal `QUIT_GRACE_S` after the first is for a teardown that
    wedges: out now. One inside that window is a double tap, and is ignored.

    Call it again with the same `Quit` to re-register the handlers, in case
    something opened in between installed its own.
    """
    quitting = Quit() if quitting is None else quitting

    def handler(signum, frame) -> None:      # the signal module's shape
        now = clock()
        if quitting.at is None:
            quitting.at = now
        elif now - quitting.at >= QUIT_GRACE_S:
            hard()

    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, handler)
        except (OSError, ValueError):     # not the main thread; the loop is, so not the app
            pass
    return quitting


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001, S110 — teardown is best-effort
        pass


def _close_each(closes) -> None:
    """Every one of `closes` called, whichever raises: one output's or deck's
    teardown never leaves another's open (plan 44 D4: deck 2's segment workers
    outlive a raise in deck 1's close otherwise)."""
    for close in closes:
        _quiet(close)


@dataclass
class _Closer:
    """Something `close_all` closes that is a function, not an object."""

    fn: Callable[[], None]

    def close(self) -> None:
        self.fn()


def close_all(audio, *adapters) -> None:
    """Every optional adapter's `close()` — the device registry (every
    device, the pad included; plan 27 B1), the dream worker — then the
    audio stream, best-effort, so a broken port never blocks a quit or a
    restart. The one list for both exits (audit P1); `None` for an
    adapter that was never opened. Plan 32 (final review A-m1): the
    closes share one deadline, `media.pool.EXIT_S` from here — each waits
    what is left of it at most."""
    _quiet(media_pool.begin_exit)
    try:
        for a in adapters:
            if a is not None:
                _quiet(a.close)
        _quiet(audio.stop)
    finally:
        _quiet(media_pool.end_exit)     # the deadline is the exit's alone


class MediaResolver:
    """The app's `media.adapters.Resolver` (plan 32): the file kinds from
    the media folder's last scan, live feeds from the device registry's
    `media_feeds` (plan 32 T8: the ndi / syphon / camera entries' last
    scans — `devices` is pointed at the registry once it exists). Both are
    lookups in what a scan already made, never a scan: the MEDIA page asks
    every frame. `stamp` is what tells a replaced file: the scan's size
    and mtime for the id, and its status, so a file that finishes
    downloading opens afresh (final review A-I1); `status` is the scan's
    word on a file (`fetching` is never opened)."""

    def __init__(self, folder: MediaFolder, devices=None, builtin: dict | None = None):
        self.folder = folder
        self.devices = devices
        # the app's own pictures (2026-11-02): `panel:graph` → its `PanelSource`,
        # the one object every call, so `channels._stale` keeps it
        self.builtin: dict = dict(builtin or {})

    @property
    def proxy_cache(self) -> Path:
        return self.folder.proxy_cache

    def path(self, sid: str) -> Path | None:
        return self.folder.path(sid)

    def live(self, sid: str):
        own = getattr(self, "builtin", {}).get(sid)
        if own is not None:
            return own
        reg = getattr(self, "devices", None)
        return None if reg is None else reg.media_feeds().get(sid)

    def stamp(self, sid: str):
        e = self.folder.entry(sid)
        return None if e is None else (e.size, e.mtime, e.status)

    def status(self, sid: str) -> str:
        return self.folder.status(sid)

    def prefer_shared(self, sid: str) -> str:
        return self.folder.prefer_shared(sid)


class MediaIO:
    """The media side of the app (plan 32): the folder (scanned on its own
    timer), the eight channels, polled once a frame in the scene-setter
    slot, and the close that both exits run — every source closed on the
    channels' closer thread within a 1.5 s budget
    (`channels.CLOSE_BUDGET_S`), the folder's timer stopped, the proxy
    worker and the pool told to stop without waiting, all inside the
    exit's one deadline (`media.pool.left`; review focus 3: the exit stays
    under 2 s). The workers are daemon threads, so one stuck in a read
    never holds the interpreter's exit."""

    def __init__(self, folder: MediaFolder, state: MediaState):
        self.folder, self.state = folder, state
        self.off_air: list = []       # the channels of the decks but the first (plan 44 D4)
        self.heard: Callable[[], Any] | None = None   # the channels on air; None: `state`

    def seat(self, meta) -> None:
        """The meta controller's two `Deck`s: `state` is the first's channels and the other's
        are polled beside it, and the mixer plays whichever `Deck` is on air, as it moves."""
        self.off_air[:] = [c for c in (d.loaded_patch.media for d in meta.decks)
                           if c is not self.state]
        self.heard = lambda: meta.on_air.loaded_patch.media

    def poll(self, dt: float, now: float) -> None:
        # each source read once a frame from here on, whichever deck asks
        # (plan 44 §8: both renderers handed the same `MediaFrame`)
        self.state.sources.begin_frame()
        heard = self.heard() if self.heard is not None else self.state
        # the deck not heard first, so what it lets go is let go before the one on air asks
        for channels in sorted((self.state, *self.off_air), key=lambda c: c is heard):
            channels.poll(dt, now, heard=channels is heard)   # the mixer plays the deck on air

    def close(self) -> None:
        for channels in self.off_air:
            _quiet(channels.drop_sources)
        _quiet(self.state.close)
        _quiet(self.folder.stop)
        _quiet(media_proxy.cancel_all)
        _quiet(lambda: media_pool.shutdown(wait=False))


def _open_media(lib_path: str, home: Path) -> MediaIO:
    """The media folder — `<library>/media/` shared when ``[library] path``
    is set, `<home>/media/` this Mac's own, the proxies and thumbnails in
    `<home>/media-cache/` — and the channels over it. The folder's scans
    start now, on the pool."""
    folder = MediaFolder(Path(lib_path) / "media" if lib_path else None,
                         home / "media", home / "media-cache")
    folder.start()
    return MediaIO(folder, MediaState(MediaResolver(folder)))


def _destroy_windows(windows) -> None:
    """Destroy every window one by one, before `glfw.terminate()` — never
    terminate with a window still open (the exit crash, macOS's "Python
    closed unexpectedly"). pyGLFW's `terminate()` frees every window's
    Python callbacks (their ctypes closures) *before* `glfwTerminate`
    destroys the windows, and on macOS destroying a window pumps the
    event queue: a key, click, mouse move or scroll still queued for a
    window not yet destroyed (the quit key, the hand on the mouse) then
    calls a freed closure — SIGSEGV in `ffi_closure_SYSV_inner`.
    `destroy_window` clears that window's callbacks in C before it pumps
    and frees its closures only after, so the windows go one at a time
    safely and `terminate` finds none left. `None` (a window never
    opened) is skipped; each is best-effort, so one bad handle stops none."""
    for w in windows:
        if w:
            _quiet(lambda w=w: glfw.destroy_window(w))


def _restart(audio, adapters, impl, ctrl_win, save=None, windows=()) -> None:
    # execv swaps the process image in place — same PID, same terminal,
    # same stdio — so stdout doesn't detach and the user's shell keeps
    # owning the child. The OS reclaims the GL contexts and audio device
    # on image swap; we still close the ports and stop the audio stream
    # first so Core Audio doesn't complain about a stream vanishing
    # mid-callback and the next image finds the MIDI ports free.
    # `save` remembers where the windows are (_save_windows), so the next
    # image opens them there.
    if save is not None:
        _quiet(save)
    close_all(audio, *adapters)
    _quiet(lambda: glfw.make_context_current(ctrl_win))  # imgui's GL objects live there
    _quiet(impl.shutdown)
    _destroy_windows(windows)        # every window before terminate: the exit crash
    _quiet(glfw.terminate)
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _save_windows(home, render_win, ctrl_win, output, more=(), slots=(), away=None) -> None:
    """Remember where the windows are, in <home>/windows.json
    (placement.py) — on quit and on restart only. Always the *windowed*
    rect: a fullscreen or overlay render window is remembered by the rect
    `Output` would restore, and a minimised window keeps its old entry.
    `more`: the later render outputs' `Output`s in the config's order
    (plan 21 WP3), None for one not opened this run — its old entry is
    kept, as a minimised window's is. `slots`: every window's spot again, by
    the display it's on (`placement.spot`, SC2). `render_win` None: output 1 has
    no display this run. `away`: where windows closed or held were (`Hotplug.away_spots`)."""
    def minimised(win) -> bool:
        return bool(glfw.get_window_attrib(win, glfw.ICONIFIED))

    control = None
    if not minimised(ctrl_win):
        control = (*glfw.get_window_pos(ctrl_win), *glfw.get_window_size(ctrl_win))
    def rect_of(o) -> tuple | None:
        return None if o is None or o.win is None or minimised(o.win) else o.windowed_rect()

    render = [rect_of(output) if render_win is not None else None, *(rect_of(o) for o in more)]
    spots = {sl.display: rect_of(sl.output) for sl in slots if sl.opened and sl.display}
    spots.update({a.display: rect_of(a.output) for sl in slots for a in sl.also})
    placement.save(home, control, render, placement.screens(glfw), spots, away)


def _slots(cfg: dict | None, scr: list | None = None, notes: list | None = None) -> list[Slot]:
    """The render outputs the config lists (config.screens: one with no
    list), numbered from 1, with their launch switches; no window yet.
    A later output's monitor given by name is an index from here on, by
    `scr` (row 771), and one no screen has is `missing`, as an index no
    screen has is (fork F9), said in `notes`. Output 1's is
    `placement.settle`'s, since it always opens."""
    from . import config

    out = []
    for k, e in enumerate(config.screens(cfg or {})):
        sw = Switches(scene=bool(e["scene"]), hands=bool(e["hands"]), dim=float(e["dim"]),
                      flip_x=bool(e.get("flip_x", False)), flip_y=bool(e.get("flip_y", False)))
        window = bool(e.get("window", True)) or k == 0
        name, monitor, said = placement.named(e["monitor"]), e["monitor"], ""
        if k and scr and name and window:
            monitor, said = placement.resolve(name, scr)
        out.append(Slot(k + 1, name=str(e["name"] or ""), switches=sw,
                        monitor=placement.index(monitor),
                        fullscreen=bool(e["fullscreen"]),
                        window=window,
                        syphon=str(e.get("syphon", "") or ""), ndi=str(e.get("ndi", "") or "")))
        if said:
            if monitor < 0:
                out[-1].missing = f'screen "{name}" is not connected'
            if notes is not None:
                tail = " — not opened" if monitor < 0 else ""
                notes.append(f"config: {out[-1].label}: monitor = {name!r} {said}{tail}")
    return out


def _take_rows(slots: list[Slot], want: Wanted) -> list[Slot]:
    """What the display rows want (`displays.wanted`) on the slots, for this launch: one slot
    for every output there can be, so `output.N.*` never appear mid-run (SC3b), with N kept
    (a wire names it). A slot's first display has its `win` and flips, its others go on
    `also`, and with no display it has no window, publishing if the config has it publish.
    Its name, mutes, dim and what it publishes stay the config's."""
    slots = [*slots, *(Slot(n) for n in range(len(slots) + 1, MAX_OUTPUTS + 1))]
    for sl in slots:
        shows = want.renders.get(sl.n)
        sl.missing = ""
        if not shows:
            sl.monitor, sl.fullscreen = -1, False
            sl.window = not (sl.syphon or sl.ndi)
            away = want.away.get(sl.n)
            if sl.window and away:
                sl.missing = f"its display is not connected ({', '.join(away)})"
            continue
        first, *more = shows
        sl.window, sl.monitor, sl.fullscreen, sl.display = True, first.index, first.fullscreen, first.display
        sl.switches.flip_x, sl.switches.flip_y = first.flip_x, first.flip_y
        sl.also = [Also(o.display, o.index, o.fullscreen, flip_x=o.flip_x, flip_y=o.flip_y)
                   for o in more]
    return slots


NOTHING_TO_PUBLISH = "window = false and nothing to publish (no syphon or ndi)"


CASCADE = 40     # px: a later output's default spot, down and right of the one before


def _later_rect(slot: Slot, k: int, scr, renders: list,
                taken: list) -> tuple[tuple | None, str]:
    """Where a later output (`k` ≥ 1, its place in the list from 0) opens,
    or (None, why) when its screen is not connected (fork F9): an index
    no connected screen has means that output is not opened at all — a
    window landing on the laptop over the controls is worse than none.
    A default spot another output already has (`taken`, their top-left
    corners) is moved down and right by CASCADE until it is free."""
    n = len(scr)
    if slot.monitor >= n:
        have = "0" if n == 1 else f"0–{n - 1}"
        slot.missing = f"screen {slot.monitor} is not connected"
        return None, (f"config: {slot.label}: monitor = {slot.monitor}, but {n} "
                      f"screen{'s are' if n != 1 else ' is'} connected ({have}) — "
                      "not opened")
    remembered = renders[k] if k < len(renders) else None
    rect, note = placement.place("render", RENDER_SIZE, scr, slot.monitor, remembered,
                                 what=slot.label)
    on = scr[slot.monitor] if slot.monitor >= 0 else scr[0]
    if tuple(rect) == placement.default_rect("render", RENDER_SIZE, on):
        # the default spot: cascaded, so it does not sit exactly on another output
        while tuple(rect[:2]) in taken:
            rect = (rect[0] + CASCADE, rect[1] + CASCADE, rect[2], rect[3])
    taken.append(tuple(rect[:2]))
    return rect, note


def _context_hints() -> None:
    """The one GL context every window asks for."""
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)


def _root_window():
    """The window that holds the renderer's context (SC3a, plan 58), hidden,
    never destroyed until the app exits, so no unplugged display can take the
    context or the picture with it. No samples: MSAA is the renderer's own
    framebuffers' (`outputs.FRAME_SAMPLES`). Every other window shares with it.
    Its swap never waits, so it paces nothing (`pacing.py`), and nothing is ever
    drawn on it."""
    _context_hints()
    glfw.window_hint(glfw.SAMPLES, 0)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, False)
    glfw.window_hint(glfw.VISIBLE, False)
    win = glfw.create_window(*ROOT_SIZE, f"{TITLE} — root", None, None)
    glfw.window_hint(glfw.VISIBLE, True)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the render context's window")
    return win


def _open_also(slots: list[Slot], scr: list, seen: dict, root, notes: list[str]) -> None:
    """Each output's further displays (SC2): a window like a later output's, in the root's
    share group. One that won't open is said and goes, and the output's others stand."""
    for slot in slots:
        kept = []
        for also in slot.also:
            rect, note = placement.place("render", RENDER_SIZE, scr, also.monitor,
                                         placement.spot(seen, also.display, slot.n), what=slot.label)
            if note:
                notes.append(note)
            also.win = glfw.create_window(*rect[2:], f"{TITLE} — {also.display}", None, root)
            if not also.win:
                notes.append(f"output: {slot.label} on {also.display}: its window could not be "
                             "created — not opened")
                continue
            glfw.set_window_pos(also.win, *rect[:2])
            kept.append(also)
        slot.also = kept


def _windows(overlay: bool = False, cfg: dict | None = None, home: Path | None = None,
             root=None, want: Wanted | None = None):
    """The GLFW windows on one shared GL context, `root`'s (`_root_window`):
    the render outputs and the controls. Returns (slots, control window): one
    `outputs.Slot` per output the config lists (plan 21 WP3; one with no list,
    as before), `slot.win` its window — or None, with `slot.missing` saying
    why, for a later output whose screen is not connected (fork F9). Output 1
    always opens. Created in this order: output 1, the controls (as before),
    then the later outputs.

    `overlay` is the config's ``[output] overlay`` (decision 21 (a)): only
    then is output 1's framebuffer transparent. A later output is never
    transparent and has its own title. No window has MSAA: each only shows the
    frame, multisampled before it gets there (SC3a).

    Where they open is placement.py's say: ``[output] monitor`` /
    ``control_monitor`` in `cfg` (with a list, `config.load` put output 1's
    entry there) and each later output's ``monitor``, else where they were
    (`home`'s windows.json, one render entry per output), else the default
    spots on the primary screen — a later output's cascaded from output
    1's. Its notes go to stderr and `cfg["notes"]` (the SYSTEM page). With
    no screens no position is set and every output opens.

    `want` (SC2): what the display rows say, in place of the config's screens: where
    each opens and whether it does. Output 1 too: with no display it has no window. The
    config then says only each output's name, mutes, dim and what it publishes. With no
    screens at all, none has a window, until one comes (SC3b). With no `want` (`--laptop`), the
    config says as before."""
    scr = placement.screens(glfw)
    oc = (cfg or {}).get("output", {})
    oc = oc if isinstance(oc, dict) else {}
    if want is not None:
        one = want.renders.get(1)
        oc["monitor"] = one[0].index if one else -1
        oc["fullscreen"] = one[0].fullscreen if one else False
        where = want.control or want.floats
        oc["control_monitor"] = where.index if where else -1
    # a name in the config is an index from here on, said once (row 771)
    said = placement.settle(oc, scr) if scr else []
    slots = _slots(cfg, None if want is not None else scr, said)
    if want is not None:
        slots = _take_rows(slots, want)
        said += want.notes
    first_opens = want is None or bool(slots[0].display)
    render_rect = ctrl_rect = None
    seen: dict = {}
    later_rects: list = [None] * len(slots)
    notes: list[str] = []
    # plan 32 T9: a publish-only output never has a window, so no screen
    # or spot is looked for; one with nothing to publish is not drawn either
    idle = []
    for slot in slots[1:]:
        if slot.publish_only and not (slot.syphon or slot.ndi):
            slot.missing = NOTHING_TO_PUBLISH
            idle.append(f"output: {slot.label}: {slot.missing} — not drawn")
    if scr:
        try:
            seen = placement.load(home) if home is not None else {}
            renders = seen.get("render") or [None]
            if want is not None:
                renders = [placement.spot(seen, sl.display, sl.n) for sl in slots]
            n1 = ""
            if first_opens:
                render_rect, n1 = placement.place("render", RENDER_SIZE, scr,
                                                  oc.get("monitor", -1), renders[0])
            ctrl_rect, n2 = placement.place("control", CONTROL_SIZE, scr,
                                            oc.get("control_monitor", -1), seen.get("control"))
            notes += [n1, n2]
            taken = [tuple(render_rect[:2])] if render_rect else []
            for k, slot in enumerate(slots[1:], start=1):
                if slot.publish_only or slot.missing or (want is not None and not slot.display):
                    continue
                later_rects[k], n = _later_rect(slot, k, scr, renders, taken)
                notes.append(n)
        except Exception as e:  # noqa: BLE001 — a file nobody foresaw must not stop a launch
            render_rect = placement.default_rect("render", RENDER_SIZE, scr[0]) if first_opens else None
            ctrl_rect = placement.default_rect("control", CONTROL_SIZE, scr[0])
            notes = [_err("placement", e) + " — the windows open at their default spots"]
            for k, slot in enumerate(slots[1:], start=1):
                if slot.publish_only or (want is not None and not slot.display):
                    continue
                if slot.monitor >= len(scr):        # fork F9 holds here too (review of #123)
                    slot.missing = f"screen {slot.monitor} is not connected"
                if not slot.missing:
                    r = placement.default_rect("render", RENDER_SIZE, scr[0])
                    later_rects[k] = (r[0] + CASCADE * k, r[1] + CASCADE * k, r[2], r[3])
    for note in filter(None, [*said, *notes, *idle]):
        print(note, file=sys.stderr)
        if cfg is not None:
            cfg.setdefault("notes", []).append(note)
    if scr:
        # …and the config is left saying what was done: an index no screen
        # has (or no number at all) is −1 from here on, as the note above
        # said, so `Output.monitor` cannot carry it further (plan 16 WP7)
        for key in ("monitor", "control_monitor"):
            if key in oc:
                oc[key] = placement.index(oc[key], len(scr))
    slots[0].monitor = placement.index(oc.get("monitor", -1))
    render_size = render_rect[2:] if render_rect else RENDER_SIZE
    ctrl_size = ctrl_rect[2:] if ctrl_rect else CONTROL_SIZE
    _context_hints()
    glfw.window_hint(glfw.SAMPLES, 0)
    # creation-time hints: only when the config asks for overlay does the
    # framebuffer keep alpha so overlay mode can clear to see-through (the
    # other modes clear opaque, and the renderer keeps every pixel at alpha
    # 1 there — plan 14 WP1); otherwise the window is opaque whatever is
    # drawn, for the Pepper's Ghost glass (decision 21 (a), plan 14 WP2).
    # Fullscreen must not minimise when the control window takes focus
    # (overlay.py).
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, bool(overlay))
    glfw.window_hint(glfw.AUTO_ICONIFY, False)
    render_win = None
    if first_opens:
        render_win = glfw.create_window(*render_size, TITLE, None, root)
        if not render_win:
            glfw.terminate()
            raise SystemExit("could not create the render window")
    # the control window is an ordinary opaque window; the shared context
    # lets both sides see the same buffers, textures and programs
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, False)
    ctrl_win = glfw.create_window(*ctrl_size, f"{TITLE} — controls", None, root)
    if not ctrl_win:
        glfw.terminate()
        raise SystemExit("could not create the control window")
    # by default: render left, controls flush right on the primary screen's
    # work area; they overlap on a narrow laptop screen until one goes to a
    # projector (placement.default_rect)
    if render_rect and render_win:
        glfw.set_window_pos(render_win, *render_rect[:2])
    if ctrl_rect:
        glfw.set_window_pos(ctrl_win, *ctrl_rect[:2])
    slots[0].win = render_win
    # the later outputs (plan 21 WP3): in the root's share group (they
    # sample its frame textures), opaque, no MSAA, never minimised when
    # another window takes focus — the hints above still hold
    # (TRANSPARENT_FRAMEBUFFER off, SAMPLES 0, AUTO_ICONIFY off)
    for k, slot in enumerate(slots[1:], start=1):
        if slot.missing or slot.publish_only or (want is not None and not slot.display):
            continue
        rect = later_rects[k]
        size = rect[2:] if rect else RENDER_SIZE
        title = f"{TITLE} — {slot.name or f'output {slot.n}'}"
        win = glfw.create_window(*size, title, None, root)
        if not win:
            slot.missing = "its window could not be created"
            note = f"output: {slot.label}: {slot.missing} — not opened"
            print(note, file=sys.stderr)
            if cfg is not None:
                cfg.setdefault("notes", []).append(note)
            continue
        slot.win = win
        if rect:
            glfw.set_window_pos(win, *rect[:2])
    if want is not None:
        more: list[str] = []
        _open_also(slots, scr, seen, root, more)
        for note in more:
            print(note, file=sys.stderr)
            if cfg is not None:
                cfg.setdefault("notes", []).append(note)
    return slots, ctrl_win


def _overlay_allowed(cfg: dict) -> bool:
    """Decision 21 (a): overlay mode exists only when ``[output] overlay``
    is true (config.DEFAULTS: false)."""
    return bool(cfg.get("output", {}).get("overlay", False))


def _make_output(win, reg: Registry, cfg: dict) -> Output:
    """The render window's output settings, seeded from config."""
    # [output] in config.toml — config.load has already folded a pre-split
    # [overlay] section under it, so this is the one place that reads it
    oc = cfg.get("output", {})
    out = Output(win, GlfwBackend(glfw), allowed=_overlay_allowed(cfg))
    out.register(reg)
    # a screen index, or −1: `_windows` has already put −1 in place of an
    # index no connected screen has and made a name its index (and placement
    # said so; an index at runtime until SC3b, row 771), `config.load` put −1
    # in place of anything neither a number nor a name — and a cfg that came
    # by neither road must not stop the launch here either (plan 16 WP7)
    out.monitor = placement.index(oc.get("monitor", -1))
    out.fullscreen = bool(oc.get("fullscreen", False))
    out.render = render_index(oc.get("render", RENDER_DEFAULT))
    if oc.get("on_start", False) and not out.allowed:
        print("output: on_start asks for overlay, but [output] overlay is false — "
              "the window stays opaque", file=sys.stderr)
    out.overlay = bool(oc.get("on_start", False)) and out.allowed
    out.passthrough = bool(oc.get("passthrough", True))
    # `bg = "x"` stopped the launch here; config.load now says so and
    # keeps the default — and a cfg that came another road falls back too
    from .config import number

    bg, alpha = number(oc.get("bg", 0.0)), number(oc.get("alpha", 1.0))
    out.bg = 0.0 if bg is None else bg
    out.alpha = 1.0 if alpha is None else alpha
    return out


def _later_output(slot: Slot) -> Output:
    """A later render output's window settings (plan 21 WP3): its screen
    and fullscreen from its config entry (fork F10: no params — the
    output.* params are output 1's), never overlay; `apply()` runs each
    frame as output 1's does."""
    out = Output(slot.win, GlfwBackend(glfw), allowed=False)
    out.monitor = placement.index(slot.monitor)
    out.fullscreen = bool(slot.fullscreen)
    return out


def _also_output(also: Also) -> Output:
    """A further display's window settings (SC2), as a later output's."""
    out = Output(also.win, GlfwBackend(glfw), allowed=False)
    out.monitor = placement.index(also.monitor)
    out.fullscreen = bool(also.fullscreen)
    return out


def _promote(slot: Slot, also: Also) -> None:
    """A further display takes over as `slot`'s first: its flips become the ones the output is
    drawn with, as what a first display has."""
    slot.win, slot.presenter, slot.display = also.win, also.presenter, also.display
    slot.monitor, slot.fullscreen, slot.missing = also.monitor, also.fullscreen, ""
    slot.switches.flip_x, slot.switches.flip_y = also.flip_x, also.flip_y


def _outputs_now(slots: list[Slot]) -> list:
    """Every open window's `Output`, output 1's first: applied once a frame."""
    return [*(sl.output for sl in slots if sl.output is not None),
            *(a.output for sl in slots for a in sl.also)]


def _slot_windows(slots: list[Slot]) -> list:
    """Every window the outputs have, in slot order: the first in the list paces."""
    return [w for sl in slots if sl.opened for w in (sl.win, *(a.win for a in sl.also))]


def _open_presenters(slots: list[Slot], root, make_context=None, notes: list | None = None) -> None:
    """Each output's `Presenter`, on its own window's context, none waiting
    for its screen: `Pacer.choose` says which one does (fork F6: two waiting
    swaps a frame halve the rate, plan 21 §1: 121 fps against 60–81). A later
    output that will not build is closed and counts as not opened, its
    `missing` saying why (`notes`, the SYSTEM page): a window that is never
    drawn would show garbage and fool the watch (review of #123). The others
    go on. Output 1 always opens, so its failing stops the launch, as its
    context failing always has. Leaves the root's context current."""
    make = make_context or moderngl.create_context
    for slot in slots:
        if not slot.opened:
            continue
        try:
            glfw.make_context_current(slot.win)
            glfw.swap_interval(0)
            slot.presenter = Presenter(make())
        except Exception as e:
            glfw.make_context_current(root)
            if slot is slots[0]:
                raise
            _quiet(lambda w=slot.win: glfw.destroy_window(w))
            slot.win, slot.presenter = None, None
            slot.missing = f"its GL context would not open ({_err('presenter', e)})"
            note = f"output: {slot.label}: {slot.missing} — not opened"
            print(note, file=sys.stderr)
            if notes is not None:
                notes.append(note)
    for slot in slots:
        kept = []
        for also in slot.also:
            try:
                glfw.make_context_current(also.win)
                glfw.swap_interval(0)
                also.presenter = Presenter(make())
                kept.append(also)
            except Exception as e:  # noqa: BLE001 — as a later output: the others go on
                glfw.make_context_current(root)
                _quiet(lambda w=also.win: glfw.destroy_window(w))
                note = (f"output: {slot.label} on {also.display}: its GL context would not open "
                        f"({_err('presenter', e)}) — not opened")
                print(note, file=sys.stderr)
                if notes is not None:
                    notes.append(note)
        # a first display that wouldn't build: the next takes over, so no window that's fine
        # goes undrawn, and the output still has its picture
        if not slot.opened and kept:
            _promote(slot, kept.pop(0))
        slot.also = kept
    glfw.make_context_current(root)


def _open_publishers(slots: list[Slot], ctx, notes: list | None = None) -> None:
    """Plan 32 T9: each drawn output's publishers (media/publish.py), made
    with the render context current — a Syphon server takes the context
    current as it is made; a publisher that cannot open says so on its
    SYSTEM line, and every failure is said once in `notes` (the
    config's). A publish-only output gets its offscreen target, a
    published window its tap (`outputs.Offscreen`)."""
    for slot in slots:
        if not slot.drawn:
            continue
        slot.publishers = publish.open_for(slot, ctx, notes=notes)
        if slot.publish_only:
            slot.offscreen = Offscreen(ctx)
        elif slot.publishers:
            slot.tap = Offscreen(ctx)


def _close_publishers(win, slots: list[Slot]) -> None:
    """Both exits: every publisher closed (an NDI sender's thread joined)
    and the offscreen targets freed, with the render context (the root's,
    `win`) current — their GL objects are its."""
    _quiet(lambda: glfw.make_context_current(win))
    publish.close_all(slots)
    for slot in slots:
        for off in (slot.offscreen, slot.tap):
            if off is not None:
                _quiet(off.release)
        slot.publishers, slot.offscreen, slot.tap = [], None, None


def _gl_flush() -> None:
    """glFlush in the current context: a presenter's context samples the
    renderer's frame textures, and without the flush it sees last frame's
    (plan 21 §1, measured: 199 of 200 frames late). `_say_gl_error` has taken
    anything pending, so a `GLError` here is the flush's own."""
    from OpenGL import GL

    GL.glFlush()


def _say_gl_error(ctx, watch) -> None:
    """What the frame left pending in the render context, told to the watch, not
    raised: moderngl doesn't check, so PyOpenGL's next call would blame the flush
    for it. GL_OUT_OF_MEMORY is one of these, so it mustn't vanish."""
    for _ in range(4):                     # a driver may hold several flags
        err = ctx.error
        if err == "GL_NO_ERROR":
            return
        if watch is not None:
            watch.gl_error(err)


def _bands(audio) -> tuple[float, ...]:
    """The analyzer's lanes normalized, or () while the analyzer is off or
    has none (a stub). Never raises: it feeds a picture, not a control."""
    try:
        if not getattr(audio, "on", False):
            return ()
        lanes = getattr(getattr(audio, "chain", None), "lanes", None)
        return () if lanes is None else tuple(float(v) / CEIL for v in lanes)
    except Exception:  # noqa: BLE001 — a missing band is a dark bar, not a crash
        return ()


def _also_handoff(sl: Slot, v: View, also: Also, first: Slot, frame_tex, frame_size) -> Handoff | None:
    """What a further display of `sl` is given (SC2): the same picture, in its own window's
    shape, with its own flips. Output 1's picture is whole on the frame target with its first
    display's flips in it, so the rest is what's left to undo; opaque, as overlay is that
    window's alone. Another output's is its `Handoff`, whose mix was drawn for its first
    display (`Handoff.mix_flip`)."""
    fl = (also.flip_x, also.flip_y)
    sw = (bool(sl.switches.flip_x), bool(sl.switches.flip_y))
    off = (fl[0] != sw[0], fl[1] != sw[1])
    if sl is first:
        return Handoff(frame_tex, frame_size, fit(frame_size, also.size), flip=off)
    ho = v.handoff
    if ho is None:
        return None
    rect = fit(ho.frame_size, also.size)
    return replace(ho, rect=rect, flip=fl, mix_flip=off,
                   mix_viewport=_mix_viewport(ho.mix, ho.frame_size, rect))


def _mix_viewport(mix, frame_size, rect) -> tuple[int, int, int, int] | None:
    """Where to lay `mix`, the other deck's whole picture at the first display's shape, so its
    frame lands on `rect`, this window's: it may stick out past the window, where nothing is
    but its bars. None with no mix on."""
    if mix is None:
        return None
    ix, iy, iw, ih = fit(frame_size, mix.size)
    if iw <= 0 or ih <= 0:
        return None
    sx, sy = rect[2] / iw, rect[3] / ih
    return (round(rect[0] - ix * sx), round(rect[1] - iy * sy),
            round(mix.size[0] * sx), round(mix.size[1] * sy))


def _draw_render(renderer, ctx, s, slots: list[Slot], root: Root, watch=None, flush=None,
                 preview=None, monitor=None, fade=None, panel_deck=None) -> None:
    """One render frame onto every output (plan 21 WP3, "the frame in
    app.draw_render"; SC3a, plan 58: the picture depends on no display):

    1. the root's context current; the stranded-target check; the handover,
       if the pacing window should change (`Pacer.choose`);
    2. a `View` per output — output 1 on the root's frame target (`Root.frame`,
       at its window's framebuffer size, or the last known with no window),
       each later one with its presenter and its framebuffer's size, or (plan
       32 T9) a publish-only one on its offscreen target at the render
       cap's size ("full": output 1's framebuffer), in their list order;
       each published one carries its publishers (and its tap). Output 1's view
       says `FRAME_SAMPLES`: an offscreen target can't, so the scene's MSAA
       would go without it;
    3. `renderer.draw_outputs`: output 1 drawn whole, a `Handoff` left for
       the others;
    4. glFlush in the root's context;
    5. each window, in its own `try`, the pacing one last: current, `present`
       (output 1's, its target 1:1), swap (only the pacing one waits). A later
       output's raising sets its slot's `error` and tells the watch; the frame
       goes on;
    6. the root's context current, whatever happened.

    **A window swaps only a whole picture it was just given.** A draw that raises, a
    view that caught a draw's error (`View.exc`: its target is half-drawn, or its
    ground), or a present that raises leaves it on its last frame, as `frame` promises;
    the slot's `error` says why. With nothing swapped the timer paces (`Pacer`).

    What output 1's view caught, and output 1's own present raising, are raised after
    the others were presented, so they reach `RenderWatch.failed` and the red banner:
    the operator's one warning that the main picture has stopped. A further display of an
    output (`Slot.also`, SC2) takes its output's picture as step 5 does, and is one more
    present; its failing is said on its own row. `preview` (an `outputs.Preview`), when
    the GRAPH page asked for it, rides on output 1's view as one more
    publisher — through output 1's own tap, else its own — and is flushed
    for the control window as a presenter's frame is.

    Plan 44 D4: `fade` (a `deck.Fade`). At `output.xfade` 0, exactly the
    above. Above 0, before output 1's draw, deck 2 draws every output
    offscreen (`Fade.draw`) and each view carries its picture to the mix
    pass, so every presenter, publisher and panel inset shows the mix.

    Plan 44 D5c: `panel_deck`, the deck the panel is on. Off air, the page's
    backdrop is that deck's picture (`Fade.preview`), not output 1's, and a look
    just landed there is drawn once small (`Fade.warm`). Output 1 then rides
    `monitor` (another `Preview`, the page's inset of what is on air) when the
    page asked for it."""
    first = slots[0]
    glfw.make_context_current(root.win)
    # the frame target, bound explicitly every frame: the renderer draws into
    # whatever is bound, and a frame that once left another offscreen
    # framebuffer bound froze the picture with no error (plan 14 WP1).
    # draw_outputs puts its target back; the check is the alarm.
    stranded = ctx.fbo
    if (stranded is not None and stranded.glo != 0 and stranded is not root.frame.fbo
            and watch is not None):
        watch.stranded(stranded.glo)
    presented = [sl for sl in slots if sl.opened and sl.presenter is not None]
    pacer = root.pacer
    pacer.choose(_slot_windows(presented), root.win)
    # output 1's own size and DPI (a 1080p projector next to a retina laptop); with no display
    # on it, the first that shows anything's, each frame: a window goes fullscreen, or is moved
    # (a display that dropped a moment ago may be back: nothing resizes for it yet, SC3b)
    measured = None if root.hold_size else first if first.opened else next(iter(presented), None)
    if measured is not None:
        root.measure(glfw.get_window_size(measured.win), glfw.get_framebuffer_size(measured.win))
    w, h = root.logical
    fbw, fbh = root.size
    first.size = (fbw, fbh)
    offscreen = [sl for sl in slots[1:] if sl.publish_only and sl.offscreen is not None]
    wanted = preview is not None and preview.take()
    panel_off = fade is not None and panel_deck is not None and panel_deck is fade.off_air
    off_preview = wanted and panel_off
    shown_to_panel = wanted and not panel_off
    watched = panel_off and monitor is not None and monitor.take()
    pubs, tap = first.publishers, first.tap
    if shown_to_panel or watched:
        pv = preview if shown_to_panel else monitor
        pubs, tap = [*pubs, pv], tap if tap is not None else pv.tap
    try:
        target = root.frame.fit((fbw, fbh))
        target.use()
        ctx.viewport = (0, 0, fbw, fbh)
        views = [View(first.switches, (fbw, fbh), target=target,
                      bg_alpha=getattr(renderer, "bg_alpha", 1.0), viewport=(0, 0, fbw, fbh),
                      publish=pubs, tap=tap, samples=FRAME_SAMPLES)]
        shown = [(first, views[0])] if first in presented else []   # (slot, view): the windows
        pub_size = getattr(renderer, "max_frame", None) or (fbw, fbh)
        for sl in slots[1:]:
            if sl in presented:
                sl.size = tuple(int(v) for v in glfw.get_framebuffer_size(sl.win))
                views.append(View(sl.switches, sl.size, presenter=sl.presenter,
                                  publish=sl.publishers, tap=sl.tap))
                shown.append((sl, views[-1]))
            elif sl in offscreen:
                sl.size = (int(pub_size[0]), int(pub_size[1]))
                views.append(View(sl.switches, sl.size, target=sl.offscreen.fit(sl.size),
                                  publish=sl.publishers))
        if fade is not None:
            fade.begin_frame()
            if fade.k > 0.0 or fade.warm_deck is not None or off_preview:
                lw, lh, dpr = max(w, 1), max(h, 1), fbw / max(w, 1)
                fade.warm(lw, lh, dpr, first.switches, FRAME_SAMPLES)
                if fade.k > 0.0:
                    fade.draw(views, lw, lh, dpr, FRAME_SAMPLES)
                if off_preview:
                    off_preview = fade.preview(preview, lw, lh, dpr, (fbw, fbh), first.switches)
                target.use()                      # the frame target again, with its viewport
                ctx.viewport = (0, 0, fbw, fbh)
        renderer.draw_outputs(s, max(w, 1), max(h, 1), fbw / max(w, 1), views)
        _say_gl_error(ctx, watch)
        if presented or shown_to_panel or watched or off_preview:
            (flush or _gl_flush)()
        lost = None                     # output 1's present, raised after the others had theirs
        for sl, v in shown:
            for also in sl.also:            # (never the pacing window: its slot's first would be)
                also.error = v.error
                try:
                    fbx, fby = glfw.get_framebuffer_size(also.win)
                    also.size = (int(fbx), int(fby))
                    ho = _also_handoff(sl, v, also, first, root.frame.tex, (fbw, fbh))
                    if v.exc is not None or ho is None or min(also.size) <= 0:
                        continue
                    glfw.make_context_current(also.win)
                    also.presenter.present(ho, also.size)
                    glfw.swap_buffers(also.win)
                except Exception as e:  # noqa: BLE001 — as a later output
                    also.error = _err("present", e)
                    if watch is not None:
                        watch.output_failed(f"{sl.label} on {also.display}", e)
        for sl, v in sorted(shown, key=lambda p: p[0].win is pacer.owner):
            # output 1's picture is already whole on the frame target: flip, hands,
            # mix and dim are in it, so its window only shows it, 1:1
            ho, size = v.handoff, sl.size
            if sl is first:
                rect = (0, 0, fbw, fbh)
                if root.hold_size:
                    # its first display is away a moment: this one shows the frame in its own shape
                    wx, wy = glfw.get_framebuffer_size(sl.win)
                    size = (int(wx), int(wy))
                    rect = fit((fbw, fbh), size)
                ho = Handoff(root.frame.tex, (fbw, fbh), rect, bg_alpha=v.bg_alpha)
            sl.error = v.error
            if v.exc is not None or ho is None or size[0] <= 0 or size[1] <= 0:
                continue                # a failed or empty picture: it holds what it shows
            try:
                glfw.make_context_current(sl.win)
                sl.presenter.present(ho, size)
                glfw.swap_buffers(sl.win)
                if sl.win is pacer.owner:
                    pacer.swapped()
            except Exception as e:  # noqa: BLE001 — one output must not take the frame down
                sl.error = _err("present", e)
                if sl is first:
                    lost = e
                elif watch is not None:
                    watch.output_failed(sl.label, e)
        if views[0].exc is not None:
            raise views[0].exc
        if lost is not None:
            raise lost
    finally:
        glfw.make_context_current(root.win)


def control_title(meta) -> str:
    """The control window's title: which `Deck` the panel is on."""
    return f"{TITLE} — controls · {meta.words(meta.panel)}"


def _desk_table(reg: Registry, table: Bindings) -> Bindings:
    """The app's binding table, with the desk's own params declared on it
    and knob smoothing at the app's default (plan 18 WP2, fork 12). Called
    before `library.attach`, like every shared meta param's registration, so
    `desk.slew` exists when the show's session values land: a show that
    saved a number keeps it (0 included), one that names none takes 80 ms
    as the state it opened with — clean, and what "default" means. A bare
    `Bindings` (the tests', the probe's) stays at 0."""
    register_desk(reg, table)
    table.slew = SLEW_DEFAULT_S
    return table


def _hand_settings(reg: Registry, cfg: dict):
    """The hands setup as `hands.*` params — registered whether or not the
    tracker is on, so a project or loadable patch carries it either way. hands/core.py
    imports the SDK only inside LeapSource, so this costs nothing."""
    try:
        from . import hands
        settings = hands.HandSettings.from_config(cfg.get("hands"))
        hands.register(reg, settings)
        return settings
    except Exception as e:  # noqa: BLE001 — a bad [hands] must not stop the show
        print(f"hands: {e}", file=sys.stderr)
        return None


def _open_devices(cfg: dict, ctx: devices.Context, home: Path | None,
                  clock=time.monotonic, store: DeviceList | None = None) -> devices.DeviceRegistry:
    """The device registry (devices.py, plan 27 B1) over the config's
    `[[devices]]` list — the old `[midi]` / `[gamepad]` / `[hands]` /
    `[bridge]` tables translated when there is none — every device opened
    behind its own entry. One that would not open (no `leap` package, a
    `[hands] tape` that is missing) is said on stderr and in
    `cfg["notes"]`, which the SYSTEM page lists and the HANDS page shows
    in place of "tracker off" (plan 21 WP5 R10), and is tried again on
    the Ports schedule. With a `store` (`devicelist.DeviceList`, `main`'s) the
    registry watches that for the other Mac's changes, and the tray can adopt;
    with none, `<home>/config.toml` for edits to the list. The first look for
    MIDI ports is made here, before any frame, as it takes up to a second."""
    path = (home / config.FILE) if home is not None and store is None else None
    reg = devices.DeviceRegistry(config.devices(cfg), ctx, path=path, clock=clock,
                                 notes=cfg.setdefault("notes", []), store=store)
    reg.open_all()
    if not cfg.get("no_midi_look"):
        port_names()
    return reg


# torch is an ordinary dependency (decision register row 23 (a)): `uv sync`
# installs it. A missing torch means the environment was not synced.
DREAM_SETUP = "run `uv sync`, then launch with `uv run hyperspace`"


def dream_error(e: Exception) -> str:
    """What the panel says when the dream worker would not start: torch
    missing gets the setup commands (README "Dream worker")."""
    mod = (getattr(e, "name", "") or "").split(".")[0] if isinstance(e, ImportError) else ""
    if mod in ("torch", "torchvision"):
        return f"dream worker off: {mod} is not installed — {DREAM_SETUP}"
    return f"dream worker off: {type(e).__name__}: {e}"[:200]


def _open_dream(reg: Registry, cfg: dict) -> tuple[object | None, str]:
    """The look-back's dream worker (dream.py, torch), only when [dream]
    enabled; with the reason it is off when it would not start (the SYSTEM
    and LOOKBACK pages show it), "" otherwise."""
    if not cfg.get("dream", {}).get("enabled", False):
        return None, ""
    try:
        from . import dream
        return dream.DreamWorker(reg, cfg["dream"]), ""
    except Exception as e:  # noqa: BLE001 — no torch, no GPU: the plain tracer runs
        print(f"dream: {e}", file=sys.stderr)
        return None, dream_error(e)


def _dial_launch(cfg: dict) -> dict[str, str]:
    """Each stick's dial reading at launch, {"L": …, "R": …}: the first enabled gamepad
    entry's `dial_left` / `dial_right` (`[[devices]]`, or the old `[gamepad]` table
    translated), else `gamepad.DIAL_DEFAULT`. What a loadable patch naming none gets. A
    reading is a deck's, not a pad's, so there is one pair: a later entry's that differs
    is said (`cfg["notes"]`, the SYSTEM page) and not read."""
    out = dict(gamepad.DIAL_DEFAULT)
    pads = [e for e in config.devices(cfg) if e.get("kind") == "gamepad" and e.get("enabled", True)]
    keys = (("L", "dial_left"), ("R", "dial_right"))
    for stick, key in keys:
        if pads and pads[0].get(key) in gamepad.DIAL_MODES:
            out[stick] = pads[0][key]
    for e in pads[1:]:
        if any(e.get(key) in gamepad.DIAL_MODES and e[key] != out[stick] for stick, key in keys):
            cfg.setdefault("notes", []).append(
                f"config: {e.get('role')}: dial_left / dial_right are read on the first "
                "enabled pad only; a loadable patch's own readings win")
    return out


class Awake:
    """The Mac kept out of the screensaver, display sleep and idle system
    sleep while the app runs: macOS's own `caffeinate -d -i`, tied to this
    process with ``-w`` so it ends with us even after a crash or a kill -9.
    `close` ends it at a quit and before ⌘R's execv (same PID: the new
    image starts its own). Not macOS, or no caffeinate: nothing, with a
    note — never a dead launch."""

    CMD = "caffeinate"

    def __init__(self, pid: int | None = None, popen=subprocess.Popen,
                 which=shutil.which, platform: str = sys.platform) -> None:
        self.proc = None
        self.note = ""
        if platform != "darwin":
            self.note = "keep awake: not macOS — the OS's own sleep settings apply"
            return
        exe = which(self.CMD)
        if exe is None:
            self.note = "keep awake: no caffeinate on PATH — the screensaver can come on"
            return
        try:
            self.proc = popen([exe, "-d", "-i", "-w", str(os.getpid() if pid is None else pid)],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        except OSError as e:
            self.note = f"keep awake: caffeinate did not start ({e}) — the screensaver can come on"

    def close(self) -> None:
        if self.proc is not None:
            proc, self.proc = self.proc, None
            proc.terminate()
            proc.wait(timeout=1.0)     # reaped, so no zombie rides through ⌘R's execv


def _share_experiments(first: Registry, second: Registry, *, poi_cfg: dict) -> None:
    """The totem's and the poi's params on the second deck too (plan 44 D5a),
    over the one state each: they are registered by the panel hook, which only
    the first deck runs, and neither is a shared meta group, so a pad or the panel
    on deck 2 would lose them. One state, one pad: what it holds of a look is of
    the deck its pad is on (`on_reg`, plan 55) and goes no further."""
    if (state := totem.state_of(first)) is not None:
        totem.register(second, state)
    if (swing := poi.state_of(first)) is not None:
        poi.register(second, swing, poi_cfg)


def _open_awake(cfg: dict):
    """`Awake`, unless [output] keep_awake = false (on by default)."""
    if cfg.get("output", {}).get("keep_awake", True) is False:
        return None
    awake = Awake()
    if awake.note:
        print(awake.note, file=sys.stderr)
    return awake


class Keys:
    """Edge detection and hold timing over polled key state, across both windows.

    A key counts as down when it is down in the render window, or in the
    control window while imgui is not typing (`typing` is io.want_capture_
    keyboard, set each frame after new_frame()). This is the `keys` the
    router's key rows read: pressed() is an edge, shift() / super() /
    control() the modifier state a "key:SHIFT+B" or "key:CONTROL+Z" row
    needs (routing.MODIFIERS). R and F1–F8 / ⇧F1–F8 are
    table rows since plan 11 WP7; Cmd+R, Q and ↑ / ↓ stay in the
    loop (`frame`), Cmd+R claiming R's edge before the table reads it.
    """

    def __init__(self, render_win, ctrl_win, more=()):
        self.render_win, self.ctrl_win = render_win, ctrl_win
        self.more = tuple(more)     # every other render window (plan 21 WP3, SC2); SC3b keeps both
        self.typing = False
        self.prev: dict[int, bool] = {}
        self.down_since: dict[int, float] = {}

    def _down(self, key: int) -> bool:
        if self.render_win is not None and glfw.get_key(self.render_win, key) == glfw.PRESS:
            return True
        for win in getattr(self, "more", ()):
            if glfw.get_key(win, key) == glfw.PRESS:
                return True
        return not self.typing and glfw.get_key(self.ctrl_win, key) == glfw.PRESS

    def pressed(self, key: int) -> bool:
        down = self._down(key)
        was = self.prev.get(key, False)
        self.prev[key] = down
        return down and not was

    def held(self, key: int, now: float) -> float:
        """Seconds the key has been continuously down at the frame's `now`;
        0.0 when up. The loop's clock, not one of its own (audit P4)."""
        if not self._down(key):
            self.down_since.pop(key, None)
            return 0.0
        return now - self.down_since.setdefault(key, now)

    def down(self, *keys: int) -> bool:
        return any(self._down(k) for k in keys)

    # the modifier state the routing table's key rows read ("key:SHIFT+B")
    def shift(self) -> bool:
        return self.down(glfw.KEY_LEFT_SHIFT, glfw.KEY_RIGHT_SHIFT)

    def super(self) -> bool:  # the modifier's name, as the table spells it
        return self.down(glfw.KEY_LEFT_SUPER, glfw.KEY_RIGHT_SUPER)

    def control(self) -> bool:  # either Control key (plan 15: Ctrl+Z)
        return self.down(glfw.KEY_LEFT_CONTROL, glfw.KEY_RIGHT_CONTROL)


class Mouse:
    """Orbit, pan and zoom from the render window's mouse — no imgui to defer to.

    Buttons and cursor are polled; the wheel arrives by callback and is
    drained once per frame.
    """

    def __init__(self, win, reg: Registry, view: ViewState, switches=None,
                 pointer: Pointer | None = None):
        self.win = win
        # output 1's switches (plan 23 WP1): on a flipped output the cursor
        # is mirrored before use, so a drag and the wheel follow the picture
        self.switches = switches
        self.pointer = pointer      # the deck it is on (plan 44 D5a); None: `reg`, always
        self.use(reg, view)
        self.drag = {"btn": None, "x": 0.0, "y": 0.0}
        self._wheel = 0.0
        if win is not None:         # (no display shows output 1: nothing to orbit from, SC2)
            self._listen(win)

    def aim(self, win) -> None:
        """Output 1's window now (SC3b: its display came or went); a drag under way ends."""
        if win is self.win:
            return
        self.win = win
        self.drag = {"btn": None, "x": 0.0, "y": 0.0}
        if win is not None:
            self._listen(win)

    def _listen(self, win) -> None:
        """The wheel over `win`, while it's output 1's. A window that stops being one may be alive
        as a further display, and one may be destroyed, so it's filtered, never cleared."""
        glfw.set_scroll_callback(win, lambda w, dx, dy: self._on_scroll(w, dx, dy) if self.win is win else None)

    def use(self, reg: Registry, view: ViewState) -> None:
        """The camera params it writes and the view it reads: `reg`'s."""
        self.reg, self.view = reg, view
        self.yaw, self.pitch, self.zoom = reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]
        self.pan_x, self.pan_y = reg["camera.pan.x"], reg["camera.pan.y"]

    def _on_scroll(self, _win, _dx: float, dy: float) -> None:
        self._wheel += dy

    def poll(self, shift: bool) -> None:
        if self.pointer is not None and self.pointer.deck.reg is not self.reg:
            self.use(self.pointer.deck.reg, self.pointer.deck.view)
        win, s, drag = self.win, self.view, self.drag
        if win is None:
            return
        x, y = glfw.get_cursor_pos(win)
        w, h = glfw.get_window_size(win)
        x, y = flipped(self.switches, x, y, w, h)
        left = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS
        right = glfw.get_mouse_button(win, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS
        # shift+drag pans too — a trackpad has no right button to hold
        btn = "pan" if (right or (left and shift)) else "orbit" if left else None
        if btn != drag["btn"]:
            drag.update(btn=btn, x=x, y=y)
        elif btn == "orbit":
            self.yaw.nudge((x - drag["x"]) * 0.005)
            self.pitch.nudge((y - drag["y"]) * 0.005)
            drag.update(x=x, y=y)
        elif btn == "pan":
            # the pan is in world units (plan 26 A2): the shape's centre
            # follows the cursor
            unit = _px_per_unit(s, w, h)
            self.pan_x.nudge((x - drag["x"]) / unit)
            self.pan_y.nudge((y - drag["y"]) / unit)
            drag.update(x=x, y=y)
        wheel, self._wheel = self._wheel, 0.0
        if wheel:
            _zoom_about(self.zoom, self.pan_x, self.pan_y, s, wheel, x, y, w, h)


def flipped(switches, x: float, y: float, w: float, h: float) -> tuple[float, float]:
    """A cursor position in output 1's window, mirrored as its picture is
    (plan 23 WP1: `Switches.flip_x` / `flip_y`); output 1's frame fills its
    window, so the window is the space to mirror in. No switches: as is."""
    if switches is not None and getattr(switches, "flip_x", False):
        x = w - x
    if switches is not None and getattr(switches, "flip_y", False):
        y = h - y
    return x, y


# ---- relative writers: the mouse, the sticks and ↑/↓ move a param by a
# delta each frame, through Param.nudge / Param.scale — on the base, so a
# performer's offset rides on the move (plan 09 decision 3; audit
# simulation 1). The two helpers below are the moves with geometry of
# their own; they take Params and a view, so they run without a window.

def _zoom_about(zoom, pan_x, pan_y, view, wheel: float, x: float, y: float,
                w: float, h: float) -> None:
    """Wheel zoom about the cursor: keep the point under it fixed.

    The picture moves by the *effective* ratio, not the base's — a
    performer pinning the zoom at a stop means the wheel moves the return
    value and nothing on screen, so the pan must not move either. apply()
    runs later in the frame, so that ratio is predicted: the performer's
    share is a ratio on a log range, and the effective lands clamped.
    The centre is where the picture is (the effective pan); the
    correction lands on the pan's base like any other nudge.
    """
    eff = min(max(view.zoom, zoom.lo), zoom.hi)     # apply()'s clamp, to the last bit
    ratio = zoom.scale(2.0 ** (wheel * 0.15))
    factor = min(max(eff * ratio, zoom.lo), zoom.hi) / eff
    # plan 26 A2: the zoom scales the shape about the world origin and the
    # pan is in world units, so the point under the cursor is held in the
    # world (on the plane through the origin, where a unit is `unit` px)
    unit = _px_per_unit(view, w, h)
    cx, cy = view.pan[0], view.pan[1]
    pan_x.nudge((cx - (x - w / 2) / unit) * (factor - 1))
    pan_y.nudge((cy - (y - h / 2) / unit) * (factor - 1))


def _px_per_unit(view, w: float, h: float) -> float:
    """Logical px a world unit spans at the origin through the view's eye
    (geometry.px_per_unit): how far a pan moves the shape on screen."""
    return px_per_unit(w, h, getattr(view, "eye_fov", EYE_FOV),
                       getattr(view, "eye_distance", EYE_DISTANCE))


def _ride_depth(p, octaves: float) -> None:
    """Move 4D depth by a number of octaves of (depth − 1) — the taper's
    own space (gamepad.ride_depth: the triggers ride it the same way)."""
    gamepad.ride_depth(p, octaves)


class _DevicesMade(NamedTuple):
    """What `main`'s devices hook made beside the deck (plan 44 D1): the
    device registry, the dream worker (or None), the keep-awake and the
    segment workers' closer."""

    device_reg: devices.DeviceRegistry
    dream_io: object | None
    awake: object
    segmenters: object


@dataclass
class Host:
    """Everything one frame touches, built once by `main()`; `frame()` runs a
    frame over it. Optional adapters are `None` when their config gate is
    shut. `draw_render` / `draw_panel` / `restart` / `quit` are the window
    system's four moves, closures in `main()` so the order can be tested
    over stubs (tests/test_app_boundary.py)."""

    reg: Registry
    view: ViewState
    control: Control
    audio: AudioEngine
    router: Router
    clock: tempo.Clock
    lfos: lfo.LFOs
    keys: Keys
    mouse: Mouse
    output: Output
    renderer: Renderer
    panel: Panel
    reloader: HotReloader
    draw_render: Callable[[float], None]
    draw_panel: Callable[[float, float], None]
    restart: Callable[[], None]
    quit: Callable[[], None]
    # the device registry (devices.py, plan 27 B1): the pad, MIDI, the
    # hands, the bridge — every input and output the config lists
    devices: devices.DeviceRegistry | None = None
    dream_io: object | None = None    # the look-back's worker: not a device
    learn: object | None = None       # learn.Learn: what MIDI and the hands complete
    media: MediaIO | None = None      # the media folder and channels (plan 32)
    render_watch: RenderWatch | None = None   # the render window's health (watchdog.py)
    undo: object | None = None        # undo.Undo of the panel's deck (plan 15 WP1)
    # every undo stack, each ticked once a frame (plan 44 D5b): each deck's and
    # the meta controller's. Empty (a host from a test): `undo` alone
    stacks: tuple = ()
    # every opened render output's window settings, output 1's (`output`)
    # first; each applied once a frame (plan 21 WP3)
    outputs: list = field(default_factory=list)
    # the deck (deck.py, plan 44 D1): the bundle `reg`, `view`, `router`,
    # `lfos`, `renderer`, `learn` and `undo` above belong to
    deck: Deck | None = None
    # the decks off air (plan 44 D4): each runs its scene-setters, its pass
    # and its integrator in the frame; nothing else in the frame touches them
    off_air: list = field(default_factory=list)
    # the pointers `Host`'s handles read through (plan 44 D5a, below); None (a
    # host from a test): the handles are what was assigned
    on_air_pointer: Pointer | None = None
    panel_pointer: Pointer | None = None
    keys_pointer: Pointer | None = None     # the keys' own: key rows and ↑/↓
    # the crossfader and the decks (deck.MetaController): `frame` ticks it first, so
    # every handle above reads the frame's deck on air from the frame's first line
    meta: MetaController | None = None
    # makes the render context current: what `frame` runs a hot reload's hooks in
    # (audit V8). None (a host from a test): whatever is current
    render_current: Callable[[], None] | None = None
    # the world objects (world.py, plan 59): the shape and the hands, stepped
    # once a frame after the integrator (`_step_world`). None: no world step
    world: worlds.World | None = None

    @property
    def adapters(self) -> tuple:
        """What `close_all` closes, in shutdown order: the media channels
        and folder (plan 32: their sources go before the devices that may
        feed them), the registry (every device, last listed first — the pad
        included) and the dream worker."""
        return (getattr(self, "media", None), self.devices, self.dream_io)

    @property
    def pad(self):
        """The open `gamepad.Pad`, or None (the pad device runs the
        sticks' camera job itself, plan 27 B2)."""
        return self.devices.adapter("gamepad") if self.devices is not None else None


# plan 44 D5a: `frame`'s flat handles read through the pointers. The outputs,
# the pass and the sinks' fallback are the deck on air's; Learn and the undo
# that is ticked are the panel's (D5b ticks every deck's). Set after the class,
# so the dataclass keeps them as required fields of its `__init__`
for _handle in ("reg", "view", "router", "lfos", "renderer"):
    setattr(Host, _handle, Through(_handle, via="on_air_pointer"))
Host.deck = Through(None, via="on_air_pointer")
Host.deck.name = "deck"
for _handle in ("learn", "undo"):
    setattr(Host, _handle, Through(_handle, via="panel_pointer"))


def _off_air(h: Host, what: str, step: Callable[[Deck], object]) -> str:
    """`step` on each deck off air (plan 44 D4), a raise costing the on-air
    deck nothing; what the first raised, "" when none did."""
    said = ""
    for d in h.off_air:
        try:
            step(d)
        except Exception as e:  # noqa: BLE001 — deck 2 must not cost the on-air deck
            said = said or _err(f"deck off air: {what}", e)
    return said


def frame(h: Host, now: float, dt: float, fps: float) -> bool:
    """One frame, in the order ARCHITECTURE §2 states: the scene-setters
    (keys, loop keys, the devices polled — pad, MIDI — the macros' base
    subscribers) write bases, and the undo watcher compares them
    (`undo.tick`, plan 15); the sources feed the table (output, mouse,
    audio, the devices' feeds — hands, bridge); the pass lands offsets in
    dependency order, the LFOs stepping inside it (`router.modulate`, plan
    28 N0), then `reg.apply`; the sinks send (`devices.send`,
    plan 27 B3), `integrate`; then the two windows draw. Returns False
    when a guarded block raised — the error is on `reloader.runtime_error`
    and the loop goes on, so the next save can fix it. `imgui.new_frame()`
    has already run (main): `keys.typing` is this frame's value.

    Plan 44 D4 (row 625): a deck off air (`Host.off_air`) sets its macros'
    bases beside the on-air deck's and runs its pass and apply straight
    **after** the on-air deck's, so what it reads of a shared meta param (a
    route's scale on `master.gain`) is this frame's, landed by the on-air
    deck, the meta controller's lead; then its integrator.

    Plan 44 D5d: the crossfader comes first of all (`MetaController.tick`), so the
    deck arriving on air is the one this frame's `dim`, `bands` and `max_frame` go
    to, and `reg` and `router` here are that deck's."""
    ok = True
    if h.meta is not None:
        try:
            h.meta.tick(now, dt)
        except Exception as e:  # noqa: BLE001
            ok, h.reloader.runtime_error = False, _err("crossfader", e)
    reg, keys, router, reloader = h.reg, h.keys, h.router, h.reloader
    # the router's shared half (routing_sources.Sources, plan 44 D2): where
    # the audio lanes' names and the devices' feeds go — the router's own,
    # so the pad's lanes (fed through the router in `devs.poll`) and every
    # other feed land in one place
    sources = router.sources
    # the keys' own deck (plan 44 D5a): their rows and ↑/↓
    on_keys = h.keys_pointer.deck if h.keys_pointer is not None else h
    h.clock.tick(now)   # the clock's "now" for the frame: a trigger and the LFO step agree

    # the chain object is recreated on source attach; keep bindings fresh
    h.control.chain = h.audio.chain
    # the render context current for a reload's `on_reload` hooks: they build the
    # renderer's vertex arrays and framebuffers, which no other context can use
    # (audit V8, decided in SC3a). Every frame, as the poll can't say beforehand
    if h.render_current is not None:
        h.render_current()
    reloader.poll()     # its own throttle clock (monotonic): a file watch, not a frame clock

    # ---- polled keys, from either window ----
    # Esc does not quit: it is too easy to hit mid-show (Q, Ctrl+C or the
    # window's close button do)
    if keys.pressed(glfw.KEY_Q):
        h.quit()
    shift = keys.shift()
    # Cmd+R restarts; it claims R's edge first, so the table's `key:R`
    # (camera.reset) never hears it — a press with ⌘ held is the loop's
    if keys.super() and keys.pressed(glfw.KEY_R):
        h.restart()
    # ⌘[ / ⌘] go back / forward through the side pane's views, as a browser
    # does — a section, or the selection with the node it showed; they claim
    # [ and ]'s edge the same way, so brightness (the table's bare [ ]) never
    # hears them
    hist = getattr(h.panel, "history", None)    # (a panel from before a hot reload)
    if hist is not None:
        hist.note(view_of(h.panel))             # however the view changed since
        if keys.super():
            for key, by in ((glfw.KEY_LEFT_BRACKET, -1), (glfw.KEY_RIGHT_BRACKET, 1)):
                if keys.pressed(key) and (view := hist.step(by)) is not None:
                    go_view(h.panel, view)
    on_keys.router.keys(keys)   # key rows: B / ⇧B, R, F1–F8 / ⇧F1–F8, and the rest
    # ↑/↓ ride depth4 toward its range limit, accelerating with hold
    for key, sgn in ((glfw.KEY_UP, 1.0), (glfw.KEY_DOWN, -1.0)):
        hold = keys.held(key, now)
        if hold > 0.0:
            ramp = min(hold / D4_RAMP, 1.0)
            rate = D4_RATE0 + (D4_RATE1 - D4_RATE0) * ramp * ramp
            _ride_depth(on_keys.reg["view.depth4"], sgn * rate * dt)

    # ---- the devices, polled (devices.py, plan 27): the pad (a second
    # hand on the same controls — imgui never claims it, so it works even
    # while the panel has keyboard focus; a press that completes an armed
    # learn does not also fire its old row) delivers its rows, then runs
    # the sticks' default camera job (gamepad.steer, plan 27 B2: each axis
    # no route names, a relative move on the base); each MIDI desk applies
    # its rows; the hands and the bridge feed below. A device that raises
    # records itself on the registry; the frame goes on and `ok` keeps the
    # note alive until a clean frame ----
    devs = h.devices
    if devs is not None:
        devs.poll(dt, now, router=router, learn=h.learn)
        if devs.error:
            ok, reloader.runtime_error = False, devs.error

    # ---- the media channels (plan 32): each follows its slot — a source
    # opened or closed, never decoded here — and a clip's transport steps
    # on the bases the devices just wrote ----
    media = getattr(h, "media", None)
    if media is not None:
        try:
            media.poll(dt, now)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("media", e)

    # ---- the macros' base subscribers: the last scene-setter — a macro
    # whose base moved (a knob just now, the panel last frame, a restore)
    # sets its subscribers' bases before any source feeds (plan 13 §2.4) ----
    try:
        router.follow_macros()
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("macros", e)
    if said := _off_air(h, "macros", lambda d: d.router.follow_macros()):
        ok, reloader.runtime_error = False, said

    # ---- undo: every scene-setter of this frame has written its base
    # (the panel's edits are last frame's tail), so compare the bases and
    # the loadable patch's table against last frame's — a change opens a step, a
    # settle time closes it. No performer has run yet; a performer writes a
    # base only on a step it holds open (undo.py, plan 15 WP1; plan 51 O2) ----
    for stack in h.stacks or (h.undo,):
        if stack is None:
            continue
        try:
            stack.tick(now)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("undo", e)

    # ---- output: the render window follows the output.* params; a later
    # render output follows its config entry (plan 21 WP3) ----
    h.output.apply()
    for out in h.outputs:
        if out is not h.output:
            out.apply()
    h.renderer.bg_alpha = h.output.bg_alpha
    # the master dim (plan 15 WP3), the frame's last pass; getattr: an
    # Output made before a hot reload brought the attribute has none
    h.renderer.dim = getattr(h.output, "dim", 1.0)
    # the render cap (output.render): the frame's size, whatever the screens
    h.renderer.max_frame = getattr(h.output, "max_frame", None)

    # ---- mouse: orbit / pan / zoom, render window only ----
    h.mouse.poll(shift)

    # ---- audio + rotation + draw, guarded: hot-reloaded code may raise;
    # record it and keep the loop alive so the next save can fix it ----
    try:
        audio = h.audio
        audio.step(dt)
        audio.publish(sources)      # the lanes' names, like every source (R8)
        chain = audio.chain if audio.on else None
        if devs is not None:
            # the devices' feeds: the hands feed `hand` (and complete a
            # hand Learn), the bridge feeds `ext` (its out half is a sink,
            # below) — each guarded by the registry, the first error the toast's
            devs.feed(sources)
            if devs.error and ok:
                ok, reloader.runtime_error = False, devs.error
        # the lanes are a modulation source like any other (routing.py);
        # once every source has spoken for this frame, the pass runs the
        # patch in dependency order — the LFOs step inside it, on the
        # frame's clock, each after the knobs it reads (plan 28 N0) — and
        # `reg.apply` lands base + offsets on the rest before the
        # integrator reads them
        router.modulate(chain, dt, now)   # dt: the rows' motion; now: the LFOs'
        reg.apply()

        def off_air_pass(d: Deck) -> None:
            d.router.modulate(chain, dt, now)
            d.reg.apply()
        if said := _off_air(h, "pass", off_air_pass):
            ok, reloader.runtime_error = False, said
        if devs is not None:        # the sinks read effective values out (plan 27 B3)
            devs.send(reg, chain)
            if devs.error and ok:
                ok, reloader.runtime_error = False, devs.error
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("step", e)
    # the integrator on its own (K3, row 578): the turn, the field's motion
    # and the media path keep moving through a step that raised every frame
    try:
        h.view.integrate(dt)
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("view.integrate", e)
    if said := _off_air(h, "integrate", lambda d: d.view.integrate(dt)):
        ok, reloader.runtime_error = False, said
    # the world (plan 59): the shape's home from this frame's params, the
    # puppets (the palms, read after HandsIO.poll), then the physics' fixed
    # steps; the render below reads the poses
    try:
        _step_world(h, dt)
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("world", e)
    # the analyzer's lanes as a route reads them (out / CEIL), for the
    # patterns that draw the bands themselves (u_levels, plan 22 B3): render
    # input, read-only, like the dim — never a param
    h.renderer.bands = _bands(h.audio)
    watch = h.render_watch
    if watch is not None:     # a NaN / inf a param dropped: named once in the stall log
        watch.nonfinite(getattr(reg, "nonfinite", ()))

    # ---- render window, then the control window. A raising draw leaves
    # the render window on its last frame while the panel goes on — the
    # render watch logs it (traceback, once per error) and the control
    # window's red banner names it, until dismissed ----
    try:
        h.draw_render(dt)
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("render.draw", e)
        if watch is not None:
            watch.failed(e, now)
    else:
        if watch is not None:
            watch.drew(now)
    try:
        h.draw_panel(dt, fps)
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("panel.draw", e)
    if ok:
        reloader.runtime_error = ""
    if watch is not None:     # no presented render frame for 2 s: logged, bannered
        watch.tick(now)

    if h.panel.restart_requested:
        h.panel.restart_requested = False
        h.restart()
    return ok


def palm_in_world(skel: dict, cal: np.ndarray):
    """A `hands.core.skeleton`'s palm in the world (plan 59, the hand objects'
    puppets): (position (3), rotation 3×3), through calibration `cal` (Leap mm
    → world, `ghost.calibration`) — the transform the ghost hand is drawn
    through, so the position is where its palm is drawn. The rotation's columns
    are `hands.room.palm_axes` (right, up, back) of the palm through the
    calibration's turn: a proper rotation, mirror or not. None for a palm that
    gives no frame. Here, not in ghost.py: `hands` is the meta controller's,
    and the render stack does not reach it (tests/test_layer_boundary.py)."""
    from .hands.room import palm_axes  # lazily: importing app imports no hands adapter

    p = cal @ np.array([*map(float, skel["palm"]), 1.0])
    t = (cal[:3, :3] / max(float(np.linalg.norm(cal[:3, 0])), 1e-12)).tolist()   # s · R, s off
    turn = ((t[0][0], t[0][1], t[0][2]), (t[1][0], t[1][1], t[1][2]), (t[2][0], t[2][1], t[2][2]))
    axes = palm_axes(skel["normal"], skel["direction"], turn)
    if axes is None or not np.isfinite(p).all():
        return None
    return p[:3].copy(), np.array(axes, dtype=np.float64).T


def palms_in_world(gh) -> dict:
    """side → `palm_in_world` for the hands `gh` (a `ghost.Ghost`) has this
    frame, through the calibration it draws with (`Ghost.calibrated`: the
    tracking mode, `ghost.mirror`, the box and hands.json's units) — whether or
    not the ghost hands are shown. A side not seen is missing; no tracker, {}."""
    src = getattr(gh, "source", None)
    skel = (getattr(src, "skeleton", None) or {}) if src is not None else {}
    if not skel:
        return {}
    cfg = getattr(src, "cfg", None) or {}
    m = ghosts.basis(cfg.get("mode", "desktop"), bool(getattr(gh.state, "mirror", False)))
    cal = gh.calibrated(ghosts.box_of(src), m, getattr(src, "units", None))
    return {side: palm_in_world(sk, cal) for side, sk in skel.items()}


def _step_world(h: Host, dt: float) -> None:
    """The world's frame (plan 59, ARCHITECTURE §2 step 13a): the shape
    object's home is `camera.zoom` / `camera.pan` as they landed this frame
    (the on-air deck's view), the hands' puppets read the palms through the
    ghost hands' calibration (`palms_in_world`), then the physics steps."""
    world = h.world
    if world is None:
        return
    view = h.view
    world.home(worlds.SHAPE, worlds.shape_home(view.zoom, view.pan))
    # plan 60: the on-air deck's grip (a patch's own, `reg.grip`) sets the shape's
    # body, joint and clutches; a deck switch hands the one world to the other's
    state = getattr(getattr(h, "reg", None), "grip", None)
    if not isinstance(getattr(state, "on", None), bool):     # no grip on this registry
        state = None
    if state is not None:
        router = h.router
        grip.apply(world, state, lambda address: grip.lane_closed(router, address))
    world.frame(dt, palms_in_world(getattr(h.renderer, "ghost", None)))
    if state is not None:
        grip.publish(getattr(h, "router", None), world, state)   # `grip:*`, the next frame's


def _hot_error_toast(msg: str) -> None:
    """The hot-reload failure notice, top-left of the control window."""
    imgui.set_next_window_pos(imgui.ImVec2(12, 12), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.7)
    imgui.begin(
        "##hoterr", None,
        imgui.WindowFlags_.no_decoration
        | imgui.WindowFlags_.always_auto_resize
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_focus_on_appearing
        | imgui.WindowFlags_.no_nav,
    )
    imgui.text_colored(imgui.ImVec4(1, 0.4, 0.3, 1), f"HOT RELOAD  {msg}")
    imgui.text_disabled("last good code keeps running — fix the file and save")
    imgui.end()


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    """The command line. ``--laptop`` (or ``--single``): no projector on
    this machine — config.laptop reads the show machine's config for one screen."""
    p = argparse.ArgumentParser(prog="hyperspace", description="Real-time 4D polytope visualizer.")
    p.add_argument("--laptop", "--single", action="store_true",
                   help="one screen, no projector: the render output is a plain window "
                        "(no fullscreen, no overlay, no later outputs) and the controls "
                        "come to the front; this Mac's remembered window spots are "
                        "neither used nor overwritten")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _args(argv)                    # before GLFW: --help prints and exits here
    # before GLFW too: a Ctrl-C during the seconds of startup below is a quit,
    # not a traceback out of half-built windows
    quitting = _install_quit_signals()
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise")
    cfg = config.load()                   # before the windows: [output] overlay is a creation hint
    if args.laptop:
        config.laptop(cfg)
    home = library_home()                 # the folder config.load has just ensured
    # the controllers both Macs share, from the library's configured path: before anything
    # reads `cfg`'s device tables, and whether or not that folder is mounted
    device_list = DeviceList.open(cfg, home)
    # which display shows what, likewise (SC2). --laptop leaves the rows alone: not read,
    # not written, not seeded (config.laptop's one plain window, as ever)
    display_list = (None if args.laptop else
                    DisplayList.open(cfg, home, placement.screens(glfw), (RENDER_SIZE, CONTROL_SIZE)))
    want = None if display_list is None else wanted(display_list.current, placement.screens(glfw))
    # the players, on this Mac (plan 55): beside bindings.json, before the devices
    # read who holds what
    players = Players.load(home, cfg.setdefault("notes", []))
    # (a rename the list's first read made: before the devices open, so they open right)
    for old_role, new_role in device_list.take_renames():
        players.rename(old_role, new_role)
    # the window that holds the render context, hidden, which no unplug can take
    root_win = _root_window()
    # the render outputs (plan 21 WP3: one per [[output.screens]] entry, one
    # with no list) and the controls; output 1's window is the render window.
    # On a laptop the show machine's windows.json is not read: its spots are the show machine's
    slots, ctrl_win = _windows(_overlay_allowed(cfg), cfg, None if args.laptop else home, root_win, want)
    render_win = slots[0].win                 # None when no display shows output 1 (SC2)
    if args.laptop:
        glfw.focus_window(ctrl_win)       # the controls in front of the render window

    # the render side: moderngl on the root's context — it renders every
    # output's frame (fork F12); the first live output's window paces the loop
    # (fork F6, `pacing.Pacer`)
    glfw.make_context_current(root_win)
    glfw.swap_interval(0)
    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    # the world objects (plan 59): one world, the renderers' (deck 2's is a sibling)
    world = worlds.World.default()
    renderer.world = world
    root = Root(root_win, Offscreen(ctx), Pacer(glfw), logical=RENDER_SIZE, size=RENDER_SIZE)
    # each output: a presenter on its own context, none waiting yet
    _open_presenters(slots, root_win, notes=cfg.setdefault("notes", []))
    root.pacer.choose(_slot_windows(slots), root_win)
    # the outputs published out (plan 32 T9), the root's context current
    _open_publishers(slots, ctx, cfg.setdefault("notes", []))

    # the control side: imgui on the control window's context. Its swap
    # never waits for a vblank — two vsynced swaps a frame would halve the
    # rate — so it paces itself off the render window.
    glfw.make_context_current(ctrl_win)
    glfw.swap_interval(0)
    # a handle on the control context: it clears the window each frame and
    # owns the GRAPH canvas's tap textures (`CanvasTap`, 2026-11-02), which
    # `replay.grab` draws into after imgui's render. Rebinding its `screen`
    # through moderngl reapplies the viewport moderngl noted at creation,
    # not the window's size now; `grab` puts the viewport back itself, and
    # the backend's `impl.render` sets its own at the start of every frame
    ui_gl = moderngl.create_context()
    ui_ctx = imgui.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(ctrl_win)
    install_pinch()     # the trackpad's pinch, which GLFW drops: GRAPH zooms on it
    io = imgui.get_io()
    # hot-reloaded panel code can raise mid-window; let imgui unwind the
    # stack itself instead of asserting the process away
    io.config_error_recovery = True
    io.config_error_recovery_enable_assert = False

    audio = AudioEngine()
    audio.rescan()                         # the one PortAudio scan, here at startup — never mid-set on a first read
    control = Control(audio.chain)
    # loadable patches, projects, the loadable patch bank (its project's): in the home, or in
    # the folder [library] path names (plan 25) — the machine files
    # (config, bindings, windows, logs, last_show) stay in the home either way
    # A config.toml that doesn't read says nothing of [library]: the library is where this
    # Mac's copy says it last was, not the home, whose saves the next good launch would lose
    lp = cfg.get("library", {}).get("path", "")
    lib_root, unknown = sharedfile.library_root(lp, bool(cfg.get("error")), home / DISPLAYS_COPY,
                                                home, DISPLAYS_FILE)
    library = (Library(home / CONFIG_UNREAD, machine=home) if unknown
               else Library() if lib_root == home else Library(lib_root, machine=home))
    if library.not_moved:
        print(f"library: {library.not_moved}", file=sys.stderr)
        library.say(warning=library.not_moved)
    # the media folder and the eight channels (plan 32): the channels'
    # params are declared over this one `MediaState`, the loadable patch's bins are
    # its, and the renderer reads its frames
    media = _open_media(str(lib_root) if lib_root != home and not unknown else "", home)
    renderer.media = media.state
    # dream.* drives the renderer's look-back (lookback.py); the post pass
    # runs inside renderer.draw
    panels: list = []                  # app.restart raises the panel's flag; frame() polls it
    # an analyzer loadable patch carries its band layout; the library hands it to
    # control before restoring values (07-overhaul contracts)
    library.on_layout("band", control.apply_layout)
    # …and a saved band preset carries the layout back out (audit A2); the
    # scene combo and the strip keep each other posted (audit A1)
    library.extra("band", lambda: {"layout": audio.chain.layout()})
    library.on_load("band", control.scene_loaded)
    control.library = library

    # the deck (deck.py, plan 44 D1): the registry, the view state, the
    # table, the router, the banks, the loadable patches, learn and undo,
    # built by `Deck.build` in the order these lines had here. The meta controller
    # objects built between its lines — the hands' setup, the outputs, the
    # panel, the devices — are the hooks below, each run at its old place
    made = DeckHooksMade()          # what each hook below returned, filled by Deck.build
    mix = Mix()               # output.xfade and its seconds (plan 44 D4)
    rendering = [renderer]    # the renderers whose segment workers an exit closes

    def hands_setup(reg: Registry):
        return _hand_settings(reg, cfg)       # before attach: "default" includes them

    plug: Hotplug | None = None         # displays coming and going; made once the panel is

    def outputs_setup(reg: Registry) -> Output:
        # the render window's placement registers before attach, so "default"
        # includes output.* and reset / the dirty dot see them (audit L6)
        output = _make_output(render_win, reg, cfg)
        register_xfade(reg, mix)               # the deck fade (plan 44 D4): meta controls
        slots[0].output = output
        for sl in slots[1:]:                   # no params: the config says (fork F10)
            if sl.opened:
                sl.output = _later_output(sl)
        for sl in slots:                       # a further display's: likewise (SC2)
            for also in sl.also:
                also.output = _also_output(also)
        # each opened output's switches (plan 21 WP4): meta settings, seeded
        # from the config's launch values already on the slots, never saved
        register_switches(reg, slots)
        return output

    def load_table(reg: Registry) -> Bindings:
        # one binding table for keys, pad, MIDI and lanes (an old midi_map.json
        # migrates) — read before attach for the same reason: the desk's
        # shared meta param, `desk.slew`, is the table's, at the app's default
        # until the show says otherwise
        mc = cfg.get("midi", {})
        return _desk_table(reg, Bindings.load(
            bindings_path(home), mc.get("profile", "apc40"),
            Path(mc.get("map", "midi_map.json")),
        ))

    def panel_setup(reg: Registry, s: ViewState, *, clock, lfos, envs, seq,
                    output) -> Panel:
        # the Joy-Con totem (plan 47, an experiment): off unless `[totem] on`
        # says so or the pad window's word is clicked; never saved, so it may
        # register after attach (a fresh extra, library.py); `s` for the reset
        totem.register(reg, totem.TotemState())
        if totem.configured_on(cfg):
            reg["totem.on"].set(True)
        # the Joy-Con as a poi's handle (plan 47, the poi): likewise; its
        # dials start from `[poi]` (weight, length, spring, gravity, drag,
        # hand, depth), the only way they outlast a launch
        poi_cfg = poi.configured(cfg)
        swing = poi.PoiState()
        poi.register(reg, swing, poi_cfg)
        renderer.poi_source = swing          # its guide over the outputs (poi_guide.py)
        if poi_cfg.get("on") is True:
            reg["poi.on"].set(True)
        # after attach, before the router: its ui.* params are the last a
        # launch declares before the table's rows resolve; `output` is what
        # the outputs hook returned
        if output is None:
            raise RuntimeError("Deck.build: the panel hook needs the outputs hook's Output")
        panel = Panel(control, audio, s, renderer, library.install, registry=reg, library=library)
        panels.append(panel)
        panel.graph_start_zoom = placement.window_zoom(glfw, ctrl_win)   # plan 58 SM2
        panel.clock, panel.lfos = clock, lfos     # the LFO page's scopes and beat light
        panel.envs, panel.seq = envs, seq         # plan 31: what a SEQ page draws
        panel.output = output
        panel.outputs = slots                  # the OUTPUT page: a block per output (plan 21 WP4)
        if display_list is not None:           # …and a row per display (SC2)
            panel.displays = Running(display_list, lambda: placement.screens(glfw), slots,
                                     opened_of(slots, want.control if want is not None else None))
        panel.preview = Preview(ctx)           # output 1 behind the GRAPH page (2026-10-26)
        panel.monitor = Preview(ctx)           # on the deck off air, what is on air's inset there
        panel.canvas_tap = CanvasTap(ui_gl)    # the GRAPH canvas as `panel:graph` (2026-11-02)
        return panel

    def devices_setup(reg: Registry, router: Router, learn: Learn, *, panel,
                      hand_settings) -> _DevicesMade:
        # `panel` and `hand_settings` are what those hooks returned
        if panel is None:
            raise RuntimeError("Deck.build: the devices hook needs the panel hook's Panel")
        panel.learn = learn
        panel.router = router                  # the ROUTING page edits the live table
        # the devices (devices.py, plan 27 B1): the pad, MIDI, the hands and
        # the bridge, each opened behind its `[[devices]]` entry (the old
        # tables translated), polled by `frame` through the registry. What
        # holds an adapter — the panel (Learn's hints, the desk page, the HANDS
        # page, the Learn pad menu) and the ghost renderer (the tracker's
        # skeletons) — is pointed at it now and again whenever the list changes
        device_reg = _open_devices(cfg, devices.Context(reg=reg, table=router.table, learn=learn,
                                                 audio=audio, hand_settings=hand_settings,
                                                 notes=cfg.setdefault("notes", []), home=home,
                                                 players=players),
                            home, store=device_list)

        def point_at_devices() -> None:
            panel.midi = device_reg.adapter("midi")         # the first desk listed: the APC40's page
            # the pad window's and the menu's "Learn pad": the first pad
            # with a controller behind it now, re-picked on every connect
            panel.pad = device_reg.live_adapter("gamepad")
            panel.hands = device_reg.adapter("hands")
            for r in rendering:                      # either deck can be on air (D5c)
                r.ghost.source = panel.hands         # no tracker, nothing draws
            router.follow_devices()                  # the MIDI roles and row schemes, again
        # schemes from the registry (plan 27 B2): the router asks it which
        # sources are lanes and in what order the pages offer them, the learn
        # what can be armed — each handed the registry, importing nothing
        router.use(device_reg)
        learn.devices = device_reg
        device_reg.listeners.append(point_at_devices)
        # plan 40 T4: a device coming or going, said in the footer with what it brings
        device_reg.said = lambda role, was, now: library.say(
            devices.arrival(device_reg.table_of(role, router.table), device_reg, role, was, now) or None)
        point_at_devices()
        panel.devices = device_reg                        # the SYSTEM page's device lines
        panel.media = media                        # the MEDIA page: the folder and the channels
        renderer.ghost.router = router           # the guide lights what the table routes
        renderer.cloud_source = device_reg              # cloud:<role> → the scene's point clouds (A4b)
        # (the bus cuts: the renderer reads the loadable patches, `Deck.build` — plan 44 D3)
        media.state.resolver.devices = device_reg       # ndi: / syphon: / camera: ids → live feeds (plan 32 T8)
        # the GRAPH canvas (2026-11-02); `on_page` is the panel's own fact, read
        media.state.resolver.builtin[PANEL_GRAPH] = PanelSource(
            panel.canvas_tap, on_page=lambda: panel.canvas_px is not None)
        panel.hand_settings = hand_settings
        dream_io, panel.dream_error = _open_dream(reg, cfg)
        if dream_io is not None:            # what the dream node dreams with (plan 36 T4)
            renderer.dreamer.source = dream_io
        renderer.segment_cfg = cfg.get("segment", {})   # the segment workers' backend (plan 39 T4)
        # …closed with the adapters, at quit and restart — deck 2's too (plan 44 D4)
        segmenters = _Closer(lambda: _close_each([r.close for r in rendering]))
        awake = _open_awake(cfg)               # no screensaver over the show
        return _DevicesMade(device_reg, dream_io, awake, segmenters)

    restart = lambda: [setattr(p, "restart_requested", True) for p in panels]
    # the meta controller's params, with what any deck's registry reads as it is built
    meta_reg = build_meta(control, audio, restart, media=media.state)
    worlds.register(meta_reg, world)          # `world.reset`: one world, every deck
    meta_reg.dial_launch = _dial_launch(cfg)
    deck = Deck.build(library=library, control=control, audio=audio, table=load_table,
                      renderer=renderer, media=media.state, restart=restart, meta_reg=meta_reg,
                      hands=hands_setup, outputs=outputs_setup, panel=panel_setup,
                      devices=devices_setup, made=made, warm=True)
    hand_settings, output, panel = made.hands, made.outputs, made.panel
    device_reg, dream_io, awake, segmenters = made.devices
    s, reg, router = deck.view, deck.reg, deck.router
    clock, loaded_patch, undo_obj = deck.clock, deck.loaded_patch, deck.undo
    panel.undo = undo_obj              # the footer's message slot
    panel.deck = deck                  # plan 44 D1: beside its handles; D5 reads through it
    # deck 2 (plan 44 D4): its own look over the same meta controller, sources and
    # clock, and a renderer of its own states on the render context (which is
    # not current here: the control window's is). Nothing points at it: no
    # controller, no page, no undo, no file. Built now, not on a fade's first
    # frame: compiling its shaders then would stall the room (rec, row 648)
    glfw.make_context_current(root_win)
    renderer2 = renderer.sibling()
    glfw.make_context_current(ctrl_win)
    renderer2.segment_cfg = renderer.segment_cfg
    # the meta controller's wires, on both (plan 44 D5c): either deck can be on air
    renderer2.cloud_source, renderer2.poi_source = renderer.cloud_source, renderer.poi_source
    renderer2.ghost.source = renderer.ghost.source
    channels2 = Channels(sources=media.state.sources)
    renderer2.media = channels2
    rendering.append(renderer2)
    deck2 = Deck.beside(deck, renderer=renderer2, media=channels2)
    renderer2.ghost.router = deck2.router       # the guide lights what its table routes
    deck2.learn.devices = device_reg                   # what can be armed, on either deck's Learn
    _share_experiments(deck.reg, deck2.reg, poi_cfg=poi.configured(cfg))
    # the owner of the two decks (plan 44 D5a): every holder's pointer, each on
    # deck 1 and moved by nothing yet. Each handle reads through its own from here
    meta = MetaController(deck, deck2, players, mix=mix)
    fade = Fade(deck, deck2, mix, ctx, dream=dream_io, pointer=meta.on_air_pointer)
    media.seat(meta)
    fade.said = lambda text: library.say(warning=text)    # a warm draw's failure, at once
    panel.fade = fade                  # the SYSTEM page's second GPU block
    panel.pointer = library.pointer = meta.panel_pointer
    panel.meta_undo = meta.undo        # the footer's message slot, beside the deck's
    panel.meta = meta                  # GRAPH's head: the deck it shows, the two verbs
    # the playlist (plan 44 D6b): ticked by the meta controller, said in its pane section
    meta.playing = panel.playing = playlist.Playing(meta, library, fade)
    playlist.register(deck.reg, meta.playing)
    playlist.at_launch(meta.playing, library.install)     # SM6: `plays` in the install file
    # what ⌘Z goes by (plan 44 D5b); read off the class each time, as a reloaded
    # `ui.py` re-classes the panel and a bound method would keep the old function
    undos.where(lambda: panel.in_meta_section())
    device_reg.point(meta.pointer, meta.panel_pointer)
    node_desk.install(meta, device_reg)     # N1a: what each deck's patch points its desks at
    # plan 55: who holds what names a pad's rows, so the list is read again when it
    # changes; a mapping on either deck moves the controller mapped
    meta.on_players.append(lambda: device_reg.apply(device_reg.entries))
    device_reg.renamed = meta.rename_controller
    meta.presence = lambda role: device_reg.presence(role)        # what an undo of a move asks
    device_reg.listeners.append(lambda: meta.reseat())    # the list can change who holds a role
    for on in meta.decks:
        on.learn.mapped = lambda b, on=on: device_reg.mapped(on, b)
    # panel state and chain must stay one object even after source changes
    # the live objects that get re-classed on a hot reload; re-evaluated
    # each swap so recreated ones (the chain after a source attach) count
    reloader = HotReloader(targets=lambda: [
        # the deck's objects (deck.py, plan 44 D1): the renderer and its
        # parts, the view state, the registry and every param, the marks,
        # undo, the router, the loadable patches, learn and the banks
        *deck.targets(),
        # deck 2 (plan 44 D4), its channels, and the fade
        *deck2.targets(),
        *meta.targets(),
        (channels2, "media.channels", "Channels"),
        *[(ch, "media.channels", "Channel") for ch in channels2.channels.values()],
        (fade, "deck", "Fade"),
        (mix, "deck", "Mix"),
        (media.state, "media.channels", "Channels"),          # plan 32 (plan 44 D3: its new name)
        (media.state.sources, "media.channels", "MediaSources"),   # plan 44 D3: the meta controller's half
        *[(ch, "media.channels", "Channel") for ch in media.state.channels.values()],
        (media.folder, "media.folder", "MediaFolder"),
        (panel, "ui", "Panel"),
        *([(panel._pad_nvg, "ui_pad_nvg", "Surface")] if "_pad_nvg" in panel.__dict__ else []),
        (control, "control", "Control"),
        (audio, "audio", "AudioEngine"),
        (audio.chain, "analyzer", "Analyzer"),
        *[(p, "bands", "Params") for p in audio.chain.params],
        *([(audio.analyser, "analysis", "Analyser")] if audio.analyser is not None else []),
        (output, "overlay", "Output"),
        (output.backend, "overlay", "GlfwBackend"),
        # the later render outputs (plan 21 WP3); a presenter rebuilds its
        # programs at its next present, in its own context
        *[(sl.output, "overlay", "Output") for sl in slots[1:] if sl.output is not None],
        *[(sl.output.backend, "overlay", "GlfwBackend") for sl in slots[1:] if sl.output is not None],
        *[(sl.presenter, "outputs", "Presenter") for sl in slots if sl.presenter],
        *[(a.output, "overlay", "Output") for sl in slots for a in sl.also],
        *[(a.output.backend, "overlay", "GlfwBackend") for sl in slots for a in sl.also],
        *[(a.presenter, "outputs", "Presenter") for sl in slots for a in sl.also],
        *([(display_list, "displays", "DisplayList")] if display_list is not None else []),
        *([(plug, "hotplug", "Hotplug"), (plug.backend, "overlay", "GlfwBackend"),
           *[(h.output, "overlay", "Output") for h in plug.held],
           *[(h.presenter, "outputs", "Presenter") for h in plug.held]] if plug is not None else []),
        (root, "outputs", "Root"),
        (root.frame, "outputs", "Offscreen"),
        (root.pacer, "pacing", "Pacer"),
        (root.pacer.floor, "pacing", "Floor"),
        (library, "library", "Library"),
        (library.install, "library", "Install"),
        *([(hand_settings, "hands.core", "HandSettings")] if hand_settings else []),
        *([(dream_io, "dream", "DreamWorker")] if dream_io else []),
        # the devices' adapters, the shims and the registry (devices.py):
        # re-evaluated each swap, so a device the list brought in counts
        *device_reg.targets(),
        *world.targets(),         # plan 59: the world, its objects, bodies and puppets
    ], watchers=[library])
    if display_list is not None:
        # the windows follow the rows and the connected list from here on (SC3b)
        plug = Hotplug(glfw, panel.displays, root, ctrl_win, output, seen=placement.load(home),
                       hold_s=float(cfg.get("output", {}).get("unplug_hold_s", 3.0)),
                       sizes=(RENDER_SIZE, CONTROL_SIZE), title=TITLE,
                       overlay=_overlay_allowed(cfg), notes=cfg.setdefault("notes", []),
                       say=library.say, warn=lambda text: library.say(warning=text))
        panel.displays.plug = plug
        panel.displays.screens = lambda: plug.screens
    panel.reloader = reloader
    panel.config_error = cfg.get("error", "")   # a config.toml that would not parse
    if router.table.said:                       # what the launch did to bindings.json
        cfg["notes"].append(router.table.said)
    # …or that wants a section renamed, and what the device list did since
    # (the registry appends to this very list, so the page follows)
    panel.config_notes = cfg["notes"]
    # keys from every window (`hotplug.py` points them at what's open, as is the mouse)
    keys = Keys(render_win, ctrl_win, [w for w in _slot_windows(slots) if w is not render_win])
    mouse = Mouse(render_win, reg, s, slots[0].switches,          # the mouse: output 1 only
                  pointer=meta.pointer(MOUSE))

    def draw_render(dt: float) -> None:
        # every render output: drawn on the root's context, presented, the
        # pacing window swapped last (_draw_render); the deck on air
        on_air = meta.on_air
        _draw_render(on_air.renderer, ctx, on_air.view, slots, root, render_watch,
                     preview=panel.preview, monitor=panel.monitor, fade=fade,
                     panel_deck=meta.panel)

    titled = [None]                     # what the control window's title last said

    def draw_panel(dt: float, fps: float) -> None:
        # the control window: black ground, then the imgui frame opened
        # before the frame's input handling
        glfw.make_context_current(ctrl_win)
        ui_gl.clear(0.0, 0.0, 0.0, 1.0)
        panel.draw(dt, fps)
        # the deck the panel is on, as GRAPH's head says it (plan 44 D5d, DQ7)
        title = control_title(meta)
        if title != titled[0]:
            titled[0] = title
            glfw.set_window_title(ctrl_win, title)

    # the stall log (watchdog.py), <home>/stall.log: a 2 s whole-loop stall,
    # a raising render draw, or 2 s with no render frame presented while the
    # panel runs, each with every thread's stack; kill -USR1 dumps on demand
    watchdog = Watchdog(home / LOG_NAME,
                        loadable=lambda: meta.on_air.loaded_patch.current)
    # with two or more outputs the stall is "no output presented", and one
    # output dark while another presents is a warning naming it (WP3)
    # (a further display counts: its window is a picture too, SC2). What's open now, each time:
    # a display gone isn't a stall, and a picture that stopped still is (SC3b)
    def opened() -> list:
        return [*((sl.label, sl.output) for sl in slots if sl.opened and sl.output is not None),
                *((f"{sl.label} on {a.display}", a.output) for sl in slots for a in sl.also)]

    def first_state() -> dict:
        # output 1's window, else the first there is: a projector that stopped is said, whichever
        open_now = opened()
        return open_now[0][1].backend.window_state(open_now[0][1].win) if open_now else {}

    render_watch = RenderWatch(
        watchdog,
        info=first_state,
        outputs=lambda: [(label, o.backend.window_state(o.win)) for label, o in opened()])
    panel.watchdog, panel.render_watch = watchdog, render_watch

    def dream_check(on: Deck, name: str | None) -> None:
        # a loadable patch that asks for the dream — a dream node on (plan 36 T4:
        # `dream.on`) with a mix above 0 — with no worker to dream: the
        # dream passes its picture through. Said on the banner (until
        # dismissed), logged once. Echoes alone are a normal mode. The deck
        # it landed on, either (plan 44 D5a)
        if on.reg["dream.on"].base and on.reg["dream.mix"].base > 0 and dream_io is None:
            why = panel.dream_error or "[dream] enabled = false in config.toml"
            render_watch.warn(f"{name} turns the dream on, but there is no dream worker ({why}); "
                              "the dream passes its picture through")
    for on in meta.decks:
        on.loaded_patch.listeners.append(lambda name, on=on: dream_check(on, name))
        on.loaded_patch.listeners.append(lambda name, on=on: fade.ask_warm(on))
    dream_check(deck, loaded_patch.current)          # the startup loadable patch has already landed

    # both exits close the publishers, in the root's context (plan 32 T9)
    publishers = _Closer(lambda: _close_each((lambda: _close_publishers(root_win, slots),
                                              panel.preview.close, panel.monitor.close,
                                              fade.close)))

    def all_windows() -> list:            # both exits destroy these before terminate, the root last
        return [*(plug.windows() if plug is not None else ()),
                *(a.win for sl in slots for a in sl.also), *(sl.win for sl in slots[1:]),
                ctrl_win, slots[0].win, root_win]

    def save_windows() -> None:           # both exits: quit below, ⌘R in _restart
        if args.laptop:                   # the show machine's spots are kept for it
            return
        _save_windows(home, slots[0].win, ctrl_win, output, [sl.output for sl in slots[1:]], slots,
                      plug.away_spots() if plug is not None else None)

    # the flat handles are the deck's (plan 44 D1), so `frame` is unchanged
    host = Host(reg=deck.reg, view=deck.view, control=control, audio=audio, router=deck.router,
                clock=clock, lfos=deck.lfos, keys=keys, mouse=mouse, output=output,
                renderer=deck.renderer, panel=panel, reloader=reloader,
                render_current=lambda: glfw.make_context_current(root_win),
                draw_render=draw_render, draw_panel=draw_panel,
                restart=lambda: _restart(audio, (watchdog, awake, panel, *host.adapters,
                                                 publishers, segmenters,
                                                 *([display_list] if display_list else [])), impl,
                                         ctrl_win,
                                         save=save_windows, windows=all_windows()),
                quit=lambda: glfw.set_window_should_close(ctrl_win, True),
                devices=device_reg, dream_io=dream_io, learn=deck.learn, render_watch=render_watch,
                undo=deck.undo, media=media,
                outputs=_outputs_now(slots), deck=deck,
                off_air=meta.parked, stacks=meta.stacks, on_air_pointer=meta.on_air_pointer,
                panel_pointer=meta.panel_pointer, keys_pointer=meta.pointer(KEYS), meta=meta,
                world=world)

    def rewired() -> None:
        # what holds a window, as the displays came or went (`hotplug.py`)
        keys.render_win = slots[0].win
        keys.more = tuple(w for w in _slot_windows(slots) if w is not slots[0].win)
        mouse.aim(slots[0].win)
        host.outputs[:] = _outputs_now(slots)

    if plug is not None:
        plug.wired = rewired
        plug.start()

    # smoke-test escape hatch: HYPERSPACE_FRAMES=n closes after n frames
    frames_left = int(os.environ.get("HYPERSPACE_FRAMES", "0")) or None

    watchdog.start()          # last, so startup is not a stall
    # and the handlers again: anything opened above (PortAudio, a driver) may
    # have installed its own SIGINT handler over ours
    _install_quit_signals(quitting)

    last = time.perf_counter()
    fps = 0.0
    # the loop ends when a person closes a window (the smoke run closes output 1), or when
    # a Ctrl-C asked (`_install_quit_signals`). A window whose display went is
    # `hotplug.py`'s to close, and is in no slot by then
    try:
        while not (quitting.asked
                   or any(glfw.window_should_close(w) for w in _slot_windows(slots))
                   or glfw.window_should_close(ctrl_win)):
            if frames_left is not None:
                frames_left -= 1
                if frames_left <= 0:
                    glfw.set_window_should_close(ctrl_win, True)
            if display_list is not None:
                display_list.look()        # memory: its worker does the disk
            glfw.poll_events()
            if plug is not None:
                plug.between_frames()      # a display came or went: never inside the poll, or a frame
            # the control window's imgui frame starts BEFORE input handling:
            # with the 1.87+ event queue, want_capture_keyboard only holds this
            # frame's value once new_frame() has run — reading it earlier sees
            # last frame's. The render window has no imgui to defer to.
            imgui.set_current_context(ui_ctx)
            impl.process_inputs()
            imgui.new_frame()
            keys.typing = io.want_capture_keyboard
            # the one frame clock: keys' hold timing, the tempo clock and the
            # LFOs all read this `now` (the file watchers keep their own)
            now = time.perf_counter()
            dt = min(now - last, 0.05)
            last = now
            fps = fps * 0.95 + (1.0 / max(dt, 1e-6)) * 0.05

            frame(host, now, dt, fps)

            if reloader.error or reloader.runtime_error:
                _hot_error_toast(reloader.error or reloader.runtime_error)

            imgui.render()
            ui_browse.scrub(panel, imgui.get_draw_data())    # a deleted icon texture: see there
            impl.render(imgui.get_draw_data())
            # the GRAPH canvas into its tap, from the lists just drawn, on a frame
            # a channel asked for `panel:graph` (replay.py, 2026-11-02)
            replay.grab(panel.canvas_tap, impl, imgui.get_draw_data(), panel.canvas_px)
            glfw.swap_buffers(ctrl_win)
            root.pacer.end_frame()     # the floor: a swap that didn't wait can't run the loop away
            watchdog.pet(now)          # a frame completed: one float write

    except KeyboardInterrupt:
        # something replaced our handler after the line above and the signal
        # unwound the stack after all: quit the way a Ctrl-C does, and take the
        # handlers back, so the grace window's escape hatch stays open
        if quitting.at is None:
            quitting.at = time.perf_counter()
        _install_quit_signals(quitting)

    _quiet(save_windows)      # where the windows are, for the next launch (placement.py)
    # the watchdog first: teardown is no stall; the panel before imgui goes
    # (its GRAPH page's node editor context, plan 28 N2)
    if display_list is not None:
        _quiet(display_list.close)
    close_all(audio, watchdog, awake, panel, *host.adapters, publishers, segmenters)
    impl.shutdown()
    _destroy_windows(all_windows())   # every window before terminate: the exit crash
    glfw.terminate()


if __name__ == "__main__":
    main()
