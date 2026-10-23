"""The host (app.py): its import boundary, the device gates (plan 27 B1:
the registry opens each device behind its own `[[devices]]` entry), the
two input classes over fake GLFW state, the one close list, and the frame
order that ARCHITECTURE §2 states — pinned over stubs, since the real loop
needs two windows (audit P1, P2, P4, P5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperspace import app, config, devices
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.params import build_registry
from hyperspace.render import ViewState

# ---- the boundary ----

IMPORT_SCRIPT = """
import sys
import hyperspace.app
gated = ("hyperspace.midi", "hyperspace.bridge", "hyperspace.dream", "hyperspace.osc",
         "leap", "torch", "pythonosc",
         "av", "pillow_heif", "syphon", "cyndilib", "AVFoundation")
print(sorted(m for m in gated if m in sys.modules), "hyperspace.hands" in sys.modules)
"""


def test_importing_app_leaves_every_gated_adapter_unimported():
    """`hyperspace.devices` is the only importer of the optional adapters
    and imports each one lazily, inside its device's `open` (plan 27 B1) —
    so importing `app` pulls in none of them, nor torch, nor the Ultraleap
    SDK, nor the OSC library (B4's `osc.py` and `pythonosc` are gated the
    same way before they exist). The hands *package* is the one exception,
    on purpose: its settings register and its page draws whether or not
    the tracker is on (`_hand_settings`, `ui.py`), and `hands/core.py`
    imports `leap` only inside `LeapSource`. In a subprocess, because this
    test session has long since imported them all itself."""
    out = subprocess.run([sys.executable, "-c", IMPORT_SCRIPT], capture_output=True, text=True,
                         check=False, cwd=str(Path(__file__).parents[1]), timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[] True"


# ---- the gates ----

def _registry():
    chain = Analyzer(Analyser())
    return build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain))


def _entries(**enabled: bool) -> list[dict]:
    """Today's four devices as checked entries, each gate as given."""
    roles = {"midi": "apc40", "gamepad": "pad", "hands": "leap", "bridge": "bridge"}
    return [{"role": roles[k], "kind": k, "enabled": on} for k, on in enabled.items()]


def test_a_shut_gate_opens_nothing(monkeypatch):
    """A `[[devices]]` entry with `enabled = false` is listed as `off`:
    its device is never opened, so its adapter module is never imported
    (plan 27 B1; the `_open_*` gates this replaced)."""
    for cls in (devices.MidiDevice, devices.PadDevice, devices.HandsDevice,
                devices.BridgeDevice):
        monkeypatch.setattr(cls, "open", _boom)
    reg = devices.DeviceRegistry(_entries(midi=False, gamepad=False, hands=False, bridge=False),
                                 devices.Context(reg=_registry()))
    reg.open_all()
    assert [d.status for d in reg] == ["off"] * 4
    assert [d.role for d in reg] == ["apc40", "pad", "leap", "bridge"]
    for kind in ("midi", "gamepad", "hands", "bridge"):
        assert reg.adapter(kind) is None
    # the config gives the same list from the old tables, every gate shut
    cfg = {"devices": _entries(midi=False, gamepad=False, hands=False, bridge=False)}
    assert all(not e["enabled"] for e in config.devices(cfg))
    # a hands entry with no hands setup is an error, not a crash
    r2 = devices.DeviceRegistry(_entries(hands=True), devices.Context(hand_settings=None))
    monkeypatch.undo()
    r2.open_all()
    assert r2.get("leap").status.startswith("error: RuntimeError: no hands setup")
    # the dream worker is not a device: its gate is app's, as before
    assert app._open_dream(_registry(), {"dream": {"enabled": False}}) == (None, "")
    assert app._open_dream(_registry(), {}) == (None, "")            # off by default


def test_the_pad_gate_is_open_by_default(tmp_path):
    """A config with no `[[devices]]` and no `[gamepad]` lists the pad
    enabled (the old table's default): the pad never raises when absent,
    so polling for one costs nothing (audit P2). The registry opens a
    `gamepad.Pad` for it; `enabled = false` leaves it `off`."""
    from hyperspace import gamepad

    cfg = config.load(tmp_path / "config.toml")
    (pad,) = [e for e in config.devices(cfg) if e["kind"] == "gamepad"]
    assert pad == {"role": "pad", "kind": "gamepad", "enabled": True, "usb": True,
                   "dial_left": "petal", "dial_right": "blend"}
    reg = devices.DeviceRegistry([pad])
    reg.open_all()
    assert isinstance(reg.adapter("gamepad"), gamepad.Pad)
    assert reg.get("pad").status == "lost"              # no pad on this machine
    assert reg.get("pad").io.usb is True
    reg.close()
    assert reg.adapter("gamepad") is None
    off = devices.DeviceRegistry([{**pad, "enabled": False}])
    off.open_all()
    assert off.get("pad").status == "off" and off.adapter("gamepad") is None


def _boom(*_a, **_k):
    raise RuntimeError("boom")


