"""The host (app.py): its import boundary, the config gates, the two input
classes over fake GLFW state, the one close list, and the frame order that
ARCHITECTURE §2 states — pinned over stubs, since the real loop needs two
windows (audit P1, P2, P4, P5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperspace import app
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.params import build_registry
from hyperspace.render import ViewState

# ---- the boundary ----

IMPORT_SCRIPT = """
import sys
import hyperspace.app
gated = ("hyperspace.midi", "hyperspace.bridge", "hyperspace.dream", "leap", "torch")
print(sorted(m for m in gated if m in sys.modules), "hyperspace.hands" in sys.modules)
"""


def test_importing_app_leaves_every_gated_adapter_unimported():
    """`hyperspace.app` is the only importer of the optional adapters and
    imports each one lazily, behind its config gate — so importing the
    module pulls in none of them, nor torch, nor the Ultraleap SDK. The
    hands *package* is the one exception, on purpose: its settings register
    and its page draws whether or not the tracker is on (`_hand_settings`,
    `ui.py`), and `hands/core.py` imports `leap` only inside `LeapSource`.
    In a subprocess, because this test session has long since imported
    them all itself."""
    out = subprocess.run([sys.executable, "-c", IMPORT_SCRIPT], capture_output=True, text=True,
                         check=False, cwd=str(Path(__file__).parents[1]), timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[] True"


# ---- the gates ----

def _registry():
    chain = Analyzer(Analyser())
    return build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain))


def test_a_shut_gate_opens_nothing():
    reg = _registry()
    assert app._open_midi(reg, {"midi": {"enabled": False}}, table=None, learn=None) is None
    assert app._open_bridge(reg, {"bridge": {"enabled": False}}) is None
    assert app._open_hands({"hands": {"enabled": False}}, settings=SimpleNamespace()) is None
    assert app._open_hands({"hands": {"enabled": True}}, settings=None) is None
    assert app._open_dream(reg, {"dream": {"enabled": False}}) is None
    assert app._open_dream(reg, {}) is None                  # off by default
    assert app._open_bridge(reg, {}) is None
    assert app._open_pad({"gamepad": {"enabled": False}}) is None


def test_the_pad_gate_is_open_by_default():
    """[gamepad] enabled defaults to true: the pad never raises when absent,
    so polling for one costs nothing (audit P2)."""
    assert isinstance(app._open_pad({}), app.Pad)
    assert isinstance(app._open_pad({"gamepad": {"enabled": True}}), app.Pad)


def _boom(*_a, **_k):
    raise RuntimeError("boom")


def test_a_broken_adapter_is_a_note_not_a_crash(monkeypatch, capsys):
    """An open gate whose adapter fails to build leaves the slot `None` and
    says why on stderr — the show goes on without it."""
    import hyperspace.bridge
    import hyperspace.hands
    import hyperspace.midi

    reg = _registry()
    monkeypatch.setattr(hyperspace.midi, "MidiIO", _boom)
    monkeypatch.setattr(hyperspace.bridge, "Bridge", _boom)
    monkeypatch.setattr(hyperspace.hands, "HandsIO", _boom)
    monkeypatch.setitem(sys.modules, "hyperspace.dream", SimpleNamespace(DreamWorker=_boom))
    assert app._open_midi(reg, {"midi": {"enabled": True}}, table=None, learn=None) is None
    assert app._open_bridge(reg, {"bridge": {"enabled": True}}) is None
    assert app._open_hands({"hands": {"enabled": True}}, settings=SimpleNamespace()) is None
    assert app._open_dream(reg, {"dream": {"enabled": True}}) is None
    err = capsys.readouterr().err
    for line in ("midi: boom", "bridge: boom", "hands: boom", "dream: boom"):
        assert line in err


# ---- Keys and Mouse over fake GLFW state ----

class FakeGlfw:
    """The handful of glfw calls Keys and Mouse make, over scripted state."""

    def __init__(self):
        self.keys: set[tuple[str, int]] = set()      # (window, key) that are down
        self.buttons: set[int] = set()
        self.cursor = (0.0, 0.0)
        self.size = (1000, 800)
        self.scroll = None

    def install(self, monkeypatch):
        g = app.glfw
        monkeypatch.setattr(g, "get_key",
                            lambda win, k: g.PRESS if (win, k) in self.keys else g.RELEASE)
        monkeypatch.setattr(g, "get_cursor_pos", lambda win: self.cursor)
        monkeypatch.setattr(g, "get_mouse_button",
                            lambda win, b: g.PRESS if b in self.buttons else g.RELEASE)
        monkeypatch.setattr(g, "get_window_size", lambda win: self.size)
        monkeypatch.setattr(g, "set_scroll_callback",
                            lambda win, cb: setattr(self, "scroll", cb))


@pytest.fixture()
def fake(monkeypatch):
    f = FakeGlfw()
    f.install(monkeypatch)
    return f


def test_keys_fire_on_the_edge_from_either_window_unless_imgui_is_typing(fake):
    g = app.glfw
    keys = app.Keys("render", "ctrl")
    assert not keys.pressed(g.KEY_B)
    fake.keys.add(("render", g.KEY_B))
    assert keys.pressed(g.KEY_B)
    assert not keys.pressed(g.KEY_B) and keys.down(g.KEY_B)   # held, not re-fired
    fake.keys.clear()
    assert not keys.pressed(g.KEY_B)
    # the control window counts too — but not while imgui owns the keyboard
    fake.keys.add(("ctrl", g.KEY_B))
    keys.typing = True
    assert not keys.pressed(g.KEY_B)
    keys.typing = False
    assert keys.pressed(g.KEY_B)


def test_keys_hold_time_reads_the_frames_clock(fake):
    """held() is measured on the `now` the loop hands it, not a clock of
    its own (audit P4): the same instant every other frame reader sees."""
    g = app.glfw
    keys = app.Keys("render", "ctrl")
    assert keys.held(g.KEY_UP, 10.0) == 0.0
    fake.keys.add(("render", g.KEY_UP))
    assert keys.held(g.KEY_UP, 10.0) == 0.0          # the press frame
    assert keys.held(g.KEY_UP, 10.25) == pytest.approx(0.25)
    assert keys.held(g.KEY_UP, 11.0) == pytest.approx(1.0)
    fake.keys.clear()
    assert keys.held(g.KEY_UP, 11.1) == 0.0
    fake.keys.add(("render", g.KEY_UP))
    assert keys.held(g.KEY_UP, 12.0) == 0.0          # a new press starts over


def test_keys_read_the_modifiers_the_table_spells(fake):
    g = app.glfw
    keys = app.Keys("render", "ctrl")
    assert not keys.shift() and not keys.super()
    fake.keys.add(("ctrl", g.KEY_RIGHT_SHIFT))
    fake.keys.add(("render", g.KEY_LEFT_SUPER))
    assert keys.shift() and keys.super()


def test_mouse_orbits_pans_and_zooms_on_the_base(fake):
    """Left drag orbits, shift-drag or right-drag pans, the wheel zooms about
    the cursor — every one a relative move on the param's base."""
    g = app.glfw
    reg = _registry()
    view = ViewState()
    mouse = app.Mouse("render", reg, view)
    yaw, pitch, zoom = reg["camera.yaw"], reg["camera.pitch"], reg["camera.zoom"]
    pan_x, pan_y = reg["camera.pan.x"], reg["camera.pan.y"]
    y0, p0, z0 = yaw.base, pitch.base, zoom.base
    # a press anchors the drag; the next frame's movement is the move
    fake.cursor, fake.buttons = (100.0, 100.0), {g.MOUSE_BUTTON_LEFT}
    mouse.poll(shift=False)
    fake.cursor = (140.0, 120.0)
    mouse.poll(shift=False)
    assert yaw.base == pytest.approx(y0 + 40 * 0.005)
    assert pitch.base == pytest.approx(p0 + 20 * 0.005)
    assert (pan_x.base, pan_y.base) == (0.0, 0.0)
    # shift turns the same drag into a pan (a trackpad has no right button)
    mouse.poll(shift=True)                            # re-anchors as a pan
    fake.cursor = (150.0, 110.0)
    mouse.poll(shift=True)
    assert (pan_x.base, pan_y.base) == (10.0, -10.0)
    # letting go ends it; the wheel zooms
    fake.buttons.clear()
    mouse.poll(shift=False)
    assert fake.scroll is not None
    fake.scroll("render", 0.0, 2.0)
    mouse.poll(shift=False)
    assert zoom.base == pytest.approx(min(z0 * 2.0 ** (2.0 * 0.15), zoom.hi))
    assert zoom.base > z0


