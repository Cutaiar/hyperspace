"""The Kinect's side pane (plan 29, row 1170): GRAPH's selected device node
drawn at the pane's narrowest and widest, every control in it with an id,
the tilt sent only on a deliberate action, a control the device cannot use
shown disabled with its word. Over a stand-in device: no hardware."""

from __future__ import annotations

import math
from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig
from ui_driver import Driver

from hyperspace import graphview, kinect, ui, ui_graph, ui_kinect

ALL = {"kinect.tilt", "kinect.tilt.go", "kinect.tilt.level", "kinect.led", "kinect.ir",
       "kinect.video.off", "kinect.video.color", "kinect.video.ir", "kinect.auto_exposure",
       "kinect.white_balance", "kinect.flicker", "kinect.exposure", "kinect.restart",
       "kinect.reconnect", "kinect.near", "kinect.far", "kinect.centre", "kinect.step",
       "kinect.mirror", "kinect.radar"}
OPEN = {k: "" for k in ("tilt", "led", "ir", "video", "restart", "reconnect", "auto_exposure",
                        "white_balance", "flicker")}


def radar_profile() -> tuple:
    """A radar profile: a person's width of readings at 2 m, a wall at 4 m, gaps."""
    p = [0] * kinect.RADAR_COLS
    for c in range(30, 42):
        p[c] = 2000
    for c in range(60, 80):
        p[c] = 4000
    p[5] = 9000                                   # past the radar's range
    return tuple(p)


class Dev:
    """What the pane reads of a KinectDevice."""

    role, kind = "room", "kinect"

    def __init__(self, **tele):
        base = {"live": True, "model": "1414", "depth_fps": 30.0, "video_fps": 29.0,
                "frames": 1234, "video_frames": 1200, "restarts": 2, "reconnects": 1,
                "share": 0.93, "nearest": 0.52, "median": 1.84, "points": 61234, "tilt": 1.0,
                "tilt_status": "stopped", "accel": (-0.38, 9.44, 0.2), "led": "green",
                "target": 0.0, "ir": 30, "exposure": 10000, "flags": {"auto_exposure": False},
                "video": "color", "log": "", "said": "", "can": {**OPEN, "exposure": ""}, "focal": 575.0,
                "radar": radar_profile()}
        self.telemetry = kinect.Telemetry(**{**base, **tele})
        self.status = "connected"
        self.options = kinect.Options()
        self.asked: list[tuple] = []
        self.placed: list[dict] = []

    def request(self, kind, value=None):
        self.asked.append((kind, value))
        return ""

    def place(self, **kw):
        self.placed.append(kw)
        return ""


def node(dev) -> graphview.VNode:
    return graphview.VNode(f"device:{dev.role}", "device", dev.role, ref=dev)


class Pane:
    """The pane drawn in a window of a width, a frame at a time."""

    def __init__(self, r, monkeypatch, dev, width, height=1800):
        self.r, self.dev, self.size = r, dev, (width, height)
        imgui.get_io().display_size = imgui.ImVec2(width + 40, height + 40)
        self.d = Driver(step=self.frame)
        self.d.record(monkeypatch.setattr)
        self.d.run(self.d.wait(3))

    def frame(self) -> None:
        r = self.r
        st = ui_graph._state(r.panel)
        imgui.new_frame()
        imgui.set_next_window_pos(imgui.ImVec2(10, 10))
        imgui.set_next_window_size(imgui.ImVec2(*self.size))
        imgui.begin("side", None, imgui.WindowFlags_.no_move)
        ui_graph._side(r.panel, st, st["view"], ("node", node(self.dev)))
        imgui.end()
        imgui.end_frame()

    def spills(self) -> list[tuple[str, float]]:
        right = 10 + self.size[0]
        return [(k, round(x1 - right, 1)) for k, (x0, _y0, x1, _y1) in self.d.rects.items()
                if x0 < right and x1 > right + 1]


@pytest.fixture()
def rig(tmp_path):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        ui_graph._state(r.panel)               # (made by a frame, below)
        from test_ui_shell import frame
        frame(r.panel, "graph")
        yield r


