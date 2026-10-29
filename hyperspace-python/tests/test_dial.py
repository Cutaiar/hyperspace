"""The sticks as dials (gamepad.dial, plan 28): a stick's angle picks
one of eight sectors clockwise from straight up, its distance from centre
is how far that sector's `axis` lane reads — petal (hard sectors, a sticky
border) or blend (neighbours crossfade), the preset's (`pad.dial.*`) — and
a route on a dial lane plays like any other `axis` route, taking its whole
stick off the camera job. The pad node on GRAPH draws the dials."""

import json
import math

import pytest
from conftest import seed
from test_pad_learn import ScriptedPad, rig  # noqa: F401 — the fixture, re-exported
from test_routing import rig as full_rig

import hyperspace.gamepad as gp
from hyperspace import app
from hyperspace.library import Library
from hyperspace.params import Registry
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Bindings, Router


def at(deg: float, r: float = 1.0) -> tuple[float, float]:
    """(x, y) — right and up — of a stick `deg` clockwise from straight up."""
    t = math.radians(deg)
    return r * math.sin(t), r * math.cos(t)


def lane(name: str) -> int:
    return gp.LANES.index(name)


# ---- the clock ----

def test_at_rest_every_lane_is_zero():
    for mode in gp.DIAL_MODES:
        assert gp.dial(0.0, 0.0, mode) == ([0.0] * gp.DIAL, None)
        assert gp.dial(*at(30, gp.DEADZONE * 0.9), mode) == ([0.0] * gp.DIAL, None)


def test_sectors_run_clockwise_from_straight_up():
    for k, deg in enumerate(range(0, 360, 45)):
        vals, sector = gp.dial(*at(deg), "petal")
        assert sector == k and vals[k] == pytest.approx(1.0), gp.COMPASS[k]
    assert gp.COMPASS[gp.dial(1.0, 0.0)[1]] == "E"         # right is three o'clock


def test_the_radius_runs_zero_to_one_past_the_deadzone_and_stops_at_the_rim():
    half = gp.DEADZONE + 0.5 * (1 - gp.DEADZONE)
    assert gp.dial(*at(0, half))[0][0] == pytest.approx(0.5)
    assert gp.dial(1.0, 1.0)[0][1] == pytest.approx(1.0)    # a square gate's corner


def test_petal_gives_the_whole_push_to_one_sector():
    vals, sector = gp.dial(*at(60, 0.8), "petal")
    assert sector == 1 and [v > 0 for v in vals].count(True) == 1


def test_a_petal_border_is_sticky():
    """22.5° is the border between N and NE: held on N, a stick a little
    past it stays N, one well past it is NE — and NE is as sticky back."""
    assert gp.dial(*at(25), "petal", held=0)[1] == 0
    assert gp.dial(*at(25), "petal", held=None)[1] == 1
    assert gp.dial(*at(35), "petal", held=0)[1] == 1
    assert gp.dial(*at(20), "petal", held=1)[1] == 1
    assert gp.dial(*at(-25), "petal", held=0)[1] == 0      # and across the wrap
    assert gp.dial(*at(-35), "petal", held=0)[1] == 7


def test_blend_crossfades_neighbours_and_sums_to_the_radius():
    vals, _ = gp.dial(*at(0), "blend")
    assert vals[0] == pytest.approx(1.0) and sum(vals) == pytest.approx(1.0)
    vals, _ = gp.dial(*at(22.5), "blend")                    # halfway N → NE
    assert vals[0] == pytest.approx(0.5) and vals[1] == pytest.approx(0.5)
    vals, _ = gp.dial(*at(-11.25, 0.6), "blend")             # a quarter into NW
    assert vals[0] > vals[7] > 0 and sum(vals) == pytest.approx(gp.dial(*at(0, 0.6))[0][0])


# ---- the pad ----

def test_the_dial_lanes_follow_the_axes():
    pad = ScriptedPad()
    pad.frame(axes=[0.0, -1.0, 1.0, 0.0, -1.0, -1.0])      # left up, right to the right
    lanes = pad.lanes()
    assert len(lanes) == len(gp.LANES) == len(gp.LANE_RESTS) == len(gp.LANE_LABELS)
    assert lanes[lane("L.N")] == pytest.approx(1.0) and lanes[lane("R.E")] == pytest.approx(1.0)
    assert sum(lanes[6:]) == pytest.approx(2.0)
    pad.frame()
    assert pad.lanes()[6:] == [0.0] * len(gp.DIAL_LANES)


