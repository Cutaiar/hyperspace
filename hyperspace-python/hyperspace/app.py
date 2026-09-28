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
  F1–F8  load theme (whole-surface save state)    ⇧F1–F8  save theme
  B  tap tempo      ⇧B  LFO trigger: the downbeat is now, synced LFOs restart

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

from . import config, gamepad, lfo, tempo
from .audio import AudioEngine
from .control import Control
from .gamepad import Pad
from .hotreload import HotReloader
from .learn import Learn
from .library import SLOTS, Library
from .overlay import GlfwBackend, Output
from .params import Registry, build_registry
from .render import Renderer, ViewState
from .routing import Bindings, Router, bindings_path
from .ui import Panel, apply_style, load_fonts

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
# these are the keys the loop still handles itself (the cheat-sheet test reads it)
LOOP_KEYS = ("R", "SUPER+R", "UP", "DOWN", "ESCAPE", "Q",
             *[f"F{k + 1}" for k in range(SLOTS)], *[f"SHIFT+F{k + 1}" for k in range(SLOTS)])


def act(reg: Registry, pid: str, op: str, arg: int = 0) -> None:
    p = reg.get(pid)
    if p is None:
        return
    if op == "step":
        p.step(arg)
    elif op == "toggle":
        p.toggle()
    elif op == "fire":
        p.fire()


def _err(where: str, e: Exception) -> str:
    return f"{where}: {type(e).__name__}: {e}"[:160]


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:  # noqa: BLE001, S110 — teardown is best-effort
        pass


def _restart(audio, impl, midi_io, ctrl_win, dream_io=None) -> None:
    # execv swaps the process image in place — same PID, same terminal,
    # same stdio — so stdout doesn't detach and the user's shell keeps
    # owning the child. The OS reclaims the GL contexts and audio device
    # on image swap; we still stop the audio stream first so Core Audio
    # doesn't complain about a stream vanishing mid-callback.
    if midi_io is not None:
        _quiet(midi_io.close)
    if dream_io is not None:
        _quiet(dream_io.close)
    _quiet(audio.stop)
    _quiet(lambda: glfw.make_context_current(ctrl_win))  # imgui's GL objects live there
    _quiet(impl.shutdown)
    _quiet(glfw.terminate)
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _windows():
    """The two GLFW windows on one shared GL context: render first, then controls."""
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, 4)
    # creation-time hints: the framebuffer keeps alpha so overlay mode can
    # clear to see-through (the other modes clear opaque), and fullscreen
    # must not minimise when the control window takes focus (overlay.py)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, True)
    glfw.window_hint(glfw.AUTO_ICONIFY, False)
    render_win = glfw.create_window(*RENDER_SIZE, TITLE, None, None)
    if not render_win:
        glfw.terminate()
        raise SystemExit("could not create the render window")
    # the control window is an ordinary opaque window; the shared context
    # lets both sides see the same buffers, textures and programs
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, False)
    glfw.window_hint(glfw.SAMPLES, 0)
    ctrl_win = glfw.create_window(*CONTROL_SIZE, f"{TITLE} — controls", None, render_win)
    if not ctrl_win:
        glfw.terminate()
        raise SystemExit("could not create the control window")
    # render left, controls flush right on the primary screen's work area;
    # they overlap on a narrow laptop screen until one goes to a projector
    mon = glfw.get_primary_monitor()
    if mon:
        x, y, w, _ = glfw.get_monitor_workarea(mon)
        glfw.set_window_pos(render_win, x + 16, y + 16)
        glfw.set_window_pos(ctrl_win, max(x + w - CONTROL_SIZE[0] - 16, x + 16), y + 16)
    return render_win, ctrl_win


