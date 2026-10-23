"""Hyperspace entry point — GLFW windows in one GL share group.

The *render* window is pure moderngl output, the thing on the projector or
TV: no imgui in it, ever. With ``[[output.screens]]`` in config.toml
(plan 21 WP3) there is one render window per listed output: output 1's
context renders the frame and paces the loop, each later output's window
shows it through an `outputs.Presenter` in its own context (`_draw_render`). The *control* window holds every widget — the
CONTROLS panel, the cheat sheet, the hot-reload error toast — in its own
imgui context and GlfwRenderer. Keys are polled, not callback-driven, so
they work from whichever window is focused (the control window defers to
imgui while it is typing); the mouse orbits, pans and zooms in the render
window only. overlay.py owns where the render window goes (screen,
fullscreen, overlay) through the output.* params.

  ← / →  shape      space  pause      P  points     R  reset view
  [ / ]  brightness , / .  speed      1–6  planes   H  panel
  M  mic on/off     K  play/pause     0  restart    Esc/Q  quit
  Cmd+R  restart the whole process (same terminal, cold reload)
  ↑ / ↓  4D perspective — holding accelerates toward the range limit
  drag  orbit       ⇧drag / right-drag  pan   scroll  zoom about cursor
  L  lines          F  faces          ?  cheat sheet
  T  overlay: float the render over the screen    G  clicks through it
     (only with [output] overlay = true in config.toml — decision 21)
  F1–F8  load a preset of the bank               ⇧F1–F8  save the live state as it
  B  tap tempo      ⇧B  LFO trigger: the downbeat is now, synced LFOs restart
  Cmd+Z / Ctrl+Z  undo the last gesture or load     with ⇧  redo (undo.py)

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

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

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
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer

from . import config, devices, envelope, gamepad, lfo, placement, sequencer, tempo, undo
from .audio import AudioEngine
from .bands import CEIL
from .control import Control
from .geometry import EYE_DISTANCE, EYE_FOV, px_per_unit
from .hotreload import HotReloader
from .learn import Learn
from .library import Library, Marks
from .library import home as library_home
from .media import pool as media_pool
from .media import proxy as media_proxy
from .media import publish
from .media.channels import MediaState
from .media.folder import MediaFolder
from .outputs import Offscreen, Presenter, Slot, Switches, View
from .overlay import RENDER_DEFAULT, GlfwBackend, Output, register_switches, render_index
from .params import Registry, build_registry
from .preset import Presets, migrate_home
from .render import Renderer
from .routing import SLEW_DEFAULT_S, Bindings, Router, bindings_path, register_desk
from .ui import Panel, apply_style, load_fonts
from .view import ViewState
from .watchdog import LOG_NAME, RenderWatch, Watchdog

TITLE = "Hyperspace"
RENDER_SIZE = (1280, 820)
# wide enough for the cheat sheet on the left and the panel on the right
CONTROL_SIZE = (960, 900)

# 4D perspective hold keys move depth4 in the taper's own log space —
# octaves of (depth − 1) — so travel feels even across the whole throw.
# The rate eases in quadratically from a tap-sized nudge to full speed.
D4_RATE0 = 0.45   # octaves/s at the instant of the press
D4_RATE1 = 3.6    # octaves/s once the ramp completes
D4_RAMP = 1.8     # seconds of hold to reach full rate

# the key / pad / MIDI / lane binding tables live in routing.py (bindings.json);
# these are the keys the loop still handles itself (the cheat-sheet test reads
# it). R and F1–F8 / ⇧F1–F8 are table rows since plan 11 (routing.LOOP_KEY_ROWS).
LOOP_KEYS = ("SUPER+R", "UP", "DOWN", "ESCAPE", "Q")


def _err(where: str, e: Exception) -> str:
    return f"{where}: {type(e).__name__}: {e}"[:160]


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001, S110 — teardown is best-effort
        pass


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

    def __init__(self, folder: MediaFolder, devices=None):
        self.folder = folder
        self.devices = devices

    @property
    def proxy_cache(self) -> Path:
        return self.folder.proxy_cache

    def path(self, sid: str) -> Path | None:
        return self.folder.path(sid)

    def live(self, sid: str):
        reg = getattr(self, "devices", None)
        return None if reg is None else reg.media_feeds().get(sid)

    def stamp(self, sid: str):
        e = self.folder.entry(sid)
        return None if e is None else (e.size, e.mtime, e.status)

    def status(self, sid: str) -> str:
        return self.folder.status(sid)


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

    def poll(self, dt: float, now: float) -> None:
        self.state.poll(dt, now)

    def close(self) -> None:
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


def _save_windows(home, render_win, ctrl_win, output, more=()) -> None:
    """Remember where the windows are, in <home>/windows.json
    (placement.py) — on quit and on restart only. Always the *windowed*
    rect: a fullscreen or overlay render window is remembered by the rect
    `Output` would restore, and a minimised window keeps its old entry.
    `more`: the later render outputs' `Output`s in the config's order
    (plan 21 WP3), None for one not opened this run — its old entry is
    kept, as a minimised window's is."""
    def minimised(win) -> bool:
        return bool(glfw.get_window_attrib(win, glfw.ICONIFIED))

    control = None
    if not minimised(ctrl_win):
        control = (*glfw.get_window_pos(ctrl_win), *glfw.get_window_size(ctrl_win))
    render = [None if minimised(render_win) else output.windowed_rect()]
    for o in more:
        render.append(None if o is None or o.win is None or minimised(o.win)
                      else o.windowed_rect())
    placement.save(home, control, render, placement.screens(glfw))