def test_a_broken_adapter_is_a_note_not_a_crash(monkeypatch, capsys):
    """A device whose adapter fails to build is `error: …` on its line, no
    adapter, and says why once on stderr and in the config notes — the
    show goes on without it (and the registry tries again on the Ports
    schedule, tests/test_devices.py)."""
    import hyperspace.bridge
    import hyperspace.hands
    import hyperspace.midi

    reg = _registry()
    monkeypatch.setattr(hyperspace.midi, "MidiIO", _boom)
    monkeypatch.setattr(hyperspace.bridge, "Bridge", _boom)
    monkeypatch.setattr(hyperspace.hands, "HandsIO", _boom)
    monkeypatch.setitem(sys.modules, "hyperspace.dream", SimpleNamespace(DreamWorker=_boom))
    notes: list[str] = []
    rig = devices.DeviceRegistry(_entries(midi=True, bridge=True, hands=True),
                                 devices.Context(reg=reg, hand_settings=SimpleNamespace(),
                                                 notes=notes))
    rig.open_all()
    assert [d.status for d in rig] == ["error: RuntimeError: boom"] * 3
    assert all(rig.adapter(k) is None for k in ("midi", "bridge", "hands"))
    assert notes == ["midi: boom", "bridge: boom", "hands: boom"]
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
    # plan 26 A2: the pan is in world units — the cursor's px over the px a
    # unit spans at the origin through the eye
    unit = app._px_per_unit(view, *g.get_window_size("render"))
    assert (pan_x.base, pan_y.base) == pytest.approx((10.0 / unit, -10.0 / unit))
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
    # the four devices as the registry's shims over recording stubs, in
    # today's list order (config.DEVICE_TABLES): the pad, MIDI, the hands,
    # the bridge — each counted open because it holds an adapter
    midi = Stub("midi", log, on=True, error="", last="", bindings=[])
    midi.name = ""
    rig = devices.DeviceRegistry(devices=[
        devices.PadDevice("pad", None, devices.Context(reg=reg), io=pad),   # its camera job's reg
        devices.MidiDevice("apc40", io=midi),
        devices.HandsDevice("leap", io=Stub("hands", log, status="tracking", last="",
                                            source=SimpleNamespace(on=True))),
        # the bridge's sink half reads the table's sink rows (plan 27 B3):
        # `table.sinks` then `bridge.send_values`, the path a live rig runs
        devices.BridgeDevice(
            "bridge", None,
            devices.Context(table=SimpleNamespace(
                sinks=lambda role: log.append("table.sinks") or [])),
            io=Stub("bridge", log, on=True, error=""), audio=audio)])
    h = app.Host(
        reg=reg, view=Stub("view", log), control=Stub("control", log), audio=audio,
        router=Stub("router", log), clock=Stub("clock", log), lfos=Stub("lfos", log),
        keys=keys, mouse=Stub("mouse", log), output=Stub("output", log, bg_alpha=0.5, dim=0.4),
        renderer=renderer, panel=panel, reloader=Stub("reloader", log, runtime_error="x"),
        draw_render=lambda dt: log.append("render.draw"),
        draw_panel=lambda dt, fps: log.append("panel.draw"),
        restart=lambda: log.append("restart"), quit=lambda: log.append("quit"),
        devices=rig, dream_io=None, undo=Stub("undo", log), media=Stub("media", log),
    )
    assert g.KEY_ESCAPE  # the fake never touches glfw; the keys are plain ints
    return h


