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
    assert app._open_dream(reg, {"dream": {"enabled": False}}) == (None, "")
    assert app._open_dream(reg, {}) == (None, "")            # off by default
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
    assert app._open_dream(reg, {"dream": {"enabled": True}}) == (
        None, "dream worker off: RuntimeError: boom")
    # torch missing (no `dream` extra): dream.py's own `import torch`
    # fails, and the reason names the fix
    import hyperspace
    monkeypatch.delitem(sys.modules, "hyperspace.dream")
    monkeypatch.delattr(hyperspace, "dream", raising=False)
    monkeypatch.setitem(sys.modules, "torch", None)
    off, why = app._open_dream(reg, {"dream": {"enabled": True}})
    assert off is None
    assert why == ("dream worker off: torch is not installed — run `uv sync`, "
                   "then launch with `uv run hyperspace`")
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
    assert not keys.shift() and not keys.super() and not keys.control()
    fake.keys.add(("ctrl", g.KEY_RIGHT_SHIFT))
    fake.keys.add(("render", g.KEY_LEFT_SUPER))
    assert keys.shift() and keys.super() and not keys.control()
    fake.keys.add(("render", g.KEY_RIGHT_CONTROL))
    assert keys.control()
    # every modifier the table may spell is one the adapter reads (plan 15)
    from hyperspace.routing import MODIFIERS
    assert MODIFIERS == ("SHIFT", "SUPER", "CONTROL")
    assert all(callable(getattr(keys, m.lower())) for m in MODIFIERS)


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
    keys.pressed = lambda k: k in down and down.discard(k) is None   # an edge, once
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
        keys=keys, mouse=Stub("mouse", log), output=Stub("output", log, bg_alpha=0.5, dim=0.4),
        renderer=renderer, panel=panel, reloader=Stub("reloader", log, runtime_error="x"),
        draw_render=lambda dt: log.append("render.draw"),
        draw_panel=lambda dt, fps: log.append("panel.draw"),
        restart=lambda: log.append("restart"), quit=lambda: log.append("quit"),
        pad=pad, midi_io=Stub("midi", log), hands_io=Stub("hands", log),
        bridge_io=Stub("bridge", log), dream_io=None, undo=Stub("undo", log),
    )
    assert g.KEY_ESCAPE  # the fake never touches glfw; the keys are plain ints
    return h