def test_the_mode_is_per_stick():
    pad = ScriptedPad()
    pad.dial_modes = {"L": "blend", "R": "petal"}
    x, y = at(22.5)
    pad.frame(axes=[x, -y, x, -y, -1.0, -1.0])
    lanes = pad.lanes()
    assert lanes[lane("L.N")] == pytest.approx(0.5)          # blend: shared
    assert {lanes[lane("R.N")], lanes[lane("R.NE")]} == {0.0, 1.0}   # petal: one


def test_a_dial_lane_claims_its_whole_stick():
    assert gp.claims({lane("L.SW")}) == {gp.AX_LX, gp.AX_LY}
    assert gp.claims({lane("R.N"), gp.AX_LT}) == {gp.AX_RX, gp.AX_RY, gp.AX_LT}
    assert gp.dialed({lane("R.N"), gp.AX_LX}) == {"R"}


# ---- routes and learn ----

def test_a_dial_route_pushes_its_param_from_the_base(rig):  # noqa: F811
    pad, r = ScriptedPad(), rig.router
    gp.publish(r)                    # the pad's lane names (the pad device does it first)
    rig.table.add(Binding("axis:L.E", "view.inst_amp", "push", 1.0))
    assert gp.claims(r.claimed("axis")) == {gp.AX_LX, gp.AX_LY}
    assert r.describe(rig.table.owner("view.inst_amp")).startswith("left dial E")
    amp = rig.reg["view.inst_amp"]
    base = amp.value
    pad.frame()
    r.pad(pad)
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(base)                  # at rest: the base
    pad.frame(axes=[0.5 + 0.5 * gp.DEADZONE, 0.0, 0.0, 0.0, -1.0, -1.0])   # halfway right
    r.pad(pad)
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(base + 0.5 * (amp.hi - amp.lo))


def test_a_dialed_stick_learns_the_sector_it_points_into(rig):  # noqa: F811
    pad, lrn = ScriptedPad(), rig.learn
    pad.frame()
    lrn.arm("view.inst_amp", "pad")
    x, y = at(135)
    pad.frame(axes=[x, -y, 0.0, 0.0, -1.0, -1.0])            # down-right
    gp.learn_from(pad, lrn, dials=lambda: {"L"})
    assert [(b.source, b.target) for b in rig.table.routes()] == [("axis:L.SE", "view.inst_amp")]


def test_a_stick_that_is_no_dial_still_learns_its_axis(rig):  # noqa: F811
    pad, lrn = ScriptedPad(), rig.learn
    pad.frame()
    lrn.arm("view.inst_amp", "pad")
    pad.frame(axes=[1.0, 0.0, 0.0, 0.0, -1.0, -1.0])
    gp.learn_from(pad, lrn)
    assert [b.source for b in rig.table.routes()] == ["axis:LX"]


def test_the_dial_preset_fills_both_clocks(tmp_path):
    seed(tmp_path)                        # the corpus: DIAL among the shipped presets
    r = full_rig(tmp_path=tmp_path, full=True)
    router = Router(r.reg, Bindings())
    assert Presets(r.lib, r.reg, router).load("DIAL") == []
    assert router.table.dropped == []
    dialed = {b.source for b in router.table.routes() if b.scheme == "axis"}
    assert dialed == {f"axis:{n}" for n in gp.DIAL_LANES}
    assert router.table.owner("fx.wobble.speed").source == "axis:L.N"
    assert router.table.owner("fx.wobble.amount").source == "axis:L.NE"


# ---- the readings: the preset's ----

def test_the_readings_are_the_presets_and_swap():
    """`pad.dial.left` / `.right` are the preset's (group `pad`, persisted,
    performance): they write the one dict the pads read, and the swap
    trades them through the params, so it is an edit like any other."""
    from hyperspace.params import part_of

    reg, modes = Registry(), dict(gp.DIAL_DEFAULT)
    app._register_dial(reg, modes)
    left = reg["pad.dial.left"]
    assert left.persist and part_of(left) == "performance" and not left.modulatable
    left.set(1)
    assert modes["L"] == "blend"
    reg["pad.dial.swap"].fire()
    assert modes == {"L": "blend", "R": "blend"}
    reg["pad.dial.right"].set(0)
    reg["pad.dial.swap"].fire()
    assert modes == {"L": "petal", "R": "blend"}
    assert "pad.dial.left" in reg.snapshot(part="performance")
    assert "pad.dial.left" not in reg.snapshot(part="session")