# ARCHITECTURE §2, top to bottom: the scene-setters, the feeds, the pass,
# the draw. Plan 27 B1: the devices poll in the scene-setter slot (the
# registry, in list order — the pad's rows, then MIDI's), the sources feed
# in the feed slot (the hands feed `hand`, the bridge feeds `ext`), and the
# sinks run after `reg.apply` (`devices.send`). Plan 27
# B2: the sticks' camera job is the pad device's own (`gamepad.steer`, in
# its `act`), so it runs right after the pad's rows, before MIDI's. Plan 27
# B3: the bridge is two halves — its ports looked for again in its `poll`,
# the ext lanes received and published in the feed slot, the out half a
# sink after `reg.apply` (effective values, no longer a frame behind)
ORDER = [
    "clock.tick", "reloader.poll",
    "router.keys",                                   # key rows (and the loop keys)
    "pad.poll", "router.pad",                        # devices.poll: the pad — axis lanes, pad and hat rows
    "router.claimed",                                #   …its sticks no route names, to the base
    "pad.lanes", "router.felt",                      #   …through the pad's feel (motion.py)
    "midi.poll",                                     #   …MIDI — cc and note rows
    "bridge.reconnect",                              #   …the bridge's ports, looked for again
    "media.poll",                                    # the media channels follow their slots (plan 32)
    "router.follow_macros",                          # the macros' base subscribers
    "undo.tick",                                     # the bases, compared (plan 15 WP1)
    "output.apply",                                  # reads last frame's objects
    "mouse.poll",                                    # relative writers, to the base
    "audio.step", "audio.publish",                   # new lanes, and their names (R8)
    "hands.poll",                                    # devices.feed: the hands feed hand
    "bridge.receive", "bridge.publish",              #   …the bridge feeds ext, its labels
    "router.modulate", "reg.apply",                  # the pass (the LFOs step inside it,
                                                     # plan 28 N0), then one commit
    "table.sinks", "bridge.send_values",             # devices.send: the sinks' rows (B3)
    "view.integrate",
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


def test_main_hands_the_router_its_lfos():
    """Plan 28 N0: the LFOs step inside `router.modulate`, so `ORDER` no
    longer shows them — a main that forgot `router.use_lfos(lfos, clock)`
    would freeze every LFO with the frame order unchanged. The call is in
    `main`, on the router it builds, with the bank and clock it registered."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(app.main))
    calls = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "use_lfos"]
    assert calls == ["router.use_lfos(lfos, clock)"]


def test_main_hands_the_router_its_envelopes_and_sequencer():
    """Plan 31 W1: the envelopes are a second bank and the sequencer fires
    them, both stepped inside `router.modulate` — a main that forgot either
    call would leave every envelope at rest and the grid silent, with the
    frame order unchanged. Each is registered before the router takes it,
    and both are hot-reload targets."""
    import ast
    import inspect

    src = inspect.getsource(app.main)
    tree = ast.parse(src)
    calls = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr in ("use_bank", "use_sequencer")]
    assert calls == ["router.use_bank(envs, clock)", "router.use_sequencer(seq, envs)"]
    assert src.index("envelope.register(reg, envs, clock)") < src.index("library.attach(reg)")
    assert src.index("sequencer.register(reg, seq, clock)") < src.index("library.attach(reg)")
    assert src.index("router.use_lfos(lfos, clock)") < src.index("router.use_bank(envs, clock)")
    assert '(envs, "envelope", "Envelopes")' in src
    assert '(seq, "sequencer", "Sequencer")' in src


def test_an_absent_pad_or_adapter_is_simply_skipped():
    """No registry, or one with nothing listed: the frame runs the same
    order with no device step in it."""
    log: list[str] = []
    h = _host(log)
    h.devices = None
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    without = [s for s in ORDER
               if not s.startswith(("pad.", "router.pad", "router.claimed", "router.felt", "midi.",
                                    "hands.", "bridge.", "table.sinks"))]
    assert log == without
    log.clear()
    h.devices = devices.DeviceRegistry([])
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert log == without
    log.clear()
    h = _host(log, pad_on=False)                     # a pad polled for but not there:
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)       # its axis lanes go dark (router.pad),
    assert "pad.poll" in log and "router.pad" in log     # no stick writes anything
    assert "router.claimed" not in log and "router.felt" not in log


def test_a_raising_step_is_recorded_and_the_windows_still_draw():
    log: list[str] = []
    h = _host(log)
    h.router.modulate = _boom                        # where the LFOs step now (plan 28 N0)
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("step: RuntimeError: boom")
    assert "reg.apply" not in log                    # the pass stopped where it raised
    assert log[-2:] == ["render.draw", "panel.draw"]


def test_a_raising_adapter_is_a_note_that_survives_the_frame():
    """A MIDI or hands adapter that raises (hot-reloaded code with a bug)
    is recorded like a raising step — and stays recorded until a clean
    frame, rather than being wiped by the end-of-frame reset while the
    loop silently drops its input."""
    log: list[str] = []
    h = _host(log)
    midi, hands = h.devices.adapter("midi"), h.devices.adapter("hands")
    midi.poll = _boom
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("midi: RuntimeError: boom")
    assert h.devices.get("apc40").status == "error: RuntimeError: boom"   # and on its line
    assert "hands.poll" in log and "reg.apply" in log and "render.draw" in log
    midi.poll = lambda: None
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    assert h.reloader.runtime_error == ""            # …and a clean frame clears it
    assert h.devices.get("apc40").status == "connected"
    hands.poll = _boom
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("hands: RuntimeError: boom")
    assert "bridge.receive" in log and "reg.apply" in log    # the next device still fed
    hands.poll = lambda *a, **k: None
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    # a sink that raises after `reg.apply` (plan 27 B3): the toast, its
    # line, and the frame still draws
    h.devices.adapter("bridge").send_values = _boom
    log.clear()
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is False
    assert h.reloader.runtime_error.startswith("bridge: RuntimeError: boom")
    assert h.devices.get("bridge").status == "error: RuntimeError: boom"
    assert "view.integrate" in log and "render.draw" in log


def test_the_relative_writers_run_with_the_setters_and_move_the_base():
    """↑/↓ held and the pad's sticks are relative writers on the base
    (`nudge` / `scale`), and they run in the scene-setter block — after the
    key rows and the pad's rows (plan 27 B2: the camera job is the pad
    device's, `gamepad.steer`, right after its rows and before MIDI's),
    before the macros and before any source feeds."""
    g = app.glfw
    log: list[str] = []
    h = _host(log, held={g.KEY_UP}, stick=0.5)
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    i = log.index
    assert i("router.keys") < i("view.depth4.nudge") < i("pad.poll") < i("router.pad")
    assert i("router.pad") < i("camera.yaw.nudge") < i("camera.pitch.nudge")
    assert i("camera.pitch.nudge") < i("camera.zoom.scale") < i("midi.poll")
    assert i("midi.poll") < i("router.follow_macros")
    assert log.count("view.depth4.nudge") == 1     # the triggers rest, so no second ride
    # the right stick's X rides the three W planes' rates, after the zoom
    w = [f"rot.rate.{p}.nudge" for p in app.gamepad.W_PLANES]
    assert app.gamepad.W_PLANES == ("XW", "YW", "ZW")
    assert i("camera.zoom.scale") < i(w[0]) < i(w[1]) < i(w[2]) < i("midi.poll")


def test_a_routed_right_stick_leaves_the_w_rates_alone():
    """A route on `axis:RX` takes the stick off its default job."""
    log: list[str] = []
    h = _host(log, stick=0.5)
    h.router.claimed__returns = {app.gamepad.AX_RX}
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert not any(s.startswith("rot.rate.") for s in log)
    assert "camera.yaw.nudge" in log


def test_the_sticks_camera_job_reads_through_the_pads_feel():
    """With the pad's feel on (`router.felt` returns lanes), the camera job
    reads those, not the stick: a stick let go (0) still gliding home on
    the left X lane keeps orbiting; the right stick's Y, at rest, zooms nothing."""
    log: list[str] = []
    h = _host(log, stick=0.0)
    h.router.felt__returns = [0.9, 0.5, 0.5, 0.5, 0.0, 0.0]
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert "camera.yaw.nudge" in log
    assert "camera.pitch.nudge" not in log and "camera.zoom.scale" not in log
    log.clear()
    h.router.felt__returns = None                  # off: the stick as read
    app.frame(h, now=1.0, dt=1 / 60, fps=60.0)
    assert "camera.yaw.nudge" not in log


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
    """The one close list (audit P1) is the media channels and folder
    (plan 32), the registry — every device, last listed first, the pad
    included (plan 27 B1) — then the dream worker."""
    log: list[str] = []
    h = _host(log)
    assert h.adapters == (h.media, h.devices, None)
    app.close_all(SimpleNamespace(stop=lambda: log.append("audio")), *h.adapters)
    assert log == ["media.close", "bridge.close", "hands.close", "midi.close", "pad.close",
                   "audio"]
    assert all(d.io is None for d in h.devices) and h.pad is None


def _imports(path: Path) -> set[str]:
    """What a module's source imports, as written (`.x` for a relative one)."""
    import ast

    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            out |= {base} if node.module else {f"{base}{a.name}" for a in node.names}
    return out