def _make_output(win, reg: Registry, cfg: dict) -> Output:
    """The render window's output settings, seeded from config."""
    out = Output(win, GlfwBackend(glfw))
    out.register(reg)
    # [output] in config.toml — config.load has already folded a pre-split
    # [overlay] section under it, so this is the one place that reads it
    oc = cfg.get("output", {})
    out.monitor = int(oc.get("monitor", -1))
    out.fullscreen = bool(oc.get("fullscreen", False))
    out.overlay = bool(oc.get("on_start", False))
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
        mapping = midi.MidiMap(table=table)
        return midi.MidiIO(reg, mapping, port=mc.get("port"), profile=mc.get("profile", "apc40"),
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


def _open_dream(reg: Registry, cfg: dict):
    """The look-back's dream worker (dream.py, torch), only when [dream] enabled."""
    if not cfg.get("dream", {}).get("enabled", False):
        return None
    try:
        from . import dream
        return dream.DreamWorker(reg, cfg["dream"])
    except Exception as e:  # noqa: BLE001 — no torch, no GPU: the plain tracer runs
        print(f"dream: {e}", file=sys.stderr)
        return None


class Keys:
    """Edge detection and hold timing over polled key state, across both windows.

    A key counts as down when it is down in the render window, or in the
    control window while imgui is not typing (`typing` is io.want_capture_
    keyboard, set each frame after new_frame()). This is the `keys` the
    router's key rows read: pressed() is an edge, shift() / super() the
    modifier state a "key:SHIFT+B" row needs. F1–F8 (⇧ saves) and Cmd+R
    stay in the loop below — they predate the table and are out of plan
    09's scope.
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

    def held(self, key: int) -> float:
        """Seconds the key has been continuously down; 0.0 when up."""
        if not self._down(key):
            self.down_since.pop(key, None)
            return 0.0
        now = time.perf_counter()
        return now - self.down_since.setdefault(key, now)

    def down(self, *keys: int) -> bool:
        return any(self._down(k) for k in keys)

    # the modifier state the routing table's key rows read ("key:SHIFT+B")
    def shift(self) -> bool:
        return self.down(glfw.KEY_LEFT_SHIFT, glfw.KEY_RIGHT_SHIFT)

    def super(self) -> bool:  # the modifier's name, as the table spells it
        return self.down(glfw.KEY_LEFT_SUPER, glfw.KEY_RIGHT_SUPER)


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
    render_win, ctrl_win = _windows()

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

    cfg = config.load()
    audio = AudioEngine()
    control = Control(audio.chain)
    library = Library()                    # presets, projects, the theme bank (its project's)
    # dream.* drives the renderer's look-back (lookback.py); the post pass
    # runs inside renderer.draw
    want = {"restart": False}          # app.restart sets it; polled after the panel draws
    reg = build_registry(s, control, audio, library.project, dream=renderer.lookback.state,
                         fx=renderer.fx.state,
                         restart=lambda: want.__setitem__("restart", True))
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
    panel.clock, panel.lfos = clock, lfos     # the LFO page's scopes and beat light
    panel.output = output
    # one binding table for keys, pad, MIDI and lanes (an old midi_map.json migrates)
    mc = cfg.get("midi", {})
    router = Router(reg, Bindings.load(
        bindings_path(library.home), mc.get("profile", "apc40"),
        Path(mc.get("map", "midi_map.json")),
    ))
    # the macros are the routing layer's, saved with the table and not in
    # any theme; the Router landed them — what the file named and the
    # registry hasn't goes where every other missing id goes
    if router.missing_values:
        library.report(router.missing_values, "bindings.json values")
    library.routing(router)                # the routing presets: the library's files, the router's documents
    # one Learn over the live table, whatever the MIDI gate says: a knob
    # or a hand completes it, the panel's prompt settles what the referee
    # refused (learn.py; the band.sel.* rule is the registry's `real`)
    learn = Learn(reg, router.table)
    panel.learn = learn
    midi_io = _open_midi(reg, cfg, router.table, learn)
    panel.midi = midi_io
    panel.router = router                  # the ROUTING page edits the live table
    bridge_io = _open_bridge(reg, cfg)
    hands_io = _open_hands(cfg, hand_settings)
    panel.hands = hands_io
    panel.hand_settings = hand_settings
    dream_io = _open_dream(reg, cfg)
    if dream_io is not None:            # fills the look-back's dream slot
        renderer.lookback.source = dream_io
    pad = Pad()
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
        (s, "render", "ViewState"),
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
        (router, "routing", "Router"),
        (learn, "learn", "Learn"),
        (clock, "tempo", "Clock"),
        (lfos, "lfo", "LFOs"),
        *[(lf, "lfo", "LFO") for lf in lfos.lfos],
        *([(midi_io, "midi", "MidiIO"), (midi_io.map, "midi", "MidiMap")] if midi_io else []),
        *([(bridge_io, "bridge", "Bridge")] if bridge_io else []),
        *([(hand_settings, "hands.core", "HandSettings")] if hand_settings else []),
        *([(hands_io, "hands.core", "HandsIO")] if hands_io else []),
        *([(dream_io, "dream", "DreamWorker")] if dream_io else []),
        (pad, "gamepad", "Pad"),
    ], watchers=[library])
    panel.reloader = reloader
    panel.config_error = cfg.get("error", "")   # a config.toml that would not parse
    panel.config_notes = cfg.get("notes", [])   # …or that wants a section renamed
    keys = Keys(render_win, ctrl_win)
    mouse = Mouse(render_win, reg, s)
    depth4, yaw, pitch, zoom = reg["view.depth4"], reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]

    # smoke-test escape hatch: HYPERSPACE_FRAMES=n closes after n frames
    frames_left = int(os.environ.get("HYPERSPACE_FRAMES", "0")) or None

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
        now = time.perf_counter()
        dt = min(now - last, 0.05)
        last = now
        fps = fps * 0.95 + (1.0 / max(now and dt, 1e-6)) * 0.05
        clock.tick(now)   # the clock's "now" for the frame: a trigger and the LFO step agree

        # the chain object is recreated on source attach; keep bindings fresh
        control.chain = audio.chain
        reloader.poll()

        # ---- polled keys, from either window ----
        if keys.pressed(glfw.KEY_ESCAPE) or keys.pressed(glfw.KEY_Q):
            glfw.set_window_should_close(render_win, True)
        shift = keys.shift()
        router.keys(keys)         # B taps, ⇧B triggers: both are table rows
        if keys.pressed(glfw.KEY_R):
            if keys.down(glfw.KEY_LEFT_SUPER, glfw.KEY_RIGHT_SUPER):
                _restart(audio, impl, midi_io, ctrl_win, dream_io)
            else:
                act(reg, "camera.reset", "fire")
        # ↑/↓ ride depth4 toward its range limit, accelerating with hold
        for key, sgn in ((glfw.KEY_UP, 1.0), (glfw.KEY_DOWN, -1.0)):
            hold = keys.held(key)
            if hold > 0.0:
                ramp = min(hold / D4_RAMP, 1.0)
                rate = D4_RATE0 + (D4_RATE1 - D4_RATE0) * ramp * ramp
                _ride_depth(depth4, sgn * rate * dt)
        # F1–F8 flip whole-surface themes; with ⇧ held they save instead
        for k in range(SLOTS):
            if keys.pressed(glfw.KEY_F1 + k):
                act(reg, f"theme.{'save' if shift else 'load'}.{k}", "fire")

        # ---- gamepad: a second hand on the same controls (imgui never
        # claims it, so it works even while the panel has keyboard focus) ----
        pad.poll()
        if pad.on:
            router.pad(pad)
            # analog: left stick orbits, right-stick Y zooms about centre,
            # triggers ride depth4 in its own log space (LT out, RT in)
            lx, ly = pad.axis(gamepad.AX_LX), pad.axis(gamepad.AX_LY)
            if lx:
                yaw.nudge(lx * 2.2 * dt)
            if ly:
                pitch.nudge(ly * 2.2 * dt)
            zoom_v = pad.axis(gamepad.AX_RY)
            if zoom_v:
                zoom.scale(2.0 ** (-zoom_v * 1.2 * dt))
            d4 = pad.trigger(gamepad.AX_RT) - pad.trigger(gamepad.AX_LT)
            if d4:
                _ride_depth(depth4, d4 * 2.4 * dt)

        # ---- MIDI controller: routed through the same registry ----
        if midi_io is not None:
            try:
                midi_io.poll()
            except Exception as e:  # noqa: BLE001 — hot-reloaded code may raise
                reloader.runtime_error = _err("midi", e)

        # ---- Ultraleap hands: hand lanes into the table, MIDI out to a DAW ----
        if hands_io is not None:
            try:
                hands_io.poll(dt, learn, router)
            except Exception as e:  # noqa: BLE001
                reloader.runtime_error = _err("hands", e)

        # ---- output: the render window follows the output.* params ----
        output.apply()
        renderer.bg_alpha = output.bg_alpha

        # ---- mouse: orbit / pan / zoom, render window only ----
        mouse.poll(shift)

        # ---- audio + rotation + draw, guarded: hot-reloaded code may raise;
        # record it and keep the loop alive so the next save can fix it ----
        ok = True
        try:
            audio.step(dt)
            if bridge_io is not None:   # lanes out, external lanes in (bridge.py)
                bridge_io.step(audio.chain if audio.on else None, router)
            # the LFOs are a source like any other: stepped on the frame's
            # clock, fed to the table as `lfo` before the modulation pass
            lfos.step(dt, now, clock)
            lfos.publish(router)
            # the lanes are a modulation source like any other (routing.py);
            # once every source has spoken for this frame, land base +
            # offsets on the objects before the integrator reads them
            router.modulate(audio.chain if audio.on else None)
            reg.apply()
            s.integrate(dt)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("step", e)

        # ---- render window: its own size and DPI (a 1080p projector next
        # to a retina laptop) ----
        glfw.make_context_current(render_win)
        w, h = glfw.get_window_size(render_win)
        fbw, fbh = glfw.get_framebuffer_size(render_win)
        ctx.viewport = (0, 0, fbw, fbh)
        try:
            renderer.draw(s, max(w, 1), max(h, 1), dpr=fbw / max(w, 1))
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("render.draw", e)
        glfw.swap_buffers(render_win)

        # ---- control window: black ground, then the imgui frame opened above ----
        glfw.make_context_current(ctrl_win)
        ui_gl.clear(0.0, 0.0, 0.0, 1.0)
        try:
            panel.draw(dt, fps)
        except Exception as e:  # noqa: BLE001
            ok, reloader.runtime_error = False, _err("panel.draw", e)
        if ok:
            reloader.runtime_error = ""

        if want["restart"]:
            want["restart"] = False
            _restart(audio, impl, midi_io, ctrl_win, dream_io)

        if reloader.error or reloader.runtime_error:
            _hot_error_toast(reloader.error or reloader.runtime_error)

        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(ctrl_win)

    if midi_io is not None:
        midi_io.close()
    if bridge_io is not None:
        bridge_io.close()
    if hands_io is not None:
        hands_io.close()
    if dream_io is not None:
        dream_io.close()
    audio.stop()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()