def test_config_picks_where_each_stick_starts():
    """The gamepad entry's `dial_left` / `dial_right` (plan 27's
    [[devices]]; the old [gamepad] table's keys translate) are the launch
    readings — the fresh values a preset naming none gets; a value that is
    no reading leaves the default. A pad opened alone still seeds itself."""
    from hyperspace import config, devices

    entry = {"role": "pad", "kind": "gamepad", **config._kind_defaults("gamepad"),
             "dial_left": "blend", "dial_right": "nonsense"}
    assert app._dial_launch({"devices": [entry]}) == {"L": "blend", "R": "blend"}
    assert app._dial_launch({}) == gp.DIAL_DEFAULT
    dev = devices.make(entry)
    dev.open()
    try:
        assert dev.io.dial_modes == {"L": "blend", "R": "blend"}
    finally:
        dev.close()
    assert config._kind_defaults("gamepad")["dial_left"] == "petal"


def test_every_pad_reads_the_registrys_readings():
    """In the app every pad reads the one dict the params write
    (`devices.Context.dial_modes`): a pad that opens later, or again after
    a config edit, reads what the preset says — its entry's keys do not
    put it back."""
    from hyperspace import config, devices

    modes = {"L": "blend", "R": "petal"}
    reg = Registry()
    app._register_dial(reg, modes)
    entry = {"role": "pad", "kind": "gamepad", **config._kind_defaults("gamepad")}
    ctx = devices.Context(dial_modes=modes)
    first = devices.make(entry, ctx)
    first.open()
    reg["pad.dial.right"].set(1)
    second = devices.make(entry, ctx)
    second.open()
    try:
        assert first.io.dial_modes is modes and second.io.dial_modes is modes
        assert second.io.dial_modes == {"L": "blend", "R": "blend"}
    finally:
        first.close()
        second.close()


def _preset_rig(tmp_path, modes):
    """A registry with the readings registered before attach, as app.main
    has them — so the launch readings are the fresh values — a router and
    the presets, over a throwaway home."""
    r = full_rig()
    lib = Library(tmp_path)
    app._register_dial(r.reg, modes)
    lib.attach(r.reg)
    router = Router(r.reg, Bindings())
    return r.reg, router, Presets(lib, r.reg, router)


def test_a_preset_keeps_its_readings(tmp_path):
    """Saved with the preset and put back by its load, whatever was set in
    between; a preset that names none gets the launch readings."""
    modes = dict(gp.DIAL_DEFAULT)
    reg, _, presets = _preset_rig(tmp_path / "home", modes)
    plain = presets.save_as("PLAIN")                   # the launch readings
    reg["pad.dial.left"].set(1)
    reg["pad.dial.right"].set(0)
    path = presets.save_as("FLIPPED")
    values = json.loads(path.read_text())["values"]
    assert values["pad.dial.left"] == 1 and values["pad.dial.right"] == 0
    reg["pad.dial.swap"].fire()
    assert presets.load("FLIPPED") == []
    assert modes == {"L": "blend", "R": "petal"}
    assert presets.load("PLAIN") == [] and modes == gp.DIAL_DEFAULT
    # a file that names no reading: the launch readings, not the last preset's
    doc = json.loads(plain.read_text())
    for k in ("pad.dial.left", "pad.dial.right"):
        doc["values"].pop(k)
    (plain.parent / "bare.json").write_text(json.dumps({**doc, "name": "BARE"}))
    presets.load("FLIPPED")
    assert presets.load("BARE") == [] and modes == gp.DIAL_DEFAULT


def test_a_reading_is_one_undo_step(tmp_path):
    """Picking a reading, or the swap, is a step undo takes back."""
    from test_undo import boot, frames, settle

    r = boot(tmp_path / "home")
    modes = dict(gp.DIAL_DEFAULT)
    app._register_dial(r.reg, modes)
    frames(r, 2)
    settle(r)
    n = len(r.undo.stack)
    r.reg["pad.dial.swap"].fire()
    settle(r)
    assert modes == {"L": "blend", "R": "petal"} and len(r.undo.stack) == n + 1
    assert r.undo.undo() is True
    assert modes == gp.DIAL_DEFAULT


# ---- the panel: the pad node on GRAPH ----