def test_the_library_never_imports_config():
    """The library never imports config: app.main reads [library] path and
    hands the library its root and the machine home (plan 25)."""
    pkg = Path(app.__file__).parent
    lib = _imports(pkg / "library.py")
    assert not any(m.endswith("config") for m in lib), lib


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
    slots, ctrl = app._windows(app._overlay_allowed(cfg))
    render = slots[0].win
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
    slots, ctrl = app._windows(False, cfg, home)
    render = slots[0].win
    return g, render, ctrl


@pytest.mark.parametrize(("monitor", "said"), [
    ("left", "monitor = 'left' is not a screen index"),      # no number at all
    (7, "monitor = 7, but 2 screens are connected (0–1)"),    # a screen that is not there
    (None, "monitor = None is not a screen index"),
])
def test_a_config_screen_that_cannot_be_used_is_minus_one_and_one_note(
        monkeypatch, tmp_path, capsys, monitor, said):
    """Plan 16 WP7: `[output] monitor = "left"` stopped the launch in
    `_make_output`, and an index no screen has stayed in `Output.monitor`
    after placement had said it was treated as −1. Both are −1 from
    `_windows` on, for both windows' keys, and each is said once."""
    from hyperspace.params import Registry

    cfg = {"output": {"monitor": monitor, "control_monitor": monitor, "fullscreen": True}}
    g, render, _ = _open(monkeypatch, cfg, tmp_path)
    assert g.pos[render] == (16, 54)                           # the primary's default spot
    assert cfg["output"]["monitor"] == cfg["output"]["control_monitor"] == -1
    notes = cfg["notes"]
    assert len(notes) == 2 and said in notes[0] and f"control_{said}" in notes[1]
    out = app._make_output(render, Registry(), cfg)            # raised ValueError on "left"
    assert out.monitor == -1 and out.fullscreen is True
    assert cfg["notes"] == notes                               # nothing said twice
    # a cfg that never went through `_windows` or `config.load` does not raise either
    out = app._make_output(render, Registry(), {"output": {"monitor": monitor}})
    assert out.monitor == (7 if monitor == 7 else -1)
    # and what was good stays: an index a screen has, and −1
    for good in (1, 0, -1):
        cfg = {"output": {"monitor": good, "control_monitor": good}}
        g, render, _ = _open(monkeypatch, cfg, tmp_path)
        assert cfg == {"output": {"monitor": good, "control_monitor": good}}
        assert app._make_output(render, Registry(), cfg).monitor == good


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
    # …and a later output whose screen is not connected stays closed then
    # too (fork F9; review of #123), while one on a connected screen opens
    cfg = {"output": {"screens": [{}, {"monitor": 5}, {"monitor": 1}]}}
    g = _PlaceGlfw()
    monkeypatch.setattr(app, "glfw", g)
    slots, _ = app._windows(False, cfg, tmp_path)
    assert [s.opened for s in slots] == [True, False, True]
    assert slots[1].missing == "screen 5 is not connected"
    monkeypatch.setattr(placement, "place", place)

    # and with no home given nothing is read: the old one-argument call
    g = _PlaceGlfw()
    monkeypatch.setattr(app, "glfw", g)
    slots, ctrl = app._windows(False)
    render = slots[0].win
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


# ---- the exit: every window destroyed before glfw.terminate (the exit crash) ----

def test_both_exits_destroy_every_window_before_terminate(monkeypatch):
    """pyGLFW's terminate() frees the windows' callback closures before
    glfwTerminate destroys the windows, and destroying one pumps macOS's
    event queue into the others: an input event queued at quit then calls
    a freed closure (SIGSEGV, "Python closed unexpectedly"). Both exits
    destroy each window themselves first, `None` skipped, one that raises
    stopping none."""
    import inspect

    log: list[str] = []

    def destroy(w):
        log.append(f"destroy {w}")
        if w == "bad":
            raise RuntimeError("gone")

    monkeypatch.setattr(app, "glfw", SimpleNamespace(
        destroy_window=destroy, terminate=lambda: log.append("terminate"),
        make_context_current=lambda w: None))
    app._destroy_windows(["w2", None, "bad", "ctrl", "render"])
    assert log == ["destroy w2", "destroy bad", "destroy ctrl", "destroy render"]

    # ⌘R: the windows go after imgui's shutdown and before terminate and execv
    log.clear()
    monkeypatch.setattr(app.os, "execv", lambda *a: log.append("execv"))
    audio = SimpleNamespace(stop=lambda: log.append("audio"))
    impl = SimpleNamespace(shutdown=lambda: log.append("shutdown"))
    app._restart(audio, (), impl, "ctrl", windows=["ctrl", "render"])
    assert log == ["audio", "shutdown", "destroy ctrl", "destroy render", "terminate", "execv"]

    # main: the quit destroys every window (the later outputs', the control
    # window, output 1's) after imgui's shutdown, before terminate; the
    # restart is handed the same list
    src = inspect.getsource(app.main)
    tail = src[src.index("impl.shutdown()"):]
    assert tail.index("_destroy_windows(all_windows())") < tail.index("glfw.terminate()")
    assert "windows=all_windows()" in src
    assert "return [*(sl.win for sl in slots[1:]), ctrl_win, render_win]" in src


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


# ---- plan 21 WP3: the output list — windows, presenters, swaps ----
# Over fake window systems: a real second window cannot exist headless.
# The presenter's drawing is pinned on a real (standalone) GL context in
# tests/test_outputs.py; the share group itself only in a real launch.

class _OutGlfw(_PlaceGlfw):
    """_PlaceGlfw that also records each window's title and share."""

    def __init__(self, mons=None):
        super().__init__(mons)
        self.titles: dict = {}
        self.shares: dict = {}

    def create_window(self, w, h, title, mon, share):
        win = super().create_window(w, h, title, mon, share)
        self.titles[win], self.shares[win] = title, share
        return win