WIDTHS = [pytest.param(ui_graph.SIDE_MIN, id="SIDE_MIN"), pytest.param(ui_graph.SIDE_W, id="SIDE_W")]


@pytest.mark.parametrize("width", WIDTHS)
def test_every_control_is_in_the_pane_with_an_id_and_none_passes_its_edge(rig, monkeypatch, width):
    p = Pane(rig, monkeypatch, Dev(), width)
    assert ALL <= set(p.d.rects), sorted(ALL - set(p.d.rects))
    assert not p.spills(), p.spills()


@pytest.mark.parametrize("width", WIDTHS)
def test_long_words_and_a_dead_sensor_still_fit(rig, monkeypatch, width):
    """A motor that did not open, a long libfreenect line, nothing live: the words wrap or
    are cut, and the controls stay inside."""
    dev = Dev(live=False, motor_why="the motor would not open (" + "LIBUSB_ERROR_ACCESS " * 6
              + "); the camera runs without it", log="x" * 300, said="tilt: " + "y" * 200,
              model="not a 1414 (bcdDevice 99999)", can={})
    dev.status = "error: " + "another app holds the Kinect " * 4
    p = Pane(rig, monkeypatch, dev, width)
    assert ALL <= set(p.d.rects)
    assert not p.spills(), p.spills()


def test_tilt_is_sent_on_release_and_never_while_dragging(rig, monkeypatch):
    dev = Dev()
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    d = p.d
    x0, y0, x1, y1 = d.rect("kinect.tilt")
    y = (y0 + y1) / 2
    d.run(d.move("kinect.tilt"), d.press(True))
    for i in range(1, 9):                                    # a drag, a frame at a time
        d.run(d.move((x0 + (x1 - x0) * i / 10, y)))
        assert dev.asked == [], f"sent while dragging, frame {i}"
    d.run(d.press(False))
    d.run(d.wait(2))
    assert [k for k, _ in dev.asked] == ["tilt"]
    _kind, target = dev.asked[0]
    assert -31.0 <= target <= 31.0 and target != 0.0


def test_go_and_level_are_the_other_deliberate_actions(rig, monkeypatch):
    dev = Dev()
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    d = p.d
    d.run(d.enter("kinect.tilt", 12))
    assert dev.asked[-1] == ("tilt", 12.0)
    n = len(dev.asked)
    d.run(d.click("kinect.tilt.go"), d.park())
    assert dev.asked[n:] == [("tilt", 12.0)]
    d.run(d.click("kinect.tilt.level"), d.park())
    assert dev.asked[-1] == ("tilt", 0.0)
    d.run(d.wait(2))
    d.run(d.click("kinect.tilt.go"), d.park())
    assert dev.asked[-1] == ("tilt", 0.0)                    # the level is the target now


def test_nothing_is_asked_by_drawing(rig, monkeypatch):
    dev = Dev()
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    p.d.run(p.d.wait(20))
    assert dev.asked == [] and dev.placed == []


def test_the_led_video_and_streams_ask_for_what_was_picked(rig, monkeypatch):
    dev = Dev()
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    d = p.d
    d.run(d.pick("kinect.led", 4))                           # blink green
    assert dev.asked[-1] == ("led", 4)
    d.run(d.pick("kinect.led", 5))
    assert dev.asked[-1] == ("led", 6)                       # blink red / yellow: libfreenect's 6
    d.run(d.click("kinect.video.ir"), d.park())
    assert dev.asked[-1] == ("video", "ir")
    d.run(d.click("kinect.video.color"), d.park())           # (it is already colour: not asked)
    assert dev.asked[-1] == ("video", "ir")
    d.run(d.click("kinect.restart"), d.park())
    assert dev.asked[-1] == ("restart", None)
    d.run(d.click("kinect.reconnect"), d.park())
    assert dev.asked[-1] == ("reconnect", None)
    d.run(d.click("kinect.flicker"), d.park())
    assert dev.asked[-1] == ("flicker", True)


