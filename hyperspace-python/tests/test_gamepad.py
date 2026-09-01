"""Pad state machine against a scripted fake of GLFW's raw joystick API."""

import hyperspace.gamepad as gp
from hyperspace.gamepad import DEADZONE, Pad


class FakeJoystick:
    """Stands in for the glfw module functions Pad touches."""

    def __init__(self):
        self.present = True
        self.buttons = [0] * 20
        self.hats = [0]
        self.axes = [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]

    def install(self, monkeypatch):
        monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: self.present and j == 0)
        monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: (self.buttons, len(self.buttons)))
        monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: (self.hats, len(self.hats)))
        monkeypatch.setattr(gp.glfw, "get_joystick_axes", lambda j: (self.axes, len(self.axes)))


def test_pressed_fires_on_the_edge_only(monkeypatch):
    fake = FakeJoystick()
    fake.install(monkeypatch)
    pad = Pad()
    pad.poll()
    assert pad.on and not pad.pressed(gp.A)
    fake.buttons[gp.A] = 1
    pad.poll()
    assert pad.pressed(gp.A)
    pad.poll()
    assert pad.down(gp.A) and not pad.pressed(gp.A)  # held, not re-fired
    fake.buttons[gp.A] = 0
    pad.poll()
    assert not pad.down(gp.A)


def test_hat_edges(monkeypatch):
    fake = FakeJoystick()
    fake.install(monkeypatch)
    pad = Pad()
    pad.poll()
    fake.hats[0] = gp.HAT_UP | gp.HAT_RIGHT
    pad.poll()
    assert pad.hat_pressed(gp.HAT_UP) and pad.hat_pressed(gp.HAT_RIGHT)
    pad.poll()
    assert not pad.hat_pressed(gp.HAT_UP)


def test_axis_deadzone_and_rescale(monkeypatch):
    fake = FakeJoystick()
    fake.install(monkeypatch)
    pad = Pad()
    fake.axes[gp.AX_LX] = DEADZONE * 0.9
    pad.poll()
    assert pad.axis(gp.AX_LX) == 0.0
    fake.axes[gp.AX_LX] = 1.0
    pad.poll()
    assert pad.axis(gp.AX_LX) == 1.0
    fake.axes[gp.AX_LX] = -1.0
    pad.poll()
    assert pad.axis(gp.AX_LX) == -1.0


def test_trigger_travel(monkeypatch):
    fake = FakeJoystick()
    fake.install(monkeypatch)
    pad = Pad()
    pad.poll()
    assert pad.trigger(gp.AX_RT) == 0.0  # resting at -1
    fake.axes[gp.AX_RT] = 1.0
    pad.poll()
    assert pad.trigger(gp.AX_RT) == 1.0


def test_disconnect_goes_inert_and_reconnects(monkeypatch):
    fake = FakeJoystick()
    fake.install(monkeypatch)
    pad = Pad()
    fake.buttons[gp.B] = 1
    pad.poll()
    fake.present = False
    pad.poll()
    assert not pad.on and not pad.down(gp.B)
    fake.present = True
    pad.poll()
    assert pad.on
    # state was cleared on reconnect, so a still-held button reads as one
    # fresh edge — deliberate and predictable
    assert pad.pressed(gp.B)
    pad.poll()
    assert pad.down(gp.B) and not pad.pressed(gp.B)
