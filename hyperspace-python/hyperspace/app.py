"""Hyperspace entry point — two GLFW windows on one GL context.

The *render* window is pure moderngl output, the thing on the projector or
TV: no imgui in it, ever. The *control* window holds every widget — the
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
import math
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
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

from . import config, gamepad, lfo, placement, tempo, undo
from .audio import AudioEngine
from .control import Control
from .gamepad import Pad
from .hotreload import HotReloader
from .learn import Learn
from .library import Library, Marks
from .library import home as library_home
from .overlay import GlfwBackend, Output
from .params import Registry, build_registry
from .preset import Presets, migrate_home
from .render import Renderer
from .routing import Bindings, Router, bindings_path
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


def close_all(audio, *adapters) -> None:
    """Every optional adapter's `close()` — MIDI, the bridge, the hands
    tracker, the dream worker — then the audio stream, best-effort, so a
    broken port never blocks a quit or a restart. The one list for both
    exits (audit P1); `None` for an adapter that was never opened."""
    for a in adapters:
        if a is not None:
            _quiet(a.close)
    _quiet(audio.stop)


def _restart(audio, adapters, impl, ctrl_win, save=None) -> None:
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
    _quiet(glfw.terminate)
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _save_windows(home, render_win, ctrl_win, output) -> None:
    """Remember where the windows are, in <home>/windows.json
    (placement.py) — on quit and on restart only. Always the *windowed*
    rect: a fullscreen or overlay render window is remembered by the rect
    `Output` would restore, and a minimised window keeps its old entry."""
    def minimised(win) -> bool:
        return bool(glfw.get_window_attrib(win, glfw.ICONIFIED))

    control = None
    if not minimised(ctrl_win):
        control = (*glfw.get_window_pos(ctrl_win), *glfw.get_window_size(ctrl_win))
    render = None if minimised(render_win) else output.windowed_rect()
    placement.save(home, control, [render], placement.screens(glfw))


def _windows(overlay: bool = False, cfg: dict | None = None, home: Path | None = None):
    """The two GLFW windows on one shared GL context: render first, then controls.

    `overlay` is the config's ``[output] overlay`` (decision 21 (a)): only
    then is the render window's framebuffer transparent.

    Where they open is placement.py's say: ``[output] monitor`` /
    ``control_monitor`` in `cfg`, else where they were (`home`'s
    windows.json), else the default spots on the primary screen. Its notes
    go to stderr and `cfg["notes"]` (the SYSTEM page). With no screens no
    position is set."""
    scr = placement.screens(glfw)
    oc = (cfg or {}).get("output", {})
    oc = oc if isinstance(oc, dict) else {}
    render_rect = ctrl_rect = None
    if scr:
        seen = placement.load(home) if home is not None else {}
        renders = seen.get("render") or [None]
        render_rect, n1 = placement.place("render", RENDER_SIZE, scr,
                                          oc.get("monitor", -1), renders[0])
        ctrl_rect, n2 = placement.place("control", CONTROL_SIZE, scr,
                                        oc.get("control_monitor", -1), seen.get("control"))
        for note in filter(None, (n1, n2)):
            print(note, file=sys.stderr)
            if cfg is not None:
                cfg.setdefault("notes", []).append(note)
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
    return render_win, ctrl_win


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
    out.monitor = int(oc.get("monitor", -1))
    out.fullscreen = bool(oc.get("fullscreen", False))
    if oc.get("on_start", False) and not out.allowed:
        print("output: on_start asks for overlay, but [output] overlay is false — "
              "the window stays opaque", file=sys.stderr)
    out.overlay = bool(oc.get("on_start", False)) and out.allowed
    out.passthrough = bool(oc.get("passthrough", True))
    out.bg = float(oc.get("bg", 0.0))
    out.alpha = float(oc.get("alpha", 1.0))
    return out


def _open_midi(reg: Registry, cfg: dict, table: Bindings, learn):
    """The adapter, only when configured — the core never imports it."""
    mc = cfg.get("midi", {})
    if not mc.get("enabled", True):
        return None
    try:
        from . import midi
    except ImportError as e:
        print(f"midi: adapter unavailable ({e})", file=sys.stderr)
        return None
    try:
        return midi.MidiIO(reg, table, port=mc.get("port"), profile=mc.get("profile", "apc40"),
                           learner=learn)
    except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
        print(f"midi: {e}", file=sys.stderr)
        return None


def _open_bridge(reg: Registry, cfg: dict):
    """The lanes bridge (bridge.py), only when [bridge] enabled — the same rule."""
    if not cfg.get("bridge", {}).get("enabled", False):
        return None
    try:
        from . import bridge
        return bridge.Bridge(reg, cfg["bridge"])
    except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
        print(f"bridge: {e}", file=sys.stderr)
        return None


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


def _open_hands(cfg: dict, settings):
    """Ultraleap hands (hands/), only when [hands] enabled — the same rule."""
    hc = cfg.get("hands", {})
    if settings is None or not hc.get("enabled", False):
        return None
    try:
        from . import hands
        cal = hc.get("calibration")
        return hands.HandsIO(settings, hc, cal_path=Path(cal) if cal else None)
    except Exception as e:  # noqa: BLE001 — a broken adapter must not stop the show
        print(f"hands: {e}", file=sys.stderr)
        return None


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


def _open_pad(cfg: dict):
    """The Xbox pad (gamepad.py), unless [gamepad] enabled = false. On by
    default: the pad never raises when absent, so there is nothing to lose
    by polling for one (audit P2)."""
    if not cfg.get("gamepad", {}).get("enabled", True):
        return None
    return Pad()


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

    def __init__(self, render_win, ctrl_win):
        self.render_win, self.ctrl_win = render_win, ctrl_win
        self.typing = False
        self.prev: dict[int, bool] = {}
        self.down_since: dict[int, float] = {}

    def _down(self, key: int) -> bool:
        if glfw.get_key(self.render_win, key) == glfw.PRESS:
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

    def __init__(self, win, reg: Registry, view: ViewState):
        self.win, self.view = win, view
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
            self.pan_x.nudge(x - drag["x"])
            self.pan_y.nudge(y - drag["y"])
            drag.update(x=x, y=y)
        wheel, self._wheel = self._wheel, 0.0
        if wheel:
            w, h = glfw.get_window_size(win)
            _zoom_about(self.zoom, self.pan_x, self.pan_y, s, wheel, x, y, w, h)


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
    cx, cy = w / 2 + view.pan[0], h / 2 + view.pan[1]
    pan_x.nudge((cx - x) * (factor - 1))
    pan_y.nudge((cy - y) * (factor - 1))


def _ride_depth(p, octaves: float) -> None:
    """Move 4D depth by a number of octaves of (depth − 1) — the taper's own space."""
    u = math.log2(max(p.base - 1.0, 1e-6) / 0.05)
    p.nudge(1.0 + 0.05 * 2.0 ** (u + octaves) - p.base)


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
    pad: Pad | None = None
    midi_io: object | None = None
    hands_io: object | None = None
    bridge_io: object | None = None
    dream_io: object | None = None
    learn: object | None = None       # learn.Learn: what MIDI and the hands complete
    render_watch: RenderWatch | None = None   # the render window's health (watchdog.py)
    undo: object | None = None        # undo.Undo: ticked once a frame (plan 15 WP1)

    @property
    def adapters(self) -> tuple:
        """What `close_all` closes, in shutdown order."""
        return (self.midi_io, self.bridge_io, self.hands_io, self.dream_io)