def _slots(cfg: dict | None) -> list[Slot]:
    """The render outputs the config lists (config.screens: one with no
    list), numbered from 1, with their launch switches; no window yet."""
    from . import config

    out = []
    for k, e in enumerate(config.screens(cfg or {})):
        sw = Switches(scene=bool(e["scene"]), hands=bool(e["hands"]),
                      through=bool(e["through"]), dim=float(e["dim"]),
                      flip_x=bool(e.get("flip_x", False)), flip_y=bool(e.get("flip_y", False)))
        out.append(Slot(k + 1, name=str(e["name"] or ""), switches=sw,
                        monitor=placement.index(e["monitor"]),
                        fullscreen=bool(e["fullscreen"]),
                        window=bool(e.get("window", True)) or k == 0,
                        syphon=str(e.get("syphon", "") or ""), ndi=str(e.get("ndi", "") or "")))
    return out


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


def _windows(overlay: bool = False, cfg: dict | None = None, home: Path | None = None):
    """The GLFW windows on one shared GL context: the render outputs and
    the controls. Returns (slots, control window): one `outputs.Slot` per
    output the config lists (plan 21 WP3; one with no list, as before),
    `slot.win` its window — or None, with `slot.missing` saying why, for a
    later output whose screen is not connected (fork F9). Output 1 always
    opens. Created in this order: output 1, the controls (as before), then
    the later outputs.

    `overlay` is the config's ``[output] overlay`` (decision 21 (a)): only
    then is output 1's framebuffer transparent. A later output is never
    transparent, has no MSAA (it only shows the frame) and its own title.

    Where they open is placement.py's say: ``[output] monitor`` /
    ``control_monitor`` in `cfg` (with a list, `config.load` put output 1's
    entry there) and each later output's ``monitor``, else where they were
    (`home`'s windows.json, one render entry per output), else the default
    spots on the primary screen — a later output's cascaded from output
    1's. Its notes go to stderr and `cfg["notes"]` (the SYSTEM page). With
    no screens no position is set and every output opens."""
    scr = placement.screens(glfw)
    oc = (cfg or {}).get("output", {})
    oc = oc if isinstance(oc, dict) else {}
    slots = _slots(cfg)
    render_rect = ctrl_rect = None
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
            render_rect, n1 = placement.place("render", RENDER_SIZE, scr,
                                              oc.get("monitor", -1), renders[0])
            ctrl_rect, n2 = placement.place("control", CONTROL_SIZE, scr,
                                            oc.get("control_monitor", -1), seen.get("control"))
            notes += [n1, n2]
            taken = [tuple(render_rect[:2])]
            for k, slot in enumerate(slots[1:], start=1):
                if slot.publish_only:
                    continue
                later_rects[k], n = _later_rect(slot, k, scr, renders, taken)
                notes.append(n)
        except Exception as e:  # noqa: BLE001 — a file nobody foresaw must not stop a launch
            render_rect = placement.default_rect("render", RENDER_SIZE, scr[0])
            ctrl_rect = placement.default_rect("control", CONTROL_SIZE, scr[0])
            notes = [_err("placement", e) + " — the windows open at their default spots"]
            for k, slot in enumerate(slots[1:], start=1):
                if slot.publish_only:
                    continue
                if slot.monitor >= len(scr):        # fork F9 holds here too (review of #123)
                    slot.missing = f"screen {slot.monitor} is not connected"
                if not slot.missing:
                    r = placement.default_rect("render", RENDER_SIZE, scr[0])
                    later_rects[k] = (r[0] + CASCADE * k, r[1] + CASCADE * k, r[2], r[3])
    for note in filter(None, [*notes, *idle]):
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
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 4)
    # creation-time hints: only when the config asks for overlay does the
    # framebuffer keep alpha so overlay mode can clear to see-through (the
    # other modes clear opaque, and the renderer keeps every pixel at alpha
    # 1 there — plan 14 WP1); otherwise the window is opaque whatever is
    # drawn, for the Pepper's Ghost glass (decision 21 (a), plan 14 WP2).
    # Fullscreen must not minimise when the control window takes focus
    # (overlay.py).
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, bool(overlay))
    glfw.window_hint(glfw.AUTO_ICONIFY, False)
    render_win = glfw.create_window(*render_size, TITLE, None, None)
    if not render_win:
        glfw.terminate()
        raise SystemExit("could not create the render window")
    # the control window is an ordinary opaque window; the shared context
    # lets both sides see the same buffers, textures and programs
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, False)
    glfw.window_hint(glfw.SAMPLES, 0)
    ctrl_win = glfw.create_window(*ctrl_size, f"{TITLE} — controls", None, render_win)
    if not ctrl_win:
        glfw.terminate()
        raise SystemExit("could not create the control window")
    # by default: render left, controls flush right on the primary screen's
    # work area; they overlap on a narrow laptop screen until one goes to a
    # projector (placement.default_rect)
    if render_rect:
        glfw.set_window_pos(render_win, *render_rect[:2])
    if ctrl_rect:
        glfw.set_window_pos(ctrl_win, *ctrl_rect[:2])
    slots[0].win = render_win
    # the later outputs (plan 21 WP3): in output 1's share group (they
    # sample its frame textures), opaque, no MSAA, never minimised when
    # another window takes focus — the hints above still hold
    # (TRANSPARENT_FRAMEBUFFER off, SAMPLES 0, AUTO_ICONIFY off)
    for k, slot in enumerate(slots[1:], start=1):
        if slot.missing or slot.publish_only:
            continue
        rect = later_rects[k]
        size = rect[2:] if rect else RENDER_SIZE
        title = f"{TITLE} — {slot.name or f'output {slot.n}'}"
        win = glfw.create_window(*size, title, None, render_win)
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
    # index no connected screen has (and placement said so), `config.load`
    # in place of anything that is not a number — and a cfg that came by
    # neither road must not stop the launch here either (plan 16 WP7)
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


