"""The OSC device (plan 27 B4): the plan's acceptance — **a device added by a
`[[devices]]` entry alone, with no edit to `app.py`**. A phone app's faders
(``/x``, ``/y``) are continuous sources under the role (``phone:x``), its
pads (``/hit``) triggers with a velocity delivered as rows; `lost` after a
silence and back on the next message.

Every message here is sent in-process by `pythonosc`'s own client to
127.0.0.1 on an ephemeral port the device bound itself (``port = 0``), so
no fixed port can be busy and nothing leaves the machine. Every home is a
scratch one; the routes come from a fixture preset loaded through it
(tests/fixtures/osc/phone-routes.json)."""

from __future__ import annotations

import ast
import math
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from conftest import boot_home
from pythonosc.udp_client import SimpleUDPClient

from hyperspace import config, devices, learn, osc, ui
from hyperspace.routing import Binding

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "osc" / "phone-routes.json"
PKG = Path(__file__).resolve().parents[1] / "hyperspace"

PHONE = """
[[devices]]
role = "phone"
kind = "osc"
host = "127.0.0.1"
port = 0
axes = ["/x", "/y"]
hits = ["/hit", "/pad"]
"""


def _show(tmp_path, devices_toml: str = PHONE, *, preset: bool = True):
    """The app's construction order over a scratch home whose config.toml
    lists `devices_toml` and nothing else (no [library]): the registry made
    from the config's entries alone, handed to the router and the Learn as
    app.main does, opened, the fixture preset loaded."""
    home = tmp_path / "home"
    (home / "presets").mkdir(parents=True)
    shutil.copyfile(FIXTURE, home / "presets" / FIXTURE.name)
    (home / "config.toml").write_text(devices_toml)
    cfg = config.load(home / "config.toml")
    app = boot_home(home)
    lrn = learn.Learn(app.reg, app.router.table, lane=app.router.lane)
    rig = devices.DeviceRegistry(
        config.devices(cfg),
        devices.Context(reg=app.reg, table=app.router.table, learn=lrn, home=home,
                        notes=cfg.setdefault("notes", [])),
        path=home / "config.toml")
    app.router.use(rig)
    lrn.devices = rig
    rig.open_all()
    if preset:
        assert app.presets.load(FIXTURE.stem) == []
        assert app.presets.notes == [] and app.router.table.dropped == []
    return NS(app=app, rig=rig, learn=lrn, cfg=cfg, home=home, now=[0.0])


def _client(s, role: str = "phone") -> SimpleUDPClient:
    return SimpleUDPClient("127.0.0.1", s.rig.get(role).io.port)


def _frame(s, dt: float = 1 / 60) -> None:
    """One frame's device slots and modulation pass, at the show's clock."""
    s.now[0] += dt
    s.rig.poll(dt, s.now[0], router=s.app.router, learn=s.learn)
    s.rig.feed(s.app.router)
    s.app.router.modulate(dt=dt)
    s.app.reg.apply()


def _until(s, cond, what: str, wait: float = 2.0) -> None:
    """Frames until `cond()` — a datagram on localhost lands within
    microseconds, but never inside the send call itself."""
    end = time.monotonic() + wait
    while True:
        _frame(s)
        if cond():
            return
        if time.monotonic() > end:
            raise AssertionError(f"no {what} within {wait} s")
        time.sleep(0.002)


# ------------------------------------------------------------ the acceptance