def frame(h: Host, now: float, dt: float, fps: float) -> bool:
    """One frame, in the order ARCHITECTURE §2 states: the scene-setters
    (keys, loop keys, pad, MIDI, the macros' base subscribers) write
    bases, and the undo watcher compares them (`undo.tick`, plan 15);
    the sources feed the table
    (hands, output, mouse, audio, bridge, LFOs); the pass lands offsets
    (`router.modulate`, `reg.apply`, `integrate`); then the two windows
    draw. Returns False when a guarded block raised — the error is on
    `reloader.runtime_error` and the loop goes on, so the next save can
    fix it. `imgui.new_frame()` has already run (main): `keys.typing` is
    this frame's value."""
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

    # ---- gamepad: a second hand on the same controls (imgui never
    # claims it, so it works even while the panel has keyboard focus) ----
    pad = h.pad
    if pad is not None:
        pad.poll()
        if pad.on:
            router.pad(pad)
            # analog: left stick orbits, right-stick Y zooms about centre,
            # triggers ride depth4 in its own log space (LT out, RT in)
            lx, ly = pad.axis(gamepad.AX_LX), pad.axis(gamepad.AX_LY)
            if lx:
                reg["camera.yaw"].nudge(lx * 2.2 * dt)
            if ly:
                reg["camera.pitch"].nudge(ly * 2.2 * dt)
            zoom_v = pad.axis(gamepad.AX_RY)
            if zoom_v:
                reg["camera.zoom"].scale(2.0 ** (-zoom_v * 1.2 * dt))
            d4 = pad.trigger(gamepad.AX_RT) - pad.trigger(gamepad.AX_LT)
            if d4:
                _ride_depth(reg["view.depth4"], d4 * 2.4 * dt)

    # ---- MIDI controller: routed through the same registry. From here
    # on a raising block records itself on the reloader and the frame goes
    # on; `ok` keeps the note alive until a clean frame ----
    ok = True
    if h.midi_io is not None:
        try:
            h.midi_io.poll()
        except Exception as e:  # noqa: BLE001 — hot-reloaded code may raise
            ok, reloader.runtime_error = False, _err("midi", e)

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

    # ---- Ultraleap hands: hand lanes into the table, MIDI out to a DAW ----
    if h.hands_io is not None:
        try:
            h.hands_io.poll(dt, h.learn, router)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("hands", e)

    # ---- output: the render window follows the output.* params ----
    h.output.apply()
    h.renderer.bg_alpha = h.output.bg_alpha
    # the master dim (plan 15 WP3), the frame's last pass; getattr: an
    # Output made before a hot reload brought the attribute has none
    h.renderer.dim = getattr(h.output, "dim", 1.0)

    # ---- mouse: orbit / pan / zoom, render window only ----
    h.mouse.poll(shift)

    # ---- audio + rotation + draw, guarded: hot-reloaded code may raise;
    # record it and keep the loop alive so the next save can fix it ----
    try:
        audio = h.audio
        audio.step(dt)
        audio.publish(router)       # the lanes' names, like every source (R8)
        if h.bridge_io is not None:   # lanes out, external lanes in (bridge.py)
            h.bridge_io.step(audio.chain if audio.on else None, router)
        # the LFOs are a source like any other: stepped on the frame's
        # clock, fed to the table as `lfo` before the modulation pass
        h.lfos.step(dt, now, h.clock)
        h.lfos.publish(router)
        # the lanes are a modulation source like any other (routing.py);
        # once every source has spoken for this frame, land base +
        # offsets on the objects before the integrator reads them
        router.modulate(audio.chain if audio.on else None)
        reg.apply()
        h.view.integrate(dt)
    except Exception as e:  # noqa: BLE001
        ok, reloader.runtime_error = False, _err("step", e)
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
    render_win, ctrl_win = _windows(_overlay_allowed(cfg), cfg, home)

    def save_windows() -> None:           # both exits: quit below, ⌘R in _restart
        _save_windows(home, render_win, ctrl_win, output)

    # the render side: moderngl on the render window's context, vsynced
    glfw.make_context_current(render_win)
    glfw.swap_interval(1)
    ctx = moderngl.create_context()
    renderer = Renderer(ctx)
    s = ViewState()

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
    library = Library()                    # presets, projects, the preset bank (its project's)
    # dream.* drives the renderer's look-back (lookback.py); the post pass
    # runs inside renderer.draw
    panels: list = []                  # app.restart raises the panel's flag; frame() polls it
    reg = build_registry(s, control, audio, library.project, dream=renderer.lookback.state,
                         fx=renderer.fx.state, ghost=renderer.ghost.state,
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
    # the tap-tempo clock and the four LFOs (tempo.py, lfo.py): their knobs
    # are params too, so a preset carries a tempo and an LFO arrangement
    clock = tempo.Clock()
    lfos = lfo.LFOs()
    tempo.register(reg, clock)
    lfo.register(reg, lfos, clock)
    # the render window's placement registers before attach, so "default"
    # includes output.* and reset / the dirty dot see them (audit L6)
    output = _make_output(render_win, reg, cfg)
    library.attach(reg)
    panel = Panel(control, audio, s, renderer, library.project, registry=reg, library=library)
    panels.append(panel)
    panel.clock, panel.lfos = clock, lfos     # the LFO page's scopes and beat light
    panel.output = output
    # one binding table for keys, pad, MIDI and lanes (an old midi_map.json migrates)
    mc = cfg.get("midi", {})
    router = Router(reg, Bindings.load(
        bindings_path(library.home), mc.get("profile", "apc40"),
        Path(mc.get("map", "midi_map.json")),
    ))
    # the presets (preset.py): the library's `presets/` files, landed on the
    # registry and the table; the project's bank loads through it
    presets = Presets(library, reg, router)
    # plan 13 §6, once: an older home's projects, routing presets and the
    # preset part of bindings.json become presets (backups beside every
    # rewritten file); a home already migrated finds nothing to do
    migrate_home(library, router, cfg.get("hands"))   # hand lanes named by the rig's layout
    # one Learn over the live table, whatever the MIDI gate says: a knob
    # or a hand completes it, the panel's prompt settles what the referee
    # refused (learn.py; the band.sel.* rule is the registry's `real`)
    learn = Learn(reg, router.table, lane=router.lane)   # hand:7 and hand:right.y: one axis
    panel.learn = learn
    midi_io = _open_midi(reg, cfg, router.table, learn)
    panel.midi = midi_io
    panel.router = router                  # the ROUTING page edits the live table
    bridge_io = _open_bridge(reg, cfg)
    hands_io = _open_hands(cfg, hand_settings)
    panel.hands = hands_io
    # the ghost hands draw the tracker's skeletons; no tracker, nothing draws
    renderer.ghost.source = hands_io
    renderer.ghost.router = router           # the guide lights what the table routes
    panel.hand_settings = hand_settings
    dream_io, panel.dream_error = _open_dream(reg, cfg)
    if dream_io is not None:            # fills the look-back's dream slot
        renderer.lookback.source = dream_io
    panel.bridge = bridge_io               # the SYSTEM page's bridge line
    pad = _open_pad(cfg)
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
                         on_restore=router.sync_macros)
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
        (library, "library", "Library"),
        (library.project, "library", "Project"),
        (marks, "library", "Marks"),
        (undo_obj, "undo", "Undo"),
        (router, "routing", "Router"),
        (presets, "preset", "Presets"),
        (learn, "learn", "Learn"),
        (clock, "tempo", "Clock"),
        (lfos, "lfo", "LFOs"),
        *[(lf, "lfo", "LFO") for lf in lfos.lfos],
        *([(midi_io, "midi", "MidiIO")] if midi_io else []),
        *([(bridge_io, "bridge", "Bridge")] if bridge_io else []),
        *([(hand_settings, "hands.core", "HandSettings")] if hand_settings else []),
        *([(hands_io, "hands.core", "HandsIO")] if hands_io else []),
        *([(dream_io, "dream", "DreamWorker")] if dream_io else []),
        *([(pad, "gamepad", "Pad")] if pad else []),
    ], watchers=[library])
    panel.reloader = reloader
    panel.config_error = cfg.get("error", "")   # a config.toml that would not parse
    panel.config_notes = cfg.get("notes", [])   # …or that wants a section renamed
    keys = Keys(render_win, ctrl_win)
    mouse = Mouse(render_win, reg, s)

    def draw_render(dt: float) -> None:
        # the render window: its own size and DPI (a 1080p projector next
        # to a retina laptop)
        glfw.make_context_current(render_win)
        # the window, bound explicitly every frame: Renderer.draw draws into
        # whatever is bound, and a frame that once left an offscreen
        # framebuffer bound froze the picture with no error (plan 14 WP1).
        # Renderer.draw now puts its target back; the check is the alarm.
        stranded = ctx.fbo
        if stranded is not None and stranded.glo != 0:
            render_watch.stranded(stranded.glo)
        ctx.screen.use()
        w, h = glfw.get_window_size(render_win)
        fbw, fbh = glfw.get_framebuffer_size(render_win)
        ctx.viewport = (0, 0, fbw, fbh)
        try:
            renderer.draw(s, max(w, 1), max(h, 1), dpr=fbw / max(w, 1))
        finally:
            glfw.swap_buffers(render_win)

    def draw_panel(dt: float, fps: float) -> None:
        # the control window: black ground, then the imgui frame opened
        # before the frame's input handling
        glfw.make_context_current(ctrl_win)
        ui_gl.clear(0.0, 0.0, 0.0, 1.0)
        panel.draw(dt, fps)

    # the stall log (watchdog.py), <home>/stall.log: a 2 s whole-loop stall,
    # a raising render draw, or 2 s with no render frame presented while the
    # panel runs, each with every thread's stack; kill -USR1 dumps on demand
    watchdog = Watchdog(library.home / LOG_NAME,
                        preset=lambda: library.current("presets"))
    render_watch = RenderWatch(watchdog,
                               info=lambda: output.backend.window_state(render_win))
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

    host = Host(reg=reg, view=s, control=control, audio=audio, router=router,
                clock=clock, lfos=lfos, keys=keys, mouse=mouse, output=output,
                renderer=renderer, panel=panel, reloader=reloader,
                draw_render=draw_render, draw_panel=draw_panel,
                restart=lambda: _restart(audio, (watchdog, *host.adapters), impl, ctrl_win,
                                         save=save_windows),
                quit=lambda: glfw.set_window_should_close(render_win, True),
                pad=pad, midi_io=midi_io, hands_io=hands_io, bridge_io=bridge_io,
                dream_io=dream_io, learn=learn, render_watch=render_watch,
                undo=undo_obj)

    # smoke-test escape hatch: HYPERSPACE_FRAMES=n closes after n frames
    frames_left = int(os.environ.get("HYPERSPACE_FRAMES", "0")) or None

    watchdog.start()          # last, so startup is not a stall

    last = time.perf_counter()
    fps = 0.0
    while not (glfw.window_should_close(render_win) or glfw.window_should_close(ctrl_win)):
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
    close_all(audio, watchdog, *host.adapters)   # the watchdog first: teardown is no stall
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