# ARCHITECTURE §2, top to bottom: the scene-setters, the feeds, the pass, the draw
ORDER = [
    "clock.tick", "reloader.poll",
    "router.keys",                                   # key rows (and the loop keys)
    "pad.poll", "router.pad",                        # pad and hat rows, sticks
    "midi.poll",                                     # cc and note rows
    "router.follow_macros",                          # the macros' base subscribers
    "undo.tick",                                     # the bases, compared (plan 15 WP1)
    "hands.poll",                                   # feeds hand
    "output.apply",                                  # reads last frame's objects
    "mouse.poll",                                    # relative writers, to the base
    "audio.step", "audio.publish",                   # new lanes, and their names (R8)
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
    assert h.renderer.dim == 0.4                     # and its master dim (plan 15 WP3)
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
    """Esc / Q close, Cmd+R restarts the process, and the panel's restart
    button restarts too — the keys ARCHITECTURE §3.7 lists as loop code.
    R alone is a table row since plan 11: the loop leaves its edge for
    `router.keys`; with ⌘ held the loop claims the edge first, so the
    `key:R` row (camera.reset) never hears a restart."""
    g = app.glfw
    log: list[str] = []
    h = _host(log, pressed={g.KEY_ESCAPE})
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log[2] == "quit" and "restart" not in log
    log.clear()
    h = _host(log, pressed={g.KEY_R})
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert "restart" not in log and h.reg.fired == []           # the loop leaves R alone…
    assert h.keys.pressed(g.KEY_R)                               # …its edge is the table's
    log.clear()
    h = _host(log, pressed={g.KEY_R}, super_=True)
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log.count("restart") == 1 and h.reg.fired == []
    assert log.index("restart") < log.index("router.keys")
    assert not h.keys.pressed(g.KEY_R)                           # claimed before the table
    log.clear()
    h = _host(log)
    h.panel.restart_requested = True
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log[-1] == "restart" and h.panel.restart_requested is False


def test_the_host_close_list_is_every_adapter_in_shutdown_order():
    log: list[str] = []
    h = _host(log)
    assert h.adapters == (h.midi_io, h.bridge_io, h.hands_io, None)


# ---- decision 21 (a): the transparent framebuffer only when the config asks ----

class _HintGlfw:
    """Records window hints and the hints each window was created under."""

    def __init__(self):
        self.hints: dict = {}
        self.created: list[dict] = []

    def window_hint(self, k, v):
        self.hints[k] = v

    def create_window(self, w, h, title, mon, share):
        self.created.append(dict(self.hints))
        return f"win{len(self.created)}"

    def get_primary_monitor(self):
        return None

    def __getattr__(self, name):        # every glfw constant: its own name
        if name.isupper():
            return name
        raise AttributeError(name)


@pytest.mark.parametrize(("cfg", "want"), [
    ({}, False),                                        # the default
    ({"output": {"overlay": False}}, False),
    ({"output": {"overlay": True}}, True),
])
def test_the_render_window_is_transparent_only_when_the_config_asks(monkeypatch, cfg, want):
    g = _HintGlfw()
    monkeypatch.setattr(app, "glfw", g)
    render, ctrl = app._windows(app._overlay_allowed(cfg))
    assert (render, ctrl) == ("win1", "win2")
    assert g.created[0]["TRANSPARENT_FRAMEBUFFER"] is want
    assert g.created[1]["TRANSPARENT_FRAMEBUFFER"] is False    # the control window, always


def test_the_config_defaults_shut_overlay():
    from hyperspace import config

    assert config.DEFAULTS["output"]["overlay"] is False
    assert app._overlay_allowed({"output": dict(config.DEFAULTS["output"])}) is False


# ---- plan 16 WP4: the windows open where placement says, and the exits remember ----

class _PlaceGlfw(_HintGlfw):
    """Two screens (the laptop, then a projector to its right) and windows
    that record the size they were created at and where they were put."""

    def __init__(self, mons=None):
        super().__init__()
        self.mons = mons if mons is not None else {
            "Built-in": (0, 38, 1728, 1041), "Projector": (1728, 0, 1920, 1080)}
        self.size: dict = {}
        self.pos: dict = {}
        self.iconified: set = set()

    def get_monitors(self):
        return list(self.mons)

    def get_monitor_workarea(self, m):
        return self.mons[m]

    def get_monitor_name(self, m):
        return m.encode()

    def create_window(self, w, h, title, mon, share):
        win = super().create_window(w, h, title, mon, share)
        self.size[win] = (w, h)
        return win

    def set_window_pos(self, win, x, y):
        self.pos[win] = (x, y)

    def get_window_pos(self, win):
        return self.pos[win]

    def get_window_size(self, win):
        return self.size[win]

    def get_window_attrib(self, win, attr):
        assert attr == "ICONIFIED"
        return int(win in self.iconified)


def _open(monkeypatch, cfg, home, mons=None):
    """A launch's `_windows` on a fresh fake window system."""
    g = _PlaceGlfw(mons)
    monkeypatch.setattr(app, "glfw", g)
    render, ctrl = app._windows(False, cfg, home)
    return g, render, ctrl


def test_the_windows_open_where_placement_says(monkeypatch, tmp_path, capsys):
    from hyperspace import config, placement

    place = placement.place
    # first launch — no file, default config: the spots and sizes as before
    cfg = {"output": dict(config.DEFAULTS["output"])}
    g, render, ctrl = _open(monkeypatch, cfg, tmp_path)
    assert (g.size[render], g.pos[render]) == (app.RENDER_SIZE, (16, 54))
    assert (g.size[ctrl], g.pos[ctrl]) == (app.CONTROL_SIZE, (1728 - 960 - 16, 54))
    assert "notes" not in cfg and not (tmp_path / placement.FILE).exists()   # a launch only reads

    # remembered: created at the remembered size, put at the remembered spot
    placement.save(tmp_path, (300, 90, 800, 850), [(1900, 120, 1000, 700)],
                   placement.screens(g))
    g, render, ctrl = _open(monkeypatch, cfg, tmp_path)
    assert (g.size[render], g.pos[render]) == ((1000, 700), (1900, 120))
    assert (g.size[ctrl], g.pos[ctrl]) == ((800, 850), (300, 90))

    # the config's screens win: the control window on control_monitor, the
    # render window (remembered on the projector) on monitor 0
    cfg = {"output": {"monitor": 0, "control_monitor": 1}}
    g, render, ctrl = _open(monkeypatch, cfg, tmp_path)
    assert (g.size[render], g.pos[render]) == (app.RENDER_SIZE, (16, 54))
    assert (g.size[ctrl], g.pos[ctrl]) == (app.CONTROL_SIZE, (1728 + 1920 - 960 - 16, 16))
    assert "notes" not in cfg

    # the projector unplugged, and a config index with no screen: default
    # spots on the primary, said on stderr and in cfg["notes"] (the SYSTEM page)
    cfg = {"output": {"monitor": -1, "control_monitor": 1}, "notes": ["an earlier note"]}
    capsys.readouterr()
    g, render, ctrl = _open(monkeypatch, cfg, tmp_path, {"Built-in": (0, 38, 1728, 1041)})
    assert (g.size[render], g.pos[render]) == (app.RENDER_SIZE, (16, 54))
    assert (g.size[ctrl], g.pos[ctrl]) == ((800, 850), (300, 90))     # −1 after the note
    assert cfg["notes"][0] == "an earlier note" and len(cfg["notes"]) == 3
    assert '"Projector", which is not connected' in cfg["notes"][1]
    assert "control_monitor = 1, but 1 screen is connected" in cfg["notes"][2]
    err = capsys.readouterr().err
    assert all(n in err for n in cfg["notes"][1:])

    # no screens at all: default sizes, no position set — as before
    g, render, ctrl = _open(monkeypatch, cfg, tmp_path, {})
    assert (g.size[render], g.size[ctrl]) == (app.RENDER_SIZE, app.CONTROL_SIZE) and g.pos == {}

    # placement raising on something nobody foresaw: default spots and a note, never a dead launch
    cfg = {"output": {}}
    monkeypatch.setattr(placement, "place", _boom)
    g, render, ctrl = _open(monkeypatch, cfg, tmp_path)
    assert (g.pos[render], g.pos[ctrl]) == ((16, 54), (1728 - 960 - 16, 54))
    assert len(cfg["notes"]) == 1 and cfg["notes"][0].startswith("placement: ")
    monkeypatch.setattr(placement, "place", place)

    # and with no home given nothing is read: the old one-argument call
    g = _PlaceGlfw()
    monkeypatch.setattr(app, "glfw", g)
    render, ctrl = app._windows(False)
    assert (g.pos[render], g.pos[ctrl]) == ((16, 54), (1728 - 960 - 16, 54))


def test_the_exits_save_the_windowed_rects(monkeypatch, tmp_path):
    import inspect

    from hyperspace import library, placement
    from hyperspace.overlay import Output

    g, render, ctrl = _open(monkeypatch, {}, tmp_path)

    class Backend:                       # the render window's rect, as overlay.GlfwBackend reads it
        def window_rect(self, win):
            return (*g.pos[win], *g.size[win])

    out = Output(render, Backend())
    g.pos[render], g.size[render] = (1900, 120), (1000, 700)   # dragged to the projector
    g.pos[ctrl] = (300, 90)

    # quit: main's helper writes both windows' rects
    app._save_windows(tmp_path, render, ctrl, out)
    doc = placement.load(tmp_path)
    assert doc["control"] == {"x": 300, "y": 90, "w": 960, "h": 900, "screen": "Built-in"}
    assert doc["render"] == [{"x": 1900, "y": 120, "w": 1000, "h": 700, "screen": "Projector"}]

    # fullscreen at the exit: the windowed rect, never the cover of the screen (F6)
    out._applied["mode"], out._saved_rect = "fullscreen", (1900, 120, 1000, 700)
    g.pos[render], g.size[render] = (1728, 0), (1920, 1080)
    g.pos[ctrl] = (340, 90)
    app._save_windows(tmp_path, render, ctrl, out)
    doc = placement.load(tmp_path)
    assert doc["render"][0]["w"] == 1000 and doc["render"][0]["x"] == 1900
    assert doc["control"]["x"] == 340

    # a minimised window keeps its old entry
    g.iconified = {ctrl, render}
    g.pos[ctrl] = (-32000, -32000)
    app._save_windows(tmp_path, render, ctrl, out)
    assert placement.load(tmp_path) == doc

    # restart (⌘R): saved before the windows go, and a save that raises
    # stops nothing
    log: list[str] = []
    g.make_context_current = lambda w: None
    g.terminate = lambda: log.append("terminate")
    monkeypatch.setattr(app.os, "execv", lambda *a: log.append("execv"))
    audio = SimpleNamespace(stop=lambda: log.append("audio"))
    impl = SimpleNamespace(shutdown=lambda: log.append("shutdown"))
    g.iconified = set()
    g.pos[ctrl] = (360, 90)

    def save():
        log.append("save")
        app._save_windows(tmp_path, render, ctrl, out)

    app._restart(audio, (), impl, ctrl, save=save)
    assert log == ["save", "audio", "shutdown", "terminate", "execv"]
    assert placement.load(tmp_path)["control"]["x"] == 360
    log.clear()
    app._restart(audio, (), impl, ctrl, save=_boom)
    assert log == ["audio", "shutdown", "terminate", "execv"]
    app._restart(audio, (), impl, ctrl)                       # and none given is none
    # an unwritable home costs only the memory
    app._save_windows(tmp_path / "gone", render, ctrl, out)

    # both exits are wired in main: the quit saves before the windows are
    # torn down, the restart is handed the same save, and the home is the
    # one config.load uses (library.home(): $HYPERSPACE_HOME)
    src = inspect.getsource(app.main)
    assert src.index("_quiet(save_windows)") < src.index("impl.shutdown()") < src.index(
        "glfw.terminate()")
    assert "save=save_windows" in src and "home = library_home()" in src
    assert app.library_home is library.home


# ---- the desk's table and knob smoothing's default (plan 18 WP2, fork 12) ----

def _launch(home):
    """`app.main`'s order around the desk's table, headless: the table is
    read and `_desk_table` called before the library attaches, the router
    and the presets after, then the show's startup preset."""
    from hyperspace import lfo, preset, tempo
    from hyperspace.library import Library
    from hyperspace.preset import Presets
    from hyperspace.routing import Bindings, Router, bindings_path

    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(home, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.project)
    lib.on_layout("band", control.apply_layout)
    lib.extra("band", lambda: {"layout": chain.layout()})
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    table = app._desk_table(reg, Bindings.load(bindings_path(home), legacy_midi=None))
    lib.attach(reg)
    router = Router(reg, table)
    Presets(lib, reg, router)
    preset.migrate_home(lib, router)
    lib.project.load_startup()
    return SimpleNamespace(lib=lib, reg=reg, table=table, show=lib.project)


def test_the_app_starts_with_knob_smoothing_at_80_ms_and_a_show_keeps_its_own(tmp_path):
    """Fork 12 as settled: a bare table is at 0 and the app's is at
    `routing.SLEW_DEFAULT_S` before the show lands. A factory show, which
    names no smoothing, opens at 80 ms and is not unsaved because of it;
    a show that saved a number keeps it — 0 included — with no unknown-id
    warning, since the param exists when the session values land (`main`
    makes the table before `library.attach`); a show file from before the
    param opens at 80 ms, clean; and a new show goes back to 80 ms."""
    import inspect
    import json

    from hyperspace import routing

    assert routing.Bindings().slew == 0.0 and routing.SLEW_DEFAULT_S == 0.08
    src = inspect.getsource(app.main)
    assert 0 < src.index("_desk_table(reg, Bindings.load(") < src.index("library.attach(reg)")
    assert src.index("library.attach(reg)") < src.index("Router(reg, table)")

    home = tmp_path / "home"
    r = _launch(home)                                   # a fresh home: the factory party show
    slew = r.reg["desk.slew"]
    assert r.show.name == "party" and r.show.factory
    assert r.table.slew == 0.08 and slew.text() == "80 ms"
    assert not r.show.is_dirty() and not r.lib.is_dirty("desk") and not r.lib.warning
    assert r.show.session["desk.slew"] == 0.08          # the reference the dot compares with
    slew.set(0.0)                                       # the owner turns it off: the show's to save
    assert r.show.is_dirty()
    slew.set(0.08)
    assert not r.show.is_dirty()
    slew.set(0.0)
    r.show.save("mine")
    assert not r.show.is_dirty()

    r = _launch(home)                                   # the next launch opens that show
    assert r.show.name == "mine" and not r.show.factory
    assert r.table.slew == 0.0 and r.reg["desk.slew"].text() == "off"
    assert not r.show.is_dirty() and not r.lib.warning
    r.reg["desk.slew"].set(0.2)
    r.show.save()
    r = _launch(home)
    assert r.table.slew == 0.2 and not r.show.is_dirty() and not r.lib.warning

    r.show.new()                                        # a new show: the app's default again
    assert r.table.slew == 0.08

    # a show saved before the param existed: no key, 80 ms, clean
    path = home / "projects" / "mine.hyp.json"
    doc = json.loads(path.read_text())
    assert doc["session"].pop("desk.slew") == 0.2
    path.write_text(json.dumps(doc))
    r = _launch(home)
    assert r.show.name == "mine" and r.table.slew == 0.08
    assert not r.show.is_dirty() and not r.lib.warning