def test_the_infrared_and_exposure_are_sent_on_release_by_value(rig, monkeypatch):
    dev = Dev()
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    d = p.d
    d.run(d.enter("kinect.ir", 42))
    assert dev.asked[-1] == ("ir", 42)
    d.run(d.enter("kinect.exposure", 5000))
    assert dev.asked[-1] == ("exposure", 5000)


def test_the_placement_is_this_run_only_and_says_so(rig, monkeypatch):
    dev = Dev()
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    d = p.d
    said = []
    real = imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_wrapped", lambda s, *a: (said.append(s), real(s, *a))[1])
    d.run(d.enter("kinect.far", 3), d.click("kinect.mirror"), d.park())
    assert dev.placed[0] == {"far": 3.0} and dev.placed[-1] == {"mirror": False}
    assert ui_kinect.NOT_SAVED in said
    assert dev.asked == []                                   # a placement is no request


def test_a_control_the_device_cannot_use_is_disabled_with_its_word(rig, monkeypatch):
    said = []
    real = imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_wrapped", lambda s, *a: (said.append(s), real(s, *a))[1])
    why = "the motor would not open (x); the camera runs without it"
    dev = Dev(motor_why=why, tilt=None, tilt_status="", accel=None, flags={},
              video="off", can={**OPEN, "tilt": why, "led": why, "exposure": "needs the colour stream",
                                "auto_exposure": "needs the colour stream",
                                "white_balance": "needs the colour stream",
                                "flicker": "needs the colour stream"})
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_MIN)
    d = p.d
    assert said.count(why) >= 3                              # the tilt's, the LED's, the motor's line
    assert "auto settings: needs the colour stream" in said        # said once, not four times
    assert "exposure time: needs the colour stream" not in said
    n = len(dev.asked)
    d.run(d.click("kinect.tilt.go"), d.click("kinect.tilt.level"), d.click("kinect.flicker"),
          d.park())
    d.run(d.enter("kinect.exposure", 4000))
    assert dev.asked[n:] == []                               # a disabled control asks nothing
    d.run(d.click("kinect.restart"), d.park())               # the streams' own are not the motor's
    assert dev.asked[-1] == ("restart", None)


def test_no_sensor_says_so_on_every_control_and_asks_nothing(rig, monkeypatch):
    said = []
    real = imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_wrapped", lambda s, *a: (said.append(s), real(s, *a))[1])
    dev = Dev(live=False, can={})
    dev.status = "lost"
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_MIN)
    p.d.run(p.d.click("kinect.restart"), p.d.click("kinect.reconnect"), p.d.click("kinect.tilt.go"),
            p.d.park())
    assert dev.asked == [] and ui_kinect.NO_SENSOR in said


def test_the_telemetry_reads_the_snapshot(rig, monkeypatch):
    shown = []
    real = imgui.text_colored
    monkeypatch.setattr(imgui, "text_colored", lambda c, s: (shown.append(s), real(c, s))[1])
    p = Pane(rig, monkeypatch, Dev(log="usb_claim_interface failed"), ui_graph.SIDE_W)
    p.d.run(p.d.wait(1))
    text = "\n".join(shown)
    for want in ("1414", "30 fps · 1234 frames", "93 % of pixels", "0.52 m", "1.84 m", "61234",
                 "1.0° · stopped", "-0.38 9.44 0.20 m/s²", "2 streams · 1 reconnects"):
        assert want in text, want


def test_other_devices_panes_are_as_they_were(rig, monkeypatch):
    """The Kinect's body is for a kinect device only: another kind's node never reaches it."""
    calls = []
    monkeypatch.setattr(ui_kinect, "body", lambda panel, dev: calls.append(dev))
    st = ui_graph._state(rig.panel)
    for kind in ("gamepad", "midi", "hands", "osc", "cloud", ""):
        n = graphview.VNode(f"device:{kind or 'x'}", "device", kind or "x", ref=NS(kind=kind, io=None))
        imgui.new_frame()
        imgui.begin("side")
        ui_graph._node_side(rig.panel, st, st["view"], None, n)
        imgui.end()
        imgui.end_frame()
    assert calls == []
    assert ui_kinect.is_kinect_node(node(Dev()))
    assert not ui_kinect.is_kinect_node(graphview.VNode("render:acid", "render", "acid", ref=Dev()))
    n = node(Dev())
    imgui.new_frame()
    imgui.begin("side")
    ui_graph._node_side(rig.panel, st, st["view"], None, n)
    imgui.end()
    imgui.end_frame()
    assert len(calls) == 1