def test_an_osc_entry_alone_adds_the_device_and_a_fader_moves_a_routed_param(tmp_path):
    s = _show(tmp_path)
    reg, router = s.app.reg, s.app.router
    d = s.rig.get("phone")
    assert isinstance(d, osc.OscDevice) and d.kind == "osc"
    assert d.schemes == d.feeds == ("phone",) and d.rows == ("phone",)
    assert s.cfg["notes"] == []
    # the role is the scheme: the page offers it, a Learn can be armed for it
    assert router.schemes() == ("lane", "lfo", "phone")
    assert s.learn.wants() == ("desk", "phone")
    assert [p.address for p in d.sources] == ["phone:x", "phone:y", "phone:hit", "phone:pad"]
    assert [p.kind for p in d.sources] == ["value", "value", "trigger", "trigger"]
    assert all(p.velocity for p in d.sources if p.kind == "trigger")
    # nothing heard: `lost`, the routes dormant, the camera where the preset put it
    yaw0, pitch0 = reg["camera.yaw"].norm, reg["camera.pitch"].norm
    for _ in range(5):
        _frame(s)
    assert d.status == "lost" and router.feeds["phone"] is None
    assert not reg["camera.yaw"].modulated and not reg["camera.pitch"].modulated
    # published like the hands' lanes: names, labels, rests
    assert router.names["phone"] == {"x": 0, "y": 1}
    assert router.labels["phone"] == ["x", "y"] and router.rests["phone"] == [0.0, 0.0]
    # a message to /x moves the param routed from phone:x
    c = _client(s)
    c.send_message("/x", 0.8)
    _until(s, lambda: reg["camera.yaw"].modulated, "phone:x on camera.yaw")
    assert d.status == "connected"
    assert reg["camera.yaw"].eff_norm == pytest.approx(0.8, abs=1e-6)
    assert reg["camera.yaw"].norm == pytest.approx(yaw0)              # the base never moves
    # /y has not been sent: its lane reads NaN and its push row stays dormant
    assert math.isnan(router.feeds["phone"][1]) and not reg["camera.pitch"].modulated
    c.send_message("/y", 1.0)
    _until(s, lambda: reg["camera.pitch"].modulated, "phone:y on camera.pitch")
    assert reg["camera.pitch"].eff_norm == pytest.approx(min(1.0, pitch0 + 0.25), abs=1e-6)
    assert ui.device_lines(s.rig) == [
        f"phone  ·  osc  ·  connected  ·  4 sources  ·  UDP 127.0.0.1:{d.io.port}  ·  /y 1"]
    s.rig.apply([])                                   # the entry removed from config.toml
    assert d.io is None and d.status == "lost"
    router = s.app.router
    # gone from the router: no held value, and no longer offered on ROUTING
    for d in (router.feeds, router.labels, router.rests, router.names):
        assert "phone" not in d
    assert "phone" not in router.schemes()


def test_a_hit_with_velocity_fires_its_rows(tmp_path):
    """`/hit` is a trigger: its rows act through the table like a pad
    button's — a toggle flips on a press, `abs` lands the velocity (the
    message's first number), a velocity of 0 presses nothing."""
    s = _show(tmp_path)
    reg, table = s.app.reg, s.app.router.table
    table.add(Binding("phone:hit", "view.points", "toggle"))
    table.add(Binding("phone:hit", "view.bright", "abs"))
    points = reg["view.points"].value
    c = _client(s)
    c.send_message("/hit", 0.3)
    _until(s, lambda: reg["view.points"].value != points, "the toggle")
    assert reg["view.bright"].norm == pytest.approx(0.3, abs=1e-6)
    c.send_message("/hit", 0.0)                      # a release: nothing toggles, abs lands 0
    _until(s, lambda: reg["view.bright"].norm == 0.0, "the release")
    assert reg["view.points"].value != points
    c.send_message("/hit", [])                       # no argument: velocity 1
    _until(s, lambda: reg["view.points"].value == points, "the second press")
    assert reg["view.bright"].norm == pytest.approx(1.0)
    # an address the entry does not list is heard (connected) and does nothing
    c.send_message("/elsewhere", 1.0)
    _until(s, lambda: s.rig.get("phone").message.startswith("/elsewhere"), "the stray")
    assert reg["view.points"].value == points