def _open_presenters(slots: list[Slot], make_context=None, notes: list | None = None) -> None:
    """Each later output's `Presenter`, on its own window's context, and
    the swap rule (fork F6): output 1 waits for its screen (interval 1,
    set where its context is made), every later output does not
    (interval 0) — two waiting swaps a frame halve the rate (plan 21 §1:
    121 fps against 60–81). One that will not build is closed and counts
    as not opened, its `missing` saying why (`notes`, the SYSTEM page): a
    window that is never drawn would show garbage and fool the watch
    (review of #123). The others go on. Leaves output 1's context
    current."""
    make = make_context or moderngl.create_context
    for slot in slots[1:]:
        if not slot.opened:
            continue
        try:
            glfw.make_context_current(slot.win)
            glfw.swap_interval(0)
            slot.presenter = Presenter(make())
        except Exception as e:  # noqa: BLE001 — one output must not stop the launch
            glfw.make_context_current(slots[0].win)
            _quiet(lambda w=slot.win: glfw.destroy_window(w))
            slot.win, slot.presenter = None, None
            slot.missing = f"its GL context would not open ({_err('presenter', e)})"
            note = f"output: {slot.label}: {slot.missing} — not opened"
            print(note, file=sys.stderr)
            if notes is not None:
                notes.append(note)
    glfw.make_context_current(slots[0].win)


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
    and the offscreen targets freed, with the render context current —
    their GL objects are its."""
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
    (plan 21 §1, measured: 199 of 200 frames late)."""
    from OpenGL import GL

    GL.glFlush()


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


def _draw_render(renderer, ctx, s, slots: list[Slot], watch=None, flush=None) -> None:
    """One render frame onto every output (plan 21 WP3, "the frame in
    app.draw_render"):

    1. output 1 current; the stranded-target check; its window bound;
    2. a `View` per output — output 1 on its window's framebuffer (the
       `View` `Renderer.draw` builds, so one output is today's frame), each
       later one with its presenter and its framebuffer's size, or (plan
       32 T9) a publish-only one on its offscreen target at the render
       cap's size ("full": output 1's framebuffer), in their list order;
       each published one carries its publishers (and its tap);
    3. `renderer.draw_outputs`: output 1 drawn whole, a `Handoff` left for
       the others;
    4. glFlush in output 1's context;
    5. each later output, in its own `try`: current, `present`, swap (it
       does not wait). One that raises sets its slot's `error` and tells
       the watch; the frame goes on;
    6. output 1 current and swapped, whatever happened (it waits: it paces
       the loop).

    What output 1's view caught is raised after the others were presented,
    as `Renderer.draw` raises it."""
    first = slots[0]
    win = first.win
    glfw.make_context_current(win)
    # the window, bound explicitly every frame: the renderer draws into
    # whatever is bound, and a frame that once left an offscreen
    # framebuffer bound froze the picture with no error (plan 14 WP1).
    # draw_outputs puts its target back; the check is the alarm.
    stranded = ctx.fbo
    if stranded is not None and stranded.glo != 0 and watch is not None:
        watch.stranded(stranded.glo)
    ctx.screen.use()
    # its own size and DPI (a 1080p projector next to a retina laptop)
    w, h = glfw.get_window_size(win)
    fbw, fbh = glfw.get_framebuffer_size(win)
    ctx.viewport = (0, 0, fbw, fbh)
    first.size = (fbw, fbh)
    later = [sl for sl in slots[1:] if sl.opened and sl.presenter is not None]
    offscreen = [sl for sl in slots[1:] if sl.publish_only and sl.offscreen is not None]
    try:
        views = [View(first.switches, (fbw, fbh), target=ctx.screen,
                      bg_alpha=getattr(renderer, "bg_alpha", 1.0), viewport=(0, 0, fbw, fbh),
                      publish=first.publishers, tap=first.tap)]
        shown = []                      # (slot, view): the presented ones
        pub_size = getattr(renderer, "max_frame", None) or (fbw, fbh)
        for sl in slots[1:]:
            if sl in later:
                sl.size = tuple(int(v) for v in glfw.get_framebuffer_size(sl.win))
                views.append(View(sl.switches, sl.size, presenter=sl.presenter,
                                  publish=sl.publishers, tap=sl.tap))
                shown.append((sl, views[-1]))
            elif sl in offscreen:
                sl.size = (int(pub_size[0]), int(pub_size[1]))
                views.append(View(sl.switches, sl.size, target=sl.offscreen.fit(sl.size),
                                  publish=sl.publishers))
        renderer.draw_outputs(s, max(w, 1), max(h, 1), fbw / max(w, 1), views)
        if later:
            (flush or _gl_flush)()
        for sl, v in shown:
            try:
                glfw.make_context_current(sl.win)
                if v.handoff is not None and sl.size[0] > 0 and sl.size[1] > 0:
                    sl.presenter.present(v.handoff, sl.size)
                glfw.swap_buffers(sl.win)
                sl.error = v.error
            except Exception as e:  # noqa: BLE001 — one output must not take the frame down
                sl.error = _err("present", e)
                if watch is not None:
                    watch.output_failed(sl.label, e)
        if views[0].exc is not None:
            raise views[0].exc
    finally:
        glfw.make_context_current(win)
        glfw.swap_buffers(win)