def test_the_module_is_watched_and_reloaded_in_order():
    from hyperspace import hotreload
    m = hotreload.MODULES
    assert m.index("kinect") < m.index("ui_kinect") < m.index("ui_graph")
    assert m.index("dkit.tokens") < m.index("ui_kinect")


def test_the_radar_is_drawn_inside_the_pane_and_asks_for_nothing_even_unlit(rig, monkeypatch):
    for width in (ui_graph.SIDE_MIN, ui_graph.SIDE_W):
        for tele in ({}, {"live": False, "radar": None, "can": {}}, {"radar": None}):
            dev = Dev(**tele)
            p = Pane(rig, monkeypatch, dev, width)
            x0, y0, x1, y1 = p.d.rects["kinect.radar"]
            assert 10 <= x0 and x1 <= 10 + width + 1 and y1 - y0 <= ui_kinect.RADAR_MAX_H + 1
            assert (y1 - y0) == pytest.approx(min((x1 - x0) * ui_kinect.RADAR_ASPECT, ui_kinect.RADAR_MAX_H), abs=1)
            assert not p.spills(), p.spills()
            p.d.run(p.d.wait(5))
            assert dev.asked == [] and dev.placed == []


def test_the_radar_plots_the_readings_as_dots_and_lines_in_the_tokens_colours(rig, monkeypatch):
    dots, lines, quads = [], [], []
    real_c, real_p = imgui.ImDrawList.add_circle_filled, imgui.ImDrawList.add_polyline
    monkeypatch.setattr(imgui.ImDrawList, "add_circle_filled",
                        lambda self, c, r, col, n=0: (dots.append(col), real_c(self, c, r, col, n))[1])
    monkeypatch.setattr(imgui.ImDrawList, "add_polyline",
                        lambda self, pts, col, fl, th: (lines.append(col), real_p(self, pts, col, fl, th))[1])
    monkeypatch.setattr(imgui.ImDrawList, "add_convex_poly_filled",
                        lambda self, *a: quads.append(a))
    Pane(rig, monkeypatch, Dev(), ui_graph.SIDE_W)
    assert dots and len(dots) % 32 == 0 and set(dots) == {ui.u32(ui.TEXT)}   # 12 + 20 a frame; the 9 m one is out of range
    assert quads == []                                                    # no cells: a dot a column
    assert {ui.u32(ui.RED), ui.u32(ui.LINE), ui.u32(ui.TEXT)} <= set(lines)   # yours, the sensor's, the readings
    dots.clear()
    Pane(rig, monkeypatch, Dev(live=False, can={}), ui_graph.SIDE_W)
    assert dots == []                                                     # not live: no readings


def test_the_readings_become_points_the_pure_way():
    prof = [0] * kinect.RADAR_COLS
    prof[40], prof[41], prof[43] = 2000, 2000, 3000
    runs = ui_kinect.radar_points(prof, 575.0, False, 100.0, 0.0, 500.0)
    assert [len(r) for r in runs] == [2, 1]                                # a gap ends a run
    (x0, y0), (x1, _y1) = runs[0]
    assert y0 == pytest.approx(500 - 2.0 * 100.0)                          # forward = z
    assert x0 == pytest.approx(((40 * 8 + 4 - 320) / 575.0) * 2.0 * 100.0) and x1 > x0   # lateral = (x − W/2) z / f
    mirrored = ui_kinect.radar_points(prof, 575.0, True, 100.0, 0.0, 500.0)
    assert mirrored[0][0][0] == pytest.approx(-x0)
    assert ui_kinect.radar_points([0] * kinect.RADAR_COLS, 575.0, False, 100, 0, 0) == []
    assert ui_kinect.radar_points([9000] * kinect.RADAR_COLS, 575.0, False, 100, 0, 0) == []


