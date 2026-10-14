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


# ---- wired Xbox 360 pads over USB ----

# captured 2026-10-13 off an Afterglow AX.1 (1BAD:F900) at rest: sticks
# near centre, nothing held
REST = bytes.fromhex("0014000000008701 5dff 8602 7700 000000000000".replace(" ", ""))


def report(b2=0, b3=0, lt=0, rt=0, lx=0, ly=0, rx=0, ry=0) -> bytes:
    def s16(v):
        return int(v).to_bytes(2, "little", signed=True)
    return bytes((0x00, 0x14, b2, b3, lt, rt)) + s16(lx) + s16(ly) + s16(rx) + s16(ry) + bytes(6)


def test_decode_rest_is_centred_and_released():
    buttons, hat, axes = gp.decode(REST)
    assert not any(buttons) and hat == 0
    assert all(abs(a) < 0.05 for a in axes[:4])
    assert axes[gp.AX_LT] == axes[gp.AX_RT] == -1.0


def test_decode_buttons_land_on_the_glfw_indices():
    buttons, _, _ = gp.decode(report(b3=0x10 | 0x80 | 0x01, b2=0x20 | 0x40))
    held = {i for i, v in enumerate(buttons) if v}
    assert held == {gp.A, gp.Y, gp.LB, gp.VIEW, gp.LSTICK}
    buttons, _, _ = gp.decode(report(b3=0x20 | 0x40 | 0x02 | 0x04, b2=0x10 | 0x80))
    assert {i for i, v in enumerate(buttons) if v} == {gp.B, gp.X, gp.RB, gp.GUIDE, gp.MENU, gp.RSTICK}


def test_decode_dpad_is_the_hat():
    _, hat, _ = gp.decode(report(b2=0x01 | 0x08))
    assert hat == gp.HAT_UP | gp.HAT_RIGHT
    _, hat, _ = gp.decode(report(b2=0x02 | 0x04))
    assert hat == gp.HAT_DOWN | gp.HAT_LEFT


def test_decode_sticks_and_triggers():
    # stick up is +y on the wire, −1 in GLFW's sense
    _, _, axes = gp.decode(report(lx=32767, ly=32767, ry=-32768, lt=255, rt=0))
    assert axes[gp.AX_LX] == 1.0 and axes[gp.AX_LY] == -1.0 and axes[gp.AX_RY] == 1.0
    assert axes[gp.AX_LT] == 1.0 and axes[gp.AX_RT] == -1.0


def test_decode_ignores_other_messages():
    assert gp.decode(bytes((0x01, 0x03, 0x0E))) is None    # LED status
    assert gp.decode(bytes((0x08, 0x03, 0x00))) is None


class FakeUsbPad:
    def __init__(self):
        self.state = None

    def latest(self):
        return self.state


def test_usb_pad_when_glfw_has_none(monkeypatch):
    fake = FakeJoystick()
    fake.present = False
    fake.install(monkeypatch)
    usb = FakeUsbPad()
    pad = Pad(usb=True)
    pad.usb_pad = usb
    pad.poll()
    assert not pad.on
    usb.state = gp.decode(report(b3=0x10))
    pad.poll()
    assert pad.on and pad.source == "usb" and pad.pressed(gp.A)
    pad.poll()
    assert pad.down(gp.A) and not pad.pressed(gp.A)
    usb.state = None
    pad.poll()
    assert not pad.on and not pad.down(gp.A)


def test_glfw_wins_over_usb(monkeypatch):
    fake = FakeJoystick()
    fake.install(monkeypatch)
    usb = FakeUsbPad()
    usb.state = gp.decode(report(b3=0x20))
    pad = Pad(usb=True)
    pad.usb_pad = usb
    pad.poll()
    assert pad.source == "glfw" and not pad.down(gp.B)


def test_usb_off_never_starts_a_reader(monkeypatch):
    fake = FakeJoystick()
    fake.present = False
    fake.install(monkeypatch)
    pad = Pad()
    pad.poll()
    assert not pad.on and pad.usb_pad is None
