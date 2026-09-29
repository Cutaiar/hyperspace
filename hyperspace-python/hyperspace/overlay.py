"""Output — where and how the render window shows: screen, fullscreen, overlay.

The render window is pure GL output — the thing on the projector or TV,
with no panel in it (the controls live in their own window; app.py). Its
window-system state is three settings and the params that drive them:

  output.monitor      enum     which screen fullscreen / overlay covers —
                               "follow window" (the one it is on) or a screen
  output.fullscreen   toggle   GLFW fullscreen on that screen, opaque
  output.overlay      toggle   a borderless cover of that screen, see-through
                               and floating above everything — on macOS
                               including another app's fullscreen Space,
                               which is what "over a fullscreen YouTube" needs
  output.passthrough  toggle   in overlay: clicks go to the window underneath
  output.bg           0–1      in overlay: ground darkness, 0 clear … 1 black
  output.alpha        0–1      in overlay: whole-window opacity

Fullscreen asks GLFW for the monitor's current video mode, so a projector
never re-syncs; the window is created with AUTO_ICONIFY off (app.py) so
focusing the control window does not minimise it. Overlay wins when both
are on. With click-through on, the render window never takes focus, so
orbit and zoom stop reaching it (keys, the gamepad and MIDI still do via
the control window) — G, or the pan button on the APC40, takes clicks
back.

Rig-specific settings (monitor, fullscreen, overlay, passthrough) never
persist in a preset and cannot be modulated; ground and opacity are a look
and can. The ``overlay.*`` ids from before the split stay registered as
aliases of the ``output.*`` params; the factory table (routing.py) and
the APC40 profile bind the alias ids, so they are the live names for
those rows, not a shim.

Overlay is there only when the config asks (decision 21 (a), plan 14
WP2): ``[output] overlay = true``. Otherwise the render window is created
without a transparent framebuffer (app._windows) and ``output.overlay``
refuses to switch on — the ``T`` key, the APC40's MASTER select, the
panel and a preset all land on the one param, so one gate covers every
road — and the ground (``output.bg``, the crossfader) and opacity do
nothing, since they only ever act in overlay. The show behind a Pepper's
Ghost glass can never go see-through by accident.

When it is allowed, the window is created with a transparent framebuffer
from the start (a creation-time GLFW hint), so toggling is only
attributes, position and the clear alpha. Every GLFW/Cocoa call goes through `apply()`, once per
frame, and only when something changed. The window-system backend is
injectable so the state machine tests headlessly.
"""

from __future__ import annotations

import sys

from .params import Param, Registry

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

    def set_fullscreen(self, win, m) -> None:
        # the monitor's current mode: GLFW then skips the mode switch
        mode = self.glfw.get_video_mode(m)
        self.glfw.set_window_monitor(win, m, 0, 0, mode.size.width, mode.size.height,
                                     mode.refresh_rate)

    def set_windowed(self, win, x, y, w, h) -> None:
        self.glfw.set_window_monitor(win, None, x, y, w, h, 0)

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

    def window_state(self, win) -> dict:
        """What the stall log records about the render window (watchdog.
        RenderWatch): visible, iconified, focused, its monitor, its
        framebuffer and rect — and on macOS whether the NSWindow is occluded
        (covered, or on a Space that is not showing). `presentable` is
        whether a completed frame reaches the screen. Read-only."""
        g = self.glfw
        fb = tuple(g.get_framebuffer_size(win))
        mon = g.get_window_monitor(win)
        st = {
            "visible": bool(g.get_window_attrib(win, g.VISIBLE)),
            "iconified": bool(g.get_window_attrib(win, g.ICONIFIED)),
            "focused": bool(g.get_window_attrib(win, g.FOCUSED)),
            "monitor": self.monitor_name(mon) if mon else "none (windowed)",
            "framebuffer": fb,
            "rect": self.window_rect(win),
        }
        ns = self._nswindow(win)
        if ns is not None:
            try:
                st["occluded"] = not (int(ns.occlusionState()) & 2)   # NSWindowOcclusionStateVisible
                st["on_active_space"] = bool(ns.isOnActiveSpace())
            except Exception:  # noqa: BLE001, S110 — an older pyobjc: GLFW's view only
                pass
        st["presentable"] = (st["visible"] and not st["iconified"]
                             and not st.get("occluded", False) and fb[0] > 0 and fb[1] > 0)
        return st

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


