"""The tracking source and the DAW port against a fake ``leap`` (audit N5).

`LeapSource` imports the SDK bindings inside its constructor, so a fake
module in `sys.modules["leap"]` — the Listener base, a Connection, the
TrackingMode names — is the whole surface it uses. The connect attempt
runs on a thread; `source.connecting.join()` waits for it.
"""

from __future__ import annotations

import math
import sys
import threading
from types import SimpleNamespace as NS

import pytest

from hyperspace.hands import HandSettings, HandsIO
from hyperspace.hands import core as hc


class FakeLeap:
    """What hands/core.py touches of the ``leap`` bindings."""

    def __init__(self):
        self.connections: list[FakeLeap.Connection] = []
        self.refuse: Exception | None = None
        leap = self

        class Listener:
            pass

        class Connection:
            def __init__(self):
                self.listeners = []
                self.mode = None
                self.connected = self.disconnected = False
                self.raise_on_disconnect = False
                leap.connections.append(self)

            def add_listener(self, listener):
                self.listeners.append(listener)

            def connect(self, auto_poll=True):
                if leap.refuse is not None:
                    raise leap.refuse
                self.connected = True
                self.fire("on_connection_event", NS())

            def set_tracking_mode(self, mode):
                self.mode = mode

            def disconnect(self):
                if self.raise_on_disconnect:
                    raise RuntimeError("already gone")
                self.disconnected = True

            def fire(self, event, *args):
                for listener in self.listeners:
                    getattr(listener, event)(*args)

        self.Listener, self.Connection = Listener, Connection
        self.TrackingMode = NS(Desktop="Desktop", ScreenTop="ScreenTop", HMD="HMD")


@pytest.fixture()
def leap(monkeypatch):
    fake = FakeLeap()
    monkeypatch.setitem(sys.modules, "leap", fake)
    return fake


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def v3(x, y, z):
    return NS(x=x, y=y, z=z)


def hand(side="right", conf=1.0, y=200.0):
    return NS(type=NS(name=side.capitalize()), confidence=conf, grab_strength=0.0,
              pinch_strength=0.0, grab_angle=0.0, pinch_distance=80.0,
              palm=NS(position=v3(0.0, y, 0.0), normal=v3(0.0, -1.0, 0.0),
                      direction=v3(0.0, 0.0, -1.0), width=0.0))


def source(leap, mode="desktop", clock=None):
    src = hc.LeapSource(mode, clock or Clock())
    src.connecting.join(5.0)
    return src, leap.connections[-1]


# ---------------------------------------------------------------- connecting

def test_the_source_connects_on_a_thread_and_sets_the_tracking_mode(leap):
    src, conn = source(leap, "screentop")
    assert isinstance(src.connecting, threading.Thread) and not src.connecting.is_alive()
    assert conn.connected and conn.mode == "ScreenTop"
    assert src.status == "connected" and src.on


def test_an_unknown_mode_falls_back_to_desktop(leap):
    _, conn = source(leap, "sideways")
    assert conn.mode == "Desktop"


def test_a_refused_connection_reports_and_stays_off(leap):
    leap.refuse = RuntimeError("no service")
    src, conn = source(leap)
    assert src.status == "RuntimeError: no service" and not src.on
    assert not conn.connected and src.latest()[2] == {}


# ---------------------------------------------------------------- frames

def test_a_device_and_a_frame_make_hands_that_go_stale(leap):
    clock = Clock()
    src, conn = source(leap, clock=clock)
    conn.fire("on_device_event", NS())
    assert src.status == "tracking" and src.on
    assert src.latest() == (0, -1.0, {})
    clock.t = 1.0
    conn.fire("on_tracking_event", NS(hands=[hand("right"), hand("left", y=150.0)]))
    seq, t, hands = src.latest()
    assert (seq, t) == (1, 1.0) and set(hands) == {"left", "right"}
    feats, conf = hands["right"]
    assert feats["y"] == 200.0 and conf == 1.0 and math.isclose(feats["roll"], 0.0)
    clock.t = 1.0 + hc.STALE_S + 0.01                # no frame for too long: no hands
    assert src.latest() == (1, 1.0, {})


def test_two_hands_of_one_side_keep_the_more_confident(leap):
    clock = Clock()
    src, conn = source(leap, clock=clock)
    clock.t = 0.5
    conn.fire("on_tracking_event",
              NS(hands=[hand("right", conf=0.3, y=100.0), hand("right", conf=0.9, y=300.0)]))
    hands = src.latest()[2]
    assert list(hands) == ["right"] and hands["right"][0]["y"] == 300.0


def test_losing_the_service_or_the_camera_and_errors_show_in_the_status(leap):
    src, conn = source(leap)
    conn.fire("on_device_lost_event", NS())
    assert src.status == "no camera" and not src.on
    conn.fire("on_connection_lost_event", NS())
    assert src.status == "service lost"
    conn.fire("on_error", ValueError("bad frame"))
    assert src.status == "error: ValueError: bad frame"