# ---- the close list ----

def test_close_all_closes_every_adapter_then_stops_audio_and_survives_a_broken_one():
    log: list[str] = []
    audio = SimpleNamespace(stop=lambda: log.append("audio"))
    midi = SimpleNamespace(close=lambda: log.append("midi"))
    bridge = SimpleNamespace(close=_boom)
    hands = SimpleNamespace(close=lambda: log.append("hands"))
    app.close_all(audio, midi, bridge, hands, None)
    assert log == ["midi", "hands", "audio"]


# ---- the frame ----

class Stub:
    """Records every method call by name onto a shared log; attributes
    default to the values the frame reads."""

    def __init__(self, name: str, log: list[str], **attrs):
        self._name, self._log = name, log
        self.__dict__.update(attrs)

    def __getattr__(self, method):
        if method.startswith("_"):
            raise AttributeError(method)

        def call(*_a, **_k):
            self._log.append(f"{self._name}.{method}")
            return self.__dict__.get(f"{method}__returns")
        return call

    def __getitem__(self, pid):
        """reg["view.depth4"]: a param stub named by its id, recording its
        relative writes (`nudge`, `scale`) on the same log."""
        return Stub(pid, self._log, base=2.0, lo=1.0, hi=20.0)


def _host(log: list[str], *, pad_on=True, pressed=(), held=(), super_=False, stick=0.0):
    """Every piece of the loop as a recording stub; the gates all open."""
    g = app.glfw
    down = set(pressed)
    keys = Stub("keys", log, typing=False)
    keys.pressed = lambda k: k in down
    keys.held = lambda k, now: 0.5 if k in held else 0.0
    keys.shift = lambda: False
    keys.super = lambda: super_
    keys.down = lambda *ks: any(k in down for k in ks)
    pad = Stub("pad", log, on=pad_on)
    pad.axis = lambda i: stick
    pad.trigger = lambda i: 0.0
    chain = object()
    audio = Stub("audio", log, chain=chain, on=True)
    reg = Stub("reg", log)
    fired: list[str] = []
    reg.get = lambda pid: SimpleNamespace(fire=lambda: fired.append(pid),
                                          step=lambda a: None, toggle=lambda: None)
    reg.__dict__["fired"] = fired
    panel = Stub("panel", log, restart_requested=False)
    renderer = Stub("renderer", log)
    h = app.Host(
        reg=reg, view=Stub("view", log), control=Stub("control", log), audio=audio,
        router=Stub("router", log), clock=Stub("clock", log), lfos=Stub("lfos", log),
        keys=keys, mouse=Stub("mouse", log), output=Stub("output", log, bg_alpha=0.5),
        renderer=renderer, panel=panel, reloader=Stub("reloader", log, runtime_error="x"),
        draw_render=lambda dt: log.append("render.draw"),
        draw_panel=lambda dt, fps: log.append("panel.draw"),
        restart=lambda: log.append("restart"), quit=lambda: log.append("quit"),
        pad=pad, midi_io=Stub("midi", log), hands_io=Stub("hands", log),
        bridge_io=Stub("bridge", log), dream_io=None,
    )
    assert g.KEY_ESCAPE  # the fake never touches glfw; the keys are plain ints
    return h