def test_lost_after_the_timeout_and_back_on_the_next_message(tmp_path):
    s = _show(tmp_path, PHONE + "timeout = 2.0\n")
    reg, router = s.app.reg, s.app.router
    d = s.rig.get("phone")
    c = _client(s)
    c.send_message("/x", 0.6)
    _until(s, lambda: d.status == "connected", "the first message")
    s.now[0] += 1.9
    _frame(s)
    assert d.status == "connected"
    s.now[0] += 0.2                                  # 2.1 s of silence
    _frame(s)
    assert d.status == "lost"
    # held: a phone fader left alone keeps its place
    assert router.feeds["phone"][0] == pytest.approx(0.6, abs=1e-6)
    assert reg["camera.yaw"].eff_norm == pytest.approx(0.6, abs=1e-6)
    c.send_message("/x", 0.2)
    _until(s, lambda: d.status == "connected", "the next message")
    assert reg["camera.yaw"].eff_norm == pytest.approx(0.2, abs=1e-6)


def test_hold_false_lets_the_routes_go_in_a_silence(tmp_path):
    s = _show(tmp_path, PHONE + "timeout = 1.0\nhold = false\n")
    reg, router = s.app.reg, s.app.router
    d = s.rig.get("phone")
    c = _client(s)
    c.send_message("/x", 0.6)
    _until(s, lambda: reg["camera.yaw"].modulated, "the route")
    s.now[0] += 1.5
    _frame(s)
    assert d.status == "lost" and router.feeds["phone"] is None
    assert not reg["camera.yaw"].modulated
    c.send_message("/y", 0.4)                        # back — /x not resent: still dormant
    _until(s, lambda: d.status == "connected", "the next message")
    _frame(s)
    assert math.isnan(router.feeds["phone"][0]) and not reg["camera.yaw"].modulated


def test_a_learn_armed_for_the_role_takes_a_hit_as_a_row_and_a_fader_as_a_route(tmp_path):
    s = _show(tmp_path)
    reg, table, lrn = s.app.reg, s.app.router.table, s.learn
    c = _client(s)
    points = reg["view.points"].value
    lrn.arm("view.points", "phone")
    c.send_message("/pad", 1.0)
    _until(s, lambda: lrn.learning is None, "the hit learn")
    (row,) = [b for b in table.bindings if b.source == "phone:pad"]
    assert (row.target, row.op) == ("view.points", "toggle")
    assert reg["view.points"].value == points        # the learning press acts on nothing
    assert "phone:pad" in (s.home / "bindings.json").read_text()     # the session's, as a pad's
    c.send_message("/pad", 1.0)
    _until(s, lambda: reg["view.points"].value != points, "the learned row")
    # a fader moved from its rest becomes a route
    lrn.arm("view.bright", "phone")
    c.send_message("/x", 0.05)                       # not far enough from its rest
    _until(s, lambda: s.rig.get("phone").message.startswith("/x"), "the nudge")
    assert lrn.learning == "view.bright"
    c.send_message("/x", 0.9)
    _until(s, lambda: lrn.learning is None, "the fader learn")
    assert table.owner("view.bright").source == "phone:x"


# ------------------------------------------------------------ errors and gates