@pytest.mark.parametrize("event, arg", [("on_error", ValueError("bad frame")),
                                        ("on_connection_lost_event", NS()),
                                        ("on_device_lost_event", NS())])
def test_a_tracking_frame_after_a_bad_status_puts_the_hands_back_on_the_router(leap, event, arg):
    """2026-10-08 at the rig: one SDK error mid-show left the status bad
    while frames kept coming — the ghost hands drew, but `on` was false,
    so HandsIO fed the router None and no hand route moved until a relaunch."""
    clock = Clock()
    src, conn = source(leap, clock=clock)
    conn.fire("on_device_event", NS())
    conn.fire(event, arg)
    assert not src.on
    clock.t = 1.0
    conn.fire("on_tracking_event", NS(hands=[hand("right")]))
    assert src.status == "tracking" and src.on

    class Router:
        def __init__(self):
            self.labels, self.names, self.gates, self.rests, self.fed = {}, {}, {}, {}, {}

        def feed(self, scheme, values):
            self.fed[scheme] = values

    settings = HandSettings.from_config({})
    io = HandsIO(settings, {"out": ""}, source=src, out=NS(send=lambda m: None),
                 clock=clock)
    router = Router()
    io.poll(1 / 60, None, router)
    assert router.fed["hand"] is not None


# ---------------------------------------------------------------- the skeleton

def _floats(x):
    """Every leaf of a skeleton, which must be a plain float."""
    if isinstance(x, dict):
        return [v for k in x.values() for v in _floats(k)]
    if isinstance(x, (list, tuple)):
        return [v for k in x for v in _floats(k)]
    return [x]


def test_a_tracking_frame_yields_a_complete_skeleton_per_side_that_goes_stale(leap):
    from fake_hands import hand as full_hand

    clock = Clock()
    src, conn = source(leap, clock=clock)
    clock.t = 1.0
    conn.fire("on_tracking_event",
              NS(hands=[full_hand("right", "fist", (90.0, 210.0, 5.0)),
                        full_hand("left", "open", (-90.0, 190.0, 0.0))]))
    seq, t, skel = src.skeletons()
    assert (seq, t) == src.latest()[:2] == (1, 1.0) and set(skel) == {"left", "right"}
    for side, sk in skel.items():
        assert len(sk["digits"]) == len(hc.DIGITS) == 5
        for digit in sk["digits"]:
            assert len(digit) == len(hc.BONES) == 4
            for bone in digit:
                assert len(bone["prev"]) == len(bone["next"]) == 3 and len(bone["rot"]) == 4
                assert bone["width"] > 0
        feats = src.latest()[2][side][0]
        assert sk["palm"] == (feats["x"], feats["y"], feats["z"])   # the same hand
        assert len(sk["normal"]) == len(sk["direction"]) == 3 and sk["width"] == 85.0
        assert sk["arm"] is not None and len(sk["arm"]["prev"]) == 3
        # nothing the SDK owns survives the callback: plain floats throughout
        assert all(type(v) is float for v in _floats(sk))
    assert skel["right"]["palm"] == (90.0, 210.0, 5.0)
    # the fingertip is the distal bone's far end, as pinches() reads it
    tip = skel["right"]["digits"][1][3]["next"]
    f = full_hand("right", "fist", (90.0, 210.0, 5.0)).index.distal.next_joint
    assert tip == (f.x, f.y, f.z)
    clock.t = 1.0 + hc.STALE_S + 0.01                # no frame for too long: no skeleton
    assert src.skeletons() == (1, 1.0, {})


def test_the_skeleton_is_the_more_confident_hand_of_a_side(leap):
    from fake_hands import hand as full_hand

    clock = Clock()
    src, conn = source(leap, clock=clock)
    conn.fire("on_tracking_event",
              NS(hands=[full_hand("right", conf=0.3, at=(0.0, 100.0, 0.0)),
                        full_hand("right", conf=0.9, at=(0.0, 300.0, 0.0))]))
    skel = src.skeletons()[2]
    assert list(skel) == ["right"] and skel["right"]["palm"][1] == 300.0
    assert src.latest()[2]["right"][0]["y"] == 300.0     # the same hand as the features


def test_a_palm_only_hand_has_a_skeleton_with_no_digits(leap):
    src, conn = source(leap)
    conn.fire("on_tracking_event", NS(hands=[hand("right")]))
    sk = src.skeletons()[2]["right"]
    assert sk["digits"] == [] and sk["arm"] is None and sk["width"] == hc.PALM_W


def test_a_skeleton_that_cannot_be_read_never_costs_the_features(leap):
    from fake_hands import hand as full_hand

    src, conn = source(leap)
    h = full_hand("right")
    del h.index.metacarpal.prev_joint               # bindings missing a joint
    conn.fire("on_tracking_event", NS(hands=[h]))
    assert src.latest()[2]["right"][0]["y"] == 200.0   # the axes still get the frame
    assert src.skeletons()[2] == {}