# ARCHITECTURE §2, top to bottom: the scene-setters, the feeds, the pass, the draw
ORDER = [
    "clock.tick", "reloader.poll",
    "router.keys",                                   # key rows (and the loop keys)
    "pad.poll", "router.pad",                        # pad and hat rows, sticks
    "midi.poll",                                     # cc and note rows
    "hands.poll",                                    # feeds hand
    "output.apply",                                  # reads last frame's objects
    "mouse.poll",                                    # relative writers, to the base
    "audio.step",                                    # new lanes
    "bridge.step",                                   # feeds ext
    "lfos.step", "lfos.publish",                     # feeds lfo
    "router.modulate", "reg.apply", "view.integrate",  # the pass, then one commit
    "render.draw", "panel.draw",                     # the two windows
]


def test_the_frame_runs_in_the_documented_order():
    log: list[str] = []
    h = _host(log)
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    assert log == ORDER
    assert h.renderer.bg_alpha == 0.5                # the output's ground, this frame
    assert h.control.chain is h.audio.chain          # the chain stays one object
    assert h.reloader.runtime_error == ""            # a clean frame clears the toast


def test_an_absent_pad_or_adapter_is_simply_skipped():
    log: list[str] = []
    h = _host(log)
    h.pad, h.midi_io, h.hands_io, h.bridge_io = None, None, None, None
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log == [s for s in ORDER
                   if not s.startswith(("pad.", "router.pad", "midi.", "hands.", "bridge."))]
    log.clear()
    h = _host(log, pad_on=False)                     # a pad polled for but not there
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert "pad.poll" in log and "router.pad" not in log