def _screens_cfg(*entries, **output):
    return {"output": {**output, "screens": [dict(e) for e in entries]}}


def test_one_window_per_listed_output(monkeypatch, tmp_path, capsys):
    """Three listed outputs, two screens: output 1 is created as before
    (MSAA, transparent only with overlay), then the controls, then each
    later output in output 1's share group — opaque, no MSAA, never
    minimised on focus loss — titled by its name, at its screen's default
    spot (cascaded when it would sit on output 1's). No list: two windows,
    as before."""
    from hyperspace import config

    g = _OutGlfw()
    monkeypatch.setattr(app, "glfw", g)
    cfg = _screens_cfg({"name": "glass", "monitor": 0}, {"name": "projector", "monitor": 1},
                       {"monitor": -1, "scene": False, "dim": 0.5}, monitor=0)
    slots, ctrl = app._windows(True, cfg, tmp_path)
    assert [s.n for s in slots] == [1, 2, 3] and all(s.opened for s in slots)
    out1, proj, third = slots
    assert (out1.win, ctrl, proj.win, third.win) == ("win1", "win2", "win3", "win4")
    assert out1.label == "output 1 (glass)" and third.label == "output 3"
    assert g.titles[proj.win] == "Hyperspace — projector" and g.titles["win4"] == (
        "Hyperspace — output 3")
    assert g.titles["win1"] == "Hyperspace"                         # as before
    assert g.shares == {"win1": None, "win2": "win1", "win3": "win1", "win4": "win1"}
    first, later = g.created[0], g.created[2:]
    assert first["SAMPLES"] == 4 and first["TRANSPARENT_FRAMEBUFFER"] is True   # overlay asked
    for hints in later:
        assert hints["SAMPLES"] == 0 and hints["TRANSPARENT_FRAMEBUFFER"] is False
        assert hints["AUTO_ICONIFY"] is False
    assert g.pos[proj.win] == (1728 + 16, 16)                       # the projector's default spot
    assert g.pos[third.win] == (16 + app.CASCADE, 54 + app.CASCADE)    # off output 1's spot
    # the launch switches ride on the slot: what draws each output's View
    assert third.switches == app.Switches(scene=False, dim=0.5) and proj.switches == app.Switches()
    assert "notes" not in cfg
    # no list: one slot (default switches, no name) and the control window, as before
    g = _OutGlfw()
    monkeypatch.setattr(app, "glfw", g)
    slots, ctrl = app._windows(False, {"output": dict(config.DEFAULTS["output"])}, tmp_path)
    assert len(slots) == 1 and slots[0].win == "win1" and ctrl == "win2" and len(g.created) == 2
    assert slots[0].switches == app.Switches() and slots[0].label == "output 1"


def test_a_later_output_whose_screen_is_absent_is_not_opened(monkeypatch, tmp_path, capsys):
    """Fork F9: output 1 always opens (an index no screen has is −1 with a
    note, today's rule); a later output with an index no screen has is not
    opened at all — said on stderr and the SYSTEM page — and keeps its
    number, so the outputs after it are still numbered by their place."""
    g = _OutGlfw()
    monkeypatch.setattr(app, "glfw", g)
    cfg = _screens_cfg({"monitor": 5}, {"name": "projector", "monitor": 2}, {"monitor": 1},
                       monitor=5)
    slots, _ = app._windows(False, cfg, tmp_path)
    one, two, three = slots
    assert one.opened and one.monitor == -1 and g.pos[one.win] == (16, 54)
    assert not two.opened and two.missing == "screen 2 is not connected"
    assert three.opened and three.n == 3 and len(g.created) == 3     # out 1, controls, out 3
    notes = cfg["notes"]
    assert "monitor = 5, but 2 screens are connected" in notes[0]
    assert notes[1] == ("config: output 2 (projector): monitor = 2, but 2 screens are "
                        "connected (0–1) — not opened")
    assert notes[1] in capsys.readouterr().err
    # monitor = −1 on a later output: a plain window where it was last
    placement = app.placement
    placement.save(tmp_path, None, [(100, 100, 800, 500), (900, 200, 640, 400)],
                   placement.screens(g))
    g = _OutGlfw()
    monkeypatch.setattr(app, "glfw", g)
    slots, _ = app._windows(False, _screens_cfg({}, {"monitor": -1}), tmp_path)
    assert g.pos[slots[1].win] == (900, 200) and g.size[slots[1].win] == (640, 400)
    # a window the system will not create: not opened, said, the launch goes on
    g = _OutGlfw()
    real = g.create_window
    g.create_window = lambda w, h, title, mon, share: (
        None if "two" in title else real(w, h, title, mon, share))
    monkeypatch.setattr(app, "glfw", g)
    cfg = _screens_cfg({}, {"name": "two"})
    slots, _ = app._windows(False, cfg, tmp_path)
    assert not slots[1].opened and "could not be created" in cfg["notes"][-1]