def _desk_table(reg: Registry, table: Bindings) -> Bindings:
    """The app's binding table, with the desk's own params declared on it
    and knob smoothing at the app's default (plan 18 WP2, fork 12). Called
    before `library.attach`, like every session param's registration, so
    `desk.slew` exists when the show's session values land: a show that
    saved a number keeps it (0 included), one that names none takes 80 ms
    as the state it opened with — clean, and what "default" means. A bare
    `Bindings` (the tests', the probe's) stays at 0."""
    register_desk(reg, table)
    table.slew = SLEW_DEFAULT_S
    return table


def _hand_settings(reg: Registry, cfg: dict):
    """The hands setup as `hands.*` params — registered whether or not the
    tracker is on, so a project or preset carries it either way. hands/core.py
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
                  clock=time.monotonic) -> devices.DeviceRegistry:
    """The device registry (devices.py, plan 27 B1) over the config's
    `[[devices]]` list — the old `[midi]` / `[gamepad]` / `[hands]` /
    `[bridge]` tables translated when there is none — every device opened
    behind its own entry. One that would not open (no `leap` package, a
    `[hands] tape` that is missing) is said on stderr and in
    `cfg["notes"]`, which the SYSTEM page lists and the HANDS page shows
    in place of "tracker off" (plan 21 WP5 R10), and is tried again on
    the Ports schedule. The registry watches `<home>/config.toml` for
    edits to the list."""
    path = (home / config.FILE) if home is not None else None
    reg = devices.DeviceRegistry(config.devices(cfg), ctx, path=path, clock=clock,
                                 notes=cfg.setdefault("notes", []))
    reg.open_all()
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


def _register_dial(reg: Registry, pad) -> None:
    """The sticks' dial readings (gamepad.dial, a prototype) as session
    params on the pad: one enum per stick, and a trigger that swaps the
    two — the same routes felt the other way, to compare them. Never
    saved, never performed: the gamepad entry's `dial_left` / `dial_right`
    set where a launch starts. `pad` is a `gamepad.Pad` or a callable
    returning the one that is current (the device registry's primary pad,
    which a config edit may replace); None, no pad: nothing registered."""
    pad_of = pad if callable(pad) else (lambda: pad)
    if pad_of() is None or "desk.pad.dial.left" in reg:
        return
    modes = list(gamepad.DIAL_MODES)

    def mode_of(stick: str) -> str:
        p = pad_of()
        return (p.dial_modes if p is not None else gamepad.DIAL_DEFAULT).get(
            stick, gamepad.DIAL_DEFAULT[stick])

    def set_mode(stick: str, i) -> None:
        p = pad_of()
        if p is not None:
            p.dial_modes[stick] = modes[int(i) % len(modes)]

    tip = ("How the {} stick reads as a dial (its axis:{}.* lanes): petal, the "
           "sector it points into gets the whole push; blend, neighbouring sectors "
           "crossfade as it sweeps round.")
    for stick, side in (("L", "left"), ("R", "right")):
        reg.enum(f"desk.pad.dial.{side}", f"{side.capitalize()} dial",
                 lambda s=stick: modes.index(mode_of(s)),
                 lambda i, s=stick: set_mode(s, i),
                 modes, group="desk", persist=False, modulatable=False,
                 tip=tip.format(side, stick))

    def swap():
        p = pad_of()
        if p is not None:
            m = p.dial_modes
            m["L"], m["R"] = m.get("R", "blend"), m.get("L", "petal")
    reg.trigger("desk.pad.dial.swap", "Swap dials", swap, group="desk", modulatable=False,
                tip="Swap the two sticks' dial readings — petal ↔ blend.")


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
    table rows since plan 11 WP7; Cmd+R, Esc / Q and ↑ / ↓ stay in the
    loop (`frame`), Cmd+R claiming R's edge before the table reads it.
    """

    def __init__(self, render_win, ctrl_win, more=()):
        self.render_win, self.ctrl_win = render_win, ctrl_win
        self.more = tuple(more)     # the later render outputs' windows (plan 21 WP3)
        self.typing = False
        self.prev: dict[int, bool] = {}
        self.down_since: dict[int, float] = {}

    def _down(self, key: int) -> bool:
        if glfw.get_key(self.render_win, key) == glfw.PRESS:
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

    def __init__(self, win, reg: Registry, view: ViewState, switches=None):
        self.win, self.view = win, view
        # output 1's switches (plan 23 WP1): on a flipped output the cursor
        # is mirrored before use, so a drag and the wheel follow the picture
        self.switches = switches
        self.yaw, self.pitch, self.zoom = reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]
        self.pan_x, self.pan_y = reg["camera.pan.x"], reg["camera.pan.y"]
        self.drag = {"btn": None, "x": 0.0, "y": 0.0}
        self._wheel = 0.0
        glfw.set_scroll_callback(win, self._on_scroll)

    def _on_scroll(self, _win, _dx: float, dy: float) -> None:
        self._wheel += dy

    def poll(self, shift: bool) -> None:
        win, s, drag = self.win, self.view, self.drag
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
    undo: object | None = None        # undo.Undo: ticked once a frame (plan 15 WP1)
    # every opened render output's window settings, output 1's (`output`)
    # first; each applied once a frame (plan 21 WP3)
    outputs: list = field(default_factory=list)

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
    has already run (main): `keys.typing` is this frame's value."""
    reg, keys, router, reloader = h.reg, h.keys, h.router, h.reloader
    h.clock.tick(now)   # the clock's "now" for the frame: a trigger and the LFO step agree

    # the chain object is recreated on source attach; keep bindings fresh
    h.control.chain = h.audio.chain
    reloader.poll()     # its own throttle clock (monotonic): a file watch, not a frame clock

    # ---- polled keys, from either window ----
    if keys.pressed(glfw.KEY_ESCAPE) or keys.pressed(glfw.KEY_Q):
        h.quit()
    shift = keys.shift()
    # Cmd+R restarts; it claims R's edge first, so the table's `key:R`
    # (camera.reset) never hears it — a press with ⌘ held is the loop's
    if keys.super() and keys.pressed(glfw.KEY_R):
        h.restart()
    router.keys(keys)         # key rows: B / ⇧B, R, F1–F8 / ⇧F1–F8, and the rest
    # ↑/↓ ride depth4 toward its range limit, accelerating with hold
    for key, sgn in ((glfw.KEY_UP, 1.0), (glfw.KEY_DOWN, -1.0)):
        hold = keys.held(key, now)
        if hold > 0.0:
            ramp = min(hold / D4_RAMP, 1.0)
            rate = D4_RATE0 + (D4_RATE1 - D4_RATE0) * ramp * ramp
            _ride_depth(reg["view.depth4"], sgn * rate * dt)

    # ---- the devices, polled (devices.py, plan 27): the pad (a second
    # hand on the same controls — imgui never claims it, so it works even
    # while the panel has keyboard focus; a press that completes an armed
    # learn does not also fire its old row) delivers its rows, then runs
    # the sticks' default camera job (gamepad.steer, plan 27 B2: each axis
    # no route names, a relative move on the base); each MIDI desk applies
    # its rows; the hands and the bridge feed below. A device that raises
    # records itself on the registry; the frame goes on and `ok` keeps the
    # note alive until a clean frame ----
    ok = True
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

    # ---- undo: every scene-setter of this frame has written its base
    # (the panel's edits are last frame's tail), so compare the bases and
    # the preset's table against last frame's — a change opens a step, a
    # settle time closes it. No performer has run yet, and none writes a
    # base (undo.py, plan 15 WP1) ----
    if h.undo is not None:
        try:
            h.undo.tick(now)
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
        audio.publish(router)       # the lanes' names, like every source (R8)
        chain = audio.chain if audio.on else None
        if devs is not None:
            # the devices' feeds: the hands feed `hand` (and complete a
            # hand Learn), the bridge feeds `ext` (its out half is a sink,
            # below) — each guarded by the registry, the first error the toast's
            devs.feed(router)
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
        if devs is not None:        # the sinks read effective values out (plan 27 B3)
            devs.send(reg, chain)
            if devs.error and ok:
                ok, reloader.runtime_error = False, devs.error
        h.view.integrate(dt)
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("step", e)
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


