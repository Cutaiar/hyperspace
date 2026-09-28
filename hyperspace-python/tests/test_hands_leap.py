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

def test_open_out_prefers_an_existing_port_else_makes_a_virtual_one(monkeypatch):
    calls = []
    monkeypatch.setattr(hc.mido, "get_output_names", lambda: ["IAC Bus 1", "Hyperspace Hands"])
    monkeypatch.setattr(hc.mido, "open_output",
                        lambda name, virtual=False: calls.append((name, virtual)) or NS(name=name))
    port, err = hc._open_out("hyperspace hands")
    assert port.name == "Hyperspace Hands" and err == "" and calls == [("Hyperspace Hands", False)]
    port, err = hc._open_out("Other")
    assert port.name == "Other" and err == "" and calls[-1] == ("Other", True)
    assert hc._open_out("") == (None, "")


def test_open_out_reports_a_refusing_backend(monkeypatch):
    def boom():
        raise RuntimeError("no MIDI backend")

    monkeypatch.setattr(hc.mido, "get_output_names", boom)
    assert hc._open_out("Hands") == (None, "out 'Hands': no MIDI backend")


def test_a_failed_open_is_said_once_and_retried(monkeypatch, capsys):
    monkeypatch.setattr(hc.mido, "get_output_names", list)
    attempts = []

    def open_output(name, virtual=False):
        attempts.append(name)
        raise RuntimeError("virtual ports unsupported")

    monkeypatch.setattr(hc.mido, "open_output", open_output)
    clock = Clock()
    io = HandsIO(HandSettings.from_config(), {"out": "Hands"}, source=NS(latest=lambda: (0, 0.0, {})),
                 clock=clock)
    assert io.out is None and io.error == "out 'Hands': virtual ports unsupported"
    io.poll(1 / 60)
    clock.t += hc.RECONNECT_S
    io.poll(1 / 60)
    assert len(attempts) == 2
    assert capsys.readouterr().err.count("virtual ports unsupported") == 1