def test_the_exits_save_one_rect_per_output(monkeypatch, tmp_path):
    """windows.json's `render` gets one rect per output, in the config's
    order; an output not opened this run (or minimised) keeps its old
    entry, and an old one-entry file still loads for a two-output rig."""
    from hyperspace import placement
    from hyperspace.overlay import Output

    g = _OutGlfw()
    monkeypatch.setattr(app, "glfw", g)
    placement.save(tmp_path, (300, 90, 960, 900), [(40, 60, 800, 500)], placement.screens(g))
    slots, ctrl = app._windows(False, _screens_cfg({}, {"monitor": 1}, {"monitor": 7}),
                               tmp_path)
    assert g.pos[slots[0].win] == (40, 60) and g.size[slots[0].win] == (800, 500)
    assert g.pos[slots[1].win] == (1728 + 16, 16)          # no entry for it yet: its default spot

    class Backend:
        def window_rect(self, win):
            return (*g.pos[win], *g.size[win])

    outs = [Output(s.win, Backend()) if s.opened else None for s in slots]
    g.pos[slots[1].win] = (2000, 100)
    app._save_windows(tmp_path, slots[0].win, ctrl, outs[0], outs[1:])
    doc = placement.load(tmp_path)
    assert [r and r["x"] for r in doc["render"]] == [40, 2000, None]     # 3: never opened
    assert doc["render"][1]["screen"] == "Projector"
    # a third entry from an earlier run survives a run that did not open it
    placement.save(tmp_path, None, [None, None, (3000, 100, 640, 400)], placement.screens(g))
    app._save_windows(tmp_path, slots[0].win, ctrl, outs[0], outs[1:])
    assert [r and r["x"] for r in placement.load(tmp_path)["render"]] == [40, 2000, 3000]
    # minimised: its old entry
    g.iconified = {slots[1].win}
    g.pos[slots[1].win] = (-32000, -32000)
    app._save_windows(tmp_path, slots[0].win, ctrl, outs[0], outs[1:])
    assert placement.load(tmp_path)["render"][1]["x"] == 2000


class _SwapGlfw:
    """The calls `_open_presenters` and `_draw_render` make, logged."""

    def __init__(self, log, sizes=None):
        self.log, self.sizes = log, sizes or {}

    def make_context_current(self, win):
        self.log.append(f"current {win}")

    def swap_interval(self, n):
        self.log.append(f"interval {n}")

    def swap_buffers(self, win):
        self.log.append(f"swap {win}")

    def get_window_size(self, win):
        return self.sizes.get(win, (640, 400))

    def get_framebuffer_size(self, win):
        return self.sizes.get(win, (640, 400))


def _rig_slots(*names, presenter=None):
    from hyperspace.outputs import Slot

    out = []
    for k, name in enumerate(names):
        sl = Slot(k + 1, name=name, win=f"w{k + 1}")
        if k:
            sl.presenter = presenter(sl) if presenter else None
        out.append(sl)
    return out


def test_only_the_first_output_waits_for_the_screen(monkeypatch):
    """Fork F6: output 1's swap waits (interval 1, set where main makes its
    context), every later output's does not (interval 0), and each gets a
    presenter on its own context; one that will not build is said on its
    slot. Output 1's context is current after. In a frame the others swap
    first and output 1 last (it paces the loop)."""
    import inspect

    log: list[str] = []
    monkeypatch.setattr(app, "glfw", _SwapGlfw(log))
    slots = _rig_slots("glass", "projector", "third")
    slots.append(app.Slot(4, missing="screen 4 is not connected"))
    made = iter([object(), RuntimeError("no context")])

    def make():
        m = next(made)
        if isinstance(m, Exception):
            raise m
        return m

    destroyed: list = []
    app.glfw.destroy_window = destroyed.append
    notes: list[str] = []
    app._open_presenters(slots, make, notes)
    assert log == ["current w2", "interval 0", "current w3", "interval 0", "current w1",
                   "current w1"]
    assert isinstance(slots[1].presenter, app.Presenter) and slots[2].presenter is None
    # one that will not build is closed and counts as not opened (review of #123):
    # never drawn, it would show garbage and the watch would count it as live
    assert destroyed == ["w3"] and not slots[2].opened
    assert slots[2].missing == "its GL context would not open (presenter: RuntimeError: no context)"
    assert notes == [f"output: output 3 (third): {slots[2].missing} — not opened"]
    src = inspect.getsource(app.main)
    assert src.index("glfw.make_context_current(render_win)") < src.index(
        "glfw.swap_interval(1)") < src.index("_open_presenters(slots, ")
    assert src.index("glfw.swap_interval(0)") > src.index("glfw.make_context_current(ctrl_win)")


class _Ctx:
    """The renderer's moderngl context as `_draw_render` touches it."""

    def __init__(self, log):
        self.fbo = None
        self.viewport = None
        self.screen = SimpleNamespace(use=lambda: log.append("bind screen"), glo=0)


class _Renderer:
    """draw_outputs over the views: a Handoff per presenter view (or a
    raise for output 1's, recorded on its view as the renderer does)."""

    bg_alpha = 1.0

    def __init__(self, log, raise_first=None):
        self.log, self.raise_first, self.calls = log, raise_first, []

    def draw_outputs(self, s, w, h, dpr, views, t_now=None):
        from hyperspace.outputs import Handoff

        self.calls.append(views)
        self.log.append(f"draw {len(views)}")
        for v in views[1:]:
            v.handoff = Handoff(None, (640, 400), (0, 0, *v.size))
        if self.raise_first is not None:
            views[0].error, views[0].exc = "SCENE: boom", self.raise_first


class _Pres:
    def __init__(self, log, name, boom=False):
        self.log, self.name, self.boom = log, name, boom

    def present(self, ho, size):
        self.log.append(f"present {self.name}")
        if self.boom:
            raise RuntimeError("lost the context")


def test_one_output_draws_the_view_renderer_draw_would():
    """No list (or a list of one): `draw_outputs` with the one `View`
    `Renderer.draw` builds — the window's framebuffer, its whole
    viewport, the renderer's ground, the default switches — so the frame
    is today's; nothing is flushed and output 1 is swapped."""
    import inspect

    from hyperspace.render import Renderer

    log: list[str] = []
    g = _SwapGlfw(log, {"w1": (800, 500)})
    app_glfw, app.glfw = app.glfw, g
    try:
        r = _Renderer(log)
        r.bg_alpha = 0.4
        app._draw_render(r, _Ctx(log), object(), _rig_slots("x"),
                         flush=lambda: log.append("flush"))
    finally:
        app.glfw = app_glfw
    (v,) = r.calls[0]
    assert v.switches == app.Switches() and v.size == (800, 500) and v.bg_alpha == 0.4
    assert v.viewport == (0, 0, 800, 500) and v.presenter is None
    assert log == ["current w1", "bind screen", "draw 1", "current w1", "swap w1"]
    # Renderer.draw's own view, for comparison: the same fields from the bound framebuffer
    src = inspect.getsource(Renderer.draw)
    assert "View(Switches(), (vp[2], vp[3]), target=target," in src
    assert 'bg_alpha=getattr(self, "bg_alpha", 1.0), viewport=vp)' in src