def test_the_sensors_working_range_is_drawn_apart_from_your_frustum():
    g = ui_kinect.radar_geometry(575.0, 1.0, 3.0, 2.0, 40.0, 100.0, 200.0)
    assert len(g.spec) == 2 and g.near_arc != g.spec[0]
    assert g.spec[0][0][1] > g.spec[1][0][1]                               # 0.8 m is nearer the sensor than 4 m


def test_your_frustum_is_drawn_with_no_sensor_too(rig, monkeypatch):
    lines = []
    real = imgui.ImDrawList.add_polyline
    monkeypatch.setattr(imgui.ImDrawList, "add_polyline",
                        lambda self, pts, col, fl, th: (lines.append(col), real(self, pts, col, fl, th))[1])
    Pane(rig, monkeypatch, Dev(live=False, can={}), ui_graph.SIDE_W)
    assert ui.u32(ui.RED) in lines


def test_the_pane_tells_the_device_it_is_looked_at(rig, monkeypatch):
    dev = Dev()
    dev.watched = 0
    dev.watch = lambda: setattr(dev, "watched", dev.watched + 1)
    Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    assert dev.watched >= 3 and dev.asked == []


def test_the_limited_frustum_follows_near_and_far():
    f = 575.0
    a = ui_kinect.radar_geometry(f, 0.5, 4.5, 2.0, 40.0, 100.0, 200.0)
    b = ui_kinect.radar_geometry(f, 1.0, 3.0, 2.0, 40.0, 100.0, 200.0)
    assert a.fan == b.fan and a.rim == b.rim and a.apex == (100.0, 200.0)
    assert a.near_arc != b.near_arc and a.far_arc != b.far_arc
    mid = len(a.far_arc) // 2
    assert a.near_arc[mid] == pytest.approx((100.0, 200.0 - 0.5 * 40.0))     # straight ahead
    assert b.far_arc[mid] == pytest.approx((100.0, 200.0 - 3.0 * 40.0))
    half = ui_kinect.half_angle(f)
    assert half == pytest.approx(math.atan(320 / 575))
    (nl, fl), (nr, fr) = b.edges                                   # the edge rays join the arcs' ends
    assert nl == pytest.approx(b.near_arc[0]) and fr == pytest.approx(b.far_arc[-1])
    assert fl == pytest.approx(b.far_arc[0]) and nr == pytest.approx(b.near_arc[-1])
    assert b.centre == ((96.0, 200.0 - 80.0), (104.0, 200.0 - 80.0))
    assert ui_kinect.radar_geometry(f, 0.5, 4.5, 9.0, 40.0, 0, 0).centre is None
    wide = ui_kinect.radar_geometry(f, 0.5, 20.0, 2.0, 40.0, 0, 0)         # clipped to the range
    assert wide.far_arc[mid][1] == pytest.approx(-ui_kinect.RADAR_RANGE * 40.0)


def test_the_geometry_follows_the_devices_place():
    d = kinect.KinectDevice("room", {}, sensor=lambda o: None)
    before = ui_kinect.radar_geometry(575.0, d.options.near, d.options.far, d.options.centre, 40, 0, 0)
    assert d.place(near=1.0, far=3.0) == ""
    after = ui_kinect.radar_geometry(575.0, d.options.near, d.options.far, d.options.centre, 40, 0, 0)
    assert before.near_arc != after.near_arc and before.far_arc != after.far_arc


def test_the_fan_fits_the_radar_box_at_both_widths():
    for width in (ui_graph.SIDE_MIN, ui_graph.SIDE_W):
        h = min(width * ui_kinect.RADAR_ASPECT, ui_kinect.RADAR_MAX_H)
        s = ui_kinect.radar_scale(575.0, width, h)
        g = ui_kinect.radar_geometry(575.0, 0.5, 4.5, 2.0, s, width / 2, h - ui_kinect.RADAR_PAD)
        xs = [x for x, _ in g.rim]
        ys = [y for _, y in g.rim]
        assert min(xs) >= 0 and max(xs) <= width and min(ys) >= 0


