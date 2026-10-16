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


# ---- several pads at once (plan 27 B6) ----

class FakeJoysticks:
    """Several GLFW joysticks: `present` is the set of jids plugged in,
    each with its own buttons (button `jid` held, so a test can tell
    which one a pad reads)."""

    def __init__(self, *present: int):
        self.present = set(present)

    def install(self, monkeypatch):
        def buttons(j):
            b = [0] * 16
            b[j] = 1
            return (b, len(b))
        monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: j in self.present)
        monkeypatch.setattr(gp.glfw, "get_joystick_buttons", buttons)
        monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: ([0], 1))
        monkeypatch.setattr(gp.glfw, "get_joystick_axes",
                            lambda j: ([0.0, 0.0, 0.0, 0.0, -1.0, -1.0], 6))


def two_pads(*, pin2=None, usb=False):
    claims = gp.Claims()
    one, two = Pad(usb=usb), Pad(usb=usb)
    one.attach(claims, "pad")
    two.attach(claims, "p2", joystick=pin2)
    return claims, one, two


def test_two_pads_take_different_joysticks_in_list_order(monkeypatch):
    """Each pad device reads its own controller: the next present GLFW
    joystick no other pad has taken, in list order (the order they poll)."""
    fake = FakeJoysticks(0, 1)
    fake.install(monkeypatch)
    claims, one, two = two_pads()
    one.poll()
    two.poll()
    assert (one.jid, two.jid) == (0, 1) and one.on and two.on
    assert one.down(0) and two.down(1) and not one.down(1)
    assert claims.taken == {0: one, 1: two}
    one.poll()
    two.poll()
    assert (one.jid, two.jid) == (0, 1)                   # each keeps its own


def test_an_unpinned_pad_whose_joystick_leaves_is_lost_then_takes_the_next_free(monkeypatch):
    fake = FakeJoysticks(0, 1)
    fake.install(monkeypatch)
    claims, one, two = two_pads()
    one.poll()
    two.poll()
    fake.present.discard(0)
    one.poll()
    two.poll()
    assert not one.on and one.jid is None and two.jid == 1   # pad 1 is lost; p2 keeps reading
    assert 0 not in claims.taken
    fake.present.add(2)                                    # a third pad appears
    one.poll()
    two.poll()
    assert one.on and one.jid == 2 and two.jid == 1
    fake.present.add(0)                                    # the first comes back: free, untaken
    one.poll()
    two.poll()
    assert (one.jid, two.jid) == (2, 1)


def test_a_pinned_pad_waits_for_its_index(monkeypatch):
    """`joystick = 1` pins a pad: it reads only that index, waits while it
    is absent, and no unpinned pad takes it."""
    fake = FakeJoysticks(0)
    fake.install(monkeypatch)
    claims, one, two = two_pads(pin2=1)
    assert claims.pinned == {1: two}
    one.poll()
    two.poll()
    assert one.jid == 0 and not two.on                    # p2 waits for joystick 1
    fake.present = {1}
    one.poll()
    two.poll()
    assert not one.on and two.jid == 1                    # 1 is p2's, never pad's
    fake.present = {0, 1}
    one.poll()
    two.poll()
    assert (one.jid, two.jid) == (0, 1)


def test_a_bare_pad_still_takes_the_first_present_joystick(monkeypatch):
    """A pad no device attached (the tests', the probe) reads the first
    present joystick, as before plan 27 B6."""
    fake = FakeJoysticks(3, 5)
    fake.install(monkeypatch)
    pad = Pad()
    pad.poll()
    assert pad.jid == 3


def test_one_usb_reader_across_two_pads(monkeypatch):
    """The libusb reader stays one: the first pad attached with usb on
    owns it; a second with usb on is told so and reads GLFW only. Closing
    the owner lets the reader go."""
    fake = FakeJoysticks()
    fake.install(monkeypatch)
    made = []

    class Counted:
        def __init__(self):
            made.append(self)
            self.name, self.note = "", ""

        def latest(self):
            return None

        def close(self):
            pass

    monkeypatch.setattr(gp, "UsbPad", Counted)
    claims, one, two = two_pads(usb=True)
    for _ in range(3):
        one.poll()
        two.poll()
    assert len(made) == 1 and one.usb_pad is made[0] and two.usb_pad is None
    assert claims.usb is one and not two.usb
    assert two.usb_note == "usb: pad has the wired pad"
    one.close()
    assert claims.usb is None and claims.taken == {}


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