def test_the_rendering_context_is_flushed_before_a_presenter():
    """§1, measured: without glFlush in output 1's context a presenter
    shows last frame's texture. The order: draw, flush, then each later
    output current → present → swap, then output 1 current and swapped."""
    log: list[str] = []
    g = _SwapGlfw(log, {"w1": (640, 400), "w2": (1920, 1080), "w3": (0, 0)})
    app_glfw, app.glfw = app.glfw, g
    try:
        slots = _rig_slots("glass", "projector", "min",
                           presenter=lambda sl: _Pres(log, sl.name))
        r = _Renderer(log)
        app._draw_render(r, _Ctx(log), object(), slots, flush=lambda: log.append("flush"))
    finally:
        app.glfw = app_glfw
    assert log == ["current w1", "bind screen", "draw 3", "flush",
                   "current w2", "present projector", "swap w2",
                   "current w3", "swap w3",                       # no framebuffer: nothing drawn
                   "current w1", "swap w1"]
    views = r.calls[0]
    assert [v.size for v in views] == [(640, 400), (1920, 1080), (0, 0)]
    assert views[1].presenter is slots[1].presenter and views[1].target is None
    assert slots[1].size == (1920, 1080)


def test_a_raising_presenter_does_not_stop_the_frame():
    """A presenter that raises (a lost context, an unplugged screen) sets
    its slot's error and warns the watch naming it; the outputs after it
    are presented and output 1 is swapped. What output 1's view caught is
    raised after the others were presented, as `Renderer.draw` raises it."""
    log: list[str] = []
    warned: list = []
    watch = SimpleNamespace(output_failed=lambda label, e: warned.append((label, str(e))),
                            stranded=lambda glo: warned.append(glo))
    g = _SwapGlfw(log)
    app_glfw, app.glfw = app.glfw, g
    try:
        slots = _rig_slots("glass", "projector", "third",
                           presenter=lambda sl: _Pres(log, sl.name, boom=sl.n == 2))
        app._draw_render(_Renderer(log), _Ctx(log), object(), slots, watch,
                         flush=lambda: log.append("flush"))
        assert slots[1].error == "present: RuntimeError: lost the context"
        assert slots[2].error == ""
        assert warned == [("output 2 (projector)", "lost the context")]
        assert log[-5:] == ["current w3", "present third", "swap w3", "current w1", "swap w1"]
        # recovers: the next good present clears the error
        slots[1].presenter.boom = False
        log.clear()
        app._draw_render(_Renderer(log), _Ctx(log), object(), slots, watch,
                         flush=lambda: None)
        assert slots[1].error == ""
        # output 1's pipeline raised: the others still get their picture, then it raises
        log.clear()
        boom = RuntimeError("scene")
        with pytest.raises(RuntimeError, match="scene"):
            app._draw_render(_Renderer(log, raise_first=boom), _Ctx(log), object(), slots,
                             watch, flush=lambda: None)
        assert "present projector" in log and "present third" in log
        assert log[-2:] == ["current w1", "swap w1"]
        # a stranded framebuffer is still the alarm
        ctx = _Ctx(log)
        ctx.fbo = SimpleNamespace(glo=7)
        app._draw_render(_Renderer(log), ctx, object(), slots, watch, flush=lambda: None)
        assert 7 in warned
    finally:
        app.glfw = app_glfw


def test_every_output_is_applied_and_polled_for_keys(fake):
    """The later outputs follow their config entry each frame (`apply`),
    keys are read from every output window (even while imgui types: an
    output window has no imgui), and the loop ends when any window is
    closed."""
    import inspect

    log: list[str] = []
    h = _host(log)
    h.outputs = [h.output, Stub("output2", log), Stub("output3", log)]
    app.frame(h, 0.0, 1 / 60, 60.0)
    assert log.index("output.apply") < log.index("output2.apply") < log.index("output3.apply")
    assert log.count("output.apply") == 1
    g = app.glfw
    keys = app.Keys("render", "ctrl", ["out2", "out3"])
    keys.typing = True
    fake.keys.add(("out3", g.KEY_B))
    assert keys.pressed(g.KEY_B)
    src = inspect.getsource(app.main)
    assert "any(glfw.window_should_close(sl.win) for sl in slots if sl.opened)" in src
    assert "Keys(render_win, ctrl_win, [sl.win for sl in later])" in src


def test_a_later_output_is_the_configs_and_never_overlay(monkeypatch):
    """Fork F10: a later output's screen and fullscreen come from its
    entry, with no params (output.* stay output 1's); overlay can never
    switch on there, and the registry is untouched."""
    from hyperspace.outputs import Slot
    from hyperspace.params import Registry

    monkeypatch.setattr(app, "glfw", _OutGlfw())
    reg = Registry()
    out = app._later_output(Slot(2, monitor=1, fullscreen=True, win="w2"))
    assert (out.monitor, out.fullscreen, out.allowed) == (1, True, False)
    out._set_overlay(True)
    assert out.mode == "fullscreen" and out.bg_alpha == 1.0
    assert list(reg) == []
    assert app._later_output(Slot(3, monitor=-1, win="w3")).mode == "window"