def test_a_kinects_node_is_drawn_under_patch_only_though_no_cable_reaches_it(rig, monkeypatch):
    """The owner saw no Kinect node with the sensor plugged in: its cloud is no lane, so
    nothing wires it to the loadable patch, and the default "patch only" view drew
    only what reaches the patch. Its control panel is its node's pane, so it is drawn."""
    import time

    import numpy as np
    from test_ui_shell import frame

    from hyperspace import devices

    class Stand:
        focal = 575.0

        def __init__(self, o):
            pass

        def open(self):
            pass

        def read(self):
            time.sleep(0.01)
            return np.full((480, 640), 2000, np.uint16), None

        def close(self):
            pass

    monkeypatch.setattr(kinect.KinectDevice.__init__, "__kwdefaults__", {"io": None, "sensor": Stand})
    reg = devices.DeviceRegistry([{"role": "room", "kind": "kinect"}], devices.Context())
    reg.open_all()
    try:
        end = time.monotonic() + 3
        while reg.get("room").status != "connected" and time.monotonic() < end:
            time.sleep(0.01)
        rig.panel.devices = reg
        for _ in range(6):
            frame(rig.panel, "graph")
        st = ui_graph._state(rig.panel)
        st["patch_only"] = True                     # the app's default (the tests' fixtures turn it off)
        for _ in range(4):
            frame(rig.panel, "graph")
        assert st["view"].spec is not None, "a loadable patch is open"
        assert "device:room" in graphview.patch_only(st["view"])
        assert "n:device:room" in st["names"].values()                   # on the canvas
    finally:
        reg.close()


def test_a_kinects_node_is_titled_kinect_not_by_its_role(rig):
    from hyperspace import ui_routing
    router = ui_routing.router_of(rig.panel)
    one = kinect.KinectDevice("room", {"role": "room", "kind": "kinect"})
    v = graphview.build(router.table, rig.panel.reg, router, [one])
    assert v.node("device:room").label == "Kinect"                 # the id is still the role's
    two = kinect.KinectDevice("stage", {"role": "stage", "kind": "kinect"})
    v = graphview.build(router.table, rig.panel.reg, router, [one, two])
    assert [v.node("device:room").label, v.node("device:stage").label] == ["Kinect room", "Kinect stage"]


def test_a_setting_a_sink_row_drives_is_the_routes_not_the_sliders(rig, monkeypatch):
    said = []
    real = imgui.text_wrapped
    monkeypatch.setattr(imgui, "text_wrapped", lambda s, *a: (said.append(s), real(s, *a))[1])
    dev = Dev()
    dev.driven = frozenset({"ir"})
    p = Pane(rig, monkeypatch, dev, ui_graph.SIDE_W)
    assert ui_kinect.DRIVEN in said
    p.d.run(p.d.enter("kinect.ir", 10))
    assert ("ir", 10) not in dev.asked                       # the slider is the route's now
    p.d.run(p.d.enter("kinect.exposure", 5000))
    assert dev.asked[-1] == ("exposure", 5000)               # …and only that one


def test_a_kinects_cloud_is_titled_kinect_point_cloud_and_another_clouds_is_not():
    """The Kinect's cloud is made of the sensor's depth by the sensor's calibration: its
    own kind, not a general point cloud, and its node says so. A `cloud` device's stays."""
    from test_plan36_edges import Bindings, Registry, build, migrated

    from hyperspace import graph as G
    spec = G.read_graph(migrated())
    sensor = kinect.KinectDevice("room", {"role": "room", "kind": "kinect"})
    scan = NS(role="scan", kind="cloud", status="connected", sources=(), feeds=())
    g = build(spec, clouds=("room", "scan"))
    v = graphview.build(Bindings(), Registry(), None, [sensor, scan], g, spec)
    assert v.node("render:cloud").label == "Kinect point cloud"
    assert v.node("render:cloud.2").label == "Point cloud 2"
    v = graphview.build(Bindings(), Registry(), None, [scan], build(spec, clouds=("scan",)), spec)
    assert v.node("render:cloud").label == "Point cloud"