def main() -> None:
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise")
    cfg = config.load()                   # before the windows: [output] overlay is a creation hint
    home = library_home()                 # the folder config.load has just ensured
    # the render outputs (plan 21 WP3: one per [[output.screens]] entry, one
    # with no list) and the controls; output 1's window is the render window
    slots, ctrl_win = _windows(_overlay_allowed(cfg), cfg, home)
    render_win = slots[0].win

    # the render side: moderngl on output 1's context, vsynced — it renders
    # every output's frame (fork F12) and paces the loop (fork F6)
    glfw.make_context_current(render_win)
    glfw.swap_interval(1)
    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    s = ViewState()
    # each later output: a presenter on its own context, never waiting
    _open_presenters(slots, notes=cfg.setdefault("notes", []))
    later = [sl for sl in slots[1:] if sl.opened]
    # the outputs published out (plan 32 T9), output 1's context current
    _open_publishers(slots, ctx, cfg.setdefault("notes", []))

    # the control side: imgui on the control window's context. Its swap
    # never waits for a vblank — two vsynced swaps a frame would halve the
    # rate — so it paces itself off the render window.
    glfw.make_context_current(ctrl_win)
    glfw.swap_interval(0)
    ui_gl = moderngl.create_context()  # a handle on the control context; it only clears
    ui_ctx = imgui.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(ctrl_win)
    io = imgui.get_io()
    # hot-reloaded panel code can raise mid-window; let imgui unwind the
    # stack itself instead of asserting the process away
    io.config_error_recovery = True
    io.config_error_recovery_enable_assert = False

    audio = AudioEngine()
    audio.rescan()                         # the one PortAudio scan, here at startup — never mid-set on a first read
    control = Control(audio.chain)
    # presets, projects, the preset bank (its project's): in the home, or in
    # the folder [library] path names (plan 25) — the machine files
    # (config, bindings, windows, logs, last_show) stay in the home either way
    lp = cfg.get("library", {}).get("path", "")
    library = Library(Path(lp), machine=home) if lp else Library()
    # the media folder and the eight channels (plan 32): the channels'
    # params are declared over this one `MediaState`, the preset's bins are
    # its, and the renderer reads its frames
    media = _open_media(lp, home)
    renderer.media = media.state
    # dream.* drives the renderer's look-back (lookback.py); the post pass
    # runs inside renderer.draw
    panels: list = []                  # app.restart raises the panel's flag; frame() polls it
    reg = build_registry(s, control, audio, library.project, dream=renderer.lookback.state,
                         fx=renderer.fx.state, ghost=renderer.ghost.state,
                         media=media.state,
                         restart=lambda: [setattr(p, "restart_requested", True) for p in panels])
    # an analyzer preset carries its band layout; the library hands it to
    # control before restoring values (07-overhaul contracts)
    library.on_layout("band", control.apply_layout)
    # …and a saved band preset carries the layout back out (audit A2); the
    # scene combo and the strip keep each other posted (audit A1)
    library.extra("band", lambda: {"layout": audio.chain.layout()})
    library.on_load("band", control.scene_loaded)
    control.library = library
    hand_settings = _hand_settings(reg, cfg)   # before attach: "default" includes them
    # the tap-tempo clock and the LFO bank (tempo.py, lfo.py; four by
    # default, up to 16, plan 31 B): their knobs are params too, so a
    # preset carries a tempo and an LFO arrangement
    clock = tempo.Clock()
    lfos = lfo.LFOs()
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    # plan 31: the envelope bank (the five lane envelopes, plus extras) and
    # the step sequencer that fires them — registered beside the LFOs and
    # before attach, so "default" holds their knobs and an empty pattern
    envs = envelope.Envelopes()
    seq = sequencer.Sequencer()
    envelope.register(reg, envs, clock)
    sequencer.register(reg, seq, clock)
    # the render window's placement registers before attach, so "default"
    # includes output.* and reset / the dirty dot see them (audit L6)
    output = _make_output(render_win, reg, cfg)
    slots[0].output = output
    for sl in later:                       # no params: the config says (fork F10)
        sl.output = _later_output(sl)
    # each opened output's switches (plan 21 WP4): rig settings, seeded
    # from the config's launch values already on the slots, never saved
    register_switches(reg, slots)
    # one binding table for keys, pad, MIDI and lanes (an old midi_map.json
    # migrates) — read before attach for the same reason: the desk's
    # session param, `desk.slew`, is the table's, at the app's default
    # until the show says otherwise
    mc = cfg.get("midi", {})
    table = _desk_table(reg, Bindings.load(
        bindings_path(home), mc.get("profile", "apc40"),
        Path(mc.get("map", "midi_map.json")),
    ))
    library.attach(reg)
    panel = Panel(control, audio, s, renderer, library.project, registry=reg, library=library)
    panels.append(panel)
    panel.clock, panel.lfos = clock, lfos     # the LFO page's scopes and beat light
    panel.envs, panel.seq = envs, seq         # plan 31: what a SEQ page draws
    panel.output = output
    panel.outputs = slots                  # the OUTPUT page: a block per output (plan 21 WP4)
    router = Router(reg, table)
    router.use_lfos(lfos, clock)           # they step inside the pass (plan 28 N0)
    router.use_bank(envs, clock)           # …and so do the envelopes (plan 31)
    router.use_sequencer(seq, envs)        # after the banks begin, before the plan
    # the presets (preset.py): the library's `presets/` files, landed on the
    # registry and the table; the project's bank loads through it
    presets = Presets(library, reg, router)
    # plan 26 A4: a preset's graph section sets the renderer's wiring and
    # hands an extra hands node its own state (`Renderer.ghost_states`)
    presets.graph.attach(renderer)
    # plan 13 §6, once: an older home's projects, routing presets and the
    # preset part of bindings.json become presets (backups beside every
    # rewritten file); a home already migrated finds nothing to do
    migrate_home(library, router, cfg.get("hands"))   # hand lanes named by the rig's layout
    # one Learn over the live table, whatever the MIDI gate says: a knob
    # or a hand completes it, the panel's prompt settles what the referee
    # refused (learn.py; the band.sel.* rule is the registry's `real`)
    learn = Learn(reg, router.table, lane=router.lane)   # hand:7 and hand:right.y: one axis
    panel.learn = learn
    panel.router = router                  # the ROUTING page edits the live table
    # the devices (devices.py, plan 27 B1): the pad, MIDI, the hands and
    # the bridge, each opened behind its `[[devices]]` entry (the old
    # tables translated), polled by `frame` through the registry. What
    # holds an adapter — the panel (Learn's hints, the desk page, the HANDS
    # page, the Learn pad menu) and the ghost renderer (the tracker's
    # skeletons) — is pointed at it now and again whenever the list changes
    rig = _open_devices(cfg, devices.Context(reg=reg, table=router.table, learn=learn,
                                             audio=audio, hand_settings=hand_settings,
                                             notes=cfg.setdefault("notes", []), home=home),
                        home)

    def point_at_devices() -> None:
        panel.midi = rig.adapter("midi")         # the first desk listed: the APC40's page
        panel.pad = rig.adapter("gamepad")       # the menu's "Learn pad"
        panel.hands = rig.adapter("hands")
        renderer.ghost.source = panel.hands      # no tracker, nothing draws
        router.follow_devices()                  # the MIDI roles and row schemes, again
    # schemes from the registry (plan 27 B2): the router asks it which
    # sources are lanes and in what order the pages offer them, the learn
    # what can be armed — each handed the registry, importing nothing
    router.use(rig)
    learn.devices = rig
    rig.listeners.append(point_at_devices)
    point_at_devices()
    panel.devices = rig                        # the SYSTEM page's device lines
    panel.media = media                        # the MEDIA page: the folder and the channels
    renderer.ghost.router = router           # the guide lights what the table routes
    renderer.cloud_source = rig              # cloud:<role> → the scene's point clouds (A4b)
    media.state.resolver.devices = rig       # ndi: / syphon: / camera: ids → live feeds (plan 32 T8)
    panel.hand_settings = hand_settings
    dream_io, panel.dream_error = _open_dream(reg, cfg)
    if dream_io is not None:            # fills the look-back's dream slot
        renderer.lookback.source = dream_io
    # the sticks as dials (gamepad.dial, a prototype): session params on
    # whichever pad is the primary now
    _register_dial(reg, lambda: rig.adapter("gamepad"))
    awake = _open_awake(cfg)               # no screensaver over the show
    # the project's startup preset (D11), once, now that everything it lands
    # on exists; a missing one is said on the panel and the app runs on
    library.project.load_startup()
    # undo (undo.py, plan 15 WP1), built after the startup preset so a
    # launch starts with an empty stack: bases through the registry, table
    # parts through the table, what is loaded through the library's marks;
    # the bands' names in strip order say which layout a strip's values
    # belong to, and a restore tells the router its macros are acted on
    marks = Marks(library)
    undo_obj = undo.Undo(reg, router.table, marks=marks,
                         tag=lambda: tuple(s.name for s in audio.chain.spec),
                         on_restore=router.sync_macros,
                         # the LFOs' membership (plan 31 B), read off the
                         # router at each step, so a re-classed router counts
                         banks=lambda: router._banks())
    undo.install(undo_obj)             # what undo.push and the edit.* triggers reach
    panel.undo = undo_obj              # the footer's message slot
    # panel state and chain must stay one object even after source changes
    # the live objects that get re-classed on a hot reload; re-evaluated
    # each swap so recreated ones (the chain after a source attach) count
    reloader = HotReloader(targets=lambda: [
        (renderer, "render", "Renderer"),
        (renderer.scene, "render", "SceneTarget"),
        (renderer.cover, "render", "CoverTarget"),
        (renderer.lookback, "lookback", "Lookback"),
        (renderer.lookback.state, "lookback", "DreamState"),
        (renderer.fx, "fx", "FxChain"),
        (renderer.fx.state, "fx", "FxState"),
        (renderer.ghost, "ghost", "Ghost"),
        (renderer.ghost.state, "ghost", "GhostState"),
        (s, "view", "ViewState"),
        (media.state, "media.channels", "MediaState"),        # plan 32
        *[(ch, "media.channels", "Channel") for ch in media.state.channels.values()],
        (media.folder, "media.folder", "MediaFolder"),
        (panel, "ui", "Panel"),
        (control, "control", "Control"),
        (audio, "audio", "AudioEngine"),
        (audio.chain, "analyzer", "Analyzer"),
        *[(p, "bands", "Params") for p in audio.chain.params],
        *([(audio.analyser, "analysis", "Analyser")] if audio.analyser is not None else []),
        (reg, "params", "Registry"),
        *[(p, "params", "Param") for p in reg],
        (output, "overlay", "Output"),
        (output.backend, "overlay", "GlfwBackend"),
        # the later render outputs (plan 21 WP3); a presenter rebuilds its
        # programs at its next present, in its own context
        *[(sl.output, "overlay", "Output") for sl in later],
        *[(sl.output.backend, "overlay", "GlfwBackend") for sl in later],
        *[(sl.presenter, "outputs", "Presenter") for sl in later if sl.presenter],
        (library, "library", "Library"),
        (library.project, "library", "Project"),
        (marks, "library", "Marks"),
        (undo_obj, "undo", "Undo"),
        (router, "routing", "Router"),
        (presets, "preset", "Presets"),
        (presets.graph, "preset", "GraphSection"),      # plan 26 A4
        (learn, "learn", "Learn"),
        (clock, "tempo", "Clock"),
        (lfos, "lfo", "LFOs"),
        # the LFOs as they are at this swap: N of them, with gaps (plan 31 B)
        *[(lf, "lfo", "LFO") for lf in lfos.lfos],
        # the envelopes the same way (plan 31: five lane ones and the
        # extras), and the sequencer with its lanes
        (envs, "envelope", "Envelopes"),
        *[(e, "envelope", "Envelope") for e in envs.voices],
        (seq, "sequencer", "Sequencer"),
        *[(ln, "sequencer", "Lane") for ln in seq.lanes],
        *([(hand_settings, "hands.core", "HandSettings")] if hand_settings else []),
        *([(dream_io, "dream", "DreamWorker")] if dream_io else []),
        # the devices' adapters, the shims and the registry (devices.py):
        # re-evaluated each swap, so a device the list brought in counts
        *rig.targets(),
    ], watchers=[library])
    panel.reloader = reloader
    panel.config_error = cfg.get("error", "")   # a config.toml that would not parse
    if router.table.said:                       # what the launch did to bindings.json
        cfg["notes"].append(router.table.said)
    # …or that wants a section renamed, and what the device list did since
    # (the registry appends to this very list, so the page follows)
    panel.config_notes = cfg["notes"]
    keys = Keys(render_win, ctrl_win, [sl.win for sl in later])   # keys from every window
    mouse = Mouse(render_win, reg, s, slots[0].switches)          # the mouse: output 1 only

    def draw_render(dt: float) -> None:
        # every render output: output 1 drawn, the others presented, the
        # others swapped first and output 1 last (_draw_render)
        _draw_render(renderer, ctx, s, slots, render_watch)

    def draw_panel(dt: float, fps: float) -> None:
        # the control window: black ground, then the imgui frame opened
        # before the frame's input handling
        glfw.make_context_current(ctrl_win)
        ui_gl.clear(0.0, 0.0, 0.0, 1.0)
        panel.draw(dt, fps)

    # the stall log (watchdog.py), <home>/stall.log: a 2 s whole-loop stall,
    # a raising render draw, or 2 s with no render frame presented while the
    # panel runs, each with every thread's stack; kill -USR1 dumps on demand
    watchdog = Watchdog(home / LOG_NAME,
                        preset=lambda: library.current("presets"))
    # with two or more outputs the stall is "no output presented", and one
    # output dark while another presents is a warning naming it (WP3)
    opened = [sl for sl in slots if sl.opened and sl.output is not None]
    render_watch = RenderWatch(
        watchdog, info=lambda: output.backend.window_state(render_win),
        outputs=(lambda: [(sl.label, sl.output.backend.window_state(sl.win))
                          for sl in opened]) if len(opened) > 1 else None)
    panel.watchdog, panel.render_watch = watchdog, render_watch

    def dream_check(name: str | None) -> None:
        # a preset that asks for the dream — the look-back on with a dream
        # mix above 0 — with no worker to dream: the look-back shows the
        # echoes only. Said on the banner (until dismissed), logged once.
        # Echoes alone (dream.mix 0) are a normal mode and say nothing.
        if reg["dream.on"].base and reg["dream.mix"].base > 0 and dream_io is None:
            why = panel.dream_error or "[dream] enabled = false in config.toml"
            render_watch.warn(f"{name} turns the dream on, but there is no dream worker ({why}); "
                              "the look-back shows the echoes only")
    presets.listeners.append(dream_check)
    dream_check(library.current("presets"))     # the startup preset has already landed

    # both exits close the publishers, in output 1's context (plan 32 T9)
    publishers = _Closer(lambda: _close_publishers(render_win, slots))

    def all_windows() -> list:            # both exits destroy these before terminate
        return [*(sl.win for sl in slots[1:]), ctrl_win, render_win]

    def save_windows() -> None:           # both exits: quit below, ⌘R in _restart
        _save_windows(home, render_win, ctrl_win, output, [sl.output for sl in slots[1:]])

    host = Host(reg=reg, view=s, control=control, audio=audio, router=router,
                clock=clock, lfos=lfos, keys=keys, mouse=mouse, output=output,
                renderer=renderer, panel=panel, reloader=reloader,
                draw_render=draw_render, draw_panel=draw_panel,
                restart=lambda: _restart(audio, (watchdog, awake, panel, *host.adapters,
                                                 publishers), impl,
                                         ctrl_win,
                                         save=save_windows, windows=all_windows()),
                quit=lambda: glfw.set_window_should_close(render_win, True),
                devices=rig, dream_io=dream_io, learn=learn, render_watch=render_watch,
                undo=undo_obj, media=media,
                outputs=[sl.output for sl in slots if sl.output is not None])

    # smoke-test escape hatch: HYPERSPACE_FRAMES=n closes after n frames
    frames_left = int(os.environ.get("HYPERSPACE_FRAMES", "0")) or None

    watchdog.start()          # last, so startup is not a stall

    last = time.perf_counter()
    fps = 0.0
    # the loop ends when any window is closed (the smoke run closes output 1)
    while not (any(glfw.window_should_close(sl.win) for sl in slots if sl.opened)
               or glfw.window_should_close(ctrl_win)):
        if frames_left is not None:
            frames_left -= 1
            if frames_left <= 0:
                glfw.set_window_should_close(render_win, True)
        glfw.poll_events()
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
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(ctrl_win)
        watchdog.pet(now)          # a frame completed: one float write

    _quiet(save_windows)      # where the windows are, for the next launch (placement.py)
    # the watchdog first: teardown is no stall; the panel before imgui goes
    # (its GRAPH page's node editor context, plan 28 N2)
    close_all(audio, watchdog, awake, panel, *host.adapters, publishers)
    impl.shutdown()
    _destroy_windows(all_windows())   # every window before terminate: the exit crash
    glfw.terminate()


if __name__ == "__main__":
    main()