def test_the_switches_are_registered_from_the_configs_launch_values(monkeypatch, tmp_path):
    """Plan 21 WP4: main registers each opened output's switches before
    the library attaches (with the other rig settings), seeded from the
    slots `_windows` filled from the config; the panel gets the slots;
    and what a param writes is the `View` the next frame draws."""
    import inspect

    from hyperspace.overlay import register_switches
    from hyperspace.params import Registry

    src = inspect.getsource(app.main)
    assert src.index("_make_output(render_win, reg, cfg)") < src.index(
        "register_switches(reg, slots)") < src.index("library.attach(reg)")
    assert "panel.outputs = slots" in src
    g = _OutGlfw()
    monkeypatch.setattr(app, "glfw", g)
    cfg = _screens_cfg({"name": "glass"}, {"name": "projector", "monitor": 1, "scene": False,
                                           "through": True, "dim": 0.5})
    slots, _ = app._windows(False, cfg, tmp_path)
    reg = Registry()
    register_switches(reg, slots)
    assert reg["output.2.scene"].value is False and reg["output.2.through"].value is True
    assert reg["output.2.dim"].value == 0.5 and reg["output.1.dim"].value == 1.0
    reg["output.2.scene"].set(True)
    log: list[str] = []
    sizes = {"win1": (640, 400), "win3": (640, 400)}
    monkeypatch.setattr(app, "glfw", _SwapGlfw(log, sizes))
    for sl in slots[1:]:
        sl.presenter = _Pres(log, sl.name)
    r = _Renderer(log)
    app._draw_render(r, _Ctx(log), object(), slots, flush=lambda: None)
    assert r.calls[0][1].switches is slots[1].switches and r.calls[0][1].switches.scene


def test_the_media_exit_joins_everything_within_two_seconds(tmp_path):
    """Plan 32 review focus 3: the app's media close — every channel's
    source closed and its thread joined, the folder's timer stopped, the
    proxy worker and the pool let go — ends well inside 2 s, and leaves no
    media thread of the channels' or the folder's running."""
    import threading
    import time

    from test_media_channels import FakeOpener

    lib = tmp_path / "lib"
    media = app._open_media(str(lib), tmp_path / "home")
    assert media.folder.shared == lib / "media" and media.folder.local == tmp_path / "home" / "media"
    assert media.state.resolver.proxy_cache == tmp_path / "home" / "media-cache" / "proxies"
    op = FakeOpener(thread=True)
    media.state.opener = op
    media.state.resolver.path = lambda sid: Path("/x")
    for c in "abcd":
        media.state.assign(c, 0, f"local:{c}.png")
    media.poll(1 / 60, 0.0)
    assert op.opens == 4
    t = time.monotonic()
    media.close()
    assert time.monotonic() - t < 2.0
    assert op.closes == 4
    left = [th.name for th in threading.enumerate()
            if th.name.startswith(("media-fake-", "media-folder-watch"))]
    assert left == []
    other = app._open_media("", tmp_path / "home2")      # no [library] path: no shared folder
    assert other.folder.shared is None
    other.close()


def test_the_resolver_stamp_moves_when_a_download_lands(tmp_path):
    """Final review A-I1: the media resolver's stamp carries the scan's
    status, so a file whose size and mtime stay put while it goes from
    `fetching` to `ready` still reads as changed; `status` is the folder's."""
    from types import SimpleNamespace

    entry = SimpleNamespace(size=10, mtime=1.0, status="fetching")
    folder = SimpleNamespace(entry=lambda sid: entry, status=lambda sid: entry.status)
    r = app.MediaResolver(folder)
    was = r.stamp("shared:a.png")
    assert r.status("shared:a.png") == "fetching"
    entry.status = "ready"
    assert r.stamp("shared:a.png") != was and r.status("shared:a.png") == "ready"


_STUCK_EXIT = r"""
import sys, threading, time
from pathlib import Path
from types import SimpleNamespace

import av
from hyperspace import app
from hyperspace.media import pool, proxy
from hyperspace.media.video import VideoSource

home = Path(sys.argv[1])
never = threading.Event()
media = app._open_media(str(home / "lib"), home / "home")
# three stills mid-download: every pool worker stuck in a read
for _ in range(pool.WORKERS + 2):
    pool.submit(never.wait)
pool.submit_thumb(never.wait)
# a transcode running on the proxy worker
started = threading.Event()
def transcode(path, cache, cancel=None):
    started.set()
    never.wait()
proxy.make_proxy = transcode
clip = home / "clip.mp4"
clip.write_bytes(b"x")
proxy.submit(clip, home / "cache")
started.wait(2)
# a video on a channel stuck in av.open
av.open = lambda *a, **k: never.wait()
media.state.opener = lambda sid, r: VideoSource(sid, clip)
media.state.resolver.path = lambda sid: clip
media.state.assign("a", 0, "local:clip.mp4")
media.poll(1 / 60, 0.0)
time.sleep(0.1)
print("closing", time.time(), flush=True)
t = time.monotonic()
app.close_all(SimpleNamespace(stop=lambda: None), media)
print("closed", time.monotonic() - t, flush=True)
"""


def test_the_app_exits_within_two_seconds_with_reads_and_a_transcode_stuck(tmp_path):
    """Final review A-I1 / A-m1 / A-m4: with every pool worker stuck in a
    cloud file's read, a thumbnail job and a transcode running and a
    video stuck opening, the app's close path (`close_all`, one shared
    deadline) returns and the interpreter exits — no worker joined at
    exit — inside 2 s of the close starting."""
    import subprocess
    import sys
    import time

    script = tmp_path / "stuck_exit.py"
    script.write_text(_STUCK_EXIT)
    p = subprocess.Popen([sys.executable, str(script), str(tmp_path)], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, cwd=Path(__file__).parent.parent)
    try:
        out, err = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        pytest.fail(f"the process never exited: {out!r} {err[-2000:]!r}")
    ended = time.time()
    assert p.returncode == 0, err[-2000:]
    lines = dict(line.split(" ", 1) for line in out.splitlines() if " " in line)
    assert float(lines["closed"]) < 2.0, out
    assert ended - float(lines["closing"]) < 2.0, (ended, out)