def test_a_raising_step_is_recorded_and_the_windows_still_draw():
    log: list[str] = []
    h = _host(log)
    h.lfos.step = _boom
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("step: RuntimeError: boom")
    assert "router.modulate" not in log              # the pass stopped where it raised
    assert log[-2:] == ["render.draw", "panel.draw"]


def test_a_raising_adapter_is_a_note_that_survives_the_frame():
    """A MIDI or hands adapter that raises (hot-reloaded code with a bug)
    is recorded like a raising step — and stays recorded until a clean
    frame, rather than being wiped by the end-of-frame reset while the
    loop silently drops its input."""
    log: list[str] = []
    h = _host(log)
    h.midi_io.poll = _boom
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("midi: RuntimeError: boom")
    assert "hands.poll" in log and "reg.apply" in log and "render.draw" in log
    h.midi_io.poll = lambda: None
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    assert h.reloader.runtime_error == ""            # …and a clean frame clears it
    h.hands_io.poll = _boom
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("hands: RuntimeError: boom")


def test_the_relative_writers_run_with_the_setters_and_move_the_base():
    """↑/↓ held and the pad's sticks are relative writers on the base
    (`nudge` / `scale`), and they run in the scene-setter block — after the
    key rows and the pad rows, before any source feeds."""
    g = app.glfw
    log: list[str] = []
    h = _host(log, held={g.KEY_UP}, stick=0.5)
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    i = log.index
    assert i("router.keys") < i("view.depth4.nudge") < i("pad.poll") < i("router.pad")
    assert i("router.pad") < i("camera.yaw.nudge") < i("camera.pitch.nudge")
    assert i("camera.pitch.nudge") < i("camera.zoom.scale") < i("midi.poll")
    assert log.count("view.depth4.nudge") == 1     # the triggers rest, so no second ride


def test_the_loop_keys_outside_the_table():
    """Esc / Q close, R resets the camera, Cmd+R restarts the process, and
    the panel's restart button restarts too — the keys ARCHITECTURE §3.7
    lists as loop code."""
    g = app.glfw
    log: list[str] = []
    h = _host(log, pressed={g.KEY_ESCAPE})
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log[2] == "quit" and "restart" not in log
    log.clear()
    h = _host(log, pressed={g.KEY_R})
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert h.reg.fired == ["camera.reset"] and "restart" not in log
    log.clear()
    h = _host(log, pressed={g.KEY_R}, super_=True)
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log.count("restart") == 1 and h.reg.fired == []
    log.clear()
    h = _host(log)
    h.panel.restart_requested = True
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log[-1] == "restart" and h.panel.restart_requested is False


def test_the_host_close_list_is_every_adapter_in_shutdown_order():
    log: list[str] = []
    h = _host(log)
    assert h.adapters == (h.midi_io, h.bridge_io, h.hands_io, None)