def _side(panel, nid="device:pad"):
    from imgui_bundle import imgui
    from test_ui_shell import frame

    from hyperspace import graphview, ui_graph
    frame(panel, "graph")
    st = ui_graph._state(panel)
    imgui.new_frame()
    imgui.begin("side")
    ui_graph._side(panel, st, st["view"], ("node", graphview.VNode(nid, "device", nid[7:])))
    imgui.end()
    imgui.end_frame()


def test_the_pad_nodes_details_draw_both_clocks(tmp_path, monkeypatch):
    """The pad node's details draw the pad, then both sticks' faces and
    their readings; another device's do not. SYSTEM keeps only the feel."""
    from test_ui_shell import build_rig, frame

    from hyperspace.ui import Panel
    faces, rows = [], []
    draw, row = Panel._dial, Panel._row
    monkeypatch.setattr(Panel, "_dial", lambda self, vals, names, *a:
                        faces.append((list(vals), names)) or draw(self, vals, names, *a))
    monkeypatch.setattr(Panel, "_row", lambda self, pid, *a, **kw:
                        rows.append(pid) or row(self, pid, *a, **kw))
    with build_rig(tmp_path) as r:
        seed(r.lib.home)
        pad = ScriptedPad()
        r.panel.pad = pad
        app._register_dial(r.reg, pad.dial_modes)
        assert [k for k in Presets(r.lib, r.reg, r.router).load("DIAL")
                if not k.startswith(("env.", "seq."))] == []  # (plan 36 T3: the `/7`'s envelope ids, this rig has none)
        x, y = at(100)
        pad.frame(axes=[x, -y, -x, y, -1.0, -1.0])
        _side(r.panel)
        left, right = faces[-2:]
        assert left[1][0] == "Wobble speed" and right[1][0] == "4D depth"
        assert left[0][2] > 0 and right[0][6] > 0   # 100°: E on the left, W on the right
        assert {"pad.dial.left", "pad.dial.right"} <= set(rows)
        faces.clear()
        _side(r.panel, "device:apc40")
        assert faces == []
        rows.clear()
        frame(r.panel, "system")
        assert "desk.pad.feel" in rows and not any(p.startswith("pad.dial") for p in rows)
        assert faces == []


def test_picking_a_reading_on_the_pad_node_sets_it(tmp_path, monkeypatch):
    """The readings are enums: the pad node offers their choices, and
    picking one sets it (an enum row is a combo, never a slider)."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig

    pick = {"pad.dial.left": 1, "pad.dial.right": 0}

    def chosen(label, cur, *a, **kw):
        pid = label.rpartition("##")[2]
        return (pid in pick, pick.get(pid, cur))

    monkeypatch.setattr(imgui, "combo", chosen)
    with build_rig(tmp_path) as r:
        pad = ScriptedPad()
        r.panel.pad = pad
        app._register_dial(r.reg, pad.dial_modes)
        _side(r.panel)
        assert pad.dial_modes == {"L": "blend", "R": "petal"}


def test_the_stick_feel_is_picked_on_system(tmp_path, monkeypatch):
    """The stick feel stays the session's, on SYSTEM: an enum, so a combo."""
    from imgui_bundle import imgui
    from test_ui_shell import build_rig, frame

    monkeypatch.setattr(imgui, "combo", lambda label, cur, *a, **kw: (
        label.endswith("##desk.pad.feel"), 2 if label.endswith("##desk.pad.feel") else cur))
    with build_rig(tmp_path) as r:
        frame(r.panel, "system")
        assert r.reg["desk.pad.feel"].text() == "spring"


def test_the_pad_picture_shows_a_dialed_stick(tmp_path):
    """On the pad's picture a stick a route reads as a dial says so: its
    X and Y read "Left dial · petal" instead of the orbit they no longer
    drive; the other stick keeps its camera job's words."""
    from test_ui_shell import build_rig

    from hyperspace import ui_pad
    with build_rig(tmp_path) as r:
        app._register_dial(r.reg, dict(gp.DIAL_DEFAULT))
        r.router.table.add(Binding("axis:L.E", "view.inst_amp", "push", 1.0))
        _side(r.panel)
        lx, rx = gp.control("axis:LX"), gp.control("axis:RX")
        assert ui_pad.says(r.panel, lx, None) == "Left dial · petal"
        assert ui_pad.says(r.panel, rx, None) == ui_pad.BUILT_IN["axis:RX"]
        assert "read as a dial (petal)" in ui_pad.label(r.panel, lx, None)
        r.reg["pad.dial.left"].set(1)
        assert ui_pad.says(r.panel, lx, None) == "Left dial · blend"