class Output:
    """The render window's output state, its params, and the once-per-frame apply."""

    GATED = "off in the config: set [output] overlay = true in config.toml"

    def __init__(self, win, backend=None, *, allowed: bool = False):
        self.win = win
        self.backend = backend
        # decision 21 (a): the config's [output] overlay; False (the
        # default) means overlay can never switch on (_set_overlay)
        self.allowed = bool(allowed)
        self.fullscreen = False
        self.overlay = False
        self.passthrough = True  # an overlay should not block what is under it
        self.bg = 0.0
        self.alpha = 1.0
        self.monitor = -1        # index into backend.monitors(); −1 = the window's own
                                 # ("follow window", the enum's first choice)
        self._applied: dict = {"mode": "window"}  # the window starts as a plain window
        self._saved_rect = None
        self.error = ""

    # ---- params ----

    def register(self, reg: Registry) -> None:
        g = "output"
        rig = {"persist": False, "modulatable": False}
        # index 0 is "follow window" (monitor −1: the screen holding the
        # window, resolved by _target_monitor); the screens follow (audit P3)
        reg.enum("output.monitor", "Screen", lambda: self.monitor + 1,
                 lambda i: setattr(self, "monitor", int(i) - 1), self.screen_names, group=g,
                 tip="Which screen fullscreen and overlay cover: the one the window is "
                     "on, or a screen by name.", **rig)
        reg.toggle("output.fullscreen", "Fullscreen", lambda: self.fullscreen,
                   lambda v: setattr(self, "fullscreen", bool(v)), group=g,
                   tip="Borderless, covering the chosen screen — for the projector. "
                       "No video-mode switch.", **rig)
        reg.toggle("output.overlay", "Overlay", lambda: self.overlay,
                   self._set_overlay, group=g,
                   tip="Float the render, frameless and see-through, over the whole "
                       "screen — above a fullscreen video. T toggles.", **rig)
        reg.toggle("output.passthrough", "Click-through", lambda: self.passthrough,
                   lambda v: setattr(self, "passthrough", bool(v)), group=g,
                   tip="On (the default): in overlay, clicks go to whatever is underneath, "
                       "so you can run the video behind. The render window then never "
                       "takes focus — keys still work from the control window; to orbit "
                       "again press G there, or use the pan button on the APC40.", **rig)
        reg.continuous("output.bg", "Ground", lambda: self.bg,
                       lambda v: setattr(self, "bg", float(v)), lo=0.0, hi=1.0,
                       fmt=lambda v: "clear" if v <= 0 else f"{v:.2f} black", group=g,
                       tip="Darkness of the ground behind the shape in overlay mode: "
                           "0 fully see-through, 1 black.")
        reg.continuous("output.alpha", "Opacity", lambda: self.alpha,
                       lambda v: setattr(self, "alpha", float(v)), lo=0.0, hi=1.0,
                       fmt=lambda v: f"{v * 100:.0f}%", group=g,
                       tip="Opacity of the whole render window in overlay mode.")
        # the pre-split ids: views onto the params above, never saved or
        # driven. The factory table and apc40.py bind these (overlay.on /
        # .passthrough / .bg), so they are what the rows name
        for old, new in (("on", "overlay"), ("passthrough", "passthrough"),
                         ("bg", "bg"), ("alpha", "alpha"), ("monitor", "monitor")):
            p = reg[f"output.{new}"]
            reg.add(Param(f"overlay.{old}", p.label, p.kind, p.get, p.put, group=g,
                          tip=p.tip, lo=p.lo, hi=p.hi, fmt=p.fmt, choices=p.choices,
                          alias=True))

    def _set_overlay(self, v) -> None:
        """The one door into overlay mode: shut unless the config asks."""
        self.overlay = bool(v) and self.allowed

    def monitor_names(self) -> list[str]:
        if self.backend is None:
            return ["screen"]
        try:
            return [self.backend.monitor_name(m) or f"screen {i + 1}"
                    for i, m in enumerate(self.backend.monitors())]
        except Exception:  # noqa: BLE001
            return ["screen"]

    FOLLOW = "follow window"

    def screen_names(self) -> list[str]:
        """The enum's choices: "follow window" (monitor −1), then every screen."""
        return [self.FOLLOW, *self.monitor_names()]

    # ---- per frame ----

    @property
    def mode(self) -> str:
        """window · fullscreen · overlay — the overlay wins when both are on."""
        on = self.overlay and self.allowed
        return "overlay" if on else "fullscreen" if self.fullscreen else "window"

    @property
    def bg_alpha(self) -> float:
        """What the renderer clears to this frame."""
        return self.bg if self.mode == "overlay" else 1.0

    def apply(self) -> None:
        """Push state to the window; each attribute only when it changed."""
        if self.win is None or self.backend is None:
            return
        b, win = self.backend, self.win
        try:
            # a mode change always goes through the plain window: leave the
            # old mode completely, then enter the new one — rare enough that
            # the round trip beats a matrix of partial transitions
            was, mode = self._applied["mode"], self.mode
            if self._changed("mode", mode):
                if was == "window":
                    self._saved_rect = b.window_rect(win)
                self._leave(was)
                self._enter(mode)
            elif mode != "window" and self._changed("monitor", self.monitor):
                self._enter(mode)  # same mode, another screen
            on = mode == "overlay"
            want_pt = on and self.passthrough
            if self._changed("passthrough", want_pt):
                b.set_attrib(win, "MOUSE_PASSTHROUGH", want_pt)
            want_a = self.alpha if on else 1.0
            if self._changed("alpha", round(want_a, 3)):
                b.set_opacity(win, want_a)
            self.error = ""
        except Exception as e:  # noqa: BLE001 — a window-system hiccup must not kill the loop
            self.error = f"output: {e}"[:120]

    def _enter(self, mode: str) -> None:
        b, win = self.backend, self.win
        m = self._target_monitor()
        self._applied["monitor"] = self.monitor
        if mode == "window" or m is None:
            return
        if mode == "fullscreen":
            # GLFW's own fullscreen: above the menu bar, no mode switch
            b.set_fullscreen(win, m)
        else:
            # a borderless cover, floated above every Space; the
            # transparent framebuffer does the see-through. Level first:
            # Cocoa keeps a normal-level window below the menu bar
            b.set_attrib(win, "DECORATED", False)
            b.set_attrib(win, "FLOATING", True)
            b.raise_over_spaces(win, True)
            b.set_rect(win, *b.monitor_rect(m))

    def _leave(self, mode: str) -> None:
        b, win = self.backend, self.win
        if mode == "window" or self._saved_rect is None:
            return
        if mode == "fullscreen":
            b.set_windowed(win, *self._saved_rect)
        else:
            b.raise_over_spaces(win, False)
            b.set_attrib(win, "FLOATING", False)
            b.set_attrib(win, "DECORATED", True)
            b.set_rect(win, *self._saved_rect)

    def _changed(self, key: str, value) -> bool:
        if self._applied.get(key, object()) == value:
            return False
        self._applied[key] = value
        return True

    def _target_monitor(self):
        """The chosen screen, or the one holding the window when none is chosen."""
        b = self.backend
        mons = b.monitors()
        if not mons:
            return None
        if 0 <= self.monitor < len(mons):
            return mons[self.monitor]
        x, y, w, h = self._saved_rect or b.window_rect(self.win)
        cx, cy = x + w / 2, y + h / 2
        for m in mons:
            mx, my, mw, mh = b.monitor_rect(m)
            if mx <= cx < mx + mw and my <= cy < my + mh:
                return m
        return mons[0]
