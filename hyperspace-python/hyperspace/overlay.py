"""Overlay mode — the render floats, transparent, over whatever is on screen.

Off: an ordinary window, opaque black ground. On: the window loses its
frame, covers one monitor, sits above everything (on macOS including
another app's fullscreen Space, which is what "over a fullscreen YouTube"
needs), and its ground clears to a chosen darkness so the desktop, or the
video, shows through the polytope. Clicks can be sent through to whatever
is underneath; then the window never takes focus, so the keyboard stops
reaching it — the gamepad and MIDI still do, which is why the overlay has
its own params:

  overlay.on           toggle    enter / leave
  overlay.passthrough  toggle    clicks go to the window underneath
  overlay.bg           0–1       ground darkness: 0 see-through, 1 black
  overlay.alpha        0–1       whole-window opacity (GLFW window opacity)
  overlay.monitor      enum      which screen the overlay covers

The window is created with a transparent framebuffer from the start (a
creation-time GLFW hint), so toggling is only attributes, position and
the clear alpha. Every GLFW/Cocoa call goes through `apply()`, once per
frame, and only when something changed. The window-system backend is
injectable so the state machine tests headlessly.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from .params import Registry

# macOS: NSWindow collection behaviour bits and the level that beats a
# fullscreen Space. GLFW's FLOATING is NSFloatingWindowLevel (3), which
# another app's fullscreen still covers.
_JOIN_ALL_SPACES = 1 << 0
_STATIONARY = 1 << 4
_FULLSCREEN_AUX = 1 << 8
_OVERLAY_LEVEL = 1000        # NSScreenSaverWindowLevel


class GlfwBackend:
    """The real window system; the thin layer overlay.py talks to."""

    def __init__(self, glfw):
        self.glfw = glfw
        self._ns = None          # NSWindow proxy, macOS only, lazily
        self._ns_saved = None

    def monitors(self):
        return list(self.glfw.get_monitors())

    def monitor_name(self, m) -> str:
        return self.glfw.get_monitor_name(m).decode() if isinstance(
            self.glfw.get_monitor_name(m), bytes) else str(self.glfw.get_monitor_name(m))

    def monitor_rect(self, m) -> tuple[int, int, int, int]:
        x, y = self.glfw.get_monitor_pos(m)
        mode = self.glfw.get_video_mode(m)
        return x, y, mode.size.width, mode.size.height

    def window_rect(self, win) -> tuple[int, int, int, int]:
        x, y = self.glfw.get_window_pos(win)
        w, h = self.glfw.get_window_size(win)
        return x, y, w, h

    def set_rect(self, win, x, y, w, h) -> None:
        self.glfw.set_window_pos(win, x, y)
        self.glfw.set_window_size(win, w, h)

    def set_attrib(self, win, name: str, on: bool) -> None:
        attr = getattr(self.glfw, name, None)
        if attr is not None:
            self.glfw.set_window_attrib(win, attr, 1 if on else 0)

    def set_opacity(self, win, a: float) -> None:
        self.glfw.set_window_opacity(win, float(a))

    # ---- macOS: reach the NSWindow for what GLFW does not expose ----

    def _nswindow(self, win):
        if self._ns is not None or sys.platform != "darwin":
            return self._ns
        try:
            import objc

            ptr = self.glfw.get_cocoa_window(win)
            ptr = ptr.value if hasattr(ptr, "value") else ptr
            self._ns = objc.objc_object(c_void_p=ptr)
        except Exception:  # noqa: BLE001 — no pyobjc, no handle: stay at GLFW's level
            self._ns = None
        return self._ns

    def raise_over_spaces(self, win, on: bool) -> None:
        ns = self._nswindow(win)
        if ns is None:
            return
        if on:
            if self._ns_saved is None:
                self._ns_saved = (ns.collectionBehavior(), ns.level(), ns.hasShadow())
            ns.setCollectionBehavior_(_JOIN_ALL_SPACES | _STATIONARY | _FULLSCREEN_AUX)
            ns.setLevel_(_OVERLAY_LEVEL)
            ns.setHasShadow_(False)
        elif self._ns_saved is not None:
            behaviour, level, shadow = self._ns_saved
            ns.setCollectionBehavior_(behaviour)
            ns.setLevel_(level)
            ns.setHasShadow_(shadow)
            self._ns_saved = None


class Overlay:
    """The state, its params, and the once-per-frame apply."""

    def __init__(self, win, backend=None, *, on_enter: Callable | None = None,
                 on_leave: Callable | None = None):
        self.win = win
        self.backend = backend
        self.on_enter, self.on_leave = on_enter, on_leave
        self.on = False
        self.passthrough = True  # an overlay should not block what is under it
        self.bg = 0.0
        self.alpha = 1.0
        self.monitor = -1        # index into backend.monitors(); −1 = the window's own
        self._applied: dict = {"on": False}  # the window starts as a plain window
        self._saved_rect = None
        self.error = ""

    # ---- params ----

    def register(self, reg: Registry) -> None:
        g = "overlay"
        reg.toggle("overlay.on", "Overlay", lambda: self.on,
                   lambda v: setattr(self, "on", bool(v)), group=g,
                   tip="Float the render, frameless and see-through, over the whole "
                       "screen — above a fullscreen video. T toggles.")
        reg.toggle("overlay.passthrough", "Click-through", lambda: self.passthrough,
                   lambda v: setattr(self, "passthrough", bool(v)), group=g,
                   tip="On (the default): clicks go to whatever is underneath, so you can "
                       "run the video behind. The window then never takes focus — to get "
                       "clicks and keys back, ⌘-Tab to Hyperspace and press G, or use the "
                       "pan button on the APC40.")
        reg.continuous("overlay.bg", "Ground", lambda: self.bg,
                       lambda v: setattr(self, "bg", float(v)), lo=0.0, hi=1.0,
                       fmt=lambda v: "clear" if v <= 0 else f"{v:.2f} black", group=g,
                       tip="Darkness of the ground behind the shape in overlay mode: "
                           "0 fully see-through, 1 black.")
        reg.continuous("overlay.alpha", "Opacity", lambda: self.alpha,
                       lambda v: setattr(self, "alpha", float(v)), lo=0.0, hi=1.0,
                       fmt=lambda v: f"{v * 100:.0f}%", group=g,
                       tip="Opacity of the whole window, shape and panel alike.")
        reg.enum("overlay.monitor", "Screen", lambda: max(self.monitor, 0),
                 lambda i: setattr(self, "monitor", int(i)), self.monitor_names, group=g,
                 tip="Which screen the overlay covers.")

    def monitor_names(self) -> list[str]:
        if self.backend is None:
            return ["screen"]
        try:
            return [self.backend.monitor_name(m) or f"screen {i + 1}"
                    for i, m in enumerate(self.backend.monitors())]
        except Exception:  # noqa: BLE001
            return ["screen"]

    # ---- per frame ----

    @property
    def bg_alpha(self) -> float:
        """What the renderer clears to this frame."""
        return self.bg if self.on else 1.0

    def apply(self) -> None:
        """Push state to the window; each attribute only when it changed."""
        if self.win is None or self.backend is None:
            self._track_enter_leave()
            return
        b, win = self.backend, self.win
        try:
            if self._changed("on", self.on):
                if self.on:
                    self._saved_rect = b.window_rect(win)
                    b.set_attrib(win, "DECORATED", False)
                    b.set_attrib(win, "FLOATING", True)
                    x, y, w, h = self._target_rect()
                    b.set_rect(win, x, y, w, h)
                    b.raise_over_spaces(win, True)
                    self._applied.pop("monitor", None)
                else:
                    b.raise_over_spaces(win, False)
                    b.set_attrib(win, "FLOATING", False)
                    b.set_attrib(win, "DECORATED", True)
                    if self._saved_rect is not None:
                        b.set_rect(win, *self._saved_rect)
                    self._applied["passthrough"] = None  # re-apply below
                self._track_enter_leave()
            if self.on and self._changed("monitor", self.monitor):
                b.set_rect(win, *self._target_rect())
            want_pt = self.on and self.passthrough
            if self._changed("passthrough", want_pt):
                b.set_attrib(win, "MOUSE_PASSTHROUGH", want_pt)
            want_a = self.alpha if self.on else 1.0
            if self._changed("alpha", round(want_a, 3)):
                b.set_opacity(win, want_a)
            self.error = ""
        except Exception as e:  # noqa: BLE001 — a window-system hiccup must not kill the loop
            self.error = f"overlay: {e}"[:120]

    def _track_enter_leave(self) -> None:
        was = self._applied.get("entered", False)
        if self.on and not was and self.on_enter:
            self.on_enter()
        elif was and not self.on and self.on_leave:
            self.on_leave()
        self._applied["entered"] = self.on

    def _changed(self, key: str, value) -> bool:
        if self._applied.get(key, object()) == value:
            return False
        self._applied[key] = value
        return True

    def _target_rect(self) -> tuple[int, int, int, int]:
        b = self.backend
        mons = b.monitors()
        if not mons:
            return b.window_rect(self.win)
        if 0 <= self.monitor < len(mons):
            m = mons[self.monitor]
        else:
            # the monitor holding the window's centre
            x, y, w, h = self._saved_rect or b.window_rect(self.win)
            cx, cy = x + w / 2, y + h / 2
            m = mons[0]
            for mm in mons:
                mx, my, mw, mh = b.monitor_rect(mm)
                if mx <= cx < mx + mw and my <= cy < my + mh:
                    m = mm
                    break
        return b.monitor_rect(m)