def test_hands_io_keeps_the_skeletons_of_the_hands_present_only(leap):
    from fake_hands import hand as full_hand

    clock = Clock()
    io = HandsIO(HandSettings.from_config(), {"out": "", "min_confidence": 0.5}, clock=clock)
    io.source.connecting.join(5.0)
    conn = leap.connections[-1]
    conn.fire("on_tracking_event",
              NS(hands=[full_hand("right"), full_hand("left", conf=0.2)]))
    io.poll(1 / 60)
    assert set(io.skeleton) == {"right"}             # left is under the floor
    assert io.skeleton["right"] is io.source.skeletons()[2]["right"]
    clock.t = hc.STALE_S + 0.01
    io.poll(1 / 60)
    assert io.skeleton == {}
    io.close()


def test_a_source_without_skeletons_leaves_none():
    io = HandsIO(HandSettings.from_config(), {}, out=NS(send=lambda m: None),
                 source=NS(latest=lambda: (1, 0.0, {"right": ({"x": 0.0, "y": 200.0, "z": 0.0,
                                                               "roll": 0.0, "pitch": 0.0,
                                                               "yaw": 0.0}, 1.0)})))
    io.poll(1 / 60)
    assert io.present["right"] and io.skeleton == {}


# ---------------------------------------------------------------- closing

def test_close_disconnects_and_swallows_a_failure(leap):
    src, conn = source(leap)
    src.close()
    assert conn.disconnected
    src2, conn2 = source(leap)
    conn2.raise_on_disconnect = True
    src2.close()                                     # no exception
    assert not conn2.disconnected


def test_hands_io_builds_the_real_source_by_default_and_closes_it(leap):
    settings = HandSettings.from_config()
    io = HandsIO(settings, {"out": "", "mode": "hmd"}, clock=Clock())
    assert isinstance(io.source, hc.LeapSource)
    io.source.connecting.join(5.0)
    conn = leap.connections[-1]
    assert conn.mode == "HMD" and io.out is None and io.out_name == ""
    io.poll(1 / 60)                                  # a frame with nothing seen is fine
    io.close()
    assert conn.disconnected


# ---------------------------------------------------------------- the DAW port
# (plan 27 B3: the port is the `hands-daw` sink's — bridge.OutPort /
# bridge._open_out, moved out of hands/core.py — and HandsIO opens none)

def test_open_out_prefers_an_existing_port_else_makes_a_virtual_one(monkeypatch):
    from hyperspace import bridge

    calls = []
    monkeypatch.setattr(bridge.mido, "get_output_names",
                        lambda: ["IAC Bus 1", "Hyperspace Hands"])
    monkeypatch.setattr(bridge.mido, "open_output",
                        lambda name, virtual=False: calls.append((name, virtual)) or NS(name=name))
    port, err, made = bridge._open_out("hyperspace hands")
    assert port.name == "Hyperspace Hands" and (err, made) == ("", False)
    assert calls == [("Hyperspace Hands", False)]
    port, err, made = bridge._open_out("Other")
    assert port.name == "Other" and (err, made) == ("", True) and calls[-1] == ("Other", True)
    # a retry after a loss joins an existing port only
    assert bridge._open_out("Other", virtual=False) == (None, "out 'Other': no such port", False)
    assert len(calls) == 2
    assert bridge._open_out("") == (None, "", False)


def test_open_out_reports_a_refusing_backend(monkeypatch):
    from hyperspace import bridge

    def boom():
        raise RuntimeError("no MIDI backend")

    monkeypatch.setattr(bridge.mido, "get_output_names", boom)
    assert bridge._open_out("Hands") == (None, "out 'Hands': no MIDI backend", False)


def test_a_failed_open_is_said_once_and_retried(monkeypatch, capsys):
    from hyperspace import bridge, midi

    monkeypatch.setattr(bridge.mido, "get_output_names", list)
    attempts = []

    def open_output(name, virtual=False):
        attempts.append(name)
        raise RuntimeError("virtual ports unsupported")

    monkeypatch.setattr(bridge.mido, "open_output", open_output)
    clock = Clock()
    # the instrument opens nothing, whatever its `out` says
    io = HandsIO(HandSettings.from_config(), {"out": "Hands"},
                 source=NS(latest=lambda: (0, 0.0, {})), clock=clock)
    assert io.out is None and io.error == "" and attempts == []
    port = bridge.OutPort("Hands", clock=clock, who="hands-daw")
    port.open()
    assert port.out is None and port.error == "out 'Hands': virtual ports unsupported"
    port.retry()
    clock.t += midi.RECONNECT_S
    port.retry()
    assert len(attempts) == 2
    assert capsys.readouterr().err.count("virtual ports unsupported") == 1