def test_a_busy_port_is_an_error_line_and_comes_up_when_it_frees(tmp_path):
    """Another program on the port: `error: OSError: …`, one note, retried
    on the registry's schedule — and up, with no relaunch, once it frees.
    The port is one this test holds itself (ephemeral), so nothing else on
    the machine can make the test pass or fail."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("127.0.0.1", 0))
    port = blocker.getsockname()[1]
    try:
        clock = [0.0]
        notes: list[str] = []
        entry = {"role": "phone", "kind": "osc", "enabled": True, "host": "127.0.0.1",
                 "port": port, "axes": ["/x"]}
        rig = devices.DeviceRegistry([entry], clock=lambda: clock[0], notes=notes)
        rig.open_all()
        d = rig.get("phone")
        assert d.status.startswith("error: OSError: ") and f":{port}" in d.status
        assert len(notes) == 1 and notes[0].startswith("osc: ")
    finally:
        blocker.close()
    clock[0] = devices.RETRY_S
    rig.poll(1 / 60, 0.0)
    assert d.status == "lost" and d.io.port == port
    rig.close()


@pytest.mark.parametrize(("entry", "why"), [
    ({"role": "cc"}, "role 'cc' is a scheme the app already reads"),
    ({"role": "lfo"}, "role 'lfo' is a scheme the app already reads"),
    ({"axes": ["x"]}, "axes: 'x' is not an OSC address"),
    ({"axes": ["/x", "/x"]}, "axes: /x is listed twice"),
    ({"axes": ["/x"], "hits": ["/x"]}, "/x is both an axis and a hit"),
    ({"rest": "low"}, "rest for /x = 'low' is not a number"),
    ({"range": [1, 1]}, "range = [1, 1] is not [low, high]"),
    ({"port": 70000}, "port = 70000 is not a UDP port"),
    ({"timeout": "5"}, "timeout = '5' is not a positive number of seconds"),
    ({"timeout": 0}, "timeout = 0 is not a positive number of seconds"),
])
def test_a_bad_entry_is_an_error_line_never_a_crash(entry, why):
    full = {"role": "phone", "kind": "osc", "enabled": True, "host": "127.0.0.1", "port": 0,
            "axes": ["/x"], **entry}
    rig = devices.DeviceRegistry([full], notes=[])
    rig.open_all()
    (d,) = list(rig)
    assert d.status.startswith("error: ValueError: ") and why in d.status, d.status
    rig.close()


def test_an_osc_role_on_a_fed_scheme_is_refused_and_an_off_one_still_lists_its_scheme():
    """The role is the scheme, so `make` checks it like any fed scheme: an
    OSC device called `axis` after the pad is refused (B1's rule). An off
    entry still lists its scheme and its hit rows, so a preset row naming
    it waits rather than being refused."""
    entries = [{"role": "axis", "kind": "gamepad", "enabled": True},
               {"role": "axis2", "kind": "osc", "enabled": True}]
    assert isinstance(devices.make_all(entries)[1], osc.OscDevice)
    entries = [{"role": "pad", "kind": "gamepad", "enabled": True},
               {"role": "axis", "kind": "osc", "enabled": True}]
    refused = devices.make_all(entries)[1]
    assert isinstance(refused, devices.RefusedDevice)
    assert refused.status == "error: feeds 'axis', which pad already feeds — not opened"
    off = devices.DeviceRegistry([{"role": "phone", "kind": "osc", "enabled": False,
                                   "hits": ["/hit"]}])
    assert off.continuous_schemes() == ("lane", "lfo", "phone")
    assert off.row_schemes() == ("phone",) and off.wants() == ("phone",)
    no_hits = devices.DeviceRegistry([{"role": "phone", "kind": "osc", "enabled": True}])
    assert no_hits.row_schemes() == ()               # no hits: a button row on it is refused


OFF_SCRIPT = """
import sys
from hyperspace import devices
rig = devices.DeviceRegistry([{"role": "phone", "kind": "osc", "enabled": False}])
rig.open_all()
print(rig.get("phone").status, "pythonosc" in sys.modules)
"""


def test_an_off_osc_entry_imports_no_osc_library():
    """`pythonosc` is imported only when an entry opens a server (the
    import boundary itself — importing `app` imports neither `hyperspace.osc`
    nor `pythonosc` — is tests/test_app_boundary.py's)."""
    out = subprocess.run([sys.executable, "-c", OFF_SCRIPT], capture_output=True, text=True,
                         check=False, cwd=str(Path(__file__).parents[1]), timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "off False"


def _names_osc(tree) -> list[str]:
    """Where a module's *code* (not its comments or docstrings) names the
    OSC device: an import of `osc`, the class, or the kind string — as the
    enclosing top-level function's name ("" at module level)."""
    out: list[str] = []
    for top in tree.body:
        where = top.name if isinstance(top, ast.FunctionDef | ast.ClassDef) else ""
        docs = {id(n.value) for n in ast.walk(top)
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
        for n in ast.walk(top):
            hit = (isinstance(n, ast.ImportFrom)
                   and (n.module in ("osc", "hyperspace.osc")
                        or (n.module in (None, "hyperspace") and any(a.name == "osc"
                                                                     for a in n.names)))
                   or isinstance(n, ast.Import) and any(a.name == "hyperspace.osc"
                                                        for a in n.names)
                   or isinstance(n, ast.Name) and n.id == "OscDevice"
                   or isinstance(n, ast.Constant) and n.value == "osc" and id(n) not in docs)
            if hit:
                out.append(where)
    return out


def test_only_osc_py_and_the_kind_table_name_the_osc_device():
    """The plan's acceptance in code: the OSC device is named by `osc.py`
    and the registry's kind table (`devices.kinds`) — and by the hot
    reloader's watch list, which lists every module — and nowhere else;
    `app.py` not at all."""
    naming = {str(p.relative_to(PKG)): _names_osc(ast.parse(p.read_text()))
              for p in PKG.rglob("*.py")}
    naming = {k: v for k, v in naming.items() if v}
    assert sorted(naming) == ["devices.py", "hotreload.py", "osc.py"]
    assert set(naming["devices.py"]) == {"kinds"}
    assert set(naming["hotreload.py"]) == {""}                   # MODULES
    assert re.search(r"\bosc\b", (PKG / "app.py").read_text(), re.IGNORECASE) is None


def test_the_osc_value_mapping():
    lay = osc.Layout({"axes": ["/acc"], "range": [-10, 10], "rest": {"/acc": 0.5}})
    assert lay.rests == [0.5] and lay.names == ["acc"]
    assert [lay.norm(v) for v in (-10, 0, 10, 99)] == [0.0, 0.5, 1.0, 1.0]
    assert osc._number(["a", True, 3, 0.5]) == 3.0 and osc._number(["a"]) is None
    assert osc._number([float("nan"), 0.25]) == 0.25


def test_a_session_hit_row_waits_while_its_device_is_not_listed(tmp_path):
    """Decision 11 for a hit row: `bindings.json` keeps a ``phone:hit``
    toggle row — loaded and written back unchanged — while no phone is
    listed (`Bindings.load` runs only the referee). The one refusal tied
    to the device's absence is interactive: re-enabling a disabled hit
    row while no phone is listed is refused (`_check`), and accepted once
    the registry lists the phone."""
    from hyperspace import routing

    path = tmp_path / "bindings.json"
    table = routing.Bindings.load(path, legacy_midi=None)
    on = Binding("phone:hit", "view.points", "toggle")
    off = Binding("phone:pad", "view.lines", "fire", enabled=False)
    table.bindings += [on, off]
    table.write()
    again = routing.Bindings.load(path, legacy_midi=None)
    rows = {(b.source, b.target, b.op, b.enabled) for b in again.bindings
            if b.source.startswith("phone:")}
    assert rows == {("phone:hit", "view.points", "toggle", True),
                    ("phone:pad", "view.lines", "fire", False)}
    again.write()
    assert "phone:hit" in path.read_text() and "phone:pad" in path.read_text()
    (row,) = [b for b in again.bindings if b.source == "phone:pad"]
    with pytest.raises(ValueError, match="'fire' is not an op for a phone source"):
        again.enable(row)
    rig = devices.DeviceRegistry([{"role": "phone", "kind": "osc", "enabled": False,
                                   "hits": ["/hit", "/pad"]}])
    again.row_schemes = (*routing.ROW_SCHEMES, *rig.row_schemes())    # Router.use does this
    again.enable(row)
    assert row.enabled
