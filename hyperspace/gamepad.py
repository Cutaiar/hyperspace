"""Xbox gamepad as a second hand on the hotkeys — polled raw through GLFW.

GLFW's bundled SDL mapping database misses this controller's Bluetooth-LE
GUID (030000005e040000130b000009050000) and a runtime mapping doesn't
take on macOS, so the pad is read through the raw joystick API with our
own index map, captured against a real Xbox Series S controller over
Bluetooth (fw 5.9.2709.0). Buttons 2/5/8/9 are unused gaps on this
firmware. Works identically over USB-C.

The Pad class mirrors app.Keys: poll once per frame, then edge-detect
with pressed(). A disconnect just makes the pad inert; reconnecting is
picked up on a later poll, no re-pairing dance in code.
"""

from __future__ import annotations

import glfw

# raw button indices (captured; stick clicks follow the SDL layout)
A, B, X, Y = 0, 1, 3, 4
LB, RB = 6, 7
VIEW, MENU, XBOX = 10, 11, 12
LSTICK, RSTICK = 13, 14

# axes: sticks in ±1, triggers resting at −1.0
AX_LX, AX_LY, AX_RX, AX_RY, AX_LT, AX_RT = 0, 1, 2, 3, 4, 5

# the D-pad is the hat, a GLFW bitmask
HAT_UP, HAT_RIGHT, HAT_DOWN, HAT_LEFT = 1, 2, 4, 8

DEADZONE = 0.18


def _unwrap(ret) -> list:
    """pyGLFW's raw joystick getters return a (pointer, count) pair."""
    if not ret:
        return []
    ptr, n = ret
    return [ptr[i] for i in range(n)]


class Pad:
    """Edge detection and analog reads over polled pad state."""

    def __init__(self):
        self.jid: int | None = None
        self.buttons: list = []
        self.prev_buttons: list = []
        self.hat = 0
        self.prev_hat = 0
        self.axes: list[float] = [0.0] * 6

    @property
    def on(self) -> bool:
        return self.jid is not None

    def poll(self) -> None:
        if self.jid is None or not glfw.joystick_present(self.jid):
            self.jid = next(
                (j for j in range(glfw.JOYSTICK_1, glfw.JOYSTICK_LAST + 1)
                 if glfw.joystick_present(j)),
                None,
            )
            self.buttons, self.prev_buttons = [], []
            self.hat = self.prev_hat = 0
            self.axes = [0.0] * 6
            if self.jid is None:
                return
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons = _unwrap(glfw.get_joystick_buttons(self.jid))
        hats = _unwrap(glfw.get_joystick_hats(self.jid))
        self.hat = hats[0] if hats else 0
        ax = _unwrap(glfw.get_joystick_axes(self.jid))
        if len(ax) >= 6:
            self.axes = ax

    def down(self, b: int) -> bool:
        return b < len(self.buttons) and bool(self.buttons[b])

    def pressed(self, b: int) -> bool:
        was = b < len(self.prev_buttons) and bool(self.prev_buttons[b])
        return self.down(b) and not was

    def hat_pressed(self, bit: int) -> bool:
        return bool(self.hat & bit) and not (self.prev_hat & bit)

    def axis(self, i: int) -> float:
        """Stick axis with the deadzone cut out and the rest rescaled to ±1."""
        v = self.axes[i] if i < len(self.axes) else 0.0
        if abs(v) < DEADZONE:
            return 0.0
        s = 1.0 if v > 0 else -1.0
        return s * (abs(v) - DEADZONE) / (1.0 - DEADZONE)

    def trigger(self, i: int) -> float:
        """Trigger travel in [0, 1] (raw axis rests at −1)."""
        v = (self.axes[i] + 1.0) / 2.0 if i < len(self.axes) else 0.0
        return v if v > 0.02 else 0.0
